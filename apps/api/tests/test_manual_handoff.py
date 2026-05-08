from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.main import create_app
from app.schemas.manual_handoff import ManualHandoffCreate, ManualHandoffResolveRequest
from app.services.audit import AuditEventService
from app.services.manual_handoff import ManualHandoffService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'handoffs.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'handoff-api.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url=database_url, service_name="jobfinder-api"))
    with TestClient(app) as test_client:
        yield test_client


def test_manual_handoff_service_creates_lists_and_resolves_records(session: Session) -> None:
    audit = AuditEventService(session)
    service = ManualHandoffService(session, audit_service=audit)

    record = service.create_record(
        ManualHandoffCreate(
            url="https://careers.example.test/jobs/platform",
            source_domain="careers.example.test",
            trigger_type="bot_detection",
            requested_by="operator-test",
            detection_detail="Manual handoff required: bot-detection control detected.",
            run_id="run-1",
        )
    )

    assert record.status == "open"
    assert record.source_domain == "careers.example.test"
    assert service.list_records(status="open")[0].id == record.id

    resolved = service.resolve_record(
        record.id,
        ManualHandoffResolveRequest(
            reviewer_id="reviewer-test",
            resolution_notes="Reviewed manually; no automation performed.",
        ),
    )

    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert [event.event_type for event in audit.list_events()] == [
        "manual_handoff.created",
        "manual_handoff.resolved",
    ]


def test_manual_handoff_endpoints_create_list_and_resolve_record(client: TestClient) -> None:
    create_response = client.post(
        "/manual-handoffs",
        json={
            "url": "https://careers.example.test/jobs/platform",
            "source_domain": "careers.example.test",
            "trigger_type": "login_required",
            "requested_by": "operator-test",
            "detection_detail": "Manual handoff required: login-only page detected.",
        },
    )

    assert create_response.status_code == 200
    record_id = create_response.json()["id"]

    list_response = client.get("/manual-handoffs?status=open")
    assert list_response.status_code == 200
    assert [record["id"] for record in list_response.json()] == [record_id]

    resolve_response = client.post(
        f"/manual-handoffs/{record_id}/resolve",
        json={
            "reviewer_id": "reviewer-test",
            "resolution_notes": "Reviewed manually; no automation performed.",
        },
    )

    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"
