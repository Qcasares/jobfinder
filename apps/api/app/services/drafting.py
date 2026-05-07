from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import CandidateEvidence, DraftingRun
from app.schemas.audit import ActorType
from app.schemas.drafting import (
    DraftingClaimMapping,
    DraftingFailure,
    DraftingRequest,
    DraftingRunRead,
    DraftingSafety,
)
from app.schemas.policy import PolicyAction
from app.schemas.review import ReviewQueueItem
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.review_queue import ReviewQueueService
from app.services.source_registry import SourceRegistryService


@dataclass(frozen=True)
class DraftingProviderResult:
    draft_text: str
    claim_mappings: list[dict[str, Any]]
    model: str


DraftingProvider = Callable[[object], DraftingProviderResult]


class DraftingSafetyError(ValueError):
    """Raised when drafting output cannot be grounded in approved evidence."""


class DraftingService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        provider: DraftingProvider | None = None,
        audit_service: AuditEventService | None = None,
        review_queue: ReviewQueueService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._provider = provider or _missing_provider
        self._audit_service = audit_service or AuditEventService(session=session)
        self._review_queue = review_queue or ReviewQueueService()

    def create_draft(self, request: DraftingRequest) -> DraftingRunRead:
        run_id = str(uuid4())
        self._audit_service.create_event(
            event_type="drafting.requested",
            actor_type=ActorType.USER,
            actor_id=request.requested_by,
            correlation_id=run_id,
            payload={
                "review_item_id": request.review_item_id,
                "evidence_count": len(request.evidence_ids),
                "autofill_performed": False,
                "submit_performed": False,
            },
        )
        review_item = self._find_review_item(request.review_item_id)
        if review_item is None:
            return self._complete(
                run_id,
                request,
                status="denied",
                failure_reason="review_item_not_found",
                failure_detail=f"Review item {request.review_item_id} was not found.",
                llm_called=False,
            )
        if not self._settings.llm_drafting_enabled:
            return self._complete(
                run_id,
                request,
                status="denied",
                failure_reason="llm_drafting_disabled",
                failure_detail="LLM-assisted drafting is disabled by runtime configuration.",
                llm_called=False,
            )

        source_domain = _domain_from_url(review_item.source_url)
        decision = SourceRegistryService(self._session).evaluate_action(
            domain=source_domain,
            action=PolicyAction.DRAFT,
        )
        if not decision.allowed:
            return self._complete(
                run_id,
                request,
                status="denied",
                failure_reason="source_policy_denied",
                failure_detail=decision.reason,
                llm_called=False,
            )

        evidence_ids = self._validated_evidence_ids(request.evidence_ids)
        result = self._provider(
            {
                "review_item_id": request.review_item_id,
                "job": {
                    "title": review_item.title,
                    "company": review_item.company,
                    "source_url": review_item.source_url,
                    "required_skills": list(review_item.required_skills),
                    "preferred_skills": list(review_item.preferred_skills),
                },
                "evidence_ids": evidence_ids,
            }
        )
        claim_mappings = _claim_mappings(result.claim_mappings)
        requested_ids = set(evidence_ids)
        has_unsupported_claim = any(
            not set(mapping.evidence_ids) or not set(mapping.evidence_ids) <= requested_ids
            for mapping in claim_mappings
        )
        if has_unsupported_claim:
            raise DraftingSafetyError("unsupported claim is missing requested evidence")

        row = DraftingRun(
            id=run_id,
            review_item_id=request.review_item_id,
            requested_by=request.requested_by,
            status="review_required",
            model=result.model,
            draft_text=result.draft_text,
            evidence_ids=evidence_ids,
            claim_mappings=[
                {"claim": mapping.claim, "evidence_ids": list(mapping.evidence_ids)}
                for mapping in claim_mappings
            ],
            approval_required=True,
            failure_reason=None,
            failure_detail=None,
        )
        self._session.add(row)
        self._session.flush()
        self._audit_service.create_event(
            event_type="drafting.review_required",
            actor_type=ActorType.SYSTEM,
            actor_id="drafting-service",
            correlation_id=run_id,
            payload={
                "drafting_run_id": row.id,
                "review_item_id": row.review_item_id,
                "model": row.model,
                "claim_count": len(claim_mappings),
                "evidence_count": len(evidence_ids),
                "approval_required": True,
                "autofill_performed": False,
                "submit_performed": False,
            },
        )
        return self._read(row, llm_called=True)

    def _complete(
        self,
        run_id: str,
        request: DraftingRequest,
        *,
        status: str,
        failure_reason: str,
        failure_detail: str,
        llm_called: bool,
    ) -> DraftingRunRead:
        row = DraftingRun(
            id=run_id,
            review_item_id=request.review_item_id,
            requested_by=request.requested_by,
            status=status,
            model=None,
            draft_text=None,
            evidence_ids=list(request.evidence_ids),
            claim_mappings=[],
            approval_required=True,
            failure_reason=failure_reason,
            failure_detail=failure_detail,
        )
        self._session.add(row)
        self._session.flush()
        return self._read(row, llm_called=llm_called)

    def _validated_evidence_ids(self, evidence_ids: list[str]) -> list[str]:
        rows = self._session.scalars(
            select(CandidateEvidence.id).where(CandidateEvidence.id.in_(evidence_ids))
        ).all()
        found = set(rows)
        missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in found]
        if missing:
            raise DraftingSafetyError("requested evidence was not found")
        return list(dict.fromkeys(evidence_ids))

    def _find_review_item(self, review_item_id: str) -> ReviewQueueItem | None:
        return next(
            (item for item in self._review_queue.list_items() if item.id == review_item_id),
            None,
        )

    @staticmethod
    def _read(row: DraftingRun, *, llm_called: bool) -> DraftingRunRead:
        failure = (
            DraftingFailure(reason=row.failure_reason, detail=row.failure_detail)
            if row.failure_reason and row.failure_detail
            else None
        )
        return DraftingRunRead(
            id=row.id,
            review_item_id=row.review_item_id,
            requested_by=row.requested_by,
            status=row.status,
            model=row.model,
            draft_text=row.draft_text,
            claim_mappings=_claim_mappings(row.claim_mappings),
            evidence_ids=tuple(row.evidence_ids),
            approval_required=row.approval_required,
            safety=DraftingSafety(llm_called=llm_called),
            failure=failure,
            created_at=row.created_at or datetime.now(UTC),
        )


def _missing_provider(_: object) -> DraftingProviderResult:
    raise DraftingSafetyError("drafting provider is not configured")


def _claim_mappings(values: list[dict[str, Any]]) -> tuple[DraftingClaimMapping, ...]:
    return tuple(
        DraftingClaimMapping(
            claim=str(value.get("claim", "")).strip(),
            evidence_ids=tuple(str(item) for item in value.get("evidence_ids", [])),
        )
        for value in values
    )


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return normalize_domain(parsed.netloc)
