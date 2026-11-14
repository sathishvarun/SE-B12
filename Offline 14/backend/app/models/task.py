"""Task model and its enums."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import pg_enum

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.deal import Deal
    from app.models.lead import Lead
    from app.models.user import User

# At most one of the three optional parent links may be set.
TASK_ONE_PARENT_SQL = (
    "(CASE WHEN contact_id IS NOT NULL THEN 1 ELSE 0 END"
    " + CASE WHEN lead_id IS NOT NULL THEN 1 ELSE 0 END"
    " + CASE WHEN deal_id IS NOT NULL THEN 1 ELSE 0 END) <= 1"
)


class TaskPriority(enum.StrEnum):
    """How urgent a task is."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(enum.StrEnum):
    """Whether a task is finished."""

    PENDING = "pending"
    DONE = "done"


class Task(TimestampMixin, Base):
    """A to-do item, optionally linked to a contact, lead or deal."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(TASK_ONE_PARENT_SQL, name="at_most_one_parent"),
        Index("ix_tasks_user_id_status_due_date", "user_id", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[TaskPriority] = mapped_column(
        pg_enum(TaskPriority, "task_priority"),
        default=TaskPriority.MEDIUM,
        server_default=TaskPriority.MEDIUM.value,
    )
    status: Mapped[TaskStatus] = mapped_column(
        pg_enum(TaskStatus, "task_status"),
        default=TaskStatus.PENDING,
        server_default=TaskStatus.PENDING.value,
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), index=True
    )
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), index=True
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), index=True
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="tasks")
    contact: Mapped[Contact | None] = relationship(back_populates="tasks")
    lead: Mapped[Lead | None] = relationship(back_populates="tasks")
    deal: Mapped[Deal | None] = relationship(back_populates="tasks")
