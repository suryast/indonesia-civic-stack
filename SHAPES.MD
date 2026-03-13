# indonesia-civic-stack — Sprint Shapes

> Derived from the Product Requirements Document (Draft v1.0, March 2026).
> Each sprint is shaped as a discrete unit of work with a clear appetite, explicit outputs,
> and defined done-conditions. Sprints are time-boxed; scope is cut to fit time, never the
> reverse. Phases map to the PRD's three-phase module roadmap.

---

## Sprint 0 — Foundation
**Appetite:** 1 day · **Phase:** Pre-launch
**Owner:** Core maintainer(s)

### Problem
Nothing can be built until the monorepo has a shared contract (schema, HTTP layer, MCP base),
contributor guardrails (CI, lint), and repo scaffolding that future module PRs can slot into.

### Outputs
| Artefact | Detail |
|---|---|
| `pyproject.toml` | Workspace config, dependencies (httpx, playwright, fastapi, fastmcp, pydantic, pytest, vcrpy) |
| `shared/schema.py` | `CivicStackResponse` envelope: `result`, `found`, `status`, `confidence`, `source_url`, `fetched_at`, `last_updated`, `module`, `raw` |
| `shared/http.py` | Rate-limit helper, exponential backoff, `proxy_url` passthrough |
| `shared/mcp.py` | `CivicStackMCPBase` — abstract base class every module MCP server inherits |
| `CONTRIBUTING.md` | Module contract (fetch, search, MCP class, VCR fixtures, README template) |
| `docs/module-spec.md` | Template contributors copy when adding a new module |
| `docker-compose.yml` | Local dev stack |
| `LICENSE` | MIT |
| GitHub Actions CI | Lint (ruff), type-check (mypy), test (pytest) on PR |

### Done conditions
- `python -m pytest` passes on an empty test suite (no false failures)
- `CivicStackResponse` is importable from `shared.schema`
- CI runs green on a test PR

### Out of scope
- Any actual scraper logic
- Deployment configs (Railway)
- Any UI or CLI tooling beyond the test harness in `scripts/`

---

## Sprint 1 — Phase 1 Modules: BPOM + BPJPH + AHU
**Appetite:** 9 days (Days 2–10 of the two-week plan) · **Phase:** 1
**Owner:** Core maintainer(s)

### Problem
halalkah.id and AmanKah are currently running bespoke scrapers that will bit-rot. These three
modules are the minimum to make civic-stack a real dependency, not just scaffolding. All three
sources are publicly accessible (no login required for the data tier we need).

### Sub-shape A — `modules/bpom/` (Days 2–3)

**Source:** cekbpom.pom.go.id — static HTML, no JS rendering needed.

**Scrape approach:** httpx + BeautifulSoup. Rate cap ~10 req/min with exponential backoff.

**Key normalized fields:** registration number · product name · company · category ·
registration status (ACTIVE / EXPIRED / CANCELLED) · expiry date

**MCP tools:** `check_bpom(registration_no)` · `search_bpom(product_name)` · `get_bpom_status(id)`

**Outputs:**
- `modules/bpom/__init__.py` — `fetch()` and `search()` implementing the module contract
- `modules/bpom/router.py` — FastAPI router (GET endpoints mirroring MCP tools)
- `modules/bpom/server.py` — FastMCP server inheriting `CivicStackMCPBase`
- `modules/bpom/Dockerfile`
- `tests/bpom/` — VCR fixtures for: found · not_found · expired · search_multi_result
- `modules/bpom/README.md` — source, rate limits, schema, known quirks

**Done conditions:**
- `fetch("MD12345")` returns a valid `CivicStackResponse` (replay via VCR)
- FastAPI `/bpom/check/{id}` returns 200 with correct envelope
- MCP `check_bpom` tool callable via FastMCP
- CI green

---

**Sub-shape B — `modules/bpjph/` (Days 4–5)**

**Source:** sertifikasi.halal.go.id — JS-rendered, form submission required.

**Scrape approach:** Playwright (Python) + Camoufox fingerprint randomization. No auth required
for certificate lookup tier.

