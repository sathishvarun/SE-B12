"""The refresh token lives only in an HttpOnly cookie: page scripts (and anything injected into the page) can't read it.

- HttpOnly: JavaScript can't see it.  - Secure: sent only over HTTPS on the live site.
- SameSite=Strict: other websites can't make the browser send it.  - Path: sent only to /api/v1/auth.
"""

from fastapi import Request, Response

from app.config import settings
from app.schemas.auth import TokenOut

COOKIE = "vr_session"
PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=PATH,
        httponly=True,
        secure=settings.APP_URL.startswith("https://"),
        samesite="strict",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE, path=PATH, httponly=True, secure=settings.APP_URL.startswith("https://"), samesite="strict"
    )


def read_refresh_cookie(request: Request) -> str | None:
    return request.cookies.get(COOKIE)


def to_cookie(response: Response, tokens: TokenOut) -> TokenOut:
    """Put the refresh token in the HttpOnly cookie; the browser's scripts only ever get the short access token."""
    if tokens.refresh_token:
        set_refresh_cookie(response, tokens.refresh_token)
    return tokens.model_copy(update={"refresh_token": None})
