# Contributing to indonesia-civic-stack

## Module Contract

Every module PR must include **all** of these:

### 1. Module Code (`modules/<name>/`)
- `__init__.py` — `fetch(identifier)` and `search(query)` functions
- `router.py` — FastAPI router with GET endpoints mirroring MCP tools
- `server.py` — FastMCP server inheriting `CivicStackMCPBase`
- `Dockerfile` — Standalone deployment

### 2. Tests (`tests/<name>/`)
- Minimum 3 VCR fixtures: `found`, `not_found`, and one edge case
- No live portal calls in tests — all via VCR replay
- `pytest` must pass in CI

### 3. Documentation (`modules/<name>/README.md`)
- Source URL and data description
- Rate limits and known quirks
- Schema of returned fields
- MCP tool descriptions

## PR Checklist

- [ ] `fetch()` returns `CivicStackResponse` for a valid ID
- [ ] `search()` returns `CivicStackResponse` with list results
- [ ] FastAPI router returns 200 with correct envelope
- [ ] MCP tools callable via FastMCP
- [ ] VCR fixtures committed (no live portal calls in CI)
- [ ] `README.md` follows module-spec template
- [ ] `ruff check` passes
- [ ] `mypy` passes
- [ ] `pytest` passes

## DEGRADED Policy

A module that breaks and stays broken for **60 days** is flagged `DEGRADED` and archived.
Government portals change without notice — this is expected, not a failure.

## Code Style

- Python 3.11+
- ruff for linting, mypy for type checking
- All functions return `CivicStackResponse` — no raw dicts
- Use `shared.http.RateLimitedClient` for HTTP requests
- Async-first (`async def fetch`, `async def search`)
