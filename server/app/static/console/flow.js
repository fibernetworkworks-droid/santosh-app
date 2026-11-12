/* v0.751 HOOLA FLOW - the Kaan pack (W0-W6) as a console page (owner: "check the code" -> the 8-screen canvas -> "GO").

   One page, its own small sidebar:
     home      Dictate / A file to text / Live captions + her recent transcripts (search by what was said) + month minutes + engine
     dictate   speak -> words appear as the server hears them (a live session) -> Stop -> the transcript in the style she picks
               (As said / Clean / Notes / Social) -> Copy / Put in the chat box / Save to Gyaan
     files     a recording -> POST /api/kaan/transcribe (language, translate, quality, word list, speakers) -> the transcript
     t         one transcript: turns (she names them), styles, action items (-> a chat ask for reminders), SRT / VTT / TXT / JSON,
               Save to Gyaan, Keep for ever, Rename, Delete (her tap)
     live      live captions from this computer's mic; Stop and save -> the transcript with its minutes
     words     her word list (a hint, or "always write as")
     settings  engine, recording switch, speakers, voiceprint, limits, other doors - read from the server, never guessed

   Audio: one recorder (HoolaFlowRec) captures the mic as 16 kHz mono WAV in 2 s pieces - every piece is a whole file, so the
   server's ffmpeg decodes each one on its own (a MediaRecorder webm slice after the first has no header). The same recorder
   drives the chat box mic (window.HoolaFlowMic) when the engine is ready. Audio and text stay on her server. */
(function () {
  function wav(f32, rate) {
    const n = f32.length, b = new ArrayBuffer(44 + n * 2), v = new DataView(b);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true);
    v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true);
    v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true);
    for (let i = 0; i < n; i++) { const s = Math.max(-1, Math.min(1, f32[i])); v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true); }
    return new Blob([b], {type: 'audio/wav'});
  }
  function down(buf, from, to) {
    if (from === to) return buf;
    const r = from / to, n = Math.floor(buf.length / r), o = new Float32Array(n);
    for (let i = 0; i < n; i++) { const a = Math.floor(i * r), z = Math.min(buf.length, Math.floor((i + 1) * r)); let s = 0; for (let j = a; j < z; j++) s += buf[j]; o[i] = s / Math.max(1, z - a); }
    return o;
  }
  /* rec = HoolaFlowRec({onPiece(blob), onLevel(0..1)}); await rec.start(); ...; await rec.stop() (the last piece is sent first) */
  window.HoolaFlowRec = function ({onPiece, onLevel, every = 2000}) {
    let stream = null, ctx = null, src = null, proc = null, parts = [], timer = 0, paused = false;
    const flush = () => {
      if (!parts.length || !ctx) return;
      const len = parts.reduce((n, p) => n + p.length, 0), all = new Float32Array(len); let o = 0;
      parts.forEach(p => { all.set(p, o); o += p.length; }); parts = [];
      onPiece(wav(down(all, ctx.sampleRate, 16000), 16000));
    };
    return {
      async start() {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error('This browser cannot use the microphone.');
        stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}});
        ctx = new (window.AudioContext || window.webkitAudioContext)();
        src = ctx.createMediaStreamSource(stream); proc = ctx.createScriptProcessor(4096, 1, 1);
        proc.onaudioprocess = e => {
          if (paused) return;
          const d = e.inputBuffer.getChannelData(0); parts.push(new Float32Array(d));
          if (onLevel) { let m = 0; for (let i = 0; i < d.length; i += 64) m = Math.max(m, Math.abs(d[i])); onLevel(Math.min(1, m * 2.2)); }
        };
        src.connect(proc); proc.connect(ctx.destination);
        timer = setInterval(flush, every);
      },
      pause(on) { paused = !!on; },
      async stop() {
        clearInterval(timer); flush();
        try { proc && proc.disconnect(); src && src.disconnect(); } catch {}
        stream && stream.getTracks().forEach(t => t.stop());
        try { ctx && await ctx.close(); } catch {}
        stream = ctx = src = proc = null;
      }};
  };
  /* a live session over the recorder: pieces go up in order (one at a time), new phrases come back */
  window.HoolaFlowSession = function ({api, onWords, onLevel, onError}) {
    let sid = '', rec = null, chain = Promise.resolve(), words = [], dead = false;
    const send = blob => { chain = chain.then(async () => {
      if (dead || !sid) return;
      try { const r = await api('POST', `/api/kaan/live/${encodeURIComponent(sid)}/chunk`, undefined, {form: blob});
        (r.new || []).forEach(p => p.text && words.push(p.text.trim())); onWords && onWords(words.join(' '), r);
      } catch (e) { onError && onError(e); }
    }); };
    return {
      get sid() { return sid; },
      text() { return words.join(' '); },
      async start(opts = {}) {
        const s = await api('POST', '/api/kaan/live/start', {model: opts.model || '', language: opts.language || '', vocab: true});
        sid = s.id; rec = window.HoolaFlowRec({onPiece: send, onLevel});
        try { await rec.start(); } catch (e) { dead = true; try { await api('POST', `/api/kaan/live/${encodeURIComponent(sid)}/stop`, {}); } catch {} throw e; }
        return s;
      },
      pause(on) { rec && rec.pause(on); },
      async stop() {
        if (rec) await rec.stop(); await chain;
        const out = await api('POST', `/api/kaan/live/${encodeURIComponent(sid)}/stop`, {}); dead = true; return out;
      },
      async cancel() { dead = true; try { rec && await rec.stop(); } catch {} try { sid && await api('POST', `/api/kaan/live/${encodeURIComponent(sid)}/stop`, {}); } catch {} }};
  };
})();

/* v0.777 HOOLA FLOW like Wispr Flow (owner: "CHECK DESIGN AND MAKE IT SAME AS WISPERFLOW"). Its own page /console/flow
   (flowapp.html), styled by flow.css:
     sidebar    Home / Dictionary / Snippets / Style, then Transcribe a file / Live captions, then Settings + back to Hoola
     home       "Welcome back, <name>", a streak / words / WPM pill (counted from her own transcripts on this server),
                the dictate card, and history grouped Today / Yesterday / date - time in its own column, Copy / Open on hover
     Flow bar   a dark pill at the bottom: click, or hold Space (release = done; a tap keeps listening, Space again = done),
                Esc = cancel (nothing kept). While she speaks it shows a waveform, a clock and her words so far; when she
                stops, the text comes back in her Style, is copied for her and lands at the top of the history.
     dictionary words Hoola should spell her way (a hint, or "always write it as")
     snippets   say a short cue, Hoola writes the whole text (stored in the same word list, marked as a snippet)
     style      how a dictation reads (As said / Clean / Notes / Social), kept in this browser
   Everything else (files, live captions, one transcript, settings) keeps the v0.751 routes. Audio and text stay on her
   server. Nothing here invents words: Clean only tidies, Notes / Social only pick what was said. */
