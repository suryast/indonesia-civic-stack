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
OJK_PORTAL_BASE = "https://www.ojk.go.id"
OJK_WASPADA_URL = "https://sikapiuangmu.ojk.go.id/FrontEnd/AlertPortal/Negative"
OJK_WASPADA_LIST_URL = "https://emiten.ojk.go.id/Satgas/AlertPortal/IndexAlertPortal"

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
    # api.ojk.go.id is DNS-dead since Feb 2026 — go straight to portal scraping
    try:
        return await _scrape_portal_search(name_or_id, proxy_url=proxy_url, debug=debug)

    except Exception as exc:
        logger.exception("OJK fetch failed for '%s'", name_or_id)
        return error_response(MODULE, OJK_PORTAL_BASE, detail=str(exc))


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
    url = f"{OJK_PORTAL_BASE}/lembaga/pencarian"
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


async def check_waspada_list(*, proxy_url: str | None = None) -> list[dict]:
    """
    Fetch the full OJK Waspada Investasi blacklist (11,383 illegal entities).

    Returns raw dicts with: entity_name, address, phone, website, entity_type,
    activity_type, blacklist_date, notes.

    Requires Playwright + Indonesian IP proxy (geo-blocked outside ID).
    Uses socks5:// (not socks5h://) for Chromium compatibility.
    """
    url = OJK_WASPADA_LIST_URL
    records: list[dict] = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("Playwright not installed — skipping OJK waspada list fetch")
        return records

    # Chromium doesn't support socks5h:// — convert to socks5://
    proxy_config = None
    if proxy_url:
        proxy_server = proxy_url.replace("socks5h://", "socks5://")
        proxy_config = {"server": proxy_server}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                proxy=proxy_config,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="id-ID",
            )
            page = await context.new_page()
            await page.goto(url, timeout=120000, wait_until="networkidle")
            # networkidle already waits for the 11MB table to render;
            # explicit wait_for_selector as a safety net with generous timeout
            await page.wait_for_selector("table tbody tr", timeout=60000)

            html = await page.content()
            await browser.close()

            # Parse the table
            soup = BeautifulSoup(html, "html.parser")
            for row in soup.select("table tbody tr"):
                cols = [td.get_text(strip=True) for td in row.find_all("td")]
                # cols[0] is checkbox, cols[1] is Nama
                if len(cols) >= 6 and cols[1]:
                    records.append(
                        {
                            "entity_name": cols[1],  # Nama
                            "address": cols[2] if len(cols) > 2 else "",  # Alamat
                            "phone": cols[3] if len(cols) > 3 else "",  # No. Telp
                            "website": cols[4] if len(cols) > 4 else "",  # Website
                            "entity_type": cols[5] if len(cols) > 5 else "",  # Jenis Entitas
                            "activity_type": cols[6] if len(cols) > 6 else "",  # Jenis Kegiatan
                            "blacklist_date": cols[7] if len(cols) > 7 else "",  # Tgl Input
                            "notes": cols[8] if len(cols) > 8 else "",  # Keterangan
                        }
                    )

            logger.info("OJK waspada list: fetched %d blacklist entries", len(records))
            return records

    except Exception as exc:
        logger.exception("OJK waspada list fetch failed: %s", exc)
        return records


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
