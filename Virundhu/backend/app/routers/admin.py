"""Super admin: every restaurant, every user, review volumes, AI cost."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_superadmin
from app.config import settings
from app.database import get_db
from app.models import (
    ActivityLog,
    Lead,
    Membership,
    Organization,
    Outlet,
    Payment,
    Review,
    ReviewAnalysis,
    UsageCounter,
    User,
)
from app.services import activity  # noqa: E402
from app.services.dates import today_local
from app.services.pricing import tier_for  # noqa: E402

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_superadmin)])


class DayCount(BaseModel):
    day: date
    google: int
    zomato: int
    swiggy: int
    other: int


class Stats(BaseModel):
    restaurants: int
    paying: int
    trialing: int
    users: int
    reviews_today: int
    reviews_7d: int
    reviews_30d: int
    urgent_open: int
    ai_cost_month_inr: float
    mrr_inr: int
    collected_month_inr: float = 0
    by_platform_30d: dict[str, int]
    daily: list[DayCount]


@router.get("/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)) -> Stats:
    """Platform-wide numbers for the admin home."""
    today = today_local()
    orgs = db.scalars(select(Organization)).all()
    real = [o for o in orgs if not o.is_demo]
    count = lambda since: db.scalar(select(func.count(Review.id)).where(Review.review_date >= since)) or 0  # noqa: E731
    urgent = (
        db.scalar(
            select(func.count(Review.id))
            .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
            .where(ReviewAnalysis.urgency == "high", Review.workflow_status.in_(("new", "in_progress")))
        )
        or 0
    )
    cost = db.scalar(
        select(func.coalesce(func.sum(UsageCounter.cost_inr), 0)).where(
            UsageCounter.period == datetime.now(UTC).strftime("%Y-%m")
        )
    ) or Decimal(0)
    plat = dict(
        db.execute(
            select(Review.platform, func.count(Review.id))
            .where(Review.review_date >= today - timedelta(days=29))
            .group_by(Review.platform)
        ).all()
    )
    rows = db.execute(
        select(Review.review_date, Review.platform, func.count(Review.id))
        .where(Review.review_date >= today - timedelta(days=13))
        .group_by(Review.review_date, Review.platform)
    ).all()
    platforms = ("google", "zomato", "swiggy", "direct", "other")
    days: dict[date, dict[str, int]] = {
        today - timedelta(days=i): dict.fromkeys(platforms, 0) for i in range(13, -1, -1)
    }
    for d, p, n in rows:
        if d in days:
            days[d][p] = days[d].get(p, 0) + n
    return Stats(
        restaurants=len(real),
        paying=sum(o.plan in ("starter", "growth", "chain") for o in real),
        trialing=sum(o.plan == "trial" for o in real),
        users=db.scalar(select(func.count(User.id))) or 0,
        reviews_today=count(today),
        reviews_7d=count(today - timedelta(days=6)),
        reviews_30d=count(today - timedelta(days=29)),
        urgent_open=urgent,
        ai_cost_month_inr=float(cost),
        mrr_inr=sum(
            tier_for(o.paid_outlets)[0] * o.paid_outlets
            for o in real
            if not o.is_suspended and o.plan != "trial" and o.paid_outlets
        ),
        collected_month_inr=float(
            db.scalar(
                select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                    Payment.created_at >= datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                    Payment.is_test.is_(False),
                )
            )
            or 0
        )
        / 100,
        by_platform_30d={k: plat.get(k, 0) for k in ("google", "zomato", "swiggy", "direct", "other")},
        daily=[DayCount(day=d, **v) for d, v in days.items()],
    )


class OrgRow(BaseModel):
    id: int
    name: str
    city: str | None
    plan: str
    is_demo: bool
    is_suspended: bool
    trial_ends_at: datetime | None
    created_at: datetime
    users: int
    outlets: int
    reviews_30d: int
    urgent_open: int
    ai_cost_month_inr: float
    last_review: date | None
    owner_email: str | None


@router.get("/organizations", response_model=list[OrgRow])
def organizations(db: Session = Depends(get_db)) -> list[OrgRow]:
    """Every restaurant with its usage."""
    today = today_local()
    period = datetime.now(UTC).strftime("%Y-%m")
    out = []
    for o in db.scalars(select(Organization).order_by(Organization.created_at.desc())):
        r = db.execute(
            select(
                func.count(case((Review.review_date >= today - timedelta(days=29), 1))),
                func.count(
                    case(((ReviewAnalysis.urgency == "high") & Review.workflow_status.in_(("new", "in_progress")), 1))
                ),
                func.max(Review.review_date),
            )
            .select_from(Review)
            .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
            .where(Review.organization_id == o.id)
        ).one()
        owner = db.scalar(
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.organization_id == o.id, Membership.role == "owner")
            .order_by(Membership.id)
        )
        cost = (
            db.scalar(
                select(UsageCounter.cost_inr).where(UsageCounter.organization_id == o.id, UsageCounter.period == period)
            )
            or 0
        )
        out.append(
            OrgRow(
                id=o.id,
                name=o.name,
                city=o.city,
                plan=o.plan,
                is_demo=o.is_demo,
                is_suspended=o.is_suspended,
                trial_ends_at=o.trial_ends_at,
                created_at=o.created_at,
                users=db.scalar(select(func.count(Membership.id)).where(Membership.organization_id == o.id)) or 0,
                outlets=db.scalar(select(func.count(Outlet.id)).where(Outlet.organization_id == o.id)) or 0,
                reviews_30d=r[0],
                urgent_open=r[1],
                last_review=r[2],
                ai_cost_month_inr=float(cost),
                owner_email=owner,
            )
        )
    return out


class OrgUpdate(BaseModel):
    plan: str | None = Field(default=None, pattern="^(trial|starter|growth|chain)$")
    is_suspended: bool | None = None


@router.patch("/organizations/{org_id}", response_model=OrgRow)
def update_org(org_id: int, body: OrgUpdate, db: Session = Depends(get_db)) -> OrgRow:
    """Change plan or suspend a restaurant. Every trial is exactly 14 days: there is no way to lengthen one."""
    o = db.get(Organization, org_id)
    if o is None:
        raise HTTPException(404, "Restaurant not found.")
    if body.plan:
        o.plan = body.plan
    if body.is_suspended is not None:
        o.is_suspended = body.is_suspended
    db.commit()
    return next(r for r in organizations(db) if r.id == org_id)


class UserRow(BaseModel):
    id: int
    full_name: str
    email: str
    is_active: bool
    is_superadmin: bool
    restaurants: list[str]
    last_login_at: datetime | None
    created_at: datetime


@router.get("/users", response_model=list[UserRow])
def users(db: Session = Depends(get_db)) -> list[UserRow]:
    """Every user and the restaurants they belong to."""
    names: dict[int, list[str]] = {}
    for uid, org_name, role in db.execute(
        select(Membership.user_id, Organization.name, Membership.role).join(
            Organization, Organization.id == Membership.organization_id
        )
    ):
        names.setdefault(uid, []).append(f"{org_name} ({role})")
    return [
        UserRow(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            is_active=u.is_active,
            is_superadmin=u.is_superadmin,
            restaurants=names.get(u.id, []),
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in db.scalars(select(User).order_by(User.created_at.desc()))
    ]


class UserUpdate(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}", status_code=204)
def update_user(
    user_id: int, body: UserUpdate, admin: User = Depends(require_superadmin), db: Session = Depends(get_db)
) -> None:
    """Switch a user on or off."""
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "User not found.")
    if u.id == admin.id:
        raise HTTPException(400, "You can't switch off your own account.")
    u.is_active = body.is_active
    db.commit()


class AdminEvent(BaseModel):
    id: str
    kind: str  # signup | trial_ending | trial_ended | urgent_waiting
    title: str
    body: str
    at: datetime
    organization_id: int | None = None


@router.get("/events", response_model=list[AdminEvent])
def events(db: Session = Depends(get_db)) -> list[AdminEvent]:
    """What the platform admin should know about: new customers, trials ending, urgent reviews left unanswered."""
    now = datetime.now(UTC)
    out: list[AdminEvent] = []
    for o in db.scalars(select(Organization).where(Organization.is_demo.is_(False))):
        if o.created_at >= now - timedelta(days=7):
            out.append(
                AdminEvent(
                    id=f"signup-{o.id}",
                    kind="signup",
                    title=f"New customer: {o.name}",
                    body=f"Started a free trial{f' in {o.city}' if o.city else ''}.",
                    at=o.created_at,
                    organization_id=o.id,
                )
            )
        if o.plan == "trial" and o.trial_ends_at:
            if now <= o.trial_ends_at <= now + timedelta(days=3):
                out.append(
                    AdminEvent(
                        id=f"trial-{o.id}",
                        kind="trial_ending",
                        title=f"Trial ending: {o.name}",
                        body=f"Ends {o.trial_ends_at:%d %b}. A good moment to call them.",
                        at=o.trial_ends_at - timedelta(days=3),
                        organization_id=o.id,
                    )
                )
            elif now - timedelta(days=14) <= o.trial_ends_at < now:
                out.append(
                    AdminEvent(
                        id=f"ended-{o.id}",
                        kind="trial_ended",
                        title=f"Trial ended: {o.name}",
                        body="They can't reply to reviews until they choose a plan.",
                        at=o.trial_ends_at,
                        organization_id=o.id,
                    )
                )
        stale = (
            db.scalar(
                select(func.count(Review.id))
                .join(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
                .where(
                    Review.organization_id == o.id,
                    Review.is_sample.is_(False),
                    ReviewAnalysis.urgency == "high",
                    Review.workflow_status.in_(("new", "in_progress")),
                    Review.created_at < now - timedelta(hours=24),
                )
            )
            or 0
        )
        if stale:
            out.append(
                AdminEvent(
                    id=f"urgent-{o.id}-{stale}",
                    kind="urgent_waiting",
                    title=f"{o.name}: {stale} urgent review{'s' if stale > 1 else ''} unanswered",
                    body="Waiting more than 24 hours. The customer may need help.",
                    at=now,
                    organization_id=o.id,
                )
            )
    since = now - timedelta(days=14)
    for a in db.scalars(
        select(ActivityLog).where(
            ActivityLog.created_at >= since,
            ActivityLog.kind.not_in(activity.QUIET),
        )
    ):
        out.append(
            AdminEvent(
                id=f"act-{a.id}",
                kind=a.kind,
                title=f"{activity.LABELS.get(a.kind, a.kind)}{f': {a.restaurant}' if a.restaurant else ''}",
                body=" · ".join(x for x in (a.user_email, a.detail) if x) or "",
                at=a.created_at,
                organization_id=a.organization_id,
            )
        )
    return sorted(out, key=lambda e: e.at, reverse=True)[:40]


class ActivityOut(BaseModel):
    id: int
    kind: str
    label: str
    restaurant: str | None
    user_email: str | None
    detail: str | None
    created_at: datetime


@router.get("/activity", response_model=list[ActivityOut])
def activity_log(kind: str | None = None, db: Session = Depends(get_db)) -> list[ActivityOut]:
    """Everything recorded for the admin, newest first (kept even after a restaurant is deleted)."""
    q = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(300)
    if kind:
        q = q.where(ActivityLog.kind == kind)
    return [
        ActivityOut(
            id=a.id,
            kind=a.kind,
            label=activity.LABELS.get(a.kind, a.kind),
            restaurant=a.restaurant,
            user_email=a.user_email,
            detail=a.detail,
            created_at=a.created_at,
        )
        for a in db.scalars(q)
    ]


class OrgLogItem(BaseModel):
    at: datetime
    kind: str
    label: str
    who: str | None = None
    detail: str | None = None


@router.get("/organizations/{org_id}/log", response_model=list[OrgLogItem])
def org_log(org_id: int, db: Session = Depends(get_db)) -> list[OrgLogItem]:
    """One restaurant's own history: sign-ins, emails sent to it, uploads, payments, password changes, support."""
    from app.models import ImportBatch, SupportTicket

    items = [
        OrgLogItem(
            at=a.created_at,
            kind=a.kind,
            label=activity.LABELS.get(a.kind, a.kind),
            who=a.user_email,
            detail=a.detail,
        )
        for a in db.scalars(
            select(ActivityLog)
            .where(ActivityLog.organization_id == org_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(500)
        )
    ]
    for b in db.scalars(
        select(ImportBatch).where(ImportBatch.organization_id == org_id).order_by(ImportBatch.id.desc()).limit(200)
    ):
        items.append(
            OrgLogItem(
                at=b.created_at,
                kind="upload",
                label="Reviews added",
                detail=f"{b.filename}: {b.valid_rows} new, {b.duplicate_rows} already there, {b.invalid_rows} skipped",
            )
        )
    for t in db.scalars(
        select(SupportTicket)
        .where(SupportTicket.organization_id == org_id)
        .order_by(SupportTicket.id.desc())
        .limit(100)
    ):
        items.append(
            OrgLogItem(
                at=t.created_at, kind="support_ticket", label="Support request", who=t.user_email, detail=t.subject
            )
        )
    return sorted(items, key=lambda i: i.at, reverse=True)[:600]


class LeadOut(BaseModel):
    id: int
    name: str
    restaurant: str
    phone: str | None
    email: str | None
    city: str | None
    outlets: int | None
    message: str | None
    status: str
    created_at: datetime


@router.get("/leads", response_model=list[LeadOut])
def leads(db: Session = Depends(get_db)) -> list[LeadOut]:
    """Demo requests from the Contact page, newest first."""
    rows = db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(200)).all()
    return [LeadOut.model_validate(r, from_attributes=True) for r in rows]


