"""Demonstration data for the restaurant orders analysis."""

from restaurant_orders.models import Dish, Order
from restaurant_orders.services import add_dish_to_order, create_order

MENU: tuple[Dish, ...] = (
    Dish("Борщ", "Перші страви", 95.0),
    Dish("Бульйон", "Перші страви", 70.0),
    Dish("Вареники", "Основні страви", 120.0),
    Dish("Деруни", "Основні страви", 110.0),
    Dish("Стейк", "Основні страви", 280.0),
    Dish("Тірамісу", "Десерти", 110.0),
    Dish("Сирник", "Десерти", 85.0),
    Dish("Узвар", "Напої", 45.0),
    Dish("Капучино", "Напої", 75.0),
)

ORDER_CONTENTS: dict[int, list[str]] = {
    101: ["Борщ", "Вареники", "Узвар"],
    102: ["Стейк", "Капучино"],
    103: ["Борщ", "Деруни", "Сирник", "Узвар"],
    104: ["Борщ", "Вареники", "Тірамісу", "Капучино"],
    105: ["Борщ", "Стейк", "Узвар"],
    106: ["Сирник", "Капучино"],
}


def create_demo_orders() -> list[Order]:
    """Create demo orders from the menu and the order contents."""
    menu_by_name = {dish.name: dish for dish in MENU}
    orders: list[Order] = []
    for number, dish_names in ORDER_CONTENTS.items():
        create_order(orders, number)
        for name in dish_names:
            add_dish_to_order(orders, number, menu_by_name[name])
    return orders
