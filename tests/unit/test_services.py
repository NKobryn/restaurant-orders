"""Unit tests for restaurant order business logic."""

import unittest

from restaurant_orders.models import Dish, Order
from restaurant_orders.services import (
    OrderNotFoundError,
    add_dish_to_order,
    calculate_average_order_value,
    calculate_order_total,
    create_order,
    find_most_expensive_dish,
    sort_orders_by_total,
)


class RestaurantOrderServicesTest(unittest.TestCase):
    """Tests for calculations and order operations."""

    def setUp(self) -> None:
        self.orders: list[Order] = []
        create_order(self.orders, 1)
        add_dish_to_order(self.orders, 1, Dish("Суп", "Перші страви", 80.0))
        add_dish_to_order(self.orders, 1, Dish("Стейк", "Основні страви", 220.0))

    def test_calculates_order_total(self) -> None:
        self.assertEqual(calculate_order_total(self.orders[0]), 300.0)

    def test_finds_most_expensive_dish(self) -> None:
        dish = find_most_expensive_dish(self.orders[0])
        self.assertIsNotNone(dish)
        self.assertEqual(dish.name, "Стейк")

    def test_calculates_average_order_value(self) -> None:
        create_order(self.orders, 2)
        add_dish_to_order(self.orders, 2, Dish("Чай", "Напої", 40.0))
        self.assertEqual(calculate_average_order_value(self.orders), 170.0)

    def test_sorts_orders_by_total_descending(self) -> None:
        create_order(self.orders, 2)
        add_dish_to_order(self.orders, 2, Dish("Салат", "Закуски", 350.0))
        result = sort_orders_by_total(self.orders)
        self.assertEqual([order.number for order in result], [2, 1])

    def test_rejects_duplicate_order_number(self) -> None:
        with self.assertRaises(ValueError):
            create_order(self.orders, 1)

    def test_rejects_adding_dish_to_absent_order(self) -> None:
        with self.assertRaises(OrderNotFoundError):
            add_dish_to_order(self.orders, 99, Dish("Сік", "Напої", 50.0))

    def test_rejects_non_positive_dish_price(self) -> None:
        with self.assertRaises(ValueError):
            Dish("Вода", "Напої", 0)


if __name__ == "__main__":
    unittest.main()
