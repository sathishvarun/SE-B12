"""How an outlet compares with restaurants nearby, from Google Places (public ratings only).

Needs GOOGLE_PLACES_API_KEY (Places API (New), billed per request by Google). Results are cached for a day per outlet.
"""

from datetime import UTC, datetime, timedelta

import httpx

from app.config import settings
from app.models import Organization, Outlet

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = "places.id,places.displayName,places.rating,places.userRatingCount,places.formattedAddress"
CACHE = timedelta(hours=24)


class CompetitorError(RuntimeError):
    pass


def _search(query: str, limit: int) -> list[dict]:
    res = httpx.post(
        URL,
        json={"textQuery": query, "maxResultCount": limit, "languageCode": "en", "regionCode": "IN"},
        headers={"X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY, "X-Goog-FieldMask": FIELDS},
        timeout=15,
    )
    if res.status_code >= 400:
        raise CompetitorError(
            "Google Places refused the request. Check GOOGLE_PLACES_API_KEY and that Places API is on."
        )
    return [
        {
            "id": p.get("id"),
            "name": (p.get("displayName") or {}).get("text", ""),
            "rating": p.get("rating"),
            "reviews": p.get("userRatingCount", 0),
            "address": p.get("formattedAddress", ""),
        }
        for p in res.json().get("places", [])
    ]


def compare(org: Organization, outlet: Outlet, refresh: bool = False) -> dict:
    now = datetime.now(UTC)
    if outlet.competitors and outlet.competitors_at and not refresh and now - outlet.competitors_at < CACHE:
        return outlet.competitors
    where = ", ".join(x for x in (outlet.area, outlet.city or org.city, outlet.district) if x) or (org.city or "")
    if not where:
        raise CompetitorError("Add the outlet's area and city in Settings → Outlets first.")
    own = _search(f"{org.name} {outlet.name} {where}", 1)
    you = own[0] if own else None
    nearby = [p for p in _search(f"restaurants in {where}", 15) if not you or p["id"] != you["id"]]
    rated = [p for p in nearby if p["rating"]]
    avg = round(sum(p["rating"] for p in rated) / len(rated), 2) if rated else None
    data = {
        "where": where,
        "you": you,
        "nearby": sorted(rated, key=lambda p: (-(p["rating"] or 0), -p["reviews"]))[:10],
        "area_average": avg,
        "fetched_at": now.isoformat(),
    }
    outlet.competitors, outlet.competitors_at = data, now
    return data
