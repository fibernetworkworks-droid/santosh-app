// W5 offscreen: MediaRecorder lives here because an MV3 service worker cannot. It consumes
// the tabCapture streamId born in the popup's click, records the tab audio as audio/webm in
// 2s slices, and POSTs every slice to the SAME /api/kaan/live/{sid}/chunk door the API and
// the MCP server use - with the SAME paired-device Bearer. No eval, no remote code: only the
// paired server is fetched.
let rec = null;

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.kind === "captions-record") {
    startRec(msg).catch((e) => {
      chrome.runtime.sendMessage({ kind: "captions-error", error: String((e && e.message) || e).slice(0, 200) }).catch(() => {});
    });
  }
  if (msg && msg.kind === "captions-halt") haltRec();
  return false;
});

async function startRec({ streamId, server, token, sid }) {
  // The tabCapture handshake: the streamId only ever works with the "tab" media source.
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: streamId } },
  });
  rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
  rec.ondataavailable = async (e) => {
    if (!e.data || !e.data.size) return;   // an empty slice is nothing to send
    try {
      const r = await fetch(server + "/api/kaan/live/" + encodeURIComponent(sid) + "/chunk", {
        method: "POST",
        headers: { "Authorization": "Bearer " + token, "Content-Type": "application/octet-stream" },
        body: await e.data.arrayBuffer(),
      });
      if (!r.ok) {
        chrome.runtime.sendMessage({ kind: "captions-error", error: "Chunk par server ne mana kiya (HTTP " + r.status + ")." }).catch(() => {});
      }
    } catch (err) {
      // one lost slice is honest loss - the spine keeps the rest; the popup's poll shows the truth
    }
  };
  rec.start(2000);   // 2s slices: small enough for rolling captions, big enough to not spam
}

function haltRec() {
  try {
    if (rec && rec.state !== "inactive") rec.stop();   // the final slice fires ondataavailable
  } catch (e) { /* already stopped */ }
}
