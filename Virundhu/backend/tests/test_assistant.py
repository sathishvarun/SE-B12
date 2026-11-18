"""Ask Virundhu: numbers come from SQL, the model only explains; AI mocked."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config import settings
from app.database import SessionLocal
from app.models import Review, ReviewAnalysis


def _owner(client):
    email = f"ask-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ask Owner",
            "organization_name": "Ask Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def test_empty_restaurant_gets_a_plain_answer(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_TAGGING_MODEL", "m")
    monkeypatch.setattr(settings, "OPENAI_REPORT_MODEL", "m")
    h, _ = _owner(client)
    res = client.post("/api/v1/assistant/chat", json={"message": "What should I fix first?"}, headers=h)
    assert res.status_code == 200 and "no reviews" in res.json()["answer"]


def test_priorities_use_computed_data(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_TAGGING_MODEL", "m")
    monkeypatch.setattr(settings, "OPENAI_REPORT_MODEL", "m")
    h, org_id = _owner(client)
    for text, rating in [("Found a hair in the biryani", 1), ("Delivery 1 hour late, cold food", 2), ("Super!", 5)]:
        client.post("/api/v1/reviews", json={"text": text, "rating": rating, "platform": "zomato"}, headers=h)
    with SessionLocal() as db:
        reviews = db.query(Review).filter_by(organization_id=org_id).all()
        for r in reviews:
            if r.analysis is None:
                cat = (
                    "hygiene" if "hair" in r.review_text else "delivery" if "late" in r.review_text else "food_quality"
                )
                db.add(
                    ReviewAnalysis(
                        review_id=r.id,
                        status="analyzed",
                        sentiment="negative" if r.rating < 3 else "positive",
                        category=cat,
                        urgency="high" if r.rating == 1 else "low",
                        summary=r.review_text,
                    )
                )
                r.analysis_status = "analyzed"
        db.commit()

    fake = MagicMock()
    fake.invoke.return_value = SimpleNamespace(
        content="Priority 1: hygiene", usage_metadata={"input_tokens": 10, "output_tokens": 5}
    )
    with patch("app.services.assistant.chat_model", return_value=fake):
        res = client.post(
            "/api/v1/assistant/chat",
            json={
                "message": "What should I fix first?",
                "history": [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}],
            },
            headers=h,
        )
    assert res.status_code == 200 and res.json()["answer"] == "Priority 1: hygiene"
    system = fake.invoke.call_args.args[0][0].content
    data = json.loads(system.split("DATA:\n", 1)[1])
    assert data["total_reviews"] == 3
    assert data["unhappy_reviews_by_topic"] == {"hygiene": 1, "delivery": 1}
    assert len(data["food_safety_or_hygiene_reviews"]) == 1
    assert len(fake.invoke.call_args.args[0]) == 4  # system + 2 history turns + question


def test_another_restaurant_never_leaks(client, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "OPENAI_TAGGING_MODEL", "m")
    monkeypatch.setattr(settings, "OPENAI_REPORT_MODEL", "m")
    h1, _ = _owner(client)
    client.post("/api/v1/reviews", json={"text": "Secret complaint XYZ", "rating": 1, "platform": "google"}, headers=h1)
    h2, _ = _owner(client)
    client.post("/api/v1/reviews", json={"text": "Nice", "rating": 5, "platform": "google"}, headers=h2)
    fake = MagicMock()
    fake.invoke.return_value = SimpleNamespace(content="ok", usage_metadata={})
    with patch("app.services.assistant.chat_model", return_value=fake):
        client.post("/api/v1/assistant/chat", json={"message": "summary"}, headers=h2)
    assert "Secret complaint XYZ" not in fake.invoke.call_args.args[0][0].content
