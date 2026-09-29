"""Main entry point: REST API demo of laboratory work 8 (FastAPI, Pydantic, HTTPX, asyncio).

The API runs in the same process through httpx.ASGITransport, so no server or network is needed:
python -m restaurant_orders.main   (a real server: uvicorn restaurant_orders.api.app:app)
"""

import asyncio
import json
import time
from typing import Any
from urllib.parse import unquote

import httpx

from restaurant_orders.api.app import app
from restaurant_orders.api.client import OrderTotal, RetryPolicy, fetch_order_totals
from restaurant_orders.api.transports import DelayTransport, FlakyTransport
from restaurant_orders.data import MENU
from restaurant_orders.persistence.database import database_url
from restaurant_orders.persistence.demo import prepare_database

BASE_URL = "http://restaurant.test"
ORDERS: dict[int, list[dict[str, Any]]] = {
    101: [{"dish": "Борщ", "quantity": 2}, {"dish": "Вареники"}, {"dish": "Узвар", "quantity": 2}],
    102: [{"dish": "Стейк"}, {"dish": "Капучино", "quantity": 2}],
    103: [{"dish": "Борщ"}, {"dish": "Деруни"}, {"dish": "Тірамісу"}],
    104: [{"dish": "Сирник", "quantity": 3}, {"dish": "Капучино"}],
    105: [{"dish": "Бульйон"}, {"dish": "Стейк", "quantity": 2}],
}


def show(response: httpx.Response, body: bool = True) -> Any:
    """Print the method, path, status and JSON body of a response; return the JSON."""
    request = response.request
    path = request.url.path + (f"?{unquote(request.url.query.decode())}" if request.url.query else "")
    data = response.json() if response.content else None
    text = f" {json.dumps(data, ensure_ascii=False)}" if body and data is not None else ""
    print(f"{request.method} {path} → {response.status_code}{text}")
    return data


def print_totals(title: str, results: list[OrderTotal], elapsed: float) -> None:
    """Print totals received by the async client."""
    print(f"{title}: {elapsed:.1f} с")
    for result in results:
        value = f"{result.total:.2f} грн, позицій {result.items_count}" if result.total is not None else result.error
        print(f"  №{result.order_id}: {value} (спроб: {result.attempts})")


async def demo_rest(client: httpx.AsyncClient) -> None:
    """CRUD of dishes, orders with items, totals, statistics and error answers."""
    show(await client.get("/"))
    print("\nМЕНЮ")
    statuses = [(await client.post("/dishes", json={"name": d.name, "category": d.category, "price": d.price}))
                .status_code for d in MENU]
    print(f"POST /dishes × {len(statuses)} → {sorted(set(statuses))}")
    show(await client.get("/dishes", params={"category": "Напої", "sort": "price_asc"}))
    show(await client.patch("/dishes/9", json={"price": 80.0}))
    show(await client.get("/categories"))
    show(await client.get("/dishes", params={"sort": "name", "limit": 3, "offset": 3}))

    print("\nЗАМОВЛЕННЯ")
    for order_id, items in ORDERS.items():
        data = show(await client.post("/orders", json={"id": order_id, "items": items}), body=False)
        print(f"  №{data['id']}: сума {data['total']:.2f} грн, найдорожча — {data['most_expensive']['dish']}")
    show(await client.post("/orders/103/items", json={"dish": "Узвар", "quantity": 2}))
    order = await client.get("/orders/101")
    dumplings = next(item for item in order.json()["items"] if item["dish"] == "Вареники")
    show(await client.delete(f"/orders/101/items/{dumplings['id']}"))
    show(await client.get("/orders/101"))
    show(await client.get("/orders/101/total"))
    show(await client.get("/orders/statistics"))
    history = show(await client.get("/orders", params={"limit": 2, "offset": 1}), body=False)
    print(f"  історія, сторінка 2: {[(item['id'], item['total']) for item in history]}")

    print("\nПОМИЛКИ (structured error responses)")
    show(await client.post("/dishes", json={"name": "Борщ", "category": "Перші страви", "price": 95.0}))
    show(await client.post("/dishes", json={"name": "", "category": "Напої", "price": -5}))
    show(await client.post("/orders", json={"id": 106, "items": [{"dish": "Піца"}]}))
    show(await client.post("/orders", json={"id": 101, "items": [{"dish": "Борщ"}]}))
    show(await client.get("/orders/999"))
    show(await client.delete("/dishes/5"))
    show(await client.get("/dishes", params={"limit": 0}))


async def demo_async(asgi: httpx.ASGITransport) -> None:
    """Concurrent totals with a semaphore, retry after failures and a timeout."""
    order_ids = [101, 102, 103, 104, 105, 999]
    print("\nАСИНХРОННИЙ КЛІЄНТ (httpx.AsyncClient + Task + gather + Semaphore)")
    delayed = DelayTransport(asgi, delay=0.2)
    async with httpx.AsyncClient(transport=delayed, base_url=BASE_URL) as client:
        start = time.perf_counter()
        results = await fetch_order_totals(client, order_ids, max_concurrency=2)
        print_totals(f"{len(order_ids)} запитів по 0.2 с, max_concurrency=2", results, time.perf_counter() - start)
    print(f"  одночасно виконувалось не більше {delayed.max_active} запитів (послідовно було б ≈ "
          f"{0.2 * len(order_ids):.1f} с)")

    print("\nRETRY (перші 2 з'єднання падають, експоненційна затримка 0.1 → 0.2 с)")
    for attempts in (3, 2):
        flaky = FlakyTransport(asgi, failures=2)
        async with httpx.AsyncClient(transport=flaky, base_url=BASE_URL) as client:
            start = time.perf_counter()
            results = await fetch_order_totals(client, [102], policy=RetryPolicy(attempts=attempts, base_delay=0.1))
            print_totals(f"attempts={attempts}", results, time.perf_counter() - start)

    print("\nTIMEOUT (відповідь за 0.5 с, timeout=0.1 с, attempts=2)")
    slow = DelayTransport(asgi, delay=0.5)
    async with httpx.AsyncClient(transport=slow, base_url=BASE_URL) as client:
        start = time.perf_counter()
        results = await fetch_order_totals(client, [101], policy=RetryPolicy(attempts=2, timeout=0.1, base_delay=0.1))
        print_totals("повільний сервер", results, time.perf_counter() - start)


async def run() -> None:
    """Prepare the database and talk to the API over HTTP."""
    asgi = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=asgi, base_url=BASE_URL) as client:
        await demo_rest(client)
    await demo_async(asgi)


def main() -> None:
    """Run the REST API demo on a fresh database."""
    print("REST API ЗАМОВЛЕНЬ РЕСТОРАНУ (лабораторна робота №8, варіант №11)")
    path = prepare_database(database_url())
    print(f"База: {path} (створено заново міграціями Alembic)")
    asyncio.run(run())


if __name__ == "__main__":
    main()
