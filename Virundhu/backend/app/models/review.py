"""Outlets, imports, reviews, AI analysis, corrections and usage."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, OrgScopedMixin, TimestampMixin, str_enum

PLATFORMS = (
    "google",
    "zomato",
    "swiggy",
    "direct",
    "other",
    "tripadvisor",
    "instagram",
    "facebook",
)  # direct = the restaurant's own QR feedback link
SENTIMENTS = ("positive", "neutral", "negative")
CATEGORIES = ("food_quality", "delivery", "price", "staff", "packaging", "hygiene", "app", "other")
URGENCIES = ("low", "medium", "high")
LANGUAGES = ("english", "tamil", "tanglish", "other")
ANALYSIS_STATUS = ("pending", "pending_quota", "analyzed", "needs_review")
WORKFLOW_STATUS = ("new", "in_progress", "replied", "ignored")
IMPORT_STATUS = ("queued", "processing", "completed", "failed")
RESULT_STATUS = ("analyzed", "needs_review", "human_corrected")


class Outlet(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "outlets"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(80))
    google_maps_url: Mapped[str | None] = mapped_column(String(500))
    address: Mapped[str | None] = mapped_column(String(300))
    district: Mapped[str | None] = mapped_column(String(80))
    pincode: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(20))
    manager_name: Mapped[str | None] = mapped_column(String(120))
    manager_phone: Mapped[str | None] = mapped_column(String(20))
    manager_email: Mapped[str | None] = mapped_column(String(254))
    zomato_url: Mapped[str | None] = mapped_column(String(500))
    swiggy_url: Mapped[str | None] = mapped_column(String(500))
    competitors: Mapped[dict | None] = mapped_column(JSONB)  # nearby restaurants from Google Places (cached daily)
    competitors_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ImportBatch(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "import_batches"

    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    analyzed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(str_enum("import_status", *IMPORT_STATUS), default="queued", nullable=False)
    error_report: Mapped[list | None] = mapped_column(JSONB)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Review(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("organization_id", "platform", "external_id", name="uq_review_org_platform_ext"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        Index("ix_reviews_org_date", "organization_id", "review_date"),
        Index("ix_reviews_org_workflow", "organization_id", "workflow_status"),
    )

    outlet_id: Mapped[int | None] = mapped_column(ForeignKey("outlets.id", ondelete="SET NULL"), index=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id", ondelete="SET NULL"))
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(str_enum("review_platform", *PLATFORMS), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    analysis_status: Mapped[str] = mapped_column(
        str_enum("analysis_status", *ANALYSIS_STATUS), default="pending", nullable=False
    )
    workflow_status: Mapped[str] = mapped_column(
        str_enum("workflow_status", *WORKFLOW_STATUS), default="new", nullable=False
    )
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    final_reply: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Sample data (demo restaurant, sample feed) is labelled everywhere so it is never mistaken for real reviews.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Where the review lives at its source, e.g. Google's "accounts/1/locations/2/reviews/3" (used to post replies).
    source_ref: Mapped[str | None] = mapped_column(String(300))
    reply_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_replied: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    holding_reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # safe "please call us" reply
    guest_name: Mapped[str | None] = mapped_column(String(80))
    guest_contact: Mapped[str | None] = mapped_column(String(120))  # phone or email the guest chose to give

    analysis: Mapped["ReviewAnalysis | None"] = relationship(
        back_populates="review", uselist=False, cascade="all, delete-orphan"
    )


class ReviewAnalysis(TimestampMixin, Base):
    __tablename__ = "review_analyses"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), unique=True, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(str_enum("sentiment", *SENTIMENTS))
    category: Mapped[str | None] = mapped_column(str_enum("category", *CATEGORIES))
    urgency: Mapped[str | None] = mapped_column(str_enum("urgency", *URGENCIES), index=True)
    language: Mapped[str | None] = mapped_column(str_enum("language", *LANGUAGES))
    summary: Mapped[str | None] = mapped_column(String(200))
    suggested_reply: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(str_enum("result_status", *RESULT_STATUS), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(80))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_inr: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"), nullable=False)
    safety_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # [{"name": "chicken biryani", "sentiment": "negative"}], staff: [{"name": "Ravi", "sentiment": "positive"}]
    dishes: Mapped[list | None] = mapped_column(JSONB)
    staff: Mapped[list | None] = mapped_column(JSONB)

    review: Mapped[Review] = relationship(back_populates="analysis")


class ReviewCorrection(TimestampMixin, Base):
    __tablename__ = "review_corrections"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(64))
    new_value: Mapped[str] = mapped_column(String(64), nullable=False)


class UsageCounter(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "usage_counters"
    __table_args__ = (UniqueConstraint("organization_id", "period", name="uq_usage_org_period"),)

    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    reviews_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_inr: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"), nullable=False)
