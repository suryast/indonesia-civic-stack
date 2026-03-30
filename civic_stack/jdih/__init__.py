"""
modules/jdih — BPK Legal Documents scraper.

🇮🇩 Requires Indonesian proxy — set PROXY_URL env var

Source: jdih.bpk.go.id
Method: httpx + BeautifulSoup (static HTML)
License: MIT

Public API:
    fetch(doc_id, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, category=1, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.jdih.scraper import fetch, search

__all__ = ["fetch", "search"]
