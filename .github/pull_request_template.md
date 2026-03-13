# PR Checklist

## Type
- [ ] New module
- [ ] Bug fix (module scraper / normalizer)
- [ ] Fix for degraded module (reference issue: #___)
- [ ] Shared layer change (schema / http / mcp)
- [ ] Docs / tests only

## Module contract (required for new modules — skip for non-module PRs)

- [ ] `fetch(query, *, debug, proxy_url) -> CivicStackResponse` implemented
- [ ] `search(keyword, filters, *, proxy_url) -> list[CivicStackResponse]` implemented
- [ ] MCP server class inheriting `CivicStackMCPBase` with `_register_tools()`
- [ ] At least 3 VCR cassettes or HTML fixtures (`found`, `not_found`, `error`)
- [ ] `modules/<name>/README.md` filled from `docs/module-spec.md` template
- [ ] `modules/<name>/LICENSE` file added (MIT or Apache-2.0 per `LICENSES.md`)
- [ ] `LICENSES.md` updated with new module entry

## Quality

- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `mypy shared/ modules/<name>/` passes
- [ ] `pytest tests/<name>/` passes
- [ ] No live portal calls in any test (VCR `record_mode="none"` or monkeypatched Playwright)

## Description

<!-- What does this PR do? Why is it needed? -->

## Test evidence

<!-- Paste a `pytest -v tests/<name>/` run or link to CI run -->

## Portal notes

<!-- Any quirks discovered, rate limits tested, known block behaviour -->
