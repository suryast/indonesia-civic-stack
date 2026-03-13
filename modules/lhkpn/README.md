# Module: `lhkpn`

**Source portal:** elhkpn.kpk.go.id
**Scrape method:** REST API (search + detail) + pdfplumber + Claude Vision API fallback for PDF extraction
**Phase:** 3
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://elhkpn.kpk.go.id/portal/user/check_a_lhkpn` |
| Operator | Komisi Pemberantasan Korupsi (KPK RI) |
| Data type | LHKPN (Laporan Harta Kekayaan Penyelenggara Negara) — public official wealth declarations |
| Auth required | None — public search tier |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~0.25 req/s (1 req per 4 seconds) |
| Block trigger | Unknown — needs testing |
| Block type | TBD (portal is conservative) |
| Mitigation | Built-in token-bucket rate limiter (0.25 req/s) |
| IP rotation needed | Not required for normal use; supply `proxy_url` for bulk scraping |

---

## Normalized Schema (`result` object)

```python
{
    "official_name": str,                      # Full name of public official
    "position": str | None,                    # Current position/jabatan
    "ministry": str | None,                    # Instansi/ministry
    "work_unit": str | None,                   # Satuan kerja
    "declaration_year": int | None,            # Year of declaration
    "submission_date": str | None,             # Date submitted
    "declaration_period": str | None,          # Reporting period
    "report_type": str | None,                 # Jenis laporan (annual/periodic)
    "report_number": str | None,               # Official report number
    "report_id": str,                          # Internal KPK report ID
    "total_assets_idr": int | None,            # Total harta in IDR
    "total_liabilities_idr": int | None,       # Total hutang in IDR
    "net_assets_idr": int | None,              # Harta bersih (assets - liabilities)
    "asset_breakdown": {
        "immovable_property_idr": int | None,  # Harta tidak bergerak (land, buildings)
        "movable_property_idr": int | None,    # Harta bergerak (vehicles, goods)
        "securities_idr": int | None,          # Surat berharga (stocks, bonds)
        "cash_idr": int | None,                # Kas & setara kas
        "other_assets_idr": int | None,        # Harta lainnya
    },
    "income_from_position_idr": int | None,    # Penghasilan dari jabatan
    "other_income_idr": int | None,            # Penghasilan lainnya
}
```

**IDR parsing:** All monetary values are parsed to int (removing "Rp", commas, dots).

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `get_lhkpn` | `(official_name: str) -> dict` | Look up latest wealth declaration by name |
| `search_lhkpn` | `(ministry_or_name: str) -> list[dict]` | Search officials by name, ministry, or position |
| `compare_lhkpn` | `(official_id: str, year_a: int, year_b: int) -> dict` | Compare declarations across years — returns delta |
| `get_lhkpn_pdf` | `(report_id: str) -> dict` | Download & extract PDF (requires `[pdf]` extra) |

### claude mcp add

```bash
claude mcp add lhkpn -- python -m modules.lhkpn.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/lhkpn/official/{name}` | Look up official's latest declaration |
| `GET` | `/lhkpn/search?q=keyword` | Search officials |
| `GET` | `/lhkpn/compare?official_id=...&year_a=...&year_b=...` | Compare declarations |

---

## Example Response

```json
{
  "result": {
    "official_name": "DR. H. PRABOWO SUBIANTO, M.Si.",
    "position": "Presiden Republik Indonesia",
    "ministry": "Istana Kepresidenan",
    "declaration_year": 2024,
    "submission_date": "2024-12-15",
    "report_type": "Tahunan",
    "report_id": "LHKPN-001234",
    "total_assets_idr": 150000000000,
    "total_liabilities_idr": 5000000000,
    "net_assets_idr": 145000000000,
    "asset_breakdown": {
      "immovable_property_idr": 80000000000,
      "movable_property_idr": 20000000000,
      "securities_idr": 30000000000,
      "cash_idr": 15000000000,
      "other_assets_idr": 5000000000
    },
    "income_from_position_idr": 2400000000,
    "other_income_idr": 500000000
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://elhkpn.kpk.go.id/portal/user/check_a_lhkpn",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "lhkpn",
  "raw": {
    "report_id": "LHKPN-001234"
  }
}
```

---

## Known Issues & Quirks

- PDF extraction requires `pip install 'indonesia-civic-stack[pdf]'` (pdfplumber + anthropic)
- Text-layer PDFs are processed with pdfplumber (fast); scanned/image PDFs fall back to Claude Vision API (slow, requires `ANTHROPIC_API_KEY`)
- Some older declarations have incomplete data or missing asset breakdowns
- Net assets are computed as `total_assets - total_liabilities` if not explicitly provided
- The portal occasionally returns duplicate entries for the same official with different report IDs
- Confidence scoring: exact name match = 1.0, partial match = 0.9, word overlap = 0.5-0.9

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| TBD | Active declaration found |
| TBD | Official not found |
| TBD | Search results with 5 officials |
| TBD | Compare declarations across 2 years |

---

## Legal Basis

This module queries KPK's public LHKPN portal, which publishes wealth declarations for
transparency and anti-corruption monitoring purposes as mandated by Indonesian law (UU No. 28/1999).
No authentication is required for public search. Data is fetched on demand and not persisted.
All data is voluntarily disclosed by public officials as required by law.
