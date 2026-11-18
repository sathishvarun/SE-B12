"""Review inbox: list with filters, detail, update status/reply."""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ai.safety import has_food_safety_risk
from app.auth.deps import OrgContext, get_org_context, require_writable
from app.database import get_db
from app.models import Outlet, Review, ReviewAnalysis
from app.schemas.reviews import AnalysisOut, ReviewOut, ReviewPage, ReviewUpdate
from app.services import google_reviews

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
View = Literal["all", "today", "week", "replied"]
PENDING = ("new", "in_progress")


def _view_filter(view: View):  # noqa: ANN202
    if view == "today":
        return and_(ReviewAnalysis.urgency == "high", Review.workflow_status.in_(PENDING))
    if view == "week":
        return and_(ReviewAnalysis.urgency == "medium", Review.workflow_status.in_(PENDING))
    if view == "replied":
        return Review.workflow_status == "replied"
    return None


def _to_out(r: Review, outlets: dict[int, str]) -> ReviewOut:
    a = r.analysis
    return ReviewOut(
        id=r.id,
        external_id=r.external_id,
        platform=r.platform,
        rating=r.rating,
        review_date=r.review_date,
        review_text=r.review_text,
        outlet_id=r.outlet_id,
        outlet_name=outlets.get(r.outlet_id or 0),
        workflow_status=r.workflow_status,
        final_reply=r.final_reply,
        is_sample=r.is_sample,
        reply_posted_at=r.reply_posted_at,
        can_post_to_google=r.platform == "google" and bool(r.source_ref),
        auto_replied=r.auto_replied,
        guest_name=r.guest_name,
        guest_contact=r.guest_contact,
        analysis=AnalysisOut(
            sentiment=a.sentiment,
            category=a.category,
            urgency=a.urgency,
            language=a.language,
            summary=a.summary,
            suggested_reply=a.suggested_reply,
            safety_override=a.safety_override,
            food_safety=has_food_safety_risk(r.review_text),
        )
        if a
        else None,
    )


def _outlet_names(db: Session, org_id: int) -> dict[int, str]:
    return {o.id: o.name for o in db.scalars(select(Outlet).where(Outlet.organization_id == org_id))}


@router.get("", response_model=ReviewPage)
def list_reviews(
    view: View = "all",
    outlet_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    ctx: OrgContext = Depends(get_org_context),
    db: Session = Depends(get_db),
) -> ReviewPage:
    """Reviews of the current restaurant, urgent first, newest first."""
    base: Select = (
        select(Review)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Review.organization_id == ctx.org.id)
    )
    if ctx.outlet_ids is not None:
        base = base.where(Review.outlet_id.in_(ctx.outlet_ids))
    if outlet_id:
        base = base.where(Review.outlet_id == outlet_id)
    if q:
        base = base.where(or_(Review.review_text.ilike(f"%{q}%"), ReviewAnalysis.summary.ilike(f"%{q}%")))

    counts = {}
    for name in ("all", "today", "week", "replied"):
        f = _view_filter(name)  # type: ignore[arg-type]
        stmt = base.with_only_columns(func.count(Review.id))
        counts[name] = db.scalar(stmt.where(f) if f is not None else stmt) or 0

    f = _view_filter(view)
    stmt = base.where(f) if f is not None else base
    urgency_rank = case((ReviewAnalysis.urgency == "high", 0), (ReviewAnalysis.urgency == "medium", 1), else_=2)
    pending_rank = case((Review.workflow_status.in_(PENDING), 0), else_=1)
    order = [pending_rank, urgency_rank, Review.review_date.desc(), Review.id.desc()]
    total = db.scalar(stmt.with_only_columns(func.count(Review.id))) or 0
    rows = db.scalars(
        stmt.options(selectinload(Review.analysis)).order_by(*order).offset((page - 1) * page_size).limit(page_size)
    ).all()
    names = _outlet_names(db, ctx.org.id)
    return ReviewPage(
        items=[_to_out(r, names) for r in rows], total=total, page=page, page_size=page_size, counts=counts
    )


def _get_owned(db: Session, org_id: int, review_id: int, ctx: OrgContext | None = None) -> Review:
    review = db.scalar(
        select(Review)
        .options(selectinload(Review.analysis))
        .where(Review.id == review_id, Review.organization_id == org_id)
    )
    if review is None or (ctx is not None and not ctx.can_see_outlet(review.outlet_id)):
        raise HTTPException(404, "Review not found.")
    return review


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> ReviewOut:
    """One review with its analysis."""
    return _to_out(_get_owned(db, ctx.org.id, review_id, ctx), _outlet_names(db, ctx.org.id))


@router.patch("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int, body: ReviewUpdate, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)
) -> ReviewOut:
    """Change status or save the reply the team posted."""
    review = _get_owned(db, ctx.org.id, review_id, ctx)
    if body.final_reply is not None:
        review.final_reply = body.final_reply
    if body.workflow_status:
        review.workflow_status = body.workflow_status
        review.replied_at = datetime.now(UTC) if body.workflow_status == "replied" else None
    db.commit()
    return _to_out(review, _outlet_names(db, ctx.org.id))


class PostReplyIn(BaseModel):
    text: str = Field(min_length=2, max_length=4000)


@router.post("/{review_id}/post-reply", response_model=ReviewOut)
def post_reply(
    review_id: int, body: PostReplyIn, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)
) -> ReviewOut:
    """Publish the reply on Google for reviews that came from the Google connection."""
    review = _get_owned(db, ctx.org.id, review_id, ctx)
    try:
        google_reviews.post_reply(db, ctx.org.id, review, body.text.strip())
    except google_reviews.GoogleError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _to_out(review, _outlet_names(db, ctx.org.id))
