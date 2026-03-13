"""
modules/lpse — Indonesian LPSE procurement portal aggregator.

Source: Regional LPSE portals running SPSE v4 (lpse.*.go.id/eproc4)
Method: httpx REST — standardised SPSE API across all portals
License: Apache-2.0

Public API:
    fetch(query, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    search_tenders(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from modules.lpse.scraper import fetch, search, search_tenders

__all__ = ["fetch", "search", "search_tenders"]
