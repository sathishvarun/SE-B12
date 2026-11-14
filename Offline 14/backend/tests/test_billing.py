"""Billing: subscription overview, checkout/cancel (Dodo mocked), webhook verification + events."""

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Subscription
from app.services import dodo_payments
from tests.conftest import API, Outbox, Seller, create_contact, create_deal

RAW_KEY = b"0123456789abcdef0123456789abcdef"
WEBHOOK_SECRET = "whsec_" + base64.b64encode(RAW_KEY).decode()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sub(db: Session, user_id: int) -> Subscription:
    db.expire_all()
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    assert sub is not None
    return sub


def _make_pro(db: Session, user_id: int, sub_id: str = "sub_1") -> None:
    sub = _sub(db, user_id)
    sub.plan = "pro"  # type: ignore[assignment]
    sub.status = "active"  # type: ignore[assignment]
    sub.dodo_subscription_id = sub_id
    db.commit()


def sign(body: bytes, msg_id: str = "msg_1", ts: int | None = None, key: bytes = RAW_KEY) -> dict:
    ts = int(time.time()) if ts is None else ts
    signed = f"{msg_id}.{ts}.".encode() + body
    sig = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {
        "webhook-id": msg_id,
        "webhook-timestamp": str(ts),
        "webhook-signature": f"v1,{sig}",
        "content-type": "application/json",
    }


def event(event_type: str, user_id: int | None = None, **data: Any) -> dict:
    payload_data: dict[str, Any] = {"subscription_id": "sub_1", **data}
    if user_id is not None:
        payload_data.setdefault("metadata", {"user_id": str(user_id)})
    return {"type": event_type, "data": payload_data}


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "DODO_PAYMENTS_WEBHOOK_SECRET", WEBHOOK_SECRET)
    return WEBHOOK_SECRET


@pytest.fixture
def post_webhook(client: TestClient, webhook_secret: str) -> Callable[..., httpx.Response]:
    def _post(payload: dict | bytes, **sign_kwargs: Any) -> httpx.Response:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return client.post(
            f"{API}/billing/webhook", content=body, headers=sign(body, **sign_kwargs)
        )

    return _post


