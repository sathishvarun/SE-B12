"""Sign-in, dashboard and inbox against the seeded demo restaurant (run `python -m app.seed` first)."""

import uuid
from unittest.mock import patch

from app.config import settings


def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_login_and_profile(client):
    data = _login(client, settings.SUPERADMIN_EMAIL, settings.SUPERADMIN_PASSWORD)
    assert data["user"]["is_superadmin"] is True
    me = client.get("/api/v1/auth/me", headers=_auth(data["access_token"])).json()
    # The platform admin is not inside any restaurant; they use the Admin console.
    assert me["organization"] is None


def test_wrong_password_gives_clear_message(client):
    res = client.post("/api/v1/auth/login", json={"email": settings.DEMO_EMAIL, "password": "nope"})
    assert res.status_code == 401
    assert "don't match" in res.json()["detail"]


def test_protected_routes_need_sign_in(client):
    assert client.get("/api/v1/dashboard/overview").status_code == 401
    assert client.get("/api/v1/reviews").status_code == 401


def test_dashboard_numbers_match_database(client):
    token = _login(client, settings.DEMO_EMAIL, settings.DEMO_PASSWORD)["access_token"]
    ov = client.get("/api/v1/dashboard/overview", headers=_auth(token)).json()
    reviews = client.get("/api/v1/reviews?view=today&page_size=100", headers=_auth(token)).json()
    assert ov["kpis"]["urgent_pending"] == reviews["counts"]["today"] == reviews["total"]
    assert len(ov["outlets"]) == 3
    assert all(r["analysis"]["urgency"] == "high" for r in reviews["items"])


def test_demo_is_read_only(client):
    token = _login(client, settings.DEMO_EMAIL, settings.DEMO_PASSWORD)["access_token"]
    rid = client.get("/api/v1/reviews", headers=_auth(token)).json()["items"][0]["id"]
    res = client.patch(f"/api/v1/reviews/{rid}", json={"workflow_status": "replied"}, headers=_auth(token))
    assert res.status_code == 403


def test_register_refresh_and_isolation(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Owner",
            "organization_name": "Test Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["role"] == "owner" and data["user"]["organization"]["plan"] == "trial"
    # a new restaurant sees none of the demo reviews
    page = client.get("/api/v1/reviews", headers=_auth(data["access_token"])).json()
    assert page["total"] == 0
    # the refresh token never reaches the page: only an HttpOnly, SameSite=Strict cookie carries it
    assert "refresh_token" not in data
    set_cookie = res.headers["set-cookie"]
    assert "vr_session=" in set_cookie and "HttpOnly" in set_cookie and "SameSite=strict" in set_cookie
    old = client.cookies.get("vr_session")
    # refresh rotates the token; the old one stops working
    new = client.post("/api/v1/auth/refresh")
    assert new.status_code == 200 and "refresh_token" not in new.json()
    client.cookies.clear()
    # reused within 30 seconds (two tabs refreshing at once) is allowed; reused later is refused
    from datetime import UTC, datetime, timedelta

    from app.auth.security import hash_token
    from app.database import SessionLocal
    from app.models import RefreshToken

    assert client.post("/api/v1/auth/refresh", json={"refresh_token": old}).status_code == 200
    with SessionLocal() as db:
        row = db.query(RefreshToken).filter_by(token_hash=hash_token(old)).one()
        row.updated_at = datetime.now(UTC) - timedelta(minutes=2)
        db.commit()
    client.cookies.clear()
    again = client.post("/api/v1/auth/refresh", json={"refresh_token": old})
    assert again.status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401  # no cookie, no session
    # same email twice is refused
    dup = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "X Y",
            "organization_name": "Other",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    )
    assert dup.status_code == 409


def test_live_try_uses_safety_net(client):
    fake = {
        "sentiment": "negative",
        "category": "food_quality",
        "urgency": "medium",
        "language": "tanglish",
        "summary": "Found a hair in the rice.",
        "suggested_reply": "Sorry!",
        "safety_override": False,
        "model_used": "x",
        "input_tokens": 1,
        "output_tokens": 1,
    }
    with (
        patch.object(settings, "ANTHROPIC_API_KEY", "test-key"),
        patch("app.routers.public.tag_review", return_value=fake),
    ):
        res = client.post("/api/v1/public/try", json={"text": "Rice la mudi irundhuchu"})
    assert res.status_code == 200
    assert res.json()["food_safety"] is True
