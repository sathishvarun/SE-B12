"""Invoice numbers and billing details (company, GSTIN, address) on every payment; billing details on the restaurant

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-17 09:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAY = [("invoice_no", sa.String(24)), ("bill_name", sa.String(160)), ("bill_gstin", sa.String(15)),
       ("bill_address", sa.String(300)), ("bill_email", sa.String(255))]


def upgrade() -> None:
    for name, kind in PAY:
        op.add_column("payments", sa.Column(name, kind))
    op.create_unique_constraint("uq_payments_invoice_no", "payments", ["invoice_no"])
    op.add_column("organizations", sa.Column("billing_name", sa.String(160)))
    op.add_column("organizations", sa.Column("billing_address", sa.String(300)))


def downgrade() -> None:
    op.drop_column("organizations", "billing_address")
    op.drop_column("organizations", "billing_name")
    op.drop_constraint("uq_payments_invoice_no", "payments", type_="unique")
    for name, _ in reversed(PAY):
        op.drop_column("payments", name)
