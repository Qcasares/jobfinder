from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ObservabilityAlertSeverity = Literal["info", "warning", "critical"]


class ObservabilityAlertRead(BaseModel):
    id: str
    severity: ObservabilityAlertSeverity
    title: str
    detail: str
    recommended_action: str

    model_config = ConfigDict(frozen=True)


class ObservabilitySummaryRead(BaseModel):
    total_audit_events: int = Field(ge=0)
    error_events: int = Field(ge=0)
    open_manual_handoffs: int = Field(ge=0)
    queued_discovery_runs: int = Field(ge=0)
    failed_discovery_runs: int = Field(ge=0)
    audit_chain_valid: bool
    latest_audit_hash: str | None
    active_alerts: list[ObservabilityAlertRead] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)
