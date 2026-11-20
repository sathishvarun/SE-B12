"""Plan and billing: see the current plan, pay with Razorpay, receive Razorpay webhooks."""

import io
import json
import logging
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, object_session

from app.auth.deps import OrgContext, get_current_user, get_org_context
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import (
    InvoiceRequest,
    Membership,
    Organization,
    Outlet,
    Payment,
    Refund,
    Subscription,
    User,
    WebhookEvent,
)
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
    from app.services import books, invoice_pdf

    what = f"{q.outlets} outlets × {q.months} months" + (f" + {q.bonus_months} free" if q.bonus_months else "")
    req = books.open_request(db, org, q.outlets, q.months, q.total, ctx.user.email)
    pdf = [(f"{req.number}.pdf", invoice_pdf.proforma(req, org), "application/pdf")]
    detail = (
        f"{org.name} asks to pay {pricing.inr(q.total)} by bank transfer for {what}. Proforma {req.number}.\n"
        f"Bill to: {org.billing_name or org.name}; GSTIN: {org.gstin or 'none'}; "
        f"address: {org.billing_address or '-'}\n"
        f"Owner: {ctx.user.full_name} <{ctx.user.email}>"
    )
    activity.record(
        db, "bank_transfer_request", org_id=org.id, restaurant=org.name, email=ctx.user.email, detail=detail
    )
    send_email(
        [settings.notify_email],
        f"Bank transfer request {req.number}: {org.name}, {pricing.inr(q.total)}",
        detail + "\n\nThe proforma invoice with your bank details is attached and was sent to the owner. When the "
        f"money arrives, record it at {settings.APP_URL}/app/admin/accounts (Waiting for bank transfer).",
        attachments=pdf,
    )
    send_email(
        [ctx.user.email],
        f"Proforma invoice {req.number}: pay {pricing.inr(q.total)} by bank transfer",
        f"Thank you. Your proforma invoice for {what} is attached, with our bank details.\n\n"
        f"Please write {req.number} in the transfer remarks. Your plan switches on as soon as the money reaches us, "
        "and the tax invoice comes by email.",
        details=[
            ("Proforma", req.number or ""),
            ("Outlets", str(q.outlets)),
            ("Months", str(q.months)),
            ("Amount", pricing.inr(q.total)),
        ],
        attachments=pdf,
    )
    msg = f"Proforma invoice {req.number} sent to {ctx.user.email}. You can also download it below."
    return {"ok": True, "total": q.total, "message": msg, "request_id": req.id, "number": req.number}


# ---------- Owner downloads: invoices, proformas, credit notes (PDF) ----------


def _owned_payment(db: Session, ctx: OrgContext, payment_id: int) -> Payment:
    pay = db.get(Payment, payment_id)
    if pay is None or pay.organization_id != ctx.org.id:
        raise HTTPException(404, "Receipt not found.")
    return pay


def _pdf(data: bytes, name: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/receipts/{payment_id}/pdf")
def receipt_pdf(payment_id: int, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)):
    """Tax invoice (bank transfer) or payment receipt (online) as a PDF."""
    from app.services import invoice_pdf

    pay = _owned_payment(db, ctx, payment_id)
    return _pdf(invoice_pdf.invoice(pay, ctx.org), f"{pay.invoice_no or pay.id}.pdf")


@router.get("/credit-notes")
def my_credit_notes(ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Refund)
        .where(Refund.organization_id == ctx.org.id, Refund.credit_note_no.is_not(None))
        .order_by(Refund.refunded_at.desc())
    )
    return [
        {
            "id": r.id,
            "credit_note_no": r.credit_note_no,
            "amount": r.amount_paise / 100,
            "refunded_at": r.refunded_at,
            "reason": r.reason,
        }
        for r in rows
    ]


