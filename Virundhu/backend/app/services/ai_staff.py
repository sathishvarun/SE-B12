"""Virundhu's AI staff: the agents that do the restaurant's review work, and the numbers that prove it.

Everything here is computed from data Virundhu already holds (reviews, the AI's reading of them, alerts, requests),
so it works the same with or without an LLM key. Money figures are labelled estimates: they use the restaurant's own
average order value (owner rule) and fixed, stated assumptions.
"""

import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext
from app.models import (
    AlertLog,
    GuestRecovery,
    Organization,
    Outlet,
    Review,
    ReviewAnalysis,
    ReviewRequest,
    WeeklyReport,
)
from app.services.dates import today_local

# Stated assumptions behind the "work done" numbers (shown to the owner on the page).
MIN_READ = 1.0  # minutes a person takes to read and tag one review
MIN_REPLY = 3.0  # minutes to write a careful reply
STAFF_RATE = 150  # rupees per hour of a manager's time
GUESTS_PER_BAD_REVIEW = 3  # guests a visible bad review typically turns away (conservative)

DEFAULT_RULES = {
    "banned_words": ["refund", "free", "compensation"],  # the AI never promises these in a public reply
    "escalate": ["hygiene"],  # these categories always wait for a person
    "avg_order_value": 400,  # rupees, used for revenue-at-risk
    "comeback_offer": "10% off your next visit",
}

LABEL = {
    "food_quality": "food quality",
    "delivery": "delivery",
    "price": "price",
    "staff": "staff behaviour",
    "packaging": "packaging",
    "hygiene": "hygiene",
    "app": "app or ordering",
    "other": "other issues",
}


def rules(org: Organization) -> dict:
    merged = dict(DEFAULT_RULES)
    merged.update({k: v for k, v in (org.ai_rules or {}).items() if k in DEFAULT_RULES})
    return merged


def reply_allowed(org: Organization, review: Review, analysis: ReviewAnalysis | None) -> bool:
    """Owner rules on top of auto-pilot's own checks: banned words never go out, escalated topics wait."""
    r = rules(org)
    if analysis is None:
        return False
    if analysis.category in set(r["escalate"]):
        return False
    text = f"{analysis.suggested_reply or ''}".lower()
    return not any(w.strip().lower() in text for w in r["banned_words"] if w.strip())


@dataclass
class Row:
    review: Review
    analysis: ReviewAnalysis | None
    outlet: str | None


def _rows(db: Session, ctx: OrgContext, since) -> list[Row]:  # noqa: ANN001
    stmt = (
        select(Review, ReviewAnalysis, Outlet.name)
        .outerjoin(ReviewAnalysis, ReviewAnalysis.review_id == Review.id)
        .outerjoin(Outlet, Outlet.id == Review.outlet_id)
        .where(Review.organization_id == ctx.org.id, Review.review_date >= since)
    )
    if not ctx.org.is_demo:  # the demo restaurant runs on its sample reviews; real ones never count samples
        stmt = stmt.where(Review.is_sample.is_(False))
    if ctx.outlet_ids is not None:
        stmt = stmt.where(Review.outlet_id.in_(ctx.outlet_ids))
    return [Row(r, a, o) for r, a, o in db.execute(stmt).all()]


def _negative(row: Row) -> bool:
    return bool(row.review.rating <= 2 or (row.analysis and row.analysis.sentiment == "negative"))


def crisis_radar(rows: list[Row], now_day) -> list[dict]:  # noqa: ANN001
    """The same complaint 3+ times at one outlet in 72 hours = a pattern, not bad luck. Ranked by severity."""
    recent = [r for r in rows if _negative(r) and r.analysis and (now_day - r.review.review_date).days <= 3]
    groups: dict[tuple, list[Row]] = defaultdict(list)
    for r in recent:
        groups[(r.outlet or "All outlets", r.analysis.category or "other")].append(r)
    out = []
    for (outlet, cat), items in groups.items():
        if len(items) < 3 and not (cat == "hygiene" and len(items) >= 2):
            continue
        severity = "critical" if cat == "hygiene" or len(items) >= 5 else "high"
        dishes = Counter(d for i in items for d in (i.analysis.dishes or []) if isinstance(d, str))
        out.append(
            {
                "outlet": outlet,
                "topic": LABEL.get(cat, cat),
                "count": len(items),
                "severity": severity,
                "likely_cause": (
                    f"Most mention {dishes.most_common(1)[0][0]}"
                    if dishes
                    else "Several guests describe the same problem"
                ),
                "examples": [i.analysis.summary or i.review.review_text[:120] for i in items[:3]],
                "action": _crisis_action(cat),
            }
        )
    return sorted(out, key=lambda c: (c["severity"] != "critical", -c["count"]))


