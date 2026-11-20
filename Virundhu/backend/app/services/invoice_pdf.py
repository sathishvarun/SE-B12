"""PDF documents for the books: tax invoice / payment receipt, proforma invoice, credit note.

One layout for all four, built with fpdf2 and the bundled DejaVu Sans (it has the ₹ sign). Amounts come from the
database row, never recomputed from today's prices. GST is split from the GST-inclusive amount exactly as in
Admin → Accounts (`admin_accounts._split`), so the PDF and the Excel always agree.

- Bank transfer (direct sale): "Tax invoice" with taxable value and CGST + SGST or IGST.
- Online through Dodo: "Payment receipt". Dodo Payments is the merchant of record and issues the tax invoice itself.
- Proforma invoice: what to pay by bank transfer, with the bank details from settings. Not a tax invoice.
- Credit note: one per refund (partial or full), pointing at the original invoice.
"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fpdf import FPDF

from app.config import settings
from app.models import InvoiceRequest, Organization, Payment, Refund

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
IST = ZoneInfo("Asia/Kolkata")
GREEN = (12, 59, 46)
SOFT = (91, 93, 120)


def _rs(x: Decimal | float) -> str:
    """₹ with Indian commas and paise."""
    v = Decimal(str(x)).quantize(Decimal("0.01"))
    whole, frac = str(abs(v)).split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    body = ",".join([*groups, tail]) if groups else tail
    return f"{'-' if v < 0 else ''}₹{body}.{frac}"


def _seller() -> list[str]:
    name = settings.PARENT_COMPANY or settings.COMPANY_NAME
    lines = [f"{name}" + (f" (brand: {settings.COMPANY_NAME})" if settings.PARENT_COMPANY else "")]
    if settings.COMPANY_ADDRESS:
        lines.append(settings.COMPANY_ADDRESS)
    lines.append(f"GSTIN: {settings.PARENT_GSTIN}" if settings.PARENT_GSTIN else "GSTIN: (to be added)")
    if settings.CONTACT_EMAIL:
        lines.append(settings.CONTACT_EMAIL)
    return lines


class _Doc(FPDF):
    def __init__(self, title: str, number: str, when: date) -> None:
        super().__init__(format="A4")
        self.add_font("dv", "", str(FONTS / "DejaVuSans.ttf"))
        self.add_font("dv", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
        self.set_auto_page_break(True, 18)
        self.set_margins(16, 16, 16)
        self.add_page()
        self.set_font("dv", "B", 20)
        self.set_text_color(*GREEN)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.set_font("dv", "", 10)
        self.set_text_color(*SOFT)
        self.cell(0, 6, f"No. {number}    Date: {when:%d %b %Y}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def two_blocks(self, left_title: str, left: list[str], right_title: str, right: list[str]) -> None:
        y = self.get_y()
        w = (self.w - self.l_margin - self.r_margin) / 2 - 4
        for i, (t, lines) in enumerate(((left_title, left), (right_title, right))):
            self.set_xy(self.l_margin + i * (w + 8), y)
            self.set_font("dv", "B", 10)
            self.set_text_color(*SOFT)
            self.cell(w, 6, t.upper(), new_x="LEFT", new_y="NEXT")
            self.set_text_color(20, 20, 20)
            for j, line in enumerate(lines):
                self.set_font("dv", "B" if j == 0 else "", 10)
                self.multi_cell(w, 5, line, align="L", new_x="LEFT", new_y="NEXT")
        self.set_y(max(self.get_y(), y) + 6)

    def table(self, rows: list[tuple[str, str]], total: tuple[str, str] | None = None) -> None:
        width = self.w - self.l_margin - self.r_margin
        self.set_draw_color(220, 214, 196)
        for k, v in rows:
            self.set_font("dv", "", 10)
            self.set_text_color(*SOFT)
            self.cell(width * 0.55, 8, k, border="B")
            self.set_text_color(20, 20, 20)
            self.cell(width * 0.45, 8, v, border="B", align="R", new_x="LMARGIN", new_y="NEXT")
        if total:
            self.set_fill_color(*GREEN)
            self.set_text_color(255, 255, 255)
            self.set_font("dv", "B", 12)
            self.cell(width * 0.55, 11, " " + total[0], fill=True)
            self.cell(width * 0.45, 11, total[1] + " ", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def note(self, text: str) -> None:
        self.set_font("dv", "", 9)
        self.set_text_color(*SOFT)
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def bytes(self) -> bytes:
        return bytes(self.output())


def _buyer(name: str | None, gstin: str | None, address: str | None, email: str | None) -> list[str]:
    from app.routers.admin_accounts import STATES

    lines = [name or "-"]
    if address:
        lines.append(address)
    if gstin:
        lines.append(f"GSTIN: {gstin}")
        if gstin[:2] in STATES:
            lines.append(f"Place of supply: {STATES[gstin[:2]]} ({gstin[:2]})")
    if email:
        lines.append(email)
    return lines


def _gst_rows(gross: Decimal, gstin: str | None) -> list[tuple[str, str]]:
    from app.routers.admin_accounts import STATES, _seller_state, _split

    code = (gstin or "")[:2]
    code = code if code in STATES else _seller_state()
    taxable, cgst, sgst, igst = _split(gross, code)
    rate = settings.GST_RATE_PERCENT
    rows = [("Taxable value", _rs(taxable))]
    if igst:
        rows.append((f"IGST @ {rate}%", _rs(igst)))
    else:
        rows += [(f"CGST @ {rate / 2:g}%", _rs(cgst)), (f"SGST @ {rate / 2:g}%", _rs(sgst))]
    return rows


def _what(outlets: int | None, months: int | None) -> str:
    o, m = outlets or 1, months or 1
    return f"Virundhu review care, {o} outlet{'' if o == 1 else 's'} × {m} month{'' if m == 1 else 's'}"


def invoice(pay: Payment, org: Organization) -> bytes:
    """Tax invoice (bank transfer) or payment receipt (online through Dodo) for one payment."""
    direct = pay.razorpay_payment_id.startswith("bank_")
    when = (pay.created_at or datetime.now(IST)).astimezone(IST).date()
    doc = _Doc("Tax invoice" if direct else "Payment receipt", pay.invoice_no or f"P-{pay.id}", when)
    doc.two_blocks(
        "Seller",
        _seller(),
        "Bill to",
        _buyer(pay.bill_name or org.name, pay.bill_gstin, pay.bill_address, pay.bill_email),
    )
    gross = Decimal(pay.amount_paise) / 100
    rows = [("Description", _what(pay.outlets, pay.months))]
    if pay.period_start and pay.period_end:
        rows.append(
            (
                "Service period",
                f"{pay.period_start.astimezone(IST):%d %b %Y} to {pay.period_end.astimezone(IST):%d %b %Y}",
            )
        )
    if settings.GST_SAC:
        rows.append(("SAC", settings.GST_SAC))
    if direct:
        rows += _gst_rows(gross, pay.bill_gstin)
        rows.append(("Payment", f"Bank transfer, reference {pay.razorpay_payment_id.removeprefix('bank_')}"))
    else:
        rows += [("GST", "Included; tax invoice issued by Dodo Payments"), ("Payment ID", pay.razorpay_payment_id)]
    if pay.refunded_paise:
        rows.append(("Refunded (see credit notes)", _rs(Decimal(pay.refunded_paise) / 100)))
    doc.table(rows, ("Total paid (GST included)", _rs(gross)))
    if not direct:
        doc.note(
            "Dodo Payments is the merchant of record for online payments: it sells this subscription to you and "
            "emails the GST tax invoice for it. This receipt is Virundhu's record of what was bought."
        )
    doc.note("This is a computer-generated document and needs no signature.")
    return doc.bytes()


def proforma(req: InvoiceRequest, org: Organization) -> bytes:
    """What to pay by bank transfer. The tax invoice follows once the money arrives."""
    when = (req.created_at or datetime.now(IST)).astimezone(IST).date()
    doc = _Doc("Proforma invoice", req.number or f"PI-{req.id}", when)
    doc.two_blocks(
        "Seller",
        _seller(),
        "Bill to",
        _buyer(req.bill_name or org.name, req.bill_gstin, req.bill_address, req.bill_email),
    )
    gross = Decimal(req.amount_paise) / 100
    rows = [("Description", _what(req.outlets, req.months)), *_gst_rows(gross, req.bill_gstin)]
    doc.table(rows, ("Amount to pay (GST included)", _rs(gross)))
    bank = [
        ("Account name", settings.BANK_ACCOUNT_NAME),
        ("Bank", settings.BANK_NAME),
        ("Account number", settings.BANK_ACCOUNT_NUMBER),
        ("IFSC", settings.BANK_IFSC),
        ("Branch", settings.BANK_BRANCH),
    ]
    filled = [(k, v) for k, v in bank if v]
    if filled:
        doc.set_font("dv", "B", 12)
        doc.set_text_color(*GREEN)
        doc.cell(0, 8, "Pay by NEFT / RTGS / IMPS to", new_x="LMARGIN", new_y="NEXT")
        doc.table(filled)
    else:
        doc.note("Bank details will be sent to you by email.")
    doc.note(
        f"Please write {req.number} in the transfer remarks. Your plan switches on as soon as the money reaches "
        "us, and the tax invoice is emailed to you. This proforma is not a tax invoice. Valid for 15 days."
    )
    return doc.bytes()


def credit_note(ref: Refund, pay: Payment | None, org: Organization | None) -> bytes:
    """One credit note per refund, partial or full."""
    when = ref.refunded_at.astimezone(IST).date()
    doc = _Doc("Credit note", ref.credit_note_no or f"CN-{ref.id}", when)
    name = (pay.bill_name if pay else None) or (org.name if org else "Customer")
    doc.two_blocks(
        "Seller",
        _seller(),
        "Issued to",
        _buyer(
            name, pay.bill_gstin if pay else None, pay.bill_address if pay else None, pay.bill_email if pay else None
        ),
    )
    amount = Decimal(ref.amount_paise) / 100
    rows = [
        ("Against invoice", (pay.invoice_no if pay else None) or ref.provider_payment_id),
        ("Original amount", _rs(Decimal(pay.amount_paise) / 100) if pay else "-"),
        ("Reason", ref.reason or "Refund"),
        ("Refund reference", ref.refund_id),
    ]
    if pay and pay.razorpay_payment_id.startswith("bank_"):
        rows += _gst_rows(amount, pay.bill_gstin)
    doc.table(rows, ("Credit amount (GST included)", _rs(amount)))
    if pay and not pay.razorpay_payment_id.startswith("bank_"):
        doc.note("This refund was paid back through Dodo Payments, the merchant of record for online payments.")
    doc.note("This is a computer-generated document and needs no signature.")
    return doc.bytes()
