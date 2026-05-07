from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import AutofillPacket, FinalReviewPacket
from app.schemas.audit import ActorType
from app.schemas.final_review import (
    FinalReviewPacketFailure,
    FinalReviewPacketRead,
    FinalReviewPacketRequest,
    FinalReviewPacketSafety,
)
from app.schemas.policy import PolicyAction
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.source_registry import SourceRegistryService


class FinalReviewPacketService:
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

    def create_packet(self, request: FinalReviewPacketRequest) -> FinalReviewPacketRead:
        packet_id = str(uuid4())
        self._audit_service.create_event(
            event_type="final_review.packet.requested",
            actor_type=ActorType.USER,
            actor_id=request.requested_by,
            correlation_id=packet_id,
            payload={
                "autofill_packet_id": request.autofill_packet_id,
                "operator_confirmation": request.operator_confirmation,
                "submit_performed": False,
                "external_side_effect": False,
            },
        )
        autofill_packet = self._session.get(AutofillPacket, request.autofill_packet_id)
        if autofill_packet is None:
            return self._deny(
                packet_id,
                request,
                target_url="",
                reason="autofill_packet_not_found",
                detail=f"Autofill packet {request.autofill_packet_id} was not found.",
                submit_policy_checked=False,
            )
        if not self._settings.submission_packets_enabled:
            return self._deny(
                packet_id,
                request,
                target_url=autofill_packet.target_url,
                reason="submission_packets_disabled",
                detail="Final-review packet preparation is disabled by runtime configuration.",
                submit_policy_checked=False,
            )
        if autofill_packet.status != "review_required" or not autofill_packet.approval_required:
            return self._deny(
                packet_id,
                request,
                target_url=autofill_packet.target_url,
                reason="autofill_packet_not_reviewable",
                detail="Autofill packet is not ready for final review.",
                submit_policy_checked=False,
            )

        target_domain = _domain_from_url(autofill_packet.target_url)
        decision = SourceRegistryService(self._session).evaluate_action(
            domain=target_domain,
            action=PolicyAction.SUBMIT,
        )
        if not decision.allowed:
            return self._deny(
                packet_id,
                request,
                target_url=autofill_packet.target_url,
                reason="source_policy_denied",
                detail=decision.reason,
                submit_policy_checked=True,
            )

        row = FinalReviewPacket(
            id=packet_id,
            autofill_packet_id=request.autofill_packet_id,
            target_url=autofill_packet.target_url,
            requested_by=request.requested_by,
            operator_confirmation=request.operator_confirmation,
            rollback_notes=request.rollback_notes,
            status="review_required",
            approval_required=True,
            failure_reason=None,
            failure_detail=None,
        )
        self._session.add(row)
        self._session.flush()
        self._audit_service.create_event(
            event_type="final_review.packet.review_required",
            actor_type=ActorType.SYSTEM,
            actor_id="final-review-service",
            correlation_id=packet_id,
            payload={
                "final_review_packet_id": row.id,
                "autofill_packet_id": row.autofill_packet_id,
                "target_domain": target_domain,
                "operator_confirmation": row.operator_confirmation,
                "approval_required": True,
                "submit_policy_checked": True,
                "submit_performed": False,
                "external_side_effect": False,
            },
        )
        return _read_packet(
            row,
            final_confirmation_recorded=True,
            submit_policy_checked=True,
        )

    def _deny(
        self,
        packet_id: str,
        request: FinalReviewPacketRequest,
        *,
        target_url: str,
        reason: str,
        detail: str,
        submit_policy_checked: bool,
    ) -> FinalReviewPacketRead:
        row = FinalReviewPacket(
            id=packet_id,
            autofill_packet_id=request.autofill_packet_id,
            target_url=target_url,
            requested_by=request.requested_by,
            operator_confirmation=request.operator_confirmation,
            rollback_notes=request.rollback_notes,
            status="denied",
            approval_required=True,
            failure_reason=reason,
            failure_detail=detail,
        )
        self._session.add(row)
        self._session.flush()
        return _read_packet(
            row,
            final_confirmation_recorded=False,
            submit_policy_checked=submit_policy_checked,
        )


def _read_packet(
    row: FinalReviewPacket,
    *,
    final_confirmation_recorded: bool,
    submit_policy_checked: bool,
) -> FinalReviewPacketRead:
    failure = (
        FinalReviewPacketFailure(reason=row.failure_reason, detail=row.failure_detail)
        if row.failure_reason and row.failure_detail
        else None
    )
    return FinalReviewPacketRead(
        id=row.id,
        autofill_packet_id=row.autofill_packet_id,
        target_url=row.target_url,
        requested_by=row.requested_by,
        operator_confirmation=row.operator_confirmation,
        rollback_notes=row.rollback_notes,
        status=row.status,
        approval_required=row.approval_required,
        safety=FinalReviewPacketSafety(
            final_confirmation_recorded=final_confirmation_recorded,
            submit_policy_checked=submit_policy_checked,
        ),
        failure=failure,
        created_at=row.created_at or datetime.now(UTC),
    )


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return normalize_domain(parsed.netloc)
