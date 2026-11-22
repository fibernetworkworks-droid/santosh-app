/* v0.999.96 HOOLA VOCAL, REDESIGNED (owner: "GO BUILD" on the design canvas claude.ai/artifact/GkVsAZLf4iTSJMUrEjtiuH,
   15 boards; the build contract is docs/HOOLA_VOCAL_REDESIGN.md). Hoola Vocal now sits on the Create Studio frame:
   a 248 px sidebar with the real Hoola mark and four groups (Make, Voices, Tools, Assets) plus the credits card, a
   52 px top bar with the crumb "Vocal · <page>", and every page as a settings panel on the left with its results on
   the sunk stage on the right. The home is the Vocal chat with the Music chat bar docked at the bottom (+, ONE
   settings pill that opens the settings sheet above the box, the engine chip, the wand = Improve, a round send that
   stays grey until there are words) and "Your sounds" beside it.
   Every dropdown is the console menu (HoolaMenu, menu.js); no native select, no bare file input (a button opens a
   hidden picker). Colours are console tokens only (vocal2.css), so Light / Dark / System follow. Prices are in
   credits only and come from /quote, keyed by the job id. No page names a server key. Her text is always esc()'d.
   Everything stands on /api/vocal/*. No data-v attributes inside this page (the console's global [data-v] click
   handler would take them): data-a / data-val / data-p instead.
   window.HoolaVocal(ctx) = the full page (v2.js). window.HoolaVocal.mountSpeech(el, ctx) = the Speech page alone, used
   by Create Studio's Voice tool inside its own frame (one place for speech). */
