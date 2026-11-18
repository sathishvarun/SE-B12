"""Google auto-pilot, own QR feedback link, WhatsApp alert numbers

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-16 09:20:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "'google', 'zomato', 'swiggy', 'other'"
NEW = "'google', 'zomato', 'swiggy', 'direct', 'other'"


def upgrade() -> None:
    op.add_column("organizations", sa.Column("autopilot_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("organizations", sa.Column("autopilot_min_rating", sa.Integer(), server_default="4", nullable=False))
    op.add_column("organizations", sa.Column("feedback_token", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_org_feedback_token", "organizations", ["feedback_token"])
    op.add_column("organizations", sa.Column("google_review_url", sa.String(length=500), nullable=True))
    op.add_column("organizations", sa.Column("whatsapp_numbers", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("reviews", sa.Column("auto_replied", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("reviews", sa.Column("guest_name", sa.String(length=80), nullable=True))
    op.add_column("reviews", sa.Column("guest_contact", sa.String(length=120), nullable=True))
    op.drop_constraint("review_platform", "reviews", type_="check")
    op.create_check_constraint("review_platform", "reviews", f"platform IN ({NEW})")


def downgrade() -> None:
    op.execute("UPDATE reviews SET platform = 'other' WHERE platform = 'direct'")
    op.drop_constraint("review_platform", "reviews", type_="check")
    op.create_check_constraint("review_platform", "reviews", f"platform IN ({OLD})")
    for col in ("guest_contact", "guest_name", "auto_replied"):
        op.drop_column("reviews", col)
    op.drop_constraint("uq_org_feedback_token", "organizations", type_="unique")
    for col in ("whatsapp_numbers", "google_review_url", "feedback_token", "autopilot_min_rating", "autopilot_enabled"):
        op.drop_column("organizations", col)
