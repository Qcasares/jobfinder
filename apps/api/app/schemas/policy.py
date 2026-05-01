from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PolicyAction(StrEnum):
    DISCOVER = "discover"
    EXTRACT = "extract"
    DRAFT = "draft"
    AUTOFILL = "autofill"
    SUBMIT = "submit"


class PolicyStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    NOT_ALLOWED = "not_allowed"
    REVIEW_REQUIRED = "review_required"
    UNKNOWN_SOURCE = "unknown_source"


class PolicyDecision(BaseModel):
    allowed: bool
    action: PolicyAction
    status: PolicyStatus
    reason: str = Field(min_length=1)
    source_id: str
    policy_id: str | None

    model_config = ConfigDict(frozen=True)
