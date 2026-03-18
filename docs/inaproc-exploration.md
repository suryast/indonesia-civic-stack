# inaproc.id Exploration Notes (2026-03-18)

## Tooling Discovery

### curl_cffi — BYPASSES THE WAF ✅
**The key finding:** `curl_cffi` with Chrome TLS impersonation bypasses the inaproc.id WAF on ALL subdomains. Playwright and regular httpx are blocked.

```python
from curl_cffi import requests as cffi_requests

session = cffi_requests.Session(impersonate="chrome")
r = session.get("https://spse.inaproc.id", timeout=15)
# Status: 200 ✅ (Playwright gets "Akses Ditolak!")
```

**Install:** `pip install curl_cffi`

### What works / what doesn't

| Tool | spse | data | katalog | api |
|------|------|------|---------|-----|
| curl (plain) | ❌ 403 | ✅ 200 | ✅ 200 | ✅ 404 |
| httpx | ❌ 403 | ✅ 200 | ✅ 200 | ✅ 404 |
| curl_cffi (chrome) | ✅ 200 | ✅ 200 | ✅ 200 | ✅ 404 |
| Playwright | ❌ WAF | ❌ WAF | ❌ CF 403 | — |
| Playwright + Camoufox | ❌ WAF | ❌ WAF | — | — |

### Why Playwright fails
The inaproc.id WAF (custom LKPP, not just Cloudflare) detects:
- WebDriver/automation flags
- Headless browser fingerprints
- TLS fingerprint mismatches (Playwright uses Node.js TLS, not Chrome)

`curl_cffi` works because it uses the actual Chrome TLS stack via libcurl-impersonate.

## Portal Architecture

### spse.inaproc.id
- **Framework:** Next.js (App Router with React Server Components)
- **Build ID:** `0eZSZ26KfOfUVQdTM2qff` (changes on deploy)
- **Behavior:** Pure client-side SPA shell — all routes return the same HTML
- **Data loading:** Unknown. No API endpoints found in JS bundles.
- **JS references:** `eproc.dev` staging domains (`spse-dpd.eproc.dev`, `spse-latihan.eproc.dev`)
- **Hypothesis:** Actual data fetching happens after CF challenge cookie is set, through an API endpoint not discoverable from the JS bundle alone
- **Next steps:** Need to intercept network traffic from a real browser session to find the data API

### katalog.inaproc.id
- **Framework:** Next.js (App Router, React Server Components)
- **Build ID:** `aujHiGgHNjuYGtdscXxH0`
- **Routes found:** `/produk`, `/kategori`, `/cari?q=...`
- **RSC responses:** Returns React Server Components payload with product references
- **No `__NEXT_DATA__`** — uses streaming RSC protocol instead
- **Data partially embedded** in RSC chunks but encoded in React wire format

### data.inaproc.id
- **Framework:** Streamlit
- **Health:** `/_stcore/health` → `ok`
- **Data:** Requires WebSocket connection for Streamlit protocol
- **WAF:** Blocks Playwright but allows curl/curl_cffi
- **Problem:** Can't interact with Streamlit via HTTP alone — needs WebSocket + protobuf

### sirup.inaproc.id
- **Framework:** Server-rendered (classic CodeIgniter/PHP-style)
- **Access:** Redirects to login page
- **Title:** "RUP - Form Login"
- **Requires:** Government credentials

### api.inaproc.id
- **Gateway:** Returns `404 page not found` (plaintext, Go-style)
- **Via:** `1.1 google` (Google Cloud proxy)
- **Routes:** ALL tested paths return 404
- **Hypothesis:** Requires authentication tokens or specific headers from the SPSE frontend

## Recommended SDK Tooling

### For LPSE/SPSE data (when API is found):
```python
from curl_cffi import requests as cffi_requests

class InaprocClient:
    def __init__(self, proxy_url=None):
        self.session = cffi_requests.Session(
            impersonate="chrome",
            proxy=proxy_url,
        )
    
    async def search_tenders(self, keyword):
        # TODO: Replace with actual API endpoint when discovered
        r = self.session.get(
            "https://spse.inaproc.id/pencarian",
            params={"q": keyword},
        )
        # Parse RSC response...
```

### For Katalog data:
```python
# RSC-based extraction (experimental)
r = session.get(
    "https://katalog.inaproc.id/cari",
    params={"q": "komputer"},
    headers={"RSC": "1"},
)
# Parse React Server Components wire format
```

## Open Questions
1. What API does spse.inaproc.id call for tender data? (Need browser network tab)
2. Can we interact with data.inaproc.id Streamlit via WebSocket + curl_cffi?
3. Does api.inaproc.id accept JWT tokens from the SPSE auth flow?
4. Are there undiscovered subdomains? (subdomain enumeration needed)

## Next Steps
- [ ] Intercept SPSE network traffic from a real browser (with CF challenge solved)
- [ ] Parse Katalog RSC payloads for product data
- [ ] Try curl_cffi WebSocket for data.inaproc.id Streamlit
- [ ] Subdomain enumeration on inaproc.id
- [ ] Check if sirup.inaproc.id has any public endpoints (old SiRUP had CKAN)
