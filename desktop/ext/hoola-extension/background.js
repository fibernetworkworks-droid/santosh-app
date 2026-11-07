// W3 - the Hoola extension's service worker: the "send page to Hoola" door.
// Three entries, one lane: the toolbar popup, the right-click menu ("Hoola ko bhejiye"),
// the Ctrl+Shift+H command. Everything POSTs to the SAME server lane the desktop uses
// (/api/pc/quickask) with the token the extension pairs through the phone's 6-digit code
// (the SAME /api/pc/pair flow a PC uses - the extension shows up on her Mera PC list).
// No eval, no remote code: the worker only fetches its own paired server.

const DEFAULT_SERVER = "https://hoola.ainewtika.com";
const LANEPATH = "/api/pc/quickask";
const MSGPATH = "/api/pc/quickask/messages";
const LIVEPATH = "/api/kaan/live";   // W5: the SAME kaan live door the API and the MCP server serve

// W5 - live captions state: one session at a time, the tab's audio recorded offscreen.
let capSession = { sid: "", startedAt: 0 };

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "hoola-send-page",
    title: "Hoola ko bhejiye",
    contexts: ["page", "selection", "link"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const sel = info.selectionText || "";
  const page = await capturePage(tab);
  await sendToHoola({
    url: page.url,
    title: page.title,
    selection: sel || page.selection,
    text: "",
  });
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "send-page") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const page = await capturePage(tab);
  await sendToHoola({ url: page.url, title: page.title, selection: page.selection, text: "" });
});

// the popup asks the worker to do the capture + send (the click already grants the tab)
chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.kind === "send-page") {
    (async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      const page = await capturePage(tab);
      const out = await sendToHoola({
        url: page.url, title: page.title, selection: page.selection, text: msg.text || "",
      });
      reply(out);
    })();
    return true;   // async reply
  }
  if (msg && msg.kind === "last-replies") {
    (async () => reply(await readReplies(msg.conversationId, msg.after || 0)))();
    return true;
  }
  if (msg && msg.kind === "captions-start") {
    (async () => reply(await captionsStart()))();
    return true;
  }
  if (msg && msg.kind === "captions-stop") {
    (async () => reply(await captionsStop()))();
    return true;
  }
  return false;
});

async function capturePage(tab) {
  const out = { url: "", title: "", selection: "" };
  if (!tab || !tab.id) return out;
  out.url = (tab.url || "").slice(0, 2048);
  out.title = (tab.title || "").slice(0, 300);
  if (!out.url.startsWith("http://") && !out.url.startsWith("https://")) {
    out.url = "";   // chrome:// pages and file:// are her own business; the lane takes web pages
  }
  try {
    const [res] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => (window.getSelection() ? window.getSelection().toString() : ""),
    });
    out.selection = ((res && res.result) || "").slice(0, 4000);
  } catch (e) {
    // restricted page (web store, chrome://) - the link still rides, the selection stays empty
  }
  return out;
}

async function sendToHoola(body) {
  const st = await chrome.storage.local.get(["server", "token", "lastConversationId", "lastSentAt"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  if (!st.token) {
    await flash("!", "#D93C3C");
    return { ok: false, message: "Pehle pair kijiye - extension ke Options mein phone ka 6 anko ka code daaliye." };
  }
  if (!body.text && !body.url) {
    return { ok: false, message: "Kuch bhejiye - ek sawaal ya ek page." };
  }
  body.client_id = "ext_" + crypto.randomUUID().slice(0, 20);
  try {
    const r = await fetch(server + LANEPATH, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + st.token },
      body: JSON.stringify(body),
    });
    if (r.status === 401) {
      await flash("!", "#D93C3C");
      return { ok: false, message: "Yeh device hata diya gaya - Options mein dobara pair kijiye." };
    }
    if (r.status === 429) {
      await flash("!", "#D93C3C");
      return { ok: false, message: "Bahut jaldi bahut sawaal - thodi der baad." };
    }
    if (!r.ok) {
      await flash("!", "#D93C3C");
      let msg = "Server ne mana kar diya (" + r.status + ").";
      try { msg = (await r.json()).detail || msg; } catch (e) { /* keep the honest default */ }
      return { ok: false, message: String(msg).slice(0, 200) };
    }
    const d = await r.json();
    await chrome.storage.local.set({
      lastConversationId: d.conversation_id || st.lastConversationId || "",
      lastSentAt: Date.now(),
      lastKind: d.kind || "ask",
    });
    await flash("\u2713", "#0E9F6E");
    return { ok: true, conversation_id: d.conversation_id, duplicate: !!d.duplicate };
  } catch (e) {
    await flash("!", "#D93C3C");
    return { ok: false, message: "Server tak nahi pahuncha - Options mein server address check kijiye." };
  }
}