class DodoMock:
    """Records requests to the (mocked) Dodo API and returns a configurable response."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.json: dict[str, Any] = {"session_id": "cs_1", "checkout_url": "https://pay.test/cs_1"}
        self.raise_error = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.raise_error:
            raise httpx.ConnectError("down", request=request)
        return httpx.Response(self.status, json=self.json)


@pytest.fixture
def dodo(monkeypatch: pytest.MonkeyPatch) -> DodoMock:
    """Route every httpx.AsyncClient made by dodo_payments through a MockTransport."""
    mock = DodoMock()
    real_async_client = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(mock.handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(dodo_payments.httpx, "AsyncClient", factory)
    monkeypatch.setattr(settings, "DODO_PAYMENTS_API_KEY", "sk_test")
    monkeypatch.setattr(settings, "DODO_PAYMENTS_PRO_PRODUCT_ID", "prod_pro")
    return mock


# ---------------------------------------------------------------------------
# Subscription overview
# ---------------------------------------------------------------------------


def test_subscription_overview_free(
    client: TestClient, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_CONTACTS", 7)
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_OPEN_DEALS", 3)
    c = create_contact(client, seller_a)
    create_deal(client, seller_a, c["id"])
    create_deal(client, seller_a, c["id"], stage="won")
    resp = client.get(f"{API}/billing/subscription", headers=seller_a.headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "plan": "free",
        "status": "active",
        "current_period_end": None,
        "limits": {"max_contacts": 7, "max_open_deals": 3},
        "usage": {"contacts": 1, "open_deals": 1},
    }


def test_subscription_overview_pro_has_null_limits(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    _make_pro(db, seller_a.id)
    body = client.get(f"{API}/billing/subscription", headers=seller_a.headers).json()
    assert body["plan"] == "pro"
    assert body["limits"] == {"max_contacts": None, "max_open_deals": None}


def test_subscription_row_created_if_missing(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    db.delete(_sub(db, seller_a.id))
    db.commit()
    body = client.get(f"{API}/billing/subscription", headers=seller_a.headers).json()
    assert body["plan"] == "free" and body["status"] == "active"


def test_billing_requires_auth(client: TestClient) -> None:
    assert client.get(f"{API}/billing/subscription").status_code == 401
    assert client.post(f"{API}/billing/checkout").status_code == 401
    assert client.post(f"{API}/billing/cancel").status_code == 401


# ---------------------------------------------------------------------------
# Checkout / cancel
# ---------------------------------------------------------------------------


def test_checkout_returns_url_and_does_not_change_plan(
    client: TestClient, db: Session, seller_a: Seller, dodo: DodoMock
) -> None:
    resp = client.post(f"{API}/billing/checkout", headers=seller_a.headers)
    assert resp.status_code == 200
    assert resp.json() == {"checkout_url": "https://pay.test/cs_1"}

    (req,) = dodo.requests
    assert req.method == "POST"
    assert str(req.url) == "https://test.dodopayments.com/checkouts"
    assert req.headers["authorization"] == "Bearer sk_test"
    sent = json.loads(req.content)
    assert sent["product_cart"] == [{"product_id": "prod_pro", "quantity": 1}]
    assert sent["metadata"] == {"user_id": str(seller_a.id)}
    assert sent["customer"]["email"] == seller_a.email
    assert sent["return_url"] == f"{settings.FRONTEND_URL}/billing?checkout=success"
    # plan only changes via webhook
    assert _sub(db, seller_a.id).plan == "free"


def test_checkout_live_mode_url(
    client: TestClient, seller_a: Seller, dodo: DodoMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DODO_PAYMENTS_ENVIRONMENT", "live_mode")
    client.post(f"{API}/billing/checkout", headers=seller_a.headers)
    assert dodo.requests[0].url.host == "live.dodopayments.com"


def test_checkout_already_pro_409(
    client: TestClient, db: Session, seller_a: Seller, dodo: DodoMock
) -> None:
    _make_pro(db, seller_a.id)
    assert client.post(f"{API}/billing/checkout", headers=seller_a.headers).status_code == 409
    assert dodo.requests == []


def test_checkout_not_configured_400(client: TestClient, seller_a: Seller) -> None:
    assert client.post(f"{API}/billing/checkout", headers=seller_a.headers).status_code == 400


@pytest.mark.parametrize("failure", ["http_500", "network", "no_url"])
def test_checkout_provider_errors_502(
    client: TestClient, seller_a: Seller, dodo: DodoMock, failure: str
) -> None:
    if failure == "http_500":
        dodo.status = 500
    elif failure == "network":
        dodo.raise_error = True
    else:
        dodo.json = {"session_id": "cs_1"}
    resp = client.post(f"{API}/billing/checkout", headers=seller_a.headers)
    assert resp.status_code == 502


def test_cancel_free_user_400(client: TestClient, seller_a: Seller, dodo: DodoMock) -> None:
    assert client.post(f"{API}/billing/cancel", headers=seller_a.headers).status_code == 400
    assert dodo.requests == []


def test_cancel_pro_calls_dodo_but_plan_waits_for_webhook(
    client: TestClient, db: Session, seller_a: Seller, dodo: DodoMock
) -> None:
    _make_pro(db, seller_a.id, sub_id="sub_42")
    dodo.json = {}
    resp = client.post(f"{API}/billing/cancel", headers=seller_a.headers)
    assert resp.status_code == 200
    assert resp.json()["plan"] == "pro"
    (req,) = dodo.requests
    assert req.method == "PATCH"
    assert req.url.path == "/subscriptions/sub_42"
    assert json.loads(req.content) == {"status": "cancelled"}


def test_cancel_with_empty_provider_body(
    client: TestClient, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dodo may answer the PATCH with an empty body; that must not crash."""
    _make_pro(db, seller_a.id)
    monkeypatch.setattr(settings, "DODO_PAYMENTS_API_KEY", "sk_test")
    real = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = httpx.MockTransport(lambda r: httpx.Response(200, content=b""))
        return real(*args, **kwargs)

    monkeypatch.setattr(dodo_payments.httpx, "AsyncClient", factory)
    assert client.post(f"{API}/billing/cancel", headers=seller_a.headers).status_code == 200


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def test_webhook_valid_signature_upgrades_to_pro(
    post_webhook, db: Session, seller_a: Seller, outbox: Outbox
) -> None:
    resp = post_webhook(
        event(
            "subscription.active",
            seller_a.id,
            customer={"customer_id": "cus_1"},
            next_billing_date="2026-12-14T00:00:00Z",
            status="active",
        )
    )
    assert resp.status_code == 200
    assert resp.json() == {"received": True}
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.status == "active"
    assert sub.dodo_subscription_id == "sub_1" and sub.dodo_customer_id == "cus_1"
    assert sub.current_period_end is not None
    assert sub.current_period_end.strftime("%Y-%m-%d") == "2026-12-14"
    # notification email sent once
    subjects = [m[1] for m in outbox.to(seller_a.email)]
    assert subjects.count("Your Sathish CRM subscription has changed") == 1


