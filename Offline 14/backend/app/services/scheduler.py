"""APScheduler setup: runs the task-reminder job every day at 08:00 (server local time).

Note: with several worker processes each would start its own scheduler; run one worker
(or move the job to a separate process) to avoid duplicate emails.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app.services.reminder_job import send_task_reminders

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_task_reminders() -> None:
    """Job entry point: open a dedicated DB session and send reminders."""
    db = SessionLocal()
    try:
        send_task_reminders(db)
    except Exception:
        logger.exception("Task reminder job failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler (idempotent)."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_task_reminders,
        CronTrigger(hour=8, minute=0, timezone=settings.APP_TIMEZONE),
        id="task_reminders",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info("Scheduler started: task reminders daily at 08:00")


def shutdown_scheduler() -> None:
    """Stop the background scheduler if it is running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None
