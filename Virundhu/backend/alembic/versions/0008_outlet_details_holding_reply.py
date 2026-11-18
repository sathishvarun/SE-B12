"""Outlet and brand details (address, district, manager, delivery links) and the safe holding reply

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-16 17:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OUTLET = [
    ("address", 300), ("district", 80), ("pincode", 10), ("phone", 20), ("manager_name", 120),
    ("manager_phone", 20), ("manager_email", 254), ("zomato_url", 500), ("swiggy_url", 500),
]
ORG = [("owner_phone", 20), ("business_type", 30), ("cuisine", 120), ("gstin", 15), ("head_office", 300)]


def upgrade() -> None:
    for name, size in OUTLET:
        op.add_column("outlets", sa.Column(name, sa.String(size), nullable=True))
    for name, size in ORG:
        op.add_column("organizations", sa.Column(name, sa.String(size), nullable=True))
    op.add_column("organizations", sa.Column("outlets_declared", sa.Integer(), nullable=True))
    op.add_column("organizations", sa.Column("holding_reply_hours", sa.Integer(), nullable=True))
    op.add_column("reviews", sa.Column("holding_reply_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_outlets_district", "outlets", ["organization_id", "district"])


def downgrade() -> None:
    op.drop_index("ix_outlets_district", table_name="outlets")
    op.drop_column("reviews", "holding_reply_at")
    op.drop_column("organizations", "holding_reply_hours")
    op.drop_column("organizations", "outlets_declared")
    for name, _ in ORG:
        op.drop_column("organizations", name)
    for name, _ in OUTLET:
        op.drop_column("outlets", name)
