"""Statistics for restaurant orders: small demo orders (laboratory work 2) and a large order history (laboratory work 9)."""

import random
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from restaurant_orders.data import MENU
from restaurant_orders.decorators import track_operation
from restaurant_orders.models import Dish
from restaurant_orders.processors import OrderLine


@track_operation("сума кожного замовлення")
def calculate_order_totals(groups: dict[int, list[OrderLine]]) -> dict[int, float]:
    """Return the total price of every order."""
    return {number: sum(line[3] for line in lines) for number, lines in groups.items()}


def calculate_average(*values: float) -> float:
    """Return the arithmetic mean of any number of values."""
    if not values:
        return 0.0
    return sum(values) / len(values)


@track_operation("середня вартість замовлення")
def calculate_average_check(totals: dict[int, float]) -> float:
    """Return the average order value."""
    return calculate_average(*totals.values())


@track_operation("найдорожча позиція")
def find_most_expensive_line(lines: list[OrderLine]) -> OrderLine | None:
    """Return the order position with the highest price."""
    return max(lines, key=lambda line: line[3], default=None)


@track_operation("найпопулярніша страва")
def find_most_popular_dish(dish_counter: Counter[str]) -> tuple[str, int] | None:
    """Return the most often ordered dish and its count."""
    most_common = dish_counter.most_common(1)
    return most_common[0] if most_common else None


@track_operation("рейтинг замовлень")
def rank_orders_by_total(totals: dict[int, float]) -> list[tuple[int, float]]:
    """Return (number, total) pairs from the most expensive order to the cheapest."""
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)


def create_price_filter(min_price: float) -> Callable[[OrderLine], bool]:
    """Create a check that keeps positions not cheaper than min_price."""

    def is_expensive_enough(line: OrderLine) -> bool:
        return line[3] >= min_price

    return is_expensive_enough


def create_summary(**values: Any) -> dict[str, Any]:
    """Collect named results of the analysis into one dictionary."""
    return dict(values)


# ---------------------------------------------------------------------------
# Laboratory work 9: statistics of a large order history.

# One position of the order history: (order number, dish name, quantity).
HistoryItem = tuple[int, str, int]
# Portions and revenue of one dish or category.
Sales = tuple[int, float]


@dataclass(frozen=True, slots=True)
class OrderStatistics:
    """Statistics of an order history; every implementation must return the same values."""

    orders_count: int
    turnover: float
    average_check: float
    most_expensive_order: tuple[int, float]
    most_popular_dish: tuple[str, int]
    top_revenue_dish: tuple[str, float]
    categories: dict[str, Sales]


def menu_by_name(menu: Iterable[Dish] = MENU) -> dict[str, Dish]:
    """Return the menu as a dictionary: dish name → dish."""
    return {dish.name: dish for dish in menu}


def generate_order_history(count: int, seed: int = 42) -> list[HistoryItem]:
    """Generate count orders with 1–5 different dishes of the menu, 1–3 portions each."""
    rng = random.Random(seed)
    names = [dish.name for dish in MENU]
    history: list[HistoryItem] = []
    for number in range(1, count + 1):
        for name in rng.sample(names, rng.randint(1, 5)):
            history.append((number, name, rng.randint(1, 3)))
    return history


def order_totals_python(history: list[HistoryItem], menu: dict[str, Dish]) -> dict[int, float]:
    """Return the total of every order (Python loop)."""
    totals: dict[int, float] = {}
    for number, name, quantity in history:
        totals[number] = totals.get(number, 0.0) + menu[name].price * quantity
    return totals


def dish_sales_python(history: list[HistoryItem], menu: dict[str, Dish]) -> dict[str, Sales]:
    """Return portions and revenue of every dish in menu order (Python loop)."""
    portions = dict.fromkeys(menu, 0)
    revenue = dict.fromkeys(menu, 0.0)
    for _, name, quantity in history:
        portions[name] += quantity
        revenue[name] += menu[name].price * quantity
    return {name: (portions[name], revenue[name]) for name in menu}


def category_sales(dish_sales: dict[str, Sales], menu: dict[str, Dish]) -> dict[str, Sales]:
    """Add up the sales of dishes by category."""
    categories: dict[str, Sales] = {}
    for name, (portions, revenue) in dish_sales.items():
        old_portions, old_revenue = categories.get(menu[name].category, (0, 0.0))
        categories[menu[name].category] = (old_portions + portions, old_revenue + revenue)
    return categories


def most_expensive_order(totals: dict[int, float]) -> tuple[int, float]:
    """Return (number, total) of the most expensive order; on a tie — the smallest number."""
    best = (0, 0.0)
    for number, total in totals.items():
        if total > best[1] or (total == best[1] and number < best[0]):
            best = (number, total)
    return best


def best_dish(dish_sales: dict[str, Sales], index: int) -> tuple[str, Any]:
    """Return the dish with the largest portions (index 0) or revenue (index 1); on a tie — the first in the menu."""
    name = max(dish_sales, key=lambda dish: dish_sales[dish][index])
    return name, dish_sales[name][index]


def build_statistics(
    orders_count: int, turnover: float, best_order: tuple[int, float],
    dish_sales: dict[str, Sales], menu: dict[str, Dish],
) -> OrderStatistics:
    """Collect the final statistics from already aggregated values."""
    return OrderStatistics(
        orders_count=orders_count,
        turnover=turnover,
        average_check=turnover / orders_count if orders_count else 0.0,
        most_expensive_order=best_order,
        most_popular_dish=best_dish(dish_sales, 0),
        top_revenue_dish=best_dish(dish_sales, 1),
        categories=category_sales(dish_sales, menu),
    )


def statistics_python(history: list[HistoryItem], menu: dict[str, Dish]) -> OrderStatistics:
    """Baseline: order totals, average check, best orders and dishes, turnover and categories with Python loops."""
    totals = order_totals_python(history, menu)
    dish_sales = dish_sales_python(history, menu)
    return build_statistics(len(totals), sum(totals.values()), most_expensive_order(totals), dish_sales, menu)
