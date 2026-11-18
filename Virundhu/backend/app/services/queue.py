"""Hand analysis work to the background worker (ARQ). Falls back to a local thread if Redis is down."""

import logging
import threading

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def _run_locally(org_id: int, review_ids: list[int], batch_id: int | None) -> None:
    from app.services.analysis import analyze_reviews

    with SessionLocal() as db:
        analyze_reviews(db, org_id, review_ids, batch_id)


async def enqueue_analysis(org_id: int, review_ids: list[int], batch_id: int | None = None) -> None:
    """Queue reviews for reading by the AI."""
    if not review_ids:
        return
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job("analyze_job", org_id, review_ids, batch_id)
        await pool.aclose()
    except Exception:
        logger.warning("Worker queue unavailable; analysing in the API process instead")
        threading.Thread(target=_run_locally, args=(org_id, review_ids, batch_id), daemon=True).start()
