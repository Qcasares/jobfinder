from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FinalReviewPacketStatus = Literal["denied", "review_required"]
OperatorConfirmation = Literal["ready_for_final_review"]


class FinalReviewPacketRequest(BaseModel):
    autofill_packet_id: str = Field(min_length=1, max_length=36)
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)
    operator_confirmation: OperatorConfirmation
    rollback_notes: str | None = Field(default=None, max_length=1000)


class FinalReviewPacketFailure(BaseModel):
    reason: str
    detail: str

    model_config = ConfigDict(frozen=True)


class FinalReviewPacketSafety(BaseModel):
    final_confirmation_recorded: bool = False
    submit_policy_checked: bool = False
    submit_performed: bool = False
    external_side_effect: bool = False
    application_created: bool = False

    model_config = ConfigDict(frozen=True)


class FinalReviewPacketRead(BaseModel):
    id: str
    autofill_packet_id: str
    target_url: str
    requested_by: str
    operator_confirmation: OperatorConfirmation | None = None
    rollback_notes: str | None = None
    status: FinalReviewPacketStatus
    approval_required: bool = True
    safety: FinalReviewPacketSafety = Field(default_factory=FinalReviewPacketSafety)
    failure: FinalReviewPacketFailure | None = None
    created_at: datetime

    model_config = ConfigDict(frozen=True)
