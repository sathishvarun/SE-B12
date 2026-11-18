"""Billing-software hook, nearby competitors, testimonials and the extra review platforms."""

from unittest.mock import patch

from app.config import settings
from tests.test_automation import _owner


def _admin(client):
    tok = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_billing_software_hook(client, monkeypatch):
    h, _ = _owner(client)
    key = client.post("/api/v1/settings/billing-key", headers=h).json()["key"]
    body = {"phone": "98765 43210", "outlet": "Main outlet"}
    assert client.post("/api/v1/hooks/bill", json=body, headers={"X-Virundhu-Key": "vbk_wrong"}).status_code == 401
    hk = {"X-Virundhu-Key": key}
    assert client.post("/api/v1/hooks/bill", json=body, headers=hk).json()["status"] == "off"
    client.patch("/api/v1/settings", json={"ask_after_bill": True}, headers=h)
    assert client.post("/api/v1/hooks/bill", json=body, headers=hk).status_code == 409  # WhatsApp not connected
    monkeypatch.setattr(type(settings), "whatsapp_enabled", property(lambda _: True))
    with patch("app.services.review_requests.whatsapp.send_review_request", return_value=True) as send:
        assert client.post("/api/v1/hooks/bill", json=body, headers=hk).json()["status"] == "sent"
        assert client.post("/api/v1/hooks/bill", json=body, headers=hk).json()["status"] == "skipped_recent"
    assert send.call_count == 1
    assert client.get("/api/v1/settings", headers=h).json()["has_billing_key"] is True


def test_nearby_competitors(client, monkeypatch):
    h, _ = _owner(client)
    o = client.post("/api/v1/outlets", json={"name": "RS Puram", "area": "DB Road", "city": "Coimbatore"}, headers=h)
    oid = o.json()["id"]
    assert client.get(f"/api/v1/competitors?outlet_id={oid}", headers=h).json() == {"enabled": False}
    monkeypatch.setattr(settings, "GOOGLE_PLACES_API_KEY", "test")
    me = {"id": "me", "name": "Auto Mess RS Puram", "rating": 4.1, "reviews": 320, "address": ""}
    others = [
        me,
        {"id": "a", "name": "Biryani A", "rating": 4.5, "reviews": 900, "address": ""},
        {"id": "b", "name": "Mess B", "rating": 3.9, "reviews": 120, "address": ""},
    ]
    with patch("app.services.competitors._search", side_effect=[[me], others]) as search:
        data = client.get(f"/api/v1/competitors?outlet_id={oid}", headers=h).json()
        assert data["you"]["rating"] == 4.1 and [p["name"] for p in data["nearby"]] == ["Biryani A", "Mess B"]
        assert data["area_average"] == 4.2
        client.get(f"/api/v1/competitors?outlet_id={oid}", headers=h)  # second time: from the day's cache
    assert search.call_count == 2


def test_testimonials_only_published_and_admin_only(client):
    a = _admin(client)
    h, _ = _owner(client)
    body = {"name": "Kumar", "role": "Owner, test", "quote": "We caught a hygiene complaint the same day."}
    assert client.post("/api/v1/admin/testimonials", json=body, headers=h).status_code == 403
    t = client.post("/api/v1/admin/testimonials", json=body, headers=a).json()
    assert all(x["id"] != t["id"] for x in client.get("/api/v1/public/testimonials").json())
    client.put(f"/api/v1/admin/testimonials/{t['id']}", json={**body, "published": True}, headers=a)
    assert any(x["id"] == t["id"] for x in client.get("/api/v1/public/testimonials").json())
    client.delete(f"/api/v1/admin/testimonials/{t['id']}", headers=a)


def test_tripadvisor_and_instagram_reviews(client):
    h, _ = _owner(client)
    with patch("app.routers.intake.enqueue_analysis"):
        for p in ("tripadvisor", "instagram", "facebook"):
            body = {"text": "Lovely view and food", "rating": 5, "platform": p}
            assert client.post("/api/v1/reviews", json=body, headers=h).status_code == 202
