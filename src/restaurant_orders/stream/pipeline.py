"""Stages of the streaming pipeline and its assembly."""

from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import groupby, islice
from pathlib import Path
from typing import Any

from restaurant_orders.data import MENU
from restaurant_orders.models import OrderItemRecord, OrderSummary
from restaurant_orders.stream.parsers import clean_lines, parse_rows
from restaurant_orders.stream.readers import read_many
from restaurant_orders.stream.validation import validate_records

ALLOWED_CATEGORIES: set[str] = {dish.category for dish in MENU}


def read_records(paths: Iterable[Path], stats: Counter[str]) -> Iterator[OrderItemRecord]:
    """Source part of the pipeline: files -> lines -> rows -> valid records."""
    lines = clean_lines(read_many(paths))
    return validate_records(parse_rows(lines), ALLOWED_CATEGORIES, stats)


def sort_by_order(records: Iterable[OrderItemRecord]) -> list[OrderItemRecord]:
    """Sort records by order number (eager: all records are kept in memory)."""
    return sorted(records, key=lambda record: record.order_id)


def summarize_orders(records: Iterable[OrderItemRecord]) -> Iterator[OrderSummary]:
    """Group consecutive records of one order and yield the order summary."""
    for order_id, group in groupby(records, key=lambda record: record.order_id):
        items = list(group)
        yield OrderSummary(
            order_id=order_id,
            items_count=len(items),
            total=sum(item.line_total for item in items),
            most_expensive=max(items, key=lambda item: item.price),
        )


def batched(items: Iterable[Any], size: int) -> Iterator[list[Any]]:
    """Yield lists of size items; the last list may be shorter."""
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def build_pipeline(paths: Iterable[Path], stats: Counter[str]) -> Iterator[OrderSummary]:
    """Lazy pipeline for files already sorted by order number."""
    return summarize_orders(read_records(paths, stats))
