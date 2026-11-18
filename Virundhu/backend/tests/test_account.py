"""Forgot / reset / change password, export and delete (the owner's data rights), signup consent, security headers."""

import uuid
from unittest.mock import patch

from app.database import SessionLocal
from app.models import Organization, Review, User

PW = "Strong#Pass1"


def _register(client, accept=True):
    email = f"acc-{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Acc Owner",
            "organization_name": "Acc Mess",
            "email": email,
            "password": PW,
            "accept_terms": accept,
        },
    )
    return email, res


def test_signup_needs_consent_and_records_it(client):
    _, res = _register(client, accept=False)
    assert res.status_code == 422
    email, res = _register(client)
    assert res.status_code == 201
    with SessionLocal() as db:
        assert db.query(User).filter_by(email=email).one().terms_accepted_at is not None


def test_forgot_and_reset_password(client):
    email, res = _register(client)
    refresh = client.cookies.get("vr_session")
    sent = {}
    with patch("app.routers.account.send_email", side_effect=lambda to, s, text: sent.update(text=text) or True):
        same1 = client.post("/api/v1/auth/forgot-password", json={"email": email}).json()
        same2 = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}).json()
    assert same1 == same2  # no hint whether the account exists
    token = sent["text"].split("token=")[1].split()[0]
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "password": "short"}).status_code == 422
    assert (
        client.post("/api/v1/auth/reset-password", json={"token": token, "password": "New#Pass123"}).status_code == 200
    )
    assert (
        client.post("/api/v1/auth/reset-password", json={"token": token, "password": "New#Pass123"}).status_code == 400
    )
    assert client.post("/api/v1/auth/login", json={"email": email, "password": PW}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "New#Pass123"}).status_code == 200
    client.cookies.clear()
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401  # signed out


def test_change_password(client):
    _, res = _register(client)
    h = {"Authorization": f"Bearer {res.json()['access_token']}"}
    bad = client.post(
        "/api/v1/account/password", json={"current_password": "wrong", "new_password": "New#Pass123"}, headers=h
    )
    assert bad.status_code == 400
    ok = client.post(
        "/api/v1/account/password", json={"current_password": PW, "new_password": "New#Pass123"}, headers=h
    )
    assert ok.status_code == 200


def test_export_and_delete_everything(client):
    email, res = _register(client)
    h = {"Authorization": f"Bearer {res.json()['access_token']}"}
    org_id = res.json()["user"]["organization"]["id"]
    client.post("/api/v1/reviews", json={"text": "தோசை சூப்பர்", "rating": 5, "platform": "google"}, headers=h)
    csv = client.get("/api/v1/account/export", headers=h)
    assert csv.status_code == 200 and "தோசை சூப்பர்" in csv.text and "attachment" in csv.headers["content-disposition"]

    assert (
        client.post("/api/v1/account/delete", json={"confirm_name": "wrong", "password": PW}, headers=h).status_code
        == 400
    )
    assert (
        client.post("/api/v1/account/delete", json={"confirm_name": "Acc Mess", "password": "x"}, headers=h).status_code
        == 400
    )
    assert (
        client.post("/api/v1/account/delete", json={"confirm_name": "acc mess", "password": PW}, headers=h).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.get(Organization, org_id) is None
        assert db.query(Review).filter_by(organization_id=org_id).count() == 0
        assert db.query(User).filter_by(email=email).count() == 0


def test_security_headers(client):
    res = client.get("/api/v1/public/config")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["cache-control"] == "no-store"


def test_admin_sees_activity(client):
    from app.config import settings

    email, res = _register(client)
    h = {"Authorization": f"Bearer {res.json()['access_token']}"}
    client.post("/api/v1/account/password", json={"current_password": PW, "new_password": "New#Pass123"}, headers=h)
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "New#Pass123"}).json()
    h = {"Authorization": f"Bearer {login['access_token']}"}
    client.post("/api/v1/account/delete", json={"confirm_name": "Acc Mess", "password": "New#Pass123"}, headers=h)
    admin = client.post(
        "/api/v1/auth/login", json={"email": settings.SUPERADMIN_EMAIL, "password": settings.SUPERADMIN_PASSWORD}
    ).json()["access_token"]
    ah = {"Authorization": f"Bearer {admin}"}
    mine = [a for a in client.get("/api/v1/admin/activity", headers=ah).json() if a["user_email"] == email]
    assert {a["kind"] for a in mine} == {"signup", "login", "password_changed", "account_deleted"}
    assert any(e["kind"] == "account_deleted" for e in client.get("/api/v1/admin/events", headers=ah).json())
    assert client.get("/api/v1/admin/activity", headers=h).status_code in (401, 403)


