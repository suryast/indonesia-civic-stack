"""
modules/ksei — KSEI Securities Depository wrapper.

Source: web.ksei.co.id
Method: HTTP scraping (server-rendered HTML)
License: Apache-2.0

Public API:
    fetch(security_code, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    get_statistics_links(*, proxy_url=None) -> list[dict]
    get_latest_statistics_url(*, proxy_url=None) -> str | None
"""

from __future__ import annotations

from civic_stack.ksei.scraper import (
    fetch,
    get_latest_statistics_url,
    get_statistics_links,
    search,
)

__all__ = ["fetch", "search", "get_statistics_links", "get_latest_statistics_url"]
