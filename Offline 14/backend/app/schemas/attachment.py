"""Attachment schemas (shared: used by the attachments router and contact/deal detail)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    """File metadata as returned by the API (see PRPs/api-contract.md)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    contact_id: int | None
    deal_id: int | None
    created_at: datetime
