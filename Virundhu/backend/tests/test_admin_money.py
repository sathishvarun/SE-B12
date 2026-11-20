"""Admin money page: totals per day/week/month, refunds from Dodo, test payments kept apart."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import delete, select

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, Payment, Refund
from app.services import dodo_billing


def _admin(client) -> dict:
    tok = client.post("/api/v1/auth/login", json={
        "email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_money_totals_refunds_and_test_mode(client):
    db = SessionLocal()
    org = db.scalar(select(Organization).where(Organization.is_demo.is_(True)))
    now = datetime.now(UTC)
    live = Payment(organization_id=org.id, razorpay_payment_id="pay_TESTMONEY_live", amount_paise=149900,
                   status="paid", outlets=1, months=1, created_at=now)
    old = Payment(organization_id=org.id, razorpay_payment_id="pay_TESTMONEY_old", amount_paise=299800,
                  status="paid", outlets=1, months=2, created_at=now - timedelta(days=10))
    practice = Payment(organization_id=org.id, razorpay_payment_id="pay_TESTMONEY_test", amount_paise=100000,
                       status="paid", is_test=True, created_at=now)
    db.add_all([live, old, practice])
    db.commit()
    try:
        # A Dodo refund arrives twice (webhook retry): counted once, payment marked refunded
        ref = SimpleNamespace(refund_id="ref_TESTMONEY_1", payment_id="pay_TESTMONEY_old", amount=299800,
                              status="succeeded", created_at=now, reason="Changed mind")
        assert dodo_billing.record_refund(db, ref) is True
        assert dodo_billing.record_refund(db, ref) is False
        db.refresh(old)
        assert old.refunded_paise == 299800

        h = _admin(client)
        m = client.get("/api/v1/admin/money", headers=h).json()
        w = {x["key"]: x for x in m["windows"]}
        assert w["today"]["collected"] >= 1499 and w["today"]["refunded"] >= 2998
        assert m["hidden_test_payments"] >= 1
        assert not any(p["provider_id"] == "pay_TESTMONEY_test" for p in m["payments"])
        assert next(p for p in m["payments"] if p["provider_id"] == "pay_TESTMONEY_old")["status"] == "refunded"
        assert len(m["daily"]) == 30 and len(m["weekly"]) == 12
        with_test = client.get("/api/v1/admin/money?include_test=true", headers=h).json()
        assert any(p["provider_id"] == "pay_TESTMONEY_test" for p in with_test["payments"])
        owner = client.post("/api/v1/auth/login", json={"email": "demo@virundhu.local", "password": "x"})
        assert client.get("/api/v1/admin/money").status_code in (401, 403) and owner.status_code in (401, 429)
    finally:
        db.execute(delete(Refund).where(Refund.refund_id.like("ref_TESTMONEY%")))
        db.execute(delete(Payment).where(Payment.razorpay_payment_id.like("pay_TESTMONEY%")))
        db.commit()
        db.close()
