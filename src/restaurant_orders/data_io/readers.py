"""Streaming readers of CSV and JSON Lines files behind one Importer protocol."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

from restaurant_orders.data_io.exceptions import DataImportError

FIELDS = ("order_id", "dish", "category", "price", "quantity")

# One input record: raw field values by field name.
Row = dict[Any, Any]


class Importer(Protocol):
    """Reads records one by one together with their line numbers."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]: ...


class CsvImporter:
    """Reads a CSV file with a header line."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                missing = set(FIELDS) - set(reader.fieldnames or ())
                if missing:
                    raise DataImportError(f"У файлі {path} немає колонок: {', '.join(sorted(missing))}.")
                for row in reader:
                    yield reader.line_num, row
        except OSError as error:
            raise DataImportError(f"Не вдалося прочитати файл {path}.") from error
        except (csv.Error, UnicodeDecodeError) as error:
            raise DataImportError(f"Файл {path} не є коректним CSV у UTF-8.") from error


class JsonLinesImporter:
    """Reads a JSON Lines file: one JSON object per line."""

    def read(self, path: Path) -> Iterator[tuple[int, Row]]:
        try:
            with path.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise DataImportError(f"Некоректний JSON у рядку {line_number} файлу {path}.") from error
                    if not isinstance(data, dict):
                        raise DataImportError(f"Рядок {line_number} файлу {path} не є JSON-об'єктом.")
                    yield line_number, data
        except OSError as error:
            raise DataImportError(f"Не вдалося прочитати файл {path}.") from error


IMPORTERS: dict[str, Importer] = {".csv": CsvImporter(), ".jsonl": JsonLinesImporter()}


def importer_for(path: Path) -> Importer:
    """Choose the importer by the file extension."""
    try:
        return IMPORTERS[path.suffix.lower()]
    except KeyError as error:
        raise DataImportError(f"Формат {path.suffix or '(без розширення)'} не підтримується.") from error
