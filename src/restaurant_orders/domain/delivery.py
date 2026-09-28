"""Asynchronous delivery of paid orders."""

import asyncio
from typing import Protocol

from restaurant_orders.domain.exceptions import DeliveryError, OrderStateError
from restaurant_orders.domain.models import Order, OrderStatus
from restaurant_orders.domain.protocols import KitchenNotifier


class DeliveryService(Protocol):
    """External delivery service with an asynchronous API."""

    async def schedule(self, order_id: int, address: str) -> str: ...


class DemoDeliveryService:
    """Delivery service for the demo: waits a little and returns a tracking number."""

    def __init__(self, delay: float = 0.01) -> None:
        self.delay = delay

    async def schedule(self, order_id: int, address: str) -> str:
        await asyncio.sleep(self.delay)
        return f"DLV-{order_id}"


async def dispatch_paid_order(
    order: Order, address: str, delivery: DeliveryService, notifier: KitchenNotifier
) -> str:
    """Pass a paid order to delivery and tell the kitchen the tracking number."""
    if order.status is not OrderStatus.PAID:
        raise OrderStateError(f"Замовлення №{order.id} ще не оплачено.")
    if not address.strip():
        raise DeliveryError("Адреса доставки порожня.")
    tracking = await delivery.schedule(order.id, address.strip())
    notifier.notify(f"замовлення №{order.id} передано в доставку ({tracking})")
    return tracking
