"""Measurement tools for laboratory work 9: benchmarks, speedup, CSV results, text charts, cProfile and tracemalloc.

Profile of the order history statistics: python -m restaurant_orders.profiling
"""

import cProfile
import csv
import io
import pstats
import timeit
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

from restaurant_orders.analytics import (
    generate_order_history,
    menu_by_name,
    statistics_numpy,
    statistics_python,
    to_arrays,
)

RESULT_FIELDS = [
    "experiment",
    "dataset",
    "method",
    "workers",
    "run1",
    "run2",
    "run3",
    "run4",
    "run5",
    "mean",
    "speedup",
]


@dataclass(slots=True)
class Measurement:
    """Times of several runs of one function and the result of the last run."""

    name: str
    times: list[float]
    result: Any

    @property
    def mean(self) -> float:
        return mean(self.times)


def benchmark_repeated(name: str, function: Callable[..., Any], *args: Any, repeats: int = 5) -> Measurement:
    """Run function repeats times and measure every run with perf_counter."""
    times: list[float] = []
    result: Any = None
    for _ in range(repeats):
        start = perf_counter()
        result = function(*args)
        times.append(perf_counter() - start)
    return Measurement(name, times, result)


def timeit_best(function: Callable[[], Any], number: int, repeat: int = 5) -> float:
    """Return the best time of one call measured by timeit (number calls in each of repeat series)."""
    return min(timeit.repeat(function, number=number, repeat=repeat)) / number


def calculate_speedup(baseline: float, optimized: float) -> float:
    """Return how many times the optimized version is faster than the baseline."""
    return baseline / optimized


def result_row(
    experiment: str, dataset: int | str, measurement: Measurement, workers: int | str, baseline: float
) -> dict[str, Any]:
    """Build one row of the results table."""
    row: dict[str, Any] = {"experiment": experiment, "dataset": dataset, "method": measurement.name, "workers": workers}
    for number, elapsed in enumerate(measurement.times, start=1):
        row[f"run{number}"] = f"{elapsed:.4f}"
    row["mean"] = f"{measurement.mean:.4f}"
    row["speedup"] = f"{calculate_speedup(baseline, measurement.mean):.2f}"
    return row


def update_results_csv(path: Path, experiment: str, rows: list[dict[str, Any]]) -> None:
    """Replace the rows of one experiment in the CSV file and keep the rows of other experiments."""
    kept: list[dict[str, Any]] = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as file:
            kept = [row for row in csv.DictReader(file) if row["experiment"] != experiment]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(kept + rows)


def print_table(rows: list[dict[str, Any]]) -> None:
    """Print result rows as a text table."""
    print(f"{'Dataset':>9} | {'Method':<26} | {'Workers':>7} | {'Runs, s':<39} | {'Mean, s':>8} | {'Speedup':>7}")
    for row in rows:
        runs = " ".join(str(row.get(f"run{number}", "")) for number in range(1, 6))
        print(
            f"{row['dataset']:>9} | {row['method']:<26} | {row['workers']:>7} | {runs:<39} | "
            f"{row['mean']:>8} | {row['speedup'] + '×':>7}"
        )


def bar_chart(values: dict[str, float], unit: str, width: int = 40) -> list[str]:
    """Return a horizontal text bar chart: one line per value."""
    largest = max(values.values())
    label_width = max(len(label) for label in values)
    lines = []
    for label, value in values.items():
        bar = "█" * max(1, round(value / largest * width))
        lines.append(f"{label:<{label_width}} │{bar} {value:.4g} {unit}")
    return lines


def profile_call(function: Callable[..., Any], *args: Any, limit: int = 12) -> str:
    """Profile one call with cProfile and return the pstats report sorted by cumulative time."""
    profiler = cProfile.Profile()
    profiler.enable()
    function(*args)
    profiler.disable()
    stream = io.StringIO()
    statistics = pstats.Stats(profiler, stream=stream)
    statistics.strip_dirs().sort_stats("cumulative").print_stats(limit)
    return stream.getvalue()


def peak_memory(function: Callable[..., Any], *args: Any) -> tuple[Any, float, float]:
    """Run function under tracemalloc; return (result, memory kept by the result in MB, peak memory in MB)."""
    tracemalloc.start()
    try:
        result = function(*args)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, current / 1024**2, peak / 1024**2


def top_allocations(function: Callable[..., Any], *args: Any, limit: int = 5) -> list[str]:
    """Return the source lines that allocated the most memory while function was running."""
    tracemalloc.start()
    try:
        result = function(*args)
        snapshot = tracemalloc.take_snapshot()
    finally:
        tracemalloc.stop()
    del result
    lines = []
    for stat in snapshot.statistics("lineno")[:limit]:
        frame = stat.traceback[0]
        lines.append(f"{Path(frame.filename).name}:{frame.lineno}: {stat.size / 1024**2:.1f} MB, блоків {stat.count}")
    return lines


def run_profile(size: int = 1_000_000) -> None:
    """Profile the generation and the statistics of a large order history (time and memory)."""
    menu = menu_by_name()
    history, history_mb, generation_peak_mb = peak_memory(generate_order_history, size)
    print(f"Історія: {size} замовлень, {len(history)} позицій")
    print(f"tracemalloc: історія займає {history_mb:.1f} MB, пік під час генерації {generation_peak_mb:.1f} MB")
    print(f"Найбільші виділення пам'яті (генерація {size // 10} замовлень):")
    for line in top_allocations(generate_order_history, size // 10, limit=3):
        print("  " + line)
    _, _, statistics_peak_mb = peak_memory(statistics_python, history, menu)
    print(f"tracemalloc: пік під час statistics_python {statistics_peak_mb:.2f} MB")
    print("cProfile ДО оптимізації: statistics_python")
    print(profile_call(statistics_python, history, menu))
    arrays = to_arrays(history, menu)
    print("cProfile ПІСЛЯ оптимізації: statistics_numpy")
    print(profile_call(statistics_numpy, arrays, menu, limit=8))


if __name__ == "__main__":
    run_profile()
