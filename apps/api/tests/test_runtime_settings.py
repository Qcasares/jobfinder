from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas.runtime_settings import RuntimeSettingsRead
from app.services.runtime_settings import RuntimeSettingsService


def test_runtime_settings_expose_safe_posture_without_secret_values() -> None:
    settings = Settings(
        service_name="jobfinder-api",
        environment="local-test",
        database_url="postgresql+psycopg://user:password@localhost:5432/jobfinder",
        redis_url="redis://:password@localhost:6379/0",
        audit_schema_version=3,
    )

    runtime = RuntimeSettingsService(settings).get_status()

    assert runtime.service_name == "jobfinder-api"
    assert runtime.environment == "local-test"
    assert runtime.audit_schema_version == 3
    assert runtime.database_configured is True
    assert runtime.redis_configured is True
    assert runtime.secrets_loaded is False
    assert runtime.external_integrations_enabled is False
    assert all("password" not in capability.detail for capability in runtime.capabilities)
    assert {capability.key for capability in runtime.capabilities if capability.enabled} == {
        "source_policy_gate",
        "audit_hash_chain",
        "single_user_local_mode",
        "write_api",
    }
    assert {capability.key for capability in runtime.capabilities if not capability.enabled} >= {
        "operator_api_key",
        "live_crawling",
        "live_discovery",
        "live_search_discovery",
        "llm_calls",
        "llm_drafting",
        "browser_automation",
        "autofill_packets",
        "submission_packets",
        "autofill_submit",
        "real_candidate_data",
        "candidate_vault",
    }


def test_runtime_settings_can_expose_explicit_live_discovery_opt_in() -> None:
    settings = Settings(live_discovery_enabled=True, live_search_discovery_enabled=True)

    runtime = RuntimeSettingsService(settings).get_status()

    live_discovery = next(
        capability for capability in runtime.capabilities if capability.key == "live_discovery"
    )
    live_search_discovery = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "live_search_discovery"
    )
    assert live_discovery.enabled is True
    assert "explicitly enabled" in live_discovery.detail
    assert live_search_discovery.enabled is True
    assert "explicitly enabled" in live_search_discovery.detail


def test_runtime_settings_can_expose_operator_key_configuration() -> None:
    settings = Settings(environment="production", operator_api_key="operator-secret")

    runtime = RuntimeSettingsService(settings).get_status()

    operator_key = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "operator_api_key"
    )
    assert runtime.secrets_loaded is True
    assert operator_key.enabled is True
    assert "operator-secret" not in operator_key.detail
    assert "Configured" in operator_key.detail


def test_runtime_settings_can_expose_candidate_vault_opt_in() -> None:
    settings = Settings(candidate_vault_enabled=True)

    runtime = RuntimeSettingsService(settings).get_status()

    vault = next(
        capability for capability in runtime.capabilities if capability.key == "candidate_vault"
    )
    real_candidate_data = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "real_candidate_data"
    )
    assert vault.enabled is True
    assert "metadata-only" in vault.detail
    assert real_candidate_data.enabled is False


def test_runtime_settings_can_expose_llm_drafting_opt_in() -> None:
    settings = Settings(llm_drafting_enabled=True)

    runtime = RuntimeSettingsService(settings).get_status()

    llm_calls = next(
        capability for capability in runtime.capabilities if capability.key == "llm_calls"
    )
    drafting = next(
        capability for capability in runtime.capabilities if capability.key == "llm_drafting"
    )
    browser_automation = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "browser_automation"
    )
    assert llm_calls.enabled is True
    assert drafting.enabled is True
    assert "review-required" in drafting.detail
    assert browser_automation.enabled is False


def test_runtime_settings_can_expose_autofill_packet_opt_in() -> None:
    settings = Settings(autofill_packets_enabled=True)

    runtime = RuntimeSettingsService(settings).get_status()

    packets = next(
        capability for capability in runtime.capabilities if capability.key == "autofill_packets"
    )
    browser_automation = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "browser_automation"
    )
    submit = next(
        capability for capability in runtime.capabilities if capability.key == "autofill_submit"
    )
    assert packets.enabled is True
    assert "dry-run" in packets.detail
    assert browser_automation.enabled is False
    assert submit.enabled is False


def test_runtime_settings_can_expose_submission_packet_opt_in() -> None:
    settings = Settings(submission_packets_enabled=True)

    runtime = RuntimeSettingsService(settings).get_status()

    packets = next(
        capability
        for capability in runtime.capabilities
        if capability.key == "submission_packets"
    )
    submit = next(
        capability for capability in runtime.capabilities if capability.key == "autofill_submit"
    )
    assert packets.enabled is True
    assert "no external submission" in packets.detail
    assert submit.enabled is False


def test_runtime_settings_endpoint_returns_typed_schema() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            redis_url="",
            service_name="jobfinder-api",
            environment="test",
        )
    )

    with TestClient(app) as client:
        response = client.get("/settings/runtime")

    assert response.status_code == 200
    payload_text = response.text
    runtime = RuntimeSettingsRead.model_validate(response.json())
    assert runtime.redis_configured is False
    assert runtime.database_configured is True
    assert "sqlite+pysqlite" not in payload_text
    assert "redis://" not in payload_text
