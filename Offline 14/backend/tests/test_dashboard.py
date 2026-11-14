"""Dashboard: summary counters and analytics (SQLite month-grouping branch), scoped per seller."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Deal
from app.services import dashboard_service
from tests.conftest import (
    API,
    Seller,
    app_today,
    create_contact,
    create_deal,
    create_lead,
    create_task,
)

STAGES = ["prospect", "proposal", "negotiation", "won", "lost"]
SOURCES = ["website", "referral", "social", "other"]


def test_empty_dashboard(client: TestClient, seller_a: Seller) -> None:
    summary = client.get(f"{API}/dashboard/summary", headers=seller_a.headers).json()
    assert summary == {
        "contacts": 0,
        "open_leads": 0,
        "open_deals": 0,
        "open_pipeline_value": "0.00",
        "tasks_due_today": 0,
        "tasks_overdue": 0,
    }
    analytics = client.get(f"{API}/dashboard/analytics", headers=seller_a.headers).json()
    assert [b["stage"] for b in analytics["pipeline_by_stage"]] == STAGES
    assert all(b["count"] == 0 and b["value"] == "0.00" for b in analytics["pipeline_by_stage"])
    assert len(analytics["deals_won_by_month"]) == 6
    assert all(b["count"] == 0 for b in analytics["deals_won_by_month"])
    assert analytics["lead_conversion_rate"] == 0
    assert analytics["leads_by_source"] == [{"source": s, "count": 0} for s in SOURCES]


def test_summary_counts(client: TestClient, seller_a: Seller, seller_b: Seller) -> None:
    today = app_today()
    c = create_contact(client, seller_a)
    create_contact(client, seller_a, name="Two")
    create_deal(client, seller_a, c["id"], value="100.50")
    create_deal(client, seller_a, c["id"], value="200", stage="negotiation")
    create_deal(client, seller_a, c["id"], value="999", stage="won")
    create_lead(client, seller_a)
    lost = create_lead(client, seller_a)
    client.patch(
        f"{API}/leads/{lost['id']}/status", json={"status": "lost"}, headers=seller_a.headers
    )
    create_task(client, seller_a, due_date=today.isoformat())
    create_task(client, seller_a, due_date=(today - timedelta(days=2)).isoformat())
    done = create_task(client, seller_a, due_date=(today - timedelta(days=2)).isoformat())
    client.patch(f"{API}/tasks/{done['id']}/complete", headers=seller_a.headers)
    create_task(client, seller_a, due_date=(today + timedelta(days=2)).isoformat())

    # noise from another seller must not leak in
    bc = create_contact(client, seller_b)
    create_deal(client, seller_b, bc["id"], value="5000")
    create_task(client, seller_b, due_date=today.isoformat())

    summary = client.get(f"{API}/dashboard/summary", headers=seller_a.headers).json()
    assert summary == {
        "contacts": 2,
        "open_leads": 1,
        "open_deals": 2,
        "open_pipeline_value": "300.50",
        "tasks_due_today": 1,
        "tasks_overdue": 1,
    }


def test_analytics(client: TestClient, db: Session, seller_a: Seller, seller_b: Seller) -> None:
    c = create_contact(client, seller_a)
    create_deal(client, seller_a, c["id"], value="10")
    create_deal(client, seller_a, c["id"], value="20", stage="proposal")
    won_now = create_deal(client, seller_a, c["id"], value="300", stage="won")
    create_deal(client, seller_a, c["id"], value="5", stage="lost")
    old_won = create_deal(client, seller_a, c["id"], value="70", stage="won")
    ancient_won = create_deal(client, seller_a, c["id"], value="1", stage="won")

    today = app_today()
    first_of_month = today.replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    row = db.get(Deal, old_won["id"])
    assert row is not None
    row.closed_at = datetime(last_month.year, last_month.month, 15, 12, tzinfo=UTC)
    ancient = db.get(Deal, ancient_won["id"])
    assert ancient is not None
    ancient.closed_at = datetime(today.year - 2, 1, 1, tzinfo=UTC)
    db.commit()

    for source in ["website", "website", "referral"]:
        create_lead(client, seller_a, source=source)
    lead = create_lead(client, seller_a, source="social")
    client.post(
        f"{API}/leads/{lead['id']}/convert",
        json={"deal_title": "x", "deal_value": "0"},
        headers=seller_a.headers,
    )
    create_lead(client, seller_b, source="other")

    body = client.get(f"{API}/dashboard/analytics", headers=seller_a.headers).json()
    pipeline = {b["stage"]: (b["count"], b["value"]) for b in body["pipeline_by_stage"]}
    assert pipeline == {
        "prospect": (2, "10.00"),  # incl. the converted lead's 0-value deal
        "proposal": (1, "20.00"),
        "negotiation": (0, "0.00"),
        "won": (3, "371.00"),
        "lost": (1, "5.00"),
    }

    months = body["deals_won_by_month"]
    assert len(months) == 6
    assert months[-1]["month"] == today.strftime("%Y-%m")
    assert months[-2]["month"] == last_month.strftime("%Y-%m")
    assert [m["month"] for m in months] == sorted(m["month"] for m in months)
    assert (months[-1]["count"], months[-1]["value"]) == (1, "300.00")
    assert (months[-2]["count"], months[-2]["value"]) == (1, "70.00")
    assert sum(m["count"] for m in months) == 2  # ancient deal outside window
    assert won_now["closed_at"] is not None

    assert body["lead_conversion_rate"] == 0.25
    assert {b["source"]: b["count"] for b in body["leads_by_source"]} == {
        "website": 2,
        "referral": 1,
        "social": 1,
        "other": 0,
    }


def test_last_months_wraps_year() -> None:
    assert dashboard_service._last_months(date(2026, 2, 10), 6) == [
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
    ]


def test_money_formatting() -> None:
    assert dashboard_service.money(None) == "0.00"
    assert dashboard_service.money(Decimal("12.5")) == "12.50"
    assert dashboard_service.money(3) == "3.00"


def test_dashboard_requires_auth(client: TestClient) -> None:
    assert client.get(f"{API}/dashboard/summary").status_code == 401
    assert client.get(f"{API}/dashboard/analytics").status_code == 401
