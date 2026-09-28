"""Import process: read -> validate -> export with strict or tolerant policy."""

import logging
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass

from restaurant_orders.data_io.config import AppConfig
from restaurant_orders.data_io.exceptions import RecordValidationError
from restaurant_orders.data_io.exporters import errors_csv, export_json, export_summary
from restaurant_orders.data_io.files import logged_operation
from restaurant_orders.data_io.readers import importer_for
from restaurant_orders.data_io.validators import validate_row
from restaurant_orders.models import OrderItemRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ImportStatistics:
    """Counters of one import run."""

    total: int = 0
    valid: int = 0
    invalid: int = 0
    exported: int = 0


def valid_records(
    config: AppConfig, statistics: ImportStatistics, on_error: Callable[[RecordValidationError], None]
) -> Iterator[OrderItemRecord]:
    """Yield valid records; skip invalid ones (tolerant) or stop on the first one (strict)."""
    for line_number, row in importer_for(config.input_path).read(config.input_path):
        statistics.total += 1
        try:
            record = validate_row(line_number, row, config.rules)
        except RecordValidationError as error:
            statistics.invalid += 1
            if not config.skip_invalid:
                raise
            on_error(error)
            logger.warning("Некоректний запис пропущено, %s", error)
            continue
        statistics.valid += 1
        yield record


def run_import(config: AppConfig, statistics: ImportStatistics) -> None:
    """Import the input file and write valid records, invalid records and the summary."""
    mode = "tolerant" if config.skip_invalid else "strict"
    with logged_operation(f"Імпорт {config.input_path} (режим {mode})"):
        with errors_csv(config.errors_path) as write_error:
            records = valid_records(config, statistics, write_error)
            statistics.exported = export_json(records, config.output_path)
        summary = {"mode": mode, "input": str(config.input_path), **asdict(statistics)}
        export_summary(summary, config.summary_path)
    logger.info(
        "Статистика: всього %d, коректних %d, некоректних %d, експортовано %d",
        statistics.total, statistics.valid, statistics.invalid, statistics.exported,
    )
