from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal["not_started", "ready_for_review", "approved", "submitted", "withdrawn"]


class ApplicationSafety(BaseModel):
    submit_performed: bool = False
    autofill_performed: bool = False
    external_side_effect: bool = False

    model_config = ConfigDict(frozen=True)


class ApplicationRead(BaseModel):
    id: str
    job_posting_id: str
    approval_request_id: str | None
    job_title: str
    company: str
    status: ApplicationStatus
    application_url: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    synthetic: bool = True
    safety: ApplicationSafety = Field(default_factory=ApplicationSafety)

    model_config = ConfigDict(frozen=True)


class ApplicationSummary(BaseModel):
    total: int = Field(ge=0)
    not_started: int = Field(ge=0)
    in_review: int = Field(ge=0)
    approved: int = Field(ge=0)
    submitted: int = Field(ge=0)
    external_side_effects: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