def test_retention_deletes_only_old_data(client):
    """Guest-number hashes and contact messages older than a year are deleted; recent ones stay."""
    from datetime import UTC, datetime, timedelta

    from app.database import SessionLocal
    from app.models import Lead, Organization, ReviewRequest
    from app.services.retention import purge

    with SessionLocal() as db:
        org = db.query(Organization).first()
        old = datetime.now(UTC) - timedelta(days=400)
        a = ReviewRequest(organization_id=org.id, phone_hash="a" * 64, channel="whatsapp_link", created_at=old)
        b = ReviewRequest(organization_id=org.id, phone_hash="b" * 64, channel="whatsapp_link")
        lead = Lead(name="Old", restaurant="Old Mess", created_at=old)
        db.add_all([a, b, lead])
        db.commit()
        ids = (a.id, b.id, lead.id)
        counts = purge(db)
        assert counts["review_requests"] >= 1 and counts["contact_messages"] >= 1
        assert db.get(ReviewRequest, ids[0]) is None
        assert db.get(ReviewRequest, ids[1]) is not None
        assert db.get(Lead, ids[2]) is None
        db.delete(db.get(ReviewRequest, ids[1]))
        db.commit()


def test_trial_reminders_go_once_at_4_3_2_1_days_and_when_ended(client):
    """A new trial gets reminders 4, 3, 2 and 1 days before the end and once after; never twice; never at night."""
    from datetime import timedelta

    from app.database import SessionLocal
    from app.models import Notification, Organization, PlanReminder
    from app.services.plan_reminders import due, send_due

    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Trial Owner",
            "organization_name": "Reminder Mess",
            "email": f"reminder.owner.{__import__('uuid').uuid4().hex[:6]}@gmail.com",
            "password": "Tiffin#Hall2026",
            "city": "Coimbatore",
            "accept_terms": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name="Reminder Mess").one()
        end = org.trial_ends_at
        noon = end.replace(hour=6, minute=30)  # 12:00 India time on the end date
        assert due(end, noon - timedelta(days=10)) is None  # day 4 of the trial: nothing yet
        assert due(end, noon - timedelta(days=4)) == 4
        assert due(end, noon - timedelta(days=1)) == 1
        assert due(end, end + timedelta(hours=2)) == 0  # ended
        assert due(end, end + timedelta(days=5)) is None  # long ended: stop
        night = (noon - timedelta(days=3)).replace(hour=18)  # 11:30 pm India time
        assert send_due(db, night) == 0
        for days in (4, 3, 2, 1):
            assert send_due(db, noon - timedelta(days=days)) >= 1
            assert send_due(db, noon - timedelta(days=days)) == 0  # same reminder never twice
        assert send_due(db, end + timedelta(hours=3)) >= 1
        kinds = sorted(x.days_left for x in db.query(PlanReminder).filter_by(organization_id=org.id))
        assert kinds == [0, 1, 2, 3, 4]
        bell = db.query(Notification).filter_by(organization_id=org.id).all()
        assert any("ends in 3 days" in n.title for n in bell) and any("has ended" in n.title for n in bell)
        from app.models import Membership, User

        uids = [m.user_id for m in db.query(Membership).filter_by(organization_id=org.id)]
        db.query(Organization).filter_by(id=org.id).delete()
        db.query(User).filter(User.id.in_(uids)).delete()
        db.commit()


