from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent
from app.schemas.audit import ActorType, JsonValue, thaw_json
from app.schemas.audit_explorer import (
    AuditChainVerification,
    AuditExplorerEvent,
    AuditExplorerSummary,
)
from app.services.audit import AuditEventService


class AuditExplorerService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_events(
        self,
        *,
        limit: int | None = None,
        correlation_id: str | None = None,
    ) -> list[AuditExplorerEvent]:
        rows = self._session.scalars(
            _ordered_audit_query(limit=limit, correlation_id=correlation_id)
        ).all()
        return [_event_from_model(row) for row in rows]

    def get_summary(self) -> AuditExplorerSummary:
        rows = self._event_rows()
        chain = self.verify_chain()
        return AuditExplorerSummary(
            total_events=len(rows),
            counts_by_event_type=dict(Counter(row.event_type for row in rows)),
            counts_by_actor_type=dict(Counter(row.actor_type for row in rows)),
            latest_hash=chain.latest_hash,
            chain=chain,
        )

    def verify_chain(self) -> AuditChainVerification:
        rows = self._event_rows()
        expected_previous_hash: str | None = None
        latest_hash: str | None = None
        for index, row in enumerate(rows, start=1):
            if row.previous_hash != expected_previous_hash:
                return AuditChainVerification(
                    valid=False,
                    event_count=index,
                    latest_hash=latest_hash,
                    invalid_event_id=row.id,
                    reason="previous hash mismatch",
                )
            try:
                recomputed_hash = AuditEventService._hash_event(
                    event_id=row.id,
                    event_type=row.event_type,
                    actor_type=ActorType(row.actor_type),
                    actor_id=row.actor_id,
                    correlation_id=row.correlation_id,
                    schema_version=row.schema_version,
                    previous_hash=row.previous_hash,
                    payload=cast(dict[str, JsonValue], thaw_json(row.payload)),
                    created_at=_canonical_datetime(row.created_at),
                )
            except ValueError:
                return AuditChainVerification(
                    valid=False,
                    event_count=index,
                    latest_hash=latest_hash,
                    invalid_event_id=row.id,
                    reason="invalid actor type",
                )
            if recomputed_hash != row.event_hash:
                return AuditChainVerification(
                    valid=False,
                    event_count=index,
                    latest_hash=latest_hash,
                    invalid_event_id=row.id,
                    reason="hash mismatch",
                )
            expected_previous_hash = row.event_hash
            latest_hash = row.event_hash

        return AuditChainVerification(
            valid=True,
            event_count=len(rows),
            latest_hash=latest_hash,
            invalid_event_id=None,
            reason="valid hash chain" if rows else "empty audit log",
        )

    def _event_rows(self) -> list[AuditEvent]:
        return list(self._session.scalars(_ordered_audit_query()).all())


def _ordered_audit_query(
    *,
    limit: int | None = None,
    correlation_id: str | None = None,
) -> Select[tuple[AuditEvent]]:
    query = select(AuditEvent).order_by(AuditEvent.created_at, AuditEvent.id)
    if correlation_id is not None:
        query = query.where(AuditEvent.correlation_id == correlation_id)
    if limit is not None:
        query = query.limit(limit)
    return query


def _event_from_model(row: AuditEvent) -> AuditExplorerEvent:
    return AuditExplorerEvent(
        id=row.id,
        event_type=row.event_type,
        actor_type=ActorType(row.actor_type),
        actor_id=row.actor_id,
        correlation_id=row.correlation_id,
        schema_version=row.schema_version,
        previous_hash=row.previous_hash,
        event_hash=row.event_hash,
        payload=cast(dict[str, JsonValue], thaw_json(row.payload)),
        created_at=row.created_at,
    )


def _canonical_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
