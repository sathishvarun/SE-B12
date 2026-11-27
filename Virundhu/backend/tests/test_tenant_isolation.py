"""Attacker's view: one restaurant must never reach another restaurant's data, an owner must never reach admin routes,
and nobody signed out reaches anything private.

These tests walk the live route list (OpenAPI), so a new endpoint is checked automatically the day it is added:
an ID route nobody listed here fails `test_every_id_route_is_covered`.
"""

import re
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Organization, Outlet, Payment, Refund, Review
from app.services import books

# Routes that are public on purpose: sign-in, the QR page, webhooks signed by the provider, the price list, the sample
# CSV, the website's Quick help box and accepting an invitation by its emailed token.
PUBLIC = re.compile(
    r"^/health$|^/api/v1/(auth/|public/|billing/(pricing|quote|webhook|dodo-webhook)$|hooks/bill$|"
    r"invitations/\{token\}(/accept)?$|connections/google/callback$|imports/template\.csv$|help/(ask|contact)$)"
)
# Admin routes reachable by an owner on purpose (none).
ADMIN = re.compile(r"^/api/v1/admin/")


def _routes() -> list[tuple[str, str]]:
    spec = app.openapi()
    return [
        (m.upper(), p) for p, ms in spec["paths"].items() for m in ms if m in ("get", "post", "put", "patch", "delete")
    ]


def _fill(path: str, value: int | str = 999999) -> str:
    return re.sub(r"\{[^}]+\}", str(value), path)


def _owner(client, name: str) -> tuple[dict, int, str]:
    email = f"iso-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Iso Owner",
            "organization_name": name,
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["organization"]["id"], email


def _admin(client) -> dict:
    tok = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_signed_out_reaches_nothing_private(client):
    client.cookies.clear()
    leaks = []
    for method, path in _routes():
        if PUBLIC.search(path):
            continue
        r = client.request(method, _fill(path), json={})
        if r.status_code < 400 or r.status_code not in (401, 403, 405):
            leaks.append(f"{method} {path} -> {r.status_code}")
    assert leaks == [], "Reachable without signing in:\n" + "\n".join(leaks)


def test_owner_reaches_no_admin_route(client):
    h, _, _ = _owner(client, "Iso Not Admin")
    leaks = []
    for method, path in _routes():
        if not ADMIN.search(path):
            continue
        r = client.request(method, _fill(path), json={}, headers=h)
        if r.status_code != 403:
            leaks.append(f"{method} {path} -> {r.status_code}")
    assert leaks == [], "Admin routes an owner reached:\n" + "\n".join(leaks)


@pytest.fixture
def two_restaurants(client):
    """Restaurant A with one of everything; restaurant B is the attacker."""
    a, a_org, a_email = _owner(client, "Iso Victim Mess")
    b, b_org, _ = _owner(client, "Iso Attacker Hotel")
    secret = f"SECRET-{uuid.uuid4().hex[:6]}"
    outlet = client.post("/api/v1/outlets", json={"name": f"{secret} branch", "city": "Madurai"}, headers=a)
    assert outlet.status_code in (200, 201), outlet.text
    ids: dict[str, int | str] = {"outlet_id": outlet.json()["id"]}
    rev = client.post(
        "/api/v1/reviews",
        json={"text": f"{secret} biryani was cold", "rating": 1, "platform": "zomato", "outlet_id": ids["outlet_id"]},
        headers=a,
    )
    assert rev.status_code in (200, 201, 202), rev.text
    with SessionLocal() as db:
        review = db.scalar(select(Review).where(Review.organization_id == a_org).order_by(Review.id.desc()))
        ids["review_id"] = review.id
        pay = Payment(
            organization_id=a_org,
            razorpay_payment_id=f"pay_iso_{uuid.uuid4().hex[:8]}",
            amount_paise=64900,
            status="captured",
            is_test=False,
        )
        db.add(pay)
        db.flush()
        ids["payment_id"] = pay.id
        ref = Refund(
            organization_id=a_org,
            refund_id=f"rf_iso_{uuid.uuid4().hex[:8]}",
            provider_payment_id=pay.razorpay_payment_id,
            amount_paise=1000,
            status="succeeded",
            refunded_at=datetime.now(UTC),
        )
        db.add(ref)
        db.flush()
        ids["refund_id"] = ref.id
        org = db.get(Organization, a_org)
        ids["req_id"] = books.open_request(db, org, 1, 1, 649, a_email).id
        db.commit()
    batches = client.get("/api/v1/imports", headers=a).json()
    items = batches["items"] if isinstance(batches, dict) else batches
    if items:
        ids["batch_id"] = items[0]["id"]
    t = client.post(
        "/api/v1/support/tickets",
        json={"category": "other", "subject": f"{secret} help", "message": f"{secret} please help"},
        headers=a,
    )
    assert t.status_code in (200, 201), t.text
    ids["ticket_id"] = t.json()["id"]
    inv = client.post(
        "/api/v1/team/invitations",
        json={"email": f"iso-{uuid.uuid4().hex[:6]}@example.com", "role": "manager"},
        headers=a,
    )
    if inv.status_code in (200, 201):
        ids["invite_id"] = inv.json()["id"]
    members = client.get("/api/v1/team", headers=a).json()["members"]
    ids["membership_id"] = members[0]["membership_id"]
    return {"a": a, "b": b, "a_org": a_org, "b_org": b_org, "ids": ids, "secret": secret}


