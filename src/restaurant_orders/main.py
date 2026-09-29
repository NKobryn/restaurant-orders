"""Main entry point: the production REST API service (laboratory work 10).

restaurant-orders (or python -m restaurant_orders.main): settings from environment variables and .env,
logging with LOG_LEVEL, database migrations, then the API server (uvicorn) on HOST:PORT.
"""

import logging

import uvicorn

from restaurant_orders import __version__
from restaurant_orders.config import configure_logging, get_settings
from restaurant_orders.persistence.database import create_database_engine
from restaurant_orders.persistence.migrations import ALEMBIC_INI, upgrade_database
from restaurant_orders.persistence.models import Order

logger = logging.getLogger("restaurant_orders")


def prepare_database(url: str) -> str:
    """Apply Alembic migrations if alembic.ini is here (project, Docker image); otherwise create the tables."""
    if ALEMBIC_INI.exists():
        upgrade_database(url)
        return "alembic upgrade head"
    engine = create_database_engine(url)
    Order.metadata.create_all(engine)
    engine.dispose()
    return "create_all"


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "Restaurant Orders %s, environment: %s, log level: %s", __version__, settings.environment, settings.log_level
    )
    method = prepare_database(settings.database_url)
    logger.info("Database %s is ready (%s)", settings.database_url, method)
    uvicorn.run(
        "restaurant_orders.api.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )


if __name__ == "__main__":
    main()
