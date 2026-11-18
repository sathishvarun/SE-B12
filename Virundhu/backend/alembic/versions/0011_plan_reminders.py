"""Trial and plan ending reminders (sent once each)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-17 07:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("days_left", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "period_end", "days_left", name="uq_plan_reminder"),
    )
    op.create_index("ix_plan_reminders_organization_id", "plan_reminders", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_plan_reminders_organization_id", table_name="plan_reminders")
    op.drop_table("plan_reminders")