class LeadPatch(BaseModel):
    status: str = Field(pattern="^(new|contacted|won|lost)$")


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadPatch, db: Session = Depends(get_db)) -> LeadOut:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    lead.status = body.status
    db.commit()
    return LeadOut.model_validate(lead, from_attributes=True)


class MailboxBox(BaseModel):
    key: str
    label: str
    address: str
    purpose: str
    total: int
    new: int
    week: int
    gmail_url: str


class MailboxItem(BaseModel):
    at: datetime
    box: str
    who: str | None
    title: str
    detail: str | None
    status: str


class MailboxOut(BaseModel):
    account: str
    sender: str
    boxes: list[MailboxBox]
    recent: list[MailboxItem]


def _gmail(account: str, address: str) -> str:
    from urllib.parse import quote

    return f"https://mail.google.com/mail/?authuser={quote(account)}#search/{quote('to:' + address)}"


@router.get("/mailbox", response_model=MailboxOut)
def mailbox(db: Session = Depends(get_db)) -> MailboxOut:
    """The company inboxes (info, demo, sender) with counts from what Virundhu itself recorded, plus Gmail links."""
    from email.utils import parseaddr

    from app.models import ActivityLog, SupportTicket

    week = datetime.now(UTC) - timedelta(days=7)
    account = settings.MAILBOX_ACCOUNT or settings.notify_email
    sender = parseaddr(settings.EMAIL_FROM)[1] or settings.notify_email
    n = lambda q: db.scalar(q) or 0  # noqa: E731
    leads_q = select(func.count()).select_from(Lead)
    tickets_q = select(func.count()).select_from(SupportTicket)
    sent_q = select(func.count()).select_from(ActivityLog).where(ActivityLog.kind == "email_sent")
    failed = n(select(func.count()).select_from(ActivityLog).where(ActivityLog.kind == "email_failed"))
    boxes = [
        MailboxBox(
            key="demo",
            label="Demo requests",
            address=settings.demo_requests_email,
            purpose="Contact page demo requests land here",
            total=n(leads_q),
            new=n(leads_q.where(Lead.status == "new")),
            week=n(leads_q.where(Lead.created_at >= week)),
            gmail_url=_gmail(account, settings.demo_requests_email),
        ),
        MailboxBox(
            key="info",
            label="Info and support",
            address=settings.notify_email,
            purpose="Questions, Quick help hand-overs, support tickets, sign-up and payment alerts",
            total=n(tickets_q),
            new=n(tickets_q.where(SupportTicket.status != "resolved")),
            week=n(tickets_q.where(SupportTicket.created_at >= week)),
            gmail_url=_gmail(account, settings.notify_email),
        ),
        MailboxBox(
            key="sent",
            label="Sent to customers",
            address=sender,
            purpose="Welcome, password, reminder, suspension and receipt emails go out from here",
            total=n(sent_q),
            new=failed,
            week=n(sent_q.where(ActivityLog.created_at >= week)),
            gmail_url=f"https://mail.google.com/mail/?authuser={account}#sent",
        ),
    ]
    recent = [
        MailboxItem(
            at=x.created_at,
            box="demo",
            who=x.email or x.phone,
            title=f"{x.name}, {x.restaurant}",
            detail=", ".join(str(v) for v in (x.city, f"{x.outlets} outlets" if x.outlets else None, x.message) if v),
            status=x.status,
        )
        for x in db.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(15))
    ] + [
        MailboxItem(
            at=t.created_at,
            box="info",
            who=t.user_email,
            title=f"VT-{t.id:05d} {t.subject}",
            detail=t.restaurant,
            status=t.status,
        )
        for t in db.scalars(select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(15))
    ]
    recent.sort(key=lambda r: r.at, reverse=True)
    return MailboxOut(account=account, sender=sender, boxes=boxes, recent=recent[:20])


