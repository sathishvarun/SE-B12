"""Shared FastAPI dependencies: DB session, current user, current admin."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models import User

__all__ = ["get_db", "get_current_user", "get_current_admin", "oauth2_scheme"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the user for a valid Bearer access token.

    Raises 401 if the token is invalid/expired or the user no longer exists,
    and 403 if the account has been deactivated.
    """
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token") from exc

    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Return the current user if they are an admin, else raise 403."""
    if not user.is_admin:
        raise ForbiddenError("Admin access required")
    return user
