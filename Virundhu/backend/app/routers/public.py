"""Public endpoints used by the landing page (no sign-in)."""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.ai.safety import has_food_safety_risk
from app.ai.tagging import TaggingError, tag_review
from app.config import settings
from app.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/public", tags=["public"])


class TryIn(BaseModel):
    text: str = Field(min_length=3, max_length=500)
    rating: int | None = Field(default=None, ge=1, le=5)


class TryOut(BaseModel):
    sentiment: str
    category: str
    urgency: str
    language: str
    summary: str
    suggested_reply: str
    safety_override: bool
    food_safety: bool


@router.post("/try", response_model=TryOut)
@limiter.limit("6/minute;40/day")
async def try_review(request: Request, body: TryIn) -> TryOut:
    """Landing-page demo: tag one short review live.

    The only place an LLM is called inside a web request: one short review, strictly rate limited per visitor.
    """
    if not settings.llm_configured:
        raise HTTPException(503, "The live demo isn't switched on yet. Add your AI key to .env.")
    try:
        result = await run_in_threadpool(
            tag_review, body.text.strip(), body.rating, "google", "warm", "- Team Virundhu", 1
        )
    except TaggingError as exc:
        logger.warning("Public try failed: %s", exc)
        raise HTTPException(503, "Couldn't read that review just now. Try again in a minute.") from exc
    result["food_safety"] = has_food_safety_risk(body.text)
    return TryOut(**{k: result[k] for k in TryOut.model_fields})
