"""Lead model and its enums."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import pg_enum

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.task import Task
    from app.models.user import User


class LeadSource(enum.StrEnum):
    """Where a lead came from."""

    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL = "social"
    OTHER = "other"


class LeadStatus(enum.StrEnum):
    """Pipeline status of a lead."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CONVERTED = "converted"


class Lead(TimestampMixin, Base):
    """A potential customer not yet converted to a contact."""

    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_user_id_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[LeadSource] = mapped_column(
        pg_enum(LeadSource, "lead_source"),
        default=LeadSource.OTHER,
        server_default=LeadSource.OTHER.value,
    )
    status: Mapped[LeadStatus] = mapped_column(
        pg_enum(LeadStatus, "lead_status"),
        default=LeadStatus.NEW,
        server_default=LeadStatus.NEW.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    converted_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL")
    )

    user: Mapped[User] = relationship(back_populates="leads")
    converted_contact: Mapped[Contact | None] = relationship(back_populates="converted_leads")
    tasks: Mapped[list[Task]] = relationship(back_populates="lead", passive_deletes=True)
