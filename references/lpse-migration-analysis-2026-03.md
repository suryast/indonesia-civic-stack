# LPSE Network Migration Analysis — March 2026

## Summary

LKPP's migration from individual `lpse.*.go.id` domains to `inaproc.id` has broken the entire LPSE procurement network for automated access. 589 regional portals are inaccessible.

## Root Cause

LKPP CNAMEd individual ministry LPSE domains (e.g. `lpse.kemenkeu.go.id`, `lpse.jatimprov.go.id`) to `ars.inaproc.id`. Because the source domains are on different Cloudflare zones than `ars.inaproc.id`, CF returns **"CNAME Cross-User Banned"** (HTTP 403).

This is a Cloudflare configuration error — the target zone needs to allowlist the source domains via [Cloudflare for SaaS](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/) or equivalent.

## Portal Status

| Domain | DNS | HTTP | Notes |
|--------|-----|------|-------|
| lpse.lkpp.go.id | ❌ Dead | — | Old central portal, no longer resolves |
| lpse.pu.go.id | ❌ Dead | — | Ministry of Public Works |
| lpse.kominfo.go.id | ❌ Dead | — | Ministry of Communications |
| lpse.kemenkeu.go.id | CNAME → ars.inaproc.id | 403 | CF cross-user ban |
| lpse.kemkes.go.id | CNAME → ars.inaproc.id | 403 | CF cross-user ban |
| lpse.jatimprov.go.id | CNAME → ars.inaproc.id | 403 | CF cross-user ban (confirmed via Playwright) |
| lpse.bappenas.go.id | CNAME → ars.inaproc.id | 403 | CF cross-user ban |
| lpse.jakarta.go.id | ? | timeout | Previously working, now unreachable |
| lpse.polri.go.id | ✅ | 404 | Resolves but eproc4 path gone |
| spse.inaproc.id | ✅ CF proxy | 200* | Next.js directory only (*CF Turnstile challenge for bots) |
| ars.inaproc.id | ✅ CF proxy | 302→500 | Pomerium SSO protected (internal admin) |
| inaproc.id | ✅ 162.159.140.153 | 403 | CF Turnstile challenge |

## Mass Check Results (20 portals via Jakarta proxy)

- **15** returned `000` (connection timeout / DNS dead)
- **3** returned `403` (CF challenge / cross-user ban)
- **1** returned `404` (alive but eproc4 removed)
- **1** returned `200` (spse.inaproc.id directory only)
- **0** returned usable data

## Access Methods Tested

| Method | Result |
|--------|--------|
| curl direct (Sydney) | DNS dead or timeout |
| curl via Jakarta SOCKS5 proxy | 403 CF challenge on all surviving portals |
| Playwright headless via proxy | "CNAME Cross-User Banned" |
| Playwright headless direct | CF Turnstile challenge (empty page) |
| spse.inaproc.id JS chunk extraction | ✅ Got 589 portal URLs, no tender data |

## New Architecture

```
spse.inaproc.id          → Next.js SSR app (directory of LPSE instances)
ars.inaproc.id           → Pomerium-protected admin portal  
api-spse.inaproc.id      → Returns 403 (not public)
inaproc.id               → CF Turnstile challenge
```

- Build ID: `0eZSZ26KfOfUVQdTM2qff`
- GA: `G-KLDH3FQ7DR`
- Data is server-rendered via React Server Components (RSC), not REST API
- Portal is a directory listing LPSE instances, not a tender search engine

## 589 Portal URLs

Extracted from `spse.inaproc.id/_next/static/chunks/785-e33b530dc9e31e50.js` (206KB).

Includes:
- ~570 `lpse.*.go.id` domains (kabupaten, kota, provinsi, kementerian)
- ~4 `eproc.*.go.id` domains
- ~3 `spse.*.go.id` domains
- ~3 dev/training instances (`spse-latihan.eproc.dev`, etc.)

Full list saved at: `references/lpse-portal-urls-2026-03.txt`

## SPSE API (when accessible)

The old eproc4 API endpoints are unchanged on portals that still serve them:

```
GET /eproc4/dt/rekanan?term=<keyword>&draw=1&start=0&length=10  → vendor search
GET /eproc4/dt/tender?term=<keyword>&draw=1&start=0&length=10  → tender search
GET /eproc4/tender/{id}/view                                    → tender detail
GET /eproc4/rekanan/{id}/view                                   → vendor detail
```

## Recommendation

1. Keep LPSE adapter in civic-stack with current portal list
2. Monitor `spse.inaproc.id` for architecture changes (new API?)
3. Watch for LKPP fixing CF CNAME config — portals should resume immediately
4. LPSE signal monitor status: ❌ until portals accessible again
5. Consider filing issue with LKPP about CF misconfiguration

---

*Analysis date: 2026-03-16*
*Analyst: Polycat (civic-stack maintainer)*
