"""Task schemas (shared: used by the tasks router and by contact/deal detail responses)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import local_today
from app.models import Task
from app.models.task import TaskPriority, TaskStatus

LinkedType = Literal["contact", "lead", "deal"]


class TaskInput(BaseModel):
    """Body for creating or updating a task. At most one link may be set."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    contact_id: int | None = None
    lead_id: int | None = None
    deal_id: int | None = None


class TaskResponse(BaseModel):
    """A task as returned by the API (see PRPs/api-contract.md)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    due_date: date | None
    priority: TaskPriority
    status: TaskStatus
    contact_id: int | None
    lead_id: int | None
    deal_id: int | None
    linked_type: LinkedType | None
    linked_name: str | None
    is_overdue: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


def task_to_response(task: Task, today: date | None = None) -> TaskResponse:
    """
    Build a TaskResponse from a Task, filling the computed fields.

    Args:
        task: Task ORM object (its contact/lead/deal relationships may be lazy-loaded)
        today: Date used for the overdue check (defaults to today in APP_TIMEZONE)

    Returns:
        TaskResponse with linked_type, linked_name and is_overdue set
    """
    today = today or local_today()
    linked_type: LinkedType | None = None
    linked_name: str | None = None
    if task.contact_id is not None and task.contact is not None:
        linked_type, linked_name = "contact", task.contact.name
    elif task.lead_id is not None and task.lead is not None:
        linked_type, linked_name = "lead", task.lead.name
    elif task.deal_id is not None and task.deal is not None:
        linked_type, linked_name = "deal", task.deal.title

    is_overdue = (
        task.status == TaskStatus.PENDING and task.due_date is not None and task.due_date < today
    )
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
        status=task.status,
        contact_id=task.contact_id,
        lead_id=task.lead_id,
        deal_id=task.deal_id,
        linked_type=linked_type,
        linked_name=linked_name,
        is_overdue=is_overdue,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
