"""Stop password guessing: after 5 wrong passwords for one email (or 20 from one network) in 15 minutes, sign-in for
that email (or network) is blocked for 15 minutes. Counters live in Redis; if Redis is down, sign-in still works."""

import hashlib
import logging

import redis

from app.config import settings

logger = logging.getLogger(__name__)

WINDOW = 15 * 60
MAX_PER_EMAIL = 5
MAX_PER_IP = 20
_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1, socket_connect_timeout=1)
    return _client


def _keys(email: str, ip: str | None) -> tuple[str, str]:
    e = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]  # no plain emails in Redis
    return f"login-fail:e:{e}", f"login-fail:ip:{ip or '-'}"


def is_locked(email: str, ip: str | None) -> bool:
    ek, ik = _keys(email, ip)
    try:
        e, i = _redis().mget(ek, ik)
        return int(e or 0) >= MAX_PER_EMAIL or int(i or 0) >= MAX_PER_IP
    except redis.RedisError:
        logger.warning("Redis unavailable: sign-in lockout skipped")
        return False


def record_failure(email: str, ip: str | None) -> None:
    try:
        pipe = _redis().pipeline()
        for k in _keys(email, ip):
            pipe.incr(k)
            pipe.expire(k, WINDOW)
        pipe.execute()
    except redis.RedisError:
        pass


def clear(email: str) -> None:
    try:
        _redis().delete(_keys(email, None)[0])
    except redis.RedisError:
        pass
