"""Agencies: one login, several client restaurants.

PR and reputation agencies look after many restaurants. Each client stays its own restaurant (own data, own plan, own
billing); the agency's login is simply a member of each one. The app switches between them with the X-Org-Id header,
which `auth.deps.get_org_context` accepts only for restaurants the login belongs to.

- GET  /agency/restaurants   every client with this week's numbers and the reply promise, worst first
- POST /agency/restaurants   add a client restaurant (14-day trial, the agency login as its owner)
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, plan_lock
from app.database import get_db
from app.limiter import limiter
from app.models import AlertRule, Membership, Organization, Outlet, Review, Subscription, User
from app.services import activity, reply_promise
from app.services.auth_service import TRIAL_DAYS, _slugify

router = APIRouter(prefix="/api/v1/agency", tags=["agency"])
MAX_CLIENTS = 200


class ClientRow(BaseModel):
    id: int
    name: str
    city: str | None
    role: str
    plan: str
    trial_ends_at: datetime | None
    locked: bool
    outlets: int
    reviews_7d: int
    avg_rating_7d: float | None
    waiting: int
    overdue: int
    pct_within: float | None


class ClientPage(BaseModel):
    items: list[ClientRow]
    total: int
    waiting: int
    overdue: int


@router.get("/restaurants", response_model=ClientPage)
def clients(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ClientPage:
    """Every restaurant this login can open, the ones with overdue bad reviews first."""
    rows = db.execute(
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id, Organization.is_suspended.is_(False))
        .limit(MAX_CLIENTS)
    ).all()
    since = datetime.now(UTC) - timedelta(days=7)
    out = []
    for org, role in rows:
        n, avg = db.execute(
            select(func.count(Review.id), func.avg(Review.rating)).where(
                Review.organization_id == org.id, Review.created_at >= since
            )
        ).one()
        outlets = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == org.id, Outlet.is_active))
        p = reply_promise.stats(db, org, 7)
        out.append(
            ClientRow(
                id=org.id,
                name=org.name,
                city=org.city,
                role=role,
                plan=org.plan,
                trial_ends_at=org.trial_ends_at,
                locked=bool(plan_lock(db, org)),
                outlets=outlets or 0,
                reviews_7d=n or 0,
                avg_rating_7d=round(float(avg), 1) if avg is not None else None,
                waiting=p.waiting,
                overdue=p.overdue,
                pct_within=p.pct_within,
            )
        )
    out.sort(key=lambda r: (-r.overdue, -r.waiting, r.name.lower()))
    return ClientPage(
        items=out, total=len(out), waiting=sum(r.waiting for r in out), overdue=sum(r.overdue for r in out)
    )


class NewClient(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(default="", max_length=80)
    outlets: int | None = Field(default=None, ge=1, le=1000)


@router.post("/restaurants", response_model=ClientRow, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def add_client(
    request: Request, body: NewClient, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ClientRow:
    """A new client restaurant with its own 14-day trial; this login becomes its owner."""
    if user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins add restaurants from the Admin console.")
    count = db.scalar(select(func.count(Membership.id)).where(Membership.user_id == user.id)) or 0
    if count >= MAX_CLIENTS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"An agency login can hold up to {MAX_CLIENTS} restaurants.")
    name = body.name.strip()
    taken = db.scalar(
        select(Organization.id)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id, func.lower(Organization.name) == name.lower())
    )
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{name} is already one of your restaurants.")
    trial_end = datetime.now(UTC) + timedelta(days=TRIAL_DAYS)
    org = Organization(
        name=name,
        slug=_slugify(db, name),
        city=body.city.strip() or None,
        outlets_declared=body.outlets,
        plan="trial",
        trial_ends_at=trial_end,
        reply_signature=f"- Team {name}",
    )
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    db.add(Subscription(organization_id=org.id, plan="trial", status="trialing", current_period_end=trial_end))
    db.add(AlertRule(organization_id=org.id, recipients=[user.email], min_urgency="high"))
    db.add(Outlet(organization_id=org.id, name="Main outlet", city=org.city))
    activity.record(
        db,
        "signup",
        org_id=org.id,
        restaurant=org.name,
        email=user.email,
        detail=f"Client restaurant added by an agency login{f' in {org.city}' if org.city else ''}",
        commit=False,
    )
    db.commit()
    return ClientRow(
        id=org.id,
        name=org.name,
        city=org.city,
        role="owner",
        plan=org.plan,
        trial_ends_at=org.trial_ends_at,
        locked=False,
        outlets=1,
        reviews_7d=0,
        avg_rating_7d=None,
        waiting=0,
        overdue=0,
        pct_within=None,
    )
