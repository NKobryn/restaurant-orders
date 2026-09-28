"""Custom iterator and infinite generator of order numbers."""

from collections.abc import Iterator
from itertools import count


class OrderIdSequence:
    """Iterator over order numbers start, start + 1, ..., start + amount - 1."""

    def __init__(self, start: int, amount: int) -> None:
        self.current = start
        self.stop = start + amount

    def __iter__(self) -> "OrderIdSequence":
        return self

    def __next__(self) -> int:
        if self.current >= self.stop:
            raise StopIteration
        value = self.current
        self.current += 1
        return value


def endless_order_ids(start: int = 1) -> Iterator[int]:
    """Yield order numbers without end; limit the result with islice."""
    yield from count(start)
