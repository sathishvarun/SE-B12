"""Schemas for the /admin endpoints (see PRPs/api-contract.md)."""

from datetime import datetime

from pydantic import BaseModel

from app.models import SubscriptionPlan


class AdminUser(BaseModel):
    """A user row as shown in the admin users table."""

    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    plan: SubscriptionPlan
    created_at: datetime


class AdminUserUpdate(BaseModel):
    """Body for PUT /admin/users/{id}. Only fields that are sent get changed."""

    is_active: bool | None = None
    is_admin: bool | None = None


class AdminStats(BaseModel):
    """Platform-wide numbers for the admin dashboard."""

    total_users: int
    active_users: int
    pro_subscriptions: int
    signups_last_30_days: int
    total_contacts: int
    total_deals: int
