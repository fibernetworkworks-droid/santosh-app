/* v0.999.170 HOOLA INTERACTIVE, REBUILT (owner: "GO BUILD" on the design canvas claude.ai/artifact/38Ejw9Eekn9y8u8H8nEwGp;
   the build contract is docs/HOOLA_INTERACTIVE_REBUILD.md). Hoola Interactive now sits on the Create Studio / Hoola Vocal
   frame: a 248 px sidebar with the real Hoola mark and four groups (Make, Faces and voices, Live, Assets) plus the
   credits card, a 52 px top bar with the crumb "Interactive · <page>", and the Interactive chat as the home.

   What each page stands on is real:
     /api/interactive/chat*            the Interactive chat (kind 'interactive'): she says it, Hoola plans a DRAFT
     /api/interactive/studio/*         the film: draft -> scenes -> make (progress, stop, the video, her faces)
     /api/interactive/hub/*            brand, glossary, templates, batch, names, translate, trash
     /api/interactive/x/*              engines + defaults, voices (Vocal's), languages (140), the price card, B-roll,
                                       live agents (ask, session pass, publish), app keys + webhooks
   A paid face engine starts only with her tap on the exact price (quote key). An engine that is not connected says
   which key it needs. Every dropdown is the console menu (HoolaMenu). Colours are console tokens (interactive2.css).
   Her text is always esc()'d. No data-v attributes (the console's global [data-v] handler would take them). */
