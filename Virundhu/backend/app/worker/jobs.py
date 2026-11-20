"""Background jobs run by the ARQ worker."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Review, SourceConnection
from app.services.analysis import analyze_reviews
from app.services.autopilot import send_holding_replies
from app.services.plan_reminders import send_due as send_plan_reminders
from app.services.retention import purge as purge_old_data
from app.services.weekly_summary import send_all as send_weekly_summaries

logger = logging.getLogger(__name__)


def _analyze(org_id: int, review_ids: list[int], batch_id: int | None) -> dict[str, int]:
    with SessionLocal() as db:
        return analyze_reviews(db, org_id, review_ids, batch_id)


async def analyze_job(ctx: dict[str, Any], org_id: int, review_ids: list[int], batch_id: int | None = None) -> dict:
    """Read reviews with the AI, store results and fire instant alerts."""
    stats = await asyncio.to_thread(_analyze, org_id, review_ids, batch_id)
    logger.info("analyze_job org=%s: %s", org_id, stats)
    return stats


def _google_tick() -> None:
    from app.models import Organization
    from app.services import google_reviews

    with SessionLocal() as db:
        conns = db.scalars(
            select(SourceConnection).where(
                SourceConnection.provider == "google", SourceConnection.status == "connected"
            )
        ).all()
        targets = [(c.organization_id, db.get(Organization, c.organization_id)) for c in conns]
    from app.services.autopilot import plan_active

    for org_id, org in targets:
        if org is None or org.is_suspended:
            continue
        with SessionLocal() as db:
            fresh = db.get(Organization, org_id)
            if fresh is None or not plan_active(db, fresh):
                continue  # unpaid: Google reviews wait on Google until the restaurant pays
        with SessionLocal() as db:
            new_ids = google_reviews.sync(db, org_id, org.plan)
            if new_ids:
                analyze_reviews(db, org_id, new_ids)


def _places_tick() -> int:
    """Daily Google check for outlets linked to a Maps listing (Places API). Paid or trial restaurants only."""
    from app.models import Organization, Outlet
    from app.services import google_places
    from app.services.autopilot import plan_active

    if not google_places.enabled():
        return 0
    with SessionLocal() as db:
        due = google_places.due_outlets(db)
    added = 0
    skip: set[int] = set()
    for org_id, outlet_id in due:
        if org_id in skip:
            continue
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            paying = org is not None and (plan_active(db, org) or org.is_demo)
            if not paying or google_places.full_sync_connected(db, org_id):
                skip.add(org_id)
                continue
            outlet = db.get(Outlet, outlet_id)
            if outlet is None:
                continue
            new_ids = google_places.sync_outlet(db, outlet)
            if new_ids:
                added += len(new_ids)
                analyze_reviews(db, org_id, new_ids)
    return added


async def places_tick(ctx: dict[str, Any]) -> None:
    """Hourly: outlets whose daily Google check is due (Places API)."""
    n = await asyncio.to_thread(_places_tick)
    if n:
        logger.info("places_tick: %d new Google reviews", n)


def _accounts_month() -> dict:
    """1st of the month: refresh Dodo fees and payouts, then email last month's accounts Excel."""
    from app.config import settings
    from app.services import books

    with SessionLocal() as db:
        if settings.PAYMENT_PROVIDER == "dodo" and settings.DODO_PAYMENTS_API_KEY:
            try:
                books.sync_dodo(db)
            except Exception:  # noqa: BLE001 - the email still goes with what we have
                logger.exception("Dodo sync before the monthly accounts email failed")
        return books.email_month(db)


async def accounts_month_tick(ctx: dict[str, Any]) -> None:
    """8:20 am India time on the 1st: last month's accounts to the accountant list."""
    r = await asyncio.to_thread(_accounts_month)
    logger.info("Monthly accounts sent: %s", r)


async def google_sync_tick(ctx: dict[str, Any]) -> None:
    """Every 10 minutes: pull new Google reviews for every connected restaurant, read them, alert."""
    await asyncio.to_thread(_google_tick)


def _retry_unread() -> int:
    """Unread reviews: AI failed (last 7 days), or the restaurant hadn't paid yet (last 60 days, read once it pays)."""
    now = datetime.now(UTC)
    with SessionLocal() as db:
        rows = db.execute(
            select(Review.organization_id, Review.id).where(
                ((Review.analysis_status == "needs_review") & (Review.created_at >= now - timedelta(days=7)))
                | ((Review.analysis_status == "pending_quota") & (Review.created_at >= now - timedelta(days=60)))
            )
        ).all()
        from app.models import Organization
        from app.services.autopilot import plan_active

        active = {o.id for o in db.scalars(select(Organization)) if plan_active(db, o) or o.is_demo}
    by_org: dict[int, list[int]] = {}
    for org_id, review_id in rows:
        if org_id in active:
            by_org.setdefault(org_id, []).append(review_id)
    done = 0
    for org_id, ids in by_org.items():
        with SessionLocal() as db:
            done += analyze_reviews(db, org_id, ids)["analyzed"]
    return done


async def retry_unread_tick(ctx: dict[str, Any]) -> None:
    """Every 5 minutes (and at start-up): try again on reviews the AI couldn't read earlier."""
    done = await asyncio.to_thread(_retry_unread)
    if done:
        logger.info("retry_unread: read %d reviews that failed earlier", done)


