"""Benchmark of threads: CPU-bound statistics (GIL), reading order files, race condition and Lock.

Run from the project root: python benchmarks/benchmark_threads.py
"""

import tempfile
from pathlib import Path

from restaurant_orders.analytics import generate_order_history, menu_by_name, statistics_python
from restaurant_orders.parallel import (
    LoadProgress,
    ProcessedCounter,
    count_in_threads,
    load_files_sequential,
    load_files_threads,
    statistics_threads,
    write_order_files,
)
from restaurant_orders.profiling import benchmark_repeated, print_table, result_row, update_results_csv

RESULTS = Path(__file__).parent / "results" / "benchmark_results.csv"
WORKERS = (1, 2, 4, 8)
REPEATS = 5
LATENCY = 0.05


def benchmark_statistics_threads(size: int) -> list[dict[str, object]]:
    """CPU-bound statistics: Sequential against ThreadPoolExecutor."""
    menu = menu_by_name()
    history = generate_order_history(size)
    expected = statistics_python(history, menu)
    baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
    rows = [result_row("threads_cpu", size, baseline, 1, baseline.mean)]
    for workers in WORKERS:
        threads = benchmark_repeated("ThreadPoolExecutor", statistics_threads, history, menu, workers, repeats=REPEATS)
        assert threads.result == expected
        rows.append(result_row("threads_cpu", size, threads, workers, baseline.mean))
    return rows


def benchmark_files(size: int, files: int, latency: float, experiment: str) -> list[dict[str, object]]:
    """Reading order files: one after another against ThreadPoolExecutor."""
    history = generate_order_history(size)
    with tempfile.TemporaryDirectory() as directory:
        paths = write_order_files(history, Path(directory), files)
        baseline = benchmark_repeated("Sequential read", load_files_sequential, paths, None, latency, repeats=REPEATS)
        assert baseline.result == history
        rows = [result_row(experiment, size, baseline, 1, baseline.mean)]
        for workers in WORKERS:
            progress = LoadProgress()
            threads = benchmark_repeated(
                "ThreadPoolExecutor read", load_files_threads, paths, workers, progress, latency, repeats=REPEATS
            )
            assert threads.result == history
            assert (progress.files, progress.items) == (files * REPEATS, len(history) * REPEATS)
            rows.append(result_row(experiment, size, threads, workers, baseline.mean))
    return rows


def main() -> None:
    print("1. CPU-bound: статистика 1 000 000 замовлень у потоках (GIL)")
    cpu_rows = benchmark_statistics_threads(1_000_000)
    print_table(cpu_rows)

    print("\n2. Читання 8 CSV-файлів (1 000 000 замовлень) з локального диска: читання + розбір CSV")
    local_rows = benchmark_files(1_000_000, 8, 0.0, "threads_files_local")
    print_table(local_rows)

    print(f"\n3. Читання 16 CSV-файлів (100 000 замовлень) з повільного сховища: очікування {LATENCY} с на файл")
    slow_rows = benchmark_files(100_000, 16, LATENCY, "threads_files_slow")
    print_table(slow_rows)
    print("LoadProgress (спільний стан потоків під Lock): кількість файлів і позицій збіглася з очікуваною")

    print("\n4. Race condition: 4 потоки threading.Thread × 1000 збільшень лічильника (очікується 4000)")
    for use_lock in (False, True):
        value = count_in_threads(ProcessedCounter(use_lock), threads=4, increments=1_000)
        print(f"  {'з Lock   ' if use_lock else 'без Lock '}: {value}")

    for experiment, rows in (("threads_cpu", cpu_rows), ("threads_files_local", local_rows), ("threads_files_slow", slow_rows)):
        update_results_csv(RESULTS, experiment, rows)
    print("Результати збережено: benchmarks/results/benchmark_results.csv")


if __name__ == "__main__":
    main()