def _crisis_action(cat: str) -> str:
    return {
        "hygiene": "Inspect the kitchen today, photograph the fix, and reply to each guest personally.",
        "food_quality": "Taste-check the batch with the head chef before the next service.",
        "delivery": "Check packing-to-pickup time and the delivery partner's handover this evening.",
        "packaging": "Switch to sealed containers for curries and gravies today.",
        "staff": "Talk to the shift team before the next service; reply to the guests with an apology.",
        "price": "Check the bill items guests mention; make sure menu and app prices match.",
    }.get(cat, "Read the reviews together with the outlet manager today and agree one fix.")


def todays_moves(rows: list[Row], now_day) -> list[dict]:  # noqa: ANN001
    """The three things worth doing today, picked from the last 7 days."""
    week = [r for r in rows if (now_day - r.review.review_date).days <= 6]
    moves: list[dict] = []
    waiting = [r for r in week if _negative(r) and r.review.workflow_status == "new"]
    if waiting:
        oldest = max((now_day - r.review.review_date).days for r in waiting)
        moves.append(
            {
                "kind": "reply",
                "title": f"Reply to {len(waiting)} unhappy guest{'s' if len(waiting) > 1 else ''}",
                "why": f"The oldest has waited {oldest} day{'s' if oldest != 1 else ''}. "
                "A reply within 24 hours wins back about a third of unhappy guests.",
                "link": "/app/inbox",
            }
        )
    complaints = Counter((r.outlet or "All outlets", r.analysis.category) for r in week if _negative(r) and r.analysis)
    if complaints:
        (outlet, cat), n = complaints.most_common(1)[0]
        moves.append(
            {
                "kind": "fix",
                "title": f"Fix {LABEL.get(cat, cat)} at {outlet}",
                "why": f"{n} complaint{'s' if n > 1 else ''} about it in the last 7 days, the most of any topic.",
                "link": "/app/insights",
            }
        )
    bad_dish = Counter(
        d for r in week if _negative(r) and r.analysis for d in (r.analysis.dishes or []) if isinstance(d, str)
    )
    if bad_dish:
        dish, n = bad_dish.most_common(1)[0]
        moves.append(
            {
                "kind": "dish",
                "title": f"Check the {dish}",
                "why": f"Named in {n} unhappy review{'s' if n > 1 else ''} this week.",
                "link": "/app/insights",
            }
        )
    praised = Counter(
        s
        for r in week
        if r.analysis and r.analysis.sentiment == "positive"
        for s in (r.analysis.staff or [])
        if isinstance(s, str)
    )
    if praised:
        name, n = praised.most_common(1)[0]
        moves.append(
            {
                "kind": "praise",
                "title": f"Thank {name} in today's team briefing",
                "why": f"Guests praised {name} {n} time{'s' if n > 1 else ''} this week.",
                "link": "/app/insights",
            }
        )
    if not moves:
        moves.append(
            {
                "kind": "grow",
                "title": "Ask today's happy guests for a Google review",
                "why": "No problems need you today, so it's a good day to grow your rating.",
                "link": "/app/settings",
            }
        )
    return moves[:3]


def recovery_queue(db: Session, ctx: OrgContext, rows: list[Row]) -> list[dict]:
    done = {
        g.review_id: g for g in db.scalars(select(GuestRecovery).where(GuestRecovery.organization_id == ctx.org.id))
    }
    out = []
    for r in rows:
        if not (_negative(r) and r.review.guest_contact):
            continue
        g = done.get(r.review.id)
        out.append(
            {
                "review_id": r.review.id,
                "guest": r.review.guest_name or "Guest",
                "contact": r.review.guest_contact,
                "rating": r.review.rating,
                "summary": (r.analysis.summary if r.analysis else None) or r.review.review_text[:140],
                "outlet": r.outlet,
                "date": r.review.review_date.isoformat(),
                "status": g.status if g else "new",
                "code": g.code if g else None,
                "message": g.message if g else None,
                "whatsapp_url": _wa_link(r.review.guest_contact, g.message) if g else None,
            }
        )
    return sorted(out, key=lambda x: (x["status"] != "new", x["date"]), reverse=False)[:30]


