"""Business dates in India time."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings


def today_local() -> date:
    """Today's date in the business time zone (Asia/Kolkata)."""
    return datetime.now(ZoneInfo(settings.TIMEZONE)).date()