def test_webhook_invalid_signature_401(
    client: TestClient, db: Session, seller_a: Seller, webhook_secret: str
) -> None:
    body = json.dumps(event("subscription.active", seller_a.id)).encode()
    headers = sign(body, key=b"wrong-key-wrong-key-wrong-key-00")
    resp = client.post(f"{API}/billing/webhook", content=body, headers=headers)
    assert resp.status_code == 401
    assert _sub(db, seller_a.id).plan == "free"


def test_webhook_tampered_body_401(
    client: TestClient, db: Session, seller_a: Seller, webhook_secret: str
) -> None:
    original = json.dumps(event("subscription.cancelled", 999)).encode()
    headers = sign(original)
    tampered = json.dumps(event("subscription.active", seller_a.id)).encode()
    resp = client.post(f"{API}/billing/webhook", content=tampered, headers=headers)
    assert resp.status_code == 401
    assert _sub(db, seller_a.id).plan == "free"


@pytest.mark.parametrize("missing", ["webhook-id", "webhook-timestamp", "webhook-signature"])
def test_webhook_missing_header_401(
    client: TestClient, seller_a: Seller, webhook_secret: str, missing: str
) -> None:
    body = json.dumps(event("subscription.active", seller_a.id)).encode()
    headers = sign(body)
    del headers[missing]
    assert client.post(f"{API}/billing/webhook", content=body, headers=headers).status_code == 401


def test_webhook_non_numeric_timestamp_401(
    client: TestClient, seller_a: Seller, webhook_secret: str
) -> None:
    body = b"{}"
    headers = sign(body)
    headers["webhook-timestamp"] = "yesterday"
    assert client.post(f"{API}/billing/webhook", content=body, headers=headers).status_code == 401


@pytest.mark.parametrize("offset", [-600, 600])
def test_webhook_replay_with_stale_or_future_timestamp_401(
    post_webhook, db: Session, seller_a: Seller, offset: int
) -> None:
    """A captured, correctly-signed message can't be replayed outside the 5-minute window."""
    resp = post_webhook(event("subscription.active", seller_a.id), ts=int(time.time()) + offset)
    assert resp.status_code == 401
    assert _sub(db, seller_a.id).plan == "free"


def test_webhook_no_secret_configured_401(client: TestClient, seller_a: Seller) -> None:
    body = json.dumps(event("subscription.active", seller_a.id)).encode()
    resp = client.post(f"{API}/billing/webhook", content=body, headers=sign(body))
    assert resp.status_code == 401


def test_webhook_accepts_any_matching_signature_entry(
    client: TestClient, db: Session, seller_a: Seller, webhook_secret: str
) -> None:
    body = json.dumps(event("subscription.active", seller_a.id)).encode()
    headers = sign(body)
    headers["webhook-signature"] = "v1,bogus v2,whatever " + headers["webhook-signature"]
    assert client.post(f"{API}/billing/webhook", content=body, headers=headers).status_code == 200
    assert _sub(db, seller_a.id).plan == "pro"


