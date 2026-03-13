# Module: `ahu`

**Source portal:** ahu.go.id (Sistem Administrasi Badan Usaha, Kemenkumham)
**Scrape method:** Playwright + Camoufox + Cloudflare Worker routing
**Phase:** 1
**License:** Apache-2.0
**Status:** ACTIVE

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://ahu.go.id/pencarian/perseroan-terbatas` |
| Operator | Kementerian Hukum dan HAM (Kemenkumham) RI |
| Data type | Company registrations — PT, CV, Yayasan, Koperasi, Firma |
| Auth required | None — public search for basic company data |
| Last verified | 2026-03-01 |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | ~3 req/min |
| Block trigger | Datacenter IPs detected immediately by Cloudflare Bot Management |
| Block type | CF Bot Management challenge / JS challenge page |
| Mitigation | Cloudflare Worker routing (mandatory) + Camoufox |
| IP rotation needed | **Yes** — this module will not work from datacenter IPs without proxy |

### IP Block Mitigation — Cloudflare Worker Setup

Deploy a Cloudflare Worker that proxies requests through CF edge IPs:

```javascript
// worker.js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = "ahu.go.id";
    return fetch(url.toString(), request);
  }
}
```

Then pass your Worker URL as `proxy_url`:

```python
from modules.ahu import fetch

resp = await fetch("PT Contoh Indonesia", proxy_url="https://your-worker.workers.dev")
```

### Camoufox setup

```bash
pip install camoufox
python -m camoufox fetch
```

---

## Normalized Schema (`result` object)

```python
{
    "company_name": str,           # Full company name in uppercase
    "registration_no": str,        # AHU registration number
    "deed_date": str | None,       # ISO 8601 deed/registration date
    "legal_form": str,             # "Perseroan Terbatas (PT)" | "CV" | "Yayasan" | etc.
    "legal_status": str,           # ACTIVE | REVOKED | SUSPENDED | EXPIRED
    "domicile": str | None,        # City/province
    "business_activities": str | None,
    "authorized_capital": str | None,
    "paid_up_capital": str | None,
    "directors": [                  # Direksi
        {"nama": str, "jabatan": str, "npwp": str | None}
    ],
    "commissioners": [              # Dewan Komisaris
        {"nama": str, "jabatan": str}
    ],
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `lookup_company_ahu` | `(name_or_id: str, proxy_url?: str) -> dict` | Full company record |
| `get_company_directors` | `(company_id: str, proxy_url?: str) -> dict` | Directors + commissioners |
| `verify_company_status` | `(company_id: str, proxy_url?: str) -> dict` | Legal status + deed date |
| `search_companies_ahu` | `(keyword: str, proxy_url?: str) -> list[dict]` | Multi-result search |

### claude mcp add

```bash
claude mcp add ahu -- python -m modules.ahu.server
```

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/ahu/company/{query}` | Full company lookup |
| `GET` | `/ahu/company/{id}/directors` | Directors and commissioners |
| `GET` | `/ahu/company/{id}/status` | Legal status only |
| `GET` | `/ahu/search?q=keyword` | Multi-result search |

---

## Example Response

```json
{
  "result": {
    "company_name": "PT CONTOH INDONESIA TBK",
    "registration_no": "AHU-0012345.AH.01.01.TAHUN2020",
    "deed_date": "2020-03-15T00:00:00",
    "legal_form": "Perseroan Terbatas (PT)",
    "legal_status": "ACTIVE",
    "domicile": "Jl. Sudirman Kav. 52-53, Jakarta Pusat, DKI Jakarta",
    "directors": [
      {"nama": "BUDI SANTOSO", "jabatan": "Direktur Utama"},
      {"nama": "SARI DEWI", "jabatan": "Direktur"}
    ],
    "commissioners": [
      {"nama": "AHMAD YUSUF", "jabatan": "Komisaris Utama"}
    ]
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://ahu.go.id/pencarian/perseroan-terbatas",
  "fetched_at": "2026-03-01T10:00:00Z",
  "module": "ahu"
}
```

---

## Test Fixtures

| Fixture | Scenario |
|---|---|
| `tests/ahu/fixtures/company_found.html` | Active PT with directors and commissioners |
| `tests/ahu/fixtures/company_not_found.html` | No results / empty state |
| `tests/ahu/fixtures/search_results.html` | Search results table (3 companies) |

---

## Known Issues & Quirks

- AHU blocks datacenter IPs — a Cloudflare Worker proxy is mandatory in production.
- The portal occasionally times out for companies with large numbers of directors.
  Implement a retry in these cases.
- Director NPWP fields may be omitted from public view — the module returns `null` for these.
- The portal URL structure has changed twice since 2020. If the module degrades,
  first check if the search URL path has been updated.

---

## Legal Basis

AHU company registration data is published by Kemenkumham for public access per Government
Regulation (PP) No. 24 Tahun 2022 on company transparency. Basic company data (name,
registration number, status) is a matter of public record. Directors and commissioners
are public figures in their corporate capacity. Data is fetched on demand and not stored.
