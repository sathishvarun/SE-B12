"""Deal / pipeline business logic. Every query is scoped to the owning user.

Positions: within each (user, stage) column, deals are numbered 0..n-1 by `position`.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import NotFoundError
from app.models import Attachment, Contact, Deal, DealStage, Task
from app.schemas.deal import DealInput
from app.services import plan_limits, storage

logger = logging.getLogger(__name__)

CLOSED_STAGES = plan_limits.CLOSED_STAGES


def is_open(stage: DealStage) -> bool:
    """Return True for prospect/proposal/negotiation, False for won/lost."""
    return stage not in CLOSED_STAGES


def ensure_contact_owned(db: Session, user_id: int, contact_id: int) -> None:
    """
    Check that the contact exists and belongs to the user.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    stmt = select(Contact.id).where(Contact.id == contact_id, Contact.user_id == user_id)
    if db.scalar(stmt) is None:
        raise NotFoundError("Contact not found")


def next_position(db: Session, user_id: int, stage: DealStage) -> int:
    """Return the position at the end of a stage column (max position + 1, or 0 if empty)."""
    stmt = select(func.max(Deal.position)).where(Deal.user_id == user_id, Deal.stage == stage)
    current_max = db.scalar(stmt)
    return 0 if current_max is None else current_max + 1


def column_deals(
    db: Session, user_id: int, stage: DealStage, exclude_id: int | None = None
) -> list[Deal]:
    """Return the deals in one stage column ordered by position (optionally excluding one)."""
    stmt = select(Deal).where(Deal.user_id == user_id, Deal.stage == stage)
    if exclude_id is not None:
        stmt = stmt.where(Deal.id != exclude_id)
    return list(db.scalars(stmt.order_by(Deal.position, Deal.id)))


def renumber(deals: list[Deal]) -> None:
    """Set positions to 0..n-1 in list order."""
    for index, deal in enumerate(deals):
        deal.position = index


def compact_all_columns(db: Session, user_id: int) -> None:
    """Renumber every stage column of the user (e.g. after deals were cascade-deleted)."""
    for stage in DealStage:
        renumber(column_deals(db, user_id, stage))
    db.commit()


def place_deal(
    db: Session, user_id: int, deal: Deal, stage: DealStage, position: int | None
) -> None:
    """
    Move a deal to `stage` at `position` (None = end), keeping both columns numbered 0..n-1.

    Also sets closed_at when entering won/lost from an open stage and clears it when
    entering an open stage. Re-opening a closed deal checks the free-plan open-deal limit.
    Does not commit.

    Raises:
        PaymentRequiredError: Re-opening would exceed the free-plan open-deal limit
    """
    old_stage = deal.stage
    if not is_open(old_stage) and is_open(stage):
        plan_limits.ensure_can_create_open_deal(db, user_id)

    target = column_deals(db, user_id, stage, exclude_id=deal.id)
    if position is None or position > len(target):
        position = len(target)
    target.insert(position, deal)

    if old_stage != stage:
        renumber(column_deals(db, user_id, old_stage, exclude_id=deal.id))
        if is_open(stage):
            deal.closed_at = None
        elif is_open(old_stage):
            deal.closed_at = datetime.now(UTC)
    deal.stage = stage
    renumber(target)


