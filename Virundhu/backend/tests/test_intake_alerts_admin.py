"""Upload, AI reading (mocked), instant alerts, team invites and the super admin panel."""

import uuid
from unittest.mock import patch

from app.config import settings
from app.database import SessionLocal
from app.services.analysis import analyze_reviews


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _new_owner(client):
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Kumar Owner",
            "organization_name": "Kumar Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    )
    return res.json()


def fake_tag(text, rating=None, platform="google", tone="warm", signature="", attempts=2):
    urgent = "late" in text.lower() or "mudi" in text.lower()
    return {
        "sentiment": "negative" if urgent else "positive",
        "category": "delivery" if urgent else "food_quality",
        "urgency": "high" if urgent else "low",
        "language": "tanglish",
        "summary": "Test summary.",
        "suggested_reply": "Thank you!",
        "safety_override": False,
        "model_used": "fake",
        "input_tokens": 100,
        "output_tokens": 50,
    }


async def run_now(org_id, review_ids, batch_id=None):
    with SessionLocal() as db:
        analyze_reviews(db, org_id, review_ids, batch_id)


CSV = (
    "review_id,date,platform,rating,review_text\n"
    "A1,2026-11-15,Zomato,1,Delivery romba late food cold\n"
    "A2,2026-11-15,Swiggy,5,Biryani semma\n"
    "A2,2026-11-15,Swiggy,5,Biryani semma\n"
    "A3,2026-11-15,Google,9,Bad rating value\n"
)


def test_upload_reads_reviews_and_fires_instant_alert(client):
    data = _new_owner(client)
    h = _auth(data["access_token"])
    with (
        patch.object(settings, "ANTHROPIC_API_KEY", "test"),
        patch("app.services.analysis.tag_review", fake_tag),
        patch("app.routers.intake.enqueue_analysis", run_now),
    ):
        res = client.post("/api/v1/imports", headers=h, files={"file": ("week.csv", CSV.encode(), "text/csv")})
    assert res.status_code == 202, res.text
    batch = res.json()
    assert batch["valid_rows"] == 2 and batch["duplicate_rows"] == 1 and batch["invalid_rows"] == 1
    done = client.get(f"/api/v1/imports/{batch['id']}", headers=h).json()
    assert done["status"] == "completed" and done["analyzed_rows"] == 2
    notes = client.get("/api/v1/notifications", headers=h).json()
    assert notes["unread"] == 1 and "Delivery complaint" in notes["items"][0]["title"]
    page = client.get("/api/v1/reviews?view=today", headers=h).json()
    assert page["total"] == 1
    client.post("/api/v1/notifications/read-all", headers=h)
    assert client.get("/api/v1/notifications", headers=h).json()["unread"] == 0


def test_bad_file_gives_clear_message(client):
    h = _auth(_new_owner(client)["access_token"])
    res = client.post("/api/v1/imports", headers=h, files={"file": ("x.csv", b"name,stars\nA,5\n", "text/csv")})
    assert res.status_code == 400 and "review_text" in res.json()["detail"]


def test_single_review_and_connections(client):
    h = _auth(_new_owner(client)["access_token"])
    with patch("app.routers.intake.enqueue_analysis", run_now):
        res = client.post(
            "/api/v1/reviews", headers=h, json={"text": "Chicken la mudi", "rating": 1, "platform": "swiggy"}
        )
    assert res.status_code == 202
    assert (
        client.post(
            "/api/v1/connections/test-feed", headers=h, json={"provider": "zomato", "enabled": True}
        ).status_code
        == 404
    )
    conns = {c["provider"]: c for c in client.get("/api/v1/connections", headers=h).json()}
    assert conns["google"]["official_api"] is True and conns["zomato"]["official_api"] is False


def test_team_invite_and_accept(client):
    owner = _new_owner(client)
    h = _auth(owner["access_token"])
    email = f"staff-{uuid.uuid4().hex[:6]}@example.com"
    inv = client.post("/api/v1/team/invitations", headers=h, json={"email": email, "role": "agent"}).json()
    token = inv["invite_url"].rsplit("/", 1)[1]
    assert client.get(f"/api/v1/invitations/{token}").json()["organization_name"] == "Kumar Mess"
    joined = client.post(
        f"/api/v1/invitations/{token}/accept", json={"full_name": "Staff One", "password": "Ladle#Spoon77"}
    )
    assert joined.status_code == 200 and joined.json()["user"]["role"] == "agent"
    team = client.get("/api/v1/team", headers=h).json()
    assert len(team["members"]) == 2
    # staff cannot invite
    sh = _auth(joined.json()["access_token"])
    assert (
        client.post(
            "/api/v1/team/invitations", headers=sh, json={"email": "x@example.com", "role": "agent"}
        ).status_code
        == 403
    )
    # invitation works only once
    assert (
        client.post(
            f"/api/v1/invitations/{token}/accept", json={"full_name": "X Y", "password": "Ladle#Spoon77"}
        ).status_code
        == 404
    )


def test_admin_panel_is_admin_only_and_can_open_any_restaurant(client):
    owner = _new_owner(client)
    assert client.get("/api/v1/admin/stats", headers=_auth(owner["access_token"])).status_code == 403
    admin = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()
    ah = _auth(admin["access_token"])
    stats = client.get("/api/v1/admin/stats", headers=ah).json()
    assert stats["restaurants"] >= 1 and len(stats["daily"]) == 14
    orgs = client.get("/api/v1/admin/organizations", headers=ah).json()
    target = next(o for o in orgs if o["name"] == "Kumar Mess")
    me = client.get("/api/v1/settings", headers={**ah, "X-Org-Id": str(target["id"])}).json()
    assert me["name"] == "Kumar Mess"
    before = target["trial_ends_at"]
    upd = client.patch(f"/api/v1/admin/organizations/{target['id']}", headers=ah, json={"extend_trial_days": 7})
    assert (
        upd.status_code == 200 and upd.json()["trial_ends_at"] == before
    )  # trials can't be lengthened: always 14 days
    assert client.get("/api/v1/admin/users", headers=ah).status_code == 200
