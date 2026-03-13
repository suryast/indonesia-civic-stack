"""
modules/bps — BPS Statistics Indonesia open data API wrapper.

Source: webapi.bps.go.id
Method: REST API (requires free BPS_API_KEY env var)
License: Apache-2.0

Public API:
    fetch(query, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    get_indicator(id, *, region_code, year_range, proxy_url) -> CivicStackResponse
    list_regions(parent_code, *, proxy_url) -> list[dict]
"""

from __future__ import annotations

from modules.bps.scraper import fetch, get_indicator, list_regions, search

__all__ = ["fetch", "search", "get_indicator", "list_regions"]
