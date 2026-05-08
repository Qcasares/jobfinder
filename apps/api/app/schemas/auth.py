from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OperatorTokenRequest(BaseModel):
    login_secret: str = Field(min_length=1)
    actor_id: str = Field(default="operator", min_length=1, max_length=200)


class OperatorTokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"
    actor_id: str
    role: str = "operator"
    expires_at: datetime

    model_config = ConfigDict(frozen=True)
