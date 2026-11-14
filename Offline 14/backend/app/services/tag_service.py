"""Tag business logic. Every query is scoped to the owning user."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models import Tag
from app.schemas.contact import TagInput

logger = logging.getLogger(__name__)


def list_tags(db: Session, user_id: int) -> list[Tag]:
    """Return all of the user's tags ordered by name."""
    stmt = select(Tag).where(Tag.user_id == user_id).order_by(Tag.name)
    return list(db.scalars(stmt))


def create_tag(db: Session, user_id: int, data: TagInput) -> Tag:
    """
    Create a tag for the user.

    Raises:
        ConflictError: The user already has a tag with this name
    """
    existing = db.scalar(select(Tag.id).where(Tag.user_id == user_id, Tag.name == data.name))
    if existing is not None:
        raise ConflictError(f"Tag '{data.name}' already exists")

    tag = Tag(user_id=user_id, name=data.name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:  # race with a concurrent insert of the same name
        db.rollback()
        raise ConflictError(f"Tag '{data.name}' already exists") from exc
    db.refresh(tag)
    logger.info("Created tag %s for user %s", tag.id, user_id)
    return tag


def get_tags_by_ids(db: Session, user_id: int, tag_ids: list[int]) -> list[Tag]:
    """
    Load the given tags, all of which must belong to the user.

    Raises:
        NotFoundError: Any id is missing or owned by another user
    """
    unique_ids = set(tag_ids)
    if not unique_ids:
        return []
    stmt = select(Tag).where(Tag.user_id == user_id, Tag.id.in_(unique_ids))
    tags = list(db.scalars(stmt))
    if len(tags) != len(unique_ids):
        raise NotFoundError("Tag not found")
    return tags
