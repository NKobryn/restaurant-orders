"""Export of valid records, invalid records and the summary."""

import csv
import json
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from restaurant_orders.data_io.exceptions import DataExportError, RecordValidationError
from restaurant_orders.data_io.files import atomic_write
from restaurant_orders.models import OrderItemRecord


def export_json(records: Iterable[OrderItemRecord], path: Path) -> int:
    """Write records as a JSON array one by one (streaming) and atomically; return their count."""
    count = 0
    try:
        with atomic_write(path) as file:
            file.write("[\n")
            for record in records:
                if count:
                    file.write(",\n")
                file.write("  " + json.dumps(asdict(record), ensure_ascii=False))
                count += 1
            file.write("\n]\n")
    except OSError as error:
        raise DataExportError(f"Не вдалося записати {path}.") from error
    return count


@contextmanager
def errors_csv(path: Path) -> Iterator[Callable[[RecordValidationError], None]]:
    """Open an atomic CSV of invalid records and give a function that writes one error at once."""
    try:
        with atomic_write(path) as file:
            writer = csv.writer(file)
            writer.writerow(["line_number", "field", "message"])

            def write_error(error: RecordValidationError) -> None:
                writer.writerow([error.line_number, error.field or "", error.args[0]])

            yield write_error
    except OSError as error:
        raise DataExportError(f"Не вдалося записати {path}.") from error


def export_summary(summary: dict[str, Any], path: Path) -> None:
    """Write the import summary as a JSON object."""
    try:
        with atomic_write(path) as file:
            json.dump(summary, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except OSError as error:
        raise DataExportError(f"Не вдалося записати {path}.") from error
