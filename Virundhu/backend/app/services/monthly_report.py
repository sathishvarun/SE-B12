"""The monthly audit report: built automatically, emailed to the admin on the 1st, downloadable for any month.

Sheets: Summary, Payments (every receipt with billing details), Plan mix (1/3/6/9/12 months), Renewals due next month,
Idle accounts (trial or plan ended, not paid), New sign-ups.
"""

import io
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ActivityLog, Organization, Payment, Subscription
from app.services import pricing

DURATIONS = (1, 3, 6, 9, 12)


@dataclass
class Month:
    label: str
    revenue: float = 0
    payments: list[list] = field(default_factory=list)
    new_paying: int = 0
    renewals: int = 0
    mix: dict[int, list[float]] = field(default_factory=lambda: {d: [0, 0.0] for d in DURATIONS})
    active_paid_at_end: int = 0
    signups: list[list] = field(default_factory=list)
    converted: int = 0
    idle: list[list] = field(default_factory=list)
    due_next: list[list] = field(default_factory=list)
    deleted: list[list] = field(default_factory=list)


def _bounds(year: int, month: int) -> tuple[datetime, datetime, datetime]:
    tz = ZoneInfo(settings.TIMEZONE)
    start = datetime.combine(date(year, month, 1), time(), tz)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    end = datetime.combine(nxt, time(), tz)
    after = datetime.combine(date(nxt.year + (nxt.month == 12), nxt.month % 12 + 1, 1), time(), tz)
    return start, end, after


def build(db: Session, year: int, month: int) -> Month:
    start, end, after = _bounds(year, month)
    tz = ZoneInfo(settings.TIMEZONE)
    m = Month(label=start.strftime("%B %Y"))
    names = {o.id: o for o in db.scalars(select(Organization))}
    first_paid: dict[int, datetime] = {}
    for p in db.scalars(select(Payment).where(Payment.status == "paid").order_by(Payment.created_at)):
        first_paid.setdefault(p.organization_id, p.created_at)
        if not (start <= p.created_at < end):
            continue
        amount = p.amount_paise / 100
        org = names.get(p.organization_id)
        m.revenue += amount
        is_new = first_paid[p.organization_id] == p.created_at
        m.new_paying += is_new
        m.renewals += not is_new
        if p.months in m.mix:
            m.mix[p.months][0] += 1
            m.mix[p.months][1] += amount
        m.payments.append(
            [
                p.invoice_no,
                p.created_at.astimezone(tz).replace(tzinfo=None),
                org.name if org else "-",
                p.bill_name,
                p.bill_gstin,
                p.bill_address,
                p.bill_email,
                p.outlets,
                p.months,
                p.period_end.astimezone(tz).date() if p.period_end else None,
                amount,
                "New customer" if is_new else "Renewal",
                p.razorpay_payment_id,
            ]
        )
    for a in db.scalars(
        select(ActivityLog)
        .where(ActivityLog.kind == "account_deleted", ActivityLog.created_at >= start, ActivityLog.created_at < end)
        .order_by(ActivityLog.created_at)
    ):
        m.deleted.append([a.created_at.astimezone(tz).replace(tzinfo=None), a.restaurant, a.user_email, a.detail])
    subs = {s.organization_id: s for s in db.scalars(select(Subscription))}
    for o in names.values():
        if o.is_demo:
            continue
        if start <= o.created_at < end:
            paid = o.id in first_paid and first_paid[o.id] < after
            m.converted += paid
            m.signups.append(
                [
                    o.name,
                    o.city,
                    o.created_at.astimezone(tz).date(),
                    o.trial_ends_at.astimezone(tz).date() if o.trial_ends_at else None,
                    "Paid" if paid else "Not yet",
                ]
            )
        sub = subs.get(o.id)
        paid_end = sub.current_period_end if sub and o.plan != "trial" else None
        if paid_end and paid_end >= end:
            m.active_paid_at_end += 1
        if paid_end and end <= paid_end < after:
            months = 1
            last = db.scalar(
                select(Payment)
                .where(Payment.organization_id == o.id, Payment.status == "paid")
                .order_by(Payment.created_at.desc())
            )
            outlets = (last.outlets if last and last.outlets else None) or o.paid_outlets or 1
            months = (last.months if last and last.months else None) or 1
            m.due_next.append(
                [
                    o.name,
                    paid_end.astimezone(tz).date(),
                    outlets,
                    months,
                    pricing.quote(min(outlets, pricing.MAX_OUTLETS), months).total,
                ]
            )
        ended = paid_end if paid_end else (o.trial_ends_at if o.plan == "trial" else None)
        if ended and ended < end and not o.is_suspended:
            m.idle.append(
                [
                    o.name,
                    o.city,
                    "Paid plan ended" if paid_end else "Trial ended",
                    ended.astimezone(tz).date(),
                    (end.date() - ended.astimezone(tz).date()).days,
                ]
            )
    return m


def to_excel(m: Month) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    head, fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="11132A")

    def sheet(title: str, headers: list[str], rows: list[list]) -> None:
        ws = wb.create_sheet(title)
        ws.append(headers)
        for c in ws[1]:
            c.font, c.fill = head, fill
        for r in rows:
            ws.append(r)
        for i, h in enumerate(headers, 1):
            width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if r[i - 1] is not None])
            ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 46)
        ws.freeze_panes = "A2"

    sheet(
        "Summary",
        ["Item", "Value"],
        [
            ["Month", m.label],
            ["Revenue received (Rs, taxes included)", m.revenue],
            ["Payments", len(m.payments)],
            ["New paying restaurants", m.new_paying],
            ["Renewals", m.renewals],
            ["Restaurants on a paid plan at month end", m.active_paid_at_end],
            ["New sign-ups (free trials started)", len(m.signups)],
            ["...of which have paid", m.converted],
            ["Idle: trial or plan ended and not paid", len(m.idle)],
            ["Renewals due next month", len(m.due_next)],
            ["Accounts deleted this month", len(m.deleted)],
            ["Expected from those renewals (Rs)", sum(r[4] for r in m.due_next)],
            ["Report made", datetime.now(UTC).astimezone(ZoneInfo(settings.TIMEZONE)).strftime("%d %b %Y %H:%M")],
        ],
    )
    sheet(
        "Payments",
        [
            "Receipt no",
            "Paid at",
            "Restaurant",
            "Billed to",
            "GSTIN",
            "Address",
            "Email",
            "Outlets",
            "Months",
            "Covers until",
            "Amount (Rs)",
            "Type",
            "Payment ID",
        ],
        m.payments,
    )
    sheet(
        "Plan mix",
        ["Plan length", "Payments", "Revenue (Rs)"],
        [[f"{d} month{'s' if d > 1 else ''}", v[0], v[1]] for d, v in m.mix.items()],
    )
    sheet("Renewals due next month", ["Restaurant", "Plan ends", "Outlets", "Months", "If renewed (Rs)"], m.due_next)
    sheet("Idle accounts", ["Restaurant", "City", "What ended", "Ended on", "Days idle at month end"], m.idle)
    sheet("Deleted accounts", ["When", "Restaurant", "Owner email", "Details"], m.deleted)
    sheet("New sign-ups", ["Restaurant", "City", "Signed up", "Trial ends", "Paid?"], m.signups)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def previous_month(today: date) -> tuple[int, int]:
    first = today.replace(day=1) - timedelta(days=1)
    return first.year, first.month
