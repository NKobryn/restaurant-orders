"""Experiment 1-2: weak tests only execute code and never check the result."""

from buggy_pricing import apply_discount, free_table
from order_size import classify_order

from restaurant_orders.domain.models import Dish, Order
from restaurant_orders.domain.pricing import CategoryDiscount
from restaurant_orders.domain.value_objects import Money


def test_discount_weak() -> None:
    apply_discount(100, 10)


def test_category_discount_weak() -> None:
    order = Order(1)
    order.add_dish(Dish(8, "Узвар", "Напої", Money(45.0)), 2)
    CategoryDiscount("Напої", 20).final_total(order)


def test_classify_weak() -> None:
    for total in (1200, 500, 100):
        classify_order(total)
    free_table()
