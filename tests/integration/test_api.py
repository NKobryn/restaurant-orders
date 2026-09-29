"""API tests of the REST endpoints (TestClient and httpx.AsyncClient) on a separate test database."""

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from restaurant_orders.api.app import app

pytestmark = pytest.mark.integration

MENU = [("Борщ", "Перші страви", 95.0), ("Стейк", "Основні страви", 280.0), ("Деруни", "Основні страви", 110.0),
        ("Узвар", "Напої", 45.0)]


@pytest.fixture
def client(api_session_factory: Callable[[], Session]) -> Iterator[TestClient]:
    """HTTP client of the application with an empty test database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def menu_client(client: TestClient) -> TestClient:
    """Client whose database already has four dishes."""
    for name, category, price in MENU:
        assert client.post("/dishes", json={"name": name, "category": category, "price": price}).status_code == 201
    return client


def create_order(client: TestClient, order_id: int, *items: tuple[str, int]) -> dict[str, Any]:
    """POST /orders and return the JSON answer."""
    response = client.post("/orders", json={"id": order_id, "items": [{"dish": d, "quantity": q} for d, q in items]})
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()
    return data


# --- dishes and categories ---

def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_create_dish_returns_201_and_json(client: TestClient) -> None:
    response = client.post("/dishes", json={"name": "  Борщ ", "category": "Перші страви", "price": 95})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Борщ", "category": "Перші страви", "price": 95.0}


def test_duplicate_dish_is_conflict(menu_client: TestClient) -> None:
    response = menu_client.post("/dishes", json={"name": "Борщ", "category": "Перші страви", "price": 90})
    assert response.status_code == 409
    assert response.json() == {"status": 409, "error": "Conflict", "detail": "Страва «Борщ» вже є в меню."}


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name": "", "category": "Напої", "price": 10}, "body.name"),
        ({"name": "Вода", "category": "Напої", "price": 0}, "body.price"),
        ({"name": "Вода", "category": "Напої", "price": 20000}, "body.price"),
        ({"name": "Вода", "price": 10}, "body.category"),
        ({"name": "Вода", "category": "Напої", "price": 10, "color": "red"}, "body.color"),
    ],
    ids=["empty-name", "zero-price", "too-expensive", "missing-category", "extra-field"],
)
def test_invalid_dish_is_422(client: TestClient, body: dict[str, Any], field: str) -> None:
    response = client.post("/dishes", json=body)
    assert response.status_code == 422
    assert response.json()["detail"].startswith(field)


def test_list_dishes_filter_sort_and_pages(menu_client: TestClient) -> None:
    names = lambda response: [dish["name"] for dish in response.json()]  # noqa: E731
    assert names(menu_client.get("/dishes")) == ["Стейк", "Деруни", "Борщ", "Узвар"]
    assert names(menu_client.get("/dishes", params={"category": "Основні страви", "sort": "price_asc"})) == [
        "Деруни", "Стейк"]
    assert names(menu_client.get("/dishes", params={"sort": "name", "limit": 2, "offset": 1})) == ["Деруни", "Стейк"]
    assert menu_client.get("/dishes", params={"sort": "random"}).status_code == 422
    assert menu_client.get("/dishes", params={"limit": 0}).status_code == 422


def test_get_update_and_delete_dish(menu_client: TestClient) -> None:
    assert menu_client.get("/dishes/4").json()["name"] == "Узвар"
    assert menu_client.get("/dishes/99").status_code == 404
    updated = menu_client.patch("/dishes/4", json={"price": 50, "category": "Гарячі напої"}).json()
    assert updated == {"id": 4, "name": "Узвар", "category": "Гарячі напої", "price": 50.0}
    assert menu_client.patch("/dishes/4", json={"price": -1}).status_code == 422
    assert menu_client.delete("/dishes/4").status_code == 204
    assert menu_client.delete("/dishes/4").status_code == 404


def test_dish_used_in_order_cannot_be_deleted(menu_client: TestClient) -> None:
    create_order(menu_client, 1, ("Борщ", 1))
    response = menu_client.delete("/dishes/1")
    assert response.status_code == 409
    assert menu_client.get("/dishes/1").status_code == 200


def test_categories_with_counts(menu_client: TestClient) -> None:
    counts = {row["name"]: row["dishes_count"] for row in menu_client.get("/categories").json()}
    assert counts == {"Перші страви": 1, "Основні страви": 2, "Напої": 1}


# --- orders ---

def test_create_and_get_order(menu_client: TestClient) -> None:
    data = create_order(menu_client, 101, ("Борщ", 2), ("Узвар", 2))
    assert data["total"] == 280.0
    assert data["most_expensive"]["dish"] == "Борщ"
    loaded = menu_client.get("/orders/101").json()
    assert [(item["dish"], item["quantity"], item["line_total"]) for item in loaded["items"]] == [
        ("Борщ", 2, 190.0), ("Узвар", 2, 90.0)]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"id": 5, "items": [{"dish": "Піца"}]}, 404),
        ({"id": 5, "items": []}, 422),
        ({"id": 0, "items": [{"dish": "Борщ"}]}, 422),
        ({"id": 5, "items": [{"dish": "Борщ", "quantity": 0}]}, 422),
        ({"id": 5, "items": [{"dish": "Борщ"}, {"dish": "Борщ"}]}, 409),
    ],
    ids=["unknown-dish", "no-items", "zero-id", "zero-quantity", "same-dish-twice"],
)
def test_invalid_orders(menu_client: TestClient, body: dict[str, Any], code: int) -> None:
    assert menu_client.post("/orders", json=body).status_code == code
    assert menu_client.get("/orders/5").status_code == 404


def test_duplicate_order_number_is_conflict(menu_client: TestClient) -> None:
    create_order(menu_client, 7, ("Борщ", 1))
    response = menu_client.post("/orders", json={"id": 7, "items": [{"dish": "Узвар"}]})
    assert response.status_code == 409
    assert "вже існує" in response.json()["detail"]


def test_add_and_delete_items(menu_client: TestClient) -> None:
    create_order(menu_client, 3, ("Борщ", 1))
    added = menu_client.post("/orders/3/items", json={"dish": "Стейк", "quantity": 2})
    assert added.status_code == 201
    assert menu_client.get("/orders/3/total").json() == {"order_id": 3, "items_count": 2, "total": 655.0}
    assert menu_client.delete(f"/orders/3/items/{added.json()['id']}").status_code == 204
    assert menu_client.delete(f"/orders/3/items/{added.json()['id']}").status_code == 404
    assert menu_client.post("/orders/99/items", json={"dish": "Борщ"}).status_code == 404
    assert menu_client.post("/orders/3/items", json={"dish": "Піца"}).status_code == 404


def test_statistics_and_history(menu_client: TestClient) -> None:
    create_order(menu_client, 1, ("Борщ", 2))
    create_order(menu_client, 2, ("Стейк", 1), ("Узвар", 2))
    stats = menu_client.get("/orders/statistics").json()
    assert stats["orders_count"] == 2
    assert stats["average_order_value"] == pytest.approx((190 + 370) / 2)
    assert stats["categories"][0] == {"category": "Основні страви", "portions": 1, "revenue": 280.0}
    history = menu_client.get("/orders", params={"limit": 1, "offset": 1}).json()
    assert [order["id"] for order in history] == [2]


def test_path_parameter_must_be_integer(menu_client: TestClient) -> None:
    response = menu_client.get("/orders/abc/total")
    assert response.status_code == 422
    assert response.json()["detail"].startswith("path.order_id")


@pytest.mark.asyncio
async def test_api_with_async_client(api_session_factory: Callable[[], Session]) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/dishes", json={"name": "Узвар", "category": "Напої", "price": 45})
        order = await client.post("/orders", json={"id": 1, "items": [{"dish": "Узвар", "quantity": 3}]})
        total = await client.get("/orders/1/total")
    assert (created.status_code, order.status_code, total.status_code) == (201, 201, 200)
    assert total.json()["total"] == 135.0


def test_rest_demo(tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from restaurant_orders.api.dependencies import session_factory
    from restaurant_orders.api.demo import main

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    session_factory.cache_clear()
    main()
    session_factory.cache_clear()
    output = capsys.readouterr().out
    assert "POST /dishes × 9 → [201]" in output
    assert "GET /orders/101/total → 200" in output
    assert "DELETE /dishes/5 → 409" in output
    assert "№102: 440.00 грн, позицій 2 (спроб: 3)" in output
    assert "№101: TimeoutError (спроб: 2)" in output
