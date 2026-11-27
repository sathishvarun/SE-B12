"""Demo prep: open the call with replies already written to the restaurant's own latest Google reviews.

The admin (or the restaurant, on the contact form) gives a Google Maps link or the restaurant's name and area. The
worker finds the listing (Places API), takes its newest reviews, and drafts a reply to each with the same reading
pipeline the product uses. Without a Places key, or when Google has no reviews, the admin pastes up to three reviews
and gets the same drafts.

Runs in the worker (`demo_prep_job`), never inside a web request.
"""

import logging
import re
import threading
from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote_plus, urlparse

import httpx
from sqlalchemy.orm import Session

from app.ai.tagging import tag_review
from app.config import settings
from app.database import SessionLocal
from app.models import DemoPrep
from app.services import google_places

logger = logging.getLogger(__name__)
TAKE = 3
# Exact hosts only: the link may come from the public contact form, so nothing else is ever fetched (no SSRF).
MAPS_HOST = re.compile(r"^((www|maps)\.)?google\.(com|co\.in)$|^(maps\.app\.)?goo\.gl$|^g\.page$")
SHORT_HOST = re.compile(r"^(maps\.app\.)?goo\.gl$|^g\.page$")


class PrepError(Exception):
    """A plain-English reason the prep couldn't run, shown to the admin."""


def is_maps_link(url: str) -> bool:
    """https link on Google Maps' own hosts (no user info, no port)."""
    u = urlparse((url or "").strip())
    return u.scheme == "https" and not u.port and "@" not in u.netloc and bool(MAPS_HOST.match(u.hostname or ""))


def _expand(url: str) -> str:
    """Short links (maps.app.goo.gl, g.page) redirect to the full Maps URL that names the place.

    Redirects are followed by hand, at most 5, and every hop must stay on Google's own hosts."""
    for _ in range(5):
        if not SHORT_HOST.match(urlparse(url).hostname or ""):
            return url
        try:
            res = httpx.get(url, follow_redirects=False, timeout=10, headers={"User-Agent": "Mozilla/5.0 Virundhu"})
        except httpx.HTTPError as exc:
            raise PrepError("Couldn't open that Maps link. Check it, or type the restaurant name and area.") from exc
        nxt = res.headers.get("location")
        if not res.is_redirect or not nxt:
            break
        url = str(httpx.URL(url).join(nxt))
        if not is_maps_link(url):
            raise PrepError("That link didn't lead to Google Maps. Paste the link from the Share button on Maps.")
    if SHORT_HOST.match(urlparse(url).hostname or ""):
        raise PrepError("Couldn't open that Maps link. Paste the full link, or type the restaurant name and area.")
    return url


def place_hint(url: str) -> tuple[str | None, str | None]:
    """(place_id, search text) found in a Google Maps URL."""
    u = urlparse(url)
    q = parse_qs(u.query)
    pid = (q.get("query_place_id") or q.get("place_id") or [None])[0]
    if pid and google_places.valid_place_id(pid):
        return pid, None
    m = re.search(r"/maps/place/([^/@]+)", u.path)
    if m:
        return None, unquote_plus(m.group(1))[:200]
    for key in ("q", "query"):
        if q.get(key):
            return None, q[key][0][:200]
    return None, None


def _find_place(prep: DemoPrep) -> dict:
    if not google_places.enabled():
        raise PrepError("Google Maps reviews aren't switched on yet (no Places key). Paste up to 3 reviews instead.")
    pid, text = (None, None)
    if prep.maps_link:
        pid, text = place_hint(_expand(prep.maps_link.strip()))
    if not pid:
        hits = google_places.search(text or prep.restaurant, limit=1)
        if not hits:
            raise PrepError("Google Maps didn't find this restaurant. Try its name with the area, or paste reviews.")
        pid = hits[0]["place_id"]
    return google_places._details(pid)


def _when(r: dict) -> str:
    return (r.get("publishTime") or "")[:10]


def run(db: Session, prep_id: int) -> DemoPrep | None:
    """Fill one demo prep: find the reviews (unless pasted), then draft a reply to each."""
    prep = db.get(DemoPrep, prep_id)
    if prep is None:
        return None
    try:
        reviews = [r for r in (prep.reviews or []) if (r.get("text") or "").strip()]
        if not reviews:
            place = _find_place(prep)
            prep.place_id = place.get("id")
            prep.place_name = ((place.get("displayName") or {}).get("text") or "")[:200] or None
            prep.rating = place.get("rating")
            prep.rating_count = place.get("userRatingCount")
            found = sorted(place.get("reviews") or [], key=_when, reverse=True)
            for r in found:
                text = ((r.get("originalText") or {}).get("text") or (r.get("text") or {}).get("text") or "").strip()
                if not text:
                    continue
                reviews.append(
                    {
                        "author": ((r.get("authorAttribution") or {}).get("displayName") or "A guest")[:80],
                        "rating": int(round(r.get("rating") or 0)) or None,
                        "text": text[:2000],
                        "when": _when(r),
                    }
                )
                if len(reviews) == TAKE:
                    break
            if not reviews:
                raise PrepError("This listing has no written reviews on Google yet. Paste a few from Zomato instead.")
        if not settings.llm_configured:
            raise PrepError("The AI key isn't set on the server, so replies can't be drafted.")
        drafted = []
        signature = f"- Team {prep.place_name or prep.restaurant}"
        for r in reviews[:TAKE]:
            out = tag_review(r["text"], r.get("rating"), "google", prep.tone, signature, 2, None)
            drafted.append(
                {
                    **r,
                    "reply": out["suggested_reply"],
                    "summary": out["summary"],
                    "language": out["language"],
                    "urgency": out["urgency"],
                    "sentiment": out["sentiment"],
                }
            )
        prep.reviews = drafted
        prep.status, prep.error = "ready", None
    except PrepError as exc:
        prep.status, prep.error = "failed", str(exc)[:300]
    except google_places.PlacesError as exc:
        prep.status, prep.error = "failed", str(exc)[:300]
    except Exception:
        logger.exception("Demo prep %s failed", prep_id)
        prep.status, prep.error = "failed", "Something went wrong while drafting. Try again in a minute."
    prep.updated_at = datetime.now(UTC)
    db.commit()
    return prep


def _run_locally(prep_id: int) -> None:
    with SessionLocal() as db:
        run(db, prep_id)


async def enqueue(prep_id: int) -> None:
    """Hand the prep to the worker; if Redis is down, run it in a background thread instead."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job("demo_prep_job", prep_id)
        await pool.aclose()
    except Exception:
        logger.warning("Worker queue unavailable; preparing the demo in the API process instead")
        threading.Thread(target=_run_locally, args=(prep_id,), daemon=True).start()
