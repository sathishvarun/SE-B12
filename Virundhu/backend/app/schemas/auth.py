"""Request and response bodies for sign-up and sign-in."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    organization_name: str = Field(min_length=2, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accept_terms: bool = False
    phone: str | None = Field(default=None, max_length=20)
    outlets: int | None = Field(default=None, ge=1, le=5000)

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Please accept the Terms and the Privacy Policy to create an account.")
        return v


class LoginIn(BaseModel):
    # Plain string on purpose: sign-in must accept local addresses such as admin@virundhu.local
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10, max_length=200)  # normally sent as a cookie


class OrgOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    is_demo: bool
    city: str | None
    trial_ends_at: datetime | None = None
    is_suspended: bool = False
    locked_since: datetime | None = None  # set while unpaid: the app shows only Plan and billing


class OrgChoice(BaseModel):
    id: int
    name: str
    city: str | None = None
    role: str
    plan: str


class MeOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_superadmin: bool
    role: str | None
    organization: OrgOut | None
    outlet_names: list[str] | None = None  # None = all outlets
    # Every restaurant this login can open (agencies run several). The one above is the one open now.
    organizations: list[OrgChoice] = []




class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None  # never sent to the browser: it goes in the HttpOnly cookie instead
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    user: MeOut
