# CLAUDE.md — Instructions for Claude Code

## MCP Integration

This repo includes `.mcp.json` — Claude Code auto-discovers 40 MCP tools on startup.
The unified server (`server.py`) registers all tools from all 11 modules in one process.

## Quick Context

This is a Python SDK for Indonesian government data. 11 modules, each wrapping a gov portal.
Shared layer in `shared/`. Tests use VCR (no live calls). All async, Pydantic v2, Python 3.11+.

## Before Writing Code

1. Read `AGENTS.md` for architecture and patterns
2. Read `CONTRIBUTING.md` for the module contract
3. Check the module's `README.md` for portal-specific quirks
4. Check GitHub issues for known portal changes

## Commands

```bash
# Test
pytest -v
pytest tests/<module>/ -v

# Lint + format
ruff check . && ruff format --check .

# Type check
mypy shared/ modules/

# Run unified MCP server (40 tools)
python server.py

# Run single module MCP server
python -m modules.bpom.server

# Run single module REST API
uvicorn modules.bpom.app:app --port 8001

# Run unified REST API
uvicorn app:app --port 8000

# Build & deploy proxy
cd proxy && npx wrangler deploy

# Verify MCP tools load
python -c "import asyncio; from server import mcp; print(asyncio.run(mcp.list_tools()))"
```

## Do Not

- Create raw `httpx.AsyncClient` — use `civic_client()`
- Raise exceptions from `search()` — return `error_response()` envelope
- Hit live portals in tests — record VCR cassettes
- Modify `shared/schema.py` without checking all 11 modules
- Remove proxy_url parameter from any function signature
- Use `print()` — use `logger` from `logging`

## Style

- Line length: 100
- Async-first: `async def`, `httpx.AsyncClient`
- Type hints on all public functions
- Pydantic v2 models
- `ruff` for linting and formatting
