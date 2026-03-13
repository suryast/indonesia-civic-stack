"""
KPU REST API client.

KPU publishes clean open APIs for the 2024 Pemilu:
- SIREKAP: real-time vote counting results
- infopemilu: candidate profiles, campaign finance (SILON)

No scraping required — all endpoints return JSON.
Rate limits are generous; no IP blocking observed.
"""

from __future__ import annotations

import logging

from modules.kpu.normalizer import (
    normalize_candidate,
    normalize_election_results,
    normalize_finance,
)
from shared.http import RateLimiter, civic_client, fetch_with_retry
from shared.schema import CivicStackResponse, error_response, not_found_response

logger = logging.getLogger(__name__)

# KPU SIREKAP — 2024 Pemilu results
SIREKAP_BASE = "https://sirekap-obj-data.kpu.go.id/pemilu"
# Infopemilu — candidate profiles and campaign finance
INFOPEMILU_BASE = "https://infopemilu.kpu.go.id/Pemilu"

MODULE = "kpu"
_rate_limiter = RateLimiter(rate=2.0)  # 2 req/s — KPU API is generous

# Election type codes used by KPU SIREKAP
ELECTION_TYPES = {
    "presiden": "ppwp",
    "dpr": "pdpr",
    "dpd": "dpd",
    "dprd_prov": "pdprd_prov",
    "dprd_kab": "pdprd_kab",
}


async def fetch(
    candidate_id: str,
    *,
    debug: bool = False,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Fetch a candidate profile by candidate ID or name.

    Args:
        candidate_id: KPU candidate ID (numeric) or full candidate name.
        debug: If True, include raw API response in result.
        proxy_url: Optional proxy (not typically needed for KPU).
    """
    url = f"{INFOPEMILU_BASE}/caleg/list"
    params = {"nama": candidate_id, "limit": 1}

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
        candidates = data.get("data", data.get("list", []))
        if not candidates:
            return not_found_response(MODULE, url)
        return normalize_candidate(candidates[0], source_url=url, debug=debug)

    except Exception as exc:
        logger.exception("KPU fetch failed for '%s'", candidate_id)
        return error_response(MODULE, url, detail=str(exc))


async def search(
    keyword: str,
    filters: dict | None = None,
    *,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """
    Search KPU candidate registry by name.

    Filters (optional):
        election_type: "presiden" | "dpr" | "dpd" | "dprd_prov" | "dprd_kab"
        region_code: Province or regency code (e.g. "31" for DKI Jakarta)
        party: Party name or abbreviation
    """
    url = f"{INFOPEMILU_BASE}/caleg/list"
    params: dict = {"nama": keyword, "limit": 10}
    if filters:
        if filters.get("election_type"):
            params["jenis_pemilu"] = filters["election_type"]
        if filters.get("region_code"):
            params["kode_dapil"] = filters["region_code"]
        if filters.get("party"):
            params["partai"] = filters["party"]

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
        candidates = data.get("data", data.get("list", []))
        if not candidates:
            return [not_found_response(MODULE, url)]
        return [normalize_candidate(c, source_url=url) for c in candidates]

    except Exception as exc:
        logger.exception("KPU search failed for '%s'", keyword)
        return [error_response(MODULE, url, detail=str(exc))]


async def get_election_results(
    region_code: str,
    election_type: str = "dpr",
    *,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Fetch SIREKAP election results for a region.

    Args:
        region_code: Province/regency code. "0" for national aggregate.
        election_type: "presiden" | "dpr" | "dpd" | "dprd_prov" | "dprd_kab"
    """
    sirekap_key = ELECTION_TYPES.get(election_type, "pdpr")
    url = f"{SIREKAP_BASE}/hhcw/{sirekap_key}/{region_code}.json"
    if region_code == "0":
        url = f"{SIREKAP_BASE}/hhcw/{sirekap_key}.json"

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_rate_limiter,
            )
        return normalize_election_results(resp.json(), source_url=url, region_code=region_code)

    except Exception as exc:
        logger.exception("KPU election results failed for region %s", region_code)
        return error_response(MODULE, url, detail=str(exc))


async def get_campaign_finance(
    candidate_id: str,
    *,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """Fetch SILON campaign finance summary for a candidate."""
    url = f"{INFOPEMILU_BASE}/silon/detail/{candidate_id}"

    try:
        async with civic_client(proxy_url=proxy_url) as client:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_rate_limiter,
            )
        data = resp.json()
        if not data:
            return not_found_response(MODULE, url)
        return normalize_finance(data, source_url=url)

    except Exception as exc:
        logger.exception("KPU campaign finance failed for candidate %s", candidate_id)
        return error_response(MODULE, url, detail=str(exc))
