"""Record events the platform admin should see (Admin console → Activity, and the admin bell)."""

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ActivityLog
from app.services.emailer import send_email

logger = logging.getLogger(__name__)

LABELS = {
    "signup": "New restaurant signed up",
    "password_changed": "Password changed",
    "password_reset": "Password reset by email link",
    "account_deleted": "Restaurant deleted by its owner",
    "payment": "Payment received",
    "demo_request": "New demo request",
    "login": "Signed in",
    "login_failed": "Wrong password",
    "login_locked": "Sign-in locked (5 wrong passwords)",
    "support_ticket": "New support ticket",
    "ticket_reply": "Reply on a support ticket",
    "help_question": "Quick help couldn't answer",
}
EMAIL_ADMIN = {"account_deleted", "payment", "demo_request", "login_locked", "support_ticket"}


def record(
    db: Session,
    kind: str,
    *,
    org_id: int | None = None,
    restaurant: str | None = None,
    email: str | None = None,
    detail: str | None = None,
    commit: bool = True,
) -> None:
    """Save one event. Never raises: activity logging must not break the action it records."""
    try:
        db.add(ActivityLog(kind=kind, organization_id=org_id, restaurant=restaurant, user_email=email, detail=detail))
        if commit:
            db.commit()
    except Exception:  # pragma: no cover - logging only
        logger.exception("Couldn't record activity %s", kind)
        return
    if kind in EMAIL_ADMIN:
        try:
            send_email(
                [settings.SUPERADMIN_EMAIL],
                f"Virundhu: {LABELS.get(kind, kind)}{f' - {restaurant}' if restaurant else ''}",
                f"{LABELS.get(kind, kind)}\nRestaurant: {restaurant or '-'}\nUser: {email or '-'}\n{detail or ''}\n\n"
                f"Admin console: {settings.APP_URL}/app/admin",
            )
        except Exception:  # pragma: no cover
            logger.warning("Couldn't email the admin about %s", kind)
