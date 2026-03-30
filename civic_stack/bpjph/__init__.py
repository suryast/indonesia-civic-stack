"""
modules/bpjph — BPJPH halal certificate lookup via REST API.

Source: cmsbl.halal.go.id (primary), gateway.halal.go.id (fallback)
Method: httpx REST API (no browser needed)
License: Apache-2.0
Proxy: 🌐 Works globally (intermittent 504s — has retry)

Public API:
    fetch(cert_no, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    cross_ref_bpom(product_name, *, proxy_url=None) -> dict
"""

from __future__ import annotations

from civic_stack.bpjph.scraper import cross_ref_bpom, fetch, search

__all__ = ["fetch", "search", "cross_ref_bpom"]
