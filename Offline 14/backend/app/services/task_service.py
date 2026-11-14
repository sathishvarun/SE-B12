"""Task business logic: CRUD, list views and completion. Every query is scoped by user_id."""

import logging
from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.config import local_today
from app.exceptions import BadRequestError, NotFoundError
from app.models import Contact, Deal, Lead, Task, TaskStatus
from app.schemas.task import TaskInput

logger = logging.getLogger(__name__)

TaskView = Literal["today", "upcoming", "overdue", "done"]


def _base_query(user_id: int) -> Select[Task]:
    """Select the user's tasks with linked records eager-loaded (avoids N+1 in responses)."""
    return (
        select(Task)
        .where(Task.user_id == user_id)
        .options(selectinload(Task.contact), selectinload(Task.lead), selectinload(Task.deal))
    )


def _validate_links(db: Session, user_id: int, data: TaskInput) -> None:
    """
    Ensure at most one link is set and that the linked record belongs to the user.

    Raises:
        BadRequestError: more than one of contact_id / lead_id / deal_id is set
        NotFoundError: the linked record does not exist or belongs to another user
    """
    links = [data.contact_id, data.lead_id, data.deal_id]
    if sum(link is not None for link in links) > 1:
        raise BadRequestError("A task can be linked to at most one contact, lead or deal")

    checks: list[tuple[type[Contact] | type[Lead] | type[Deal], int | None, str]] = [
        (Contact, data.contact_id, "Contact not found"),
        (Lead, data.lead_id, "Lead not found"),
        (Deal, data.deal_id, "Deal not found"),
    ]
    for model, record_id, message in checks:
        if record_id is None:
            continue
        found = db.scalar(select(model.id).where(model.id == record_id, model.user_id == user_id))
        if found is None:
            raise NotFoundError(message)


def list_tasks(
    db: Session,
    user_id: int,
    view: TaskView | None = None,
    contact_id: int | None = None,
    lead_id: int | None = None,
    deal_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
    today: date | None = None,
) -> tuple[list[Task], int]:
    """
    List the user's tasks for a view, with optional link filters and pagination.

    Views: today / upcoming / overdue / done; no view means all pending tasks.

    Returns:
        (tasks for the requested page, total matching count)
    """
    today = today or local_today()
    conditions = [Task.user_id == user_id]

    if view == "done":
        conditions.append(Task.status == TaskStatus.DONE)
    else:
        conditions.append(Task.status == TaskStatus.PENDING)
        if view == "today":
            conditions.append(Task.due_date == today)
        elif view == "upcoming":
            conditions.append(or_(Task.due_date > today, Task.due_date.is_(None)))
        elif view == "overdue":
            conditions.append(Task.due_date < today)

    if contact_id is not None:
        conditions.append(Task.contact_id == contact_id)
    if lead_id is not None:
        conditions.append(Task.lead_id == lead_id)
    if deal_id is not None:
        conditions.append(Task.deal_id == deal_id)

    total = db.scalar(select(func.count()).select_from(Task).where(*conditions)) or 0

    order: list[ColumnElement[Any]]
    if view == "done":
        order = [Task.completed_at.desc().nulls_last(), Task.id.desc()]
    else:
        order = [Task.due_date.asc().nulls_last(), Task.id.asc()]

    query = _base_query(user_id).where(*conditions).order_by(*order).offset(offset).limit(limit)
    return list(db.scalars(query).all()), total


def get_task(db: Session, user_id: int, task_id: int) -> Task:
    """Return one of the user's tasks, or raise NotFoundError."""
    task = db.scalar(_base_query(user_id).where(Task.id == task_id))
    if task is None:
        raise NotFoundError("Task not found")
    return task


def create_task(db: Session, user_id: int, data: TaskInput) -> Task:
    """Create a task after validating its (optional) link."""
    _validate_links(db, user_id, data)
    task = Task(user_id=user_id, **data.model_dump())
    db.add(task)
    db.commit()
    logger.info("Task %s created for user %s", task.id, user_id)
    return get_task(db, user_id, task.id)


def update_task(db: Session, user_id: int, task_id: int, data: TaskInput) -> Task:
    """Replace a task's editable fields. Changing due_date resets reminder_sent."""
    task = get_task(db, user_id, task_id)
    _validate_links(db, user_id, data)

    if data.due_date != task.due_date:
        task.reminder_sent = False
    for field, value in data.model_dump().items():
        setattr(task, field, value)

    db.commit()
    db.expire(task)  # reload relationships after link changes
    return get_task(db, user_id, task_id)


def complete_task(db: Session, user_id: int, task_id: int) -> Task:
    """Mark a task done and stamp completed_at (UTC). Completing twice is a no-op."""
    task = get_task(db, user_id, task_id)
    if task.status != TaskStatus.DONE:
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(UTC)
        db.commit()
    return get_task(db, user_id, task_id)


def delete_task(db: Session, user_id: int, task_id: int) -> None:
    """Delete one of the user's tasks."""
    task = get_task(db, user_id, task_id)
    db.delete(task)
    db.commit()
    logger.info("Task %s deleted for user %s", task_id, user_id)
