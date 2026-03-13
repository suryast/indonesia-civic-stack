"""
modules/oss-nib — OSS RBA NIB business identity scraper.

Source: oss.go.id (Online Single Submission Risk-Based Approach)
Method: Playwright form submission (JS-rendered)
License: Apache-2.0

Public API (public search tier — no login required):
    fetch(query, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from modules.oss_nib.scraper import fetch, search

__all__ = ["fetch", "search"]
