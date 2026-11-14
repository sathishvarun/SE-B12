"""Daily task reminders (send_task_reminders), scheduler job wrapper, and the email module."""

import smtplib
from datetime import date, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session, sessionmaker

import app.services.email as email_module
from app.config import settings
from app.models import Contact, Subscription, Task, TaskStatus, User
from app.services import scheduler
from app.services.reminder_job import send_task_reminders
from tests.conftest import Outbox

TODAY = date(2026, 11, 14)


def _user(db: Session, email: str, active: bool = True, name: str | None = "Sam") -> User:
    user = User(email=email, hashed_password=None, full_name=name, is_active=active)
    user.subscription = Subscription()
    db.add(user)
    db.commit()
    return user


def _task(db: Session, user: User, due: date | None, **kw: Any) -> Task:
    task = Task(user_id=user.id, title=kw.pop("title", "Do it"), due_date=due, **kw)
    db.add(task)
    db.commit()
    return task


def test_sends_one_digest_per_user_and_marks_tasks(db: Session, outbox: Outbox) -> None:
    alice = _user(db, "alice@x.com", name="Alice")
    bob = _user(db, "bob@x.com", name=None)
    contact = Contact(user_id=alice.id, name="Client Co")
    db.add(contact)
    db.commit()
    due_today = _task(db, alice, TODAY, title="Today task", contact_id=contact.id)
    overdue = _task(db, alice, TODAY - timedelta(days=3), title="Late task")
    future = _task(db, alice, TODAY + timedelta(days=1), title="Future")
    no_date = _task(db, alice, None, title="Someday")
    done = _task(db, alice, TODAY, title="Done", status=TaskStatus.DONE)
    already = _task(db, alice, TODAY, title="Already", reminder_sent=True)
    bobs = _task(db, bob, TODAY, title="Bob task")

    sent = send_task_reminders(db, today=TODAY)
    assert sent == 2

    alice_mail = outbox.to("alice@x.com")
    assert len(alice_mail) == 1
    _, subject, html = alice_mail[0]
    assert subject == "You have 2 task(s) due"
    assert "Today task" in html and "Late task" in html and "Client Co" in html
    assert "Future" not in html and "Someday" not in html and "Already" not in html
    assert "Alice" in html
    assert len(outbox.to("bob@x.com")) == 1
    assert "bob@x.com" in outbox.to("bob@x.com")[0][2]  # falls back to email as name

    db.expire_all()
    assert db.get(Task, due_today.id).reminder_sent is True  # type: ignore[union-attr]
    assert db.get(Task, overdue.id).reminder_sent is True  # type: ignore[union-attr]
    assert db.get(Task, bobs.id).reminder_sent is True  # type: ignore[union-attr]
    assert db.get(Task, already.id).reminder_sent is True  # type: ignore[union-attr]
    for t in (future, no_date, done):
        assert db.get(Task, t.id).reminder_sent is False  # type: ignore[union-attr]


def test_reminder_sent_only_once(db: Session, outbox: Outbox) -> None:
    user = _user(db, "a@x.com")
    _task(db, user, TODAY)
    assert send_task_reminders(db, today=TODAY) == 1
    assert send_task_reminders(db, today=TODAY) == 0
    assert send_task_reminders(db, today=TODAY + timedelta(days=1)) == 0
    assert len(outbox.messages) == 1


def test_inactive_users_are_skipped(db: Session, outbox: Outbox) -> None:
    user = _user(db, "off@x.com", active=False)
    task = _task(db, user, TODAY)
    assert send_task_reminders(db, today=TODAY) == 0
    assert outbox.messages == []
    db.expire_all()
    assert db.get(Task, task.id).reminder_sent is False  # type: ignore[union-attr]


