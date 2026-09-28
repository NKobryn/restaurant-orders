"""Running Alembic migrations from Python code."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text

ALEMBIC_INI = Path("alembic.ini")


def alembic_config(url: str, ini_path: Path = ALEMBIC_INI) -> Config:
    """Alembic configuration for the given database URL (logging of alembic is left to the caller)."""
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(ini_path.parent / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


def upgrade_database(url: str, revision: str = "head", ini_path: Path = ALEMBIC_INI) -> None:
    """Apply migrations up to the revision (alembic upgrade)."""
    command.upgrade(alembic_config(url, ini_path), revision)


def downgrade_database(url: str, revision: str, ini_path: Path = ALEMBIC_INI) -> None:
    """Roll migrations back to the revision (alembic downgrade)."""
    command.downgrade(alembic_config(url, ini_path), revision)


def current_revision(engine: Engine) -> str | None:
    """Revision stored by Alembic in the alembic_version table."""
    if not inspect(engine).has_table("alembic_version"):
        return None
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
    return None if version is None else str(version)
