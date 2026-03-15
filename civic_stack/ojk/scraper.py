"""
OJK licensed institution registry scraper.

OJK exposes several data endpoints:
- sikapiuangmu.ojk.go.id for investment alert / waspada investasi list
- Web pages for institution types on www.ojk.go.id
- NOTE: api.ojk.go.id and investor.ojk.go.id are DNS-dead as of March 2026

Strategy:
1. Try the OJK portal pages for institution data
2. Use sikapiuangmu.ojk.go.id for waspada/investor alert list
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from civic_stack.ojk.normalizer import normalize_institution, normalize_search_row
from civic_stack.shared.http import RateLimiter, civic_client, fetch_with_retry
from civic_stack.shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

# NOTE: api.ojk.go.id is DNS-dead (NXDOMAIN) as of March 2026.
# investor.ojk.go.id is also DNS-dead.
# Waspada list moved to sikapiuangmu.ojk.go.id/FrontEnd/AlertPortal/Negative
OJK_API_BASE = "https://api.ojk.go.id/v1"  # DEPRECATED — DNS dead
OJK_PORTAL_BASE = "https://www.ojk.go.id"
OJK_WASPADA_URL = "https://sikapiuangmu.ojk.go.id/FrontEnd/AlertPortal/Negative"

MODULE = "ojk"
_rate_limiter = RateLimiter(rate=0.5)  # OJK portal is slow — 30 req/min

# Institution type → OJK API category code
INSTITUTION_TYPE_MAP = {
    "bank_umum": "bank-umum",
    "bpr": "bpr",
    "fintech_p2p": "fintech-pendanaan",
    "fintech_payment": "fintech-pembayaran",
    "asuransi": "asuransi",
    "dana_pensiun": "dana-pensiun",
    "manajer_investasi": "manajer-investasi",
    "sekuritas": "perusahaan-efek",
}


async def fetch(
    name_or_id: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Look up a single OJK licensed institution by name or license number.

    Searches across all institution types. Returns the first matching record.
    """
    url = f"{OJK_API_BASE}/lembaga/pencarian"
    params = {"keyword": name_or_id, "limit": 1}

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                params=params,
                rate_limiter=_rate_limiter,
            )
        data = resp.json()
        institutions = data.get("data", data.get("result", []))

        if not institutions:
            # Fallback: scrape the portal search page
            return await _scrape_portal_search(name_or_id, proxy_url=proxy_url, debug=debug)

        return normalize_institution(institutions[0], source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("OJK fetch failed for '%s'", name_or_id)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search OJK licensed institution registry.

    Filters (optional):
        institution_type: One of INSTITUTION_TYPE_MAP keys
        status: "aktif" | "dicabut" | "dibekukan"
    """
    url = f"{OJK_API_BASE}/lembaga/pencarian"
    params: dict = {"keyword": keyword, "limit": 10}
    if filters:
        if filters.get("institution_type"):
            params["jenis"] = INSTITUTION_TYPE_MAP.get(
                filters["institution_type"], filters["institution_type"]
            )
        if filters.get("status"):
            params["status"] = filters["status"]

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                params=params,
                rate_limiter=_rate_limiter,
            )
        data = resp.json()
        institutions = data.get("data", data.get("result", []))

        if not institutions:
            return [not_found_response(MODULE, url)]

        return [normalize_institution(i, source_url=url) for i in institutions]

    except Exception as exc:
        logger.exception("OJK search failed for '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


async def check_waspada(entity_name: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """
    Check if an entity appears on OJK's Waspada Investasi (investment alert) list.

    Returns ACTIVE if the entity is on the alert list (i.e. unlicensed / flagged).
    Returns NOT_FOUND if clean.
    """
    url = OJK_WASPADA_URL
    params = {"keyword": entity_name, "draw": 1, "start": 0, "length": 10}

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                params=params,
                rate_limiter=_rate_limiter,
            )
        data = resp.json()
        records = data.get("data", [])

        if not records:
            return not_found_response(MODULE, url)

        first = records[0]
        return normalize_institution(
            {**first, "_waspada": True},
            source_url=url,
        )

    except Exception as exc:
        logger.exception("OJK waspada check failed for '%s'", entity_name)
        return error_response(MODULE, url, detail=str(exc))


async def _scrape_portal_search(
    keyword: str,
    *,
    proxy_url: str | None = None,
    debug: bool = False,
) -> CivicStackResponse:
    """Fallback: scrape the OJK portal search page when API returns nothing."""
    url = f"{OJK_PORTAL_BASE}/id/kanal/perbankan/data-dan-statistik/Pages/Direktori.aspx"
    params = {"SearchText": keyword}

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                params=params,
                rate_limiter=_rate_limiter,
            )
        soup = BeautifulSoup(resp.text, "html.parser")
        rows = _extract_table_rows(soup)
        if not rows:
            return not_found_response(MODULE, url)
        return normalize_search_row(rows[0], source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("OJK portal scrape fallback failed for '%s'", keyword)
        return error_response(MODULE, url, detail=str(exc))


def _extract_table_rows(soup: BeautifulSoup) -> list[dict]:
    rows: list[dict] = []
    table = soup.find("table", {"class": lambda c: c and "table" in c})
    if not table:
        return rows
    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if cells:
            rows.append(
                {
                    headers[i]: cells[i].get_text(strip=True)
                    for i in range(min(len(headers), len(cells)))
                }
            )
    return rows
