"""
modules/bpjph — BPJPH SiHalal certificate scraper.

Source: sertifikasi.halal.go.id
Method: Playwright (JS-rendered portal) + Camoufox fingerprint randomization
License: Apache-2.0

Public API:
    fetch(cert_no, *, debug=False, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    cross_ref_bpom(product_name, *, proxy_url=None) -> dict
"""

from __future__ import annotations

from civic_stack.bpjph.scraper import cross_ref_bpom, fetch, search

__all__ = ["fetch", "search", "cross_ref_bpom"]
