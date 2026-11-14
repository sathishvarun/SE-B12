"""Lead schemas (see PRPs/api-contract.md - Leads)."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import LeadSource, LeadStatus
from app.schemas.contact import ContactResponse, blank_to_none
from app.schemas.deal import DealResponse, MoneyInput


class LeadInput(BaseModel):
    """Body for creating or updating a lead (status is changed via PATCH /status)."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)
    source: LeadSource = LeadSource.OTHER
    notes: str | None = None

    @field_validator("email", "phone", "company", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: Any) -> Any:
        """Convert "" to None so optional fields (especially email) can be left blank."""
        return blank_to_none(value)


class LeadResponse(BaseModel):
    """A lead as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None
    phone: str | None
    company: str | None
    source: LeadSource
    status: LeadStatus
    notes: str | None
    converted_contact_id: int | None
    created_at: datetime
    updated_at: datetime


class LeadStatusUpdate(BaseModel):
    """Body for PATCH /leads/{id}/status."""

    status: LeadStatus


class ConvertLeadInput(BaseModel):
    """Body for POST /leads/{id}/convert."""

    deal_title: str = Field(min_length=1, max_length=255)
    deal_value: MoneyInput
    expected_close_date: date | None = None


class ConvertLeadResult(BaseModel):
    """Result of converting a lead: the updated lead plus the new contact and deal."""

    lead: LeadResponse
    contact: ContactResponse
    deal: DealResponse
