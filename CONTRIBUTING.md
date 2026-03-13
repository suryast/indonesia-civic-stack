# Contributing to indonesia-civic-stack

Thank you for helping build open civic infrastructure for Indonesia.

---

## Module Contract

Every module added to this repo **must** implement the full contract below.
A PR that is missing any item will not be merged.

### 1. Required functions

```python
# modules/<name>/__init__.py

async def fetch(query: str, *, debug: bool = False, proxy_url: str | None = None, **kwargs) -> CivicStackResponse:
    """Primary single-record lookup. query is a registration/cert/company ID or name."""
    ...

async def search(keyword: str, filters: dict | None = None, *, proxy_url: str | None = None) -> list[CivicStackResponse]:
    """Multi-result keyword search. Returns an empty list, never raises on not-found."""
    ...
```

Both must return `CivicStackResponse` from `shared.schema`. Use the `not_found_response()`
and `error_response()` helpers for non-result cases.

### 2. MCP server

Create `modules/<name>/server.py` with a class inheriting `CivicStackMCPBase`:

```python
from shared.mcp import CivicStackMCPBase

class MyModuleMCPServer(CivicStackMCPBase):
    def __init__(self) -> None:
        super().__init__("my_module")

    def _register_tools(self) -> None:
        @self.mcp.tool()
        async def check_my_module(id: str) -> dict:
            ...
```

The server must expose at minimum: `check_<module>(id)`, `search_<module>(keyword)`,
`get_<module>_status(id)`.

### 3. FastAPI router

Create `modules/<name>/router.py` exposing GET endpoints that mirror the MCP tools.
Mount it in the module's `app.py` with prefix `/<module_name>`.

### 4. VCR.py fixtures

Provide **at least 3** recorded HTTP fixtures under `tests/<name>/cassettes/`:

| Fixture | What it covers |
|---|---|
| `found.yaml` | A valid, active record returned from the portal |
| `not_found.yaml` | Portal returns empty / no results |
| `error.yaml` | A 429 or 503 response to validate backoff logic |

Run `pytest --vcr-record=new_episodes` once against the live portal to capture cassettes.
**Never hit live portals in CI** — VCR replay only.

### 5. Module README

Copy `docs/module-spec.md` to `modules/<name>/README.md` and fill in all sections:
source URL, scrape method, rate limits, known IP-block behaviour, normalized schema fields,
MCP tools, and example responses.

---

## Contribution Workflow

1. Fork the repo and create a branch: `feat/module-<name>` or `fix/<module>-<description>`.
2. Implement the full module contract (all 5 items above).
3. Run the test suite locally: `pytest tests/<name>/` — all tests must pass.
4. Run lint: `ruff check . && mypy shared/ modules/<name>/`.
5. Open a PR against `main`. Fill in the PR checklist (auto-populated from the template).
6. Maintainer review SLA: **2 weeks** from PR open.

---

## Module Degradation Policy

Portals change. When a module breaks:

1. A `DEGRADED` label is added to the module in the registry (README table).
2. A GitHub Issue is opened with the `degraded` label — community fixes welcome.
3. If the module is not fixed within **60 days**, it is archived to `modules/_archived/`.

If you are fixing a degraded module, reference the issue number in your PR.

---

## Licensing

This repo uses per-module licensing (see `LICENSES.md`). When adding a new module:

- Copy the correct `LICENSE` file into `modules/<name>/LICENSE` based on the table in `LICENSES.md`.
- State the license in your `modules/<name>/README.md` (the `License` field in the module spec).
- Do **not** use a license not already present in the repo without opening a discussion issue first.

---

## Scope Rules

- **Do not scrape data that requires authentication** unless the authenticated tier is
  explicitly listed in the module spec.
- **Do not persist data** — modules fetch and return. No databases, no file writes.
- **Do not duplicate pasal.id** — legal text search is their domain. Cross-link; don't copy.
- All scraped portals must be **publicly accessible government portals**.
  Document the legal basis for scraping in the module README.

---

## Code Style

```bash
ruff check .          # linting
ruff format .         # formatting
mypy shared/ modules/ # type checking
```

Line length: 100. Python 3.11+. Pydantic v2. Async-first (`httpx.AsyncClient`, `asyncio`).
