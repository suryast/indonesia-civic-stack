"""
JDIH scraper — jdih.bpk.go.id (BPK Legal Documents)

🇮🇩 Requires Indonesian proxy — set PROXY_URL env var

The portal provides access to legal documents (Peraturan, Keputusan, Monografi)
from BPK (Badan Pemeriksa Keuangan) via a form-based HTML interface.
This module uses httpx + BeautifulSoup to fetch and parse results.

Rate limit: ~10 req/min observed. Enforced via RateLimiter.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from bs4 import BeautifulSoup

from civic_stack.jdih.normalizer import normalize_detail, normalize_search_row
from civic_stack.shared.http import RateLimiter, civic_client, fetch_with_retry
from civic_stack.shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

JDIH_BASE = "https://jdih.bpk.go.id"
JDIH_SEARCH_URL = f"{JDIH_BASE}/Dokumen/Search"

# Category codes: 1=Peraturan BPK, 2=Keputusan BPK, 5=Monografi, etc.
CATEGORY_MAP = {
    "peraturan": 1,
    "keputusan": 2,
    "monografi": 5,
}

# ~10 req/min = ~0.167 req/s; use 0.15 for safety margin
_rate_limiter = RateLimiter(rate=0.15)

MODULE = "jdih"


async def fetch(
    doc_id: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a single JDIH document by document ID or regulation number.

    Args:
        doc_id: Document ID or regulation number (e.g. "Nomor 4 Tahun 2025")
        debug: If True, include raw scraped HTML in the response.
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        CivicStackResponse with JDIH document details, or NOT_FOUND / ERROR.
    """
    # Try to find the document via search
    results = await search(doc_id, proxy_url=proxy_url)
    
    if not results or not results[0].found:
        return not_found_response(MODULE, f"{JDIH_SEARCH_URL}?keyword={quote(doc_id)}")
    
    # Return first match with debug flag applied
    result = results[0]
    if not debug:
        result.raw = None
    return result


async def search(
    keyword: str,
    category: int = 1,
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search JDIH legal documents by keyword.

    Args:
        keyword: Search term (regulation title, number, or content keyword).
        category: Document category (1=Peraturan, 2=Keputusan, 5=Monografi). Default: 1.
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        List of CivicStackResponse objects (may be empty, never raises on not-found).
    """
    url = f"{JDIH_SEARCH_URL}?cari={category}&keyword={quote(keyword)}"

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
        logger.exception("JDIH search failed for keyword '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


def _extract_search_rows(soup: BeautifulSoup) -> list[dict]:
    """Extract document entries from JDIH search results."""
    rows: list[dict] = []
    
    # JDIH results are typically in a table or list structure
    # Look for common table patterns
    table = soup.find("table", {"class": lambda c: c and ("table" in c or "result" in c)})
    if table:
        headers: list[str] = []
        header_row = table.find("tr")
        if header_row:
            for th in header_row.find_all(["th", "td"]):
                headers.append(th.get_text(strip=True).lower())

        for tr in table.find_all("tr")[1:]:  # skip header row
            cells = tr.find_all("td")
            if not cells:
                continue
            
            row: dict[str, str] = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row[headers[i]] = cell.get_text(strip=True)
                
                # Extract PDF link if present
                link = cell.find("a", href=True)
                if link and link["href"].endswith(".pdf"):
                    row["pdf_url"] = link["href"] if link["href"].startswith("http") else f"{JDIH_BASE}{link['href']}"
            
            if row:
                rows.append(row)
    
    # Alternative: Look for result divs/cards
    if not rows:
        result_items = soup.find_all("div", {"class": lambda c: c and "result" in c})
        for item in result_items:
            row: dict[str, str] = {}
            
            # Extract title
            title = item.find(["h3", "h4", "strong"])
            if title:
                row["title"] = title.get_text(strip=True)
            
            # Extract link
            link = item.find("a", href=True)
            if link:
                row["pdf_url"] = link["href"] if link["href"].startswith("http") else f"{JDIH_BASE}{link['href']}"
            
            if row:
                rows.append(row)

    return rows
