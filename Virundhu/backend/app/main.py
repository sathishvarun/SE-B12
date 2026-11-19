"""Virundhu API entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.limiter import limiter
from app.routers import (
    account,
    admin,
    admin_data,
    ai_staff,
    assistant,
    auth,
    billing,
    contact,
    dashboard,
    extras,
    feedback,
    google_auth,
    health,
    help,
    insights,
    intake,
    notifications,
    product_feedback,
    public,
    review_requests,
    reviews,
    support,
    team,
)

_FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=_FMT)
try:  # Server log files: backend/logs/virundhu.log, 10 files of 10 MB, oldest deleted (never committed to Git)
    from logging.handlers import RotatingFileHandler
    from pathlib import Path

    _logdir = Path(__file__).resolve().parents[1] / "logs"
    _logdir.mkdir(exist_ok=True)
    _fh = RotatingFileHandler(_logdir / "virundhu.log", maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    _fh.setFormatter(logging.Formatter(_FMT))
    logging.getLogger().addHandler(_fh)
except OSError:  # read-only disk: keep logging to the terminal only
    pass

app = FastAPI(
    title="Virundhu API",
    description="Every guest, heard. Review intelligence for restaurant chains.",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Browser safety headers on every API answer; nothing from the API is ever cached or framed."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if settings.APP_URL.startswith("https://"):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.APP_URL],
    # In development, also allow the same site opened from a phone on your Wi-Fi (http://192.168.x.x:5450).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):\d+"
    if settings.APP_ENV == "development"
    else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(public.router)
app.include_router(product_feedback.router)
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(intake.router)
app.include_router(notifications.router)
app.include_router(team.router)
app.include_router(admin.router)
app.include_router(admin_data.router)
app.include_router(insights.router)
app.include_router(support.router)
app.include_router(help.router)
app.include_router(billing.router)
app.include_router(assistant.router)
app.include_router(feedback.router)
app.include_router(contact.router)
app.include_router(account.router)
app.include_router(dashboard.router)
app.include_router(reviews.router)
app.include_router(review_requests.router)
app.include_router(extras.router)
app.include_router(ai_staff.router)
