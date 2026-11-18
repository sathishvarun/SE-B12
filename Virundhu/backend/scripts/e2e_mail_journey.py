"""Live end-to-end check of the customer email journey. Run inside the api container: python scripts/e2e_mail_journey.py

Creates one clearly marked TEST restaurant whose owner email is a +tag on the company inbox, walks it through
register -> welcome -> reset -> password changed -> sign in -> payment link -> 5/4/2/1-day reminders -> suspension
(features off) -> payment (features back on) -> demo request -> support hand-over, and checks every email it sends.
Every sent email is saved to /backups/e2e/ as .eml + .html so it can be inspected.
"""

import os
import re
import secrets
import smtplib
import sys
from datetime import UTC, datetime, timedelta
from email import message_from_bytes, policy

sys.path.insert(0, os.getcwd())
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

OUT = os.environ.get("E2E_OUT", "/app/logs/e2e")
os.makedirs(OUT, exist_ok=True)
SENT: list = []
_orig = smtplib.SMTP.send_message


def _capture(self, msg, *a, **k):
    res = _orig(self, msg, *a, **k)
    n = len(SENT) + 1
    raw = msg.as_bytes()
    open(f"{OUT}/{n:02d}.eml", "wb").write(raw)
    parsed = message_from_bytes(raw, policy=policy.default)
    body = parsed.get_body(("html",))
    if body:
        open(f"{OUT}/{n:02d}.html", "w").write(body.get_content())
    SENT.append(parsed)
    return res


smtplib.SMTP.send_message = _capture
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> bool:
    RESULTS.append((name, bool(ok), note))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {note}", flush=True)
    return ok


def mails_since(i: int):
    return SENT[i:]


def find(i: int, needle: str):
    return next((m for m in SENT[i:] if needle.lower() in str(m["Subject"]).lower()), None)


def headers_ok(m, to: str) -> bool:
    return (
        m is not None
        and "virundhu@skminimart.com" in str(m["From"])
        and "virundhu.info@skminimart.com" in str(m["Reply-To"])
        and to.lower() in str(m["To"]).lower()
    )


def text_of(m) -> str:
    return m.get_body(("plain",)).get_content() if m else ""


tag = secrets.token_hex(3)
owner = f"info+test{tag}@skminimart.com"
pw1, pw2 = "Tst#" + secrets.token_urlsafe(12), "Tst#" + secrets.token_urlsafe(12)
c = TestClient(app, base_url="https://virundhu.sathishsakthivel.tech")
print(f"Test restaurant owner email: {owner}")
print(f"From address in use: {settings.EMAIL_FROM}   Reply-To: {settings.CONTACT_EMAIL}")

# 1 Register -> welcome
i = len(SENT)
r = c.post(
    "/api/v1/auth/register",
    json={
        "full_name": "Meena Krishnan",
        "organization_name": f"TEST Kaveri Mess {tag}",
        "email": owner,
        "password": pw1,
        "city": "Coimbatore",
        "phone": "9876543210",
        "outlets": 2,
        "accept_terms": True,
    },
)
check("1. Register a new restaurant", r.status_code in (200, 201), str(r.status_code))
m = find(i, "Welcome to Virundhu")
check("1a. Welcome email sent", m is not None, str(m["Subject"]) if m else "")
check("1b. From virundhu@skminimart.com, Reply-To virundhu.info@", headers_ok(m, owner))
t = text_of(m)
check("1c. Welcome lists the registration details", all(x in t for x in ("Meena", "Krishnan", owner, "Coimbatore")))
check("1d. Welcome has confirm-email and plans links", "verify-email" in t and "/app/billing" in t)
token = r.json().get("access_token") if r.status_code in (200, 201) else None

# 2 Forgot password -> reset email
i = len(SENT)
r = c.post("/api/v1/auth/forgot-password", json={"email": owner})
m = find(i, "Reset your Virundhu password")
check("2. Reset email sent", r.status_code == 200 and m is not None)
check("2a. Reset email headers", headers_ok(m, owner))
link = re.search(r"https?://\S+/reset-password\?token=(\S+)", text_of(m))
check("2b. Reset link points to the live site", bool(link) and settings.APP_URL in link.group(0))

# 3 Reset -> password changed email with sign-in link
i = len(SENT)
r = c.post("/api/v1/auth/reset-password", json={"token": link.group(1) if link else "x", "password": pw2})
check("3. New password saved through the link", r.status_code == 200, r.text[:80])
m = find(i, "password was changed")
check("3a. 'Password changed' email sent", m is not None)
check("3b. It asks them to sign in, with the sign-in link", "/login" in text_of(m) and "sign in" in text_of(m).lower())
r = c.post("/api/v1/auth/reset-password", json={"token": link.group(1) if link else "x", "password": pw1})
check("3c. The same reset link can't be used twice", r.status_code == 400)

