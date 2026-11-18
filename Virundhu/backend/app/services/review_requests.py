"""Ask guests how their food was, on WhatsApp.

Two ways, chosen automatically:
- WhatsApp Cloud API keys set: Virundhu sends the approved template message itself.
- No keys yet: Virundhu returns one-tap wa.me links; the owner taps each and presses Send in their own WhatsApp.

Only a hash of each number is stored, to avoid asking the same guest twice within 30 days.
Guests must have agreed to hear from the restaurant (for example on the bill or while ordering).
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Organization, Outlet, ReviewRequest
from app.services import whatsapp

COOLDOWN_DAYS = 30
MAX_PER_BATCH = 200


def normalise_phone(raw: str) -> str | None:
    """Indian mobile numbers to +91XXXXXXXXXX; other countries need the + already. None if it isn't a mobile."""
    digits = re.sub(r"[^0-9+]", "", raw or "")
    if digits.startswith("+"):
        return digits if re.fullmatch(r"\+\d{10,15}", digits) else None
    digits = digits.lstrip("0")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    return f"+91{digits}" if re.fullmatch(r"[6-9]\d{9}", digits) else None


def phone_hash(org_id: int, phone: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{org_id}:{phone}".encode()).hexdigest()


def message_text(place: str, link: str) -> str:
    return f"Thank you for eating at {place}! How was your food? Tell us in 10 seconds: {link}"


@dataclass
class RequestResult:
    phone: str  # shown masked to the owner
    status: str  # sent | link | skipped_recent | invalid
    link: str | None = None


def send_requests(db: Session, org: Organization, numbers: list[str], outlet_id: int | None) -> list[RequestResult]:
    outlet = db.get(Outlet, outlet_id) if outlet_id else None
    if outlet and outlet.organization_id != org.id:
        outlet = None
    place = f"{org.name}, {outlet.name}" if outlet else org.name
    if not org.feedback_token:
        import secrets

        org.feedback_token = secrets.token_urlsafe(9)
    link = f"{settings.APP_URL}/f/{org.feedback_token}" + (f"?o={outlet.id}" if outlet else "")
    since = datetime.now(UTC) - timedelta(days=COOLDOWN_DAYS)
    recent = set(
        db.scalars(
            select(ReviewRequest.phone_hash).where(
                ReviewRequest.organization_id == org.id, ReviewRequest.created_at >= since
            )
        )
    )
    results: list[RequestResult] = []
    seen: set[str] = set()
    for raw in numbers[:MAX_PER_BATCH]:
        phone = normalise_phone(raw)
        if phone is None:
            if raw.strip():
                results.append(RequestResult(phone=raw.strip()[:20], status="invalid"))
            continue
        masked = f"{phone[:3]} ••••• {phone[-4:]}"
        h = phone_hash(org.id, phone)
        if h in seen or h in recent:
            results.append(RequestResult(phone=masked, status="skipped_recent"))
            continue
        seen.add(h)
        if settings.whatsapp_enabled and whatsapp.send_review_request(phone, place, link):
            channel, item = "whatsapp_api", RequestResult(phone=masked, status="sent")
        else:
            wa = f"https://wa.me/{phone.lstrip('+')}?text={quote(message_text(place, link), safe='')}"
            channel, item = "whatsapp_link", RequestResult(phone=masked, status="link", link=wa)
        db.add(
            ReviewRequest(
                organization_id=org.id, outlet_id=outlet.id if outlet else None, phone_hash=h, channel=channel
            )
        )
        results.append(item)
    db.commit()
    return results
