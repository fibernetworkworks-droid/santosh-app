// W3 - the Hoola extension's service worker: the "send page to Hoola" door.
// Three entries, one lane: the toolbar popup, the right-click menu ("Hoola ko bhejiye"),
// the Ctrl+Shift+H command. Everything POSTs to the SAME server lane the desktop uses
// (/api/pc/quickask) with the token the extension pairs through the phone's 6-digit code
// (the SAME /api/pc/pair flow a PC uses - the extension shows up on her Mera PC list).
// No eval, no remote code: the worker only fetches its own paired server.

const DEFAULT_SERVER = "https://hoola.ainewtika.com";
const LANEPATH = "/api/pc/quickask";
const MSGPATH = "/api/pc/quickask/messages";

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
