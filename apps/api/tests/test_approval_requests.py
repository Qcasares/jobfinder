from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import Application, ApprovalRequest, AuditEvent
from app.db.session import get_engine
from app.main import create_app
from app.schemas.approvals import (
    ApprovalDecisionCreate,
    ApprovalRequestCreate,
    ApprovalRequestRead,
    ApprovalRequestSummary,
)
from app.services.approvals import (
    ApprovalRequestNotFoundError,
    ApprovalRequestService,
    InvalidApprovalTransitionError,
    ReviewItemNotFoundError,
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'approvals.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client_and_database_url(tmp_path: Path) -> Iterator[tuple[TestClient, str]]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    app = create_app(Settings(database_url=database_url, service_name="jobfinder-api"))
    with TestClient(app) as client:
        yield client, database_url


def test_create_list_summary_and_decide_manual_approval_request(session: Session) -> None:
    service = ApprovalRequestService(session)

    created = service.create_request(
        ApprovalRequestCreate(
            review_item_id="greenhouse:101",
            requester_id="reviewer-local",
            reason="Low confidence extraction requires manual review.",
        )
    )
    session.commit()

    assert created.status == "pending"
    assert created.review_item_id == "greenhouse:101"
    assert created.safety.submit_performed is False
    assert created.safety.autofill_performed is False
    assert service.get_summary() == ApprovalRequestSummary(
        total=1,
        pending=1,
        approved=0,
        rejected=0,
        needs_changes=0,
    )
    assert [item.id for item in service.list_requests()] == [created.id]

    decided = service.record_decision(
        created.id,
        ApprovalDecisionCreate(
            reviewer_id="reviewer-local",
            decision="approved",
            reason="Reviewed source and provenance manually.",
        ),
    )
    session.commit()

    assert decided.status == "approved"
    assert decided.reviewer_id == "reviewer-local"
    assert decided.resolved_at is not None
    assert decided.safety.application_created is False
    assert session.scalars(select(Application)).all() == []
    assert service.get_summary().approved == 1

    audit_events = session.scalars(select(AuditEvent).order_by(AuditEvent.created_at)).all()
    assert [event.event_type for event in audit_events] == [
        "approval.request.created",
        "approval.request.decided",
    ]
    assert audit_events[-1].payload["submit_performed"] is False
    assert audit_events[-1].payload["autofill_performed"] is False


def test_unknown_review_item_and_request_ids_fail_cleanly(session: Session) -> None:
    service = ApprovalRequestService(session)

    with pytest.raises(ReviewItemNotFoundError):
        service.create_request(
            ApprovalRequestCreate(
                review_item_id="unknown:missing",
                requester_id="reviewer-local",
                reason="Missing review item.",
            )
        )

    with pytest.raises(ApprovalRequestNotFoundError):
        service.record_decision(
            "missing-request",
            ApprovalDecisionCreate(
                reviewer_id="reviewer-local",
                decision="rejected",
                reason="No such request.",
            ),
        )


def test_decision_transitions_are_constrained(session: Session) -> None:
    service = ApprovalRequestService(session)
    created = service.create_request(
        ApprovalRequestCreate(
            review_item_id="lever:lev-200",
            requester_id="reviewer-local",
            reason="Manual gate before action.",
        )
    )
    service.record_decision(
        created.id,
        ApprovalDecisionCreate(
            reviewer_id="reviewer-local",
            decision="needs_changes",
            reason="Need revised extraction evidence.",
        ),
    )

    with pytest.raises(InvalidApprovalTransitionError):
        service.record_decision(
            created.id,
            ApprovalDecisionCreate(
                reviewer_id="reviewer-local",
                decision="approved",
                reason="Trying to approve after terminal decision.",
            ),
        )


def test_approval_request_endpoints_return_typed_schemas(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, database_url = client_and_database_url

    create_response = client.post(
        "/approvals/requests",
        json={
            "review_item_id": "ashby:ash-300",
            "requester_id": "reviewer-local",
            "reason": "Manual review requested from dashboard.",
        },
    )
    assert create_response.status_code == 200
    created = ApprovalRequestRead.model_validate(create_response.json())

    list_response = client.get("/approvals/requests")
    summary_response = client.get("/approvals/summary")
    decision_response = client.post(
        f"/approvals/requests/{created.id}/decision",
        json={
            "reviewer_id": "reviewer-local",
            "decision": "rejected",
            "reason": "Rejected after manual review.",
        },
    )

    assert list_response.status_code == 200
    listed = [ApprovalRequestRead.model_validate(item) for item in list_response.json()]
    assert [item.id for item in listed] == [created.id]
    assert summary_response.status_code == 200
    assert ApprovalRequestSummary.model_validate(summary_response.json()).pending == 1
    assert decision_response.status_code == 200
    decided = ApprovalRequestRead.model_validate(decision_response.json())
    assert decided.status == "rejected"
    assert decided.safety.submit_performed is False

    with Session(get_engine(database_url)) as db_session:
        assert db_session.scalars(select(Application)).all() == []
        assert len(db_session.scalars(select(ApprovalRequest)).all()) == 1


def test_invalid_decision_transition_endpoint_returns_conflict(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, _ = client_and_database_url
    created = ApprovalRequestRead.model_validate(
        client.post(
            "/approvals/requests",
            json={
                "review_item_id": "workable:wk-500",
                "requester_id": "reviewer-local",
                "reason": "Manual review requested.",
            },
        ).json()
    )
    first_decision = client.post(
        f"/approvals/requests/{created.id}/decision",
        json={
            "reviewer_id": "reviewer-local",
            "decision": "approved",
            "reason": "Approved manually.",
        },
    )
    second_decision = client.post(
        f"/approvals/requests/{created.id}/decision",
        json={
            "reviewer_id": "reviewer-local",
            "decision": "rejected",
            "reason": "Cannot decide twice.",
        },
    )

    assert first_decision.status_code == 200
    assert second_decision.status_code == 409
