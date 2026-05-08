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
    operator_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("JOBFINDER_API_OPERATOR_API_KEY", "OPERATOR_API_KEY"),
    )
    operator_login_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "JOBFINDER_API_OPERATOR_LOGIN_SECRET",
            "OPERATOR_LOGIN_SECRET",
        ),
    )
    operator_token_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "JOBFINDER_API_OPERATOR_TOKEN_SECRET",
            "OPERATOR_TOKEN_SECRET",
        ),
    )
    operator_token_ttl_seconds: int = Field(default=28_800, ge=300, le=86_400)
    audit_schema_version: int = Field(default=1, ge=1)
    write_api_enabled: bool = Field(default=False)
    live_discovery_enabled: bool = Field(default=False)
    live_search_discovery_enabled: bool = Field(default=False)
    live_discovery_timeout_seconds: float = Field(default=8.0, gt=0)
    live_discovery_max_bytes: int = Field(default=1_000_000, ge=1024)
    candidate_vault_enabled: bool = Field(default=False)
    candidate_vault_storage_prefix: str = Field(default="vault://candidate-documents/")
    candidate_vault_kms_key_id: str = Field(default="")
    llm_drafting_enabled: bool = Field(default=False)
    autofill_packets_enabled: bool = Field(default=False)
    submission_packets_enabled: bool = Field(default=False)
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
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def production_writes_allowed(self) -> bool:
        return self.environment != "production" or self.write_api_enabled

    @property
    def production_operator_auth_required(self) -> bool:
        return self.environment == "production"

    @property
    def operator_auth_configured(self) -> bool:
        return bool(self.operator_api_key)

    @property
    def operator_session_auth_configured(self) -> bool:
        return bool(self.operator_login_secret and self.operator_token_secret)

    @property
    def candidate_vault_encrypted_storage_configured(self) -> bool:
        return bool(
            self.candidate_vault_enabled
            and self.candidate_vault_storage_prefix.strip()
            and self.candidate_vault_kms_key_id.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
