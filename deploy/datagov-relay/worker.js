// v0.756 DATA.GOV.IN RELAY - the owner's own Cloudflare Worker (free plan). NIC's data centre drops connections from
// cloud servers like the Hoola VPS, so the VPS asks this worker and the worker asks api.data.gov.in.
// It forwards ONLY GET /resource/... and /lists to api.data.gov.in, keeps nothing, logs nothing, and adds nothing.
// The data.gov.in key stays in the VPS .env; it passes through here inside the request only.
//
// v0.828 + API SETU: apisetu.gov.in drops the VPS the same way (ReadTimeout from the server, 401 in 2 s from anywhere
// else). This SAME worker now also forwards ONLY GET /gstn/v1|v2/taxpayers/<15-character GSTIN> to apisetu.gov.in with
// ONLY the two API Setu headers (X-APISETU-CLIENTID / X-APISETU-APIKEY) - nothing else is passed on, nothing is kept.
// On the VPS: APISETU_GSTN_BASE=https://<this worker>/gstn/v1
const GSTN = /^\/gstn\/v[12]\/taxpayers\/[0-9A-Z]{15}$/;

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method !== "GET") {
      return new Response("Not found", { status: 404 });
    }
    if (GSTN.test(url.pathname)) {
      const headers = { "User-Agent": "Hoola/1.0 (+API Setu relay)", "Accept": "application/json" };
      for (const h of ["X-APISETU-CLIENTID", "X-APISETU-APIKEY"]) {
        const v = request.headers.get(h);
        if (v) headers[h] = v;
      }
      const upstream = await fetch("https://apisetu.gov.in" + url.pathname, { headers });
      return new Response(upstream.body, {
        status: upstream.status,
        headers: { "content-type": upstream.headers.get("content-type") || "application/json", "cache-control": "no-store" },
      });
    }
    if (!(url.pathname.startsWith("/resource/") || url.pathname === "/lists")) {
      return new Response("Not found", { status: 404 });
    }
    const upstream = await fetch("https://api.data.gov.in" + url.pathname + url.search, {
      headers: { "User-Agent": "Hoola/1.0 (+data.gov.in relay)", "Accept": "application/json" },
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") || "application/json", "cache-control": "no-store" },
    });
  },
};
