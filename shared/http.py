"""Shared HTTP utilities — rate limiting, retries, proxy support."""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

logger = logging.getLogger("civic_stack")

# Default rate limits per module (requests per minute)
DEFAULT_RATE_LIMIT = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30.0

# Retry status codes
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ScraperBlockedError(Exception):
    """Raised when bot detection blocks the request."""

    pass


class RateLimitedClient:
    """httpx client with built-in rate limiting and exponential backoff.

    Usage:
        async with RateLimitedClient(rpm=10) as client:
            response = await client.get("https://example.go.id/api")
    """

    def __init__(
        self,
        rpm: int = DEFAULT_RATE_LIMIT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.rpm = rpm
        self.min_interval = 60.0 / rpm
        self.max_retries = max_retries
        self.timeout = timeout
        self.proxy_url = proxy_url
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

        default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        }
        if headers:
            default_headers.update(headers)

        transport = httpx.AsyncHTTPTransport(proxy=proxy_url) if proxy_url else None
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=default_headers,
            transport=transport,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "RateLimitedClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    async def _wait_for_rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < self.min_interval:
                wait = self.min_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait:.2f}s")
                await asyncio.sleep(wait)
            self._last_request_time = asyncio.get_event_loop().time()

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with rate limiting and retries."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            await self._wait_for_rate_limit()

            try:
                response = await self._client.request(method, url, **kwargs)

                # Check for bot detection
                if response.status_code == 403:
                    body = response.text[:500].lower()
                    if any(kw in body for kw in ["captcha", "blocked", "forbidden", "cloudflare"]):
                        raise ScraperBlockedError(
                            f"Bot detection triggered at {url} (HTTP 403)"
                        )

                if response.status_code in RETRYABLE_STATUS:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else _backoff(attempt)
                    logger.warning(
                        f"Retryable {response.status_code} from {url}, "
                        f"attempt {attempt + 1}/{self.max_retries + 1}, "
                        f"waiting {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                wait = _backoff(attempt)
                logger.warning(
                    f"Connection error for {url}: {e}, "
                    f"attempt {attempt + 1}/{self.max_retries + 1}, "
                    f"waiting {wait:.1f}s"
                )
                await asyncio.sleep(wait)

        raise last_error or Exception(f"Request to {url} failed after {self.max_retries} retries")

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)


def _backoff(attempt: int) -> float:
    """Exponential backoff with jitter."""
    base = min(2**attempt, 60)
    return base + random.uniform(0, base * 0.5)
