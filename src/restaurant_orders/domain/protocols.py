"""Structural interfaces (Protocol) for external services and repositories."""

from typing import Protocol, runtime_checkable

from restaurant_orders.domain.value_objects import Money


class HasId(Protocol):
    """Any object with an integer id can be stored in a repository."""

    id: int


class PaymentGateway(Protocol):
    """Service that takes payment for an order and returns a payment id."""

    def pay(self, order_id: int, amount: Money) -> str: ...


@runtime_checkable
class KitchenNotifier(Protocol):
    """Service that sends a message to the kitchen."""

    def notify(self, message: str) -> None: ...
