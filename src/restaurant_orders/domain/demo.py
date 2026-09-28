"""Main entry point: demonstration of the typed object model (laboratory work 4)."""

from collections.abc import Callable

from restaurant_orders.domain.adapters import ConsoleKitchenNotifier, DemoPaymentGateway
from restaurant_orders.domain.dto import DishPayload, menu_from_payloads
from restaurant_orders.domain.exceptions import RestaurantError
from restaurant_orders.domain.models import Menu, Order
from restaurant_orders.domain.pricing import CategoryDiscount, NoDiscount
from restaurant_orders.domain.repositories import InMemoryRepository
from restaurant_orders.domain.services import RestaurantService
from restaurant_orders.domain.value_objects import Money

MENU_PAYLOADS: list[DishPayload] = [
    {"id": 1, "name": "Борщ", "category": "Перші страви", "price": 95.0, "currency": "UAH"},
    {"id": 2, "name": "Бульйон", "category": "Перші страви", "price": 70.0, "currency": "UAH"},
    {"id": 3, "name": "Вареники", "category": "Основні страви", "price": 120.0, "currency": "UAH"},
    {"id": 4, "name": "Деруни", "category": "Основні страви", "price": 110.0, "currency": "UAH"},
    {"id": 5, "name": "Стейк", "category": "Основні страви", "price": 280.0, "currency": "UAH"},
    {"id": 6, "name": "Тірамісу", "category": "Десерти", "price": 110.0, "currency": "UAH"},
    {"id": 7, "name": "Сирник", "category": "Десерти", "price": 85.0, "currency": "UAH"},
    {"id": 8, "name": "Узвар", "category": "Напої", "price": 45.0, "currency": "UAH"},
    {"id": 9, "name": "Капучино", "category": "Напої", "price": 75.0, "currency": "UAH"},
]


def show_money() -> None:
    """Demonstrate the immutable value object Money and its dunder methods."""
    print("\nVALUE OBJECT Money (frozen dataclass)")
    borscht, steak = Money(95.0), Money(280.0)
    print(f"{borscht} + {steak} = {borscht + steak}")
    print(f"{Money(45.0)} * 3 = {Money(45.0) * 3}")
    print(f"{borscht} < {steak}: {borscht < steak};  max: {max(borscht, steak)}")
    wrong_actions: list[Callable[[], object]] = [lambda: Money(-10.0), lambda: borscht + Money(5.0, "EUR")]
    for action in wrong_actions:
        try:
            action()
        except (ValueError, RestaurantError) as error:
            print(f"{type(error).__name__}: {error}")


def show_menu(menu: Menu) -> None:
    """Print the menu and demonstrate the custom collection."""
    print(f"\nМЕНЮ (страв: {len(menu)})")
    for dish in menu:
        print(f"{dish.id:>2}. {dish.name:10} {dish.category:15} {dish.price}")
    print(f"menu[5] -> {menu[5]};  5 in menu: {5 in menu};  42 in menu: {42 in menu}")
    print(f"Напої: {', '.join(dish.name for dish in menu.by_category('Напої'))}")


def print_order(service: RestaurantService, order: Order) -> None:
    """Print order items, totals and the most expensive dish."""
    print(f"\nЗамовлення №{order.id} [{order.status.value}], позицій: {len(order)}")
    for item in order:
        print(f"  {item.dish.name:10} × {item.quantity}  {item.total}")
    print(f"  Сума: {order.total};  до сплати: {service.order_total(order.id)}")
    print(f"  Найдорожча страва: {service.most_expensive_dish(order.id)}")


def main() -> None:
    """Run the demonstration scenario of the restaurant service."""
    print("СИСТЕМА ОБЛІКУ ЗАМОВЛЕНЬ РЕСТОРАНУ — ООП-модель (лабораторна робота №4, варіант №11)")
    show_money()
    menu = menu_from_payloads(MENU_PAYLOADS)
    show_menu(menu)

    orders = InMemoryRepository[Order]()
    gateway, notifier = DemoPaymentGateway(), ConsoleKitchenNotifier()
    service = RestaurantService(menu, orders, gateway, notifier, NoDiscount())
    print("\nСТВОРЕННЯ ЗАМОВЛЕНЬ І ДОДАВАННЯ СТРАВ")
    contents = [[(1, 2), (3, 1), (8, 2)], [(5, 1), (9, 2)], [(1, 1), (4, 1), (6, 1), (8, 3), (1, 1)]]
    for dishes in contents:
        order = service.create_order()
        for dish_id, quantity in dishes:
            service.add_dish(order.id, dish_id, quantity)
        print_order(service, order)
    print(f"\nСередня вартість замовлення: {service.average_order_value()}")

    print("\nОПЛАТА (PaymentGateway) І СПОВІЩЕННЯ КУХНІ (KitchenNotifier)")
    for order_id in (1, 2):
        service.checkout(order_id)
    empty_order = service.create_order()
    wrong_calls: list[Callable[[], object]] = [
        lambda: service.checkout(1),
        lambda: service.checkout(empty_order.id),
        lambda: service.add_dish(3, 42),
        lambda: service.order_total(99),
    ]
    for action in wrong_calls:
        try:
            action()
        except RestaurantError as error:
            print(f"{type(error).__name__}: {error}")
    print("Статуси: " + ", ".join(f"№{order.id} {order.status.value}" for order in orders.all()))

    print("\nСТРАТЕГІЯ ЦІНИ: «щаслива година» −20 % на напої (ті самі repository і gateway)")
    happy_hour = RestaurantService(menu, orders, gateway, notifier, CategoryDiscount("Напої", 20))
    print(f"Замовлення №3: NoDiscount {service.order_total(3)}, CategoryDiscount {happy_hour.order_total(3)}")
    happy_hour.checkout(3)


if __name__ == "__main__":
    main()