def test_admin_excel_and_test_account_cleanup(client):
    """Admin downloads customers as Excel; test accounts are found and deleted; real ones are protected."""
    import io
    import uuid

    from openpyxl import load_workbook

    tag = uuid.uuid4().hex[:6]
    real_email, test_email = f"sangeetha.{tag}@gmail.com", f"test{tag}@test.com"

    def reg(name, email):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Owner",
                "organization_name": name,
                "email": email,
                "password": "Swift#Mess2026",
                "accept_terms": True,
            },
        )
        assert r.status_code in (200, 201), r.text

    reg(f"Sangeetha Mess {tag}", real_email)
    reg(f"Quick Bites {tag}", test_email)
    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    h = {"Authorization": "Bearer " + admin.json()["access_token"]}

    x = client.get("/api/v1/admin/export.xlsx", headers=h)
    assert x.status_code == 200 and "spreadsheetml" in x.headers["content-type"]
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == ["Restaurants", "People", "Payments", "Demo requests"]
    rows = list(wb["Restaurants"].iter_rows(min_row=2, values_only=True))
    assert any(r[1] == f"Sangeetha Mess {tag}" for r in rows) and any(r[1] == f"Quick Bites {tag}" for r in rows)

    tests = {t["name"]: t for t in client.get("/api/v1/admin/test-accounts", headers=h).json()}
    assert f"Quick Bites {tag}" in tests and f"Sangeetha Mess {tag}" not in tests
    real_id = next(r[0] for r in rows if r[1] == f"Sangeetha Mess {tag}")
    test_id = tests[f"Quick Bites {tag}"]["id"]
    url = "/api/v1/admin/test-accounts/delete"
    assert client.post(url, headers=h, json={"ids": [real_id], "confirm": "DELETE"}).status_code == 400
    assert client.post(url, headers=h, json={"ids": [test_id], "confirm": "yes"}).status_code == 400
    assert client.post(url, headers=h, json={"ids": [test_id], "confirm": "DELETE"}).json() == {"deleted": 1}
    gone = client.post("/api/v1/auth/login", json={"email": test_email, "password": "Swift#Mess2026"})
    assert gone.status_code == 401

    owner = client.post("/api/v1/auth/login", json={"email": real_email, "password": "Swift#Mess2026"})
    oh = {"Authorization": "Bearer " + owner.json()["access_token"]}
    assert client.get("/api/v1/admin/export.xlsx", headers=oh).status_code == 403
    assert client.get("/api/v1/admin/backups", headers=h).json()["folder"].endswith("backups")
    client.post(
        "/api/v1/account/delete",
        headers=oh,
        json={"confirm_name": f"Sangeetha Mess {tag}", "password": "Swift#Mess2026"},
    )


