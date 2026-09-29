"""Integration tests of the persistence layer on a separate test database."""

from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from restaurant_orders.persistence.database import (
    DEFAULT_DATABASE_URL,
    Base,
    create_database_engine,
    create_session_factory,
    database_url,
)
from restaurant_orders.persistence.dbapi import find_dishes_by_category
from restaurant_orders.persistence.migrations import current_revision, downgrade_database, upgrade_database
from restaurant_orders.persistence.models import Order, OrderItem
from restaurant_orders.persistence.repositories import CategoryRepository, DishRepository, OrderRepository
from restaurant_orders.persistence.services import OrderPlacementError, OrderService

pytestmark = pytest.mark.integration

PROJECT = Path(__file__).resolve().parents[2]


def count(session: Session, model: type[Order] | type[OrderItem]) -> int:
    """Number of rows in the table of the model."""
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


# --- CRUD of dishes ---

def test_create_and_read_dish(db_session: Session) -> None:
    category = CategoryRepository(db_session).get_or_create("Напої")
    dish = DishRepository(db_session).add("Узвар", category, 45)
    db_session.commit()
    loaded = DishRepository(db_session).get(dish.id)
    assert loaded is not None
    assert (loaded.name, loaded.price, loaded.category.name) == ("Узвар", 45.0, "Напої")


def test_update_dish_price(menu_session: Session) -> None:
    dishes = DishRepository(menu_session)
    borscht = dishes.get_by_name("Борщ")
    assert borscht is not None
    dishes.update_price(borscht.id, 99.5)
    menu_session.commit()
    menu_session.expire_all()
    assert dishes.get(borscht.id).price == pytest.approx(99.5)  # type: ignore[union-attr]
    assert dishes.update_price(999, 10.0) is None


def test_delete_dish(menu_session: Session) -> None:
    dishes = DishRepository(menu_session)
    uzvar = dishes.get_by_name("Узвар")
    assert uzvar is not None
    assert dishes.delete(uzvar.id) is True
    menu_session.commit()
    assert dishes.get(uzvar.id) is None
    assert dishes.delete(uzvar.id) is False


def test_list_filters_sorts_and_pages(menu_session: Session) -> None:
    dishes = DishRepository(menu_session)
    assert [dish.name for dish in dishes.list()] == ["Стейк", "Деруни", "Борщ", "Узвар"]
    assert [dish.name for dish in dishes.list(category="Основні страви")] == ["Стейк", "Деруни"]
    assert [dish.name for dish in dishes.list(limit=2, offset=2)] == ["Борщ", "Узвар"]


def test_category_is_created_once(db_session: Session) -> None:
    categories = CategoryRepository(db_session)
    assert categories.get_or_create("Десерти") is categories.get_or_create("Десерти")


# --- orders, totals and aggregates ---

def test_place_order_saves_all_items(menu_session: Session) -> None:
    service = OrderService(menu_session)
    order = service.place_order(101, [("Борщ", 2), ("Узвар", 2)])
    menu_session.expire_all()
    assert count(menu_session, OrderItem) == 2
    assert service.order_total(101) == pytest.approx(280.0)
    assert order.total == pytest.approx(280.0)


def test_most_expensive_item_and_tie(menu_session: Session) -> None:
    service = OrderService(menu_session)
    service.place_order(101, [("Деруни", 1), ("Стейк", 1), ("Борщ", 1)])
    item = service.most_expensive_item(101)
    assert item is not None and item.dish.name == "Стейк"
    assert service.most_expensive_item(999) is None


def test_average_order_value(menu_session: Session) -> None:
    service = OrderService(menu_session)
    assert service.average_order_value() == 0.0
    service.place_order(1, [("Борщ", 2)])
    service.place_order(2, [("Стейк", 1), ("Узвар", 2)])
    assert service.average_order_value() == pytest.approx((190 + 370) / 2)


def test_add_and_remove_dish(menu_session: Session) -> None:
    service = OrderService(menu_session)
    service.place_order(7, [("Борщ", 1)])
    service.add_dish(7, "Узвар", 3)
    assert service.order_total(7) == pytest.approx(230.0)
    assert service.remove_dish(7, "Борщ") is True
    assert service.remove_dish(7, "Борщ") is False
    assert service.order_total(7) == pytest.approx(135.0)
    with pytest.raises(OrderPlacementError):
        service.add_dish(7, "Піца")
    with pytest.raises(OrderPlacementError):
        service.add_dish(7, "Узвар")


def test_unit_price_keeps_history_after_menu_change(menu_session: Session) -> None:
    service = OrderService(menu_session)
    service.place_order(5, [("Стейк", 1)])
    steak = DishRepository(menu_session).get_by_name("Стейк")
    assert steak is not None
    DishRepository(menu_session).update_price(steak.id, 300.0)
    menu_session.commit()
    assert service.order_total(5) == pytest.approx(280.0)


