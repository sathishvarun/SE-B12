"""Quick help chat (website and app), hand-over to a person, and AI-drafted support replies for the admin."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_superadmin
from app.database import get_db
from app.limiter import limiter
from app.models import Lead, SupportTicket, TicketMessage
from app.routers.support import CATEGORIES, number
from app.services import activity, help_bot
from app.services.emailer import send_email

router = APIRouter(prefix="/api/v1", tags=["help"])


class Turn(BaseModel):
    from_: str = Field(alias="from", pattern="^(user|bot)$")
    text: str = Field(max_length=2000)


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    history: list[Turn] = Field(default_factory=list, max_length=12)


@router.post("/help/ask")
@limiter.limit("20/minute")
def ask(request: Request, body: AskIn, db: Session = Depends(get_db)) -> dict:  # noqa: ARG001
    """Answer from the help guide. covered=false means: offer 'Talk to a person'."""
    res = help_bot.ask(body.question, [{"from": t.from_, "text": t.text} for t in body.history])
    if not res.covered:  # the guide lacks this: keep it so the guide can be improved
        activity.record(db, "help_question", detail=f"Not in the guide: {body.question[:500]}")
    return res.model_dump()


def transcript(history: list[Turn]) -> str:
    return "\n".join(("Guest: " if t.from_ == "user" else "Quick help: ") + t.text[:600] for t in history[-12:])


class AppHandover(BaseModel):
    message: str = Field(min_length=3, max_length=3000)
    topic: str = Field(default="other", pattern="^(payment|bug|account|feature|other)$")
    history: list[Turn] = Field(default_factory=list, max_length=12)


@router.post("/help/handover", status_code=201)
def handover(body: AppHandover, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Signed-in owner: turn the chat into a support ticket (with the chat attached) and notify the admin."""
    t = SupportTicket(
        organization_id=ctx.org.id,
        restaurant=ctx.org.name,
        user_id=ctx.user.id,
        user_email=ctx.user.email,
        category=body.topic,
        subject=body.message.strip()[:150],
    )
    db.add(t)
    db.flush()
    chat = transcript(body.history)
    db.add(
        TicketMessage(
            ticket_id=t.id,
            author_email=ctx.user.email,
            body=body.message.strip() + (f"\n\n--- Quick help chat ---\n{chat}" if chat else ""),
        )
    )
    db.commit()
    activity.record(
        db,
        "support_ticket",
        org_id=ctx.org.id,
        restaurant=ctx.org.name,
        email=ctx.user.email,
        detail=f"{number(t)} [{CATEGORIES[t.category]}] from Quick help: {body.message.strip()[:1200]}",
    )
    send_email(
        [ctx.user.email],
        f"We've got your request {number(t)}",
        f"Thank you. A person will reply to {number(t)} within 24 hours.\n\nTrack it in Help and support.\n\n"
        "- Virundhu support",
    )
    return {"number": number(t), "id": t.id}


class WebsiteHandover(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    restaurant: str | None = Field(default=None, max_length=120)
    message: str = Field(min_length=3, max_length=1800)
    history: list[Turn] = Field(default_factory=list, max_length=12)


@router.post("/help/contact", status_code=201)
@limiter.limit("5/minute")
def website_contact(request: Request, body: WebsiteHandover, db: Session = Depends(get_db)) -> dict:  # noqa: ARG001
    """Website visitor (not signed in): save as a contact request and notify the admin."""
    chat = transcript(body.history)
    msg = (body.message.strip() + (f"\n\n--- Quick help chat ---\n{chat}" if chat else ""))[:2000]
    lead = Lead(
        name=body.name.strip(),
        restaurant=(body.restaurant or "Website visitor").strip(),
        phone=body.phone,
        email=str(body.email),
        message=msg,
    )
    db.add(lead)
    db.commit()
    activity.record(
        db,
        "support_ticket",
        restaurant=lead.restaurant,
        email=str(body.email),
        detail=f"Website Quick help: {body.message.strip()[:1200]}",
    )
    send_email(
        [str(body.email)],
        "We've got your message",
        "Thank you for contacting Virundhu. A person will reply within 24 hours.\n\n- Virundhu",
    )
    return {"ok": True}


@router.get("/admin/tickets/{ticket_id}/draft", dependencies=[Depends(require_superadmin)])
def draft(ticket_id: int, db: Session = Depends(get_db)) -> dict:
    """AI-written reply suggestion for the admin, from the help guide and the conversation."""
    t = db.get(SupportTicket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found.")
    msgs = db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == t.id).order_by(TicketMessage.id))
    try:
        text = help_bot.draft_reply(t.subject, [(m.from_admin, m.body) for m in msgs], t.restaurant)
    except Exception as exc:  # AI down
        raise HTTPException(503, "The AI couldn't write a draft just now. Please write the reply yourself.") from exc
    return {"draft": text}
