"""Statistics for restaurant orders: small demo orders (laboratory work 2) and a large order history (laboratory work 9)."""

import random
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from numpy.typing import NDArray

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


@dataclass(frozen=True, eq=False)
class HistoryArrays:
    """The order history as NumPy arrays: one element per position."""

    order_ids: NDArray[np.int32]
    dish_indexes: NDArray[np.uint8]
    quantities: NDArray[np.uint8]
    dish_names: tuple[str, ...]


def to_arrays(history: list[HistoryItem], menu: dict[str, Dish]) -> HistoryArrays:
    """Convert the history to compact NumPy arrays; dishes are stored as their index in the menu."""
    names = tuple(menu)
    index = {name: number for number, name in enumerate(names)}
    count = len(history)
    return HistoryArrays(
        order_ids=np.fromiter((item[0] for item in history), dtype=np.int32, count=count),
        dish_indexes=np.fromiter((index[item[1]] for item in history), dtype=np.uint8, count=count),
        quantities=np.fromiter((item[2] for item in history), dtype=np.uint8, count=count),
        dish_names=names,
    )


def statistics_numpy(arrays: HistoryArrays, menu: dict[str, Dish]) -> OrderStatistics:
    """The same statistics with vectorized NumPy operations instead of Python loops."""
    prices = np.array([menu[name].price for name in arrays.dish_names], dtype=np.float64)
    line_totals = prices[arrays.dish_indexes] * arrays.quantities
    totals = np.bincount(arrays.order_ids, weights=line_totals)
    present = np.bincount(arrays.order_ids) > 0
    order_numbers = np.flatnonzero(present)
    order_totals = totals[present]
    best = int(np.argmax(order_totals)) if order_totals.size else -1
    best_order = (int(order_numbers[best]), float(order_totals[best])) if best >= 0 else (0, 0.0)
    dishes = len(arrays.dish_names)
    portions = np.bincount(arrays.dish_indexes, weights=arrays.quantities, minlength=dishes)
    revenue = np.bincount(arrays.dish_indexes, weights=line_totals, minlength=dishes)
    dish_sales = {name: (int(portions[i]), float(revenue[i])) for i, name in enumerate(arrays.dish_names)}
    return build_statistics(int(order_numbers.size), float(order_totals.sum()), best_order, dish_sales, menu)


def statistics_numpy_from_history(history: list[HistoryItem], menu: dict[str, Dish]) -> OrderStatistics:
    """NumPy statistics including the conversion of the Python list to arrays."""
    return statistics_numpy(to_arrays(history, menu), menu)


class OrderHistory:
    """Order history with its menu; the statistics are cached until the prices or the orders change."""

    def __init__(self, history: Iterable[HistoryItem], menu: dict[str, Dish]) -> None:
        self.items = list(history)
        self.menu = dict(menu)
        self.version = 0

    def change_price(self, name: str, price: float) -> None:
        """Change the price of a dish; the cached statistics become outdated."""
        dish = self.menu[name]
        self.menu[name] = Dish(dish.name, dish.category, price)
        self.version += 1

    def add_item(self, order_id: int, name: str, quantity: int = 1) -> None:
        """Add a dish to an order; the cached statistics become outdated."""
        if name not in self.menu:
            raise KeyError(f"Страви «{name}» немає в меню.")
        self.items.append((order_id, name, quantity))
        self.version += 1

    def statistics(self) -> OrderStatistics:
        return cached_statistics(self, self.version)


@lru_cache(maxsize=32)
def cached_statistics(history: OrderHistory, version: int) -> OrderStatistics:
    """Statistics of the history; version is a part of the cache key, so a change of data means a new key (invalidation)."""
    return statistics_python(history.items, history.menu)
