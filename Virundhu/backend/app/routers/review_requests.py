"""Ask guests for feedback on WhatsApp."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, require_writable
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Review, ReviewRequest
from app.services import review_requests

router = APIRouter(prefix="/api/v1/review-requests", tags=["review requests"])


class RequestIn(BaseModel):
    numbers: list[str] = Field(min_length=1, max_length=review_requests.MAX_PER_BATCH)
    outlet_id: int | None = None
    consent: bool = False  # "these guests agreed to hear from us"


class RequestOut(BaseModel):
    phone: str
    status: str
    link: str | None = None


class RequestsResult(BaseModel):
    results: list[RequestOut]
    sending_automatically: bool


class StatsOut(BaseModel):
    asked_30d: int
    feedback_30d: int
    sending_automatically: bool


@router.post("", response_model=RequestsResult)
@limiter.limit("20/minute")
def ask(request: Request, body: RequestIn, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(400, "Only message guests who agreed to hear from you. Tick the box to confirm.")
    if ctx.outlet_ids is not None and body.outlet_id not in ctx.outlet_ids:
        raise HTTPException(403, "You can only ask guests of your own outlet.")
    results = review_requests.send_requests(db, ctx.org, body.numbers, body.outlet_id)
    return RequestsResult(
        results=[RequestOut(**r.__dict__) for r in results], sending_automatically=settings.whatsapp_enabled
    )


@router.get("/stats", response_model=StatsOut)
def stats(ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)) -> StatsOut:
    since = datetime.now(UTC) - timedelta(days=30)
    asked = db.scalar(
        select(func.count(ReviewRequest.id)).where(
            ReviewRequest.organization_id == ctx.org.id, ReviewRequest.created_at >= since
        )
    )
    feedback = db.scalar(
        select(func.count(Review.id)).where(
            Review.organization_id == ctx.org.id, Review.platform == "direct", Review.created_at >= since
        )
    )
    return StatsOut(asked_30d=asked or 0, feedback_30d=feedback or 0, sending_automatically=settings.whatsapp_enabled)
