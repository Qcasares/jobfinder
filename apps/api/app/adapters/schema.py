from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RawJobPosting(BaseModel):
    source: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    application_url: str = Field(min_length=1)
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    locations: tuple[str, ...] = ()
    remote_type: str | None = None
    employment_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = Field(default=None, min_length=3, max_length=3)
    posted_date: date | None = None
    valid_through: date | None = None
    extraction_method: str = Field(min_length=1)
    raw_payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    model_config = ConfigDict(frozen=True)

    @field_validator(
        "source",
        "source_url",
        "application_url",
        "external_id",
        "title",
        "company",
        "remote_type",
        "employment_type",
        "extraction_method",
        mode="before",
    )
    @classmethod
    def _strip_optional_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("locations", mode="before")
    @classmethod
    def _normalize_locations(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            values: tuple[str, ...] = (value,)
        elif isinstance(value, list | tuple):
            values = tuple(str(item) for item in value)
        else:
            values = ()
        return tuple(location.strip() for location in values if location.strip())

    @field_validator("salary_currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @model_validator(mode="after")
    def _validate_salary_range(self) -> Self:
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must be less than or equal to salary_max")
        return self
