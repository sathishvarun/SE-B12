"""Read reviews out of a screenshot of the Zomato or Swiggy partner app (the owner's own screen).

The owner takes the screenshot and uploads it; nothing is fetched from Zomato or Swiggy.
"""

import base64

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.ai.llm import chat_model
from app.config import settings

SYSTEM = (
    "You read screenshots of restaurant reviews from the Zomato or Swiggy restaurant partner app, Google Maps or "
    "similar. List every customer review you can see. Copy the review text exactly as written (it may be Tamil, "
    "Tanglish or English). Give the star rating as a whole number 1-5; if the stars are not visible, guess from the "
    "words. Skip the restaurant's own replies, menus, ads and anything that is not a customer review. If there are "
    "no reviews, return an empty list."
)


class ShotReview(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str = Field(min_length=1, max_length=5000)
    reviewer_name: str | None = None
    date_text: str | None = Field(default=None, description="The date as shown, e.g. '2 days ago' or '12 Nov'")


class ShotResult(BaseModel):
    reviews: list[ShotReview]


def read_screenshot(image: bytes, mime: str, org_id: int | None = None) -> list[ShotReview]:
    data = base64.b64encode(image).decode()
    extra = {} if settings.LLM_PROVIDER == "anthropic" else {"method": "function_calling"}
    model = chat_model("report", "screenshot", org_id).with_structured_output(ShotResult, **extra)
    result = model.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=[
                    {"type": "text", "text": "List the customer reviews in this screenshot."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}},
                ]
            ),
        ]
    )
    return list(result.reviews)[:30]
