# Usage and implementation limits — 1.2.0

This guide describes code interfaces, not fresh portal availability. Counts derive
from `civic_stack/*/scraper.py`, decorators in `civic_stack/server.py`, and mounted
routers in `civic_stack/app.py`. Normalizer and test files exist for all 14
modules. Test-file presence does not imply live coverage or passing tests.

## Module selection

Import `fetch` or `search` from `civic_stack.<module>.scraper`. Signatures differ;
only pass supported arguments. Every scraper has these two entry points, but
specialized helpers have different return shapes.

| Module | Data / lookup input | Implementation notes | Unified MCP tools | REST |
|---|---|---|---:|:---:|
| bpom | Product registration number; product/company keyword | HTTP + HTML parsing | 3 | Yes |
| bpjph | Certificate number; product/company keyword | HTTP REST; `search_type` selects search field | 4 | Yes |
| ahu | Company name or registration number | Browser helper; Camoufox path with Playwright fallback | 4 | Yes |
| ojk | Institution name/license; alert-list entity | HTTP portal/API paths; full-list helper uses Playwright | 4 | Yes |
| oss_nib | NIB number or company name | Playwright through shared BPJPH browser helper | 3 | Yes |
| lpse | Vendor name/NPWP or tender keyword | Multiple HTTP portals; partial failures possible | 4 | Yes |
| kpu | Candidate ID/name, region code | HTTP JSON; election helpers target 2024 data | 4 | Yes |
| lhkpn | Official name or report ID | Playwright search; HTTP PDF/detail helpers | 3 | Yes |
| bps | Dataset keyword, indicator ID, region code | HTTP API; `BPS_API_KEY` required | 3 | Yes |
| bmkg | City, earthquake/alert keyword | HTTP JSON/XML; inspect event time separately | 4 | Yes |
| simbg | Permit ID/address/applicant/area | Multiple HTTP portals; partial failures possible | 3 | Yes |
| jdih | Regulation ID or keyword/type | Playwright; search filters up to 50 recent listing links | 2 | No |
| ksei | Security code/name | HTTP HTML; fetch/search scan page 1 only | 2 | No |
| djpb | Budget theme ID or theme-name keyword | HTTP JSON; `fetch()` matches `id_tematik` | 2 | No |

**Total: 14 scraper modules, 45 unified MCP tools, 11 REST routers.** Individual
module MCP servers have their own inventories; do not sum those to describe the
unified server. JDIH, KSEI, and DJPB have no individual `server.py` or `router.py`.

## Install dependencies

```bash
pip install indonesia-civic-stack             # HTTP SDK
pip install "indonesia-civic-stack[mcp]"       # FastMCP server
pip install "indonesia-civic-stack[api]"       # FastAPI + uvicorn
pip install "indonesia-civic-stack[browser]"   # Playwright + Camoufox
playwright install chromium
python -m camoufox fetch                      # AHU Camoufox binary
pip install "indonesia-civic-stack[all]"       # mcp + api + browser
```

Declared extras are `mcp`, `api`, `browser`, `all`, and `dev`. Neither `playwright`
nor `pdf` is a declared extra. For LHKPN PDF text extraction, install
`pdfplumber` directly. The optional scanned-PDF fallback uses `anthropic` and
`ANTHROPIC_API_KEY`, makes a separate external API request, and may incur cost;
obtain approval before transmitting a document. `[all]` does not include these
PDF packages or browser binary downloads.

```bash
pip install pdfplumber
# Only if explicitly enabling the external scanned-PDF fallback:
pip install anthropic
```

## Bounded SDK example

This performs a live lookup when executed; it is not an offline availability test.

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
        print("No records returned; successful acquisition is not established")
    for record in records:
        print(record.status, record.found, record.source_url, record.fetched_at)
        if record.status == "ERROR":
            print("Could not verify:", record.result)
        elif record.found:
            print(record.result)  # Check identity, scope, and status before conclusions
        else:
            print("No match reported within this lookup's scope; absence may be unverified")

