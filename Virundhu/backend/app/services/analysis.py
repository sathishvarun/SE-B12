"""Read reviews with the configured AI provider, store results, enforce quotas, fire instant alerts."""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.ai.safety import has_food_safety_risk
from app.ai.tagging import TaggingError, tag_review
from app.config import settings
from app.models import ImportBatch, Organization, Review, ReviewAnalysis, UsageCounter
from app.services.alerts import alert_for_review
from app.services.autopilot import maybe_auto_reply
from app.services.plans import limits_for

logger = logging.getLogger(__name__)
_LETTERS = re.compile(r"[A-Za-z஀-௿]")


def _cost_inr(input_tokens: int, output_tokens: int) -> Decimal:
    usd = (
        input_tokens * settings.LLM_PRICE_INPUT_PER_M_USD + output_tokens * settings.LLM_PRICE_OUTPUT_PER_M_USD
    ) / 1_000_000
    return Decimal(str(round(usd * settings.USD_INR, 4)))


def _rating_only(review: Review) -> dict:
    """Reviews with no words (empty or only emoji) are tagged from the stars alone, without an AI call."""
    r = review.rating
    sentiment = "positive" if r >= 4 else "neutral" if r == 3 else "negative"
    return {
        "sentiment": sentiment,
        "category": "other",
        "urgency": "medium" if r <= 2 else "low",
        "language": "other",
        "summary": f"{r}-star rating with no written comment.",
        "suggested_reply": "Thank you for your rating! We'd love to hear more about your visit.",
        "safety_override": False,
        "model_used": "rules",
        "input_tokens": 0,
        "output_tokens": 0,
    }


def _usage(db: Session, org_id: int) -> UsageCounter:
    period = datetime.now(UTC).strftime("%Y-%m")
    db.execute(
        insert(UsageCounter)
        .values(organization_id=org_id, period=period, reviews_analyzed=0, cost_inr=0)
        .on_conflict_do_nothing(constraint="uq_usage_org_period")
    )
    return db.scalar(select(UsageCounter).where(UsageCounter.organization_id == org_id, UsageCounter.period == period))


def analyze_reviews(db: Session, org_id: int, review_ids: list[int], batch_id: int | None = None) -> dict[str, int]:
    """Analyze pending reviews of one organization. Safe to call twice (already analyzed reviews are skipped)."""
    org = db.get(Organization, org_id)
    if org is None:
        return {"analyzed": 0}
    from app.services.autopilot import plan_active

    if not org.is_demo and not plan_active(db, org):
        # Trial or plan has ended (or the account is suspended): keep the reviews, but don't spend AI on them. They are
        # read automatically once the restaurant pays (worker retry picks up "pending_quota").
        db.query(Review).filter(
            Review.organization_id == org_id,
            Review.id.in_(review_ids),
            Review.analysis_status.in_(("pending", "needs_review")),
        ).update({"analysis_status": "pending_quota"}, synchronize_session=False)
        db.commit()
        return {"analyzed": 0, "waiting_for_payment": len(review_ids)}
    reviews = db.scalars(
        select(Review)
        .where(
            Review.organization_id == org_id,
            Review.id.in_(review_ids),
            Review.analysis_status.in_(("pending", "pending_quota", "needs_review")),
        )
        .order_by(Review.id)
    ).all()
    usage = _usage(db, org_id)
    room = max(0, limits_for(org)["reviews_per_month"] - usage.reviews_analyzed) if not org.is_demo else len(reviews)
    to_run, over = reviews[:room], reviews[room:]
    for r in over:
        r.analysis_status = "pending_quota"
    db.commit()

    def run(review: Review) -> tuple[int, dict | None]:
        if not _LETTERS.search(review.review_text or ""):
            return review.id, _rating_only(review)
        if not settings.llm_configured:
            return review.id, None
        try:
            return review.id, tag_review(
                review.review_text,
                review.rating,
                review.platform,
                org.reply_tone,
                org.reply_signature or f"- Team {org.name}",
                org_id=org.id,
            )
        except TaggingError as exc:
            logger.warning("Review %s could not be read: %s", review.id, exc)
            return review.id, None

    by_id = {r.id: r for r in to_run}
    stats = {"analyzed": 0, "needs_review": 0, "pending_quota": len(over), "alerts": 0}
    with ThreadPoolExecutor(max_workers=max(1, settings.LLM_MAX_CONCURRENCY)) as pool:
        for review_id, result in pool.map(run, to_run):
            review = by_id[review_id]
            analysis = db.scalar(select(ReviewAnalysis).where(ReviewAnalysis.review_id == review_id))
            if result is None:
                review.analysis_status = "needs_review"
                if analysis is None:
                    db.add(
                        ReviewAnalysis(review_id=review_id, status="needs_review", attempts=1, safety_override=False)
                    )
                    db.flush()
                    a = db.scalar(select(ReviewAnalysis).where(ReviewAnalysis.review_id == review_id))
                    if has_food_safety_risk(review.review_text):
                        # Even without the AI, food-safety words make it urgent.
                        a.urgency, a.category, a.sentiment = "high", "hygiene", "negative"
                        a.summary = "Possible food-safety complaint. Read the review."
                    else:
                        # Sort it by the stars until the AI can read it, so a 1-2 star review is never hidden.
                        r = review.rating
                        a.urgency = "medium" if r <= 2 else "low"
                        a.sentiment = "positive" if r >= 4 else "neutral" if r == 3 else "negative"
                        a.summary = "Not read by the AI yet; sorted by its stars. It will be read again shortly."
                stats["needs_review"] += 1
            else:
                cost = _cost_inr(result["input_tokens"], result["output_tokens"])
                values = {
                    k: result.get(k)
                    for k in (
                        "sentiment",
                        "category",
                        "urgency",
                        "language",
                        "summary",
                        "suggested_reply",
                        "dishes",
                        "staff",
                        "safety_override",
                        "model_used",
                        "input_tokens",
                        "output_tokens",
                    )
                }
                if analysis is None:
                    analysis = ReviewAnalysis(
                        review_id=review_id, status="analyzed", cost_inr=cost, attempts=1, **values
                    )
                    db.add(analysis)
                else:
                    for k, v in values.items():
                        setattr(analysis, k, v)
                    analysis.status, analysis.cost_inr, analysis.attempts = "analyzed", cost, analysis.attempts + 1
                review.analysis_status = "analyzed"
                usage.reviews_analyzed += 1
                usage.cost_inr = (usage.cost_inr or 0) + cost
                stats["analyzed"] += 1
            if batch_id:
                batch = db.get(ImportBatch, batch_id)
                if batch:
                    batch.analyzed_rows += 1
            db.commit()
            final = db.scalar(select(ReviewAnalysis).where(ReviewAnalysis.review_id == review_id))
            if final and final.urgency == "high":
                stats["alerts"] += alert_for_review(db, review, final)
            elif final and maybe_auto_reply(db, review, final):
                stats["auto_replied"] = stats.get("auto_replied", 0) + 1
    if batch_id:
        batch = db.get(ImportBatch, batch_id)
        if batch:
            batch.status, batch.finished_at = "completed", datetime.now(UTC)
            db.commit()
    return stats
