from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit import JsonValue

RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
ReviewStatus = Literal["ready", "needs_review"]


class FieldProvenance(BaseModel):
    field_name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    extraction_method: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    raw_value: JsonValue = None
    normalized_value: JsonValue = None
    note: str = ""

    model_config = ConfigDict(frozen=True)


class ExtractedJobPosting(BaseModel):
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
    responsibilities: str | None
    qualifications: str | None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    field_provenance: dict[str, FieldProvenance]
    requires_review: bool
    review_status: ReviewStatus
    review_reasons: tuple[str, ...] = ()

    model_config = ConfigDict(frozen=True)
