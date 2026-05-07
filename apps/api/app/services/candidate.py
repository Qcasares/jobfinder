from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import (
    CandidateDocumentRecord,
    CandidateEvidence,
    CandidateProfile,
    SearchCriteria,
    User,
)
from app.schemas.audit import ActorType
from app.schemas.candidate import (
    CandidateDocumentRecordCreate,
    CandidateDocumentRecordRead,
    CandidateEvidenceCreate,
    CandidateEvidenceRead,
    CandidateProfileRead,
    CandidateProfileUpdate,
    CandidateWorkspaceRead,
    SearchCriteriaCreate,
    SearchCriteriaRead,
)
from app.services.audit import AuditEventService

LOCAL_USER_ID = str(uuid5(NAMESPACE_URL, "jobfinder:local-user:synthetic-candidate"))
LOCAL_PROFILE_ID = str(uuid5(NAMESPACE_URL, "jobfinder:local-profile:synthetic-candidate"))
SAFETY_NOTE = (
    "Synthetic local candidate workspace only. Do not enter a real CV, private contact data, "
    "or production candidate evidence in this tranche."
)


class CandidateSafetyError(ValueError):
    """Raised when candidate workspace input violates synthetic-only guardrails."""


class CandidateWorkspaceService:
    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        audit_service: AuditEventService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._audit_service = audit_service or AuditEventService(session=session)

    def get_workspace(self) -> CandidateWorkspaceRead:
        self._ensure_seed_data()
        return CandidateWorkspaceRead(
            profile=self._profile_read(self._profile()),
            evidence=[self._evidence_read(row) for row in self._evidence_rows()],
            search_criteria=[self._criteria_read(row) for row in self._criteria_rows()],
            safety_note=SAFETY_NOTE,
        )

    def update_profile(self, request: CandidateProfileUpdate) -> CandidateProfileRead:
        _validate_synthetic_text(request.profile_name, request.summary)
        profile = self._profile()
        profile.profile_name = request.profile_name
        profile.summary = request.summary
        self._session.flush()
        self._audit_service.create_event(
            event_type="candidate.profile.updated",
            actor_type=ActorType.USER,
            actor_id=LOCAL_USER_ID,
            correlation_id=profile.id,
            payload={
                "profile_id": profile.id,
                "synthetic": True,
                "real_candidate_data": False,
            },
        )
        return self._profile_read(profile)

    def create_evidence(self, request: CandidateEvidenceCreate) -> CandidateEvidenceRead:
        _validate_synthetic_text(request.title, request.description)
        _validate_source_url(request.source_url)
        profile = self._profile()
        evidence = CandidateEvidence(
            id=str(uuid4()),
            candidate_profile_id=profile.id,
            evidence_type=request.evidence_type,
            title=request.title,
            description=request.description,
            source_url=request.source_url,
            verified_at=datetime.now(UTC),
        )
        self._session.add(evidence)
        self._session.flush()
        self._audit_service.create_event(
            event_type="candidate.evidence.created",
            actor_type=ActorType.USER,
            actor_id=LOCAL_USER_ID,
            correlation_id=profile.id,
            payload={
                "candidate_profile_id": profile.id,
                "evidence_id": evidence.id,
                "evidence_type": evidence.evidence_type,
                "synthetic": True,
                "real_candidate_data": False,
            },
        )
        return self._evidence_read(evidence)

    def create_document_record(
        self,
        request: CandidateDocumentRecordCreate,
    ) -> CandidateDocumentRecordRead:
        if not self._settings.candidate_vault_enabled:
            raise CandidateSafetyError("candidate vault is disabled by runtime configuration")
        _validate_document_record(request)
        user = self._user()
        now = datetime.now(UTC)
        record = CandidateDocumentRecord(
            id=str(uuid4()),
            user_id=user.id,
            document_type=request.document_type,
            display_name=request.display_name,
            storage_ref=request.storage_ref,
            content_sha256=request.content_sha256,
            byte_size=request.byte_size,
            mime_type=request.mime_type,
            consent_scope=request.consent_scope,
            consent_recorded_at=now,
            retention_delete_after=now + timedelta(days=request.retention_days),
            redaction_status="pending",
            extraction_approved=False,
        )
        self._session.add(record)
        self._session.flush()
        self._audit_service.create_event(
            event_type="candidate.document_record.created",
            actor_type=ActorType.USER,
            actor_id=user.id,
            correlation_id=record.id,
            payload={
                "document_record_id": record.id,
                "document_type": record.document_type,
                "content_sha256": record.content_sha256,
                "byte_size": record.byte_size,
                "mime_type": record.mime_type,
                "consent_scope": record.consent_scope,
                "redaction_status": record.redaction_status,
                "extraction_approved": False,
                "content_stored": False,
                "real_candidate_data": True,
            },
        )
        return self._document_record_read(record)

    def create_search_criteria(self, request: SearchCriteriaCreate) -> SearchCriteriaRead:
        _validate_synthetic_text(request.name, request.query, request.location)
        if (
            request.salary_min is not None
            and request.salary_max is not None
            and request.salary_min > request.salary_max
        ):
            raise CandidateSafetyError("salary_min must be less than or equal to salary_max")
        user = self._user()
        criteria = SearchCriteria(
            id=str(uuid4()),
            user_id=user.id,
            name=request.name,
            query=request.query,
            location=request.location,
            remote_type=request.remote_type,
            salary_min=request.salary_min,
            salary_max=request.salary_max,
        )
        self._session.add(criteria)
        self._session.flush()
        self._audit_service.create_event(
            event_type="candidate.search_criteria.created",
            actor_type=ActorType.USER,
            actor_id=user.id,
            correlation_id=criteria.id,
            payload={
                "search_criteria_id": criteria.id,
                "synthetic": True,
                "real_candidate_data": False,
            },
        )
        return self._criteria_read(criteria)

    def _ensure_seed_data(self) -> None:
        user = self._user()
        profile = self._profile()
        if not self._evidence_rows():
            self._session.add_all(
                [
                    CandidateEvidence(
                        id=str(uuid5(NAMESPACE_URL, "jobfinder:synthetic-evidence:api-design")),
                        candidate_profile_id=profile.id,
                        evidence_type="project",
                        title="Synthetic API design evidence",
                        description="Example evidence item for schema and provenance testing only.",
                        source_url="https://example.com/synthetic-api-design",
                        verified_at=datetime.now(UTC),
                    ),
                    CandidateEvidence(
                        id=str(uuid5(NAMESPACE_URL, "jobfinder:synthetic-evidence:python-sql")),
                        candidate_profile_id=profile.id,
                        evidence_type="skill",
                        title="Synthetic Python and SQL evidence",
                        description="Placeholder skill evidence; not derived from a real CV.",
                        source_url=None,
                        verified_at=datetime.now(UTC),
                    ),
                ]
            )
        if not self._criteria_rows():
            self._session.add(
                SearchCriteria(
                    id=str(uuid5(NAMESPACE_URL, "jobfinder:synthetic-criteria:backend")),
                    user_id=user.id,
                    name="Synthetic backend platform search",
                    query="backend platform roles using Python, APIs, and SQL",
                    location="Remote - UK",
                    remote_type="remote",
                    salary_min=None,
                    salary_max=None,
                )
            )
        self._session.flush()

    def _user(self) -> User:
        user = self._session.get(User, LOCAL_USER_ID)
        if user is not None:
            return user
        user = User(
            id=LOCAL_USER_ID,
            email="synthetic-candidate@local.jobfinder.synthetic",
            display_name="Synthetic Candidate",
        )
        self._session.add(user)
        self._session.flush()
        return user

    def _profile(self) -> CandidateProfile:
        profile = self._session.get(CandidateProfile, LOCAL_PROFILE_ID)
        if profile is not None:
            return profile
        profile = CandidateProfile(
            id=LOCAL_PROFILE_ID,
            user_id=self._user().id,
            profile_name="Synthetic Candidate Profile",
            summary="Synthetic profile for local workflow validation. No real CV data is stored.",
        )
        self._session.add(profile)
        self._session.flush()
        return profile

    def _evidence_rows(self) -> list[CandidateEvidence]:
        return list(
            self._session.scalars(
                select(CandidateEvidence)
                .where(CandidateEvidence.candidate_profile_id == LOCAL_PROFILE_ID)
                .order_by(CandidateEvidence.created_at, CandidateEvidence.id)
            ).all()
        )

    def _criteria_rows(self) -> list[SearchCriteria]:
        return list(
            self._session.scalars(
                select(SearchCriteria)
                .where(SearchCriteria.user_id == LOCAL_USER_ID)
                .order_by(SearchCriteria.created_at, SearchCriteria.id)
            ).all()
        )

    @staticmethod
    def _profile_read(profile: CandidateProfile) -> CandidateProfileRead:
        return CandidateProfileRead.model_validate(profile, from_attributes=True)

    @staticmethod
    def _evidence_read(evidence: CandidateEvidence) -> CandidateEvidenceRead:
        return CandidateEvidenceRead.model_validate(evidence, from_attributes=True)

    @staticmethod
    def _document_record_read(record: CandidateDocumentRecord) -> CandidateDocumentRecordRead:
        return CandidateDocumentRecordRead.model_validate(
            {
                "id": record.id,
                "user_id": record.user_id,
                "document_type": record.document_type,
                "display_name": record.display_name,
                "storage_ref": record.storage_ref,
                "content_sha256": record.content_sha256,
                "byte_size": record.byte_size,
                "mime_type": record.mime_type,
                "consent_scope": record.consent_scope,
                "consent_recorded_at": record.consent_recorded_at,
                "retention_delete_after": record.retention_delete_after,
                "redaction_status": record.redaction_status,
                "extraction_approved": record.extraction_approved,
                "content_stored": False,
                "synthetic": False,
                "created_at": record.created_at,
            }
        )

    @staticmethod
    def _criteria_read(criteria: SearchCriteria) -> SearchCriteriaRead:
        return SearchCriteriaRead.model_validate(criteria, from_attributes=True)


