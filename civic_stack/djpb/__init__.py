"""
modules/djpb — Indonesian Treasury/Budget (DJPB) wrapper.

Source: data-apbn.kemenkeu.go.id
Method: REST JSON API
License: Apache-2.0

Public API:
    fetch(theme_id, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    get_budget_summary(*, year=None, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.djpb.scraper import fetch, get_budget_summary, search

__all__ = ["fetch", "search", "get_budget_summary"]
