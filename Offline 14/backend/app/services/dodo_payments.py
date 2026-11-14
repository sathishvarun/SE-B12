"""Thin wrapper around the Dodo Payments REST API (httpx) plus webhook signature verification.

Checked against docs.dodopayments.com (Nov 2026):
  - Auth: ``Authorization: Bearer <DODO_PAYMENTS_API_KEY>``
  - Base URL: https://test.dodopayments.com (test_mode) / https://live.dodopayments.com (live_mode)
  - Checkout:  POST /checkouts  {product_cart: [{product_id, quantity}], customer: {email, name},
               return_url, metadata}  ->  {session_id, checkout_url}
  - Cancel:    PATCH /subscriptions/{subscription_id}  {"status": "cancelled"}
  - Webhooks:  Standard Webhooks (headers webhook-id / webhook-timestamp / webhook-signature),
               body {business_id, type, timestamp, data}; subscription events include
               subscription.active / renewed / on_hold / failed / cancelled / expired / past_due.

STILL TO VERIFY against a real test-mode webhook (assumptions kept in billing_service):
  - subscription ``data`` field names: subscription_id, status, next_billing_date, metadata,
    customer.customer_id (the docs page lists the first four; ``customer`` is from the API schema).
  - checkout ``metadata`` is copied onto the subscription (so data.metadata.user_id is present).
"""

import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from app.config import settings
from app.exceptions import AppError, BadRequestError, UnauthorizedError
from app.models import User

logger = logging.getLogger(__name__)

BASE_URLS = {
    "test_mode": "https://test.dodopayments.com",
    "live_mode": "https://live.dodopayments.com",
}
WEBHOOK_TOLERANCE_SECONDS = 5 * 60
REQUEST_TIMEOUT_SECONDS = 15.0


class PaymentProviderError(AppError):
    """502 - the payment provider returned an error or was unreachable."""

    status_code = 502
    default_detail = "Payment provider error. Please try again later."


def _base_url() -> str:
    """Return the API base URL for the configured environment."""
    return BASE_URLS.get(settings.DODO_PAYMENTS_ENVIRONMENT, BASE_URLS["test_mode"])


def _headers() -> dict[str, str]:
    """Auth headers for Dodo API calls."""
    if not settings.DODO_PAYMENTS_API_KEY:
        raise BadRequestError("Payments are not configured")
    return {
        "Authorization": f"Bearer {settings.DODO_PAYMENTS_API_KEY}",
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Send one JSON request to Dodo and return the decoded JSON body (or {})."""
    headers = _headers()
    try:
        async with httpx.AsyncClient(
            base_url=_base_url(), timeout=REQUEST_TIMEOUT_SECONDS
        ) as client:
            response = await client.request(method, path, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.error("Dodo %s %s failed: %s", method, path, exc)
        raise PaymentProviderError() from exc
    if response.status_code >= 400:
        logger.error(
            "Dodo %s %s returned %s: %s", method, path, response.status_code, response.text[:500]
        )
        raise PaymentProviderError()
    if not response.content:
        return {}
    return response.json()


async def create_checkout(user: User, return_url: str) -> str:
    """
    Create a hosted checkout session for the Pro subscription product.

    Args:
        user: The buyer; user.id is passed in metadata so the webhook can find them
        return_url: Where Dodo redirects after checkout

    Returns:
        The hosted checkout URL

    Raises:
        BadRequestError: payments not configured (no API key / product id)
        PaymentProviderError: Dodo API error
    """
    if not settings.DODO_PAYMENTS_API_KEY or not settings.DODO_PAYMENTS_PRO_PRODUCT_ID:
        raise BadRequestError("Payments are not configured")
    payload: dict[str, Any] = {
        "product_cart": [{"product_id": settings.DODO_PAYMENTS_PRO_PRODUCT_ID, "quantity": 1}],
        "customer": {"email": user.email, "name": user.full_name or user.email},
        "return_url": return_url,
        "metadata": {"user_id": str(user.id)},
    }
    data = await _request("POST", "/checkouts", payload)
    checkout_url = data.get("checkout_url")
    if not checkout_url:
        logger.error("Dodo checkout response had no checkout_url: %s", data)
        raise PaymentProviderError()
    return str(checkout_url)


async def cancel_subscription(subscription_id: str) -> None:
    """Cancel a Dodo subscription immediately (the webhook then downgrades the user)."""
    await _request("PATCH", f"/subscriptions/{subscription_id}", {"status": "cancelled"})
    logger.info("Requested cancellation of Dodo subscription %s", subscription_id)


def _signing_key(secret: str) -> bytes:
    """Decode the webhook secret (``whsec_<base64>``) into raw HMAC key bytes."""
    raw = secret.removeprefix("whsec_")
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        # Not base64: fall back to using the secret bytes directly.
        return raw.encode()


def verify_webhook(headers: Mapping[str, str], raw_body: bytes) -> dict[str, Any]:
    """
    Verify a Standard Webhooks signature and return the parsed JSON payload.

    Signed content is ``f"{webhook-id}.{webhook-timestamp}.{raw body}"`` (HMAC-SHA256,
    base64); the signature header holds space-separated ``v1,<sig>`` entries.

    Raises:
        UnauthorizedError: missing headers, stale timestamp or bad signature
        BadRequestError: correctly signed but not a JSON object
    """
    secret = settings.DODO_PAYMENTS_WEBHOOK_SECRET
    if not secret:
        logger.error("Webhook received but DODO_PAYMENTS_WEBHOOK_SECRET is not set")
        raise UnauthorizedError("Invalid webhook signature")

    lowered = {k.lower(): v for k, v in headers.items()}
    msg_id = lowered.get("webhook-id")
    timestamp = lowered.get("webhook-timestamp")
    signature_header = lowered.get("webhook-signature")
    if not msg_id or not timestamp or not signature_header:
        raise UnauthorizedError("Invalid webhook signature")

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise UnauthorizedError("Invalid webhook signature") from exc
    if abs(time.time() - ts) > WEBHOOK_TOLERANCE_SECONDS:
        raise UnauthorizedError("Webhook timestamp outside tolerance")

    signed = f"{msg_id}.{timestamp}.".encode() + raw_body
    expected = base64.b64encode(
        hmac.new(_signing_key(secret), signed, hashlib.sha256).digest()
    ).decode()

    valid = False
    for entry in signature_header.split():
        version, _, sig = entry.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            valid = True
            break
    if not valid:
        raise UnauthorizedError("Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except ValueError as exc:
        raise BadRequestError("Invalid webhook payload") from exc
    if not isinstance(payload, dict):
        raise BadRequestError("Invalid webhook payload")
    return payload
