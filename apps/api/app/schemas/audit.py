from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

type JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
type FrozenJsonValue = (
    str
    | int
    | float
    | bool
    | None
    | tuple["FrozenJsonValue", ...]
    | Mapping[str, "FrozenJsonValue"]
)
type FrozenJsonObject = Mapping[str, FrozenJsonValue]


def freeze_json(value: JsonValue) -> FrozenJsonValue:
    if isinstance(value, dict):
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_json(item) for item in value)
    return value


def thaw_json(value: FrozenJsonValue | JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [thaw_json(item) for item in value]
    return value


class ActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    WORKER = "worker"


class AuditEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=160)
    actor_type: ActorType
    actor_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=120)
    payload: dict[str, JsonValue] = Field(default_factory=dict)


class AuditEventRead(AuditEventCreate):
    id: str
    schema_version: int = Field(ge=1)
    previous_hash: str | None
    event_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def freeze_payload(self) -> AuditEventRead:
        object.__setattr__(self, "payload", freeze_json(self.payload))
        return self

    @field_serializer("payload")
    def serialize_payload(self, payload: FrozenJsonObject, _: Any) -> JsonValue:
        return thaw_json(payload)
