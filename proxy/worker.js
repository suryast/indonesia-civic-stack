/**
 * Cloudflare Worker proxy for indonesia-civic-stack.
 * Forwards requests to Indonesian government portals (*.go.id)
 * through Cloudflare's edge network (Jakarta PoP).
 *
 * Usage: GET https://civic-stack-proxy.workers.dev/?url=https://cekbpom.pom.go.id/...
 * Or: POST with same ?url= param and body forwarded.
 */

const ALLOWED_DOMAINS = [
  'cekbpom.pom.go.id',
  'sertifikasi.halal.go.id',
  'ahu.go.id',
  'api.ojk.go.id',
  'ojk.go.id',
  'oss.go.id',
  'lpse.lkpp.go.id',
  'lpse.pu.go.id',
  'lpse.kemenkeu.go.id',
  'lpse.kominfo.go.id',
  'lpse.kemenkes.go.id',
  'infopemilu.kpu.go.id',
  'elhkpn.kpk.go.id',
  'webapi.bps.go.id',
  'data.bmkg.go.id',
  'simbg.pu.go.id',
];

export default {
  async fetch(request) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': '*',
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

    // Domain allowlist
    if (!ALLOWED_DOMAINS.some(d => target.hostname === d || target.hostname.endsWith('.' + d))) {
      return new Response(JSON.stringify({
        error: 'Domain not allowed',
        domain: target.hostname,
        allowed: ALLOWED_DOMAINS,
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Forward headers (strip CF-specific)
    const headers = new Headers(request.headers);
    headers.set('Host', target.host);
    headers.delete('cf-connecting-ip');
    headers.delete('cf-ipcountry');
    headers.delete('cf-ray');
    headers.delete('x-forwarded-for');
    headers.delete('x-real-ip');

    // Set Indonesian locale headers
    headers.set('Accept-Language', 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7');

    try {
      const response = await fetch(target.toString(), {
        method: request.method,
        headers,
        body: ['GET', 'HEAD'].includes(request.method) ? null : request.body,
        redirect: 'follow',
      });

      // Return with CORS headers
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('Access-Control-Allow-Origin', '*');
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
