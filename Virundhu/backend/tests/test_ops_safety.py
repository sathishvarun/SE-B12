"""Error alerts to the admin, off-server encrypted backups, and the CEO summary."""

import gzip
import logging
import uuid
from datetime import date, timedelta
from unittest.mock import patch

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Outlet, Review, ReviewAnalysis
from app.services import error_alerts
from app.tools import offsite_backup


def test_error_alert_emails_once_per_error(monkeypatch):
    sent = []
    monkeypatch.setattr(error_alerts, "_send", lambda subject, body: sent.append(subject))
    monkeypatch.setattr(
        error_alerts.threading,
        "Thread",
        lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})(),
    )
    handler = error_alerts.ErrorAlertHandler()
    log = logging.getLogger(f"app.test_alerts.{uuid.uuid4().hex[:6]}")
    log.addHandler(handler)
    for _ in range(3):  # the same failure repeating (e.g. every 5 minutes) is emailed once
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("Payment sync failed")
    log.info("not an error")
    assert len(sent) == 1 and "Payment sync failed" in sent[0]


def test_unhandled_error_answers_plainly_and_is_logged(monkeypatch):
    import asyncio
    import json

    from starlette.requests import Request

    from app.main import _unhandled

    seen = []
    monkeypatch.setattr(logging.getLogger("app.unhandled"), "error", lambda *a, **k: seen.append(k.get("exc_info")))
    req = Request({"type": "http", "method": "GET", "path": "/api/v1/x", "headers": [], "query_string": b""})
    r = asyncio.run(_unhandled(req, RuntimeError("kaboom")))
    body = json.loads(r.body)
    assert r.status_code == 500 and "looking at it" in body["detail"] and "kaboom" not in r.body.decode()
    assert seen and seen[0][0] is RuntimeError  # traceback goes to the log (and the admin's inbox), not the user


def test_offsite_backup_is_encrypted_and_restorable(tmp_path, monkeypatch):
    raw = b"CREATE TABLE x(); -- customer data"
    f = tmp_path / "virundhu-2026-11-27-0300.sql.gz"
    f.write_bytes(gzip.compress(raw))
    monkeypatch.setattr(settings, "BACKUP_PASSPHRASE", "correct horse battery staple")
    mails = []
    with patch(
        "app.services.emailer.send_email",
        side_effect=lambda to, s, t, attachments=None, **k: mails.append(attachments) or True,
    ):
        out = offsite_backup.send(tmp_path)
    assert out.startswith("sent")
    name, blob, _ = mails[0][0]
    assert name.endswith(".enc") and raw not in blob and gzip.compress(raw) not in blob
    assert gzip.decompress(offsite_backup.decrypt_bytes(blob, "correct horse battery staple")) == raw
    monkeypatch.setattr(settings, "BACKUP_PASSPHRASE", "")
    assert offsite_backup.send(tmp_path).startswith("skipped")


def test_ceo_summary_counts_today_and_months(client):
    email = f"ceo-{uuid.uuid4().hex[:6]}@example.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ceo",
            "organization_name": "Ceo Mess",
            "email": email,
            "password": "Strong#Pass1",
            "accept_terms": True,
        },
    ).json()
    h, org_id = {"Authorization": f"Bearer {r['access_token']}"}, r["user"]["organization"]["id"]
    from app.services.dates import today_local

    today = today_local()
    last_month = today.replace(day=1) - timedelta(days=1)
    with SessionLocal() as db:
        o = db.scalar(select(Outlet).where(Outlet.organization_id == org_id)) or Outlet(
            organization_id=org_id, name="Main"
        )
        db.add(o)
        db.flush()
        rows = [
            (today, 5, "positive", "google"),
            (today, 1, "negative", "zomato"),
            (today, 2, "negative", "swiggy"),
            (last_month, 4, "positive", "google"),
        ]
        for d, rating, s, p in rows:
            rv = Review(
                organization_id=org_id,
                outlet_id=o.id,
                external_id=uuid.uuid4().hex,
                platform=p,
                rating=rating,
                review_date=d,
                review_text="x",
                analysis_status="analyzed",
            )
            db.add(rv)
            db.flush()
            db.add(
                ReviewAnalysis(
                    review_id=rv.id,
                    sentiment=s,
                    category="other",
                    urgency="low",
                    language="english",
                    summary="x",
                    suggested_reply="y",
                    status="analyzed",
                )
            )
        db.commit()
    s = client.get("/api/v1/dashboard/summary", headers=h).json()
    assert (s["today"]["reviews"], s["today"]["positive"], s["today"]["negative"]) == (3, 1, 2)
    assert s["this_month"]["reviews"] >= 3 and s["last_month"]["reviews"] == 1
    plats = {p["key"]: p for p in s["by_platform"]}
    assert plats["google"]["this_month"] >= 1 and plats["google"]["last_month"] == 1
    assert s["by_outlet"] and isinstance(date.fromisoformat(s["as_of"]), date)
