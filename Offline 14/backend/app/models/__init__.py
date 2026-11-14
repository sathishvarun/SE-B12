"""All ORM models. Importing this package registers every table on Base.metadata."""

from app.models.attachment import Attachment
from app.models.base import Base, CreatedAtMixin, TimestampMixin
from app.models.contact import Contact, Tag, contact_tags
from app.models.deal import Deal, DealStage
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import PasswordResetToken, RefreshToken, User

__all__ = [
    "Attachment",
    "Base",
    "Contact",
    "CreatedAtMixin",
    "Deal",
    "DealStage",
    "Lead",
    "LeadSource",
    "LeadStatus",
    "PasswordResetToken",
    "RefreshToken",
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "Tag",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "TimestampMixin",
    "User",
    "contact_tags",
]
