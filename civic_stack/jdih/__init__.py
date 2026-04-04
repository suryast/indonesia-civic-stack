"""
modules/jdih — Indonesian Legal Database (JDIH) wrapper.

Source: peraturan.go.id
Method: Playwright scraping (JS-rendered site, no API)
License: Apache-2.0

Public API:
    fetch(regulation_id, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None, regulation_type="uu") -> list[CivicStackResponse]
    list_recent(regulation_type="uu", *, limit=20, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.jdih.scraper import fetch, list_recent, search

__all__ = ["fetch", "search", "list_recent"]
