"""FastAPI application entry point for Sathish CRM."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.exceptions import AppError
from app.middleware import MaxBodySizeMiddleware
from app.rate_limit import limiter
from app.routers import (
    admin,
    attachments,
    auth,
    billing,
    contacts,
    dashboard,
    deals,
    leads,
    tags,
    tasks,
)
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Start the daily task-reminder scheduler on startup and stop it on shutdown."""
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Sathish CRM API", version="1.0.0", lifespan=lifespan)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Reject huge request bodies early (upload limit + 1 MB for multipart overhead)
app.add_middleware(MaxBodySizeMiddleware, max_bytes=(settings.MAX_UPLOAD_MB + 1) * 1024 * 1024)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert AppError subclasses into {"detail": ...} JSON responses."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


# All module routers live under /api/v1
for module in (auth, admin, contacts, tags, leads, deals, tasks, attachments, dashboard, billing):
    app.include_router(module.router, prefix="/api/v1")
