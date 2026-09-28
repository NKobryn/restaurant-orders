"""Unit tests for collection processors, analytics and decorators."""

import unittest
from collections import Counter

from restaurant_orders.analytics import (
    calculate_average,
    calculate_average_check,
    calculate_order_totals,
    create_price_filter,
    create_summary,
    find_most_expensive_line,
    find_most_popular_dish,
    rank_orders_by_total,
)
from restaurant_orders.data import create_demo_orders
from restaurant_orders.decorators import OPERATION_HISTORY, measure_time, track_operation
from restaurant_orders.models import Dish, Order
from restaurant_orders.processors import (
    count_dishes,
    create_order_index,
    filter_items,
    get_unique_categories,
    get_unique_dishes,
    group_lines_by_order,
    to_order_lines,
)


class ProcessorsTest(unittest.TestCase):
    """Tests for turning orders into collections."""

    def setUp(self) -> None:
        soup = Dish("Суп", "Перші страви", 80.0)
        tea = Dish("Чай", "Напої", 40.0)
        self.orders = [Order(1, [soup, tea]), Order(2, [soup])]
        self.lines = to_order_lines(self.orders)

    def test_creates_one_line_per_dish(self) -> None:
        self.assertEqual(self.lines[0], (1, "Суп", "Перші страви", 80.0))
        self.assertEqual(len(self.lines), 3)

    def test_returns_unique_dishes_and_categories(self) -> None:
        self.assertEqual(get_unique_dishes(self.lines), {"Суп", "Чай"})
        self.assertEqual(get_unique_categories(self.lines), {"Перші страви", "Напої"})

    def test_groups_lines_by_order(self) -> None:
        groups = group_lines_by_order(self.lines)
        self.assertEqual(list(groups), [1, 2])
        self.assertEqual(len(groups[1]), 2)

    def test_counts_dishes(self) -> None:
        self.assertEqual(count_dishes(self.lines), Counter({"Суп": 2, "Чай": 1}))

    def test_index_finds_order_by_number(self) -> None:
        index = create_order_index(self.orders)
        self.assertIs(index[2], self.orders[1])
        self.assertIsNone(index.get(99))

    def test_filter_items_uses_predicate(self) -> None:
        drinks = filter_items(self.lines, lambda line: line[2] == "Напої")
        self.assertEqual([line[1] for line in drinks], ["Чай"])

    def test_empty_orders_give_empty_collections(self) -> None:
        self.assertEqual(to_order_lines([]), [])
        self.assertEqual(group_lines_by_order([]), {})
        self.assertEqual(get_unique_dishes([]), set())


class AnalyticsTest(unittest.TestCase):
    """Tests for statistics of the demo orders."""

    def setUp(self) -> None:
        self.lines = to_order_lines(create_demo_orders())
        self.totals = calculate_order_totals(group_lines_by_order(self.lines))

    def test_calculates_order_totals(self) -> None:
        self.assertEqual(self.totals[101], 260.0)
        self.assertEqual(self.totals[105], 420.0)

    def test_calculates_average_check(self) -> None:
        self.assertAlmostEqual(calculate_average_check(self.totals), 1930.0 / 6)

    def test_finds_most_expensive_line(self) -> None:
        self.assertEqual(find_most_expensive_line(self.lines), (102, "Стейк", "Основні страви", 280.0))

    def test_finds_most_popular_dish(self) -> None:
        self.assertEqual(find_most_popular_dish(count_dishes(self.lines)), ("Борщ", 4))

    def test_ranks_orders_from_highest_total(self) -> None:
        ranking = rank_orders_by_total(self.totals)
        self.assertEqual(ranking[0], (105, 420.0))
        self.assertEqual(ranking[-1], (106, 160.0))

    def test_empty_data_do_not_raise(self) -> None:
        self.assertEqual(calculate_average(), 0.0)
        self.assertEqual(calculate_average_check({}), 0.0)
        self.assertIsNone(find_most_expensive_line([]))
        self.assertIsNone(find_most_popular_dish(Counter()))

    def test_average_accepts_any_number_of_values(self) -> None:
        self.assertEqual(calculate_average(10, 20, 30), 20.0)

    def test_price_filter_remembers_minimum(self) -> None:
        is_expensive = create_price_filter(110.0)
        self.assertTrue(is_expensive((1, "Деруни", "Основні страви", 110.0)))
        self.assertFalse(is_expensive((1, "Узвар", "Напої", 45.0)))

    def test_summary_collects_keyword_arguments(self) -> None:
        self.assertEqual(create_summary(orders=6, revenue=1930.0), {"orders": 6, "revenue": 1930.0})


class DecoratorsTest(unittest.TestCase):
    """Tests for the decorators behaviour."""

    def test_track_operation_saves_last_five_labels(self) -> None:
        @track_operation("тест")
        def action() -> int:
            return 5

        for _ in range(7):
            self.assertEqual(action(), 5)
        self.assertEqual(list(OPERATION_HISTORY), ["тест"] * 5)

    def test_decorators_keep_function_name(self) -> None:
        self.assertEqual(calculate_order_totals.__name__, "calculate_order_totals")
        self.assertEqual(measure_time(calculate_average).__name__, "calculate_average")


if __name__ == "__main__":
    unittest.main()
