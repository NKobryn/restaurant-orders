"""Business operations on top of the repositories: transactions and SQL aggregates."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from restaurant_orders.persistence.models import Category, Dish, Order, OrderItem
from restaurant_orders.persistence.repositories import DishRepository, OrderRepository


class OrderPlacementError(Exception):
    """The order cannot be saved; nothing was written to the database."""


@dataclass(frozen=True, slots=True)
class CategoryStatistics:
    """How many portions of a category were ordered and for how much."""

    category: str
    portions: int
    revenue: float


class OrderService:
    """Orders stored in the database."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.dishes = DishRepository(session)
        self.orders = OrderRepository(session)

    def place_order(self, order_id: int, items: list[tuple[str, int]]) -> Order:
        """One transaction: save the order and all its items, or roll everything back."""
        try:
            if not items:
                raise OrderPlacementError(f"Замовлення №{order_id} порожнє.")
            order = Order(id=order_id)
            for name, quantity in items:
                dish = self.dishes.get_by_name(name)
                if dish is None:
                    raise OrderPlacementError(f"Страви «{name}» немає в меню.")
                order.items.append(OrderItem(dish=dish, quantity=quantity, unit_price=dish.price))
            self.orders.add(order)
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise OrderPlacementError(f"Замовлення №{order_id} порушує обмеження бази даних.") from error
        except OrderPlacementError:
            self.session.rollback()
            raise
        return order

    def add_dish(self, order_id: int, name: str, quantity: int = 1) -> OrderItem:
        """Add one more dish to an existing order and commit."""
        order = self.orders.get(order_id)
        dish = self.dishes.get_by_name(name)
        if order is None or dish is None:
            raise OrderPlacementError(f"Немає замовлення №{order_id} або страви «{name}».")
        item = OrderItem(dish=dish, quantity=quantity, unit_price=dish.price)
        order.items.append(item)
        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise OrderPlacementError(f"Страву «{name}» не можна додати до замовлення №{order_id}.") from error
        return item

    def remove_dish(self, order_id: int, name: str) -> bool:
        """Delete a dish from an order and commit."""
        dish = self.dishes.get_by_name(name)
        removed = dish is not None and self.orders.remove_item(order_id, dish.id)
        self.session.commit()
        return removed

    def order_total(self, order_id: int) -> float:
        """SUM(quantity * unit_price) of one order."""
        statement = select(func.sum(OrderItem.quantity * OrderItem.unit_price)).where(OrderItem.order_id == order_id)
        return round(float(self.session.scalar(statement) or 0), 2)

    def most_expensive_item(self, order_id: int) -> OrderItem | None:
        """Order item with the highest unit price (the earlier item wins a tie)."""
        statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .order_by(OrderItem.unit_price.desc(), OrderItem.id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def average_order_value(self) -> float:
        """AVG of the order totals (GROUP BY order_id in a subquery)."""
        totals = (
            select(func.sum(OrderItem.quantity * OrderItem.unit_price).label("total"))
            .group_by(OrderItem.order_id)
            .subquery()
        )
        return round(float(self.session.scalar(select(func.avg(totals.c.total))) or 0), 2)

    def category_statistics(self) -> list[CategoryStatistics]:
        """Portions and revenue by category: JOIN + GROUP BY + SUM."""
        revenue = func.sum(OrderItem.quantity * OrderItem.unit_price)
        statement = (
            select(Category.name, func.sum(OrderItem.quantity), revenue)
            .join(Dish, Dish.id == OrderItem.dish_id)
            .join(Category, Category.id == Dish.category_id)
            .group_by(Category.name)
            .order_by(revenue.desc())
        )
        return [CategoryStatistics(name, int(portions), round(float(total), 2))
                for name, portions, total in self.session.execute(statement)]
