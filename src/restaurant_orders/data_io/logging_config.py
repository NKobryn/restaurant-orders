"""Logging to a file and to the console."""

import logging

from restaurant_orders.data_io.config import LoggingConfig

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(config: LoggingConfig) -> None:
    """Send log records of the given level to the log file and the console."""
    config.path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=config.level.upper(),
        format=LOG_FORMAT,
        handlers=[logging.FileHandler(config.path, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
