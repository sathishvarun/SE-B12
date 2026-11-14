"""Daily task-reminder job: one digest email per user for pending tasks due today or earlier."""

import logging
from datetime import date
from itertools import groupby

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import local_today, settings
from app.models import Task, TaskStatus, User
from app.schemas.task import task_to_response

logger = logging.getLogger(__name__)


def send_task_reminders(db: Session, today: date | None = None) -> int:
    """
    Email each active user a digest of pending tasks with due_date <= today that
    have not been reminded yet, then mark those tasks reminder_sent.

    A failed send leaves that user's tasks unmarked so the next run retries them.

    Returns:
        Number of digest emails sent.
    """
    from app.services.email import render_template, send_email

    today = today or local_today()
    tasks = db.scalars(
        select(Task)
        .join(User, User.id == Task.user_id)
        .where(
            Task.status == TaskStatus.PENDING,
            Task.due_date.is_not(None),
            Task.due_date <= today,
            Task.reminder_sent.is_(False),
            User.is_active.is_(True),
        )
        .options(
            selectinload(Task.user),
            selectinload(Task.contact),
            selectinload(Task.lead),
            selectinload(Task.deal),
        )
        .order_by(Task.user_id, Task.due_date, Task.id)
    ).all()

    app_url = settings.FRONTEND_URL.rstrip("/")
    sent = 0
    for user_id, group in groupby(tasks, key=lambda t: t.user_id):
        user_tasks = list(group)
        user = user_tasks[0].user
        items = []
        for task in user_tasks:
            resp = task_to_response(task, today=today)
            items.append(
                {
                    "title": resp.title,
                    "due_date": resp.due_date,
                    "linked_name": resp.linked_name,
                    "is_overdue": resp.is_overdue,
                }
            )
        try:
            html = render_template(
                "task_reminder.html",
                user_name=user.full_name or user.email,
                tasks=items,
                app_url=app_url,
            )
            send_email(user.email, f"You have {len(items)} task(s) due", html)
        except Exception:
            logger.exception("Task reminder email failed for user %s", user_id)
            continue

        for task in user_tasks:
            task.reminder_sent = True
        db.commit()
        sent += 1

    logger.info("Task reminders: %s email(s) sent", sent)
    return sent
