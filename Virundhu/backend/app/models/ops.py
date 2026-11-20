"""Alerts, weekly reports and billing."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, OrgScopedMixin, TimestampMixin, str_enum
from app.models.review import URGENCIES
from app.models.user import PLANS

SUB_STATUS = ("trialing", "active", "past_due", "cancelled", "expired")


class AlertRule(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "alert_rules"

    channel: Mapped[str] = mapped_column(str_enum("alert_channel", "email"), default="email", nullable=False)
    recipients: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    min_urgency: Mapped[str] = mapped_column(str_enum("alert_min_urgency", *URGENCIES), default="high", nullable=False)
    categories: Mapped[list | None] = mapped_column(JSONB)
    outlet_ids: Mapped[list | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertLog(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "alert_logs"
    __table_args__ = (UniqueConstraint("review_id", "recipient", name="uq_alert_review_recipient"),)

    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(16), default="email", nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WeeklyReport(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (UniqueConstraint("organization_id", "outlet_id", "week_start", name="uq_report_org_outlet_week"),)

    outlet_id: Mapped[int | None] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"))
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    narrative: Mapped[dict | None] = mapped_column(JSONB)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    razorpay_customer_id: Mapped[str | None] = mapped_column(String(64))
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    plan: Mapped[str] = mapped_column(str_enum("sub_plan", *PLANS), default="trial", nullable=False)
    status: Mapped[str] = mapped_column(str_enum("sub_status", *SUB_STATUS), default="trialing", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Payment(OrgScopedMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    razorpay_payment_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    invoice_url: Mapped[str | None] = mapped_column(String(500))
    outlets: Mapped[int | None] = mapped_column(Integer)
    months: Mapped[int | None] = mapped_column(Integer)  # months paid for (free bonus months not counted)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invoice_no: Mapped[str | None] = mapped_column(String(24), unique=True)  # VR-202611-00012
    bill_name: Mapped[str | None] = mapped_column(String(160))
    bill_gstin: Mapped[str | None] = mapped_column(String(15))
    bill_address: Mapped[str | None] = mapped_column(String(300))
    bill_email: Mapped[str | None] = mapped_column(String(255))
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # made in the provider's test mode
    refunded_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # sum of succeeded refunds
    # From Dodo after the sale (migration 0022): tax Dodo charged inside the amount and what Dodo settles to us.
    provider_tax_paise: Mapped[int | None] = mapped_column(Integer)
    settlement_paise: Mapped[int | None] = mapped_column(Integer)
    settlement_currency: Mapped[str | None] = mapped_column(String(3))


class WebhookEvent(TimestampMixin, Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(OrgScopedMixin, TimestampMixin, Base):
    """In-app alert for one user (bell icon). Created the moment an urgent review is read."""

    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "review_id", name="uq_notification_user_review"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    severity: Mapped[str] = mapped_column(str_enum("notification_severity", "high", "medium", "info"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceConnection(OrgScopedMixin, TimestampMixin, Base):
    """Where reviews come from: google (official API), zomato / swiggy (file import + test feed)."""

    __tablename__ = "source_connections"
    __table_args__ = (UniqueConstraint("organization_id", "provider", name="uq_connection_org_provider"),)

    provider: Mapped[str] = mapped_column(str_enum("connection_provider", "google", "zomato", "swiggy"), nullable=False)
    status: Mapped[str] = mapped_column(
        str_enum("connection_status", "not_connected", "connected", "error"), default="not_connected", nullable=False
    )
    test_feed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_feed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Lead(TimestampMixin, Base):
    """A restaurant that wrote in through the Contact page. Seen by the platform admin only."""

    __tablename__ = "leads"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    restaurant: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))
    outlets: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(16), default="new", server_default="new", nullable=False)
    meet_mode: Mapped[str | None] = mapped_column(String(12))  # meet | zoom | teams | in_person | phone


class DemoMeeting(TimestampMixin, Base):
    """Demo agent: times offered to a lead, the one they booked, and the reminders sent."""

    __tablename__ = "demo_meetings"

    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False)
    token: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    slots: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # ISO times (UTC) offered
    mode: Mapped[str] = mapped_column(String(12), default="meet", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    meeting_link: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(12), default="offered", nullable=False)  # offered|booked|done|expired
    nudged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminded_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminded_hour: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AgentRun(TimestampMixin, Base):
    """One thing an AI agent did on its own (or handed to a person). Shown in the admin's Autopilot feed."""

    __tablename__ = "agent_runs"

    agent: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    outcome: Mapped[str] = mapped_column(String(12), default="done", nullable=False)  # done | escalated | failed
    ref: Mapped[str | None] = mapped_column(String(40))  # lead:12, ticket:5, meeting:3
    detail: Mapped[str | None] = mapped_column(Text)


