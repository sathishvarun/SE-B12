"""Billing-software hook, nearby competitors and testimonials."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_owner, require_superadmin
from app.auth.security import hash_token
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Organization, Outlet, Testimonial
from app.services import competitors, review_requests

router = APIRouter(prefix="/api/v1", tags=["extras"])


# ---------- Billing software: ask every guest automatically after the bill ----------


class BillingKeyOut(BaseModel):
    key: str  # shown once; only a hash is stored
    endpoint: str


@router.post("/settings/billing-key", response_model=BillingKeyOut)
def new_billing_key(ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> BillingKeyOut:
    """Create (or replace) the key your billing software uses. The old key stops working."""
    key = "vbk_" + secrets.token_urlsafe(24)
    ctx.org.billing_key_hash = hash_token(key)
    db.commit()
    return BillingKeyOut(key=key, endpoint=f"{settings.APP_URL.replace('5450', '8450')}/api/v1/hooks/bill")


class BillIn(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    outlet: str | None = Field(default=None, max_length=120)  # outlet name or id
    consent: bool = True  # the billing software only sends guests who agreed


@router.post("/hooks/bill")
@limiter.limit("300/minute")
def bill_hook(
    request: Request, body: BillIn, x_virundhu_key: str = Header(default=""), db: Session = Depends(get_db)
) -> dict[str, str]:
    """Called by the restaurant's billing software after each bill. Sends the guest a feedback request on WhatsApp."""
    if not x_virundhu_key.startswith("vbk_"):
        raise HTTPException(401, "Missing or wrong X-Virundhu-Key header.")
    org = db.scalar(select(Organization).where(Organization.billing_key_hash == hash_token(x_virundhu_key)))
    if org is None:
        raise HTTPException(401, "Missing or wrong X-Virundhu-Key header.")
    if not org.ask_after_bill:
        return {"status": "off"}
    if not body.consent:
        return {"status": "no_consent"}
    if not settings.whatsapp_enabled:
        raise HTTPException(409, "WhatsApp isn't connected yet, so messages can't go out automatically.")
    outlet_id = None
    if body.outlet:
        q = select(Outlet).where(Outlet.organization_id == org.id, Outlet.is_active)
        q = q.where(Outlet.id == int(body.outlet)) if body.outlet.isdigit() else q.where(Outlet.name.ilike(body.outlet))
        outlet = db.scalar(q)
        outlet_id = outlet.id if outlet else None
    result = review_requests.send_requests(db, org, [body.phone], outlet_id)
    return {"status": result[0].status if result else "invalid"}


# ---------- Nearby competitors (Google Places) ----------


@router.get("/competitors")
def nearby(
    outlet_id: int, refresh: bool = False, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> dict:
    if not settings.GOOGLE_PLACES_API_KEY:
        return {"enabled": False}
    if ctx.outlet_ids is not None and outlet_id not in ctx.outlet_ids:
        raise HTTPException(403, "You can only see your own outlet.")
    outlet = db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.organization_id == ctx.org.id))
    if outlet is None:
        raise HTTPException(404, "Outlet not found.")
    try:
        data = competitors.compare(ctx.org, outlet, refresh=refresh)
    except competitors.CompetitorError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Couldn't reach Google right now. Try again later.") from exc
    db.commit()
    return {"enabled": True, "outlet": outlet.name, **data}


# ---------- Testimonials (real customers only, added by the admin) ----------


class TestimonialIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    quote: str = Field(min_length=10, max_length=600)
    published: bool = False
    sort_order: int = 0


class TestimonialOut(TestimonialIn):
    id: int
    created_at: datetime


@router.get("/public/testimonials", response_model=list[TestimonialOut])
def public_testimonials(db: Session = Depends(get_db)) -> list[Testimonial]:
    q = select(Testimonial).where(Testimonial.published).order_by(Testimonial.sort_order, Testimonial.id)
    return list(db.scalars(q.limit(12)))


@router.get("/admin/testimonials", response_model=list[TestimonialOut], dependencies=[Depends(require_superadmin)])
def all_testimonials(db: Session = Depends(get_db)) -> list[Testimonial]:
    return list(db.scalars(select(Testimonial).order_by(Testimonial.sort_order, Testimonial.id)))


@router.post("/admin/testimonials", response_model=TestimonialOut, dependencies=[Depends(require_superadmin)])
def add_testimonial(body: TestimonialIn, db: Session = Depends(get_db)) -> Testimonial:
    t = Testimonial(**body.model_dump())
    db.add(t)
    db.commit()
    return t


@router.put("/admin/testimonials/{tid}", response_model=TestimonialOut, dependencies=[Depends(require_superadmin)])
def edit_testimonial(tid: int, body: TestimonialIn, db: Session = Depends(get_db)) -> Testimonial:
    t = db.get(Testimonial, tid)
    if t is None:
        raise HTTPException(404, "Not found.")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    return t


@router.delete("/admin/testimonials/{tid}", status_code=204, dependencies=[Depends(require_superadmin)])
def delete_testimonial(tid: int, db: Session = Depends(get_db)) -> None:
    t = db.get(Testimonial, tid)
    if t:
        db.delete(t)
        db.commit()
