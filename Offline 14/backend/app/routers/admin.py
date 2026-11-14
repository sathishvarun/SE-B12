"""Admin endpoints: /admin/* (403 unless the current user is an admin)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.models import User
from app.schemas.admin import AdminStats, AdminUser, AdminUserUpdate
from app.schemas.common import Page, PaginationParams
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=Page[AdminUser])
def list_users(
    search: str | None = Query(None, max_length=255),
    params: PaginationParams = Depends(),
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Page[AdminUser]:
    """List all users with their plan (search by email or name)."""
    return admin_service.list_users(db, search, params.page, params.page_size)


@router.put("/users/{user_id}", response_model=AdminUser)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUser:
    """Activate/deactivate a user or change admin rights (not for yourself)."""
    return admin_service.update_user(db, admin, user_id, data)


@router.get("/stats", response_model=AdminStats)
def get_stats(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminStats:
    """Platform-wide stats for the admin dashboard."""
    return admin_service.get_stats(db)
