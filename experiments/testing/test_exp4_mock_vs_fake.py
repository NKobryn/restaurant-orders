"""Experiment 4: the same checkout scenario with a Mock repository and with a fake repository."""

from unittest.mock import Mock

from restaurant_orders.domain.models import Dish, Menu, Order, OrderStatus
from restaurant_orders.domain.pricing import NoDiscount
from restaurant_orders.domain.repositories import InMemoryRepository, Repository
from restaurant_orders.domain.services import RestaurantService
from restaurant_orders.domain.value_objects import Money

MENU = Menu([Dish(1, "Борщ", "Перші страви", Money(95.0))])


def test_checkout_with_mock_repository() -> None:
    order = Order(1)
    order.add_dish(MENU[1])
    repository = Mock(spec=Repository)
    repository.get.return_value = order
    service = RestaurantService(MENU, repository, Mock(), Mock(), NoDiscount())
    service.checkout(1)
    repository.get.assert_called_with(1)
    repository.add.assert_called_once_with(order)


def test_checkout_with_fake_repository() -> None:
    repository = InMemoryRepository[Order]()
    service = RestaurantService(MENU, repository, Mock(), Mock(), NoDiscount())
    order = service.create_order()
    service.add_dish(order.id, 1)
    service.checkout(order.id)
    stored = repository.get(order.id)
    assert stored is not None and stored.status is OrderStatus.PAID
