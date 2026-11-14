"""Auth: register, login, refresh rotation, logout, /me, password reset, Google, rate limit."""

import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import oauth
from app.auth.security import create_access_token, hash_token, verify_password
from app.config import settings
from app.models import PasswordResetToken, RefreshToken, Subscription, User
from app.rate_limit import limiter
from tests.conftest import API, PASSWORD, Outbox, Seller

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def test_register_returns_tokens_and_creates_free_subscription(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    resp = client.post(
        f"{API}/auth/register",
        json={"email": "New@Example.com ", "password": PASSWORD, "full_name": "  New User "},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body) == {"access_token", "refresh_token", "token_type"}
    assert body["token_type"] == "bearer"

    user = db.scalar(select(User).where(User.email == "new@example.com"))
    assert user is not None
    assert user.full_name == "New User"
    assert user.hashed_password != PASSWORD
    assert verify_password(PASSWORD, user.hashed_password or "")
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    assert sub is not None and sub.plan == "free" and sub.status == "active"
    # welcome email sent as a background task
    assert [m[1] for m in outbox.to("new@example.com")] == ["Welcome to Sathish CRM"]


def test_register_duplicate_email_is_409_case_insensitive(
    client: TestClient, seller_a: Seller
) -> None:
    resp = client.post(
        f"{API}/auth/register",
        json={"email": "ALICE@example.com", "password": PASSWORD, "full_name": "Dup"},
    )
    assert resp.status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"email": "bad-email", "password": PASSWORD, "full_name": "X"},
        {"email": "a@b.com", "password": "short", "full_name": "X"},
        {"email": "a@b.com", "password": PASSWORD, "full_name": ""},
        {"email": "a@b.com", "password": PASSWORD},
    ],
)
def test_register_validation_422(client: TestClient, body: dict) -> None:
    assert client.post(f"{API}/auth/register", json=body).status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_success(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(
        f"{API}/auth/login", json={"email": "Alice@Example.com", "password": PASSWORD}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "alice@example.com"


@pytest.mark.parametrize(
    "email,password",
    [("alice@example.com", "WrongPassword1"), ("ghost@example.com", PASSWORD)],
)
def test_login_bad_credentials_401(
    client: TestClient, seller_a: Seller, email: str, password: str
) -> None:
    resp = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Incorrect email or password"}


def test_login_inactive_user_403(client: TestClient, db: Session, seller_a: Seller) -> None:
    user = db.get(User, seller_a.id)
    assert user is not None
    user.is_active = False
    db.commit()
    resp = client.post(f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD})
    assert resp.status_code == 403


def test_login_google_only_user_without_password_401(client: TestClient, db: Session) -> None:
    db.add(User(email="g@example.com", hashed_password=None, oauth_provider="google"))
    db.commit()
    resp = client.post(f"{API}/auth/login", json={"email": "g@example.com", "password": PASSWORD})
    assert resp.status_code == 401


def test_login_is_json_not_form(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(f"{API}/auth/login", data={"username": seller_a.email, "password": PASSWORD})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Current user / token validation
# ---------------------------------------------------------------------------


def test_me_requires_auth(client: TestClient) -> None:
    assert client.get(f"{API}/auth/me").status_code == 401


def test_me_shape(client: TestClient, seller_a: Seller) -> None:
    resp = client.get(f"{API}/auth/me", headers=seller_a.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "id",
        "email",
        "full_name",
        "is_active",
        "is_verified",
        "is_admin",
        "oauth_provider",
        "has_password",
        "plan",
        "created_at",
    }
    assert body["plan"] == "free"
    assert body["has_password"] is True
    assert body["is_admin"] is False
    assert body["oauth_provider"] is None


@pytest.mark.parametrize(
    "token",
    [
        "garbage",
        jwt.encode({"sub": "1", "type": "refresh"}, settings.SECRET_KEY, algorithm="HS256"),
        jwt.encode({"type": "access"}, settings.SECRET_KEY, algorithm="HS256"),
        jwt.encode({"sub": "abc", "type": "access"}, settings.SECRET_KEY, algorithm="HS256"),
        jwt.encode(
            {"sub": "1", "type": "access"},
            "a-completely-different-32-byte-key!!",
            algorithm="HS256",
        ),
        jwt.encode(
            {"sub": "1", "type": "access", "exp": datetime.now(UTC) - timedelta(minutes=1)},
            settings.SECRET_KEY,
            algorithm="HS256",
        ),
    ],
)
def test_invalid_tokens_401(client: TestClient, seller_a: Seller, token: str) -> None:
    resp = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_for_deleted_user_401(client: TestClient) -> None:
    token = create_access_token(99999)
    resp = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_access_token_expiry_is_30_minutes(seller_a: Seller) -> None:
    payload = jwt.decode(seller_a.access_token, options={"verify_signature": False})
    exp = datetime.fromtimestamp(payload["exp"], UTC)
    delta = exp - datetime.now(UTC)
    assert timedelta(minutes=29) < delta <= timedelta(minutes=30)
    assert jwt.get_unverified_header(seller_a.access_token)["alg"] == "HS256"


def test_deactivated_user_with_valid_token_gets_403(
    client: TestClient, db: Session, seller_a: Seller
) -> None:
    user = db.get(User, seller_a.id)
    assert user is not None
    user.is_active = False
    db.commit()
    assert client.get(f"{API}/auth/me", headers=seller_a.headers).status_code == 403


# ---------------------------------------------------------------------------
# Refresh / logout
# ---------------------------------------------------------------------------


def test_refresh_rotates_token(client: TestClient, db: Session, seller_a: Seller) -> None:
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert resp.status_code == 200
    new = resp.json()
    assert new["refresh_token"] != seller_a.refresh_token
    # old one is revoked -> reuse fails
    again = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert again.status_code == 401
    # new one works
    ok = client.post(f"{API}/auth/refresh", json={"refresh_token": new["refresh_token"]})
    assert ok.status_code == 200
    # refresh tokens stored hashed, 7-day expiry
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(new["refresh_token"]))
    )
    assert stored is not None
    expires = stored.expires_at.replace(tzinfo=UTC)
    assert timedelta(days=6, hours=23) < expires - datetime.now(UTC) <= timedelta(days=7)


