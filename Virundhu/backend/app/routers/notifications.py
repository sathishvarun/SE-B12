"""The bell: instant alerts for the signed-in user."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context
from app.database import get_db
from app.models import Notification

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    review_id: int | None
    severity: str
    title: str
    body: str
    created_at: datetime
    read: bool


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]


@router.get("", response_model=NotificationList)
def list_notifications(
    limit: int = 30, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> NotificationList:
    """Latest alerts and the unread count."""
    base = select(Notification).where(Notification.user_id == ctx.user.id, Notification.organization_id == ctx.org.id)
    unread = db.scalar(base.with_only_columns(func.count(Notification.id)).where(Notification.read_at.is_(None))) or 0
    rows = db.scalars(base.order_by(Notification.id.desc()).limit(min(limit, 100)))
    return NotificationList(
        unread=unread,
        items=[
            NotificationOut(
                id=n.id,
                review_id=n.review_id,
                severity=n.severity,
                title=n.title,
                body=n.body,
                created_at=n.created_at,
                read=n.read_at is not None,
            )
            for n in rows
        ],
    )


@router.post("/read-all")
def read_all(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Mark every alert as read."""
    db.execute(
        update(Notification)
        .where(Notification.user_id == ctx.user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return {"ok": True}
