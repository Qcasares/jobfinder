from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import DiscoveryQueueRun
from app.schemas.audit import ActorType, JsonValue
from app.schemas.discovery_queue import DiscoveryQueueRunCreate, DiscoveryQueueRunRead
from app.schemas.live_discovery import LiveDiscoveryRequest, LiveSearchDiscoveryRequest
from app.services.audit import AuditEventService
from app.services.domain import normalize_domain
from app.services.live_discovery import LiveDiscoveryService

RATE_LIMIT_SECONDS = 60


class DiscoveryQueueNotFoundError(ValueError):
    """Raised when a queued discovery run id does not exist."""


class DiscoveryQueueService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings,
        live_discovery_service: LiveDiscoveryService,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._live_discovery_service = live_discovery_service
        self._audit_service = audit_service or AuditEventService(session=session)

    def enqueue(self, request: DiscoveryQueueRunCreate) -> DiscoveryQueueRunRead:
        url = str(request.url)
        source_domain = _source_domain(url, request.source_domain)
        duplicate = self._session.scalar(
            select(DiscoveryQueueRun)
            .where(
                DiscoveryQueueRun.url == url,
                DiscoveryQueueRun.source_domain == source_domain,
                DiscoveryQueueRun.status.in_(["queued", "rate_limited", "running"]),
            )
            .order_by(DiscoveryQueueRun.created_at.desc())
            .limit(1)
        )
        if duplicate is not None:
            return _read(duplicate)

        now = datetime.now(UTC)
        rate_limit_after = self._rate_limit_after(source_domain, now)
        row = DiscoveryQueueRun(
            id=str(uuid4()),
            mode=request.mode,
            url=url,
            source_domain=source_domain,
            requested_by=request.requested_by,
            status="rate_limited" if rate_limit_after is not None else "queued",
            max_results=request.max_results,
            attempts=0,
            max_attempts=request.max_attempts,
            rate_limit_after=rate_limit_after,
            live_run_id=None,
            manual_handoff_id=None,
            failure_reason=None,
            failure_detail=None,
            discovered_urls=[],
            review_item_ids=[],
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.flush()
        self._audit(
            "discovery_queue.enqueued",
            row.id,
            {
                "queue_run_id": row.id,
                "mode": row.mode,
                "source_domain": row.source_domain,
                "url": row.url,
                "status": row.status,
                "rate_limited": row.rate_limit_after is not None,
            },
        )
        return _read(row)

    def list_runs(self, *, limit: int = 25) -> list[DiscoveryQueueRunRead]:
        rows = self._session.scalars(
            select(DiscoveryQueueRun)
            .order_by(DiscoveryQueueRun.created_at.desc(), DiscoveryQueueRun.id)
            .limit(limit)
        ).all()
        return [_read(row) for row in rows]

    def process_run(self, run_id: str) -> DiscoveryQueueRunRead:
        row = self._session.get(DiscoveryQueueRun, run_id)
        if row is None:
            raise DiscoveryQueueNotFoundError(f"discovery queue run {run_id} was not found")
        now = datetime.now(UTC)
        if row.rate_limit_after is not None and row.rate_limit_after > now:
            row.status = "rate_limited"
            self._session.flush()
            return _read(row)
        if row.status in {"completed", "manual_handoff_required"}:
            return _read(row)
        if row.attempts >= row.max_attempts:
            row.status = "failed"
            row.failure_reason = "max_attempts_exceeded"
            row.failure_detail = "Queued discovery exceeded its retry budget."
            self._session.flush()
            return _read(row)

        row.status = "running"
        row.attempts += 1
        self._session.flush()
        if row.mode == "search":
            live_run = self._live_discovery_service.run_search_discovery(
                LiveSearchDiscoveryRequest(
                    url=row.url,
                    source_domain=row.source_domain,
                    requested_by=row.requested_by,
                    max_results=row.max_results,
                ),
                session=self._session,
            )
        else:
            live_run = self._live_discovery_service.run(
                LiveDiscoveryRequest(
                    url=row.url,
                    source_domain=row.source_domain,
                    requested_by=row.requested_by,
                ),
                session=self._session,
            )

        row.live_run_id = live_run.id
        row.manual_handoff_id = live_run.manual_handoff_id
        row.discovered_urls = list(live_run.discovered_urls)
        row.review_item_ids = list(live_run.review_item_ids)
        if row.mode == "search" and live_run.discovered_urls:
            self._enqueue_discovered_job_runs(row, list(live_run.discovered_urls))
        if live_run.manual_handoff_id:
            row.status = "manual_handoff_required"
        elif live_run.status.value in {"extracted", "discovered"}:
            row.status = "completed"
        else:
            row.status = "failed" if row.attempts >= row.max_attempts else "queued"
        row.failure_reason = live_run.failure.reason if live_run.failure else None
        row.failure_detail = live_run.failure.detail if live_run.failure else None
        row.rate_limit_after = datetime.now(UTC) + timedelta(seconds=RATE_LIMIT_SECONDS)
        self._session.flush()
        self._audit(
            "discovery_queue.processed",
            row.id,
            {
                "queue_run_id": row.id,
                "live_run_id": row.live_run_id or "",
                "status": row.status,
                "attempts": row.attempts,
                "manual_handoff_id": row.manual_handoff_id or "",
            },
        )
        return _read(row)

    def _enqueue_discovered_job_runs(
        self,
        parent: DiscoveryQueueRun,
        discovered_urls: list[str],
    ) -> None:
        now = datetime.now(UTC)
        for url in discovered_urls:
            existing = self._session.scalar(
                select(DiscoveryQueueRun)
                .where(
                    DiscoveryQueueRun.url == url,
                    DiscoveryQueueRun.source_domain == parent.source_domain,
                    DiscoveryQueueRun.mode == "job",
                    DiscoveryQueueRun.status.in_(
                        [
                            "queued",
                            "rate_limited",
                            "running",
                            "completed",
                            "manual_handoff_required",
                        ]
                    ),
                )
                .limit(1)
            )
            if existing is not None:
                continue
            rate_limit_after = self._rate_limit_after(parent.source_domain, now)
            row = DiscoveryQueueRun(
                id=str(uuid4()),
                mode="job",
                url=url,
                source_domain=parent.source_domain,
                requested_by=parent.requested_by,
                status="rate_limited" if rate_limit_after is not None else "queued",
                max_results=1,
                attempts=0,
                max_attempts=parent.max_attempts,
                rate_limit_after=rate_limit_after,
                live_run_id=None,
                manual_handoff_id=None,
                failure_reason=None,
                failure_detail=None,
                discovered_urls=[],
                review_item_ids=[],
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
            self._audit(
                "discovery_queue.enqueued",
                row.id,
                {
                    "queue_run_id": row.id,
                    "parent_queue_run_id": parent.id,
                    "mode": row.mode,
                    "source_domain": row.source_domain,
                    "url": row.url,
                    "status": row.status,
                    "rate_limited": row.rate_limit_after is not None,
                },
            )
        self._session.flush()

    def _rate_limit_after(self, source_domain: str, now: datetime) -> datetime | None:
        latest = self._session.scalar(
            select(DiscoveryQueueRun)
            .where(DiscoveryQueueRun.source_domain == source_domain)
            .order_by(DiscoveryQueueRun.updated_at.desc())
            .limit(1)
        )
        if latest is None:
            return None
        latest_time = latest.updated_at
        if latest_time.tzinfo is None:
            latest_time = latest_time.replace(tzinfo=UTC)
        allowed_after = latest_time + timedelta(seconds=RATE_LIMIT_SECONDS)
        return allowed_after if allowed_after > now else None

    def _audit(self, event_type: str, correlation_id: str, payload: dict[str, JsonValue]) -> None:
        self._audit_service.create_event(
            event_type=event_type,
            actor_type=ActorType.WORKER,
            actor_id="discovery-queue-service",
            correlation_id=correlation_id,
            payload=payload,
        )


def _source_domain(url: str, source_domain: str | None) -> str:
    if source_domain:
        return normalize_domain(source_domain)
    parsed = urlparse(url)
    return normalize_domain(parsed.hostname or "")


def _read(row: DiscoveryQueueRun) -> DiscoveryQueueRunRead:
    return DiscoveryQueueRunRead(
        id=row.id,
        mode=row.mode,
        url=row.url,
        source_domain=row.source_domain,
        requested_by=row.requested_by,
        status=row.status,
        max_results=row.max_results,
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        rate_limit_after=row.rate_limit_after,
        live_run_id=row.live_run_id,
        manual_handoff_id=row.manual_handoff_id,
        failure_reason=row.failure_reason,
        failure_detail=row.failure_detail,
        discovered_urls=row.discovered_urls,
        review_item_ids=row.review_item_ids,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
