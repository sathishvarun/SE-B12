"""Google reviews through the Places API (New): works without Business Profile API approval.

The owner links each outlet to its Google Maps listing once (search by name and area, then pick). After that Virundhu
checks the listing once a day (and on "Check now"): Google returns the outlet's rating and up to 5 reviews per check,
which land in the Inbox and are read by the AI like any other review. Replies are posted by the owner on Google
(Places is read-only). When the restaurant connects its Business Profile, that full sync takes over and this stops.

Needs GOOGLE_PLACES_API_KEY with "Places API (New)" switched on. Each check is one billed Place Details request.
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Organization, Outlet, Review, SourceConnection

logger = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{id}"
SEARCH_FIELDS = "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount"
DETAILS_FIELDS = "id,displayName,rating,userRatingCount,reviews"
EVERY = timedelta(hours=24)
PLACE_ID = re.compile(r"^[A-Za-z0-9_-]{10,300}$")


class PlacesError(RuntimeError):
    """Something the owner can act on, worded for them."""


def enabled() -> bool:
    return bool(settings.GOOGLE_PLACES_API_KEY)


def _headers(fields: str) -> dict[str, str]:
    return {"X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": fields}


def _raise_for(res: httpx.Response) -> None:
    if res.status_code < 400:
        return
    try:
        msg = res.json().get("error", {}).get("message", "")
    except ValueError:
        msg = ""
    logger.warning("Google Places %s: %s", res.status_code, msg[:300])
    if res.status_code == 404:
        raise PlacesError("Google no longer has this listing. Link the outlet again.")
    if res.status_code in (401, 403):
        raise PlacesError("Google refused the request. The Places API key needs checking (admin).")
    if res.status_code == 429:
        raise PlacesError("Google is busy. We'll try again shortly.")
    raise PlacesError("Google didn't answer properly. We'll try again shortly.")


def search(query: str, limit: int = 6) -> list[dict]:
    """Listings on Google Maps matching a name and area, for the owner to pick from."""
    if not enabled():
        raise PlacesError("Google reviews by Maps listing aren't switched on yet.")
    query = query.strip()[:200]
    if len(query) < 3:
        raise PlacesError("Type the restaurant name and area, for example 'Annapoorna RS Puram Coimbatore'.")
    try:
        res = httpx.post(
            SEARCH_URL,
            json={"textQuery": query, "maxResultCount": limit, "languageCode": "en", "regionCode": "IN"},
            headers=_headers(SEARCH_FIELDS),
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise PlacesError("Couldn't reach Google. Try again in a minute.") from exc
    _raise_for(res)
    return [
        {
            "place_id": p.get("id"),
            "name": (p.get("displayName") or {}).get("text", ""),
            "address": p.get("formattedAddress", ""),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount", 0),
        }
        for p in res.json().get("places", [])
        if p.get("id")
    ]


def _details(place_id: str) -> dict:
    try:
        res = httpx.get(
            DETAILS_URL.format(id=place_id),
            params={"languageCode": "en"},
            headers=_headers(DETAILS_FIELDS),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise PlacesError("Couldn't reach Google. We'll try again shortly.") from exc
    _raise_for(res)
    return res.json()


def _review_values(org_id: int, outlet_id: int, r: dict) -> dict | None:
    rid = str(r.get("name") or "")
    rating = r.get("rating")
    if not rid or not isinstance(rating, int | float):
        return None
    original = (r.get("originalText") or {}).get("text") or (r.get("text") or {}).get("text") or ""
    published = r.get("publishTime") or datetime.now(UTC).isoformat()
    try:
        when = datetime.fromisoformat(published.replace("Z", "+00:00")).date()
    except ValueError:
        when = datetime.now(UTC).date()
    return {
        "organization_id": org_id,
        "outlet_id": outlet_id,
        "external_id": "gp:" + rid.split("/")[-1][:110],
        "platform": "google",
        "rating": max(1, min(5, int(round(rating)))),
        "review_date": when,
        "review_text": original.strip()[:5000],
        "analysis_status": "pending",
        "workflow_status": "new",
        "guest_name": ((r.get("authorAttribution") or {}).get("displayName") or "")[:80] or None,
        "is_sample": False,
    }


def sync_outlet(db: Session, outlet: Outlet) -> list[int]:
    """Check one linked outlet on Google. Returns ids of reviews that are new to Virundhu."""
    if not outlet.google_place_id:
        return []
    new_ids: list[int] = []
    try:
        data = _details(outlet.google_place_id)
        outlet.google_place_name = ((data.get("displayName") or {}).get("text") or outlet.google_place_name or "")[:200]
        if data.get("rating") is not None:
            outlet.google_rating = Decimal(str(round(float(data["rating"]), 1)))
        outlet.google_rating_count = data.get("userRatingCount")
        for r in data.get("reviews") or []:
            values = _review_values(outlet.organization_id, outlet.id, r)
            if values is None:
                continue
            stmt = (
                insert(Review)
                .values(**values)
                .on_conflict_do_nothing(constraint="uq_review_org_platform_ext")
                .returning(Review.id)
            )
            new_id = db.execute(stmt).scalar()
            if new_id:
                new_ids.append(new_id)
        outlet.google_sync_error = None
    except PlacesError as exc:
        outlet.google_sync_error = str(exc)[:300]
    outlet.google_synced_at = datetime.now(UTC)
    db.commit()
    return new_ids


def full_sync_connected(db: Session, org_id: int) -> bool:
    """True when the restaurant connected its Business Profile: that sync brings every review, so Places stops."""
    conn = db.scalar(
        select(SourceConnection).where(
            SourceConnection.organization_id == org_id,
            SourceConnection.provider == "google",
            SourceConnection.status == "connected",
        )
    )
    return conn is not None


def due_outlets(db: Session, limit: int = 300) -> list[tuple[int, int]]:
    """(org_id, outlet_id) pairs whose daily check is due, oldest first."""
    cutoff = datetime.now(UTC) - EVERY
    rows = db.execute(
        select(Outlet.organization_id, Outlet.id)
        .join(Organization, Organization.id == Outlet.organization_id)
        .where(
            Outlet.google_place_id.is_not(None),
            Outlet.is_active.is_(True),
            Organization.is_suspended.is_(False),
            (Outlet.google_synced_at.is_(None)) | (Outlet.google_synced_at < cutoff),
        )
        .order_by(Outlet.google_synced_at.asc().nulls_first())
        .limit(limit)
    ).all()
    return [(o, i) for o, i in rows]


def valid_place_id(place_id: str) -> bool:
    return bool(PLACE_ID.match(place_id or ""))
