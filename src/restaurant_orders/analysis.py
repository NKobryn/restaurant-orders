"""Entry point of laboratory work 2: analysis of restaurant orders."""

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
from restaurant_orders.data import MENU, create_demo_orders
from restaurant_orders.decorators import OPERATION_HISTORY
from restaurant_orders.models import Order
from restaurant_orders.processors import (
    OrderLine,
    count_dishes,
    create_order_index,
    filter_items,
    get_unique_categories,
    get_unique_dishes,
    group_lines_by_order,
    to_order_lines,
)


def print_lines(title: str, lines: list[OrderLine]) -> None:
    """Print order positions as a table."""
    print(f"\n{title}")
    print("-" * 56)
    for number, dish, category, price in lines:
        print(f"№{number:<5} {dish:12} {category:16} {price:8.2f} грн")


def print_groups(groups: dict[int, list[OrderLine]], totals: dict[int, float]) -> None:
    """Print dishes of every order and the order total."""
    print("\nГРУПУВАННЯ ПОЗИЦІЙ ЗА ЗАМОВЛЕННЯМИ")
    for number, lines in groups.items():
        dishes = ", ".join(line[1] for line in lines)
        print(f"№{number}: {dishes} — разом {totals[number]:.2f} грн")


def print_unique_values(lines: list[OrderLine]) -> None:
    """Print unique dishes, categories and menu dishes nobody ordered."""
    ordered_dishes = get_unique_dishes(lines)
    menu_dishes = {dish.name for dish in MENU}
    print("\nУНІКАЛЬНІ ЗНАЧЕННЯ")
    print(f"Страви ({len(ordered_dishes)}): {', '.join(sorted(ordered_dishes))}")
    categories = get_unique_categories(lines)
    print(f"Категорії ({len(categories)}): {', '.join(sorted(categories))}")
    print(f"Страви меню без замовлень: {', '.join(sorted(menu_dishes - ordered_dishes))}")


def print_statistics(lines: list[OrderLine], totals: dict[int, float]) -> None:
    """Print Counter of dishes and the main statistics of orders."""
    dish_counter = count_dishes(lines)
    print("\nКІЛЬКІСТЬ ЗАМОВЛЕНЬ КОЖНОЇ СТРАВИ (Counter)")
    for dish, count in dish_counter.most_common():
        print(f"{dish:12} {count}")
    popular = find_most_popular_dish(dish_counter)
    if popular is not None:
        print(f"\nНайпопулярніша страва: {popular[0]} ({popular[1]} рази)")
    expensive = find_most_expensive_line(lines)
    if expensive is not None:
        print(f"Найдорожча позиція: {expensive[1]}, {expensive[3]:.2f} грн (замовлення №{expensive[0]})")
    print(f"Середня вартість замовлення: {calculate_average_check(totals):.2f} грн")


def print_ranking(totals: dict[int, float]) -> None:
    """Print orders sorted by total from the highest to the lowest."""
    print("\nРЕЙТИНГ ЗАМОВЛЕНЬ ЗА СУМОЮ")
    for place, (number, total) in enumerate(rank_orders_by_total(totals), start=1):
        print(f"{place}. №{number}: {total:.2f} грн")


def print_search(orders_index: dict[int, Order], numbers: tuple[int, ...]) -> None:
    """Search orders by number using the dictionary index."""
    print("\nПОШУК ЗАМОВЛЕННЯ ЗА НОМЕРОМ (dict-index)")
    for number in numbers:
        order = orders_index.get(number)
        if order is None:
            print(f"№{number}: не знайдено")
        else:
            names = ", ".join(dish.name for dish in order.dishes)
            print(f"№{number}: {names} (страв: {len(order.dishes)})")


def main() -> None:
    """Run all steps of the orders analysis for the demo data."""
    orders = create_demo_orders()
    lines = to_order_lines(orders)
    groups = group_lines_by_order(lines)
    totals = calculate_order_totals(groups)

    print("АНАЛІЗ ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №2, варіант №11)")
    print_lines("УСІ ПОЗИЦІЇ ЗАМОВЛЕНЬ", lines)
    print_groups(groups, totals)
    print_unique_values(lines)
    print_statistics(lines, totals)
    print_ranking(totals)
    print_search(create_order_index(orders), (103, 999))

    print_lines("ПОЗИЦІЇ ВІД 110 ГРН (closure)", filter_items(lines, create_price_filter(110.0)))
    drinks = filter_items(lines, lambda line: line[2] == "Напої")
    print_lines("НАПОЇ (lambda)", drinks)

    drink_prices = [line[3] for line in drinks]
    print(f"\nСередня ціна напою (*args): {calculate_average(*drink_prices):.2f} грн")
    summary = create_summary(orders=len(orders), positions=len(lines), revenue=sum(totals.values()))
    print(f"Підсумок (**kwargs): {summary}")

    print("\nОСТАННІ ОПЕРАЦІЇ (deque, maxlen=5)")
    for operation in OPERATION_HISTORY:
        print(f"- {operation}")


if __name__ == "__main__":
    main()
