"""Numbered payment receipts: billing details are copied onto the payment when it lands, then emailed to the owner.

Dodo Payments is the merchant of record and also emails its own tax invoice. This receipt is Virundhu's record of what
was bought (outlets, months, dates covered) with the customer's company name, GSTIN and address, for both sides' audit.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Membership, Organization, Payment, User
from app.services.emailer import send_email

logger = logging.getLogger(__name__)


def owners(db: Session, org_id: int) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.organization_id == org_id, Membership.role == "owner", User.is_active)
        )
    )


def finalise(db: Session, pay: Payment, org: Organization) -> None:
    """Give the payment its invoice number and a copy of the billing details as they are today."""
    tz = ZoneInfo(settings.TIMEZONE)
    when = (pay.created_at or datetime.now(tz)).astimezone(tz)
    db.flush()
    pay.invoice_no = pay.invoice_no or f"VR-{when:%Y%m}-{pay.id:05d}"
    pay.bill_name = org.billing_name or org.name
    pay.bill_gstin = org.gstin
    pay.bill_address = org.billing_address or ", ".join(x for x in (org.head_office, org.city) if x) or None
    first = next(iter(owners(db, org.id)), None)
    pay.bill_email = first.email if first else None


def as_dict(pay: Payment, org: Organization) -> dict:
    tz = ZoneInfo(settings.TIMEZONE)
    return {
        "id": pay.id,
        "invoice_no": pay.invoice_no,
        "paid_at": pay.created_at,
        "restaurant": org.name,
        "bill_name": pay.bill_name or org.name,
        "bill_gstin": pay.bill_gstin,
        "bill_address": pay.bill_address,
        "bill_email": pay.bill_email,
        "outlets": pay.outlets,
        "months": pay.months,
        "period_start": pay.period_start.astimezone(tz).date() if pay.period_start else None,
        "period_end": pay.period_end.astimezone(tz).date() if pay.period_end else None,
        "amount": pay.amount_paise / 100,
        "currency": pay.currency,
        "payment_id": pay.razorpay_payment_id,
        "status": pay.status,
        "seller": {
            "name": settings.COMPANY_NAME,
            "email": settings.CONTACT_EMAIL,
            "address": settings.COMPANY_ADDRESS,
            "parent": settings.PARENT_COMPANY or None,
            "gstin": settings.PARENT_GSTIN or None,
        },
    }


def receipt_email(pay: Payment, org: Organization, first: str = "there") -> tuple[str, str, list[tuple[str, str]]]:
    """(subject, text, details table) for the payment confirmation."""
    r = as_dict(pay, org)
    tz = ZoneInfo(settings.TIMEZONE)
    paid = (pay.created_at or datetime.now(tz)).astimezone(tz)
    months = r["months"] or 1
    added = "1 month" if months == 1 else f"{months} months"
    outlets = r["outlets"] or 1
    link = f"{settings.APP_URL}/app/receipt/{pay.id}"
    details = [
        ("Invoice number", r["invoice_no"] or "-"),
        ("Restaurant", org.name),
        ("Billed to", r["bill_name"]),
        *([("GSTIN", r["bill_gstin"])] if r["bill_gstin"] else []),
        *([("Address", r["bill_address"])] if r["bill_address"] else []),
        ("Months added", added),
        ("Outlets covered", f"{outlets} outlet" + ("" if outlets == 1 else "s")),
        *(
            [("Plan valid", f"{r['period_start']:%d %b %Y} to {r['period_end']:%d %b %Y}")]
            if r["period_start"] and r["period_end"]
            else []
        ),
        ("Amount paid", f"Rs {r['amount']:,.2f}"),
        ("Taxes (GST)", "Included in the amount"),
        ("Paid on", f"{paid:%d %b %Y, %I:%M %p}"),
        ("Payment ID", r["payment_id"] or "-"),
        ("Status", "Paid"),
    ]
    text = (
        f"Hi {first},\n\nThank you! Your payment is received and {added} {'has' if months == 1 else 'have'} been added "
        f"to {org.name} for {outlets} outlet{'' if outlets == 1 else 's'}. Everything is switched on.\n\n"
        f"View, print or download this receipt:\n\n{link}\n\n"
        "Dodo Payments, our payment partner, also emails you the GST tax invoice for this payment."
    )
    return f"Payment received: {r['invoice_no']} ({added} added)", text, details


def email_receipt(db: Session, pay: Payment, org: Organization) -> None:
    for u in owners(db, org.id):
        first = (u.full_name or "").split(" ")[0] or "there"
        subject, text, details = receipt_email(pay, org, first)
        send_email([u.email], subject, text, details=details)
