from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class LiveDiscoveryStatus(StrEnum):
    REQUESTED = "requested"
    DENIED = "denied"
    FETCHED = "fetched"
    DISCOVERED = "discovered"
    EXTRACTED = "extracted"
    FAILED = "failed"


class LiveDiscoveryRequest(BaseModel):
    url: HttpUrl
    source_domain: str | None = Field(default=None, min_length=1, max_length=500)
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)


class LiveSearchDiscoveryRequest(BaseModel):
    url: HttpUrl
    source_domain: str | None = Field(default=None, min_length=1, max_length=500)
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)
    max_results: int = Field(default=25, ge=1, le=100)


class LiveDiscoveryFailure(BaseModel):
    reason: str
    detail: str

    model_config = ConfigDict(frozen=True)


class LiveDiscoveryRun(BaseModel):
    id: str
    url: str
    final_url: str | None = None
    source_domain: str
    requested_by: str
    status: LiveDiscoveryStatus
    fetched_status_code: int | None = Field(default=None, ge=100, le=599)
    content_type: str | None = None
    extracted_count: int = Field(default=0, ge=0)
    review_item_ids: tuple[str, ...] = ()
    discovered_count: int = Field(default=0, ge=0)
    discovered_urls: tuple[str, ...] = ()
    manual_handoff_id: str | None = None
    failure: LiveDiscoveryFailure | None = None

    model_config = ConfigDict(frozen=True)
