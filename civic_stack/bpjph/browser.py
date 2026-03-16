"""
Playwright browser helpers for JS-rendered portals.

Camoufox is used for fingerprint randomization to reduce bot detection.
Falls back to standard Playwright chromium if camoufox is not installed.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

# Default viewport sizes to rotate through (avoid fingerprinting by fixed dimensions)
_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 800},
]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


@asynccontextmanager
async def new_page(
    proxy_url: str | None = None,
    headless: bool = True,
) -> AsyncGenerator[Any, None]:
    """
    Async context manager yielding a Playwright page with randomized fingerprint.

    Tries camoufox first (better anti-detection); falls back to standard Playwright.

    Args:
        proxy_url: Optional proxy URL (e.g. Cloudflare Worker endpoint).
        headless: Whether to run headless. Set False for local debugging.
    """
    import random

    viewport = random.choice(_VIEWPORTS)
    user_agent = random.choice(_USER_AGENTS)
    # Chromium/Playwright doesn't support socks5h:// — convert to socks5://
    _proxy_url = proxy_url.replace("socks5h://", "socks5://") if proxy_url else None
    proxy = {"server": _proxy_url} if _proxy_url else None

    try:
        from camoufox.async_api import AsyncCamoufox  # type: ignore[import]

        async with AsyncCamoufox(
            headless=headless,
            proxy=proxy,
        ) as browser:
            page = await browser.new_page()
            yield page
            await page.close()

    except ImportError:
        logger.debug("camoufox not installed, falling back to standard Playwright")
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                proxy=proxy,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            context = await browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="id-ID",
                timezone_id="Asia/Jakarta",
            )
            # Remove navigator.webdriver flag
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()
                await browser.close()


async def wait_for_results(page: Any, selector: str, timeout: int = 15000) -> bool:
    """
    Wait for a results selector to appear on the page.

    Returns True if found, False on timeout (graceful — caller decides how to handle).
    """
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        return False
