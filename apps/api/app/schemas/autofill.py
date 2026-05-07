from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

AutofillPacketStatus = Literal["denied", "review_required"]


class AutofillPacketRequest(BaseModel):
    drafting_run_id: str = Field(min_length=1, max_length=36)
    target_url: HttpUrl
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)


class AutofillPacketField(BaseModel):
    field_key: str
    value_preview: str
    provenance: str

    model_config = ConfigDict(frozen=True)


class AutofillPacketFailure(BaseModel):
    reason: str
    detail: str

    model_config = ConfigDict(frozen=True)


class AutofillPacketSafety(BaseModel):
    dry_run: bool = True
    browser_automation_performed: bool = False
    autofill_performed: bool = False
    submit_performed: bool = False
    application_created: bool = False

    model_config = ConfigDict(frozen=True)


class AutofillPacketRead(BaseModel):
    id: str
    drafting_run_id: str
    target_url: str
    requested_by: str
    status: AutofillPacketStatus
    fields: tuple[AutofillPacketField, ...] = ()
    approval_required: bool = True
    safety: AutofillPacketSafety = Field(default_factory=AutofillPacketSafety)
    failure: AutofillPacketFailure | None = None
    created_at: datetime

    model_config = ConfigDict(frozen=True)
