"""
modules/ahu — AHU company registry scraper.

Source: ahu.go.id (Kemenkumham)
Method: Playwright + Cloudflare Worker routing + Camoufox fingerprint randomization
License: Apache-2.0

Public API:
    fetch(query, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from modules.ahu.scraper import fetch, search

__all__ = ["fetch", "search"]
