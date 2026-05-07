from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.base import Base
from app.db.models import AuditEvent, CandidateEvidence, CandidateProfile, SearchCriteria
from app.db.session import get_engine
from app.main import create_app
from app.schemas.candidate import (
    CandidateDocumentRecordCreate,
    CandidateEvidenceCreate,
    CandidateProfileUpdate,
    CandidateWorkspaceRead,
    SearchCriteriaCreate,
)
from app.services.candidate import CandidateSafetyError, CandidateWorkspaceService


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = get_engine(f"sqlite+pysqlite:///{tmp_path / 'candidate.db'}")
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


def test_candidate_workspace_seeds_synthetic_profile_evidence_and_criteria(
    session: Session,
) -> None:
    workspace = CandidateWorkspaceService(session).get_workspace()

    assert workspace.profile.synthetic is True
    assert workspace.profile.profile_name == "Synthetic Candidate Profile"
    assert "Synthetic local candidate workspace" in workspace.safety_note
    assert len(workspace.evidence) == 2
    assert len(workspace.search_criteria) == 1
    assert all(item.synthetic for item in workspace.evidence)
    assert all(item.synthetic for item in workspace.search_criteria)


def test_candidate_workspace_updates_profile_and_audits(session: Session) -> None:
    service = CandidateWorkspaceService(session)
    service.get_workspace()

    updated = service.update_profile(
        CandidateProfileUpdate(
            profile_name="Synthetic Platform Candidate",
            summary="Synthetic profile summary for workflow validation only.",
        )
    )

    assert updated.profile_name == "Synthetic Platform Candidate"
    events = session.scalars(select(AuditEvent)).all()
    assert [event.event_type for event in events] == ["candidate.profile.updated"]
    assert events[0].payload["real_candidate_data"] is False


def test_candidate_evidence_rejects_non_synthetic_source_url(session: Session) -> None:
    service = CandidateWorkspaceService(session)

    with pytest.raises(CandidateSafetyError):
        service.create_evidence(
            CandidateEvidenceCreate(
                evidence_type="project",
                title="Synthetic project evidence",
                description="Synthetic only.",
                source_url="https://not-example.invalid/profile",
            )
        )


def test_candidate_document_record_requires_explicit_vault_enablement(session: Session) -> None:
    service = CandidateWorkspaceService(session, settings=Settings(candidate_vault_enabled=False))

    with pytest.raises(CandidateSafetyError, match="candidate vault is disabled"):
        service.create_document_record(
            CandidateDocumentRecordCreate(
                document_type="cv",
                display_name="Current CV",
                storage_ref="vault://candidate-documents/current-cv.pdf",
                content_sha256="a" * 64,
                byte_size=1024,
                mime_type="application/pdf",
                consent_scope="job_search",
                retention_days=90,
            )
        )


def test_candidate_document_record_stores_metadata_only_and_audits(session: Session) -> None:
    service = CandidateWorkspaceService(session, settings=Settings(candidate_vault_enabled=True))

    record = service.create_document_record(
        CandidateDocumentRecordCreate(
            document_type="cv",
            display_name="Current CV",
            storage_ref="vault://candidate-documents/current-cv.pdf",
            content_sha256="b" * 64,
            byte_size=2048,
            mime_type="application/pdf",
            consent_scope="job_search",
            retention_days=30,
        )
    )

    assert record.document_type == "cv"
    assert record.synthetic is False
    assert record.extraction_approved is False
    assert record.content_stored is False
    assert record.storage_ref == "vault://candidate-documents/current-cv.pdf"
    events = session.scalars(select(AuditEvent)).all()
    assert [event.event_type for event in events] == ["candidate.document_record.created"]
    assert events[0].payload["real_candidate_data"] is True
    assert "content_sha256" in events[0].payload
    assert "document_content" not in events[0].payload


