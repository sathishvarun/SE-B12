"""Admin → Demo prep: replies drafted to a prospect's own latest reviews, ready before the call."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.database import get_db
from app.limiter import limiter
from app.models import DemoPrep, Lead, User
from app.services import demo_prep

router = APIRouter(prefix="/api/v1/admin/demo-preps", tags=["admin"])


class PastedReview(BaseModel):
    text: str = Field(min_length=3, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    author: str = Field(default="A guest", max_length=80)


class PrepIn(BaseModel):
    restaurant: str = Field(min_length=2, max_length=160)
    maps_link: str = Field(default="", max_length=500)
    tone: str = Field(default="warm", pattern="^(warm|formal|friendly)$")
    reviews: list[PastedReview] = Field(default_factory=list, max_length=3)
    lead_id: int | None = None

    @model_validator(mode="after")
    def _link(self) -> "PrepIn":
        if self.maps_link and not demo_prep.is_maps_link(self.maps_link):
            raise ValueError("Paste a Google Maps link (from the Share button), or leave it empty.")
        return self


class PrepOut(BaseModel):
    id: int
    lead_id: int | None
    restaurant: str
    maps_link: str | None
    place_name: str | None
    rating: float | None
    rating_count: int | None
    tone: str
    status: str
    error: str | None
    reviews: list[dict]
    created_at: str


def _out(p: DemoPrep) -> PrepOut:
    return PrepOut(
        id=p.id,
        lead_id=p.lead_id,
        restaurant=p.restaurant,
        maps_link=p.maps_link,
        place_name=p.place_name,
        rating=float(p.rating) if p.rating is not None else None,
        rating_count=p.rating_count,
        tone=p.tone,
        status=p.status,
        error=p.error,
        reviews=p.reviews or [],
        created_at=p.created_at.isoformat(),
    )


@router.get("", response_model=list[PrepOut])
def list_preps(_: User = Depends(require_superadmin), db: Session = Depends(get_db)) -> list[PrepOut]:
    return [_out(p) for p in db.scalars(select(DemoPrep).order_by(DemoPrep.id.desc()).limit(50))]


@router.get("/{prep_id}", response_model=PrepOut)
def get_prep(prep_id: int, _: User = Depends(require_superadmin), db: Session = Depends(get_db)) -> PrepOut:
    p = db.get(DemoPrep, prep_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return _out(p)


@router.post("", response_model=PrepOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/hour")
async def create_prep(
    request: Request, body: PrepIn, admin: User = Depends(require_superadmin), db: Session = Depends(get_db)
) -> PrepOut:
    """Queue the prep; the page polls until the replies are ready (usually under a minute)."""
    if body.lead_id and db.get(Lead, body.lead_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found.")
    p = DemoPrep(
        lead_id=body.lead_id,
        restaurant=body.restaurant.strip(),
        maps_link=body.maps_link.strip() or None,
        tone=body.tone,
        reviews=[r.model_dump() for r in body.reviews],
        status="queued",
        created_by=admin.email,
    )
    db.add(p)
    db.commit()
    await demo_prep.enqueue(p.id)
    return _out(p)


@router.delete("/{prep_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prep(prep_id: int, _: User = Depends(require_superadmin), db: Session = Depends(get_db)) -> None:
    p = db.get(DemoPrep, prep_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    db.delete(p)
    db.commit()
