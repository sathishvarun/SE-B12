"""Billing logic: subscription overview, checkout, cancel and Dodo webhook handling.

Plan/status changes happen ONLY in ``handle_webhook_event`` (after signature verification);
a checkout redirect or cancel request never changes the plan by itself.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import BadRequestError, ConflictError
from app.models import (
    Contact,
    Deal,
    DealStage,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)
from app.schemas.billing import PlanLimits, PlanUsage, SubscriptionResponse
from app.services import dodo_payments

logger = logging.getLogger(__name__)

OPEN_DEAL_STAGES = (DealStage.PROSPECT, DealStage.PROPOSAL, DealStage.NEGOTIATION)

# Dodo event type -> (new plan or None to keep, new status)
EVENT_TRANSITIONS: dict[str, tuple[SubscriptionPlan | None, SubscriptionStatus]] = {
    "subscription.active": (SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE),
    "subscription.renewed": (SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE),
    "subscription.on_hold": (None, SubscriptionStatus.PAST_DUE),
    "subscription.past_due": (None, SubscriptionStatus.PAST_DUE),
    # Note: "subscription.failed" is deliberately not handled. Dodo sends it when a
    # *new* subscription could not be created, so the user never had Pro.
    "subscription.cancelled": (SubscriptionPlan.FREE, SubscriptionStatus.CANCELLED),
    "subscription.expired": (SubscriptionPlan.FREE, SubscriptionStatus.CANCELLED),
}
# Events that should not affect a *different* (newer) subscription than the one stored.
NEGATIVE_EVENTS = {
    "subscription.on_hold",
    "subscription.past_due",
    "subscription.cancelled",
    "subscription.expired",
}


@dataclass
class SubscriptionChange:
    """Details needed to notify a user after a webhook changed their subscription."""

    email: str
    user_name: str
    plan: str
    status: str


def get_or_create_subscription(db: Session, user: User) -> Subscription:
    """Return the user's Subscription row, creating a free/active one if missing."""
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if sub is None:
        sub = Subscription(
            user_id=user.id, plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def get_subscription_overview(db: Session, user: User) -> SubscriptionResponse:
    """Build the Subscription response (plan, status, limits and usage)."""
    sub = get_or_create_subscription(db, user)
    contacts = db.scalar(select(func.count(Contact.id)).where(Contact.user_id == user.id)) or 0
    open_deals = (
        db.scalar(
            select(func.count(Deal.id)).where(
                Deal.user_id == user.id, Deal.stage.in_(OPEN_DEAL_STAGES)
            )
        )
        or 0
    )

    if sub.plan == SubscriptionPlan.PRO:
        limits = PlanLimits(max_contacts=None, max_open_deals=None)
    else:
        limits = PlanLimits(
            max_contacts=settings.FREE_PLAN_MAX_CONTACTS,
            max_open_deals=settings.FREE_PLAN_MAX_OPEN_DEALS,
        )
    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        current_period_end=sub.current_period_end,
        limits=limits,
        usage=PlanUsage(contacts=contacts, open_deals=open_deals),
    )


async def start_checkout(db: Session, user: User) -> str:
    """Create a Dodo checkout for Pro and return its URL (409 if already Pro)."""
    sub = get_or_create_subscription(db, user)
    if sub.plan == SubscriptionPlan.PRO:
        raise ConflictError("You are already on the Pro plan")
    return_url = f"{settings.FRONTEND_URL.rstrip('/')}/billing?checkout=success"
    return await dodo_payments.create_checkout(user, return_url)


async def cancel_subscription(db: Session, user: User) -> SubscriptionResponse:
    """Ask Dodo to cancel the Pro subscription. The plan flips when the webhook arrives."""
    sub = get_or_create_subscription(db, user)
    if sub.plan != SubscriptionPlan.PRO or not sub.dodo_subscription_id:
        raise BadRequestError("No active Pro subscription to cancel")
    await dodo_payments.cancel_subscription(sub.dodo_subscription_id)
    return get_subscription_overview(db, user)


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO 8601 string from Dodo (``Z`` suffix allowed); None if missing/invalid."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Could not parse datetime %r from webhook", value)
        return None


