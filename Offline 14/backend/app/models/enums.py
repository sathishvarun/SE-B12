"""Helpers for storing Python enums in PostgreSQL by their lowercase values."""

import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Return a SQLAlchemy Enum that stores the member *values* (not names)."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )
