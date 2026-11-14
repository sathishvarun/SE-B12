"""Walk through the whole Sathish CRM flow against the local API with sample data.

Usage (from the project folder, with the app running):
    python3 scripts/demo_walkthrough.py .env

Needs the `requests` package. Each run creates new demo users, so it is safe to repeat.
"""

import base64
import hashlib
import hmac
import json
import sys
import time
import uuid
from datetime import date, timedelta

import requests

API = "http://localhost:8000/api/v1"
STAMP = int(time.time())
PASSWORD = "DemoPass123!"


def step(title: str) -> None:
    print(f"\n=== {title} ===")


def call(session: requests.Session, method: str, path: str, expect: int, **kwargs) -> dict:
    r = session.request(method, API + path, **kwargs)
    ok = "OK " if r.status_code == expect else "FAIL"
    print(f"  [{ok}] {method} {path} -> {r.status_code} (expected {expect})")
    if r.status_code != expect:
        print("        ", r.text[:300])
    try:
        return r.json()
    except ValueError:
        return {}


def new_user(name: str) -> tuple[requests.Session, str]:
    email = f"{name.lower()}.{STAMP}@example.com"
    s = requests.Session()
    call(s, "POST", "/auth/register", 201, json={"email": email, "password": PASSWORD, "full_name": name})
    tokens = call(s, "POST", "/auth/login", 200, json={"email": email, "password": PASSWORD})
    s.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return s, email


def signed_webhook(secret: str, payload: dict) -> tuple[dict, bytes]:
    body = json.dumps(payload).encode()
    msg_id, ts = f"msg_{uuid.uuid4().hex}", str(int(time.time()))
    key = base64.b64decode(secret.removeprefix("whsec_"))
    sig = base64.b64encode(hmac.new(key, f"{msg_id}.{ts}.".encode() + body, hashlib.sha256).digest()).decode()
    headers = {"webhook-id": msg_id, "webhook-timestamp": ts,
               "webhook-signature": f"v1,{sig}", "Content-Type": "application/json"}
    return headers, body


