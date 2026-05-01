from __future__ import annotations

import re
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApprovalRequest, JobPosting, User
from app.schemas.approvals import (
    ApprovalDecisionCreate,
    ApprovalRequestCreate,
    ApprovalRequestRead,
    ApprovalRequestSummary,
    ApprovalSafety,
)
from app.schemas.audit import ActorType
from app.schemas.review import ReviewQueueItem
from app.services.audit import AuditEventService
from app.services.review_queue import ReviewQueueService


class ReviewItemNotFoundError(ValueError):
    """Raised when an approval request references an unknown synthetic review item."""


class ApprovalRequestNotFoundError(ValueError):
    """Raised when a manual approval request id does not exist."""


class InvalidApprovalTransitionError(ValueError):
    """Raised when a manual approval request moves out of the constrained state machine."""


class ApprovalRequestService:
    def __init__(
        self,
        session: Session,
        *,
        audit_service: AuditEventService | None = None,
        review_queue: ReviewQueueService | None = None,
    ) -> None:
        self._session = session
        self._audit_service = audit_service or AuditEventService(session=session)
        self._review_queue = review_queue or ReviewQueueService()

    def create_request(self, request: ApprovalRequestCreate) -> ApprovalRequestRead:
        review_item = self._find_review_item(request.review_item_id)
        if review_item is None:
            raise ReviewItemNotFoundError(f"review item {request.review_item_id} was not found")

        synthetic_user = self._get_or_create_user(request.requester_id)
        job_posting = self._get_or_create_job_posting(review_item)
        approval = ApprovalRequest(
            id=str(uuid4()),
            review_item_id=review_item.id,
            job_posting_id=job_posting.id,
            user_id=synthetic_user.id,
            requester_id=request.requester_id,
            reviewer_id=None,
            request_type=request.request_type,
            status="pending",
            reason=request.reason,
            requested_at=datetime.now(UTC),
            resolved_at=None,
        )
        self._session.add(approval)
        self._session.flush()
        self._audit_service.create_event(
            event_type="approval.request.created",
            actor_type=ActorType.USER,
            actor_id=request.requester_id,
            correlation_id=approval.id,
            payload={
                "approval_request_id": approval.id,
                "review_item_id": review_item.id,
                "job_posting_id": job_posting.id,
                "request_type": request.request_type,
                "submit_performed": False,
                "autofill_performed": False,
                "application_created": False,
            },
        )
        return self._read(approval)

    def list_requests(self) -> list[ApprovalRequestRead]:
        rows = self._session.scalars(
            select(ApprovalRequest).order_by(ApprovalRequest.requested_at, ApprovalRequest.id)
        ).all()
        return [self._read(row) for row in rows]

    def get_summary(self) -> ApprovalRequestSummary:
        requests = self.list_requests()
        return ApprovalRequestSummary(
            total=len(requests),
            pending=sum(1 for request in requests if request.status == "pending"),
            approved=sum(1 for request in requests if request.status == "approved"),
            rejected=sum(1 for request in requests if request.status == "rejected"),
            needs_changes=sum(1 for request in requests if request.status == "needs_changes"),
        )

    def record_decision(
        self,
        request_id: str,
        decision: ApprovalDecisionCreate,
    ) -> ApprovalRequestRead:
        approval = self._session.get(ApprovalRequest, request_id)
        if approval is None:
            raise ApprovalRequestNotFoundError(f"approval request {request_id} was not found")
        if approval.status != "pending":
            raise InvalidApprovalTransitionError(
                f"approval request {request_id} is already {approval.status}"
            )

        approval.status = decision.decision
        approval.reviewer_id = decision.reviewer_id
        approval.reason = decision.reason
        approval.resolved_at = datetime.now(UTC)
        self._session.flush()
        self._audit_service.create_event(
            event_type="approval.request.decided",
            actor_type=ActorType.USER,
            actor_id=decision.reviewer_id,
            correlation_id=approval.id,
            payload={
                "approval_request_id": approval.id,
                "review_item_id": approval.review_item_id or "",
                "decision": decision.decision,
                "reason": decision.reason,
                "submit_performed": False,
                "autofill_performed": False,
                "application_created": False,
            },
        )
        return self._read(approval)

    def _find_review_item(self, review_item_id: str) -> ReviewQueueItem | None:
        return next(
            (item for item in self._review_queue.list_items() if item.id == review_item_id),
            None,
        )

    def _get_or_create_user(self, actor_id: str) -> User:
        user_id = str(uuid5(NAMESPACE_URL, f"jobfinder:local-user:{actor_id}"))
        user = self._session.get(User, user_id)
        if user is not None:
            return user
        user = User(
            id=user_id,
            email=f"{_slug(actor_id)}@local.jobfinder.synthetic",
            display_name=actor_id,
        )
        self._session.add(user)
        self._session.flush()
        return user

    def _get_or_create_job_posting(self, review_item: ReviewQueueItem) -> JobPosting:
        job_id = str(uuid5(NAMESPACE_URL, f"jobfinder:review-item:{review_item.id}"))
        job_posting = self._session.get(JobPosting, job_id)
        if job_posting is not None:
            return job_posting
        job_posting = JobPosting(
            id=job_id,
            canonical_url=review_item.source_url,
            title=review_item.title or "Unknown title",
            company=review_item.company or "Unknown company",
            remote_type=review_item.remote_type,
            employment_type=review_item.employment_type,
            salary_min=review_item.salary_min,
            salary_max=review_item.salary_max,
            salary_currency=review_item.salary_currency,
            posted_date=_date_to_datetime(review_item.posted_date),
            valid_through=_date_to_datetime(review_item.valid_through),
            extraction_confidence=Decimal(str(review_item.extraction_confidence)),
        )
        self._session.add(job_posting)
        self._session.flush()
        return job_posting

    @staticmethod
    def _read(approval: ApprovalRequest) -> ApprovalRequestRead:
        return ApprovalRequestRead(
            id=approval.id,
            review_item_id=approval.review_item_id or "",
            job_posting_id=approval.job_posting_id,
            requester_id=approval.requester_id or approval.user_id,
            reviewer_id=approval.reviewer_id,
            request_type="manual_review",
            status=approval.status,
            reason=approval.reason,
            requested_at=approval.requested_at,
            resolved_at=approval.resolved_at,
            safety=ApprovalSafety(
                submit_performed=False,
                autofill_performed=False,
                application_created=False,
            ),
        )


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized[:80] or "local-reviewer"
