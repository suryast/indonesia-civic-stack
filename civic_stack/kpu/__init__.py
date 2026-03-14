"""
modules/kpu — KPU election data REST API wrapper.

Source: sirekap-obj-data.kpu.go.id + infopemilu.kpu.go.id
Method: REST API wrapper + normalization (no scraping needed)
License: Apache-2.0

Public API:
    fetch(candidate_id, *, debug=False) -> CivicStackResponse
    search(keyword, *, filters=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.kpu.scraper import fetch, search

__all__ = ["fetch", "search"]
