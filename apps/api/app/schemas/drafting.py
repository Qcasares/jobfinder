from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DraftingStatus = Literal["denied", "failed", "review_required"]


class DraftingRequest(BaseModel):
    review_item_id: str = Field(min_length=1, max_length=240)
    requested_by: str = Field(default="local-operator", min_length=1, max_length=200)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


class DraftingClaimMapping(BaseModel):
    claim: str
    evidence_ids: tuple[str, ...]

    model_config = ConfigDict(frozen=True)


class DraftingFailure(BaseModel):
    reason: str
    detail: str

    model_config = ConfigDict(frozen=True)


class DraftingSafety(BaseModel):
    llm_called: bool = False
    autofill_performed: bool = False
    submit_performed: bool = False
    application_created: bool = False

    model_config = ConfigDict(frozen=True)


class DraftingRunRead(BaseModel):
    id: str
    review_item_id: str
    requested_by: str
    status: DraftingStatus
    model: str | None = None
    draft_text: str | None = None
    claim_mappings: tuple[DraftingClaimMapping, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    approval_required: bool = True
    safety: DraftingSafety = Field(default_factory=DraftingSafety)
    failure: DraftingFailure | None = None
    created_at: datetime

    model_config = ConfigDict(frozen=True)
