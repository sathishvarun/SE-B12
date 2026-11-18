"""Admin vs owner vs outlet staff, trial expiry, and the Google reviews sync (Google mocked)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.config import settings
from app.database import SessionLocal
from app.models import Organization, Review, SourceConnection
from app.services import google_reviews
from app.services.crypto import decrypt, encrypt


def _login(client, email, password):
    token = client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_is_not_inside_a_restaurant(client):
    h = _login(client, settings.SUPERADMIN_EMAIL, settings.SUPERADMIN_PASSWORD)
    assert client.get("/api/v1/dashboard/overview", headers=h).status_code == 403
    assert client.get("/api/v1/admin/events", headers=h).status_code == 200


def test_outlet_manager_sees_only_their_outlet(client):
    h = _login(client, "rspuram@virundhu.local", settings.DEMO_PASSWORD)
    me = client.get("/api/v1/auth/me", headers=h).json()
    assert me["role"] == "manager" and me["outlet_names"] == ["RS Puram"]
    page = client.get("/api/v1/reviews?view=all&page_size=100", headers=h).json()
    assert page["total"] > 0 and {r["outlet_name"] for r in page["items"]} == {"RS Puram"}
    assert all(r["is_sample"] for r in page["items"])
    ov = client.get("/api/v1/dashboard/overview", headers=h).json()
    assert [o["name"] for o in ov["outlets"]] == ["RS Puram"]
    assert [o["name"] for o in client.get("/api/v1/outlets", headers=h).json()] == ["RS Puram"]
    owner = _login(client, settings.DEMO_EMAIL, settings.DEMO_PASSWORD)
    other = next(
        r
        for r in client.get("/api/v1/reviews?page_size=100", headers=owner).json()["items"]
        if r["outlet_name"] != "RS Puram"
    )
    assert client.get(f"/api/v1/reviews/{other['id']}", headers=h).status_code == 404


def test_trial_end_makes_account_read_only(client):
    email = f"t-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Trial Ends",
            "organization_name": "Old Trial",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    with SessionLocal() as db:
        org = db.get(Organization, data["user"]["organization"]["id"])
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    h = {"Authorization": f"Bearer {data['access_token']}"}
    res = client.post("/api/v1/reviews", headers=h, json={"text": "ok", "rating": 4, "platform": "google"})
    assert res.status_code == 402 and "trial has ended" in res.json()["detail"]
    assert client.get("/api/v1/reviews", headers=h).status_code == 200  # can still look


class FakeResp:
    def __init__(self, code, data):
        self.status_code, self._d = code, data

    def json(self):
        return self._d


class FakeClient:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, params=None):
        if url.endswith("/accounts"):
            return FakeResp(200, {"accounts": [{"name": "accounts/1"}]})
        if url.endswith("/locations"):
            return FakeResp(200, {"locations": [{"name": "locations/22", "title": "Anna Nagar"}]})
        return FakeResp(
            200,
            {
                "reviews": [
                    {
                        "reviewId": "g-1",
                        "name": "accounts/1/locations/22/reviews/g-1",
                        "starRating": "ONE",
                        "comment": "Found hair in biryani",
                        "createTime": "2026-11-15T10:00:00Z",
                    },
                    {
                        "reviewId": "g-2",
                        "name": "accounts/1/locations/22/reviews/g-2",
                        "starRating": "FIVE",
                        "comment": "Lovely",
                        "createTime": "2026-11-15T11:00:00Z",
                        "reviewReply": {"comment": "Thanks!"},
                    },
                ]
            },
        )


def test_google_sync_imports_live_reviews(client):
    email = f"g-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Google Owner",
            "organization_name": "G Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    org_id = data["user"]["organization"]["id"]
    assert decrypt(encrypt("secret-token")) == "secret-token"
    with SessionLocal() as db:
        db.add(
            SourceConnection(
                organization_id=org_id,
                provider="google",
                status="connected",
                details={"refresh_token": encrypt("r"), "email": "owner@gmail.com"},
            )
        )
        db.commit()
        with (
            patch.object(google_reviews, "_access_token", return_value="tok"),
            patch.object(google_reviews.httpx, "Client", FakeClient),
        ):
            ids = google_reviews.sync(db, org_id, "trial")
            again = google_reviews.sync(db, org_id, "trial")
        assert len(ids) == 2 and again == []
        rows = {r.external_id: r for r in db.query(Review).filter(Review.organization_id == org_id)}
        assert rows["g-2"].workflow_status == "replied" and rows["g-1"].rating == 1 and not rows["g-1"].is_sample
        assert rows["g-1"].source_ref == "accounts/1/locations/22/reviews/g-1"
    conns = {
        c["provider"]: c
        for c in client.get("/api/v1/connections", headers={"Authorization": f"Bearer {data['access_token']}"}).json()
    }
    assert conns["google"]["status"] == "connected" and conns["google"]["locations"] == ["Anna Nagar"]


def test_google_access_not_approved_is_explained(client):
    with SessionLocal() as db:
        conn = (
            db.query(SourceConnection)
            .filter(SourceConnection.provider == "google", SourceConnection.status == "connected")
            .first()
        )

        class Denied(FakeClient):
            def get(self, url, params=None):
                return FakeResp(403, {})

        with (
            patch.object(google_reviews, "_access_token", return_value="tok"),
            patch.object(google_reviews.httpx, "Client", Denied),
        ):
            google_reviews.sync(db, conn.organization_id, "trial")
        db.refresh(conn)
        assert "API access" in conn.details["last_error"]
