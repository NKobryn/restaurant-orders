"""Experiment 3: only two of three results of classify_order are checked."""

from order_size import classify_order


def test_large_order() -> None:
    assert classify_order(1200) == "large"


def test_medium_order() -> None:
    assert classify_order(500) == "medium"
