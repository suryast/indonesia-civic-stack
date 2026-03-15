# Geo-Restriction Matrix for Indonesian Government Portals

> Last tested: 2026-03-15 from Sydney (AU), Singapore, Jakarta (CloudKilat)

## Test Results

| Portal | Sydney (AU) | Singapore | Jakarta (ID) | Verdict |
|--------|:-----------:|:---------:|:------------:|---------|
| `data.bmkg.go.id` | ✅ 200 | ✅ 200 | ✅ 200 | **No restriction** |
| `jaga.id` (KPK) | ✅ 200 | ✅ 200 | ✅ 200 | **No restriction** |
| `webapi.bps.go.id` | ❌ 403 | ❌ 403 | ❌ 403 | **WAF, not geo** (needs `BPS_API_KEY`) |
| `ahu.go.id` | ❌ timeout | ✅ 200 | ✅ 200 | **Geo-blocked** (SEA+ OK) |
| `elhkpn.kpk.go.id` | ❌ timeout | ✅ 200 | ✅ 200 | **Geo-blocked** (SEA+ OK) |
| `www.ojk.go.id` | ❌ 403 | ❌ 403 | ✅ 200 | **Indonesia-only** |
| `emiten.ojk.go.id` | ❌ | ❌ | ✅ 200 | **Indonesia-only** |
| `sikapiuangmu.ojk.go.id` | ❌ 302→403 | ❌ 302→403 | ✅ 200 | **Indonesia-only** |
| `cekbpom.pom.go.id` | ⚠️ CF | ⚠️ CF | ⚠️ CF | **Cloudflare-protected** (all locations) |
| `lpse.lkpp.go.id` | ❌ timeout | ❌ timeout | ❌ timeout | **Unreliable** (all locations) |
| `lpse.pu.go.id` | ❌ DNS | ❌ DNS | ❌ DNS | **DNS dead** |
| `coretaxdjp.pajak.go.id` | ❌ timeout | ❌ timeout | ❌ timeout | **Unreliable** (all locations) |
| `oss.go.id` | ✅ 200 | ✅ 200 | ✅ 200 | **No restriction** (but JS-rendered) |
| `simbg.pu.go.id` | ⚠️ | ⚠️ | ⚠️ | **Regional portals vary** |

## DNS-Dead Endpoints (March 2026)

These subdomains no longer resolve (NXDOMAIN):

| Endpoint | Was | Replacement |
|----------|-----|-------------|
| `api.ojk.go.id` | REST API for licensed institutions | None — portal pages only |
| `investor.ojk.go.id` | InvestorAlert/getList API | `emiten.ojk.go.id/Satgas/AlertPortal/IndexAlertPortal` |

## Proxy Tiers

Based on testing, portals fall into three tiers:

### Tier 1 — No proxy needed
`data.bmkg.go.id`, `jaga.id`, `oss.go.id`, `infopemilu.kpu.go.id`

### Tier 2 — Singapore/SEA proxy sufficient
`ahu.go.id`, `elhkpn.kpk.go.id`

### Tier 3 — Indonesian IP required
`www.ojk.go.id`, `emiten.ojk.go.id`, `sikapiuangmu.ojk.go.id`

### Tier 4 — Broken regardless of location
`lpse.lkpp.go.id`, `lpse.pu.go.id`, `coretaxdjp.pajak.go.id`

## Recommended Proxy Setup

For full coverage, use an Indonesian VPS (e.g., CloudKilat Jakarta) as a SOCKS5 proxy:

```bash
# On the Indonesian VPS
apt install dante-server
# Configure danted to listen on 127.0.0.1:1080 only

# On your server — SSH tunnel
ssh -N -L 1080:127.0.0.1:1080 user@indonesian-vps

# Set in your app
export PROXY_URL="socks5h://127.0.0.1:1080"
```

A Cloudflare Worker proxy does **not** work for CF-protected portals (CF→CF fetch returns 403/522).

## How to Reproduce

```bash
# Test from any location
curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://www.ojk.go.id"

# Test through SOCKS proxy
curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  --proxy socks5h://127.0.0.1:1080 "https://www.ojk.go.id"
```
