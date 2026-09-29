"""Integration tests: CSV -> validation -> JSON export with real files in tmp_path."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from restaurant_orders.data_io.config import load_config
from restaurant_orders.data_io.exceptions import RecordValidationError
from restaurant_orders.data_io.services import ImportStatistics, run_import

pytestmark = pytest.mark.integration

ROWS = (
    "101,Борщ,Перші страви,95,2\n"
    "101,Узвар,Напої,45,2\n"
    "102,Стейк,Основні страви,280,1\n"
    "abc,Сирник,Десерти,85,1\n"
    "103,Капучино,Напої,75,0\n"
)


def test_tolerant_import_writes_json_errors_and_summary(import_files: Callable[..., Path], tmp_path: Path) -> None:
    statistics = ImportStatistics()
    run_import(load_config(import_files(ROWS)), statistics)
    exported = json.loads((tmp_path / "orders.json").read_text(encoding="utf-8"))
    assert [(item["order_id"], item["dish"]) for item in exported] == [(101, "Борщ"), (101, "Узвар"), (102, "Стейк")]
    assert exported[0] == {"order_id": 101, "dish": "Борщ", "category": "Перші страви", "price": 95.0, "quantity": 2}
    errors = (tmp_path / "invalid.csv").read_text(encoding="utf-8").splitlines()
    assert [line.split(",")[:2] for line in errors[1:]] == [["5", "order_id"], ["6", "quantity"]]
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary == {
        "mode": "tolerant",
        "input": str(tmp_path / "orders.csv"),
        "total": 5,
        "valid": 3,
        "invalid": 2,
        "exported": 3,
    }


def test_configuration_categories_change_the_result(import_files: Callable[..., Path], tmp_path: Path) -> None:
    statistics = ImportStatistics()
    run_import(load_config(import_files(ROWS, categories="Напої")), statistics)
    exported = json.loads((tmp_path / "orders.json").read_text(encoding="utf-8"))
    assert [item["dish"] for item in exported] == ["Узвар"]
    assert (statistics.valid, statistics.invalid) == (1, 4)


def test_strict_import_stops_and_keeps_previous_output(import_files: Callable[..., Path], tmp_path: Path) -> None:
    config = load_config(import_files(ROWS, skip_invalid=False))
    (tmp_path / "orders.json").write_text("[]\n", encoding="utf-8")
    statistics = ImportStatistics()
    with pytest.raises(RecordValidationError, match="рядок 5"):
        run_import(config, statistics)
    assert (tmp_path / "orders.json").read_text(encoding="utf-8") == "[]\n"
    assert sorted(path.name for path in tmp_path.iterdir() if path.suffix == ".tmp") == []
    assert (statistics.total, statistics.valid, statistics.invalid) == (4, 3, 1)
