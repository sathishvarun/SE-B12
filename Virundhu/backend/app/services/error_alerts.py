"""Tell the admin when something breaks, without waiting for a customer to complain.

A logging handler on the root logger: every ERROR (an unhandled exception in a request, a failed background job, a
failed payment sync) sends one plain email to the admin (NOTIFY_EMAIL, else SUPERADMIN_EMAIL). The same error is sent
at most once an hour (Redis key on a fingerprint of where it happened and what it was), and a burst stops after
ERROR_ALERTS_PER_HOUR emails. Off in tests and development unless ERROR_ALERTS is set.

Every error also counts in Redis per day, shown at Admin → Launch check.
"""

import hashlib
import logging
import threading
import traceback
from datetime import UTC, datetime

from app.config import settings

logger = logging.getLogger(__name__)
_local = threading.local()
SKIP = ("app.services.emailer", "app.services.error_alerts", "slowapi", "httpx", "httpcore")


def _redis():  # noqa: ANN202
    try:
        import redis

        return redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1, socket_connect_timeout=1)
    except Exception:
        return None


def fingerprint(record: logging.LogRecord) -> str:
    exc = record.exc_info[1] if record.exc_info else None
    where = f"{record.name}:{record.funcName}:{record.lineno}"
    what = type(exc).__name__ if exc else record.getMessage()[:120]
    return hashlib.sha256(f"{where}|{what}".encode()).hexdigest()[:16]


def _should_send(fp: str) -> bool:
    r = _redis()
    if r is None:
        return True
    try:
        day = datetime.now(UTC).strftime("%Y%m%d")
        r.incr(f"errors:{day}")
        r.expire(f"errors:{day}", 8 * 86400)
        if not r.set(f"erralert:{fp}", 1, nx=True, ex=3600):
            return False  # same error already reported this hour
        hour = datetime.now(UTC).strftime("%Y%m%d%H")
        n = r.incr(f"erralert-hour:{hour}")
        r.expire(f"erralert-hour:{hour}", 7200)
        return n <= settings.ERROR_ALERTS_PER_HOUR
    except Exception:
        return True


def errors_today() -> int | None:
    r = _redis()
    try:
        v = r.get(f"errors:{datetime.now(UTC).strftime('%Y%m%d')}") if r else None
        return int(v) if v else 0
    except Exception:
        return None


def _send(subject: str, body: str) -> None:
    _local.busy = True
    try:
        from app.services.emailer import send_email

        send_email([settings.notify_email], subject, body)
    except Exception:  # noqa: S110 - never let an alert break anything (and logging here would loop)
        pass
    finally:
        _local.busy = False


class ErrorAlertHandler(logging.Handler):
    """Emails the admin about new errors (deduplicated, rate limited, sent in the background)."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(_local, "busy", False) or record.name.startswith(SKIP):
            return
        try:
            fp = fingerprint(record)
            if not _should_send(fp):
                return
            tb = "".join(traceback.format_exception(*record.exc_info))[-4000:] if record.exc_info else ""
            subject = f"[Virundhu {settings.APP_ENV}] Error: {record.getMessage()[:90]}"
            body = (
                f"Something failed on {settings.APP_URL} at {datetime.now(UTC):%Y-%m-%d %H:%M} UTC.\n\n"
                f"Where: {record.name} ({record.pathname.split('/app/')[-1]}:{record.lineno})\n"
                f"Message: {record.getMessage()[:1000]}\n\n{tb}\n"
                "The same error won't be emailed again for an hour. Server logs: backend/logs/virundhu.log\n"
            )
            threading.Thread(target=_send, args=(subject, body), daemon=True).start()
        except Exception:  # noqa: S110 - a logging handler must never raise
            pass


def install() -> None:
    """Attach the handler once (API and worker both call this at start-up)."""
    if not settings.ERROR_ALERTS:
        return
    root = logging.getLogger()
    if not any(isinstance(h, ErrorAlertHandler) for h in root.handlers):
        root.addHandler(ErrorAlertHandler())
