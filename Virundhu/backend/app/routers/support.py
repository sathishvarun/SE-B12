"""Support tickets: owners raise issues (payment, bug, account...), the admin replies and resolves. Every step is
recorded in the activity log and emailed, so nothing gets lost."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_superadmin
from app.config import settings
from app.database import get_db
from app.models import Payment, SupportTicket, TicketMessage, User
from app.services import activity
from app.services.emailer import send_email

router = APIRouter(prefix="/api/v1", tags=["support"])
CATEGORIES = {
    "payment": "Payment or billing",
    "bug": "Something isn't working",
    "account": "Account or sign-in",
    "feature": "Suggestion",
    "other": "Other",
}
STATUSES = {"open": "Open", "in_progress": "Being worked on", "resolved": "Resolved"}


def number(t: SupportTicket) -> str:
    return f"VT-{t.id:05d}"


class NewTicket(BaseModel):
    category: str = Field(pattern="^(payment|bug|account|feature|other)$")
    subject: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=5, max_length=5000)
    payment_id: int | None = None


class Reply(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    status: str | None = Field(default=None, pattern="^(open|in_progress|resolved)$")


def _out(db: Session, t: SupportTicket, with_messages: bool = False) -> dict:
    out = {
        "id": t.id,
        "number": number(t),
        "category": t.category,
        "category_label": CATEGORIES.get(t.category),
        "subject": t.subject,
        "status": t.status,
        "status_label": STATUSES.get(t.status),
        "restaurant": t.restaurant,
        "user_email": t.user_email,
        "payment_id": t.payment_id,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "resolved_at": t.resolved_at,
    }
    if with_messages:
        msgs = db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == t.id).order_by(TicketMessage.id))
        out["messages"] = [
            {
                "from_admin": m.from_admin,
                "author": "Virundhu support" if m.from_admin else m.author_email,
                "body": m.body,
                "at": m.created_at,
            }
            for m in msgs
        ]
    return out


@router.post("/support/tickets", status_code=201)
def create(body: NewTicket, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    if body.payment_id:
        pay = db.get(Payment, body.payment_id)
        if pay is None or pay.organization_id != ctx.org.id:
            raise HTTPException(404, "That payment isn't on this account.")
    t = SupportTicket(
        organization_id=ctx.org.id,
        restaurant=ctx.org.name,
        user_id=ctx.user.id,
        user_email=ctx.user.email,
        category=body.category,
        subject=body.subject.strip(),
        payment_id=body.payment_id,
    )
    db.add(t)
    db.flush()
    db.add(TicketMessage(ticket_id=t.id, author_email=ctx.user.email, body=body.message.strip()))
    db.commit()
    activity.record(
        db,
        "support_ticket",
        org_id=ctx.org.id,
        restaurant=ctx.org.name,
        email=ctx.user.email,
        detail=f"{number(t)} [{CATEGORIES[t.category]}] {t.subject}\n\n{body.message.strip()[:1500]}",
    )
    send_email(
        [ctx.user.email],
        f"We've got your request {number(t)}: {t.subject}",
        f"Thank you. Your request {number(t)} is logged and we'll reply within 24 hours.\n\n"
        f"Track it here: {settings.APP_URL}/app/support\n\n- Virundhu support",
    )
    return _out(db, t, True)


@router.get("/support/tickets")
def mine(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(SupportTicket)
        .where(SupportTicket.organization_id == ctx.org.id)
        .order_by(SupportTicket.updated_at.desc())
    )
    return [_out(db, t) for t in rows]


def _own_ticket(db: Session, ctx: OrgContext, ticket_id: int) -> SupportTicket:
    t = db.get(SupportTicket, ticket_id)
    if t is None or t.organization_id != ctx.org.id:
        raise HTTPException(404, "Ticket not found.")
    return t


@router.get("/support/tickets/{ticket_id}")
def one(ticket_id: int, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    return _out(db, _own_ticket(db, ctx, ticket_id), True)


@router.post("/support/tickets/{ticket_id}/messages")
def owner_reply(
    ticket_id: int, body: Reply, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> dict:
    t = _own_ticket(db, ctx, ticket_id)
    db.add(TicketMessage(ticket_id=t.id, author_email=ctx.user.email, body=body.message.strip()))
    if t.status == "resolved":
        t.status, t.resolved_at = "open", None  # a new message reopens it
    t.updated_at = datetime.now(UTC)
    db.commit()
    activity.record(
        db,
        "ticket_reply",
        org_id=ctx.org.id,
        restaurant=ctx.org.name,
        email=ctx.user.email,
        detail=f"{number(t)}: {body.message.strip()[:300]}",
    )
    send_email(
        [settings.notify_email],
        f"Customer replied on {number(t)}: {t.subject}",
        f"{t.restaurant} ({t.user_email}) wrote:\n\n{body.message.strip()}\n\n{settings.APP_URL}/app/admin",
    )
    return _out(db, t, True)


# ---------- admin ----------


@router.get("/admin/tickets", dependencies=[Depends(require_superadmin)])
def all_tickets(status: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    q = select(SupportTicket).order_by(SupportTicket.updated_at.desc())
    if status:
        q = q.where(SupportTicket.status == status)
    return [_out(db, t) for t in db.scalars(q)]


@router.get("/admin/tickets/{ticket_id}", dependencies=[Depends(require_superadmin)])
def admin_one(ticket_id: int, db: Session = Depends(get_db)) -> dict:
    t = db.get(SupportTicket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found.")
    out = _out(db, t, True)
    if t.payment_id:
        p = db.get(Payment, t.payment_id)
        out["payment"] = (
            {
                "invoice_no": p.invoice_no,
                "amount": p.amount_paise / 100,
                "status": p.status,
                "payment_id": p.razorpay_payment_id,
                "paid_at": p.created_at,
            }
            if p
            else None
        )
    return out


@router.post("/admin/tickets/{ticket_id}/messages")
def admin_reply(
    ticket_id: int, body: Reply, admin: User = Depends(require_superadmin), db: Session = Depends(get_db)
) -> dict:
    t = db.get(SupportTicket, ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found.")
    db.add(TicketMessage(ticket_id=t.id, from_admin=True, author_email=admin.email, body=body.message.strip()))
    if body.status:
        t.status = body.status
        t.resolved_at = datetime.now(UTC) if body.status == "resolved" else None
    elif t.status == "open":
        t.status = "in_progress"
    t.updated_at = datetime.now(UTC)
    db.commit()
    activity.record(
        db,
        "ticket_reply",
        org_id=t.organization_id,
        restaurant=t.restaurant,
        email=admin.email,
        detail=f"Admin on {number(t)} ({STATUSES[t.status]}): {body.message.strip()[:300]}",
    )
    if t.user_email:
        send_email(
            [t.user_email],
            f"Reply on {number(t)}: {t.subject} ({STATUSES[t.status]})",
            f"{body.message.strip()}\n\nSee the whole conversation: {settings.APP_URL}/app/support\n\n"
            "- Virundhu support",
        )
    return _out(db, t, True)
