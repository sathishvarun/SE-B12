"""Contact endpoints: /contacts."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.common import Page, PaginationParams
from app.schemas.contact import (
    ContactDetail,
    ContactInput,
    ContactOption,
    ContactResponse,
    contact_to_detail,
)
from app.services import contact_service

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=Page[ContactResponse])
def list_contacts(
    search: str | None = Query(None, max_length=255),
    tag_id: int | None = None,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ContactResponse]:
    """List contacts (search by name/email/company, filter by tag), ordered by name."""
    contacts, total = contact_service.list_contacts(
        db, user.id, search, tag_id, params.offset, params.limit
    )
    return Page[ContactResponse](
        items=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/options", response_model=list[ContactOption])
def list_contact_options(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ContactOption]:
    """All contacts as {id, name, company} for select dropdowns."""
    return [
        ContactOption.model_validate(c) for c in contact_service.list_contact_options(db, user.id)
    ]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    data: ContactInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ContactResponse:
    """Create a contact (402 if the free plan limit is reached)."""
    return ContactResponse.model_validate(contact_service.create_contact(db, user.id, data))


@router.get("/{contact_id}", response_model=ContactDetail)
def get_contact(
    contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> ContactDetail:
    """Contact detail with tags, deals, tasks and attachments."""
    return contact_to_detail(contact_service.get_contact_detail(db, user.id, contact_id))


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    data: ContactInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContactResponse:
    """Update a contact."""
    contact = contact_service.update_contact(db, user.id, contact_id, data)
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Delete a contact (its deals and attachments are deleted too)."""
    contact_service.delete_contact(db, user.id, contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