def _find_subscription(
    db: Session, user_id_meta: Any, subscription_id: str | None, customer_id: str | None
) -> Subscription | None:
    """Locate the local Subscription via metadata user_id, then Dodo subscription/customer id."""
    if user_id_meta is not None:
        try:
            user = db.get(User, int(user_id_meta))
        except (TypeError, ValueError):
            user = None
        if user is not None:
            return get_or_create_subscription(db, user)
    if subscription_id:
        sub = db.scalar(
            select(Subscription).where(Subscription.dodo_subscription_id == subscription_id)
        )
        if sub is not None:
            return sub
    if customer_id:
        return db.scalar(select(Subscription).where(Subscription.dodo_customer_id == customer_id))
    return None


def handle_webhook_event(db: Session, payload: dict[str, Any]) -> SubscriptionChange | None:
    """
    Apply a verified Dodo webhook payload. Idempotent: replaying an event is a no-op.

    Assumed payload shape (verify with a real test-mode event):
        {"type": "subscription.active", "data": {"subscription_id": "...",
         "customer": {"customer_id": "..."}, "metadata": {"user_id": "1"},
         "next_billing_date": "2026-12-14T00:00:00Z", ...}}

    Returns:
        A SubscriptionChange when plan/status actually changed (to notify the user), else None.
    """
    event_type = str(payload.get("type", ""))
    transition = EVENT_TRANSITIONS.get(event_type)
    if transition is None:
        logger.info("Ignoring Dodo webhook event %r", event_type)
        return None

    data = payload.get("data") or {}
    metadata = data.get("metadata") or {}
    customer = data.get("customer") or {}
    subscription_id = data.get("subscription_id")
    customer_id = customer.get("customer_id") if isinstance(customer, dict) else None

    sub = _find_subscription(db, metadata.get("user_id"), subscription_id, customer_id)
    if sub is None:
        logger.warning(
            "Dodo webhook %s for unknown subscription %s / customer %s",
            event_type,
            subscription_id,
            customer_id,
        )
        return None

    if (
        event_type in NEGATIVE_EVENTS
        and sub.dodo_subscription_id
        and subscription_id
        and sub.dodo_subscription_id != subscription_id
    ):
        logger.info(
            "Ignoring %s for old subscription %s (current is %s)",
            event_type,
            subscription_id,
            sub.dodo_subscription_id,
        )
        return None

    new_plan, new_status = transition

    # Dodo may deliver events late or out of order. Never let an "upgrade" event
    # turn Pro back on unless Dodo says the subscription is active right now, and
    # never revive a subscription we already saw cancelled.
    if new_plan == SubscriptionPlan.PRO:
        if data.get("status") not in (None, "active"):
            logger.info("Ignoring %s: subscription status is %r", event_type, data.get("status"))
            return None
        if (
            sub.status == SubscriptionStatus.CANCELLED
            and subscription_id
            and sub.dodo_subscription_id == subscription_id
        ):
            logger.info(
                "Ignoring late %s for cancelled subscription %s", event_type, subscription_id
            )
            return None

    old_state = (sub.plan, sub.status)

    if new_plan is not None:
        sub.plan = new_plan
    sub.status = new_status
    if subscription_id:
        sub.dodo_subscription_id = subscription_id
    if customer_id:
        sub.dodo_customer_id = customer_id
    if new_plan == SubscriptionPlan.PRO:
        sub.current_period_end = _parse_datetime(data.get("next_billing_date"))
    elif new_plan == SubscriptionPlan.FREE:
        sub.current_period_end = None
    db.commit()

    logger.info(
        "Dodo webhook %s: user %s %s/%s -> %s/%s",
        event_type,
        sub.user_id,
        old_state[0],
        old_state[1],
        sub.plan,
        sub.status,
    )
    if old_state == (sub.plan, sub.status):
        return None

    user = db.get(User, sub.user_id)
    if user is None:
        return None
    return SubscriptionChange(
        email=user.email,
        user_name=user.full_name or user.email,
        plan=sub.plan.value,
        status=sub.status.value,
    )


def send_subscription_changed_email(change: SubscriptionChange) -> None:
    """Send the subscription-changed email (runs as a background task; never raises)."""
    try:
        from app.services.email import render_template, send_email

        html = render_template(
            "subscription_changed.html",
            user_name=change.user_name,
            plan=change.plan,
            status=change.status,
        )
        send_email(change.email, "Your Sathish CRM subscription has changed", html)
    except Exception:
        logger.exception("Failed to send subscription-changed email to %s", change.email)
