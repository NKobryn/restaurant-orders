"""Main entry point: order flow of laboratory work 6 (import -> orders -> payment -> async delivery).

Usage: python -m restaurant_orders.main [config.yaml]
"""

import logging
import sys
from pathlib import Path

from restaurant_orders.data_io.config import load_config
from restaurant_orders.data_io.exceptions import ApplicationError
from restaurant_orders.domain.adapters import ConsoleKitchenNotifier, LimitedPaymentGateway
from restaurant_orders.domain.delivery import DemoDeliveryService
from restaurant_orders.domain.value_objects import Money
from restaurant_orders.flow import FlowResult, run_order_flow

ADDRESS = "Львів, вул. Університетська, 1"
CARD_LIMIT = Money(450.0)


def print_result(result: FlowResult) -> None:
    """Print imported orders, payments and deliveries."""
    statistics = result.statistics
    print(f"\nІмпортовано позицій: {statistics.valid} з {statistics.total} (пропущено {statistics.invalid})")
    print("\nЗАМОВЛЕННЯ")
    for order in result.orders:
        dishes = ", ".join(f"{item.dish.name} × {item.quantity}" for item in order)
        tracking = result.deliveries.get(order.id, "—")
        print(f"№{order.id} [{order.status.value}] {order.total}: {dishes}; доставка: {tracking}")
    print(f"\nОплачено й передано в доставку: {len(result.deliveries)}; оплату відхилено: {result.failed_payments}")


def main(argv: list[str] | None = None) -> int:
    """Run the order flow; return 0 on success and 1 on an application error."""
    arguments = sys.argv[1:] if argv is None else argv
    config_path = Path(arguments[0]) if arguments else Path("config.yaml")
    print("ПОВНИЙ СЦЕНАРІЙ ЗАМОВЛЕННЯ (лабораторна робота №6, варіант №11)")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s", stream=sys.stdout, force=True)
    try:
        config = load_config(config_path)
        result = run_order_flow(config, LimitedPaymentGateway(CARD_LIMIT), ConsoleKitchenNotifier(),
                                DemoDeliveryService(), ADDRESS)
    except ApplicationError as error:
        print(f"CRITICAL | {error} (причина: {error.__cause__!r})")
        return 1
    print_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
