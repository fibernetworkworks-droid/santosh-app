/* v0.999.224 THE CHAT BOX MICROPHONE (owner: "THE CONSOLE MICROPHONE NOT FUNCTIONING PROPERLY - FIND THE BUG, DESIGN -
   MAKE IT ADVANCED, PREMIUM AND PROFESSIONAL - MATCHING THIS CHAT PANEL DESIGN").

   The bugs the old composer mic (v0.173 in v2.js) had, each fixed here:
     1. it always listened for HINDI (lang hi-IN), so English came back as the wrong words or in Devanagari -
        now the language she speaks (her browser's first language, then her pick, kept in this browser)
     2. sending a message while it listened did not stop it: the next result wrote the SENT words back into the box
     3. Chrome ends a "continuous" session by itself after a pause - the mic just went off mid-sentence; now it carries on
        until she finishes (three silent rounds in a row = it stops and says so)
     4. typing while it listened was overwritten by the next result; now her typing is kept and dictation goes on after it
     5. only "not allowed" said anything - no microphone, no network, a language the browser cannot type were silent
     6. a browser without speech typing (Firefox) was thrown onto the voice call page; now it says what to use instead
     7. Ctrl + Space only worked with the Hoola Flow engine; now with both
   The design: tapping the mic turns the row under the words into one recording bar - cancel, a live waveform of her
   voice, the state, the language, the clock, and Done in ink (the Send button's black circle). No red pulse, no colour
   outside the page's own ink. Esc cancels (her words before dictation come back), Ctrl + Space or Done finishes,
   Enter sends what is in the box. Hoola Flow (Kaan, her own server) still runs first when its engine is ready. */
