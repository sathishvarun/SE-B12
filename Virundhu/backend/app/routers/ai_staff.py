"""AI staff: the agents' work, today's moves, crisis radar, guest win-back and the owner's rules."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_writable
from app.database import get_db
from app.services import ai_staff

router = APIRouter(prefix="/api/v1/ai-staff", tags=["ai-staff"])


@router.get("")
def command_center(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Everything the AI staff did in the last 30 days, and what needs the owner today."""
    return ai_staff.command_center(db, ctx)


class RulesIn(BaseModel):
    banned_words: list[str] = Field(default_factory=list, max_length=30)
    escalate: list[str] = Field(default_factory=list, max_length=8)
    avg_order_value: int = Field(default=400, ge=50, le=20000)
    comeback_offer: str = Field(default="10% off your next visit", min_length=3, max_length=80)


@router.put("/rules")
def save_rules(body: RulesIn, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)) -> dict:
    """The owner's rules for the AI staff (what never goes in a reply, what always waits for a person)."""
    allowed = {"food_quality", "delivery", "price", "staff", "packaging", "hygiene", "app", "other"}
    ctx.org.ai_rules = {
        "banned_words": [w.strip()[:40] for w in body.banned_words if w.strip()],
        "escalate": [c for c in body.escalate if c in allowed],
        "avg_order_value": body.avg_order_value,
        "comeback_offer": body.comeback_offer.strip(),
    }
    db.commit()
    return ai_staff.rules(ctx.org)


@router.post("/recovery/{review_id}")
def draft_recovery(review_id: int, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)) -> dict:
    """Win-back: draft an apology with a comeback code for an unhappy guest who left a contact."""
    try:
        g = ai_staff.draft_recovery(db, ctx, review_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"code": g.code, "message": g.message, "status": g.status}


class MarkIn(BaseModel):
    status: str = Field(pattern="^(sent|returned)$")


@router.post("/recovery/{review_id}/status")
def mark_recovery(
    review_id: int, body: MarkIn, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)
) -> dict:
    """Mark the message sent, or the guest as came back (counts as revenue won back)."""
    try:
        g = ai_staff.mark(db, ctx, review_id, body.status)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"status": g.status}
