"""Contact and tag schemas (see PRPs/api-contract.md - Contacts)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Contact
from app.schemas.attachment import AttachmentResponse
from app.schemas.deal import DealSummary
from app.schemas.task import TaskResponse, task_to_response


def blank_to_none(value: Any) -> Any:
    """Treat empty / whitespace-only strings as "not provided" (None)."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


class TagInput(BaseModel):
    """Body for POST /tags."""

    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Trim surrounding whitespace and reject names that are only whitespace."""
        value = value.strip()
        if not value:
            raise ValueError("Tag name cannot be blank")
        return value


class Tag(BaseModel):
    """A tag as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ContactInput(BaseModel):
    """Body for creating or updating a contact. Omitted `tag_ids` keeps tags on update."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)
    address: str | None = None
    notes: str | None = None
    tag_ids: list[int] | None = None

    @field_validator("email", "phone", "company", "address", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: Any) -> Any:
        """Convert "" to None so optional fields (especially email) can be left blank."""
        return blank_to_none(value)


class ContactResponse(BaseModel):
    """A contact as returned by list/create/update endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone: str | None
    company: str | None
    address: str | None
    notes: str | None
    tags: list[Tag]
    created_at: datetime
    updated_at: datetime


class ContactDetail(ContactResponse):
    """A contact with its deals, tasks and attachments."""

    deals: list[DealSummary]
    tasks: list[TaskResponse]
    attachments: list[AttachmentResponse]


class ContactOption(BaseModel):
    """Minimal contact shape for select dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str | None


def contact_to_detail(contact: Contact) -> ContactDetail:
    """
    Build a ContactDetail from a Contact whose tags, deals, tasks and attachments are loaded.

    Args:
        contact: Contact ORM object

    Returns:
        ContactDetail with tasks converted via task_to_response
    """
    base = ContactResponse.model_validate(contact)
    return ContactDetail(
        **dict(base),
        deals=[DealSummary.model_validate(d) for d in contact.deals],
        tasks=[task_to_response(task) for task in contact.tasks],
        attachments=[AttachmentResponse.model_validate(a) for a in contact.attachments],
    )
