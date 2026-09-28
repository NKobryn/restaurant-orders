"""Unit tests of dishes, order items, orders and pricing (pytest style)."""

from collections.abc import Callable

import pytest

from restaurant_orders.domain.exceptions import CurrencyMismatchError, OrderStateError
from restaurant_orders.domain.models import Dish, Menu, Order, OrderItem, OrderStatus
from restaurant_orders.domain.pricing import CategoryDiscount, PricingPolicy
from restaurant_orders.domain.value_objects import Money


def test_dish_is_created_with_price_property(dish_factory: Callable[..., Dish]) -> None:
    # Arrange + Act
    dish = dish_factory(5, "Стейк", "Основні страви", 280.0)
    # Assert
    assert dish.price == Money(280.0)
    assert str(dish) == "Стейк (280.00 UAH)"


@pytest.mark.parametrize(
    ("dish_id", "name", "message"),
    [(0, "Борщ", "Ідентифікатор"), (-1, "Борщ", "Ідентифікатор"), (1, "   ", "Назва")],
    ids=["zero-id", "negative-id", "blank-name"],
)
def test_invalid_dish_is_rejected(dish_id: int, name: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Dish(dish_id, name, "Перші страви", Money(95.0))


@pytest.mark.parametrize(
    ("amount", "is_valid"),
    [(0.0, True), (0.01, True), (-0.01, False), (-95.0, False)],
    ids=["zero-boundary", "smallest-positive", "just-below-zero", "negative"],
)
def test_money_amount_boundaries(amount: float, is_valid: bool) -> None:
    if is_valid:
        assert Money(amount).amount == amount
    else:
        with pytest.raises(ValueError):
            Money(amount)


@pytest.mark.parametrize("quantity", [0, -1], ids=["zero", "negative"])
def test_order_item_rejects_invalid_quantity(menu: Menu, quantity: int) -> None:
    with pytest.raises(ValueError, match="Кількість"):
        OrderItem(menu[1], quantity)


def test_order_item_minimum_quantity_is_one(menu: Menu) -> None:
    assert OrderItem(menu[1]).total == Money(95.0)


def test_adding_same_dish_increases_quantity(order_factory: Callable[..., Order]) -> None:
    order = order_factory(items=((1, 2), (8, 1), (1, 1)))
    assert [(item.dish.name, item.quantity) for item in order] == [("Борщ", 3), ("Узвар", 1)]
    assert len(order) == 2


def test_order_total_and_most_expensive_dish(order_factory: Callable[..., Order]) -> None:
    order = order_factory(items=((1, 2), (5, 1), (8, 3)))
    assert order.total == Money(605.0)
    assert order.most_expensive_dish() is not None
    assert order.most_expensive_dish().name == "Стейк"  # type: ignore[union-attr]


def test_empty_order_has_zero_total_and_no_dish() -> None:
    order = Order(1)
    assert order.total == Money(0)
    assert order.most_expensive_dish() is None
    assert len(order) == 0


def test_paid_order_cannot_be_paid_or_changed_again(order_factory: Callable[..., Order], menu: Menu) -> None:
    order = order_factory()
    order.mark_paid()
    assert order.status is OrderStatus.PAID
    with pytest.raises(OrderStateError, match="не можна оплатити: paid"):
        order.mark_paid()
    with pytest.raises(OrderStateError) as error_info:
        order.add_dish(menu[5])
    assert "вже не можна змінювати" in str(error_info.value)


def test_category_discount_uses_approx_for_money() -> None:
    order = Order(1)
    order.add_dish(Dish(8, "Узвар", "Напої", Money(45.1)), 3)
    total = CategoryDiscount("Напої", 20).final_total(order)
    expected = 45.1 * 3 * 0.8  # 108.24000000000001 because of binary floating point
    assert expected != 108.24
    assert total.amount == pytest.approx(expected)


def test_pricing_never_increases_total(pricing: PricingPolicy, order_factory: Callable[..., Order]) -> None:
    order = order_factory(items=((1, 1), (8, 2)))
    assert pricing.final_total(order) <= order.total


def test_money_in_different_currencies_cannot_be_added() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(10.0) + Money(10.0, "EUR")
