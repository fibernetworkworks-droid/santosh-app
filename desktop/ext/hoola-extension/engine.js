// v0.999.111 ULTIMATE PC PLAN P1 - Hoola's page engine 2 in HER Chrome (the same engine as Hoola PC's).
// When she turns it on (Options > "Let Hoola work on my pages": host access + the debugger permission, her click),
// this worker keeps ONE socket to her paired Hoola server (/api/pc/ext-ws, first message = the paired token) and
// answers three kinds of request, always for the tab she has in front:
//   js    - inject pagekit.js (generated from desktop-linux/pagekit.py) into the page's isolated world and run ONE of
//           its functions (elements / snap / text / point / click / type / select / drag); data comes back, never
//           what was typed;
//   mouse - the real mouse through chrome.debugger (Input.dispatchMouseEvent): hover menus open, a banner lying on
//           top is respected. Chrome shows "Hoola started debugging this browser" while it is attached;
//   tab   - the active tab's title + address.
// The server keeps the refs and decides (server/app/pc/extlink.py). No eval, no remote code.

const ENGINE_PATH = "/api/pc/ext-ws";
let engineWs = null;
let engineBackoff = 2000;
let dbgTab = null;
let dbgTimer = null;

async function engineWanted() {
  const st = await chrome.storage.local.get(["server", "token", "pageEngine"]);
  if (!st.token || st.pageEngine !== true) return null;
  const ok = await chrome.permissions.contains({ permissions: ["debugger"], origins: ["https://*/*", "http://*/*"] });
  return ok ? st : null;
}

async function engineConnect() {
  if (engineWs && (engineWs.readyState === 0 || engineWs.readyState === 1)) return;
  const st = await engineWanted();
  if (!st) return;
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  const url = server.replace(/^http/, "ws") + ENGINE_PATH;
  let ws;
  try { ws = new WebSocket(url); } catch (e) { return; }
  engineWs = ws;
  ws.onopen = () => {
    engineBackoff = 2000;
    ws.send(JSON.stringify({ type: "hello", token: st.token, browser: navigator.userAgent.slice(0, 60) }));
  };
  ws.onmessage = async (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch (e) { return; }
    if (!msg || !msg.id) return;
    let reply;
    try {
      reply = { id: msg.id, ok: true, result: await engineRun(msg) };
    } catch (e) {
      reply = { id: msg.id, ok: false, error: String((e && e.message) || e).slice(0, 300) };
    }
    try { ws.send(JSON.stringify(reply)); } catch (e) { /* the socket closed meanwhile */ }
  };
  ws.onclose = () => {
    engineWs = null;
    setTimeout(engineConnect, engineBackoff);
    engineBackoff = Math.min(engineBackoff * 2, 60000);
  };
  ws.onerror = () => { try { ws.close(); } catch (e) { /* closing anyway */ } };
}

async function engineTab() {
  const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true, windowType: "normal" });
  if (!tab || !tab.id) throw new Error("no browser tab is in front");
  if (!/^https?:/.test(tab.url || "")) throw new Error("the tab in front is not a web page (" + String(tab.url || "").slice(0, 40) + ")");
  return tab;
}

async function engineRun(msg) {
  const tab = await engineTab();
  if (msg.op === "tab") return { title: tab.title || "", url: tab.url || "" };
  if (msg.op === "js") {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["pagekit.js"] });
    const [res] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (fn, a) => {
        const pk = window.__hoolaPK;
        if (!pk || typeof pk[fn] !== "function") return { __err: "unknown engine function " + fn };
        return pk[fn](a);
      },
      args: [String(msg.fn || ""), msg.args || {}],
    });
    const out = res ? res.result : null;
    if (out && out.__err) throw new Error(out.__err);
    return out;
  }
  if (msg.op === "mouse") {
    await engineAttach(tab.id);
    for (const e of (msg.events || []).slice(0, 20)) {
      await chrome.debugger.sendCommand({ tabId: tab.id }, "Input.dispatchMouseEvent", e);
    }
    return { done: true };
  }
  throw new Error("unknown request " + msg.op);
}

async function engineAttach(tabId) {
  if (dbgTab !== tabId) {
    if (dbgTab !== null) { try { await chrome.debugger.detach({ tabId: dbgTab }); } catch (e) { /* already gone */ } }
    await chrome.debugger.attach({ tabId }, "1.3");
    dbgTab = tabId;
  }
  clearTimeout(dbgTimer);
  dbgTimer = setTimeout(async () => {      // let go after 30 s of nothing: Chrome's debugging bar goes away
    if (dbgTab !== null) { try { await chrome.debugger.detach({ tabId: dbgTab }); } catch (e) { /* gone */ } }
    dbgTab = null;
  }, 30000);
}

chrome.debugger.onDetach && chrome.debugger.onDetach.addListener((src) => { if (src.tabId === dbgTab) dbgTab = null; });

// keep the socket alive (a worker is put to sleep after ~30 s without work; a ping every 20 s is work)
setInterval(() => {
  if (engineWs && engineWs.readyState === 1) {
    try { engineWs.send(JSON.stringify({ type: "ping" })); } catch (e) { /* reconnects on close */ }
  } else {
    engineConnect();
  }
}, 20000);
chrome.alarms && chrome.alarms.create("hoola-engine", { periodInMinutes: 1 });
chrome.alarms && chrome.alarms.onAlarm.addListener((a) => { if (a.name === "hoola-engine") engineConnect(); });
chrome.storage.onChanged.addListener((ch) => { if (ch.pageEngine || ch.token) engineConnect(); });
chrome.runtime.onStartup.addListener(engineConnect);
engineConnect();
