"""Two-step sign-in with an authenticator app (TOTP), with single-use recovery codes.

Revision ID: 0026
Revises: 0025
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(300)))  # encrypted (services/crypto.py)
    op.add_column("users", sa.Column("totp_pending", sa.String(300)))  # encrypted; set while scanning the QR code
    op.add_column("users", sa.Column("totp_enabled_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("totp_recovery", JSONB))  # sha256 of unused recovery codes
    op.add_column("users", sa.Column("totp_last_step", sa.BigInteger))  # last accepted 30-second step: no replays


def downgrade() -> None:
    for c in ("totp_last_step", "totp_recovery", "totp_enabled_at", "totp_pending", "totp_secret"):
        op.drop_column("users", c)
