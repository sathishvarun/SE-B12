"""Token ledger (owner + admin views), pricing up to 1,000 outlets, Google reviews by Maps listing (Places mocked)."""

import uuid
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from sqlalchemy import delete, select

from app.ai.usage import UsageRecorder
from app.config import settings
from app.database import SessionLocal
from app.models import AiUsage, Outlet, Review
from app.services import google_places, pricing


def _owner(client, name="Token Mess"):
    email = f"tok-{uuid.uuid4().hex[:6]}@example.com"
    data = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Tok Owner", "organization_name": name, "email": email, "password": "Strong#Pass1",
              "accept_terms": True},
    ).json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"]


def _admin(client) -> dict:
    tok = client.post("/api/v1/auth/login", json={
        "email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _llm_result(tin: int, tout: int) -> LLMResult:
    usage = {"input_tokens": tin, "output_tokens": tout, "total_tokens": tin + tout}
    msg = AIMessage(content="ok", usage_metadata=usage, response_metadata={"model_name": "gpt-test"})
    return LLMResult(generations=[[ChatGeneration(message=msg)]])


def test_every_ai_call_is_counted_per_restaurant(client):
    h1, org1 = _owner(client, "Token Mess One")
    h2, org2 = _owner(client, "Token Mess Two")
    # what the model callback sees after each AI call
    UsageRecorder("review_reading", org1).on_llm_end(_llm_result(1200, 300))
    UsageRecorder("review_reading", org1).on_llm_end(_llm_result(800, 200))
    UsageRecorder("ask", org1).on_llm_end(_llm_result(2000, 500))
    UsageRecorder("review_reading", org2).on_llm_end(_llm_result(100, 50))
    UsageRecorder("support_draft", None).on_llm_end(_llm_result(10, 10))  # Virundhu's own work
    UsageRecorder("review_reading", org2).on_llm_end(_llm_result(0, 0))  # nothing used: no row

    mine = client.get("/api/v1/usage/tokens", headers=h1).json()
    assert mine["this_month"]["tokens"] == 5000 and mine["this_month"]["calls"] == 3
    assert mine["this_month"]["input_tokens"] == 4000 and mine["all_time"]["tokens"] == 5000
    assert mine["this_month"]["cost_inr"] == 0  # owners never see the platform's rupee cost
    feats = {f["feature"]: f["tokens"] for f in mine["by_feature"]}
    assert feats == {"review_reading": 2500, "ask": 2500}
    assert len(mine["daily"]) == 30 and sum(d["tokens"] for d in mine["daily"]) == 5000
    theirs = client.get("/api/v1/usage/tokens", headers=h2).json()
    assert theirs["all_time"]["tokens"] == 150  # never another restaurant's numbers

    admin = _admin(client)
    total = client.get("/api/v1/admin/tokens", headers=admin).json()
    assert total["windows"]["today"]["tokens"] >= 5170 and total["windows"]["all_time"]["cost_inr"] > 0
    assert total["platform_own"]["tokens"] >= 20
    rows = {r["id"]: r for r in client.get("/api/v1/admin/tokens/restaurants", headers=admin).json()}
    assert rows[org1]["tokens_this_month"] == 5000 and rows[org1]["calls_all_time"] == 3
    assert rows[org2]["tokens_all_time"] == 150
    assert rows[org1]["cost_all_time_inr"] > rows[org2]["cost_all_time_inr"]
    # owners can't open the admin views
    assert client.get("/api/v1/admin/tokens", headers=h1).status_code == 403
    assert client.get("/api/v1/admin/tokens/restaurants", headers=h1).status_code == 403
    with SessionLocal() as db:
        db.execute(delete(AiUsage).where(AiUsage.organization_id.is_(None), AiUsage.feature == "support_draft",
                                         AiUsage.input_tokens == 10))
        db.commit()


def test_outlets_up_to_1000_priced_exactly():
    q = pricing.quote(700, 12)  # a 700-outlet chain for a year
    assert q.per_outlet_month == 649 and q.total == round(649 * 700 * 12 * 0.85) == 4633860
    assert pricing.quote(1000, 1).total == 649000
    assert pricing.table()["max_outlets"] == 1000
    for bad in (0, 1001):
        try:
            pricing.quote(bad, 1)
        except pricing.PricingError:
            continue
        raise AssertionError(f"{bad} outlets should be refused")


def test_quote_endpoint_for_big_chain(client):
    res = client.get("/api/v1/billing/quote", params={"outlets": 700, "months": 12})
    assert res.status_code == 200, res.text
    assert res.json()["total"] == 4633860
    assert client.get("/api/v1/billing/quote", params={"outlets": 1001, "months": 1}).status_code in (400, 422)


def test_google_reviews_by_maps_listing(client, monkeypatch):
    h, org = _owner(client, "Places Mess")
    outlet_id = client.post("/api/v1/outlets", json={"name": "Places Mess RS Puram", "city": "Coimbatore"},
                            headers=h).json()["id"]
    assert client.get("/api/v1/places/status", headers=h).json()["enabled"] is False
    monkeypatch.setattr(settings, "GOOGLE_PLACES_API_KEY", "test")
    found = [{"place_id": "ChIJplacesMess01", "name": "Places Mess", "address": "Coimbatore", "rating": 4.2,
              "reviews": 80}]
    with patch("app.services.google_places.search", return_value=found):
        assert client.get("/api/v1/places/search", params={"q": "Places Mess Coimbatore"}, headers=h).json() == found
    details = {
        "displayName": {"text": "Places Mess"}, "rating": 4.2, "userRatingCount": 81,
        "reviews": [
            {"name": "places/ChIJplacesMess01/reviews/r1", "rating": 5, "publishTime": "2026-11-18T10:00:00Z",
             "originalText": {"text": "சாப்பாடு அருமை, super service"}, "authorAttribution": {"displayName": "Kumar"}},
            {"name": "places/ChIJplacesMess01/reviews/r2", "rating": 1, "publishTime": "2026-11-19T10:00:00Z",
             "text": {"text": "Found a hair in the sambar"}},
        ],
    }
    queued = []

    async def fake_enqueue(org_id, ids, batch_id=None):
        queued.append((org_id, ids))

    with patch("app.services.google_places._details", return_value=details), \
            patch("app.routers.places.enqueue_analysis", side_effect=fake_enqueue):
        res = client.put(f"/api/v1/outlets/{outlet_id}/google-place", json={"place_id": "ChIJplacesMess01"}, headers=h)
        assert res.status_code == 200, res.text
        assert res.json()["new_reviews"] == 2 and res.json()["outlet"]["rating"] == 4.2
        again = client.post(f"/api/v1/outlets/{outlet_id}/google-place/sync", headers=h).json()
        assert again["new_reviews"] == 0 and "no new reviews" in again["message"]  # same reviews: not added twice
    assert queued and queued[0][0] == org and len(queued[0][1]) == 2
    with SessionLocal() as db:
        rows = db.scalars(select(Review).where(Review.organization_id == org, Review.platform == "google")).all()
        assert {r.rating for r in rows} == {5, 1} and any("அருமை" in r.review_text for r in rows)
        assert all(r.source_ref is None for r in rows)  # Places reviews are never auto-replied on Google
        assert db.get(Outlet, outlet_id).google_rating_count == 81
    # another restaurant can't touch this outlet
    h2, _ = _owner(client, "Other Mess")
    assert client.post(f"/api/v1/outlets/{outlet_id}/google-place/sync", headers=h2).status_code == 404
    # a refused key shows the owner a plain message instead of failing
    with patch("app.services.google_places._details", side_effect=google_places.PlacesError("Google refused.")):
        out = client.post(f"/api/v1/outlets/{outlet_id}/google-place/sync", headers=h).json()
        assert out["outlet"]["error"] == "Google refused."
    assert client.delete(f"/api/v1/outlets/{outlet_id}/google-place", headers=h).json() == {"ok": True}
    status = client.get("/api/v1/places/status", headers=h).json()["outlets"]
    assert next(o for o in status if o["outlet_id"] == outlet_id)["place_id"] is None


def test_review_values_skip_bad_rows():
    assert google_places._review_values(1, 1, {"rating": 5}) is None
    v = google_places._review_values(1, 2, {"name": "places/x/reviews/abc", "rating": 4.6})
    assert v["rating"] == 5 and v["external_id"] == "gp:abc" and v["review_text"] == ""
