from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RuntimeCapabilityKey = Literal[
    "source_policy_gate",
    "audit_hash_chain",
    "single_user_local_mode",
    "write_api",
    "live_crawling",
    "llm_calls",
    "browser_automation",
    "autofill_submit",
    "real_candidate_data",
]


class RuntimeCapability(BaseModel):
    key: RuntimeCapabilityKey
    label: str
    enabled: bool
    detail: str

    model_config = ConfigDict(frozen=True)


class RuntimeSettingsRead(BaseModel):
    service_name: str
    environment: str
    audit_schema_version: int = Field(ge=1)
    database_configured: bool
    redis_configured: bool
    secrets_loaded: bool = False
    external_integrations_enabled: bool = False
    capabilities: list[RuntimeCapability]

    model_config = ConfigDict(frozen=True)
