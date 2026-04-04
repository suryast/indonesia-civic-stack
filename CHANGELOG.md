# Changelog

## Unreleased (2026-04-04)

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
