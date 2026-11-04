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
    say("Pair hai (device " + String(st.deviceId).slice(0, 12) + "…) - phone ke Mera PC se hata bhi sakti hain.", "ok");
  } else {
    say("Pair nahi hai - phone par Hoola app > Mera PC > 'PC jodiye' kholkar code yahan daaliye.");
  }
  $("pair").addEventListener("click", pair);
  $("unpair").addEventListener("click", unpair);
}

async function pair() {
  const server = $("server").value.trim().replace(/\/+$/, "");
  const code = $("code").value.trim();
  if (!/^https:\/\/|^http:\/\/(localhost|127\.0\.0\.1)/.test(server)) {
    say("Server https:// se shuru hona chahiye (ya localhost).", "bad");
    return;
  }
  if (!/^\d{6}$/.test(code)) {
    say("6 anko ka code daaliye (phone > Mera PC > 'PC jodiye').", "bad");
    return;
  }
  if (!(await ensureOriginAllowed(server))) {
    say("Is server address ki permission nahi mili - browser ne mana kar diya.", "bad");
    return;
  }
  $("pair").disabled = true;
  say("Jud raha hoon…");
  try {
    const r = await fetch(server + "/api/pc/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, name: "Hoola Extension", os: "Browser extension" }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok || !d.token) {
      say("Pair nahi hua: " + (d.detail || ("HTTP " + r.status)) + " (code purana to nahi? naya code leijiye.)", "bad");
      return;
    }
    await chrome.storage.local.set({ server, token: d.token, deviceId: d.device_id });
    say("Pair ho gaya! Ab kisi bhi page par right-click > 'Hoola ko bhejiye', ya Ctrl+Shift+H.", "ok");
  } catch (e) {
    say("Server tak nahi pahuncha: " + server, "bad");
  } finally {
    $("pair").disabled = false;
  }
}

async function unpair() {
  await chrome.storage.local.remove(["token", "deviceId", "lastConversationId", "lastSentAt"]);
  say("Alag kar diya (yahan se). Phone ke Mera PC se device ko revoke karna behtar hai - wahan se ka poora band hota hai.");
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

init();
