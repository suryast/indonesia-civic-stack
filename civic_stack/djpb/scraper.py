"""
DJPB scraper — Direktorat Jenderal Perbendaharaan (Indonesian Treasury/Budget).

Source: data-apbn.kemenkeu.go.id (APBN budget data portal)
Method: REST JSON API (clean!)
Auth:   None required

Key endpoints:
  - /be/api/data-series → budget themes with targets/realization
  - /be/api/tableau → Tableau embed config
"""

from __future__ import annotations

import logging
from typing import Any

from civic_stack.shared.http import RateLimiter, civic_client, fetch_with_retry
from civic_stack.shared.schema import (
    CivicStackResponse,
    RecordStatus,
    error_response,
    not_found_response,
)

from .normalizer import normalize_budget_theme

logger = logging.getLogger(__name__)

_BASE = "https://data-apbn.kemenkeu.go.id"
MODULE = "djpb"
SOURCE_URL = "https://data-apbn.kemenkeu.go.id"

_limiter = RateLimiter(rate=1.0)  # 1 req/s for API


async def _fetch_data_series(*, proxy_url: str | None = None) -> list[dict[str, Any]]:
    """Fetch all budget themes from data-series endpoint."""
    async with civic_client(proxy_url=proxy_url) as client:
        await _limiter.acquire()
        url = f"{_BASE}/be/api/data-series"

        try:
            resp = await fetch_with_retry(
                client,
                "GET",
                url,
                rate_limiter=_limiter,
            )
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("DJPB data-series fetch error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(theme_id: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch a single budget theme by ID."""
    themes = await _fetch_data_series(proxy_url=proxy_url)

    for theme in themes:
        if theme.get("id_tematik") == theme_id:
            rec = normalize_budget_theme(theme)
            return CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=1.0,
                source_url=SOURCE_URL,
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )

    return not_found_response(module=MODULE, query=theme_id, source_url=SOURCE_URL)


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search budget themes by keyword (name or English name)."""
    themes = await _fetch_data_series(proxy_url=proxy_url)

    keyword_lower = keyword.lower()
    results: list[CivicStackResponse] = []

    for theme in themes:
        name = (theme.get("nama_tema") or "").lower()
        name_en = (theme.get("nama_tema_en") or "").lower()

        if keyword_lower in name or keyword_lower in name_en:
            rec = normalize_budget_theme(theme)
            confidence = (
                1.0
                if keyword_lower == name or keyword_lower == name_en
                else 0.9
                if keyword_lower in name
                else 0.8
            )
            results.append(
                CivicStackResponse(
                    result=rec,
                    found=True,
                    status=RecordStatus.ACTIVE,
                    confidence=confidence,
                    source_url=SOURCE_URL,
                    fetched_at=__import__("datetime").datetime.utcnow(),
                    module=MODULE,
                )
            )

    return results


async def get_budget_summary(
    *,
    year: str | None = None,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """Get all budget themes, optionally filtered by year."""
    themes = await _fetch_data_series(proxy_url=proxy_url)

    results: list[CivicStackResponse] = []
    for theme in themes:
        # Filter by year if specified
        if year:
            theme_year = theme.get("tahun", "")
            # tahun format: "2026 - 2026" or "2025 - 2025"
            if year not in theme_year:
                continue

        rec = normalize_budget_theme(theme)
        results.append(
            CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=1.0,
                source_url=SOURCE_URL,
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )
        )

    return results
