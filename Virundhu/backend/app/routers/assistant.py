"""Ask Virundhu: a chat about the restaurant's own reviews.

This is the one place an LLM is called inside a request: the owner is waiting for the answer, it's a single call,
and it runs in FastAPI's thread pool with the provider timeout (45 s).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.services import assistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(max_length=4000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=20)


@router.post("/chat")
@limiter.limit("20/minute")
def chat(
    request: Request, body: ChatIn, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> dict:
    if not settings.llm_configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "The AI key isn't set up yet, so I can't answer.")
    try:
        text = assistant.answer(db, ctx.org, ctx.outlet_ids, body.message, [t.model_dump() for t in body.history])
    except Exception as exc:  # provider errors, timeouts
        logger.warning("Assistant failed for org %s: %s", ctx.org.id, exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "I couldn't get an answer just now. Please try again in a minute."
        ) from exc
    return {"answer": text}
