"""Initial schema: users, auth tokens, CRM tables and subscriptions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types (DB stores the lowercase values).
lead_source = sa.Enum("website", "referral", "social", "other", name="lead_source")
lead_status = sa.Enum(
    "new", "contacted", "qualified", "lost", "converted", name="lead_status"
)
deal_stage = sa.Enum(
    "prospect", "proposal", "negotiation", "won", "lost", name="deal_stage"
)
task_priority = sa.Enum("low", "medium", "high", name="task_priority")
task_status = sa.Enum("pending", "done", name="task_status")
subscription_plan = sa.Enum("free", "pro", name="subscription_plan")
subscription_status = sa.Enum(
    "active", "trialing", "past_due", "cancelled", name="subscription_status"
)

ENUM_NAMES = [
    "lead_source",
    "lead_status",
    "deal_stage",
    "task_priority",
    "task_status",
    "subscription_plan",
    "subscription_status",
]


def _created_at() -> sa.Column:
    """created_at column with a server default of now()."""
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _updated_at() -> sa.Column:
    """updated_at column with a server default of now()."""
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def _user_fk(table: str) -> sa.Column:
    """Non-null user_id column referencing users.id with ON DELETE CASCADE."""
    return sa.Column(
        "user_id",
        sa.Integer(),
        sa.ForeignKey(
            "users.id", ondelete="CASCADE", name=f"fk_{table}_user_id_users"
        ),
        nullable=False,
    )


def upgrade() -> None:
    """Create all tables, enum types, constraints and indexes."""
    # --- users -----------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- refresh_tokens --------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("refresh_tokens"),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # --- password_reset_tokens ------------------------------------------
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("password_reset_tokens"),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.false(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )

    # --- contacts --------------------------------------------------------
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("contacts"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
    )
    op.create_index("ix_contacts_user_id", "contacts", ["user_id"])
    op.create_index("ix_contacts_user_id_name", "contacts", ["user_id", "name"])

    # --- tags ------------------------------------------------------------
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("tags"),
        sa.Column("name", sa.String(50), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_tags"),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])

    # --- contact_tags (association) --------------------------------------
    op.create_table(
        "contact_tags",
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey(
                "contacts.id",
                ondelete="CASCADE",
                name="fk_contact_tags_contact_id_contacts",
            ),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey(
                "tags.id", ondelete="CASCADE", name="fk_contact_tags_tag_id_tags"
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("contact_id", "tag_id", name="pk_contact_tags"),
    )

    # --- leads -----------------------------------------------------------
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("leads"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("source", lead_source, server_default="other", nullable=False),
        sa.Column("status", lead_status, server_default="new", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "converted_contact_id",
            sa.Integer(),
            sa.ForeignKey(
                "contacts.id",
                ondelete="SET NULL",
                name="fk_leads_converted_contact_id_contacts",
            ),
            nullable=True,
        ),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_leads"),
    )
    op.create_index("ix_leads_user_id", "leads", ["user_id"])
    op.create_index("ix_leads_user_id_status", "leads", ["user_id", "status"])

    # --- deals -----------------------------------------------------------
    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("deals"),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey(
                "contacts.id", ondelete="CASCADE", name="fk_deals_contact_id_contacts"
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("stage", deal_stage, server_default="prospect", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_deals"),
        sa.CheckConstraint("value >= 0", name=op.f("ck_deals_value_non_negative")),
    )
    op.create_index("ix_deals_user_id", "deals", ["user_id"])
    op.create_index("ix_deals_contact_id", "deals", ["contact_id"])
    op.create_index("ix_deals_user_id_stage", "deals", ["user_id", "stage"])

    # --- tasks -----------------------------------------------------------
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("tasks"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("priority", task_priority, server_default="medium", nullable=False),
        sa.Column("status", task_status, server_default="pending", nullable=False),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey(
                "contacts.id", ondelete="SET NULL", name="fk_tasks_contact_id_contacts"
            ),
            nullable=True,
        ),
        sa.Column(
            "lead_id",
            sa.Integer(),
            sa.ForeignKey(
                "leads.id", ondelete="SET NULL", name="fk_tasks_lead_id_leads"
            ),
            nullable=True,
        ),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey(
                "deals.id", ondelete="SET NULL", name="fk_tasks_deal_id_deals"
            ),
            nullable=True,
        ),
        sa.Column(
            "reminder_sent", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
        sa.CheckConstraint(
            "(CASE WHEN contact_id IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN lead_id IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN deal_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name=op.f("ck_tasks_at_most_one_parent"),
        ),
    )
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_contact_id", "tasks", ["contact_id"])
    op.create_index("ix_tasks_lead_id", "tasks", ["lead_id"])
    op.create_index("ix_tasks_deal_id", "tasks", ["deal_id"])
    op.create_index(
        "ix_tasks_user_id_status_due_date", "tasks", ["user_id", "status", "due_date"]
    )

    # --- attachments -----------------------------------------------------
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("attachments"),
        sa.Column(
            "contact_id",
            sa.Integer(),
            sa.ForeignKey(
                "contacts.id",
                ondelete="CASCADE",
                name="fk_attachments_contact_id_contacts",
            ),
            nullable=True,
        ),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey(
                "deals.id", ondelete="CASCADE", name="fk_attachments_deal_id_deals"
            ),
            nullable=True,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
        sa.UniqueConstraint("storage_path", name="uq_attachments_storage_path"),
        sa.CheckConstraint(
            "(contact_id IS NULL) <> (deal_id IS NULL)",
            name=op.f("ck_attachments_exactly_one_parent"),
        ),
    )
    op.create_index("ix_attachments_user_id", "attachments", ["user_id"])
    op.create_index("ix_attachments_contact_id", "attachments", ["contact_id"])
    op.create_index("ix_attachments_deal_id", "attachments", ["deal_id"])

    # --- subscriptions ---------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        _user_fk("subscriptions"),
        sa.Column("dodo_customer_id", sa.String(255), nullable=True),
        sa.Column("dodo_subscription_id", sa.String(255), nullable=True),
        sa.Column("plan", subscription_plan, server_default="free", nullable=False),
        sa.Column(
            "status", subscription_status, server_default="active", nullable=False
        ),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint(
            "dodo_subscription_id", name="uq_subscriptions_dodo_subscription_id"
        ),
    )
    op.create_index(
        "ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True
    )


def downgrade() -> None:
    """Drop all tables (children first), then the enum types."""
    for table in [
        "subscriptions",
        "attachments",
        "tasks",
        "deals",
        "leads",
        "contact_tags",
        "tags",
        "contacts",
        "password_reset_tokens",
        "refresh_tokens",
        "users",
    ]:
        op.drop_table(table)

    for enum_name in ENUM_NAMES:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
