"""Admin → Accounts: audit-ready sales, refund and GST reports by month, quarter or financial year (April to March).

Everything is computed here from `payments`, `refunds` and `activity_log` (India time). Test-mode payments are left out
and counted separately, so practice payments never reach the books.

Two kinds of sale are kept apart because they are taxed differently:
- Online payments through Dodo Payments: Dodo is the merchant of record. It sells to the customer, issues the tax
  invoice and handles GST on that sale; Virundhu's income is Dodo's payout. Listed for reconciliation with Dodo.
- Bank transfers: Virundhu (through the GST-registered parent company) sells directly, so the GST inside the price is
  split here into taxable value and CGST + SGST (same state) or IGST (other state), for GSTR-1 and GSTR-3B.
Prices include GST at `GST_RATE_PERCENT`. Whether and how to file is the accountant's decision; these sheets give them
every number with its source.
"""

import io
import re
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.config import settings
from app.database import get_db
from app.models import ActivityLog, Organization, Payment, Refund

router = APIRouter(prefix="/api/v1/admin/accounts", tags=["admin"], dependencies=[Depends(require_superadmin)])
IST = ZoneInfo("Asia/Kolkata")

STATES = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}
AUDIT_KINDS = {
    "payment",
    "refund",
    "renewal",
    "account_reactivated",
    "account_deleted",
    "account_suspended",
    "bank_transfer_request",
    "signup",
    "trial_ended",
    "password_changed",
    "password_reset",
}
PERIOD = re.compile(r"^(?:(?P<m>\d{4}-\d{2})|(?P<q>\d{4}-Q[1-4])|FY(?P<fy>\d{4}))$")
TWO = Decimal("0.01")


def _seller_state() -> str:
    g = settings.PARENT_GSTIN or ""
    return g[:2] if g[:2] in STATES else settings.SELLER_STATE_CODE


def period_range(value: str) -> tuple[date, date, str]:
    """'2026-11' (month), '2026-Q3' (Indian FY quarter: Q1 = Apr-Jun of FY starting that year), 'FY2026' (Apr 2026 -
    Mar 2027). Returns (first day, day after the last day, label)."""
    m = PERIOD.match(value or "")
    if not m:
        raise HTTPException(400, "Choose a month (2026-11), a quarter (2026-Q3) or a financial year (FY2026).")
    if m["m"]:
        y, mo = map(int, m["m"].split("-"))
        if not 1 <= mo <= 12:
            raise HTTPException(400, "That month doesn't exist.")
        start = date(y, mo, 1)
        end = date(y + (mo == 12), mo % 12 + 1, 1)
        return start, end, start.strftime("%B %Y")
    if m["q"]:
        y, q = int(m["q"][:4]), int(m["q"][-1])
        first = 4 + (q - 1) * 3  # Q1 Apr, Q2 Jul, Q3 Oct, Q4 Jan (next calendar year)
        sy = y + (first > 12)
        first = (first - 1) % 12 + 1
        start = date(sy, first, 1)
        last = first + 3
        end = date(sy + (last > 12), (last - 1) % 12 + 1, 1)
        months = ["Apr-Jun", "Jul-Sep", "Oct-Dec", "Jan-Mar"][q - 1]
        return start, end, f"Q{q} FY {y}-{str(y + 1)[2:]} ({months})"
    y = int(m["fy"])
    return date(y, 4, 1), date(y + 1, 4, 1), f"Financial year {y}-{str(y + 1)[2:]} (Apr {y} to Mar {y + 1})"


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=IST).astimezone(UTC)


def _channel(p: Payment) -> str:
    if p.razorpay_payment_id.startswith("bank_"):
        return "Bank transfer (direct sale)"
    return "Online via Dodo (merchant of record)" if settings.PAYMENT_PROVIDER == "dodo" else "Online via Razorpay"


