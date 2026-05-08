from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import DiscoveryQueueRun, ManualHandoffRecord
from app.db.session import get_engine
from app.schemas.audit import ActorType
from app.services.audit import AuditEventService
from app.services.observability import ObservabilityService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'observability.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_observability_summary_reports_no_alerts_for_clean_state(session: Session) -> None:
    AuditEventService(session=session).create_event(
        event_type="source.policy.checked",
        actor_type=ActorType.SYSTEM,
        actor_id="test",
        correlation_id="clean",
        payload={"allowed": True},
    )

    summary = ObservabilityService(session).get_summary()

    assert summary.audit_chain_valid is True
    assert summary.total_audit_events == 1
    assert summary.active_alerts == []


def test_observability_summary_reports_actionable_alerts(session: Session) -> None:
    AuditEventService(session=session).create_event(
        event_type="discovery_queue.failed",
        actor_type=ActorType.SYSTEM,
        actor_id="test",
        correlation_id="failed",
        payload={"failure_reason": "source_policy_denied"},
    )
    session.add(
        DiscoveryQueueRun(
            id="queue-run-1",
            mode="job",
            url="https://careers.example.test/jobs/platform",
            source_domain="careers.example.test",
            requested_by="operator",
            status="failed",
            failure_reason="source_policy_denied",
        )
    )
    session.add(
        ManualHandoffRecord(
            id="handoff-1",
            source_domain="careers.example.test",
            url="https://careers.example.test/jobs/platform",
            trigger_type="login_required",
            requested_by="operator",
            status="open",
            detection_detail="Login required.",
        )
    )
    session.flush()

    summary = ObservabilityService(session).get_summary()

    assert summary.error_events == 1
    assert summary.failed_discovery_runs == 1
    assert summary.open_manual_handoffs == 1
    assert [alert.id for alert in summary.active_alerts] == [
        "audit-error-events",
        "failed-discovery-runs",
        "open-manual-handoffs",
    ]
