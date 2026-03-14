# Cloudflare Worker Proxy

A reverse proxy that routes requests to Indonesian government portals (`*.go.id`)
through Cloudflare's edge network, which has Points of Presence in Jakarta.

## Why?

Most Indonesian government portals restrict access to Indonesian IP addresses.
If you're deploying from outside Indonesia (or from a datacenter IP), requests
will fail with DNS errors or timeouts.

## Deploy

```bash
cd proxy
npx wrangler deploy
```

## Usage

```bash
# Direct test
curl "https://your-proxy.workers.dev/?url=https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"

# With the SDK (once PROXY_URL env var support is added — see issue #13)
export PROXY_URL="https://your-proxy.workers.dev"
```

## Security

- **Domain allowlist**: Only `*.go.id` domains are proxied
- **No authentication**: Add your own auth header check if exposing publicly
- **CORS**: Enabled for all origins (restrict in production)

## Allowed Domains

- cekbpom.pom.go.id
- sertifikasi.halal.go.id
- ahu.go.id
- api.ojk.go.id / ojk.go.id
- oss.go.id
- lpse.*.go.id (5 portals)
- infopemilu.kpu.go.id
- elhkpn.kpk.go.id
- webapi.bps.go.id
- data.bmkg.go.id
- simbg.pu.go.id
