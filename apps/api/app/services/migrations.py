from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from alembic import command
from app.config import Settings
from app.schemas.maintenance import MigrationUpgradeRead


def run_database_upgrade(settings: Settings, *, target: str = "head") -> MigrationUpgradeRead:
    app_root = Path(__file__).resolve().parents[2]
    config = Config(str(app_root / "alembic.ini"))
    config.set_main_option("script_location", str(app_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)

    command.upgrade(config, target)

    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()

    return MigrationUpgradeRead(status="upgraded", revision=revision, target=target)
