"""Dishes and staff guests talk about (insights page) and the public review widget for the restaurant's own website."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context
from app.database import get_db
from app.limiter import limiter
from app.models import Organization, Outlet, Review, ReviewAnalysis
from app.services import maps

router = APIRouter(prefix="/api/v1", tags=["insights"])


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())[:60]


@router.get("/insights/mentions")
def mentions(
    days: int = Query(90, ge=7, le=730),
    outlet_id: int | None = None,
    ctx: OrgContext = Depends(get_org_context),
    db: Session = Depends(get_db),
) -> dict:
    """Which dishes and which staff guests name, how often, and whether they liked them, with example reviews."""
    since = date.today() - timedelta(days=days)
    q = (
        select(
            Review.id,
            Review.rating,
            Review.review_text,
            Review.review_date,
            Review.platform,
            Outlet.name,
            ReviewAnalysis.dishes,
            ReviewAnalysis.staff,
        )
        .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .outerjoin(Outlet, Outlet.id == Review.outlet_id)
        .where(Review.organization_id == ctx.org.id, Review.review_date >= since)
    )
    if outlet_id:
        q = q.where(Review.outlet_id == outlet_id)
    out: dict[str, dict] = {"dishes": defaultdict(dict), "staff": defaultdict(dict)}
    for rid, rating, text, rdate, platform, outlet, dishes, staff in db.execute(q):
        for kind, items in (("dishes", dishes or []), ("staff", staff or [])):
            for m in items:
                name = _norm(str(m.get("name", "")))
                if len(name) < 2:
                    continue
                row = out[kind][name] or {
                    "name": name,
                    "mentions": 0,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "outlets": defaultdict(int),
                    "examples": [],
                }
                out[kind][name] = row
                s = m.get("sentiment") if m.get("sentiment") in ("positive", "negative", "neutral") else "neutral"
                row["mentions"] += 1
                row[s] += 1
                if outlet:
                    row["outlets"][outlet] += 1
                if len(row["examples"]) < 3:
                    row["examples"].append(
                        {
                            "id": rid,
                            "rating": rating,
                            "text": (text or "")[:220],
                            "date": rdate.isoformat(),
                            "platform": platform,
                            "outlet": outlet,
                            "sentiment": s,
                        }
                    )

    def finish(rows: dict) -> list[dict]:
        items = sorted(rows.values(), key=lambda r: (-r["mentions"], r["name"]))[:40]
        for r in items:
            r["outlets"] = sorted(({"name": k, "count": v} for k, v in r["outlets"].items()), key=lambda x: -x["count"])
            r["score"] = round(100 * (r["positive"] - r["negative"]) / r["mentions"]) if r["mentions"] else 0
        return items

    return {"days": days, "dishes": finish(out["dishes"]), "staff": finish(out["staff"])}


@router.get("/public/widget/{token}")
@limiter.limit("60/minute")
def widget(token: str, request: Request, db: Session = Depends(get_db)) -> dict:  # noqa: ARG001
    """Data for the review widget a restaurant puts on its own website: the true average from every review in the last
    year, and the latest reviews with text. The widget states which reviews it shows, so nothing is hidden."""
    org = db.scalar(select(Organization).where(Organization.feedback_token == token))
    if org is None or org.is_suspended:
        raise HTTPException(404, "Widget not found.")
    since = date.today() - timedelta(days=365)
    base = select(Review).where(
        Review.organization_id == org.id, Review.review_date >= since, Review.is_sample.is_(False)
    )
    count, avg = db.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.organization_id == org.id, Review.review_date >= since, Review.is_sample.is_(False)
        )
    ).one()
    latest = db.scalars(
        base.where(Review.rating >= 4, func.length(Review.review_text) >= 20)
        .order_by(Review.review_date.desc())
        .limit(6)
    )
    outlets = db.scalars(select(Outlet).where(Outlet.organization_id == org.id, Outlet.is_active.is_(True)))
    return {
        "restaurant": org.name,
        "average": round(float(avg), 1) if avg else None,
        "count": count,
        "shown": "Latest 4 and 5 star reviews with comments",
        "reviews": [
            {"rating": r.rating, "text": r.review_text[:400], "date": r.review_date.isoformat(), "platform": r.platform}
            for r in latest
        ],
        "branches": [
            {"name": o.name, "area": o.area or o.city, "directions_url": maps.directions_url(o)}
            for o in outlets
            if maps.directions_url(o)
        ],
        "updated": datetime.now(UTC).isoformat(),
    }