**Key normalized fields:** certificate number · company · product list · issuer (MUI / BPJPH) ·
issue date · expiry date · status

**MCP tools:** `check_halal_cert(cert_no)` · `lookup_halal_by_product(name)` ·
`get_halal_status(company_name)`

**Cross-reference hook:** After a BPJPH lookup, optionally call `bpom.fetch()` to surface any
BPOM registration for the same product — flags cases where BPOM registration is active but halal
cert has lapsed.

**Outputs:**
- `modules/bpjph/__init__.py` — `fetch()`, `search()`, and `cross_ref_bpom()` helper
- `modules/bpjph/router.py` — FastAPI router
- `modules/bpjph/server.py` — FastMCP server
- `modules/bpjph/Dockerfile`
- `tests/bpjph/` — VCR fixtures (Playwright sessions recorded via `playwright-har` + VCR adapter)
- `modules/bpjph/README.md` — Camoufox setup instructions, known JS rendering delays

**Done conditions:**
- `fetch("BPJPH-12345")` returns valid `CivicStackResponse` via VCR replay
- Cross-ref returns a BPOM result when product name matches
- CI green (Playwright in Docker, no live portal hit)

---

**Sub-shape C — `modules/ahu/` (Days 6–7)**

**Source:** ahu.go.id — Playwright, form submission, datacenter IP blocking risk.

**Scrape approach:** Playwright + Cloudflare Worker routing (CF Worker URL configurable via
`proxy_url`). Camoufox per session. Request signing to reduce bot detection.

**Key normalized fields:** company name · registration number · legal form (PT / CV / Yayasan /
Koperasi) · legal status · directors list · commissioners list · deed date · domicile

**MCP tools:** `lookup_company_ahu(name_or_id)` · `get_company_directors(id)` ·
`verify_company_status(id)`

**Outputs:**
- `modules/ahu/__init__.py` — `fetch()`, `search()`, director extraction logic
- `modules/ahu/router.py` — FastAPI router
- `modules/ahu/server.py` — FastMCP server
- `modules/ahu/Dockerfile`
- `tests/ahu/` — VCR fixtures: company_found · company_not_found · blocked_response (tests
  backoff logic without hitting live portal)
- `modules/ahu/README.md` — IP mitigation setup, CF Worker config, tested rate limits

**Done conditions:**
- `fetch("PT Contoh Indonesia")` returns valid `CivicStackResponse` via VCR
- Blocked-response fixture triggers exponential backoff and ultimately raises `ScraperBlockedError`
- CI green with `PLAYWRIGHT_PROXY_URL` env var documented

---

**Sprint 1 shared done conditions (Days 8–9: integration + CI)**
- End-to-end test harness in `scripts/test_module.py` runs all three modules against VCR fixtures
- GitHub Actions runs full suite in under 5 minutes
- No live portal calls in any CI step
- Rate limit validation documented per module
- Unified OpenAPI spec (Day 10) auto-generated from FastAPI and published to `docs/openapi.json`

---

## Sprint 2 — Docs, Launch, and HalalKah Integration
**Appetite:** 4 days (Days 11–14) · **Phase:** 1 close-out
**Owner:** Core maintainer(s)

### Problem
A working repo that no one knows about, and that halalkah.id is not yet using, is not a shipped
product. This sprint makes the repo public-ready and delivers the first real consumer integration.

### Outputs

| Day | Output | Detail |
|---|---|---|
| 11 | Root README | Why → What → How → Modules table → Quick start (pip install, mcp add) |
| 11 | Per-module docs | `modules/*/README.md` following module-spec template |
| 11 | CONTRIBUTING.md complete | Module contract, PR checklist, DEGRADED policy, 60-day archival rule |
| 12 | HalalKah integration | Wire halalkah.id to `bpjph` + `bpom` modules; remove bespoke scraper; smoke test in staging |
| 13 | Public launch | Repo published; posts to IndieHackers Indonesia, Hacker News (Show HN), GitHub Explore |
| 14 | Issue triage | Label `good-first-issue`; draft Phase 2 module tickets; write Phase 2 scoping notes |

