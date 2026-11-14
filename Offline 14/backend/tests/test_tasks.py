"""Tasks: CRUD, link rules, views, overdue logic, completion, reminder re-arm, isolation."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Task
from tests.conftest import (
    API,
    Seller,
    app_today,
    create_contact,
    create_deal,
    create_lead,
    create_task,
)

TODAY = app_today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


def test_create_task_defaults_and_shape(client: TestClient, seller_a: Seller) -> None:
    t = create_task(client, seller_a)
    assert t["priority"] == "medium"
    assert t["status"] == "pending"
    assert t["linked_type"] is None and t["linked_name"] is None
    assert t["is_overdue"] is False and t["completed_at"] is None
    assert set(t) == {
        "id",
        "title",
        "description",
        "due_date",
        "priority",
        "status",
        "contact_id",
        "lead_id",
        "deal_id",
        "linked_type",
        "linked_name",
        "is_overdue",
        "completed_at",
        "created_at",
        "updated_at",
    }


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "x", "priority": "urgent"},
        {"title": "x", "due_date": "not-a-date"},
    ],
)
def test_task_validation_422(client: TestClient, seller_a: Seller, body: dict) -> None:
    assert client.post(f"{API}/tasks", json=body, headers=seller_a.headers).status_code == 422


def test_status_cannot_be_set_via_create(client: TestClient, seller_a: Seller) -> None:
    t = create_task(client, seller_a, status="done")
    assert t["status"] == "pending"


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_priorities(client: TestClient, seller_a: Seller, priority: str) -> None:
    assert create_task(client, seller_a, priority=priority)["priority"] == priority


def test_link_to_each_record_type(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a, name="Cathy")
    lead = create_lead(client, seller_a, name="Larry")
    d = create_deal(client, seller_a, c["id"], title="Dealio")
    tc = create_task(client, seller_a, contact_id=c["id"])
    tl = create_task(client, seller_a, lead_id=lead["id"])
    td = create_task(client, seller_a, deal_id=d["id"])
    assert (tc["linked_type"], tc["linked_name"]) == ("contact", "Cathy")
    assert (tl["linked_type"], tl["linked_name"]) == ("lead", "Larry")
    assert (td["linked_type"], td["linked_name"]) == ("deal", "Dealio")


@pytest.mark.parametrize(
    "links", [("contact_id", "lead_id"), ("contact_id", "deal_id"), ("lead_id", "deal_id")]
)
def test_more_than_one_link_is_400(client: TestClient, seller_a: Seller, links) -> None:
    c = create_contact(client, seller_a)
    ids = {
        "contact_id": c["id"],
        "lead_id": create_lead(client, seller_a)["id"],
        "deal_id": create_deal(client, seller_a, c["id"])["id"],
    }
    body = {"title": "x", **{k: ids[k] for k in links}}
    resp = client.post(f"{API}/tasks", json=body, headers=seller_a.headers)
    assert resp.status_code == 400
    # also on update
    t = create_task(client, seller_a)
    upd = client.put(f"{API}/tasks/{t['id']}", json=body, headers=seller_a.headers)
    assert upd.status_code == 400


def test_all_three_links_is_400(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(
        f"{API}/tasks",
        json={"title": "x", "contact_id": 1, "lead_id": 1, "deal_id": 1},
        headers=seller_a.headers,
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("field", ["contact_id", "lead_id", "deal_id"])
def test_link_to_missing_record_404(client: TestClient, seller_a: Seller, field: str) -> None:
    resp = client.post(f"{API}/tasks", json={"title": "x", field: 999}, headers=seller_a.headers)
    assert resp.status_code == 404


def test_overdue_flag(client: TestClient, seller_a: Seller) -> None:
    assert create_task(client, seller_a, due_date=YESTERDAY)["is_overdue"] is True
    assert create_task(client, seller_a, due_date=TODAY.isoformat())["is_overdue"] is False
    assert create_task(client, seller_a, due_date=TOMORROW)["is_overdue"] is False
    assert create_task(client, seller_a)["is_overdue"] is False


def test_completing_overdue_task_clears_overdue(client: TestClient, seller_a: Seller) -> None:
    t = create_task(client, seller_a, due_date=YESTERDAY)
    resp = client.patch(f"{API}/tasks/{t['id']}/complete", headers=seller_a.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done" and body["completed_at"] is not None
    assert body["is_overdue"] is False
    # completing twice is a no-op (completed_at unchanged)
    again = client.patch(f"{API}/tasks/{t['id']}/complete", headers=seller_a.headers).json()
    assert (
        again["completed_at"] == body["completed_at"].rstrip("Z")
        or again["completed_at"] == body["completed_at"]
    )


def test_views(client: TestClient, seller_a: Seller) -> None:
    overdue = create_task(client, seller_a, title="overdue", due_date=YESTERDAY)
    today = create_task(client, seller_a, title="today", due_date=TODAY.isoformat())
    later = create_task(client, seller_a, title="later", due_date=TOMORROW)
    nodate = create_task(client, seller_a, title="nodate")
    done = create_task(client, seller_a, title="done", due_date=YESTERDAY)
    client.patch(f"{API}/tasks/{done['id']}/complete", headers=seller_a.headers)

    def ids(view: str | None = None) -> list[int]:
        params = {"view": view} if view else {}
        r = client.get(f"{API}/tasks", params=params, headers=seller_a.headers)
        assert r.status_code == 200
        return [t["id"] for t in r.json()["items"]]

    # no view = all pending, due_date asc, nulls last
    assert ids() == [overdue["id"], today["id"], later["id"], nodate["id"]]
    assert ids("today") == [today["id"]]
    assert ids("overdue") == [overdue["id"]]
    assert ids("upcoming") == [later["id"], nodate["id"]]
    assert ids("done") == [done["id"]]
    assert client.get(f"{API}/tasks?view=week", headers=seller_a.headers).status_code == 422


def test_done_view_ordered_by_completed_at_desc(client: TestClient, seller_a: Seller) -> None:
    first = create_task(client, seller_a)
    second = create_task(client, seller_a)
    client.patch(f"{API}/tasks/{first['id']}/complete", headers=seller_a.headers)
    client.patch(f"{API}/tasks/{second['id']}/complete", headers=seller_a.headers)
    items = client.get(f"{API}/tasks?view=done", headers=seller_a.headers).json()["items"]
    assert [t["id"] for t in items] == [second["id"], first["id"]]


def test_list_filters_by_link_and_paginates(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a)
    lead = create_lead(client, seller_a)
    d = create_deal(client, seller_a, c["id"])
    tc = create_task(client, seller_a, contact_id=c["id"])
    tl = create_task(client, seller_a, lead_id=lead["id"])
    td = create_task(client, seller_a, deal_id=d["id"])
    for _ in range(3):
        create_task(client, seller_a)

    def ids(q: str) -> list[int]:
        return [
            t["id"]
            for t in client.get(f"{API}/tasks?{q}", headers=seller_a.headers).json()["items"]
        ]

    assert ids(f"contact_id={c['id']}") == [tc["id"]]
    assert ids(f"lead_id={lead['id']}") == [tl["id"]]
    assert ids(f"deal_id={d['id']}") == [td["id"]]
    page = client.get(f"{API}/tasks?page=2&page_size=4", headers=seller_a.headers).json()
    assert page["total"] == 6 and len(page["items"]) == 2


def test_update_task_and_relink(client: TestClient, db: Session, seller_a: Seller) -> None:
    c = create_contact(client, seller_a, name="C")
    lead = create_lead(client, seller_a, name="L")
    t = create_task(client, seller_a, contact_id=c["id"], due_date=YESTERDAY)
    resp = client.put(
        f"{API}/tasks/{t['id']}",
        json={
            "title": "New",
            "description": "d",
            "priority": "high",
            "lead_id": lead["id"],
            "due_date": YESTERDAY,
        },
        headers=seller_a.headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "New" and body["priority"] == "high"
    assert body["contact_id"] is None and body["lead_id"] == lead["id"]
    assert (body["linked_type"], body["linked_name"]) == ("lead", "L")


def test_changing_due_date_rearms_reminder(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    t = create_task(client, seller_a, due_date=YESTERDAY)
    row = db.get(Task, t["id"])
    assert row is not None
    row.reminder_sent = True
    db.commit()

    # same due date -> stays sent
    client.put(
        f"{API}/tasks/{t['id']}",
        json={"title": "same", "due_date": YESTERDAY},
        headers=seller_a.headers,
    )
    db.expire_all()
    assert db.get(Task, t["id"]).reminder_sent is True  # type: ignore[union-attr]

    client.put(
        f"{API}/tasks/{t['id']}",
        json={"title": "moved", "due_date": TOMORROW},
        headers=seller_a.headers,
    )
    db.expire_all()
    assert db.get(Task, t["id"]).reminder_sent is False  # type: ignore[union-attr]


def test_delete_task(client: TestClient, seller_a: Seller) -> None:
    t = create_task(client, seller_a)
    assert client.delete(f"{API}/tasks/{t['id']}", headers=seller_a.headers).status_code == 204
    assert client.get(f"{API}/tasks/{t['id']}", headers=seller_a.headers).status_code == 404


def test_deleting_linked_lead_or_deal_keeps_task(client: TestClient, seller_a: Seller) -> None:
    c = create_contact(client, seller_a)
    lead = create_lead(client, seller_a)
    d = create_deal(client, seller_a, c["id"])
    tl = create_task(client, seller_a, lead_id=lead["id"])
    td = create_task(client, seller_a, deal_id=d["id"])
    client.delete(f"{API}/leads/{lead['id']}", headers=seller_a.headers)
    client.delete(f"{API}/deals/{d['id']}", headers=seller_a.headers)
    got_l = client.get(f"{API}/tasks/{tl['id']}", headers=seller_a.headers).json()
    got_d = client.get(f"{API}/tasks/{td['id']}", headers=seller_a.headers).json()
    assert got_l["lead_id"] is None and got_l["linked_type"] is None
    assert got_d["deal_id"] is None and got_d["linked_type"] is None


# ---------------------------------------------------------------------------
# Cross-seller isolation
# ---------------------------------------------------------------------------


def test_cross_seller_task_access_is_404(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    t = create_task(client, seller_a, title="A's")
    url = f"{API}/tasks/{t['id']}"
    h = seller_b.headers
    assert client.get(url, headers=h).status_code == 404
    assert client.put(url, json={"title": "x"}, headers=h).status_code == 404
    assert client.patch(f"{url}/complete", headers=h).status_code == 404
    assert client.delete(url, headers=h).status_code == 404
    assert client.get(f"{API}/tasks", headers=h).json()["total"] == 0
    still = client.get(url, headers=seller_a.headers).json()
    assert still["status"] == "pending" and still["title"] == "A's"


@pytest.mark.parametrize("field", ["contact_id", "lead_id", "deal_id"])
def test_cannot_link_task_to_other_sellers_record(
    client: TestClient, seller_a: Seller, seller_b: Seller, field: str
) -> None:
    c = create_contact(client, seller_a)
    ids = {
        "contact_id": c["id"],
        "lead_id": create_lead(client, seller_a)["id"],
        "deal_id": create_deal(client, seller_a, c["id"])["id"],
    }
    resp = client.post(
        f"{API}/tasks", json={"title": "x", field: ids[field]}, headers=seller_b.headers
    )
    assert resp.status_code == 404
    mine = create_task(client, seller_b)
    upd = client.put(
        f"{API}/tasks/{mine['id']}",
        json={"title": "x", field: ids[field]},
        headers=seller_b.headers,
    )
    assert upd.status_code == 404


def test_link_filter_with_other_sellers_ids_returns_nothing(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    c = create_contact(client, seller_a)
    create_task(client, seller_a, contact_id=c["id"])
    resp = client.get(f"{API}/tasks?contact_id={c['id']}", headers=seller_b.headers).json()
    assert resp["items"] == [] and resp["total"] == 0