def test_webhook_non_base64_secret_is_used_raw(
    client: TestClient, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DODO_PAYMENTS_WEBHOOK_SECRET", "whsec_not*base64!")
    body = json.dumps(event("subscription.active", seller_a.id)).encode()
    headers = sign(body, key=b"not*base64!")
    assert client.post(f"{API}/billing/webhook", content=body, headers=headers).status_code == 200


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"])
def test_webhook_signed_but_invalid_payload_400(post_webhook, body: bytes) -> None:
    assert post_webhook(body).status_code == 400


# ---------------------------------------------------------------------------
# Webhook event handling
# ---------------------------------------------------------------------------


def test_webhook_replayed_event_is_idempotent(
    post_webhook, db: Session, seller_a: Seller, outbox: Outbox
) -> None:
    payload = event("subscription.active", seller_a.id, status="active")
    assert post_webhook(payload, msg_id="msg_a").status_code == 200
    assert post_webhook(payload, msg_id="msg_a").status_code == 200
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.status == "active"
    assert len(outbox.to(seller_a.email)) == 2  # welcome + one change email (not two)


@pytest.mark.parametrize("event_type", ["subscription.cancelled", "subscription.expired"])
def test_webhook_cancelled_downgrades_to_free(
    post_webhook, db: Session, seller_a: Seller, event_type: str
) -> None:
    post_webhook(
        event("subscription.active", seller_a.id, next_billing_date="2026-12-14T00:00:00Z")
    )
    resp = post_webhook(event(event_type, seller_a.id))
    assert resp.status_code == 200
    sub = _sub(db, seller_a.id)
    assert sub.plan == "free" and sub.status == "cancelled"
    assert sub.current_period_end is None


def test_free_limits_apply_again_after_cancel(
    post_webhook,
    client: TestClient,
    seller_a: Seller,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_CONTACTS", 1)
    post_webhook(event("subscription.active", seller_a.id))
    create_contact(client, seller_a, name="1")
    create_contact(client, seller_a, name="2")  # pro: unlimited
    post_webhook(event("subscription.cancelled", seller_a.id))
    resp = client.post(f"{API}/contacts", json={"name": "3"}, headers=seller_a.headers)
    assert resp.status_code == 402


@pytest.mark.parametrize("event_type", ["subscription.on_hold", "subscription.past_due"])
def test_webhook_past_due_keeps_plan(
    post_webhook, db: Session, seller_a: Seller, event_type: str
) -> None:
    post_webhook(event("subscription.active", seller_a.id))
    post_webhook(event(event_type, seller_a.id))
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.status == "past_due"
    # renewal brings it back to active
    post_webhook(event("subscription.renewed", seller_a.id, status="active"))
    assert _sub(db, seller_a.id).status == "active"


def test_webhook_failed_event_is_ignored(post_webhook, db: Session, seller_a: Seller) -> None:
    """subscription.failed = a new subscription was never created; nothing to change."""
    assert post_webhook(event("subscription.failed", seller_a.id)).status_code == 200
    sub = _sub(db, seller_a.id)
    assert sub.plan == "free" and sub.status == "active"


def test_webhook_unknown_event_ignored(post_webhook, db: Session, seller_a: Seller) -> None:
    assert post_webhook(event("payment.succeeded", seller_a.id)).status_code == 200
    assert _sub(db, seller_a.id).plan == "free"


def test_webhook_active_event_with_non_active_status_ignored(
    post_webhook, db: Session, seller_a: Seller
) -> None:
    post_webhook(event("subscription.active", seller_a.id, status="on_hold"))
    assert _sub(db, seller_a.id).plan == "free"


def test_late_active_event_does_not_revive_cancelled_subscription(
    post_webhook, db: Session, seller_a: Seller
) -> None:
    post_webhook(event("subscription.active", seller_a.id))
    post_webhook(event("subscription.cancelled", seller_a.id))
    post_webhook(event("subscription.renewed", seller_a.id))  # delivered late
    sub = _sub(db, seller_a.id)
    assert sub.plan == "free" and sub.status == "cancelled"
    # a NEW subscription can still upgrade the user
    post_webhook(event("subscription.active", seller_a.id, subscription_id="sub_2"))
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.dodo_subscription_id == "sub_2"


def test_negative_event_for_old_subscription_ignored(
    post_webhook, db: Session, seller_a: Seller
) -> None:
    post_webhook(event("subscription.active", seller_a.id, subscription_id="sub_new"))
    post_webhook(event("subscription.cancelled", seller_a.id, subscription_id="sub_old"))
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.dodo_subscription_id == "sub_new"


def test_webhook_finds_user_by_subscription_or_customer_id(
    post_webhook, db: Session, seller_a: Seller
) -> None:
    post_webhook(event("subscription.active", seller_a.id, customer={"customer_id": "cus_9"}))
    # no metadata: matched by subscription_id
    post_webhook({"type": "subscription.on_hold", "data": {"subscription_id": "sub_1"}})
    assert _sub(db, seller_a.id).status == "past_due"
    # no metadata or known subscription id: matched by customer id
    post_webhook({"type": "subscription.renewed", "data": {"customer": {"customer_id": "cus_9"}}})
    assert _sub(db, seller_a.id).status == "active"


@pytest.mark.parametrize(
    "data",
    [
        {"metadata": {"user_id": "99999"}, "subscription_id": "sub_x"},
        {"metadata": {"user_id": "not-a-number"}},
        {},
    ],
)
def test_webhook_unknown_subscription_is_acknowledged(
    post_webhook, db: Session, seller_a: Seller, data: dict
) -> None:
    resp = post_webhook({"type": "subscription.active", "data": data})
    assert resp.status_code == 200
    assert _sub(db, seller_a.id).plan == "free"


def test_webhook_bad_next_billing_date_is_tolerated(
    post_webhook, db: Session, seller_a: Seller
) -> None:
    post_webhook(event("subscription.active", seller_a.id, next_billing_date="soon"))
    sub = _sub(db, seller_a.id)
    assert sub.plan == "pro" and sub.current_period_end is None


def test_subscription_email_failure_does_not_break_webhook(
    post_webhook, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.email as email_module

    def boom(*args: object) -> None:
        raise RuntimeError("smtp down")

    monkeypatch.setattr(email_module, "send_email", boom)
    assert post_webhook(event("subscription.active", seller_a.id)).status_code == 200
    assert _sub(db, seller_a.id).plan == "pro"
