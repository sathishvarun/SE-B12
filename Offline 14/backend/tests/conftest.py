"""Shared pytest fixtures: SQLite test DB, TestClient, sellers/admin, email outbox.

Env vars are set BEFORE importing the app because app.config.Settings requires them.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["SECRET_KEY"] = "pytest-only-9f3c1e7a2b4d6f8091a3c5e7b9d1f2a4c6e8"  # >= 32 chars
os.environ["SMTP_HOST"] = ""  # never send real email from tests
os.environ["DODO_PAYMENTS_API_KEY"] = ""
os.environ["DODO_PAYMENTS_WEBHOOK_SECRET"] = ""

from collections.abc import Callable, Generator, Iterator  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from datetime import date  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.services.email as email_module  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.rate_limit import limiter  # noqa: E402
from app.services import auth_service  # noqa: E402

API = "/api/v1"


def app_today() -> date:
    """'Today' as the app sees it (APP_TIMEZONE if the app defines local_today)."""
    import app.config as config_module

    local_today = getattr(config_module, "local_today", None)
    return local_today() if local_today else date.today()


PASSWORD = "Password123!"


def _enable_sqlite_fks(dbapi_connection: Any, _record: Any) -> None:
    """Turn on FK enforcement so ON DELETE CASCADE / SET NULL behave like Postgres."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def engine() -> Iterator[Engine]:
    """A fresh in-memory SQLite database (one shared connection) per test."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(eng, "connect", _enable_sqlite_fks)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory configured like app.database.SessionLocal."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """A session for arranging/inspecting data directly in tests."""
    session = session_factory()
    yield session
    session.close()


@dataclass
class Outbox:
    """Captured emails: list of (to, subject, html)."""

    messages: list[tuple[str, str, str]] = field(default_factory=list)

    def send(self, to: str, subject: str, html: str) -> None:
        self.messages.append((to, subject, html))

    def to(self, address: str) -> list[tuple[str, str, str]]:
        return [m for m in self.messages if m[0] == address]


@pytest.fixture(autouse=True)
def outbox(monkeypatch: pytest.MonkeyPatch) -> Outbox:
    """Capture every email instead of sending (auth_service imports send_email by name)."""
    box = Outbox()
    monkeypatch.setattr(email_module, "send_email", box.send)
    monkeypatch.setattr(auth_service, "send_email", box.send)
    return box


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Uploads go to a temp dir; no payment/email config leaks between tests."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "DODO_PAYMENTS_API_KEY", "")
    monkeypatch.setattr(settings, "DODO_PAYMENTS_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "DODO_PAYMENTS_PRO_PRODUCT_ID", "")


@pytest.fixture(autouse=True)
def _no_rate_limit() -> Iterator[None]:
    """Disable slowapi by default; a dedicated test re-enables it."""
    limiter.reset()
    limiter.enabled = False
    yield
    limiter.enabled = False
    limiter.reset()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """TestClient wired to the test DB. Not used as a context manager, so the
    lifespan (APScheduler) never starts."""

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@dataclass
class Seller:
    """A registered user plus ready-to-use auth headers."""

    id: int
    email: str
    access_token: str
    refresh_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


def register(client: TestClient, email: str, full_name: str = "Test Seller") -> Seller:
    """Register via the real endpoint and return the new seller."""
    resp = client.post(
        f"{API}/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name},
    )
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200, me.text
    return Seller(
        id=me.json()["id"],
        email=email,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
    )


@pytest.fixture
def make_seller(client: TestClient) -> Callable[..., Seller]:
    """Factory: make_seller("x@example.com") registers a new seller."""
    counter = {"n": 0}

    def _make(email: str | None = None, full_name: str = "Test Seller") -> Seller:
        counter["n"] += 1
        return register(client, email or f"seller{counter['n']}@example.com", full_name)

    return _make


@pytest.fixture
def seller_a(client: TestClient) -> Seller:
    return register(client, "alice@example.com", "Alice Seller")


@pytest.fixture
def seller_b(client: TestClient) -> Seller:
    return register(client, "bob@example.com", "Bob Seller")


@pytest.fixture
def admin(client: TestClient, db: Session) -> Seller:
    """A registered user promoted to admin directly in the DB."""
    seller = register(client, "admin@example.com", "Admin User")
    user = db.get(User, seller.id)
    assert user is not None
    user.is_admin = True
    db.commit()
    return seller


# ---------------------------------------------------------------------------
# Small API helpers used across modules
# ---------------------------------------------------------------------------


def create_contact(client: TestClient, seller: Seller, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Jane Customer", "email": "jane@cust.com"}
    body.update(overrides)
    resp = client.post(f"{API}/contacts", json=body, headers=seller.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_lead(client: TestClient, seller: Seller, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"name": "Lenny Lead", "email": "lenny@lead.com", "source": "website"}
    body.update(overrides)
    resp = client.post(f"{API}/leads", json=body, headers=seller.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_deal(
    client: TestClient, seller: Seller, contact_id: int, **overrides: Any
) -> dict[str, Any]:
    body: dict[str, Any] = {"title": "Big Deal", "contact_id": contact_id, "value": "1500"}
    body.update(overrides)
    resp = client.post(f"{API}/deals", json=body, headers=seller.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_task(client: TestClient, seller: Seller, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"title": "Call back"}
    body.update(overrides)
    resp = client.post(f"{API}/tasks", json=body, headers=seller.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
