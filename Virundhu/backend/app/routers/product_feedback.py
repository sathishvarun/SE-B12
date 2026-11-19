"""Feedback about Virundhu itself: the share-feedback form (website and app) and the in-app ease-of-use check.

Nothing here calls the AI: rows are saved as `new` and Isai, the feedback agent, handles them within a minute
(services/agent_team.isai_round). Numbers on the admin page are computed here in SQL, never by the model.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_superadmin
from app.database import get_db
from app.limiter import limiter
from app.models import ProductFeedback

router = APIRouter(prefix="/api/v1", tags=["product-feedback"])

AREAS = ("setup", "inbox", "replies", "alerts", "reports", "ai_staff", "billing", "other")
EASE_PROMPT_AFTER = timedelta(days=3)
EASE_PROMPT_EVERY = timedelta(days=30)


class FeedbackIn(BaseModel):
    kind: str = Field(pattern="^(idea|problem|praise|other)$")
    message: str = Field(min_length=3, max_length=3000)
    rating: int | None = Field(default=None, ge=1, le=5)
    area: str | None = Field(default=None, pattern="^(" + "|".join(AREAS) + ")$")
    consent_quote: bool = False
    page: str = Field(default="", max_length=120)


class PublicFeedbackIn(FeedbackIn):
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    restaurant: str = Field(default="", max_length=160)
    website: str = Field(default="", max_length=200)  # honeypot

    @model_validator(mode="after")
    def _email(self) -> "PublicFeedbackIn":
        if self.email and ("@" not in self.email or "." not in self.email.split("@")[-1]):
            raise ValueError("That email doesn't look right.")
        return self


class EaseIn(BaseModel):
    ease: int = Field(ge=1, le=5)
    nps: int | None = Field(default=None, ge=0, le=10)
    area: str | None = Field(default=None, pattern="^(" + "|".join(AREAS) + ")$")
    message: str = Field(default="", max_length=2000)
    page: str = Field(default="", max_length=120)


THANKS = "Thank you. Isai, our feedback agent, is reading it now; you'll hear back by email within a few minutes."


@router.post("/public/feedback", status_code=201)
@limiter.limit("5/minute")
def public_feedback(request: Request, body: PublicFeedbackIn, db: Session = Depends(get_db)) -> dict:
    """The website's share-feedback form: no sign-in."""
    if body.website:  # bots fill the hidden field; pretend all is well
        return {"ok": True, "message": THANKS}
    db.add(ProductFeedback(
        source="website", kind=body.kind, rating=body.rating, area=body.area, message=body.message.strip(),
        name=body.name.strip() or None, email=body.email.strip().lower() or None,
        restaurant=body.restaurant.strip() or None, page=body.page or None, consent_quote=body.consent_quote,
    ))
    db.commit()
    return {"ok": True, "message": THANKS if body.email else "Thank you. Your feedback is in."}


@router.post("/feedback", status_code=201)
def app_feedback(body: FeedbackIn, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Share-feedback inside the app; the restaurant and the person come from the sign-in."""
    db.add(ProductFeedback(
        organization_id=ctx.org.id, user_id=ctx.user.id, source="app", kind=body.kind, rating=body.rating,
        area=body.area, message=body.message.strip(), name=ctx.user.full_name, email=ctx.user.email,
        restaurant=ctx.org.name, page=body.page or None, consent_quote=body.consent_quote,
    ))
    db.commit()
    return {"ok": True, "message": THANKS}


@router.get("/feedback/ease-prompt")
def ease_prompt(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Should the app ask 'How easy is Virundhu?' now? After 3 days of use, then at most once a month."""
    if ctx.user.is_superadmin or ctx.org.is_demo:
        return {"due": False}
    now = datetime.now(UTC)
    if ctx.org.created_at and now - ctx.org.created_at < EASE_PROMPT_AFTER:
        return {"due": False}
    last = db.scalar(select(func.max(ProductFeedback.created_at)).where(
        ProductFeedback.user_id == ctx.user.id, ProductFeedback.kind == "ease"))
    return {"due": last is None or now - last > EASE_PROMPT_EVERY}


@router.post("/feedback/ease", status_code=201)
def ease_check(body: EaseIn, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    db.add(ProductFeedback(
        organization_id=ctx.org.id, user_id=ctx.user.id, source="app", kind="ease", ease=body.ease, nps=body.nps,
        area=body.area, message=body.message.strip() or None, name=ctx.user.full_name, email=ctx.user.email,
        restaurant=ctx.org.name, page=body.page or None,
    ))
    db.commit()
    hard = body.ease <= 2 and body.message.strip()
    return {"ok": True, "message": "Thank you. Tara will email you a step-by-step for the hard part in a few minutes."
            if hard else "Thank you. This helps us make Virundhu easier."}


@router.get("/admin/feedback", dependencies=[Depends(require_superadmin)])
def admin_feedback(db: Session = Depends(get_db), days: int = 90) -> dict:
    """Ease score, recommend score, where people struggle, and every piece of feedback with what Isai did."""
    since = datetime.now(UTC) - timedelta(days=max(1, min(days, 365)))
    rows = list(db.scalars(select(ProductFeedback).where(ProductFeedback.created_at >= since)
                           .order_by(ProductFeedback.id.desc())))
    eases = [r.ease for r in rows if r.ease]
    npss = [r.nps for r in rows if r.nps is not None]
    nps = round(100 * (sum(n >= 9 for n in npss) - sum(n <= 6 for n in npss)) / len(npss)) if npss else None
    area_of = lambda r: r.area or r.ai_area or "other"  # noqa: E731
    kind_of = lambda r: "ease" if r.kind == "ease" else (r.ai_kind or r.kind)  # noqa: E731
    hard: dict[str, int] = {}
    ideas: dict[str, int] = {}
    for r in rows:
        if (r.ease and r.ease <= 3) or kind_of(r) == "problem":
            hard[area_of(r)] = hard.get(area_of(r), 0) + 1
        if kind_of(r) == "idea":
            ideas[area_of(r)] = ideas.get(area_of(r), 0) + 1
    kinds: dict[str, int] = {}
    for r in rows:
        kinds[kind_of(r)] = kinds.get(kind_of(r), 0) + 1
    return {
        "days": days,
        "total": len(rows),
        "ease_avg": round(sum(eases) / len(eases), 1) if eases else None,
        "ease_count": len(eases),
        "ease_split": [sum(1 for e in eases if e == i) for i in range(1, 6)],
        "nps": nps,
        "nps_count": len(npss),
        "kinds": kinds,
        "hard_areas": sorted(hard.items(), key=lambda x: -x[1]),
        "idea_areas": sorted(ideas.items(), key=lambda x: -x[1]),
        "items": [
            {"id": r.id, "at": r.created_at.isoformat(), "source": r.source, "kind": kind_of(r),
             "sentiment": r.ai_sentiment, "rating": r.rating, "ease": r.ease, "nps": r.nps, "area": area_of(r),
             "message": r.message, "summary": r.ai_summary, "who": r.name or r.email or "Visitor",
             "restaurant": r.restaurant, "action": r.agent_action, "status": r.status}
            for r in rows[:100]
        ],
    }

