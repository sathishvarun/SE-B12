"""Add reviews: file upload, single review, import history, test feed."""

import asyncio
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OrgContext, get_org_context, require_owner, require_writable
from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.models import ImportBatch, Review, SourceConnection
from app.services import google_reviews, intake
from app.services.queue import enqueue_analysis

router = APIRouter(prefix="/api/v1", tags=["intake"])
MAX_BYTES = 5 * 1024 * 1024
TEMPLATE = (
    "review_id,date,platform,rating,review_text,outlet\n"
    'R-1001,2026-11-10,Zomato,5,"Biryani was amazing, packing also neat.",Anna Nagar\n'
    'R-1002,2026-11-10,Swiggy,1,"Delivery romba late, food ellam cold",Anna Nagar\n'
)


class BatchOut(BaseModel):
    id: int
    filename: str
    status: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    analyzed_rows: int
    errors: list[dict] | None
    created_at: datetime | None = None
    source: str = "file"


def _batch_out(b: ImportBatch) -> BatchOut:
    return BatchOut(
        id=b.id,
        filename=b.filename,
        status=b.status,
        total_rows=b.total_rows,
        valid_rows=b.valid_rows,
        duplicate_rows=b.duplicate_rows,
        invalid_rows=b.invalid_rows,
        analyzed_rows=b.analyzed_rows,
        errors=b.error_report,
        created_at=b.created_at,
        source="paste"
        if b.filename.startswith("Pasted")
        else "screenshot"
        if b.filename.startswith("Screenshot")
        else "file",
    )


def _source(filename: str) -> str:
    if filename.startswith("Pasted"):
        return "paste"
    return "screenshot" if filename.startswith("Screenshot") else "file"


def _log_batch(db: Session, ctx: OrgContext, label: str, ids: list[int], duplicates: int = 0) -> int:
    """Record pasted and screenshot reviews in the same upload log as files, so owners see where every review went."""
    batch = ImportBatch(
        organization_id=ctx.org.id,
        uploaded_by=ctx.user.id,
        filename=label[:255],
        total_rows=len(ids) + duplicates,
        valid_rows=len(ids),
        duplicate_rows=duplicates,
        status="processing" if ids else "completed",
    )
    db.add(batch)
    db.flush()
    for rid in ids:
        r = db.get(Review, rid)
        if r is not None:
            r.import_batch_id = batch.id
    db.commit()
    return batch.id


def _allowed_outlet(ctx: OrgContext, outlet_id: int | None) -> int | None:
    """Outlet staff can only add reviews to their own outlets."""
    if ctx.outlet_ids is None:
        return outlet_id
    return outlet_id if outlet_id in ctx.outlet_ids else ctx.outlet_ids[0]


@router.post("/imports", response_model=BatchOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    outlet_id: int | None = Form(default=None),
    ctx: OrgContext = Depends(require_writable),
    db: Session = Depends(get_db),
) -> BatchOut:
    """Upload a CSV or Excel file of reviews. Reading starts straight away in the background."""
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "This file is over 5 MB. Split it into smaller files.")
    try:
        batch, new_ids = intake.import_file(
            db,
            ctx.org.id,
            ctx.user.id,
            content,
            file.filename or "reviews.csv",
            _allowed_outlet(ctx, outlet_id),
            force_outlet=ctx.outlet_ids is not None,
        )
    except intake.IntakeError as exc:
        raise HTTPException(400, str(exc)) from exc
    await enqueue_analysis(ctx.org.id, new_ids, batch.id)
    return _batch_out(batch)


