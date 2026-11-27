"""Sign-up, sign-in, refresh, sign-out and profile."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.cookies import clear_refresh_cookie, read_refresh_cookie, to_cookie
from app.auth.deps import get_current_user
from app.database import get_db
from app.limiter import limiter
from app.models import User
from app.schemas.auth import LoginIn, MeOut, RefreshIn, RegisterIn, TokenOut
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenOut, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
def register(request: Request, response: Response, body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    """Create an account and a restaurant with a 14-day trial."""
    return to_cookie(response, auth_service.register(db, body))


@router.post("/login", response_model=TokenOut, response_model_exclude_none=True)
@limiter.limit("10/minute")
def login(request: Request, response: Response, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Sign in with email and password."""
    ip = request.client.host if request.client else None
    device = request.headers.get("user-agent")
    return to_cookie(response, auth_service.login(db, body.email, body.password, ip, device))


@router.post("/refresh", response_model=TokenOut, response_model_exclude_none=True)
@limiter.limit("30/minute")
def refresh(
    request: Request, response: Response, body: RefreshIn | None = None, db: Session = Depends(get_db)
) -> TokenOut:
    """Swap the session cookie for a new short access token (and a new cookie)."""
    token = read_refresh_cookie(request) or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in again.")
    try:
        return to_cookie(response, auth_service.refresh(db, token))
    except HTTPException:
        clear_refresh_cookie(response)
        raise


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, body: RefreshIn | None = None, db: Session = Depends(get_db)) -> None:
    """Sign out: the session is revoked on the server and the cookie is removed."""
    token = read_refresh_cookie(request) or (body.refresh_token if body else None)
    if token:
        auth_service.logout(db, token)
    clear_refresh_cookie(response)


@router.get("/me", response_model=MeOut)
def me(
    user: User = Depends(get_current_user), db: Session = Depends(get_db), x_org_id: int | None = Header(default=None)
) -> MeOut:
    """The signed-in user's profile and the restaurant open now (X-Org-Id switches between their own restaurants)."""
    return auth_service.build_me(db, user, x_org_id)


@router.get("/verify-email", include_in_schema=False)
def verify_email(token: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """The link in the welcome email: marks the email address as confirmed."""
    from app.config import settings
    from app.services.welcome import check_token

    uid = token.split(".", 1)[0]
    user = db.get(User, int(uid)) if uid.isdigit() else None
    if user is None or not check_token(token, user):
        return RedirectResponse(f"{settings.APP_URL}/login?email_confirmed=0")
    user.is_verified = True
    db.commit()
    return RedirectResponse(f"{settings.APP_URL}/login?email_confirmed=1")
