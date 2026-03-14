# AGENTS.md — AI Agent Development Guide

> This file helps AI coding agents (Claude Code, Codex, Cursor, etc.) work effectively in this repo.

## Project Overview

**indonesia-civic-stack** is a Python SDK + MCP server + REST API that wraps 11 Indonesian government data portals into a unified interface. Every module returns `CivicStackResponse`.

## Architecture

```
indonesia-civic-stack/
├── shared/              # Core shared code (DO NOT break these)
│   ├── schema.py        # CivicStackResponse — the universal envelope
│   ├── http.py          # civic_client(), fetch_with_retry(), proxy support
│   └── mcp.py           # CivicStackMCPBase — base class for MCP servers
├── modules/             # One directory per government portal
│   ├── bpom/            # Example module (Food & Drug registry)
│   │   ├── scraper.py   # fetch() + search() — core logic
│   │   ├── normalizer.py # Raw HTML/JSON → structured dict
│   │   ├── router.py    # FastAPI routes
│   │   ├── server.py    # MCP server (FastMCP)
│   │   ├── app.py       # FastAPI app entry point
│   │   ├── Dockerfile
│   │   └── README.md
│   └── ... (11 modules total)
├── proxy/               # CF Worker proxy for geo-blocked portals
├── tests/               # VCR-based tests (no live portal calls in CI)
└── app.py               # Unified FastAPI app (all modules)
```

## Key Patterns

### Every module MUST follow this contract:

```python
# modules/<name>/scraper.py
async def fetch(query: str, *, proxy_url: str | None = None) -> CivicStackResponse:
    """Single-record lookup by ID."""

async def search(keyword: str, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Multi-result keyword search. Returns [] on not-found, never raises."""
```

### HTTP client — always use civic_client():

```python
from shared.http import civic_client, fetch_with_retry

async with civic_client(proxy_url=proxy_url) as client:
    response = await fetch_with_retry(client, "GET", url, rate_limiter=_limiter)
```

`civic_client()` auto-reads `PROXY_URL` from environment. Never create raw `httpx.AsyncClient`.

### MCP servers — two valid patterns:

```python
# Pattern 1: explicit init
class BpomMCPServer(CivicStackMCPBase):
    def __init__(self):
        super().__init__("bpom")
    def _register_tools(self): ...

# Pattern 2: class attribute
class BmkgMCPServer(CivicStackMCPBase):
    module_name = "bmkg"
    def _register_tools(self): ...
```

### Error handling — return envelopes, don't raise:

```python
from shared.schema import error_response, not_found_response

# When portal is unreachable:
return error_response("bpom", url, detail="Portal returned 404")

# When no results found:
return not_found_response("bpom", url)
```

## Critical Rules

1. **Never break `shared/`** — all 11 modules depend on schema.py, http.py, mcp.py
2. **Never hit live portals in tests** — use VCR cassettes (`tests/<module>/cassettes/`)
3. **Always return CivicStackResponse** — never return raw dicts or raise on not-found
4. **Rate limiting is mandatory** — every scraper must use `RateLimiter` from shared.http
5. **Proxy support is mandatory** — every function takes `proxy_url` kwarg and passes to `civic_client()`
6. **No data persistence** — modules fetch and return, no databases, no file writes

## Running Tests

```bash
pytest -v                    # All tests (VCR replay, no live calls)
pytest tests/bpom/ -v        # Single module
ruff check .                 # Lint
mypy shared/                 # Type check
```

## Adding a New Module

1. Copy `modules/bpom/` as template
2. Implement `scraper.py` (fetch + search)
3. Add `normalizer.py`, `router.py`, `server.py`, `app.py`
4. Record VCR cassettes: `pytest --vcr-record=new_episodes`
5. Add module to README table and `docker-compose.yml`
6. See `CONTRIBUTING.md` for full checklist

## Known Gotchas

- **Geo-blocking**: Most .go.id portals block non-Indonesian IPs. Set `PROXY_URL` env var.
- **Portal URL churn**: Indonesian gov portals change URLs without notice. Check issue tracker.
- **Browser modules**: bpjph, ahu, oss_nib need Playwright. ahu also needs Camoufox.
- **BPS needs API key**: Set `BPS_API_KEY` env var (free registration).
- **LHKPN is degraded**: Portal moved behind auth. Module returns errors.
- **CF Worker proxy has limits**: Can't proxy to CF-protected origins (403/522).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_URL` | For non-ID deploys | Proxy URL (auto-detects *.workers.dev as rewrite mode) |
| `PROXY_MODE` | No | Override: `connect` or `rewrite` |
| `BPS_API_KEY` | For BPS module | Free key from webapi.bps.go.id |
| `CIVIC_API_KEY` | For REST API auth | Set to enable API key checking |
| `CIVIC_RATE_LIMIT` | No | Requests per minute (default: 60) |

## Common Tasks (Copy-Paste Recipes)

### "Add a new search parameter to an existing module"
1. Read `modules/<name>/scraper.py` — find the `search()` function
2. Add the new parameter to the function signature (with default `None`)
3. Pass it to `fetch_with_retry()` via `params=` dict
4. Update `modules/<name>/server.py` — add parameter to MCP tool
5. Update `modules/<name>/router.py` — add query param to FastAPI endpoint
6. Record new VCR cassette: `pytest tests/<name>/ --vcr-record=new_episodes`

### "Fix a broken portal URL"
1. Check the portal manually: `curl -sI "https://portal.go.id/old-path"`
2. Find the new URL (check portal homepage, inspect network tab)
3. Update the URL constant at top of `modules/<name>/scraper.py`
4. Re-record VCR cassettes
5. Update `modules/<name>/README.md` with the URL change
6. Check if other modules reference the same portal

### "Add proxy support to a new function"
1. Add `proxy_url: str | None = None` to function signature
2. Pass to `civic_client(proxy_url=proxy_url)` — that's it
3. `civic_client()` auto-reads `PROXY_URL` from env when `proxy_url=None`

### "Debug a failing scraper"
1. Check if it's a geo-block: `curl -sI "https://portal.go.id" | head -5`
2. Check if URL changed: compare with `modules/<name>/README.md`
3. Check portal HTML structure: `curl -s "https://portal.go.id" | python -m bs4`
4. Run with debug: `await fetch(query, debug=True)` — check `.raw` field in response
5. Check GitHub issues for known portal changes

## File Conventions

- `scraper.py` — all HTTP logic lives here
- `normalizer.py` — transforms raw HTML/JSON to structured dicts
- `router.py` — FastAPI routes (thin, delegates to scraper)
- `server.py` — MCP server (thin, delegates to scraper)
- Module constants (URLs, rate limits) go at top of scraper.py
- Use `MODULE = "module_name"` constant in every scraper
