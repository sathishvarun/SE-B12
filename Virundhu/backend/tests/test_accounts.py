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


def _owner(client, name):
    tag = uuid.uuid4().hex[:6]
    d = client.post("/api/v1/auth/register", json={"full_name": "Books Owner", "organization_name": name,
                    "email": f"books-{tag}@example.com", "password": "Strong#Pass1", "accept_terms": True}).json()
    return {"Authorization": f"Bearer {d['access_token']}"}, d["user"]["organization"]["id"]


def test_proforma_bank_payment_partial_refund_credit_note_and_zip(client):
    import zipfile

    from app.models import InvoiceRequest

    h, org = _owner(client, "Books Chain")
    body = {"outlets": 700, "months": 12, "company_name": "Books Chain Pvt Ltd", "gstin": "33AAACB1234C1Z5",
            "address": "1 Main Road, Coimbatore 641006"}
    asked = client.post("/api/v1/billing/bank-transfer", json=body, headers=h).json()
    assert asked["number"].startswith("PI-") and asked["total"] == 4633860
    mine = client.get("/api/v1/billing/invoice-requests", headers=h).json()
    assert mine[0]["status"] == "open"
    pdf = client.get(f"/api/v1/billing/invoice-requests/{asked['request_id']}/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    other, _ = _owner(client, "Other Books")
    assert client.get(f"/api/v1/billing/invoice-requests/{asked['request_id']}/pdf", headers=other).status_code == 404

    admin = _admin(client)
    ref = f"UTRBK{uuid.uuid4().hex[:6].upper()}"
    ok = client.post(f"/api/v1/admin/organizations/{org}/bank-payment",
                     json={"outlets": 700, "months": 12, "amount_inr": 4633860, "reference": ref}, headers=admin)
    assert ok.status_code == 200, ok.text
    with SessionLocal() as db:
        assert db.get(InvoiceRequest, asked["request_id"]).status == "paid"
        pay = db.scalar(select(Payment).where(Payment.razorpay_payment_id == f"bank_{ref}"))
        pay.is_test = False  # the local Dodo key is a test key; treat this one as a live sale for the books
        db.commit()
        db.refresh(pay)
    inv = client.get(f"/api/v1/billing/receipts/{pay.id}/pdf", headers=h)
    assert inv.status_code == 200 and inv.content[:4] == b"%PDF"
    assert client.get(f"/api/v1/admin/accounts/payments/{pay.id}/pdf", headers=admin).content[:4] == b"%PDF"

    # partial refund by bank: credit note issued, cannot go over what's left, same reference refused
    url = f"/api/v1/admin/accounts/payments/{pay.id}/refund"
    r1 = client.post(url, json={"amount_inr": 100000, "reference": f"RF{ref}", "reason": "Two outlets closed"},
                     headers=admin)
    assert r1.status_code == 200 and r1.json()["credit_note"].startswith("CN-")
    assert client.post(url, json={"amount_inr": 100000, "reference": f"RF{ref}"}, headers=admin).status_code == 400
    assert client.post(url, json={"amount_inr": 9999999, "reference": f"RX{ref}"}, headers=admin).status_code == 400
    notes = client.get("/api/v1/billing/credit-notes", headers=h).json()
    assert notes[0]["amount"] == 100000
    cn = client.get(f"/api/v1/billing/credit-notes/{notes[0]['id']}/pdf", headers=h)
    assert cn.content[:4] == b"%PDF"
    assert client.get(f"/api/v1/billing/credit-notes/{notes[0]['id']}/pdf", headers=other).status_code == 404
    bank = client.get("/api/v1/admin/accounts/bank-payments", headers=admin).json()
    assert next(b for b in bank if b["id"] == pay.id)["refunded"] == 100000

    fy = 2026 if datetime.now(UTC).month >= 4 else 2025
    z = client.get("/api/v1/billing/receipts.zip", params={"fy": fy}, headers=h)
    assert z.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "summary.csv" in names and any(n.startswith("invoices/") for n in names)
    assert any(n.startswith("credit-notes/CN-") for n in names)
    assert client.get("/api/v1/billing/receipts.zip", params={"fy": 2020}, headers=h).status_code == 404

    wb = load_workbook(io.BytesIO(client.get("/api/v1/admin/accounts/report.xlsx", params={"period": f"FY{fy}"},
                                              headers=admin).content))
    assert "Dodo payouts" in wb.sheetnames
    cns = [r[0] for r in wb["Refunds"].iter_rows(min_row=2, values_only=True)]
    assert notes[0]["credit_note_no"] in cns
    with SessionLocal() as db:
        db.execute(delete(Refund).where(Refund.provider_payment_id == f"bank_{ref}"))
        db.execute(delete(Payment).where(Payment.razorpay_payment_id == f"bank_{ref}"))
        db.commit()


def test_dodo_refund_gets_credit_note_and_sync_reads_fees(client, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    from app.models import DodoPayout
    from app.services import books, dodo_billing

    tag = uuid.uuid4().hex[:6].upper()
    db = SessionLocal()
    org = db.scalar(select(Organization).where(Organization.is_demo.is_(True)))
    pay = Payment(organization_id=org.id, razorpay_payment_id=f"pay_DS{tag}", amount_paise=299800, status="paid",
                  outlets=2, months=1, invoice_no=f"VR-DS{tag}")
    db.add(pay)
    db.commit()
    try:
        r = SimpleNamespace(refund_id=f"ref_DS{tag}", payment_id=f"pay_DS{tag}", amount=50000, status="succeeded",
                            created_at=datetime.now(UTC), reason="Partial")
        dodo_billing.record_refund(db, r)
        row = db.scalar(select(Refund).where(Refund.refund_id == f"ref_DS{tag}"))
        assert row.credit_note_no and row.credit_note_no.startswith("CN-")
        fake = MagicMock()
        fake.payments.retrieve.return_value = SimpleNamespace(tax=45732, settlement_amount=280000,
                                                              settlement_currency="INR")
        fake.payouts.list.return_value = SimpleNamespace(items=[SimpleNamespace(
            payout_id=f"pout_{tag}", amount=280000, fee=5000, tax=900, refunds=0, chargebacks=0, currency="INR",
            status="success", created_at=datetime.now(UTC), remarks=None, payout_document_url=None)])
        with patch.object(dodo_billing, "_client", return_value=fake):
            out = books.sync_dodo(db)
        db.refresh(pay)
        assert pay.settlement_paise == 280000 and pay.provider_tax_paise == 45732 and out["new_payouts"] >= 1
        assert db.scalar(select(DodoPayout).where(DodoPayout.payout_id == f"pout_{tag}")).fee_paise == 5000
        h = _admin(client)
        sent = client.post("/api/v1/admin/accounts/email-now", json={"period": "2026-11"}, headers=h).json()
        assert sent["period"] == "2026-11" and sent["to"]
        st = client.get("/api/v1/admin/accounts/settings", headers=h).json()
        assert st["payouts"] >= 1 and "bank_ready" in st
    finally:
        db.execute(delete(Refund).where(Refund.refund_id == f"ref_DS{tag}"))
        db.execute(delete(DodoPayout).where(DodoPayout.payout_id == f"pout_{tag}"))
        db.execute(delete(Payment).where(Payment.razorpay_payment_id == f"pay_DS{tag}"))
        db.commit()
        db.close()
