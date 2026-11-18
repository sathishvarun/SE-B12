"""Review requests to guests and the weekly summary switch

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-16 20:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outlet_id", sa.Integer(), sa.ForeignKey("outlets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("phone_hash", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_requests_organization_id", "review_requests", ["organization_id"])
    op.create_index("ix_review_requests_phone_hash", "review_requests", ["phone_hash"])
    op.add_column(
        "organizations", sa.Column("weekly_summary", sa.Boolean(), server_default=sa.true(), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("organizations", "weekly_summary")
    op.drop_index("ix_review_requests_phone_hash", table_name="review_requests")
    op.drop_index("ix_review_requests_organization_id", table_name="review_requests")
    op.drop_table("review_requests")
