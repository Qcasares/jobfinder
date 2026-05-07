from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.extraction import RemoteType, ReviewStatus

ReviewQueueStatusFilter = Literal["all", "ready", "needs_review"]
ReviewDataOrigin = Literal[
    "synthetic_adapter_fixture",
    "synthetic_raw_posting",
    "live_extraction",
]


class ReviewProvenanceHint(BaseModel):
    field_name: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    note: str = ""

    model_config = ConfigDict(frozen=True)


class ReviewQueueItem(BaseModel):
    id: str
    source: str
    external_id: str
    source_url: str
    application_url: str | None
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
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    review_status: ReviewStatus
    review_reasons: tuple[str, ...]
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    provenance_hints: dict[str, ReviewProvenanceHint]
    synthetic: bool = True
    data_origin: ReviewDataOrigin
    fixture_name: str | None = None

    model_config = ConfigDict(frozen=True)


class ReviewQueueSummary(BaseModel):
    total: int = Field(ge=0)
    ready: int = Field(ge=0)
    needs_review: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