def list_deals(
    db: Session,
    user_id: int,
    stage: DealStage | None,
    contact_id: int | None,
    offset: int,
    limit: int,
) -> tuple[list[Deal], int]:
    """
    Return one page of the user's deals (newest first) and the total count.

    Args:
        db: Database session
        user_id: Owner of the deals
        stage: Only deals in this stage
        contact_id: Only deals for this contact
        offset: Rows to skip
        limit: Page size
    """
    stmt = select(Deal).where(Deal.user_id == user_id)
    if stage is not None:
        stmt = stmt.where(Deal.stage == stage)
    if contact_id is not None:
        stmt = stmt.where(Deal.contact_id == contact_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page_stmt = (
        stmt.options(selectinload(Deal.contact))
        .order_by(Deal.created_at.desc(), Deal.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(page_stmt)), total


def get_board(db: Session, user_id: int) -> dict[str, list[Deal]]:
    """Return all of the user's deals grouped by every stage key, each ordered by position."""
    stmt = (
        select(Deal)
        .where(Deal.user_id == user_id)
        .options(selectinload(Deal.contact))
        .order_by(Deal.position, Deal.id)
    )
    board: dict[str, list[Deal]] = {stage.value: [] for stage in DealStage}
    for deal in db.scalars(stmt):
        board[deal.stage.value].append(deal)
    return board


def get_deal(db: Session, user_id: int, deal_id: int) -> Deal:
    """
    Return a user's deal with its contact loaded.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    stmt = (
        select(Deal)
        .where(Deal.id == deal_id, Deal.user_id == user_id)
        .options(selectinload(Deal.contact))
    )
    deal = db.scalar(stmt)
    if deal is None:
        raise NotFoundError("Deal not found")
    return deal


def get_deal_detail(db: Session, user_id: int, deal_id: int) -> Deal:
    """
    Return a user's deal with contact, tasks and attachments loaded.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    stmt = (
        select(Deal)
        .where(Deal.id == deal_id, Deal.user_id == user_id)
        .options(
            selectinload(Deal.contact),
            selectinload(Deal.tasks).selectinload(Task.deal),
            selectinload(Deal.attachments),
        )
    )
    deal = db.scalar(stmt)
    if deal is None:
        raise NotFoundError("Deal not found")
    return deal


def build_new_deal(db: Session, user_id: int, contact_id: int, data: DealInput) -> Deal:
    """
    Create (add + flush, no commit) a deal at the end of its stage column.

    Raises:
        PaymentRequiredError: Free plan open-deal limit reached (open stages only)
    """
    stage = data.stage or DealStage.PROSPECT
    if is_open(stage):
        plan_limits.ensure_can_create_open_deal(db, user_id)
    deal = Deal(
        user_id=user_id,
        contact_id=contact_id,
        title=data.title,
        value=data.value,
        currency=data.currency,
        stage=stage,
        position=next_position(db, user_id, stage),
        expected_close_date=data.expected_close_date,
        notes=data.notes,
        closed_at=None if is_open(stage) else datetime.now(UTC),
    )
    db.add(deal)
    db.flush()
    return deal


def create_deal(db: Session, user_id: int, data: DealInput) -> Deal:
    """
    Create a deal for one of the user's contacts.

    Raises:
        NotFoundError: Contact not owned by the user
        PaymentRequiredError: Free plan open-deal limit reached
    """
    ensure_contact_owned(db, user_id, data.contact_id)
    deal = build_new_deal(db, user_id, data.contact_id, data)
    db.commit()
    logger.info("Created deal %s for user %s", deal.id, user_id)
    return get_deal(db, user_id, deal.id)


def update_deal(db: Session, user_id: int, deal_id: int, data: DealInput) -> Deal:
    """
    Update a user's deal. A changed `stage` moves the deal to the end of the new column.

    Raises:
        NotFoundError: Deal or contact not owned by the user
        PaymentRequiredError: Re-opening a closed deal exceeds the open-deal limit
    """
    deal = get_deal(db, user_id, deal_id)
    if data.contact_id != deal.contact_id:
        ensure_contact_owned(db, user_id, data.contact_id)

    if data.stage is not None and data.stage != deal.stage:
        place_deal(db, user_id, deal, data.stage, position=None)

    deal.title = data.title
    deal.contact_id = data.contact_id
    deal.value = data.value
    deal.currency = data.currency
    deal.expected_close_date = data.expected_close_date
    deal.notes = data.notes
    db.commit()
    db.expire(deal, ["contact"])
    return get_deal(db, user_id, deal.id)


def move_deal(db: Session, user_id: int, deal_id: int, stage: DealStage, position: int) -> Deal:
    """
    Move a deal on the Kanban board (PATCH /deals/{id}/stage).

    Raises:
        NotFoundError: Deal not owned by the user
        PaymentRequiredError: Re-opening a closed deal exceeds the open-deal limit
    """
    deal = get_deal(db, user_id, deal_id)
    place_deal(db, user_id, deal, stage, position)
    db.commit()
    return get_deal(db, user_id, deal.id)


def delete_deal(db: Session, user_id: int, deal_id: int) -> None:
    """
    Delete a user's deal and close the gap in its column.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    deal = get_deal(db, user_id, deal_id)
    stage = deal.stage
    # Attachment rows cascade in the database; the files on disk must be removed by us.
    file_paths = db.scalars(
        select(Attachment.storage_path).where(Attachment.deal_id == deal_id)
    ).all()
    db.delete(deal)
    db.flush()
    renumber(column_deals(db, user_id, stage))
    db.commit()
    for path in file_paths:
        storage.get_storage().delete(path)
    logger.info("Deleted deal %s for user %s", deal_id, user_id)
