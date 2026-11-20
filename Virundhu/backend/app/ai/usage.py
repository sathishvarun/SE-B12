"""Token ledger: every AI call is written to `ai_usage` with the restaurant it was for.

`chat_model(purpose, feature=..., org_id=...)` attaches `UsageRecorder`, so a call is counted even when it fails to
parse or is retried. Writing never raises: a broken ledger must not stop a review from being read.
"""

import logging
from decimal import Decimal
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.config import settings

logger = logging.getLogger(__name__)

# feature key -> label shown to owners and the admin
FEATURES: dict[str, str] = {
    "review_reading": "Reading reviews and drafting replies",
    "ask": "Ask Virundhu chat",
    "screenshot": "Reading screenshots",
    "help": "Help chat",
    "support_agent": "Support agent (Tara)",
    "support_draft": "Support reply drafts",
    "feedback_agent": "Feedback agent (Isai)",
    "other": "Other",
}


def cost_inr(input_tokens: int, output_tokens: int) -> Decimal:
    """Rupee cost from the configured per-million prices (prices are set in .env, USD)."""
    usd = (
        input_tokens * settings.LLM_PRICE_INPUT_PER_M_USD + output_tokens * settings.LLM_PRICE_OUTPUT_PER_M_USD
    ) / 1_000_000
    return Decimal(str(round(usd * settings.USD_INR, 4)))


def _tokens(response: LLMResult) -> tuple[int, int, str | None]:
    """Input/output tokens and model name from a LangChain result (OpenAI and Anthropic shapes)."""
    tin = tout = 0
    model = None
    for gens in response.generations or []:
        for g in gens:
            msg = getattr(g, "message", None)
            meta = getattr(msg, "usage_metadata", None) or {}
            tin += int(meta.get("input_tokens", 0) or 0)
            tout += int(meta.get("output_tokens", 0) or 0)
            rm = getattr(msg, "response_metadata", None) or {}
            model = model or rm.get("model_name") or rm.get("model")
    if not (tin or tout):
        tu = (response.llm_output or {}).get("token_usage") or (response.llm_output or {}).get("usage") or {}
        tin = int(tu.get("prompt_tokens", tu.get("input_tokens", 0)) or 0)
        tout = int(tu.get("completion_tokens", tu.get("output_tokens", 0)) or 0)
    model = model or (response.llm_output or {}).get("model_name")
    return tin, tout, model


def record(org_id: int | None, feature: str, model: str | None, input_tokens: int, output_tokens: int) -> None:
    """Write one ledger row in its own session. Never raises."""
    if not (input_tokens or output_tokens):
        return
    try:
        from app.database import SessionLocal
        from app.models import AiUsage

        with SessionLocal() as db:
            db.add(
                AiUsage(
                    organization_id=org_id,
                    feature=feature if feature in FEATURES else "other",
                    model=(model or "")[:80] or None,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_inr=cost_inr(input_tokens, output_tokens),
                )
            )
            db.commit()
    except Exception:  # pragma: no cover - the ledger must never break the AI step
        logger.exception("Couldn't record AI usage for org %s (%s)", org_id, feature)


class UsageRecorder(BaseCallbackHandler):
    """Counts the tokens of every model call it is attached to."""

    def __init__(self, feature: str, org_id: int | None) -> None:
        self.feature = feature
        self.org_id = org_id

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        tin, tout, model = _tokens(response)
        record(self.org_id, self.feature, model, tin, tout)
