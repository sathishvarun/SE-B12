"""Health check and public client configuration."""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", tags=["health"])
async def health(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    """Report database and Redis status. Returns 503 if either is down."""
    result = {"status": "ok", "database": "ok", "redis": "ok"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        result["database"] = "down"
    try:
        client = aioredis.from_url(settings.REDIS_URL)
        await client.ping()
        await client.aclose()
    except Exception:
        logger.exception("Redis health check failed")
        result["redis"] = "down"
    if "down" in result.values():
        result["status"] = "degraded"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/api/v1/public/config", tags=["public"])
def public_config() -> dict[str, object]:
    """What the frontend needs to know before login (no secrets)."""
    return {
        "app_name": settings.APP_NAME,
        "google_enabled": settings.google_enabled,
        # "Sign in with Google" needs only the public client ID (Google Identity Services, no secret).
        "google_client_id": settings.GOOGLE_CLIENT_ID or None,
        "payments_enabled": settings.payments_enabled,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID or None,
        "ai_ready": settings.llm_configured,
        "llm_provider": settings.LLM_PROVIDER,
        "company": {
            "name": settings.COMPANY_NAME,
            "email": settings.CONTACT_EMAIL or None,
            "phone": settings.CONTACT_PHONE or None,
            "address": settings.COMPANY_ADDRESS or None,
            "parent": settings.PARENT_COMPANY or None,
            "parent_gstin": settings.PARENT_GSTIN or None,
            "grievance_officer": settings.GRIEVANCE_OFFICER or settings.COMPANY_NAME,
        },
    }