# ID routes and the fixture key that fills each placeholder. Token routes are guarded by unguessable tokens instead.
ID_PARAMS = {
    "review_id",
    "outlet_id",
    "payment_id",
    "refund_id",
    "req_id",
    "batch_id",
    "ticket_id",
    "invite_id",
    "membership_id",
}
TOKEN_ROUTE = re.compile(r"\{token\}")


def _id_routes() -> list[tuple[str, str, str]]:
    out = []
    for method, path in _routes():
        if ADMIN.search(path) or TOKEN_ROUTE.search(path):
            continue
        names = re.findall(r"\{([^}]+)\}", path)
        if names:
            out.append((method, path, names[0]))
    return out


def test_every_id_route_is_covered():
    unknown = [f"{m} {p}" for m, p, n in _id_routes() if n not in ID_PARAMS]
    assert unknown == [], "New ID routes: add them to the isolation test:\n" + "\n".join(unknown)


def _body_for(path: str, ids: dict) -> dict:
    if "/status" in path:
        return {"status": "sent"}
    if "/messages" in path:
        return {"message": "hello"}
    if "post-reply" in path:
        return {"reply": "Thank you"}
    if "google-place" in path:
        return {"place_id": "ChIJx", "name": "x"}
    if path.startswith("/api/v1/reviews/"):
        return {"workflow_status": "replied"}
    if path.startswith("/api/v1/outlets/"):
        return {"name": "Taken over"}
    if path.startswith("/api/v1/team/members"):
        return {"role": "manager"}
    return {}


def test_other_restaurant_ids_are_not_found(client, two_restaurants):
    t = two_restaurants
    leaks = []
    skipped = [f"{m} {p}" for m, p, n in _id_routes() if n not in t["ids"]]
    assert skipped == [], f"Fixture didn't create a record for: {skipped}"
    for method, path, name in _id_routes():
        url = _fill(path, t["ids"][name])
        r = client.request(method, url, json=_body_for(path, t["ids"]), headers=t["b"])
        if r.status_code < 400 or t["secret"] in r.text:
            leaks.append(f"{method} {url} -> {r.status_code}")
    assert leaks == [], "Attacker reached the other restaurant:\n" + "\n".join(leaks)
    # ...and the victim's records are untouched and still theirs
    with SessionLocal() as db:
        o = db.get(Outlet, t["ids"]["outlet_id"])
        assert o.organization_id == t["a_org"] and o.is_active and t["secret"] in o.name
        assert db.get(Review, t["ids"]["review_id"]).workflow_status != "replied"
    # the owner of A still reaches their own records (so the test isn't passing because everything is broken)
    assert client.get(f"/api/v1/reviews/{t['ids']['review_id']}", headers=t["a"]).status_code == 200


