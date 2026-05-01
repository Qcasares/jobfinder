from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import Application, ApprovalRequest, JobPosting, User
from app.db.session import get_engine
from app.main import create_app
from app.schemas.applications import ApplicationRead, ApplicationSummary
from app.services.applications import ApplicationTrackerService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'applications.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as seed_session:
        _seed_application_fixture(seed_session)
    app = create_app(Settings(database_url=database_url, service_name="jobfinder-api"))
    with TestClient(app) as test_client:
        yield test_client


def test_application_tracker_is_empty_until_records_exist(session: Session) -> None:
    service = ApplicationTrackerService(session)

    assert service.list_applications() == []
    assert service.get_summary() == ApplicationSummary(
        total=0,
        not_started=0,
        in_review=0,
        approved=0,
        submitted=0,
        external_side_effects=0,
    )


def test_application_tracker_reads_existing_records_without_side_effects(session: Session) -> None:
    _seed_application_fixture(session)
    service = ApplicationTrackerService(session)

    applications = service.list_applications()

    assert len(applications) == 1
    assert applications[0].status == "ready_for_review"
    assert applications[0].job_title == "Backend Engineer"
    assert applications[0].company == "Acme Robotics"
    assert applications[0].safety.submit_performed is False
    assert applications[0].safety.autofill_performed is False
    assert applications[0].safety.external_side_effect is False
    assert service.get_summary() == ApplicationSummary(
        total=1,
        not_started=0,
        in_review=1,
        approved=0,
        submitted=0,
        external_side_effects=0,
    )


def test_application_endpoints_are_read_only(client: TestClient) -> None:
    list_response = client.get("/applications")
    summary_response = client.get("/applications/summary")
    create_response = client.post("/applications", json={"status": "submitted"})
    submit_response = client.post("/applications/job-1/submit")

    assert list_response.status_code == 200
    assert summary_response.status_code == 200
    listed = [ApplicationRead.model_validate(item) for item in list_response.json()]
    assert [item.status for item in listed] == ["ready_for_review"]
    assert ApplicationSummary.model_validate(summary_response.json()).in_review == 1
    assert create_response.status_code == 405
    assert submit_response.status_code == 404


def _seed_application_fixture(session: Session) -> None:
    user = User(
        id="user-local",
        email="reviewer@local.jobfinder.synthetic",
        display_name="Reviewer Local",
    )
    job = JobPosting(
        id="job-1",
        canonical_url="https://example.com/jobs/backend-engineer",
        title="Backend Engineer",
        company="Acme Robotics",
        remote_type="onsite",
        employment_type="full_time",
        salary_min=None,
        salary_max=None,
        salary_currency=None,
        posted_date=None,
        valid_through=None,
        extraction_confidence=None,
    )
    approval = ApprovalRequest(
        id="approval-1",
        review_item_id="greenhouse:101",
        job_posting_id=job.id,
        user_id=user.id,
        requester_id="reviewer-local",
        reviewer_id=None,
        request_type="manual_review",
        status="pending",
        reason="Manual review before any application work.",
        requested_at=datetime(2026, 4, 30, 9, 0, tzinfo=UTC),
        resolved_at=None,
    )
    application = Application(
        id="application-1",
        job_posting_id=job.id,
        user_id=user.id,
        approval_request_id=approval.id,
        status="ready_for_review",
        application_url=None,
        submitted_at=None,
    )
    session.add_all([user, job, approval, application])
    session.commit()
