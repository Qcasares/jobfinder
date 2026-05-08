from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.policy import PolicyAction, PolicyDecision


class SourceUpsertRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=500)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    source_type: str = Field(default="job_board", min_length=1, max_length=80)
    base_url: str | None = Field(default=None, max_length=1000)


class SourcePolicyEvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=1000)
    excerpt: str | None = None
    expires_at: datetime | None = None


class SourcePolicyEvidenceRead(SourcePolicyEvidenceCreate):
    id: str
    captured_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SourcePolicySummary(BaseModel):
    id: str
    status: str
    reason: str
    allowed_actions: list[PolicyAction]
    denied_actions: list[PolicyAction]
    effective_from: datetime


class SourceRead(BaseModel):
    id: str
    name: str
    source_type: str
    base_url: str | None
    domain: str
    created_at: datetime
    updated_at: datetime
    latest_policy: SourcePolicySummary | None


class SourcePolicyRead(BaseModel):
    id: str
    source_id: str
    status: str
    reason: str
    allowed_actions: list[PolicyAction]
    denied_actions: list[PolicyAction]
    effective_from: datetime
    effective_to: datetime | None
    evidence_items: list[SourcePolicyEvidenceRead]


class SourcePolicyCheckRequest(BaseModel):
    action: PolicyAction
    domain: str | None = Field(default=None, min_length=1, max_length=500)
    source_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode="after")
    def require_domain_or_source_id(self) -> SourcePolicyCheckRequest:
        if self.domain is None and self.source_id is None:
            raise ValueError("domain or source_id is required")
        return self


class SourcePolicyCheckResponse(PolicyDecision):
    pass


class SourcePolicyAttachRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=36)
    status: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1)
    allowed_actions: list[PolicyAction] = Field(default_factory=list)
    denied_actions: list[PolicyAction] = Field(default_factory=list)
    evidence: list[SourcePolicyEvidenceCreate] = Field(default_factory=list)


def actions_from_raw(raw_actions: list[str]) -> list[PolicyAction]:
    return [PolicyAction(action) for action in raw_actions]


def model_dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
