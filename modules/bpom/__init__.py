"""
modules/bpom — BPOM product registry scraper.

Source: cekbpom.pom.go.id
Method: httpx + BeautifulSoup (static HTML, no JS rendering needed)
License: MIT

Public API:
    fetch(registration_no, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from modules.bpom.scraper import fetch, search

__all__ = ["fetch", "search"]