def test_refresh_unknown_token_401(client: TestClient) -> None:
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": "nope"})
    assert resp.status_code == 401


def test_refresh_expired_token_401(client: TestClient, db: Session, seller_a: Seller) -> None:
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token == hash_token(seller_a.refresh_token))
    )
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert resp.status_code == 401


def test_refresh_inactive_user_403(client: TestClient, db: Session, seller_a: Seller) -> None:
    user = db.get(User, seller_a.id)
    assert user is not None
    user.is_active = False
    db.commit()
    resp = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert resp.status_code == 403


def test_logout_revokes_refresh_token(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(
        f"{API}/auth/logout",
        json={"refresh_token": seller_a.refresh_token},
        headers=seller_a.headers,
    )
    assert resp.status_code == 204
    refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert refresh.status_code == 401


def test_logout_cannot_revoke_other_users_token(
    client: TestClient, seller_a: Seller, seller_b: Seller
) -> None:
    resp = client.post(
        f"{API}/auth/logout",
        json={"refresh_token": seller_a.refresh_token},
        headers=seller_b.headers,
    )
    assert resp.status_code == 204
    still_ok = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert still_ok.status_code == 200


def test_logout_requires_auth(client: TestClient, seller_a: Seller) -> None:
    resp = client.post(f"{API}/auth/logout", json={"refresh_token": seller_a.refresh_token})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Profile update
# ---------------------------------------------------------------------------


def test_update_full_name(client: TestClient, seller_a: Seller) -> None:
    resp = client.put(
        f"{API}/auth/me", json={"full_name": "  Alice Renamed "}, headers=seller_a.headers
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Alice Renamed"


def test_change_password_requires_correct_current_password(
    client: TestClient, seller_a: Seller
) -> None:
    bad = client.put(
        f"{API}/auth/me",
        json={"current_password": "wrong-one", "new_password": "NewPassword9"},
        headers=seller_a.headers,
    )
    assert bad.status_code == 400
    missing = client.put(
        f"{API}/auth/me", json={"new_password": "NewPassword9"}, headers=seller_a.headers
    )
    assert missing.status_code == 400

    ok = client.put(
        f"{API}/auth/me",
        json={"current_password": PASSWORD, "new_password": "NewPassword9"},
        headers=seller_a.headers,
    )
    assert ok.status_code == 200
    login_new = client.post(
        f"{API}/auth/login", json={"email": seller_a.email, "password": "NewPassword9"}
    )
    assert login_new.status_code == 200
    login_old = client.post(
        f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD}
    )
    assert login_old.status_code == 401


def test_change_password_revokes_refresh_tokens(client: TestClient, seller_a: Seller) -> None:
    resp = client.put(
        f"{API}/auth/me",
        json={"current_password": PASSWORD, "new_password": "NewPassword9"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 200
    refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert refresh.status_code == 401


def test_name_only_update_keeps_refresh_tokens(client: TestClient, seller_a: Seller) -> None:
    client.put(f"{API}/auth/me", json={"full_name": "N"}, headers=seller_a.headers)
    refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert refresh.status_code == 200


def test_google_only_user_can_set_password_without_current(client: TestClient, db: Session) -> None:
    user = User(email="g@example.com", hashed_password=None, oauth_provider="google")
    db.add(user)
    db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    me = client.get(f"{API}/auth/me", headers=headers).json()
    assert me["has_password"] is False and me["oauth_provider"] == "google"
    assert me["plan"] == "free"  # no subscription row -> free

    resp = client.put(f"{API}/auth/me", json={"new_password": "FreshPass99"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["has_password"] is True


def test_update_profile_short_new_password_422(client: TestClient, seller_a: Seller) -> None:
    resp = client.put(
        f"{API}/auth/me",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=seller_a.headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------


def _reset_token_from(outbox: Outbox, email: str) -> str:
    html = outbox.to(email)[-1][2]
    match = re.search(r"reset-password\?token=([A-Za-z0-9_\-%]+)", html)
    assert match, html
    return match.group(1)


def test_forgot_and_reset_password_flow(
    client: TestClient, db: Session, seller_a: Seller, outbox: Outbox
) -> None:
    resp = client.post(f"{API}/auth/forgot-password", json={"email": seller_a.email})
    assert resp.status_code == 200
    assert resp.json() == {"message": "If that email exists, a reset link has been sent."}
    token = _reset_token_from(outbox, seller_a.email)
    assert f"{settings.FRONTEND_URL}/reset-password?token=" in outbox.to(seller_a.email)[-1][2]

    reset = client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "BrandNew123"}
    )
    assert reset.status_code == 200
    assert reset.json() == {"message": "Password updated."}

    # new password works, old refresh tokens were revoked
    assert (
        client.post(
            f"{API}/auth/login", json={"email": seller_a.email, "password": "BrandNew123"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token}
        ).status_code
        == 401
    )
    # token is single use
    again = client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "Another123"}
    )
    assert again.status_code == 400


def test_forgot_password_unknown_email_same_message_no_email(
    client: TestClient, outbox: Outbox
) -> None:
    resp = client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "If that email exists, a reset link has been sent."
    assert outbox.messages == []


def test_forgot_password_invalidates_older_tokens(
    client: TestClient, seller_a: Seller, outbox: Outbox
) -> None:
    client.post(f"{API}/auth/forgot-password", json={"email": seller_a.email})
    first = _reset_token_from(outbox, seller_a.email)
    client.post(f"{API}/auth/forgot-password", json={"email": seller_a.email})
    second = _reset_token_from(outbox, seller_a.email)
    assert first != second
    old = client.post(
        f"{API}/auth/reset-password", json={"token": first, "new_password": "BrandNew123"}
    )
    assert old.status_code == 400
    new = client.post(
        f"{API}/auth/reset-password", json={"token": second, "new_password": "BrandNew123"}
    )
    assert new.status_code == 200


def test_reset_password_expired_token_400(
    client: TestClient, db: Session, seller_a: Seller, outbox: Outbox
) -> None:
    client.post(f"{API}/auth/forgot-password", json={"email": seller_a.email})
    token = _reset_token_from(outbox, seller_a.email)
    stored = db.scalar(select(PasswordResetToken))
    assert stored is not None
    stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    resp = client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "BrandNew123"}
    )
    assert resp.status_code == 400


