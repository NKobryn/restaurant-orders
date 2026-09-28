"""Cleaning and parsing of CSV lines."""

import csv
from collections.abc import Iterable, Iterator

HEADER = "order_id,dish,category,price,quantity"


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Strip line ends and skip empty lines, comments and repeated headers."""
    header_seen = False
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text == HEADER:
            if header_seen:
                continue
            header_seen = True
        yield text


def parse_rows(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    """Turn CSV lines into dictionaries with column names as keys."""
    yield from csv.DictReader(lines)
