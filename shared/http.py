"""
Shared HTTP utilities for indonesia-civic-stack modules.

Provides:
- A pre-configured httpx.AsyncClient factory with sensible defaults
- Exponential backoff retry logic (respects 429 / 503 / 5xx)
- Rate limiting (token bucket, per-module configurable)
- Proxy URL validation (SSRF prevention)
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import socket
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

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


class UnsafeProxyError(ValueError):
    """Raised when a proxy URL targets private/internal networks (SSRF prevention)."""


# Private IP ranges that must never be proxied to
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_proxy_url(proxy_url: str) -> str:
    """
    Validate a proxy URL to prevent SSRF attacks.

    Rules:
    - Must be http:// or https://
    - Must not resolve to private/internal IP ranges
    - If CIVIC_ALLOWED_PROXIES env var is set, must match one of those hosts

    Raises:
        UnsafeProxyError: If the proxy URL fails validation.
    """
    parsed = urlparse(proxy_url)

    # Must be HTTP(S)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeProxyError(f"Proxy must use http:// or https://, got: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeProxyError("Proxy URL has no hostname")

    # Check allowlist first (if configured)
    allowed = os.environ.get("CIVIC_ALLOWED_PROXIES", "").strip()
    if allowed:
        allowed_hosts = {h.strip().lower() for h in allowed.split(",") if h.strip()}
        if hostname.lower() not in allowed_hosts:
            raise UnsafeProxyError(
                f"Proxy host '{hostname}' not in CIVIC_ALLOWED_PROXIES: {allowed_hosts}"
            )
        return proxy_url  # Allowlisted — skip IP check

    # Resolve hostname and block private IPs
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, parsed.port or 443):
            ip = ipaddress.ip_address(sockaddr[0])
            for net in _PRIVATE_NETWORKS:
                if ip in net:
                    raise UnsafeProxyError(f"Proxy host '{hostname}' resolves to private IP {ip}")
    except socket.gaierror:
        raise UnsafeProxyError(f"Cannot resolve proxy hostname: {hostname}") from None

    return proxy_url


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
        self._lock_loop_id: int | None = None
        self._lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        """Get or recreate lock bound to the current event loop."""
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        if self._lock is None or self._lock_loop_id != loop_id:
            self._lock = asyncio.Lock()
            self._lock_loop_id = loop_id
        return self._lock

    async def acquire(self) -> None:
        async with self._get_lock():
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

    # SSRF prevention: validate proxy URL before use
    if proxy_url:
        proxy_url = validate_proxy_url(proxy_url)

    transport = httpx.AsyncHTTPTransport(proxy=proxy_url) if proxy_url else None
    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
        max_redirects=5,
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
