from __future__ import annotations

from app.config import Settings
from app.schemas.runtime_settings import RuntimeCapability, RuntimeSettingsRead


class RuntimeSettingsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_status(self) -> RuntimeSettingsRead:
        return RuntimeSettingsRead(
            service_name=self._settings.service_name,
            environment=self._settings.environment,
            audit_schema_version=self._settings.audit_schema_version,
            database_configured=bool(self._settings.database_url.strip()),
            redis_configured=bool(self._settings.redis_url.strip()),
            secrets_loaded=False,
            external_integrations_enabled=False,
            capabilities=[
                RuntimeCapability(
                    key="source_policy_gate",
                    label="Source policy gate",
                    enabled=True,
                    detail="Unknown and prohibited sources are denied by default.",
                ),
                RuntimeCapability(
                    key="audit_hash_chain",
                    label="Hash-chained audit log",
                    enabled=True,
                    detail="Material decisions are recorded with previous and current hashes.",
                ),
                RuntimeCapability(
                    key="single_user_local_mode",
                    label="Single-user local mode",
                    enabled=True,
                    detail=(
                        "Local owner fields are present, but no external auth provider is active."
                    ),
                ),
                RuntimeCapability(
                    key="live_crawling",
                    label="Live crawling",
                    enabled=False,
                    detail="Disabled in phase 1; only deterministic synthetic fixtures are used.",
                ),
                RuntimeCapability(
                    key="llm_calls",
                    label="LLM calls",
                    enabled=False,
                    detail="Disabled in phase 1; no model provider or API key is configured.",
                ),
                RuntimeCapability(
                    key="browser_automation",
                    label="Browser automation",
                    enabled=False,
                    detail="Disabled in phase 1; no browser agent is invoked by the product.",
                ),
                RuntimeCapability(
                    key="autofill_submit",
                    label="Autofill and submit",
                    enabled=False,
                    detail="Disabled in phase 1; application records remain read-only.",
                ),
                RuntimeCapability(
                    key="real_candidate_data",
                    label="Real candidate data",
                    enabled=False,
                    detail="Disabled in phase 1; only synthetic examples are accepted.",
                ),
            ],
        )
