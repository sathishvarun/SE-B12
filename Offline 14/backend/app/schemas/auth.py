"""Request/response schemas for the /auth endpoints (see PRPs/api-contract.md)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models import SubscriptionPlan

PASSWORD_MIN = 8
PASSWORD_MAX = 128


class RegisterRequest(BaseModel):
    """Body for POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Body for POST /auth/login (JSON, not form data)."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX)


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh and POST /auth/logout."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class UserResponse(BaseModel):
    """The current user's profile."""

    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    oauth_provider: Literal["google"] | None
    has_password: bool
    plan: SubscriptionPlan
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Body for PUT /auth/me. All fields optional."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    current_password: str | None = Field(default=None, max_length=PASSWORD_MAX)
    new_password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class ForgotPasswordRequest(BaseModel):
    """Body for POST /auth/forgot-password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body for POST /auth/reset-password."""

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class MessageResponse(BaseModel):
    """Simple {message} response."""

    message: str
