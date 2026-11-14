"""Google OAuth 2.0 helpers.

The ``state`` parameter is a short-lived JWT signed with SECRET_KEY. It carries a
random nonce that is also stored in an HttpOnly cookie, so the callback only
succeeds in the same browser that started the login (prevents login CSRF).
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

STATE_TYPE = "oauth_state"
STATE_EXPIRE_MINUTES = 10
STATE_COOKIE = "oauth_state"


class OAuthError(Exception):
    """Raised when any step of the Google OAuth flow fails."""


def is_google_configured() -> bool:
    """Return True if Google OAuth client credentials are set."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def create_state() -> tuple[str, str]:
    """Create a signed 10-minute `state`. Returns (state, nonce); the nonce goes in a cookie."""
    nonce = secrets.token_urlsafe(16)
    expire = datetime.now(UTC) + timedelta(minutes=STATE_EXPIRE_MINUTES)
    payload = {"type": STATE_TYPE, "nonce": nonce, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM), nonce


def verify_state(state: str, cookie_nonce: str | None) -> bool:
    """Return True if `state` is valid, unexpired and its nonce matches the browser's cookie."""
    if not cookie_nonce:
        return False
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError:
        return False
    nonce = payload.get("nonce")
    return (
        payload.get("type") == STATE_TYPE
        and isinstance(nonce, str)
        and secrets.compare_digest(nonce, cookie_nonce)
    )


def build_authorization_url(state: str) -> str:
    """Build the Google consent-screen URL for the given signed state."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def fetch_google_user(code: str) -> dict[str, Any]:
    """Exchange an authorization code for tokens, then return Google's userinfo.

    Raises OAuthError if the exchange fails or the email is missing/unverified.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                },
            )
            if token_resp.status_code != 200:
                raise OAuthError(f"Token exchange failed ({token_resp.status_code})")
            access_token = token_resp.json().get("access_token")
            if not access_token:
                raise OAuthError("No access_token in Google response")

            info_resp = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            if info_resp.status_code != 200:
                raise OAuthError(f"Userinfo request failed ({info_resp.status_code})")
            userinfo: dict[str, Any] = info_resp.json()
    except httpx.HTTPError as exc:
        raise OAuthError(f"HTTP error talking to Google: {exc}") from exc

    if not userinfo.get("email") or not userinfo.get("email_verified"):
        raise OAuthError("Google account has no verified email")
    return userinfo
