"""LangChain model factory. Works with OpenAI or any OpenAI-compatible API (Groq, Gemini, Ollama)."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=1)
def get_llm():
    if not settings.has_llm:
        return None
    from langchain_openai import ChatOpenAI
    kw = {"model": settings.llm_model, "temperature": 0.1, "api_key": settings.openai_api_key or "ollama"}
    if settings.openai_base_url:
        kw["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kw)


@lru_cache(maxsize=1)
def get_embeddings():
    if not settings.openai_api_key or settings.search_mode != "vector":
        return None
    from langchain_openai import OpenAIEmbeddings
    kw = {"model": settings.embedding_model, "api_key": settings.openai_api_key}
    if settings.openai_base_url and "openai.com" not in settings.openai_base_url:
        kw["base_url"] = settings.openai_base_url
    return OpenAIEmbeddings(**kw)


def token_usage(msg) -> tuple[int, int]:
    meta = getattr(msg, "usage_metadata", None) or {}
    return int(meta.get("input_tokens", 0)), int(meta.get("output_tokens", 0))
