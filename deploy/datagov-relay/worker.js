// v0.756 DATA.GOV.IN RELAY - the owner's own Cloudflare Worker (free plan). NIC's data centre drops connections from
// cloud servers like the Hoola VPS, so the VPS asks this worker and the worker asks api.data.gov.in.
// It forwards ONLY GET /resource/... and /lists to api.data.gov.in, keeps nothing, logs nothing, and adds nothing.
// The data.gov.in key stays in the VPS .env; it passes through here inside the request only.
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method !== "GET" || !(url.pathname.startsWith("/resource/") || url.pathname === "/lists")) {
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
