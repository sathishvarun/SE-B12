"""User account and auth token models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.contact import Contact, Tag
    from app.models.deal import Deal
    from app.models.lead import Lead
    from app.models.subscription import Subscription
    from app.models.task import Task


class User(TimestampMixin, Base):
    """A seller who owns CRM records."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    oauth_provider: Mapped[str | None] = mapped_column(String(50))

    contacts: Mapped[list[Contact]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list[Tag]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    leads: Mapped[list[Lead]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    deals: Mapped[list[Deal]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RefreshToken(CreatedAtMixin, Base):
    """A refresh token, stored as a SHA-256 hash of the raw token."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class PasswordResetToken(CreatedAtMixin, Base):
    """A single-use password reset token, stored as a SHA-256 hash."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")