### Done conditions
- `README.md` includes working pip install snippet and `claude mcp add` snippet
- halalkah.id staging smoke test passes with civic-stack as data layer
- Repo is public with at least one `good-first-issue` labelled
- Phase 2 tickets exist as GitHub Issues

---

## Sprint 3 — Phase 2 Modules: OJK + OSS-NIB + LPSE + KPU
**Appetite:** 4 weeks (Weeks 3–6) · **Phase:** 2
**Owner:** Community contributors + core review

### Problem
Phase 1 unblocks halalkah.id and AmanKah. Phase 2 expands civic-stack's coverage to financial
licensing, business identity, procurement, and election data — enabling legalkah.id deepening,
IzinKah, TerpercayaKah, and BenarKah.

### Module shapes (parallel tracks — each is a self-contained contributor PR)

#### `modules/ojk/`
**Source:** OJK licensed institution registry
**Method:** REST + light scrape for gaps
**Key outputs:** Institution name · license type · license status · regulated products
**MCP tools:** `check_ojk_license(name_or_id)` · `search_ojk_institutions(type)` · `get_ojk_status(id)`
**Powers:** legalkah.id (financial license verification), AmanKah (unlicensed fintech detection)

#### `modules/oss-nib/`
**Source:** oss.go.id OSS RBA — public search tier only (no login)
**Method:** Playwright form submission
**Key outputs:** NIB number · company name · business classification · basic status
**MCP tools:** `lookup_nib(company_name)` · `verify_nib(nib_number)`
**Powers:** IzinKah, SahKah
**Note:** Confirm with legalkah.id team that public tier (name → NIB → status) is sufficient for v1
before investing in login-tier access.

#### `modules/lpse/`
**Source:** 500+ regional lpse.*.go.id portals
**Method:** Standardized parser across shared LPSE portal structure
**Key outputs:** Vendor name · contract value · contract status · procurement category · issuing agency
**MCP tools:** `search_lpse_vendor(name)` · `get_lpse_contracts(vendor_id)` · `search_lpse_procurement(keyword)`
**Powers:** TerpercayaKah (vendor trust), BenarKah
**Note:** lpse module is an aggregator — it must handle portal-not-responding gracefully and
return partial results with confidence < 1.0.

#### `modules/kpu/`
**Source:** KPU open data REST API (clean API exists — no scraping needed)
**Method:** REST wrapper + normalization
**Key outputs:** Candidate profile · election results · campaign finance summary
**MCP tools:** `get_candidate(name_or_id)` · `get_election_results(region, year)` · `get_campaign_finance(candidate_id)`
**Powers:** DPR Watch (candidate research), TerpercayaKah
**Note:** KPU API is the only Phase 2 module requiring no scraping. Ship this first in the sprint
to get a quick win and validate the Phase 2 CI pipeline.

### Sprint 3 done conditions
- All four modules pass module contract (fetch, search, MCP, VCR fixtures, README)
- CI green for all four
- Each module deployed to Railway (per-module Dockerfile)
- OpenAPI spec updated with Phase 2 routes
- Module registry in README updated

---

## Sprint 4 — Phase 3 Enrichment: LHKPN + BPS + BMKG + SIMBG
**Appetite:** 6 weeks (Weeks 7–12) · **Phase:** 3
**Owner:** Community contributors + core review

### Problem
Phase 3 modules are harder — PDFs, fragmented regional portals, and bulk statistical data — but
they're what enables DPR Watch and the full TerpercayaKah profile. These are greenfield for the
Indonesian civic tech community.

### Module shapes

#### `modules/lhkpn/`
**Source:** elhkpn.kpk.go.id — KPK wealth declarations
**Method:** pdfplumber primary; Claude Vision API fallback for scanned PDFs
**Key outputs:** Official name · position · declaration year · total assets · asset breakdown
**MCP tools:** `get_lhkpn(official_name)` · `search_lhkpn(ministry_or_position)` · `compare_lhkpn(official_id, year_a, year_b)`
**Powers:** DPR Watch (primary), TerpercayaKah
**Complexity note:** PDF extraction pipeline adds the `pdfplumber` + `anthropic` Vision dependency.
This module warrants its own mini-sprint before community handoff.

