"""Delete personal data once the Privacy Policy says it's no longer kept. Runs daily from the worker."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Lead, PasswordResetToken, RefreshToken, ReviewRequest

REVIEW_REQUEST_DAYS = 365  # hash of a guest number, kept only to avoid asking twice
CONTACT_MESSAGE_DAYS = 365  # contact-page / demo requests


def purge(db: Session, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    year_ago = now - timedelta(days=REVIEW_REQUEST_DAYS)
    contact_cutoff = now - timedelta(days=CONTACT_MESSAGE_DAYS)
    day_ago = now - timedelta(days=1)
    statements = {
        "review_requests": delete(ReviewRequest).where(ReviewRequest.created_at < year_ago),
        "contact_messages": delete(Lead).where(Lead.created_at < contact_cutoff),
        "expired_sessions": delete(RefreshToken).where(RefreshToken.expires_at < day_ago),
        "expired_reset_links": delete(PasswordResetToken).where(PasswordResetToken.expires_at < day_ago),
    }
    counts = {name: db.execute(stmt).rowcount for name, stmt in statements.items()}
    db.commit()
    return counts
