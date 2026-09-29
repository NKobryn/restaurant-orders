"""Asynchronous HTTP client of the Restaurant Orders API (httpx.AsyncClient)."""

from dataclasses import dataclass

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class OrderTotal:
    """Total of one order as received from the API, or the reason why it is missing."""

    order_id: int
    total: float | None
    items_count: int = 0
    attempts: int = 1
    error: str | None = None


async def fetch_order_total(client: httpx.AsyncClient, order_id: int) -> OrderTotal:
    """GET /orders/{order_id}/total and turn the JSON answer into OrderTotal."""
    response = await client.get(f"/orders/{order_id}/total")
    if response.status_code == httpx.codes.NOT_FOUND:
        return OrderTotal(order_id, None, error=response.json()["detail"])
    response.raise_for_status()
    data = response.json()
    return OrderTotal(order_id, data["total"], data["items_count"])