def _validate_synthetic_text(*values: str | None) -> None:
    joined = " ".join(value.casefold() for value in values if value)
    if not joined:
        return
    blocked_tokens = {"@", "phone", "address", "linkedin.com/in", "github.com/"}
    if any(token in joined for token in blocked_tokens):
        raise CandidateSafetyError("candidate workspace accepts synthetic placeholder text only")


def _validate_source_url(source_url: str | None) -> None:
    if source_url is None:
        return
    normalized = source_url.casefold()
    if not (
        normalized.startswith("https://example.com/")
        or normalized.startswith("https://example.test/")
    ):
        raise CandidateSafetyError("synthetic evidence source_url must use example.com/test")


def _validate_document_record(request: CandidateDocumentRecordCreate) -> None:
    if request.document_type == "credential":
        raise CandidateSafetyError("third-party credentials cannot be stored in candidate records")
    if not request.storage_ref.startswith("vault://"):
        raise CandidateSafetyError("candidate document storage_ref must use vault://")
    if request.mime_type not in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }:
        raise CandidateSafetyError("candidate document mime_type is not allowed")
    joined = f"{request.display_name} {request.storage_ref} {request.consent_scope}".casefold()
    blocked_content_markers = {
        "full cv text",
        "private candidate details",
        "password",
        "secret",
        "token",
        "cookie",
    }
    if any(marker in joined for marker in blocked_content_markers):
        raise CandidateSafetyError("document content and credentials must not be stored inline")