@router.get("/agents")
def agent_feed(db: Session = Depends(get_db)) -> dict:
    """The AI agent team: who did what, upcoming demos, and anything that needed you."""
    from app.services import agent_team

    return agent_team.feed(db)


@router.get("/autopilot")
def autopilot(db: Session = Depends(get_db)) -> dict:
    """The admin's daily chores, what runs by itself and what still needs a person today."""
    from app.models import ActivityLog, Payment

    now = datetime.now(UTC)
    day = now - timedelta(days=1)
    n = lambda q: db.scalar(q) or 0  # noqa: E731
    orgs = [o for o in db.scalars(select(Organization).where(Organization.is_demo.is_(False)))]
    ending = [
        o for o in orgs if o.plan == "trial" and o.trial_ends_at and now <= o.trial_ends_at <= now + timedelta(days=3)
    ]
    from app.models import AgentRun

    def runs(agent: str, outcome: str = "done") -> int:
        return n(select(func.count()).select_from(AgentRun).where(
            AgentRun.agent == agent, AgentRun.outcome == outcome, AgentRun.created_at >= day))

    no_email = n(select(func.count()).select_from(Lead).where(Lead.status == "no_email", Lead.created_at >= day))
    failed = n(
        select(func.count())
        .select_from(ActivityLog)
        .where(ActivityLog.kind == "email_failed", ActivityLog.created_at >= day)
    )
    paid_today = (
        n(
            select(func.coalesce(func.sum(Payment.amount_paise), 0)).where(
                Payment.status.in_(("captured", "succeeded", "paid")), Payment.created_at >= day
            )
        )
        // 100
    )
    chores = [
        {
            "key": "leads",
            "name": "Nila",
            "title": "The Demo Booker",
            "chore": "Booking demos",
            "before": "Open the mailbox, reply to each request, agree a time, send an invite, remember to remind.",
            "now": "Within a minute Nila emails open times; the restaurant taps one and it's booked with a calendar "
            "invite for both sides and a Meet, Zoom, Teams, phone or in-person plan. You get the details on "
            "WhatsApp and email, and both sides get reminders.",
            "needs_you": no_email,
            "needs_label": "left no email",
            "done": runs("nila"),
            "done_label": "actions today",
            "link": "/app/admin/leads",
        },
        {
            "key": "trials",
            "name": "Ravi",
            "title": "The Trial Saver",
            "chore": "Chasing trials before they end",
            "before": "Check each restaurant's end date, send reminders by hand, switch features off when unpaid.",
            "now": "Reminders go out at 5, 4, 3, 2 and 1 days; unpaid accounts lock by themselves and unlock the "
            "moment they pay. You get an alert for every suspension and reactivation.",
            "needs_you": 0,
            "needs_label": "",
            "done": len(ending),
            "done_label": "trials ending in 3 days, being reminded",
            "link": "/app/admin/restaurants",
        },
        {
            "key": "support",
            "name": "Tara",
            "title": "The Help Desk Hero",
            "chore": "Answering and fixing support tickets",
            "before": "Read every message, look up the account, check the payment, type an answer.",
            "now": "Tara replies to every ticket within minutes, day and night. For payment problems she checks Dodo "
            "herself and switches the plan on if the money arrived. Only refunds and legal matters come to you.",
            "needs_you": runs("tara", "escalated"),
            "needs_label": "sent to you",
            "done": runs("tara"),
            "done_label": "answered today",
            "link": "/app/admin/support",
        },
        {
            "key": "health",
            "name": "Dev",
            "title": "The Night Watch",
            "chore": "Checking the system is healthy",
            "before": "Log in to the server, read logs, check emails went out and backups ran.",
            "now": "Every failed email is logged; backups run at 3 am daily; a 9 pm digest sums up the day.",
            "needs_you": failed,
            "needs_label": "emails failed in 24 h",
            "done": 1,
            "done_label": "backup a day",
            "link": "/app/admin/emails",
        },
        {
            "key": "money",
            "name": "Lakshmi",
            "title": "The Money Keeper",
            "chore": "Tracking payments and invoices",
            "before": "Match payments to restaurants, make invoices, update a spreadsheet.",
            "now": "Payments switch plans on by themselves, receipts and GST-ready invoices are emailed, and a "
            "monthly audit Excel arrives in your inbox.",
            "needs_you": 0,
            "needs_label": "",
            "done": paid_today,
            "done_label": "collected today",
            "link": "/app/admin",
        },
    ]
    return {"as_of": now.isoformat(), "chores": chores, "restaurants": len(orgs)}


