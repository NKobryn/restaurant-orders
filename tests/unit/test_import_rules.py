"""Unit tests of validation rules, exception chaining and configuration (pytest style)."""

from collections.abc import Callable
from pathlib import Path

import pytest

from restaurant_orders.data_io import config as config_module
from restaurant_orders.data_io.config import ValidationRules, default_config_path, load_config
from restaurant_orders.data_io.exceptions import ConfigurationError, DataImportError, RecordValidationError
from restaurant_orders.data_io.files import atomic_write
from restaurant_orders.data_io.readers import CsvImporter, importer_for
from restaurant_orders.data_io.validators import validate_row

RULES = ValidationRules(frozenset({"Перші страви", "Напої"}), 20.0, 500.0)


def row(**changes: str) -> dict[str, str]:
    """Correct raw record with some fields replaced."""
    data = {"order_id": "1", "dish": "Борщ", "category": "Перші страви", "price": "95", "quantity": "1"}
    data.update(changes)
    return data


@pytest.mark.parametrize("price", ["20", "20.00", "500", "499.99"], ids=["min", "min-float", "max", "below-max"])
def test_price_boundaries_are_accepted(price: str) -> None:
    assert validate_row(2, row(price=price), RULES).price == pytest.approx(float(price))


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"price": "19.99"}, "price"),
        ({"price": "500.01"}, "price"),
        ({"quantity": "0"}, "quantity"),
        ({"quantity": "два"}, "quantity"),
        ({"order_id": "-3"}, "order_id"),
        ({"dish": ""}, "dish"),
        ({"category": "Суші"}, "category"),
    ],
    ids=["price-below-min", "price-above-max", "zero-quantity", "text-quantity", "negative-id", "empty-dish",
         "unknown-category"],
)
def test_invalid_record_names_field(changes: dict[str, str], field: str) -> None:
    with pytest.raises(RecordValidationError) as error_info:
        validate_row(9, row(**changes), RULES)
    assert error_info.value.field == field
    assert str(error_info.value).startswith(f"рядок 9, поле {field}")


def test_malformed_record_with_missing_field() -> None:
    data = row()
    data["quantity"] = None  # type: ignore[assignment]
    with pytest.raises(RecordValidationError, match="Поле відсутнє"):
        validate_row(3, data, RULES)


def test_exception_chaining_keeps_value_error() -> None:
    with pytest.raises(RecordValidationError) as error_info:
        validate_row(2, row(price="wrong"), RULES)
    assert isinstance(error_info.value.__cause__, ValueError)


def test_csv_reader_streams_records_from_tmp_path(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text("order_id,dish,category,price,quantity\n1,Борщ,Перші страви,95,1\n", encoding="utf-8")
    assert [number for number, _ in CsvImporter().read(path)] == [2]


def test_unsupported_format_is_rejected() -> None:
    with pytest.raises(DataImportError, match=r"\.xml"):
        importer_for(Path("orders.xml"))


def test_atomic_write_cleans_temporary_file_on_error(tmp_path: Path) -> None:
    target = tmp_path / "orders.json"
    target.write_text("old valid data", encoding="utf-8")
    with pytest.raises(RuntimeError):
        with atomic_write(target) as file:
            file.write("half")
            raise RuntimeError("збій")
    assert target.read_text(encoding="utf-8") == "old valid data"
    assert not (tmp_path / "orders.json.tmp").exists()


def test_config_path_from_environment_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RESTAURANT_CONFIG", str(tmp_path / "custom.yaml"))
    assert default_config_path() == tmp_path / "custom.yaml"
    monkeypatch.delenv("RESTAURANT_CONFIG")
    assert default_config_path() == Path("config.yaml")


def test_configuration_categories_are_read(import_files: Callable[..., Path]) -> None:
    config = load_config(import_files("", categories="Напої"))
    assert config.rules.allowed_categories == frozenset({"Напої"})


def test_yaml_error_is_wrapped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def broken_safe_load(stream: object) -> object:
        raise config_module.yaml.YAMLError("зламаний YAML")

    monkeypatch.setattr(config_module.yaml, "safe_load", broken_safe_load)
    path = tmp_path / "config.yaml"
    path.write_text("schema_version: 1\n", encoding="utf-8")
    with pytest.raises(ConfigurationError) as error_info:
        load_config(path)
    assert isinstance(error_info.value.__cause__, config_module.yaml.YAMLError)
