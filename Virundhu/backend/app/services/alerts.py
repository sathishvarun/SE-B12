"""Instant alerts: the moment a review is read as urgent, owners and managers hear about it."""

import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertLog, AlertRule, Membership, Notification, Organization, Outlet, Review, ReviewAnalysis, User
from app.services import whatsapp
from app.services.emailer import send_email

logger = logging.getLogger(__name__)
CATEGORY_WORDS = {
    "hygiene": "Food-safety complaint",
    "delivery": "Delivery complaint",
    "staff": "Staff complaint",
    "food_quality": "Food complaint",
    "price": "Billing complaint",
    "packaging": "Packaging complaint",
    "app": "Ordering problem",
    "other": "Complaint",
}


def alert_for_review(db: Session, review: Review, analysis: ReviewAnalysis) -> int:
    """Create in-app notifications and send one email for an urgent review. Returns notifications created."""
    if analysis.urgency != "high":
        return 0
    org = db.get(Organization, review.organization_id)
    if org is None:
        return 0
    outlet = db.get(Outlet, review.outlet_id) if review.outlet_id else None
    if outlet is None:
        where = org.name
    else:
        where = outlet.name if "outlet" in outlet.name.lower() else f"{outlet.name} outlet"
    title = f"{CATEGORY_WORDS.get(analysis.category or 'other', 'Complaint')} at {where}"
    body = f"{analysis.summary or review.review_text[:180]} ({review.platform.title()}, {review.rating}★)"
    if review.is_sample:
        title = f"Sample: {title}"
        body = f"{body}. This is sample data, not a real guest."

    # In-app: every owner and manager of this restaurant
    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == org.id, Membership.role.in_(("owner", "manager")), User.is_active)
    ).all()
    # Owners hear about every outlet; managers only about the outlets they look after.
    members = [u for u, m in rows if m.role == "owner" or not m.outlet_ids or review.outlet_id in m.outlet_ids]
    created = 0
    for user in members:
        stmt = (
            insert(Notification)
            .values(
                organization_id=org.id,
                user_id=user.id,
                review_id=review.id,
                severity="high",
                title=title,
                body=body,
            )
            .on_conflict_do_nothing(constraint="uq_notification_user_review")
        )
        created += db.execute(stmt).rowcount or 0

    # Email: alert-rule recipients plus owners/managers, once per review per address
    recipients = {u.email for u in members}
    for rule in db.scalars(select(AlertRule).where(AlertRule.organization_id == org.id, AlertRule.is_active)):
        if rule.outlet_ids and review.outlet_id not in rule.outlet_ids:
            continue
        if rule.categories and analysis.category not in rule.categories:
            continue
        recipients.update(rule.recipients or [])
    outlet = db.get(Outlet, review.outlet_id) if review.outlet_id else None
    if outlet and outlet.manager_email:  # the branch manager hears about their own branch
        recipients.add(outlet.manager_email.lower())
    if review.is_sample:  # never email anyone about sample data
        recipients = set()
    fresh = []
    for email in sorted(recipients):
        res = db.execute(
            insert(AlertLog)
            .values(
                organization_id=org.id,
                review_id=review.id,
                channel="email",
                recipient=email,
                status="queued",
            )
            .on_conflict_do_nothing(constraint="uq_alert_review_recipient")
        )
        if res.rowcount:
            fresh.append(email)
    db.commit()
    if fresh:
        link = f"{settings.APP_URL}/app/inbox?view=today&id={review.id}"
        text = (
            f'{title}\n\n{body}\n\nWhat the guest wrote:\n"{review.review_text}"\n\n'
            f"Suggested reply:\n{analysis.suggested_reply or ''}\n\nOpen it in Virundhu: {link}\n"
        )
        ok = send_email(fresh, f"Urgent: {title}", text)
        for row in db.scalars(select(AlertLog).where(AlertLog.review_id == review.id, AlertLog.recipient.in_(fresh))):
            row.status = "sent" if ok else "failed"
            row.sent_at = datetime.now(UTC) if ok else None
        db.commit()
    sent_wa = _whatsapp(db, org, review, title, body)
    logger.info(
        "Alert for review %s: %d notifications, %d emails, %d WhatsApp", review.id, created, len(fresh), sent_wa
    )
    return created


def _whatsapp(db: Session, org: Organization, review: Review, title: str, body: str) -> int:
    """One WhatsApp message per number per review (deduplicated through AlertLog). Never for sample data."""
    numbers = list(org.whatsapp_numbers or [])
    outlet = db.get(Outlet, review.outlet_id) if review.outlet_id else None
    if outlet and outlet.manager_phone:
        mp = re.sub(r"[\s-]", "", outlet.manager_phone)
        mp = mp if mp.startswith("+") else f"+91{mp[-10:]}"
        if re.fullmatch(r"\+\d{10,15}", mp) and mp not in numbers:
            numbers.append(mp)
    if review.is_sample or not settings.whatsapp_enabled or not numbers:
        return 0
    link = f"{settings.APP_URL}/app/inbox?view=today&id={review.id}"
    sent = 0
    for number in numbers:
        first = db.execute(
            insert(AlertLog)
            .values(
                organization_id=org.id,
                review_id=review.id,
                channel="whatsapp",
                recipient=f"wa:{number}",
                status="queued",
            )
            .on_conflict_do_nothing(constraint="uq_alert_review_recipient")
        ).rowcount
        db.commit()
        if not first:
            continue
        ok = whatsapp.send_alert(number, org.name, f"{title}. {body}", link)
        row = db.scalar(select(AlertLog).where(AlertLog.review_id == review.id, AlertLog.recipient == f"wa:{number}"))
        if row:
            row.status = "sent" if ok else "failed"
            row.sent_at = datetime.now(UTC) if ok else None
            db.commit()
        sent += int(ok)
    return sent
