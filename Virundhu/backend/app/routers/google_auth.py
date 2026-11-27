"""Sign in with Google (OAuth 2.0). Works as soon as GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are in .env."""

import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.cookies import set_refresh_cookie, to_cookie
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.schemas.auth import RegisterIn, TokenOut
from app.services import auth_service, google_reviews, two_step

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth/google", tags=["auth"])
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - URL, not a secret
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_jwks = jwt.PyJWKClient(CERTS_URL, cache_keys=True, lifespan=3600)


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
    tokens = _sign_in(db, request, email, info.get("name"))
    if tokens is None:
        return RedirectResponse(fail)
    frag = urlencode({"access": tokens.access_token})
    out = RedirectResponse(f"{settings.APP_URL}/auth/callback#{frag}")
    if tokens.refresh_token:
        set_refresh_cookie(out, tokens.refresh_token)
    return out


def _sign_in(db: Session, request: Request, email: str, name: str | None):
    """Sign in a Google-verified email, creating the account and 14-day trial if it's new. None if blocked."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        name = name or email.split("@")[0]
        return auth_service.register(
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
    if not user.is_active:
        return None
    if two_step.enabled(user):  # Google can't ask for the code: these accounts sign in with password + code
        return None
    auth_service.record_sign_in(
        db, user, request.client.host if request.client else None, request.headers.get("user-agent"), how="Google"
    )
    return auth_service.issue_tokens(db, user)


class IdTokenIn(BaseModel):
    credential: str = Field(min_length=20, max_length=5000)


@router.post("/id-token", response_model=TokenOut, response_model_exclude_none=True)
@limiter.limit("20/minute")
def id_token_sign_in(request: Request, response: Response, body: IdTokenIn, db: Session = Depends(get_db)) -> TokenOut:
    """'Sign in with Google' button: Google gives the browser a signed ID token; we check it with Google's public keys.

    Needs only GOOGLE_CLIENT_ID (no client secret).
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google sign-in isn't set up yet.")
    try:
        key = _jwks.get_signing_key_from_jwt(body.credential).key
        claims = jwt.decode(
            body.credential,
            key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            issuer=["accounts.google.com", "https://accounts.google.com"],
        )
    except Exception as exc:
        logger.info("Google ID token rejected: %s", type(exc).__name__)
        raise HTTPException(401, "Google sign-in didn't work. Please try again.") from None
    email = str(claims.get("email", "")).lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(401, "Your Google email isn't verified.")
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None and two_step.enabled(existing):
        raise HTTPException(403, "This account uses two-step sign-in. Sign in with your email, password and code.")
    tokens = _sign_in(db, request, email, claims.get("name"))
    if tokens is None:
        raise HTTPException(403, "This account is switched off. Please contact us.")
    return to_cookie(response, tokens)
