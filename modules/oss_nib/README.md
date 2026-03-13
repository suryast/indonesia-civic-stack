# Module: `oss_nib`

**Source portal:** oss.go.id/informasi/pencarian-nib
**Scrape method:** Playwright (React SPA)
**Phase:** 2
**License:** MIT
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://oss.go.id/informasi/pencarian-nib` |
| Operator | OSS RBA (Online Single Submission Risk-Based Approach), BKPM RI |
| Data type | Business registration — NIB (Nomor Induk Berusaha), KBLI codes, risk levels |
| Auth required | None — public search tier |
| Last verified | 2026-03-13 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~5 req/min (React SPA rendering is slow) |
| Block trigger | Unknown — needs testing |
| Block type | TBD (likely Cloudflare challenge for rapid automation) |
| Mitigation | Camoufox fingerprint randomization (via shared bpjph browser module) |
| IP rotation needed | Recommended for bulk use — supply `proxy_url` |

---

## Normalized Schema (`result` object)

```python
{
    "nib": str,                   # 13-digit Nomor Induk Berusaha
    "company_name": str,          # Registered business name
    "business_type": str | None,  # Business classification description
    "kbli_code": str | None,      # Klasifikasi Baku Lapangan Usaha Indonesia code
    "risk_level": str | None,     # "rendah" | "menengah rendah" | "menengah tinggi" | "tinggi"
    "license_status": str,        # ACTIVE | EXPIRED | REVOKED | SUSPENDED
    "domicile": str | None,       # City/province
    "issue_date": str | None,     # ISO 8601 date when NIB was issued
}
```

**Risk level classification:**
- `rendah` — Low risk
- `menengah rendah` — Medium-low risk
- `menengah tinggi` — Medium-high risk
- `tinggi` — High risk

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `lookup_nib` | `(company_name: str, proxy_url: str?) -> dict` | Look up business by company name |
| `verify_nib` | `(nib_number: str, proxy_url: str?) -> dict` | Verify NIB number and return status (lighter) |
| `search_oss_businesses` | `(keyword: str, proxy_url: str?) -> list[dict]` | Multi-result company name search |

### claude mcp add

```bash
claude mcp add oss_nib -- python -m modules.oss_nib.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/oss-nib/nib/{query}` | Look up by NIB number or company name |
| `GET` | `/oss-nib/search?q=keyword` | Multi-result search |
| `GET` | `/oss-nib/verify/{nib_number}` | Verify NIB number status (lighter) |

---

## Example Response

```json
{
  "result": {
    "nib": "1234567890123",
    "company_name": "PT GOJEK INDONESIA",
    "business_type": "Perdagangan Elektronik",
    "kbli_code": "63121",
    "risk_level": "menengah rendah",
    "license_status": "ACTIVE",
    "domicile": "Jakarta Selatan",
    "issue_date": "2021-05-15T00:00:00"
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://oss.go.id/informasi/pencarian-nib",
  "fetched_at": "2026-03-13T10:00:00Z",
  "last_updated": null,
  "module": "oss_nib",
  "raw": null
}
```

---

## Known Issues & Quirks

- The OSS portal is a React SPA — Playwright is required (httpx will only get the shell HTML)
- Search input selector varies across OSS redesigns; the scraper tries 5 fallback selectors
- Risk level field is sometimes missing for older NIB records
- KBLI codes can have multiple values; currently the scraper captures the first one only
- The portal occasionally shows "status: tidak aktif" for both EXPIRED and REVOKED — both are normalized to EXPIRED unless more context is available

---

## VCR Fixtures

Playwright sessions cannot be recorded as VCR cassettes. Tests use HTML fixture injection via monkeypatching.

| Fixture | Scenario |
|---|---|
| TBD | Active NIB record |
| TBD | NIB not found |
| TBD | Search results with 3 businesses |

---

## Legal Basis

This module scrapes publicly accessible data from OSS's public search tier with no login requirement.
NIB data is published by BKPM for business verification and transparency purposes. Fetching is performed
at low rates consistent with normal user browsing. No personal data beyond what is voluntarily published
on the public portal is accessed or stored.
