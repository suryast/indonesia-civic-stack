"""
OSS RBA NIB scraper — oss.go.id public search tier.

Public tier: company name → NIB number → basic status.
No login required for this data tier.

Note: OSS uses a React SPA — Playwright is required.
The portal is generally more stable than AHU/BPJPH for IP blocking.
"""

from __future__ import annotations

import logging

from civic_stack.bpjph.browser import new_page, wait_for_results
from civic_stack.oss_nib.normalizer import normalize_nib_page, normalize_search_results
from civic_stack.shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

OSS_BASE = "https://oss.go.id"
OSS_SEARCH_URL = f"{OSS_BASE}/informasi/pencarian-nib"

MODULE = "oss_nib"

_RESULTS_SELECTOR = "table.MuiTable-root, .nib-result, [class*='result']"
_NO_RESULT_SELECTOR = ".no-data, [class*='empty-state'], .alert"


async def fetch(
    query: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a business by NIB number or company name.

    Args:
        query: NIB number (13-digit) or company name.
        debug: Include raw scraped data in response.
        proxy_url: Optional proxy URL.
    """
    url = OSS_SEARCH_URL

    try:
        async with new_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")
            search_input = await _find_search_input(page)
            if not search_input:
                return error_response(MODULE, url, detail="Search input not found on OSS page")

            await search_input.fill(query)
            await search_input.press("Enter")

            found = await wait_for_results(page, _RESULTS_SELECTOR)
            if not found:
                no_result = await page.query_selector(_NO_RESULT_SELECTOR)
                if no_result:
                    return not_found_response(MODULE, url)
                return error_response(MODULE, url, detail="OSS page did not render results")

            # Click first result to get detail view
            first_row = await page.query_selector("table tbody tr:first-child, .nib-result-item")
            if first_row:
                await first_row.click()
                await page.wait_for_load_state("networkidle")

            html = await page.content()

        return normalize_nib_page(html, query=query, source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("OSS-NIB fetch failed for '%s'", query)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,  # noqa: ARG001
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """Search OSS by company name keyword."""
    url = OSS_SEARCH_URL

    try:
        async with new_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")
            search_input = await _find_search_input(page)
            if not search_input:
                return [error_response(MODULE, url, detail="Search input not found")]

            await search_input.fill(keyword)
            await search_input.press("Enter")

            found = await wait_for_results(page, _RESULTS_SELECTOR)
            if not found:
                return [not_found_response(MODULE, url)]

            html = await page.content()

        return normalize_search_results(html, source_url=url)

    except Exception as exc:
        logger.exception("OSS-NIB search failed for '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


async def _find_search_input(page: object) -> object | None:
    for sel in [
        "input[placeholder*='NIB']",
        "input[placeholder*='nama']",
        "input[placeholder*='perusahaan']",
        "input[type='search']",
        "input[type='text']:first-of-type",
    ]:
        el = await page.query_selector(sel)  # type: ignore[attr-defined]
        if el:
            return el
    return None