@router.get("/imports", response_model=list[BatchOut])
def list_batches(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> list[BatchOut]:
    """Recent uploads, newest first."""
    rows = db.scalars(
        select(ImportBatch).where(ImportBatch.organization_id == ctx.org.id).order_by(ImportBatch.id.desc()).limit(20)
    )
    return [_batch_out(b) for b in rows]


@router.get("/imports/template.csv")
def template() -> Response:
    """A ready-to-fill CSV template."""
    return Response(
        TEMPLATE,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=virundhu-reviews-template.csv"},
    )


@router.get("/imports/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: int, ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> BatchOut:
    """Progress of one upload (polled by the page)."""
    b = db.scalar(select(ImportBatch).where(ImportBatch.id == batch_id, ImportBatch.organization_id == ctx.org.id))
    if b is None:
        raise HTTPException(404, "Upload not found.")
    return _batch_out(b)


class SingleIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    rating: int = Field(ge=1, le=5)
    platform: str = Field(pattern="^(google|zomato|swiggy|tripadvisor|instagram|facebook|other)$")
    outlet_id: int | None = None
    review_date: date | None = None


@router.post("/reviews", status_code=status.HTTP_202_ACCEPTED)
async def add_review(
    body: SingleIn, ctx: OrgContext = Depends(require_writable), db: Session = Depends(get_db)
) -> dict[str, int]:
    """Add one review by hand. It is read by the AI within seconds."""
    review = intake.add_single(
        db, ctx.org.id, body.text, body.rating, body.platform, _allowed_outlet(ctx, body.outlet_id), body.review_date
    )
    batch_id = _log_batch(db, ctx, f"Pasted review ({body.platform.title()}, {body.rating}★)", [review.id])
    await enqueue_analysis(ctx.org.id, [review.id], batch_id)
    return {"id": review.id, "batch_id": batch_id}


class ShotOut(BaseModel):
    added: int
    duplicates: int
    reviews: list[dict]


@router.post("/imports/screenshot", response_model=ShotOut)
@limiter.limit("20/minute")
async def from_screenshot(
    request: Request,
    file: UploadFile = File(...),
    platform: str = Form(default="zomato", pattern="^(google|zomato|swiggy|tripadvisor|instagram|facebook|other)$"),
    outlet_id: int | None = Form(default=None),
    ctx: OrgContext = Depends(require_writable),
    db: Session = Depends(get_db),
) -> ShotOut:
    """A screenshot of the Zomato/Swiggy partner app: the AI reads the reviews in it and adds them."""
    from app.ai.screenshot import read_screenshot

    mime = (file.content_type or "").lower()
    if mime not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(400, "Upload a screenshot as PNG, JPG or WebP.")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "This image is over 5 MB. Take a smaller screenshot.")
    if not settings.llm_configured:
        raise HTTPException(503, "Reading screenshots needs the AI key. Add it in .env first.")
    try:
        found = await asyncio.to_thread(read_screenshot, content, mime)
    except Exception as exc:
        raise HTTPException(502, "Couldn't read this screenshot. Try a clearer one, or paste the review.") from exc
    outlet = _allowed_outlet(ctx, outlet_id)
    existing = set(
        db.scalars(
            select(Review.review_text)
            .where(Review.organization_id == ctx.org.id, Review.platform == platform)
            .limit(5000)
        )
    )
    ids, dupes = [], 0
    for r in found:
        text = r.review_text.strip()
        if text in existing:
            dupes += 1
            continue
        existing.add(text)
        ids.append(intake.add_single(db, ctx.org.id, text, r.rating, platform, outlet, None).id)
    batch_id = _log_batch(db, ctx, f"Screenshot: {(file.filename or 'image')[:120]} ({platform.title()})", ids, dupes)
    if ids:
        await enqueue_analysis(ctx.org.id, ids, batch_id)
    return ShotOut(
        added=len(ids), duplicates=dupes, reviews=[{"rating": r.rating, "text": r.review_text[:200]} for r in found]
    )


class ConnectionOut(BaseModel):
    provider: str
    status: str
    account_email: str | None = None
    locations: list[str] = []
    last_synced_at: datetime | None = None
    last_error: str | None = None
    official_api: bool
    note: str
    available: bool = True


NOTES = {
    "google": "Live and official. Sign in with the Google account that manages your restaurant's Google listing. New "
    "reviews arrive every 10 minutes and replies are posted back to Google.",
    "zomato": "Not live yet. Zomato doesn't let outside software read restaurant reviews unless it is an approved "
    "Zomato integration partner. Once approved, this connects here. Until then, paste Zomato reviews in Add reviews; "
    "the inbox copies your reply and opens Zomato's partner site.",
    "swiggy": "Not live yet. Swiggy doesn't let outside software read restaurant reviews unless it is an approved "
    "Swiggy integration partner. Once approved, this connects here. Until then, paste Swiggy reviews in Add reviews; "
    "the inbox copies your reply and opens Swiggy's partner site.",
}


@router.get("/connections", response_model=list[ConnectionOut])
def connections(ctx: OrgContext = Depends(get_org_context), db: Session = Depends(get_db)) -> list[ConnectionOut]:
    """Review sources and their status."""
    rows = {
        c.provider: c
        for c in db.scalars(select(SourceConnection).where(SourceConnection.organization_id == ctx.org.id))
    }
    out = []
    for provider in ("google", "zomato", "swiggy"):
        c = rows.get(provider)
        out.append(
            ConnectionOut(
                provider=provider,
                status=c.status if c else "not_connected",
                official_api=provider == "google",
                note=NOTES[provider],
                account_email=(c.details or {}).get("email") if c else None,
                locations=(c.details or {}).get("locations") or [] if c else [],
                last_synced_at=c.last_synced_at if c else None,
                last_error=(c.details or {}).get("last_error") if c else None,
                available=settings.google_enabled if provider == "google" else True,
            )
        )
    return out


# ---------------- Google Business Profile (live reviews) ----------------
@router.post("/connections/google/start")
def google_start(ctx: OrgContext = Depends(require_owner)) -> dict[str, str]:
    """Where to send the owner to give Virundhu access to their Google reviews."""
    if not settings.google_enabled:
        raise HTTPException(
            503, "Google connection is being switched on by the Virundhu team. Add Google reviews by paste for now."
        )
    return {"url": google_reviews.connect_url(ctx.org.id, ctx.user.id)}


def _sync_and_read(org_id: int, plan: str) -> None:
    from app.database import SessionLocal
    from app.services.analysis import analyze_reviews

    with SessionLocal() as db:
        new_ids = google_reviews.sync(db, org_id, plan)
        if new_ids:
            analyze_reviews(db, org_id, new_ids)


@router.post("/connections/google/sync", status_code=status.HTTP_202_ACCEPTED)
def google_sync(background: BackgroundTasks, ctx: OrgContext = Depends(require_owner)) -> dict[str, bool]:
    """Fetch new Google reviews now (also happens automatically every 10 minutes)."""
    background.add_task(_sync_and_read, ctx.org.id, ctx.org.plan)
    return {"ok": True}


@router.post("/connections/google/disconnect")
def google_disconnect(ctx: OrgContext = Depends(require_owner), db: Session = Depends(get_db)) -> dict[str, bool]:
    google_reviews.disconnect(db, ctx.org.id)
    return {"ok": True}
