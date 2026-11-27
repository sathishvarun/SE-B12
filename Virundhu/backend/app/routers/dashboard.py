"""Dashboard numbers. Every count is calculated in SQL, never by the AI."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context
from app.config import settings
from app.database import get_db
from app.models import Outlet, Review, ReviewAnalysis
from app.services import reply_promise
from app.services.dates import today_local

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
PENDING = ("new", "in_progress")


class Kpis(BaseModel):
    reviews_week: int
    reviews_prev_week: int
    positive_pct: float
    positive_pct_prev: float
    avg_rating: float | None
    avg_rating_prev: float | None
    urgent_pending: int
    reply_rate_30d: float


class TrendPoint(BaseModel):
    week_start: date
    positive: int
    neutral: int
    negative: int


class CategoryCount(BaseModel):
    category: str
    count: int


class OutletRow(BaseModel):
    outlet_id: int
    name: str
    city: str | None
    reviews: int
    avg_rating: float | None
    negative_pct: float
    urgent_pending: int


class PlatformCount(BaseModel):
    platform: str
    count: int


class UrgentItem(BaseModel):
    id: int
    platform: str
    rating: int
    review_date: date
    review_text: str
    summary: str | None
    category: str | None
    outlet_name: str | None


class Promise(BaseModel):
    """Reply promise: bad reviews (1-3 stars or urgent) answered within the target, last 7 days."""

    target_minutes: int
    reminders_on: bool
    bad: int
    within: int
    late: int
    missed: int
    pct_within: float | None
    median_minutes: int | None
    waiting: int
    overdue: int
    days: int = 7


class Overview(BaseModel):
    kpis: Kpis
    promise: Promise | None = None
    trend: list[TrendPoint]
    categories: list[CategoryCount]
    outlets: list[OutletRow]
    platforms: list[PlatformCount]
    urgent: list[UrgentItem]
    as_of: date


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


@router.get("/overview", response_model=Overview)
def overview(
    outlet_id: int | None = None, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> Overview:
    """KPIs, 8-week trend, complaint categories, outlet league, platforms and urgent reviews."""
    org = ctx.org.id
    today = today_local()
    week_from, prev_from, d30 = today - timedelta(days=6), today - timedelta(days=13), today - timedelta(days=29)

    def scoped(stmt):  # noqa: ANN001, ANN202
        stmt = stmt.where(Review.organization_id == org)
        if ctx.outlet_ids is not None:  # outlet managers/staff see only their outlets
            stmt = stmt.where(Review.outlet_id.in_(ctx.outlet_ids))
        return stmt.where(Review.outlet_id == outlet_id) if outlet_id else stmt

    joined = select().select_from(Review).outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)

    def window(start: date, end: date) -> tuple[int, int, float | None]:
        row = db.execute(
            scoped(
                joined.add_columns(
                    func.count(Review.id),
                    func.count(case((ReviewAnalysis.sentiment == "positive", 1))),
                    func.avg(Review.rating),
                ).where(Review.review_date.between(start, end))
            )
        ).one()
        return row[0], row[1], (round(float(row[2]), 2) if row[2] is not None else None)

    n_w, pos_w, avg_w = window(week_from, today)
    n_p, pos_p, avg_p = window(prev_from, week_from - timedelta(days=1))
    urgent_pending = (
        db.scalar(
            scoped(
                joined.add_columns(func.count(Review.id)).where(
                    ReviewAnalysis.urgency == "high", Review.workflow_status.in_(PENDING)
                )
            )
        )
        or 0
    )
    r30 = db.execute(
        scoped(
            joined.add_columns(func.count(Review.id), func.count(case((Review.workflow_status == "replied", 1)))).where(
                Review.review_date >= d30
            )
        )
    ).one()

    week = func.date_trunc("week", Review.review_date)
    trend_rows = db.execute(
        scoped(
            joined.add_columns(week, ReviewAnalysis.sentiment, func.count(Review.id)).where(
                Review.review_date >= today - timedelta(weeks=8)
            )
        )
        .group_by(week, ReviewAnalysis.sentiment)
        .order_by(week)
    ).all()
    buckets: dict[date, dict[str, int]] = {}
    for wk, sentiment, count in trend_rows:
        d = wk.date() if hasattr(wk, "date") else wk
        buckets.setdefault(d, {"positive": 0, "neutral": 0, "negative": 0})
        if sentiment in buckets[d]:
            buckets[d][sentiment] += count
    trend = [TrendPoint(week_start=k, **v) for k, v in sorted(buckets.items())]

    cat_rows = db.execute(
        scoped(
            joined.add_columns(ReviewAnalysis.category, func.count(Review.id)).where(
                Review.review_date >= d30, ReviewAnalysis.sentiment != "positive"
            )
        )
        .group_by(ReviewAnalysis.category)
        .order_by(func.count(Review.id).desc())
    ).all()

    out_rows = db.execute(
        select(
            Outlet.id,
            Outlet.name,
            Outlet.city,
            func.count(Review.id),
            func.avg(Review.rating),
            func.count(case((ReviewAnalysis.sentiment == "negative", 1))),
            func.count(case(((ReviewAnalysis.urgency == "high") & Review.workflow_status.in_(PENDING), 1))),
        )
        .select_from(Outlet)
        .outerjoin(Review, (Review.outlet_id == Outlet.id) & (Review.review_date >= d30))
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(
            Outlet.organization_id == org,
            Outlet.is_active.is_(True),
            Outlet.id.in_(ctx.outlet_ids) if ctx.outlet_ids is not None else True,
        )
        .group_by(Outlet.id)
        .order_by(Outlet.name)
    ).all()

    plat_rows = db.execute(
        scoped(select(Review.platform, func.count(Review.id)).where(Review.review_date >= d30))
        .group_by(Review.platform)
        .order_by(func.count(Review.id).desc())
    ).all()

    names = {o.id: o.name for o in db.scalars(select(Outlet).where(Outlet.organization_id == org))}
    urgent_q = select(Review, ReviewAnalysis).join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
    urgent_rows = db.execute(
        scoped(urgent_q.where(ReviewAnalysis.urgency == "high", Review.workflow_status.in_(PENDING)))
        .order_by(Review.review_date.desc(), Review.id.desc())
        .limit(6)
    ).all()

    return Overview(
        kpis=Kpis(
            reviews_week=n_w,
            reviews_prev_week=n_p,
            positive_pct=_pct(pos_w, n_w),
            positive_pct_prev=_pct(pos_p, n_p),
            avg_rating=avg_w,
            avg_rating_prev=avg_p,
            urgent_pending=urgent_pending,
            reply_rate_30d=_pct(r30[1], r30[0]),
        ),
        promise=Promise(**vars(reply_promise.stats(db, ctx.org, 7, [outlet_id] if outlet_id else ctx.outlet_ids))),
        trend=trend,
        categories=[CategoryCount(category=c or "other", count=n) for c, n in cat_rows],
        outlets=[
            OutletRow(
                outlet_id=i,
                name=n,
                city=c,
                reviews=t,
                avg_rating=round(float(a), 2) if a else None,
                negative_pct=_pct(neg, t),
                urgent_pending=u,
            )
            for i, n, c, t, a, neg, u in out_rows
        ],
        platforms=[PlatformCount(platform=p, count=n) for p, n in plat_rows],
        urgent=[
            UrgentItem(
                id=r.id,
                platform=r.platform,
                rating=r.rating,
                review_date=r.review_date,
                review_text=r.review_text,
                summary=a.summary,
                category=a.category,
                outlet_name=names.get(r.outlet_id or 0),
            )
            for r, a in urgent_rows
        ],
        as_of=today,
    )


# ---------------- At a glance: the owner's / CEO's one screen ----------------


class Period(BaseModel):
    """Reviews written in a period, by how guests felt, and replies sent in it."""

    reviews: int
    positive: int
    neutral: int
    negative: int
    avg_rating: float | None
    replied: int


class SplitRow(BaseModel):
    key: str
    this_month: int
    last_month: int
    positive: int
    negative: int
    avg_rating: float | None


class Summary(BaseModel):
    today: Period
    waiting: int  # reviews still waiting for a reply (any age)
    this_month: Period
    last_month_to_date: Period  # 1st to the same day last month: a fair comparison mid-month
    last_month: Period
    by_platform: list[SplitRow]
    by_outlet: list[SplitRow]
    month_label: str
    last_month_label: str
    as_of: date


def _month_bounds(today: date) -> tuple[date, date, date, date]:
    first = today.replace(day=1)
    last_end = first - timedelta(days=1)
    last_first = last_end.replace(day=1)
    same_day = last_first.replace(day=min(today.day, last_end.day))
    return first, last_first, last_end, same_day


@router.get("/summary", response_model=Summary)
def summary(
    outlet_id: int | None = None, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> Summary:
    """At a glance: today, this month vs last month, by platform and by branch. Counted in SQL, never by the AI."""
    org = ctx.org.id
    today = today_local()
    first, last_first, last_end, same_day = _month_bounds(today)
    tz = settings.TIMEZONE

    def scoped(stmt):  # noqa: ANN001, ANN202
        stmt = stmt.where(Review.organization_id == org)
        if ctx.outlet_ids is not None:
            stmt = stmt.where(Review.outlet_id.in_(ctx.outlet_ids))
        return stmt.where(Review.outlet_id == outlet_id) if outlet_id else stmt

    base = select().select_from(Review).outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
    sent = ReviewAnalysis.sentiment
    feel = [
        func.count(Review.id),
        func.count(case((sent == "positive", 1))),
        func.count(case((sent == "neutral", 1))),
        func.count(case((sent == "negative", 1))),
        func.avg(Review.rating),
    ]
    replied_day = func.date(func.timezone(tz, Review.replied_at))

    def period(start: date, end: date) -> Period:
        n, pos, neu, neg, avg = db.execute(
            scoped(base.add_columns(*feel).where(Review.review_date.between(start, end)))
        ).one()
        replied = db.scalar(
            scoped(select(func.count(Review.id)).where(Review.replied_at.is_not(None), replied_day.between(start, end)))
        )
        return Period(
            reviews=n,
            positive=pos,
            neutral=neu,
            negative=neg,
            avg_rating=round(float(avg), 2) if avg is not None else None,
            replied=replied or 0,
        )

    waiting = db.scalar(scoped(select(func.count(Review.id)).where(Review.workflow_status.in_(PENDING)))) or 0

    def split(col):  # noqa: ANN001, ANN202
        rows = db.execute(
            scoped(
                base.add_columns(
                    col,
                    func.count(case((Review.review_date >= first, 1))),
                    func.count(case((Review.review_date.between(last_first, last_end), 1))),
                    func.count(case(((Review.review_date >= first) & (sent == "positive"), 1))),
                    func.count(case(((Review.review_date >= first) & (sent == "negative"), 1))),
                    func.avg(case((Review.review_date >= first, Review.rating))),
                ).where(Review.review_date.between(last_first, today))
            ).group_by(col)
        ).all()
        out = [
            SplitRow(
                key=str(k or "Not set"),
                this_month=t,
                last_month=lm,
                positive=p,
                negative=ng,
                avg_rating=round(float(a), 2) if a is not None else None,
            )
            for k, t, lm, p, ng, a in rows
        ]
        return sorted(out, key=lambda r: (-r.this_month, -r.last_month, r.key))

    outlet_name = func.coalesce(Outlet.name, "Not set")
    rows = db.execute(
        scoped(
            base.outerjoin(Outlet, Outlet.id == Review.outlet_id)
            .add_columns(
                outlet_name,
                func.count(case((Review.review_date >= first, 1))),
                func.count(case((Review.review_date.between(last_first, last_end), 1))),
                func.count(case(((Review.review_date >= first) & (sent == "positive"), 1))),
                func.count(case(((Review.review_date >= first) & (sent == "negative"), 1))),
                func.avg(case((Review.review_date >= first, Review.rating))),
            )
            .where(Review.review_date.between(last_first, today))
        ).group_by(outlet_name)
    ).all()
    by_outlet = sorted(
        [
            SplitRow(
                key=k,
                this_month=t,
                last_month=lm,
                positive=p,
                negative=ng,
                avg_rating=round(float(a), 2) if a is not None else None,
            )
            for k, t, lm, p, ng, a in rows
        ],
        key=lambda r: (-r.this_month, -r.last_month, r.key),
    )
    return Summary(
        today=period(today, today),
        waiting=waiting,
        this_month=period(first, today),
        last_month_to_date=period(last_first, same_day),
        last_month=period(last_first, last_end),
        by_platform=split(Review.platform),
        by_outlet=by_outlet,
        month_label=first.strftime("%B %Y"),
        last_month_label=last_first.strftime("%B %Y"),
        as_of=today,
    )
