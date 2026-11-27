"""Account safety and the owner's data rights: forgot / reset / change password, export everything, delete everything.

- Forgot password never reveals whether an email has an account.
- Reset links are single-use, expire after 1 hour, and only their SHA-256 hash is stored.
- Resetting or changing a password signs the user out everywhere (all refresh tokens revoked).
- Export gives the owner every review and AI result as a CSV (right to access).
- Delete removes the restaurant and all its data for good (right to erasure); the platform admin can't be deleted here.
"""

import csv
import io
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.auth import lockout
from app.auth.cookies import clear_refresh_cookie, set_refresh_cookie
from app.auth.deps import OrgContext, get_current_user, get_org_context
from app.auth.passwords import weak_reason
from app.auth.security import hash_password, hash_token, new_opaque_token, verify_password
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import Membership, Organization, Outlet, PasswordResetToken, RefreshToken, Review, ReviewAnalysis, User
from app.services import activity, two_step
from app.services.auth_service import issue_tokens
from app.services.emailer import send_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["account"])
RESET_MINUTES = 30


def _org_of(db: Session, user: User) -> dict:
    """The user's restaurant, for the activity log."""
    org = db.scalar(
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    return {"org_id": org.id, "restaurant": org.name} if org else {}


def _sign_out_everywhere(db: Session, user_id: int) -> None:
    """Revoke every refresh token and refuse every access token issued until now."""
    now = datetime.now(UTC)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True, expires_at=now))
    db.execute(update(User).where(User.id == user_id).values(sessions_valid_after=now))


# ---------------- Forgot / reset password ----------------
class ForgotIn(BaseModel):
    email: EmailStr


