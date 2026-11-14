"""Attachment business logic: validated uploads, downloads and deletes (scoped by user_id)."""

import logging
import re
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import BadRequestError, NotFoundError
from app.models import Attachment, Contact, Deal
from app.services import storage as storage_module
from app.services.storage import FileTooLargeError

logger = logging.getLogger(__name__)

# Allowed extension -> accepted content types (first one is stored as canonical).
ALLOWED_TYPES: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "png": ("image/png",),
    "jpg": ("image/jpeg", "image/jpg", "image/pjpeg"),
    "jpeg": ("image/jpeg", "image/jpg", "image/pjpeg"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
}

_UNSAFE_CHARS = re.compile(r"[^\w.\- ()]+")


def sanitize_filename(raw: str | None, ext: str) -> str:
    """Return a display-safe filename (no path parts or control chars, max 255 chars)."""
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = _UNSAFE_CHARS.sub("_", name).strip(" .")
    if not name:
        name = f"file.{ext}"
    if len(name) > 255:
        stem = name[: 250 - len(ext)]
        name = f"{stem}.{ext}"
    return name


def _validate_type(filename: str | None, content_type: str | None) -> tuple[str, str]:
    """
    Check extension and content type agree with the allow-list.

    Returns:
        (extension, canonical content type)

    Raises:
        BadRequestError: unsupported or mismatched type
    """
    ext = Path(filename or "").suffix.lower().lstrip(".")
    if ext not in ALLOWED_TYPES:
        raise BadRequestError("File type not allowed. Allowed: pdf, png, jpg, jpeg, docx, xlsx")
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in ALLOWED_TYPES[ext]:
        raise BadRequestError("File content type does not match its extension")
    return ext, ALLOWED_TYPES[ext][0]


def _check_parent(db: Session, user_id: int, contact_id: int | None, deal_id: int | None) -> None:
    """Require exactly one owned parent (contact or deal)."""
    if (contact_id is None) == (deal_id is None):
        raise BadRequestError("Provide exactly one of contact_id or deal_id")
    if contact_id is not None:
        owned = db.scalar(
            select(Contact.id).where(Contact.id == contact_id, Contact.user_id == user_id)
        )
        if owned is None:
            raise NotFoundError("Contact not found")
    else:
        owned = db.scalar(select(Deal.id).where(Deal.id == deal_id, Deal.user_id == user_id))
        if owned is None:
            raise NotFoundError("Deal not found")


def create_attachment(
    db: Session,
    user_id: int,
    stream: BinaryIO,
    filename: str | None,
    content_type: str | None,
    contact_id: int | None = None,
    deal_id: int | None = None,
    declared_size: int | None = None,
) -> Attachment:
    """
    Validate and store an uploaded file, then record its metadata.

    Args:
        stream: Uploaded file stream (read in chunks)
        filename: Original client filename (display only)
        content_type: Client-declared MIME type
        declared_size: Size reported by the upload, if known (for an early 413)

    Raises:
        BadRequestError (400), NotFoundError (404), FileTooLargeError (413)
    """
    _check_parent(db, user_id, contact_id, deal_id)
    ext, canonical_type = _validate_type(filename, content_type)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if declared_size is not None and declared_size > max_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit")

    store = storage_module.get_storage()
    storage_path, size = store.save(user_id, stream, ext, max_bytes=max_bytes)
    if size == 0:
        store.delete(storage_path)
        raise BadRequestError("File is empty")

    attachment = Attachment(
        user_id=user_id,
        contact_id=contact_id,
        deal_id=deal_id,
        filename=sanitize_filename(filename, ext),
        content_type=canonical_type,
        size_bytes=size,
        storage_path=storage_path,
    )
    db.add(attachment)
    try:
        db.commit()
    except Exception:
        db.rollback()
        store.delete(storage_path)
        raise
    db.refresh(attachment)
    logger.info("Attachment %s uploaded by user %s (%s bytes)", attachment.id, user_id, size)
    return attachment


def get_attachment(db: Session, user_id: int, attachment_id: int) -> Attachment:
    """Return one of the user's attachments, or raise NotFoundError."""
    attachment = db.scalar(
        select(Attachment).where(Attachment.id == attachment_id, Attachment.user_id == user_id)
    )
    if attachment is None:
        raise NotFoundError("Attachment not found")
    return attachment


def get_attachment_file(db: Session, user_id: int, attachment_id: int) -> tuple[Attachment, Path]:
    """Return the attachment and its filesystem path for download."""
    attachment = get_attachment(db, user_id, attachment_id)
    return attachment, storage_module.get_storage().open(attachment.storage_path)


def delete_attachment(db: Session, user_id: int, attachment_id: int) -> None:
    """Delete the DB row, then the stored file."""
    attachment = get_attachment(db, user_id, attachment_id)
    storage_path = attachment.storage_path
    db.delete(attachment)
    db.commit()
    storage_module.get_storage().delete(storage_path)
    logger.info("Attachment %s deleted by user %s", attachment_id, user_id)