def test_reset_password_invalid_token_400(client: TestClient) -> None:
    resp = client.post(
        f"{API}/auth/reset-password", json={"token": "bogus", "new_password": "BrandNew123"}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_login_rate_limited_after_5_per_minute(client: TestClient, seller_a: Seller) -> None:
    limiter.reset()
    limiter.enabled = True
    codes = [
        client.post(
            f"{API}/auth/login", json={"email": seller_a.email, "password": "wrong-pass"}
        ).status_code
        for _ in range(6)
    ]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


# ---------------------------------------------------------------------------
# Google OAuth (state JWT + nonce cookie)
# ---------------------------------------------------------------------------


@pytest.fixture
def google_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "csecret")


def _fake_google(monkeypatch: pytest.MonkeyPatch, userinfo: dict | Exception) -> None:
    async def fake_fetch(code: str) -> dict:
        if isinstance(userinfo, Exception):
            raise userinfo
        return userinfo

    monkeypatch.setattr(oauth, "fetch_google_user", fake_fetch)


def _start_google(client: TestClient) -> str:
    """GET /auth/google (sets the nonce cookie on the client) and return the state."""
    resp = client.get(f"{API}/auth/google", follow_redirects=False)
    assert resp.status_code == 307
    return parse_qs(urlparse(resp.headers["location"]).query)["state"][0]


