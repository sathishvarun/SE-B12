"""The 1-hour reply promise: clock on bad reviews, reminder ladder, numbers on the dashboard and for the admin, maps."""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Notification, Organization, Outlet, Review, ReviewAnalysis
from app.services import maps, reply_promise


def _owner(client, name="Promise Mess"):
    email = f"prom-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Prom Owner", "organization_name": name, "email": email, "password": "Strong#Pass1",
              "accept_terms": True},
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def _admin(client) -> dict:
    tok = client.post("/api/v1/auth/login", json={
        "email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _outlet(db, org_id) -> Outlet:
    outlet = db.scalar(select(Outlet).where(Outlet.organization_id == org_id))
    if outlet is None:
        outlet = Outlet(organization_id=org_id, name="Main branch")
        db.add(outlet)
        db.commit()
    return outlet


def _review(db, org_id, rating, minutes_ago, *, replied_after=None, urgency="low", old=False) -> Review:
    outlet = _outlet(db, org_id)
    created = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    r = Review(
        organization_id=org_id, outlet_id=outlet.id, external_id=uuid.uuid4().hex, platform="zomato", rating=rating,
        review_date=date(2024, 1, 1) if old else created.date(), review_text="Biryani was cold and late.",
        analysis_status="analyzed", created_at=created,
    )
    if replied_after is not None:
        r.workflow_status = "replied"
        r.replied_at = created + timedelta(minutes=replied_after)
    db.add(r)
    db.flush()
    db.add(ReviewAnalysis(review_id=r.id, sentiment="negative", category="food_quality",
                          urgency=urgency, language="english", summary="Cold biryani",
                          suggested_reply="Sorry about the cold biryani.", status="analyzed"))
    db.commit()
    return r


def test_numbers_count_bad_reviews_answered_within_the_target(client):
    h, org_id = _owner(client)
    with SessionLocal() as db:
        _review(db, org_id, 2, 300, replied_after=20)  # within
        _review(db, org_id, 1, 300, replied_after=40)  # within
        _review(db, org_id, 3, 300, replied_after=90)  # late
        _review(db, org_id, 1, 120)  # still waiting, past the hour: missed + overdue
        _review(db, org_id, 2, 10)  # waiting, still inside the hour
        _review(db, org_id, 5, 300, urgency="high", replied_after=30)  # urgent 5★ counts too: within
        _review(db, org_id, 5, 300, replied_after=500)  # happy review: not on the clock
        _review(db, org_id, 1, 300, old=True)  # old review imported in bulk: history, no clock
    ov = client.get("/api/v1/dashboard/overview", headers=h).json()
    p = ov["promise"]
    assert p["target_minutes"] == 60 and p["reminders_on"] is True
    assert (p["within"], p["late"], p["missed"], p["bad"]) == (3, 1, 1, 5)
    assert p["pct_within"] == 60.0
    assert p["median_minutes"] == 35
    assert (p["waiting"], p["overdue"]) == (2, 1)

    page = client.get("/api/v1/reviews?view=clock", headers=h).json()
    assert page["counts"]["clock"] == 2 and len(page["items"]) == 2
    first = page["items"][0]
    assert first["rating"] == 1 and first["reply_due_at"]  # oldest (overdue) first
    happy = [i for i in client.get("/api/v1/reviews", headers=h).json()["items"] if i["rating"] == 5]
    assert any(i["reply_due_at"] for i in happy) and not all(i["reply_due_at"] for i in happy)


def test_reminders_climb_the_ladder_once_each(client):
    h, org_id = _owner(client, "Promise Ladder")
    with SessionLocal() as db:
        outlet = _outlet(db, org_id)
        outlet.manager_email = "branch-manager@example.com"
        outlet.name = "Ladder branch"
        db.commit()
        r = _review(db, org_id, 1, 35)
        rid = r.id
    sent: list[tuple[list[str], str]] = []

    def mail(to, subj, text):  # only this test's branch (other tests' reviews may be waiting too)
        if "Ladder branch" in subj:
            sent.append((to, subj))

    with patch("app.services.reply_promise.send_email", side_effect=mail):
        with SessionLocal() as db:
            reply_promise.run_reminders(db)  # 35 min: half-time, the branch manager
            reply_promise.run_reminders(db)  # nothing new
        assert len(sent) == 1 and sent[0][0] == ["branch-manager@example.com"] and "min left" in sent[0][1]
        with SessionLocal() as db:
            db.get(Review, rid).created_at = datetime.now(UTC) - timedelta(minutes=65)
            db.commit()
            reply_promise.run_reminders(db)  # past the hour: the owner hears
        assert len(sent) == 2 and "Past 1 hour" in sent[1][1] and any("prom-" in e for e in sent[1][0])
        with SessionLocal() as db:
            n = db.scalar(select(Notification).where(Notification.review_id == rid))
            assert n and n.read_at is None and "Past" in n.title
        # Replied: the clock stops, no more reminders
        client.patch(f"/api/v1/reviews/{rid}", json={"workflow_status": "replied"}, headers=h)
        with SessionLocal() as db:
            db.get(Review, rid).created_at = datetime.now(UTC) - timedelta(minutes=130)
            db.commit()
            reply_promise.run_reminders(db)
        assert len(sent) == 2


def test_owner_can_change_or_switch_off_the_target(client):
    h, org_id = _owner(client, "Promise Settings")
    assert client.get("/api/v1/settings", headers=h).json()["reply_target_minutes"] == 60
    assert client.patch("/api/v1/settings", json={"reply_target_minutes": 30}, headers=h).json()[
        "reply_target_minutes"] == 30
    assert client.patch("/api/v1/settings", json={"reply_target_minutes": 45}, headers=h).status_code == 422
    assert client.patch("/api/v1/settings", json={"reply_target_minutes": 0}, headers=h).json()[
        "reply_target_minutes"] is None
    with SessionLocal() as db:
        _review(db, org_id, 1, 200)
        sent = []
        with patch("app.services.reply_promise.send_email", side_effect=lambda *a, **k: sent.append(a)):
            reply_promise.run_reminders(db)
        assert sent == []  # reminders off
        assert db.get(Organization, org_id).reply_target_minutes is None


def test_admin_sees_every_restaurant_score_and_every_branch(client):
    h, org_id = _owner(client, "Promise League")
    with SessionLocal() as db:
        _review(db, org_id, 1, 300, replied_after=200)
        outlet = _outlet(db, org_id)
        outlet.city, outlet.area = "Coimbatore", "Gandhipuram"
        db.commit()
    a = _admin(client)
    league = client.get("/api/v1/admin/reply-promise", headers=a).json()
    mine = next(r for r in league if r["org_id"] == org_id)
    assert mine["bad"] == 1 and mine["pct_within"] == 0.0
    assert client.get("/api/v1/admin/reply-promise", headers=h).status_code == 403
    page = client.get("/api/v1/admin/branches?q=Promise League", headers=a).json()
    row = next(b for b in page["items"] if b["org_id"] == org_id)
    assert row["directions_url"].startswith("https://www.google.com/maps/")
    assert client.get("/api/v1/admin/branches", headers=h).status_code == 403


def test_maps_links_prefer_the_exact_listing():
    o = Outlet(name="Annapoorna", area="RS Puram", city="Coimbatore")
    assert "dir/?api=1&destination=Annapoorna" in maps.directions_url(o)
    o.google_place_id, o.google_place_name = "ChIJabc", "Annapoorna RS Puram"
    assert "query_place_id=ChIJabc" in maps.directions_url(o) and maps.on_google_maps(o)
    o.google_maps_url = "https://maps.app.goo.gl/xyz"
    assert maps.directions_url(o) == "https://maps.app.goo.gl/xyz"
    assert maps.directions_url(Outlet(name="X")) is None
