"""Attachment endpoints: /attachments (upload, download, delete)."""

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.attachment import AttachmentResponse
from app.services import attachment_service

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(
    file: UploadFile = File(...),
    contact_id: int | None = Form(None),
    deal_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """Upload a file to exactly one contact or deal (400 bad type, 413 too large)."""
    try:
        attachment = attachment_service.create_attachment(
            db,
            user.id,
            stream=file.file,
            filename=file.filename,
            content_type=file.content_type,
            contact_id=contact_id,
            deal_id=deal_id,
            declared_size=file.size,
        )
    finally:
        file.file.close()
    return AttachmentResponse.model_validate(attachment)


@router.get("/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """Download a file as an attachment with its stored content type."""
    attachment, path = attachment_service.get_attachment_file(db, user.id, attachment_id)
    return FileResponse(
        path,
        media_type=attachment.content_type,
        filename=attachment.filename,
        content_disposition_type="attachment",
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Delete an attachment (DB row and file)."""
    attachment_service.delete_attachment(db, user.id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
