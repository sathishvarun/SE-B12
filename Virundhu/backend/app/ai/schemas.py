"""Structured output the LLM must return for one review."""

from typing import Literal

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "neutral", "negative"]
Category = Literal["food_quality", "delivery", "price", "staff", "packaging", "hygiene", "app", "other"]
Urgency = Literal["low", "medium", "high"]
Language = Literal["english", "tamil", "tanglish", "other"]


class Mention(BaseModel):
    """A dish or a staff member named in the review, and how the guest felt about it."""

    name: str = Field(
        max_length=60,
        description="As written, lower case for dishes (e.g. 'chicken biryani'); a person's first name for staff.",
    )
    sentiment: Sentiment


class ReviewAnalysisOut(BaseModel):
    """Tags, summary and reply draft for one review."""

    sentiment: Sentiment
    category: Category
    urgency: Urgency
    language: Language
    summary: str = Field(max_length=200, description="One plain English sentence, max 160 characters.")
    suggested_reply: str = Field(max_length=700, description="Reply in the same language and script as the review.")
    dishes: list[Mention] = Field(
        default_factory=list, max_length=6, description="Dishes or drinks named in the review. Empty if none."
    )
    staff: list[Mention] = Field(
        default_factory=list,
        max_length=4,
        description="Staff named by name or role (e.g. 'Ravi', 'delivery person'). Empty if none.",
    )
