from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalRequestStatus = Literal["pending", "approved", "rejected", "needs_changes"]
ApprovalDecisionStatus = Literal["approved", "rejected", "needs_changes"]
ApprovalRequestType = Literal["manual_review"]


class ApprovalSafety(BaseModel):
    submit_performed: bool = False
    autofill_performed: bool = False
    application_created: bool = False

    model_config = ConfigDict(frozen=True)


class ApprovalRequestCreate(BaseModel):
    review_item_id: str = Field(min_length=1, max_length=240)
    requester_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1)
    request_type: ApprovalRequestType = "manual_review"


class ApprovalDecisionCreate(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=200)
    decision: ApprovalDecisionStatus
    reason: str = Field(min_length=1)


class ApprovalRequestRead(BaseModel):
    id: str
    review_item_id: str
    job_posting_id: str
    requester_id: str
    reviewer_id: str | None
    request_type: ApprovalRequestType
    status: ApprovalRequestStatus
    reason: str
    requested_at: datetime
    resolved_at: datetime | None
    safety: ApprovalSafety = Field(default_factory=ApprovalSafety)

    model_config = ConfigDict(frozen=True)


class ApprovalRequestSummary(BaseModel):
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    approved: int = Field(ge=0)
    rejected: int = Field(ge=0)
    needs_changes: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
