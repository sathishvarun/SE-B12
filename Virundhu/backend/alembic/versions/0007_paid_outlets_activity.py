"""Outlet-based pricing (paid outlets) and the admin activity log

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16 11:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("paid_outlets", sa.Integer(), nullable=True))
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=40), nullable=False, index=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("restaurant", sa.String(length=120), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("seen", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("activity_log")
    op.drop_column("organizations", "paid_outlets")
