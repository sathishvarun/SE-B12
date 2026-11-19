"""Feedback about Virundhu itself: the form, the ease-of-use check, Isai's routing and the admin numbers."""

import uuid

import pytest
from sqlalchemy import delete, select

from app.config import settings
from app.database import SessionLocal
from app.models import ProductFeedback, SupportTicket, Testimonial
from app.services import agent_team


@pytest.fixture()
def db(monkeypatch):
    monkeypatch.setattr(agent_team, "send_email", lambda *a, **k: True)
    s = SessionLocal()
    yield s
    s.execute(delete(Testimonial).where(Testimonial.quote.like("TEST FB%")))
    s.execute(delete(SupportTicket).where(SupportTicket.subject.like("From feedback: TEST FB%")))
    s.execute(delete(ProductFeedback).where(ProductFeedback.message.like("TEST FB%")))
    s.commit()
    s.close()


def _owner(client) -> dict:
    data = client.post("/api/v1/auth/register", json={
        "full_name": "FB Owner", "organization_name": "FB Mess", "email": f"fb-{uuid.uuid4().hex[:6]}@example.com",
        "password": "Strong#Pass1", "accept_terms": True}).json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def _admin(client) -> dict:
    tok = client.post("/api/v1/auth/login", json={
        "email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _read(kind: str, area: str = "inbox"):
    return lambda f: agent_team.IsaiRead(kind=kind, sentiment="neutral", area=area, summary=f.message[:60],
                                         reply="Thanks - Isai")


def test_public_form_and_honeypot(client, db):
    ok = client.post("/api/v1/public/feedback", json={"kind": "idea", "message": "TEST FB add Swiggy sync",
                                                      "email": "info+fb@skminimart.com"})
    assert ok.status_code == 201
    bot = client.post("/api/v1/public/feedback", json={"kind": "idea", "message": "TEST FB spam", "website": "x"})
    assert bot.status_code == 201
    msgs = list(db.scalars(select(ProductFeedback.message).where(ProductFeedback.message.like("TEST FB%"))))
    assert msgs == ["TEST FB add Swiggy sync"]
    assert client.post("/api/v1/public/feedback", json={"kind": "nope", "message": "TEST FB"}).status_code == 422


def test_isai_routes_problem_to_tara_and_praise_to_site(client, db, monkeypatch):
    h = _owner(client)
    monkeypatch.setattr(agent_team, "_read_feedback", _read("problem"))
    body = {"kind": "problem", "message": "TEST FB inbox filter is confusing"}
    assert client.post("/api/v1/feedback", json=body, headers=h).status_code == 201
    agent_team.isai_round(db)
    f = db.scalar(select(ProductFeedback).where(ProductFeedback.message == "TEST FB inbox filter is confusing"))
    assert f.status == "done" and f.ticket_id and "Tara" in f.agent_action

    monkeypatch.setattr(agent_team, "_read_feedback", _read("praise"))
    client.post("/api/v1/feedback", json={"kind": "praise", "rating": 5, "consent_quote": True,
                                          "message": "TEST FB saves me an hour a day"}, headers=h)
    agent_team.isai_round(db)
    assert db.scalar(select(Testimonial).where(Testimonial.quote == "TEST FB saves me an hour a day")).published


def test_ease_check_and_admin_numbers(client, db, monkeypatch):
    h = _owner(client)
    assert client.get("/api/v1/feedback/ease-prompt", headers=h).json() == {"due": False}  # too new to ask
    r = client.post("/api/v1/feedback/ease", json={"ease": 2, "nps": 9, "area": "setup",
                                                   "message": "TEST FB connecting Google took long"}, headers=h)
    assert r.status_code == 201 and "Tara" in r.json()["message"]
    monkeypatch.setattr(agent_team, "_read_feedback", _read("problem", "setup"))
    agent_team.isai_round(db)
    data = client.get("/api/v1/admin/feedback", headers=_admin(client)).json()
    assert data["ease_count"] >= 1 and data["nps"] is not None
    assert any(a == "setup" for a, _ in data["hard_areas"])
    assert client.get("/api/v1/admin/feedback", headers=h).status_code == 403
