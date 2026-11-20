"""Plan and billing: see the current plan, pay with Razorpay, receive Razorpay webhooks."""

import json
import logging
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, object_session

from app.auth.deps import OrgContext, get_current_user, get_org_context
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Membership, Organization, Outlet, Payment, Subscription, User, WebhookEvent
from app.services import billing, dodo_billing, pricing, receipts
from app.services.plans import limits_for

logger = logging.getLogger(__name__)
GSTIN = re.compile(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]")

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


def owner_only(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
    """Billing stays open after a trial ends (that's when people need it), but only for owners."""
    if ctx.role != "owner" and not ctx.user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the restaurant owner can manage the plan.")
    return ctx


class OrderIn(BaseModel):
    outlets: int = Field(ge=1, le=pricing.MAX_OUTLETS)
    months: int = 1


class VerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.get("")
def billing_status(ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> dict:
    sub = db.scalar(select(Subscription).where(Subscription.organization_id == ctx.org.id))
    outlets_now = (
        db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == ctx.org.id, Outlet.is_active)) or 1
    )
    payments = db.scalars(
        select(Payment).where(Payment.organization_id == ctx.org.id).order_by(Payment.created_at.desc()).limit(24)
    ).all()
    now = datetime.now(UTC)
    paid_until = sub.current_period_end if sub and sub.status == "active" else None
    if ctx.org.plan == "trial":
        ends = ctx.org.trial_ends_at
    else:
        ends = paid_until
    return {
        "plan": ctx.org.plan,
        "limits": limits_for(ctx.org),
        "paid_outlets": ctx.org.paid_outlets,
        "outlets_now": outlets_now,
        "billing": {
            "company_name": ctx.org.billing_name or ctx.org.name,
            "gstin": ctx.org.gstin,
            "address": ctx.org.billing_address or ctx.org.head_office,
        },
        "ends_at": ends,
        "expired": bool(ends and ends < now),
        "payments_enabled": settings.payments_enabled,
        "provider": settings.PAYMENT_PROVIDER,
        "promo": {"code": settings.PROMO_CODE, "text": settings.PROMO_TEXT} if settings.PROMO_CODE else None,
        "pricing": pricing.table(),
        "payments": [
            {
                "id": p.razorpay_payment_id,
                "receipt_id": p.id,
                "invoice_no": p.invoice_no,
                "months": p.months,
                "outlets": p.outlets,
                "amount": p.amount_paise / 100,
                "status": p.status,
                "paid_at": p.created_at,
            }
            for p in payments
        ],
    }


def _online_or_bank(outlets: int, months: int) -> None:
    """Refuse online checkout above the provider's single-payment limit, with the way forward."""
    try:
        total = pricing.quote(outlets, months).total
    except pricing.PricingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if total > settings.ONLINE_PAYMENT_MAX_INR:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{pricing.inr(total)} is more than one online payment can take "
            f"({pricing.inr(settings.ONLINE_PAYMENT_MAX_INR)}). "
            "Choose Pay by bank transfer: we send a GST invoice and switch the plan on when the money arrives.",
        )


@router.post("/order")
def create_order(body: OrderIn, ctx: OrgContext = Depends(owner_only)) -> dict:
    _online_or_bank(body.outlets, body.months)
    try:
        order = billing.create_order(ctx.org, body.outlets, body.months)
    except billing.BillingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {**order, "restaurant": ctx.org.name, "email": ctx.user.email, "name": ctx.user.full_name}


class CheckoutIn(BaseModel):
    outlets: int = Field(ge=1, le=pricing.MAX_OUTLETS)
    months: int = 1
    company_name: str | None = Field(default=None, max_length=160)
    gstin: str | None = Field(default=None, max_length=15)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, v: str | None) -> str | None:
        v = (v or "").strip().upper()
        if v and not GSTIN.fullmatch(v):
            raise ValueError("That GSTIN doesn't look right. It has 15 characters, like 33ABCDE1234F1Z5.")
        return v or None


@router.post("/checkout")
def dodo_checkout(body: CheckoutIn, ctx: OrgContext = Depends(owner_only)) -> dict:
    """Dodo Payments: returns the hosted checkout page to send the owner to."""
    _online_or_bank(body.outlets, body.months)
    try:
        if body.company_name is not None:
            ctx.org.billing_name = body.company_name.strip() or None
        if body.gstin is not None or body.company_name is not None:
            ctx.org.gstin = body.gstin
        if body.address is not None:
            ctx.org.billing_address = body.address.strip() or None
        object_session(ctx.org).commit()
        url = dodo_billing.start_checkout(ctx.org, ctx.user.email, ctx.user.full_name, body.outlets, body.months)
    except billing.BillingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"checkout_url": url}


class ConfirmIn(BaseModel):
    payment_id: str


