"""Demo prep: replies to the prospect's own latest Google reviews before the call. Google and the AI are mocked."""

import time
from unittest.mock import patch

import pytest

from app.config import settings
from app.services import demo_prep
from tests.test_intake_alerts_admin import fake_tag

PLACE = {
    "id": "ChIJtestplace123",
    "displayName": {"text": "Iso Annapoorna RS Puram"},
    "rating": 4.2,
    "userRatingCount": 3100,
    "reviews": [
        {
            "rating": 5,
            "publishTime": "2026-11-20T10:00:00Z",
            "originalText": {"text": "Ghee roast super!"},
            "authorAttribution": {"displayName": "Priya"},
        },
        {
            "rating": 2,
            "publishTime": "2026-11-25T10:00:00Z",
            "originalText": {"text": "Sambar was cold today"},
            "authorAttribution": {"displayName": "Karthik"},
        },
        {"rating": 4, "publishTime": "2026-11-24T10:00:00Z", "text": {"text": "Good filter coffee"}},
        {"rating": 3, "publishTime": "2026-11-01T10:00:00Z", "originalText": {"text": "Old review, should be skipped"}},
    ],
}


def _admin(client) -> dict:
    tok = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _wait(client, h, pid):
    for _ in range(50):
        p = client.get(f"/api/v1/admin/demo-preps/{pid}", headers=h).json()
        if p["status"] != "queued":
            return p
        time.sleep(0.1)
    raise AssertionError("demo prep never finished")


@pytest.fixture(autouse=True)
def _clean():
    yield
    from sqlalchemy import delete

    from app.database import SessionLocal
    from app.models import DemoPrep, Lead

    with SessionLocal() as db:  # tests clean up after themselves
        db.execute(
            delete(DemoPrep).where(DemoPrep.restaurant.like("Iso%") | DemoPrep.restaurant.in_(["Annapoorna", "X"]))
        )
        db.execute(delete(Lead).where(Lead.restaurant.like("Iso%")))
        db.commit()


@pytest.fixture
def mocked():
    with (
        patch("app.services.demo_prep.tag_review", fake_tag),
        patch("app.services.demo_prep.google_places.enabled", return_value=True),
        patch("app.services.demo_prep.google_places.search", return_value=[{"place_id": PLACE["id"]}]),
        patch("app.services.demo_prep.google_places._details", return_value=PLACE) as details,
        patch("app.services.demo_prep.settings.LLM_PROVIDER", settings.LLM_PROVIDER),
        patch.object(type(settings), "llm_configured", property(lambda s: True)),
        patch("app.services.demo_prep.enqueue", new=_sync),
    ):
        yield details


async def _sync(pid):
    demo_prep._run_locally(pid)


def test_maps_link_gives_three_latest_reviews_with_replies(client, mocked):
    h = _admin(client)
    link = "https://www.google.com/maps/place/Iso+Annapoorna+RS+Puram/@11.0,76.9,17z"
    r = client.post("/api/v1/admin/demo-preps", json={"restaurant": "Annapoorna", "maps_link": link}, headers=h)
    assert r.status_code == 202, r.text
    p = _wait(client, h, r.json()["id"])
    assert p["status"] == "ready", p
    assert p["place_name"] == "Iso Annapoorna RS Puram" and p["rating"] == 4.2
    assert [x["text"] for x in p["reviews"]] == ["Sambar was cold today", "Good filter coffee", "Ghee roast super!"]
    assert all(x["reply"] for x in p["reviews"])


def test_pasted_reviews_work_without_google(client, mocked):
    h = _admin(client)
    body = {"restaurant": "Iso Kovai Mess", "reviews": [{"text": "Parotta was hard", "rating": 2}]}
    p = _wait(client, h, client.post("/api/v1/admin/demo-preps", json=body, headers=h).json()["id"])
    assert p["status"] == "ready" and p["reviews"][0]["reply"]
    mocked.assert_not_called()


def test_only_google_maps_links_are_ever_fetched(client):
    h = _admin(client)
    for bad in [
        "http://www.google.com/maps/place/x",
        "https://google.evil.com/maps",
        "https://127.0.0.1/x",
        "https://user@goo.gl/x",
        "https://goo.gl:8443/x",
        "file:///etc/passwd",
    ]:
        r = client.post("/api/v1/admin/demo-preps", json={"restaurant": "X", "maps_link": bad}, headers=h)
        assert r.status_code == 422, bad
    assert demo_prep.is_maps_link("https://maps.app.goo.gl/AbC123")
    assert demo_prep.place_hint("https://www.google.com/maps/search/?api=1&query=x&query_place_id=ChIJabcdefghij") == (
        "ChIJabcdefghij",
        None,
    )

    # a redirect that leaves Google is refused
    class R:
        is_redirect = True
        headers = {"location": "http://169.254.169.254/latest/meta-data"}

    with patch("app.services.demo_prep.httpx.get", return_value=R()):
        with pytest.raises(demo_prep.PrepError):
            demo_prep._expand("https://maps.app.goo.gl/AbC123")


def test_contact_form_link_prepares_the_demo(client, mocked):
    r = client.post(
        "/api/v1/public/contact",
        json={
            "name": "Ravi",
            "restaurant": "Iso Ravi Mess",
            "email": "ravi-iso@example.com",
            "phone": "9876543210",
            "maps_link": "https://www.google.com/maps/place/Iso+Ravi+Mess",
            "website": "",
        },
    )
    assert r.status_code == 201, r.text
    h = _admin(client)
    preps = client.get("/api/v1/admin/demo-preps", headers=h).json()
    mine = next(p for p in preps if p["restaurant"] == "Iso Ravi Mess")
    assert mine["lead_id"] and _wait(client, h, mine["id"])["status"] == "ready"
    bad = client.post(
        "/api/v1/public/contact",
        json={
            "name": "Ravi",
            "restaurant": "Iso Ravi Mess",
            "email": "ravi-iso@example.com",
            "maps_link": "https://evil.example.com/maps",
            "website": "",
        },
    )
    assert bad.status_code == 422
