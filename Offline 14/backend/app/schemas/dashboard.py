"""Dashboard schemas (see PRPs/api-contract.md). Money values are string decimals."""

from pydantic import BaseModel

from app.models import DealStage, LeadSource


class DashboardSummary(BaseModel):
    """Headline counters for the dashboard."""

    contacts: int
    open_leads: int
    open_deals: int
    open_pipeline_value: str
    tasks_due_today: int
    tasks_overdue: int


class StageBucket(BaseModel):
    """Deal count and total value for one pipeline stage."""

    stage: DealStage
    count: int
    value: str


class MonthBucket(BaseModel):
    """Won deals for one calendar month ("YYYY-MM")."""

    month: str
    count: int
    value: str


class SourceBucket(BaseModel):
    """Lead count for one source."""

    source: LeadSource
    count: int


class DashboardAnalytics(BaseModel):
    """Chart data for the dashboard."""

    pipeline_by_stage: list[StageBucket]
    deals_won_by_month: list[MonthBucket]
    lead_conversion_rate: float
    leads_by_source: list[SourceBucket]