def _split(gross: Decimal, buyer_state: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """GST-inclusive amount -> (taxable, CGST, SGST, IGST)."""
    rate = Decimal(settings.GST_RATE_PERCENT)
    taxable = (gross * 100 / (100 + rate)).quantize(TWO, ROUND_HALF_UP)
    tax = gross - taxable
    if buyer_state == _seller_state():
        half = (tax / 2).quantize(TWO, ROUND_HALF_UP)
        return taxable, half, tax - half, Decimal(0)
    return taxable, Decimal(0), Decimal(0), tax


class Line(BaseModel):
    invoice_no: str | None
    date: date
    customer: str
    gstin: str | None
    state: str
    state_code: str
    address: str | None
    email: str | None
    channel: str
    reference: str
    outlets: int | None
    months: int | None
    covers_from: date | None
    covers_to: date | None
    gross: float
    taxable: float
    cgst: float
    sgst: float
    igst: float
    refunded: float
    net: float
    b2b: bool


def _lines(db: Session, start: date, end: date) -> tuple[list[Line], int]:
    pays = db.scalars(
        select(Payment)
        .where(Payment.created_at >= _utc(start), Payment.created_at < _utc(end), Payment.status == "paid")
        .order_by(Payment.created_at, Payment.id)
    ).all()
    names = {o.id: o for o in db.scalars(select(Organization))}
    out, tests = [], 0
    for p in pays:
        if p.is_test:
            tests += 1
            continue
        org = names.get(p.organization_id)
        code = (p.bill_gstin or "")[:2]
        code = code if code in STATES else _seller_state()  # no GSTIN: place of supply taken as the seller's state
        gross = Decimal(p.amount_paise) / 100
        direct = p.razorpay_payment_id.startswith("bank_")
        taxable, cgst, sgst, igst = _split(gross, code) if direct else (gross, Decimal(0), Decimal(0), Decimal(0))
        refunded = Decimal(p.refunded_paise or 0) / 100
        out.append(
            Line(
                invoice_no=p.invoice_no,
                date=p.created_at.astimezone(IST).date(),
                customer=p.bill_name or (org.name if org else "Deleted restaurant"),
                gstin=p.bill_gstin,
                state=STATES.get(code, code),
                state_code=code,
                address=p.bill_address,
                email=p.bill_email,
                channel=_channel(p),
                reference=p.razorpay_payment_id,
                outlets=p.outlets,
                months=p.months,
                covers_from=p.period_start.astimezone(IST).date() if p.period_start else None,
                covers_to=p.period_end.astimezone(IST).date() if p.period_end else None,
                gross=float(gross),
                taxable=float(taxable),
                cgst=float(cgst),
                sgst=float(sgst),
                igst=float(igst),
                refunded=float(refunded),
                net=float(gross - refunded),
                b2b=bool(p.bill_gstin),
            )
        )
    return out, tests


def _refunds(db: Session, start: date, end: date) -> list[Refund]:
    return list(
        db.scalars(
            select(Refund)
            .where(Refund.refunded_at >= _utc(start), Refund.refunded_at < _utc(end), Refund.is_test.is_(False))
            .order_by(Refund.refunded_at)
        )
    )


def _invoice_check(db: Session) -> list[list]:
    """Every invoice number ever issued, in order, with any duplicate called out (auditors ask first)."""
    rows = db.execute(
        select(Payment.invoice_no, Payment.id, Payment.created_at, Payment.is_test)
        .where(Payment.invoice_no.is_not(None))
        .order_by(Payment.id)
    ).all()
    seen: dict[str, int] = {}
    for inv, *_ in rows:
        seen[inv] = seen.get(inv, 0) + 1
    return [
        [
            inv,
            pid,
            when.astimezone(IST).replace(tzinfo=None),
            "Test" if test else "Live",
            "Duplicate number: check" if seen[inv] > 1 else "OK, unique",
        ]
        for inv, pid, when, test in rows
    ]


class Summary(BaseModel):
    label: str
    start: date
    end: date
    invoices: int
    gross: float
    refunded: float
    net: float
    test_payments_left_out: int
    by_channel: dict[str, float]
    direct_taxable: float
    direct_cgst: float
    direct_sgst: float
    direct_igst: float
    b2b_invoices: int
    b2c_invoices: int
    refunds: int
    gst_rate: int
    seller: str
    seller_gstin: str | None


def _summary(db: Session, value: str) -> tuple[Summary, list[Line], list[Refund], date, date]:
    start, end, label = period_range(value)
    lines, tests = _lines(db, start, end)
    refunds = _refunds(db, start, end)
    by: dict[str, float] = {}
    for x in lines:
        by[x.channel] = round(by.get(x.channel, 0) + x.gross, 2)
    direct = [x for x in lines if x.channel.startswith("Bank")]
    s = Summary(
        label=label,
        start=start,
        end=end - timedelta(days=1),
        invoices=len(lines),
        gross=round(sum(x.gross for x in lines), 2),
        refunded=round(sum(r.amount_paise for r in refunds) / 100, 2),
        net=0,
        test_payments_left_out=tests,
        by_channel=by,
        direct_taxable=round(sum(x.taxable for x in direct), 2),
        direct_cgst=round(sum(x.cgst for x in direct), 2),
        direct_sgst=round(sum(x.sgst for x in direct), 2),
        direct_igst=round(sum(x.igst for x in direct), 2),
        b2b_invoices=sum(x.b2b for x in lines),
        b2c_invoices=sum(not x.b2b for x in lines),
        refunds=len(refunds),
        gst_rate=settings.GST_RATE_PERCENT,
        seller=settings.PARENT_COMPANY or settings.COMPANY_NAME,
        seller_gstin=settings.PARENT_GSTIN or None,
    )
    s.net = round(s.gross - s.refunded, 2)
    return s, lines, refunds, start, end


@router.get("/summary", response_model=Summary)
def summary(period: str, db: Session = Depends(get_db)) -> Summary:
    """On-screen totals for a month, quarter or financial year."""
    return _summary(db, period)[0]


HEAD, FILL = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0C3B2E")
MONEY = "#,##,##0.00"


def _sheet(wb: Workbook, title: str, headers: list[str], rows: list[list], money: set[int] = frozenset()) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = HEAD, FILL
    for r in rows:
        ws.append(r)
    for i, h in enumerate(headers, 1):
        width = max([len(str(h))] + [len(str(r[i - 1])) for r in rows if r[i - 1] is not None] or [10])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 10), 50)
        if i in money:
            for row in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                row[0].number_format = MONEY
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions


