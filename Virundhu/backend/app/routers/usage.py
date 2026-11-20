"""AI token usage from the `ai_usage` ledger.

- Owners: `GET /api/v1/usage/tokens`, their own restaurant only (tokens and reviews read; no rupee cost).
- Admin: `GET /api/v1/admin/tokens` (all restaurants together) and `GET /api/v1/admin/tokens/restaurants`
  (one row per restaurant with tokens, AI cost and what they paid).

Every number is summed in SQL; nothing here is estimated.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.ai.usage import FEATURES
from app.auth.deps import OrgContext, get_org_context, require_superadmin
from app.database import get_db
from app.models import AiUsage, Organization, Payment, UsageCounter
from app.services.plans import limits_for

IST = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/api/v1", tags=["usage"])


class Totals(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    tokens: int = 0
    calls: int = 0
    cost_inr: float = 0


class FeatureRow(Totals):
    feature: str
    label: str


class DayRow(BaseModel):
    day: date
    label: str
    tokens: int = 0
    cost_inr: float = 0


def _ist_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=IST).astimezone(UTC)


def _windows() -> dict[str, datetime | None]:
    today = datetime.now(IST).date()
    month = today.replace(day=1)
    last_month = (month - timedelta(days=1)).replace(day=1)
    return {
        "today": _ist_start(today),
        "this_month": _ist_start(month),
        "last_month": _ist_start(last_month),
        "last_30": _ist_start(today - timedelta(days=29)),
        "all_time": None,
    }


def _totals(
    db: Session, org_id: int | None, since: datetime | None, until: datetime | None = None, *, all_orgs: bool = False
) -> Totals:
    q = select(
        func.coalesce(func.sum(AiUsage.input_tokens), 0),
        func.coalesce(func.sum(AiUsage.output_tokens), 0),
        func.count(AiUsage.id),
        func.coalesce(func.sum(AiUsage.cost_inr), 0),
    )
    if not all_orgs:
        q = q.where(AiUsage.organization_id == org_id)
    if since is not None:
        q = q.where(AiUsage.created_at >= since)
    if until is not None:
        q = q.where(AiUsage.created_at < until)
    tin, tout, calls, cost = db.execute(q).one()
    return Totals(input_tokens=tin, output_tokens=tout, tokens=tin + tout, calls=calls, cost_inr=round(float(cost), 2))


def _by_feature(db: Session, org_id: int | None, since: datetime | None, *, all_orgs: bool = False) -> list[FeatureRow]:
    q = select(
        AiUsage.feature,
        func.sum(AiUsage.input_tokens),
        func.sum(AiUsage.output_tokens),
        func.count(AiUsage.id),
        func.sum(AiUsage.cost_inr),
    ).group_by(AiUsage.feature)
    if not all_orgs:
        q = q.where(AiUsage.organization_id == org_id)
    if since is not None:
        q = q.where(AiUsage.created_at >= since)
    rows = [
        FeatureRow(
            feature=f,
            label=FEATURES.get(f, f),
            input_tokens=i,
            output_tokens=o,
            tokens=i + o,
            calls=c,
            cost_inr=round(float(cost or 0), 2),
        )
        for f, i, o, c, cost in db.execute(q).all()
    ]
    return sorted(rows, key=lambda r: -r.tokens)


def _daily(db: Session, org_id: int | None, days: int, *, all_orgs: bool = False) -> list[DayRow]:
    today = datetime.now(IST).date()
    start = today - timedelta(days=days - 1)
    day = cast(func.timezone("Asia/Kolkata", AiUsage.created_at), Date)
    q = (
        select(day, func.sum(AiUsage.input_tokens + AiUsage.output_tokens), func.sum(AiUsage.cost_inr))
        .where(AiUsage.created_at >= _ist_start(start))
        .group_by(day)
    )
    if not all_orgs:
        q = q.where(AiUsage.organization_id == org_id)
    got = {d: (int(t or 0), float(c or 0)) for d, t, c in db.execute(q).all()}
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        t, c = got.get(d, (0, 0.0))
        out.append(DayRow(day=d, label=d.strftime("%d %b"), tokens=t, cost_inr=round(c, 2)))
    return out


# ---------------------------------------------------------------- owner


class OwnerTokens(BaseModel):
    restaurant: str
    this_month: Totals
    last_month: Totals
    all_time: Totals
    by_feature: list[FeatureRow]
    daily: list[DayRow]
    reviews_read_this_month: int
    reviews_allowed_per_month: int


@router.get("/usage/tokens", response_model=OwnerTokens)
def owner_tokens(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> OwnerTokens:
    """Tokens the AI used for this restaurant. Owners see tokens only; rupee costs are the platform's business."""
    w = _windows()
    org = ctx.org

    def hide_cost(t: Totals) -> Totals:
        return t.model_copy(update={"cost_inr": 0})

    period = datetime.now(UTC).strftime("%Y-%m")
    read = db.scalar(
        select(UsageCounter.reviews_analyzed).where(
            UsageCounter.organization_id == org.id, UsageCounter.period == period
        )
    )
    return OwnerTokens(
        restaurant=org.name,
        this_month=hide_cost(_totals(db, org.id, w["this_month"])),
        last_month=hide_cost(_totals(db, org.id, w["last_month"], w["this_month"])),
        all_time=hide_cost(_totals(db, org.id, None)),
        by_feature=[r.model_copy(update={"cost_inr": 0}) for r in _by_feature(db, org.id, w["this_month"])],
        daily=[d.model_copy(update={"cost_inr": 0}) for d in _daily(db, org.id, 30)],
        reviews_read_this_month=int(read or 0),
        reviews_allowed_per_month=limits_for(org)["reviews_per_month"],
    )


