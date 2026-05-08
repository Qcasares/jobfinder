from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ObservabilitySummaryRead(BaseModel):
    total_audit_events: int = Field(ge=0)
    error_events: int = Field(ge=0)
    open_manual_handoffs: int = Field(ge=0)
    queued_discovery_runs: int = Field(ge=0)
    failed_discovery_runs: int = Field(ge=0)
    audit_chain_valid: bool
    latest_audit_hash: str | None

    model_config = ConfigDict(frozen=True)