async def holding_reply_tick(ctx: dict[str, Any]) -> None:
    """Every 15 minutes: safe first replies to unanswered unhappy Google reviews (only where switched on)."""

    def run() -> int:
        with SessionLocal() as db:
            return send_holding_replies(db)

    n = await asyncio.to_thread(run)
    if n:
        logger.info("Sent %s holding replies", n)


async def weekly_summary_tick(ctx: dict[str, Any]) -> None:
    """Monday morning: last week's summary to owners and outlet managers."""

    def run() -> int:
        with SessionLocal() as db:
            return send_weekly_summaries(db)

    await asyncio.to_thread(run)


async def retention_tick(ctx: dict[str, Any]) -> None:
    """Daily: delete personal data that is past the retention period in the Privacy Policy."""

    def run() -> dict[str, int]:
        with SessionLocal() as db:
            return purge_old_data(db)

    counts = await asyncio.to_thread(run)
    if any(counts.values()):
        logger.info("Retention clean-up: %s", counts)


async def plan_reminder_tick(ctx: dict[str, Any]) -> None:
    """Hourly: trial/plan ends in 5/4/3/2/1 days, and 'suspended' when it ends (each once, 9 am to 9 pm IST)."""

    def run() -> int:
        with SessionLocal() as db:
            return send_plan_reminders(db)

    n = await asyncio.to_thread(run)
    if n:
        logger.info("Sent %s plan reminders", n)


async def monthly_report_tick(ctx: dict[str, Any]) -> None:
    """1st of every month: email last month's audit report (Excel) to the platform admin."""
    from zoneinfo import ZoneInfo

    from app.config import settings
    from app.services import monthly_report as mr
    from app.services.emailer import send_email

    def run() -> None:
        today = datetime.now(UTC).astimezone(ZoneInfo(settings.TIMEZONE)).date()
        year, month = mr.previous_month(today)
        with SessionLocal() as db:
            m = mr.build(db, year, month)
        body = (
            f"Virundhu report for {m.label}\n\nRevenue: Rs {m.revenue:,.0f} from {len(m.payments)} payments "
            f"({m.new_paying} new, {m.renewals} renewals).\nOn a paid plan at month end: {m.active_paid_at_end}.\n"
            f"New trials: {len(m.signups)} ({m.converted} paid). Idle: {len(m.idle)}. "
            f"Renewals due next month: {len(m.due_next)}.\n\nThe full report is attached.\n\n- Virundhu"
        )
        send_email(
            [settings.notify_email],
            f"Virundhu monthly report: {m.label}",
            body,
            attachments=[
                (
                    f"virundhu-report-{year:04d}-{month:02d}.xlsx",
                    mr.to_excel(m),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            ],
        )

    await asyncio.to_thread(run)


async def daily_digest_tick(ctx: dict[str, Any]) -> None:
    """9 pm India time: one email to the admin with the day's sign-ins, wrong passwords, payments and tickets."""
    from collections import Counter
    from zoneinfo import ZoneInfo

    from app.config import settings
    from app.models import ActivityLog, SupportTicket
    from app.services.activity import LABELS
    from app.services.emailer import send_email

    def run() -> None:
        tz = ZoneInfo(settings.TIMEZONE)
        since = datetime.now(UTC) - timedelta(days=1)
        with SessionLocal() as db:
            events = list(
                db.scalars(select(ActivityLog).where(ActivityLog.created_at >= since).order_by(ActivityLog.created_at))
            )
            open_tickets = db.query(SupportTicket).filter(SupportTicket.status != "resolved").count()
        if not events and not open_tickets:
            return
        counts = Counter(e.kind for e in events)
        logins = Counter(f"{e.restaurant or 'Admin'} ({e.user_email})" for e in events if e.kind == "login")
        lines = [f"Virundhu: the last 24 hours ({datetime.now(tz):%d %b %Y})", ""]
        lines += [f"{LABELS.get(k, k)}: {n}" for k, n in counts.most_common()]
        lines += ["", f"Open support tickets: {open_tickets}", "", "Who signed in:"]
        lines += [f"  {who}: {n} time(s)" for who, n in logins.most_common()] or ["  nobody"]
        fails = [e for e in events if e.kind in ("login_failed", "login_locked")]
        if fails:
            lines += ["", "Wrong passwords and locks:"]
            lines += [f"  {e.created_at.astimezone(tz):%H:%M} {e.user_email}: {e.detail}" for e in fails[:30]]
        lines += ["", f"Full log (Excel): {settings.APP_URL}/app/admin  (Data tab, Log history)", "- Virundhu"]
        send_email([settings.notify_email], "Virundhu daily summary", "\n".join(lines))

    await asyncio.to_thread(run)


async def agent_tick(ctx: dict[str, Any]) -> None:
    """Every minute: Mani, the lead agent, hands waiting work to Nila (demos) and Tara (support)."""
    from app.database import SessionLocal
    from app.services import agent_team

    def run() -> None:
        with SessionLocal() as db:
            agent_team.run_once(db)

    await asyncio.to_thread(run)
