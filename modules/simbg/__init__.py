"""
modules/simbg — Indonesian building permit (PBG/IMB) aggregator.

Source: simbg.pu.go.id + pilot regional portals (Jakarta, Surabaya, Bandung, Medan, Makassar)
Method: httpx REST — SIMBG national API + regional SPBE portals
License: Apache-2.0

Public API:
    fetch(query, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from modules.simbg.scraper import fetch, search

__all__ = ["fetch", "search"]
