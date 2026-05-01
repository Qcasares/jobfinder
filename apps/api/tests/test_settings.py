from pytest import MonkeyPatch

from app.config import Settings


def test_settings_load_defaults() -> None:
    settings = Settings()

    assert settings.service_name == "jobfinder-api"
    assert settings.environment == "local"
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.audit_schema_version == 1
    assert settings.write_api_enabled is False
    assert settings.production_writes_allowed is True
    assert settings.cors_allowed_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]


def test_settings_accept_common_database_and_redis_env_names(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@db:5432/app")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/2")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/app"
    assert settings.redis_url == "redis://redis:6379/2"


def test_production_write_api_requires_explicit_opt_in() -> None:
    production_settings = Settings(environment="production")
    enabled_settings = Settings(environment="production", write_api_enabled=True)

    assert production_settings.production_writes_allowed is False
    assert enabled_settings.production_writes_allowed is True


def test_settings_accept_cors_origin_list_from_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["http://127.0.0.1:3000","http://localhost:3000"]',
    )

    settings = Settings()

    assert settings.cors_allowed_origins == [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]
