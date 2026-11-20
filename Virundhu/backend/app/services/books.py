"""Bookkeeping helpers: credit note numbers, proforma invoice requests, bank refunds, Dodo payouts, monthly report mail.

Every money change also lands in `activity_log`, so the audit trail sheet shows who did what and when.
"""

import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DodoPayout, InvoiceRequest, Organization, Payment, Refund
from app.services import activity

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def ensure_credit_note(db: Session, ref: Refund) -> bool:
    """Give a succeeded refund its credit note number. True when a new number was issued."""
    if ref.status != "succeeded" or ref.credit_note_no:
        return False
    db.flush()
    ref.credit_note_no = f"CN-{ref.refunded_at.astimezone(IST):%Y%m}-{ref.id:05d}"
    return True


def email_credit_note(db: Session, ref: Refund) -> None:
    """Send the owner their credit note as a PDF. Never raises."""
    try:
        from app.services import invoice_pdf, receipts
        from app.services.emailer import send_email

        pay = db.scalar(select(Payment).where(Payment.razorpay_payment_id == ref.provider_payment_id))
        org = db.get(Organization, ref.organization_id) if ref.organization_id else None
        if org is None or ref.is_test:
            return
        pdf = invoice_pdf.credit_note(ref, pay, org)
        to = [u.email for u in receipts.owners(db, org.id)]
        if to:
            send_email(
                to,
                f"Credit note {ref.credit_note_no}: refund of ₹{ref.amount_paise / 100:,.2f}",
                f"Your refund of ₹{ref.amount_paise / 100:,.2f} for {org.name} is done. "
                "The credit note is attached for your records and GST books.",
                attachments=[(f"{ref.credit_note_no}.pdf", pdf, "application/pdf")],
            )
    except Exception:  # pragma: no cover - mail must not break the refund
        logger.exception("Couldn't email credit note %s", ref.credit_note_no)


def open_request(
    db: Session, org: Organization, outlets: int, months: int, amount_inr: int, email: str
) -> InvoiceRequest:
    """Record a proforma invoice request and number it PI-YYYYMM-NNNNN."""
    req = InvoiceRequest(
        organization_id=org.id,
        outlets=outlets,
        months=months,
        amount_paise=amount_inr * 100,
        bill_name=org.billing_name or org.name,
        bill_gstin=org.gstin,
        bill_address=org.billing_address or ", ".join(x for x in (org.head_office, org.city) if x) or None,
        bill_email=email,
    )
    db.add(req)
    db.flush()
    req.number = f"PI-{datetime.now(IST):%Y%m}-{req.id:05d}"
    db.commit()
    return req


def close_requests(db: Session, org_id: int, outlets: int, months: int, payment: Payment | None) -> None:
    """A bank payment arrived: the matching open proforma requests are paid."""
    for r in db.scalars(
        select(InvoiceRequest).where(
            InvoiceRequest.organization_id == org_id,
            InvoiceRequest.status == "open",
            InvoiceRequest.outlets == outlets,
            InvoiceRequest.months == months,
        )
    ):
        r.status, r.payment_id = "paid", payment.id if payment else None


class RefundError(ValueError):
    pass


def bank_refund(db: Session, pay: Payment, amount_inr: int, reference: str, reason: str | None) -> Refund:
    """Money sent back by bank transfer for a bank payment: refund row, credit note, refunded total, audit line."""
    if not pay.razorpay_payment_id.startswith("bank_"):
        raise RefundError("Online payments are refunded in Dodo; they show here by themselves.")
    left = pay.amount_paise - (pay.refunded_paise or 0)
    if amount_inr * 100 > left:
        raise RefundError(f"Only ₹{left / 100:,.2f} of this payment is left to refund.")
    rid = f"bankref_{reference}"
    if db.scalar(select(Refund.id).where(Refund.refund_id == rid)):
        raise RefundError("This bank reference was already recorded as a refund.")
    ref = Refund(
        refund_id=rid,
        provider_payment_id=pay.razorpay_payment_id,
        organization_id=pay.organization_id,
        amount_paise=amount_inr * 100,
        status="succeeded",
        reason=(reason or "Refund")[:300],
        is_test=pay.is_test,
        refunded_at=datetime.now(UTC),
    )
    db.add(ref)
    db.flush()
    ensure_credit_note(db, ref)
    pay.refunded_paise = (
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
                Refund.provider_payment_id == pay.razorpay_payment_id, Refund.status == "succeeded"
            )
        )
        or 0
    )
    org = db.get(Organization, pay.organization_id)
    activity.record(
        db,
        "refund",
        org_id=pay.organization_id,
        restaurant=org.name if org else None,
        detail=f"Bank refund ₹{amount_inr:,} on {pay.invoice_no} ({ref.credit_note_no}), ref {reference}",
        commit=False,
    )
    db.commit()
    email_credit_note(db, ref)
    return ref


