"""Contact and Tag models plus the contact_tags association table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Index, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.deal import Deal
    from app.models.lead import Lead
    from app.models.task import Task
    from app.models.user import User

contact_tags = Table(
    "contact_tags",
    Base.metadata,
    Column(
        "contact_id",
        ForeignKey("contacts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Contact(TimestampMixin, Base):
    """A person or company the seller does business with."""

    __tablename__ = "contacts"
    __table_args__ = (Index("ix_contacts_user_id_name", "user_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="contacts")
    tags: Mapped[list[Tag]] = relationship(secondary=contact_tags, back_populates="contacts")
    deals: Mapped[list[Deal]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list[Task]] = relationship(back_populates="contact", passive_deletes=True)
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )
    converted_leads: Mapped[list[Lead]] = relationship(
        back_populates="converted_contact", passive_deletes=True
    )


class Tag(TimestampMixin, Base):
    """A user-defined label that can be attached to contacts."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))

    user: Mapped[User] = relationship(back_populates="tags")
    contacts: Mapped[list[Contact]] = relationship(secondary=contact_tags, back_populates="tags")
