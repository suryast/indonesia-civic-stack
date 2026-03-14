# Module: `bpom`

**Source portal:** cekbpom.pom.go.id
**Scrape method:** httpx + BeautifulSoup (static HTML)
**Phase:** 1
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://cekbpom.pom.go.id` |
| Operator | Badan Pengawas Obat dan Makanan (BPOM RI) |
| Data type | Product registrations — food, drugs, cosmetics, traditional medicine |
| Auth required | None — public search |
| Last verified | 2026-03-01 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~10 req/min (~0.15 req/s) |
| Block trigger | >20 req/min sustained from same IP |
| Block type | Cloudflare 403 or silent timeout |
| Mitigation | Built-in token-bucket rate limiter + exponential backoff |
| IP rotation needed | Not required for normal use; supply `proxy_url` for bulk scraping |

---

## Normalized Schema (`result` object)

```python
{
    "registration_no": str,        # e.g. "BPOM MD 123456789012"
    "product_name": str,           # Full product name in uppercase
    "brand_name": str | None,      # Trade name / Nama Dagang
    "category": str | None,        # e.g. "Pangan Olahan", "Obat Bebas"
    "company": str,                # Registrant company name
    "company_address": str | None, # Registrant address
    "company_npwp": str | None,    # NPWP if available
    "registration_status": str,    # ACTIVE | EXPIRED | REVOKED | SUSPENDED
    "expiry_date": str | None,     # ISO 8601, e.g. "2027-12-31T00:00:00"
    "valid_from": str | None,      # ISO 8601
}
```

**Registration number prefixes:**
- `BPOM MD` — domestically manufactured food
- `BPOM ML` — imported food
- `BPOM GKL` — generic drug
- `BPOM GTL` — traditional medicine
- `BPOM NA` — cosmetics (domestic)
- `BPOM NB` — cosmetics (imported)

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `check_bpom` | `(registration_no: str) -> dict` | Single product lookup by registration number |
| `search_bpom` | `(product_name: str) -> list[dict]` | Multi-result product name search |
| `get_bpom_status` | `(registration_no: str) -> dict` | Status + expiry only (lighter) |

### claude mcp add

```bash
claude mcp add bpom -- python -m modules.bpom.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/bpom/check/{registration_no}` | Single product lookup |
| `GET` | `/bpom/search?q=keyword` | Multi-result search |
| `GET` | `/bpom/status/{registration_no}` | Status-only lookup |

---

## Example Response

```json
{
  "result": {
    "registration_no": "BPOM MD 123456789012",
    "product_name": "MIE GORENG SPESIAL RASA AYAM",
    "brand_name": "SuperMie Goreng",
    "category": "Pangan Olahan",
    "company": "PT INDOFOOD SUKSES MAKMUR TBK",
    "company_address": "Jl. Jend. Sudirman Kav. 76-78, Jakarta Selatan",
    "registration_status": "ACTIVE",
    "expiry_date": "2027-12-31T00:00:00"
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://cekbpom.pom.go.id/index.php/home/produk/0/BPOM%20MD%20123456789012/10/1/0",
  "fetched_at": "2026-03-01T10:00:00Z",
  "last_updated": "2027-12-31T00:00:00",
  "module": "bpom",
  "raw": null
}
```

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| `tests/bpom/cassettes/found.yaml` | Active product — exact registration number match |
| `tests/bpom/cassettes/not_found.yaml` | Registration number not in database |
| `tests/bpom/cassettes/expired.yaml` | Product found but registration expired |
| `tests/bpom/cassettes/search_multi.yaml` | Keyword search returning 3 results |

---

## Known Issues & Quirks

- The portal occasionally returns `TIDAK AKTIF` for both `EXPIRED` and `SUSPENDED` states.
  The normalizer maps both to `EXPIRED`; if granularity is needed, check `expiry_date`.
- Registration numbers can be formatted as `BPOM MD 123456789012` or `MD 123456789012`
  (with/without prefix). The scraper normalizes both.
- The portal does not return `last_updated` — only `expiry_date` is available.

---

## Legal Basis

Data is fetched from a publicly accessible government portal with no authentication requirement.
BPOM product registrations are public records published for consumer safety purposes.
Fetching is performed at low rates consistent with normal user browsing.
No personal data beyond what is voluntarily published on the public portal is accessed or stored.