async function readReplies(conversationId, after) {
  const st = await chrome.storage.local.get(["server", "token"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  if (!st.token || !conversationId) return { ok: false, messages: [] };
  try {
    const r = await fetch(server + MSGPATH + "?conversation_id=" + encodeURIComponent(conversationId) + "&after=" + after, {
      headers: { "Authorization": "Bearer " + st.token },
    });
    if (!r.ok) return { ok: false, messages: [] };
    return { ok: true, messages: (await r.json()).messages || [] };
  } catch (e) {
    return { ok: false, messages: [] };
  }
}

async function flash(text, color) {
  await chrome.action.setBadgeBackgroundColor({ color });
  await chrome.action.setBadgeText({ text });
  setTimeout(() => chrome.action.setBadgeText({ text: "" }), 4000);
}

// ---------------------------------------------------------------- W5: live captions
// The service worker cannot touch MediaRecorder (MV3), so an OFFSCREEN document records the
// tab audio; the session lifecycle rides the SAME /api/kaan/live endpoints every other door
// uses, with the SAME paired-device Bearer. The streamId must be born in a user gesture -
// the popup's click travels here as the captions-start message.
const OFFSCREEN_URL = "offscreen.html";

async function hasOffscreen() {
  const ctx = await chrome.runtime.getContexts({ contextTypes: ["OFFSCREEN_DOCUMENT"] });
  return !!(ctx && ctx.length);
}

async function setupOffscreen() {
  if (await hasOffscreen()) return;
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_URL,
    reasons: ["USER_MEDIA"],
    justification: "Hoola live captions: record the tab audio and stream it to her paired kaan server.",
  });
}

async function captionsStart() {
  const st = await chrome.storage.local.get(["server", "token"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  if (!st.token) return { ok: false, message: "Pehle pair kijiye - Options mein 6 anko ka code daaliye." };
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return { ok: false, message: "Koi tab nahi mila - jis page ki baatein sunni hain use kholkar dubara." };
  let streamId = "";
  try {
    streamId = await chrome.tabCapture.getMediaStreamId({ consumerTabId: tab.id });
  } catch (e) {
    return { ok: false, message: "Is tab ka audio nahi mila (" + String(e && e.message || e).slice(0, 80) + "). Tab ko dobara kijiye ya doosra tab." };
  }
  try {
    const r = await fetch(server + LIVEPATH + "/start", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + st.token },
      body: JSON.stringify({}),
    });
    if (r.status === 401) return { ok: false, message: "Yeh device hata diya gaya - Options mein dobara pair kijiye." };
    if (!r.ok) {
      let m = "Live session nahi khula (HTTP " + r.status + ").";
      try { m = String((await r.json()).detail || m); } catch (e) { /* keep the honest default */ }
      return { ok: false, message: m.slice(0, 200) };
    }
    const sess = await r.json();
    capSession = { sid: sess.id || "", startedAt: Date.now() };
    await setupOffscreen();
    await chrome.runtime.sendMessage({ kind: "captions-record", streamId, server, token: st.token, sid: capSession.sid });
    return { ok: true, sid: capSession.sid, model: sess.model || "" };
  } catch (e) {
    return { ok: false, message: "Server tak nahi pahuncha - Options mein server address check kijiye." };
  }
}

async function captionsStop() {
  const st = await chrome.storage.local.get(["server", "token"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  const sid = capSession.sid;
  if (!sid) return { ok: false, message: "Koi live session chal nahi raha tha." };
  await chrome.runtime.sendMessage({ kind: "captions-halt" }).catch(() => {});
  await new Promise((res) => setTimeout(res, 400));   // the recorder's last slice lands first
  let out = { ok: true, transcript_id: "" };
  try {
    const r = await fetch(server + LIVEPATH + "/" + sid + "/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + st.token },
      body: JSON.stringify({}),
    });
    if (r.ok) out.transcript_id = (await r.json()).transcript_id || "";
    else out = { ok: false, message: "Stop par server ne mana kiya (HTTP " + r.status + ")." };
  } catch (e) {
    out = { ok: false, message: "Stop tak nahi pahuncha - session server par khula reh gaya." };
  }
  capSession = { sid: "", startedAt: 0 };
  await chrome.offscreen.closeDocument().catch(() => {});
  return out;
}
