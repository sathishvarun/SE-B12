"""Contact business logic. Every query is scoped to the owning user."""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import NotFoundError
from app.models import Attachment, Contact, Deal, Tag, Task
from app.schemas.contact import ContactInput
from app.services import deal_service, plan_limits, storage, tag_service

logger = logging.getLogger(__name__)


def like_pattern(term: str) -> str:
    """Build a "%term%" pattern, escaping LIKE wildcards so they match literally."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_contacts(
    db: Session,
    user_id: int,
    search: str | None,
    tag_id: int | None,
    offset: int,
    limit: int,
) -> tuple[list[Contact], int]:
    """
    Return one page of the user's contacts (ordered by name) and the total count.

    Args:
        db: Database session
        user_id: Owner of the contacts
        search: Case-insensitive match on name, email or company
        tag_id: Only contacts that have this tag
        offset: Rows to skip
        limit: Page size

    Returns:
        (contacts with tags loaded, total matching rows)
    """
    stmt = select(Contact).where(Contact.user_id == user_id)
    if search and search.strip():
        pattern = like_pattern(search.strip())
        stmt = stmt.where(
            or_(
                Contact.name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.company.ilike(pattern, escape="\\"),
            )
        )
    if tag_id is not None:
        stmt = stmt.where(Contact.tags.any(Tag.id == tag_id))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page_stmt = (
        stmt.options(selectinload(Contact.tags))
        .order_by(Contact.name, Contact.id)
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(page_stmt)), total


def list_contact_options(db: Session, user_id: int) -> list[Contact]:
    """Return all of the user's contacts ordered by name (for dropdowns)."""
    stmt = select(Contact).where(Contact.user_id == user_id).order_by(Contact.name, Contact.id)
    return list(db.scalars(stmt))


def get_contact(db: Session, user_id: int, contact_id: int) -> Contact:
    """
    Return a user's contact with its tags loaded.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    stmt = (
        select(Contact)
        .where(Contact.id == contact_id, Contact.user_id == user_id)
        .options(selectinload(Contact.tags))
    )
    contact = db.scalar(stmt)
    if contact is None:
        raise NotFoundError("Contact not found")
    return contact


def get_contact_detail(db: Session, user_id: int, contact_id: int) -> Contact:
    """
    Return a user's contact with tags, deals, tasks and attachments loaded.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    stmt = (
        select(Contact)
        .where(Contact.id == contact_id, Contact.user_id == user_id)
        .options(
            selectinload(Contact.tags),
            selectinload(Contact.deals),
            selectinload(Contact.tasks).selectinload(Task.contact),
            selectinload(Contact.attachments),
        )
    )
    contact = db.scalar(stmt)
    if contact is None:
        raise NotFoundError("Contact not found")
    return contact


def create_contact(db: Session, user_id: int, data: ContactInput) -> Contact:
    """
    Create a contact (with optional tags) for the user.

    Raises:
        PaymentRequiredError: Free plan contact limit reached
        NotFoundError: A tag id is not owned by the user
    """
    plan_limits.ensure_can_create_contact(db, user_id)
    tags = tag_service.get_tags_by_ids(db, user_id, data.tag_ids or [])
    contact = Contact(user_id=user_id, **data.model_dump(exclude={"tag_ids"}))
    contact.tags = tags
    db.add(contact)
    db.commit()
    logger.info("Created contact %s for user %s", contact.id, user_id)
    return get_contact(db, user_id, contact.id)


def update_contact(db: Session, user_id: int, contact_id: int, data: ContactInput) -> Contact:
    """
    Update a user's contact. Tags are replaced only when `tag_ids` is provided.

    Raises:
        NotFoundError: Contact or a tag id not owned by the user
    """
    contact = get_contact(db, user_id, contact_id)
    for field, value in data.model_dump(exclude={"tag_ids"}).items():
        setattr(contact, field, value)
    if data.tag_ids is not None:
        contact.tags = tag_service.get_tags_by_ids(db, user_id, data.tag_ids)
    db.commit()
    return get_contact(db, user_id, contact.id)


def delete_contact(db: Session, user_id: int, contact_id: int) -> None:
    """
    Delete a user's contact (its deals and attachments cascade).

    Raises:
        NotFoundError: Missing or owned by another user
    """
    contact = get_contact(db, user_id, contact_id)
    # The database removes the attachment rows (cascade) but not the files on disk,
    # so collect the files of the contact and of its deals first.
    deal_ids = select(Deal.id).where(Deal.contact_id == contact_id)
    file_paths = db.scalars(
        select(Attachment.storage_path).where(
            or_(Attachment.contact_id == contact_id, Attachment.deal_id.in_(deal_ids))
        )
    ).all()
    db.delete(contact)
    db.commit()
    for path in file_paths:
        storage.get_storage().delete(path)
    # The contact's deals were cascade-deleted, so close the gaps in the board columns.
    deal_service.compact_all_columns(db, user_id)
    logger.info("Deleted contact %s for user %s", contact_id, user_id)
