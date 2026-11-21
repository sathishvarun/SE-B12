"""The reply promise: no bad review sits unanswered for more than an hour (the owner can choose 30, 60 or 120 minutes).

A bad review is 1-3 stars or one the AI read as urgent. The clock starts when the review reaches Virundhu (Zomato and
Swiggy have no API, so their reviews arrive by paste, upload or screenshot). Old reviews imported in bulk are history
and never start a clock: only reviews written in the 2 days before they reached Virundhu count.

Reminder ladder for each bad review still waiting:
  half the target   -> that branch's manager (bell, email, WhatsApp)
  the target        -> the owner as well
  double the target -> a last nudge to both
Each step is sent once (reviews.promise_stage). Marking the review Replied, or posting to Google, stops the clock.
"""

import logging
import re
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Membership, Notification, Organization, Outlet, Review, ReviewAnalysis, User
from app.services import whatsapp
from app.services.autopilot import plan_active
from app.services.emailer import send_email

logger = logging.getLogger(__name__)
DEFAULT_TARGET = 60
TARGET_CHOICES = (30, 60, 120)
PENDING = ("new", "in_progress")
FRESH_DAYS = 2


def target_of(org: Organization | None) -> int:
    return (org.reply_target_minutes if org and org.reply_target_minutes else None) or DEFAULT_TARGET


def bad_filter():  # noqa: ANN201
    """1-3 stars, or read as urgent. Use with an outer join on ReviewAnalysis."""
    return or_(Review.rating <= 3, ReviewAnalysis.urgency == "high")


def is_bad(review: Review) -> bool:
    a = review.analysis
    return review.rating <= 3 or bool(a and a.urgency == "high")


def is_fresh(review: Review) -> bool:
    if review.created_at is None:
        return True
    return review.review_date >= review.created_at.date() - timedelta(days=FRESH_DAYS)


def due_at(review: Review, org: Organization | None) -> datetime | None:
    """When the reply is due, or None when this review isn't on the clock."""
    if review.created_at is None or not is_bad(review) or not is_fresh(review):
        return None
    return review.created_at + timedelta(minutes=target_of(org))


def label(minutes: int) -> str:
    if minutes == 60:
        return "1 hour"
    if minutes < 120:
        return f"{minutes} minutes"
    return f"{minutes // 60} hours"


@dataclass
class PromiseStats:
    target_minutes: int
    reminders_on: bool
    bad: int  # bad reviews that reached Virundhu in the period (still-running clocks left out)
    within: int  # answered inside the target
    late: int  # answered after the target
    missed: int  # still waiting, past the target
    pct_within: float | None
    median_minutes: int | None
    waiting: int  # bad reviews waiting for a reply right now
    overdue: int  # of those, past the target


def stats(
    db: Session, org: Organization, days: int = 7, outlet_ids: list[int] | None = None, now: datetime | None = None
) -> PromiseStats:
    now = now or datetime.now(UTC)
    target = target_of(org)
    since = now - timedelta(days=days)
    q = (
        select(Review)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Review.organization_id == org.id, bad_filter(), Review.workflow_status != "ignored")
        .where(Review.created_at >= since - timedelta(days=30))
    )
    if outlet_ids is not None:
        q = q.where(Review.outlet_id.in_(outlet_ids))
    within = late = missed = waiting = overdue = 0
    minutes: list[float] = []
    for r in db.scalars(q):
        if not is_fresh(r):
            continue
        deadline = r.created_at + timedelta(minutes=target)
        if r.workflow_status in PENDING:
            waiting += 1
            if now > deadline:
                overdue += 1
                if r.created_at >= since:
                    missed += 1
            continue
        if r.created_at < since or r.workflow_status != "replied":
            continue
        done = r.replied_at or r.reply_posted_at
        if done is None:
            continue
        took = max((done - r.created_at).total_seconds() / 60, 0)
        minutes.append(took)
        if took <= target:
            within += 1
        else:
            late += 1
    counted = within + late + missed
    return PromiseStats(
        target_minutes=target,
        reminders_on=bool(org.reply_target_minutes),
        bad=counted,
        within=within,
        late=late,
        missed=missed,
        pct_within=round(100 * within / counted, 1) if counted else None,
        median_minutes=round(statistics.median(minutes)) if minutes else None,
        waiting=waiting,
        overdue=overdue,
    )


def summary_line(s: PromiseStats) -> str | None:
    if not s.bad:
        return None
    line = f"Bad reviews answered within {label(s.target_minutes)}: {s.within} of {s.bad} ({s.pct_within:.0f}%)"
    if s.median_minutes is not None:
        line += f", usual reply time {s.median_minutes} min"
    return line + "."


# ---------------------------------------------------------------- reminders


def _phone(raw: str | None) -> str | None:
    if not raw:
        return None
    n = re.sub(r"[\s-]", "", raw)
    n = n if n.startswith("+") else f"+91{n[-10:]}"
    return n if re.fullmatch(r"\+\d{10,15}", n) else None


