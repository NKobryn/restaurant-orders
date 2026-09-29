"""Shared fixtures of the test suite (pytest finds them automatically)."""

import logging
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest.mock import Mock, create_autospec

import pytest
from sqlalchemy.orm import Session

from restaurant_orders.config import get_settings
from restaurant_orders.domain.models import Dish, Menu, Order
from restaurant_orders.domain.pricing import CategoryDiscount, NoDiscount, PricingPolicy
from restaurant_orders.domain.protocols import KitchenNotifier, PaymentGateway
from restaurant_orders.domain.repositories import Repository
from restaurant_orders.domain.value_objects import Money

CSV_HEADER = "order_id,dish,category,price,quantity\n"
CONFIG_TEMPLATE = """schema_version: 1
input: {{path: {input}}}
output: {{path: {folder}/orders.json, errors_path: {folder}/invalid.csv, summary_path: {folder}/summary.json}}
processing:
  skip_invalid: {skip_invalid}
  allowed_categories: [{categories}]
  price_range: {{min: 20, max: 500}}
logging: {{level: INFO, path: {folder}/logs/import.log}}
"""


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    """Settings are cached by get_settings(); every test reads the environment again."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeOrderRepository(Repository[Order]):
    """Fake: a small working repository that keeps orders in a dict and counts saves."""

    def __init__(self) -> None:
        self.items: dict[int, Order] = {}
        self.saves = 0

    def add(self, item: Order) -> None:
        self.items[item.id] = item
        self.saves += 1

    def get(self, item_id: int) -> Order | None:
        return self.items.get(item_id)

    def all(self) -> list[Order]:
        return list(self.items.values())


@pytest.fixture(autouse=True)
def quiet_logging() -> Iterator[None]:
    """Autouse fixture with teardown: silence logging during a test and restore it after."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture
def dish_factory() -> Callable[..., Dish]:
    """Fixture factory: create dishes with only the fields a test cares about."""

    def create_dish(dish_id: int = 1, name: str = "Борщ", category: str = "Перші страви", price: float = 95.0) -> Dish:
        return Dish(dish_id, name, category, Money(price))

    return create_dish


@pytest.fixture
def menu(dish_factory: Callable[..., Dish]) -> Menu:
    """Menu of four dishes of different categories."""
    return Menu(
        [
            dish_factory(1, "Борщ", "Перші страви", 95.0),
            dish_factory(3, "Вареники", "Основні страви", 120.0),
            dish_factory(5, "Стейк", "Основні страви", 280.0),
            dish_factory(8, "Узвар", "Напої", 45.0),
        ]
    )


@pytest.fixture
def order_factory(menu: Menu) -> Callable[..., Order]:
    """Fixture factory: create an order from pairs (dish id, quantity)."""

    def create_order(order_id: int = 1, items: tuple[tuple[int, int], ...] = ((1, 2), (8, 1))) -> Order:
        order = Order(order_id)
        for dish_id, quantity in items:
            order.add_dish(menu[dish_id], quantity)
        return order

    return create_order


@pytest.fixture
def fake_repository() -> FakeOrderRepository:
    """Fake order repository with real behaviour."""
    return FakeOrderRepository()


@pytest.fixture
def gateway() -> Mock:
    """Autospec mock of the payment gateway that accepts payments."""
    mock = create_autospec(PaymentGateway, instance=True)
    mock.pay.return_value = "PAY-001"
    return mock


@pytest.fixture
def notifier() -> Mock:
    """Mock of the kitchen notifier restricted to the protocol methods."""
    return Mock(spec=KitchenNotifier)


@pytest.fixture(params=[NoDiscount(), CategoryDiscount("Напої", 20)], ids=["no-discount", "drinks-20%"])
def pricing(request: pytest.FixtureRequest) -> PricingPolicy:
    """Parameterized fixture: every test that uses it runs once per pricing policy."""
    policy: PricingPolicy = request.param
    return policy


@pytest.fixture
def import_files(tmp_path: Path) -> Callable[..., Path]:
    """Fixture factory: write an input CSV and config.yaml into tmp_path and return the config path."""

    def create(rows: str, skip_invalid: bool = True, categories: str = "Перші страви, Основні страви, Напої") -> Path:
        input_path = tmp_path / "orders.csv"
        input_path.write_text(CSV_HEADER + rows, encoding="utf-8")
        config = tmp_path / "config.yaml"
        config.write_text(
            CONFIG_TEMPLATE.format(
                input=input_path, folder=tmp_path, categories=categories, skip_invalid=str(skip_invalid).lower()
            ),
            encoding="utf-8",
        )
        return config

    return create


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Separate test database: a new empty in-memory SQLite database for every test."""
    from restaurant_orders.persistence.database import Base, create_database_engine, create_session_factory

    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = create_session_factory(engine)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def menu_session(db_session: Session) -> Session:
    """Test database with four dishes of three categories."""
    from restaurant_orders.persistence.repositories import CategoryRepository, DishRepository

    categories, dishes = CategoryRepository(db_session), DishRepository(db_session)
    for name, category, price in (
        ("Борщ", "Перші страви", 95.0),
        ("Стейк", "Основні страви", 280.0),
        ("Деруни", "Основні страви", 110.0),
        ("Узвар", "Напої", 45.0),
    ):
        dishes.add(name, categories.get_or_create(category), price)
    db_session.commit()
    return db_session


@pytest.fixture
def api_session_factory() -> Iterator[Callable[[], Session]]:
    """Separate in-memory test database shared by all sessions of one test (StaticPool) for the API."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    from restaurant_orders.api.app import app
    from restaurant_orders.api.dependencies import get_session
    from restaurant_orders.persistence.database import Base, create_session_factory, enable_sqlite_foreign_keys

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", enable_sqlite_foreign_keys)
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)

    def override_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()
