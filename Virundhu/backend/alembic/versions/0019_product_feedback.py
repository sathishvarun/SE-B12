"""Feedback about Virundhu itself: share-feedback form and ease-of-use check.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("rating", sa.Integer),
        sa.Column("ease", sa.Integer),
        sa.Column("nps", sa.Integer),
        sa.Column("area", sa.String(12)),
        sa.Column("message", sa.Text),
        sa.Column("name", sa.String(120)),
        sa.Column("email", sa.String(254)),
        sa.Column("restaurant", sa.String(160)),
        sa.Column("page", sa.String(120)),
        sa.Column("consent_quote", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(8), nullable=False, server_default="new", index=True),
        sa.Column("ai_kind", sa.String(10)),
        sa.Column("ai_sentiment", sa.String(10)),
        sa.Column("ai_area", sa.String(12)),
        sa.Column("ai_summary", sa.String(300)),
        sa.Column("agent_action", sa.String(300)),
        sa.Column("ticket_id", sa.Integer, sa.ForeignKey("support_tickets.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("product_feedback")
