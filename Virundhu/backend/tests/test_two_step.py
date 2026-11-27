"""Two-step sign-in: password + authenticator code, recovery codes, no replays, admin can be required to use it."""

import uuid

import pyotp
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.services import two_step


def _owner(client):
    email = f"otp-{uuid.uuid4().hex[:6]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Otp Owner",
            "organization_name": "Otp Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    )
    return email, {"Authorization": f"Bearer {r.json()['access_token']}"}


def _now_code(secret: str, steps: int = 0) -> str:
    t = pyotp.TOTP(secret)
    import time

    return t.at(time.time() + steps * t.interval)


def test_switch_on_then_sign_in_needs_the_code(client):
    email, h = _owner(client)
    start = client.post("/api/v1/account/two-step/start", headers=h).json()
    secret = start["secret"]
    assert start["otpauth_uri"].startswith("otpauth://totp/Virundhu") and start["qr_svg_base64"]
    assert client.post("/api/v1/account/two-step/confirm", json={"code": "000000"}, headers=h).status_code == 400
    import time

    time.sleep(1.1)  # tokens carry whole seconds: the old one must be from an earlier second
    on = client.post("/api/v1/account/two-step/confirm", json={"code": _now_code(secret, -1)}, headers=h)
    assert on.status_code == 200, on.text
    recovery = on.json()["recovery_codes"]
    assert len(recovery) == 8
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401  # old session signed out
    fresh = {"Authorization": f"Bearer {on.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=fresh).json()["two_step"] is True

    no_code = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1"})
    assert no_code.status_code == 401 and no_code.headers["x-two-step"] == "required"
    wrong = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1", "code": "123456"})
    assert wrong.status_code == 401
    code = _now_code(secret)
    ok = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1", "code": code})
    assert ok.status_code == 200, ok.text
    replay = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1", "code": code})
    assert replay.status_code == 401  # a code works once
    rec = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1", "code": recovery[0]})
    assert rec.status_code == 200
    again = client.post("/api/v1/auth/login", json={"email": email, "password": "Strong#Pass1", "code": recovery[0]})
    assert again.status_code == 401  # recovery codes are single-use
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == email))
        assert u.totp_secret and secret not in u.totp_secret  # stored encrypted
        assert len(u.totp_recovery) == 7


def test_wrong_password_never_reveals_two_step(client):
    email, h = _owner(client)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == email))
        two_step.start(u)
        db.commit()
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope"})
    assert r.status_code == 401 and "x-two-step" not in r.headers


def test_admin_console_waits_for_two_step_when_required(client, monkeypatch):
    tok = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    a = {"Authorization": f"Bearer {tok}"}
    monkeypatch.setattr(settings, "ADMIN_REQUIRE_TWO_STEP", True)
    r = client.get("/api/v1/admin/stats", headers=a)
    assert r.status_code == 403 and r.headers.get("x-two-step") == "setup"
    assert client.get("/api/v1/auth/me", headers=a).json()["two_step_required"] is True
    assert client.get("/api/v1/account/two-step", headers=a).status_code == 200  # set-up stays reachable
    monkeypatch.setattr(settings, "ADMIN_REQUIRE_TWO_STEP", False)
    assert client.get("/api/v1/admin/stats", headers=a).status_code == 200
