"""Remind owners before their free trial or paid plan ends: 5, 4, 2 and 1 days before, and once when it
has ended (the account is then suspended until a plan is chosen).

Each reminder goes out once: by email to every owner's sign-in email, by WhatsApp to the owner's number (when
WhatsApp is connected), and to the bell in the app. Sent only between 9 am and 9 pm India time.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Membership, Notification, Organization, PlanReminder, Subscription, User
from app.services import whatsapp
from app.services.emailer import send_email
from app.services.review_requests import normalise_phone

logger = logging.getLogger(__name__)

DAYS_BEFORE = (5, 4, 2, 1)
ENDED = 0
SEND_FROM_HOUR, SEND_UNTIL_HOUR = 9, 21  # local time


def _period_end(db: Session, org: Organization) -> tuple[str, datetime] | None:
    if org.plan == "trial":
        return ("trial", org.trial_ends_at) if org.trial_ends_at else None
    sub = db.scalar(select(Subscription).where(Subscription.organization_id == org.id))
    if sub and sub.current_period_end:
        return "plan", sub.current_period_end
    return None


def due(end: datetime, now: datetime) -> int | None:
    """Which reminder is due now: 4/3/2/1 (days left, by local calendar date), 0 (ended, within 3 days), or None."""
    tz = ZoneInfo(settings.TIMEZONE)
    if end <= now:
        return ENDED if now - end <= timedelta(days=3) else None
    days_left = (end.astimezone(tz).date() - now.astimezone(tz).date()).days
    return days_left if days_left in DAYS_BEFORE else None


def message(kind: str, org_name: str, days_left: int, end_local: date) -> tuple[str, str, str]:
    """(email subject, email body, short WhatsApp line)."""
    what = "free trial" if kind == "trial" else "plan"
    link = f"{settings.APP_URL}/app/billing"
    when = end_local.strftime("%d %b %Y")
    if days_left == ENDED:
        subject = f"Your Virundhu account for {org_name} is suspended"
        line = f"your {what} has ended, so your account is suspended. Your reviews are safe; renew to switch it back on"
        lead = (
            f"Your Virundhu {what} for {org_name} ended on {when}, and it wasn't renewed, so your account is now "
            "suspended.\n\nNothing is deleted. You can still sign in and see every review, but new reviews, urgent "
            "alerts, AI replies and reports are switched off until you renew. Renew any time and everything comes "
            "back exactly as you left it."
        )
        ask = "Renew now (1 to 12 months, priced by outlets):"
    else:
        days = "1 day" if days_left == 1 else f"{days_left} days"
        subject = f"Your Virundhu {what} ends in {days}"
        line = f"your {what} ends in {days}, on {when}. Choose a plan to keep alerts and replies running"
        lead = (
            f"Your Virundhu {what} for {org_name} ends in {days}, on {when}.\n\nIf it isn't renewed by then, your "
            "account will be suspended: your data stays safe, but new reviews, alerts and replies stop."
        )
        ask = "Choose a plan (1 to 12 months, priced by outlets):"
    body = f"{lead}\n\n{ask}\n\n{link}\n\nPlans never renew by themselves, and you only pay when you choose to."
    return subject, body, line


def details(db: Session, org: Organization, kind: str, days_left: int, end_local: date) -> list[tuple[str, str]]:
    from sqlalchemy import func

    from app.models import Outlet

    count = db.scalar(select(func.count()).select_from(Outlet).where(Outlet.organization_id == org.id)) or 0
    outlets = org.paid_outlets if kind == "plan" and org.paid_outlets else count
    rows = [
        ("Restaurant", org.name),
        ("Plan", "Free trial" if kind == "trial" else "Paid plan"),
        ("Outlets", str(outlets or 1)),
        ("Ended on" if days_left == ENDED else "Ends on", end_local.strftime("%d %b %Y")),
        ("Status", "Suspended" if days_left == ENDED else f"{days_left} day{'' if days_left == 1 else 's'} left"),
    ]
    return rows


def send_due(
    db: Session, now: datetime | None = None, force_hours: bool = False, only_org_id: int | None = None
) -> int:
    """Send every reminder that is due. Returns how many organisations were reminded."""
    now = now or datetime.now(UTC)
    tz = ZoneInfo(settings.TIMEZONE)
    local_hour = now.astimezone(tz).hour
    if not force_hours and not (SEND_FROM_HOUR <= local_hour < SEND_UNTIL_HOUR):
        return 0
    sent = 0
    query = select(Organization).where(Organization.is_suspended.is_(False))
    if only_org_id is not None:  # a check run on one restaurant must never touch the others
        query = query.where(Organization.id == only_org_id)
    for org in db.scalars(query):
        found = _period_end(db, org)
        if not found:
            continue
        kind, end = found
        days_left = due(end, now)
        if days_left is None:
            continue
        end_local = end.astimezone(tz).date()
        mark = PlanReminder(organization_id=org.id, period_end=end_local, days_left=days_left, kind=kind)
        db.add(mark)
        try:
            db.flush()
        except IntegrityError:  # already sent this one
            db.rollback()
            continue
        owners = list(
            db.scalars(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(Membership.organization_id == org.id, Membership.role == "owner", User.is_active)
            )
        )
        subject, body, line = message(kind, org.name, days_left, end_local)
        table = details(db, org, kind, days_left, end_local)
        if days_left == ENDED:
            from app.services import activity

            activity.record(
                db,
                "account_suspended",
                org_id=org.id,
                restaurant=org.name,
                email=", ".join(u.email for u in owners) or None,
                detail=f"{'Free trial' if kind == 'trial' else 'Paid plan'} ended {end_local:%d %b %Y}, not renewed. "
                "New reviews, alerts and AI replies are off until they pay.",
                commit=False,
            )
        for u in owners:
            first = (u.full_name or "").split(" ")[0] or "there"
            send_email([u.email], subject, f"Hi {first},\n\n{body}", details=table)
        phone = normalise_phone(org.owner_phone or "")
        if phone:
            whatsapp.send_plan_reminder(phone, org.name, line, f"{settings.APP_URL}/app/billing")
        for u in owners:
            db.add(
                Notification(
                    organization_id=org.id,
                    user_id=u.id,
                    severity="info",
                    title=subject,
                    body=line[:1].upper() + line[1:] + ".",
                )
            )
        db.commit()
        sent += 1
    return sent