def _wa_link(contact: str, message: str) -> str | None:
    digits = "".join(ch for ch in contact if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) < 11:
        return None
    return f"https://wa.me/{digits}?text={quote(message)}"


def draft_recovery(db: Session, ctx: OrgContext, review_id: int) -> GuestRecovery:
    review = db.get(Review, review_id)
    if review is None or review.organization_id != ctx.org.id or not review.guest_contact:
        raise ValueError("That guest can't be contacted.")
    existing = db.scalar(select(GuestRecovery).where(GuestRecovery.review_id == review.id))
    if existing:
        return existing
    r = rules(ctx.org)
    analysis = db.scalar(select(ReviewAnalysis).where(ReviewAnalysis.review_id == review.id))
    code = "VR" + secrets.token_hex(3).upper()
    name = (review.guest_name or "").split(" ")[0]
    topic = LABEL.get(analysis.category, "your visit") if analysis and analysis.category else "your visit"
    if analysis and analysis.language in ("tamil", "tanglish"):
        text = (
            f"Vanakkam{(' ' + name) if name else ''}! {ctx.org.name}-la ungal anubavam ({topic}) sariyaga illai, "
            f"mannikkavum. Naangal adhai sari seidhuvittom. Adutha murai varumbodhu indha code kaattungal: {code} "
            f"({r['comeback_offer']}). Nandri!"
        )
    else:
        text = (
            f"Hi{(' ' + name) if name else ''}, this is {ctx.org.name}. We're truly sorry about {topic} on your visit; "
            f"we've looked into it and fixed it. Please give us another chance: show code {code} for "
            f"{r['comeback_offer']}. Thank you for telling us."
        )
    g = GuestRecovery(organization_id=ctx.org.id, review_id=review.id, code=code, message=text)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def mark(db: Session, ctx: OrgContext, review_id: int, status: str) -> GuestRecovery:
    g = db.scalar(
        select(GuestRecovery).where(GuestRecovery.review_id == review_id, GuestRecovery.organization_id == ctx.org.id)
    )
    if g is None:
        raise ValueError("Draft the message first.")
    now = datetime.now(UTC)
    g.status = status
    if status == "sent":
        g.sent_at = g.sent_at or now
    if status == "returned":
        g.returned_at = now
    db.commit()
    return g


