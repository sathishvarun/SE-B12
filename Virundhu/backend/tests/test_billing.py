"""Razorpay payments with Razorpay itself mocked: order, signature check, plan activation, webhook, expiry."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, Payment, Subscription


def _owner(client):
    email = f"pay-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pay Owner",
            "organization_name": "Pay Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def _resp(code, body):
    r = MagicMock()
    r.status_code, r.json.return_value, r.text = code, body, json.dumps(body)
    return r


def test_pay_monthly_and_plan_turns_on(client, monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "razorpay")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "secret123")
    h, org_id = _owner(client)
    assert client.get("/api/v1/billing", headers=h).json()["plan"] == "trial"
    notes = {"org_id": str(org_id), "outlets": "3", "months": "1"}
    with patch("app.services.billing.httpx.post", return_value=_resp(200, {"id": "order_A"})) as post:
        order = client.post("/api/v1/billing/order", json={"outlets": 3, "months": 1}, headers=h).json()
    assert order["order_id"] == "order_A" and order["amount"] == 3 * 1199 * 100
    assert post.call_args.kwargs["json"]["amount"] == 359700  # amount set by the server, not the browser

    pay_id = f"pay_{uuid.uuid4().hex[:8]}"
    bad = {"razorpay_order_id": "order_A", "razorpay_payment_id": pay_id, "razorpay_signature": "nope"}
    assert client.post("/api/v1/billing/verify", json=bad, headers=h).status_code == 400

    sig = hmac.new(b"secret123", f"order_A|{pay_id}".encode(), hashlib.sha256).hexdigest()
    good = {**bad, "razorpay_signature": sig}
    with patch("app.services.billing.httpx.get", return_value=_resp(200, {"amount": 359700, "notes": notes})):
        assert client.post("/api/v1/billing/verify", json=good, headers=h).status_code == 200
        client.post("/api/v1/billing/verify", json=good, headers=h)  # same payment twice counts once
    status = client.get("/api/v1/billing", headers=h).json()
    assert status["plan"] == "growth" and not status["expired"] and len(status["payments"]) == 1
    assert status["paid_outlets"] == 3 and status["limits"]["outlets"] == 3
    with SessionLocal() as db:
        sub = db.query(Subscription).filter_by(organization_id=org_id).one()
        assert (sub.current_period_end - datetime.now(UTC)).days in (29, 30)


def test_webhook_activates_and_ignores_repeats(client, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "whsec")
    _, org_id = _owner(client)
    pay_id = f"pay_{uuid.uuid4().hex[:8]}"
    event = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": pay_id,
                    "amount": 1529000,
                    "order_id": "order_B",
                    "notes": {"org_id": str(org_id), "outlets": "1", "months": "12"},
                }
            }
        },
    }
    raw = json.dumps(event).encode()
    sig = hmac.new(b"whsec", raw, hashlib.sha256).hexdigest()
    headers = {"X-Razorpay-Signature": sig, "X-Razorpay-Event-Id": f"evt_{pay_id}", "content-type": "application/json"}
    assert (
        client.post(
            "/api/v1/billing/webhook", content=raw, headers={**headers, "X-Razorpay-Signature": "x"}
        ).status_code
        == 400
    )
    assert client.post("/api/v1/billing/webhook", content=raw, headers=headers).json() == {"ok": True}
    assert client.post("/api/v1/billing/webhook", content=raw, headers=headers).json()["duplicate"] is True
    with SessionLocal() as db:
        assert db.get(Organization, org_id).plan == "starter"
        assert db.query(Payment).filter_by(razorpay_payment_id=pay_id).count() == 1


def test_expired_paid_plan_is_read_only_but_billing_still_opens(client):
    h, org_id = _owner(client)
    with SessionLocal() as db:
        db.get(Organization, org_id).plan = "starter"
        sub = db.query(Subscription).filter_by(organization_id=org_id).one()
        sub.plan, sub.status, sub.current_period_end = "starter", "active", datetime.now(UTC) - timedelta(days=1)
        db.commit()
    res = client.post(
        "/api/v1/reviews", json={"review_text": "Nice food", "rating": 5, "platform": "google"}, headers=h
    )
    assert res.status_code == 402
    assert client.get("/api/v1/billing", headers=h).json()["expired"] is True


def test_payments_off_without_keys(client, monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    h, _ = _owner(client)
    res = client.post("/api/v1/billing/order", json={"outlets": 1, "months": 1}, headers=h)
    assert res.status_code == 400 and "isn't switched on" in res.json()["detail"]


def test_dodo_checkout_and_confirm(client, monkeypatch):
    """Dodo: server picks the product, and only a succeeded payment read back from Dodo turns the plan on."""
    from types import SimpleNamespace

    from app.services import dodo_billing

    for k, v in {
        "PAYMENT_PROVIDER": "dodo",
        "DODO_PAYMENTS_API_KEY": "dodo_test_x",
        "DODO_PRODUCT_FLEX": "pdt_flex",
    }.items():
        monkeypatch.setattr(settings, k, v)
    h, org_id = _owner(client)
    fake = MagicMock()
    fake.checkout_sessions.create.return_value = SimpleNamespace(
        checkout_url="https://test.checkout.dodopayments.com/x"
    )
    with patch.object(dodo_billing, "_client", return_value=fake):
        res = client.post("/api/v1/billing/checkout", json={"outlets": 60, "months": 12}, headers=h).json()
        assert res["checkout_url"].startswith("https://test.checkout")
        kwargs = fake.checkout_sessions.create.call_args.kwargs
        item = kwargs["product_cart"][0]
        assert item["product_id"] == "pdt_flex" and kwargs["metadata"]["org_id"] == str(org_id)
        assert item["amount"] == round(649 * 60 * 12 * 0.85) * 100  # 60 outlets: chain tier, 12 months: 15% off

        meta = {"org_id": str(org_id), "outlets": "60", "months": "12"}
        pid = f"pay_{uuid.uuid4().hex[:8]}"
        fake.payments.retrieve.return_value = SimpleNamespace(
            payment_id=pid, status="processing", metadata=meta, total_amount=item["amount"]
        )
        assert client.post("/api/v1/billing/confirm", json={"payment_id": pid}, headers=h).json()["plan"] == "trial"
        fake.payments.retrieve.return_value.status = "succeeded"
        assert client.post("/api/v1/billing/confirm", json={"payment_id": pid}, headers=h).json()["plan"] == "chain"

        other = {**meta, "org_id": "999999"}
        fake.payments.retrieve.return_value = SimpleNamespace(
            payment_id="pay_other", status="succeeded", metadata=other, total_amount=1
        )
        assert client.post("/api/v1/billing/confirm", json={"payment_id": "pay_other"}, headers=h).status_code == 400


def test_pricing_rules():
    from app.services import pricing

    one = pricing.quote(1, 1)
    assert one.total == 1499 and one.plan == "starter" and one.bonus_months == 0
    small = pricing.quote(3, 1)
    assert small.per_outlet_month == 1199 and small.total == 3597
    year = pricing.quote(1, 12)
    assert year.bonus_months == 2 and year.total == round(1499 * 12 * 0.85) and year.access_days > 400
    big = pricing.quote(120, 12)
    assert big.per_outlet_month == 649 and big.plan == "chain" and big.effective_per_outlet_month < 500
    for bad in ((0, 1), (1, 2), (501, 1)):
        try:
            pricing.quote(*bad)
            raise AssertionError("should refuse")
        except pricing.PricingError:
            pass


def test_underpaid_payment_is_refused(client):
    from app.services import billing

    _, org_id = _owner(client)
    with SessionLocal() as db:
        assert billing.activate(db, org_id, 10, 12, f"pay_{uuid.uuid4().hex[:6]}", 100) is False  # ₹1 for a year: no
        assert db.get(Organization, org_id).plan == "trial"


def test_public_quote_endpoint(client):
    q = client.get("/api/v1/billing/quote?outlets=8&months=9").json()
    assert q["tier"] == "Growing chain" and q["bonus_months"] == 1 and q["total"] == round(949 * 8 * 9 * 0.9)
    assert client.get("/api/v1/billing/quote?outlets=8&months=2").status_code == 400
