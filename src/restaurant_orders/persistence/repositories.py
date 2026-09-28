"""Repositories: the only place that reads and writes rows of the database."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from restaurant_orders.persistence.models import Category, Dish, Order, OrderItem


class CategoryRepository:
    """Access to the categories table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Category | None:
        return self.session.scalar(select(Category).where(Category.name == name))

    def get_or_create(self, name: str) -> Category:
        """Return the category with the name, creating it if needed."""
        category = self.get_by_name(name)
        if category is None:
            category = Category(name=name)
            self.session.add(category)
            self.session.flush()
        return category


class DishRepository:
    """CRUD of dishes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str, category: Category, price: float) -> Dish:
        """Create: insert a new dish."""
        dish = Dish(name=name, category=category, price=float(price))
        self.session.add(dish)
        self.session.flush()
        return dish

    def get(self, dish_id: int) -> Dish | None:
        """Read: find a dish by its id."""
        return self.session.get(Dish, dish_id)

    def get_by_name(self, name: str) -> Dish | None:
        return self.session.scalar(select(Dish).where(Dish.name == name))

    def list(self, category: str | None = None, limit: int = 100, offset: int = 0) -> list[Dish]:
        """Read: dishes sorted by price (most expensive first), optionally of one category, page by page."""
        statement = select(Dish).join(Dish.category).order_by(Dish.price.desc(), Dish.name)
        if category is not None:
            statement = statement.where(Category.name == category)
        return list(self.session.scalars(statement.limit(limit).offset(offset)))

    def update_price(self, dish_id: int, price: float) -> Dish | None:
        """Update: change the price of a dish."""
        dish = self.get(dish_id)
        if dish is not None:
            dish.price = float(price)
            self.session.flush()
        return dish

    def delete(self, dish_id: int) -> bool:
        """Delete: remove a dish; return False if there is no such dish."""
        dish = self.get(dish_id)
        if dish is None:
            return False
        self.session.delete(dish)
        self.session.flush()
        return True


class OrderRepository:
    """Orders and their items."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, order: Order) -> Order:
        self.session.add(order)
        self.session.flush()
        return order

    def get(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def history(self) -> list[Order]:
        """All orders with their items, from the first to the last."""
        statement = select(Order).options(selectinload(Order.items).selectinload(OrderItem.dish)).order_by(Order.id)
        return list(self.session.scalars(statement))

    def remove_item(self, order_id: int, dish_id: int) -> bool:
        """Delete one dish from an order; return False if it was not there."""
        item = self.session.scalar(
            select(OrderItem).where(OrderItem.order_id == order_id, OrderItem.dish_id == dish_id)
        )
        if item is None:
            return False
        item.order.items.remove(item)
        self.session.flush()
        return True

    def delete(self, order_id: int) -> bool:
        """Delete an order; its items are deleted by the cascade."""
        order = self.get(order_id)
        if order is None:
            return False
        self.session.delete(order)
        self.session.flush()
        return True
