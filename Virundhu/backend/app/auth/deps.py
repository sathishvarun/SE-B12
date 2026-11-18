"""FastAPI dependencies: current user, current organization membership, role checks."""

from dataclasses import dataclass
from datetime import UTC, datetime

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models import Membership, Organization, Subscription, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    """Resolve the signed-in user from the Bearer token, or 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please sign in again.") from exc
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account is not active.")
    return user


@dataclass
class OrgContext:
    """The user plus the organization they are working in."""

    user: User
    org: Organization
    role: str
    outlet_ids: list[int] | None = None  # None = all outlets

    def can_see_outlet(self, outlet_id: int | None) -> bool:
        return self.outlet_ids is None or (outlet_id is not None and outlet_id in self.outlet_ids)


def get_org_context(
    user: User = Depends(get_current_user), db: Session = Depends(get_db), x_org_id: int | None = Header(default=None)
) -> OrgContext:
    """The restaurant the user works in. Super admins may open any restaurant with the X-Org-Id header."""
    if x_org_id and user.is_superadmin:
        org = db.get(Organization, x_org_id)
        if org is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found.")
        return OrgContext(user=user, org=org, role="owner")
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id).order_by(Membership.id))
    if membership is None:
        if user.is_superadmin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Admins work in the Admin console. Open a restaurant from there."
            )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your account is not linked to a restaurant yet.")
    org = db.get(Organization, membership.organization_id)
    if org is None or org.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This restaurant account is suspended.")
    scope = None if membership.role == "owner" else (membership.outlet_ids or None)
    return OrgContext(user=user, org=org, role=membership.role, outlet_ids=scope)


def require_writable(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
    """Block changes in the read-only demo, and after a free trial has ended (until a plan is chosen)."""
    if ctx.user.is_superadmin:
        return ctx
    if (
        ctx.org.plan == "trial"
        and ctx.org.trial_ends_at
        and ctx.org.trial_ends_at < datetime.now(UTC)
        and not ctx.org.is_demo
    ):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Your free trial has ended. Choose a plan to keep adding and replying to reviews.",
        )
    if ctx.org.plan != "trial" and not ctx.org.is_demo:
        db = object_session(ctx.org)
        sub = db.scalar(select(Subscription).where(Subscription.organization_id == ctx.org.id)) if db else None
        if sub and sub.current_period_end and sub.current_period_end < datetime.now(UTC):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                "Your plan has run out. Renew it on the Plan and billing page to keep adding and replying to reviews.",
            )
    if ctx.org.is_demo:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "The demo restaurant is read-only. Start a free trial to try this."
        )
    return ctx


def require_owner(ctx: OrgContext = Depends(require_writable)) -> OrgContext:
    """Only owners (and super admins) manage the team and restaurant settings."""
    if ctx.role != "owner" and not ctx.user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the restaurant owner can change this.")
    return ctx


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """Platform owner only."""
    if not user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only.")
    return user
