"""Admin → Accounts: month / quarter / financial-year sales, refunds, GST split and the audit Excel file."""

import io
import uuid
from datetime import UTC, date, datetime

from openpyxl import load_workbook
from sqlalchemy import delete, select

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, Payment, Refund
from app.routers.admin_accounts import period_range


def _admin(client) -> dict:
    tok = client.post("/api/v1/auth/login", json={
        "email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_periods_follow_the_indian_financial_year():
    assert period_range("2026-11")[:2] == (date(2026, 11, 1), date(2026, 12, 1))
    assert period_range("2026-12")[:2] == (date(2026, 12, 1), date(2027, 1, 1))
    assert period_range("2026-Q1")[:2] == (date(2026, 4, 1), date(2026, 7, 1))
    assert period_range("2026-Q3")[:2] == (date(2026, 10, 1), date(2027, 1, 1))
    assert period_range("2026-Q4")[:2] == (date(2027, 1, 1), date(2027, 4, 1))
    assert period_range("FY2026")[:2] == (date(2026, 4, 1), date(2027, 4, 1))


def test_report_splits_gst_and_leaves_out_test_payments(client):
    tag = uuid.uuid4().hex[:6].upper()
    db = SessionLocal()
    org = db.scalar(select(Organization).where(Organization.is_demo.is_(True)))
    when = datetime(2026, 11, 15, 6, 0, tzinfo=UTC)
    rows = [
        # direct sale, customer in Tamil Nadu: CGST + SGST
        Payment(organization_id=org.id, razorpay_payment_id=f"bank_ACC{tag}TN", amount_paise=11800000, status="paid",
                outlets=100, months=3, bill_name="TN Chain", bill_gstin="33AAAAA0000A1Z5", invoice_no=f"VR-T{tag}1",
                created_at=when),
        # direct sale, customer in Karnataka: IGST
        Payment(organization_id=org.id, razorpay_payment_id=f"bank_ACC{tag}KA", amount_paise=5900000, status="paid",
                outlets=50, months=1, bill_name="KA Chain", bill_gstin="29AAAAA0000A1Z5", invoice_no=f"VR-T{tag}2",
                created_at=when),
        # online through Dodo (merchant of record): no GST split here
        Payment(organization_id=org.id, razorpay_payment_id=f"pay_ACC{tag}ON", amount_paise=149900, status="paid",
                outlets=1, months=1, invoice_no=f"VR-T{tag}3", created_at=when, refunded_paise=149900),
        # practice payment: never in the books
        Payment(organization_id=org.id, razorpay_payment_id=f"pay_ACC{tag}TEST", amount_paise=999900, status="paid",
                is_test=True, created_at=when),
    ]
    db.add_all(rows)
    db.add(Refund(refund_id=f"ref_ACC{tag}", provider_payment_id=f"pay_ACC{tag}ON", organization_id=org.id,
                  amount_paise=149900, status="succeeded", refunded_at=when))
    db.commit()
    try:
        h = _admin(client)
        s = client.get("/api/v1/admin/accounts/summary", params={"period": "2026-11"}, headers=h).json()
        assert s["test_payments_left_out"] >= 1
        assert s["gross"] >= 118000 + 59000 + 1499 and s["refunded"] >= 1499
        assert s["direct_cgst"] >= 9000 and s["direct_sgst"] >= 9000 and s["direct_igst"] >= 9000
        res = client.get("/api/v1/admin/accounts/report.xlsx", params={"period": "FY2026"}, headers=h)
        assert res.status_code == 200
        wb = load_workbook(io.BytesIO(res.content))
        assert {"Summary", "Sales register", "Refunds", "GST summary (direct)", "B2B invoices (GSTR-1)",
                "Month by month", "Invoice number check", "Audit trail"} <= set(wb.sheetnames)
        reg = {r[0]: r for r in wb["Sales register"].iter_rows(min_row=2, values_only=True)}
        tn, ka = reg[f"VR-T{tag}1"], reg[f"VR-T{tag}2"]
        # ₹1,18,000 incl. 18% GST = ₹1,00,000 taxable + ₹9,000 CGST + ₹9,000 SGST
        assert (tn[15], tn[16], tn[17], tn[18]) == (100000, 9000, 9000, 0)
        assert (ka[15], ka[16], ka[17], ka[18]) == (50000, 0, 0, 9000)
        assert reg[f"VR-T{tag}3"][8].startswith("Online via") and reg[f"VR-T{tag}3"][20] == 0  # refunded in full
        assert not any(k and "TEST" in str(k) for k in reg)  # test payment is not in the register
        assert len(list(wb["Month by month"].iter_rows(min_row=2))) == 13  # 12 months + total
        bad = client.get("/api/v1/admin/accounts/summary", params={"period": "Nov 2026"}, headers=h)
        assert bad.status_code == 400
        owner = client.post("/api/v1/auth/register", json={"full_name": "Acc", "organization_name": "Acc Mess",
                            "email": f"acc-{tag.lower()}@example.com", "password": "Strong#Pass1",
                            "accept_terms": True}).json()
        oh = {"Authorization": f"Bearer {owner['access_token']}"}
        assert client.get("/api/v1/admin/accounts/summary", params={"period": "2026-11"}, headers=oh).status_code == 403
    finally:
        db.execute(delete(Refund).where(Refund.refund_id == f"ref_ACC{tag}"))
        db.execute(delete(Payment).where(Payment.razorpay_payment_id.like(f"%ACC{tag}%")))
        db.commit()
        db.close()
