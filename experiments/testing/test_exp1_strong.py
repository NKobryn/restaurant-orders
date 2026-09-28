"""Experiment 1-2: strong tests check the expected result."""

import pytest
from buggy_pricing import apply_discount
from order_size import classify_order

from restaurant_orders.domain.models import Dish, Order
from restaurant_orders.domain.pricing import CategoryDiscount
from restaurant_orders.domain.value_objects import Money


def test_discount_strong() -> None:
    assert apply_discount(100, 10) == pytest.approx(90)


def test_category_discount_strong() -> None:
    order = Order(1)
    order.add_dish(Dish(8, "Узвар", "Напої", Money(45.0)), 2)
    assert CategoryDiscount("Напої", 20).final_total(order).amount == pytest.approx(72.0)


def test_classify_strong() -> None:
    assert [classify_order(total) for total in (1200, 500, 100)] == ["large", "medium", "small"]