@router.get("/credit-notes/{refund_id}/pdf")
def credit_note_pdf(refund_id: int, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)):
    from app.services import invoice_pdf

    ref = db.get(Refund, refund_id)
    if ref is None or ref.organization_id != ctx.org.id or not ref.credit_note_no:
        raise HTTPException(404, "Credit note not found.")
    pay = db.scalar(select(Payment).where(Payment.razorpay_payment_id == ref.provider_payment_id))
    return _pdf(invoice_pdf.credit_note(ref, pay, ctx.org), f"{ref.credit_note_no}.pdf")


@router.get("/invoice-requests")
def my_invoice_requests(ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(InvoiceRequest)
        .where(InvoiceRequest.organization_id == ctx.org.id)
        .order_by(InvoiceRequest.id.desc())
        .limit(20)
    )
    return [
        {
            "id": r.id,
            "number": r.number,
            "outlets": r.outlets,
            "months": r.months,
            "amount": r.amount_paise / 100,
            "status": r.status,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/invoice-requests/{req_id}/pdf")
def proforma_pdf(req_id: int, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)):
    from app.services import invoice_pdf

    r = db.get(InvoiceRequest, req_id)
    if r is None or r.organization_id != ctx.org.id:
        raise HTTPException(404, "Proforma invoice not found.")
    return _pdf(invoice_pdf.proforma(r, ctx.org), f"{r.number}.pdf")


@router.get("/receipts.zip")
def receipts_zip(fy: int, ctx: OrgContext = Depends(owner_only), db: Session = Depends(get_db)):
    """Every invoice and credit note of one financial year (April to March) in one ZIP, with a summary sheet."""
    import csv
    import zipfile
    from zoneinfo import ZoneInfo

    from app.services import invoice_pdf

    tz = ZoneInfo("Asia/Kolkata")
    start = datetime(fy, 4, 1, tzinfo=tz).astimezone(UTC)
    end = datetime(fy + 1, 4, 1, tzinfo=tz).astimezone(UTC)
    pays = db.scalars(
        select(Payment)
        .where(
            Payment.organization_id == ctx.org.id,
            Payment.status == "paid",
            Payment.created_at >= start,
            Payment.created_at < end,
        )
        .order_by(Payment.created_at)
    ).all()
    refs = db.scalars(
        select(Refund)
        .where(
            Refund.organization_id == ctx.org.id,
            Refund.credit_note_no.is_not(None),
            Refund.refunded_at >= start,
            Refund.refunded_at < end,
        )
        .order_by(Refund.refunded_at)
    ).all()
    if not pays and not refs:
        raise HTTPException(404, f"No payments in FY {fy}-{str(fy + 1)[2:]}.")
    by_pid = {p.razorpay_payment_id: p for p in pays}
    buf = io.BytesIO()
    summary = io.StringIO()
    w = csv.writer(summary)
    w.writerow(["Document", "Number", "Date", "Outlets", "Months", "Amount (INR, GST included)", "Refunded", "GSTIN"])
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in pays:
            z.writestr(f"invoices/{p.invoice_no or p.id}.pdf", invoice_pdf.invoice(p, ctx.org))
            w.writerow(
                [
                    "Invoice" if p.razorpay_payment_id.startswith("bank_") else "Receipt",
                    p.invoice_no,
                    p.created_at.astimezone(tz).date(),
                    p.outlets,
                    p.months,
                    p.amount_paise / 100,
                    (p.refunded_paise or 0) / 100,
                    p.bill_gstin or "",
                ]
            )
        for r in refs:
            pay = by_pid.get(r.provider_payment_id) or db.scalar(
                select(Payment).where(Payment.razorpay_payment_id == r.provider_payment_id)
            )
            z.writestr(f"credit-notes/{r.credit_note_no}.pdf", invoice_pdf.credit_note(r, pay, ctx.org))
            w.writerow(
                [
                    "Credit note",
                    r.credit_note_no,
                    r.refunded_at.astimezone(tz).date(),
                    "",
                    "",
                    -r.amount_paise / 100,
                    "",
                    "",
                ]
            )
        z.writestr("summary.csv", summary.getvalue())
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="virundhu-receipts-FY{fy}-{str(fy + 1)[2:]}.zip"'},
    )
