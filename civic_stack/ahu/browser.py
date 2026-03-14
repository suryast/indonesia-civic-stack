"""
Playwright browser helpers for AHU — includes stricter anti-detection measures.

AHU uses Cloudflare Bot Management which is more aggressive than the CF on
other portals. Camoufox is strongly recommended. Additional mitigations:
- Random human-like delays between actions
- Realistic mouse movement simulation
- Cloudflare Worker proxy routing (supply via proxy_url)
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)

_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 800},
    {"width": 1600, "height": 900},
]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Human-like delay range in milliseconds
_MIN_DELAY_MS = 800
_MAX_DELAY_MS = 2500


async def human_delay() -> None:
    """Random delay to simulate human browsing cadence."""
    delay = random.uniform(_MIN_DELAY_MS, _MAX_DELAY_MS) / 1000
    await asyncio.sleep(delay)


@asynccontextmanager
async def ahu_page(
    proxy_url: str | None = None,
    headless: bool = True,
) -> AsyncGenerator[Any, None]:
    """
    Context manager yielding a Playwright page configured for AHU.

    Uses Camoufox if available; falls back to Playwright with anti-detection flags.
    Routes through proxy_url (Cloudflare Worker or residential proxy).

    Args:
        proxy_url: Strongly recommended for AHU. Datacenter IPs are blocked.
        headless: Set False for local debugging/session verification.
    """
    viewport = random.choice(_VIEWPORTS)
    user_agent = random.choice(_USER_AGENTS)
    proxy = {"server": proxy_url} if proxy_url else None

    try:
        from camoufox.async_api import AsyncCamoufox  # type: ignore[import]

        async with AsyncCamoufox(headless=headless, proxy=proxy) as browser:
            page = await browser.new_page()
            await human_delay()
            yield page
            await page.close()

    except ImportError:
        logger.warning(
            "camoufox not installed. AHU Bot Management may block requests. "
            "Install with: pip install camoufox && python -m camoufox fetch"
        )
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                proxy=proxy,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            context = await browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="id-ID",
                timezone_id="Asia/Jakarta",
                extra_http_headers={
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['id-ID', 'id', 'en-US', 'en']});
                window.chrome = {runtime: {}};
            """)
            page = await context.new_page()
            try:
                await human_delay()
                yield page
            finally:
                await context.close()
                await browser.close()


async def wait_for_ahu_results(page: Any, selector: str, timeout: int = 20000) -> bool:
    """
    Wait for AHU results to render. Longer timeout than BPJPH due to CF challenge.

    Returns True if found within timeout, False otherwise.
    """
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception:
        # Check if we hit a CF challenge page
        content = await page.content()
        if "cloudflare" in content.lower() and "challenge" in content.lower():
            logger.error(
                "AHU: Cloudflare challenge detected. "
                "Ensure proxy_url points to a Cloudflare Worker or residential proxy."
            )
        return False
