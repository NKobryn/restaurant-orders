"""Entities of the restaurant domain: dishes, menu, orders and their items."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from enum import Enum

from restaurant_orders.domain.exceptions import DishNotFoundError, OrderStateError
from restaurant_orders.domain.value_objects import Money


class OrderStatus(str, Enum):
    """Possible states of an order."""

    NEW = "new"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass
class Dish:
    """A dish of the menu; the price is changed only through change_price()."""

    id: int
    name: str
    category: str
    _price: Money

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("Ідентифікатор страви має бути додатним.")
        if not self.name.strip():
            raise ValueError("Назва страви не може бути порожньою.")

    @property
    def price(self) -> Money:
        """Return the current price of the dish."""
        return self._price

    def change_price(self, new_price: Money) -> None:
        """Set a new price in the same currency."""
        if new_price.currency != self._price.currency:
            raise ValueError("Нова ціна має бути в тій самій валюті.")
        self._price = new_price

    def __str__(self) -> str:
        return f"{self.name} ({self.price})"


@dataclass(slots=True)
class OrderItem:
    """A dish in an order together with its quantity."""

    dish: Dish
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль.")

    @property
    def total(self) -> Money:
        """Return the price of the dish multiplied by the quantity."""
        return self.dish.price * self.quantity


@dataclass
class Order:
    """An order that consists of order items (composition)."""

    id: int
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.NEW

    def add_dish(self, dish: Dish, quantity: int = 1) -> None:
        """Add a dish; the quantity grows if the dish is already in the order."""
        if self.status is not OrderStatus.NEW:
            raise OrderStateError(f"Замовлення №{self.id} вже не можна змінювати.")
        for item in self.items:
            if item.dish.id == dish.id:
                item.quantity += quantity
                return
        self.items.append(OrderItem(dish, quantity))

    @property
    def total(self) -> Money:
        """Return the sum of all order items."""
        return sum((item.total for item in self.items), Money(0))

    def most_expensive_dish(self) -> Dish | None:
        """Return the dish with the highest price, if the order is not empty."""
        return max((item.dish for item in self.items), key=lambda dish: dish.price, default=None)

    def mark_paid(self) -> None:
        """Change the status of a new order to paid."""
        if self.status is not OrderStatus.NEW:
            raise OrderStateError(f"Замовлення №{self.id} не можна оплатити: {self.status.value}.")
        self.status = OrderStatus.PAID

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[OrderItem]:
        return iter(self.items)

    def __contains__(self, dish_id: object) -> bool:
        return any(item.dish.id == dish_id for item in self.items)


class Menu:
    """Collection of dishes with access by dish id."""

    def __init__(self, dishes: Iterable[Dish] = ()) -> None:
        self._dishes: dict[int, Dish] = {}
        for dish in dishes:
            self.add(dish)

    def add(self, dish: Dish) -> None:
        """Add a dish with a new id to the menu."""
        if dish.id in self._dishes:
            raise ValueError(f"Страва з id {dish.id} вже є в меню.")
        self._dishes[dish.id] = dish

    def by_category(self, category: str) -> list[Dish]:
        """Return dishes of one category."""
        return [dish for dish in self._dishes.values() if dish.category == category]

    def __getitem__(self, dish_id: int) -> Dish:
        try:
            return self._dishes[dish_id]
        except KeyError as error:
            raise DishNotFoundError(f"У меню немає страви з id {dish_id}.") from error

    def __iter__(self) -> Iterator[Dish]:
        return iter(self._dishes.values())

    def __len__(self) -> int:
        return len(self._dishes)

    def __contains__(self, dish_id: object) -> bool:
        return dish_id in self._dishes
