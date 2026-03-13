"""
BMKG scraper — Badan Meteorologi, Klimatologi, dan Geofisika open API.

Source: data.bmkg.go.id / inatews.bmkg.go.id
Method: REST — BMKG Tier 1 open API (no auth required, clean JSON/XML)
Auth:   None — fully public

Endpoints used:
  - Weather forecast by city (cuaca wilayah)
  - Earthquake / seismology data
  - Disaster alerts (peringatan dini)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from shared.http import RateLimiter, civic_client
from shared.schema import CivicStackResponse, RecordStatus, error_response, not_found_response

from .normalizer import normalize_alert, normalize_earthquake, normalize_forecast

logger = logging.getLogger(__name__)

_BMKG_BASE = "https://data.bmkg.go.id"
_INATEWS_BASE = "https://inatews.bmkg.go.id"

# Standard BMKG open data endpoints
_FORECAST_URL = _BMKG_BASE + "/DataMKG/MEWS/DigitalForecast/DigitalForecast-{province}.xml"
_EARTHQUAKE_URL = _BMKG_BASE + "/DataMKG/TEWS/autogempa.json"
_EQ_HISTORY_URL = _BMKG_BASE + "/DataMKG/TEWS/gempaterkini.json"  # last 15 significant quakes
_ALERT_URL = _BMKG_BASE + "/DataMKG/MEWS/Warning/cuacasignifikan.json"

MODULE = "bmkg"
SOURCE_URL = _BMKG_BASE

_limiter = RateLimiter(rate=1.0)  # polite — public open API

# Province code mapping (city → BMKG province filename)
_PROVINCE_CODES: dict[str, str] = {
    "jakarta": "DKIJakarta",
    "dki jakarta": "DKIJakarta",
    "surabaya": "JawaTimur",
    "jawa timur": "JawaTimur",
    "bandung": "JawaBarat",
    "jawa barat": "JawaBarat",
    "medan": "SumateraUtara",
    "sumatera utara": "SumateraUtara",
    "makassar": "SulawesiSelatan",
    "sulawesi selatan": "SulawesiSelatan",
    "yogyakarta": "DIYogyakarta",
    "bali": "Bali",
    "denpasar": "Bali",
    "semarang": "JawaTengah",
    "jawa tengah": "JawaTengah",
    "palembang": "SumateraSelatan",
    "pekanbaru": "Riau",
    "balikpapan": "KalimantanTimur",
    "kalimantan timur": "KalimantanTimur",
}


def _province_code(city: str) -> str:
    return _PROVINCE_CODES.get(city.lower().strip(), city)


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    try:
        await _limiter.acquire()
        resp = await client.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("BMKG request failed %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Fetch latest weather forecast or earthquake alert for a city/region."""
    # Try earthquake first if query looks seismological
    if any(kw in query.lower() for kw in ("gempa", "earthquake", "quake", "seism")):
        return await get_latest_earthquake(proxy_url=proxy_url)

    return await get_weather_forecast(query, proxy_url=proxy_url)


async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Search BMKG alerts and recent earthquakes by keyword/region."""
    results: list[CivicStackResponse] = []

    async with civic_client(proxy_url=proxy_url) as client:
        alert_data = await _get_json(client, _ALERT_URL)
        eq_data = await _get_json(client, _EQ_HISTORY_URL)

    kw = keyword.lower()

    if alert_data:
        for item in (alert_data.get("Infogempa", {}).get("gempa") or [])[:10]:
            rec = normalize_alert(item)
            if kw in str(rec).lower():
                results.append(
                    CivicStackResponse(
                        result=rec,
                        found=True,
                        status=RecordStatus.ACTIVE,
                        confidence=0.8,
                        source_url=SOURCE_URL,
                        fetched_at=__import__("datetime").datetime.utcnow(),
                        module=MODULE,
                    )
                )

    if eq_data:
        for item in (eq_data.get("Infogempa", {}).get("gempa") or [])[:10]:
            rec = normalize_earthquake(item)
            if kw in str(rec).lower():
                results.append(
                    CivicStackResponse(
                        result=rec,
                        found=True,
                        status=RecordStatus.ACTIVE,
                        confidence=1.0,
                        source_url=SOURCE_URL,
                        fetched_at=__import__("datetime").datetime.utcnow(),
                        module=MODULE,
                    )
                )

    return results


async def get_weather_forecast(city: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Get 3-day weather forecast for an Indonesian city."""
    province = _province_code(city)
    url = _FORECAST_URL.format(province=province)
    source_url = url

    # BMKG forecast endpoint returns XML — fetch as text and parse
    try:
        async with civic_client(proxy_url=proxy_url) as client:
            await _limiter.acquire()
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as exc:
        return error_response(
            module=MODULE,
            query=city,
            source_url=source_url,
            message=f"Forecast unavailable: {exc}",
        )

    rec = normalize_forecast(xml_text, city=city, province=province)
    if not rec:
        return not_found_response(module=MODULE, query=city, source_url=source_url)

    return CivicStackResponse(
        result=rec,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=1.0,
        source_url=source_url,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
    )


async def get_latest_earthquake(*, proxy_url: str | None = None) -> CivicStackResponse:
    """Get the most recent significant earthquake from BMKG."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get_json(client, _EARTHQUAKE_URL)

    if not data:
        return error_response(
            module=MODULE,
            query="latest_earthquake",
            source_url=SOURCE_URL,
            message="BMKG earthquake API unreachable",
        )

    eq_raw = (data.get("Infogempa") or {}).get("gempa") or {}
    if not eq_raw:
        return not_found_response(module=MODULE, query="latest_earthquake", source_url=SOURCE_URL)

    rec = normalize_earthquake(eq_raw)
    return CivicStackResponse(
        result=rec,
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=1.0,
        source_url=_EARTHQUAKE_URL,
        fetched_at=__import__("datetime").datetime.utcnow(),
        module=MODULE,
    )


async def get_earthquake_history(
    region: str = "",
    *,
    days: int = 7,
    proxy_url: str | None = None,
) -> list[CivicStackResponse]:
    """Get the last 15 significant earthquakes, optionally filtered by region name."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get_json(client, _EQ_HISTORY_URL)

    if not data:
        return []

    results: list[CivicStackResponse] = []
    kw = region.lower()
    for item in data.get("Infogempa", {}).get("gempa") or []:
        rec = normalize_earthquake(item)
        if region and kw not in str(rec.get("region", "")).lower():
            continue
        results.append(
            CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=1.0,
                source_url=_EQ_HISTORY_URL,
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )
        )
    return results


async def get_alerts(region: str = "", *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Get active BMKG weather/disaster alerts, optionally filtered by region."""
    async with civic_client(proxy_url=proxy_url) as client:
        data = await _get_json(client, _ALERT_URL)

    if not data:
        return []

    results: list[CivicStackResponse] = []
    kw = region.lower()
    for item in data.get("data") or []:
        rec = normalize_alert(item)
        if region and kw not in str(rec).lower():
            continue
        results.append(
            CivicStackResponse(
                result=rec,
                found=True,
                status=RecordStatus.ACTIVE,
                confidence=1.0,
                source_url=_ALERT_URL,
                fetched_at=__import__("datetime").datetime.utcnow(),
                module=MODULE,
            )
        )
    return results
