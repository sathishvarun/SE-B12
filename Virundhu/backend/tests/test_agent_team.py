"""The AI agent team: Nila books demos, Tara answers tickets, nobody waits on a person."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import AgentRun, DemoMeeting, Lead, Organization, SupportTicket, TicketMessage
from app.services import agent_team


@pytest.fixture()
def mail(monkeypatch):
    sent: list[tuple[list[str], str]] = []

    def fake(to, subject, text, html=None, attachments=None, details=None):
        sent.append((to, subject))
        return True

    monkeypatch.setattr(agent_team, "send_email", fake)
    return sent


@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.execute(delete(Lead).where(Lead.restaurant.like("TEST Agent%")))
    s.execute(delete(AgentRun).where(AgentRun.action.like("%TEST Agent%")))
    s.commit()
    s.close()


def test_contact_needs_email(client):
    body = {"name": "Anu", "restaurant": "TEST Agent Mess", "phone": "9876543210"}
    r = client.post("/api/v1/public/contact", json=body)
    assert r.status_code == 422


def test_nila_offers_books_and_reminds(client, db, mail):
    lead = Lead(name="Anu K", restaurant="TEST Agent Mess", email="info+agent@skminimart.com", meet_mode="zoom")
    db.add(lead)
    db.commit()
    agent_team.nila_round(db)
    db.commit()
    m = db.scalar(select(DemoMeeting).where(DemoMeeting.lead_id == lead.id))
    assert m and len(m.slots) == 6 and m.status == "offered"
    assert any("Pick a time" in s for _, s in mail)

    page = client.get(f"/api/v1/public/contact/demo/{m.token}").json()
    assert page["restaurant"] == "TEST Agent Mess" and page["mode"] == "zoom"
    r = client.post(f"/api/v1/public/contact/demo/{m.token}/book", json={"slot": m.slots[0], "mode": "zoom"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "booked" and "meet.jit.si" in r.json()["where"]
    assert any("booked" in s for _, s in mail)

    # The same time can't be taken twice
    other = Lead(name="Bala", restaurant="TEST Agent Two", email="info+agent2@skminimart.com")
    db.add(other)
    db.commit()
    agent_team.offer_times(db, other)
    db.commit()
    m2 = db.scalar(select(DemoMeeting).where(DemoMeeting.lead_id == other.id))
    assert m.slots[0] not in m2.slots

    # Reminder a day before
    db.refresh(m)
    m.starts_at = datetime.now(UTC) + timedelta(hours=20)
    db.commit()
    mail.clear()
    agent_team.nila_round(db)
    db.commit()
    assert any("tomorrow" in s for _, s in mail)


def test_tara_answers_and_escalates_refunds(db, mail, monkeypatch):
    org = db.scalar(select(Organization).where(Organization.is_demo.is_(True)))
    monkeypatch.setattr(agent_team, "_ask_llm", lambda t, th, f, n: agent_team.TaraReply(
        reply="Go to Settings, then Sources. - Tara", resolved=True, needs_person=False))
    monkeypatch.setattr(agent_team, "recover_payment", lambda db, org: None)
    escalated: list[str] = []
    monkeypatch.setattr(agent_team, "call_admin", lambda db, a, what, d, ref=None: escalated.append(what))

    t = SupportTicket(organization_id=org.id, restaurant=org.name, user_email="info+agent@skminimart.com",
                      category="other", subject="TEST Agent how do I connect Google")
    db.add(t)
    db.flush()
    db.add(TicketMessage(ticket_id=t.id, body="Where do I connect Google?"))
    db.commit()
    agent_team.handle_ticket(db, t)
    db.commit()
    db.refresh(t)
    assert t.status == "resolved" and not escalated

    t2 = SupportTicket(organization_id=org.id, restaurant=org.name, user_email="info+agent@skminimart.com",
                       category="payment", subject="TEST Agent refund please")
    db.add(t2)
    db.flush()
    db.add(TicketMessage(ticket_id=t2.id, body="I want a refund for last month"))
    db.commit()
    agent_team.handle_ticket(db, t2)
    db.commit()
    db.refresh(t2)
    assert t2.status == "in_progress" and escalated
    for x in (t, t2):
        db.delete(x)
    db.commit()


def test_admin_feed_requires_admin(client):
    assert client.get("/api/v1/admin/agents").status_code in (401, 403)
