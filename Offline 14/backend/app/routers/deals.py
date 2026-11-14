"""Deal / pipeline endpoints: /deals."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import DealStage, User
from app.schemas.common import Page, PaginationParams
from app.schemas.deal import (
    DealBoard,
    DealDetail,
    DealInput,
    DealResponse,
    MoveDealInput,
    deal_to_detail,
)
from app.services import deal_service

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("", response_model=Page[DealResponse])
def list_deals(
    stage: DealStage | None = None,
    contact_id: int | None = Query(None),
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[DealResponse]:
    """List deals (filter by stage / contact), newest first."""
    deals, total = deal_service.list_deals(
        db, user.id, stage, contact_id, params.offset, params.limit
    )
    return Page[DealResponse](
        items=[DealResponse.model_validate(d) for d in deals],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/board", response_model=DealBoard)
def get_board(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DealBoard:
    """All deals grouped by stage (every stage key present), each ordered by position."""
    board = deal_service.get_board(db, user.id)
    return DealBoard(
        **{stage: [DealResponse.model_validate(d) for d in deals] for stage, deals in board.items()}
    )


@router.post("", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    data: DealInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DealResponse:
    """Create a deal (404 if the contact isn't yours, 402 at the free open-deal limit)."""
    return DealResponse.model_validate(deal_service.create_deal(db, user.id, data))


@router.get("/{deal_id}", response_model=DealDetail)
def get_deal(
    deal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DealDetail:
    """Deal detail with contact, tasks and attachments."""
    return deal_to_detail(deal_service.get_deal_detail(db, user.id, deal_id))


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    data: DealInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DealResponse:
    """Update a deal."""
    return DealResponse.model_validate(deal_service.update_deal(db, user.id, deal_id, data))


@router.patch("/{deal_id}/stage", response_model=DealResponse)
def move_deal(
    deal_id: int,
    data: MoveDealInput,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DealResponse:
    """Move a deal to a stage/position (sets closed_at on won/lost, clears it otherwise)."""
    deal = deal_service.move_deal(db, user.id, deal_id, data.stage, data.position)
    return DealResponse.model_validate(deal)


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deal(
    deal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Delete a deal."""
    deal_service.delete_deal(db, user.id, deal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
