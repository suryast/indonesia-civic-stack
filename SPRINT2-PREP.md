# Sprint 2 Prep — Docs, Launch & HalalKah Integration

## Current HalalKah Architecture (to be refactored)

### Data Pipeline (bespoke scrapers → SQLite → D1)
```
scripts/scrape.py          → BPJPH API (cmsbl.halal.go.id/api/search)  → halalkah.db
scripts/scrape_bpom.py     → BPOM DataTables (cekbpom.pom.go.id)      → bpom.db
scripts/refresh.py         → Weekly re-scrape (INSERT OR IGNORE)
scripts/import_products_d1.py → SQLite → Cloudflare D1 (halalkah-prod)
```

### Serving Layer
- **CF Pages Functions** (`functions/api/search.ts`) — queries D1 directly
- **D1 database**: `halalkah-prod` (ID: `REDACTED_D1_ID`)
- **9.57M products** in D1, data import complete

### What civic-stack replaces
| Current | civic-stack module | Notes |
|---------|-------------------|-------|
| `scripts/scrape.py` (BPJPH API) | `modules/bpjph/` | Direct API → Playwright change; need to verify response parity |
| `scripts/scrape_bpom.py` (DataTables) | `modules/bpom/` | httpx + BS4; schema normalization needed |
| `scripts/refresh.py` | civic-stack `fetch()` + `search()` | Weekly cron calls civic-stack instead of raw scraping |
| `scripts/cross-fill-halal.py` | `bpjph.cross_ref_bpom()` | Built into civic-stack's cross-reference hook |

### What stays unchanged
- CF Pages frontend (`public/`)
- D1 database + wrangler config
- `functions/api/search.ts` (queries D1, not scrapers)
- `scripts/import_products_d1.py` (SQLite → D1 pipeline stays, just reads from civic-stack output)

## Integration Plan

### Step 1: Add civic-stack as dependency
```bash
cd ~/projects/halalkah
pip install indonesia-civic-stack  # or git submodule
```

### Step 2: Create adapter script
New `scripts/civic_refresh.py`:
```python
from civic_stack.modules.bpjph import fetch, search
from civic_stack.modules.bpom import fetch as bpom_fetch
# Replace raw HTTP scraping with civic-stack calls
# Output still goes to SQLite for D1 import pipeline
```

### Step 3: Update weekly cron
Current cron `halalkah-refresh` (ID: `REDACTED_CRON_ID`) calls `scripts/refresh.py`
→ Update to call `scripts/civic_refresh.py`

### Step 4: Smoke test
- Compare output: `civic_refresh.py` vs `refresh.py` for same inputs
- Verify record counts match
- Run D1 import pipeline with civic-stack output

## Launch Prep Checklist

### README contributions (Day 11)
- [ ] HalalKah listed as "Powered by civic-stack" consumer
- [ ] Usage example showing `check_halal_cert()` MCP tool
- [ ] Badge: "9.57M products verified"

### HalalKah integration (Day 12)
- [ ] `civic_refresh.py` adapter script
- [ ] VCR fixtures for halalkah-specific queries
- [ ] Staging smoke test
- [ ] Cron update

### Launch posts (Day 13)
- [ ] GitHub README polished
- [ ] Show HN draft (civic-stack angle: MCP servers for Indonesian gov data)
- [ ] IndieHackers Indonesia post
- [ ] Cross-link from indonesia-gov-apis repo

### Issue triage (Day 14)
- [ ] Phase 2 module tickets (OJK, OSS-NIB, LPSE, KPU)
- [ ] `good-first-issue` labels on simpler modules (KPU = REST only, no scraping)
- [ ] DEGRADED policy documented

## Key Decisions Needed

1. **civic-stack as pip package or git submodule?** Pip is cleaner but requires PyPI publish first
2. **Keep SQLite → D1 pipeline or go direct?** D1 import works; civic-stack doesn't own persistence (per PRD)
3. **BPJPH API status** — `cmsbl.halal.go.id` has been returning ENOTFOUND since ~Feb. civic-stack's Playwright approach may work if the portal is up even when API is down
4. **Launch timing** — coordinate with civic-stack public launch for maximum visibility

## Files to Prepare

```
halalkah/
├── scripts/
│   ├── civic_refresh.py      # NEW — adapter calling civic-stack
│   ├── refresh.py             # KEEP — fallback if civic-stack breaks
│   └── import_products_d1.py  # UNCHANGED
└── requirements-civic.txt     # NEW — civic-stack dependency
```

## Cron IDs
- `REDACTED_CRON_ID` — halalkah-refresh (weekly, Sun 03:00 UTC)
- `3207df84` — halal-endpoint-monitor (weekly Mon, checks if BPJPH API is back)
