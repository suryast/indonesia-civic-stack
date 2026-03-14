# Copilot Instructions

This is a Python SDK for Indonesian government data portals.

## Key rules:
- All functions are async. Use `async def` and `await`.
- Always use `civic_client()` from `shared.http` — never raw httpx.
- Every function must accept `proxy_url: str | None = None` parameter.
- Return `CivicStackResponse` from `shared.schema` — never raw dicts.
- On errors, return `error_response()` — never raise in `search()`.
- Rate limit with `RateLimiter` from `shared.http`.
- Tests use VCR cassettes — never hit live government portals.
- Python 3.11+, Pydantic v2, ruff for formatting, line length 100.

## File structure per module:
- `scraper.py` — fetch() and search() functions
- `normalizer.py` — raw HTML/JSON → dict transformations
- `router.py` — FastAPI routes
- `server.py` — MCP server using CivicStackMCPBase
- `app.py` — FastAPI app
- `README.md` — module docs

See `AGENTS.md` for full architecture guide.
