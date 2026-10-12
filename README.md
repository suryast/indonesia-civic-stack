# 🇮🇩 indonesia-civic-stack

<!-- mcp-name: io.github.suryast/indonesia-civic-stack -->

[![PyPI](https://img.shields.io/pypi/v/indonesia-civic-stack?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/indonesia-civic-stack/)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.suryast-blue?style=flat-square)](https://registry.modelcontextprotocol.io/servers/io.github.suryast/indonesia-civic-stack)
[![CI](https://img.shields.io/github/actions/workflow/status/suryast/indonesia-civic-stack/ci.yml?style=flat-square&label=CI)](https://github.com/suryast/indonesia-civic-stack/actions)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square)](https://pypi.org/project/indonesia-civic-stack/)
[![License](https://img.shields.io/github/license/suryast/indonesia-civic-stack?style=flat-square)](LICENSE)

Python SDK, MCP tools, and REST wrappers for Indonesian public-sector data.
Release **1.2.1** includes **14 scraper modules**, **45 unified MCP tools**, and
**11 REST module routers**. These counts describe code, not live availability.

Indonesian public-data portals expose different APIs, HTML structures, browser
requirements, and access restrictions. This project provides a shared response
schema and reusable clients rather than requiring every civic-tech app to build
its own integration. Portal changes can still break individual operations;
verify the response and its provenance before drawing conclusions.

## Module inventory and maturity

Each row has a scraper, normalizer, and module test file. “Tests present” means
mocked/replayed tests exist, not that they establish current portal liveness.
The MCP column counts decorators in the **unified** `civic_stack/server.py`.

| Module | Source configured in code | Data / method | MCP tools | REST | Tests present |
|---|---|---|---:|:---:|:---:|
| [bpom](civic_stack/bpom/) | cekbpom.pom.go.id | Product registration; HTTP HTML | 3 | Yes | Yes |
| [bpjph](civic_stack/bpjph/) | cmsbl.halal.go.id | Halal certificates; HTTP REST | 4 | Yes | Yes |
| [ahu](civic_stack/ahu/) | ahu.go.id | Company registry; browser helper | 4 | Yes | Yes |
| [ojk](civic_stack/ojk/) | www.ojk.go.id / sikapiuangmu.ojk.go.id | Institutions and alerts; HTTP + optional browser list | 4 | Yes | Yes |
| [oss_nib](civic_stack/oss_nib/) | oss.go.id | NIB identity; Playwright | 3 | Yes | Yes |
| [lpse](civic_stack/lpse/) | spse.inaproc.id and configured portals | Vendors/tenders; multi-portal HTTP | 4 | Yes | Yes |
| [kpu](civic_stack/kpu/) | infopemilu.kpu.go.id / sirekap-obj-data.kpu.go.id | Candidates and 2024 elections; HTTP JSON | 4 | Yes | Yes |
| [lhkpn](civic_stack/lhkpn/) | elhkpn.kpk.go.id | Wealth declarations; Playwright search, HTTP PDFs | 3 | Yes | Yes |
| [bps](civic_stack/bps/) | webapi.bps.go.id | Statistics; HTTP API, requires `BPS_API_KEY` | 3 | Yes | Yes |
| [bmkg](civic_stack/bmkg/) | data.bmkg.go.id | Earthquakes/weather; HTTP JSON/XML | 4 | Yes | Yes |
| [simbg](civic_stack/simbg/) | simbg.pu.go.id and pilot portals | Permits; multi-portal HTTP | 3 | Yes | Yes |
| [jdih](civic_stack/jdih/) | peraturan.go.id | Regulations; Playwright recent-list filtering | 2 | No | Yes |
| [ksei](civic_stack/ksei/) | web.ksei.co.id | Securities and statistics links; HTTP HTML | 2 | No | Yes |
| [djpb](civic_stack/djpb/) | data-apbn.kemenkeu.go.id | Budget themes; HTTP JSON | 2 | No | Yes |

JDIH, KSEI, and DJPB are available through the SDK and unified MCP server, but
have no individual MCP server or REST router. JDIH search checks up to 50 recent
listing links; KSEI securities fetch/search only inspect page 1. Neither is a
complete registry search. LHKPN's browser search implementation does not prove
that reCAPTCHA or the upstream portal works in your deployment.

**Current portal liveness is unverified here.** Historical March/April 2026
observations in [endpoint status](references/endpoint-status.md) and
[geo-restrictions](references/geo-restrictions.md) are troubleshooting context,
not present-day health evidence. An HTTP 200 homepage, local `/health`, or passing
mock/VCR test is not a successful live registry lookup.

## Install

```bash
pip install indonesia-civic-stack             # Core HTTP SDK
pip install "indonesia-civic-stack[mcp]"       # + unified MCP server
pip install "indonesia-civic-stack[api]"       # + FastAPI and uvicorn
pip install "indonesia-civic-stack[browser]"   # + Playwright and Camoufox
pip install "indonesia-civic-stack[all]"       # mcp + api + browser
```

Browser-backed operations also need binaries:

```bash
playwright install chromium
python -m camoufox fetch  # AHU Camoufox path
```

AHU, OSS NIB, JDIH, LHKPN search, and OJK's full-list helper use browser paths.
BPJPH's current scraper uses HTTP REST. `all` does not download browser binaries
or include LHKPN's optional PDF packages. Install `pdfplumber` directly for PDF
text extraction; the optional scanned-document fallback needs `anthropic` and
`ANTHROPIC_API_KEY`, sends the document to an external API, and may incur cost.
There are no `pdf` or `playwright` extras. SOCKS HTTP transport additionally
requires `pip install "httpx[socks]"`.

## Python SDK

```python
import asyncio
from civic_stack.bpom.scraper import search

async def main():
    try:
        async with asyncio.timeout(120):
            records = await search("paracetamol")
    except Exception as exc:
        print("Could not verify:", type(exc).__name__)
        return
    if not records:
        print("No records returned; acquisition may be unverified")
    for record in records:
        print(record.status, record.found, record.source_url, record.fetched_at)
        if record.status == "ERROR":
            print("Could not verify:", record.result)
        elif record.found:
            print(record.result)  # Check identity, period, and domain-specific status
        else:
            print("No match reported within the query scope; not proof of absence")

asyncio.run(main())
```

Every scraper has `fetch()` and `search()`, with module-specific signatures.
Specialized helpers include BMKG's `get_latest_earthquake`, KPU's
`get_election_results`, OJK's `check_waspada`, KSEI's `get_statistics_links`,
and DJPB's `get_budget_summary`. See [usage and limitations](references/usage.md)
for actual return shapes, scope limits, and unified-tool wrapper caveats.

## Response interpretation

Core lookups return `CivicStackResponse` or lists of envelopes:

```json
{
  "result": {"product_name": "Example", "registration_status": "ACTIVE"},
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://cekbpom.pom.go.id/example",
  "fetched_at": "2026-03-14T06:30:00Z",
  "last_updated": null,
  "module": "bpom",
  "raw": null
}
```

This is illustrative, not a live response. Status values are `ACTIVE`, `EXPIRED`,
`SUSPENDED`, `REVOKED`, `NOT_FOUND`, and `ERROR`. Error details are under
`result.detail`, not a top-level `detail`. Some helpers return raw lists/dicts,
PDF extraction data, or URLs instead of envelopes; status shortcut MCP tools
omit source and timestamp. Do not assume every tool has the full schema.

Check `status`, `found`, `source_url`, and `fetched_at` before reading `result`.
Retrieval time is not publication time; verify the source's reporting period.
**`ERROR` is not `NOT_FOUND`.** Current paths in several modules also collapse
network/browser failures into `NOT_FOUND` or `[]`. Consequently, an empty or
not-found result alone cannot prove acquisition succeeded or that the record
does not exist. BPS `fetch()` can raise for a missing key; other callers can
also encounter unexpected exceptions. Catch exceptions at the caller boundary.

A found registration is not a general safety/legal guarantee. An alert-list
match is a warning, not an endorsement. Partial multi-portal results and scraper
confidence values must not be presented as exhaustive or authoritative checks.

## Unified MCP server

```bash
civic-stack-mcp                   # stdio, 45 tools
python -m civic_stack.server      # packaged equivalent
civic-stack mcp                   # CLI stdio entry point
python -m civic_stack.server --transport http --host 127.0.0.1 --port 8000

# Individual module server (where present):
python -m civic_stack.bpom.server
```

For local clients, configure `civic-stack-mcp` as the command. The repository's
[.mcp.json](.mcp.json) uses `.venv/bin/python -m civic_stack.server`; create that
virtual environment and install `[mcp]` before discovery. Discovery does not
install dependencies or ensure portals respond. There is no shared hosted server.

### Unified MCP tool inventory

| Module | Registered tool names |
|---|---|
| bpom | `check_bpom`, `search_bpom`, `get_bpom_status` |
| bpjph | `check_halal_cert`, `lookup_halal_by_product`, `get_halal_status`, `cross_reference_halal_bpom` |
| ahu | `lookup_company_ahu`, `get_company_directors`, `verify_company_status`, `search_companies_ahu` |
| ojk | `check_ojk_license`, `search_ojk_institutions`, `get_ojk_status`, `check_ojk_waspada` |
| oss_nib | `lookup_nib`, `verify_nib`, `search_oss_businesses` |
| lpse | `lookup_vendor_lpse`, `search_lpse_vendors`, `search_lpse_tenders`, `get_lpse_portals` |
| kpu | `get_candidate`, `search_kpu_candidates`, `get_election_results_kpu`, `get_campaign_finance_kpu` |
| lhkpn | `get_lhkpn`, `search_lhkpn`, `get_lhkpn_pdf` |
| bps | `search_bps_datasets`, `get_bps_indicator`, `list_bps_regions` |
| bmkg | `get_bmkg_alerts`, `get_weather_forecast`, `get_earthquake_history`, `get_latest_earthquake` |
| simbg | `lookup_building_permit`, `search_permits_by_area`, `list_simbg_portals` |
| jdih | `search_jdih`, `get_jdih` |
| ksei | `search_ksei`, `get_ksei` |
| djpb | `search_djpb`, `get_djpb` |

These are 45 registered names, not 45 independently validated operations. Some
wrappers call generic scraper functions rather than the specialized helper
suggested by the tool name; read [wrapper caveats](references/usage.md) before
using election-results, campaign-finance, tender, alert-list, or portal-list tools.

Verify registration offline, without calling tools:

```bash
python -c 'import asyncio; from civic_stack.server import mcp; print(len(asyncio.run(mcp.list_tools())))'
```

## REST API

```bash
civic-stack api --host 127.0.0.1 --port 8000
uvicorn civic_stack.app:app --host 127.0.0.1 --port 8000
uvicorn civic_stack.bpom.app:app --host 127.0.0.1 --port 8001
```

The unified app mounts 11 routers. JDIH, KSEI, and DJPB have no REST routes.
Open `/docs` or `/openapi.json` for the actual route signatures. Examples:

```text
GET /bpom/search?q=paracetamol
GET /bpjph/search?q=kopi
GET /ahu/search?q=Contoh
GET /ojk/check/Bank%20BCA
GET /kpu/search?q=Contoh
GET /lhkpn/search?q=Contoh
GET /bps/search?q=inflasi
GET /bmkg/forecast/Jakarta
GET /bmkg/earthquake/latest
GET /simbg/search?q=Jakarta
```

`/health` only describes the local app; it does not probe upstream portals.

## Deployment and security

`civic_client()` reads `PROXY_URL`, with environment-based `PROXY_MODE=connect`
or `rewrite` selection. A `*.workers.dev` URL auto-selects rewriting. Browser
proxy handling is separate: a Worker rewrite URL is not a standard Chromium
proxy, AHU and OSS-NIB fall back to `PROXY_URL` only in CONNECT mode, JDIH uses
its explicit proxy argument, and LHKPN search does not forward its `proxy_url`
argument to its browser. Do not assume setting an environment variable proxies
every operation. See [usage](references/usage.md).

Whoever runs a proxy controls the portal responses the server receives. The
REST routers and the standalone AHU/OSS-NIB MCP servers therefore accept a
caller-supplied `proxy_url` only when it exactly matches `PROXY_URL` or an entry
in `CIVIC_ALLOWED_PROXIES` (comma-separated full proxy URLs); anything else is
rejected (HTTP 400 or an `ERROR` envelope). Configure proxies server-side.

Access can vary by deployment, endpoint, and time. Historical regional tests do
not establish a current geo-block or WAF cause. Stop after bounded attempts;
do not bypass authenticated tiers or repeatedly retry access controls.

**The current unified REST app does not implement API-key authentication or
per-client rate-limit middleware.** Setting `CIVIC_API_KEY` or `CIVIC_RATE_LIMIT`
alone does not enable either. `CIVIC_ALLOWED_PROXIES` only gates caller-supplied
proxies; it is not an SSRF allowlist for SDK calls. Deploy behind your own
authentication, quotas, and network controls. Bind loopback
for local use. Module acquisition rate limiters are not public-API abuse controls.

## Agent Skills installation

[SKILL.md](SKILL.md) is the portable skill entry point. Its metadata version is
`"1.2.1"`; it uses trigger phrases in `description`, not unsupported frontmatter
keys. Installation must retain the **complete repository**, especially
`references/usage.md` and the other bundled references, package code, manifest,
and licenses. The installed directory must be named `indonesia-civic-stack`.

For a host that supports a user-selected skills directory:

```bash
# Set this to your host's configured directory; destination must not already exist.
git clone https://github.com/suryast/indonesia-civic-stack.git "$SKILLS_DIR/indonesia-civic-stack"
cd "$SKILLS_DIR/indonesia-civic-stack"
pip install -e ".[mcp]"  # if running the bundled MCP code
```

Do not install only `SKILL.md`, and do not rename the package to a release
worktree's suffix. Host discovery and Python installation are separate steps.
For version-pinned installs, choose the reviewed release revision explicitly;
cloning the default branch is not a version pin.

## Development and offline verification

```bash
git clone https://github.com/suryast/indonesia-civic-stack.git
cd indonesia-civic-stack
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev]"

pytest --collect-only -q   # derive current collected tests; no fixed advertised total
pytest -v                 # mocked/VCR replay; no live portal calls intended
pytest tests/jdih/ tests/ksei/ tests/djpb/ -v
ruff check civic_stack/ tests/ scripts/ examples/ app.py server.py
ruff format --check civic_stack/ tests/ scripts/ examples/ app.py server.py
mypy civic_stack/
```

All 14 modules have test files, including JDIH, KSEI, and DJPB. A passing offline
suite validates fixtures/mocks, not upstream operation. Do not record live
cassettes in CI; review the actual test isolation and recording settings first.

Read [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md), and
[CONTRIBUTING.md](CONTRIBUTING.md) before development. The contribution guide
states the desired full module contract; the implemented surfaces above take
precedence over older blanket inventory statements in other documents.

## References and related projects

- [Usage and implementation limits](references/usage.md)
- [Historical endpoint observations](references/endpoint-status.md)
- [Historical regional access observations](references/geo-restrictions.md)
- [Portal patterns](references/portal-patterns.md)
- [Proxy operations](references/vps-hardening.md)
- [Example prompts](PROMPTS.md)
- [indonesia-civic-signal-monitor](https://github.com/suryast/indonesia-civic-signal-monitor)
- [indonesia-gov-apis](https://github.com/suryast/indonesia-gov-apis)

## License

The root skill/documentation license is MIT; see [LICENSE](LICENSE).
Module licensing varies; retain module license files and consult
[LICENSES.md](LICENSES.md) (its older `modules/` labels refer to the current
`civic_stack/` package directories).
