from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEvent, DiscoveryQueueRun, ManualHandoffRecord
from app.schemas.observability import ObservabilityAlertRead, ObservabilitySummaryRead
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
        alerts = _build_alerts(
            audit_chain_valid=chain.valid,
            error_events=error_events,
            open_handoffs=open_handoffs,
            failed_runs=failed_runs,
        )
        return ObservabilitySummaryRead(
            total_audit_events=total_audit_events,
            error_events=error_events,
            open_manual_handoffs=open_handoffs,
            queued_discovery_runs=queued_runs,
            failed_discovery_runs=failed_runs,
            audit_chain_valid=chain.valid,
            latest_audit_hash=chain.latest_hash,
            active_alerts=alerts,
        )

    def _count(self, statement: Select[tuple[int]]) -> int:
        value = self._session.scalar(statement)
        return int(value or 0)


def _build_alerts(
    *,
    audit_chain_valid: bool,
    error_events: int,
    open_handoffs: int,
    failed_runs: int,
) -> list[ObservabilityAlertRead]:
    alerts: list[ObservabilityAlertRead] = []
    if not audit_chain_valid:
        alerts.append(
            ObservabilityAlertRead(
                id="audit-chain-invalid",
                severity="critical",
                title="Audit chain invalid",
                detail="The hash-chained audit log failed verification.",
                recommended_action="Pause production mutations and investigate audit integrity.",
            )
        )
    if error_events:
        alerts.append(
            ObservabilityAlertRead(
                id="audit-error-events",
                severity="warning",
                title="Failure events recorded",
                detail=f"{error_events} failure audit event(s) are present.",
                recommended_action="Review recent audit events before processing more queued work.",
            )
        )
    if failed_runs:
        alerts.append(
            ObservabilityAlertRead(
                id="failed-discovery-runs",
                severity="warning",
                title="Discovery queue failures",
                detail=f"{failed_runs} queued discovery run(s) failed.",
                recommended_action="Inspect run history and source policy before retrying.",
            )
        )
    if open_handoffs:
        alerts.append(
            ObservabilityAlertRead(
                id="open-manual-handoffs",
                severity="info",
                title="Manual handoffs open",
                detail=f"{open_handoffs} handoff record(s) need operator review.",
                recommended_action="Resolve manually; do not bypass access controls.",
            )
        )
    return alerts
