from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ManualHandoffRecord
from app.schemas.audit import ActorType
from app.schemas.manual_handoff import (
    ManualHandoffCreate,
    ManualHandoffRead,
    ManualHandoffResolveRequest,
    ManualHandoffStatus,
)
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain


class ManualHandoffNotFoundError(ValueError):
    """Raised when a handoff record id does not exist."""


class InvalidManualHandoffTransitionError(ValueError):
    """Raised when a handoff record moves out of the constrained state machine."""


class ManualHandoffService:
    def __init__(
        self,
        session: Session,
        *,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._session = session
        self._audit_service = audit_service or AuditEventService(session=session)

    def create_record(self, request: ManualHandoffCreate) -> ManualHandoffRead:
        url = str(request.url)
        row = ManualHandoffRecord(
            id=str(uuid4()),
            source_domain=self._source_domain(url, request.source_domain),
            url=url,
            trigger_type=request.trigger_type,
            requested_by=request.requested_by,
            status="open",
            detection_detail=request.detection_detail,
            run_id=request.run_id,
            created_at=datetime.now(UTC),
            resolved_at=None,
            resolution_notes=None,
        )
        self._session.add(row)
        self._session.flush()
        self._audit_service.create_event(
            event_type="manual_handoff.created",
            actor_type=ActorType.WORKER,
            actor_id="manual-handoff-service",
            correlation_id=row.id,
            payload={
                "manual_handoff_id": row.id,
                "run_id": row.run_id or "",
                "source_domain": row.source_domain,
                "trigger_type": row.trigger_type,
                "requested_by": row.requested_by,
                "url": row.url,
                "detection_detail": row.detection_detail,
                "automation_stopped": True,
            },
        )
        return _read(row)

    def list_records(self, status: ManualHandoffStatus | None = None) -> list[ManualHandoffRead]:
        statement = select(ManualHandoffRecord)
        if status is not None:
            statement = statement.where(ManualHandoffRecord.status == status)
        rows = self._session.scalars(
            statement.order_by(ManualHandoffRecord.created_at, ManualHandoffRecord.id)
        ).all()
        return [_read(row) for row in rows]

    def resolve_record(
        self,
        record_id: str,
        request: ManualHandoffResolveRequest,
    ) -> ManualHandoffRead:
        row = self._session.get(ManualHandoffRecord, record_id)
        if row is None:
            raise ManualHandoffNotFoundError(f"manual handoff {record_id} was not found")
        if row.status != "open":
            raise InvalidManualHandoffTransitionError(
                f"manual handoff {record_id} is already {row.status}"
            )

        row.status = "resolved"
        row.resolved_at = datetime.now(UTC)
        row.resolution_notes = request.resolution_notes
        self._session.flush()
        self._audit_service.create_event(
            event_type="manual_handoff.resolved",
            actor_type=ActorType.USER,
            actor_id=request.reviewer_id,
            correlation_id=row.id,
            payload={
                "manual_handoff_id": row.id,
                "run_id": row.run_id or "",
                "source_domain": row.source_domain,
                "trigger_type": row.trigger_type,
                "resolution_notes": request.resolution_notes,
                "automation_stopped": True,
            },
        )
        return _read(row)

    @staticmethod
    def _source_domain(url: str, source_domain: str | None) -> str:
        if source_domain:
            return normalize_domain(source_domain)
        parsed = urlparse(url)
        return normalize_domain(parsed.hostname or "")


def _read(row: ManualHandoffRecord) -> ManualHandoffRead:
    return ManualHandoffRead(
        id=row.id,
        url=row.url,
        source_domain=row.source_domain,
        trigger_type=row.trigger_type,
        requested_by=row.requested_by,
        status=row.status,
        detection_detail=row.detection_detail,
        run_id=row.run_id,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
        resolution_notes=row.resolution_notes,
    )
