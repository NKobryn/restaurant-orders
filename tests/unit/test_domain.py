"""Unit tests for the typed object model of the restaurant."""

import unittest
from dataclasses import FrozenInstanceError

from restaurant_orders.domain.dto import DishPayload, dish_from_payload
from restaurant_orders.domain.exceptions import (
    CurrencyMismatchError,
    DishNotFoundError,
    OrderNotFoundError,
    OrderStateError,
    PaymentError,
    RestaurantError,
)
from restaurant_orders.domain.models import Dish, Menu, Order, OrderItem, OrderStatus
from restaurant_orders.domain.pricing import CategoryDiscount, NoDiscount
from restaurant_orders.domain.protocols import KitchenNotifier
from restaurant_orders.domain.repositories import InMemoryRepository, Repository
from restaurant_orders.domain.services import RestaurantService
from restaurant_orders.domain.value_objects import Money


def make_menu() -> Menu:
    """Create a small menu for tests."""
    return Menu(
        [
            Dish(1, "Борщ", "Перші страви", Money(95.0)),
            Dish(5, "Стейк", "Основні страви", Money(280.0)),
            Dish(8, "Узвар", "Напої", Money(45.0)),
        ]
    )


class FakeGateway:
    """Payment gateway that records payments or refuses them."""

    def __init__(self, refuse: bool = False) -> None:
        self.refuse = refuse
        self.payments: list[tuple[int, Money]] = []

    def pay(self, order_id: int, amount: Money) -> str:
        if self.refuse:
            raise PaymentError("Відмова банку.")
        self.payments.append((order_id, amount))
        return f"TEST-{order_id}"


