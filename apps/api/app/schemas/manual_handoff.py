from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

ManualHandoffTrigger = Literal[
    "captcha",
    "bot_detection",
    "login_required",
    "access_control",
]
ManualHandoffStatus = Literal["open", "resolved"]


class ManualHandoffCreate(BaseModel):
    url: HttpUrl
    source_domain: str | None = Field(default=None, min_length=1, max_length=500)
    trigger_type: ManualHandoffTrigger
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)
    detection_detail: str = Field(min_length=1)
    run_id: str | None = Field(default=None, min_length=1, max_length=36)


class ManualHandoffResolveRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=200)
    resolution_notes: str = Field(min_length=1)


class ManualHandoffRead(BaseModel):
    id: str
    url: str
    source_domain: str
    trigger_type: ManualHandoffTrigger
    requested_by: str
    status: ManualHandoffStatus
    detection_detail: str
    run_id: str | None
    created_at: datetime
    resolved_at: datetime | None
    resolution_notes: str | None

    model_config = ConfigDict(frozen=True)
