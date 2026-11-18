"""Outlets from a file, WhatsApp review requests, the weekly summary, screenshots and the launch checklist."""

from datetime import UTC, datetime
from unittest.mock import patch

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, Review
from app.services import review_requests, weekly_summary
from tests.test_automation import _owner


def test_outlets_from_a_file(client):
    h, _ = _owner(client)
    csv = (
        "Outlet Name,district,manager,manager phone,pincode\n"
        "RS Puram,Coimbatore,Ravi,9876500001,641002\n"
        "Gandhipuram,Coimbatore,Kala,9876500002,641012\n"
        "Bad Pin,Coimbatore,,,12\n"
    )
    res = client.post("/api/v1/outlets/import", files={"file": ("o.csv", csv.encode(), "text/csv")}, headers=h).json()
    assert set(res["added"]) == {"RS Puram", "Gandhipuram"} and len(res["skipped"]) == 1
    again = client.post(
        "/api/v1/outlets/import",
        files={"file": ("o.csv", b"name,manager\nRS Puram,Ravi Kumar\n", "text/csv")},
        headers=h,
    ).json()
    assert again["updated"] == ["RS Puram"] and not again["added"]
    rs = next(o for o in client.get("/api/v1/outlets", headers=h).json() if o["name"] == "RS Puram")
    assert rs["manager_name"] == "Ravi Kumar" and rs["pincode"] == "641002"  # only given columns change


def test_phone_numbers_are_cleaned():
    assert review_requests.normalise_phone("098765 43210") == "+919876543210"
    assert review_requests.normalise_phone("+91-98765-43210") == "+919876543210"
    assert review_requests.normalise_phone("12345") is None
    assert review_requests.normalise_phone("0422 2541234") is None  # landline, not WhatsApp


def test_review_requests_give_links_and_never_ask_twice(client):
    h, _ = _owner(client)
    body = {"numbers": ["9876543210", "98765 43210", "abc"], "consent": True}
    assert client.post("/api/v1/review-requests", json={**body, "consent": False}, headers=h).status_code == 400
    res = client.post("/api/v1/review-requests", json=body, headers=h).json()
    statuses = [r["status"] for r in res["results"]]
    assert statuses == ["link", "skipped_recent", "invalid"] and not res["sending_automatically"]
    link = res["results"][0]["link"]
    assert link.startswith("https://wa.me/919876543210?text=") and "%2Ff%2F" in link
    assert "43210" not in res["results"][0]["phone"][:-5]  # number is masked
    again = client.post("/api/v1/review-requests", json=body, headers=h).json()
    assert again["results"][0]["status"] == "skipped_recent"
    assert client.get("/api/v1/review-requests/stats", headers=h).json()["asked_30d"] == 1


def test_weekly_summary_names_the_outlet_to_fix_first(client):
    h, org_id = _owner(client)
    client.post("/api/v1/outlets", json={"name": "Peelamedu", "district": "Coimbatore"}, headers=h)
    oid = next(o["id"] for o in client.get("/api/v1/outlets", headers=h).json() if o["name"] == "Peelamedu")
    today = datetime.now(UTC).date()
    with SessionLocal() as db:
        for i, r in enumerate((1, 2, 5)):
            db.add(
                Review(
                    organization_id=org_id,
                    outlet_id=oid,
                    external_id=f"w{i}-{org_id}",
                    platform="zomato",
                    rating=r,
                    review_date=today,
                    review_text="Cold food" if r < 3 else "Super",
                    analysis_status="pending",
                    workflow_status="new",
                )
            )
        db.commit()
        org = db.get(Organization, org_id)
        weeks = weekly_summary.build(db, org)
        text = weekly_summary.render(org, list(weeks.values()))
    assert "Coimbatore:" in text and "Peelamedu: 3 reviews" in text and "2 unhappy" in text
    assert "Start with Peelamedu" in text


def test_reviews_from_a_screenshot(client, monkeypatch):
    from app.ai.screenshot import ShotReview

    h, _ = _owner(client)
    monkeypatch.setattr(type(settings), "llm_configured", property(lambda _: True))
    found = [ShotReview(rating=1, review_text="Biryani la mudi irundhuchu"), ShotReview(rating=5, review_text="Semma")]
    with patch("app.ai.screenshot.read_screenshot", return_value=found), patch("app.routers.intake.enqueue_analysis"):
        files = {"file": ("s.png", b"\x89PNG fake", "image/png")}
        res = client.post("/api/v1/imports/screenshot", files=files, data={"platform": "zomato"}, headers=h).json()
        assert res["added"] == 2
        again = client.post("/api/v1/imports/screenshot", files=files, data={"platform": "zomato"}, headers=h).json()
        assert again["added"] == 0 and again["duplicates"] == 2
    bad = client.post("/api/v1/imports/screenshot", files={"file": ("a.pdf", b"%PDF", "application/pdf")}, headers=h)
    assert bad.status_code == 400


def test_launch_checklist_for_admin_only(client):
    admin = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    items = {
        i["key"]: i
        for i in client.get("/api/v1/admin/launch-check", headers={"Authorization": f"Bearer {admin}"}).json()
    }
    assert items["app_url"]["ok"] is False and items["app_url"]["required"]
    h, _ = _owner(client)
    assert client.get("/api/v1/admin/launch-check", headers=h).status_code == 403
