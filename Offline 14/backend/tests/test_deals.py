"""Deals: CRUD, decimal value, board/positions, stage moves (closed_at), limits, isolation."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Deal
from tests.conftest import API, Seller, create_contact, create_deal, create_task


@pytest.fixture
def contact(client: TestClient, seller_a: Seller) -> dict:
    return create_contact(client, seller_a, name="Buyer", company="BuyCo")


def _move(client: TestClient, seller: Seller, deal_id: int, stage: str, position: int = 0):
    return client.patch(
        f"{API}/deals/{deal_id}/stage",
        json={"stage": stage, "position": position},
        headers=seller.headers,
    )


def _board_ids(client: TestClient, seller: Seller) -> dict[str, list[int]]:
    board = client.get(f"{API}/deals/board", headers=seller.headers).json()
    return {stage: [d["id"] for d in deals] for stage, deals in board.items()}


# ---------------------------------------------------------------------------
# Create / value rules
# ---------------------------------------------------------------------------


def test_create_deal_shape_and_defaults(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"], value=1500, currency="usd")
    assert d["value"] == "1500.00"
    assert isinstance(d["value"], str)
    assert d["currency"] == "USD"
    assert d["stage"] == "prospect"
    assert d["position"] == 0
    assert d["closed_at"] is None
    assert d["contact"] == {"id": contact["id"], "name": "Buyer", "company": "BuyCo"}
    assert set(d) == {
        "id",
        "title",
        "value",
        "currency",
        "stage",
        "expected_close_date",
        "contact_id",
        "contact",
        "position",
        "notes",
        "closed_at",
        "created_at",
        "updated_at",
    }


def test_default_value_and_currency(client: TestClient, seller_a: Seller, contact: dict) -> None:
    resp = client.post(
        f"{API}/deals", json={"title": "T", "contact_id": contact["id"]}, headers=seller_a.headers
    )
    assert resp.status_code == 201
    assert resp.json()["value"] == "0.00" and resp.json()["currency"] == "INR"


def test_value_stored_as_exact_decimal(
    client: TestClient, db: Session, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"], value="0.10")
    stored = db.get(Deal, d["id"])
    assert stored is not None
    assert isinstance(stored.value, Decimal)
    assert stored.value == Decimal("0.10")
    assert d["value"] == "0.10"


@pytest.mark.parametrize("value", ["-0.01", -5, "abc", "1.001", "10000000000.00"])
def test_invalid_value_422(client: TestClient, seller_a: Seller, contact: dict, value) -> None:
    resp = client.post(
        f"{API}/deals",
        json={"title": "T", "contact_id": contact["id"], "value": value},
        headers=seller_a.headers,
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "patch", [{"stage": "closed"}, {"currency": "RUPEE"}, {"title": ""}, {"contact_id": None}]
)
def test_deal_validation_422(
    client: TestClient, seller_a: Seller, contact: dict, patch: dict
) -> None:
    body = {"title": "T", "contact_id": contact["id"], "value": "1", **patch}
    assert client.post(f"{API}/deals", json=body, headers=seller_a.headers).status_code == 422


def test_create_deal_with_unknown_contact_404(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(
        f"{API}/deals", json={"title": "T", "contact_id": 999}, headers=seller_a.headers
    )
    assert resp.status_code == 404


def test_create_deal_in_closed_stage_sets_closed_at(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"], stage="won")
    assert d["stage"] == "won" and d["closed_at"] is not None


# ---------------------------------------------------------------------------
# Read / list / board
# ---------------------------------------------------------------------------


def test_get_deal_detail_has_tasks_and_attachments(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"])
    t = create_task(client, seller_a, deal_id=d["id"])
    body = client.get(f"{API}/deals/{d['id']}", headers=seller_a.headers).json()
    assert [x["id"] for x in body["tasks"]] == [t["id"]]
    assert body["tasks"][0]["linked_type"] == "deal"
    assert body["tasks"][0]["linked_name"] == d["title"]
    assert body["attachments"] == []


def test_list_deals_filters(client: TestClient, seller_a: Seller, contact: dict) -> None:
    other = create_contact(client, seller_a, name="Other")
    d1 = create_deal(client, seller_a, contact["id"])
    d2 = create_deal(client, seller_a, other["id"], stage="proposal")
    d3 = create_deal(client, seller_a, contact["id"], stage="won")

    def ids(q: str = "") -> list[int]:
        return [
            x["id"] for x in client.get(f"{API}/deals{q}", headers=seller_a.headers).json()["items"]
        ]

    assert ids() == [d3["id"], d2["id"], d1["id"]]  # newest first
    assert ids("?stage=proposal") == [d2["id"]]
    assert ids(f"?contact_id={contact['id']}") == [d3["id"], d1["id"]]
    assert client.get(f"{API}/deals?stage=nope", headers=seller_a.headers).status_code == 422


def test_board_has_all_stages_ordered_by_position(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    a = create_deal(client, seller_a, contact["id"], title="A")
    b = create_deal(client, seller_a, contact["id"], title="B")
    c = create_deal(client, seller_a, contact["id"], title="C", stage="negotiation")
    board = _board_ids(client, seller_a)
    assert set(board) == {"prospect", "proposal", "negotiation", "won", "lost"}
    assert board["prospect"] == [a["id"], b["id"]]
    assert board["negotiation"] == [c["id"]]
    assert board["proposal"] == board["won"] == board["lost"] == []


# ---------------------------------------------------------------------------
# Moving / closed_at
# ---------------------------------------------------------------------------


def test_move_to_won_sets_closed_at_and_back_clears(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"])
    won = _move(client, seller_a, d["id"], "won")
    assert won.status_code == 200
    assert won.json()["stage"] == "won" and won.json()["closed_at"] is not None
    closed_at = won.json()["closed_at"]

    # won -> lost keeps the original close time
    lost = _move(client, seller_a, d["id"], "lost").json()
    assert lost["stage"] == "lost"
    # SQLite drops tzinfo on reload, so compare the wall-clock part only
    assert lost["closed_at"].rstrip("Z") == closed_at.rstrip("Z")

    reopened = _move(client, seller_a, d["id"], "negotiation").json()
    assert reopened["stage"] == "negotiation" and reopened["closed_at"] is None


def test_move_reorders_columns(client: TestClient, seller_a: Seller, contact: dict) -> None:
    a = create_deal(client, seller_a, contact["id"], title="A")
    b = create_deal(client, seller_a, contact["id"], title="B")
    c = create_deal(client, seller_a, contact["id"], title="C")
    # reorder within column: C to top
    assert _move(client, seller_a, c["id"], "prospect", 0).json()["position"] == 0
    assert _board_ids(client, seller_a)["prospect"] == [c["id"], a["id"], b["id"]]
    # move A to proposal; prospect column renumbered
    _move(client, seller_a, a["id"], "proposal", 5)  # beyond end -> appended
    board = _board_ids(client, seller_a)
    assert board["prospect"] == [c["id"], b["id"]]
    assert board["proposal"] == [a["id"]]
    full = client.get(f"{API}/deals/board", headers=seller_a.headers).json()
    assert [d["position"] for d in full["prospect"]] == [0, 1]
    assert full["proposal"][0]["position"] == 0
    # insert B at top of proposal
    _move(client, seller_a, b["id"], "proposal", 0)
    assert _board_ids(client, seller_a)["proposal"] == [b["id"], a["id"]]


@pytest.mark.parametrize(
    "body", [{"stage": "won"}, {"stage": "won", "position": -1}, {"stage": "bad", "position": 0}]
)
def test_move_validation_422(client: TestClient, seller_a: Seller, contact: dict, body) -> None:
    d = create_deal(client, seller_a, contact["id"])
    resp = client.patch(f"{API}/deals/{d['id']}/stage", json=body, headers=seller_a.headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Update / delete
# ---------------------------------------------------------------------------


def test_update_deal_fields_and_stage(client: TestClient, seller_a: Seller, contact: dict) -> None:
    other = create_contact(client, seller_a, name="Second")
    d = create_deal(client, seller_a, contact["id"])
    resp = client.put(
        f"{API}/deals/{d['id']}",
        json={
            "title": "Renamed",
            "contact_id": other["id"],
            "value": "99.9",
            "stage": "lost",
            "notes": "n",
            "expected_close_date": "2026-01-02",
        },
        headers=seller_a.headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Renamed"
    assert body["contact_id"] == other["id"] and body["contact"]["name"] == "Second"
    assert body["value"] == "99.90"
    assert body["stage"] == "lost" and body["closed_at"] is not None
    assert body["notes"] == "n" and body["expected_close_date"] == "2026-01-02"

    # omitting stage keeps it
    kept = client.put(
        f"{API}/deals/{d['id']}",
        json={"title": "R2", "contact_id": other["id"], "value": 1},
        headers=seller_a.headers,
    ).json()
    assert kept["stage"] == "lost" and kept["closed_at"] is not None

    reopened = client.put(
        f"{API}/deals/{d['id']}",
        json={"title": "R2", "contact_id": other["id"], "value": 1, "stage": "prospect"},
        headers=seller_a.headers,
    ).json()
    assert reopened["closed_at"] is None


def test_update_deal_negative_value_422(
    client: TestClient, seller_a: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"])
    resp = client.put(
        f"{API}/deals/{d['id']}",
        json={"title": "T", "contact_id": contact["id"], "value": "-1"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 422


def test_delete_deal_compacts_column(client: TestClient, seller_a: Seller, contact: dict) -> None:
    a = create_deal(client, seller_a, contact["id"])
    b = create_deal(client, seller_a, contact["id"])
    assert client.delete(f"{API}/deals/{a['id']}", headers=seller_a.headers).status_code == 204
    assert client.get(f"{API}/deals/{a['id']}", headers=seller_a.headers).status_code == 404
    board = client.get(f"{API}/deals/board", headers=seller_a.headers).json()
    assert [(d["id"], d["position"]) for d in board["prospect"]] == [(b["id"], 0)]


# ---------------------------------------------------------------------------
# Free plan open-deal limit
# ---------------------------------------------------------------------------


def test_free_plan_open_deal_limit(
    client: TestClient, seller_a: Seller, contact: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "FREE_PLAN_MAX_OPEN_DEALS", 2)
    d1 = create_deal(client, seller_a, contact["id"])
    create_deal(client, seller_a, contact["id"])
    blocked = client.post(
        f"{API}/deals", json={"title": "3", "contact_id": contact["id"]}, headers=seller_a.headers
    )
    assert blocked.status_code == 402
    # closed deals don't count and can always be created
    create_deal(client, seller_a, contact["id"], stage="won")
    # closing one frees a slot
    _move(client, seller_a, d1["id"], "lost")
    create_deal(client, seller_a, contact["id"], title="3")
    # re-opening the closed deal now exceeds the limit
    assert _move(client, seller_a, d1["id"], "prospect").status_code == 402
    reopen_via_put = client.put(
        f"{API}/deals/{d1['id']}",
        json={"title": "x", "contact_id": contact["id"], "stage": "proposal"},
        headers=seller_a.headers,
    )
    assert reopen_via_put.status_code == 402


# ---------------------------------------------------------------------------
# Cross-seller isolation
# ---------------------------------------------------------------------------


def test_cross_seller_deal_access_is_404(
    client: TestClient, seller_a: Seller, seller_b: Seller, contact: dict
) -> None:
    d = create_deal(client, seller_a, contact["id"])
    b_contact = create_contact(client, seller_b)
    url = f"{API}/deals/{d['id']}"
    h = seller_b.headers
    assert client.get(url, headers=h).status_code == 404
    assert (
        client.put(url, json={"title": "x", "contact_id": b_contact["id"]}, headers=h).status_code
        == 404
    )
    assert _move(client, seller_b, d["id"], "won").status_code == 404
    assert client.delete(url, headers=h).status_code == 404
    assert client.get(f"{API}/deals", headers=h).json()["total"] == 0
    assert all(v == [] for v in _board_ids(client, seller_b).values())
    still = client.get(url, headers=seller_a.headers).json()
    assert still["stage"] == "prospect" and still["title"] == d["title"]


def test_cannot_link_deal_to_other_sellers_contact(
    client: TestClient, seller_a: Seller, seller_b: Seller, contact: dict
) -> None:
    resp = client.post(
        f"{API}/deals", json={"title": "x", "contact_id": contact["id"]}, headers=seller_b.headers
    )
    assert resp.status_code == 404
    b_contact = create_contact(client, seller_b)
    b_deal = create_deal(client, seller_b, b_contact["id"])
    resp = client.put(
        f"{API}/deals/{b_deal['id']}",
        json={"title": "x", "contact_id": contact["id"]},
        headers=seller_b.headers,
    )
    assert resp.status_code == 404
