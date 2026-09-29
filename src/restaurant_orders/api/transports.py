"""HTTPX transports that wrap another transport to show delays, concurrency and failures."""

import asyncio

import httpx


class DelayTransport(httpx.AsyncBaseTransport):
    """Waits before every request and remembers how many requests were running at the same time."""

    def __init__(self, inner: httpx.AsyncBaseTransport, delay: float) -> None:
        self.inner = inner
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self.requests = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
            return await self.inner.handle_async_request(request)
        finally:
            self.active -= 1


class FlakyTransport(httpx.AsyncBaseTransport):
    """Fails the first `failures` requests with a connection error, then passes requests through."""

    def __init__(self, inner: httpx.AsyncBaseTransport, failures: int) -> None:
        self.inner = inner
        self.failures = failures
        self.requests = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        if self.requests <= self.failures:
            raise httpx.ConnectError(f"імітований збій з'єднання №{self.requests}", request=request)
        return await self.inner.handle_async_request(request)
