"""Application settings, read from environment variables or the project's .env file."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration in one place. Never hard-code secrets anywhere else."""

    # Looks for .env in the project root (when run from backend/) and in the current folder.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    APP_NAME: str = "Virundhu"
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_URL: str = "http://localhost:5450"
    API_URL: str = "http://localhost:8450"
    TIMEZONE: str = "Asia/Kolkata"

    DATABASE_URL: str = "postgresql+psycopg2://virundhu:virundhu@localhost:5432/virundhu"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Required: set in .env (generate with: openssl rand -hex 32)
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SUPERADMIN_EMAIL: str = "admin@example.com"
    SUPERADMIN_PASSWORD: str = Field(min_length=8)
    DEMO_EMAIL: str = "demo@virundhu.local"
    DEMO_PASSWORD: str = Field(min_length=8)

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_MAPS_EMBED_KEY: str = ""  # optional: maps on outlet pages (Maps Embed API is free and unlimited)
    GOOGLE_PLACES_API_KEY: str = ""  # optional: "how you compare nearby" (Places API, paid per request)
    GOOGLE_REDIRECT_URI: str = "http://localhost:8450/api/v1/auth/google/callback"

    # Only ONE provider is ever called.
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_TAGGING_MODEL: str = "claude-haiku-5-5"
    ANTHROPIC_REPORT_MODEL: str = "claude-sonnet-5-5"
    OPENAI_API_KEY: str = ""
    OPENAI_TAGGING_MODEL: str = ""
    OPENAI_REPORT_MODEL: str = ""
    LLM_MAX_CONCURRENCY: int = 8
    # Estimated price per million tokens (USD) for cost tracking. Check your provider's pricing page.
    LLM_PRICE_INPUT_PER_M_USD: float = 1.0
    LLM_PRICE_OUTPUT_PER_M_USD: float = 5.0
    USD_INR: float = 88.0

    # Payments: "dodo" (Dodo Payments, default) or "razorpay". Only one is used.
    PAYMENT_PROVIDER: str = "dodo"
    DODO_PAYMENTS_API_KEY: str = ""
    DODO_PAYMENTS_WEBHOOK_KEY: str = ""
    DODO_PAYMENTS_ENVIRONMENT: str = "test_mode"
    # One "pay what you want" product: Virundhu sets the exact amount for each checkout from services/pricing.py
    DODO_PRODUCT_FLEX: str = ""
    DODO_PRODUCT_STARTER_MONTHLY: str = ""  # old fixed-price products, no longer used
    DODO_PRODUCT_STARTER_YEARLY: str = ""
    DODO_PRODUCT_GROWTH_MONTHLY: str = ""
    DODO_PRODUCT_GROWTH_YEARLY: str = ""
    # WhatsApp alerts (Meta WhatsApp Cloud API). Off until token and phone number ID are set.
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_TEMPLATE: str = "virundhu_alert"
    WHATSAPP_TEMPLATE_REVIEW: str = "virundhu_review_request"  # Marketing template; guests must have agreed
    WHATSAPP_TEMPLATE_SUMMARY: str = "virundhu_weekly_summary"  # Utility template
    WHATSAPP_TEMPLATE_PLAN: str = "virundhu_plan_reminder"  # Utility template
    WHATSAPP_TEMPLATE_LANG: str = "en"
    WHATSAPP_API_VERSION: str = "v21.0"
    # Who runs Virundhu: shown on the Contact, Privacy, Terms and Refund pages
    COMPANY_NAME: str = "Virundhu"
    CONTACT_EMAIL: str = ""
    CONTACT_PHONE: str = ""
    COMPANY_ADDRESS: str = ""
    PARENT_COMPANY: str = "SK Mini Mart"  # Virundhu is a brand of this GST-registered business
    PARENT_GSTIN: str = ""
    COMPANY_FOUNDED: str = "July 2026"  # shown on the site and receipts when set
    GRIEVANCE_OFFICER: str = ""  # person who answers privacy requests; defaults to the company name
    # Launch offer shown on the Plan and billing page (the code itself lives in Dodo > Sales > Discounts)
    PROMO_CODE: str = ""
    PROMO_MAX_DISCOUNT_PCT: int = 20  # biggest discount code you create in Dodo (FIRST10 = 20%)
    # Largest single online payment the payment provider accepts (Dodo refused ₹3.5 lakh on 20 Nov 2026).
    # Bigger orders are paid by bank transfer against a GST invoice and recorded by the admin.
    ONLINE_PAYMENT_MAX_INR: int = 300000
    # Accounts reports (Admin → Accounts). Prices include GST at this rate; SAC is confirmed by your accountant.
    GST_RATE_PERCENT: int = 18
    GST_SAC: str = ""
    SELLER_STATE_CODE: str = "33"  # Tamil Nadu; the PARENT_GSTIN's first two digits win when it is set
    # Printed on proforma invoices so big chains can pay by NEFT/RTGS. Kept in .env only, never in Git.
    BANK_ACCOUNT_NAME: str = ""
    BANK_NAME: str = ""
    BANK_ACCOUNT_NUMBER: str = ""
    BANK_IFSC: str = ""
    BANK_BRANCH: str = ""
    # Who gets the accounts Excel on the 1st of every month (comma separated). Empty = the admin notify email.
    ACCOUNTS_REPORT_EMAILS: str = ""
    PROMO_TEXT: str = ""

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_PLAN_STARTER: str = ""
    RAZORPAY_PLAN_GROWTH: str = ""

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "Virundhu <hello@example.com>"
    SMTP_HELO: str = ""
    # Where Virundhu's own notifications go (sign-ups, payments, tickets, daily digest). Default: admin login.
    NOTIFY_EMAIL: str = ""
    # Where demo requests from the Contact page go. Defaults to NOTIFY_EMAIL.
    DEMO_REQUESTS_EMAIL: str = ""
    # AI agent team (services/agent_team.py)
    ADMIN_WHATSAPP: str = ""  # your number, +91...; agents message it only when they truly need you
    WHATSAPP_TEMPLATE_ADMIN: str = "virundhu_admin_alert"  # Utility: '{{1}}: {{2}}. Details: {{3}}'
    DEMO_DAYS: str = "0,1,2,3,4,5"  # Monday=0 ... Saturday=5
    DEMO_TIMES: str = "11:00,15:00,17:30"  # India time
    DEMO_MINUTES: int = 30
    DEMO_LINK_MEET: str = ""  # optional fixed rooms; empty = a private video room is made for each demo
    DEMO_LINK_ZOOM: str = ""
    DEMO_LINK_TEAMS: str = ""
    DEMO_OFFICE: str = "SK Mini Mart, Ganapathy, Coimbatore"
    # Google Workspace user whose inbox holds the info and demo aliases (Admin console → Company mailbox).
    MAILBOX_ACCOUNT: str = ""

    @property
    def notify_email(self) -> str:
        return self.NOTIFY_EMAIL or self.SUPERADMIN_EMAIL

    @property
    def demo_requests_email(self) -> str:
        return self.DEMO_REQUESTS_EMAIL or self.notify_email

    @property
    def google_enabled(self) -> bool:
        """Google sign-in is shown only when both Google keys are set."""
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def llm_configured(self) -> bool:
        """True when the key for the chosen provider is present."""
        if self.LLM_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        return bool(self.OPENAI_API_KEY and self.OPENAI_TAGGING_MODEL and self.OPENAI_REPORT_MODEL)

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(self.WHATSAPP_TOKEN and self.WHATSAPP_PHONE_NUMBER_ID)

    @model_validator(mode="after")
    def _safe_for_production(self) -> "Settings":
        """On the live server, refuse to start with demo secrets or without HTTPS."""
        if self.APP_ENV != "production":
            return self
        problems = []
        if (
            any(w in self.SECRET_KEY.lower() for w in ("paste", "change", "random", "secret", "example"))
            or len(set(self.SECRET_KEY)) < 16
        ):
            problems.append(
                'SECRET_KEY: make a new one with  python -c "import secrets;print(secrets.token_urlsafe(48))"'
            )
        if (
            self.SUPERADMIN_PASSWORD.lower() in {"choose-your-own-long-password", "admin123", "password"}
            or len(self.SUPERADMIN_PASSWORD) < 12
        ):
            problems.append("SUPERADMIN_PASSWORD: choose your own password, at least 12 characters")
        if not self.APP_URL.startswith("https://"):
            problems.append("APP_URL must start with https:// on the live server")
        if problems:
            raise ValueError("Not safe to run in production:\n- " + "\n- ".join(problems))
        return self

    @property
    def payments_enabled(self) -> bool:
        """Checkout is offered only when the chosen provider's keys are present."""
        if self.PAYMENT_PROVIDER == "dodo":
            return bool(self.DODO_PAYMENTS_API_KEY and self.DODO_PRODUCT_FLEX)
        return bool(self.RAZORPAY_KEY_ID and self.RAZORPAY_KEY_SECRET)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


settings = get_settings()
