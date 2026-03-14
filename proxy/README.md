# Cloudflare Worker Proxy

A reverse proxy that routes requests to Indonesian government portals (`*.go.id`)
through Cloudflare's edge network.

## Why?

Most Indonesian government portals restrict access to Indonesian IP addresses.
If deploying from outside Indonesia, requests fail with DNS errors or timeouts.

## Deploy

```bash
cd proxy
npx wrangler deploy
```

## Usage

```bash
# Direct test
curl "https://your-proxy.workers.dev/?url=https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"

# With the SDK — set PROXY_URL and it auto-detects *.workers.dev as rewrite mode
export PROXY_URL="https://your-proxy.workers.dev"
python -c "from modules.bmkg.scraper import get_latest_earthquake; ..."
```

The SDK auto-detects `*.workers.dev` URLs as rewrite-mode proxies. All HTTP requests
are transparently rewritten to `https://proxy.workers.dev/?url=<encoded-target>`.

Override detection with `PROXY_MODE=connect|rewrite` if needed.

## Limitations

⚠️ **CF-to-CF blocking**: Many Indonesian portals are themselves behind Cloudflare.
CF Workers making `fetch()` calls to other CF-protected origins may receive
403/522/530 errors. This is a known Cloudflare limitation.

**Portals verified working through this proxy:**
- ✅ `data.bmkg.go.id` — Earthquake/weather data (JSON API, no CF protection)

**Portals blocked (behind CF themselves):**
- ❌ `cekbpom.pom.go.id` — 403/522 (CF-protected)
- ❌ `api.ojk.go.id` — 530 (CF origin error)
- ❌ `infopemilu.kpu.go.id` — 403
- ❌ `lpse.*.go.id` — 403
- ❌ `elhkpn.kpk.go.id` — 403

**For production use with CF-protected portals**, use a proper forward proxy:
- Indonesian VPS with SOCKS5/HTTP proxy
- Residential proxy service with Indonesian IPs
- Set `PROXY_URL` to the proxy and `PROXY_MODE=connect`

## Security

- **Domain allowlist**: Only `*.go.id` domains are proxied
- **No authentication**: Add your own auth header check if exposing publicly
- **CORS**: Enabled for all origins (restrict in production)

## Proxy Modes

| Mode | PROXY_URL example | How it works |
|------|-------------------|--------------|
| `rewrite` | `https://x.workers.dev` | Rewrites URL to `?url=<target>` (auto-detected for *.workers.dev) |
| `connect` | `socks5://id-proxy:1080` | Standard HTTP/SOCKS CONNECT proxy (httpx transport) |
| `none` | (unset) | Direct connection |
