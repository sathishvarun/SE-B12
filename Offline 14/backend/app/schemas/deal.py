"""Deal schemas (see PRPs/api-contract.md - Deals)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.models import Deal, DealStage
from app.schemas.attachment import AttachmentResponse
from app.schemas.task import TaskResponse, task_to_response


def _money_to_str(value: Decimal) -> str:
    """Format a money amount as a 2-decimal string, e.g. Decimal("1500") -> "1500.00"."""
    return f"{value:.2f}"


# Money is a Decimal in Python but a string like "1500.00" in JSON.
Money = Annotated[Decimal, PlainSerializer(_money_to_str, return_type=str)]

# Input money: accepts a string or number, must be >= 0 with at most 2 decimal places.
MoneyInput = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class DealInput(BaseModel):
    """Body for creating or updating a deal. Omitting `stage` keeps the current one on update."""

    title: str = Field(min_length=1, max_length=255)
    contact_id: int
    value: MoneyInput = Decimal("0")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    stage: DealStage | None = None
    expected_close_date: date | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, value: str) -> str:
        """Store currency codes in upper case (e.g. "inr" -> "INR")."""
        return value.upper()


class MoveDealInput(BaseModel):
    """Body for PATCH /deals/{id}/stage."""

    stage: DealStage
    position: int = Field(ge=0)


class ContactBrief(BaseModel):
    """The few contact fields embedded in a deal."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: str | None


class DealSummary(BaseModel):
    """Short deal shape used inside ContactDetail."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    value: Money
    currency: str
    stage: DealStage
    expected_close_date: date | None


class DealResponse(DealSummary):
    """A deal as returned by list/create/update/move endpoints."""

    contact_id: int
    contact: ContactBrief
    position: int
    notes: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DealDetail(DealResponse):
    """A deal with its linked tasks and attachments."""

    tasks: list[TaskResponse]
    attachments: list[AttachmentResponse]


class DealBoard(BaseModel):
    """All of a user's deals grouped by stage, each list ordered by position."""

    prospect: list[DealResponse]
    proposal: list[DealResponse]
    negotiation: list[DealResponse]
    won: list[DealResponse]
    lost: list[DealResponse]


def deal_to_detail(deal: Deal) -> DealDetail:
    """
    Build a DealDetail from a Deal whose contact, tasks and attachments are loaded.

    Args:
        deal: Deal ORM object

    Returns:
        DealDetail with tasks converted via task_to_response
    """
    base = DealResponse.model_validate(deal)
    return DealDetail(
        **dict(base),
        tasks=[task_to_response(task) for task in deal.tasks],
        attachments=[AttachmentResponse.model_validate(a) for a in deal.attachments],
    )
