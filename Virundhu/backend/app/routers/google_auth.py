"""Sign in with Google (OAuth 2.0). Works as soon as GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are in .env."""

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.cookies import set_refresh_cookie
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import RegisterIn
from app.services import auth_service, google_reviews

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth/google", tags=["auth"])
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - URL, not a secret
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _state() -> str:
    return jwt.encode(
        {"purpose": "google", "exp": datetime.now(UTC) + timedelta(minutes=10)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


@router.get("")
def start() -> RedirectResponse:
    """Send the visitor to Google's sign-in page."""
    if not settings.google_enabled:
        raise HTTPException(503, "Google sign-in isn't set up yet.")
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": _state(),
        "prompt": "select_account",
    }
    return RedirectResponse(f"{AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Google sends the visitor back here. We sign them in (creating an account and trial if new)."""
    fail = f"{settings.APP_URL}/login?error=google"
    if error or not code or not state:
        return RedirectResponse(fail)
    try:
        claims = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return RedirectResponse(fail)
    if claims.get("purpose") == "connect":  # owner connecting their Google Business Profile
        back = f"{settings.APP_URL}/app/connections"
        try:
            google_reviews.finish_connect(db, int(claims["org"]), code)
        except google_reviews.GoogleError as exc:
            return RedirectResponse(f"{back}?google=error&reason={quote(str(exc))}")
        except Exception:
            logger.exception("Google connect failed")
            return RedirectResponse(f"{back}?google=error")
        return RedirectResponse(f"{back}?google=connected")
    try:
        token = httpx.post(
            TOKEN_URL,
            timeout=15,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        ).json()
        info = httpx.get(USERINFO_URL, timeout=15, headers={"Authorization": f"Bearer {token['access_token']}"}).json()
    except Exception:
        logger.exception("Google sign-in failed")
        return RedirectResponse(fail)
    email = str(info.get("email", "")).lower()
    if not email or not info.get("email_verified"):
        return RedirectResponse(fail)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        name = info.get("name") or email.split("@")[0]
        tokens = auth_service.register(
            db,
            RegisterIn.model_construct(
                full_name=name,
                organization_name=f"{name.split(' ')[0]}'s restaurant",
                city=None,
                email=email,
                password="",
            ),
            hashed_password=None,
            oauth_provider="google",
        )
    else:
        if not user.is_active:
            return RedirectResponse(fail)
        auth_service.record_sign_in(
            db, user, request.client.host if request.client else None, request.headers.get("user-agent"), how="Google"
        )
        tokens = auth_service.issue_tokens(db, user)
    frag = urlencode({"access": tokens.access_token})
    out = RedirectResponse(f"{settings.APP_URL}/auth/callback#{frag}")
    if tokens.refresh_token:
        set_refresh_cookie(out, tokens.refresh_token)
    return out