def test_failed_send_leaves_tasks_for_retry(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    good = _user(db, "good@x.com")
    bad = _user(db, "bad@x.com")
    good_task = _task(db, good, TODAY)
    bad_task = _task(db, bad, TODAY)
    delivered: list[str] = []

    def flaky(to: str, subject: str, html: str) -> None:
        if to == "bad@x.com":
            raise RuntimeError("smtp down")
        delivered.append(to)

    monkeypatch.setattr(email_module, "send_email", flaky)
    assert send_task_reminders(db, today=TODAY) == 1
    assert delivered == ["good@x.com"]
    db.expire_all()
    assert db.get(Task, good_task.id).reminder_sent is True  # type: ignore[union-attr]
    assert db.get(Task, bad_task.id).reminder_sent is False  # type: ignore[union-attr]


def test_defaults_to_app_today(db: Session, outbox: Outbox) -> None:
    from tests.conftest import app_today

    user = _user(db, "a@x.com")
    _task(db, user, app_today())
    assert send_task_reminders(db) == 1


def test_scheduler_job_uses_own_session(
    session_factory: sessionmaker[Session], db: Session, outbox: Outbox, monkeypatch
) -> None:
    from tests.conftest import app_today

    user = _user(db, "job@x.com")
    _task(db, user, app_today())
    monkeypatch.setattr(scheduler, "SessionLocal", session_factory)
    scheduler.run_task_reminders()
    assert len(outbox.to("job@x.com")) == 1


def test_scheduler_job_swallows_errors(session_factory, monkeypatch) -> None:
    monkeypatch.setattr(scheduler, "SessionLocal", session_factory)

    def boom(db: Session) -> int:
        raise RuntimeError("db down")

    monkeypatch.setattr(scheduler, "send_task_reminders", boom)
    scheduler.run_task_reminders()  # must not raise


# ---------------------------------------------------------------------------
# email.send_email (real implementation, SMTP mocked)
# ---------------------------------------------------------------------------

# Captured at import time, before the autouse `outbox` fixture swaps it out.
ORIGINAL_SEND_EMAIL = email_module.send_email


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int = 0) -> None:
        self.host, self.port = host, port
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.sent: list[Any] = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, user: str, password: str) -> None:
        self.logged_in = (user, password)

    def send_message(self, message: Any) -> None:
        self.sent.append(message)


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[FakeSMTP]:
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USER", "user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pw")
    return FakeSMTP


def _original_send_email():
    """The real send_email (the autouse outbox fixture replaced the module attribute)."""
    return ORIGINAL_SEND_EMAIL


def test_send_email_via_starttls(smtp: type[FakeSMTP], monkeypatch) -> None:
    send = _original_send_email()
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    send("to@x.com", "Hi", "<p>Hello</p>")
    (conn,) = smtp.instances
    assert conn.host == "smtp.test" and conn.started_tls
    assert conn.logged_in == ("user", "pw")
    msg = conn.sent[0]
    assert msg["To"] == "to@x.com" and msg["Subject"] == "Hi"


def test_send_email_via_ssl_port(smtp: type[FakeSMTP], monkeypatch) -> None:
    send = _original_send_email()
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_USER", "")
    send("to@x.com", "Hi", "<p>Hello</p>")
    (conn,) = smtp.instances
    assert conn.started_tls is False and conn.logged_in is None and len(conn.sent) == 1


def test_send_email_errors_are_swallowed(smtp: type[FakeSMTP], monkeypatch) -> None:
    send = _original_send_email()

    def fail(self: FakeSMTP, message: Any) -> None:
        raise smtplib.SMTPException("nope")

    monkeypatch.setattr(FakeSMTP, "send_message", fail)
    send("to@x.com", "Hi", "<p>x</p>")  # must not raise


def test_send_email_without_smtp_host_only_logs(monkeypatch) -> None:
    send = _original_send_email()
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    called: list[object] = []
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: called.append(a))
    send("to@x.com", "Hi", "<p>x</p>")
    assert called == []


def test_render_template_autoescapes() -> None:
    html = email_module.render_template("welcome.html", user_name="<b>x</b>")
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "Sathish CRM" in html
