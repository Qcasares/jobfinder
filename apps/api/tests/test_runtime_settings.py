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
    }
    assert {capability.key for capability in runtime.capabilities if not capability.enabled} >= {
        "live_crawling",
        "llm_calls",
        "browser_automation",
        "autofill_submit",
        "real_candidate_data",
    }


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
