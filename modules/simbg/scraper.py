"""
SIMBG scraper — national building permit (PBG) aggregator.

Source: simbg.pu.go.id + pilot regional portals
Method: httpx REST — SIMBG national API + regional SPBE portals
Auth:   Public search tier (no login required)

SIMBG (Sistem Informasi Manajemen Bangunan Gedung) is managed by PUPR and
provides building permit (Persetujuan Bangunan Gedung / PBG) data.

Pilot regions per SHAPES.MD:
    Jakarta, Surabaya, Bandung, Medan, Makassar

Confidence < 1.0 when not all pilot portals respond.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from shared.http import RateLimiter, civic_client
from shared.schema import CivicStackResponse, RecordStatus, error_response, not_found_response

from .normalizer import normalize_permit, normalize_search_result

logger = logging.getLogger(__name__)

_SIMBG_NATIONAL = "https://simbg.pu.go.id/api/v1"

# Pilot regional portals (SPBE-integrated or standalone SIMBG endpoints)
PILOT_PORTALS: list[dict[str, str]] = [
    {"name": "Jakarta",  "base": "https://jakevo.jakarta.go.id/api/bangunan"},
    {"name": "Surabaya", "base": "https://simbg.surabaya.go.id/api/v1"},
    {"name": "Bandung",  "base": "https://simbg.bandung.go.id/api/v1"},
    {"name": "Medan",    "base": "https://simbg.pemkomedan.go.id/api/v1"},
    {"name": "Makassar", "base": "https://simbg.makassar.go.id/api/v1"},
]

MODULE    = "simbg"
SOURCE_URL = _SIMBG_NATIONAL

_limiter = RateLimiter(rate=0.5)  # conservative — regional portals vary in capacity


async def _search_portal(
    client: httpx.AsyncClient,
    portal: dict[str, str],
    query: str,
) -> list[dict[str, Any]]:
    """Query a single SIMBG portal; returns list of raw records or [] on failure."""
    url = portal["base"] + "/search"
    try:
        await _limiter.acquire()
        resp = await client.get(
            url,
            params={"q": query, "page": 1, "limit": 10},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("SIMBG portal %s unreachable: %s", portal["name"], exc)
        return []
    except (httpx.HTTPStatusError, ValueError) as exc:
        logger.warning("SIMBG portal %s error: %s", portal["name"], exc)
        return []


async def _search_national(
    client: httpx.AsyncClient, query: str
) -> list[dict[str, Any]]:
    url = _SIMBG_NATIONAL + "/pbg/search"
    try:
        await _limiter.acquire()
        resp = await client.get(
            url, params={"keyword": query, "limit": 20}, timeout=15.0
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []
    except Exception as exc:
        logger.warning("SIMBG national API error: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Look up building permit(s) by address, permit number, or property ID."""
    async with civic_client(proxy_url=proxy_url) as client:
        # Try national API first (fastest)
        national_results = await _search_national(client, query)

        # Concurrently query all pilot portals
        portal_tasks = [_search_portal(client, p, query) for p in PILOT_PORTALS]
        portal_results_raw = await asyncio.gather(*portal_tasks)

    portal_successes = sum(1 for r in portal_results_raw if r is not None)
    portal_failures  = [
        PILOT_PORTALS[i]["name"]
        for i, r in enumerate(portal_results_raw)
        if not r  # empty list means failure or no results
    ]

    all_records: list[dict[str, Any]] = list(national_results)
    for portal_list in portal_results_raw:
        all_records.extend(portal_list or [])

    if not all_records:
        return not_found_response(
            module=MODULE,
            query=query,
            source_url=SOURCE_URL,
            extra={"portal_errors": portal_failures},
        )

    # Deduplicate by permit_number
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for raw in all_records:
        norm = normalize_permit(raw)
        if not norm:
            continue
        key = norm.get("permit_number") or norm.get("address", "")
        if key not in seen:
            seen.add(key)
            deduped.append(norm)

    if not deduped:
        return not_found_response(module=MODULE, query=query, source_url=SOURCE_URL)

    best = deduped[0]
    confidence = 1.0 if not portal_failures else round(
        portal_successes / len(PILOT_PORTALS), 2
    )

    return CivicStackResponse(
        result={**best, "portal_errors": portal_failures, "total_results": len(deduped)},
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=confidence,
        source_url=SOURCE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
        raw={"portals_queried": len(PILOT_PORTALS), "national_results": len(national_results)},
    )


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search building permits across all portals by keyword."""
    async with civic_client(proxy_url=proxy_url) as client:
        national_results = await _search_national(client, keyword)
        portal_tasks = [_search_portal(client, p, keyword) for p in PILOT_PORTALS]
        portal_results_raw = await asyncio.gather(*portal_tasks)

    portal_successes = sum(1 for r in portal_results_raw if r)
    portal_failures  = [
        PILOT_PORTALS[i]["name"] for i, r in enumerate(portal_results_raw) if not r
    ]
    confidence = 1.0 if not portal_failures else round(
        portal_successes / len(PILOT_PORTALS), 2
    )

    all_records = list(national_results)
    for lst in portal_results_raw:
        all_records.extend(lst or [])

    seen: set[str] = set()
    responses: list[CivicStackResponse] = []
    for raw in all_records:
        rec = normalize_search_result(raw)
        if not rec:
            continue
        key = rec.get("permit_number") or rec.get("address", "")
        if key in seen:
            continue
        seen.add(key)
        responses.append(CivicStackResponse(
            result={**rec, "portal_errors": portal_failures},
            found=True,
            status=RecordStatus.ACTIVE,
            confidence=confidence,
            source_url=SOURCE_URL,
            fetched_at=__import__("datetime").datetime.utcnow(),
            module=MODULE,
        ))

    return responses