class Refund(TimestampMixin, Base):
    """Money returned to a customer, as reported by the payment provider (webhook or the admin's sync)."""

    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # succeeded | pending | failed
    reason: Mapped[str | None] = mapped_column(String(300))
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    credit_note_no: Mapped[str | None] = mapped_column(String(24), unique=True)  # CN-202611-00007 (migration 0022)


class ProductFeedback(TimestampMixin, Base):
    """Feedback about Virundhu itself (not guest reviews): the share-feedback form and the ease-of-use check.

    Isai, the feedback agent, reads each one, replies, and routes it (ticket for Tara, idea count, testimonial).
    """

    __tablename__ = "product_feedback"

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # app | website
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # idea | problem | praise | other | ease
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5 overall
    ease: Mapped[int | None] = mapped_column(Integer)  # 1 very hard ... 5 very easy
    nps: Mapped[int | None] = mapped_column(Integer)  # 0-10 would recommend
    area: Mapped[str | None] = mapped_column(String(12))
    message: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    restaurant: Mapped[str | None] = mapped_column(String(160))
    page: Mapped[str | None] = mapped_column(String(120))
    consent_quote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(8), default="new", nullable=False, index=True)  # new | done | failed
    ai_kind: Mapped[str | None] = mapped_column(String(10))
    ai_sentiment: Mapped[str | None] = mapped_column(String(10))
    ai_area: Mapped[str | None] = mapped_column(String(12))
    ai_summary: Mapped[str | None] = mapped_column(String(300))
    agent_action: Mapped[str | None] = mapped_column(String(300))
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("support_tickets.id", ondelete="SET NULL"))


class ActivityLog(TimestampMixin, Base):
    """Things the platform admin should know about: sign-ups, password changes, deletions, payments, demo requests.

    organization_id is a plain number (no foreign key) so the record survives when a restaurant is deleted.
    """

    __tablename__ = "activity_log"

    kind: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    organization_id: Mapped[int | None] = mapped_column(Integer)
    restaurant: Mapped[str | None] = mapped_column(String(120))
    user_email: Mapped[str | None] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(String(500))
    seen: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)


class ReviewRequest(TimestampMixin, Base):
    """One 'how was your food?' message to a guest. Only a hash of the number is kept (to avoid asking twice)."""

    __tablename__ = "review_requests"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[int | None] = mapped_column(ForeignKey("outlets.id", ondelete="SET NULL"))
    phone_hash: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(20))  # whatsapp_api | whatsapp_link


class Testimonial(TimestampMixin, Base):
    """A real customer's words, added by the admin with their permission. Shown on the home page when published."""

    __tablename__ = "testimonials"

    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str | None] = mapped_column(String(120))  # "Owner, Annapoorna Mess, Coimbatore"
    quote: Mapped[str] = mapped_column(String(600))
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)


class PlanReminder(OrgScopedMixin, TimestampMixin, Base):
    """One 'your trial/plan ends in N days' reminder, recorded so each one goes out only once (days_left 0 = ended)."""

    __tablename__ = "plan_reminders"
    __table_args__ = (UniqueConstraint("organization_id", "period_end", "days_left", name="uq_plan_reminder"),)

    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    days_left: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # trial | plan


class SupportTicket(TimestampMixin, Base):
    """A customer's question or problem (payment, bug, account...), handled by the admin. Number: VT-00012."""

    __tablename__ = "support_tickets"

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), index=True)
    restaurant: Mapped[str | None] = mapped_column(String(160))  # kept if the restaurant is later deleted
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    user_email: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # payment | bug | account | feature | other
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)  # open | in_progress | resolved
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TicketMessage(TimestampMixin, Base):
    __tablename__ = "ticket_messages"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    author_email: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)


class GuestRecovery(OrgScopedMixin, TimestampMixin, Base):
    """Win-back agent: an unhappy guest who left a phone/email gets an apology and a comeback code."""

    __tablename__ = "guest_recoveries"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="drafted", nullable=False)  # drafted | sent | returned
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DodoPayout(TimestampMixin, Base):
    """A payout from Dodo to the bank account, with its fee and tax (Admin → Accounts → Sync Dodo). Migration 0022."""

    __tablename__ = "dodo_payouts"

    payout_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    refunds_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chargebacks_paise: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(300))
    document_url: Mapped[str | None] = mapped_column(String(500))


class InvoiceRequest(TimestampMixin, Base):
    """A proforma invoice for a bank transfer (PI-202611-00003). Closed when the admin records the payment."""

    __tablename__ = "invoice_requests"

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    number: Mapped[str | None] = mapped_column(String(24), unique=True)
    outlets: Mapped[int] = mapped_column(Integer, nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    bill_name: Mapped[str | None] = mapped_column(String(160))
    bill_gstin: Mapped[str | None] = mapped_column(String(15))
    bill_address: Mapped[str | None] = mapped_column(String(300))
    bill_email: Mapped[str | None] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)  # open | paid | cancelled
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
