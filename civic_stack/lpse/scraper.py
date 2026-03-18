"""
LPSE scraper — aggregates procurement data across regional SPSE portals.

STATUS: FULLY DEGRADED (2026-03-18)
All legacy lpse.*.go.id portals are dead or inaccessible.
LKPP completed migration to inaproc.id which has no public API.

MIGRATION TIMELINE:
  2026-02: lpse.lkpp.go.id, lpse.pu.go.id, lpse.kominfo.go.id → DNS dead
  2026-03-16: lpse.kemenkeu.go.id, lpse.kemkes.go.id → CNAME ars.inaproc.id (CF 403)
  2026-03-18: lpse.jakarta.go.id → DNS dead, lpse.kemenag.go.id → no response

NEW ECOSYSTEM (inaproc.id):
  - spse.inaproc.id: Custom WAF blocks all automation (even Jakarta browser)
  - data.inaproc.id: Streamlit dashboard (accessible via proxy — most promising)
  - katalog.inaproc.id: Next.js e-katalog (curl 200, Playwright 403)
  - api.inaproc.id: Gateway exists (404 on root — routes unknown)
  - sirup.inaproc.id: Login-gated procurement plans
  - ars.inaproc.id: Pomerium SSO (internal only)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from civic_stack.shared.http import RateLimiter, ScraperBlockedError, civic_client
from civic_stack.shared.schema import CivicStackResponse, RecordStatus, not_found_response

from .normalizer import normalize_tender, normalize_vendor

logger = logging.getLogger(__name__)

# ALL PORTALS DEAD as of 2026-03-18.
# Kept empty — module will return degraded responses.
PORTALS: list[dict[str, str]] = []

# All legacy portals — dead or inaccessible
DEPRECATED_PORTALS = [
    {"name": "LKPP", "base": "https://lpse.lkpp.go.id/eproc4", "reason": "DNS dead since 2026-02"},
    {"name": "PU", "base": "https://lpse.pu.go.id/eproc4", "reason": "DNS dead since 2026-02"},
    {"name": "Kominfo", "base": "https://lpse.kominfo.go.id/eproc4", "reason": "DNS dead since 2026-02"},
    {"name": "Jakarta", "base": "https://lpse.jakarta.go.id/eproc4", "reason": "DNS dead since 2026-03-18"},
    {"name": "Kemenkeu", "base": "https://lpse.kemenkeu.go.id/eproc4", "reason": "CNAME ars.inaproc.id, CF 403"},
    {"name": "Kemenkes", "base": "https://lpse.kemkes.go.id/eproc4", "reason": "CNAME ars.inaproc.id, CF 403"},
    {"name": "Kemenag", "base": "https://lpse.kemenag.go.id/eproc4", "reason": "CNAME ars.inaproc.id, no response"},
]

# New unified portal (directory only, no direct tender API)
INAPROC_PORTAL = "https://spse.inaproc.id"

# Standard SPSE API endpoints (same path on every portal)
_TENDER_SEARCH = "/dt/tender"  # ?term=&draw=&start=0&length=10
_VENDOR_SEARCH = "/dt/rekanan"  # ?term=&draw=&start=0&length=10
_TENDER_DETAIL = "/tender/{id}/view"
_VENDOR_DETAIL = "/rekanan/{id}/view"

_limiter = RateLimiter(rate=1.0)  # conservative: 1 req/s across all portals

MODULE = "lpse"
SOURCE_BASE = INAPROC_PORTAL


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _search_portal(
    client: httpx.AsyncClient,
    portal: dict[str, str],
    term: str,
    endpoint: str,
) -> dict[str, Any] | None:
    """Search a single portal; returns raw JSON or None on failure."""
    url = portal["base"] + endpoint
    try:
        await _limiter.acquire()
        resp = await client.get(
            url,
            params={"term": term, "draw": "1", "start": "0", "length": "10"},
            timeout=15.0,
        )
        if resp.status_code == 429:
            raise ScraperBlockedError(f"Rate-limited by {portal['name']}")
        if resp.status_code == 403:
            logger.warning("Portal %s returned 403 (CF challenge?)", portal["name"])
            return None
        resp.raise_for_status()
        return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("Portal %s unreachable: %s", portal["name"], exc)
        return None
    except (httpx.HTTPStatusError, ScraperBlockedError) as exc:
        logger.warning("Portal %s error: %s", portal["name"], exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch tender/vendor info by name or NPWP across all major portals."""
    source_url = INAPROC_PORTAL

    async with civic_client(proxy_url=proxy_url) as client:
        tasks = [_search_portal(client, portal, query, _VENDOR_SEARCH) for portal in PORTALS]
        raw_results = await asyncio.gather(*tasks)

    successes = [r for r in raw_results if r is not None]
    failures = [PORTALS[i]["name"] for i, r in enumerate(raw_results) if r is None]

    all_records: list[dict[str, Any]] = []
    for raw in successes:
        for item in raw.get("data") or []:
            normalized = normalize_vendor(item)
            if normalized:
                all_records.append(normalized)

    if not all_records:
        return not_found_response(
            module=MODULE,
            query=query,
            source_url=source_url,
            extra=(
                {"portal_errors": failures, "note": "LPSE portals migrating to inaproc.id"}
                if failures
                else {}
            ),
        )

    # deduplicate by NPWP
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for rec in all_records:
        key = rec.get("npwp") or rec.get("vendor_name", "")
        if key not in seen:
            seen.add(key)
            deduped.append(rec)

    best = deduped[0]
    confidence = 1.0 if not failures else round(len(successes) / len(PORTALS), 2)

    return CivicStackResponse(
        result={**best, "portal_errors": failures, "total_results": len(deduped)},
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=confidence,
        source_url=source_url,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
        raw={"portals_queried": len(PORTALS), "portals_succeeded": len(successes)},
    )


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search vendors/companies across all portals; returns merged deduplicated list."""
    source_url = INAPROC_PORTAL

    async with civic_client(proxy_url=proxy_url) as client:
        tasks = [_search_portal(client, portal, keyword, _VENDOR_SEARCH) for portal in PORTALS]
        raw_results = await asyncio.gather(*tasks)

    successes = [r for r in raw_results if r is not None]
    failures = [PORTALS[i]["name"] for i, r in enumerate(raw_results) if r is None]
    confidence = 1.0 if not failures else round(len(successes) / len(PORTALS), 2)

    seen: set[str] = set()
    responses: list[CivicStackResponse] = []

    for raw in successes:
        for item in raw.get("data") or []:
            rec = normalize_vendor(item)
            if not rec:
                continue
            key = rec.get("npwp") or rec.get("vendor_name", "")
            if key in seen:
                continue
            seen.add(key)
            responses.append(
                CivicStackResponse(
                    result={**rec, "portal_errors": failures},
                    found=True,
                    status=RecordStatus.ACTIVE,
                    confidence=confidence,
                    source_url=source_url,
                    fetched_at=__import__("datetime").datetime.utcnow(),
                    module=MODULE,
                )
            )

    return responses


async def search_tenders(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search active tenders by keyword across all portals."""
    source_url = INAPROC_PORTAL

    async with civic_client(proxy_url=proxy_url) as client:
        tasks = [_search_portal(client, portal, keyword, _TENDER_SEARCH) for portal in PORTALS]
        raw_results = await asyncio.gather(*tasks)

    successes = [r for r in raw_results if r is not None]
    failures = [PORTALS[i]["name"] for i, r in enumerate(raw_results) if r is None]
    confidence = 1.0 if not failures else round(len(successes) / len(PORTALS), 2)

    responses: list[CivicStackResponse] = []
    seen: set[str] = set()

    for raw in successes:
        for item in raw.get("data") or []:
            rec = normalize_tender(item)
            if not rec:
                continue
            key = rec.get("tender_id", "")
            if key in seen:
                continue
            seen.add(key)
            responses.append(
                CivicStackResponse(
                    result={**rec, "portal_errors": failures},
                    found=True,
                    status=RecordStatus.ACTIVE,
                    confidence=confidence,
                    source_url=source_url,
                    fetched_at=__import__("datetime").datetime.utcnow(),
                    module=MODULE,
                )
            )

    return responses