@router.post("/confirm")
def dodo_confirm(body: ConfirmIn, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> dict:
    """Dodo Payments: after the owner comes back, check the payment with Dodo and turn the plan on."""
    try:
        state = dodo_billing.confirm_payment(db, ctx.org, body.payment_id)
    except billing.BillingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.refresh(ctx.org)
    return {"status": state, "plan": ctx.org.plan}


@router.post("/dodo-webhook", include_in_schema=False)
async def dodo_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Dodo calls this after a payment. Add it in Dodo > Developer > Webhooks once the site has a public URL."""
    raw = await request.body()
    headers = {k: request.headers.get(k, "") for k in ("webhook-id", "webhook-signature", "webhook-timestamp")}
    try:
        event_type = dodo_billing.handle_webhook(db, raw, headers)
    except billing.BillingError:
        raise
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature") from exc
    first = db.execute(
        insert(WebhookEvent)
        .values(event_id=headers["webhook-id"][:80], event_type=event_type[:80], received_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["event_id"])
    ).rowcount
    db.commit()
    return {"received": True, "duplicate": not first}


@router.post("/verify")
def verify(body: VerifyIn, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> dict:
    try:
        billing.verify_and_activate(
            db, ctx.org, body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
        )
    except billing.BillingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True, "plan": ctx.org.plan}


@router.post("/webhook", include_in_schema=False)
async def webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str = Header(default=""),
    x_razorpay_event_id: str = Header(default=""),
) -> dict:
    """Razorpay calls this after a payment, even if the guest closed the browser. Set it up on a public URL."""
    raw = await request.body()
    if not billing.webhook_signature_ok(raw, x_razorpay_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bad signature")
    event = json.loads(raw)
    event_id = x_razorpay_event_id or f"{event.get('event')}-{event.get('created_at')}"
    first = db.execute(
        insert(WebhookEvent)
        .values(event_id=event_id[:80], event_type=str(event.get("event"))[:80], received_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["event_id"])
    ).rowcount
    db.commit()
    if not first:
        return {"ok": True, "duplicate": True}
    if event.get("event") in ("payment.captured", "order.paid"):
        payment = event["payload"]["payment"]["entity"]
        notes = payment.get("notes") or {}
        if not notes.get("org_id") and payment.get("order_id"):
            notes = billing.fetch_order(payment["order_id"]).get("notes") or {}
        if notes.get("org_id") and notes.get("outlets") and notes.get("months"):
            billing.activate(
                db, int(notes["org_id"]), int(notes["outlets"]), int(notes["months"]), payment["id"], payment["amount"]
            )
    return {"ok": True}


@router.get("/quote")
def get_quote(outlets: int, months: int) -> dict:
    """Price for any number of outlets and months (public: the website calculator uses it too)."""
    try:
        return pricing.quote(outlets, months).as_dict()
    except pricing.PricingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/pricing")
def get_pricing() -> dict:
    """Outlet tiers and duration discounts, so the website shows exactly what checkout will charge."""
    return pricing.table()


@router.get("/receipts")
def my_receipts(ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> list[dict]:
    """Every payment this restaurant made, newest first, with its receipt number."""
    pays = db.scalars(select(Payment).where(Payment.organization_id == ctx.org.id).order_by(Payment.created_at.desc()))
    return [receipts.as_dict(p, ctx.org) for p in pays]


@router.get("/receipts/{payment_id}")
def receipt(payment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """One receipt. Owners see their own restaurant's; the platform admin sees any (for audit)."""
    pay = db.get(Payment, payment_id)
    org = db.get(Organization, pay.organization_id) if pay else None
    if pay is None or org is None:
        raise HTTPException(404, "Receipt not found.")
    if not user.is_superadmin:
        owner = db.scalar(
            select(Membership.id).where(
                Membership.user_id == user.id, Membership.organization_id == org.id, Membership.role == "owner"
            )
        )
        if not owner:
            raise HTTPException(404, "Receipt not found.")
    return receipts.as_dict(pay, org)


class BankTransferIn(CheckoutIn):
    """Big orders (over the online limit): the owner asks for a GST invoice to pay by bank transfer."""


@router.post("/bank-transfer")
@limiter.limit("3/minute")
def bank_transfer(
    request: Request,  # noqa: ARG001
    body: BankTransferIn,
    ctx: OrgContext = Depends(owner_only),
    db: Session = Depends(get_db),
) -> dict:
    """Ask for an invoice. The admin is emailed straight away; the plan starts when the admin records the payment."""
    from app.services import activity
    from app.services.emailer import send_email

    try:
        q = pricing.quote(body.outlets, body.months)
    except pricing.PricingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    org = ctx.org
    if body.company_name is not None:
        org.billing_name = body.company_name.strip() or None
    if body.gstin is not None or body.company_name is not None:
        org.gstin = body.gstin
    if body.address is not None:
        org.billing_address = body.address.strip() or None
    what = f"{q.outlets} outlets × {q.months} months" + (f" + {q.bonus_months} free" if q.bonus_months else "")
    detail = (
        f"{org.name} asks to pay {pricing.inr(q.total)} by bank transfer for {what}.\n"
        f"Bill to: {org.billing_name or org.name}; GSTIN: {org.gstin or 'none'}; "
        f"address: {org.billing_address or '-'}\n"
        f"Owner: {ctx.user.full_name} <{ctx.user.email}>"
    )
    activity.record(db, "bank_transfer_request", org_id=org.id, restaurant=org.name, email=ctx.user.email,
                    detail=detail)
    send_email(
        [settings.notify_email],
        f"Bank transfer request: {org.name}, {pricing.inr(q.total)}",
        detail + f"\n\nSend the GST invoice, then record the payment at {settings.APP_URL}/app/admin/restaurants "
        "(Record bank payment).",
    )
    send_email(
        [ctx.user.email],
        "Your Virundhu invoice is on its way",
        f"Thank you. We've got your request to pay {pricing.inr(q.total)} by bank transfer for {what}.\n\n"
        "You'll get a GST invoice with our bank details within one working day. Your plan switches on as soon as the "
        "money reaches us, and the receipt comes by email.",
        details=[("Outlets", str(q.outlets)), ("Months", str(q.months)), ("Amount", f"{pricing.inr(q.total)}")],
    )
    msg = "Request sent. Your GST invoice arrives by email within one working day."
    return {"ok": True, "total": q.total, "message": msg}
