"""Integration tests of the order flow: import -> orders -> payment -> async delivery."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from restaurant_orders.data_io.config import load_config
from restaurant_orders.domain.exceptions import PaymentError
from restaurant_orders.domain.models import OrderStatus
from restaurant_orders.domain.value_objects import Money
from restaurant_orders.flow import run_order_flow
from restaurant_orders.flow_app import main

pytestmark = pytest.mark.integration

ROWS = (
    "201,Борщ,Перші страви,95,2\n"
    "201,Узвар,Напої,45,2\n"
    "202,Стейк,Основні страви,280,2\n"
    "203,Капучино,Напої,75,1\n"
    "203,Борщ,Перші страви,95,1\n"
    "204,Сирник,Десерти,85,1\n"
)


def refuse_above_500(order_id: int, amount: Money) -> str:
    """Payment gateway behaviour for the test: refuse payments above 500 UAH."""
    if amount > Money(500.0):
        raise PaymentError("Ліміт")
    return f"PAY-{order_id}"


def test_order_flow_pays_and_delivers(import_files: Callable[..., Path], notifier: Mock) -> None:
    gateway = Mock()
    gateway.pay.side_effect = refuse_above_500
    delivery = AsyncMock()
    delivery.schedule.side_effect = lambda order_id, address: f"DLV-{order_id}"

    result = run_order_flow(load_config(import_files(ROWS)), gateway, notifier, delivery, "Львів")

    assert (result.statistics.valid, result.statistics.invalid) == (5, 1)
    assert [order.id for order in result.orders] == [201, 202, 203]
    assert result.failed_payments == [202]
    assert result.deliveries == {201: "DLV-201", 203: "DLV-203"}
    assert delivery.schedule.await_count == 2
    delivery.schedule.assert_any_await(201, "Львів")
    assert [order.status for order in result.orders] == [OrderStatus.PAID, OrderStatus.NEW, OrderStatus.PAID]
    assert notifier.notify.call_count == 4


def test_main_uses_config_from_environment(
    import_files: Callable[..., Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("RESTAURANT_CONFIG", str(import_files(ROWS)))
    assert main([]) == 0
    output = capsys.readouterr().out
    assert "№201 [paid] 280.00 UAH: Борщ × 2, Узвар × 2; доставка: DLV-201" in output
    assert "оплату відхилено: [202]" in output


def test_main_reports_missing_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "absent.yaml")]) == 1
    assert "CRITICAL" in capsys.readouterr().out
