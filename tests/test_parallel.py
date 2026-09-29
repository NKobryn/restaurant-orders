"""Tests of laboratory work 9: correctness of every implementation, synchronization, caching and measurement tools."""

import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from restaurant_orders.analytics import (
    HistoryItem,
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
from restaurant_orders.models import Dish
from restaurant_orders.parallel import (
    LoadProgress,
    ProcessedCounter,
    count_in_threads,
    load_files_sequential,
    load_files_threads,
    split_by_orders,
    statistics_from_files,
    statistics_from_files_processes,
    statistics_multiprocessing,
    statistics_processes,
    statistics_threads,
    write_order_files,
)
from restaurant_orders.profiling import (
    bar_chart,
    benchmark_repeated,
    calculate_speedup,
    peak_memory,
    profile_call,
    result_row,
    timeit_best,
    top_allocations,
    update_results_csv,
)

SMALL_HISTORY: list[HistoryItem] = [(1, "Борщ", 2), (1, "Узвар", 1), (2, "Стейк", 1), (3, "Сирник", 1)]


@pytest.fixture
def menu() -> dict[str, Dish]:
    return menu_by_name()


@pytest.fixture(scope="module")
def history() -> list[HistoryItem]:
    return generate_order_history(3_000, seed=7)


@pytest.fixture(autouse=True)
def empty_cache() -> Iterator[None]:
    cached_statistics.cache_clear()
    yield
    cached_statistics.cache_clear()


# --- Baseline ------------------------------------------------------------------------------


def test_generated_history_is_reproducible_and_grouped_by_orders() -> None:
    history = generate_order_history(500, seed=3)
    assert history == generate_order_history(500, seed=3)
    numbers = [number for number, _, _ in history]
    assert numbers == sorted(numbers) and set(numbers) == set(range(1, 501))
    assert all(1 <= quantity <= 3 for _, _, quantity in history)


def test_baseline_statistics_of_small_history(menu: dict[str, Dish]) -> None:
    statistics = statistics_python(SMALL_HISTORY, menu)
    assert order_totals_python(SMALL_HISTORY, menu) == {1: 235.0, 2: 280.0, 3: 85.0}
    assert statistics.orders_count == 3
    assert statistics.turnover == 600.0
    assert statistics.average_check == 200.0
    assert statistics.most_expensive_order == (2, 280.0)
    assert statistics.most_popular_dish == ("Борщ", 2)
    assert statistics.top_revenue_dish == ("Стейк", 280.0)
    assert statistics.categories["Перші страви"] == (2, 190.0)
    assert statistics.categories["Напої"] == (1, 45.0)


def test_tie_of_orders_keeps_the_smallest_number(menu: dict[str, Dish]) -> None:
    history: list[HistoryItem] = [(5, "Стейк", 1), (6, "Стейк", 1)]
    for implementation in (statistics_python, statistics_numpy_from_history):
        assert implementation(history, menu).most_expensive_order == (5, 280.0)


def test_empty_history(menu: dict[str, Dish]) -> None:
    expected = statistics_python([], menu)
    assert expected.orders_count == 0 and expected.average_check == 0.0
    assert statistics_numpy_from_history([], menu) == expected
    assert statistics_threads([], menu, 2) == expected


# --- Every optimized version gives the same result -----------------------------------------------


@pytest.mark.parametrize("workers", [1, 2, 3])
@pytest.mark.parametrize(
    "implementation", [statistics_threads, statistics_processes, statistics_multiprocessing], ids=lambda f: f.__name__
)
def test_parallel_versions_equal_baseline(
    implementation: Callable[..., OrderStatistics], workers: int, history: list[HistoryItem], menu: dict[str, Dish]
) -> None:
    assert implementation(history, menu, workers) == statistics_python(history, menu)


def test_numpy_version_equals_baseline(history: list[HistoryItem], menu: dict[str, Dish]) -> None:
    arrays = to_arrays(history, menu)
    assert arrays.order_ids.dtype.name == "int32" and arrays.quantities.dtype.name == "uint8"
    assert len(arrays.order_ids) == len(history)
    assert statistics_numpy(arrays, menu) == statistics_python(history, menu)


@pytest.mark.parametrize("parts", [1, 2, 7, 50])
def test_split_keeps_orders_whole(parts: int, history: list[HistoryItem]) -> None:
    chunks = split_by_orders(history, parts)
    assert [item for chunk in chunks for item in chunk] == history
    assert len(chunks) <= parts
    last_numbers = [chunk[-1][0] for chunk in chunks[:-1]]
    first_numbers = [chunk[0][0] for chunk in chunks[1:]]
    assert all(last != first for last, first in zip(last_numbers, first_numbers))


# --- Files and threads ---------------------------------------------------------------------


def test_files_are_loaded_in_order_by_threads(
    tmp_path: Path, history: list[HistoryItem], menu: dict[str, Dish]
) -> None:
    paths = write_order_files(history, tmp_path, 4)
    assert [path.name for path in paths] == ["orders_01.csv", "orders_02.csv", "orders_03.csv", "orders_04.csv"]
    progress = LoadProgress()
    assert load_files_threads(paths, 3, progress) == history
    assert (progress.files, progress.items) == (4, len(history))
    assert load_files_sequential(paths) == history
    assert statistics_from_files(paths, menu) == statistics_python(history, menu)
    assert statistics_from_files_processes(paths, menu, 2) == statistics_python(history, menu)


def test_threads_wait_for_slow_storage_at_the_same_time(tmp_path: Path, history: list[HistoryItem]) -> None:
    paths = write_order_files(history, tmp_path, 8)
    start = time.perf_counter()
    load_files_threads(paths, 8, latency=0.1)
    assert time.perf_counter() - start < 0.4  # one after another it would take at least 0.8 s


def test_lock_prevents_race_condition() -> None:
    assert count_in_threads(ProcessedCounter(use_lock=True), threads=4, increments=500) == 2_000
    assert count_in_threads(ProcessedCounter(use_lock=False), threads=4, increments=500) < 2_000


# --- Caching -------------------------------------------------------------------------------


def test_cache_hit_and_invalidation_after_price_change(history: list[HistoryItem], menu: dict[str, Dish]) -> None:
    orders = OrderHistory(history, menu)
    first = orders.statistics()
    assert orders.statistics() is first
    assert cached_statistics.cache_info().hits == 1 and cached_statistics.cache_info().misses == 1
    borshch_portions = sum(quantity for _, name, quantity in history if name == "Борщ")
    orders.change_price("Борщ", 100.0)
    changed = orders.statistics()
    assert cached_statistics.cache_info().misses == 2
    assert changed.turnover == first.turnover + borshch_portions * 5.0
    assert changed == statistics_python(orders.items, orders.menu)


def test_cache_invalidation_after_new_order_item(menu: dict[str, Dish]) -> None:
    orders = OrderHistory(SMALL_HISTORY, menu)
    before = orders.statistics()
    orders.add_item(3, "Стейк", 2)
    after = orders.statistics()
    assert after.turnover == before.turnover + 560.0
    assert after.most_expensive_order == (3, 645.0)
    with pytest.raises(KeyError, match="Піца"):
        orders.add_item(3, "Піца")


# --- Measurement tools ---------------------------------------------------------------------


def test_benchmark_speedup_and_results_csv(tmp_path: Path) -> None:
    measurement = benchmark_repeated("sum", sum, range(1_000), repeats=5)
    assert len(measurement.times) == 5 and measurement.result == 499_500
    assert measurement.mean == pytest.approx(sum(measurement.times) / 5)
    assert calculate_speedup(1.0, 0.25) == 4.0
    assert timeit_best(lambda: sum(range(100)), number=100) > 0
    path = tmp_path / "results.csv"
    update_results_csv(path, "a", [result_row("a", 10, measurement, 1, measurement.mean)])
    update_results_csv(path, "b", [result_row("b", 10, measurement, 2, measurement.mean)])
    update_results_csv(path, "a", [result_row("a", 20, measurement, 1, measurement.mean)])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("experiment,dataset,method,workers,run1")
    assert [line.split(",")[:2] for line in lines[1:]] == [["b", "10"], ["a", "20"]]
    assert lines[1].endswith(",1.00")


def test_text_chart_scales_bars() -> None:
    lines = bar_chart({"Sequential": 0.4, "NumPy": 0.04}, "s", width=10)
    assert lines[0] == "Sequential │██████████ 0.4 s"
    assert lines[1] == "NumPy      │█ 0.04 s"


def test_profile_and_memory(menu: dict[str, Dish]) -> None:
    report = profile_call(statistics_python, SMALL_HISTORY, menu)
    assert "ncalls" in report and "order_totals_python" in report
    history, current_mb, peak_mb = peak_memory(generate_order_history, 2_000)
    assert len(history) > 2_000 and 0 < current_mb <= peak_mb
    allocations: list[Any] = top_allocations(generate_order_history, 2_000, limit=2)
    assert len(allocations) == 2 and "analytics.py" in allocations[0]


def test_optimization_demo(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from restaurant_orders import optimization_demo as demo

    monkeypatch.setattr(demo, "HISTORY_SIZE", 2_000)
    demo.main()
    output = capsys.readouterr().out
    assert "суми: №1 — 235.00 грн, №2 — 430.00 грн; середня вартість: 332.50 грн; найдорожче — №2" in output
    assert output.count("результат збігається: так") == 6
    assert "дані збігаються: так" in output
    assert "з Lock: 4000" in output


def test_profiling_report(capsys: pytest.CaptureFixture[str]) -> None:
    from restaurant_orders.profiling import run_profile

    run_profile(2_000)
    output = capsys.readouterr().out
    assert "Історія: 2000 замовлень" in output
    assert "cProfile ДО оптимізації: statistics_python" in output and "order_totals_python" in output
    assert "cProfile ПІСЛЯ оптимізації: statistics_numpy" in output
