# Module: `lpse`

**Source portal:** lpse.lkpp.go.id/eproc4 + 4 other ministry portals
**Scrape method:** REST API wrapper (SPSE standardized API across all portals)
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://lpse.lkpp.go.id/eproc4` (primary) + 4 ministry portals |
| Operator | LKPP (Lembaga Kebijakan Pengadaan Barang/Jasa Pemerintah) |
| Data type | Government procurement — vendor registry, active tenders, contract awards |
| Auth required | None — public search tier |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~1 req/s (conservative across all 5 portals) |
| Block trigger | Unknown — needs testing |
| Block type | 429 Too Many Requests (observed on some portals) |
| Mitigation | Built-in token-bucket rate limiter (1 req/s) |
| IP rotation needed | Not required for normal use; supply `proxy_url` for bulk scraping |

---

## Aggregated Portals

This module queries 5 major LPSE portals in parallel and returns merged/deduplicated results:

| Portal | Base URL |
|---|---|
| LKPP | `https://lpse.lkpp.go.id/eproc4` |
| PU | `https://lpse.pu.go.id/eproc4` |
| Kominfo | `https://lpse.kominfo.go.id/eproc4` |
| Kemenkeu | `https://lpse.kemenkeu.go.id/eproc4` |
| Kemenkes | `https://lpse.kemenkes.go.id/eproc4` |

**Partial results:** If some portals are unreachable, the module returns data from successful portals with `confidence < 1.0` and records failures in `result["portal_errors"]`.

---

## Normalized Schema (`result` object)

### Vendor lookup

```python
{
    "vendor_id": str,                 # Internal SPSE vendor code
    "vendor_name": str,               # Registered company name
    "npwp": str | None,               # NPWP formatted as XX.XXX.XXX.X-XXX.XXX
    "address": str | None,            # Full address
    "city": str | None,               # City
    "province": str | None,           # Province
    "phone": str | None,              # Contact phone
    "email": str | None,              # Contact email
    "is_active": bool,                # True if vendor is active
    "business_type": str | None,      # Jenis usaha
    "qualification": str | None,      # Vendor qualification level
    "business_field": str | None,     # Bidang usaha
    "portal_errors": list[str],       # Names of portals that failed (if any)
    "total_results": int,             # Total records found (deduplicated by NPWP)
}
```

### Tender search

```python
{
    "tender_id": str,                 # Unique tender code
    "tender_name": str,               # Tender package name
    "procuring_entity": str,          # Satker (procuring entity) name
    "entity_code": str | None,        # Satker code
    "tender_stage": str | None,       # Current tender stage
    "procurement_method": str | None, # e.g. "Tender Cepat", "Pemilihan Langsung"
    "ceiling_value": float | None,    # Pagu (budget ceiling) in IDR
    "hps_value": float | None,        # HPS (owner's estimate) in IDR
    "created_date": str | None,       # Tender creation date
    "closing_date": str | None,       # Tender closing date
    "tender_status": str | None,      # Current status
    "funding_source": str | None,     # e.g. "APBN", "APBD"
    "tender_url": str | None,         # Direct link to tender detail page
    "portal_errors": list[str],       # Names of portals that failed (if any)
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `lookup_vendor_lpse` | `(query: str) -> dict` | Look up vendor by name or NPWP |
| `search_lpse_vendors` | `(keyword: str) -> list[dict]` | Search vendors across all portals |
| `search_lpse_tenders` | `(keyword: str) -> list[dict]` | Search active tenders by keyword |
| `get_lpse_portals` | `() -> list[dict]` | List all monitored LPSE portals |

### claude mcp add

```bash
claude mcp add lpse -- python -m modules.lpse.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/lpse/vendor/{query}` | Look up vendor by name or NPWP |
| `GET` | `/lpse/search?q=keyword` | Search vendors |
| `GET` | `/lpse/tenders?q=keyword` | Search active tenders |

---

## Example Response (Vendor)

```json
{
  "result": {
    "vendor_id": "123456",
    "vendor_name": "PT GOJEK INDONESIA",
    "npwp": "01.234.567.8-901.000",
    "address": "Jl. Iskandarsyah II No. 7, Kebayoran Baru",
    "city": "Jakarta Selatan",
    "province": "DKI Jakarta",
    "phone": "021-55555555",
    "email": "procurement@gojek.com",
    "is_active": true,
    "business_type": "Perseroan Terbatas",
    "qualification": "Kecil",
    "business_field": "Jasa Teknologi Informasi",
    "portal_errors": [],
    "total_results": 1
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://lpse.lkpp.go.id/eproc4/dt/rekanan",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "lpse",
  "raw": {
    "portals_queried": 5,
    "portals_succeeded": 5
  }
}
```

---

## Known Issues & Quirks

- NPWP normalization removes spaces and formats as XX.XXX.XXX.X-XXX.XXX
- Some portals are occasionally unreachable — the module returns partial results with `confidence < 1.0` and records failures in `portal_errors`
- Results are deduplicated by NPWP (for vendors) and tender_id (for tenders)
- Numeric fields (ceiling_value, hps_value) are coerced to float with commas/dots removed
- The SPSE API is standardized but response times vary across portals

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Active vendor found across all portals |
| TBD | Vendor not found |
| TBD | Partial results (2 portals down) |
| TBD | Tender search results |

---

## Legal Basis

This module queries public LPSE portals that publish government procurement data for
transparency and vendor participation. No authentication is required. Data is fetched
on demand and not persisted. Scraping is conducted at low rates consistent with normal
API usage (1 req/s across all portals). No personal data beyond what is voluntarily
published on the public portal is accessed.
