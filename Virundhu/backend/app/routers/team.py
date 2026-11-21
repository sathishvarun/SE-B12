"""Team members, invitations, outlets and restaurant settings."""

import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.cookies import to_cookie
from app.auth.deps import OrgContext, get_org_context, require_owner
from app.auth.passwords import weak_reason
from app.auth.security import hash_password, hash_token, new_opaque_token
from app.config import settings
from app.database import get_db
from app.models import AlertRule, Invitation, Membership, Organization, Outlet, SourceConnection, User
from app.schemas.auth import TokenOut
from app.services import auth_service, maps
from app.services.emailer import send_email
from app.services.plans import limits_for

router = APIRouter(prefix="/api/v1", tags=["team"])


class MemberOut(BaseModel):
    membership_id: int
    user_id: int
    full_name: str
    email: str
    role: str
    is_you: bool
    outlet_ids: list[int] | None  # None = all outlets


class InviteOut(BaseModel):
    id: int
    email: str
    role: str
    expires_at: datetime
    outlet_ids: list[int] | None = None
    invite_url: str | None = None


class TeamOut(BaseModel):
    members: list[MemberOut]
    invitations: list[InviteOut]
    seats: int


@router.get("/team", response_model=TeamOut)
def team(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> TeamOut:
    """Everyone in this restaurant and pending invitations."""
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == ctx.org.id)
        .order_by(Membership.id)
    ).all()
    invites = db.scalars(
        select(Invitation).where(
            Invitation.organization_id == ctx.org.id,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(UTC),
        )
    )
    return TeamOut(
        members=[
            MemberOut(
                membership_id=m.id,
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                role=m.role,
                is_you=u.id == ctx.user.id,
                outlet_ids=None if m.role == "owner" else (m.outlet_ids or None),
            )
            for m, u in rows
        ],
        invitations=[
            InviteOut(id=i.id, email=i.email, role=i.role, expires_at=i.expires_at, outlet_ids=i.outlet_ids)
            for i in invites
        ],
        seats=limits_for(ctx.org)["seats"],
    )


class InviteIn(BaseModel):
    email: EmailStr
    role: str = Field(pattern="^(manager|agent)$")
    outlet_ids: list[int] | None = None  # None or empty = all outlets


def _valid_outlets(db: Session, org_id: int, ids: list[int] | None) -> list[int] | None:
    """Keep only outlets of this restaurant. None/empty means every outlet."""
    if not ids:
        return None
    own = set(db.scalars(select(Outlet.id).where(Outlet.organization_id == org_id, Outlet.id.in_(ids))))
    if not own:
        raise HTTPException(400, "Pick at least one of your outlets.")
    return sorted(own)


@router.post("/team/invitations", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def invite(body: InviteIn, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> InviteOut:
    """Invite a teammate. Returns a link you can also share on WhatsApp."""
    used = db.scalar(select(func.count(Membership.id)).where(Membership.organization_id == ctx.org.id)) or 0
    if used >= limits_for(ctx.org)["seats"]:
        raise HTTPException(409, "Your plan's team seats are full. Upgrade to add more people.")
    email = body.email.lower()
    if db.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == ctx.org.id, User.email == email)
    ):
        raise HTTPException(409, "This person is already in your team.")
    token, digest = new_opaque_token()
    inv = Invitation(
        organization_id=ctx.org.id,
        email=email,
        role=body.role,
        token_hash=digest,
        invited_by=ctx.user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        outlet_ids=_valid_outlets(db, ctx.org.id, body.outlet_ids),
    )
    db.add(inv)
    db.commit()
    url = f"{settings.APP_URL}/invite/{token}"
    send_email(
        [email],
        f"{ctx.user.full_name} invited you to {ctx.org.name} on Virundhu",
        f"You've been invited to help reply to guest reviews for {ctx.org.name}.\n\nJoin here (valid 7 days): {url}\n",
    )
    return InviteOut(
        id=inv.id, email=email, role=inv.role, expires_at=inv.expires_at, outlet_ids=inv.outlet_ids, invite_url=url
    )


