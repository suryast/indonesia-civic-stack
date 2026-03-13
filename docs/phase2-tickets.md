# Phase 2 Module Tickets

> These are the GitHub Issues to open on public launch day (Day 14).
> Each is a `good-first-issue` for community contributors.
> Copy each section into a GitHub Issue with the labels indicated.

---

## Issue 1 — `modules/ojk/`: OJK licensed institution registry

**Labels:** `module-proposal`, `phase-2`, `good-first-issue`
**Milestone:** Phase 2

### What

Add a `modules/ojk/` module wrapping the OJK licensed institution registry.
OJK publishes a list of all licensed banks, fintech lenders, insurers,
investment managers, and payment providers.

### Source

- Portal: https://ojk.go.id/id/kanal/perbankan/Pages/Bank-Umum.aspx
- Also: https://apps.ojk.go.id/AplikasiIKHSAT/ (investasi ilegal check)
- Method: REST API (partial) + scrape for gaps
- Auth: None required

### Key outputs

```python
{
  "institution_name": str,
  "license_no": str,
  "institution_type": str,   # "Bank Umum" | "BPR" | "Fintech P2P" | "Asuransi" | ...
  "license_status": str,     # ACTIVE | REVOKED | SUSPENDED
  "regulated_products": list[str],
  "ojk_category": str,
}
```

### MCP tools to implement

- `check_ojk_license(name_or_id)` — single institution lookup
- `search_ojk_institutions(type)` — search by institution type
- `get_ojk_status(id)` — status only

### Powers

a downstream product (financial license verification), consumer safety app (unlicensed fintech alert)

### Acceptance criteria

Full module contract: fetch, search, MCP server, 3× VCR fixtures, README.

---

## Issue 2 — `modules/oss-nib/`: OSS RBA business identity (NIB)

**Labels:** `module-proposal`, `phase-2`, `good-first-issue`
**Milestone:** Phase 2

### What

Add a `modules/oss-nib/` module for OSS RBA (Online Single Submission)
NIB (Nomor Induk Berusaha) business identity lookup. Public search tier
(company name → NIB → basic status) — no login required for this tier.

### Source

- Portal: https://oss.go.id/informasi/pencarian-nib
- Method: Playwright (JS-rendered form)
- Auth: None for public search tier (confirm NIB number + basic status is sufficient for business verification app v1)

### Key outputs

```python
{
  "nib": str,                # e.g. "1234567890123"
  "company_name": str,
  "business_type": str,      # KBLI classification
  "risk_level": str,         # "Rendah" | "Menengah Rendah" | "Menengah Tinggi" | "Tinggi"
  "license_status": str,     # ACTIVE | EXPIRED | REVOKED
  "domicile": str,
}
```

### MCP tools to implement

- `lookup_nib(company_name)` — company name → NIB
- `verify_nib(nib_number)` — NIB → basic status

### Powers

license verification app, business verification app

### Open question to resolve before implementing

Confirm with downstream team: is the public search tier (name → NIB → status)
sufficient for business verification app v1, or do we need the authenticated tier for full detail?
Comment on this issue with the answer before starting implementation.

---

## Issue 3 — `modules/lpse/`: Government e-procurement aggregator

**Labels:** `module-proposal`, `phase-2`
**Milestone:** Phase 2

### What

Add a `modules/lpse/` module aggregating vendor and contract data across
500+ regional `lpse.*.go.id` portals. All LPSE portals share the same
underlying PHP codebase (SPSE) — one parser covers all.

### Source

- Pattern: `https://lpse.{agency}.go.id/eproc4/`
- Known portals: lpse.lkpp.go.id, lpse.pu.go.id, lpse.kominfo.go.id, etc.
- Method: httpx + BeautifulSoup (static HTML)
- Auth: None — public tender data

### Key outputs

