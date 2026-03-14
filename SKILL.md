---
name: indonesia-civic-stack
description: >
  Query Indonesian government data portals via Python SDK, MCP tools, or REST API.
  11 modules covering BPOM (food/drug), BPJPH (halal), AHU (companies), OJK (finance),
  OSS (business ID), LPSE (procurement), KPU (elections), LHKPN (wealth declarations),
  BPS (statistics), BMKG (weather/earthquakes), SIMBG (building permits).
  Use when: checking Indonesian product registrations, verifying company legality,
  looking up halal certificates, checking financial licenses, querying earthquake data,
  or any task involving Indonesian government data.
triggers:
  - Indonesian government data
  - BPOM product check
  - halal certificate
  - OJK financial license
  - company registry Indonesia
  - earthquake Indonesia
  - BMKG weather
  - civic data Indonesia
---

# indonesia-civic-stack

## Quick Start

```python
import asyncio
from civic_stack.bpom.scraper import search as bpom_search
from civic_stack.bmkg.scraper import get_latest_earthquake

async def main():
    # Search BPOM products
    results = await bpom_search("paracetamol")
    for r in results:
        print(r.result if r.found else r.status)

    # Latest earthquake
    eq = await get_latest_earthquake()
    print(eq.result)

asyncio.run(main())
```

## Available Modules

| Module | Import | Primary Function |
|--------|--------|-----------------|
| bpom | `from civic_stack.bpom.scraper import fetch, search` | Food, drug, cosmetic registry |
| bpjph | `from civic_stack.bpjph.scraper import fetch, search` | Halal certificates |
| ahu | `from civic_stack.ahu.scraper import fetch, search` | Company registry (PT, CV, Yayasan) |
| ojk | `from civic_stack.ojk.scraper import fetch, search` | Financial institution licenses |
| oss_nib | `from civic_stack.oss_nib.scraper import fetch, search` | Business identity (NIB) |
| lpse | `from civic_stack.lpse.scraper import fetch, search` | Government procurement |
| kpu | `from civic_stack.kpu.scraper import fetch, search` | Election data |
| lhkpn | `from civic_stack.lhkpn.scraper import fetch, search` | Wealth declarations (⚠️ DEGRADED) |
| bps | `from civic_stack.bps.scraper import search` | Statistics (needs BPS_API_KEY) |
| bmkg | `from civic_stack.bmkg.scraper import search, get_latest_earthquake` | Weather & earthquakes |
| simbg | `from civic_stack.simbg.scraper import fetch, search` | Building permits |

## Response Envelope

Every function returns `CivicStackResponse`:

```python
response.found      # bool — was a record found?
response.status     # ACTIVE | EXPIRED | SUSPENDED | REVOKED | NOT_FOUND | ERROR
response.result     # dict — the normalized data (module-specific schema)
response.module     # str — which module produced this
response.source_url # str — the portal URL queried
```

## MCP Tools (40 total)

Each module exposes MCP tools via FastMCP:

```bash
# Run a module's MCP server
python -m civic_stack.bpom.server      # stdio mode
python -m civic_stack.bmkg.server      # stdio mode

# Add to Claude Desktop
claude mcp add civic-bpom -- python -m civic_stack.bpom.server
```

## Proxy (for non-Indonesian IPs)

```bash
export PROXY_URL="https://your-proxy.workers.dev"
# SDK auto-detects and routes all requests through proxy
```

## Dependencies

```bash
pip install httpx beautifulsoup4 pydantic lxml fastmcp
# For browser-based modules (bpjph, ahu, oss_nib):
pip install playwright && playwright install chromium
```
