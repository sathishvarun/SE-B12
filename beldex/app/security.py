"""Password hashing (bcrypt) and login tokens (JWT)."""
from __future__ import annotations

from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import LoginSession, User, get_db, now

bearer = HTTPBearer(auto_error=False)


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def check_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def make_token(user: User, session_id: int) -> str:
    payload = {"sub": str(user.id), "role": user.role, "sid": session_id,
               "exp": now() + timedelta(hours=settings.jwt_hours)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


class Caller:
    def __init__(self, user: User, session: LoginSession | None):
        self.user, self.session = user, session


def current(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
            db: Session = Depends(get_db)) -> Caller:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in")
    try:
        data = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please sign in again")
    user = db.get(User, int(data["sub"]))
    if not user or not user.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is suspended")
    sess = db.get(LoginSession, int(data.get("sid", 0))) if data.get("sid") else None
    if sess and sess.ended_at:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "You signed out, please sign in again")
    if sess:  # heartbeat: every API call extends the measured time-in-app
        sess.last_seen = now()
        db.commit()
    return Caller(user, sess)


def admin_only(caller: Caller = Depends(current)) -> Caller:
    if caller.user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    return caller
