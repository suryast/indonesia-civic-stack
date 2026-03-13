# Module Specification Template

Copy this when adding a new module.

## `modules/<name>/`

### Source
- **URL:** https://example.go.id
- **Method:** httpx / Playwright / REST wrapper
- **Auth required:** No / Yes (describe tier)
- **Rate limit:** X req/min

### Normalized Fields
| Field | Type | Description |
|-------|------|-------------|
| id | str | Unique identifier |
| name | str | Entity name |
| status | str | ACTIVE / EXPIRED / CANCELLED |

### MCP Tools
- `check_<name>(identifier)` — Single record lookup
- `search_<name>(query)` — Multi-record search

### Known Quirks
- List any portal-specific issues (JS rendering, CSRF tokens, IP blocking, etc.)

### VCR Fixtures
- `tests/<name>/cassettes/found.yaml`
- `tests/<name>/cassettes/not_found.yaml`
- `tests/<name>/cassettes/<edge_case>.yaml`
