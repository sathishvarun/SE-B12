"""Link outlets to their Google Maps listings and pull Google reviews (Places API, no approval needed)."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_writable
from app.database import get_db
from app.limiter import limiter
from app.models import Outlet
from app.services import google_places
from app.services.queue import enqueue_analysis

router = APIRouter(prefix="/api/v1", tags=["google-places"])


class OutletPlace(BaseModel):
    outlet_id: int
    outlet: str
    place_id: str | None
    place_name: str | None
    rating: float | None
    rating_count: int | None
    synced_at: str | None
    error: str | None


class PlacesStatus(BaseModel):
    enabled: bool
    full_sync_connected: bool
    outlets: list[OutletPlace]


def _row(o: Outlet) -> OutletPlace:
    return OutletPlace(
        outlet_id=o.id,
        outlet=o.name,
        place_id=o.google_place_id,
        place_name=o.google_place_name,
        rating=float(o.google_rating) if o.google_rating is not None else None,
        rating_count=o.google_rating_count,
        synced_at=o.google_synced_at.isoformat() if o.google_synced_at else None,
        error=o.google_sync_error,
    )


def _outlet(db: Session, ctx: OrgContext, outlet_id: int) -> Outlet:
    if ctx.outlet_ids is not None and outlet_id not in ctx.outlet_ids:
        raise HTTPException(404, "Outlet not found.")
    o = db.scalar(
        select(Outlet).where(Outlet.id == outlet_id, Outlet.organization_id == ctx.org.id, Outlet.is_active.is_(True))
    )
    if o is None:
        raise HTTPException(404, "Outlet not found.")
    return o


@router.get("/places/status", response_model=PlacesStatus)
def status(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> PlacesStatus:
    q = select(Outlet).where(Outlet.organization_id == ctx.org.id, Outlet.is_active.is_(True)).order_by(Outlet.id)
    if ctx.outlet_ids is not None:
        q = q.where(Outlet.id.in_(ctx.outlet_ids))
    return PlacesStatus(
        enabled=google_places.enabled(),
        full_sync_connected=google_places.full_sync_connected(db, ctx.org.id),
        outlets=[_row(o) for o in db.scalars(q)],
    )


@router.get("/places/search")
@limiter.limit("20/minute")
def search(request: Request, q: str, ctx: OrgContext = Depends(require_writable)) -> list[dict]:  # noqa: ARG001
    """Find the outlet's listing on Google Maps."""
    try:
        return google_places.search(q)
    except google_places.PlacesError as exc:
        raise HTTPException(400, str(exc)) from exc


class LinkIn(BaseModel):
    place_id: str = Field(min_length=10, max_length=300)


class SyncOut(BaseModel):
    outlet: OutletPlace
    new_reviews: int
    message: str


async def _sync(db: Session, ctx: OrgContext, o: Outlet) -> SyncOut:
    new_ids = await asyncio.to_thread(google_places.sync_outlet, db, o)
    if new_ids:
        await enqueue_analysis(ctx.org.id, new_ids)
    if o.google_sync_error:
        msg = o.google_sync_error
    elif new_ids:
        msg = f"{len(new_ids)} new Google review{'' if len(new_ids) == 1 else 's'} added. The AI is reading them now."
    else:
        msg = "Checked Google: no new reviews since the last check."
    return SyncOut(outlet=_row(o), new_reviews=len(new_ids), message=msg)


@router.put("/outlets/{outlet_id}/google-place", response_model=SyncOut)
@limiter.limit("10/minute")
async def link(
    request: Request,  # noqa: ARG001
    outlet_id: int,
    body: LinkIn,
    ctx: OrgContext = Depends(require_writable),
    db: Session = Depends(get_db),
) -> SyncOut:
    """Link an outlet to its Google listing and pull its reviews straight away."""
    if not google_places.enabled():
        raise HTTPException(400, "Google reviews by Maps listing aren't switched on yet.")
    if not google_places.valid_place_id(body.place_id):
        raise HTTPException(422, "That isn't a Google listing. Search again and pick from the list.")
    o = _outlet(db, ctx, outlet_id)
    if o.google_place_id != body.place_id:
        o.google_place_id, o.google_place_name, o.google_synced_at = body.place_id, None, None
        o.google_rating = o.google_rating_count = None
    db.commit()
    return await _sync(db, ctx, o)


@router.post("/outlets/{outlet_id}/google-place/sync", response_model=SyncOut)
@limiter.limit("6/minute")
async def sync_now(
    request: Request,  # noqa: ARG001
    outlet_id: int,
    ctx: OrgContext = Depends(require_writable),
    db: Session = Depends(get_db),
) -> SyncOut:
    o = _outlet(db, ctx, outlet_id)
    if not o.google_place_id:
        raise HTTPException(400, "Link this outlet to its Google listing first.")
    return await _sync(db, ctx, o)


@router.delete("/outlets/{outlet_id}/google-place")
def unlink(outlet_id: int, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)) -> dict:
    """Stop checking Google for this outlet. Reviews already added stay."""
    o = _outlet(db, ctx, outlet_id)
    o.google_place_id = o.google_place_name = o.google_sync_error = None
    o.google_rating = o.google_rating_count = o.google_synced_at = None
    db.commit()
    return {"ok": True}
