"""Database engine, session factory and the FastAPI dependency."""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, SessionTransaction, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
logger = logging.getLogger(__name__)

# ---- Row-level security (migration 0025) -------------------------------------------------------------------------
# A request that has a restaurant open marks its session with that restaurant. Every transaction of that session then
# runs as the role `virundhu_tenant` with `app.org_id` set, and PostgreSQL itself refuses rows of other restaurants.
# Both settings are transaction-local (SET LOCAL / set_config(..., true)), so a pooled connection never carries them on.
TENANT_ROLE = "virundhu_tenant"
_rls_ready: bool | None = None


def rls_ready() -> bool:
    """True once the tenant role exists in this database (the migration may skip it without the right privileges)."""
    global _rls_ready
    if _rls_ready is None:
        try:
            with engine.connect() as c:
                _rls_ready = bool(
                    c.execute(
                        text("SELECT pg_has_role(current_user, :r, 'MEMBER') FROM pg_roles WHERE rolname = :r"),
                        {"r": TENANT_ROLE},
                    ).scalar()
                )
        except Exception:
            logger.warning("Couldn't check row-level security; continuing without it")
            _rls_ready = False
    return _rls_ready


def _apply_tenant(connection: Connection, org_id: int) -> None:
    connection.exec_driver_sql(f"SET LOCAL ROLE {TENANT_ROLE}")
    connection.execute(text("SELECT set_config('app.org_id', :v, true)"), {"v": str(int(org_id))})


@event.listens_for(Session, "after_begin")
def _tenant_on_begin(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    org_id = session.info.get("tenant_org")
    if org_id:
        _apply_tenant(connection, org_id)


def set_tenant(db: Session, org_id: int) -> None:
    """From now on this session reads and writes only `org_id`'s rows on every restaurant table (enforced by
    PostgreSQL). Called once the request's restaurant is known; background jobs and the admin console never call it."""
    if not rls_ready():
        return
    db.info["tenant_org"] = org_id
    if db.in_transaction():  # the transaction already running (it found the restaurant) switches now
        _apply_tenant(db.connection(), org_id)


def get_db() -> Generator[Session, None, None]:
    """Yield a session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
