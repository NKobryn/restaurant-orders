"""Main entry point: reliable import and export of orders (laboratory work 5).

Usage: python -m restaurant_orders.main [config.yaml]
"""

import logging
import sys
from pathlib import Path

from restaurant_orders.data_io.config import load_config
from restaurant_orders.data_io.exceptions import ApplicationError, ConfigurationError
from restaurant_orders.data_io.logging_config import configure_logging
from restaurant_orders.data_io.services import ImportStatistics, run_import

logger = logging.getLogger("restaurant_orders.main")


def main(argv: list[str] | None = None) -> int:
    """Run the import; return 0 on success and 1 on a critical error."""
    arguments = sys.argv[1:] if argv is None else argv
    config_path = Path(arguments[0]) if arguments else Path("config.yaml")
    print("ІМПОРТ ТА ЕКСПОРТ ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №5, варіант №11)")
    try:
        config = load_config(config_path)
    except ConfigurationError as error:
        print(f"CRITICAL | Конфігурація: {error} (причина: {error.__cause__!r})", file=sys.stderr)
        return 1
    configure_logging(config.logging)
    statistics = ImportStatistics()
    try:
        run_import(config, statistics)
    except ApplicationError as error:
        logger.critical("Імпорт зупинено: %s (причина: %r)", error, error.__cause__)
        print(f"Оброблено {statistics.total}, коректних {statistics.valid}, некоректних {statistics.invalid}; "
              f"{config.output_path} не змінено.")
        return 1
    print(f"Результат: {config.output_path}, помилки: {config.errors_path}, підсумок: {config.summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