def test_admin_revenue_dashboard(client):
    """Money by month, active plans, renewals due, trials that may pay; admins only; every trial is 14 days."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.database import SessionLocal
    from app.models import Organization
    from app.services import billing, pricing

    tag = uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Paying Owner",
            "organization_name": f"Paid Mess {tag}",
            "email": f"paid.{tag}@gmail.com",
            "password": "Swift#Mess2026",
            "accept_terms": True,
        },
    )
    me = r.json()["user"]
    ends = datetime.fromisoformat(me["organization"]["trial_ends_at"])
    assert timedelta(days=13, hours=23) < ends - datetime.now(UTC) <= timedelta(days=14)  # exactly 14 days

    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    h = {"Authorization": "Bearer " + admin.json()["access_token"]}
    before = client.get("/api/v1/admin/revenue", headers=h).json()
    assert any(t["restaurant"] == f"Paid Mess {tag}" for t in before["trials_ending"]) is False  # 14 days away: not yet

    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name=f"Paid Mess {tag}").one()
        q = pricing.quote(3, 1)
        assert billing.activate(db, org.id, 3, 1, f"pay_{tag}", q.total * 100)
    after = client.get("/api/v1/admin/revenue", headers=h).json()
    assert after["all_time"] - before["all_time"] == q.total
    assert after["this_month"] - before["this_month"] == q.total
    assert after["paying_customers"] == before["paying_customers"] + 1
    assert after["monthly_recurring"] > before["monthly_recurring"]
    row = next(u for u in after["upcoming"] if u["restaurant"] == f"Paid Mess {tag}")
    assert row["amount"] == q.total and row["outlets"] == 3 and row["kind"] == "renewal"
    assert after["expected_next_90"] >= q.total
    assert len(after["months"]) == 15 and sum(m["expected"] for m in after["months"]) >= q.total
    assert after["recent"][0]["restaurant"] == f"Paid Mess {tag}" and after["recent"][0]["covers_until"]

    owner = client.post("/api/v1/auth/login", json={"email": f"paid.{tag}@gmail.com", "password": "Swift#Mess2026"})
    assert (
        client.get(
            "/api/v1/admin/revenue", headers={"Authorization": "Bearer " + owner.json()["access_token"]}
        ).status_code
        == 403
    )


def test_password_guessing_is_blocked_and_weak_passwords_refused(client):
    """5 wrong passwords lock the email for 15 minutes; easy passwords and names in passwords are refused."""
    import uuid

    tag = uuid.uuid4().hex[:6]
    email = f"guard.{tag}@gmail.com"
    body = {"full_name": "Meena Raj", "organization_name": "Kovai Kitchen", "email": email, "accept_terms": True}
    for weak in ("password123", "12345678", "aaaaaaaa", "kovaikitchen1", "meena#2026x"):
        r = client.post("/api/v1/auth/register", json={**body, "password": weak})
        assert r.status_code == 422, weak
    assert client.post("/api/v1/auth/register", json={**body, "password": "Tiffin#Hall2026"}).status_code == 201
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"email": email, "password": "Wrong#Guess99"}).status_code == 401
    locked = client.post("/api/v1/auth/login", json={"email": email, "password": "Tiffin#Hall2026"})
    assert locked.status_code == 429  # even the right password waits 15 minutes
    # unknown emails get exactly the same answer as wrong passwords
    nobody = client.post("/api/v1/auth/login", json={"email": f"nobody.{tag}@gmail.com", "password": "Wrong#Guess99"})
    assert nobody.status_code == 401 and nobody.json()["detail"] == "That email and password don't match."


def test_unpaid_accounts_pause_and_come_back_the_moment_payment_lands(client):
    """Like a phone bill: when a trial or paid plan ends, changes stop and no AI is spent; paying reopens at once."""
    import uuid
    from datetime import UTC, datetime, timedelta

    from app.database import SessionLocal
    from app.models import Organization, Review, Subscription
    from app.services import billing, pricing
    from app.services.analysis import analyze_reviews

    tag = uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Late Payer",
            "organization_name": f"Chain {tag}",
            "email": f"late.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    paste = {"text": "Food was cold and late", "rating": 2, "platform": "zomato"}
    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name=f"Chain {tag}").one()
        org.trial_ends_at = datetime.now(UTC) - timedelta(hours=1)  # trial over, not paid
        db.commit()
        org_id = org.id
    blocked = client.post("/api/v1/reviews", headers=h, json=paste)
    assert blocked.status_code == 402
    with SessionLocal() as db:  # a review arriving now (e.g. QR) is kept but not sent to the AI
        rv = Review(
            organization_id=org_id,
            external_id=f"QR-{tag}",
            platform="direct",
            rating=2,
            review_date=datetime.now(UTC).date(),
            review_text="Cold food",
            analysis_status="pending",
            workflow_status="new",
        )
        db.add(rv)
        db.commit()
        out = analyze_reviews(db, org_id, [rv.id])
        assert out.get("waiting_for_payment") == 1
        db.refresh(rv)
        assert rv.analysis_status == "pending_quota"
        q = pricing.quote(25, 1)  # big chain plan
        assert billing.activate(db, org_id, 25, 1, f"pay_{tag}", q.total * 100)
    assert client.post("/api/v1/reviews", headers=h, json=paste).status_code != 402  # open again at once
    with SessionLocal() as db:  # the chain plan also pauses when it runs out (this was missed before)
        sub = db.query(Subscription).filter_by(organization_id=org_id).one()
        sub.current_period_end = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    assert client.post("/api/v1/reviews", headers=h, json=paste).status_code == 402


def test_signup_to_receipt_to_monthly_report(client):
    """Welcome email with trial dates and links; billing details at checkout; numbered receipt emailed; trial reminders
    stop once paid; admin sees the receipt; monthly report and plan mix count it."""
    import io
    import uuid
    from datetime import UTC, datetime, timedelta
    from unittest.mock import patch

    from openpyxl import load_workbook

    from app.database import SessionLocal
    from app.models import Organization, User
    from app.services import billing, pricing
    from app.services.plan_reminders import send_due

    tag = uuid.uuid4().hex[:6]
    sent = []
    grab = lambda to, subject, text, *a, **k: sent.append((to, subject, text)) or True  # noqa: E731
    with patch("app.services.welcome.send_email", side_effect=grab):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Lakshmi Narayanan",
                "organization_name": f"Arusuvai {tag}",
                "email": f"lakshmi.{tag}@gmail.com",
                "password": "Tiffin#Hall2026",
                "city": "Coimbatore",
                "phone": "9876543210",
                "outlets": 2,
                "accept_terms": True,
            },
        )
    assert r.status_code == 201
    to, subject, text = sent[0]
    assert to == [f"lakshmi.{tag}@gmail.com"] and "Lakshmi" in subject
    assert "Coimbatore" in text and "9876543210" in text and "ends on" in text and "/app/billing" in text
    link = text.split("confirm this is your email address: ")[1].split()[0]
    token = link.split("token=")[1]
    v = client.get(f"/api/v1/auth/verify-email?token={token}", follow_redirects=False)
    assert v.status_code in (302, 307) and "email_confirmed=1" in v.headers["location"]
    with SessionLocal() as db:
        assert db.query(User).filter_by(email=f"lakshmi.{tag}@gmail.com").one().is_verified

    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    bad = client.post("/api/v1/billing/checkout", headers=h, json={"outlets": 2, "months": 3, "gstin": "123"})
    assert bad.status_code == 422
    with patch("app.routers.billing.dodo_billing.start_checkout", return_value="https://checkout.example/x"):
        ok = client.post(
            "/api/v1/billing/checkout",
            headers=h,
            json={
                "outlets": 2,
                "months": 3,
                "company_name": "Arusuvai Foods Pvt Ltd",
                "gstin": "33abcde1234f1z5",
                "address": "12 Cross Cut Road, Gandhipuram, Coimbatore 641012",
            },
        )
    assert ok.status_code == 200, ok.text

    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name=f"Arusuvai {tag}").one()
        assert org.gstin == "33ABCDE1234F1Z5" and org.billing_name == "Arusuvai Foods Pvt Ltd"
        org_id, trial_end = org.id, org.trial_ends_at
        q = pricing.quote(2, 3)
        mails = []
        with patch("app.services.receipts.send_email", side_effect=lambda to, s, t, *a, **k: mails.append(s) or True):
            assert billing.activate(db, org_id, 2, 3, f"pay_{tag}", q.total * 100)
        assert mails and mails[0].startswith("Payment received: VR-")
        # paid: no more "trial ends" reminders for this restaurant
        from app.models import PlanReminder

        send_due(db, trial_end.replace(hour=6, minute=30) - timedelta(days=3))
        assert not db.query(PlanReminder).filter_by(organization_id=org_id, kind="trial").count()

    mine = client.get("/api/v1/billing/receipts", headers=h).json()
    rc = mine[0]
    assert rc["invoice_no"].startswith("VR-") and rc["bill_gstin"] == "33ABCDE1234F1Z5"
    assert "641012" in rc["bill_address"] and rc["outlets"] == 2 and rc["months"] == 3 and rc["amount"] == q.total

    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    ah = {"Authorization": "Bearer " + admin.json()["access_token"]}
    assert client.get(f"/api/v1/billing/receipts/{rc['id']}", headers=ah).json()["invoice_no"] == rc["invoice_no"]
    other = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Owner",
            "organization_name": f"Else {tag}",
            "email": f"else.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    oh = {"Authorization": "Bearer " + other.json()["access_token"]}
    assert client.get(f"/api/v1/billing/receipts/{rc['id']}", headers=oh).status_code == 404

    rev = client.get("/api/v1/admin/revenue", headers=ah).json()
    assert rev["recent"][0]["invoice_no"] == rc["invoice_no"]
    assert client.get("/api/v1/admin/plan-mix", headers=ah).json()["by_months"]["3"] >= 1
    month = datetime.now(UTC).strftime("%Y-%m")
    x = client.get(f"/api/v1/admin/reports/monthly.xlsx?month={month}", headers=ah)
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.sheetnames == [
        "Summary",
        "Payments",
        "Plan mix",
        "Renewals due next month",
        "Idle accounts",
        "Deleted accounts",
        "New sign-ups",
    ]
    pays = list(wb["Payments"].iter_rows(min_row=2, values_only=True))
    assert any(p[0] == rc["invoice_no"] and p[4] == "33ABCDE1234F1Z5" for p in pays)
    mix = {row[0]: row[1] for row in wb["Plan mix"].iter_rows(min_row=2, values_only=True)}
    assert mix["3 months"] >= 1
    assert client.get(f"/api/v1/admin/reports/monthly.xlsx?month={month}", headers=oh).status_code == 403


def test_delete_shows_balance_emails_owner_and_tells_admin(client):
    """Before deleting: balance due (0) and unused paid days; after: owner gets an email, admin sees it in Deleted."""
    import uuid
    from unittest.mock import patch

    from app.database import SessionLocal
    from app.models import Organization
    from app.services import billing, pricing

    tag = uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Leaving Owner",
            "organization_name": f"Bye Mess {tag}",
            "email": f"bye.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name=f"Bye Mess {tag}").one()
        q = pricing.quote(1, 3)
        billing.activate(db, org.id, 1, 3, f"pay_{tag}", q.total * 100)
    check = client.get("/api/v1/account/delete-check", headers=h).json()
    assert check["balance_due"] == 0 and check["paid_days_left"] >= 89 and check["last_payment"]["amount"] == q.total
    mails = []
    with patch(
        "app.routers.account.send_email", side_effect=lambda to, s, t, *a, **k: mails.append((to, s, t)) or True
    ):
        d = client.post(
            "/api/v1/account/delete", headers=h, json={"confirm_name": f"Bye Mess {tag}", "password": "Tiffin#Hall2026"}
        )
    assert d.status_code == 200
    mine = [m for m in mails if m[0] == [f"bye.{tag}@gmail.com"]]
    assert mine and "has been deleted" in mine[0][1] and "no balance to pay" in mine[0][2]
    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    ah = {"Authorization": "Bearer " + admin.json()["access_token"]}
    gone = client.get("/api/v1/admin/activity", headers=ah, params={"kind": "account_deleted"}).json()
    row = next(a for a in gone if a["restaurant"] == f"Bye Mess {tag}")
    assert "days unused" in row["detail"] and "balance due Rs 0" in row["detail"]


def test_maps_dish_staff_insights_and_widget(client):
    """Outlets on Google Maps get directions (and a map with a key); dishes/staff add up; the widget is honest."""
    import uuid
    from datetime import date

    from app.database import SessionLocal
    from app.models import Organization, Review, ReviewAnalysis

    tag = uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Insight Owner",
            "organization_name": f"Kovai Biryani {tag}",
            "email": f"insight.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    a = client.post(
        "/api/v1/outlets",
        headers=h,
        json={
            "name": "RS Puram",
            "city": "Coimbatore",
            "address": "12 DB Road",
            "google_maps_url": "https://maps.app.goo.gl/abc123",
        },
    ).json()
    b = client.post("/api/v1/outlets", headers=h, json={"name": "Peelamedu", "city": "Coimbatore"}).json()
    assert a["on_google_maps"] and a["directions_url"] == "https://maps.app.goo.gl/abc123"  # the exact place
    assert not b["on_google_maps"] and b["map_embed_url"] is None

    with SessionLocal() as db:
        org = db.query(Organization).filter_by(name=f"Kovai Biryani {tag}").one()
        rows = [
            (
                5,
                "Chicken biryani was superb and Ravi served us so well",
                [("chicken biryani", "positive")],
                [("Ravi", "positive")],
            ),
            (
                2,
                "Chicken Biryani too salty today, delivery person was rude",
                [("chicken biryani", "negative")],
                [("delivery person", "negative")],
            ),
            (4, "Loved the parotta and salna, great evening with family", [("parotta", "positive")], []),
        ]
        for i, (rating, text, dishes, staff) in enumerate(rows):
            rv = Review(
                organization_id=org.id,
                outlet_id=a["id"],
                external_id=f"I{tag}{i}",
                platform="google",
                rating=rating,
                review_date=date.today(),
                review_text=text,
                analysis_status="analyzed",
                workflow_status="new",
            )
            db.add(rv)
            db.flush()
            db.add(
                ReviewAnalysis(
                    review_id=rv.id,
                    status="analyzed",
                    sentiment="neutral",
                    dishes=[{"name": n, "sentiment": s} for n, s in dishes],
                    staff=[{"name": n, "sentiment": s} for n, s in staff],
                )
            )
        db.commit()
    listed = client.get("/api/v1/outlets", headers=h).json()
    token = listed[0]["feedback_url"].split("/f/")[1].split("?")[0]

    m = client.get("/api/v1/insights/mentions", headers=h).json()
    biryani = next(d for d in m["dishes"] if d["name"] == "chicken biryani")
    assert biryani["mentions"] == 2 and biryani["positive"] == 1 and biryani["negative"] == 1 and biryani["score"] == 0
    assert biryani["outlets"][0]["name"] == "RS Puram" and len(biryani["examples"]) == 2
    assert {s["name"] for s in m["staff"]} == {"ravi", "delivery person"}

    w = client.get(f"/api/v1/public/widget/{token}").json()
    assert w["count"] == 3 and w["average"] == round((5 + 2 + 4) / 3, 1)  # true average includes the 2-star review
    assert all(x["rating"] >= 4 for x in w["reviews"]) and "4 and 5 star" in w["shown"]
    assert [x["name"] for x in w["branches"]] == ["RS Puram"]
    assert client.get("/api/v1/public/widget/not-a-token").status_code == 404


def test_sign_in_log_tickets_and_daily_digest(client):
    """Sign-ins and wrong passwords are logged with IP and device; tickets flow owner -> admin -> owner with emails;
    the admin can download the log; the daily summary lists who signed in."""
    import asyncio
    import io
    import uuid
    from unittest.mock import patch

    from openpyxl import load_workbook

    tag = uuid.uuid4().hex[:6]
    email = f"logs.{tag}@gmail.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Log Owner",
            "organization_name": f"Log Mess {tag}",
            "email": email,
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    assert r.status_code == 201
    assert client.post("/api/v1/auth/login", json={"email": email, "password": "Wrong#Guess99"}).status_code == 401
    ok = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Tiffin#Hall2026"},
        headers={"user-agent": "Mozilla/5.0 (iPhone) Safari"},
    )
    h = {"Authorization": "Bearer " + ok.json()["access_token"]}
    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    ah = {"Authorization": "Bearer " + admin.json()["access_token"]}
    logins = client.get("/api/v1/admin/activity", headers=ah, params={"kind": "login"}).json()
    mine = next(a for a in logins if a["user_email"] == email)
    assert mine["restaurant"] == f"Log Mess {tag}" and "iPhone" in mine["detail"] and "IP " in mine["detail"]
    fails = client.get("/api/v1/admin/activity", headers=ah, params={"kind": "login_failed"}).json()
    assert any(a["user_email"] == email and "Wrong password" in a["detail"] for a in fails)

    sent = []
    grab = lambda to, s, t, *a, **k: sent.append((to, s)) or True  # noqa: E731
    with patch("app.routers.support.send_email", side_effect=grab):
        t = client.post(
            "/api/v1/support/tickets",
            headers=h,
            json={"category": "payment", "subject": "Paid but plan not active", "message": "I paid Rs 3,597 at 10 am."},
        ).json()
        assert t["number"].startswith("VT-") and t["status"] == "open" and len(t["messages"]) == 1
        rep = client.post(
            f"/api/v1/admin/tickets/{t['id']}/messages",
            headers=ah,
            json={"message": "Checked with Dodo: activated now. Sorry for the wait.", "status": "resolved"},
        )
        assert rep.json()["status"] == "resolved"
    assert any(to == [email] and "Reply on VT-" in s for to, s in sent)
    mine_t = client.get(f"/api/v1/support/tickets/{t['id']}", headers=h).json()
    assert [m["from_admin"] for m in mine_t["messages"]] == [False, True]
    other = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other One",
            "organization_name": f"Nosy {tag}",
            "email": f"nosy.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    oh = {"Authorization": "Bearer " + other.json()["access_token"]}
    assert client.get(f"/api/v1/support/tickets/{t['id']}", headers=oh).status_code == 404
    assert client.get("/api/v1/admin/tickets", headers=oh).status_code == 403

    x = client.get("/api/v1/admin/logs.xlsx", headers=ah, params={"days": 1})
    rows = list(load_workbook(io.BytesIO(x.content))["Log history"].iter_rows(min_row=2, values_only=True))
    assert any(r[1] == "Signed in" and r[3] == email for r in rows)
    assert any(r[1] == "New support ticket" for r in rows)

    from app.worker.jobs import daily_digest_tick

    digest = []
    with patch("app.services.emailer.send_email", side_effect=lambda to, s, t, *a, **k: digest.append(t) or True):
        asyncio.run(daily_digest_tick({}))
    assert digest and f"Log Mess {tag} ({email})" in digest[0]


def test_admin_email_moves_to_superadmin_email(monkeypatch):
    """Setting SUPERADMIN_EMAIL to your own address renames the admin login; the password stays the same."""
    from app.config import settings
    from app.database import SessionLocal
    from app.models import User
    from app.seed import ensure_admin_email

    monkeypatch.setattr(settings, "SUPERADMIN_EMAIL", "owner.admin.test@gmail.com")
    with SessionLocal() as db:
        ensure_admin_email(db)
        db.commit()
        admin = db.query(User).filter_by(is_superadmin=True).order_by(User.id).first()
        assert admin.email == "owner.admin.test@gmail.com"
    monkeypatch.setattr(settings, "SUPERADMIN_EMAIL", "admin@virundhu.local")
    with SessionLocal() as db:
        ensure_admin_email(db)
        db.commit()
        assert db.query(User).filter_by(is_superadmin=True).order_by(User.id).first().email == "admin@virundhu.local"


def test_quick_help_answers_hands_over_and_drafts(client, monkeypatch):
    """Quick help answers from the guide; unknown questions go to a person (ticket in app, contact on the website)
    with the chat attached; the admin gets an AI draft."""
    import uuid

    from app.config import settings
    from app.services import help_bot

    monkeypatch.setattr(type(settings), "llm_configured", property(lambda self: False))  # guide search, no AI call
    a = client.post(
        "/api/v1/help/ask", json={"question": "Why is there no connect button for Zomato and Swiggy?"}
    ).json()
    assert a["covered"] and "Zomato" in a["answer"] and "screenshot" in a["answer"].lower()
    g = client.post("/api/v1/help/ask", json={"question": "Google says quota 0 error 429"}).json()
    assert g["covered"] and "two weeks" in g["answer"]
    x = client.post("/api/v1/help/ask", json={"question": "xyzzy plugh frobnicate"}).json()
    assert not x["covered"]
    assert help_bot.keyword_answer("payment paid but plan not active").topic == "payment"

    tag = uuid.uuid4().hex[:6]
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Help Owner",
            "organization_name": f"Help Mess {tag}",
            "email": f"help.{tag}@gmail.com",
            "password": "Tiffin#Hall2026",
            "accept_terms": True,
        },
    )
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    hist = [{"from": "user", "text": "I paid but my plan is still trial"}, {"from": "bot", "text": "Wait 2 minutes."}]
    t = client.post(
        "/api/v1/help/handover",
        headers=h,
        json={"message": "Still not active after 10 minutes", "topic": "payment", "history": hist},
    )
    assert t.status_code == 201 and t.json()["number"].startswith("VT-")
    admin = client.post("/api/v1/auth/login", json={"email": "admin@virundhu.local", "password": "Virundhu@Admin2026"})
    ah = {"Authorization": "Bearer " + admin.json()["access_token"]}
    full = client.get(f"/api/v1/admin/tickets/{t.json()['id']}", headers=ah).json()
    assert "Quick help chat" in full["messages"][0]["body"] and full["category"] == "payment"
    d = client.get(f"/api/v1/admin/tickets/{t.json()['id']}/draft", headers=ah)
    assert d.status_code == 200 and len(d.json()["draft"]) > 20
    assert client.get(f"/api/v1/admin/tickets/{t.json()['id']}/draft", headers=h).status_code == 403
    w = client.post(
        "/api/v1/help/contact",
        json={
            "name": "Visitor",
            "email": f"v.{tag}@gmail.com",
            "message": "Do you support Kerala restaurants?",
            "history": [],
        },
    )
    assert w.status_code == 201
