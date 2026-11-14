"""Leads: CRUD, filters, status changes, conversion (single transaction), isolation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Contact, Deal, Lead
from tests.conftest import API, Seller, create_contact, create_deal, create_lead

CONVERT_BODY = {"deal_title": "First order", "deal_value": "2500.5"}


def test_create_lead_defaults(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(f"{API}/leads", json={"name": "L", "email": ""}, headers=seller_a.headers)
    assert resp.status_code == 201
    lead = resp.json()
    assert lead["status"] == "new"
    assert lead["source"] == "other"
    assert lead["email"] is None
    assert lead["converted_contact_id"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"name": "L", "source": "tv"},
        {"name": "L", "email": "nope"},
        {"name": ""},
    ],
)
def test_create_lead_validation_422(client: TestClient, seller_a: Seller, body: dict) -> None:
    assert client.post(f"{API}/leads", json=body, headers=seller_a.headers).status_code == 422


@pytest.mark.parametrize("source", ["website", "referral", "social", "other"])
def test_all_lead_sources_accepted(client: TestClient, seller_a: Seller, source: str) -> None:
    assert create_lead(client, seller_a, source=source)["source"] == source


def test_status_is_not_settable_on_create(client: TestClient, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a, status="qualified")
    assert lead["status"] == "new"


def test_get_update_delete_lead(client: TestClient, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a)
    url = f"{API}/leads/{lead['id']}"
    assert client.get(url, headers=seller_a.headers).json()["name"] == "Lenny Lead"
    upd = client.put(
        url, json={"name": "Lenny 2", "source": "social"}, headers=seller_a.headers
    ).json()
    assert upd["name"] == "Lenny 2" and upd["source"] == "social" and upd["email"] is None
    assert client.delete(url, headers=seller_a.headers).status_code == 204
    assert client.get(url, headers=seller_a.headers).status_code == 404


def test_list_leads_filters_and_newest_first(client: TestClient, seller_a: Seller) -> None:
    first = create_lead(client, seller_a, name="First", source="website", company="Acme")
    second = create_lead(client, seller_a, name="Second", source="referral")
    third = create_lead(client, seller_a, name="Third", source="website")
    client.patch(
        f"{API}/leads/{third['id']}/status", json={"status": "lost"}, headers=seller_a.headers
    )

    all_ = client.get(f"{API}/leads", headers=seller_a.headers).json()
    assert [x["id"] for x in all_["items"]] == [third["id"], second["id"], first["id"]]
    assert all_["total"] == 3

    def ids(**params: str) -> list[int]:
        r = client.get(f"{API}/leads", params=params, headers=seller_a.headers)
        assert r.status_code == 200
        return [x["id"] for x in r.json()["items"]]

    assert ids(source="website") == [third["id"], first["id"]]
    assert ids(status="lost") == [third["id"]]
    assert ids(search="acme") == [first["id"]]
    assert ids(status="new", source="website") == [first["id"]]
    assert client.get(f"{API}/leads?status=bogus", headers=seller_a.headers).status_code == 422


@pytest.mark.parametrize("status", ["new", "contacted", "qualified", "lost"])
def test_patch_status(client: TestClient, seller_a: Seller, status: str) -> None:
    lead = create_lead(client, seller_a)
    resp = client.patch(
        f"{API}/leads/{lead['id']}/status", json={"status": status}, headers=seller_a.headers
    )
    assert resp.status_code == 200 and resp.json()["status"] == status


def test_patch_status_converted_is_400(client: TestClient, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a)
    resp = client.patch(
        f"{API}/leads/{lead['id']}/status", json={"status": "converted"}, headers=seller_a.headers
    )
    assert resp.status_code == 400


def test_patch_status_invalid_value_422(client: TestClient, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a)
    resp = client.patch(
        f"{API}/leads/{lead['id']}/status", json={"status": "won"}, headers=seller_a.headers
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def test_convert_lead_creates_contact_and_deal(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    lead = create_lead(client, seller_a, phone="555", company="LeadCo", notes="hot")
    resp = client.post(
        f"{API}/leads/{lead['id']}/convert",
        json={**CONVERT_BODY, "expected_close_date": "2026-12-31"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert set(body) == {"lead", "contact", "deal"}
    contact, deal, converted = body["contact"], body["deal"], body["lead"]

    assert converted["status"] == "converted"
    assert converted["converted_contact_id"] == contact["id"]
    assert contact["name"] == lead["name"]
    assert contact["email"] == lead["email"]
    assert contact["phone"] == "555" and contact["company"] == "LeadCo"
    assert deal["contact_id"] == contact["id"]
    assert deal["title"] == "First order"
    assert deal["value"] == "2500.50"
    assert deal["stage"] == "prospect"
    assert deal["expected_close_date"] == "2026-12-31"
    assert deal["closed_at"] is None
    assert deal["contact"] == {"id": contact["id"], "name": lead["name"], "company": "LeadCo"}

    # persisted
    assert (
        client.get(f"{API}/contacts/{contact['id']}", headers=seller_a.headers).status_code == 200
    )
    assert client.get(f"{API}/deals/{deal['id']}", headers=seller_a.headers).status_code == 200


def test_convert_twice_is_409(client: TestClient, db: Session, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a)
    url = f"{API}/leads/{lead['id']}/convert"
    assert client.post(url, json=CONVERT_BODY, headers=seller_a.headers).status_code == 201
    again = client.post(url, json=CONVERT_BODY, headers=seller_a.headers)
    assert again.status_code == 409
    assert db.scalar(select(func.count(Contact.id))) == 1
    assert db.scalar(select(func.count(Deal.id))) == 1


def test_converted_lead_status_cannot_change(client: TestClient, seller_a: Seller) -> None:
    lead = create_lead(client, seller_a)
    client.post(f"{API}/leads/{lead['id']}/convert", json=CONVERT_BODY, headers=seller_a.headers)
    resp = client.patch(
        f"{API}/leads/{lead['id']}/status", json={"status": "new"}, headers=seller_a.headers
    )
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        {"deal_title": "", "deal_value": "1"},
        {"deal_title": "T", "deal_value": "-1"},
        {"deal_title": "T", "deal_value": "1.234"},
        {"deal_title": "T"},
    ],
)
def test_convert_validation_422(client: TestClient, seller_a: Seller, body: dict) -> None:
    lead = create_lead(client, seller_a)
    resp = client.post(f"{API}/leads/{lead['id']}/convert", json=body, headers=seller_a.headers)
    assert resp.status_code == 422


def test_convert_rolls_back_when_deal_limit_hit(
    client: TestClient, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single transaction: if the deal can't be created, no contact is left behind."""
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_OPEN_DEALS", 1)
    c = create_contact(client, seller_a)
    create_deal(client, seller_a, c["id"])
    lead = create_lead(client, seller_a)
    resp = client.post(
        f"{API}/leads/{lead['id']}/convert", json=CONVERT_BODY, headers=seller_a.headers
    )
    assert resp.status_code == 402
    db.expire_all()
    assert db.scalar(select(func.count(Contact.id))) == 1  # only the pre-existing one
    stored = db.get(Lead, lead["id"])
    assert stored is not None
    assert stored.status == "new" and stored.converted_contact_id is None


