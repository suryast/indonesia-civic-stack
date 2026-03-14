# Module: `ojk`

**Source portal:** api.ojk.go.id (REST API) + investor.ojk.go.id (Waspada Investasi)
**Scrape method:** REST wrapper + httpx fallback for portal HTML
**Phase:** 2
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://api.ojk.go.id/v1/lembaga` (primary) + `https://investor.ojk.go.id/InvestorAlert` (waspada) |
| Operator | Otoritas Jasa Keuangan (OJK RI) |
| Data type | Licensed financial institution registry — banks, fintech, insurance, pension funds, investment managers, securities firms |
| Auth required | None — public API |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~30 req/min (~0.5 req/s) |
| Block trigger | Unknown — API is stable |
| Block type | TBD — needs testing |
| Mitigation | Built-in token-bucket rate limiter |
| IP rotation needed | Not required for normal use; supply `proxy_url` for bulk scraping |

---

## Normalized Schema (`result` object)

```python
{
    "institution_name": str,           # e.g. "PT AKULAKU FINANCE INDONESIA"
    "license_no": str,                 # e.g. "KEP-249/NB.11/2018"
    "institution_type": str,           # e.g. "fintech-pendanaan", "bank-umum"
    "license_status": str,             # ACTIVE | EXPIRED | REVOKED | SUSPENDED
    "regulated_products": list[str],   # Products/services the institution is licensed for
    "domicile": str | None,            # City/region
    "website": str | None,             # Institution website
    "on_waspada_list": bool,           # True if on investment alert list
}
```

**Institution types:**
- `bank-umum` — Commercial banks
- `bpr` — Rural banks (Bank Perkreditan Rakyat)
- `fintech-pendanaan` — Peer-to-peer lending platforms
- `fintech-pembayaran` — Payment gateway providers
- `asuransi` — Insurance companies
- `dana-pensiun` — Pension funds
- `manajer-investasi` — Investment managers
- `perusahaan-efek` — Securities firms

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `check_ojk_license` | `(name_or_id: str) -> dict` | Single institution lookup by name or license number |
| `search_ojk_institutions` | `(keyword: str, institution_type: str?) -> list[dict]` | Multi-result search with optional type filter |
| `get_ojk_status` | `(name_or_id: str) -> dict` | Status-only lookup (lighter weight) |
| `check_ojk_waspada` | `(entity_name: str) -> dict` | Check if entity is on investment alert list |

### claude mcp add

```bash
claude mcp add ojk -- python -m modules.ojk.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/ojk/check/{name_or_id}` | Single institution lookup |
| `GET` | `/ojk/search?q=keyword&institution_type=...&status=...` | Multi-result search with filters |
| `GET` | `/ojk/status/{name_or_id}` | Status-only lookup |
| `GET` | `/ojk/waspada?q=entity_name` | Check investment alert list |

---

## Example Response

```json
{
  "result": {
    "institution_name": "PT AKULAKU FINANCE INDONESIA",
    "license_no": "KEP-249/NB.11/2018",
    "institution_type": "fintech-pendanaan",
    "license_status": "ACTIVE",
    "regulated_products": [
      "Pendanaan Bersama Berbasis Teknologi Informasi",
      "P2P Lending"
    ],
    "domicile": "Jakarta Selatan",
    "website": "https://akulaku.com",
    "on_waspada_list": false
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://api.ojk.go.id/v1/lembaga/pencarian",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "ojk",
  "raw": null
}
```

---

## Known Issues & Quirks

- The API sometimes returns duplicate records for the same institution with different license numbers — this is expected when institutions have multiple licenses for different product types
- Waspada Investasi entities are flagged with `status: SUSPENDED` and `on_waspada_list: true`
- The portal HTML fallback is used only when the API returns no results (rare)
- License status mapping: "aktif", "izin usaha", "beroperasi" → ACTIVE; "dicabut", "likuidasi" → REVOKED; "pembekuan", "dibekukan" → SUSPENDED; "tidak aktif" → EXPIRED

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| `tests/ojk/cassettes/institution_found.yaml` | Active institution — Akulaku fintech |
| `tests/ojk/cassettes/institution_not_found.yaml` | No results for keyword |
| `tests/ojk/cassettes/waspada_found.yaml` | Entity on investment alert list |

---

## Legal Basis

This module fetches data from OJK's public REST API and the Waspada Investasi portal, both of which
publish licensed institution data for consumer protection purposes. No authentication is required.
Data is fetched on demand and not persisted by this library. Scraping is conducted at low request
rates consistent with normal API usage. No personal data beyond what is voluntarily published on
the public portal is accessed.
