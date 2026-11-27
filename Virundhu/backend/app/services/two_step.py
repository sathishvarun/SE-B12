"""Two-step sign-in: password plus a 6-digit code from an authenticator app (Google Authenticator, Microsoft
Authenticator, Authy). Any account can switch it on; the admin console asks the admin to.

- The secret is stored encrypted; while the QR code is being scanned it waits in `totp_pending`.
- A code is accepted once (`totp_last_step` stops replays), one 30-second step either side for clock drift.
- 8 recovery codes, each usable once, are shown when it is switched on; only their hashes are kept.
"""

import base64
import hashlib
import io
import secrets
from datetime import UTC, datetime

import pyotp
import segno
from fastapi import HTTPException, status

from app.config import settings
from app.models import User
from app.services.crypto import decrypt, encrypt

ISSUER = "Virundhu"


def enabled(user: User) -> bool:
    return bool(user.totp_enabled_at and user.totp_secret)


def _hash(code: str) -> str:
    return hashlib.sha256(("recovery:" + code.replace("-", "").strip().lower()).encode()).hexdigest()


def start(user: User) -> dict:
    """A fresh secret for the user to scan. Nothing changes until they confirm with a code."""
    secret = pyotp.random_base32()
    user.totp_pending = encrypt(secret)
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER)
    buf = io.BytesIO()
    segno.make(uri, error="m").save(buf, kind="svg", scale=5, dark="#0c3b2e", light="#ffffff", xmldecl=False)
    svg = buf.getvalue().decode()
    return {
        "otpauth_uri": uri,
        "secret": secret,  # for typing in by hand when the camera can't scan
        "qr_svg_base64": base64.b64encode(svg.encode()).decode(),
    }


def _step_ok(user: User, secret: str, code: str) -> bool:
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(secret)
    now = datetime.now(UTC)
    for drift in (-1, 0, 1):
        when = now.timestamp() + drift * totp.interval
        step = int(when // totp.interval)
        if user.totp_last_step and step <= user.totp_last_step:
            continue  # already used: a code works once
        if secrets.compare_digest(totp.at(when), code):
            user.totp_last_step = step
            return True
    return False


def confirm(user: User, code: str) -> list[str]:
    """Switch it on after the first good code. Returns the recovery codes (shown once)."""
    secret = decrypt(user.totp_pending or "")
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Start again: open the set-up and scan the new QR code.")
    user.totp_last_step = None
    if not _step_ok(user, secret, code):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That code didn't match. Check the phone's time and try the newest code."
        )
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(8)]
    user.totp_secret, user.totp_pending = encrypt(secret), None
    user.totp_enabled_at = datetime.now(UTC)
    user.totp_recovery = [_hash(c) for c in codes]
    return codes


def check(user: User, code: str | None) -> bool:
    """A 6-digit code or an unused recovery code. Recovery codes are used up."""
    if not code:
        return False
    secret = decrypt(user.totp_secret or "")
    if secret and _step_ok(user, secret, code):
        return True
    h = _hash(code)
    left = list(user.totp_recovery or [])
    if h in left:
        left.remove(h)
        user.totp_recovery = left
        return True
    return False


def disable(user: User) -> None:
    user.totp_secret = user.totp_pending = None
    user.totp_enabled_at = None
    user.totp_recovery = None
    user.totp_last_step = None


def required_for(user: User) -> bool:
    """The admin console nags until the admin switches it on (ADMIN_REQUIRE_TWO_STEP makes it compulsory)."""
    return bool(user.is_superadmin and settings.ADMIN_REQUIRE_TWO_STEP and not enabled(user))
