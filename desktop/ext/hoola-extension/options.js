// W3 options: the pairing flow - the SAME /api/pc/pair the desktop uses, so the extension
// appears on her phone's Mera PC list like any paired PC and can be revoked from there too.
// A custom server address asks for its host permission first (optional_host_permissions).
const DEFAULT_SERVER = "https://hoola.ainewtika.com";

const $ = (id) => document.getElementById(id);

function say(msg, cls) {
  $("state").textContent = msg;
  $("state").className = cls || "";
}

async function init() {
  const st = await chrome.storage.local.get(["server", "token", "deviceId"]);
  $("server").value = st.server || DEFAULT_SERVER;
  if (st.token && st.deviceId) {
    say("Paired (device " + String(st.deviceId).slice(0, 12) + "…) - you can also remove it from My PC on the phone.", "ok");
  } else {
    say("Not paired - on the phone open the Hoola app > My PC > 'Connect a PC' and enter the code here.");
  }
  $("pair").addEventListener("click", pair);
  $("unpair").addEventListener("click", unpair);
  $("engineOn").addEventListener("click", engineOn);
  $("engineOff").addEventListener("click", engineOff);
  showEngine();
}

async function pair() {
  const server = $("server").value.trim().replace(/\/+$/, "");
  const code = $("code").value.trim();
  if (!/^https:\/\/|^http:\/\/(localhost|127\.0\.0\.1)/.test(server)) {
    say("The server address must start with https:// (or be localhost).", "bad");
    return;
  }
  if (!/^\d{6}$/.test(code)) {
    say("Enter the 6-digit code (phone > My PC > 'Connect a PC').", "bad");
    return;
  }
  if (!(await ensureOriginAllowed(server))) {
    say("Permission for this server address was not granted - the browser refused.", "bad");
    return;
  }
  $("pair").disabled = true;
  say("Connecting…");
  try {
    const r = await fetch(server + "/api/pc/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, name: "Hoola Extension", os: "Browser extension" }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || !d.token) {
      say("Pairing failed: " + (d.detail || ("HTTP " + r.status)) + " (is the code old? get a new code.)", "bad");
      return;
    }
    await chrome.storage.local.set({ server, token: d.token, deviceId: d.device_id });
    say("Paired. Now right-click any page > 'Send to Hoola', or press Ctrl+Shift+H.", "ok");
  } catch (e) {
    say("Could not reach the server: " + server, "bad");
  } finally {
    $("pair").disabled = false;
  }
}

async function unpair() {
  await chrome.storage.local.remove(["token", "deviceId", "lastConversationId", "lastSentAt"]);
  say("Unpaired (from here). It is better to also revoke the device from My PC on the phone - that closes it completely.");
}

async function ensureOriginAllowed(server) {
  const origin = server + "/*";
  const has = await chrome.permissions.contains({ origins: [origin] });
  if (has) return true;
  try {
    return await chrome.permissions.request({ origins: [origin] });
  } catch (e) {
    return false;
  }
}

// v0.999.111 page engine 2: her click grants the page access + the debugger permission; off removes both
const ENGINE_PERMS = { permissions: ["debugger"], origins: ["https://*/*", "http://*/*"] };

async function showEngine() {
  const st = await chrome.storage.local.get(["pageEngine", "token"]);
  const has = await chrome.permissions.contains(ENGINE_PERMS);
  $("engineState").textContent = !st.token ? "Pair first (above)." :
    (st.pageEngine === true && has ? "On - Hoola can work on the page you have open." : "Off.");
}

async function engineOn() {
  let ok = false;
  try { ok = await chrome.permissions.request(ENGINE_PERMS); } catch (e) { ok = false; }
  if (!ok) { $("engineState").textContent = "Chrome did not grant it - nothing changed."; return; }
  await chrome.storage.local.set({ pageEngine: true });
  showEngine();
}

async function engineOff() {
  await chrome.storage.local.set({ pageEngine: false });
  try { await chrome.permissions.remove(ENGINE_PERMS); } catch (e) { /* already removed */ }
  showEngine();
}

init();
