"""
Shared HTTP utilities for indonesia-civic-stack modules.

Provides:
- A pre-configured httpx.AsyncClient factory with sensible defaults
- Exponential backoff retry logic (respects 429 / 503 / 5xx)
- Rate limiting (token bucket, per-module configurable)
- Proxy support: CONNECT proxy or Cloudflare Worker URL-rewriting proxy
- Auto-reads PROXY_URL from environment if not passed explicitly

Proxy modes (set via PROXY_URL or proxy_url parameter):
- CONNECT proxy:  socks5://... or http://proxy:8080
- CF Worker proxy: https://your-worker.workers.dev (auto-detected by *.workers.dev)
  Requests are rewritten to: https://worker.workers.dev/?url=<encoded-target>

Override auto-detection with PROXY_MODE=connect|rewrite env var.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger(__name__)


def _resolve_proxy() -> tuple[str | None, str]:
    """
    Resolve proxy URL and mode from environment.

    Returns:
        (proxy_url, proxy_mode) where mode is 'connect', 'rewrite', or 'none'.
    """
    url = os.environ.get("PROXY_URL", "").strip() or None
    mode = os.environ.get("PROXY_MODE", "").strip().lower()

    if not url:
        return None, "none"

    if mode in ("connect", "rewrite"):
        return url, mode

    # Auto-detect: *.workers.dev → rewrite mode
    parsed = urlparse(url)
    if parsed.hostname and parsed.hostname.endswith(".workers.dev"):
        return url, "rewrite"

    return url, "connect"


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


class _RewriteProxyClient(httpx.AsyncClient):
    """httpx client that rewrites all request URLs through a CF Worker proxy."""

    def __init__(self, proxy_base: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._proxy_base = proxy_base.rstrip("/")

    async def send(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        """Intercept all requests and rewrite URLs through the proxy."""
        original_url = str(request.url)
        # Only rewrite if not already going to the proxy
        if not original_url.startswith(self._proxy_base):
            rewritten = f"{self._proxy_base}/?url={quote(original_url, safe='')}"
            request = httpx.Request(
                method=request.method,
                url=rewritten,
                headers=request.headers,
                content=request.content,
                extensions=request.extensions,
            )
            logger.debug("Proxy rewrite: %s → %s", original_url, rewritten)
        return await super().send(request, **kwargs)


@asynccontextmanager
async def civic_client(
    proxy_url: str | None = None,
    timeout: float = 30.0,
    extra_headers: dict[str, str] | None = None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Context manager that yields a configured httpx.AsyncClient.

    Proxy resolution order:
    1. Explicit proxy_url parameter
    2. PROXY_URL environment variable

    Proxy modes:
    - 'connect': Standard HTTP/SOCKS CONNECT proxy (httpx transport)
    - 'rewrite': CF Worker URL-rewriting proxy (rewrites URLs in fetch_with_retry)
    - 'none': Direct connection

    Args:
        proxy_url: Optional proxy URL. Auto-read from PROXY_URL env if not set.
        timeout: Request timeout in seconds.
        extra_headers: Module-specific headers merged on top of defaults.
    """
    env_proxy, env_mode = _resolve_proxy()
    resolved_proxy = proxy_url or env_proxy
    mode = (
        env_mode
        if not proxy_url
        else (
            "rewrite"
            if proxy_url
            and (hostname := urlparse(proxy_url).hostname)
            and hostname.endswith(".workers.dev")
            else "connect"
        )
    )

    if resolved_proxy:
        logger.info("Using proxy %s (mode=%s)", resolved_proxy, mode)

    headers = {**DEFAULT_HEADERS, **(extra_headers or {})}

    if resolved_proxy and mode == "rewrite":
        # Use URL-rewriting client — intercepts ALL requests (get, post, etc.)
        async with _RewriteProxyClient(
            proxy_base=resolved_proxy,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            client._civic_proxy_url = resolved_proxy  # type: ignore[attr-defined]
            client._civic_proxy_mode = mode  # type: ignore[attr-defined]
            yield client
    else:
        # Standard client, optionally with CONNECT proxy transport
        transport = (
            httpx.AsyncHTTPTransport(proxy=resolved_proxy)
            if resolved_proxy and mode == "connect"
            else None
        )
        async with httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        ) as client:
            client._civic_proxy_url = resolved_proxy  # type: ignore[attr-defined]
            client._civic_proxy_mode = mode if resolved_proxy else "none"  # type: ignore[attr-defined]
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
    # URL rewriting is handled by _RewriteProxyClient.send() transparently.
    # No special handling needed here — all requests go through the proxy automatically.

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
