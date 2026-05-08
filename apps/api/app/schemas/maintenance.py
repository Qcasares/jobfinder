from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MigrationUpgradeRead(BaseModel):
    status: str
    revision: str | None
    target: str

    model_config = ConfigDict(frozen=True)
