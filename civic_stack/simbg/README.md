# Module: `simbg`

**Source portal:** simbg.pu.go.id + 5 pilot regional portals
**Scrape method:** REST API wrapper (national + regional SPBE/SIMBG endpoints)
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://simbg.pu.go.id/api/v1` (national) + 5 pilot regional portals |
| Operator | Kementerian PUPR (via SIMBG — Sistem Informasi Manajemen Bangunan Gedung) |
| Data type | Building permits (PBG/IMB) — permit number, owner, address, floor area, building function |
| Auth required | None — public search tier |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~0.5 req/s (conservative across 6 portals) |
| Block trigger | Unknown — needs testing |
| Block type | TBD (regional portals vary in capacity) |
| Mitigation | Built-in token-bucket rate limiter (0.5 req/s) |
| IP rotation needed | Not required for normal use; supply `proxy_url` for bulk scraping |

---

## Aggregated Portals

This module queries the national SIMBG API plus 5 pilot regional portals in parallel and returns merged/deduplicated results:

| Portal | Base URL |
|---|---|
| Jakarta | `https://jakevo.jakarta.go.id/api/bangunan` |
| Surabaya | `https://simbg.surabaya.go.id/api/v1` |
| Bandung | `https://simbg.bandung.go.id/api/v1` |
| Medan | `https://simbg.pemkomedan.go.id/api/v1` |
| Makassar | `https://simbg.makassar.go.id/api/v1` |

**Partial results:** If some portals are unreachable, the module returns data from successful portals with `confidence < 1.0` and records failures in `result["portal_errors"]`.

---

## Normalized Schema (`result` object)

```python
{
    "permit_number": str,              # PBG/IMB number
    "permit_type": str | None,         # e.g. "PBG", "IMB Baru", "IMB Pemugaran"
    "owner_name": str | None,          # Property owner name
    "address": str,                    # Building address
    "kelurahan": str | None,           # Kelurahan/desa
    "kecamatan": str | None,           # Kecamatan/district
    "city": str | None,                # City/regency
    "province": str | None,            # Province
    "floor_area_m2": float | None,     # Total floor area in square meters
    "floor_count": float | None,       # Number of floors
    "building_function": str | None,   # e.g. "Hunian", "Perdagangan", "Perkantoran"
    "permit_status": str | None,       # e.g. "Aktif", "Berlaku", "Dicabut"
    "issue_date": str | None,          # Permit issue date
    "valid_until": str | None,         # Permit expiry date
    "issuing_authority": str | None,   # Issuing agency name
    "coordinates": str | None,         # Lat,Lon string if available
    "latitude": str | None,            # Latitude
    "longitude": str | None,           # Longitude
    "portal_errors": list[str],        # Names of portals that failed (if any)
    "total_results": int,              # Total permits found (deduplicated)
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `lookup_building_permit` | `(address_or_id: str) -> dict` | Look up permit by address or permit number |
| `search_permits_by_area` | `(region: str) -> list[dict]` | Search permits by region/area keyword |
| `list_simbg_portals` | `() -> list[dict]` | List monitored pilot portals |

### claude mcp add

```bash
claude mcp add simbg -- python -m modules.simbg.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/simbg/permit/{query}` | Look up permit by address or number |
| `GET` | `/simbg/search?q=keyword` | Search permits |
| `GET` | `/simbg/portals` | List pilot portals |

---

## Example Response

```json
{
  "result": {
    "permit_number": "503/PBG/2024/DPMPTSP",
    "permit_type": "PBG Baru",
    "owner_name": "PT GOJEK INDONESIA",
    "address": "Jl. Iskandarsyah II No. 7, Melawai",
    "kelurahan": "Melawai",
    "kecamatan": "Kebayoran Baru",
    "city": "Jakarta Selatan",
    "province": "DKI Jakarta",
    "floor_area_m2": 3500.0,
    "floor_count": 8.0,
    "building_function": "Perkantoran",
    "permit_status": "Aktif",
    "issue_date": "2024-01-15",
    "valid_until": "2029-01-15",
    "issuing_authority": "DPMPTSP DKI Jakarta",
    "coordinates": "-6.2427,106.7989",
    "latitude": "-6.2427",
    "longitude": "106.7989",
    "portal_errors": [],
    "total_results": 1
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://simbg.pu.go.id/api/v1",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "simbg",
  "raw": {
    "portals_queried": 5,
    "national_results": 1
  }
}
```

---

## Known Issues & Quirks

- Results are deduplicated by `permit_number`; if multiple permits match, the first is returned
- Regional portals occasionally have different schemas; the normalizer handles common variations
- `floor_area_m2` and `floor_count` are coerced to float with commas replaced by dots
- Legacy IMB (Izin Mendirikan Bangunan) fields are mapped to PBG equivalents
- Coordinates may be in various formats; normalizer extracts both lat and lon when available
- Some permits lack owner names or coordinates — these fields are optional

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Active PBG found across all portals |
| TBD | Permit not found |
| TBD | Partial results (2 portals down) |

---

## Legal Basis

This module queries SIMBG's public APIs (national and regional) that publish building permit data
for transparency and public access purposes. No authentication is required. Data is fetched on
demand and not persisted. Scraping is conducted at low rates consistent with normal API usage
(0.5 req/s across all portals). Owner names published in permits are public records as required
by Indonesian building permit regulations.
