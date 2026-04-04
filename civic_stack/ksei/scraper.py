"""
KSEI scraper — PT Kustodian Sentral Efek Indonesia (Securities Depository).

Source: web.ksei.co.id (old Rails app with securities data)
Method: HTTP scraping — server-rendered HTML
Auth:   None required

Key endpoints:
  - Securities master: /services/registered-securities/shares
  - Statistics PDFs: /publications/Data_Statistik_KSEI
  - Holding data: /archive_download/holding_composition
"""

from __future__ import annotations

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from civic_stack.shared.http import RateLimiter, civic_client, fetch_with_retry
from civic_stack.shared.schema import (
    CivicStackResponse,
    RecordStatus,
    error_response,
    not_found_response,
)

from .normalizer import normalize_security, normalize_statistics_link

logger = logging.getLogger(__name__)

_BASE = "https://web.ksei.co.id"
MODULE = "ksei"
SOURCE_URL = "https://web.ksei.co.id"

_limiter = RateLimiter(rate=1.0)  # 1 req/s for HTML scraping


async def _fetch_securities_page(
    *,
    page: int = 1,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch securities listing page and parse table rows."""
    async with civic_client(proxy_url=proxy_url) as client:
        await _limiter.acquire()
        url = f"{_BASE}/services/registered-securities/shares"
        params = {"setLocale": "id-ID", "page": str(page)}

        try:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                params=params,
                rate_limiter=_limiter,
            )
            html = resp.text
        except Exception as exc:
            logger.warning("KSEI securities page fetch error: %s", exc)
            return []

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    results: list[dict[str, Any]] = []
    rows = table.find_all("tr")[1:]  # Skip header row

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        code = cells[0].get_text(strip=True)
        name = cells[1].get_text(strip=True)
        sec_type = cells[2].get_text(strip=True)
        issuer = cells[3].get_text(strip=True)

        results.append({
            "security_code": code,
            "security_name": name,
            "security_type": sec_type,
            "issuer": issuer,
            "status": "ACTIVE",
        })

    return results


async def _fetch_statistics_page(*, proxy_url: str | None = None) -> list[dict[str, Any]]:
    """Fetch statistics publications page and extract PDF links."""
    async with civic_client(proxy_url=proxy_url) as client:
        await _limiter.acquire()
        url = f"{_BASE}/publications/Data_Statistik_KSEI"

        try:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_limiter,
            )
            html = resp.text
        except Exception as exc:
            logger.warning("KSEI statistics page fetch error: %s", exc)
            return []

    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=re.compile(r"Statistik_Publik.*\.pdf"))

    results: list[dict[str, Any]] = []
    for link in links:
        href = link.get("href", "")
        if not href:
            continue

        # Extract month and year from filename
        # Format: Statistik_Publik_January_2026.pdf or Statistik_Publik_Januari_2026.pdf
        match = re.search(r"Statistik_Publik_(\w+)_(\d{4})\.pdf", href)
        if match:
            month = match.group(1)
            year = match.group(2)
        else:
            month = None
            year = None

        full_url = href if href.startswith("http") else f"{_BASE}{href}"

        results.append({
            "period": f"{month} {year}" if month and year else None,
            "month": month,
            "year": year,
            "download_url": full_url,
        })

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(security_code: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch a single security by code."""
    # Fetch first page and search
    securities = await _fetch_securities_page(page=1, proxy_url=proxy_url)

    for sec in securities:
        if sec.get("security_code") == security_code:
            rec = normalize_security(sec)
            return CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=1.0,
                source_url=f"{SOURCE_URL}/services/registered-securities/shares",
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )

    return not_found_response(module=MODULE, query=security_code, source_url=SOURCE_URL)


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search securities by keyword (code or name)."""
    securities = await _fetch_securities_page(page=1, proxy_url=proxy_url)

    keyword_lower = keyword.lower()
    results: list[CivicStackResponse] = []

    for sec in securities:
        code = (sec.get("security_code") or "").lower()
        name = (sec.get("security_name") or "").lower()

        if keyword_lower in code or keyword_lower in name:
            rec = normalize_security(sec)
            confidence = 1.0 if keyword_lower == code else 0.9 if keyword_lower in code else 0.8
            results.append(
                CivicStackResponse(
                    result=rec,
                    found=True,
                    status=RecordStatus.ACTIVE,
                    confidence=confidence,
                    source_url=f"{SOURCE_URL}/services/registered-securities/shares",
                    fetched_at=__import__("datetime").datetime.utcnow(),
                    module=MODULE,
                )
            )

    return results


async def get_statistics_links(*, proxy_url: str | None = None) -> list[dict[str, Any]]:
    """List available monthly statistics PDF URLs."""
    stats = await _fetch_statistics_page(proxy_url=proxy_url)
    return [normalize_statistics_link(s) for s in stats]


async def get_latest_statistics_url(*, proxy_url: str | None = None) -> str | None:
    """Get URL of the most recent statistics PDF."""
    stats = await _fetch_statistics_page(proxy_url=proxy_url)
    if not stats:
        return None

    # Sort by year then month (newest first)
    # Simple heuristic: just take first one (assuming page lists newest first)
    latest = stats[0] if stats else None
    return latest.get("download_url") if latest else None
