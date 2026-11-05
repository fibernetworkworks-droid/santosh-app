/* Hoola Interactive - the student's side of a live talk (lab page).
   The engine sends [type u8][chunk u16][index u32][payload]: type 2 = WAV of one speech chunk, type 1 = JPEG of one
   picture in that chunk (25 fps). Audio is the clock: a picture is shown for the moment the speaker is at. */
(function (root) {
  "use strict";
  var FPS = 25;

  // Which picture belongs to time t? chunks: [{start, dur, frames:[...]}] (start in audio-clock seconds).
  function pick(chunks, t) {
    for (var k = chunks.length - 1; k >= 0; k--) {
      var c = chunks[k];
      if (!c || c.start === undefined || t < c.start) continue;
      if (t >= c.start + c.dur) return { k: k, idx: -1, have: false, over: true };   // between chunks / after the end
      var idx = Math.floor((t - c.start) * FPS + 1e-6), last = c.frames.length - 1;
      var have = c.frames[idx] !== undefined;
      return { k: k, idx: have ? idx : Math.min(idx, last), have: have, over: false };
    }
    return null;
  }

  // When does a chunk start? Right after the previous one ends; never earlier than the jitter buffer after "now".
  function startFor(now, prevEnd, buffer, first) {
    var earliest = now + (first ? buffer : 0.02);
    return Math.max(earliest, prevEnd || 0);
  }

  var api = { FPS: FPS, pick: pick, startFor: startFor };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HoolaLive = api;
})(typeof window !== "undefined" ? window : this);
