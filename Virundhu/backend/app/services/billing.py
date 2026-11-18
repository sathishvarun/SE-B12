"""Razorpay payments: one order per payment, plan activated after the signature is checked.

Flow
1. create_order: the server works out the amount with services/pricing.py (never trusts the browser) and asks
   Razorpay for an order.
2. The browser opens Razorpay Checkout with that order. The guest pays.
3. verify_and_activate: the server checks Razorpay's signature, then turns the plan on.
4. The webhook does the same activation, in case the browser closed before step 3. Both are idempotent.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Organization, Payment, Subscription
from app.services import activity, pricing, receipts

logger = logging.getLogger(__name__)

RAZORPAY_API = "https://api.razorpay.com/v1"

# A launch code like FIRST10 may lower the price on the payment page. A payment is accepted only if it is at least
# this share of the quoted price, so nobody can pay ₹1 for a year.
MIN_SHARE_OF_QUOTE = (100 - settings.PROMO_MAX_DISCOUNT_PCT) / 100


class BillingError(ValueError):
    """A payment problem the user can act on."""


def quote_or_error(outlets: int, months: int) -> pricing.Quote:
    try:
        return pricing.quote(outlets, months)
    except pricing.PricingError as exc:
        raise BillingError(str(exc)) from exc


def _auth() -> tuple[str, str]:
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


def create_order(org: Organization, outlets: int, months: int) -> dict:
    """Ask Razorpay for an order. Returns what Razorpay Checkout needs."""
    if not settings.payments_enabled:
        raise BillingError("Online payment isn't switched on yet. Please contact Virundhu.")
    q = quote_or_error(outlets, months)
    amount = q.total * 100
    body = {
        "amount": amount,
        "currency": "INR",
        "receipt": f"org{org.id}-{outlets}o-{months}m-{int(datetime.now(UTC).timestamp())}"[:40],
        "notes": {"org_id": str(org.id), "outlets": str(outlets), "months": str(months)},
    }
    try:
        res = httpx.post(f"{RAZORPAY_API}/orders", json=body, auth=_auth(), timeout=20)
    except httpx.HTTPError as exc:
        raise BillingError("Couldn't reach Razorpay. Please try again in a minute.") from exc
    if res.status_code == 401:
        raise BillingError("The Razorpay keys in .env are wrong. Check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    if res.status_code >= 400:
        logger.warning("Razorpay order failed %s: %s", res.status_code, res.text[:300])
        raise BillingError("Razorpay didn't accept the order. Please try again.")
    order = res.json()
    return {"order_id": order["id"], "amount": amount, "currency": "INR", "key_id": settings.RAZORPAY_KEY_ID}


def signature_ok(order_id: str, payment_id: str, signature: str) -> bool:
    """Razorpay Checkout signature: HMAC-SHA256 of 'order_id|payment_id' with the key secret."""
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def webhook_signature_ok(raw_body: bytes, signature: str) -> bool:
    """Webhook signature: HMAC-SHA256 of the raw body with the webhook secret."""
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def fetch_order(order_id: str) -> dict:
    res = httpx.get(f"{RAZORPAY_API}/orders/{order_id}", auth=_auth(), timeout=20)
    if res.status_code >= 400:
        raise BillingError("Couldn't confirm the order with Razorpay.")
    return res.json()


def activate(db: Session, org_id: int, outlets: int, months: int, payment_id: str, amount_paid: int) -> bool:
    """Record the payment and extend the plan. Returns False if this payment was already counted or is too small.

    The price is worked out again here from outlets + months, so a tampered amount never buys more than was paid for.
    """
    q = quote_or_error(outlets, months)
    if amount_paid < q.total * 100 * MIN_SHARE_OF_QUOTE - 100:
        logger.warning("Payment %s for org %s is below the quote (%s < %s)", payment_id, org_id, amount_paid, q.total)
        return False
    inserted = db.execute(
        insert(Payment)
        .values(
            organization_id=org_id,
            razorpay_payment_id=payment_id,
            amount_paise=amount_paid,
            currency="INR",
            status="paid",
            outlets=outlets,
            months=months,
        )
        .on_conflict_do_nothing(index_elements=["razorpay_payment_id"])
    ).rowcount
    if not inserted:
        db.rollback()
        return False
    org = db.get(Organization, org_id)
    sub = db.scalar(select(Subscription).where(Subscription.organization_id == org_id))
    if sub is None:
        sub = Subscription(organization_id=org_id, plan=q.plan, status="active")
        db.add(sub)
    now = datetime.now(UTC)
    # Renewing a paid plan early adds to its end date; paying during a trial starts the plan today.
    renewing = (
        sub.status == "active" and sub.plan != "trial" and sub.current_period_end and sub.current_period_end > now
    )
    start = sub.current_period_end if renewing else now
    sub.plan, sub.status = q.plan, "active"
    sub.current_period_end = start + timedelta(days=q.access_days)
    pay = db.scalar(select(Payment).where(Payment.razorpay_payment_id == payment_id))
    if pay is not None:
        pay.period_start, pay.period_end = start, sub.current_period_end
        if org is not None:
            receipts.finalise(db, pay, org)
    if org is not None:
        org.plan, org.paid_outlets = q.plan, outlets
        activity.record(
            db,
            "payment",
            org_id=org_id,
            restaurant=org.name,
            detail=f"₹{amount_paid / 100:,.0f} for {outlets} outlet(s), {months} month(s)"
            + (f" + {q.bonus_months} free" if q.bonus_months else ""),
            commit=False,
        )
    db.commit()
    logger.info("Payment %s: org %s now on %s until %s", payment_id, org_id, q.plan, sub.current_period_end)
    if pay is not None and org is not None:
        try:
            receipts.email_receipt(db, pay, org)
        except Exception:  # the payment is safe even if the email fails
            logger.exception("Receipt email failed for payment %s", payment_id)
    return True


def _note_int(notes: dict, key: str) -> int:
    try:
        return int(notes.get(key, 0))
    except (TypeError, ValueError):
        return 0


def verify_and_activate(db: Session, org: Organization, order_id: str, payment_id: str, signature: str) -> None:
    """Called by the browser right after payment."""
    if not signature_ok(order_id, payment_id, signature):
        raise BillingError("We couldn't verify this payment. If money was taken, it will be confirmed shortly.")
    order = fetch_order(order_id)
    notes = order.get("notes") or {}
    if str(notes.get("org_id")) != str(org.id):
        raise BillingError("This payment belongs to a different restaurant.")
    if not activate(
        db, org.id, _note_int(notes, "outlets"), _note_int(notes, "months"), payment_id, int(order["amount"])
    ):
        logger.info("Payment %s was already counted or didn't match the quote", payment_id)
