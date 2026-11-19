"""AI agent team: demo meetings, agent run log, lead's preferred meeting mode.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("leads", sa.Column("meet_mode", sa.String(12)))
    op.create_table(
        "demo_meetings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token", sa.String(40), nullable=False, unique=True),
        sa.Column("slots", JSONB, nullable=False, server_default="[]"),
        sa.Column("mode", sa.String(12), nullable=False, server_default="meet"),
        sa.Column("starts_at", sa.DateTime(timezone=True), index=True),
        sa.Column("meeting_link", sa.String(300)),
        sa.Column("status", sa.String(12), nullable=False, server_default="offered"),
        sa.Column("nudged", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reminded_day", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reminded_hour", sa.Boolean, nullable=False, server_default=sa.false()),
        *_ts(),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("agent", sa.String(20), nullable=False, index=True),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("outcome", sa.String(12), nullable=False, server_default="done"),
        sa.Column("ref", sa.String(40)),
        sa.Column("detail", sa.Text),
        *_ts(),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("demo_meetings")
    op.drop_column("leads", "meet_mode")