def test_convert_blocked_by_contact_limit(
    client: TestClient, db: Session, seller_a: Seller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_CONTACTS", 1)
    create_contact(client, seller_a)
    lead = create_lead(client, seller_a)
    resp = client.post(
        f"{API}/leads/{lead['id']}/convert", json=CONVERT_BODY, headers=seller_a.headers
    )
    assert resp.status_code == 402
    assert db.scalar(select(func.count(Deal.id))) == 0


def test_deleting_converted_contact_keeps_lead_with_null_link(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    lead = create_lead(client, seller_a)
    contact_id = client.post(
        f"{API}/leads/{lead['id']}/convert", json=CONVERT_BODY, headers=seller_a.headers
    ).json()["contact"]["id"]
    client.delete(f"{API}/contacts/{contact_id}", headers=seller_a.headers)
    got = client.get(f"{API}/leads/{lead['id']}", headers=seller_a.headers).json()
    assert got["status"] == "converted" and got["converted_contact_id"] is None


# ---------------------------------------------------------------------------
# Cross-seller isolation
# ---------------------------------------------------------------------------


def test_cross_seller_lead_access_is_404(
    client: TestClient, db: Session, seller_a: Seller, seller_b: Seller
) -> None:
    lead = create_lead(client, seller_a)
    url = f"{API}/leads/{lead['id']}"
    h = seller_b.headers
    assert client.get(url, headers=h).status_code == 404
    assert client.put(url, json={"name": "x"}, headers=h).status_code == 404
    assert client.patch(f"{url}/status", json={"status": "lost"}, headers=h).status_code == 404
    assert client.post(f"{url}/convert", json=CONVERT_BODY, headers=h).status_code == 404
    assert client.delete(url, headers=h).status_code == 404
    assert client.get(f"{API}/leads", headers=h).json()["total"] == 0
    # nothing created for B by the failed convert
    assert db.scalar(select(func.count(Contact.id))) == 0
    still = client.get(url, headers=seller_a.headers).json()
    assert still["status"] == "new" and still["name"] == lead["name"]
