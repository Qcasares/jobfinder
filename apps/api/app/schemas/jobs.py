from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.extraction import RemoteType, ReviewStatus

JobStatusFilter = Literal["all", "ready", "needs_review"]


class JobListItem(BaseModel):
    id: str
    source: str
    external_id: str
    title: str
    company: str
    locations: tuple[str, ...]
    remote_type: RemoteType
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    employment_type: str | None
    posted_date: date | None
    valid_through: date | None
    source_url: str
    application_url: str | None
    review_status: ReviewStatus
    review_reasons: tuple[str, ...]
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    fixture_name: str | None
    synthetic: bool = True

    model_config = ConfigDict(frozen=True)


class JobSummary(BaseModel):
    total: int = Field(ge=0)
    ready: int = Field(ge=0)
    needs_review: int = Field(ge=0)
    remote: int = Field(ge=0)
    hybrid: int = Field(ge=0)
    onsite: int = Field(ge=0)
    unknown_remote: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