# ---------------------------------------------------------------- admin


class AdminTokens(BaseModel):
    windows: dict[str, Totals]
    by_feature: list[FeatureRow]
    daily: list[DayRow]
    platform_own: Totals  # Virundhu's own work (support drafts, feedback without a restaurant)
    restaurants_using_ai: int
    price_note: str


@router.get("/admin/tokens", response_model=AdminTokens, dependencies=[Depends(require_superadmin)])
def admin_tokens(days: int = Query(30, ge=7, le=90), db: Session = Depends(get_db)) -> AdminTokens:
    """Every token used across Virundhu, per period, per feature and per day."""
    from app.config import settings

    w = _windows()
    windows = {
        "today": _totals(db, None, w["today"], all_orgs=True),
        "this_month": _totals(db, None, w["this_month"], all_orgs=True),
        "last_30": _totals(db, None, w["last_30"], all_orgs=True),
        "all_time": _totals(db, None, None, all_orgs=True),
    }
    using = db.scalar(
        select(func.count(func.distinct(AiUsage.organization_id))).where(AiUsage.organization_id.is_not(None))
    )
    return AdminTokens(
        windows=windows,
        by_feature=_by_feature(db, None, w["this_month"], all_orgs=True),
        daily=_daily(db, None, days, all_orgs=True),
        platform_own=_totals(db, None, None),
        restaurants_using_ai=int(using or 0),
        price_note=(
            f"Cost uses ${settings.LLM_PRICE_INPUT_PER_M_USD:g} per million input tokens and "
            f"${settings.LLM_PRICE_OUTPUT_PER_M_USD:g} per million output tokens at ₹{settings.USD_INR:g} a dollar."
        ),
    )


class RestaurantTokens(BaseModel):
    id: int
    name: str
    plan: str
    paid_outlets: int | None
    tokens_this_month: int
    tokens_last_month: int
    tokens_all_time: int
    calls_all_time: int
    cost_this_month_inr: float
    cost_all_time_inr: float
    paid_all_time_inr: float
    ai_share_percent: float | None  # AI cost as a share of what they paid


@router.get(
    "/admin/tokens/restaurants", response_model=list[RestaurantTokens], dependencies=[Depends(require_superadmin)]
)
def admin_tokens_by_restaurant(db: Session = Depends(get_db)) -> list[RestaurantTokens]:
    """One row per restaurant: tokens and AI cost this month, last month and all time, next to what they paid."""
    w = _windows()
    tokens = AiUsage.input_tokens + AiUsage.output_tokens
    in_month = AiUsage.created_at >= w["this_month"]
    in_last = (AiUsage.created_at >= w["last_month"]) & (AiUsage.created_at < w["this_month"])
    usage = {
        org_id: row
        for org_id, *row in db.execute(
            select(
                AiUsage.organization_id,
                func.coalesce(func.sum(case((in_month, tokens), else_=0)), 0),
                func.coalesce(func.sum(case((in_last, tokens), else_=0)), 0),
                func.coalesce(func.sum(tokens), 0),
                func.count(AiUsage.id),
                func.coalesce(func.sum(case((in_month, AiUsage.cost_inr), else_=0)), 0),
                func.coalesce(func.sum(AiUsage.cost_inr), 0),
            )
            .where(AiUsage.organization_id.is_not(None))
            .group_by(AiUsage.organization_id)
        ).all()
    }
    paid = dict(
        db.execute(
            select(Payment.organization_id, func.sum(Payment.amount_paise - Payment.refunded_paise))
            .where(Payment.status == "paid", Payment.is_test.is_(False))
            .group_by(Payment.organization_id)
        ).all()
    )
    out = []
    for o in db.scalars(select(Organization).where(Organization.is_demo.is_(False))):
        m, last, total, calls, cm, ca = usage.get(o.id, (0, 0, 0, 0, 0, 0))
        paid_inr = round((paid.get(o.id) or 0) / 100, 2)
        out.append(
            RestaurantTokens(
                id=o.id,
                name=o.name,
                plan=o.plan,
                paid_outlets=o.paid_outlets,
                tokens_this_month=int(m),
                tokens_last_month=int(last),
                tokens_all_time=int(total),
                calls_all_time=int(calls),
                cost_this_month_inr=round(float(cm), 2),
                cost_all_time_inr=round(float(ca), 2),
                paid_all_time_inr=paid_inr,
                ai_share_percent=round(float(ca) / paid_inr * 100, 2) if paid_inr else None,
            )
        )
    return sorted(out, key=lambda r: (-r.tokens_this_month, -r.tokens_all_time, r.name.lower()))
