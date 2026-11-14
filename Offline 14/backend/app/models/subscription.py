"""Subscription model and its enums (billing via Dodo Payments)."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import pg_enum

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionPlan(enum.StrEnum):
    """Which plan the user is on."""

    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(enum.StrEnum):
    """Billing state of the subscription."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class Subscription(TimestampMixin, Base):
    """One billing subscription per user."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    dodo_customer_id: Mapped[str | None] = mapped_column(String(255))
    dodo_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(
        pg_enum(SubscriptionPlan, "subscription_plan"),
        default=SubscriptionPlan.FREE,
        server_default=SubscriptionPlan.FREE.value,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        pg_enum(SubscriptionStatus, "subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="subscription")
