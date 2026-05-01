from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit import ActorType, JsonValue


class AuditExplorerEvent(BaseModel):
    id: str
    event_type: str
    actor_type: ActorType
    actor_id: str
    correlation_id: str
    schema_version: int = Field(ge=1)
    previous_hash: str | None
    event_hash: str = Field(min_length=64, max_length=64)
    payload: dict[str, JsonValue]
    created_at: datetime

    model_config = ConfigDict(frozen=True)


class AuditChainVerification(BaseModel):
    valid: bool
    event_count: int = Field(ge=0)
    latest_hash: str | None
    invalid_event_id: str | None
    reason: str

    model_config = ConfigDict(frozen=True)


class AuditExplorerSummary(BaseModel):
    total_events: int = Field(ge=0)
    counts_by_event_type: dict[str, int]
    counts_by_actor_type: dict[str, int]
    latest_hash: str | None
    chain: AuditChainVerification

    model_config = ConfigDict(frozen=True)
