"""Admin data tools: download customers as Excel, find and delete test accounts, and see the latest backup.

The Excel file holds the platform's own customer records (restaurants, owners, plans, payments, demo requests).
Guest reviews are not included: they belong to each restaurant, and the restaurant exports them from its own Settings.
"""

import io
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.config import settings
from app.database import get_db
from app.models import Lead, Membership, Organization, Outlet, Payment, Review, Subscription, User
from app.services import activity, pricing

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_superadmin)])

BACKUP_DIR = Path(__file__).resolve().parents[3] / "backups"
TEST_DOMAINS = {"test.com", "example.com", "example.org", "example.net", "mailinator.com", "yopmail.com", "test.in"}
TEST_WORDS = re.compile(r"\b(test|testing|dummy|sample|asdf|qwerty|fake)\b|^(test|demo)\d*$", re.I)


def _owner(db: Session, org_id: int) -> User | None:
    return db.scalar(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.organization_id == org_id, Membership.role == "owner")
        .order_by(Membership.id)
    )


def test_reason(org: Organization, owner_email: str | None) -> str | None:
    """Why this restaurant looks like test data, or None if it looks real."""
    if org.is_demo:
        return "Demo restaurant"
    email = (owner_email or "").lower()
    local, _, domain = email.partition("@")
    if domain in TEST_DOMAINS or domain.endswith((".test", ".local", ".example", ".invalid")):
        return f"Test email address ({domain})"
    if TEST_WORDS.search(local.replace(".", " ").replace("_", " ")):
        return "Email looks like a test"
    if TEST_WORDS.search(org.name):
        return "Name looks like a test"
    return None


# ---------- Excel ----------

HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="11132A")


def _sheet(wb: Workbook, title: str, headers: list[str], rows: list[list]) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = HEAD, FILL
    for r in rows:
        ws.append([v.replace(tzinfo=None) if isinstance(v, datetime) else v for v in r])
    for i, h in enumerate(headers, 1):
        width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if r[i - 1] is not None] or [10])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 48)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


@router.get("/export.xlsx")
def export_excel(db: Session = Depends(get_db)) -> StreamingResponse:
    """Every restaurant, owner, plan and payment, plus demo requests, as one Excel file."""
    wb = Workbook()
    wb.remove(wb.active)
    orgs = list(db.scalars(select(Organization).order_by(Organization.created_at)))
    subs = {s.organization_id: s for s in db.scalars(select(Subscription))}
    rest_rows, people_rows = [], []
    for o in orgs:
        owner = _owner(db, o.id)
        outlets = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == o.id)) or 0
        reviews = db.scalar(select(func.count(Review.id)).where(Review.organization_id == o.id)) or 0
        sub = subs.get(o.id)
        rest_rows.append(
            [
                o.id,
                o.name,
                o.city,
                o.business_type,
                o.cuisine,
                outlets,
                o.outlets_declared,
                o.plan,
                o.trial_ends_at,
                sub.current_period_end if sub and o.plan != "trial" else None,
                "Suspended" if o.is_suspended else "Active",
                reviews,
                o.gstin,
                o.head_office,
                owner.full_name if owner else None,
                owner.email if owner else None,
                o.owner_phone,
                o.created_at,
                test_reason(o, owner.email if owner else None) or "",
            ]
        )
    for u in db.scalars(select(User).order_by(User.created_at)):
        names = list(db.scalars(select(Organization.name).join(Membership).where(Membership.user_id == u.id)))
        people_rows.append(
            [
                u.id,
                u.full_name,
                u.email,
                ", ".join(names),
                "Admin" if u.is_superadmin else "Owner/team",
                "Active" if u.is_active else "Blocked",
                u.last_login_at,
                u.created_at,
            ]
        )
    pay_rows = []
    for p, name in db.execute(
        select(Payment, Organization.name)
        .join(Organization, Organization.id == Payment.organization_id)
        .order_by(Payment.created_at)
    ):
        pay_rows.append(
            [p.created_at, name, p.amount_paise / 100, p.currency, p.status, p.razorpay_payment_id, p.invoice_url]
        )
    lead_rows = [
        [x.created_at, x.name, x.restaurant, x.phone, x.email, x.city, x.outlets, x.status, x.message]
        for x in db.scalars(select(Lead).order_by(Lead.created_at))
    ]
    _sheet(
        wb,
        "Restaurants",
        [
            "ID",
            "Restaurant",
            "City",
            "Type",
            "Cuisine",
            "Outlets",
            "Outlets (said at sign-up)",
            "Plan",
            "Trial ends",
            "Paid until",
            "Status",
            "Reviews",
            "GSTIN",
            "Head office",
            "Owner",
            "Owner email",
            "Owner phone",
            "Signed up",
            "Looks like test data",
        ],
        rest_rows,
    )
    _sheet(
        wb, "People", ["ID", "Name", "Email", "Restaurants", "Role", "Status", "Last sign-in", "Created"], people_rows
    )
    _sheet(wb, "Payments", ["Date", "Restaurant", "Amount", "Currency", "Status", "Payment ID", "Invoice"], pay_rows)
    _sheet(
        wb,
        "Demo requests",
        ["Date", "Name", "Restaurant", "Phone", "Email", "City", "Outlets", "Status", "Message"],
        lead_rows,
    )
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="virundhu-customers-{stamp}.xlsx"'},
    )


