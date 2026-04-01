"""
modules/lhkpn — KPK wealth declaration (LHKPN) scraper.

✅ ACTIVE (2026-04-01): reCAPTCHA v3 solved via Playwright headless browser.
Public e-Announcement search works. Requires: playwright + chromium.

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