@router.delete("/team/invitations/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invite(invite_id: int, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> None:
    inv = db.scalar(select(Invitation).where(Invitation.id == invite_id, Invitation.organization_id == ctx.org.id))
    if inv:
        db.delete(inv)
        db.commit()


class InviteInfo(BaseModel):
    email: str
    role: str
    organization_name: str
    has_account: bool


def _valid_invite(db: Session, token: str) -> Invitation:
    inv = db.scalar(select(Invitation).where(Invitation.token_hash == hash_token(token)))
    if inv is None or inv.accepted_at or inv.expires_at < datetime.now(UTC):
        raise HTTPException(404, "This invitation has expired or was already used. Ask for a new one.")
    return inv


@router.get("/invitations/{token}", response_model=InviteInfo)
def invite_info(token: str, db: Session = Depends(get_db)) -> InviteInfo:
    """Shown on the join page."""
    inv = _valid_invite(db, token)
    org = db.get(Organization, inv.organization_id)
    has = db.scalar(select(User.id).where(User.email == inv.email)) is not None
    return InviteInfo(email=inv.email, role=inv.role, organization_name=org.name if org else "", has_account=has)


class AcceptIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


@router.post("/invitations/{token}/accept", response_model=TokenOut, response_model_exclude_none=True)
def accept(token: str, body: AcceptIn, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    """Join the team: creates the account (or checks the password of an existing one) and signs in."""
    inv = _valid_invite(db, token)
    user = db.scalar(select(User).where(User.email == inv.email))
    if user is None:
        problem = weak_reason(body.password, inv.email, body.full_name)
        if problem:
            raise HTTPException(422, problem)
        user = User(
            email=inv.email,
            full_name=body.full_name.strip(),
            hashed_password=hash_password(body.password),
            is_verified=True,
        )
        db.add(user)
        db.flush()
    else:
        from app.auth.security import verify_password

        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(401, "This email already has an account. Enter that account's password.")
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user.id, Membership.organization_id == inv.organization_id)
    ):
        db.add(
            Membership(user_id=user.id, organization_id=inv.organization_id, role=inv.role, outlet_ids=inv.outlet_ids)
        )
    inv.accepted_at = datetime.now(UTC)
    return to_cookie(response, auth_service.issue_tokens(db, user))


class RoleIn(BaseModel):
    role: str | None = Field(default=None, pattern="^(owner|manager|agent)$")
    outlet_ids: list[int] | None = None
    all_outlets: bool = False


@router.patch("/team/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def change_role(
    membership_id: int, body: RoleIn, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)
) -> None:
    m = db.scalar(select(Membership).where(Membership.id == membership_id, Membership.organization_id == ctx.org.id))
    if m is None:
        raise HTTPException(404, "Member not found.")
    if body.role:
        m.role = body.role
    if body.all_outlets:
        m.outlet_ids = None
    elif body.outlet_ids is not None:
        m.outlet_ids = _valid_outlets(db, ctx.org.id, body.outlet_ids)
    db.commit()


@router.delete("/team/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(membership_id: int, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> None:
    m = db.scalar(select(Membership).where(Membership.id == membership_id, Membership.organization_id == ctx.org.id))
    if m is None:
        raise HTTPException(404, "Member not found.")
    if m.user_id == ctx.user.id:
        raise HTTPException(400, "You can't remove yourself.")
    db.delete(m)
    db.commit()


# ---------------- Outlets and restaurant settings ----------------
OUTLET_FIELDS = (
    "name",
    "area",
    "city",
    "district",
    "address",
    "pincode",
    "phone",
    "manager_name",
    "manager_phone",
    "manager_email",
    "google_maps_url",
    "zomato_url",
    "swiggy_url",
)
_URL = r"^(https://.+)?$"


class OutletOut(BaseModel):
    id: int
    name: str
    area: str | None = None
    city: str | None = None
    district: str | None = None
    address: str | None = None
    pincode: str | None = None
    phone: str | None = None
    manager_name: str | None = None
    manager_phone: str | None = None
    manager_email: str | None = None
    google_maps_url: str | None = None
    zomato_url: str | None = None
    swiggy_url: str | None = None
    feedback_url: str | None = None  # the outlet's own QR link (branch already chosen)
    on_google_maps: bool = False
    directions_url: str | None = None
    map_embed_url: str | None = None
    google_rating: float | None = None
    google_rating_count: int | None = None


class OutletIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=300)
    pincode: str | None = Field(default=None, pattern=r"^(\d{6})?$")
    phone: str | None = Field(default=None, max_length=20)
    manager_name: str | None = Field(default=None, max_length=120)
    manager_phone: str | None = Field(default=None, max_length=20)
    manager_email: EmailStr | None = None
    google_maps_url: str | None = Field(default=None, max_length=500, pattern=_URL)
    zomato_url: str | None = Field(default=None, max_length=500, pattern=_URL)
    swiggy_url: str | None = Field(default=None, max_length=500, pattern=_URL)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_none(cls, v):
        return v.strip() or None if isinstance(v, str) else v


