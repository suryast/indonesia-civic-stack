"""
Shared HTTP utilities for indonesia-civic-stack modules.

Provides:
- A pre-configured httpx.AsyncClient factory with sensible defaults
- Exponential backoff retry logic (respects 429 / 503 / 5xx)
- Rate limiting (token bucket, per-module configurable)
- proxy_url passthrough so operators can supply their own proxy pool
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retryable HTTP status codes
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}


class ScraperBlockedError(Exception):
    """Raised when the portal actively blocks the scraper after exhausting retries."""


class RateLimiter:
    """
    Simple async token-bucket rate limiter.

    Args:
        rate: Maximum requests per second.
    """

    def __init__(self, rate: float) -> None:
        self._rate = rate
        self._min_interval = 1.0 / rate
        self._last_call: float = 0.0
        self._lock: asyncio.Lock | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def acquire(self) -> None:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._loop is not loop:
            self._lock = asyncio.Lock()
            self._loop = loop
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()


@asynccontextmanager
async def civic_client(
    proxy_url: str | None = None,
    timeout: float = 30.0,
    extra_headers: dict[str, str] | None = None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Context manager that yields a configured httpx.AsyncClient.

    Args:
        proxy_url: Optional HTTP/HTTPS proxy URL (e.g. Cloudflare Worker endpoint).
        timeout: Request timeout in seconds.
        extra_headers: Module-specific headers merged on top of defaults.
    """
    headers = {**DEFAULT_HEADERS, **(extra_headers or {})}
    transport = httpx.AsyncHTTPTransport(proxy=proxy_url) if proxy_url else None
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
        transport=transport,
    ) as client:
        yield client


async def fetch_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 4,
    base_backoff: float = 2.0,
    rate_limiter: RateLimiter | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """
    Perform an HTTP request with exponential backoff on retryable errors.

    Backoff schedule: 2s, 4s, 8s, 16s (base_backoff ** attempt).

    Raises:
        ScraperBlockedError: If all retries are exhausted on a 429/503.
        httpx.HTTPStatusError: For non-retryable 4xx responses.
        httpx.RequestError: For network-level failures after all retries.
    """
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        if rate_limiter:
            await rate_limiter.acquire()

        try:
            response = await client.request(method, url, **kwargs)

            if response.status_code in RETRYABLE_STATUS:
                wait = base_backoff**attempt
                logger.warning(
                    "Retryable %s from %s — attempt %d/%d, backing off %.1fs",
                    response.status_code,
                    url,
                    attempt + 1,
                    max_retries + 1,
                    wait,
                )
                if attempt < max_retries:
                    await asyncio.sleep(wait)
                    continue
                raise ScraperBlockedError(
                    f"Portal returned {response.status_code} after {max_retries + 1} attempts: {url}"
                )

            response.raise_for_status()
            return response

        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            wait = base_backoff**attempt
            logger.warning(
                "Network error on %s — attempt %d/%d, backing off %.1fs: %s",
                url,
                attempt + 1,
                max_retries + 1,
                wait,
                exc,
            )
            last_exc = exc
            if attempt < max_retries:
                await asyncio.sleep(wait)

    raise httpx.RequestError(f"All {max_retries + 1} attempts failed for {url}") from last_exc
