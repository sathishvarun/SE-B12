"""Contacts and tags: CRUD, search/filter, pagination, tags, plan limits, cross-seller isolation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Attachment, Deal, Task
from tests.conftest import API, Seller, create_contact, create_deal, create_task


def _tag(client: TestClient, seller: Seller, name: str) -> dict:
    resp = client.post(f"{API}/tags", json={"name": name}, headers=seller.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_contact_shape(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(
        client, seller_a, name="Ann", phone="123", company="Acme", address="Road", notes="vip"
    )
    assert set(c) == {
        "id",
        "name",
        "email",
        "phone",
        "company",
        "address",
        "notes",
        "tags",
        "created_at",
        "updated_at",
    }
    assert c["name"] == "Ann" and c["company"] == "Acme" and c["tags"] == []


def test_contact_email_optional_blank_becomes_null(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a, email="", phone="  ")
    assert c["email"] is None and c["phone"] is None
    c2 = create_contact(client, seller_a, email=None)
    assert c2["email"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"name": "X", "email": "not-an-email"},
        {"name": ""},
        {"email": "a@b.com"},
        {"name": "X" * 256},
    ],
)
def test_contact_validation_422(client: TestClient, seller_a: Seller, body: dict) -> None:
    resp = client.post(f"{API}/contacts", json=body, headers=seller_a.headers)
    assert resp.status_code == 422


def test_contacts_require_auth(client: TestClient) -> None:
    assert client.get(f"{API}/contacts").status_code == 401
    assert client.post(f"{API}/contacts", json={"name": "x"}).status_code == 401


def test_get_contact_detail_includes_deals_tasks_attachments(
    client: TestClient, seller_a: Seller
) -> None:
    c = create_contact(client, seller_a)
    deal = create_deal(client, seller_a, c["id"], value="10")
    task = create_task(client, seller_a, contact_id=c["id"])
    resp = client.get(f"{API}/contacts/{c['id']}", headers=seller_a.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [d["id"] for d in body["deals"]] == [deal["id"]]
    assert body["deals"][0]["value"] == "10.00"
    assert [t["id"] for t in body["tasks"]] == [task["id"]]
    assert body["tasks"][0]["linked_type"] == "contact"
    assert body["attachments"] == []


def test_update_contact(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a, company="Old")
    resp = client.put(
        f"{API}/contacts/{c['id']}",
        json={"name": "Renamed", "email": "new@x.com"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed" and body["email"] == "new@x.com"
    assert body["company"] is None  # PUT replaces fields


def test_update_contact_invalid_email_422(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a)
    resp = client.put(
        f"{API}/contacts/{c['id']}",
        json={"name": "X", "email": "bad"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 422


def test_delete_contact_cascades_deals_and_nulls_task_links(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    c = create_contact(client, seller_a)
    other = create_contact(client, seller_a, name="Other")
    d1 = create_deal(client, seller_a, c["id"])
    d2 = create_deal(client, seller_a, other["id"])
    task = create_task(client, seller_a, contact_id=c["id"])

    resp = client.delete(f"{API}/contacts/{c['id']}", headers=seller_a.headers)
    assert resp.status_code == 204
    assert client.get(f"{API}/contacts/{c['id']}", headers=seller_a.headers).status_code == 404
    assert db.get(Deal, d1["id"]) is None
    # task survives, link cleared (ON DELETE SET NULL)
    t = db.get(Task, task["id"])
    assert t is not None and t.contact_id is None
    # remaining deal column renumbered to 0
    remaining = db.get(Deal, d2["id"])
    assert remaining is not None and remaining.position == 0


def test_get_missing_contact_404(client: TestClient, seller_a: Seller) -> None:
    assert client.get(f"{API}/contacts/9999", headers=seller_a.headers).status_code == 404


# ---------------------------------------------------------------------------
# List / search / pagination / options
# ---------------------------------------------------------------------------


def test_list_contacts_ordered_by_name_and_paginated(client: TestClient, seller_a: Seller) -> None:
    for name in ["Charlie", "alpha", "Bravo", "Delta", "Echo"]:
        create_contact(client, seller_a, name=name, email=None)
    resp = client.get(f"{API}/contacts?page=1&page_size=2", headers=seller_a.headers)
    body = resp.json()
    assert body["total"] == 5 and body["page"] == 1 and body["page_size"] == 2
    assert len(body["items"]) == 2
    page3 = client.get(f"{API}/contacts?page=3&page_size=2", headers=seller_a.headers).json()
    assert len(page3["items"]) == 1
    all_names = [
        c["name"]
        for c in client.get(f"{API}/contacts?page_size=100", headers=seller_a.headers).json()[
            "items"
        ]
    ]
    assert all_names == sorted(all_names)


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101"])
def test_list_contacts_bad_pagination_422(client: TestClient, seller_a: Seller, query: str) -> None:
    assert client.get(f"{API}/contacts?{query}", headers=seller_a.headers).status_code == 422


def test_search_contacts_by_name_email_company(client: TestClient, seller_a: Seller) -> None:
    create_contact(client, seller_a, name="Zed", email="zed@foo.com", company="Globex")
    create_contact(client, seller_a, name="Amy", email="amy@bar.com", company="Initech")
    create_contact(client, seller_a, name="100% Real", email=None)

    def names(term: str) -> list[str]:
        r = client.get(f"{API}/contacts", params={"search": term}, headers=seller_a.headers)
        return [c["name"] for c in r.json()["items"]]

    assert names("zed") == ["Zed"]
    assert names("BAR.COM") == ["Amy"]
    assert names("glob") == ["Zed"]
    assert names("%") == ["100% Real"]  # wildcard escaped
    assert names("   ") == ["100% Real", "Amy", "Zed"]


def test_contact_options(client: TestClient, seller_a: Seller, seller_b: Seller) -> None:
    create_contact(client, seller_a, name="B", company="Co")
    create_contact(client, seller_a, name="A")
    create_contact(client, seller_b, name="NotMine")
    resp = client.get(f"{API}/contacts/options", headers=seller_a.headers)
    assert resp.status_code == 200
    assert resp.json() == [
        {"id": resp.json()[0]["id"], "name": "A", "company": None},
        {"id": resp.json()[1]["id"], "name": "B", "company": "Co"},
    ]


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def test_create_and_list_tags(client: TestClient, seller_a: Seller) -> None:
    _tag(client, seller_a, "vip")
    _tag(client, seller_a, "  cold ")
    resp = client.get(f"{API}/tags", headers=seller_a.headers)
    assert [t["name"] for t in resp.json()] == ["cold", "vip"]


def test_duplicate_tag_409_but_unique_per_seller(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    _tag(client, seller_a, "vip")
    dup = client.post(f"{API}/tags", json={"name": "vip"}, headers=seller_a.headers)
    assert dup.status_code == 409
    # another seller can use the same name
    _tag(client, seller_b, "vip")
    assert [t["name"] for t in client.get(f"{API}/tags", headers=seller_b.headers).json()] == [
        "vip"
    ]


@pytest.mark.parametrize("name", ["", "   ", "x" * 51])
def test_tag_validation_422(client: TestClient, seller_a: Seller, name: str) -> None:
    assert (
        client.post(f"{API}/tags", json={"name": name}, headers=seller_a.headers).status_code == 422
    )


def test_contact_with_tags_filter_and_replace(client: TestClient, seller_a: Seller) -> None:
    vip = _tag(client, seller_a, "vip")
    cold = _tag(client, seller_a, "cold")
    c1 = create_contact(client, seller_a, name="One", tag_ids=[vip["id"], cold["id"], vip["id"]])
    create_contact(client, seller_a, name="Two", tag_ids=[cold["id"]])
    assert sorted(t["name"] for t in c1["tags"]) == ["cold", "vip"]

    by_vip = client.get(f"{API}/contacts?tag_id={vip['id']}", headers=seller_a.headers).json()
    assert [c["name"] for c in by_vip["items"]] == ["One"]
    assert by_vip["total"] == 1

    # update without tag_ids keeps tags
    kept = client.put(
        f"{API}/contacts/{c1['id']}", json={"name": "One"}, headers=seller_a.headers
    ).json()
    assert len(kept["tags"]) == 2
    # update with tag_ids replaces them
    replaced = client.put(
        f"{API}/contacts/{c1['id']}",
        json={"name": "One", "tag_ids": [cold["id"]]},
        headers=seller_a.headers,
    ).json()
    assert [t["name"] for t in replaced["tags"]] == ["cold"]
    cleared = client.put(
        f"{API}/contacts/{c1['id']}",
        json={"name": "One", "tag_ids": []},
        headers=seller_a.headers,
    ).json()
    assert cleared["tags"] == []


def test_cannot_attach_other_sellers_tag(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    b_tag = _tag(client, seller_b, "theirs")
    resp = client.post(
        f"{API}/contacts", json={"name": "X", "tag_ids": [b_tag["id"]]}, headers=seller_a.headers
    )
    assert resp.status_code == 404
    mine = create_contact(client, seller_a)
    upd = client.put(
        f"{API}/contacts/{mine['id']}",
        json={"name": "X", "tag_ids": [b_tag["id"]]},
        headers=seller_a.headers,
    )
    assert upd.status_code == 404


def test_tag_filter_with_other_sellers_tag_returns_nothing(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    b_tag = _tag(client, seller_b, "theirs")
    create_contact(client, seller_b, name="B's", tag_ids=[b_tag["id"]])
    create_contact(client, seller_a, name="A's")
    resp = client.get(f"{API}/contacts?tag_id={b_tag['id']}", headers=seller_a.headers).json()
    assert resp["items"] == [] and resp["total"] == 0


# ---------------------------------------------------------------------------
# Free plan limit
# ---------------------------------------------------------------------------


def test_free_plan_contact_limit_402(
    client: TestClient, seller_a: Seller, seller_b: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_CONTACTS", 2)
    create_contact(client, seller_a, name="1")
    create_contact(client, seller_a, name="2")
    resp = client.post(f"{API}/contacts", json={"name": "3"}, headers=seller_a.headers)
    assert resp.status_code == 402
    assert "2 contacts" in resp.json()["detail"]
    # limit is per seller
    create_contact(client, seller_b, name="b1")


def test_pro_plan_has_no_contact_limit(
    client: TestClient, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models import Subscription

    monkeypatch.setattr(settings, "FREE_PLAN_MAX_CONTACTS", 1)
    sub = db.scalar(select(Subscription).where(Subscription.user_id == seller_a.id))
    assert sub is not None
    sub.plan = "pro"  # type: ignore[assignment]
    db.commit()
    create_contact(client, seller_a, name="1")
    create_contact(client, seller_a, name="2")


# ---------------------------------------------------------------------------
# Cross-seller isolation
# ---------------------------------------------------------------------------


def test_cross_seller_contact_access_is_404(
    client: TestClient, db: Session, seller_a: Seller, seller_b: Seller
) -> None:
    c = create_contact(client, seller_a, name="Secret")
    url = f"{API}/contacts/{c['id']}"
    assert client.get(url, headers=seller_b.headers).status_code == 404
    assert client.put(url, json={"name": "Hacked"}, headers=seller_b.headers).status_code == 404
    assert client.delete(url, headers=seller_b.headers).status_code == 404
    # B's list doesn't include A's contact
    listing = client.get(f"{API}/contacts", headers=seller_b.headers).json()
    assert listing["items"] == [] and listing["total"] == 0
    assert client.get(f"{API}/contacts/options", headers=seller_b.headers).json() == []
    # A's record is untouched
    assert client.get(url, headers=seller_a.headers).json()["name"] == "Secret"


def test_attachments_cascade_on_contact_delete(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    c = create_contact(client, seller_a)
    up = client.post(
        f"{API}/attachments",
        files={"file": ("a.pdf", b"%PDF-1.4 data", "application/pdf")},
        data={"contact_id": str(c["id"])},
        headers=seller_a.headers,
    )
    assert up.status_code == 201
    client.delete(f"{API}/contacts/{c['id']}", headers=seller_a.headers)
    assert db.get(Attachment, up.json()["id"]) is None
