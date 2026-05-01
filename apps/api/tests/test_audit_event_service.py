from typing import cast

import pytest
from sqlalchemy import Table, create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import AuditEvent
from app.schemas.audit import ActorType, JsonValue
from app.services.audit import AppendOnlyAuditLogError, AuditEventService


def test_audit_events_hash_chain_in_creation_order() -> None:
    service = AuditEventService()

    first = service.create_event(
        event_type="policy.decision",
        actor_type=ActorType.SYSTEM,
        actor_id="policy-service",
        correlation_id="corr-1",
        payload={"source_id": "greenhouse", "allowed": True},
    )
    second = service.create_event(
        event_type="application.approval_requested",
        actor_type=ActorType.USER,
        actor_id="user-1",
        correlation_id="corr-1",
        payload={"job_id": "job-1"},
    )

    assert first.previous_hash is None
    assert second.previous_hash == first.event_hash
    assert first.event_hash != second.event_hash
    assert len(first.event_hash) == 64
    assert service.list_events() == [first, second]


def test_audit_events_are_append_only() -> None:
    service = AuditEventService()
    event = service.create_event(
        event_type="policy.decision",
        actor_type=ActorType.SYSTEM,
        actor_id="policy-service",
        correlation_id="corr-1",
        payload={"source_id": "unknown", "allowed": False},
    )

    with pytest.raises(AppendOnlyAuditLogError):
        service.update_event(event.id, payload={"allowed": True})

    with pytest.raises(AppendOnlyAuditLogError):
        service.delete_event(event.id)


def test_audit_event_payload_is_snapshot_before_hashing() -> None:
    service = AuditEventService()
    flags: dict[str, JsonValue] = {"allowed": True}
    payload: dict[str, JsonValue] = {"source_id": "greenhouse", "flags": flags}

    event = service.create_event(
        event_type="policy.decision",
        actor_type=ActorType.SYSTEM,
        actor_id="policy-service",
        correlation_id="corr-1",
        payload=payload,
    )

    payload["source_id"] = "mutated"
    flags["allowed"] = False

    stored = service.list_events()[0]
    assert event.payload["source_id"] == "greenhouse"
    stored_flags = cast(dict[str, JsonValue], stored.payload["flags"])
    assert stored_flags["allowed"] is True

    with pytest.raises(TypeError):
        stored.payload["source_id"] = "mutated-again"


def test_audit_events_can_be_persisted_and_reloaded_from_database() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[cast(Table, AuditEvent.__table__)])

    with Session(engine) as session:
        service = AuditEventService(session=session)
        first = service.create_event(
            event_type="policy.decision",
            actor_type=ActorType.SYSTEM,
            actor_id="policy-service",
            correlation_id="corr-1",
            payload={"source_id": "greenhouse"},
        )
        second = service.create_event(
            event_type="approval.requested",
            actor_type=ActorType.USER,
            actor_id="user-1",
            correlation_id="corr-1",
            payload={"job_id": "job-1"},
        )
        session.commit()

    with Session(engine) as session:
        rows = session.scalars(select(AuditEvent).order_by(AuditEvent.created_at)).all()
        reloaded = AuditEventService(session=session).list_events()

    assert len(rows) == 2
    assert rows[0].event_hash == first.event_hash
    assert rows[1].previous_hash == first.event_hash
    assert reloaded[1].event_hash == second.event_hash
