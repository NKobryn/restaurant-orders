"""Tests added after reading the coverage report: error paths and small branches that were not executed."""

from collections.abc import Callable
from pathlib import Path

import pytest

from restaurant_orders.console import print_order, read_positive_int
from restaurant_orders.data_io.config import load_config
from restaurant_orders.data_io.exceptions import ConfigurationError, DataExportError, DataImportError, RecordValidationError
from restaurant_orders.data_io.exporters import errors_csv, export_json, export_summary
from restaurant_orders.data_io.readers import CsvImporter, JsonLinesImporter
from restaurant_orders.data_io.validators import validate_row
from restaurant_orders.decorators import measure_time
from restaurant_orders.domain.adapters import DemoPaymentGateway
from restaurant_orders.domain.dto import menu_from_payloads
from restaurant_orders.domain.models import Order
from restaurant_orders.domain.repositories import InMemoryRepository
from restaurant_orders.domain.value_objects import Money
from restaurant_orders.models import Dish as SimpleDish
from restaurant_orders.models import Order as SimpleOrder
from restaurant_orders.models import OrderItemRecord, OrderSummary
from restaurant_orders.services import calculate_average_order_value
from restaurant_orders.stream.filters import find_first


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("", "- just\n- a list\n", "словником"),
        ("price_range: {min: 20, max: 500}", "price_range: {min: abc, max: 500}", "структура"),
        ("logging: {level: INFO", "logging: {level: LOUD", "рівень логування"),
        ("processing:", "processing_typo:", "processing"),
    ],
    ids=["not-a-dictionary", "text-instead-of-number", "unknown-log-level", "missing-section"],
)
def test_invalid_configuration_values(import_files: Callable[..., Path], old: str, new: str, message: str) -> None:
    path = import_files("")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old, new, 1) if old else new, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        load_config(path)


def test_exporters_report_missing_folder(tmp_path: Path) -> None:
    missing = tmp_path / "absent" / "file"
    with pytest.raises(DataExportError):
        export_json([], missing)
    with pytest.raises(DataExportError):
        export_summary({"total": 0}, missing)
    with pytest.raises(DataExportError):
        with errors_csv(missing):
            pass


@pytest.mark.parametrize("importer", [CsvImporter(), JsonLinesImporter()], ids=["csv", "jsonl"])
def test_missing_input_file(importer: CsvImporter | JsonLinesImporter, tmp_path: Path) -> None:
    with pytest.raises(DataImportError) as error_info:
        list(importer.read(tmp_path / "absent"))
    assert isinstance(error_info.value.__cause__, FileNotFoundError)


def test_csv_in_wrong_encoding(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_bytes("order_id,dish,category,price,quantity\n1,Борщ,Перші страви,95,1\n".encode("cp1251"))
    with pytest.raises(DataImportError, match="UTF-8"):
        list(CsvImporter().read(path))


def test_json_lines_skip_blank_lines_and_reject_arrays(tmp_path: Path) -> None:
    path = tmp_path / "orders.jsonl"
    path.write_text('{"order_id": 1}\n\n[1, 2]\n', encoding="utf-8")
    records = JsonLinesImporter().read(path)
    assert next(records) == (1, {"order_id": 1})
    with pytest.raises(DataImportError, match="рядок 3|Рядок 3"):
        next(records)


def test_record_with_extra_field_is_invalid() -> None:
    from restaurant_orders.data_io.config import ValidationRules

    rules = ValidationRules(frozenset({"Напої"}), 20.0, 500.0)
    row = {"order_id": "1", "dish": "Узвар", "category": "Напої", "price": "45", "quantity": "1", None: ["x"]}
    with pytest.raises(RecordValidationError, match="Забагато полів"):
        validate_row(2, row, rules)


@pytest.mark.parametrize(
    "create",
    [
        lambda: SimpleDish(" ", "Напої", 45.0),
        lambda: SimpleDish("Узвар", " ", 45.0),
        lambda: SimpleOrder(0),
        lambda: OrderItemRecord(0, "Узвар", "Напої", 45.0, 1),
        lambda: Money(10.0, ""),
    ],
    ids=["blank-dish-name", "blank-category", "order-number-zero", "record-order-id-zero", "empty-currency"],
)
def test_model_validation_errors(create: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        create()


def test_small_helpers_on_empty_or_missing_data() -> None:
    assert calculate_average_order_value([]) == 0.0
    record = OrderItemRecord(1, "Узвар", "Напої", 45.0, 1)
    assert find_first([OrderSummary(1, 1, 45.0, record)], lambda order: order.total > 100) is None
    repository = InMemoryRepository[Order]()
    repository.add(Order(1))
    assert len(repository) == 1
    menu = menu_from_payloads([{"id": 2, "name": "Бульйон", "category": "Перші страви", "price": 70.0,
                                "currency": "UAH"}])
    assert [dish.name for dish in menu] == ["Бульйон"]


def test_measure_time_prints_duration(capsys: pytest.CaptureFixture[str]) -> None:
    assert measure_time(lambda: 42)() == 42
    assert capsys.readouterr().out.startswith("[час] <lambda>:")


def test_demo_payment_gateway_numbers_payments(capsys: pytest.CaptureFixture[str]) -> None:
    gateway = DemoPaymentGateway()
    assert [gateway.pay(1, Money(10.0)), gateway.pay(2, Money(20.0))] == ["PAY-001", "PAY-002"]
    assert "замовлення №2: 20.00 UAH → PAY-002" in capsys.readouterr().out


def test_console_helpers(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    print_order(SimpleOrder(5))
    answers = iter(["0", "7"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert read_positive_int("> ") == 7
    output = capsys.readouterr().out
    assert "Страв ще не додано." in output
    assert "Введіть ціле додатне число." in output
