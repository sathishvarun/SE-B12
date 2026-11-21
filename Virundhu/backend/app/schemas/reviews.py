"""Review list/detail bodies."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AnalysisOut(BaseModel):
    sentiment: str | None
    category: str | None
    urgency: str | None
    language: str | None
    summary: str | None
    suggested_reply: str | None
    safety_override: bool
    food_safety: bool


class ReviewOut(BaseModel):
    id: int
    external_id: str
    platform: str
    rating: int
    review_date: date
    review_text: str
    outlet_id: int | None
    outlet_name: str | None
    workflow_status: str
    final_reply: str | None
    is_sample: bool = False
    reply_posted_at: datetime | None = None
    can_post_to_google: bool = False
    auto_replied: bool = False
    guest_name: str | None = None
    guest_contact: str | None = None
    reply_due_at: datetime | None = None  # reply promise: set for bad reviews on the clock
    replied_at: datetime | None = None
    analysis: AnalysisOut | None


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
    counts: dict[str, int]


class ReviewUpdate(BaseModel):
    workflow_status: str | None = Field(default=None, pattern="^(new|in_progress|replied|ignored)$")
    final_reply: str | None = Field(default=None, max_length=2000)
