"""Run:  pytest -q      (no API key needed — uses keyword search and passage mode)"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.update({"DATABASE_URL": "sqlite:///" + str(ROOT / "data" / "test.db"), "OPENAI_API_KEY": "",
                   "SEARCH_MODE": "keyword", "JWT_SECRET": "test-secret-0123456789abcdef0123456789abcdef",
                   "ADMIN_EMAIL": "admin@test.dev", "ADMIN_PASSWORD": "Admin@12345", "ALLOW_SIGNUP": "true"})
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "test.db").unlink(missing_ok=True)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_ask_and_sources(client):
    r = client.post("/auth/register", json={"first_name": "Test", "last_name": "User", "email": "t@test.dev",
                                            "password": "password1", "lang": "en"})
    assert r.status_code == 200
    tok = r.json()["token"]
    assert r.json()["user"]["username"] == "t"
    a = client.post("/chat", json={"question": "How much BDX is needed for a masternode?"}, headers=_h(tok)).json()
    assert a["found"] and "10,000" in a["answer"]
    assert a["sources"] and a["sources"][0]["url"].startswith("https://")
    assert len(a["follow_ups"]) == 3


def test_signup_rules_and_email_check(client):
    weak = {"first_name": "A", "email": "weak@test.dev", "password": "abcdefgh"}
    assert client.post("/auth/register", json=weak).status_code == 422          # no number
    assert client.get("/auth/check-email", params={"email": "t@test.dev"}).json() == {"valid": True, "available": False}
    assert client.get("/auth/check-email", params={"email": "new@test.dev"}).json()["available"] is True
    assert client.get("/auth/check-email", params={"email": "not-an-email"}).json()["valid"] is False
    dup = {"first_name": "B", "email": "T@test.dev", "password": "password1"}
    assert client.post("/auth/register", json=dup).status_code == 409


def test_web_app_is_served(client):
    r = client.get("/index.html")
    assert r.status_code == 200 and "<title>Beldex AI" in r.text


def test_general_crypto_and_tamil_questions_are_answered(client):
    tok = client.post("/auth/login", json={"login": "t@test.dev", "password": "password1"}).json()["token"]
    for q in ["What is the purpose of a blockchain?", "What is the difference between Bitcoin and Beldex?",
              "பிளாக்செயின் என்றால் என்ன?", "கிரிப்டோகரன்சி என்றால் என்ன?", "2026-இல் என்ன புதுசு?"]:
        a = client.post("/chat", json={"question": q, "lang": "ta"}, headers=_h(tok)).json()
        assert a["found"], q


def test_academy_page_is_served(client):
    assert "Beldex Academy" in client.get("/learn.html").text


def test_off_topic_is_refused(client):
    tok = client.post("/auth/login", json={"login": "t@test.dev", "password": "password1"}).json()["token"]
    a = client.post("/chat", json={"question": "What is the weather in Chennai today?"}, headers=_h(tok)).json()
    assert a["found"] is False and a["sources"] == []


def test_user_cannot_use_admin(client):
    assert client.post("/auth/login", json={"login": "t@test.dev", "password": "password1", "as_role": "admin"}).status_code == 403
    tok = client.post("/auth/login", json={"login": "t@test.dev", "password": "password1"}).json()["token"]
    assert client.get("/admin/overview", headers=_h(tok)).status_code == 403


def test_admin_sees_usage_and_can_suspend(client):
    tok = client.post("/auth/login", json={"login": "admin@test.dev", "password": "Admin@12345", "as_role": "admin"}).json()["token"]
    o = client.get("/admin/overview", headers=_h(tok)).json()
    assert o["kpis"]["questions"] >= 2
    users = client.get("/admin/users", headers=_h(tok)).json()
    tester = next(u for u in users if u["email"] == "t@test.dev")
    assert tester["questions"] == 7 and tester["sessions"] >= 2
    assert client.patch(f"/admin/users/{tester['id']}", json={"active": False}, headers=_h(tok)).status_code == 200
    assert client.post("/auth/login", json={"login": "t@test.dev", "password": "password1"}).status_code == 403


def test_zz_logout_ends_session(client):
    tok = client.post("/auth/login", json={"login": "admin@test.dev", "password": "Admin@12345"}).json()["token"]
    assert client.post("/auth/logout", headers=_h(tok)).status_code == 200
    assert client.get("/me", headers=_h(tok)).status_code == 401


def test_voice_endpoints(client, monkeypatch):
    from app import voice
    tok = client.post("/auth/login", json={"login": "admin@test.dev", "password": "Admin@12345"}).json()["token"]
    h = _h(tok)
    # no key -> server voice off, the web app falls back to the browser
    assert client.get("/voice/status", headers=h).json()["server"] is False
    assert client.post("/voice/transcribe", content=b"x", headers=h).status_code == 503
    # with a key (mocked): speech -> text, text -> mp3, and voice questions are counted
    monkeypatch.setattr(voice, "available", lambda: True)
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "What is BNS?")
    monkeypatch.setattr(voice, "speak", lambda text, lang: (b"ID3fake-mp3", False))
    r = client.post("/voice/transcribe?lang=en&secs=3", content=b"fake-webm", headers={**h, "Content-Type": "audio/webm"})
    assert r.json() == {"text": "What is BNS?"}
    r = client.post("/voice/speak", json={"text": "**BNS** is the Beldex Name Service [1].", "lang": "en"}, headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
    client.post("/chat", json={"question": "What is BNS?", "via": "voice"}, headers=h)
    assert client.get("/admin/overview", headers=h).json()["kpis"]["voice_pct"] > 0
    assert voice.speakable("**Hi** [2]\n- one") == "Hi \none"
