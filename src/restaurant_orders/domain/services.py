"""Application layer: use cases of the restaurant."""

from restaurant_orders.domain.exceptions import OrderNotFoundError, OrderStateError
from restaurant_orders.domain.models import Dish, Menu, Order, OrderStatus
from restaurant_orders.domain.pricing import PricingPolicy
from restaurant_orders.domain.protocols import KitchenNotifier, PaymentGateway
from restaurant_orders.domain.repositories import Repository
from restaurant_orders.domain.value_objects import Money


class RestaurantService:
    """Creates and pays orders; all dependencies are passed into the constructor."""

    def __init__(
        self,
        menu: Menu,
        orders: Repository[Order],
        payment_gateway: PaymentGateway,
        notifier: KitchenNotifier,
        pricing: PricingPolicy,
        first_order_id: int = 1,
    ) -> None:
        self._menu = menu
        self._orders = orders
        self._payment_gateway = payment_gateway
        self._notifier = notifier
        self._pricing = pricing
        self._next_order_id = first_order_id

    def create_order(self) -> Order:
        """Create an empty order with the next number and save it."""
        order = Order(self._next_order_id)
        self._next_order_id += 1
        self._orders.add(order)
        return order

    def add_dish(self, order_id: int, dish_id: int, quantity: int = 1) -> Order:
        """Add a dish from the menu to an existing order."""
        order = self._get_order(order_id)
        order.add_dish(self._menu[dish_id], quantity)
        return order

    def order_total(self, order_id: int) -> Money:
        """Return the amount to pay according to the pricing policy."""
        return self._pricing.final_total(self._get_order(order_id))

    def most_expensive_dish(self, order_id: int) -> Dish | None:
        """Return the most expensive dish of the order."""
        return self._get_order(order_id).most_expensive_dish()

    def average_order_value(self) -> Money:
        """Return the average amount to pay for all non-empty orders."""
        totals = [self._pricing.final_total(order) for order in self._orders.all() if len(order) > 0]
        if not totals:
            return Money(0)
        return Money(round(sum(total.amount for total in totals) / len(totals), 2))

    def checkout(self, order_id: int) -> str:
        """Pay for the order, mark it paid and notify the kitchen."""
        order = self._get_order(order_id)
        if order.status is not OrderStatus.NEW:
            raise OrderStateError(f"Замовлення №{order_id} вже має статус {order.status.value}.")
        if len(order) == 0:
            raise OrderStateError(f"Замовлення №{order_id} порожнє.")
        payment_id = self._payment_gateway.pay(order.id, self.order_total(order_id))
        order.mark_paid()
        self._orders.add(order)
        dishes = ", ".join(f"{item.dish.name} × {item.quantity}" for item in order)
        self._notifier.notify(f"замовлення №{order.id} оплачено ({payment_id}): {dishes}")
        return payment_id

    def _get_order(self, order_id: int) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Замовлення №{order_id} не знайдено.")
        return order
