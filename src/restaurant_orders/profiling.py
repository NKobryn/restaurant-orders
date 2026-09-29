"""Measurement tools for laboratory work 9: repeated benchmarks, speedup, CSV results and text charts."""

import csv
import timeit
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

RESULT_FIELDS = ["experiment", "dataset", "method", "workers", "run1", "run2", "run3", "run4", "run5", "mean", "speedup"]


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


def result_row(experiment: str, dataset: int | str, measurement: Measurement, workers: int | str, baseline: float) -> dict[str, Any]:
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
    print(f"{'Dataset':>9} | {'Method':<22} | {'Workers':>7} | {'Runs, s':<39} | {'Mean, s':>8} | {'Speedup':>7}")
    for row in rows:
        runs = " ".join(str(row.get(f"run{number}", "")) for number in range(1, 6))
        print(
            f"{row['dataset']:>9} | {row['method']:<22} | {row['workers']:>7} | {runs:<39} | "
            f"{row['mean']:>8} | {row['speedup'] + '×':>7}"
        )


def bar_chart(values: dict[str, float], unit: str, width: int = 40) -> list[str]:
    """Return a horizontal text bar chart: one line per value."""
    largest = max(values.values())
    label_width = max(len(label) for label in values)
    lines = []
    for label, value in values.items():
        bar = "█" * max(1, round(value / largest * width))
        lines.append(f"{label:<{label_width}} │{bar} {value:.3f} {unit}")
    return lines
