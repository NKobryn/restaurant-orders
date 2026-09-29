"""Benchmark of NumPy vectorization: time for three dataset sizes and memory of a Python list against arrays.

Run from the project root: python benchmarks/benchmark_numpy.py
"""

from pathlib import Path
from typing import Any

from restaurant_orders.analytics import (
    generate_order_history,
    menu_by_name,
    statistics_numpy,
    statistics_numpy_from_history,
    statistics_python,
    to_arrays,
)
from restaurant_orders.profiling import benchmark_repeated, peak_memory, print_table, result_row, update_results_csv

RESULTS = Path(__file__).parent / "results" / "benchmark_results.csv"
SIZES = (10_000, 100_000, 1_000_000)
REPEATS = 5


def benchmark_time() -> list[dict[str, Any]]:
    """Sequential against NumPy with and without the conversion of the list to arrays."""
    menu = menu_by_name()
    rows = []
    for size in SIZES:
        history = generate_order_history(size)
        arrays = to_arrays(history, menu)
        baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
        converted = benchmark_repeated(
            "NumPy + to_arrays", statistics_numpy_from_history, history, menu, repeats=REPEATS
        )
        vectorized = benchmark_repeated("NumPy (arrays ready)", statistics_numpy, arrays, menu, repeats=REPEATS)
        assert converted.result == baseline.result and vectorized.result == baseline.result
        for measurement in (baseline, converted, vectorized):
            rows.append(result_row("numpy", size, measurement, "–" if measurement is not baseline else 1, baseline.mean))
    return rows


def compare_memory(size: int) -> None:
    """Memory of the history as a Python list of tuples and as NumPy arrays (tracemalloc)."""
    menu = menu_by_name()
    history, list_mb, _ = peak_memory(generate_order_history, size)
    arrays, arrays_mb, conversion_peak_mb = peak_memory(to_arrays, history, menu)
    _, _, python_peak_mb = peak_memory(statistics_python, history, menu)
    _, _, numpy_peak_mb = peak_memory(statistics_numpy, arrays, menu)
    print(f"Пам'ять історії {size} замовлень ({len(history)} позицій), tracemalloc:")
    print(f"  {'Python list кортежів':<32}{list_mb:8.1f} MB")
    print(f"  {'NumPy-масиви (int32 + 2×uint8)':<32}{arrays_mb:8.1f} MB (пік перетворення {conversion_peak_mb:.1f} MB)")
    print(f"  {'Пік statistics_python':<32}{python_peak_mb:8.1f} MB")
    print(f"  {'Пік statistics_numpy':<32}{numpy_peak_mb:8.1f} MB")


def main() -> None:
    print("1. Час: Sequential проти NumPy")
    rows = benchmark_time()
    print_table(rows)
    print()
    compare_memory(1_000_000)
    update_results_csv(RESULTS, "numpy", rows)
    print("Результати збережено: benchmarks/results/benchmark_results.csv")


if __name__ == "__main__":
    main()
