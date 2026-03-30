"""
BPOM scraper — cekbpom.pom.go.id

The portal exposes product registrations (food, drug, cosmetics,
traditional medicine). As of 2026-03, the site uses Laravel with
DataTables server-side rendering (POST + CSRF token).

Rate limit: ~10 req/min observed. Enforced via RateLimiter.
"""

from __future__ import annotations

import logging
from urllib.parse import quote, unquote

from modules.bpom.normalizer import normalize_search_row
from shared.http import RateLimiter, civic_client, fetch_with_retry
from shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

BPOM_BASE = "https://cekbpom.pom.go.id"
# DataTables server-side endpoint (POST, requires CSRF)
BPOM_DT_URL = f"{BPOM_BASE}/produk-dt/all"
# Page to get CSRF cookie from
BPOM_SEARCH_PAGE = f"{BPOM_BASE}/all-produk"
# Detail page (new format)
BPOM_DETAIL_URL = f"{BPOM_BASE}/produk"

# ~10 req/min = ~0.167 req/s; use 0.15 for safety margin
_rate_limiter = RateLimiter(rate=0.15)

MODULE = "bpom"

# DataTables column mapping (from site JS)
_DT_FIELD_MAP = {
    "PRODUCT_REGISTER": "registration_no",
    "PRODUCT_NAME": "product_name",
    "APPLICATION": "category",
    "CLASS": "class",
    "PRODUCT_ID": "product_id",
    "APPLICATION_ID": "application_id",
    "ID": "bpom_id",
}


async def _get_csrf_session(
    proxy_url: str | None = None,
) -> tuple[str, dict[str, str]]:
    """Get XSRF token and session cookies from BPOM search page."""
    async with civic_client(proxy_url=proxy_url) as client:
        resp = await fetch_with_retry(
            client,
            "GET",
            BPOM_SEARCH_PAGE,
            rate_limiter=_rate_limiter,
        )
        cookies = {}
        for name in ("XSRF-TOKEN", "webreg_session"):
            val = resp.cookies.get(name)
            if val:
                cookies[name] = val

        xsrf = unquote(cookies.get("XSRF-TOKEN", ""))
        return xsrf, cookies


async def fetch(
    registration_no: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a single BPOM product by registration number.

    Uses DataTables search with an exact registration number query.
    Falls back to not_found if no match.
    """
    clean_no = registration_no.strip()

    try:
        results = await search(clean_no, proxy_url=proxy_url)
        # Find exact match
        for r in results:
            if r.found and r.result:
                reg = r.result.get("registration_no", "")
                if reg.replace(" ", "").upper() == clean_no.replace(" ", "").upper():
                    return r

        # No exact match — return first result or not_found
        if results and results[0].found:
            return results[0]
        return not_found_response(MODULE, f"{BPOM_DT_URL}?q={clean_no}")

    except Exception as exc:
        logger.exception("BPOM fetch failed for %s", registration_no)
        return error_response(MODULE, BPOM_DT_URL, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,  # noqa: ARG001 — reserved for future filters
    *,
    proxy_url: str | None = None,
    length: int = 20,
) -> list[CivicStackResponse]:
    """
    Search BPOM product registry by product name, registration number, or company.

    Uses the DataTables server-side endpoint (POST with CSRF).

    Args:
        keyword: Search term.
        filters: Reserved for future use.
        proxy_url: Optional proxy URL.
        length: Number of results to fetch (max per page, default 20).

    Returns:
        List of CivicStackResponse objects.
    """
    source_url = f"{BPOM_SEARCH_PAGE}?q={quote(keyword)}"

    try:
        xsrf, cookies = await _get_csrf_session(proxy_url=proxy_url)
        if not xsrf:
            logger.warning("No XSRF token from BPOM — CSRF may fail")

        # DataTables POST params
        form_data = {
            "draw": "1",
            "start": "0",
            "length": str(length),
            "search[value]": keyword,
            "search[regex]": "false",
        }

        async with civic_client(proxy_url=proxy_url) as client:
            response = await fetch_with_retry(
                client,
                "POST",
                BPOM_DT_URL,
                rate_limiter=_rate_limiter,
                data=form_data,
                headers={
                    "X-XSRF-TOKEN": xsrf,
                    "Referer": source_url,
                },
                cookies=cookies,
            )

        data = response.json()
        rows = data.get("data", [])

        if not rows:
            return [not_found_response(MODULE, source_url)]

        results = []
        for row in rows:
            normalized = _normalize_dt_row(row)
            results.append(normalize_search_row(normalized, source_url=source_url))

        logger.info(
            "BPOM search '%s': %d/%d results (total %s)",
            keyword,
            len(results),
            data.get("recordsFiltered", "?"),
            data.get("recordsTotal", "?"),
        )
        return results

    except Exception as exc:
        logger.exception("BPOM search failed for keyword '%s'", keyword)
        return [error_response(MODULE, source_url, detail=str(exc))]


def _normalize_dt_row(row: dict) -> dict[str, str]:
    """Convert a DataTables JSON row to normalized field dict."""
    normalized: dict[str, str] = {}
    for dt_key, norm_key in _DT_FIELD_MAP.items():
        val = row.get(dt_key)
        if val is not None:
            normalized[norm_key] = str(val).strip()

    # Map remaining fields that may appear
    for key in ("REGISTRAR", "REGISTRAR_NPWP", "MANUFACTURER", "BRAND"):
        val = row.get(key)
        if val:
            normalized[key.lower()] = str(val).strip()

    return normalized
