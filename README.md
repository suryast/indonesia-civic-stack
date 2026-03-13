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
| `lhkpn` | elhkpn.kpk.go.id | Wealth declarations (officials) | 🔜 Phase 3 |
| `bps` | bps.go.id | Statistical datasets (1,000+) | 🔜 Phase 3 |
| `bmkg` | bmkg.go.id | Disaster and weather data | 🔜 Phase 3 |

Every module returns the same response envelope regardless of source — swap data sources without touching application logic.

---

## Quick Start

### Python library

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
