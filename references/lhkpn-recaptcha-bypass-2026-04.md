# LHKPN reCAPTCHA v3 Bypass — Technical Reference

**Date:** 2026-04-01
**Status:** ✅ Working
**Module:** `civic_stack/lhkpn/scraper.py`

## Background

KPK's e-LHKPN portal (`elhkpn.kpk.go.id`) added reCAPTCHA v3 (invisible, score-based) to
the public e-Announcement search sometime in late 2025/early 2026. This blocked all
programmatic access to wealth declaration data.

The module was deprecated in v1.0.0 (2026-03-30) and restored in v1.1.1 (2026-04-01).

## How It Works

### Portal Structure

The e-Announcement search lives on the login page (`/portal/user/login#announ`), not behind
authentication. It's a public search form embedded in the same page as the login form.

### reCAPTCHA Configuration

- **Type:** reCAPTCHA v3 (invisible, score-based)
- **Site key:** `6LfANPQrAAAAAFAKhYMdri6OAuMOPZZorjsCqUGk`
- **Action:** `announcement`
- **Enforcement:** Server-side — POST without valid token returns 303 redirect back to login

There's also a legacy reCAPTCHA v2 checkbox (site key `6Ler104UAAAAAIy94JTYV-yLDuoklciSupbbD4-C`)
used for the login form itself, but the announcement search only uses v3.

### Solution: Playwright Headless Browser

1. Launch headless Chromium via Playwright
2. Navigate to login page (`wait_until="domcontentloaded"` — `networkidle` times out)
3. Wait for `grecaptcha.execute` to be available
4. Fill form fields (`CARI[NAMA]`, optionally `CARI[TAHUN]`, `CARI[LEMBAGA]`)
5. Execute `grecaptcha.execute(siteKey, {action: 'announcement'})` → get token
6. Set token in hidden field `g-recaptcha-response-announ`
7. Submit form via `document.getElementById("ajaxFormCari").submit()` (causes page navigation)
8. Parse the result table

### Table Structure (14 columns)

The result table has hidden columns (displayed via CSS `display:none`):

| Index | Content | Visible |
|-------|---------|---------|
| 0 | Report hash | Hidden |
| 1 | Report ID (numeric) | Hidden |
| 2 | Unknown | Hidden |
| 3 | Year | Hidden |
| 4 | Flag (R) | Hidden |
| 5 | Row number | Visible |
| 6 | Nama (name) | Visible |
| 7 | Lembaga (institution) | Visible |
| 8 | Unit Kerja (work unit) | Visible |
| 9 | Jabatan (position) | Visible |
| 10 | Tanggal Lapor (report date) | Visible |
| 11 | Jenis Laporan (report type) | Visible |
| 12 | Total Harta Kekayaan (total assets) | Visible |
| 13 | Aksi (action buttons) | Visible |

### Download Button IDs

Download buttons have `data-id` attributes containing base64-encoded report references
(e.g., `dGluSlYzUmlpZXlyUHdUMzlQRTU5QT09`). These are used for PDF download/preview.

## Key Gotchas

1. **`networkidle` times out** — KPK site has slow/hanging resources. Use `domcontentloaded`.
2. **AJAX vs navigation** — The page JS uses `ng.LoadAjaxContentPost` for AJAX updates, but
   calling `form.submit()` directly bypasses this and triggers a full page navigation. Both work,
   but navigation is more reliable for scraping (full page with results).
3. **Rate limiting** — Be conservative. Module uses 1 request per 4 seconds.
4. **No geo-blocking** — Works from Australian IPs (no proxy needed).

## Dependencies

```
pip install playwright
playwright install chromium
```

## Test Results (2026-04-01)

```
fetch('Prabowo') → KEVIN WIDYANDRA PRABOWO | MANAGER | PT JASA MARGA | Rp 483,160,334
search('Jokowi') → 6 results including EKO JOKOWIYONO | TNI | Rp 2,017,908,793
```
