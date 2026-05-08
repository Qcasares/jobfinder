from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, DiscoveryQueueRun, ManualHandoffRecord
from app.schemas.observability import ObservabilitySummaryRead
from app.services.audit_explorer import AuditExplorerService


class ObservabilityService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_summary(self) -> ObservabilitySummaryRead:
        chain = AuditExplorerService(self._session).verify_chain()
        total_audit_events = self._count(select(func.count()).select_from(AuditEvent))
        error_events = self._count(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.event_type.like("%failed%"))
        )
        open_handoffs = self._count(
            select(func.count())
            .select_from(ManualHandoffRecord)
            .where(ManualHandoffRecord.status == "open")
        )
        queued_runs = self._count(
            select(func.count())
            .select_from(DiscoveryQueueRun)
            .where(DiscoveryQueueRun.status.in_(["queued", "rate_limited", "running"]))
        )
        failed_runs = self._count(
            select(func.count())
            .select_from(DiscoveryQueueRun)
            .where(DiscoveryQueueRun.status == "failed")
        )
        return ObservabilitySummaryRead(
            total_audit_events=total_audit_events,
            error_events=error_events,
            open_manual_handoffs=open_handoffs,
            queued_discovery_runs=queued_runs,
            failed_discovery_runs=failed_runs,
            audit_chain_valid=chain.valid,
            latest_audit_hash=chain.latest_hash,
        )

    def _count(self, statement: Select[tuple[int]]) -> int:
        value = self._session.scalar(statement)
        return int(value or 0)