'use strict';
window.HoolaVocal = function (ctx) {
  const {api, esc, upload, back, go: consoleGo} = ctx;
  const EMBED = ctx.embed || null;
  const A = '/api/vocal';
  let ROOT = null, PAGE = EMBED ? 'speech' : 'chat', ARG = '', D = null, WN = 0, NOW = null;
  const store = {get: (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window: kept for this visit only */ } }};
  // a server line never shows a server key's name on the page
  const scrub = t => String(t ?? '').replace(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:API_)?(?:KEY|TOKEN|SECRET)\b(?:\s+(?:in|on) the server(?:'s)?(?:\s+\.env|\s+settings)?)?/g, 'its key')
    .replace(/\s*\.env\b/g, ' settings');
  const toast = (m, bad) => ctx.toast(scrub(m), bad);
  const DEF = store.get('hv.defaults', {});
  const S = {voice: DEF.voice || '', lang: DEF.lang || '', style: '', speed: 1, expressive: 0.5, takes: DEF.takes || 2, engine: DEF.engine || 'auto',
    format: DEF.fmt || '', rules: true, text: String(ctx.text || ''), out: [], make: 'speech'};
  const C = {conv: '', title: '', rows: [], items: [], turn: null, sending: false, working: false, loading: false, thread: null, files: [],
    lastSend: null, seq: 0, setOpen: false, ask: '', pend: '', autosend: false};
  const UI = {vtab: 'hoola', vf: {q: '', lang: '', gender: '', age: '', accent: '', use: '', sort: 'popular'}, vsel: '',
    lib: {key: '', list: null, more: false, page: 1, ready: true, why: '', busy: false}, tryText: '',
    way: 'record', clone: {sample: null, consent: null, name: 'My voice', ok: false, lang: ''}, cline: {},
    design: {desc: '', gender: '', previews: [], pick: '', name: ''}, remix: {base: '', change: '', name: ''},
    dlg: {mode: 'natural', reactions: false, music: false, podOpen: false, lines: [{speaker: 'Host', text: ''}, {speaker: 'Guest', text: ''}],
      cast: [{name: 'Host', voice: ''}, {name: 'Guest', voice: ''}], lang: '', style: '', title: '', pod: {src: 'file', url: '', text: '', file: null, minutes: 5}},
    proj: null, chN: 0, cast: null, edited: {}, imp: {open: false, src: 'file', url: '', text: '', title: '', file: null},
    dubs: null, dub: null, dubTab: '', dubLines: null, dubNew: {file: null, langs: [], mode: 'matched', keep: true, secs: 0, speakers: 0},
    chg: {file: null, voice: '', denoise: true, secs: 0, out: null},
    cl: {file: null, denoise: true, echo: true, level: true, silence: false, people: false, music: false, secs: 0, out: null, before: ''},
    fx: {prompt: '', seconds: 0, loop: false, takes: 4, out: []}, seed: 1, snd: {tab: 'All', q: ''}, side: {tab: 'All', q: ''},
    dict: {imp: false, text: '', lang: ''}, apps: null, newKey: null, newHook: null, appName: '', hookUrl: '', kept: store.get('hv.kept', []), nav: false, slim: !!store.get('hv.slim', false),
    cw: Math.max(380, +store.get('hv.chatw', 640) || 640), cmode: store.get('hv.chatmode', 'balanced'), peek: false, recent: null, queue: []};

  const NAV = [['Make', [['chat', 'Vocal chat', 'chat'], ['speech', 'Speech', 'speech'], ['dialogue', 'Dialogue', 'dialog'], ['studio', 'Studio', 'book'], ['dub', 'Dubbing', 'dub']]],
    ['Voices', [['voices', 'Voice library', 'lib'], ['mine', 'Your voice', 'me']]],
    ['Tools', [['changer', 'Voice changer', 'change'], ['cleanup', 'Clean-up', 'clean'], ['sfx', 'Sound effects', 'fx']]],
    ['Assets', [['sounds', 'Your sounds', 'sounds'], ['dict', 'Dictionary', 'dict'], ['settings', 'Settings', 'gear']]]];
  const TITLE = Object.fromEntries(NAV.flatMap(g => g[1]).map(([k, n]) => [k, n]));
  TITLE.reading = 'Studio'; TITLE.langs = 'Every language';
  const NAVOF = {reading: 'studio', langs: 'settings'};
  const KIND = {tts: 'Speech', dialogue: 'Dialogue', podcast: 'Dialogue', chapter: 'Studio', book: 'Studio', sfx: 'Sound', cleanup: 'Clean-up',
    change: 'Changed', dub: 'Dub', music: 'Music', isolate: 'Clean-up'};
  const TABS = {All: () => true, Speech: h => h.kind === 'tts', Dialogue: h => h.kind === 'dialogue' || h.kind === 'podcast', Dubs: h => h.kind === 'dub'};
  const MAKE = {speech: 'Speech', dialogue: 'Dialogue', sound: 'Sound effect'};
  const TONES = ['warm', 'whispers', 'laughs', 'excited', 'pause', 'slowly'];
  const ENG = {auto: 'Hoola Auto', gemini: 'Gemini voice', eleven: 'ElevenLabs', lab: 'Hoola GPU lab', server: 'Hoola server'};
  const QUAL = {excellent: 'Excellent', good: 'Good', fair: 'Fair', not_tested: 'Not tested yet', none: 'Not available'};
  const FORMATS = [{id: 'mp3', name: 'MP3', note: 'Small, for sharing'}, {id: 'wav', name: 'WAV', note: 'Studio quality'},
    {id: 'ogg', name: 'OGG', note: 'For WhatsApp'}, {id: 'm4a', name: 'M4A', note: 'For iPhone'}];
  const NO_CR = 'You have no credits left this month, so nothing can be made.';
  const P = {
    chat: 'M4 5h16v11H9l-5 4z', speech: 'M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4', dialog: 'M3 6h11v8H7l-4 3zM10 17h7l4 3V9h-4',
    book: 'M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM8 7h7', dub: 'M4 5h8M8 3v2M5 11c2-1 4-3 5-6M7 8c1 2 3 3 5 3M13 21l4-9 4 9M14.5 18h5',
    lib: 'M4 19V5M9 19V5M14 19l3-14 4 1-3 14z', me: 'M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM6 11a6 6 0 0 0 12 0M12 17v4',
    change: 'M4 12h4l2-5 4 10 2-5h4', clean: 'M4 20l7-7M14 4l6 6-6 6-6-6zM3 14l3 3', fx: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
    sounds: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3zM20 16a3 3 0 1 1-3-3 3 3 0 0 1 3 3z', dict: 'M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3zM8 9h7M8 13h5',
    gear: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19 12l2-1-1-3-2 .5-1.5-1.5.5-2-3-1-1 2h-2l-1-2-3 1 .5 2L6 7.5 4 7 3 10l2 1v2l-2 1 1 3 2-.5 1.5 1.5-.5 2 3 1 1-2h2l1 2 3-1-.5-2 1.5-1.5 2 .5 1-3-2-1z',
    plus: 'M12 5v14M5 12h14', x: 'M6 6l12 12M18 6L6 18', back: 'M15 18l-6-6 6-6', down: 'M6 9l6 6 6-6', up: 'M6 15l6-6 6 6',
    send: 'M12 19V5M6 11l6-6 6 6', wand: 'M4 20L15 9M14 4v3M19 9h-3M18 5l-2 2', clock: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8v4l3 2',
    sliders: 'M4 7h10M18 7h2M4 17h4M12 17h8M16 5v4M10 15v4', side: 'M6 4h12a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM9 4v16',
    menu: 'M4 7h16M4 12h16M4 17h16', fold: 'M9 6l6 6-6 6M19 5v14', search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.5-3.5', upload: 'M12 16V4M7 9l5-5 5 5M5 20h14',
    dl: 'M12 4v12M7 11l5 5 5-5M5 20h14', mic: 'M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM6 11a6 6 0 0 0 12 0M12 17v4',
    check: 'M5 12.5l4.5 4.5L19 7.5', warn: 'M12 7v6M12 17h.01', redo: 'M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7', trash: 'M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13',
    copy: 'M9 9h10v10H9zM5 15V5h10', globe: 'M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zM3.5 12h17M12 3.5c2.5 2.6 3.6 5.4 3.6 8.5s-1.1 5.9-3.6 8.5c-2.5-2.6-3.6-5.4-3.6-8.5s1.1-5.9 3.6-8.5z'};
  const FILLED = {play: '<path d="M8 5v14l11-7z"/>', pause: '<path d="M7 5h4v14H7zM13 5h4v14h-4z"/>', stopf: '<rect x="7" y="7" width="10" height="10" rx="2"/>',
    more: '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>'};
  const ic = (n, s = 16) => FILLED[n] ? `<svg class="hv-i f" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">${FILLED[n]}</svg>`
    : `<svg class="hv-i" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><path d="${P[n] || ''}"/></svg>`;
  const $ = s => ROOT && ROOT.querySelector(s);
  const $$ = s => ROOT ? [...ROOT.querySelectorAll(s)] : [];
  const q = encodeURIComponent;
  const atOf = iso => { if (typeof iso === 'number') return iso > 1e12 ? iso / 1000 : iso; const t = Date.parse(iso || ''); return t ? t / 1000 : 0; };
  const ago = iso => { const t = atOf(iso) * 1000; if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'Just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : m < 2880 ? 'Yesterday' : `${Math.round(m / 1440)} days ago`; };
  const secs = s => { s = Math.round(+s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const num = n => (+n || 0).toLocaleString('en-US');
  const cr = n => `${num(n)} ${+n === 1 ? 'credit' : 'credits'}`;
  const plural = (n, w) => `${num(n)} ${w}${+n === 1 ? '' : 's'}`;
  const strip = t => String(t || '').replace(/(?:\s*\[(?:Web console [^\]\n]*|Vocal settings:[^\]\n]*)\])+\s*$/, '');
  const empty = (h, p, btn = '') => `<div class="hv-empty"><b>${h}</b><span>${p}</span>${btn}</div>`;
  const warnNote = t => `<p class="hv-note warn">${esc(scrub(t))}</p>`;
  // a disabled control always says why, in a line beside it (aria-describedby points at that line)
  const gate = r => { if (!r) return {a: '', l: ''}; const id = `hvw${++WN}`;
    const link = r === NO_CR ? ` <a class="hv-link" href="${esc(D?.credits_page || '/console/?v=credits')}">Get credits</a>` : '';
    return {a: ` disabled aria-describedby="${id}"`, l: `<p class="hv-why" id="${id}">${esc(scrub(r))}${link}</p>`}; };

  // ------------------------------------------------------------------ data ---
  const yn = v => v === true ? 'yes' : (v === false || v == null || v === '') ? 'none' : String(v).toLowerCase();
  function fix(o, L) {
    const d = {voices: [], rules: [], history: [], projects: [], usage: {}, limits: {}, sfx: [], styles: {}, feelings: [], engines: [], prices: [], rules_kept: [], ...o};
    d.status = {engines: {}, connected: {}, ...(o.status || {})};
    d.formats = Array.isArray(o.formats) && o.formats.length ? o.formats : FORMATS;
    d.settings = o.settings && typeof o.settings === 'object' ? o.settings : null;
    d.langs = L.map(l => ({region: '', voices: 0, quality: 'not_tested', native: l.name, ...l, speech: yn(l.speech), clone: yn(l.clone), dialogue: yn(l.dialogue), dub: yn(l.dub)}));
    d.voices = (d.voices || []).map(v => ({gender: '', age: '', tone: '', accent: '', langs: [], use: '', engine: 'gemini', tier: 'standard', kind: 'hoola', ready: true, ...v}));
    return d;
  }
  const eng = id => (D.engines || []).find(e => e.id === id);
  const ready = id => eng(id)?.state === 'ready';
  const engName = id => ENG[id] || eng(id)?.name || id;
  function whyNot(id) {
    const e = eng(id), n = ENG[id] || e?.name || id;
    if (!e) return `${n} is not on this server.`;
    if (e.state === 'off') return `${n} is switched off on this server.`;
    if (e.state !== 'ready') return `${n} is not connected on this server yet.`;
    return '';
  }
  const broke = () => typeof D.usage?.credits_left === 'number' && D.usage.credits_left <= 0;
  const paid = r => r || (broke() ? NO_CR : '');
  const lang = c => D.langs.find(l => l.code === c);
  const langLabel = c => { if (!c || c === 'auto') return 'Auto, from your words'; const l = lang(c); if (!l) return c; return l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name; };
  const short = c => !c || c === 'auto' ? 'Auto' : (lang(c)?.name || c);
  const voice = id => D.voices.find(v => v.id === id);
  const vname = id => voice(id)?.name || 'Hoola Auto';
  const styleName = id => (D.styles || {})[id] || 'Natural';
  const fmtOf = id => D.formats.find(f => f.id === id) || D.formats[0];
  function browserLang() {
    for (const x of (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''])) {
      const lo = String(x || '').toLowerCase(), l = D.langs.find(l => l.code.toLowerCase() === lo) || D.langs.find(l => l.code.toLowerCase() === lo.split('-')[0]);
      if (l && l.speech !== 'none') return l.code;
    }
    return 'auto';
  }
  // why speech cannot be made in this language on this engine (empty = it can)
  function speakWhy(lc, engine) {
    if (!ready('gemini') && !ready('eleven')) return 'No speech engine is connected on this server yet.';
    if (engine === 'eleven' && !ready('eleven')) return whyNot('eleven');
    if (engine === 'gemini' && !ready('gemini')) return whyNot('gemini');
    const l = lang(lc);
    if (l && l.speech === 'none') return `No engine speaks ${l.name} yet. Hoola never reads it in another language instead.`;
    if (l && l.speech === 'premium' && !ready('eleven')) return `${l.name} is spoken only by ElevenLabs, which is not connected on this server yet.`;
    if (l && l.speech === 'premium' && engine === 'gemini') return `${l.name} is spoken only by ElevenLabs. Choose Hoola Auto or ElevenLabs.`;
    return '';
  }
  const URLS = new Map();
  async function blobUrl(path) { if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const u = URL.createObjectURL(await r.blob()); URLS.set(path, u); return u; }
  async function load() {
    try { const o = await api('GET', `${A}/overview`) || {}; D = fix(o, Array.isArray(o.langs) ? o.langs : Object.entries(o.langs || {}).map(([code, name]) => ({code, name}))); }
    catch (e) { D = fix({error: e.message}, []); }
    if (D.settings && !load.took) { load.took = true; const z = D.settings;      // her saved defaults (PUT /settings) start every page
      if (z.lang) S.lang = z.lang; if (z.voice) S.voice = z.voice; if (z.format) S.format = z.format; if (+z.takes) S.takes = +z.takes;
      if (z.engine) S.engine = z.engine; if (z.style) S.style = z.style; }
    if (!S.voice || !D.voices.some(v => v.id === S.voice && v.ready)) S.voice = (D.voices.find(v => v.ready) || {}).id || '';
    if (!S.lang || (S.lang !== 'auto' && !lang(S.lang))) S.lang = browserLang();
    if (!S.style || !(S.style in (D.styles || {}))) S.style = Object.keys(D.styles || {})[0] || '';
    if (!S.format || !D.formats.some(f => f.id === S.format)) S.format = D.formats[0].id;
    if (!UI.dlg.lang) UI.dlg.lang = S.lang;
    if (!UI.clone.lang) UI.clone.lang = S.lang === 'auto' ? 'en' : S.lang;
    const rv = D.voices.filter(v => v.ready);
    UI.dlg.cast.forEach((c, i) => { if (!c.voice || !voice(c.voice)) c.voice = (rv[i % Math.max(1, rv.length)] || {}).id || ''; });
    if (!UI.remix.base) UI.remix.base = S.voice;
    if (!UI.chg.voice || !voice(UI.chg.voice)) UI.chg.voice = (D.voices.find(v => v.engine === 'eleven' && v.ready) || {}).id || '';
  }
  // a price before every paid job: /quote, cached by its body, keyed by the job id it asks about
  const QC = new Map(), QT = {};
  async function quote(body) {
    const k = JSON.stringify(body); if (QC.has(k)) return QC.get(k);
    try { const r = await api('POST', `${A}/quote`, body); QC.set(k, r); return r; } catch (e) { return {credits: null, line: e.message}; }
  }
  function price(key, body, line) {
    clearTimeout(QT[key]);
    QT[key] = setTimeout(async () => {
      const r = await quote(body), btn = $(`[data-qbtn="${key}"]`), ln = $(`[data-qline="${key}"]`);
      if (btn && btn.dataset.label) btn.innerHTML = `${btn.dataset.icon ? ic(btn.dataset.icon) : ''}<span>${esc(btn.dataset.label)}${r.credits != null ? ` · ${cr(r.credits)}` : ''}</span>`;
      if (ln) ln.innerHTML = line ? line(r) : r.credits != null ? `<b class="hv-num">${cr(r.credits)}</b> · nothing is spent until you tap` : esc(scrub(r.line || ''));
    }, 240);
  }
  const ttsQuote = text => ({job: 'tts', chars: (text || '').length, takes: S.takes, voice: S.voice, lang: S.lang || 'auto', engine: S.engine});
  const chatQuote = () => S.make === 'sound' ? {job: 'sfx', seconds: 5, takes: S.takes} : S.make === 'dialogue'
    ? {job: 'dialogue', chars: Math.max(200, C.ask.length), lang: S.lang || 'auto'} : ttsQuote(C.ask || 'x'.repeat(120));
  const autoLine = (r, what) => `${S.engine === 'auto' && r.engine_name ? `Hoola Auto picks ${esc(r.engine_name)}${what ? ' for ' + esc(what) : ''}` : esc(r.engine_name || engName(S.engine))} · nothing is spent until you tap`;

  // ------------------------------------------------------------------ playing + files ---
  async function play(id, src, title) {
    const a = $('#hvAudio'); if (!a) return;
    if (NOW && NOW.id === id && id && !a.paused) { a.pause(); return; }
    try { const u = src || await blobUrl(`${A}/audio?id=${q(id)}`); const h = D.history.find(x => x.id === id) || C.items.find(x => x.id === id) || S.out.find(x => x.id === id);
      NOW = {id, title: title || (h?.title ? h.title + (h.take ? ` · take ${h.take}` : '') : 'Sound')}; const bar = $('#hvBar'); if (bar) bar.hidden = false;
      const n = $('#hvNow'); if (n) n.textContent = NOW.title; a.src = u; await a.play().catch(() => {}); syncPlay(); }
    catch (e) { toast(e.message || 'That sound could not be played.', true); }
  }
  function syncPlay() {
    const a = $('#hvAudio'), on = a && NOW && !a.paused;
    $$('[data-a="play"]').forEach(b => { const me = !!NOW && b.dataset.id === NOW.id && on;
      const want = me ? 'pause' : 'play'; if (b.dataset.st !== want) { b.dataset.st = want; b.innerHTML = ic(want, +b.dataset.s || 14); } });
  }
  async function download(id, fmt, name) {
    const h = D.history.find(x => x.id === id) || C.items.find(x => x.id === id) || S.out.find(x => x.id === id);
    try { const ext = fmt || h?.ext || 'mp3', a = document.createElement('a');
      a.href = await blobUrl(`${A}/audio?id=${q(id)}${fmt ? '&format=' + q(fmt) : ''}`);
      a.download = `${(name || h?.title || 'hoola-vocal').replace(/[^\w .-]+/g, '_').slice(0, 60)}.${ext}`; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); }
  }
  async function saveFile(path, name) {
    try { const a = document.createElement('a'); a.href = await blobUrl(path); a.download = name; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); }
  }
  async function fileSecs(file) {           // how long a picked recording is, read by the browser (0 when it cannot tell)
    return new Promise(res => { try { const u = URL.createObjectURL(file), m = document.createElement(file.type.startsWith('video') ? 'video' : 'audio');
      m.preload = 'metadata'; m.onloadedmetadata = () => { res(isFinite(m.duration) ? m.duration : 0); URL.revokeObjectURL(u); }; m.onerror = () => res(0); m.src = u; setTimeout(() => res(0), 4000); } catch { res(0); } });
  }
  async function up(file) { if (!upload) throw new Error('Files cannot be added here.'); const r = await upload(file); const id = r?.file_id || r?.id; if (!id) throw new Error('The file did not upload.'); return id; }
  // a button opens a hidden picker (never a bare file input on the page)
  function pickFiles(accept, multiple) { return new Promise(res => { const i = document.createElement('input'); i.type = 'file'; i.multiple = !!multiple; i.accept = accept;
    i.className = 'hv-sr'; i.tabIndex = -1; i.onchange = () => { res([...i.files]); i.remove(); }; i.addEventListener('cancel', () => { res([]); i.remove(); });
    (ROOT || document.body).appendChild(i); i.click(); }); }

  // ------------------------------------------------------------------ menus (HoolaMenu) ---
  function menu(anchor, items, opts = {}) { if (window.HoolaMenu) window.HoolaMenu.open(anchor, items, {align: 'start', keyboard: true, ...opts}); else toast('Menus are not ready on this page.', true); }
  // a choice list: [{v, label, sub, why}] -> a menu with a find box, the current one ticked, a "why" row greyed with its reason
  function choose(anchor, {title, find, list, cur, onPick}) {
    const items = [...(title ? [{header: title}] : []), ...(find ? [{search: find, empty: 'Nothing matches'}] : []),
      ...list.map(o => ({label: o.label, sub: scrub(o.why || o.sub || ''), checked: String(o.v) === String(cur), disabled: !!o.why, run: () => onPick(o.v)}))];
    menu(anchor, items, {width: find ? 300 : undefined});
  }
  const langList = (auto, need) => [...(auto ? [{v: 'auto', label: 'Auto, from your words', sub: 'Hoola hears the language of your words'}] : []),
    ...D.langs.map(l => { const k = l[need || 'speech'];
      return {v: l.code, label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name,
        sub: [l.region, k === 'premium' ? 'ElevenLabs' : '', l.voices ? `${l.voices} voices` : ''].filter(Boolean).join(' · '),
        why: k === 'none' ? 'No engine yet' : (k === 'premium' && !ready('eleven') ? 'Needs ElevenLabs, not connected yet' : '')}; })];
  const voiceList = filt => D.voices.filter(filt || (() => true)).map(v => ({v: v.id, label: v.name,
    sub: [v.tone, (v.langs || []).map(c => lang(c)?.name || c).slice(0, 3).join(', '), v.tier === 'premium' ? 'Premium' : ''].filter(Boolean).join(' · '),
    why: v.ready ? '' : (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'Not ready yet')}));
  const engList = () => [{v: 'auto', label: 'Hoola Auto', sub: 'The best engine for each job and language'},
    {v: 'gemini', label: 'Gemini voice', sub: 'Standard', why: ready('gemini') ? '' : whyNot('gemini')},
    {v: 'eleven', label: 'ElevenLabs', sub: 'Premium', why: ready('eleven') ? '' : whyNot('eleven')}];
  const dlItems = (id, name) => [{header: 'Download as'}, ...D.formats.map(f => ({label: f.name, sub: f.note || '', run: () => download(id, f.id, name)}))];

  // ------------------------------------------------------------------ shell ---
  const markSvg = () => window.HoolaMark ? HoolaMark.svg() : '<img src="/static/hoola-mark.png" alt="" width="26" height="26">';
  function cssHref() { const s = document.querySelector('script[src*="/vocal.js"]')?.getAttribute('src') || ''; return `/static/console/vocal2.css${s.includes('?') ? s.slice(s.indexOf('?')) : ''}`; }
  function mount() {
    if (ROOT) { ROOT.hidden = false; return; }
    ROOT = document.createElement('div'); ROOT.id = 'hvRoot'; ROOT.className = EMBED ? 'hv hv-embed' : 'hv';
    ROOT.setAttribute('aria-label', 'Hoola Vocal');
    ROOT.innerHTML = EMBED
      ? `<link rel="stylesheet" href="${esc(cssHref())}"><div class="hv-main"><main class="hv-view" id="hvView"></main>${barHTML()}</div>`
      : `<aside class="hv-side" id="hvSide" aria-label="Hoola Vocal pages"></aside><div class="hv-scrim" data-a="navoff" aria-hidden="true"></div>
      <div class="hv-main"><header class="hv-top"><button type="button" class="hv-ib hv-menu" data-a="navon" aria-label="Open the menu">${ic('menu', 18)}</button>
        <div class="hv-crumb" id="hvCrumb"></div><span class="hv-grow"></span><div class="hv-topr" id="hvTopR"></div></header><main class="hv-view" id="hvView"></main>${barHTML()}</div>`;
    (EMBED || document.body).appendChild(ROOT);
    ROOT.addEventListener('click', onClick); ROOT.addEventListener('input', onInput);
    ROOT.addEventListener('change', onChange); ROOT.addEventListener('submit', onSubmit);
    ROOT.addEventListener('keydown', onKey);
    ROOT.addEventListener('pointerdown', e => { if (C.setOpen && PAGE === 'chat' && !e.target.closest('#hvSetp, [data-a="setopen"]')) { C.setOpen = false; refreshSet(); } });
    const a = $('#hvAudio'); ['play', 'pause', 'ended'].forEach(k => a.addEventListener(k, syncPlay));
    a.addEventListener('ended', () => { const n = UI.queue.shift(); if (n) play(n); });          // Compare: the takes one after another
    a.addEventListener('pause', () => { if (!a.ended) UI.queue = []; });
    ROOT.addEventListener('pointerdown', dragStart); ROOT.addEventListener('pointermove', dragMove);
    ROOT.addEventListener('pointerup', dragEnd); ROOT.addEventListener('pointercancel', dragEnd);
    ROOT.addEventListener('dblclick', e => { if (e.target.closest('[data-drag="chatw"]')) setWidth('balanced'); });
  }
  const barHTML = () => `<div class="hv-bar" id="hvBar" hidden><span class="hv-tile s">${ic('speech', 14)}</span><b id="hvNow"></b><audio id="hvAudio" controls preload="none"></audio>
    <button type="button" class="hv-ib" data-a="closebar" aria-label="Close the player">${ic('x')}</button></div>`;
  async function open() { mount(); await load(); go(PAGE, ARG); }
  function leave() { if (ROOT) { $('#hvAudio')?.pause(); window.HoolaMenu?.close(); ROOT.hidden = true; } clearTimeout(chatPoll.t); clearTimeout(dubPoll.t); Object.values(REC).forEach(r => r.mr.stop()); }
  function creditCard() {
    const u = D.usage || {}, used = +u.credits_used || +u.credits || 0, left = u.credits_left;
    if (typeof left === 'number') { const tot = Math.max(1, left + used), pct = Math.round(used / tot * 100);
      return `<div class="hv-cred"><div class="r"><span>This month</span><b class="hv-num">${num(left)} credits left</b></div>
        <div class="hv-meter" aria-hidden="true"><i style="width:${Math.min(100, Math.max(used ? 1 : 0, pct))}%"></i></div><span class="hv-num">${num(used)} of ${num(left + used)} used · ${pct}%</span></div>`; }
    return `<div class="hv-cred"><div class="r"><span>This month</span><b class="hv-num">${cr(used)} used</b></div><span>The price shows before every job</span></div>`;
  }
  function side() {
    if (EMBED) return;
    const on = NAVOF[PAGE] || PAGE;
    ROOT.classList.toggle('hv-slim', UI.slim); ROOT.classList.toggle('hv-navon', UI.nav);
    const row = ([id, n, i]) => `<button type="button" class="hv-nv" data-a="go" data-p="${id}" title="${n}"${id === on ? ' aria-current="page"' : ''}>${ic(i)}<span>${n}</span></button>`;
    $('#hvSide').innerHTML = `<div class="hv-brand"><span class="hv-mark" aria-hidden="true">${markSvg()}</span><b>Hoola</b><span class="hv-badge">Vocal</span><span class="hv-grow"></span>
        <button type="button" class="hv-ib" data-a="slim" aria-label="${UI.nav ? 'Close the menu' : UI.slim ? 'Open the sidebar' : 'Close the sidebar'}" title="${UI.slim ? 'Open the sidebar' : 'Close the sidebar'}">${ic('side', 18)}</button></div>
      <button type="button" class="hv-nv" data-a="back" title="Back to chat">${ic('back')}<span>Back to chat</span></button>
      <button type="button" class="hv-newchat" data-a="newchat" title="New vocal chat">${ic('plus')}<span>New vocal chat</span></button>
      ${NAV.map(([g, rows]) => `<span class="hv-gh">${g}</span>${rows.map(row).join('')}`).join('')}
      ${(UI.recent || []).filter(c => c.id !== C.conv).length ? `<span class="hv-gh">Recent chats</span>${UI.recent.filter(c => c.id !== C.conv).slice(0, 3).map(c => `<button type="button" class="hv-nv hv-rc" data-a="openchat" data-id="${esc(c.id)}" title="${esc(c.title || 'Vocal chat')}"${PAGE === 'chat' && c.id === C.conv ? ' aria-current="true"' : ''}>${ic('chat')}<span>${esc(c.title || 'Vocal chat')}</span></button>`).join('')}` : ''}
      <span class="hv-grow"></span>${creditCard()}`;
  }
  function crumb() {
    if (EMBED) return;
    const c = $('#hvCrumb'); if (!c) return;
    const p = PAGE === 'reading' && UI.proj ? ['Studio', UI.proj.title || 'New reading'] : PAGE === 'dub' && ARG && UI.dub ? ['Dubbing', UI.dub.title || 'Dub']
      : PAGE === 'chat' ? [C.title && C.title !== 'Vocal chat' ? C.title : 'Vocal chat'] : [TITLE[PAGE] || ''];
    c.innerHTML = `<span>Vocal ·${p.length > 1 ? ' ' + esc(p[0]) + ' ·' : ''}</span><h1 class="hv-h" id="hvCTitle">${esc(p[p.length - 1])}</h1>`;
    topTools();
  }
  // the chat page's tools in the top bar: how wide the chat is, earlier chats, a new chat
  const WIDTHS = [['narrow', 'Narrow', 460], ['balanced', 'Balanced', 640], ['wide', 'Wide', 880], ['chat', 'Chat only', 0]];
  const widthNow = () => UI.cmode === 'chat' || folded() ? 'chat' : UI.cw < 550 ? 'narrow' : UI.cw > 760 ? 'wide' : 'balanced';
  function topTools() {
    const t = $('#hvTopR'); if (!t) return;
    t.innerHTML = PAGE !== 'chat' ? '' : `<button type="button" class="hv-sndbtn" data-a="go" data-p="sounds" aria-label="Your sounds${D?.history?.length ? ', ' + plural(D.history.length, 'sound') : ''}">${ic('sounds', 17)}${D?.history?.length ? `<span class="hv-cnt on">${num(D.history.length)}</span>` : ''}</button><div class="hv-widths" role="group" aria-label="Chat width">${WIDTHS.map(([k, l]) =>
        `<button type="button" data-a="cwidth" data-val="${k}" aria-pressed="${widthNow() === k}">${l}</button>`).join('')}</div>
      <button type="button" class="hv-ib" data-a="chats" aria-label="Earlier chats" title="Earlier chats">${ic('clock', 18)}</button>
      <button type="button" class="hv-ib" data-a="newchat" aria-label="New chat" title="New chat">${ic('plus', 18)}</button>`;
  }
  function go(page, arg) {
    window.HoolaMenu?.close();
    PAGE = V[page] ? page : 'chat'; if (EMBED && PAGE !== 'speech') PAGE = 'speech';
    ARG = arg || ''; UI.nav = false; C.setOpen = false; side(); crumb(); draw();
    const v = $('#hvView'); if (v) { v.scrollTop = 0; v.classList.remove('hv-enter'); void v.offsetWidth; v.classList.add('hv-enter'); clearTimeout(go.t); go.t = setTimeout(() => v.classList.remove('hv-enter'), 700); }
    ENTER[PAGE]?.();
  }
  function draw() { WN = 0; $('#hvView').innerHTML = V[PAGE](); if (EMBED && !$('#hvView h1')) $('#hvView').insertAdjacentHTML('afterbegin', '<h1 class="hv-sr">Speech</h1>'); AFTER[PAGE]?.(); syncPlay(); }
  async function act(fn, done, btn, txt) {
    const was = btn?.innerHTML; if (btn) { btn.disabled = true; if (txt) btn.textContent = txt; }
    try { const r = await fn(); await load(); if (done) done(r); else { side(); draw(); } }
    catch (e) { toast(e.message || 'That did not work.', true); if (btn?.isConnected) { btn.disabled = false; btn.innerHTML = was; } noCredit(e); }
  }
  // a 402 from a paid route = no credits left: every paid button then says so, with the link to Credits
  function noCredit(e) { if (e?.status !== 402 || !D) return; D.usage = {...(D.usage || {}), credits_left: 0}; side(); draw(); }
  // a model binding: <input data-m="S.speed" data-t="num"> keeps the page state as she types, so a redraw keeps her words
  const MODELS = {S, UI, C};
  const getM = path => path.split('.').reduce((o, k) => o?.[k], MODELS);
  function setM(path, v) { const p = path.split('.'); let o = MODELS[p.shift()]; while (p.length > 1) { const k = p.shift(); o = o[k]; if (o == null) return; } o[p[0]] = v; }

  // ------------------------------------------------------------------ pieces ---
  const seg = (path, list, cur, gateOf, label) => `<div class="hv-seg" role="radiogroup"${label ? ` aria-label="${esc(label)}"` : ''}>${list.map(([v, l]) => { const g = gate(gateOf ? gateOf(v) : '');
    return `<button type="button" role="radio" aria-checked="${String(v) === String(cur)}" data-a="seg" data-m="${path}" data-val="${esc(String(v))}"${g.a}>${esc(l)}</button>${g.l}`; }).join('')}</div>`;
  const chipSeg = (path, list, cur, label) => `<div class="hv-chips" role="radiogroup"${label ? ` aria-label="${esc(label)}"` : ''}>${list.map(([v, l]) =>
    `<button type="button" class="hv-chip" role="radio" aria-checked="${String(v) === String(cur)}" data-a="seg" data-m="${path}" data-val="${esc(String(v))}">${esc(l)}</button>`).join('')}</div>`;
  const dd = (label, a, k, value, extra = '') => { const id = `hvdl${++WN}`;
    return `<div class="hv-fld"><span class="hv-lab" id="${id}">${label}</span><button type="button" class="hv-dd" data-a="${a}" data-k="${k}" aria-haspopup="menu" aria-describedby="${id}"${extra}><span>${esc(value)}</span>${ic('down', 14)}</button></div>`; };
  const check = (path, label, on, g = {a: '', l: ''}) => `<label class="hv-check"><input type="checkbox" data-m="${path}" data-t="bool"${on ? ' checked' : ''}${g.a}><span>${label}</span></label>${g.l}`;
  const wave = (id, n = 46, cls = '') => { let h = [...String(id || 'x')].reduce((a, ch) => (a * 33 + ch.charCodeAt(0)) >>> 0, 5); const out = [];
    for (let i = 0; i < n; i++) { h = (h * 1103515245 + 12345) >>> 0; out.push(4 + (h % 15)); } return `<span class="hv-wave ${cls}" aria-hidden="true">${out.map(x => `<i style="height:${x}px"></i>`).join('')}</span>`; };
  const kept = id => UI.kept.includes(id);
  const initial = n => esc(String(n || '?').replace(/<[^>]*>/g, '').trim().slice(0, 1).toUpperCase() || '?');
  const playBtn = (id, label, s = 14, cls = '') => `<button type="button" class="hv-play${cls}" data-a="play" data-id="${esc(id)}" data-s="${s}" aria-label="${esc(label)}">${ic('play', s)}</button>`;
  // a take on a tool page's stage: play, name + state, waveform, length, then Use this take / Download / Change it
  function takeCard(it, i, more = true) {
    const L = it.take || String.fromCharCode(65 + i), on = kept(it.id);
    return `<article class="hv-card hv-takecard"><div class="hv-takeh">${playBtn(it.id, `Play take ${L}`, 14, ' l')}
        <div class="hv-tk"><span class="hv-tn"><b>Take ${esc(L)}</b><span class="hv-st${on ? ' ok' : ''}">${on ? 'Kept' : 'Ready'}</span></span>${wave(it.id, 60)}</div>
        <span class="hv-len hv-num">${it.seconds ? secs(it.seconds) : ''}</span></div>
      <div class="hv-acts"><button type="button" class="hv-btn" data-a="keep" data-id="${esc(it.id)}" aria-pressed="${on}">${on ? 'Kept' : 'Use this take'}</button>
        <button type="button" class="hv-btn" data-a="dlmenu" data-id="${esc(it.id)}" aria-haspopup="menu">Download${ic('down', 12)}</button>
        ${canDub(it) ? `<button type="button" class="hv-btn" data-a="dubit" data-id="${esc(it.id)}" aria-haspopup="menu">${ic('globe', 13)}Dub it</button>` : ''}
        ${more && !EMBED ? `<button type="button" class="hv-btn" data-a="askabout" data-id="${esc(it.id)}">Change it in the chat</button>` : ''}</div></article>`;
  }
  // Dub it: a speech or dialogue take spoken again in another language, same voice(s); the price is asked first
  const canDub = it => (it.kind === 'tts' || it.kind === 'dialogue' || (!it.kind && it.voice)) && (ready('gemini') || ready('eleven'));
  function dubIt(b, id) {
    const it = S.out.find(x => x.id === id) || D.history.find(x => x.id === id) || C.items?.find?.(x => x.id === id); if (!it) return;
    const from = it.lang || '';
    return choose(b, {title: 'Dub it into', find: 'Search languages', cur: '', list: langList(false, it.kind === 'dialogue' ? 'dialogue' : 'speech').filter(l => l.v !== from), onPick: async v => {
      const qr = await quote({job: it.kind === 'dialogue' ? 'dialogue' : 'tts', chars: (it.text || it.title || '').length || 120, takes: 1, voice: it.voice || '', lang: v});
      if (!confirm(`Speak “${it.title || 'this take'}” in ${short(v)}, in the same voice${it.kind === 'dialogue' ? 's' : ''}?${qr.credits != null ? ` About ${cr(qr.credits)}.` : ''}`)) return;
      act(() => api('POST', `${A}/take/${q(id)}/dub`, {langs: [v], chat: PAGE === 'chat' ? (C.conv || '') : ''}), r => {
        const made = r?.items || []; if (PAGE === 'speech' && made.length) S.out = [...made, ...S.out].slice(0, 8);
        side(); if (PAGE === 'chat') { chatLoad(false).then(paintChat); refreshSide(); } else draw();
        if (made[0]) play(made[0].id); (r?.failed || []).forEach(f => toast(`${f.name}: ${f.why}`, true)); if (made.length) toast(`Ready in ${short(v)}.`); }, b, 'Dubbing…'); }});
  }
  function soundCard(h) {
    const meta = [h.lang ? short(h.lang) : '', h.voice_name, h.ext ? String(h.ext).toUpperCase() : ''].filter(Boolean).join(' · ');
    return `<article class="hv-card hv-snd"><div class="hv-sndh"><span class="hv-badge">${esc(KIND[h.kind] || 'Sound')}</span><span class="hv-mut hv-sm">${esc(ago(h.made))}</span><span class="hv-grow"></span>
        <button type="button" class="hv-ib s" data-a="sndmenu" data-id="${esc(h.id)}" aria-label="More for ${esc(h.title || 'this sound')}: download, remove">${ic('more')}</button></div>
      <b class="hv-sndt">${esc(h.title || KIND[h.kind] || 'Sound')}</b><span class="hv-mut hv-sm hv-sndm">${esc(meta || ' ')}</span>
      <div class="hv-sndp">${playBtn(h.id, `Play ${h.title || 'this sound'}`, 12, ' s')}${wave(h.id, 34, 'thin')}<span class="hv-len hv-num">${h.seconds ? secs(h.seconds) : ''}</span></div></article>`;
  }
  function voiceCard(v) {
    return `<article class="hv-card hv-snd"><div class="hv-sndh"><span class="hv-badge">Voice</span><span class="hv-mut hv-sm">${esc(ago(v.made || v.consent_at))}</span></div>
      <b class="hv-sndt">${esc(v.name)}</b><span class="hv-mut hv-sm hv-sndm">${esc(v.kind === 'clone' ? 'Recorded · consent kept' : v.kind === 'design' ? 'Described in words' : v.kind === 'remix' ? 'Changed from a voice' : 'Yours')}</span>
      <div class="hv-sndp"><button type="button" class="hv-play s" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>${wave(v.id, 34, 'thin')}</div></article>`;
  }
  function soundsList(f) {
    const lo = f.q.trim().toLowerCase();
    if (f.tab === 'Voices') return D.voices.filter(v => v.kind !== 'hoola' && (!lo || v.name.toLowerCase().includes(lo))).map(voiceCard);
    return D.history.filter(h => (TABS[f.tab] || TABS.All)(h) && (!lo || [h.title, h.voice_name, KIND[h.kind], h.lang].join(' ').toLowerCase().includes(lo))).map(soundCard);
  }
  const tabsRow = (key, cur, list) => `<div class="hv-tabs" role="tablist" aria-label="Show">${list.map(t => `<button type="button" role="tab" aria-selected="${t === cur}" data-a="tab" data-k="${key}" data-val="${t}">${t}</button>`).join('')}</div>`;
  const search = (id, model, ph, val) => `<label class="hv-search"><span class="hv-sr">${esc(ph)}</span>${ic('search', 14)}<input id="${id}" type="search" data-m="${model}" placeholder="${esc(ph)}" value="${esc(val)}" autocomplete="off"></label>`;

  // ------------------------------------------------------------------ the Vocal chat ---
  const summary = () => `${MAKE[S.make]} · ${short(S.lang)}${S.make === 'sound' ? '' : ' · ' + vname(S.voice)} · ${plural(S.takes, 'take')}`;
  const settingsNote = () => `[Vocal settings: make ${S.make}; language ${S.lang || 'auto'}; voice ${S.voice || 'auto'}; style ${S.style || 'auto'}; speed ${+(+S.speed).toFixed(2)}; takes ${S.takes}; engine ${S.engine}]`;
  const pillAv = () => S.make === 'sound' ? ic('fx', 14) : initial(vname(S.voice));
  const engShort = () => ({auto: 'Auto', gemini: 'Gemini', eleven: 'ElevenLabs'}[S.engine] || 'Auto');
  const chatWhy = () => paid(S.make === 'sound' ? (ready('eleven') ? '' : whyNot('eleven')) : speakWhy(S.lang, S.engine));
  function setPanel() {
    const l = chatWhy(), snd = S.make === 'sound';
    const row = (label, body) => `<div class="hv-sr2"><span class="hv-sl">${label}</span><div class="hv-sc">${body}</div></div>`;
    return `<div class="hv-sheeth"><b id="hvSetT">Vocal settings</b><button type="button" class="hv-lnk" data-a="setreset">Reset</button></div>
      ${row('Make', seg('S.make', Object.entries(MAKE), S.make, null, 'Make'))}
      ${row('Language', `<button type="button" class="hv-dd s" data-a="picklang" data-k="S.lang" data-auto="1" aria-haspopup="menu"><span>${esc(langLabel(S.lang))}</span>${ic('down', 14)}</button>`)}
      ${snd ? '' : row('Voice', `<button type="button" class="hv-dd s" data-a="pickvoice" data-k="S.voice" aria-haspopup="menu"><span>${esc(vname(S.voice))}</span>${ic('down', 14)}</button>`)}
      ${!snd && Object.keys(D.styles || {}).length ? row('Style', chipSeg('S.style', Object.entries(D.styles), S.style, 'Style')) : ''}
      ${snd ? '' : row('Speed', `<input type="range" min="0.7" max="1.3" step="0.05" value="${S.speed}" data-m="S.speed" data-t="num" aria-label="Speed"><span class="hv-num hv-mut" data-show="S.speed">${(+S.speed).toFixed(2)}x</span>`)}
      ${row('Takes', seg('S.takes', [[1, '1'], [2, '2'], [4, '4']], S.takes, null, 'Takes'))}
      ${row('Engine', seg('S.engine', [['auto', 'Hoola Auto'], ['gemini', 'Gemini voice'], ['eleven', 'ElevenLabs']], S.engine, v => v === 'auto' ? '' : (ready(v) ? '' : whyNot(v)), 'Engine'))}
      ${l ? `<p class="hv-why">${esc(scrub(l))}</p>` : ''}
      <div class="hv-sheetf"><span data-qline="chatset"></span><button type="button" class="hv-done" data-a="setdone">Done</button></div>`;
  }
  const trayHTML = () => C.files.map((f, i) => `<span class="hv-file" role="listitem">${ic('sounds', 14)}<span>${esc(f.name)}</span>${f.up ? '<small>Uploading…</small>' : f.err ? `<small class="bad">${esc(f.err)}</small>` : ''}
    <button type="button" class="hv-ib s" data-a="fx" data-n="${i}" aria-label="Remove ${esc(f.name)}">${ic('x', 14)}</button></span>`).join('');
  function composer() {
    const w = chatWhy(), stop = C.working && !C.sending, g = gate(stop ? '' : w), on = !!C.ask.trim();
    return `<div class="hv-comp" id="hvComp"><div class="hv-sheet" id="hvSetp" role="dialog" aria-labelledby="hvSetT"${C.setOpen ? '' : ' hidden'}>${C.setOpen ? setPanel() : ''}</div>
      <form class="hv-box" data-f="chat"><div class="hv-tray" id="hvTray" role="list" aria-label="Files to send"${C.files.length ? '' : ' hidden'}>${trayHTML()}</div>
        <label class="hv-sr" for="hvAsk">Message to Hoola Vocal</label>
        <textarea id="hvAsk" rows="2" maxlength="4000" data-m="C.ask" placeholder="Say what to make, or ask for a change...">${esc(C.ask)}</textarea>
        <div class="hv-boxrow"><button type="button" class="hv-plus" data-a="plus" aria-label="Add a recording, a document or a video" title="Add a recording, a document or a video">${ic('plus')}</button>
          <button type="button" class="hv-setpill" data-a="setopen" aria-haspopup="dialog" aria-expanded="${C.setOpen}" aria-controls="hvSetp"><span class="hv-av" id="hvAv" aria-hidden="true">${pillAv()}</span><span id="hvSum">${esc(summary())}</span>${ic(C.setOpen ? 'down' : 'up', 12)}</button>
          <button type="button" class="hv-engchip" data-a="pickengine" data-k="S.engine" aria-haspopup="menu" aria-label="Engine: ${esc(engName(S.engine))}">${ic('speech', 14)}<span id="hvEng">${engShort()}</span></button>
          <span class="hv-grow"></span>
          <button type="button" class="hv-ib" data-a="improve" aria-label="Improve what I wrote" title="Improve what I wrote">${ic('wand', 17)}</button>
          <button class="hv-send${on || stop ? ' on' : ''}${stop ? ' stop' : ''}" data-qbtn="chat" aria-label="${stop ? 'Stop' : 'Send'}" title="${stop ? 'Stop' : 'Send'}"${g.a}>${ic(stop ? 'stopf' : 'send')}</button></div></form>
      ${g.l}<p class="hv-foot" data-qline="chat">The price shows here before you send · nothing is spent until you send</p></div>`;
  }
  const chatLine = r => r.credits != null ? `About <b class="hv-num">${cr(r.credits)}</b> for ${plural(S.takes, 'take')} · nothing is spent until you send` : esc(scrub(r.line || ''));
  function stageSounds(f, key) {
    const list = soundsList(f), side = key === 'side';
    const tabs = tabsRow(key, f.tab, ['All', 'Speech', 'Dialogue', 'Dubs', 'Voices']), find = search(side ? 'hvSq' : 'hvSnq', `UI.${key}.q`, 'Search', f.q);
    return `<div class="hv-stageh${side ? ' two' : ''}">${side ? `<div class="hv-str"><b>Your sounds</b>${D.history.length ? `<span class="hv-cnt">${num(D.history.length)}</span>` : ''}<span class="hv-grow"></span>
          <button type="button" class="hv-ib" data-a="cwidth" data-val="chat" aria-label="Fold Your sounds away" title="Fold Your sounds away">${ic('fold', 18)}</button></div>
        <div class="hv-str">${tabs}<span class="hv-grow"></span>${find}</div>` : `<b>Your sounds</b><span class="hv-grow"></span>${tabs}${find}`}</div>
      <div class="hv-stageb"><div class="hv-sgrid" id="hvSndGrid">${list.slice(0, side ? 30 : 300).join('') || `<p class="hv-mut">${f.q ? 'Nothing matches.' : 'Nothing yet. What you make appears here.'}</p>`}</div></div>`;
  }
  // the chat is as wide as she wants: drag the line, pick a width, or fold Your sounds away (remembered on this computer)
  const STARTERS = [['ES', 0, 'A shop welcome in Spanish', '“¡Bienvenidos! Pan recién horneado todos los días.”', 'A 10 second welcome for my bakery, in Spanish, warm and friendly'],
    ['AR', 1, 'A bedtime story in Arabic', 'A calm voice, slow, with a soft ending.', 'A short bedtime story in Arabic, calm and slow, with a soft ending'],
    ['2', 2, 'A two-host podcast intro', 'Two voices, small reactions, soft music under it.', 'A two-host podcast intro in English, two voices, with small reactions and soft music'],
    ['FX', 3, 'A sound effect', 'Rain on a tin roof, ten seconds, loops cleanly.', 'Rain on a tin roof, ten seconds, that loops cleanly']];
  const folded = () => UI.cmode === 'chat' || (!(D?.history || []).length && !UI.peek);
  const fresh = () => !C.rows.some(r => r.role === 'user') && !C.pend && !C.items.length;
  function hero() {
    return `<div class="hv-hero"><span class="hv-heromark" aria-hidden="true">${markSvg()}</span>
      <h2 class="hv-heroh">What should Hoola say today?</h2>
      <p class="hv-herop">A welcome, an ad, a story, a podcast for two or a sound, in any of ${D.langs.length ? num(D.langs.length) : 'the world’s'} languages. You hear the takes before anything is kept.</p>
      ${composer()}
      <div class="hv-starts">${STARTERS.map(([t, n, h, l, ask]) => `<button type="button" class="hv-start" data-a="idea" data-val="${esc(ask)}">
        <span class="hv-stt t${n}" aria-hidden="true">${t}</span><span class="hv-stw"><b>${esc(h)}</b><span>${esc(l)}</span></span></button>`).join('')}</div></div>`;
  }
  const railHTML = () => { const n = (D.history || []).length;
    return `<button type="button" class="hv-rail" data-a="unfold" aria-label="Open Your sounds${n ? `, ${plural(n, 'sound')}` : ', nothing yet'}" title="Open Your sounds">${ic('sounds', 18)}${n ? `<span class="hv-cnt on">${num(n)}</span>` : ''}<span class="hv-railt">Your sounds</span></button>`; };
  const splitHTML = () => `<div class="hv-splith" role="separator" tabindex="0" aria-orientation="vertical" aria-label="Chat width: drag, or use the arrow keys. Double-click to reset."
      aria-valuemin="380" aria-valuemax="1400" aria-valuenow="${UI.cw}" data-drag="chatw"><span></span></div>`;
  const stageHTML = () => folded() ? railHTML() : `<section class="hv-stage" id="hvStage" aria-label="Your sounds">${splitHTML()}${stageSounds(UI.side, 'side')}</section>`;
  function chatView() {
    const f = fresh();
    return `<div class="hv-split hv-chatpage${folded() ? ' hv-folded' : ''}" id="hvSplit" style="--hv-cw:${UI.cw}px"><section class="hv-chat${f ? ' hv-fresh' : ''}" aria-label="Vocal chat">
        <div class="hv-log" id="hvLog">${D.error ? warnNote('Hoola Vocal could not load: ' + D.error) : ''}
          ${f ? hero() : ''}<div class="hv-thin"><div id="hvThread"></div><div id="hvFail"></div></div></div>
        ${f ? '' : composer()}</section>${stageHTML()}</div>`;
  }
  // width + fold applied in place: the thread, her typing and the player are never redrawn
  function layout() {
    const sp = $('#hvSplit'); if (!sp) return;
    sp.style.setProperty('--hv-cw', UI.cw + 'px');
    const f = folded(); sp.classList.toggle('hv-folded', f);
    if (f === !!$('#hvStage')) { $$('#hvSplit > :is(.hv-splith,.hv-stage,.hv-rail)').forEach(n => n.remove()); sp.insertAdjacentHTML('beforeend', stageHTML()); syncPlay(); }
    const h = $('.hv-splith'); if (h) h.setAttribute('aria-valuenow', String(UI.cw));
    topTools();
  }
  function setWidth(k, w) {
    if (k === 'chat') UI.cmode = 'chat';
    else { UI.cmode = 'open'; UI.peek = true; UI.cw = Math.round(w || (WIDTHS.find(x => x[0] === k) || WIDTHS[1])[2]); }
    const sp = $('#hvSplit'); if (sp && UI.cmode !== 'chat') UI.cw = Math.max(380, Math.min(UI.cw, sp.clientWidth - 320));
    store.set('hv.chatw', UI.cw); store.set('hv.chatmode', UI.cmode === 'chat' ? 'chat' : 'open'); layout();
  }
  let DRAG = null;
  function dragStart(e) { const h = e.target.closest?.('[data-drag="chatw"]'); if (!h || e.button) return;
    e.preventDefault(); h.setPointerCapture?.(e.pointerId); DRAG = {h, x0: e.clientX, w0: UI.cw}; h.classList.add('on'); ROOT.classList.add('hv-dragging'); }
  function dragMove(e) { if (!DRAG) return; const sp = $('#hvSplit'); if (!sp) return;
    UI.cw = Math.round(Math.max(380, Math.min(sp.clientWidth - 320, DRAG.w0 + e.clientX - DRAG.x0))); sp.style.setProperty('--hv-cw', UI.cw + 'px');
    DRAG.h.setAttribute('aria-valuenow', String(UI.cw)); topTools(); }
  function dragEnd() { if (!DRAG) return; DRAG.h.classList.remove('on'); ROOT.classList.remove('hv-dragging'); DRAG = null; store.set('hv.chatw', UI.cw); }
  // the takes of one ask, kept together and placed after the reply of the turn that made them
  function sets() {
    const m = new Map();
    for (const it of C.items) { const k = it.job || it.id, s = m.get(k) || {id: k, at: Infinity, items: []}; s.items.push(it); s.at = Math.min(s.at, atOf(it.made) || 0); m.set(k, s); }
    m.forEach(s => s.items.sort((a, b) => String(a.take || '').localeCompare(String(b.take || '')) || atOf(a.made) - atOf(b.made)));
    return [...m.values()].sort((a, b) => a.at - b.at);
  }
  function setCard(s) {
    const f = s.items[0] || {}, credits = s.items.reduce((n, x) => n + (+x.credits || 0), 0), t = f.title || 'Your sound';
    const meta = [f.lang ? short(f.lang) : '', f.voice_name, f.style ? styleName(f.style) : '', f.speed && +f.speed !== 1 ? `${+f.speed}x` : '', plural(s.items.length, 'take'), f.engine ? engName(f.engine) : ''].filter(Boolean).join(' · ');
    const who = f.voice_name && (f.kind === 'tts' || !f.kind) ? `<span class="hv-av l" aria-hidden="true">${initial(f.voice_name)}</span>` : `<span class="hv-tile l">${ic(f.kind === 'sfx' ? 'fx' : f.kind === 'dialogue' || f.kind === 'podcast' ? 'dialog' : 'speech', 20)}</span>`;
    const take = (it, i) => { const L = it.take || String.fromCharCode(65 + i), on = kept(it.id);
      return `<div class="hv-take${on ? ' kept' : ''}">${playBtn(it.id, `Play take ${L}`, 14, ' l')}<span class="hv-tn">Take ${esc(L)}</span>${wave(it.id, 64)}
        <span class="hv-len hv-num">${it.seconds ? secs(it.seconds) : ''}</span>
        <button type="button" class="hv-keep${on ? ' on' : ''}" data-a="keep" data-id="${esc(it.id)}" aria-pressed="${on}" aria-label="${on ? `Take ${esc(L)} is kept` : `Keep take ${esc(L)}`}">${on ? ic('check', 13) + 'Kept' : 'Keep'}</button>
        <button type="button" class="hv-ib s" data-a="takemenu" data-id="${esc(it.id)}" aria-label="More for take ${esc(L)}: download, dub it, remove">${ic('more')}</button></div>`; };
    const dlg = f.kind === 'dialogue' || f.kind === 'podcast';
    const chips = [['Slower', `Make "${t}" a little slower`], ['Warmer', `Make "${t}" warmer`], ['Another voice', `Read "${t}" again in another voice`],
      dlg ? ['Add soft music', `Make "${t}" again with soft music under it`] : ['Make it English', `Make "${t}" in English`]];
    return `<article class="hv-card hv-setc" aria-label="${esc(t)}"><div class="hv-seth">${who}<div class="hv-ct"><b>${esc(t)}</b><small>${esc(meta)}</small></div>
        ${s.items.length > 1 ? `<button type="button" class="hv-btn s" data-a="compare" data-val="${esc(s.items.map(x => x.id).join(','))}" aria-label="Play the takes one after another">Compare</button>` : ''}</div>
      <div class="hv-takesl">${s.items.map(take).join('')}</div>
      <div class="hv-chips">${chips.map(([l, ask]) => `<button type="button" class="hv-chip" data-a="ask" data-val="${esc(ask)}">${l}</button>`).join('')}
        ${canDub(f) ? `<button type="button" class="hv-chip pri" data-a="dubit" data-id="${esc(f.id)}" aria-haspopup="menu">${ic('globe', 13)}Dub it into another language</button>` : ''}</div>
      <span class="hv-mut hv-sm">Made by AI · marked in the file${credits ? ' · ' + cr(credits) : ''}</span></article>`;
  }
  function threadList() {
    const first = C.rows.findIndex(r => r.role === 'user');
    const msgs = C.rows.filter((r, i) => r.role === 'user' || (r.role === 'assistant' && first >= 0 && i > first)).map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? strip(r.text) : String(r.text || ''), at: atOf(r.at || r.created_at)}));
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
      sync(st) { const h = st.messages.map(m => m.role === 'raw' ? m.html : m.role === 'her' ? `<div class="hv-me hck-bub">${esc(m.text)}</div>` : `<div class="hv-ho hck-txt">${esc(m.text)}</div>`).join('')
        + (st.working ? `<p class="hv-mut">${esc(st.label)}</p>` : ''); if (h !== K) { host.innerHTML = h; K = h; } }};
  }
  function drawSets() {
    const m = new Map(sets().map(s => [String(s.id), s]));
    $$('[data-vset]').forEach(n => { const s = m.get(n.dataset.vset); if (!s) return; const h = setCard(s); if (n._h === h) return; n._h = h; n.innerHTML = h; });
    syncPlay();
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
    if (f) { const g = gate(paid(speakWhy(C.lastSend?.lang || S.lang, C.lastSend?.engine || S.engine)));
      f.innerHTML = bad ? `<div class="hv-card hv-fail"><b>Hoola could not answer this time.</b><span class="hv-mut">You can still make it now from your words and settings.</span>
      <div><button type="button" class="hv-cta s" data-a="direct"${g.a}>${ic('play')}<span>Make it now</span></button>${g.l}</div></div>` : ''; }
    if (was !== working) sendState();
  }
  function sendState() {
    const b = $('[data-qbtn="chat"]'); if (!b) return;
    const stop = C.working && !C.sending, w = stop ? '' : chatWhy();
    b.classList.toggle('stop', stop); b.classList.toggle('on', stop || !!C.ask.trim());
    b.setAttribute('aria-label', stop ? 'Stop' : 'Send'); b.title = stop ? 'Stop' : 'Send'; b.innerHTML = ic(stop ? 'stopf' : 'send');
    b.disabled = !!w;
  }
  async function openChat(id) {
    try {
      if (id) { await api('GET', `${A}/chat/${q(id)}/ok`); }
      const c = id ? {id} : await api('GET', `${A}/chat`);
      C.conv = c.id; C.rows = []; C.items = []; C.turn = null; C.lastSend = null; if (c.title) C.title = c.title;
      C.thread?.clear?.(); await chatLoad(true);
      if (PAGE === 'chat') { crumb(); side(); draw(); }
      recent();
    } catch (e) { toast(`The Vocal chat could not open: ${e.message}`, true); }
  }
  function recent() { api('GET', `${A}/chats`).then(r => { UI.recent = (r.chats || []).slice(0, 4); side(); }).catch(() => { /* the list waits for next time */ }); }
  async function chatLoad(first) {
    if (!C.conv || C.loading) return; const conv = C.conv; C.loading = true;
    try {
      const last = C.rows[C.rows.length - 1];
      if (C.sending || C.working || first || (last && last.role === 'user')) { try { C.turn = await api('GET', `/api/conversations/${q(conv)}/result`); } catch { /* no turn yet */ } }
      let rows; try { rows = (await api('GET', `/api/conversations/${q(conv)}/messages?limit=200`)).messages || []; } catch { return; }
      let items = C.items; try { items = (await api('GET', `${A}/chat/${q(conv)}/items`)).items || []; } catch { /* the sounds come next time */ }
      if (conv !== C.conv) return;
      const before = C.items.length; C.rows = rows; C.items = items; if (rows.some(r => r.role === 'user')) C.pend = '';
      if (first) return;
      if (PAGE === 'chat') { if ($('.hv-fresh') && !fresh()) return draw(); paintChat(); if (items.length !== before) { await load(); refreshSide(); side(); } }
    } finally { C.loading = false; }
  }
  function refreshSide() { const g = $('#hvSndGrid'); if (!g) return; const f = PAGE === 'sounds' ? UI.snd : UI.side;
    g.innerHTML = soundsList(f).slice(0, PAGE === 'sounds' ? 300 : 30).join('') || `<p class="hv-mut">${f.q ? 'Nothing matches.' : 'Nothing yet. What you make appears here.'}</p>`; syncPlay(); }
  function chatPoll() {
    clearTimeout(chatPoll.t);
    const tick = async () => { if (PAGE !== 'chat' || !ROOT || ROOT.hidden) return; await chatLoad(false); chatPoll.t = setTimeout(tick, C.working ? 2000 : 8000); };
    chatPoll.t = setTimeout(tick, C.working || C.sending ? 1500 : 8000);
  }
  async function chatSend(textIn) {
    const ta = $('#hvAsk'), text = String(textIn ?? C.ask ?? '').trim();
    if (C.working && !C.sending && textIn == null && !text) { try { await api('POST', `/api/conversations/${q(C.conv)}/stop`); toast('Stopping.'); } catch (e) { toast(e.message, true); } return; }
    if (!text) { ta?.focus(); toast('Tell Hoola what to say first.'); return; }
    const w = chatWhy(); if (w) { toast(w, true); return; }
    if (C.files.some(f => f.up)) { toast('Wait for the files to finish uploading.'); return; }
    if (!C.conv) await openChat();
    if (!C.conv) return;
    const files = C.files.filter(f => f.file_id);
    C.sending = true; C.turn = null; C.setOpen = false; refreshSet();
    C.lastSend = {text, at: Date.now() / 1000, voice: S.voice, lang: S.lang, style: S.style, speed: S.speed, takes: S.takes, engine: S.engine, format: S.format, expressive: S.expressive, rules: S.rules};
    if (textIn == null) C.ask = ''; C.files = []; C.pend = text;
    if (ta && textIn == null) { ta.value = ''; ta.style.height = ''; } const t = $('#hvTray'); if (t) { t.innerHTML = ''; t.hidden = true; }
    if ($('.hv-fresh')) draw();
    C.thread?.her(text, {pending: true, files: files.map(f => f.name)});
    paintChat();
    try {
      await api('POST', `/api/conversations/${q(C.conv)}/messages`, {text: `${text}\n\n${settingsNote()}`, files: files.map(f => f.file_id),
        client_id: 'vo' + Date.now().toString(36) + (++C.seq).toString(36)});
      C.turn = {status: 'queued', line: ''};
    } catch (e) { toast(e.message, true); if (textIn == null) C.ask = text; C.files = files; C.pend = ''; noCredit(e); }
    C.sending = false; await chatLoad(false); paintChat(); sendState(); chatPoll();
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
  function refreshSet() {           // the chat's settings sheet + pill + price, without redrawing the thread
    const p = $('#hvSetp'); if (p) { const was = !p.hidden; p.hidden = !C.setOpen; p.innerHTML = C.setOpen ? setPanel() : '';
      if (C.setOpen && !was && p.closest('.hv-hero')) requestAnimationFrame(() => p.scrollIntoView({block: 'nearest'})); }
    const s = $('#hvSum'); if (s) s.textContent = summary();
    const av = $('#hvAv'); if (av) av.innerHTML = pillAv();
    const e = $('#hvEng'); if (e) e.textContent = engShort();
    const o = $('[data-a="setopen"]'); if (o) { o.setAttribute('aria-expanded', String(C.setOpen)); const svgs = o.querySelectorAll('svg'); if (svgs[1]) svgs[1].outerHTML = ic(C.setOpen ? 'down' : 'up', 12); }
    const comp = $('#hvComp');
    if (comp) { comp.querySelectorAll(':scope > .hv-why').forEach(n => n.remove()); const b = $('[data-qbtn="chat"]'), w = C.working && !C.sending ? '' : chatWhy();
      if (b) { b.removeAttribute('aria-describedby'); b.disabled = !!w;
        if (w) { const g = gate(w); b.setAttribute('aria-describedby', `hvw${WN}`); comp.querySelector('.hv-box')?.insertAdjacentHTML('afterend', g.l); } } }
    price('chat', chatQuote(), chatLine);
    if (C.setOpen) price('chatset', chatQuote(), r => r.credits != null ? `${cr(r.credits)} · ${plural(S.takes, 'take')}` : '');
  }

  // ------------------------------------------------------------------ pages ---
  const ENTER = {
    chat() { if (!UI.recent) recent(); if (!C.conv) openChat().then(() => { if (C.ask && PAGE === 'chat' && C.autosend) { C.autosend = false; chatSend(); } chatPoll(); });
      else { chatLoad(false).then(() => { paintChat(); if (C.autosend) { C.autosend = false; chatSend(); } chatPoll(); }); } },
    dub() { if (ARG) { loadDub(ARG); return; } api('GET', `${A}/dubs`).then(r => { UI.dubs = r.dubs || []; if (PAGE === 'dub' && !ARG) draw(); }).catch(e => { UI.dubs = []; toast(e.message, true); }); },
    mine() { consentLine(UI.clone.lang); },
    voices() { if (UI.vtab === 'shared') libLoad(); },
    settings() { UI.newKey = null; UI.newHook = null; loadApps(); },
  };
  const AFTER = {
    chat() {
      const host = $('#hvThread');
      if (host) { C.thread = window.HoolaChat ? HoolaChat.mount(host, {acts: ['copy'], scroller: $('#hvLog'), jump: true}) : plainThread(host); paintChat(C.sending); }
      else C.thread = null;
      const ta = $('#hvAsk'); if (ta) { ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); chatSend(); } });
        ta.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); chatFiles(fs); } }); grow(ta); }
      price('chat', chatQuote(), chatLine);
    },
    speech() { price('speech', ttsQuote(S.text), r => autoLine(r, short(S.lang))); },
    mine() { if (UI.way === 'record') price('clone', {job: 'clone', lang: UI.clone.lang}); if (UI.way === 'design') price('design', {job: 'design'}); },
    dialogue() { $$('.hv-lt').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }); price('dlg', dlgQuote(), r => r.credits != null ? `About ${secs(dlgChars() / 15)} of sound · nothing is spent until you tap` : esc(scrub(r.line || ''))); },
    changer() { price('chg', {job: 'change', seconds: UI.chg.secs || 60, voice: UI.chg.voice}, r => r.credits != null ? `${UI.chg.secs ? secs(UI.chg.secs) + ' of sound · ' : 'Priced for a minute · '}nothing is spent until you tap` : ''); },
    cleanup() { price('cl', {job: UI.cl.people || UI.cl.music ? 'isolate' : 'cleanup', seconds: UI.cl.secs || 60}); },
    sfx() { price('fx', {job: 'sfx', seconds: UI.fx.seconds || 5, takes: UI.fx.takes}); },
    dub() { if (!ARG) price('dub', {job: UI.dubNew.mode === 'own' ? 'dub_own' : 'dub_matched', seconds: UI.dubNew.secs || 60, langs: UI.dubNew.langs.length || 1}); else dubMedia(); },
    reading() { const p = UI.proj, ch = p?.chapters?.[UI.chN]; if (ch) price('readch', {job: 'chapter', chars: (ch.text || '').length, lang: p.lang || 'en'});
      if (p) price('readall', {job: 'chapter', chars: p.chapters.filter((c, i) => !c.audio || UI.edited[i]).reduce((n, c) => n + (c.text || '').length, 0), lang: p.lang || 'en'}); },
  };
  const grow = t => { t.style.height = 'auto'; t.style.height = Math.min(180, t.scrollHeight) + 'px'; };
  function dictHits(text) { if (!S.rules) return 0; const lo = String(text || '').toLowerCase();
    return D.rules.filter(r => r.word && new RegExp(`(^|[^\\p{L}\\p{N}])${String(r.word).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[^\\p{L}\\p{N}])`, 'u').test(lo)).length; }
  const countLine = () => { const n = dictHits(S.text); return `${num(S.text.length)} characters · tones work on every engine${n ? ` · ${plural(n, 'word')} from your dictionary will be read your way` : ''}`; };
  const panel = (label, body, cls = '') => `<section class="hv-panel${cls ? ' ' + cls : ''}" aria-label="${label}">${body}</section>`;
  const stage = (label, head, body) => `<section class="hv-stage" aria-label="${label}"><div class="hv-stageh">${head}</div><div class="hv-stageb">${body}</div></section>`;
  const dlgChars = () => UI.dlg.lines.reduce((n, l) => n + (l.text || '').length, 0);
  const dlgQuote = () => ({job: 'dialogue', chars: dlgChars(), lang: UI.dlg.lang || 'auto'});

  const V = {
    chat: chatView,

    speech() {
      const lim = D.limits?.characters || 100000, w = paid(speakWhy(S.lang, S.engine)), g = gate(w), v = voice(S.voice);
      const f = S.out[0];
      return `<div class="hv-split hv-tool">${panel('Speech settings', `<form class="hv-form" data-f="speech">
          <div class="hv-fld"><label class="hv-lab" for="hvText">Words</label>
            <textarea id="hvText" class="hv-in hv-words" rows="6" maxlength="${lim}" data-m="S.text" placeholder="Type or paste your words. Put a tone in square brackets, like [warm] or [laughs]; it is never read out.">${esc(S.text)}</textarea>
            <div class="hv-tags" role="toolbar" aria-label="Add a tone"><span>Add a tone:</span>${TONES.map(t => `<button type="button" class="hv-chip s" data-a="tag" data-val="${t}">[${t}]</button>`).join('')}</div>
            <span class="hv-hint hv-num" id="hvCount">${esc(countLine())}</span></div>
          <div class="hv-picks">${dd('Language', 'picklang', 'S.lang', langLabel(S.lang), ' data-auto="1"')}${dd('Voice', 'pickvoice', 'S.voice', v ? `${v.name}${v.tone ? ' · ' + v.tone.toLowerCase() : ''}` : 'No voice ready')}
            ${dd('Format', 'pickfmt', 'S.format', fmtOf(S.format).name)}${dd('Engine', 'pickengine', 'S.engine', engName(S.engine))}</div>
          ${Object.keys(D.styles || {}).length ? `<div class="hv-fld"><span class="hv-lab">Style</span>${chipSeg('S.style', Object.entries(D.styles), S.style, 'Style')}</div>` : ''}
          <div class="hv-row2"><div class="hv-fld hv-growf"><label class="hv-lab hv-labr" for="hvSpeed"><span>Speed</span><span class="hv-num hv-mut" data-show="S.speed">${(+S.speed).toFixed(2)}x</span></label>
              <input id="hvSpeed" type="range" min="0.7" max="1.3" step="0.05" value="${S.speed}" data-m="S.speed" data-t="num"></div>
            <div class="hv-fld"><span class="hv-lab">Takes</span>${seg('S.takes', [[1, '1'], [2, '2'], [4, '4']], S.takes, null, 'Takes')}</div></div>
          ${check('S.rules', `Read my dictionary words my way (${plural(D.rules.length, 'word')})`, S.rules)}
          <span class="hv-grow"></span>
          <button class="hv-cta" data-qbtn="speech" data-label="Speak it"${g.a}><span>Speak it</span></button>${g.l}
          ${D.status?.connected?.stream && v?.engine === 'eleven' ? `<button type="button" class="hv-btn" data-a="stream"${g.a}>${ic('play', 13)}Play while it is made</button>` : ''}
          <p class="hv-hint c" data-qline="speech">The price shows here before anything is made.</p></form>`)}
        ${stage('Takes', `<b>Takes</b><span class="hv-mut hv-sm">${f ? esc([f.title, f.lang ? short(f.lang) : '', f.voice_name].filter(Boolean).join(' · ')) : 'What you make appears here'}</span>`,
          S.out.length ? `<div class="hv-takes" id="hvTakes">${S.out.map((t, i) => takeCard(t, i)).join('')}</div><p class="hv-mut hv-sm">Every file carries the AI mark.</p>`
            : empty('No takes yet', 'Write the words, pick a voice and tap Speak it. Each take is a version to choose from.'))}</div>`;
    },

    voices() {
      const f = UI.vf, t = UI.vtab;
      const own = t === 'mine' ? D.voices.filter(v => v.kind !== 'hoola') : D.voices.filter(v => v.kind === 'hoola');
      const lo = f.q.trim().toLowerCase();
      const list = t === 'shared' ? (UI.lib.list || []) : own.filter(v => (!lo || [v.name, v.tone, v.accent, v.use, ...(v.langs || []).map(c => [c, lang(c)?.name, lang(c)?.native].join(' '))].join(' ').toLowerCase().includes(lo))
        && (!f.lang || (v.langs || []).includes(f.lang)) && (!f.accent || v.accent === f.accent) && (!f.gender || v.gender === f.gender) && (!f.age || v.age === f.age) && (!f.use || v.use === f.use));
      if (!list.some(v => v.id === UI.vsel)) UI.vsel = list[0]?.id || '';   // a voice is always open beside the list
      const chip = (k, label) => `<button type="button" class="hv-fchip${f[k] ? ' on' : ''}" data-a="vfilter" data-k="${k}" aria-haspopup="menu">${esc(label)}${ic('down', 12)}</button>`;
      const filters = [chip('lang', f.lang ? short(f.lang) : 'Any language'), chip('gender', f.gender ? f.gender[0].toUpperCase() + f.gender.slice(1) : 'Any gender'),
        chip('age', f.age ? f.age[0].toUpperCase() + f.age.slice(1) : 'Any age'), chip('accent', f.accent || 'Any accent'), chip('use', f.use ? 'Use: ' + f.use[0].toUpperCase() + f.use.slice(1) : 'Any use'),
        ...(t === 'shared' ? [`<button type="button" class="hv-fchip" data-a="vfilter" data-k="sort" aria-haspopup="menu">${esc({popular: 'Most used', trending: 'Trending', newest: 'Newest', most_added: 'Most added'}[f.sort] || 'Most used')}${ic('down', 12)}</button>`] : [])].join('');
      const count = t === 'shared' ? (UI.lib.list ? `${plural(list.length, 'voice')}${UI.lib.more ? ' and more' : ''}` : '') : `${plural(list.length, 'voice')}${f.lang ? ` speak${list.length === 1 ? 's' : ''} ${short(f.lang)}` : ''}`;
      const row = v => { const shared = t === 'shared', sel = UI.vsel === v.id, g = !shared && !v.ready;
        return `<article class="hv-vrow${sel ? ' on' : ''}"><button type="button" class="hv-vsel" data-a="vsel" data-id="${esc(v.id)}" aria-pressed="${sel}"><span class="hv-ava" aria-hidden="true">${initial(v.name)}</span>
            <span class="hv-vt"><span class="hv-vn"><b>${esc(v.name)}</b><span class="hv-src">${shared ? 'Shared' : v.kind === 'hoola' ? 'Hoola' : 'Yours'}</span></span>
            <span class="hv-mut hv-sm">${esc(shared ? v.line || [v.gender, v.age, v.accent].filter(Boolean).join(' · ') : [v.tone, (v.langs || []).map(c => lang(c)?.name || c).slice(0, 2).join(', '), v.use].filter(Boolean).join(' · '))}</span></span></button>
          <button type="button" class="hv-play o" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${g ? ' disabled' : ''}>${ic('play', 12)}</button>
          ${shared ? `<button type="button" class="hv-btn dark" data-a="libadd" data-id="${esc(v.id)}">Add</button>` : `<button type="button" class="hv-btn dark" data-a="usev" data-id="${esc(v.id)}"${g ? ' disabled' : ''}>Use</button>`}</article>`; };
      const body = t === 'shared' && UI.lib.list == null ? `<p class="hv-mut">Loading the shared library…</p>`
        : t === 'shared' && !UI.lib.ready ? warnNote(UI.lib.why || 'The shared library is not connected on this server yet.')
        : list.length ? `<div class="hv-vgrid">${list.map(row).join('')}</div>${t === 'shared' && UI.lib.more ? `<button type="button" class="hv-btn" data-a="libmore">Show more</button>` : ''}`
        : empty(t === 'mine' ? 'No voices of your own yet' : 'No voice matches', t === 'mine' ? 'Record, describe or change one in Your voice.' : 'Try fewer filters.');
      return `<div class="hv-split hv-tool"><section class="hv-panel wide" aria-label="Voices">
          <div class="hv-vhead">${seg('UI.vtab', [['hoola', 'Hoola voices'], ['shared', 'Shared library'], ['mine', 'Your voices']], t, null, 'Which voices')}<span class="hv-grow"></span>
            ${search('hvVq', 'UI.vf.q', 'Describe a voice: calm older man, Tamil', f.q)}</div>
          <div class="hv-chips">${filters}<span class="hv-mut hv-sm hv-count">${esc(count)}</span></div>${body}</section>
        <aside class="hv-stage hv-vdetail" aria-label="The chosen voice">${voiceDetail()}</aside></div>`;
    },

    mine() {
      const w = UI.way, cl = UI.clone, cline = UI.cline[cl.lang];
      const canClone = D.status.connected.clone ?? (ready('gemini') || ready('lab')), canDesign = D.status.connected.design ?? (ready('gemini') || ready('lab'));
      const why = ok => ok ? '' : 'No engine that makes voices is connected on this server yet.';
      const ways = [['record', 'Record your voice', '30 seconds in the page, or a file you have'], ['design', 'Describe a voice', 'A voice made from words, 3 options to hear'], ['remix', 'Change a voice', 'Older, softer, another accent']];
      const rec = k => REC[k];
      const recBox = k => `<div class="hv-recrow"><button type="button" class="hv-recb${rec(k) ? ' on' : ''}" data-a="${rec(k) ? 'recstop' : 'rec'}" data-k="${k}" aria-label="${rec(k) ? 'Stop recording' : 'Start recording'}">${rec(k) ? '<span class="hv-sq"></span>' : ic('mic', 20)}</button>
        <div class="hv-recm"><span class="hv-tn"><b>${rec(k) ? 'Recording' : cl[k]?.file_id ? 'Recorded' : 'Record here'}</b><span class="hv-mut hv-num" data-rect="${k}">${rec(k) ? '0:00 of 0:30' : cl[k] ? esc([cl[k].name, cl[k].secs ? secs(cl[k].secs) : '', cl[k].up ? 'uploading…' : cl[k].err || ''].filter(Boolean).join(' · ')) : 'up to 30 seconds'}</span></span>
          ${wave('lvl' + k, 70, rec(k) ? 'live' : 'thin')}</div></div>`;
      const sample = cl.sample || cl.consent;
      const checks = cl.consent ? [[sample?.secs >= 10, sample?.secs >= 10 ? 'Long enough' : `${Math.max(1, Math.ceil(10 - (sample?.secs || 0)))} more seconds needed`],
        [!!cl.consent?.file_id, cl.consent?.file_id ? 'Your yes is recorded' : cl.consent.err ? 'The recording did not upload' : 'Uploading your yes…']] : [];
      const gc = gate(paid(why(canClone) || (!cl.consent?.file_id ? 'Record the statement first.' : !cl.ok ? 'Tick the box above first.' : '')));
      const gd = gate(paid(why(canDesign))), gs = gate(UI.design.pick ? '' : 'Pick one of the three options first.'), gr = gate(paid(why(canDesign) || (UI.remix.base ? '' : 'Choose a voice to start from.')));
      const mine = D.voices.filter(v => v.kind !== 'hoola');
      const form = w === 'record' ? `<form class="hv-form" data-f="clone">${why(canClone) ? warnNote(why(canClone)) : ''}
          <div class="hv-card hv-recard"><div class="hv-rh"><b>Read this out loud, in your own voice</b><button type="button" class="hv-dd s" data-a="picklang" data-k="UI.clone.lang" data-need="clone" aria-haspopup="menu"><span>${esc(short(cl.lang))}</span>${ic('down', 12)}</button></div>
            ${cline ? `<p class="hv-consent" lang="${esc(cline.locale || cline.lang || '')}">“${esc(cline.line)}”</p>${cline.english && cline.english !== cline.line ? `<p class="hv-mut hv-sm">“${esc(cline.english)}”</p>` : ''}
              ${cline.lang && cline.lang !== cl.lang ? `<p class="hv-why">There is no consent statement in ${esc(lang(cl.lang)?.name || cl.lang)} yet, so the English one is used.</p>` : ''}` : '<p class="hv-mut">Loading the statement…</p>'}
            <p class="hv-mut hv-sm">Then keep talking naturally until about 30 seconds: this one recording makes your voice.</p>
            ${recBox('consent')}
            <span class="hv-mut hv-sm">or <button type="button" class="hv-lnk" data-a="pickrec" data-k="consent">${ic('upload', 13)}choose a recording</button> · 10 to 30 seconds</span>
            ${checks.length ? `<ul class="hv-checks">${checks.map(([ok, t]) => `<li class="${ok ? 'ok' : 'warn'}">${ic(ok ? 'check' : 'warn', 14)}${esc(t)}</li>`).join('')}</ul>` : ''}
            <details class="hv-more"><summary>Add a separate, longer sample (optional)</summary>${recBox('sample')}<span class="hv-mut hv-sm"><button type="button" class="hv-lnk" data-a="pickrec" data-k="sample">${ic('upload', 13)}choose a recording</button></span></details></div>
          <div class="hv-fld"><label class="hv-lab" for="hvCName">Name of the voice</label><input id="hvCName" class="hv-in" maxlength="40" data-m="UI.clone.name" value="${esc(cl.name)}"></div>
          <label class="hv-check"><input type="checkbox" id="hvCOk" required data-m="UI.clone.ok" data-t="bool" data-redraw="1"${cl.ok ? ' checked' : ''}><span>This is my own voice. I agree that Hoola keeps this recording as proof of my consent, and I can delete the voice at any time.</span></label>
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="clone" data-label="Make my voice"${gc.a}><span>Make my voice</span></button><span class="hv-mut hv-sm">Ready in about a minute · speaks every language its engine can</span></div>${gc.l}
          <p class="hv-mut hv-sm">Never a famous or named person’s voice. A voice of someone else needs them to read the statement themselves. No one under 18.</p></form>`
        : w === 'design' ? `<form class="hv-form" data-f="design">${why(canDesign) ? warnNote(why(canDesign)) : ''}
          <div class="hv-fld"><label class="hv-lab" for="hvDDesc">Describe the voice</label><textarea id="hvDDesc" class="hv-in" rows="4" maxlength="300" data-m="UI.design.desc" placeholder="An older man with a deep, kind voice, slow and calm, telling stories by a fire.">${esc(UI.design.desc)}</textarea>
            <span class="hv-hint">Who · age · tone · pace · accent · the room. Never a named person.</span></div>
          ${dd('Gender', 'pickgender', 'UI.design.gender', UI.design.gender ? UI.design.gender[0].toUpperCase() + UI.design.gender.slice(1) : 'Not set')}
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="design" data-label="Make 3 options"${gd.a}><span>Make 3 options</span></button></div>${gd.l}
          ${UI.design.previews.length ? `<div class="hv-fld"><span class="hv-lab">Pick the one you like</span>${UI.design.previews.map((p, i) => `<div class="hv-opt${UI.design.pick === p.pid ? ' on' : ''}">${playBtn(p.audio_id, `Play option ${i + 1}`, 12, ' s')}
              <span class="hv-grow">${esc(p.title || `Option ${i + 1}`)}</span><button type="button" class="hv-btn" data-a="dpick" data-val="${esc(p.pid)}" aria-pressed="${UI.design.pick === p.pid}">${UI.design.pick === p.pid ? 'Picked' : 'Pick'}</button></div>`).join('')}
            <label class="hv-lab" for="hvDName">Name</label><input id="hvDName" class="hv-in" maxlength="40" data-m="UI.design.name" value="${esc(UI.design.name)}" placeholder="Old storyteller">
            <div><button type="button" class="hv-cta s" data-a="dsave"${gs.a}><span>Save the voice</span></button>${gs.l}</div></div>` : ''}</form>`
        : `<form class="hv-form" data-f="remix">${dd('Starting voice', 'pickbase', 'UI.remix.base', vname(UI.remix.base))}
          <div class="hv-fld"><label class="hv-lab" for="hvRChange">What to change</label><input id="hvRChange" class="hv-in" maxlength="300" data-m="UI.remix.change" value="${esc(UI.remix.change)}" placeholder="Same voice, but more energetic, like a radio host"></div>
          <div class="hv-chips">${['Older', 'Younger', 'Deeper', 'Brighter', 'Calmer', 'Another accent'].map(c => `<button type="button" class="hv-chip" data-a="rxchip" data-val="${c}">${c}</button>`).join('')}</div>
          <div class="hv-fld"><label class="hv-lab" for="hvRName">Name</label><input id="hvRName" class="hv-in" maxlength="40" data-m="UI.remix.name" value="${esc(UI.remix.name)}" placeholder="My voice, softer"></div>
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="remix" data-label="Make the change"${gr.a}><span>Make the change</span></button></div>${gr.l}</form>`;
      return `<div class="hv-split hv-tool">${panel('Make a voice', `<div class="hv-ways" role="radiogroup" aria-label="How to make it">${ways.map(([k, n, l]) => `<button type="button" role="radio" class="hv-way" aria-checked="${w === k}" data-a="way" data-val="${k}"><b>${n}</b><span>${l}</span></button>`).join('')}</div>${form}`)}
        ${stage('Your voices', `<b>Your voices</b><span class="hv-mut hv-sm">${plural(mine.length, 'voice')}</span>`,
          (mine.length ? `<div class="hv-list">${mine.map(v => `<article class="hv-card hv-mv"><button type="button" class="hv-play" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>
              <span class="hv-vt"><b>${esc(v.name)}</b><span class="hv-mut hv-sm">${esc(v.kind === 'clone' ? `Recorded${v.made ? ' · ' + ago(v.made) : ''} · consent kept` : v.kind === 'design' ? 'Described in words' : v.kind === 'remix' ? 'Changed from a voice' : 'Yours')}${v.ready ? '' : ' · not ready'}</span></span>
              <button type="button" class="hv-ib s" data-a="mvmenu" data-id="${esc(v.id)}" aria-label="More for ${esc(v.name)}: use, change, remove">${ic('more')}</button></article>`).join('')}</div>`
            : empty('No voices of your own yet', 'Record, describe or change one on the left.')))}</div>`;
    },

    dialogue() {
      const d = UI.dlg, names = d.cast.map(c => c.name), n2 = d.cast.length;
      const natWhy = d.mode === 'natural' && n2 > 2 && !ready('eleven') ? 'Natural talk with more than 2 speakers needs ElevenLabs, which is not connected on this server yet. Choose Line by line, or keep 2 speakers.' : '';
      const w = paid(speakWhy(d.lang, 'auto') || natWhy || (d.lines.some(l => (l.text || '').trim()) ? '' : 'Write at least one line first.')), g = gate(w);
      const last = D.history.find(h => h.kind === 'dialogue' || h.kind === 'podcast');
      const pod = d.pod, gp = gate(paid(!ready('gemini') && !ready('eleven') ? 'No engine that writes and speaks a talk is connected on this server yet.' : ''));
      const podForm = d.podOpen ? `<form class="hv-card hv-form tight" data-f="podcast"><div class="hv-rh"><b>Write it from a document</b><button type="button" class="hv-ib s" data-a="podclose" aria-label="Close">${ic('x', 14)}</button></div>
          ${seg('UI.dlg.pod.src', [['file', 'A file'], ['url', 'A web address'], ['text', 'Pasted text']], pod.src, null, 'From')}
          ${pod.src === 'file' ? `<div class="hv-filerow"><button type="button" class="hv-btn" data-a="pickfile" data-k="pod" data-accept=".pdf,.doc,.docx,.txt,.epub,.md">${ic('upload', 14)}Choose a file</button><span class="hv-mut hv-sm">${pod.file ? esc(pod.file.name) + (pod.file.up ? ' · uploading…' : pod.file.file_id ? ' · ready' : '') : 'PDF, Word, text or EPUB'}</span></div>`
            : pod.src === 'url' ? `<label class="hv-sr" for="hvPodU">Web address</label><input id="hvPodU" class="hv-in" type="url" data-m="UI.dlg.pod.url" value="${esc(pod.url)}" placeholder="https://">`
            : `<label class="hv-sr" for="hvPodT">The text</label><textarea id="hvPodT" class="hv-in" rows="5" data-m="UI.dlg.pod.text" maxlength="60000">${esc(pod.text)}</textarea>`}
          <div class="hv-row2"><div class="hv-fld"><span class="hv-lab">Minutes</span>${seg('UI.dlg.pod.minutes', [[2, '2'], [5, '5'], [10, '10'], [15, '15']], pod.minutes, null, 'Minutes')}</div></div>
          <div class="hv-ctarow"><button class="hv-btn dark"${gp.a}>${ic('dialog', 14)}Write the script</button><span class="hv-mut hv-sm">You read it and change any line before the sound is made.</span></div>${gp.l}</form>` : '';
      return `<div class="hv-split hv-tool">${panel('Script', `<div class="hv-rh"><b class="hv-t">${esc(d.title || 'A new talk')}</b><span class="hv-grow"></span>
            <button type="button" class="hv-btn" data-a="podopen">${ic('upload', 14)}Write it from a document</button>
            <button type="button" class="hv-dd s" data-a="picklang" data-k="UI.dlg.lang" data-need="dialogue" data-auto="1" aria-haspopup="menu"><span>${esc(short(d.lang))}</span>${ic('down', 12)}</button></div>
          ${podForm}
          <div class="hv-cast">${d.cast.map((c, i) => `<div class="hv-castc"><span class="hv-ava s t${i % 4}" aria-hidden="true">${initial(c.name)}</span>
              <label class="hv-sr" for="hvCn${i}">Speaker ${i + 1} name</label><input id="hvCn${i}" class="hv-castn" maxlength="30" data-m="UI.dlg.cast.${i}.name" value="${esc(c.name)}">
              <button type="button" class="hv-dd xs" data-a="pickcast" data-n="${i}" aria-haspopup="menu" aria-label="Voice of ${esc(c.name)}"><span>${esc(vname(c.voice))}</span>${ic('down', 12)}</button>
              ${n2 > 1 ? `<button type="button" class="hv-ib xs" data-a="castrm" data-n="${i}" aria-label="Remove ${esc(c.name)}">${ic('x', 12)}</button>` : ''}</div>`).join('')}
            ${n2 < 6 ? `<button type="button" class="hv-btn" data-a="castadd">${ic('plus', 14)}Add a speaker</button>` : ''}</div>
          <form class="hv-lines" data-f="dialogue"><ol>${d.lines.map((l, n) => { const ci = Math.max(0, names.indexOf(l.speaker));
            return `<li class="hv-line"><button type="button" class="hv-who t${ci % 4}" data-a="pickwho" data-n="${n}" aria-haspopup="menu" aria-label="Speaker of line ${n + 1}: ${esc(l.speaker)}">${esc(l.speaker)}</button>
              <label class="hv-sr" for="hvLt${n}">Line ${n + 1}</label><textarea id="hvLt${n}" class="hv-lt" rows="1" maxlength="1500" data-m="UI.dlg.lines.${n}.text" placeholder="What ${esc(l.speaker)} says">${esc(l.text)}</textarea>
              ${d.lines.length > 1 ? `<button type="button" class="hv-ib xs" data-a="dlrm" data-n="${n}" aria-label="Remove line ${n + 1}">${ic('x', 12)}</button>` : ''}</li>`; }).join('')}</ol>
            ${d.lines.length < (D.limits?.lines || 40) ? `<button type="button" class="hv-btn" data-a="dladd">${ic('plus', 14)}Add a line</button>` : ''}</form>`, 'wide')}
        <aside class="hv-stage hv-side2" aria-label="Make the dialogue"><div class="hv-stageb"><b class="hv-t">How it sounds</b>
          <div class="hv-ways" role="radiogroup" aria-label="Way of making">${[['natural', 'Natural talk, one take', 'Both voices made together, so they react, pause and overlap like people'], ['lines', 'Line by line', 'Each line its own take, easier to redo one line']]
            .map(([k, n, l]) => `<button type="button" role="radio" class="hv-way" aria-checked="${d.mode === k}" data-a="seg" data-m="UI.dlg.mode" data-val="${k}"><b>${n}</b><span>${l}</span></button>`).join('')}</div>
          ${Object.keys(D.styles || {}).length ? `<div class="hv-fld"><span class="hv-lab">How they talk</span>${chipSeg('UI.dlg.style', [['', 'Natural'], ...Object.entries(D.styles)], d.style, 'How they talk')}</div>` : ''}
          <fieldset class="hv-fs"><legend class="hv-lab">Extras</legend>${check('UI.dlg.reactions', 'Small reactions <span class="hv-mut hv-sm">· a short “Mm-hmm” from the listener now and then</span>', d.reactions)}
            ${check('UI.dlg.music', 'Soft music under it <span class="hv-mut hv-sm">· made on Hoola’s server, free</span>', d.music, gate(ready('server') ? '' : 'Soft music needs ffmpeg on the server, which is not installed.'))}</fieldset>
          ${last ? `<div class="hv-card hv-lastv">${playBtn(last.id, `Play ${last.title || 'the last talk'}`, 12)}<span class="hv-vt"><b>${esc(last.title || 'The last talk')}</b><span class="hv-mut hv-sm hv-num">${esc([last.seconds ? secs(last.seconds) : '', ago(last.made)].filter(Boolean).join(' · '))}</span></span></div>` : ''}
          <span class="hv-grow"></span>
          <button type="button" class="hv-cta" data-a="dlgmake" data-qbtn="dlg" data-label="Make the dialogue"${g.a}><span>Make the dialogue</span></button>${g.l}
          <p class="hv-hint c" data-qline="dlg">${num(dlgChars())} characters · up to 6 speakers and 40 lines</p></div></aside></div>`;
    },

    studio() {
      const im = UI.imp;
      const imp = im.open ? `<form class="hv-card hv-form tight" data-f="import"><div class="hv-rh"><b>Import a book</b><button type="button" class="hv-ib s" data-a="impclose" aria-label="Close">${ic('x', 14)}</button></div>
          <span class="hv-mut hv-sm">EPUB, PDF, TXT, DOCX, a web page or pasted text. It is split into chapters for you.</span>
          ${seg('UI.imp.src', [['file', 'A file'], ['url', 'A web address'], ['text', 'Pasted text']], im.src, null, 'From')}
          ${im.src === 'file' ? `<div class="hv-filerow"><button type="button" class="hv-btn" data-a="pickfile" data-k="imp" data-accept=".epub,.pdf,.txt,.doc,.docx,.md">${ic('upload', 14)}Choose a file</button><span class="hv-mut hv-sm">${im.file ? esc(im.file.name) + (im.file.up ? ' · uploading…' : im.file.file_id ? ' · ready' : '') : ''}</span></div>`
            : im.src === 'url' ? `<label class="hv-sr" for="hvImU">Web address</label><input id="hvImU" class="hv-in" type="url" data-m="UI.imp.url" value="${esc(im.url)}" placeholder="https://">`
            : `<label class="hv-sr" for="hvImT">The text</label><textarea id="hvImT" class="hv-in" rows="6" data-m="UI.imp.text">${esc(im.text)}</textarea>`}
          <label class="hv-lab" for="hvImTi">Title (optional)</label><input id="hvImTi" class="hv-in" maxlength="80" data-m="UI.imp.title" value="${esc(im.title)}">
          <div class="hv-ctarow"><button class="hv-btn dark">Import</button></div></form>` : '';
      return `<div class="hv-doc"><div class="hv-doch"><div><b class="hv-t">Long readings</b><p class="hv-mut">Stories, lessons and audiobooks in chapters, with a voice per character.</p></div><span class="hv-grow"></span>
          <button type="button" class="hv-btn" data-a="impopen">${ic('upload', 14)}Import a book</button><button type="button" class="hv-btn dark" data-a="newproj">${ic('plus', 14)}New reading</button></div>${imp}
        ${D.projects.length ? `<div class="hv-pgrid">${D.projects.map(p => { const ch = p.chapters || [], done = ch.filter(c => c.audio).length;
            return `<button type="button" class="hv-card hv-proj" data-a="proj" data-id="${esc(p.id)}"><span class="hv-ava l" aria-hidden="true">${initial(p.title)}</span><span class="hv-vt"><b>${esc(p.title || 'A reading')}</b>
              <span class="hv-mut hv-sm hv-num">${esc([plural(ch.length, 'chapter'), langLabel(p.lang), ago(p.updated || p.made)].filter(Boolean).join(' · '))}</span></span><span class="hv-st${done && done === ch.length ? ' ok' : ''}">${done} of ${ch.length} made</span></button>`; }).join('')}</div>`
          : empty('No readings yet', 'Paste a story or a lesson, or import a book, and Hoola reads each chapter.', '<button type="button" class="hv-btn dark" data-a="newproj">New reading</button>')}</div>`;
    },

    reading() {
      const p = UI.proj; if (!p) return V.studio();
      const n = Math.min(UI.chN, p.chapters.length - 1), ch = p.chapters[n] || {title: '', text: ''}, w = paid(speakWhy(p.lang || S.lang, 'auto'));
      const left = p.chapters.filter((c, i) => !c.audio || UI.edited[i]).length, all = p.chapters.length && p.chapters.every((c, i) => c.audio && !UI.edited[i]);
      const cast = UI.cast && UI.cast.n === n ? UI.cast : null;
      const state = i => p.chapters[i].audio ? (UI.edited[i] ? 'changed' : 'made') : 'none';
      const g = gate(w), ge = gate(p.id && all ? '' : 'Make every chapter first.'), gl = gate(w || (left ? '' : 'Every chapter is made.'));
      return `<div class="hv-split hv-tool three"><nav class="hv-chaps" aria-label="Chapters"><div class="hv-rh"><span class="hv-ava" aria-hidden="true">${initial(p.title)}</span><span class="hv-vt"><b>${plural(p.chapters.length, 'chapter')}</b><span class="hv-mut hv-sm">${esc(langLabel(p.lang || 'en'))}</span></span></div>
          <label class="hv-sr" for="hvPTitle">Title of the reading</label><input id="hvPTitle" class="hv-in" data-m="UI.proj.title" value="${esc(p.title || '')}" maxlength="80" placeholder="Title of the reading">
          ${p.chapters.map((c, i) => `<button type="button" class="hv-chap" data-a="chsel" data-n="${i}"${i === n ? ' aria-current="true"' : ''}><span>${i + 1} · ${esc(c.title || 'Chapter')}</span><span class="hv-dot ${state(i)}" title="${state(i) === 'made' ? 'Made' : state(i) === 'changed' ? 'Changed since it was made' : 'Not made yet'}"></span></button>`).join('')}
          <button type="button" class="hv-btn" data-a="chadd">${ic('plus', 14)}Add a chapter</button>
          <span class="hv-grow"></span><div class="hv-acts"><button type="button" class="hv-btn" data-a="go" data-p="studio">${ic('back', 14)}All readings</button>${p.id ? `<button type="button" class="hv-btn danger" data-a="rmproj" data-id="${esc(p.id)}">Remove</button>` : ''}</div></nav>
        <section class="hv-panel wide hv-chapter" aria-label="Chapter ${n + 1}"><label class="hv-sr" for="hvChT">Chapter ${n + 1} title</label>
          <input id="hvChT" class="hv-chtitle" data-m="UI.proj.chapters.${n}.title" data-ch="${n}" value="${esc(ch.title || '')}" maxlength="80" placeholder="Chapter ${n + 1}">
          ${w ? warnNote(w + ' You can write and save; reading needs the engine.') : ''}
          ${cast ? `<div class="hv-paras">${(cast.paragraphs || []).map(pa => `<div class="hv-para"><span class="hv-who t${Math.max(0, (cast.characters || []).findIndex(c => c.name === pa.who)) % 4}">${esc(pa.who || 'Narrator')}</span><p>${esc(pa.text)}</p></div>`).join('')}</div>` : ''}
          <label class="hv-sr" for="hvChX">Chapter ${n + 1} words</label><textarea id="hvChX" class="hv-in hv-words serif" data-m="UI.proj.chapters.${n}.text" data-ch="${n}" maxlength="${D.limits?.chapter || 40000}" placeholder="The words of this chapter">${esc(ch.text || '')}</textarea>
          <div class="hv-card hv-playrow">${ch.audio ? playBtn(ch.audio, `Play chapter ${n + 1}`, 12) : ''}<span class="hv-mut hv-sm hv-num hv-growf">Chapter ${n + 1}${ch.audio ? ` · ${secs(ch.seconds)} · made${UI.edited[n] ? ' · changed since' : ''}` : ' · not made yet'} · ${num((ch.text || '').length)} characters</span>
            <button type="button" class="hv-btn dark" data-a="readch" data-n="${n}" data-qbtn="readch" data-label="${ch.audio ? 'Make the changes' : 'Make this chapter'}"${g.a}><span>${ch.audio ? 'Make the changes' : 'Make this chapter'}</span></button></div>${g.l}
          <p class="hv-mut hv-sm">Change a word and only that paragraph is read again, in the same voice.</p></section>
        <aside class="hv-stage hv-side2" aria-label="Voices and export"><div class="hv-stageb">
          ${dd('Reading voice', 'pickpvoice', 'UI.proj.voice', vname(p.voice || S.voice))}${dd('Language', 'picklang', 'UI.proj.lang', langLabel(p.lang || 'en'))}
          <b class="hv-t">Who reads whom</b>
          ${cast && (cast.characters || []).length ? (cast.characters || []).map((c, i) => `<div class="hv-role"><span class="hv-dot t${i % 4}"></span><span class="hv-vt"><b>${esc(c.name)}</b><span class="hv-mut hv-sm">${esc(vname(c.voice))}</span></span>
              <button type="button" class="hv-btn s" data-a="pickrole" data-n="${i}" aria-haspopup="menu" aria-label="Change the voice for ${esc(c.name)}">Change</button></div>`).join('')
            : `<p class="hv-mut hv-sm">${cast ? 'No speakers found in this chapter.' : 'Hoola can find the characters in this chapter; quoted words go to their voice.'}</p>`}
          <button type="button" class="hv-btn" data-a="cast" data-n="${n}">Find the characters</button>
          <b class="hv-t">Export</b><div class="hv-acts">${[['m4b', 'One audiobook file'], ['mp3', 'MP3'], ['srt', 'Captions, SRT']].map(([f, l]) => `<button type="button" class="hv-btn" data-a="export" data-val="${f}"${ge.a}>${l}</button>`).join('')}</div>${ge.l}
          <span class="hv-grow"></span><button type="button" class="hv-btn" data-a="saveproj">Save</button>
          <button type="button" class="hv-cta" data-a="readall" data-qbtn="readall" data-label="Make all ${left} left"${gl.a}><span>Make all ${left} left</span></button>${gl.l}
          <p class="hv-hint c">You can stop any time; nothing made is lost.</p></div></aside></div>`;
    },

    dub() {
      if (ARG) return dubView();
      const n = UI.dubNew, ownWhy = ready('eleven') ? '' : whyNot('eleven'), lim = D.limits || {}, maxL = n.mode === 'own' ? (lim.dub_langs_own || 6) : (lim.dub_langs_matched || 4), maxS = lim.dub_speakers || 6;
      if (n.langs.length > maxL) n.langs = n.langs.slice(0, maxL);
      const go_ = gate(paid(!ready('gemini') && !ready('eleven') ? 'No dubbing engine is connected on this server yet.' : !n.file?.file_id ? 'Add the video first.' : !n.langs.length ? 'Choose at least one language.' : (n.mode === 'own' && ownWhy) ? ownWhy : ''));
      const og = gate(ownWhy);
      return `<div class="hv-split hv-tool">${panel('New dub', `<form class="hv-form" data-f="dub"><b class="hv-t">New dub</b>
          <p class="hv-mut hv-sm">Your video in another language. Only your own videos, or ones you have the right to dub. Each dub is marked as AI.</p>
          <div class="hv-filerow"><button type="button" class="hv-btn" data-a="pickfile" data-k="dub" data-accept="video/*,audio/*">${ic('upload', 14)}Choose a video or recording</button><span class="hv-mut hv-sm">${n.file ? esc(n.file.name) + (n.secs ? ' · ' + secs(n.secs) : '') + (n.file.up ? ' · uploading…' : n.file.file_id ? ' · ready' : '') : ''}</span></div>
          <div class="hv-fld"><span class="hv-lab">Into (up to ${maxL})</span><div class="hv-chips">${n.langs.map(c => `<button type="button" class="hv-chip on" data-a="dubrm" data-val="${esc(c)}" aria-label="Remove ${esc(langLabel(c))}">${esc(short(c))}${ic('x', 12)}</button>`).join('')}
            ${n.langs.length < maxL ? `<button type="button" class="hv-chip" data-a="picklang" data-k="dubadd" data-need="dub" aria-haspopup="menu">${ic('plus', 12)}Add a language</button>` : ''}</div></div>
          <div class="hv-ways" role="radiogroup" aria-label="How it sounds"><button type="button" role="radio" class="hv-way" aria-checked="${n.mode === 'own'}" data-a="seg" data-m="UI.dubNew.mode" data-val="own"${og.a}><b>Their own voices</b><span>Each speaker sounds like themselves in the new language</span></button>${og.l}
            <button type="button" role="radio" class="hv-way" aria-checked="${n.mode === 'matched'}" data-a="seg" data-m="UI.dubNew.mode" data-val="matched"><b>Matched voices</b><span>A close Hoola voice per speaker</span></button></div>
          ${n.mode === 'matched' ? `<div class="hv-fld"><span class="hv-lab">Speakers in the video</span>${seg('UI.dubNew.speakers', [[0, 'Auto'], ...Array.from({length: maxS}, (_, i) => [i + 1, String(i + 1)])], n.speakers, null, 'Speakers')}</div>` : ''}
          ${check('UI.dubNew.keep', 'Keep the music and room sound underneath', n.keep)}
          <span class="hv-grow"></span><button class="hv-cta" data-qbtn="dub" data-label="Make the dubs"${go_.a}><span>Make the dubs</span></button>${go_.l}<p class="hv-hint c" data-qline="dub"></p></form>`)}
        ${stage('Your dubs', `<b>Your dubs</b>`, UI.dubs == null ? '<p class="hv-mut">Loading…</p>' : UI.dubs.length ? `<div class="hv-list">${UI.dubs.map(x => `<article class="hv-card hv-mv"><span class="hv-tile">${ic('dub')}</span><span class="hv-vt"><b>${esc(x.title || x.name || 'Dub')}</b>
            <span class="hv-mut hv-sm">${esc((x.langs || []).map(l => typeof l === 'string' ? short(l) : (l.name || l.code)).join(', '))}${x.made ? ' · ' + esc(ago(x.made)) : ''}</span></span>
            <span class="hv-st ${x.status === 'ready' ? 'ok' : x.status === 'failed' ? 'bad' : 'work'}">${esc(x.status === 'ready' ? 'Ready' : x.status === 'failed' ? 'Failed' : 'Working')}</span><button type="button" class="hv-btn" data-a="dubopen" data-id="${esc(x.id)}">Open</button></article>`).join('')}</div>`
          : empty('No dubs yet', 'Choose a video on the left.'))}</div>`;
    },

    changer() {
      const c = UI.chg, w = ready('eleven') ? '' : whyNot('eleven');
      const g = gate(paid(w || (!voice(c.voice) ? 'There is no voice on ElevenLabs to change into yet.' : !c.file?.file_id ? (c.file?.up ? 'The recording is still uploading.' : 'Record or choose a recording first.') : '')));
      const into = voice(c.voice);
      return `<div class="hv-split hv-tool">${panel('Voice changer', `<form class="hv-form" data-f="change"><b class="hv-t">Voice changer</b><p class="hv-mut hv-sm">Say it your way; it comes out in another voice with your timing and feeling.</p>
          ${w ? warnNote('The voice changer runs on ElevenLabs only. ' + w) : ''}
          <div class="hv-recbig"><button type="button" class="hv-recb l${REC.chg ? ' on' : ''}" data-a="${REC.chg ? 'recstop' : 'rec'}" data-k="chg" aria-label="${REC.chg ? 'Stop recording' : 'Start recording'}">${REC.chg ? '<span class="hv-sq"></span>' : ic('mic', 22)}</button>
            <span class="hv-tn"><b>${REC.chg ? 'Recording' : c.file ? 'Your recording' : 'Record here'}</b><span class="hv-mut hv-sm hv-num" data-rect="chg">${REC.chg ? '0:00' : c.file ? esc([c.file.name, c.secs ? secs(c.secs) : '', c.file.up ? 'uploading…' : c.file.err || (c.file.file_id ? 'ready' : '')].filter(Boolean).join(' · ')) : 'up to 5 minutes'}</span></span>
            <span class="hv-mut hv-sm">or <button type="button" class="hv-lnk" data-a="pickfile" data-k="chg" data-accept="audio/*,video/*">${ic('upload', 13)}choose a recording</button></span></div>
          ${dd('Into', 'pickinto', 'UI.chg.voice', into ? `${into.name}${into.kind === 'clone' ? ' · your voice' : into.tone ? ' · ' + into.tone.toLowerCase() : ''}` : 'No voice on ElevenLabs')}
          ${check('UI.chg.denoise', 'Remove room noise first', c.denoise)}
          <span class="hv-grow"></span><button class="hv-cta" data-qbtn="chg" data-label="Change it"${g.a}><span>Change it</span></button>${g.l}<p class="hv-hint c" data-qline="chg"></p></form>`)}
        ${stage('Result', `<b>Result</b>`, c.out ? `<div class="hv-takes">${takeCard(c.out, 0, false)}</div>` : empty('Nothing changed yet', 'Your recording comes back here in the new voice.'))}</div>`;
    },

    cleanup() {
      const c = UI.cl, w = ready('eleven') ? '' : whyNot('eleven'), gw = gate(paid(!c.file?.file_id ? 'Choose the recording first.' : ''));
      const opt = (k, n, prem) => { const g = gate(prem ? w : ''); return `<label class="hv-check"><input type="checkbox" data-m="UI.cl.${k}" data-t="bool" data-redraw="1"${c[k] && !(prem && w) ? ' checked' : ''}${g.a}><span>${n}${prem ? ' <span class="hv-src">ElevenLabs</span>' : ''}</span></label>${g.l}`; };
      return `<div class="hv-split hv-tool">${panel('Clean-up', `<form class="hv-form" data-f="cleanup"><b class="hv-t">Clean-up</b><p class="hv-mut hv-sm">Make a voice clear, or lift it out of music.</p>
          <div class="hv-filerow"><button type="button" class="hv-btn" data-a="pickfile" data-k="cl" data-accept="audio/*,video/*">${ic('upload', 14)}Choose a recording</button><span class="hv-mut hv-sm">${c.file ? esc(c.file.name) + (c.secs ? ' · ' + secs(c.secs) : '') + (c.file.up ? ' · uploading…' : c.file.file_id ? ' · ready' : '') : 'or a video'}</span></div>
          <fieldset class="hv-fs"><legend class="hv-lab">Fix</legend>${opt('denoise', 'Remove background noise')}${opt('echo', 'Make the voice clearer')}${opt('level', 'Even out the loudness')}${opt('silence', 'Cut long silences')}
            ${opt('people', 'Remove street sounds and other people', true)}${opt('music', 'Take the voice out of music', true)}</fieldset>
          <span class="hv-grow"></span><button class="hv-cta" data-qbtn="cl" data-label="Clean it"${gw.a}><span>Clean it</span></button>${gw.l}
          <p class="hv-hint c" data-qline="cl">${c.people || c.music ? '' : 'Noise, clarity, silences and loudness are made on Hoola’s own server.'}</p></form>`)}
        ${stage('Before and after', `<b>Before and after</b>`, c.file ? `<div class="hv-card hv-ba"><span class="hv-mut hv-sm">Before · ${esc(c.file.name)}</span>${wave('b' + c.file.name, 60, 'thin')}
            <span class="hv-mut hv-sm">After</span>${c.out ? wave('a' + c.out.id, 60) : '<span class="hv-mut hv-sm">Not cleaned yet</span>'}
            <div class="hv-acts">${c.before ? `<button type="button" class="hv-btn" data-a="playurl" data-val="before">${ic('play', 12)}Hear before</button>` : ''}${c.out ? `<button type="button" class="hv-btn" data-a="play" data-id="${esc(c.out.id)}" data-s="12">${ic('play', 12)}Hear after</button>
              <button type="button" class="hv-btn" data-a="dlmenu" data-id="${esc(c.out.id)}" aria-haspopup="menu">Download${ic('down', 12)}</button>` : ''}</div></div>` : empty('Nothing here yet', 'Choose a recording on the left.'))}</div>`;
    },

    sfx() {
      const f = UI.fx, w = ready('eleven') ? '' : whyNot('eleven'), g = gate(paid(w || (f.prompt.trim().length < 3 ? 'Describe the sound first.' : '')));
      return `<div class="hv-split hv-tool">${panel('Sound effects', `<form class="hv-form" data-f="sfx"><b class="hv-t">Sound effects</b>${w ? warnNote('Sounds from words run on ElevenLabs only. ' + w) : ''}
          <div class="hv-fld"><label class="hv-lab" for="hvFx">Describe the sound</label><textarea id="hvFx" class="hv-in" rows="3" maxlength="450" data-m="UI.fx.prompt" placeholder="A temple bell, far away, soft echo">${esc(f.prompt)}</textarea></div>
          <div class="hv-row2">${dd('Length', 'picklen', 'UI.fx.seconds', f.seconds ? `${f.seconds} seconds` : 'Auto')}
            <div class="hv-fld"><span class="hv-lab">Loop</span><button type="button" class="hv-chip${f.loop ? ' on' : ''}" data-a="fxloop" aria-pressed="${f.loop}">Loops smoothly</button></div></div>
          <div class="hv-fld"><span class="hv-lab">Takes</span>${seg('UI.fx.takes', [[1, '1'], [2, '2'], [3, '3'], [4, '4']], f.takes, null, 'Takes')}</div>
          <button class="hv-cta" data-qbtn="fx" data-label="Make ${f.takes} take${f.takes > 1 ? 's' : ''}"${g.a}><span>Make ${f.takes} take${f.takes > 1 ? 's' : ''}</span></button>${g.l}<p class="hv-hint c" data-qline="fx"></p>
          <div class="hv-fld"><span class="hv-lab">Quick game sounds</span><span class="hv-mut hv-sm">Coin, jump, click and more, made on Hoola’s own server. The same choice always gives the same sound.</span>
            <div class="hv-pads">${(D.sfx || []).map(p => `<button type="button" class="hv-chip" data-a="preset" data-val="${esc(p)}">${ic('fx', 12)}${esc(String(p).replace(/_/g, ' '))}</button>`).join('') || '<span class="hv-mut hv-sm">No quick sounds on this server.</span>'}</div></div></form>`)}
        ${stage('Takes', `<b>Takes</b><span class="hv-mut hv-sm">${f.out.length ? esc(f.prompt.slice(0, 60)) : ''}</span>`, f.out.length ? `<div class="hv-list">${f.out.map((t, i) => `<article class="hv-card hv-mv">${playBtn(t.id, `Play version ${i + 1}`, 12)}
            <span class="hv-vt"><b>Version ${i + 1}</b><span class="hv-mut hv-sm hv-num">${t.seconds ? secs(t.seconds) : ''}</span></span><button type="button" class="hv-btn" data-a="dlmenu" data-id="${esc(t.id)}" aria-haspopup="menu">Download${ic('down', 12)}</button></article>`).join('')}</div>`
          : empty('No sounds yet', 'Describe a sound on the left, or tap a quick game sound.'))}</div>`;
    },

    sounds() {
      return `<div class="hv-doc hv-soundsp"><div class="hv-doch"><div><b class="hv-t">Everything you have made</b><p class="hv-mut">The newest ${num(D.limits?.history || 300)} are kept. Download any of them in the format you need.</p></div></div>
        <div class="hv-stage flat">${stageSounds(UI.snd, 'snd')}</div></div>`;
    },

    dict() {
      return `<div class="hv-doc"><div class="hv-doch"><div><b class="hv-t">Pronunciation dictionary</b><p class="hv-mut">How your names, places and product words must be said. Hoola applies these before any voice reads your words.</p></div><span class="hv-grow"></span>
          <button type="button" class="hv-btn" data-a="dictimp">${ic('upload', 14)}Import a list</button></div>
        ${UI.dict.imp ? `<form class="hv-card hv-form tight" data-f="ruleimp"><label class="hv-lab" for="hvDImp">One word a line: word, say it as, sounds (IPA, optional), language (optional)</label>
            <textarea id="hvDImp" class="hv-in" rows="5" data-m="UI.dict.text" placeholder="Mithas,Mi-thaas,mɪˈt̪ʰaːs,hi&#10;Nashik,Naa-shik">${esc(UI.dict.text)}</textarea>
            <div class="hv-acts"><button class="hv-btn dark">Add these words</button><button type="button" class="hv-btn" data-a="dictimp">Cancel</button></div></form>` : ''}
        <form class="hv-card hv-dform" data-f="rule"><div class="hv-fld"><label class="hv-lab" for="hvRWord">Word</label><input id="hvRWord" class="hv-in" maxlength="60" required placeholder="Mithas"></div>
          <div class="hv-fld"><label class="hv-lab" for="hvRSay">Say it as</label><input id="hvRSay" class="hv-in" maxlength="120" required placeholder="Mi-thaas"></div>
          <div class="hv-fld"><label class="hv-lab" for="hvRIpa">Sounds (IPA)</label><input id="hvRIpa" class="hv-in" maxlength="120" placeholder="mɪˈt̪ʰaːs"></div>
          ${dd('Languages', 'pickrlang', 'UI.dict.lang', UI.dict.lang ? short(UI.dict.lang) : 'All')}<button class="hv-btn dark">${ic('plus', 14)}Add a word</button></form>
        ${D.rules.length ? `<div class="hv-card hv-tablew"><table class="hv-table"><thead><tr><th>Word</th><th>Say it as</th><th>Sounds (IPA)</th><th>Languages</th><th><span class="hv-sr">Remove</span></th></tr></thead><tbody>${D.rules.map(r => `<tr><td><b>${esc(r.word)}</b></td><td>${esc(r.say)}</td>
            <td class="hv-ipa">${esc(r.ipa || '')}</td><td>${r.lang ? esc(short(r.lang)) : 'All'}</td><td class="r"><button type="button" class="hv-btn s danger" data-a="rmrule" data-id="${esc(r.id)}">Remove</button></td></tr>`).join('')}</tbody></table></div>`
          : empty('No words yet', 'Add your shop name, your town, a product: anything a voice says wrongly.')}
        <p class="hv-mut hv-sm">A word matches whole, in any letter case. Your sounds keep the words as you wrote them.</p></div>`;
    },

    settings() {
      const u = D.usage || {};
      const state = e => e.state === 'ready' ? ['ok', 'Ready'] : e.state === 'off' ? ['', 'Off'] : ['warn', 'Not connected'];
      const DF = defs();
      const drows = [['Language', 'defl', DF.lang ? langLabel(DF.lang) : 'Auto, from my words'], ['Download as', 'deff', fmtOf(DF.fmt || D.formats[0].id).name], ['Takes', 'deft', String(DF.takes || 2)], ['Voice', 'defv', DF.voice ? vname(DF.voice) : 'Hoola Auto']];
      return `<div class="hv-doc"><div class="hv-sgrid2">
        <section class="hv-card hv-sec" aria-label="Engines"><b class="hv-t">Engines</b><span class="hv-mut hv-sm">Hoola Auto picks the engine for each job. You can pin one.</span>
          ${(D.engines || []).map(e => { const [k, t] = state(e); return `<div class="hv-eng"><span class="hv-dot ${k}"></span><span class="hv-vt"><b>${esc(ENG[e.id] || e.name || e.id)}</b><span class="hv-mut hv-sm">${esc(e.does || '')}${e.langs ? ' · ' + esc(e.langs) : ''}</span></span><span class="hv-st ${k}">${t}</span></div>`; }).join('') || '<p class="hv-mut">No engine list from the server.</p>'}
          <button type="button" class="hv-dd" data-a="pickengine" data-k="S.engine" data-def="1" aria-haspopup="menu"><span>Use: ${esc(engName(S.engine))}</span>${ic('down', 14)}</button>
          <button type="button" class="hv-lnk" data-a="go" data-p="langs">${ic('globe', 14)}What works in each of ${num(D.langs.length)} languages</button></section>
        <section class="hv-card hv-sec" aria-label="What things cost"><b class="hv-t">What things cost</b>
          <table class="hv-table plain"><tbody>${(D.prices || []).map(p => `<tr><td>${esc(p.name || p.label || p.job)}</td><td class="r hv-num">${p.credits ? `${cr(p.credits)}` : 'Free'}</td></tr>`).join('') || '<tr><td>The price shows before every job.</td></tr>'}</tbody></table>
          <span class="hv-mut hv-sm">You always see the price before you tap. ${typeof u.credits_left === 'number' ? `${cr(u.credits_left)} left this month.` : ''}</span></section>
        <section class="hv-card hv-sec" aria-label="Defaults"><b class="hv-t">Defaults</b>${drows.map(([n, a, v]) => `<div class="hv-def"><span>${n}</span><button type="button" class="hv-dd s" data-a="${a}" aria-haspopup="menu"><span>${esc(v)}</span>${ic('down', 12)}</button></div>`).join('')}
          <span class="hv-mut hv-sm">Every page starts from these, on every device.</span></section>
        <section class="hv-card hv-sec" aria-label="Keep my sounds"><b class="hv-t">Keep my sounds</b>
          <div class="hv-def"><span>Delete what I make after</span><button type="button" class="hv-dd s" data-a="defkeep" aria-haspopup="menu"><span>${esc(KEEP[+(D.settings?.keep_days || 0)] || 'Never')}</span>${ic('down', 12)}</button></div>
          <span class="hv-mut hv-sm">Sounds, dubs and the videos you gave for them go after that time. Your voices and your dictionary are always kept.</span></section>
        ${appsSec()}
        <section class="hv-card hv-sec" aria-label="This month"><b class="hv-t">This month${u.month ? ' · ' + esc(u.month) : ''}</b>
          ${[['Characters spoken', num(u.characters)], ['Minutes of sound', String(u.minutes || 0)], ['Things made', num(u.made)], ['Credits used', num(u.credits_used || u.credits || 0)], ['Kept on this server', `${num(u.kept)} of ${num(u.kept_max || 300)}`]]
            .map(([a, b]) => `<div class="hv-def"><span class="hv-mut">${a}</span><b class="hv-num">${esc(b)}</b></div>`).join('')}</section>
        <section class="hv-card hv-sec" aria-label="The rules Hoola keeps"><b class="hv-t">The rules Hoola keeps</b><ul class="hv-checks">${[...(D.rules_kept || []), 'The AI mark goes in every file (always on).'].map(t => `<li class="ok">${ic('check', 14)}${esc(t)}</li>`).join('')}</ul></section></div></div>`;
    },

    langs() {
      return `<div class="hv-doc"><div class="hv-doch"><div><b class="hv-t">Every language</b><p class="hv-mut">What works where, across ${num(D.langs.length)} languages and accents. A language with no engine is never read in another language instead.</p></div><span class="hv-grow"></span>
          <button type="button" class="hv-btn" data-a="go" data-p="settings">${ic('back', 14)}Settings</button></div>
        ${search('hvLq', 'UI.langQ', 'Search a language', UI.langQ || '')}
        <div class="hv-card hv-tablew"><table class="hv-table"><thead><tr><th>Language</th><th>Speech</th><th>Your voice</th><th>Dialogue</th><th>Dubbing</th><th>Voices</th><th>In our test</th></tr></thead><tbody id="hvLangRows">${langRows()}</tbody></table></div></div>`;
    },
  };
  const KEEP = {0: 'Never', 7: '7 days', 30: '30 days', 90: '90 days'};
  // "For your own apps": app keys (shown once) + webhooks (signed, public https only)
  function appsSec() {
    const a = UI.apps;
    if (!a) return `<section class="hv-card hv-sec hv-wide" aria-label="For your own apps"><b class="hv-t">For your own apps</b><p class="hv-mut">Loading…</p></section>`;
    const once = (t, v, note) => `<div class="hv-card hv-once" role="status"><b>${esc(t)}</b><code class="hv-code">${esc(v)}</code><div class="hv-acts"><button type="button" class="hv-btn" data-a="copyval" data-val="${esc(v)}">${ic('copy', 13)}Copy</button>
      <button type="button" class="hv-btn" data-a="oncehide">Done</button></div><span class="hv-mut hv-sm">${esc(note)}</span></div>`;
    return `<section class="hv-card hv-sec hv-wide" aria-label="For your own apps"><b class="hv-t">For your own apps</b>
      <span class="hv-mut hv-sm">Let your own website or program make sounds with your voices. Everything it makes uses your credits, at most ${num(a.rate_hour || 120)} calls an hour a key.</span>
      ${UI.newKey ? once(`New key: ${UI.newKey.name}`, UI.newKey.key, UI.newKey.note) : ''}
      <b class="hv-lab">App keys</b>${(a.keys || []).length ? `<div class="hv-list">${a.keys.map(k => `<div class="hv-eng"><span class="hv-vt"><b>${esc(k.name)}</b><span class="hv-mut hv-sm hv-num">hv_live_…${esc(k.last4)} · ${plural(k.calls || 0, 'call')}${k.used_at ? ' · used ' + esc(ago(k.used_at)) : ' · not used yet'}</span></span>
          <button type="button" class="hv-btn s danger" data-a="keyrm" data-id="${esc(k.id)}">Remove</button></div>`).join('')}</div>` : '<span class="hv-mut hv-sm">No app keys yet.</span>'}
      ${(a.keys || []).length < (a.max_keys || 5) ? `<form class="hv-inline" data-f="appkey"><label class="hv-sr" for="hvKeyN">Key name</label><input id="hvKeyN" class="hv-in" maxlength="40" data-m="UI.appName" value="${esc(UI.appName)}" placeholder="My shop website">
        <button class="hv-btn dark">${ic('plus', 14)}Make a key</button></form>` : ''}
      ${UI.newHook ? once('Webhook signing secret', UI.newHook.secret, UI.newHook.note) : ''}
      <b class="hv-lab">Webhooks</b><span class="hv-mut hv-sm">Hoola tells your server when a sound or a dub is ready (${esc((a.events || []).join(', '))}).</span>
      ${(a.hooks || []).length ? `<div class="hv-list">${a.hooks.map(h => `<div class="hv-eng"><span class="hv-vt"><b class="hv-brk">${esc(h.url)}</b><span class="hv-mut hv-sm">${h.last_at ? `Last: ${esc(h.last_event || '')} · ${esc(h.last_status || '')} · ${esc(ago(h.last_at))}` : 'Nothing sent yet'}</span></span>
          <button type="button" class="hv-btn s" data-a="hooktest" data-id="${esc(h.id)}">Send a test</button><button type="button" class="hv-btn s danger" data-a="hookrm" data-id="${esc(h.id)}">Remove</button></div>`).join('')}</div>` : '<span class="hv-mut hv-sm">No webhooks yet.</span>'}
      ${(a.hooks || []).length < (a.max_hooks || 3) ? `<form class="hv-inline" data-f="apphook"><label class="hv-sr" for="hvHookU">Your server's address</label><input id="hvHookU" class="hv-in" type="url" maxlength="400" data-m="UI.hookUrl" value="${esc(UI.hookUrl)}" placeholder="https://your-site.com/hoola">
        <button class="hv-btn dark">${ic('plus', 14)}Add a webhook</button></form>` : ''}
      <details class="hv-more"><summary>How your app calls Hoola</summary><ul class="hv-doors">${(a.doors || []).map(x => `<li><code>${esc(x.method)} ${esc(x.path)}</code> <span class="hv-mut">${esc(x.does)}</span></li>`).join('')}</ul>
        <span class="hv-mut hv-sm">Send the key as <code>Authorization: Bearer hv_live_…</code>. Every webhook carries <code>${esc(a.signature || '')}</code>.</span></details></section>`;
  }
  async function loadApps() { try { UI.apps = await api('GET', `${A}/apps`); } catch (e) { UI.apps = {keys: [], hooks: [], events: [], doors: []}; toast(e.message, true); } if (PAGE === 'settings') draw(); }
  function langRows() {
    const lo = String(UI.langQ || '').trim().toLowerCase();
    const cell = v => v === 'yes' ? '<span class="hv-st ok">Yes</span>' : v === 'premium' ? '<span class="hv-src">ElevenLabs</span>' : '<span class="hv-mut">No</span>';
    return D.langs.filter(l => !lo || [l.code, l.name, l.native].join(' ').toLowerCase().includes(lo)).map(l => `<tr><td><b>${esc(l.name)}</b><br><span class="hv-mut hv-sm">${esc([l.native !== l.name ? l.native : '', l.region].filter(Boolean).join(' · '))}</span></td>
      <td>${l.speech === 'none' ? '<span class="hv-mut">No engine yet</span>' : cell(l.speech)}</td><td>${cell(l.clone)}</td><td>${cell(l.dialogue)}</td><td>${cell(l.dub)}</td>
      <td class="hv-num">${num(l.voices)}</td><td>${esc(QUAL[l.quality] || 'Not tested yet')}</td></tr>`).join('');
  }

  // ------------------------------------------------------------------ voice library ---
  function libVoice(id) { return (UI.lib.list || []).find(v => v.id === id); }
  function voiceDetail() {
    const shared = UI.vtab === 'shared', v = shared ? libVoice(UI.vsel) : voice(UI.vsel);
    if (!v) return `<div class="hv-stageb">${empty('Choose a voice', 'Tap a voice to hear it and see what it is good for.')}</div>`;
    const langs = (v.langs || []).map(c => lang(c)?.name || c);
    const gT = gate(shared ? 'Add it to your voices first.' : !v.ready ? (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.') : paid(''));
    return `<div class="hv-stageb"><div class="hv-rh"><span class="hv-ava l" aria-hidden="true">${initial(v.name)}</span><span class="hv-vt"><b class="hv-t">${esc(v.name)}</b>
        <span class="hv-mut hv-sm hv-num">${shared ? `Shared library${v.uses ? ` · used ${num(v.uses)} times` : ''}` : v.kind === 'hoola' ? 'Hoola voice' : 'Your voice'}</span></span></div>
      <p class="hv-serifp">${esc(v.line || [v.tone, v.accent ? `from ${v.accent}` : '', v.use ? `good for ${v.use.toLowerCase()}` : ''].filter(Boolean).join(', ') || 'A natural voice.')}</p>
      <div class="hv-card hv-sample"><button type="button" class="hv-play" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}'s sample"${!shared && !v.ready ? ' disabled' : ''}>${ic('play', 12)}</button>${wave(v.id, 40, 'thin')}</div>
      <label class="hv-lab" for="hvTry">Hear it say your words</label>
      <div class="hv-tryrow"><input id="hvTry" class="hv-in" maxlength="200" data-m="UI.tryText" value="${esc(UI.tryText)}" placeholder="Hello, today's special offer is…"><button type="button" class="hv-btn" data-a="tryv" data-qbtn="tryv" data-label="Try"${gT.a}><span>Try</span></button></div>${gT.l}
      <dl class="hv-dl"><dt>Speaks</dt><dd>${esc(langs.length ? langs.slice(0, 3).join(', ') + (langs.length > 3 ? ` + ${langs.length - 3} more` : '') : 'Every language its engine knows')}</dd>
        ${v.use ? `<dt>Good for</dt><dd>${esc(v.use)}</dd>` : ''}<dt>Engine</dt><dd>${esc(shared ? 'ElevenLabs · premium' : `${engName(v.engine)}${v.tier === 'premium' ? ' · premium' : ''}`)}</dd></dl>
      <span class="hv-grow"></span>
      ${shared ? `<button type="button" class="hv-cta" data-a="libadd" data-id="${esc(v.id)}"><span>Add to my voices</span></button><p class="hv-hint c">Shared voices were offered by their owners for anyone to use.</p>`
        : `<button type="button" class="hv-cta" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}><span>Use this voice</span></button>`}</div>`;
  }
  async function libLoad(more) {
    const f = UI.vf, key = JSON.stringify([f.q, f.lang, f.gender, f.age, f.accent, f.use, f.sort]);
    if (!more && UI.lib.key === key && UI.lib.list) return;
    if (!more) { UI.lib = {key, list: null, more: false, page: 1, ready: true, why: '', busy: true}; if (PAGE === 'voices') draw(); } else UI.lib.page++;
    const p = new URLSearchParams({q: f.q, lang: f.lang, gender: f.gender, age: f.age, accent: f.accent, use: f.use, sort: f.sort, page: String(UI.lib.page)});
    try { const r = await api('GET', `${A}/library?${p}`);
      if (UI.lib.key !== key) return;
      UI.lib.ready = r.ready !== false; UI.lib.why = scrub(r.why || ''); UI.lib.more = !!r.more;
      UI.lib.list = [...(more ? UI.lib.list || [] : []), ...(r.voices || []).map(v => ({langs: [], ...v, id: String(v.id), ready: true}))]; }
    catch (e) { UI.lib.list = UI.lib.list || []; UI.lib.ready = false; UI.lib.why = scrub(e.message); }
    UI.lib.busy = false; if (PAGE === 'voices' && UI.vtab === 'shared') draw();
  }

  // ------------------------------------------------------------------ one dub ---
  function dubView() {
    const d = UI.dub;
    if (!d || d.id !== ARG) return `<div class="hv-doc"><p class="hv-mut">Loading the dub…</p></div>`;
    const tab = UI.dubTab || d.langs?.[0]?.code || '', L = (d.langs || []).find(l => l.code === tab) || {}, DL = UI.dubLines;
    const st = s => s === 'ready' ? 'Ready' : s === 'failed' ? 'Failed' : s === 'waiting' ? 'Waiting' : 'Working';
    const rows = DL && DL.lang === tab ? DL.lines : null, ed = DL ? DL.editable !== false : false, own = !!DL?.own;
    const changed = own && (rows || []).some(r => r.edited);
    const speakers = [...new Set((rows || d.lines || []).map(r => r.speaker).filter(Boolean))];
    const lname = L.name || langLabel(tab);
    return `<div class="hv-split hv-tool"><section class="hv-panel wide" aria-label="Lines"><div class="hv-chips"><span class="hv-mut">From</span><span class="hv-chip static">${esc(d.source_lang ? langLabel(d.source_lang) + ', found by Hoola' : 'Found by Hoola')}</span><span class="hv-mut">to</span>
          ${(d.langs || []).map(l => `<button type="button" class="hv-chip${l.code === tab ? ' on' : ''}" data-a="dubtab" data-val="${esc(l.code)}" aria-pressed="${l.code === tab}">${esc(short(l.code) || l.name)}${l.status === 'ready' ? '' : ' · ' + st(l.status)}</button>`).join('')}
          ${d.status !== 'working' ? `<button type="button" class="hv-chip" data-a="dubmore" aria-haspopup="menu">${ic('plus', 12)}Add a language</button>` : ''}</div>
        ${d.status === 'failed' ? warnNote(d.error || 'This dub could not be made.') : ''}
        ${DL && DL.lang === tab && DL.editable === false ? `<p class="hv-note">${esc(scrub(DL.why || 'These lines were made in their own voices and cannot be changed one by one here.'))}</p>` : ''}
        <div class="hv-tablew"><table class="hv-table hv-dubt"><thead><tr><th>Time</th><th>Speaker</th><th>They said</th><th>${esc(short(tab) || 'Dubbed')}</th><th><span class="hv-sr">Actions</span></th></tr></thead><tbody>
          ${rows == null ? '<tr><td colspan="5" class="hv-mut">Loading the lines…</td></tr>' : rows.length ? rows.map(r => `<tr class="${r.too_long ? 'long' : ''}"><td class="hv-num">${secs(r.start)}</td><td><span class="hv-who t${Math.max(0, speakers.indexOf(r.speaker)) % 4}">${esc(r.speaker || '')}</span></td>
              <td>${esc(r.src || '')}</td><td>${ed ? `<label class="hv-sr" for="hvDl${r.n}">Line ${r.n} in ${esc(lname)}</label><textarea id="hvDl${r.n}" class="hv-lt" rows="2" lang="${esc(tab)}" data-dubline="${r.n}">${esc(r.dst || '')}</textarea>` : `<span lang="${esc(tab)}">${esc(r.dst || '')}</span>`}
                ${r.too_long ? `<span class="hv-why">Longer than the ${(+r.end - +r.start).toFixed(1)} s they spoke. Shorten it, or it is read a little faster.</span>` : ''}</td>
              <td class="r"><span class="hv-acts nw">${playBtn('line:' + r.n, `Play line ${r.n}`, 11, ' o s')}${r.edited && own ? '<span class="hv-st work">Changed</span>' : ''}${ed && !own ? `<button type="button" class="hv-ib s" data-a="dubredo" data-n="${r.n}" aria-label="Redo line ${r.n}" title="Redo this line · 1 credit">${ic('redo', 14)}</button>` : ''}</span></td></tr>`).join('')
            : '<tr><td colspan="5" class="hv-mut">The lines appear when the speech is read.</td></tr>'}</tbody></table></div>
        ${ed && !own ? `<p class="hv-mut hv-sm">Change any ${esc(lname)} line, then redo only that line · ${cr(DL.credits_redo || 1)} a line</p>` : ''}
        ${ed && own ? `<div class="hv-ctarow">${L.remaking ? `<span class="hv-st work">Making the changed lines…</span><span class="hv-mut hv-sm">The page checks every 10 seconds.</span>`
            : `<button type="button" class="hv-btn dark" data-a="ownredo"${changed ? '' : ' disabled'}>${ic('redo', 14)}Make the changes</button><span class="hv-mut hv-sm">${esc(DL.note || '')}</span>`}</div>
          ${L.remake_error ? warnNote(L.remake_error) : ''}` : ''}</section>
      <aside class="hv-stage hv-side2" aria-label="Preview and export"><div class="hv-stageb">
        ${L.video_id ? `<video class="hv-media" id="hvDubMedia" controls preload="none" playsinline data-src="${esc(L.video_id)}"></video>` : L.audio_id ? `<audio class="hv-media" id="hvDubMedia" controls preload="none" data-src="${esc(L.audio_id)}"></audio>`
          : `<p class="hv-mut">${L.status === 'failed' ? 'This language could not be made.' : 'This language is still being made. The page checks every few seconds.'}</p>`}
        <b class="hv-t">Speakers</b>${speakers.length ? speakers.map((s, i) => `<div class="hv-role"><span class="hv-dot t${i % 4}"></span><span><b>${esc(s)}</b> · <span class="hv-mut">${d.mode === 'own' ? 'their own voice' : 'a matched voice'}, in ${esc(short(tab))}</span></span></div>`).join('') : '<p class="hv-mut hv-sm">Found when the speech is read.</p>'}
        <b class="hv-t">Download</b><div class="hv-acts">${L.video_id ? `<button type="button" class="hv-btn" data-a="dubdl" data-val="video">Video with the dub</button>` : ''}${L.audio_id ? `<button type="button" class="hv-btn" data-a="dubdl" data-val="mp3">Sound only, MP3</button>` : ''}
          ${L.status === 'ready' ? `<button type="button" class="hv-btn" data-a="dubdl" data-val="srt">Subtitles, SRT</button><button type="button" class="hv-btn" data-a="dubdl" data-val="vtt">Subtitles, VTT</button>` : ''}</div>
        <span class="hv-grow"></span><button type="button" class="hv-btn" data-a="go" data-p="dub">${ic('back', 14)}All dubs</button>
        <p class="hv-hint c hv-num">${esc([d.seconds ? secs(d.seconds) + ' video' : '', d.mode === 'own' ? 'their own voices' : 'matched voices'].filter(Boolean).join(' · '))}</p></div></aside></div>`;
  }
  async function loadDub(id) {
    try { UI.dub = await api('GET', `${A}/dub/${q(id)}`); } catch (e) { toast(e.message, true); return; }
    if (PAGE !== 'dub' || ARG !== id) return;
    if (!UI.dubTab || !(UI.dub.langs || []).some(l => l.code === UI.dubTab)) UI.dubTab = UI.dub.langs?.[0]?.code || '';
    crumb(); draw(); dubLines(id); dubPoll(id);
  }
  async function dubLines(id) {
    const lc = UI.dubTab; if (!lc) return;
    try { const r = await api('GET', `${A}/dub/${q(id)}/lines?lang=${q(lc)}`); UI.dubLines = {lang: lc, lines: r.lines || [], editable: r.editable, why: r.why, credits_redo: r.credits_redo, own: !!r.own, note: r.note || ''}; }
    catch { UI.dubLines = {lang: lc, lines: (UI.dub.lines || []).map((l, i) => ({n: i + 1, start: l.start, end: l.end, speaker: l.speaker, src: l.text, dst: (l.tr || {})[lc] || ''})), editable: false, why: ''}; }
    if (PAGE === 'dub' && ARG === id) { const keep = ROOT.querySelector(':focus')?.id; draw(); $$('.hv-lt').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }); if (keep) $('#' + keep)?.focus(); }
  }
  async function dubMedia() { const m = $('#hvDubMedia'); if (!m) return; try { m.src = await blobUrl(`${A}/audio?id=${q(m.dataset.src)}`); } catch { /* the controls stay, the file comes when ready */ } }
  function dubPoll(id) { clearTimeout(dubPoll.t); const remake = (UI.dub?.langs || []).some(l => l.remaking);
    if (UI.dub?.status !== 'working' && !remake) return;
    dubPoll.t = setTimeout(() => { if (PAGE === 'dub' && ARG === id && ROOT && !ROOT.hidden) { if (remake) URLS.clear(); loadDub(id); } }, remake ? 10000 : 3000); }

  // ------------------------------------------------------------------ recording in the page ---
  const REC = {};
  async function recStart(k) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { toast('This browser cannot record here. Choose a recording instead.', true); return; }
    try { const st = await navigator.mediaDevices.getUserMedia({audio: true}), mr = new MediaRecorder(st), parts = [];
      mr.ondataavailable = e => { if (e.data.size) parts.push(e.data); };
      mr.onstop = () => { st.getTracks().forEach(t => t.stop()); const s = (Date.now() - REC[k].t0) / 1000; delete REC[k];
        const type = (mr.mimeType || 'audio/webm').split(';')[0], ext = /ogg/.test(type) ? 'ogg' : /mp4|m4a|aac/.test(type) ? 'm4a' : 'webm';
        const blob = new Blob(parts, {type}); recFile(k, new File([blob], `recording-${k}.${ext}`, {type}), s); };
      const limit = k === 'chg' ? 300 : 30;
      REC[k] = {mr, t0: Date.now()}; mr.start(); draw();
      const tick = () => { if (!REC[k]) return; const t = (Date.now() - REC[k].t0) / 1000, el = $(`[data-rect="${k}"]`);
        if (el) el.textContent = k === 'chg' ? secs(t) : `${secs(t)} of 0:30`; if (t >= limit) { REC[k].mr.stop(); return; } setTimeout(tick, 400); }; tick(); }
    catch (e) { toast(`The microphone did not start: ${e.message}`, true); }
  }
  // a recording or a picked file for the voice pages: uploaded at once, its length kept for the price and the checks
  async function recFile(k, file, s) {
    const slot = {name: file.name, up: true, secs: s || 0};
    if (k === 'chg') UI.chg.file = slot; else UI.clone[k] = slot;
    draw(); if (!s) slot.secs = await fileSecs(file);
    if (k === 'chg') UI.chg.secs = slot.secs;
    try { slot.file_id = await up(file); } catch (e) { slot.err = scrub(e.message); toast(e.message, true); }
    slot.up = false; if (['mine', 'changer'].includes(PAGE)) draw();
  }
  async function consentLine(code) {
    if (!code || UI.cline[code]) return;
    try { UI.cline[code] = await api('GET', `${A}/consent-line?lang=${q(code)}`); } catch (e) { UI.cline[code] = {line: '', english: '', lang: ''}; toast(e.message, true); }
    if (PAGE === 'mine') draw();
  }
  // a picked file on a tool page: uploaded at once, its length read for the price
  async function pageFile(k, file) {
    if (k === 'chg') return recFile('chg', file, 0);
    const slot = {name: file.name, up: true};
    const set = o => { if (k === 'pod') UI.dlg.pod.file = o; else if (k === 'imp') UI.imp.file = o; else if (k === 'dub') UI.dubNew.file = o; else if (k === 'cl') UI.cl.file = o; };
    set(slot); draw();
    const s = ['dub', 'cl'].includes(k) ? await fileSecs(file) : 0;
    if (k === 'dub') UI.dubNew.secs = s; if (k === 'cl') { UI.cl.secs = s; UI.cl.out = null; try { UI.cl.before = URL.createObjectURL(file); } catch { /* no preview */ } }
    try { slot.file_id = await up(file); } catch (e) { slot.err = scrub(e.message); toast(e.message, true); }
    slot.up = false; draw();
  }

  // ------------------------------------------------------------------ events ---
  function speechBody() { return {text: S.text, voice: S.voice, lang: S.lang || 'auto', style: S.style, speed: +S.speed, expressive: +S.expressive, takes: +S.takes,
    engine: S.engine, format: S.format, rules: !!S.rules}; }
  function askHoola(text) { C.ask = text; C.autosend = true; go('chat'); }
  // her defaults: saved on the server (PUT /settings, kept for every device), the local copy only while that is not there
  const defs = () => { const z = D.settings || store.get('hv.defaults', {}); return {lang: z.lang, voice: z.voice, fmt: z.format || z.fmt, takes: z.takes, engine: z.engine, style: z.style}; };
  async function setDef(k, v) {
    const cur = defs(), body = {lang: cur.lang || S.lang, voice: cur.voice || S.voice, format: cur.fmt || S.format, takes: +(cur.takes || S.takes), engine: cur.engine || S.engine, style: cur.style || S.style};
    body[{fmt: 'format'}[k] || k] = v;
    try { const r = await api('PUT', `${A}/settings`, body); D.settings = r?.settings || r || body; toast('Saved as your default.'); }
    catch (e) { const d = store.get('hv.defaults', {}); d[k] = v; store.set('hv.defaults', d); toast(`Kept on this device only: ${e.message}`, true); }
    draw(); }
  function onClick(ev) {
    const b = ev.target.closest('[data-a]'); if (!b || b.disabled || !ROOT.contains(b)) return;
    const d = b.dataset, id = d.id;
    switch (d.a) {
      case 'back': return back ? back() : leave();
      case 'go': return go(d.p, d.arg);
      case 'slim': if (UI.nav) { UI.nav = false; return side(); } UI.slim = !UI.slim; store.set('hv.slim', UI.slim); return side();
      case 'navon': UI.nav = true; side(); return $('#hvSide .hv-nv[aria-current]')?.focus();
      case 'navoff': UI.nav = false; return side();
      case 'seg': { const v = isNaN(+d.val) || d.val === '' ? d.val : +d.val; setM(d.m, v);
        if (d.m === 'UI.vtab') { UI.vsel = ''; if (v === 'shared') { draw(); return libLoad(); } }
        if (PAGE === 'chat') return refreshSet();
        return draw(); }
      case 'tab': { const f = d.k === 'side' ? UI.side : UI.snd; f.tab = d.val; $$(`[data-a="tab"][data-k="${d.k}"]`).forEach(x => x.setAttribute('aria-selected', String(x === b))); return refreshSide(); }
      case 'setopen': C.setOpen = !C.setOpen; refreshSet(); if (C.setOpen) $('#hvSetp [aria-checked="true"]')?.focus(); return;
      case 'setdone': C.setOpen = false; refreshSet(); return $('[data-a="setopen"]')?.focus();
      case 'setreset': Object.assign(S, {make: 'speech', lang: browserLang(), style: Object.keys(D.styles || {})[0] || '', speed: 1, takes: 2, engine: 'auto'}); return refreshSet();
      case 'picklang': { const k = d.k, cur = k === 'dubadd' ? '' : String(getM(k) || '');
        return choose(b, {title: 'Language', find: `Search ${num(D.langs.length)} languages`, cur, list: langList(!!d.auto, d.need), onPick: v => {
          if (k === 'dubadd') { if (!UI.dubNew.langs.includes(v)) UI.dubNew.langs.push(v); return draw(); }
          setM(k, v); if (k === 'UI.clone.lang') consentLine(v); if (PAGE === 'chat') return refreshSet(); draw(); }}); }
      case 'pickvoice': return choose(b, {title: 'Voice', find: 'Search: warm, news, Brazilian…', cur: S.voice, list: voiceList(), onPick: v => { S.voice = v; if (PAGE === 'chat') refreshSet(); else draw(); }});
      case 'pickengine': return choose(b, {title: 'Engine', cur: S.engine, list: engList(), onPick: v => { S.engine = v; if (d.def) setDef('engine', v); else if (PAGE === 'chat') refreshSet(); else draw(); }});
      case 'pickfmt': return choose(b, {title: 'Format', cur: S.format, list: D.formats.map(f => ({v: f.id, label: f.name, sub: f.note})), onPick: v => { S.format = v; draw(); }});
      case 'pickgender': return choose(b, {title: 'Gender', cur: UI.design.gender, list: [{v: '', label: 'Not set'}, {v: 'female', label: 'Female'}, {v: 'male', label: 'Male'}], onPick: v => { UI.design.gender = v; draw(); }});
      case 'pickbase': return choose(b, {title: 'Starting voice', find: 'Search voices', cur: UI.remix.base, list: voiceList(v => v.ready), onPick: v => { UI.remix.base = v; draw(); }});
      case 'pickinto': return choose(b, {title: 'Into', find: 'Search voices', cur: UI.chg.voice, list: D.voices.filter(v => v.kind !== 'hoola' || v.engine === 'eleven').map(v => ({v: v.id,
          label: v.kind === 'clone' ? `${v.name} · your voice` : v.name, sub: v.tone || '', why: v.engine !== 'eleven' ? `${v.kind === 'hoola' ? 'This voice' : 'Your voice'} lives on ${engName(v.engine)}; the changer needs a voice on ElevenLabs` : !v.ready ? 'Not ready yet' : ''})),
        onPick: v => { UI.chg.voice = v; draw(); }});
      case 'pickcast': { const i = +d.n; return choose(b, {title: `Voice of ${UI.dlg.cast[i].name}`, find: 'Search voices', cur: UI.dlg.cast[i].voice, list: voiceList(), onPick: v => { UI.dlg.cast[i].voice = v; draw(); }}); }
      case 'pickwho': { const n = +d.n; return choose(b, {title: 'Who says this line', cur: UI.dlg.lines[n].speaker, list: UI.dlg.cast.map(c => ({v: c.name, label: c.name, sub: vname(c.voice)})), onPick: v => { UI.dlg.lines[n].speaker = v; draw(); }}); }
      case 'pickpvoice': return choose(b, {title: 'Reading voice', find: 'Search voices', cur: UI.proj.voice || S.voice, list: voiceList(v => v.ready), onPick: v => { UI.proj.voice = v; draw(); }});
      case 'pickrole': { const c = UI.cast.characters[+d.n]; return choose(b, {title: `Voice for ${c.name}`, find: 'Search voices', cur: c.voice, list: voiceList(v => v.ready), onPick: v => { c.voice = v; draw(); }}); }
      case 'picklen': return choose(b, {title: 'Length', cur: UI.fx.seconds, list: [[0, 'Auto'], [2, '2 seconds'], [5, '5 seconds'], [10, '10 seconds'], [30, '30 seconds']].map(([v, label]) => ({v, label})), onPick: v => { UI.fx.seconds = +v; draw(); }});
      case 'pickrlang': return choose(b, {title: 'Languages', find: 'Search languages', cur: UI.dict.lang, list: [{v: '', label: 'All languages'}, ...langList(false, 'speech').map(l => ({...l, why: ''}))], onPick: v => { UI.dict.lang = v; draw(); }});
      case 'defl': return choose(b, {title: 'Language', find: 'Search languages', cur: defs().lang || 'auto', list: langList(true), onPick: v => { S.lang = v; setDef('lang', v); }});
      case 'deff': return choose(b, {title: 'Download as', cur: defs().fmt || D.formats[0].id, list: D.formats.map(f => ({v: f.id, label: f.name, sub: f.note})), onPick: v => { S.format = v; setDef('fmt', v); }});
      case 'deft': return choose(b, {title: 'Takes', cur: defs().takes || 2, list: [1, 2, 4].map(v => ({v, label: String(v)})), onPick: v => { S.takes = +v; setDef('takes', +v); }});
      case 'defkeep': return choose(b, {title: 'Delete what I make after', cur: +(D.settings?.keep_days || 0), list: [0, 7, 30, 90].map(v => ({v, label: KEEP[v], sub: v ? '' : 'Keep everything until I remove it'})),
        onPick: v => api('PUT', `${A}/settings`, {keep_days: +v}).then(r => { D.settings = r?.settings || r; toast(+v ? `Sounds older than ${KEEP[v]} will be deleted.` : 'Your sounds are kept until you remove them.'); draw(); }).catch(e => toast(e.message, true))});
      case 'copyval': return navigator.clipboard?.writeText(d.val).then(() => toast('Copied.'), () => toast('Copy did not work here. Select it and copy.', true));
      case 'oncehide': UI.newKey = null; UI.newHook = null; return draw();
      case 'keyrm': return confirm('Remove this app key? Apps using it stop working at once.') && act(() => api('DELETE', `${A}/apps/keys/${q(id)}`), loadApps);
      case 'hookrm': return confirm('Remove this webhook? Hoola stops telling that address.') && act(() => api('DELETE', `${A}/apps/hooks/${q(id)}`), loadApps);
      case 'hooktest': return act(() => api('POST', `${A}/apps/hooks/${q(id)}/test`), r => { toast(`Your server answered: ${r?.last_status || 'nothing'}.`, !/^2\d\d$/.test(r?.last_status || '')); loadApps(); }, b, 'Sending…');
      case 'defv': return choose(b, {title: 'Voice', find: 'Search voices', cur: defs().voice || '', list: voiceList(v => v.ready), onPick: v => { S.voice = v; setDef('voice', v); }});
      case 'vfilter': { const k = d.k, f = UI.vf;
        const opts = {lang: [{v: '', label: 'Any language'}, ...langList(false).map(l => ({...l, why: ''}))], gender: [['', 'Any gender'], ['female', 'Female'], ['male', 'Male']],
          age: [['', 'Any age'], ['young', 'Young'], ['middle', 'Middle'], ['older', 'Older']],
          accent: [['', 'Any accent'], ...[...new Set(D.voices.map(v => v.accent).filter(Boolean))].sort().map(a => [a, a])],
          use: [['', 'Any use'], ...(UI.vtab === 'shared' ? ['ads', 'stories', 'narration', 'news', 'support', 'learning', 'social', 'reels', 'podcasts'].map(u => [u, u[0].toUpperCase() + u.slice(1)])
            : [...new Set(D.voices.map(v => v.use).filter(Boolean))].map(u => [u, u]))],
          sort: [['popular', 'Most used'], ['trending', 'Trending'], ['newest', 'Newest'], ['most_added', 'Most added']]}[k];
        return choose(b, {title: {lang: 'Language', gender: 'Gender', age: 'Age', accent: 'Accent', use: 'Use', sort: 'Sort'}[k], find: k === 'lang' ? 'Search languages' : '', cur: f[k],
          list: opts.map(o => Array.isArray(o) ? {v: o[0], label: o[1]} : o), onPick: v => { f[k] = v; if (UI.vtab === 'shared') libLoad(); else draw(); }}); }
      case 'vsel': UI.vsel = id; return draw();
      case 'libmore': return libLoad(true);
      case 'libadd': { const v = libVoice(id); if (!v) return;
        return act(() => api('POST', `${A}/library/add`, {id: v.id, owner: v.owner, name: v.name}), r => { toast(`${v.name} is in your voices now.`); UI.vtab = 'mine'; UI.vsel = r?.id || ''; side(); draw(); }, b, 'Adding…'); }
      case 'tryv': { const v = voice(UI.vsel), t = (UI.tryText || '').trim(); if (!v) return; if (!t) { toast('Type a few words first.'); return $('#hvTry')?.focus(); }
        return act(() => api('POST', `${A}/tts`, {text: t, voice: v.id, lang: 'auto', style: S.style, speed: 1, takes: 1, engine: 'auto', format: S.format, rules: true}),
          r => { const it = (r.items || [])[0]; draw(); if (it) play(it.id, '', `${v.name} · your words`); }, b, 'Making…'); }
      case 'way': UI.way = d.val; return draw();
      case 'dlmenu': return menu(b, dlItems(id));
      case 'takemenu': { const on = kept(id), it = C.items?.find?.(x => x.id === id) || D.history.find(x => x.id === id) || {};
        return menu(b, [{label: on ? 'Not kept' : 'Keep this take', icon: 'check', run: () => keep(id)}, ...(canDub(it) ? [{label: 'Dub it into another language', icon: 'globe', run: () => dubIt(b, id)}] : []), {sep: true}, ...dlItems(id)]); }
      case 'sndmenu': { const h = D.history.find(x => x.id === id);
        return menu(b, [...dlItems(id, h?.title), ...(h && canDub(h) ? [{label: 'Dub it into another language', icon: 'globe', run: () => dubIt(b, id)}] : []), {sep: true}, {label: 'Remove', icon: 'trash', danger: true, run: () => removeSound(id)}]); }
      case 'dubit': return dubIt(b, id);
      case 'stream': { if (S.text.trim().length < 2) { toast('Type the words to speak first.', true); return $('#hvText')?.focus(); }
        b.disabled = true;
        return api('POST', `${A}/tts/stream`, speechBody()).then(async r => { const a = $('#hvAudio');
          await play('stream:' + Date.now(), r.url, `${r.voice_name || 'Premium voice'} · playing while it is made`);
          a?.addEventListener('ended', () => { load().then(() => { side(); if (PAGE === 'speech') { S.out = D.history.slice(0, 1); draw(); } }); }, {once: true}); })
          .catch(e => { toast(e.message, true); noCredit(e); }).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'mvmenu': { const v = voice(id); return menu(b, [{label: 'Use this voice', run: () => { S.voice = id; go('speech'); }, disabled: !v?.ready},
          {label: 'Change this voice', run: () => { UI.way = 'remix'; UI.remix.base = id; draw(); }, disabled: !v?.ready}, {sep: true},
          {label: 'Remove', icon: 'trash', danger: true, run: () => confirm('Remove this voice? Its recordings are deleted. Sounds already made are kept.') && act(() => api('DELETE', `${A}/voice?id=${q(id)}`))}]); }
      case 'idea': C.ask = d.val; { const ta = $('#hvAsk'); if (ta) { ta.value = d.val; ta.focus(); grow(ta); } } sendState(); return price('chat', chatQuote(), chatLine);
      case 'ask': return chatSend(d.val);
      case 'askabout': { const it = S.out.find(x => x.id === id) || D.history.find(x => x.id === id); return askHoola(`Change "${it?.title || 'this take'}": `); }
      case 'plus': return pickFiles('audio/*,video/*,.pdf,.txt,.docx,.epub', true).then(chatFiles);
      case 'fx': C.files.splice(+d.n, 1); { const t = $('#hvTray'); if (t) { t.innerHTML = trayHTML(); t.hidden = !C.files.length; } } return;
      case 'improve': { const ta = $('#hvAsk'); if (!ta?.value.trim()) { ta?.focus(); toast('Write a few words first.'); return; }
        if (window.HoolaImprove?.ui) return window.HoolaImprove.ui.open(ta.value, {section: 'voice', onUse: t => { C.ask = ta.value = String(t).slice(0, 4000); grow(ta); ta.focus(); sendState(); toast('Words updated: edit them or send.'); }});
        return api('POST', '/api/prompting/understand', {text: ta.value, section: 'voice'}).then(r => { const t = r?.prompt || r?.text; if (t) { C.ask = ta.value = String(t).slice(0, 4000); grow(ta); toast('Words updated: edit them or send.'); } }).catch(e => toast(e.message, true)); }
      case 'newchat': return api('POST', `${A}/chat/new`).then(c => { C.title = c.title || 'Vocal chat'; return openChat(c.id); }).catch(e => toast(e.message, true));
      case 'chats': return api('GET', `${A}/chats`).then(r => { const cs = r.chats || []; if (!cs.length) return toast('No earlier Vocal chats yet.');
        choose(b, {title: 'Earlier Vocal chats', cur: C.conv, list: cs.map(c => ({v: c.id, label: c.title || 'Vocal chat', sub: c.at ? ago(c.at) : ''})), onPick: v => { C.title = (cs.find(x => x.id === v) || {}).title || 'Vocal chat'; openChat(v); }}); }).catch(e => toast(e.message, true));
      case 'direct': { const s = C.lastSend; if (!s) return; b.disabled = true;
        return act(() => api('POST', `${A}/tts`, {text: s.text, voice: s.voice, lang: s.lang || 'auto', style: s.style, speed: +s.speed, expressive: +s.expressive, takes: +s.takes, engine: s.engine, format: s.format, rules: !!s.rules, chat: C.conv}),
          async () => { C.lastSend = null; await chatLoad(false); paintChat(); toast('Made.'); }, b, 'Making…'); }
      case 'tag': { const ta = $('#hvText'); if (!ta) return; const t = `[${d.val}] `, a = ta.selectionStart ?? ta.value.length, z = ta.selectionEnd ?? a;
        ta.value = ta.value.slice(0, a) + t + ta.value.slice(z); S.text = ta.value; ta.focus(); ta.selectionStart = ta.selectionEnd = a + t.length; onInput({target: ta}); return; }
      case 'play': return id.startsWith('line:') ? playLine(+id.slice(5)) : play(id);
      case 'playurl': return d.val === 'before' && UI.cl.before ? play('before', UI.cl.before, 'Before') : null;
      case 'keep': return keep(id);
      case 'cwidth': return setWidth(d.val);
      case 'unfold': UI.peek = true; return setWidth(UI.cw < 550 ? 'narrow' : UI.cw > 760 ? 'wide' : 'balanced', UI.cw);
      case 'openchat': { const c = (UI.recent || []).find(x => x.id === id); C.title = c?.title || 'Vocal chat'; if (PAGE !== 'chat') go('chat'); return openChat(id); }
      case 'compare': { const ids = String(d.val || '').split(',').filter(Boolean); if (!ids.length) return; UI.queue = ids.slice(1); return play(ids[0]); }
      case 'closebar': $('#hvAudio').pause(); $('#hvBar').hidden = true; return;
      case 'hear': { const v = voice(id) || libVoice(id); b.disabled = true;
        const path = libVoice(id) && UI.vtab === 'shared' ? (v.preview ? (String(v.preview).startsWith('/api/') ? v.preview : `${A}/library/preview?url=${q(v.preview)}`) : '') : `${A}/voice/preview?id=${q(id)}&lang=${q(S.lang === 'auto' ? ((v?.langs || [])[0] || 'en') : S.lang)}`;
        if (!path) { b.disabled = false; return toast('This voice has no sample to hear.'); }
        return blobUrl(path).then(u => play('hear:' + id, u, `${v?.name || 'Voice'} · sample`)).catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'usev': S.voice = id; toast(`${vname(id)} is your voice now.`); return go('speech');
      case 'rec': return recStart(d.k);
      case 'recstop': return REC[d.k]?.mr.stop();
      case 'pickrec': return pickFiles('audio/*', false).then(fs => fs[0] && recFile(d.k, fs[0], 0));
      case 'pickfile': return pickFiles(d.accept || '*/*', false).then(fs => fs[0] && pageFile(d.k, fs[0]));
      case 'dpick': UI.design.pick = d.val; return draw();
      case 'dsave': return act(() => api('POST', `${A}/voice/design/save`, {pid: UI.design.pick, name: UI.design.name || 'My designed voice'}),
        () => { UI.design = {desc: '', gender: '', previews: [], pick: '', name: ''}; toast('Voice saved.'); side(); draw(); }, b, 'Saving…');
      case 'rxchip': UI.remix.change = [UI.remix.change.trim(), d.val.toLowerCase()].filter(Boolean).join(', '); return draw();
      case 'rmrule': return act(() => api('DELETE', `${A}/rule?id=${q(id)}`));
      case 'dictimp': UI.dict.imp = !UI.dict.imp; return draw();
      case 'podopen': UI.dlg.podOpen = true; return draw();
      case 'podclose': UI.dlg.podOpen = false; return draw();
      case 'dladd': UI.dlg.lines.push({speaker: UI.dlg.cast[UI.dlg.lines.length % UI.dlg.cast.length]?.name || 'Speaker', text: ''}); draw(); return $(`#hvLt${UI.dlg.lines.length - 1}`)?.focus();
      case 'dlrm': UI.dlg.lines.splice(+d.n, 1); return draw();
      case 'castadd': { const rv = D.voices.filter(v => v.ready); UI.dlg.cast.push({name: `Speaker ${UI.dlg.cast.length + 1}`, voice: (rv[UI.dlg.cast.length % Math.max(1, rv.length)] || {}).id || ''}); return draw(); }
      case 'castrm': { const gone = UI.dlg.cast.splice(+d.n, 1)[0]; UI.dlg.lines.forEach(l => { if (l.speaker === gone.name) l.speaker = UI.dlg.cast[0].name; }); return draw(); }
      case 'dlgmake': { const dd2 = UI.dlg, cast = Object.fromEntries(dd2.cast.map(c => [c.name, c.voice]));
        return act(() => api('POST', `${A}/dialogue`, {lines: dd2.lines.filter(l => (l.text || '').trim()).map(l => ({speaker: l.speaker, text: l.text})), cast, lang: dd2.lang || 'auto', style: dd2.style, engine: 'auto', mode: dd2.mode, reactions: !!dd2.reactions, music: dd2.music ? 'soft' : ''}),
          r => { side(); draw(); if (r?.id) play(r.id); toast('Ready.'); }, b, 'Making…'); }
      case 'impopen': UI.imp.open = true; return draw();
      case 'impclose': UI.imp.open = false; return draw();
      case 'newproj': UI.cast = null; UI.chN = 0; UI.edited = {}; UI.proj = {id: '', title: '', voice: S.voice, lang: S.lang === 'auto' ? 'en' : S.lang, chapters: [{title: 'Chapter 1', text: ''}]}; return go('reading');
      case 'proj': UI.cast = null; UI.chN = 0; UI.edited = {}; UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === id) || null)); return go('reading');
      case 'chsel': UI.chN = +d.n; return draw();
      case 'chadd': UI.proj.chapters.push({title: `Chapter ${UI.proj.chapters.length + 1}`, text: ''}); UI.chN = UI.proj.chapters.length - 1; return draw();
      case 'saveproj': return saveProj(b).then(ok => ok && toast('Saved.'));
      case 'cast': return saveProj().then(ok => ok && act(() => api('POST', `${A}/project/cast`, {id: UI.proj.id, n: +d.n}), r => { UI.cast = {n: +d.n, ...r}; draw(); }, b, 'Reading…'));
      case 'readch': return saveProj().then(ok => ok && readChapter(+d.n, b));
      case 'readall': return readAll(b);
      case 'export': return act(() => api('POST', `${A}/project/export`, {id: UI.proj.id, format: d.val}), r => { toast('Exported. It is in Your sounds.'); side(); draw(); if (r?.id) download(r.id, d.val === 'srt' || d.val === 'm4b' ? '' : d.val, UI.proj.title); }, b, 'Exporting…');
      case 'rmproj': return confirm('Remove this reading? Sounds already made stay in Your sounds.') && act(() => api('DELETE', `${A}/project?id=${q(id)}`), () => { UI.proj = null; go('studio'); });
      case 'dubrm': UI.dubNew.langs = UI.dubNew.langs.filter(c => c !== d.val); return draw();
      case 'dubopen': UI.dub = null; UI.dubTab = ''; UI.dubLines = null; return go('dub', id);
      case 'dubtab': UI.dubTab = d.val; UI.dubLines = null; draw(); dubMedia(); return dubLines(ARG);
      case 'dubredo': { const n = +d.n; return act(() => api('POST', `${A}/dub/${q(ARG)}/lines/${n}/redo`, {lang: UI.dubTab}), async () => { URLS.clear(); toast(`Line ${n} was made again.`); await loadDub(ARG); }, b); }
      case 'ownredo': { const first = (UI.dubLines?.lines || []).find(r => r.edited); if (!first) return;
        if (!confirm('Make the changed lines again? ElevenLabs charges for the seconds it makes again.')) return;
        return act(() => api('POST', `${A}/dub/${q(ARG)}/lines/${first.n}/redo`, {lang: UI.dubTab}), async r => { toast(`Making ${plural(r?.lines || 1, 'changed line')} again${r?.credits ? ' · ' + cr(r.credits) : ''}.`); await loadDub(ARG); }, b, 'Starting…'); }
      case 'dubdl': { const L = (UI.dub.langs || []).find(l => l.code === UI.dubTab) || {}, nm = `${(UI.dub.title || 'dub').replace(/\.[a-z0-9]+$/i, '')}-${UI.dubTab}`;
        if (d.val === 'video') return saveFile(`${A}/audio?id=${q(L.video_id)}`, `${nm}.mp4`);
        if (d.val === 'mp3') return saveFile(`${A}/audio?id=${q(L.audio_id)}&format=mp3`, `${nm}.mp3`);
        return saveFile(`${A}/dub/${q(ARG)}/subtitles?lang=${q(UI.dubTab)}&format=${d.val}`, `${nm}.${d.val}`); }
      case 'dubmore': { const have = new Set((UI.dub.langs || []).map(l => l.code));
        return choose(b, {title: 'Add a language', find: 'Search languages', cur: '', list: langList(false, 'dub').filter(l => !have.has(l.v)), onPick: v =>
          act(() => api('POST', `${A}/dub/${q(ARG)}/langs`, {langs: [v]}), r => { toast(`A new dub in ${short(v)} is being made from the same video.`); UI.dub = null; UI.dubTab = ''; UI.dubLines = null; side(); if (r?.id) go('dub', r.id); else draw(); }, b, 'Starting…')}); }
      case 'fxloop': UI.fx.loop = !UI.fx.loop; return draw();
      case 'preset': return act(() => api('POST', `${A}/sfx`, {preset: d.val, seed: +UI.seed || 1}), r => { const it = r?.items?.[0] || r; if (it?.id) { UI.fx.out = [it, ...UI.fx.out].slice(0, 8); } side(); draw(); if (it?.id) play(it.id); }, b);
    }
  }
  function keep(id) { const i = UI.kept.indexOf(id); if (i >= 0) UI.kept.splice(i, 1); else UI.kept.push(id); UI.kept = UI.kept.slice(-500); store.set('hv.kept', UI.kept);
    if (PAGE === 'chat') { $$('[data-vset]').forEach(n => { n._h = ''; }); return drawSets(); } draw(); }
  function removeSound(id) { if (!confirm('Remove this from Your sounds? The file is deleted.')) return;
    act(() => api('DELETE', `${A}/history?id=${q(id)}`), () => { URLS.forEach((u, k) => { if (k.includes(`id=${q(id)}`)) URLS.delete(k); }); side(); if (PAGE === 'chat') refreshSide(); else draw(); }); }
  async function playLine(n) {
    const m = $('#hvDubMedia'), r = (UI.dubLines?.lines || []).find(x => x.n === n); if (!m || !r) return;
    if (!m.src) await dubMedia(); try { m.currentTime = +r.start || 0; await m.play(); const end = +r.end || 0;
      const stop = () => { if (m.currentTime >= end) { m.pause(); m.removeEventListener('timeupdate', stop); } }; if (end) m.addEventListener('timeupdate', stop); } catch { /* the player shows its own state */ }
  }
  async function readChapter(n, b) {
    return act(() => api('POST', `${A}/project/chapter`, {id: UI.proj.id, n}), r => { delete UI.edited[n]; UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id) || UI.proj)); side(); draw(); if (r?.id) play(r.id); }, b, 'Making…');
  }
  async function readAll(b) {
    if (!await saveProj()) return;
    const todo = UI.proj.chapters.map((c, i) => [c, i]).filter(([c, i]) => !c.audio || UI.edited[i]).map(([, i]) => i);
    for (const n of todo) { if (!ROOT || PAGE !== 'reading') return; UI.chN = n; draw(); const btn = $('[data-a="readall"]'); if (btn) { btn.disabled = true; btn.textContent = `Making chapter ${n + 1}…`; }
      try { await api('POST', `${A}/project/chapter`, {id: UI.proj.id, n}); delete UI.edited[n]; await load(); UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id) || UI.proj)); }
      catch (e) { toast(e.message, true); break; } }
    side(); draw();
  }
  async function saveProj(btn) {
    const p = UI.proj;
    try { if (btn) btn.disabled = true;
      const cast = UI.cast ? Object.fromEntries((UI.cast.characters || []).map(c => [c.name, c.voice])) : undefined;
      const out = await api('POST', `${A}/project`, {id: p.id, title: p.title, voice: p.voice || S.voice, lang: p.lang, chapters: p.chapters.map(c => ({title: c.title, text: c.text})), ...(cast ? {cast} : {})});
      await load(); const chapters = p.chapters; UI.proj = JSON.parse(JSON.stringify(out)); if (!UI.proj.chapters) UI.proj.chapters = chapters; crumb(); side(); draw(); return true; }
    catch (e) { toast(e.message, true); if (btn?.isConnected) btn.disabled = false; return false; }
  }
  function onInput(ev) {
    const t = ev.target;
    const rn = /^UI\.dlg\.cast\.(\d+)\.name$/.exec(t.dataset?.m || '');      // a renamed speaker keeps their lines
    if (rn) { const old = UI.dlg.cast[+rn[1]]?.name; UI.dlg.lines.forEach(l => { if (l.speaker === old) l.speaker = t.value; }); }
    if (t.dataset?.m) { setM(t.dataset.m, t.type === 'checkbox' ? t.checked : t.dataset.t === 'num' ? +t.value : t.value);
      $$(`[data-show="${t.dataset.m}"]`).forEach(x => { x.textContent = `${(+t.value).toFixed(2)}x`; }); }
    if (t.dataset?.ch != null && UI.proj?.chapters?.[+t.dataset.ch]?.audio) UI.edited[+t.dataset.ch] = true;
    if (t.id === 'hvText') { const c = $('#hvCount'); if (c) c.textContent = countLine(); price('speech', ttsQuote(S.text), r => autoLine(r, short(S.lang))); }
    if (t.id === 'hvAsk') { grow(t); sendState(); price('chat', chatQuote(), chatLine); }
    if (t.id === 'hvSq' || t.id === 'hvSnq') refreshSide();
    if (t.id === 'hvLq') { const tb = $('#hvLangRows'); if (tb) tb.innerHTML = langRows(); }
    if (t.id === 'hvVq') { clearTimeout(onInput.t); onInput.t = setTimeout(() => { if (UI.vtab === 'shared') libLoad(); else { const id = t.id, a = t.selectionStart; draw(); const n = $('#' + id); if (n) { n.focus(); try { n.setSelectionRange(a, a); } catch { /* */ } } } }, 300); }
    if (t.dataset?.m === 'S.speed' && PAGE === 'chat') { const s = $('#hvSum'); if (s) s.textContent = summary(); }
    if (t.classList?.contains('hv-lt')) { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }
    if (t.id === 'hvFx') { const b = $('[data-qbtn="fx"]'); if (b && ready('eleven') && !broke()) { const ok = UI.fx.prompt.trim().length >= 3; if (ok === b.disabled) { const a = t.selectionStart; draw(); const n = $('#hvFx'); if (n) { n.focus(); n.setSelectionRange(a, a); } } } }
    if (t.dataset?.m?.startsWith('UI.dlg.lines') && t.tagName === 'TEXTAREA') { const b = $('[data-qbtn="dlg"]'); const has = UI.dlg.lines.some(l => (l.text || '').trim());
      if (b && (has === b.disabled) && !speakWhy(UI.dlg.lang, 'auto') && !broke()) { const id = t.id, a = t.selectionStart; draw(); const n = $('#' + id); if (n) { n.focus(); n.setSelectionRange(a, a); } } else price('dlg', dlgQuote()); }
  }
  function onChange(ev) {
    const t = ev.target;
    if (t.dataset?.dubline) { const n = +t.dataset.dubline, text = t.value;
      return api('PUT', `${A}/dub/${q(ARG)}/lines/${n}`, {lang: UI.dubTab, text}).then(() => { const r = (UI.dubLines?.lines || []).find(x => x.n === n); if (r) { r.dst = text; r.edited = true; }
        if (UI.dubLines?.own) { toast(`Line ${n} saved. Tap Make the changes when you are done.`); draw(); } else toast(`Line ${n} saved. Redo it to hear the change.`); }).catch(e => toast(e.message, true)); }
    if (t.dataset?.m) {
      if (t.type === 'checkbox' || t.type === 'range') setM(t.dataset.m, t.type === 'checkbox' ? t.checked : +t.value);
      if (/^UI\.dlg\.cast\.\d+\.name$/.test(t.dataset.m)) return draw();
      if (t.dataset.redraw || (t.type === 'checkbox' && t.dataset.m.startsWith('UI.'))) return draw();
      if (t.dataset.m === 'S.rules') { const c = $('#hvCount'); if (c) c.textContent = countLine(); }
    }
  }
  function onKey(ev) {
    if (ev.target.closest?.('[data-drag="chatw"]') && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(ev.key)) { ev.preventDefault();
      const sp = $('#hvSplit'), max = sp ? sp.clientWidth - 320 : 1400;
      UI.cw = ev.key === 'Home' ? 380 : ev.key === 'End' ? max : UI.cw + (ev.key === 'ArrowLeft' ? -40 : 40); return setWidth('open', Math.max(380, UI.cw)); }
    if (ev.key !== 'Escape') return;
    if (C.setOpen && PAGE === 'chat') { ev.preventDefault(); C.setOpen = false; refreshSet(); return $('[data-a="setopen"]')?.focus(); }
    if (UI.nav) { UI.nav = false; side(); return $('.hv-menu')?.focus(); }
  }
  function onSubmit(ev) {
    const f = ev.target.closest('form[data-f]'); if (!f) return;
    ev.preventDefault();
    const v = id => ($(id)?.value || '').trim(), btn = ev.submitter || f.querySelector('button:not([type=button])');
    switch (f.dataset.f) {
      case 'chat': return chatSend();
      case 'speech': if (S.text.trim().length < 2) { toast('Type the words to speak first.', true); return $('#hvText')?.focus(); }
        return act(() => api('POST', `${A}/tts`, speechBody()), r => { S.out = r.items || []; side(); draw(); if (S.out[0]) play(S.out[0].id); toast(`${plural(S.out.length, 'take')} ready${r.lang_name ? ' · ' + r.lang_name : ''}.`); }, btn, 'Making…');
      case 'clone': { const c = UI.clone, sample = c.sample?.file_id ? c.sample : c.consent;
        return act(() => api('POST', `${A}/voice/clone`, {name: c.name || 'My voice', file_id: sample.file_id, consent_file_id: c.consent.file_id, lang: c.lang, consent: c.ok === true}),
          () => { UI.clone = {sample: null, consent: null, name: 'My voice', ok: false, lang: c.lang}; toast('Your voice is ready.'); side(); draw(); }, btn, 'Making…'); }
      case 'design': if (UI.design.desc.trim().length < 8) { toast('Describe the voice in a few more words.', true); return $('#hvDDesc')?.focus(); }
        return act(() => api('POST', `${A}/voice/design`, {description: UI.design.desc, gender: UI.design.gender, preview: true}),
          r => { UI.design.previews = (r.previews || []).filter(p => p && p.audio_id); UI.design.pick = ''; if (!UI.design.previews.length) toast('The engine gave no options to hear this time. Try other words.', true); draw(); }, btn, 'Making 3 options…');
      case 'remix': if (!UI.remix.change.trim()) { toast('Say what to change.', true); return $('#hvRChange')?.focus(); }
        return act(() => api('POST', `${A}/voice/remix`, {base: UI.remix.base, change: UI.remix.change, name: UI.remix.name || `${vname(UI.remix.base)} · changed`}),
          () => { UI.remix.change = ''; UI.remix.name = ''; toast('The new voice is ready.'); side(); draw(); }, btn, 'Making…');
      case 'podcast': { const p = UI.dlg.pod, src = p.src === 'file' ? {file_id: p.file?.file_id} : p.src === 'url' ? {url: p.url} : {text: p.text};
        if (!Object.values(src)[0]) { toast(p.src === 'file' ? 'Choose the file first.' : p.src === 'url' ? 'Type the web address first.' : 'Paste the text first.', true); return; }
        return act(() => api('POST', `${A}/podcast`, {...src, minutes: Math.max(1, Math.min(15, +p.minutes || 5)), hosts: UI.dlg.cast.slice(0, 2).map(c => ({name: c.name, voice: c.voice})), lang: UI.dlg.lang || 'auto'}),
          r => { UI.dlg.lines = (r.lines || []).map(l => ({speaker: l.speaker, text: l.text})); const names = new Set(UI.dlg.cast.map(c => c.name));
            UI.dlg.lines.forEach(l => { if (!names.has(l.speaker) && UI.dlg.cast.length < 6) { UI.dlg.cast.push({name: l.speaker, voice: (D.voices.find(x => x.ready) || {}).id || ''}); names.add(l.speaker); } });
            UI.dlg.title = r.title || ''; UI.dlg.podOpen = false; draw(); toast('The script is ready. Change any line, then make it.'); }, btn, 'Writing…'); }
      case 'dialogue': return;
      case 'import': { const im = UI.imp, src = im.src === 'file' ? {file_id: im.file?.file_id} : im.src === 'url' ? {url: im.url} : {text: im.text};
        if (!Object.values(src)[0]) { toast('Add what to import first.', true); return; }
        return act(() => api('POST', `${A}/project/import`, {...src, title: im.title}), p => { UI.imp = {open: false, src: 'file', url: '', text: '', title: '', file: null}; UI.cast = null; UI.chN = 0; UI.edited = {}; UI.proj = JSON.parse(JSON.stringify(p)); go('reading'); }, btn, 'Importing…'); }
      case 'dub': { const n = UI.dubNew;
        return act(() => api('POST', `${A}/dub`, {file_id: n.file.file_id, langs: n.langs, mode: n.mode, keep_sound: !!n.keep, ...(n.mode === 'matched' && n.speakers ? {speakers: n.speakers} : {})}),
          r => { UI.dubNew = {file: null, langs: [], mode: n.mode, keep: n.keep, secs: 0, speakers: n.speakers}; UI.dub = null; UI.dubLines = null; go('dub', r.id); }, btn, 'Starting…'); }
      case 'change': return act(() => api('POST', `${A}/change`, {file_id: UI.chg.file.file_id, voice: UI.chg.voice, denoise: !!UI.chg.denoise}), r => { UI.chg.out = r; side(); draw(); if (r?.id) play(r.id); }, btn, 'Changing…');
      case 'cleanup': { const c = UI.cl, prem = ready('eleven');
        return act(() => api('POST', `${A}/cleanup`, {file_id: c.file.file_id, denoise: !!c.denoise, voice: !!c.echo, silence: !!c.silence, level: !!c.level, people: prem && !!c.people, music: prem && !!c.music}),
          r => { UI.cl.out = r; side(); draw(); if (r?.id) play(r.id); toast('Cleaned.'); }, btn, 'Cleaning…'); }
      case 'sfx': return act(() => api('POST', `${A}/sfx`, {prompt: UI.fx.prompt.trim(), seconds: +UI.fx.seconds, loop: !!UI.fx.loop, takes: +UI.fx.takes}), r => { UI.fx.out = r.items || []; side(); draw(); if (UI.fx.out[0]) play(UI.fx.out[0].id); }, btn, 'Making…');
      case 'appkey': return act(() => api('POST', `${A}/apps/keys`, {name: UI.appName || 'My app'}), r => { UI.newKey = r; UI.appName = ''; loadApps(); }, btn, 'Making…');
      case 'apphook': if (!UI.hookUrl.trim()) { toast("Type your server's address first.", true); return $('#hvHookU')?.focus(); }
        return act(() => api('POST', `${A}/apps/hooks`, {url: UI.hookUrl.trim()}), r => { UI.newHook = r; UI.hookUrl = ''; loadApps(); }, btn, 'Adding…');
      case 'rule': return act(() => api('POST', `${A}/rule`, {word: v('#hvRWord'), say: v('#hvRSay'), ipa: v('#hvRIpa'), lang: UI.dict.lang}), null, btn);
      case 'ruleimp': if (!UI.dict.text.trim()) { toast('Paste the words first.', true); return $('#hvDImp')?.focus(); }
        return act(() => api('POST', `${A}/rules/import`, {text: UI.dict.text}), r => { const n = r?.added ?? r?.count, sk = r?.skipped || []; UI.dict = {imp: !!sk.length, text: sk.map(x => x.line).join('\n'), lang: UI.dict.lang}; toast(`${n != null ? plural(n, 'word') + ' added' : 'Words added'}${sk.length ? ` · ${sk.length} left out: ${sk[0].why || 'not understood'}` : ''}.`, !!sk.length); draw(); }, btn, 'Adding…');
    }
  }
  // the Speech page on its own, inside another frame (Create Studio's Voice tool)
  async function openEmbed() { window.HoolaVocal.stopEmbed?.(); window.HoolaVocal._embed = {leave}; mount(); await load(); go('speech'); }
  return {open, leave, openEmbed};
};
window.HoolaVocal.mountSpeech = (el, ctx) => { const v = window.HoolaVocal({...ctx, embed: el}); v.openEmbed(); return v; };
// Create Studio leaves its Voice tool: the embedded page stops its sound (a page taken out of the DOM would keep playing)
window.HoolaVocal.stopEmbed = () => { const e = window.HoolaVocal._embed; window.HoolaVocal._embed = null; e?.leave(); };
