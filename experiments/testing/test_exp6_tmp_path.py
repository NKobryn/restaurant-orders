"""Experiment 6: every run gets a new empty tmp_path; nothing is written into the repository."""

from pathlib import Path

from restaurant_orders.data_io.exporters import export_json
from restaurant_orders.models import OrderItemRecord


def test_export_into_tmp_path(tmp_path: Path) -> None:
    assert list(tmp_path.iterdir()) == []
    output = tmp_path / "orders.json"
    assert export_json([OrderItemRecord(1, "Борщ", "Перші страви", 95.0, 1)], output) == 1
    print(f"\ntmp_path = {tmp_path}")