'use strict';
window.HoolaInteractive = function (ctx) {
  const {api, esc, upload, back} = ctx;
  const X = '/api/interactive/x', S = '/api/interactive/studio', H = '/api/interactive/hub', C0 = '/api/interactive';
  let ROOT = null, PAGE = 'chat', ARG = '', D = null;
  const store = {get: (k, d) => { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window */ } }};
  const scrub = t => String(t ?? '').replace(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:API_)?(?:KEY|TOKEN|SECRET)\b/g, 'its key');
  const toast = (m, bad) => ctx.toast(scrub(m), bad);
  const SET = Object.assign({lang: 'auto', face: '', voice: '', engine: '', shape: 'talking_head', kind: 'presenter', len: 30}, store.get('hx.set', {}));
  if (SET.lang === 'hi' && !store.get('hx.langv2', false)) { SET.lang = 'auto'; store.set('hx.langv2', true); store.set('hx.set', SET); }   // v0.999.172 the old India default becomes Auto
  const C = {conv: '', title: '', rows: [], items: [], ask: '', files: [], sending: false, waitUntil: 0, t: 0, gen: 0};
  const UI = {slim: store.get('hx.slim', false), nav: false, etab: 'video', ptab: 'Videos', scene: 0, tool: 'Scene', lf: 'all', lq: '', ls: store.get('hx.lsort', 'new'), lv: store.get('hx.lview', 'grid'), edv: 'video', edp: false, edt: 0, jp: {}, q: null, cmp: null, V: null, L: null,
    live: '', liveOut: [], newKey: null, newHook: null, pub: null, broll: {prompt: '', seconds: 6, aspect: '16:9', q: null}, jobs: {},
    me: '', credits: null, recent: [], est: null, ideaG: 'business', pv: {id: '', scene: 0, tab: 'sketch', play: false, t: 0}, audio: null};
  const URLS = new Map();
  const q = encodeURIComponent;
  const $ = s => ROOT && ROOT.querySelector(s);
  const $$ = s => ROOT ? [...ROOT.querySelectorAll(s)] : [];

  const NAV = [['Make', [['chat', 'Interactive chat', 'chat'], ['studio', 'Studio', 'film'], ['templates', 'Templates', 'grid'], ['apps', 'Apps', 'apps']]],
    ['Faces and voices', [['avatars', 'Avatars', 'user'], ['voices', 'Voices', 'mic']]],
    ['Live', [['live', 'Live agents', 'live']]],
    ['Assets', [['projects', 'Projects', 'folder'], ['brand', 'Brand', 'brand'], ['engines', 'Engines', 'bolt'], ['developers', 'Developers', 'code'], ['settings', 'Settings', 'gear']]]];
  const TITLE = Object.fromEntries(NAV.flatMap(([, r]) => r.map(([k, n]) => [k, n])));
  const SHAPE = {talking_head: 'Talking person', product: 'Product film', reel: 'Reel 9:16'};
  const LOOK = {none: 'Just the words', title: 'Big title', big_number: 'Big number', price: 'Price reveal', bar_chart: 'Bar chart', lower_third: 'Name strip'};
  const P = {
    chat: '<path d="M4 5h16v11H9l-5 4z"/>', film: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
    grid: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    apps: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><path d="M17.5 14v7M14 17.5h7"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>', mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    live: '<circle cx="12" cy="12" r="2.5"/><path d="M7.5 7.5a6.4 6.4 0 0 0 0 9M16.5 7.5a6.4 6.4 0 0 1 0 9M4.5 4.5a10.6 10.6 0 0 0 0 15M19.5 4.5a10.6 10.6 0 0 1 0 15"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    brand: '<path d="M12 3a9 9 0 1 0 0 18c1.6 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/>',
    bolt: '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>', code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', up: '<path d="M12 19V5M6 11l6-6 6 6"/>', down: '<path d="M6 9l6 6 6-6"/>', x: '<path d="M6 6l12 12M18 6L6 18"/>',
    back: '<path d="M19 12H5M11 6l-6 6 6 6"/>', side: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>', menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    play: '<path d="M8 5.5v13l11-6.5z"/>', stop: '<rect x="7" y="7" width="10" height="10" rx="1.5"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>', globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    dl: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>', copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    trash: '<path d="M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13"/>', warn: '<path d="M12 4l9 15.5H3zM12 10v4.5M12 17.2v.1"/>', spark: '<path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>',
    dots: '<circle cx="5.5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="18.5" cy="12" r="1.3"/>', search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    sort: '<path d="M7 5v14M4 16l3 3 3-3M17 19V5M14 8l3-3 3 3"/>', rows: '<path d="M4 6h16M4 12h16M4 18h16"/>', doc: '<path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6"/>',
    fwd: '<path d="M5 12h14M13 6l6 6-6 6"/>', dn: '<path d="M12 5v14M6 13l6 6 6-6"/>', vol: '<path d="M4 9.5v5h4l5 4v-13l-5 4zM16.5 9a4.5 4.5 0 0 1 0 6M19 6.5a8 8 0 0 1 0 11"/>'};
  const ic = (n, s = 16) => `<svg class="hx-i" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">${P[n] || ''}</svg>`;
  const markSvg = () => window.HoolaMark ? HoolaMark.svg() : '<img src="/static/hoola-mark.png" alt="" width="26" height="26">';
  const num = n => (+n || 0).toLocaleString('en-IN');
  const cr = n => `${num(n)} credit${+n === 1 ? '' : 's'}`;
  const secs = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const strip = t => String(t || '').replace(/(?:\s*\[(?:Web console [^\]\n]*|Interactive settings:[^\]\n]*)\])+\s*$/, '');
  const engine = id => (D?.engines?.engines || []).find(e => e.id === id);
  const face = id => (D?.avatars || []).find(a => a.id === id);
  const voiceName = id => { const v = UI.V && [...UI.V.mine, ...UI.V.library].find(x => x.id === id); return v ? v.name : (id ? 'Chosen voice' : 'Hoola picks'); };
  const LN0 = {en: 'English', es: 'Spanish', fr: 'French', ar: 'Arabic', pt: 'Portuguese', de: 'German', ja: 'Japanese', ko: 'Korean', it: 'Italian', tr: 'Turkish', nl: 'Dutch', sw: 'Swahili', id: 'Indonesian', hi: 'Hindi', zh: 'Chinese (Mandarin)', auto: 'Auto'};
  const langName = c => (UI.L || []).find(l => l.code === c)?.name || LN0[c] || c || 'Auto';
  const defEngine = () => SET.engine || D?.engines?.defaults?.video || 'hoola';
  const status = p => ({ready: ['ok', 'Ready'], making: ['work', 'Making it'], failed: ['bad', 'Could not make it']}[p.status]
    || ((p.scenes || []).some(s => s.needs) ? ['warn', 'Waiting for your numbers'] : ['', 'Draft']));
  const chip = p => { const [c, t] = status(p); return `<span class="hx-st ${c}">${t}</span>`; };

  async function blobUrl(path) {
    if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true});
    const u = URL.createObjectURL(await r.blob()); URLS.set(path, u); return u;
  }
  function fillMedia() {
    $$('img[data-av]').forEach(async img => { try { img.src = await blobUrl(`${S}/photo?id=${q(img.dataset.av)}`); } catch { img.remove(); } });
    $$('img[data-ci]').forEach(async img => { try { img.src = await blobUrl(`/api/create/items/${q(img.dataset.ci)}`); } catch { img.remove(); } });
    $$('video[data-vid]').forEach(async v => { try { v.src = await blobUrl(`${S}/video?id=${q(v.dataset.vid)}`); } catch { /* not ready */ } });
    $$('video[data-broll]').forEach(async v => { try { v.src = await blobUrl(`${X}/broll/file?id=${q(v.dataset.broll)}`); } catch { /* not ready */ } });
  }
  const avImg = (a, cls = '') => a ? `<span class="hx-face ${cls}"><img data-av="${esc(a.id)}" alt=""><span>${esc((a.name || 'H').slice(0, 1).toUpperCase())}</span></span>`
    : `<span class="hx-face ${cls} none">${ic('user', 18)}</span>`;

  // ------------------------------------------------------------------ data ---
  async function load() {
    try { D = await api('GET', `${X}/home`); }
    catch (e) { D = D || {projects: [], avatars: [], engines: {engines: [], defaults: {}}, live: {agents: [], broll: [], faces: []}, apps: {keys: [], hooks: []}, usage: {}, templates: [], glossary: [], brand: {}, trash: []};
      toast(e.message, true); }
  }
  async function voicesLoad() { if (UI.V) return; try { UI.V = await api('GET', `${X}/voices`); } catch { UI.V = {mine: [], library: []}; } }
  async function langsLoad() { if (UI.L) return; try { UI.L = (await api('GET', `${X}/langs`)).langs; } catch { UI.L = Object.entries(LN0).filter(([c]) => c !== 'auto').map(([code, name]) => ({code, name})); } }

  // ------------------------------------------------------------------ shell ---
  function cssHref() { const s = document.querySelector('script[src*="/interactive.js"]')?.getAttribute('src') || ''; return `/static/console/interactive2.css${s.includes('?') ? s.slice(s.indexOf('?')) : ''}`; }
  function mount() {
    if (ROOT) { ROOT.hidden = false; return; }
    if (!document.querySelector('link[data-hx], link[href*="interactive2.css"]')) { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = cssHref(); l.dataset.hx = '1'; document.head.appendChild(l); }
    ROOT = document.createElement('div'); ROOT.id = 'hxRoot'; ROOT.className = 'hx'; ROOT.setAttribute('aria-label', 'Hoola Interactive');
    ROOT.innerHTML = `<aside class="hx-side" id="hxSide" aria-label="Hoola Interactive pages"></aside><div class="hx-scrim" data-a="navoff" aria-hidden="true"></div>
      <div class="hx-main"><header class="hx-top"><button type="button" class="hx-ib hx-menu" data-a="navon" aria-label="Open the menu">${ic('menu', 18)}</button>
        <div class="hx-crumb" id="hxCrumb"></div><span class="hx-grow"></span><div class="hx-topr" id="hxTopR"></div></header><main class="hx-view" id="hxView"></main></div>`;
    document.body.appendChild(ROOT);
    ROOT.addEventListener('click', onClick); ROOT.addEventListener('input', onInput); ROOT.addEventListener('change', onChange);
    ROOT.addEventListener('focusin', e => { const n = e.target.dataset?.sc; if (n != null && PAGE === 'studio' && +n !== UI.scene) { edStop(); UI.scene = +n; edPaint(); } });
    ROOT.addEventListener('keydown', e => { if (e.target.id === 'hxAsk' && e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); chatSend(); }
      if (e.key === 'Escape' && UI.dlg) { dlgClose(); return; }
      if (e.key === 'Escape' && UI.nav) { UI.nav = false; side(); } });
  }
  async function open() { mount(); await load(); go(PAGE, ARG); voicesLoad().then(() => { if (PAGE === 'chat') refreshBar(); }); langsLoad().then(() => { if (PAGE === 'chat' && $('.hx-hero')) draw(); }); meLoad(); recentLoad(); estimate(); }
  function leave() { clearTimeout(C.t); pvStop(); clearTimeout(UI.edt); UI.edp = false; UI.audio?.pause(); Object.values(UI.jobs).forEach(clearTimeout); UI.jobs = {}; window.HoolaMenu?.close(); if (ROOT) { ROOT.querySelectorAll('audio,video').forEach(m => m.pause?.()); ROOT.hidden = true; } }
  function creditCard() {
    const u = D?.usage || {};
    return `<div class="hx-cred"><div class="r"><span>This month</span><b class="hx-num">${num(u.videos || 0)} video${u.videos === 1 ? '' : 's'}</b></div>
      <span>${num(u.minutes || 0)} min made · the price shows before every paid video</span></div>`;
  }
  function side() {
    ROOT.classList.toggle('hx-slim', UI.slim); ROOT.classList.toggle('hx-navon', UI.nav);
    const on = PAGE;
    const row = ([id, n, i]) => `<button type="button" class="hx-nv" data-a="go" data-p="${id}"${UI.slim && !UI.nav ? ` title="${n}"` : ''}${id === on ? ' aria-current="page"' : ''}>${ic(i)}<span>${n}</span></button>`;
    $('#hxSide').innerHTML = `<div class="hx-brand"><span class="hx-mark" aria-hidden="true">${markSvg()}</span><b>Hoola</b><span class="hx-badge">Interactive</span><span class="hx-grow"></span>
        <button type="button" class="hx-ib" data-a="slim" aria-label="${UI.slim ? 'Open the sidebar' : 'Close the sidebar'}">${ic('side', 18)}</button></div>
      <button type="button" class="hx-nv" data-a="back">${ic('back')}<span>Back to chat</span></button>
      <button type="button" class="hx-newchat" data-a="newchat">${ic('plus')}<span>New video</span></button>
      ${NAV.map(([g, rows]) => `<span class="hx-gh">${g}</span>${rows.map(row).join('')}`).join('')}
      ${UI.recent?.length && !(UI.slim && !UI.nav) ? `<span class="hx-gh">Recent chats</span>${UI.recent.map(c => `<button type="button" class="hx-nv hx-rc" data-a="openchat" data-id="${esc(c.id)}"${PAGE === 'chat' && C.conv === c.id ? ' aria-current="true"' : ''}><span>${esc(c.title || 'Interactive chat')}</span></button>`).join('')}
        <button type="button" class="hx-nv hx-rc dim" data-a="chats"><span>All chats</span></button>` : ''}
      <span class="hx-grow"></span>${creditCard()}`;
  }
  function crumb() {
    const p = PAGE === 'apps' && ARG && appOf(ARG) ? ['Apps', appOf(ARG).name] : PAGE === 'templates' && ARG ? ['Templates', tplOf(ARG)?.name || 'Template'] : PAGE === 'studio' && ARG ? ['Studio', (D.projects || []).find(x => x.id === ARG)?.title || 'Video'] : PAGE === 'chat' ? [C.title && C.title !== 'Interactive chat' ? C.title : 'Interactive chat'] : [TITLE[PAGE] || ''];
    $('#hxCrumb').innerHTML = `<span>Interactive ·${p.length > 1 ? ' ' + esc(p[0]) + ' ·' : ''}</span><h1 class="hx-h">${esc(p[p.length - 1])}</h1>`;
    const t = $('#hxTopR');
    t.innerHTML = PAGE === 'chat' ? `${UI.credits != null ? `<button type="button" class="hx-credp hx-num" data-a="credits" title="Your credits">${ic('spark', 14)}${num(UI.credits)} credits</button>` : ''}
      <button type="button" class="hx-ib" data-a="chats" aria-label="Earlier chats" title="Earlier chats">${ic('clock', 18)}</button>
      <button type="button" class="hx-ib" data-a="newchat" aria-label="New chat" title="New chat">${ic('plus', 18)}</button>`
      : PAGE === 'studio' || PAGE === 'templates' || PAGE === 'apps' || PAGE === 'avatars' || PAGE === 'voices' ? (UI.credits != null ? `<button type="button" class="hx-credp hx-num" data-a="credits" title="Your credits">${ic('spark', 14)}${num(UI.credits)} credits</button>` : '') : '';
  }
  function go(page, arg) {
    window.HoolaMenu?.close();
    clearTimeout(UI.edt); UI.edp = false; if (page !== 'studio' || arg !== ARG) UI.q = null;
    clearTimeout(abT); tuStop(); if (UI.dlg && !(UI.dlg.k === 'sheet' && page === 'templates')) { UI.dlg = null; dlgPaint(); }
    PAGE = V[page] ? page : 'chat'; ARG = arg || ''; UI.nav = false;
    side(); crumb(); draw();
    const v = $('#hxView'); v.scrollTop = 0; v.classList.remove('hx-enter'); void v.offsetWidth; v.classList.add('hx-enter');
    ENTER[PAGE]?.();
  }
  function draw() {
    const keep = $$('#hxView [data-keep]').map(e => [e.dataset.keep, e.scrollTop]);
    $('#hxView').innerHTML = V[PAGE](); keep.forEach(([k, t]) => { const e = $(`#hxView [data-keep="${CSS.escape(k)}"]`); if (e) e.scrollTop = t; });
    AFTER[PAGE]?.(); fillMedia();
  }

  // ------------------------------------------------------------------ the chat (v0.999.172: design claude.ai/artifact/5wm914F3jEgnNNfNr3rXPn) ---
  // The home: the kind of video, one box with every pick and the price before anything is planned, start from something
  // she has, ideas from around the world, her videos. The chat: her words, then a plan card (scene thumbnails, face,
  // voice she can hear for free, language, engine, the itemised price, Make), and beside it a sketch / the script / the
  // subtitles of that plan. Making is always her tap on the card's price.
  const KINDS = [['presenter', 'Talking presenter', 'P', 'Describe your video, or paste a script. Any language.'],
    ['explainer', 'Explainer', 'E', 'What should people understand after watching?'],
    ['reel', 'Social reel', 'R', 'A short reel: what is new, and who is it for?'],
    ['product', 'Product video', '$', 'Your product, its price, and why people love it.'],
    ['lesson', 'Lesson', 'L', 'The topic, who is learning, and how long it should be.'],
    ['translate', 'Translate a video', 'T', '']];
  const KIND_NAME = Object.fromEntries(KINDS.map(k => [k[0], k[1]]));
  const shapeOf = k => k === 'reel' ? 'reel' : k === 'product' ? 'product' : 'talking_head';
  const aspectOf = k => k === 'reel' ? '9:16' : '16:9';
  const LENS = [15, 30, 45, 60, 90];
  const IDEA_G = {business: 'For a business', teach: 'Teaching', personal: 'Personal', nonprofit: 'Nonprofits'};
  const IDEAS = {
    business: [['Welcome new guests to my café in Lisbon, friendly, with English subtitles', 'pt', 'presenter'],
      ['Spring sale: 20% off all plants until 30 April, as a 15-second reel', 'es', 'reel'],
      ['Our clinic has new opening hours from Monday, 8 am to 6 pm', 'ar', 'presenter'],
      ['Introduce my new skincare serum in 30 seconds, with its price', 'en', 'product']],
    teach: [['Lesson 1 of my photography course: light and shadow, in 90 seconds', 'fr', 'lesson'],
      ['Explain photosynthesis to 12-year-olds in three simple scenes', 'de', 'explainer'],
      ['Welcome my new students and explain how the class works this term', 'ja', 'presenter'],
      ['Turn my training notes into a short video for new staff', 'ko', 'lesson']],
    personal: [['A birthday message for my grandmother, warm and short', 'it', 'presenter'],
      ['Introduce myself for a job application in 45 seconds', 'en', 'presenter'],
      ['Invite our friends to our wedding, with the date and the place', 'tr', 'reel'],
      ['A thank-you video for my running club', 'nl', 'presenter']],
    nonprofit: [['Thank our donors and show what their gifts paid for this year', 'sw', 'explainer'],
      ['Ask volunteers to join our beach clean-up on Saturday', 'id', 'reel'],
      ['Explain how to apply for our scholarship, step by step', 'hi', 'explainer'],
      ['Our year in numbers, from the report I attach', 'pt', 'explainer']]};
  const SUGGEST = ['Make it shorter', 'More energetic', 'Add a call to action at the end', 'Make a vertical version for social media', 'Use a calmer voice'];
  const MORE_LANGS = ['en', 'es', 'fr', 'ar', 'zh', 'pt', 'hi', 'de', 'ja'];
  const kindNow = () => KIND_NAME[SET.kind] && SET.kind !== 'translate' ? SET.kind : 'presenter';
  const settingsNote = () => `[Interactive settings: kind ${kindNow()}; language ${SET.lang || 'auto'}; face ${SET.face || 'none'}; voice ${SET.voice || 'auto'}; engine ${defEngine()}; shape ${shapeOf(kindNow())}; length ${SET.len || 30} s]`;
  const greet = () => { const h = new Date().getHours(); return (h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening') + (UI.me ? `, ${UI.me}` : ''); };
  const brandColor = () => /^#[0-9a-f]{6}$/i.test(D?.brand?.color || '') ? D.brand.color : '#2F4B5C';
  const lenOf = p => p?.video?.duration || (p?.scenes || []).reduce((n, s) => n + Math.max(2, (s.say || '').split(/\s+/).filter(Boolean).length / 2.6) + .35, 0) + 1.2;
  const clock = s => { s = Math.max(0, Math.round(+s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const lookText = lk => !lk ? '' : lk.kind === 'title' ? lk.text : lk.kind === 'big_number' ? `${lk.value || ''} ${lk.label || ''}` : lk.kind === 'price' ? `${lk.new || ''}${lk.old ? ' · was ' + lk.old : ''}`
    : lk.kind === 'lower_third' ? `${lk.title || ''}${lk.sub ? ' · ' + lk.sub : ''}` : lk.kind === 'bar_chart' ? (lk.bars || []).map(b => `${b.label} ${b.value}`).join(' · ') : '';
  const sceneTimes = p => { let t = 0; return (p.scenes || []).map(s => { const d = Math.max(2, (s.say || '').split(/\s+/).filter(Boolean).length / 2.6) + .35; const r = [t, t + d]; t += d; return r; }); };

  async function openChat(fresh) {
    const gen = ++C.gen;
    try { const c = await api(fresh ? 'POST' : 'GET', fresh ? `${C0}/chat/new` : `${C0}/chat`);
      if (gen !== C.gen) return;                    // she started another chat meanwhile: that one wins
      C.conv = c.id; C.title = c.title; }
    catch (e) { toast(e.message, true); }
  }
  async function chatLoad() {
    const conv = C.conv; if (!conv) return;
    let rows, items;
    try { rows = (await api('GET', `/api/conversations/${q(conv)}/messages?limit=200`)).messages || []; } catch { return; }
    try { items = (await api('GET', `${C0}/chat/${q(conv)}/items`)).items || []; } catch { items = null; }
    if (conv !== C.conv) return;                     // a slower load of the chat she just left never paints over this one
    C.rows = rows; if (items) C.items = items;
  }
  async function recentLoad() { try { UI.recent = ((await api('GET', `${C0}/chats`)).chats || []).slice(0, 4); if (ROOT && !ROOT.hidden) side(); } catch { UI.recent = []; } }
  async function meLoad() {
    try { const m = await api('GET', '/api/console/me'); const o = String(m.owner || ''); UI.me = o && o !== 'Hoola user' ? o.split(' ')[0] : ''; } catch { UI.me = ''; }
    try { const w = await api('GET', '/api/credits'); UI.credits = w && w.on && !w.exempt ? (w.unlocked ? w.paid_left : w.free_left) : null; } catch { UI.credits = null; }
    if (PAGE === 'chat' && ROOT && !ROOT.hidden) { crumb(); if ($('.hx-hero')) { const h = $('#hxGreet'); if (h) h.textContent = `${greet()}. What should your video say?`; } }
  }
  let estT = 0;
  function estimate() {
    clearTimeout(estT);
    estT = setTimeout(async () => {
      try { UI.est = await api('GET', `${X}/estimate?engine=${q(defEngine())}&seconds=${SET.len || 30}&voice=${q(SET.voice || '')}`); }
      catch { UI.est = null; }
      const el = $('#hxEst'); if (el) el.textContent = UI.est ? `About ${cr(UI.est.credits)}` : '';
    }, 250);
  }
  const fresh = () => !C.rows.some(r => r.role === 'user') && !C.items.length;
  function chatPoll() {
    clearTimeout(C.t);
    const tick = async () => {
      if (PAGE !== 'chat' || !ROOT || ROOT.hidden) return;
      const n = C.rows.length, m = C.items.map(i => i.id + i.status + i.updated).join();
      await chatLoad();
      if (C.rows.length !== n || C.items.map(i => i.id + i.status + i.updated).join() !== m) { if ($('.hx-hero') && !fresh()) draw(); else paintChat(); }
      const waiting = Date.now() < C.waitUntil && C.rows[C.rows.length - 1]?.role === 'user';
      C.t = setTimeout(tick, waiting || C.items.some(i => i.status === 'making') ? 2000 : 8000);
    };
    C.t = setTimeout(tick, 1500);
  }
  function chips(home = true) {
    const e = engine(defEngine()), f = face(SET.face), k = kindNow();
    const add = `<button type="button" class="hx-chip s" data-a="attach" aria-haspopup="menu" aria-label="Add a file or a web page">${ic('plus', 14)}</button>`;
    if (!home) return add;                          // in a chat the plan card holds every pick; the box stays one line
    return `${add}
      <button type="button" class="hx-chip s" data-a="pick" data-k="face" aria-haspopup="menu">${f ? avImg(f, 'xs') : ic('user', 14)}<span>${esc(f ? f.name : 'No face')}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="voice" aria-haspopup="menu">${ic('mic', 14)}<span>${esc(voiceName(SET.voice))}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="lang" aria-haspopup="menu">${ic('globe', 14)}<span>${esc(SET.lang && SET.lang !== 'auto' ? langName(SET.lang) : 'Auto · matches what you write')}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="len" aria-haspopup="menu">${ic('film', 14)}<span>${aspectOf(k)} · ${SET.len || 30} s</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="engine" aria-haspopup="menu">${ic('bolt', 14)}<span>${esc(e ? e.label : 'Hoola standard')}</span></button>`;
  }
  function tray() {
    return C.files.length ? `<div class="hx-tray">${C.files.map((f, i) => `<span class="hx-file">${f.up ? '<span class="hx-spin" aria-hidden="true"></span>' : ic('folder', 14)}<span>${esc(f.name)}</span>
      <button type="button" class="hx-ib s" data-a="unfile" data-n="${i}" aria-label="Remove ${esc(f.name)}">${ic('x', 13)}</button></span>`).join('')}</div>` : '';
  }
  function composer(home) {
    const ph = home ? (KINDS.find(k => k[0] === kindNow())?.[3] || KINDS[0][3]) : 'Change anything: a line, the tone, the length, the face';
    return `<div class="hx-comp${home ? ' home' : ''}" id="hxComp"><div class="hx-box"><label class="hx-sr" for="hxAsk">${home ? 'Describe your video' : 'Change the plan'}</label>
      <div id="hxTray">${tray()}</div>
      <textarea id="hxAsk" rows="${home ? 3 : 1}" placeholder="${esc(ph)}">${esc(C.ask)}</textarea>
      <div class="hx-boxrow"><div class="hx-chips" id="hxChips">${chips(home)}</div><span class="hx-grow"></span>
        ${home ? `<span class="hx-est hx-num" id="hxEst">${UI.est ? `About ${cr(UI.est.credits)}` : ''}</span>` : ''}
        <button type="button" class="hx-send${C.ask.trim() ? ' on' : ''}" data-a="send" aria-label="${home ? 'Plan the video' : 'Send'}">${ic('up', 18)}</button></div></div>
      ${home ? '' : '<p class="hx-foot">Hoola changes the plan. <b>Nothing is made until you tap Make.</b></p>'}</div>`;
  }
  function refreshBar() { const c = $('#hxChips'); if (c) { c.innerHTML = chips(!!$('#hxComp.home')); fillMedia(); } estimate(); }
  function vthumb(p) {
    const f = face(p.avatar_id), tall = p.aspect === '9:16';
    return `<span class="hx-vth${tall ? ' tall' : ''}" style="--brand:${esc(brandColor())}"><i class="l1"></i><i class="l2"></i>
      ${f ? `<span class="hx-vthf">${avImg(f, 'xs')}</span>` : ''}<span class="hx-vtht hx-num">${clock(lenOf(p))}</span></span>`;
  }
  function vstate(p) {
    return p.status === 'ready' ? ['ok', `Ready · ${langName(p.lang)}`] : p.status === 'making' ? ['work', 'Making it now'] : p.status === 'failed' ? ['bad', 'Could not be made'] : ['', 'Plan · not made yet'];
  }
  function vidsGrid() {
    const ps = (D.projects || []).slice(0, 8);
    return ps.length ? `<div class="hx-vgrid">${ps.map(p => { const [c, t] = vstate(p);
      return `<button type="button" class="hx-vc" data-a="openv" data-id="${esc(p.id)}">${vthumb(p)}<b>${esc(p.title)}</b><span class="hx-st ${c}">${esc(t)}</span></button>`; }).join('')}</div>`
      : `<p class="hx-mut hx-sm">Your videos appear here: plans you have not made yet, the ones being made, and the finished ones.</p>`;
  }
  function home() {
    const g = UI.ideaG || 'business';
    return `<div class="hx-hero"><div class="hx-herob">
        <h2 class="hx-serif" id="hxGreet">${esc(greet())}. What should your video say?</h2>
        <p class="hx-mut">Write it in any language. Hoola writes the script, plans the scenes and shows the price. Nothing is made until you tap Make.</p>
        <div class="hx-kinds" role="radiogroup" aria-label="Kind of video">${KINDS.map(([k, n, m]) => `<button type="button" role="radio" aria-checked="${kindNow() === k && SET.kind !== 'translate'}" class="hx-kind k-${k}" data-a="kind" data-val="${k}"><span class="hx-km" aria-hidden="true">${esc(m)}</span>${esc(n)}</button>`).join('')}</div>
        ${composer(true)}
        <p class="hx-foot c">The plan and a short voice sample are free. Credits are used only when you tap <b>Make the video</b>.</p></div>
      <section class="hx-sec" aria-labelledby="hxSt"><b class="hx-t" id="hxSt">Or start from something you have</b><div class="hx-starts">
        <button type="button" class="hx-start" data-a="from" data-val="doc"><span class="hx-sic">${ic('folder', 18)}</span><span><b>A document</b>A PDF or Word file into an explainer</span></button>
        <button type="button" class="hx-start" data-a="from" data-val="web"><span class="hx-sic">${ic('globe', 18)}</span><span><b>A web page</b>Your product page into a video</span></button>
        <button type="button" class="hx-start" data-a="from" data-val="slides"><span class="hx-sic">${ic('film', 18)}</span><span><b>Slides</b>A deck into a narrated lesson</span></button>
        <button type="button" class="hx-start" data-a="from" data-val="video"><span class="hx-sic">${ic('mic', 18)}</span><span><b>A video</b>Into another language, in the same voice</span></button></div></section>
      <section class="hx-sec" aria-labelledby="hxId"><div class="hx-sech"><b class="hx-t" id="hxId">Ideas</b>
        <div class="hx-gtabs" role="tablist" aria-label="Idea groups">${Object.entries(IDEA_G).map(([k, n]) => `<button type="button" role="tab" aria-selected="${g === k}" data-a="ideag" data-val="${k}">${esc(n)}</button>`).join('')}</div></div>
        <div class="hx-ideas">${IDEAS[g].map(([t, l, k], i) => `<button type="button" class="hx-idea" data-a="idea" data-n="${i}"><span>${esc(t)}</span>
          <span class="hx-tags"><span>${esc(langName(l))}</span><span>${esc(KIND_NAME[k])}</span></span></button>`).join('')}</div></section>
      <section class="hx-sec" aria-labelledby="hxYv"><div class="hx-sech"><b class="hx-t" id="hxYv">Your videos</b><span class="hx-grow"></span>
        ${(D.projects || []).length > 8 ? '<button type="button" class="hx-lnk" data-a="go" data-p="projects">See all</button>' : ''}</div>${vidsGrid()}</section></div>`;
  }

  // ---- the plan card
  function sceneGrid(it) {
    const f = face(it.avatar_id), on = UI.pv.id === it.id ? UI.pv.scene : -1;
    return `<div class="hx-scg">${(it.scenes || []).map((s, i) => { const lk = s.look?.kind && s.look.kind !== 'none';
      return `<button type="button" class="hx-sct${i === on ? ' on' : ''}" data-a="pvscene" data-id="${esc(it.id)}" data-n="${i}" aria-label="Scene ${i + 1}">
        <span class="hx-scth" style="--brand:${esc(brandColor())}"><small class="hx-num">${i + 1} · ${clock(sceneTimes(it)[i][0])}</small><i></i>${f && (it.face_layout !== 'full' || i === 0) ? `<span class="hx-scf">${avImg(f, 'xs')}</span>` : ''}</span>
        <b>${esc(lk ? (LOOK[s.look.kind] || 'Scene') : (f ? 'Presenter' : 'Words'))}</b><span class="hx-scl">${esc(s.say)}</span>${s.needs ? `<em>${esc(s.needs)}</em>` : ''}</button>`; }).join('')}</div>`;
  }
  function priceBox(qn) {
    if (!qn) return '';
    return `<div class="hx-pbox hx-num"><div><span>Voice, about ${secs(qn.seconds)}</span><span>${qn.voice_credits ? cr(qn.voice_credits) : 'Included'}</span></div>
      <div><span>${esc(qn.label)}${qn.face_credits ? ', the talking face' : ''}</span><span>${qn.face_credits ? cr(qn.face_credits) : 'Included'}</span></div>
      <div><span>Scenes, titles and subtitles</span><span>Included</span></div>
      <div class="t"><span>Total</span><span>${cr(qn.credits)}${qn.usd ? ` <small>≈ US$${(+qn.usd).toFixed(2)}</small>` : ''}</span></div></div>`;
  }
  function planCard(it, newest) {
    const e = engine(it.engine) || engine('hoola'), f = face(it.avatar_id), qn = it.quote || null, pr = it.problems || [];
    const making = it.status === 'making', ready = it.status === 'ready', failed = it.status === 'failed';
    const meta = [KIND_NAME[it.kind] || SHAPE[it.shape] || 'Video', `${(it.scenes || []).length} scenes`, it.aspect || '16:9', clock(lenOf(it)), langName(it.lang)].join(' · ');
    const head = `<div class="hx-planh"><span class="hx-ct"><b>${esc(it.title)}</b><small>${esc(meta)}</small></span>${ready ? '' : `<span class="hx-pstate ${making ? 'work' : failed ? 'bad' : ''}">${making ? 'Making it' : failed ? 'Not made' : 'Plan · nothing made yet'}</span>`}</div>`;
    if (ready) return `<article class="hx-plan" data-id="${esc(it.id)}" aria-label="Finished video">${head}
      <div class="hx-vwrap"><video class="hx-player" controls playsinline preload="metadata" data-vid="${esc(it.id)}"></video><span class="hx-aimark">Made with AI</span></div>
      <div class="hx-acts"><span class="hx-mut hx-sm hx-num">${esc(it.video?.engine_label || e?.label || '')}${it.video?.credits ? ' · used ' + cr(it.video.credits) : ''}</span><span class="hx-grow"></span>
        <button type="button" class="hx-btn dark" data-a="dlv" data-id="${esc(it.id)}">${ic('dl', 14)}Download MP4</button>
        <button type="button" class="hx-btn" data-a="openp" data-id="${esc(it.id)}">Open in Studio</button></div>
      <div class="hx-next"><b class="hx-sm">Next with this video</b><div class="hx-nextg">
        <button type="button" class="hx-nx" data-a="morelang" data-id="${esc(it.id)}"><b>More languages</b><span>Same face and voice, in any of 140</span></button>
        <button type="button" class="hx-nx" data-a="say" data-t="Make a 9:16 reel version of this video, about 15 seconds, for Instagram and TikTok."><b>Reel cut</b><span>A vertical version for social media</span></button>
        <button type="button" class="hx-nx" data-a="openp" data-id="${esc(it.id)}"><b>Change a line</b><span>Edit the script in the Studio, make it again</span></button>
        <button type="button" class="hx-nx" data-a="tplsave" data-id="${esc(it.id)}"><b>Save as a template</b><span>Reuse it with new names and numbers</span></button></div></div>
      ${newest ? `<div class="hx-mk"><span class="hx-mut hx-sm">Make it in:</span>${MORE_LANGS.filter(c => c !== it.lang).slice(0, 5).map(c => `<button type="button" class="hx-chip s" data-a="say" data-t="Make the same video in ${esc(langName(c))}, keeping every name and number.">${esc(langName(c))}</button>`).join('')}
        <button type="button" class="hx-chip s" data-a="morelang" data-id="${esc(it.id)}">${ic('plus', 13)}Choose</button></div>` : ''}</article>`;
    return `<article class="hx-plan" data-id="${esc(it.id)}" aria-label="Video plan">${head}
      ${sceneGrid(it)}
      <div class="hx-prow"><span class="k">Face</span>${avImg(f, 'xs')}<span class="v">${esc(f ? f.name : 'No face')}<small>${f ? 'Consent on record' : 'Scenes and voice only'}</small></span>
        ${f ? `<div class="hx-seg" role="radiogroup" aria-label="Where the face appears"><button type="button" role="radio" aria-checked="${it.face_layout !== 'full'}" data-a="flay" data-id="${esc(it.id)}" data-val="corner">In a corner</button><button type="button" role="radio" aria-checked="${it.face_layout === 'full'}" data-a="flay" data-id="${esc(it.id)}" data-val="full">Full frame</button></div>` : ''}
        <button type="button" class="hx-btn s" data-a="ipick" data-k="face" data-id="${esc(it.id)}"${making ? ' disabled' : ''}>Change</button></div>
      <div class="hx-prow"><span class="k">Voice</span><button type="button" class="hx-hear" data-a="hear" data-id="${esc(it.id)}" aria-label="Hear a short sample, free">${ic('play', 12)}</button>
        <span class="v">${esc(voiceName(it.voice))}<small>Hear a short sample, free</small></span>
        <button type="button" class="hx-btn s" data-a="ipick" data-k="voice" data-id="${esc(it.id)}"${making ? ' disabled' : ''}>Change</button></div>
      <div class="hx-prow"><span class="k">Language</span><span class="v">${esc(langName(it.lang))}<small>Spoken, with subtitles in the same language</small></span>
        <button type="button" class="hx-btn s" data-a="morelang" data-id="${esc(it.id)}">${ic('plus', 13)}Another language</button></div>
      <div class="hx-prow"><span class="k">Engine</span><span class="v">${esc(e ? e.label : 'Hoola standard')}<small>${esc(e?.what || '')}</small></span>
        <button type="button" class="hx-btn s" data-a="cmp" data-id="${esc(it.id)}"${making ? ' disabled' : ''}>Compare engines</button></div>
      ${priceBox(qn)}
      ${pr.length ? `<ul class="hx-why">${pr.map(w => `<li>${esc(scrub(w))}</li>`).join('')}</ul>` : ''}
      ${failed && it.error ? `<p class="hx-why">${esc(scrub(it.error))}</p>` : ''}
      <div id="hxJob-${esc(it.id)}">${making ? '<p class="hx-mut hx-sm">Making it…</p>' : ''}</div>
      ${making ? '' : `<div class="hx-acts big">
        <button type="button" class="hx-btn dark l" data-a="make" data-id="${esc(it.id)}" data-k="${esc(qn?.key || '')}"${pr.length ? ' disabled' : ''}>${failed ? 'Try again' : 'Make the video'}${qn ? ' · ' + cr(qn.credits) : ''}</button>
        <button type="button" class="hx-btn l" data-a="openp" data-id="${esc(it.id)}">Open in Studio</button><span class="hx-grow"></span>
        <span class="hx-mut hx-sm hx-pnote">If the face engine fails, its credits are not used. The plan stays.</span></div>`}</article>
      ${newest && !making ? `<div class="hx-sugg">${SUGGEST.map(t => `<button type="button" class="hx-chip s" data-a="say" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}`;
  }
  function thread() {
    const items = [...C.items].reverse();
    const out = [];
    let it = 0;
    const rows = C.rows.filter(r => r.role === 'user' || r.role === 'assistant');
    const last = items[items.length - 1]?.id;
    const mark = `<span class="hx-mark s" aria-hidden="true">${markSvg()}</span>`;
    rows.forEach(r => {
      while (it < items.length && Date.parse(items[it].created) <= Date.parse(r.at)) { const x = items[it++]; out.push(`<div class="hx-turn">${mark}<div class="hx-tb">${planCard(x, x.id === last)}</div></div>`); }
      out.push(r.role === 'user' ? `<div class="hx-me">${esc(strip(r.text))}</div>` : `<div class="hx-turn">${mark}<div class="hx-tb"><div class="hx-ho">${esc(r.text).replace(/\n/g, '<br>')}</div></div></div>`);
    });
    while (it < items.length) { const x = items[it++]; out.push(`<div class="hx-turn">${mark}<div class="hx-tb">${planCard(x, x.id === last)}</div></div>`); }
    if (C.sending || (Date.now() < C.waitUntil && rows[rows.length - 1]?.role === 'user')) out.push(`<div class="hx-working"><span class="hx-mark s">${markSvg()}</span><span>Writing the script and planning the scenes…</span></div>`);
    return out.join('');
  }

  // ---- the preview beside the chat: a sketch, the script, the subtitles of one plan
  const pvItem = () => C.items.find(i => i.id === UI.pv.id) || C.items[0];
  function srt(p, vtt) {
    const T = sceneTimes(p), fmt = s => { const ms = Math.round(s * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, ss = Math.floor(ms / 1000) % 60;
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}${vtt ? '.' : ','}${String(ms % 1000).padStart(3, '0')}`; };
    const body = (p.scenes || []).map((s, i) => `${vtt ? '' : (i + 1) + '\n'}${fmt(T[i][0])} --> ${fmt(T[i][1])}\n${s.say}`).join('\n\n');
    return vtt ? `WEBVTT\n\n${body}\n` : `${body}\n`;
  }
  function sketch(p) {
    const n = Math.min(UI.pv.scene, (p.scenes || []).length - 1), sc = p.scenes[n] || {}, f = face(p.avatar_id), full = p.face_layout === 'full';
    const T = sceneTimes(p), total = T.length ? T[T.length - 1][1] : 1, at = T[n] ? T[n][0] : 0;
    return `<div class="hx-preview ${p.aspect === '9:16' ? 'tall' : p.aspect === '1:1' ? 'sq' : ''}" style="--brand:${esc(brandColor())}">
        ${f && full ? `<span class="hx-pvfull">${avImg(f, 'xl')}</span>` : ''}
        <div class="hx-pvlook">${lookText(sc.look) ? `<b>${esc(lookText(sc.look))}</b>` : n === 0 ? `<b>${esc(p.title)}</b>` : ''}</div>
        ${f && !full ? `<span class="hx-pvface">${avImg(f, 'l')}</span>` : ''}<p class="hx-pvcap">${esc(sc.say || '')}</p></div>
      <div class="hx-pvbar"><button type="button" class="hx-pplay" data-a="pvplay" aria-label="${UI.pv.play ? 'Pause the sketch' : 'Play the sketch'}">${ic(UI.pv.play ? 'stop' : 'play', 14)}</button>
        <span class="hx-track"><i style="width:${Math.round(100 * at / total)}%"></i></span><span class="hx-mut hx-sm hx-num">${clock(at)} / ${clock(total)}</span></div>
      <p class="hx-mut hx-sm">A free sketch with the real scenes and timing. Your talking face and the voice are made when you tap Make.</p>`;
  }
  function pvPane() {
    const p = pvItem();
    if (!p) return `<div class="hx-pvempty"><span class="hx-mark l" aria-hidden="true">${markSvg()}</span><b>Your plan appears here</b><span class="hx-mut hx-sm">A sketch of every scene, the script and the subtitles, before anything is made.</span></div>`;
    const tab = UI.pv.tab;
    const body = p.status === 'ready' && tab === 'sketch' ? `<div class="hx-vwrap"><video class="hx-player" controls playsinline preload="metadata" data-vid="${esc(p.id)}"></video><span class="hx-aimark">Made with AI</span></div>`
      : tab === 'sketch' ? sketch(p)
      : tab === 'script' ? `<p class="hx-mut hx-sm">Change any line here; the plan updates and the price follows.${p.status === 'ready' ? ' Make it again for a new version.' : ''}</p>
          <ol class="hx-pvscript">${(p.scenes || []).map((s, i) => `<li><span class="hx-mut hx-sm hx-num">Scene ${i + 1} · ${clock(sceneTimes(p)[i][0])}</span>
            <textarea class="hx-in hx-serifp" rows="2" data-isc="${i}" data-id="${esc(p.id)}" aria-label="Scene ${i + 1} words"${p.status === 'making' ? ' disabled' : ''}>${esc(s.say)}</textarea></li>`).join('')}</ol>`
      : `<pre class="hx-srt">${esc(srt(p))}</pre><div class="hx-acts"><button type="button" class="hx-btn s" data-a="subdl" data-val="srt">${ic('dl', 13)}Download .srt</button>
          <button type="button" class="hx-btn s" data-a="subdl" data-val="vtt">${ic('dl', 13)}Download .vtt</button></div>
          <p class="hx-mut hx-sm">${p.status === 'ready' ? 'Timed from the plan; the finished video follows the same scenes.' : 'Timed from the plan. The finished video follows the same scenes.'}</p>`;
    return `<div class="hx-pvh"><div class="hx-tabs" role="tablist" aria-label="Preview">${[['sketch', p.status === 'ready' ? 'Video' : 'Sketch'], ['script', 'Script'], ['subs', 'Subtitles']].map(([k, n]) => `<button type="button" role="tab" aria-selected="${tab === k}" data-a="pvtab" data-val="${k}">${n}</button>`).join('')}</div>
      <span class="hx-grow"></span>${C.items.length > 1 ? `<button type="button" class="hx-btn s" data-a="pvwhich" aria-haspopup="menu">${esc((p.title || '').slice(0, 22))}${ic('down', 13)}</button>` : ''}</div>
      <div class="hx-pvb">${body}</div>`;
  }
  function paintPv() { const a = $('#hxPv'); if (!a) return; a.innerHTML = pvPane(); fillMedia(); }
  function paintChat() {
    const t = $('#hxThread'); if (!t) return; const log = $('#hxLog'), atEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 80;
    t.innerHTML = thread(); fillMedia(); if (atEnd) log.scrollTop = log.scrollHeight;
    if (!C.items.some(i => i.id === UI.pv.id)) { UI.pv.id = C.items[0]?.id || ''; UI.pv.scene = 0; }
    if (!$('#hxPv textarea:focus')) paintPv();
    C.items.filter(i => i.status === 'making').forEach(i => watchJob(i.id));
  }
  function pvStop() { clearTimeout(UI.pv.t); UI.pv.play = false; }
  function pvPlay() {
    const p = pvItem(); if (!p) return;
    if (UI.pv.play) { pvStop(); return paintPv(); }
    UI.pv.play = true; if (UI.pv.scene >= p.scenes.length - 1) UI.pv.scene = 0;
    const step = () => {
      if (!UI.pv.play || PAGE !== 'chat') return;
      paintPv(); const T = sceneTimes(p)[UI.pv.scene]; const d = T ? (T[1] - T[0]) * 1000 : 2500;
      UI.pv.t = setTimeout(() => { if (UI.pv.scene < p.scenes.length - 1) { UI.pv.scene++; step(); } else { pvStop(); paintPv(); } }, d);
    };
    step();
  }
  async function saveItem(id, body) {
    try { const p = await api('PUT', `${S}/project?id=${q(id)}`, body); const i = (D.projects || []).findIndex(x => x.id === id); if (i >= 0) D.projects[i] = p;
      await chatLoad(); paintChat(); }
    catch (e) { toast(e.message, true); }
  }
  let iscT = 0;
  function saveLine(id, n, text) {
    const p = C.items.find(x => x.id === id); if (!p) return;
    p.scenes = p.scenes.map((s, i) => i === n ? {...s, say: text} : s);
    clearTimeout(iscT); iscT = setTimeout(() => saveItem(id, {scenes: p.scenes}), 700);
  }
  async function hear(id, line) {
    const p = C.items.find(x => x.id === id) || (D.projects || []).find(x => x.id === id), text = (line || p?.scenes?.[0]?.say || p?.title || '').split(/(?<=[.!?。！？])\s/)[0].slice(0, 160);
    if (!text) return;
    try { const r = await api('POST', '/api/vocal/hear', {text, voice: p.voice || '', lang: p.lang || ''}, {raw: true});
      if (!r.ok) { let m = 'The sample could not be made.'; try { m = (await r.json()).detail || m; } catch { /* keep */ } throw new Error(m); }
      UI.audio?.pause(); UI.audio = new Audio(URL.createObjectURL(await r.blob())); UI.audio.play().catch(() => {}); }
    catch (e) { toast(e.message, true); }
  }
  async function compare(el, id) {
    let r; try { r = await api('GET', `${X}/compare?id=${q(id)}`); } catch (e) { return toast(e.message, true); }
    menu(el, [{header: `Price for this ${secs(r.seconds)} video`}, ...r.engines.map(e => ({label: e.label, sub: e.ready ? `${cr(e.credits)} · ${e.what}` : `Not connected · ${e.what}`,
      disabled: !e.ready, checked: r.chosen === e.id, run: () => saveItem(id, {engine: e.id})})), {sep: true}, {label: 'Set a default engine', icon: 'bolt', run: () => go('engines')}], {width: 340});
  }
  async function addFiles(list, kind, ask) {
    if (!C.conv) await openChat(); if (!C.conv) return;
    for (const file of list) {
      if (file.size > 30 * 1024 * 1024) { toast(`${file.name} is larger than 30 MB.`, true); continue; }
      const row = {name: file.name, up: true}; C.files.push(row); const tr = $('#hxTray'); if (tr) tr.innerHTML = tray();
      try { const fd = new FormData(); fd.append('file', file, file.name); const r = await api('POST', `/api/conversations/${q(C.conv)}/files`, undefined, {form: fd}); row.id = r.file_id; row.up = false; }
      catch (e) { C.files.splice(C.files.indexOf(row), 1); toast(e.message, true); }
      const t2 = $('#hxTray'); if (t2) t2.innerHTML = tray();
    }
    if (kind) { SET.kind = kind; store.set('hx.set', SET); }
    if (ask && !C.ask.trim()) { C.ask = ask; const t = $('#hxAsk'); if (t) t.value = ask; }
    if ($('.hx-hero')) draw(); $('.hx-send')?.classList.toggle('on', !!C.ask.trim()); $('#hxAsk')?.focus();
  }
  function pickFiles(accept, kind, ask) {
    const i = document.createElement('input'); i.type = 'file'; i.multiple = true; i.accept = accept || '';
    i.onchange = () => { if (i.files?.length) addFiles([...i.files], kind, ask); }; i.click();
  }
  function fromWeb() {
    const u = (prompt('Paste the address of the web page') || '').trim(); if (!u) return;
    if (!/^https?:\/\/\S+\.\S+/i.test(u)) return toast('Paste a full web address that starts with https://', true);
    SET.kind = 'product'; store.set('hx.set', SET); C.ask = `Make a product video from this page: ${u}`; draw(); $('#hxAsk')?.focus(); $('.hx-send')?.classList.add('on');
  }
  function toDubbing() { window.__hvPage = 'dub'; leave(); return ctx.go ? ctx.go('vocal') : back?.(); }
  async function chatSend(textIn) {
    const text = String(textIn ?? $('#hxAsk')?.value ?? C.ask).trim();
    if (C.files.some(f => f.up)) return toast('Wait for the files to finish uploading.');
    if (!text && !C.files.length) { $('#hxAsk')?.focus(); toast('Say what the video should say first.'); return; }
    if (!C.conv) await openChat(); if (!C.conv) return;
    const files = textIn == null ? C.files.filter(f => f.id) : [];
    const said = text || 'Make a video from the file I attached.';
    C.sending = true; if (textIn == null) { C.ask = ''; C.files = []; } const ta = $('#hxAsk'); if (ta && textIn == null) ta.value = '';
    C.rows.push({role: 'user', text: said + (files.length ? `\n(${files.map(f => f.name).join(', ')})` : ''), at: new Date().toISOString()});
    pvStop();
    if ($('.hx-hero')) draw(); else paintChat();
    try {
      await api('POST', `/api/conversations/${q(C.conv)}/messages`, {text: `${said}\n\n${settingsNote()}`, files: files.map(f => f.id), client_id: 'ix' + Date.now().toString(36)});
      C.waitUntil = Date.now() + 180000;
    } catch (e) { toast(e.message, true); if (textIn == null) C.ask = text; }
    C.sending = false; await chatLoad(); paintChat(); chatPoll(); recentLoad();
  }

  // ------------------------------------------------------------------ the make job ---
  async function make(id, key) {
    try {
      await api('POST', `${X}/make`, {id, quote_key: key || ''});
      toast('Making the video. You can leave this page; it carries on.');
      await load(); await chatLoad(); PAGE === 'chat' ? paintChat() : draw(); watchJob(id);
    } catch (e) { toast(e.message, true); }
  }
  function jobHTML(j) {
    if (!j || !j.steps) return '';
    const steps = j.steps.filter(s => s.k !== 'done' && (s.k !== 'face' || (j.engine && j.engine !== 'hoola')));
    const pct = jobPct(j);
    return `<div class="hx-jobh"><span class="hx-ct"><b>${j.done ? (j.status === 'ready' ? 'Ready' : j.status === 'failed' ? 'Not made' : 'Stopped') : 'Making the video'}</b>
        <small class="hx-num">Working for ${clock(j.elapsed)}${j.credits ? ' · ' + cr(j.credits) : ''}</small></span><span class="hx-grow"></span>
        ${j.done ? '' : `<button type="button" class="hx-btn s danger" data-a="stop" data-id="${esc(j.pid)}">${ic('stop', 14)}Stop</button>`}</div>
      <div class="hx-pbar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div>
      <ol class="hx-steps">${steps.map(s => {
      const ok = s.at != null && s.k !== j.current, now = s.k === j.current && !j.done;
      return `<li class="${ok ? 'ok' : now ? 'now' : ''}">${ok ? ic('check', 14) : now ? '<span class="hx-spin" aria-hidden="true"></span>' : '<span class="hx-dot"></span>'}
        <span>${esc(s.label)}</span>${s.detail ? `<small>${esc(scrub(s.detail))}</small>` : ''}</li>`; }).join('')}</ol>
      ${j.done ? '' : '<p class="hx-mut hx-sm">You can close this page. The video keeps being made, and it appears here when it is ready.</p>'}
      ${j.error && j.status === 'failed' ? `<p class="hx-why">${esc(scrub(j.error))}</p>` : ''}`;
  }
  function watchJob(id) {
    if (UI.jobs[id]) return;
    const tick = async () => {
      let j; try { j = await api('GET', `${S}/progress?id=${q(id)}`); } catch { delete UI.jobs[id]; return; }
      const box = $(`#hxJob-${CSS.escape(id)}`); if (box) box.innerHTML = jobHTML(j);
      UI.jp[id] = jobPct(j); $$(`[data-jobm="${CSS.escape(id)}"] i`).forEach(i => { i.style.width = UI.jp[id] + '%'; });
      if (j.done) { delete UI.jobs[id]; await load(); if (PAGE === 'chat') { await chatLoad(); paintChat(); } else draw();
        if (j.status === 'ready') toast('Your video is ready.'); else if (j.status === 'failed') toast(j.error || 'The video could not be made.', true); return; }
      UI.jobs[id] = setTimeout(tick, 2000);
    };
    UI.jobs[id] = setTimeout(tick, 600);
  }
  async function download(id) {
    const p = (D.projects || []).find(x => x.id === id);
    try { const a = document.createElement('a'); a.href = await blobUrl(`${S}/video?id=${q(id)}`); a.download = `${(p?.title || 'hoola-video').replace(/[^\w .-]+/g, '_').slice(0, 60)}.mp4`; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); }
  }

  // ------------------------------------------------------------------ the Studio (v0.999.173: the library + the editor) ---
  const LIBF = [['all', 'All'], ['plan', 'Plans'], ['making', 'Making'], ['ready', 'Ready'], ['failed', 'Not made']];
  const LSORT = {new: 'Newest first', old: 'Oldest first', title: 'Title A to Z'};
  const TOOLS = ['Scene', 'Face', 'Voice', 'Engine', 'Video'];
  const libKind = p => p.status === 'ready' ? 'ready' : p.status === 'making' ? 'making' : p.status === 'failed' ? 'failed' : 'plan';
  const total = p => { const T = sceneTimes(p); return p?.video?.duration || (T.length ? T[T.length - 1][1] + (p.closing ? 2.2 : 1.2) : 0); };
  const metaOf = p => [KIND_NAME[p.kind] || SHAPE[p.shape] || 'Video', langName(p.lang), clock(total(p))].join(' · ');
  function jobPct(j) {
    if (!j || !j.steps) return 4;
    const steps = j.steps.filter(s => s.k !== 'done' && (s.k !== 'face' || (j.engine && j.engine !== 'hoola')));
    const done = steps.filter(s => s.at != null && s.k !== j.current).length;
    return j.done ? 100 : Math.max(4, Math.round(100 * (done + .5) / Math.max(1, steps.length)));
  }
  function libRows() {
    const qy = (UI.lq || '').trim().toLowerCase(), f = UI.lf || 'all', s = UI.ls || 'new';
    const ps = (D.projects || []).filter(p => (f === 'all' || libKind(p) === f)
      && (!qy || `${p.title} ${p.ask || ''} ${(p.scenes || []).map(x => x.say).join(' ')}`.toLowerCase().includes(qy)));
    return ps.sort((a, b) => s === 'title' ? String(a.title).localeCompare(String(b.title))
      : s === 'old' ? String(a.updated || '').localeCompare(String(b.updated || '')) : String(b.updated || '').localeCompare(String(a.updated || '')));
  }
  function libThumb(p) {
    const k = libKind(p);
    const f = face(p.avatar_id), sc = (p.scenes || [])[0] || {}, lt = lookText(sc.look) || p.title;
    return `<span class="hx-lth"><span class="hx-pst k-${esc(p.kind || 'presenter')}${p.aspect === '9:16' ? ' tall' : ''}" style="--brand:${esc(brandColor())}"><b>${esc(lt)}</b>${sc.say ? `<small>${esc(sc.say)}</small>` : ''}
      ${f ? `<span class="hx-pstf">${avImg(f, 'xs')}</span>` : ''}<span class="hx-vtht hx-num">${clock(total(p))}</span></span>${k === 'ready' ? `<span class="hx-lplay" aria-hidden="true">${ic('play', 16)}</span>` : ''}
      ${k === 'making' ? `<span class="hx-lbar" data-jobm="${esc(p.id)}"><i style="width:${UI.jp[p.id] || 4}%"></i></span>` : ''}</span>`;
  }
  function libCard(p) {
    return `<article class="hx-lc" data-k="${libKind(p)}">
      <button type="button" class="hx-lco" data-a="openp" data-id="${esc(p.id)}" aria-label="Open ${esc(p.title)}">${libThumb(p)}</button>
      <div class="hx-lcb"><button type="button" class="hx-lct" data-a="openp" data-id="${esc(p.id)}" tabindex="-1">${esc(p.title)}</button>
        <span class="hx-lcm hx-num">${esc(metaOf(p))} · ${(p.scenes || []).length} scenes</span>
        <div class="hx-lcf">${chip(p)}<span class="hx-mut hx-sm">${esc(ago(p.updated))}</span><span class="hx-grow"></span>
          <button type="button" class="hx-ib s" data-a="vmenu" data-id="${esc(p.id)}" aria-label="More for ${esc(p.title)}">${ic('dots', 16)}</button></div></div></article>`;
  }
  function libRow(p) {
    return `<div class="hx-lr" role="row"><button type="button" class="hx-lro" data-a="openp" data-id="${esc(p.id)}">${libThumb(p)}
        <span class="hx-ct"><b>${esc(p.title)}</b><small class="hx-num">${esc(metaOf(p))} · ${(p.scenes || []).length} scenes</small></span></button>
      <span class="hx-lrs">${chip(p)}</span><span class="hx-mut hx-sm hx-lru">${esc(ago(p.updated))}</span>
      <button type="button" class="hx-ib s" data-a="vmenu" data-id="${esc(p.id)}" aria-label="More for ${esc(p.title)}">${ic('dots', 16)}</button></div>`;
  }
  function libList() {
    const rows = libRows();
    if (!rows.length) return `<div class="hx-empty"><b>No videos match</b><span>Try another word, or show every video.</span>
      <button type="button" class="hx-btn s" data-a="lclear">Show all videos</button></div>`;
    return UI.lv === 'list' ? `<div class="hx-lrows hx-card" role="table" aria-label="Your videos">${rows.map(libRow).join('')}</div>`
      : `<div class="hx-lgrid">${rows.map(libCard).join('')}</div>`;
  }
  function libEmpty() {
    const tp = (D.templates || []).length;
    return `<div class="hx-doc hx-lib"><div class="hx-lempty">
      <div class="hx-lart" aria-hidden="true" style="--brand:${esc(brandColor())}"><span class="f"><i class="t"></i><i class="t2"></i><i class="c"></i><b class="av"></b></span>
        <span class="r"><i></i><i></i><i></i><i></i></span></div>
      <h2 class="hx-serif">Your first video starts with one sentence</h2>
      <p class="hx-mut">Say what it should say, in any language. Hoola writes the scenes; you check the plan and the price. Nothing is made until you tap Make.</p>
      <div class="hx-lstarts">
        <button type="button" class="hx-lst" data-a="newchat"><span class="hx-lsi a">${ic('chat', 18)}</span><b>Describe it</b><span>Write or say what the video is for</span></button>
        <button type="button" class="hx-lst" data-a="go" data-p="templates"><span class="hx-lsi b">${ic('grid', 18)}</span><b>Start from a template</b><span>${tp ? `${num(tp)} ready-made videos; your words fill the blanks` : 'Ready-made videos; your words fill the blanks'}</span></button>
        <button type="button" class="hx-lst" data-a="lfrom"><span class="hx-lsi c">${ic('doc', 18)}</span><b>From a document</b><span>A PDF, Word file or slides become an explainer</span></button></div>
      <ol class="hx-how"><li><span class="n">1</span><span><b>Say it</b>One line, any language</span></li>
        <li><span class="n">2</span><span><b>Check the plan</b>Scenes, face, voice and the price</span></li>
        <li><span class="n">3</span><span><b>Make it</b>Your tap; it carries on if you leave</span></li></ol></div></div>`;
  }
  function libPage() {
    const all = D.projects || [];
    if (!all.length) return libEmpty();
    const n = k => all.filter(p => k === 'all' || libKind(p) === k).length, u = D.usage || {};
    const waiting = all.filter(p => libKind(p) === 'plan' && (p.scenes || []).some(s => s.needs)).length;
    const kpi = (lab, val, sub) => `<div class="hx-kpi"><span>${lab}</span><b class="hx-num">${val}</b><small>${sub}</small></div>`;
    return `<div class="hx-doc hx-lib"><div class="hx-libh"><div class="hx-growf"><h2 class="hx-serif">Studio</h2>
        <p class="hx-mut">Every video you planned or made. Open one to change its scenes, face, voice and engine.</p></div>
        <div class="hx-acts"><button type="button" class="hx-btn" data-a="go" data-p="templates">${ic('grid', 14)}From a template</button>
          <button type="button" class="hx-btn dark" data-a="newchat">${ic('plus', 14)}New video</button></div></div>
      <div class="hx-kpis">${kpi('Videos', num(all.length), `${num(n('ready'))} ready to download`)}
        ${kpi('Plans', num(n('plan')), waiting ? `${num(waiting)} need your numbers` : 'Nothing is spent until you tap')}
        ${kpi('Made this month', num(u.videos || 0), `${num(u.minutes || 0)} minutes`)}
        ${kpi('Kept on Hoola', `${num(u.stored || 0)}<small> of ${num(u.kept_max || 0)}</small>`, 'Older videos make room for new ones')}</div>
      <div class="hx-libbar"><div class="hx-seg hx-lf" role="tablist" aria-label="Show">${LIBF.map(([k, l]) => `<button type="button" role="tab" aria-selected="${(UI.lf || 'all') === k}" aria-checked="${(UI.lf || 'all') === k}" data-a="lf" data-val="${k}">${l}<span class="hx-num">${num(n(k))}</span></button>`).join('')}</div>
        <span class="hx-grow"></span>
        <label class="hx-lsearch">${ic('search', 15)}<span class="hx-sr">Find a video</span><input id="hxLq" type="search" placeholder="Find a video" value="${esc(UI.lq || '')}" autocomplete="off"></label>
        <button type="button" class="hx-btn" data-a="lsort">${ic('sort', 14)}<span>${LSORT[UI.ls || 'new']}</span></button>
        <div class="hx-seg hx-lv" role="radiogroup" aria-label="View">${[['grid', 'grid', 'Cards'], ['list', 'rows', 'List']].map(([k, i, l]) => `<button type="button" role="radio" aria-checked="${(UI.lv || 'grid') === k}" data-a="lview" data-val="${k}" aria-label="${l}" title="${l}">${ic(i, 15)}</button>`).join('')}</div></div>
      <div id="hxLibList">${libList()}</div>
      ${(D.trash || []).length ? `<button type="button" class="hx-lnk hx-ltrash" data-a="ltrash">${ic('trash', 14)}Trash · ${num(D.trash.length)} video${D.trash.length === 1 ? '' : 's'}, kept for 30 days</button>` : ''}</div>`;
  }

  // the editor
  function edStage(p) {
    const n = Math.min(UI.scene, Math.max(0, p.scenes.length - 1)), sc = p.scenes[n] || {say: '', look: {kind: 'none'}}, f = face(p.avatar_id), full = p.face_layout === 'full';
    const T = sceneTimes(p), tot = total(p), at = T[n] ? T[n][0] : 0, vid = p.status === 'ready' && UI.edv !== 'sketch';
    const lt = lookText(sc.look) || (n === 0 ? p.title : '');
    return `<div class="hx-edframe"><div class="hx-preview ${p.aspect === '9:16' ? 'tall' : p.aspect === '1:1' ? 'sq' : ''}" style="--brand:${esc(brandColor())}">
        ${vid ? `<video class="hx-player" controls playsinline preload="metadata" data-vid="${esc(p.id)}"></video><span class="hx-aimark">Made with AI</span>`
          : `${f && full ? `<span class="hx-pvfull">${avImg(f, 'xl')}</span>` : ''}
            <div class="hx-pvlook">${lt ? `<b>${esc(lt)}</b>` : ''}</div>${f && !full ? `<span class="hx-pvface">${avImg(f, 'l')}</span>` : ''}
            <p class="hx-pvcap">${esc(sc.say || '')}</p>`}</div></div>
      <div class="hx-edctl">${vid ? `<span class="hx-mut hx-sm">The finished video. Tap a scene below to jump to it.</span>`
        : `<button type="button" class="hx-pplay" data-a="edplay" aria-label="${UI.edp ? 'Pause the sketch' : 'Play the sketch'}">${ic(UI.edp ? 'stop' : 'play', 14)}</button>
          <button type="button" class="hx-ib s" data-a="scprev" aria-label="Previous scene"${n ? '' : ' disabled'}>${ic('back', 15)}</button>
          <button type="button" class="hx-ib s" data-a="scnext" aria-label="Next scene"${n < p.scenes.length - 1 ? '' : ' disabled'}>${ic('fwd', 15)}</button>
          <span class="hx-sm hx-num"><b>Scene ${n + 1}</b> of ${p.scenes.length} · ${clock(at)} / ${clock(tot)}</span>`}
        <span class="hx-grow"></span>
        ${p.status === 'ready' ? `<div class="hx-seg" role="radiogroup" aria-label="Show">${[['video', 'Video'], ['sketch', 'Sketch']].map(([k, l]) => `<button type="button" role="radio" aria-checked="${(UI.edv || 'video') === k}" data-a="edview" data-val="${k}">${l}</button>`).join('')}</div>` : ''}</div>`;
  }
  function edTimeline(p) {
    const T = sceneTimes(p), tot = total(p);
    return `<div class="hx-tl" role="tablist" aria-label="Scenes on the timeline">${p.scenes.map((s, i) => {
      const lk = s.look?.kind && s.look.kind !== 'none';
      return `<button type="button" role="tab" aria-selected="${i === UI.scene}" class="hx-tlb${i === UI.scene ? ' on' : ''}${s.needs ? ' warn' : ''}" data-a="scene" data-n="${i}" style="flex:${(T[i][1] - T[i][0]).toFixed(2)} 1 0" title="Scene ${i + 1} · ${clock(T[i][0])}">
        <span class="hx-num">${i + 1}</span><small>${esc(lk ? LOOK[s.look.kind] : (s.say || '').slice(0, 40))}</small></button>`; }).join('')}
      ${p.closing ? `<span class="hx-tlb end" style="flex:2.2 1 0" title="Closing card"><small>${esc(p.closing)}</small></span>` : ''}</div>
      <div class="hx-tlr hx-num"><span>0:00</span><span>${clock(tot / 2)}</span><span>${clock(tot)}</span></div>`;
  }
  function edScenes(p) {
    const T = sceneTimes(p), dis = p.status === 'making' ? ' disabled' : '', last = p.scenes.length - 1;
    return `<div class="hx-edsech"><b class="hx-t">Scenes</b><span class="hx-mut hx-sm hx-num" id="hxEdLen">${p.scenes.length} · ${clock(total(p))}</span><span class="hx-grow"></span>
        <button type="button" class="hx-btn s" data-a="addsc"${dis}>${ic('plus', 14)}Scene</button></div>
      <ol class="hx-edsc">${p.scenes.map((s, i) => `<li class="hx-scc${i === UI.scene ? ' on' : ''}" data-n="${i}">
        <div class="hx-scch"><button type="button" class="hx-scnum" data-a="scene" data-n="${i}" aria-label="Show scene ${i + 1}">${i + 1}</button>
          <span class="hx-mut hx-sm hx-num hx-sct">${clock(T[i][0])} · ${secs(T[i][1] - T[i][0])}</span>
          ${s.look?.kind && s.look.kind !== 'none' ? `<span class="hx-sclk">${esc(LOOK[s.look.kind])}</span>` : ''}<span class="hx-grow"></span>
          <span class="hx-scops"><button type="button" class="hx-ib xs" data-a="scmove" data-n="${i}" data-d="-1" aria-label="Move scene ${i + 1} up"${i && !dis ? '' : ' disabled'}>${ic('up', 14)}</button>
            <button type="button" class="hx-ib xs" data-a="scmove" data-n="${i}" data-d="1" aria-label="Move scene ${i + 1} down"${i < last && !dis ? '' : ' disabled'}>${ic('dn', 14)}</button>
            <button type="button" class="hx-ib xs" data-a="scdup" data-n="${i}" aria-label="Copy scene ${i + 1}"${dis}>${ic('copy', 14)}</button>
            <button type="button" class="hx-ib xs" data-a="delsc" data-n="${i}" aria-label="Remove scene ${i + 1}"${last && !dis ? '' : ' disabled'}>${ic('trash', 14)}</button></span></div>
        <textarea class="hx-in hx-serifp" data-sc="${i}" rows="3" aria-label="Scene ${i + 1} words"${dis}>${esc(s.say)}</textarea>
        ${s.needs ? `<p class="hx-why">${ic('warn', 14)}<span>${esc(s.needs)}</span></p>` : ''}</li>`).join('')}</ol>
      <label class="hx-fld hx-edclose"><span class="hx-lab">Closing line</span><input class="hx-in" data-f="closing" value="${esc(p.closing || '')}" maxlength="80" placeholder="Visit us at…"${dis}>
        <span class="hx-hint">Shown on the last card, after the final scene.</span></label>`;
  }
  function edTool(p) {
    const sc = p.scenes[UI.scene] || {say: '', look: {kind: 'none'}}, lk = sc.look || {kind: 'none'}, f = face(p.avatar_id), e = engine(p.engine);
    const dis = p.status === 'making' ? ' disabled' : '';
    if (UI.tool === 'Scene') {
      const field = (k, l, ph) => `<label class="hx-fld"><span class="hx-lab">${l}</span><input class="hx-in" data-lk="${k}" value="${esc(lk[k] || '')}" maxlength="60" placeholder="${esc(ph || '')}"${dis}></label>`;
      const extra = {title: field('text', 'Title', 'Grand opening'), big_number: field('value', 'Number', '1,200') + field('label', 'What it is', 'happy customers'),
        price: `<div class="hx-row2">${field('new', 'Price now', '€19')}${field('old', 'Price before', '€25')}</div>${field('label', 'Item', 'Lunch menu')}`,
        lower_third: field('title', 'Name', 'Maya Costa') + field('sub', 'Line under it', 'Owner, Café Azul'),
        bar_chart: `<div class="hx-fld"><span class="hx-lab">Bars</span>${(lk.bars || []).map((b, i) => `<div class="hx-barr"><input class="hx-in" data-bar="${i}" data-bk="label" value="${esc(b.label)}" placeholder="Label" aria-label="Bar ${i + 1} label"${dis}><input class="hx-in" data-bar="${i}" data-bk="value" value="${esc(b.value)}" placeholder="Value" aria-label="Bar ${i + 1} value"${dis}>
          <button type="button" class="hx-ib xs" data-a="bardel" data-n="${i}" aria-label="Remove bar ${i + 1}"${(lk.bars || []).length > 1 && !dis ? '' : ' disabled'}>${ic('x', 14)}</button></div>`).join('')}
          ${(lk.bars || []).length < 6 ? `<button type="button" class="hx-btn s" data-a="baradd"${dis}>${ic('plus', 13)}Add a bar</button>` : ''}</div>`}[lk.kind] || '';
      return `<div class="hx-fld"><span class="hx-lab">What scene ${UI.scene + 1} shows</span><div class="hx-looks" role="radiogroup">${Object.entries(LOOK).map(([k, n]) => `<button type="button" role="radio" aria-checked="${(lk.kind || 'none') === k}" class="hx-lkt" data-a="lookset" data-val="${k}"${dis}>
          <span class="hx-lka ${k}" aria-hidden="true"><i></i><i></i><i></i></span><span>${esc(n)}</span></button>`).join('')}</div></div>
        ${extra}<p class="hx-hint">Numbers on screen are yours: a number you did not write is never added.</p>`;
    }
    if (UI.tool === 'Face') {
      const talk = (D.engines?.engines || []).filter(x => x.job === 'video' && x.face && x.ready).map(x => x.label);
      return `<div class="hx-fld"><span class="hx-lab">Who presents</span><div class="hx-faces" role="radiogroup">
          <button type="button" role="radio" aria-checked="${!p.avatar_id}" class="hx-fct" data-a="faceset" data-val=""${dis}>${avImg(null, 'm')}<span>No face</span></button>
          ${(D.avatars || []).map(a => `<button type="button" role="radio" aria-checked="${p.avatar_id === a.id}" class="hx-fct" data-a="faceset" data-val="${esc(a.id)}"${dis}>${avImg(a, 'm')}<span>${esc(a.name)}</span></button>`).join('')}
          <button type="button" class="hx-fct add" data-a="go" data-p="avatars">${ic('plus', 18)}<span>Add a face</span></button></div></div>
        ${f ? `<div class="hx-fld"><span class="hx-lab">Where the person sits</span><div class="hx-seg" role="radiogroup">${[['corner', 'In a corner'], ['full', 'The whole frame']].map(([k, n]) => `<button type="button" role="radio" aria-checked="${(p.face_layout || 'corner') === k}" data-a="layout" data-val="${k}"${dis}>${n}</button>`).join('')}</div></div>` : ''}
        <p class="hx-hint">${f ? (e?.face ? `${esc(e.label)} makes this photo talk.` : `Hoola standard shows the photo still. ${talk.length ? `To make it talk, pick ${esc(talk.join(' or '))} in Engine.` : 'A talking-face engine is not connected yet.'}`) : 'A face is used only with consent: it is you, or the person agreed.'}</p>`;
    }
    if (UI.tool === 'Voice') return `<div class="hx-fld"><span class="hx-lab">Voice</span><button type="button" class="hx-dd" data-a="ppick" data-k="voice"${dis}><span>${esc(voiceName(p.voice))}</span>${ic('down', 14)}</button></div>
      <div class="hx-fld"><span class="hx-lab">Language</span><button type="button" class="hx-dd" data-a="ppick" data-k="lang"${dis}><span>${esc(langName(p.lang))}</span>${ic('down', 14)}</button></div>
      <button type="button" class="hx-btn" data-a="edhear">${ic('vol', 14)}Hear scene ${UI.scene + 1} in this voice<span class="hx-mut">· free</span></button>
      <p class="hx-hint">Your Hoola Vocal dictionary applies: names are said your way. <button type="button" class="hx-lnk" data-a="go" data-p="voices">All voices</button></p>`;
    if (UI.tool === 'Engine') {
      const r = UI.cmp?.id === p.id ? UI.cmp.r : null;
      if (!r) return '<p class="hx-mut hx-sm">Pricing every engine for this video…</p>';
      const bars = n => `<span class="hx-q" aria-label="Quality ${n} of 5">${[0, 1, 2, 3, 4].map(i => `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</span>`;
      return `<p class="hx-hint">Prices for this exact video, about ${secs(r.seconds)}, in this voice.</p><div class="hx-engs" role="radiogroup">${r.engines.map(x => `<button type="button" role="radio" aria-checked="${r.chosen === x.id}" class="hx-eng${x.ready ? '' : ' off'}" data-a="engset" data-id="${esc(x.id)}"${x.ready && !dis ? '' : ' disabled'}>
        <span class="hx-ct"><b>${esc(x.label)}</b><small>${esc(x.ready ? x.what : `Not connected · ${scrub(x.status || '')}`)}</small></span>
        <span class="hx-engr">${bars(x.quality)}<b class="hx-num">${cr(x.credits)}</b></span></button>`).join('')}</div>
        <button type="button" class="hx-lnk" data-a="go" data-p="engines">Set a default engine</button>`;
    }
    return `<div class="hx-fld"><span class="hx-lab">Shape</span><div class="hx-seg" role="radiogroup">${Object.entries(SHAPE).map(([k, n]) => `<button type="button" role="radio" aria-checked="${p.shape === k}" data-a="pshape" data-val="${k}"${dis}>${n}</button>`).join('')}</div></div>
      ${p.shape !== 'reel' ? `<div class="hx-fld"><span class="hx-lab">Frame</span><div class="hx-seg" role="radiogroup">${[['16:9', 'Wide 16:9'], ['1:1', 'Square 1:1']].map(([k, n]) => `<button type="button" role="radio" aria-checked="${p.aspect === k}" data-a="paspect" data-val="${k}"${dis}>${n}</button>`).join('')}</div></div>` : ''}
      <label class="hx-fld"><span class="hx-lab">Business name on screen</span><input class="hx-in" data-f="brand" value="${esc(p.brand || '')}" maxlength="40" placeholder="${esc(D.brand?.name || 'Your business')}"${dis}></label>
      ${p.shape === 'product' ? `<div class="hx-fld"><span class="hx-lab">Products</span><div id="hxItems">${(p.items || []).map((it, i) => `<div class="hx-itrow"><input class="hx-in" data-it="${i}" data-ik="name" value="${esc(it.name)}" placeholder="Name" maxlength="48" aria-label="Product ${i + 1} name"${dis}>
          <input class="hx-in" data-it="${i}" data-ik="price" value="${esc(it.price)}" placeholder="Price" maxlength="24" aria-label="Product ${i + 1} price"${dis}>
          <button type="button" class="hx-ib xs" data-a="itdel" data-n="${i}" aria-label="Remove product ${i + 1}"${dis}>${ic('x', 14)}</button></div>`).join('')}</div>
          ${(p.items || []).length < 8 ? `<button type="button" class="hx-btn s" data-a="itadd"${dis}>${ic('plus', 13)}Add a product</button>` : ''}</div>` : ''}
      <div class="hx-fld"><span class="hx-lab">Subtitles</span><div class="hx-acts"><button type="button" class="hx-btn s" data-a="subdl" data-val="srt">${ic('dl', 13)}.srt</button>
        <button type="button" class="hx-btn s" data-a="subdl" data-val="vtt">${ic('dl', 13)}.vtt</button></div><span class="hx-hint">Timed from the scenes.</span></div>`;
  }
  function makeBtn(p, big) {
    if (p.status === 'making') return `<button type="button" class="hx-btn ${big ? 'hx-mkb' : ''} danger" data-a="stop" data-id="${esc(p.id)}">${ic('stop', 14)}<span>Stop</span></button>`;
    const qn = UI.q?.id === p.id ? UI.q : null, blocked = !qn || (qn.problems || []).length;
    return `<button type="button" class="hx-btn dark ${big ? 'hx-mkb' : ''}" data-a="make" data-mk="1" data-id="${esc(p.id)}" data-k="${esc(qn?.quote?.key || '')}"${blocked ? ' disabled' : ''}>${ic('play', 14)}<span>${p.status === 'ready' ? 'Make it again' : 'Make the video'}${qn ? ` · ${cr(qn.quote.credits)}` : ''}</span></button>`;
  }
  function edMakeBox(p) {
    const qn = UI.q?.id === p.id ? UI.q : null, pr = qn?.problems || [];
    return `<div class="hx-edmk"><div id="hxEdPrice">${qn ? priceBox(qn.quote) : '<p class="hx-mut hx-sm">Working out the price…</p>'}</div>
      ${pr.length ? `<ul class="hx-probs">${pr.map(x => `<li>${ic('warn', 14)}<span>${esc(scrub(x))}</span></li>`).join('')}</ul>` : ''}
      ${makeBtn(p, true)}<p class="hx-hint">${p.status === 'making' ? 'Making it now. You can leave this page; it carries on.' : 'The price is for this exact video. Nothing is spent until you tap.'}</p></div>`;
  }
  function edPage() {
    const p = cur();
    if (!p) return `<div class="hx-doc"><div class="hx-empty"><b>This video was not found</b><span>It may be in the trash.</span><button type="button" class="hx-btn" data-a="go" data-p="studio">All videos</button></div></div>`;
    if (UI.scene >= p.scenes.length) UI.scene = Math.max(0, p.scenes.length - 1);
    if (!TOOLS.includes(UI.tool)) UI.tool = 'Scene';
    const dis = p.status === 'making' ? ' disabled' : '';
    return `<div class="hx-ed"><div class="hx-edh"><button type="button" class="hx-ib" data-a="go" data-p="studio" aria-label="All videos" title="All videos">${ic('back', 18)}</button>
        <div class="hx-edtt"><label class="hx-sr" for="hxEdTitle">Title</label><input id="hxEdTitle" class="hx-edti" data-f="title" value="${esc(p.title)}" maxlength="80"${dis}>
          <span class="hx-edmeta">${chip(p)}<span class="hx-num">${esc([KIND_NAME[p.kind] || SHAPE[p.shape] || 'Video', p.aspect, langName(p.lang)].join(' · '))}</span>${p.chat ? `<button type="button" class="hx-lnk" data-a="openchat" data-id="${esc(p.chat)}">Its chat</button>` : ''}</span></div>
        <span class="hx-grow"></span>
        ${p.status === 'ready' ? `<button type="button" class="hx-btn" data-a="dlv" data-id="${esc(p.id)}">${ic('dl', 14)}<span>Download</span></button>` : ''}
        <button type="button" class="hx-ib" data-a="vmenu" data-id="${esc(p.id)}" aria-label="More for this video">${ic('dots', 18)}</button>
        <span class="hx-edhmk">${makeBtn(p)}</span></div>
      <div class="hx-edb"><section class="hx-edl" data-keep="edl-${esc(p.id)}" aria-label="Scenes">${edScenes(p)}</section>
        <section class="hx-edc" aria-label="Preview"><div id="hxEdStage">${edStage(p)}</div><div id="hxEdTl">${edTimeline(p)}</div>
          <div id="hxJob-${esc(p.id)}" class="hx-edjob"></div>${p.error && p.status === 'failed' ? `<p class="hx-why">${ic('warn', 14)}<span>${esc(scrub(p.error))}</span></p>` : ''}</section>
        <aside class="hx-edr" data-keep="edr-${esc(p.id)}" aria-label="Settings"><div class="hx-tabs hx-edtabs" role="tablist">${TOOLS.map(t => `<button type="button" role="tab" aria-selected="${UI.tool === t}" data-a="tool" data-val="${t}">${t}</button>`).join('')}</div>
          <div id="hxEdTool" class="hx-edtool">${edTool(p)}</div>${edMakeBox(p)}</aside></div></div>`;
  }
  function edPaint(tool = true) {
    const p = cur(); if (!p || PAGE !== 'studio') return;
    const s = $('#hxEdStage'); if (s) { s.innerHTML = edStage(p); fillMedia(); }
    const t = $('#hxEdTl'); if (t) t.innerHTML = edTimeline(p);
    $$('.hx-scc').forEach(li => li.classList.toggle('on', +li.dataset.n === UI.scene));
    if (tool && UI.tool === 'Scene') { const x = $('#hxEdTool'); if (x) x.innerHTML = edTool(p); }
  }
  function edTimes(p) {
    const T = sceneTimes(p);
    $$('.hx-scc').forEach(li => { const i = +li.dataset.n, el = li.querySelector('.hx-sct'); if (el && T[i]) el.textContent = `${clock(T[i][0])} · ${secs(T[i][1] - T[i][0])}`; });
    const l = $('#hxEdLen'); if (l) l.textContent = `${p.scenes.length} · ${clock(total(p))}`;
    const t = $('#hxEdTl'); if (t) t.innerHTML = edTimeline(p);
  }
  function edScene(n, show) {
    const p = cur(); if (!p) return; UI.scene = Math.max(0, Math.min(n, p.scenes.length - 1));
    const v = $('#hxEdStage video');
    if (v) { const T = sceneTimes(p)[UI.scene]; try { v.currentTime = T ? T[0] : 0; v.play().catch(() => {}); } catch { /* not loaded */ } $$('.hx-tlb').forEach((b, i) => b.classList.toggle('on', i === UI.scene)); $$('.hx-scc').forEach(li => li.classList.toggle('on', +li.dataset.n === UI.scene)); }
    else edPaint();
    if (show) $(`.hx-scc[data-n="${UI.scene}"]`)?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }
  function edPlay() {
    if (UI.edp) return edStop();
    const p = cur(); if (!p || !p.scenes.length) return;
    UI.edp = true; if (UI.scene >= p.scenes.length - 1) UI.scene = 0; edTick(true);
  }
  function edTick(first) {
    const p = cur(); if (!UI.edp || !p || PAGE !== 'studio') return edStop();
    if (!first) { if (UI.scene >= p.scenes.length - 1) return edStop(); UI.scene++; }
    edPaint(); $(`.hx-scc[data-n="${UI.scene}"]`)?.scrollIntoView({block: 'nearest'});
    const T = sceneTimes(p)[UI.scene]; UI.edt = setTimeout(() => edTick(false), Math.max(1500, (T[1] - T[0]) * 1000));
  }
  function edStop() { clearTimeout(UI.edt); if (!UI.edp) return; UI.edp = false; edPaint(false); }
  async function edCompare() {
    const id = ARG; if (!id) return;
    try { const r = await api('GET', `${X}/compare?id=${q(id)}`); UI.cmp = {id, r}; } catch (e) { UI.cmp = {id, r: {engines: [], seconds: 0, chosen: ''}}; toast(e.message, true); }
    if (PAGE === 'studio' && ARG === id && UI.tool === 'Engine') { const x = $('#hxEdTool'); if (x) x.innerHTML = edTool(cur()); }
  }
  function scenesSave(sc, n) { if (n != null) UI.scene = n; return save({scenes: sc}); }
  async function newVideo() { clearTimeout(C.t); C.gen++; C.conv = ''; C.rows = []; C.items = []; C.files = []; C.ask = ''; UI.pv.id = ''; pvStop(); await openChat(true); recentLoad(); go('chat'); }
  function trMenu(el, id) {
    return menu(el, [{search: 'Translate into', empty: 'No language matches'}, ...(UI.L || []).map(l => ({label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name, sub: l.region, run: async () => {
      try { const p = await api('POST', `${H}/translate`, {id, lang: l.code}); toast('A translated draft is ready. Check it, then make it.'); await load(); UI.scene = 0; go('studio', p.id); } catch (er) { toast(er.message, true); } }}))], {width: 280});
  }
  async function dupP(id) { try { const p = await api('POST', `${H}/duplicate`, {id}); await load(); toast('A copy is ready.'); UI.scene = 0; go('studio', p.id); } catch (er) { toast(er.message, true); } }
  function tplSave(id) { return svOpen(id); }
  async function trashP(id) {
    try { await api('POST', `${H}/trash`, {id}); await load(); toast('Moved to the trash for 30 days.'); if (PAGE === 'studio' && ARG === id) go('studio'); else draw(); }
    catch (er) { toast(er.message, true); }
  }
  function vMenu(el, id) {
    const p = (D.projects || []).find(x => x.id === id); if (!p) return;
    return menu(el, [...(PAGE === 'studio' && ARG === id ? [] : [{label: 'Open in the Studio', icon: 'library', run: () => { UI.scene = 0; UI.edv = 'video'; go('studio', id); }}]),
      ...(p.chat ? [{label: 'Open its chat', icon: 'clip', run: () => openChatId(p.chat)}] : []),
      ...(p.status === 'ready' ? [{label: 'Download the MP4', run: () => download(id)}] : []),
      {label: 'Duplicate', icon: 'plus', run: () => dupP(id)},
      {label: 'Translate into another language', run: () => trMenu(el, id)},
      {label: 'Save as a template', icon: 'grid', run: () => tplSave(id)},
      {sep: true}, {label: 'Move to the trash', icon: 'trash', danger: true, disabled: p.status === 'making', run: () => trashP(id)}], {align: 'end', width: 260});
  }
  async function openChatId(conv) { clearTimeout(C.t); C.gen++; C.conv = conv; C.rows = []; C.items = []; UI.pv.id = ''; pvStop(); await chatLoad(); go('chat'); }

  // ------------------------------------------------------------------ templates (v0.999.174: design claude.ai/artifact/JzJ7s7bqJGC983XfwCZbMk) ---
  // The library (her own templates first, then the ready-made ones as cards with a poster of their first scene, what they
  // are for and the blanks), the Use page (one field per blank, the live preview filling in as she types, language / face /
  // voice / engine / frame, the price: the draft is free, the video is priced again in the Studio), the save dialog (tap
  // the words that change; Hoola marks prices, dates and names by code) and a sheet with one free draft per row.
  const TGROUP = {Offers: 'Offers & sales', Updates: 'Updates', Reminders: 'Reminders', Lessons: 'Lessons', Greetings: 'Greetings', Events: 'Events', Reels: 'Social reels', Mine: 'Yours'};
  const TSORT = {used: 'Most used', name: 'Name A to Z', short: 'Shortest first'};
  const TSHAPE = {any: 'Any shape', wide: 'Landscape', tall: 'Vertical', sq: 'Square'};
  const HI_TPL = ['tp_offer', 'tp_rate', 'tp_batch', 'tp_timing', 'tp_thanks', 'tp_reel'];   // written in Hindi too
  const tplOf = id => (D.templates || []).find(t => t.id === id);
  const shapeKey = t => t.aspect === '9:16' || t.shape === 'reel' ? 'tall' : t.aspect === '1:1' ? 'sq' : 'wide';
  const shapeName = t => ({tall: 'Vertical', sq: 'Square', wide: 'Landscape'})[shapeKey(t)];
  const sampleOf = t => Object.fromEntries((t.blanks || []).map(b => [b.key, String(b.example || '').replace(/^e\.g\.\s*/i, '').split(/,\s*/)[0].replace(/^with its \w+,\s*/i, '') || b.label]));
  const fillStr = (s, v) => String(s || '').replace(/\{([a-z][a-z0-9_]*)\}/g, (m, k) => v[k] || m);
  const shown = s => { s = String(s || '').replace(/\{[a-z][a-z0-9_]*\}/g, '…'); return s.charAt(0).toUpperCase() + s.slice(1); };   // a poster never shows {braces}
  const fillLook = (lk, v) => { const o = {...(lk || {kind: 'none'})}; for (const k of ['text', 'label', 'title', 'sub', 'unit', 'value', 'new', 'old']) if (o[k]) o[k] = fillStr(o[k], v);
    if (o.bars) o.bars = o.bars.map(b => ({label: fillStr(b.label, v), value: fillStr(b.value, v)})); return o; };
  function fillParts(s, v, tb) {   // her words in the line: a value she typed, a gap she has not filled yet
    const out = []; let at = 0; const rx = /\{([a-z][a-z0-9_]*)\}/g; let m;
    while ((m = rx.exec(s || ''))) { if (m.index > at) out.push(esc(s.slice(at, m.index)));
      const b = (tb || []).find(x => x.key === m[1]), val = v[m[1]];
      out.push(val ? `<mark class="hx-tv">${esc(val)}</mark>` : `<mark class="hx-tgap">${esc((b?.label || m[1]).toLowerCase())}</mark>`); at = rx.lastIndex; }
    out.push(esc(String(s || '').slice(at))); return out.join('');
  }
  function tplPoster(t, cls) {
    const v = sampleOf(t), sc = (t.scenes || []).find(s => s.look?.kind && s.look.kind !== 'none') || (t.scenes || [])[0] || {}, lk = fillLook(sc.look, v), g = (t.group || 'Mine').toLowerCase();
    const body = shapeKey(t) === 'tall' ? `<span class="hx-tph"><b>${esc(fillStr((t.scenes || [])[0]?.say, v))}</b><i></i><i></i></span>`
      : lk.kind === 'price' ? `<small>${esc(lk.label || '')}</small><span class="hx-tpp">${lk.old ? `<s>${esc(lk.old)}</s>` : ''}<b>${esc(lk.new || '')}</b></span>`
      : lk.kind === 'big_number' ? `<b class="big">${esc(lk.value || '')}</b><small>${esc(lk.label || '')}</small>`
      : lk.kind === 'lower_third' ? `<b>${esc(lk.title || '')}</b><small>${esc(lk.sub || '')}</small>`
      : `<b>${esc(shown(lookText(lk) || fillStr(sc.say, v)))}</b>${t.closing ? `<small>${esc(shown(fillStr(t.closing, v)))}</small>` : ''}`;
    return `<span class="hx-tpo g-${esc(g)}${cls ? ' ' + cls : ''}${shapeKey(t) === 'tall' ? ' tall' : ''}">${body}
      <span class="hx-tpg">${esc(TGROUP[t.group] || t.group || 'Yours')}</span><span class="hx-tplen hx-num">${clock(t.seconds)}</span></span>`;
  }
  const blankChips = t => (t.blanks || []).map(b => `<span class="hx-tbk">${esc(b.label.toLowerCase())}</span>`).join('');
  function tplRows() {
    const qy = (UI.tq || '').trim().toLowerCase(), g = UI.tg || 'all', sh = UI.tsh || 'any', so = UI.tso || 'used';
    const rows = (D.templates || []).filter(t => (g === 'all' || t.group === g) && (sh === 'any' || shapeKey(t) === sh)
      && (!qy || `${t.name} ${t.line || ''} ${TGROUP[t.group] || ''} ${(t.scenes || []).map(s => s.say).join(' ')} ${(t.blanks || []).map(b => b.label).join(' ')}`.toLowerCase().includes(qy)));
    return rows.sort((a, b) => so === 'name' ? a.name.localeCompare(b.name) : so === 'short' ? a.seconds - b.seconds : (b.used || 0) - (a.used || 0));
  }
  function tplCard(t) {
    return `<article class="hx-tc"><button type="button" class="hx-tco" data-a="tpluse" data-id="${esc(t.id)}" aria-label="Use ${esc(t.name)}">${tplPoster(t)}</button>
      <div class="hx-tcb"><div class="hx-tcn"><b>${esc(t.name)}</b>${t.id === 'tp_remind' || t.id === 'tp_event' ? '<span class="hx-tnew">New</span>' : ''}</div>
        <p>${esc(t.line || '')}</p><div class="hx-tbks">${blankChips(t)}</div><span class="hx-grow"></span>
        <div class="hx-tcf"><span class="hx-mut hx-sm hx-num">${t.count} scene${t.count === 1 ? '' : 's'} · ${shapeName(t)}${t.used ? ` · used ${num(t.used)}×` : ''}</span><span class="hx-grow"></span>
          <button type="button" class="hx-ib s ring" data-a="tplsample" data-id="${esc(t.id)}" aria-label="Watch a sample of ${esc(t.name)}" title="Watch a sample">${ic('play', 13)}</button>
          <button type="button" class="hx-btn s dark" data-a="tpluse" data-id="${esc(t.id)}">Use</button></div></div></article>`;
  }
  function tplMine(t) {
    return `<article class="hx-tm"><button type="button" class="hx-tmo" data-a="tpluse" data-id="${esc(t.id)}" aria-label="Use ${esc(t.name)}">${tplPoster(t, 'mini')}</button>
      <div class="hx-ct"><b>${esc(t.name)}</b><small class="hx-num">${esc(t.line || 'Yours')} · ${t.count} scene${t.count === 1 ? '' : 's'}${t.used ? ` · used ${num(t.used)}×` : ''}</small><span class="hx-tbks">${blankChips(t)}</span></div>
      <button type="button" class="hx-ib s" data-a="tplmenu" data-id="${esc(t.id)}" aria-label="More for ${esc(t.name)}">${ic('dots', 16)}</button>
      <button type="button" class="hx-btn s dark" data-a="tpluse" data-id="${esc(t.id)}">Use</button></article>`;
  }
  function tplEmptyMine() {
    return `<div class="hx-tempty"><div class="hx-teart" aria-hidden="true"><span class="a"></span><span class="b"><b>Only <mark class="hx-tv">price</mark> this week</b><i></i><i></i><em><u></u><u></u></em></span><span class="c">${ic('plus', 20)}</span></div>
      <div class="hx-growf"><h3 class="hx-serif">Make a video once. Reuse it every week.</h3>
        <p class="hx-mut">Turn any of your videos into a template. The words that change, like a price, a date or a name, become blanks you fill in next time.</p>
        <ol class="hx-how"><li><span class="n">1</span><span>Pick a video you made: an offer, a lesson, a weekly update.</span></li>
          <li><span class="n">2</span><span>Tap the words that change. They become blanks.</span></li>
          <li><span class="n">3</span><span>Next time, fill the blanks and the draft is ready in seconds.</span></li></ol>
        <div class="hx-acts"><button type="button" class="hx-btn dark" data-a="tplfrom">Choose one of my videos</button>
          <button type="button" class="hx-btn" data-a="ttab" data-val="ready">Browse ready-made</button></div>
        <span class="hx-mut hx-sm">Up to 40 templates. Only you can see them.</span></div></div>`;
  }
  function tplList() {
    const tab = UI.tt || 'all', rows = tplRows(), mine = rows.filter(t => t.mine), ready = rows.filter(t => !t.mine), all = D.templates || [];
    if (tab === 'mine' && !all.some(t => t.mine)) return tplEmptyMine();
    if (!rows.length) return `<div class="hx-empty"><b>No templates match</b><span>Try another word, or show every template.</span><button type="button" class="hx-btn s" data-a="tclear">Show all templates</button></div>`;
    const nm = all.filter(t => t.mine).length;
    return `${tab !== 'ready' && mine.length ? `<section class="hx-tsec" aria-labelledby="hxTm"><div class="hx-sech"><b class="hx-t" id="hxTm">Your templates</b><span class="hx-mut hx-sm">${num(nm)} of 40 · made from your own videos</span></div>
        <div class="hx-tmg">${mine.map(tplMine).join('')}</div></section>` : ''}
      ${tab !== 'mine' && ready.length ? `<section class="hx-tsec" aria-labelledby="hxTr"><div class="hx-sech"><b class="hx-t" id="hxTr">Ready-made</b><span class="hx-mut hx-sm">Every one speaks in any of 140 languages</span></div>
        <div class="hx-tgrid">${ready.map(tplCard).join('')}</div></section>` : ''}`;
  }
  function tplLib() {
    const all = D.templates || [], n = k => k === 'all' ? all.length : k === 'mine' ? all.filter(t => t.mine).length : all.filter(t => !t.mine).length;
    const groups = ['all', ...Object.keys(TGROUP).filter(g => g !== 'Mine' && all.some(t => t.group === g))];
    return `<div class="hx-doc hx-tlib"><div class="hx-libh"><div class="hx-growf"><h2 class="hx-serif">Templates</h2>
        <p class="hx-mut">Start from a video that already works. Fill in a few words, and Hoola writes the draft in your language. Making the draft is free; you see the price before the video is made.</p></div>
        <div class="hx-acts"><button type="button" class="hx-btn" data-a="tplfrom">${ic('plus', 14)}Save a video as a template</button></div></div>
      <div class="hx-libbar"><label class="hx-lsearch hx-tsearch">${ic('search', 15)}<span class="hx-sr">Search templates</span><input id="hxTq" type="search" placeholder="Search: offer, reminder, lesson, thank you…" value="${esc(UI.tq || '')}" autocomplete="off"></label>
        <div class="hx-seg" role="tablist" aria-label="Which templates">${[['all', 'All'], ['ready', 'Ready-made'], ['mine', 'Yours']].map(([k, l]) => `<button type="button" role="tab" aria-selected="${(UI.tt || 'all') === k}" aria-checked="${(UI.tt || 'all') === k}" data-a="ttab" data-val="${k}">${l}<span class="hx-num">${num(n(k))}</span></button>`).join('')}</div>
        <span class="hx-grow"></span>
        <button type="button" class="hx-btn" data-a="tshape">${esc(TSHAPE[UI.tsh || 'any'])}${ic('down', 13)}</button>
        <button type="button" class="hx-btn" data-a="tsort">${ic('sort', 14)}<span>${esc(TSORT[UI.tso || 'used'])}</span></button></div>
      <div class="hx-tchips" role="radiogroup" aria-label="Kind">${groups.map(g => `<button type="button" role="radio" aria-checked="${(UI.tg || 'all') === g}" class="hx-chip s" data-a="tgrp" data-val="${esc(g)}">${esc(g === 'all' ? 'All kinds' : TGROUP[g])}</button>`).join('')}</div>
      <div id="hxTplList">${tplList()}</div></div>`;
  }

  // ---- using one
  function tuState(t) {
    if (!UI.tu || UI.tu.id !== t.id) UI.tu = {id: t.id, vals: {}, lang: 'auto', face: SET.face || '', voice: SET.voice || '', engine: defEngine(), aspect: t.aspect, layout: 'corner', scene: 0, play: false, sample: false, est: null};
    return UI.tu;
  }
  const tuVals = (t, u) => u.sample ? {...sampleOf(t), ...Object.fromEntries(Object.entries(u.vals).filter(([, x]) => x))} : u.vals;
  const tuMissing = (t, u) => (t.blanks || []).filter(b => !(u.vals[b.key] || '').trim());
  const tuShape = (t, u) => t.shape === 'reel' ? '9:16' : u.aspect;
  const tuProject = (t, u) => { const v = tuVals(t, u); return {scenes: (t.scenes || []).map(s => ({say: fillStr(s.say, v), look: fillLook(s.look, v)})), closing: fillStr(t.closing, v)}; };
  function tuStage(t, u) {
    const v = tuVals(t, u), n = Math.min(u.scene, t.scenes.length - 1), sc = t.scenes[n] || {}, lk = fillLook(sc.look, v), f = face(u.face), full = u.layout === 'full', asp = tuShape(t, u);
    const pp = tuProject(t, u), T = sceneTimes(pp), tot = T.length ? T[T.length - 1][1] : 1, at = T[n] ? T[n][0] : 0;
    return `<div class="hx-preview ${asp === '9:16' ? 'tall' : asp === '1:1' ? 'sq' : ''}" style="--brand:${esc(brandColor())}">
        ${f && full ? `<span class="hx-pvfull">${avImg(f, 'xl')}</span>` : ''}
        <div class="hx-pvlook">${lookText(lk) ? `<b>${esc(shown(lookText(lk)))}</b>` : n === 0 ? `<b>${esc(t.name)}</b>` : ''}</div>
        ${f && !full ? `<span class="hx-pvface">${avImg(f, 'l')}</span>` : ''}<p class="hx-pvcap">${fillParts(sc.say, v, t.blanks)}</p>
        <span class="hx-tsn hx-num">Scene ${n + 1} of ${t.scenes.length} · ${clock(at)}</span></div>
      <div class="hx-pvbar"><button type="button" class="hx-pplay" data-a="tuplay" aria-label="${u.play ? 'Pause the sketch' : 'Play the sketch'}">${ic(u.play ? 'stop' : 'play', 14)}</button>
        <span class="hx-tseg">${T.map((x, i) => `<button type="button" class="${i === n ? 'on' : i < n ? 'past' : ''}" data-a="tuscene" data-n="${i}" style="flex:${(x[1] - x[0]).toFixed(2)} 1 0" aria-label="Scene ${i + 1}"></button>`).join('')}</span>
        <span class="hx-mut hx-sm hx-num">${clock(at)} / ${clock(tot)}</span>
        <button type="button" class="hx-btn s" data-a="tuhear">${ic('vol', 14)}Hear it<span class="hx-mut">· free</span></button></div>`;
  }
  function tuScenes(t, u) {
    const v = tuVals(t, u), pp = tuProject(t, u), T = sceneTimes(pp), n = Math.min(u.scene, t.scenes.length - 1);
    return `<ol class="hx-tsl">${t.scenes.map((s, i) => { const lk = s.look?.kind && s.look.kind !== 'none';
      return `<li><button type="button" class="hx-tsr${i === n ? ' on' : ''}" data-a="tuscene" data-n="${i}">
        <span class="hx-tsm g-${esc((t.group || 'Mine').toLowerCase())}">${esc(shown(lookText(fillLook(s.look, v))) || (i + 1))}</span>
        <span class="hx-growf"><span class="hx-tsh hx-num"><b>Scene ${i + 1}</b><span>${esc(lk ? LOOK[s.look.kind] : 'Just the words')}</span><span class="hx-grow"></span><span>${secs(T[i][1] - T[i][0])}</span></span>
          <span class="hx-tsw">${fillParts(s.say, v, t.blanks)}</span></span></button></li>`; }).join('')}</ol>
      <div class="hx-tclose">${ic('doc', 15)}<span>Closing card: ${t.closing ? `<strong>${fillParts(t.closing, v, t.blanks)}</strong>` : '<strong>your business name</strong>'} with your logo and colour from Brand</span></div>`;
  }
  function tuPrice(t, u) {
    const miss = tuMissing(t, u), e = u.est;
    return `<div class="hx-tprice"><div class="r"><b>The draft</b><span class="hx-grow"></span><b class="ok">Free</b></div>
      <div class="r hx-mut"><span>The video, later in the Studio</span><span class="hx-grow"></span><span class="hx-num">${e ? 'about ' + cr(e.credits) : '…'}</span></div>
      <p class="hx-mut hx-sm">${esc(secs(Math.round(sceneTimes(tuProject(t, u)).slice(-1)[0]?.[1] || t.seconds)))} · ${esc(e?.label || 'Hoola standard')} · ${esc(voiceName(u.voice))}. The exact price is shown again before anything is made.</p>
      <div class="r"><span class="hx-tmiss">${miss.length ? `Fill in: ${esc(miss.map(b => b.label.toLowerCase()).join(', '))}.` : '<span class="ok">Ready.</span> Opens in the Studio.'}</span>
        <button type="button" class="hx-btn dark l" data-a="tumake"${miss.length || u.busy ? ' disabled' : ''}>${u.busy ? 'Making the draft…' : 'Make the draft'}</button></div></div>`;
  }
  function tplUse(t) {
    const u = tuState(t), bl = t.blanks || [], filled = bl.length - tuMissing(t, u).length, langNow = u.lang === 'auto' ? `Auto · ${langName(t.lang || 'en')}` : langName(u.lang);
    const where = b => [b.where.length ? `scene${b.where.length > 1 ? 's' : ''} ${b.where.join(', ').replace(/, (\d+)$/, ' and $1')}` : '', b.closing ? 'closing' : ''].filter(Boolean).join(' and ');
    const opt = (k, lab, val, mark) => `<button type="button" class="hx-topt" data-a="tupick" data-k="${k}">${mark}<span class="hx-growf"><small>${lab}</small><b>${esc(val)}</b></span>${ic('down', 13)}</button>`;
    const eng = (D.engines?.engines || []).find(e => e.id === u.engine);
    return `<div class="hx-tuse"><section class="hx-tform" aria-label="Fill in the blanks">
        <div class="hx-tfh"><h2 class="hx-t">Fill in the blanks</h2><span class="hx-grow"></span><span class="hx-sm hx-num" id="hxTuN">${filled} of ${bl.length} filled</span></div>
        <div class="hx-tbar"><i id="hxTuBar" style="width:${bl.length ? Math.round(100 * filled / bl.length) : 100}%"></i></div>
        <p class="hx-mut hx-sm">Hoola only uses the words you give. Nothing is guessed or filled in for you.</p>
        <div class="hx-tfl">${bl.map((b, i) => { const v = u.vals[b.key] || '';
          return `<label class="hx-fld${v ? '' : ' miss'}" data-tf="${esc(b.key)}"><span class="hx-lab"><span class="hx-tdot">${i + 1}</span>${esc(b.label)}<small>${esc(where(b))}</small></span>
            <input class="hx-in" data-tv="${esc(b.key)}" value="${esc(v)}" placeholder="${esc(b.example || '')}" maxlength="60" autocomplete="off"></label>`; }).join('')}
          ${bl.length ? '' : '<p class="hx-mut">This template has no blanks. Make the draft and change it in the Studio.</p>'}
          ${bl.length ? `<button type="button" class="hx-lnk" data-a="tusheet">${ic('rows', 15)}Many people or shops? Fill a sheet and make one draft for each row</button>` : ''}</div>
        <div class="hx-tfo"><h3 class="hx-t">How it looks and sounds</h3><div class="hx-topts">
          ${opt('lang', 'Language', langNow, '<span class="hx-tom a">Aa</span>')}
          ${opt('face', 'Face', face(u.face)?.name || 'No face', face(u.face) ? avImg(face(u.face), 'xs') : '<span class="hx-tom b">—</span>')}
          ${opt('voice', 'Voice', voiceName(u.voice), `<span class="hx-tom c">${ic('vol', 14)}</span>`)}
          ${opt('engine', 'Engine', eng?.label || 'Hoola standard', `<span class="hx-tom d">${ic('bolt', 14)}</span>`)}</div>
          ${face(u.face) ? `<div class="hx-seg" role="radiogroup" aria-label="Where the face sits">${[['corner', 'In a corner'], ['full', 'The whole frame']].map(([k, l]) => `<button type="button" role="radio" aria-checked="${u.layout === k}" data-a="tulayout" data-val="${k}">${l}</button>`).join('')}</div>` : ''}
          <div class="hx-seg" role="radiogroup" aria-label="Frame">${[['16:9', 'Landscape 16:9'], ['9:16', 'Vertical 9:16'], ['1:1', 'Square 1:1']].map(([k, l]) => `<button type="button" role="radio" aria-checked="${tuShape(t, u) === k}" data-a="tuaspect" data-val="${k}"${t.shape === 'reel' && k !== '9:16' ? ' disabled' : ''}>${l}</button>`).join('')}</div>
          ${u.lang !== 'auto' && u.lang !== (t.lang || 'en') && !(u.lang === 'hi' && !t.mine && HI_TPL.includes(t.id)) ? `<p class="hx-hint">Hoola translates the words into ${esc(langName(u.lang))}, keeping your names, prices and dates exactly. Lines that change a number are marked for you to check.</p>` : ''}</div>
        <div id="hxTuPrice">${tuPrice(t, u)}</div></section>
      <section class="hx-tlive" aria-label="Live preview"><div class="hx-tfh"><h2 class="hx-t">Live preview</h2><span class="hx-grow"></span><span class="hx-mut hx-sm">${u.sample ? 'A sample with example words' : 'Updates as you type'}</span></div>
        <div id="hxTuStage">${tuStage(t, u)}</div><div id="hxTuScenes">${tuScenes(t, u)}</div>
        <p class="hx-mut hx-sm">After the draft opens in the Studio you can change any word, scene, face or voice. Nothing is made until you press Make there.</p></section></div>`;
  }
  function tuPaint(full) {
    const t = tplOf(ARG), u = UI.tu; if (!t || !u) return;
    const set = (sel, html) => { const e = $(sel); if (e) e.innerHTML = html; };
    set('#hxTuStage', tuStage(t, u)); set('#hxTuScenes', tuScenes(t, u)); set('#hxTuPrice', tuPrice(t, u)); fillMedia();
    const bl = t.blanks || [], filled = bl.length - tuMissing(t, u).length, nEl = $('#hxTuN'), bar = $('#hxTuBar');
    if (nEl) nEl.textContent = `${filled} of ${bl.length} filled`; if (bar) bar.style.width = `${bl.length ? Math.round(100 * filled / bl.length) : 100}%`;
    $$('[data-tf]').forEach(l => l.classList.toggle('miss', !(u.vals[l.dataset.tf] || '').trim()));
    if (full) draw();
  }
  let tuEstT = 0;
  function tuEstimate() {
    const t = tplOf(ARG), u = UI.tu; if (!t || !u) return;
    clearTimeout(tuEstT); tuEstT = setTimeout(async () => {
      const sec = Math.round(sceneTimes(tuProject(t, u)).slice(-1)[0]?.[1] || t.seconds) + (t.closing ? 2 : 1);
      try { u.est = await api('GET', `${X}/estimate?engine=${q(u.engine)}&seconds=${sec}&voice=${q(u.voice || '')}`); } catch { u.est = null; }
      if (PAGE === 'templates' && ARG === t.id) { const e = $('#hxTuPrice'); if (e) e.innerHTML = tuPrice(t, u); }
    }, 350);
  }
  function tuStop() { clearTimeout(UI.tut); if (UI.tu) UI.tu.play = false; }
  function tuPlay() {
    const t = tplOf(ARG), u = UI.tu; if (!t || !u) return;
    if (u.play) { tuStop(); return tuPaint(); }
    u.play = true; if (u.scene >= t.scenes.length - 1) u.scene = 0;
    const step = () => {
      if (!u.play || PAGE !== 'templates' || ARG !== t.id) return;
      tuPaint(); const T = sceneTimes(tuProject(t, u))[u.scene]; const d = T ? (T[1] - T[0]) * 1000 : 2500;
      UI.tut = setTimeout(() => { if (u.scene < t.scenes.length - 1) { u.scene++; step(); } else { u.play = false; tuPaint(); } }, d);
    };
    step();
  }
  async function tuMake() {
    const t = tplOf(ARG), u = UI.tu; if (!t || !u || tuMissing(t, u).length) return;
    u.busy = true; tuPaint();
    try {
      const p = await api('POST', `${H}/template/use`, {id: t.id, values: u.vals, lang: u.lang, avatar_id: u.face,
        opts: {aspect: tuShape(t, u), voice: u.voice, engine: u.engine, face_layout: u.layout}});
      u.busy = false; UI.tu = null; await load(); go('studio', p.id); if (p.notice) toast(p.notice, true); else toast('Draft ready. Nothing is made until you press Make.');
    } catch (er) { u.busy = false; tuPaint(); toast(er.message, true); }
  }

  // ---- a dialog: save a video as a template, or fill a sheet
  function dlgPaint() {
    let w = $('#hxDlg');
    if (!UI.dlg) { if (w) w.remove(); return; }
    if (!w) { w = document.createElement('div'); w.id = 'hxDlg'; w.className = 'hx-dlgw'; ROOT.appendChild(w); }
    w.innerHTML = `<div class="hx-dlgs" data-a="dlgx" aria-hidden="true"></div>${({save: svBody, pick: pickBody, need: needBody, voput: voPutBody, avphoto: avPhBody, avai: avAiBody, avtwin: avTwinBody, avren: avRenBody}[UI.dlg.k] || shBody)()}`;
    const f = w.querySelector('[data-auto]'); if (f && !w.contains(document.activeElement)) f.focus();
    fillMedia();
  }
  function dlgClose() { UI.dlg = null; dlgPaint(); }
  function pickBody() {
    const ps = (D.projects || []).filter(p => (p.scenes || []).length);
    return `<div class="hx-dlg" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><h2 class="hx-serif" id="hxDlgT">Which video?</h2><span class="hx-grow"></span>
      <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close" data-auto="1">${ic('x', 16)}</button></div>
      ${ps.length ? `<div class="hx-dlgb"><div class="hx-tpick">${ps.slice(0, 40).map(p => `<button type="button" class="hx-tpr" data-a="svopen" data-id="${esc(p.id)}">${libThumb(p)}<span class="hx-ct"><b>${esc(p.title)}</b><small class="hx-num">${esc(metaOf(p))} · ${(p.scenes || []).length} scenes</small></span></button>`).join('')}</div></div>`
        : `<div class="hx-dlgb"><p class="hx-mut">You have no videos yet. Make one first, then save it as a template.</p><div class="hx-acts"><button type="button" class="hx-btn dark" data-a="newchat">New video</button></div></div>`}</div>`;
  }
  function svMark(s, bl, sg) {   // her words as tappable words; blanks as chips; Hoola's suggestions underlined
    const spans = []; const marks = [...bl.map(b => ({text: b.text, k: 'b', key: b.label || 'blank'})), ...sg.filter(x => !bl.some(b => b.text === x.text)).map(x => ({text: x.text, k: 's'}))].sort((a, b) => b.text.length - a.text.length);
    let rest = [{t: String(s || '')}];
    for (const m of marks) rest = rest.flatMap(x => { if (x.m) return [x]; const parts = x.t.split(m.text); return parts.flatMap((p, i) => i ? [{t: m.text, m}, {t: p}] : [{t: p}]); });
    for (const x of rest) {
      if (x.m?.k === 'b') spans.push(`<button type="button" class="hx-svb" data-a="svdrop" data-t="${esc(x.t)}" aria-label="Keep “${esc(x.t)}” as it is">${esc(x.m.key)}</button>`);
      else if (x.m) spans.push(`<button type="button" class="hx-svs" data-a="svadd" data-t="${esc(x.t)}" title="Make this a blank">${esc(x.t)}</button>`);
      else spans.push(x.t.split(/(\s+)/).map(w => /^\s*$/.test(w) ? w : (() => { const core = w.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, ''); if (!core) return esc(w);
        const i = w.indexOf(core); return `${esc(w.slice(0, i))}<button type="button" class="hx-svw" data-a="svadd" data-w="1" data-t="${esc(core)}">${esc(core)}</button>${esc(w.slice(i + core.length))}`; })()).join(''));
    }
    return spans.join('');
  }
  function svBody() {
    const s = UI.dlg, p = (D.projects || []).find(x => x.id === s.id); if (!p) return '';
    const used = (D.templates || []).filter(t => t.mine).length;
    return `<div class="hx-dlg w" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">Save as a template</h2>
        <span class="hx-mut hx-sm">From <b>${esc(p.title)}</b> · ${p.scenes.length} scenes · ${esc(p.aspect === '9:16' ? 'Vertical' : p.aspect === '1:1' ? 'Square' : 'Landscape')} · ${esc(langName(p.lang))}</span></div>
        <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><label class="hx-fld"><span class="hx-lab">Name</span><input class="hx-in" id="hxSvName" value="${esc(s.name)}" maxlength="60" data-auto="1"></label>
        <div class="hx-fld"><div class="hx-sech"><span class="hx-lab">Words that change each time</span><span class="hx-grow"></span><span class="hx-sm hx-num">${s.blanks.length} blank${s.blanks.length === 1 ? '' : 's'}</span></div>
          <p class="hx-mut hx-sm">Tap a word to make it a blank; tap the next word too to make the blank longer. Next time you only fill these in. ${s.sugg.length ? 'Underlined: words Hoola thinks change, like prices, dates and names.' : ''}</p>
          <div class="hx-svs-list" id="hxSvText">${p.scenes.map((sc, i) => `<div class="hx-svr"><span class="hx-sm hx-num">Scene ${i + 1}</span><div class="hx-serifp">${svMark(sc.say, s.blanks, s.sugg)}</div></div>`).join('')}
            ${p.closing ? `<div class="hx-svr"><span class="hx-sm">Closing</span><div class="hx-serifp">${svMark(p.closing, s.blanks, s.sugg)}</div></div>` : ''}</div></div>
        ${s.blanks.length ? `<div class="hx-fld"><span class="hx-lab">Name each blank</span><div class="hx-svbl">${s.blanks.map((b, i) => `<div class="hx-svbr"><span class="hx-svq">“${esc(b.text)}”</span><span class="hx-mut hx-sm">becomes</span>
            <input class="hx-in" data-svk="${i}" value="${esc(b.label)}" maxlength="40" aria-label="Name for “${esc(b.text)}”">
            <button type="button" class="hx-ib xs" data-a="svdrop" data-t="${esc(b.text)}" aria-label="Keep “${esc(b.text)}” as it is">${ic('x', 14)}</button></div>`).join('')}</div></div>`
          : '<p class="hx-why">No blanks yet. Every video made from it will say exactly the same words.</p>'}</div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">${num(used + 1)} of 40 templates · the video itself stays as it is</span>
        <button type="button" class="hx-btn" data-a="dlgx">Cancel</button><button type="button" class="hx-btn dark" data-a="svsave"${s.busy ? ' disabled' : ''}>Save template</button></div></div>`;
  }
  async function svOpen(id) {
    const p = (D.projects || []).find(x => x.id === id); if (!p) return;
    UI.dlg = {k: 'save', id, name: p.title, blanks: [], sugg: []}; dlgPaint();
    try { const r = await api('GET', `${H}/template/suggest?project=${q(id)}`); if (UI.dlg?.id === id) { UI.dlg.sugg = r.words || []; dlgPaint(); } } catch { /* the dialog works without them */ }
  }
  const svLabel = (txt, sg) => { const k = (sg || []).find(x => x.text === txt)?.key; return k ? k.replace(/_\d+$/, '').replace(/_/g, ' ') : txt.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim().split(' ').slice(0, 3).join(' '); };
  function svAdd(txt, tapped) {
    const s = UI.dlg; txt = (txt || '').trim(); if (!s || !txt || s.blanks.some(b => b.text === txt)) return;
    const p = (D.projects || []).find(x => x.id === s.id), words = p ? [...p.scenes.map(x => x.say), p.closing || ''].join('\n') : '';
    const last = s.blanks[s.blanks.length - 1];
    if (tapped && last && Date.now() - (s.at || 0) < 8000) {     // the next word after the last blank: the blank grows
      const join = [`${last.text} ${txt}`, `${last.text}, ${txt}`].find(j => words.includes(j));
      if (join) { if (last.auto) last.label = svLabel(join, s.sugg); last.text = join; s.at = Date.now(); return dlgPaint(); }
    }
    s.at = tapped ? Date.now() : 0;
    if (s.blanks.length >= 12) return toast('A template can have up to 12 blanks.', true);
    let label = svLabel(txt, s.sugg) || 'blank', n = 2; const base = label; while (s.blanks.some(b => b.label === label)) label = `${base} ${n++}`;
    s.blanks.push({text: txt, label, auto: !(s.sugg || []).some(x => x.text === txt)}); dlgPaint();
  }
  async function svSave() {
    const s = UI.dlg; if (!s) return; s.name = ($('#hxSvName')?.value || '').trim() || s.name;
    const blanks = s.blanks.map(b => ({text: b.text, key: b.label, label: b.label.charAt(0).toUpperCase() + b.label.slice(1), example: `e.g. ${b.text}`}));
    s.busy = true; dlgPaint();
    try { await api('POST', `${H}/template`, {project: s.id, name: s.name, blanks}); dlgClose(); await load(); UI.tt = 'mine'; toast('Saved as a template.'); if (PAGE === 'templates' && !ARG) draw(); else go('templates'); }
    catch (er) { s.busy = false; dlgPaint(); toast(er.message, true); }
  }
  function csvRows(text) {
    const rows = []; let row = [], f = '', qd = false;
    for (let i = 0; i < text.length; i++) { const c = text[i];
      if (qd) { if (c === '"' && text[i + 1] === '"') { f += '"'; i++; } else if (c === '"') qd = false; else f += c; continue; }
      if (c === '"') qd = true; else if (c === ',' || c === '\t' || c === ';') { row.push(f); f = ''; } else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(f); rows.push(row); row = []; f = ''; } else f += c; }
    if (f || row.length) { row.push(f); rows.push(row); }
    return rows.map(r => r.map(x => x.trim())).filter(r => r.some(Boolean));
  }
  function sheetParse(t, text) {
    const rows = csvRows(text || ''); if (rows.length < 2) return {rows: [], cols: [], miss: []};
    const norm = s => String(s || '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '_').replace(/^_+|_+$/g, '');
    const cols = rows[0].map(h => (t.blanks || []).find(b => norm(b.key) === norm(h) || norm(b.label) === norm(h))?.key || (norm(h) === 'title' ? 'title' : ''));
    const out = rows.slice(1).map(r => Object.fromEntries(cols.map((k, i) => [k, r[i] || '']).filter(([k]) => k)));
    return {rows: out, cols, miss: (t.blanks || []).filter(b => !cols.includes(b.key))};
  }
  function shBody() {
    const s = UI.dlg, t = tplOf(s.id); if (!t) return '';
    const r = sheetParse(t, s.text), head = (t.blanks || []).map(b => b.label).join(', ');
    return `<div class="hx-dlg w" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">One draft for each row</h2>
        <span class="hx-mut hx-sm">${esc(t.name)} · up to 50 rows · each draft is free</span></div><button type="button" class="hx-ib" data-a="dlgx" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hx-dlgb">${s.done ? `<p><b>${num(s.done.made.length)} draft${s.done.made.length === 1 ? '' : 's'} made.</b> They are in the Studio; nothing is made until you press Make on each.</p>
          ${s.done.skipped.length ? `<ul class="hx-why">${s.done.skipped.map(x => `<li>Row ${x.row}: ${esc(x.why)}</li>`).join('')}</ul>` : ''}`
        : `<p class="hx-mut hx-sm">The first row names the columns: <b>${esc(head)}</b>. A column called <b>title</b> names each draft. Copy cells from a spreadsheet, or choose a CSV file.</p>
          <textarea class="hx-in hx-mono" id="hxShText" rows="8" placeholder="${esc((t.blanks || []).map(b => b.label).join(','))}&#10;${esc(Object.values(sampleOf(t)).join(','))}" data-auto="1">${esc(s.text || '')}</textarea>
          <div class="hx-acts"><button type="button" class="hx-btn s" data-a="shfile">${ic('doc', 13)}Choose a CSV file</button><input type="file" id="hxShFile" accept=".csv,.tsv,.txt,text/csv" hidden>
            <span class="hx-sm hx-mut" id="hxShSum">${r.rows.length ? `${num(r.rows.length)} row${r.rows.length === 1 ? '' : 's'}${r.miss.length ? ` · no column for: ${esc(r.miss.map(b => b.label.toLowerCase()).join(', '))}` : ' · every blank has a column'}` : ''}</span></div>`}</div>
      <div class="hx-dlgf"><span class="hx-grow"></span>${s.done ? `<button type="button" class="hx-btn" data-a="dlgx">Close</button><button type="button" class="hx-btn dark" data-a="shstudio">Open the Studio</button>`
        : `<button type="button" class="hx-btn" data-a="dlgx">Cancel</button><button type="button" class="hx-btn dark" data-a="shmake"${r.rows.length && r.rows.length <= 50 && !s.busy ? '' : ' disabled'}>${s.busy ? 'Making…' : `Make ${r.rows.length ? num(r.rows.length) + ' ' : ''}draft${r.rows.length === 1 ? '' : 's'} · free`}</button>`}</div></div>`;
  }
  async function shMake() {
    const s = UI.dlg, t = tplOf(s.id), u = UI.tu; if (!t) return;
    const r = sheetParse(t, s.text); if (!r.rows.length) return;
    s.busy = true; dlgPaint();
    try { s.done = await api('POST', `${H}/template/many`, {id: t.id, rows: r.rows, lang: u?.lang || 'auto', avatar_id: u?.face || '',
        opts: u ? {aspect: tuShape(t, u), voice: u.voice, engine: u.engine, face_layout: u.layout} : {}}); s.busy = false; await load(); dlgPaint(); }
    catch (er) { s.busy = false; dlgPaint(); toast(er.message, true); }
  }
  function tplMenu(el, id) {
    const t = tplOf(id); if (!t) return;
    menu(el, [{label: 'Use', icon: 'play', run: () => go('templates', id)},
      {label: 'Make many from a sheet', icon: 'rows', run: () => { go('templates', id); UI.dlg = {k: 'sheet', id, text: ''}; dlgPaint(); }},
      {sep: true}, {label: 'Delete template', icon: 'trash', danger: true, run: async () => { if (!confirm(`Delete “${t.name}”? Videos made from it stay.`)) return;
        try { await api('DELETE', `${H}/template?id=${q(id)}`); await load(); draw(); } catch (er) { toast(er.message, true); } }}]);
  }

  // ------------------------------------------------------------------ apps (v0.999.175: design claude.ai/artifact/EW7fbQi3VZeBoTyPyG88Ke) ---
  // Every tool that works with her videos, each saying whether it is ready on this server (read from the engines it uses,
  // GET /hub/apps), where it opens and what it costs. Five run right on this page - many names, a batch, translate, a B-roll
  // shot, from a sheet (through a template) - the rest open Hoola Vocal or Create. An app that is not connected opens a
  // short check of what it needs instead of a page that cannot work.
  const AGROUP = {voice: ['Voice & sound', 'In Hoola Vocal and Create'], shots: ['Shots & languages', 'Two run right here'], many: ['Make many', 'Every one runs here; drafts are free']};
  const AWHERE = {here: 'Runs here', vocal: 'Opens in Hoola Vocal', create: 'Opens in Create'};
  const ACOST = {free: 'Free', free_draft: 'Free draft', free_drafts: 'Free drafts', priced: 'Priced before it runs'};
  const ATINT = {voice: 'g-events', shots: 'g-updates', many: 'g-offers', face: 'g-greetings'};
  const AICON = {
    podcast: 'M12 3a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM5 11a7 7 0 0 0 14 0M12 18v3', cleanup: 'M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2',
    ownvoice: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c1.5-4 4.5-6 8-6s6.5 2 8 6',
    music: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
    broll: 'M3 5h18v14H3zM7 5v14M17 5v14M3 9h4M17 9h4M3 15h4M17 15h4',
    translate: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18',
    dub: 'M4 6h10M9 4v2M6 6c0 4 3 7 7 8M12 6c-1 4-4 7-8 8M14 20l4-9 4 9M15.5 17h5',
    lipsync: 'M3 12c3-4 6-5 9-3 3-2 6-1 9 3-3 4-6 5-9 5s-6-1-9-5zM3 12h18', batch: 'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5',
    names: 'M4 6h16M4 12h10M4 18h7M17 15l2 2 4-4', sheet: 'M4 4h16v16H4zM4 10h16M4 16h16M10 4v16',
    aiface: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9 10h.01M15 10h.01M8.5 15a5 5 0 0 0 7 0'};
  const BR_IDEAS = ['A café counter in soft morning light', 'Rain on a shop window at night', 'Hands wrapping a gift', 'A busy market street, slow pan'];
  const appOf = id => (UI.apps?.apps || []).find(a => a.id === id);
  const aTint = a => ATINT[['lipsync', 'aiface'].includes(a.id) ? 'face' : a.group];
  const aIcon = (a, s = 22) => `<svg class="hx-i" width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true"><path d="${AICON[a.id] || ''}"/></svg>`;
  async function appsLoad() { try { UI.apps = await api('GET', `${H}/apps`); } catch (e) { UI.apps = UI.apps || {apps: [], recent: []}; toast(e.message, true); } }
  function appsRows() {
    const qy = (UI.aq || '').trim().toLowerCase(), g = UI.ag || 'all';
    return (UI.apps?.apps || []).filter(a => (g === 'all' || a.group === g) && (!UI.aready || a.ready)
      && (!qy || `${a.name} ${a.line} ${AGROUP[a.group][0]}`.toLowerCase().includes(qy)));
  }
  function appCard(a) {
    return `<article class="hx-ac${a.ready ? '' : ' off'}"><div class="hx-ach"><span class="hx-ati ${aTint(a)}">${aIcon(a)}</span><span class="hx-grow"></span>
        <span class="hx-ast ${a.ready ? 'ok' : 'no'}"><i></i>${a.ready ? 'Ready' : 'Not connected'}</span></div>
      <b class="hx-acn">${esc(a.name)}</b><p>${esc(a.line)}</p>
      <div class="hx-atags"><span>${esc(AWHERE[a.where])}</span><span class="${a.cost === 'priced' ? 'p' : 'f'}">${esc(ACOST[a.cost])}</span></div>
      <button type="button" class="hx-btn ${a.ready ? 'dark' : ''}" data-a="aopen" data-id="${esc(a.id)}">${a.ready ? (a.where === 'here' ? 'Start' : 'Open') : 'See what it needs'}</button></article>`;
  }
  function appsList() {
    const rows = appsRows();
    if (!(UI.apps?.apps || []).length) return '<p class="hx-mut">Loading the apps…</p>';
    if (!rows.length) return `<div class="hx-empty"><b>No apps match</b><span>Try another word, or show every app.</span><button type="button" class="hx-btn s" data-a="aclear">Show all apps</button></div>`;
    return Object.keys(AGROUP).map(g => { const r = rows.filter(a => a.group === g); return r.length ? `<section class="hx-asec" aria-labelledby="hxAg-${g}"><div class="hx-sech"><b class="hx-t" id="hxAg-${g}">${esc(AGROUP[g][0])}</b><span class="hx-mut hx-sm">${esc(AGROUP[g][1])}</span></div>
      <div class="hx-agrid">${r.map(appCard).join('')}</div></section>` : ''; }).join('');
  }
  function appFeature(id, kicker, line, cta, meta) {
    const a = appOf(id); if (!a) return '';
    return `<article class="hx-afeat ${aTint(a)}"><div class="hx-afst" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="hx-growf"><small>${esc(kicker)}</small><h3 class="hx-serif">${esc(a.name)}</h3><p>${esc(line)}</p>
        <div class="hx-acts"><button type="button" class="hx-btn dark" data-a="aopen" data-id="${esc(id)}">${esc(a.ready ? cta : 'See what it needs')}</button><span class="hx-sm">${esc(a.ready ? meta : 'Needs an engine on this server')}</span></div></div></article>`;
  }
  function appsLib() {
    const all = UI.apps?.apps || [], n = g => all.filter(a => g === 'all' || a.group === g).length, rec = UI.apps?.recent || [];
    return `<div class="hx-doc hx-alib"><div class="hx-libh"><div class="hx-growf"><h2 class="hx-serif">Apps</h2>
        <p class="hx-mut">Tools that work with your videos. Some run right here; others open in Hoola Vocal or Create. Each one says what it needs and what it costs before you start.</p></div></div>
      <div class="hx-libbar"><label class="hx-lsearch hx-tsearch">${ic('search', 15)}<span class="hx-sr">Search apps</span><input id="hxAq" type="search" placeholder="What do you want to do? Dub, clean up, names…" value="${esc(UI.aq || '')}" autocomplete="off"></label>
        <div class="hx-tchips" role="radiogroup" aria-label="Kind">${['all', ...Object.keys(AGROUP)].map(g => `<button type="button" role="radio" aria-checked="${(UI.ag || 'all') === g}" class="hx-chip" data-a="agrp" data-val="${g}">${esc(g === 'all' ? 'All' : AGROUP[g][0])}<span class="hx-num hx-mut">${num(n(g))}</span></button>`).join('')}</div>
        <span class="hx-grow"></span><label class="hx-acheck"><input type="checkbox" id="hxAready"${UI.aready ? ' checked' : ''}>Only ready to use</label></div>
      ${rec.length ? `<div class="hx-arec"><span class="hx-mut hx-sm">Recently used</span>${rec.map(a => `<button type="button" class="hx-arp" data-a="aopen" data-id="${esc(a.id)}"><span class="hx-ati xs ${aTint(a)}">${aIcon(a, 13)}</span>${esc(a.name)}<span class="hx-mut">${esc(ago(a.used))}</span></button>`).join('')}</div>` : ''}
      ${!UI.aq && (UI.ag || 'all') === 'all' && !UI.aready ? `<div class="hx-afeats">${appFeature('names', 'MAKE MANY · RUNS HERE', 'Thank each customer by name, or greet every student. Paste the names; each becomes its own draft.', 'Start', `Drafts are free · up to ${num(D.limits?.batch || 20)}`)}
        ${appFeature('dub', 'LANGUAGES · OPENS IN HOOLA VOCAL', 'Your video in other languages, in voices matched to each speaker. You check every line first.', 'Choose a video', '140 languages · priced before it runs')}</div>` : ''}
      <div id="hxAppList">${appsList()}</div></div>`;
  }

  // ---- the apps that run right here
  const arState = () => (UI.ar = UI.ar || {vid: '', names: '', scripts: '', lang: '', face: SET.face || '', est: null, busy: false, tlang: ''});
  const nameList = t => [...new Set(String(t || '').split(/\n|,/).map(s => s.trim()).filter(Boolean))];
  const scriptList = t => String(t || '').split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
  const hasName = p => JSON.stringify(p.scenes || []).includes('{name}') || String(p.closing || '').includes('{name}');
  function arHead(a) {
    return `<div class="hx-arh"><span class="hx-ati ${aTint(a)}">${aIcon(a, 18)}</span><div class="hx-growf"><h2 class="hx-serif">${esc(a.name)}</h2><span class="hx-mut hx-sm">${esc(a.line)}</span></div>
      <span class="hx-atag ${a.cost === 'priced' ? 'p' : 'f'}">${esc(AWHERE[a.where])} · ${esc(ACOST[a.cost].toLowerCase())}</span></div>`;
  }
  const arVid = (p, on) => `<button type="button" class="hx-tpr${on ? ' on' : ''}" data-a="arvid" data-id="${esc(p.id)}" role="radio" aria-checked="${on}">${libThumb(p)}<span class="hx-ct"><b>${esc(p.title)}</b><small class="hx-num">${esc(metaOf(p))} · ${(p.scenes || []).length} scenes</small></span><span class="hx-arr" aria-hidden="true"></span></button>`;
  function arPrice(count, unit, sec) {
    const r = arState(), e = r.est;
    return `<div class="hx-tprice"><div class="r"><b>${num(count)} ${unit}${count === 1 ? '' : 's'}</b><span class="hx-grow"></span><b class="ok">Free</b></div>
      <div class="r hx-mut"><span>Each video, made later from the Studio</span><span class="hx-grow"></span><span class="hx-num">${e ? `about ${cr(e.credits)} each` : '…'}</span></div>
      <p class="hx-mut hx-sm">Nothing is made or sent until you press Make on each draft.${sec ? ` About ${esc(secs(sec))} each.` : ''}</p></div>`;
  }
  let arEstT = 0;
  function arEstimate(sec) {
    clearTimeout(arEstT); arEstT = setTimeout(async () => {
      const r = arState(); try { r.est = await api('GET', `${X}/estimate?engine=${q(defEngine())}&seconds=${Math.max(10, Math.round(sec || 30))}&voice=${q(SET.voice || '')}`); } catch { r.est = null; }
      const e = $('#hxArPrice'); if (e) e.innerHTML = arPriceNow();
    }, 300);
  }
  function arPriceNow() {
    const r = arState();
    if (ARG === 'names') { const p = (D.projects || []).find(x => x.id === r.vid); return arPrice(nameList(r.names).length, 'draft', p ? lenOf(p) : 0); }
    if (ARG === 'batch') return arPrice(scriptList(r.scripts).length, 'draft', 0);
    return '';
  }
  function arNames(a) {
    const r = arState(), ps = (D.projects || []).filter(hasName), p = ps.find(x => x.id === r.vid) || ps[0]; if (p) r.vid = p.id;
    const names = nameList(r.names), max = D.limits?.batch || 20, first = names[0] || 'Amara';
    const fill = s => esc(String(s || '')).replace(/\{name\}/g, `<mark class="hx-tv">${esc(first)}</mark>`);
    return `<div class="hx-tuse"><section class="hx-tform" aria-label="Set it up">${arHead(a)}
        <div class="hx-arstep"><span class="hx-tdot">1</span><b>The video</b></div>
        <p class="hx-mut hx-sm">Only videos that say <mark class="hx-tv">{name}</mark> are shown. Write {name} in a scene in the Studio to add one.</p>
        ${ps.length ? `<div class="hx-tpick" role="radiogroup" aria-label="The video">${ps.slice(0, 8).map(x => arVid(x, x.id === r.vid)).join('')}</div>`
          : `<div class="hx-why">None of your videos says {name} yet. Open one in the Studio and write {name} where the person's name goes.</div><div class="hx-acts"><button type="button" class="hx-btn" data-a="go" data-p="studio">Open the Studio</button></div>`}
        <div class="hx-arstep"><span class="hx-tdot">2</span><label for="hxArNames"><b>The names, one a line</b></label><span class="hx-grow"></span><span class="hx-sm hx-num" id="hxArN">${num(names.length)} name${names.length === 1 ? '' : 's'} · up to ${num(max)}</span></div>
        <textarea class="hx-in" id="hxArNames" rows="7" placeholder="Amara&#10;Kenji&#10;Sofía">${esc(r.names)}</textarea>
        <p class="hx-hint">Each name is said the way your Hoola Vocal dictionary says it. Duplicates are left out.</p>
        <div id="hxArPrice">${arPriceNow()}</div>
        <div class="hx-acts"><span class="hx-grow"></span><button type="button" class="hx-btn dark l" data-a="arnames"${p && names.length && names.length <= max && !r.busy ? '' : ' disabled'}>${r.busy ? 'Making the drafts…' : `Make ${names.length ? num(names.length) + ' ' : ''}draft${names.length === 1 ? '' : 's'}`}</button></div></section>
      <section class="hx-tlive" aria-label="What you will get"><div class="hx-tfh"><h2 class="hx-t">What you will get</h2><span class="hx-grow"></span><span class="hx-mut hx-sm">${names.length ? 'Showing the first name' : 'An example name'}</span></div>
        ${p ? `<div class="hx-preview ${p.aspect === '9:16' ? 'tall' : p.aspect === '1:1' ? 'sq' : ''}" style="--brand:${esc(brandColor())}"><div class="hx-pvlook"><b>${fill(lookText(p.scenes[0]?.look) || p.title)}</b></div>
            ${face(p.avatar_id) ? `<span class="hx-pvface">${avImg(face(p.avatar_id), 'l')}</span>` : ''}<p class="hx-pvcap">${fill(p.scenes[0]?.say)}</p></div>
          <ol class="hx-arl" id="hxArList">${(names.length ? names : []).slice(0, 6).map((n, i) => `<li><span class="n">${i + 1}</span><b>${esc(n)}</b><span>${esc(String(p.scenes[0]?.say || '').replace(/\{name\}/g, n))}</span></li>`).join('')}</ol>
          ${names.length > 6 ? `<p class="hx-mut hx-sm">and ${num(names.length - 6)} more</p>` : ''}` : '<p class="hx-mut">Choose a video to see it here.</p>'}</section></div>`;
  }
  function arBatch(a) {
    const r = arState(), sc = scriptList(r.scripts), max = D.limits?.batch || 20;
    return `<div class="hx-tuse"><section class="hx-tform" aria-label="Set it up">${arHead(a)}
        <div class="hx-arstep"><span class="hx-tdot">1</span><label for="hxArBatch"><b>The scripts</b></label><span class="hx-grow"></span><span class="hx-sm hx-num" id="hxArN">${num(sc.length)} script${sc.length === 1 ? '' : 's'} · up to ${num(max)}</span></div>
        <textarea class="hx-in hx-serifp" id="hxArBatch" rows="10" placeholder="Our new opening hours are 9 am to 7 pm, Monday to Saturday.&#10;&#10;This week only: 20% off every plant in the shop.">${esc(r.scripts)}</textarea>
        <p class="hx-hint">Leave an empty line between scripts. Each one becomes its own video, split into scenes by sentence.</p>
        <div class="hx-arstep"><span class="hx-tdot">2</span><b>Who says them</b></div>
        <div class="hx-topts"><button type="button" class="hx-topt" data-a="arpick" data-k="lang"><span class="hx-tom a">Aa</span><span class="hx-growf"><small>Language</small><b>${esc(r.lang ? langName(r.lang) : 'Auto')}</b></span>${ic('down', 13)}</button>
          <button type="button" class="hx-topt" data-a="arpick" data-k="face">${face(r.face) ? avImg(face(r.face), 'xs') : '<span class="hx-tom b">—</span>'}<span class="hx-growf"><small>Face</small><b>${esc(face(r.face)?.name || 'No face')}</b></span>${ic('down', 13)}</button></div>
        <div id="hxArPrice">${arPriceNow()}</div>
        <div class="hx-acts"><span class="hx-grow"></span><button type="button" class="hx-btn dark l" data-a="arbatch"${sc.length && sc.length <= max && !r.busy ? '' : ' disabled'}>${r.busy ? 'Making the drafts…' : `Make ${sc.length ? num(sc.length) + ' ' : ''}draft${sc.length === 1 ? '' : 's'}`}</button></div></section>
      <section class="hx-tlive" aria-label="What you will get"><div class="hx-tfh"><h2 class="hx-t">What you will get</h2></div>
        ${sc.length ? `<ol class="hx-arl" id="hxArList">${sc.slice(0, 8).map((s, i) => `<li><span class="n">${i + 1}</span><span>${esc(s)}</span></li>`).join('')}</ol>${sc.length > 8 ? `<p class="hx-mut hx-sm">and ${num(sc.length - 8)} more</p>` : ''}`
          : '<p class="hx-mut">Each script you paste shows here as its own draft.</p>'}</section></div>`;
  }
  function arTranslate(a) {
    const r = arState(), ps = (D.projects || []).filter(p => (p.scenes || []).length), p = ps.find(x => x.id === r.vid) || ps[0]; if (p) r.vid = p.id;
    return `<div class="hx-tuse"><section class="hx-tform" aria-label="Set it up">${arHead(a)}
        <div class="hx-arstep"><span class="hx-tdot">1</span><b>The video</b></div>
        ${ps.length ? `<div class="hx-tpick" role="radiogroup" aria-label="The video">${ps.slice(0, 8).map(x => arVid(x, x.id === r.vid)).join('')}</div>` : '<p class="hx-why">You have no videos yet. Make one first.</p>'}
        <div class="hx-arstep"><span class="hx-tdot">2</span><b>The language</b></div>
        <button type="button" class="hx-topt" data-a="arpick" data-k="tlang"><span class="hx-tom a">Aa</span><span class="hx-growf"><small>Into</small><b>${esc(r.tlang ? langName(r.tlang) : 'Choose a language')}</b></span>${ic('down', 13)}</button>
        <p class="hx-hint">A new draft; the video you have stays as it is. Names, prices and dates are kept exactly, and a line that changes a number is marked for you to check.</p>
        <div class="hx-tprice"><div class="r"><b>The translated draft</b><span class="hx-grow"></span><b class="ok">Free</b></div><p class="hx-mut hx-sm">The video is priced again in the Studio before anything is made.</p></div>
        <div class="hx-acts"><span class="hx-grow"></span><button type="button" class="hx-btn dark l" data-a="artrans"${p && r.tlang && r.tlang !== p.lang && !r.busy ? '' : ' disabled'}>${r.busy ? 'Translating…' : 'Make the translated draft'}</button></div></section>
      <section class="hx-tlive" aria-label="The words"><div class="hx-tfh"><h2 class="hx-t">The words now</h2><span class="hx-grow"></span><span class="hx-mut hx-sm">${p ? esc(langName(p.lang)) : ''}</span></div>
        ${p ? `<ol class="hx-arl">${p.scenes.map((s, i) => `<li><span class="n">${i + 1}</span><span class="hx-serifp">${esc(s.say)}</span></li>`).join('')}</ol>` : ''}</section></div>`;
  }
  function arBroll(a) {
    const br = UI.broll, shots = D.live?.broll || [], qn = br.q;
    return `<div class="hx-tuse"><section class="hx-tform" aria-label="Describe the shot">${arHead(a)}
        <label class="hx-fld"><span class="hx-lab">What the shot shows</span><textarea class="hx-in" id="hxArBr" rows="4" maxlength="800" placeholder="Morning light on a bakery counter, fresh bread on wooden shelves, slow push in.">${esc(br.prompt || '')}</textarea>
          <span class="hx-hint">A place, a product or a mood. Shots never show a real person; a face goes in through your avatar.</span></label>
        <div class="hx-tchips">${BR_IDEAS.map(t => `<button type="button" class="hx-chip s" data-a="abidea" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div>
        <div class="hx-fld"><span class="hx-lab">Length</span><div class="hx-seg" role="radiogroup" aria-label="Length">${[4, 6, 8].map(n => `<button type="button" role="radio" aria-checked="${br.seconds === n}" data-a="abs" data-val="${n}">${n} s</button>`).join('')}</div></div>
        <div class="hx-fld"><span class="hx-lab">Frame</span><div class="hx-seg" role="radiogroup" aria-label="Frame">${[['16:9', 'Landscape 16:9'], ['9:16', 'Vertical 9:16']].map(([k, l]) => `<button type="button" role="radio" aria-checked="${br.aspect === k}" data-a="aba" data-val="${k}">${l}</button>`).join('')}</div></div>
        <div class="hx-tprice"><div class="r hx-mut"><span>${num(br.seconds)}-second shot</span><span class="hx-grow"></span><span class="hx-num">${qn ? cr(qn.credits) : '…'}</span></div>
          <div class="r"><b>Total</b><span class="hx-grow"></span><b class="hx-num">${qn ? cr(qn.credits) : '…'}${qn?.usd ? ` <small class="hx-mut">≈ US$${(+qn.usd).toFixed(2)}</small>` : ''}</b></div>
          <div class="r"><span class="hx-mut hx-sm hx-grow">If the shot cannot be made, its credits are not used.</span>
            <button type="button" class="hx-btn dark l" data-a="abmake"${qn && !br.busy ? '' : ' disabled'}>${br.busy ? 'Starting…' : `Make the shot${qn ? ' · ' + cr(qn.credits) : ''}`}</button></div></div></section>
      <section class="hx-tlive" aria-label="Your shots"><div class="hx-tfh"><h2 class="hx-t">Your shots</h2><span class="hx-grow"></span><span class="hx-mut hx-sm">Use one in any scene from the Studio</span></div>
        ${shots.length ? `<div class="hx-abg">${shots.map(s => `<article class="hx-abs"><div class="hx-absv${s.aspect === '9:16' ? ' tall' : ''}">${s.status === 'ready' ? `<video class="hx-player" controls playsinline preload="metadata" data-broll="${esc(s.id)}"></video>`
            : `<span class="hx-st ${s.status === 'failed' ? 'bad' : 'work'}">${s.status === 'failed' ? 'Could not make it' : 'Making it'}</span>`}<span class="hx-tplen hx-num">${clock(s.seconds)}</span></div>
          <div class="hx-absb"><span>${esc(s.prompt)}</span>${s.status === 'failed' && s.error ? `<small class="hx-why">${esc(scrub(s.error))}</small>` : ''}</div></article>`).join('')}</div>`
          : '<p class="hx-mut">Your shots appear here as they are made.</p>'}</section></div>`;
  }
  function appRun(id) {
    const a = appOf(id); if (!a) return '<div class="hx-doc"><p class="hx-mut">Loading…</p></div>';
    return id === 'names' ? arNames(a) : id === 'batch' ? arBatch(a) : id === 'translate' ? arTranslate(a) : id === 'broll' ? arBroll(a) : appsLib();
  }
  async function appOpen(el, id) {
    if (!appOf(id)) await appsLoad();
    const a = appOf(id); if (!a) return;
    if (!a.ready) { UI.dlg = {k: 'need', id}; return dlgPaint(); }
    api('POST', `${H}/apps/used`, {id}).then(appsLoad).catch(() => {});
    if (id === 'sheet') { const ts = (D.templates || []).filter(t => (t.blanks || []).length);
      return menu(el, [{header: 'Which template?'}, ...ts.map(t => ({label: t.name, sub: `${t.blanks.length} blank${t.blanks.length === 1 ? '' : 's'}${t.mine ? ' · yours' : ''}`, run: () => { go('templates', t.id); UI.dlg = {k: 'sheet', id: t.id, text: ''}; dlgPaint(); }}))], {width: 300}); }
    if (a.where === 'here') { UI.ar = null; return go('apps', id); }
    if (a.where === 'vocal') { window.__hvPage = a.page; leave(); return ctx.go ? ctx.go('vocal') : back?.(); }
    location.assign(`/console/?v=creative&a=${q(a.page)}`);
  }
  function needBody() {
    const a = appOf(UI.dlg.id); if (!a) return '';
    const alt = (UI.apps?.apps || []).filter(x => x.ready && x.id !== a.id && (x.group === a.group || ['dub', 'translate'].includes(x.id))).slice(0, 3);
    return `<div class="hx-dlg" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><span class="hx-ati ${aTint(a)}">${aIcon(a)}</span>
        <div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">${esc(a.name)}</h2><span class="hx-ast no"><i></i>Not connected on this Hoola yet</span></div>
        <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close" data-auto="1">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><p>${esc(a.line)} It needs ${esc(a.needs)}, which the owner of this Hoola connects once on the server. Nothing is charged and nothing is sent while it is off.</p>
        <div class="hx-svs-list"><div class="hx-svr"><span class="hx-anck no">!</span><div><b>${esc(a.needs.charAt(0).toUpperCase() + a.needs.slice(1))}</b><p class="hx-mut hx-sm">Not connected. Once it is, this app turns Ready by itself.</p></div></div>
          <div class="hx-svr"><span class="hx-anck ok">✓</span><div><b>${esc(AWHERE[a.where])}</b><p class="hx-mut hx-sm">${a.where === 'here' ? 'This page is ready for it.' : 'That tool is ready to open it.'}</p></div></div></div>
        ${alt.length ? `<div class="hx-fld"><span class="hx-lab">Meanwhile, these work today</span><div class="hx-acts">${alt.map(x => `<button type="button" class="hx-btn" data-a="aopen" data-id="${esc(x.id)}">${esc(x.name)}</button>`).join('')}</div></div>` : ''}</div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">The owner sees what to add in Engines.</span><button type="button" class="hx-btn" data-a="dlgx">Close</button><button type="button" class="hx-btn dark" data-a="aeng">Open Engines</button></div></div>`;
  }
  let abT = 0;
  function abWatch() {
    clearTimeout(abT);
    if (!(D.live?.broll || []).some(s => s.status === 'making')) return;
    abT = setTimeout(async () => { if (PAGE !== 'apps' || ARG !== 'broll') return; await load(); if (PAGE === 'apps' && ARG === 'broll' && !$('#hxArBr:focus')) draw(); abWatch(); }, 20000);
  }
  async function abQuote() { try { UI.broll.q = await api('GET', `${X}/broll/quote?seconds=${UI.broll.seconds}`); } catch { UI.broll.q = null; } if (PAGE === 'apps' && ARG === 'broll') draw(); }

  // ---- avatars (v0.999.176 AVATARS, REDESIGNED: her faces as cards with their consent record, a side panel per face,
  //      a face from a photo (whose face, size checked), a face made by AI (no real person, priced first), a video twin explained)
  Object.assign(P, {
    camera: '<path d="M4 7h3l2-3h6l2 3h3v13H4z"/><circle cx="12" cy="13" r="4"/>',
    wand: '<path d="M12 3l2.2 5.8L20 11l-5.8 2.2L12 19l-2.2-5.8L4 11l5.8-2.2z"/>',
    video: '<rect x="3" y="6" width="12" height="12" rx="2"/><path d="M15 10l6-3v10l-6-3z"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    pen: '<path d="M4 20h4L19 9l-4-4L4 16zM14 6l4 4"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>'});
  const AVMAX = 12;
  const avKind = a => (a.kind === 'ai' || a.ai) ? 'ai' : 'photo';
  const avUses = a => (D.projects || []).filter(p => p.avatar_id === a.id);
  const avWhen = s => { const d = String(s || '').slice(0, 10); if (!d) return ''; const t = new Date(d + 'T00:00:00');
    return isNaN(t) ? d : t.toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric'}); };
  const avConsent = a => avKind(a) === 'ai' ? 'Not a real person · marked as AI'
    : a.who === 'agreed' && a.person ? `${a.person} agreed · ${avWhen(a.consent_at)}` : `Consent · ${avWhen(a.consent_at)}`;
  const avUsedLine = a => { const n = avUses(a).length; return n ? `In ${num(n)} video${n === 1 ? '' : 's'}` : 'Not used yet'; };
  const avTint = a => avKind(a) === 'ai' ? 'ai' : ['t1', 't2', 't3', 't4'][[...String(a.id)].reduce((x, c) => x + c.charCodeAt(0), 0) % 4];
  const avPortrait = (a, cls = '') => `<span class="hx-avp ${avTint(a)} ${cls}"><img data-av="${esc(a.id)}" alt=""><b aria-hidden="true">${esc((a.name || 'H').slice(0, 1).toUpperCase())}</b></span>`;
  function avTalkers() {
    const es = (D.engines?.engines || []).filter(e => e.job === 'video');
    const still = es.find(e => !e.face) || {label: 'Hoola standard (still photo)', ready: true, price: 'free'};
    return [{label: still.face ? still.label : 'Hoola standard (still photo)', ready: true, price: 'Free'},
      ...es.filter(e => e.face).map(e => ({label: e.label, ready: e.ready, price: e.ready ? (e.price === 'free' ? 'Free' : e.price.replace('≈ ', 'about ')) : 'Not connected'}))];
  }
  function avList() {
    const st = UI.av || {}, all = D.avatars || [], ql = (st.q || '').trim().toLowerCase();
    let xs = all.filter(a => (st.kind || 'all') === 'all' || avKind(a) === st.kind).filter(a => !ql || a.name.toLowerCase().includes(ql));
    if ((st.sort || 'used') === 'used') xs = [...xs].sort((x, y) => avUses(y).length - avUses(x).length);
    else if (st.sort === 'name') xs = [...xs].sort((x, y) => x.name.localeCompare(y.name));
    if (!xs.length) return `<div class="hx-empty"><b>No face matches</b><span>Try another word, or show all faces.</span></div>`;
    return `<div class="hx-avgrid">${xs.map(a => { const on = (UI.av?.sel || all[0]?.id) === a.id, def = SET.face === a.id;
      return `<button type="button" class="hx-avc2${on ? ' on' : ''}" data-a="avsel" data-id="${esc(a.id)}" aria-pressed="${on}">
        ${avPortrait(a)}<span class="hx-avk ${avKind(a)}">${avKind(a) === 'ai' ? 'Made by AI' : 'Your photo'}</span>${def ? '<span class="hx-avdef">Default</span>' : ''}
        <span class="hx-avt"><b>${esc(a.name)}</b><small>${esc(avConsent(a))}</small><small class="hx-mut">${esc(avUsedLine(a))}</small></span></button>`; }).join('')}</div>`;
  }
  function avPanel(a) {
    if (!a) return '';
    const uses = avUses(a), def = SET.face === a.id, ai = avKind(a) === 'ai';
    return `<aside class="hx-avside" aria-label="${esc(a.name)}">${avPortrait(a, 'big')}
      <span class="hx-avk ${avKind(a)} in">${ai ? 'Made by AI' : 'Your photo'}</span>
      <div class="hx-avsb"><div class="hx-avnm"><h2 class="hx-serif">${esc(a.name)}</h2>
          <button type="button" class="hx-ib" data-a="avren" data-id="${esc(a.id)}" aria-label="Rename ${esc(a.name)}">${ic('pen', 15)}</button></div>
        <div class="hx-avrec ${ai ? 'ai' : ''}">${ic(ai ? 'wand' : 'shield', 16)}<span><b>${ai ? 'Not a real person' : 'Consent on record'}</b><br>${ai
          ? 'Made by AI from your words. Every video with this face carries the AI mark.'
          : esc(a.who === 'agreed' && a.person ? `${a.person} agreed to be in AI videos, ticked on ${avWhen(a.consent_at)}.` : `Your own face, ticked on ${avWhen(a.consent_at)}.`) + ' Only you can use it.'}</span></div>
        <div class="hx-avsec"><span class="hx-lab">Can talk with</span>${(() => { const ts = avTalkers(), on = ts.filter(t => t.ready), off = ts.length - on.length;
          return on.map(t => `<div class="hx-avtk"><i class="ok"></i><span class="hx-grow">${esc(t.label)}</span><span class="hx-mut hx-num">${esc(t.price)}</span></div>`).join('')
            + (off ? `<button type="button" class="hx-avtk more" data-a="aeng"><i class="no"></i><span class="hx-grow">${num(off)} more face engine${off === 1 ? ' is' : 's are'} not connected on this server</span>${ic('fwd', 14)}</button>` : ''); })()}</div>
        <div class="hx-avsec"><span class="hx-lab">${uses.length ? `In ${num(uses.length)} video${uses.length === 1 ? '' : 's'}` : 'Not in a video yet'}</span>
          ${uses.length ? `<div class="hx-avvids">${uses.slice(0, 4).map(p => `<button type="button" class="hx-avvid" data-a="avvid" data-id="${esc(p.id)}" title="${esc(p.title)}">${libThumb(p)}</button>`).join('')}</div>` : ''}</div>
        <div class="hx-avact"><button type="button" class="hx-btn dark l" data-a="avtest" data-id="${esc(a.id)}"${UI.av?.busy ? ' disabled' : ''}>${UI.av?.busy ? 'Making the draft…' : 'Make a test video'}</button>
          <div class="hx-acts"><button type="button" class="hx-btn hx-grow" data-a="avdefault" data-id="${esc(a.id)}"${def ? ' aria-pressed="true"' : ''}>${def ? `${ic('check', 14)}Default face` : 'Make it the default'}</button>
            <button type="button" class="hx-btn danger hx-grow" data-a="avdel" data-id="${esc(a.id)}">Remove</button></div>
          <span class="hx-mut hx-sm">The test video is a free one-scene draft in the Studio. Making it talk is priced before it runs.</span></div></div></aside>`;
  }
  function avPage() {
    const all = D.avatars || [], st = UI.av || (UI.av = {kind: 'all', q: '', sort: 'used', sel: ''});
    if (st.sel && !all.some(a => a.id === st.sel)) st.sel = '';
    const sel = all.find(a => a.id === (st.sel || all[0]?.id)), full = all.length >= AVMAX;
    const n = k => all.filter(a => k === 'all' || avKind(a) === k).length;
    const way = (k, icon, name, line, tag, tcls) => `<button type="button" class="hx-avway" data-a="${k}"${full && k !== 'avtwin' ? ' disabled' : ''}>
      <span class="hx-avwi ${k}">${ic(icon, 22)}</span><span class="hx-ct"><b>${name}</b><small>${line}</small><span class="hx-avtag ${tcls}">${tag}</span></span></button>`;
    return `<div class="hx-doc hx-avpage"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Avatars</h2>
          <p class="hx-mut">The faces in your videos. A real face is used only with consent: it is you, or the person agreed. An AI-made face is no real person and is marked as AI wherever it shows.</p></div>
        <div class="hx-acts hx-avhd"><span class="hx-avcount hx-num">${num(all.length)} of ${AVMAX} faces</span>
        <button type="button" class="hx-btn dark" data-a="avadd"${full ? ' disabled' : ''}>${ic('plus', 14)}Add a face</button></div></div>
      <section class="hx-avways" aria-label="Ways to add a face">
        ${way('avadd', 'camera', 'From your photo', 'A clear photo facing the camera. You confirm it is you, or the person agreed.', 'Free', 'ok')}
        ${way('avai', 'wand', 'Made by AI', 'Describe a presenter; pick one of four. No real person, so no consent is needed.', 'Priced first', 'pr')}
        ${way('avtwin', 'video', 'A video twin', 'A short filmed video of you, read with a consent line, for lips that move.', 'Needs an engine on this server', 'no')}</section>
      ${full ? `<p class="hx-why">You have ${AVMAX} faces, the most there can be. Remove one to add another.</p>` : ''}
      ${all.length ? `<div class="hx-avbody"><div class="hx-avmain"><div class="hx-avbar">
          ${[['all', 'All'], ['photo', 'Your photos'], ['ai', 'Made by AI']].map(([k, l]) => `<button type="button" class="hx-chip${(st.kind || 'all') === k ? ' on' : ''}" data-a="avkind" data-val="${k}">${l} <span class="hx-num">${n(k)}</span></button>`).join('')}
          <span class="hx-grow"></span><label class="hx-avq">${ic('search', 15)}<span class="hx-sr">Search faces</span><input type="search" id="hxAvq" placeholder="Search faces" value="${esc(st.q || '')}"></label>
          <button type="button" class="hx-chip" data-a="avsort" aria-haspopup="menu">${{used: 'Most used', name: 'By name', new: 'Newest'}[st.sort || 'used']}${ic('down', 12)}</button></div>
        <div id="hxAvList">${avList()}</div></div>${avPanel(sel)}</div>`
        : `<div class="hx-avfirst"><span class="hx-avp t1 big" aria-hidden="true"><b>${ic('user', 40)}</b></span><div><b class="hx-serif">No faces yet</b>
          <p class="hx-mut">Add your photo and your videos can show you talking, or make a presenter with AI. Videos work without a face too: the words and your voice carry them.</p>
          <div class="hx-acts"><button type="button" class="hx-btn dark" data-a="avadd">${ic('camera', 14)}Add your photo</button><button type="button" class="hx-btn" data-a="avai">${ic('wand', 14)}Make one with AI</button></div></div></div>`}</div>`;
  }
  // the photo window
  function avPhBody() {
    const s = UI.dlg, ok = s.file && s.real && s.big && s.consent;
    const chk = (good, t, d) => `<div class="hx-avck"><span class="hx-anck ${good === true ? 'ok' : good === false ? 'no' : 'i'}">${good === true ? '✓' : good === false ? '!' : 'i'}</span><span><b>${t}</b> <span class="hx-mut">${d}</span></span></div>`;
    return `<div class="hx-dlg w" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">Add a face from a photo</h2>
        <span class="hx-mut hx-sm">Free. Nothing is made until you use the face in a video.</span></div><button type="button" class="hx-ib" data-a="dlgx" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><div class="hx-avph"><div class="hx-avphl">
          <button type="button" class="hx-avdrop${s.url ? ' has' : ''}" data-a="avpick" aria-label="${s.url ? 'Choose another photo' : 'Choose a photo'}">${s.url ? `<img src="${esc(s.url)}" alt="The chosen photo"><span class="hx-avoval" aria-hidden="true"></span><span class="hx-avre">Choose another</span>`
            : `${ic('camera', 28)}<b>Choose a photo</b><small>PNG, JPG or WebP · a clear face, facing the camera</small>`}</button>
          ${s.file ? `<div class="hx-avcks">${chk(s.real, s.real ? 'A real photo.' : 'Not a photo.', s.real ? `${esc(s.type)}, ${s.size >= 1048576 ? (s.size / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(s.size / 1024)) + ' KB'}.` : 'Use a PNG, JPG or WebP picture.')}
            ${s.real ? chk(s.big, s.big ? 'Big enough.' : 'Too small.', `${num(s.w)} × ${num(s.h)}${s.big ? (Math.min(s.w, s.h) >= 720 ? ', good for a full-screen face.' : ', fine for a face in the corner.') : `. Use one at least 300 pixels on each side.`}`) : ''}
            ${s.real ? chk(s.h >= s.w ? true : null, s.h >= s.w ? 'Upright.' : 'Wider than tall.', s.h >= s.w ? 'Taller than it is wide, like a portrait.' : 'It works; a portrait photo frames the face better.') : ''}
            ${chk(null, 'Look at it yourself:', 'one face, facing the camera, nothing covering the mouth.')}</div>` : ''}</div>
        <div class="hx-avphr"><label class="hx-fld"><span class="hx-lab">Name</span><input class="hx-in" id="hxAvNm" maxlength="40" placeholder="Meghana" value="${esc(s.name || '')}" data-auto="1"></label>
          <fieldset class="hx-avwho"><legend class="hx-lab">Whose face is this?</legend>
            <label class="hx-avopt${s.who !== 'agreed' ? ' on' : ''}"><input type="radio" name="hxAvWho" value="me"${s.who !== 'agreed' ? ' checked' : ''}><span><b>Mine</b><small>It is my own face.</small></span></label>
            <label class="hx-avopt${s.who === 'agreed' ? ' on' : ''}"><input type="radio" name="hxAvWho" value="agreed"${s.who === 'agreed' ? ' checked' : ''}><span><b>Someone who agreed</b><small>A colleague, family member or staff member who said yes to being in AI videos. Their name goes on the record.</small></span></label>
            ${s.who === 'agreed' ? `<label class="hx-fld"><span class="hx-lab">Their full name</span><input class="hx-in" id="hxAvPer" maxlength="60" value="${esc(s.person || '')}"></label>` : ''}</fieldset>
          <label class="hx-avok"><input type="checkbox" id="hxAvOk"${s.consent ? ' checked' : ''}><span>I confirm this is me, or the person agreed to be shown speaking in AI videos. It is not a public figure and not anyone under 18. Hoola keeps this confirmation with the date.</span></label>
          <p class="hx-avnote">Hoola checks that this is a real photo and that it is big enough. It cannot check who is in it: your confirmation is the record.</p></div></div></div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">You can remove the face any time. Videos already made keep it.</span><button type="button" class="hx-btn" data-a="dlgx">Cancel</button>
        <button type="button" class="hx-btn dark" data-a="avphsave"${!ok || s.busy ? ' disabled' : ''}>${s.busy ? 'Adding…' : 'Add the face'}</button></div>
      <input type="file" id="hxAvPh" accept="image/png,image/jpeg,image/webp" hidden></div>`;
  }
  function avPhFile(f) {
    const s = UI.dlg; if (!s || s.k !== 'avphoto' || !f) return;
    if (s.url) URL.revokeObjectURL(s.url);
    Object.assign(s, {file: f, size: f.size, type: (f.type.split('/')[1] || '').toUpperCase().replace('JPEG', 'JPG'), real: /^image\/(png|jpeg|webp)$/.test(f.type) && f.size <= 15 * 1048576, w: 0, h: 0, big: false, url: URL.createObjectURL(f)});
    if (!s.name) s.name = f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').slice(0, 40);
    if (!s.real) return dlgPaint();
    const im = new Image(); im.onload = () => { s.w = im.naturalWidth; s.h = im.naturalHeight; s.big = Math.min(s.w, s.h) >= 300; dlgPaint(); };
    im.onerror = () => { s.real = false; dlgPaint(); }; im.src = s.url;
  }
  async function avPhSave() {
    const s = UI.dlg; if (!s || s.busy) return;
    const name = ($('#hxAvNm')?.value || s.name || '').trim(), person = ($('#hxAvPer')?.value || s.person || '').trim();
    if (!name) return toast('Give the face a name.');
    if (s.who === 'agreed' && !person) return toast('Write the name of the person who agreed.');
    if (!s.consent) return toast('Tick that this is you, or that the person agreed.', true);
    s.busy = true; dlgPaint();
    try { const up = await upload(s.file); const row = await api('POST', `${S}/avatar`, {file_id: up.file_id, name, consent: true, who: s.who || 'me', person, lang: SET.lang});
      if (s.url) URL.revokeObjectURL(s.url); UI.dlg = null; dlgPaint(); await load(); (UI.av ||= {}).sel = row.id; draw(); toast('Face added.'); }
    catch (er) { s.busy = false; dlgPaint(); toast(er.message, true); }
  }
  // the AI window
  const AIROWS = [['age', 'Age', [['20s', '20s'], ['30s', '30s'], ['40s', '40s'], ['50s', '50s +']]],
    ['look', 'Look', [['warm', 'Warm'], ['formal', 'Formal'], ['casual', 'Casual'], ['expert', 'Doctor or teacher']]],
    ['behind', 'Behind', [['wall', 'Plain wall'], ['shop', 'A shop'], ['office', 'An office'], ['outdoors', 'Outdoors']]]];
  function avAiBody() {
    const s = UI.dlg, q = s.quote, run = s.job && s.status === 'running', items = s.items || [];
    return `<div class="hx-dlg w x" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">A face made by AI</h2>
        <span class="hx-mut hx-sm">A presenter who is no real person. Every video with this face carries the AI mark.</span></div><button type="button" class="hx-ib" data-a="dlgx" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><div class="hx-avph"><div class="hx-avphl">
          <label class="hx-fld"><span class="hx-lab">Describe the presenter</span><textarea class="hx-in hx-ta" id="hxAiD" rows="4" maxlength="400" placeholder="A friendly woman in her thirties, warm smile, simple teal kurta." data-auto="1">${esc(s.describe || '')}</textarea></label>
          ${AIROWS.map(([k, l, os]) => `<div class="hx-fld"><span class="hx-lab">${l}</span><div class="hx-acts">${os.map(([v, t]) => `<button type="button" class="hx-chip s${s[k] === v ? ' on' : ''}" data-a="aiopt" data-k="${k}" data-val="${v}" aria-pressed="${s[k] === v}">${t}</button>`).join('')}</div></div>`).join('')}
          <p class="hx-avwarn">Asking for a real or famous person is refused. The face is made up, so it needs no consent, and it is never passed off as someone real.</p></div>
        <div class="hx-avphr">${items.length ? `<div class="hx-sech"><b>Pick one</b><span class="hx-mut hx-sm">${num(items.length)} made</span></div>
            <div class="hx-aipicks">${items.map(it => `<button type="button" class="hx-aipick${s.pick === it.id ? ' on' : ''}" data-a="aipick" data-id="${esc(it.id)}" aria-pressed="${s.pick === it.id}"><img data-ci="${esc(it.id)}" alt="An AI-made face"><span class="hx-avk ai">AI</span>${s.pick === it.id ? `<span class="hx-aion">${ic('check', 14)}</span>` : ''}</button>`).join('')}</div>
            <label class="hx-fld"><span class="hx-lab">Name the face</span><input class="hx-in" id="hxAiNm" maxlength="40" value="${esc(s.name || '')}" placeholder="Asha (AI)"></label>`
          : run ? `<div class="hx-aiwait"><span class="hx-spin" aria-hidden="true"></span><b>Making ${num(s.count || 4)} faces…</b><span class="hx-mut hx-sm">${esc(s.step || 'Usually under a minute')}</span></div>`
          : `<div class="hx-aiwait idle">${ic('wand', 28)}<b>Your four faces appear here</b><span class="hx-mut hx-sm">${s.error ? esc(s.error) : 'Describe the presenter, then make them.'}</span></div>`}</div></div></div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">${q ? (q.ready ? `4 faces · about ${cr(q.credits)}. Kept in Create › My creations too.` : 'Making faces needs the picture engine on this server.') : 'Checking the price…'}</span>
        <button type="button" class="hx-btn${items.length ? '' : ' dark'}" data-a="aimake"${run || !q?.ready ? ' disabled' : ''}>${items.length ? 'Make 4 more' : `Make 4 faces${q?.ready ? ' · ' + cr(q.credits) : ''}`}</button>
        ${items.length ? `<button type="button" class="hx-btn dark" data-a="aikeep"${!s.pick || s.busy ? ' disabled' : ''}>${s.busy ? 'Keeping…' : 'Keep this face'}</button>` : ''}</div></div>`;
  }
  let aiT = 0;
  async function aiMake() {
    const s = UI.dlg; if (!s || s.k !== 'avai') return;
    s.describe = ($('#hxAiD')?.value || s.describe || '').trim();
    if (!s.describe && !s.age && !s.look) return toast('Describe the presenter in a few words.');
    s.error = ''; s.status = 'running'; s.step = ''; dlgPaint();
    try { const r = await api('POST', `${S}/avatar/ai`, {describe: s.describe, age: s.age, look: s.look, behind: s.behind, count: 4});
      s.job = r.job; s.count = r.count; aiPoll(); }
    catch (er) { s.status = ''; s.error = er.message; dlgPaint(); }
  }
  function aiPoll() {
    clearTimeout(aiT);
    aiT = setTimeout(async () => { const s = UI.dlg; if (!s || s.k !== 'avai' || !s.job) return;
      try { const j = await api('GET', `/api/create/jobs/${q(s.job)}`); s.step = j.step ? `Face ${j.step}` : '';
        if (j.status === 'running') { dlgPaint(); return aiPoll(); }
        s.status = j.status; if (j.status === 'failed') s.error = j.error || 'The faces could not be made. Nothing was kept.';
        s.items = [...(j.items || []).filter(i => i.kind === 'image'), ...(s.items || [])].slice(0, 8);
        if (!s.pick && s.items[0]) s.pick = s.items[0].id; dlgPaint(); }
      catch (er) { s.status = ''; s.error = er.message; dlgPaint(); } }, 2500);
  }
  async function aiKeep() {
    const s = UI.dlg; if (!s?.pick || s.busy) return;
    const name = ($('#hxAiNm')?.value || s.name || '').trim(); if (!name) return toast('Give the face a name.');
    s.busy = true; dlgPaint();
    try { const row = await api('POST', `${S}/avatar/keep`, {item_id: s.pick, name}); UI.dlg = null; dlgPaint(); await load(); (UI.av ||= {}).sel = row.id; draw(); toast('Face kept.'); }
    catch (er) { s.busy = false; dlgPaint(); toast(er.message, true); }
  }
  function avTwinBody() {
    return `<div class="hx-dlg" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><span class="hx-avwi avtwin">${ic('video', 22)}</span>
        <div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">A video twin</h2><span class="hx-ast no"><i></i>Needs an engine on this server</span></div>
        <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close" data-auto="1">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><p>A short video of you, filmed facing the camera, so the face in your videos moves its lips with the words. It needs a face engine that learns from a video, which the owner of this Hoola connects on the server. Nothing is filmed, sent or charged while it is off.</p>
        <div class="hx-svs-list"><div class="hx-svr"><span class="hx-anck ok">✓</span><div><b>Your consent line</b><p class="hx-mut hx-sm">You will read one sentence on camera saying you agree. That recording is the record.</p></div></div>
          <div class="hx-svr"><span class="hx-anck no">!</span><div><b>The video face engine</b><p class="hx-mut hx-sm">Not connected on this server yet.</p></div></div></div>
        <div class="hx-fld"><span class="hx-lab">Meanwhile, these work today</span><div class="hx-acts"><button type="button" class="hx-btn" data-a="avadd">From your photo</button><button type="button" class="hx-btn" data-a="avai">Made by AI</button></div></div></div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">Your photo face can already talk through the face engines in Engines.</span><button type="button" class="hx-btn" data-a="dlgx">Close</button><button type="button" class="hx-btn dark" data-a="aeng">Open Engines</button></div></div>`;
  }
  function avRenBody() {
    const a = face(UI.dlg.id); if (!a) return '';
    return `<div class="hx-dlg" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><h2 class="hx-serif hx-growf" id="hxDlgT">Rename ${esc(a.name)}</h2>
        <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close">${ic('x', 16)}</button></div>
      <div class="hx-dlgb"><label class="hx-fld"><span class="hx-lab">Name</span><input class="hx-in" id="hxAvRn" maxlength="40" value="${esc(a.name)}" data-auto="1"></label></div>
      <div class="hx-dlgf"><span class="hx-grow"></span><button type="button" class="hx-btn" data-a="dlgx">Cancel</button><button type="button" class="hx-btn dark" data-a="avrensave">Save</button></div></div>`;
  }
  async function avTest(id) {
    const a = face(id); if (!a || UI.av?.busy) return;
    UI.av.busy = true; draw();
    try { const r = await api('POST', `${H}/batch`, {scripts: [`Hello, I am ${a.name}. This is how I look in a Hoola video.`], lang: SET.lang === 'auto' ? 'en' : SET.lang, avatar_id: id});
      UI.av.busy = false; await load(); const p = (r.made || [])[0]; toast('Test draft ready. Nothing is made until you press Make.'); return p ? go('studio', p.id) : go('studio'); }
    catch (er) { UI.av.busy = false; draw(); toast(er.message, true); }
  }

  // ---- voices (v0.999.201 VOICES, REDESIGNED: the voice her videos speak in, find one by describing it, a sample in her
  //      language, favourites shared with Hoola Vocal, a voice put into several videos at once)
  const VOWORDS = {man: 'male', men: 'male', male: 'male', boy: 'male', guy: 'male', woman: 'female', women: 'female', lady: 'female', female: 'female', girl: 'female',
    old: 'older', older: 'older', elderly: 'older', senior: 'older', young: 'young', youthful: 'young', teen: 'young', middle: 'middle'};
  const VOSKIP = new Set(['a', 'an', 'the', 'for', 'and', 'with', 'of', 'to', 'in', 'voice', 'voices', 'who', 'that', 'very', 'bit', 'little', 'my', 'some', 'like', 'sounds', 'sounding']);
  const VOSETS = [['narrat', 'story', 'stories', 'audiobook', 'informative', 'knowledgeable', 'documentary', 'clear', 'mature', 'firm', 'even', 'news'],
    ['upbeat', 'excited', 'lively', 'bright', 'energetic', 'ad', 'ads', 'promo', 'youthful', 'social', 'reels'],
    ['friendly', 'casual', 'easy', 'warm', 'conversation', 'support', 'breezy', 'forward', 'chat'],
    ['gravelly', 'breathy', 'playful', 'character', 'games', 'rough', 'husky', 'deep', 'quirky'],
    ['calm', 'soft', 'smooth', 'gentle', 'soothing', 'meditation', 'relaxed', 'mellow']];
  const voAll = () => { const Vv = UI.V || {mine: [], library: []}; return [...(Vv.mine || []).map(v => ({...v, mine: true})), ...(Vv.library || [])]; };
  const voOf = id => voAll().find(v => v.id === id);
  const voHay = v => [v.name, v.tone, v.accent, v.use, v.gender, v.age].join(' ').toLowerCase();
  const voFav = id => (UI.V?.favs || []).includes(id);
  const voUses = id => (D.projects || []).filter(p => p.voice === id);
  const voTint = id => [...String(id || 'x')].reduce((a, c) => a + c.charCodeAt(0), 0) % 5;
  const voGender = v => v.gender === 'male' ? 'man' : v.gender === 'female' ? 'woman' : '';
  const voLine = v => v.mine ? (v.kind === 'designed' ? 'Your voice, designed from words' : v.kind === 'remix' ? 'Your voice, changed from another' : 'Your own voice, kept with your consent')
    : [v.tone, voGender(v), v.accent].filter(Boolean).join(' · ') || 'A ready-made voice';
  const voTier = v => v.mine ? ['mine', 'Your voice'] : v.tier === 'premium' ? ['pr', 'Premium'] : ['st', 'Standard'];
  const voCur = () => SET.voice || UI.V?.default || '';
  function voMatch(v, q) {
    const hay = voHay(v), why = []; let n = 0;
    for (const raw of String(q).toLowerCase().split(/[\s,;.]+/).filter(Boolean)) {
      if (VOSKIP.has(raw)) continue;
      const g = VOWORDS[raw];
      if (g === 'male' || g === 'female') { if (v.gender === g) { n += 2; why.push(g === 'male' ? 'man' : 'woman'); } else if (v.gender) n -= 3; continue; }
      if (g) { if (v.age === g || hay.includes(g)) { n += 2; why.push(g); } continue; }
      const w = raw.replace(/s$/, '');
      if (hay.includes(w)) { n += 3; why.push(raw); continue; }
      const set = VOSETS.find(x => x.some(k => raw.startsWith(k) || k.startsWith(w)));
      if (set && set.some(k => new RegExp(`\\b${k}`).test(hay))) { n += 1; why.push(raw); }
    }
    return {n, why: [...new Set(why)].slice(0, 4).join(', ')};
  }
  function voList() {
    const st = UI.vo || (UI.vo = {k: 'all', q: '', g: '', lang: '', more: 0, sel: ''}), q = (st.q || '').trim();
    let xs = voAll().filter(v => st.k === 'all' || (st.k === 'mine' ? v.mine : st.k === 'fav' ? voFav(v.id) : st.k === 'premium' ? !v.mine && v.tier === 'premium' : !v.mine && v.tier !== 'premium'))
      .filter(v => !st.g || v.gender === st.g);
    let why = {};
    if (q) { const m = xs.map(v => [v, voMatch(v, q)]).filter(([v, r]) => r.n > 0 || v.name.toLowerCase().includes(q.toLowerCase()));
      m.sort((a, b) => b[1].n - a[1].n); xs = m.map(([v]) => v); why = Object.fromEntries(m.map(([v, r]) => [v.id, r.why])); }
    if (!xs.length) return `<div class="hx-empty"><b>No voice matches</b><span>${q ? 'Try other words, like warm, deep, calm, young, woman.' : st.k === 'fav' ? 'Tap the star on a voice to keep it here.' : 'Try another filter.'}</span></div>`;
    const lim = 60 + (st.more || 0) * 120, sel = st.sel || voCur();
    return `<div class="hx-vol">${xs.slice(0, lim).map(v => { const [tc, tl] = voTier(v), on = sel === v.id, pl = UI.voPlay === v.id;
      return `<div class="hx-vor${on ? ' on' : ''}"><button type="button" class="hx-vop${pl ? ' on' : ''}" data-a="voplay" data-id="${esc(v.id)}" aria-label="${pl ? 'Stop' : 'Play'} ${esc(v.name)}">${ic(pl ? 'stop' : 'play', 13)}</button>
        <button type="button" class="hx-vom" data-a="vosel" data-id="${esc(v.id)}" aria-pressed="${on}"><span class="hx-vot t${voTint(v.id)}" aria-hidden="true">${esc(v.name.slice(0, 1).toUpperCase())}</span>
          <span class="hx-ct"><b>${esc(v.name)}${voCur() === v.id ? ' <small class="hx-vous">Your videos</small>' : ''}</b><small>${esc(voLine(v))}${why[v.id] ? ` · matches “${esc(why[v.id])}”` : ''}</small></span></button>
        <span class="hx-vtier ${tc}">${tl}</span>${v.ready ? '' : '<span class="hx-vtier no">Not connected</span>'}
        <button type="button" class="hx-ib hx-vofav${voFav(v.id) ? ' on' : ''}" data-a="vofav" data-id="${esc(v.id)}" aria-pressed="${voFav(v.id)}" aria-label="${voFav(v.id) ? 'Remove from favourites' : 'Add to favourites'}">${ic('star', 17)}</button></div>`; }).join('')}</div>
      ${xs.length > lim ? `<div class="hx-acts hx-vomore"><span class="hx-mut hx-sm hx-num">Showing ${num(lim)} of ${num(xs.length)}</span><button type="button" class="hx-btn" data-a="vomore">Show more voices</button></div>` : ''}`;
  }
  const voWave = (id, n = 28) => { let h = [...String(id || 'x')].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 9973, 7); const bars = [];
    for (let i = 0; i < n; i++) { h = (h * 17 + 7) % 101; bars.push(6 + (h % 22)); } return `<span class="hx-vow" aria-hidden="true">${bars.map(b => `<i style="height:${b}px"></i>`).join('')}</span>`; };
  const voLang = () => UI.vo?.lang || (SET.lang && SET.lang !== 'auto' ? SET.lang : 'en');
  function voPanel(v) {
    if (!v) return '';
    const uses = voUses(v.id), [tc, tl] = voTier(v), pl = UI.voPlay === v.id, line = (UI.V?.sample_lines || {})[voLang()] || (UI.V?.sample_lines || {}).en || '';
    return `<aside class="hx-voside" aria-label="${esc(v.name)}"><div class="hx-vosh t${voTint(v.id)}">
        <div class="hx-vohd"><span class="hx-vot big t${voTint(v.id)}" aria-hidden="true">${esc(v.name.slice(0, 1).toUpperCase())}</span><div class="hx-growf"><h2 class="hx-serif">${esc(v.name)}</h2><span class="hx-sm">${esc(voLine(v))}</span></div></div>
        <div class="hx-voplay"><button type="button" class="hx-vop big${pl ? ' on' : ''}" data-a="voplay" data-id="${esc(v.id)}" aria-label="${pl ? 'Stop' : 'Play'} ${esc(v.name)}">${ic(pl ? 'stop' : 'play', 15)}</button>${voWave(v.id, 26)}
          <button type="button" class="hx-chip s" data-a="volang" aria-haspopup="menu">${esc(langName(voLang()))}${ic('down', 12)}</button></div>
        ${line ? `<p class="hx-voline">“${esc(line)}”</p>` : ''}</div>
      <div class="hx-vosb"><div class="hx-acts hx-votags"><span class="hx-vtier ${tc}">${tl}</span>${voGender(v) ? `<span class="hx-vtag">${esc(voGender(v).replace(/^./, c => c.toUpperCase()))}</span>` : ''}${v.accent ? `<span class="hx-vtag">${esc(v.accent)}</span>` : ''}<span class="hx-vtag">${v.any || v.mine ? 'Speaks every language' : esc(`${(v.langs || []).length} language${(v.langs || []).length === 1 ? '' : 's'}`)}</span></div>
        <span class="hx-mut hx-sm">${uses.length ? `In ${num(uses.length)} of your video${uses.length === 1 ? '' : 's'}` : 'Not in a video yet'}</span>
        ${v.ready ? '' : '<p class="hx-why">This voice is not connected on this server, so it cannot speak yet.</p>'}
        <button type="button" class="hx-btn dark l" data-a="vouse" data-id="${esc(v.id)}"${voCur() === v.id && SET.voice ? ' aria-pressed="true"' : ''}${v.ready ? '' : ' disabled'}>${voCur() === v.id && SET.voice ? `${ic('check', 14)}Your videos use this voice` : 'Use for my videos'}</button>
        <div class="hx-acts"><button type="button" class="hx-btn hx-grow" data-a="voput" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}>Put in a video</button><button type="button" class="hx-btn hx-grow" data-a="vovocal" data-id="${esc(v.id)}">Open in Vocal</button></div>
        <span class="hx-mut hx-sm">A sample is made once per voice and language, then it is free to hear again. The first one in a new language uses a few credits.</span></div></aside>`;
  }
  function voPage() {
    if (!UI.V) return `<div class="hx-doc"><p class="hx-mut">Loading voices…</p></div>`;
    const st = UI.vo || (UI.vo = {k: 'all', q: '', g: '', lang: '', more: 0, sel: ''}), all = voAll(), cur = voOf(voCur()), sel = voOf(st.sel) || cur || all[0];
    const n = k => all.filter(v => k === 'all' || (k === 'mine' ? v.mine : k === 'fav' ? voFav(v.id) : k === 'premium' ? !v.mine && v.tier === 'premium' : !v.mine && v.tier !== 'premium')).length;
    const pl = cur && UI.voPlay === cur.id;
    return `<div class="hx-doc hx-vopage"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Voices</h2>
          <p class="hx-mut">The voice that speaks your videos. The same voices as Hoola Vocal: 140 languages, premium voices and your own. Every voice speaks any language.</p></div>
        <button type="button" class="hx-btn" data-a="aopen" data-id="ownvoice">${ic('mic', 14)}Make your own voice</button></div>
      <section class="hx-vocur" aria-label="The voice for your videos">${cur ? `<button type="button" class="hx-vop big inv${pl ? ' on' : ''}" data-a="voplay" data-id="${esc(cur.id)}" aria-label="${pl ? 'Stop' : 'Play'} ${esc(cur.name)}">${ic(pl ? 'stop' : 'play', 16)}</button>` : ''}
        <div class="hx-growf"><span class="hx-vok">YOUR VIDEOS SPEAK IN</span><b class="hx-serif">${esc(cur ? cur.name : 'Hoola picks')}</b><span class="hx-sm">${cur ? `${esc(voLine(cur))} · ${voTier(cur)[1]}${SET.voice ? '' : ' · Hoola picks it until you choose'}` : 'A ready-made voice that fits each video.'}</span></div>
        ${cur ? voWave(cur.id, 30) : ''}<button type="button" class="hx-btn" data-a="pick" data-k="voice" aria-haspopup="menu">Change</button></section>
      <div class="hx-vobody"><div class="hx-vomain">
          <label class="hx-vodesc">${ic('wand', 18)}<span class="hx-sr">Describe a voice</span><input type="search" id="hxVoq" placeholder="Describe a voice: warm woman, calm older man, bright and young…" value="${esc(st.q || '')}"><small class="hx-mut">${st.q ? 'Best matches first' : ''}</small></label>
          <div class="hx-avbar">${[['all', 'All'], ['mine', 'Your voices'], ['fav', 'Favourites'], ['premium', 'Premium'], ['standard', 'Standard']].map(([k, l]) => `<button type="button" class="hx-chip${st.k === k ? ' on' : ''}" data-a="vokind" data-val="${k}">${l} <span class="hx-num">${num(n(k))}</span></button>`).join('')}
            <span class="hx-grow"></span><button type="button" class="hx-chip" data-a="vogen" aria-haspopup="menu">${st.g === 'male' ? 'Men' : st.g === 'female' ? 'Women' : 'Any gender'}${ic('down', 12)}</button>
            <button type="button" class="hx-chip" data-a="volang" aria-haspopup="menu">Samples in ${esc(langName(voLang()))}${ic('down', 12)}</button></div>
          <div id="hxVoList">${voList()}</div></div>${voPanel(sel)}</div></div>`;
  }
  async function voPlay(id) {
    if (UI.voPlay === id) { UI.audio?.pause(); UI.voPlay = ''; return voRepaint(); }
    UI.audio?.pause(); UI.voPlay = id; voRepaint();
    try { const r = await api('GET', `/api/vocal/voice/preview?id=${q(id)}&lang=${q(voLang())}`, undefined, {raw: true});
      if (!r.ok) { let m = 'The sample could not be made.'; try { m = (await r.json()).detail || m; } catch { /* keep */ } throw new Error(m); }
      if (UI.voPlay !== id) return;
      UI.audio = new Audio(URL.createObjectURL(await r.blob())); UI.audio.onended = () => { if (UI.voPlay === id) { UI.voPlay = ''; voRepaint(); } };
      UI.audio.play().catch(() => {}); }
    catch (er) { if (UI.voPlay === id) { UI.voPlay = ''; voRepaint(); } toast(er.message, true); }
  }
  function voRepaint() { if (PAGE !== 'voices') return; const y = $('#hxView')?.scrollTop; const qf = document.activeElement?.id === 'hxVoq'; draw(); if (y != null && $('#hxView')) $('#hxView').scrollTop = y;
    if (qf) { const i = $('#hxVoq'); if (i) { i.focus(); i.setSelectionRange(i.value.length, i.value.length); } } }
  async function voFavToggle(id) {
    const on = !voFav(id);
    try { const r = await api('PUT', '/api/vocal/voices/fav', {id, on}); UI.V.favs = r.favs || []; voRepaint();
      toast(on ? `${voOf(id)?.name || 'The voice'} is in your favourites, here and in Hoola Vocal.` : `${voOf(id)?.name || 'The voice'} is out of your favourites.`); }
    catch (er) { toast(er.message, true); }
  }
  function voPutBody() {
    const s = UI.dlg, v = voOf(s.id); if (!v) return '';
    const ps = (D.projects || []).filter(p => (p.scenes || []).length || p.title);
    return `<div class="hx-dlg" role="dialog" aria-modal="true" aria-labelledby="hxDlgT"><div class="hx-dlgh"><span class="hx-vot t${voTint(v.id)}" aria-hidden="true">${esc(v.name.slice(0, 1).toUpperCase())}</span>
        <div class="hx-growf"><h2 class="hx-serif" id="hxDlgT">Put ${esc(v.name)} in a video</h2><span class="hx-mut hx-sm">Only the voice changes. The words, faces and scenes stay as they are.</span></div>
        <button type="button" class="hx-ib" data-a="dlgx" aria-label="Close" data-auto="1">${ic('x', 16)}</button></div>
      <div class="hx-dlgb">${ps.length ? `<div class="hx-vopick">${ps.slice(0, 50).map(p => { const on = s.ids.includes(p.id), mk = p.status === 'making';
          return `<label class="hx-vopr${on ? ' on' : ''}${mk ? ' off' : ''}"><input type="checkbox" data-vop="${esc(p.id)}"${on ? ' checked' : ''}${mk ? ' disabled' : ''}>${libThumb(p)}
            <span class="hx-ct"><b>${esc(p.title)}</b><small>${num((p.scenes || []).length)} scene${(p.scenes || []).length === 1 ? '' : 's'} · now ${esc(p.voice ? (voOf(p.voice)?.name || 'another voice') : 'Hoola picks')}</small></span>${chip(p)}</label>`; }).join('')}</div>
          <p class="hx-mut hx-sm">A video that is already made keeps its old voice until you make it again, priced first in the Studio.</p>`
        : `<p class="hx-mut">You have no videos yet. Choose “Use for my videos” and every new video starts with this voice.</p>`}</div>
      <div class="hx-dlgf"><span class="hx-mut hx-sm hx-grow">${num(s.ids.length)} video${s.ids.length === 1 ? '' : 's'} chosen · free</span><button type="button" class="hx-btn" data-a="dlgx">Cancel</button>
        <button type="button" class="hx-btn dark" data-a="voputgo"${!s.ids.length || s.busy ? ' disabled' : ''}>${s.busy ? 'Saving…' : `Use in ${num(s.ids.length)} video${s.ids.length === 1 ? '' : 's'}`}</button></div></div>`;
  }
  async function voPutGo() {
    const s = UI.dlg; if (!s || !s.ids.length || s.busy) return;
    s.busy = true; dlgPaint();
    try { const r = await api('POST', `${X}/voices/apply`, {voice: s.id, ids: s.ids}); UI.dlg = null; dlgPaint(); await load(); draw();
      toast(`${voOf(s.id)?.name || 'The voice'} is in ${num(r.done.length)} video${r.done.length === 1 ? '' : 's'}.${r.skipped.length ? ` ${num(r.skipped.length)} left out: ${r.skipped[0].why}` : ''}`, !!r.skipped.length); }
    catch (er) { s.busy = false; dlgPaint(); toast(er.message, true); }
  }

  // ------------------------------------------------------------------ pages ---
  const V = {
    chat() {
      if (fresh()) return home();
      return `<div class="hx-split hx-ixchat"><div class="hx-chat"><div class="hx-log" id="hxLog"><div id="hxThread">${thread()}</div></div>${composer(false)}</div>
        <aside class="hx-stage hx-pv" id="hxPv" aria-label="Preview">${pvPane()}</aside></div>`;
    },
    studio() { return ARG ? edPage() : libPage(); },
    templates() { const t = ARG && tplOf(ARG); return t ? tplUse(t) : tplLib(); },
    apps() { return ARG && appOf(ARG) ? appRun(ARG) : appsLib(); },
    avatars() { return avPage(); },
    voices() { return voPage(); },
    live() {
      const ag = D.live?.agents || [], cur = ag.find(a => a.id === UI.live);
      if (!cur && UI.live !== 'new') {
        return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Live agents</h2><p class="hx-mut">An assistant that listens and answers from your facts, in your voice, with a face you choose.</p></div>
          <button type="button" class="hx-btn dark" data-a="livenew">${ic('plus', 14)}New agent</button></div>
          ${ag.length ? `<div class="hx-grid3">${ag.map(a => `<button type="button" class="hx-card hx-agent" data-a="liveopen" data-id="${esc(a.id)}"><b>${esc(a.name)}</b>
            <small class="hx-mut">${esc(langName(a.lang))} · ${esc(engine(a.face)?.label || 'Voice only')}${a.published ? ' · on your website' : ''}</small>
            <span class="hx-hint">${num(Math.round((a.used_today_s || 0) / 60))} of ${num(a.minutes_day)} min today</span></button>`).join('')}</div>`
            : `<div class="hx-empty"><b>No agents yet</b><span>Write what your business knows; the agent answers only from that.</span></div>`}</div>`;
      }
      const a = cur || {name: '', knows: '', opening: '', lang: SET.lang || 'hi', voice: SET.voice || '', face: 'voice_only', face_ref: '', minutes_day: 30};
      const faces = D.live?.faces || [], fe = faces.find(f => f.id === a.face);
      const needRef = ['simli', 'anam', 'liveavatar', 'tavus'].includes(a.face);
      return `<div class="hx-split"><section class="hx-panel wide" aria-label="Build the agent"><form id="hxLiveF" class="hx-form tight">
          <label class="hx-fld"><span class="hx-lab">Name</span><input class="hx-in" name="name" maxlength="40" value="${esc(a.name)}" placeholder="Shop helper"></label>
          <label class="hx-fld"><span class="hx-lab">What it knows</span><textarea class="hx-in hx-serifp" name="knows" rows="6" placeholder="Open 9 am to 9 pm. Kaju katli Rs 1,100 a kg. Home delivery above Rs 500.">${esc(a.knows)}</textarea>
            <span class="hx-hint">It answers only from these words. A number you did not write here is never said.</span></label>
          <label class="hx-fld"><span class="hx-lab">First words (optional)</span><input class="hx-in" name="opening" maxlength="160" value="${esc(a.opening || '')}"></label>
          <div class="hx-row2"><div class="hx-fld"><span class="hx-lab">Language</span><button type="button" class="hx-dd" data-a="lpick" data-k="lang"><span>${esc(langName(a.lang))}</span>${ic('down', 14)}</button><input type="hidden" name="lang" value="${esc(a.lang)}"></div>
            <div class="hx-fld"><span class="hx-lab">Voice</span><button type="button" class="hx-dd" data-a="lpick" data-k="voice"><span>${esc(voiceName(a.voice))}</span>${ic('down', 14)}</button><input type="hidden" name="voice" value="${esc(a.voice || '')}"></div>
            <label class="hx-fld"><span class="hx-lab">Minutes a day</span><input class="hx-in" name="minutes_day" type="number" min="1" max="600" value="${esc(a.minutes_day || 30)}"></label></div>
          <fieldset class="hx-fs"><legend class="hx-lab">Face</legend><div class="hx-grid3 tight">${faces.map(f => `<label class="hx-opt${f.id === a.face ? ' on' : ''}${f.ready ? '' : ' off'}"><input type="radio" name="face" value="${esc(f.id)}"${f.id === a.face ? ' checked' : ''}${f.ready ? '' : ' disabled'}>
            <span class="hx-ct"><b>${esc(f.label)}</b><small>${esc(f.ready ? f.price : scrub(f.status))}</small></span></label>`).join('')}</div></fieldset>
          ${needRef ? `<label class="hx-fld"><span class="hx-lab">${esc(fe?.label || '')} face id</span><input class="hx-in" name="face_ref" maxlength="80" value="${esc(a.face_ref || '')}" placeholder="Made in ${esc(fe?.label || 'the engine')}'s own dashboard"></label>` : ''}
          <input type="hidden" name="id" value="${esc(cur?.id || '')}">
          <div class="hx-acts"><button type="button" class="hx-btn dark" data-a="livesave">Save</button><button type="button" class="hx-btn" data-a="liveback">All agents</button>
          ${cur ? `<span class="hx-grow"></span><button type="button" class="hx-btn danger" data-a="livedel" data-id="${esc(cur.id)}">Remove</button>` : ''}</div></form></section>
        <aside class="hx-stage hx-side2" aria-label="Try it"><div class="hx-stageb"><b class="hx-t">Try it</b>
          ${cur ? `<div class="hx-tryface" id="hxFace">${cur.avatar_id ? avImg(face(cur.avatar_id), 'xl') : `<span class="hx-mark l">${markSvg()}</span>`}<span class="hx-livebadge">Live · ${esc(engine(cur.face)?.label || 'Voice only')}</span></div>
            <div class="hx-trylog" id="hxTry">${UI.liveOut.map(o => `<div class="hx-${o.me ? 'me' : 'ho'}">${esc(o.t)}</div>`).join('')}</div>
            <form class="hx-tryf" data-a="noop" onsubmit="return false"><input class="hx-in" id="hxTryIn" placeholder="Ask it something" maxlength="400"><button type="button" class="hx-btn dark" data-a="liveask">Ask</button></form>
            ${cur.face !== 'voice_only' ? `<button type="button" class="hx-btn" data-a="livesess">Start the face</button>` : ''}
            <div class="hx-card"><b class="hx-sm">On your website</b>${cur.published ? `<p class="hx-hint">Published (pass ending ${esc(cur.pass_last4)}) on ${esc((cur.sites || []).join(', '))}.</p>
              ${UI.pub && UI.pub.id === cur.id ? `<code class="hx-code">${esc(UI.pub.embed)}</code><p class="hx-hint">Copy this line now; the pass is shown once.</p>` : ''}
              <button type="button" class="hx-btn s danger" data-a="liveunpub" data-id="${esc(cur.id)}">Take it off my website</button>`
              : `<input class="hx-in" id="hxSites" placeholder="Your website address, e.g. myshop.in"><button type="button" class="hx-btn s" data-a="livepub" data-id="${esc(cur.id)}">Put it on my website</button>`}
              <p class="hx-hint">Each visitor gets a short pass; your keys never reach the page. A minute cap a day keeps the bill safe.</p></div>`
            : '<p class="hx-mut">Save the agent first, then talk to it here.</p>'}</div></aside></div>`;
    },
    projects() {
      const tabs = ['Videos', 'Batch', 'Many names', 'Trash'], t = UI.ptab;
      const ps = D.projects || [];
      let body = '';
      if (t === 'Videos') body = ps.length ? `<div class="hx-tablew hx-card"><table class="hx-table"><thead><tr><th>Video</th><th>Status</th><th></th></tr></thead><tbody>${ps.map(p => `<tr><td><button type="button" class="hx-lnk" data-a="openp" data-id="${esc(p.id)}">${esc(p.title)}</button><br><small class="hx-mut">${esc(langName(p.lang))} · ${esc(ago(p.updated))}</small></td><td>${chip(p)}</td>
          <td class="r"><button type="button" class="hx-btn s" data-a="dup" data-id="${esc(p.id)}">Duplicate</button> <button type="button" class="hx-btn s" data-a="tplsave" data-id="${esc(p.id)}">Save as template</button> <button type="button" class="hx-ib s" data-a="trash" data-id="${esc(p.id)}" aria-label="Move to trash">${ic('trash', 15)}</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="hx-mut">No videos yet.</p>';
      if (t === 'Batch') body = `<div class="hx-card hx-form tight"><label class="hx-fld"><span class="hx-lab">One script per block, an empty line between them</span><textarea class="hx-in" id="hxBatch" rows="8"></textarea></label>
        <button type="button" class="hx-btn dark" data-a="batch">Make the drafts</button><p class="hx-hint">Each becomes a draft; nothing is made until you tap Make on it.</p></div>`;
      if (t === 'Many names') body = `<div class="hx-card hx-form tight"><div class="hx-fld"><span class="hx-lab">The video</span><button type="button" class="hx-dd" data-a="pnpick"><span id="hxPnName">${esc((ps.find(p => p.id === UI.pn) || {}).title || 'Choose a video with {name} in it')}</span>${ic('down', 14)}</button></div>
        <label class="hx-fld"><span class="hx-lab">Names, one a line</span><textarea class="hx-in" id="hxNames" rows="6"></textarea></label><button type="button" class="hx-btn dark" data-a="names">Make a draft for each name</button></div>`;
      if (t === 'Trash') body = (D.trash || []).length ? `<div class="hx-card hx-list">${D.trash.map(p => `<div class="hx-vrow"><span class="hx-ct"><b>${esc(p.title)}</b><small>Removed ${esc(ago(p.trashed))}</small></span><button type="button" class="hx-btn s" data-a="restore" data-id="${esc(p.id)}">Restore</button></div>`).join('')}</div>
        <button type="button" class="hx-btn danger" data-a="emptytrash">Empty the trash</button>` : '<p class="hx-mut">The trash is empty. Removed videos stay here for 30 days.</p>';
      return `<div class="hx-doc"><h2 class="hx-serif">Projects</h2><div class="hx-tabs" role="tablist">${tabs.map(x => `<button type="button" role="tab" aria-selected="${x === t}" data-a="ptab" data-val="${x}">${x}</button>`).join('')}</div>${body}</div>`;
    },
    brand() {
      const b = D.brand || {};
      return `<div class="hx-doc"><h2 class="hx-serif">Brand</h2><p class="hx-mut">Drawn into every video: your name, your colour, your closing line.</p>
        <form class="hx-card hx-form tight" id="hxBrandF"><label class="hx-fld"><span class="hx-lab">Business name</span><input class="hx-in" name="name" maxlength="40" value="${esc(b.name || '')}"></label>
          <label class="hx-fld"><span class="hx-lab">Colour</span><input class="hx-in" name="color" type="color" value="${esc(/^#[0-9a-f]{6}$/i.test(b.color || '') ? b.color : '#5B45E0')}"></label>
          <label class="hx-fld"><span class="hx-lab">Closing line</span><input class="hx-in" name="closing" maxlength="80" value="${esc(b.closing || '')}"></label>
          <button type="button" class="hx-btn dark" data-a="brandsave">Save</button></form>
        <b class="hx-t">Words to keep</b><p class="hx-mut hx-sm">Names and words a translation must never change.</p>
        <div class="hx-card hx-list">${(D.glossary || []).map(g => `<div class="hx-vrow"><span class="hx-ct"><b>${esc(g.term)}</b><small>${g.mode === 'keep' ? 'Kept as it is' : 'Becomes ' + esc(g.to)}</small></span><button type="button" class="hx-ib s" data-a="glodel" data-id="${esc(g.id)}" aria-label="Remove">${ic('trash', 15)}</button></div>`).join('') || '<p class="hx-mut hx-sm">None yet.</p>'}
          <div class="hx-filerow"><input class="hx-in" id="hxGlo" placeholder="A word to keep" maxlength="60"><button type="button" class="hx-btn s" data-a="gloadd">Add</button></div></div></div>`;
    },
    engines() {
      const E = D.engines || {engines: [], notes: {}}, rows = E.engines.filter(e => e.job === UI.etab);
      const bars = n => `<span class="hx-q" aria-label="Quality ${n} of 5">${[0, 1, 2, 3, 4].map(i => `<i class="${i < n ? 'on' : ''}"></i>`).join('')}</span>`;
      const br = UI.broll, shots = D.live?.broll || [];
      return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Engines</h2><p class="hx-mut">Choose who draws the face. The brain and the voice stay Hoola's.</p></div></div>
        <div class="hx-tabs" role="tablist">${[['video', 'Videos'], ['live', 'Live agents'], ['broll', 'B-roll shots']].map(([k, n]) => `<button type="button" role="tab" aria-selected="${UI.etab === k}" data-a="etab" data-val="${k}">${n}</button>`).join('')}</div>
        <p class="hx-note">${esc(E.notes?.[UI.etab] || '')}</p>
        <div class="hx-tablew hx-card"><table class="hx-table"><thead><tr><th>Engine</th><th>Quality</th><th>Languages</th><th>Cost</th><th>Status</th><th></th></tr></thead><tbody>
        ${rows.map(e => `<tr><td><b>${esc(e.label)}</b><br><small class="hx-mut">${esc(e.what)}</small></td><td>${bars(e.quality)}</td><td>${esc(e.langs)}</td><td class="hx-num">${esc(e.price)}</td>
          <td><span class="hx-st ${e.ready ? 'ok' : ''}">${esc(scrub(e.status))}</span></td>
          <td class="r">${e.default ? '<span class="hx-chip s static on">Default</span>' : `<button type="button" class="hx-btn s" data-a="edef" data-id="${esc(e.id)}"${e.ready ? '' : ' disabled'}>Make default</button>`}</td></tr>`).join('')}</tbody></table></div>
        ${UI.etab === 'broll' ? `<div class="hx-card hx-form tight"><b class="hx-t">Make a B-roll shot</b>
          <label class="hx-fld"><span class="hx-lab">What is seen (no people)</span><textarea class="hx-in" id="hxBr" rows="3" placeholder="Slow pan over a sweet shop counter with trays of kaju katli, warm evening light">${esc(br.prompt)}</textarea></label>
          <div class="hx-row2"><div class="hx-fld"><span class="hx-lab">Length</span><div class="hx-seg" role="radiogroup">${[4, 6, 8].map(n => `<button type="button" role="radio" aria-checked="${br.seconds === n}" data-a="brs" data-val="${n}">${n} s</button>`).join('')}</div></div>
            <div class="hx-fld"><span class="hx-lab">Shape</span><div class="hx-seg" role="radiogroup">${['16:9', '9:16'].map(n => `<button type="button" role="radio" aria-checked="${br.aspect === n}" data-a="bra" data-val="${n}">${n}</button>`).join('')}</div></div></div>
          <div class="hx-acts"><span class="hx-price hx-num">${esc(br.q?.line || '')}</span><span class="hx-grow"></span><button type="button" class="hx-btn dark" data-a="brmake">Make the shot</button></div></div>
          ${shots.length ? `<div class="hx-grid3">${shots.map(s => `<div class="hx-card">${s.status === 'ready' ? `<video class="hx-player" controls playsinline preload="metadata" data-broll="${esc(s.id)}"></video>` : `<span class="hx-st ${s.status === 'failed' ? 'bad' : 'work'}">${s.status === 'failed' ? 'Could not make it' : 'Making it'}</span>`}
            <p class="hx-hint">${esc(s.prompt)}</p>${s.error ? `<p class="hx-why">${esc(scrub(s.error))}</p>` : ''}</div>`).join('')}</div>` : ''}` : ''}</div>`;
    },
    developers() {
      const A = D.apps || {keys: [], hooks: [], doors: []};
      return `<div class="hx-doc"><h2 class="hx-serif">Developers</h2><p class="hx-mut">Let your own programs make videos with your credits. Keys are shown once.</p>
        <b class="hx-t">App keys</b>${UI.newKey ? `<div class="hx-note warn"><code class="hx-code">${esc(UI.newKey.key)}</code><br>${esc(UI.newKey.note)}</div>` : ''}
        <div class="hx-card hx-list">${A.keys.map(k => `<div class="hx-vrow"><span class="hx-ct"><b>${esc(k.name)}</b><small>…${esc(k.last4)} · ${num(k.calls)} calls${k.used_at ? ' · used ' + esc(ago(k.used_at)) : ''}</small></span><button type="button" class="hx-btn s danger" data-a="keydel" data-id="${esc(k.id)}">Remove</button></div>`).join('') || '<p class="hx-mut hx-sm">No keys yet.</p>'}
          <div class="hx-filerow"><input class="hx-in" id="hxKeyName" placeholder="My app" maxlength="40"><button type="button" class="hx-btn s dark" data-a="keynew">Make a key</button></div></div>
        <b class="hx-t">Webhooks</b>${UI.newHook ? `<div class="hx-note warn"><code class="hx-code">${esc(UI.newHook.secret)}</code><br>${esc(UI.newHook.note)}</div>` : ''}
        <div class="hx-card hx-list">${A.hooks.map(h => `<div class="hx-vrow"><span class="hx-ct"><b>${esc(h.url)}</b><small>${esc((h.events || []).join(', '))}${h.last_status ? ' · last answer ' + esc(h.last_status) : ''}</small></span>
            <button type="button" class="hx-btn s" data-a="hooktest" data-id="${esc(h.id)}">Send a test</button><button type="button" class="hx-btn s danger" data-a="hookdel" data-id="${esc(h.id)}">Remove</button></div>`).join('') || '<p class="hx-mut hx-sm">No webhooks yet.</p>'}
          <div class="hx-filerow"><input class="hx-in" id="hxHookUrl" placeholder="https://your-server.com/hoola" maxlength="400"><button type="button" class="hx-btn s dark" data-a="hooknew">Add</button></div></div>
        <b class="hx-t">Doors</b><div class="hx-tablew hx-card"><table class="hx-table"><tbody>${(A.doors || []).map(d => `<tr><td class="hx-num"><b>${esc(d.method)}</b></td><td><code>${esc(d.path)}</code></td><td>${esc(d.does)}</td></tr>`).join('')}</tbody></table></div>
        <p class="hx-hint">${esc(A.signature || '')}</p></div>`;
    },
    settings() {
      const st = D.status || {}, u = D.usage || {};
      return `<div class="hx-doc"><h2 class="hx-serif">Settings</h2>
        <div class="hx-card hx-form tight"><b class="hx-t">For new videos</b>
          <div class="hx-row2"><div class="hx-fld"><span class="hx-lab">Language</span><button type="button" class="hx-dd" data-a="pick" data-k="lang"><span>${esc(langName(SET.lang))}</span>${ic('down', 14)}</button></div>
          <div class="hx-fld"><span class="hx-lab">Voice</span><button type="button" class="hx-dd" data-a="pick" data-k="voice"><span>${esc(voiceName(SET.voice))}</span>${ic('down', 14)}</button></div>
          <div class="hx-fld"><span class="hx-lab">Shape</span><button type="button" class="hx-dd" data-a="pick" data-k="shape"><span>${esc(SHAPE[SET.shape])}</span>${ic('down', 14)}</button></div></div></div>
        <div class="hx-card"><b class="hx-t">This month</b><dl class="hx-dl"><dt>Videos</dt><dd class="hx-num">${num(u.videos)}</dd><dt>Minutes</dt><dd class="hx-num">${num(u.minutes)}</dd><dt>Kept</dt><dd class="hx-num">${num(u.stored)} of ${num(u.kept_max)}</dd></dl></div>
        <div class="hx-card"><b class="hx-t">On this server</b><dl class="hx-dl"><dt>Drawing videos</dt><dd>${st.draw ? 'Ready' : 'Not installed'}</dd><dt>Hoola voices</dt><dd>${st.vocal ? 'Ready' : 'Not connected'}</dd>
          <dt>GPU lab</dt><dd>${st.lab ? 'Connected' : 'Off'}</dd></dl></div></div>`;
    },
  };
  const ENTER = {
    chat() { (C.conv ? Promise.resolve() : openChat()).then(chatLoad).then(() => { if (PAGE !== 'chat') return; if ($('.hx-hero') && !fresh()) draw(); else paintChat(); chatPoll(); }); estimate(); },
    voices() { Promise.all([voicesLoad(), langsLoad()]).then(() => { if (PAGE === 'voices') draw(); }); },
    apps() { appsLoad().then(() => { if (PAGE !== 'apps') return; draw(); if (ARG === 'broll') { abQuote(); abWatch(); } if (ARG === 'names' || ARG === 'batch') arEstimate(ARG === 'names' ? lenOf((D.projects || []).find(x => x.id === arState().vid) || {}) : 30); }); },
    templates() { const t = ARG && tplOf(ARG); if (!t) return; const u = tuState(t); tuEstimate(); if (u.sample) { u.scene = 0; tuPlay(); } },
    studio() { if (ARG) { const p = cur(); if (!p) return; if (p.status === 'making') watchJob(ARG); studioQuote(); if (UI.tool === 'Engine') edCompare(); }
      else (D.projects || []).filter(p => p.status === 'making').forEach(p => watchJob(p.id)); },
    engines() { if (UI.etab === 'broll') brQuote(); },
  };
  const AFTER = {};

  // ------------------------------------------------------------------ studio edits ---
  const cur = () => (D.projects || []).find(x => x.id === ARG);
  async function save(body, redraw = true) {
    try { const p = await api('PUT', `${S}/project?id=${q(ARG)}`, body); const i = D.projects.findIndex(x => x.id === ARG); if (i >= 0) D.projects[i] = p; if (redraw) { draw(); } studioQuote(); if (UI.tool === 'Engine') edCompare(); }
    catch (e) { toast(e.message, true); }
  }
  let saveT = 0;
  function saveSoon(body) { clearTimeout(saveT); saveT = setTimeout(() => save(body, false), 600); }
  async function studioQuote() {
    if (PAGE !== 'studio' || !ARG) return; const id = ARG;
    let r; try { r = await api('GET', `${X}/quote?id=${q(id)}`); }
    catch (e) { const el = $('#hxEdPrice'); if (el) el.innerHTML = `<p class="hx-why">${esc(e.message)}</p>`; return; }
    if (PAGE !== 'studio' || ARG !== id) return;
    UI.q = {id, ...r}; const p = cur(); if (!p) return;
    const box = $('.hx-edmk'); if (box) box.outerHTML = edMakeBox(p);
    const h = $('.hx-edhmk'); if (h) h.innerHTML = makeBtn(p);
  }
  async function brQuote() { try { UI.broll.q = await api('GET', `${X}/broll/quote?seconds=${UI.broll.seconds}`); if (PAGE === 'engines') draw(); } catch { /* shown on make */ } }

  // ------------------------------------------------------------------ menus ---
  function menu(el, items, opts) { if (window.HoolaMenu) HoolaMenu.open(el, items, {align: 'start', ...(opts || {})}); }
  function pickMenu(el, k, onPick, item) {
    const cbs = v => () => onPick(v);
    if (k === 'len') return menu(el, [{header: kindNow() === 'reel' ? 'Vertical 9:16, for social media' : 'Wide 16:9 (a reel is vertical)'}, ...LENS.map(n => ({label: n < 60 ? `${n} seconds` : `${n / 60 === 1 ? '1 minute' : '1.5 minutes'}`, checked: (SET.len || 30) === n, run: () => setPick('len', n)}))]);
    if (k === 'face') return menu(el, [{label: 'No face', checked: !SET.face, run: cbs('')}, ...(D.avatars || []).map(a => ({label: a.name, sub: 'Consent on record', checked: SET.face === a.id, run: cbs(a.id)})),
      {sep: true}, {label: 'Add a face', icon: 'plus', run: () => go('avatars')}]);
    if (k === 'voice') { const Vv = UI.V || {mine: [], library: []};
      return menu(el, [{search: 'Find a voice', empty: 'No voice matches'}, {label: 'Hoola picks', checked: !SET.voice, run: cbs('')}, ...(Vv.mine.length ? [{header: 'Your voices'}] : []),
        ...Vv.mine.map(v => ({label: v.name, sub: 'Your own', disabled: !v.ready, run: cbs(v.id)})), {header: 'Ready-made'},
        ...Vv.library.slice(0, 120).map(v => ({label: v.name, sub: [v.gender, v.tier === 'premium' ? 'Premium' : ''].filter(Boolean).join(' · '), disabled: !v.ready, run: cbs(v.id)}))], {width: 300}); }
    if (k === 'engine') return menu(el, (D.engines?.engines || []).filter(e => e.job === 'video').map(e => ({label: e.label, sub: e.ready ? e.price : scrub(e.status), disabled: !e.ready, checked: defEngine() === e.id, run: cbs(e.id)})), {width: 300});
    if (k === 'lang') return menu(el, [{search: 'Find a language', empty: 'No language matches'}, ...(item ? [] : [{label: 'Auto', sub: 'Matches the language you write in', checked: !SET.lang || SET.lang === 'auto', run: cbs('auto')}]), ...(UI.L || []).map(l => ({label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name, sub: l.region, run: cbs(l.code)}))], {width: 280});
    if (k === 'shape') return menu(el, Object.entries(SHAPE).map(([s, n]) => ({label: n, checked: SET.shape === s, run: cbs(s)})));
  }
  function setPick(k, v) { SET[k] = v; store.set('hx.set', SET); if (PAGE === 'chat') refreshBar(); else draw(); }

  // ------------------------------------------------------------------ clicks ---
  async function onClick(e) {
    const b = e.target.closest('[data-a]'); if (!b || !ROOT.contains(b)) return;
    const a = b.dataset.a, id = b.dataset.id;
    switch (a) {
      case 'go': return go(b.dataset.p);
      case 'back': leave(); return back?.();
      case 'slim': UI.slim = !UI.slim; store.set('hx.slim', UI.slim); return side();
      case 'navon': UI.nav = true; return side();
      case 'navoff': UI.nav = false; return side();
      case 'newchat': return newVideo();
      case 'openchat': clearTimeout(C.t); C.gen++; C.conv = id; C.rows = []; C.items = []; UI.pv.id = ''; pvStop(); await chatLoad(); return go('chat');
      case 'credits': leave(); location.assign('/console/?v=credits'); return;
      case 'kind': if (b.dataset.val === 'translate') return toDubbing();
        SET.kind = b.dataset.val; SET.shape = shapeOf(SET.kind); if (SET.kind === 'reel' && (SET.len || 30) > 30) SET.len = 15; store.set('hx.set', SET); estimate(); return draw();
      case 'ideag': UI.ideaG = b.dataset.val; return draw();
      case 'from': { const v = b.dataset.val;
        if (v === 'doc') return pickFiles('.pdf,.doc,.docx,.txt,.md,.rtf,.odt', 'explainer', 'Make an explainer video from this document.');
        if (v === 'slides') return pickFiles('.pptx,.ppt,.pdf,.key,.odp', 'lesson', 'Turn these slides into a narrated lesson.');
        if (v === 'web') return fromWeb();
        return toDubbing(); }
      case 'attach': return menu(b, [{label: 'A file', sub: 'PDF, Word, slides, a photo, notes', icon: 'plus', run: () => pickFiles('', '', '')},
        {label: 'A web page', sub: 'Hoola reads the page you give', icon: 'globe', run: fromWeb}]);
      case 'unfile': { C.files.splice(+b.dataset.n, 1); const t = $('#hxTray'); if (t) t.innerHTML = tray(); return; }
      case 'openv': { const p = (D.projects || []).find(x => x.id === id); if (!p) return;
        if (p.chat) { clearTimeout(C.t); C.gen++; C.conv = p.chat; C.rows = []; C.items = []; await chatLoad(); UI.pv = {...UI.pv, id: p.id, scene: 0, tab: 'sketch'}; return go('chat'); }
        UI.scene = 0; return go('studio', id); }
      case 'say': return chatSend(b.dataset.t);
      case 'morelang': return menu(b, [{search: 'Make it in', empty: 'No language matches'}, ...(UI.L || []).map(l => ({label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name, sub: l.region,
        run: () => chatSend(`Make the same video in ${l.name}, keeping every name and number.`)}))], {width: 300});
      case 'ipick': { const k = b.dataset.k; return pickMenu(b, k, v => saveItem(id, {[k === 'face' ? 'avatar_id' : k]: v}), id); }
      case 'flay': return saveItem(id, {face_layout: b.dataset.val});
      case 'hear': return hear(id);
      case 'edhear': { const p = cur(); return p && hear(p.id, p.scenes[UI.scene]?.say); }
      case 'cmp': return compare(b, id);
      case 'pvtab': UI.pv.tab = b.dataset.val; pvStop(); return paintPv();
      case 'pvscene': pvStop(); UI.pv.id = id; UI.pv.scene = +b.dataset.n; UI.pv.tab = 'sketch'; $$('.hx-sct.on').forEach(x => x.classList.remove('on')); b.classList.add('on'); return paintPv();
      case 'pvplay': return pvPlay();
      case 'pvwhich': return menu(b, C.items.map(i => ({label: i.title, sub: vstate(i)[1], checked: pvItem()?.id === i.id, run: () => { pvStop(); UI.pv.id = i.id; UI.pv.scene = 0; paintChat(); }})), {align: 'end', width: 300});
      case 'subdl': { const p = PAGE === 'studio' && ARG ? cur() : pvItem(); if (!p) return; const vtt = b.dataset.val === 'vtt';
        const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([srt(p, vtt)], {type: vtt ? 'text/vtt' : 'application/x-subrip'}));
        link.download = `${(p.title || 'subtitles').replace(/[^\w .-]+/g, '_').slice(0, 60)}.${vtt ? 'vtt' : 'srt'}`; document.body.appendChild(link); link.click(); link.remove(); return; }
      case 'chats': { let list = []; try { list = (await api('GET', `${C0}/chats`)).chats || []; } catch (er) { return toast(er.message, true); }
        return menu(b, list.length ? list.map(c => ({label: c.title, sub: ago(c.at), run: async () => { clearTimeout(C.t); C.gen++; C.conv = c.id; C.title = c.title; C.rows = []; C.items = []; await chatLoad(); go('chat'); }})) : [{note: 'No earlier chats yet.'}], {align: 'end', width: 300}); }
      case 'send': return chatSend();
      case 'idea': { const [t, l, k] = IDEAS[UI.ideaG || 'business'][+b.dataset.n]; C.ask = t; SET.lang = l; SET.kind = k; SET.shape = shapeOf(k); store.set('hx.set', SET);
        draw(); const ta = $('#hxAsk'); if (ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); } return; }
      case 'pick': return pickMenu(b, b.dataset.k, v => setPick(b.dataset.k, v));
      case 'make': return make(id, b.dataset.k);
      case 'stop': try { await api('POST', `${S}/stop`, {id}); toast('Stopping at the next step.'); } catch (er) { toast(er.message, true); } return;
      case 'openp': UI.scene = 0; UI.edv = 'video'; return go('studio', id);
      case 'dlv': return download(id);
      case 'tr': return trMenu(b, id);
      case 'dup': return dupP(id);
      case 'trash': return trashP(id);
      case 'restore': try { await api('POST', `${H}/restore`, {id}); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'emptytrash': if (!confirm('Remove everything in the trash for good?')) return; try { await api('POST', `${H}/trash/empty`); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'scene': return edScene(+b.dataset.n, true);
      case 'tool': { UI.tool = b.dataset.val; $$('.hx-edtabs [role=tab]').forEach(t => t.setAttribute('aria-selected', String(t.dataset.val === UI.tool)));
        const x = $('#hxEdTool'), p = cur(); if (x && p) x.innerHTML = edTool(p); else draw(); fillMedia(); if (UI.tool === 'Engine') edCompare(); return; }
      case 'addsc': { const p = cur(); if (!p) return; UI.scene = p.scenes.length; return save({scenes: [...p.scenes, {say: '', look: {kind: 'none'}}]}); }
      case 'delsc': { const p = cur(); if (!p || p.scenes.length < 2) return; const n = b.dataset.n != null ? +b.dataset.n : UI.scene;
        if ((p.scenes[n]?.say || '').trim() && !confirm(`Remove scene ${n + 1}?`)) return;
        return scenesSave(p.scenes.filter((_, i) => i !== n), Math.max(0, Math.min(UI.scene > n ? UI.scene - 1 : UI.scene, p.scenes.length - 2))); }
      case 'scmove': { const p = cur(); if (!p) return; const n = +b.dataset.n, to = n + +b.dataset.d; if (to < 0 || to >= p.scenes.length) return;
        const sc = [...p.scenes]; [sc[n], sc[to]] = [sc[to], sc[n]]; return scenesSave(sc, to); }
      case 'scdup': { const p = cur(); if (!p) return; const n = +b.dataset.n, sc = [...p.scenes]; sc.splice(n + 1, 0, JSON.parse(JSON.stringify(sc[n]))); return scenesSave(sc, n + 1); }
      case 'scprev': return edScene(UI.scene - 1, true);
      case 'scnext': return edScene(UI.scene + 1, true);
      case 'edplay': return edPlay();
      case 'edview': UI.edv = b.dataset.val; edStop(); return edPaint(false);
      case 'lookset': { const p = cur(); if (!p) return; const k = b.dataset.val, old = p.scenes[UI.scene]?.look || {};
        if ((old.kind || 'none') === k) return;
        return scenesSave(p.scenes.map((s, i) => i === UI.scene ? {...s, look: {kind: k, ...(k === 'bar_chart' ? {bars: [{label: '', value: ''}, {label: '', value: ''}]} : {})}} : s)); }
      case 'baradd': { const p = cur(); if (!p) return; return scenesSave(p.scenes.map((s, i) => i === UI.scene ? {...s, look: {...s.look, bars: [...(s.look.bars || []), {label: '', value: ''}]}} : s)); }
      case 'bardel': { const p = cur(); if (!p) return; return scenesSave(p.scenes.map((s, i) => i === UI.scene ? {...s, look: {...s.look, bars: (s.look.bars || []).filter((_, j) => j !== +b.dataset.n)}} : s)); }
      case 'faceset': return save({avatar_id: b.dataset.val});
      case 'engset': if (UI.cmp?.id === ARG) UI.cmp.r.chosen = id; return save({engine: id});
      case 'paspect': return save({aspect: b.dataset.val});
      case 'itadd': { const p = cur(); if (!p) return; p.items = [...(p.items || []), {name: '', price: '', note: ''}]; const x = $('#hxEdTool'); if (x) x.innerHTML = edTool(p); $$('#hxItems [data-ik="name"]').pop()?.focus(); return; }
      case 'itdel': { const p = cur(); if (!p) return; return save({items: (p.items || []).filter((_, i) => i !== +b.dataset.n)}); }
      case 'vmenu': return vMenu(b, id);
      case 'lf': UI.lf = b.dataset.val; return draw();
      case 'lview': UI.lv = b.dataset.val; store.set('hx.lview', UI.lv); return draw();
      case 'lsort': return menu(b, Object.entries(LSORT).map(([k, l]) => ({label: l, checked: (UI.ls || 'new') === k, run: () => { UI.ls = k; store.set('hx.lsort', k); draw(); }})), {align: 'end'});
      case 'lclear': UI.lf = 'all'; UI.lq = ''; return draw();
      case 'ltrash': UI.ptab = 'Trash'; return go('projects');
      case 'lfrom': await newVideo(); return pickFiles('.pdf,.doc,.docx,.txt,.md,.rtf,.odt,.pptx,.ppt,.key,.odp', 'explainer', 'Make an explainer video from this document.');
      case 'lookpick': { const p = cur(); return menu(b, Object.entries(LOOK).map(([k, n]) => ({label: n, checked: (p.scenes[UI.scene]?.look?.kind || 'none') === k, run: () => {
        const sc = p.scenes.map((s, i) => i === UI.scene ? {...s, look: {kind: k, ...(k === 'bar_chart' ? {bars: [{label: '', value: ''}, {label: '', value: ''}]} : {})}} : s); save({scenes: sc}); }}))); }
      case 'ppick': { const k = b.dataset.k, p = cur(); const map = {avatar_id: 'face', voice: 'voice', lang: 'lang'};
        return pickMenu(b, map[k], v => save({[k]: v}), true); }
      case 'layout': return save({face_layout: b.dataset.val});
      case 'pshape': return save({shape: b.dataset.val});
      case 'peng': return;
      case 'tpluse': { const t = tplOf(id); if (!t) return; if (UI.tu?.id === id) UI.tu.sample = false; return go('templates', id); }
      case 'tplsample': { const t = tplOf(id); if (!t) return; tuState(t).sample = true; return go('templates', id); }
      case 'tplmenu': return tplMenu(b, id);
      case 'tplfrom': UI.dlg = {k: 'pick'}; return dlgPaint();
      case 'ttab': UI.tt = b.dataset.val; return draw();
      case 'tgrp': UI.tg = b.dataset.val; return draw();
      case 'tclear': UI.tq = ''; UI.tg = 'all'; UI.tsh = 'any'; UI.tt = 'all'; return draw();
      case 'tshape': return menu(b, Object.entries(TSHAPE).map(([k, l]) => ({label: l, checked: (UI.tsh || 'any') === k, run: () => { UI.tsh = k; draw(); }})));
      case 'tsort': return menu(b, Object.entries(TSORT).map(([k, l]) => ({label: l, checked: (UI.tso || 'used') === k, run: () => { UI.tso = k; draw(); }})), {align: 'end'});
      case 'tuscene': { if (!UI.tu) return; tuStop(); UI.tu.scene = +b.dataset.n; return tuPaint(); }
      case 'tuplay': return tuPlay();
      case 'tuhear': { const t = tplOf(ARG), u = UI.tu; if (!t || !u) return; const v = tuVals(t, u);
        const say = fillStr(t.scenes[u.scene]?.say, v).replace(/\{([a-z][a-z0-9_]*)\}/g, (m, k) => ((t.blanks || []).find(x => x.key === k)?.label || k).toLowerCase());
        try { const r = await api('POST', '/api/vocal/hear', {text: say.slice(0, 160), voice: u.voice || '', lang: t.lang || 'en'}, {raw: true});
          if (!r.ok) { let m = 'The sample could not be made.'; try { m = (await r.json()).detail || m; } catch { /* keep */ } throw new Error(m); }
          UI.audio?.pause(); UI.audio = new Audio(URL.createObjectURL(await r.blob())); UI.audio.play().catch(() => {}); } catch (er) { toast(er.message, true); } return; }
      case 'tupick': { const k = b.dataset.k, u = UI.tu; if (!u) return;
        return pickMenu(b, k, v => { u[k] = v; if (k === 'face' && !v) u.layout = 'corner'; draw(); tuEstimate(); }, k !== 'lang'); }
      case 'tulayout': if (UI.tu) { UI.tu.layout = b.dataset.val; tuPaint(true); } return;
      case 'tuaspect': if (UI.tu) { UI.tu.aspect = b.dataset.val; tuPaint(true); } return;
      case 'tumake': return tuMake();
      case 'tusheet': UI.dlg = {k: 'sheet', id: ARG, text: ''}; return dlgPaint();
      case 'dlgx': return dlgClose();
      case 'svopen': return svOpen(id);
      case 'svadd': return svAdd(b.dataset.t, !!b.dataset.w);
      case 'svdrop': if (UI.dlg) { UI.dlg.blanks = UI.dlg.blanks.filter(x => x.text !== b.dataset.t); dlgPaint(); } return;
      case 'svsave': return svSave();
      case 'shfile': return $('#hxShFile')?.click();
      case 'shmake': return shMake();
      case 'shstudio': dlgClose(); UI.lf = 'plan'; return go('studio');
      case 'tpldel': { const t = tplOf(id); if (!confirm(`Delete “${t?.name || 'this template'}”? Videos made from it stay.`)) return;
        try { await api('DELETE', `${H}/template?id=${q(id)}`); await load(); draw(); } catch (er) { toast(er.message, true); } return; }
      case 'tplsave': return tplSave(id);
      case 'aopen': if (UI.dlg?.k === 'need') dlgClose(); return appOpen(b, id);
      case 'aeng': dlgClose(); return go('engines');
      case 'agrp': UI.ag = b.dataset.val; return draw();
      case 'aclear': UI.aq = ''; UI.ag = 'all'; UI.aready = false; return draw();
      case 'arvid': arState().vid = id; draw(); if (ARG === 'names') arEstimate(lenOf((D.projects || []).find(x => x.id === id) || {})); return;
      case 'arpick': { const r = arState(), k = b.dataset.k;
        return pickMenu(b, k === 'tlang' ? 'lang' : k, v => { r[k] = v === 'auto' ? '' : v; draw(); }, k === 'tlang'); }
      case 'arnames': { const r = arState(), names = nameList(r.names); if (!r.vid || !names.length) return;
        r.busy = true; draw();
        try { const out = await api('POST', `${H}/personalise`, {project: r.vid, names}); r.busy = false; r.names = ''; await load(); toast(`${num(out.made.length)} drafts made. Nothing is made until you press Make on each.`); UI.lf = 'plan'; return go('studio'); }
        catch (er) { r.busy = false; draw(); toast(er.message, true); } return; }
      case 'arbatch': { const r = arState(), scripts = scriptList(r.scripts); if (!scripts.length) return;
        r.busy = true; draw();
        try { const out = await api('POST', `${H}/batch`, {scripts, lang: r.lang || 'auto', avatar_id: r.face}); r.busy = false; r.scripts = ''; await load(); toast(`${num(out.made.length)} drafts made. Nothing is made until you press Make on each.`); UI.lf = 'plan'; return go('studio'); }
        catch (er) { r.busy = false; draw(); toast(er.message, true); } return; }
      case 'artrans': { const r = arState(); if (!r.vid || !r.tlang) return;
        r.busy = true; draw();
        try { const p = await api('POST', `${H}/translate`, {id: r.vid, lang: r.tlang}); r.busy = false; await load(); UI.scene = 0; toast('A translated draft is ready. Lines that changed a number are marked.'); return go('studio', p.id); }
        catch (er) { r.busy = false; draw(); toast(er.message, true); } return; }
      case 'abidea': UI.broll.prompt = b.dataset.t; return draw();
      case 'abs': UI.broll.seconds = +b.dataset.val; UI.broll.q = null; draw(); return abQuote();
      case 'aba': UI.broll.aspect = b.dataset.val; return draw();
      case 'abmake': { const br = UI.broll; br.prompt = ($('#hxArBr')?.value || '').trim();
        br.busy = true; draw();
        try { await api('POST', `${X}/broll`, {prompt: br.prompt, seconds: br.seconds, aspect: br.aspect, quote_key: br.q?.key || ''}); br.busy = false; br.prompt = ''; await load(); draw(); abWatch(); toast('Making the shot. It appears here when ready.'); }
        catch (er) { br.busy = false; draw(); toast(er.message, true); } return; }
      case 'avadd': if ((D.avatars || []).length >= AVMAX) return toast(`You have ${AVMAX} faces. Remove one first.`);
        UI.dlg = {k: 'avphoto', who: 'me', consent: false}; return dlgPaint();
      case 'avai': if ((D.avatars || []).length >= AVMAX) return toast(`You have ${AVMAX} faces. Remove one first.`);
        UI.dlg = {k: 'avai', age: '30s', look: 'warm', behind: 'wall', items: []}; dlgPaint();
        api('GET', `${S}/avatar/ai/quote?count=4`).then(r => { if (UI.dlg?.k === 'avai') { UI.dlg.quote = r; dlgPaint(); } }).catch(() => { if (UI.dlg?.k === 'avai') { UI.dlg.quote = {ready: false}; dlgPaint(); } }); return;
      case 'avtwin': UI.dlg = {k: 'avtwin'}; return dlgPaint();
      case 'avpick': return $('#hxAvPh')?.click();
      case 'avphsave': return avPhSave();
      case 'aiopt': if (UI.dlg?.k === 'avai') { const k = b.dataset.k; UI.dlg.describe = $('#hxAiD')?.value ?? UI.dlg.describe; UI.dlg[k] = UI.dlg[k] === b.dataset.val ? '' : b.dataset.val; dlgPaint(); } return;
      case 'aimake': return aiMake();
      case 'aipick': if (UI.dlg?.k === 'avai') { UI.dlg.describe = $('#hxAiD')?.value ?? UI.dlg.describe; UI.dlg.name = $('#hxAiNm')?.value ?? UI.dlg.name; UI.dlg.pick = id; dlgPaint(); } return;
      case 'aikeep': return aiKeep();
      case 'avsel': (UI.av ||= {}).sel = id; return draw();
      case 'avkind': (UI.av ||= {}).kind = b.dataset.val; return draw();
      case 'avsort': return menu(b, [['used', 'Most used'], ['name', 'By name'], ['new', 'Newest']].map(([v, l]) => ({label: l, checked: (UI.av?.sort || 'used') === v, run: () => { (UI.av ||= {}).sort = v; draw(); }})));
      case 'avvid': return go('studio', id);
      case 'avren': UI.dlg = {k: 'avren', id}; return dlgPaint();
      case 'avrensave': { const n = ($('#hxAvRn')?.value || '').trim(); if (!n) return toast('Give the face a name.');
        try { await api('PATCH', `${S}/avatar`, {id: UI.dlg.id, name: n}); UI.dlg = null; dlgPaint(); await load(); draw(); toast('Renamed.'); } catch (er) { toast(er.message, true); } return; }
      case 'avdefault': if (SET.face === id) { setPick('face', ''); toast('No default face now. New videos start without one.'); } else { setPick('face', id); toast(`New videos start with ${face(id)?.name || 'this face'}.`); } return;
      case 'avtest': return avTest(id);
      case 'avdel': { const a = face(id); const n = avUses(a || {}).length;
        if (!confirm(`Remove ${a?.name || 'this face'}?${n ? ` ${n} video${n === 1 ? ' uses' : 's use'} it; those drafts lose the face, and videos already made keep it.` : ''} This cannot be undone.`)) return;
        try { await api('DELETE', `${S}/avatar?id=${q(id)}`); if (SET.face === id) setPick('face', ''); if (UI.av?.sel === id) UI.av.sel = ''; await load(); draw(); toast('Face removed.'); } catch (er) { toast(er.message, true); } return; }
      case 'useface': setPick('face', id); toast('Your next video uses this face.'); return;
      case 'setvoice': setPick('voice', id); return;
      case 'voplay': return voPlay(id);
      case 'vosel': (UI.vo ||= {}).sel = id; return voRepaint();
      case 'vokind': Object.assign(UI.vo ||= {}, {k: b.dataset.val, more: 0}); return voRepaint();
      case 'vomore': (UI.vo ||= {}).more = (UI.vo.more || 0) + 1; return voRepaint();
      case 'vofav': return voFavToggle(id);
      case 'vogen': return menu(b, [['', 'Any gender'], ['female', 'Women'], ['male', 'Men']].map(([v, l]) => ({label: l, checked: (UI.vo?.g || '') === v, run: () => { Object.assign(UI.vo ||= {}, {g: v, more: 0}); voRepaint(); }})));
      case 'volang': return menu(b, [{search: 'Samples in', empty: 'No language matches'}, ...(UI.L || []).map(l => ({label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name, sub: l.region, checked: voLang() === l.code,
        run: () => { (UI.vo ||= {}).lang = l.code; UI.audio?.pause(); UI.voPlay = ''; voRepaint(); }}))], {width: 280});
      case 'vouse': setPick('voice', id); toast(`New videos speak in ${voOf(id)?.name || 'this voice'}.`); return;
      case 'voput': UI.dlg = {k: 'voput', id, ids: []}; return dlgPaint();
      case 'voputgo': return voPutGo();
      case 'vovocal': window.__hvPage = 'voices'; leave(); return ctx.go ? ctx.go('vocal') : back?.();
      case 'livenew': UI.live = 'new'; UI.liveOut = []; return draw();
      case 'liveopen': UI.live = id; UI.liveOut = []; UI.pub = null; return draw();
      case 'liveback': UI.live = ''; return draw();
      case 'lpick': { const k = b.dataset.k; return pickMenu(b, k, v => { const i = $(`#hxLiveF [name="${k}"]`); if (i) i.value = v; b.querySelector('span').textContent = k === 'lang' ? langName(v) : voiceName(v); }, true); }
      case 'livesave': return liveSave();
      case 'livedel': if (!confirm('Remove this agent? If it is on your website it stops answering there.')) return; try { await api('DELETE', `${X}/live?id=${q(id)}`); UI.live = ''; await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'liveask': return liveAsk();
      case 'livesess': return liveSession();
      case 'livepub': try { UI.pub = {id, ...(await api('POST', `${X}/live/publish`, {id, on: true, sites: [($('#hxSites')?.value || '').trim()]}))}; await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'liveunpub': try { await api('POST', `${X}/live/publish`, {id, on: false}); UI.pub = null; await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'ptab': UI.ptab = b.dataset.val; return draw();
      case 'batch': { const scripts = ($('#hxBatch')?.value || '').split(/\n\s*\n/).map(s => s.trim()).filter(Boolean); if (!scripts.length) return toast('Write at least one script.');
        try { const r = await api('POST', `${H}/batch`, {scripts, lang: SET.lang, avatar_id: SET.face}); toast(`${r.made.length} drafts made.`); await load(); UI.ptab = 'Videos'; draw(); } catch (er) { toast(er.message, true); } return; }
      case 'pnpick': return menu(b, (D.projects || []).map(p => ({label: p.title, run: () => { UI.pn = p.id; draw(); }})), {width: 300});
      case 'names': { const names = ($('#hxNames')?.value || '').split('\n').map(s => s.trim()).filter(Boolean);
        try { const r = await api('POST', `${H}/personalise`, {project: UI.pn || '', names}); toast(`${r.made.length} drafts made.`); await load(); UI.ptab = 'Videos'; draw(); } catch (er) { toast(er.message, true); } return; }
      case 'brandsave': { const f = new FormData($('#hxBrandF')); try { D.brand = await api('PUT', `${H}/brand`, Object.fromEntries(f)); toast('Saved.'); } catch (er) { toast(er.message, true); } return; }
      case 'gloadd': { const t = ($('#hxGlo')?.value || '').trim(); if (!t) return; try { D.glossary = await api('POST', `${H}/glossary`, {term: t}); draw(); } catch (er) { toast(er.message, true); } return; }
      case 'glodel': try { D.glossary = await api('DELETE', `${H}/glossary?id=${q(id)}`); draw(); } catch (er) { toast(er.message, true); } return;
      case 'etab': UI.etab = b.dataset.val; draw(); if (UI.etab === 'broll') brQuote(); return;
      case 'edef': try { await api('PUT', `${X}/engines/default`, {id}); await load(); if (D.engines.engines.find(x => x.id === id)?.job === 'video') { SET.engine = ''; store.set('hx.set', SET); } draw(); } catch (er) { toast(er.message, true); } return;
      case 'brs': UI.broll.seconds = +b.dataset.val; return brQuote();
      case 'bra': UI.broll.aspect = b.dataset.val; return draw();
      case 'brmake': { UI.broll.prompt = ($('#hxBr')?.value || '').trim();
        try { await api('POST', `${X}/broll`, {prompt: UI.broll.prompt, seconds: UI.broll.seconds, aspect: UI.broll.aspect, quote_key: UI.broll.q?.key || ''}); toast('Making the shot. It appears here when ready.'); await load(); draw(); setTimeout(async () => { await load(); if (PAGE === 'engines') draw(); }, 60000); }
        catch (er) { toast(er.message, true); } return; }
      case 'keynew': try { UI.newKey = await api('POST', `${X}/apps/keys`, {name: $('#hxKeyName')?.value || ''}); D.apps = await api('GET', `${X}/apps`); draw(); } catch (er) { toast(er.message, true); } return;
      case 'keydel': try { await api('DELETE', `${X}/apps/keys?id=${q(id)}`); UI.newKey = null; D.apps = await api('GET', `${X}/apps`); draw(); } catch (er) { toast(er.message, true); } return;
      case 'hooknew': try { UI.newHook = await api('POST', `${X}/apps/hooks`, {url: $('#hxHookUrl')?.value || ''}); D.apps = await api('GET', `${X}/apps`); draw(); } catch (er) { toast(er.message, true); } return;
      case 'hookdel': try { await api('DELETE', `${X}/apps/hooks?id=${q(id)}`); D.apps = await api('GET', `${X}/apps`); draw(); } catch (er) { toast(er.message, true); } return;
      case 'hooktest': try { const h = await api('POST', `${X}/apps/hooks/test`, {id}); toast(`Your server answered: ${h.last_status || 'nothing'}`); D.apps = await api('GET', `${X}/apps`); draw(); } catch (er) { toast(er.message, true); } return;
    }
  }
  function onInput(e) {
    const t = e.target;
    if (t.dataset.isc != null) { saveLine(t.dataset.id, +t.dataset.isc, t.value); return; }
    if (t.id === 'hxAsk') { C.ask = t.value; t.style.height = 'auto'; t.style.height = Math.min(180, t.scrollHeight) + 'px'; $('.hx-send')?.classList.toggle('on', !!t.value.trim()); return; }
    if (t.id === 'hxVoq') { Object.assign(UI.vo ||= {}, {q: t.value, more: 0}); const l = $('#hxVoList'); if (l) l.innerHTML = voList(); const sm = t.parentElement?.querySelector('small'); if (sm) sm.textContent = t.value ? 'Best matches first' : ''; return; }
    if (t.id === 'hxAvq') { (UI.av ||= {}).q = t.value; const l = $('#hxAvList'); if (l) l.innerHTML = avList(); fillMedia(); return; }
    if (UI.dlg && t.id === 'hxAvNm') { UI.dlg.name = t.value; return; }
    if (UI.dlg && t.id === 'hxAvPer') { UI.dlg.person = t.value; return; }
    if (UI.dlg && t.id === 'hxAiD') { UI.dlg.describe = t.value; return; }
    if (UI.dlg && t.id === 'hxAiNm') { UI.dlg.name = t.value; return; }
    if (t.id === 'hxAq') { UI.aq = t.value; const l = $('#hxAppList'); if (l) l.innerHTML = appsList(); return; }
    if (t.id === 'hxArBr') { UI.broll.prompt = t.value; return; }
    if (t.id === 'hxArNames' || t.id === 'hxArBatch') { const r = arState(); r[t.id === 'hxArNames' ? 'names' : 'scripts'] = t.value;
      const nn = t.id === 'hxArNames' ? nameList(t.value).length : scriptList(t.value).length, max = D.limits?.batch || 20, wd = t.id === 'hxArNames' ? 'name' : 'script';
      const c = $('#hxArN'); if (c) c.textContent = `${num(nn)} ${wd}${nn === 1 ? '' : 's'} · up to ${num(max)}`;
      const pr = $('#hxArPrice'); if (pr) pr.innerHTML = arPriceNow();
      const mk = $(t.id === 'hxArNames' ? '[data-a=arnames]' : '[data-a=arbatch]');
      if (mk) { mk.disabled = !nn || nn > max || (t.id === 'hxArNames' && !r.vid); mk.textContent = `Make ${nn ? num(nn) + ' ' : ''}draft${nn === 1 ? '' : 's'}`; }
      clearTimeout(UI.arT); UI.arT = setTimeout(() => { if (PAGE === 'apps' && !$('#hxArNames:focus, #hxArBatch:focus')) draw(); }, 2500);
      const li = $('#hxArList'); if (li && t.id === 'hxArNames') { const p = (D.projects || []).find(x => x.id === r.vid);
        li.innerHTML = nameList(t.value).slice(0, 6).map((n, i) => `<li><span class="n">${i + 1}</span><b>${esc(n)}</b><span>${esc(String(p?.scenes?.[0]?.say || '').replace(/\{name\}/g, n))}</span></li>`).join(''); }
      return; }
    if (t.id === 'hxTq') { UI.tq = t.value; const l = $('#hxTplList'); if (l) { l.innerHTML = tplList(); fillMedia(); } return; }
    if (t.dataset.tv && UI.tu) { UI.tu.vals[t.dataset.tv] = t.value; tuPaint(); tuEstimate(); return; }
    if (t.id === 'hxSvName' && UI.dlg) { UI.dlg.name = t.value; return; }
    if (t.dataset.svk != null && UI.dlg?.blanks) { const bb = UI.dlg.blanks[+t.dataset.svk]; if (bb) { bb.label = t.value; bb.auto = false; $$('#hxSvText .hx-svb').filter(x => x.dataset.t === bb.text).forEach(x => { x.textContent = t.value || 'blank'; }); } return; }
    if (t.id === 'hxShText' && UI.dlg) { UI.dlg.text = t.value; const tt = tplOf(UI.dlg.id), r = tt && sheetParse(tt, t.value), sm = $('#hxShSum'), mk = $('#hxDlg [data-a=shmake]');
      if (r && sm) sm.textContent = r.rows.length ? `${num(r.rows.length)} row${r.rows.length === 1 ? '' : 's'}${r.miss.length ? ` · no column for: ${r.miss.map(x => x.label.toLowerCase()).join(', ')}` : ' · every blank has a column'}` : '';
      if (r && mk) { mk.disabled = !r.rows.length || r.rows.length > 50; mk.textContent = `Make ${r.rows.length ? num(r.rows.length) + ' ' : ''}draft${r.rows.length === 1 ? '' : 's'} · free`; } return; }
    if (t.id === 'hxLq') { UI.lq = t.value; const l = $('#hxLibList'); if (l) { l.innerHTML = libList(); fillMedia(); } return; }
    const p = PAGE === 'studio' && cur(); if (!p) return;
    if (t.dataset.sc != null) { const n = +t.dataset.sc, sc = p.scenes.map((s, i) => i === n ? {...s, say: t.value} : s); p.scenes = sc; saveSoon({scenes: sc});
      if (n === UI.scene) { const c = $('#hxEdStage .hx-pvcap'); if (c) c.textContent = t.value; } edTimes(p); return; }
    if (t.dataset.it != null) { const items = $$('#hxItems .hx-itrow').map(r => ({name: r.querySelector('[data-ik=name]').value, price: r.querySelector('[data-ik=price]').value, note: ''}));
      p.items = items; saveSoon({items}); return; }
    if (t.dataset.f) { saveSoon({[t.dataset.f]: t.value}); return; }
    if (t.dataset.lk) { const sc = p.scenes.map((s, i) => i === UI.scene ? {...s, look: {...s.look, [t.dataset.lk]: t.value}} : s); p.scenes = sc; saveSoon({scenes: sc});
      const lb = $('#hxEdStage .hx-pvlook'); if (lb) lb.innerHTML = lookText(sc[UI.scene].look) ? `<b>${esc(lookText(sc[UI.scene].look))}</b>` : ''; return; }
    if (t.dataset.bar != null) { const sc = p.scenes.map((s, i) => i !== UI.scene ? s : {...s, look: {...s.look, bars: (s.look.bars || []).map((bb, j) => j === +t.dataset.bar ? {...bb, [t.dataset.bk]: t.value} : bb)}}); p.scenes = sc; saveSoon({scenes: sc});
      const lb = $('#hxEdStage .hx-pvlook'); if (lb) lb.innerHTML = `<b>${esc(lookText(sc[UI.scene].look))}</b>`; }
  }
  function onChange(e) {
    const t = e.target;
    if (t.id === 'hxAready') { UI.aready = t.checked; const l = $('#hxAppList'); if (l) l.innerHTML = appsList(); return; }
    if (t.id === 'hxShFile' && UI.dlg) { const f = t.files?.[0]; if (!f) return; if (f.size > 2 * 1024 * 1024) return toast('That file is larger than 2 MB.', true);
      const rd = new FileReader(); rd.onload = () => { UI.dlg.text = String(rd.result || ''); dlgPaint(); }; rd.readAsText(f); return; }
    if (t.dataset?.vop && UI.dlg?.k === 'voput') { const id = t.dataset.vop, ids = UI.dlg.ids; if (t.checked) { if (!ids.includes(id)) ids.push(id); } else UI.dlg.ids = ids.filter(x => x !== id); return dlgPaint(); }
    if (t.id === 'hxAvPh') return avPhFile(t.files?.[0]);
    if (t.name === 'hxAvWho' && UI.dlg?.k === 'avphoto') { UI.dlg.who = t.value; return dlgPaint(); }
    if (t.id === 'hxAvOk' && UI.dlg?.k === 'avphoto') { UI.dlg.consent = t.checked; return dlgPaint(); }
    if (t.name === 'peng' && PAGE === 'studio') return save({engine: t.value});
    if (t.name === 'face' && t.closest('#hxLiveF')) { const f = new FormData($('#hxLiveF')); UI._draft = Object.fromEntries(f); }
  }
  async function liveSave() {
    const body = Object.fromEntries(new FormData($('#hxLiveF')));
    try { const a = await api('POST', `${X}/live`, body); UI.live = a.id; await load(); draw(); toast('Saved.'); } catch (er) { toast(er.message, true); }
  }
  async function liveAsk() {
    const i = $('#hxTryIn'), t = (i?.value || '').trim(); if (!t) return;
    i.value = ''; UI.liveOut.push({me: true, t}); draw();
    try { const r = await api('POST', `${X}/live/ask`, {id: UI.live, text: t}); UI.liveOut.push({t: r.answer}); draw();
      if (r.audio) { const au = new Audio(`data:${r.mime || 'audio/wav'};base64,${r.audio}`); au.play().catch(() => {}); } else if (r.voice_error) toast(r.voice_error, true); }
    catch (er) { UI.liveOut.push({t: er.message}); draw(); }
  }
  async function liveSession() {
    try {
      const s = await api('POST', `${X}/live/session`, {id: UI.live});
      if (s.kind === 'tavus' && s.url) { window.open(s.url, '_blank', 'noopener'); toast('Tavus opened in a new tab.'); return; }
      if (s.kind === 'gpulab') { window.open('/static/interactive/live.html', '_blank', 'noopener'); return; }
      if (s.kind === 'voice') { toast('This agent answers by voice only. Ask it something.'); return; }
      toast(`${engine(s.engine)?.label || 'The face engine'} gave a session pass. Showing its face in this page needs its browser kit, which is not added yet; Try it answers by voice meanwhile.`);
    } catch (er) { toast(er.message, true); }
  }
  return {open, leave};
};
