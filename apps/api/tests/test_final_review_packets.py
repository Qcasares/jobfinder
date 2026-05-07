from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import AuditEvent
from app.db.session import get_engine
from app.main import create_app
from app.schemas.autofill import AutofillPacketRequest
from app.schemas.drafting import DraftingRequest
from app.schemas.final_review import FinalReviewPacketRequest
from app.schemas.policy import PolicyAction
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.autofill import AutofillPacketService
from app.services.candidate import CandidateWorkspaceService
from app.services.drafting import DraftingProviderResult, DraftingService
from app.services.final_review import FinalReviewPacketService
from app.services.source_registry import SourceRegistryService


def test_final_review_packet_denies_when_runtime_flag_is_disabled(tmp_path: Path) -> None:
    session = _session(tmp_path)
    packet_id = _autofill_packet(session)
    service = FinalReviewPacketService(
        session,
        settings=Settings(submission_packets_enabled=False),
    )

    packet = service.create_packet(
        FinalReviewPacketRequest(
            autofill_packet_id=packet_id,
            requested_by="operator-test",
            operator_confirmation="ready_for_final_review",
        )
    )

    assert packet.status == "denied"
    assert packet.failure is not None
    assert packet.failure.reason == "submission_packets_disabled"
    assert packet.safety.submit_performed is False
    assert packet.safety.external_side_effect is False


def test_final_review_packet_requires_source_policy_submit_allowance(tmp_path: Path) -> None:
    session = _session(tmp_path)
    packet_id = _autofill_packet(session)
    service = FinalReviewPacketService(
        session,
        settings=Settings(submission_packets_enabled=True),
    )

    packet = service.create_packet(
        FinalReviewPacketRequest(
            autofill_packet_id=packet_id,
            requested_by="operator-test",
            operator_confirmation="ready_for_final_review",
        )
    )

    assert packet.status == "denied"
    assert packet.failure is not None
    assert packet.failure.reason == "source_policy_denied"
    assert packet.safety.submit_performed is False


def test_final_review_packet_records_review_required_no_external_side_effect(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    packet_id = _autofill_packet(session)
    _allow_source(session, "boards.greenhouse.io", [PolicyAction.SUBMIT])
    service = FinalReviewPacketService(
        session,
        settings=Settings(submission_packets_enabled=True),
    )

    packet = service.create_packet(
        FinalReviewPacketRequest(
            autofill_packet_id=packet_id,
            requested_by="operator-test",
            operator_confirmation="ready_for_final_review",
            rollback_notes="Withdraw through source dashboard if needed.",
        )
    )

    assert packet.status == "review_required"
    assert packet.approval_required is True
    assert packet.operator_confirmation == "ready_for_final_review"
    assert packet.safety.final_confirmation_recorded is True
    assert packet.safety.submit_performed is False
    assert packet.safety.external_side_effect is False
    assert packet.rollback_notes == "Withdraw through source dashboard if needed."
    events = session.scalars(select(AuditEvent)).all()
    assert [event.event_type for event in events][-2:] == [
        "final_review.packet.requested",
        "final_review.packet.review_required",
    ]
    assert events[-1].payload["submit_policy_checked"] is True
    assert events[-1].payload["submit_performed"] is False
    assert events[-1].payload["external_side_effect"] is False
    assert "field_values" not in events[-1].payload


def test_final_review_packet_endpoint_returns_review_required_packet(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'final-review-api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        packet_id = _autofill_packet(db_session)
        _allow_source(db_session, "boards.greenhouse.io", [PolicyAction.SUBMIT])
        db_session.commit()

    app = create_app(Settings(database_url=database_url, submission_packets_enabled=True))

    with TestClient(app) as client:
        response = client.post(
            "/final-review/packets",
            json={
                "autofill_packet_id": packet_id,
                "requested_by": "operator-test",
                "operator_confirmation": "ready_for_final_review",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "review_required"
    assert response.json()["safety"]["submit_performed"] is False
    assert response.json()["safety"]["external_side_effect"] is False


def _session(tmp_path: Path) -> Session:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'final-review.db'}")
    Base.metadata.create_all(engine)
    return Session(engine)


def _autofill_packet(session: Session) -> str:
    workspace = CandidateWorkspaceService(session).get_workspace()
    evidence_id = workspace.evidence[0].id
    _allow_source(session, "boards.greenhouse.io", [PolicyAction.DRAFT, PolicyAction.AUTOFILL])
    drafting_run = DraftingService(
        session,
        settings=Settings(llm_drafting_enabled=True),
        provider=lambda _: DraftingProviderResult(
            draft_text="Drafted answer.",
            claim_mappings=[{"claim": "Synthetic claim.", "evidence_ids": [evidence_id]}],
            model="test-drafting-model",
        ),
    ).create_draft(
        DraftingRequest(
            review_item_id="greenhouse:101",
            requested_by="operator-test",
            evidence_ids=[evidence_id],
        )
    )
    packet = AutofillPacketService(
        session,
        settings=Settings(autofill_packets_enabled=True),
    ).create_packet(
        AutofillPacketRequest(
            drafting_run_id=drafting_run.id,
            target_url="https://boards.greenhouse.io/acmerobotics/jobs/101",
            requested_by="operator-test",
        )
    )
    session.commit()
    return packet.id


def _allow_source(
    session: Session,
    domain: str,
    allowed_actions: list[PolicyAction],
) -> None:
    registry = SourceRegistryService(session)
    source = registry.upsert_source(domain=domain)
    registry.attach_source_policy(
        source_id=source.id,
        status="approved",
        reason="Synthetic approval for final review packet tests.",
        allowed_actions=allowed_actions,
        denied_actions=[],
        evidence=[
            SourcePolicyEvidenceCreate(
                evidence_type="manual_approval",
                url=f"https://{domain}/policy",
                excerpt="Synthetic approval.",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        ],
    )
    session.commit()
