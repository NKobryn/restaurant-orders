"""Streaming export of order totals into a new CSV file."""

import csv
from collections.abc import Iterable
from pathlib import Path

from restaurant_orders.models import OrderSummary


def export_order_totals(orders: Iterable[OrderSummary], path: Path) -> int:
    """Write every order total as soon as it is ready; return the number of rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["order_id", "items_count", "total"])
        for order in orders:
            writer.writerow([order.order_id, order.items_count, f"{order.total:.2f}"])
            written += 1
    return written
