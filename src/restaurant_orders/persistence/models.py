"""ORM models of the tables categories, dishes, orders and order_items."""

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant_orders.persistence.database import Base

Price = Numeric(10, 2, asdecimal=False)


class Category(Base):
    """Category of dishes, for example «Напої»."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")


class Dish(Base):
    """Dish of the menu."""

    __tablename__ = "dishes"
    __table_args__ = (CheckConstraint("price > 0", name="price_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    price: Mapped[float] = mapped_column(Price)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))

    category: Mapped[Category] = relationship(back_populates="dishes")


class Order(Base):
    """Order of a guest; its number is the primary key."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )

    @property
    def total(self) -> float:
        """Return the sum of all order items."""
        return round(sum(item.line_total for item in self.items), 2)


class OrderItem(Base):
    """Dish in an order; unit_price keeps the price at the moment of the order."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price > 0", name="unit_price_positive"),
        UniqueConstraint("order_id", "dish_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="RESTRICT"))
    quantity: Mapped[int]
    unit_price: Mapped[float] = mapped_column(Price)

    order: Mapped[Order] = relationship(back_populates="items")
    dish: Mapped[Dish] = relationship()

    @property
    def line_total(self) -> float:
        """Return unit price multiplied by quantity."""
        return round(self.unit_price * self.quantity, 2)
