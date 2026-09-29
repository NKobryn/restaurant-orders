"""Experiment: eager and lazy processing of the same files."""

import platform
import tracemalloc
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any

from restaurant_orders.models import OrderSummary
from restaurant_orders.stream.analytics import OrdersStatistics, collect_statistics
from restaurant_orders.stream.dataset import ensure_dataset
from restaurant_orders.stream.filters import find_first
from restaurant_orders.stream.parsers import clean_lines, parse_rows
from restaurant_orders.stream.pipeline import ALLOWED_CATEGORIES, build_pipeline, summarize_orders
from restaurant_orders.stream.readers import read_lines
from restaurant_orders.stream.validation import validate_records

SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
EARLY_RECORDS = 1_000_000
REPEATS = 3


def eager_orders(path: Path) -> list[OrderSummary]:
    """Eager version: every stage builds a complete list before the next one."""
    lines = list(clean_lines(read_lines(path)))
    rows = list(parse_rows(lines))
    records = list(validate_records(rows, ALLOWED_CATEGORIES, Counter()))
    return list(summarize_orders(records))


def eager_statistics(path: Path) -> OrdersStatistics:
    """Statistics computed from fully materialised lists."""
    return collect_statistics(eager_orders(path))


def lazy_statistics(path: Path) -> OrdersStatistics:
    """Statistics computed while records flow through generators."""
    return collect_statistics(build_pipeline([path], Counter()))


def best_time(action: Callable[[], Any]) -> float:
    """Return the best of REPEATS runs in seconds."""
    times = []
    for _ in range(REPEATS):
        start = perf_counter()
        action()
        times.append(perf_counter() - start)
    return min(times)


def peak_memory_mb(action: Callable[[], Any]) -> float:
    """Return the peak memory allocated during the action, in megabytes."""
    tracemalloc.start()
    action()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024 / 1024


def compare_size(records: int) -> tuple[float, ...]:
    """Measure eager and lazy variants for one file."""
    path = ensure_dataset(records)
    if eager_statistics(path) != lazy_statistics(path):
        raise RuntimeError("eager і lazy дали різні результати")
    return (
        best_time(lambda: eager_statistics(path)),
        best_time(lambda: lazy_statistics(path)),
        peak_memory_mb(lambda: eager_statistics(path)),
        peak_memory_mb(lambda: lazy_statistics(path)),
        best_time(lambda: eager_orders(path)[0]) * 1000,
        best_time(lambda: next(build_pipeline([path], Counter()))) * 1000,
    )


def early_termination() -> None:
    """Find the first large order in 1 000 000 records with eager and lazy search."""
    path = ensure_dataset(EARLY_RECORDS)

    def condition(order: OrderSummary) -> bool:
        return order.total >= 1800

    def eager_search() -> OrderSummary:
        return [order for order in eager_orders(path) if condition(order)][0]

    def lazy_search() -> OrderSummary | None:
        return find_first(build_pipeline([path], Counter()), condition)

    found = lazy_search()
    if found is None or eager_search() != found:
        raise RuntimeError("eager і lazy знайшли різні замовлення")
    print(f"\nEARLY TERMINATION: {EARLY_RECORDS} записів, умова: сума замовлення >= 1800 грн")
    print(f"Знайдено замовлення №{found.order_id} на {found.total:.2f} грн (обидва варіанти)")
    print(f"{'Варіант':<8} | {'час, с':>8} | {'пік пам., МБ':>12}")
    print("-" * 34)
    for name, search in (("eager", eager_search), ("lazy", lazy_search)):
        print(f"{name:<8} | {best_time(search):>8.3f} | {peak_memory_mb(search):>12.2f}")


def main() -> None:
    """Run the eager/lazy experiment and print the results tables."""
    print("ЕКСПЕРИМЕНТ: EAGER ПРОТИ LAZY")
    print(f"Python {platform.python_version()}, {platform.system()} {platform.machine()}")
    print(f"Час: найкращий із {REPEATS} запусків (perf_counter); пам'ять: пік tracemalloc\n")
    header = (
        f"{'Записів':>8} | {'eager, с':>8} | {'lazy, с':>8} | {'eager, МБ':>9} | "
        f"{'lazy, МБ':>8} | {'1-й eager, мс':>13} | {'1-й lazy, мс':>12}"
    )
    print(header)
    print("-" * len(header))
    for records in SIZES:
        eager_s, lazy_s, eager_mb, lazy_mb, eager_first, lazy_first = compare_size(records)
        print(
            f"{records:>8} | {eager_s:>8.3f} | {lazy_s:>8.3f} | {eager_mb:>9.2f} | "
            f"{lazy_mb:>8.2f} | {eager_first:>13.2f} | {lazy_first:>12.3f}"
        )
    early_termination()


if __name__ == "__main__":
    main()
