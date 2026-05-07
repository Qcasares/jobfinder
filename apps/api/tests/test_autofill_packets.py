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
from app.schemas.policy import PolicyAction
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.autofill import AutofillPacketService
from app.services.candidate import CandidateWorkspaceService
from app.services.drafting import DraftingProviderResult, DraftingService
from app.services.source_registry import SourceRegistryService


def test_autofill_packet_denies_when_runtime_flag_is_disabled(tmp_path: Path) -> None:
    session = _session(tmp_path)
    drafting_run_id = _drafting_run(session)
    service = AutofillPacketService(
        session,
        settings=Settings(autofill_packets_enabled=False),
    )

    packet = service.create_packet(
        AutofillPacketRequest(
            drafting_run_id=drafting_run_id,
            target_url="https://boards.greenhouse.io/acmerobotics/jobs/101",
            requested_by="operator-test",
        )
    )

    assert packet.status == "denied"
    assert packet.failure is not None
    assert packet.failure.reason == "autofill_packets_disabled"
    assert packet.safety.dry_run is True
    assert packet.safety.browser_automation_performed is False
    assert packet.safety.autofill_performed is False
    assert packet.safety.submit_performed is False


def test_autofill_packet_requires_source_policy_autofill_allowance(tmp_path: Path) -> None:
    session = _session(tmp_path)
    drafting_run_id = _drafting_run(session)
    service = AutofillPacketService(
        session,
        settings=Settings(autofill_packets_enabled=True),
    )

    packet = service.create_packet(
        AutofillPacketRequest(
            drafting_run_id=drafting_run_id,
            target_url="https://boards.greenhouse.io/acmerobotics/jobs/101",
            requested_by="operator-test",
        )
    )

    assert packet.status == "denied"
    assert packet.failure is not None
    assert packet.failure.reason == "source_policy_denied"


def test_autofill_packet_creates_dry_run_fields_and_audit(tmp_path: Path) -> None:
    session = _session(tmp_path)
    drafting_run_id = _drafting_run(session)
    _allow_source_for_autofill(session, "boards.greenhouse.io")
    service = AutofillPacketService(
        session,
        settings=Settings(autofill_packets_enabled=True),
    )

    packet = service.create_packet(
        AutofillPacketRequest(
            drafting_run_id=drafting_run_id,
            target_url="https://boards.greenhouse.io/acmerobotics/jobs/101",
            requested_by="operator-test",
        )
    )

    assert packet.status == "review_required"
    assert packet.approval_required is True
    assert packet.safety.dry_run is True
    assert packet.safety.browser_automation_performed is False
    assert packet.safety.autofill_performed is False
    assert packet.safety.submit_performed is False
    assert packet.fields[0].field_key == "cover_letter"
    assert packet.fields[0].value_preview == "Drafted answer."
    assert packet.fields[0].provenance == "drafting_run"
    events = session.scalars(select(AuditEvent)).all()
    assert [event.event_type for event in events][-2:] == [
        "autofill.packet.requested",
        "autofill.packet.review_required",
    ]
    assert events[-1].payload["dry_run"] is True
    assert events[-1].payload["browser_automation_performed"] is False
    assert events[-1].payload["submit_performed"] is False
    assert "field_values" not in events[-1].payload


def test_autofill_packet_endpoint_returns_review_required_packet(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'autofill-api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        drafting_run_id = _drafting_run(db_session)
        _allow_source_for_autofill(db_session, "boards.greenhouse.io")
        db_session.commit()

    app = create_app(Settings(database_url=database_url, autofill_packets_enabled=True))

    with TestClient(app) as client:
        response = client.post(
            "/autofill/packets",
            json={
                "drafting_run_id": drafting_run_id,
                "target_url": "https://boards.greenhouse.io/acmerobotics/jobs/101",
                "requested_by": "operator-test",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "review_required"
    assert response.json()["safety"]["dry_run"] is True
    assert response.json()["safety"]["browser_automation_performed"] is False


def _session(tmp_path: Path) -> Session:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'autofill.db'}")
    Base.metadata.create_all(engine)
    return Session(engine)


def _drafting_run(session: Session) -> str:
    workspace = CandidateWorkspaceService(session).get_workspace()
    evidence_id = workspace.evidence[0].id
    _allow_source_for_drafting(session, "boards.greenhouse.io")
    run = DraftingService(
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
    session.commit()
    return run.id


def _allow_source_for_drafting(session: Session, domain: str) -> None:
    _attach_policy(session, domain, allowed_actions=[PolicyAction.DRAFT])


def _allow_source_for_autofill(session: Session, domain: str) -> None:
    _attach_policy(session, domain, allowed_actions=[PolicyAction.DRAFT, PolicyAction.AUTOFILL])


def _attach_policy(
    session: Session,
    domain: str,
    *,
    allowed_actions: list[PolicyAction],
) -> None:
    registry = SourceRegistryService(session)
    source = registry.upsert_source(domain=domain)
    registry.attach_source_policy(
        source_id=source.id,
        status="approved",
        reason="Synthetic approval for autofill packet tests.",
        allowed_actions=allowed_actions,
        denied_actions=[PolicyAction.SUBMIT],
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
