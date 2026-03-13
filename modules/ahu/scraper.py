"""
AHU company registry scraper — ahu.go.id (Kemenkumham)

JS-rendered portal requiring Playwright. Datacenter IPs are actively blocked;
route through Cloudflare Workers or a residential proxy pool via proxy_url.

Risk: AHU uses Cloudflare Bot Management. Camoufox fingerprint randomization
is mandatory; do not run without it in production.

Safe rate: ~3 req/min. Lower than BPJPH due to CF Bot Management sensitivity.
"""

from __future__ import annotations

import logging

from modules.ahu.browser import ahu_page, wait_for_ahu_results
from modules.ahu.normalizer import normalize_company_page, normalize_search_results
from shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

AHU_BASE = "https://ahu.go.id"
AHU_COMPANY_SEARCH_URL = f"{AHU_BASE}/pencarian/perseroan-terbatas"

MODULE = "ahu"

# Selectors for the AHU React portal
_RESULT_SELECTOR = "table.table, .company-result, [class*='result-table']"
_NO_RESULT_SELECTOR = ".alert-warning, .no-data, [class*='not-found']"
_DETAIL_SELECTOR = ".company-detail, [class*='company-info']"


async def fetch(
    query: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a company in the AHU registry by name or registration number.

    Args:
        query: Company name (full or partial) or AHU registration number.
        debug: If True, include raw scraped data in response.
        proxy_url: Required for datacenter IPs — use Cloudflare Worker URL.

    Returns:
        CivicStackResponse with company details, or NOT_FOUND / ERROR.

    Warning:
        AHU blocks datacenter IPs. Always supply proxy_url in production.
        See modules/ahu/README.md for Cloudflare Worker setup.
    """
    url = AHU_COMPANY_SEARCH_URL

    if not proxy_url:
        logger.warning(
            "AHU scraper called without proxy_url — datacenter IPs will be blocked. "
            "Supply a Cloudflare Worker URL via proxy_url."
        )

    try:
        async with ahu_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")

            search_input = await _find_search_input(page)
            if search_input is None:
                return error_response(MODULE, url, detail="Could not locate search input on AHU page")

            await search_input.fill(query)
            await search_input.press("Enter")

            found = await wait_for_ahu_results(page, _RESULT_SELECTOR)
            if not found:
                no_result = await page.query_selector(_NO_RESULT_SELECTOR)
                if no_result:
                    return not_found_response(MODULE, url)
                return error_response(MODULE, url, detail="AHU page did not render results")

            # If multiple results, click the first one to get full detail
            await _click_first_result(page)
            await page.wait_for_load_state("networkidle")

            html = await page.content()

        return normalize_company_page(html, query=query, source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("AHU fetch failed for query '%s'", query)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,  # noqa: ARG001
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search AHU company registry by company name keyword.

    Returns up to 10 results. Never raises on not-found — returns empty list.
    """
    url = AHU_COMPANY_SEARCH_URL

    if not proxy_url:
        logger.warning("AHU search called without proxy_url — datacenter IPs will be blocked.")

    try:
        async with ahu_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")

            search_input = await _find_search_input(page)
            if search_input is None:
                return [error_response(MODULE, url, detail="Could not locate search input")]

            await search_input.fill(keyword)
            await search_input.press("Enter")

            found = await wait_for_ahu_results(page, _RESULT_SELECTOR)
            if not found:
                return [not_found_response(MODULE, url)]

            html = await page.content()

        return normalize_search_results(html, source_url=url)

    except Exception as exc:
        logger.exception("AHU search failed for keyword '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


# ── Private helpers ───────────────────────────────────────────────────────────


async def _find_search_input(page: object) -> object | None:
    """Try several selectors to find the AHU search input."""
    selectors = [
        "input[placeholder*='nama']",
        "input[placeholder*='perusahaan']",
        "input[placeholder*='pencarian']",
        "input[placeholder*='cari']",
        "input[type='search']",
        "input[type='text']:first-of-type",
        "#searchInput",
        ".search-input input",
    ]
    for sel in selectors:
        el = await page.query_selector(sel)  # type: ignore[attr-defined]
        if el:
            return el
    return None


async def _click_first_result(page: object) -> None:
    """Click the first row in the results table to navigate to detail page."""
    try:
        first_row = await page.query_selector("table tbody tr:first-child")  # type: ignore[attr-defined]
        if first_row:
            await first_row.click()
    except Exception:
        pass  # If clicking fails, the caller will parse whatever is on the page