def test_history_and_category_statistics(menu_session: Session) -> None:
    service = OrderService(menu_session)
    service.place_order(2, [("Узвар", 2)])
    service.place_order(1, [("Стейк", 1), ("Узвар", 1)])
    history = OrderRepository(menu_session).history()
    assert [order.id for order in history] == [1, 2] or history[0].created_at <= history[1].created_at
    assert all(order.created_at is not None for order in history)
    stats = {row.category: (row.portions, row.revenue) for row in service.category_statistics()}
    assert stats == {"Основні страви": (1, 280.0), "Напої": (3, 135.0)}


# --- transactions, rollback and constraints ---

@pytest.mark.parametrize(
    ("items", "message"),
    [
        ([("Борщ", 1), ("Піца", 1)], "Піца"),
        ([("Борщ", 1), ("Узвар", 0)], "обмеження"),
        ([("Борщ", 1), ("Борщ", 2)], "обмеження"),
        ([], "порожнє"),
    ],
    ids=["unknown-dish", "check-quantity", "unique-dish-in-order", "empty-order"],
)
def test_failed_order_is_rolled_back(menu_session: Session, items: list[tuple[str, int]], message: str) -> None:
    with pytest.raises(OrderPlacementError, match=message):
        OrderService(menu_session).place_order(104, items)
    assert count(menu_session, Order) == 0
    assert count(menu_session, OrderItem) == 0


def test_rollback_keeps_earlier_orders(menu_session: Session) -> None:
    service = OrderService(menu_session)
    service.place_order(1, [("Борщ", 1)])
    with pytest.raises(OrderPlacementError, match="вже існує"):
        service.place_order(1, [("Узвар", 1)])
    with pytest.raises(OrderPlacementError) as error_info:
        service.place_order(2, [("Узвар", -1)])
    assert isinstance(error_info.value.__cause__, IntegrityError)
    assert count(menu_session, Order) == 1
    assert service.order_total(1) == pytest.approx(95.0)


def test_check_constraint_on_price(db_session: Session) -> None:
    category = CategoryRepository(db_session).get_or_create("Напої")
    with pytest.raises(IntegrityError, match="CHECK"):
        DishRepository(db_session).add("Вода", category, 0)
    db_session.rollback()


def test_foreign_key_rejects_unknown_category(db_session: Session) -> None:
    from restaurant_orders.persistence.models import Dish

    db_session.add(Dish(name="Вода", price=20.0, category_id=999))
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_restricts_deleting_category_with_dishes(menu_session: Session) -> None:
    category = CategoryRepository(menu_session).get_by_name("Напої")
    menu_session.delete(category)
    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        menu_session.commit()
    menu_session.rollback()


def test_deleting_order_cascades_to_items(menu_session: Session) -> None:
    OrderService(menu_session).place_order(3, [("Борщ", 1), ("Узвар", 1)])
    assert OrderRepository(menu_session).delete(3) is True
    menu_session.commit()
    assert count(menu_session, OrderItem) == 0
    assert OrderRepository(menu_session).delete(3) is False


# --- DB-API, migrations, configuration, application ---

def test_dbapi_parameterized_search(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'menu.db'}"
    engine = create_database_engine(url)
    Base.metadata.create_all(engine)
    with create_session_factory(engine)() as session:
        categories, dishes = CategoryRepository(session), DishRepository(session)
        dishes.add("Узвар", categories.get_or_create("Напої"), 45.0)
        dishes.add("Капучино", categories.get_or_create("Напої"), 75.0)
        dishes.add("Борщ", categories.get_or_create("Перші страви"), 95.0)
        session.commit()
    engine.dispose()
    path = str(tmp_path / "menu.db")
    assert find_dishes_by_category(path, "Напої") == [("Капучино", 75.0), ("Узвар", 45.0)]
    assert find_dishes_by_category(path, "Напої' OR '1'='1") == []


def test_migrations_upgrade_and_downgrade(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    ini = PROJECT / "alembic.ini"
    upgrade_database(url, ini_path=ini)
    engine = create_database_engine(url)
    assert current_revision(engine) == "0002"
    assert "created_at" in [column["name"] for column in inspect(engine).get_columns("orders")]
    downgrade_database(url, "0001", ini_path=ini)
    assert "created_at" not in [column["name"] for column in inspect(engine).get_columns("orders")]
    downgrade_database(url, "base", ini_path=ini)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()


def test_database_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///other.db")
    assert database_url() == "sqlite:///other.db"
    monkeypatch.delenv("DATABASE_URL")
    assert database_url() == DEFAULT_DATABASE_URL


def test_database_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from restaurant_orders.persistence.demo import main

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    main()
    output = capsys.readouterr().out
    assert "поточна ревізія: 0002" in output
    assert "rollback: Страви «Піца» немає в меню." in output
    assert "Замовлень у БД після rollback: 3" in output
    assert "Середня вартість замовлення (AVG): 375.00 грн" in output
