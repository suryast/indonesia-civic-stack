# Changelog

## 1.2.1 (2026-10-12)

### Security
- Stop trusting caller-supplied `proxy_url` values. The AHU, BPJPH, BPOM, OJK and OSS-NIB REST routers and the standalone AHU/OSS-NIB MCP servers passed any `proxy_url` straight to the HTTP client or browser. A `*.workers.dev` value routed BPOM, BPJPH and OJK lookups (including `check_waspada`) through a caller-controlled URL-rewriting proxy that could return fabricated registration, halal or fraud-list results; other values made the server connect to arbitrary proxy hosts. Caller-supplied proxies must now exactly match `PROXY_URL` or an entry in the new `CIVIC_ALLOWED_PROXIES` (comma-separated full URLs): REST returns HTTP 400 and MCP tools return an `ERROR` envelope otherwise. SDK functions still accept `proxy_url` from library callers unchanged. Reported by Syed Anas Mohiuddin ([@SyedAnas01](https://github.com/SyedAnas01)).

### Changed
- AHU and OSS-NIB browser lookups fall back to `PROXY_URL` when it is a CONNECT proxy, so deployments can configure their proxy server-side.

## 1.2.0 (2026-10-10)

### Changed
- Migrate `SKILL.md` to portable Agent Skills frontmatter, with complete-package installation and source/status-aware usage guidance.
- Reconcile documented inventory with the implementation: 14 SDK modules and 45 unified MCP tools.
- Refactor CLI/server transport dispatch and version reporting; derive health tool counts from the registered MCP inventory.
- Synchronize package, runtime, skill and MCP registry manifest release versions.

### Fixed
- Prevent the default LHKPN regression tests from making live browser requests; exercise browser results and failures with deterministic mocks.
- Repair the OSS NIB monkeypatch target after the `modules` to `civic_stack` package migration.
- Make SDK modules genuinely lazy so a core-only installation does not require Playwright; verify the built wheel separately from the development environment.
- Consolidate the repository REST entry point onto the packaged app and synchronize its OpenAPI version.
- Correct unsupported authentication, rate-limit and SSRF-protection claims; deployments still require their own access controls.
- Enforce offline browser regression failures in CI instead of accepting them silently.
- Refresh vulnerable locked AnyIO, PyJWT, cryptography, MCP, Starlette, urllib3, SoupSieve, Pydantic Settings and VCR.py dependencies, and add an installed-dependency audit to CI.

### Verification scope
- Offline fixtures and transport/package checks do not certify current government portal availability.
- Historical observations below retain their original dates; they are not new liveness checks.

## Changes since 1.1.0 (recorded 2026-04-04)

### Added
- **jdih** — National legal database (peraturan.go.id). Playwright-based scraping for UU, PP, Perpres, Permen. Requires Indonesian proxy.
- **ksei** — Securities depository (web.ksei.co.id). HTML scraping for registered securities + 62 monthly statistics PDFs. No proxy needed.
- **djpb** — Treasury/budget data (data-apbn.kemenkeu.go.id). Clean REST JSON API for APBN budget themes with target/realization/achievement. Requires proxy.

### Fixed
- **bmkg** — Normalizer now extracts `event_date` (YYYY-MM-DD), `event_id` (stable hash), and `disaster_type` from earthquake data. Previously `event_date` was always `None`.
- **ojk** — Updated waspada URLs after portal migration. `sikapiuangmu.ojk.go.id` now redirects to `www.ojk.go.id/waspada-investasi`. `emiten.ojk.go.id` is WAF-blocked.

### Known Issues (Apr 2026 portal changes)
- **ojk** — Waspada portal migrated to SharePoint. No table DOM to scrape — `check_waspada_list()` returns 0 results. Needs scraper rewrite for SharePoint list webparts.
- **ahu** — Search page restructured. Playwright can't locate search input element. Needs selector update.
- **oss_nib** — Same as AHU — page structure changed, Playwright selectors broken.

### Endpoint Reachability (tested 2026-04-04 from Sydney via CloudKilat Jakarta proxy)

| Module | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| bmkg | data.bmkg.go.id | ✅ 200 | No proxy needed |
| bps | webapi.bps.go.id | ✅ 200 | No proxy needed, requires `BPS_API_KEY` |
| bpom | cekbpom.pom.go.id | ✅ 200 | No proxy needed |
| bpjph | cmsbl.halal.go.id | ✅ 200 | No proxy needed |
| kpu | infopemilu.kpu.go.id | ✅ 200 | No proxy needed |
| ksei | web.ksei.co.id | ✅ 200 | No proxy needed |
| djpb | data-apbn.kemenkeu.go.id/be/api | ✅ 200 | Proxy required |
| jdih | peraturan.go.id | ✅ 200 | Proxy + Playwright required |
| ojk | www.ojk.go.id/waspada-investasi | ✅ 200 | HTML loads but SharePoint data requires JS |
| ahu | ahu.go.id | ✅ reachable | Page structure changed |
| oss_nib | oss.go.id | ✅ reachable | Page structure changed |
| lpse | spse.inaproc.id | ✅ reachable | Proxy required |
| simbg | simbg.pu.go.id | untested | |
| lhkpn | elhkpn.kpk.go.id | untested | |

### Dead endpoints
- `api.ojk.go.id` — NXDOMAIN since Feb 2026
- `investor.ojk.go.id` — NXDOMAIN since Feb 2026
- `sikapiuangmu.ojk.go.id` — redirects to www.ojk.go.id/waspada-investasi
- `emiten.ojk.go.id` — WAF "Request Rejected"
