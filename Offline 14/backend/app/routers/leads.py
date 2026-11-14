"""Lead endpoints: /leads."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import LeadSource, LeadStatus, User
from app.schemas.common import Page, PaginationParams
from app.schemas.contact import ContactResponse
from app.schemas.deal import DealResponse
from app.schemas.lead import (
    ConvertLeadInput,
    ConvertLeadResult,
    LeadInput,
    LeadResponse,
    LeadStatusUpdate,
)
from app.services import lead_service

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=Page[LeadResponse])
def list_leads(
    status_filter: LeadStatus | None = Query(None, alias="status"),
    source: LeadSource | None = None,
    search: str | None = Query(None, max_length=255),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[LeadResponse]:
    """List leads (filter by status/source, search name/email/company), newest first."""
    leads, total = lead_service.list_leads(
        db, user.id, status_filter, source, search, params.offset, params.limit
    )
    return Page[LeadResponse](
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    data: LeadInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LeadResponse:
    """Create a lead."""
    return LeadResponse.model_validate(lead_service.create_lead(db, user.id, data))


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LeadResponse:
    """Lead detail."""
    return LeadResponse.model_validate(lead_service.get_lead(db, user.id, lead_id))


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    data: LeadInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LeadResponse:
    """Update a lead's details."""
    return LeadResponse.model_validate(lead_service.update_lead(db, user.id, lead_id, data))


@router.patch("/{lead_id}/status", response_model=LeadResponse)
def update_lead_status(
    lead_id: int,
    data: LeadStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LeadResponse:
    """Change a lead's status (400 for "converted" or if the lead is already converted)."""
    lead = lead_service.update_lead_status(db, user.id, lead_id, data.status)
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Delete a lead."""
    lead_service.delete_lead(db, user.id, lead_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{lead_id}/convert", response_model=ConvertLeadResult, status_code=status.HTTP_201_CREATED
)
def convert_lead(
    lead_id: int,
    data: ConvertLeadInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConvertLeadResult:
    """Convert a lead into a contact + prospect deal (409 if already converted)."""
    lead, contact, deal = lead_service.convert_lead(db, user.id, lead_id, data)
    return ConvertLeadResult(
        lead=LeadResponse.model_validate(lead),
        contact=ContactResponse.model_validate(contact),
        deal=DealResponse.model_validate(deal),
    )
