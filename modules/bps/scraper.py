"""
BPS scraper — Badan Pusat Statistik (Statistics Indonesia) open data API.

Source: webapi.bps.go.id (1,000+ statistical datasets)
Method: REST API — BPS provides a clean authenticated-key API
Auth:   BPS_API_KEY environment variable (free registration at webapi.bps.go.id)

Without BPS_API_KEY: raises EnvironmentError with registration URL.

Key datasets:
  - Indicators (id_variabel) by region (id_wilayah) and year
  - Subjects (domain categories)
  - Regional codes (wilayah)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from shared.http import RateLimiter, civic_client
from shared.schema import CivicStackResponse, RecordStatus, error_response, not_found_response

from .normalizer import normalize_dataset, normalize_indicator, normalize_region

logger = logging.getLogger(__name__)

_BASE    = "https://webapi.bps.go.id/v1/api"
MODULE   = "bps"
SOURCE_URL = "https://webapi.bps.go.id"

_limiter = RateLimiter(rate=2.0)  # BPS API is clean — 2 req/s is safe


def _api_key() -> str:
    key = os.environ.get("BPS_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "BPS_API_KEY is not set. Register for a free key at: "
            "https://webapi.bps.go.id/developer/register"
        )
    return key


async def _get(
    client: httpx.AsyncClient,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    full_params = {"key": _api_key(), **(params or {})}
    url = _BASE + endpoint
    try:
        await _limiter.acquire()
        resp = await client.get(url, params=full_params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("BPS API error %s: %s", endpoint, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch a BPS dataset or indicator by keyword. Returns best match."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get(client, "/list/model/subject/lang/ind/", {"keyword": query})

    if not data or not data.get("data"):
        return not_found_response(module=MODULE, query=query, source_url=SOURCE_URL)

    items = data["data"]
    if not items:
        return not_found_response(module=MODULE, query=query, source_url=SOURCE_URL)

    best = normalize_dataset(items[0], query=query)
    return CivicStackResponse(
        result=best,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=best.pop("_confidence", 0.8),
        source_url=SOURCE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
    )


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search BPS datasets/subjects by keyword."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get(
            client,
            "/list/model/subject/lang/ind/",
            {"keyword": keyword, "page": 1, "row": 20},
        )

    if not data or not data.get("data"):
        return []

    results: list[CivicStackResponse] = []
    for item in data["data"]:
        rec = normalize_dataset(item, query=keyword)
        confidence = rec.pop("_confidence", 0.8)
        results.append(CivicStackResponse(
            result=rec,
            found=True,
            status=RecordStatus.ACTIVE,
            confidence=confidence,
            source_url=SOURCE_URL,
            fetched_at=__import__("datetime").datetime.utcnow(),
            module=MODULE,
        ))
    return results


async def get_indicator(
    indicator_id: str,
    *,
    region_code: str = "0000",
    year_range: str | None = None,
    proxy_url: str | None = None,
) -> CivicStackResponse:
    """
    Fetch time-series values for a specific BPS indicator.

    Args:
        indicator_id:  BPS variable/indicator ID
        region_code:   BPS wilayah code (default '0000' = national)
        year_range:    e.g. '2018,2019,2020,2021,2022' or None for all years
    """
    params: dict[str, Any] = {
        "id_variabel": indicator_id,
        "id_wilayah":  region_code,
    }
    if year_range:
        params["th"] = year_range

    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get(client, "/list/model/statictable/lang/ind/", params)

    if not data or not data.get("data"):
        return not_found_response(
            module=MODULE,
            query=f"indicator:{indicator_id}",
            source_url=SOURCE_URL,
        )

    rec = normalize_indicator(data["data"], indicator_id=indicator_id, region_code=region_code)
    return CivicStackResponse(
        result=rec,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=1.0,
        source_url=SOURCE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
    )


async def list_regions(
    parent_code: str = "0",
    *,
    proxy_url: str | None = None,
) -> list[dict[str, Any]]:
    """List BPS regional codes (wilayah), optionally filtered by parent."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get(
            client,
            "/list/model/wilayah/lang/ind/",
            {"level": "1", "id_wilayah": parent_code},
        )

    if not data or not data.get("data"):
        return []

    return [normalize_region(r) for r in data["data"]]
