"""Users, organizations, memberships and tokens."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, str_enum

ROLES = ("owner", "manager", "agent")
PLANS = ("trial", "starter", "growth", "chain")
REPLY_TONES = ("warm", "professional", "short")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    oauth_provider: Mapped[str | None] = mapped_column(String(32))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    city: Mapped[str | None] = mapped_column(String(80))
    plan: Mapped[str] = mapped_column(str_enum("org_plan", *PLANS), default="trial", nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reply_tone: Mapped[str] = mapped_column(str_enum("reply_tone", *REPLY_TONES), default="warm", nullable=False)
    reply_signature: Mapped[str | None] = mapped_column(String(120))
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Google auto-pilot: post the reply draft by itself on happy Google reviews
    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    autopilot_min_rating: Mapped[int] = mapped_column(Integer, default=4, server_default="4", nullable=False)
    # Own feedback link (QR code): /f/<feedback_token>
    feedback_token: Mapped[str | None] = mapped_column(String(32), unique=True)
    google_review_url: Mapped[str | None] = mapped_column(String(500))
    owner_phone: Mapped[str | None] = mapped_column(String(20))
    business_type: Mapped[str | None] = mapped_column(String(30))  # dine_in | cloud_kitchen | both
    cuisine: Mapped[str | None] = mapped_column(String(120))
    gstin: Mapped[str | None] = mapped_column(String(15))
    billing_name: Mapped[str | None] = mapped_column(String(160))  # company name printed on receipts
    billing_address: Mapped[str | None] = mapped_column(String(300))
    head_office: Mapped[str | None] = mapped_column(String(300))
    outlets_declared: Mapped[int | None] = mapped_column(Integer)  # "how many outlets do you have" at sign-up
    holding_reply_hours: Mapped[int | None] = mapped_column(Integer)  # None = off
    weekly_summary: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    billing_key_hash: Mapped[str | None] = mapped_column(String(64), index=True)  # key for the billing-software hook
    ask_after_bill: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # WhatsApp alert numbers in international format, e.g. ["+919876543210"]
    whatsapp_numbers: Mapped[list | None] = mapped_column(JSONB)
    ai_rules: Mapped[dict | None] = mapped_column(JSONB)  # AI staff rules: banned words, escalate, offer, order value
    # Outlets paid for in the current plan (sets the outlet and review limits)
    paid_outlets: Mapped[int | None] = mapped_column(Integer)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Membership(TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(str_enum("member_role", *ROLES), nullable=False)
    # None = every outlet. A list of outlet ids limits a manager/staff member to those outlets only.
    outlet_ids: Mapped[list | None] = mapped_column(JSONB)

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class Invitation(TimestampMixin, Base):
    __tablename__ = "invitations"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(str_enum("invite_role", *ROLES), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    outlet_ids: Mapped[list | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PasswordResetToken(TimestampMixin, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