def _callback(client: TestClient, state: str, code: str = "the-code"):
    return client.get(
        f"{API}/auth/google/callback", params={"code": code, "state": state}, follow_redirects=False
    )


FAILED = "/login?error=oauth_failed"


def test_google_login_not_configured_redirects_to_failure(client: TestClient) -> None:
    resp = client.get(f"{API}/auth/google", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"].endswith(FAILED)


def test_google_login_redirects_with_signed_state_and_cookie(
    client: TestClient, google_configured: None
) -> None:
    resp = client.get(f"{API}/auth/google", follow_redirects=False)
    assert resp.status_code == 307
    url = urlparse(resp.headers["location"])
    assert url.netloc == "accounts.google.com"
    params = parse_qs(url.query)
    assert params["client_id"] == ["cid"]
    cookie = resp.headers["set-cookie"]
    assert "oauth_state=" in cookie and "HttpOnly" in cookie
    nonce = client.cookies.get("oauth_state")
    assert oauth.verify_state(params["state"][0], nonce) is True
    assert oauth.verify_state(params["state"][0], "other-nonce") is False
    assert oauth.verify_state(params["state"][0], None) is False


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?code=abc",
        "?code=abc&state=tampered",
        "?code=abc&state=" + jwt.encode({"type": "other"}, settings.SECRET_KEY, algorithm="HS256"),
    ],
)
def test_google_callback_rejects_bad_state(client: TestClient, query: str) -> None:
    resp = client.get(f"{API}/auth/google/callback{query}", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"].endswith(FAILED)


def test_google_callback_without_cookie_fails_csrf(
    client: TestClient, google_configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid signed state is useless without the browser's matching nonce cookie."""
    _fake_google(monkeypatch, {"email": "x@example.com", "email_verified": True})
    state = _start_google(client)
    client.cookies.clear()
    assert _callback(client, state).headers["location"].endswith(FAILED)
    # a state minted directly (cookie never set on this client) is rejected too
    forged_state, _nonce = oauth.create_state()
    assert _callback(client, forged_state).headers["location"].endswith(FAILED)


def test_google_callback_creates_user_and_redirects_with_tokens(
    client: TestClient, google_configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_google(
        monkeypatch, {"email": "Goog@Example.com", "email_verified": True, "name": "Goo Gle"}
    )
    state = _start_google(client)
    resp = _callback(client, state)
    assert resp.status_code == 307
    loc = resp.headers["location"]
    assert loc.startswith(f"{settings.FRONTEND_URL}/oauth/callback#")
    fragment = parse_qs(urlparse(loc).fragment)
    headers = {"Authorization": f"Bearer {fragment['access_token'][0]}"}
    me = client.get(f"{API}/auth/me", headers=headers).json()
    assert me["email"] == "goog@example.com"
    assert me["full_name"] == "Goo Gle"
    assert me["oauth_provider"] == "google"
    assert me["has_password"] is False
    assert me["is_verified"] is True
    assert me["plan"] == "free"


def test_google_state_is_single_use(
    client: TestClient, google_configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_google(monkeypatch, {"email": "g@example.com", "email_verified": True})
    state = _start_google(client)
    assert "/oauth/callback#" in _callback(client, state).headers["location"]
    # cookie was cleared by the successful callback -> replaying the same state fails
    assert _callback(client, state).headers["location"].endswith(FAILED)


def test_google_login_into_unverified_password_account_drops_password(
    client: TestClient,
    db: Session,
    seller_a: Seller,
    google_configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-hijack protection: an unverified password account loses its password and sessions."""
    _fake_google(monkeypatch, {"email": seller_a.email, "email_verified": True})
    resp = _callback(client, _start_google(client))
    assert "/oauth/callback#" in resp.headers["location"]
    db.expire_all()
    user = db.get(User, seller_a.id)
    assert user is not None
    assert user.oauth_provider == "google" and user.is_verified
    assert user.hashed_password is None
    old_refresh = client.post(f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token})
    assert old_refresh.status_code == 401
    pw_login = client.post(
        f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD}
    )
    assert pw_login.status_code == 401


def test_google_login_into_verified_account_keeps_password(
    client: TestClient,
    db: Session,
    seller_a: Seller,
    google_configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = db.get(User, seller_a.id)
    assert user is not None
    user.is_verified = True
    db.commit()
    _fake_google(monkeypatch, {"email": seller_a.email, "email_verified": True})
    assert "/oauth/callback#" in _callback(client, _start_google(client)).headers["location"]
    assert (
        client.post(
            f"{API}/auth/login", json={"email": seller_a.email, "password": PASSWORD}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"{API}/auth/refresh", json={"refresh_token": seller_a.refresh_token}
        ).status_code
        == 200
    )


def test_google_callback_inactive_user_fails(
    client: TestClient,
    db: Session,
    seller_a: Seller,
    google_configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = db.get(User, seller_a.id)
    assert user is not None
    user.is_active = False
    db.commit()
    _fake_google(monkeypatch, {"email": seller_a.email, "email_verified": True})
    assert _callback(client, _start_google(client)).headers["location"].endswith(FAILED)


def test_google_callback_provider_error_redirects_to_failure(
    client: TestClient, google_configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_google(monkeypatch, oauth.OAuthError("boom"))
    assert _callback(client, _start_google(client)).headers["location"].endswith(FAILED)


# --- fetch_google_user against a mocked httpx transport (no network) ---


class _FakeResponse:
    def __init__(self, status_code: int, data: dict) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> dict:
        return self._data


class _FakeAsyncClient:
    """Stand-in for httpx.AsyncClient used by oauth.fetch_google_user."""

    token_resp = _FakeResponse(200, {"access_token": "at"})
    info_resp = _FakeResponse(200, {"email": "x@y.com", "email_verified": True})
    raise_exc: Exception | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> _FakeResponse:
        if self.raise_exc:
            raise self.raise_exc
        return self.token_resp

    async def get(self, *args: object, **kwargs: object) -> _FakeResponse:
        return self.info_resp


@pytest.fixture
def fake_httpx(monkeypatch: pytest.MonkeyPatch) -> type[_FakeAsyncClient]:
    class Fake(_FakeAsyncClient):
        pass

    monkeypatch.setattr(oauth.httpx, "AsyncClient", Fake)
    return Fake


async def _fetch() -> dict:
    return await oauth.fetch_google_user("code")


def test_fetch_google_user_success(fake_httpx: type[_FakeAsyncClient]) -> None:
    import asyncio

    assert asyncio.run(_fetch())["email"] == "x@y.com"


@pytest.mark.parametrize(
    "setup",
    [
        lambda f: setattr(f, "token_resp", _FakeResponse(400, {})),
        lambda f: setattr(f, "token_resp", _FakeResponse(200, {})),
        lambda f: setattr(f, "info_resp", _FakeResponse(500, {})),
        lambda f: setattr(f, "info_resp", _FakeResponse(200, {"email": "x@y.com"})),
        lambda f: setattr(f, "raise_exc", __import__("httpx").ConnectError("down")),
    ],
)
def test_fetch_google_user_failures(fake_httpx: type[_FakeAsyncClient], setup) -> None:
    import asyncio

    setup(fake_httpx)
    with pytest.raises(oauth.OAuthError):
        asyncio.run(_fetch())