window.HoolaFlow = function ({api, esc, toast, say}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, ME = null, T = null, MIN = null, Q = '', VOC = null, VTAB = 'all';
  let SESS = null, LIVE = null, TICK = 0, T0 = 0, LEVEL = 0, BUSY = false, PAUSED = false, FRESH = '', BAR = 'idle';
  let HOLD = null, PEND_STOP = false, KEYS = false;
  let STYLE = 'clean'; try { STYLE = localStorage.getItem('hoola.flow.style') || 'clean'; } catch (e) { /* private window */ }
  const $ = s => EL && EL.querySelector(s);
  const STY = [['verbatim', 'As said'], ['clean', 'Clean'], ['minutes', 'Notes'], ['social', 'Social'], ['subtitles', 'Subtitles']];
  const clock = s => { s = Math.max(0, Math.round(+s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
    return h ? `${h}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}` : `${m}:${String(x).padStart(2, '0')}`; };
  const hhmm = iso => { const d = new Date(iso || ''); return isNaN(d) ? '' : d.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}); };
  const dayKey = d => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  const dayName = iso => { const d = new Date(iso || ''); if (isNaN(d)) return 'Earlier';
    const t = new Date(), y = new Date(Date.now() - 864e5);
    if (dayKey(d) === dayKey(t)) return 'Today'; if (dayKey(d) === dayKey(y)) return 'Yesterday';
    return d.toLocaleDateString([], {weekday: 'long', day: 'numeric', month: 'long'}); };
  const nwords = s => (String(s || '').match(/\S+/g) || []).length;
  const kfmt = n => n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K` : String(n);
  const I = {
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
    dict: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21V5M9 7h6"/></svg>',
    snip: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 3L5 14h6l-1 7 8-11h-6z"/></svg>',
    style: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/></svg>',
    file: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></svg>',
    live: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 6.3a8 8 0 0 1 0 11.4"/></svg>',
    gear: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
    back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>',
    copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    open: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17L17 7M8 7h9v9"/></svg>',
    trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
    search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    ok: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5L20 7"/></svg>',
    mic: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
    flame: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3c1 3 4 5 4 9a4 4 0 0 1-8 0c0-1 .3-2 1-3 0 2 1 3 2 3 0-3-1-5 1-9z"/></svg>',
    right: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
  };

  async function load() {
    try { OV = await api('GET', '/api/flow/overview?limit=100'); } catch (e) { OV = {error: e.message, items: [], engine: {}, recording: {}, usage: {}, retention: {}}; }
  }
  async function loadMe() { if (ME) return; try { ME = await api('GET', '/api/me'); } catch (e) { ME = {}; } }
  async function loadVoc() { try { VOC = await api('GET', '/api/kaan/vocab'); } catch (e) { VOC = {items: [], error: e.message}; } }
  const canHear = () => !!OV?.ready;
  const firstName = () => { const n = String(ME?.name || '').trim() || String(ME?.email || '').split('@')[0]; return n ? n.split(/\s+/)[0] : ''; };

  /* ---------------------------------------------------------------- routing: #/ #/dictionary #/snippets #/style #/files #/live #/settings #/t/<id> */
  const HASH = {home: '#/', words: '#/dictionary', snippets: '#/snippets', style: '#/style', files: '#/files', live: '#/live', settings: '#/settings'};
  function parse() {
    const h = location.hash || '#/', m = /^#\/t\/(.+)$/.exec(h);
    if (m) return ['t', decodeURIComponent(m[1])];
    const v = Object.keys(HASH).find(k => HASH[k] === h);
    return [v || 'home', ''];
  }
  async function open(root, view, arg) {
    EL = root || EL; if (!EL) return;
    shell();
    await Promise.all([load(), loadMe()]);
    const [v, a] = view ? [view, arg || ''] : parse();
    show(v, a);
    if (!KEYS) { KEYS = true; keys(); window.addEventListener('hashchange', () => { const [v2, a2] = parse(); if (v2 !== VIEW || a2 !== TID) show(v2, a2); }); }
  }
  function leave() { if (!SESS && !LIVE) clearInterval(TICK); }
  function busyNow() { return !!(SESS || LIVE); }
  function show(view, arg) {
    if (LIVE && view !== 'live') { toast('Stop the live captions first.', true); if (location.hash !== HASH.live) location.hash = HASH.live; return; }
    VIEW = view; TID = arg || '';
    const h = view === 't' ? `#/t/${encodeURIComponent(TID)}` : HASH[view] || '#/';
    if (location.hash !== h) history.replaceState(null, '', h);
    side();
    const page = {words, snippets, style, files, live, settings, t: () => transcript(TID)}[view] || home;
    page();
    bar();
    const m = $('#wfmain'); if (m) m.scrollTop = 0;
  }

  /* ---------------------------------------------------------------- the shell (built once; the Flow bar survives page changes) */
  function shell() {
    if ($('.wf')) return;
    EL.innerHTML = `<div class="wf"><aside class="wf-side" aria-label="Main navigation">
        <a class="wf-logo" href="#/"><img src="/static/hoola-mark.png" alt=""><b>Hoola Flow</b></a>
        <nav class="wf-nav" id="wfnav"></nav>
        <div class="wf-grow"></div>
        <div class="wf-tip"><b>Shortcuts</b><p>Dictate<span><kbd>Space</kbd></span></p><p>Cancel<span><kbd>Esc</kbd></span></p><p>In Hoola chat<span><kbd>Ctrl</kbd><kbd>Space</kbd></span></p></div>
        <nav class="wf-nav" aria-label="Secondary navigation">
          <button type="button" class="wf-nv" data-go="settings">${I.gear}Settings</button>
          <a class="wf-nv" href="/console/">${I.back}Back to Hoola</a></nav>
        <div class="wf-user" id="wfuser" hidden></div>
      </aside>
      <main class="wf-main" id="wfmain" aria-label="Main content"></main>
      <div class="wf-flowbar" id="wfbar" aria-live="polite"></div></div>`;
    EL.querySelector('.wf').addEventListener('click', e => { const b = e.target.closest('[data-go]'); if (b) show(b.dataset.go); });
  }
  function side() {
    const cur = VIEW === 't' ? 'home' : VIEW;
    const item = (k, n, ic) => `<button type="button" class="wf-nv${k === cur ? ' on' : ''}" data-go="${k}"${k === cur ? ' aria-current="page"' : ''}>${ic}${n}</button>`;
    $('#wfnav').innerHTML = item('home', 'Home', I.home) + item('words', 'Dictionary', I.dict) + item('snippets', 'Snippets', I.snip) +
      item('style', 'Style', I.style) + '<p class="wf-sec">Transcribe</p>' + item('files', 'A file to text', I.file) + item('live', 'Live captions', I.live);
    EL.querySelectorAll('.wf-side [data-go="settings"]').forEach(b => { b.classList.toggle('on', cur === 'settings'); });
    const u = $('#wfuser'), nm = String(ME?.name || '').trim() || String(ME?.email || '').split('@')[0];
    if (u && nm) { u.hidden = false; u.innerHTML = `<span class="wf-ava" aria-hidden="true">${esc(nm[0].toUpperCase())}</span><div><b>${esc(nm)}</b><small>${esc(ME?.email || 'Your own server')}</small></div>`; }
  }
  function main(html) { $('#wfmain').innerHTML = html; }
  function notReady() {
    if (!OV || OV.error) return `<div class="wf-warn" role="status">Hoola Flow could not read the server: ${esc(OV?.error || '')}</div>`;
    if (!OV.engine?.ok) return `<div class="wf-warn" role="status"><b>The speech engine is not ready on this server.</b> ${esc(OV.engine?.why || '')} Your saved transcripts still open.</div>`;
    if (!OV.recording?.on) return `<div class="wf-warn" role="status"><b>Recording is off.</b> ${esc(OV.recording?.how || '')} Your saved transcripts still open.</div>`;
    return '';
  }

  /* ---------------------------------------------------------------- home */
  function stats() {
    const items = OV?.items || [];
    const words = items.reduce((n, it) => n + nwords(it.text), 0);
    const dict = items.filter(it => it.kind === 'dictated' && it.duration_s > 0);
    const dw = dict.reduce((n, it) => n + nwords(it.text), 0), ds = dict.reduce((n, it) => n + (+it.duration_s || 0), 0);
    const wpm = ds >= 20 ? Math.round(dw / (ds / 60)) : null;
    const days = new Set(items.map(it => { const d = new Date(it.created_at || ''); return isNaN(d) ? '' : dayKey(d); }));
    let streak = 0; const d = new Date();
    if (!days.has(dayKey(d))) d.setDate(d.getDate() - 1);           // a streak still counts until today ends
    while (days.has(dayKey(d))) { streak++; d.setDate(d.getDate() - 1); }
    return {words, wpm, streak, n: items.length};
  }
  function home() {
    const st = stats(), nm = firstName();
    const items = (OV?.items || []).filter(it => !Q || `${it.title} ${it.text}`.toLowerCase().includes(Q.toLowerCase()));
    const groups = []; items.forEach(it => { const g = dayName(it.created_at); const last = groups[groups.length - 1];
      if (last && last.name === g) last.items.push(it); else groups.push({name: g, items: [it]}); });
    main(`<div class="wf-in">
      <header class="wf-hd"><h1 class="wf-h1">Welcome back${nm ? ', ' + esc(nm) : ''}</h1>
        <div class="wf-stats" title="Counted from your last ${st.n} transcripts on this server">
          <span>${I.flame}<b>${st.streak}</b> day streak</span><span><b>${kfmt(st.words)}</b> words</span><span><b>${st.wpm ?? '-'}</b> WPM</span></div></header>
      ${notReady()}
      <section class="wf-hero" aria-labelledby="wfhero"><div>
        <span class="wf-chip"><i class="wf-dot ${canHear() ? 'ok' : 'bad'}"></i>${canHear() ? 'Ready on your server' : 'Not ready'}</span>
        <h2 id="wfhero">Just speak.<br><em>Hoola writes it.</em></h2>
        <p class="wf-lead">Hindi, Marathi, English or a mix. When you stop, your words are tidied, copied and saved here - paste them anywhere.</p>
        <p class="wf-keys"><span><kbd>Space</kbd> Hold to dictate</span><span><kbd>Esc</kbd> Cancel</span><span><kbd>Ctrl</kbd><kbd>V</kbd> Paste</span></p></div>
        <button type="button" class="wf-mic" id="wfgo"${canHear() ? '' : ' disabled'}><i>${I.mic}</i><b>Start dictating</b></button></section>
      <div class="wf-quick">
        <button type="button" class="wf-q" data-go="files"><i class="wf-tile">${I.file}</i><span><b>A file to text</b><small>Meetings, voice notes, videos</small></span></button>
        <button type="button" class="wf-q" data-go="live"><i class="wf-tile b">${I.live}</i><span><b>Live captions</b><small>Words as people speak</small></span></button>
        <button type="button" class="wf-q" data-go="words"><i class="wf-tile c">${I.dict}</i><span><b>Dictionary</b><small>Names and words, your way</small></span></button></div>
      <div class="wf-histbar"><h2 class="wf-h2">History</h2>
        <label class="wf-search">${I.search}<span class="wf-sr">Search what was said</span><input id="wfq" placeholder="Search what was said" value="${esc(Q)}"></label></div>
      ${groups.length ? groups.map(g => `<p class="wf-day">${esc(g.name)}</p><div class="wf-list">${g.items.map(row).join('')}</div>`).join('')
        : `<div class="wf-list" style="margin-top:16px"><div class="wf-empty">${Q ? '<b>Nothing matches</b>Nothing said matches that search.' : '<b>Nothing here yet</b>Hold Space and say something - it shows up here.'}</div></div>`}
    </div>`);
    $('#wfgo').onclick = () => startDictation();
    const q = $('#wfq'); q.oninput = () => { Q = q.value; const p = q.selectionStart; home(); const n = $('#wfq'); n.focus(); n.setSelectionRange(p, p); };
    wireRows();
  }
  function row(it) {
    const tag = it.kind === 'file' ? `<span class="wf-tag">File · ${clock(it.duration_s)}</span>` : it.kind === 'live' ? `<span class="wf-tag live">Live · ${clock(it.duration_s)}</span>` : '';
    const body = it.kind === 'dictated'
      ? (it.text ? esc(it.text) : '<span class="wf-dim">Nothing was heard.</span>')
      : `<b>${esc(it.title)}</b>${tag}${it.text ? `<br><span class="wf-mut">${esc(String(it.text).slice(0, 260))}</span>` : ''}`;
    return `<div class="wf-row${it.id === FRESH ? ' fresh' : ''}" data-tid="${esc(it.id)}" tabindex="0" role="button" aria-label="Open ${esc(it.title)}">
      <time datetime="${esc(it.created_at || '')}">${esc(hhmm(it.created_at))}</time><p class="wf-txt">${body}</p>
      <span class="wf-ra"><button type="button" class="wf-ic" data-copy="${esc(it.id)}" title="Copy" aria-label="Copy">${I.copy}</button>
        <button type="button" class="wf-ic" data-open="${esc(it.id)}" title="Open" aria-label="Open">${I.open}</button></span></div>`;
  }
  function wireRows() {
    EL.querySelectorAll('.wf-row[data-tid]').forEach(r => {
      r.onclick = e => { if (e.target.closest('[data-copy]')) return; show('t', r.dataset.tid); };
      r.onkeydown = e => { if (e.key === 'Enter') show('t', r.dataset.tid); };
    });
    EL.querySelectorAll('[data-copy]').forEach(b => b.onclick = async e => { e.stopPropagation();
      const it = (OV?.items || []).find(x => x.id === b.dataset.copy); await copy(it?.text || '', true); });
  }
  async function copy(text, say_it) {
    if (!text) { if (say_it) toast('There is no text to copy.', true); return false; }
    try { await navigator.clipboard.writeText(text); if (say_it) toast('Copied.'); return true; }
    catch (e) { if (say_it) toast('The browser did not allow copying.', true); return false; }
  }

  /* ---------------------------------------------------------------- the Flow bar (dictation from any page) */
  function bars(n) { const L = SESS ? Math.max(.12, LEVEL) : .08;
    return Array.from({length: n}, (_, i) => `<i style="height:${Math.round(3 + Math.abs(Math.sin(i * 1.3 + Date.now() / 180)) * 18 * L)}px"></i>`).join(''); }
  function bar() {
    const w = $('#wfbar'); if (!w) return;
    if (LIVE) { w.innerHTML = ''; return; }
    if (BAR === 'writing') { w.innerHTML = '<div class="wf-pill writing" role="status"><i class="wf-spin" aria-hidden="true"></i>Writing it down…</div>'; return; }
    if (BAR === 'rec' && SESS) {
      w.innerHTML = `<div class="wf-live" id="wflive">${esc(SESS.text()) || '<span class="wf-dim">Listening…</span>'}<span class="wf-caret" aria-hidden="true"></span></div>
        <div class="wf-pill" role="group" aria-label="Dictating"><button type="button" class="wf-pbtn" id="wfx" title="Cancel (Esc)" aria-label="Cancel, keep nothing">${I.x}</button>
          <span class="wf-wave" id="wfwave" aria-hidden="true">${bars(14)}</span><span class="wf-clk" id="wfclk">${clock((Date.now() - T0) / 1000)}</span>
          <button type="button" class="wf-pbtn ok" id="wfok" title="Done (Space)" aria-label="Done, write it down">${I.ok}</button></div>`;
      $('#wfx').onclick = cancelDictation; $('#wfok').onclick = finishDictation; return;
    }
    if (BAR === 'starting') { w.innerHTML = '<div class="wf-pill writing" role="status"><i class="wf-spin" aria-hidden="true"></i>Starting the microphone…</div>'; return; }
    w.innerHTML = `<button type="button" class="wf-pill idle" id="wfpill"${canHear() ? '' : ' disabled'} aria-label="Start dictating">
      <span class="wf-pmic" aria-hidden="true">${I.mic}</span><span class="wf-hintt">Click or hold <kbd>Space</kbd> to dictate</span></button>`;
    $('#wfpill').onclick = () => startDictation();
  }
  function tick() {
    clearInterval(TICK);
    TICK = setInterval(() => {
      const c = $('#wfclk'); if (c) c.textContent = clock((Date.now() - T0) / 1000);
      const v = $('#wfwave'); if (v) v.innerHTML = bars(14);
      const lc = $('#wflclk'); if (lc) lc.textContent = clock((Date.now() - T0) / 1000);
    }, 120);
  }
  async function startDictation() {
    if (SESS || BUSY || LIVE) return;
    if (!canHear()) { toast(OV?.engine?.ok === false ? 'The speech engine is not ready on this server.' : 'Recording is off on this server.', true); return; }
    BUSY = true; BAR = 'starting'; bar();
    const s = window.HoolaFlowSession({api, onLevel: l => { LEVEL = l; },
      onWords: t => { const w = $('#wflive'); if (w) w.innerHTML = `${esc(t)}<span class="wf-caret" aria-hidden="true"></span>`; },
      onError: e => toast(e.message || 'A piece of audio was not heard.', true)});
    try { await s.start(); SESS = s; T0 = Date.now(); BAR = 'rec'; tick(); }
    catch (e) { BAR = 'idle'; toast(micWhy(e), true); }
    BUSY = false; bar();
    if (SESS && PEND_STOP) { PEND_STOP = false; finishDictation(); }
  }
  async function finishDictation() {
    if (!SESS || BUSY) return;
    BUSY = true; const s = SESS; BAR = 'writing'; bar(); clearInterval(TICK);
    let text = '', tid = '';
    try {
      const out = await s.stop(); tid = out.transcript_id || '';
      text = s.text();
      if (tid) {
        await api('POST', `/api/flow/t/${encodeURIComponent(tid)}/rename`, {name: `Dictation ${new Date().toLocaleString([], {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'})}`}).catch(() => {});
        const r = await styleOf(tid, STYLE); text = plain(r) || text;
      }
    } catch (e) { toast(e.message, true); }
    SESS = null; BAR = 'idle'; BUSY = false; FRESH = tid;
    await load();
    const copied = await copy(text.trim(), false);
    if (!text.trim()) toast('Nothing was heard - only silence.', true);
    else toast(copied ? 'Copied. Paste it anywhere with Ctrl + V.' : 'Written down. Press Copy on it in your history.');
    if (VIEW === 'home') home(); bar();
  }
  async function cancelDictation() {
    if (!SESS || BUSY) return;
    BUSY = true; const s = SESS; SESS = null; BAR = 'idle'; clearInterval(TICK); bar();
    try { const out = await s.stop(); if (out.transcript_id) await api('DELETE', `/api/flow/t/${encodeURIComponent(out.transcript_id)}`).catch(() => {}); }
    catch (e) { /* the session may already be gone */ }
    BUSY = false; toast('Cancelled. Nothing was kept.');
  }
  function keys() {
    const typing = t => t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
    document.addEventListener('keydown', e => {
      if (!EL || !document.body.contains(EL) || document.querySelector('.wf-modal')) return;
      if (e.key === 'Escape' && SESS) { e.preventDefault(); cancelDictation(); return; }
      if (e.code !== 'Space' || typing(e.target) || VIEW === 'live' || LIVE || e.ctrlKey || e.metaKey || e.altKey) return;
      e.preventDefault();
      if (e.repeat) return;
      if (SESS && !HOLD) { finishDictation(); return; }
      if (!SESS && !BUSY) { HOLD = {t: Date.now()}; startDictation(); }
    });
    document.addEventListener('keyup', e => {
      if (e.code !== 'Space' || !HOLD) return;
      const held = Date.now() - HOLD.t; HOLD = null;
      if (held < 450) return;                                  // a tap keeps listening; Space again or the tick finishes
      if (SESS) finishDictation(); else PEND_STOP = true;       // the mic was still starting: finish as soon as it is up
    });
  }
  function micWhy(e) {
    const m = String(e?.message || e || '');
    if (/denied|NotAllowed|Permission/i.test(m)) return 'Allow the microphone for this site in your browser address bar, then try again.';
    return m || 'The microphone could not start.';
  }
  async function styleOf(tid, style) {
    try { return await api('POST', `/api/kaan/${encodeURIComponent(tid)}/style`, {style}); } catch (e) { return {error: e.message}; }
  }
  function plain(r) {
    if (!r || r.error) return '';
    const x = r.rendered || {};
    if (x.text != null) return x.text;
    if (x.lines) return x.lines.map(l => l.text).join('\n');
    if (x.hook != null) return [x.hook, ...(x.bullets || []).map(b => '• ' + b)].join('\n');
    if (x.minutes) { const m = x.minutes; return [(m.keywords || []).length ? 'Key words: ' + m.keywords.join(', ') : '', ...(m.action_candidates || []).map(c => '• ' + c.text)].filter(Boolean).join('\n'); }
    return '';
  }
  function rendered(r) {
    if (!r) return '';
    if (r.error) return `<span class="wf-bad">${esc(r.error)}</span>`;
    const t = plain(r);
    return t ? esc(t).replace(/\n/g, '<br>') : '<span class="wf-dim">Nothing was heard - only silence.</span>';
  }

  /* ---------------------------------------------------------------- dictionary + snippets (one word list on the server) */
  function modal(title, sub, fields, okText, onOk) {
    const m = document.createElement('div'); m.className = 'wf-modal';
    m.innerHTML = `<form class="wf-dlg" role="dialog" aria-modal="true" aria-labelledby="wfdlgt"><h2 id="wfdlgt">${esc(title)}</h2><p class="wf-sub">${esc(sub)}</p>
      ${fields.map(f => `<label class="wf-lb" for="${f.id}">${esc(f.label)}</label>${f.area
        ? `<textarea id="${f.id}" class="wf-input" rows="3" maxlength="${f.max || 120}" placeholder="${esc(f.ph || '')}"${f.req ? ' required' : ''}></textarea>`
        : `<input id="${f.id}" class="wf-input" maxlength="${f.max || 120}" placeholder="${esc(f.ph || '')}"${f.req ? ' required' : ''}>`}
        ${f.count ? `<p class="wf-count" id="${f.id}n">0 / ${f.max || 120}</p>` : ''}`).join('')}
      <div class="wf-acts"><button type="button" class="wf-btn ghost" data-x>Cancel</button><button type="submit" class="wf-btn dark">${esc(okText)}</button></div></form>`;
    (EL.querySelector('.wf') || document.body).appendChild(m);
    const close = () => m.remove();
    m.querySelector('[data-x]').onclick = close;
    m.onclick = e => { if (e.target === m) close(); };
    m.onkeydown = e => { if (e.key === 'Escape') close(); };
    fields.forEach(f => { if (f.count) { const i = m.querySelector('#' + f.id), n = m.querySelector(`#${f.id}n`); i.oninput = () => { n.textContent = `${i.value.length} / ${f.max || 120}`; }; } });
    m.querySelector('form').onsubmit = async e => { e.preventDefault(); const vals = {}; fields.forEach(f => { vals[f.id] = m.querySelector('#' + f.id).value.trim(); });
      try { await onOk(vals); close(); } catch (er) { toast(er.message, true); } };
    m.querySelector('input,textarea').focus();
  }
  async function removeWord(term) {
    try { await api('DELETE', `/api/kaan/vocab/${encodeURIComponent(term)}`); await loadVoc(); show(VIEW); toast('Removed.'); } catch (e) { toast(e.message, true); }
  }
  async function words() {
    main('<div class="wf-in"><p class="wf-dim">Opening…</p></div>');
    await loadVoc(); if (VIEW !== 'words') return;
    const all = (VOC.items || []).filter(w => w.note !== 'snippet');
    const list = VTAB === 'hints' ? all.filter(w => !w.fix_to) : VTAB === 'fixes' ? all.filter(w => w.fix_to) : all;
    main(`<div class="wf-in">
      <header class="wf-hd"><div><h1 class="wf-h1">Dictionary</h1></div><button type="button" class="wf-btn dark" id="wfadd">Add new</button></header>
      <section class="wf-banner"><i class="wf-tile">${I.dict}</i><div><h2>Hoola spells it your way</h2><p>Names, brands, places and Hinglish words Hoola should spell your way. A word on its own is a listening hint. Add "always write it as" and it is corrected every time.</p></div></section>
      <div class="wf-tabs" role="tablist" aria-label="Show">${[['all', 'All'], ['hints', 'Listening hints'], ['fixes', 'Spelling fixes']].map(([k, n]) =>
        `<button type="button" class="wf-tab" role="tab" data-vt="${k}" aria-selected="${k === VTAB}">${n}</button>`).join('')}</div>
      ${VOC.error ? `<p class="wf-bad">${esc(VOC.error)}</p>` : ''}
      <div class="wf-list">${list.length ? list.map(w => `<div class="wf-wr"><span><span class="wf-word">${esc(w.term)}</span>${w.fix_to
          ? `<span class="wf-arrow">→</span><span class="wf-word">${esc(w.fix_to)}</span>` : '<span class="wf-hint">listening hint</span>'}</span>
          <span class="wf-ra"><button type="button" class="wf-ic" data-rm="${esc(w.term)}" title="Remove" aria-label="Remove ${esc(w.term)}">${I.trash}</button></span></div>`).join('')
        : '<div class="wf-empty"><b>No words yet</b>Add the names and words you say often.</div>'}</div>
      <p class="wf-fine">Used by dictation, files and live captions. Hints share an 800-character space; each word up to 120 characters.</p></div>`);
    EL.querySelectorAll('[data-vt]').forEach(b => b.onclick = () => { VTAB = b.dataset.vt; words(); });
    EL.querySelectorAll('[data-rm]').forEach(b => b.onclick = () => removeWord(b.dataset.rm));
    $('#wfadd').onclick = () => modal('Add to dictionary', 'A word Hoola should hear and spell your way.', [
      {id: 'wfw1', label: 'Word or name', ph: 'e.g. Newtika', req: true}, {id: 'wfw2', label: 'Always write it as (optional)', ph: 'e.g. Newtika Pvt Ltd'}],
    'Add', async v => { await api('POST', '/api/kaan/vocab', {term: v.wfw1, fix_to: v.wfw2}); await loadVoc(); words(); toast('Added.'); });
  }
  async function snippets() {
    main('<div class="wf-in"><p class="wf-dim">Opening…</p></div>');
    await loadVoc(); if (VIEW !== 'snippets') return;
    const list = (VOC.items || []).filter(w => w.note === 'snippet');
    main(`<div class="wf-in">
      <header class="wf-hd"><div><h1 class="wf-h1">Snippets</h1></div><button type="button" class="wf-btn dark" id="wfadd">Add new</button></header>
      <section class="wf-banner"><i class="wf-tile">${I.snip}</i><div><h2>Say less, write more</h2><p>Say a short cue and Hoola writes the whole text - your UPI ID, address, timings, a link. Example: say "my upi" and it becomes your UPI ID.</p></div></section>
      ${VOC.error ? `<p class="wf-bad">${esc(VOC.error)}</p>` : ''}
      <div class="wf-list">${list.length ? list.map(w => `<div class="wf-sn"><span class="wf-cue">${esc(w.term)}</span><span>${esc(w.fix_to)}</span>
          <span class="wf-ra"><button type="button" class="wf-ic" data-rm="${esc(w.term)}" title="Remove" aria-label="Remove ${esc(w.term)}">${I.trash}</button></span></div>`).join('')
        : '<div class="wf-empty"><b>No snippets yet</b>Add one for the things you type again and again.</div>'}</div>
      <p class="wf-fine">A snippet is replaced word for word wherever its cue is heard, so pick a cue you would not say by accident. Up to 120 characters each.</p></div>`);
    EL.querySelectorAll('[data-rm]').forEach(b => b.onclick = () => removeWord(b.dataset.rm));
    $('#wfadd').onclick = () => modal('Add a snippet', 'When you say the cue, Hoola writes the text instead.', [
      {id: 'wfs1', label: 'When I say', ph: 'e.g. my upi', req: true, max: 60}, {id: 'wfs2', label: 'Write', ph: 'e.g. meghana@okaxis', req: true, area: true, count: true, max: 120}],
    'Add snippet', async v => { await api('POST', '/api/kaan/vocab', {term: v.wfs1, fix_to: v.wfs2, note: 'snippet'}); await loadVoc(); snippets(); toast('Snippet added.'); });
  }

  /* ---------------------------------------------------------------- style */
  const SAID = 'so the the meeting moved to friday. tell ravi to bring the samples and send the bill by monday';
  const LOOK = {
    verbatim: ['As said', 'Exactly the words you spoke, nothing touched.', SAID],
    clean: ['Clean', 'Spacing, repeated words and sentence starts tidied. Nothing added or reworded.', 'So the meeting moved to friday. Tell ravi to bring the samples and send the bill by monday'],
    minutes: ['Notes', 'Key words and the things someone has to do, picked from what you said.', 'Key words: meeting, friday, samples, bill\n• tell ravi to bring the samples and send the bill by monday'],
    social: ['Social', 'A first line and short points, ready for a post or a status.', 'So the meeting moved to friday.\n• tell ravi to bring the samples and send the bill by monday'],
  };
  function style() {
    main(`<div class="wf-in">
      <header class="wf-hd"><div><h1 class="wf-h1">Style</h1><p class="wf-sub">How your words read when you stop dictating. Hoola never adds words you did not say - each style only tidies or picks.</p></div></header>
      <div class="wf-styles" role="radiogroup" aria-label="Dictation style">${Object.entries(LOOK).map(([k, [n, d, ex]]) =>
        `<button type="button" class="wf-sty" role="radio" data-sty="${k}" aria-checked="${k === STYLE}"><h3>${n}<i aria-hidden="true">${I.ok}</i></h3><p>${d}</p><div class="wf-bubble">${esc(ex)}</div></button>`).join('')}</div>
      <p class="wf-fine">You said: "${esc(SAID)}". Your choice is kept in this browser. Every transcript can still be opened in any style.</p></div>`);
    EL.querySelectorAll('[data-sty]').forEach(b => b.onclick = () => { STYLE = b.dataset.sty; try { localStorage.setItem('hoola.flow.style', STYLE); } catch (e) {} style(); toast(`Style: ${LOOK[STYLE][0]}.`); });
  }

  /* ---------------------------------------------------------------- files */
  function files() {
    const list = (OV?.items || []).filter(it => it.kind === 'file');
    main(`<div class="wf-in wide">
      <header class="wf-hd"><div><h1 class="wf-h1">A file to text</h1><p class="wf-sub">A meeting, a voice note or a video - every word with its time. Up to 5 GB, and the file never leaves your server.</p></div></header>
      ${notReady()}
      <div class="wf-two"><div class="wf-col">
        <label class="wf-drop" for="wffile" id="wfdrop"><i class="wf-tile">${I.file}</i><b>Drop a recording here, or choose a file</b><span>mp3 · wav · m4a · mp4 · ogg · webm</span>
          <input id="wffile" type="file" accept="audio/*,video/*,.m4a,.mp3,.wav,.ogg,.flac,.webm,.mp4,.mkv,.mov" class="wf-sr"></label>
        <p class="wf-mut" id="wfpicked" role="status"></p>
        <section class="wf-card" id="wfwork" hidden></section>
        ${list.length ? `<div><p class="wf-day">Your files</p><div class="wf-list">${list.map(row).join('')}</div></div>` : ''}
      </div>
      <aside class="wf-card" aria-labelledby="wfop"><h2 id="wfop">Options</h2>
        <label class="wf-lb" for="wflg">Spoken language</label><select id="wflg" class="wf-input"><option value="">Find it myself</option><option value="hi">Hindi</option><option value="mr">Marathi</option><option value="en">English</option><option value="gu">Gujarati</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="bn">Bengali</option><option value="kn">Kannada</option><option value="ml">Malayalam</option><option value="pa">Punjabi</option><option value="ur">Urdu</option></select>
        <label class="wf-lb" for="wfts">Result</label><select id="wfts" class="wf-input"><option value="transcribe">Same language as spoken</option><option value="translate">Translate to English</option></select>
        <label class="wf-lb" for="wfmd">Quality</label><select id="wfmd" class="wf-input"><option value="">Server default${OV?.engine?.default_model ? ` (${esc(OV.engine.default_model)})` : ''}</option>${(OV?.engine?.ladder || []).map(m => `<option value="${esc(m.name)}">${esc(m.name)}${m.note ? ' - ' + esc(String(m.note).slice(0, 48)) : ''}</option>`).join('')}</select>
        <p class="wf-fine">Bigger is slower on this server. "turbo" cannot translate.</p>
        <label class="wf-ck"><input type="checkbox" id="wfvb" checked>Use my dictionary</label>
        <label class="wf-ck"><input type="checkbox" id="wfsp" checked>Split into speakers</label>
        <button type="button" class="wf-btn dark full" id="wfmake" style="margin-top:8px" disabled>Make the transcript</button></aside></div></div>`);
    wireRows();
    let FILE = null;
    const pick = f => { FILE = f || null; $('#wfpicked').textContent = FILE ? `${FILE.name} · ${(FILE.size / 1048576).toFixed(1)} MB` : '';
      $('#wfmake').disabled = !FILE || !canHear(); };
    $('#wffile').onchange = e => pick(e.target.files[0]);
    const d = $('#wfdrop');
    d.ondragover = e => { e.preventDefault(); d.classList.add('over'); }; d.ondragleave = () => d.classList.remove('over');
    d.ondrop = e => { e.preventDefault(); d.classList.remove('over'); pick(e.dataTransfer.files[0]); };
    $('#wfmake').onclick = () => FILE && makeFromFile(FILE);
  }
  async function makeFromFile(file) {
    const w = $('#wfwork'); w.hidden = false; $('#wfmake').disabled = true;
    const t0 = Date.now();
    const draw = (step, bad) => { if (!document.body.contains(w)) return; w.innerHTML = `<div class="wf-work"><b>${esc(file.name)}</b><span class="wf-mono wf-dim">${(file.size / 1048576).toFixed(1)} MB</span></div>
      <p>${bad ? '<i class="wf-dot bad"></i>' : '<i class="wf-dot rec"></i>'}${esc(step)} <span class="wf-mono wf-dim">${clock((Date.now() - t0) / 1000)}</span></p>
      ${bad ? '' : '<p class="wf-fine">The server sends it back in one go when the whole recording is written. A long meeting can take several minutes.</p>'}`; };
    draw('Sending the file and writing the words');
    const tk = setInterval(() => draw('Sending the file and writing the words'), 1000);
    const fd = new FormData();
    fd.append('file', file, file.name); fd.append('model', $('#wfmd').value); fd.append('language', $('#wflg').value);
    fd.append('task', $('#wfts').value); fd.append('vocab', $('#wfvb').checked ? 'true' : 'false');
    fd.append('diarize', $('#wfsp').checked ? 'pause_turns' : '');
    try { const r = await api('POST', '/api/kaan/transcribe', undefined, {form: fd}); clearInterval(tk); await load(); show('t', r.id); }
    catch (e) { clearInterval(tk); draw(e.message || 'The transcript could not be made.', true); const b = $('#wfmake'); if (b) b.disabled = false; }
  }

  /* ---------------------------------------------------------------- one transcript */
  async function transcript(tid, keep) {
    if (!keep || !T || T.id !== tid) {
      main('<div class="wf-in"><p class="wf-dim">Opening…</p></div>');
      try { T = await api('GET', `/api/flow/t/${encodeURIComponent(tid)}`); } catch (e) { main(`<div class="wf-in"><p class="wf-bad">${esc(e.message)}</p></div>`); return; }
      T.view = T.kind === 'dictated' ? STYLE : 'turns'; T.render = null;
      if (T.view !== 'turns') T.render = await styleOf(T.id, T.view);
      MIN = null; api('GET', `/api/kaan/${encodeURIComponent(tid)}/minutes`).then(m => { MIN = m; if (VIEW === 't' && T?.id === tid) transcript(tid, true); }).catch(() => {});
    }
    if (VIEW !== 't' || T.id !== tid) return;
    const sp = T.speakers && T.speakers.turns ? T.speakers.turns : null;
    const body = T.view === 'turns'
      ? (sp ? sp.map(t => `<div class="wf-turn"><div><b class="wf-who s${(t.turn - 1) % 4}">${esc(t.speaker || `Speaker ${t.turn}`)}</b><span class="wf-mono wf-dim">${clock(t.start)}</span>
            <button type="button" class="wf-btn xs ghost" data-name="${t.turn}">${t.speaker ? 'Rename' : 'Name'}</button></div><p>${esc(t.text || '')}</p></div>`).join('')
          + '<p class="wf-fine">Speakers are split where the talking pauses. Hoola does not guess who they are - you name them.</p>'
        : (T.segments || []).map(s => `<div class="wf-turn"><div><span class="wf-mono wf-dim">${clock(s.start)}</span></div><p>${esc(s.text || '')}</p></div>`).join('')
          || `<p class="wf-dim">${esc(T.note || 'Nothing was heard.')}</p>`)
      : `<div class="wf-rend">${rendered(T.render)}</div>${T.render?.note ? `<p class="wf-fine">${esc(T.render.note)}</p>` : ''}`;
    const acts = MIN?.action_candidates || [];
    main(`<div class="wf-in wide">
      <nav class="wf-crumb" aria-label="Breadcrumb"><button type="button" data-home>${I.back}Home</button><span>${esc(T.title)}</span></nav>
      <header class="wf-hd"><div><h1 class="wf-h1">${esc(T.title)}</h1>
        <p class="wf-meta"><span>${clock(T.duration_s)}</span>${T.language ? `<span>${esc(T.language)}</span>` : ''}${sp ? `<span>${sp.length} turns by pauses</span>` : ''}${T.task === 'translate' ? '<span>translated to English</span>' : ''}${T.model ? `<span>model ${esc(T.model)}</span>` : ''}</p></div>
        <div class="wf-acts"><button type="button" class="wf-btn" id="wfcopy">${I.copy}Copy</button><button type="button" class="wf-btn" id="wfgy">Save to Gyaan</button><button type="button" class="wf-btn dark" id="wfchat">Put in the Hoola chat</button></div></header>
      <div class="wf-seg" role="tablist" aria-label="Show as" style="margin-bottom:16px"><button type="button" role="tab" data-tv="turns" aria-selected="${T.view === 'turns'}">${sp ? 'Speakers' : 'With times'}</button>
        ${STY.map(([k, n]) => `<button type="button" role="tab" data-tv="${k}" aria-selected="${T.view === k}">${n}</button>`).join('')}</div>
      <div class="wf-two"><section class="wf-body" aria-label="Transcript">${body}</section>
        <aside class="wf-col">
          <section class="wf-card"><h2>Action items found</h2>
            ${MIN ? (acts.length ? acts.slice(0, 12).map(c => `<p class="wf-ai"><span>${esc(c.text)}</span>${c.speaker ? `<small>${esc(c.speaker)}</small>` : ''}</p>`).join('') + '<p class="wf-fine">Picked by the words used ("will", "by Friday", "need to"...), not decided. Check them.</p><button type="button" class="wf-btn full" style="margin-top:12px" id="wfrem">Make reminders from these</button>' : '<p class="wf-dim">None found in what was said.</p>') : '<p class="wf-dim">Reading…</p>'}
            ${MIN?.keywords?.length ? `<p class="wf-fine">Key words: ${esc(MIN.keywords.join(', '))}</p>` : ''}</section>
          <section class="wf-card"><h2>Download as</h2><div class="wf-grid2">${['srt', 'vtt', 'txt', 'json'].map(f => `<button type="button" class="wf-btn" data-ex="${f}">${{srt: 'SRT subtitles', vtt: 'VTT subtitles', txt: 'Text', json: 'JSON'}[f]}</button>`).join('')}</div></section>
          <section class="wf-card"><h2>This transcript</h2><div class="wf-grid2"><button type="button" class="wf-btn" id="wfask">Ask Hoola</button><button type="button" class="wf-btn" id="wfren">Rename</button>
            <button type="button" class="wf-btn" id="wfpin">${T.pinned ? 'Kept for ever ✓' : 'Keep for ever'}</button><button type="button" class="wf-btn danger" id="wfdel">Delete</button></div></section>
        </aside></div></div>`);
    $('[data-home]').onclick = () => show('home');
    EL.querySelectorAll('[data-tv]').forEach(b => b.onclick = async () => { T.view = b.dataset.tv; if (T.view !== 'turns') T.render = await styleOf(T.id, T.view); transcript(T.id, true); });
    EL.querySelectorAll('[data-name]').forEach(b => b.onclick = () => nameTurn(+b.dataset.name));
    EL.querySelectorAll('[data-ex]').forEach(b => b.onclick = () => download(b.dataset.ex));
    const txt = () => T.view === 'turns' ? (T.text || '') : plain(T.render);
    $('#wfcopy').onclick = () => copy(txt(), true);
    $('#wfchat').onclick = () => say(txt(), false);
    $('#wfgy').onclick = async () => { try { await api('POST', `/api/kaan/${encodeURIComponent(T.id)}/to_gyaan`); toast('Saved to Gyaan.'); } catch (e) { toast(e.message, true); } };
    $('#wfask').onclick = () => say(`About my transcript "${T.title}" (Kaan ${T.id}): `, false);
    $('#wfrem') && ($('#wfrem').onclick = () => say(`Make reminders from these action items in my transcript "${T.title}" (Kaan ${T.id}). Ask me for any date that is not clear:\n${acts.slice(0, 12).map(c => '- ' + c.text).join('\n')}`, false));
    $('#wfren').onclick = () => modal('Rename', 'A name you will recognise later.', [{id: 'wfrn', label: 'Name', req: true, max: 120}], 'Save', async v => {
      await api('POST', `/api/flow/t/${encodeURIComponent(T.id)}/rename`, {name: v.wfrn}); T.title = v.wfrn; await load(); transcript(T.id, true); });
    $('#wfpin').onclick = async () => { try { const r = await api('POST', `/api/flow/t/${encodeURIComponent(T.id)}/pin`, {pinned: !T.pinned}); T.pinned = r.pinned; transcript(T.id, true); } catch (e) { toast(e.message, true); } };
    $('#wfdel').onclick = async () => { if (!confirm(`Delete "${T.title}"? This cannot be undone.`)) return;
      try { await api('DELETE', `/api/flow/t/${encodeURIComponent(T.id)}`); T = null; toast('Deleted.'); await load(); show('home'); } catch (e) { toast(e.message, true); } };
  }
  async function nameTurn(turn) {
    const cur = (T.speakers?.turns || []).find(t => t.turn === turn);
    const n = prompt(`Who is speaking in turn ${turn}?`, cur?.speaker || ''); if (n == null) return;
    const names = {}; (T.speakers?.turns || []).forEach(t => { if (t.speaker) names[String(t.turn)] = t.speaker; });
    if (n.trim()) names[String(turn)] = n.trim(); else delete names[String(turn)];
    try { await api('POST', `/api/kaan/${encodeURIComponent(T.id)}/diarize`, {names}); T = await api('GET', `/api/flow/t/${encodeURIComponent(T.id)}`); T.view = 'turns'; transcript(T.id, true); }
    catch (e) { toast(e.message, true); }
  }
  async function download(fmt) {
    try {
      const r = await api('GET', `/api/kaan/${encodeURIComponent(T.id)}/export?fmt=${fmt}&download=1`, undefined, {raw: true});
      const b = await r.blob(), a = document.createElement('a'), u = URL.createObjectURL(b);
      const m = /filename="([^"]+)"/.exec(r.headers.get('Content-Disposition') || '');
      a.href = u; a.download = m ? m[1] : `${T.id}.${fmt}`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000);
    } catch (e) { toast(e.message, true); }
  }

  /* ---------------------------------------------------------------- live captions */
  function live() {
    const busy = !!LIVE;
    main(`<div class="wf-in wide">${notReady()}<div class="wf-two"><div class="wf-col">
      <header class="wf-hd" style="margin:0"><div style="flex:1">${busy ? `<p class="wf-livebadge"><i class="wf-dot rec"></i>LIVE · <span class="wf-mono" id="wflclk">${clock((Date.now() - T0) / 1000)}</span></p>` : '<h1 class="wf-h1" style="margin-bottom:10px">Live captions</h1>'}
        <label class="wf-sr" for="wfttl">Name</label><input id="wfttl" class="wf-title" placeholder="Name this, e.g. Monday stand-up" value="${esc(LIVE?.title || '')}"></div>
        <div class="wf-acts">${busy ? `<button type="button" class="wf-btn" id="wfpause">${PAUSED ? 'Resume' : 'Pause'}</button><button type="button" class="wf-btn dark" id="wfstop">Stop and save</button>`
          : `<button type="button" class="wf-btn dark" id="wfgo"${canHear() ? '' : ' disabled'}>Start captions</button>`}</div></header>
      <section class="wf-caps" aria-live="polite" aria-label="Captions" id="wfcaps">${busy ? capsHtml() : '<p class="wf-dim">Captions appear here a few seconds after people speak.</p>'}</section>
      <p class="wf-fine">When you stop, the transcript opens with its minutes and action items.</p></div>
      <aside class="wf-col">
        <section class="wf-card"><h2>Listening to</h2><p><i class="wf-dot ok"></i>This computer's microphone</p>
          <p class="wf-fine">A Chrome tab (Meet, Zoom, YouTube): open the Hoola extension and press Live captions - it lands here too.</p></section>
        <section class="wf-card"><h2>Before you start</h2><p class="wf-mut">Tell everyone it is being written down. The red LIVE mark stays on the whole time; Hoola never records in secret.</p></section>
      </aside></div></div>`);
    if (busy) { tick(); $('#wfstop').onclick = stopLive; $('#wfpause').onclick = () => { PAUSED = !PAUSED; LIVE.s.pause(PAUSED); live(); }; }
    else $('#wfgo') && ($('#wfgo').onclick = startLive);
    $('#wfttl').oninput = e => { if (LIVE) LIVE.title = e.target.value; };
  }
  function capsHtml() { const c = LIVE?.caps || []; return c.length ? c.slice(-30).map((p, i, a) => `<p class="wf-cap${i === a.length - 1 ? ' now' : ''}"><span>${clock(p.start)}</span>${esc(p.text)}</p>`).join('') : '<p class="wf-dim">Listening…</p>'; }
  async function startLive() {
    if (BUSY || SESS) return; BUSY = true; PAUSED = false;
    const st = {title: ($('#wfttl')?.value || '').trim(), caps: [], s: null};
    st.s = window.HoolaFlowSession({api, onLevel: l => { LEVEL = l; }, onError: e => toast(e.message, true),
      onWords: (_t, r) => { (r.new || []).forEach(p => st.caps.push(p)); const c = $('#wfcaps'); if (c && VIEW === 'live') { c.innerHTML = capsHtml(); c.scrollTop = c.scrollHeight; } }});
    try { await st.s.start(); LIVE = st; T0 = Date.now(); } catch (e) { toast(micWhy(e), true); }
    BUSY = false; live();
  }
  async function stopLive() {
    if (BUSY) return; BUSY = true;
    const b = $('#wfstop'); if (b) { b.disabled = true; b.textContent = 'Saving…'; }
    let tid = '';
    try { const out = await LIVE.s.stop(); tid = out.transcript_id || '';
      const name = (LIVE.title || '').trim();
      if (tid && name) await api('POST', `/api/flow/t/${encodeURIComponent(tid)}/rename`, {name}).catch(() => {});
      if (tid) await api('POST', `/api/kaan/${encodeURIComponent(tid)}/diarize`, {}).catch(() => {});
    } catch (e) { toast(e.message, true); }
    LIVE = null; BUSY = false; clearInterval(TICK); await load();
    tid ? show('t', tid) : show('live');
  }

  /* ---------------------------------------------------------------- settings (read from the server) */
  function settings() {
    const o = OV || {}, e = o.engine || {}, u = o.usage || {};
    const r = (k, v, sm) => `<div class="wf-tg"><span>${k}${sm ? `<small>${sm}</small>` : ''}</span><span>${v}</span></div>`;
    const on = b => b ? '<span class="wf-on">On</span>' : '<span class="wf-off">Off</span>';
    main(`<div class="wf-in wide"><header class="wf-hd"><div><h1 class="wf-h1">Settings</h1>
      <p class="wf-sub">The engine, limits and doors are set on your server, so everyone using it gets the same rules. This page shows them as they are now.</p></div></header>
      <div class="wf-sets">
        <section class="wf-card"><h2>Engine</h2><p><i class="wf-dot ${e.ok ? 'ok' : 'bad'}"></i>${e.ok ? 'Ready on this server · Whisper (MIT licence)' : esc(e.why || 'Not ready')}</p>
          ${(e.ladder || []).map(m => `<div class="wf-tg"><span class="wf-mono">${esc(m.name)}</span><span class="wf-dim">${m.name === e.default_model ? 'Default for files' : m.name === e.live_model ? 'Default for live' : esc(String(m.note || '').slice(0, 40))}</span></div>`).join('')}</section>
        <section class="wf-card"><h2>Recording and privacy</h2>
          ${r('Recording on this server', on(o.recording?.on), o.recording?.on ? 'Off: nothing is heard or written.' : esc(o.recording?.how || ''))}
          ${r('Split into speakers by pauses', on(o.speakers?.on), 'Turns stay unnamed until you name them')}
          ${r('Know people by their voice', on(o.voiceprint?.on), esc(o.voiceprint?.why || 'Needs their enrolled voice, consent and a delete-after period'))}</section>
        <section class="wf-card"><h2>Limits</h2>
          ${r('Monthly audio limit', u.cap ? `<span class="wf-mono">${esc(String(u.cap))} min</span>` : 'None', 'KAAN_QUOTA_AUDIO_MIN')}
          ${r('Used this month', `<span class="wf-mono">${esc(String(u.minutes ?? 0))} min</span>`, esc(u.month || ''))}
          ${r('Delete transcripts after', o.retention?.days ? `<span class="wf-mono">${esc(String(o.retention.days))} days</span>` : 'Kept', 'KAAN_RETENTION_DAYS · kept-for-ever ones stay')}</section>
        <section class="wf-card"><h2>This browser</h2>
          ${r('Dictation style', esc((LOOK[STYLE] || LOOK.clean)[0]), 'Change it on the Style page')}
          ${r('Dictate on this page', '<kbd>Space</kbd>', 'Hold to talk, or tap and tap again. Esc cancels')}
          ${r('Dictate in the Hoola chat box', '<kbd>Ctrl</kbd> + <kbd>Space</kbd>')}</section>
        <section class="wf-card"><h2>Other ways in</h2><p class="wf-fine">The same engine, switches and limits behind every door.</p>
          ${r('Chrome extension', '<span class="wf-dim">Live captions from a tab</span>')}
          ${r('Phone app', '<span class="wf-dim">Coming</span>')}
          ${r('API', `<span class="wf-mono">${esc(o.doors?.api || '/api/kaan')}</span>`)}
          ${r('MCP for coding tools', `<span class="wf-mono">${esc(o.doors?.mcp || '')}</span>`)}</section>
      </div></div>`);
  }

  return {open, leave, busy: busyNow, show};
};


