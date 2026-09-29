"""Tests of the asynchronous client: Task + gather, Semaphore, timeout, retry with a mocked HTTP service."""

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.orm import Session

from restaurant_orders.api import client as client_module
from restaurant_orders.api.app import app
from restaurant_orders.api.client import RetryPolicy, fetch_order_totals, fetch_order_totals_from
from restaurant_orders.api.transports import DelayTransport, FlakyTransport

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

FAST = RetryPolicy(attempts=3, timeout=1.0, base_delay=0.001)


def mock_service(totals: dict[int, float], failures: dict[int, int] | None = None) -> httpx.MockTransport:
    """Mock of the external HTTP service: /orders/{id}/total answers, some ids fail with 503 first."""
    left = dict(failures or {})

    def handler(request: httpx.Request) -> httpx.Response:
        order_id = int(request.url.path.split("/")[2])
        if left.get(order_id, 0) > 0:
            left[order_id] -= 1
            return httpx.Response(503, json={"detail": "busy"})
        if order_id not in totals:
            return httpx.Response(404, json={"detail": f"Замовлення №{order_id} не знайдено."})
        return httpx.Response(200, json={"order_id": order_id, "items_count": 1, "total": totals[order_id]})

    return httpx.MockTransport(handler)


async def test_totals_are_fetched_concurrently_in_order() -> None:
    delayed = DelayTransport(mock_service({1: 10.0, 2: 20.0, 3: 30.0, 4: 40.0}), delay=0.05)
    async with httpx.AsyncClient(transport=delayed, base_url="http://test") as client:
        results = await fetch_order_totals(client, [4, 1, 3, 2, 99], max_concurrency=2, policy=FAST)
    assert [(r.order_id, r.total) for r in results] == [(4, 40.0), (1, 10.0), (3, 30.0), (2, 20.0), (99, None)]
    assert results[-1].error == "Замовлення №99 не знайдено."
    assert delayed.max_active == 2
    assert delayed.requests == 5


@pytest.mark.parametrize("limit", [1, 3, 10])
async def test_semaphore_limits_concurrency(limit: int) -> None:
    delayed = DelayTransport(mock_service({number: 1.0 for number in range(1, 8)}), delay=0.02)
    async with httpx.AsyncClient(transport=delayed, base_url="http://test") as client:
        await fetch_order_totals(client, list(range(1, 8)), max_concurrency=limit, policy=FAST)
    assert delayed.max_active == min(limit, 7)


async def test_retry_after_server_errors() -> None:
    async with httpx.AsyncClient(transport=mock_service({5: 55.0}, failures={5: 2}), base_url="http://test") as client:
        [result] = await fetch_order_totals(client, [5], policy=FAST)
    assert (result.total, result.attempts, result.error) == (55.0, 3, None)


async def test_retry_gives_up_after_all_attempts() -> None:
    flaky = FlakyTransport(mock_service({5: 55.0}), failures=5)
    async with httpx.AsyncClient(transport=flaky, base_url="http://test") as client:
        [result] = await fetch_order_totals(client, [5], policy=FAST)
    assert result.total is None
    assert result.error is not None and result.error.startswith("ConnectError")
    assert flaky.requests == FAST.attempts


async def test_exponential_backoff_between_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr(client_module.asyncio, "sleep", sleep)
    flaky = FlakyTransport(mock_service({1: 1.0}), failures=3)
    async with httpx.AsyncClient(transport=flaky, base_url="http://test") as client:
        await fetch_order_totals(client, [1], policy=RetryPolicy(attempts=4, base_delay=0.1))
    assert [call.args[0] for call in sleep.await_args_list] == pytest.approx([0.1, 0.2, 0.4])


async def test_timeout_is_reported() -> None:
    slow = DelayTransport(mock_service({1: 1.0}), delay=0.2)
    async with httpx.AsyncClient(transport=slow, base_url="http://test") as client:
        [result] = await fetch_order_totals(client, [1], policy=RetryPolicy(attempts=2, timeout=0.02, base_delay=0.001))
    assert (result.total, result.error, result.attempts) == (None, "TimeoutError", 2)


async def test_client_against_the_real_application(
    api_session_factory: Callable[[], Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/dishes", json={"name": "Борщ", "category": "Перші страви", "price": 95})
        await client.post("/orders", json={"id": 1, "items": [{"dish": "Борщ", "quantity": 2}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        client_module.httpx, "AsyncClient", lambda base_url: original(transport=transport, base_url=base_url)
    )
    [result] = await fetch_order_totals_from("http://test", [1])
    assert result.total == 190.0


async def test_tasks_run_at_the_same_time() -> None:
    delayed = DelayTransport(mock_service({number: 1.0 for number in range(1, 6)}), delay=0.1)
    async with httpx.AsyncClient(transport=delayed, base_url="http://test") as client:
        start = asyncio.get_running_loop().time()
        await fetch_order_totals(client, [1, 2, 3, 4, 5], max_concurrency=5, policy=FAST)
        elapsed = asyncio.get_running_loop().time() - start
    assert elapsed < 0.3
