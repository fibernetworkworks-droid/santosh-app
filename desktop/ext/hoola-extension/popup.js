// W3 popup: the ask box, the page send, and the honest state line. The heavy lifting
// (capture + POST) is the service worker's - the popup only talks to it and shows truth.
const DEFAULT_SERVER = "https://hoola.ainewtika.com";

const $ = (id) => document.getElementById(id);

async function init() {
  const st = await chrome.storage.local.get(["server", "token", "lastConversationId", "lastSentAt"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  if (!st.token) {
    $("pairline").textContent = "Pair nahi hai - Options mein 6 anko ka code daaliye.";
    $("pairline").style.color = "#D93C3C";
  } else {
    const when = st.lastSentAt ? new Date(st.lastSentAt).toLocaleString() : "";
    $("pairline").textContent = "Pair hai · server " + server.replace(/^https?:\/\//, "") +
                                (when ? " · aakhri bheja: " + when : "");
    $("pairline").style.color = "#0E9F6E";
    loadReplies(st.lastConversationId);
  }
  $("console").href = server + "/console" +
      (st.lastConversationId ? "/c/" + encodeURIComponent(st.lastConversationId) : "/");
  $("console").addEventListener("click", (e) => { e.preventDefault(); chrome.tabs.create({ url: $("console").href }); });
  $("opts").addEventListener("click", (e) => { e.preventDefault(); chrome.runtime.openOptionsPage(); });
  $("sendpage").addEventListener("click", () => send($("ask").value.trim(), true));
  $("sendask").addEventListener("click", () => send($("ask").value.trim(), false));
  $("capstart").addEventListener("click", captionsStart);
  $("capstop").addEventListener("click", captionsStop);
  captionsResume();   // W5: a reopened popup keeps polling a session that is still live
}

// ---------------------------------------------------------------- W5: live captions
// The worker owns the session (offscreen recording + start/stop); the popup only shows the
// truth: poll GET /api/kaan/live/{sid} every 3s and render the captions_tail as it grows.
let capPoll = null, capSid = "";

function capState(msg, bad) {
  const el = $("capstate");
  el.textContent = msg;
  el.style.color = bad ? "#D93C3C" : (msg.startsWith("Live") ? "#0E9F6E" : "#5B5675");
}

async function captionsStart() {
  $("capstart").disabled = true;
  capState("Session khol raha hoon…", false);
  const out = await chrome.runtime.sendMessage({ kind: "captions-start" });
  $("capstart").disabled = false;
  if (!out || !out.ok) {
    capState((out && out.message) || "Session nahi khula.", true);
    return;
  }
  capSid = out.sid;
  await chrome.storage.local.set({ capSid, capStartedAt: Date.now() });
  $("capstop").disabled = false;
  $("caps").innerHTML = "";
  capState("Live · " + (out.model || "base") + " · captions aa rahe hain…", false);
  clearInterval(capPoll);
  capPoll = setInterval(pollCaptions, 3000);
  pollCaptions();
}

async function pollCaptions() {
  if (!capSid) return;
  const st = await chrome.storage.local.get(["server", "token"]);
  const server = (st.server || DEFAULT_SERVER).replace(/\/+$/, "");
  try {
    const r = await fetch(server + "/api/kaan/live/" + encodeURIComponent(capSid), {
      headers: { "Authorization": "Bearer " + st.token },
    });
    if (!r.ok) { capState("Session ki sthiti nahi mili (HTTP " + r.status + ").", true); return; }
    const d = await r.json();
    if (d.status !== "live") { stopPolling("Session band ho gaya."); return; }
    const secs = Math.round(d.duration_s || 0);
    capState("Live · " + secs + "s · " + (d.n_phrases || 0) + " phrase(s)", false);
    const box = $("caps");
    box.innerHTML = "";
    for (const p of (d.captions_tail || []).slice(-6)) {
      const div = document.createElement("div");
      div.className = "reply";
      div.textContent = p.text || "";
      box.appendChild(div);
    }
  } catch (e) {
    capState("Server tak poll nahi pahuncha.", true);
  }
}

async function captionsStop() {
  $("capstop").disabled = true;
  capState("Band kar raha hoon…", false);
  const out = await chrome.runtime.sendMessage({ kind: "captions-stop" });
  clearInterval(capPoll); capPoll = null;
  await chrome.storage.local.remove(["capSid", "capStartedAt"]);
  $("capstart").disabled = false;
  $("capstop").disabled = true;
  capSid = "";
  if (out && out.ok) {
    capState("Transcript ban gayi" + (out.transcript_id ? " - " + out.transcript_id : "") + ". Conversation mein dikhegi.", false);
  } else {
    capState((out && out.message) || "Band nahi hua.", true);
  }
}

function stopPolling(msg) {
  clearInterval(capPoll); capPoll = null;
  capSid = "";
  chrome.storage.local.remove(["capSid", "capStartedAt"]).catch(() => {});
  $("capstart").disabled = false;
  $("capstop").disabled = true;
  capState(msg, false);
}

async function captionsResume() {
  const st = await chrome.storage.local.get(["capSid"]);
  if (!st.capSid) return;
  capSid = st.capSid;
  $("capstop").disabled = false;
  capPoll = setInterval(pollCaptions, 3000);
  pollCaptions();
}

function say(msg, bad) {
  $("state").textContent = msg;
  $("state").style.color = bad ? "#D93C3C" : "#0E9F6E";
}

async function send(text, withPage) {
  $("sendpage").disabled = $("sendask").disabled = true;
  say("Bhej raha hoon…", false);
  const out = await chrome.runtime.sendMessage({ kind: "send-page", text });
  $("sendpage").disabled = $("sendask").disabled = false;
  if (out && out.ok) {
    $("ask").value = "";
    say(out.duplicate ? "Yeh sawaal pehle hi ja chuka tha." :
        (withPage ? "Page bhej diya - Hoola padh kar jawab de rahi hai." : "Sawaal bhej diya - jawab conversation mein."),
        false);
    const st = await chrome.storage.local.get("lastConversationId");
    loadReplies(st.lastConversationId);
  } else {
    say((out && out.message) || "Nahi bheja.", true);
  }
}

async function loadReplies(conv) {
  if (!conv) return;
  const out = await chrome.runtime.sendMessage({ kind: "last-replies", conversationId: conv, after: 0 });
  if (!out || !out.ok || !out.messages.length) return;
  const last = out.messages.slice(-3);   // her ask + Hoola's answer, the last few rows
  const box = $("replies");
  box.innerHTML = "";
  for (const m of last) {
    const d = document.createElement("div");
    d.className = "reply";
    d.textContent = m.text.length > 400 ? m.text.slice(0, 400) + "…" : m.text;
    box.appendChild(d);
  }
}

init();
