"""One AI provider at a time, chosen by LLM_PROVIDER. No second provider is ever called."""

from langchain_core.language_models.chat_models import BaseChatModel

from app.ai.usage import UsageRecorder
from app.config import settings


def chat_model(purpose: str, feature: str = "other", org_id: int | None = None) -> BaseChatModel:
    """Chat model for 'tagging' (fast, cheap) or 'report' (stronger).

    Every call is written to the token ledger (`ai_usage`) under `feature` and the restaurant `org_id`.
    """
    callbacks = [UsageRecorder(feature, org_id)]
    if settings.LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        model = settings.ANTHROPIC_TAGGING_MODEL if purpose == "tagging" else settings.ANTHROPIC_REPORT_MODEL
        return ChatAnthropic(
            model=model,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0,
            max_tokens=800,
            timeout=45,
            max_retries=2,
            callbacks=callbacks,
        )
    from langchain_openai import ChatOpenAI

    model = settings.OPENAI_TAGGING_MODEL if purpose == "tagging" else settings.OPENAI_REPORT_MODEL
    return ChatOpenAI(
        model=model,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
        timeout=45,
        max_retries=2,
        callbacks=callbacks,
    )
