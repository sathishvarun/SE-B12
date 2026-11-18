"""Contact page: a restaurant asks for a demo. Saved as a lead and emailed to the platform admin."""

import logging

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import Lead
from app.services import activity

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/public/contact", tags=["contact"])


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    restaurant: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=160)
    city: str = Field(default="", max_length=80)
    outlets: int | None = Field(default=None, ge=1, le=1000)
    message: str = Field(default="", max_length=2000)
    website: str = Field(default="", max_length=200)  # honeypot

    @model_validator(mode="after")
    def _reachable(self) -> "ContactIn":
        if not self.phone.strip() and "@" not in self.email:
            raise ValueError("Give us a phone number or an email so we can reach you.")
        return self


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def contact(request: Request, body: ContactIn, db: Session = Depends(get_db)) -> dict:
    if body.website:
        return {"ok": True}
    lead = Lead(
        name=body.name.strip(),
        restaurant=body.restaurant.strip(),
        phone=body.phone.strip() or None,
        email=body.email.strip().lower() or None,
        city=body.city.strip() or None,
        outlets=body.outlets,
        message=body.message.strip() or None,
    )
    db.add(lead)
    db.commit()
    activity.record(
        db,
        "demo_request",
        restaurant=lead.restaurant,
        email=lead.email or lead.phone,
        detail=f"{lead.name}, {lead.city or 'city not given'}, {lead.outlets or '?'} outlets",
        commit=True,
    )
    return {"ok": True}
