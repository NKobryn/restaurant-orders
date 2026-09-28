"""External data (TypedDict) and its conversion into domain objects."""

from collections.abc import Iterable
from typing import TypedDict

from restaurant_orders.domain.models import Dish, Menu
from restaurant_orders.domain.value_objects import Money


class DishPayload(TypedDict):
    """Dish as it comes from outside: a JSON-like dictionary."""

    id: int
    name: str
    category: str
    price: float
    currency: str


def dish_from_payload(data: DishPayload) -> Dish:
    """Convert an external dictionary into a Dish entity."""
    return Dish(
        id=data["id"],
        name=data["name"],
        category=data["category"],
        _price=Money(data["price"], data["currency"]),
    )


def menu_from_payloads(payloads: Iterable[DishPayload]) -> Menu:
    """Build a menu from external dictionaries."""
    return Menu(dish_from_payload(payload) for payload in payloads)
