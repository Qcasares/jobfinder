from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))

    candidate_profiles: Mapped[list[CandidateProfile]] = relationship(back_populates="user")
    search_criteria: Mapped[list[SearchCriteria]] = relationship(back_populates="user")


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    profile_name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text())

    user: Mapped[User] = relationship(back_populates="candidate_profiles")
    evidence_items: Mapped[list[CandidateEvidence]] = relationship(
        back_populates="candidate_profile"
    )


class CandidateEvidence(Base):
    __tablename__ = "candidate_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    source_url: Mapped[str | None] = mapped_column(Text())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    candidate_profile: Mapped[CandidateProfile] = relationship(back_populates="evidence_items")


class CandidateDocumentRecord(Base):
    __tablename__ = "candidate_document_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    storage_ref: Mapped[str] = mapped_column(Text(), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    consent_scope: Mapped[str] = mapped_column(String(120), nullable=False)
    consent_recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    retention_delete_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    redaction_status: Mapped[str] = mapped_column(
        String(40), default="pending", nullable=False
    )
    extraction_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class SearchCriteria(TimestampMixin, Base):
    __tablename__ = "search_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    query: Mapped[str] = mapped_column(Text(), nullable=False)
    location: Mapped[str | None] = mapped_column(String(240))
    remote_type: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    salary_min: Mapped[int | None]
    salary_max: Mapped[int | None]

    user: Mapped[User] = relationship(back_populates="search_criteria")


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text())
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    policies: Mapped[list[SourcePolicy]] = relationship(back_populates="source")


class SourcePolicy(TimestampMixin, Base):
    __tablename__ = "source_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    denied_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship(back_populates="policies")
    evidence_items: Mapped[list[SourcePolicyEvidence]] = relationship(back_populates="policy")


class SourcePolicyEvidence(Base):
    __tablename__ = "source_policy_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_policy_id: Mapped[str] = mapped_column(
        ForeignKey("source_policies.id"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    url: Mapped[str | None] = mapped_column(Text())
    excerpt: Mapped[str | None] = mapped_column(Text())
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    policy: Mapped[SourcePolicy] = relationship(back_populates="evidence_items")


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_url: Mapped[str] = mapped_column(Text(), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    company: Mapped[str] = mapped_column(String(240), nullable=False)
    remote_type: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(80))
    salary_min: Mapped[int | None]
    salary_max: Mapped[int | None]
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    sources: Mapped[list[JobPostingSource]] = relationship(back_populates="job_posting")
    field_provenance: Mapped[list[JobFieldProvenance]] = relationship(back_populates="job_posting")
    scores: Mapped[list[JobScore]] = relationship(back_populates="job_posting")

    __table_args__ = (Index("ix_job_postings_company_title", "company", "title"),)


class JobPostingSource(Base):
    __tablename__ = "job_posting_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text(), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(240))
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="sources")

    __table_args__ = (
        UniqueConstraint("source_id", "source_url", name="uq_job_posting_sources_source_url"),
    )


class JobFieldProvenance(Base):
    __tablename__ = "job_field_provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str] = mapped_column(Text(), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    raw_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="field_provenance")


class JobScore(Base):
    __tablename__ = "job_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, index=True
    )
    search_criteria_id: Mapped[str] = mapped_column(
        ForeignKey("search_criteria.id"), nullable=False, index=True
    )
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    job_posting: Mapped[JobPosting] = relationship(back_populates="scores")


class DraftingRun(Base):
    __tablename__ = "drafting_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    draft_text: Mapped[str | None] = mapped_column(Text())
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    claim_mappings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    approval_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    failure_detail: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class AutofillPacket(Base):
    __tablename__ = "autofill_packets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    drafting_run_id: Mapped[str] = mapped_column(
        ForeignKey("drafting_runs.id"), nullable=False, index=True
    )
    target_url: Mapped[str] = mapped_column(Text(), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    approval_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    failure_detail: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class FinalReviewPacket(Base):
    __tablename__ = "final_review_packets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    autofill_packet_id: Mapped[str] = mapped_column(
        ForeignKey("autofill_packets.id"), nullable=False, index=True
    )
    target_url: Mapped[str] = mapped_column(Text(), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    operator_confirmation: Mapped[str] = mapped_column(String(80), nullable=False)
    rollback_notes: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    approval_required: Mapped[bool] = mapped_column(default=True, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    failure_detail: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ManualHandoffRecord(Base):
    __tablename__ = "manual_handoff_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text(), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="open", nullable=False, index=True)
    detection_detail: Mapped[str] = mapped_column(Text(), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[str | None] = mapped_column(Text())


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    review_item_id: Mapped[str | None] = mapped_column(String(240), index=True)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    requester_id: Mapped[str | None] = mapped_column(String(200))
    reviewer_id: Mapped[str | None] = mapped_column(String(200))
    request_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_posting_id: Mapped[str] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    approval_request_id: Mapped[str | None] = mapped_column(ForeignKey("approval_requests.id"))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    application_url: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    schema_version: Mapped[int] = mapped_column(nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
