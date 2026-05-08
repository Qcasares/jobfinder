from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_production_live_mutations_require_configured_operator_auth() -> None:
    app = create_app(Settings(environment="production", database_url="sqlite+pysqlite:///:memory:"))

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Operator API key is not configured."}


def test_production_live_mutations_reject_missing_operator_key() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_api_key="operator-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "A valid operator API key is required."}


def test_production_manual_handoff_mutations_reject_missing_operator_key() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_api_key="operator-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/manual-handoffs",
            json={
                "url": "https://careers.example.test/jobs/platform",
                "trigger_type": "login_required",
                "requested_by": "operator-test",
                "detection_detail": "Manual handoff required.",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "A valid operator API key is required."}


def test_production_migration_upgrade_rejects_missing_operator_key() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_api_key="operator-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post("/maintenance/migrations/upgrade")

    assert response.status_code == 401
    assert response.json() == {"detail": "A valid operator API key is required."}


def test_production_live_mutations_accept_operator_key() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_api_key="operator-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            headers={"x-jobfinder-operator-key": "operator-secret"},
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert response.json()["failure"]["reason"] == "live_discovery_disabled"


def test_production_live_mutations_accept_signed_operator_session() -> None:
    settings = Settings(
        environment="production",
        database_url="sqlite+pysqlite:///:memory:",
        operator_login_secret="login-secret",
        operator_token_secret="token-secret",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        token_response = client.post(
            "/auth/operator-token",
            json={"login_secret": "login-secret", "actor_id": "operator-test"},
        )
        response = client.post(
            "/live-discovery/runs",
            headers={"authorization": f"Bearer {token_response.json()['access_token']}"},
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert token_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert response.json()["failure"]["reason"] == "live_discovery_disabled"


def test_production_live_mutations_accept_operator_key_when_session_auth_configured() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_api_key="operator-secret",
            operator_login_secret="login-secret",
            operator_token_secret="token-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            headers={"x-jobfinder-operator-key": "operator-secret"},
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert response.json()["failure"]["reason"] == "live_discovery_disabled"


def test_operator_token_rejects_invalid_login_secret() -> None:
    app = create_app(
        Settings(
            environment="production",
            database_url="sqlite+pysqlite:///:memory:",
            operator_login_secret="login-secret",
            operator_token_secret="token-secret",
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/operator-token",
            json={"login_secret": "wrong-secret", "actor_id": "operator-test"},
        )

    assert response.status_code == 401


def test_local_live_mutations_do_not_require_operator_key() -> None:
    app = create_app(Settings(environment="local-test", database_url="sqlite+pysqlite:///:memory:"))

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            json={"url": "https://careers.example.test/jobs/platform"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "denied"
    assert response.json()["failure"]["reason"] == "live_discovery_disabled"
