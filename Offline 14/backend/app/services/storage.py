"""File storage. Local-disk implementation; keep the interface small (save/open/delete)
so an S3-backed version can be swapped in later."""

import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from app.config import settings
from app.exceptions import AppError, NotFoundError

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1 MB


class FileTooLargeError(AppError):
    """413 - uploaded file exceeds the size limit."""

    status_code = 413
    default_detail = "File too large"


class LocalStorage:
    """Stores files under ``<base_dir>/<user_id>/<uuid4>.<ext>``."""

    def __init__(self, base_dir: str | None = None) -> None:
        """
        Args:
            base_dir: Root folder; defaults to settings.UPLOAD_DIR (read at call time).
        """
        self._base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        """Absolute root folder for stored files."""
        return Path(self._base_dir or settings.UPLOAD_DIR).resolve()

    def _resolve(self, storage_path: str) -> Path:
        """Map a stored relative path to an absolute path, rejecting path traversal."""
        base = self.base_dir
        full = (base / storage_path).resolve()
        if not full.is_relative_to(base) or full == base:
            raise NotFoundError("File not found")
        return full

    def save(
        self, user_id: int, stream: BinaryIO, ext: str, max_bytes: int | None = None
    ) -> tuple[str, int]:
        """
        Copy a stream to disk in chunks under a generated name.

        Args:
            user_id: Owner (used as the sub-folder)
            stream: Readable binary stream
            ext: File extension without the dot (already validated by the caller)
            max_bytes: Optional size limit; exceeding it deletes the partial file

        Returns:
            (storage_path relative to base_dir, size in bytes)

        Raises:
            FileTooLargeError: the stream is larger than max_bytes
        """
        safe_ext = "".join(c for c in ext.lower() if c.isalnum())
        storage_path = f"{int(user_id)}/{uuid.uuid4().hex}.{safe_ext}"
        target = self._resolve(storage_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        size = 0
        try:
            with target.open("wb") as out:
                while chunk := stream.read(CHUNK_SIZE):
                    size += len(chunk)
                    if max_bytes is not None and size > max_bytes:
                        raise FileTooLargeError(
                            f"File exceeds the {max_bytes // (1024 * 1024)} MB limit"
                        )
                    out.write(chunk)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return storage_path, size

    def open(self, storage_path: str) -> Path:
        """Return the filesystem path of a stored file (404 if missing)."""
        full = self._resolve(storage_path)
        if not full.is_file():
            raise NotFoundError("File not found")
        return full

    def delete(self, storage_path: str) -> None:
        """Delete a stored file; missing files are ignored."""
        try:
            self._resolve(storage_path).unlink(missing_ok=True)
        except NotFoundError:
            logger.warning("Refused to delete suspicious storage path %r", storage_path)


storage = LocalStorage()


def get_storage() -> LocalStorage:
    """Return the active storage backend (tests can replace ``storage.storage``)."""
    return storage