def _outlet_out(o: Outlet, org: Organization) -> OutletOut:
    data = {f: getattr(o, f) for f in OUTLET_FIELDS}
    link = f"{settings.APP_URL}/f/{org.feedback_token}?o={o.id}" if org.feedback_token else None
    return OutletOut(
        id=o.id,
        feedback_url=link,
        on_google_maps=maps.on_google_maps(o),
        directions_url=maps.directions_url(o),
        map_embed_url=maps.embed_url(o),
        google_rating=float(o.google_rating) if o.google_rating is not None else None,
        google_rating_count=o.google_rating_count,
        **data,
    )


@router.get("/outlets", response_model=list[OutletOut])
def outlets(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> list[OutletOut]:
    if not ctx.org.feedback_token:  # every outlet's QR link needs the restaurant's feedback token
        ctx.org.feedback_token = secrets.token_urlsafe(9)
        db.commit()
    rows = db.scalars(
        select(Outlet)
        .where(Outlet.organization_id == ctx.org.id, Outlet.is_active)
        .where(Outlet.id.in_(ctx.outlet_ids) if ctx.outlet_ids is not None else True)
        .order_by(Outlet.district, Outlet.city, Outlet.name)
    )
    return [_outlet_out(o, ctx.org) for o in rows]


@router.post("/outlets", response_model=OutletOut, status_code=status.HTTP_201_CREATED)
def add_outlet(body: OutletIn, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> OutletOut:
    count = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == ctx.org.id, Outlet.is_active)) or 0
    if count >= limits_for(ctx.org)["outlets"]:
        raise HTTPException(409, "Your plan's outlet limit is reached. Add outlets on the Plan and billing page.")
    data = body.model_dump()
    data["manager_email"] = str(data["manager_email"]).lower() if data["manager_email"] else None
    o = Outlet(organization_id=ctx.org.id, **data)
    db.add(o)
    db.commit()
    return _outlet_out(o, ctx.org)


@router.put("/outlets/{outlet_id}", response_model=OutletOut)
def update_outlet(
    outlet_id: int, body: OutletIn, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)
) -> OutletOut:
    o = db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.organization_id == ctx.org.id))
    if o is None:
        raise HTTPException(404, "Outlet not found.")
    data = body.model_dump()
    data["manager_email"] = str(data["manager_email"]).lower() if data["manager_email"] else None
    for k, v in data.items():
        setattr(o, k, v)
    db.commit()
    return _outlet_out(o, ctx.org)


class OutletImportOut(BaseModel):
    added: list[str]
    updated: list[str]
    skipped: list[str]  # with the reason


OUTLET_ALIASES = {
    "name": ("name", "outlet", "outlet name", "branch", "branch name"),
    "manager_name": ("manager", "manager name"),
    "manager_phone": ("manager phone", "manager mobile", "manager whatsapp"),
    "manager_email": ("manager email",),
    "phone": ("phone", "outlet phone", "landline"),
    "pincode": ("pincode", "pin", "pin code"),
    "google_maps_url": ("google maps", "google maps link", "maps"),
    "zomato_url": ("zomato", "zomato link", "zomato page"),
    "swiggy_url": ("swiggy", "swiggy link", "swiggy page"),
}


