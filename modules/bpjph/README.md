# Module: `bpjph`

**Source portal:** sertifikasi.halal.go.id (SiHalal)
**Scrape method:** Playwright + Camoufox fingerprint randomization (JS-rendered)
**Phase:** 1
**License:** Apache-2.0
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://sertifikasi.halal.go.id/sertifikat/publik` |
| Operator | Badan Penyelenggara Jaminan Produk Halal (BPJPH), Kemenag RI |
| Data type | Halal certificates — food, cosmetics, pharmaceutical, services |
| Auth required | None — public certificate lookup |
| Last verified | 2026-03-01 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~5 req/min (JS rendering is slow) |
| Block trigger | Rapid repeated Playwright sessions |
| Block type | Cloudflare Bot Management challenge |
| Mitigation | Camoufox fingerprint randomization; random viewport/UA rotation |
| IP rotation needed | Recommended for bulk use — supply `proxy_url` |

### Camoufox setup

```bash
pip install camoufox
python -m camoufox fetch  # downloads browser binary
```

If camoufox is not installed, the module falls back to standard Playwright.

---

## Normalized Schema (`result` object)

```python
{
    "cert_no": str,             # e.g. "ID00110019882120240001"
    "company": str,             # Registrant company name
    "product_list": list[str],  # List of certified products
    "issuer": str,              # "BPJPH" or "MUI" (pre-2023 certs)
    "inspection_body": str,     # e.g. "LPPOM MUI"
    "issue_date": str | None,   # ISO 8601
    "expiry_date": str | None,  # ISO 8601
    "status": str,              # ACTIVE | EXPIRED | REVOKED | SUSPENDED
}
```

**Certificate number format:**
- Post-2023 (BPJPH issued): `ID001XXXXXXXXXXXXXX`
- Pre-2023 (MUI issued): various formats, e.g. `01221001820317`

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `check_halal_cert` | `(cert_no: str) -> dict` | Single cert lookup by number |
| `lookup_halal_by_product` | `(product_name: str) -> list[dict]` | Search by product name |
| `get_halal_status` | `(company_name: str) -> list[dict]` | All certs for a company |
| `cross_reference_halal_bpom` | `(product_name: str) -> dict` | BPJPH × BPOM cross-reference |

### claude mcp add

```bash
claude mcp add bpjph -- python -m modules.bpjph.server
```

---

## Cross-Reference with BPOM

The `cross_ref_bpom()` function and `/bpjph/cross-ref` endpoint run a BPJPH lookup and a
BPOM lookup in parallel for the same product name. It flags:

- **BPOM ACTIVE, halal cert EXPIRED** — product is registered but halal certification has lapsed
- **Halal cert ACTIVE, BPOM EXPIRED** — halal cert is valid but BPOM registration has lapsed

This is the primary HalalKah verification pattern.

---

## VCR / Test Fixtures

Playwright sessions cannot be VCR-recorded directly. Tests use HTML fixtures injected
via monkeypatching of the `browser.new_page()` context manager.

| Fixture | Scenario |
|---|---|
| `tests/bpjph/fixtures/cert_found.html` | Active certificate detail page |
| `tests/bpjph/fixtures/cert_not_found.html` | No results / empty state |
| `tests/bpjph/fixtures/search_results.html` | Search results table with 2 rows |

---

## Legal Basis

Halal certificate data is publicly published by BPJPH on the SiHalal portal for consumer
information purposes. No authentication is required. Data is fetched on demand and not
persisted. Scraping is conducted at low rates consistent with normal human browsing.
