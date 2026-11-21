"""Admin: every restaurant's reply-promise score, and every branch with its Google Maps link."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.database import get_db
from app.models import Organization, Outlet, Review
from app.services import maps, reply_promise

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_superadmin)])


class PromiseRow(BaseModel):
    org_id: int
    name: str
    plan: str
    target_minutes: int
    reminders_on: bool
    bad: int
    within: int
    pct_within: float | None
    median_minutes: int | None
    waiting: int
    overdue: int


@router.get("/reply-promise", response_model=list[PromiseRow])
def promise_league(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)) -> list[PromiseRow]:
    """Restaurants with bad reviews in the period, slowest first (the ones to call)."""
    since = datetime.now(UTC) - timedelta(days=days + 30)
    org_ids = db.scalars(select(Review.organization_id).where(Review.created_at >= since).distinct()).all()
    rows = []
    for org in db.scalars(select(Organization).where(Organization.id.in_(org_ids))):
        s = reply_promise.stats(db, org, days)
        if not s.bad and not s.waiting:
            continue
        rows.append(
            PromiseRow(
                org_id=org.id,
                name=org.name,
                plan=org.plan,
                target_minutes=s.target_minutes,
                reminders_on=s.reminders_on,
                bad=s.bad,
                within=s.within,
                pct_within=s.pct_within,
                median_minutes=s.median_minutes,
                waiting=s.waiting,
                overdue=s.overdue,
            )
        )
    return sorted(rows, key=lambda r: (r.pct_within if r.pct_within is not None else 101, -r.overdue))


class BranchRow(BaseModel):
    id: int
    org_id: int
    restaurant: str
    name: str
    area: str | None
    city: str | None
    district: str | None
    address: str | None
    phone: str | None
    google_rating: float | None
    google_rating_count: int | None
    on_google_maps: bool
    directions_url: str | None
    map_embed_url: str | None


class BranchPage(BaseModel):
    items: list[BranchRow]
    total: int
    with_map: int
    cities: list[tuple[str, int]]


@router.get("/branches", response_model=BranchPage)
def branches(
    q: str | None = Query(default=None, max_length=100),
    city: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> BranchPage:
    """Every active branch of every restaurant, with free Google Maps links."""
    base = (
        select(Outlet, Organization.name)
        .join(Organization, Organization.id == Outlet.organization_id)
        .where(Outlet.is_active.is_(True), Organization.is_demo.is_(False))
    )
    if q:
        like = f"%{q}%"
        base = base.where(
            Outlet.name.ilike(like) | Organization.name.ilike(like) | Outlet.area.ilike(like) | Outlet.city.ilike(like)
        )
    if city:
        base = base.where(func.lower(Outlet.city) == city.lower())
    rows = db.execute(base.order_by(Organization.name, Outlet.name)).all()
    cities = db.execute(
        select(Outlet.city, func.count(Outlet.id))
        .join(Organization, Organization.id == Outlet.organization_id)
        .where(Outlet.is_active.is_(True), Organization.is_demo.is_(False), Outlet.city.is_not(None))
        .group_by(Outlet.city)
        .order_by(func.count(Outlet.id).desc())
        .limit(20)
    ).all()
    items = [
        BranchRow(
            id=o.id,
            org_id=o.organization_id,
            restaurant=org_name,
            name=o.name,
            area=o.area,
            city=o.city,
            district=o.district,
            address=o.address,
            phone=o.phone,
            google_rating=float(o.google_rating) if o.google_rating is not None else None,
            google_rating_count=o.google_rating_count,
            on_google_maps=maps.on_google_maps(o),
            directions_url=maps.directions_url(o),
            map_embed_url=maps.embed_url(o),
        )
        for o, org_name in rows
    ]
    return BranchPage(
        items=items[:limit],
        total=len(items),
        with_map=sum(1 for i in items if i.directions_url),
        cities=[(c, n) for c, n in cities],
    )
