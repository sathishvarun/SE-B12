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
    return event.type
