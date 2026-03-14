"""
modules/bmkg — BMKG meteorological and disaster data wrapper.

Source: data.bmkg.go.id (Tier 1 open API — no auth required)
Method: REST JSON + XML parsing
License: Apache-2.0

Public API:
    fetch(query, *, proxy_url=None) -> CivicStackResponse
    search(keyword, *, proxy_url=None) -> list[CivicStackResponse]
    get_weather_forecast(city, *, proxy_url=None) -> CivicStackResponse
    get_latest_earthquake(*, proxy_url=None) -> CivicStackResponse
    get_earthquake_history(region, *, days, proxy_url) -> list[CivicStackResponse]
    get_alerts(region, *, proxy_url=None) -> list[CivicStackResponse]
"""

from __future__ import annotations

from civic_stack.bmkg.scraper import (
    fetch,
    get_alerts,
    get_earthquake_history,
    get_latest_earthquake,
    get_weather_forecast,
    search,
)

__all__ = [
    "fetch",
    "search",
    "get_weather_forecast",
    "get_latest_earthquake",
    "get_earthquake_history",
    "get_alerts",
]
