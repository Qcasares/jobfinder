from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import AuditEvent
from app.db.session import get_engine
from app.main import create_app
from app.schemas.policy import PolicyAction, PolicyStatus
from app.services.source_registry import SourceRegistryService


@pytest.fixture
def client_and_database_url(tmp_path: Path) -> Iterator[tuple[TestClient, str]]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url=database_url, service_name="jobfinder-api"))
    with TestClient(app) as client:
        yield client, database_url


def test_policy_check_endpoint_denies_unknown_domain_and_persists_audit_event(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, database_url = client_and_database_url

    response = client.post(
        "/source-policies/check",
        json={"domain": "unknown.example", "action": "discover"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == PolicyStatus.UNKNOWN_SOURCE
    assert response.json()["allowed"] is False

    with Session(get_engine(database_url)) as session:
        events = session.scalars(select(AuditEvent)).all()

    assert len(events) == 1
    assert events[0].event_type == "source_policy.decision"
    assert events[0].payload["source_id"] == "unknown.example"
    assert events[0].payload["allowed"] is False


def test_policy_check_endpoint_allows_explicit_persisted_policy(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, database_url = client_and_database_url

    with Session(get_engine(database_url)) as session:
        service = SourceRegistryService(session)
        source = service.upsert_source(
            domain="ashbyhq.com",
            name="Ashby",
            source_type="official_ats",
        )
        service.attach_source_policy(
            source_id=source.id,
            status="approved",
            reason="Official integration permits extraction.",
            allowed_actions=[PolicyAction.EXTRACT],
            denied_actions=[PolicyAction.SUBMIT],
            evidence=[],
        )
        session.commit()

    response = client.post(
        "/source-policies/check",
        json={"domain": "https://www.ashbyhq.com/jobs", "action": "extract"},
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["status"] == PolicyStatus.ALLOWED


def test_seed_known_endpoint_creates_prohibited_sources(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, _ = client_and_database_url

    seed_response = client.post("/source-policies/seed-known")
    check_response = client.post(
        "/source-policies/check",
        json={"domain": "linkedin.com", "action": "extract"},
    )

    assert seed_response.status_code == 200
    assert len(seed_response.json()) == 2
    assert check_response.status_code == 200
    assert check_response.json()["allowed"] is False
    assert check_response.json()["status"] == PolicyStatus.DENIED


def test_local_dashboard_origin_can_preflight_policy_check(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, _ = client_and_database_url

    response = client.options(
        "/source-policies/check",
        headers={
            "origin": "http://127.0.0.1:3000",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_untrusted_origin_does_not_receive_cors_allow_origin(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, _ = client_and_database_url

    response = client.options(
        "/source-policies/check",
        headers={
            "origin": "https://untrusted.example",
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
