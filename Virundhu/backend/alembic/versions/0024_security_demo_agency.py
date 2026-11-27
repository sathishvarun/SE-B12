"""Security, demo prep and agencies.

- users.sessions_valid_after: access tokens issued before it are refused (password change/reset, sign out everywhere).
- leads.maps_link: the restaurant's Google Maps link, so the demo opens with replies to their own latest reviews.
- demo_preps: those prepared replies.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sessions_valid_after", sa.DateTime(timezone=True)))
    op.add_column("leads", sa.Column("maps_link", sa.String(500)))
    op.create_table(
        "demo_preps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lead_id", sa.Integer, sa.ForeignKey("leads.id", ondelete="SET NULL"), index=True),
        sa.Column("restaurant", sa.String(160), nullable=False),
        sa.Column("maps_link", sa.String(500)),
        sa.Column("place_id", sa.String(300)),
        sa.Column("place_name", sa.String(200)),
        sa.Column("rating", sa.Numeric(2, 1)),
        sa.Column("rating_count", sa.Integer),
        sa.Column("tone", sa.String(16), nullable=False, server_default="warm"),
        sa.Column("reviews", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(12), nullable=False, server_default="queued"),  # queued | ready | failed
        sa.Column("error", sa.String(300)),
        sa.Column("created_by", sa.String(160)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("demo_preps")
    op.drop_column("leads", "maps_link")
    op.drop_column("users", "sessions_valid_after")
