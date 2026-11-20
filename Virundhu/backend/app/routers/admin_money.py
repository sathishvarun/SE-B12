"""Admin → Money → Payments and refunds: what came in and went out, per day, per week, per month and all time.

All numbers are computed here from `payments` and `refunds` (rupees, India time). Test-mode payments are left out unless
asked for, so practice payments never look like revenue.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.config import settings
from app.database import get_db
from app.models import Organization, Payment, Refund

router = APIRouter(prefix="/api/v1/admin/money", tags=["admin"], dependencies=[Depends(require_superadmin)])


class Window(BaseModel):
    key: str
    label: str
    collected: float = 0
    refunded: float = 0
    net: float = 0
    payments: int = 0
    refunds: int = 0


class Bucket(BaseModel):
    start: date
    label: str
    collected: float = 0
    refunded: float = 0
    net: float = 0
    payments: int = 0
    refunds: int = 0


class PaymentLine(BaseModel):
    id: int
    paid_at: datetime
    restaurant: str
    amount: float
    refunded: float
    status: str  # paid | partly refunded | refunded
    invoice_no: str | None
    outlets: int | None
    months: int | None
    provider_id: str
    is_test: bool


class RefundLine(BaseModel):
    refund_id: str
    refunded_at: datetime
    restaurant: str | None
    amount: float
    status: str
    reason: str | None
    is_test: bool


class Money(BaseModel):
    mode: str
    include_test: bool
    hidden_test_payments: int
    windows: list[Window]
    daily: list[Bucket]
    weekly: list[Bucket]
    payments: list[PaymentLine]
    refunds: list[RefundLine]


def _rs(paise: int) -> float:
    return round(paise / 100, 2)


@router.get("", response_model=Money)
def money(days: int = 30, include_test: bool = False, db: Session = Depends(get_db)) -> Money:
    """Totals for today, this/last week, this month, last 30 days and all time, plus daily and weekly series."""
    tz = ZoneInfo(settings.TIMEZONE)
    today = datetime.now(UTC).astimezone(tz).date()
    days = max(7, min(days, 120))

    pays = list(db.execute(
        select(Payment, Organization.name).outerjoin(Organization, Organization.id == Payment.organization_id)
        .where(Payment.status == "paid").order_by(Payment.created_at.desc())
    ))
    refs = list(db.execute(
        select(Refund, Organization.name).outerjoin(Organization, Organization.id == Refund.organization_id)
        .order_by(Refund.refunded_at.desc())
    ))
    hidden = sum(1 for p, _ in pays if p.is_test) if not include_test else 0
    pays = [(p, n) for p, n in pays if include_test or not p.is_test]
    refs = [(r, n) for r, n in refs if include_test or not r.is_test]
    ok_refs = [(r, n) for r, n in refs if r.status == "succeeded"]

    week_start = today - timedelta(days=today.weekday())  # Monday
    windows = [
        ("today", "Today", today, today),
        ("yesterday", "Yesterday", today - timedelta(days=1), today - timedelta(days=1)),
        ("this_week", "This week", week_start, today),
        ("last_week", "Last week", week_start - timedelta(days=7), week_start - timedelta(days=1)),
        ("this_month", "This month", today.replace(day=1), today),
        ("last_30", "Last 30 days", today - timedelta(days=29), today),
        ("all_time", "All time", date(2000, 1, 1), today),
    ]
    out: list[Window] = []
    for key, label, a, b in windows:
        w = Window(key=key, label=label)
        for p, _ in pays:
            if a <= p.created_at.astimezone(tz).date() <= b:
                w.collected += p.amount_paise / 100
                w.payments += 1
        for r, _ in ok_refs:
            if a <= r.refunded_at.astimezone(tz).date() <= b:
                w.refunded += r.amount_paise / 100
                w.refunds += 1
        w.collected, w.refunded = round(w.collected, 2), round(w.refunded, 2)
        w.net = round(w.collected - w.refunded, 2)
        out.append(w)

    def series(starts: list[date], span: int, fmt: str) -> list[Bucket]:
        buckets = [Bucket(start=s, label=s.strftime(fmt).replace(" 0", " ")) for s in starts]
        index = {s: b for s, b in zip(starts, buckets, strict=True)}

        def find(d: date) -> Bucket | None:
            for s in starts:
                if s <= d < s + timedelta(days=span):
                    return index[s]
            return None

        for p, _ in pays:
            if bk := find(p.created_at.astimezone(tz).date()):
                bk.collected += p.amount_paise / 100
                bk.payments += 1
        for r, _ in ok_refs:
            if bk := find(r.refunded_at.astimezone(tz).date()):
                bk.refunded += r.amount_paise / 100
                bk.refunds += 1
        for bk in buckets:
            bk.collected, bk.refunded = round(bk.collected, 2), round(bk.refunded, 2)
            bk.net = round(bk.collected - bk.refunded, 2)
        return buckets

    daily = series([today - timedelta(days=i) for i in range(days - 1, -1, -1)], 1, "%d %b")
    weekly = series([week_start - timedelta(weeks=i) for i in range(11, -1, -1)], 7, "%d %b")

    lines = [
        PaymentLine(
            id=p.id, paid_at=p.created_at, restaurant=name or "Deleted restaurant", amount=_rs(p.amount_paise),
            refunded=_rs(p.refunded_paise),
            status="refunded" if p.refunded_paise >= p.amount_paise and p.refunded_paise else
            "partly refunded" if p.refunded_paise else "paid",
            invoice_no=p.invoice_no, outlets=p.outlets, months=p.months, provider_id=p.razorpay_payment_id,
            is_test=p.is_test,
        )
        for p, name in pays[:200]
    ]
    refund_lines = [
        RefundLine(refund_id=r.refund_id, refunded_at=r.refunded_at, restaurant=name, amount=_rs(r.amount_paise),
                   status=r.status, reason=r.reason, is_test=r.is_test)
        for r, name in refs[:100]
    ]
    mode = "live" if settings.DODO_PAYMENTS_ENVIRONMENT == "live_mode" else "test"
    return Money(mode=mode, include_test=include_test, hidden_test_payments=hidden, windows=out, daily=daily,
                 weekly=weekly, payments=lines, refunds=refund_lines)


@router.post("/sync")
def sync(db: Session = Depends(get_db)) -> dict:
    """Ask Dodo for refunds now (webhooks normally do this within seconds)."""
    if settings.PAYMENT_PROVIDER != "dodo" or not settings.payments_enabled:
        raise HTTPException(400, "Online payments aren't switched on yet.")
    from app.services import dodo_billing

    try:
        added = dodo_billing.sync_refunds(db)
    except Exception as exc:
        raise HTTPException(502, "Couldn't reach Dodo just now. Try again in a minute.") from exc
    return {"new_refunds": added, "message": f"Checked Dodo. {added} new refund{'s' if added != 1 else ''} found."}
