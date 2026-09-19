"""Business logic independent of the console interface."""

from restaurant_orders.models import Dish, Order


class OrderNotFoundError(ValueError):
    """Raised when an operation refers to an absent order."""


def create_order(orders: list[Order], number: int) -> Order:
    """Create and store an order, rejecting a duplicate number."""
    if find_order(orders, number) is not None:
        raise ValueError(f"Замовлення №{number} вже існує.")
    order = Order(number=number)
    orders.append(order)
    return order


def find_order(orders: list[Order], number: int) -> Order | None:
    """Find an order by its number."""
    return next((order for order in orders if order.number == number), None)


def add_dish_to_order(orders: list[Order], number: int, dish: Dish) -> None:
    """Add a dish to an existing order."""
    order = find_order(orders, number)
    if order is None:
        raise OrderNotFoundError(f"Замовлення №{number} не знайдено.")
    order.add_dish(dish)


def calculate_order_total(order: Order) -> float:
    """Return the total price of all dishes in an order."""
    return sum(dish.price for dish in order.dishes)


def find_most_expensive_dish(order: Order) -> Dish | None:
    """Return the most expensive dish in an order, if it exists."""
    return max(order.dishes, key=lambda dish: dish.price, default=None)


def calculate_average_order_value(orders: list[Order]) -> float:
    """Return the average total value across all orders."""
    if not orders:
        return 0.0
    return sum(calculate_order_total(order) for order in orders) / len(orders)


def sort_orders_by_total(orders: list[Order]) -> list[Order]:
    """Return orders from the highest total to the lowest."""
    return sorted(orders, key=calculate_order_total, reverse=True)
