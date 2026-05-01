from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DashboardCounts(BaseModel):
    job_postings: int = Field(ge=0)
    approval_requests: int = Field(ge=0)
    applications: int = Field(ge=0)
    audit_events: int = Field(ge=0)


class DashboardStatus(BaseModel):
    service: str
    database: str
    policy_mode: str


class DashboardAuditFeedItem(BaseModel):
    event_type: str
    actor: str
    summary: str
    created_at: datetime
    synthetic: bool = True


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    status: DashboardStatus
    audit_feed: list[DashboardAuditFeedItem]

    model_config = ConfigDict(frozen=True)
