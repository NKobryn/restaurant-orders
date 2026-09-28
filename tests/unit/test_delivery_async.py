"""Unit tests of asynchronous delivery with AsyncMock."""

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock, Mock

import pytest

from restaurant_orders.domain import delivery as delivery_module
from restaurant_orders.domain.delivery import DemoDeliveryService, dispatch_paid_order
from restaurant_orders.domain.exceptions import DeliveryError, OrderStateError
from restaurant_orders.domain.models import Order


@pytest.fixture
def paid_order(order_factory: Callable[..., Order]) -> Order:
    """Order that has already been paid."""
    order = order_factory(order_id=7)
    order.mark_paid()
    return order


def test_paid_order_is_scheduled_and_kitchen_notified(paid_order: Order, notifier: Mock) -> None:
    delivery = AsyncMock()
    delivery.schedule.return_value = "DLV-7"
    tracking = asyncio.run(dispatch_paid_order(paid_order, "  Львів  ", delivery, notifier))
    assert tracking == "DLV-7"
    delivery.schedule.assert_awaited_once_with(7, "Львів")
    notifier.notify.assert_called_once_with("замовлення №7 передано в доставку (DLV-7)")


def test_unpaid_order_is_not_sent_to_delivery(order_factory: Callable[..., Order], notifier: Mock) -> None:
    delivery = AsyncMock()
    with pytest.raises(OrderStateError, match="не оплачено"):
        asyncio.run(dispatch_paid_order(order_factory(), "Львів", delivery, notifier))
    delivery.schedule.assert_not_awaited()


@pytest.mark.parametrize("address", ["", "   "], ids=["empty", "spaces"])
def test_empty_address_is_rejected(paid_order: Order, notifier: Mock, address: str) -> None:
    delivery = AsyncMock()
    with pytest.raises(DeliveryError):
        asyncio.run(dispatch_paid_order(paid_order, address, delivery, notifier))
    delivery.schedule.assert_not_awaited()


def test_delivery_failure_is_propagated_without_notification(paid_order: Order, notifier: Mock) -> None:
    delivery = AsyncMock()
    delivery.schedule.side_effect = TimeoutError("служба доставки не відповідає")
    with pytest.raises(TimeoutError):
        asyncio.run(dispatch_paid_order(paid_order, "Львів", delivery, notifier))
    notifier.notify.assert_not_called()


def test_demo_delivery_awaits_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sleep = AsyncMock()
    monkeypatch.setattr(delivery_module.asyncio, "sleep", fake_sleep)
    assert asyncio.run(DemoDeliveryService(delay=5).schedule(3, "Львів")) == "DLV-3"
    fake_sleep.assert_awaited_once_with(5)
