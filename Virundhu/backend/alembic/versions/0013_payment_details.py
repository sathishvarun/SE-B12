"""Payments remember what they bought (outlets, months) and the dates they cover, for the admin revenue dashboard

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-17 08:10:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("outlets", sa.Integer()))
    op.add_column("payments", sa.Column("months", sa.Integer()))
    op.add_column("payments", sa.Column("period_start", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("period_end", sa.DateTime(timezone=True)))


def downgrade() -> None:
    for c in ("period_end", "period_start", "months", "outlets"):
        op.drop_column("payments", c)
