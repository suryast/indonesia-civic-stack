# Endpoint Status — Living Document

> Last verified: 2026-03-15

## Active Endpoints

| Module | Endpoint | Status | Notes |
|--------|----------|--------|-------|
| **BMKG** | `data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json` | ✅ Active | Public JSON, no auth |
| **BMKG** | `data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json` | ✅ Active | Public JSON, no auth |
| **BPS** | `webapi.bps.go.id/v1/api/list/model/statictable/...` | ✅ Active | Requires `BPS_API_KEY` (free registration) |
| **OJK** | `emiten.ojk.go.id/Satgas/AlertPortal/IndexAlertPortal` | ✅ Active | 11,383 illegal entities, ID IP required |
| **OJK** | `www.ojk.go.id/id/berita-dan-kegiatan/siaran-pers` | ✅ Active | Press releases, ID IP required |
| **OJK** | `www.ojk.go.id/id/kanal/perbankan/data-dan-statistik/Pages/Direktori.aspx` | ✅ Active | Licensed institutions, ID IP required |
| **AHU** | `ahu.go.id` | ✅ Active | JS-rendered (Playwright required), SEA+ IP |
| **LHKPN** | `elhkpn.kpk.go.id/portal/user/login#announ` | ⚠️ Degraded | reCAPTCHA v3 on search, SEA+ IP |
| **KPK** | `www.kpk.go.id/id/publikasi-data/statistik` | ✅ Active | Moved from `/id/statistik/penindakan` |
| **KPU** | `infopemilu.kpu.go.id/Pemilu/Peserta_pemilu` | ✅ Active | Moved from `/Pemilu/caleg/list` |
| **BPOM** | `cekbpom.pom.go.id/all-produk?q={keyword}` | ⚠️ CF-protected | Moved from `/index.php/home/produk/...` |
| **BPJPH** | `sertifikasi.halal.go.id` | ✅ Active | Playwright required |
| **OSS** | `oss.go.id` | ✅ Active | Playwright required |
| **SIMBG** | `simbg.pu.go.id` | ⚠️ Regional | Regional portals vary |

## Dead Endpoints

| Endpoint | Died | Was | Replacement |
|----------|------|-----|-------------|
| `api.ojk.go.id` | ~2026-03 | REST API (`/v1/lembaga/pencarian`) | Portal pages on `www.ojk.go.id` |
| `investor.ojk.go.id` | ~2026-03 | `/InvestorAlert/getList` JSON API | `emiten.ojk.go.id/Satgas/AlertPortal/IndexAlertPortal` |
| `sikapiuangmu.ojk.go.id/FrontEnd/Waspada/GetData` | ~2026-03 | DataTables JSON endpoint | Redirects to OJK SharePoint page |
| `www.kpk.go.id/id/statistik/penindakan` | ~2026-03 | KPK prosecution stats | `/id/publikasi-data/statistik` |
| `lpse.pu.go.id` | ~2026-03 | Ministry of Public Works LPSE | DNS dead |

## URL Migration History

| Module | Old URL | New URL | When |
|--------|---------|---------|------|
| BPOM | `/index.php/home/produk/1/{keyword}/...` | `/all-produk?q={keyword}` | ~2026-01 |
| KPU | `/Pemilu/caleg/list` | `/Pemilu/Peserta_pemilu` | ~2026-02 |
| BMKG | `/DataMKG/MEWS/Warning/cuacasignifikan.json` | `/DataMKG/TEWS/gempadirasakan.json` | ~2026-01 |
| KPK stats | `/id/statistik/penindakan` | `/id/publikasi-data/statistik` | ~2026-03 |
| OJK waspada | `investor.ojk.go.id/InvestorAlert/getList` | `emiten.ojk.go.id/Satgas/AlertPortal/...` | ~2026-03 |

## BPS API Key

Register for free at: https://webapi.bps.go.id/developer/register

```bash
export BPS_API_KEY="your-key-here"
```

## Monitoring

Indonesian government portals change URLs frequently without notice. Check this document if a module starts returning 404/403 errors. Common patterns:
- ASP.NET portals add `/Pages/default.aspx` or remove it
- Subdomains get retired (api.ojk.go.id) without redirects
- Content moves behind iframes or JS rendering
- Cloudflare gets added to previously open portals
