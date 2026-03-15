/**
 * Cloudflare Worker proxy for indonesia-civic-stack.
 * Forwards requests to Indonesian government portals (*.go.id)
 * through Cloudflare's edge network (Jakarta PoP).
 *
 * Usage: GET https://civic-stack-proxy.workers.dev/?url=https://cekbpom.pom.go.id/...
 * Or: POST with same ?url= param and body forwarded.
 */

const ALLOWED_ORIGINS = [
  'https://datarakyat.id',
  'https://halalkah.id',
  'https://legalkah.id',
];

const ALLOWED_DOMAINS = [
  'cekbpom.pom.go.id',
  'sertifikasi.halal.go.id',
  'halal.go.id',
  'ahu.go.id',
  'api.ojk.go.id',
  'ojk.go.id',
  'sikapiuangmu.ojk.go.id',
  'oss.go.id',
  'lpse.lkpp.go.id',
  'lpse.pu.go.id',
  'lpse.kemenkeu.go.id',
  'lpse.kominfo.go.id',
  'lpse.kemenkes.go.id',
  'infopemilu.kpu.go.id',
  'kpu.go.id',
  'elhkpn.kpk.go.id',
  'kpk.go.id',
  'www.kpk.go.id',
  'webapi.bps.go.id',
  'bps.go.id',
  'www.bps.go.id',
  'data.bmkg.go.id',
  'bmkg.go.id',
  'coretaxdjp.pajak.go.id',
  'pajak.go.id',
  'simbg.pu.go.id',
  'jakevo.jakarta.go.id',
  'simbg.surabaya.go.id',
  'simbg.bandung.go.id',
  'simbg.makassar.go.id',
  'simbg.pemkomedan.go.id',
  'gis.bnpb.go.id',
  'bnpb.go.id',
  'data.bnpb.go.id',
];

export default {
  async fetch(request) {
    const origin = request.headers.get('Origin') || '';
    const corsOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': corsOrigin,
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    const url = new URL(request.url);
    const targetUrl = url.searchParams.get('url');

    if (!targetUrl) {
      return new Response(JSON.stringify({
        error: 'Missing ?url= parameter',
        usage: 'GET /?url=https://cekbpom.pom.go.id/...',
        allowed_domains: ALLOWED_DOMAINS,
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    let target;
    try {
      target = new URL(targetUrl);
    } catch {
      return new Response(JSON.stringify({ error: 'Invalid URL' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Domain allowlist — match exact or subdomain
    const hostname = target.hostname;
    if (!ALLOWED_DOMAINS.some(d => hostname === d || hostname.endsWith('.' + d))) {
      return new Response(JSON.stringify({
        error: 'Domain not allowed',
        domain: hostname,
        allowed: ALLOWED_DOMAINS,
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Build clean headers — only forward safe ones, set correct Host
    const outHeaders = new Headers({
      'Host': target.host,
      'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': request.headers.get('Accept') || 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
      'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
      'Accept-Encoding': 'gzip, deflate, br',
    });

    // Forward Content-Type for POST/PUT
    const ct = request.headers.get('Content-Type');
    if (ct) outHeaders.set('Content-Type', ct);

    // Forward cookies if present
    const cookie = request.headers.get('Cookie');
    if (cookie) outHeaders.set('Cookie', cookie);

    try {
      const response = await fetch(target.toString(), {
        method: request.method,
        headers: outHeaders,
        body: ['GET', 'HEAD'].includes(request.method) ? null : request.body,
        redirect: 'follow',
      });

      // Return with CORS headers
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('Access-Control-Allow-Origin', corsOrigin);
      responseHeaders.set('X-Proxied-Via', 'civic-stack-proxy');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({
        error: 'Upstream request failed',
        detail: err.message,
        target: target.toString(),
      }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
