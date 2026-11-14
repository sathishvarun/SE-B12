"""Custom application exceptions, converted to {"detail": ...} responses in main.py."""


class AppError(Exception):
    """Base error carrying an HTTP status code and a client-facing detail message."""

    status_code: int = 500
    default_detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class BadRequestError(AppError):
    """400 - invalid input that passed schema validation."""

    status_code = 400
    default_detail = "Bad request"


class UnauthorizedError(AppError):
    """401 - missing or invalid credentials."""

    status_code = 401
    default_detail = "Not authenticated"


class PaymentRequiredError(AppError):
    """402 - free plan limit reached; upgrade required."""

    status_code = 402
    default_detail = "Plan limit reached. Upgrade to Pro to continue."


class ForbiddenError(AppError):
    """403 - authenticated but not allowed (e.g. non-admin)."""

    status_code = 403
    default_detail = "Forbidden"


class NotFoundError(AppError):
    """404 - resource missing or owned by another user."""

    status_code = 404
    default_detail = "Not found"


class ConflictError(AppError):
    """409 - duplicate or conflicting state."""

    status_code = 409
    default_detail = "Conflict"
