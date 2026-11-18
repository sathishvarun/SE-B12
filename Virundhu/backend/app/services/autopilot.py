"""Google auto-pilot: post the reply draft by itself on happy Google reviews, so the owner only handles the rest.

A review is auto-replied only when ALL of these hold (anything doubtful waits for a person):
- the restaurant turned auto-pilot on and its plan is active (not an expired trial or plan);
- it came from the Google connection (has source_ref) and has no reply yet;
- stars >= the restaurant's minimum (3, 4 or 5); 4-5 stars need a positive reading, 3 stars a neutral or positive
  one; urgency low, no food-safety flag;
- the AI wrote a reply draft.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, Review, ReviewAnalysis, Subscription
from app.services import google_reviews

logger = logging.getLogger(__name__)


def plan_active(db: Session, org: Organization) -> bool:
    now = datetime.now(UTC)
    if org.is_suspended:
        return False
    if org.plan == "trial":
        return not (org.trial_ends_at and org.trial_ends_at < now)
    sub = db.scalar(select(Subscription).where(Subscription.organization_id == org.id))
    return not (sub and sub.current_period_end and sub.current_period_end < now)


def eligible(org: Organization, review: Review, analysis: ReviewAnalysis | None) -> bool:
    return bool(
        org.autopilot_enabled
        and review.platform == "google"
        and review.source_ref
        and not review.is_sample
        and review.workflow_status == "new"
        and review.rating >= max(3, org.autopilot_min_rating or 4)
        and analysis is not None
        and analysis.status == "analyzed"
        and (analysis.sentiment == "positive" or (review.rating == 3 and analysis.sentiment == "neutral"))
        and analysis.urgency == "low"
        and analysis.category != "hygiene"
        and not analysis.safety_override
        and (analysis.suggested_reply or "").strip()
    )


def maybe_auto_reply(db: Session, review: Review, analysis: ReviewAnalysis | None) -> bool:
    """Post the draft to Google if the review qualifies. Never raises: a failure just leaves it for the owner."""
    org = db.get(Organization, review.organization_id)
    if org is None or not eligible(org, review, analysis) or not plan_active(db, org):
        return False
    try:
        google_reviews.post_reply(db, org.id, review, analysis.suggested_reply.strip())
    except Exception as exc:  # Google down, token revoked, API not approved
        logger.warning("Auto-pilot couldn't reply to review %s: %s", review.id, exc)
        db.rollback()
        return False
    review.auto_replied = True
    db.commit()
    logger.info("Auto-pilot replied to Google review %s for org %s", review.id, org.id)
    return True


def holding_text(org: Organization, outlet_phone: str | None) -> str:
    """A safe first reply to an unhappy review: sorry + how to reach us. Never admits fault, never promises a refund."""
    phone = outlet_phone or org.owner_phone
    reach = (
        f"Please call us on {phone} so we can put it right." if phone else "Please reply here so we can put it right."
    )
    sorry = "We're sorry your experience wasn't what it should have been, and thank you for telling us."
    return f"{sorry} {reach} - Team {org.name}"


def send_holding_replies(db: Session) -> int:
    """Where switched on: unhappy Google reviews nobody answered within N hours get the safe reply.

    The review stays in the owner's inbox (status 'in progress') so a person still follows up.
    """
    from datetime import timedelta

    from app.models import Outlet

    sent = 0
    now = datetime.now(UTC)
    for org in db.scalars(
        select(Organization).where(Organization.holding_reply_hours.is_not(None), Organization.holding_reply_hours > 0)
    ):
        if not plan_active(db, org):
            continue
        cutoff = now - timedelta(hours=org.holding_reply_hours)
        rows = db.scalars(
            select(Review)
            .where(
                Review.organization_id == org.id,
                Review.platform == "google",
                Review.source_ref.is_not(None),
                Review.is_sample.is_(False),
                Review.workflow_status == "new",
                Review.rating <= 2,
                Review.holding_reply_at.is_(None),
                Review.created_at <= cutoff,
                Review.created_at >= now - timedelta(days=14),  # never reply to very old reviews by surprise
            )
            .limit(50)
        )
        for review in rows:
            outlet = db.get(Outlet, review.outlet_id) if review.outlet_id else None
            try:
                google_reviews.post_reply(db, org.id, review, holding_text(org, outlet.phone if outlet else None))
            except Exception as exc:
                logger.warning("Holding reply failed for review %s: %s", review.id, exc)
                db.rollback()
                continue
            review.holding_reply_at = now
            review.workflow_status = "in_progress"  # a person still needs to call or reply properly
            db.commit()
            sent += 1
    return sent
