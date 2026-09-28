"""Small functions for the testing experiments of laboratory work 6 (one has a deliberate bug)."""

import random


def apply_discount(price: float, percent: float) -> float:
    """Return the price after a percentage discount. BUG on purpose: divides by 10 instead of 100."""
    return price * (1 - percent / 10)


def free_table() -> int:
    """Return a random table number 1 or 2 (a source of flaky tests)."""
    return random.randint(1, 2)
