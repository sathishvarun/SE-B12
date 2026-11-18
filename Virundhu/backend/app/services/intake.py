"""Bring reviews in: CSV/Excel files, single reviews, and the Zomato/Swiggy test feed."""

import io
import logging
from datetime import UTC, date, datetime, timedelta

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ImportBatch, Outlet, Review

logger = logging.getLogger(__name__)
MAX_ROWS = 5000
ALIASES = {
    "review_id": ("review_id", "id", "reviewid", "review id", "order_id"),
    "date": ("date", "review_date", "created", "created_at", "review date"),
    "platform": ("platform", "source", "site", "channel"),
    "rating": ("rating", "stars", "star", "score"),
    "review_text": ("review_text", "review", "text", "comment", "comments", "feedback", "review text"),
    "outlet": ("outlet", "branch", "store", "location", "outlet_name"),
}
PLATFORM_WORDS = {
    "google": "google",
    "gmb": "google",
    "google maps": "google",
    "zomato": "zomato",
    "swiggy": "swiggy",
    "tripadvisor": "tripadvisor",
    "trip advisor": "tripadvisor",
    "instagram": "instagram",
    "insta": "instagram",
    "facebook": "facebook",
    "fb": "facebook",
}


class IntakeError(ValueError):
    """A problem with the uploaded file that the user can fix."""


def normalise_platform(value: object) -> str:
    text = str(value or "").strip().lower()
    for word, platform in PLATFORM_WORDS.items():
        if word in text:
            return platform
    return "other"


def _parse_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() == "":
        return None
    for dayfirst in (False, True):
        try:
            parsed = pd.to_datetime(str(value).strip(), dayfirst=dayfirst, errors="raise")
            return parsed.date()
        except (ValueError, TypeError):
            continue
    return None


def read_table(content: bytes, filename: str) -> pd.DataFrame:
    """CSV (UTF-8 / UTF-8 with BOM) or Excel into a DataFrame with standard column names."""
    name = filename.lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        else:
            df = pd.read_csv(io.BytesIO(content), dtype=str, encoding="utf-8-sig", keep_default_na=False)
    except Exception as exc:
        raise IntakeError("Couldn't read this file. Save it as CSV (UTF-8) or Excel (.xlsx) and try again.") from exc
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename = {}
    for std, options in ALIASES.items():
        for col in df.columns:
            if col in options:
                rename[col] = std
                break
    df = df.rename(columns=rename)
    if "review_text" not in df.columns:
        raise IntakeError("The file needs a column called review_text (the review itself).")
    if "rating" not in df.columns:
        raise IntakeError("The file needs a column called rating (1 to 5 stars).")
    if len(df) > MAX_ROWS:
        raise IntakeError(f"Please upload at most {MAX_ROWS} reviews at a time. This file has {len(df)}.")
    return df.fillna("")


def default_outlet(db: Session, org_id: int) -> Outlet:
    """The first outlet, created as 'Main outlet' if the restaurant has none yet."""
    outlet = db.scalar(select(Outlet).where(Outlet.organization_id == org_id, Outlet.is_active).order_by(Outlet.id))
    if outlet is None:
        outlet = Outlet(organization_id=org_id, name="Main outlet")
        db.add(outlet)
        db.flush()
    return outlet


def import_file(
    db: Session,
    org_id: int,
    user_id: int,
    content: bytes,
    filename: str,
    outlet_id: int | None,
    force_outlet: bool = False,
) -> tuple[ImportBatch, list[int]]:
    """Validate and insert rows. Returns the batch and the ids of newly added reviews."""
    df = read_table(content, filename)
    outlets = {o.name.lower(): o.id for o in db.scalars(select(Outlet).where(Outlet.organization_id == org_id))}
    fallback = outlet_id if outlet_id in outlets.values() else default_outlet(db, org_id).id
    created: list[str] = []
    if not force_outlet:
        # Branch names in the file that we don't know yet become new outlets (up to the plan's outlet limit).
        from app.models import Organization
        from app.services.plans import limits_for

        org = db.get(Organization, org_id)
        room = limits_for(org)["outlets"] - db.scalar(
            select(func.count(Outlet.id)).where(Outlet.organization_id == org_id, Outlet.is_active)
        )
        names = {str(x).strip() for x in df.get("outlet", []) if str(x).strip() and str(x).strip().lower() != "nan"}
        for name in sorted(names, key=str.lower):
            if name.lower() in outlets or room <= 0:
                continue
            o = Outlet(organization_id=org_id, name=name[:120])
            db.add(o)
            db.flush()
            outlets[name.lower()] = o.id
            created.append(name)
            room -= 1
    today = datetime.now(UTC).date()
    batch = ImportBatch(
        organization_id=org_id, uploaded_by=user_id, filename=filename[:255], total_rows=len(df), status="processing"
    )
    db.add(batch)
    db.flush()
    errors, new_ids, duplicates = [], [], 0
    for i, row in enumerate(df.to_dict("records"), start=2):  # row 1 is the header
        text = str(row.get("review_text", "")).strip()
        try:
            rating = int(float(str(row.get("rating", "")).strip()))
        except ValueError:
            rating = 0
        if not 1 <= rating <= 5:
            errors.append({"row": i, "reason": "Rating must be a number from 1 to 5."})
            continue
        review_date = _parse_date(row.get("date")) or today
        if review_date > today + timedelta(days=1):
            errors.append({"row": i, "reason": "The date is in the future."})
            continue
        platform = normalise_platform(row.get("platform"))
        ext = str(row.get("review_id", "")).strip() or f"{platform}-{review_date}-{abs(hash(text)) % 10**10}"
        outlet_name = str(row.get("outlet", "")).strip().lower()
        stmt = (
            insert(Review)
            .values(
                organization_id=org_id,
                outlet_id=fallback if force_outlet else outlets.get(outlet_name, fallback),
                import_batch_id=batch.id,
                external_id=ext[:120],
                platform=platform,
                rating=rating,
                review_date=review_date,
                review_text=text[:5000],
                analysis_status="pending",
                workflow_status="new",
            )
            .on_conflict_do_nothing(constraint="uq_review_org_platform_ext")
            .returning(Review.id)
        )
        new_id = db.execute(stmt).scalar()
        if new_id:
            new_ids.append(new_id)
        else:
            duplicates += 1
    batch.valid_rows, batch.duplicate_rows, batch.invalid_rows = len(new_ids), duplicates, len(errors)
    if created:
        errors.append({"row": 0, "reason": f"New outlets added from the file: {', '.join(created)}."})
    batch.error_report = errors[:500] or None
    if not new_ids:
        batch.status, batch.finished_at = "completed", datetime.now(UTC)
    db.commit()
    return batch, new_ids


def add_single(
    db: Session, org_id: int, text: str, rating: int, platform: str, outlet_id: int | None, review_date: date | None
) -> Review:
    """One review typed or pasted by the team."""
    outlet = (
        db.scalar(select(Outlet).where(Outlet.id == outlet_id, Outlet.organization_id == org_id))
        if outlet_id
        else default_outlet(db, org_id)
    )
    review = Review(
        organization_id=org_id,
        outlet_id=outlet.id if outlet else None,
        external_id=f"manual-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        platform=platform,
        rating=rating,
        review_date=review_date or datetime.now(UTC).date(),
        review_text=text.strip(),
        analysis_status="pending",
        workflow_status="new",
    )
    db.add(review)
    db.commit()
    return review
