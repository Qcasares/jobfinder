from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.main import create_app
from app.schemas.jobs import JobListItem, JobSummary
from app.services.jobs import JobCatalogService


def test_job_catalog_lists_synthetic_fixture_jobs() -> None:
    service = JobCatalogService()

    jobs = service.list_jobs()
    summary = service.get_summary()

    assert len(jobs) == 7
    assert summary == JobSummary(
        total=7,
        ready=7,
        needs_review=0,
        remote=3,
        hybrid=1,
        onsite=3,
        unknown_remote=0,
    )
    assert all(job.synthetic for job in jobs)
    assert {job.fixture_name for job in jobs} == {
        "ashby_remote.json",
        "greenhouse_missing_salary.json",
        "jsonld_remote.json",
        "lever_multiple_locations.json",
        "smartrecruiters_expired.json",
        "static_html_on_site.html",
        "workable_hybrid.json",
    }


def test_job_catalog_status_filter_uses_review_status() -> None:
    service = JobCatalogService()

    assert len(service.list_jobs(status="ready")) == 7
    assert service.list_jobs(status="needs_review") == []


def test_jobs_endpoints_return_typed_schemas() -> None:
    client = _test_client()

    jobs_response = client.get("/jobs")
    summary_response = client.get("/jobs/summary")

    assert jobs_response.status_code == 200
    jobs = [JobListItem.model_validate(item) for item in jobs_response.json()]
    assert len(jobs) == 7
    assert jobs[0].source_url.startswith("https://")
    assert all(job.review_status == "ready" for job in jobs)

    assert summary_response.status_code == 200
    summary = JobSummary.model_validate(summary_response.json())
    assert summary.total == 7
    assert summary.ready == 7


def _test_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return TestClient(create_app(test_engine=engine))
