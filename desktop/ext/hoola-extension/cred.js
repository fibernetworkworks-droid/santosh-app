// v0.999.54 HOOLA CRED autofill: her sign-ins on the site she is on, filled ONLY when she clicks Fill.
// The master password is typed here; the vault key is unwrapped here (WebCrypto) and kept for 15 minutes in
// chrome.storage.session (memory only, wiped when the browser closes, never readable by web pages).
// The server only ever sends the encrypted vault (/api/cred/device/vault with this paired device's token).
(() => {
  const SERVER_DEFAULT = "https://hoola.ainewtika.com";
  const KEEP_MS = 15 * 60 * 1000;
  const te = new TextEncoder(), td = new TextDecoder();
  const el = (id) => document.getElementById(id);
  const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  const b64 = (u8) => { let s = ""; for (const b of u8) s += String.fromCharCode(b); return btoa(s); };

  function regHost(u) {
    let h = "";
    try { h = new URL(/:\/\//.test(u) ? u : "https://" + u).hostname.toLowerCase(); } catch { return ""; }
    const p = h.replace(/^www\./, "").split(".").filter(Boolean);
    if (p.length >= 3 && ["gov", "co", "nic", "org", "ac", "net", "edu"].includes(p[p.length - 2]) && p[p.length - 1].length === 2) return p.slice(-3).join(".");
    return p.slice(-2).join(".");
  }
  async function vault() {
    const st = await chrome.storage.local.get(["server", "token"]);
    if (!st.token) throw new Error("Pair this browser first (Options).");
    const r = await fetch((st.server || SERVER_DEFAULT).replace(/\/+$/, "") + "/api/cred/device/vault",
      { headers: { Authorization: "Bearer " + st.token }, cache: "no-store" });
    if (r.status === 401) throw new Error("This browser was removed - pair it again in Options.");
    if (!r.ok) throw new Error("Hoola Cred is not reachable right now.");
    return r.json();
  }
  async function vkFromSession() {
    const s = await chrome.storage.session.get(["credVk", "credAt"]);
    if (!s.credVk || Date.now() - (s.credAt || 0) > KEEP_MS) { await chrome.storage.session.remove(["credVk", "credAt"]); return null; }
    return crypto.subtle.importKey("raw", unb64(s.credVk), { name: "AES-GCM" }, false, ["decrypt"]);
  }
  async function unlock(pw, meta) {
    const base = await crypto.subtle.importKey("raw", te.encode(pw), "PBKDF2", false, ["deriveKey"]);
    const kek = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: unb64(meta.salt), iterations: meta.iters },
      base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
    const raw = new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(meta.wrapped.iv) }, kek, unb64(meta.wrapped.ct)));
    await chrome.storage.session.set({ credVk: b64(raw), credAt: Date.now() });
    const k = await crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["decrypt"]);
    raw.fill(0);
    return k;
  }
  async function items(vk, meta) {
    const out = [];
    for (const it of meta.items || []) {
      try {
        const d = JSON.parse(td.decode(new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(it.iv) }, vk, unb64(it.ct)))));
        out.push(d);
      } catch { /* an item this key cannot open is skipped */ }
    }
    return out;
  }
  // runs INSIDE the page: put the values into the visible sign-in fields; the page never gets them otherwise
  function fillPage(user, pass) {
    const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== "hidden"; };
    const set = (e, v) => {
      const proto = Object.getPrototypeOf(e);
      const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
      e.focus(); setter ? setter.call(e, v) : (e.value = v);
      e.dispatchEvent(new Event("input", { bubbles: true })); e.dispatchEvent(new Event("change", { bubbles: true }));
    };
    const pw = [...document.querySelectorAll('input[type="password"]')].find(vis);
    const scope = (pw && pw.form) || document;
    const users = [...scope.querySelectorAll('input[type="email"],input[type="text"],input[type="tel"],input:not([type])')]
      .filter((e) => vis(e) && (!pw || (e.compareDocumentPosition(pw) & Node.DOCUMENT_POSITION_FOLLOWING)));
    const u = users.find((e) => /user|email|login|mobile|phone|id/i.test(e.name + e.id + e.autocomplete + e.placeholder)) || users[users.length - 1];
    let n = 0;
    if (u && user) { set(u, user); n++; }
    if (pw && pass) { set(pw, pass); n++; }
    return n;
  }
  async function totp(v) {
    let t = String(v || "").trim();
    if (/^otpauth:\/\//i.test(t)) { try { t = new URL(t).searchParams.get("secret") || ""; } catch { t = ""; } }
    t = t.replace(/[\s-]/g, "").toUpperCase(); if (!t) return "";
    const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = "", bytes = [];
    for (const c of t.replace(/=+$/, "")) { const i = A.indexOf(c); if (i < 0) return ""; bits += i.toString(2).padStart(5, "0"); }
    for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
    const key = await crypto.subtle.importKey("raw", new Uint8Array(bytes), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
    let c = Math.floor(Date.now() / 30000); const msg = new Uint8Array(8);
    for (let i = 7; i >= 0; i--) { msg[i] = c & 0xff; c = Math.floor(c / 256); }
    const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, msg)); const o = mac[19] & 15;
    return String(((mac[o] & 127) << 24 | mac[o + 1] << 16 | mac[o + 2] << 8 | mac[o + 3]) % 1e6).padStart(6, "0");
  }

  const say = (m, bad) => { el("credstate").textContent = m; el("credstate").style.color = bad ? "#D93C3C" : "#5B5675"; };
  async function show(tab, vk, meta) {
    const site = regHost(tab.url || "");
    const all = await items(vk, meta);
    const mine = all.filter((d) => (d.urls || []).some((u) => regHost(u) === site));
    el("credlock").hidden = true;
    const box = el("credlist");
    box.innerHTML = "";
    if (!site) { say("Open a website first."); return; }
    if (!mine.length) { say(`No login for ${site} in Hoola Cred.`); return; }
    say(`${mine.length} login${mine.length > 1 ? "s" : ""} for ${site} - Fill puts it into the page.`);
    for (const d of mine) {
      const row = document.createElement("div");
      row.className = "reply";
      const name = document.createElement("div");
      name.textContent = (d.title || site) + (d.username ? " · " + d.username : "");
      const btns = document.createElement("div");
      btns.className = "row";
      const fill = document.createElement("button");
      fill.textContent = "Fill";
      fill.addEventListener("click", async () => {
        try {
          const [r] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fillPage, args: [d.username || "", d.password || ""] });
          say(r && r.result ? "Filled. Press the page's sign-in button." : "No sign-in box on this page.", !(r && r.result));
        } catch (e) { say("This page cannot be filled (" + (e.message || e) + ").", true); }
      });
      btns.appendChild(fill);
      if (d.totp) {
        const code = document.createElement("button");
        code.className = "ghost"; code.textContent = "Copy 2-step code";
        code.addEventListener("click", async () => { const c = await totp(d.totp); if (c) { await navigator.clipboard.writeText(c); say("2-step code copied."); } });
        btns.appendChild(code);
      }
      row.append(name, btns);
      box.appendChild(row);
    }
  }
  async function start() {
    if (!el("credsec")) return;
    el("credlockbtn").addEventListener("click", async (e) => { e.preventDefault(); await chrome.storage.session.remove(["credVk", "credAt"]); el("credlist").innerHTML = ""; say("Locked."); });
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    let meta;
    try { meta = await vault(); } catch (e) { say(e.message, true); el("credlock").hidden = true; return; }
    if (!meta.exists) { say("Make your Hoola Cred first: Hoola console > Hoola Cred."); el("credlock").hidden = true; return; }
    const vk = await vkFromSession();
    if (vk) return show(tab, vk, meta);
    el("credlock").hidden = false;
    el("credunlock").addEventListener("click", async () => {
      const pw = el("credpw").value; el("credpw").value = "";
      try { await show(tab, await unlock(pw, meta), meta); }
      catch { say("That is not the master password.", true); }
    });
    el("credpw").addEventListener("keydown", (e) => { if (e.key === "Enter") el("credunlock").click(); });
  }
  start();
})();
