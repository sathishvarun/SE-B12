"""More review platforms, billing-software hook, nearby competitors cache, testimonials

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16 21:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD = "'google', 'zomato', 'swiggy', 'direct', 'other'"
NEW = OLD + ", 'tripadvisor', 'instagram', 'facebook'"


def upgrade() -> None:
    op.drop_constraint("review_platform", "reviews", type_="check")
    op.create_check_constraint("review_platform", "reviews", f"platform IN ({NEW})")
    op.add_column("organizations", sa.Column("billing_key_hash", sa.String(64), nullable=True))
    op.create_index("ix_organizations_billing_key_hash", "organizations", ["billing_key_hash"])
    op.add_column(
        "organizations", sa.Column("ask_after_bill", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column("outlets", sa.Column("competitors", JSONB(), nullable=True))
    op.add_column("outlets", sa.Column("competitors_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "testimonials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(120), nullable=True),
        sa.Column("quote", sa.String(600), nullable=False),
        sa.Column("published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.execute("UPDATE reviews SET platform = 'other' WHERE platform IN ('tripadvisor', 'instagram', 'facebook')")
    op.drop_constraint("review_platform", "reviews", type_="check")
    op.create_check_constraint("review_platform", "reviews", f"platform IN ({OLD})")
    op.drop_table("testimonials")
    op.drop_column("outlets", "competitors_at")
    op.drop_column("outlets", "competitors")
    op.drop_column("organizations", "ask_after_bill")
    op.drop_index("ix_organizations_billing_key_hash", table_name="organizations")
    op.drop_column("organizations", "billing_key_hash")
