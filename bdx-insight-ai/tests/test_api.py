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
    r = client.post("/auth/register", json={"name": "Test User", "username": "tester", "email": "t@test.dev",
                                            "password": "password1", "lang": "en"})
    assert r.status_code == 200
    tok = r.json()["token"]
    a = client.post("/chat", json={"question": "How much BDX is needed for a masternode?"}, headers=_h(tok)).json()
    assert a["found"] and "10,000" in a["answer"]
    assert a["sources"] and a["sources"][0]["url"].startswith("https://")


def test_off_topic_is_refused(client):
    tok = client.post("/auth/login", json={"login": "tester", "password": "password1"}).json()["token"]
    a = client.post("/chat", json={"question": "What is the weather in Chennai today?"}, headers=_h(tok)).json()
    assert a["found"] is False and a["sources"] == []


def test_user_cannot_use_admin(client):
    assert client.post("/auth/login", json={"login": "tester", "password": "password1", "as_role": "admin"}).status_code == 403
    tok = client.post("/auth/login", json={"login": "tester", "password": "password1"}).json()["token"]
    assert client.get("/admin/overview", headers=_h(tok)).status_code == 403


def test_admin_sees_usage_and_can_suspend(client):
    tok = client.post("/auth/login", json={"login": "admin@test.dev", "password": "Admin@12345", "as_role": "admin"}).json()["token"]
    o = client.get("/admin/overview", headers=_h(tok)).json()
    assert o["kpis"]["questions"] >= 2
    users = client.get("/admin/users", headers=_h(tok)).json()
    tester = next(u for u in users if u["username"] == "tester")
    assert tester["questions"] == 2 and tester["sessions"] >= 2
    assert client.patch(f"/admin/users/{tester['id']}", json={"active": False}, headers=_h(tok)).status_code == 200
    assert client.post("/auth/login", json={"login": "tester", "password": "password1"}).status_code == 403


def test_logout_ends_session(client):
    tok = client.post("/auth/login", json={"login": "admin@test.dev", "password": "Admin@12345"}).json()["token"]
    assert client.post("/auth/logout", headers=_h(tok)).status_code == 200
    assert client.get("/me", headers=_h(tok)).status_code == 401
