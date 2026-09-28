"""Streaming validation of order positions."""

from collections import Counter
from collections.abc import Iterable, Iterator

from restaurant_orders.models import OrderItemRecord


def to_record(row: dict[str, str], categories: set[str]) -> OrderItemRecord:
    """Convert one CSV row into a record or raise ValueError."""
    if None in row or None in row.values():
        raise ValueError("Неправильна кількість полів.")
    category = row["category"].strip()
    if category not in categories:
        raise ValueError(f"Невідома категорія: {category}.")
    return OrderItemRecord(
        order_id=int(row["order_id"]),
        dish=row["dish"].strip(),
        category=category,
        price=float(row["price"]),
        quantity=int(row["quantity"]),
    )


def validate_records(
    rows: Iterable[dict[str, str]], categories: set[str], stats: Counter[str]
) -> Iterator[OrderItemRecord]:
    """Yield only correct records and count valid and invalid rows in stats."""
    for row in rows:
        try:
            record = to_record(row, categories)
        except ValueError:
            stats["invalid"] += 1
            continue
        stats["valid"] += 1
        yield record
