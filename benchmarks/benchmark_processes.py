"""Benchmark of processes: scaling of ProcessPoolExecutor for dataset sizes and workers, cost of serialization.

Run from the project root: python benchmarks/benchmark_processes.py
"""

import os
import pickle
import tempfile
from pathlib import Path
from typing import Any

from restaurant_orders.analytics import generate_order_history, menu_by_name, statistics_python
from restaurant_orders.parallel import (
    statistics_from_files,
    statistics_from_files_processes,
    statistics_multiprocessing,
    statistics_processes,
    write_order_files,
)
from restaurant_orders.profiling import (
    bar_chart,
    benchmark_repeated,
    calculate_speedup,
    print_table,
    result_row,
    update_results_csv,
)

RESULTS = Path(__file__).parent / "results" / "benchmark_results.csv"
SIZES = (10_000, 100_000, 1_000_000)
WORKERS = (1, 2, 4, 8)
REPEATS = 5


def benchmark_scaling() -> list[dict[str, Any]]:
    """Statistics of a history already loaded in memory: Sequential against ProcessPoolExecutor."""
    menu = menu_by_name()
    rows = []
    for size in SIZES:
        history = generate_order_history(size)
        baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
        rows.append(result_row("processes_memory", size, baseline, 1, baseline.mean))
        for workers in WORKERS:
            processes = benchmark_repeated(
                "ProcessPoolExecutor", statistics_processes, history, menu, workers, repeats=REPEATS
            )
            assert processes.result == baseline.result
            rows.append(result_row("processes_memory", size, processes, workers, baseline.mean))
        if size == SIZES[-1]:
            process_objects = benchmark_repeated(
                "multiprocessing.Process", statistics_multiprocessing, history, menu, 4, repeats=REPEATS
            )
            assert process_objects.result == baseline.result
            rows.append(result_row("processes_memory", size, process_objects, 4, baseline.mean))
            serialization = benchmark_repeated("pickle.dumps(history)", pickle.dumps, history, repeats=REPEATS)
            print(f"Серіалізація історії {size} замовлень для передавання процесам: {serialization.mean:.3f} s")
    return rows


def benchmark_files(size: int, files: int) -> list[dict[str, Any]]:
    """Every process reads and aggregates its own files: only small partial results are serialized."""
    menu = menu_by_name()
    history = generate_order_history(size)
    expected = statistics_python(history, menu)
    with tempfile.TemporaryDirectory() as directory:
        paths = write_order_files(history, Path(directory), files)
        baseline = benchmark_repeated("Sequential files", statistics_from_files, paths, menu, repeats=REPEATS)
        assert baseline.result == expected
        rows = [result_row("processes_files", size, baseline, 1, baseline.mean)]
        for workers in WORKERS:
            processes = benchmark_repeated(
                "ProcessPoolExecutor files", statistics_from_files_processes, paths, menu, workers, repeats=REPEATS
            )
            assert processes.result == expected
            rows.append(result_row("processes_files", size, processes, workers, baseline.mean))
    return rows


def speedup_chart(rows: list[dict[str, Any]], size: int, method: str) -> None:
    """Print the speedup of a method for every number of workers."""
    baseline = next(float(row["mean"]) for row in rows if row["dataset"] == size and row["method"].startswith("Sequential"))
    chart = {
        f"workers={row['workers']}": calculate_speedup(baseline, float(row["mean"]))
        for row in rows
        if row["dataset"] == size and row["method"] == method
    }
    print("\n".join("  " + line for line in bar_chart(chart, "×")))


def main() -> None:
    print(f"CPU: {os.cpu_count()} (os.cpu_count())")
    print("1. Статистика історії в пам'яті: Sequential проти ProcessPoolExecutor")
    memory_rows = benchmark_scaling()
    print_table(memory_rows)
    print("Speedup ProcessPoolExecutor, 1 000 000 замовлень:")
    speedup_chart(memory_rows, 1_000_000, "ProcessPoolExecutor")

    print("\n2. Кожен процес читає й агрегує свої файли (8 CSV-файлів, 1 000 000 замовлень)")
    file_rows = benchmark_files(1_000_000, 8)
    print_table(file_rows)
    print("Speedup ProcessPoolExecutor files, 1 000 000 замовлень:")
    speedup_chart(file_rows, 1_000_000, "ProcessPoolExecutor files")

    update_results_csv(RESULTS, "processes_memory", memory_rows)
    update_results_csv(RESULTS, "processes_files", file_rows)
    print("Результати збережено: benchmarks/results/benchmark_results.csv")


if __name__ == "__main__":
    main()
