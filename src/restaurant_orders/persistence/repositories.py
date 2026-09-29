"""Repositories: the only place that reads and writes rows of the database."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from restaurant_orders.persistence.models import Category, Dish, Order, OrderItem


class CategoryRepository:
    """Access to the categories table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_name(self, name: str) -> Category | None:
        return self.session.scalar(select(Category).where(Category.name == name))

    def list_with_counts(self) -> list[tuple[Category, int]]:
        """Categories with the number of dishes (LEFT JOIN + GROUP BY)."""
        statement = (
            select(Category, func.count(Dish.id))
            .outerjoin(Dish, Dish.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name)
        )
        return [(category, int(count)) for category, count in self.session.execute(statement)]

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

    SORTING = {
        "price_desc": (Dish.price.desc(), Dish.name),
        "price_asc": (Dish.price.asc(), Dish.name),
        "name": (Dish.name,),
    }

    def list(
        self, category: str | None = None, limit: int = 100, offset: int = 0, sort: str = "price_desc"
    ) -> list[Dish]:
        """Read: dishes of one category or all, sorted (price_desc, price_asc, name), page by page."""
        statement = select(Dish).join(Dish.category).order_by(*self.SORTING[sort])
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

    def history(self, limit: int | None = None, offset: int = 0) -> list[Order]:
        """Orders with their items, from the oldest to the newest (created_at, then number)."""
        statement = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.dish))
            .order_by(Order.created_at, Order.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count(self) -> int:
        """Number of orders."""
        return int(self.session.scalar(select(func.count()).select_from(Order)) or 0)

    def get_item(self, order_id: int, item_id: int) -> OrderItem | None:
        """Find an item that belongs to the order."""
        return self.session.scalar(select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id))

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
