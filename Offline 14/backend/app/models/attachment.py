"""Attachment model (file metadata; bytes live on disk)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.deal import Deal
    from app.models.user import User

# Exactly one of contact_id / deal_id must be set.
ATTACHMENT_ONE_PARENT_SQL = "(contact_id IS NULL) <> (deal_id IS NULL)"


class Attachment(CreatedAtMixin, Base):
    """An uploaded file linked to exactly one contact or deal."""

    __tablename__ = "attachments"
    __table_args__ = (CheckConstraint(ATTACHMENT_ONE_PARENT_SQL, name="exactly_one_parent"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), index=True
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)

    user: Mapped[User] = relationship(back_populates="attachments")
    contact: Mapped[Contact | None] = relationship(back_populates="attachments")
    deal: Mapped[Deal | None] = relationship(back_populates="attachments")
