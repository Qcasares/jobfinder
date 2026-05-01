from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "jobfinder-api"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+psycopg://jobfinder:jobfinder@localhost:5432/jobfinder",
        validation_alias=AliasChoices("JOBFINDER_API_DATABASE_URL", "DATABASE_URL"),
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("JOBFINDER_API_REDIS_URL", "REDIS_URL"),
    )
    audit_schema_version: int = Field(default=1, ge=1)
    write_api_enabled: bool = Field(default=False)
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        validation_alias=AliasChoices("JOBFINDER_API_CORS_ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )

    model_config = SettingsConfigDict(
        env_prefix="JOBFINDER_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @property
    def production_writes_allowed(self) -> bool:
        return self.environment != "production" or self.write_api_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
