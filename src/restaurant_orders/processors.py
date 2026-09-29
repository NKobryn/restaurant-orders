"""Functions that reorganise orders into Python collections."""

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from restaurant_orders.models import Order

# One order position: (order number, dish name, category, price).
OrderLine = tuple[int, str, str, float]


def to_order_lines(orders: list[Order]) -> list[OrderLine]:
    """Turn orders into a flat list of order positions."""
    return [(order.number, dish.name, dish.category, dish.price) for order in orders for dish in order.dishes]


def get_unique_dishes(lines: list[OrderLine]) -> set[str]:
    """Return the names of all dishes without repetitions."""
    return {line[1] for line in lines}


def get_unique_categories(lines: list[OrderLine]) -> set[str]:
    """Return all dish categories without repetitions."""
    return {line[2] for line in lines}


def group_lines_by_order(lines: list[OrderLine]) -> dict[int, list[OrderLine]]:
    """Group order positions by the order number."""
    groups: defaultdict[int, list[OrderLine]] = defaultdict(list)
    for line in lines:
        groups[line[0]].append(line)
    return dict(groups)


def count_dishes(lines: list[OrderLine]) -> Counter[str]:
    """Count how many times every dish was ordered."""
    return Counter(line[1] for line in lines)


def create_order_index(orders: list[Order]) -> dict[int, Order]:
    """Build a dictionary for fast search of an order by its number."""
    return {order.number: order for order in orders}


def filter_items(items: list[Any], predicate: Callable[[Any], bool]) -> list[Any]:
    """Return the items for which the predicate is true."""
    return [item for item in items if predicate(item)]
