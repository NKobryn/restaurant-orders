"""Benchmark of the order history statistics: all implementations for three dataset sizes.

Run from the project root: python benchmarks/benchmark_statistics.py
"""

import os
import platform
from pathlib import Path

from restaurant_orders.analytics import (
    generate_order_history,
    menu_by_name,
    statistics_numpy,
    statistics_python,
    to_arrays,
)
from restaurant_orders.parallel import statistics_processes, statistics_threads
from restaurant_orders.profiling import bar_chart, benchmark_repeated, print_table, result_row, update_results_csv

RESULTS = Path(__file__).parent / "results" / "benchmark_results.csv"
SIZES = (10_000, 100_000, 1_000_000)
REPEATS = 5
WORKERS = 4


def main() -> None:
    print(f"Python {platform.python_version()}, {platform.system()} {platform.machine()}, CPU: {os.cpu_count()}")
    menu = menu_by_name()
    rows = []
    for size in SIZES:
        history = generate_order_history(size)
        print(f"Замовлень: {size}, позицій: {len(history)}")
        baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
        rows.append(result_row("statistics", size, baseline, 1, baseline.mean))
        threads = benchmark_repeated("ThreadPoolExecutor", statistics_threads, history, menu, WORKERS, repeats=REPEATS)
        assert threads.result == baseline.result
        rows.append(result_row("statistics", size, threads, WORKERS, baseline.mean))
        processes = benchmark_repeated(
            "ProcessPoolExecutor", statistics_processes, history, menu, WORKERS, repeats=REPEATS
        )
        assert processes.result == baseline.result
        rows.append(result_row("statistics", size, processes, WORKERS, baseline.mean))
        vectorized = benchmark_repeated("NumPy", statistics_numpy, to_arrays(history, menu), menu, repeats=REPEATS)
        assert vectorized.result == baseline.result
        rows.append(result_row("statistics", size, vectorized, "–", baseline.mean))
    print_table(rows)
    for size in SIZES:
        print(f"Час виконання, {size} замовлень:")
        chart = {row["method"]: float(row["mean"]) for row in rows if row["dataset"] == size}
        print("\n".join("  " + line for line in bar_chart(chart, "s")))
    update_results_csv(RESULTS, "statistics", rows)
    print("Результати збережено: benchmarks/results/benchmark_results.csv")


if __name__ == "__main__":
    main()
