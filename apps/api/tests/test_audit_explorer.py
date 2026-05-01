from __future__ import annotations

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
from app.schemas.audit import ActorType
from app.schemas.audit_explorer import AuditChainVerification, AuditExplorerSummary
from app.services.audit import AuditEventService
from app.services.audit_explorer import AuditExplorerService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'audit.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client_and_database_url(tmp_path: Path) -> Iterator[tuple[TestClient, str]]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url=database_url, service_name="jobfinder-api"))
    with TestClient(app) as client:
        yield client, database_url


def seed_audit_events(session: Session) -> tuple[str, str]:
    audit = AuditEventService(session=session)
    first = audit.create_event(
        event_type="approval.request.created",
        actor_type=ActorType.USER,
        actor_id="reviewer-local",
        correlation_id="approval-1",
        payload={"review_item_id": "greenhouse:101", "submit_performed": False},
    )
    second = audit.create_event(
        event_type="approval.request.decided",
        actor_type=ActorType.USER,
        actor_id="reviewer-local",
        correlation_id="approval-1",
        payload={"decision": "approved", "autofill_performed": False},
    )
    audit.create_event(
        event_type="source_policy.decision",
        actor_type=ActorType.SYSTEM,
        actor_id="policy-service",
        correlation_id="policy-1",
        payload={"allowed": False},
    )
    session.commit()
    return first.id, second.id


def test_empty_audit_log_summary_and_chain_verification(session: Session) -> None:
    service = AuditExplorerService(session)

    assert service.list_events() == []
    assert service.verify_chain() == AuditChainVerification(
        valid=True,
        event_count=0,
        latest_hash=None,
        invalid_event_id=None,
        reason="empty audit log",
    )
    assert service.get_summary() == AuditExplorerSummary(
        total_events=0,
        counts_by_event_type={},
        counts_by_actor_type={},
        latest_hash=None,
        chain=service.verify_chain(),
    )


def test_ordered_listing_limit_and_correlation_filter(session: Session) -> None:
    first_id, second_id = seed_audit_events(session)
    service = AuditExplorerService(session)

    all_events = service.list_events()
    limited = service.list_events(limit=2)
    filtered = service.list_events(correlation_id="approval-1")

    assert [event.id for event in all_events][:2] == [first_id, second_id]
    assert [event.id for event in limited] == [first_id, second_id]
    assert [event.correlation_id for event in filtered] == ["approval-1", "approval-1"]
    assert filtered[0].payload["submit_performed"] is False


def test_chain_verification_reports_valid_chain(session: Session) -> None:
    seed_audit_events(session)

    verification = AuditExplorerService(session).verify_chain()

    assert verification.valid is True
    assert verification.event_count == 3
    assert verification.latest_hash is not None
    assert verification.invalid_event_id is None


def test_chain_verification_detects_direct_database_tampering(session: Session) -> None:
    first_id, _ = seed_audit_events(session)
    tampered = session.get(AuditEvent, first_id)
    assert tampered is not None
    tampered.event_type = "approval.request.tampered"
    session.commit()

    verification = AuditExplorerService(session).verify_chain()

    assert verification.valid is False
    assert verification.invalid_event_id == first_id
    assert "hash mismatch" in verification.reason


def test_audit_explorer_is_read_only(session: Session) -> None:
    seed_audit_events(session)
    service = AuditExplorerService(session)

    before = len(session.scalars(select(AuditEvent)).all())
    service.list_events()
    service.get_summary()
    service.verify_chain()
    after = len(session.scalars(select(AuditEvent)).all())

    assert before == after == 3


def test_audit_endpoints_return_typed_schemas(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, database_url = client_and_database_url
    with Session(get_engine(database_url)) as db_session:
        seed_audit_events(db_session)

    list_response = client.get("/audit/events?correlation_id=approval-1&limit=1")
    summary_response = client.get("/audit/summary")
    verify_response = client.get("/audit/verify-chain")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["correlation_id"] == "approval-1"
    assert summary_response.status_code == 200
    summary = AuditExplorerSummary.model_validate(summary_response.json())
    assert summary.total_events == 3
    assert summary.chain.valid is True
    assert verify_response.status_code == 200
    assert AuditChainVerification.model_validate(verify_response.json()).valid is True