# ---------- Test accounts ----------


class TestAccount(BaseModel):
    id: int
    name: str
    owner_email: str | None
    reason: str
    reviews: int
    payments: int
    created_at: datetime


@router.get("/test-accounts", response_model=list[TestAccount])
def test_accounts(db: Session = Depends(get_db)) -> list[TestAccount]:
    """Restaurants that look like test data (test emails, demo restaurants, names like 'test')."""
    out = []
    for o in db.scalars(select(Organization).order_by(Organization.created_at.desc())):
        owner = _owner(db, o.id)
        reason = test_reason(o, owner.email if owner else None)
        if not reason:
            continue
        out.append(
            TestAccount(
                id=o.id,
                name=o.name,
                owner_email=owner.email if owner else None,
                reason=reason,
                created_at=o.created_at,
                reviews=db.scalar(select(func.count(Review.id)).where(Review.organization_id == o.id)) or 0,
                payments=db.scalar(select(func.count(Payment.id)).where(Payment.organization_id == o.id)) or 0,
            )
        )
    return out


class DeleteIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=5000)
    confirm: str


@router.post("/test-accounts/delete")
def delete_test_accounts(body: DeleteIn, db: Session = Depends(get_db)) -> dict:

    if body.confirm != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm.")
    allowed = {t.id: t for t in test_accounts(db)}
    refused = [i for i in body.ids if i not in allowed]
    if refused:
        raise HTTPException(
            400,
            "Some of these don't look like test accounts, so they weren't deleted. "
            "A real restaurant can delete itself from its own Settings.",
        )
    deleted = 0
    for org_id in body.ids:
        t = allowed[org_id]
        member_ids = list(db.scalars(select(Membership.user_id).where(Membership.organization_id == org_id)))
        db.execute(delete(Organization).where(Organization.id == org_id))
        for uid in member_ids:
            if not db.scalar(select(Membership.id).where(Membership.user_id == uid)):
                db.execute(delete(User).where(User.id == uid, User.is_superadmin.is_(False)))
        activity.record(
            db,
            "account_deleted",
            org_id=org_id,
            restaurant=t.name,
            email=t.owner_email,
            detail=f"Test data deleted by admin ({t.reason})",
            commit=False,
        )
        deleted += 1
    db.commit()
    return {"deleted": deleted}


# ---------- Backups ----------


class BackupInfo(BaseModel):
    folder: str
    count: int
    latest: str | None
    latest_at: datetime | None
    latest_size_kb: int | None
    hours_ago: float | None


