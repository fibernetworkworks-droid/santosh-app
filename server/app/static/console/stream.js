/* v0.161 Hoola Console: the event stream and the word pacer.
   HoolaStream.open(): SSE read with fetch (Bearer header, Last-Event-ID, backoff reconnect). `live=1` asks for the reply
   being written (reply_start / delta / delta_reset / reply_end): those come without an id and never move the cursor.
   HoolaStream.Pacer: words come out at a steady pace (v0.283: ~20 ms a word, a capped catch-up) with requestAnimationFrame, split with
   Intl.Segmenter so Hindi / Devanagari and mixed Hinglish break at real word edges; a big backlog is caught up faster;
   a hidden tab or the reply's end shows everything at once. */
'use strict';
(() => {
function open({url, token, after, onEvent, onState, onAuth}) {
  const ctl = new AbortController(); let last = after || 0, retry = 0;
  (async () => {
    while (!ctl.signal.aborted) {
      try {
        onState('', 'Jud raha hai…');
        const r = await fetch(`${url}${url.includes('?') ? '&' : '?'}after=${last}&live=1`, {
          headers: {Authorization: 'Bearer ' + token, 'Last-Event-ID': String(last)}, signal: ctl.signal, cache: 'no-store'});
        if (r.status === 401) { onAuth(); return; }
        if (!r.ok || !r.body) throw new Error('stream ' + r.status);
        onState('ok', 'Live'); retry = 0;
        const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
        for (;;) {
          const {value, done} = await rd.read(); if (done) break;
          buf += dec.decode(value, {stream: true});
          let i; while ((i = buf.indexOf('\n\n')) >= 0) {
            const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
            const data = chunk.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trimStart()).join('\n');
            if (!data) continue;
            let ev; try { ev = JSON.parse(data); } catch (e) { console.warn('event', e); continue; }
            if (ev.live) { onEvent(ev); continue; }                    // the reply being written: no cursor
            if (!ev.id) { if (ev.kind === 'resync') { onEvent(ev); return; } continue; }   // replay_end and other markers
            if (ev.id > last) { last = ev.id; onEvent(ev); }
          }
        }
      } catch (e) { if (ctl.signal.aborted) return; }
      if (ctl.signal.aborted) return;
      onState('bad', 'Dobara jud raha hai…'); retry = Math.min(retry + 1, 6);
      await new Promise(r => setTimeout(r, 800 * 2 ** retry));
    }
  })();
  return {abort: () => ctl.abort(), last: () => last};
}

const SEG = (typeof Intl !== 'undefined' && Intl.Segmenter) ? new Intl.Segmenter(undefined, {granularity: 'word'}) : null;
function words(s) {
  // pieces that end at a word edge (a word plus the spaces / signs after it)
  if (!s) return [];
  if (!SEG) return s.match(/\S+\s*|\s+/g) || [];
  const out = []; let cur = '';
  for (const p of SEG.segment(s)) { if (p.isWordLike && cur.trim()) { out.push(cur); cur = ''; } cur += p.segment; }
  if (cur) out.push(cur);
  return out;
}

class Pacer {
  /* show(text, done): called with everything to show so far. push(text): more words. final(text): the whole answer
     (continues from what is shown when it starts the same way, else shows it at once). */
  constructor(show) { this.show = show; this.shown = ''; this.queue = []; this.target = ''; this.finalText = null; this.raf = 0; this.t = 0; }
  push(text) { if (!text) return; this.target += text; this.queue.push(...words(text)); this._go(); }
  final(text) {
    this.finalText = text;
    if (text.startsWith(this.target)) { const rest = text.slice(this.target.length); this.target = text; this.queue.push(...words(rest)); this._go(); }
    else this.flush();
  }
  reset() { cancelAnimationFrame(this.raf); this.raf = 0; this.shown = ''; this.queue = []; this.target = ''; this.finalText = null; this.show('', false); }
  flush() {
    cancelAnimationFrame(this.raf); this.raf = 0; this.queue = [];
    this.shown = this.finalText ?? this.target; this.target = this.shown; this.show(this.shown, this.finalText !== null);
  }
  get done() { return this.finalText !== null && !this.queue.length; }
  _go() {
    if (document.hidden) { if (this.finalText !== null) this.flush(); else { this.shown = this.target; this.queue = []; this.show(this.shown, false); } return; }
    if (this.raf) return;
    this.t = performance.now();
    const tick = now => {
      // v0.283: measured with this very code - 10 ms a word with an uncapped catch-up ran a 300-word answer at
      // 244 words a second (1.2 s), and even a properly streamed one at 165. Claude lands at roughly 40-80.
      // 20 ms a word, and the catch-up only once more than 80 words are waiting, capped at 2 extra a frame:
      // 300 words take 3.8 s instead of 1.2, while a 30-word reply is unchanged (0.5 s).
      const n = Math.max(1, Math.floor((now - this.t) / 20) + Math.min(2, Math.floor(this.queue.length / 80)));
      this.t = now;
      this.shown += this.queue.splice(0, n).join('');
      const fin = this.finalText !== null && !this.queue.length;
      if (fin) this.shown = this.finalText;
      this.show(this.shown, fin);
      this.raf = this.queue.length ? requestAnimationFrame(tick) : 0;
    };
    this.raf = requestAnimationFrame(tick);
  }
}

window.HoolaStream = {open, Pacer, words};
})();
