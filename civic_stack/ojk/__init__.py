"""
modules/ojk — OJK licensed institution registry scraper.

Source: ojk.go.id + investor.ojk.go.id
Method: REST API (primary) + httpx + BeautifulSoup for gaps
License: Apache-2.0

Public API:
    fetch(name_or_id, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, filters=None, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.ojk.scraper import fetch, search

__all__ = ["fetch", "search"]
