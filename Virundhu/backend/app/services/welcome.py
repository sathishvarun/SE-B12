"""Welcome email at sign-up: the details given, trial start and end dates, a confirm-email link and the plans link."""

import hashlib
import hmac
from zoneinfo import ZoneInfo

from app.config import settings
from app.models import Organization, User
from app.services.emailer import send_email


def verify_token(user: User) -> str:
    sig = hmac.new(settings.SECRET_KEY.encode(), f"verify:{user.id}:{user.email}".encode(), hashlib.sha256).hexdigest()
    return f"{user.id}.{sig[:40]}"


def check_token(token: str, user: User) -> bool:
    return hmac.compare_digest(token, verify_token(user))


def send_welcome(user: User, org: Organization, phone: str | None = None, outlets: int | None = None) -> bool:
    tz = ZoneInfo(settings.TIMEZONE)
    start = org.created_at.astimezone(tz) if org.created_at else None
    end = org.trial_ends_at.astimezone(tz) if org.trial_ends_at else None
    first = (user.full_name or "").split(" ")[0] or "there"
    confirm = f"{settings.API_URL}/api/v1/auth/verify-email?token={verify_token(user)}"
    plans = f"{settings.APP_URL}/app/billing"
    details = [
        f"Name: {user.full_name}",
        f"Email: {user.email}",
        *([f"Phone: {phone}"] if phone else []),
        f"Restaurant: {org.name}",
        *([f"City: {org.city}"] if org.city else []),
        *([f"Outlets: {outlets}"] if outlets else []),
    ]
    body = "\n".join(
        [
            f"Hi {first},",
            "",
            "Welcome to Virundhu. Your account is ready. These are the details you gave us:",
            "",
            *details,
            "",
            f"Your 14-day free trial started on {start:%d %b %Y} and ends on {end:%d %b %Y}." if start and end else "",
            "Everything is included during the trial, and no card is needed.",
            "",
            *([] if user.is_verified else [f"Please confirm this is your email address: {confirm}", ""]),
            f"To keep Virundhu after the trial, choose a plan here (1 to 12 months, priced by outlets): {plans}",
            "We'll remind you 4, 3, 2 and 1 days before the trial ends. Plans never renew by themselves.",
            "",
            "Questions? Just reply to this email.",
            "",
            "- Virundhu",
        ]
    )
    return send_email([user.email], f"Welcome to Virundhu, {first}: your free trial is on", body)
