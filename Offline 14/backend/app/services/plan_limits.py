"""Free-plan limits: max contacts and max open deals per user (Pro is unlimited)."""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import PaymentRequiredError
from app.models import Contact, Deal, DealStage, Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)

CLOSED_STAGES = (DealStage.WON, DealStage.LOST)


def is_pro(db: Session, user_id: int) -> bool:
    """Return True if the user has a Pro subscription (no row means Free)."""
    plan = db.scalar(select(Subscription.plan).where(Subscription.user_id == user_id))
    return plan == SubscriptionPlan.PRO


def count_contacts(db: Session, user_id: int) -> int:
    """Return how many contacts the user has."""
    stmt = select(func.count()).select_from(Contact).where(Contact.user_id == user_id)
    return db.scalar(stmt) or 0


def count_open_deals(db: Session, user_id: int) -> int:
    """Return how many of the user's deals are open (stage not won/lost)."""
    stmt = (
        select(func.count())
        .select_from(Deal)
        .where(Deal.user_id == user_id, Deal.stage.not_in(CLOSED_STAGES))
    )
    return db.scalar(stmt) or 0


def ensure_can_create_contact(db: Session, user_id: int) -> None:
    """
    Raise 402 if a Free user already has the maximum number of contacts.

    Args:
        db: Database session
        user_id: Owner of the new contact

    Raises:
        PaymentRequiredError: Free plan contact limit reached
    """
    if is_pro(db, user_id):
        return
    limit = settings.FREE_PLAN_MAX_CONTACTS
    if count_contacts(db, user_id) >= limit:
        logger.info("User %s hit the free contact limit (%s)", user_id, limit)
        raise PaymentRequiredError(
            f"Free plan limit reached: you can have up to {limit} contacts. "
            "Upgrade to Pro for unlimited contacts."
        )


def ensure_can_create_open_deal(db: Session, user_id: int) -> None:
    """
    Raise 402 if a Free user already has the maximum number of open deals.

    Args:
        db: Database session
        user_id: Owner of the new (or re-opened) deal

    Raises:
        PaymentRequiredError: Free plan open-deal limit reached
    """
    if is_pro(db, user_id):
        return
    limit = settings.FREE_PLAN_MAX_OPEN_DEALS
    if count_open_deals(db, user_id) >= limit:
        logger.info("User %s hit the free open-deal limit (%s)", user_id, limit)
        raise PaymentRequiredError(
            f"Free plan limit reached: you can have up to {limit} open deals. "
            "Close some deals or upgrade to Pro for unlimited deals."
        )
