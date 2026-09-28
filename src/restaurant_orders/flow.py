"""Order flow that joins the laboratory works: import -> orders -> payment -> async delivery."""

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from restaurant_orders.data_io.config import AppConfig
from restaurant_orders.data_io.services import ImportStatistics, valid_records
from restaurant_orders.domain.delivery import DeliveryService, dispatch_paid_order
from restaurant_orders.domain.exceptions import PaymentError
from restaurant_orders.domain.models import Dish, Menu, Order
from restaurant_orders.domain.pricing import NoDiscount
from restaurant_orders.domain.protocols import KitchenNotifier, PaymentGateway
from restaurant_orders.domain.repositories import InMemoryRepository
from restaurant_orders.domain.services import RestaurantService
from restaurant_orders.domain.value_objects import Money
from restaurant_orders.models import OrderItemRecord

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FlowResult:
    """What happened with the imported orders."""

    statistics: ImportStatistics
    orders: list[Order] = field(default_factory=list)
    failed_payments: list[int] = field(default_factory=list)
    deliveries: dict[int, str] = field(default_factory=dict)


def build_menu(records: Iterable[OrderItemRecord]) -> Menu:
    """Create a menu from the dishes that appear in the records (first price wins)."""
    menu = Menu()
    names: set[str] = set()
    for record in records:
        if record.dish not in names:
            names.add(record.dish)
            menu.add(Dish(len(names), record.dish, record.category, Money(record.price)))
    return menu


def build_orders(records: Iterable[OrderItemRecord], menu: Menu) -> InMemoryRepository[Order]:
    """Group records into orders with the same numbers as in the input file."""
    ids_by_name = {dish.name: dish.id for dish in menu}
    orders = InMemoryRepository[Order]()
    for record in records:
        order = orders.get(record.order_id)
        if order is None:
            order = Order(record.order_id)
            orders.add(order)
        order.add_dish(menu[ids_by_name[record.dish]], record.quantity)
    return orders


async def deliver_orders(
    orders: list[Order], address: str, delivery: DeliveryService, notifier: KitchenNotifier
) -> dict[int, str]:
    """Pass every paid order to delivery one after another."""
    return {order.id: await dispatch_paid_order(order, address, delivery, notifier) for order in orders}


def run_order_flow(
    config: AppConfig,
    gateway: PaymentGateway,
    notifier: KitchenNotifier,
    delivery: DeliveryService,
    address: str,
) -> FlowResult:
    """Import valid records, pay every order and deliver the paid ones."""
    result = FlowResult(ImportStatistics())
    # valid_records already logs every skipped record, so nothing else is needed here
    records = list(valid_records(config, result.statistics, lambda error: None))
    menu = build_menu(records)
    orders = build_orders(records, menu)
    service = RestaurantService(menu, orders, gateway, notifier, NoDiscount())
    paid: list[Order] = []
    for order in orders.all():
        result.orders.append(order)
        try:
            service.checkout(order.id)
        except PaymentError as error:
            logger.warning("Оплату замовлення №%d відхилено: %s", order.id, error)
            result.failed_payments.append(order.id)
        else:
            paid.append(order)
    result.deliveries = asyncio.run(deliver_orders(paid, address, delivery, notifier))
    return result
