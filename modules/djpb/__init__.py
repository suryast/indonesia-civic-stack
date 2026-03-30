"""
modules/djpb — Budget Data scraper.

🇮🇩 Requires Indonesian proxy — set PROXY_URL env var

Source: djpb.kemenkeu.go.id
Method: httpx + BeautifulSoup (static HTML)
License: MIT

Public API:
    fetch(report_id, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.djpb.scraper import fetch, search

__all__ = ["fetch", "search"]
