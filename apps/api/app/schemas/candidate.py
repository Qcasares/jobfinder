from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RemotePreference = Literal["remote", "hybrid", "onsite", "unknown"]
EvidenceType = Literal["skill", "project", "experience", "credential"]
CandidateDocumentType = Literal[
    "cv",
    "cover_letter",
    "portfolio",
    "certificate",
    "credential",
    "other",
]


class CandidateProfileRead(BaseModel):
    id: str
    user_id: str
    profile_name: str
    summary: str | None
    synthetic: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(frozen=True)


class CandidateEvidenceRead(BaseModel):
    id: str
    candidate_profile_id: str
    evidence_type: EvidenceType
    title: str
    description: str | None
    source_url: str | None
    verified_at: datetime | None
    synthetic: bool = True
    created_at: datetime

    model_config = ConfigDict(frozen=True)


class CandidateDocumentRecordRead(BaseModel):
    id: str
    user_id: str
    document_type: CandidateDocumentType
    display_name: str
    storage_ref: str
    content_sha256: str
    byte_size: int
    mime_type: str
    consent_scope: str
    consent_recorded_at: datetime
    retention_delete_after: datetime
    redaction_status: str
    extraction_approved: bool = False
    content_stored: bool = False
    synthetic: bool = False
    created_at: datetime

    model_config = ConfigDict(frozen=True)


class CandidateDocumentExportRead(BaseModel):
    records: list[CandidateDocumentRecordRead]
    content_included: Literal[False] = False
    export_note: str

    model_config = ConfigDict(frozen=True)


class CandidateDocumentDeleteRead(BaseModel):
    id: str
    deleted: bool
    content_deleted: Literal[False] = False

    model_config = ConfigDict(frozen=True)


class SearchCriteriaRead(BaseModel):
    id: str
    user_id: str
    name: str
    query: str
    location: str | None
    remote_type: RemotePreference
    salary_min: int | None
    salary_max: int | None
    synthetic: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(frozen=True)


class CandidateWorkspaceRead(BaseModel):
    profile: CandidateProfileRead
    evidence: list[CandidateEvidenceRead]
    search_criteria: list[SearchCriteriaRead]
    safety_note: str

    model_config = ConfigDict(frozen=True)


class CandidateProfileUpdate(BaseModel):
    profile_name: str = Field(min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=1200)
    synthetic: Literal[True] = True


class CandidateEvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=1200)
    source_url: str | None = Field(default=None, max_length=500)
    synthetic: Literal[True] = True


class CandidateDocumentRecordCreate(BaseModel):
    document_type: CandidateDocumentType
    display_name: str = Field(min_length=1, max_length=240)
    storage_ref: str = Field(min_length=1, max_length=500)
    content_sha256: str = Field(min_length=64, max_length=64)
    byte_size: int = Field(gt=0, le=25_000_000)
    mime_type: str = Field(min_length=1, max_length=120)
    consent_scope: str = Field(min_length=1, max_length=120)
    retention_days: int = Field(ge=1, le=365)

    @field_validator("content_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.casefold()
        if any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("content_sha256 must be lowercase hexadecimal")
        return normalized


class SearchCriteriaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=800)
    location: str | None = Field(default=None, max_length=240)
    remote_type: RemotePreference = "unknown"
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    synthetic: Literal[True] = True