/* the chat box mic: dictation through Kaan (start / stop). Returns null when it cannot (the caller falls back). */
window.HoolaFlowMic = function ({api, toast, onText, onState}) {
  let S = null, base = '', ready = null;
  async function canUse() {
    if (ready != null) return ready;
    try { const o = await api('GET', '/api/flow/overview?limit=1'); ready = !!o.ready; } catch { ready = false; }
    setTimeout(() => { ready = null; }, 60000);
    return ready;
  }
  return {
    get on() { return !!S; },
    canUse,
    async start(current) {
      base = current ? current.replace(/\s*$/, ' ') : '';
      const s = window.HoolaFlowSession({api, onWords: t => onText(base + t), onError: e => toast(e.message, true)});
      await s.start(); S = s; onState(true);
    },
    async stop() {
      const s = S; if (!s) return; S = null; onState(false, 'writing');
      try { const out = await s.stop(); let t = s.text();
        if (out.transcript_id) {
          await api('POST', `/api/flow/t/${encodeURIComponent(out.transcript_id)}/rename`, {name: 'Dictation (chat box)'}).catch(() => {});
          try { const r = await api('POST', `/api/kaan/${encodeURIComponent(out.transcript_id)}/style`, {style: 'clean'}); if (r?.rendered?.text != null) t = r.rendered.text; } catch {}
        }
        onText(base + (t || '').trim());
      } catch (e) { toast(e.message, true); }
      onState(false);
    }};
};
