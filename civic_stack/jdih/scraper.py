"""
JDIH scraper — Jaringan Dokumentasi dan Informasi Hukum (Indonesian Legal Database).

Source: peraturan.go.id (national legal database)
Method: Playwright scraping — site is JS-rendered, no public API
Auth:   None required

Regulation types:
  - uu: Undang-Undang (Laws)
  - pp: Peraturan Pemerintah (Government Regulations)
  - perpres: Peraturan Presiden (Presidential Regulations)
  - permen: Peraturan Menteri (Ministerial Regulations)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from playwright.async_api import async_playwright

from civic_stack.shared.http import RateLimiter
from civic_stack.shared.schema import (
    CivicStackResponse,
    RecordStatus,
    error_response,
    not_found_response,
)

from .normalizer import normalize_regulation

logger = logging.getLogger(__name__)

_BASE = "https://peraturan.go.id"
MODULE = "jdih"
SOURCE_URL = "https://peraturan.go.id"

_limiter = RateLimiter(rate=0.5)  # Conservative: 0.5 req/s for scraping


def _convert_proxy_url(proxy_url: str | None) -> str | None:
    """Convert socks5h:// to socks5:// for Chromium compatibility."""
    if not proxy_url:
        return None
    if proxy_url.startswith("socks5h://"):
        return proxy_url.replace("socks5h://", "socks5://")
    return proxy_url


async def _scrape_regulation_detail(
    regulation_id: str,
    *,
    proxy_url: str | None = None,
) -> dict[str, Any] | None:
    """Scrape single regulation detail page."""
    await _limiter.acquire()
    chromium_proxy = _convert_proxy_url(proxy_url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": chromium_proxy} if chromium_proxy else None,
            )
            page = await browser.new_page()
            await page.goto(f"{_BASE}/id/{regulation_id}", wait_until="networkidle", timeout=30000)

            # Extract regulation details from page
            title_el = await page.query_selector("h1.judul, h1")
            title = await title_el.inner_text() if title_el else None

            about_el = await page.query_selector(".tentang, .about")
            about = await about_el.inner_text() if about_el else None

            status_el = await page.query_selector(".status")
            status = await status_el.inner_text() if status_el else "ACTIVE"

            # Extract number and year from regulation_id or title
            number_match = re.search(r"no-(\d+)", regulation_id)
            year_match = re.search(r"tahun-(\d{4})", regulation_id)
            reg_type_match = re.match(r"([a-z]+)-", regulation_id)

            await browser.close()

            if not title:
                return None

            return {
                "regulation_id": regulation_id,
                "regulation_type": reg_type_match.group(1) if reg_type_match else "uu",
                "number": number_match.group(1) if number_match else None,
                "year": year_match.group(1) if year_match else None,
                "title": title.strip() if title else None,
                "status": status.strip().upper() if status else "ACTIVE",
                "about": about.strip() if about else None,
                "full_url": f"{_BASE}/id/{regulation_id}",
            }

    except Exception as exc:
        logger.warning("JDIH scraping error for %s: %s", regulation_id, exc)
        return None


async def _scrape_regulation_list(
    regulation_type: str = "uu",
    *,
    limit: int = 20,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Scrape list of regulations from listing page."""
    await _limiter.acquire()
    chromium_proxy = _convert_proxy_url(proxy_url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": chromium_proxy} if chromium_proxy else None,
            )
            page = await browser.new_page()
            await page.goto(f"{_BASE}/{regulation_type}", wait_until="networkidle", timeout=30000)

            # Extract regulation links
            links = await page.query_selector_all("a[href*='/id/']")
            results: list[dict[str, Any]] = []

            for link in links[:limit]:
                href = await link.get_attribute("href")
                if not href or "/id/" not in href:
                    continue

                text = await link.inner_text()
                regulation_id = href.split("/id/")[-1]

                # Parse from link text (format: "UU No. 1 Tahun 2023 tentang ...")
                number_match = re.search(r"No\.\s*(\d+)", text)
                year_match = re.search(r"Tahun\s*(\d{4})", text)

                results.append({
                    "regulation_id": regulation_id,
                    "regulation_type": regulation_type,
                    "number": number_match.group(1) if number_match else None,
                    "year": year_match.group(1) if year_match else None,
                    "title": text.strip(),
                    "status": "ACTIVE",
                    "about": None,
                    "full_url": f"{_BASE}{href}" if href.startswith("/") else href,
                })

                if len(results) >= limit:
                    break

            await browser.close()
            return results

    except Exception as exc:
        logger.warning("JDIH list scraping error for %s: %s", regulation_type, exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(regulation_id: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch a single regulation by ID (e.g. 'uu-no-1-tahun-2023')."""
    data = await _scrape_regulation_detail(regulation_id, proxy_url=proxy_url)

    if not data:
        return not_found_response(module=MODULE, query=regulation_id, source_url=SOURCE_URL)

    rec = normalize_regulation(data)
    return CivicStackResponse(
        result=rec,
        found=True,
        status=RecordStatus.ACTIVE if data.get("status") == "ACTIVE" else RecordStatus.EXPIRED,
        confidence=1.0,
        source_url=data.get("full_url", SOURCE_URL),
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
    )


async def search(
    keyword: str,
    *,
    proxy_url: str | None = None,
    regulation_type: str = "uu",
) -> list[CivicStackResponse]:
    """Search regulations by keyword. Returns recent matches."""
    # For now, fetch recent and filter by keyword (no search API available)
    regulations = await _scrape_regulation_list(
        regulation_type=regulation_type,
        limit=50,
        proxy_url=proxy_url,
    )

    keyword_lower = keyword.lower()
    results: list[CivicStackResponse] = []

    for reg in regulations:
        title = (reg.get("title") or "").lower()
        about = (reg.get("about") or "").lower()

        if keyword_lower in title or keyword_lower in about:
            rec = normalize_regulation(reg)
            confidence = 1.0 if keyword_lower in title else 0.8
            results.append(
                CivicStackResponse(
                    result=rec,
                    found=True,
                    status=RecordStatus.ACTIVE
                    if reg.get("status") == "ACTIVE"
                    else RecordStatus.EXPIRED,
                    confidence=confidence,
                    source_url=reg.get("full_url", SOURCE_URL),
                    fetched_at=__import__("datetime").datetime.utcnow(),
                    module=MODULE,
                )
            )

    return results


async def list_recent(
    regulation_type: str = "uu",
    *,
    limit: int = 20,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """List recent regulations of a specific type."""
    regulations = await _scrape_regulation_list(
        regulation_type=regulation_type,
        limit=limit,
        proxy_url=proxy_url,
    )

    results: list[CivicStackResponse] = []
    for reg in regulations:
        rec = normalize_regulation(reg)
        results.append(
            CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE
                if reg.get("status") == "ACTIVE"
                else RecordStatus.EXPIRED,
                confidence=1.0,
                source_url=reg.get("full_url", SOURCE_URL),
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )
        )

    return results