# 4 Sign in with the new password (old one refused)
bad = c.post("/api/v1/auth/login", json={"email": owner, "password": pw1})
r = c.post("/api/v1/auth/login", json={"email": owner, "password": pw2})
check("4. Old password refused, new password signs in", bad.status_code == 401 and r.status_code == 200)
token = r.json().get("access_token", token)
H = {"Authorization": f"Bearer {token}"}

# 5 Payment link
r = c.post("/api/v1/billing/checkout", json={"outlets": 2, "months": 1}, headers=H)
url = r.json().get("checkout_url", "") if r.status_code == 200 else ""
check("5. Payment link opens Dodo checkout", r.status_code == 200 and url.startswith("https://"), url or r.text[:120])

# 6 Reminders 5/4/2/1 and suspension
from app.database import SessionLocal  # noqa: E402
from app.models import ActivityLog, Organization  # noqa: E402
from app.services import billing, plan_reminders, pricing  # noqa: E402
from app.services.autopilot import plan_active  # noqa: E402

db = SessionLocal()
org = db.query(Organization).filter_by(name=f"TEST Kaveri Mess {tag}").one()
end = org.trial_ends_at
noon = end.replace(hour=6, minute=30)
for d in (5, 4, 2, 1):
    i = len(SENT)
    plan_reminders.send_due(db, noon - timedelta(days=d), force_hours=True)
    m = find(i, f"ends in {d} day")
    check(f"6. Reminder {d} day(s) before trial ends", headers_ok(m, owner), str(m["Subject"]) if m else "missing")
i = len(SENT)
plan_reminders.send_due(db, end + timedelta(hours=3), force_hours=True)
m = find(i, "is suspended")
check("7. 'Account suspended' email to the owner", headers_ok(m, owner))
adm = next((x for x in SENT[i:] if settings.notify_email in str(x["To"]) and "suspended" in str(x["Subject"])), None)
check("7a. Admin alert 'Account suspended' to virundhu.info@", adm is not None)

# Make the trial really over, then check features are off
org.trial_ends_at = datetime.now(UTC) - timedelta(hours=1)
db.commit()
r = c.post("/api/v1/reviews", json={"text": "Test review", "rating": 4, "platform": "google"}, headers=H)
check("7b. While suspended, adding a review is blocked", r.status_code == 402, r.text[:90])
check("7c. While suspended, AI and alerts are off (plan not active)", not plan_active(db, org))

# 8 Payment lands -> receipt, everything back on
q = pricing.quote(2, 1) if hasattr(pricing, "quote") else billing.quote_or_error(2, 1)
i = len(SENT)
billing.activate(db, org.id, 2, 1, f"test_e2e_{tag}", q.total * 100)
db.refresh(org)
m = find(i, "Payment received: VR")
check("8. Payment confirmation email", headers_ok(m, owner), str(m["Subject"]) if m else "")
t = text_of(m)
check(
    "8a. Shows invoice no., months added, outlets, amount, payment ID",
    all(x in t for x in ("Invoice number", "Months added", "Outlets covered", "Amount paid", "Payment ID")),
)
adm = next((x for x in SENT[i:] if "reactivated" in str(x["Subject"]).lower()), None)
check("8b. Admin alert 'Account reactivated after payment'", adm is not None)
r = c.post("/api/v1/reviews", json={"text": "Lovely filter coffee, test", "rating": 5, "platform": "google"}, headers=H)
check("8c. After payment, adding a review works again", r.status_code in (200, 201, 202), str(r.status_code))
check("8d. Plan active again", plan_active(db, org))

# 9 Demo request -> virundhu.demo@
i = len(SENT)
r = c.post(
    "/api/v1/public/contact",
    json={
        "name": "Test Visitor",
        "restaurant": f"TEST Demo Hotel {tag}",
        "phone": "9840012345",
        "email": owner,
        "city": "Madurai",
        "outlets": 3,
        "message": "Test demo request",
    },
)
m = next((x for x in SENT[i:] if settings.demo_requests_email in str(x["To"])), None)
check("9. Demo request emails virundhu.demo@skminimart.com", r.status_code == 201 and m is not None)

# 10 Support hand-over -> virundhu.info@
i = len(SENT)
r = c.post(
    "/api/v1/help/handover", json={"message": "Test: please call me about billing", "topic": "payment"}, headers=H
)
m = next((x for x in SENT[i:] if settings.notify_email in str(x["To"])), None)
check("10. Support message emails virundhu.info@skminimart.com", r.status_code == 201 and m is not None)

cnt = db.query(ActivityLog).filter(ActivityLog.restaurant == org.name).count()
check("11. Admin console log has this restaurant's events", cnt > 0, f"{cnt} events")
db.close()

print("\nEMAILS SENT:")
for n, x in enumerate(SENT, 1):
    print(f"{n:02d} | To: {x['To']} | From: {x['From']} | Reply-To: {x['Reply-To']} | {x['Subject']}")
ok = sum(1 for r in RESULTS if r[1])
print(f"\nRESULT: {ok}/{len(RESULTS)} checks passed. Saved emails: {OUT}")
