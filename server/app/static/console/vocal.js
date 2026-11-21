/* v0.999.90 HOOLA VOCAL, GLOBAL - Hoola's own ElevenLabs for every user in the world (owner, on the design canvas
   claude.ai/artifact/Uf3iF3gBt1q8qq57gZJcue: "GO BUILD ALL"; the contract is docs/HOOLA_VOCAL_GLOBAL.md). The home is the
   Vocal chat, like the Music page: she asks, Hoola makes takes in the chat, she keeps talking to change them. Every tool
   stays one tap away in the menu: Speech, Voices, Your voice, Dialogue, Studio, Dubbing, Voice changer, Clean-up, Sound
   effects, Dictionary, History, plus Languages and Settings. Everything stands on /api/vocal/*. An engine that is not
   set up is read from overview.engines and its controls are disabled WITH the reason beside them. Prices come from
   /quote before every paid job: credits plus her money. Her text is always esc()'d. No data-v attributes inside this
   overlay (the console's global [data-v] click handler would take them): data-a / data-val / data-p instead. */
window.HoolaVocal = function ({api, esc, toast, upload, back, go: consoleGo}) {
  const A = '/api/vocal';
  let ROOT = null, PAGE = 'chat', ARG = '', D = null, NOW = null, WN = 0, POP = null;
  const store = {get: (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window: kept for this visit only */ } }};
  // what she picked for speech: shared by the chat, Speech, Dialogue and the readings
  const S = {voice: '', lang: '', style: '', speed: 1, expressive: 0.5, takes: 2, engine: 'auto', format: 'wav', rules: true, text: '', out: []};
  const C = {conv: '', title: '', rows: [], items: [], turn: null, sending: false, working: false, loading: false, thread: null, files: [],
    lastSend: null, seq: 0, setOpen: false, ask: '', pend: '', side: '', fail: false};
  const UI = {slim: null, vf: {tab: 'Library', q: '', lang: '', accent: '', gender: '', age: '', engine: '', use: ''}, saved: store.get('hv.saved', []),
    kept: store.get('hv.kept', []), hist: 'All', langR: 'All', langQ: '', setTab: 'Engines and prices',
    clone: {sample: null, consent: null, name: 'My voice', ok: false, lang: ''}, cline: {}, design: {desc: '', gender: '', previews: [], pick: '', name: ''},
    remix: {base: '', change: '', name: ''},
    dlg: {mode: 'lines', lines: [{speaker: 'Maya', text: ''}, {speaker: 'Daniel', text: ''}], cast: [{name: 'Maya', voice: ''}, {name: 'Daniel', voice: ''}],
      lang: '', style: '', title: '', pod: {src: 'file', url: '', text: '', file: null, minutes: 5}},
    proj: null, cast: null, imp: {open: false, src: 'file', url: '', text: '', title: '', file: null},
    dubs: null, dub: null, dubTab: '', dubNew: {file: null, langs: [], mode: 'matched', keep: true, secs: 0},
    chg: {file: null, voice: '', denoise: true, secs: 0, out: null}, cl: {file: null, denoise: true, voice: true, silence: false, level: true, people: false, music: false, secs: 0, out: null, before: ''},
    fx: {prompt: '', seconds: 0, loop: false, takes: 4, out: []}, seed: 1};
  const PAGES = [['chat', 'Vocal chat', 'chat'], ['speech', 'Speech', 'wave'], ['voices', 'Voices', 'voices'], ['mine', 'Your voice', 'mic'],
    ['dialogue', 'Dialogue', 'dialogue'], ['studio', 'Studio', 'book'], ['dub', 'Dubbing', 'lang'], ['changer', 'Voice changer', 'swap'],
    ['cleanup', 'Clean-up', 'filter'], ['sfx', 'Sound effects', 'spark'], ['dict', 'Dictionary', 'abc'], ['history', 'History', 'clock']];
  const LOWER = [['langs', 'Languages', 'globe'], ['settings', 'Settings', 'gear']];
  const KIND = {tts: 'Speech', dialogue: 'Dialogue', chapter: 'Chapter', book: 'Reading', sfx: 'Effect', cleanup: 'Cleaned', change: 'Changed', dub: 'Dub', music: 'Music'};
  const FEEL = ['warm', 'whispers', 'laughs', 'sighs', 'excited', 'serious', 'slowly', 'cheerful'];
  const IDEAS = ['Shop welcome in Spanish', 'Bedtime story in Arabic', 'Product ad in Portuguese', 'Lesson in Japanese', 'Podcast intro, two hosts',
    'Dub my video into French', 'Rain on a tin roof', 'Read my PDF aloud'];
  const TILES = [['speech', 'Speech', 'Words in, a natural voice out, in any language', 'wave'], ['voices', 'Voices', 'Voices for every language and accent', 'voices'],
    ['mine', 'Your voice', 'Clone, design or remix a voice', 'mic'], ['dialogue', 'Dialogue', 'Several speakers, or a podcast from a file', 'dialogue'],
    ['studio', 'Studio', 'Audiobooks with a voice per character', 'book'], ['dub', 'Dubbing', 'Your video in another language', 'lang'],
    ['changer', 'Voice changer', 'Your recording in another voice', 'swap'], ['sfx', 'Sound effects', 'Describe any sound, get takes', 'spark']];
  const NAMES = {gemini: 'Gemini voice', eleven: 'ElevenLabs', lab: 'Hoola GPU lab', server: 'Hoola server'};
  const KEYS = {gemini: 'GEMINI_API_KEY', eleven: 'ELEVENLABS_API_KEY in the server settings', lab: 'the lab address and key', server: 'ffmpeg'};
  const QUAL = {excellent: 'Excellent', good: 'Good', fair: 'Fair', not_tested: 'Not tested yet', none: 'Not available'};
  const COLORS = ['#F6C7D6', '#C9E7DF', '#D7D2F2', '#FBE3B5', '#C9C1F0', '#E8D9C9', '#D6EBC9', '#FFD9A8', '#C7DDF6'];
  const PATHS = {
    chat: '<path d="M4 5h16v11H9l-5 4z"/>', wave: '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>',
    voices: '<circle cx="8" cy="8" r="4"/><path d="M2 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 4a4 4 0 0 1 0 8M22 20c0-2.6-1.6-4.8-4-5.6"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    dialogue: '<path d="M3 5h11v8H7l-4 3zM10 16h7l4 3v-9h-3"/>', book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
    lang: '<path d="M4 6h9M8.5 4v2M6 6c.6 3.6 3 6.4 6 7.6M11.5 6c-.7 3.8-3.4 6.8-7 8M13 20l4-9 4 9M14.4 17h5.2"/>',
    swap: '<path d="M4 8h14M14 4l4 4-4 4M20 16H6M10 12l-4 4 4 4"/>', filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    abc: '<path d="M4 17l3.5-10L11 17M5.3 13.5h4.4M14 7v10M20 13a2.5 2.5 0 1 0 0 4"/>', clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.6 5.4 3.6 8.5s-1.1 5.9-3.6 8.5c-2.5-2.6-3.6-5.4-3.6-8.5s1.1-5.9 3.6-8.5z"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', x: '<path d="M6 6l12 12M18 6L6 18"/>', back: '<path d="M15 18l-6-6 6-6"/>', play: '<path d="M8 5.5v13l11-6.5z"/>',
    down: '<path d="M12 5v14M6 13l6 6 6-6"/>', send: '<path d="M12 19V5M6 11l6-6 6 6"/>', wand: '<path d="M4 20L15 9M14 4v3M18 6h3M17 10l2 2M12 6l2-2"/>',
    sliders: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>', side: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.8-5.2 2.8 1-5.8-4.3-4.1 5.9-.9z"/>', redo: '<path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v4.5h-4.5"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', stop: '<rect x="7" y="7" width="10" height="10" rx="2"/>'};
  const ic = n => `<svg class="hi-i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[n] || ''}</svg>`;
  const $ = s => ROOT && ROOT.querySelector(s);
  const $$ = s => ROOT ? [...ROOT.querySelectorAll(s)] : [];
  const q = encodeURIComponent;
  const atOf = iso => { if (typeof iso === 'number') return iso > 1e12 ? iso / 1000 : iso; const t = Date.parse(iso || ''); return t ? t / 1000 : 0; };
  const ago = iso => { const t = atOf(iso) * 1000; if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const secs = s => { s = Math.round(+s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const num = n => (+n || 0).toLocaleString('en-US');
  const cr = n => num(n) + (+n === 1 ? ' credit' : ' credits');
  const usd = u => u == null ? '' : `≈ $${(+u < 0.1 ? (+u).toFixed(3) : (+u).toFixed(2))}`;
  const colorOf = id => COLORS[[...String(id || '')].reduce((n, ch) => (n * 31 + ch.charCodeAt(0)) >>> 0, 7) % COLORS.length];
  const strip = t => String(t || '').replace(/(?:\s*\[(?:Web console [^\]\n]*|Vocal settings:[^\]\n]*)\])+\s*$/, '');
  const head = (h, p, btn = '') => `<div class="hi-head"><div><h1>${h}</h1>${p ? `<p>${p}</p>` : ''}</div>${btn}</div>`;
  const warnNote = t => `<div class="hi-note warn">${esc(t)}</div>`;
  // a disabled control always says why, in a line beside it (aria-describedby points at that line)
  const gate = r => { if (!r) return {a: '', l: ''}; const id = `hvw${++WN}`; return {a: ` disabled aria-describedby="${id}"`, l: `<p class="hv-why" id="${id}">${esc(r)}</p>`}; };

  // ------------------------------------------------------------------ data ---
  const yn = v => v === true ? 'yes' : (v === false || v == null || v === '') ? 'none' : String(v).toLowerCase();
  function fix(o, L) {
    const d = {voices: [], rules: [], history: [], projects: [], usage: {}, limits: {}, sfx: [], styles: {}, feelings: [], engines: [], prices: [], ...o};
    d.status = {engines: {}, connected: {}, ...(o.status || {})};
    d.langs = L.map(l => ({region: '', voices: 0, quality: 'not_tested', native: l.name, ...l, speech: yn(l.speech), clone: yn(l.clone), dialogue: yn(l.dialogue), dub: yn(l.dub)}));
    d.voices = (d.voices || []).map(v => ({gender: '', age: '', tone: '', accent: '', langs: [], use: '', engine: 'gemini', tier: 'standard', kind: 'hoola', ready: true, ...v}));
    if (!d.feelings || !d.feelings.length) d.feelings = FEEL;
    return d;
  }
  const eng = id => (D.engines || []).find(e => e.id === id);
  const ready = id => eng(id)?.state === 'ready';
  function whyNot(id) {
    const e = eng(id), n = e?.name || NAMES[id] || id;
    if (!e) return `${n} is not on this server.`;
    if (e.state === 'needs_key') return `${n} is not connected: the server needs ${KEYS[id] || 'its key'}.`;
    if (e.state === 'off') return `${n} is switched off on this server.`;
    return '';
  }
  const lang = c => D.langs.find(l => l.code === c);
  const langLabel = c => { if (!c || c === 'auto') return 'Auto · from your words'; const l = lang(c); if (!l) return c; return l.native && l.native !== l.name ? `${l.native} · ${l.name}` : l.name; };
  const short = c => !c || c === 'auto' ? 'Auto' : (lang(c)?.native || lang(c)?.name || c);
  const voice = id => D.voices.find(v => v.id === id);
  const vname = id => voice(id)?.name || 'Hoola Auto';
  const styleName = id => (D.styles || {})[id] || 'Natural';
  function browserLang() {
    for (const x of (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''])) {
      const lo = String(x || '').toLowerCase(), l = D.langs.find(l => l.code.toLowerCase() === lo) || D.langs.find(l => l.code.toLowerCase() === lo.split('-')[0]);
      if (l && l.speech !== 'none') return l.code;
    }
    return 'auto';
  }
  // why speech cannot be made in this language on this engine (empty = it can)
  function speakWhy(lc, engine) {
    if (!ready('gemini') && !ready('eleven')) return 'No speech engine is set up on this server yet.';
    if (engine === 'eleven' && !ready('eleven')) return whyNot('eleven');
    if (engine === 'gemini' && !ready('gemini')) return whyNot('gemini');
    const l = lang(lc);
    if (l && l.speech === 'none') return `No engine speaks ${l.name} yet. Hoola never reads it in another language instead.`;
    if (l && l.speech === 'premium' && !ready('eleven')) return `${l.name} is spoken only by the premium engine. ${whyNot('eleven')}`;
    if (l && l.speech === 'premium' && engine === 'gemini') return `${l.name} is spoken only by the premium engine. Choose Hoola Auto or ElevenLabs.`;
    return '';
  }

  async function blobUrl(path) { if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const u = URL.createObjectURL(await r.blob()); URLS.set(path, u); return u; }
  const URLS = new Map();
  async function load() {
    try { const o = await api('GET', `${A}/overview`) || {}; D = fix(o, Array.isArray(o.langs) ? o.langs : Object.entries(o.langs || {}).map(([code, name]) => ({code, name}))); }
    catch (e) { D = fix({error: e.message}, []); }
    if (!S.voice || !D.voices.some(v => v.id === S.voice && v.ready)) S.voice = (D.voices.find(v => v.ready) || {}).id || '';
    if (!S.lang) S.lang = browserLang();
    if (!S.style || !(S.style in (D.styles || {}))) S.style = Object.keys(D.styles || {})[0] || '';
    if (!UI.dlg.lang) UI.dlg.lang = S.lang;
    if (!UI.clone.lang) UI.clone.lang = S.lang === 'auto' ? 'en' : S.lang;
    const rv = D.voices.filter(v => v.ready);
    UI.dlg.cast.forEach((c, i) => { if (!c.voice || !voice(c.voice)) c.voice = (rv[i % Math.max(1, rv.length)] || {}).id || ''; });
    if (!UI.remix.base) UI.remix.base = S.voice;
  }
  // a price before every paid job: /quote, cached by its body
  const QC = new Map(), QT = {};
  async function quote(body) {
    const k = JSON.stringify(body); if (QC.has(k)) return QC.get(k);
    try { const r = await api('POST', `${A}/quote`, body); QC.set(k, r); return r; } catch (e) { return {credits: null, line: e.message}; }
  }
  function price(key, body) {
    clearTimeout(QT[key]);
    QT[key] = setTimeout(async () => {
      const r = await quote(body), btn = $(`[data-qbtn="${key}"]`), line = $(`[data-qline="${key}"]`);
      if (btn) { const base = btn.dataset.label || ''; btn.innerHTML = `${btn.dataset.icon ? ic(btn.dataset.icon) : ''}${esc(base)}${r.credits != null && base !== 'Stop' ? ` · ${cr(r.credits)}` : ''}`; }
      if (line) line.innerHTML = r.credits != null
        ? `<b>${cr(r.credits)}</b> ${esc(usd(r.usd))}${r.engine_name ? ' · ' + esc(r.engine_name) : ''} · nothing is spent until you tap` : esc(r.line || '');
      const en = $(`[data-qeng="${key}"]`); if (en && r.engine_name) en.textContent = `Hoola Auto → ${r.engine_name}`;
    }, 260);
  }
  const ttsQuote = (text) => ({job: 'tts', chars: (text || '').length, takes: S.takes, voice: S.voice, lang: S.lang || 'auto', engine: S.engine});

  async function play(id, src, title, fmt) {
    try { const u = src || await blobUrl(`${A}/audio?id=${q(id)}${fmt ? '&format=' + q(fmt) : ''}`); const h = D.history.find(x => x.id === id);
      NOW = {id, title: title || h?.title || 'Sound'}; const bar = $('#hvBar'); bar.hidden = false;
      $('#hvNow').textContent = NOW.title; const a = $('#hvAudio'); a.src = u; await a.play().catch(() => {}); }
    catch (e) { toast(e.message || 'That sound could not be played.', true); }
  }
  async function download(id, fmt) { const h = D.history.find(x => x.id === id) || C.items.find(x => x.id === id) || S.out.find(x => x.id === id);
    try { const a = document.createElement('a'); a.href = await blobUrl(`${A}/audio?id=${q(id)}&format=${q(fmt || h?.ext || 'wav')}`);
      a.download = `${(h?.title || 'hoola-vocal').replace(/[^\w .-]+/g, '_').slice(0, 60)}.${fmt || h?.ext || 'wav'}`; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); } }
  async function fileSecs(file) {           // how long a picked recording is, read by the browser (0 when it cannot tell)
    return new Promise(res => { try { const u = URL.createObjectURL(file), m = document.createElement(file.type.startsWith('video') ? 'video' : 'audio');
      m.preload = 'metadata'; m.onloadedmetadata = () => { res(isFinite(m.duration) ? m.duration : 0); URL.revokeObjectURL(u); }; m.onerror = () => res(0); m.src = u; setTimeout(() => res(0), 4000); } catch { res(0); } });
  }
  async function up(file) { const r = await upload(file); const id = r?.file_id || r?.id; if (!id) throw new Error('The file did not upload.'); return id; }

  // ------------------------------------------------------------------ shell ---
  function mount() {
    if (ROOT) { ROOT.hidden = false; return; }
    ROOT = document.createElement('div'); ROOT.id = 'hvRoot';
    ROOT.setAttribute('role', 'application'); ROOT.setAttribute('aria-label', 'Hoola Vocal');
    ROOT.innerHTML = `<nav class="hv-rail" id="hvRail" aria-label="Hoola Vocal pages"></nav>
      <div class="hi-main hv-main"><main class="hi-view" id="hvView"></main>
        <div class="hv-bar" id="hvBar" hidden><span class="hv-dot s" style="--c:var(--pri-soft)">${ic('wave')}</span><b id="hvNow" class="hi-fill"></b><audio id="hvAudio" controls preload="none"></audio>
          <button class="hi-ib" data-a="closebar" aria-label="Close the player">${ic('x')}</button></div></div>`;
    document.body.appendChild(ROOT);
    ROOT.addEventListener('click', onClick); ROOT.addEventListener('input', onInput);
    ROOT.addEventListener('change', onChange); ROOT.addEventListener('submit', onSubmit);
    ROOT.addEventListener('keydown', onKey);
    ROOT.addEventListener('pointerdown', e => { if (POP && !e.target.closest('.hv-pop, [data-popfrom]')) popClose(); });
  }
  async function open() { mount(); await load(); go(PAGE, ARG); }
  function leave() { if (ROOT) { $('#hvAudio')?.pause(); popClose(); ROOT.hidden = true; } clearTimeout(chatPoll.t); clearTimeout(dubPoll.t); }
  function credit() {
    const u = D.usage || {}, sp = (D.prices || []).find(p => p.job === 'tts' || /speech/i.test(p.job || ''));
    const left = u.credits_left ?? u.credits;
    return `<div class="hv-credit"><span>Credits</span><b>${left != null ? `${num(left)} left` : `${num(u.credits_used || 0)} used this month`}</b>
      <span>${sp ? `1 minute of speech ≈ ${cr(sp.credits)}` : 'The price shows before every job'}</span></div>`;
  }
  function rail() {
    const on = {reading: 'studio'}[PAGE] || PAGE, slim = UI.slim ?? false;
    ROOT.dataset.slim = slim ? 1 : 0;
    const nb = ([id, n, i]) => `<button class="hv-nv" data-a="go" data-p="${id}" title="${n}"${id === on ? ' aria-current="page"' : ''}>${ic(i)}<span>${n}</span></button>`;
    $('#hvRail').innerHTML = `<div class="hv-brand"><button class="hv-mark" data-a="go" data-p="chat" aria-label="Hoola Vocal home" title="Hoola Vocal home"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M12 12 19 5"/></svg></button>
        <span class="hv-bt"><b>Hoola Vocal</b><small>Every voice, every language</small></span>
        <button class="hi-ib hv-fold" data-a="slim" aria-label="${slim ? 'Open' : 'Fold'} the sidebar" title="${slim ? 'Open' : 'Fold'} the sidebar">${ic('side')}</button></div>`
      + PAGES.map(nb).join('') + '<hr>' + LOWER.map(nb).join('') + `<span class="hv-grow"></span>${credit()}
      <button class="hv-nv quiet" data-a="back" title="Back to Hoola">${ic('back')}<span>Back to Hoola</span></button>`;
  }
  function go(page, arg) { popClose(); PAGE = V[page] ? page : 'chat'; ARG = arg || ''; rail(); draw(); const v = $('#hvView'); if (v) { v.scrollTop = 0; v.classList.remove('hi-in'); void v.offsetWidth; v.classList.add('hi-in'); clearTimeout(go.t); go.t = setTimeout(() => v.classList.remove('hi-in'), 900); }
    ENTER[PAGE]?.(); }
  function draw() { WN = 0; $('#hvView').innerHTML = V[PAGE](); AFTER[PAGE]?.(); }
  async function act(fn, done, btn, txt) {
    const was = btn?.innerHTML; if (btn) { btn.disabled = true; if (txt) btn.textContent = txt; }
    try { const r = await fn(); await load(); if (done) done(r); else { rail(); draw(); } }
    catch (e) { toast(e.message || 'That did not work.', true); if (btn?.isConnected) { btn.disabled = false; btn.innerHTML = was; } }
  }
  // a model binding: <input data-m="S.speed" data-t="num"> keeps the page state as she types, so a redraw keeps her words
  const MODELS = {S, UI, C};
  function setM(path, v) { const p = path.split('.'); let o = MODELS[p.shift()]; while (p.length > 1) { const k = p.shift(); o = o[k]; if (o == null) return; } o[p[0]] = v; }

  // ------------------------------------------------------------------ pieces ---
  function popOpen(anchor, o) {
    popClose(); const items = o.items || [];
    const el = document.createElement('div'); el.className = 'hv-pop'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', o.title);
    el.innerHTML = `<div class="hv-pophd"><b>${esc(o.title)}</b><button type="button" class="hi-ib" data-a="popx" aria-label="Close">${ic('x')}</button></div>
      ${o.search === false ? '' : `<label class="hv-sr" for="hvPopQ">Search</label><input type="search" id="hvPopQ" placeholder="${esc(o.ph || 'Search')}" autocomplete="off">`}<div class="hv-poplist" role="listbox" aria-label="${esc(o.title)}"></div>`;
    ROOT.appendChild(el); POP = {el, items, o, anchor}; anchor.setAttribute('data-popfrom', '1');
    popList('');
    const r = anchor.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight;
    el.style.left = `${Math.max(12, Math.min(r.left, innerWidth - w - 12))}px`;
    el.style.top = `${r.bottom + h + 8 < innerHeight ? r.bottom + 6 : Math.max(12, r.top - h - 6)}px`;
    (el.querySelector('#hvPopQ') || el.querySelector('.hv-poplist button:not(:disabled)'))?.focus();
  }
  function popList(qs) {
    if (!POP) return; const lo = qs.trim().toLowerCase();
    const list = POP.items.filter(it => !lo || [it.label, it.sub, it.key].join(' ').toLowerCase().includes(lo)).slice(0, 300);
    POP.el.querySelector('.hv-poplist').innerHTML = list.map(it => `<button type="button" role="option" data-a="popv" data-val="${esc(it.v)}" aria-selected="${it.v === POP.o.cur}"${it.why ? ' disabled' : ''}>
      <span>${esc(it.label)}</span>${it.why ? `<small>${esc(it.why)}</small>` : it.sub ? `<small>${esc(it.sub)}</small>` : ''}</button>`).join('') || '<p class="hv-line" style="padding:8px 10px">Nothing matches.</p>';
  }
  function popClose() { if (!POP) return; POP.anchor?.removeAttribute('data-popfrom'); POP.el.remove(); const a = POP.anchor; POP = null; if (a?.isConnected) a.focus({preventScroll: true}); }
  const langItems = (auto, need) => [...(auto ? [{v: 'auto', label: 'Auto · from your words', sub: 'Hoola hears the language of your words'}] : []),
    ...D.langs.map(l => ({v: l.code, key: l.code + ' ' + (l.region || ''), label: l.native && l.native !== l.name ? `${l.native} · ${l.name}` : l.name,
      sub: [l.region, l[need || 'speech'] === 'premium' ? 'Premium engine' : '', l.voices ? `${l.voices} voices` : ''].filter(Boolean).join(' · '),
      why: l[need || 'speech'] === 'none' ? 'No engine yet' : (l[need || 'speech'] === 'premium' && !ready('eleven') ? 'Needs the premium engine, not connected' : '')}))];
  const voiceItems = (filt) => D.voices.filter(filt || (() => true)).map(v => ({v: v.id, label: v.name, key: (v.langs || []).join(' ') + ' ' + (v.use || ''),
    sub: [v.tone, (v.langs || []).map(c => lang(c)?.native || c).slice(0, 3).join(', '), v.tier === 'premium' ? 'Premium' : 'Standard'].filter(Boolean).join(' · '),
    why: v.ready ? '' : (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'Not ready yet')}));
  const seg = (path, list, cur, gateOf) => `<div class="hv-seg" role="radiogroup">${list.map(([v, label]) => { const g = gate(gateOf ? gateOf(v) : '');
    return `<button type="button" role="radio" aria-checked="${String(v) === String(cur)}" data-a="seg" data-m="${path}" data-val="${esc(String(v))}"${g.a}>${esc(label)}</button>${g.l}`; }).join('')}</div>`;
  const engSeg = (path, cur) => seg(path, [['auto', 'Hoola Auto'], ['gemini', 'Gemini voice'], ['eleven', 'ElevenLabs, premium']], cur, v => v === 'auto' ? '' : (ready(v) ? '' : whyNot(v)));
  const wave = id => { let h = [...String(id || 'x')].reduce((n, ch) => (n * 33 + ch.charCodeAt(0)) >>> 0, 5); const out = [];
    for (let i = 0; i < 34; i++) { h = (h * 1103515245 + 12345) >>> 0; out.push(6 + (h % 20)); } return `<span class="hv-wave" aria-hidden="true">${out.map(n => `<i style="height:${n}px"></i>`).join('')}</span>`; };
  const kept = id => UI.kept.includes(id);
  function takeCard(it, i) {
    const L = it.take || String.fromCharCode(65 + i), on = kept(it.id);
    return `<div class="hv-take${on ? ' on' : ''}"><button type="button" class="hv-play" data-a="play" data-id="${esc(it.id)}" aria-label="Play take ${esc(L)}">${ic('play')}</button>
      <span class="hi-fill"><b>Take ${esc(L)}</b> <span class="hi-sm hi-mut">${it.seconds ? secs(it.seconds) + ' · ' : ''}${esc([it.voice_name, it.lang ? short(it.lang) : ''].filter(Boolean).join(' · '))}</span></span>${wave(it.id)}
      <button type="button" class="hi-btn q s" data-a="keep" data-id="${esc(it.id)}" aria-pressed="${on}">${on ? `${ic('check')}Kept` : 'Keep this'}</button>
      <button type="button" class="hi-btn q s" data-a="dlmenu" data-id="${esc(it.id)}">${ic('down')}Download</button></div>`;
  }
  const sndRow = h => `<div class="hv-snd"><button type="button" class="hv-play" data-a="play" data-id="${esc(h.id)}" aria-label="Play ${esc(h.title || KIND[h.kind] || 'sound')}">${ic('play')}</button>
    <span class="hi-fill"><b>${esc(h.title || KIND[h.kind] || 'Sound')}</b><small>${esc([h.lang ? short(h.lang) : '', h.voice_name, h.seconds ? secs(h.seconds) : '', ago(h.made)].filter(Boolean).join(' · '))}</small></span>
    <span class="hv-chip">${esc(KIND[h.kind] || h.kind || 'Sound')}</span></div>`;
  const histRow = h => `<div class="hv-row"><button class="hv-play" data-a="play" data-id="${esc(h.id)}" aria-label="Play ${esc(h.title || 'sound')}">${ic('play')}</button>
      <span class="hi-fill"><b>${esc(h.title || KIND[h.kind] || 'Sound')}</b><br><span class="hi-sm hi-mut">${esc([h.voice_name, h.lang ? langLabel(h.lang) : '', h.engine ? (NAMES[h.engine] || h.engine) : '', h.seconds ? secs(h.seconds) : '', h.credits != null ? cr(h.credits) : '', ago(h.made)].filter(Boolean).join(' · '))}</span></span>
      <span class="hi-chip">${esc(KIND[h.kind] || h.kind || '')}</span><button class="hi-btn q s" data-a="dlmenu" data-id="${esc(h.id)}">${ic('down')}Download</button>
      <button class="hi-ib" data-a="rmh" data-id="${esc(h.id)}" aria-label="Remove ${esc(h.title || 'this sound')}" title="Remove">${ic('x')}</button></div>`;

  // ------------------------------------------------------------------ the Vocal chat ---
  const chatMode = () => C.sending || !!C.pend || C.rows.some(r => r.role === 'user');
  const summary = () => `${S.lang === 'auto' ? 'Auto language' : short(S.lang)} · ${vname(S.voice)} · ${styleName(S.style)} · ${+(+S.speed).toFixed(2)}x · ${S.takes} take${S.takes > 1 ? 's' : ''}`;
  const settingsNote = () => `[Vocal settings: language ${S.lang || 'auto'}; voice ${S.voice || 'auto'}; style ${S.style || 'auto'}; speed ${+(+S.speed).toFixed(2)}; takes ${S.takes}; engine ${S.engine}]`;
  function setPanel() {
    const l = speakWhy(S.lang, S.engine);
    return `<div class="hv-sethd" style="justify-content:space-between"><b id="hvSetT" style="color:var(--ink);font-size:14px">Vocal settings</b><button type="button" class="hi-link" data-a="setreset">Reset</button></div>
      <div class="hv-setr"><span class="lab">Language</span><div><button type="button" class="hv-pick" data-a="picklang" data-k="S.lang" data-auto="1">${ic('lang')}<span>${esc(langLabel(S.lang))}</span></button></div></div>
      <div class="hv-setr"><span class="lab">Voice</span><div><button type="button" class="hv-pick" data-a="pickvoice" data-k="S.voice">${ic('voices')}<span>${esc(vname(S.voice))}</span></button></div></div>
      ${Object.keys(D.styles || {}).length ? `<div class="hv-setr"><span class="lab">Style</span>${seg('S.style', Object.entries(D.styles), S.style)}</div>` : ''}
      <div class="hv-setr"><span class="lab">Speed</span><div class="hv-field"><input type="range" min="0.7" max="1.3" step="0.05" value="${S.speed}" data-m="S.speed" data-t="num" aria-label="Speed"><span class="hv-sub" data-show="S.speed">${(+S.speed).toFixed(2)}x</span></div></div>
      <div class="hv-setr"><span class="lab">Takes</span>${seg('S.takes', [[1, '1'], [2, '2'], [3, '3']], S.takes)}</div>
      <div class="hv-setr"><span class="lab">Engine</span><div>${engSeg('S.engine', S.engine)}</div></div>
      ${l ? `<p class="hv-why">${esc(l)}</p>` : ''}
      <div class="hv-sethd" style="justify-content:flex-end"><button type="button" class="hv-pill s" data-a="setdone">Done</button></div>`;
  }
  function composer() {
    const w = speakWhy(S.lang, S.engine), g = gate(w);
    return `<div class="hv-comp"><div class="hv-setp" id="hvSetp" role="dialog" aria-labelledby="hvSetT"${C.setOpen ? '' : ' hidden'}>${C.setOpen ? setPanel() : ''}</div>
      <form class="hv-box" data-f="chat"><div class="hv-tray" id="hvTray" role="list" aria-label="Files to send"${C.files.length ? '' : ' hidden'}>${trayHTML()}</div>
        <label for="hvAsk">Tell Hoola what to say, or paste the words</label>
        <textarea id="hvAsk" rows="3" maxlength="4000" data-m="C.ask" placeholder="Read this welcome for my bakery in Swahili, a warm woman's voice, a little slow…">${esc(C.ask)}</textarea>
        <div class="hv-boxrow"><button type="button" class="hv-ic" data-a="plus" aria-label="Add a file" title="Add a file">${ic('plus')}</button>
          <button type="button" class="hv-setpill" data-a="setopen" aria-expanded="${C.setOpen}" aria-controls="hvSetp">${ic('sliders')}<span id="hvSum">${esc(summary())}</span></button>
          <span class="hi-fill"></span><button type="button" class="hi-btn q s" data-a="improve">${ic('wand')}Improve</button>
          <button class="hv-pill" data-qbtn="chat" data-label="${C.working && !C.sending ? 'Stop' : 'Speak it'}" data-icon="${C.working && !C.sending ? 'stop' : 'send'}"${g.a}>${ic(C.working && !C.sending ? 'stop' : 'send')}${C.working && !C.sending ? 'Stop' : 'Speak it'}</button></div></form>
      ${g.l}<p class="hv-line" data-qline="chat">${esc(S.takes)} take${S.takes > 1 ? 's' : ''} by Hoola Auto · nothing is spent until you press Speak it</p></div>`;
  }
  const trayHTML = () => C.files.map((f, i) => `<span class="hv-file" role="listitem"><span>${esc(f.name)}</span>${f.up ? '<small class="hi-mut">Uploading…</small>' : f.err ? `<small class="hv-why">${esc(f.err)}</small>` : ''}
    <button type="button" class="hi-ib" data-a="fx" data-n="${i}" aria-label="Remove ${esc(f.name)}">${ic('x')}</button></span>`).join('');
  function sideHTML() {
    const lo = C.side.toLowerCase(), list = D.history.filter(h => !lo || [h.title, h.voice_name, h.kind, h.lang].join(' ').toLowerCase().includes(lo)).slice(0, 30);
    return `<aside class="hv-side" aria-label="Your sounds"><h2>Your sounds</h2><label class="hv-sr" for="hvSq">Search your sounds</label>
      <input id="hvSq" class="hv-in" type="search" placeholder="Search" value="${esc(C.side)}" data-m="C.side">
      <div id="hvSide">${list.map(sndRow).join('') || '<p class="hv-line">Nothing yet. What you make appears here.</p>'}</div>
      <button type="button" class="hi-link" data-a="go" data-p="history">See all of History</button></aside>`;
  }
  function chatView() {
    if (!chatMode()) return `<div class="hv-home"><section class="hv-cmain"><h1 class="hv-h1">What should Hoola say?</h1>
        <p class="hv-lead">Speech, a dialogue, an audiobook, a dub or a sound, in any of ${D.langs.length ? num(D.langs.length) : 'many'} languages. Just ask, then keep talking to change it.</p>
        ${D.error ? warnNote('Hoola Vocal could not load: ' + D.error) : ''}${composer()}
        <div class="hv-grid" style="display:grid;gap:10px"><span class="hi-sm hi-mut">Start from an idea</span><div class="hv-chips">${IDEAS.map(i => `<button type="button" data-a="idea" data-val="${esc(i)}">${esc(i)}</button>`).join('')}</div></div>
        <div class="hv-tiles">${TILES.map(([p, n, l, i]) => `<button type="button" class="hv-tile" data-a="go" data-p="${p}"><span class="ic">${ic(i)}</span><b>${n}</b><span>${l}</span></button>`).join('')}</div>
      </section>${sideHTML()}</div>`;
    return `<div class="hv-home"><section class="hv-cmain"><div class="hv-chathd"><h1 id="hvCTitle">${esc(C.title || 'Vocal chat')}</h1>
        <button type="button" class="hi-btn q s" data-a="chats">${ic('redo')}Earlier chats</button><button type="button" class="hi-btn q s" data-a="newchat">${ic('plus')}New chat</button></div>
        <div class="hv-log" id="hvLog"><div id="hvThread"></div><div id="hvFail"></div></div>${composer()}</section>${sideHTML()}</div>`;
  }
  // the takes of one ask, kept together and placed after the reply of the turn that made them
  function sets() {
    const m = new Map();
    for (const it of C.items) { const k = it.job || it.id, s = m.get(k) || {id: k, at: Infinity, items: []}; s.items.push(it); s.at = Math.min(s.at, atOf(it.made) || 0); m.set(k, s); }
    m.forEach(s => s.items.sort((a, b) => String(a.take || '').localeCompare(String(b.take || '')) || atOf(a.made) - atOf(b.made)));
    return [...m.values()].sort((a, b) => a.at - b.at);
  }
  function setCard(s) {
    const f = s.items[0] || {}, credits = s.items.reduce((n, x) => n + (+x.credits || 0), 0), t = f.title || 'this sound';
    return `<div class="hv-set"><div class="hv-sethd"><span class="hv-chip ok">Ready</span><span>${s.items.length} take${s.items.length > 1 ? 's' : ''}${f.voice_name ? ' · ' + esc(f.voice_name) : ''}${f.lang ? ' · ' + esc(short(f.lang)) : ''}${credits ? ' · ' + cr(credits) : ''}</span></div>
      <div class="hv-takes">${s.items.map(takeCard).join('')}</div>
      <div class="hv-chips">${[['Slower', `Make "${t}" a little slower`], ['Warmer', `Make "${t}" warmer`], ['Another voice', `Read "${t}" again in another voice`]]
        .map(([l, ask]) => `<button type="button" data-a="ask" data-val="${esc(ask)}">${l}</button>`).join('')}</div></div>`;
  }
  function threadList() {
    const msgs = C.rows.filter(r => r.role === 'user' || r.role === 'assistant').map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? strip(r.text) : String(r.text || ''), at: atOf(r.at || r.created_at)}));
    const after = new Map();
    for (const s of sets()) { let i = -1; msgs.forEach((m, j) => { if (m.at <= s.at + 1) i = j; });
      if (i >= 0 && msgs[i].role === 'her' && msgs[i + 1]?.role === 'hoola') i++;
      (after.get(i) || after.set(i, []).get(i)).push(s); }
    const raw = s => ({id: 'vset:' + s.id, role: 'raw', html: `<div data-vset="${esc(s.id)}"></div>`});
    const out = [...(after.get(-1) || []).map(raw)];
    msgs.forEach((m, j) => { out.push(m); (after.get(j) || []).forEach(s => out.push(raw(s))); });
    return out;
  }
  function plainThread(host) {             // used only when the shared chat kit is not on the page
    let K = '';
    return {her(text, o) { const d = document.createElement('div'); d.className = 'hv-me hck-bub'; d.textContent = text; if (o?.pending) d.dataset.pending = '1'; host.append(d); },
      clear() { host.innerHTML = ''; K = ''; },
      sync(st) { const h = st.messages.map(m => m.role === 'raw' ? m.html : m.role === 'her' ? `<div class="hv-me hck-bub">${esc(m.text)}</div>` : `<div class="hv-ho">${esc(m.text)}</div>`).join('')
        + (st.working ? `<p class="hv-line">${esc(st.label)}</p>` : ''); if (h !== K) { host.innerHTML = h; K = h; } }};
  }
  function drawSets() {
    const m = new Map(sets().map(s => [String(s.id), s]));
    $$('[data-vset]').forEach(n => { const s = m.get(n.dataset.vset); if (!s) return; const h = setCard(s); if (n._h === h) return; n._h = h; n.innerHTML = h; });
  }
  function paintChat(quiet) {         // quiet: draw what is there without a working row (her new bubble goes in first)
    if (PAGE !== 'chat' || !C.thread) return;
    const st = C.turn ? String(C.turn.status || '') : '', last = C.rows[C.rows.length - 1];
    const working = !quiet && (C.sending || (st ? st === 'working' || st === 'queued' : !!last && last.role === 'user'));
    const was = C.working; C.working = working;
    C.thread.sync({key: C.conv, working, label: (C.turn && working && C.turn.line) ? String(C.turn.line) : 'Hoola is listening to your words…', steps: [], messages: threadList()});
    drawSets();
    const mine = sets().some(s => s.at >= (C.lastSend?.at || 0) - 1);
    const bad = !working && !!st && /fail|error|stuck/.test(st) && !mine && !!C.lastSend;
    const f = $('#hvFail');
    if (f) { const g = gate(speakWhy(C.lastSend?.lang || S.lang, C.lastSend?.engine || S.engine));
      f.innerHTML = bad ? `<div class="hv-fail"><b>Hoola could not answer this time.</b><span class="hi-sm hi-mut">You can still make it now from your words and settings.</span>
      <div><button type="button" class="hv-pill s" data-a="direct"${g.a}>${ic('play')}Make it now</button>${g.l}</div></div>` : ''; }
    if (was !== working) { const b = $('[data-qbtn="chat"]'); if (b) { const s = working && !C.sending; b.dataset.label = s ? 'Stop' : 'Speak it'; b.dataset.icon = s ? 'stop' : 'send'; b.innerHTML = `${ic(b.dataset.icon)}${b.dataset.label}`; } }
  }
  async function openChat(id) {
    try {
      if (id) { await api('GET', `${A}/chat/${q(id)}/ok`); }
      const c = id ? {id} : await api('GET', `${A}/chat`);
      C.conv = c.id; C.rows = []; C.items = []; C.turn = null; C.lastSend = null; if (c.title) C.title = c.title;
      C.thread?.clear?.(); await chatLoad(true);
      if (PAGE === 'chat') { draw(); }
    } catch (e) { toast(`The Vocal chat could not open: ${e.message}`, true); }
  }
  async function chatLoad(first) {
    if (!C.conv || C.loading) return; const conv = C.conv; C.loading = true;
    try {
      const last = C.rows[C.rows.length - 1];
      if (C.sending || C.working || first || (last && last.role === 'user')) { try { C.turn = await api('GET', `/api/conversations/${q(conv)}/result`); } catch { /* no turn yet */ } }
      let rows; try { rows = (await api('GET', `/api/conversations/${q(conv)}/messages?limit=200`)).messages || []; } catch { return; }
      let items = C.items; try { items = (await api('GET', `${A}/chat/${q(conv)}/items`)).items || []; } catch { /* the sounds come next time */ }
      if (conv !== C.conv) return;
      const wasMode = chatMode(); C.rows = rows; C.items = items; if (rows.some(r => r.role === 'user')) C.pend = '';
      if (first) return;
      if (PAGE === 'chat') { if (wasMode !== chatMode()) draw(); else paintChat(); }
    } finally { C.loading = false; }
  }
  function chatPoll() {
    clearTimeout(chatPoll.t);
    const tick = async () => { if (PAGE !== 'chat' || !ROOT || ROOT.hidden) return; await chatLoad(false); chatPoll.t = setTimeout(tick, C.working ? 2000 : 8000); };
    chatPoll.t = setTimeout(tick, C.working || C.sending ? 1500 : 8000);
  }
  async function chatSend(textIn) {
    const ta = $('#hvAsk'), text = String(textIn ?? C.ask ?? '').trim();
    if (C.working && !C.sending && !textIn && !text) { try { await api('POST', `/api/conversations/${q(C.conv)}/stop`); toast('Stopping.'); } catch (e) { toast(e.message, true); } return; }
    if (!text) { ta?.focus(); toast('Tell Hoola what to say first.'); return; }
    if (C.files.some(f => f.up)) { toast('Wait for the files to finish uploading.'); return; }
    if (!C.conv) await openChat();
    if (!C.conv) return;
    const files = C.files.filter(f => f.file_id), first = !chatMode();
    C.sending = true; C.turn = null; C.setOpen = false;
    C.lastSend = {text, at: Date.now() / 1000, voice: S.voice, lang: S.lang, style: S.style, speed: S.speed, takes: S.takes, engine: S.engine, format: S.format, expressive: S.expressive, rules: S.rules};
    if (!textIn) C.ask = ''; C.files = []; C.pend = text;
    if (first || PAGE !== 'chat') draw(); else { if (ta) ta.value = ''; const t = $('#hvTray'); if (t) { t.innerHTML = ''; t.hidden = true; } }
    C.thread?.her(text, {pending: true, files: files.map(f => f.name)});
    paintChat();
    try {
      await api('POST', `/api/conversations/${q(C.conv)}/messages`, {text: `${text}\n\n${settingsNote()}`, files: files.map(f => f.file_id),
        client_id: 'vo' + Date.now().toString(36) + (++C.seq).toString(36)});
      C.turn = {status: 'queued', line: ''};
    } catch (e) { toast(e.message, true); if (!textIn) C.ask = text; C.files = files; C.pend = ''; }
    C.sending = false; await chatLoad(false); paintChat(); chatPoll();
  }
  async function chatFiles(list) {
    const fs = [...list].slice(0, Math.max(0, 10 - C.files.length));
    if (!C.conv) await openChat(); if (!C.conv) return;
    const tray = () => { const t = $('#hvTray'); if (t) { t.innerHTML = trayHTML(); t.hidden = !C.files.length; } };
    for (const file of fs) {
      const f = {name: file.name || 'file', up: true}; C.files.push(f); tray();
      if (file.size > 30 * 1024 * 1024) { f.up = false; f.err = 'Over 30 MB'; tray(); continue; }
      try { const fd = new FormData(); fd.append('file', file, file.name); f.file_id = (await api('POST', `/api/conversations/${q(C.conv)}/files`, undefined, {form: fd})).file_id; }
      catch (e) { f.err = 'Not uploaded'; toast(`${file.name}: ${e.message}`, true); }
      f.up = false; tray();
    }
  }
  function pickFiles(accept) { return new Promise(res => { const i = document.createElement('input'); i.type = 'file'; i.multiple = true; i.accept = accept; i.onchange = () => res([...i.files]); i.click(); }); }

  // ------------------------------------------------------------------ pages ---
  const ENTER = {
    chat() { if (!C.conv) openChat().then(() => { if (C.ask && PAGE === 'chat' && C.autosend) { C.autosend = false; chatSend(); } chatPoll(); });
      else { chatLoad(false).then(() => { paintChat(); if (C.autosend) { C.autosend = false; chatSend(); } chatPoll(); }); } },
    dub() { if (ARG) { loadDub(ARG); return; } api('GET', `${A}/dubs`).then(r => { UI.dubs = r.dubs || []; if (PAGE === 'dub' && !ARG) draw(); }).catch(e => { UI.dubs = []; toast(e.message, true); }); },
    mine() { consentLine(UI.clone.lang); },
  };
  const AFTER = {
    chat() {
      const host = $('#hvThread');
      if (host) { C.thread = window.HoolaChat ? HoolaChat.mount(host, {acts: ['copy'], scroller: $('#hvView'), jump: false}) : plainThread(host); paintChat(C.sending); }
      else C.thread = null;
      const ta = $('#hvAsk'); if (ta) { ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); chatSend(); } });
        ta.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); chatFiles(fs); } }); }
      price('chat', ttsQuote(C.ask));
    },
    speech() { price('speech', ttsQuote(S.text)); },
    mine() { price('clone', {job: 'clone', lang: UI.clone.lang}); },
    dialogue() { price('dlg', {job: 'dialogue', chars: UI.dlg.lines.reduce((n, l) => n + (l.text || '').length, 0), lang: UI.dlg.lang}); },
    changer() { price('chg', {job: 'change', seconds: UI.chg.secs || 60, voice: UI.chg.voice}); },
    cleanup() { if (UI.cl.people || UI.cl.music) price('cl', {job: 'isolate', seconds: UI.cl.secs || 60}); },
    sfx() { price('fx', {job: 'sfx', seconds: UI.fx.seconds, takes: UI.fx.takes}); },
    dub() { if (!ARG) price('dub', {job: UI.dubNew.mode === 'own' ? 'dub_own' : 'dub_matched', seconds: UI.dubNew.secs || 60, langs: UI.dubNew.langs.length || 1}); },
  };

  const V = {
    chat: chatView,

    speech() {
      const lim = D.limits?.characters || 100000, n = S.text.length, w = speakWhy(S.lang, S.engine), g = gate(w), v = voice(S.voice);
      return `<div class="hi-wrap">${head('Speech', `Paste up to ${num(lim)} characters. Long text is read in parts that flow as one.`)}
        <form class="hv-two" data-f="speech"><div class="hi-grid">
          <div class="hi-card hv-write"><div class="hv-tags" role="toolbar" aria-label="Add a feeling"><span>Add a feeling</span>${D.feelings.map(t => `<button type="button" data-a="tag" data-val="${esc(t)}">[${esc(t)}]</button>`).join('')}<button type="button" data-a="tag" data-val="pause">+ Pause</button></div>
            <label class="hv-sr" for="hvText">Words to speak</label><textarea id="hvText" class="hv-in" maxlength="${lim}" data-m="S.text" placeholder="Start typing here, or paste your script. Put a feeling in square brackets, like [warm] or [laughs]; it is never read out.">${esc(S.text)}</textarea>
            <div class="hv-boxrow"><span class="hi-sm hi-mut hi-num" id="hvCount">${num(n)} / ${num(lim)} characters</span><span class="hi-fill"></span>
              <button class="hv-pill" data-qbtn="speech" data-label="Make ${S.takes} take${S.takes > 1 ? 's' : ''}" data-icon="play"${g.a}>${ic('play')}Make ${S.takes} take${S.takes > 1 ? 's' : ''}</button></div>
            ${g.l}<p class="hv-line" data-qline="speech">The price shows here before anything is made.</p></div>
          ${S.out.length ? `<section class="hi-grid" aria-label="Takes"><h2>Takes</h2><div class="hv-takes" id="hvTakes">${S.out.map(takeCard).join('')}</div></section>` : ''}
          <div class="hv-ask"><label class="hv-sr" for="hvAskS">Ask Hoola to change it</label><input id="hvAskS" placeholder="Ask Hoola to change it: make take B slower and warmer…" maxlength="1000">
            <button type="button" class="hv-pill s" data-a="askspeech">${ic('chat')}Ask Hoola</button></div></div>
          <aside class="hi-card hv-aside"><h3>Settings</h3>
            <div class="hv-field"><span class="lab">Voice</span><button type="button" class="hv-pick" data-a="pickvoice" data-k="S.voice"><span class="hv-dot s" style="--c:${v?.color || colorOf(S.voice)}">${esc((v?.name || '?').slice(0, 1))}</span><span>${esc(v ? `${v.name}${v.tone ? ' · ' + v.tone : ''}` : 'No voice ready')}</span><b class="hi-sm" style="color:var(--pri-ink)">Change</b></button></div>
            <div class="hv-field"><span class="lab">Language</span><button type="button" class="hv-pick" data-a="picklang" data-k="S.lang" data-auto="1">${ic('lang')}<span>${esc(langLabel(S.lang))}</span></button><span class="hv-sub">Or choose one of ${num(D.langs.length)} languages and accents</span></div>
            <div class="hv-field"><span class="lab">Expressive <b data-show="S.expressive">${(+S.expressive).toFixed(2)}</b></span><input type="range" min="0" max="1" step="0.05" value="${S.expressive}" data-m="S.expressive" data-t="num" aria-label="Expressive"><span class="hv-sub">Steady and calm ← → lively and emotional</span></div>
            <div class="hv-field"><span class="lab">Speed <b data-show="S.speed">${(+S.speed).toFixed(2)}x</b></span><input type="range" min="0.7" max="1.3" step="0.05" value="${S.speed}" data-m="S.speed" data-t="num" aria-label="Speed"><span class="hv-sub">0.7x to 1.3x</span></div>
            ${Object.keys(D.styles || {}).length ? `<div class="hv-field"><span class="lab">Style</span>${seg('S.style', Object.entries(D.styles), S.style)}</div>` : ''}
            <div class="hv-field"><span class="lab">Takes</span>${seg('S.takes', [[1, '1'], [2, '2'], [3, '3']], S.takes)}</div>
            <div class="hv-field"><span class="lab">File</span>${seg('S.format', [['wav', 'WAV'], ['mp3', 'MP3'], ['flac', 'FLAC']], S.format)}</div>
            <label class="hi-check"><input type="checkbox" data-m="S.rules" data-t="bool"${S.rules ? ' checked' : ''}><span>Use my dictionary (${D.rules.length} word${D.rules.length === 1 ? '' : 's'})</span></label>
            <div class="hv-field"><span class="lab">Engine</span><b data-qeng="speech">${S.engine === 'auto' ? 'Hoola Auto' : esc(NAMES[S.engine])}</b>${engSeg('S.engine', S.engine)}
              <span class="hv-sub">${esc(priceHint())}</span></div></aside></form></div>`;
    },

    voices() {
      const f = UI.vf, lib = D.voices.filter(v => v.kind === 'hoola'), mine = D.voices.filter(v => v.kind !== 'hoola'), saved = D.voices.filter(v => UI.saved.includes(v.id));
      const base = f.tab === 'Your voices' ? mine : f.tab === 'Saved' ? saved : lib, lo = f.q.trim().toLowerCase();
      const list = base.filter(v => (!lo || [v.name, v.tone, v.accent, v.use, ...(v.langs || []).map(c => [c, lang(c)?.name, lang(c)?.native].join(' '))].join(' ').toLowerCase().includes(lo))
        && (!f.lang || (v.langs || []).includes(f.lang)) && (!f.accent || v.accent === f.accent) && (!f.gender || v.gender === f.gender) && (!f.age || v.age === f.age)
        && (!f.engine || v.engine === f.engine) && (!f.use || v.use === f.use));
      const uniq = k => [...new Set(D.voices.map(v => v[k]).filter(Boolean))].sort();
      const langsIn = [...new Set(D.voices.flatMap(v => v.langs || []))];
      const sel = (k, label, opts) => `<label class="hv-sr" for="hvF${k}">${label}</label><select id="hvF${k}" data-m="UI.vf.${k}" data-redraw="1"><option value="">${label}: any</option>${opts.map(([v, n]) => `<option value="${esc(v)}"${f[k] === v ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select>`;
      const card = v => { const g = gate(v.ready ? '' : (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.')), sv = UI.saved.includes(v.id);
        return `<div class="hv-vc"><div class="hv-vtop"><span class="hv-dot" style="--c:${esc(v.color || colorOf(v.id))}">${esc((v.name || '?').slice(0, 1))}</span><span><b>${esc(v.name)}</b><br><span class="hi-sm hi-mut">${esc([v.tone, [v.gender, v.age].filter(Boolean).join(', ')].filter(Boolean).join(' · '))}</span></span></div>
          <span class="hv-vlangs">${esc((v.langs || []).map(c => lang(c)?.native || c).join(' · ') || 'Every language its engine speaks')}</span>
          <span class="hi-row" style="gap:6px">${v.use ? `<span class="hv-chip">${esc(v.use)}</span>` : ''}<span class="hv-chip ${v.tier === 'premium' ? 'prem' : ''}">${v.tier === 'premium' ? 'Premium' : 'Standard'}</span>${v.kind === 'clone' ? '<span class="hv-chip ok">Your yes recorded</span>' : v.kind !== 'hoola' ? '<span class="hv-chip pri">Yours</span>' : ''}</span>
          <span class="hv-vacts"><button type="button" class="hi-btn q s" data-a="hear" data-id="${esc(v.id)}"${g.a}>${ic('play')}Hear</button><button type="button" class="hv-pill s" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ` disabled aria-describedby="hvw${WN}"`}>Use</button>
            <button type="button" class="hi-btn q s ico hv-star" data-a="save" data-id="${esc(v.id)}" aria-pressed="${sv}" aria-label="${sv ? 'Remove from Saved' : 'Save'} ${esc(v.name)}" title="${sv ? 'Saved' : 'Save'}">${ic('star')}</button></span>${g.l}</div>`; };
      return `<div class="hi-wrap">${head('Voices', 'Voices for every language, plus the ones you make', `<button class="hv-pill" data-a="go" data-p="mine">${ic('plus')}Your own voice</button>`)}
        <div class="hi-tabs" role="tablist">${[['Library', lib.length], ['Your voices', mine.length], ['Saved', saved.length]].map(([t, n]) => `<button class="hi-tab" role="tab" aria-selected="${f.tab === t}" data-a="vtab" data-val="${t}">${t} · ${n}</button>`).join('')}</div>
        <div class="hi-grid"><label class="hv-sr" for="hvVq">Search voices</label><input id="hvVq" class="hv-in" type="search" value="${esc(f.q)}" data-m="UI.vf.q" data-redraw="1" placeholder="Search: warm grandmother, news, Brazilian, deep…">
          <div class="hv-filters">${sel('lang', 'Language', langsIn.map(c => [c, langLabel(c)]))}${sel('accent', 'Accent', uniq('accent').map(a => [a, a]))}${sel('gender', 'Gender', [['female', 'Female'], ['male', 'Male']])}
            ${sel('age', 'Age', [['young', 'Young'], ['middle', 'Middle'], ['older', 'Older']])}${sel('engine', 'Engine', [['gemini', 'Gemini voice'], ['eleven', 'ElevenLabs'], ['lab', 'Hoola GPU lab']])}</div>
          <div class="hv-chips">${uniq('use').map(u => `<button type="button" data-a="vuse" data-val="${esc(u)}" aria-pressed="${f.use === u}">${esc(u)}</button>`).join('')}</div></div>
        ${list.length ? `<div class="hv-vgrid">${list.map(card).join('')}</div>` : `<div class="hi-empty"><b>${f.tab === 'Saved' ? 'No saved voices yet' : f.tab === 'Your voices' ? 'No voices of your own yet' : 'No voice matches'}</b>${f.tab === 'Saved' ? 'Tap the star on a voice to keep it here.' : f.tab === 'Your voices' ? 'Clone, design or remix one in Your voice.' : 'Try fewer filters.'}</div>`}
        <p class="hi-sm hi-mut">The sample is made once and kept, so hearing a voice is free. Every voice speaks every language its engine knows; the languages shown are where it sounds most natural.</p></div>`;
    },

    mine() {
      const cl = UI.clone, ds = UI.design, rx = UI.remix, cline = UI.cline[cl.lang];
      const canClone = D.status.connected.clone ?? (ready('gemini') || ready('lab')), canDesign = D.status.connected.design ?? (ready('gemini') || ready('lab'));
      const why = ok => ok ? '' : 'No engine that makes voices is set up on this server (Gemini voice or the Hoola GPU lab).';
      const fstate = (k) => { const x = cl[k]; return x ? `<span class="hi-sm ${x.err ? 'hv-why' : 'hi-mut'}">${esc(x.name)}${x.secs ? ' · ' + secs(x.secs) : ''}${x.up ? ' · uploading…' : x.err ? ' · ' + esc(x.err) : x.file_id ? ' · ready' : ''}</span>` : ''; };
      const recBtn = k => REC[k] ? `<button type="button" class="hi-btn q s" data-a="recstop" data-k="${k}">${ic('stop')}Stop</button><span class="hv-rec" data-rect="${k}">Recording…</span>`
        : `<button type="button" class="hi-btn q s" data-a="rec" data-k="${k}">${ic('mic')}Record</button>`;
      const gc = gate(why(canClone) || (!cl.sample?.file_id ? 'Add the recording first (step 1).' : !cl.consent?.file_id ? 'Record the yes first (step 2).' : !cl.ok ? 'Tick the box above first.' : ''));
      const gd = gate(why(canDesign)), gs = gate(ds.pick ? '' : 'Pick one of the three options first.'), gr = gate(why(canDesign) || (rx.base ? '' : 'Choose a voice to start from.'));
      const mine = D.voices.filter(v => v.kind !== 'hoola');
      const fallback = cline && cline.lang && cline.lang !== cl.lang;
      return `<div class="hi-wrap wide">${head('Your own voice', 'Three ways to a voice that is only yours. Each works in every language its engine speaks.')}
        <div class="hv-three">
          <form class="hi-card hi-grid" data-f="clone"><div><h2>Clone a voice</h2><span class="hi-sm hi-mut">From a recording</span></div>${why(canClone) ? warnNote(why(canClone)) : ''}
            <div class="hv-step"><span class="n">1</span><div><b>Record 10 to 30 seconds, or upload</b><div class="hi-row">${recBtn('sample')}<label class="hi-btn q s" for="hvCSample" style="cursor:pointer">${ic('plus')}Upload</label><input id="hvCSample" type="file" accept="audio/*" class="hv-sr" data-file="sample"></div>${fstate('sample')}
              <span class="hi-sm hi-mut">One person, a quiet room, speak naturally. Any language.</span></div></div>
            <div class="hv-step"><span class="n">2</span><div><b>Say yes, in your own voice</b>
              <button type="button" class="hv-pick" data-a="picklang" data-k="UI.clone.lang" data-need="clone">${ic('lang')}<span>${esc(langLabel(cl.lang))}</span></button>
              ${cline ? `<p class="hv-consent" lang="${esc(cline.locale || cline.lang || '')}">"${esc(cline.line)}"</p>${cline.english && cline.english !== cline.line ? `<p class="hi-sm hi-mut">"${esc(cline.english)}"</p>` : ''}
                ${fallback ? `<p class="hv-why">There is no consent statement in ${esc(lang(cl.lang)?.name || cl.lang)} yet, so the English one is used.</p>` : ''}` : '<p class="hi-sm hi-mut">Loading the consent line…</p>'}
              <div class="hi-row">${recBtn('consent')}<label class="hi-btn q s" for="hvCConsent" style="cursor:pointer">${ic('plus')}Upload</label><input id="hvCConsent" type="file" accept="audio/*" class="hv-sr" data-file="consent"></div>${fstate('consent')}
              <span class="hi-sm hi-mut">Read this line aloud in the same voice as step 1.</span></div></div>
            <div class="hv-step"><span class="n">3</span><div><b>Name it</b><label class="hv-sr" for="hvCName">Name of the voice</label><input id="hvCName" class="hv-in" maxlength="40" data-m="UI.clone.name" value="${esc(cl.name)}">
              <label class="hi-check"><input type="checkbox" id="hvCOk" required data-m="UI.clone.ok" data-t="bool" data-redraw="1"${cl.ok ? ' checked' : ''}><span>This is my own voice, or the person speaking agreed to this</span></label>
              <button class="hv-pill" data-qbtn="clone" data-label="Make my voice"${gc.a}>Make my voice</button>${gc.l}<p class="hv-line" data-qline="clone"></p></div></div>
            <p class="hi-sm hi-mut">Not allowed: anyone under 18, public figures, a person who did not say yes. Removing the voice deletes both recordings.</p></form>
          <form class="hi-card hi-grid" data-f="design"><div><h2>Design a voice</h2><span class="hi-sm hi-mut">From words</span></div>${why(canDesign) ? warnNote(why(canDesign)) : ''}
            <label class="hi-f">Describe the voice<textarea id="hvDDesc" rows="4" maxlength="400" data-m="UI.design.desc" placeholder="An older man with a deep, kind voice, slow and calm, telling stories by a fire. A light Irish accent.">${esc(ds.desc)}</textarea></label>
            <span class="hi-sm hi-mut">Who · age · tone · pace · accent · the room. Never a named person.</span>
            <label class="hi-f">Gender<select id="hvDGender" data-m="UI.design.gender"><option value="">Not set</option><option value="female"${ds.gender === 'female' ? ' selected' : ''}>Female</option><option value="male"${ds.gender === 'male' ? ' selected' : ''}>Male</option></select></label>
            <div><button class="hi-btn q" data-qbtn="design" data-label="Make 3 options"${gd.a}>Make 3 options</button>${gd.l}</div>
            ${ds.previews.length ? `<div class="hi-grid" style="gap:8px"><span class="hi-sm hi-mut">3 to choose from</span>${ds.previews.map(p => `<div class="hv-opt${ds.pick === p.pid ? ' on' : ''}"><button type="button" class="hv-play" data-a="playa" data-id="${esc(p.audio_id)}" aria-label="Play ${esc(p.title)}">${ic('play')}</button>
                <span class="hi-fill">${esc(p.title)}</span><button type="button" class="hi-btn q s" data-a="dpick" data-val="${esc(p.pid)}" aria-pressed="${ds.pick === p.pid}">${ds.pick === p.pid ? `${ic('check')}Picked` : 'Pick'}</button></div>`).join('')}
              <label class="hi-f">Name<input id="hvDName" maxlength="40" data-m="UI.design.name" value="${esc(ds.name)}" placeholder="Grandpa Joe"></label>
              <div><button type="button" class="hv-pill" data-a="dsave"${gs.a}>Save the voice</button>${gs.l}</div></div>` : ''}</form>
          <form class="hi-card hi-grid" data-f="remix"><div><h2>Remix a voice</h2><span class="hi-sm hi-mut">Change one you have</span></div>
            <label class="hi-f">Starting voice<select id="hvRBase" data-m="UI.remix.base">${D.voices.filter(v => v.ready).map(v => `<option value="${esc(v.id)}"${rx.base === v.id ? ' selected' : ''}>${esc(v.name)}</option>`).join('') || '<option value="">No voice ready</option>'}</select></label>
            <label class="hi-f">What to change<input id="hvRChange" maxlength="300" data-m="UI.remix.change" value="${esc(rx.change)}" placeholder="Same voice, but more energetic, like a radio host"></label>
            <div class="hv-chips">${['Older', 'Younger', 'Deeper', 'Brighter', 'Calmer', 'Another accent'].map(c => `<button type="button" data-a="rxchip" data-val="${c}">${c}</button>`).join('')}</div>
            <label class="hi-f">Name<input id="hvRName" maxlength="40" data-m="UI.remix.name" value="${esc(rx.name)}" placeholder="Amani · radio"></label>
            <div><button class="hv-pill"${gr.a}>Make the remix</button>${gr.l}</div></form></div>
        <section class="hi-grid"><h2>Your voices</h2>${mine.length ? `<div class="hi-card hv-list">${mine.map(v => `<div class="hv-row"><span class="hv-dot s" style="--c:${esc(v.color || colorOf(v.id))}">${esc(v.name.slice(0, 1))}</span>
            <span class="hi-fill"><b>${esc(v.name)}</b><br><span class="hi-sm hi-mut">${v.kind === 'clone' ? 'Cloned · your yes recorded' : v.kind === 'design' ? 'Designed from words' : v.kind === 'remix' ? 'A remix' : esc(v.kind)}</span></span>
            <span class="hv-chip ${v.ready ? 'ok' : ''}">${v.ready ? 'Ready' : 'Not ready'}</span><button type="button" class="hi-btn danger s" data-a="rmv" data-id="${esc(v.id)}">Remove</button></div>`).join('')}</div>`
          : '<div class="hi-empty"><b>No voices of your own yet</b>Clone, design or remix one above.</div>'}</section></div>`;
    },

    dialogue() {
      const d = UI.dlg, chars = d.lines.reduce((n, l) => n + (l.text || '').length, 0), names = d.cast.map(c => c.name);
      const w = speakWhy(d.lang, 'auto') || (d.lines.some(l => (l.text || '').trim()) ? '' : 'Write at least one line first.'), g = gate(w);
      const lines = `<div class="hv-lines">${d.lines.map((l, n) => `<div class="hv-ln"><label class="hv-sr" for="hvLs${n}">Speaker of line ${n + 1}</label><select id="hvLs${n}" data-m="UI.dlg.lines.${n}.speaker">${names.map(x => `<option${x === l.speaker ? ' selected' : ''}>${esc(x)}</option>`).join('')}</select>
          <label class="hv-sr" for="hvLt${n}">Line ${n + 1}</label><textarea id="hvLt${n}" class="hv-in" maxlength="1500" rows="2" data-m="UI.dlg.lines.${n}.text" placeholder="What this speaker says. Feelings in brackets, like [laughs].">${esc(l.text)}</textarea>
          ${d.lines.length > 1 ? `<button type="button" class="hi-ib" data-a="dlrm" data-n="${n}" aria-label="Remove line ${n + 1}">${ic('x')}</button>` : '<span></span>'}</div>`).join('')}
        ${d.lines.length < (D.limits?.lines || 40) ? `<button type="button" class="hi-btn q s" data-a="dladd" style="justify-self:start">${ic('plus')}Add a line</button>` : ''}</div>`;
      const pod = d.pod, gp = gate(!ready('gemini') && !ready('eleven') ? 'No engine that writes and speaks a podcast is set up on this server.' : '');
      const podForm = `<form class="hi-card hi-grid" data-f="podcast"><h2>Podcast from a document</h2>
          ${seg('UI.dlg.pod.src', [['file', 'A file'], ['url', 'A web address'], ['text', 'Pasted text']], pod.src)}
          ${pod.src === 'file' ? `<label class="hi-f">PDF, Word, text or EPUB<input type="file" data-file="pod" accept=".pdf,.doc,.docx,.txt,.epub,.md"></label>${pod.file ? `<span class="hi-sm hi-mut">${esc(pod.file.name)}${pod.file.up ? ' · uploading…' : pod.file.file_id ? ' · ready' : ''}</span>` : ''}`
            : pod.src === 'url' ? `<label class="hi-f">Web address<input type="url" data-m="UI.dlg.pod.url" value="${esc(pod.url)}" placeholder="https://"></label>`
            : `<label class="hi-f">The text<textarea rows="5" data-m="UI.dlg.pod.text" maxlength="60000">${esc(pod.text)}</textarea></label>`}
          <label class="hi-f">Minutes (1 to 15)<input type="number" min="1" max="15" data-m="UI.dlg.pod.minutes" data-t="num" value="${pod.minutes}"></label>
          <span class="hi-sm hi-mut">The two hosts are the first two speakers in the cast.</span>
          <div><button class="hv-pill"${gp.a}>${ic('dialogue')}Write the script</button>${gp.l}</div><span class="hi-sm hi-mut">Hoola writes the talk first. You read it, change any line, then make the sound.</span></form>`;
      return `<div class="hi-wrap wide">${head('Dialogue', d.title ? esc(d.title) : 'Several speakers in one file, each in their own voice.')}
        <div class="hi-tabs" role="tablist">${[['lines', 'Write the lines'], ['podcast', 'Podcast from a document']].map(([k, t]) => `<button class="hi-tab" role="tab" aria-selected="${d.mode === k}" data-a="dmode" data-val="${k}">${t}</button>`).join('')}</div>
        <div class="hv-two"><div class="hi-grid">${d.mode === 'podcast' ? podForm : `<form class="hi-grid" data-f="dialogue">${lines}</form>`}
          <div class="hv-ask"><label class="hv-sr" for="hvAskD">Ask Hoola to change it</label><input id="hvAskD" placeholder="Ask Hoola to change it: make it 3 minutes…" maxlength="1000"><button type="button" class="hv-pill s" data-a="askdlg">${ic('chat')}Ask Hoola</button></div></div>
          <aside class="hi-card hv-aside"><h3>Cast</h3>${d.cast.map((c, i) => `<div class="hv-cast"><label class="hv-sr" for="hvCn${i}">Speaker ${i + 1} name</label><input id="hvCn${i}" maxlength="30" data-m="UI.dlg.cast.${i}.name" data-rename="${i}" value="${esc(c.name)}">
              <label class="hv-sr" for="hvCv${i}">Voice of ${esc(c.name)}</label><select id="hvCv${i}" data-m="UI.dlg.cast.${i}.voice">${D.voices.filter(v => v.ready).map(v => `<option value="${esc(v.id)}"${c.voice === v.id ? ' selected' : ''}>${esc(v.name)}</option>`).join('') || '<option value="">No voice ready</option>'}</select>
              ${d.cast.length > 1 ? `<button type="button" class="hi-ib" data-a="castrm" data-n="${i}" aria-label="Remove ${esc(c.name)}">${ic('x')}</button>` : '<span></span>'}</div>`).join('')}
            ${d.cast.length < 6 ? `<button type="button" class="hi-btn q s" data-a="castadd" style="justify-self:start">${ic('plus')}Add a speaker (up to 6)</button>` : ''}
            <div class="hv-field"><span class="lab">Language</span><button type="button" class="hv-pick" data-a="picklang" data-k="UI.dlg.lang" data-need="dialogue" data-auto="1">${ic('lang')}<span>${esc(langLabel(d.lang))}</span></button></div>
            ${Object.keys(D.styles || {}).length ? `<div class="hv-field"><span class="lab">How they talk</span>${seg('UI.dlg.style', [['', 'Natural'], ...Object.entries(D.styles)], d.style)}</div>` : ''}
            ${d.mode === 'lines' ? `<div><button type="button" class="hv-pill" data-a="dlgmake" data-qbtn="dlg" data-label="Make the dialogue"${g.a}>Make the dialogue</button>${g.l}</div><p class="hv-line" data-qline="dlg">${num(chars)} characters · up to 6 speakers and 40 lines</p>` : ''}</aside></div></div>`;
    },

    studio() {
      const im = UI.imp;
      return `<div class="hi-wrap">${head('Studio', 'Long readings in chapters: stories, lessons, audiobooks, with a voice per character.', `<span class="hi-row"><button class="hi-btn q" data-a="impopen">${ic('down')}Import a book</button><button class="hv-pill" data-a="newproj">${ic('plus')}New reading</button></span>`)}
        ${im.open ? `<form class="hi-card hi-grid" data-f="import"><h2>Import</h2><span class="hi-sm hi-mut">EPUB, PDF, TXT, DOCX, a web page or pasted text. It is split into chapters for you.</span>
          ${seg('UI.imp.src', [['file', 'A file'], ['url', 'A web address'], ['text', 'Pasted text']], im.src)}
          ${im.src === 'file' ? `<label class="hi-f">The file<input type="file" data-file="imp" accept=".epub,.pdf,.txt,.doc,.docx,.md"></label>${im.file ? `<span class="hi-sm hi-mut">${esc(im.file.name)}${im.file.up ? ' · uploading…' : im.file.file_id ? ' · ready' : ''}</span>` : ''}`
            : im.src === 'url' ? `<label class="hi-f">Web address<input type="url" data-m="UI.imp.url" value="${esc(im.url)}" placeholder="https://"></label>` : `<label class="hi-f">The text<textarea rows="6" data-m="UI.imp.text">${esc(im.text)}</textarea></label>`}
          <label class="hi-f">Title (optional)<input maxlength="80" data-m="UI.imp.title" value="${esc(im.title)}"></label>
          <div class="hi-row"><button class="hv-pill">Import</button><button type="button" class="hi-btn q" data-a="impclose">Cancel</button></div></form>` : ''}
        ${D.projects.length ? `<div class="hi-grid hi-g3">${D.projects.map(p => { const ch = p.chapters || [], done = ch.filter(c => c.audio).length;
            return `<button class="hi-av" data-a="proj" data-id="${esc(p.id)}"><span class="hi-thumb" style="--t:${colorOf(p.id)}"><span class="cnt hi-num">${ch.length} chapter${ch.length === 1 ? '' : 's'}</span><span class="cap">${esc(p.title)}</span></span>
              <span class="hi-row nw" style="justify-content:space-between"><span class="hi-sm hi-mut">${esc(langLabel(p.lang))} · ${esc(ago(p.updated || p.made))}</span><span class="hi-chip ${done && done === ch.length ? 'ok' : ''}">${done} of ${ch.length} read</span></span></button>`; }).join('')}</div>`
          : `<div class="hi-empty"><b>No readings yet</b>Paste a story or a lesson, or import a book, and Hoola reads each chapter.<button class="hv-pill" data-a="newproj">New reading</button></div>`}</div>`;
    },

    reading() {
      const p = UI.proj; if (!p) return V.studio();
      const all = p.chapters.length && p.chapters.every(x => x.audio), w = speakWhy(p.lang || S.lang, 'auto'), ge = gate(p.id && all ? '' : 'Read every chapter first.');
      const cast = UI.cast, who = cast ? new Map((cast.characters || []).map((c, i) => [c.name, COLORS[i % COLORS.length]])) : null;
      return `<div class="hi-wrap wide"><div class="hi-edhead"><button class="hi-btn q ico" data-a="go" data-p="studio" aria-label="Back to Studio" title="Back to Studio">${ic('back')}</button>
          <h1 class="hv-sr">Reading</h1><label class="hv-sr" for="hvPTitle">Title</label><input id="hvPTitle" class="hi-title" data-m="UI.proj.title" value="${esc(p.title || '')}" maxlength="80" placeholder="Title of the reading">
          ${p.id ? `<button class="hi-btn danger" data-a="rmproj" data-id="${esc(p.id)}">Remove</button>` : ''}<button class="hi-btn q" data-a="saveproj">Save</button>
          <span><button class="hv-pill" data-a="expmenu"${ge.a}>${ic('down')}Export</button>${ge.l}</span></div>
        ${w ? warnNote(w + ' You can write and save; reading needs the engine.') : ''}
        <div class="hv-two"><div class="hi-grid">${p.chapters.map((ch, n) => { const g = gate(w);
            return `<div class="hi-scene"><div class="hd"><span class="hi-sn">${n + 1}</span><label class="hv-sr" for="hvCh${n}">Chapter ${n + 1} title</label><input class="hv-who" id="hvCh${n}" data-m="UI.proj.chapters.${n}.title" value="${esc(ch.title || '')}" maxlength="80" placeholder="Chapter title"><span class="hi-fill"></span>
                ${ch.audio ? `<button type="button" class="hi-btn q s" data-a="play" data-id="${esc(ch.audio)}">${ic('play')}${secs(ch.seconds)}</button>` : ''}
                <button type="button" class="hi-btn q s" data-a="cast" data-n="${n}"${p.id ? '' : gate('Save the reading first.').a}>Characters</button>
                <button type="button" class="hv-pill s" data-a="readch" data-n="${n}"${g.a}>${ch.audio ? 'Read again' : 'Read chapter'}</button>
                ${p.chapters.length > 1 ? `<button type="button" class="hi-ib" data-a="chrm" data-n="${n}" aria-label="Remove chapter ${n + 1}">${ic('x')}</button>` : ''}</div>${g.l}${p.id ? '' : `<p class="hv-why" id="hvw${WN}">Save the reading first to find its characters.</p>`}
              <label class="hv-sr" for="hvCt${n}">Chapter ${n + 1} words</label><textarea id="hvCt${n}" class="hv-in hv-serif" data-m="UI.proj.chapters.${n}.text" style="min-height:140px" maxlength="${D.limits?.characters || 100000}" placeholder="The words of this chapter">${esc(ch.text || '')}</textarea>
              ${cast && cast.n === n ? `<div class="hi-grid" style="gap:8px">${(cast.paragraphs || []).map(pa => `<p class="hv-para" style="--c:${who.get(pa.who) || 'var(--hair)'}"><b>${esc(pa.who || 'Narrator')}</b>${esc(pa.text)}</p>`).join('')}</div>` : ''}
              <div class="ft"><span class="hi-chip ${ch.audio ? 'ok' : ''}">${ch.audio ? 'Read' : 'Not read yet'}</span><span class="hi-sm hi-dim hi-num">${num((ch.text || '').length)} characters</span></div></div>`; }).join('')}
            <button type="button" class="hi-btn q s" data-a="chadd" style="justify-self:start">${ic('plus')}Add a chapter</button></div>
          <aside class="hi-card hv-aside"><h3>Reading voice</h3><label class="hi-f">Voice<select data-m="UI.proj.voice">${D.voices.filter(v => v.ready).map(v => `<option value="${esc(v.id)}"${(p.voice || S.voice) === v.id ? ' selected' : ''}>${esc(v.name)}</option>`).join('') || '<option value="">No voice ready</option>'}</select></label>
            <div class="hv-field"><span class="lab">Language</span><button type="button" class="hv-pick" data-a="picklang" data-k="UI.proj.lang">${ic('lang')}<span>${esc(langLabel(p.lang || 'en'))}</span></button></div>
            ${cast ? `<h3>Characters</h3>${(cast.characters || []).map((c, i) => `<label class="hi-f"><span><span class="hv-chip" style="background:${COLORS[i % COLORS.length]};color:#1C1B1A">${esc(c.name)}</span></span>
              <select data-cvoice="${esc(c.name)}">${D.voices.filter(v => v.ready).map(v => `<option value="${esc(v.id)}"${c.voice === v.id ? ' selected' : ''}>${esc(v.name)}</option>`).join('')}</select></label>`).join('') || '<p class="hi-sm hi-mut">No speakers found in this chapter.</p>'}` : ''}
            <p class="hi-sm hi-mut">Change a word and only that paragraph is read again, in the same voice.</p></aside></div></div>`;
    },

    dub() {
      if (ARG) return dubView();
      const n = UI.dubNew, ownWhy = ready('eleven') ? '' : whyNot('eleven'), go_ = gate(!ready('gemini') && !ready('eleven') ? 'No dubbing engine is set up on this server.' : !n.file?.file_id ? 'Add the video first.' : !n.langs.length ? 'Choose at least one language.' : (n.mode === 'own' && ownWhy) ? ownWhy : '');
      const og = gate(ownWhy);
      return `<div class="hi-wrap">${head('Dubbing', 'Your video in another language, in the same voices or matched ones. Only your own videos, or ones you have the right to dub. Each dub is marked as AI.')}
        <form class="hi-card hi-grid" data-f="dub"><h2>New dub</h2>
          <label class="hi-f">Video or recording<input type="file" data-file="dub" accept="video/*,audio/*"></label>${n.file ? `<span class="hi-sm hi-mut">${esc(n.file.name)}${n.secs ? ' · ' + secs(n.secs) : ''}${n.file.up ? ' · uploading…' : n.file.file_id ? ' · ready' : ''}</span>` : ''}
          <div class="hv-field"><span class="lab">Languages (up to 6)</span><div class="hv-chips">${n.langs.map(c => `<button type="button" data-a="dubrm" data-val="${esc(c)}" aria-label="Remove ${esc(langLabel(c))}">${esc(langLabel(c))} ×</button>`).join('')}
            ${n.langs.length < 6 ? `<button type="button" data-a="picklang" data-k="dubadd" data-need="dub">${ic('plus')} Language</button>` : ''}</div></div>
          <fieldset class="hi-grid" style="border:0;padding:0;margin:0;gap:8px"><legend class="hi-sm hi-mut" style="margin-bottom:6px">How it sounds</legend>
            <label class="hi-check"><input type="radio" name="hvDubMode" value="own" data-m="UI.dubNew.mode" data-redraw="1"${n.mode === 'own' ? ' checked' : ''}${og.a}><span><b>Their own voices</b> · premium<br><span class="hi-sm hi-mut">Each speaker sounds like themselves in the new language.</span></span></label>${og.l}
            <label class="hi-check"><input type="radio" name="hvDubMode" value="matched" data-m="UI.dubNew.mode" data-redraw="1"${n.mode === 'matched' ? ' checked' : ''}><span><b>Matched voices</b><br><span class="hi-sm hi-mut">A close Hoola voice per speaker.</span></span></label></fieldset>
          <label class="hi-check"><input type="checkbox" data-m="UI.dubNew.keep" data-t="bool"${n.keep ? ' checked' : ''}><span>Keep the music and room sound underneath</span></label>
          <div><button class="hv-pill" data-qbtn="dub" data-label="Make the dubs"${go_.a}>Make the dubs</button>${go_.l}</div><p class="hv-line" data-qline="dub"></p></form>
        <section class="hi-grid"><h2>Your dubs</h2>${UI.dubs == null ? '<p class="hv-line">Loading…</p>' : UI.dubs.length ? `<div class="hi-card hv-list">${UI.dubs.map(x => `<div class="hv-row"><span class="hi-fill"><b>${esc(x.title || x.name || 'Dub')}</b><br><span class="hi-sm hi-mut">${esc((x.langs || []).map(l => typeof l === 'string' ? langLabel(l) : (l.name || l.code)).join(', '))}${x.made ? ' · ' + esc(ago(x.made)) : ''}</span></span>
            <span class="hv-chip ${x.status === 'ready' ? 'ok' : x.status === 'failed' ? 'bad' : 'pri'}">${esc(x.status === 'ready' ? 'Ready' : x.status === 'failed' ? 'Failed' : 'Working')}</span><button type="button" class="hi-btn q s" data-a="dubopen" data-id="${esc(x.id)}">Open</button></div>`).join('')}</div>`
          : '<div class="hi-empty"><b>No dubs yet</b>Upload a video above.</div>'}</section></div>`;
    },

    changer() {
      const c = UI.chg, w = ready('eleven') ? '' : whyNot('eleven'), ev = D.voices.filter(v => v.engine === 'eleven' && v.ready);
      const g = gate(w || (!ev.length ? 'There is no ElevenLabs voice to change into yet.' : !c.file?.file_id ? 'Add the recording first.' : ''));
      return `<div class="hi-wrap narrow">${head('Voice changer', 'Say it your way: the timing, the laugh, the whisper. Get it back in another voice.')}
        ${w ? warnNote('The voice changer runs on ElevenLabs only. ' + w) : ''}
        <form class="hi-card hi-grid" data-f="change"><label class="hi-f">Record, or drop a recording or video (up to 5 minutes, 50 MB)<input type="file" data-file="chg" accept="audio/*,video/*"></label>
          ${c.file ? `<span class="hi-sm hi-mut">${esc(c.file.name)}${c.secs ? ' · ' + secs(c.secs) : ''}${c.file.up ? ' · uploading…' : c.file.file_id ? ' · ready' : ''}</span>` : ''}
          <label class="hi-f">Into<select data-m="UI.chg.voice">${ev.map(v => `<option value="${esc(v.id)}"${c.voice === v.id ? ' selected' : ''}>${esc(v.name)}${v.tone ? ' · ' + esc(v.tone) : ''}</option>`).join('') || '<option value="">No ElevenLabs voice</option>'}</select></label>
          <label class="hi-check"><input type="checkbox" data-m="UI.chg.denoise" data-t="bool"${c.denoise ? ' checked' : ''}><span>Remove background noise too</span></label>
          <div><button class="hv-pill" data-qbtn="chg" data-label="Change the voice"${g.a}>Change the voice</button>${g.l}</div><p class="hv-line" data-qline="chg"></p>
          ${c.out ? `<div class="hv-takes">${takeCard(c.out, 0)}</div>` : ''}</form></div>`;
    },

    cleanup() {
      const c = UI.cl, w = ready('eleven') ? '' : whyNot('eleven'), gw = gate(!c.file?.file_id ? 'Add the recording first.' : '');
      const opt = (k, n, l, prem) => { const g = gate(prem ? w : ''); return `<label class="hi-check"><input type="checkbox" data-m="UI.cl.${k}" data-t="bool" data-redraw="1"${c[k] && !(prem && w) ? ' checked' : ''}${g.a}><span><b>${n}</b> <span class="hv-chip ${prem ? 'prem' : 'ok'}">${prem ? 'Premium' : 'Free'}</span><br><span class="hi-sm hi-mut">${l}</span></span></label>${g.l}`; };
      return `<div class="hi-wrap narrow">${head('Clean-up', 'Make a voice clear, or pull it out of music.')}
        <form class="hi-card hi-grid" data-f="cleanup"><label class="hi-f">Recording or video<input type="file" data-file="cl" accept="audio/*,video/*"></label>
          ${c.file ? `<span class="hi-sm hi-mut">${esc(c.file.name)}${c.secs ? ' · ' + secs(c.secs) : ''}${c.file.up ? ' · uploading…' : c.file.file_id ? ' · ready' : ''}</span>` : ''}
          ${opt('denoise', 'Remove steady noise', 'Fans, hum, hiss, wind')}${opt('voice', 'Make the voice clearer', 'A little brighter and closer')}${opt('silence', 'Cut long silences', 'Gaps over a second are shortened')}
          ${opt('level', 'Even the loudness', 'Ready for reels and podcasts')}${opt('people', 'Remove street and people', 'Traffic, chatter, a second voice', true)}${opt('music', 'Lift the voice out of music', 'Keep the singing or speech only', true)}
          <div class="hi-row">${c.before ? `<button type="button" class="hi-btn q s" data-a="playurl" data-val="before">${ic('play')}Before</button>` : ''}${c.out ? `<button type="button" class="hi-btn q s" data-a="play" data-id="${esc(c.out.id)}">${ic('play')}After</button>` : ''}</div>
          <div><button class="hv-pill" data-qbtn="cl" data-label="Clean it"${gw.a}>Clean it</button>${gw.l}</div><p class="hv-line" data-qline="cl">${c.people || c.music ? '' : 'Noise, clarity, silences and loudness are free, made on Hoola\'s own server.'}</p></form></div>`;
    },

    sfx() {
      const f = UI.fx, w = ready('eleven') ? '' : whyNot('eleven'), g = gate(w || (f.prompt.trim().length < 3 ? 'Describe the sound first.' : ''));
      return `<div class="hi-wrap">${head('Sound effects', 'Describe any sound and get takes, or make a quick game sound for free.')}
        <form class="hi-card hi-grid" data-f="sfx"><h2>Describe the sound</h2>${w ? warnNote('Sounds from words run on ElevenLabs only. ' + w) : ''}
          <label class="hv-sr" for="hvFx">Describe the sound</label><textarea id="hvFx" class="hv-in" rows="3" maxlength="450" data-m="UI.fx.prompt" data-redraw-lazy="1" placeholder="A busy street market in the evening, people talking, a bicycle bell, distant music">${esc(f.prompt)}</textarea>
          <div class="hv-field"><span class="lab">Length</span>${seg('UI.fx.seconds', [[0, 'Auto'], [2, '2 s'], [5, '5 s'], [10, '10 s'], [30, '30 s']], f.seconds)}</div>
          <label class="hi-check"><input type="checkbox" data-m="UI.fx.loop" data-t="bool"${f.loop ? ' checked' : ''}><span>Loop smoothly</span></label>
          <div class="hv-field"><span class="lab">Takes</span>${seg('UI.fx.takes', [[1, '1'], [2, '2'], [3, '3'], [4, '4']], f.takes)}</div>
          <div><button class="hv-pill" data-qbtn="fx" data-label="Make ${f.takes} take${f.takes > 1 ? 's' : ''}"${g.a}>Make ${f.takes} take${f.takes > 1 ? 's' : ''}</button>${g.l}</div><p class="hv-line" data-qline="fx"></p>
          ${f.out.length ? `<div class="hv-takes">${f.out.map(takeCard).join('')}</div>` : ''}</form>
        <div class="hi-card hi-grid"><h2>Quick game sounds</h2><span class="hi-sm hi-mut">Coin, jump, click and more stay free, made on Hoola's own server. The same choice always gives the same sound.</span>
          <div class="hi-row"><label class="hi-f" style="width:140px">Variation<input type="number" id="hvSeed" min="1" max="9999" data-m="UI.seed" data-t="num" value="${UI.seed}"></label></div>
          <div class="hv-pads">${(D.sfx || []).map(p => `<button type="button" class="hv-pad" data-a="preset" data-val="${esc(p)}"><span class="hv-dot s" style="--c:${colorOf(p)}">${ic('spark')}</span>${esc(String(p).replace(/_/g, ' '))}</button>`).join('') || '<p class="hv-line">No quick sounds on this server.</p>'}</div></div></div>`;
    },

    dict() {
      return `<div class="hi-wrap">${head('Dictionary', 'How your names, places and product words must be said. Hoola applies these before any voice reads your text.')}
        <form class="hi-card hi-cols" data-f="rule"><label class="hi-f">Word as written<input id="hvRWord" maxlength="60" required placeholder="Akola"></label>
          <label class="hi-f">Say it as<input id="hvRSay" maxlength="120" required placeholder="Uh-ko-laa"></label>
          <label class="hi-f">In language<select id="hvRLang"><option value="">Every language</option>${D.langs.map(l => `<option value="${esc(l.code)}">${esc(langLabel(l.code))}</option>`).join('')}</select></label><button class="hv-pill" style="align-self:end">Add</button></form>
        ${D.rules.length ? `<div class="hi-card hi-scroll"><table><thead><tr><th>Word</th><th>Said as</th><th>Language</th><th></th></tr></thead><tbody>${D.rules.map(r => `<tr><td><b>${esc(r.word)}</b></td><td>${esc(r.say)}</td>
            <td>${r.lang ? esc(langLabel(r.lang)) : 'Every language'}</td><td style="text-align:right"><button class="hi-btn danger s" data-a="rmrule" data-id="${esc(r.id)}">Remove</button></td></tr>`).join('')}</tbody></table></div>`
          : '<div class="hi-empty"><b>No words yet</b>Add your shop name, your town, a product - anything a voice says wrongly.</div>'}
        <p class="hi-sm hi-mut">A rule matches the whole word, in any letter case. Your history keeps the words as you wrote them.</p></div>`;
    },

    history() {
      const kinds = ['All', ...new Set(D.history.map(h => KIND[h.kind] || h.kind))], f = UI.hist;
      const list = D.history.filter(h => f === 'All' || (KIND[h.kind] || h.kind) === f);
      return `<div class="hi-wrap">${head('History', `Everything you have made. The newest ${num(D.limits?.history || 200)} are kept; download the ones you need in WAV, MP3 or FLAC.`)}
        <div class="hv-chips">${kinds.map(x => `<button type="button" aria-pressed="${x === f}" data-a="hist" data-val="${esc(x)}">${esc(x)}</button>`).join('')}</div>
        ${list.length ? `<div class="hi-card hv-list">${list.map(histRow).join('')}</div>` : '<div class="hi-empty"><b>Nothing here yet</b><button class="hv-pill" data-a="go" data-p="chat">Ask Hoola</button></div>'}</div>`;
    },

    langs() {
      const R = ['All', 'Africa', 'Americas', 'Asia', 'Europe', 'Middle East', 'Pacific'], lo = UI.langQ.trim().toLowerCase();
      const list = D.langs.filter(l => (UI.langR === 'All' || l.region === UI.langR) && (!lo || [l.code, l.name, l.native].join(' ').toLowerCase().includes(lo)));
      const cell = v => v === 'yes' ? '<span class="hv-yes">Yes</span>' : v === 'premium' ? '<span class="hv-chip prem">Premium</span>' : '<span class="hi-mut">No</span>';
      return `<div class="hi-wrap wide">${head('Every language', `What works where, across ${num(D.langs.length)} languages and accents. Each name is shown in its own script.`)}
        <div class="hv-chips" role="group" aria-label="Region">${R.map(r => `<button type="button" aria-pressed="${UI.langR === r}" data-a="lregion" data-val="${r}">${r}</button>`).join('')}</div>
        <label class="hv-sr" for="hvLq">Search languages</label><input id="hvLq" class="hv-in" type="search" value="${esc(UI.langQ)}" data-m="UI.langQ" data-redraw="1" placeholder="Search a language">
        <div class="hi-card hi-scroll"><table><thead><tr><th>Language</th><th>Speech</th><th>Your voice</th><th>Dialogue</th><th>Dubbing</th><th>Voices</th><th>Sounded in our test</th></tr></thead><tbody>
          <tr><td><b>Auto</b><br><span class="hi-sm hi-mut">Hoola hears the language of your words</span></td><td colspan="6" class="hi-sm hi-mut">Mixed text keeps each part in its own language.</td></tr>
          ${list.map(l => `<tr><td><b>${esc(l.native || l.name)}</b><br><span class="hi-sm hi-mut">${esc(l.name)}${l.region ? ' · ' + esc(l.region) : ''}</span></td>
            <td>${l.speech === 'none' ? '<span class="hv-no">No engine yet</span>' : cell(l.speech)}</td><td>${cell(l.clone)}</td><td>${l.dialogue === 'none' && l.speech === 'none' ? '<span class="hv-no">No engine yet</span>' : cell(l.dialogue)}</td><td>${cell(l.dub)}</td>
            <td class="hi-num">${num(l.voices)}</td><td><span class="hv-q ${esc(l.quality || 'not_tested')}">${esc(QUAL[l.quality] || 'Not tested yet')}</span></td></tr>`).join('')}</tbody></table></div>
        <p class="hi-sm hi-mut">A language with no engine says so here and in every box, and nothing is read in another language instead. "Sounded in our test" comes from Hoola's own listening test of each language.</p></div>`;
    },

    settings() {
      if (ARG) { UI.setTab = ARG; ARG = ''; }
      const t = UI.setTab, u = D.usage || {};
      const state = e => e.state === 'ready' ? '<span class="hv-chip ok">Ready</span>' : e.state === 'needs_key' ? '<span class="hv-chip prem">Needs its key</span>' : '<span class="hv-chip">Off</span>';
      const tabsH = `<div class="hi-tabs" role="tablist">${['Engines and prices', 'Usage', 'Safety'].map(x => `<button class="hi-tab" role="tab" aria-selected="${t === x}" data-a="settab" data-val="${x}">${x}</button>`).join('')}</div>`;
      const body = t === 'Usage' ? `<div class="hi-cols"><div class="hi-card hi-grid"><h3>This month${u.month ? ' (' + esc(u.month) + ')' : ''}</h3><div>
            <div class="hi-kv"><span class="hi-mut">Characters spoken</span><b class="hi-num">${num(u.characters)}</b></div><div class="hi-kv"><span class="hi-mut">Minutes of sound</span><b class="hi-num">${u.minutes || 0}</b></div>
            <div class="hi-kv"><span class="hi-mut">Things made</span><b class="hi-num">${num(u.made)}</b></div>${u.credits_used != null ? `<div class="hi-kv"><span class="hi-mut">Credits used</span><b class="hi-num">${num(u.credits_used)}</b></div>` : ''}
            ${Object.entries(u.by_kind || {}).map(([k, n]) => `<div class="hi-kv"><span class="hi-mut">${esc(KIND[k] || k)}</span><span class="hi-num">${num(n)}</span></div>`).join('')}</div>
            <div class="hi-grid" style="gap:8px"><div class="hi-row nw" style="justify-content:space-between"><span class="hi-mut">Kept on this server</span><b class="hi-num">${num(u.kept)} / ${num(u.kept_max || 200)}</b></div><div class="hi-bar"><i style="width:${Math.min(100, (u.kept || 0) / (u.kept_max || 200) * 100)}%"></i></div></div></div></div>`
        : t === 'Safety' ? `<div class="hi-card"><ol class="hi-steps">${[['A cloned voice needs the person\'s spoken yes', 'Recorded in their own language, checked against the sample. Removing the voice deletes both recordings.'],
            ['No public figures, no imitation of a named person', 'A described or remixed voice that asks to sound like someone is refused.'],
            ['Every file carries an AI mark', 'Written into the file\'s own details.'], ['The price shows before every job', 'Nothing paid runs without your tap.'],
            ['A language with no engine is said plainly', 'It is never read in another language instead.'], ['Your sounds stay yours', 'They are files in your own folder. Nobody else can fetch them.']]
            .map(([a, b]) => `<li class="hi-step done"><span class="n">${ic('check')}</span><span><b>${a}</b><br><span class="hi-sm hi-mut">${b}</span></span></li>`).join('')}</ol></div>`
        : `<p class="hi-mut">Hoola Auto picks the engine for each job and language: the best that does it well, at the lowest price. You can choose one yourself for any job.</p>
          <div class="hi-grid hi-g3">${(D.engines || []).map(e => `<div class="hi-card hi-grid" style="gap:6px;align-content:start"><div class="hi-sh"><h3>${esc(e.name || NAMES[e.id] || e.id)}</h3>${state(e)}</div>
            <span class="hi-sm">${esc(e.does || '')}</span><span class="hi-sm hi-mut">${esc(Array.isArray(e.langs) ? e.langs.length + ' languages' : e.langs || '')}</span>${e.state !== 'ready' ? `<p class="hv-why">${esc(whyNot(e.id))}</p>` : ''}</div>`).join('') || '<p class="hv-line">No engine list from the server.</p>'}</div>
          <div class="hi-card hi-scroll"><table><thead><tr><th>Job</th><th>Hoola Auto uses</th><th>Credits</th><th>About</th></tr></thead><tbody>${(D.prices || []).map(p => `<tr><td>${esc(JOBS[p.job] || p.job)}</td><td>${esc(eng(p.engine)?.name || NAMES[p.engine] || p.engine || '')}</td>
            <td class="hi-num">${p.credits ? '≈ ' + num(p.credits) : 'Free'}</td><td class="hi-num">${p.usd ? esc(usd(p.usd)) : ''}</td></tr>`).join('')}</tbody></table></div>
          <p class="hi-sm hi-mut">The price shows before every job and comes off your Hoola credits. Prices are estimates from the engines' own rates: 1 credit = $0.001 of engine cost.</p>`;
      return `<div class="hi-wrap">${head('Settings', 'Engines and prices, what you have used, and the rules Hoola keeps.')}${tabsH}${body}</div>`;
    },
  };
  const JOBS = {tts: 'Speech, 1 minute', tts_premium: 'Premium speech, 1 minute', dialogue: 'Dialogue or podcast, 1 minute', clone: 'Clone a voice', design: 'Design a voice',
    chapter: 'Audiobook chapter', change: 'Voice changer, 1 minute', isolate: 'Voice out of music, 1 minute', sfx: 'Sound effect', dub_own: 'Dub in their own voices, 1 minute',
    dub_matched: 'Dub in matched voices, 1 minute', cleanup: 'Noise clean-up'};
  function priceHint() { const p = j => (D.prices || []).find(x => x.job === j);
    const a = p('tts'), b = p('tts_premium') || (D.prices || []).find(x => x.job === 'tts' && x.engine === 'eleven');
    return [a ? `≈ ${cr(a.credits)} a minute` : '', b && b !== a ? `premium ≈ ${num(b.credits)}` : ''].filter(Boolean).join(' · ') || 'The price shows under the button before anything is made.'; }

  // ------------------------------------------------------------------ one dub ---
  function dubView() {
    const d = UI.dub;
    if (!d || d.id !== ARG) return `<div class="hi-wrap">${head('Dubbing', '')}<p class="hv-line">Loading the dub…</p></div>`;
    const tab = UI.dubTab || d.langs?.[0]?.code || '', L = (d.langs || []).find(l => l.code === tab) || {};
    const st = s => s === 'ready' ? 'Ready' : s === 'failed' ? 'Failed' : s === 'waiting' ? 'Waiting' : 'Working';
    return `<div class="hi-wrap wide"><div class="hi-edhead"><button class="hi-btn q ico" data-a="go" data-p="dub" aria-label="Back to Dubbing" title="Back to Dubbing">${ic('back')}</button>
        <h1 class="hi-fill" style="font-family:var(--fr);font-weight:400;font-size:26px">Dubbing</h1>${L.subtitles_id ? `<button class="hi-btn q" data-a="dlraw" data-id="${esc(L.subtitles_id)}" data-val="srt">${ic('down')}Subtitles</button>` : ''}</div>
      <p class="hi-mut">${esc([d.title, d.source_lang ? 'spoken in ' + langLabel(d.source_lang) : '', d.mode === 'own' ? 'their own voices' : 'matched voices'].filter(Boolean).join(' · '))}</p>
      ${d.status === 'failed' ? warnNote(d.error || 'This dub could not be made.') : ''}
      <div class="hv-dubtabs" role="tablist">${(d.langs || []).map(l => `<button class="hi-tab" role="tab" aria-selected="${l.code === tab}" data-a="dubtab" data-val="${esc(l.code)}">${esc(l.name || langLabel(l.code))} · ${st(l.status)}</button>`).join('')}</div>
      <div class="hi-card hi-grid">${L.video_id ? `<video class="hv-media" id="hvDubMedia" controls preload="none" data-src="${esc(L.video_id)}"></video>` : L.audio_id ? `<audio class="hv-media" id="hvDubMedia" controls preload="none" data-src="${esc(L.audio_id)}"></audio>`
        : `<p class="hv-line">${L.status === 'failed' ? 'This language could not be made.' : 'This language is still being made. The page checks every few seconds.'}</p>`}</div>
      <div class="hi-card hi-scroll"><table><thead><tr><th>Time</th><th>Speaker</th><th>Heard</th><th>${esc(L.name || 'Spoken')}</th></tr></thead><tbody>${(d.lines || []).map(r => `<tr><td class="hi-num" style="white-space:nowrap">${secs(r.start)}-${secs(r.end)}</td><td>${esc(r.speaker || '')}</td><td>${esc(r.text || '')}</td><td class="hv-serif" lang="${esc(tab)}">${esc((r.tr || {})[tab] || '')}</td></tr>`).join('') || '<tr><td colspan="4" class="hi-mut">The lines appear when the speech is read.</td></tr>'}</tbody></table></div></div>`;
  }
  async function loadDub(id) {
    try { UI.dub = await api('GET', `${A}/dub/${q(id)}`); } catch (e) { toast(e.message, true); return; }
    if (PAGE !== 'dub' || ARG !== id) return;
    if (!UI.dubTab || !(UI.dub.langs || []).some(l => l.code === UI.dubTab)) UI.dubTab = UI.dub.langs?.[0]?.code || '';
    draw(); dubMedia(); dubPoll(id);
  }
  async function dubMedia() { const m = $('#hvDubMedia'); if (!m) return; try { m.src = await blobUrl(`${A}/audio?id=${q(m.dataset.src)}`); } catch { /* the controls stay, the file comes when ready */ } }
  function dubPoll(id) { clearTimeout(dubPoll.t); if (UI.dub?.status !== 'working') return;
    dubPoll.t = setTimeout(() => { if (PAGE === 'dub' && ARG === id && ROOT && !ROOT.hidden) loadDub(id); }, 3000); }

  // ------------------------------------------------------------------ recording in the browser ---
  const REC = {};
  async function recStart(k) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { toast('This browser cannot record here. Upload a file instead.', true); return; }
    try { const st = await navigator.mediaDevices.getUserMedia({audio: true}), mr = new MediaRecorder(st), parts = [];
      mr.ondataavailable = e => { if (e.data.size) parts.push(e.data); };
      mr.onstop = () => { st.getTracks().forEach(t => t.stop()); const s = (Date.now() - REC[k].t0) / 1000; delete REC[k];
        const blob = new Blob(parts, {type: mr.mimeType || 'audio/webm'}); setCloneFile(k, new File([blob], `${k}.webm`, {type: blob.type}), s); };
      REC[k] = {mr, t0: Date.now()}; mr.start(); draw();
      const tick = () => { const el = $(`[data-rect="${k}"]`); if (!REC[k]) return; if (el) el.textContent = `Recording · ${secs((Date.now() - REC[k].t0) / 1000)}`; setTimeout(tick, 500); }; tick(); }
    catch (e) { toast(`The microphone did not start: ${e.message}`, true); }
  }
  async function setCloneFile(k, file, s) {
    UI.clone[k] = {name: file.name, up: true, secs: s || 0}; draw();
    if (!s) { UI.clone[k].secs = await fileSecs(file); }
    try { UI.clone[k].file_id = await up(file); } catch (e) { UI.clone[k].err = e.message; }
    UI.clone[k].up = false;
    if (k === 'sample' && UI.clone[k].secs && (UI.clone[k].secs < 10 || UI.clone[k].secs > 30)) toast('The best sample is 10 to 30 seconds long.');
    if (PAGE === 'mine') draw();
  }
  async function consentLine(code) {
    if (!code || UI.cline[code]) return;
    try { UI.cline[code] = await api('GET', `${A}/consent-line?lang=${q(code)}`); } catch (e) { UI.cline[code] = {line: '', english: '', lang: ''}; toast(e.message, true); }
    if (PAGE === 'mine') draw();
  }
  // a picked file on a tool page: uploaded at once, its length read for the price
  async function pageFile(k, file) {
    const slot = {name: file.name, up: true};
    const set = (o) => { if (k === 'pod') UI.dlg.pod.file = o; else if (k === 'imp') UI.imp.file = o; else if (k === 'dub') UI.dubNew.file = o; else if (k === 'chg') UI.chg.file = o; else if (k === 'cl') UI.cl.file = o; };
    set(slot); draw();
    const s = ['dub', 'chg', 'cl'].includes(k) ? await fileSecs(file) : 0;
    if (k === 'dub') UI.dubNew.secs = s; if (k === 'chg') UI.chg.secs = s; if (k === 'cl') { UI.cl.secs = s; try { UI.cl.before = URL.createObjectURL(file); } catch { /* no preview */ } }
    try { slot.file_id = await up(file); } catch (e) { slot.err = e.message; toast(e.message, true); }
    slot.up = false; draw();
  }

  // ------------------------------------------------------------------ events ---
  function speechBody() { return {text: S.text, voice: S.voice, lang: S.lang || 'auto', style: S.style, speed: +S.speed, expressive: +S.expressive, takes: +S.takes,
    engine: S.engine, format: S.format, rules: !!S.rules}; }
  function askHoola(text) { C.ask = text; C.autosend = true; go('chat'); }
  function onClick(ev) {
    const b = ev.target.closest('[data-a]'); if (!b || b.disabled || !ROOT.contains(b)) return;
    const d = b.dataset, id = d.id;
    switch (d.a) {
      case 'back': return back ? back() : leave();
      case 'console': leave(); return consoleGo?.(d.val);
      case 'go': return go(d.p, d.arg);
      case 'slim': UI.slim = ROOT.dataset.slim !== '1'; return rail();
      case 'popx': return popClose();
      case 'popv': { const p = POP; popClose(); return p?.o.onPick(d.val); }
      case 'seg': { const v = isNaN(+d.val) || d.val === '' ? d.val : +d.val; setM(d.m, v);
        if (d.m === 'UI.dlg.pod.src' || d.m === 'UI.imp.src' || d.m === 'UI.dlg.style') return draw();
        if (PAGE === 'chat') return refreshSet();
        return draw(); }
      case 'setopen': C.setOpen = !C.setOpen; return refreshSet();
      case 'setdone': C.setOpen = false; return refreshSet();
      case 'setreset': Object.assign(S, {lang: browserLang(), style: Object.keys(D.styles || {})[0] || '', speed: 1, takes: 2, engine: 'auto'}); return refreshSet();
      case 'picklang': { const k = d.k, cur = k === 'dubadd' ? '' : String(k.split('.').reduce((o, x) => o?.[x], MODELS) || '');
        return popOpen(b, {title: 'Language', ph: 'Search 150+ languages', cur, items: langItems(!!d.auto, d.need), onPick: v => {
          if (k === 'dubadd') { if (!UI.dubNew.langs.includes(v)) UI.dubNew.langs.push(v); return draw(); }
          setM(k, v); if (k === 'UI.clone.lang') consentLine(v); if (PAGE === 'chat') return refreshSet(); draw(); }}); }
      case 'pickvoice': return popOpen(b, {title: 'Voice', ph: 'Search: warm, news, Brazilian…', cur: S.voice, items: voiceItems(), onPick: v => { S.voice = v; if (PAGE === 'chat') refreshSet(); else draw(); }});
      case 'dlmenu': return popOpen(b, {title: 'Download as', search: false, cur: '', items: [['wav', 'WAV, studio quality'], ['mp3', 'MP3, small file'], ['flac', 'FLAC, lossless']].map(([v, label]) => ({v, label})), onPick: f => download(id, f)});
      case 'idea': C.ask = d.val; { const ta = $('#hvAsk'); if (ta) { ta.value = d.val; ta.focus(); } } return price('chat', ttsQuote(C.ask));
      case 'ask': return chatSend(d.val);
      case 'askspeech': { const t = ($('#hvAskS')?.value || '').trim(); if (!t) { toast('Say what to change first.'); return $('#hvAskS')?.focus(); }
        return askHoola(`${t}\n\nThe words on the Speech page: ${S.text.slice(0, 3000)}`); }
      case 'askdlg': { const t = ($('#hvAskD')?.value || '').trim(); if (!t) { toast('Say what to change first.'); return $('#hvAskD')?.focus(); }
        return askHoola(`${t}\n\nThe dialogue: ${UI.dlg.lines.map(l => `${l.speaker}: ${l.text}`).join(' / ').slice(0, 3000)}`); }
      case 'plus': return pickFiles('audio/*,video/*,.pdf,.txt,.docx,.epub').then(chatFiles);
      case 'fx': C.files.splice(+d.n, 1); { const t = $('#hvTray'); if (t) { t.innerHTML = trayHTML(); t.hidden = !C.files.length; } } return;
      case 'improve': { const ta = $('#hvAsk'); if (!ta?.value.trim()) { ta?.focus(); toast('Write a few words first.'); return; }
        if (window.HoolaImprove?.ui) return window.HoolaImprove.ui.open(ta.value, {section: 'voice', onUse: t => { C.ask = ta.value = String(t).slice(0, 4000); ta.focus(); toast('Words updated: edit them or send.'); }});
        return api('POST', '/api/prompting/understand', {text: ta.value, section: 'voice'}).then(r => { const t = r?.prompt || r?.text; if (t) { C.ask = ta.value = String(t).slice(0, 4000); toast('Words updated: edit them or send.'); } }).catch(e => toast(e.message, true)); }
      case 'newchat': return api('POST', `${A}/chat/new`).then(c => { C.title = c.title || 'Vocal chat'; return openChat(c.id); }).catch(e => toast(e.message, true));
      case 'chats': return api('GET', `${A}/chats`).then(r => { const cs = r.chats || []; if (!cs.length) return toast('No earlier Vocal chats yet.');
        popOpen(b, {title: 'Earlier Vocal chats', cur: C.conv, items: cs.map(c => ({v: c.id, label: c.title || 'Vocal chat', sub: c.at ? ago(c.at) : ''})), onPick: v => { C.title = (cs.find(x => x.id === v) || {}).title || 'Vocal chat'; openChat(v); }}); }).catch(e => toast(e.message, true));
      case 'direct': { const s = C.lastSend; if (!s) return; b.disabled = true;
        return act(() => api('POST', `${A}/tts`, {text: s.text, voice: s.voice, lang: s.lang || 'auto', style: s.style, speed: +s.speed, expressive: +s.expressive, takes: +s.takes, engine: s.engine, format: s.format, rules: !!s.rules, chat: C.conv}),
          async () => { C.lastSend = null; await chatLoad(false); paintChat(); toast('Made.'); }, b, 'Making…'); }
      case 'tag': { const ta = $('#hvText'); if (!ta) return; const t = `[${d.val}] `, a = ta.selectionStart ?? ta.value.length, z = ta.selectionEnd ?? a;
        ta.value = ta.value.slice(0, a) + t + ta.value.slice(z); S.text = ta.value; ta.focus(); ta.selectionStart = ta.selectionEnd = a + t.length; onInput({target: ta}); return; }
      case 'play': return play(id);
      case 'playa': return blobUrl(`${A}/audio?id=${q(id)}`).then(u => play('', u, 'Voice option')).catch(e => toast(e.message, true));
      case 'playurl': return d.val === 'before' && UI.cl.before ? play('', UI.cl.before, 'Before') : null;
      case 'dlraw': return download(id, d.val);
      case 'keep': { const i = UI.kept.indexOf(id); if (i >= 0) UI.kept.splice(i, 1); else UI.kept.push(id); UI.kept = UI.kept.slice(-500); store.set('hv.kept', UI.kept);
        if (PAGE === 'chat') { $$('[data-vset]').forEach(n => { n._h = ''; }); return drawSets(); } return draw(); }
      case 'closebar': $('#hvAudio').pause(); $('#hvBar').hidden = true; return;
      case 'rmh': return confirm('Remove this from your history? The file is deleted.') && act(() => api('DELETE', `${A}/history?id=${q(id)}`), () => { URLS.forEach((u, k) => { if (k.includes(`id=${q(id)}`)) URLS.delete(k); }); rail(); draw(); });
      case 'hear': { const v = voice(id); b.disabled = true;
        return blobUrl(`${A}/voice/preview?id=${q(id)}&lang=${q(S.lang === 'auto' ? ((v?.langs || [])[0] || 'en') : S.lang)}`).then(u => play('', u, `${v?.name || 'Voice'} · sample`)).catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'usev': S.voice = id; toast(`${vname(id)} is your voice now.`); return go('speech');
      case 'save': { const i = UI.saved.indexOf(id); if (i >= 0) UI.saved.splice(i, 1); else UI.saved.push(id); store.set('hv.saved', UI.saved); return draw(); }
      case 'vtab': UI.vf.tab = d.val; return draw();
      case 'vuse': UI.vf.use = UI.vf.use === d.val ? '' : d.val; return draw();
      case 'rmv': return confirm('Remove this voice? Its recordings are deleted. Sounds already made are kept.') && act(() => api('DELETE', `${A}/voice?id=${q(id)}`));
      case 'rec': return recStart(d.k);
      case 'recstop': return REC[d.k]?.mr.stop();
      case 'dpick': UI.design.pick = d.val; return draw();
      case 'dsave': return act(() => api('POST', `${A}/voice/design/save`, {pid: UI.design.pick, name: UI.design.name || 'My designed voice'}),
        () => { UI.design = {desc: '', gender: '', previews: [], pick: '', name: ''}; toast('Voice saved.'); draw(); }, b, 'Saving…');
      case 'rxchip': UI.remix.change = [UI.remix.change.trim(), d.val.toLowerCase()].filter(Boolean).join(', '); return draw();
      case 'rmrule': return act(() => api('DELETE', `${A}/rule?id=${q(id)}`));
      case 'hist': UI.hist = d.val; return draw();
      case 'lregion': UI.langR = d.val; return draw();
      case 'settab': UI.setTab = d.val; return draw();
      case 'dmode': UI.dlg.mode = d.val; return draw();
      case 'dladd': UI.dlg.lines.push({speaker: UI.dlg.cast[UI.dlg.lines.length % UI.dlg.cast.length]?.name || 'Speaker', text: ''}); draw(); return $(`#hvLt${UI.dlg.lines.length - 1}`)?.focus();
      case 'dlrm': UI.dlg.lines.splice(+d.n, 1); return draw();
      case 'castadd': { const rv = D.voices.filter(v => v.ready); UI.dlg.cast.push({name: `Speaker ${UI.dlg.cast.length + 1}`, voice: (rv[UI.dlg.cast.length % Math.max(1, rv.length)] || {}).id || ''}); return draw(); }
      case 'castrm': { const gone = UI.dlg.cast.splice(+d.n, 1)[0]; UI.dlg.lines.forEach(l => { if (l.speaker === gone.name) l.speaker = UI.dlg.cast[0].name; }); return draw(); }
      case 'dlgmake': { const dd = UI.dlg, cast = Object.fromEntries(dd.cast.map(c => [c.name, c.voice]));
        return act(() => api('POST', `${A}/dialogue`, {lines: dd.lines.filter(l => (l.text || '').trim()).map(l => ({speaker: l.speaker, text: l.text})), cast, lang: dd.lang || 'auto', style: dd.style, engine: 'auto'}),
          r => { draw(); if (r?.id) play(r.id); toast('Ready.'); }, b, 'Speaking…'); }
      case 'impopen': UI.imp.open = true; return draw();
      case 'impclose': UI.imp.open = false; return draw();
      case 'newproj': UI.cast = null; UI.proj = {id: '', title: '', voice: S.voice, lang: S.lang === 'auto' ? 'en' : S.lang, chapters: [{title: 'Chapter 1', text: ''}]}; return go('reading');
      case 'proj': UI.cast = null; UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === id) || null)); return go('reading');
      case 'chadd': UI.proj.chapters.push({title: `Chapter ${UI.proj.chapters.length + 1}`, text: ''}); return draw();
      case 'chrm': UI.proj.chapters.splice(+d.n, 1); return draw();
      case 'saveproj': return saveProj(b).then(ok => ok && toast('Saved.'));
      case 'cast': return saveProj().then(ok => ok && act(() => api('POST', `${A}/project/cast`, {id: UI.proj.id, n: +d.n}), r => { UI.cast = {n: +d.n, ...r}; draw(); }, null));
      case 'readch': return saveProj().then(ok => ok && act(() => api('POST', `${A}/project/chapter`, {id: UI.proj.id, n: +d.n}), r => { UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id) || UI.proj)); draw(); if (r?.id) play(r.id); }, null));
      case 'expmenu': return popOpen(b, {title: 'Export', search: false, cur: '', items: [['m4b', 'Audiobook (M4B with chapters)'], ['mp3', 'MP3'], ['wav', 'WAV, studio quality'], ['srt', 'Captions with times (SRT)']].map(([v, label]) => ({v, label})),
        onPick: f => act(() => api('POST', `${A}/project/export`, {id: UI.proj.id, format: f}), r => { toast('Exported. It is in your history.'); draw(); if (r?.id) download(r.id, f); }, null)});
      case 'rmproj': return confirm('Remove this reading? Sounds already made stay in your history.') && act(() => api('DELETE', `${A}/project?id=${q(id)}`), () => { UI.proj = null; go('studio'); });
      case 'dubrm': UI.dubNew.langs = UI.dubNew.langs.filter(c => c !== d.val); return draw();
      case 'dubopen': UI.dub = null; UI.dubTab = ''; return go('dub', id);
      case 'dubtab': UI.dubTab = d.val; draw(); return dubMedia();
      case 'preset': return act(() => api('POST', `${A}/sfx`, {preset: d.val, seed: +UI.seed || 1}), r => { draw(); const it = r?.items?.[0] || r; if (it?.id) play(it.id); }, b);
    }
  }
  function refreshSet() {           // the chat's settings panel + pill + price, without redrawing the thread
    const p = $('#hvSetp'); if (p) { p.hidden = !C.setOpen; p.innerHTML = C.setOpen ? setPanel() : ''; }
    const s = $('#hvSum'); if (s) s.textContent = summary();
    $('[data-a="setopen"]')?.setAttribute('aria-expanded', String(C.setOpen));
    const btn = $('[data-qbtn="chat"]'), w = speakWhy(S.lang, S.engine), comp = $('.hv-comp');
    comp?.querySelectorAll(':scope > .hv-why').forEach(n => n.remove());
    if (btn) { btn.disabled = !!w; btn.removeAttribute('aria-describedby');
      if (w) { const id = `hvw${++WN}`; btn.setAttribute('aria-describedby', id); comp?.querySelector('.hv-box')?.insertAdjacentHTML('afterend', `<p class="hv-why" id="${id}">${esc(w)}</p>`); } }
    price('chat', ttsQuote(C.ask));
  }
  async function saveProj(btn) {
    const p = UI.proj;
    try { if (btn) btn.disabled = true;
      const cast = UI.cast ? Object.fromEntries((UI.cast.characters || []).map(c => [c.name, c.voice])) : undefined;
      const out = await api('POST', `${A}/project`, {id: p.id, title: p.title, voice: p.voice || S.voice, lang: p.lang, chapters: p.chapters.map(c => ({title: c.title, text: c.text})), ...(cast ? {cast} : {})});
      await load(); UI.proj = JSON.parse(JSON.stringify(out)); rail(); draw(); return true; }
    catch (e) { toast(e.message, true); if (btn?.isConnected) btn.disabled = false; return false; }
  }
  function redrawKeep(t) { const id = t.id, a = t.selectionStart, z = t.selectionEnd; draw(); const n = id && $(`#${id}`);
    if (n) { n.focus(); try { n.setSelectionRange(a, z); } catch { /* not a text box */ } } }
  function onInput(ev) {
    const t = ev.target;
    const rn = /^UI\.dlg\.cast\.(\d+)\.name$/.exec(t.dataset?.m || '');      // a renamed speaker keeps their lines
    if (rn) { const old = UI.dlg.cast[+rn[1]]?.name; UI.dlg.lines.forEach(l => { if (l.speaker === old) l.speaker = t.value; }); }
    if (t.dataset?.m) { setM(t.dataset.m, t.type === 'checkbox' ? t.checked : t.dataset.t === 'num' ? +t.value : t.value);
      $$(`[data-show="${t.dataset.m}"]`).forEach(x => { x.textContent = t.dataset.m.endsWith('speed') ? `${(+t.value).toFixed(2)}x` : (+t.value).toFixed(2); }); }
    if (t.id === 'hvText') { const c = $('#hvCount'); if (c) c.textContent = `${num(t.value.length)} / ${num(D.limits?.characters || 100000)} characters`; price('speech', ttsQuote(S.text)); }
    if (t.id === 'hvAsk') { t.style.height = 'auto'; t.style.height = Math.min(220, t.scrollHeight) + 'px'; price('chat', ttsQuote(C.ask)); }
    if (t.id === 'hvSq') { const s = $('#hvSide'); if (s) { const lo = C.side.toLowerCase(); s.innerHTML = D.history.filter(h => !lo || [h.title, h.voice_name, h.kind, h.lang].join(' ').toLowerCase().includes(lo)).slice(0, 30).map(sndRow).join('') || '<p class="hv-line">Nothing matches.</p>'; } }
    if (t.id === 'hvPopQ') popList(t.value);
    if (t.dataset?.m === 'S.speed' && PAGE === 'chat') { const s = $('#hvSum'); if (s) s.textContent = summary(); }
    if (t.dataset?.m && t.type === 'search' && t.dataset.redraw) { clearTimeout(onInput.t); onInput.t = setTimeout(() => redrawKeep(t), 250); }
    if (t.id === 'hvFx') { const b = $('[data-qbtn="fx"]'); const w = ready('eleven') ? '' : whyNot('eleven'); if (b && !w) { const ok = UI.fx.prompt.trim().length >= 3; if (ok === b.disabled) redrawKeep(t); } }
    if (t.dataset?.m?.startsWith('UI.dlg.lines') && t.tagName === 'TEXTAREA') { const b = $('[data-qbtn="dlg"]'); const has = UI.dlg.lines.some(l => (l.text || '').trim()); if (b && (has === b.disabled) && !speakWhy(UI.dlg.lang, 'auto')) redrawKeep(t); }
  }
  function onChange(ev) {
    const t = ev.target;
    if (t.dataset?.file && t.files?.[0]) { const k = t.dataset.file; if (k === 'sample' || k === 'consent') return setCloneFile(k, t.files[0]); return pageFile(k, t.files[0]); }
    if (t.dataset?.m) {
      if (t.type !== 'text' && t.type !== 'search' && t.tagName !== 'TEXTAREA') setM(t.dataset.m, t.type === 'checkbox' ? t.checked : t.dataset.t === 'num' ? +t.value : t.value);
      if (/^UI\.dlg\.cast\.\d+\.name$/.test(t.dataset.m)) return draw();
      if (t.dataset.redraw && t.type !== 'search') return draw();
      if (t.dataset.m === 'UI.chg.voice') price('chg', {job: 'change', seconds: UI.chg.secs || 60, voice: UI.chg.voice});
    }
    if (t.dataset?.cvoice && UI.cast) { const c = (UI.cast.characters || []).find(x => x.name === t.dataset.cvoice); if (c) c.voice = t.value; }
  }
  function onKey(ev) { if (ev.key === 'Escape') { if (POP) { ev.preventDefault(); popClose(); } else if (C.setOpen && PAGE === 'chat') { C.setOpen = false; refreshSet(); } } }
  function onSubmit(ev) {
    const f = ev.target.closest('form[data-f]'); if (!f) return;
    ev.preventDefault();
    const v = id => ($(id)?.value || '').trim(), btn = ev.submitter || f.querySelector('button:not([type=button])');
    switch (f.dataset.f) {
      case 'chat': return chatSend();
      case 'speech': if (S.text.trim().length < 2) { toast('Type the words to speak.', true); return $('#hvText')?.focus(); }
        return act(() => api('POST', `${A}/tts`, speechBody()), r => { S.out = r.items || []; draw(); if (S.out[0]) play(S.out[0].id); toast(`${S.out.length} take${S.out.length === 1 ? '' : 's'} ready${r.lang_name ? ' · ' + r.lang_name : ''}.`); }, btn, 'Making…');
      case 'clone': { const c = UI.clone;
        return act(() => api('POST', `${A}/voice/clone`, {name: c.name || 'My voice', file_id: c.sample.file_id, consent_file_id: c.consent.file_id, lang: c.lang, consent: c.ok === true}),
          () => { UI.clone = {sample: null, consent: null, name: 'My voice', ok: false, lang: c.lang}; toast('Your voice is ready.'); draw(); }, btn, 'Making…'); }
      case 'design': if (UI.design.desc.trim().length < 8) { toast('Describe the voice in a few more words.', true); return $('#hvDDesc')?.focus(); }
        return act(() => api('POST', `${A}/voice/design`, {description: UI.design.desc, gender: UI.design.gender}), r => { UI.design.previews = r.previews || []; UI.design.pick = ''; draw(); }, btn, 'Making 3 options…');
      case 'remix': if (!UI.remix.change.trim()) { toast('Say what to change.', true); return $('#hvRChange')?.focus(); }
        return act(() => api('POST', `${A}/voice/remix`, {base: UI.remix.base, change: UI.remix.change, name: UI.remix.name || `${vname(UI.remix.base)} · remix`}),
          () => { UI.remix.change = ''; UI.remix.name = ''; toast('Remix ready.'); draw(); }, btn, 'Making…');
      case 'podcast': { const p = UI.dlg.pod, src = p.src === 'file' ? {file_id: p.file?.file_id} : p.src === 'url' ? {url: p.url} : {text: p.text};
        if (!Object.values(src)[0]) { toast(p.src === 'file' ? 'Add the file first.' : p.src === 'url' ? 'Type the web address first.' : 'Paste the text first.', true); return; }
        return act(() => api('POST', `${A}/podcast`, {...src, minutes: Math.max(1, Math.min(15, +p.minutes || 5)), hosts: UI.dlg.cast.slice(0, 2).map(c => ({name: c.name, voice: c.voice})), lang: UI.dlg.lang || 'auto'}),
          r => { UI.dlg.lines = (r.lines || []).map(l => ({speaker: l.speaker, text: l.text})); const names = new Set(UI.dlg.cast.map(c => c.name));
            UI.dlg.lines.forEach(l => { if (!names.has(l.speaker) && UI.dlg.cast.length < 6) { UI.dlg.cast.push({name: l.speaker, voice: (D.voices.find(x => x.ready) || {}).id || ''}); names.add(l.speaker); } });
            UI.dlg.title = r.title || ''; UI.dlg.mode = 'lines'; draw(); toast('The script is ready. Change any line, then make it.'); }, btn, 'Writing…'); }
      case 'dialogue': return;
      case 'import': { const im = UI.imp, src = im.src === 'file' ? {file_id: im.file?.file_id} : im.src === 'url' ? {url: im.url} : {text: im.text};
        if (!Object.values(src)[0]) { toast('Add what to import first.', true); return; }
        return act(() => api('POST', `${A}/project/import`, {...src, title: im.title}), p => { UI.imp = {open: false, src: 'file', url: '', text: '', title: '', file: null}; UI.cast = null; UI.proj = JSON.parse(JSON.stringify(p)); go('reading'); }, btn, 'Importing…'); }
      case 'dub': { const n = UI.dubNew;
        return act(() => api('POST', `${A}/dub`, {file_id: n.file.file_id, langs: n.langs.slice(0, 6), mode: n.mode, keep_sound: !!n.keep}), r => { UI.dubNew = {file: null, langs: [], mode: n.mode, keep: n.keep, secs: 0}; UI.dub = null; go('dub', r.id); }, btn, 'Starting…'); }
      case 'change': return act(() => api('POST', `${A}/change`, {file_id: UI.chg.file.file_id, voice: UI.chg.voice, denoise: !!UI.chg.denoise}), r => { UI.chg.out = r; draw(); if (r?.id) play(r.id); }, btn, 'Changing…');
      case 'cleanup': { const c = UI.cl, prem = ready('eleven');
        return act(() => api('POST', `${A}/cleanup`, {file_id: c.file.file_id, denoise: !!c.denoise, voice: !!c.voice, silence: !!c.silence, level: !!c.level, people: prem && !!c.people, music: prem && !!c.music}),
          r => { UI.cl.out = r; draw(); if (r?.id) play(r.id); toast('Cleaned.'); }, btn, 'Cleaning…'); }
      case 'sfx': return act(() => api('POST', `${A}/sfx`, {prompt: UI.fx.prompt.trim(), seconds: +UI.fx.seconds, loop: !!UI.fx.loop, takes: +UI.fx.takes}), r => { UI.fx.out = r.items || []; draw(); if (UI.fx.out[0]) play(UI.fx.out[0].id); }, btn, 'Making…');
      case 'rule': return act(() => api('POST', `${A}/rule`, {word: v('#hvRWord'), say: v('#hvRSay'), lang: v('#hvRLang')}), null, btn);
    }
  }
  return {open, leave};
};
