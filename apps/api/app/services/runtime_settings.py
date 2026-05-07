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
            secrets_loaded=self._settings.operator_auth_configured,
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
                    key="operator_api_key",
                    label="Operator API key",
                    enabled=self._settings.operator_auth_configured,
                    detail=(
                        "Configured; production mutation endpoints require an operator key."
                        if self._settings.operator_auth_configured
                        else "Not configured; production mutation endpoints remain unavailable."
                    ),
                ),
                RuntimeCapability(
                    key="write_api",
                    label="Write API",
                    enabled=self._settings.production_writes_allowed,
                    detail=(
                        "Production write endpoints require explicit opt-in until "
                        "authentication and operator controls are configured."
                    ),
                ),
                RuntimeCapability(
                    key="live_crawling",
                    label="Live crawling",
                    enabled=False,
                    detail=(
                        "Disabled; broad unbounded crawling is not part of the live intake tranche."
                    ),
                ),
                RuntimeCapability(
                    key="live_discovery",
                    label="Live discovery",
                    enabled=self._settings.live_discovery_enabled,
                    detail=(
                        "Live discovery is explicitly enabled for policy-approved sources only."
                        if self._settings.live_discovery_enabled
                        else "Disabled by default; enable only with source policy and audit gates."
                    ),
                ),
                RuntimeCapability(
                    key="live_search_discovery",
                    label="Live search discovery",
                    enabled=self._settings.live_search_discovery_enabled,
                    detail=(
                        "Search-result discovery is explicitly enabled for approved sources only."
                        if self._settings.live_search_discovery_enabled
                        else "Disabled by default; enable only after crawl budgets and policies."
                    ),
                ),
                RuntimeCapability(
                    key="llm_calls",
                    label="LLM calls",
                    enabled=self._settings.llm_drafting_enabled,
                    detail=(
                        "Enabled only for drafting packets; outputs require human review and "
                        "cannot autofill or submit applications."
                        if self._settings.llm_drafting_enabled
                        else "Disabled by default; no model provider is invoked."
                    ),
                ),
                RuntimeCapability(
                    key="llm_drafting",
                    label="LLM-assisted drafting",
                    enabled=self._settings.llm_drafting_enabled,
                    detail=(
                        "Drafting packets are enabled with claim-to-evidence mapping and "
                        "review-required output."
                        if self._settings.llm_drafting_enabled
                        else "Disabled by default; drafting requires explicit runtime opt-in."
                    ),
                ),
                RuntimeCapability(
                    key="browser_automation",
                    label="Browser automation",
                    enabled=False,
                    detail=(
                        "Disabled; autofill packets are dry-run review artifacts and do not "
                        "invoke a browser agent."
                    ),
                ),
                RuntimeCapability(
                    key="autofill_packets",
                    label="Autofill packets",
                    enabled=self._settings.autofill_packets_enabled,
                    detail=(
                        "Enabled for dry-run field packets only; browser automation and submit "
                        "remain disabled."
                        if self._settings.autofill_packets_enabled
                        else "Disabled by default; packet preparation requires explicit opt-in."
                    ),
                ),
                RuntimeCapability(
                    key="submission_packets",
                    label="Final review packets",
                    enabled=self._settings.submission_packets_enabled,
                    detail=(
                        "Enabled for final review records only; no external submission is "
                        "performed by this API."
                        if self._settings.submission_packets_enabled
                        else "Disabled by default; final review packet preparation requires "
                        "explicit opt-in."
                    ),
                ),
                RuntimeCapability(
                    key="autofill_submit",
                    label="Autofill and submit",
                    enabled=False,
                    detail=(
                        "Disabled; autofill packets are dry-run review artifacts and external "
                        "submission remains blocked."
                    ),
                ),
                RuntimeCapability(
                    key="candidate_vault",
                    label="Candidate vault",
                    enabled=self._settings.candidate_vault_enabled,
                    detail=(
                        "Enabled for metadata-only candidate document records; document bytes "
                        "and credentials are not stored by Jobfinder."
                        if self._settings.candidate_vault_enabled
                        else "Disabled by default; real candidate document records require "
                        "explicit vault enablement."
                    ),
                ),
                RuntimeCapability(
                    key="real_candidate_data",
                    label="Real candidate data",
                    enabled=False,
                    detail=(
                        "Disabled for profile/evidence text; candidate vault records may only "
                        "reference external encrypted storage metadata when separately enabled."
                    ),
                ),
            ],
        )
