"""
modules/lhkpn — KPK wealth declaration (LHKPN) scraper.

⚠️ DEPRECATED (2026-03-30): elhkpn.kpk.go.id is behind reCAPTCHA + login wall.
No public data path available. Module kept for reference but removed from MCP server.

Source: elhkpn.kpk.go.id (Komisi Pemberantasan Korupsi)
Method: REST API + pdfplumber / Claude Vision API for PDF extraction
License: Apache-2.0

Public API:
    fetch(query, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    compare_lhkpn(official_id, year_a, year_b, *, proxy_url=None) -> dict
    get_pdf(report_id, *, proxy_url=None) -> dict
"""

from __future__ import annotations

from civic_stack.lhkpn.scraper import compare_lhkpn, fetch, get_pdf, search

__all__ = ["fetch", "search", "compare_lhkpn", "get_pdf"]