class LaunchItem(BaseModel):
    key: str
    label: str
    ok: bool
    fix: str
    required: bool


@router.get("/launch-check", response_model=list[LaunchItem])
def launch_check(db: Session = Depends(get_db)) -> list[LaunchItem]:
    """What still needs setting before real restaurants use Virundhu. Reads .env only; changes nothing."""
    from app.auth.security import verify_password

    admin = db.scalar(select(User).where(User.email == settings.SUPERADMIN_EMAIL))
    placeholder = "choose-your-own-long-password"
    default_pw = bool(admin and admin.hashed_password and verify_password(placeholder, admin.hashed_password))
    local = any(x in settings.APP_URL for x in ("localhost", "127.0.0.1"))
    return [
        LaunchItem(
            key="app_url",
            label="Real website address (APP_URL)",
            ok=not local,
            required=True,
            fix="Set APP_URL in .env to your domain (https://...). QR codes and email links use it; "
            "don't print QR codes before this.",
        ),
        LaunchItem(
            key="smtp",
            label="Email sending (SMTP)",
            ok=bool(settings.SMTP_HOST and (settings.SMTP_USER or "relay" in settings.SMTP_HOST)),
            required=True,
            fix="Add SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD and EMAIL_FROM in .env. Without it no alerts or "
            "password-reset emails go out. Then press 'Send test email'.",
        ),
        LaunchItem(
            key="ai",
            label="AI key",
            ok=settings.llm_configured,
            required=True,
            fix="Add the key for LLM_PROVIDER in .env (OPENAI_API_KEY for openai).",
        ),
        LaunchItem(
            key="admin_pw",
            label="Admin password changed",
            ok=not default_pw,
            required=True,
            fix="Admin console → Change my password. The starting password is in the docs.",
        ),
        LaunchItem(
            key="phone",
            label="Your phone number on the website",
            ok=bool(settings.CONTACT_PHONE),
            required=True,
            fix="Set CONTACT_PHONE in .env, e.g. +91 98765 43210. It shows on Contact, the footer and the "
            "WhatsApp button.",
        ),
        LaunchItem(
            key="payments",
            label="Payments",
            ok=settings.payments_enabled,
            required=True,
            fix="Set the Dodo key and DODO_PRODUCT_FLEX (switch Dodo to live mode before launch).",
        ),
        LaunchItem(
            key="google",
            label="Google sign-in and Google reviews",
            ok=settings.google_enabled,
            required=False,
            fix="Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, and apply for Business Profile API access (see "
            "docs/MARKET_AND_QA_REPORT.md, Part 2).",
        ),
        LaunchItem(
            key="whatsapp",
            label="WhatsApp messages",
            ok=settings.whatsapp_enabled,
            required=False,
            fix="Add WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID and get the three templates approved (GETTING_STARTED "
            "Part 7). Until then review requests use one-tap links.",
        ),
    ]


@router.post("/test-email")
def test_email(user: User = Depends(require_superadmin)) -> dict[str, bool]:
    """Send a test email to the admin, to check the SMTP settings."""
    from app.services.emailer import send_email

    ok = send_email(
        [settings.notify_email],
        "Virundhu test email",
        "If you can read this, Virundhu can send emails. - Virundhu",
    )
    return {"sent": ok and bool(settings.SMTP_HOST)}
