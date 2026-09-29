"""Dependencies injected into the endpoints: a database session per request."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from restaurant_orders.persistence.database import create_database_engine, create_session_factory, database_url


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    """One engine and session factory for the whole application (DATABASE_URL)."""
    return create_session_factory(create_database_engine(database_url()))


def get_session() -> Iterator[Session]:
    """Open a session for one HTTP request and close it afterwards."""
    with session_factory()() as session:
        yield session
