"""Dishes and staff named in each review (for the insights page)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-17 12:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("review_analyses", sa.Column("dishes", JSONB))
    op.add_column("review_analyses", sa.Column("staff", JSONB))


def downgrade() -> None:
    op.drop_column("review_analyses", "staff")
    op.drop_column("review_analyses", "dishes")
