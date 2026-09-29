"""Database demo of laboratory work 7 (SQLite, SQLAlchemy ORM, Alembic, DB-API).

The demo database is created from scratch on every run: python -m restaurant_orders.persistence.demo
"""

import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from restaurant_orders.data import MENU
from restaurant_orders.persistence.database import create_database_engine, create_session_factory, database_url
from restaurant_orders.persistence.dbapi import find_dishes_by_category
from restaurant_orders.persistence.migrations import current_revision, upgrade_database
from restaurant_orders.persistence.models import Order
from restaurant_orders.persistence.repositories import CategoryRepository, DishRepository, OrderRepository
from restaurant_orders.persistence.services import OrderPlacementError, OrderService

ORDERS: dict[int, list[tuple[str, int]]] = {
    101: [("Борщ", 2), ("Вареники", 1), ("Узвар", 2)],
    102: [("Стейк", 1), ("Капучино", 2)],
    103: [("Борщ", 1), ("Деруни", 1), ("Тірамісу", 1)],
}
INJECTION_ATTEMPT = "Напої' OR '1'='1"
FAILING_ORDERS: dict[int, list[tuple[str, int]]] = {
    104: [("Борщ", 1), ("Піца", 1)],
    105: [("Сирник", 2), ("Узвар", 0)],
}


def prepare_database(url: str) -> str:
    """Delete the old demo SQLite file and create the schema with Alembic migrations; return the file path."""
    path = url.removeprefix("sqlite:///")
    Path(path).unlink(missing_ok=True)
    upgrade_database(url)
    return path


def print_schema(path: str) -> None:
    """Print CREATE TABLE statements stored by SQLite (plain DB-API)."""
    print("\nСХЕМА БАЗИ ДАНИХ (sqlite_master)")
    with closing(sqlite3.connect(path)) as connection:
        for (sql,) in connection.execute("SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"):
            print(sql + ";")


def print_dishes(title: str, session: Session) -> None:
    """Print all dishes sorted by price."""
    print(f"\n{title}")
    for dish in DishRepository(session).list():
        print(f"  #{dish.id:<2} {dish.name:10} {dish.category.name:15} {dish.price:7.2f} грн")


def demo_menu_crud(session: Session) -> None:
    """Create, read, update and delete dishes."""
    categories, dishes = CategoryRepository(session), DishRepository(session)
    for dish in MENU:
        dishes.add(dish.name, categories.get_or_create(dish.category), dish.price)
    session.commit()
    print_dishes("МЕНЮ (Create + Read, сортування за ціною)", session)
    cappuccino = dishes.get_by_name("Капучино")
    assert cappuccino is not None
    dishes.update_price(cappuccino.id, 80.0)
    lemonade = dishes.add("Лимонад", categories.get_or_create("Напої"), 60.0)
    session.commit()
    print(f"\nUpdate: Капучино 75.00 → {cappuccino.price:.2f} грн; Create: Лимонад #{lemonade.id}")
    print(
        f"Delete: Лимонад #{lemonade.id} видалено: {dishes.delete(lemonade.id)}; повторно: {dishes.delete(lemonade.id)}"
    )
    session.commit()
    print(f"Сторінка 2 меню (limit=3, offset=3): {[dish.name for dish in dishes.list(limit=3, offset=3)]}")


def demo_orders(session: Session) -> OrderService:
    """Place orders in transactions and show rollback on errors."""
    service = OrderService(session)
    print("\nОФОРМЛЕННЯ ЗАМОВЛЕНЬ (одна транзакція на замовлення)")
    for order_id, items in ORDERS.items():
        order = service.place_order(order_id, items)
        print(f"commit: замовлення №{order.id}, позицій {len(order.items)}, сума {order.total:.2f} грн")
    for order_id, items in FAILING_ORDERS.items():
        try:
            service.place_order(order_id, items)
        except OrderPlacementError as error:
            cause = f" (причина: {type(error.__cause__).__name__})" if error.__cause__ else ""
            print(f"rollback: {error}{cause}")
    print(f"Замовлень у БД після rollback: {len(OrderRepository(session).history())}")
    service.add_dish(103, "Узвар", 2)
    print(f"Додано до №103: Узвар × 2; видалено з №101 Вареники: {service.remove_dish(101, 'Вареники')}")
    return service


def print_history(service: OrderService, orders: list[Order]) -> None:
    """Print order history with totals and the most expensive item."""
    print("\nІСТОРІЯ ЗАМОВЛЕНЬ (created_at з міграції 0002, час SQLite CURRENT_TIMESTAMP — UTC)")
    for order in orders:
        dishes = ", ".join(f"{item.dish.name} × {item.quantity}" for item in order.items)
        best = service.most_expensive_item(order.id)
        best_text = f"{best.dish.name} ({best.unit_price:.2f} грн)" if best else "—"
        print(
            f"№{order.id} [{order.created_at:%Y-%m-%d %H:%M:%S}] {dishes}; сума {service.order_total(order.id):.2f} грн; "
            f"найдорожча: {best_text}"
        )
    print(f"Середня вартість замовлення (AVG): {service.average_order_value():.2f} грн")


def main() -> None:
    """Run the database demo."""
    url = database_url()
    print("БАЗА ДАНИХ ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №7, варіант №11)")
    path = prepare_database(url)
    engine = create_database_engine(url)
    print(f"База: {path}; міграції Alembic застосовано, поточна ревізія: {current_revision(engine)}")
    print(f"Таблиці: {', '.join(sorted(inspect(engine).get_table_names()))}")
    print_schema(path)
    with create_session_factory(engine)() as session:
        demo_menu_crud(session)
        service = demo_orders(session)
        print_history(service, OrderRepository(session).history())
        print("\nСТАТИСТИКА КАТЕГОРІЙ (JOIN + GROUP BY + SUM)")
        for row in service.category_statistics():
            print(f"  {row.category:15} порцій {row.portions:>2}, виручка {row.revenue:8.2f} грн")
    print("\nDB-API: SELECT … WHERE categories.name = ?  (параметр, а не склеювання рядків)")
    print(f"  «Напої»: {find_dishes_by_category(path, 'Напої')}")
    print(f"  «{INJECTION_ATTEMPT}»: {find_dishes_by_category(path, INJECTION_ATTEMPT)}")
    engine.dispose()


if __name__ == "__main__":
    main()
