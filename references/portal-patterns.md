# Indonesian Government Portal Patterns

> Hard-won knowledge about how `.go.id` portals behave. Read this before writing scrapers.

## Pattern 1: SharePoint Iframes

**Affected:** OJK (waspada investasi)

The main page (`www.ojk.go.id/waspada-investasi/...`) is a SharePoint site that loads actual data in an **iframe** from a completely different subdomain.

```
Main page: www.ojk.go.id/waspada-investasi/id/alert-portal/Pages/default.aspx
  └── iframe: emiten.ojk.go.id/Satgas/AlertPortal/IndexAlertPortal  ← actual data here
```

**Detection:** If Playwright returns HTML with "Please enable JavaScript" on a SharePoint page, check `page.frames` for the real content.

```python
for frame in page.frames:
    if frame.url != page.url:
        html = await frame.content()  # This has the actual data
```

**Lesson:** Always enumerate frames. The main page may be just a shell.

## Pattern 2: reCAPTCHA v3 on Search

**Affected:** LHKPN (elhkpn.kpk.go.id)

The e-Announcement search endpoint (`/portal/user/check_search_announ`) requires a reCAPTCHA v3 token. The portal injects a Google reCAPTCHA script and validates server-side.

**Workaround options:**
1. Browse to the announcement listing page (no captcha) and parse the public listings
2. Use the PDF download endpoint (`/portal/user/preview_laporan_pdf?id_laporan=...`) which doesn't require captcha
3. Accept degraded functionality — list what's publicly visible without search

**Lesson:** Always check if there's a non-search path to the same data.

## Pattern 3: JS-Rendered Search Results

**Affected:** AHU, OSS/NIB, BPJPH

These portals require a real browser because:
- Search forms are React/Vue SPAs
- Results are loaded via XHR after form submission
- Anti-bot checks block non-browser User-Agents

**Required stack:**
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        proxy={"server": "socks5://proxy:1080"},  # NOT socks5h://
        user_agent="Mozilla/5.0 ...",
        locale="id-ID",
    )
```

**Critical:** Chromium's proxy implementation does **not** support `socks5h://` (SOCKS5 with remote DNS). Use `socks5://` instead. The `h` variant is httpx-only.

## Pattern 4: Cloudflare-Protected Portals

**Affected:** BPOM (cekbpom.pom.go.id), some KPU pages

These portals are behind Cloudflare, which means:
1. **CF Worker proxy won't work** — CF→CF fetch returns 403/522 (known Cloudflare limitation)
2. **Direct requests get challenged** — JS challenge or CAPTCHA
3. **Playwright may work** — if Chromium passes the JS challenge

**Lesson:** A CF Worker proxy is useless for CF-protected `.go.id` portals. Use a VPS with SOCKS5 proxy instead.

## Pattern 5: DataTables API Endpoints

**Affected:** BPOM (historical), LPSE, KPU

Some portals use jQuery DataTables with server-side processing. The AJAX endpoint is predictable:

```
GET /eproc4/dt/lelang?draw=1&start=0&length=20
```

Response is JSON with `data`, `recordsTotal`, `recordsFiltered` fields.

**Detection:** View page source, search for `dataTable`, `ajax`, `serverSide`.

**Gotcha:** These endpoints sometimes disappear when portals redesign. The BPOM DataTables endpoint was replaced with a simpler `?q=` search.

## Pattern 6: ASP.NET ViewState

**Affected:** Some OJK subpages

Classic ASP.NET WebForms pages require `__VIEWSTATE` and `__EVENTVALIDATION` tokens for POST requests. These must be extracted from the initial GET response.

```python
soup = BeautifulSoup(resp.text, "html.parser")
viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
```

## Pattern 7: Redirect Chains

**Affected:** OJK (sikapiuangmu → www.ojk.go.id), KPK (/statistik → /publikasi-data/statistik)

Government portals frequently reorganize URLs. Redirects may be:
- HTTP 301/302 (follow with `curl -L`)
- JavaScript `window.location` redirects (need Playwright)
- Meta refresh tags

**Lesson:** When a portal returns a tiny HTML page (<1KB), check for JS/meta redirects before concluding it's broken.

## Anti-Patterns (Things NOT to Do)

1. **Don't hardcode subdomains** — they get retired without notice (`api.ojk.go.id`)
2. **Don't assume JSON APIs exist** — most portals are HTML-only
3. **Don't scrape from non-ID IPs without testing** — check geo-restrictions.md first
4. **Don't use CF Worker proxies for CF-protected portals** — it's a known limitation
5. **Don't disable SSH password auth before verifying key login** — you'll get locked out
6. **Don't trust `200 OK`** — some portals return 200 with an error page body