```python
{
  "vendor_name": str,
  "vendor_npwp": str,
  "contract_value": int,       # IDR
  "contract_status": str,
  "procurement_category": str,
  "issuing_agency": str,
  "lpse_portal": str,          # Source portal URL
}
```

### MCP tools to implement

- `search_lpse_vendor(name)` — vendor lookup across portals
- `get_lpse_contracts(vendor_id)` — contracts for a vendor
- `search_lpse_procurement(keyword)` — tender search

### Implementation note

This is an aggregator — handle portal-not-responding gracefully and
return partial results with `confidence < 1.0`. Start with 5 major portals:
lkpp.go.id, pu.go.id, kominfo.go.id, kemenkeu.go.id, kemenkes.go.id.

### Powers

TerpercayaKah (vendor trust verification), BenarKah

---

## Issue 4 — `modules/kpu/`: KPU election data API wrapper

**Labels:** `module-proposal`, `phase-2`, `good-first-issue`
**Milestone:** Phase 2

### What

Add a `modules/kpu/` module wrapping the KPU open data REST API.
This is the easiest Phase 2 module — KPU has a clean REST API, no
scraping needed. The module adds a normalized schema + MCP layer.

### Source

- API: https://sirekap-obj-data.kpu.go.id (election results)
- Also: https://infopemilu.kpu.go.id (candidate profiles)
- Method: REST API wrapper — no scraping, no Playwright
- Auth: None

### Key outputs

```python
{
  "candidate_name": str,
  "party": str,
  "election_year": int,
  "region": str,
  "position": str,            # "DPR RI" | "DPRD Provinsi" | "Bupati" | ...
  "vote_count": int | None,
  "elected": bool | None,
}
```

### MCP tools to implement

- `get_candidate(name_or_id)` — candidate profile + election history
- `get_election_results(region, year)` — results for a region/election
- `get_campaign_finance(candidate_id)` — campaign finance summary

### Why start here

KPU is the only Phase 2 module requiring no scraping. It's a fast win
that validates the Phase 2 CI pipeline before tackling Playwright modules.
**Recommended first Phase 2 module to implement.**

### Powers

DPR Watch (candidate research), TerpercayaKah

---

## Issue 5 — Good first issue: Add error cassette to `modules/bpom/` tests

**Labels:** `good-first-issue`, `tests`

### What

The BPOM module test suite is missing an `error.yaml` cassette that covers
the 429 / 503 retry path (the `ScraperBlockedError` flow in `shared/http.py`).

### Steps

1. Add `tests/bpom/cassettes/error.yaml` — a cassette returning HTTP 429
2. Add a test in `tests/bpom/test_bpom.py` verifying that:
   - `fetch()` with the 429 cassette returns `status=ERROR` after retries
   - `error_response()` is returned (not an exception)
3. Run `pytest tests/bpom/ -v` — all tests must pass

### Why this is a good first issue

- Self-contained: one cassette file + one test function
- No Playwright, no live portals
- Good introduction to the VCR cassette format and the `shared/http.py` backoff logic

---

## Issue 6 — Good first issue: Add Camoufox CI installation to Playwright Dockerfiles

**Labels:** `good-first-issue`, `devops`

### What

The BPJPH and AHU Dockerfiles currently install standard Playwright.
Camoufox should be installed as the primary browser driver, with Playwright
as a fallback. Update both Dockerfiles to install camoufox.

### Steps

1. Update `modules/bpjph/Dockerfile` to install camoufox:
   ```dockerfile
   RUN pip install camoufox && python -m camoufox fetch --browser chromium
   ```
2. Update `modules/ahu/Dockerfile` similarly
3. Verify the Docker build works: `docker build -f modules/bpjph/Dockerfile .`
4. Add a smoke test that confirms camoufox is importable inside the container

### Why this is a good first issue

- Dockerfile change only — no Python logic changes needed
- Well-documented in the camoufox README
- High impact: improves scraper resilience for all Playwright-based modules
