"""Lazy filters for order positions and orders."""

from collections.abc import Callable, Iterable, Iterator
from itertools import islice

from restaurant_orders.models import OrderItemRecord, OrderSummary


def filter_by_category(records: Iterable[OrderItemRecord], categories: set[str]) -> Iterator[OrderItemRecord]:
    """Yield only positions whose category is in categories."""
    for record in records:
        if record.category in categories:
            yield record


def first_orders(
    orders: Iterable[OrderSummary], amount: int, condition: Callable[[OrderSummary], bool]
) -> list[OrderSummary]:
    """Return the first amount orders that satisfy the condition."""
    matching = (order for order in orders if condition(order))
    return list(islice(matching, amount))


def find_first(orders: Iterable[OrderSummary], condition: Callable[[OrderSummary], bool]) -> OrderSummary | None:
    """Return the first order that satisfies the condition and stop reading."""
    for order in orders:
        if condition(order):
            return order
    return None
