from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

DiscoveryQueueMode = Literal["job", "search"]
DiscoveryQueueStatus = Literal[
    "queued",
    "rate_limited",
    "running",
    "completed",
    "failed",
    "manual_handoff_required",
]


class DiscoveryQueueRunCreate(BaseModel):
    url: HttpUrl
    source_domain: str | None = Field(default=None, min_length=1, max_length=500)
    mode: DiscoveryQueueMode = "job"
    requested_by: str = Field(default="operator", min_length=1, max_length=200)
    max_results: int = Field(default=25, ge=1, le=100)
    max_attempts: int = Field(default=3, ge=1, le=5)


class DiscoveryQueueRunRead(BaseModel):
    id: str
    mode: DiscoveryQueueMode
    url: str
    source_domain: str
    requested_by: str
    status: DiscoveryQueueStatus
    max_results: int
    attempts: int
    max_attempts: int
    rate_limit_after: datetime | None
    live_run_id: str | None
    manual_handoff_id: str | None
    failure_reason: str | None
    failure_detail: str | None
    discovered_urls: list[str]
    review_item_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(frozen=True)


class DiscoveryQueueBatchRead(BaseModel):
    requested_limit: int
    processed_count: int
    processed_run_ids: list[str]
    completed_count: int
    failed_count: int
    manual_handoff_count: int
    rate_limited_count: int

    model_config = ConfigDict(frozen=True)
