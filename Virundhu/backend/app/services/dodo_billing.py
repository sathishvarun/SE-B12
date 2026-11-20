"""Dodo Payments (Merchant of Record): hosted checkout, then the plan is turned on from Dodo's own records.

Flow
1. start_checkout: the server works out the price from outlets + months (services/pricing.py) and opens a checkout
   for one "pay what you want" product with that exact amount. The browser never sends a price.
2. The owner pays on Dodo's page (UPI, cards). Dodo sends them back to /app/billing?payment_id=...
3. confirm_payment: the server reads that payment from Dodo's API. Only a "succeeded" payment whose
   metadata names this restaurant turns the plan on. The return URL itself is never trusted.
4. The webhook does the same activation (needed once the site is public), deduplicated by webhook-id.
"""

import logging
from typing import Literal

from dodopayments import DodoPayments

from app.config import settings
from app.models import Organization
from app.services import billing

logger = logging.getLogger(__name__)


def _client() -> DodoPayments:
    env: Literal["live_mode", "test_mode"] = (
        "live_mode" if settings.DODO_PAYMENTS_ENVIRONMENT == "live_mode" else "test_mode"
    )
    return DodoPayments(
        bearer_token=settings.DODO_PAYMENTS_API_KEY,
        webhook_key=settings.DODO_PAYMENTS_WEBHOOK_KEY or None,
        environment=env,
    )


def _address(org: Organization) -> dict:
    """Billing address for Dodo's checkout and tax invoice, from what the owner typed (country is always India)."""
    import re

    addr: dict = {"country": "IN"}
    text = org.billing_address or ""
    pin = re.search(r"\b(\d{6})\b", text)
    if text:
        addr["street"] = text[:200]
    if org.city:
        addr["city"] = org.city
    if pin:
        addr["zipcode"] = pin.group(1)
    return addr


def start_checkout(org: Organization, email: str, name: str, outlets: int, months: int) -> str:
    """Create a one-time Dodo checkout for this many outlets and months. Returns the checkout page URL."""
    if not settings.payments_enabled:
        raise billing.BillingError("Online payment isn't switched on yet. Please contact Virundhu.")
    q = billing.quote_or_error(outlets, months)
    try:
        session = _client().checkout_sessions.create(
            product_cart=[{"product_id": settings.DODO_PRODUCT_FLEX, "quantity": 1, "amount": q.total * 100}],
            customer={"email": email, "name": org.billing_name or name or org.name},
            billing_address=_address(org),
            billing_currency="INR",
            metadata={
                "org_id": str(org.id),
                "outlets": str(outlets),
                "months": str(months),
                "quote": str(q.total),
                "company": (org.billing_name or org.name)[:100],
                "gstin": org.gstin or "",
            },
            feature_flags={"allow_discount_code": True},  # e.g. FIRST10, set up in the Dodo dashboard
            return_url=f"{settings.APP_URL}/app/billing",
        )
    except billing.BillingError:
        raise
    except Exception as exc:  # the SDK raises its own error types
        logger.warning("Dodo checkout failed: %s", exc)
        raise billing.BillingError(
            "Dodo Payments didn't accept the request. Check the API key and product IDs in .env."
        ) from exc
    if not session.checkout_url:
        raise billing.BillingError("Dodo didn't return a checkout page. Please try again.")
    return session.checkout_url


def _activate_from_payment(db, payment, expected_org_id: int | None = None) -> bool:
    meta = payment.metadata or {}
    if str(getattr(payment.status, "value", payment.status)) != "succeeded":
        return False
    if not meta.get("org_id") or not meta.get("outlets") or not meta.get("months"):
        return False
    if expected_org_id is not None and str(expected_org_id) != str(meta["org_id"]):
        raise billing.BillingError("This payment belongs to a different restaurant.")
    return billing.activate(
        db,
        int(meta["org_id"]),
        int(meta["outlets"]),
        int(meta["months"]),
        payment.payment_id,
        int(payment.total_amount or 0),
    )


def confirm_payment(db, org: Organization, payment_id: str) -> str:
    """Read the payment from Dodo and turn the plan on if it succeeded. Returns the payment status."""
    try:
        payment = _client().payments.retrieve(payment_id)
    except Exception as exc:
        raise billing.BillingError("Couldn't confirm the payment with Dodo. Please refresh in a minute.") from exc
    _activate_from_payment(db, payment, expected_org_id=org.id)
    return str(getattr(payment.status, "value", payment.status) or "unknown")


def handle_webhook(db, raw_body: bytes, headers: dict[str, str]) -> str:
    """Verify a Dodo webhook (Standard Webhooks signature) and activate on payment.succeeded."""
    event = _client().webhooks.unwrap(raw_body.decode("utf-8"), headers=headers)
    if event.type == "payment.succeeded":
        payment = _client().payments.retrieve(event.data.payment_id)  # read the full record, metadata included
        _activate_from_payment(db, payment)
    elif event.type.startswith("refund."):
        record_refund(db, event.data)
    return event.type


def record_refund(db, refund) -> bool:
    """Save (or update) one Dodo refund and keep the payment's refunded total right. Safe to call twice."""
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from app.models import Payment, Refund
    from app.services import activity
    from app.services.billing import payments_in_test_mode

    rid = getattr(refund, "refund_id", None)
    pid = getattr(refund, "payment_id", None)
    if not rid or not pid:
        return False
    status = str(getattr(getattr(refund, "status", ""), "value", getattr(refund, "status", ""))).lower()
    amount = int(getattr(refund, "amount", 0) or 0)
    when = getattr(refund, "created_at", None) or datetime.now(UTC)
    pay = db.scalar(select(Payment).where(Payment.razorpay_payment_id == pid))
    row = db.scalar(select(Refund).where(Refund.refund_id == rid))
    is_new = row is None
    if row is None:
        row = Refund(refund_id=rid, provider_payment_id=pid, amount_paise=amount, status=status or "pending",
                     refunded_at=when, organization_id=pay.organization_id if pay else None,
                     is_test=pay.is_test if pay else payments_in_test_mode())
        db.add(row)
    row.status, row.amount_paise = status or row.status, amount or row.amount_paise
    row.reason = (getattr(refund, "reason", None) or row.reason or None)
    db.flush()
    if pay:
        pay.refunded_paise = db.scalar(select(func.coalesce(func.sum(Refund.amount_paise), 0)).where(
            Refund.provider_payment_id == pid, Refund.status == "succeeded")) or 0
    if is_new and row.status == "succeeded":
        activity.record(db, "refund", detail=f"Refund of Rs {amount / 100:,.0f} on payment {pid}")
    db.commit()
    return is_new


def sync_refunds(db) -> int:
    """Pull every refund from Dodo (last 200) so the money page is right even if a webhook was missed."""
    client = _client()
    page = client.refunds.list(page_size=100)
    items = list(getattr(page, "items", None) or page)
    return sum(1 for r in items[:200] if record_refund(db, r))
