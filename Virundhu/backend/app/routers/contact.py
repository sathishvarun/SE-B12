"""Contact page: a restaurant asks for a demo. Saved as a lead and emailed to the platform admin."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import DemoMeeting, DemoPrep, Lead
from app.services import activity, agent_team, demo_prep

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
    meet_mode: str = Field(default="meet", pattern="^(meet|zoom|teams|in_person|phone)$")
    maps_link: str = Field(default="", max_length=500)  # optional: we draft replies to their latest reviews

    @model_validator(mode="after")
    def _reachable(self) -> "ContactIn":
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise ValueError("Give us your email; our demo agent sends the times there within a minute.")
        return self


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def contact(request: Request, body: ContactIn, db: Session = Depends(get_db)) -> dict:
    if body.website:
        return {"ok": True}
    link = body.maps_link.strip()
    if link and not demo_prep.is_maps_link(link):
        raise HTTPException(422, "That doesn't look like a Google Maps link. Copy it from the Share button on Maps.")
    lead = Lead(
        name=body.name.strip(),
        restaurant=body.restaurant.strip(),
        phone=body.phone.strip() or None,
        email=body.email.strip().lower() or None,
        city=body.city.strip() or None,
        outlets=body.outlets,
        message=body.message.strip() or None,
        meet_mode=body.meet_mode,
        maps_link=link or None,
    )
    db.add(lead)
    db.commit()
    if link:  # the demo opens with replies to their own three latest Google reviews
        prep = DemoPrep(lead_id=lead.id, restaurant=lead.restaurant, maps_link=link, created_by="contact form")
        db.add(prep)
        db.commit()
        await demo_prep.enqueue(prep.id)
    activity.record(
        db,
        "demo_request",
        restaurant=lead.restaurant,
        email=lead.email or lead.phone,
        detail=f"{lead.name}, {lead.city or 'city not given'}, {lead.outlets or '?'} outlets",
        commit=True,
    )
    return {"ok": True}


# ---------- the demo agent's booking page (/demo/:token), no sign-in; the token is the key

class BookIn(BaseModel):
    slot: str = Field(max_length=40)
    mode: str = Field(pattern="^(meet|zoom|teams|in_person|phone)$")


def _meeting(db: Session, token: str) -> tuple[DemoMeeting, Lead]:
    m = db.query(DemoMeeting).filter(DemoMeeting.token == token).one_or_none()
    lead = db.get(Lead, m.lead_id) if m else None
    if m is None or lead is None:
        raise HTTPException(404, "This demo link isn't valid. Ask for a demo on the contact page.")
    return m, lead


@router.get("/demo/{token}")
@limiter.limit("30/minute")
def demo_page(request: Request, token: str, db: Session = Depends(get_db)) -> dict:
    m, lead = _meeting(db, token)
    return agent_team.public_view(m, lead)


@router.post("/demo/{token}/book")
@limiter.limit("10/minute")
def demo_book(request: Request, token: str, body: BookIn, db: Session = Depends(get_db)) -> dict:
    m, lead = _meeting(db, token)
    try:
        agent_team.book(db, m, body.slot, body.mode)
    except agent_team.BookingError as exc:
        raise HTTPException(409, str(exc)) from exc
    return agent_team.public_view(m, lead)


@router.post("/demo/{token}/more")
@limiter.limit("10/minute")
def demo_more(request: Request, token: str, db: Session = Depends(get_db)) -> dict:
    m, lead = _meeting(db, token)
    agent_team.more_times(db, m)
    return agent_team.public_view(m, lead)


@router.post("/demo/{token}/cancel")
@limiter.limit("10/minute")
def demo_cancel(request: Request, token: str, db: Session = Depends(get_db)) -> dict:
    m, lead = _meeting(db, token)
    agent_team.cancel(db, m)
    db.commit()
    return agent_team.public_view(m, lead)
