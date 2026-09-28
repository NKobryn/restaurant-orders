"""Unit tests for iterators, generators and the streaming pipeline."""

import tempfile
import unittest
from collections import Counter
from itertools import islice
from pathlib import Path

from restaurant_orders.models import OrderItemRecord
from restaurant_orders.stream.analytics import batch_reports, collect_statistics, running_averages
from restaurant_orders.stream.export import export_order_totals
from restaurant_orders.stream.filters import filter_by_category, find_first, first_orders
from restaurant_orders.stream.iterators import OrderIdSequence, endless_order_ids
from restaurant_orders.stream.parsers import clean_lines, parse_rows
from restaurant_orders.stream.pipeline import (
    ALLOWED_CATEGORIES,
    batched,
    build_pipeline,
    read_records,
    sort_by_order,
    summarize_orders,
)
from restaurant_orders.stream.readers import read_lines, read_many
from restaurant_orders.stream.validation import validate_records

CSV_TEXT = """order_id,dish,category,price,quantity
1,Борщ,Перші страви,95.00,2
1,Стейк,Основні страви,280.00,1
2,Узвар,Напої,45.00,1
2,Суші,Японська кухня,210.00,1

3,Сирник,Десерти,85.00,0
3,Тірамісу,Десерти,110.00,2
"""


def record(order_id: int, dish: str, price: float, quantity: int = 1) -> OrderItemRecord:
    """Create a record of the «Основні страви» category for tests."""
    return OrderItemRecord(order_id, dish, "Основні страви", price, quantity)


class IteratorsTest(unittest.TestCase):
    """Tests for the custom iterator and the infinite generator."""

    def test_sequence_follows_iterator_protocol(self) -> None:
        sequence = OrderIdSequence(5, 2)
        self.assertIs(iter(sequence), sequence)
        self.assertEqual(next(sequence), 5)
        self.assertEqual(next(sequence), 6)
        with self.assertRaises(StopIteration):
            next(sequence)

    def test_exhausted_iterator_gives_nothing(self) -> None:
        sequence = OrderIdSequence(1, 3)
        self.assertEqual(list(sequence), [1, 2, 3])
        self.assertEqual(list(sequence), [])

    def test_endless_generator_is_limited_by_islice(self) -> None:
        self.assertEqual(list(islice(endless_order_ids(10), 3)), [10, 11, 12])


class ReadingAndValidationTest(unittest.TestCase):
    """Tests for the source, cleaning, parsing and validation stages."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "orders.csv"
        self.path.write_text(CSV_TEXT, encoding="utf-8")

    def tearDown(self) -> None:
        self.folder.cleanup()

    def test_read_lines_is_lazy_generator(self) -> None:
        lines = read_lines(self.path)
        self.assertEqual(next(lines).strip(), "order_id,dish,category,price,quantity")

    def test_clean_lines_skips_empty_comments_and_repeated_header(self) -> None:
        header = "order_id,dish,category,price,quantity"
        lines = [header + "\n", "# comment\n", "\n", "1,a\n", header + "\n"]
        self.assertEqual(list(clean_lines(lines)), [header, "1,a"])

    def test_parse_rows_uses_header_as_keys(self) -> None:
        rows = list(parse_rows(["order_id,dish,category,price,quantity", "1,Борщ,Перші страви,95,1"]))
        self.assertEqual(rows[0]["dish"], "Борщ")

    def test_validation_counts_invalid_rows(self) -> None:
        stats: Counter[str] = Counter()
        records = list(read_records([self.path], stats))
        self.assertEqual([item.dish for item in records], ["Борщ", "Стейк", "Узвар", "Тірамісу"])
        self.assertEqual(stats, Counter({"valid": 4, "invalid": 2}))

    def test_missing_field_is_invalid(self) -> None:
        stats: Counter[str] = Counter()
        rows = [{"order_id": "1", "dish": "Борщ", "category": "Перші страви", "price": "95", "quantity": None}]
        self.assertEqual(list(validate_records(rows, ALLOWED_CATEGORIES, stats)), [])
        self.assertEqual(stats["invalid"], 1)

    def test_read_many_chains_files(self) -> None:
        self.assertEqual(len(list(read_many([self.path, self.path]))), 2 * len(CSV_TEXT.splitlines()))

    def test_empty_file_gives_no_orders(self) -> None:
        self.path.write_text("", encoding="utf-8")
        self.assertEqual(list(build_pipeline([self.path], Counter())), [])


class PipelineTest(unittest.TestCase):
    """Tests for grouping, filtering, batching and aggregation."""

    def setUp(self) -> None:
        self.records = [record(2, "Стейк", 280.0), record(1, "Деруни", 110.0, 2), record(2, "Вареники", 120.0, 3)]

    def test_groupby_needs_sorted_records(self) -> None:
        unsorted_ids = [order.order_id for order in summarize_orders(self.records)]
        sorted_ids = [order.order_id for order in summarize_orders(sort_by_order(self.records))]
        self.assertEqual(unsorted_ids, [2, 1, 2])
        self.assertEqual(sorted_ids, [1, 2])

    def test_order_summary_has_total_and_most_expensive_position(self) -> None:
        orders = list(summarize_orders(sort_by_order(self.records)))
        self.assertEqual(orders[1].total, 640.0)
        self.assertEqual(orders[1].most_expensive.dish, "Стейк")

    def test_filter_by_category_is_lazy(self) -> None:
        desserts = filter_by_category(iter(self.records), {"Десерти"})
        self.assertEqual(list(desserts), [])
        self.assertEqual(len(list(filter_by_category(self.records, {"Основні страви"}))), 3)

    def test_batched_keeps_short_last_batch(self) -> None:
        self.assertEqual(list(batched(range(5), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(batched([], 3)), [])

    def test_first_orders_and_find_first_stop_early(self) -> None:
        orders = summarize_orders(sort_by_order(self.records))
        self.assertEqual([order.order_id for order in first_orders(orders, 1, lambda o: o.total > 100)], [1])
        endless = summarize_orders(record(number, "Стейк", 280.0) for number in endless_order_ids(1))
        found = find_first(endless, lambda order: order.order_id == 50)
        self.assertIsNotNone(found)

    def test_statistics_and_running_average(self) -> None:
        orders = list(summarize_orders(sort_by_order(self.records)))
        statistics = collect_statistics(orders)
        self.assertEqual(statistics.orders_count, 2)
        self.assertAlmostEqual(statistics.average_check, 430.0)
        self.assertEqual(list(running_averages([100.0, 300.0, 200.0])), [100.0, 200.0, 200.0])
        self.assertEqual(collect_statistics([]).average_check, 0.0)

    def test_batch_reports_sum_every_batch(self) -> None:
        orders = summarize_orders(sort_by_order(self.records))
        self.assertEqual(list(batch_reports(orders, 1)), [(1, 1, 220.0), (2, 1, 640.0)])

    def test_export_writes_one_row_per_order(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "totals.csv"
            written = export_order_totals(summarize_orders(sort_by_order(self.records)), path)
            self.assertEqual(written, 2)
            self.assertEqual(path.read_text(encoding="utf-8").splitlines()[1], "1,1,220.00")


if __name__ == "__main__":
    unittest.main()
