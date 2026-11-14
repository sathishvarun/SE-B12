"""Billing schemas (see PRPs/api-contract.md)."""

from datetime import datetime

from pydantic import BaseModel

from app.models import SubscriptionPlan, SubscriptionStatus


class PlanLimits(BaseModel):
    """Free-plan limits; both null on Pro (unlimited)."""

    max_contacts: int | None
    max_open_deals: int | None


class PlanUsage(BaseModel):
    """Current usage counted against the limits."""

    contacts: int
    open_deals: int


class SubscriptionResponse(BaseModel):
    """The user's plan, billing status, limits and usage."""

    plan: SubscriptionPlan
    status: SubscriptionStatus
    current_period_end: datetime | None
    limits: PlanLimits
    usage: PlanUsage


class CheckoutResponse(BaseModel):
    """Hosted checkout URL to redirect the browser to."""

    checkout_url: str


class WebhookAck(BaseModel):
    """Webhook acknowledgement."""

    received: bool = True