@router.get("/backups", response_model=BackupInfo)
def backups() -> BackupInfo:
    """Where backups are kept and how fresh the newest one is."""
    files = sorted(BACKUP_DIR.glob("virundhu-*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return BackupInfo(
            folder=str(BACKUP_DIR), count=0, latest=None, latest_at=None, latest_size_kb=None, hours_ago=None
        )
    f = files[0]
    at = datetime.fromtimestamp(f.stat().st_mtime, UTC)
    return BackupInfo(
        folder=str(BACKUP_DIR),
        count=len(files),
        latest=f.name,
        latest_at=at,
        latest_size_kb=round(f.stat().st_size / 1024),
        hours_ago=round((datetime.now(UTC) - at).total_seconds() / 3600, 1),
    )


# ---------- Revenue ----------


class MonthRow(BaseModel):
    month: str  # YYYY-MM
    label: str  # "Nov 2026"
    collected: float = 0
    payments: int = 0
    expected: float = 0  # renewals due that month (future months only)


class UpcomingRow(BaseModel):
    org_id: int
    restaurant: str
    owner_email: str | None
    ends_on: date
    outlets: int
    months: int
    amount: float
    kind: str  # renewal | trial


class PaymentRow(BaseModel):
    id: int
    invoice_no: str | None
    bill_name: str | None
    bill_gstin: str | None
    paid_at: datetime
    restaurant: str
    amount: float
    outlets: int | None
    months: int | None
    covers_until: datetime | None


class Revenue(BaseModel):
    all_time: float
    this_month: float
    last_month: float
    this_year: float
    paying_customers: int
    monthly_recurring: float  # what active plans are worth per month
    expected_next_30: float
    expected_next_90: float
    possible_from_trials: float
    months: list[MonthRow]
    upcoming: list[UpcomingRow]
    trials_ending: list[UpcomingRow]
    recent: list[PaymentRow]


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


@router.get("/revenue", response_model=Revenue)
def revenue(db: Session = Depends(get_db)) -> Revenue:
    """Money collected (all time, by month), what active plans are worth, and what's due to come in."""
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(UTC)
    today = now.astimezone(tz).date()
    first = today.replace(day=1)
    keys = [_add_months(first, i) for i in range(-11, 4)]  # 12 past months incl. this one + 3 ahead
    months = {_month_key(k): MonthRow(month=_month_key(k), label=k.strftime("%b %Y")) for k in keys}

    paid = list(
        db.execute(
            select(Payment, Organization.name)
            .join(Organization, Organization.id == Payment.organization_id)
            .where(Payment.status == "paid", Payment.is_test.is_(False))
            .order_by(Payment.created_at.desc())
        )
    )
    all_time = this_month = last_month = this_year = 0.0
    last_first = _add_months(first, -1)
    for p, _name in paid:
        amount = p.amount_paise / 100
        d = p.created_at.astimezone(tz).date()
        all_time += amount
        this_month += amount if d >= first else 0
        last_month += amount if last_first <= d < first else 0
        this_year += amount if d.year == today.year else 0
        row = months.get(_month_key(d))
        if row:
            row.collected += amount
            row.payments += 1

    latest: dict[int, Payment] = {}
    for p, _name in paid:
        latest.setdefault(p.organization_id, p)

    upcoming: list[UpcomingRow] = []
    monthly_recurring = 0.0
    paying = 0
    for org, sub in db.execute(
        select(Organization, Subscription)
        .join(Subscription, Subscription.organization_id == Organization.id)
        .where(
            Organization.plan != "trial", Subscription.current_period_end > now, Organization.is_suspended.is_(False)
        )
    ):
        paying += 1
        last = latest.get(org.id)
        outlets = (last.outlets if last and last.outlets else None) or org.paid_outlets or 1
        months_bought = (last.months if last and last.months else None) or 1
        try:
            q = pricing.quote(outlets, months_bought)
        except pricing.PricingError:
            continue
        monthly_recurring += q.total / (q.access_days / pricing.DAYS_PER_MONTH)
        ends = sub.current_period_end.astimezone(tz).date()
        if sub.current_period_end <= now + timedelta(days=90):
            owner = _owner(db, org.id)
            upcoming.append(
                UpcomingRow(
                    org_id=org.id,
                    restaurant=org.name,
                    owner_email=owner.email if owner else None,
                    ends_on=ends,
                    outlets=outlets,
                    months=months_bought,
                    amount=q.total,
                    kind="renewal",
                )
            )
        row = months.get(_month_key(ends))
        if row and ends >= first:
            row.expected += q.total

    trials: list[UpcomingRow] = []
    for org in db.scalars(
        select(Organization).where(
            Organization.plan == "trial",
            Organization.is_demo.is_(False),
            Organization.is_suspended.is_(False),
            Organization.trial_ends_at > now - timedelta(days=7),
            Organization.trial_ends_at <= now + timedelta(days=7),
        )
    ):
        count = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == org.id)) or 0
        outlets = max(count, org.outlets_declared or 0, 1)
        try:
            q = pricing.quote(min(outlets, pricing.MAX_OUTLETS), 1)
        except pricing.PricingError:
            continue
        owner = _owner(db, org.id)
        trials.append(
            UpcomingRow(
                org_id=org.id,
                restaurant=org.name,
                owner_email=owner.email if owner else None,
                ends_on=org.trial_ends_at.astimezone(tz).date(),
                outlets=outlets,
                months=1,
                amount=q.total,
                kind="trial",
            )
        )

    upcoming.sort(key=lambda r: r.ends_on)
    trials.sort(key=lambda r: r.ends_on)
    in_30, in_90 = today + timedelta(days=30), today + timedelta(days=90)
    return Revenue(
        all_time=all_time,
        this_month=this_month,
        last_month=last_month,
        this_year=this_year,
        paying_customers=paying,
        monthly_recurring=round(monthly_recurring),
        expected_next_30=sum(r.amount for r in upcoming if r.ends_on <= in_30),
        expected_next_90=sum(r.amount for r in upcoming if r.ends_on <= in_90),
        possible_from_trials=sum(r.amount for r in trials),
        months=list(months.values()),
        upcoming=upcoming,
        trials_ending=trials,
        recent=[
            PaymentRow(
                id=p.id,
                invoice_no=p.invoice_no,
                bill_name=p.bill_name,
                bill_gstin=p.bill_gstin,
                paid_at=p.created_at,
                restaurant=name,
                amount=p.amount_paise / 100,
                outlets=p.outlets,
                months=p.months,
                covers_until=p.period_end,
            )
            for p, name in paid[:25]
        ],
    )


