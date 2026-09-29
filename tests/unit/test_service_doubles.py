"""Unit tests of RestaurantService with test doubles: Mock, autospec, fake repository."""

from collections.abc import Callable
from unittest.mock import Mock, call

import pytest

from restaurant_orders.domain.exceptions import OrderNotFoundError, OrderStateError, PaymentError
from restaurant_orders.domain.models import Menu, Order, OrderStatus
from restaurant_orders.domain.pricing import NoDiscount, PricingPolicy
from restaurant_orders.domain.repositories import Repository
from restaurant_orders.domain.services import RestaurantService
from restaurant_orders.domain.value_objects import Money


@pytest.fixture
def service(menu: Menu, fake_repository: Repository[Order], gateway: Mock, notifier: Mock) -> RestaurantService:
    """Service with a fake repository and mocked external services."""
    return RestaurantService(menu, fake_repository, gateway, notifier, NoDiscount())


def test_create_order_and_add_dishes(service: RestaurantService, fake_repository: Repository[Order]) -> None:
    order = service.create_order()
    service.add_dish(order.id, 1, 2)
    service.add_dish(order.id, 5)
    assert fake_repository.get(1) is order
    assert service.order_total(order.id) == Money(470.0)
    assert service.most_expensive_dish(order.id).name == "Стейк"  # type: ignore[union-attr]


def test_average_order_value_uses_pricing(
    menu: Menu, fake_repository: Repository[Order], gateway: Mock, notifier: Mock, pricing: PricingPolicy
) -> None:
    service = RestaurantService(menu, fake_repository, gateway, notifier, pricing)
    for items in (((1, 2),), ((8, 4),)):
        order = service.create_order()
        for dish_id, quantity in items:
            service.add_dish(order.id, dish_id, quantity)
    second = fake_repository.get(2)
    assert second is not None
    expected = (190.0 + pricing.final_total(second).amount) / 2
    assert service.average_order_value().amount == pytest.approx(expected, abs=0.01)


def test_average_of_no_orders_is_zero(service: RestaurantService) -> None:
    service.create_order()
    assert service.average_order_value() == Money(0)


def test_checkout_uses_return_value_and_notifies_kitchen(
    service: RestaurantService, gateway: Mock, notifier: Mock
) -> None:
    order = service.create_order()
    service.add_dish(order.id, 8, 2)
    assert service.checkout(order.id) == "PAY-001"
    gateway.pay.assert_called_once_with(order.id, Money(90.0))
    notifier.notify.assert_called_once()
    assert "PAY-001" in notifier.notify.call_args.args[0]
    assert order.status is OrderStatus.PAID


def test_payment_failure_does_not_notify_kitchen(service: RestaurantService, gateway: Mock, notifier: Mock) -> None:
    gateway.pay.side_effect = PaymentError("Відмова банку")
    order = service.create_order()
    service.add_dish(order.id, 5)
    with pytest.raises(PaymentError, match="Відмова банку"):
        service.checkout(order.id)
    notifier.notify.assert_not_called()
    assert order.status is OrderStatus.NEW


def test_second_checkout_does_not_charge_again(service: RestaurantService, gateway: Mock) -> None:
    order = service.create_order()
    service.add_dish(order.id, 1)
    service.checkout(order.id)
    with pytest.raises(OrderStateError):
        service.checkout(order.id)
    assert gateway.pay.call_count == 1


def test_empty_order_cannot_be_checked_out(service: RestaurantService, gateway: Mock) -> None:
    order = service.create_order()
    with pytest.raises(OrderStateError, match="порожнє"):
        service.checkout(order.id)
    gateway.pay.assert_not_called()


def test_side_effect_function_decides_per_call(service: RestaurantService, gateway: Mock) -> None:
    def refuse_big_amounts(order_id: int, amount: Money) -> str:
        if amount > Money(300.0):
            raise PaymentError("Ліміт")
        return f"OK-{order_id}"

    gateway.pay.side_effect = refuse_big_amounts
    small, big = service.create_order(), service.create_order()
    service.add_dish(small.id, 1)
    service.add_dish(big.id, 5, 2)
    assert service.checkout(small.id) == "OK-1"
    with pytest.raises(PaymentError):
        service.checkout(big.id)
    assert gateway.pay.call_args_list == [call(1, Money(95.0)), call(2, Money(560.0))]


def test_repository_mock_interactions(
    menu: Menu, gateway: Mock, notifier: Mock, order_factory: Callable[..., Order]
) -> None:
    repository = Mock(spec=Repository)
    order = order_factory(order_id=7)
    repository.get.return_value = order
    service = RestaurantService(menu, repository, gateway, notifier, NoDiscount())
    service.checkout(7)
    repository.get.assert_called_with(7)
    repository.add.assert_called_once_with(order)


def test_unknown_order_raises_custom_exception(menu: Menu, gateway: Mock, notifier: Mock) -> None:
    repository = Mock(spec=Repository)
    repository.get.return_value = None
    service = RestaurantService(menu, repository, gateway, notifier, NoDiscount())
    with pytest.raises(OrderNotFoundError) as error_info:
        service.order_total(99)
    assert error_info.value.args[0] == "Замовлення №99 не знайдено."


def test_autospec_rejects_wrong_signature(gateway: Mock) -> None:
    with pytest.raises(TypeError):
        gateway.pay(1)
