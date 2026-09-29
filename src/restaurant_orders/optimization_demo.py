"""Optimization demo of laboratory work 9: statistics of the order history.

python -m restaurant_orders.optimization_demo — correctness and speed of every implementation, threads, caching, Lock.
Detailed experiments: python benchmarks/benchmark_*.py; profile: python -m restaurant_orders.profiling.
"""

import os
import platform
import tempfile
from pathlib import Path

from restaurant_orders.analytics import (
    OrderHistory,
    OrderStatistics,
    cached_statistics,
    generate_order_history,
    menu_by_name,
    order_totals_python,
    statistics_numpy,
    statistics_numpy_from_history,
    statistics_python,
    to_arrays,
)
from restaurant_orders.parallel import (
    ProcessedCounter,
    count_in_threads,
    load_files_sequential,
    load_files_threads,
    statistics_multiprocessing,
    statistics_processes,
    statistics_threads,
    write_order_files,
)
from restaurant_orders.profiling import bar_chart, benchmark_repeated, calculate_speedup

HISTORY_SIZE = 1_000_000
WORKERS = 4
REPEATS = 3


def print_statistics(statistics: OrderStatistics) -> None:
    """Print the statistics of an order history."""
    number, total = statistics.most_expensive_order
    print(f"  замовлень: {statistics.orders_count}, оборот: {statistics.turnover:.2f} грн")
    print(f"  середній чек: {statistics.average_check:.2f} грн; найдорожче замовлення: №{number} — {total:.2f} грн")
    print(f"  найпопулярніша страва: {statistics.most_popular_dish[0]} ({statistics.most_popular_dish[1]} порцій)")
    print(f"  найбільша виручка: {statistics.top_revenue_dish[0]} ({statistics.top_revenue_dish[1]:.2f} грн)")
    for category, (portions, revenue) in statistics.categories.items():
        print(f"  {category}: {portions} порцій, {revenue:.2f} грн")


def show_basic_features() -> None:
    """Basic features of the project on a small order history: orders, items, totals, cache."""
    orders = OrderHistory([], menu_by_name())
    for order_id, name, quantity in [(1, "Борщ", 2), (1, "Узвар", 1), (2, "Стейк", 1), (2, "Капучино", 2)]:
        orders.add_item(order_id, name, quantity)
    statistics = orders.statistics()
    totals = order_totals_python(orders.items, orders.menu)
    print("1. БАЗОВІ МОЖЛИВОСТІ: замовлення №1 (Борщ×2, Узвар), №2 (Стейк, Капучино×2)")
    print(
        f"  суми: {', '.join(f'№{number} — {total:.2f} грн' for number, total in totals.items())}; "
        f"середня вартість: {statistics.average_check:.2f} грн; найдорожче — №{statistics.most_expensive_order[0]}"
    )


def compare_implementations(history_size: int) -> None:
    """Measure every implementation and check that it returns the same statistics."""
    menu = menu_by_name()
    history = generate_order_history(history_size)
    arrays = to_arrays(history, menu)
    print(f"\n2. ІСТОРІЯ: {history_size} замовлень, {len(history)} позицій (seed 42)")
    baseline = benchmark_repeated("Sequential", statistics_python, history, menu, repeats=REPEATS)
    print_statistics(baseline.result)
    measurements = [
        baseline,
        benchmark_repeated(
            f"ThreadPoolExecutor({WORKERS})", statistics_threads, history, menu, WORKERS, repeats=REPEATS
        ),
        benchmark_repeated(
            f"ProcessPoolExecutor({WORKERS})", statistics_processes, history, menu, WORKERS, repeats=REPEATS
        ),
        benchmark_repeated(
            f"multiprocessing.Process({WORKERS})", statistics_multiprocessing, history, menu, WORKERS, repeats=REPEATS
        ),
        benchmark_repeated("NumPy + to_arrays", statistics_numpy_from_history, history, menu, repeats=REPEATS),
        benchmark_repeated("NumPy (arrays ready)", statistics_numpy, arrays, menu, repeats=REPEATS),
    ]
    print(f"\n3. РЕАЛІЗАЦІЇ (середнє з {REPEATS} запусків, perf_counter)")
    for measurement in measurements:
        same = "так" if measurement.result == baseline.result else "НІ"
        speedup = calculate_speedup(baseline.mean, measurement.mean)
        print(
            f"  {measurement.name:<30} {measurement.mean:8.4f} s  speedup {speedup:6.2f}×  результат збігається: {same}"
        )
    print("\n".join("  " + line for line in bar_chart({m.name: m.mean for m in measurements}, "s", width=30)))


def show_threads_for_files() -> None:
    """ThreadPoolExecutor for reading order files from a slow storage."""
    history = generate_order_history(100_000)
    with tempfile.TemporaryDirectory() as directory:
        paths = write_order_files(history, Path(directory), 16)
        sequential = benchmark_repeated("Sequential", load_files_sequential, paths, None, 0.05, repeats=1)
        threads = benchmark_repeated("ThreadPoolExecutor(8)", load_files_threads, paths, 8, None, 0.05, repeats=1)
    same = "так" if sequential.result == threads.result == history else "НІ"
    print("\n4. ФАЙЛИ ЗАМОВЛЕНЬ: 16 CSV-файлів, повільне сховище (очікування 0.05 с на файл)")
    print(
        f"  послідовно {sequential.mean:.3f} s, ThreadPoolExecutor(8) {threads.mean:.3f} s, "
        f"speedup {calculate_speedup(sequential.mean, threads.mean):.2f}×, дані збігаються: {same}"
    )


def show_caching(history_size: int) -> None:
    """Cache hit, miss and invalidation after a change of the price or of an order."""
    cached_statistics.cache_clear()
    orders = OrderHistory(generate_order_history(history_size), menu_by_name())
    cold = benchmark_repeated("cold", orders.statistics, repeats=1)
    warm = benchmark_repeated("warm", orders.statistics, repeats=1)
    print(f"\n5. CACHING ({history_size} замовлень, lru_cache з версією даних)")
    print(f"  cold cache: {cold.mean:.4f} s; warm cache: {warm.mean * 1e6:.1f} µs; {cached_statistics.cache_info()}")
    before = cold.result.turnover
    orders.change_price("Борщ", 100.0)
    changed = orders.statistics()
    print(f"  ціна Борщу 95 → 100 грн (версія {orders.version}): оборот {before:.2f} → {changed.turnover:.2f} грн")
    orders.add_item(1, "Стейк", 1)
    added = orders.statistics()
    print(
        f"  +Стейк у замовлення №1 (версія {orders.version}): оборот {added.turnover:.2f} грн; "
        f"{cached_statistics.cache_info()}"
    )


def show_race_condition() -> None:
    """A shared counter without and with a Lock."""
    unsafe = count_in_threads(ProcessedCounter(use_lock=False), threads=4, increments=1_000)
    safe = count_in_threads(ProcessedCounter(use_lock=True), threads=4, increments=1_000)
    print("\n6. SYNCHRONIZATION: 4 потоки × 1000 збільшень спільного лічильника (очікується 4000)")
    print(f"  без Lock: {unsafe} (race condition), з Lock: {safe}")


def main() -> None:
    print("ОПТИМІЗАЦІЯ ОБЛІКУ ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №9, варіант №11)")
    print(f"Python {platform.python_version()}, {platform.system()} {platform.machine()}, CPU: {os.cpu_count()}")
    show_basic_features()
    compare_implementations(HISTORY_SIZE)
    show_threads_for_files()
    show_caching(HISTORY_SIZE)
    show_race_condition()


if __name__ == "__main__":
    main()
