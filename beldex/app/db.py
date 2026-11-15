"""Database tables (SQLite by default). Everything the admin dashboard shows comes from here."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import settings


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(10), default="user")  # "user" | "admin"
    lang: Mapped[str] = mapped_column(String(5), default="en")     # "en" | "ta"
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sessions = relationship("LoginSession", back_populates="user")


class LoginSession(Base):
    """One row per sign-in. Time used = last_seen (or ended_at) - started_at."""
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    user = relationship("User", back_populates="sessions")

    @property
    def seconds(self) -> int:
        end = self.ended_at or self.last_seen
        return max(0, int((end - self.started_at).total_seconds()))


class QueryLog(Base):
    """Every question: answer, sources and the resources it used."""
    __tablename__ = "queries"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    lang: Mapped[str] = mapped_column(String(5), default="en")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    found: Mapped[bool] = mapped_column(Boolean, default=True)  # answered from the knowledge base?
    mode: Mapped[str] = mapped_column(String(20), default="llm")  # llm | extractive
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cpu_ms: Mapped[int] = mapped_column(Integer, default=0)
    mem_mb: Mapped[float] = mapped_column(Float, default=0.0)
    feedback: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 helpful, -1 not
    via: Mapped[str] = mapped_column(String(10), default="text")  # "text" | "voice"


class Activity(Base):
    """Audit trail: sign-ins, sign-outs, page views, admin actions."""
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text, default="")


class KnowledgeRun(Base):
    """Each refresh of the knowledge base (crawl + index)."""
    __tablename__ = "knowledge_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    pages: Mapped[int] = mapped_column(Integer, default=0)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")


engine = create_engine(settings.db_url, connect_args={"check_same_thread": False}
                       if settings.db_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    # small upgrade for databases created before voice existed
    from sqlalchemy import inspect, text
    cols = {c["name"] for c in inspect(engine).get_columns("queries")}
    if "via" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE queries ADD COLUMN via VARCHAR(10) DEFAULT 'text'"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