def _total_row(rows: list[list], cols: set[int], width: int) -> list:
    t: list = [None] * width
    t[0] = "TOTAL"
    for c in cols:
        t[c - 1] = round(sum(r[c - 1] or 0 for r in rows), 2)
    return t


@router.get("/report.xlsx")
def report(period: str, db: Session = Depends(get_db)) -> StreamingResponse:
    """The audit file: summary, sales register, refunds, GST summary, monthly split, invoice check, audit trail."""
    s, lines, refunds, start, end = _summary(db, period)
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    seller_state = STATES.get(_seller_state(), _seller_state())
    info = [
        ["Report", f"Virundhu sales and GST report: {s.label}"],
        ["Period", f"{s.start:%d %b %Y} to {s.end:%d %b %Y} (India time)"],
        ["Seller", f"{s.seller} (brand: {settings.COMPANY_NAME})"],
        ["Seller GSTIN", s.seller_gstin or "Not set: add PARENT_GSTIN on the server"],
        ["Seller state", seller_state],
        ["SAC code", settings.GST_SAC or "Confirm with your accountant"],
        ["GST rate inside prices", f"{s.gst_rate}%"],
        ["Generated", datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")],
        [],
        ["Invoices (live payments)", s.invoices],
        ["Gross received", s.gross],
        ["Refunded in this period", s.refunded],
        ["Net", s.net],
        ["B2B invoices (customer GSTIN given)", s.b2b_invoices],
        ["B2C invoices", s.b2c_invoices],
        ["Test-mode payments left out", s.test_payments_left_out],
        [],
        ["By channel", ""],
        *[[k, v] for k, v in s.by_channel.items()],
        [],
        ["Direct sales (bank transfer): GST inside the price", ""],
        ["Taxable value", s.direct_taxable],
        ["CGST", s.direct_cgst],
        ["SGST", s.direct_sgst],
        ["IGST", s.direct_igst],
        [],
        ["Notes for the auditor", ""],
        [
            "1",
            "Online payments are taken by Dodo Payments as merchant of record: Dodo invoices the customer and handles "
            "GST on that sale. Reconcile these lines with Dodo's payout report (Dodo dashboard > Payouts).",
        ],
        [
            "2",
            "Bank transfers are direct sales: GST is split here from the GST-inclusive price. CGST+SGST when the "
            "customer's GSTIN state matches the seller's, IGST otherwise; no GSTIN = treated as same state.",
        ],
        [
            "3",
            "Every amount comes from the payments table; refunds from Dodo's refund events. "
            "Test payments are left out.",
        ],
        ["4", "Audit trail sheet: every payment, refund, plan change and account event in the period, with time."],
    ]
    for r in info:
        ws.append(r)
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 44, 110
    for row in ws.iter_rows(min_row=1, max_col=1):
        row[0].font = Font(bold=True)
    for row in ws.iter_rows(min_row=1, min_col=2, max_col=2):
        if isinstance(row[0].value, float | int) and not isinstance(row[0].value, bool):
            row[0].number_format = MONEY

    head = [
        "Invoice no",
        "Date",
        "Customer (bill to)",
        "Customer GSTIN",
        "Place of supply",
        "State code",
        "Address",
        "Email",
        "Channel",
        "Payment reference",
        "Outlets",
        "Months",
        "Covers from",
        "Covers to",
        "Gross (incl. GST)",
        "Taxable value",
        "CGST",
        "SGST",
        "IGST",
        "Refunded",
        "Net",
        "Type",
    ]
    rows = [
        [
            x.invoice_no,
            x.date,
            x.customer,
            x.gstin,
            x.state,
            x.state_code,
            x.address,
            x.email,
            x.channel,
            x.reference,
            x.outlets,
            x.months,
            x.covers_from,
            x.covers_to,
            x.gross,
            x.taxable,
            x.cgst,
            x.sgst,
            x.igst,
            x.refunded,
            x.net,
            "B2B" if x.b2b else "B2C",
        ]
        for x in lines
    ]
    money = {15, 16, 17, 18, 19, 20, 21}
    _sheet(wb, "Sales register", head, rows + ([_total_row(rows, money, len(head))] if rows else []), money)

    by_pay = {
        p.razorpay_payment_id: p
        for p in db.scalars(
            select(Payment).where(Payment.razorpay_payment_id.in_([r.provider_payment_id for r in refunds]))
        )
    }
    rrows = [
        [
            r.refund_id,
            r.refunded_at.astimezone(IST).replace(tzinfo=None),
            r.provider_payment_id,
            by_pay[r.provider_payment_id].invoice_no if r.provider_payment_id in by_pay else None,
            by_pay[r.provider_payment_id].bill_name if r.provider_payment_id in by_pay else None,
            r.amount_paise / 100,
            r.status,
            r.reason,
        ]
        for r in refunds
    ]
    _sheet(
        wb,
        "Refunds",
        ["Refund id", "When (IST)", "Payment reference", "Original invoice", "Customer", "Amount", "Status", "Reason"],
        rrows + ([_total_row(rrows, {6}, 8)] if rrows else []),
        {6},
    )

    direct = [x for x in lines if x.channel.startswith("Bank")]
    gst_rows = []
    for kind in ("B2B", "B2C"):
        for code in sorted({x.state_code for x in direct if ("B2B" if x.b2b else "B2C") == kind}):
            xs = [x for x in direct if ("B2B" if x.b2b else "B2C") == kind and x.state_code == code]
            gst_rows.append(
                [
                    kind,
                    STATES.get(code, code),
                    code,
                    len(xs),
                    round(sum(x.gross for x in xs), 2),
                    round(sum(x.taxable for x in xs), 2),
                    round(sum(x.cgst for x in xs), 2),
                    round(sum(x.sgst for x in xs), 2),
                    round(sum(x.igst for x in xs), 2),
                ]
            )
    gm = {5, 6, 7, 8, 9}
    _sheet(
        wb,
        "GST summary (direct)",
        ["Type", "Place of supply", "State code", "Invoices", "Gross", "Taxable value", "CGST", "SGST", "IGST"],
        gst_rows + ([_total_row(gst_rows, gm | {4}, 9)] if gst_rows else []),
        gm,
    )
    b2b = [
        [x.gstin, x.customer, x.invoice_no, x.date, x.gross, x.state, x.taxable, x.cgst, x.sgst, x.igst]
        for x in direct
        if x.b2b
    ]
    _sheet(
        wb,
        "B2B invoices (GSTR-1)",
        [
            "Customer GSTIN",
            "Customer",
            "Invoice no",
            "Invoice date",
            "Invoice value",
            "Place of supply",
            "Taxable value",
            "CGST",
            "SGST",
            "IGST",
        ],
        b2b,
        {5, 7, 8, 9, 10},
    )

    months: dict[str, list[Line]] = {}
    for x in lines:
        months.setdefault(x.date.strftime("%Y-%m"), []).append(x)
    mrows = []
    d = start
    while d < end:
        k = d.strftime("%Y-%m")
        xs = months.get(k, [])
        refd = sum(r.amount_paise for r in refunds if r.refunded_at.astimezone(IST).strftime("%Y-%m") == k) / 100
        gross = round(sum(x.gross for x in xs), 2)
        mrows.append(
            [
                d.strftime("%b %Y"),
                len(xs),
                gross,
                round(refd, 2),
                round(gross - refd, 2),
                round(sum(x.gross for x in xs if x.channel.startswith("Online")), 2),
                round(sum(x.gross for x in xs if x.channel.startswith("Bank")), 2),
                round(sum(x.cgst + x.sgst + x.igst for x in xs), 2),
            ]
        )
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    _sheet(
        wb,
        "Month by month",
        ["Month", "Invoices", "Gross", "Refunded", "Net", "Online (Dodo)", "Bank transfer", "GST on direct sales"],
        mrows + [_total_row(mrows, {2, 3, 4, 5, 6, 7, 8}, 8)],
        {3, 4, 5, 6, 7, 8},
    )

    _sheet(
        wb, "Invoice number check", ["Invoice no", "Payment id", "Issued (IST)", "Mode", "Check"], _invoice_check(db)
    )

    acts = db.scalars(
        select(ActivityLog)
        .where(
            ActivityLog.created_at >= _utc(start), ActivityLog.created_at < _utc(end), ActivityLog.kind.in_(AUDIT_KINDS)
        )
        .order_by(ActivityLog.created_at)
    ).all()
    _sheet(
        wb,
        "Audit trail",
        ["When (IST)", "Event", "Restaurant", "Who", "Details"],
        [
            [
                a.created_at.astimezone(IST).replace(tzinfo=None),
                a.kind.replace("_", " "),
                a.restaurant,
                a.user_email,
                a.detail,
            ]
            for a in acts
        ],
    )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = re.sub(r"[^A-Za-z0-9-]+", "-", period)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="virundhu-accounts-{name}.xlsx"'},
    )
