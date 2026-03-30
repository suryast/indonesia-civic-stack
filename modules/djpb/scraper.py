"""
DJPB scraper — djpb.kemenkeu.go.id (Budget Data)

🇮🇩 Requires Indonesian proxy — set PROXY_URL env var

DJPB (Direktorat Jenderal Perbendaharaan) publishes APBN budget execution data,
fiscal reports, and treasury statistics via HTML pages.
This module uses httpx + BeautifulSoup to fetch and parse results.

Rate limit: ~10 req/min observed. Enforced via RateLimiter.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from civic_stack.djpb.normalizer import normalize_search_row
from civic_stack.shared.http import RateLimiter, civic_client, fetch_with_retry
from civic_stack.shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

DJPB_BASE = "https://djpb.kemenkeu.go.id"
# Budget data typically under /portal/data or /apbn paths
DJPB_DATA_URL = f"{DJPB_BASE}/portal/data-apbn"

# ~10 req/min = ~0.167 req/s; use 0.15 for safety margin
_rate_limiter = RateLimiter(rate=0.15)

MODULE = "djpb"


async def fetch(
    report_id: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a single DJPB budget report by report ID.

    Args:
        report_id: Report identifier or title keyword
        debug: If True, include raw scraped HTML in the response.
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        CivicStackResponse with DJPB report details, or NOT_FOUND / ERROR.
    """
    # Try to find the report via search
    results = await search(report_id, proxy_url=proxy_url)

    if not results or not results[0].found:
        return not_found_response(MODULE, f"{DJPB_DATA_URL}?q={quote(report_id)}")

    # Return first match with debug flag applied
    result = results[0]
    if not debug:
        result.raw = None
    return result


async def search(
    keyword: str,
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search DJPB budget data and reports by keyword.

    Args:
        keyword: Search term (report title, fiscal year, or category).
        proxy_url: Optional proxy URL for IP rotation.

    Returns:
        List of CivicStackResponse objects (may be empty, never raises on not-found).
    """
    # Try the data page first
    url = DJPB_DATA_URL

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            response = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_rate_limiter,
            )
        soup = BeautifulSoup(response.text, "html.parser")
        rows = _extract_budget_data(soup, keyword)

        if not rows:
            return [not_found_response(MODULE, url)]

        return [normalize_search_row(row, source_url=url) for row in rows]

    except Exception as exc:
        logger.exception("DJPB search failed for keyword '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


def _extract_budget_data(soup: BeautifulSoup, keyword: str) -> list[dict]:
    """Extract budget data entries from DJPB pages, filtering by keyword."""
    rows: list[dict] = []
    keyword_lower = keyword.lower()

    # Look for tables with budget data
    tables = soup.find_all("table")
    for table in tables:
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
            row_text = ""

            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                row_text += text.lower() + " "

                if i < len(headers):
                    row[headers[i]] = text
                else:
                    row[f"column_{i}"] = text

                # Extract download links
                link = cell.find("a", href=True)
                if link:
                    href = link["href"]
                    if not href.startswith("http"):
                        href = f"{DJPB_BASE}{href}"
                    row["download_url"] = href

            # Filter by keyword
            if keyword_lower in row_text and row:
                rows.append(row)

    # Alternative: Look for budget report cards/sections
    if not rows:
        report_sections = soup.find_all(
            ["div", "section"],
            {"class": lambda c: c and ("report" in c or "data" in c or "apbn" in c)},
        )
        for section in report_sections:
            section_text = section.get_text(strip=True).lower()

            if keyword_lower in section_text:
                row: dict[str, str] = {}

                # Extract title
                title = section.find(["h2", "h3", "h4", "strong"])
                if title:
                    row["title"] = title.get_text(strip=True)

                # Extract fiscal year
                year_match = re.search(r"20\d{2}", section_text)
                if year_match:
                    row["fiscal_year"] = year_match.group(0)

                # Extract amount/value
                amount = section.find(
                    ["span", "p"], {"class": lambda c: c and ("amount" in c or "value" in c)}
                )
                if amount:
                    row["amount"] = amount.get_text(strip=True)

                # Extract link
                link = section.find("a", href=True)
                if link:
                    href = link["href"]
                    if not href.startswith("http"):
                        href = f"{DJPB_BASE}{href}"
                    row["download_url"] = href

                if row:
                    rows.append(row)

    return rows
