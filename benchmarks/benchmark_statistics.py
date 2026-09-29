"""Benchmark of the order history statistics: baseline for three dataset sizes.

Run from the project root: python benchmarks/benchmark_statistics.py
"""

import os
import platform
from pathlib import Path

from restaurant_orders.analytics import generate_order_history, menu_by_name, statistics_python
from restaurant_orders.profiling import bar_chart, benchmark_repeated, print_table, result_row, update_results_csv

RESULTS = Path(__file__).parent / "results" / "benchmark_results.csv"
SIZES = (10_000, 100_000, 1_000_000)
REPEATS = 5


def main() -> None:
    print(f"Python {platform.python_version()}, {platform.system()} {platform.machine()}, CPU: {os.cpu_count()}")
    menu = menu_by_name()
    rows = []
    for size in SIZES:
        history = generate_order_history(size)
        print(f"Замовлень: {size}, позицій: {len(history)}")
        baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
        rows.append(result_row("statistics", size, baseline, 1, baseline.mean))
    print_table(rows)
    print("\n".join(bar_chart({f"{row['dataset']:>9}": float(row["mean"]) for row in rows}, "s")))
    update_results_csv(RESULTS, "statistics", rows)
    print("Результати збережено: benchmarks/results/benchmark_results.csv")


if __name__ == "__main__":
    main()
