from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.main import create_app
from app.schemas.live_discovery import LiveDiscoveryRequest, LiveDiscoveryStatus
from app.schemas.policy import PolicyAction
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.audit import AuditEventService
from app.services.live_discovery import FetchResult, LiveDiscoveryService
from app.services.source_registry import SourceRegistryService

JSON_LD_HTML = b"""
<html>
  <head>
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Live Platform Engineer",
        "url": "https://careers.example.test/jobs/platform",
        "identifier": {"value": "live-platform-1"},
        "hiringOrganization": {"name": "Example Careers"},
        "jobLocationType": "TELECOMMUTE",
        "applicantLocationRequirements": {"name": "Remote - UK"},
        "employmentType": "FULL_TIME",
        "baseSalary": {
          "currency": "GBP",
          "value": {"minValue": 90000, "maxValue": 120000}
        },
        "datePosted": "2026-05-01",
        "validThrough": "2026-06-01"
      }
    </script>
  </head>
</html>
"""

SEARCH_RESULTS_HTML = b"""
<html>
  <body>
    <a href="/jobs/platform">Platform Engineer</a>
    <a href="https://careers.example.test/jobs/data">Data Engineer</a>
    <a href="https://external.example.test/jobs/blocked">External Role</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_live_discovery_is_denied_when_runtime_flag_is_disabled() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=False),
        fetcher=_fetcher(JSON_LD_HTML),
    )

    run = service.run(
        LiveDiscoveryRequest(
            url="https://careers.example.test/jobs/platform",
            source_domain="careers.example.test",
        )
    )

    assert run.status == LiveDiscoveryStatus.DENIED
    assert run.failure is not None
    assert run.failure.reason == "live_discovery_disabled"
    assert service.review_items() == []


def test_live_discovery_denies_unknown_source_before_fetch() -> None:
    session = _session()
    fetched = False

    def fetcher(_: str) -> FetchResult:
        nonlocal fetched
        fetched = True
        return FetchResult(
            final_url="https://unknown.example.test/jobs/platform",
            status_code=200,
            content_type="text/html",
            body=JSON_LD_HTML,
        )

    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True),
        fetcher=fetcher,
    )

    run = service.run(LiveDiscoveryRequest(url="https://unknown.example.test/jobs/platform"))

    assert run.status == LiveDiscoveryStatus.DENIED
    assert run.failure is not None
    assert run.failure.reason == "source_policy_denied"
    assert fetched is False


def test_live_discovery_requires_extract_policy_before_fetch() -> None:
    session = _session()
    registry = SourceRegistryService(session)
    source = registry.upsert_source(domain="careers.example.test")
    registry.attach_source_policy(
        source_id=source.id,
        status="approved",
        reason="Discovery only.",
        allowed_actions=[PolicyAction.DISCOVER],
        denied_actions=[PolicyAction.EXTRACT],
        evidence=[
            SourcePolicyEvidenceCreate(
                evidence_type="manual_approval",
                url="https://careers.example.test/policy",
                excerpt="Synthetic test approval.",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        ],
    )
    fetched = False

    def fetcher(_: str) -> FetchResult:
        nonlocal fetched
        fetched = True
        return FetchResult(
            final_url="https://careers.example.test/jobs/platform",
            status_code=200,
            content_type="text/html",
            body=JSON_LD_HTML,
        )

    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True),
        fetcher=fetcher,
    )

    run = service.run(
        LiveDiscoveryRequest(
            url="https://careers.example.test/jobs/platform",
            source_domain="careers.example.test",
        )
    )

    assert run.status == LiveDiscoveryStatus.DENIED
    assert run.failure is not None
    assert run.failure.reason == "source_policy_denied"
    assert fetched is False


def test_live_discovery_extracts_json_ld_and_appends_audit_events() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    audit = AuditEventService(session)
    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True),
        audit_service=audit,
        fetcher=_fetcher(JSON_LD_HTML),
    )

    run = service.run(
        LiveDiscoveryRequest(
            url="https://careers.example.test/jobs/platform",
            source_domain="careers.example.test",
        )
    )

    assert run.status == LiveDiscoveryStatus.EXTRACTED
    assert run.extracted_count == 1
    items = service.review_items()
    assert len(items) == 1
    assert items[0].title == "Live Platform Engineer"
    assert items[0].synthetic is False
    assert items[0].data_origin == "live_extraction"
    event_types = [event.event_type for event in audit.list_events()]
    assert "live_discovery.requested" in event_types
    assert "live_discovery.fetched" in event_types
    assert "live_discovery.extracted" in event_types


def test_live_discovery_rejects_non_https_urls() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True),
        fetcher=_fetcher(JSON_LD_HTML),
    )

    run = service.run(LiveDiscoveryRequest(url="http://careers.example.test/jobs/platform"))

    assert run.status == LiveDiscoveryStatus.DENIED
    assert run.failure is not None
    assert run.failure.reason == "invalid_url"


def test_live_discovery_endpoints_return_run_and_review_item() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _allow_source(session, "careers.example.test")
        session.commit()

    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            live_discovery_enabled=True,
        ),
        live_discovery_fetcher=_fetcher(JSON_LD_HTML),
        test_engine=engine,
    )

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/runs",
            json={
                "url": "https://careers.example.test/jobs/platform",
                "source_domain": "careers.example.test",
            },
        )
        review_response = client.get("/review/queue")

    assert response.status_code == 200
    assert response.json()["status"] == "extracted"
    assert any(item["data_origin"] == "live_extraction" for item in review_response.json())


def test_live_search_discovery_finds_same_domain_job_links_and_audits_run() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    audit = AuditEventService(session)
    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        audit_service=audit,
        fetcher=_fetcher(SEARCH_RESULTS_HTML),
    )

    run = service.discover_search_results(
        url="https://careers.example.test/search?q=engineer",
        source_domain="careers.example.test",
        requested_by="operator-test",
        max_results=5,
    )

    assert run.status == LiveDiscoveryStatus.DISCOVERED
    assert run.discovered_count == 2
    assert run.discovered_urls == (
        "https://careers.example.test/jobs/platform",
        "https://careers.example.test/jobs/data",
    )
    event_types = [event.event_type for event in audit.list_events()]
    assert "live_search_discovery.requested" in event_types
    assert "live_search_discovery.discovered" in event_types


def test_live_search_discovery_requires_runtime_flag_and_discover_policy_before_fetch() -> None:
    session = _session()
    _allow_source(session, "careers.example.test")
    fetched = False

    def fetcher(_: str) -> FetchResult:
        nonlocal fetched
        fetched = True
        return FetchResult(
            final_url="https://careers.example.test/search",
            status_code=200,
            content_type="text/html",
            body=SEARCH_RESULTS_HTML,
        )

    service = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=False),
        fetcher=fetcher,
    )

    disabled_run = service.discover_search_results(
        url="https://careers.example.test/search",
        source_domain="careers.example.test",
    )
    unknown_run = LiveDiscoveryService(
        session,
        settings=Settings(live_discovery_enabled=True, live_search_discovery_enabled=True),
        fetcher=fetcher,
    ).discover_search_results(url="https://unknown.example.test/search")

    assert disabled_run.status == LiveDiscoveryStatus.DENIED
    assert disabled_run.failure is not None
    assert disabled_run.failure.reason == "live_search_discovery_disabled"
    assert unknown_run.status == LiveDiscoveryStatus.DENIED
    assert unknown_run.failure is not None
    assert unknown_run.failure.reason == "source_policy_denied"
    assert fetched is False


def test_live_search_discovery_endpoint_returns_discovered_urls() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _allow_source(session, "careers.example.test")
        session.commit()

    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            live_discovery_enabled=True,
            live_search_discovery_enabled=True,
        ),
        live_discovery_fetcher=_fetcher(SEARCH_RESULTS_HTML),
        test_engine=engine,
    )

    with TestClient(app) as client:
        response = client.post(
            "/live-discovery/search-runs",
            json={
                "url": "https://careers.example.test/search?q=engineer",
                "source_domain": "careers.example.test",
                "max_results": 5,
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "discovered"
    assert response.json()["discovered_urls"] == [
        "https://careers.example.test/jobs/platform",
        "https://careers.example.test/jobs/data",
    ]


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
        reason="Synthetic test approval for live discovery and extraction.",
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


def _fetcher(body: bytes) -> Callable[[str], FetchResult]:
    def fetch(url: str) -> FetchResult:
        return FetchResult(
            final_url=url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=body,
        )

    return fetch
