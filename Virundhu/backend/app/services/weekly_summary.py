"""Monday summary for owners and outlet managers: how last week went, per district and outlet, and what to fix first.

Sent by email (and WhatsApp once keys are set). Owners get every outlet; each manager gets only their own outlet.
Restaurants can switch it off in Settings (organizations.weekly_summary).
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Membership, Organization, Outlet, Review, ReviewAnalysis, User
from app.services import reply_promise, whatsapp
from app.services.autopilot import plan_active
from app.services.emailer import send_email
from app.services.review_requests import normalise_phone

logger = logging.getLogger(__name__)

PROBLEM = {
    "food_quality": "food quality",
    "delivery": "delivery",
    "price": "price",
    "staff": "staff behaviour",
    "packaging": "packaging",
    "hygiene": "hygiene",
    "app": "the ordering app",
    "other": "other complaints",
}


@dataclass
class OutletWeek:
    name: str
    district: str
    reviews: int = 0
    stars: float = 0.0
    unhappy: int = 0
    urgent_open: int = 0
    problems: Counter = field(default_factory=Counter)

    @property
    def top_problem(self) -> str | None:
        if not self.problems:
            return None
        key = self.problems.most_common(1)[0][0]
        return PROBLEM.get(key, key)

    def line(self) -> str:
        if not self.reviews:
            return f"{self.name}: no reviews this week"
        bits = [f"{self.reviews} reviews", f"{self.stars:.1f}★"]
        if self.unhappy:
            bits.append(f"{self.unhappy} unhappy")
        if self.urgent_open:
            bits.append(f"{self.urgent_open} urgent still open")
        if self.top_problem:
            bits.append(f"fix first: {self.top_problem}")
        return f"{self.name}: " + ", ".join(bits)


def build(db: Session, org: Organization, today: date | None = None) -> dict[int, OutletWeek]:
    today = today or datetime.now(UTC).date()
    start = today - timedelta(days=7)
    outlets = {
        o.id: OutletWeek(name=o.name, district=o.district or o.city or "Other")
        for o in db.scalars(select(Outlet).where(Outlet.organization_id == org.id, Outlet.is_active))
    }
    rows = db.execute(
        select(Review, ReviewAnalysis)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Review.organization_id == org.id, Review.is_sample.is_(False), Review.review_date >= start)
    ).all()
    sums: dict[int, int] = defaultdict(int)
    for review, analysis in rows:
        week = outlets.get(review.outlet_id)
        if week is None:
            continue
        week.reviews += 1
        sums[review.outlet_id] += review.rating
        if review.rating <= 2 or (analysis and analysis.sentiment == "negative"):
            week.unhappy += 1
            if analysis and analysis.category:
                week.problems[analysis.category] += 1
        if analysis and analysis.urgency == "high" and review.workflow_status in ("new", "in_progress"):
            week.urgent_open += 1
    for oid, total in sums.items():
        outlets[oid].stars = total / outlets[oid].reviews
    return outlets


def render(org: Organization, weeks: list[OutletWeek]) -> str:
    by_district: dict[str, list[OutletWeek]] = defaultdict(list)
    for w in weeks:
        by_district[w.district].append(w)
    total = sum(w.reviews for w in weeks)
    unhappy = sum(w.unhappy for w in weeks)
    lines = [f"Last 7 days at {org.name}: {total} reviews, {unhappy} unhappy.", ""]
    for district in sorted(by_district):
        lines.append(f"{district}:")
        for w in sorted(by_district[district], key=lambda x: (-x.unhappy, x.name)):
            lines.append(f"  - {w.line()}")
        lines.append("")
    worst = max(weeks, key=lambda w: (w.urgent_open, w.unhappy), default=None)
    if worst and (worst.unhappy or worst.urgent_open):
        lines.append(f"Start with {worst.name}" + (f": {worst.top_problem}." if worst.top_problem else "."))
    return "\n".join(lines).strip()


def short(org: Organization, weeks: list[OutletWeek]) -> str:
    total = sum(w.reviews for w in weeks)
    unhappy = sum(w.unhappy for w in weeks)
    worst = max(weeks, key=lambda w: (w.urgent_open, w.unhappy), default=None)
    tail = f" Fix first: {worst.name}, {worst.top_problem}." if worst and worst.top_problem else ""
    return f"{total} reviews, {unhappy} unhappy.{tail}"


def send_all(db: Session, today: date | None = None) -> int:
    sent = 0
    link = f"{settings.APP_URL}/app"
    for org in db.scalars(select(Organization).where(Organization.weekly_summary.is_(True))):
        if not plan_active(db, org):
            continue
        weeks = build(db, org, today)
        if not weeks or not any(w.reviews for w in weeks.values()):
            continue
        owners = [
            u
            for u in db.scalars(
                select(User)
                .join(Membership, Membership.user_id == User.id)
                .where(Membership.organization_id == org.id, Membership.role == "owner", User.is_active)
            )
        ]
        promise = reply_promise.summary_line(reply_promise.stats(db, org, 7))
        body = render(org, list(weeks.values())) + (f"\n\n{promise}" if promise else "")
        body += f"\n\nOpen your dashboard: {link}\n\n- Virundhu"
        if send_email([u.email for u in owners], f"Your week at {org.name}", body):
            sent += 1
        owner_phone = normalise_phone(org.owner_phone or "")
        if owner_phone:
            whatsapp.send_summary(
                owner_phone, org.name, short(org, list(weeks.values())) + (f" {promise}" if promise else ""), link
            )
        for outlet in db.scalars(select(Outlet).where(Outlet.organization_id == org.id, Outlet.is_active)):
            week = weeks.get(outlet.id)
            if not week or not week.reviews:
                continue
            text = render(org, [week]) + f"\n\nOpen your dashboard: {link}\n\n- Virundhu"
            if outlet.manager_email:
                send_email([outlet.manager_email], f"Your week at {org.name}, {outlet.name}", text)
            manager_phone = normalise_phone(outlet.manager_phone or "")
            if manager_phone:
                whatsapp.send_summary(manager_phone, f"{org.name}, {outlet.name}", short(org, [week]), link)
    logger.info("Weekly summaries sent to %s restaurants", sent)
    return sent
