from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import AuditEvent
from app.db.session import get_engine
from app.main import create_app
from app.schemas.drafting import DraftingRequest
from app.schemas.policy import PolicyAction
from app.schemas.source_registry import SourcePolicyEvidenceCreate
from app.services.candidate import CandidateWorkspaceService
from app.services.drafting import (
    DraftingProvider,
    DraftingProviderResult,
    DraftingSafetyError,
    DraftingService,
)
from app.services.source_registry import SourceRegistryService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'drafting.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_drafting_denies_when_runtime_flag_is_disabled(session: Session) -> None:
    evidence_id = CandidateWorkspaceService(session).get_workspace().evidence[0].id
    service = DraftingService(
        session,
        settings=Settings(llm_drafting_enabled=False),
        provider=_provider(),
    )

    run = service.create_draft(
        DraftingRequest(
            review_item_id="greenhouse:101",
            requested_by="operator-test",
            evidence_ids=[evidence_id],
        )
    )

    assert run.status == "denied"
    assert run.failure is not None
    assert run.failure.reason == "llm_drafting_disabled"
    assert run.safety.llm_called is False
    assert run.safety.autofill_performed is False
    assert run.safety.submit_performed is False


def test_drafting_requires_source_policy_draft_allowance(session: Session) -> None:
    evidence_id = CandidateWorkspaceService(session).get_workspace().evidence[0].id
    service = DraftingService(
        session,
        settings=Settings(llm_drafting_enabled=True),
        provider=_provider(),
    )

    run = service.create_draft(
        DraftingRequest(
            review_item_id="greenhouse:101",
            requested_by="operator-test",
            evidence_ids=[evidence_id],
        )
    )

    assert run.status == "denied"
    assert run.failure is not None
    assert run.failure.reason == "source_policy_denied"


def test_drafting_creates_review_required_packet_with_claim_evidence_map(
    session: Session,
) -> None:
    workspace = CandidateWorkspaceService(session).get_workspace()
    evidence_id = workspace.evidence[0].id
    _allow_source_for_drafting(session, "boards.greenhouse.io")
    service = DraftingService(
        session,
        settings=Settings(llm_drafting_enabled=True),
        provider=_provider(
            draft_text="Drafted answer grounded in approved evidence.",
            claim="Built governed APIs.",
            evidence_ids=[evidence_id],
        ),
    )

    run = service.create_draft(
        DraftingRequest(
            review_item_id="greenhouse:101",
            requested_by="operator-test",
            evidence_ids=[evidence_id],
        )
    )

    assert run.status == "review_required"
    assert run.draft_text == "Drafted answer grounded in approved evidence."
    assert run.approval_required is True
    assert run.safety.llm_called is True
    assert run.safety.autofill_performed is False
    assert run.safety.submit_performed is False
    assert run.claim_mappings[0].claim == "Built governed APIs."
    assert run.claim_mappings[0].evidence_ids == (evidence_id,)
    events = session.scalars(select(AuditEvent)).all()
    assert [event.event_type for event in events] == [
        "drafting.requested",
        "drafting.review_required",
    ]
    assert events[-1].payload["approval_required"] is True
    assert "prompt" not in events[-1].payload
    assert "draft_text" not in events[-1].payload


def test_drafting_rejects_provider_claims_without_requested_evidence(
    session: Session,
) -> None:
    workspace = CandidateWorkspaceService(session).get_workspace()
    evidence_id = workspace.evidence[0].id
    _allow_source_for_drafting(session, "boards.greenhouse.io")
    service = DraftingService(
        session,
        settings=Settings(llm_drafting_enabled=True),
        provider=_provider(claim="Unsupported claim.", evidence_ids=["missing-evidence"]),
    )

    with pytest.raises(DraftingSafetyError, match="unsupported claim"):
        service.create_draft(
            DraftingRequest(
                review_item_id="greenhouse:101",
                requested_by="operator-test",
                evidence_ids=[evidence_id],
            )
        )


def test_drafting_endpoint_returns_review_required_packet(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'drafting-api.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        workspace = CandidateWorkspaceService(db_session).get_workspace()
        evidence_id = workspace.evidence[0].id
        _allow_source_for_drafting(db_session, "boards.greenhouse.io")
        db_session.commit()

    app = create_app(
        Settings(database_url=database_url, llm_drafting_enabled=True),
        drafting_provider=_provider(evidence_ids=[evidence_id]),
    )

    with TestClient(app) as client:
        response = client.post(
            "/drafting/runs",
            json={
                "review_item_id": "greenhouse:101",
                "requested_by": "operator-test",
                "evidence_ids": [evidence_id],
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "review_required"
    assert response.json()["approval_required"] is True


def _provider(
    *,
    draft_text: str = "Drafted answer.",
    claim: str = "Synthetic supported claim.",
    evidence_ids: list[str] | None = None,
) -> DraftingProvider:
    def generate(_: object) -> DraftingProviderResult:
        return DraftingProviderResult(
            draft_text=draft_text,
            claim_mappings=[
                {
                    "claim": claim,
                    "evidence_ids": evidence_ids or [],
                }
            ],
            model="test-drafting-model",
        )

    return generate


def _allow_source_for_drafting(session: Session, domain: str) -> None:
    registry = SourceRegistryService(session)
    source = registry.upsert_source(domain=domain)
    registry.attach_source_policy(
        source_id=source.id,
        status="approved",
        reason="Synthetic approval for drafting tests.",
        allowed_actions=[PolicyAction.DRAFT],
        denied_actions=[PolicyAction.AUTOFILL, PolicyAction.SUBMIT],
        evidence=[
            SourcePolicyEvidenceCreate(
                evidence_type="manual_approval",
                url=f"https://{domain}/policy",
                excerpt="Synthetic test approval for drafting.",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        ],
    )
    session.commit()
