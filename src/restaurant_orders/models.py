"""Data models used by the restaurant orders application."""

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Dish:
    """A dish that can be added to an order."""

    name: str
    category: str
    price: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Назва страви не може бути порожньою.")
        if not self.category.strip():
            raise ValueError("Категорія страви не може бути порожньою.")
        if self.price <= 0:
            raise ValueError("Ціна страви має бути більшою за нуль.")


@dataclass(slots=True)
class Order:
    """A restaurant order containing a numbered list of dishes."""

    number: int
    dishes: list[Dish] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.number <= 0:
            raise ValueError("Номер замовлення має бути додатним.")

    def add_dish(self, dish: Dish) -> None:
        """Add one dish to the order."""
        self.dishes.append(dish)