# ---------- Monthly audit report ----------


@router.get("/reports/monthly.xlsx")
def monthly_report(month: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """The audit report for one month (YYYY-MM). The same file is emailed to the admin automatically on the 1st."""
    from app.services import monthly_report as mr

    try:
        year, mon = (int(x) for x in month.split("-"))
        date(year, mon, 1)
    except ValueError as exc:
        raise HTTPException(400, "Use the month as YYYY-MM, for example 2026-11.") from exc
    data = mr.to_excel(mr.build(db, year, mon))
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="virundhu-report-{year:04d}-{mon:02d}.xlsx"'},
    )


@router.get("/plan-mix")
def plan_mix(db: Session = Depends(get_db)) -> dict:
    """Restaurants on a paid plan right now, by plan length (from their latest payment)."""
    now = datetime.now(UTC)
    counts = {str(d): 0 for d in (1, 3, 6, 9, 12)}
    for org, _sub in db.execute(
        select(Organization, Subscription)
        .join(Subscription, Subscription.organization_id == Organization.id)
        .where(Organization.plan != "trial", Subscription.current_period_end > now)
    ):
        last = db.scalar(
            select(Payment)
            .where(Payment.organization_id == org.id, Payment.status == "paid")
            .order_by(Payment.created_at.desc())
        )
        key = str(last.months if last and last.months else 1)
        if key in counts:
            counts[key] += 1
    trials = (
        db.scalar(
            select(func.count(Organization.id)).where(
                Organization.plan == "trial", Organization.is_demo.is_(False), Organization.trial_ends_at > now
            )
        )
        or 0
    )
    return {"by_months": counts, "on_trial": trials}


# ---------- Log history ----------


@router.get("/logs.xlsx")
def logs_excel(days: int = 30, kind: str | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    """Every recorded event (sign-ins, wrong passwords, payments, deletions, tickets) for the last N days."""
    from app.models import ActivityLog
    from app.services.activity import LABELS

    since = datetime.now(UTC) - timedelta(days=max(1, min(days, 730)))
    q = select(ActivityLog).where(ActivityLog.created_at >= since).order_by(ActivityLog.created_at.desc())
    if kind:
        q = q.where(ActivityLog.kind == kind)
    tz = ZoneInfo(settings.TIMEZONE)
    rows = [
        [
            a.created_at.astimezone(tz).replace(tzinfo=None),
            LABELS.get(a.kind, a.kind),
            a.restaurant,
            a.user_email,
            a.detail,
        ]
        for a in db.scalars(q)
    ]
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "Log history", ["When (India time)", "Event", "Restaurant", "Email", "Details"], rows)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="virundhu-logs-last-{days}-days.xlsx"'},
    )
