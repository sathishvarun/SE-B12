"""Task endpoints: /tasks."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.common import Page, PaginationParams
from app.schemas.task import TaskInput, TaskResponse, task_to_response
from app.services import task_service
from app.services.task_service import TaskView

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskResponse])
def list_tasks(
    view: TaskView | None = Query(None, description="today | upcoming | overdue | done"),
    contact_id: int | None = None,
    lead_id: int | None = None,
    deal_id: int | None = None,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[TaskResponse]:
    """List tasks for a view (no view = all pending), paginated."""
    tasks, total = task_service.list_tasks(
        db,
        user.id,
        view=view,
        contact_id=contact_id,
        lead_id=lead_id,
        deal_id=deal_id,
        offset=params.offset,
        limit=params.limit,
    )
    return Page[TaskResponse](
        items=[task_to_response(t) for t in tasks],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Create a task (at most one linked contact/lead/deal, which must be owned)."""
    return task_to_response(task_service.create_task(db, user.id, data))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Get one task."""
    return task_to_response(task_service.get_task(db, user.id, task_id))


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Update a task (changing due_date re-arms the reminder)."""
    return task_to_response(task_service.update_task(db, user.id, task_id, data))


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Mark a task as done."""
    return task_to_response(task_service.complete_task(db, user.id, task_id))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Delete a task."""
    task_service.delete_task(db, user.id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
