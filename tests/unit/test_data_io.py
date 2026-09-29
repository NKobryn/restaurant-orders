"""Unit tests for reliable import and export of orders."""

import io
import json
import logging
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from restaurant_orders.data_io.app import main
from restaurant_orders.data_io.config import ValidationRules, load_config
from restaurant_orders.data_io.exceptions import (
    ApplicationError,
    ConfigurationError,
    DataImportError,
    RecordValidationError,
)
from restaurant_orders.data_io.files import atomic_write
from restaurant_orders.data_io.readers import CsvImporter, importer_for
from restaurant_orders.data_io.services import ImportStatistics, run_import
from restaurant_orders.data_io.validators import validate_row

RULES = ValidationRules(frozenset({"Перші страви", "Напої"}), 20.0, 500.0)
HEADER = "order_id,dish,category,price,quantity\n"
CSV_TEXT = HEADER + "1,Борщ,Перші страви,95,2\n2,Узвар,Напої,0,1\n3,Узвар,Напої,45,1\n"
CONFIG_TEXT = """schema_version: 1
input: {path: INPUT}
output: {path: DIR/orders.json, errors_path: DIR/invalid.csv, summary_path: DIR/summary.json}
processing:
  skip_invalid: SKIP
  allowed_categories: [Перші страви, Напої]
  price_range: {min: 20, max: 500}
logging: {level: INFO, path: DIR/logs/import.log}
"""


def row(
    order_id: str = "1", dish: str = "Борщ", category: str = "Перші страви", price: str = "95", quantity: str = "1"
) -> dict[str, str]:
    """Create a raw record for validation tests."""
    return {"order_id": order_id, "dish": dish, "category": category, "price": price, "quantity": quantity}


class FolderTestCase(unittest.TestCase):
    """Base class with a temporary folder and helpers for files."""

    def setUp(self) -> None:
        self.folder_manager = tempfile.TemporaryDirectory()
        self.folder = Path(self.folder_manager.name)
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)
        self.folder_manager.cleanup()

    def write(self, name: str, text: str) -> Path:
        """Write a UTF-8 file into the temporary folder."""
        path = self.folder / name
        path.write_text(text, encoding="utf-8")
        return path

    def config_file(self, skip_invalid: bool = True, input_name: str = "orders.csv") -> Path:
        """Write config.yaml that points to files in the temporary folder."""
        text = CONFIG_TEXT.replace("INPUT", str(self.folder / input_name)).replace("DIR", str(self.folder))
        return self.write("config.yaml", text.replace("SKIP", "true" if skip_invalid else "false"))


class ConfigTest(FolderTestCase):
    """Tests for loading and validating the configuration."""

    def test_loads_valid_configuration(self) -> None:
        self.write("orders.csv", CSV_TEXT)
        config = load_config(self.config_file())
        self.assertTrue(config.skip_invalid)
        self.assertEqual(config.rules.allowed_categories, frozenset({"Перші страви", "Напої"}))
        self.assertEqual(config.rules.max_price, 500.0)

    def test_missing_file_and_bad_yaml_keep_the_cause(self) -> None:
        with self.assertRaises(ConfigurationError) as missing:
            load_config(self.folder / "absent.yaml")
        self.assertIsInstance(missing.exception.__cause__, FileNotFoundError)
        with self.assertRaises(ConfigurationError):
            load_config(self.write("bad.yaml", "processing: [\n"))

    def test_wrong_structure_and_values_are_rejected(self) -> None:
        self.write("orders.csv", CSV_TEXT)
        good = self.config_file().read_text(encoding="utf-8")
        wrong_texts = [
            good.replace("schema_version: 1", "schema_version: 2"),
            good.replace("max: 500", "max: 10"),
            good.replace("allowed_categories: [Перші страви, Напої]", "allowed_categories: []"),
            good.replace(str(self.folder / "orders.csv"), str(self.folder / "absent.csv")),
            good.replace(f"{self.folder}/orders.json", f"{self.folder}/nope/orders.json"),
        ]
        for text in wrong_texts:
            with self.assertRaises(ConfigurationError):
                load_config(self.write("wrong.yaml", text))