def sync_dodo(db: Session) -> dict[str, int]:
    """Pull Dodo's tax and settlement for each live online payment, and every payout with its fee and tax."""
    from app.services.dodo_billing import _client

    client = _client()
    updated = 0
    for pay in db.scalars(
        select(Payment)
        .where(
            Payment.status == "paid",
            Payment.is_test.is_(False),
            Payment.settlement_paise.is_(None),
            ~Payment.razorpay_payment_id.like("bank_%"),
        )
        .limit(200)
    ):
        try:
            p = client.payments.retrieve(pay.razorpay_payment_id)
        except Exception:  # noqa: BLE001 - a payment Dodo doesn't know (e.g. from Razorpay days) is skipped
            logger.info("Dodo has no payment %s; skipped", pay.razorpay_payment_id)
            continue
        pay.provider_tax_paise = getattr(p, "tax", None)
        pay.settlement_paise = getattr(p, "settlement_amount", None)
        cur = getattr(p, "settlement_currency", None)
        pay.settlement_currency = str(getattr(cur, "value", cur) or "")[:3] or None
        updated += 1
    payouts = 0
    try:
        page = client.payouts.list(page_size=100)
        for po in getattr(page, "items", None) or list(page):
            row = db.scalar(select(DodoPayout).where(DodoPayout.payout_id == po.payout_id))
            if row is None:
                row = DodoPayout(payout_id=po.payout_id, paid_at=po.created_at, status="", amount_paise=0)
                db.add(row)
                payouts += 1
            status = getattr(po.status, "value", po.status)
            cur = getattr(po.currency, "value", po.currency)
            row.amount_paise, row.fee_paise, row.tax_paise = po.amount, po.fee or 0, po.tax or 0
            row.refunds_paise, row.chargebacks_paise = po.refunds or 0, po.chargebacks or 0
            row.currency, row.status, row.remarks = str(cur)[:3], str(status)[:20], (po.remarks or None)
            row.document_url, row.paid_at = po.payout_document_url, po.created_at
    except Exception:  # noqa: BLE001 - payouts are best effort; payments above are still saved
        logger.exception("Couldn't read Dodo payouts")
    db.commit()
    return {"payments_updated": updated, "new_payouts": payouts}


def recipients() -> list[str]:
    raw = settings.ACCOUNTS_REPORT_EMAILS or settings.notify_email
    return [e.strip() for e in raw.split(",") if "@" in e]


def last_month(today: date | None = None) -> str:
    t = today or datetime.now(IST).date()
    y, m = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
    return f"{y}-{m:02d}"


def email_month(db: Session, period: str | None = None) -> dict:
    """Email the accounts Excel for a month (default: last month) to the accountant list."""
    from app.routers.admin_accounts import _summary, build_workbook
    from app.services.emailer import send_email

    period = period or last_month()
    s = _summary(db, period)[0]
    data = build_workbook(db, period)
    to = recipients()
    send_email(
        to,
        f"Virundhu accounts: {s.label}",
        f"The accounts file for {s.label} is attached.\n\nInvoices: {s.invoices}\nGross received: ₹{s.gross:,.2f}\n"
        f"Refunded: ₹{s.refunded:,.2f}\nNet: ₹{s.net:,.2f}\nGST on direct sales: CGST ₹{s.direct_cgst:,.2f}, "
        f"SGST ₹{s.direct_sgst:,.2f}, IGST ₹{s.direct_igst:,.2f}\n\nThe Summary sheet explains every figure.",
        attachments=[
            (
                f"virundhu-accounts-{period}.xlsx",
                data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        ],
    )
    activity.record(db, "accounts_report", detail=f"Accounts for {s.label} emailed to {', '.join(to)}")
    return {"period": period, "to": to}
