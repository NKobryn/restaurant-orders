"""Database engine, sessions and the declarative base of ORM models."""

import os
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///restaurant.db"

# Stable constraint names make migrations reproducible.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


class Base(DeclarativeBase):
    """Base class of all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def database_url() -> str:
    """Return DATABASE_URL from the environment or the default SQLite file."""
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """SQLite checks FOREIGN KEY constraints only after this PRAGMA on every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database_engine(url: str | None = None) -> Engine:
    """Create an engine; for SQLite foreign keys are switched on."""
    engine = create_engine(url or database_url())
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", enable_sqlite_foreign_keys)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a factory of sessions bound to the engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)
