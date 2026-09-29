"""Parallel processing of the order history: threads, processes and synchronization (laboratory work 9)."""

import csv
import multiprocessing
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from restaurant_orders.analytics import (
    HistoryItem,
    OrderStatistics,
    Sales,
    build_statistics,
    dish_sales_python,
    most_expensive_order,
    order_totals_python,
)
from restaurant_orders.models import Dish

# Statistics of one part of the history: (orders, turnover, most expensive order, sales of dishes).
PartialStatistics = tuple[int, float, tuple[int, float], dict[str, Sales]]


def split_by_orders(history: list[HistoryItem], parts: int) -> list[list[HistoryItem]]:
    """Split the history into parts of similar size; positions of one order always stay in the same part.

    The history must be grouped by orders, as it is generated and saved to files.
    """
    step = -(-len(history) // parts)
    chunks: list[list[HistoryItem]] = []
    start = 0
    while start < len(history):
        end = min(start + step, len(history))
        while end < len(history) and history[end][0] == history[end - 1][0]:
            end += 1
        chunks.append(history[start:end])
        start = end
    return chunks


def partial_statistics(history: list[HistoryItem], menu: dict[str, Dish]) -> PartialStatistics:
    """Aggregate one part of the history (runs in a thread or in a separate process)."""
    totals = order_totals_python(history, menu)
    return len(totals), sum(totals.values()), most_expensive_order(totals), dish_sales_python(history, menu)


def merge_statistics(parts: list[PartialStatistics], menu: dict[str, Dish]) -> OrderStatistics:
    """Combine partial statistics into the statistics of the whole history."""
    best_order = (0, 0.0)
    dish_sales: dict[str, Sales] = dict.fromkeys(menu, (0, 0.0))
    for _, _, (number, total), sales in parts:
        if total > best_order[1] or (total == best_order[1] and number < best_order[0]):
            best_order = (number, total)
        for name, (portions, revenue) in sales.items():
            dish_sales[name] = (dish_sales[name][0] + portions, dish_sales[name][1] + revenue)
    orders_count = sum(part[0] for part in parts)
    turnover = sum(part[1] for part in parts)
    return build_statistics(orders_count, turnover, best_order, dish_sales, menu)


def statistics_threads(history: list[HistoryItem], menu: dict[str, Dish], workers: int = 4) -> OrderStatistics:
    """Statistics with ThreadPoolExecutor: every thread aggregates its part of the history."""
    chunks = split_by_orders(history, workers)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(partial_statistics, chunks, [menu] * len(chunks)))
    return merge_statistics(parts, menu)


def statistics_processes(history: list[HistoryItem], menu: dict[str, Dish], workers: int = 4) -> OrderStatistics:
    """Statistics with ProcessPoolExecutor: every process aggregates its part on its own CPU core."""
    chunks = split_by_orders(history, workers)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(partial_statistics, chunks, [menu] * len(chunks)))
    return merge_statistics(parts, menu)


def _process_worker(
    index: int, history: list[HistoryItem], menu: dict[str, Dish], results: "multiprocessing.Queue[tuple[int, PartialStatistics]]"
) -> None:
    results.put((index, partial_statistics(history, menu)))


def statistics_multiprocessing(history: list[HistoryItem], menu: dict[str, Dish], workers: int = 4) -> OrderStatistics:
    """Statistics with multiprocessing.Process objects that send partial results through a Queue."""
    chunks = split_by_orders(history, workers)
    results: "multiprocessing.Queue[tuple[int, PartialStatistics]]" = multiprocessing.Queue()
    processes = [
        multiprocessing.Process(target=_process_worker, args=(index, chunk, menu, results))
        for index, chunk in enumerate(chunks)
    ]
    for process in processes:
        process.start()
    parts = dict(results.get() for _ in processes)
    for process in processes:
        process.join()
    return merge_statistics([parts[index] for index in range(len(chunks))], menu)


# --- Files of orders (I/O) -------------------------------------------------------------------

FILE_HEADER = ["order_id", "dish", "quantity"]


def write_order_files(history: list[HistoryItem], directory: Path, parts: int) -> list[Path]:
    """Save the history into several CSV files, e.g. orders of different days or restaurants."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for number, chunk in enumerate(split_by_orders(history, parts), start=1):
        path = directory / f"orders_{number:02}.csv"
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(FILE_HEADER)
            writer.writerows(chunk)
        paths.append(path)
    return paths


class LoadProgress:
    """Numbers of loaded files and positions shared by several threads; changed only under a Lock."""

    def __init__(self) -> None:
        self.files = 0
        self.items = 0
        self._lock = threading.Lock()

    def mark_loaded(self, items: int) -> None:
        with self._lock:
            self.files += 1
            self.items += items


def load_order_file(path: Path, progress: LoadProgress | None = None, latency: float = 0.0) -> list[HistoryItem]:
    """Read one CSV file of orders; latency imitates waiting for a slow storage (network disk) before reading."""
    if latency:
        time.sleep(latency)
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        next(reader)
        items = [(int(order_id), dish, int(quantity)) for order_id, dish, quantity in reader]
    if progress is not None:
        progress.mark_loaded(len(items))
    return items


def load_files_sequential(
    paths: list[Path], progress: LoadProgress | None = None, latency: float = 0.0
) -> list[HistoryItem]:
    """Read the files one after another."""
    history: list[HistoryItem] = []
    for path in paths:
        history.extend(load_order_file(path, progress, latency))
    return history


def load_files_threads(
    paths: list[Path], workers: int = 4, progress: LoadProgress | None = None, latency: float = 0.0
) -> list[HistoryItem]:
    """Read the files with ThreadPoolExecutor; the result keeps the order of the files."""
    count = len(paths)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        loaded = executor.map(load_order_file, paths, [progress] * count, [latency] * count)
        history: list[HistoryItem] = []
        for items in loaded:
            history.extend(items)
    return history


def file_statistics(path: Path, menu: dict[str, Dish]) -> PartialStatistics:
    """Read one file and aggregate it; only the small partial result goes back to the main process."""
    return partial_statistics(load_order_file(path), menu)


def statistics_from_files(paths: list[Path], menu: dict[str, Dish]) -> OrderStatistics:
    """Read and aggregate the files one after another."""
    return merge_statistics([file_statistics(path, menu) for path in paths], menu)


def statistics_from_files_processes(paths: list[Path], menu: dict[str, Dish], workers: int = 4) -> OrderStatistics:
    """Read and aggregate the files with ProcessPoolExecutor: every process works with its own files."""
    with ProcessPoolExecutor(max_workers=workers) as executor:
        parts = list(executor.map(file_statistics, paths, [menu] * len(paths)))
    return merge_statistics(parts, menu)


# --- Race condition and Lock ------------------------------------------------------------------


class ProcessedCounter:
    """Counter of processed orders; without a Lock it shows a race condition."""

    def __init__(self, use_lock: bool) -> None:
        self.value = 0
        self._lock = threading.Lock() if use_lock else None

    def increment(self) -> None:
        if self._lock is None:
            self._unsafe_increment()
        else:
            with self._lock:
                self._unsafe_increment()

    def _unsafe_increment(self) -> None:
        # read → pause → write: time.sleep(0) lets another thread run between reading and writing
        value = self.value
        time.sleep(0)
        self.value = value + 1


def count_in_threads(counter: ProcessedCounter, threads: int = 4, increments: int = 1_000) -> int:
    """Start several threading.Thread objects that increment one counter; return its final value."""

    def work() -> None:
        for _ in range(increments):
            counter.increment()

    workers = [threading.Thread(target=work, name=f"counter-{number}") for number in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    return counter.value
