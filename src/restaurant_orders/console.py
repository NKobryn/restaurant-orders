"""Console application of laboratory work 1 (demo and interactive menu)."""

import sys

from restaurant_orders.models import Dish, Order
from restaurant_orders.services import (
    OrderNotFoundError,
    add_dish_to_order,
    calculate_average_order_value,
    calculate_order_total,
    create_order,
    find_most_expensive_dish,
    sort_orders_by_total,
)


def create_demo_orders() -> list[Order]:
    """Create several orders to demonstrate the application's features."""
    orders: list[Order] = []
    create_order(orders, 101)
    add_dish_to_order(orders, 101, Dish("Борщ", "Перші страви", 95.0))
    add_dish_to_order(orders, 101, Dish("Вареники", "Основні страви", 120.0))
    create_order(orders, 102)
    add_dish_to_order(orders, 102, Dish("Стейк", "Основні страви", 280.0))
    add_dish_to_order(orders, 102, Dish("Лимонад", "Напої", 65.0))
    create_order(orders, 103)
    add_dish_to_order(orders, 103, Dish("Тірамісу", "Десерти", 110.0))
    add_dish_to_order(orders, 103, Dish("Капучино", "Напої", 75.0))
    return orders


def print_order(order: Order) -> None:
    """Print one order and its dishes in a readable form."""
    print(f"\nЗамовлення №{order.number}")
    if not order.dishes:
        print("  Страв ще не додано.")
    for dish in order.dishes:
        print(f"  {dish.name:15} | {dish.category:18} | {dish.price:7.2f} грн")
    print(f"  Разом: {calculate_order_total(order):.2f} грн")


def print_statistics(orders: list[Order]) -> None:
    """Print required statistics for all supplied orders."""
    print("\nСТАТИСТИКА ЗАМОВЛЕНЬ")
    print(f"Кількість замовлень: {len(orders)}")
    print(f"Середня вартість: {calculate_average_order_value(orders):.2f} грн")
    for order in orders:
        most_expensive = find_most_expensive_dish(order)
        if most_expensive is not None:
            print(
                f"Найдорожча позиція в №{order.number}: "
                f"{most_expensive.name} ({most_expensive.price:.2f} грн)"
            )


def read_positive_int(prompt: str) -> int:
    """Read a positive integer from keyboard with validation."""
    while True:
        try:
            value = int(input(prompt))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Введіть ціле додатне число.")


def read_positive_float(prompt: str) -> float:
    """Read a positive price from keyboard with validation."""
    while True:
        try:
            value = float(input(prompt).replace(",", "."))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            print("Введіть додатне число.")


def run_menu(orders: list[Order]) -> None:
    """Run an interactive menu for entering and processing orders."""
    while True:
        print("\n1 — показати замовлення; 2 — створити; 3 — додати страву")
        print("4 — статистика; 5 — сортувати за сумою; 0 — вихід")
        command = input("Оберіть команду: ").strip()
        if command == "1":
            for order in orders:
                print_order(order)
        elif command == "2":
            try:
                create_order(orders, read_positive_int("Номер замовлення: "))
                print("Замовлення створено.")
            except ValueError as error:
                print(error)
        elif command == "3":
            number = read_positive_int("Номер замовлення: ")
            name = input("Назва страви: ").strip()
            category = input("Категорія: ").strip()
            price = read_positive_float("Ціна: ")
            try:
                add_dish_to_order(orders, number, Dish(name, category, price))
                print("Страву додано.")
            except (ValueError, OrderNotFoundError) as error:
                print(error)
        elif command == "4":
            print_statistics(orders)
        elif command == "5":
            for order in sort_orders_by_total(orders):
                print_order(order)
        elif command == "0":
            print("До побачення!")
            return
        else:
            print("Невідома команда. Спробуйте ще раз.")


def main() -> None:
    """Run demonstration mode or menu mode selected by --interactive."""
    orders = create_demo_orders()
    print("СИСТЕМА ОБЛІКУ ЗАМОВЛЕНЬ РЕСТОРАНУ")
    for order in orders:
        print_order(order)
    print_statistics(orders)
    print("\nРЕЙТИНГ ЗАМОВЛЕНЬ ЗА СУМОЮ")
    for order in sort_orders_by_total(orders):
        print(f"№{order.number}: {calculate_order_total(order):.2f} грн")
    if "--interactive" in sys.argv:
        run_menu(orders)
    else:
        print("\nДля введення даних з клавіатури: python -m restaurant_orders.console --interactive")


if __name__ == "__main__":
    main()
