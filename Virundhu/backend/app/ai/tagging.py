"""Tag a single review with the configured provider."""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm import chat_model
from app.ai.prompts import TAGGING_HUMAN, TAGGING_SYSTEM
from app.ai.safety import apply_safety_net
from app.ai.schemas import ReviewAnalysisOut
from app.config import settings

logger = logging.getLogger(__name__)
TONES = {"warm": "warm and friendly", "professional": "polite and professional", "short": "brief and polite"}


class TaggingError(Exception):
    """The model could not produce a valid result."""


def tag_review(
    text: str,
    rating: int | None = None,
    platform: str = "google",
    tone: str = "warm",
    signature: str = "- Team Virundhu",
    attempts: int = 2,
) -> dict[str, Any]:
    """Return analysis fields plus model name, token counts and safety flag. Retries invalid output."""
    prompt = ChatPromptTemplate.from_messages([("system", TAGGING_SYSTEM), ("human", TAGGING_HUMAN)])
    # OpenAI's strict JSON mode rejects some schema shapes; tool calling works for both providers.
    extra = {} if settings.LLM_PROVIDER == "anthropic" else {"method": "function_calling"}
    chain = prompt | chat_model("tagging").with_structured_output(ReviewAnalysisOut, include_raw=True, **extra)
    inputs = {
        "review_text": text,
        "rating": rating if rating else "not given",
        "platform": platform,
        "tone": TONES.get(tone, TONES["warm"]),
        "signature": signature,
    }
    last_error: Exception | None = None
    for _ in range(attempts + 1):
        try:
            res = chain.invoke(inputs)
        except Exception as exc:  # provider/network errors
            logger.warning("Tagging call failed: %s", exc)
            last_error = exc
            continue
        parsed = res.get("parsed")
        if parsed is None:
            last_error = res.get("parsing_error")
            continue
        result, overridden = apply_safety_net(text, parsed)
        raw = res.get("raw")
        usage = getattr(raw, "usage_metadata", None) or {}
        meta = getattr(raw, "response_metadata", None) or {}
        return {
            **result.model_dump(),
            "safety_override": overridden,
            "model_used": meta.get("model_name") or meta.get("model"),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
        }
    raise TaggingError(str(last_error) if last_error else "No valid result")