def command_center(db: Session, ctx: OrgContext) -> dict:
    org = ctx.org
    today = today_local()
    since = today - timedelta(days=29)
    since_dt = datetime.now(UTC) - timedelta(days=30)
    rows = _rows(db, ctx, since)
    analysed = [r for r in rows if r.analysis and r.analysis.status == "analyzed"]
    drafts = [r for r in analysed if (r.analysis.suggested_reply or "").strip()]
    auto = [r for r in rows if r.review.auto_replied]
    negatives = [r for r in rows if _negative(r)]
    alerts = (
        db.scalar(
            select(func.count())
            .select_from(AlertLog)
            .where(AlertLog.organization_id == org.id, AlertLog.created_at >= since_dt)
        )
        or 0
    )
    asked = (
        db.scalar(
            select(func.count())
            .select_from(ReviewRequest)
            .where(ReviewRequest.organization_id == org.id, ReviewRequest.created_at >= since_dt)
        )
        or 0
    )
    briefs = (
        db.scalar(
            select(func.count())
            .select_from(WeeklyReport)
            .where(WeeklyReport.organization_id == org.id, WeeklyReport.created_at >= since_dt)
        )
        or 0
    )
    recs = list(db.scalars(select(GuestRecovery).where(GuestRecovery.organization_id == org.id)))
    crises = crisis_radar(rows, today)
    r = rules(org)

    minutes = len(analysed) * MIN_READ + len(drafts) * MIN_REPLY
    hours = round(minutes / 60, 1)
    at_risk = len(negatives) * GUESTS_PER_BAD_REVIEW * int(r["avg_order_value"])
    won_back = sum(1 for g in recs if g.status == "returned") * int(r["avg_order_value"])

    agents = [
        {
            "key": "listener",
            "sample": "Read 12 reviews before 9 am: 9 happy, 2 about slow delivery, 1 hygiene complaint sent to Meera.",
            "name": "Kavya",
            "role": "The Guest Whisperer",
            "job": "Reads every review the moment it arrives: mood, topic, urgency, dishes and staff named.",
            "status": "working",
            "done": len(analysed),
            "unit": "reviews read",
            "link": "/app/inbox",
        },
        {
            "key": "responder",
            "sample": "Replied to Karthik in Tamil: 'Ungal anbukku nandri! Adutha murai sambar innum soodaaga.'",
            "name": "Arjun",
            "role": "The Reply Maestro",
            "job": "Writes a reply in the guest's own language; posts happy Google replies itself, within your rules.",
            "status": "working" if org.autopilot_enabled else "approval",
            "done": len(drafts),
            "extra": f"{len(auto)} posted by itself",
            "unit": "replies written",
            "link": "/app/automation",
        },
        {
            "key": "guardian",
            "sample": "8:42 pm: 'Hair in the biryani' at RS Puram. Branch manager alerted in 40 seconds.",
            "name": "Meera",
            "role": "The Kitchen Guardian",
            "job": "Hygiene, food-safety and angry reviews reach the owner and branch manager within a minute.",
            "status": "working",
            "done": alerts,
            "unit": "alerts sent",
            "link": "/app/alerts",
        },
        {
            "key": "radar",
            "sample": "3 complaints about cold parcels at Gandhipuram since Friday. Likely cause: the 7-9 pm rush.",
            "name": "Vikram",
            "role": "The Trouble Spotter",
            "job": "Spots the same complaint repeating at one outlet within 72 hours, before it hurts your rating.",
            "status": "working",
            "done": len(crises),
            "unit": "patterns caught now",
            "link": "/app/ai-staff",
        },
        {
            "key": "winback",
            "sample": "Sent Divya an apology with code VR7F2A1. She came back on Sunday with her family.",
            "name": "Anbu",
            "role": "The Comeback Captain",
            "job": "Drafts an apology and a comeback code for unhappy guests who left a phone number.",
            "status": "working",
            "done": len(recs),
            "extra": f"{sum(1 for g in recs if g.status == 'returned')} came back",
            "unit": "guests contacted",
            "link": "/app/ai-staff",
        },
        {
            "key": "promoter",
            "sample": "Invited 40 happy dine-in guests to Google this week; 11 posted 5-star reviews.",
            "name": "Malar",
            "role": "The Star Builder",
            "job": "Invites happy guests to post on Google, so your rating climbs.",
            "status": "working" if org.ask_after_bill or asked else "setup",
            "done": asked,
            "unit": "review invites",
            "link": "/app/settings",
        },
        {
            "key": "analyst",
            "sample": "Monday: fix delivery packing, check the chilli parotta, thank Ramesh at Peelamedu.",
            "name": "Siva",
            "role": "The Monday Strategist",
            "job": "Sends a Monday brief: what to fix, which dish, who to thank, how each outlet moved.",
            "status": "working" if org.weekly_summary else "off",
            "done": briefs,
            "unit": "briefs sent",
            "link": "/app/settings",
        },
    ]
    return {
        "as_of": today.isoformat(),
        "agents": agents,
        "roi": {
            "reviews_read": len(analysed),
            "replies_written": len(drafts),
            "hours_saved": hours,
            "value_saved": int(hours * STAFF_RATE),
            "revenue_at_risk": at_risk,
            "revenue_won_back": won_back,
            "assumptions": (
                f"{int(MIN_READ)} min to read a review, {int(MIN_REPLY)} min to write a reply, "
                f"Rs {STAFF_RATE} an hour of a manager's time; each bad review turns away "
                f"{GUESTS_PER_BAD_REVIEW} guests at your average order of Rs {r['avg_order_value']}."
            ),
        },
        "moves": todays_moves(rows, today),
        "crises": crises,
        "recovery": recovery_queue(db, ctx, rows),
        "rules": r,
    }