def test_candidate_document_record_rejects_credentials_and_inline_content(session: Session) -> None:
    service = CandidateWorkspaceService(session, settings=Settings(candidate_vault_enabled=True))

    with pytest.raises(CandidateSafetyError, match="credentials"):
        service.create_document_record(
            CandidateDocumentRecordCreate(
                document_type="credential",
                display_name="Job board password",
                storage_ref="vault://candidate-documents/password.txt",
                content_sha256="c" * 64,
                byte_size=128,
                mime_type="text/plain",
                consent_scope="job_search",
                retention_days=30,
            )
        )

    with pytest.raises(CandidateSafetyError, match="document content"):
        service.create_document_record(
            CandidateDocumentRecordCreate(
                document_type="cv",
                display_name="Current CV",
                storage_ref="vault://candidate-documents/current-cv.pdf",
                content_sha256="d" * 64,
                byte_size=2048,
                mime_type="application/pdf",
                consent_scope="Full CV text: private candidate details",
                retention_days=30,
            )
        )


def test_candidate_search_criteria_rejects_reversed_salary(session: Session) -> None:
    service = CandidateWorkspaceService(session)

    with pytest.raises(CandidateSafetyError):
        service.create_search_criteria(
            SearchCriteriaCreate(
                name="Synthetic criteria",
                query="synthetic backend roles",
                salary_min=200000,
                salary_max=100000,
            )
        )


def test_candidate_endpoints_return_typed_schemas(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, database_url = client_and_database_url

    workspace_response = client.get("/candidate/workspace")
    profile_response = client.post(
        "/candidate/profile",
        json={
            "profile_name": "Synthetic Candidate Variant",
            "summary": "Synthetic summary for dashboard testing only.",
            "synthetic": True,
        },
    )
    evidence_response = client.post(
        "/candidate/evidence",
        json={
            "evidence_type": "skill",
            "title": "Synthetic API testing evidence",
            "description": "Placeholder evidence for local validation.",
            "source_url": "https://example.com/synthetic-api-testing",
            "synthetic": True,
        },
    )
    criteria_response = client.post(
        "/candidate/search-criteria",
        json={
            "name": "Synthetic API roles",
            "query": "backend APIs and data workflow",
            "location": "Remote - UK",
            "remote_type": "remote",
            "synthetic": True,
        },
    )
    document_response = client.post(
        "/candidate/document-records",
        json={
            "document_type": "cv",
            "display_name": "Current CV",
            "storage_ref": "vault://candidate-documents/current-cv.pdf",
            "content_sha256": "e" * 64,
            "byte_size": 2048,
            "mime_type": "application/pdf",
            "consent_scope": "job_search",
            "retention_days": 30,
        },
    )

    assert workspace_response.status_code == 200
    workspace = CandidateWorkspaceRead.model_validate(workspace_response.json())
    assert workspace.profile.profile_name == "Synthetic Candidate Profile"
    assert profile_response.status_code == 200
    assert evidence_response.status_code == 200
    assert criteria_response.status_code == 200
    assert document_response.status_code == 422

    with Session(get_engine(database_url)) as db_session:
        assert len(db_session.scalars(select(CandidateProfile)).all()) == 1
        assert len(db_session.scalars(select(CandidateEvidence)).all()) == 3
        assert len(db_session.scalars(select(SearchCriteria)).all()) == 2
        assert len(db_session.scalars(select(AuditEvent)).all()) == 3


def test_candidate_endpoint_rejects_real_contact_like_text(
    client_and_database_url: tuple[TestClient, str],
) -> None:
    client, _ = client_and_database_url

    response = client.post(
        "/candidate/profile",
        json={
            "profile_name": "Synthetic Candidate",
            "summary": "Email me at candidate@example.com",
            "synthetic": True,
        },
    )

    assert response.status_code == 422


def test_production_write_guard_blocks_candidate_mutation(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'candidate-production.db'}"
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    app = create_app(
        Settings(
            database_url=database_url,
            service_name="jobfinder-api",
            environment="production",
        )
    )

    with TestClient(app) as client:
        workspace_response = client.get("/candidate/workspace")
        profile_response = client.post(
            "/candidate/profile",
            json={
                "profile_name": "Synthetic Candidate Variant",
                "summary": "Synthetic summary for dashboard testing only.",
                "synthetic": True,
            },
        )

    assert workspace_response.status_code == 200
    assert profile_response.status_code == 403
