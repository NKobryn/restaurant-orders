"""Streaming readers: lines are taken from files one by one."""

from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Yield lines of a text file without loading the whole file into memory."""
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from file


def read_many(paths: Iterable[Path]) -> Iterator[str]:
    """Yield lines of several files one after another."""
    return chain.from_iterable(read_lines(path) for path in paths)
