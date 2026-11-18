"""Declarative base, shared mixins and the enum helper."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""


class TimestampMixin:
    """id, created_at and updated_at (UTC) on every table."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrgScopedMixin:
    """Every tenant table belongs to one organization."""

    @declared_attr
    def organization_id(cls) -> Mapped[int]:  # noqa: N805
        return mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)


def str_enum(name: str, *values: str) -> Enum:
    """A VARCHAR column with a CHECK constraint (portable, easy to migrate)."""
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=32)
