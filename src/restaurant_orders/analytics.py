"""Statistics for restaurant orders built from order positions."""

from collections import Counter
from collections.abc import Callable
from typing import Any

from restaurant_orders.decorators import track_operation
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
