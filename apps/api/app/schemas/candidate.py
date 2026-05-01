from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RemotePreference = Literal["remote", "hybrid", "onsite", "unknown"]
EvidenceType = Literal["skill", "project", "experience", "credential"]


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


class SearchCriteriaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=800)
    location: str | None = Field(default=None, max_length=240)
    remote_type: RemotePreference = "unknown"
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    synthetic: Literal[True] = True
