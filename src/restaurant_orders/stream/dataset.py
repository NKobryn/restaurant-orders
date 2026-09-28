"""Generator of large CSV files with order positions for experiments."""

import csv
import random
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from restaurant_orders.data import MENU
from restaurant_orders.stream.iterators import endless_order_ids
from restaurant_orders.stream.parsers import HEADER

GENERATED_DIR = Path("data") / "generated"
INVALID_SHARE = 0.01
SEED = 11


def generate_rows(rng: random.Random) -> Iterator[list[str]]:
    """Yield rows of orders without end; about 1% of rows get an empty field."""
    for order_id in endless_order_ids(1):
        for dish in rng.sample(MENU, rng.randint(1, 4)):
            row = [str(order_id), dish.name, dish.category, f"{dish.price:.2f}", str(rng.randint(1, 3))]
            if rng.random() < INVALID_SHARE:
                row[rng.randint(1, 4)] = ""
            yield row


def ensure_dataset(records: int) -> Path:
    """Create data/generated/orders_<records>.csv once and return its path."""
    path = GENERATED_DIR / f"orders_{records}.csv"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER.split(","))
            writer.writerows(islice(generate_rows(random.Random(SEED)), records))
    return path