asyncio.run(main())
```

Other actual SDK helpers include:

- `civic_stack.bmkg.scraper.get_latest_earthquake()` → envelope;
  `get_earthquake_history(region="", days=7)` → envelope list (the current
  implementation does not apply the `days` filter).
- `civic_stack.bps.scraper.get_indicator(indicator_id, region_code="0000")`
  → envelope; `list_regions()` → raw list of dicts.
- `civic_stack.ksei.scraper.get_statistics_links()` → raw list of PDF link dicts;
  `get_latest_statistics_url()` → URL or `None`, taking the first page link,
  not independently proving chronological recency.
- `civic_stack.djpb.scraper.get_budget_summary(year="2026")` → envelope list.
- `civic_stack.jdih.scraper.list_recent("uu", limit=20)` → envelope list.
- `civic_stack.lhkpn.scraper.get_pdf(report_id)` and `compare_lhkpn(...)`
  → raw dicts, potentially containing `error`; comparison is not a registered
  unified MCP tool.

## MCP

```bash
civic-stack-mcp                       # Unified stdio server
python -m civic_stack.server          # Equivalent packaged entry point
python -m civic_stack.server --transport http --host 127.0.0.1 --port 8000
python -m civic_stack.bpom.server     # Individual BPOM server
```

The unified tools are wrappers, not interchangeable with every specialized SDK
helper. For example, `get_ksei(report_id)` actually invokes securities
`fetch()`, so pass a security code; `get_djpb(report_id)` invokes budget-theme
`fetch()`, so pass a theme ID, not a fiscal year. `get_lpse_portals` and
`list_simbg_portals` currently call `fetch("__portals__")`, not a dedicated
catalog helper. `get_election_results_kpu`, `get_campaign_finance_kpu`,
`search_lpse_tenders`, and `check_ojk_waspada` also wrap generic `fetch/search`
rather than the named specialized SDK helpers. Use the specialized SDK/REST
operation where the intended behavior requires it; do not infer capability
from a tool name alone.

Full-response tools normally serialize envelopes or envelope lists. Quick-status
tools return only `found`, `status`, and `module`; cross-reference tools return
containers of results; BPS region lists and LHKPN PDF tools return raw objects.

## REST

```bash
civic-stack api --host 127.0.0.1 --port 8000
uvicorn civic_stack.app:app --host 127.0.0.1 --port 8000
uvicorn civic_stack.bpom.app:app --host 127.0.0.1 --port 8001
```

The unified app exposes `/docs`, `/openapi.json`, and `/health`; health describes
local app state, not upstream liveness. Example implemented GET routes:

```text
/bpom/search?q=paracetamol
/bpjph/search?q=kopi
/ahu/search?q=Contoh
/ojk/check/Bank%20BCA
/ojk/waspada?q=Contoh
/kpu/search?q=Contoh
/lhkpn/search?q=Contoh
/bps/search?q=inflasi
/bmkg/forecast/Jakarta
/bmkg/earthquake/latest
/simbg/search?q=Jakarta
```

Do not assume environment variables implement security: the current unified app
does not read `CIVIC_API_KEY` or `CIVIC_RATE_LIMIT`, or install authentication or
per-client rate-limit middleware. Put authentication, quotas, and network access
controls in a deployment layer before exposing it. Shared HTTP code does not
implement `CIVIC_ALLOWED_PROXIES` or an SSRF allowlist. Do not accept untrusted
proxy URLs or arbitrary deployment credentials.

## Error, absence, and provenance limits

`CivicStackResponse` contains `result`, `found`, `status`, `confidence`,
`source_url`, `fetched_at`, `last_updated`, `module`, and `raw`. Status values are
`ACTIVE`, `EXPIRED`, `SUSPENDED`, `REVOKED`, `NOT_FOUND`, and `ERROR`.
Error detail is stored in `result["detail"]`, not a top-level `detail` field.

Some paths suppress transport or browser failures into empty results or
`NOT_FOUND`: examples include BPJPH exceptions, JDIH browser failures, KSEI/DJPB
acquisition failures, LHKPN search failures, and multi-portal/BMKG/BPS paths.
BPS `fetch()` can raise when its API key is missing; its `search()` and
`get_indicator()` explicitly return configuration error envelopes. Catch
unexpected exceptions at the caller boundary and do not equate missing data
with proof of absence. Confidence is a scraper heuristic, not a legal guarantee.

`PROXY_URL` is resolved by `civic_client()` for HTTP paths, with `PROXY_MODE`
controlling environment-based connect/rewrite selection. SOCKS transport also
needs `pip install "httpx[socks]"`. Browser paths are separate: JDIH receives
its explicit proxy argument, while LHKPN search currently does not forward its
`proxy_url` argument to the browser. A Worker rewrite proxy is not generally a
Chromium proxy. Diagnose current behavior before assuming any geographic cause;
historical reference reports and offline tests do not establish present liveness.
