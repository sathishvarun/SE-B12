"""Authentication business logic: register, login, tokens, profile, password reset, Google."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.config import settings
from app.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.models import (
    PasswordResetToken,
    RefreshToken,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)
from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.email import render_template, send_email

logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRE_HOURS = 1
FORGOT_PASSWORD_MESSAGE = "If that email exists, a reset link has been sent."
RESET_PASSWORD_MESSAGE = "Password updated."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes (e.g. from SQLite) as UTC so comparisons work."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email (case-insensitive, emails are stored lowercase)."""
    return db.scalar(select(User).where(User.email == _normalize_email(email)))


def to_user_response(user: User) -> UserResponse:
    """Build the API representation of a user, including plan and has_password."""
    plan = user.subscription.plan if user.subscription else SubscriptionPlan.FREE
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        oauth_provider="google" if user.oauth_provider == "google" else None,
        has_password=user.hashed_password is not None,
        plan=plan,
        created_at=user.created_at,
    )


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    """Create an access token and a new stored (hashed) refresh token. Commits."""
    raw_refresh = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=hash_token(raw_refresh),
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=raw_refresh)


def _create_free_subscription(db: Session, user: User) -> None:
    """Attach a free, active subscription to a user who doesn't have one yet."""
    if user.subscription is None:
        user.subscription = Subscription(
            plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE
        )


def _revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    """Revoke every active refresh token of a user (e.g. after a password reset)."""
    tokens = db.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    )
    for token in tokens:
        token.revoked = True


def _send_welcome_email(email: str, user_name: str | None) -> None:
    send_email(
        email,
        "Welcome to Sathish CRM",
        render_template("welcome.html", user_name=user_name),
    )


def _send_reset_email(email: str, user_name: str | None, raw_token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?{urlencode({'token': raw_token})}"
    send_email(
        email,
        "Reset your Sathish CRM password",
        render_template("password_reset.html", user_name=user_name, reset_url=reset_url),
    )


# ---------------------------------------------------------------------------
# Register / login / tokens
# ---------------------------------------------------------------------------


def register(
    db: Session, data: RegisterRequest, background_tasks: BackgroundTasks
) -> TokenResponse:
    """Create a user with a free subscription, queue a welcome email, return tokens.

    Raises ConflictError (409) if the email is already registered.
    """
    email = _normalize_email(data.email)
    if get_user_by_email(db, email) is not None:
        raise ConflictError("Email is already registered")

    user = User(
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )
    _create_free_subscription(db, user)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # two sign-ups with the same email at once
        db.rollback()
        raise ConflictError("Email is already registered") from exc
    logger.info("Registered user id=%s", user.id)

    tokens = _issue_tokens(db, user)
    background_tasks.add_task(_send_welcome_email, user.email, user.full_name)
    return tokens


_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def login(db: Session, email: str, password: str) -> TokenResponse:
    """Check credentials and return tokens. 401 on bad credentials, 403 if inactive."""
    user = get_user_by_email(db, email)
    if user is None or user.hashed_password is None:
        verify_password(password, _DUMMY_HASH)  # same timing as a real check (no user enumeration)
        raise UnauthorizedError("Incorrect email or password")
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return _issue_tokens(db, user)


def refresh(db: Session, raw_token: str) -> TokenResponse:
    """Rotate a refresh token: revoke the old one and issue a new pair.

    Raises UnauthorizedError (401) if the token is unknown, revoked or expired.
    """
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token == hash_token(raw_token)))
    if stored is None or stored.revoked or _as_utc(stored.expires_at) <= _now():
        raise UnauthorizedError("Invalid or expired refresh token")

    user = db.get(User, stored.user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired refresh token")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")

    stored.revoked = True
    return _issue_tokens(db, user)


def logout(db: Session, user: User, raw_token: str) -> None:
    """Revoke the given refresh token if it belongs to the user (silently ignores others)."""
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token == hash_token(raw_token), RefreshToken.user_id == user.id
        )
    )
    if stored is not None and not stored.revoked:
        stored.revoked = True
        db.commit()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> User:
    """Update full_name and/or password.

    Changing the password requires current_password, unless the user has no
    password yet (Google-only account).
    """
    if data.full_name is not None:
        user.full_name = data.full_name.strip()

    if data.new_password is not None:
        if user.hashed_password is not None:
            if not data.current_password or not verify_password(
                data.current_password, user.hashed_password
            ):
                raise BadRequestError("Current password is incorrect")
        user.hashed_password = hash_password(data.new_password)
        _revoke_all_refresh_tokens(db, user.id)  # a stolen refresh token stops working
        logger.info("Password changed for user id=%s", user.id)

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def forgot_password(db: Session, email: str, background_tasks: BackgroundTasks) -> str:
    """Create a 1-hour reset token and email the link. Same message for unknown emails."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        logger.info("Password reset requested for unknown/inactive email")
        return FORGOT_PASSWORD_MESSAGE

    # Invalidate older unused tokens so only the newest link works.
    for old in db.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False)
        )
    ):
        old.used = True

    raw_token = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=_now() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS),
        )
    )
    db.commit()
    background_tasks.add_task(_send_reset_email, user.email, user.full_name, raw_token)
    return FORGOT_PASSWORD_MESSAGE


def reset_password(db: Session, raw_token: str, new_password: str) -> str:
    """Set a new password using a valid reset token (single use). 400 if invalid/expired."""
    stored = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw_token))
    )
    if stored is None or stored.used or _as_utc(stored.expires_at) <= _now():
        raise BadRequestError("Invalid or expired reset token")

    user = db.get(User, stored.user_id)
    if user is None:
        raise BadRequestError("Invalid or expired reset token")

    user.hashed_password = hash_password(new_password)
    stored.used = True
    _revoke_all_refresh_tokens(db, user.id)  # log out other sessions
    db.commit()
    logger.info("Password reset for user id=%s", user.id)
    return RESET_PASSWORD_MESSAGE


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


def google_login(db: Session, userinfo: dict[str, Any]) -> TokenResponse:
    """Log in with a verified Google profile: link an existing user or create a new one.

    Raises ForbiddenError if the matching account is deactivated.
    """
    email = _normalize_email(str(userinfo["email"]))
    user = get_user_by_email(db, email)

    if user is None:
        name = userinfo.get("name")
        user = User(
            email=email,
            hashed_password=None,
            full_name=str(name) if name else None,
            is_verified=True,
            oauth_provider="google",
        )
        _create_free_subscription(db, user)
        db.add(user)
        db.flush()
        logger.info("Created user id=%s via Google", user.id)
    else:
        if not user.is_active:
            raise ForbiddenError("Account is deactivated")
        if not user.is_verified:
            # Nobody proved they own this email when the password was set, so the
            # password may belong to someone else (account pre-hijack). Drop it and
            # end every existing session; the owner can set a new one in Settings.
            user.hashed_password = None
            _revoke_all_refresh_tokens(db, user.id)
        if user.oauth_provider is None:
            user.oauth_provider = "google"
            logger.info("Linked Google account to user id=%s", user.id)
        user.is_verified = True
        _create_free_subscription(db, user)

    return _issue_tokens(db, user)
