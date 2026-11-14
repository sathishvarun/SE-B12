"""Admin panel business logic: list/update users and platform stats."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import BadRequestError, NotFoundError
from app.models import (
    Contact,
    Deal,
    RefreshToken,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    User,
)
from app.schemas.admin import AdminStats, AdminUser, AdminUserUpdate
from app.schemas.common import Page
from app.services.contact_service import like_pattern

logger = logging.getLogger(__name__)


def to_admin_user(user: User) -> AdminUser:
    """Build the admin-table representation of a user (plan defaults to free)."""
    plan = user.subscription.plan if user.subscription else SubscriptionPlan.FREE
    return AdminUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        plan=plan,
        created_at=user.created_at,
    )


def list_users(db: Session, search: str | None, page: int, page_size: int) -> Page[AdminUser]:
    """Return a page of all users, newest first, optionally filtered by email/name."""
    query = select(User)
    if search and search.strip():
        pattern = like_pattern(search.strip())  # "%" and "_" in the search match literally
        query = query.where(
            or_(User.email.ilike(pattern, escape="\\"), User.full_name.ilike(pattern, escape="\\"))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(
        query.options(selectinload(User.subscription))
        .order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[AdminUser](
        items=[to_admin_user(u) for u in users], total=total, page=page, page_size=page_size
    )


def update_user(db: Session, admin: User, user_id: int, data: AdminUserUpdate) -> AdminUser:
    """Change a user's is_active / is_admin flags.

    Raises NotFoundError if the user doesn't exist and BadRequestError if an
    admin tries to change their own flags.
    """
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    if user.id == admin.id and (data.is_active is not None or data.is_admin is not None):
        raise BadRequestError("You cannot change your own active or admin status")

    if data.is_active is not None:
        user.is_active = data.is_active
        if not data.is_active:
            # Deactivated users must not be able to refresh their way back in.
            for token in db.scalars(
                select(RefreshToken).where(
                    RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
                )
            ):
                token.revoked = True
    if data.is_admin is not None:
        user.is_admin = data.is_admin

    db.commit()
    db.refresh(user)
    logger.info(
        "Admin id=%s updated user id=%s: is_active=%s is_admin=%s",
        admin.id,
        user.id,
        user.is_active,
        user.is_admin,
    )
    return to_admin_user(user)


def get_stats(db: Session) -> AdminStats:
    """Compute platform-wide counts with SQL aggregates."""
    since = datetime.now(UTC) - timedelta(days=30)
    return AdminStats(
        total_users=db.scalar(select(func.count(User.id))) or 0,
        active_users=db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0,
        pro_subscriptions=db.scalar(
            select(func.count(Subscription.id)).where(
                Subscription.plan == SubscriptionPlan.PRO,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
            )
        )
        or 0,
        signups_last_30_days=db.scalar(select(func.count(User.id)).where(User.created_at >= since))
        or 0,
        total_contacts=db.scalar(select(func.count(Contact.id))) or 0,
        total_deals=db.scalar(select(func.count(Deal.id))) or 0,
    )
