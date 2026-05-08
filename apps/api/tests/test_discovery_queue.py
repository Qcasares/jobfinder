from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.schemas.discovery_queue import DiscoveryQueueRunCreate
from app.schemas.policy import PolicyAction
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.discovery_queue import DiscoveryQueueService
from app.services.live_discovery import FetchResult, LiveDiscoveryService
from app.services.source_registry import SourceRegistryService

JSON_LD_HTML = b"""
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"Queued Engineer",
"url":"https://careers.example.test/jobs/queued","identifier":{"value":"queued-1"},
"hiringOrganization":{"name":"Example Careers"},"jobLocationType":"TELECOMMUTE",
"applicantLocationRequirements":{"name":"Remote - UK"}}
</script></head></html>
"""


def test_discovery_queue_enqueues_processes_and_dedupes_runs() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    live = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        fetcher=lambda url: FetchResult(
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=JSON_LD_HTML,
        ),
    )
    service = DiscoveryQueueService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        live_discovery_service=live,
    )

    queued = service.enqueue(
        DiscoveryQueueRunCreate(
            url="https://careers.example.test/jobs/queued",
            source_domain="careers.example.test",
            mode="job",
            requested_by="operator-test",
        )
    )
    duplicate = service.enqueue(
        DiscoveryQueueRunCreate(
            url="https://careers.example.test/jobs/queued",
            source_domain="careers.example.test",
            mode="job",
            requested_by="operator-test",
        )
    )
    processed = service.process_run(queued.id)

    assert duplicate.id == queued.id
    assert processed.status == "completed"
    assert processed.attempts == 1
    assert processed.review_item_ids


def test_discovery_queue_rate_limits_same_source_runs() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    live = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True),
        fetcher=lambda url: FetchResult(
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=JSON_LD_HTML,
        ),
    )
    service = DiscoveryQueueService(
        session,
        settings=Settings(live_discovery_enabled=True),
        live_discovery_service=live,
    )

    first = service.enqueue(
        DiscoveryQueueRunCreate(url="https://careers.example.test/jobs/one")
    )
    processed = service.process_run(first.id)
    second = service.enqueue(
        DiscoveryQueueRunCreate(url="https://careers.example.test/jobs/two")
    )

    assert processed.status == "completed"
    assert second.status == "rate_limited"
    assert second.rate_limit_after is not None


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _allow_source(session: Session, domain: str) -> None:
    registry = SourceRegistryService(session)
    source = registry.upsert_source(domain=domain)
    registry.attach_source_policy(
        source_id=source.id,
        status="approved",
        reason="Synthetic approval for queued discovery.",
        allowed_actions=[PolicyAction.DISCOVER, PolicyAction.EXTRACT],
        denied_actions=[PolicyAction.DRAFT, PolicyAction.AUTOFILL, PolicyAction.SUBMIT],
        evidence=[
            SourcePolicyEvidenceCreate(
                evidence_type="manual_approval",
                url=f"https://{domain}/policy",
                excerpt="Synthetic test approval.",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        ],
    )
    session.commit()
