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