def _people(db: Session, org: Organization, outlet: Outlet | None) -> tuple[list[User], list[User]]:
    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == org.id, Membership.role.in_(("owner", "manager")), User.is_active)
    ).all()
    owners = [u for u, m in rows if m.role == "owner"]
    managers = [
        u for u, m in rows if m.role == "manager" and (not m.outlet_ids or (outlet and outlet.id in m.outlet_ids))
    ]
    return owners, managers


def _notify(db: Session, org: Organization, users: list[User], review: Review, title: str, body: str) -> None:
    """One bell notification per person per review: a later reminder refreshes it and marks it unread."""
    for u in users:
        db.execute(
            insert(Notification)
            .values(organization_id=org.id, user_id=u.id, review_id=review.id, severity="high", title=title, body=body)
            .on_conflict_do_update(
                constraint="uq_notification_user_review",
                set_={
                    "title": title,
                    "body": body,
                    "severity": "high",
                    "read_at": None,
                    "updated_at": datetime.now(UTC),
                },
            )
        )


def _remind(db: Session, org: Organization, review: Review, stage: int, waited: int) -> None:
    target = target_of(org)
    outlet = db.get(Outlet, review.outlet_id) if review.outlet_id else None
    where = outlet.name if outlet else org.name
    owners, managers = _people(db, org, outlet)
    emails: set[str] = set()
    phones: set[str] = set()
    manager_side = bool(managers or (outlet and (outlet.manager_email or outlet.manager_phone)))
    if stage == 1 or stage == 3 or not manager_side:
        users = managers if manager_side else owners
    else:
        users = []
    if stage >= 2:
        users = list({u.id: u for u in [*users, *owners, *(managers if stage == 3 else [])]}.values())
    if stage in (1, 3) or not manager_side:
        if outlet and outlet.manager_email:
            emails.add(outlet.manager_email.lower())
        if p := _phone(outlet.manager_phone if outlet else None):
            phones.add(p)
    if stage >= 2:
        for n in org.whatsapp_numbers or []:
            if p := _phone(n):
                phones.add(p)
        if p := _phone(org.owner_phone):
            phones.add(p)
    emails.update(u.email.lower() for u in users)

    left = target - waited
    if stage == 1:
        title = f"{left} min left to reply: {review.rating}★ {review.platform.title()} review at {where}"
    elif stage == 2:
        title = f"Past {label(target)}: {review.rating}★ {review.platform.title()} review at {where} has no reply"
    else:
        title = f"Still no reply after {label(waited)}: {review.rating}★ review at {where}"
    text = (review.review_text or "").strip()
    body = (text[:180] + ("…" if len(text) > 180 else "")) or "No text, only the star rating."
    link = f"{settings.APP_URL}/app/inbox?id={review.id}"
    _notify(db, org, users, review, title, body)
    db.commit()
    if emails:
        reply = review.analysis.suggested_reply if review.analysis else None
        msg = (
            f'{title}\n\nWhat the guest wrote:\n"{text or "(no text)"}"\n\n'
            + (f"Reply ready to copy:\n{reply}\n\n" if reply else "")
            + f"Open it, copy the reply, post it on {review.platform.title()}, then tap Replied: {link}\n\n"
            f"Your promise: every bad review answered within {label(target)}.\n- Virundhu"
        )
        send_email(sorted(emails), title, msg)
    if settings.whatsapp_enabled:
        for p in sorted(phones):
            whatsapp.send_alert(p, where, f"{title}. {body}", link)


def run_reminders(db: Session, now: datetime | None = None) -> int:
    """Every 5 minutes: move each waiting bad review up the reminder ladder. Returns reminders sent."""
    now = now or datetime.now(UTC)
    sent = 0
    orgs = db.scalars(
        select(Organization).where(
            Organization.reply_target_minutes.is_not(None),
            Organization.reply_target_minutes > 0,
            Organization.is_suspended.is_(False),
        )
    ).all()
    for org in orgs:
        if not plan_active(db, org):
            continue
        target = target_of(org)
        reviews = db.scalars(
            select(Review)
            .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
            .where(
                Review.organization_id == org.id,
                Review.workflow_status.in_(PENDING),
                Review.is_sample.is_(False),
                Review.promise_stage < 3,
                Review.created_at >= now - timedelta(days=1),
                and_(bad_filter()),
            )
        ).all()
        for r in reviews:
            if not is_fresh(r):
                r.promise_stage = 3
                continue
            waited = int((now - r.created_at).total_seconds() // 60)
            stage = 3 if waited >= 2 * target else 2 if waited >= target else 1 if waited >= target // 2 else 0
            if stage <= r.promise_stage:
                continue
            r.promise_stage = stage
            db.commit()
            try:
                _remind(db, org, r, stage, waited)
                sent += 1
            except Exception:  # one bad address must not stop the rest
                logger.exception("Reply reminder failed for review %s", r.id)
                db.rollback()
        db.commit()
    if sent:
        logger.info("Reply promise: %d reminders sent", sent)
    return sent
