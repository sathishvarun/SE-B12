"""All settings come from the .env file (see .env.example). Nothing secret is hard-coded."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- LLM (any OpenAI-compatible provider: OpenAI, Groq, Gemini, Ollama...) ---
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "").strip()
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    # "vector" = FAISS + embeddings (by meaning), "keyword" = BM25 (no embeddings needed)
    search_mode: str = os.getenv("SEARCH_MODE", "vector").lower()
    # price per 1M tokens, used for the admin cost column (gpt-4o-mini defaults)
    price_in_per_m: float = float(os.getenv("PRICE_INPUT_PER_M", "0.15"))
    price_out_per_m: float = float(os.getenv("PRICE_OUTPUT_PER_M", "0.60"))

    # --- Security ---
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-env")
    jwt_hours: int = int(os.getenv("JWT_HOURS", "12"))
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    allow_signup: bool = _bool("ALLOW_SIGNUP", True)

    # --- Knowledge sources (answers come ONLY from these) ---
    crawl_start_urls: list[str] = field(default_factory=lambda: [
        u.strip() for u in os.getenv(
            "CRAWL_START_URLS",
            "https://beldex.io/,https://beldex.io/whitepaper.pdf,https://bchat.beldex.io/,"
            "https://belnet.beldex.io/,https://browser.beldex.io/,https://bns.beldex.io/,"
            "https://beldex.io/partners,https://beldex.io/usebdx",
        ).split(",") if u.strip()
    ])
    crawl_allowed_domain: str = os.getenv("CRAWL_ALLOWED_DOMAIN", "beldex.io")
    crawl_max_pages: int = int(os.getenv("CRAWL_MAX_PAGES", "60"))

    # --- Paths ---
    data_dir: Path = ROOT / "data"
    api_url: str = os.getenv("API_URL", "http://127.0.0.1:8000")

    # --- LangSmith tracing: set LANGSMITH_TRACING=true + LANGSMITH_API_KEY in .env ---

    @property
    def has_llm(self) -> bool:
        return bool(self.openai_api_key) or "localhost" in self.openai_base_url or "ollama" in self.openai_base_url

    @property
    def db_url(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{self.data_dir / 'app.db'}")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "knowledge").mkdir(exist_ok=True)
