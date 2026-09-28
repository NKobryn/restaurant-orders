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


@dataclass(slots=True, frozen=True)
class OrderItemRecord:
    """One order position with quantity, read from a stream of records."""

    order_id: int
    dish: str
    category: str
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if self.order_id <= 0:
            raise ValueError("Номер замовлення має бути додатним.")
        if not self.dish:
            raise ValueError("Назва страви не може бути порожньою.")
        if self.price <= 0:
            raise ValueError("Ціна має бути більшою за нуль.")
        if self.quantity <= 0:
            raise ValueError("Кількість має бути більшою за нуль.")

    @property
    def line_total(self) -> float:
        """Return the price of the position for the whole quantity."""
        return self.price * self.quantity


@dataclass(slots=True, frozen=True)
class OrderSummary:
    """Result of processing all positions of one order."""

    order_id: int
    items_count: int
    total: float
    most_expensive: OrderItemRecord
