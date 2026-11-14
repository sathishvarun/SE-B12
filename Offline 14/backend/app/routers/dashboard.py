"""Dashboard endpoints: /dashboard/summary and /dashboard/analytics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.dashboard import DashboardAnalytics, DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardSummary:
    """Headline counters (contacts, open leads/deals, pipeline value, task counts)."""
    return dashboard_service.get_summary(db, user.id)


@router.get("/analytics", response_model=DashboardAnalytics)
def analytics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardAnalytics:
    """Chart data for the dashboard."""
    return dashboard_service.get_analytics(db, user.id)
