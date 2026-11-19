"""AI staff: work counts, today's moves, crisis radar, guest win-back and the owner's rules."""

import uuid
from datetime import date

from app.database import SessionLocal
from app.models import Organization, Review, ReviewAnalysis
from app.services import ai_staff


def _owner(client):
    email = f"staff-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Staff Owner",
            "organization_name": "Staff Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def _review(db, org_id, rating, category, sentiment, text, contact=None, dishes=None, staff=None, language="english"):
    r = Review(
        organization_id=org_id,
        external_id=f"q-{uuid.uuid4().hex[:8]}",
        platform="direct",
        rating=rating,
        review_date=date.today(),
        review_text=text,
        analysis_status="analyzed",
        workflow_status="new",
        guest_name="Ravi Kumar" if contact else None,
        guest_contact=contact,
    )
    db.add(r)
    db.flush()
    db.add(
        ReviewAnalysis(
            review_id=r.id,
            sentiment=sentiment,
            category=category,
            urgency="high" if category == "hygiene" else "medium",
            language=language,
            summary=text[:80],
            suggested_reply="Sorry, we'll fix it.",
            status="analyzed",
            dishes=dishes or [],
            staff=staff or [],
        )
    )
    db.commit()
    return r


def test_command_center_counts_work_and_finds_patterns(client):
    h, org_id = _owner(client)
    with SessionLocal() as db:
        for _ in range(3):
            _review(db, org_id, 2, "food_quality", "negative", "Biryani was cold and dry", dishes=["Chicken biryani"])
        _review(db, org_id, 5, "staff", "positive", "Lovely service by Ramesh", staff=["Ramesh"])
        bad = _review(
            db, org_id, 1, "delivery", "negative", "Late and spilled", contact="9876543210", language="tanglish"
        )

    data = client.get("/api/v1/ai-staff", headers=h).json()
    assert {a["key"] for a in data["agents"]} >= {"listener", "responder", "guardian", "radar", "winback"}
    assert data["roi"]["reviews_read"] == 5 and data["roi"]["hours_saved"] > 0
    assert data["roi"]["revenue_at_risk"] == 4 * 3 * 400  # 4 unhappy reviews x 3 guests x Rs 400
    crisis = data["crises"][0]
    assert crisis["topic"] == "food quality" and crisis["count"] == 3 and "Chicken biryani" in crisis["likely_cause"]
    titles = " ".join(m["title"] for m in data["moves"])
    assert "Reply to 4 unhappy guests" in titles and "Fix food quality" in titles
    assert len(data["moves"]) <= 3
    assert [r["review_id"] for r in data["recovery"]] == [bad.id]

    # Win-back: Tanglish guest gets a Tamil-flavoured message, a code and a WhatsApp link
    msg = client.post(f"/api/v1/ai-staff/recovery/{bad.id}", headers=h).json()
    assert msg["code"].startswith("VR") and "Vanakkam Ravi" in msg["message"]
    back = client.post(f"/api/v1/ai-staff/recovery/{bad.id}/status", json={"status": "returned"}, headers=h)
    assert back.status_code == 200
    data = client.get("/api/v1/ai-staff", headers=h).json()
    row = next(r for r in data["recovery"] if r["review_id"] == bad.id)
    assert row["status"] == "returned" and row["whatsapp_url"].startswith("https://wa.me/919876543210")
    assert data["roi"]["revenue_won_back"] == 400


def test_owner_rules_stop_auto_replies(client):
    h, org_id = _owner(client)
    saved = client.put(
        "/api/v1/ai-staff/rules",
        json={
            "banned_words": ["free"],
            "escalate": ["delivery", "nonsense"],
            "avg_order_value": 650,
            "comeback_offer": "a free filter coffee",
        },
        headers=h,
    ).json()
    assert saved["escalate"] == ["delivery"] and saved["avg_order_value"] == 650
    with SessionLocal() as db:
        org = db.get(Organization, org_id)
        r = _review(db, org_id, 5, "food_quality", "positive", "Great dosa")
        a = db.query(ReviewAnalysis).filter_by(review_id=r.id).one()
        assert ai_staff.reply_allowed(org, r, a)
        a.suggested_reply = "Thanks! Your next dessert is free."
        assert not ai_staff.reply_allowed(org, r, a)  # banned word
        a.suggested_reply, a.category = "Thanks!", "delivery"
        assert not ai_staff.reply_allowed(org, r, a)  # escalated topic waits for a person


def test_other_restaurants_cannot_touch_my_guests(client):
    h1, org1 = _owner(client)
    h2, _ = _owner(client)
    with SessionLocal() as db:
        r = _review(db, org1, 1, "staff", "negative", "Rude", contact="9876500000")
    assert client.post(f"/api/v1/ai-staff/recovery/{r.id}", headers=h2).status_code == 404