(() => {
  const LANGS = [['en-IN', 'English (India)'], ['en-US', 'English (US)'], ['en-GB', 'English (UK)'], ['hi-IN', 'Hindi'],
    ['mr-IN', 'Marathi'], ['bn-IN', 'Bengali'], ['ta-IN', 'Tamil'], ['te-IN', 'Telugu'], ['gu-IN', 'Gujarati'],
    ['kn-IN', 'Kannada'], ['ml-IN', 'Malayalam'], ['pa-IN', 'Punjabi'], ['ur-IN', 'Urdu'], ['es-ES', 'Spanish'],
    ['fr-FR', 'French'], ['de-DE', 'German'], ['pt-BR', 'Portuguese'], ['ar-SA', 'Arabic'], ['id-ID', 'Indonesian'],
    ['ja-JP', 'Japanese'], ['zh-CN', 'Chinese']];
  const KEY = 'hoola.dictate.lang';
  const ICON = {
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.4 2.6 3.5 5.4 3.5 8.5s-1.1 5.9-3.5 8.5c-2.4-2.6-3.5-5.4-3.5-8.5s1.1-5.9 3.5-8.5z"/></svg>',
    down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10l5 5 5-5"/></svg>'};

  function label(code) {
    const k = LANGS.find(([c]) => c.toLowerCase() === String(code).toLowerCase()); if (k) return k[1];
    try { return new Intl.DisplayNames(['en'], {type: 'language'}).of(code) || code; } catch { return code; }
  }
  function pickDefault() {
    let saved = ''; try { saved = localStorage.getItem(KEY) || ''; } catch { /* private window */ }
    if (saved) return saved;
    const want = (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en-IN']).filter(Boolean);
    for (const w of want) { const hit = LANGS.find(([c]) => c.toLowerCase() === w.toLowerCase()); if (hit) return hit[0]; }
    for (const w of want) { if (/-/.test(w)) return w; const hit = LANGS.find(([c]) => c.split('-')[0] === w.toLowerCase()); if (hit) return hit[0]; }
    return 'en-IN';
  }
  const ERR = {
    'not-allowed': 'Hoola cannot use the microphone. Allow it for this site (the icon at the left of the address bar), then try again.',
    'service-not-allowed': 'This browser has turned off speech typing for this site. Allow the microphone in the address bar, or use Chrome or Edge.',
    'audio-capture': 'No microphone was found. Plug one in, or choose one in your computer\'s sound settings.',
    'network': 'Speech typing in this browser needs the internet and could not reach it. Check your connection and try again.',
    'language-not-supported': 'This browser cannot type that language. Pick another language on the microphone bar.',
    'bad-grammar': 'Speech typing stopped. Try again.'};

  window.HoolaDictate = function ({composer, msg, button, toast, flow, onWrite}) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const row = composer.querySelector('.row');
    let lang = pickDefault();
    let S = null;          // the running dictation
    let bar = null, cv = null, raf = 0, tick = 0;

    function build() {
      if (bar) return;
      bar = document.createElement('div'); bar.className = 'dictbar'; bar.hidden = true;
      bar.setAttribute('role', 'group'); bar.setAttribute('aria-label', 'Dictation');
      bar.innerHTML = `<button type="button" class="dx" aria-label="Cancel dictation" title="Cancel (Esc)">${ICON.x}</button>
        <span class="dwave" aria-hidden="true"><canvas></canvas></span>
        <span class="dstate" aria-live="polite">Listening</span>
        <button type="button" class="dlang" aria-haspopup="menu" aria-label="Language you speak" title="Language you speak">${ICON.globe}<span class="dl"></span>${ICON.down}</button>
        <span class="dtime" aria-label="Time">0:00</span>
        <button type="button" class="dok" aria-label="Finish dictation" title="Done (Ctrl + Space)">${ICON.ok}</button>`;
      row.append(bar);
      cv = bar.querySelector('canvas');
      bar.querySelector('.dx').addEventListener('click', () => cancel());
      bar.querySelector('.dok').addEventListener('click', () => finish());
      bar.querySelector('.dlang').addEventListener('click', e => langMenu(e.currentTarget));
    }
    function paintLang() { if (!bar) return; const l = label(lang); bar.querySelector('.dl').textContent = l.replace(/\s*\(.*\)$/, ''); bar.querySelector('.dlang').title = `Language you speak: ${l}`; }
    function setState(t) { if (bar) bar.querySelector('.dstate').textContent = t; }
    function show(on) {
      build(); bar.hidden = !on; composer.classList.toggle('dicting', !!on);
      if (on && !msg.dataset.ph) { msg.dataset.ph = msg.placeholder; msg.placeholder = 'Speak - your words appear here'; }
      if (!on && msg.dataset.ph != null) { msg.placeholder = msg.dataset.ph; delete msg.dataset.ph; }
      button.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (on) { paintLang(); bar.querySelector('.dlang').hidden = !!(S && S.engine === 'flow'); }
    }

    /* --- the live waveform: her real voice level (an analyser on the microphone) or, where the browser keeps the
       microphone to itself (phones), a gentle level from the speech events. Bars in the page's own ink. */
    const LEVELS = new Array(48).fill(0);
    let level = 0, synth = 0;
    function pushLevel(v) { level = Math.max(0, Math.min(1, v)); }
    async function meter() {
      if (!navigator.mediaDevices?.getUserMedia || /Android|iPhone|iPad/i.test(navigator.userAgent)) return null;
      try {
        const st = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, channelCount: 1}});
        const AC = window.AudioContext || window.webkitAudioContext; const ac = new AC();
        const src = ac.createMediaStreamSource(st), an = ac.createAnalyser(); an.fftSize = 1024; src.connect(an);
        const buf = new Uint8Array(an.fftSize);
        return {read() { an.getByteTimeDomainData(buf); let m = 0; for (let i = 0; i < buf.length; i += 4) m = Math.max(m, Math.abs(buf[i] - 128)); return Math.min(1, m / 64); },
                close() { try { st.getTracks().forEach(t => t.stop()); ac.close(); } catch { /* already gone */ } }};
      } catch { return null; }
    }
    function draw() {
      raf = requestAnimationFrame(draw);
      if (!cv || !S) return;
      const live = S.meter ? S.meter.read() : (S.engine === 'flow' ? level : (synth = synth * .86 + (S.heard ? .35 + Math.random() * .45 : .04) * .14));
      LEVELS.push(Math.max(.06, live)); LEVELS.shift();
      const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return;
      if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
      const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
      g.fillStyle = getComputedStyle(cv).color;
      const step = 4, n = Math.floor(w / step), bw = 2;
      for (let i = 0; i < n; i++) {
        const v = LEVELS[Math.max(0, LEVELS.length - n + i)] ?? .06;
        const bh = Math.max(2, Math.min(h, v * h * 1.15));
        const x = i * step, y = (h - bh) / 2; g.globalAlpha = .35 + .65 * Math.min(1, v * 1.6);
        if (g.roundRect) { g.beginPath(); g.roundRect(x, y, bw, bh, 1); g.fill(); } else g.fillRect(x, y, bw, bh);
      }
      g.globalAlpha = 1;
    }
    function clock() { if (!S || !bar) return; const s = Math.floor((Date.now() - S.t0) / 1000); bar.querySelector('.dtime').textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }

    /* --- writing into the box: what was there before + finished phrases + the phrase still being heard */
    function write(text) {
      msg.value = text; S && (S.wrote = text); msg.dispatchEvent(new Event('input')); onWrite && onWrite();
    }
    const join = (a, b) => (a && b ? a.replace(/\s*$/, '') + ' ' + b.replace(/^\s*/, '') : (a || '') + (b || ''));

    /* --- the browser's own speech typing */
    function startSR() {
      const r = new SR(); r.lang = lang; r.interimResults = true; r.continuous = true; r.maxAlternatives = 1;
      S.rec = r; S.done = 0;
      r.onresult = ev => {
        if (!S || S.rec !== r) return;
        if (msg.value !== S.wrote) { end(false); return; }   // the box was cleared or changed by the page (a sent message, another chat)
        S.heard = true; S.quiet = 0; setState('Listening');
        let fin = '', mid = '';
        for (let i = Math.max(ev.resultIndex, S.done); i < ev.results.length; i++) {
          const t = ev.results[i][0].transcript;
          if (ev.results[i].isFinal) { fin = join(fin, t.trim()); S.done = i + 1; } else mid = join(mid, t.trim());
        }
        if (fin) S.base = join(S.base, fin);
        write(join(S.base, mid));
      };
      r.onspeechstart = () => { if (S) { S.heard = true; setState('Listening'); } };
      r.onspeechend = () => { if (S) S.heard = false; };
      r.onerror = ev => {
        if (!S || S.rec !== r) return;
        if (ev.error === 'no-speech') { S.quiet++; setState('Speak now - I did not hear anything yet'); return; }
        if (ev.error === 'aborted') return;
        S.fatal = ERR[ev.error] || `Speech typing stopped (${ev.error}). Try again.`;
      };
      r.onend = () => {
        if (!S || S.rec !== r) return;
        if (S.fatal) { const m = S.fatal; end(true); toast(m, true); return; }
        if (S.quiet >= 3) { end(true); toast('Dictation stopped - no speech heard. Tap the microphone when you are ready.'); return; }
        if (S.stopping) { end(true); return; }
        S.base = msg.value; S.wrote = msg.value;   // Chrome closed the session after a pause: carry on in a new one
        try { startSR(); } catch { end(true); }
      };
      r.start();
    }

    async function start() {
      if (S) return;
      if (flow && await flow.canUse?.()) {         // Hoola Flow first: her own server hears it
        S = {engine: 'flow', t0: Date.now(), orig: msg.value, wrote: msg.value};
        show(true); setState('Listening');
        try { await flow.start(msg.value); }
        catch (e) { S = null; show(false); toast(/denied|NotAllowed|Permission/i.test(String(e?.message)) ? ERR['not-allowed'] : (e.message || 'The microphone could not start.'), true); return; }
        loop(); return;
      }
      if (!SR) { toast('This browser cannot turn speech into text. Use Chrome, Edge or Safari - or tap the voice button to talk instead.', true); return; }
      S = {engine: 'sr', t0: Date.now(), orig: msg.value, base: msg.value, wrote: msg.value, quiet: 0, heard: false};
      show(true); setState('Starting the microphone');
      try { startSR(); } catch (e) { S = null; show(false); toast('The microphone could not start. Try again.', true); return; }
      setState('Listening');
      loop();
      meter().then(m => { if (S && S.engine === 'sr') S.meter = m; else m && m.close(); });
    }
    function loop() { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw); clearInterval(tick); tick = setInterval(clock, 250); clock(); }
    function end(keep) {   // keep = the words stay in the box
      const s = S; if (!s) return; S = null; clearTimeout(s.rt);
      cancelAnimationFrame(raf); clearInterval(tick); LEVELS.fill(0);
      try { s.rec && (keep ? s.rec.stop() : s.rec.abort()); } catch { /* already ended */ }
      s.meter && s.meter.close();
      show(false);
      if (!keep && msg.value === s.wrote) { msg.value = s.orig; msg.dispatchEvent(new Event('input')); }
    }
    async function finish() {
      if (!S) return;
      if (S.engine === 'flow') { const s = S; setState('Writing it down'); bar.classList.add('busy');
        try { await flow.stop(); } finally { bar.classList.remove('busy'); if (S === s) { S = null; cancelAnimationFrame(raf); clearInterval(tick); show(false); } }
        msg.focus(); return; }
      S.stopping = true; const s = S; end(true); s.rec = null;
      msg.focus(); try { msg.setSelectionRange(msg.value.length, msg.value.length); } catch { /* not focusable */ }
    }
    async function cancel() {
      if (!S) return;
      if (S.engine === 'flow') { const s = S; S = null; cancelAnimationFrame(raf); clearInterval(tick); show(false);
        try { await flow.cancel?.(); } catch { /* gone */ } msg.value = s.orig; msg.dispatchEvent(new Event('input')); msg.focus(); return; }
      end(false); msg.focus();
    }
    function langMenu(anchor) {
      const items = LANGS.map(([c, n]) => ({label: n, checked: c === lang, run: () => setLang(c)}));
      if (!LANGS.some(([c]) => c === lang)) items.unshift({label: label(lang), checked: true, run: () => {}});
      if (window.HoolaMenu) window.HoolaMenu.open(anchor, items, {align: 'end', place: 'above', label: 'Language you speak', width: 240, cls: 'dlangm'});
    }
    function setLang(c) {
      lang = c; try { localStorage.setItem(KEY, c); } catch { /* private window */ }
      paintLang();
      if (S && S.engine === 'sr' && S.rec) { const old = S.rec; S.base = msg.value; S.wrote = msg.value; S.rec = null; try { old.abort(); } catch {} try { startSR(); } catch { end(true); } }
    }

    button.addEventListener('click', () => { S ? finish() : start(); });
    msg.addEventListener('input', e => {             // her own typing while it listens: keep it, listen again after it
      if (!S || !e.isTrusted) return;
      S.base = msg.value; S.wrote = msg.value;
      if (S.engine !== 'sr') return;
      if (S.rec) { const r = S.rec; S.rec = null; try { r.abort(); } catch { /* ended */ } }
      clearTimeout(S.rt); setState('Paused while you type');
      S.rt = setTimeout(() => { if (S && !S.rec) { try { startSR(); setState('Listening'); } catch { end(true); } } }, 700);
    });
    composer.addEventListener('submit', () => { if (S) { if (S.engine === 'flow') { finish(); } else { S.stopping = true; end(true); } } }, true);
    document.addEventListener('keydown', e => {
      if (e.ctrlKey && e.code === 'Space' && (document.activeElement === msg || S)) { e.preventDefault(); S ? finish() : start(); return; }
      if (S && e.key === 'Escape' && !document.querySelector('.hmenu.on')) { e.preventDefault(); cancel(); }
    });

    return {get on() { return !!S; }, start, finish, cancel, stop: () => end(true), level: pushLevel,
            flowText: t => { if (S && S.engine === 'flow') write(t); }, get lang() { return lang; }, setLang};
  };
})();