def test_foreign_ids_in_query_body_and_headers_change_nothing(client, two_restaurants):
    t = two_restaurants
    a_outlet, secret, b = t["ids"]["outlet_id"], t["secret"], t["b"]
    reads = [
        f"/api/v1/reviews?outlet_id={a_outlet}",
        f"/api/v1/reviews?view=all&q={secret}",
        f"/api/v1/dashboard/overview?outlet_id={a_outlet}",
        f"/api/v1/insights/dishes?outlet_id={a_outlet}",
        f"/api/v1/competitors?outlet_id={a_outlet}",
        "/api/v1/outlets",
        "/api/v1/notifications",
        "/api/v1/support/tickets",
        "/api/v1/billing/receipts",
        "/api/v1/billing/credit-notes",
        "/api/v1/billing/invoice-requests",
        "/api/v1/account/export",
    ]
    for url in reads:
        r = client.get(url, headers=b)
        assert secret not in r.text, f"{url} showed the other restaurant's data"
    # Pretending to be an admin (or an agency) with the X-Org-Id header: their restaurant "doesn't exist"
    r = client.get("/api/v1/reviews?view=all", headers={**b, "X-Org-Id": str(t["a_org"])})
    assert r.status_code == 404 and secret not in r.text
    r = client.get("/api/v1/auth/me", headers={**b, "X-Org-Id": str(t["a_org"])})
    assert r.status_code == 404 and secret not in r.text
    assert client.get("/api/v1/auth/me", headers=b).json()["organization"]["id"] == t["b_org"]
    # Writing into their branch: the review lands in B's own restaurant, never on A's branch
    client.post(
        "/api/v1/reviews",
        json={"text": "planted review", "rating": 5, "platform": "google", "outlet_id": a_outlet},
        headers=b,
    )
    client.post(
        "/api/v1/review-requests", json={"numbers": ["9876543210"], "outlet_id": a_outlet, "consent": True}, headers=b
    )
    with SessionLocal() as db:
        planted = db.scalars(select(Review).where(Review.outlet_id == a_outlet)).all()
        assert all(p.organization_id == t["a_org"] for p in planted)
    # Ticket about their payment is refused
    r = client.post(
        "/api/v1/support/tickets",
        json={
            "category": "payment",
            "subject": "refund",
            "message": "please refund this",
            "payment_id": t["ids"]["payment_id"],
        },
        headers=b,
    )
    assert r.status_code == 404
    # Invites can't be scoped to their branches
    r = client.post(
        "/api/v1/team/invitations",
        json={"email": f"x-{uuid.uuid4().hex[:5]}@example.com", "role": "manager", "outlet_ids": [a_outlet]},
        headers=b,
    )
    if r.status_code in (200, 201):
        assert a_outlet not in (r.json().get("outlet_ids") or [])


def test_admin_can_open_any_restaurant_only_with_the_admin_account(client, two_restaurants):
    t = two_restaurants
    adm = _admin(client)
    r = client.get(f"/api/v1/reviews/{t['ids']['review_id']}", headers={**adm, "X-Org-Id": str(t["a_org"])})
    assert r.status_code == 200 and t["secret"] in r.text
    # the same request without the header is not a back door either
    assert client.get(f"/api/v1/reviews/{t['ids']['review_id']}", headers=adm).status_code in (403, 404)


def test_password_change_kills_every_old_session(client):
    h, _, email = _owner(client, "Iso Session Shop")
    stolen = dict(h)  # a copy of the access token someone grabbed
    assert client.get("/api/v1/auth/me", headers=stolen).status_code == 200
    import time

    time.sleep(1.1)  # tokens carry whole seconds
    r = client.post(
        "/api/v1/account/password",
        json={"current_password": "Strong#Pass1", "new_password": "Even#Stronger2x"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert client.get("/api/v1/auth/me", headers=stolen).status_code == 401
    fresh = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=fresh).json()["email"] == email
    time.sleep(1.1)
    assert client.post("/api/v1/account/sign-out-everywhere", headers=fresh).status_code == 200
    assert client.get("/api/v1/auth/me", headers=fresh).status_code == 401


def test_agency_switches_only_between_its_own_clients(client):
    agency, agency_org, _ = _owner(client, "Iso Spice PR Agency")
    other, other_org, _ = _owner(client, "Iso Not A Client")
    r = client.post("/api/v1/agency/restaurants", json={"name": "Iso Client Biryani", "city": "Salem"}, headers=agency)
    assert r.status_code == 201, r.text
    client_id = r.json()["id"]
    assert (
        client.post("/api/v1/agency/restaurants", json={"name": "iso client biryani"}, headers=agency).status_code
        == 409
    )
    me = client.get("/api/v1/auth/me", headers=agency).json()
    assert {o["id"] for o in me["organizations"]} == {agency_org, client_id}
    assert me["organization"]["id"] == agency_org  # first restaurant opens by default
    sw = {**agency, "X-Org-Id": str(client_id)}
    assert client.get("/api/v1/auth/me", headers=sw).json()["organization"]["name"] == "Iso Client Biryani"
    client.post(
        "/api/v1/reviews", json={"text": "Client salna was cold", "rating": 2, "platform": "zomato"}, headers=sw
    )
    with SessionLocal() as db:
        assert (
            db.scalar(select(Review.organization_id).where(Review.review_text == "Client salna was cold")) == client_id
        )
    # the agency's own restaurant doesn't see the client's review
    own = client.get("/api/v1/reviews?view=all", headers=agency).json()
    assert all(i["review_text"] != "Client salna was cold" for i in own["items"])
    # a restaurant the agency isn't in: 404, never its data
    assert client.get("/api/v1/reviews", headers={**agency, "X-Org-Id": str(other_org)}).status_code == 404
    rows = client.get("/api/v1/agency/restaurants", headers=agency).json()
    assert {r["id"] for r in rows["items"]} == {agency_org, client_id}
    assert [r["id"] for r in client.get("/api/v1/agency/restaurants", headers=other).json()["items"]] == [other_org]
