from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AutofillPacket, DraftingRun
from app.schemas.audit import ActorType
from app.schemas.autofill import (
    AutofillPacketFailure,
    AutofillPacketField,
    AutofillPacketRead,
    AutofillPacketRequest,
    AutofillPacketSafety,
)
from app.schemas.policy import PolicyAction
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.source_registry import SourceRegistryService


class AutofillPacketService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._audit_service = audit_service or AuditEventService(session=session)

    def create_packet(self, request: AutofillPacketRequest) -> AutofillPacketRead:
        packet_id = str(uuid4())
        target_url = str(request.target_url)
        self._audit_service.create_event(
            event_type="autofill.packet.requested",
            actor_type=ActorType.USER,
            actor_id=request.requested_by,
            correlation_id=packet_id,
            payload={
                "drafting_run_id": request.drafting_run_id,
                "target_domain": _domain_from_url(target_url),
                "dry_run": True,
                "browser_automation_performed": False,
                "autofill_performed": False,
                "submit_performed": False,
            },
        )

        drafting_run = self._session.get(DraftingRun, request.drafting_run_id)
        if drafting_run is None:
            return self._deny(
                packet_id,
                request,
                reason="drafting_run_not_found",
                detail=f"Drafting run {request.drafting_run_id} was not found.",
            )
        if not self._settings.autofill_packets_enabled:
            return self._deny(
                packet_id,
                request,
                reason="autofill_packets_disabled",
                detail="Autofill packet preparation is disabled by runtime configuration.",
            )
        if drafting_run.status != "review_required" or not drafting_run.approval_required:
            return self._deny(
                packet_id,
                request,
                reason="draft_not_reviewable",
                detail="Drafting run is not ready for autofill packet review.",
            )

        target_domain = _domain_from_url(target_url)
        decision = SourceRegistryService(self._session).evaluate_action(
            domain=target_domain,
            action=PolicyAction.AUTOFILL,
        )
        if not decision.allowed:
            return self._deny(
                packet_id,
                request,
                reason="source_policy_denied",
                detail=decision.reason,
            )

        fields = [
            {
                "field_key": "cover_letter",
                "value_preview": drafting_run.draft_text or "",
                "provenance": "drafting_run",
            }
        ]
        row = AutofillPacket(
            id=packet_id,
            drafting_run_id=request.drafting_run_id,
            target_url=target_url,
            requested_by=request.requested_by,
            status="review_required",
            fields=fields,
            approval_required=True,
            failure_reason=None,
            failure_detail=None,
        )
        self._session.add(row)
        self._session.flush()
        self._audit_service.create_event(
            event_type="autofill.packet.review_required",
            actor_type=ActorType.SYSTEM,
            actor_id="autofill-packet-service",
            correlation_id=packet_id,
            payload={
                "autofill_packet_id": row.id,
                "drafting_run_id": row.drafting_run_id,
                "target_domain": target_domain,
                "field_count": len(fields),
                "approval_required": True,
                "dry_run": True,
                "browser_automation_performed": False,
                "autofill_performed": False,
                "submit_performed": False,
            },
        )
        return _read_packet(row)

    def _deny(
        self,
        packet_id: str,
        request: AutofillPacketRequest,
        *,
        reason: str,
        detail: str,
    ) -> AutofillPacketRead:
        row = AutofillPacket(
            id=packet_id,
            drafting_run_id=request.drafting_run_id,
            target_url=str(request.target_url),
            requested_by=request.requested_by,
            status="denied",
            fields=[],
            approval_required=True,
            failure_reason=reason,
            failure_detail=detail,
        )
        self._session.add(row)
        self._session.flush()
        return _read_packet(row)


def _read_packet(row: AutofillPacket) -> AutofillPacketRead:
    failure = (
        AutofillPacketFailure(reason=row.failure_reason, detail=row.failure_detail)
        if row.failure_reason and row.failure_detail
        else None
    )
    return AutofillPacketRead(
        id=row.id,
        drafting_run_id=row.drafting_run_id,
        target_url=row.target_url,
        requested_by=row.requested_by,
        status=row.status,
        fields=tuple(AutofillPacketField.model_validate(field) for field in row.fields),
        approval_required=row.approval_required,
        safety=AutofillPacketSafety(),
        failure=failure,
        created_at=row.created_at or datetime.now(UTC),
    )


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return normalize_domain(parsed.netloc)
