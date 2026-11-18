"""Sign-up, sign-in and token rotation."""

import logging
import re
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import lockout
from app.auth.deps import plan_lock
from app.auth.passwords import weak_reason
from app.auth.security import create_access_token, hash_password, hash_token, new_opaque_token, verify_password
from app.config import settings
from app.models import AlertRule, Membership, Organization, Outlet, RefreshToken, Subscription, User
from app.schemas.auth import MeOut, OrgOut, RegisterIn, TokenOut
from app.services import activity

TRIAL_DAYS = 14


def _slugify(db: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:120] or "restaurant"
    slug, n = base, 2
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def build_me(db: Session, user: User) -> MeOut:
    """Profile + organization + role + outlet access for the frontend. Admins have no restaurant."""
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.id))
    org = db.get(Organization, membership.organization_id) if membership else None
    outlet_names = None
    if membership and membership.role != "owner" and membership.outlet_ids:
        outlet_names = list(db.scalars(select(Outlet.name).where(Outlet.id.in_(membership.outlet_ids))))
    return MeOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_superadmin=user.is_superadmin,
        role=membership.role if membership else None,
        outlet_names=outlet_names,
        organization=OrgOut(
            id=org.id,
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            is_demo=org.is_demo,
            city=org.city,
            trial_ends_at=org.trial_ends_at,
            is_suspended=org.is_suspended,
            locked_since=plan_lock(db, org),
        )
        if org
        else None,
    )


def issue_tokens(db: Session, user: User) -> TokenOut:
    """New access token + new refresh token (only its hash is stored)."""
    refresh, digest = new_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id), refresh_token=refresh, user=build_me(db, user))


def register(
    db: Session, data: RegisterIn, hashed_password: str | None = "", oauth_provider: str | None = None
) -> TokenOut:
    """Create user + organization + owner membership + 14-day trial in one transaction."""
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists. Try signing in.")
    trial_end = datetime.now(UTC) + timedelta(days=TRIAL_DAYS)
    if hashed_password == "":
        problem = weak_reason(data.password, data.email, data.full_name, data.organization_name)
        if problem:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    pw_hash = hash_password(data.password) if hashed_password == "" else hashed_password
    user = User(
        email=email,
        hashed_password=pw_hash,
        full_name=data.full_name.strip(),
        oauth_provider=oauth_provider,
        is_verified=oauth_provider is not None,
        terms_accepted_at=datetime.now(UTC),  # email sign-up ticks the box; Google sign-up shows the same notice
    )
    org = Organization(
        name=data.organization_name.strip(),
        slug=_slugify(db, data.organization_name),
        city=data.city,
        owner_phone=(getattr(data, "phone", None) or "").strip() or None,
        outlets_declared=getattr(data, "outlets", None),
        plan="trial",
        trial_ends_at=trial_end,
        reply_signature=f"- Team {data.organization_name.strip()}",
    )
    db.add_all([user, org])
    db.flush()
    db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    db.add(Subscription(organization_id=org.id, plan="trial", status="trialing", current_period_end=trial_end))
    db.add(AlertRule(organization_id=org.id, recipients=[email], min_urgency="high"))
    activity.record(
        db,
        "signup",
        org_id=org.id,
        restaurant=org.name,
        email=email,
        detail=f"Free trial{f' in {org.city}' if org.city else ''}{' (Google sign-in)' if oauth_provider else ''}",
        commit=False,
    )
    tokens = issue_tokens(db, user)
    try:
        from app.services.welcome import send_welcome

        send_welcome(user, org, phone=org.owner_phone, outlets=org.outlets_declared)
    except Exception:  # an email problem must never block sign-up
        logging.getLogger(__name__).exception("Welcome email failed for user %s", user.id)
    return tokens


_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def _org_of(db: Session, user: User | None) -> tuple[int | None, str | None]:
    if user is None:
        return None, None
    m = db.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.id))
    org = db.get(Organization, m.organization_id) if m else None
    return (org.id, org.name) if org else (None, None)


def record_sign_in(db: Session, user: User, ip: str | None, device: str | None, how: str = "password") -> None:
    org_id, name = _org_of(db, user)
    role = "admin" if user.is_superadmin else "owner/team"
    activity.record(
        db,
        "login",
        org_id=org_id,
        restaurant=name,
        email=user.email,
        detail=f"{how} sign-in as {role}; IP {ip or '-'}; {(device or '-')[:120]}",
    )


def login(db: Session, email: str, password: str, ip: str | None = None, device: str | None = None) -> TokenOut:
    """Check the password and issue tokens.

    Same message and the same time for an unknown email and a wrong password, so nobody can find out which emails have
    accounts. After 5 wrong passwords the email is locked for 15 minutes (see auth/lockout.py).
    """
    if lockout.is_locked(email, ip):
        activity.record(db, "login_failed", email=email.lower()[:255], detail=f"Blocked while locked; IP {ip or '-'}")
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many wrong passwords. For your safety, sign-in is paused for 15 minutes, or reset your password.",
        )
    user = db.scalar(select(User).where(User.email == email.lower()))
    ok = verify_password(password, user.hashed_password if user and user.hashed_password else _DUMMY_HASH)
    if user is None or not user.hashed_password or not ok:
        lockout.record_failure(email, ip)
        org_id, name = _org_of(db, user)
        known = "known account" if user else "no such account"
        activity.record(
            db,
            "login_failed",
            org_id=org_id,
            restaurant=name,
            email=email.lower()[:255],
            detail=f"Wrong password ({known}); IP {ip or '-'}; {(device or '-')[:120]}",
        )
        if lockout.is_locked(email, ip):
            activity.record(
                db,
                "login_locked",
                org_id=org_id,
                restaurant=name,
                email=email.lower()[:255],
                detail=f"Locked for 15 minutes after repeated wrong passwords; IP {ip or '-'}",
            )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That email and password don't match.")
    lockout.clear(email)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been switched off. Contact support.")
    record_sign_in(db, user, ip, device)
    return issue_tokens(db, user)


def refresh(db: Session, token: str) -> TokenOut:
    """Rotate the refresh token: the old one is revoked, a new pair is issued."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    now = datetime.now(UTC)
    # Two tabs (or a page load and a request) may refresh with the same token at the same moment: allow that for
    # 30 seconds after it was swapped. Older reuse means the token was copied or stolen, so it's refused.
    just_swapped = row is not None and row.revoked and row.updated_at > now - timedelta(seconds=30)
    if row is None or (row.revoked and not just_swapped) or row.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.")
    row.revoked = True
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account is not active.")
    return issue_tokens(db, user)


def logout(db: Session, token: str) -> None:
    """Revoke a refresh token (idempotent)."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(token)))
    if row:
        row.revoked = True
        row.expires_at = datetime.now(UTC)  # dead at once: no grace period after signing out
        db.commit()
