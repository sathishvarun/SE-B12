"""Books: credit notes on refunds, Dodo tax and settlement per payment, Dodo payouts, proforma invoice requests.

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def _stamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("payments", sa.Column("provider_tax_paise", sa.Integer))
    op.add_column("payments", sa.Column("settlement_paise", sa.Integer))
    op.add_column("payments", sa.Column("settlement_currency", sa.String(3)))
    op.add_column("refunds", sa.Column("credit_note_no", sa.String(24), unique=True))
    # Credit notes for refunds that already went through
    op.execute(
        "UPDATE refunds SET credit_note_no = 'CN-' || to_char(refunded_at AT TIME ZONE 'Asia/Kolkata', 'YYYYMM') "
        "|| '-' || lpad(id::text, 5, '0') WHERE status = 'succeeded' AND credit_note_no IS NULL"
    )
    op.create_table(
        "dodo_payouts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("payout_id", sa.String(64), nullable=False, unique=True),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("fee_paise", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tax_paise", sa.Integer, nullable=False, server_default="0"),
        sa.Column("refunds_paise", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chargebacks_paise", sa.Integer, nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("remarks", sa.String(300)),
        sa.Column("document_url", sa.String(500)),
        *_stamps(),
    )
    op.create_table(
        "invoice_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("organization_id", sa.Integer, sa.ForeignKey("organizations.id", ondelete="CASCADE"), index=True),
        sa.Column("number", sa.String(24), unique=True),
        sa.Column("outlets", sa.Integer, nullable=False),
        sa.Column("months", sa.Integer, nullable=False),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("bill_name", sa.String(160)),
        sa.Column("bill_gstin", sa.String(15)),
        sa.Column("bill_address", sa.String(300)),
        sa.Column("bill_email", sa.String(254)),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("payment_id", sa.Integer, sa.ForeignKey("payments.id", ondelete="SET NULL")),
        *_stamps(),
    )


def downgrade() -> None:
    op.drop_table("invoice_requests")
    op.drop_table("dodo_payouts")
    op.drop_column("refunds", "credit_note_no")
    for c in ("settlement_currency", "settlement_paise", "provider_tax_paise"):
        op.drop_column("payments", c)
