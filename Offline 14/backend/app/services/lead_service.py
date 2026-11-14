"""Lead business logic, including lead -> contact + deal conversion."""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import Contact, Deal, DealStage, Lead, LeadSource, LeadStatus
from app.schemas.deal import DealInput
from app.schemas.lead import ConvertLeadInput, LeadInput
from app.services import contact_service, deal_service, plan_limits

logger = logging.getLogger(__name__)


def list_leads(
    db: Session,
    user_id: int,
    status: LeadStatus | None,
    source: LeadSource | None,
    search: str | None,
    offset: int,
    limit: int,
) -> tuple[list[Lead], int]:
    """
    Return one page of the user's leads (newest first) and the total count.

    Args:
        db: Database session
        user_id: Owner of the leads
        status: Only leads with this status
        source: Only leads from this source
        search: Case-insensitive match on name, email or company
        offset: Rows to skip
        limit: Page size
    """
    stmt = select(Lead).where(Lead.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    if source is not None:
        stmt = stmt.where(Lead.source == source)
    if search and search.strip():
        pattern = contact_service.like_pattern(search.strip())
        stmt = stmt.where(
            or_(
                Lead.name.ilike(pattern, escape="\\"),
                Lead.email.ilike(pattern, escape="\\"),
                Lead.company.ilike(pattern, escape="\\"),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page_stmt = stmt.order_by(Lead.created_at.desc(), Lead.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(page_stmt)), total


def get_lead(db: Session, user_id: int, lead_id: int) -> Lead:
    """
    Return a user's lead.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    lead = db.scalar(select(Lead).where(Lead.id == lead_id, Lead.user_id == user_id))
    if lead is None:
        raise NotFoundError("Lead not found")
    return lead


def create_lead(db: Session, user_id: int, data: LeadInput) -> Lead:
    """Create a new lead (status "new") for the user."""
    lead = Lead(user_id=user_id, status=LeadStatus.NEW, **data.model_dump())
    db.add(lead)
    db.commit()
    logger.info("Created lead %s for user %s", lead.id, user_id)
    return lead


def update_lead(db: Session, user_id: int, lead_id: int, data: LeadInput) -> Lead:
    """
    Update a user's lead details (not its status).

    Raises:
        NotFoundError: Missing or owned by another user
    """
    lead = get_lead(db, user_id, lead_id)
    for field, value in data.model_dump().items():
        setattr(lead, field, value)
    db.commit()
    return lead


def update_lead_status(db: Session, user_id: int, lead_id: int, status: LeadStatus) -> Lead:
    """
    Change a lead's status.

    Raises:
        NotFoundError: Missing or owned by another user
        BadRequestError: Setting "converted" directly, or changing a converted lead
    """
    if status == LeadStatus.CONVERTED:
        raise BadRequestError("Use the convert endpoint to mark a lead as converted")
    lead = get_lead(db, user_id, lead_id)
    if lead.status == LeadStatus.CONVERTED:
        raise BadRequestError("A converted lead's status cannot be changed")
    lead.status = status
    db.commit()
    return lead


def delete_lead(db: Session, user_id: int, lead_id: int) -> None:
    """
    Delete a user's lead.

    Raises:
        NotFoundError: Missing or owned by another user
    """
    lead = get_lead(db, user_id, lead_id)
    db.delete(lead)
    db.commit()
    logger.info("Deleted lead %s for user %s", lead_id, user_id)


def convert_lead(
    db: Session, user_id: int, lead_id: int, data: ConvertLeadInput
) -> tuple[Lead, Contact, Deal]:
    """
    Convert a lead into a Contact plus a prospect Deal, in one transaction.

    Raises:
        NotFoundError: Missing or owned by another user
        ConflictError: The lead was already converted
        PaymentRequiredError: Free plan contact or open-deal limit reached
    """
    get_lead(db, user_id, lead_id)  # 404 if missing or another seller's
    # Lock the lead row so a double-click can't convert it twice at the same time.
    lead = db.scalars(
        select(Lead)
        .where(Lead.id == lead_id, Lead.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if lead.status == LeadStatus.CONVERTED:
        raise ConflictError("Lead has already been converted")

    plan_limits.ensure_can_create_contact(db, user_id)
    try:
        contact = Contact(
            user_id=user_id,
            name=lead.name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            notes=lead.notes,
        )
        contact.tags = []
        db.add(contact)
        db.flush()  # assigns contact.id

        deal_data = DealInput(
            title=data.deal_title,
            contact_id=contact.id,
            value=data.deal_value,
            stage=DealStage.PROSPECT,
            expected_close_date=data.expected_close_date,
        )
        deal = deal_service.build_new_deal(db, user_id, contact.id, deal_data)
        deal.contact = contact

        lead.status = LeadStatus.CONVERTED
        lead.converted_contact_id = contact.id
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info("Converted lead %s -> contact %s, deal %s", lead.id, contact.id, deal.id)
    return lead, contact, deal
