"""Experiment 3: all branches of classify_order, including both boundaries."""

import pytest
from order_size import classify_order


@pytest.mark.parametrize(
    ("total", "size"),
    [(1200, "large"), (1000, "large"), (999.99, "medium"), (300, "medium"), (299.99, "small"), (100, "small")],
)
def test_classify_order(total: float, size: str) -> None:
    assert classify_order(total) == size
