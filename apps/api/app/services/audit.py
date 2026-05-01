from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import AuditEvent
from app.schemas.audit import ActorType, AuditEventRead, JsonValue, thaw_json


class AppendOnlyAuditLogError(RuntimeError):
    """Raised when callers try to mutate the append-only audit log."""


class AuditEventService:
    def __init__(self, session: Session | None = None, schema_version: int | None = None) -> None:
        self._events: list[AuditEventRead] = []
        self._session = session
        self._schema_version = schema_version or get_settings().audit_schema_version

    def create_event(
        self,
        *,
        event_type: str,
        actor_type: ActorType,
        actor_id: str,
        correlation_id: str,
        payload: dict[str, JsonValue] | None = None,
    ) -> AuditEventRead:
        event_id = str(uuid4())
        created_at = datetime.now(UTC)
        previous_hash = self._latest_hash()
        event_payload = self._clone_payload(payload or {})
        event_hash = self._hash_event(
            event_id=event_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            schema_version=self._schema_version,
            previous_hash=previous_hash,
            payload=event_payload,
            created_at=created_at,
        )
        if self._session is not None:
            self._session.add(
                AuditEvent(
                    id=event_id,
                    event_type=event_type,
                    actor_type=actor_type.value,
                    actor_id=actor_id,
                    correlation_id=correlation_id,
                    schema_version=self._schema_version,
                    previous_hash=previous_hash,
                    event_hash=event_hash,
                    payload=event_payload,
                    created_at=created_at,
                )
            )
            self._session.flush()

        event = AuditEventRead(
            id=event_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            schema_version=self._schema_version,
            previous_hash=previous_hash,
            event_hash=event_hash,
            payload=event_payload,
            created_at=created_at,
        )
        self._events.append(event)
        return event

    def list_events(self) -> list[AuditEventRead]:
        if self._session is not None:
            rows = self._session.scalars(
                select(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id)
            ).all()
            return [self._from_model(row) for row in rows]
        return list(self._events)

    def update_event(self, event_id: str, **_: object) -> None:
        raise AppendOnlyAuditLogError(f"audit event {event_id} cannot be updated")

    def delete_event(self, event_id: str) -> None:
        raise AppendOnlyAuditLogError(f"audit event {event_id} cannot be deleted")

    @staticmethod
    def _hash_event(
        *,
        event_id: str,
        event_type: str,
        actor_type: ActorType,
        actor_id: str,
        correlation_id: str,
        schema_version: int,
        previous_hash: str | None,
        payload: dict[str, JsonValue],
        created_at: datetime,
    ) -> str:
        canonical = json.dumps(
            {
                "id": event_id,
                "event_type": event_type,
                "actor_type": actor_type.value,
                "actor_id": actor_id,
                "correlation_id": correlation_id,
                "schema_version": schema_version,
                "previous_hash": previous_hash,
                "payload": payload,
                "created_at": created_at.isoformat(),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _latest_hash(self) -> str | None:
        if self._session is None:
            return self._events[-1].event_hash if self._events else None

        latest_hash = self._session.scalar(
            select(AuditEvent.event_hash).order_by(
                AuditEvent.created_at.desc(), AuditEvent.id.desc()
            )
        )
        return latest_hash

    @staticmethod
    def _clone_payload(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return cast(dict[str, JsonValue], json.loads(json.dumps(payload, sort_keys=True)))

    @staticmethod
    def _from_model(row: AuditEvent) -> AuditEventRead:
        return AuditEventRead(
            id=row.id,
            event_type=row.event_type,
            actor_type=ActorType(row.actor_type),
            actor_id=row.actor_id,
            correlation_id=row.correlation_id,
            schema_version=row.schema_version,
            previous_hash=row.previous_hash,
            event_hash=row.event_hash,
            payload=thaw_json(row.payload),
            created_at=row.created_at,
        )
