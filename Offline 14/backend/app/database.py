"""Database engine, session factory and the FastAPI ``get_db`` dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.base import Base

__all__ = ["Base", "SessionLocal", "engine", "get_db", "normalize_db_url"]


def normalize_db_url(url: str) -> str:
    """Pin plain ``postgresql://`` URLs to the installed psycopg2 driver.

    SQLAlchemy 2.1 maps ``postgresql://`` to psycopg (v3) by default, but this
    project installs ``psycopg2-binary``.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url


engine = create_engine(normalize_db_url(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
