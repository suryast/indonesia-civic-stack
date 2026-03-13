"""
BPOM scraper — cekbpom.pom.go.id

The portal exposes product registrations (food, drug, cosmetics,
traditional medicine) via a form-based HTML interface. This module
uses httpx + BeautifulSoup to fetch and parse results.

Rate limit: ~10 req/min observed. Enforced via RateLimiter.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from bs4 import BeautifulSoup

from modules.bpom.normalizer import normalize_detail, normalize_search_row
from shared.http import RateLimiter, civic_client, fetch_with_retry
from shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

BPOM_BASE = "https://cekbpom.pom.go.id"
# Direct product lookup by registration number
BPOM_DETAIL_URL = f"{BPOM_BASE}/index.php/home/produk/0"
# Search by product name — returns a table of matches
BPOM_SEARCH_URL = f"{BPOM_BASE}/index.php/home/produk/1"

# ~10 req/min = ~0.167 req/s; use 0.15 for safety margin
_rate_limiter = RateLimiter(rate=0.15)

MODULE = "bpom"


async def fetch(
    registration_no: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a single BPOM product by registration number.

    Args:
        registration_no: BPOM registration number, e.g. "BPOM MD 123456789012"
                         or short form "MD 123456789012".
        debug: If True, include raw scraped HTML in the response.
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        CivicStackResponse with BPOM product details, or NOT_FOUND / ERROR.
    """
    clean_no = registration_no.strip()
    url = f"{BPOM_DETAIL_URL}/{quote(clean_no)}/10/1/0"

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            response = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_rate_limiter,
            )
        soup = BeautifulSoup(response.text, "html.parser")
        return normalize_detail(soup, registration_no=clean_no, source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("BPOM fetch failed for %s", registration_no)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,  # noqa: ARG001 — reserved for future filters
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search BPOM product registry by product name or company name.

    Args:
        keyword: Search term (product name or partial name).
        filters: Reserved for future use (category filter, etc.).
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        List of CivicStackResponse objects (may be empty, never raises on not-found).
    """
    url = f"{BPOM_SEARCH_URL}/{quote(keyword)}/10/1/1"

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            response = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_rate_limiter,
            )
        soup = BeautifulSoup(response.text, "html.parser")
        rows = _extract_search_rows(soup)

        if not rows:
            return [not_found_response(MODULE, url)]

        return [normalize_search_row(row, source_url=url) for row in rows]

    except Exception as exc:
        logger.exception("BPOM search failed for keyword '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


def _extract_search_rows(soup: BeautifulSoup) -> list[dict]:
    """Extract rows from a BPOM search results table."""
    rows: list[dict] = []
    table = soup.find("table", {"class": lambda c: c and "table" in c})
    if not table:
        return rows

    headers: list[str] = []
    for th in table.find_all("th"):
        headers.append(th.get_text(strip=True).lower())

    for tr in table.find_all("tr")[1:]:  # skip header row
        cells = tr.find_all("td")
        if not cells:
            continue
        row = {
            headers[i]: cells[i].get_text(strip=True) for i in range(min(len(headers), len(cells)))
        }
        rows.append(row)

    return rows
