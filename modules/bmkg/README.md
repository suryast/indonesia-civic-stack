# Module: `bmkg`

**Source portal:** data.bmkg.go.id + inatews.bmkg.go.id
**Scrape method:** REST API (clean JSON/XML, no scraping)
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://data.bmkg.go.id` (primary) + `https://inatews.bmkg.go.id` |
| Operator | Badan Meteorologi, Klimatologi, dan Geofisika (BMKG RI) |
| Data type | Weather forecasts, earthquake alerts, disaster warnings |
| Auth required | None — fully public open API |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~1 req/s (polite — public open API) |
| Block trigger | Unknown — no blocking observed |
| Block type | TBD |
| Mitigation | Built-in token-bucket rate limiter (1 req/s) |
| IP rotation needed | Not required |

---

## Normalized Schema (`result` object)

### Weather forecast

```python
{
    "city": str,                       # Requested city name
    "province": str,                   # BMKG province code
    "area": str,                       # Area description from BMKG
    "forecast": list[dict],            # Forecast entries (capped at 50)
}
```

Each forecast entry:
```python
{
    "parameter": str,                  # e.g. "t" (temperature), "hu" (humidity), "weather"
    "description": str,                # Human-readable parameter name
    "day": str,                        # Forecast day (e.g. "1", "2", "3")
    "hour": str,                       # Forecast hour
    "value": str,                      # Forecast value
    "unit": str,                       # Unit (e.g. "C", "%")
}
```

### Earthquake

```python
{
    "date": str,                       # Date (DD-MMM-YYYY or similar)
    "time": str,                       # Time (HH:MM:SS WIB)
    "datetime_utc": str | None,        # ISO 8601 UTC timestamp if available
    "coordinates": str | None,         # Lat,Lon string
    "latitude": str,                   # Latitude
    "longitude": str,                  # Longitude
    "magnitude": float,                # Richter magnitude
    "depth_km": float,                 # Depth in kilometers
    "region": str,                     # Affected region description
    "tsunami_potential": str | None,   # Raw tsunami potential text
    "tsunami_warning": bool,           # True if tsunami warning issued
    "felt_reports": str | None,        # Dirasakan (felt reports)
    "shakemap_url": str | None,        # URL to shakemap image
}
```

### Alert

```python
{
    "alert_id": str,                   # Internal alert ID
    "alert_type": str,                 # e.g. "Cuaca Ekstrem", "Gelombang Tinggi"
    "region": str,                     # Affected region
    "description": str,                # Alert description
    "date": str,                       # Alert date
    "time": str,                       # Alert time
    "severity_level": str | None,      # Severity level if available
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `get_weather_forecast` | `(city: str) -> dict` | Get 3-day forecast for supported Indonesian cities |
| `get_latest_earthquake` | `() -> dict` | Get most recent significant earthquake |
| `get_earthquake_history` | `(region: str, days: int) -> list[dict]` | Get recent earthquakes, optionally filtered |
| `get_bmkg_alerts` | `(region: str) -> list[dict]` | Get active disaster/weather alerts |

### claude mcp add

```bash
claude mcp add bmkg -- python -m modules.bmkg.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/bmkg/forecast/{city}` | Get weather forecast for city |
| `GET` | `/bmkg/earthquake/latest` | Get latest earthquake |
| `GET` | `/bmkg/earthquake/history?region=...&days=7` | Get earthquake history |
| `GET` | `/bmkg/alerts?region=...` | Get active alerts |

---

## Supported Cities (Weather Forecast)

Jakarta, Surabaya, Bandung, Medan, Makassar, Yogyakarta, Bali/Denpasar, Semarang, Palembang, Pekanbaru, Balikpapan

For other cities, use the province name.

---

## Example Response (Earthquake)

```json
{
  "result": {
    "date": "13-Mar-2026",
    "time": "14:25:33 WIB",
    "coordinates": "-2.10,100.45",
    "latitude": "-2.10",
    "longitude": "100.45",
    "magnitude": 5.7,
    "depth_km": 10.0,
    "region": "47 km BaratLaut BUKITTINGGI-SUMBAR",
    "tsunami_potential": "Tidak berpotensi tsunami",
    "tsunami_warning": false,
    "felt_reports": "Dirasakan (Skala MMI): II-III Bukittinggi",
    "shakemap_url": "https://data.bmkg.go.id/DataMKG/TEWS/20260313142533.mmi.jpg"
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
  "fetched_at": "2026-03-13T07:30:00Z",
  "last_updated": null,
  "module": "bmkg",
  "raw": null
}
```

---

## Known Issues & Quirks

- Weather forecast endpoint returns XML — parsed into structured JSON
- Earthquake coordinates are sometimes returned as "Lat,Lon" string; normalizer extracts both
- Magnitude is parsed to float; depth has "km" stripped and parsed to float
- Tsunami warning is inferred from `tsunami_potential` text ("tidak berpotensi" → false)
- Forecast entries are capped at 50 to avoid huge responses
- City name matching is case-insensitive and supports partial matches
- Province codes (for forecast URLs) are hardcoded — fallback uses the city name as-is

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Weather forecast for Jakarta |
| TBD | Latest earthquake |
| TBD | Earthquake history for Sulawesi |
| TBD | Active disaster alerts |

---

## Legal Basis

This module queries BMKG's official open data APIs, which publish meteorological, climatological,
and seismological data for public safety and awareness. No authentication is required. Data is
fetched on demand and not persisted. All data is public record published for disaster preparedness.
