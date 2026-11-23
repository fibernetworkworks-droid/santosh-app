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
    vset: '', vlang: '', vsort: '', cmp: [], cmpBlind: false, cmpPick: '', cmpLike: [], cmpOut: {}, cmpText: '',
    way: 'record', yv: 'home', mv: '', yvf: 'all', ren: '', rxp: {}, clone: {sample: null, consent: null, name: 'My voice', ok: false, lang: ''}, cline: {},
    design: {desc: '', gender: '', previews: [], pick: '', name: '', lang: ''}, remix: {base: '', change: '', name: '', made: ''},
    dlg: {mode: 'natural', reactions: false, music: false, podOpen: false, sel: 0, out: [], cp: null,
      lines: [{speaker: 'Host', text: '', pause: 0, cut: false}, {speaker: 'Guest', text: '', pause: 0, cut: false}],
      cast: [{name: 'Host', voice: ''}, {name: 'Guest', voice: ''}], lang: '', style: '', title: '',
      pod: {src: 'file', url: '', text: '', file: null, minutes: 5, kind: 'podcast', must: '', draft: null}},
    proj: null, chN: 0, cast: null, edited: {}, imp: {open: false, src: 'file', url: '', text: '', title: '', author: '', file: null, pv: null, keep: {}},
    sd: null, ab: {fmt: 'm4b', even: true}, para: null, editing: false,
    dubs: null, dub: null, dubTab: '', dubLines: null, dubNew: {file: null, langs: [], mode: 'matched', keep: true, secs: 0, speakers: 0, check: true, words: [], preview: ''},
    dubSel: null, dubHear: 'dub', dubRead: false, dubUndo: null, dubDl: {what: 'video', on: {}}, dubKeep: [],
    chg: {file: null, voice: '', denoise: true, secs: 0, out: null, view: '', start: 0, end: 0, close: 75, feel: 50, hear: 'after', cmp: ['', '', ''], cmpOut: null, cmpPick: '', rm: true, filt: '', fileFor: ''},
    cl: {file: null, denoise: true, noise: 'medium', voice: true, level: true, target: 'podcast', silence: false, gap: 1, people: false, music: false, secs: 0, out: null, heard: null, listening: false, kind: '', job: null, view: '', hear: 'after', filt: '', fileFor: ''},
    fx: {prompt: '', seconds: 0, loop: false, takes: 4, out: []}, seed: 1, snd: {tab: 'All', q: ''}, side: {tab: 'All', q: ''},
    dict: {imp: false, text: '', lang: ''}, apps: null, newKey: null, newHook: null, appName: '', hookUrl: '', kept: store.get('hv.kept', []), nav: false, slim: !!store.get('hv.slim', false),
    cw: Math.max(380, +store.get('hv.chatw', 640) || 640), cmode: store.get('hv.chatmode', 'balanced'), peek: false, recent: null, queue: []};

  const SP = {mode: store.get('hv.spmode', 'whole') === 'lines' ? 'lines' : 'whole', more: !!store.get('hv.spmore', false), sel: 0,
    made: store.get('hv.lines', {}), at: store.get('hv.lineat', {}), lv: {}, vp: null};
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
    star: 'M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z',
    chat: 'M4 5h16v11H9l-5 4z', speech: 'M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4', dialog: 'M3 6h11v8H7l-4 3zM10 17h7l4 3V9h-4',
    book: 'M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM8 7h7', dub: 'M4 5h8M8 3v2M5 11c2-1 4-3 5-6M7 8c1 2 3 3 5 3M13 21l4-9 4 9M14.5 18h5',
    lib: 'M4 19V5M9 19V5M14 19l3-14 4 1-3 14z', me: 'M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM6 11a6 6 0 0 0 12 0M12 17v4',
    change: 'M4 12h4l2-5 4 10 2-5h4', clean: 'M4 20l7-7M14 4l6 6-6 6-6-6zM3 14l3 3', fx: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
    sounds: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-3-3 3 3 0 0 1 3 3zM20 16a3 3 0 1 1-3-3 3 3 0 0 1 3 3z', dict: 'M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3zM8 9h7M8 13h5',
    gear: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19 12l2-1-1-3-2 .5-1.5-1.5.5-2-3-1-1 2h-2l-1-2-3 1 .5 2L6 7.5 4 7 3 10l2 1v2l-2 1 1 3 2-.5 1.5 1.5-.5 2 3 1 1-2h2l1 2 3-1-.5-2 1.5-1.5 2 .5 1-3-2-1z',
    plus: 'M12 5v14M5 12h14', x: 'M6 6l12 12M18 6L6 18', back: 'M15 18l-6-6 6-6', down: 'M6 9l6 6 6-6', up: 'M6 15l6-6 6 6',
    send: 'M12 19V5M6 11l6-6 6 6', wand: 'M4 20L15 9M14 4v3M19 9h-3M18 5l-2 2', clock: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 8v4l3 2',
    sliders: 'M4 7h10M18 7h2M4 17h4M12 17h8M16 5v4M10 15v4', side: 'M6 4h12a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM9 4v16',
    chev: 'M9 6l6 6-6 6', edit: 'M4 20l4-1L19 8l-3-3L5 16zM14 7l3 3', cutin: 'M3 9h11M9 15h12M14 6v6M9 12v6', swap: 'M7 7h13l-3-3M17 17H4l3 3',
    menu: 'M4 7h16M4 12h16M4 17h16', tone: 'M4 7h16M4 12h10M4 17h13', pause2: 'M9 6v12M15 6v12', say: 'M4 18l4-12 4 12M5.5 14h5M15 9v9M15 9c2.2 0 3.5.9 3.5 2.4S17.2 14 15 14',
    lines: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01', file: 'M6 3h8l4 4v14H6zM14 3v4h4', fold: 'M9 6l6 6-6 6M19 5v14', search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-3.5-3.5', upload: 'M12 16V4M7 9l5-5 5 5M5 20h14',
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
  // the big voice catalog is read in the background after a server restart: ask again until it is there (v0.999.155)
  let VW = 0, VWT = null;
  function voicesWait() {
    if (VWT || VW >= 15) return;
    VWT = setTimeout(async () => { VWT = null; VW += 1;
      try { const o = await api('GET', `${A}/overview`) || {};
        if (Array.isArray(o.voices) && o.voices.length > D.voices.length) {
          D.voices = fix({...o, langs: D.langs}, D.langs).voices; D.hoola_voices = o.hoola_voices;
          if (PAGE === 'voices') draw(); if ($("#hvVp")) vpPaint(); }
        D.voices_loading = !!o.voices_loading; if (!o.voices_loading && PAGE === 'voices') draw(); if (o.voices_loading) voicesWait(); } catch (e) { voicesWait(); } }, 4000);
  }
  const URLS = new Map();
  async function blobUrl(path) { if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const u = URL.createObjectURL(await r.blob()); URLS.set(path, u); return u; }
  async function load() {
    try { const o = await api('GET', `${A}/overview`) || {}; D = fix(o, Array.isArray(o.langs) ? o.langs : Object.entries(o.langs || {}).map(([code, name]) => ({code, name}))); }
    catch (e) { D = fix({error: e.message}, []); }
    if (D.voices_loading) voicesWait();
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
    try { const u = src || await blobUrl(`${A}/audio?id=${q(id)}`); const h = D.history.find(x => x.id === id) || C.items.find(x => x.id === id) || S.out.find(x => x.id === id) || UI.dlg.out.find(x => x.id === id);
      NOW = {id, title: title || (h?.title ? h.title + (h.take ? ` · take ${h.take}` : '') : 'Sound')}; const bar = $('#hvBar'); if (bar) bar.hidden = false;
      const n = $('#hvNow'); if (n) n.textContent = NOW.title; a.src = u; await a.play().catch(() => {}); syncPlay(); }
    catch (e) { toast(e.message || 'That sound could not be played.', true); }
  }
  function syncPlay() {
    const a = $('#hvAudio'), on = a && NOW && !a.paused;
    $$('.hv-vhear').forEach(b => { const me = !!NOW && on && NOW.id === 'hear:' + b.dataset.id, want = me ? 'pause' : 'play';
      b.classList.toggle('on', me); if (b.dataset.st !== want) { b.dataset.st = want; b.innerHTML = ic(want, 12); } });
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
    ROOT.addEventListener('focusin', e => { const l = e.target.dataset?.line; if (l != null && +l !== SP.sel) lnSel(+l); });
    ROOT.addEventListener('focusin', e => { const l = e.target.closest?.('.hv-dl[data-n]')?.dataset.n; if (l != null && PAGE === 'dialogue' && !UI.dlg.podOpen && +l !== UI.dlg.sel) dlSel(+l); });
    ROOT.addEventListener('pointerdown', e => { if (C.setOpen && PAGE === 'chat' && !e.target.closest('#hvSetp, [data-a="setopen"]')) { C.setOpen = false; refreshSet(); } });
    const a = $('#hvAudio'); ['play', 'pause', 'ended'].forEach(k => a.addEventListener(k, syncPlay));
    a.addEventListener('ended', () => { const n = UI.queue.shift(); if (n) play(n); });
    a.addEventListener('timeupdate', dlTick);          // Compare: the takes one after another
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
    const row = ([id, n, i]) => `<button type="button" class="hv-nv" data-a="go" data-p="${id}"${UI.slim && !UI.nav ? ` title="${n}"` : ''}${id === on ? ' aria-current="page"' : ''}>${ic(i)}<span>${n}</span></button>`;
    $('#hvSide').innerHTML = `<div class="hv-brand"><span class="hv-mark" aria-hidden="true">${markSvg()}</span><b>Hoola</b><span class="hv-badge">Vocal</span><span class="hv-grow"></span>
        <button type="button" class="hv-ib" data-a="slim" aria-label="${UI.nav ? 'Close the menu' : UI.slim ? 'Open the sidebar' : 'Close the sidebar'}" title="${UI.slim ? 'Open the sidebar' : 'Close the sidebar'}">${ic('side', 18)}</button></div>
      <button type="button" class="hv-nv" data-a="back"${UI.slim && !UI.nav ? ' title="Back to chat"' : ''}>${ic('back')}<span>Back to chat</span></button>
      <button type="button" class="hv-newchat" data-a="newchat" title="New vocal chat">${ic('plus')}<span>New vocal chat</span></button>
      ${NAV.map(([g, rows]) => `<span class="hv-gh">${g}</span>${rows.map(row).join('')}`).join('')}
      ${(UI.recent || []).filter(c => c.id !== C.conv).length ? `<span class="hv-gh">Recent chats</span>${UI.recent.filter(c => c.id !== C.conv).slice(0, 3).map(c => `<button type="button" class="hv-nv hv-rc" data-a="openchat" data-id="${esc(c.id)}"${UI.slim && !UI.nav ? ` title="${esc(c.title || 'Vocal chat')}"` : ''}${PAGE === 'chat' && c.id === C.conv ? ' aria-current="true"' : ''}>${ic('chat')}<span>${esc(c.title || 'Vocal chat')}</span></button>`).join('')}` : ''}
      <span class="hv-grow"></span>${creditCard()}`;
  }
  function crumb() {
    if (EMBED) return;
    const c = $('#hvCrumb'); if (!c) return;
    const p = PAGE === 'reading' && UI.proj ? ['Studio', UI.proj.title || 'New reading'] : PAGE === 'dub' && ARG && UI.dub ? ['Dubbing', UI.dub.title || 'Dub'] : PAGE === 'voices' && ARG === 'compare' ? ['Voice library', 'Compare voices']
      : PAGE === 'chat' ? [C.title && C.title !== 'Vocal chat' ? C.title : 'Vocal chat'] : [TITLE[PAGE] || ''];
    c.innerHTML = `<span>Vocal ·${p.length > 1 ? ' ' + esc(p[0]) + ' ·' : ''}</span><h1 class="hv-h" id="hvCTitle">${esc(p[p.length - 1])}</h1>`;
    topTools();
  }
  // the chat page's tools in the top bar: how wide the chat is, earlier chats, a new chat
  const WIDTHS = [['narrow', 'Narrow', 460], ['balanced', 'Balanced', 640], ['wide', 'Wide', 880], ['chat', 'Chat only', 0]];
  const widthNow = () => UI.cmode === 'chat' || folded() ? 'chat' : UI.cw < 550 ? 'narrow' : UI.cw > 760 ? 'wide' : 'balanced';
  function topTools() {
    const t = $('#hvTopR'); if (!t) return;
    if (PAGE === 'studio' || PAGE === 'reading') return readTools();
    if (PAGE === 'dub') return dubTools();
    if (PAGE === 'voices') { const hl = UI.vlang || (S.lang !== 'auto' ? S.lang : '') || 'en';
      t.innerHTML = ARG === 'compare' ? '' : `<button type="button" class="hv-btn s" data-a="vlang" aria-haspopup="menu">${ic('speech', 14)}<span class="hv-tlab">Every sample speaks <b>${esc(short(hl))}</b></span></button>
        <button type="button" class="hv-btn s dark" data-a="go" data-p="mine" aria-label="Make a voice">${ic('plus', 14)}<span class="hv-tlab">Make a voice</span></button>`; return; }
    t.innerHTML = PAGE !== 'chat' ? '' : `<button type="button" class="hv-sndbtn" data-a="go" data-p="sounds" aria-label="Your sounds${D?.history?.length ? ', ' + plural(D.history.length, 'sound') : ''}">${ic('sounds', 17)}${D?.history?.length ? `<span class="hv-cnt on">${num(D.history.length)}</span>` : ''}</button><div class="hv-widths" role="group" aria-label="Chat width">${WIDTHS.map(([k, l]) =>
        `<button type="button" data-a="cwidth" data-val="${k}" aria-pressed="${widthNow() === k}">${l}</button>`).join('')}</div>
      <button type="button" class="hv-ib" data-a="chats" aria-label="Earlier chats" title="Earlier chats">${ic('clock', 18)}</button>
      <button type="button" class="hv-ib" data-a="newchat" aria-label="New chat" title="New chat">${ic('plus', 18)}</button>`;
  }
  function go(page, arg) {
    window.HoolaMenu?.close(); if (SP.vp) vpClose(); if (UI.dlg.cp) { $('#hvCp')?.remove(); UI.dlg.cp = null; } if (UI.sd) { $('#hvSd')?.remove(); UI.sd = null; }
    try { chgStop(); } catch { /* not ready yet */ }
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
    mine() { consentLine(UI.clone.lang); if (UI.ren) setTimeout(() => { const i = $('#hvRen'); i?.focus(); i?.select(); }, 0); },
    voices() { if (UI.vtab === 'shared') libLoad(); },
    settings() { UI.newKey = null; UI.newHook = null; loadApps(); },
  };
  const AFTER = {
    voices() { vPrice(); },
    chat() {
      const host = $('#hvThread');
      if (host) { C.thread = window.HoolaChat ? HoolaChat.mount(host, {acts: ['copy'], scroller: $('#hvLog'), jump: true}) : plainThread(host); paintChat(C.sending); }
      else C.thread = null;
      const ta = $('#hvAsk'); if (ta) { ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); chatSend(); } });
        ta.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); chatFiles(fs); } }); grow(ta); }
      price('chat', chatQuote(), chatLine);
    },
    speech() {
      if (SP.mode === 'lines') { $$('.hv-lnt').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }); lnPrice(); return; }
      edSync(); price('speech', ttsQuote(S.text), r => autoLine(r, short(S.lang)));
      const ta = $('#hvText'); if (ta) ta.addEventListener('scroll', () => { const hi = $('#hvHi'); if (hi) hi.scrollTop = ta.scrollTop; });
    },
    mine() { const yl = r => r.credits != null ? cr(r.credits) : 'priced before you tap';
      if (UI.yv === 'detail') { const t = (UI.tryText || '').trim(), v = voice(UI.mv); if (t && v) price('tryv', {job: 'tts', chars: t.length, takes: 1, voice: v.id, lang: 'auto', engine: 'auto'}); return; }
      if (UI.yv !== 'make') { if (!yMine().length) { price('ywrecord', {job: 'clone', lang: UI.clone.lang}, yl); price('ywdesign', {job: 'design'}, yl); price('ywremix', {job: 'remix'}, yl); } return; }
      if (UI.way === 'record') price('clone', {job: 'clone', lang: UI.clone.lang}); if (UI.way === 'design') price('design', {job: 'design'}); if (UI.way === 'remix') price('remix', {job: 'remix'}); },
    dialogue() { $$('.hv-lt').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; });
      if (UI.dlg.podOpen) return; dlPrice();
      const one = $('[data-qbtn="dlone"]'); if (one) { const l = UI.dlg.lines[+one.dataset.n]; price('dlone', {job: 'dialogue', chars: (l?.text || '').length, lang: UI.dlg.lang || 'auto'}, r => r.credits != null ? 'Only this line is spoken' : ''); } },
    changer() { chgPrice(); },
    cleanup() { clPrice();
      $$('[data-drop="cl"]').forEach(el => { el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('over'); }); el.addEventListener('dragleave', () => el.classList.remove('over'));
        el.addEventListener('drop', e => { e.preventDefault(); el.classList.remove('over'); const f = e.dataTransfer?.files?.[0]; if (f) clFile(f, 0); }); }); },
    sfx() { price('fx', {job: 'sfx', seconds: UI.fx.seconds || 5, takes: UI.fx.takes}); },
    dub() { topTools(); dubPosters();
      if (!ARG) { if (UI.dubNew.file) price('dub', {job: UI.dubNew.mode === 'own' ? 'dub_own' : 'dub_matched', seconds: UI.dubNew.secs || 60, langs: UI.dubNew.langs.length || 1});
        $$('[data-drop="dub"]').forEach(el => { el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('over'); }); el.addEventListener('dragleave', () => el.classList.remove('over'));
          el.addEventListener('drop', e => { e.preventDefault(); el.classList.remove('over'); const f = e.dataTransfer?.files?.[0]; if (f) pageFile('dub', f); }); });
        return; }
      dubMediaSet(); $$('.hv-dedit textarea').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }); },
    reading() { const p = UI.proj, ch = p?.chapters?.[UI.chN]; readTools(); fillCovers();
      const todo = c => paraList(c).filter(x => x.state !== 'made').reduce((n, x) => n + x.text.length, 0);
      if (ch) price('readch', {job: 'chapter', chars: todo(ch) || (ch.text || '').length, lang: p.lang || 'en'}, r => r.credits != null ? (ch.audio ? 'Only the changed paragraphs are read' : 'Each paragraph in the voice of who says it') : '');
      if (p) price('readall', {job: 'chapter', chars: p.chapters.reduce((n, c, i) => n + (chState(p, i) === 'made' ? 0 : todo(c) || (c.text || '').length), 0), lang: p.lang || 'en'}); },
    studio() { readTools(); fillCovers();
      $$('[data-drop="imp"]').forEach(el => { el.addEventListener('dragover', e => { e.preventDefault(); el.classList.add('over'); });
        el.addEventListener('dragleave', () => el.classList.remove('over'));
        el.addEventListener('drop', e => { e.preventDefault(); el.classList.remove('over'); const f = e.dataTransfer?.files?.[0]; if (!f) return;
          UI.imp.open = true; UI.imp.src = 'file'; UI.imp.pv = null; pageFile('imp', f); }); }); },
  };
  const grow = t => { t.style.height = 'auto'; t.style.height = Math.min(180, t.scrollHeight) + 'px'; };
  function dictHits(text) { if (!S.rules) return 0; const lo = String(text || '').toLowerCase();
    return D.rules.filter(r => r.word && new RegExp(`(^|[^\\p{L}\\p{N}])${String(r.word).toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[^\\p{L}\\p{N}])`, 'u').test(lo)).length; }
  const countLine = () => { const n = dictHits(S.text); return `${num(S.text.length)} characters · tones work on every engine${n ? ` · ${plural(n, 'word')} from your dictionary will be read your way` : ''}`; };
  const panel = (label, body, cls = '') => `<section class="hv-panel${cls ? ' ' + cls : ''}" aria-label="${label}">${body}</section>`;
  const stage = (label, head, body) => `<section class="hv-stage" aria-label="${label}"><div class="hv-stageh">${head}</div><div class="hv-stageb">${body}</div></section>`;
  const dlgChars = () => UI.dlg.lines.reduce((n, l) => n + (l.text || '').length, 0);
  const dlgQuote = () => ({job: 'dialogue', chars: dlgChars(), lang: UI.dlg.lang || 'auto'});
  const dlPrice = () => price('dlg', dlgQuote(), r => r.credits != null ? `About ${secs(Math.round(dlTotal()))} of sound · nothing is spent until you press Make` : esc(scrub(r.line || '')));

  // ------------------------------------------------------------------ Speech (v0.999.133, design canvas claude.ai/artifact/B6TXccvssgFpNsR4ndVq3p) ---
  // the words in a writing area set in Literata, a coloured layer under it marks every [tone] and every word her dictionary
  // reads her way; the voice as a card; style, pace, takes; the rest under More settings; a Speak bar that stays in view
  // with the price; the takes beside it. Line by line: every line made on its own, only a changed line made again.
  const SP_STARTS = [['AD', 2, 'A short ad', 'Bright, ends with your offer and how to reach you.', '[excited] This week only at [YOUR SHOP]: [YOUR OFFER]. [warm] Come in today, or call [YOUR NUMBER].'],
    ['IN', 1, 'Phone greeting', 'Thanks for calling, then the keys to press.', '[warm] Thank you for calling [YOUR BUSINESS]. [pause] Press one for orders. Press two to talk to us.'],
    ['ST', 0, 'A short story', 'A calm voice, an easy pace, a soft ending.', '[slowly] Once upon a time, in a small house by the river, lived a girl called [NAME]. [whispers] Every night, she counted the stars.'],
    ['LS', 3, 'A lesson', 'Clear and patient, with small pauses.', '[warm] Today we learn [THE TOPIC]. [pause] First, [THE FIRST IDEA]. [pause] Now let us try it together.'],
    ['RL', 2, 'A reel voice-over', 'Quick and lively, for a short video.', '[excited] Three things you did not know about [THE TOPIC]. [pause] Number one: [THE FIRST THING].'],
    ['AN', 1, 'An announcement', 'Serious and clear, for a shop, a school or an event.', 'Attention, please. [pause] [THE NEWS]. [pause] Thank you.']];
  const TONE_NOTE = {warm: 'Friendly and kind', whispers: 'Very soft and close', laughs: 'A small laugh', excited: 'More energy',
    pause: 'A short quiet', slowly: 'Slower, with care'};
  const TAG_RE = /\[[^\]\n]{1,40}\]/g;
  const words = t => String(t || '').replace(TAG_RE, ' ').split(/\s+/).filter(Boolean).length;
  const estSecs = t => Math.max(1, Math.round(words(t) / 2.6 / (+S.speed || 1) + (String(t || '').match(/\[pause[^\]]*\]/gi) || []).length * 0.6));
  const timeLine = () => S.text.trim() ? `${plural(words(S.text), 'word')} · about ${secs(estSecs(S.text))}` : 'Nothing written yet';
  const reEsc = w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // the layer under the words: the same text, the same wrap, with the tones and her dictionary words marked
  function hiHTML(t) {
    const ws = S.rules ? D.rules.map(r => String(r.word || '')).filter(Boolean) : [];
    const re = ws.length ? new RegExp(`(^|[^\\p{L}\\p{N}])(${ws.map(w => reEsc(esc(w))).join('|')})(?=$|[^\\p{L}\\p{N}])`, 'giu') : null;
    return String(t || '').split(/(\[[^\]\n]{1,40}\])/).map((part, k) => k % 2 ? `<mark class="hv-tg">${esc(part)}</mark>`
      : re ? esc(part).replace(re, (m, a, w) => `${a}<span class="hv-dw">${w}</span>`) : esc(part)).join('') + '\n';
  }
  function edSync() { const ta = $('#hvText'), hi = $('#hvHi'); if (!ta) return; ta.style.height = 'auto'; ta.style.height = Math.max(150, ta.scrollHeight) + 'px'; if (hi) hi.innerHTML = hiHTML(ta.value); }
  const vfeel = v => !v ? 'Pick a voice' : [v.tone, (v.langs || []).length ? `speaks ${(v.langs || []).slice(0, 2).map(c => lang(c)?.name || c).join(', ')}${v.langs.length > 2 ? ` and ${num(v.langs.length - 2)} more` : ''}` : (v.any ? 'speaks any language' : ''), v.tier === 'premium' ? 'Premium' : ''].filter(Boolean).join(' · ');
  const spSum = () => [vname(S.voice), styleName(S.style), `${(+S.speed).toFixed(2)}x`, plural(S.takes, 'take')].join(' · ');
  const moreSum = () => [`Language: ${short(S.lang)}`, fmtOf(S.format).name, engName(S.engine), S.rules ? 'Dictionary on' : 'Dictionary off'].join(' · ');
  const canStream = () => !!D.status?.connected?.stream && voice(S.voice)?.engine === 'eleven';
  function speechView() {
    return `<div class="hv-split hv-tool hv-spk"><section class="hv-panel hv-spe" aria-label="Script">
        <div class="hv-sptab"><div class="hv-seg" role="tablist" aria-label="How to write">${[['whole', 'Whole script'], ['lines', 'Line by line']].map(([k, l]) =>
          `<button type="button" role="tab" aria-selected="${SP.mode === k}" aria-checked="${SP.mode === k}" data-a="spmode" data-val="${k}">${l}</button>`).join('')}</div>
          <span class="hv-grow"></span><button type="button" class="hv-btn" data-a="spimport">${ic('file', 14)}Import text</button></div>
        ${SP.mode === 'lines' ? spLinesBody() : spWholeBody()}</section>
      ${SP.mode === 'lines' ? spLineSide() : spStage()}</div>`;
  }
  function spWholeBody() {
    const lim = D.limits?.characters || 100000, w = paid(speakWhy(S.lang, S.engine)), g = gate(w), v = voice(S.voice), blank = !S.text.trim() && !S.out.length;
    return `<form class="hv-form hv-spform" data-f="speech">
      ${blank ? `<div class="hv-sphero"><h2 class="hv-sph">Write it once. Hear it said well.</h2><p class="hv-mut">Type or paste your words. Hoola reads them in the voice and style you pick, in any of ${num(D.langs.length || 140)} languages. You hear every take before anything is kept.</p></div>` : ''}
      <article class="hv-card hv-script"><div class="hv-sptools" role="toolbar" aria-label="Writing tools">
          <button type="button" class="hv-tl pri" data-a="tonemenu" aria-haspopup="menu">${ic('tone', 14)}Add a tone</button>
          <button type="button" class="hv-tl" data-a="tag" data-val="pause">${ic('pause2', 14)}Pause</button>
          <button type="button" class="hv-tl" data-a="sayas">${ic('say', 14)}Say it like</button>
          <button type="button" class="hv-tl" data-a="spimprove">${ic('wand', 14)}Improve the words</button>
          <span class="hv-grow"></span><span class="hv-mut hv-sm hv-num" id="hvTime">${esc(timeLine())}</span></div>
        <div class="hv-edw"><div class="hv-edhi" id="hvHi" aria-hidden="true">${hiHTML(S.text)}</div>
          <label class="hv-sr" for="hvText">Your words</label>
          <textarea id="hvText" class="hv-edta" rows="4" maxlength="${lim}" data-m="S.text" spellcheck="true" placeholder="Type or paste your words. A tone in square brackets, like [warm] or [pause], changes how it is read and is never read out.">${esc(S.text)}</textarea></div>
        <p class="hv-spfoot hv-sm hv-mut hv-num"><span class="hv-key" aria-hidden="true"></span><span id="hvCount">${esc(countLine())}</span></p></article>
      ${blank ? `<div class="hv-spstarts"><span class="hv-lab">Start from one of these</span><div class="hv-sgrid3">${SP_STARTS.map(([m, n, h, l, t]) =>
        `<button type="button" class="hv-start" data-a="spstart" data-val="${esc(t)}"><span class="hv-stt t${n}" aria-hidden="true">${m}</span><span class="hv-stw"><b>${esc(h)}</b><span>${esc(l)}</span></span></button>`).join('')}</div></div>` : ''}
      <div class="hv-dlv"><div class="hv-card hv-vcard"><span class="hv-av xl" aria-hidden="true">${initial(v?.name)}</span><div class="hv-ct"><b>${esc(v?.name || 'No voice ready')}</b><small>${esc(vfeel(v))}</small></div>
          ${v ? `<button type="button" class="hv-play o" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}">${ic('play', 12)}</button>` : ''}
          <button type="button" class="hv-btn" data-a="vpopen" aria-haspopup="dialog">Change</button></div>
        <div class="hv-card hv-pace"><label class="hv-labr" for="hvSpeed"><span>Pace</span><span class="hv-num hv-mut" data-show="S.speed">${(+S.speed).toFixed(2)}x</span></label>
          <input id="hvSpeed" type="range" min="0.7" max="1.3" step="0.05" value="${S.speed}" data-m="S.speed" data-t="num"><span class="hv-ends hv-sm hv-mut"><span>Slower</span><span>Faster</span></span></div></div>
      ${Object.keys(D.styles || {}).length ? `<div class="hv-fld"><span class="hv-lab">Style</span>${chipSeg('S.style', Object.entries(D.styles), S.style, 'Style')}</div>` : ''}
      <div class="hv-sprow"><span class="hv-lab">Takes</span>${seg('S.takes', [[1, '1'], [2, '2'], [4, '4']], S.takes, null, 'Takes')}
        <button type="button" class="hv-btn hv-morebtn" data-a="spmore" aria-expanded="${SP.more}" aria-controls="hvSpMore">${ic('sliders', 14)}More settings${ic(SP.more ? 'up' : 'down', 12)}</button>
        ${SP.more ? '' : `<span class="hv-mut hv-sm">${esc(moreSum())}</span>`}</div>
      <div class="hv-spmore" id="hvSpMore"${SP.more ? '' : ' hidden'}><div class="hv-picks">${dd('Language', 'picklang', 'S.lang', langLabel(S.lang), ' data-auto="1"')}
          ${dd('Format', 'pickfmt', 'S.format', fmtOf(S.format).name)}${dd('Engine', 'pickengine', 'S.engine', engName(S.engine))}</div>
        ${check('S.rules', `Read my dictionary words my way (${plural(D.rules.length, 'word')})`, S.rules)}</div>
      <span class="hv-grow"></span>
      <div class="hv-spbar"><span class="hv-av" aria-hidden="true">${initial(v?.name)}</span><div class="hv-ct"><b id="hvSpSum">${esc(spSum())}</b><span class="hv-sm hv-mut" data-qline="speech">The price shows here before anything is made.</span></div>
        ${canStream() ? `<button type="button" class="hv-btn" data-a="stream"${g.a}>${ic('play', 13)}Play while it is made</button>` : ''}
        <button class="hv-cta s" data-qbtn="speech" data-label="Speak it" data-icon="speech" title="Speak it (Ctrl + Enter)"${g.a}>${ic('speech')}<span>Speak it</span></button></div>${g.l}</form>`;
  }
  // a take of the Speech page: play, its letter, waveform, length, Keep, download, more
  function spTake(it, i) {
    const L = it.take || String.fromCharCode(65 + i), on = kept(it.id);
    return `<div class="hv-take hv-takecard hv-sptake${on ? ' kept' : ''}">${playBtn(it.id, `Play take ${L}`, 13, ' l')}<span class="hv-tn"><b>${esc(L)}</b></span>${wave(it.id, 44)}
      <span class="hv-len hv-num">${it.seconds ? secs(it.seconds) : ''}</span>
      <button type="button" class="hv-keep${on ? ' on' : ''}" data-a="keep" data-id="${esc(it.id)}" aria-pressed="${on}" aria-label="${on ? `Take ${esc(L)} is kept` : `Keep take ${esc(L)}`}">${on ? ic('check', 13) + 'Kept' : 'Keep'}</button>
      <button type="button" class="hv-ib s" data-a="dlmenu" data-id="${esc(it.id)}" aria-haspopup="menu" aria-label="Download take ${esc(L)}">${ic('dl', 15)}</button>
      <button type="button" class="hv-ib s" data-a="takemenu" data-id="${esc(it.id)}" aria-label="More for take ${esc(L)}">${ic('more')}</button></div>`;
  }
  function spStage() {
    const f = S.out[0], mine = new Set(S.out.map(x => x.id));
    const old = (D.history || []).filter(h => h.kind === 'tts' && !mine.has(h.id) && !h.joined).slice(0, 5);
    const credits = S.out.reduce((n, x) => n + (+x.credits || 0), 0);
    const set = f ? `<article class="hv-card hv-setc" aria-label="${esc(f.title || 'Your sound')}"><div class="hv-seth"><span class="hv-av l" aria-hidden="true">${initial(f.voice_name)}</span>
        <div class="hv-ct"><b>${esc(f.title || 'Your sound')}</b><small>${esc([f.made ? ago(f.made) : 'Just now', f.voice_name, f.style ? styleName(f.style) : '', f.lang ? short(f.lang) : '', plural(S.out.length, 'take')].filter(Boolean).join(' · '))}</small></div>
        ${credits ? `<span class="hv-mut hv-sm hv-num">${cr(credits)}</span>` : ''}</div>
      <div class="hv-takesl" id="hvTakes">${S.out.map(spTake).join('')}</div>
      <div class="hv-chips"><button type="button" class="hv-chip" data-a="sptweak" data-val="slower">Slower</button>
        ${'warm' in (D.styles || {}) && S.style !== 'warm' ? '<button type="button" class="hv-chip" data-a="sptweak" data-val="warm">Warmer</button>' : ''}
        <button type="button" class="hv-chip" data-a="vpopen" aria-haspopup="dialog">Another voice</button>
        ${canDub(f) ? `<button type="button" class="hv-chip pri" data-a="dubit" data-id="${esc(f.id)}" aria-haspopup="menu">${ic('globe', 13)}Dub it</button>` : ''}</div>
      <span class="hv-mut hv-sm">Made by AI · marked in the file</span></article>`
      : `<div class="hv-card hv-spnone"><span class="hv-ghost" aria-hidden="true">${wave('ghost', 22, 'thin')}</span><b>Your takes land here</b>
        <p class="hv-mut">Each take is a version to choose from. Keep the ones you like.</p>
        <ol class="hv-steps"><li><span>1</span>Write or paste your words</li><li><span>2</span>Pick a voice and a style</li><li><span>3</span>See the price, then press Speak it</li></ol></div>`;
    const prev = old.length ? `<span class="hv-lab hv-sm">Earlier</span>${old.map(h => `<div class="hv-card hv-spold">${playBtn(h.id, `Play ${h.title || 'this sound'}`, 12, ' o s')}
        <div class="hv-ct"><b>${esc(h.title || 'Speech')}</b><small>${esc([ago(h.made), h.voice_name, h.style ? styleName(h.style) : ''].filter(Boolean).join(' · '))}</small></div>
        <span class="hv-len hv-num">${h.seconds ? secs(h.seconds) : ''}</span>${h.text ? `<button type="button" class="hv-btn s" data-a="spreuse" data-id="${esc(h.id)}">Use these words</button>` : ''}</div>`).join('')}` : '';
    return stage('Takes', `<b>Takes</b>${S.out.length ? `<span class="hv-cnt on">${num(S.out.length)}</span>` : ''}<span class="hv-grow"></span>
        ${S.out.length > 1 ? `<button type="button" class="hv-btn s" data-a="compare" data-val="${esc(S.out.map(x => x.id).join(','))}" aria-label="Play the takes one after another">Compare</button>` : ''}`, set + prev);
  }

  // ---- line by line: each line its own tone and voice, made on its own; a line she changes is the only one made again ----
  const toneOf = line => { const m = /^\s*\[([^\]\n]{1,40})\]\s*/.exec(line || ''); return m ? {tone: m[1].trim(), rest: line.slice(m[0].length)} : {tone: '', rest: line || ''}; };
  const spLines = () => { const l = S.text.split('\n'); return l.length ? l : ['']; };
  const lineKey = (i, line) => [SP.lv[i] || S.voice, S.style, (+S.speed).toFixed(2), S.lang || 'auto', line.trim()].join('|');
  const histRow = id => (D.history || []).find(h => h.id === id);
  function lineState(i, line) {
    if (!line.trim()) return {st: 'empty', label: 'Empty', row: null};
    const row = histRow(SP.made[lineKey(i, line)]);
    if (row) return {st: 'made', label: 'Made', row};
    return SP.at[i] && histRow(SP.at[i]) ? {st: 'changed', label: 'Changed', row: null} : {st: 'new', label: 'Not made yet', row: null};
  }
  const lineSecs = (i, line) => { const s = lineState(i, line); return s.row?.seconds ? +s.row.seconds : estSecs(line); };
  function lnRow(line, i) {
    const {tone, rest} = toneOf(line), s = lineState(i, line), on = i === SP.sel, lv = SP.lv[i];
    return `<li class="hv-ln${on ? ' on' : ''}" data-ln="${i}"><button type="button" class="hv-lnn" data-a="lnsel" data-val="${i}" aria-label="Line ${i + 1}" aria-pressed="${on}">${i + 1}</button>
      <div class="hv-lnb"><span class="hv-lnm"><span class="hv-tgp">${esc(tone || 'natural')}</span><span class="hv-mut hv-sm">${esc(vname(lv || S.voice))}${lv ? ' · this line only' : ''}</span></span>
        <textarea class="hv-lnt" rows="1" data-line="${i}" aria-label="Line ${i + 1}" placeholder="Write this line">${esc(rest)}</textarea></div>
      <div class="hv-lnr"><span class="hv-lst ${s.st}" data-lst="${i}">${s.label}</span><span class="hv-len hv-num" data-llen="${i}">${line.trim() ? secs(lineSecs(i, line)) : ''}</span>
        ${s.row ? playBtn(s.row.id, `Play line ${i + 1}`, 12, ' o s') : line.trim() ? `<button type="button" class="hv-btn s" data-a="lnmake" data-val="${i}">Make</button>` : ''}</div></li>`;
  }
  function lnTodo() { return spLines().map((l, i) => [l, i]).filter(([l, i]) => l.trim() && lineState(i, l).st !== 'made'); }
  function lnBar() {
    const ls = spLines(), todo = lnTodo(), done = ls.filter((l, i) => lineState(i, l).st === 'made').length, have = ls.filter(l => l.trim()).length;
    const w = paid(speakWhy(S.lang, S.engine)), g = gate(todo.length ? w : '');
    const total = ls.reduce((n, l, i) => n + (l.trim() ? lineSecs(i, l) : 0), 0);
    const segs = ls.map((l, i) => l.trim() ? `<span class="hv-tseg ${lineState(i, l).st}" style="flex-grow:${Math.max(1, Math.round(lineSecs(i, l)))}">${i + 1}</span>` : '').join('');
    return `<div class="hv-lnbar" id="hvLnBar"><button type="button" class="hv-play l" data-a="lnplayall" aria-label="Play every made line, in order" aria-describedby="hvLnSum"${done ? '' : ' disabled'}>${ic('play', 13)}</button>
      <div class="hv-tl1"><div class="hv-tsegs" aria-label="The lines one after another">${segs}</div>
        <span class="hv-sm hv-mut hv-num" id="hvLnSum">The whole script about ${secs(total)} · ${num(done)} of ${plural(have, 'line')} made${todo.length ? ` · ${plural(todo.length, 'line')} to make` : ''}</span></div>
      ${todo.length ? `<button type="button" class="hv-cta s" data-a="lnmakeall" data-qbtn="lines" data-label="Make ${plural(todo.length, 'line')}"${g.a}><span>Make ${plural(todo.length, 'line')}</span></button>` : ''}
      <button type="button" class="hv-btn" data-a="lnjoin"${done >= 2 && !todo.length ? '' : ' disabled aria-describedby="hvJoinWhy"'}>${ic('dl', 14)}Download as one file</button></div>
      ${g.l}${done >= 2 && !todo.length ? '' : `<p class="hv-why" id="hvJoinWhy">${have < 2 ? 'Write at least two lines to join them into one file.' : 'Make every line first, then they join into one file.'}</p>`}`;
  }
  function spLinesBody() {
    return `<div class="hv-lnwrap"><p class="hv-mut hv-sm">Each line is made on its own. Change one line and only that line is made again. Lines are made as WAV and joined in your format.</p>
      <ol class="hv-lns" id="hvLns">${spLines().map(lnRow).join('')}</ol>
      <button type="button" class="hv-btn hv-lnadd" data-a="lnadd">${ic('plus', 14)}Add a line</button><span class="hv-grow"></span>${lnBar()}</div>`;
  }
  function spLineSide() {
    const ls = spLines(), i = Math.min(SP.sel, ls.length - 1), line = ls[i] || '', {tone, rest} = toneOf(line), s = lineState(i, line), vid = SP.lv[i] || S.voice, v = voice(vid);
    const hits = S.rules ? D.rules.filter(r => r.word && new RegExp(`(^|[^\\p{L}\\p{N}])${reEsc(String(r.word).toLowerCase())}($|[^\\p{L}\\p{N}])`, 'u').test(rest.toLowerCase())) : [];
    const earlier = (D.history || []).filter(h => h.kind === 'tts' && !h.joined && rest.trim() && GV(h.text) === GV(line)).slice(0, 4);
    return `<section class="hv-stage hv-lnside" aria-label="This line"><div class="hv-stageh"><b>Line ${i + 1}</b><span class="hv-mut hv-sm">${esc(s.label)}</span></div><div class="hv-stageb">
      <div class="hv-fld"><span class="hv-lab">Voice for this line</span><button type="button" class="hv-vrow" data-a="vpopen" data-k="line" aria-haspopup="dialog">
        <span class="hv-av" aria-hidden="true">${initial(v?.name)}</span><span class="hv-growf">${esc(v?.name || 'Pick a voice')}</span><span class="hv-mut hv-sm">Change</span></button>
        ${SP.lv[i] ? '<button type="button" class="hv-link hv-sm" data-a="lnvoice0">Use the script’s voice</button>' : ''}</div>
      <div class="hv-fld"><span class="hv-lab">Tone</span><div class="hv-chips" role="radiogroup" aria-label="Tone of line ${i + 1}">${['natural', ...TONES.filter(t => t !== 'pause')].map(t =>
        `<button type="button" class="hv-chip" role="radio" aria-checked="${(tone || 'natural').toLowerCase() === t}" data-a="lntone" data-val="${t}">${t[0].toUpperCase() + t.slice(1)}</button>`).join('')}</div></div>
      <div class="hv-fld"><span class="hv-lab">Say it like</span><div class="hv-card hv-dictl">${hits.length ? hits.map(r => `<div class="hv-dr"><b>${esc(r.word)}</b>${ic('back', 12)}<span>${esc(r.say || r.ipa || '')}</span></div>`).join('')
        : '<p class="hv-mut hv-sm">No word of this line is in your dictionary.</p>'}<button type="button" class="hv-link" data-a="sayas" data-k="line">Add a word</button></div></div>
      ${earlier.length ? `<div class="hv-fld"><span class="hv-lab">Earlier takes of this line</span>${earlier.map(h => `<div class="hv-dr">${playBtn(h.id, 'Play this take', 11, ' o s')}<span class="hv-growf hv-sm">${esc([ago(h.made), h.voice_name, h.seconds ? secs(h.seconds) : ''].filter(Boolean).join(' · '))}</span>
        ${SP.made[lineKey(i, line)] === h.id ? '<span class="hv-inuse hv-sm">In use</span>' : `<button type="button" class="hv-btn s" data-a="lnuse" data-id="${esc(h.id)}">Use this one</button>`}</div>`).join('')}</div>` : ''}
      <span class="hv-grow"></span>${ls.length > 1 ? `<button type="button" class="hv-btn" data-a="lnremove">${ic('trash', 14)}Remove this line</button>` : ''}</div></section>`;
  }
  const GV = t => String(t || '').replace(TAG_RE, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  function lnSave() { store.set('hv.lines', Object.fromEntries(Object.entries(SP.made).slice(-400))); store.set('hv.lineat', SP.at); }
  function lnRefresh() {                        // after typing in a line: its state, the bar, the side - never the line she is typing in
    spLines().forEach((l, i) => { const s = lineState(i, l), b = $(`[data-lst="${i}"]`), n = $(`[data-llen="${i}"]`);
      if (b) { b.className = `hv-lst ${s.st}`; b.textContent = s.label; } if (n) n.textContent = l.trim() ? secs(lineSecs(i, l)) : ''; });
    const bar = $('#hvLnBar'); if (bar) { bar.parentElement.querySelectorAll(':scope > .hv-why').forEach(x => x.remove()); bar.outerHTML = lnBar(); }
    lnPrice();
  }
  function lnPrice() { const todo = lnTodo(); if (todo.length) price('lines', {job: 'tts', chars: todo.reduce((n, [l]) => n + l.length, 0), takes: 1, voice: S.voice, lang: S.lang || 'auto', engine: S.engine}); }
  function lnSel(i) { SP.sel = i; $$('.hv-ln').forEach(n => { const on = +n.dataset.ln === i; n.classList.toggle('on', on); n.querySelector('.hv-lnn')?.setAttribute('aria-pressed', String(on)); });
    const sd = $('.hv-lnside'); if (sd) sd.outerHTML = spLineSide(); syncPlay(); }
  function lnSet(i, text) { const ls = spLines(); ls[i] = text; S.text = ls.join('\n'); }
  async function lnMake(i) {
    const line = spLines()[i] || ''; if (!line.trim()) return;
    const r = await api('POST', `${A}/tts`, {...speechBody(), text: line, voice: SP.lv[i] || S.voice, takes: 1, format: 'wav'});
    const it = (r.items || [r])[0]; if (!it?.id) throw new Error('The line came back empty. Try again.');
    SP.made[lineKey(i, line)] = it.id; SP.at[i] = it.id; lnSave(); return it;
  }
  // the voice picker: search, a few filters, hear each voice's sample (free), Use
  function vpOpen(k) {
    SP.vp = {k: k || 'script', q: '', f: 'All', back: document.activeElement};
    const host = document.createElement('div'); host.id = 'hvVp'; host.className = 'hv-vphost';
    host.innerHTML = `<div class="hv-vpscrim" data-a="vpclose" aria-hidden="true"></div><div class="hv-vp" role="dialog" aria-modal="true" aria-labelledby="hvVpH">
      <div class="hv-vph"><h2 class="hv-t" id="hvVpH">${SP.vp.k === 'line' ? `Pick a voice for line ${SP.sel + 1}` : 'Pick a voice'}</h2><span class="hv-grow"></span><button type="button" class="hv-ib" data-a="vpclose" aria-label="Close">${ic('x', 16)}</button></div>
      <label class="hv-search hv-vpq">${ic('search', 15)}<span class="hv-sr">Search voices</span><input id="hvVpQ" type="search" placeholder="Search by name, language or feel" autocomplete="off"></label>
      <div class="hv-chips" id="hvVpF" role="radiogroup" aria-label="Show"></div>
      <p class="hv-mut hv-sm">Hearing a voice’s sample is free.</p>
      <div class="hv-vpl" id="hvVpL"></div>
      ${EMBED ? '' : `<div class="hv-vpf"><button type="button" class="hv-btn" data-a="vpgo" data-val="voices">Open the whole library</button><button type="button" class="hv-btn" data-a="vpgo" data-val="design">${ic('plus', 14)}Describe a new voice</button><button type="button" class="hv-btn" data-a="vpgo" data-val="record">Use my own voice</button></div>`}</div>`;
    ROOT.appendChild(host); vpPaint(); $('#hvVpQ')?.focus();
  }
  function vpPaint() {
    const vp = SP.vp; if (!vp) return; const cur = vp.k === 'line' ? (SP.lv[SP.sel] || S.voice) : S.voice;
    const lc = S.lang !== 'auto' ? S.lang : '', rec = vRecent(), favs = D.favs || [];
    const fl = ['All', ...(rec.length ? ['Recent'] : []), ...(favs.length ? ['Favourites'] : []), ...(lc ? [`For ${short(lc)}`] : []), ...(D.voices.some(v => v.kind !== 'hoola') ? ['Your voices'] : [])];
    if (!fl.includes(vp.f)) vp.f = 'All';
    const f = $('#hvVpF'), had = document.activeElement?.closest?.('#hvVpF [data-val]')?.dataset.val;
    if (f) { f.innerHTML = fl.map(x => `<button type="button" class="hv-chip" role="radio" aria-checked="${vp.f === x}" data-a="vpf" data-val="${esc(x)}">${esc(x)}</button>`).join('');
      if (had != null) [...f.querySelectorAll('[data-val]')].find(x => x.dataset.val === had)?.focus(); }
    const lo = vp.q.trim().toLowerCase();
    const pool = vp.f === 'Recent' ? rec.map(voice) : vp.f === 'Favourites' ? favs.map(voice).filter(Boolean) : vp.f === 'Your voices' ? D.voices.filter(v => v.kind !== 'hoola')
      : vp.f.startsWith('For ') ? D.voices.filter(v => vSpeaks(v, lc)) : D.voices;
    const list = pool.filter(v => v && (!lo || [v.name, v.tone, v.accent, v.use, ...(v.langs || []).map(c => [c, lang(c)?.name, lang(c)?.native].join(' '))].join(' ').toLowerCase().includes(lo)));
    const l = $('#hvVpL'); if (!l) return;
    l.innerHTML = list.length ? list.map((v, n) => { const on = v.id === cur;
      return `<div class="hv-vpr${on ? ' on' : ''}"><button type="button" class="hv-play o" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>
        ${vprint(v.id)}<div class="hv-ct"><b>${esc(v.name)}${v.kind !== 'hoola' ? ' <span class="hv-badge">Your voice</span>' : ''}</b><small>${esc(vfeel(v))}</small></div>
        <button type="button" class="hv-ib hv-star${favs.includes(v.id) ? ' on' : ''}" data-a="vfav" data-id="${esc(v.id)}" aria-pressed="${favs.includes(v.id)}" aria-label="Favourite ${esc(v.name)}">${ic('star', 15)}</button>
        ${v.ready ? `<button type="button" class="hv-btn${on ? ' on' : ''}" data-a="vpuse" data-id="${esc(v.id)}" aria-pressed="${on}">${on ? 'Chosen' : 'Use'}</button>`
          : `<span class="hv-mut hv-sm">${esc(scrub(v.engine && !ready(v.engine) ? whyNot(v.engine) : 'Not ready yet'))}</span>`}</div>`; }).join('')
      : '<p class="hv-mut">No voice matches. Try other words.</p>';
  }
  function vpClose() { const h = $('#hvVp'); const back = SP.vp?.back; SP.vp = null; h?.remove(); if (back?.isConnected) back.focus(); }
  // ---- v0.999.142 DIALOGUE, PREMIUM (design canvas claude.ai/artifact/A3gj67mEkASbVMm2k9PcX4): the talk as a conversation (who says
  // each line, its tone, a pause after it, a line that cuts in), the cast as cards, the takes with a lane per voice, one line made
  // again on its own, a script written from a document that names its pages and checks its figures ----
  const DLG_STARTS = [
    ['A podcast chat', 'A host and a guest talk about [YOUR TOPIC], easy and friendly.', 2, [[0, '[cheerful] Welcome back to the show. Today I am talking with [YOUR GUEST] about [YOUR TOPIC].'], [1, '[warm] Thanks for having me. I have been looking forward to this.'], [0, 'So, how did it all start?']]],
    ['A customer call', 'A shop answers a caller asking about [YOUR PRODUCT].', 1, [[0, '[warm] Hello, [YOUR SHOP], how can I help?'], [1, 'Hi, do you have [YOUR PRODUCT] in stock?'], [0, 'Yes, we do. It is [YOUR PRICE], and we can deliver today.']]],
    ['Two friends, an ad', 'One friend tells the other about [YOUR OFFER].', 2, [[0, '[excited] Have you heard about [YOUR OFFER]?'], [1, '[surprised] No, tell me!'], [0, 'Only at [YOUR SHOP], until [THE DATE].']]],
    ['A lesson, asked and answered', 'A student asks, a teacher explains [YOUR SUBJECT] step by step.', 3, [[1, 'What exactly is [YOUR SUBJECT]?'], [0, '[warm] Good question. [pause] Think of it like this: [THE FIRST IDEA].'], [1, 'Oh, that makes sense.']]],
    ['A radio skit', 'A short, funny scene with a twist at the end.', 1, [[0, '[whispers] Did you hear that noise?'], [1, 'It is just the cat.'], [0, '[surprised] We do not have a cat.']]],
    ['An interview', 'Clear questions and full answers, for [YOUR GUEST].', 0, [[0, 'Thank you for joining us, [YOUR GUEST]. What do you do?'], [1, '[warm] I run [YOUR BUSINESS] in [YOUR CITY].'], [0, 'And what is the hardest part of it?']]]];
  const PAUSES = [[0, 'No pause'], [0.5, 'Half a second'], [1, '1 second'], [2, '2 seconds'], [3, '3 seconds']];
  const TALK_KINDS = [['podcast', 'Podcast chat'], ['interview', 'Interview'], ['explainer', 'Explainer'], ['debate', 'Debate']];
  const pauseName = p => (PAUSES.find(x => x[0] === +p) || [0, `${p} seconds`])[1];
  const dlNames = () => UI.dlg.cast.map(c => c.name);
  const dlT = name => Math.max(0, dlNames().indexOf(name)) % 4;
  const dlFilled = () => UI.dlg.lines.filter(l => (l.text || '').trim());
  const dlSecs = t => (t || '').trim() ? Math.max(1, Math.round(words(t) / 2.6 + (String(t).match(/\[pause[^\]]*\]/gi) || []).length * 0.6)) : 0;
  const dlTotal = () => UI.dlg.lines.reduce((n, l) => n + ((l.text || '').trim() ? dlSecs(l.text) + (+l.pause || 0) + 0.3 : 0), 0);
  const dlSum = () => { const ls = dlFilled(), who = new Set(ls.map(l => l.speaker));
    return ls.length ? `${plural(ls.length, 'line')} · ${plural(who.size, 'speaker')} · about ${secs(Math.round(dlTotal()))}` : 'Nothing written yet'; };
  const dlBarSum = () => [UI.dlg.mode === 'natural' ? 'Natural talk' : 'Line by line', UI.dlg.style ? styleName(UI.dlg.style) : 'Natural',
    UI.dlg.reactions ? 'Reactions on' : '', UI.dlg.music ? 'Soft music' : ''].filter(Boolean).join(' · ');
  const dlTakes = () => UI.dlg.out.length ? UI.dlg.out : (D.history || []).filter(h => h.kind === 'dialogue').slice(0, 1);
  const dlChip = (name, cls = '') => `<span class="hv-dwho t${dlT(name)}${cls}"><span class="hv-dwi" aria-hidden="true">${initial(name)}</span>${esc(name)}</span>`;
  // a line against the newest Line-by-line take: made as it is, changed (words or speaker), or new
  function dlState(i) {
    const t = dlTakes()[0], l = UI.dlg.lines[i]; if (!t || t.mode !== 'lines' || !t.segments || !(l.text || '').trim()) return {s: ''};
    const k = UI.dlg.lines.slice(0, i).filter(x => (x.text || '').trim()).length, seg = (t.segments || []).filter(x => !x.reaction)[k];
    if (!seg) return {s: 'new', t, k};
    const same = seg.text === l.text && seg.speaker === l.speaker, opts = (+seg.pause || 0) === (+l.pause || 0) && !!seg.cut === !!l.cut;
    return {s: same && opts ? 'made' : 'changed', t, k, one: !same && opts && (t.cast || {})[l.speaker] != null};
  }
  function dlLine(l, n) {
    const d = UI.dlg, on = d.sel === n, nx = d.lines[n + 1], st = dlState(n), s = dlSecs(l.text);
    const tools = on ? `<div class="hv-dltools" role="group" aria-label="Line ${n + 1}">
        <button type="button" class="hv-chip" data-a="dltone" aria-haspopup="menu">Tone</button>
        <button type="button" class="hv-chip" data-a="pickwho" data-n="${n}" aria-haspopup="menu">Said by ${esc(l.speaker)}</button>
        <button type="button" class="hv-chip" data-a="dlpause" aria-haspopup="menu">${+l.pause ? `Pause after: ${esc(pauseName(l.pause))}` : 'Pause after'}</button>
        ${n ? `<button type="button" class="hv-chip" data-a="dlcut" aria-pressed="${!!l.cut}">${l.cut ? 'Cuts in' : 'Cut in'}</button>` : ''}
        ${n ? `<button type="button" class="hv-chip" data-a="dlmove" data-val="-1">Move up</button>` : ''}${nx ? `<button type="button" class="hv-chip" data-a="dlmove" data-val="1">Move down</button>` : ''}
        ${d.lines.length > 1 ? `<button type="button" class="hv-chip" data-a="dlrm" data-n="${n}">Delete</button>` : ''}
        ${st.one ? `<button type="button" class="hv-chip dark" data-a="dlone" data-n="${n}" data-qbtn="dlone" data-label="Make only this line">Make only this line</button><span class="hv-sm hv-mut" data-qline="dlone"></span>` : ''}</div>` : '';
    const after = [+l.pause && nx ? `Pause · ${pauseName(l.pause)}` : '', nx?.cut ? `${esc(nx.speaker)} cuts in · they overlap a little` : ''].filter(Boolean);
    return `<li class="hv-dl${on ? ' on' : ''}" data-n="${n}"><div class="hv-dlrow">
        <button type="button" class="hv-dwho t${dlT(l.speaker)}" data-a="pickwho" data-n="${n}" aria-haspopup="menu" aria-label="Line ${n + 1}, said by ${esc(l.speaker)}. Change"><span class="hv-dwi" aria-hidden="true">${initial(l.speaker)}</span>${esc(l.speaker)}</button>
        <div class="hv-dlw"><div class="hv-dlhi" aria-hidden="true">${hiHTML(l.text)}</div><label class="hv-sr" for="hvLt${n}">Line ${n + 1}, ${esc(l.speaker)}</label><textarea id="hvLt${n}" class="hv-lt hv-dlt" rows="1" maxlength="1500" data-m="UI.dlg.lines.${n}.text" data-dl="${n}" spellcheck="true" placeholder="What ${esc(l.speaker)} says">${esc(l.text)}</textarea></div>
        <span class="hv-dlr">${st.s === 'made' ? '<span class="hv-lst made">Made</span>' : st.s === 'changed' ? '<span class="hv-lst changed">Changed</span>' : ''}<span class="hv-len hv-num hv-mut" id="hvDlLen${n}">${s ? secs(s) : ''}</span></span></div>
      ${tools}${after.length ? `<div class="hv-dlmark" aria-label="After line ${n + 1}">${after.map(a => `<span>${a}</span>`).join('')}</div>` : ''}</li>`;
  }
  function dlView() {
    const d = UI.dlg, n2 = d.cast.length, ls = dlFilled();
    if (d.podOpen) return dlDocView();
    const natWhy = d.mode === 'natural' && n2 > 2 && !ready('eleven') ? 'Natural talk with more than 2 speakers needs ElevenLabs, which is not connected on this server yet. Choose Line by line, or keep 2 speakers.' : '';
    const w = paid(speakWhy(d.lang, 'auto') || natWhy || (ls.length ? '' : 'Write at least one line first.')), g = gate(w);
    const blank = !ls.length, last = d.lines[d.lines.length - 1], next = d.cast.find(c => c.name !== last?.speaker)?.name || d.cast[0]?.name || 'Speaker';
    const count = name => d.lines.filter(l => l.speaker === name && (l.text || '').trim()).length;
    return `<div class="hv-split hv-tool hv-spk hv-dlk"><section class="hv-panel hv-spe hv-dle" aria-label="Script">
        <div class="hv-sptab"><b class="hv-t hv-dlh">${esc(d.title || 'A new talk')}</b><span class="hv-grow"></span>
          <button type="button" class="hv-btn" data-a="podopen">${ic('file', 14)}Write it from a document</button>
          <button type="button" class="hv-dd s" data-a="picklang" data-k="UI.dlg.lang" data-need="dialogue" data-auto="1" aria-haspopup="menu" aria-label="Language: ${esc(short(d.lang))}"><span>${esc(short(d.lang))}</span>${ic('down', 12)}</button></div>
        <form class="hv-form hv-spform hv-dlform" data-f="dialogue">
        ${blank ? `<div class="hv-sphero"><h2 class="hv-sph">Two voices. One real conversation.</h2><p class="hv-mut">Write who says what, or let Hoola write it from a document. The voices answer each other, laugh and pause like people do.</p></div>` : ''}
        <div class="hv-dcast" aria-label="Speakers">${d.cast.map((c, i) => `<div class="hv-card hv-dcc"><span class="hv-dav t${i % 4}" aria-hidden="true">${initial(c.name)}</span>
            <div class="hv-ct"><label class="hv-sr" for="hvCn${i}">Speaker ${i + 1} name</label><input id="hvCn${i}" class="hv-castn" maxlength="30" data-m="UI.dlg.cast.${i}.name" value="${esc(c.name)}">
              <small>Voice: ${esc(vname(c.voice))} · ${plural(count(c.name), 'line')}</small></div>
            ${c.voice ? `<button type="button" class="hv-play o s" data-a="hear" data-id="${esc(c.voice)}" aria-label="Hear ${esc(vname(c.voice))}, free">${ic('play', 11)}</button>` : ''}
            <button type="button" class="hv-btn s" data-a="pickcast" data-n="${i}" aria-haspopup="dialog" aria-label="Change the voice of ${esc(c.name)}">Change</button>
            ${n2 > 1 ? `<button type="button" class="hv-ib xs" data-a="castrm" data-n="${i}" aria-label="Remove ${esc(c.name)}">${ic('x', 12)}</button>` : ''}</div>`).join('')}
          ${n2 < 6 ? `<button type="button" class="hv-btn hv-dadd" data-a="castadd" title="Add a speaker (up to 6)">${ic('plus', 14)}Speaker</button>` : ''}</div>
        <article class="hv-card hv-script hv-dscript"><div class="hv-sptools" role="toolbar" aria-label="Tools for line ${d.sel + 1}">
            <button type="button" class="hv-tl pri" data-a="dltone" aria-haspopup="menu">${ic('tone', 14)}Add a tone</button>
            <button type="button" class="hv-tl" data-a="dlpause" aria-haspopup="menu">${ic('pause2', 14)}Pause after</button>
            <button type="button" class="hv-tl" data-a="dlcut" aria-pressed="${!!d.lines[d.sel]?.cut}">${ic('cutin', 14)}Cuts in</button>
            ${n2 === 2 ? `<button type="button" class="hv-tl" data-a="dlswap">${ic('swap', 14)}Swap the speakers</button>` : ''}
            <span class="hv-grow"></span><span class="hv-mut hv-sm hv-num" id="hvDlSum">${esc(dlSum())}</span></div>
          <ol class="hv-dls">${d.lines.map(dlLine).join('')}</ol>
          ${d.lines.length < (D.limits?.lines || 40) ? `<button type="button" class="hv-dladd" data-a="dladd">${dlChip(next)}<span>Next line… Enter in a line starts a new one</span></button>` : ''}
          <p class="hv-spfoot hv-sm hv-mut">A tone in square brackets, like [warm] or [laughs], changes how a line is said and is never read out. Ctrl + Enter makes the talk.</p></article>
        ${blank ? `<button type="button" class="hv-card hv-dldoc" data-a="podopen"><span class="hv-tile">${ic('file', 18)}</span><span class="hv-ct"><b>Write it from a document</b><small>A PDF, a web page or your notes become a 2 to 15 minute talk. You read and change every line first.</small></span>${ic('chev', 16)}</button>
          <div class="hv-spstarts"><span class="hv-lab">Or start from one of these</span><div class="hv-sgrid3">${DLG_STARTS.map(([h, l, t], i) =>
            `<button type="button" class="hv-start" data-a="dlstart" data-val="${i}"><span class="hv-dpair" aria-hidden="true"><i class="t0"></i><i class="t${t}"></i></span><span class="hv-stw"><b>${esc(h)}</b><span>${esc(l)}</span></span></button>`).join('')}</div></div>` : ''}
        <span class="hv-grow"></span>
        <div class="hv-spbar hv-dlbar"><span class="hv-dstack" aria-hidden="true">${d.cast.slice(0, 3).map((c, i) => `<span class="hv-dav s t${i % 4}">${initial(c.name)}</span>`).join('')}</span>
          <div class="hv-ct"><b id="hvDlBar">${esc(dlBarSum())}</b><span class="hv-sm hv-mut" data-qline="dlg">The price shows here before anything is made.</span></div>
          <button type="button" class="hv-cta s" data-a="dlgmake" data-qbtn="dlg" data-label="Make the talk" data-icon="dialog" title="Make the talk (Ctrl + Enter)"${g.a}>${ic('dialog')}<span>Make the talk</span></button></div>${g.l}</form></section>
      ${dlStage()}</div>`;
  }
  // the lanes of a take: one row of bars per voice, lit where that voice speaks (measured Line by line, shared out by length in a natural take)
  function dlLanes(t) {
    const segs = t.segments || [], total = t.seconds || Math.max(1, ...segs.map(x => +x.end || 0)), N = 48;
    const who = [...new Set(segs.map(x => x.speaker))];
    let h = [...String(t.id || 'x')].reduce((a, ch) => (a * 33 + ch.charCodeAt(0)) >>> 0, 7);
    return `<div class="hv-lanes" aria-hidden="true">${who.map(w => `<div class="hv-lane t${dlT(w)}"><span class="hv-dav xs t${dlT(w)}">${initial(w)}</span><span class="hv-lbars">${Array.from({length: N}, (_, i) => {
        const a = i * total / N, b = (i + 1) * total / N, lit = segs.some(x => x.speaker === w && +x.start < b && +x.end > a); h = (h * 1103515245 + 12345) >>> 0;
        return `<i class="${lit ? 'on' : ''}" style="height:${lit ? 5 + (h % 17) : 2}px"></i>`; }).join('')}</span></div>`).join('')}
      <span class="hv-head" data-head="${esc(t.id)}"></span></div>`;
  }
  function dlTakeCard(t, i) {
    const on = kept(t.id), L = t.take || String.fromCharCode(65 + i), lines = t.mode === 'lines' && (t.segments || []).length;
    const meta = [t.made ? ago(t.made) : 'Just now', t.mode === 'natural' ? 'natural talk' : t.mode === 'lines' ? 'line by line' : '', t.remade != null ? `line ${+t.remade + 1} made again` : '', t.music ? 'soft music' : ''].filter(Boolean).join(' · ');
    if (i) return `<div class="hv-card hv-spold">${playBtn(t.id, `Play take ${L}`, 12, ' o s')}<div class="hv-ct"><b>Take ${esc(L)}</b><small>${esc(meta)}</small></div>
        <span class="hv-len hv-num">${t.seconds ? secs(t.seconds) : ''}</span><button type="button" class="hv-keep${on ? ' on' : ''}" data-a="keep" data-id="${esc(t.id)}" aria-pressed="${on}" aria-label="${on ? `Take ${esc(L)} is kept` : `Keep take ${esc(L)}`}">${on ? ic('check', 13) + 'Kept' : 'Keep'}</button></div>`;
    return `<article class="hv-card hv-setc hv-dtake" aria-label="Take ${esc(L)}"><div class="hv-seth">${playBtn(t.id, `Play take ${L}`, 13, ' l')}
        <div class="hv-ct"><b>${t.title ? esc(t.title) + ' · ' : ''}Take ${esc(L)}</b><small>${esc(meta)}${t.seconds ? ' · ' + secs(t.seconds) : ''}</small></div>
        <button type="button" class="hv-keep${on ? ' on' : ''}" data-a="keep" data-id="${esc(t.id)}" aria-pressed="${on}" aria-label="${on ? `Take ${esc(L)} is kept` : `Keep take ${esc(L)}`}">${on ? ic('check', 13) + 'Kept' : 'Keep'}</button></div>
      ${(t.segments || []).length ? dlLanes(t) : wave(t.id, 44)}
      ${(t.segments || []).length ? `<p class="hv-dlnow" data-now="${esc(t.id)}"><span class="hv-mut">Press play to follow along${t.timing_est ? ' (the times of a natural take are shared out by line length)' : ''}.</span></p>` : ''}
      <div class="hv-chips"><button type="button" class="hv-chip" data-a="dlmenu" data-id="${esc(t.id)}" aria-haspopup="menu">${ic('dl', 13)}Download</button>
        ${lines ? `<button type="button" class="hv-chip" data-a="dlvoices" data-id="${esc(t.id)}">Each voice on its own track</button>` : ''}
        ${(t.segments || []).length ? `<button type="button" class="hv-chip" data-a="dlsubs" data-id="${esc(t.id)}" aria-haspopup="menu">Subtitles</button>` : ''}
        ${canDub(t) ? `<button type="button" class="hv-chip pri" data-a="dubit" data-id="${esc(t.id)}" aria-haspopup="menu">${ic('globe', 13)}Dub it</button>` : ''}</div>
      ${t.mode === 'natural' ? '<p class="hv-mut hv-sm">A natural take is one recording. Make it Line by line to change one line or get each voice on its own track.</p>' : ''}
      <span class="hv-mut hv-sm">Made by AI · marked in the file</span></article>`;
  }
  function dlStage() {
    const d = UI.dlg, ts = dlTakes();
    const how = `<div class="hv-dlhow"><b class="hv-t">How it sounds</b>
        <div class="hv-seg hv-dmode" role="radiogroup" aria-label="Way of making">${[['natural', 'Natural talk'], ['lines', 'Line by line']].map(([k, l]) =>
          `<button type="button" role="radio" aria-checked="${d.mode === k}" data-a="seg" data-m="UI.dlg.mode" data-val="${k}">${l}</button>`).join('')}</div>
        <p class="hv-sm">${d.mode === 'natural' ? 'Both voices are made together in one take, so they react, pause and overlap like people. A pause or a cut-in is written in as a hint.' : 'Each line is its own take, joined with the exact pauses and cut-ins. Change one line and only that line is made again.'}</p>
        ${Object.keys(D.styles || {}).length ? `<div class="hv-fld"><span class="hv-lab">How they talk</span>${chipSeg('UI.dlg.style', [['', 'Natural'], ...Object.entries(D.styles)], d.style, 'How they talk')}</div>` : ''}
        <fieldset class="hv-fs"><legend class="hv-lab">Extras</legend>${check('UI.dlg.reactions', 'Small reactions <span class="hv-mut hv-sm">· a short “Mm-hmm” from the one listening</span>', d.reactions)}
          ${check('UI.dlg.music', 'Soft music under it <span class="hv-mut hv-sm">· made on Hoola’s server, free</span>', d.music, gate(ready('server') ? '' : 'Soft music needs ffmpeg on the server, which is not installed.'))}</fieldset></div>`;
    const body = ts.length ? ts.map(dlTakeCard).join('')
      : `<div class="hv-card hv-spnone"><span class="hv-ghost hv-ghost2" aria-hidden="true">${wave('ghost-a', 22, 'thin')}${wave('ghost-b', 22, 'thin')}</span><b>Your talks land here</b>
        <p class="hv-mut">Each voice gets its own lane, so you can see who speaks when, and hear any part again.</p>
        <ol class="hv-steps"><li><span>1</span>Write the lines, or start from a document</li><li><span>2</span>Give each speaker a voice</li><li><span>3</span>See the price, then press Make the talk</li></ol></div>`;
    return `<section class="hv-stage hv-dlside" aria-label="How it sounds and takes"><div class="hv-stageb">${how}
        <div class="hv-stageh hv-dlth"><b>Takes</b>${d.out.length ? `<span class="hv-cnt on">${num(d.out.length)}</span>` : ''}<span class="hv-grow"></span>
          ${d.out.length > 1 ? `<button type="button" class="hv-btn s" data-a="compare" data-val="${esc(d.out.slice(0, 2).map(x => x.id).join(','))}" aria-label="Play the two newest takes one after another">Compare A and B</button>` : ''}</div>${body}</div></section>`;
  }
  // a script from a document: what to talk about on the left, the draft (with its pages and checked figures) on the right
  function dlDocView() {
    const d = UI.dlg, p = d.pod, r = p.draft, gp = gate(paid(!ready('gemini') && !ready('eleven') ? 'No engine that writes and speaks a talk is connected on this server yet.' : ''));
    const src = p.src === 'file' ? `<div class="hv-filerow"><button type="button" class="hv-btn" data-a="pickfile" data-k="pod" data-accept=".pdf,.doc,.docx,.txt,.epub,.md">${ic('upload', 14)}${p.file ? 'Change' : 'Choose a file'}</button><span class="hv-mut hv-sm">${p.file ? esc(p.file.name) + (p.file.up ? ' · uploading…' : p.file.file_id ? ' · ready' : '') : 'PDF, Word, text or EPUB'}</span></div>`
      : p.src === 'url' ? `<label class="hv-sr" for="hvPodU">Web address</label><input id="hvPodU" class="hv-in" type="url" data-m="UI.dlg.pod.url" value="${esc(p.url)}" placeholder="https://">`
      : `<label class="hv-sr" for="hvPodT">Your notes</label><textarea id="hvPodT" class="hv-in" rows="5" data-m="UI.dlg.pod.text" maxlength="60000">${esc(p.text)}</textarea>`;
    let part = '';
    const draft = r ? `<div class="hv-chips">${(r.lines || []).filter(x => x.part).map((x, i) => `<span class="hv-chip hv-static${i ? '' : ' pri'}">${i + 1} · ${esc(x.part)}</span>`).join('')}</div>
        <ol class="hv-dls hv-ddraft">${(r.lines || []).map(x => { const h = x.part && x.part !== part ? `<li class="hv-dpart">${esc(x.part)}</li>` : ''; if (x.part) part = x.part;
          return `${h}<li class="hv-dl"><div class="hv-dlrow">${dlChip(x.speaker)}<p class="hv-dtx">${esc(x.text)}</p><span class="hv-dlr">${x.from ? `<span class="hv-lst" title="Where this comes from">${esc(x.from)}</span>` : ''}
            ${x.unchecked ? `<span class="hv-lst changed">Check: ${esc(x.unchecked.join(', '))} is not in the document</span>` : ''}</span></div></li>`; }).join('')}</ol>
        ${r.must && !r.must_said ? `<p class="hv-why" role="status">The script does not say “${esc(r.must)}” yet. Add it to a line, or write it again.</p>` : ''}
        <p class="hv-sm">${r.unchecked ? `${plural(r.unchecked, 'line')} has a figure the document does not have. Change ${r.unchecked === 1 ? 'it' : 'them'} before you make the talk.` : 'Every figure written in digits is in the document.'}${r.paged ? ' Each fact points to the page it came from.' : ''}</p>
        <div class="hv-ctarow"><button type="button" class="hv-btn" data-a="podagain">Write it again</button><button type="button" class="hv-cta s" data-a="poduse"><span>Use this script</span></button></div>`
      : `<div class="hv-card hv-spnone"><b>The script shows here</b><p class="hv-mut">You read it and change any line. No sound is made until you press Make the talk.</p></div>`;
    return `<div class="hv-split hv-tool hv-dldoc2"><section class="hv-panel hv-dlsrc" aria-label="What to talk about"><div class="hv-rh"><button type="button" class="hv-btn s" data-a="podclose">${ic('back', 14)}Back to the talk</button></div>
        <form class="hv-form" data-f="podcast"><span class="hv-mut hv-sm hv-num">Step 1 of 2</span><h2 class="hv-sph s">What should they talk about?</h2>
          ${seg('UI.dlg.pod.src', [['file', 'A file'], ['url', 'A web page'], ['text', 'Your notes']], p.src, null, 'From')}${src}
          <div class="hv-fld"><span class="hv-lab">Kind of talk</span>${chipSeg('UI.dlg.pod.kind', TALK_KINDS, p.kind, 'Kind of talk')}</div>
          <div class="hv-fld"><span class="hv-lab">Length</span>${seg('UI.dlg.pod.minutes', [[2, '2 min'], [5, '5 min'], [10, '10 min'], [15, '15 min']], p.minutes, null, 'Length in minutes')}</div>
          <div class="hv-fld"><span class="hv-lab">Who talks</span><div class="hv-dcast">${d.cast.slice(0, 2).map(c => dlChip(c.name)).join('')}<button type="button" class="hv-link" data-a="castopen" aria-haspopup="dialog">Change</button></div></div>
          <label class="hv-fld"><span class="hv-lab">Anything to be sure they say <span class="hv-mut">· optional</span></span><input class="hv-in" maxlength="200" data-m="UI.dlg.pod.must" value="${esc(p.must)}" placeholder="The offer ends Sunday"></label>
          <span class="hv-grow"></span><button class="hv-cta"${gp.a}>${ic('dialog', 15)}<span>${r ? 'Write it again' : 'Write the script'}</span></button>${gp.l}
          <p class="hv-hint c">Only words are written now. No sound is made until you press Make the talk.</p></form></section>
      <section class="hv-panel hv-dldraft" aria-label="The draft script"><span class="hv-mut hv-sm hv-num">Step 2 of 2</span><h2 class="hv-sph s">Read it, change any line</h2>${draft}</section></div>`;
  }
  // the cast picker: one speaker at a time, voices that sound unlike the others first, Use for <speaker>
  function cpOpen(slot) {
    UI.dlg.cp = {slot: Math.max(0, Math.min(UI.dlg.cast.length - 1, +slot || 0)), q: '', back: document.activeElement};
    const host = document.createElement('div'); host.id = 'hvCp'; host.className = 'hv-vphost';
    host.innerHTML = `<div class="hv-vpscrim" data-a="cpclose" aria-hidden="true"></div><div class="hv-vp" role="dialog" aria-modal="true" aria-labelledby="hvCpH">
      <div class="hv-vph"><h2 class="hv-t" id="hvCpH">Cast the voices</h2><span class="hv-grow"></span><button type="button" class="hv-ib" data-a="cpclose" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hv-cpslots" id="hvCpS" role="tablist" aria-label="Speaker"></div>
      <label class="hv-search hv-vpq">${ic('search', 15)}<span class="hv-sr">Search voices</span><input id="hvCpQ" type="search" placeholder="Search by name, language or feel" autocomplete="off"></label>
      <p class="hv-mut hv-sm" id="hvCpN"></p><div class="hv-vpl" id="hvCpL"></div>
      <div class="hv-vpf"><button type="button" class="hv-btn" data-a="cpall">${ic('play', 12)}Hear them one after the other</button><span class="hv-mut hv-sm">Free: each plays its own sample</span><span class="hv-grow"></span><button type="button" class="hv-cta s" data-a="cpclose">Done</button></div></div>`;
    ROOT.appendChild(host); cpPaint(); $('#hvCpQ')?.focus();
  }
  function cpPaint() {
    const cp = UI.dlg.cp; if (!cp) return; const cast = UI.dlg.cast, me = cast[cp.slot];
    const s = $('#hvCpS'), had = document.activeElement?.closest?.('#hvCpS [data-n]')?.dataset.n;
    if (s) { s.innerHTML = cast.map((c, i) => `<button type="button" role="tab" class="hv-cps${i === cp.slot ? ' on' : ''}" aria-selected="${i === cp.slot}" data-a="cpslot" data-n="${i}"><span class="hv-dav t${i % 4}" aria-hidden="true">${initial(c.name)}</span><span class="hv-ct"><b>${esc(c.name)}</b><small>Voice: ${esc(vname(c.voice))}</small></span></button>`).join('');
      if (had != null) s.querySelector(`[data-n="${had}"]`)?.focus(); }
    const others = cast.filter((_, i) => i !== cp.slot).map(c => voice(c.voice)).filter(Boolean);
    const apart = v => others.length && others.every(o => (v.gender && o.gender && v.gender !== o.gender) || (!(v.gender && o.gender) && String(v.tone || '').split(/[,\s]+/)[0].toLowerCase() !== String(o.tone || '').split(/[,\s]+/)[0].toLowerCase()));
    const lo = cp.q.trim().toLowerCase();
    const list = D.voices.filter(v => !lo || [v.name, v.tone, v.accent, v.gender, ...(v.langs || []).map(c => [c, lang(c)?.name].join(' '))].join(' ').toLowerCase().includes(lo))
      .map(v => ({v, a: apart(v)})).sort((x, y) => (y.a - x.a) || (y.v.ready - x.v.ready));
    const n = $('#hvCpN'); if (n) n.textContent = others.length ? `Picking for ${me.name}. Voices that sound unlike ${others.length === 1 ? esc(cast.find((_, i) => i !== cp.slot).name) : 'the others'} come first, so listeners can tell them apart.` : `Picking for ${me.name}.`;
    const l = $('#hvCpL'); if (!l) return; const fa = document.activeElement?.closest?.('#hvCpL [data-id]'), fk = fa && `[data-a="${fa.dataset.a}"][data-id="${CSS.escape(fa.dataset.id)}"]`;
    l.innerHTML = list.length ? list.map(({v, a}) => { const on = v.id === me.voice, by = cast.find((c, i) => i !== cp.slot && c.voice === v.id);
      return `<div class="hv-vpr${on ? ' on' : ''}"><button type="button" class="hv-play o" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>
        <span class="hv-av l t${D.voices.indexOf(v) % 4}" aria-hidden="true">${initial(v.name)}</span><div class="hv-ct"><b>${esc(v.name)}${a && !by ? ' <span class="hv-badge ok">Easy to tell apart</span>' : ''}${by ? ` <span class="hv-badge">Already ${esc(by.name)}</span>` : ''}</b><small>${esc(vfeel(v))}</small></div>
        ${v.ready ? `<button type="button" class="hv-btn${on ? ' on' : ''}" data-a="cpuse" data-id="${esc(v.id)}" aria-pressed="${on}">${on ? 'Chosen' : `Use for ${esc(me.name)}`}</button>`
          : `<span class="hv-mut hv-sm">${esc(scrub(v.engine && !ready(v.engine) ? whyNot(v.engine) : 'Not ready yet'))}</span>`}</div>`; }).join('')
      : '<p class="hv-mut">No voice matches. Try other words.</p>';
    if (fk) (l.querySelector(fk) || $('#hvCpQ'))?.focus();
  }
  function cpClose() { const h = $('#hvCp'); const back = UI.dlg.cp?.back; UI.dlg.cp = null; h?.remove(); draw(); if (back?.isConnected) back.focus(); }
  // following a take as it plays: the playhead over the lanes and the line being said
  function dlTick() {
    const a = $('#hvAudio'); if (!a || !NOW || PAGE !== 'dialogue') return; const t = dlTakes().find(x => x.id === NOW.id); if (!t?.segments) return;
    const head = $(`.hv-head[data-head="${CSS.escape(t.id)}"]`), total = t.seconds || a.duration || 1;
    if (head) { head.classList.add('on'); head.style.left = `calc(44px + (100% - 58px) * ${Math.min(1, a.currentTime / total).toFixed(4)})`; }
    const s = t.segments.filter(x => !x.reaction).find(x => a.currentTime >= +x.start && a.currentTime < +x.end + 0.25), p = $(`.hv-dlnow[data-now="${CSS.escape(t.id)}"]`);
    if (p && s) p.innerHTML = `<b class="hv-dwn t${dlT(s.speaker)}">${esc(s.speaker)}</b><span class="hv-dtx">${esc(GV_strip(s.text))}</span><span class="hv-num hv-mut">${secs(+s.start)}</span>`;
  }
  const GV_strip = t => String(t || '').replace(/\[[a-z][a-z ]{1,30}\]/g, '').replace(/\s{2,}/g, ' ').trim();
  // choosing a line moves its tools under it, without drawing the page again (the caret stays where she clicked)
  // a line she types in: its Made / Changed mark and its Make only this line button follow at once
  function dlMark(n) {
    const li = $(`.hv-dls .hv-dl[data-n="${n}"]`); if (!li) return; const st = dlState(n), r = li.querySelector('.hv-dlr');
    li.querySelector('.hv-dlr .hv-lst')?.remove();
    if (r && (st.s === 'made' || st.s === 'changed')) r.insertAdjacentHTML('afterbegin', `<span class="hv-lst ${st.s}">${st.s === 'made' ? 'Made' : 'Changed'}</span>`);
    if (UI.dlg.sel === n && !!li.querySelector('[data-a="dlone"]') !== !!st.one) { UI.dlg.sel = -1; dlSel(n); }
  }
  function dlSel(n) {
    UI.dlg.sel = n; $$('.hv-dls .hv-dl').forEach(li => { li.classList.toggle('on', +li.dataset.n === n); li.querySelector('.hv-dltools')?.remove(); });
    const li = $(`.hv-dls .hv-dl[data-n="${n}"]`), l = UI.dlg.lines[n]; if (!li || !l) return;
    const tmp = document.createElement('div'); tmp.innerHTML = dlLine(l, n); const tools = tmp.querySelector('.hv-dltools'); if (tools) li.querySelector('.hv-dlrow').after(tools);
    const tb = $('.hv-dscript .hv-sptools'); if (tb) tb.setAttribute('aria-label', `Tools for line ${n + 1}`); const cb = $('.hv-dscript .hv-sptools [data-a="dlcut"]'); if (cb) cb.setAttribute('aria-pressed', String(!!l.cut));
    if (tools?.querySelector('[data-qbtn="dlone"]')) price('dlone', {job: 'dialogue', chars: (l.text || '').length, lang: UI.dlg.lang || 'auto'}, r => r.credits != null ? 'Only this line is spoken' : '');
  }
  function dlFocus(n, end) { const t = $(`#hvLt${n}`); if (!t) return; t.focus(); const at = end ? t.value.length : 0; try { t.setSelectionRange(at, at); } catch { /* */ } }
  function dlToneAt(tone) {
    const n = UI.dlg.sel, l = UI.dlg.lines[n]; if (!l) return; const {rest} = toneOf(l.text || '');
    l.text = tone === 'pause' ? `${(l.text || '').trimEnd()} [pause] ` : `[${tone}] ${rest}`; draw(); dlFocus(n, true);
  }

  const V = {
    chat: chatView,

    speech: speechView,

    voices() {
      if (ARG === 'compare') return cmpView();
      const f = UI.vf, t = UI.vtab, favs = D.favs || [];
      const base = t === 'mine' ? D.voices.filter(v => v.kind !== 'hoola') : t === 'favs' ? favs.map(id => voice(id)).filter(Boolean) : D.voices.filter(v => v.kind === 'hoola');
      const lo = f.q.trim();
      let list = t === 'shared' ? (UI.lib.list || []) : base.filter(v => (!f.lang || vSpeaks(v, f.lang)) && (!f.accent || v.accent === f.accent)
        && (!f.gender || v.gender === f.gender) && (!f.age || v.age === f.age) && (!f.use || v.use === f.use) && (!UI.vset || vInSet(v, UI.vset)));
      let why = {};
      if (lo && t !== 'shared') { const sc = list.map(v => [v, vMatch(v, lo)]).filter(([, m]) => m.n > 0).sort((a, b) => b[1].n - a[1].n);
        list = sc.map(([v]) => v); sc.forEach(([v, m]) => { why[v.id] = m.why; }); }
      else if (t !== 'shared' && UI.vsort === 'name') list = [...list].sort((a, b) => String(a.name).localeCompare(String(b.name)));
      if (!list.some(v => v.id === UI.vsel)) UI.vsel = list[0]?.id || '';   // a voice is always open beside the list
      const chip = (k, label) => `<button type="button" class="hv-fchip${f[k] ? ' on' : ''}" data-a="vfilter" data-k="${k}" aria-haspopup="menu">${esc(label)}${ic('down', 12)}</button>`;
      const filters = [chip('lang', f.lang ? short(f.lang) : 'Any language'), chip('gender', f.gender ? f.gender[0].toUpperCase() + f.gender.slice(1) : 'Any gender'),
        chip('age', f.age ? f.age[0].toUpperCase() + f.age.slice(1) : 'Any age'), chip('accent', f.accent || 'Any accent'), chip('use', f.use ? 'Use: ' + f.use[0].toUpperCase() + f.use.slice(1) : 'Any use'),
        ...(t === 'shared' ? [`<button type="button" class="hv-fchip" data-a="vfilter" data-k="sort" aria-haspopup="menu">${esc({popular: 'Most used', trending: 'Trending', newest: 'Newest', most_added: 'Most added'}[f.sort] || 'Most used')}${ic('down', 12)}</button>`] : [])].join('');
      const count = t === 'shared' ? (UI.lib.list ? `${plural(list.length, 'voice')}${UI.lib.more ? ' and more' : ''}` : '')
        : lo ? `${plural(list.length, 'best match', 'best matches')}` : `${plural(list.length, 'voice')}${f.lang ? ` speak${list.length === 1 ? 's' : ''} ${short(f.lang)}` : ''}`;
      const tabs = [['hoola', 'Hoola voices', D.voices.filter(v => v.kind === 'hoola').length], ['shared', 'Shared library', 0], ['mine', 'Your voices', D.voices.filter(v => v.kind !== 'hoola').length], ['favs', 'Favourites', favs.length]];
      const sets = t === 'shared' ? '' : `<div class="hv-vsets" role="group" aria-label="Kinds of voices">${VSETS.map(([k, name], i) => { const n = base.filter(v => vInSet(v, k)).length, on = UI.vset === k;
          return `<button type="button" class="hv-vset s${i}" data-a="vset" data-val="${k}" aria-pressed="${on}"><b>${esc(name)}</b><span class="hv-vsetf"><span class="hv-vfaces" aria-hidden="true">${base.filter(v => vInSet(v, k)).slice(0, 3).map(v => `<span class="t${vtint(v.id)}"></span>`).join('')}</span><span class="hv-num">${plural(n, 'voice')}</span></span></button>`; }).join('')}</div>`;
      const row = v => { const shared = t === 'shared', sel = UI.vsel === v.id, g = !shared && !v.ready, fav = favs.includes(v.id);
        return `<article class="hv-vrow${sel ? ' on' : ''}">
          <button type="button" class="hv-play o hv-vhear" data-a="hear" data-id="${esc(v.id)}" aria-label="Hear ${esc(v.name)}"${g ? ' disabled' : ''}>${ic('play', 12)}</button>
          ${vprint(v.id)}
          <button type="button" class="hv-vsel" data-a="vsel" data-id="${esc(v.id)}" aria-pressed="${sel}"><span class="hv-vn"><b>${esc(v.name)}</b>${v.tier === 'premium' || shared ? '<span class="hv-badge">Premium</span>' : ''}${v.kind !== 'hoola' && !shared ? '<span class="hv-src">Yours</span>' : ''}${why[v.id] ? `<span class="hv-vwhy">${esc(why[v.id])}</span>` : ''}</span>
            <span class="hv-mut hv-sm hv-vwords">${esc(shared ? v.line || [v.gender, v.age, v.accent].filter(Boolean).join(' · ') : [vWords(v), v.accent].filter(Boolean).join(' · '))}</span></button>
          <span class="hv-vcol w hv-sm">${esc(shared ? (v.langs || []).map(c => lang(c)?.name || c).slice(0, 2).join(', ') : vLangs(v))}</span>
          <span class="hv-vcol">${v.use ? `<span class="hv-vuse">${esc(v.use)}</span>` : ''}</span>
          ${shared ? `<button type="button" class="hv-btn s dark" data-a="libadd" data-id="${esc(v.id)}">Add</button>`
            : `<button type="button" class="hv-ib hv-star${fav ? ' on' : ''}" data-a="vfav" data-id="${esc(v.id)}" aria-pressed="${fav}" aria-label="Favourite ${esc(v.name)}">${ic('star', 16)}</button>
          <button type="button" class="hv-btn s hv-vuseb" data-a="usev" data-id="${esc(v.id)}"${g ? ' disabled' : ''}>Use</button>`}</article>`; };
      const body = t === 'shared' && UI.lib.list == null ? `<p class="hv-mut">Loading the shared library…</p>`
        : t === 'shared' && !UI.lib.ready ? warnNote(UI.lib.why || 'The shared library is not connected on this server yet.')
        : list.length ? `<div class="hv-vgrid">${list.map(row).join('')}</div>${t === 'shared' && UI.lib.more ? `<button type="button" class="hv-btn" data-a="libmore">Show more</button>` : ''}`
        : t === 'favs' ? empty('No favourites yet', 'Tap the star on a voice to keep it here.')
        : empty(t === 'mine' ? 'No voices of your own yet' : 'No voice matches', t === 'mine' ? 'Record, describe or change one in Your voice.' : 'Try other words, or fewer filters.');
      const cmp = UI.cmp.length ? `<div class="hv-vtray" role="region" aria-label="Voices to compare"><span class="hv-vfaces" aria-hidden="true">${UI.cmp.map(id => `<span class="t${vtint(id)}"></span>`).join('')}</span>
          <span>${plural(UI.cmp.length, 'voice')} to compare · up to 4</span><button type="button" class="hv-btn s" data-a="cmpclear">Clear</button>
          <button type="button" class="hv-btn s light" data-a="go" data-p="voices" data-arg="compare"${UI.cmp.length < 2 ? ' disabled aria-describedby="hvCmpW"' : ''}>Compare</button>${UI.cmp.length < 2 ? '<span class="hv-sr" id="hvCmpW">Add one more voice to compare.</span>' : ''}</div>` : '';
      return `<div class="hv-split hv-tool hv-vlib"><section class="hv-panel wide" aria-label="Voices">
          <div class="hv-vfind">${search('hvVq', 'UI.vf.q', t === 'shared' ? 'Search the shared library: a cricket commentator, a Bengali grandmother…' : 'Describe the voice you want: calm older man for a story, Tamil', f.q)}
            ${t !== 'shared' ? `<div class="hv-vtry"><span class="hv-mut hv-sm">Try</span>${VIDEAS.map(x => `<button type="button" class="hv-chip" data-a="videa" data-val="${esc(x)}">${esc(x)}</button>`).join('')}</div>` : ''}</div>
          <div class="hv-vhead"><div class="hv-seg" role="tablist" aria-label="Which voices">${tabs.map(([k, l, n]) => `<button type="button" class="hv-chip" role="tab" aria-selected="${t === k}" data-a="vtab" data-val="${k}">${esc(l)}${n ? ` <span class="hv-num hv-mut">${num(n)}</span>` : ''}</button>`).join('')}</div>
            <span class="hv-grow"></span><div class="hv-chips">${filters}</div></div>
          ${sets}
          ${t === 'shared' ? `<p class="hv-note hv-vshared">${ic('star', 14)}Shared voices are made by people on ElevenLabs. Hearing them is free; speaking with one is Premium and its maker is credited.</p>` : ''}
          <div class="hv-vlisth"><span class="hv-mut hv-sm hv-count">${esc(count)}${D.voices_loading && t === 'hoola' ? ' · loading the full library…' : ''}</span>${t !== 'shared' && !lo ? `<span class="hv-grow"></span><button type="button" class="hv-fchip" data-a="vfilter" data-k="vsort" aria-haspopup="menu">${UI.vsort === 'name' ? 'A to Z' : 'Hoola order'}${ic('down', 12)}</button>` : ''}</div>
          ${body}${cmp}</section>
        <aside class="hv-stage hv-vdetail" aria-label="The chosen voice">${voiceDetail()}</aside></div>`;
    },


    mine: yvView,

    dialogue: dlView,

    studio() {
      const im = UI.imp;
      if (im.open) return im.pv ? impView() : impStart();
      const books = D.projects;
      return `<div class="hv-doc hv-lib"><div class="hv-libhero"><div class="hv-libcopy"><h2 class="hv-libh">Turn any book into an audiobook.</h2>
          <p>Stories, lessons and handbooks, read chapter by chapter, with a voice for each character. Change a sentence later and only that paragraph is read again.</p>
          <div class="hv-libtags"><span>EPUB, PDF, Word, text or a web page</span><span>Chapters found for you</span><span>One audiobook file with chapters</span></div></div>
          <button type="button" class="hv-sdrop" data-a="impopen" data-drop="imp" aria-label="Import a book: drop a file here, or choose a file, a web address or text">
            <span class="hv-sdi">${ic('upload', 24)}</span><b>Drop a book here</b><span>or choose a file · paste a web address · paste the text</span></button></div>
        <div class="hv-shelfh"><b>Your readings</b>${books.length ? `<span class="hv-num hv-mut hv-sm">${books.length}</span>` : ''}<span class="hv-grow"></span>${books.length > 1 ? '<span class="hv-mut hv-sm">Newest first</span>' : ''}</div>
        ${books.length ? `<div class="hv-shelf">${books.map(p => { const b = bookStat(p);
            return `<button type="button" class="hv-bookc" data-a="proj" data-id="${esc(p.id)}">${coverOf(p)}<span class="hv-vt"><b>${esc(p.title || 'A reading')}</b>
              <span class="hv-mut hv-sm hv-num">${esc([plural(b.n, 'chapter'), langLabel(p.lang), plural(b.voices, 'voice')].join(' · '))}</span>
              <span class="hv-prog" aria-hidden="true"><span style="width:${b.pct}%" class="${b.done ? 'ok' : ''}"></span></span>
              <span class="hv-bst${b.done ? ' ok' : b.made ? ' go' : ''}">${b.done ? `Ready · ${hm(b.secs)}` : b.made ? `${b.made} of ${b.n} made · continue` : 'Not made yet'}</span></span></button>`; }).join('')}</div>`
          : empty('No readings yet', 'Import a book, or start a new reading and paste a story or a lesson. Hoola reads it chapter by chapter.', '<button type="button" class="hv-btn dark" data-a="newproj">New reading</button>')}</div>`;
    },

    reading() {
      const p = UI.proj; if (!p) return V.studio();
      const n = Math.min(UI.chN, p.chapters.length - 1), ch = p.chapters[n] || {title: '', text: ''}, w = paid(speakWhy(p.lang || S.lang, 'auto'));
      const b = bookStat(p), paras = paraList(ch, n), todo = paras.filter(x => x.state !== 'made'), cast = castOf(p);
      const left = p.chapters.filter((c, i) => chState(p, i) !== 'made').length;
      const words = (ch.text || '').trim() ? ch.text.trim().split(/\s+/).length : 0;
      const g = gate(w || (ch.audio && !todo.length ? 'Nothing has changed since this chapter was made.' : !(ch.text || '').trim() ? 'Write the words of this chapter first.' : ''));
      const gl = gate(w || (left ? '' : 'Every chapter is made.'));
      const st = i => chState(p, i), editing = UI.editing || !(ch.text || '').trim();
      const sel = UI.para != null && UI.para < paras.length ? UI.para : null;
      const leftSecs = p.chapters.reduce((s, c, i) => s + (st(i) === 'made' ? 0 : wordsOf(c.text) / 150 * 60), 0);
      return `<div class="hv-split hv-tool three hv-reading"><nav class="hv-chaps" aria-label="Chapters"><div class="hv-bookh">${coverOf(p, 's')}<span class="hv-vt">
            <label class="hv-sr" for="hvPTitle">Title of the reading</label><input id="hvPTitle" class="hv-bkt" data-m="UI.proj.title" data-dirty="1" value="${esc(p.title || '')}" maxlength="80" placeholder="Title of the reading">
            <span class="hv-mut hv-sm">${esc([p.author ? `By ${p.author}` : '', langLabel(p.lang || 'en')].filter(Boolean).join(' · '))}</span>
            <span class="hv-mut hv-sm hv-num">${b.made} of ${b.n} chapters made</span><span class="hv-prog" aria-hidden="true"><span style="width:${b.pct}%"></span></span></span></div>
          <ol class="hv-chol">${p.chapters.map((c, i) => { const s = st(i);
            return `<li><button type="button" class="hv-chap" data-a="chsel" data-n="${i}"${i === n ? ' aria-current="true"' : ''}><span class="hv-num hv-mut hv-chn">${i + 1}</span><span class="hv-cht">${esc(c.title || 'Chapter')}</span>
              <span class="hv-chs ${s}"><span class="hv-dot ${s}" aria-hidden="true"></span><span class="hv-num">${s === 'made' ? secs(c.seconds) : s === 'changed' ? 'Changed' : 'Not made'}</span></span></button></li>`; }).join('')}</ol>
          <button type="button" class="hv-btn s" data-a="chadd">${ic('plus', 14)}Add a chapter</button>
          <span class="hv-grow"></span><div class="hv-acts"><button type="button" class="hv-btn s" data-a="go" data-p="studio">${ic('back', 14)}All readings</button>${p.id ? `<button type="button" class="hv-btn s danger" data-a="rmproj" data-id="${esc(p.id)}">Remove</button>` : ''}</div></nav>
        <section class="hv-panel wide hv-chapter hv-bookpg" aria-label="Chapter ${n + 1}">
          <div class="hv-pgtools"><button type="button" class="hv-btn s" data-a="cast" data-n="${n}"${(ch.text || '').trim() ? '' : ' disabled'}>${ic('dialog', 14)}Find the characters</button>
            <button type="button" class="hv-btn s" data-a="edit" aria-pressed="${editing}"${(ch.text || '').trim() ? '' : ' disabled'}>${ic(editing ? 'check' : 'tone', 14)}${editing ? 'Done' : 'Change the words'}</button>
            <span class="hv-grow"></span><span class="hv-mut hv-sm hv-num">${plural(words, 'word')} · about ${secs(words / 150 * 60)}</span></div>
          ${w ? warnNote(w + ' You can write and save; reading needs the engine.') : ''}
          <div class="hv-pgscroll"><article class="hv-page"><span class="hv-eyebrow">Chapter ${n + 1}</span>
            <label class="hv-sr" for="hvChT">Chapter ${n + 1} title</label><input id="hvChT" class="hv-chtitle" data-m="UI.proj.chapters.${n}.title" data-ch="${n}" data-dirty="1" value="${esc(ch.title || '')}" maxlength="80" placeholder="Chapter ${n + 1}">
            ${editing ? `<label class="hv-sr" for="hvChX">Chapter ${n + 1} words</label><textarea id="hvChX" class="hv-in hv-words serif" data-m="UI.proj.chapters.${n}.text" data-ch="${n}" data-dirty="1" maxlength="${D.limits?.chapter || 40000}" placeholder="The words of this chapter. Leave an empty line between paragraphs.">${esc(ch.text || '')}</textarea>
              <p class="hv-mut hv-sm">Change a word and only that paragraph is read again, in the same voice.</p>`
            : paras.map((x, k) => `<div class="hv-pgw"><button type="button" class="hv-pg${sel === k ? ' on' : ''}" data-a="parasel" data-k="${k}" aria-pressed="${sel === k}" aria-label="Paragraph ${k + 1}, ${x.who === 'Narrator' ? 'the narrator' : esc(x.who)}, ${stName(x.state)}">
                <span class="hv-pdot ${x.state}" aria-hidden="true" title="${stName(x.state)}"></span><span class="hv-pgt">${said(x, cast)}</span></button>
                ${sel === k ? `<div class="hv-pgbar">${x.state === 'made' ? `<button type="button" class="hv-play o" data-a="paraplay" data-k="${k}" aria-label="Play paragraph ${k + 1}">${ic('play', 11)}</button>` : ''}
                  <span class="hv-pgst ${x.state}">${x.state === 'made' ? 'Read as it is' : x.state === 'changed' ? 'Changed since it was read' : 'Not read yet'}</span>
                  <button type="button" class="hv-btn s" data-a="parawho" data-k="${k}" aria-haspopup="menu">${ic('dialog', 13)}Who says it: ${esc(x.who === 'Narrator' ? 'the narrator' : x.who)}</button>
                  <button type="button" class="hv-btn s" data-a="edit">Change the words</button></div>` : ''}</div>`).join('')}
          </article></div>
          <div class="hv-chplay">${ch.audio ? playBtn(ch.audio, `Play chapter ${n + 1}`, 12) : `<span class="hv-play o off" aria-hidden="true">${ic('play', 12)}</span>`}
            <span class="hv-vt"><b>Chapter ${n + 1} · ${esc(ch.title || 'Chapter')}</b><span class="hv-mut hv-sm">${ch.audio ? `Narrator · ${esc(vname(cast.Narrator || p.voice || S.voice))}` : 'Not made yet'}</span></span>
            <span class="hv-grow"></span><span class="hv-mut hv-sm hv-num">${ch.audio ? secs(ch.seconds) : ''}</span></div></section>
        <aside class="hv-stage hv-side2 hv-bookside" aria-label="Making the reading"><div class="hv-stageb">
          <article class="hv-card hv-thisch"><div class="hv-rh"><b>This chapter</b><span class="hv-grow"></span><span class="hv-pill ${ch.audio ? (todo.length ? 'warn' : 'ok') : ''}">${!ch.audio ? 'Not made yet' : todo.length ? plural(todo.length, 'paragraph') + ' changed' : 'Made'}</span></div>
            <span class="hv-sm">${ch.audio ? `Made${ch.made ? ' ' + esc(ago(ch.made)) : ''} · <span class="hv-num">${secs(ch.seconds)}</span>. ` : ''}${ch.audio ? 'Only the changed paragraphs are read again, in the same voices.' : 'Each paragraph is read in the voice of who says it.'}</span>
            <button type="button" class="hv-btn dark" data-a="readch" data-n="${n}" data-qbtn="readch" data-label="${ch.audio ? 'Make the changes' : 'Make this chapter'}"${g.a}><span>${ch.audio ? 'Make the changes' : 'Make this chapter'}</span></button>${g.l}</article>
          <div class="hv-fld"><div class="hv-rh"><b>Who reads whom</b><span class="hv-grow"></span><button type="button" class="hv-link" data-a="sdopen" data-k="people" aria-haspopup="dialog">Change</button></div>
            ${Object.entries(cast).slice(0, 5).map(([who, v], i) => `<div class="hv-role"><span class="hv-dav t${i % 4}${who === 'Narrator' ? ' n' : ''}" aria-hidden="true">${initial(who)}</span><span class="hv-vt"><b>${esc(who)}</b><span class="hv-mut hv-sm">${esc(vname(v))}</span></span>
              <button type="button" class="hv-play o" data-a="hear" data-id="${esc(v)}" aria-label="Hear ${esc(who)}">${ic('play', 10)}</button></div>`).join('')}
            ${Object.keys(cast).length < 2 ? '<p class="hv-mut hv-sm">Find the characters and the words in quotes go to the person who says them.</p>' : ''}</div>
          <div class="hv-fld"><b>How it is read</b>
            ${dd('Reading voice', 'pickpvoice', 'UI.proj.voice', vname(p.voice || S.voice))}${dd('Language', 'picklang', 'UI.proj.lang', langLabel(p.lang || 'en'))}
            <div class="hv-rh"><label for="hvPace" class="hv-lab">Pace</label><span class="hv-grow"></span><span class="hv-mut hv-sm hv-num" data-show="UI.proj.pace">${paceWord(p.pace)}</span></div>
            <input id="hvPace" type="range" class="hv-range" min="0.7" max="1.3" step="0.05" value="${+(p.pace || 1)}" data-m="UI.proj.pace" data-t="num" data-dirty="1" data-pace="1">
            <div class="hv-fld"><span class="hv-lab" id="hvGapL">Quiet between chapters</span>${seg('UI.proj.gap', [[0.5, '0.5 s'], [1, '1 s'], [2, '2 s'], [3, '3 s'], [5, '5 s']], gapOf(p), null, 'Quiet between chapters')}</div></div>
          <span class="hv-grow"></span>
          <article class="hv-card hv-whole"><div class="hv-rh"><b>The whole book</b><span class="hv-grow"></span><span class="hv-mut hv-sm hv-num">${b.made} of ${b.n} made</span></div>
            <div class="hv-strip" aria-hidden="true">${p.chapters.map((_, i) => `<span class="${st(i)}"></span>`).join('')}</div>
            <span class="hv-sm">${left ? `About <span class="hv-num">${hm(leftSecs)}</span> of sound left to make. You can stop any time; nothing made is lost.` : 'Every chapter is made. Put the audiobook together; that is free.'}</span>
            ${left ? `<button type="button" class="hv-cta" data-a="readall" data-qbtn="readall" data-label="Make all ${left} left"${gl.a}><span>Make all ${left} left</span></button>${gl.l}`
              : `<button type="button" class="hv-cta" data-a="sdopen" data-k="book" aria-haspopup="dialog"><span>Make the audiobook</span></button>`}</article></div></aside></div>`;
    },

    dub() {
      if (ARG) return dubView();
      if (UI.dubNew.file) return dubNewView();
      const ds = UI.dubs;
      return `<div class="hv-doc hv-lib hv-dublib"><div class="hv-libhero"><div class="hv-libcopy"><h2 class="hv-libh">Your video, in any language.</h2>
          <p>The same people, speaking Hindi, Spanish or Tamil, with the music kept underneath. Read every line before it is spoken, change any of them, and only that line is made again.</p>
          <div class="hv-libtags"><span>Their own voices, or a matched voice</span><span>Up to 6 languages in one dub</span><span>Subtitles with every dub</span></div></div>
          <button type="button" class="hv-sdrop" data-a="pickfile" data-k="dub" data-drop="dub" data-accept="video/*,audio/*" aria-label="New dub: drop a video here or choose one">
            <span class="hv-sdi">${ic('upload', 24)}</span><b>Drop a video here</b><span>or choose a file · MP4, MOV or a recording</span></button></div>
        <div class="hv-shelfh"><b>Your dubs</b>${ds?.length ? `<span class="hv-num hv-mut hv-sm">${ds.length}</span>` : ''}<span class="hv-grow"></span>${ds?.length > 1 ? '<span class="hv-mut hv-sm">Newest first</span>' : ''}</div>
        ${ds == null ? '<p class="hv-mut">Loading…</p>' : ds.length ? `<div class="hv-dubgrid">${ds.map(x => `<button type="button" class="hv-dubc" data-a="dubopen" data-id="${esc(x.id)}">
            <span class="hv-poster t${tint(x.name)}" aria-hidden="true"><img alt="" data-dposter="${esc(x.id)}"><span class="hv-plen hv-num">${secs(x.seconds)}</span></span>
            <b>${esc(String(x.title || x.name || 'Dub').replace(/\.[a-z0-9]{2,4}$/i, ''))}</b>
            <span class="hv-mut hv-sm">${esc([x.source_lang, x.mode === 'own' ? 'their own voices' : 'matched voices', ago(x.made)].filter(Boolean).join(' · '))}</span>
            <span class="hv-ltags">${(x.langs || []).map(l => typeof l === 'string' ? {code: l, name: short(l), status: x.status} : l).map(l =>
              `<span class="hv-ltag ${dubSt(l.status)}"><span class="hv-dot ${dubSt(l.status)}" aria-hidden="true"></span>${esc(l.name || short(l.code))}${l.status === 'ready' ? '' : ' · ' + dubWord(l)}</span>`).join('')}</span></button>`).join('')}</div>`
          : empty('No dubs yet', 'Drop a video above, or choose one. You read the lines before anything is spoken.')}</div>`;
    },

    changer() {
      if (!ready('eleven') || !chgVoices().length) return chgNot();
      if (UI.chg.view === 'compare') return chgCompare();
      if (UI.chg.view === 'list') return chgList();
      return chgMain();
    },

    cleanup() {
      if (!ready('server')) return clNot();
      if (UI.cl.job) return clWork();
      if (UI.cl.view === 'list') return clList();
      if (!UI.cl.file && !UI.cl.out) return clStart();
      return clMain();
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

  function libVoice(id) { return (UI.lib.list || []).find(v => v.id === id); }
  // ------------------------------------------------------------------ voice library (v0.999.151 VOICE LIBRARY, PREMIUM) ---
  const VSETS = [['story', 'Narration & stories', ['narrat', 'story', 'stories', 'audiobook', 'informative', 'knowledgeable', 'documentary', 'clear', 'mature', 'firm', 'even']],
    ['ads', 'Ads & promos', ['upbeat', 'excited', 'lively', 'bright', 'energetic', 'ad', 'ads', 'advert', 'promo', 'youthful', 'social', 'reels']],
    ['talk', 'Conversation', ['friendly', 'casual', 'easy', 'warm', 'conversation', 'support', 'breezy', 'forward', 'chat']],
    ['char', 'Characters', ['gravelly', 'breathy', 'playful', 'character', 'animation', 'games', 'rough', 'husky', 'deep', 'quirky']],
    ['calm', 'Calm & soothing', ['calm', 'soft', 'smooth', 'gentle', 'soothing', 'meditation', 'relaxed', 'mellow']]];
  const VIDEAS = ['Warm narrator', 'Young and bright, for ads', 'Calm older man', 'News reader', 'Kind voice for kids'];
  const VWORDS = {man: 'male', men: 'male', male: 'male', boy: 'male', guy: 'male', woman: 'female', women: 'female', lady: 'female', female: 'female', girl: 'female',
    old: 'older', older: 'older', elderly: 'older', senior: 'older', grandmother: 'older', grandfather: 'older', young: 'young', youthful: 'young', teen: 'young',
    middle: 'middle', 'middle-aged': 'middle', kids: 'kids', kid: 'kids', children: 'kids'};
  const VSKIP = new Set(['a', 'an', 'the', 'for', 'and', 'with', 'of', 'to', 'in', 'voice', 'voices', 'who', 'that', 'very', 'bit', 'little', 'my', 'some', 'like']);
  const vtint = id => [...String(id || 'x')].reduce((a, c) => a + c.charCodeAt(0), 0) % 6;
  // a voice's own picture: seven bars drawn from its id, in its own colour (never a letter)
  const vprint = (id, cls = '') => { let h = [...String(id || 'x')].reduce((a, ch) => (a * 31 + ch.charCodeAt(0)) % 9973, 0); const bars = [];
    for (let i = 0; i < 7; i++) { h = (h * 17 + 7) % 101; bars.push(6 + (h % 13)); }
    return `<span class="hv-vprint t${vtint(id)}${cls ? ' ' + cls : ''}" aria-hidden="true">${bars.map(b => `<span style="--h:${b}"></span>`).join('')}</span>`; };
  const vEngineLangs = v => D.langs.filter(l => v.engine === 'eleven' ? l.speech === 'yes' || l.speech === 'premium' : l.speech === 'yes').map(l => l.code);
  const vSpeaks = (v, code) => (v.langs || []).includes(code) || (v.any && vEngineLangs(v).includes(code));
  const vLangs = v => { const ls = (v.langs || []).map(c => lang(c)?.name || c), all = v.any ? vEngineLangs(v).length : 0, lc = UI.vlang || (S.lang !== 'auto' ? S.lang : '');
    if (ls.length) return ls.slice(0, 2).join(', ') + (ls.length > 2 ? ` +${num(ls.length - 2)}` : '');
    return all ? (lc && vSpeaks(v, lc) ? `${short(lc)} and ${num(all - 1)} more` : plural(all, 'language')) : 'Every language its engine speaks'; };
  const vWords = v => [v.tone, v.age === 'middle' ? 'middle-aged' : v.age, v.gender].filter(Boolean).join(' · ') || v.line || 'A natural voice';
  const vHay = v => [v.name, v.tone, v.accent, v.use, v.gender, v.age, v.line].join(' ').toLowerCase();
  const vInSet = (v, k) => { const set = VSETS.find(s => s[0] === k); if (!set) return true; const hay = vHay(v); return set[2].some(w => new RegExp(`\\b${w}`).test(hay)); };
  // "calm older man for a story, Tamil": each word read as a gender, an age, a language, a kind of voice or a feel; the why is said
  function vMatch(v, q) {
    const hay = vHay(v), why = []; let n = 0;
    for (const raw of String(q).toLowerCase().split(/[\s,;.]+/).filter(Boolean)) {
      if (VSKIP.has(raw)) continue;
      const g = VWORDS[raw];
      if (g === 'male' || g === 'female') { if (v.gender === g) { n += 2; why.push(g); } else if (v.gender) n -= 3; continue; }
      if (g === 'older' || g === 'young' || g === 'middle') { if (v.age === g || hay.includes(g)) { n += 2; why.push(g === 'middle' ? 'middle-aged' : g); } continue; }
      const L = D.langs.find(l => [l.code, String(l.name).toLowerCase(), String(l.native).toLowerCase()].includes(raw));
      if (L) { if (vSpeaks(v, L.code)) { n += 2; why.push(L.name); } else n -= 4; continue; }
      const set = VSETS.find(s => s[2].some(w => raw.startsWith(w) || w.startsWith(raw.replace(/s$/, ''))));
      if (hay.includes(raw.replace(/s$/, ''))) { n += 3; why.push(raw); }
      else if (set && vInSet(v, set[0])) { n += 1; why.push(set[1].split(' ')[0].toLowerCase()); }
    }
    return {n, why: n > 0 ? [...new Set(why)].slice(0, 4).join(', ') : ''};
  }
  // how she used a voice: from her sounds
  const vUse = id => { const hs = (D.history || []).filter(h => h.voice === id); return {n: hs.length, last: hs[0]}; };
  const vRecent = () => [...new Set((D.history || []).map(h => h.voice).filter(Boolean))].filter(id => voice(id)).slice(0, 12);
  const vSampleLine = code => (D.sample_lines || {})[code] || (D.sample_lines || {}).en || '';
  const vHearLang = v => { const want = UI.vlang || (S.lang !== 'auto' ? S.lang : '') || 'en'; return v && !vSpeaks(v, want) && (v.langs || []).length ? v.langs[0] : want; };
  async function vFav(id, b) {
    const on = !(D.favs || []).includes(id);
    try { const r = await api('PUT', `${A}/voices/fav`, {id, on}); D.favs = r.favs || []; toast(on ? `${vname(id)} is in your favourites.` : `${vname(id)} is out of your favourites.`); }
    catch (e) { toast(e.message, true); return; }
    if (PAGE === 'voices') { draw(); $(`[data-a="vfav"][data-id="${CSS.escape(id)}"]`)?.focus(); }
    if (SP.vp) { vpPaint(); }
  }
  // ------------------------------------------------------------------ v0.999.157 Your voice: home, the first time, three ways, one voice ---
  const YK = {clone: 'Recorded from you', design: 'Described in words', remix: 'Changed from a voice', shared: 'From the shared library'};
  const YF = [['all', 'All', () => true], ['clone', 'Recorded', v => v.kind === 'clone'], ['design', 'Described', v => v.kind === 'design'], ['remix', 'Changed', v => v.kind === 'remix']];
  const YSTEPS = ['Read the line', 'Keep talking', 'Check it', 'Name and make'];
  const YRX = [['Age', ['Younger', 'Older']], ['Pitch', ['Deeper', 'Higher']], ['Energy', ['Calmer', 'More energetic']], ['Pace', ['Slower', 'Faster']],
    ['Feel', ['Warmer', 'Crisper', 'Softer']], ['Accent', ['Indian English', 'British English', 'American English', 'Neutral']]];
  const YADD = [['Age', ['young', 'middle-aged', 'older']], ['Voice', ['deep', 'bright', 'husky', 'soft']], ['Pace', ['slow', 'steady', 'quick']], ['Feel', ['warm', 'calm', 'confident', 'playful']]];
  const YREF = ['A little slower', 'Warmer', 'Deeper', 'Brighter', 'Less breathy'];
  const yMine = () => D.voices.filter(v => v.kind !== 'hoola');
  const yWays = () => [
    {k: 'record', n: 'Record your voice', l: 'Read one line out loud, then keep talking for about 30 seconds.', needs: 'A quiet room and a microphone', time: 'Ready in about a minute', q: 'clone', icon: 'mic'},
    {k: 'design', n: 'Describe a voice', l: '“A kind older teacher, slow and clear.” Hear three options and keep one.', needs: 'Just a sentence', time: 'Three options in about 20 seconds', q: 'design', icon: 'edit'},
    {k: 'remix', n: 'Change a voice', l: 'Start from a voice you like and make it older, softer or faster.', needs: 'A voice to start from', time: 'Before and after to compare', q: 'remix', icon: 'swap'}];
  const yWayIcon = n => ic(n, 22);
  const yBack = (label = 'Your voice') => `<button type="button" class="hv-lnk hv-yvback" data-a="yvhome">${ic('back', 14)}${esc(label)}</button>`;
  function yvView() {
    const mine = yMine();
    if (UI.yv === 'detail') { const v = voice(UI.mv); if (v && v.kind !== 'hoola') return yvDetail(v); UI.yv = 'home'; }
    if (UI.yv === 'make') return yvMake();
    return mine.length ? yvHome(mine) : yvFirst();
  }
  function yvCard(v) {
    const hl = vHearLang(v), u = vUse(v.id);
    const facts = [`Speaks ${vLangs(v)}`, v.kind === 'clone' ? (v.consent_kept ? 'Your consent is kept' : 'Made with your yes') : v.kind === 'remix' && v.base_name ? `Changed from ${v.base_name}` : '',
      u.n ? `Used in ${plural(u.n, 'sound')}` : 'Not used yet'].filter(Boolean);
    return `<article class="hv-card hv-mv hv-yvc"><div class="hv-yvch">${vprint(v.id, 'l')}<span class="hv-vt"><b class="hv-yvn">${esc(v.name)}</b><span class="hv-yvk k-${esc(v.kind)}">${esc(YK[v.kind] || 'Yours')}</span></span>
        <button type="button" class="hv-ib s" data-a="mvmenu" data-id="${esc(v.id)}" aria-label="More for ${esc(v.name)}: use, rename, change, remove">${ic('more')}</button></div>
      <div class="hv-yvs"><button type="button" class="hv-play s" data-a="hear" data-id="${esc(v.id)}" data-lang="${esc(hl)}" aria-label="Hear ${esc(v.name)} in ${esc(short(hl))}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>${wave(v.id, 34, 'thin')}</div>
      <span class="hv-vline" lang="${esc(hl)}">“${esc(vSampleLine(hl))}”</span>
      <ul class="hv-yvf">${facts.map(f => `<li>${esc(f)}</li>`).join('')}</ul>
      ${v.ready ? '' : `<p class="hv-why">${esc(v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.')}</p>`}
      <div class="hv-yvca"><button type="button" class="hv-cta s" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}><span>Use in Speech</span></button>
        <button type="button" class="hv-btn" data-a="yvopen" data-id="${esc(v.id)}">Open</button></div></article>`;
  }
  function yvHome(mine) {
    const f = YF.find(x => x[0] === UI.yvf) || YF[0], list = mine.filter(f[2]);
    return `<div class="hv-doc hv-yv"><div class="hv-doc hv-yvbar"><div class="hv-seg" role="tablist" aria-label="Show">${YF.map(([k, l, fn]) => { const n = mine.filter(fn).length;
        return `<button type="button" class="hv-chip" role="tab" aria-selected="${f[0] === k}" data-a="yvf" data-val="${k}">${esc(l)} <span class="hv-num hv-mut">${num(n)}</span></button>`; }).join('')}</div>
        <span class="hv-grow"></span><span class="hv-mut hv-sm hv-count">${plural(mine.length, 'voice')} of ${num(D.limits?.voices || 30)}</span>
        <button type="button" class="hv-cta s" data-a="yvmake" data-val="record">${ic('plus', 14)}<span>Make a voice</span></button></div>
      ${list.length ? `<div class="hv-yvgrid">${list.map(yvCard).join('')}</div>` : empty(`No ${esc(f[1].toLowerCase())} voices yet`, 'Make one with the ways below.')}
      <h2 class="hv-yvh2">Make another voice</h2>
      <div class="hv-yvways">${yWays().map(w => `<button type="button" class="hv-yvway" data-a="yvmake" data-val="${w.k}"><span class="hv-yvwi w-${w.k}">${yWayIcon(w.icon)}</span>
        <span class="hv-vt"><b>${esc(w.n)}</b><span class="hv-mut hv-sm">${esc(w.time)}</span></span>${ic('chev', 14)}</button>`).join('')}</div></div>`;
  }
  function yvFirst() {
    const steps = [['Read one line', 'A short sentence that says this is your voice and you agree. In your language.'],
      ['Keep talking', 'About your day or your work, up to 30 seconds. Hoola checks the sound as soon as you stop.'],
      ['Check it', 'Play it back. Too quiet or noisy? Record again, nothing is spent.'], ['Name it and make it', 'About a minute. Then hear it say anything, in any language it speaks.']];
    return `<div class="hv-doc hv-yv hv-yvfirst"><section class="hv-yvhero" aria-label="Make a voice"><span class="hv-badge">No voices of your own yet</span>
        <h2 class="hv-yvtitle">A voice that is yours, in every language you work in.</h2>
        <p class="hv-yvlead">Record yourself once, describe a voice in a sentence, or change one you like. Only you can use it, and you can delete it at any time.</p>
        <div class="hv-yvbig">${yWays().map(w => `<div class="hv-card hv-yvbw"><span class="hv-yvwi w-${w.k}">${yWayIcon(w.icon)}</span>
          <span class="hv-vt"><b>${esc(w.n)}</b><span>${esc(w.l)}</span><span class="hv-mut hv-sm">${esc(w.needs)} · ${esc(w.time)} · <span data-qline="yw${w.k}">priced before you tap</span></span></span>
          <button type="button" class="hv-cta s${w.k === 'record' ? '' : ' hv-ink'}" data-a="yvmake" data-val="${w.k}"><span>${w.k === 'record' ? 'Start' : w.k === 'design' ? 'Describe' : 'Change'}</span></button></div>`).join('')}</div></section>
      <aside class="hv-yvside" aria-label="How it works"><div class="hv-card hv-yvhow"><b>How your own voice is made</b><ol>${steps.map(([t, d], i) => `<li><span class="hv-num">${i + 1}</span><span class="hv-vt"><b>${esc(t)}</b><span class="hv-mut hv-sm">${esc(d)}</span></span></li>`).join('')}</ol></div>
        <div class="hv-yvkeep"><b>What Hoola keeps, and what it never does</b><ul><li>Your consent recording, as proof, for as long as the voice exists.</li><li>No one else can speak with your voice.</li>
          <li>Never a famous or named person’s voice, and no one under 18.</li><li>Every file made with it carries an AI mark.</li></ul></div></aside></div>`;
  }
  function yvMake() {
    const w = UI.way, ways = yWays();
    const head = `<div class="hv-yvmh">${yBack()}<div class="hv-ways two hv-yvpick" role="radiogroup" aria-label="How to make it">${ways.map(x => `<button type="button" role="radio" class="hv-way" aria-checked="${w === x.k}" data-a="way" data-val="${x.k}"><b>${esc(x.n)}</b><span>${esc(x.time)}</span></button>`).join('')}</div></div>`;
    return `<div class="hv-doc hv-yv hv-yvmake">${head}${w === 'design' ? yvDesign() : w === 'remix' ? yvRemix() : yvRecord()}</div>`;
  }
  const canMake = k => (k === 'clone' ? D.status.connected.clone : D.status.connected.design) ?? (ready('gemini') || ready('lab'));
  const noEngine = ok => ok ? '' : 'No engine that makes voices is connected on this server yet.';
  // the four checks on her recording: read from the sound itself once it stops (the browser decodes it), never guessed
  function yChecks(slot) {
    if (!slot) return [];
    const m = slot.meter, out = [[slot.secs >= 10, slot.secs >= 10 ? `Long enough (${secs(slot.secs)})` : `Long enough: ${Math.max(1, Math.ceil(10 - (slot.secs || 0)))} more seconds needed`]];
    if (m) out.unshift([m.loud, m.loud ? 'Loud enough' : 'Too quiet: come closer to the microphone'], [!m.clip, m.clip ? 'Too loud in places: move back a little' : 'Not too loud'],
      [!m.noise, m.noise ? 'Background noise: try a quieter room' : 'Little background noise']);
    out.push([!!slot.file_id, slot.file_id ? 'Uploaded' : slot.err ? 'The recording did not upload' : 'Uploading…']);
    return out;
  }
  function yvRecord() {
    const cl = UI.clone, cline = UI.cline[cl.lang], sl = cl.consent, recOn = !!REC.consent, ok = canMake('clone');
    const checks = yChecks(sl), good = checks.length && checks.every(c => c[0]);
    const step = recOn ? 1 : !sl ? 0 : !cl.ok ? 2 : 3;
    const gc = gate(paid(noEngine(ok) || (!sl?.file_id ? 'Record the line first.' : !cl.ok ? 'Tick the box above first.' : '')));
    const t = recOn ? 0 : sl?.secs || 0;
    return `<form class="hv-form hv-yvrec" data-f="clone">${noEngine(ok) ? warnNote(noEngine(ok)) : ''}
      <ol class="hv-yvsteps" aria-label="Steps">${YSTEPS.map((x, i) => `<li class="${i < step ? 'done' : i === step ? 'now' : ''}"${i === step ? ' aria-current="step"' : ''}><span class="hv-num">${i < step ? ic('check', 12) : i + 1}</span>${esc(x)}</li>`).join('')}</ol>
      <div class="hv-yvrecg"><div class="hv-card hv-recard"><div class="hv-rh"><b>Read this out loud, in your own voice</b><button type="button" class="hv-dd s" data-a="picklang" data-k="UI.clone.lang" data-need="clone" aria-haspopup="menu"><span>${esc(short(cl.lang))}</span>${ic('down', 12)}</button></div>
          ${cline ? `<p class="hv-consent" lang="${esc(cline.locale || cline.lang || '')}">“${esc(cline.line)}”</p>${cline.english && cline.english !== cline.line ? `<p class="hv-mut hv-sm">“${esc(cline.english)}”</p>` : ''}
            ${cline.lang && cline.lang !== cl.lang ? `<p class="hv-why">There is no consent statement in ${esc(lang(cl.lang)?.name || cl.lang)} yet, so the English one is used.</p>` : ''}` : '<p class="hv-mut">Loading the statement…</p>'}
          <p class="hv-mut hv-sm">Then keep talking naturally until about 30 seconds: about your day, your work, a story. This one recording makes your voice.</p>
          <div class="hv-yvmic"><button type="button" class="hv-recb xl${recOn ? ' on' : ''}" data-a="${recOn ? 'recstop' : 'rec'}" data-k="consent" style="--p:${Math.min(1, t / 30).toFixed(3)}" aria-label="${recOn ? 'Stop recording' : sl ? 'Record again' : 'Start recording'}">${recOn ? '<span class="hv-sq"></span>' : ic('mic', 26)}</button>
            <span class="hv-vt"><b>${recOn ? 'Recording' : sl ? 'Recorded' : 'Tap to start recording'}</b><span class="hv-mut hv-num" data-rect="consent">${recOn ? '0:00 of 0:30' : sl ? esc([sl.name, sl.secs ? secs(sl.secs) : '', sl.up ? 'uploading…' : sl.err || ''].filter(Boolean).join(' · ')) : 'up to 30 seconds'}</span>
              <span class="hv-yvlvl" aria-hidden="true"><span data-lvl="consent"></span></span></span></div>
          <span class="hv-mut hv-sm">or <button type="button" class="hv-lnk" data-a="pickrec" data-k="consent">${ic('upload', 13)}choose a recording</button> · 10 to 30 seconds</span></div>
        <div class="hv-yvcheck"><div class="hv-card"><b>Checks on your recording</b>
            ${checks.length ? `<ul class="hv-checks">${checks.map(([okc, x]) => `<li class="${okc ? 'ok' : 'warn'}">${ic(okc ? 'check' : 'warn', 14)}${esc(x)}</li>`).join('')}</ul>`
              : '<p class="hv-mut hv-sm">Loud enough, not too loud, little background noise and long enough are checked as soon as you stop.</p>'}
            ${sl?.url ? `<div class="hv-rh"><button type="button" class="hv-btn" data-a="recplay"><span>${ic('play', 12)} Play it back</span></button><button type="button" class="hv-btn" data-a="recagain"><span>Record again</span></button></div>` : ''}
            ${sl && !good && checks.length && !sl.up ? '<p class="hv-why">You can still make the voice, but a cleaner recording makes a closer voice. Recording again costs nothing.</p>' : ''}</div>
          <div class="hv-fld"><label class="hv-lab" for="hvCName">Name of the voice</label><input id="hvCName" class="hv-in" maxlength="40" data-m="UI.clone.name" value="${esc(cl.name)}"></div>
          <label class="hv-check"><input type="checkbox" id="hvCOk" required data-m="UI.clone.ok" data-t="bool" data-redraw="1"${cl.ok ? ' checked' : ''}><span>This is my own voice. I agree that Hoola keeps this recording as proof of my consent, and I can delete the voice at any time.</span></label>
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="clone" data-label="Make my voice"${gc.a}><span>Make my voice</span></button></div>${gc.l}
          <p class="hv-mut hv-sm">Never a famous or named person’s voice. A voice of someone else needs them to read the statement themselves. No one under 18.</p></div></div></form>`;
  }
  function yvDesign() {
    const ds = UI.design, ok = canMake('design'), gd = gate(paid(noEngine(ok))), gs = gate(ds.pick ? '' : 'Pick one of the three options first.');
    const dl = ds.lang || (S.lang !== 'auto' ? S.lang : 'en');
    return `<form class="hv-form hv-yvdes" data-f="design">${noEngine(ok) ? warnNote(noEngine(ok)) : ''}
      <div class="hv-yvdg"><div class="hv-yvdl"><div class="hv-fld"><label class="hv-lab" for="hvDDesc">Describe the voice</label><textarea id="hvDDesc" class="hv-in hv-serif" rows="4" maxlength="300" data-m="UI.design.desc" placeholder="A kind older teacher, slow and clear, a little warm.">${esc(ds.desc)}</textarea>
            <span class="hv-hint">Who · age · tone · pace · accent · the room. Never a named person.</span></div>
          <div class="hv-yvadd"><span class="hv-lab">Add to it</span>${YADD.map(([g, ws]) => `<div class="hv-chips"><span class="hv-mut hv-sm">${esc(g)}</span>${ws.map(x => `<button type="button" class="hv-chip" data-a="dadd" data-val="${esc(x)}">${esc(x)}</button>`).join('')}</div>`).join('')}</div>
          <div class="hv-rh">${dd('Gender', 'pickgender', 'UI.design.gender', ds.gender ? ds.gender[0].toUpperCase() + ds.gender.slice(1) : 'Not set')}
            <div class="hv-fld"><span class="hv-lab">What the options say</span><button type="button" class="hv-dd" data-a="picklang" data-k="UI.design.lang" aria-haspopup="menu"><span>${esc(short(dl))}</span>${ic('down', 12)}</button></div></div>
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="design" data-label="Make 3 options"${gd.a}><span>Make 3 options</span></button></div>${gd.l}</div>
        <div class="hv-yvdr">${ds.previews.length ? `<span class="hv-lab">Pick the one you like</span><div class="hv-yvopts" role="radiogroup" aria-label="The three options">${ds.previews.map((p, i) => { const L = 'ABC'[i] || i + 1, on = ds.pick === p.pid;
              return `<div class="hv-card hv-yvopt${on ? ' on' : ''}"><div class="hv-rh">${vprint(p.pid, 'm')}<b>Option ${L}</b></div>
                <div class="hv-yvs">${playBtn(p.audio_id, `Play option ${L}`, 12, ' s')}${wave(p.pid, 30, 'thin')}</div>
                <button type="button" class="hv-btn" role="radio" aria-checked="${on}" data-a="dpick" data-val="${esc(p.pid)}">${on ? 'Picked' : `Pick ${L}`}</button></div>`; }).join('')}</div>
            <div class="hv-fld"><label class="hv-lab" for="hvDName">Name</label><input id="hvDName" class="hv-in" maxlength="40" data-m="UI.design.name" value="${esc(ds.name)}" placeholder="Kind teacher"></div>
            <div class="hv-ctarow"><button type="button" class="hv-cta" data-a="dsave"${gs.a}><span>${ds.pick ? `Save option ${'ABC'[ds.previews.findIndex(p => p.pid === ds.pick)] || ''}` : 'Save the voice'}</span></button></div>${gs.l}
            <div class="hv-chips"><span class="hv-mut hv-sm">Not quite?</span>${YREF.map(x => `<button type="button" class="hv-chip" data-a="dref" data-val="${esc(x)}">${esc(x)}</button>`).join('')}</div>
            <p class="hv-mut hv-sm">Each change makes three new options. Every file made with the voice carries an AI mark.</p>`
          : empty('Three options to hear', 'Describe the voice, then make three. You keep only the one you like.')}</div></div></form>`;
  }
  function yvRemix() {
    const rx = UI.remix, ok = canMake('design'), base = voice(rx.base), gr = gate(paid(noEngine(ok) || (base ? '' : 'Choose a voice to start from.')));
    const hl = base ? vHearLang(base) : 'en', made = rx.made ? voice(rx.made) : null;
    return `<form class="hv-form hv-yvrx" data-f="remix">${noEngine(ok) ? warnNote(noEngine(ok)) : ''}
      <div class="hv-yvdg"><div class="hv-yvdl"><span class="hv-lab">Start from</span>
          <div class="hv-card hv-mv hv-yvbase">${base ? vprint(base.id, 'm') : ''}<span class="hv-vt"><b>${esc(base ? base.name : 'Choose a voice')}</b><span class="hv-mut hv-sm">${esc(base ? (base.kind === 'hoola' ? 'Hoola voice' : YK[base.kind] || 'Yours') : 'Any Standard voice or one of yours')}</span></span>
            <button type="button" class="hv-btn" data-a="pickbase" aria-haspopup="menu">Change</button></div>
          ${YRX.map(([g, ws]) => `<div class="hv-chips hv-yvrxr" role="group" aria-label="${esc(g)}"><span class="hv-mut hv-sm">${esc(g)}</span>${ws.map(x => `<button type="button" class="hv-chip" data-a="rxpick" data-k="${esc(g)}" data-val="${esc(x)}" aria-pressed="${(UI.rxp || {})[g] === x}">${esc(x)}</button>`).join('')}</div>`).join('')}
          <div class="hv-fld"><label class="hv-lab" for="hvRChange">In your words</label><input id="hvRChange" class="hv-in" maxlength="300" data-m="UI.remix.change" value="${esc(rx.change)}" placeholder="Same voice, but older and a little calmer"></div>
          <div class="hv-fld"><label class="hv-lab" for="hvRName">Name</label><input id="hvRName" class="hv-in" maxlength="40" data-m="UI.remix.name" value="${esc(rx.name)}" placeholder="${esc(base ? base.name + ', softer' : 'My voice, softer')}"></div>
          <div class="hv-ctarow"><button class="hv-cta" data-qbtn="remix" data-label="Make the change"${gr.a}><span>Make the change</span></button></div>${gr.l}</div>
        <div class="hv-yvdr">${made ? `<span class="hv-lab">Before and after, the same words</span>
            <div class="hv-yvba"><div class="hv-card hv-sample"><b>Before · ${esc(base?.name || '')}</b><div class="hv-yvs"><button type="button" class="hv-play s" data-a="hear" data-id="${esc(rx.base)}" data-lang="${esc(hl)}" aria-label="Hear the voice before">${ic('play', 12)}</button>${wave(rx.base, 30, 'thin')}</div></div>
              <div class="hv-card hv-sample on"><b>After · ${esc(made.name)}</b><div class="hv-yvs"><button type="button" class="hv-play s" data-a="hear" data-id="${esc(made.id)}" data-lang="${esc(hl)}" aria-label="Hear the new voice"${made.ready ? '' : ' disabled'}>${ic('play', 12)}</button>${wave(made.id, 30, 'thin')}</div></div></div>
            <span class="hv-vline" lang="${esc(hl)}">“${esc(vSampleLine(hl))}”</span>
            <div class="hv-ctarow"><button type="button" class="hv-cta" data-a="rxkeep"><span>Keep the new voice</span></button><button type="button" class="hv-btn" data-a="rxdrop"><span>Not this one, remove it</span></button></div>`
          : empty('Before and after', 'Pick what to change on the left. Then hear the old and the new voice say the same words.')}</div></div></form>`;
  }
  function yvDetail(v) {
    UI.vsel = v.id;
    const hl = vHearLang(v), uses = (D.history || []).filter(h => h.voice === v.id), all = v.any ? vEngineLangs(v) : (v.langs || []), isDef = (D.settings || {}).voice === v.id;
    const gT = gate(!v.ready ? (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.') : paid(''));
    const facts = [['Made', `${v.kind === 'clone' ? 'From your recording' : v.kind === 'design' ? 'From your words' : v.kind === 'remix' ? `Changed from ${v.base_name || 'a voice'}` : 'Added from the shared library'}${v.made ? ' · ' + ago(v.made) : ''}`],
      ...(v.description ? [[v.kind === 'remix' ? 'The change' : 'Described as', v.description]] : []),
      ['Speaks', all.length ? all.slice(0, 3).map(c => lang(c)?.name || c).join(', ') + (all.length > 3 ? ` and ${num(all.length - 3)} more` : '') : 'Every language its engine knows'],
      ['Engine', `${engName(v.engine)}${v.tier === 'premium' ? ' · Premium' : ' · Standard'}`], ['Used', uses.length ? `${plural(uses.length, 'sound')} · last ${ago(uses[0].made)}` : 'Not used yet']];
    const acts = [['yvchange', 'Change this voice', 'Older, softer, faster', !v.ready || v.engine !== 'gemini'], ['vlike', 'Make one like it', 'Describe a new voice from this one', false],
      ['yvdef', isDef ? 'Your default voice' : 'Make your default voice', 'For every new sound', isDef], ['yvdl', 'Download the sample', 'WAV', !v.ready], ['yvrm', 'Delete this voice', 'Sounds already made stay', false]];
    return `<div class="hv-doc hv-yv hv-yvd">${yBack()}<div class="hv-yvdh">${vprint(v.id, 'xl')}<span class="hv-vt">${UI.ren === v.id ? `<form class="hv-yvnm" data-f="yvren"><label class="hv-sr" for="hvRen">New name</label><input id="hvRen" class="hv-in" maxlength="40" value="${esc(v.name)}"><button class="hv-cta s"><span>Save</span></button><button type="button" class="hv-btn" data-a="yvrenx">Cancel</button></form>`
          : `<span class="hv-yvnm"><b class="hv-vdn">${esc(v.name)}</b><button type="button" class="hv-ib s" data-a="yvren" data-id="${esc(v.id)}" aria-label="Rename ${esc(v.name)}">${ic('edit', 15)}</button></span>`}
        <span class="hv-chips"><span class="hv-yvk k-${esc(v.kind)}">${esc(YK[v.kind] || 'Yours')}</span><span class="hv-badge">Only you can use it</span>${isDef ? '<span class="hv-badge ok">Default</span>' : ''}</span></span>
        <span class="hv-grow"></span><div class="hv-vuse2"><button type="button" class="hv-cta" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}><span>Use in Speech</span></button><button type="button" class="hv-cta hv-ctam" data-a="vusein" data-id="${esc(v.id)}" aria-haspopup="menu" aria-label="Use it somewhere else"${v.ready ? '' : ' disabled'}>${ic('down', 14)}</button></div></div>
      ${v.ready ? '' : `<p class="hv-note warn">${esc(v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.')}</p>`}
      <div class="hv-yvdg"><div class="hv-yvdl"><div class="hv-card hv-sample"><div class="hv-rh"><b>Hear it</b><span class="hv-grow"></span><span class="hv-mut hv-sm">in</span><button type="button" class="hv-chip" data-a="vlang" aria-haspopup="menu">${esc(short(hl))}</button></div>
            <div class="hv-yvs"><button type="button" class="hv-play hv-vhear" data-a="hear" data-id="${esc(v.id)}" data-lang="${esc(hl)}" aria-label="Hear ${esc(v.name)}'s sample in ${esc(short(hl))}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>${wave(v.id, 44, 'thin')}</div>
            <span class="hv-vline" lang="${esc(hl)}">“${esc(vSampleLine(hl))}”</span><span class="hv-mut hv-sm">Hearing the sample is free.</span>
            <div class="hv-fld"><label class="hv-lab" for="hvTry">Hear it say your words</label><div class="hv-chips">${VTRY.map(([k, w]) => `<button type="button" class="hv-chip" data-a="vtryp" data-val="${esc(k)}" aria-pressed="${UI.tryText === w}">${esc(k)}</button>`).join('')}</div>
              <div class="hv-tryrow"><input id="hvTry" class="hv-in" maxlength="200" data-m="UI.tryText" value="${esc(UI.tryText)}" placeholder="Hello, today's special offer is…"><button type="button" class="hv-btn" data-a="tryv" data-qbtn="tryv" data-label="Hear it"${gT.a}><span>Hear it</span></button></div>${gT.l}
              <p class="hv-hint" data-qline="tryv"></p></div></div>
          <div class="hv-card"><div class="hv-rh"><b>In your work</b><span class="hv-mut hv-sm">${plural(uses.length, 'sound')}</span><span class="hv-grow"></span>${uses.length ? '<button type="button" class="hv-lnk" data-a="yvsounds">See all in Your sounds</button>' : ''}</div>
            ${uses.length ? `<div class="hv-list">${uses.slice(0, 4).map(h => `<div class="hv-mv hv-yvu">${playBtn(h.id, `Play ${h.title || 'this sound'}`, 10, ' s')}<span class="hv-grow hv-ell">${esc(h.title || KIND[h.kind] || 'Sound')}</span><span class="hv-mut hv-sm">${esc(KIND[h.kind] || '')}</span><span class="hv-mut hv-sm hv-num">${esc(ago(h.made))}</span></div>`).join('')}</div>`
              : '<p class="hv-mut hv-sm">Nothing made with this voice yet.</p>'}</div></div>
        <div class="hv-yvdr">${v.kind === 'clone' ? `<div class="hv-yvkeep hv-yvcons"><b>Your consent is kept</b>
            ${v.consent_kept ? `<div class="hv-rh"><button type="button" class="hv-play s" data-a="yvcons" data-id="${esc(v.id)}" aria-label="Play your consent recording">${ic('play', 12)}</button><span class="hv-vt"><b>You read the line${v.lang ? ` in ${esc(lang(v.lang)?.name || v.lang)}` : ''}</b><span class="hv-num hv-sm">${esc(ago(v.consent_at || v.made))}</span></span></div>` : `<span class="hv-sm">You agreed${v.consent_at ? ' ' + esc(ago(v.consent_at)) : ''}.</span>`}
            <span class="hv-sm">Kept as proof while this voice exists. Deleting the voice deletes the recording too.</span></div>` : ''}
          <div class="hv-card"><b>About this voice</b><dl class="hv-dl">${facts.map(([k, x]) => `<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`).join('')}</dl></div>
          <div class="hv-card hv-yvacts">${acts.map(([a, t, sub, off]) => `<button type="button" class="hv-yvact${a === 'yvrm' ? ' bad' : ''}" data-a="${a}" data-id="${esc(v.id)}"${off ? ' aria-disabled="true"' : ''}><span class="hv-vt"><b>${esc(t)}</b><span class="hv-mut hv-sm">${esc(sub)}</span></span>${ic('chev', 14)}</button>`).join('')}</div></div></div></div>`;
  }
  // her recording, read by the browser once it stops: loudness, clipping and the quiet floor, in 50 ms frames
  async function yMeter(file) {
    try { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
      const ac = new AC(), buf = await ac.decodeAudioData(await file.arrayBuffer()); ac.close?.();
      const ch = buf.getChannelData(0), n = Math.max(1, Math.round(buf.sampleRate * 0.05)), rms = []; let clip = 0;
      for (let i = 0; i < ch.length; i += n) { let s = 0; const e = Math.min(ch.length, i + n); for (let j = i; j < e; j++) { const x = ch[j]; s += x * x; if (x >= 0.99 || x <= -0.99) clip++; } rms.push(Math.sqrt(s / (e - i))); }
      const sorted = [...rms].sort((a, b) => a - b), p = q => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] || 0;
      return {loud: p(0.9) >= 0.04, clip: clip / ch.length > 0.001, noise: p(0.1) > 0.02 && p(0.1) > p(0.9) * 0.35};
    } catch { return null; }
  }
  function voiceDetail() {
    const shared = UI.vtab === 'shared', v = shared ? libVoice(UI.vsel) : voice(UI.vsel);
    if (!v) return `<div class="hv-stageb">${empty('Choose a voice', 'Tap a voice to hear it and see what it is good for.')}</div>`;
    const hl = vHearLang(v), u = shared ? {n: 0} : vUse(v.id), fav = (D.favs || []).includes(v.id), inCmp = UI.cmp.includes(v.id);
    const gT = gate(shared ? 'Add it to your voices first.' : !v.ready ? (v.engine && !ready(v.engine) ? whyNot(v.engine) : 'This voice is not ready yet.') : paid(''));
    const about = v.line || `${[v.tone, v.age === 'middle' ? 'middle-aged' : v.age, v.gender].filter(Boolean).join(', ') || 'A natural'} voice${v.accent ? `, ${v.accent} accent` : ''}.${v.use ? ` Good for ${v.use.toLowerCase()}.` : ''}`;
    const all = v.any ? vEngineLangs(v) : (v.langs || []);
    return `<div class="hv-stageb hv-vd"><div class="hv-vdh">${vprint(v.id, 'xl')}<span class="hv-vt"><b class="hv-vdn">${esc(v.name)}</b>
        <span class="hv-mut hv-sm">${esc(shared ? `Shared library${v.uses ? ` · used ${num(v.uses)} times` : ''}` : [v.kind === 'hoola' ? 'Hoola voice' : 'Your voice', v.tier === 'premium' ? 'Premium' : '', v.accent].filter(Boolean).join(' · '))}</span></span>
        ${shared ? '' : `<button type="button" class="hv-ib hv-star${fav ? ' on' : ''}" data-a="vfav" data-id="${esc(v.id)}" aria-pressed="${fav}" aria-label="Favourite ${esc(v.name)}">${ic('star', 18)}</button>`}</div>
      <p class="hv-serifp">${esc(about)}</p>
      <div class="hv-card hv-sample"><div class="hv-rh"><button type="button" class="hv-play hv-vhear" data-a="hear" data-id="${esc(v.id)}" data-lang="${esc(hl)}" aria-label="Hear ${esc(v.name)}'s sample in ${esc(short(hl))}"${!shared && !v.ready ? ' disabled' : ''}>${ic('play', 12)}</button>${wave(v.id, 40, 'thin')}</div>
        ${shared ? '' : `<div class="hv-vsay"><span class="hv-mut hv-sm">In</span><button type="button" class="hv-chip" data-a="vlang" aria-haspopup="menu">${esc(short(hl))}</button><span class="hv-vline" lang="${esc(hl)}">“${esc(vSampleLine(hl))}”</span></div>`}
        <span class="hv-mut hv-sm">Hearing a voice’s sample is free.</span></div>
      ${shared ? '' : `<div class="hv-fld"><span class="hv-lab" id="hvTryL">Hear it say your words</span>
        <div class="hv-chips">${VTRY.map(([k, w]) => `<button type="button" class="hv-chip" data-a="vtryp" data-val="${esc(k)}" aria-pressed="${UI.tryText === w}">${esc(k)}</button>`).join('')}</div>
        <div class="hv-tryrow"><label class="hv-sr" for="hvTry">Your words</label><input id="hvTry" class="hv-in" maxlength="200" data-m="UI.tryText" value="${esc(UI.tryText)}" placeholder="Hello, today's special offer is…"><button type="button" class="hv-btn" data-a="tryv" data-qbtn="tryv" data-label="Hear it"${gT.a}><span>Hear it</span></button></div>${gT.l}
        <p class="hv-hint" data-qline="tryv"></p></div>`}
      <dl class="hv-dl"><dt>Speaks</dt><dd>${esc(all.length ? all.slice(0, 3).map(c => lang(c)?.name || c).join(', ') + (all.length > 3 ? ` and ${num(all.length - 3)} more` : '') : 'Every language its engine knows')}</dd>
        ${v.use ? `<dt>Best for</dt><dd>${esc(v.use)}</dd>` : ''}<dt>Engine</dt><dd>${esc(shared ? 'ElevenLabs · Premium' : `${engName(v.engine)}${v.tier === 'premium' ? ' · Premium' : ''}`)}</dd>
        ${shared ? '' : `<dt>In your work</dt><dd>${u.n ? `Used in ${plural(u.n, 'sound')}${u.last?.title ? ` · last in “${esc(u.last.title)}”` : ''}` : 'Not used yet'}</dd>`}</dl>
      <span class="hv-grow"></span>
      ${shared ? `<button type="button" class="hv-cta" data-a="libadd" data-id="${esc(v.id)}"><span>Add to my voices</span></button><p class="hv-hint c">Shared voices were offered by their owners for anyone to use.</p>`
        : `<div class="hv-vuse2"><button type="button" class="hv-cta" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}><span>Use in Speech</span></button><button type="button" class="hv-cta hv-ctam" data-a="vusein" data-id="${esc(v.id)}" aria-haspopup="menu" aria-label="Use it somewhere else"${v.ready ? '' : ' disabled'}>${ic('down', 14)}</button></div>
          <div class="hv-acts"><button type="button" class="hv-btn" data-a="vcmp" data-id="${esc(v.id)}" aria-pressed="${inCmp}">${inCmp ? 'In the comparison' : 'Compare'}</button>
            <button type="button" class="hv-btn" data-a="vlike" data-id="${esc(v.id)}">Make one like it</button></div>`}</div>`;
  }
  const VTRY = [['Ad', 'Big Diwali sale this weekend. Everything in the shop is twenty percent off.'], ['Story', 'Once upon a time, in a small village by the river, there lived an old storyteller.'],
    ['Support call', 'Thank you for calling. I am sorry for the wait. How can I help you today?'], ['News', 'Good evening. Here are the main stories of the day.']];
  // Compare: up to 4 voices, the same words, one after another; names can be hidden until she chooses
  function cmpView() {
    const ids = UI.cmp.filter(id => voice(id)), hl = UI.vlang || (S.lang !== 'auto' ? S.lang : '') || 'en', blind = UI.cmpBlind && !UI.cmpPick;
    const col = (id, i) => { const v = voice(id), name = blind ? `Voice ${'ABCD'[i]}` : v.name, chosen = UI.cmpPick === id, liked = UI.cmpLike.includes(id);
      return `<section class="hv-cmpc${chosen ? ' on' : ''}" aria-label="${esc(name)}"><div class="hv-rh">${blind ? `<span class="hv-vprint t5 l" aria-hidden="true">${'<span style="--h:10"></span>'.repeat(7)}</span>` : vprint(id, 'l')}
          <span class="hv-vt"><b class="hv-vdn s">${esc(name)}</b><span class="hv-mut hv-sm">${esc(blind ? 'Names show after you choose' : vWords(v))}</span></span>
          <button type="button" class="hv-ib" data-a="cmprm" data-id="${esc(id)}" aria-label="Take ${esc(name)} out of the comparison">${ic('x', 14)}</button></div>
        <div class="hv-card hv-sample"><div class="hv-rh"><button type="button" class="hv-play hv-vhear" data-a="cmphear" data-id="${esc(id)}" aria-label="Hear ${esc(name)}"${v.ready ? '' : ' disabled'}>${ic('play', 12)}</button>${wave(id, 28, 'thin')}</div>
          ${UI.cmpOut[id] ? '<span class="hv-mut hv-sm">Your words</span>' : `<span class="hv-mut hv-sm">The ${esc(short(hl))} sample · free</span>`}</div>
        <dl class="hv-dl">${blind ? '' : `<dt>Sounds</dt><dd>${esc(v.tone || '—')}</dd><dt>Accent</dt><dd>${esc(v.accent || '—')}</dd>`}<dt>Speaks</dt><dd>${esc(vLangs(v))}</dd><dt>Engine</dt><dd>${esc(v.tier === 'premium' ? 'Premium' : 'Standard')}</dd></dl>
        <span class="hv-grow"></span>
        <button type="button" class="hv-btn" data-a="cmplike" data-id="${esc(id)}" aria-pressed="${liked}">${liked ? 'I like this one' : 'Like it'}</button>
        <button type="button" class="hv-cta" data-a="cmppick" data-id="${esc(id)}"${v.ready ? '' : ' disabled'}><span>${chosen ? `Chosen · use ${esc(v.name)} in Speech` : `Choose ${esc(name)}`}</span></button></section>`; };
    const g = gate((UI.cmpText || '').trim() ? paid('') : 'Type the words first, or hear the free samples.');
    return `<div class="hv-doc hv-cmp"><div class="hv-cmph"><button type="button" class="hv-btn s" data-a="go" data-p="voices">${ic('back', 14)}Voice library</button><span class="hv-grow"></span>
        <button type="button" role="switch" class="hv-switchrow s" data-a="cmpblind" aria-checked="${!!UI.cmpBlind}"><span class="hv-sw${UI.cmpBlind ? ' on' : ''}" aria-hidden="true"><span></span></span><span>Listen without names</span></button></div>
      <div class="hv-cmpw"><label class="hv-fld hv-grow"><span class="hv-lab">The same words for every voice</span><textarea id="hvCmpT" class="hv-in serif" rows="2" maxlength="200" data-m="UI.cmpText" placeholder="${esc(vSampleLine(hl))}">${esc(UI.cmpText || '')}</textarea></label>
        <div class="hv-acts"><button type="button" class="hv-btn" data-a="vlang" aria-haspopup="menu">${esc(short(hl))}</button>
          <button type="button" class="hv-btn" data-a="cmpwords" data-qbtn="cmp" data-label="Say my words in each"${g.a}><span>Say my words in each</span></button>
          <button type="button" class="hv-btn dark" data-a="cmpall"${ids.length ? '' : ' disabled'}>${ic('play', 12)}Play them one after another</button></div>${g.l}<p class="hv-hint" data-qline="cmp"></p></div>
      <div class="hv-cmpg">${ids.map(col).join('')}${ids.length < 4 ? `<button type="button" class="hv-cmpadd" data-a="go" data-p="voices">${ic('plus', 18)}<b>Add a voice</b><span class="hv-mut hv-sm">Up to 4 voices, the same words</span></button>` : ''}</div></div>`;
  }
  function vPrice() {
    if (PAGE !== 'voices') return;
    if (ARG === 'compare') { const t = (UI.cmpText || '').trim(), n = UI.cmp.filter(id => voice(id)?.ready).length; if (t && n) price('cmp', {job: 'tts', chars: t.length * n, takes: 1, voice: UI.cmp[0], lang: 'auto', engine: 'auto'}); return; }
    const t = (UI.tryText || '').trim(), v = voice(UI.vsel); if (t && v) price('tryv', {job: 'tts', chars: t.length, takes: 1, voice: v.id, lang: 'auto', engine: 'auto'});
  }
  async function cmpSrc(id) {
    if (UI.cmpOut[id]) return blobUrl(`${A}/audio?id=${q(UI.cmpOut[id])}`);
    const v = voice(id); return blobUrl(`${A}/voice/preview?id=${q(id)}&lang=${q(vHearLang(v))}`);
  }
  function cmpHear(i, chain) {
    const ids = UI.cmp.filter(id => voice(id)); if (i >= ids.length) return;
    const id = ids[i], name = UI.cmpBlind && !UI.cmpPick ? `Voice ${'ABCD'[i]}` : vname(id);
    return cmpSrc(id).then(async u => { const a = $('#hvAudio'); await play('hear:' + id, u, `${name} · compare`);
      if (chain) a?.addEventListener('ended', () => cmpHear(i + 1, true), {once: true}); }).catch(e => toast(e.message, true));
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
  // ------------------------------------------------------------------ Dubbing (v0.999.148): a new dub, being made, at work ---
  const dubSt = s => s === 'ready' ? 'made' : s === 'failed' ? 'bad' : s === 'check' ? 'changed' : 'work';
  const STEPW = {heard: 'Listening', translated: 'Translating', check: 'Waiting for you', spoken: 'Speaking', mixed: 'Mixing'};
  const dubWord = l => l.status === 'failed' ? 'Failed' : l.status === 'check' ? 'Read the lines' : l.status === 'ready' ? 'Ready'
    : l.step === 'spoken' && l.total ? `${Math.round((+l.done || 0) / l.total * 100)}%` : (STEPW[l.step] || 'Waiting');
  const DSTEPS = [['heard', 'Heard'], ['translated', 'Translated'], ['check', 'Your OK'], ['spoken', 'Spoken'], ['mixed', 'Mixed']];
  const dubName = (d, sp) => (d.people || []).find(p => p.id === sp)?.name || (d.names || {})[sp] || sp || '';
  const dubBase = d => String(d.name || d.title || 'dub').replace(/\.[a-z0-9]{2,4}$/i, '');
  function dubNewView() {
    const n = UI.dubNew, ownWhy = ready('eleven') ? '' : whyNot('eleven'), lim = D.limits || {}, maxL = n.mode === 'own' ? (lim.dub_langs_own || 6) : (lim.dub_langs_matched || 4);
    if (n.langs.length > maxL) n.langs = n.langs.slice(0, maxL);
    const go_ = gate(paid(!ready('gemini') && !ready('eleven') ? 'No dubbing engine is connected on this server yet.' : n.file?.up ? 'The video is still uploading.'
      : !n.file?.file_id ? (n.file?.err || 'Add the video first.') : !n.langs.length ? 'Choose at least one language.' : (n.mode === 'own' && ownWhy) ? ownWhy : ''));
    const og = gate(ownWhy), ck = gate(n.mode === 'own' ? 'In their own voices the whole dub is made in one go, so the lines cannot wait for you.' : '');
    const sw = (k, name, note, g = {a: '', l: ''}) => `<button type="button" role="switch" class="hv-switchrow" data-a="dubsw" data-k="${k}" aria-checked="${!!n[k] && !g.a}"${g.a}><span class="hv-sw${n[k] && !g.a ? ' on' : ''}" aria-hidden="true"><span></span></span>
      <span class="hv-vt"><b>${name}</b><span class="hv-mut hv-sm">${note}</span></span></button>${g.l}`;
    return `<div class="hv-split hv-tool hv-dubnew"><section class="hv-panel wide" aria-label="What to dub">
        <div class="hv-card hv-dubsrc"><span class="hv-poster s" aria-hidden="true">${n.preview ? `<video src="${esc(n.preview)}" muted preload="metadata"></video>` : ''}</span>
          <span class="hv-vt"><b>${esc(n.file.name || 'Your video')}</b><span class="hv-sm">${n.secs ? `<span class="hv-num">${secs(n.secs)}</span> · ` : ''}the language and the people are found by Hoola</span>
            <span class="hv-sm ${n.file.err ? 'hv-bad' : n.file.file_id ? 'hv-ok' : 'hv-mut'}">${n.file.up ? 'Uploading…' : n.file.err ? esc(n.file.err) : n.file.file_id ? 'Ready to dub' : ''}</span></span>
          <button type="button" class="hv-btn s" data-a="pickfile" data-k="dub" data-accept="video/*,audio/*">Choose another</button></div>
        <div class="hv-fld"><div class="hv-rh"><b class="hv-t">Into</b><span class="hv-mut hv-sm">Up to ${maxL} languages · each one its own dub, made at the same time</span></div>
          <div class="hv-chips">${n.langs.map(c => `<button type="button" class="hv-chip on" data-a="dubrm" data-val="${esc(c)}" aria-label="Remove ${esc(langLabel(c))}">${esc(langLabel(c))}${ic('x', 12)}</button>`).join('')}
            ${n.langs.length < maxL ? `<button type="button" class="hv-chip" data-a="picklang" data-k="dubadd" data-need="dub" aria-haspopup="menu">${ic('plus', 12)}Add a language</button>` : ''}</div></div>
        <div class="hv-fld"><b class="hv-t">How they sound</b><div class="hv-ways two" role="radiogroup" aria-label="How they sound">
          <button type="button" role="radio" class="hv-way" aria-checked="${n.mode === 'own'}" data-a="seg" data-m="UI.dubNew.mode" data-val="own"${og.a}><span class="hv-wayh"><span class="hv-rad" aria-hidden="true"></span><b>Their own voices</b><span class="hv-badge">Premium</span></span>
            <span>Each person sounds like themselves, speaking the new language.</span><span>Changed lines are made again together.</span></button>
          <button type="button" role="radio" class="hv-way" aria-checked="${n.mode === 'matched'}" data-a="seg" data-m="UI.dubNew.mode" data-val="matched"><span class="hv-wayh"><span class="hv-rad" aria-hidden="true"></span><b>Matched voices</b></span>
            <span>A close Hoola voice for each person, chosen by their sound.</span><span>Any line can be changed and made again on its own.</span></button></div>${og.l}</div>
        <div class="hv-fld">${sw('keep', 'Keep the music and room sound', 'Only the voices change')}
          ${sw('check', 'Let me read the lines before they are spoken', 'The translation waits for your OK; nothing is spoken until then', ck)}
          <p class="hv-mut hv-sm">Subtitles come with every dub.</p></div>
        <div class="hv-fld"><div class="hv-rh"><b class="hv-t">Words to keep as they are</b><span class="hv-mut hv-sm">Names, brands, products: never translated</span></div>
          <div class="hv-words2">${(n.words || []).map((w, i) => `<span class="hv-wtag">${esc(w)}<button type="button" class="hv-ib xs" data-a="dubwrm" data-n="${i}" aria-label="Remove ${esc(w)}">${ic('x', 11)}</button></span>`).join('')}
            <label class="hv-sr" for="hvDubW">Add a word to keep</label><input id="hvDubW" class="hv-win" placeholder="${n.words?.length ? 'Add another…' : 'Add a word, then Enter'}" maxlength="60" data-dubword="1"></div></div>
      </section>
      <aside class="hv-stage hv-side2" aria-label="Your dub"><div class="hv-stageb"><b class="hv-t">Your dub</b>
        <div class="hv-tot2">${n.langs.length ? n.langs.map(c => `<div><span>${esc(langLabel(c))}</span><span class="hv-mut hv-sm">${n.mode === 'own' ? 'their own voices' : 'matched voices'}</span></div>`).join('') : '<p class="hv-mut hv-sm">Choose the languages on the left.</p>'}</div>
        <p class="hv-sm">${n.check && n.mode !== 'own' ? 'Hoola listens and translates first; you read the lines, then they are spoken.' : 'You can leave this page; each language is ready on its own.'}</p>
        <span class="hv-grow"></span><form data-f="dub" class="hv-form tight"><button class="hv-cta" data-qbtn="dub" data-label="Make ${n.langs.length > 1 ? n.langs.length + ' dubs' : 'the dub'}"${go_.a}><span>Make ${n.langs.length > 1 ? n.langs.length + ' dubs' : 'the dub'}</span></button>${go_.l}</form>
        <p class="hv-hint c" data-qline="dub"></p>
        <p class="hv-hint c">Only your own videos, or ones you have the right to dub. Every dub is marked as made with AI.</p>
        <button type="button" class="hv-btn s" data-a="dubcancel">${ic('back', 14)}All dubs</button></div></aside></div>`;
  }
  function dubView() {
    const d = UI.dub;
    if (!d || d.id !== ARG) return `<div class="hv-doc"><p class="hv-mut">Loading the dub…</p></div>`;
    const anyReady = (d.langs || []).some(l => l.status === 'ready');
    if (!anyReady && !UI.dubRead && ['working', 'check'].includes(d.status)) return dubMaking(d);
    if (!anyReady && d.status === 'failed') return `<div class="hv-doc"><div class="hv-rh"><b class="hv-t">${esc(dubBase(d))}</b></div>${warnNote(d.error || 'This dub could not be made.')}
      <p class="hv-mut">Nothing more is charged. Try again with a shorter video, or another language.</p><button type="button" class="hv-btn" data-a="dubopen" data-id="">${ic('back', 14)}All dubs</button></div>`;
    return dubWork(d);
  }
  function dubMaking(d) {
    const checks = (d.langs || []).filter(l => l.status === 'check');
    return `<div class="hv-split hv-tool hv-dubmk"><section class="hv-panel wide" aria-label="Each language">
        <div class="hv-vt"><h2 class="hv-h2">${(d.langs || []).length > 1 ? `${plural(d.langs.length, 'dub')} on the way` : 'Your dub is on the way'}</h2>
          <span class="hv-mut hv-sm">Each language moves on by itself. You can leave this page; come back any time.</span></div>
        ${checks.map(l => `<div class="hv-dubask"><span class="hv-sdi s" aria-hidden="true">${ic('lines', 16)}</span><span class="hv-vt"><b>The ${esc(l.name)} lines are ready to read</b>
            <span class="hv-sm">${plural((d.lines || []).length, 'line')}. Nothing is spoken until you say OK.</span></span>
          <button type="button" class="hv-btn dark" data-a="dubread" data-val="${esc(l.code)}">Read the ${esc(l.name)} lines</button></div>`).join('')}
        <ol class="hv-mklist">${(d.langs || []).map(l => { const at = DSTEPS.findIndex(s => s[0] === l.step), done = l.status === 'ready';
          return `<li class="hv-card"><div class="hv-rh"><b>${esc(l.name)}</b><span class="hv-grow"></span><span class="hv-sm hv-mkst ${dubSt(l.status)}">${esc(l.status === 'failed' ? (l.error || 'Failed') : l.status === 'check' ? 'Waiting for you'
              : l.step === 'spoken' && l.total ? `Speaking · line ${Math.min(l.total, (+l.done || 0) + 1)} of ${l.total}` : STEPW[l.step] || 'Waiting')}</span></div>
            <div class="hv-steps" role="list">${DSTEPS.map(([k, name], i) => { const skip = k === 'check' && !d.check, s = done || i < at ? 'done' : i === at ? (l.status === 'check' ? 'you' : l.status === 'failed' ? 'bad' : 'now') : '';
              return `<span role="listitem" class="hv-stp ${skip ? 'skip' : s}"><span class="hv-stpb" aria-hidden="true"></span><span>${skip ? 'No OK asked' : name}</span></span>`; }).join('')}</div></li>`; }).join('')}</ol>
        ${d.status === 'working' ? '<div class="hv-acts"><button type="button" class="hv-btn s" data-a="dubstop">Stop</button></div>' : ''}</section>
      <aside class="hv-stage hv-side2" aria-label="What Hoola heard"><div class="hv-stageb"><b class="hv-t">What Hoola heard</b>
        ${(d.lines || []).length ? `<span class="hv-mut hv-sm">${esc([d.source_lang, ((d.people || []).length === 1 ? '1 person' : `${(d.people || []).length} people`)].filter(Boolean).join(' · '))}. Name them so the lines and the voices say who is who.</span>
          ${(d.people || []).map((p, i) => `<div class="hv-namer"><span class="hv-dav t${i % 4}" aria-hidden="true">${initial(p.name)}</span><span class="hv-vt"><span class="hv-mut hv-sm">${esc(p.id)} · ${plural(p.lines, 'line')}</span>
              <label class="hv-sr" for="hvDn${i}">Name of ${esc(p.id)}</label><input id="hvDn${i}" class="hv-bkt" value="${esc(p.name)}" maxlength="40" data-dubname="${esc(p.id)}"></span>
            <button type="button" class="hv-play o" data-a="dubsp" data-val="${esc(p.id)}" aria-label="Hear ${esc(p.name)} in the video">${ic('play', 10)}</button></div>`).join('')}
          <ol class="hv-heard">${(d.lines || []).slice(0, 60).map(ln => `<li><span class="hv-num hv-mut hv-sm">${secs(ln.start)}</span><span class="hv-vt"><b class="hv-sm">${esc(dubName(d, ln.speaker))}</b><span class="serif">${esc(ln.text || '')}</span></span></li>`).join('')}</ol>`
          : '<p class="hv-mut hv-sm">Hoola is listening to the video. The people and their lines show here in a moment.</p>'}</div></aside></div>`;
  }
  function dubWork(d) {
    const tab = UI.dubTab || (d.langs || []).find(l => l.status === 'ready')?.code || d.langs?.[0]?.code || '', L = (d.langs || []).find(l => l.code === tab) || {}, DL = UI.dubLines;
    const rows = DL && DL.lang === tab ? DL.lines : null, own = d.mode === 'own', ed = !!DL?.editable, people = d.people || [];
    const order = people.map(p => p.id), total = +d.seconds || Math.max(1, ...((rows || []).map(r => +r.end || 0)));
    const lname = L.name || langLabel(tab), sel = UI.dubSel;
    const changedN = own ? (rows || []).filter(r => r.edited).length : (d.changed || {})[tab] || 0;
    const tooLong = (rows || []).filter(r => r.too_long).length;
    const pct = v => `${Math.max(0, Math.min(100, (+v || 0) / total * 100)).toFixed(2)}%`;
    const lanes = order.map((sp, i) => `<div class="hv-dlane"><span class="hv-sm t${i % 4}">${esc(dubName(d, sp))}</span><span class="hv-dtrack">${(rows || []).filter(r => r.speaker === sp).map(r =>
      `<i class="t${i % 4}${r.too_long ? ' long' : ''}${r.n === sel ? ' sel' : ''}" style="left:${pct(r.start)};width:${pct(Math.max(0.3, (+r.end || +r.start + 1) - +r.start))}"></i>`).join('')}</span></div>`).join('');
    const foot = L.status === 'check' ? `<div class="hv-dubfoot"><span class="hv-vt"><b>Nothing is spoken yet</b><span class="hv-mut hv-sm">Read the ${esc(lname)} lines, change any, then say OK.</span></span>
          <button type="button" class="hv-cta s" data-a="dubok" data-val="${esc(tab)}"><span>OK, speak the ${esc(lname)} lines</span></button></div>`
      : L.status === 'working' || L.status === 'waiting' ? `<div class="hv-dubfoot"><span class="hv-vt"><b>${esc(L.step === 'spoken' && L.total ? `Speaking line ${Math.min(L.total, (+L.done || 0) + 1)} of ${L.total}` : STEPW[L.step] || 'Working')}</b><span class="hv-mut hv-sm">The page follows it by itself.</span></span>
          <button type="button" class="hv-btn s" data-a="dubstop">Stop</button></div>`
      : own && (L.remaking || DL?.remaking) ? `<div class="hv-dubfoot"><span class="hv-vt"><b>Making the changed lines…</b><span class="hv-mut hv-sm">The page checks every 10 seconds.</span></span></div>`
      : L.status === 'ready' && ed ? (() => { const g = gate(changedN ? '' : 'Change a line first; only changed lines are spoken again.');
          return `<div class="hv-dubfoot"><span class="hv-vt"><b>${changedN ? plural(changedN, 'line') + ' changed' : 'No changes yet'}</b><span class="hv-mut hv-sm">Only those are spoken again, in the same voices</span></span>
          <button type="button" class="hv-cta s" data-a="dubremake" data-val="${esc(tab)}"${g.a}><span>Make the changes${changedN && !own ? ' · ' + cr(changedN) : ''}</span></button></div>${g.l}`; })() : '';
    return `<div class="hv-split hv-tool hv-dubwork"><section class="hv-panel wide hv-dubstage" aria-label="The video">
        <div class="hv-chips" role="tablist" aria-label="Language">${(d.langs || []).map(l => `<button type="button" role="tab" class="hv-chip hv-ltab${l.code === tab ? ' on' : ''}" data-a="dubtab" data-val="${esc(l.code)}" aria-selected="${l.code === tab}">
            <span class="hv-dot ${dubSt(l.status)}" aria-hidden="true"></span>${esc(l.name || short(l.code))}${l.status === 'ready' ? '' : `<span class="hv-sm"> · ${esc(dubWord(l))}</span>`}</button>`).join('')}
          ${!own || d.status !== 'working' ? `<button type="button" class="hv-chip dash" data-a="dubmore" aria-haspopup="menu">${ic('plus', 12)}Add a language</button>` : ''}</div>
        ${L.status === 'failed' ? warnNote(L.error || 'This language could not be made.') : ''}
        <div class="hv-dubv"><video id="hvDubMedia" playsinline controls preload="metadata" data-src="${esc(L.status === 'ready' && UI.dubHear !== 'orig' ? (L.video_id || '') : '')}"></video>
          <span class="hv-dubsub" id="hvDubSub" lang="${esc(L.status === 'ready' && UI.dubHear !== 'orig' ? tab : d.source_lang ? '' : '')}" aria-live="off"></span>
          <span class="hv-dubin">${L.status === 'ready' ? (UI.dubHear === 'orig' ? 'Playing the original' : `Playing in ${esc(lname)}`) : 'The original · not spoken yet'}</span></div>
        <div class="hv-card hv-dubplay"><div class="hv-rh"><span class="hv-mut hv-sm">${esc(own ? 'their own voices' : 'matched voices')} · ${d.keep_sound === false ? 'the voices only' : 'the music and room sound stay under the new voices'}</span><span class="hv-grow"></span>
            ${L.status === 'ready' ? seg('UI.dubHear', [['dub', 'The dub'], ['orig', 'The original'], ['both', 'Both']], UI.dubHear || 'dub', null, 'Hear') : ''}</div>
          <div class="hv-dlanes" aria-hidden="true"><div class="hv-dlane"><span class="hv-sm">Original</span><span class="hv-dtrack o">${(d.lines || []).map(ln => `<i style="left:${pct(ln.start)};width:${pct(Math.max(0.3, (+ln.end || +ln.start + 1) - +ln.start))}"></i>`).join('')}</span></div>
            ${lanes}<span class="hv-dhead" id="hvDubHead"></span></div></div></section>
      <aside class="hv-stage hv-side2 hv-dublines" aria-label="The lines"><div class="hv-rh hv-dlh"><b class="hv-t">Lines in ${esc(lname)}</b><span class="hv-mut hv-sm">${rows ? plural(rows.length, 'line') + (tooLong ? ` · ${tooLong} too long` : '') : ''}</span><span class="hv-grow"></span>
          ${!own ? `<button type="button" class="hv-btn s" data-a="sdopen" data-k="dkeep" aria-haspopup="dialog">Words to keep${(d.keep || []).length ? ` · ${d.keep.length}` : ''}</button>` : ''}</div>
        ${DL && DL.lang === tab && !ed && DL.why ? `<p class="hv-note">${esc(scrub(DL.why))}</p>` : ''}
        <ol class="hv-dlist">${rows == null ? '<li class="hv-mut">Loading the lines…</li>' : rows.length ? rows.map(r => { const on = r.n === sel, sp = Math.max(0, order.indexOf(r.speaker));
          return `<li class="hv-dline${on ? ' on' : ''}${r.too_long ? ' long' : ''}" data-dn="${r.n}"><button type="button" class="hv-dlb" data-a="dubsel" data-n="${r.n}" aria-expanded="${on}">
              <span class="hv-num hv-mut hv-sm">${secs(r.start)}</span><span class="hv-vt"><span class="hv-dsrc"><b class="t${sp % 4}">${esc(r.name || dubName(d, r.speaker))}</b> <span class="hv-mut">${esc(r.src || '')}</span></span>
              <span class="hv-ddst serif" lang="${esc(tab)}">${esc(r.dst || '')}</span>
              <span class="hv-dfit">${r.fit ? `<span class="hv-fitb" aria-hidden="true"><span class="${r.too_long ? 'long' : ''}" style="width:${Math.min(100, r.fit)}%"></span></span><span class="hv-num hv-sm${r.too_long ? ' hv-warn' : ' hv-mut'}">${r.fit}% of their time${r.too_long ? ' · too long' : ''}</span>` : ''}
                ${r.edited ? '<span class="hv-sm hv-warn">Changed</span>' : ''}${(r.kept_missing || []).length ? `<span class="hv-sm hv-warn">“${esc(r.kept_missing[0])}” is missing</span>` : ''}${r.pace > 1 ? '<span class="hv-sm hv-mut">Read faster</span>' : ''}</span></span></button>
            ${on ? `<div class="hv-dedit">${ed ? `<label class="hv-sr" for="hvDl${r.n}">Line ${r.n + 1} in ${esc(lname)}</label><textarea id="hvDl${r.n}" class="hv-in serif" rows="2" lang="${esc(tab)}" data-dubline="${r.n}">${esc(r.dst || '')}</textarea>` : ''}
              <div class="hv-acts wrap">${L.status === 'ready' ? `<button type="button" class="hv-btn s" data-a="dubhearl" data-n="${r.n}">${ic('play', 11)}Hear it</button>` : ''}
                ${ed && !own ? `<button type="button" class="hv-btn s" data-a="dubshort" data-n="${r.n}">Shorten it</button>
                  <button type="button" class="hv-btn s" data-a="dubfast" data-n="${r.n}" aria-pressed="${r.pace > 1}">${r.pace > 1 ? 'Read at the normal pace' : 'Read it a little faster'}</button>
                  ${order.length > 1 ? `<button type="button" class="hv-btn s" data-a="dubwho" data-n="${r.n}" aria-haspopup="menu">Who says it</button>` : ''}` : ''}
                ${UI.dubUndo?.n === r.n ? `<button type="button" class="hv-btn s" data-a="dubundo">Undo</button>` : ''}</div>
              ${r.too_long ? `<p class="hv-why">Their line lasts ${(+r.room || Math.max(0, (+r.end || 0) - (+r.start || 0))).toFixed(1)} s; this one would not fit. Shorten the words, or it is read faster to fit.</p>` : ''}</div>` : ''}</li>`; }).join('')
          : `<li class="hv-mut">${L.status === 'ready' || L.status === 'check' ? 'No lines were found.' : 'The lines show when the speech is heard.'}</li>`}</ol>
        ${foot}</aside></div>`;
  }
  function dubTools() {
    const t = $('#hvTopR'); if (!t) return;
    if (!ARG) { t.innerHTML = UI.dubNew.file ? '' : `<button type="button" class="hv-btn s dark" data-a="pickfile" data-k="dub" data-accept="video/*,audio/*" aria-label="New dub">${ic('plus', 14)}<span class="hv-tlab">New dub</span></button>`; return; }
    const d = UI.dub; if (!d || d.id !== ARG) { t.innerHTML = ''; return; }
    const anyReady = (d.langs || []).some(l => l.status === 'ready');
    t.innerHTML = `${(d.people || []).length ? `<button type="button" class="hv-btn s" data-a="sdopen" data-k="dvoices" aria-haspopup="dialog" aria-label="Voices">${ic('dialog', 14)}<span class="hv-tlab">Voices</span></button>` : ''}
      ${anyReady ? `<button type="button" class="hv-btn s dark" data-a="sdopen" data-k="ddl" aria-haspopup="dialog" aria-label="Download">${ic('dl', 14)}<span class="hv-tlab">Download</span></button>` : ''}
      <button type="button" class="hv-ib" data-a="dubmenu" aria-label="More for this dub" aria-haspopup="menu">${ic('more', 16)}</button>`;
  }
  function dvVoices() {
    const d = UI.dub || {}, own = d.mode === 'own';
    return `<div class="hv-vph"><span class="hv-vt"><h2 class="hv-t" id="hvSdH">Voices</h2><span class="hv-mut hv-sm">Who speaks in the video, and how they sound in every language of this dub.</span></span>
        <button type="button" class="hv-ib" data-a="sdclose" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hv-sdb">${(d.people || []).map((p, i) => `<div class="hv-person">
          <span class="hv-dav l t${i % 4}" aria-hidden="true">${initial(p.name)}</span>
          <span class="hv-vt"><span><label class="hv-sr" for="hvDvn${i}">Name of ${esc(p.id)}</label><input id="hvDvn${i}" class="hv-bkt w" value="${esc(p.name)}" maxlength="40" data-dubname="${esc(p.id)}"> <span class="hv-mut hv-sm">${plural(p.lines, 'line')} · ${secs(p.seconds)} of speech</span></span><span class="hv-pq serif">${esc(p.quote ? '“' + p.quote + '”' : '')}</span></span>
          <button type="button" class="hv-play o" data-a="dubsp" data-val="${esc(p.id)}" aria-label="Hear ${esc(p.name)} in the original">${ic('play', 11)}</button>
          ${own ? `<span class="hv-vpick off"><span class="hv-dav s" aria-hidden="true">${initial(p.name)}</span><span>Their own voice</span></span>`
            : `<button type="button" class="hv-vpick" data-a="dubvoice" data-k="${esc(p.id)}" aria-haspopup="menu" aria-label="Voice for ${esc(p.name)}: ${esc(p.voice || 'Hoola picks')}"><span class="hv-dav s" aria-hidden="true">${initial(p.voice || '?')}</span><span>${esc(p.voice || 'Hoola picks')}</span>${ic('down', 12)}</button>`}</div>`).join('')}
        <p class="hv-note">${own ? 'Their own voices are made from the video itself. A changed line is made again together with the other changed lines.' : 'A matched voice is a Hoola voice close to how they sound, the same in every language. Choose another and that person’s lines are marked changed; Make the changes speaks only those.'}</p></div>
      <div class="hv-vpf"><span class="hv-mut hv-sm">Names are saved as you type them.</span><span class="hv-grow"></span><button type="button" class="hv-cta s" data-a="sdclose">Done</button></div>`;
  }
  const DLKINDS = [['video', 'The video with the dub', 'MP4, the same picture with the new voices', 24000],
    ['subbed', 'The video with the subtitles on it', 'The words shown on the picture, in the same language', 24000],
    ['sound', 'The sound only', 'MP3, for a podcast or a reel you edit yourself', 2000],
    ['voices', 'Each voice on its own track', 'A zip: each dubbed voice, the full length, and the original sound', 6000],
    ['subs', 'Subtitles only', 'SRT and VTT, timed to the dub', 0]];
  function dvDownload() {
    const d = UI.dub || {}, x = UI.dubDl, own = d.mode === 'own';
    const ready_ = (d.langs || []).filter(l => l.status === 'ready');
    if (!Object.keys(x.on).length && ready_.length) x.on[UI.dubTab && ready_.some(l => l.code === UI.dubTab) ? UI.dubTab : ready_[0].code] = true;
    const n = ready_.filter(l => x.on[l.code]).length, kind = DLKINDS.find(k => k[0] === x.what) || DLKINDS[0];
    const no = own && x.what === 'voices' ? 'A dub in their own voices comes as one mix; each voice on its own track works for matched voices.' : !n ? 'Choose a language.' : '';
    const g = gate(no);
    return `<div class="hv-vph hv-abh"><span class="hv-poster m" aria-hidden="true"><img alt="" data-dposter="${esc(d.id)}"></span><span class="hv-vt"><span class="hv-rh"><h2 class="hv-t" id="hvSdH">Download</h2><span class="hv-grow"></span><button type="button" class="hv-ib" data-a="sdclose" aria-label="Close">${ic('x', 16)}</button></span>
        <span>${esc(dubBase(d))} · <span class="hv-num">${secs(d.seconds)}</span></span><span class="hv-mut hv-sm">Dubbed into ${esc(ready_.map(l => l.name).join(', ') || 'no language yet')}${(d.langs || []).some(l => l.status !== 'ready') ? ' · the others are still being made' : ''}</span></span></div>
      <div class="hv-sdb"><div class="hv-fld"><b>Languages</b><div class="hv-chips">${(d.langs || []).map(l => { const on = l.status === 'ready' && !!x.on[l.code];
          return `<button type="button" role="checkbox" class="hv-chip hv-ckchip${on ? ' on' : ''}" data-a="dldlang" data-val="${esc(l.code)}" aria-checked="${on}"${l.status === 'ready' ? '' : ' disabled'}><span class="hv-ckb" aria-hidden="true">${on ? ic('check', 11) : ''}</span>${esc(l.name)}${l.status === 'ready' ? '' : ` <span class="hv-sm">· ${esc(dubWord(l))}</span>`}</button>`; }).join('')}</div></div>
        <div class="hv-fld"><b>What</b><div class="hv-ways col" role="radiogroup" aria-label="What to download">${DLKINDS.map(([k, name, note, kbs]) =>
          `<button type="button" role="radio" class="hv-way" aria-checked="${x.what === k}" data-a="dldwhat" data-val="${k}"><span class="hv-rad" aria-hidden="true"></span><span class="hv-vt"><b>${name}</b><span>${note}</span></span><span class="hv-num hv-mut hv-sm">${kbs ? `about ${Math.max(1, Math.round((+d.seconds || 60) * kbs / 8e6 * 8))} MB each` : 'small'}</span></button>`).join('')}</div></div>
        <p class="hv-note">Every dubbed file says it was made with AI, in its details. Share it only where you have the right to.</p></div>
      <div class="hv-vpf"><span class="hv-mut hv-sm">${n > 1 ? 'More than one language comes as one zip, a folder per language. Free.' : 'Free: the dub is already made.'}</span><span class="hv-grow"></span>
        <button type="button" class="hv-cta s" data-a="dldgo"${g.a}><span>${n > 1 ? `Download ${n} languages` : 'Download'}</span></button></div>${g.l}`;
  }
  function dvKeep() {
    const d = UI.dub || {}, w = UI.dubKeep || [];
    return `<div class="hv-vph"><span class="hv-vt"><h2 class="hv-t" id="hvSdH">Words to keep as they are</h2><span class="hv-mut hv-sm">Names, brands and products that are never translated. Lines are checked for them: a kept word that went missing from a line is marked on it.</span></span>
        <button type="button" class="hv-ib" data-a="sdclose" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hv-sdb"><div class="hv-words2">${w.map((x, i) => `<span class="hv-wtag">${esc(x)}<button type="button" class="hv-ib xs" data-a="dkrm" data-n="${i}" aria-label="Remove ${esc(x)}">${ic('x', 11)}</button></span>`).join('')}
          <label class="hv-sr" for="hvDkW">Add a word to keep</label><input id="hvDkW" class="hv-win" maxlength="60" placeholder="Add a word, then Enter" data-dkword="1"></div>
        <p class="hv-mut hv-sm">${d.mode === 'own' ? '' : 'Languages added from now on keep these words. For lines already translated, change a line or shorten it and it is kept.'}</p></div>
      <div class="hv-vpf"><span class="hv-grow"></span><button type="button" class="hv-cta s" data-a="dksave">Save</button></div>`;
  }
  // the video beside the lines: the dub, the original, or both together; the line said shown on the picture and the lanes' playhead
  async function dubMediaSet() {
    const m = $('#hvDubMedia'); if (!m || !UI.dub) return; const d = UI.dub, L = (d.langs || []).find(l => l.code === (UI.dubTab || '')) || (d.langs || []).find(l => l.status === 'ready') || {};
    const orig = UI.dubHear === 'orig' || L.status !== 'ready';
    try { m.src = await blobUrl(orig ? `${A}/dub/${q(d.id)}/source` : `${A}/audio?id=${q(L.video_id)}`); } catch { /* the controls stay */ }
    let o = $('#hvDubOrig'); o?.pause(); o?.remove(); o = null;
    if (UI.dubHear === 'both' && L.status === 'ready') {
      o = document.createElement('audio'); o.id = 'hvDubOrig'; o.className = 'hv-sr'; o.volume = 0.35; (ROOT || document.body).appendChild(o);
      try { o.src = await blobUrl(`${A}/dub/${q(d.id)}/source`); } catch { o = null; }
      if (o) { const sync = () => { if (Math.abs(o.currentTime - m.currentTime) > 0.25) o.currentTime = m.currentTime; };
        m.addEventListener('play', () => { sync(); o.play().catch(() => {}); }); m.addEventListener('pause', () => o.pause()); m.addEventListener('seeked', sync); }
    }
    const rows = () => (UI.dubLines?.lines || []), sub = $('#hvDubSub'), head = $('#hvDubHead');
    m.addEventListener('timeupdate', () => { const t = m.currentTime, r = rows().find(x => t >= +x.start && t <= Math.max(+x.end || 0, +x.start + 1.5));
      if (sub) { const w = r ? (orig ? r.src : r.dst) : ''; if (sub.textContent !== w) sub.textContent = w || ''; sub.hidden = !w; }
      if (head) head.style.left = `calc(var(--lw) + (100% - var(--lw)) * ${Math.min(1, t / Math.max(1, +d.seconds || m.duration || 1)).toFixed(4)})`; });
  }
  function dubPosters() { for (const im of $$('img[data-dposter]')) { if (im.src) continue; blobUrl(`${A}/dub/${q(im.dataset.dposter)}/poster`).then(u => { im.src = u; im.onload = () => im.parentElement?.classList.add('img'); }, () => im.remove()); } }
  async function dubRefresh() { if (!ARG) return; await loadDub(ARG); }

  async function loadDub(id) {
    try { UI.dub = await api('GET', `${A}/dub/${q(id)}`); } catch (e) { toast(e.message, true); return; }
    if (PAGE !== 'dub' || ARG !== id) return;
    if (!UI.dubTab || !(UI.dub.langs || []).some(l => l.code === UI.dubTab)) UI.dubTab = UI.dub.langs?.[0]?.code || '';
    crumb(); draw(); dubLines(id); dubPoll(id);
  }
  async function dubLines(id) {
    const lc = UI.dubTab; if (!lc) return;
    try { const r = await api('GET', `${A}/dub/${q(id)}/lines?lang=${q(lc)}`); UI.dubLines = {lang: lc, lines: r.lines || [], editable: r.editable, why: r.why, credits_redo: r.credits_redo, own: !!r.own, note: r.note || '', remaking: !!r.remaking}; }
    catch { UI.dubLines = {lang: lc, lines: (UI.dub.lines || []).map((l, i) => ({n: i + 1, start: l.start, end: l.end, speaker: l.speaker, src: l.text, dst: (l.tr || {})[lc] || ''})), editable: false, why: ''}; }
    if (PAGE === 'dub' && ARG === id) { const keep = ROOT.querySelector(':focus')?.id; draw(); $$('.hv-lt').forEach(t => { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }); if (keep) $('#' + keep)?.focus(); }
  }
  async function dubMedia() { const m = $('#hvDubMedia'); if (!m) return; try { m.src = await blobUrl(`${A}/audio?id=${q(m.dataset.src)}`); } catch { /* the controls stay, the file comes when ready */ } }
  function dubPoll(id) { clearTimeout(dubPoll.t); const remake = (UI.dub?.langs || []).some(l => l.remaking);
    if (UI.dub?.status !== 'working' && !remake) return;
    dubPoll.t = setTimeout(() => { if (PAGE === 'dub' && ARG === id && ROOT && !ROOT.hidden) { if (remake) URLS.clear(); loadDub(id); } }, remake ? 10000 : 3000); }

  // ------------------------------------------------------------------ Voice changer (v0.999.159, design canvas claude.ai/artifact/HGbVJ4bghAiMFg9QyFCh2P)
  // her recording -> the part she marks -> a voice on ElevenLabs -> Before / After on one timeline; up to three voices
  // at once; every change kept as a pair, her own recording beside it for 30 days so it can be heard and changed again.
  const CHG = {a: null, b: null, raf: 0, on: false};
  const chgVoices = () => D.voices.filter(v => v.engine === 'eleven');
  const chgHist = () => D.history.filter(h => h.kind === 'change');
  const chgKind = v => v.kind === 'clone' ? 'Your voice' : v.kind === 'shared' ? 'From the shared library' : v.kind === 'hoola' ? 'Premium voice' : 'Your voice';
  const chgLine = v => [chgKind(v), v.tone ? v.tone.toLowerCase() : '', (v.langs || []).slice(0, 2).map(c => lang(c)?.name || c).join(' and ')].filter(Boolean).join(' · ');
  const first = n => String(n || 'the voice').split(/[\s,]+/)[0];
  const chgLen = () => { const c = UI.chg; if (!c.file) return 0; const e = c.end || c.secs || 0; return Math.max(0, e - (c.start || 0)); };
  const chgMarked = () => { const c = UI.chg; return !!c.file && c.secs > 0 && (c.start > 0.05 || (c.end && c.end < c.secs - 0.05)); };
  async function chgPeaks(file, n = 120) {      // her recording's own shape, read by the browser (nothing leaves it)
    try { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
      const ac = new AC(), buf = await ac.decodeAudioData(await file.arrayBuffer()); ac.close?.();
      const ch = buf.getChannelData(0), step = Math.max(1, Math.floor(ch.length / n)), out = [];
      for (let i = 0; i < n; i++) { let m = 0; for (let j = i * step, e = Math.min(ch.length, j + step); j < e; j += 8) m = Math.max(m, Math.abs(ch[j])); out.push(m); }
      const top = Math.max(0.05, ...out); return out.map(x => x / top);
    } catch { return null; }
  }
  const chgBars = (peaks, seed, n = 90) => (peaks && peaks.length ? peaks : null) ? peaks.map(p => `<i style="height:${Math.round(4 + p * 40)}px"></i>`).join('')
    : (() => { let h = [...String(seed || 'x')].reduce((a, ch) => (a * 33 + ch.charCodeAt(0)) >>> 0, 5); const o = [];
      for (let i = 0; i < n; i++) { h = (h * 1103515245 + 12345) >>> 0; o.push(`<i style="height:${6 + (h % 34)}px"></i>`); } return o.join(''); })();
  function chgChecks(sl) {
    if (!sl) return [];
    const m = sl.meter, out = [];
    if (m) out.push([m.loud, m.loud ? 'Clear and loud enough' : 'Quiet: the change will be quiet too'], [!m.noise, m.noise ? 'Room noise: keep Remove room noise ticked' : 'Little room noise'],
      [!m.clip, m.clip ? 'Too loud in places' : 'Not too loud']);
    out.push([!!sl.file_id, sl.file_id ? 'Uploaded' : sl.err ? 'The recording did not upload' : 'Uploading…']);
    return out;
  }
  function chgTop(title, sub) {
    const n = chgHist().length;
    return `<div class="hv-chgtop"><span class="hv-vt"><b class="hv-chgt">${esc(title)}</b><span class="hv-mut hv-sm">${esc(sub)}</span></span><span class="hv-grow"></span>
      ${UI.chg.view ? `<button type="button" class="hv-btn" data-a="chgview" data-val="">${ic('back', 14)}<span>Voice changer</span></button>` : ''}
      ${UI.chg.view !== 'list' ? `<button type="button" class="hv-btn" data-a="chgview" data-val="list"${n ? '' : ' aria-describedby="hvChgNone"'}>Your changes <span class="hv-num hv-mut">${num(n)}</span></button>${n ? '' : '<span class="hv-sr" id="hvChgNone">None yet</span>'}` : ''}</div>`;
  }
  // the part of the page where her recording lives: the microphone, then her recording with the part she marks
  function chgRec() {
    const c = UI.chg, f = c.file, recOn = !!REC.chg;
    if (!f || recOn) return `<div class="hv-card hv-chgrec"><div class="hv-yvmic"><button type="button" class="hv-recb xl${recOn ? ' on' : ''}" data-a="${recOn ? 'recstop' : 'rec'}" data-k="chg" style="--p:0" aria-label="${recOn ? 'Stop recording' : 'Start recording'}">${recOn ? '<span class="hv-sq"></span>' : ic('mic', 26)}</button>
        <span class="hv-vt"><b>${recOn ? 'Listening… say it the way you want it to sound' : 'Say it your way'}</b><span class="hv-mut hv-num" data-rect="chg">${recOn ? '0:00 of 5:00' : 'Tap the mic and speak, up to 5 minutes'}</span>
          <span class="hv-yvlvl" aria-hidden="true"><span data-lvl="chg"></span></span></span></div>
      ${recOn ? '' : `<span class="hv-mut hv-sm">or <button type="button" class="hv-lnk" data-a="pickfile" data-k="chg" data-accept="audio/*,video/*">${ic('upload', 13)}choose a recording or a video</button> · up to 5 minutes, 50 MB</span>
      <ul class="hv-chgtips"><li><b>A quiet room.</b> Noise left over can be removed.</li><li><b>Only you speaking.</b> Two people become one voice.</li><li><b>Say it with feeling.</b> The new voice copies your timing, pauses and laughs.</li></ul>`}</div>`;
    const s = c.secs || 0, a = c.start || 0, e = c.end || s, pa = s ? a / s : 0, pb = s ? e / s : 1, checks = chgChecks(f);
    return `<div class="hv-card hv-chgrec"><div class="hv-rh"><b>Your recording</b><span class="hv-mut hv-sm hv-ell">${esc([f.name, s ? secs(s) : '', f.up ? 'uploading…' : f.err || ''].filter(Boolean).join(' · '))}</span><span class="hv-grow"></span>
        <button type="button" class="hv-lnk" data-a="rec" data-k="chg">Record again</button><button type="button" class="hv-lnk" data-a="pickfile" data-k="chg" data-accept="audio/*,video/*">Choose another</button></div>
      <div class="hv-chgwave" data-trimwave style="--chga:${pa.toFixed(4)};--chgb:${pb.toFixed(4)}" aria-hidden="true">${chgBars(f.peaks, f.name)}<span class="hv-chgsel"></span></div>
      ${s ? `<div class="hv-chgtrim"><div class="hv-fld"><label class="hv-lab" for="hvChgA">Start</label><input id="hvChgA" type="range" min="0" max="${s.toFixed(1)}" step="0.1" value="${a.toFixed(1)}" data-trim="start"></div>
        <div class="hv-fld"><label class="hv-lab" for="hvChgB">End</label><input id="hvChgB" type="range" min="0" max="${s.toFixed(1)}" step="0.1" value="${e.toFixed(1)}" data-trim="end"></div></div>` : ''}
      <div class="hv-rh"><button type="button" class="hv-play" data-a="chgpart" aria-label="Play the part you keep"${f.url ? '' : ' disabled aria-describedby="hvChgNp"'}>${ic('play', 12)}</button>
        <span class="hv-num" data-trimt>${secs(a)} – ${secs(e)}</span><span class="hv-mut hv-sm" data-triml>${chgMarked() ? `Only this part is changed · ${secs(e - a)}` : 'All of it is changed'}</span><span class="hv-grow"></span>
        ${chgMarked() ? '<button type="button" class="hv-lnk" data-a="chgall">Use all of it</button>' : ''}</div>${f.url ? '' : '<span class="hv-sr" id="hvChgNp">This recording cannot be played in this browser</span>'}
      ${checks.length ? `<ul class="hv-checks hv-chgchk">${checks.map(([ok, x]) => `<li class="${ok ? 'ok' : 'warn'}">${ic(ok ? 'check' : 'warn', 14)}${esc(x)}</li>`).join('')}</ul>` : ''}</div>`;
  }
  function chgInto(id, a = 'chgpick', i = '') {
    const v = voice(id);
    return `<button type="button" class="hv-mv hv-yvbase hv-chginto" data-a="${a}"${i !== '' ? ` data-i="${i}"` : ''} aria-haspopup="menu">${v ? vprint(v.id, 'm') : '<span class="hv-vprint m t0" aria-hidden="true"></span>'}
      <span class="hv-vt"><b>${esc(v ? v.name : 'Choose a voice')}</b><span class="hv-mut hv-sm">${esc(v ? chgLine(v) : 'Premium voices, your voices on ElevenLabs and voices from the shared library')}</span></span><span class="hv-lnk">${v ? 'Change' : 'Choose'}</span></button>`;
  }
  // Before (her recording) and After (the new voice) on one timeline; one play button, Before / After switches at the same moment
  function chgHear(h) {
    const c = UI.chg, v = h ? voice(h.voice) : voice(c.voice), name = h ? h.voice_name || v?.name || 'New voice' : v?.name || 'New voice';
    const srcKept = h ? !!h.src || (c.fileFor === h.id && !!c.file?.url) : !!c.file;
    const lane = (k, who, bars, on, note) => `<div class="hv-chglane${on ? ' on' : ''} l-${k}"><span class="hv-vt"><b class="hv-sm">${k === 'before' ? 'Before' : 'After'}</b><span class="hv-mut hv-sm hv-ell">${esc(who)}</span></span>
      <span class="hv-chgw${note ? ' empty' : ''}">${note ? `<span class="hv-chgnote">${esc(note)}</span>` : `${bars}<span class="hv-chgph" data-ph></span>`}</span></div>`;
    const bPeaks = c.file?.peaks && (!h || c.fileFor === h.id) ? c.file.peaks.slice(Math.floor((c.start / (c.secs || 1)) * c.file.peaks.length), Math.ceil(((c.end || c.secs) / (c.secs || 1)) * c.file.peaks.length) || undefined) : null;
    return `<div class="hv-rh hv-chgh"><b class="hv-chgt2">Hear the difference</b><span class="hv-mut hv-sm">Same words, same timing</span><span class="hv-grow"></span>
        ${h ? `<div class="hv-seg" role="radiogroup" aria-label="Hear">${[['before', 'Before'], ['after', 'After']].map(([k, l]) => { const dis = k === 'before' && !srcKept;
          return `<button type="button" role="radio" aria-checked="${c.hear === k && !dis}" data-a="chghear" data-val="${k}"${dis ? ' disabled aria-describedby="hvChgNs"' : ''}>${l}</button>`; }).join('')}</div>${srcKept ? '' : '<span class="hv-sr" id="hvChgNs">Your own recording is no longer kept</span>'}` : ''}</div>
      <div class="hv-card hv-chgab">
        ${lane('before', 'You', chgBars(bPeaks, (h?.id || 'rec') + 'src', 70), c.hear === 'before', !srcKept ? (h ? 'Your own recording is no longer kept' : 'Record or choose a recording') : '')}
        ${lane('after', name, chgBars(null, h?.id || 'none', 70), c.hear !== 'before', h ? '' : 'Made when you tap Change it')}
        ${h ? `<div class="hv-rh hv-chgpl"><button type="button" class="hv-play l" data-a="chgplay" aria-label="${CHG.on ? 'Pause' : 'Play'} before and after">${ic(CHG.on ? 'pause' : 'play', 14)}</button>
          <span class="hv-num" data-chgt>0:00 / ${secs(h.seconds || 0)}</span><span class="hv-mut hv-sm">${srcKept ? 'Tap Before or After while it plays to switch at the same moment.' : 'Only the new voice can be played.'}</span></div>` : ''}</div>`;
  }
  function chgMain() {
    const c = UI.chg, f = c.file, into = voice(c.voice), h = c.out && D.history.find(x => x.id === c.out.id) || c.out;
    const step = !f?.file_id ? 0 : !into ? 1 : 2;
    const g = gate(paid(!into ? 'Choose the voice to change into.' : !f?.file_id ? (f?.up ? 'The recording is still uploading.' : f?.err ? 'The recording did not upload. Record again or choose another.' : 'Record or choose a recording first.') : ''));
    const steps = ['Your recording', 'Into a voice', 'Change it'];
    const recent = chgHist().filter(x => x.id !== h?.id).slice(0, 3);
    return `<div class="hv-doc hv-chg">${chgTop('Voice changer', 'Say it your way. It comes back in another voice, with your timing and feeling.')}
      <div class="hv-chggrid"><section class="hv-chgl" aria-label="What to change">
        <ol class="hv-yvsteps" aria-label="Steps">${steps.map((x, i) => `<li class="${i < step ? 'done' : i === step ? 'now' : ''}"${i === step ? ' aria-current="step"' : ''}><span class="hv-num">${i < step ? ic('check', 12) : i + 1}</span>${esc(x)}</li>`).join('')}</ol>
        ${chgRec()}
        <div class="hv-fld"><span class="hv-lab">Into</span>${chgInto(c.voice)}</div>
        ${check('UI.chg.denoise', 'Remove room noise first <span class="hv-mut hv-sm">fans, traffic, echo</span>', c.denoise)}
        <div class="hv-chgsl"><div class="hv-fld"><label class="hv-lab" for="hvChgC">How close to ${esc(first(into?.name))}</label><input id="hvChgC" type="range" min="0" max="100" step="5" value="${c.close}" data-m="UI.chg.close" data-t="num"><span class="hv-ends hv-sm hv-mut"><span>More of you</span><span>All ${esc(first(into?.name))}</span></span></div>
          <div class="hv-fld"><label class="hv-lab" for="hvChgF">Keep my feeling</label><input id="hvChgF" type="range" min="0" max="100" step="5" value="${c.feel}" data-m="UI.chg.feel" data-t="num"><span class="hv-ends hv-sm hv-mut"><span>Even</span><span>Every rise and laugh</span></span></div></div>
        <div class="hv-chgcta"><button type="button" class="hv-cta" data-a="chgmake" data-qbtn="chg" data-label="Change it"${g.a}><span>Change it</span></button>${g.l}<p class="hv-hint c" data-qline="chg"></p></div>
      </section>
      <section class="hv-chgr" aria-label="Before and after">
        ${chgHear(h)}
        ${h ? `<div class="hv-acts"><button type="button" class="hv-cta s" data-a="dlmenu" data-id="${esc(h.id)}" aria-haspopup="menu"><span>Download</span>${ic('down', 12)}</button>
          <button type="button" class="hv-btn" data-a="chgview" data-val="compare">Try it in other voices</button>
          <button type="button" class="hv-btn" data-a="chganother" data-id="${esc(h.id)}" aria-haspopup="menu"${h.src ? '' : ' disabled aria-describedby="hvChgNs2"'}>Into another voice</button>${h.src ? '' : '<span class="hv-sr" id="hvChgNs2">Your own recording is no longer kept</span>'}
          <span class="hv-mut hv-sm">Kept in Your sounds · ${esc(ago(h.made))}</span></div>` : ''}
        <p class="hv-note">Only the voice changes: your words, pauses and laughs stay. Change only your own voice, or a voice you have the right to use. Every changed sound carries the AI mark, and your own recording is kept beside it for 30 days.</p>
        ${recent.length ? `<div class="hv-chgrecent"><div class="hv-rh"><b>Recent changes</b><button type="button" class="hv-lnk" data-a="chgview" data-val="list">See all</button></div>
          ${recent.map(x => `<div class="hv-chgrow">${playBtn(x.id, `Play ${x.title || 'change'}`, 11, ' s')}<button type="button" class="hv-chgrt" data-a="chgopen" data-id="${esc(x.id)}">${esc(x.title || 'Change')}</button><span class="hv-mut hv-sm hv-ell">${esc(x.voice_name || '')}</span><span class="hv-num hv-mut hv-sm">${x.seconds ? secs(x.seconds) : ''}</span></div>`).join('')}</div>` : ''}
      </section></div></div>`;
  }
  // the same recording in up to three voices, each changed and priced on its own; she picks one
  function chgCompare() {
    const c = UI.chg, src = c.file?.file_id ? 'file' : c.out?.src ? 'kept' : '', picked = c.cmp.filter(Boolean), res = c.cmpOut;
    const len = src === 'file' ? chgLen() : (c.out?.seconds || 0);
    const g = gate(paid(!src ? 'Record or choose a recording first.' : !picked.length ? 'Choose at least one voice.' : ''));
    const slot = (vid, i) => { const v = voice(vid), it = res?.items?.find(x => x.voice === vid), fl = res?.failed?.find(x => x.voice === vid), on = it && c.cmpPick === it.id;
      return `<article class="hv-card hv-chgslot${on ? ' on' : ''}">${chgInto(vid, res ? 'chgnone' : 'chgslot', i)}
        <span class="hv-chgw s${it ? '' : ' dim'}" aria-hidden="true">${chgBars(null, it?.id || 'none' + i, 40)}</span>
        <div class="hv-rh">${it ? playBtn(it.id, `Play in ${v?.name || 'this voice'}`, 12) : ''}<span class="hv-mut hv-sm">${it ? `${secs(it.seconds || 0)} · ready` : fl ? esc(scrub(fl.why)) : v ? 'Made when you tap Change' : 'Choose a voice for this place'}</span></div>
        ${it ? `<button type="button" class="hv-btn${on ? ' on' : ''}" data-a="chgcpick" data-id="${esc(it.id)}" aria-pressed="${!!on}">${on ? 'Chosen' : 'Choose this one'}</button>` : ''}</article>`; };
    return `<div class="hv-doc hv-chg">${chgTop('Try it in other voices', 'The same recording, up to three voices. Each voice is changed and priced on its own.')}
      <div class="hv-card hv-chgab cmp"><div class="hv-chglane l-before"><span class="hv-vt"><b class="hv-sm">Before</b><span class="hv-mut hv-sm">${esc(src === 'file' ? `Your recording · ${secs(len)}` : src ? 'Your recording, kept' : 'No recording yet')}</span></span><span class="hv-chgw">${chgBars(null, 'cmpsrc', 110)}</span></div></div>
      <div class="hv-chgslots">${[0, 1, 2].map(i => slot(c.cmp[i], i)).join('')}</div>
      <div class="hv-chgcta row">${res ? `<button type="button" class="hv-cta" data-a="chggo"${c.cmpPick ? '' : ' disabled aria-describedby="hvChgPk"'}><span>Go on with ${esc(D.history.find(x => x.id === c.cmpPick)?.voice_name || 'the one you choose')}</span></button>${c.cmpPick ? '' : '<p class="hv-why" id="hvChgPk">Choose one of the voices first.</p>'}
          ${check('UI.chg.rm', 'Remove the others from Your sounds', c.rm)}<button type="button" class="hv-btn" data-a="chgcagain">Try other voices</button>`
        : `<button type="button" class="hv-cta" data-a="chgmany" data-qbtn="chgn" data-label="Change it in ${picked.length || 'the'} voice${picked.length === 1 ? '' : 's'}"${g.a}><span>Change it</span></button>${g.l}<p class="hv-hint" data-qline="chgn"></p>`}</div></div>`;
  }
  function chgList() {
    const all = chgHist(), names = [...new Set(all.map(h => h.voice_name).filter(Boolean))].slice(0, 6), fl = UI.chg.filt, list = fl ? all.filter(h => h.voice_name === fl) : all;
    const card = h => { const meta = [h.trim ? 'A part of the recording' : '', h.denoise ? 'Room noise removed' : '', h.src ? '' : 'Your recording no longer kept'].filter(Boolean).join(' · ');
      return `<article class="hv-card hv-chgc"><div class="hv-rh"><b class="hv-ell">${esc(h.title || 'Change')}</b><span class="hv-grow"></span><span class="hv-mut hv-sm">${esc(ago(h.made))}</span>
          <button type="button" class="hv-ib s" data-a="sndmenu" data-id="${esc(h.id)}" aria-label="More for ${esc(h.title || 'this change')}: download, remove">${ic('more')}</button></div>
        <div class="hv-chgpair"><span class="hv-sm">You</span>${h.src ? `<button type="button" class="hv-play s" data-a="chgsrc" data-id="${esc(h.id)}" aria-label="Play your own recording">${ic('play', 11)}</button>` : '<span class="hv-play s off" aria-hidden="true"></span>'}<span class="hv-chgw s dim" aria-hidden="true">${chgBars(null, h.id + 'src', 48)}</span>
          <b class="hv-sm hv-ell" title="${esc(h.voice_name || '')}">${esc(h.voice_name || 'New voice')}</b>${playBtn(h.id, `Play in ${h.voice_name || 'the new voice'}`, 11, ' s')}<span class="hv-chgw s" aria-hidden="true">${chgBars(null, h.id, 48)}</span></div>
        <div class="hv-rh"><span class="hv-num hv-mut hv-sm">${h.seconds ? secs(h.seconds) : ''}</span><span class="hv-mut hv-sm hv-ell">${esc(meta)}</span><span class="hv-grow"></span>
          <button type="button" class="hv-btn s" data-a="chgopen" data-id="${esc(h.id)}">Open</button>
          ${h.src ? `<button type="button" class="hv-btn s" data-a="chganother" data-id="${esc(h.id)}" aria-haspopup="menu">Into another voice</button>` : ''}</div></article>`; };
    return `<div class="hv-doc hv-chg">${chgTop('Your changes', `${plural(all.length, 'changed recording')}`)}
      ${all.length ? `<div class="hv-chips" role="radiogroup" aria-label="Show">${[['', 'All'], ...names.map(n => [n, n])].map(([k, l]) => `<button type="button" class="hv-chip" role="radio" aria-checked="${fl === k}" data-a="chgfilt" data-val="${esc(k)}">${esc(l)}</button>`).join('')}</div>
        <div class="hv-chglist">${list.map(card).join('')}</div>
        <p class="hv-mut hv-sm">Your own recording is kept beside each change for 30 days so you can hear it and change it again. The changed sound stays until you remove it.</p>`
        : empty('No changes yet', 'Record something and change it into another voice.', '<button type="button" class="hv-cta s" data-a="chgview" data-val=""><span>Change a recording</span></button>')}</div>`;
  }
  // when the changer cannot run: the engine, a voice to change into, credits - each said plainly with what to do
  function chgNot() {
    const cards = [];
    if (!ready('eleven')) cards.push(['warn', 'Not connected yet', 'The voice engine is not on this server', `The voice changer runs on ElevenLabs. ${whyNot('eleven')} Until the owner of this Hoola server adds its key, nothing on this page can run, and nothing is charged.`, '', 'For the owner: add the key in the server settings, never in a chat.']);
    if (!chgVoices().length) cards.push(['pri', 'No voice to change into', 'Add a Premium voice first', 'Only voices on ElevenLabs can be used here: the Premium voices, voices you add from the shared library, and your own voice if you recorded it there.', '<button type="button" class="hv-cta s" data-a="go" data-p="voices"><span>Open the Voice library</span></button>', 'Takes a minute. The voice stays in your list.']);
    if (broke()) cards.push(['', 'No credits left', 'Add credits to change a recording', 'A change is priced by how long the recording is. You always see the price on the button before you tap.', `<a class="hv-btn" href="${esc(D.credits_page || '/console/?v=credits')}">Get credits</a>`, 'Your recordings and changes stay as they are.']);
    return `<div class="hv-doc hv-chg hv-chgnot"><div class="hv-chghero"><span class="hv-chgfig" aria-hidden="true">${vprint('you', 'l')}${ic('chev', 18)}${vprint('arjun', 'l')}</span>
        <h2 class="hv-yvtitle">Say it once. Hear it in another voice.</h2>
        <p class="hv-yvlead">You record the words with your own timing and feeling, and the voice changer speaks them again in the voice you choose. Good for ads, reels, phone menus and stories.</p></div>
      <div class="hv-chgnots">${cards.map(([t, tag, h, b, btn, foot]) => `<article class="hv-card hv-chgnc${t ? ' ' + t : ''}"><span class="hv-badge">${esc(tag)}</span><b>${esc(h)}</b><span class="hv-sm">${esc(scrub(b))}</span>${btn}<span class="hv-mut hv-sm">${esc(foot)}</span></article>`).join('')}</div>
      <p class="hv-note">Meanwhile you can still change one of your own voices by describing it in <button type="button" class="hv-lnk" data-a="go" data-p="mine">Your voice</button>, and clean up a recording in <button type="button" class="hv-lnk" data-a="go" data-p="cleanup">Clean-up</button>.</p></div>`;
  }
  // the picker: voices that can change grouped; the ones that cannot, with why
  function chgPick(b, cur, onPick) {
    const can = chgVoices(), grp = [['Your voices', v => v.kind === 'clone' || v.kind === 'design' || v.kind === 'remix'], ['Premium voices', v => v.kind === 'hoola'], ['Added from the shared library', v => v.kind === 'shared']];
    const row = v => ({label: v.name, sub: scrub(chgLine(v)), checked: v.id === cur, disabled: !v.ready, run: () => onPick(v.id)});
    const items = [{header: 'Change into'}, {search: 'Find a voice', empty: 'Nothing matches'}];
    for (const [h, fn] of grp) { const vs = can.filter(fn); if (vs.length) items.push({header: h}, ...vs.map(row)); }
    const no = D.voices.filter(v => v.kind !== 'hoola' && v.engine !== 'eleven');
    if (no.length) items.push({header: 'Cannot be used here'}, ...no.map(v => ({label: v.name, sub: `Lives on ${engName(v.engine)}; the voice changer works only with voices on ElevenLabs`, disabled: true})));
    menu(b, items, {width: 340});
  }
  // Before / After players: both run together, she hears one; switching never restarts
  function chgStop() { CHG.on = false; cancelAnimationFrame(CHG.raf); try { CHG.a?.pause(); CHG.b?.pause(); } catch { /* */ }
    $$('[data-a="chgplay"],[data-a="clplay"]').forEach(x => { x.innerHTML = ic('play', 14); x.setAttribute('aria-label', 'Play before and after'); }); }
  function chgMute() { const st = CHG.st || UI.chg; if (CHG.b) CHG.b.muted = st.hear === 'before' && !!CHG.a; if (CHG.a) CHG.a.muted = st.hear !== 'before'; }
  async function chgPlay(h) {
    if (CHG.on) return chgStop();
    try { const after = await blobUrl(`${A}/audio?id=${q(h.id)}`); let before = '', off = 0;
      const st = h.kind === 'cleanup' ? UI.cl : UI.chg;
      if (h.src) { try { before = await blobUrl(`${A}/${h.kind === 'cleanup' ? 'cleanup' : 'change'}/source?id=${q(h.id)}`); } catch { before = ''; } }
      if (!before && st.fileFor === h.id && st.file?.url) { before = st.file.url; off = h.trim ? h.trim[0] : 0; }
      $('#hvAudio')?.pause(); chgStop(); CHG.st = st; CHG.b = new Audio(after); CHG.a = before ? new Audio(before) : null; CHG.off = off; chgMute(); CHG.on = true;
      if (CHG.a) CHG.a.currentTime = off;
      await Promise.all([CHG.b.play(), CHG.a?.play()].filter(Boolean));
      $$('[data-a="chgplay"],[data-a="clplay"]').forEach(x => { x.innerHTML = ic('pause', 14); x.setAttribute('aria-label', 'Pause before and after'); });
      const tick = () => { if (!CHG.on) return; const b = CHG.b, d = b.duration || h.seconds || 1, p = Math.min(1, b.currentTime / d);
        if (CHG.a && Math.abs(CHG.a.currentTime - CHG.off - b.currentTime) > 0.15) CHG.a.currentTime = CHG.off + b.currentTime;
        $$('[data-ph]').forEach(x => { x.style.left = `${(p * 100).toFixed(2)}%`; }); const t = $('[data-chgt]'); if (t) t.textContent = `${secs(b.currentTime)} / ${secs(d)}`;
        if (b.ended) { chgStop(); return; } CHG.raf = requestAnimationFrame(tick); }; tick();
    } catch { chgStop(); toast('That sound could not be played here. Try Download instead.', true); }
  }
  function chgPart() {
    const c = UI.chg; if (!c.file?.url) return; chgStop(); $('#hvAudio')?.pause();
    const a = new Audio(c.file.url), e = c.end || c.secs; CHG.a = a; a.currentTime = c.start || 0;
    a.addEventListener('timeupdate', () => { if (a.currentTime >= e) a.pause(); }); a.play().catch(() => {});
  }
  function chgTrim(t) {      // the marked part moves live, no redraw (the slider keeps her finger)
    const c = UI.chg, s = c.secs || 0; let v = +t.value;
    if (t.dataset.trim === 'start') { v = Math.min(v, (c.end || s) - 1); c.start = Math.max(0, v); t.value = c.start; }
    else { v = Math.max(v, (c.start || 0) + 1); c.end = Math.min(s, v); t.value = c.end; }
    const w = $('[data-trimwave]'); if (w) { w.style.setProperty('--chga', (c.start / s).toFixed(4)); w.style.setProperty('--chgb', ((c.end || s) / s).toFixed(4)); }
    const tt = $('[data-trimt]'); if (tt) tt.textContent = `${secs(c.start)} – ${secs(c.end || s)}`;
    const tl = $('[data-triml]'); if (tl) tl.textContent = chgMarked() ? `Only this part is changed · ${secs(chgLen())}` : 'All of it is changed';
    chgPrice();
  }
  const chgBody = () => { const c = UI.chg, b = {denoise: !!c.denoise, closeness: c.close, feel: c.feel};
    if (c.file?.file_id) return {...b, file_id: c.file.file_id, ...(chgMarked() ? {start: c.start, end: c.end || c.secs} : {})};
    return c.out?.src ? {...b, source_of: c.out.id} : b; };
  function chgPrice() {
    if (PAGE !== 'changer') return; const c = UI.chg, len = chgLen() || 60;
    price('chg', {job: 'change', seconds: len, voice: c.voice}, r => r.credits != null ? `${chgLen() ? secs(chgLen()) + ' of sound' : 'Priced for a minute'} · nothing is spent until you tap` : esc(scrub(r.line || '')));
    const n = c.cmp.filter(Boolean).length, lc = c.file?.file_id ? chgLen() : (c.out?.seconds || 0);
    if (c.view === 'compare' && n) price('chgn', {job: 'change', seconds: lc || 60, voices: n}, r => r.credits != null ? `${n} × ${secs(lc || 60)} · nothing is spent until you tap` : esc(scrub(r.line || '')));
  }

  // ------------------------------------------------------------------ Clean-up (v0.999.161, design canvas claude.ai/artifact/1U18RieVdsG2uj2KqVeYUW)
  // Hoola listens first (measured on the server), says what is wrong and picks the fixes; she can change any of them; the
  // clean-up runs step by step in the background (Stop between steps); Before / After on one timeline with the readings
  // before and after; her recording kept beside it for 30 days (Before, Clean again).
  const CL_KINDS = [
    ['phone', 'Phone recording', 'Light noise removal, a clearer voice, loudness for reels and WhatsApp.', {denoise: true, noise: 'light', voice: true, level: true, target: 'reels', silence: false, people: false, music: false}],
    ['podcast', 'Podcast', 'Clearer voice, pauses kept natural, loudness at -16 for podcast apps.', {denoise: true, noise: 'medium', voice: true, level: true, target: 'podcast', silence: true, gap: 1, people: false, music: false}],
    ['meeting', 'Meeting call', 'Strong noise removal, a clearer voice, long pauses shortened.', {denoise: true, noise: 'strong', voice: true, level: true, target: 'podcast', silence: true, gap: 2, people: false, music: false}],
    ['outside', 'Interview outside', 'Street sounds and other people lifted out, then cleaned and evened out.', {denoise: true, noise: 'strong', voice: true, level: true, target: 'podcast', silence: true, gap: 1, people: true, music: false}],
    ['music', 'Voice in music', 'The voice is taken out of the music first, then evened out.', {denoise: false, voice: false, level: true, target: 'reels', silence: false, people: false, music: true}]];
  const CL_TGT = [['podcast', 'Podcast', -16], ['reels', 'Reels and YouTube', -14], ['audiobook', 'Audiobook', -19], ['broadcast', 'Radio and TV', -23]];
  const clHist = () => D.history.filter(h => h.kind === 'cleanup');
  const clPrem = () => UI.cl.people || UI.cl.music;
  const clSrc = () => { const c = UI.cl, f = c.file; return f?.from ? {source_of: f.from} : f?.sound ? {sound: f.sound} : f?.file_id ? {file_id: f.file_id} : null; };
  const db = v => v == null ? '–' : `${v > 0 ? '+' : ''}${(+v).toFixed(1)} dB`;
  const lu = v => v == null ? '–' : `${(+v).toFixed(0)} LUFS`;
  function clTop(title, sub) {
    const n = clHist().length;
    return `<div class="hv-chgtop"><span class="hv-vt"><b class="hv-chgt">${esc(title)}</b><span class="hv-mut hv-sm">${esc(sub)}</span></span><span class="hv-grow"></span>
      ${UI.cl.view ? `<button type="button" class="hv-btn" data-a="clview" data-val="">${ic('back', 14)}<span>Clean-up</span></button>` : ''}
      ${UI.cl.view !== 'list' ? `<button type="button" class="hv-btn" data-a="clview" data-val="list">Your clean-ups <span class="hv-num hv-mut">${num(n)}</span></button>` : ''}</div>`;
  }
  // what Hoola heard, as cards: each reading said in words, its number under it
  function clHeard(m) {
    const f = m.found || {}, out = [];
    out.push(f.noise ? ['warn', 'Background noise under the voice', `${db(m.background)} background`] : ['ok', 'Little background noise', `${db(m.background)} background`]);
    out.push(f.quiet ? ['warn', 'Quiet', `${lu(m.lufs)} · podcasts sit at -16`] : f.loud ? ['warn', 'Loud', `${lu(m.lufs)} · reels sit at -14`] : ['ok', 'Loudness is fine', lu(m.lufs)]);
    out.push(f.clips ? ['bad', m.clips ? `Loud words hit the top ${m.clips === 1 ? 'once' : m.clips + ' times'}` : 'Loud words hit the top', `loudest ${db(m.peak)}`] : ['ok', 'No crackle on loud words', `loudest ${db(m.peak)}`]);
    out.push(f.pauses ? ['info', `${plural(m.pauses, 'long pause')}`, `longest ${(+m.longest).toFixed(1)} s`] : ['ok', 'No long pauses', 'none over 1 s']);
    return `<div class="hv-clheard">${out.map(([k, t, v]) => `<div class="hv-clh ${k}"><span class="hv-clht"><span class="hv-cldt" aria-hidden="true"></span>${esc(t)}</span><span class="hv-num hv-sm">${esc(v)}</span></div>`).join('')}</div>
      ${m.partial ? '<span class="hv-mut hv-sm">Measured on the first 20 minutes.</span>' : ''}`;
  }
  function clRec() {
    const c = UI.cl, f = c.file, s = c.secs || f?.secs || 0;
    return `<div class="hv-card hv-chgrec"><div class="hv-rh"><b>Your recording</b><span class="hv-mut hv-sm hv-ell">${esc([f.name, s ? secs(s) : '', f.up ? 'uploading…' : f.err || '', f.from ? 'kept from before' : ''].filter(Boolean).join(' · '))}</span><span class="hv-grow"></span>
        <button type="button" class="hv-lnk" data-a="clnew">Choose another</button></div>
      <div class="hv-chgwave" aria-hidden="true">${chgBars(f.peaks, f.name + (f.from || ''), 96)}</div>
      ${f.url ? `<div class="hv-rh"><button type="button" class="hv-play" data-a="clpart" aria-label="Play your recording">${ic('play', 12)}</button><span class="hv-mut hv-sm">Your recording as it is</span></div>` : ''}
      <span class="hv-lab">What Hoola heard</span>
      ${c.listening ? `<div class="hv-clwait" role="status"><span class="hv-spin" aria-hidden="true"></span>Listening for noise, loudness, crackle and long pauses…</div>`
        : c.heard ? clHeard(c.heard) : f.err ? `<p class="hv-why">${esc(f.err)}</p>` : f.up ? '<span class="hv-mut hv-sm">Hoola listens as soon as it has uploaded.</span>' : ''}</div>`;
  }
  function clFixes() {
    const c = UI.cl, fnd = c.heard?.found || {}, w = ready('eleven') ? '' : whyNot('eleven'), pw = w || (broke() ? 'No credits left for lifting the voice out. The free clean-ups still work.' : '');
    const row = (k, t, found, more) => `<div class="hv-clfix"><label class="hv-check"><input type="checkbox" data-m="UI.cl.${k}" data-t="bool" data-redraw="1"${c[k] ? ' checked' : ''}><span>${t}</span></label>
      ${found ? '<span class="hv-badge warn">Found</span>' : ''}${c[k] && more ? `<div class="hv-clopt">${more}</div>` : ''}</div>`;
    const prem = (k, t) => { const g = gate(pw); return `<label class="hv-check"><input type="checkbox" data-m="UI.cl.${k}" data-t="bool" data-redraw="1"${c[k] && !pw ? ' checked' : ''}${g.a}><span>${t}</span></label>${g.l}`; };
    return `<div class="hv-card hv-clfixes">
      ${row('denoise', 'Remove background noise', fnd.noise, `<span class="hv-lab">How much</span>${seg('UI.cl.noise', [['light', 'Light'], ['medium', 'Medium'], ['strong', 'Strong']], c.noise, null, 'How much noise to remove')}`)}
      ${row('voice', 'Make the voice clearer', false, '')}
      ${row('level', 'Even out the loudness', fnd.quiet || fnd.loud || fnd.clips, `<span class="hv-lab">Heard on</span>${seg('UI.cl.target', CL_TGT.map(([v, l]) => [v, l]), c.target, null, 'Where it will be heard')}`)}
      ${row('silence', 'Shorten long pauses', fnd.pauses, `<span class="hv-lab">Longer than</span>${seg('UI.cl.gap', [[0.5, '0.5 s'], [1, '1 s'], [2, '2 s']], c.gap, null, 'Shorten pauses longer than')}`)}
      <div class="hv-clprem"><div class="hv-rh"><b class="hv-sm">Lift the voice out</b><span class="hv-src">ElevenLabs · uses credits</span></div>
        ${prem('people', 'Remove street sounds and other people')}${prem('music', 'Take the voice out of music')}
        ${pw ? `<span class="hv-mut hv-sm">${esc(scrub(pw))}${broke() && !w ? ` <a class="hv-lnk" href="${esc(D.credits_page || '/console/?v=credits')}">Get credits</a>` : ''}</span>` : ''}</div></div>`;
  }
  function clReadings(h) {
    const b = h.before || {}, a = h.after || {}, fx = h.fixes || {}, tgt = CL_TGT.find(x => x[0] === fx.target);
    const rows = [['Loudness', lu(b.lufs), lu(a.lufs), fx.level && tgt ? `${tgt[1]} level` : ''],
      ['Loudest peak', db(b.peak), db(a.peak), a.peak != null && a.peak < -1 && b.peak != null && b.peak >= -1 ? 'No more crackle' : ''],
      ['Background', db(b.background), db(a.background), b.background != null && a.background != null && b.background - a.background >= 3 ? `${Math.round(b.background - a.background)} dB quieter` : ''],
      ['Length', b.seconds ? secs(b.seconds) : '–', a.seconds ? secs(a.seconds) : '–', fx.silence && b.pauses ? `${plural(b.pauses, 'pause')} shortened` : '']];
    return `<div class="hv-card hv-clreadw"><table class="hv-clread"><caption class="hv-sr">Measured before and after</caption><thead><tr><th scope="col">Measured</th><th scope="col">Before</th><th scope="col">After</th><th scope="col"><span class="hv-sr">What changed</span></th></tr></thead>
      <tbody>${rows.map(([t, x, y, n]) => `<tr><th scope="row">${t}</th><td class="hv-num b">${x}</td><td class="hv-num a">${y}</td><td class="hv-sm">${esc(n)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function clHear(h) {
    const c = UI.cl, srcKept = h ? !!h.src || (c.fileFor === h.id && !!c.file?.url) : !!c.file;
    const lane = (k, who, bars, on, note) => `<div class="hv-chglane${on ? ' on' : ''} l-${k}"><span class="hv-vt"><b class="hv-sm">${k === 'before' ? 'Before' : 'After'}</b><span class="hv-mut hv-sm hv-ell">${esc(who)}</span></span>
      <span class="hv-chgw${note ? ' empty' : ''}">${note ? `<span class="hv-chgnote">${esc(note)}</span>` : `${bars}<span class="hv-chgph" data-ph></span>`}</span></div>`;
    const bp = c.file?.peaks && (!h || c.fileFor === h.id) ? c.file.peaks : null;
    return `<div class="hv-rh hv-chgh"><b class="hv-chgt2">Hear the difference</b><span class="hv-mut hv-sm">${h ? `Cleaned · ${esc(String(ago(h.made)).toLowerCase())}` : 'Your words and timing stay'}</span><span class="hv-grow"></span>
        ${h ? `<div class="hv-seg" role="radiogroup" aria-label="Hear">${[['before', 'Before'], ['after', 'After']].map(([k, l]) => { const dis = k === 'before' && !srcKept;
          return `<button type="button" role="radio" aria-checked="${c.hear === k && !dis}" data-a="clhear" data-val="${k}"${dis ? ' disabled aria-describedby="hvClNs"' : ''}>${l}</button>`; }).join('')}</div>${srcKept ? '' : '<span class="hv-sr" id="hvClNs">Your own recording is no longer kept</span>'}` : ''}</div>
      <div class="hv-card hv-chgab">
        ${lane('before', h ? secs(h.before?.seconds || h.src_secs || 0) : 'As recorded', chgBars(bp, (h?.id || 'rec') + 'src', 72), c.hear === 'before', !srcKept ? (h ? 'Your own recording is no longer kept' : 'Choose a recording') : '')}
        ${lane('after', h ? secs(h.seconds || 0) : 'Cleaned', chgBars(null, h?.id || 'none', 72), c.hear !== 'before', h ? '' : 'Made when you tap Clean it')}
        ${h ? `<div class="hv-rh hv-chgpl"><button type="button" class="hv-play l" data-a="clplay" aria-label="${CHG.on ? 'Pause' : 'Play'} before and after">${ic(CHG.on ? 'pause' : 'play', 14)}</button>
          <span class="hv-num" data-chgt>0:00 / ${secs(h.seconds || 0)}</span><span class="hv-mut hv-sm">${srcKept ? 'Tap Before or After while it plays to switch at the same moment.' : 'Only the cleaned recording can be played.'}</span></div>` : ''}</div>`;
  }
  function clStart() {
    const recOn = !!REC.cl, free = 'Free · on Hoola’s own server', prem = 'ElevenLabs · uses credits';
    const cards = [['Background noise', 'Fans, hiss, AC hum and room sound, light to strong.', free], ['A clearer voice', 'Muddy or far-away voices brought forward and warmer.', free],
      ['Loudness', 'Too quiet or too loud, set right for where it will be heard.', free], ['Long pauses', 'Gaps longer than you choose made shorter, words untouched.', free],
      ['Street sounds and other people', 'Only the main voice is kept: traffic, crowds, other talk gone.', prem], ['Take the voice out of music', 'The singing or speaking voice lifted out of the song.', prem]];
    return `<div class="hv-doc hv-chg hv-cl hv-clstart">${clTop('Clean-up', 'Hoola listens first, tells you what is wrong, and fixes only that.')}
      <div class="hv-chghero"><span class="hv-clfig" aria-hidden="true"><span class="hv-chgw s dim">${chgBars(null, 'rough', 18)}</span>${ic('chev', 18)}<span class="hv-chgw s ok">${chgBars(null, 'clean', 18)}</span></span>
        <h2 class="hv-yvtitle">Make any recording sound clear</h2>
        <p class="hv-yvlead">Hoola listens first and tells you what is wrong: noise, a quiet voice, crackle on loud words, long pauses. Then it fixes only that. Your words and timing stay as they are.</p></div>
      <div class="hv-cldrop" data-drop="cl">
        ${recOn ? `<div class="hv-yvmic"><button type="button" class="hv-recb xl on" data-a="recstop" data-k="cl" style="--p:0" aria-label="Stop recording"><span class="hv-sq"></span></button>
          <span class="hv-vt"><b>Listening…</b><span class="hv-mut hv-num" data-rect="cl">0:00 of 5:00</span><span class="hv-yvlvl" aria-hidden="true"><span data-lvl="cl"></span></span></span></div>`
        : `<div class="hv-acts c"><button type="button" class="hv-cta s" data-a="pickfile" data-k="cl" data-accept="audio/*,video/*">${ic('upload', 14)}<span>Choose a recording or a video</span></button>
          <button type="button" class="hv-btn" data-a="rec" data-k="cl">${ic('mic', 14)}Record here</button>
          <button type="button" class="hv-btn" data-a="clsound" aria-haspopup="menu"${D.history.length ? '' : ' disabled'}>From Your sounds</button></div>
          <span class="hv-mut hv-sm">or drop a file here · WAV, MP3, M4A, OGG, FLAC, or a video</span>`}</div>
      <div class="hv-clcan"><b>What Hoola can fix</b><div class="hv-clcards">${cards.map(([h, b, t]) => `<article class="hv-card hv-clcard${t === prem ? ' prem' : ''}"><b>${esc(h)}</b><span class="hv-sm">${esc(b)}</span><span class="hv-sm hv-cltag">${esc(t)}</span></article>`).join('')}</div></div></div>`;
  }
  function clWorkInner() {
    const j = UI.cl.job, st = j.steps || [], done = st.filter(s => s.state === 'done').length, f = UI.cl.file || {};
    const p = st.length ? done / st.length : 0, bars = chgBars(f.peaks, (f.name || 'x') + (f.from || ''), 120);
    return `<div class="hv-chgwave hv-clprog" style="--clp:${p.toFixed(3)}" aria-hidden="true">${bars}</div>
      <ol class="hv-clsteps" aria-label="Steps">${st.map(s => `<li class="${s.state}"${s.state === 'now' ? ' aria-current="step"' : ''}><span class="hv-cldot">${s.state === 'done' ? ic('check', 12) : s.state === 'now' ? '<span class="hv-spin" aria-hidden="true"></span>' : ''}</span>
        <span class="hv-vt"><b>${esc(s.t)}</b>${s.sub ? `<span class="hv-mut hv-sm">${esc(s.sub)}</span>` : ''}</span><span class="hv-num hv-mut hv-sm">${s.secs != null ? secs(s.secs) : ''}</span>
        <span class="hv-sr">${s.state === 'done' ? 'done' : s.state === 'now' ? 'working' : 'waiting'}</span></li>`).join('')}</ol>`;
  }
  function clWork() {
    const j = UI.cl.job;
    return `<div class="hv-doc hv-chg hv-cl hv-clwork">${clTop('Clean-up', UI.cl.file?.name || '')}
      <div class="hv-clworkb"><div class="hv-rh"><h2 class="hv-yvtitle">Cleaning your recording</h2><span class="hv-num hv-mut" data-clclock>${secs(j.seconds || 0)}</span><span class="hv-grow"></span>
        <button type="button" class="hv-btn" data-a="clstop"${j.stop ? ' disabled' : ''}>${j.stop ? 'Stopping after this step…' : 'Stop'}</button></div>
        <div data-clwork>${clWorkInner()}</div>
        <p class="hv-mut hv-sm">You can leave this page. The clean recording lands in Your sounds and here when it is done.</p></div></div>`;
  }
  function clMain() {
    const c = UI.cl, h = c.out && D.history.find(x => x.id === c.out.id) || c.out, src = clSrc();
    const g = gate(clPrem() && broke() ? NO_CR : !src ? (c.file?.up ? 'The recording is still uploading.' : c.file?.err ? 'The recording did not upload. Choose another.' : 'Choose a recording first.')
      : !['denoise', 'voice', 'level', 'silence', 'people', 'music'].some(k => c[k]) ? 'Choose at least one thing to fix.' : '');
    const kind = CL_KINDS.find(k => k[0] === c.kind), recent = clHist().filter(x => x.id !== h?.id).slice(0, 3);
    const label = clPrem() ? 'Clean it' : 'Clean it · free';
    return `<div class="hv-doc hv-chg hv-cl">${clTop('Clean-up', 'Hoola listens first, tells you what is wrong, and fixes only that.')}
      <div class="hv-chggrid"><section class="hv-chgl" aria-label="What to fix">
        ${clRec()}
        <div class="hv-fld"><span class="hv-lab" id="hvClKind">What kind of recording is it?</span>
          <div class="hv-chips" role="radiogroup" aria-labelledby="hvClKind">${CL_KINDS.map(([k, l]) => `<button type="button" class="hv-chip" role="radio" aria-checked="${c.kind === k}" data-a="clkind" data-val="${k}">${esc(l)}</button>`).join('')}</div>
          <span class="hv-mut hv-sm">${esc(kind ? kind[2] : c.heard ? 'Hoola picked the fixes from what it heard. Pick a kind to start from that instead.' : 'Pick one to start from, or tick the fixes yourself.')}</span></div>
        ${clFixes()}
        <div class="hv-chgcta"><button type="button" class="hv-cta" data-a="clrun" data-qbtn="cl" data-label="${label}"${g.a}><span>${label}</span></button>${g.l}
          <p class="hv-hint c" data-qline="cl">${clPrem() ? '' : 'Noise, clarity, pauses and loudness are free · only lifting the voice out uses credits'}</p></div>
      </section>
      <section class="hv-chgr" aria-label="Before and after">
        ${clHear(h)}
        ${h && h.before && h.after ? clReadings(h) : ''}
        ${h ? `<div class="hv-acts"><button type="button" class="hv-cta s" data-a="dlmenu" data-id="${esc(h.id)}" aria-haspopup="menu"><span>Download</span>${ic('down', 12)}</button>
          ${h.src && h.fixes?.noise !== 'strong' ? `<button type="button" class="hv-btn" data-a="clagain" data-id="${esc(h.id)}" data-val="stronger">Clean again, stronger</button>` : ''}
          ${h.src ? `<button type="button" class="hv-btn" data-a="clagain" data-id="${esc(h.id)}" data-val="settings">Clean again, other settings</button>` : ''}
          <button type="button" class="hv-btn" data-a="go" data-p="changer">Change the voice</button>
          <span class="hv-mut hv-sm">Kept in Your sounds${h.src ? ' · your recording kept 30 days' : ''}</span></div>` : ''}
        ${recent.length ? `<div class="hv-chgrecent"><div class="hv-rh"><b>Recent clean-ups</b><button type="button" class="hv-lnk" data-a="clview" data-val="list">See all</button></div>
          ${recent.map(x => `<div class="hv-chgrow">${playBtn(x.id, `Play ${x.title || 'clean-up'}`, 11, ' s')}<button type="button" class="hv-chgrt" data-a="clopen" data-id="${esc(x.id)}">${esc(x.title || 'Clean-up')}</button><span class="hv-mut hv-sm hv-ell">${esc(x.voice_name || '')}</span><span class="hv-num hv-mut hv-sm">${x.seconds ? secs(x.seconds) : ''}</span></div>`).join('')}</div>` : ''}
      </section></div></div>`;
  }
  function clList() {
    const all = clHist(), fl = UI.cl.filt, list = all.filter(h => !fl || (fl === 'free' ? h.engine !== 'eleven' : h.engine === 'eleven'));
    const card = h => `<article class="hv-card hv-chgc"><div class="hv-rh"><b class="hv-ell">${esc(h.title || 'Clean-up')}</b><span class="hv-grow"></span><span class="hv-mut hv-sm">${esc(ago(h.made))}</span>
        <button type="button" class="hv-ib s" data-a="sndmenu" data-id="${esc(h.id)}" aria-label="More for ${esc(h.title || 'this clean-up')}: download, remove">${ic('more')}</button></div>
      <div class="hv-chgpair"><span class="hv-sm">Before</span>${h.src ? `<button type="button" class="hv-play s" data-a="chgsrc" data-id="${esc(h.id)}" aria-label="Play your own recording">${ic('play', 11)}</button>` : '<span class="hv-play s off" aria-hidden="true"></span>'}<span class="hv-chgw s dim" aria-hidden="true">${chgBars(null, h.id + 'src', 48)}</span>
        <b class="hv-sm hv-okt">After</b>${playBtn(h.id, `Play ${h.title || 'the clean-up'}`, 11, ' s')}<span class="hv-chgw s ok" aria-hidden="true">${chgBars(null, h.id, 48)}</span></div>
      ${(h.done || []).length ? `<div class="hv-chips">${h.done.map(x => `<span class="hv-tag">${esc(x)}</span>`).join('')}</div>` : h.voice_name ? `<span class="hv-mut hv-sm">${esc(h.voice_name)}</span>` : ''}
      <div class="hv-rh"><button type="button" class="hv-btn s" data-a="clopen" data-id="${esc(h.id)}">Open</button><button type="button" class="hv-btn s" data-a="dlmenu" data-id="${esc(h.id)}" aria-haspopup="menu">Download</button><span class="hv-grow"></span>
        <span class="hv-mut hv-sm">${h.src ? `Your recording kept until ${esc(new Date(h.src_until).toLocaleDateString(undefined, {day: 'numeric', month: 'short'}))}` : 'Your recording no longer kept'}</span></div></article>`;
    return `<div class="hv-doc hv-chg hv-cl">${clTop('Your clean-ups', plural(all.length, 'cleaned recording'))}
      ${all.length ? `<div class="hv-chips" role="radiogroup" aria-label="Show">${[['', 'All'], ['free', 'Free'], ['lift', 'Voice lifted out']].map(([k, l]) => `<button type="button" class="hv-chip" role="radio" aria-checked="${fl === k}" data-a="clfilt" data-val="${k}">${l}</button>`).join('')}</div>
        <div class="hv-chglist">${list.map(card).join('') || '<span class="hv-mut hv-sm">None of this kind yet.</span>'}</div>
        <p class="hv-mut hv-sm">Your own recording is kept beside each clean-up for 30 days so you can hear it and clean it again. The cleaned sound stays until you remove it.</p>`
        : empty('No clean-ups yet', 'Choose a recording and Hoola will tell you what to fix.', '<button type="button" class="hv-cta s" data-a="clview" data-val=""><span>Clean a recording</span></button>')}</div>`;
  }
  function clNot() {
    const cards = [['bad', 'Not on this server', 'The sound tool is missing', `Cleaning runs on ffmpeg on this Hoola server. ${whyNot('server')} Nothing can be cleaned until it is, and nothing is charged.`, '', 'For the owner: install ffmpeg on the server.']];
    if (!ready('eleven')) cards.push(['', 'Not connected', 'Lifting the voice out is not connected', 'Removing street sounds, other people or music needs ElevenLabs on this server.', '', 'For the owner: add the key in the server settings, never in a chat.']);
    return `<div class="hv-doc hv-chg hv-cl hv-chgnot"><div class="hv-chghero"><span class="hv-clfig" aria-hidden="true"><span class="hv-chgw s dim">${chgBars(null, 'rough', 18)}</span>${ic('chev', 18)}<span class="hv-chgw s ok">${chgBars(null, 'clean', 18)}</span></span>
        <h2 class="hv-yvtitle">Make any recording sound clear.</h2>
        <p class="hv-yvlead">Noise, a quiet voice, crackle and long pauses are fixed on Hoola’s own server for free. Lifting a voice out of street sounds or music runs on ElevenLabs.</p></div>
      <div class="hv-chgnots">${cards.map(([t, tag, h, b, btn, foot]) => `<article class="hv-card hv-chgnc${t ? ' ' + t : ''}"><span class="hv-badge">${esc(tag)}</span><b>${esc(h)}</b><span class="hv-sm">${esc(scrub(b))}</span>${btn}<span class="hv-mut hv-sm">${esc(foot)}</span></article>`).join('')}</div>
      <p class="hv-note">Your recordings and earlier clean-ups stay in <button type="button" class="hv-lnk" data-a="go" data-p="sounds">Your sounds</button> whatever happens here.</p></div>`;
  }
  // a recording chosen (file, the mic, a sound she made here, or her recording kept beside a clean-up) -> Hoola listens
  async function clFile(file, s) {
    chgStop(); const slot = {name: file.name, up: true, secs: s || 0};
    Object.assign(UI.cl, {file: slot, secs: s || 0, heard: null, out: null, job: null, fileFor: '', kind: ''}); draw();
    if (!s) slot.secs = UI.cl.secs = await fileSecs(file);
    try { slot.url = URL.createObjectURL(file); } catch { /* no playback */ }
    slot.peaks = await chgPeaks(file, 120); if (PAGE === 'cleanup') draw();
    try { slot.file_id = await up(file); } catch (e) { slot.err = scrub(e.message); toast(e.message, true); }
    slot.up = false; if (UI.cl.file === slot && slot.file_id) return clListen();
    if (PAGE === 'cleanup') draw();
  }
  async function clListen() {
    const c = UI.cl, body = clSrc(); if (!body) return;
    c.listening = true; if (PAGE === 'cleanup') draw();
    try { const r = await api('POST', `${A}/cleanup/listen`, body); if (clSrc()?.file_id !== body.file_id || clSrc()?.source_of !== body.source_of) return;
      c.heard = r; if (!c.secs && r.seconds) c.secs = r.seconds;
      if (!c.kind && r.pick) Object.assign(c, {denoise: r.pick.denoise, noise: r.pick.noise, level: r.pick.level, silence: r.pick.silence, voice: true}); }
    catch (e) { toast(e.message, true); }
    c.listening = false; if (PAGE === 'cleanup') { draw(); clPrice(); }
  }
  function clBody() {
    const c = UI.cl;
    return {...clSrc(), wait: false, name: c.file?.name || '', denoise: !!c.denoise, noise: c.noise, voice: !!c.voice, level: !!c.level, target: c.target,
      silence: !!c.silence, gap: +c.gap, people: ready('eleven') && !!c.people, music: ready('eleven') && !!c.music};
  }
  function clPoll() {
    clearTimeout(UI.cl.poll);
    UI.cl.poll = setTimeout(async () => { const j = UI.cl.job; if (!j) return;
      try { const r = await api('GET', `${A}/cleanup/job?id=${q(j.id)}`); r.stop = j.stop; UI.cl.job = r;
        if (r.status === 'done') { Object.assign(UI.cl, {job: null, out: r.result, hear: 'after', fileFor: r.result?.id || ''}); await load(); side(); toast('Cleaned. Hear the difference.'); draw(); if (innerWidth < 1100) $('#hvView .hv-chgr')?.scrollIntoView({block: 'start'}); return; }
        if (r.status !== 'working') { UI.cl.job = null; toast(r.status === 'stopped' ? 'Stopped. Nothing was kept.' : (r.error || 'That recording could not be cleaned.'), r.status !== 'stopped'); return draw(); }
        if (PAGE === 'cleanup') { const w = $('[data-clwork]'); if (w) w.innerHTML = clWorkInner(); else draw(); const t = $('[data-clclock]'); if (t) t.textContent = secs(r.seconds || 0); }
      } catch (e) { UI.cl.job = null; toast(e.message, true); draw(); return; }
      clPoll(); }, 700);
  }
  function clPrice() {
    if (PAGE !== 'cleanup' || !clPrem()) return;
    price('cl', {job: 'isolate', seconds: UI.cl.secs || 60}, r => r.credits != null ? `${UI.cl.secs ? secs(UI.cl.secs) + ' of sound' : 'Priced for a minute'} · lifting the voice out · the rest is free` : esc(scrub(r.line || '')));
  }

  // ------------------------------------------------------------------ recording in the page ---
  const REC = {};
  async function recStart(k) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { toast('This browser cannot record here. Choose a recording instead.', true); return; }
    try { const st = await navigator.mediaDevices.getUserMedia({audio: true}), mr = new MediaRecorder(st), parts = [];
      mr.ondataavailable = e => { if (e.data.size) parts.push(e.data); };
      mr.onstop = () => { st.getTracks().forEach(t => t.stop()); const s = (Date.now() - REC[k].t0) / 1000; delete REC[k];
        const type = (mr.mimeType || 'audio/webm').split(';')[0], ext = /ogg/.test(type) ? 'ogg' : /mp4|m4a|aac/.test(type) ? 'm4a' : 'webm';
        const blob = new Blob(parts, {type}); recFile(k, new File([blob], `recording-${k}.${ext}`, {type}), s); };
      const limit = k === 'chg' || k === 'cl' ? 300 : 30;
      let an = null, ac = null, buf = null;                    // the live level: a meter of her voice while she speaks (nothing leaves the browser)
      try { const AC = window.AudioContext || window.webkitAudioContext; ac = new AC(); an = ac.createAnalyser(); an.fftSize = 1024; ac.createMediaStreamSource(st).connect(an); buf = new Float32Array(an.fftSize); } catch { an = null; }
      mr.addEventListener('stop', () => { try { ac?.close(); } catch { /* closed */ } });
      REC[k] = {mr, t0: Date.now()}; mr.start(); draw();
      const lvl = () => { if (!REC[k] || !an) return; an.getFloatTimeDomainData(buf); let x = 0; for (const v of buf) x = Math.max(x, Math.abs(v));
        const bar = $(`[data-lvl="${k}"]`); if (bar) { bar.style.width = `${Math.round(Math.min(1, x * 1.4) * 100)}%`; bar.classList.toggle('hot', x >= 0.98); } requestAnimationFrame(lvl); }; lvl();
      const tick = () => { if (!REC[k]) return; const t = (Date.now() - REC[k].t0) / 1000, el = $(`[data-rect="${k}"]`), btn = $(`[data-a="recstop"][data-k="${k}"]`);
        if (el) el.textContent = k === 'chg' || k === 'cl' ? `${secs(t)} of 5:00` : `${secs(t)} of 0:30`; if (btn) btn.style.setProperty('--p', Math.min(1, t / limit).toFixed(3));
        if (t >= limit) { REC[k].mr.stop(); return; } setTimeout(tick, 200); }; tick(); }
    catch (e) { toast(`The microphone did not start: ${e.message}`, true); }
  }
  // a recording or a picked file for the voice pages: uploaded at once, its length kept for the price and the checks
  async function recFile(k, file, s) {
    if (k === 'cl') return clFile(file, s);
    const slot = {name: file.name, up: true, secs: s || 0};
    if (k === 'chg') { chgStop(); Object.assign(UI.chg, {file: slot, start: 0, end: 0, out: null, cmpOut: null, cmpPick: '', fileFor: ''}); } else UI.clone[k] = slot;
    draw(); if (!s) slot.secs = await fileSecs(file);
    if (k === 'chg') UI.chg.secs = slot.secs;
    try { slot.url = URL.createObjectURL(file); } catch { /* no playback */ }
    slot.meter = await yMeter(file); if (k === 'chg') { slot.peaks = await chgPeaks(file); if (PAGE === 'changer') draw(); }
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
    if (k === 'cl') return clFile(file, 0);
    const slot = {name: file.name, up: true};
    const set = o => { if (k === 'pod') UI.dlg.pod.file = o; else if (k === 'imp') UI.imp.file = o; else if (k === 'dub') UI.dubNew.file = o; else if (k === 'cl') UI.cl.file = o; };
    set(slot); draw();
    const s = ['dub', 'cl'].includes(k) ? await fileSecs(file) : 0;
    if (k === 'dub') { UI.dubNew.secs = s; try { UI.dubNew.preview = URL.createObjectURL(file); } catch { UI.dubNew.preview = ''; } topTools(); }
    try { slot.file_id = await up(file); } catch (e) { slot.err = scrub(e.message); toast(e.message, true); }
    slot.up = false; draw();
    if (k === 'imp' && slot.file_id && PAGE === 'studio' && UI.imp.file === slot) impPreview();
  }

  // ------------------------------------------------------------------ the Studio: books, chapters, paragraphs ---
  const hm = s => { s = Math.round(+s || 0); const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60); return h ? `${h} h ${String(m).padStart(2, '0')} min` : `${Math.max(1, m)} min`; };
  const wordsOf = t => (String(t || '').trim() ? String(t).trim().split(/\s+/).length : 0);
  const tint = t => [...String(t || 'x')].reduce((a, c) => a + c.charCodeAt(0), 0) % 4;
  const paceWord = v => { v = +(v || 1); return `${v.toFixed(2)}x · ${v < 0.9 ? 'slow' : v < 0.98 ? 'calm' : v <= 1.02 ? 'as written' : v < 1.12 ? 'brisk' : 'fast'}`; };
  const gapOf = p => { const g = +(p.gap || 0.9); return [0.5, 1, 2, 3, 5].reduce((a, x) => Math.abs(x - g) < Math.abs(a - g) ? x : a, 1); };
  const stName = s => s === 'made' ? 'read' : s === 'changed' ? 'changed since it was read' : 'not read yet';
  // a cover: her picture when the book has one, else one painted from the title (the picture fills in after drawing)
  const coverOf = (p, cls = '', token = '') => `<span class="hv-cover ${cls} t${tint(p.title)}" aria-hidden="true">${p.cover || token ? `<img alt="" ${token ? `data-ctoken="${esc(token)}"` : `data-cover="${esc(p.id)}"`}>` : ''}
    <span class="hv-cvt">${esc(p.title || 'A reading')}</span><span class="hv-cvr"></span><span class="hv-cva">${esc(p.author || '')}</span></span>`;
  async function fillCovers() {
    for (const im of $$('img[data-cover],img[data-ctoken]')) { if (im.src) continue;
      try { im.src = await blobUrl(im.dataset.cover ? `${A}/project/cover?id=${q(im.dataset.cover)}` : `${A}/project/cover?token=${q(im.dataset.ctoken)}`);
        im.onload = () => im.parentElement?.classList.add('img'); } catch { im.remove(); } }
  }
  // the paragraphs of a chapter as they read now: who says each, and whether it was read like this (made / changed / none)
  function paraList(ch) {
    const texts = String(ch.text || '').split(/\n\s*\n/).map(x => x.trim()).filter(Boolean);
    const who = new Map((ch.paragraphs || []).map(x => [x.text, x.who]));
    const segs = (ch.segments || []).map(s => `${s.who || 'Narrator'}\u0001${s.text}`);
    return texts.map(t => { const w = who.get(t) || 'Narrator'; return {text: t, who: w, state: !ch.audio ? 'none' : segs.includes(`${w}\u0001${t}`) ? 'made' : 'changed'}; });
  }
  function chState(p, i) { const c = p.chapters[i]; if (!c?.audio) return 'none'; if (UI.edited[i]) return 'changed';
    return (c.segments || []).length && paraList(c).some(x => x.state !== 'made') ? 'changed' : 'made'; }
  function bookStat(p) { const ch = p.chapters || [], made = ch.filter(c => c.audio).length, sec = ch.reduce((s, c) => s + (+c.seconds || 0), 0);
    const voices = new Set([p.voice, ...Object.values(p.cast || {})].filter(Boolean)).size || 1;
    return {n: ch.length, made, done: !!ch.length && made === ch.length, pct: ch.length ? Math.round(made / ch.length * 100) : 0, secs: sec, voices}; }
  // who reads whom: the narrator first, then the people found in the book
  function castOf(p) { const c = {...(p.cast || {})}; const nar = c.Narrator || p.voice || S.voice; delete c.Narrator; return {Narrator: nar, ...c}; }
  // a paragraph's words, the quoted words in the colour of who says them
  function said(x, cast) {
    const t = esc(x.text); if (x.who === 'Narrator') return t;
    const i = Object.keys(cast).indexOf(x.who), k = i < 0 ? 1 : i % 4;
    const out = t.replace(/(“[^”]*”|&quot;[^&]*?&quot;|"[^"]*")/g, m => `<span class="hv-q t${k}">${m}</span>`);
    return out === t ? `<span class="hv-q t${k}">${t}</span>` : out;
  }
  const projDirty = () => { const p = UI.proj, s = p && D.projects.find(x => x.id === p.id); if (!p) return false; if (!s) return true;
    const pick = o => JSON.stringify([o.title, o.voice, o.lang, +(o.pace || 1), +(o.gap || 0.9), (o.chapters || []).map(c => [c.title, c.text])]); return pick(p) !== pick(s); };
  function readTools() {
    const t = $('#hvTopR'); if (!t) return; const p = UI.proj;
    if (PAGE === 'studio' && !UI.imp.open) { t.innerHTML = `<button type="button" class="hv-btn s" data-a="impopen" aria-label="Import a book">${ic('upload', 14)}<span class="hv-tlab">Import a book</span></button><button type="button" class="hv-btn s dark" data-a="newproj" aria-label="New reading">${ic('plus', 14)}<span class="hv-tlab">New reading</span></button>`; return; }
    if (PAGE !== 'reading' || !p) { t.innerHTML = ''; return; }
    const dirty = projDirty();
    t.innerHTML = `<span class="hv-saved${dirty ? ' no' : ''}" role="status"><span class="hv-dot ${dirty ? 'changed' : 'made'}" aria-hidden="true"></span><span class="hv-tlab">${dirty ? 'Not saved yet' : 'Saved'}</span></span>
      ${dirty ? '<button type="button" class="hv-btn s" data-a="saveproj">Save</button>' : ''}
      <button type="button" class="hv-btn s" data-a="sdopen" data-k="people" aria-haspopup="dialog" aria-label="Who reads whom">${ic('dialog', 14)}<span class="hv-tlab">Who reads whom</span></button>
      <button type="button" class="hv-btn s dark" data-a="sdopen" data-k="book" aria-haspopup="dialog" aria-label="Make the audiobook">${ic('book', 14)}<span class="hv-tlab">Make the audiobook</span></button>`;
  }

  // ------------------------------------------------------------------ import a book: the source, then a look before anything is made ---
  function impStart() {
    const im = UI.imp;
    return `<div class="hv-doc hv-impa"><form class="hv-card hv-form" data-f="import"><div class="hv-rh"><b class="hv-t">Import a book</b><span class="hv-grow"></span><button type="button" class="hv-ib s" data-a="impclose" aria-label="Close">${ic('x', 14)}</button></div>
        <span class="hv-mut hv-sm">EPUB, PDF, Word, text, a web page or pasted text. You see the chapters before anything is made.</span>
        ${seg('UI.imp.src', [['file', 'A file'], ['url', 'A web address'], ['text', 'Pasted text']], im.src, null, 'From')}
        ${im.src === 'file' ? `<button type="button" class="hv-sdrop s" data-a="pickfile" data-k="imp" data-drop="imp" data-accept=".epub,.pdf,.txt,.doc,.docx,.md">${ic('upload', 20)}<b>${im.file ? esc(im.file.name) : 'Drop a book here, or choose a file'}</b>
            <span>${im.file ? (im.file.up ? 'Uploading…' : im.file.err ? esc(im.file.err) : im.file.file_id ? 'Reading the book…' : '') : 'EPUB, PDF, Word or text'}</span></button>`
          : im.src === 'url' ? `<label class="hv-lab" for="hvImU">Web address</label><input id="hvImU" class="hv-in" type="url" data-m="UI.imp.url" value="${esc(im.url)}" placeholder="https://">`
          : `<label class="hv-lab" for="hvImT">The text</label><textarea id="hvImT" class="hv-in serif" rows="8" data-m="UI.imp.text" placeholder="Paste the story. Chapter headings are found for you.">${esc(im.text)}</textarea>`}
        ${im.src === 'file' ? '' : '<div class="hv-ctarow"><button class="hv-btn dark">Look at the chapters</button></div>'}
        <p class="hv-mut hv-sm">Only books you wrote or have the right to read aloud. Nothing is spent until you make a chapter.</p></form></div>`;
  }
  function impTotals() { const pv = UI.imp.pv, on = pv.parts.filter(x => UI.imp.keep[x.n]);
    return {on, words: on.reduce((s, x) => s + x.words, 0), secs: on.reduce((s, x) => s + x.seconds, 0), credits: on.reduce((s, x) => s + (+x.credits || 0), 0)}; }
  function impView() {
    const im = UI.imp, pv = im.pv, t = impTotals(), max = pv.max_chapters || 60;
    const src = im.src === 'file' ? (im.file?.name || 'Your file') : im.src === 'url' ? im.url : 'Pasted text', kind = im.src === 'file' ? (String(im.file?.name || '').split('.').pop() || 'file').toUpperCase().slice(0, 4) : im.src === 'url' ? 'WEB' : 'TEXT';
    const tooMany = t.on.length > max, g = gate(!t.on.length ? 'Tick at least one part to read.' : tooMany ? `A reading holds up to ${max} chapters. Untick ${t.on.length - max}.` : '');
    return `<div class="hv-split hv-tool hv-imp"><section class="hv-panel wide" aria-label="Chapters found">
        <div class="hv-card hv-impsrc"><span class="hv-kind">${esc(kind)}</span><span class="hv-vt"><b>${esc(src)}</b><span class="hv-ok hv-sm">Read · ${plural(pv.parts.length, 'part')} found · ${plural(pv.parts.reduce((s, x) => s + x.words, 0), 'word')}</span></span>
          <span class="hv-grow"></span><button type="button" class="hv-btn s" data-a="impagain">Choose another</button></div>
        <div class="hv-rh hv-imph"><span class="hv-vt"><b class="hv-h2">Check the chapters</b><span class="hv-mut hv-sm">Parts that are not the story (contents, copyright, thanks) are left out for you. Tick any you want read.</span></span>
          <span class="hv-grow"></span><span class="hv-mut hv-sm hv-num" role="status"><b>${t.on.length}</b> of ${pv.parts.length} will be read</span></div>
        <ol class="hv-parts">${pv.parts.map((x, i) => { const on = !!im.keep[x.n];
          return `<li class="hv-part${on ? '' : ' off'}"><button type="button" role="checkbox" class="hv-tick" aria-checked="${on}" data-a="imptick" data-n="${x.n}" aria-label="${esc(x.title)}">${on ? ic('check', 12) : ''}</button>
            <span class="hv-num hv-mut hv-sm">${i + 1}</span><span class="hv-vt"><b>${esc(x.title)}</b><span class="hv-ptxt serif">${esc(x.first)}</span></span>
            <span class="hv-num hv-mut hv-sm">${num(x.words)} words</span>${!on && x.why ? `<span class="hv-badge">${esc(x.why)}</span>` : ''}</li>`; }).join('')}</ol></section>
      <aside class="hv-stage hv-side2" aria-label="About the book"><div class="hv-stageb">
        <div class="hv-impcov">${coverOf({title: im.title || pv.title, author: im.author}, 'm', pv.cover)}<span class="hv-vt"><span class="hv-mut hv-sm">${pv.cover ? 'The cover from the book' : 'A cover painted from the title'}</span>
          <span class="hv-mut hv-sm">You can add your own picture once the reading is made.</span></span></div>
        <label class="hv-lab" for="hvImTi">Title</label><input id="hvImTi" class="hv-in" maxlength="80" data-m="UI.imp.title" value="${esc(im.title)}">
        <label class="hv-lab" for="hvImA">Author</label><input id="hvImA" class="hv-in" maxlength="80" data-m="UI.imp.author" value="${esc(im.author)}" placeholder="Who wrote it">
        <div class="hv-fld"><span class="hv-lab">Language</span><span class="hv-in hv-ro">${esc(langLabel(pv.lang))} · found in the book</span></div>
        <dl class="hv-tot"><div><dt>Chapters to read</dt><dd class="hv-num">${t.on.length}</dd></div><div><dt>Words</dt><dd class="hv-num">${num(t.words)}</dd></div>
          <div><dt>Sound, about</dt><dd class="hv-num">${hm(t.secs)}</dd></div><div><dt>To make all of it, about</dt><dd class="hv-num">${cr(t.credits)}</dd></div></dl>
        <span class="hv-grow"></span><button type="button" class="hv-cta" data-a="impmake"${g.a}><span>Create the reading</span></button>${g.l}
        <p class="hv-hint c">Nothing is spent now. You choose the voices, then make one chapter or all of them.</p></div></aside></div>`;
  }
  async function impPreview(btn) {
    const im = UI.imp, src = im.src === 'file' ? {file_id: im.file?.file_id} : im.src === 'url' ? {url: im.url} : {text: im.text};
    if (!Object.values(src)[0]) { toast(im.src === 'file' ? 'Choose the file first.' : im.src === 'url' ? 'Type the web address first.' : 'Paste the text first.', true); return; }
    const was = btn?.innerHTML; if (btn) { btn.disabled = true; btn.textContent = 'Reading the book…'; }
    try { const pv = await api('POST', `${A}/project/import/preview`, {...src, title: im.title});
      im.pv = pv; im.title = im.title || pv.title; im.author = pv.author || ''; im.keep = Object.fromEntries(pv.parts.map(x => [x.n, !x.skip])); draw(); readTools(); }
    catch (e) { toast(e.message, true); if (im.file) im.file.err = scrub(e.message); if (btn?.isConnected) { btn.disabled = false; btn.innerHTML = was; } else draw(); }
  }
  function impReset() { UI.imp = {open: false, src: 'file', url: '', text: '', title: '', author: '', file: null, pv: null, keep: {}}; }

  // ------------------------------------------------------------------ the two Studio dialogs: who reads whom, make the audiobook ---
  async function sdOpen(k, back) {
    const dubK = ['dvoices', 'ddl', 'dkeep'].includes(k);
    if (!dubK) { const p = UI.proj; if (!p) return; if (!p.id || projDirty()) { if (!await saveProj()) return; } }
    if (k === 'dkeep') UI.dubKeep = [...(UI.dub?.keep || [])];
    UI.sd = {k, back: back || document.activeElement, data: null, err: ''};
    const host = document.createElement('div'); host.id = 'hvSd'; host.className = 'hv-vphost';
    host.innerHTML = `<div class="hv-vpscrim" data-a="sdclose" aria-hidden="true"></div><div class="hv-vp hv-sd" role="dialog" aria-modal="true" aria-labelledby="hvSdH"></div>`;
    ROOT.appendChild(host); sdPaint(); host.querySelector('[data-a="sdclose"]:not(.hv-vpscrim)')?.focus();
    if (dubK) { UI.sd.data = true; dubPosters(); return; }
    try { UI.sd.data = await api('GET', `${A}/project/${k === 'people' ? 'people' : 'check'}?id=${q(UI.proj.id)}`); }
    catch (e) { if (UI.sd) UI.sd.err = scrub(e.message); }
    sdPaint(); fillCovers();
  }
  function sdClose() { const back = UI.sd?.back, k = UI.sd?.k, inTop = !!back?.closest?.('#hvTopR'); UI.sd = null; $('#hvSd')?.remove(); draw(); topTools();
    (back?.isConnected ? back : $(`${inTop ? '#hvTopR ' : ''}[data-a="sdopen"][data-k="${k}"]`))?.focus(); }
  function sdPaint() {
    const sd = UI.sd, box = $('#hvSd .hv-vp'); if (!sd || !box) return; const p = UI.proj;
    const fk = document.activeElement?.closest?.('#hvSd [data-a]'), key = fk && `[data-a="${fk.dataset.a}"]${fk.dataset.k ? `[data-k="${CSS.escape(fk.dataset.k)}"]` : ''}${fk.dataset.val ? `[data-val="${CSS.escape(fk.dataset.val)}"]` : ''}`;
    box.innerHTML = sd.k === 'people' ? sdPeople(p, sd) : sd.k === 'book' ? sdBook(p, sd) : sd.k === 'dvoices' ? dvVoices() : sd.k === 'ddl' ? dvDownload() : dvKeep();
    if (sd.k === 'ddl') dubPosters();
    (key && box.querySelector(key) || box.querySelector('[data-a="sdclose"]'))?.focus();
  }
  function sdPeople(p, sd) {
    const d = sd.data, head = `<div class="hv-vph"><span class="hv-vt"><h2 class="hv-t" id="hvSdH">Who reads whom</h2><span class="hv-mut hv-sm">${d ? `Hoola found these people in ${d.found === d.total ? `the ${plural(d.total, 'chapter')}` : `${d.found} of ${plural(d.total, 'chapter')}`}. Words in quotes go to the person who says them; everything else is the narrator.` : ''}</span></span>
      <button type="button" class="hv-ib" data-a="sdclose" aria-label="Close">${ic('x', 16)}</button></div>`;
    if (!d) return head + `<div class="hv-sdb"><p class="hv-mut">${sd.err ? esc(sd.err) : 'Looking at the book…'}</p></div>`;
    const cast = castOf(p), order = d.people.map(x => x.name);
    return head + `<div class="hv-sdb">
      ${d.found < d.total ? `<div class="hv-note hv-sdnote"><span>${d.total - d.found} ${d.total - d.found === 1 ? 'chapter has' : 'chapters have'} not been looked at yet, so the people in ${d.total - d.found === 1 ? 'it are' : 'them are'} not here.</span>
        <button type="button" class="hv-btn s dark" data-a="pplfind">Find the people in ${d.total - d.found === 1 ? 'it' : 'them'}</button></div>` : ''}
      ${d.suggestions.map(s => `<div class="hv-note warn hv-sdnote"><span>${esc(s.why)}</span><button type="button" class="hv-btn s dark" data-a="pplmerge" data-k="${esc(s.a)}" data-val="${esc(s.b)}">Make them one</button>
        <button type="button" class="hv-btn s" data-a="pplapart" data-k="${esc(s.a)}" data-val="${esc(s.b)}">Keep apart</button></div>`).join('')}
      ${d.people.map((x, i) => { const v = x.name === 'Narrator' ? (cast.Narrator || p.voice) : x.voice;
        return `<div class="hv-person"><span class="hv-dav l t${i % 4}${x.name === 'Narrator' ? ' n' : ''}${x.small ? ' off' : ''}" aria-hidden="true">${initial(x.name)}</span>
          <span class="hv-vt"><span><b>${esc(x.name)}</b> <span class="hv-mut hv-sm">${x.name === 'Narrator' ? `Everything outside quotes · ${plural(x.chapters.length || d.total, 'chapter')}` : `${plural(x.lines, 'line')}${x.small ? ' · read by the narrator' : ''}`}</span></span>
            <span class="hv-pq serif">${esc(x.quote || '')}</span></span>
          <button type="button" class="hv-play o" data-a="hear" data-id="${esc(x.small ? cast.Narrator : v || '')}" aria-label="Hear ${esc(x.name)}"${v || x.small ? '' : ' disabled'}>${ic('play', 11)}</button>
          ${x.small ? `<span class="hv-vpick off"><span class="hv-dav s n" aria-hidden="true">N</span><span>Narrator’s voice</span></span>`
            : `<button type="button" class="hv-vpick" data-a="pplvoice" data-k="${esc(x.name)}" aria-haspopup="menu" aria-label="Voice for ${esc(x.name)}: ${esc(v ? vname(v) : 'not chosen')}"><span class="hv-dav s" aria-hidden="true">${initial(v ? vname(v) : '?')}</span><span>${esc(v ? vname(v) : 'Choose a voice')}</span>${ic('down', 12)}</button>`}</div>`; }).join('')}
      ${order.length < 2 ? '<p class="hv-mut hv-sm">Only the narrator so far. Find the people in a chapter and the words in quotes go to their voices.</p>' : ''}
      <button type="button" role="switch" class="hv-switchrow" data-a="pplsmall" aria-checked="${!!d.small}"><span class="hv-sw${d.small ? ' on' : ''}" aria-hidden="true"><span></span></span>
        <span class="hv-vt"><b>The narrator reads small parts</b><span class="hv-mut hv-sm">People with fewer than ${d.small_lines || 3} lines keep the narrator’s voice</span></span></button></div>
      <div class="hv-vpf"><span class="hv-mut hv-sm">Changes are read the next time a chapter is made; what is made stays until then.</span><span class="hv-grow"></span><button type="button" class="hv-cta s" data-a="sdclose">Done</button></div>`;
  }
  const KINDS = [['m4b', 'One audiobook file', 'M4B with chapters, the cover and the details. Plays in Apple Books and most audiobook apps.', 12000],
    ['mp3zip', 'MP3, one file per chapter', 'A zip, numbered in order. Plays anywhere.', 24000], ['srt', 'The words with times', 'SRT captions for every chapter, for videos or a read-along page.', 0]];
  function sdBook(p, sd) {
    const d = sd.data, b = bookStat(p), cast = castOf(p), names = [...new Set(Object.values(cast).filter(Boolean).map(vname))];
    const head = `<div class="hv-vph hv-abh">${coverOf(p, 'm')}<span class="hv-vt"><span class="hv-rh"><h2 class="hv-t" id="hvSdH">Make the audiobook</h2><span class="hv-grow"></span><button type="button" class="hv-ib" data-a="sdclose" aria-label="Close">${ic('x', 16)}</button></span>
      <span>${esc([p.title || 'A reading', p.author].filter(Boolean).join(' · '))}</span>
      <span class="hv-mut hv-sm"><span class="hv-num">${plural(b.n, 'chapter')}</span> · <span class="hv-num">${hm(b.secs)}</span> · narrated by AI voices (${esc(names.slice(0, 4).join(', '))})</span></span></div>`;
    if (!d) return head + `<div class="hv-sdb"><p class="hv-mut">${sd.err ? esc(sd.err) : 'Checking the sound…'}</p></div>`;
    const ab = UI.ab, mb = k => { const x = KINDS.find(z => z[0] === k); return x?.[3] ? `about ${Math.max(1, Math.round(b.secs * x[3] / 1e6))} MB` : 'about 1 MB'; };
    const g = gate(d.ready ? '' : `${d.missing.length === 1 ? 'Chapter ' + (d.missing[0] + 1) + ' is' : d.missing.length + ' chapters are'} not made yet. Putting the book together is free.`);
    return head + `<div class="hv-sdb"><div class="hv-fld"><b>As</b><div class="hv-ways col" role="radiogroup" aria-label="File">${KINDS.map(([k, n, note]) =>
        `<button type="button" role="radio" class="hv-way" aria-checked="${ab.fmt === k}" data-a="abfmt" data-val="${k}"><span class="hv-rad" aria-hidden="true"></span><span class="hv-vt"><b>${n}</b><span>${note}</span></span><span class="hv-num hv-mut hv-sm">${mb(k)}</span></button>`).join('')}</div></div>
      <div class="hv-fld"><div class="hv-rh"><b>Sound check</b><span class="hv-grow"></span><span class="hv-mut hv-sm">Measured on Hoola’s server, free</span></div>
        <div class="hv-checks">${d.checks.map(c => `<div class="hv-ckrow"><span class="hv-ck ${c.ok === true ? 'ok' : c.ok === false ? 'warn' : ''}" aria-hidden="true">${ic(c.ok === true ? 'check' : 'warn', 12)}</span>
          <span class="hv-vt"><b>${esc(c.name)}</b><span class="hv-mut hv-sm">${esc(c.note)}</span></span><span class="hv-num hv-sm">${esc(c.value)}</span><span class="hv-sr">${c.ok === true ? 'Passed' : c.ok === false ? 'Needs a look' : 'Not measured'}</span></div>`).join('')}</div>
        ${ab.fmt !== 'srt' ? check('UI.ab.even', 'Even out the loudness of every chapter (right for listening apps)', ab.even) : ''}</div>
      <p class="hv-note">Every file says it was made with AI voices, in its details and as a short spoken line at the start of the book. Only books you wrote or have the right to read aloud.</p></div>
      <div class="hv-vpf">${d.ready ? '' : `<button type="button" class="hv-btn" data-a="abmake">Make ${d.missing.length === 1 ? 'chapter ' + (d.missing[0] + 1) : 'the ' + d.missing.length + ' chapters left'} first</button>`}<span class="hv-grow"></span>
        <button type="button" class="hv-cta s" data-a="abgo"${g.a}><span>Download the audiobook</span></button></div>${g.l}`;
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
      case 'seg': { const v = isNaN(+d.val) || d.val === '' ? d.val : +d.val; setM(d.m, v); if (String(d.m).startsWith('UI.proj')) readTools();
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
      case 'chgview': { chgStop(); UI.chg.view = d.val || ''; if (UI.chg.view === 'compare' && !UI.chg.cmp.some(Boolean)) UI.chg.cmp[0] = UI.chg.out?.voice || UI.chg.voice;
        draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0; return; }
      case 'chgpick': return chgPick(b, UI.chg.voice, v => { UI.chg.voice = v; draw(); });
      case 'chgslot': return chgPick(b, UI.chg.cmp[+d.i], v => { UI.chg.cmp[+d.i] = v; draw(); });
      case 'chgnone': return;
      case 'chgall': UI.chg.start = 0; UI.chg.end = 0; return draw();
      case 'chgpart': return chgPart();
      case 'chghear': UI.chg.hear = d.val; chgMute();
        $$('.hv-chglane').forEach(x => x.classList.toggle('on', x.classList.contains('l-' + (d.val === 'before' ? 'before' : 'after'))));
        $$('[data-a="chghear"]').forEach(x => x.setAttribute('aria-checked', String(x.dataset.val === d.val))); return;
      case 'chgplay': { const h = D.history.find(x => x.id === UI.chg.out?.id) || UI.chg.out; return h && chgPlay(h); }
      case 'chgmake': return act(() => api('POST', `${A}/change`, {...chgBody(), voice: UI.chg.voice}), r => {
        Object.assign(UI.chg, {out: r, fileFor: r?.id || '', hear: 'after'}); side(); draw(); if (r?.id) chgPlay(r); }, b, 'Changing…');
      case 'chgmany': { const vs = UI.chg.cmp.filter(Boolean); return act(() => api('POST', `${A}/change`, {...chgBody(), voices: vs}), r => {
        UI.chg.cmpOut = r; UI.chg.cmpPick = r?.items?.[0]?.id || ''; (r?.failed || []).forEach(f => toast(`${f.name}: ${f.why}`, true)); side(); draw(); }, b, 'Changing…'); }
      case 'chgcpick': UI.chg.cmpPick = id; return draw();
      case 'chgcagain': UI.chg.cmpOut = null; UI.chg.cmpPick = ''; return draw();
      case 'chggo': { const c = UI.chg, pick = c.cmpPick, others = (c.cmpOut?.items || []).map(x => x.id).filter(x => x !== pick);
        return act(async () => { if (c.rm) for (const o of others) await api('DELETE', `${A}/history?id=${q(o)}`); }, () => {
          const h = D.history.find(x => x.id === pick); Object.assign(c, {out: h || null, voice: h?.voice || c.voice, view: '', cmpOut: null, cmpPick: '', hear: 'after', fileFor: c.file ? pick : ''}); side(); draw(); }, b); }
      case 'chgopen': { chgStop(); const h = D.history.find(x => x.id === id); if (!h) return;
        Object.assign(UI.chg, {out: h, voice: voice(h.voice) ? h.voice : UI.chg.voice, view: '', hear: 'after'}); draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0; return; }
      case 'chganother': { const h = D.history.find(x => x.id === id); if (!h?.src) return;
        return chgPick(b, '', async v => { const qr = await quote({job: 'change', seconds: h.src_secs || h.seconds || 60, voice: v});
          if (!confirm(`Change “${h.title || 'this recording'}” into ${voice(v)?.name || 'that voice'}?${qr.credits != null ? ` About ${cr(qr.credits)}.` : ''}`)) return;
          act(() => api('POST', `${A}/change`, {source_of: h.id, voices: [v], denoise: h.denoise !== false, closeness: UI.chg.close, feel: UI.chg.feel}), r => {
            (r?.failed || []).forEach(f => toast(`${f.name}: ${f.why}`, true)); const it = r?.items?.[0];
            if (it) Object.assign(UI.chg, {out: it, voice: v, view: '', hear: 'after', fileFor: ''}); side(); draw(); if (it) chgPlay(it); }); }); }
      case 'chgsrc': { const h = D.history.find(x => x.id === id); return blobUrl(`${A}/${h?.kind === 'cleanup' ? 'cleanup' : 'change'}/source?id=${q(id)}`).then(u => play('src:' + id, u, `${h?.title || 'Change'} · your recording`)).catch(e => toast(e.message, true)); }
      case 'chgfilt': UI.chg.filt = d.val || ''; return draw();
      case 'clview': { chgStop(); UI.cl.view = d.val || ''; draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0; return; }
      case 'clnew': chgStop(); Object.assign(UI.cl, {file: null, heard: null, out: null, kind: '', fileFor: '', listening: false}); return draw();
      case 'clkind': { const k = CL_KINDS.find(x => x[0] === d.val); if (!k) return; Object.assign(UI.cl, {kind: k[0], gap: 1, ...k[3]}); draw(); return clPrice(); }
      case 'clrun': return act(() => api('POST', `${A}/cleanup`, clBody()), j => { chgStop(); UI.cl.job = j; draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0; clPoll(); }, b, 'Starting…');
      case 'clstop': { const j = UI.cl.job; if (!j) return; j.stop = true; b.disabled = true; b.textContent = 'Stopping after this step…';
        return api('POST', `${A}/cleanup/stop`, {id: j.id}).catch(e => toast(e.message, true)); }
      case 'clplay': { const h = D.history.find(x => x.id === UI.cl.out?.id) || UI.cl.out; return h && chgPlay(h); }
      case 'clhear': UI.cl.hear = d.val; chgMute();
        $$('.hv-chglane').forEach(x => x.classList.toggle('on', x.classList.contains('l-' + (d.val === 'before' ? 'before' : 'after'))));
        $$('[data-a="clhear"]').forEach(x => x.setAttribute('aria-checked', String(x.dataset.val === d.val))); return;
      case 'clpart': { const u = UI.cl.file?.url; return u ? play('clsrc', u, 'Your recording') : null; }
      case 'clopen': case 'clagain': { chgStop(); const h = D.history.find(x => x.id === id); if (!h) return;
        const fx = h.fixes || {}, stronger = d.a === 'clagain' && d.val === 'stronger';
        Object.assign(UI.cl, {out: h, view: '', hear: 'after', kind: '', heard: h.before?.found ? h.before : null, fileFor: h.id,
          file: {name: h.title || 'Clean-up', secs: h.src_secs || 0, from: h.src ? h.id : ''}, secs: h.src_secs || 0,
          ...(fx.noise ? {denoise: !!fx.denoise, noise: fx.noise, voice: !!fx.voice, level: !!fx.level, target: fx.target || 'podcast', silence: !!fx.silence, gap: fx.gap || 1, people: !!fx.people, music: !!fx.music} : {})});
        if (stronger) { UI.cl.denoise = true; UI.cl.noise = fx.noise === 'light' ? 'medium' : 'strong';
          return act(() => api('POST', `${A}/cleanup`, clBody()), j => { UI.cl.job = j; draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0; clPoll(); }, b, 'Starting…'); }
        draw(); const vw = $('#hvView'); if (vw) vw.scrollTop = 0;
        if (d.a === 'clagain') toast('Your recording is ready to clean again. Change the fixes and tap Clean it.');
        return; }
      case 'clsound': { const list = D.history.filter(h => h.kind !== 'dub').slice(0, 40);
        return menu(b, [{header: 'Clean one of your sounds'}, {search: 'Find a sound', empty: 'Nothing matches'}, ...list.map(h => ({label: h.title || KIND[h.kind] || 'Sound', sub: [KIND[h.kind] || '', h.seconds ? secs(h.seconds) : ''].filter(Boolean).join(' · '),
          run: () => { chgStop(); Object.assign(UI.cl, {file: {name: h.title || 'Sound', secs: h.seconds || 0, sound: h.id}, secs: h.seconds || 0, heard: null, out: null, kind: '', fileFor: '', view: ''}); draw(); clListen(); }}))], {width: 340}); }
      case 'clfilt': UI.cl.filt = d.val || ''; return draw();
      case 'pickcast': return cpOpen(+d.n);
      case 'castopen': return cpOpen(0);
      case 'cpclose': return cpClose();
      case 'cpslot': UI.dlg.cp.slot = +d.n; return cpPaint();
      case 'cpuse': { const cp = UI.dlg.cp, cast = UI.dlg.cast, me = cast[cp.slot], v = voice(id); if (!v?.ready) return;
        const other = cast.find((c, i) => i !== cp.slot && c.voice === id); if (other) other.voice = me.voice;
        me.voice = id; cpPaint(); return toast(other ? `${v.name} speaks for ${me.name} now, and ${other.name} takes ${vname(other.voice)}.` : `${v.name} speaks for ${me.name}.`); }
      case 'cpall': UI.queue = []; { const ids = UI.dlg.cast.map(c => c.voice).filter(Boolean); if (!ids.length) return;
        const hear = async i => { if (i >= ids.length) return; try { const a = $('#hvAudio'); await play('', await blobUrl(`${A}/voice/preview?id=${q(ids[i])}&lang=${q(UI.dlg.lang && UI.dlg.lang !== 'auto' ? UI.dlg.lang : 'en')}`), `${UI.dlg.cast[i].name} · ${vname(ids[i])}`);
          a?.addEventListener('ended', () => hear(i + 1), {once: true}); } catch (e) { toast(e.message, true); } }; return hear(0); }
      case 'pickwho': { const n = +d.n; UI.dlg.sel = n; return choose(b, {title: 'Who says this line', cur: UI.dlg.lines[n].speaker, list: UI.dlg.cast.map(c => ({v: c.name, label: c.name, sub: vname(c.voice)})), onPick: v => { UI.dlg.lines[n].speaker = v; draw(); }}); }
      case 'dltone': return menu(b, [{header: `Tone of line ${UI.dlg.sel + 1}`}, ...TONES.map(t => ({label: t[0].toUpperCase() + t.slice(1), sub: `[${t}] · ${TONE_NOTE[t] || ''}`, run: () => dlToneAt(t)}))]);
      case 'dlpause': { const l = UI.dlg.lines[UI.dlg.sel]; if (!l) return; return menu(b, [{header: `After line ${UI.dlg.sel + 1}`}, ...PAUSES.map(([v, n]) => ({label: n, check: +l.pause === v, run: () => { l.pause = v; draw(); }}))]); }
      case 'dlcut': { const n = UI.dlg.sel, l = UI.dlg.lines[n]; if (!l) return; if (!n) return toast('The first line has nothing to cut into.');
        l.cut = !l.cut; draw(); return toast(l.cut ? `${l.speaker} cuts in on line ${n + 1}.` : `Line ${n + 1} waits its turn again.`); }
      case 'dlswap': { const [x, y] = dlNames(); UI.dlg.lines.forEach(l => { l.speaker = l.speaker === x ? y : l.speaker === y ? x : l.speaker; }); draw(); return toast(`${x} and ${y} swapped their lines.`); }
      case 'dlmove': { const n = UI.dlg.sel, m = n + (+d.val), ls = UI.dlg.lines; if (m < 0 || m >= ls.length) return; [ls[n], ls[m]] = [ls[m], ls[n]]; UI.dlg.sel = m; draw(); return $(`.hv-dl[data-n="${m}"] [data-a="dlmove"][data-val="${d.val}"]`)?.focus() || dlFocus(m, true); }
      case 'dlstart': { const st = DLG_STARTS[+d.val]; if (!st) return; const names = dlNames();
        UI.dlg.lines = st[3].map(([w, t]) => ({speaker: names[w] || names[0], text: t, pause: 0, cut: false})); UI.dlg.title = st[0]; UI.dlg.sel = 0; draw();
        const t = $('#hvLt0'); if (t) { t.focus(); const k = t.value.indexOf('['), e = t.value.indexOf(']', t.value.indexOf('[YOUR')); const at = t.value.indexOf('[YOUR'); if (at >= 0) t.setSelectionRange(at, e + 1); else if (k >= 0) t.setSelectionRange(t.value.length, t.value.length); } return; }
      case 'dlone': { const n = +d.n, st = dlState(n), l = UI.dlg.lines[n]; if (!st.one) return;
        return act(() => api('POST', `${A}/dialogue/${q(st.t.id)}/line`, {n: st.k, text: l.text, speaker: l.speaker}),
          r => { UI.dlg.out = [r, ...UI.dlg.out.filter(x => x.id !== r.id)].slice(0, 8); side(); draw(); play(r.id); toast(`Line ${n + 1} made again · take ${r.take}.`); }, b, 'Making…'); }
      case 'dlvoices': { const t = dlTakes().find(x => x.id === id); return saveFile(`${A}/dialogue/${q(id)}/voices`, `${(t?.title || 'talk').replace(/[^\w .-]+/g, '_').slice(0, 50)} - voices.zip`); }
      case 'dlsubs': { const t = dlTakes().find(x => x.id === id), nm = (t?.title || 'talk').replace(/[^\w .-]+/g, '_').slice(0, 50);
        return menu(b, [{header: t?.timing_est ? 'Times shared out by line length' : 'Subtitles'}, {label: 'SRT', sub: 'For most video editors', run: () => saveFile(`${A}/dialogue/${q(id)}/subtitles?fmt=srt`, `${nm}.srt`)},
          {label: 'VTT', sub: 'For the web', run: () => saveFile(`${A}/dialogue/${q(id)}/subtitles?fmt=vtt`, `${nm}.vtt`)}]); }
      case 'podagain': return $('form[data-f="podcast"]')?.requestSubmit();
      case 'poduse': { const r = UI.dlg.pod.draft; if (!r) return; UI.dlg.lines = (r.lines || []).map(l => ({speaker: l.speaker, text: l.text, pause: 0, cut: false})); const names = new Set(dlNames());
        UI.dlg.lines.forEach(l => { if (!names.has(l.speaker) && UI.dlg.cast.length < 6) { UI.dlg.cast.push({name: l.speaker, voice: (D.voices.find(x => x.ready) || {}).id || ''}); names.add(l.speaker); } });
        UI.dlg.title = r.title || ''; UI.dlg.sel = 0; UI.dlg.podOpen = false; draw(); return toast('The script is in. Change any line, then make the talk.'); }
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
          sort: [['popular', 'Most used'], ['trending', 'Trending'], ['newest', 'Newest'], ['most_added', 'Most added']], vsort: [['', 'Hoola order'], ['name', 'A to Z']]}[k];
        if (k === 'vsort') return choose(b, {title: 'Order', cur: UI.vsort, list: opts.map(o => ({v: o[0], label: o[1]})), onPick: v => { UI.vsort = v; draw(); }});
        return choose(b, {title: {lang: 'Language', gender: 'Gender', age: 'Age', accent: 'Accent', use: 'Use', sort: 'Sort'}[k], find: k === 'lang' ? 'Search languages' : '', cur: f[k],
          list: opts.map(o => Array.isArray(o) ? {v: o[0], label: o[1]} : o), onPick: v => { f[k] = v; if (UI.vtab === 'shared') libLoad(); else draw(); }}); }
      case 'vsel': UI.vsel = id; draw(); return $(`[data-a="vsel"][data-id="${CSS.escape(id)}"]`)?.focus();
      case 'vtab': UI.vtab = d.val; UI.vset = ''; if (d.val === 'shared') libLoad(); draw(); return $(`[data-a="vtab"][data-val="${d.val}"]`)?.focus();
      case 'vset': UI.vset = UI.vset === d.val ? '' : d.val; draw(); return $(`[data-a="vset"][data-val="${d.val}"]`)?.focus();
      case 'videa': UI.vf.q = d.val; draw(); return $('#hvVq')?.focus();
      case 'vfav': return vFav(id, b);
      case 'vlang': return choose(b, {title: 'Every sample speaks', find: 'Search languages', cur: UI.vlang || (S.lang !== 'auto' ? S.lang : '') || 'en', list: langList(false).map(l => ({...l, why: ''})),
        onPick: v => { UI.vlang = v; topTools(); draw(); }});
      case 'vtryp': UI.tryText = (VTRY.find(x => x[0] === d.val) || [0, ''])[1]; draw(); return $('#hvTry')?.focus();
      case 'vusein': { const v = voice(id); if (!v) return;
        return menu(b, [{header: 'Use ' + v.name}, {label: 'In Speech', run: () => { S.voice = id; toast(`${v.name} is your voice now.`); go('speech'); }},
          {label: 'In Dialogue, as the next speaker', run: () => { const c = UI.dlg.cast.find(x => !x.voice) || UI.dlg.cast[UI.dlg.cast.length - 1]; if (c) c.voice = id; toast(`${v.name} speaks as ${c?.name || 'a speaker'}.`); go('dialogue'); }},
          {label: 'In the Vocal chat', run: () => { S.voice = id; toast(`The Vocal chat speaks with ${v.name} now.`); go('chat'); }},
          {label: 'As your default voice', run: () => { S.voice = id; setDef('voice', id); toast(`${v.name} is your default voice.`); }}]); }
      case 'vcmp': UI.cmp = UI.cmp.includes(id) ? UI.cmp.filter(x => x !== id) : [...UI.cmp, id].slice(-4); UI.cmpPick = ''; draw(); return $(`[data-a="vcmp"][data-id="${CSS.escape(id)}"]`)?.focus();
      case 'vlike': { const v = voice(id); if (!v) return; UI.way = 'design'; UI.yv = 'make'; UI.design.previews = []; UI.design.pick = '';
        UI.design.desc = [v.tone, v.age === 'middle' ? 'middle-aged' : v.age, v.gender, v.accent ? `with a ${v.accent} accent` : '', v.use ? `for ${v.use.toLowerCase()}` : ''].filter(Boolean).join(', ');
        UI.design.gender = v.gender || ''; toast('Describe what to change, then make three to hear.'); return go('mine'); }
      case 'cmpclear': UI.cmp = []; UI.cmpPick = ''; UI.cmpOut = {}; return draw();
      case 'cmprm': UI.cmp = UI.cmp.filter(x => x !== id); delete UI.cmpOut[id]; return UI.cmp.length ? draw() : go('voices');
      case 'cmphear': return cmpHear(UI.cmp.indexOf(id), false);
      case 'cmpall': return cmpHear(0, true);
      case 'cmpblind': UI.cmpBlind = !UI.cmpBlind; UI.cmpPick = ''; return draw();
      case 'cmplike': UI.cmpLike = UI.cmpLike.includes(id) ? UI.cmpLike.filter(x => x !== id) : [...UI.cmpLike, id]; return draw();
      case 'cmppick': { if (UI.cmpPick === id) { S.voice = id; toast(`${vname(id)} is your voice now.`); return go('speech'); } UI.cmpPick = id; draw(); toast(`You chose ${vname(id)}.`); return; }
      case 'cmpwords': { const t = (UI.cmpText || '').trim(), ids = UI.cmp.filter(x => voice(x)?.ready); if (!t || !ids.length) return;
        return act(async () => { for (const vid of ids) { const r = await api('POST', `${A}/tts`, {text: t, voice: vid, lang: 'auto', style: S.style, speed: 1, takes: 1, engine: 'auto', format: 'mp3', rules: true});
            const it = (r.items || [r])[0]; if (it?.id) UI.cmpOut[vid] = it.id; } return true; }, () => { draw(); cmpHear(0, true); }, b, 'Making…'); }
      case 'libmore': return libLoad(true);
      case 'libadd': { const v = libVoice(id); if (!v) return;
        return act(() => api('POST', `${A}/library/add`, {id: v.id, owner: v.owner, name: v.name}), r => { toast(`${v.name} is in your voices now.`); UI.vtab = 'mine'; UI.vsel = r?.id || ''; side(); draw(); }, b, 'Adding…'); }
      case 'tryv': { const v = voice(UI.vsel), t = (UI.tryText || '').trim(); if (!v) return; if (!t) { toast('Type a few words first.'); return $('#hvTry')?.focus(); }
        return act(() => api('POST', `${A}/tts`, {text: t, voice: v.id, lang: 'auto', style: S.style, speed: 1, takes: 1, engine: 'auto', format: S.format, rules: true}),
          r => { const it = (r.items || [])[0]; draw(); if (it) play(it.id, '', `${v.name} · your words`); }, b, 'Making…'); }
      case 'way': UI.way = d.val; UI.yv = 'make'; return draw();
      case 'yvhome': UI.yv = 'home'; UI.ren = ''; draw(); return $('#hvView [data-a="yvmake"]')?.focus();
      case 'yvmake': UI.way = d.val || 'record'; UI.yv = 'make'; draw(); return $('#hvView .hv-yvpick [aria-checked="true"]')?.focus();
      case 'yvopen': UI.yv = 'detail'; UI.mv = id; UI.ren = ''; UI.tryText = ''; draw(); return $('#hvView .hv-yvback')?.focus();
      case 'yvf': UI.yvf = d.val; draw(); return $(`#hvView [data-a="yvf"][data-val="${d.val}"]`)?.focus();
      case 'yvren': UI.ren = id; return draw();
      case 'yvrenx': UI.ren = ''; return draw();
      case 'yvcons': b.disabled = true; return blobUrl(`${A}/voice/consent?id=${q(id)}`).then(u => play('cons:' + id, u, 'Your consent recording')).catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; });
      case 'yvchange': { const v = voice(id); if (!v?.ready || v.engine !== 'gemini') return toast(v?.engine === 'gemini' ? 'This voice is not ready yet.' : 'Only Standard voices and your Google-made voices can be changed.', true);
        UI.way = 'remix'; UI.yv = 'make'; UI.remix = {base: id, change: '', name: '', made: ''}; UI.rxp = {}; return draw(); }
      case 'yvdef': { const v = voice(id); if (!v || (D.settings || {}).voice === id) return; S.voice = id; return setDef('voice', id).then(() => { D.settings = {...(D.settings || {}), voice: id}; draw(); }); }
      case 'yvdl': { const v = voice(id); if (!v?.ready) return toast('This voice is not ready yet.', true);
        return saveFile(`${A}/voice/preview?id=${q(id)}&lang=${q(vHearLang(v))}`, `${(v.name || 'voice').replace(/[^\w .-]+/g, '_').slice(0, 40)} sample.wav`); }
      case 'yvrm': { const v = voice(id); if (!v) return;
        return confirm(`Delete ${v.name}? Its recordings${v.kind === 'clone' ? ', including your consent recording,' : ''} are deleted. Sounds already made with it are kept.`)
          && act(() => api('DELETE', `${A}/voice?id=${q(id)}`), () => { UI.yv = 'home'; UI.mv = ''; if (S.voice === id) S.voice = (D.voices.find(x => x.ready) || {}).id || ''; toast(`${v.name} is deleted.`); side(); draw(); }); }
      case 'yvsounds': UI.side = {...(UI.side || {}), q: vname(UI.mv)}; return go('sounds');
      case 'recplay': { const sl = UI.clone.consent; return sl?.url ? play('rec:consent', sl.url, 'Your recording') : null; }
      case 'recagain': if (UI.clone.consent?.url) URL.revokeObjectURL(UI.clone.consent.url); UI.clone.consent = null; UI.clone.ok = false; draw(); return $('#hvView [data-a="rec"]')?.focus();
      case 'dadd': UI.design.desc = [UI.design.desc.trim().replace(/[.,]$/, ''), d.val].filter(Boolean).join(', ').slice(0, 300); draw(); return $('#hvDDesc')?.focus();
      case 'dref': UI.design.desc = [UI.design.desc.trim().replace(/[.,]$/, ''), d.val.toLowerCase()].filter(Boolean).join(', ').slice(0, 300); UI.design.previews = []; UI.design.pick = '';
        toast('Added to the description. Make three new options to hear it.'); draw(); return $('[data-qbtn="design"]')?.focus();
      case 'rxpick': { const p = UI.rxp; p[d.k] = p[d.k] === d.val ? '' : d.val;
        const parts = YRX.map(([g]) => p[g]).filter(Boolean).map(x => /English|Neutral/.test(x) ? `with ${/^Neutral/.test(x) ? 'a neutral' : 'an ' + x} accent` : x.toLowerCase());
        UI.remix.change = parts.length ? `Same voice, but ${parts.join(', ')}` : ''; draw(); return $(`#hvView [data-a="rxpick"][data-k="${d.k}"][data-val="${d.val}"]`)?.focus(); }
      case 'rxkeep': { const vid = UI.remix.made; UI.remix = {base: UI.remix.base, change: '', name: '', made: ''}; UI.rxp = {}; UI.yv = 'detail'; UI.mv = vid; toast('The new voice is kept.'); return draw(); }
      case 'rxdrop': { const vid = UI.remix.made; return act(() => api('DELETE', `${A}/voice?id=${q(vid)}`), () => { UI.remix.made = ''; toast('Removed. Change the words and try again.'); side(); draw(); }); }
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
      case 'mvmenu': { const v = voice(id); return menu(b, [{label: 'Open', run: () => { UI.yv = 'detail'; UI.mv = id; UI.ren = ''; draw(); }}, {label: 'Use this voice', run: () => { S.voice = id; go('speech'); }, disabled: !v?.ready},
          {label: 'Rename', run: () => { UI.yv = 'detail'; UI.mv = id; UI.ren = id; draw(); }},
          {label: 'Change this voice', run: () => { UI.way = 'remix'; UI.yv = 'make'; UI.remix = {base: id, change: '', name: '', made: ''}; UI.rxp = {}; draw(); }, disabled: !v?.ready || v.engine !== 'gemini'}, {sep: true},
          {label: 'Remove', icon: 'trash', danger: true, run: () => confirm('Remove this voice? Its recordings are deleted. Sounds already made are kept.') && act(() => api('DELETE', `${A}/voice?id=${q(id)}`), () => { if (UI.mv === id) UI.yv = 'home'; side(); draw(); })}]); }
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
      case 'tag': return tagAt(d.val);
      case 'tonemenu': return menu(b, [{header: 'Add a tone'}, ...TONES.map(t => ({label: t[0].toUpperCase() + t.slice(1), sub: `[${t}] · ${TONE_NOTE[t] || ''}`, run: () => tagAt(t)}))]);
      case 'spmode': SP.mode = d.val === 'lines' ? 'lines' : 'whole'; store.set('hv.spmode', SP.mode); SP.sel = 0; return draw();
      case 'spmore': SP.more = !SP.more; store.set('hv.spmore', SP.more); { const y = $('.hv-spform')?.scrollTop; draw(); if (y != null && $('.hv-spform')) $('.hv-spform').scrollTop = y; }
        return $('[data-a="spmore"]')?.focus();
      case 'spstart': S.text = d.val; draw(); { const ta = $('#hvText'); if (ta) { const k = ta.value.indexOf('[YOUR'); ta.focus(); if (k >= 0) ta.setSelectionRange(k, ta.value.indexOf(']', k) + 1); } } return;
      case 'spimport': return pickFiles('.txt,.md,text/plain', false).then(async fs => { const f = fs[0]; if (!f) return;
        if (f.size > 2 * 1024 * 1024) return toast('That file is over 2 MB. Paste the words instead.', true);
        const t = (await f.text()).replace(/\r\n?/g, '\n').trim(); if (!t) return toast('That file has no words in it.', true);
        if (S.text.trim() && !confirm('Put the words of this file in place of what is written now?')) return;
        S.text = t.slice(0, D.limits?.characters || 100000); draw(); toast(`${plural(words(S.text), 'word')} imported from ${f.name}.`); });
      case 'spimprove': { const ta = $('#hvText'); if (!S.text.trim()) { ta?.focus(); return toast('Write a few words first.'); }
        const use = t => { S.text = String(t).slice(0, D.limits?.characters || 100000); draw(); $('#hvText')?.focus(); toast('Words updated: listen, then keep or change them.'); };
        if (window.HoolaImprove?.ui) return window.HoolaImprove.ui.open(S.text, {section: 'voice', onUse: use});
        b.disabled = true;
        return api('POST', '/api/prompting/understand', {text: S.text, section: 'voice'}).then(r => { const t = r?.prompt || r?.text; if (t) use(t); else toast('No better words came back. Your words are kept.'); })
          .catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'sayas': { const ta = d.k === 'line' ? $(`.hv-lnt[data-line="${SP.sel}"]`) : $('#hvText');
        const picked = ta && ta.selectionEnd > ta.selectionStart ? ta.value.slice(ta.selectionStart, ta.selectionEnd).trim().slice(0, 60) : '';
        const word = (prompt('Which word should be read your way?', picked) || '').trim(); if (!word) return;
        const say = (prompt(`How should “${word}” be said? Write it the way it sounds, like “KAA-joo KUT-lee”.`, '') || '').trim(); if (!say) return;
        return act(() => api('POST', `${A}/rule`, {word, say, lang: S.lang && S.lang !== 'auto' ? S.lang : ''}), () => { side(); draw(); toast(`“${word}” will be read your way.`); }); }
      case 'sptweak': if (d.val === 'slower') { S.speed = Math.max(0.7, Math.round((+S.speed - 0.1) * 20) / 20); toast(`Pace is ${(+S.speed).toFixed(2)}x now. Press Speak it to hear it.`); }
        else if (d.val in (D.styles || {})) { S.style = d.val; toast(`Style is ${styleName(d.val)} now. Press Speak it to hear it.`); }
        draw(); return $('[data-qbtn="speech"]')?.focus();
      case 'spreuse': { const h = D.history.find(x => x.id === id); if (!h?.text) return;
        if (S.text.trim() && S.text !== h.text && !confirm('Put the words of that sound in place of what is written now?')) return;
        S.text = h.text; if (h.voice && voice(h.voice)?.ready) S.voice = h.voice; if (h.style && h.style in (D.styles || {})) S.style = h.style; SP.mode = 'whole'; draw(); return $('#hvText')?.focus(); }
      case 'vpopen': return vpOpen(d.k);
      case 'vpclose': return vpClose();
      case 'vpf': SP.vp.f = d.val; return vpPaint();
      case 'vpuse': { const v = voice(id); if (!v?.ready) return;
        const forLine = SP.vp?.k === 'line'; if (forLine) { if (id === S.voice) delete SP.lv[SP.sel]; else SP.lv[SP.sel] = id; } else S.voice = id;
        vpClose(); draw(); return toast(forLine ? `${v.name} reads line ${SP.sel + 1}.` : `${v.name} is the voice now.`); }
      case 'vpgo': vpClose(); if (d.val === 'voices') return go('voices'); UI.way = d.val === 'design' ? 'design' : 'record'; UI.yv = 'make'; return go('mine');
      case 'lnsel': return lnSel(+d.val);
      case 'lnadd': S.text = S.text.replace(/\n+$/, '') + (S.text.trim() ? '\n' : ''); SP.sel = spLines().length - 1; draw(); return $(`.hv-lnt[data-line="${SP.sel}"]`)?.focus();
      case 'lnremove': { const ls = spLines(); if (ls.length < 2) return; ls.splice(SP.sel, 1); S.text = ls.join('\n');
        const lv = {}; Object.entries(SP.lv).forEach(([k, v]) => { const n = +k; if (n < SP.sel) lv[n] = v; else if (n > SP.sel) lv[n - 1] = v; }); SP.lv = lv;
        const at = {}; Object.entries(SP.at).forEach(([k, v]) => { const n = +k; if (n < SP.sel) at[n] = v; else if (n > SP.sel) at[n - 1] = v; }); SP.at = at; lnSave();
        SP.sel = Math.max(0, SP.sel - 1); return draw(); }
      case 'lntone': { const ls = spLines(), {rest} = toneOf(ls[SP.sel] || ''); lnSet(SP.sel, d.val === 'natural' ? rest : `[${d.val}] ${rest}`); return draw(); }
      case 'lnvoice0': delete SP.lv[SP.sel]; return draw();
      case 'lnuse': { const line = spLines()[SP.sel] || ''; SP.made[lineKey(SP.sel, line)] = id; SP.at[SP.sel] = id; lnSave(); return draw(); }
      case 'lnmake': { const i = +d.val; SP.sel = i; b.disabled = true; b.textContent = 'Making…';
        return (async () => { try { const it = await lnMake(i); await load(); side(); draw(); if (it) play(it.id); } catch (e) { toast(e.message, true); noCredit(e); if (b.isConnected) { b.disabled = false; b.textContent = 'Make'; } } })(); }
      case 'lnmakeall': { const todo = lnTodo(); b.disabled = true;
        return (async () => { for (let k = 0; k < todo.length; k++) { const [, i] = todo[k]; const bt = $('[data-a="lnmakeall"]'); if (bt) bt.innerHTML = `<span>Making line ${i + 1} · ${k + 1} of ${todo.length}…</span>`;
          try { await lnMake(i); } catch (e) { toast(`Line ${i + 1}: ${e.message}`, true); noCredit(e); break; } }
        await load(); side(); draw(); })(); }
      case 'lnplayall': { const ids = spLines().map((l, i) => lineState(i, l).row?.id).filter(Boolean); if (!ids.length) return; UI.queue = ids.slice(1); return play(ids[0]); }
      case 'lnjoin': { const ids = spLines().map((l, i) => l.trim() ? lineState(i, l).row?.id : null).filter(Boolean);
        return act(() => api('POST', `${A}/join`, {ids, format: S.format}), r => { side(); draw(); toast(`One file made from ${plural(ids.length, 'line')}. It is in Your sounds.`); if (r?.id) download(r.id); }, b, 'Joining…'); }
      case 'play': return id.startsWith('line:') ? playLine(+id.slice(5)) : play(id);
      case 'keep': return keep(id);
      case 'cwidth': return setWidth(d.val);
      case 'unfold': UI.peek = true; return setWidth(UI.cw < 550 ? 'narrow' : UI.cw > 760 ? 'wide' : 'balanced', UI.cw);
      case 'openchat': { const c = (UI.recent || []).find(x => x.id === id); C.title = c?.title || 'Vocal chat'; if (PAGE !== 'chat') go('chat'); return openChat(id); }
      case 'compare': { const ids = String(d.val || '').split(',').filter(Boolean); if (!ids.length) return; UI.queue = ids.slice(1); return play(ids[0]); }
      case 'closebar': $('#hvAudio').pause(); $('#hvBar').hidden = true; return;
      case 'hear': { const v = voice(id) || libVoice(id); b.disabled = true;
        const path = libVoice(id) && UI.vtab === 'shared' ? (v.preview ? (String(v.preview).startsWith('/api/') ? v.preview : `${A}/library/preview?url=${q(v.preview)}`) : '') : `${A}/voice/preview?id=${q(id)}&lang=${q(d.lang || (v && voice(id) ? vHearLang(v) : (S.lang === 'auto' ? ((v?.langs || [])[0] || 'en') : S.lang)))}`;
        if (!path) { b.disabled = false; return toast('This voice has no sample to hear.'); }
        return blobUrl(path).then(u => play('hear:' + id, u, `${v?.name || 'Voice'} · sample`)).catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'usev': S.voice = id; toast(`${vname(id)} is your voice now.`); return go('speech');
      case 'rec': return recStart(d.k);
      case 'recstop': return REC[d.k]?.mr.stop();
      case 'pickrec': return pickFiles('audio/*', false).then(fs => fs[0] && recFile(d.k, fs[0], 0));
      case 'pickfile': return pickFiles(d.accept || '*/*', false).then(fs => fs[0] && pageFile(d.k, fs[0]));
      case 'dpick': UI.design.pick = d.val; return draw();
      case 'dsave': return act(() => api('POST', `${A}/voice/design/save`, {pid: UI.design.pick, name: UI.design.name || 'My designed voice'}),
        r => { UI.design = {desc: '', gender: '', previews: [], pick: '', name: '', lang: UI.design.lang}; if (r?.id) { UI.yv = 'detail'; UI.mv = r.id; } toast('Voice saved.'); side(); draw(); }, b, 'Saving…');
      case 'rxchip': UI.remix.change = [UI.remix.change.trim(), d.val.toLowerCase()].filter(Boolean).join(', '); return draw();
      case 'rmrule': return act(() => api('DELETE', `${A}/rule?id=${q(id)}`));
      case 'dictimp': UI.dict.imp = !UI.dict.imp; return draw();
      case 'podopen': UI.dlg.podOpen = true; draw(); return $('#hvView [data-f="podcast"] [role="radio"][aria-checked="true"]')?.focus();
      case 'podclose': UI.dlg.podOpen = false; return draw();
      case 'dladd': { const ls = UI.dlg.lines, last = ls[ls.length - 1]; ls.push({speaker: UI.dlg.cast.find(c => c.name !== last?.speaker)?.name || UI.dlg.cast[0]?.name || 'Speaker', text: '', pause: 0, cut: false});
        UI.dlg.sel = ls.length - 1; draw(); return dlFocus(UI.dlg.sel); }
      case 'dlrm': { const n = +d.n; UI.dlg.lines.splice(n, 1); if (UI.dlg.lines[0]) UI.dlg.lines[0].cut = false; UI.dlg.sel = Math.max(0, Math.min(n, UI.dlg.lines.length - 1)); draw(); return dlFocus(UI.dlg.sel, true); }
      case 'castadd': { const rv = D.voices.filter(v => v.ready); UI.dlg.cast.push({name: `Speaker ${UI.dlg.cast.length + 1}`, voice: (rv[UI.dlg.cast.length % Math.max(1, rv.length)] || {}).id || ''}); return draw(); }
      case 'castrm': { const gone = UI.dlg.cast.splice(+d.n, 1)[0]; UI.dlg.lines.forEach(l => { if (l.speaker === gone.name) l.speaker = UI.dlg.cast[0].name; }); return draw(); }
      case 'dlgmake': { const dd2 = UI.dlg, cast = Object.fromEntries(dd2.cast.map(c => [c.name, c.voice]));
        return act(() => api('POST', `${A}/dialogue`, {lines: dd2.lines.filter(l => (l.text || '').trim()).map(l => ({speaker: l.speaker, text: l.text, pause: +l.pause || 0, cut: !!l.cut})), cast, lang: dd2.lang || 'auto', style: dd2.style, engine: 'auto', mode: dd2.mode, reactions: !!dd2.reactions, music: dd2.music ? 'soft' : ''}),
          r => { if (r?.id) dd2.out = [r, ...dd2.out.filter(x => x.id !== r.id)].slice(0, 8); side(); draw(); if (r?.id) play(r.id); toast(`The talk is ready · take ${r?.take || 'A'}.`); }, b, 'Making…'); }
      case 'impopen': if (PAGE !== 'studio') { UI.imp.open = true; return go('studio'); } UI.imp.open = true; draw(); return readTools();
      case 'impclose': impReset(); draw(); return readTools();
      case 'impagain': UI.imp.pv = null; UI.imp.file = null; UI.imp.keep = {}; return draw();
      case 'imptick': UI.imp.keep[+d.n] = !UI.imp.keep[+d.n]; draw(); return $(`[data-a="imptick"][data-n="${+d.n}"]`)?.focus();
      case 'impmake': { const im = UI.imp, src = im.src === 'file' ? {file_id: im.file?.file_id} : im.src === 'url' ? {url: im.url} : {text: im.text};
        const keep = im.pv.parts.filter(x => im.keep[x.n]).map(x => x.n);
        return act(() => api('POST', `${A}/project/import`, {...src, title: im.title, author: im.author, keep, cover: im.pv.cover || ''}),
          r => { impReset(); UI.cast = null; UI.chN = 0; UI.edited = {}; UI.para = null; UI.editing = false; UI.proj = JSON.parse(JSON.stringify(r)); go('reading'); }, b, 'Creating…'); }
      case 'newproj': UI.cast = null; UI.chN = 0; UI.edited = {}; UI.para = null; UI.editing = true; UI.proj = {id: '', title: '', voice: S.voice, lang: S.lang === 'auto' ? 'en' : S.lang, chapters: [{title: 'Chapter 1', text: ''}]}; return go('reading');
      case 'proj': UI.cast = null; UI.chN = 0; UI.edited = {}; UI.para = null; UI.editing = false; UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === id) || null)); return go('reading');
      case 'chsel': UI.chN = +d.n; UI.para = null; UI.editing = false; draw(); return $('.hv-pgscroll')?.scrollTo?.(0, 0);
      case 'edit': UI.editing = !UI.editing; UI.para = null; draw(); if (UI.editing) $('#hvChX')?.focus(); else $('[data-a="edit"]')?.focus(); return;
      case 'parasel': UI.para = UI.para === +d.k ? null : +d.k; draw(); return $(`[data-a="parasel"][data-k="${+d.k}"]`)?.focus();
      case 'paraplay': return blobUrl(`${A}/project/para?id=${q(UI.proj.id)}&n=${UI.chN}&k=${+d.k}`).then(u => play(`para:${UI.chN}:${+d.k}`, u, `Chapter ${UI.chN + 1} · paragraph ${+d.k + 1}`), e => toast(e.message, true));
      case 'parawho': { const pr = paraList(UI.proj.chapters[UI.chN])[+d.k], names = Object.keys(castOf(UI.proj));
        return choose(b, {title: 'Who says it', cur: pr.who, list: names.map(x => ({v: x, label: x === 'Narrator' ? 'The narrator' : x, sub: vname(castOf(UI.proj)[x])})),
          onPick: who => saveProj().then(ok => ok && act(() => api('PUT', `${A}/project/para`, {id: UI.proj.id, n: UI.chN, k: +d.k, who}), r => { UI.proj = JSON.parse(JSON.stringify(r)); draw(); readTools(); }))}); }
      case 'sdopen': return sdOpen(d.k, b);
      case 'sdclose': return sdClose();
      case 'pplfind': return act(() => api('POST', `${A}/project/people/find`, {id: UI.proj.id}), r => { UI.sd && (UI.sd.data = r); pplSync(); }, b, 'Finding the people…');
      case 'pplmerge': return act(() => api('POST', `${A}/project/people/merge`, {id: UI.proj.id, keep: d.val, drop: d.k}), r => { UI.sd && (UI.sd.data = r); pplSync(); toast(`${d.k} and ${d.val} are one person now.`); }, b);
      case 'pplapart': return act(() => api('POST', `${A}/project/people/apart`, {id: UI.proj.id, a: d.k, b: d.val}), r => { UI.sd && (UI.sd.data = r); pplSync(); }, b);
      case 'pplsmall': return act(() => api('PUT', `${A}/project/people`, {id: UI.proj.id, small: !UI.sd?.data?.small}), r => { UI.sd && (UI.sd.data = r); pplSync(); }, b);
      case 'pplvoice': { const who = d.k, cur = castOf(UI.proj)[who] || '';
        return choose(b, {title: who === 'Narrator' ? 'The narrator’s voice' : `Voice for ${who}`, find: 'Search voices', cur, list: voiceList(v => v.ready),
          onPick: v => act(() => api('PUT', `${A}/project/people`, {id: UI.proj.id, voices: {[who]: v}}), r => { UI.sd && (UI.sd.data = r); pplSync(); })}); }
      case 'abfmt': UI.ab.fmt = d.val; return sdPaint();
      case 'abmake': sdClose(); return readAll($('[data-a="readall"]'));
      case 'abgo': { const fmt = UI.ab.fmt, title = UI.proj.title;
        return act(() => api('POST', `${A}/project/export`, {id: UI.proj.id, format: fmt, even: fmt !== 'srt' && !!UI.ab.even, intro: fmt !== 'srt'}),
          r => { sdClose(); side(); toast('The audiobook is ready. It is in Your sounds too.'); if (r?.id) download(r.id, '', title); }, b, 'Putting the book together…'); }
      case 'chadd': UI.proj.chapters.push({title: `Chapter ${UI.proj.chapters.length + 1}`, text: ''}); UI.chN = UI.proj.chapters.length - 1; return draw();
      case 'saveproj': return saveProj(b).then(ok => ok && toast('Saved.'));
      case 'cast': return saveProj().then(ok => ok && act(() => api('POST', `${A}/project/cast`, {id: UI.proj.id, n: +d.n}), r => { UI.cast = null; UI.editing = false; UI.para = null;
        UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id) || UI.proj)); draw(); readTools(); toast(plural((r?.characters || []).length, 'person') + ' found in this chapter.'); }, b, 'Finding the characters…'));
      case 'readch': return saveProj().then(ok => ok && readChapter(+d.n, b));
      case 'readall': return readAll(b);
      case 'export': return act(() => api('POST', `${A}/project/export`, {id: UI.proj.id, format: d.val}), r => { toast('Exported. It is in Your sounds.'); side(); draw(); if (r?.id) download(r.id, d.val === 'srt' || d.val === 'm4b' ? '' : d.val, UI.proj.title); }, b, 'Exporting…');
      case 'rmproj': return confirm('Remove this reading? Sounds already made stay in Your sounds.') && act(() => api('DELETE', `${A}/project?id=${q(id)}`), () => { UI.proj = null; go('studio'); });
      case 'dubrm': UI.dubNew.langs = UI.dubNew.langs.filter(c => c !== d.val); return draw();
      case 'dubsw': UI.dubNew[d.k] = !UI.dubNew[d.k]; draw(); return $(`[data-a="dubsw"][data-k="${d.k}"]`)?.focus();
      case 'dubwrm': UI.dubNew.words.splice(+d.n, 1); draw(); return $('#hvDubW')?.focus();
      case 'dubcancel': UI.dubNew = {file: null, langs: UI.dubNew.langs, mode: UI.dubNew.mode, keep: UI.dubNew.keep, secs: 0, speakers: 0, check: UI.dubNew.check, words: UI.dubNew.words, preview: ''}; draw(); return topTools();
      case 'dubopen': UI.dub = null; UI.dubTab = ''; UI.dubLines = null; UI.dubSel = null; UI.dubRead = false; UI.dubUndo = null; UI.dubDl = {what: 'video', on: {}}; return go('dub', id);
      case 'dubtab': UI.dubTab = d.val; UI.dubLines = null; UI.dubSel = null; UI.dubUndo = null; draw(); dubMediaSet(); return dubLines(ARG);
      case 'dubread': UI.dubRead = true; UI.dubTab = d.val; UI.dubLines = null; draw(); dubMediaSet(); return dubLines(ARG);
      case 'dubsel': UI.dubSel = UI.dubSel === +d.n ? null : +d.n; draw(); dubMediaSet(); { const el = $(`[data-a="dubsel"][data-n="${+d.n}"]`); el?.focus(); el?.closest('li')?.scrollIntoView({block: 'nearest'}); } return;
      case 'dubhearl': return playLine(+d.n);
      case 'dubsp': return blobUrl(`${A}/dub/${q(ARG)}/speaker?sp=${q(d.val)}`).then(u => play(`sp:${d.val}`, u, `${dubName(UI.dub, d.val)} in the original`), e => toast(e.message, true));
      case 'dubok': return act(() => api('POST', `${A}/dub/${q(ARG)}/ok`, {lang: d.val}), async r => { UI.dub = r; toast('The lines are being spoken now.'); await dubRefresh(); }, b, 'Starting…');
      case 'dubremake': if (UI.dub?.mode === 'own' && !confirm('Make the changed lines again? ElevenLabs charges for the seconds it makes again.')) return;
        return act(() => api('POST', `${A}/dub/${q(ARG)}/remake`, {lang: d.val}), async () => { URLS.clear(); toast('The changed lines are being made again.'); UI.dubUndo = null; await dubRefresh(); }, b, 'Starting…');
      case 'dubstop': return confirm('Stop this dub? Languages that are made stay.') && act(() => api('POST', `${A}/dub/${q(ARG)}/stop`), () => dubRefresh(), b);
      case 'dubshort': { const n = +d.n; return act(() => api('POST', `${A}/dub/${q(ARG)}/lines/${n}/shorten`, {lang: UI.dubTab}), async r => { UI.dubUndo = {n, text: r.before}; toast('Shortened. Undo puts the old words back.'); await dubRefresh(); }, b, 'Shortening…'); }
      case 'dubfast': { const n = +d.n, r0 = (UI.dubLines?.lines || []).find(x => x.n === n); return act(() => api('PUT', `${A}/dub/${q(ARG)}/lines/${n}`, {lang: UI.dubTab, pace: r0?.pace > 1 ? 1.0 : 1.15}), () => dubRefresh(), b); }
      case 'dubundo': { const u = UI.dubUndo; if (!u) return; return act(() => api('PUT', `${A}/dub/${q(ARG)}/lines/${u.n}`, {lang: UI.dubTab, text: u.text}), async () => { UI.dubUndo = null; await dubRefresh(); }, b); }
      case 'dubwho': { const n = +d.n, r0 = (UI.dubLines?.lines || []).find(x => x.n === n);
        return choose(b, {title: 'Who says it', cur: r0?.speaker, list: (UI.dub.people || []).map(p => ({v: p.id, label: p.name, sub: plural(p.lines, 'line')})),
          onPick: v => act(() => api('PUT', `${A}/dub/${q(ARG)}/lines/${n}`, {lang: UI.dubTab, speaker: v}), () => dubRefresh())}); }
      case 'dubvoice': { const sp = d.k, cur = ((UI.dub.people || []).find(p => p.id === sp) || {}).voice_id;
        return choose(b, {title: `Voice for ${dubName(UI.dub, sp)}`, find: 'Search voices', cur, list: voiceList(v => v.ready && v.kind === 'hoola' && v.engine === 'gemini' && !v.gid),
          onPick: v => act(() => api('PUT', `${A}/dub/${q(ARG)}/speakers`, {voices: {[sp]: v}}), async r => { UI.dub = r; await dubRefresh(); sdPaint(); })}); }
      case 'dubmenu': return menu(b, [{label: 'Remove this dub', sub: 'The dubbed videos stay in Your sounds', danger: true,
        run: () => confirm('Remove this dub? The dubbed videos stay in Your sounds.') && act(() => api('DELETE', `${A}/dub/${q(ARG)}`), () => { UI.dub = null; UI.dubs = null; go('dub'); })}]);
      case 'dldlang': UI.dubDl.on[d.val] = !UI.dubDl.on[d.val]; return sdPaint();
      case 'dldwhat': UI.dubDl.what = d.val; return sdPaint();
      case 'dldgo': { const x = UI.dubDl, dd_ = UI.dub, langs = (dd_.langs || []).filter(l => l.status === 'ready' && x.on[l.code]);
        const ext = langs.length > 1 || ['voices'].includes(x.what) || x.what === 'subs' ? 'zip' : x.what === 'sound' ? 'mp3' : 'mp4';
        const name = langs.length > 1 ? `${dubBase(dd_)} - ${({video: 'videos', subbed: 'videos with subtitles', sound: 'sound', voices: 'voices', subs: 'subtitles'})[x.what]}.zip`
          : `${dubBase(dd_)} - ${langs[0]?.name || ''}${x.what === 'subbed' ? ' (subtitles)' : ''}.${ext}`;
        b.disabled = true; b.textContent = 'Getting it ready…';
        return saveFile(`${A}/dub/${q(ARG)}/export?what=${q(x.what)}&langs=${q(langs.map(l => l.code).join(','))}`, name).then(() => sdClose()); }
      case 'dkrm': UI.dubKeep.splice(+d.n, 1); sdPaint(); return $('#hvDkW')?.focus();
      case 'dksave': return act(() => api('PUT', `${A}/dub/${q(ARG)}/keep`, {words: UI.dubKeep}), async r => { UI.dub = r; sdClose(); toast('Saved. Lines are checked for these words.'); await dubRefresh(); }, b);
      case 'dubmore': { const have = new Set((UI.dub.langs || []).map(l => l.code));
        return choose(b, {title: 'Add a language', find: 'Search languages', cur: '', list: langList(false, 'dub').filter(l => !have.has(l.v)), onPick: v =>
          act(() => api('POST', `${A}/dub/${q(ARG)}/langs`, {langs: [v]}), r => { side(); if (r?.id && r.id !== ARG) { toast(`A new dub in ${short(v)} is being made from the same video.`); UI.dub = null; UI.dubTab = ''; UI.dubLines = null; go('dub', r.id); }
            else { toast(`${short(v)} is being added to this dub.`); UI.dub = r; UI.dubTab = v; UI.dubLines = null; draw(); dubLines(ARG); dubPoll(ARG); } }, b, 'Starting…')}); }
      case 'fxloop': UI.fx.loop = !UI.fx.loop; return draw();
      case 'preset': return act(() => api('POST', `${A}/sfx`, {preset: d.val, seed: +UI.seed || 1}), r => { const it = r?.items?.[0] || r; if (it?.id) { UI.fx.out = [it, ...UI.fx.out].slice(0, 8); } side(); draw(); if (it?.id) play(it.id); }, b);
    }
  }
  function tagAt(tone) {
    const ta = $('#hvText'); if (!ta) return; const a = ta.selectionStart ?? ta.value.length, z = ta.selectionEnd ?? a, before = ta.value.slice(0, a);
    const t = `${before && !/\s$/.test(before) ? ' ' : ''}[${tone}] `;
    ta.value = before + t + ta.value.slice(z); S.text = ta.value; ta.focus(); ta.selectionStart = ta.selectionEnd = a + t.length; onInput({target: ta});
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
  async function pplSync() { await load(); if (UI.proj) UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id) || UI.proj)); draw(); sdPaint(); }
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
      const out = await api('POST', `${A}/project`, {id: p.id, title: p.title, voice: p.voice || S.voice, lang: p.lang, chapters: p.chapters.map(c => ({title: c.title, text: c.text})), ...(cast ? {cast} : {}),
        ...(p.pace != null ? {pace: +p.pace} : {}), ...(p.gap != null ? {gap: +p.gap} : {}), ...(p.author != null ? {author: p.author} : {})});
      await load(); const chapters = p.chapters; UI.proj = JSON.parse(JSON.stringify(out)); if (!UI.proj.chapters) UI.proj.chapters = chapters; crumb(); side(); draw(); return true; }
    catch (e) { toast(e.message, true); if (btn?.isConnected) btn.disabled = false; return false; }
  }
  function onInput(ev) {
    const t = ev.target;
    const rn = /^UI\.dlg\.cast\.(\d+)\.name$/.exec(t.dataset?.m || '');      // a renamed speaker keeps their lines
    if (rn) { const old = UI.dlg.cast[+rn[1]]?.name; UI.dlg.lines.forEach(l => { if (l.speaker === old) l.speaker = t.value; }); }
    if (t.dataset?.m) { setM(t.dataset.m, t.type === 'checkbox' ? t.checked : t.dataset.t === 'num' ? +t.value : t.value);
      $$(`[data-show="${t.dataset.m}"]`).forEach(x => { x.textContent = `${(+t.value).toFixed(2)}x`; }); }
    if (t.dataset?.trim) chgTrim(t);
    if (t.dataset?.ch != null && UI.proj?.chapters?.[+t.dataset.ch]?.audio) UI.edited[+t.dataset.ch] = true;
    if (t.dataset?.pace) $$('[data-show="UI.proj.pace"]').forEach(x => { x.textContent = paceWord(t.value); });
    if (t.dataset?.dirty) readTools();
    if (t.id === 'hvText') { const c = $('#hvCount'); if (c) c.textContent = countLine(); const tm = $('#hvTime'); if (tm) tm.textContent = timeLine();
      edSync(); if (S.text.trim()) { $('.hv-sphero')?.remove(); $('.hv-spstarts')?.remove(); } price('speech', ttsQuote(S.text), r => autoLine(r, short(S.lang))); }
    if (t.dataset?.line != null) { const i = +t.dataset.line, {tone} = toneOf(spLines()[i] || ''); lnSet(i, tone ? `[${tone}] ${t.value.replace(/\n/g, ' ')}` : t.value.replace(/\n/g, ' '));
      if (/\n/.test(t.value)) t.value = t.value.replace(/\n/g, ' '); t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; lnRefresh(); }
    if (t.id === 'hvVpQ' && SP.vp) { SP.vp.q = t.value; vpPaint(); }
    if (t.dataset?.m === 'S.speed' && PAGE === 'speech') { const sm = $('#hvSpSum'); if (sm) sm.textContent = spSum(); const tm = $('#hvTime'); if (tm) tm.textContent = timeLine(); }
    if (t.id === 'hvAsk') { grow(t); sendState(); price('chat', chatQuote(), chatLine); }
    if (t.id === 'hvSq' || t.id === 'hvSnq') refreshSide();
    if (t.id === 'hvLq') { const tb = $('#hvLangRows'); if (tb) tb.innerHTML = langRows(); }
    if (t.id === 'hvTry' || t.id === 'hvCmpT') vPrice();
    if (t.id === 'hvVq') { clearTimeout(onInput.t); onInput.t = setTimeout(() => { if (UI.vtab === 'shared') libLoad(); else { const id = t.id, a = t.selectionStart; draw(); const n = $('#' + id); if (n) { n.focus(); try { n.setSelectionRange(a, a); } catch { /* */ } } } }, 300); }
    if (t.dataset?.m === 'S.speed' && PAGE === 'chat') { const s = $('#hvSum'); if (s) s.textContent = summary(); }
    if (t.classList?.contains('hv-lt')) { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }
    if (t.id === 'hvFx') { const b = $('[data-qbtn="fx"]'); if (b && ready('eleven') && !broke()) { const ok = UI.fx.prompt.trim().length >= 3; if (ok === b.disabled) { const a = t.selectionStart; draw(); const n = $('#hvFx'); if (n) { n.focus(); n.setSelectionRange(a, a); } } } }
    if (t.dataset?.dl != null) { const n = +t.dataset.dl, ln = $(`#hvDlLen${n}`), s2 = dlSecs(t.value); if (ln) ln.textContent = s2 ? secs(s2) : ''; const sm = $('#hvDlSum'); if (sm) sm.textContent = dlSum(); const hi = t.closest('.hv-dlw')?.querySelector('.hv-dlhi'); if (hi) hi.innerHTML = hiHTML(t.value); dlMark(n); }
    if (t.dataset?.m?.startsWith('UI.dlg.lines') && t.tagName === 'TEXTAREA') { const b = $('[data-qbtn="dlg"]'); const has = UI.dlg.lines.some(l => (l.text || '').trim());
      if (b && (has === b.disabled) && !speakWhy(UI.dlg.lang, 'auto') && !broke()) { const id = t.id, a = t.selectionStart; draw(); const n = $('#' + id); if (n) { n.focus(); n.setSelectionRange(a, a); } } else dlPrice(); }
    if (t.id === 'hvCpQ' && UI.dlg.cp) { UI.dlg.cp.q = t.value; cpPaint(); }
  }
  function onChange(ev) {
    const t = ev.target;
    if (t.dataset?.dubline) { const n = +t.dataset.dubline, text = t.value;
      return api('PUT', `${A}/dub/${q(ARG)}/lines/${n}`, {lang: UI.dubTab, text}).then(() => { UI.dubUndo = null; toast(`Line ${n + 1} saved. Make the changes when you are done.`); return dubRefresh(); }).catch(e => toast(e.message, true)); }
    if (t.dataset?.dubname) { const sp = t.dataset.dubname, name = t.value.trim(); if (!name) return;
      return api('PUT', `${A}/dub/${q(ARG)}/speakers`, {names: {[sp]: name}}).then(r => { UI.dub = r; toast('Saved.'); if (!UI.sd) { const keep = ROOT.querySelector(':focus')?.id; draw(); if (keep) $('#' + keep)?.focus(); } }).catch(e => toast(e.message, true)); }
    if (t.dataset?.m) {
      if (t.type === 'checkbox' || t.type === 'range') setM(t.dataset.m, t.type === 'checkbox' ? t.checked : +t.value);
      if (/^UI\.dlg\.cast\.\d+\.name$/.test(t.dataset.m)) return draw();
      if (t.dataset.redraw || (t.type === 'checkbox' && t.dataset.m.startsWith('UI.'))) return draw();
      if (t.dataset.m === 'S.rules') { const c = $('#hvCount'); if (c) c.textContent = countLine(); }
    }
  }
  function onKey(ev) {
    if (ev.key === 'Enter' && (ev.target.dataset?.dubword || ev.target.dataset?.dkword)) { ev.preventDefault(); const w = ev.target.value.trim(); if (!w) return;
      const list = ev.target.dataset.dubword ? UI.dubNew.words : UI.dubKeep; if (!list.some(x => x.toLowerCase() === w.toLowerCase()) && list.length < 30) list.push(w);
      if (ev.target.dataset.dubword) { draw(); $('#hvDubW')?.focus(); } else { sdPaint(); $('#hvDkW')?.focus(); } return; }
    if (ev.target.closest?.('[data-drag="chatw"]') && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(ev.key)) { ev.preventDefault();
      const sp = $('#hvSplit'), max = sp ? sp.clientWidth - 320 : 1400;
      UI.cw = ev.key === 'Home' ? 380 : ev.key === 'End' ? max : UI.cw + (ev.key === 'ArrowLeft' ? -40 : 40); return setWidth('open', Math.max(380, UI.cw)); }
    if (ev.target.dataset?.dl != null) { const n = +ev.target.dataset.dl, ls = UI.dlg.lines;
      if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); const bt = $('[data-qbtn="dlg"]'); if (bt && !bt.disabled) bt.click(); return; }
      if (ev.key === 'Enter' && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); if (ls.length >= (D.limits?.lines || 40)) return toast('That is the most lines one talk can have.');
        const ta = ev.target, at = ta.selectionStart, cur = ls[n], tail = (cur.text || '').slice(at).trim(); cur.text = (cur.text || '').slice(0, at).trimEnd();
        ls.splice(n + 1, 0, {speaker: UI.dlg.cast.find(c => c.name !== cur.speaker)?.name || cur.speaker, text: tail, pause: 0, cut: false}); UI.dlg.sel = n + 1; draw(); return dlFocus(n + 1); }
      if (ev.key === 'Backspace' && !ev.target.value && ls.length > 1 && n > 0) { ev.preventDefault(); ls.splice(n, 1); UI.dlg.sel = n - 1; draw(); return dlFocus(n - 1, true); } }
    if (ev.key === 'Escape' && UI.dlg.cp) { ev.preventDefault(); return cpClose(); }
    if (ev.key === 'Escape' && UI.sd) { ev.preventDefault(); return sdClose(); }
    if (ev.key === 'Tab' && UI.sd) { const f = [...($('#hvSd .hv-vp')?.querySelectorAll('button:not([disabled]),input,a[href]') || [])]; if (f.length) { const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); } else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); } } return; }
    if (ev.key === 'Tab' && UI.dlg.cp) { const box = $('#hvCp .hv-vp'), f = box ? [...box.querySelectorAll('button:not([disabled]),input')] : []; if (f.length) { const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); } else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); } } }
    if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && ev.target.id === 'hvText') { ev.preventDefault(); const f = $('form[data-f="speech"]'); const btn = $('[data-qbtn="speech"]'); if (f && btn && !btn.disabled) f.requestSubmit(btn); return; }
    if (ev.key === 'Enter' && !ev.shiftKey && ev.target.dataset?.line != null) { ev.preventDefault(); const i = +ev.target.dataset.line, ls = spLines(), el = ev.target, at = el.selectionStart ?? el.value.length;
      const {tone} = toneOf(ls[i]), head = el.value.slice(0, at), tail = el.value.slice(at); ls[i] = tone ? `[${tone}] ${head}` : head; ls.splice(i + 1, 0, tail); S.text = ls.join('\n');
      SP.sel = i + 1; draw(); const n = $(`.hv-lnt[data-line="${i + 1}"]`); if (n) { n.focus(); n.setSelectionRange(0, 0); } return; }
    if (ev.key === 'Tab' && SP.vp) { const f = [...($('#hvVp .hv-vp')?.querySelectorAll('button:not(:disabled),input') || [])]; if (f.length) { const k = f.indexOf(document.activeElement);
      if (ev.shiftKey && k <= 0) { ev.preventDefault(); f[f.length - 1].focus(); } else if (!ev.shiftKey && k === f.length - 1) { ev.preventDefault(); f[0].focus(); } } return; }
    if (ev.key !== 'Escape') return;
    if (SP.vp) { ev.preventDefault(); return vpClose(); }
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
          r => { UI.clone = {sample: null, consent: null, name: 'My voice', ok: false, lang: c.lang}; if (r?.id) { UI.yv = 'detail'; UI.mv = r.id; } toast('Your voice is ready.'); side(); draw(); }, btn, 'Making…'); }
      case 'design': if (UI.design.desc.trim().length < 8) { toast('Describe the voice in a few more words.', true); return $('#hvDDesc')?.focus(); }
        return act(() => api('POST', `${A}/voice/design`, {description: UI.design.desc, gender: UI.design.gender, preview: true, lang: UI.design.lang || (S.lang !== 'auto' ? S.lang : '')}),
          r => { UI.design.previews = (r.previews || []).filter(p => p && p.audio_id); UI.design.pick = ''; if (!UI.design.previews.length) toast('The engine gave no options to hear this time. Try other words.', true); draw(); }, btn, 'Making 3 options…');
      case 'yvren': { const n = v('#hvRen'); if (!n) { toast('Give the voice a name.', true); return $('#hvRen')?.focus(); } const vid = UI.ren;
        return act(() => api('PATCH', `${A}/voice`, {id: vid, name: n}), () => { UI.ren = ''; toast('Renamed.'); side(); draw(); $('#hvView [data-a="yvren"]')?.focus(); }, btn, 'Saving…'); }
      case 'remix': if (!UI.remix.change.trim()) { toast('Say what to change.', true); return $('#hvRChange')?.focus(); }
        return act(() => api('POST', `${A}/voice/remix`, {base: UI.remix.base, change: UI.remix.change, name: UI.remix.name || `${vname(UI.remix.base)} · changed`}),
          r => { UI.remix.made = r?.id || ''; toast('The new voice is ready. Hear before and after.'); side(); draw(); }, btn, 'Making…');
      case 'podcast': { const p = UI.dlg.pod, src = p.src === 'file' ? {file_id: p.file?.file_id} : p.src === 'url' ? {url: p.url} : {text: p.text};
        if (!Object.values(src)[0]) { toast(p.src === 'file' ? 'Choose the file first.' : p.src === 'url' ? 'Type the web address first.' : 'Paste the text first.', true); return; }
        return act(() => api('POST', `${A}/podcast`, {...src, minutes: Math.max(1, Math.min(15, +p.minutes || 5)), hosts: UI.dlg.cast.slice(0, 2).map(c => ({name: c.name, voice: c.voice})), lang: UI.dlg.lang || 'auto', kind: p.kind || 'podcast', must: p.must || ''}),
          r => { p.draft = r; draw(); toast(r.unchecked ? 'The script is ready. Check the marked lines before you use it.' : 'The script is ready. Read it, then use it.'); }, btn, 'Writing…'); }
      case 'dialogue': return;
      case 'import': return impPreview(btn);
      case 'dub': { const n = UI.dubNew;
        return act(() => api('POST', `${A}/dub`, {file_id: n.file.file_id, langs: n.langs, mode: n.mode, keep_sound: !!n.keep, keep: n.words || [], check: n.mode === 'matched' && !!n.check,
          ...(n.mode === 'matched' && n.speakers ? {speakers: n.speakers} : {})}),
          r => { UI.dubNew = {file: null, langs: [], mode: n.mode, keep: n.keep, secs: 0, speakers: n.speakers, check: n.check, words: [], preview: ''}; UI.dub = null; UI.dubLines = null; UI.dubs = null; UI.dubRead = false; go('dub', r.id); }, btn, 'Starting…'); }
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
