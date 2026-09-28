"""Concrete implementations of the payment and notification protocols."""

from restaurant_orders.domain.exceptions import PaymentError
from restaurant_orders.domain.value_objects import Money


class DemoPaymentGateway:
    """Payment gateway for the demo: accepts every payment."""

    def __init__(self) -> None:
        self.payments_count = 0

    def pay(self, order_id: int, amount: Money) -> str:
        self.payments_count += 1
        payment_id = f"PAY-{self.payments_count:03d}"
        print(f"[оплата] замовлення №{order_id}: {amount} → {payment_id}")
        return payment_id


class LimitedPaymentGateway:
    """Payment gateway that refuses payments above a card limit."""

    def __init__(self, limit: Money) -> None:
        self.limit = limit

    def pay(self, order_id: int, amount: Money) -> str:
        if amount > self.limit:
            raise PaymentError(f"Сума {amount} перевищує ліміт картки {self.limit}.")
        return f"CARD-{order_id}"


class ConsoleKitchenNotifier:
    """Notifier that prints messages for the kitchen to the console."""

    def notify(self, message: str) -> None:
        print(f"[кухня] {message}")
