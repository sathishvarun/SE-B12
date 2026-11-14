"""Tag endpoints: /tags."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.contact import Tag, TagInput
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[Tag])
def list_tags(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Tag]:
    """List the current user's tags."""
    return [Tag.model_validate(t) for t in tag_service.list_tags(db, user.id)]


@router.post("", response_model=Tag, status_code=status.HTTP_201_CREATED)
def create_tag(
    data: TagInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Tag:
    """Create a tag (409 if the name already exists)."""
    return Tag.model_validate(tag_service.create_tag(db, user.id, data))
