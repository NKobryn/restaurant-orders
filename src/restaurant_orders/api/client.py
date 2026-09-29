"""Asynchronous HTTP client of the Restaurant Orders API (httpx.AsyncClient).

Totals of several orders are requested concurrently: asyncio.Task + asyncio.gather, at most
max_concurrency requests at once (asyncio.Semaphore), every attempt limited by a timeout and
temporary failures repeated with exponential backoff.
"""

import asyncio
from dataclasses import dataclass

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """How many attempts to make, how long to wait for one and how long to pause between them."""

    attempts: int = 3
    timeout: float = 2.0
    base_delay: float = 0.1

    def delay(self, attempt: int) -> float:
        """Exponential backoff: base_delay, 2 * base_delay, 4 * base_delay, …"""
        return self.base_delay * (1 << (attempt - 1))


@dataclass(frozen=True, slots=True)
class OrderTotal:
    """Total of one order as received from the API, or the reason why it is missing."""

    order_id: int
    total: float | None
    items_count: int = 0
    attempts: int = 1
    error: str | None = None


class TemporaryServerError(Exception):
    """The server answered 5xx; the request may succeed if repeated."""


async def get_with_retry(client: httpx.AsyncClient, url: str, policy: RetryPolicy) -> tuple[httpx.Response, int]:
    """GET url with a timeout per attempt; repeat after network errors, timeouts and 5xx answers."""
    for attempt in range(1, policy.attempts + 1):
        try:
            response = await asyncio.wait_for(client.get(url), timeout=policy.timeout)
            if response.status_code >= 500:
                raise TemporaryServerError(f"HTTP {response.status_code}")
            return response, attempt
        except (httpx.TransportError, TimeoutError, TemporaryServerError):
            if attempt == policy.attempts:
                raise
            await asyncio.sleep(policy.delay(attempt))
    raise AssertionError("unreachable: the loop either returns or raises")


async def fetch_order_total(
    client: httpx.AsyncClient, order_id: int, semaphore: asyncio.Semaphore, policy: RetryPolicy
) -> OrderTotal:
    """GET /orders/{order_id}/total inside the semaphore; errors become OrderTotal.error."""
    async with semaphore:
        try:
            response, attempts = await get_with_retry(client, f"/orders/{order_id}/total", policy)
        except (httpx.TransportError, TimeoutError, TemporaryServerError) as error:
            reason = type(error).__name__ + (f": {error}" if str(error) else "")
            return OrderTotal(order_id, None, attempts=policy.attempts, error=reason)
    if response.status_code == httpx.codes.NOT_FOUND:
        return OrderTotal(order_id, None, attempts=attempts, error=response.json()["detail"])
    response.raise_for_status()
    data = response.json()
    return OrderTotal(order_id, data["total"], data["items_count"], attempts)


async def fetch_order_totals(
    client: httpx.AsyncClient, order_ids: list[int], max_concurrency: int = 3, policy: RetryPolicy = RetryPolicy()
) -> list[OrderTotal]:
    """Request totals of all orders concurrently and return them in the order of order_ids."""
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        asyncio.create_task(fetch_order_total(client, order_id, semaphore, policy), name=f"order-{order_id}")
        for order_id in order_ids
    ]
    return list(await asyncio.gather(*tasks))


async def fetch_order_totals_from(base_url: str, order_ids: list[int], max_concurrency: int = 3) -> list[OrderTotal]:
    """Open an HTTP client for a running server (uvicorn), use it and close it."""
    async with httpx.AsyncClient(base_url=base_url) as client:
        return await fetch_order_totals(client, order_ids, max_concurrency)