class FakeNotifier:
    """Notifier that keeps messages in a list."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


class MoneyTest(unittest.TestCase):
    """Tests for the Money value object."""

    def test_arithmetic_and_comparison(self) -> None:
        self.assertEqual(Money(95.0) + Money(280.0), Money(375.0))
        self.assertEqual(Money(45.0) * 3, Money(135.0))
        self.assertTrue(Money(95.0) < Money(280.0))
        self.assertTrue(Money(280.0) >= Money(95.0))

    def test_money_is_immutable_and_validated(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            Money(10.0).amount = 20.0  # type: ignore[misc]
        with self.assertRaises(ValueError):
            Money(-1.0)
        with self.assertRaises(CurrencyMismatchError):
            Money(1.0) + Money(1.0, "EUR")


class ModelsTest(unittest.TestCase):
    """Tests for dishes, order items, orders and the menu."""

    def setUp(self) -> None:
        self.menu = make_menu()

    def test_dish_price_is_read_through_property(self) -> None:
        dish = self.menu[1]
        dish.change_price(Money(99.0))
        self.assertEqual(dish.price, Money(99.0))
        with self.assertRaises(ValueError):
            dish.change_price(Money(99.0, "EUR"))

    def test_order_item_total_and_validation(self) -> None:
        self.assertEqual(OrderItem(self.menu[8], 3).total, Money(135.0))
        with self.assertRaises(ValueError):
            OrderItem(self.menu[8], 0)

    def test_order_merges_same_dish_and_counts_total(self) -> None:
        order = Order(1)
        order.add_dish(self.menu[1], 2)
        order.add_dish(self.menu[5])
        order.add_dish(self.menu[1])
        self.assertEqual(len(order), 2)
        self.assertEqual([item.quantity for item in order], [3, 1])
        self.assertEqual(order.total, Money(565.0))
        self.assertIn(5, order)
        self.assertNotIn(8, order)

    def test_most_expensive_dish_and_empty_order(self) -> None:
        order = Order(1)
        self.assertIsNone(order.most_expensive_dish())
        self.assertEqual(order.total, Money(0))
        order.add_dish(self.menu[8], 5)
        order.add_dish(self.menu[5])
        self.assertEqual(order.most_expensive_dish(), self.menu[5])

    def test_paid_order_cannot_change(self) -> None:
        order = Order(1)
        order.add_dish(self.menu[1])
        order.mark_paid()
        self.assertIs(order.status, OrderStatus.PAID)
        with self.assertRaises(OrderStateError):
            order.add_dish(self.menu[8])
        with self.assertRaises(OrderStateError):
            order.mark_paid()

    def test_menu_is_a_collection(self) -> None:
        self.assertEqual(len(self.menu), 3)
        self.assertIn(5, self.menu)
        self.assertEqual([dish.name for dish in self.menu.by_category("Напої")], ["Узвар"])
        with self.assertRaises(DishNotFoundError):
            self.menu[42]
        with self.assertRaises(ValueError):
            self.menu.add(Dish(1, "Інший борщ", "Перші страви", Money(1.0)))


class RepositoryPricingDtoTest(unittest.TestCase):
    """Tests for the repository, pricing policies and TypedDict conversion."""

    def test_repository_stores_items_by_id(self) -> None:
        repository = InMemoryRepository[Order]()
        order = Order(3)
        repository.add(order)
        self.assertIs(repository.get(3), order)
        self.assertIsNone(repository.get(4))
        self.assertEqual(repository.all(), [order])

    def test_abstract_repository_cannot_be_created(self) -> None:
        with self.assertRaises(TypeError):
            Repository()  # type: ignore[abstract]

    def test_category_discount_changes_only_one_category(self) -> None:
        menu = make_menu()
        order = Order(1)
        order.add_dish(menu[1])
        order.add_dish(menu[8], 2)
        self.assertEqual(NoDiscount().final_total(order), Money(185.0))
        self.assertEqual(CategoryDiscount("Напої", 20).final_total(order), Money(167.0))
        with self.assertRaises(ValueError):
            CategoryDiscount("Напої", 0)

    def test_payload_becomes_dish(self) -> None:
        payload: DishPayload = {
            "id": 2,
            "name": "Бульйон",
            "category": "Перші страви",
            "price": 70.0,
            "currency": "UAH",
        }
        self.assertEqual(dish_from_payload(payload).price, Money(70.0))


class RestaurantServiceTest(unittest.TestCase):
    """Tests for the application service with fake dependencies."""

    def setUp(self) -> None:
        self.gateway = FakeGateway()
        self.notifier = FakeNotifier()
        self.service = RestaurantService(
            make_menu(), InMemoryRepository[Order](), self.gateway, self.notifier, NoDiscount()
        )

    def test_create_order_add_dishes_and_totals(self) -> None:
        first = self.service.create_order()
        second = self.service.create_order()
        self.service.add_dish(first.id, 1, 2)
        self.service.add_dish(second.id, 5)
        self.assertEqual((first.id, second.id), (1, 2))
        self.assertEqual(self.service.order_total(first.id), Money(190.0))
        self.assertEqual(self.service.most_expensive_dish(second.id), make_menu()[5])
        self.assertEqual(self.service.average_order_value(), Money(235.0))

    def test_checkout_pays_and_notifies_kitchen(self) -> None:
        order = self.service.create_order()
        self.service.add_dish(order.id, 8, 2)
        self.assertEqual(self.service.checkout(order.id), "TEST-1")
        self.assertEqual(self.gateway.payments, [(1, Money(90.0))])
        self.assertIn("Узвар × 2", self.notifier.messages[0])
        self.assertIs(order.status, OrderStatus.PAID)

    def test_second_checkout_does_not_charge_again(self) -> None:
        order = self.service.create_order()
        self.service.add_dish(order.id, 1)
        self.service.checkout(order.id)
        with self.assertRaises(OrderStateError):
            self.service.checkout(order.id)
        self.assertEqual(len(self.gateway.payments), 1)

    def test_refused_payment_keeps_order_new(self) -> None:
        service = RestaurantService(
            make_menu(), InMemoryRepository[Order](), FakeGateway(refuse=True), self.notifier, NoDiscount()
        )
        order = service.create_order()
        service.add_dish(order.id, 5)
        with self.assertRaises(PaymentError):
            service.checkout(order.id)
        self.assertIs(order.status, OrderStatus.NEW)
        self.assertEqual(self.notifier.messages, [])

    def test_errors_share_one_base_class(self) -> None:
        empty = self.service.create_order()
        for action in (
            lambda: self.service.checkout(empty.id),
            lambda: self.service.order_total(99),
            lambda: self.service.add_dish(empty.id, 42),
        ):
            with self.assertRaises(RestaurantError):
                action()
        self.assertTrue(issubclass(OrderNotFoundError, RestaurantError))
        self.assertEqual(self.service.average_order_value(), Money(0))

    def test_runtime_checkable_protocol(self) -> None:
        self.assertIsInstance(self.notifier, KitchenNotifier)
        self.assertNotIsInstance(self.gateway, KitchenNotifier)


if __name__ == "__main__":
    unittest.main()