@router.post("/outlets/import", response_model=OutletImportOut)
async def import_outlets(
    file: UploadFile = File(...), ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)
) -> OutletImportOut:
    """Add or update many outlets from one CSV/Excel file (one row per branch, matched by name)."""
    import io

    import pandas as pd

    content = await file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(413, "This file is over 2 MB.")
    try:
        if (file.filename or "").lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8-sig", keep_default_na=False)
    except Exception as exc:
        raise HTTPException(400, "Couldn't read this file. Save it as CSV (UTF-8) or Excel (.xlsx).") from exc
    df = df.fillna("")
    cols = {}
    for c in df.columns:
        key = str(c).strip().lower().replace("_", " ")
        std = next((k for k, opts in OUTLET_ALIASES.items() if key in opts), key.replace(" ", "_"))
        if std in OUTLET_FIELDS:
            cols[c] = std
    df = df.rename(columns=cols)
    if "name" not in df.columns:
        raise HTTPException(400, "The file needs a column called name (the outlet name).")
    if len(df) > 1000:
        raise HTTPException(400, "Please upload at most 1,000 outlets at a time.")

    existing = {
        o.name.lower(): o
        for o in db.scalars(select(Outlet).where(Outlet.organization_id == ctx.org.id, Outlet.is_active))
    }
    room = limits_for(ctx.org)["outlets"] - len(existing)
    added, updated, skipped = [], [], []
    for i, row in enumerate(df.to_dict("records"), start=2):
        raw = {k: str(row.get(k, "")).strip() for k in OUTLET_FIELDS if k in df.columns}
        try:
            data = OutletIn(**raw).model_dump(exclude_unset=False)
        except Exception as exc:
            first = str(exc).splitlines()[1] if len(str(exc).splitlines()) > 1 else str(exc)
            skipped.append(f"Row {i} ({raw.get('name') or 'no name'}): check {first.strip()}")
            continue
        data["manager_email"] = str(data["manager_email"]).lower() if data["manager_email"] else None
        target = existing.get(data["name"].lower())
        if target:
            for k, v in data.items():
                if k in raw and v is not None:  # only overwrite what the file actually gives
                    setattr(target, k, v)
            updated.append(target.name)
        elif room <= 0:
            skipped.append(f"Row {i} ({data['name']}): your plan's outlet limit is reached")
        else:
            o = Outlet(organization_id=ctx.org.id, **data)
            db.add(o)
            existing[o.name.lower()] = o
            added.append(o.name)
            room -= 1
    db.commit()
    return OutletImportOut(added=added, updated=updated, skipped=skipped[:100])


@router.delete("/outlets/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_outlet(outlet_id: int, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> None:
    """Hide a closed outlet. Its old reviews stay in the reports."""
    o = db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.organization_id == ctx.org.id))
    if o is None:
        raise HTTPException(404, "Outlet not found.")
    active = db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == ctx.org.id, Outlet.is_active))
    if active <= 1:
        raise HTTPException(400, "Keep at least one outlet.")
    o.is_active = False
    db.commit()


class SettingsOut(BaseModel):
    name: str
    city: str | None
    reply_tone: str
    reply_signature: str | None
    alert_emails: list[str]
    plan: str
    trial_ends_at: datetime | None
    autopilot_enabled: bool
    autopilot_min_rating: int
    google_connected: bool
    google_review_url: str | None
    feedback_url: str
    whatsapp_numbers: list[str]
    whatsapp_available: bool
    owner_phone: str | None = None
    business_type: str | None = None
    cuisine: str | None = None
    gstin: str | None = None
    head_office: str | None = None
    outlets_declared: int | None = None
    holding_reply_hours: int | None = None
    reply_target_minutes: int | None = 60
    weekly_summary: bool = True
    ask_after_bill: bool = False
    has_billing_key: bool = False


class SettingsIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    reply_tone: str | None = Field(default=None, pattern="^(warm|professional|short)$")
    reply_signature: str | None = Field(default=None, max_length=120)
    alert_emails: list[EmailStr] | None = Field(default=None, max_length=10)
    autopilot_enabled: bool | None = None
    autopilot_min_rating: int | None = Field(default=None, ge=3, le=5)
    owner_phone: str | None = Field(default=None, max_length=20)
    business_type: str | None = Field(default=None, pattern="^(dine_in|cloud_kitchen|both)?$")
    cuisine: str | None = Field(default=None, max_length=120)
    gstin: str | None = Field(default=None, pattern=r"^([0-9]{2}[A-Z0-9]{13})?$")
    head_office: str | None = Field(default=None, max_length=300)
    outlets_declared: int | None = Field(default=None, ge=1, le=5000)
    holding_reply_hours: int | None = Field(default=None, ge=0, le=72)  # 0 switches it off
    reply_target_minutes: int | None = Field(default=None, ge=0, le=240)  # 0 = reminders off; else 30/60/120
    weekly_summary: bool | None = None
    ask_after_bill: bool | None = None
    google_review_url: str | None = Field(default=None, max_length=500, pattern=r"^(https://.+)?$")
    whatsapp_numbers: list[str] | None = Field(default=None, max_length=5)

    @field_validator("whatsapp_numbers")
    @classmethod
    def _numbers(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned = []
        for n in v:
            n = re.sub(r"[\s-]", "", n)
            if not re.fullmatch(r"\+\d{10,15}", n):
                raise ValueError(f"{n or 'A number'} isn't valid. Use the country code, like +919876543210.")
            cleaned.append(n)
        return sorted(set(cleaned))


def _rule(db: Session, org_id: int) -> AlertRule:
    rule = db.scalar(select(AlertRule).where(AlertRule.organization_id == org_id).order_by(AlertRule.id))
    if rule is None:
        rule = AlertRule(organization_id=org_id, recipients=[], min_urgency="high")
        db.add(rule)
        db.flush()
    return rule


@router.get("/settings", response_model=SettingsOut)
def get_settings(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> SettingsOut:
    o = ctx.org
    if not o.feedback_token:
        o.feedback_token = secrets.token_urlsafe(9)
        db.commit()
    google = db.scalar(
        select(SourceConnection).where(SourceConnection.organization_id == o.id, SourceConnection.provider == "google")
    )
    return SettingsOut(
        name=o.name,
        city=o.city,
        reply_tone=o.reply_tone,
        reply_signature=o.reply_signature,
        alert_emails=list(_rule(db, o.id).recipients or []),
        plan=o.plan,
        trial_ends_at=o.trial_ends_at,
        autopilot_enabled=o.autopilot_enabled,
        autopilot_min_rating=o.autopilot_min_rating,
        google_connected=bool(google and google.status == "connected"),
        google_review_url=o.google_review_url,
        feedback_url=f"{settings.APP_URL}/f/{o.feedback_token}",
        whatsapp_numbers=list(o.whatsapp_numbers or []),
        whatsapp_available=settings.whatsapp_enabled,
        owner_phone=o.owner_phone,
        business_type=o.business_type,
        cuisine=o.cuisine,
        gstin=o.gstin,
        head_office=o.head_office,
        outlets_declared=o.outlets_declared,
        holding_reply_hours=o.holding_reply_hours,
        reply_target_minutes=o.reply_target_minutes,
        weekly_summary=o.weekly_summary,
        ask_after_bill=o.ask_after_bill,
        has_billing_key=bool(o.billing_key_hash),
    )


@router.patch("/settings", response_model=SettingsOut)
def update_settings(
    body: SettingsIn, ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)
) -> SettingsOut:
    o = ctx.org
    for field in ("name", "city", "reply_tone", "reply_signature", "autopilot_enabled", "autopilot_min_rating"):
        value = getattr(body, field)
        if value is not None:
            setattr(o, field, value)
    for field in ("owner_phone", "business_type", "cuisine", "gstin", "head_office"):
        value = getattr(body, field)
        if value is not None:
            setattr(o, field, value.strip() or None)
    if body.outlets_declared is not None:
        o.outlets_declared = body.outlets_declared
    if body.ask_after_bill is not None:
        o.ask_after_bill = body.ask_after_bill
    if body.weekly_summary is not None:
        o.weekly_summary = body.weekly_summary
    if body.holding_reply_hours is not None:
        o.holding_reply_hours = body.holding_reply_hours or None
    if body.reply_target_minutes is not None:
        if body.reply_target_minutes and body.reply_target_minutes not in (30, 60, 120):
            raise HTTPException(422, "Choose 30, 60 or 120 minutes, or switch the reminders off.")
        o.reply_target_minutes = body.reply_target_minutes or None
    if body.google_review_url is not None:
        o.google_review_url = body.google_review_url or None
    if body.whatsapp_numbers is not None:
        o.whatsapp_numbers = body.whatsapp_numbers
    if body.alert_emails is not None:
        _rule(db, o.id).recipients = sorted({str(e).lower() for e in body.alert_emails})
    db.commit()
    return get_settings(ctx, db)
