"""Entry point of laboratory work 3: streaming processing of restaurant orders."""

from collections import Counter
from itertools import islice
from pathlib import Path

from restaurant_orders.models import OrderSummary
from restaurant_orders.stream.analytics import (
    OrdersStatistics,
    batch_reports,
    collect_statistics,
    running_averages,
)
from restaurant_orders.stream.dataset import GENERATED_DIR, ensure_dataset
from restaurant_orders.stream.export import export_order_totals
from restaurant_orders.stream.filters import filter_by_category, first_orders
from restaurant_orders.stream.iterators import OrderIdSequence, endless_order_ids
from restaurant_orders.stream.pipeline import (
    build_pipeline,
    read_records,
    sort_by_order,
    summarize_orders,
)

SAMPLE_FILE = Path("data") / "orders_sample.csv"
LARGE_RECORDS = 100_000


def show_iterator_protocol() -> None:
    """Demonstrate iter(), next(), StopIteration and an infinite generator."""
    print("\n1. ПРОТОКОЛ ІТЕРАТОРА")
    sequence = OrderIdSequence(101, 3)
    print(f"iter(sequence) is sequence: {iter(sequence) is sequence}")
    for _ in range(4):
        try:
            print(f"next(sequence) -> {next(sequence)}")
        except StopIteration:
            print("next(sequence) -> StopIteration")
    print(f"Повторний прохід вичерпаного iterator: {list(sequence)}")
    print(f"Нескінченний generator + islice: {list(islice(endless_order_ids(1), 5))}")


def print_orders(orders: list[OrderSummary]) -> None:
    """Print order summaries as a table."""
    for order in orders:
        best = order.most_expensive
        print(
            f"№{order.order_id}: позицій {order.items_count}, сума {order.total:8.2f} грн, "
            f"найдорожча — {best.dish} ({best.price:.2f} грн)"
        )


def print_statistics(statistics: OrdersStatistics) -> None:
    """Print totals of a stream of orders."""
    print(
        f"Замовлень: {statistics.orders_count}, виручка: {statistics.revenue:.2f} грн, "
        f"середній чек: {statistics.average_check:.2f} грн"
    )
    best = statistics.most_expensive
    if best is not None:
        print(f"Найдорожча позиція: {best.dish}, {best.price:.2f} грн (замовлення №{best.order_id})")


def show_sample_file() -> None:
    """Process the small unsorted file with invalid rows."""
    print(f"\n2. МАЛИЙ ФАЙЛ {SAMPLE_FILE} (незасортований, з помилками)")
    stats: Counter[str] = Counter()
    records = sort_by_order(read_records([SAMPLE_FILE], stats))
    print(f"Коректних позицій: {stats['valid']}, некоректних: {stats['invalid']}")

    unsorted = summarize_orders(read_records([SAMPLE_FILE], Counter()))
    print(f"groupby без сортування: {[order.order_id for order in unsorted]}")
    orders = list(summarize_orders(records))
    print(f"groupby після сортування: {[order.order_id for order in orders]}")
    print_orders(orders)
    print_statistics(collect_statistics(orders))
    desserts = filter_by_category(records, {"Десерти"})
    print(f"Позиції категорії «Десерти» (lazy filter): {[record.dish for record in desserts]}")

    two_files = read_records([SAMPLE_FILE, SAMPLE_FILE], Counter())
    print(f"Два файли через chain: {sum(1 for _ in two_files)} коректних позицій")


def show_large_file() -> None:
    """Run the lazy pipeline over the large generated file."""
    path = ensure_dataset(LARGE_RECORDS)
    print(f"\n3. ВЕЛИКИЙ ФАЙЛ {path} ({LARGE_RECORDS} записів)")
    stats: Counter[str] = Counter()
    print_statistics(collect_statistics(build_pipeline([path], stats)))
    print(f"Коректних позицій: {stats['valid']}, некоректних: {stats['invalid']}")

    print("\nСередній чек у потоці (accumulate) після N замовлень:")
    checkpoints = {1, 10, 100, 1_000, 10_000}
    totals = (order.total for order in build_pipeline([path], Counter()))
    for number, average in enumerate(running_averages(totals), start=1):
        if number in checkpoints:
            print(f"  N = {number:>6}: {average:8.2f} грн")

    print("\nПерші 5 замовлень із сумою понад 1500 грн (islice):")
    print_orders(first_orders(build_pipeline([path], Counter()), 5, lambda order: order.total > 1500))

    desserts = filter_by_category(read_records([path], Counter()), {"Десерти"})
    first_desserts = [f"№{record.order_id} {record.dish}" for record in islice(desserts, 3)]
    print(f"\nПерші 3 позиції «Десерти»: {', '.join(first_desserts)}")

    print("\nПакетна обробка (по 10 000 замовлень):")
    for number, size, revenue in batch_reports(build_pipeline([path], Counter()), 10_000):
        print(f"  пачка {number}: замовлень {size:>5}, виручка {revenue:12.2f} грн")

    export_path = GENERATED_DIR / f"order_totals_{LARGE_RECORDS}.csv"
    written = export_order_totals(build_pipeline([path], Counter()), export_path)
    print(f"\nПотоковий експорт: {written} рядків у {export_path}")


def main() -> None:
    """Run all demonstrations of the streaming pipeline."""
    print("ПОТОКОВА ОБРОБКА ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №3, варіант №11)")
    show_iterator_protocol()
    show_sample_file()
    show_large_file()


if __name__ == "__main__":
    main()
