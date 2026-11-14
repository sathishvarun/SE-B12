"""Admin: access control (403), user list/search, update flags, stats."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Subscription, User
from tests.conftest import API, PASSWORD, Seller, create_contact, create_deal


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admin/users"),
        ("put", "/admin/users/1"),
        ("get", "/admin/stats"),
    ],
)
def test_non_admin_gets_403(client: TestClient, seller_a: Seller, method: str, path: str) -> None:
    kwargs = {"json": {"is_active": False}} if method == "put" else {}
    resp = getattr(client, method)(f"{API}{path}", headers=seller_a.headers, **kwargs)
    assert resp.status_code == 403


@pytest.mark.parametrize("path", ["/admin/users", "/admin/stats"])
def test_unauthenticated_gets_401(client: TestClient, path: str) -> None:
    assert client.get(f"{API}{path}").status_code == 401


def test_list_users(client: TestClient, admin: Seller, seller_a: Seller, seller_b: Seller) -> None:
    resp = client.get(f"{API}/admin/users", headers=admin.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3 and body["page"] == 1 and body["page_size"] == 20
    emails = [u["email"] for u in body["items"]]
    assert set(emails) == {"admin@example.com", "alice@example.com", "bob@example.com"}
    assert emails[0] == "bob@example.com"  # newest first
    item = body["items"][0]
    assert set(item) == {"id", "email", "full_name", "is_active", "is_admin", "plan", "created_at"}
    assert item["plan"] == "free"


def test_list_users_search_and_pagination(
    client: TestClient, admin: Seller, seller_a: Seller, seller_b: Seller
) -> None:
    def emails(**params: str) -> list[str]:
        r = client.get(f"{API}/admin/users", params=params, headers=admin.headers)
        return [u["email"] for u in r.json()["items"]]

    assert emails(search="alice") == ["alice@example.com"]
    assert emails(search="Bob Seller") == ["bob@example.com"]  # matches full_name
    assert emails(search="%") == []  # wildcard escaped -> literal match
    assert emails(search="_") == []
    page = client.get(f"{API}/admin/users?page=2&page_size=2", headers=admin.headers).json()
    assert page["total"] == 3 and len(page["items"]) == 1


def test_user_without_subscription_shows_free(
    client: TestClient, db: Session, admin: Seller
) -> None:
    db.add(User(email="nosub@example.com", hashed_password=None))
    db.commit()
    items = client.get(
        f"{API}/admin/users", params={"search": "nosub"}, headers=admin.headers
    ).json()["items"]
    assert items[0]["plan"] == "free"


def test_deactivate_user_blocks_access_and_revokes_tokens(
    client: TestClient, admin: Seller, seller_a: Seller
) -> None:
    resp = client.put(
        f"{API}/admin/users/{seller_a.id}", json={"is_active": False}, headers=admin.headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert client.get(f"{API}/auth/me", headers=seller_a.headers).status_code == 403
    assert (
        client.post(
            f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token}
        ).status_code
        == 401
    )
    login = client.post(f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD})
    assert login.status_code == 403

    # reactivate
    resp = client.put(
        f"{API}/admin/users/{seller_a.id}", json={"is_active": True}, headers=admin.headers
    )
    assert resp.json()["is_active"] is True
    login = client.post(f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD})
    assert login.status_code == 200


def test_grant_and_revoke_admin(client: TestClient, admin: Seller, seller_a: Seller) -> None:
    resp = client.put(
        f"{API}/admin/users/{seller_a.id}", json={"is_admin": True}, headers=admin.headers
    )
    assert resp.status_code == 200 and resp.json()["is_admin"] is True
    assert client.get(f"{API}/admin/stats", headers=seller_a.headers).status_code == 200
    client.put(f"{API}/admin/users/{seller_a.id}", json={"is_admin": False}, headers=admin.headers)
    assert client.get(f"{API}/admin/stats", headers=seller_a.headers).status_code == 403


def test_empty_update_is_noop(client: TestClient, admin: Seller, seller_a: Seller) -> None:
    resp = client.put(f"{API}/admin/users/{seller_a.id}", json={}, headers=admin.headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True and resp.json()["is_admin"] is False


@pytest.mark.parametrize("body", [{"is_active": False}, {"is_admin": False}])
def test_admin_cannot_change_own_flags_400(client: TestClient, admin: Seller, body: dict) -> None:
    resp = client.put(f"{API}/admin/users/{admin.id}", json=body, headers=admin.headers)
    assert resp.status_code == 400


def test_update_missing_user_404(client: TestClient, admin: Seller) -> None:
    resp = client.put(f"{API}/admin/users/9999", json={"is_active": False}, headers=admin.headers)
    assert resp.status_code == 404


def test_update_validation_422(client: TestClient, admin: Seller, seller_a: Seller) -> None:
    resp = client.put(
        f"{API}/admin/users/{seller_a.id}", json={"is_active": "maybe"}, headers=admin.headers
    )
    assert resp.status_code == 422


def test_stats(
    client: TestClient, db: Session, admin: Seller, seller_a: Seller, seller_b: Seller
) -> None:
    c = create_contact(client, seller_a)
    create_contact(client, seller_b)
    create_deal(client, seller_a, c["id"])
    sub = db.scalar(select(Subscription).where(Subscription.user_id == seller_b.id))
    assert sub is not None
    sub.plan = "pro"  # type: ignore[assignment]
    db.commit()
    client.put(f"{API}/admin/users/{seller_a.id}", json={"is_active": False}, headers=admin.headers)

    resp = client.get(f"{API}/admin/stats", headers=admin.headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "total_users": 3,
        "active_users": 2,
        "pro_subscriptions": 1,
        "signups_last_30_days": 3,
        "total_contacts": 2,
        "total_deals": 1,
    }
