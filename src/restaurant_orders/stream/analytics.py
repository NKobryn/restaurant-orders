"""Aggregation stage: statistics computed in one pass over the orders."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import accumulate

from restaurant_orders.models import OrderItemRecord, OrderSummary
from restaurant_orders.stream.pipeline import batched


@dataclass(slots=True)
class OrdersStatistics:
    """Totals of a processed stream of orders."""

    orders_count: int = 0
    revenue: float = 0.0
    most_expensive: OrderItemRecord | None = None

    @property
    def average_check(self) -> float:
        """Return the average order value."""
        return self.revenue / self.orders_count if self.orders_count else 0.0


def collect_statistics(orders: Iterable[OrderSummary]) -> OrdersStatistics:
    """Count orders, revenue and the most expensive position in one pass."""
    statistics = OrdersStatistics()
    for order in orders:
        statistics.orders_count += 1
        statistics.revenue += order.total
        best = statistics.most_expensive
        if best is None or order.most_expensive.price > best.price:
            statistics.most_expensive = order.most_expensive
    return statistics


def running_averages(totals: Iterable[float]) -> Iterator[float]:
    """Yield the average order value after every next order."""
    for number, subtotal in enumerate(accumulate(totals), start=1):
        yield subtotal / number


def batch_reports(orders: Iterable[OrderSummary], size: int) -> Iterator[tuple[int, int, float]]:
    """Yield (batch number, orders in batch, batch revenue) for every batch of orders."""
    for number, batch in enumerate(batched(orders, size), start=1):
        yield number, len(batch), sum(order.total for order in batch)
