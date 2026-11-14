"""Deal model and its stage enum."""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import pg_enum

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.contact import Contact
    from app.models.task import Task
    from app.models.user import User


class DealStage(enum.StrEnum):
    """Kanban column a deal sits in."""

    PROSPECT = "prospect"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class Deal(TimestampMixin, Base):
    """A sales opportunity tied to a contact."""

    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("value >= 0", name="value_non_negative"),
        Index("ix_deals_user_id_stage", "user_id", "stage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), server_default="0")
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    stage: Mapped[DealStage] = mapped_column(
        pg_enum(DealStage, "deal_stage"),
        default=DealStage.PROSPECT,
        server_default=DealStage.PROSPECT.value,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="deals")
    contact: Mapped[Contact] = relationship(back_populates="deals")
    tasks: Mapped[list[Task]] = relationship(back_populates="deal", passive_deletes=True)
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", passive_deletes=True
    )
