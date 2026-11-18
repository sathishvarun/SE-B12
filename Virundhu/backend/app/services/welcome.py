"""Welcome email at sign-up: the details given, trial start and end dates, a confirm-email link and the plans link."""

import hashlib
import hmac
from zoneinfo import ZoneInfo

from app.config import settings
from app.models import Organization, User
from app.services.emailer import branded_html, closing_text, send_email


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
    parts = (user.full_name or "").split()
    details = [
        ("First name", parts[0] if parts else ""),
        ("Last name", " ".join(parts[1:]) or "-"),
        ("Email", user.email),
        *([("Phone", phone)] if phone else []),
        ("Restaurant", org.name),
        *([("City", org.city)] if org.city else []),
        *([("Outlets", str(outlets))] if outlets else []),
        *([("Free trial", f"{start:%d %b %Y} to {end:%d %b %Y}")] if start and end else []),
    ]
    lines = [
        f"Welcome to Virundhu, {first}!",
        "",
        f"Thank you for registering {org.name} with Virundhu. Your account is ready, and every review your guests "
        "write will now be read, sorted and answered in one place. Here are the details you gave us:",
        "",
    ]
    if not user.is_verified:
        lines += ["Please confirm this is your email address:", "", confirm, ""]
    lines += [
        "Your 14-day free trial includes everything, and no card is needed. We'll remind you 4, 3, 2 and 1 days "
        "before it ends. Plans never renew by themselves.",
        "",
        "To keep Virundhu after the trial, choose a plan (1 to 12 months, priced by outlets):",
        "",
        plans,
        "",
        "Questions? Just reply to this email. A real person reads every one.",
    ]
    subject = f"Welcome to Virundhu, {first}: your free trial is on"
    body = "\n".join(lines)
    listed = "\n".join(f"{k}: {v}" for k, v in details)
    text = body.replace("details you gave us:", f"details you gave us:\n\n{listed}", 1) + closing_text(subject)
    return send_email([user.email], subject, text, html=branded_html(subject, body, details))
