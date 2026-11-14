"""Pure security helpers: password hashing, JWT access tokens, refresh tokens."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings


def _password_bytes(password: str) -> bytes:
    """bcrypt only uses the first 72 bytes; cut explicitly so every bcrypt version agrees."""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the plain password."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("utf-8"))
    except ValueError:  # malformed hash in the database
        return False


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token with `sub` = subject (usually the user id)."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate an access token. Returns the payload, or None if invalid/expired."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except InvalidTokenError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def create_refresh_token() -> str:
    """Create an opaque random refresh token (store only its hash in the DB)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Return the sha256 hex digest of a token, for storing refresh/reset tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
