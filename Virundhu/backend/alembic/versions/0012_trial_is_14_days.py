"""Every free trial is exactly 14 days: shorten any trial that was extended beyond that

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-17 08:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE organizations SET trial_ends_at = created_at + interval '14 days' "
        "WHERE plan = 'trial' AND is_demo = false AND trial_ends_at > created_at + interval '14 days'"
    )


def downgrade() -> None:
    pass  # the old, longer end dates aren't kept
