"""Billing endpoints: /billing (subscription, checkout, cancel, Dodo webhook)."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.billing import CheckoutResponse, SubscriptionResponse, WebhookAck
from app.services import billing_service, dodo_payments

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Current plan, status, limits (null on Pro) and usage."""
    return billing_service.get_subscription_overview(db, user)


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CheckoutResponse:
    """Start a Dodo Payments checkout for Pro (409 if already Pro)."""
    url = await billing_service.start_checkout(db, user)
    return CheckoutResponse(checkout_url=url)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    """Cancel the Pro subscription at Dodo; the plan changes when the webhook confirms."""
    return await billing_service.cancel_subscription(db, user)


@router.post("/webhook", response_model=WebhookAck)
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> WebhookAck:
    """Public Dodo webhook: verify the signature (401 if invalid), then apply the event."""
    raw_body = await request.body()
    payload = dodo_payments.verify_webhook(request.headers, raw_body)
    change = billing_service.handle_webhook_event(db, payload)
    if change is not None:
        background_tasks.add_task(billing_service.send_subscription_changed_email, change)
    return WebhookAck(received=True)
