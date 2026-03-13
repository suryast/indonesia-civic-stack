# Module: `bps`

**Source portal:** webapi.bps.go.id
**Scrape method:** REST API with authentication key (free registration required)
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://webapi.bps.go.id/v1/api` |
| Operator | Badan Pusat Statistik (BPS — Statistics Indonesia) |
| Data type | 1,000+ official statistical datasets — economic indicators, demographic data, regional statistics |
| Auth required | **BPS_API_KEY** environment variable (free registration at webapi.bps.go.id/developer/register) |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~2 req/s |
| Block trigger | Unknown — API is well-designed |
| Block type | 401 Unauthorized if API key is invalid |
| Mitigation | Built-in token-bucket rate limiter (2 req/s) |
| IP rotation needed | Not required |

**Setup:** Set `BPS_API_KEY` environment variable with your registered key. Without it, the module raises `EnvironmentError` with registration instructions.

---

## Normalized Schema (`result` object)

### Dataset/subject search

```python
{
    "subject_id": str,               # BPS subject ID
    "subject_name": str,             # Subject name in Indonesian
    "category_id": str | None,       # Category ID
    "category_name": str | None,     # Category name
    "records_unavailable": int | None, # Number of unavailable records
}
```

### Indicator time-series

```python
{
    "indicator_id": str,             # BPS variable/indicator ID
    "region_code": str,              # Wilayah code (0000 = national)
    "table_id": str | None,          # Internal table ID
    "title": str | None,             # Indicator title
    "note": str | None,              # Explanatory notes
    "last_updated": str | None,      # ISO 8601 timestamp
    "record_count": int | None,      # Number of data points
    "time_series": list[dict],       # [{"period": "2020", "value": 123.45}, ...]
}
```

### Region list

```python
{
    "region_code": str,              # BPS wilayah code
    "region_name": str,              # Region name
    "level": str | None,             # Administrative level
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `search_bps_datasets` | `(keyword: str) -> list[dict]` | Search datasets by keyword |
| `get_bps_indicator` | `(indicator_id: str, region_code: str, year_range: str?) -> dict` | Get time-series data for indicator |
| `list_bps_regions` | `(parent_code: str) -> list[dict]` | List regional codes (wilayah) |

### claude mcp add

```bash
export BPS_API_KEY=your_key_here
claude mcp add bps -- python -m modules.bps.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/bps/dataset/{subject_id}` | Fetch dataset by subject ID |
| `GET` | `/bps/search?q=keyword` | Search datasets |
| `GET` | `/bps/indicator/{indicator_id}?region=...&years=...` | Get indicator time-series |
| `GET` | `/bps/regions?parent=...` | List regional codes |

---

## Example Response (Indicator)

```json
{
  "result": {
    "indicator_id": "570",
    "region_code": "0000",
    "table_id": "GDP-001",
    "title": "Produk Domestik Bruto (PDB)",
    "note": "Dalam miliar rupiah",
    "last_updated": "2024-08-15T00:00:00Z",
    "record_count": 10,
    "time_series": [
      {"period": "2020", "value": 15434.2},
      {"period": "2021", "value": 16970.8},
      {"period": "2022", "value": 19588.4},
      {"period": "2023", "value": 20892.4},
      {"period": "2024", "value": 22135.1}
    ]
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://webapi.bps.go.id",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": "2024-08-15T00:00:00Z",
  "module": "bps",
  "raw": null
}
```

---

## Known Issues & Quirks

- **Requires BPS_API_KEY:** Register for free at webapi.bps.go.id/developer/register
- Region code "0000" returns national aggregates; province codes are 2-digit (e.g. "31" = DKI Jakarta)
- Some indicators have missing values represented as "-" or "" — normalized to `null`
- Time series are sorted by period ascending
- Dataset keyword search uses Indonesian language only
- The API returns JSON with mixed camelCase and snake_case keys — the normalizer handles both

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Dataset search results |
| TBD | Indicator time-series (GDP national) |
| TBD | Region list (provinces) |

---

## Legal Basis

This module queries BPS's official open data API, which publishes statistical datasets for
public access as mandated by Indonesian open data policies. Authentication is required
(free API key) for rate limiting and usage tracking purposes. Data is fetched on demand
and not persisted. No personal data is accessed — all data is aggregate statistical information.
