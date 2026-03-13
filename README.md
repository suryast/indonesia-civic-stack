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
