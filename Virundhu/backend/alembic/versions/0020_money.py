"""Money page: refunds table, refunded total and test-mode flag on payments.

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("is_test", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("payments", sa.Column("refunded_paise", sa.Integer, nullable=False, server_default="0"))
    # Every payment so far was made while Dodo was in test mode (live mode was switched on 20 Nov 2026).
    op.execute("UPDATE payments SET is_test = true WHERE created_at < '2026-11-20 06:00:00+00'")
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("refund_id", sa.String(64), nullable=False, unique=True),
        sa.Column("provider_payment_id", sa.String(64), nullable=False, index=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(300)),
        sa.Column("is_test", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_column("payments", "refunded_paise")
    op.drop_column("payments", "is_test")
