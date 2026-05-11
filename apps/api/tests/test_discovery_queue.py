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
from app.services.live_review_items import LiveReviewItemStore
from app.services.source_registry import SourceRegistryService

JSON_LD_HTML = b"""
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"JobPosting","title":"Queued Engineer",
"url":"https://careers.example.test/jobs/queued","identifier":{"value":"queued-1"},
"hiringOrganization":{"name":"Example Careers"},"jobLocationType":"TELECOMMUTE",
"applicantLocationRequirements":{"name":"Remote - UK"}}
</script></head></html>
"""

SEARCH_RESULTS_HTML = b"""
<html><body>
  <a href="/jobs/queued-one/101">Queued One</a>
  <a href="https://careers.example.test/jobs/queued-two/202#details">Queued Two</a>
  <a href="https://external.example.test/jobs/external">External</a>
  <a href="/about">About</a>
  <a href="/jobs/queued-one/101">Duplicate</a>
</body></html>
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
    assert [item.title for item in LiveReviewItemStore(session).list_items()] == [
        "Queued Engineer"
    ]


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


def test_discovery_queue_search_enqueues_discovered_job_runs() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    live = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        fetcher=lambda url: FetchResult(
            final_url=url,
            status_code=200,
            content_type="text/html",
            body=SEARCH_RESULTS_HTML,
        ),
    )
    service = DiscoveryQueueService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        live_discovery_service=live,
    )

    queued = service.enqueue(
        DiscoveryQueueRunCreate(
            url="https://careers.example.test/jobs/search?q=engineer",
            source_domain="careers.example.test",
            mode="search",
            requested_by="operator-test",
            max_results=5,
        )
    )
    processed = service.process_run(queued.id)
    runs = service.list_runs(limit=10)
    child_runs = [run for run in runs if run.mode == "job"]

    assert processed.status == "completed"
    assert processed.discovered_urls == [
        "https://careers.example.test/jobs/queued-one/101",
        "https://careers.example.test/jobs/queued-two/202",
    ]
    assert sorted(run.url for run in child_runs) == [
        "https://careers.example.test/jobs/queued-one/101",
        "https://careers.example.test/jobs/queued-two/202",
    ]
    assert all(run.status in {"queued", "rate_limited"} for run in child_runs)


def test_discovery_queue_processes_ready_batch_and_skips_future_rate_limits() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    _allow_source(session, "other.example.test")
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
    first = service.enqueue(DiscoveryQueueRunCreate(url="https://careers.example.test/jobs/one"))
    second = service.enqueue(DiscoveryQueueRunCreate(url="https://careers.example.test/jobs/two"))
    third = service.enqueue(DiscoveryQueueRunCreate(url="https://other.example.test/jobs/three"))

    batch = service.process_ready_runs(limit=5)

    refreshed = {run.id: run for run in service.list_runs(limit=10)}
    assert batch.requested_limit == 5
    assert batch.processed_count == 2
    assert batch.processed_run_ids == [first.id, third.id]
    assert batch.rate_limited_count == 1
    assert refreshed[first.id].status == "completed"
    assert refreshed[second.id].status == "rate_limited"
    assert refreshed[third.id].status == "completed"


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
