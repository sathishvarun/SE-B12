"""The restaurant's own feedback link (QR code on the bill, the food packet, the WhatsApp order message).

Guests rate the food without signing in. The review goes straight into Virundhu as platform "direct",
is read by the AI and raises alerts like any other review: no Zomato or Swiggy needed.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import Organization, Outlet, Review
from app.services.dates import today_local
from app.services.intake import default_outlet
from app.services.queue import enqueue_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/public/feedback", tags=["feedback"])


def _org(db: Session, token: str) -> Organization:
    org = db.scalar(select(Organization).where(Organization.feedback_token == token))
    if org is None or org.is_suspended or org.is_demo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This feedback link isn't active.")
    return org


@router.get("/{token}")
def feedback_form(token: str, db: Session = Depends(get_db)) -> dict:
    org = _org(db, token)
    outlets = db.scalars(
        select(Outlet).where(Outlet.organization_id == org.id, Outlet.is_active).order_by(Outlet.name)
    ).all()
    return {"restaurant": org.name, "city": org.city, "outlets": [{"id": o.id, "name": o.name} for o in outlets]}


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)
    outlet_id: int | None = None
    name: str = Field(default="", max_length=80)
    contact: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=200)  # honeypot: people never see or fill this


@router.post("/{token}", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def send_feedback(request: Request, token: str, body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    org = _org(db, token)
    if body.website:  # a bot filled the hidden field: pretend it worked, store nothing
        return {"thanks": True, "google_review_url": None}
    if body.rating <= 3 and len(body.text.strip()) < 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please tell us what went wrong, so we can fix it.")
    outlet = None
    if body.outlet_id:
        outlet = db.scalar(select(Outlet).where(Outlet.id == body.outlet_id, Outlet.organization_id == org.id))
    outlet = outlet or default_outlet(db, org.id)
    review = Review(
        organization_id=org.id,
        outlet_id=outlet.id if outlet else None,
        external_id=f"QR-{uuid.uuid4().hex[:16]}",
        platform="direct",
        rating=body.rating,
        review_date=today_local(),
        review_text=body.text.strip() or f"{body.rating} stars, no comment.",
        guest_name=body.name.strip() or None,
        guest_contact=body.contact.strip() or None,
        analysis_status="pending",
        workflow_status="new",
    )
    db.add(review)
    db.commit()
    await enqueue_analysis(org.id, [review.id])
    # Google's rules: invite every guest to post on Google, never only the happy ones.
    return {"thanks": True, "google_review_url": org.google_review_url}
