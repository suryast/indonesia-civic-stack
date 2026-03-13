"""
BPJPH SiHalal scraper — sertifikasi.halal.go.id

JS-rendered portal. Uses Playwright to:
1. Navigate to the search page
2. Fill the search form with cert number or product name
3. Wait for JS-rendered results
4. Parse the resulting HTML

Includes a cross_ref_bpom() helper that runs a BPOM lookup for the
same product to detect lapsed BPOM registrations alongside valid halal certs.
"""

from __future__ import annotations

import logging

from modules.bpjph.browser import new_page, wait_for_results
from modules.bpjph.normalizer import normalize_cert_page, normalize_search_results
from shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

BPJPH_BASE = "https://sertifikasi.halal.go.id"
BPJPH_SEARCH_URL = f"{BPJPH_BASE}/sertifikat/publik"

MODULE = "bpjph"

# CSS selectors for the SiHalal portal (React-rendered)
_RESULTS_TABLE_SELECTOR = "table.MuiTable-root, table[class*='table'], .certificate-result"
_DETAIL_SELECTOR = ".certificate-detail, .sertifikat-detail, [class*='detail']"
_NO_RESULT_SELECTOR = ".no-data, [class*='empty'], .alert-warning"


async def fetch(
    cert_no: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a BPJPH halal certificate by certificate number.

    Args:
        cert_no: Certificate number, e.g. "BPJPH-00001-2023" or "ID-2023-000001".
        debug: If True, include raw scraped data in response.
        proxy_url: Optional proxy URL for IP rotation.
    """
    url = BPJPH_SEARCH_URL

    try:
        async with new_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")

            # Try to find and fill the certificate number search input
            search_input = await _find_search_input(page)
            if search_input is None:
                return error_response(MODULE, url, detail="Could not locate search input on page")

            await search_input.fill(cert_no)
            await search_input.press("Enter")

            found = await wait_for_results(page, _RESULTS_TABLE_SELECTOR)
            if not found:
                # Check for explicit no-results message
                no_result = await page.query_selector(_NO_RESULT_SELECTOR)
                if no_result:
                    return not_found_response(MODULE, url)
                return error_response(MODULE, url, detail="Page did not render results in time")

            html = await page.content()

        return normalize_cert_page(html, cert_no=cert_no, source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("BPJPH fetch failed for cert %s", cert_no)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,  # noqa: ARG001
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search SiHalal by product name or company name.

    Returns up to 10 results. Never raises on not-found — returns empty list.
    """
    url = BPJPH_SEARCH_URL

    try:
        async with new_page(proxy_url=proxy_url) as page:
            await page.goto(url, wait_until="networkidle")

            search_input = await _find_search_input(page)
            if search_input is None:
                return [error_response(MODULE, url, detail="Could not locate search input")]

            await search_input.fill(keyword)
            await search_input.press("Enter")

            found = await wait_for_results(page, _RESULTS_TABLE_SELECTOR)
            if not found:
                return [not_found_response(MODULE, url)]

            html = await page.content()

        return normalize_search_results(html, source_url=url)

    except Exception as exc:
        logger.exception("BPJPH search failed for keyword '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


async def cross_ref_bpom(
    product_name: str,
    *,
    proxy_url: str | None = None,
) -> dict:
    """
    Cross-reference a product between BPJPH (halal cert) and BPOM (product registration).

    Runs both lookups in parallel and returns a combined dict flagging any mismatch,
    e.g. where BPOM registration is ACTIVE but halal cert is EXPIRED.

    Returns:
        {
            "product_name": str,
            "bpjph": CivicStackResponse (dict),
            "bpom": CivicStackResponse (dict) | None,
            "mismatch": bool,
            "mismatch_detail": str | None,
        }
    """
    import asyncio

    from modules.bpom.scraper import search as bpom_search

    bpjph_results, bpom_results = await asyncio.gather(
        search(product_name, proxy_url=proxy_url),
        bpom_search(product_name, proxy_url=proxy_url),
    )

    bpjph_resp = bpjph_results[0] if bpjph_results else None
    bpom_resp = bpom_results[0] if bpom_results else None

    mismatch = False
    mismatch_detail = None

    if bpjph_resp and bpom_resp:
        bpjph_active = bpjph_resp.status == "ACTIVE"
        bpom_active = bpom_resp.status == "ACTIVE"
        if bpom_active and not bpjph_active:
            mismatch = True
            mismatch_detail = (
                f"BPOM registration is {bpom_resp.status} but halal cert is {bpjph_resp.status}"
            )
        elif bpjph_active and not bpom_active:
            mismatch = True
            mismatch_detail = (
                f"Halal cert is {bpjph_resp.status} but BPOM registration is {bpom_resp.status}"
            )

    return {
        "product_name": product_name,
        "bpjph": bpjph_resp.model_dump(mode="json") if bpjph_resp else None,
        "bpom": bpom_resp.model_dump(mode="json") if bpom_resp else None,
        "mismatch": mismatch,
        "mismatch_detail": mismatch_detail,
    }


# ── Private helpers ───────────────────────────────────────────────────────────


async def _find_search_input(page: object) -> object | None:
    """Try several CSS selectors to locate the search input field."""
    selectors = [
        "input[placeholder*='nomor']",
        "input[placeholder*='sertifikat']",
        "input[placeholder*='cari']",
        "input[placeholder*='search']",
        "input[type='search']",
        "input[type='text']:first-of-type",
    ]
    for sel in selectors:
        el = await page.query_selector(sel)  # type: ignore[attr-defined]
        if el:
            return el
    return None
