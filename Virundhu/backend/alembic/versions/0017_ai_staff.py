"""AI staff: owner rules on organizations and the guest win-back table

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-19 10:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("ai_rules", postgresql.JSONB(), nullable=True))
    op.create_table(
        "guest_recoveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("code", sa.String(16), nullable=False, unique=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="drafted"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("returned_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_guest_recoveries_organization_id", "guest_recoveries", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_guest_recoveries_organization_id", "guest_recoveries")
    op.drop_table("guest_recoveries")
    op.drop_column("organizations", "ai_rules")
