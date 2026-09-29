"""Benchmark of search in list, dict and set for laboratory work 2."""

import platform
import random
from collections.abc import Callable
from time import perf_counter
from typing import Any

from restaurant_orders.data import MENU
from restaurant_orders.decorators import measure_time
from restaurant_orders.models import Order
from restaurant_orders.processors import create_order_index
from restaurant_orders.services import find_order

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)
SEARCHES = 1_000
REPEATS = 3
SEED = 11


@measure_time
def generate_orders(count: int, rng: random.Random) -> list[Order]:
    """Generate orders numbered 1..count with one to four random dishes."""
    return [Order(number, rng.sample(MENU, rng.randint(1, 4))) for number in range(1, count + 1)]


def measure_ms(action: Callable[[int], Any], numbers: list[int]) -> float:
    """Return the best time in milliseconds of calling action for all numbers."""
    best = float("inf")
    for _ in range(REPEATS):
        start = perf_counter()
        for number in numbers:
            action(number)
        best = min(best, perf_counter() - start)
    return best * 1000


def benchmark_size(size: int, rng: random.Random) -> tuple[float, ...]:
    """Measure all search variants for one data size."""
    orders = generate_orders(size, rng)
    numbers = [rng.randint(1, size) for _ in range(SEARCHES)]

    start = perf_counter()
    index = create_order_index(orders)
    index_ms = (perf_counter() - start) * 1000
    if any(find_order(orders, number) is not index.get(number) for number in numbers[:100]):
        raise RuntimeError("list і dict повернули різні замовлення")

    order_numbers = [order.number for order in orders]
    number_set = set(order_numbers)
    return (
        measure_ms(lambda number: find_order(orders, number), numbers),
        measure_ms(lambda number: index.get(number), numbers),
        index_ms,
        measure_ms(lambda number: number in order_numbers, numbers),
        measure_ms(lambda number: number in number_set, numbers),
    )


def main() -> None:
    """Run the benchmark for all sizes and print the results table."""
    rng = random.Random(SEED)
    print("BENCHMARK: ПОШУК ЗАМОВЛЕННЯ ЗА НОМЕРОМ")
    print(f"Python {platform.python_version()}, {platform.system()} {platform.machine()}")
    print(f"Пошуків на розмір: {SEARCHES}, повторів: {REPEATS} (береться найкращий), seed = {SEED}\n")
    results = {size: benchmark_size(size, rng) for size in SIZES}

    print("\nЧас на 1000 пошуків, мс")
    print(
        f"{'Записів':>8} | {'list пошук':>10} | {'dict get':>9} | {'list/dict':>9} | "
        f"{'побудова dict':>13} | {'in list':>8} | {'in set':>7}"
    )
    print("-" * 84)
    for size, (list_ms, dict_ms, index_ms, in_list_ms, in_set_ms) in results.items():
        print(
            f"{size:>8} | {list_ms:>10.3f} | {dict_ms:>9.3f} | {list_ms / dict_ms:>8.0f}x | "
            f"{index_ms:>13.3f} | {in_list_ms:>8.3f} | {in_set_ms:>7.3f}"
        )


if __name__ == "__main__":
    main()