class ReadAndValidateTest(FolderTestCase):
    """Tests for readers and record validation."""

    def test_valid_row_becomes_record(self) -> None:
        record = validate_row(2, row(price="95.5", quantity="2"), RULES)
        self.assertEqual((record.order_id, record.price, record.quantity), (1, 95.5, 2))

    def test_invalid_rows_name_line_and_field(self) -> None:
        cases = [
            (row(order_id="abc"), "order_id"),
            (row(dish="  "), "dish"),
            (row(category="Суші"), "category"),
            (row(price="600"), "price"),
            (row(quantity="0"), "quantity"),
        ]
        for data, field in cases:
            with self.assertRaises(RecordValidationError) as context:
                validate_row(5, data, RULES)
            self.assertEqual((context.exception.line_number, context.exception.field), (5, field))

    def test_conversion_error_is_chained(self) -> None:
        with self.assertRaises(RecordValidationError) as context:
            validate_row(2, row(price="wrong"), RULES)
        self.assertIsInstance(context.exception.__cause__, ValueError)

    def test_csv_reader_streams_rows_with_line_numbers(self) -> None:
        path = self.write("orders.csv", CSV_TEXT)
        self.assertEqual([number for number, _ in CsvImporter().read(path)], [2, 3, 4])

    def test_reader_errors(self) -> None:
        with self.assertRaises(DataImportError):
            list(CsvImporter().read(self.write("short.csv", "order_id,dish\n1,Борщ\n")))
        with self.assertRaises(DataImportError) as context:
            list(importer_for(Path("x.jsonl")).read(self.write("x.jsonl", '{"order_id": 1}\n{broken\n')))
        self.assertIsNotNone(context.exception.__cause__)
        with self.assertRaises(DataImportError):
            importer_for(Path("orders.xml"))


class ImportTest(FolderTestCase):
    """Tests for the import process, atomic output and main()."""

    def test_atomic_write_keeps_old_file_on_error(self) -> None:
        target = self.write("result.json", "old")
        with self.assertRaises(RuntimeError):
            with atomic_write(target) as file:
                file.write("new")
                raise RuntimeError("збій")
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        self.assertFalse((self.folder / "result.json.tmp").exists())

    def test_tolerant_import_writes_all_outputs(self) -> None:
        self.write("orders.csv", CSV_TEXT)
        statistics = ImportStatistics()
        run_import(load_config(self.config_file()), statistics)
        self.assertEqual((statistics.total, statistics.valid, statistics.invalid, statistics.exported), (3, 2, 1, 2))
        exported = json.loads((self.folder / "orders.json").read_text(encoding="utf-8"))
        self.assertEqual([item["order_id"] for item in exported], [1, 3])
        errors = (self.folder / "invalid.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(errors[1].split(",")[:2], ["3", "price"])
        summary = json.loads((self.folder / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["mode"], "tolerant")

    def test_strict_import_stops_and_keeps_previous_output(self) -> None:
        self.write("orders.csv", CSV_TEXT)
        self.write("orders.json", "[]\n")
        statistics = ImportStatistics()
        with self.assertRaises(RecordValidationError):
            run_import(load_config(self.config_file(skip_invalid=False)), statistics)
        self.assertEqual((statistics.total, statistics.invalid), (2, 1))
        self.assertEqual((self.folder / "orders.json").read_text(encoding="utf-8"), "[]\n")

    def test_json_lines_input_is_chosen_by_extension(self) -> None:
        self.write(
            "orders.jsonl", '{"order_id": 7, "dish": "Узвар", "category": "Напої", "price": 45, "quantity": 2}\n'
        )
        statistics = ImportStatistics()
        run_import(load_config(self.config_file(input_name="orders.jsonl")), statistics)
        self.assertEqual(statistics.exported, 1)

    def test_main_returns_exit_code(self) -> None:
        self.write("orders.csv", CSV_TEXT)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.config_file())]), 0)
            self.assertEqual(main([str(self.config_file(skip_invalid=False))]), 1)
            self.assertEqual(main([str(self.folder / "absent.yaml")]), 1)
        self.assertTrue(issubclass(ConfigurationError, ApplicationError))


if __name__ == "__main__":
    unittest.main()