@router.post("/auth/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotIn, db: Session = Depends(get_db)) -> dict:
    """Always answers the same way, so nobody can test which emails have accounts."""
    user = db.scalar(select(User).where(User.email == body.email.lower(), User.is_active))
    if user is not None:
        token, token_hash = new_opaque_token()
        db.add(
            PasswordResetToken(
                user_id=user.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(minutes=RESET_MINUTES)
            )
        )
        db.commit()
        link = f"{settings.APP_URL}/reset-password?token={token}"
        send_email(
            [user.email],
            "Reset your Virundhu password",
            f"Hi {user.full_name.split(' ')[0]},\n\nSomeone asked to reset the password for your Virundhu account "
            f"({user.email}). If that was you, choose a new password below. This link works once and expires in "
            f"{RESET_MINUTES} minutes.\n\n{link}\n\n"
            "Didn't ask for this? Ignore this email and your password stays the same.\n",
        )
    return {"ok": True, "message": "If that email has an account, a reset link is on its way."}


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


@router.post("/auth/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetIn, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(body.token)))
    if row is None or row.used_at is not None or row.expires_at < datetime.now(UTC):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "This reset link has expired or was already used. Ask for a new one."
        )
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This account is switched off. Contact support.")
    problem = weak_reason(body.password, user.email, user.full_name)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    user.hashed_password = hash_password(body.password)
    lockout.clear(user.email)
    row.used_at = datetime.now(UTC)
    _sign_out_everywhere(db, user.id)
    activity.record(
        db, "password_reset", email=user.email, detail="Used an emailed reset link", **_org_of(db, user), commit=False
    )
    db.commit()
    _password_changed_email(user, request)
    return {"ok": True}


# ---------------- Change password ----------------
class ChangeIn(BaseModel):
    current_password: str = Field(default="", max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/account/password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    response: Response,
    body: ChangeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Google-only accounts (no password yet) can set one without the current password."""
    if user.hashed_password and not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password isn't right.")
    problem = weak_reason(body.new_password, user.email, user.full_name)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    user.hashed_password = hash_password(body.new_password)
    _sign_out_everywhere(db, user.id)
    activity.record(
        db, "password_changed", email=user.email, detail="Changed in Settings", **_org_of(db, user), commit=False
    )
    db.commit()
    _password_changed_email(user, request)
    # This device stays signed in with a fresh session; every other device (and any stolen token) is out.
    fresh = issue_tokens(db, user)
    set_refresh_cookie(response, fresh.refresh_token or "")
    return {
        "ok": True,
        "message": "Password changed. Other devices have been signed out.",
        "access_token": fresh.access_token,
    }


@router.post("/account/sign-out-everywhere")
@limiter.limit("5/minute")
def sign_out_everywhere(
    request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Lost a phone? Every device, this one included, has to sign in again."""
    _sign_out_everywhere(db, user.id)
    activity.record(
        db, "signed_out_everywhere", email=user.email, detail="From Settings", **_org_of(db, user), commit=False
    )
    db.commit()
    clear_refresh_cookie(response)
    return {"ok": True}


def _password_changed_email(user: User, request: Request) -> None:
    """Tell the owner their password changed, so they notice if it wasn't them."""
    when = datetime.now(UTC).astimezone(ZoneInfo(settings.TIMEZONE)).strftime("%d %b %Y, %I:%M %p")
    device = (request.headers.get("user-agent") or "unknown device")[:120]
    send_email(
        [user.email],
        "Your Virundhu password was changed",
        f"Hi {user.full_name.split(' ')[0]},\n\nThe password for your Virundhu account ({user.email}) was changed on "
        f"{when}. Other devices were signed out to keep your account safe.\n\nDevice: {device}\n\n"
        "Your password is updated. Please sign in with your new password:\n\n"
        f"{settings.APP_URL}/login\n\n"
        "Wasn't you? Reset your password straight away at "
        f"{settings.APP_URL}/forgot-password and tell us by replying to this email.\n",
    )


# ---------------- Export ----------------
def _owner(ctx: OrgContext) -> OrgContext:
    if ctx.role != "owner" or ctx.user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the restaurant owner can do this.")
    return ctx


@router.get("/account/export")
def export_data(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> StreamingResponse:
    """Every review of this restaurant with the AI result, as a CSV the owner can open in Excel."""
    _owner(ctx)
    outlets = {o.id: o.name for o in db.scalars(select(Outlet).where(Outlet.organization_id == ctx.org.id))}
    rows = db.execute(
        select(Review, ReviewAnalysis)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .where(Review.organization_id == ctx.org.id)
        .order_by(Review.review_date.desc())
    ).all()
    buf = io.StringIO()
    buf.write("﻿")  # so Excel opens Tamil text correctly
    w = csv.writer(buf)
    w.writerow(
        [
            "date",
            "platform",
            "outlet",
            "stars",
            "review",
            "guest_name",
            "guest_contact",
            "feeling",
            "topic",
            "urgency",
            "summary",
            "reply_draft",
            "status",
            "reply_sent",
        ]
    )
    for r, a in rows:
        w.writerow(
            [
                r.review_date,
                r.platform,
                outlets.get(r.outlet_id or 0, ""),
                r.rating,
                r.review_text,
                r.guest_name or "",
                r.guest_contact or "",
                a.sentiment if a else "",
                a.category if a else "",
                a.urgency if a else "",
                a.summary if a else "",
                a.suggested_reply if a else "",
                r.workflow_status,
                r.final_reply or "",
            ]
        )
    name = f"virundhu-{ctx.org.slug}-{datetime.now(UTC).date()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


# ---------------- Delete ----------------
class DeleteIn(BaseModel):
    confirm_name: str = Field(min_length=1, max_length=120)
    password: str = Field(default="", max_length=128)


def _money_check(db: Session, org) -> dict:
    """What the owner should know before deleting: anything owed, and paid days that will be given up."""
    from zoneinfo import ZoneInfo

    from app.config import settings
    from app.models import Payment, Subscription

    now = datetime.now(UTC)
    tz = ZoneInfo(settings.TIMEZONE)
    sub = db.scalar(select(Subscription).where(Subscription.organization_id == org.id))
    paid_until = sub.current_period_end if sub and org.plan != "trial" and sub.current_period_end else None
    days_left = max(0, (paid_until - now).days) if paid_until and paid_until > now else 0
    last = db.scalar(
        select(Payment)
        .where(Payment.organization_id == org.id, Payment.status == "paid")
        .order_by(Payment.created_at.desc())
    )
    return {
        # Virundhu is paid in advance and never renews by itself, so nothing can be owed. Kept as a field so that
        # deletion is refused if a balance ever exists (for example, if invoicing after use is added later).
        "balance_due": 0,
        "plan": org.plan,
        "paid_until": paid_until.astimezone(tz).date().isoformat() if paid_until else None,
        "paid_days_left": days_left,
        "last_payment": {
            "amount": last.amount_paise / 100,
            "invoice_no": last.invoice_no,
            "date": last.created_at.astimezone(tz).date().isoformat(),
        }
        if last
        else None,
    }


@router.get("/account/delete-check")
def delete_check(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> dict:
    """Shown before the delete button: balance due (always zero today) and unused paid days."""
    _owner(ctx)
    return _money_check(db, ctx.org)


@router.post("/account/delete")
@limiter.limit("3/minute")
def delete_account(
    request: Request, body: DeleteIn, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)
) -> dict:
    """Delete the restaurant, all its reviews and settings, and the owner's login. Can't be undone."""
    _owner(ctx)
    if body.confirm_name.strip().lower() != ctx.org.name.strip().lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type your restaurant's name exactly to confirm.")
    if ctx.user.hashed_password and not verify_password(body.password, ctx.user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your password isn't right.")
    org_id, user_id = ctx.org.id, ctx.user.id
    money = _money_check(db, ctx.org)
    if money["balance_due"] > 0:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Please pay the balance of Rs {money['balance_due']:,.0f} on Plan and billing first, then delete.",
        )
    reviews = db.scalar(select(func.count(Review.id)).where(Review.organization_id == org_id)) or 0
    owner_email, owner_name, org_name = ctx.user.email, ctx.user.full_name, ctx.org.name
    activity.record(
        db,
        "account_deleted",
        org_id=org_id,
        restaurant=ctx.org.name,
        email=ctx.user.email,
        detail=f"Deleted with {reviews} reviews; plan was {ctx.org.plan}"
        + (f"; paid until {money['paid_until']} ({money['paid_days_left']} days unused)" if money["paid_until"] else "")
        + "; balance due Rs 0",
        commit=False,
    )
    member_ids = list(db.scalars(select(Membership.user_id).where(Membership.organization_id == org_id)))
    db.execute(delete(Organization).where(Organization.id == org_id))  # cascades to every restaurant table
    for uid in member_ids:
        still_member = db.scalar(select(Membership.id).where(Membership.user_id == uid))
        if not still_member:
            db.execute(delete(User).where(User.id == uid, User.is_superadmin.is_(False)))
    db.commit()
    logger.info("Restaurant %s and its users were deleted at the owner's request (user %s)", org_id, user_id)
    first = (owner_name or "").split(" ")[0] or "there"
    send_email(
        [owner_email],
        f"Your Virundhu account for {org_name} has been deleted",
        f"Hi {first},\n\nAs you asked, your Virundhu account for {org_name} was deleted on "
        f"{datetime.now(UTC):%d %b %Y}: the restaurant, its {reviews} reviews, replies, settings and your login.\n\n"
        "There is no balance to pay. Virundhu is paid in advance, so nothing more will ever be charged.\n"
        + (
            f"Your paid plan ran until {money['paid_until']}. Refunds follow our Refund Policy.\n"
            if money["paid_until"]
            else ""
        )
        + "\nPayment records are kept only as long as tax law requires. "
        "If you didn't ask for this, reply to this email straight away.\n\nThank you for trying Virundhu.\n- Virundhu",
    )
    return {"ok": True}


# ---------------- Two-step sign-in (authenticator app) ----------------
class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=20)


class OffIn(BaseModel):
    password: str = Field(default="", max_length=128)
    code: str = Field(min_length=6, max_length=20)


@router.get("/account/two-step")
def two_step_status(user: User = Depends(get_current_user)) -> dict:
    return {
        "enabled": two_step.enabled(user),
        "enabled_at": user.totp_enabled_at,
        "recovery_left": len(user.totp_recovery or []),
        "required": two_step.required_for(user),
    }


@router.post("/account/two-step/start")
@limiter.limit("10/hour")
def two_step_start(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """A QR code to scan with Google Authenticator, Microsoft Authenticator or Authy."""
    if two_step.enabled(user):
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-step sign-in is already on.")
    out = two_step.start(user)
    db.commit()
    return out


@router.post("/account/two-step/confirm")
@limiter.limit("10/minute")
def two_step_confirm(
    request: Request,
    response: Response,
    body: CodeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Switch it on with the first code. The recovery codes are shown once: keep them somewhere safe."""
    codes = two_step.confirm(user, body.code)
    _sign_out_everywhere(db, user.id)  # other devices signed in without the code are signed out
    activity.record(
        db, "two_step_on", email=user.email, detail="Authenticator app added", **_org_of(db, user), commit=False
    )
    db.commit()
    fresh = issue_tokens(db, user)
    set_refresh_cookie(response, fresh.refresh_token or "")
    return {"recovery_codes": codes, "access_token": fresh.access_token}


@router.post("/account/two-step/off")
@limiter.limit("5/minute")
def two_step_off(
    request: Request, body: OffIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Needs the password (if the account has one) and a current code."""
    if user.hashed_password and not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your password isn't right.")
    if not two_step.check(user, body.code):
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code didn't match.")
    two_step.disable(user)
    activity.record(
        db, "two_step_off", email=user.email, detail="Switched off in Settings", **_org_of(db, user), commit=False
    )
    db.commit()
    return {"ok": True}
