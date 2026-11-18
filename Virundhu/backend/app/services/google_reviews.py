"""Live Google reviews through the official Google Business Profile APIs.

Flow: the owner clicks Connect Google -> signs in with the Google account that manages their listings ->
we keep an encrypted refresh token -> every 10 minutes (and on "Sync now") we pull new reviews for every
verified location, read them with the AI, and fire instant alerts. Replies can be posted back to Google.

Google must first approve Business Profile API access for the Google Cloud project; until then Google answers
with 403/429 errors, which we show to the user in plain words.
"""

import logging
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Organization, Outlet, Review, SourceConnection
from app.services.crypto import decrypt, encrypt
from app.services.plans import limits, limits_for

logger = logging.getLogger(__name__)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 - URL, not a secret
SCOPE = "https://www.googleapis.com/auth/business.manage openid email"
ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
INFO_URL = "https://mybusinessbusinessinformation.googleapis.com/v1"
V4_URL = "https://mybusiness.googleapis.com/v4"
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class GoogleError(Exception):
    """A problem talking to Google, with a message the owner can understand."""


def connect_url(org_id: int, user_id: int) -> str:
    """Google consent page for the Business Profile scope. The state carries who is connecting."""
    state = jwt.encode(
        {"purpose": "connect", "org": org_id, "user": user_id, "exp": datetime.now(UTC).timestamp() + 600},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _connection(db: Session, org_id: int) -> SourceConnection:
    conn = db.scalar(
        select(SourceConnection).where(
            SourceConnection.organization_id == org_id, SourceConnection.provider == "google"
        )
    )
    if conn is None:
        conn = SourceConnection(organization_id=org_id, provider="google")
        db.add(conn)
        db.flush()
    return conn


def finish_connect(db: Session, org_id: int, code: str) -> None:
    """Exchange the code for tokens and store the refresh token encrypted."""
    res = httpx.post(
        TOKEN_URL,
        timeout=20,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    ).json()
    if "refresh_token" not in res:
        raise GoogleError("Google didn't return a long-term permission. Please click Connect Google again.")
    email = None
    if res.get("id_token"):
        email = jwt.decode(res["id_token"], options={"verify_signature": False}).get("email")
    conn = _connection(db, org_id)
    conn.status = "connected"
    conn.details = {"refresh_token": encrypt(res["refresh_token"]), "email": email, "locations": [], "last_error": None}
    db.commit()


def disconnect(db: Session, org_id: int) -> None:
    conn = _connection(db, org_id)
    conn.status, conn.details = "not_connected", None
    db.commit()


def _access_token(conn: SourceConnection) -> str:
    token = decrypt((conn.details or {}).get("refresh_token", ""))
    if not token:
        raise GoogleError("The Google connection has expired. Please connect Google again.")
    res = httpx.post(
        TOKEN_URL,
        timeout=20,
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": token,
            "grant_type": "refresh_token",
        },
    )
    if res.status_code != 200:
        raise GoogleError("Google refused the saved permission. Please connect Google again.")
    return res.json()["access_token"]


def _get(client: httpx.Client, url: str, **params: object) -> dict:
    res = client.get(url, params=params)
    if res.status_code == 200:
        return res.json()
    if res.status_code in (403, 429):
        raise GoogleError(
            "Google hasn't switched on Business Profile API access for this app yet. "
            "Request it in Google Cloud (Application for Basic API Access); reviews flow in once Google approves."
        )
    if res.status_code == 401:
        raise GoogleError("The Google connection has expired. Please connect Google again.")
    raise GoogleError(f"Google returned an error ({res.status_code}). We'll try again in 10 minutes.")


def _outlet_for(db: Session, org_id: int, plan: str, title: str) -> int | None:
    outlet = db.scalar(select(Outlet).where(Outlet.organization_id == org_id, func.lower(Outlet.name) == title.lower()))
    if outlet:
        return outlet.id
    count = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == org_id, Outlet.is_active)) or 0
    org = db.get(Organization, org_id)
    if count >= (limits_for(org) if org else limits(plan))["outlets"]:
        first = db.scalar(select(Outlet.id).where(Outlet.organization_id == org_id).order_by(Outlet.id))
        return first
    outlet = Outlet(organization_id=org_id, name=title[:120])
    db.add(outlet)
    db.flush()
    return outlet.id


def sync(db: Session, org_id: int, plan: str) -> list[int]:
    """Pull new Google reviews for every location. Returns ids of newly added reviews."""
    conn = _connection(db, org_id)
    if conn.status != "connected":
        return []
    new_ids: list[int] = []
    details = dict(conn.details or {})
    try:
        token = _access_token(conn)
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as client:
            accounts = _get(client, ACCOUNTS_URL).get("accounts", [])
            locations_seen = []
            for account in accounts:
                locs = _get(client, f"{INFO_URL}/{account['name']}/locations", readMask="name,title", pageSize=100)
                for loc in locs.get("locations", []):
                    title = loc.get("title") or "Google location"
                    locations_seen.append(title)
                    outlet_id = _outlet_for(db, org_id, plan, title)
                    loc_id = loc["name"].split("/")[-1]
                    page = _get(
                        client,
                        f"{V4_URL}/{account['name']}/locations/{loc_id}/reviews",
                        pageSize=50,
                        orderBy="updateTime desc",
                    )
                    for r in page.get("reviews", []):
                        created = (r.get("createTime") or datetime.now(UTC).isoformat())[:10]
                        replied = bool(r.get("reviewReply"))
                        stmt = (
                            insert(Review)
                            .values(
                                organization_id=org_id,
                                outlet_id=outlet_id,
                                external_id=str(r.get("reviewId"))[:120],
                                platform="google",
                                rating=STARS.get(r.get("starRating", ""), 3),
                                review_date=datetime.fromisoformat(created).date(),
                                review_text=(r.get("comment") or "").strip()[:5000],
                                analysis_status="pending",
                                workflow_status="replied" if replied else "new",
                                final_reply=(r.get("reviewReply") or {}).get("comment"),
                                source_ref=r.get("name"),
                                is_sample=False,
                            )
                            .on_conflict_do_nothing(constraint="uq_review_org_platform_ext")
                            .returning(Review.id)
                        )
                        new_id = db.execute(stmt).scalar()
                        if new_id:
                            new_ids.append(new_id)
            details.update(locations=locations_seen, last_error=None)
    except GoogleError as exc:
        details["last_error"] = str(exc)
        logger.warning("Google sync for org %s: %s", org_id, exc)
    except httpx.HTTPError:
        details["last_error"] = "Couldn't reach Google. We'll try again in 10 minutes."
    conn.details = details
    conn.last_synced_at = datetime.now(UTC)
    db.commit()
    return new_ids


def post_reply(db: Session, org_id: int, review: Review, text: str) -> None:
    """Publish the owner's reply on Google (creates or replaces the existing reply)."""
    if not review.source_ref:
        raise GoogleError("This review didn't come from the Google connection, so it can't be replied to from here.")
    conn = _connection(db, org_id)
    if conn.status != "connected":
        raise GoogleError("Connect Google first (Connections page).")
    token = _access_token(conn)
    res = httpx.put(
        f"{V4_URL}/{review.source_ref}/reply",
        timeout=20,
        headers={"Authorization": f"Bearer {token}"},
        json={"comment": text},
    )
    if res.status_code != 200:
        raise GoogleError(
            f"Google didn't accept the reply ({res.status_code}). Try again, or reply on Google directly."
        )
    review.final_reply = text
    review.workflow_status = "replied"
    review.reply_posted_at = review.replied_at = datetime.now(UTC)
    db.commit()
