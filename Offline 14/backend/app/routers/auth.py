"""Auth endpoints: /auth/* (register, login, tokens, profile, password reset, Google)."""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import oauth
from app.config import settings
from app.dependencies import get_current_user, get_db
from app.exceptions import AppError
from app.models import User
from app.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

OAUTH_FAILED_URL = "/login?error=oauth_failed"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create an account (with a free plan) and return tokens. 409 if email exists."""
    return auth_service.register(db, data, background_tasks)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Log in with email + password (JSON body)."""
    return auth_service.login(db, data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a refresh token for a new token pair (the old refresh token is revoked)."""
    return auth_service.refresh(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: RefreshRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Revoke the given refresh token."""
    auth_service.logout(db, user, data.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current user's profile."""
    return auth_service.to_user_response(user)


@router.put("/me", response_model=UserResponse)
def update_me(
    data: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update full_name and/or password."""
    updated = auth_service.update_profile(db, user, data)
    return auth_service.to_user_response(updated)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Email a password-reset link. Always returns the same message."""
    return MessageResponse(message=auth_service.forgot_password(db, data.email, background_tasks))


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """Set a new password with a reset token. 400 if the token is invalid or expired."""
    return MessageResponse(message=auth_service.reset_password(db, data.token, data.new_password))


@router.get("/google")
def google_login() -> RedirectResponse:
    """Redirect to Google's consent screen; the state nonce is also set as an HttpOnly cookie."""
    if not oauth.is_google_configured():
        logger.warning("Google OAuth requested but GOOGLE_CLIENT_ID/SECRET are not set")
        return RedirectResponse(f"{settings.FRONTEND_URL}{OAUTH_FAILED_URL}")
    state, nonce = oauth.create_state()
    response = RedirectResponse(oauth.build_authorization_url(state))
    response.set_cookie(
        oauth.STATE_COOKIE,
        nonce,
        max_age=oauth.STATE_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.GOOGLE_REDIRECT_URI.startswith("https://"),
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return response


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle Google's redirect: check state + cookie, log in or create the user, go to frontend."""
    failed = RedirectResponse(f"{settings.FRONTEND_URL}{OAUTH_FAILED_URL}")
    failed.delete_cookie(oauth.STATE_COOKIE, path="/api/v1/auth/google")
    if not code or not state or not oauth.verify_state(state, oauth_state):
        logger.warning("Google callback with missing code or invalid state")
        return failed

    try:
        userinfo = await oauth.fetch_google_user(code)
        tokens = auth_service.google_login(db, userinfo)
    except (oauth.OAuthError, AppError) as exc:
        logger.warning("Google login failed: %s", exc)
        return failed

    fragment = urlencode(
        {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token}
    )
    response = RedirectResponse(f"{settings.FRONTEND_URL}/oauth/callback#{fragment}")
    response.delete_cookie(oauth.STATE_COOKIE, path="/api/v1/auth/google")  # state is single-use
    return response
