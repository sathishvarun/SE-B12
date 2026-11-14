"""Application settings loaded from environment variables / backend/.env."""

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration. Secrets come only from the environment."""

    # Look for the project-root .env and backend/.env no matter which folder uvicorn starts in.
    # Later files win, so backend/.env can override the root one.
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[1] / ".env",
        ),
        extra="ignore",
    )

    # Database (required - no default so secrets are never hardcoded)
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Dodo Payments
    DODO_PAYMENTS_API_KEY: str = ""
    DODO_PAYMENTS_WEBHOOK_SECRET: str = ""
    DODO_PAYMENTS_PRO_PRODUCT_ID: str = ""
    DODO_PAYMENTS_ENVIRONMENT: str = "test_mode"

    # Email (empty SMTP_HOST = log emails instead of sending)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@example.com"

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 10

    # Plan limits
    FREE_PLAN_MAX_CONTACTS: int = 100
    FREE_PLAN_MAX_OPEN_DEALS: int = 20

    # Sellers' local time zone: decides what "today"/"overdue" mean and when reminders go out
    APP_TIMEZONE: str = "Asia/Kolkata"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, value: str) -> str:
        """Refuse to start with a short or placeholder SECRET_KEY (anyone could forge tokens)."""
        if len(value) < 32 or value.startswith(("replace-", "your-", "change-me")):
            raise ValueError(
                "SECRET_KEY must be a random value of at least 32 characters. Generate one with: "
                'python3 -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return value


settings = Settings()  # type: ignore[call-arg]  # required fields come from env


def local_today() -> date:
    """Today's date in APP_TIMEZONE (the server itself usually runs in UTC)."""
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