#### `modules/bps/`
**Source:** BPS statistics API — 1,000+ datasets
**Method:** REST wrapper + schema normalization
**Key outputs:** Dataset name · indicator · region · time series values
**MCP tools:** `search_bps_datasets(keyword)` · `get_bps_indicator(id, region, year_range)` · `list_bps_regions()`
**Powers:** BenarKah (fact-check against official statistics)

#### `modules/bmkg/`
**Source:** BMKG disaster and weather open API
**Method:** REST wrapper (Tier 1 open API — clean)
**Key outputs:** Disaster alerts · weather forecast · earthquake data
**MCP tools:** `get_bmkg_alerts(region)` · `get_weather_forecast(city)` · `get_earthquake_history(region, days)`
**Powers:** Future risk/safety Kah product

#### `modules/simbg/`
**Source:** National building permit system — regional access, fragmented
**Method:** Multi-portal scraper (similar aggregator pattern to lpse)
**Key outputs:** Permit number · permit type · address · status · issuing authority
**MCP tools:** `lookup_building_permit(address_or_id)` · `search_permits_by_area(region)`
**Powers:** IzinKah
**Complexity note:** Most fragmented module in scope. Recommend starting with 3–5 pilot regions
(Jakarta, Surabaya, Bandung, Medan, Makassar) and expanding incrementally.

### Sprint 4 done conditions
- `lhkpn` and `bps` modules merged before week 10 (highest priority)
- `bmkg` and `simbg` follow-on (bmkg is low-risk quick win; simbg is longest tail)
- All merged modules pass module contract
- AmanKah.id live using civic-stack (Sprint 4 success metric per PRD)
- ≥200 GitHub stars by end of Sprint 4

---

## Backlog / Parking Lot

These items are captured but deliberately deferred. Do not let them creep into earlier sprints.

| Item | Why deferred | Revisit |
|---|---|---|
| Caching layer (`cache=` param) | Leave to consumers in v1; add in v2 when consumer patterns are understood | Post Phase 2 |
| MCP stdio transport (vs HTTP) | HTTP is better for multi-user Railway deploy; stdio is a local-dev convenience | After launch, based on community requests |
| OSS-NIB login tier | Public search tier likely sufficient for SahKah v1; confirm before building auth flow | After SahKah v1 ships |
| Data warehouse / persistence | Explicitly out of scope per PRD. Consumers own persistence. | Never (PRD non-goal) |
| Frontend / UI | Out of scope per PRD. CLI debug tooling in `scripts/` is the limit. | Never (PRD non-goal) |
| pasal.id legal text modules | pasal.id's domain; cross-link and co-promote, do not duplicate | Never (PRD non-goal) |

---

## Sprint Calendar Summary

| Sprint | Weeks | Phase | Key deliverable |
|---|---|---|---|
| 0 — Foundation | Week 1, Day 1 | Pre-launch | Shared schema, HTTP layer, MCP base, CI |
| 1 — Phase 1 Modules | Week 1–2, Days 2–10 | 1 | BPOM + BPJPH + AHU scrapers, MCP servers, tests |
| 2 — Docs + Launch | Week 2, Days 11–14 | 1 close | README, HalalKah integration, public launch |
| 3 — Phase 2 Modules | Weeks 3–6 | 2 | OJK + OSS-NIB + LPSE + KPU |
| 4 — Phase 3 Enrichment | Weeks 7–12 | 3 | LHKPN + BPS + BMKG + SIMBG |

---

## Contribution Model (sprint-level rules)

- Every module addition is a **single PR** against `main`. No partial modules merged.
- The module contract (fetch · search · MCP class · 3× VCR fixtures · README) is the PR checklist.
  A PR that skips any item is not mergeable.
- Maintainer review SLA: **2 weeks** from PR open.
- A module that breaks and stays broken for **60 days** is flagged `DEGRADED` and archived.
- Sprint 3 and Sprint 4 modules are community-owned. Core maintainers review but do not write.
  Core maintainers write Sprint 0, Sprint 1, and Sprint 2 only.
