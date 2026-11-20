// v0.999.47 HOOLA'S OWN EMAIL - the owner's Cloudflare Email Worker (free plan) on her mail domain.
// Cloudflare Email Routing: Catch-all -> Send to a Worker -> this worker. Every mail to <anything>@<domain> is POSTed,
// raw, to the Hoola server, signed with HOOLA_MAIL_SECRET (HMAC-SHA256 over "<recipient>\n<sha256 of the body>").
// It keeps nothing and logs nothing. Mails over 10 MB are refused here.
// Worker settings: HOOLA_SERVER = https://hoola.ainewtika.com, HOOLA_MAIL_SECRET = the same value as the VPS .env (a secret).
const MAX = 10 * 1024 * 1024;

async function hex(buf) {
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async email(message, env) {
    if (message.rawSize > MAX) {
      message.setReject("Message too large");
      return;
    }
    const raw = await new Response(message.raw).arrayBuffer();
    const to = String(message.to || "").trim().toLowerCase();
    const bodyHash = await hex(await crypto.subtle.digest("SHA-256", raw));
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(env.HOOLA_MAIL_SECRET),
      { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const sig = await hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(to + "\n" + bodyHash)));
    const r = await fetch(env.HOOLA_SERVER.replace(/\/$/, "") + "/api/agentmail/inbound", {
      method: "POST",
      headers: { "content-type": "message/rfc822", "x-hoola-to": to, "x-hoola-sig": sig },
      body: raw,
    });
    if (r.status === 403) message.setReject("Unknown address");
  },
};
