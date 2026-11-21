"""Reply promise: every bad review answered within the owner's target (60 minutes by default), with reminders.

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Minutes to answer a bad review (1-3 stars or urgent). NULL switches the reminders off; the numbers still show.
    op.add_column("organizations", sa.Column("reply_target_minutes", sa.Integer, server_default="60"))
    # 0 nothing sent, 1 manager reminded (half-time), 2 owner told (deadline), 3 final nudge (double time)
    op.add_column("reviews", sa.Column("promise_stage", sa.SmallInteger, server_default="0", nullable=False))
    # Reviews already in the inbox are history: never start reminders for them.
    op.execute("UPDATE reviews SET promise_stage = 3")


def downgrade() -> None:
    op.drop_column("reviews", "promise_stage")
    op.drop_column("organizations", "reply_target_minutes")
