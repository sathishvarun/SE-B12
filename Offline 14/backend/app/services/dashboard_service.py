"""Dashboard numbers, computed with SQL aggregates (COUNT / SUM / GROUP BY), scoped by user_id."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import Session

from app.config import local_today
from app.models import Contact, Deal, DealStage, Lead, LeadSource, LeadStatus, Task, TaskStatus
from app.schemas.dashboard import (
    DashboardAnalytics,
    DashboardSummary,
    MonthBucket,
    SourceBucket,
    StageBucket,
)

OPEN_DEAL_STAGES = (DealStage.PROSPECT, DealStage.PROPOSAL, DealStage.NEGOTIATION)
OPEN_LEAD_STATUSES = (LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED)
MONTHS_BACK = 6


def money(value: Any) -> str:
    """Format a numeric DB value (or None) as a 2-decimal string, e.g. "1500.00"."""
    return f"{Decimal(str(value or 0)):.2f}"


def _month_key(db: Session, column: Any) -> ColumnElement[str]:
    """SQL expression bucketing a timestamp column into "YYYY-MM".

    PostgreSQL uses to_char(date_trunc(...)); SQLite (used in tests) uses strftime.
    """
    if db.get_bind().dialect.name == "postgresql":
        return func.to_char(func.date_trunc("month", column), "YYYY-MM")
    return func.strftime("%Y-%m", column)


def _last_months(today: date, count: int) -> list[tuple[int, int]]:
    """Return (year, month) for the last ``count`` months incl. the current one, oldest first."""
    months: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def get_summary(db: Session, user_id: int, today: date | None = None) -> DashboardSummary:
    """Return the headline counters for the user's dashboard."""
    today = today or local_today()

    contacts = db.scalar(select(func.count(Contact.id)).where(Contact.user_id == user_id)) or 0
    open_leads = (
        db.scalar(
            select(func.count(Lead.id)).where(
                Lead.user_id == user_id, Lead.status.in_(OPEN_LEAD_STATUSES)
            )
        )
        or 0
    )
    open_deals, open_value = db.execute(
        select(func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0)).where(
            Deal.user_id == user_id, Deal.stage.in_(OPEN_DEAL_STAGES)
        )
    ).one()
    due_today, overdue = db.execute(
        select(
            func.count(case((Task.due_date == today, 1))),
            func.count(case((Task.due_date < today, 1))),
        ).where(Task.user_id == user_id, Task.status == TaskStatus.PENDING)
    ).one()

    return DashboardSummary(
        contacts=contacts,
        open_leads=open_leads,
        open_deals=open_deals or 0,
        open_pipeline_value=money(open_value),
        tasks_due_today=due_today or 0,
        tasks_overdue=overdue or 0,
    )


def get_analytics(db: Session, user_id: int, today: date | None = None) -> DashboardAnalytics:
    """Return chart data: pipeline by stage, won deals by month, conversion, leads by source."""
    today = today or local_today()

    # Pipeline by stage (all 5 stages, zeros included)
    stage_rows = db.execute(
        select(Deal.stage, func.count(Deal.id), func.coalesce(func.sum(Deal.value), 0))
        .where(Deal.user_id == user_id)
        .group_by(Deal.stage)
    ).all()
    by_stage = {DealStage(stage): (count, value) for stage, count, value in stage_rows}
    pipeline = [
        StageBucket(
            stage=stage,
            count=by_stage.get(stage, (0, 0))[0],
            value=money(by_stage.get(stage, (0, 0))[1]),
        )
        for stage in DealStage
    ]

    # Deals won by month (last 6 months incl. current, zeros included)
    months = _last_months(today, MONTHS_BACK)
    start_year, start_month = months[0]
    window_start = datetime(start_year, start_month, 1, tzinfo=UTC)
    # Bucket in a subquery so GROUP BY references a plain column (Postgres can't match
    # a repeated parameterised expression between SELECT and GROUP BY).
    won_deals = (
        select(_month_key(db, Deal.closed_at).label("month"), Deal.value.label("value"))
        .where(
            Deal.user_id == user_id,
            Deal.stage == DealStage.WON,
            Deal.closed_at.is_not(None),
            Deal.closed_at >= window_start,
        )
        .subquery()
    )
    won_rows = db.execute(
        select(
            won_deals.c.month,
            func.count(),
            func.coalesce(func.sum(won_deals.c.value), 0),
        ).group_by(won_deals.c.month)
    ).all()
    by_month = {key: (count, value) for key, count, value in won_rows}
    won = []
    for year, month in months:
        key = f"{year:04d}-{month:02d}"
        count, value = by_month.get(key, (0, 0))
        won.append(MonthBucket(month=key, count=count, value=money(value)))

    # Lead conversion rate and leads by source
    total_leads, converted = db.execute(
        select(
            func.count(Lead.id),
            func.count(case((Lead.status == LeadStatus.CONVERTED, 1))),
        ).where(Lead.user_id == user_id)
    ).one()
    rate = (converted / total_leads) if total_leads else 0.0

    source_rows = db.execute(
        select(Lead.source, func.count(Lead.id))
        .where(Lead.user_id == user_id)
        .group_by(Lead.source)
    ).all()
    by_source = {LeadSource(source): count for source, count in source_rows}
    sources = [SourceBucket(source=s, count=by_source.get(s, 0)) for s in LeadSource]

    return DashboardAnalytics(
        pipeline_by_stage=pipeline,
        deals_won_by_month=won,
        lead_conversion_rate=round(rate, 4),
        leads_by_source=sources,
    )
