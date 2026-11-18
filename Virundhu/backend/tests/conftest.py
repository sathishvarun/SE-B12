"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.limiter import limiter
from app.main import app

limiter.enabled = False  # rate limits are tested separately; tests create many accounts quickly


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def _remove_test_accounts_afterwards():
    """Tests create restaurants and logins in your real database. Delete every one they created when the run ends."""
    from sqlalchemy import delete, func, select

    from app.database import SessionLocal
    from app.models import ActivityLog, Lead, Membership, Organization, User

    with SessionLocal() as db:
        last_org = db.scalar(select(func.max(Organization.id))) or 0
        last_user = db.scalar(select(func.max(User.id))) or 0
        last_lead = db.scalar(select(func.max(Lead.id))) or 0
        last_event = db.scalar(select(func.max(ActivityLog.id))) or 0
    yield
    with SessionLocal() as db:
        db.execute(delete(Organization).where(Organization.id > last_org, Organization.is_demo.is_(False)))
        orphans = select(User.id).where(
            User.id > last_user, User.is_superadmin.is_(False), ~User.id.in_(select(Membership.user_id))
        )
        db.execute(delete(User).where(User.id.in_(orphans)))
        db.execute(delete(Lead).where(Lead.id > last_lead))
        db.execute(delete(ActivityLog).where(ActivityLog.id > last_event))
        db.commit()


@pytest.fixture(autouse=True)
def _reset_sign_in_lockout():
    """Wrong-password counters (auth/lockout.py) shouldn't carry over from one test to the next."""
    import redis

    from app.config import settings

    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        keys = list(r.scan_iter("login-fail:*"))
        if keys:
            r.delete(*keys)
    except redis.RedisError:
        pass
    yield
