# indonesia-civic-stack

Production-ready scrapers, normalizers, and API wrappers for Indonesian government data sources.

The infrastructure layer beneath [halalkah.id](https://halalkah.id), [legalkah.id](https://legalkah.id), [nabung.id](https://nabung.id), and a public good for the Indonesian civic tech and developer community.

---

## Why

Indonesian public data is nominally open but practically inaccessible.

Every developer building civic tooling re-solves the same scraping problems independently: BPOM product registrations, BPJPH halal certificates, AHU company records. Scrapers bit-rot within months as portals change. There is no shared, maintained layer.

This repo is that layer.

---

## What

| Module | Source | Data | Status |
|---|---|---|---|
| [`bpom`](modules/bpom/README.md) | cekbpom.pom.go.id | Food, drug, cosmetic, traditional medicine registrations | ✅ Phase 1 |
| [`bpjph`](modules/bpjph/README.md) | sertifikasi.halal.go.id | Halal certificates (BPJPH + MUI) | ✅ Phase 1 |
| [`ahu`](modules/ahu/README.md) | ahu.go.id | Company registry — PT, CV, Yayasan, Koperasi | ✅ Phase 1 |
| [`ojk`](modules/ojk/README.md) | ojk.go.id | Licensed financial institutions + Waspada list | ✅ Phase 2 |
| [`oss-nib`](modules/oss-nib/README.md) | oss.go.id | Business identity (NIB) | ✅ Phase 2 |
| [`lpse`](modules/lpse/README.md) | lpse.*.go.id | Government procurement (5 major portals) | ✅ Phase 2 |
| [`kpu`](modules/kpu/README.md) | kpu.go.id | Election data — candidates, results, finance | ✅ Phase 2 |
| [`lhkpn`](modules/lhkpn/README.md) | elhkpn.kpk.go.id | Wealth declarations (officials) — PDF + Vision | ✅ Phase 3 |
| [`bps`](modules/bps/README.md) | webapi.bps.go.id | Statistical datasets (1,000+) | ✅ Phase 3 |
| [`bmkg`](modules/bmkg/README.md) | data.bmkg.go.id | Earthquakes, weather forecasts, disaster alerts | ✅ Phase 3 |
| [`simbg`](modules/simbg/README.md) | simbg.pu.go.id | Building permits (PBG/IMB) — 5 pilot regions | ✅ Phase 3 |

Every module returns the same response envelope regardless of source — swap data sources without touching application logic.

---

## Quick Start

### Python library

# 🇮🇩 indonesia-civic-stack

Unified Python SDK for Indonesian government data — BPOM, BPJPH, AHU, and more. REST API + MCP servers for AI agents.

> One `pip install` to query Indonesian government portals. No more bespoke scrapers.

## Why

Indonesian government data is scattered across dozens of portals with inconsistent APIs, JS-rendered forms, and aggressive bot detection. Every civic tech project ends up writing its own scraper.

**civic-stack** wraps them all in a standard `CivicStackResponse` envelope with:
- **Normalized fields** — consistent naming across agencies
- **Rate limiting & retries** — built-in, per-portal tuned
- **MCP servers** — plug into Claude, ChatGPT, or any AI agent
- **FastAPI endpoints** — deploy as microservices
- **VCR test fixtures** — CI without hitting live portals

## Quick Start

```bash
pip install indonesia-civic-stack
```

```python
import asyncio
from modules.bpom import fetch as bpom_fetch
from modules.bpjph import fetch as bpjph_fetch, cross_ref_bpom
from modules.ahu import fetch as ahu_fetch

async def main():
    # Check a BPOM product registration
    product = await bpom_fetch("BPOM MD 123456789012")
    print(product.status)        # ACTIVE
    print(product.result["company"])  # PT INDOFOOD SUKSES MAKMUR TBK

    # Look up a halal certificate
    cert = await bpjph_fetch("ID00110019882120240001")
    print(cert.result["product_list"])  # ["MIE GORENG SPESIAL", ...]

    # Cross-reference: halal cert + BPOM registration together
    check = await cross_ref_bpom("mie goreng spesial")
    print(check["mismatch"])          # False (both active)
    print(check["mismatch_detail"])   # None

    # Verify a company
    company = await ahu_fetch("PT Contoh Indonesia", proxy_url="https://your-cf-worker.workers.dev")
    print(company.result["directors"])  # [{...}, ...]

asyncio.run(main())
```

### MCP server (AI agents)

Add any module as an MCP server that Claude and other AI agents can call directly:

```bash
# Add to Claude
claude mcp add bpom -- python -m modules.bpom.server
claude mcp add bpjph -- python -m modules.bpjph.server
claude mcp add ahu -- python -m modules.ahu.server

# Or run all modules as a unified HTTP server
uvicorn app:app --reload
# → API docs at http://localhost:8000/docs
```

Once added, agents can call tools like `check_bpom("BPOM MD 123456789012")` or
`cross_reference_halal_bpom("mie goreng spesial")` directly from Claude.

### Docker

```bash
# Single module
docker compose up bpom

# All Phase 1 modules
docker compose up

# Run tests
docker compose run --rm test
```

---

## Response Envelope

Every module returns the same `CivicStackResponse` shape:

```python
{
  "result":       {...},      # Normalized domain object (module-specific schema)
  "found":        True,       # Whether a record was located
  "status":       "ACTIVE",   # ACTIVE | EXPIRED | SUSPENDED | REVOKED | NOT_FOUND | ERROR
  "confidence":   1.0,        # 0–1, scraper confidence in result accuracy
  "source_url":   "https://cekbpom.pom.go.id/...",
  "fetched_at":   "2026-03-01T10:00:00Z",
  "last_updated": "2027-12-31T00:00:00Z",
  "module":       "bpom",
  "raw":          null        # Raw scraped data (only when debug=True)
}
```

Check `found` and `status` before reading `result`. Both `NOT_FOUND` and `ERROR` set `found=False`.

---

## Architecture

```
indonesia-civic-stack/
├── shared/
│   ├── schema.py      # CivicStackResponse envelope + RecordStatus enum
│   ├── http.py        # Rate limiting, retry, proxy routing
│   └── mcp.py         # CivicStackMCPBase — inherited by all MCP servers
├── modules/
│   ├── bpom/          # httpx + BeautifulSoup (static HTML)
│   ├── bpjph/         # Playwright + Camoufox (JS-rendered)
│   └── ahu/           # Playwright + Cloudflare Worker routing
├── tests/
│   ├── bpom/          # VCR cassettes
│   ├── bpjph/         # HTML fixtures + monkeypatched Playwright
│   └── ahu/           # HTML fixtures + monkeypatched Playwright
├── app.py             # Unified FastAPI app (all modules)
└── docker-compose.yml
```

| Layer | Technology | Why |
|---|---|---|
| Scraping (static) | httpx + BeautifulSoup | Fast, no browser overhead for static HTML |
| Scraping (dynamic) | Playwright + Camoufox | JS-rendered portals; fingerprint randomization |
| API framework | FastAPI | Auto-generated OpenAPI spec; async; one router per module |
| MCP layer | FastMCP | `claude mcp add` compatible; 3–5 tools per module |
| IP rotation | Cloudflare Workers | Routes scraper traffic through CF edge to avoid datacenter blocks |
| Testing | pytest + VCR.py | Record/replay HTTP fixtures; no live portal calls in CI |

---

## IP Block Mitigation

AHU and BPJPH use Cloudflare Bot Management. The mitigation stack:

1. **Cloudflare Worker routing** — route Playwright sessions through CF edge IPs.
   See [modules/ahu/README.md](modules/ahu/README.md) for Worker setup.
2. **Camoufox** — randomizes canvas, WebGL, user-agent, viewport per session.
   `pip install camoufox && python -m camoufox fetch`
3. **Rate limiting** — per-module token buckets cap request cadence.
4. **`proxy_url` parameter** — all modules accept a proxy URL so operators can
   supply their own residential pool for heavy workloads.

---

## Consumers

- **[halalkah.id](https://halalkah.id)** — uses `bpjph` + `bpom` for halal verification
- **AmanKah** — uses `bpom` for withdrawn product detection
- **SahKah / legalkah.id** — uses `ahu` + `ojk` (Phase 2)
- **DPR Watch** — uses `ahu` + `lhkpn` (Phase 3)

See [examples/halalkah/](examples/halalkah/) for a full integration walkthrough.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the module contract, contribution workflow,
and degradation policy.

The short version:
1. Every module needs `fetch()`, `search()`, an MCP server, VCR fixtures, and a README.
2. No live portal calls in CI — use VCR cassettes or HTML fixtures.
3. Modules that break and stay broken for 60 days are archived.

**Good first issues:** look for the [`good-first-issue`](../../labels/good-first-issue) label.
Phase 2 modules (OJK, OSS-NIB, LPSE, KPU) are all open for community contribution.

---

## Relationship to indonesia-gov-apis

[indonesia-gov-apis](https://github.com/suryast/indonesia-gov-apis) catalogued what exists
and why it matters. This repo is the code that actually runs against it.

| | indonesia-gov-apis | indonesia-civic-stack |
|---|---|---|
| Type | Catalogue | Code |
| Format | Markdown docs | Python packages + MCP servers |
| Use | Developer reference | Deployable civic infrastructure |

---

## License

Repository root and `shared/`: **MIT**. Per-module licenses vary — see [LICENSES.md](LICENSES.md).

Built and maintained by the [Kah series](https://halalkah.id) team and open to community contribution.
### Python SDK

```python
from modules.bpom import fetch, search

# Look up a single product by registration number
result = await fetch("BPOM MD 123456789012")
print(result.found)    # True
print(result.status)   # "ACTIVE"
print(result.result)   # {"product_name": "...", "company": "...", ...}

# Search by name
results = await search("paracetamol")
for r in results:
    print(r.result["product_name"], r.result["registration_status"])
```

### MCP Server (for AI agents)

```bash
# Add to Claude Desktop / any MCP client
claude mcp add civic-stack-bpom -- python -m modules.bpom.server

# Or run standalone
python -m modules.bpom.server
```

### REST API

```bash
# Run all modules
uvicorn app:app --port 8000

# Or individual module
uvicorn modules.bpom.app:app --port 8001
```

```
GET /bpom/check/MD123456789012
GET /bpom/search?q=paracetamol
GET /bpjph/check/BPJPH-12345
GET /ahu/search?q=PT+Contoh+Indonesia
```

## Modules

| Module | Source | Method | Status |
|--------|--------|--------|--------|
| **bpom** | [cekbpom.pom.go.id](https://cekbpom.pom.go.id) | httpx + BeautifulSoup | ✅ Phase 1 |
| **bpjph** | [sertifikasi.halal.go.id](https://sertifikasi.halal.go.id) | Playwright + Camoufox | ✅ Phase 1 |
| **ahu** | [ahu.go.id](https://ahu.go.id) | Playwright + CF Worker proxy | ✅ Phase 1 |
| **ojk** | OJK licensed institution registry | REST + scrape | 🔜 Phase 2 |
| **oss-nib** | [oss.go.id](https://oss.go.id) | Playwright | 🔜 Phase 2 |
| **lpse** | 500+ regional LPSE portals | Multi-portal scraper | 🔜 Phase 2 |
| **kpu** | KPU open data API | REST wrapper | 🔜 Phase 2 |
| **lhkpn** | KPK wealth declarations | pdfplumber + Vision | 🔜 Phase 3 |
| **bps** | BPS statistics API | REST wrapper | 🔜 Phase 3 |
| **bmkg** | BMKG disaster/weather API | REST wrapper | 🔜 Phase 3 |

## Response Envelope

Every module returns `CivicStackResponse`:

```json
{
  "result": {"product_name": "...", "registration_status": "ACTIVE", ...},
  "found": true,
  "status": "ACTIVE",
  "confidence": 0.95,
  "source_url": "https://cekbpom.pom.go.id/...",
  "fetched_at": "2026-03-13T12:00:00Z",
  "module": "bpom"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `result` | dict \| list | Normalized data payload |
| `found` | bool | Whether the query matched |
| `status` | enum | `ACTIVE`, `EXPIRED`, `NOT_FOUND`, `ERROR`, `DEGRADED`, `BLOCKED` |
| `confidence` | float | 0.0–1.0 data reliability score |
| `source_url` | str | Government portal URL queried |
| `module` | str | Which module produced this |

## Docker

```bash
# Run all modules
docker compose up

# Or individual
docker build -t civic-bpom modules/bpom/
docker run -p 8001:8000 civic-bpom
```

## Development

```bash
git clone https://github.com/suryast/indonesia-civic-stack.git
cd indonesia-civic-stack
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,playwright]"
playwright install chromium

# Run tests (VCR only — no live portal calls)
pytest -v

# Lint
ruff check .
mypy shared/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the module contract. Every PR must include:
- `fetch()` and `search()` returning `CivicStackResponse`
- FastAPI router + FastMCP server
- 3+ VCR test fixtures
- Module README

A module that breaks for **60 days** is flagged `DEGRADED` and archived.

## Used By

- [**halalkah.id**](https://halalkah.id) — Halal product verification (9.57M products)
- [**legalkah.id**](https://legalkah.id) — Financial institution legality checker

## Related

- [**indonesia-gov-apis**](https://github.com/suryast/indonesia-gov-apis) — Reference documentation for 50+ Indonesian government APIs

## License

MIT — see [LICENSE](LICENSE)
