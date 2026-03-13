# Module Specification Template

> Copy this file to `modules/<name>/README.md` when adding a new module.
> Fill in every section. Remove this instruction block before submitting.

---

## Module: `<name>`

**Source portal:** <!-- e.g. cekbpom.pom.go.id -->
**Scrape method:** <!-- httpx+BS4 | Playwright | REST wrapper -->
**Phase:** <!-- 1 | 2 | 3 -->
**License:** <!-- MIT | Apache-2.0 — match the module's LICENSE file -->
**Status:** <!-- ACTIVE | DEGRADED | ARCHIVED -->

---

## Source

| Field | Value |
|---|---|
| Portal URL | `https://...` |
| Operator | <!-- e.g. BPOM, Kemenkumham, KPK --> |
| Data type | <!-- e.g. Product registrations, Company records, Halal certificates --> |
| Auth required | <!-- None / Public search tier / Login required --> |
| Last verified | <!-- YYYY-MM-DD — when you last confirmed the scraper works --> |

---

## Rate Limits & Block Behaviour

| Parameter | Value |
|---|---|
| Safe request rate | <!-- e.g. ~10 req/min --> |
| Block trigger | <!-- e.g. >20 req/min from same IP --> |
| Block type | <!-- e.g. Cloudflare 403, silent timeout, CAPTCHA --> |
| Mitigation | <!-- e.g. Cloudflare Worker routing, Camoufox, backoff --> |
| IP rotation needed | <!-- Yes / No --> |

---

## Normalized Schema (`result` object)

<!-- Document every field in the `result` dict your module returns. -->

```python
{
    "id": str,                  # Primary identifier (registration no, cert no, etc.)
    "name": str,                # Human-readable name
    "status": str,              # ACTIVE | EXPIRED | SUSPENDED | REVOKED
    # ... module-specific fields
}
```

---

## MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `check_<module>` | `(id: str) -> dict` | Single record lookup by ID |
| `search_<module>` | `(keyword: str) -> list[dict]` | Multi-result keyword search |
| `get_<module>_status` | `(id: str) -> dict` | Status-only lookup (lighter weight) |

---

## FastAPI Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/<module>/check/{id}` | Single record lookup |
| `GET` | `/<module>/search?q=` | Multi-result search |
| `GET` | `/<module>/status/{id}` | Status-only lookup |

---

## Example Response

```json
{
  "result": {
    "id": "...",
    "name": "...",
    "status": "ACTIVE"
  },
  "found": true,
  "status": "ACTIVE",
  "confidence": 1.0,
  "source_url": "https://...",
  "fetched_at": "2026-03-01T10:00:00Z",
  "last_updated": null,
  "module": "<name>",
  "raw": null
}
```

---

## Known Issues & Quirks

<!-- Document any portal-specific gotchas, encoding issues, field gaps, etc. -->

- ...

---

## VCR Fixtures

| Cassette | Scenario |
|---|---|
| `tests/<name>/cassettes/found.yaml` | Active record returned |
| `tests/<name>/cassettes/not_found.yaml` | Portal returns no results |
| `tests/<name>/cassettes/error.yaml` | 429 / 503 — validates backoff |

---

## Legal Basis

This module scrapes publicly accessible data from a government portal with no login
requirement. Data is fetched on demand and not persisted by this library. Scraping is
conducted at low request rates consistent with normal human browsing. No personal data
beyond what is voluntarily published on the public portal is accessed.

<!-- Add any module-specific legal notes here. -->
