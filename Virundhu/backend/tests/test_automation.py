"""Google auto-pilot, the QR feedback link and WhatsApp alerts (Google and Meta mocked)."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config import settings
from app.database import SessionLocal
from app.models import AlertLog, Organization, Review, ReviewAnalysis, SourceConnection
from app.services import alerts, autopilot


def _owner(client):
    email = f"auto-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Auto Owner",
            "organization_name": "Auto Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def _google_review(db, org_id, rating, sentiment="positive", urgency="low", category="food_quality"):
    r = Review(
        organization_id=org_id,
        external_id=f"g-{uuid.uuid4().hex[:8]}",
        platform="google",
        rating=rating,
        review_date=__import__("datetime").date.today(),
        review_text="Lovely biryani",
        analysis_status="analyzed",
        workflow_status="new",
        source_ref="accounts/1/locations/2/reviews/3",
    )
    db.add(r)
    db.flush()
    a = ReviewAnalysis(
        review_id=r.id,
        status="analyzed",
        sentiment=sentiment,
        urgency=urgency,
        category=category,
        suggested_reply="Thank you so much! - Team Auto",
        summary="Happy guest",
    )
    db.add(a)
    db.commit()
    return r, a


def test_settings_turn_on_autopilot_and_give_feedback_link(client):
    h, _ = _owner(client)
    s = client.get("/api/v1/settings", headers=h).json()
    assert s["autopilot_enabled"] is False and "/f/" in s["feedback_url"]
    bad = client.patch("/api/v1/settings", json={"whatsapp_numbers": ["98765"]}, headers=h)
    assert bad.status_code == 422
    s = client.patch(
        "/api/v1/settings",
        json={
            "autopilot_enabled": True,
            "autopilot_min_rating": 5,
            "whatsapp_numbers": ["+91 98765 43210"],
            "google_review_url": "https://g.page/r/abc/review",
        },
        headers=h,
    ).json()
    assert s["autopilot_enabled"] and s["autopilot_min_rating"] == 5 and s["whatsapp_numbers"] == ["+919876543210"]


def test_autopilot_replies_only_to_happy_google_reviews(client):
    _, org_id = _owner(client)
    with SessionLocal() as db:
        org = db.get(Organization, org_id)
        org.autopilot_enabled, org.autopilot_min_rating = True, 4
        db.add(SourceConnection(organization_id=org_id, provider="google", status="connected"))
        db.commit()
        happy, ha = _google_review(db, org_id, 5)
        angry, aa = _google_review(db, org_id, 2, sentiment="negative", urgency="high")
        four_hygiene, fa = _google_review(db, org_id, 4, category="hygiene")
        with patch.object(autopilot.google_reviews, "post_reply") as post:
            assert autopilot.maybe_auto_reply(db, happy, ha) is True
            assert autopilot.maybe_auto_reply(db, angry, aa) is False
            assert autopilot.maybe_auto_reply(db, four_hygiene, fa) is False
        assert post.call_count == 1 and post.call_args.args[3] == "Thank you so much! - Team Auto"
        db.refresh(happy)
        assert happy.auto_replied is True

        org.autopilot_enabled = False
        db.commit()
        other, oa = _google_review(db, org_id, 5)
        with patch.object(autopilot.google_reviews, "post_reply") as post:
            assert autopilot.maybe_auto_reply(db, other, oa) is False
            assert post.call_count == 0


def test_autopilot_failure_leaves_review_for_owner(client):
    _, org_id = _owner(client)
    with SessionLocal() as db:
        db.get(Organization, org_id).autopilot_enabled = True
        db.commit()
        r, a = _google_review(db, org_id, 5)
        with patch.object(autopilot.google_reviews, "post_reply", side_effect=RuntimeError("Google down")):
            assert autopilot.maybe_auto_reply(db, r, a) is False
        db.refresh(r)
        assert r.workflow_status == "new" and r.auto_replied is False


def test_qr_feedback_link_creates_a_direct_review(client):
    h, org_id = _owner(client)
    client.patch("/api/v1/settings", json={"google_review_url": "https://g.page/r/abc/review"}, headers=h)
    token = client.get("/api/v1/settings", headers=h).json()["feedback_url"].rsplit("/", 1)[1]
    form = client.get(f"/api/v1/public/feedback/{token}").json()
    assert form["restaurant"] == "Auto Mess"
    assert client.get("/api/v1/public/feedback/not-a-real-link").status_code == 404

    too_short = client.post(f"/api/v1/public/feedback/{token}", json={"rating": 2, "text": ""})
    assert too_short.status_code == 422
    res = client.post(
        f"/api/v1/public/feedback/{token}",
        json={"rating": 2, "text": "Biryani was cold", "name": "Ravi", "contact": "+919800000000"},
    )
    assert res.status_code == 201 and res.json()["google_review_url"] == "https://g.page/r/abc/review"
    happy = client.post(f"/api/v1/public/feedback/{token}", json={"rating": 5})
    assert happy.json()["google_review_url"]  # every guest is invited to Google, not only happy ones

    bot = client.post(f"/api/v1/public/feedback/{token}", json={"rating": 5, "website": "spam.example"})
    assert bot.status_code == 201
    with SessionLocal() as db:
        rows = db.query(Review).filter_by(organization_id=org_id, platform="direct").all()
        assert len(rows) == 2 and {r.guest_name for r in rows} == {"Ravi", None}


def test_whatsapp_alert_sent_once_per_number(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "t")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123")
    _, org_id = _owner(client)
    with SessionLocal() as db:
        org = db.get(Organization, org_id)
        org.whatsapp_numbers = ["+919876543210"]
        db.commit()
        r, a = _google_review(db, org_id, 1, sentiment="negative", urgency="high", category="hygiene")
        ok = MagicMock(return_value=SimpleNamespace(status_code=200, text="{}"))
        with patch("app.services.whatsapp.httpx.post", ok):
            alerts.alert_for_review(db, r, a)
            alerts.alert_for_review(db, r, a)  # second time: already sent, skipped
        assert ok.call_count == 1
        body = ok.call_args.kwargs["json"]
        assert body["to"] == "919876543210" and body["template"]["name"] == settings.WHATSAPP_TEMPLATE
        log = db.query(AlertLog).filter_by(review_id=r.id, channel="whatsapp").one()
        assert log.status == "sent"


def test_no_whatsapp_without_keys(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "")
    _, org_id = _owner(client)
    with SessionLocal() as db:
        db.get(Organization, org_id).whatsapp_numbers = ["+919876543210"]
        db.commit()
        r, a = _google_review(db, org_id, 1, sentiment="negative", urgency="high")
        with patch("app.services.whatsapp.httpx.post") as post:
            alerts.alert_for_review(db, r, a)
        assert post.call_count == 0


def test_contact_form_creates_a_lead_admin_can_see(client):
    from app.models import Lead

    assert client.post("/api/v1/public/contact", json={"name": "Ravi K", "restaurant": "Ravi Mess"}).status_code == 422
    res = client.post(
        "/api/v1/public/contact",
        json={"name": "Ravi K", "restaurant": "Ravi Mess", "email": "ravi+lead@example.com", "outlets": 2},
    )
    assert res.status_code == 201
    admin = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    rows = client.get("/api/v1/admin/leads", headers={"Authorization": f"Bearer {admin}"}).json()
    lead = next(r for r in rows if r["restaurant"] == "Ravi Mess")
    upd = client.patch(
        f"/api/v1/admin/leads/{lead['id']}", json={"status": "contacted"}, headers={"Authorization": f"Bearer {admin}"}
    )
    assert upd.json()["status"] == "contacted"
    h, _ = _owner(client)
    assert client.get("/api/v1/admin/leads", headers=h).status_code == 403
    with SessionLocal() as db:
        db.query(Lead).filter_by(restaurant="Ravi Mess").delete()
        db.commit()


def test_three_star_autoreply_and_holding_reply(client):
    from datetime import UTC, datetime, timedelta

    h, org_id = _owner(client)
    res = client.patch(
        "/api/v1/settings",
        json={
            "autopilot_enabled": True,
            "autopilot_min_rating": 3,
            "holding_reply_hours": 2,
            "owner_phone": "9876543210",
        },
        headers=h,
    )
    assert res.status_code == 200 and res.json()["holding_reply_hours"] == 2
    with SessionLocal() as db:
        db.add(SourceConnection(organization_id=org_id, provider="google", status="connected"))
        db.commit()
        mixed, ma = _google_review(db, org_id, 3, sentiment="neutral")
        with patch.object(autopilot.google_reviews, "post_reply") as post:
            assert autopilot.maybe_auto_reply(db, mixed, ma) is True
        angry, _ = _google_review(db, org_id, 1, sentiment="negative", urgency="high", category="hygiene")
        fresh, _ = _google_review(db, org_id, 2, sentiment="negative", urgency="medium")
        angry.created_at = datetime.now(UTC) - timedelta(hours=3)  # waited 3 hours, nobody replied
        db.commit()
        with patch.object(autopilot.google_reviews, "post_reply") as post:
            assert autopilot.send_holding_replies(db) >= 1
            texts = [c.args[3] for c in post.call_args_list if c.args[2].id == angry.id]
        assert texts and "9876543210" in texts[0] and "refund" not in texts[0].lower()
        db.refresh(angry)
        db.refresh(fresh)
        assert angry.workflow_status == "in_progress" and angry.holding_reply_at  # a person still follows up
        assert fresh.holding_reply_at is None  # only 0 hours old: not yet


def test_outlet_details_and_own_qr_link(client):
    h, _ = _owner(client)
    body = {
        "name": "RS Puram",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "pincode": "641002",
        "manager_name": "Ravi",
        "manager_email": "Ravi@Example.com",
        "zomato_url": "https://www.zomato.com/coimbatore/x",
    }
    o = client.post("/api/v1/outlets", json=body, headers=h).json()
    assert o["district"] == "Coimbatore" and o["manager_email"] == "ravi@example.com"
    client.get("/api/v1/settings", headers=h)  # makes the feedback link
    listed = {x["name"]: x for x in client.get("/api/v1/outlets", headers=h).json()}
    assert listed["RS Puram"]["feedback_url"].endswith(f"?o={o['id']}")
    assert client.post("/api/v1/outlets", json={**body, "pincode": "12"}, headers=h).status_code == 422
    upd = client.put(f"/api/v1/outlets/{o['id']}", json={**body, "phone": "0422 1234567"}, headers=h).json()
    assert upd["phone"] == "0422 1234567"


def test_upload_creates_outlets_named_in_the_file(client):
    h, org_id = _owner(client)
    csv = "rating,review_text,outlet\n1,Hair in the biryani,Gandhipuram\n5,Super,Peelamedu\n"
    res = client.post("/api/v1/imports", files={"file": ("r.csv", csv.encode(), "text/csv")}, headers=h)
    assert res.status_code == 202
    names = {x["name"] for x in client.get("/api/v1/outlets", headers=h).json()}
    assert {"Gandhipuram", "Peelamedu"} <= names
