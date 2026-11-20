"""AI token ledger (one row per AI call, per restaurant and feature) and Google Places link per outlet.

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True),
        sa.Column("feature", sa.String(32), nullable=False, index=True),
        sa.Column("model", sa.String(80)),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_inr", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])
    op.add_column("outlets", sa.Column("google_place_id", sa.String(300)))
    op.add_column("outlets", sa.Column("google_place_name", sa.String(200)))
    op.add_column("outlets", sa.Column("google_rating", sa.Numeric(2, 1)))
    op.add_column("outlets", sa.Column("google_rating_count", sa.Integer))
    op.add_column("outlets", sa.Column("google_synced_at", sa.DateTime(timezone=True)))
    op.add_column("outlets", sa.Column("google_sync_error", sa.String(300)))
    # Reviews read before this ledger existed already stored their tokens; copy them in so history is complete.
    op.execute(
        """
        INSERT INTO ai_usage (organization_id, feature, model, input_tokens, output_tokens, cost_inr, created_at, updated_at)
        SELECT r.organization_id, 'review_reading', a.model_used, a.input_tokens, a.output_tokens, a.cost_inr,
               a.created_at, a.created_at
        FROM review_analyses a JOIN reviews r ON r.id = a.review_id
        WHERE a.input_tokens > 0 OR a.output_tokens > 0
        """
    )


def downgrade() -> None:
    for col in (
        "google_sync_error",
        "google_synced_at",
        "google_rating_count",
        "google_rating",
        "google_place_name",
        "google_place_id",
    ):
        op.drop_column("outlets", col)
    op.drop_index("ix_ai_usage_created_at", table_name="ai_usage")
    op.drop_table("ai_usage")