def main() -> None:
    env = dict(line.split("=", 1) for line in open(sys.argv[1]).read().splitlines()
               if "=" in line and not line.startswith("#"))
    today = date.today()

    step("1. Sign up + log in")
    s, email = new_user("Priya")
    me = call(s, "GET", "/auth/me", 200)
    print(f"  Logged in as {email} (user id {me['id']})")

    step("2. Tags + contacts")
    vip = call(s, "POST", "/tags", 201, json={"name": "VIP"})
    call(s, "POST", "/tags", 409, json={"name": "VIP"})  # tag names are unique per seller
    c1 = call(s, "POST", "/contacts", 201, json={"name": "Arun Kumar", "email": "arun@acme.in",
              "company": "Acme Traders", "phone": "+91 98400 11111", "tag_ids": [vip["id"]]})
    call(s, "POST", "/contacts", 201, json={"name": "Meena Raj", "company": "Bright Tiles"})
    call(s, "POST", "/contacts", 422, json={"name": "Bad Email", "email": "not-an-email"})

    step("3. Leads: create, update status, convert")
    l1 = call(s, "POST", "/leads", 201, json={"name": "Karthik S", "email": "karthik@sunsolar.in",
              "company": "Sun Solar", "source": "referral"})
    call(s, "POST", "/leads", 201, json={"name": "Divya N", "source": "website"})
    call(s, "PATCH", f"/leads/{l1['id']}/status", 200, json={"status": "qualified"})
    conv = call(s, "POST", f"/leads/{l1['id']}/convert", 201, json={
        "deal_title": "Sun Solar - 50 panels", "deal_value": "250000.00",
        "expected_close_date": str(today + timedelta(days=30))})
    print("  Convert response keys:", list(conv)[:6])
    call(s, "POST", f"/leads/{l1['id']}/convert", 409, json={"deal_title": "again", "deal_value": 1})

    step("4. Deals: create and move through the pipeline")
    d1 = call(s, "POST", "/deals", 201, json={"title": "Acme bulk order", "contact_id": c1["id"],
              "value": "120000.50", "currency": "INR", "stage": "prospect"})
    for stage in ["proposal", "negotiation", "won"]:
        moved = call(s, "PATCH", f"/deals/{d1['id']}/stage", 200, json={"stage": stage, "position": 0})
    print(f"  Deal is now '{moved.get('stage')}', closed_at = {moved.get('closed_at')}")
    reopened = call(s, "PATCH", f"/deals/{d1['id']}/stage", 200, json={"stage": "negotiation", "position": 0})
    print(f"  Moved back to open stage, closed_at = {reopened.get('closed_at')}")
    call(s, "POST", "/deals", 422, json={"title": "Negative", "contact_id": c1["id"], "value": -5})

    step("5. Tasks: overdue, linked, complete")
    call(s, "POST", "/tasks", 201, json={"title": "Call Arun about invoice", "priority": "high",
         "due_date": str(today - timedelta(days=2)), "contact_id": c1["id"]})
    t2 = call(s, "POST", "/tasks", 201, json={"title": "Send proposal PDF", "priority": "medium",
              "due_date": str(today + timedelta(days=1)), "deal_id": d1["id"]})
    call(s, "POST", "/tasks", 400, json={"title": "Two links", "contact_id": c1["id"], "deal_id": d1["id"]})
    call(s, "PATCH", f"/tasks/{t2['id']}/complete", 200)

    step("6. Attachments: allowed and blocked file types")
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    att = call(s, "POST", "/attachments", 201, files={"file": ("quote.pdf", pdf, "application/pdf")},
               data={"deal_id": str(d1["id"])})
    call(s, "POST", "/attachments", 400, files={"file": ("virus.exe", b"MZ...", "application/octet-stream")},
         data={"deal_id": str(d1["id"])})
    if att.get("id"):
        call(s, "GET", f"/attachments/{att['id']}", 200)

    step("7. Dashboard")
    summary = call(s, "GET", "/dashboard/summary", 200)
    print("  Summary:", json.dumps(summary)[:400])

    step("8. Data isolation: another seller can't see Priya's data")
    s2, _ = new_user("Ravi")
    call(s2, "GET", f"/contacts/{c1['id']}", 404)
    call(s2, "GET", f"/deals/{d1['id']}", 404)

    step("9. Billing: checkout (real Dodo test API) + simulated webhooks")
    sub = call(s, "GET", "/billing/subscription", 200)
    print(f"  Plan before: {sub.get('plan')} / {sub.get('status')}")
    chk = call(s, "POST", "/billing/checkout", 200)
    print(f"  Dodo checkout URL: {chk.get('checkout_url')}")

    secret = env.get("DODO_PAYMENTS_WEBHOOK_SECRET", "")
    fake = requests.post(API + "/billing/webhook", json={"type": "subscription.active"})
    print(f"  Unsigned webhook -> {fake.status_code} (expected 401)")
    sub_id = f"sub_demo_{STAMP}"
    for event in ["subscription.active", "subscription.cancelled"]:
        headers, body = signed_webhook(secret, {"type": event, "data": {
            "subscription_id": sub_id, "customer": {"customer_id": f"cus_demo_{STAMP}"},
            "metadata": {"user_id": str(me["id"])},
            "next_billing_date": f"{today + timedelta(days=30)}T00:00:00Z"}})
        r = requests.post(API + "/billing/webhook", data=body, headers=headers)
        sub = call(s, "GET", "/billing/subscription", 200)
        print(f"  Signed {event} -> {r.status_code}; plan now: {sub.get('plan')} / {sub.get('status')}")

    print(f"\nDone. Log in to the app as {email} / {PASSWORD} to see it in the UI.")
    print("  (http://localhost:5173 with docker-compose.dev.yml, http://localhost:3000 with docker-compose.yml)")


if __name__ == "__main__":
    main()
