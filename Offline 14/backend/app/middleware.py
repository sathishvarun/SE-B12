"""ASGI middleware that rejects request bodies larger than a fixed limit.

FastAPI reads a whole multipart upload to disk *before* it checks login or the
10 MB rule, so without this anyone could fill the server's disk with one huge
request. This middleware stops the request as soon as it gets too big.
"""

import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class BodyTooLargeError(Exception):
    """Raised internally when the streamed body passes the limit."""


class MaxBodySizeMiddleware:
    """Return 413 for any request whose body is larger than `max_bytes`."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: the client told us the size up front.
        for name, value in scope.get("headers", []):
            if name == b"content-length" and value.isdigit() and int(value) > self.max_bytes:
                await _send_413(send)
                return

        # Slow path (chunked uploads): count bytes as they arrive.
        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise BodyTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except BodyTooLargeError:
            logger.warning("Rejected request body over %s bytes", self.max_bytes)
            if not response_started:
                await _send_413(send)


async def _send_413(send: Send) -> None:
    """Send a minimal JSON 413 response."""
    body = b'{"detail":"Request body too large"}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
