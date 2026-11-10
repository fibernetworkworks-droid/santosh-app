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

window.HoolaFlow = function ({api, esc, toast, say}) {
  let EL = null, VIEW = 'home', TID = '', OV = null, T = null, STYLE = 'clean', Q = '', MIN = null;
  let SESS = null, LIVE = null, TICK = 0, T0 = 0, LEVEL = 0, BUSY = false, DONE = null, PAUSED = false;
  const $ = s => EL && EL.querySelector(s);
  const KIND = {dictated: ['Dictated', 'ok'], live: ['Live', 'live'], file: ['File', 'file']};
  const STY = [['verbatim', 'As said'], ['clean', 'Clean'], ['minutes', 'Notes'], ['social', 'Social'], ['subtitles', 'Subtitles']];
  const clock = s => { s = Math.max(0, Math.round(+s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
    return h ? `${h}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}` : `${m}:${String(x).padStart(2, '0')}`; };
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const MIC = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>';
  const UP = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5M5 20h14"/></svg>';
  const LV = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M6.3 6.3a8 8 0 0 0 0 11.4M17.7 6.3a8 8 0 0 1 0 11.4"/></svg>';

  async function load() {
    try { OV = await api('GET', '/api/flow/overview'); } catch (e) { OV = {error: e.message, items: [], engine: {}, recording: {}, usage: {}, retention: {}}; }
  }
  async function open(root, view, arg) { EL = root || EL; if (!EL) return; await load(); show(view || VIEW, arg || TID); }
  function leave() { if (SESS || LIVE) return; clearInterval(TICK); }
  function busyNow() { return !!(SESS || LIVE); }

  function show(view, arg) {
    if (busyNow() && view !== VIEW) { toast('Stop the recording first.', true); return; }
    VIEW = view; TID = arg || ''; clearInterval(TICK);
    const page = {dictate, files, live, words, settings, t: () => transcript(TID)}[view] || home;
    page();
  }
  function frame(body) {
    const nav = [['home', 'Home'], ['dictate', 'Dictate'], ['files', 'Files'], ['live', 'Live captions'], ['words', 'My words'], ['settings', 'Settings']];
    const cur = VIEW === 't' ? 'files' : VIEW;
    EL.innerHTML = `<div class="hfl"><nav class="hfl-side" aria-label="Hoola Flow"><b class="hfl-brand">Hoola Flow</b>
      ${nav.map(([k, n]) => `<button type="button" class="hfl-nv${k === cur ? ' on' : ''}" data-go="${k}"${k === cur ? ' aria-current="page"' : ''}>${n}</button>`).join('')}
      <p class="hfl-fine">Audio and text stay on your server. Nothing goes to an outside service.</p></nav>
      <main class="hfl-main">${notReady()}${body}</main></div>`;
    EL.querySelectorAll('[data-go]').forEach(b => b.onclick = () => show(b.dataset.go));
  }
  function notReady() {
    if (!OV || OV.error) return `<div class="hfl-warn" role="status">Hoola Flow could not read the server: ${esc(OV?.error || '')}</div>`;
    if (!OV.engine?.ok) return `<div class="hfl-warn" role="status"><b>The speech engine is not ready on this server.</b> ${esc(OV.engine?.why || '')} Your saved transcripts still open.</div>`;
    if (!OV.recording?.on) return `<div class="hfl-warn" role="status"><b>Recording is off.</b> ${esc(OV.recording?.how || '')} Your saved transcripts still open.</div>`;
    return '';
  }
  const canHear = () => !!OV?.ready;

  /* ---------------------------------------------------------------- home */
  function home() {
    const items = (OV?.items || []).filter(it => !Q || (it.title + ' ' + it.text).toLowerCase().includes(Q.toLowerCase()));
    const u = OV?.usage || {};
    frame(`<div class="hfl-wrap">
      <h1 class="hfl-h1">Speak. Hoola writes it.</h1>
      <p class="hfl-sub">Dictate a message, turn a recording into text, or caption a meeting as it happens.</p>
      <div class="hfl-starts">
        <button type="button" class="hfl-start main" data-go="dictate"><i class="hfl-ico pri">${MIC}</i><b>Dictate</b><span>Talk in Hindi, Marathi, English or a mix. The text appears, ready to copy or put in the chat.</span><small class="mono">Ctrl + Space in the chat box</small></button>
        <button type="button" class="hfl-start" data-go="files"><i class="hfl-ico">${UP}</i><b>A file to text</b><span>A meeting, voice note or video. Words with their exact time, up to 5 GB.</span><small>mp3 · wav · m4a · mp4 · ogg</small></button>
        <button type="button" class="hfl-start" data-go="live"><i class="hfl-ico red">${LV}</i><b>Live captions</b><span>From your mic. When you stop, it becomes a transcript with minutes.</span><small>Chrome tabs: the Hoola extension</small></button>
      </div>
      <div class="hfl-two">
        <section class="hfl-card grow" aria-labelledby="hflrc">
          <div class="hfl-ch"><h2 id="hflrc">Recent</h2><label class="hfl-sr" for="hflq">Search what was said</label>
            <input id="hflq" class="hfl-in" placeholder="Search what was said" value="${esc(Q)}"></div>
          ${items.length ? items.map(it => { const [kn, kc] = KIND[it.kind] || KIND.file;
            return `<button type="button" class="hfl-row" data-tid="${esc(it.id)}"><span><b>${esc(it.title)}</b><small>${esc(rowMeta(it))}</small></span>
              <span class="hfl-chip ${kc}">${kn}</span><span class="mono hfl-dim">${clock(it.duration_s)}</span></button>`; }).join('')
            : `<p class="hfl-empty">${Q ? 'Nothing said matches that.' : 'Nothing yet. Dictate something or add a recording.'}</p>`}
        </section>
        <aside class="hfl-col">
          <section class="hfl-card"><h2>This month</h2><p class="hfl-big">${esc(String(u.minutes ?? 0))} min</p>
            <p class="hfl-dim">${u.cap ? `of ${esc(String(u.cap))} min allowed` : 'No monthly limit set'}</p></section>
          <section class="hfl-card"><h2>Engine</h2><p class="hfl-st"><i class="hfl-dot ${OV?.ready ? 'ok' : 'bad'}"></i>${OV?.ready ? 'Ready' : 'Not ready'}${OV?.engine?.default_model ? ` · model <span class="mono">${esc(OV.engine.default_model)}</span>` : ''}</p>
            <p class="hfl-dim">${OV?.retention?.days ? `Transcripts are deleted after ${esc(String(OV.retention.days))} days unless kept for ever.` : 'Transcripts are kept until you delete them.'}</p></section>
        </aside></div></div>`);
    EL.querySelectorAll('[data-tid]').forEach(b => b.onclick = () => show('t', b.dataset.tid));
    const q = $('#hflq'); q.oninput = () => { Q = q.value; const p = q.selectionStart; home(); const n = $('#hflq'); n.focus(); n.setSelectionRange(p, p); };
  }
  function rowMeta(it) {
    const bits = [];
    if (it.language) bits.push(it.language);
    if (it.n_turns) bits.push(`${it.n_turns} turns`);
    if (it.task === 'translate') bits.push('translated to English');
    if (it.pinned) bits.push('kept for ever');
    if (it.status === 'empty') bits.push('nothing was heard');
    bits.push(ago(it.created_at));
    return bits.filter(Boolean).join(' · ');
  }

  /* ---------------------------------------------------------------- dictate */
  function dictate() {
    const busy = !!SESS;
    frame(`<div class="hfl-wrap narrow">
      <div class="hfl-top"><p class="hfl-state" role="status">${busy ? `<i class="hfl-dot rec"></i>${PAUSED ? 'Paused' : 'Listening'} · <span class="mono" id="hflclk">${clock((Date.now() - T0) / 1000)}</span>` : DONE ? '<i class="hfl-dot ok"></i>Done' : 'Press Start and speak'}</p>
        ${DONE ? styleBar() : ''}</div>
      <section class="hfl-words" aria-live="polite" aria-label="Your words"><div id="hflw">${DONE ? rendered(DONE.render) : busy ? `${esc(SESS.text())}<span class="hfl-caret" aria-hidden="true"></span>` : '<span class="hfl-dim">Your words will appear here a second or two after you say them.</span>'}</div></section>
      <div class="hfl-meter" aria-hidden="true">${bars()}</div>
      <div class="hfl-acts">${busy ? `<button type="button" class="hfl-btn stop" id="hflstop">Stop</button><button type="button" class="hfl-btn" id="hflpause">${PAUSED ? 'Resume' : 'Pause'}</button>`
        : `<button type="button" class="hfl-btn pri" id="hflgo"${canHear() ? '' : ' disabled'}>${DONE ? 'Dictate again' : 'Start'}</button>`}
        ${DONE ? `<button type="button" class="hfl-btn" id="hflcopy">Copy text</button><button type="button" class="hfl-btn" id="hflchat">Put in the chat box</button><button type="button" class="hfl-btn" id="hflgy">Save to Gyaan</button><button type="button" class="hfl-btn" data-open="${esc(DONE.tid)}">Open transcript</button>` : ''}</div>
      <p class="hfl-fine c">"Clean" tidies spacing, repeats and sentence starts. It never adds or rewords anything you said. Green words came from My words.</p></div>`);
    if (busy) { tick(); return wireBusy(SESS); }
    $('#hflgo') && ($('#hflgo').onclick = startDictate);
    wireDone();
  }
  function bars() { const L = LEVEL; return Array.from({length: 18}, (_, i) => `<span style="height:${Math.round(6 + Math.abs(Math.sin(i * 1.7 + Date.now() / 260)) * 40 * (SESS || LIVE ? Math.max(.15, L) : .1))}px"></span>`).join(''); }
  function tick() {
    clearInterval(TICK);
    TICK = setInterval(() => { const c = $('#hflclk'); if (c) c.textContent = clock((Date.now() - T0) / 1000); const m = $('.hfl-meter'); if (m) m.innerHTML = bars(); }, 250);
  }
  function wireBusy(s) {
    $('#hflstop').onclick = () => finish(s);
    $('#hflpause').onclick = () => { PAUSED = !PAUSED; s.pause(PAUSED); show(VIEW); };
  }
  async function startDictate() {
    if (BUSY) return; BUSY = true; DONE = null; PAUSED = false;
    const s = window.HoolaFlowSession({api, onLevel: l => { LEVEL = l; },
      onWords: t => { const w = $('#hflw'); if (w && VIEW === 'dictate') w.innerHTML = `${esc(t)}<span class="hfl-caret" aria-hidden="true"></span>`; },
      onError: e => toast(e.message || 'A piece of audio was not heard.', true)});
    try { await s.start(); SESS = s; T0 = Date.now(); } catch (e) { toast(micWhy(e), true); }
    BUSY = false; show('dictate');
  }
  async function finish(s) {
    if (BUSY) return; BUSY = true;
    const btn = $('#hflstop'); if (btn) { btn.disabled = true; btn.textContent = 'Writing the last words…'; }
    try {
      const out = await s.stop();
      const tid = out.transcript_id;
      if (tid) {
        await api('POST', `/api/flow/t/${encodeURIComponent(tid)}/rename`, {name: `Dictation ${new Date().toLocaleString([], {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'})}`}).catch(() => {});
        DONE = {tid, render: await styleOf(tid, STYLE)};
      } else DONE = null;
    } catch (e) { toast(e.message, true); }
    SESS = null; BUSY = false; clearInterval(TICK); await load(); show('dictate');
  }
  function micWhy(e) {
    const m = String(e?.message || e || '');
    if (/denied|NotAllowed|Permission/i.test(m)) return 'Allow the microphone for this site in your browser address bar, then try again.';
    return m || 'The microphone could not start.';
  }
  function styleBar() {
    return `<div class="hfl-seg" role="group" aria-label="How the text should read">${STY.filter(s => s[0] !== 'subtitles').map(([k, n]) => `<button type="button" data-style="${k}" aria-pressed="${k === STYLE}">${n}</button>`).join('')}</div>`;
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
    if (r.error) return `<span class="hfl-bad">${esc(r.error)}</span>`;
    const t = plain(r);
    return t ? esc(t).replace(/\n/g, '<br>') : '<span class="hfl-dim">Nothing was heard - only silence.</span>';
  }
  function wireDone() {
    EL.querySelectorAll('[data-style]').forEach(b => b.onclick = async () => {
      STYLE = b.dataset.style;
      if (VIEW === 'dictate' && DONE) { DONE.render = await styleOf(DONE.tid, STYLE); dictate(); }
      if (VIEW === 't' && T) { T.render = await styleOf(T.id, STYLE); transcript(T.id, true); }
    });
    EL.querySelectorAll('[data-open]').forEach(b => b.onclick = () => show('t', b.dataset.open));
    const txt = () => plain(VIEW === 't' ? T?.render : DONE?.render);
    $('#hflcopy') && ($('#hflcopy').onclick = async () => { try { await navigator.clipboard.writeText(txt()); toast('Copied.'); } catch { toast('The browser did not allow copying.', true); } });
    $('#hflchat') && ($('#hflchat').onclick = () => say(txt(), false));
    $('#hflgy') && ($('#hflgy').onclick = async () => { const id = VIEW === 't' ? T?.id : DONE?.tid;
      try { await api('POST', `/api/kaan/${encodeURIComponent(id)}/to_gyaan`); toast('Saved to Gyaan.'); } catch (e) { toast(e.message, true); } });
  }

  /* ---------------------------------------------------------------- files */
  function files() {
    const list = (OV?.items || []).filter(it => it.kind === 'file');
    frame(`<div class="hfl-wrap"><div class="hfl-two">
      <div class="grow">
        <h1 class="hfl-h1 sm">A file to text</h1>
        <label class="hfl-drop" for="hflfile" id="hfldrop">${UP}<b>Drop a recording here, or choose a file</b><span>Audio or video up to 5 GB</span>
          <input id="hflfile" type="file" accept="audio/*,video/*,.m4a,.mp3,.wav,.ogg,.flac,.webm,.mp4,.mkv,.mov" class="hfl-sr"></label>
        <p class="hfl-picked" id="hflpicked" role="status"></p>
        <section class="hfl-card" id="hflwork" hidden></section>
        ${list.length ? `<section class="hfl-card" aria-labelledby="hflfl"><h2 id="hflfl">Your files</h2>${list.map(it => `<button type="button" class="hfl-row" data-tid="${esc(it.id)}"><span><b>${esc(it.title)}</b><small>${esc(rowMeta(it))}</small></span><span></span><span class="mono hfl-dim">${clock(it.duration_s)}</span></button>`).join('')}</section>` : ''}
      </div>
      <aside class="hfl-card hfl-opts" aria-labelledby="hflop"><h2 id="hflop">Options</h2>
        <label class="hfl-lb" for="hfllg">Spoken language</label><select id="hfllg" class="hfl-in"><option value="">Find it myself</option><option value="hi">Hindi</option><option value="mr">Marathi</option><option value="en">English</option><option value="gu">Gujarati</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="bn">Bengali</option><option value="kn">Kannada</option><option value="ml">Malayalam</option><option value="pa">Punjabi</option><option value="ur">Urdu</option></select>
        <label class="hfl-lb" for="hflts">Result</label><select id="hflts" class="hfl-in"><option value="transcribe">Same language as spoken</option><option value="translate">Translate to English</option></select>
        <label class="hfl-lb" for="hflmd">Quality</label><select id="hflmd" class="hfl-in"><option value="">Server default${OV?.engine?.default_model ? ` (${esc(OV.engine.default_model)})` : ''}</option>${(OV?.engine?.ladder || []).map(m => `<option value="${esc(m.name)}">${esc(m.name)}${m.note ? ' - ' + esc(String(m.note).slice(0, 48)) : ''}</option>`).join('')}</select>
        <p class="hfl-fine">Bigger is slower on this server. "turbo" cannot translate.</p>
        <label class="hfl-ck"><input type="checkbox" id="hflvb" checked>Use my word list</label>
        <label class="hfl-ck"><input type="checkbox" id="hflsp" checked>Split into speakers</label>
        <button type="button" class="hfl-btn pri" id="hflmake" disabled>Make the transcript</button>
        <p class="hfl-fine">The file never leaves your server.</p></aside></div></div>`);
    EL.querySelectorAll('[data-tid]').forEach(b => b.onclick = () => show('t', b.dataset.tid));
    let FILE = null;
    const pick = f => { FILE = f || null; $('#hflpicked').textContent = FILE ? `${FILE.name} · ${(FILE.size / 1048576).toFixed(1)} MB` : '';
      $('#hflmake').disabled = !FILE || !canHear(); };
    $('#hflfile').onchange = e => pick(e.target.files[0]);
    const d = $('#hfldrop');
    d.ondragover = e => { e.preventDefault(); d.classList.add('over'); }; d.ondragleave = () => d.classList.remove('over');
    d.ondrop = e => { e.preventDefault(); d.classList.remove('over'); pick(e.dataTransfer.files[0]); };
    $('#hflmake').onclick = () => FILE && makeFromFile(FILE);
  }
  async function makeFromFile(file) {
    const w = $('#hflwork'); w.hidden = false; $('#hflmake').disabled = true;
    const t0 = Date.now();
    const draw = (step, bad) => { w.innerHTML = `<div class="hfl-ch"><b>${esc(file.name)}</b><span class="mono hfl-dim">${(file.size / 1048576).toFixed(1)} MB</span></div>
      <p class="hfl-st">${bad ? '<i class="hfl-dot bad"></i>' : '<i class="hfl-spin" aria-hidden="true"></i>'}${esc(step)} <span class="mono hfl-dim">${clock((Date.now() - t0) / 1000)}</span></p>
      ${bad ? '' : '<p class="hfl-fine">The server sends it back in one go when the whole recording is written. A long meeting can take several minutes.</p>'}`; };
    draw('Sending the file and writing the words');
    const tk = setInterval(() => draw('Sending the file and writing the words'), 1000);
    const fd = new FormData();
    fd.append('file', file, file.name); fd.append('model', $('#hflmd').value); fd.append('language', $('#hfllg').value);
    fd.append('task', $('#hflts').value); fd.append('vocab', $('#hflvb').checked ? 'true' : 'false');
    fd.append('diarize', $('#hflsp').checked ? 'pause_turns' : '');
    try { const r = await api('POST', '/api/kaan/transcribe', undefined, {form: fd}); clearInterval(tk); await load(); show('t', r.id); }
    catch (e) { clearInterval(tk); draw(e.message || 'The transcript could not be made.', true); $('#hflmake').disabled = false; }
  }

  /* ---------------------------------------------------------------- one transcript */
  async function transcript(tid, keep) {
    if (!keep || !T || T.id !== tid) {
      frame('<div class="hfl-wrap"><p class="hfl-dim">Opening…</p></div>');
      try { T = await api('GET', `/api/flow/t/${encodeURIComponent(tid)}`); } catch (e) { frame(`<div class="hfl-wrap"><p class="hfl-bad">${esc(e.message)}</p></div>`); return; }
      T.view = 'turns'; T.render = null;
      MIN = null; api('GET', `/api/kaan/${encodeURIComponent(tid)}/minutes`).then(m => { MIN = m; if (VIEW === 't' && T?.id === tid) transcript(tid, true); }).catch(() => {});
    }
    const sp = T.speakers && T.speakers.turns ? T.speakers.turns : null;
    const body = T.view === 'turns'
      ? (sp ? sp.map(t => `<div class="hfl-turn"><div><b class="hfl-who s${(t.turn - 1) % 4}">${esc(t.speaker || `Speaker ${t.turn}`)}</b><span class="mono hfl-tm">${clock(t.start)}</span>
            <button type="button" class="hfl-btn xs" data-name="${t.turn}">${t.speaker ? 'Rename' : 'Name'}</button></div><p>${esc(t.text || '')}</p></div>`).join('')
          + '<p class="hfl-fine">Speakers are split where the talking pauses. Hoola does not guess who they are - you name them.</p>'
        : (T.segments || []).map(s => `<div class="hfl-turn"><div><span class="mono hfl-tm">${clock(s.start)}</span></div><p>${esc(s.text || '')}</p></div>`).join('')
          || `<p class="hfl-dim">${esc(T.note || 'Nothing was heard.')}</p>`)
      : `<div class="hfl-rend">${rendered(T.render)}</div>${T.render?.note ? `<p class="hfl-fine">${esc(T.render.note)}</p>` : ''}`;
    const acts = MIN?.action_candidates || [];
    frame(`<div class="hfl-wrap wide">
      <nav class="hfl-crumb" aria-label="Breadcrumb"><button type="button" data-go="home">Hoola Flow</button> / ${esc(T.title)}</nav>
      <header class="hfl-head"><div><h1 class="hfl-h1 sm">${esc(T.title)}</h1>
        <p class="hfl-dim">${clock(T.duration_s)}${T.language ? ' · ' + esc(T.language) : ''}${sp ? ` · ${sp.length} turns by pauses` : ''}${T.task === 'translate' ? ' · translated to English' : ''}${T.model ? ` · model ${esc(T.model)}` : ''}</p></div>
        <div class="hfl-acts r"><button type="button" class="hfl-btn" id="hflcopy">Copy text</button><button type="button" class="hfl-btn" id="hflgy">Save to Gyaan</button><button type="button" class="hfl-btn" id="hflask">Ask Hoola about it</button></div></header>
      <div class="hfl-tabs" role="tablist" aria-label="Show as"><button type="button" role="tab" data-tv="turns" aria-selected="${T.view === 'turns'}">${sp ? 'Speakers' : 'With times'}</button>
        ${STY.map(([k, n]) => `<button type="button" role="tab" data-tv="${k}" aria-selected="${T.view === k}">${n}</button>`).join('')}</div>
      <div class="hfl-two"><section class="grow hfl-body" aria-label="Transcript">${body}</section>
        <aside class="hfl-col">
          <section class="hfl-card"><h2>Action items found</h2>
            ${MIN ? (acts.length ? acts.slice(0, 12).map(c => `<p class="hfl-ai"><span>${esc(c.text)}</span>${c.speaker ? `<small>${esc(c.speaker)}</small>` : ''}</p>`).join('') + '<p class="hfl-fine">Picked by the words used ("will", "by Friday", "karna hai"...), not decided. Check them.</p><button type="button" class="hfl-btn wide" id="hflrem">Make reminders from these</button>' : '<p class="hfl-dim">None found in what was said.</p>') : '<p class="hfl-dim">Reading…</p>'}
            ${MIN?.keywords?.length ? `<p class="hfl-fine">Key words: ${esc(MIN.keywords.join(', '))}</p>` : ''}</section>
          <section class="hfl-card"><h2>Download as</h2><div class="hfl-grid2">${['srt', 'vtt', 'txt', 'json'].map(f => `<button type="button" class="hfl-btn" data-ex="${f}">${{srt: 'SRT subtitles', vtt: 'VTT subtitles', txt: 'Text', json: 'JSON'}[f]}</button>`).join('')}</div></section>
          <div class="hfl-acts"><button type="button" class="hfl-btn" id="hflren">Rename</button><button type="button" class="hfl-btn" id="hflpin">${T.pinned ? 'Kept for ever ✓' : 'Keep for ever'}</button><button type="button" class="hfl-btn danger" id="hfldel">Delete</button></div>
        </aside></div></div>`);
    wireDone();
    EL.querySelectorAll('[data-tv]').forEach(b => b.onclick = async () => { T.view = b.dataset.tv; if (T.view !== 'turns') T.render = await styleOf(T.id, T.view); transcript(T.id, true); });
    EL.querySelectorAll('[data-name]').forEach(b => b.onclick = () => nameTurn(+b.dataset.name));
    EL.querySelectorAll('[data-ex]').forEach(b => b.onclick = () => download(b.dataset.ex));
    $('#hflcopy').onclick = async () => { const t = T.view === 'turns' ? (T.text || '') : plain(T.render); try { await navigator.clipboard.writeText(t); toast('Copied.'); } catch { toast('The browser did not allow copying.', true); } };
    $('#hflask').onclick = () => say(`About my transcript "${T.title}" (Kaan ${T.id}): `, false);
    $('#hflrem') && ($('#hflrem').onclick = () => say(`Make reminders from these action items in my transcript "${T.title}" (Kaan ${T.id}). Ask me for any date that is not clear:\n${acts.slice(0, 12).map(c => '- ' + c.text).join('\n')}`, false));
    $('#hflren').onclick = async () => { const n = prompt('Name this transcript', T.title); if (!n) return;
      try { await api('POST', `/api/flow/t/${encodeURIComponent(T.id)}/rename`, {name: n}); T.title = n; T.file_name = n; await load(); transcript(T.id, true); } catch (e) { toast(e.message, true); } };
    $('#hflpin').onclick = async () => { try { const r = await api('POST', `/api/flow/t/${encodeURIComponent(T.id)}/pin`, {pinned: !T.pinned}); T.pinned = r.pinned; transcript(T.id, true); } catch (e) { toast(e.message, true); } };
    $('#hfldel').onclick = async () => { if (!confirm(`Delete "${T.title}"? This cannot be undone.`)) return;
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

  /* ---------------------------------------------------------------- live */
  function live() {
    const busy = !!LIVE;
    frame(`<div class="hfl-wrap"><div class="hfl-two"><div class="grow">
      <header class="hfl-head"><div>${busy ? `<p class="hfl-state live"><i class="hfl-dot rec"></i>LIVE · <span class="mono" id="hflclk">${clock((Date.now() - T0) / 1000)}</span></p>` : ''}
        <label class="hfl-sr" for="hflttl">Name</label><input id="hflttl" class="hfl-title" placeholder="Name this, e.g. Monday stand-up" value="${esc(LIVE?.title || '')}"></div>
        <div class="hfl-acts r">${busy ? `<button type="button" class="hfl-btn" id="hflpause">${PAUSED ? 'Resume' : 'Pause'}</button><button type="button" class="hfl-btn stop" id="hflstop">Stop and save</button>`
          : `<button type="button" class="hfl-btn pri" id="hflgo"${canHear() ? '' : ' disabled'}>Start captions</button>`}</div></header>
      <section class="hfl-caps" aria-live="polite" aria-label="Captions" id="hflcaps">${busy ? capsHtml() : '<p class="hfl-dim">Captions appear here a few seconds after people speak.</p>'}</section>
      <p class="hfl-fine">When you stop, the transcript opens with its minutes and action items.</p></div>
      <aside class="hfl-col">
        <section class="hfl-card"><h2>Listening to</h2><p class="hfl-st"><i class="hfl-dot ok"></i>This computer's microphone</p>
          <p class="hfl-fine">A Chrome tab (Meet, Zoom, YouTube): open the Hoola extension and press Live captions - it lands here too. Phone: coming.</p></section>
        <section class="hfl-card"><h2>Before you start</h2><p class="hfl-dim">Tell everyone it is being written down. The red LIVE mark stays on the whole time; Hoola never records in secret.</p></section>
      </aside></div></div>`);
    if (busy) { tick(); $('#hflstop').onclick = stopLive; $('#hflpause').onclick = () => { PAUSED = !PAUSED; LIVE.s.pause(PAUSED); live(); }; }
    else $('#hflgo') && ($('#hflgo').onclick = startLive);
    $('#hflttl').oninput = e => { if (LIVE) LIVE.title = e.target.value; };
  }
  function capsHtml() { const c = LIVE?.caps || []; return c.length ? c.slice(-30).map((p, i, a) => `<p class="hfl-cap${i === a.length - 1 ? ' now' : ''}"><span class="mono">${clock(p.start)}</span>${esc(p.text)}</p>`).join('') : '<p class="hfl-dim">Listening…</p>'; }
  async function startLive() {
    if (BUSY) return; BUSY = true; PAUSED = false;
    const title = ($('#hflttl')?.value || '').trim();
    const st = {title, caps: [], s: null};
    st.s = window.HoolaFlowSession({api, onLevel: l => { LEVEL = l; }, onError: e => toast(e.message, true),
      onWords: (_t, r) => { (r.new || []).forEach(p => st.caps.push(p)); const c = $('#hflcaps'); if (c && VIEW === 'live') { c.innerHTML = capsHtml(); c.scrollTop = c.scrollHeight; } }});
    try { await st.s.start(); LIVE = st; T0 = Date.now(); } catch (e) { toast(micWhy(e), true); }
    BUSY = false; live();
  }
  async function stopLive() {
    if (BUSY) return; BUSY = true;
    const b = $('#hflstop'); if (b) { b.disabled = true; b.textContent = 'Saving…'; }
    let tid = '';
    try { const out = await LIVE.s.stop(); tid = out.transcript_id || '';
      const name = (LIVE.title || '').trim();
      if (tid && name) await api('POST', `/api/flow/t/${encodeURIComponent(tid)}/rename`, {name}).catch(() => {});
      if (tid) await api('POST', `/api/kaan/${encodeURIComponent(tid)}/diarize`, {}).catch(() => {});
    } catch (e) { toast(e.message, true); }
    LIVE = null; BUSY = false; clearInterval(TICK); await load();
    tid ? show('t', tid) : show('live');
  }

  /* ---------------------------------------------------------------- words */
  async function words() {
    let V = {items: []}; try { V = await api('GET', '/api/kaan/vocab'); } catch (e) { V.error = e.message; }
    frame(`<div class="hfl-wrap narrow"><h1 class="hfl-h1 sm">My words</h1>
      <p class="hfl-sub">Names, brands and terms Hoola should spell your way. A word alone is a listening hint. With "always write as" it is replaced every time, and the transcript notes how many it fixed.</p>
      <form class="hfl-card hfl-add" id="hfladd"><div><label class="hfl-lb" for="hflw1">Word or name</label><input id="hflw1" class="hfl-in" placeholder="e.g. Newtika" required></div>
        <div><label class="hfl-lb" for="hflw2">Always write as (optional)</label><input id="hflw2" class="hfl-in" placeholder="e.g. Newtika Pvt Ltd"></div>
        <button type="submit" class="hfl-btn pri">Add</button></form>
      ${V.error ? `<p class="hfl-bad">${esc(V.error)}</p>` : ''}
      <section class="hfl-card" aria-label="Your words">${(V.items || []).length ? `<div class="hfl-wr hd"><span>Word</span><span>Always written as</span><span></span></div>` + V.items.map(w => `<div class="hfl-wr"><span>${esc(w.term)}</span><span${w.fix_to ? '' : ' class="hfl-dim"'}>${esc(w.fix_to || 'hint only')}</span><button type="button" class="hfl-btn xs" data-rm="${esc(w.term)}">Remove</button></div>`).join('') : '<p class="hfl-empty">No words yet.</p>'}</section>
      <p class="hfl-fine">Used by Dictate, files and live captions. Hints share an 800-character space.</p></div>`);
    $('#hfladd').onsubmit = async e => { e.preventDefault();
      try { await api('POST', '/api/kaan/vocab', {term: $('#hflw1').value.trim(), fix_to: $('#hflw2').value.trim()}); words(); } catch (er) { toast(er.message, true); } };
    EL.querySelectorAll('[data-rm]').forEach(b => b.onclick = async () => { try { await api('DELETE', `/api/kaan/vocab/${encodeURIComponent(b.dataset.rm)}`); words(); } catch (e) { toast(e.message, true); } });
  }

  /* ---------------------------------------------------------------- settings (read from the server) */
  function settings() {
    const o = OV || {}, e = o.engine || {}, u = o.usage || {};
    const row = (k, v, sm) => `<div class="hfl-tg"><span>${k}${sm ? `<small>${sm}</small>` : ''}</span><span>${v}</span></div>`;
    const on = b => b ? '<span class="hfl-on">On</span>' : '<span class="hfl-off">Off</span>';
    frame(`<div class="hfl-wrap wide"><h1 class="hfl-h1 sm">Engine, limits and doors</h1>
      <p class="hfl-sub">These are set on your server (its settings file), so everyone using it gets the same rules. This page shows them as they are now.</p>
      <div class="hfl-grid2 big">
        <section class="hfl-card"><h2>Engine</h2><p class="hfl-st"><i class="hfl-dot ${e.ok ? 'ok' : 'bad'}"></i>${e.ok ? 'Ready on this server · Whisper (MIT licence)' : esc(e.why || 'Not ready')}</p>
          ${(e.ladder || []).map(m => `<div class="hfl-tg"><span class="mono">${esc(m.name)}</span><span class="hfl-dim">${m.name === e.default_model ? 'Default for files' : m.name === e.live_model ? 'Default for live' : esc(String(m.note || '').slice(0, 40))}</span></div>`).join('')}</section>
        <section class="hfl-card"><h2>Recording and privacy</h2>
          ${row('Recording on this server', on(o.recording?.on), o.recording?.on ? 'Off: nothing is heard or written.' : esc(o.recording?.how || ''))}
          ${row('Split into speakers by pauses', on(o.speakers?.on), 'Turns stay unnamed until you name them')}
          ${row('Know people by their voice', on(o.voiceprint?.on), esc(o.voiceprint?.why || 'Needs their enrolled voice, consent and a delete-after period'))}</section>
        <section class="hfl-card"><h2>Limits</h2>
          ${row('Monthly audio limit', u.cap ? `<span class="mono">${esc(String(u.cap))} min</span>` : 'None', 'KAAN_QUOTA_AUDIO_MIN')}
          ${row('Used this month', `<span class="mono">${esc(String(u.minutes ?? 0))} min</span>`, esc(u.month || ''))}
          ${row('Delete transcripts after', o.retention?.days ? `<span class="mono">${esc(String(o.retention.days))} days</span>` : 'Kept', 'KAAN_RETENTION_DAYS · kept-for-ever ones stay')}</section>
        <section class="hfl-card"><h2>Other ways in</h2><p class="hfl-fine">The same engine, switches and limits behind every door.</p>
          ${row('Chrome extension', '<span class="hfl-dim">Live captions from a tab</span>')}
          ${row('Phone app', '<span class="hfl-dim">Coming</span>')}
          ${row('API', `<span class="mono">${esc(o.doors?.api || '/api/kaan')}</span>`)}
          ${row('MCP for coding tools', `<span class="mono">${esc(o.doors?.mcp || '')}</span>`)}</section>
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
