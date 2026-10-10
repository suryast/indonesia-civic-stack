---
name: indonesia-civic-stack
description: >-
  Queries Indonesian public-sector data through the indonesia-civic-stack Python
  SDK, unified MCP server, or REST API. Use when checking BPOM registrations,
  BPJPH halal certificates, AHU companies, OJK financial licenses or alerts,
  OSS NIB identities, LPSE procurement, KPU elections, LHKPN wealth declarations,
  BPS statistics, BMKG weather or earthquakes, SIMBG building permits, JDIH
  regulations, KSEI securities, or DJPB budget themes. Distinguishes retrieved
  records from unavailable sources and reports provenance and retrieval time.
license: MIT
compatibility: >-
  Requires Python 3.11+ and network access for live queries, or an already
  configured MCP/REST service. Optional mcp, api, and browser extras enable
  those interfaces; browser paths also require installed browser binaries.
  BPS requires BPS_API_KEY. Proxy needs vary by endpoint and deployment.
metadata:
  version: "1.2.0"
  package: "indonesia-civic-stack"
---

# indonesia-civic-stack

Use the smallest relevant public-data lookup. The repository contains 14 scraper
modules and 45 decorated tools in the unified MCP server; the REST app mounts
11 module routers (JDIH, KSEI, and DJPB are SDK/unified-MCP only).
These are implementation counts, not evidence that any portal is currently live.

## Bounded lookup workflow

1. Identify the requested registry, exact identifier or keyword, and relevant
   reporting period. Preserve the user's identifier; do not silently repair it.
   Read [usage and module limits](references/usage.md) for the selected module.
2. Use an existing configured MCP service when available; otherwise install the
   required SDK extras and choose the documented SDK or REST entry point.
   Check required keys/browser binaries before sending a request. Do not expose
   keys, credentials, personal queries, or raw portal output in diagnostic logs.
3. Send one focused lookup with a finite deadline (120 seconds is a starting
   budget for browser-backed SDK calls). For cross-source requests, bound each
   source separately. Respect module rate limits. Allow at most one corrective
   retry after a concrete configuration fix; do not loop around portal blocks.
4. Inspect **`status`, `found`, `source_url`, and `fetched_at`** before using
   `result`. Check exact identity, reporting period, domain-specific status, and
   `confidence`. Retrieval time is not the record's publication/update time.
   Shortcut status tools omit provenance: follow up with a full lookup if the
   answer needs a source or timestamp. Some helper tools return raw lists/dicts
   instead of envelopes; validate their documented shape separately.
5. Treat **`ERROR` as unavailable, not not-found**. Treat exceptions, timeouts,
   blocked responses, missing dependencies/keys, and partial portal failures as
   unverified. Some current scrapers collapse failures to `NOT_FOUND` or `[]`;
   absence alone cannot prove successful acquisition or registry-wide absence.
   Do not turn `found=false` into “illegal”, “not halal”, or “safe”. A record
   found on an alert list is a warning, not a license or endorsement.
6. Report the matched record, scope/period, observed status, source URL, fetched
   time, and limitations. If acquisition cannot be verified, say “could not
   verify” rather than asserting a negative. Stop at the request budget and
   explain the blocker instead of claiming successful portal access.

## Setup and entry points

```bash
pip install "indonesia-civic-stack[mcp]"  # Unified MCP server
civic-stack-mcp                         # stdio
python -m civic_stack.server --transport http --host 127.0.0.1 --port 8000

pip install "indonesia-civic-stack[api]"  # REST API (11 routers)
uvicorn civic_stack.app:app --host 127.0.0.1 --port 8000
```

For SDK-only HTTP paths, `pip install indonesia-civic-stack` is sufficient.
Install `[browser]` plus browser binaries for AHU, OSS NIB, JDIH, LHKPN search,
and OJK's full-list helper. BPJPH's current scraper uses HTTP, not a browser.
See [usage](references/usage.md) for SDK examples and optional PDF dependencies.

## Install the complete skill package

Install the whole repository into your host's skill directory as
`indonesia-civic-stack/`, retaining `SKILL.md`, `references/`, `civic_stack/`,
`pyproject.toml`, and licenses. Do not copy only `SKILL.md` or rename the
package to match a temporary release-worktree suffix. Configure discovery
using the host's supported mechanism; skill discovery does not install Python
requirements. Run `pip install -e ".[mcp]"` (or the required extras) from the
installed repository if running its code.

## Troubleshooting evidence

[Endpoint observations](references/endpoint-status.md),
[geo-restriction observations](references/geo-restrictions.md),
[portal patterns](references/portal-patterns.md), and
[proxy operations](references/vps-hardening.md) contain historical/contextual
material. Load only the relevant reference. Never present a historical success,
HTTP 200, mock/VCR test, or local MCP health response as current portal or
scraper liveness. Fresh liveness claims require a dated, successful live
operation from the actual deployment; a homepage response is not a record
lookup. Check browser-specific proxy propagation rather than assuming the
shared HTTP client's `PROXY_URL` handling applies to every browser path.
