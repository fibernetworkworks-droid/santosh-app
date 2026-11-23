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
  const UI = {slim: store.get('hx.slim', false), nav: false, etab: 'video', ptab: 'Videos', scene: 0, tool: 'Look', V: null, L: null,
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
    trash: '<path d="M5 7h14M10 7V5h4v2M7 7l1 13h8l1-13"/>', warn: '<path d="M12 4l9 15.5H3zM12 10v4.5M12 17.2v.1"/>', spark: '<path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>'};
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
    ROOT.addEventListener('keydown', e => { if (e.target.id === 'hxAsk' && e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); chatSend(); }
      if (e.key === 'Escape' && UI.nav) { UI.nav = false; side(); } });
  }
  async function open() { mount(); await load(); go(PAGE, ARG); voicesLoad().then(() => { if (PAGE === 'chat') refreshBar(); }); langsLoad().then(() => { if (PAGE === 'chat' && $('.hx-hero')) draw(); }); meLoad(); recentLoad(); estimate(); }
  function leave() { clearTimeout(C.t); pvStop(); UI.audio?.pause(); Object.values(UI.jobs).forEach(clearTimeout); UI.jobs = {}; window.HoolaMenu?.close(); if (ROOT) { ROOT.querySelectorAll('audio,video').forEach(m => m.pause?.()); ROOT.hidden = true; } }
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
    const p = PAGE === 'studio' && ARG ? ['Studio', (D.projects || []).find(x => x.id === ARG)?.title || 'Video'] : PAGE === 'chat' ? [C.title && C.title !== 'Interactive chat' ? C.title : 'Interactive chat'] : [TITLE[PAGE] || ''];
    $('#hxCrumb').innerHTML = `<span>Interactive ·${p.length > 1 ? ' ' + esc(p[0]) + ' ·' : ''}</span><h1 class="hx-h">${esc(p[p.length - 1])}</h1>`;
    const t = $('#hxTopR');
    t.innerHTML = PAGE === 'chat' ? `${UI.credits != null ? `<button type="button" class="hx-credp hx-num" data-a="credits" title="Your credits">${ic('spark', 14)}${num(UI.credits)} credits</button>` : ''}
      <button type="button" class="hx-ib" data-a="chats" aria-label="Earlier chats" title="Earlier chats">${ic('clock', 18)}</button>
      <button type="button" class="hx-ib" data-a="newchat" aria-label="New chat" title="New chat">${ic('plus', 18)}</button>`
      : PAGE === 'studio' && !ARG ? `<button type="button" class="hx-btn s dark" data-a="go" data-p="chat">${ic('plus', 14)}<span>New video</span></button>` : '';
  }
  function go(page, arg) {
    window.HoolaMenu?.close();
    PAGE = V[page] ? page : 'chat'; ARG = arg || ''; UI.nav = false;
    side(); crumb(); draw();
    const v = $('#hxView'); v.scrollTop = 0; v.classList.remove('hx-enter'); void v.offsetWidth; v.classList.add('hx-enter');
    ENTER[PAGE]?.();
  }
  function draw() { $('#hxView').innerHTML = V[PAGE](); AFTER[PAGE]?.(); fillMedia(); }

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
  async function hear(id) {
    const p = C.items.find(x => x.id === id), text = (p?.scenes?.[0]?.say || p?.title || '').split(/(?<=[.!?。！？])\s/)[0].slice(0, 160);
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
    const done = steps.filter(s => s.at != null && s.k !== j.current).length, pct = j.done ? 100 : Math.round(100 * (done + .5) / Math.max(1, steps.length));
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

  // ------------------------------------------------------------------ pages ---
  const V = {
    chat() {
      if (fresh()) return home();
      return `<div class="hx-split hx-ixchat"><div class="hx-chat"><div class="hx-log" id="hxLog"><div id="hxThread">${thread()}</div></div>${composer(false)}</div>
        <aside class="hx-stage hx-pv" id="hxPv" aria-label="Preview">${pvPane()}</aside></div>`;
    },
    studio() {
      if (!ARG) {
        const ps = (D.projects || []);
        return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Studio</h2><p class="hx-mut">Every video, scene by scene. Start a new one in the Interactive chat.</p></div></div>
          ${ps.length ? `<div class="hx-tablew hx-card"><table class="hx-table"><thead><tr><th>Video</th><th>Language</th><th>Engine</th><th>Status</th><th></th></tr></thead><tbody>
          ${ps.map(p => `<tr><td><button type="button" class="hx-lnk" data-a="openp" data-id="${esc(p.id)}">${esc(p.title)}</button><br><small class="hx-mut">${(p.scenes || []).length} scenes · ${esc(ago(p.updated))}</small></td>
            <td>${esc(langName(p.lang))}</td><td>${esc(engine(p.engine)?.label || 'Hoola standard')}</td><td>${chip(p)}</td>
            <td class="r"><button type="button" class="hx-ib s" data-a="trash" data-id="${esc(p.id)}" aria-label="Move to trash">${ic('trash', 15)}</button></td></tr>`).join('')}</tbody></table></div>`
          : `<div class="hx-empty"><b>No videos yet</b><span>Say what a video should say in the Interactive chat and its scenes appear here.</span>
            <button type="button" class="hx-btn dark" data-a="go" data-p="chat">Open the chat</button></div>`}</div>`;
      }
      const p = (D.projects || []).find(x => x.id === ARG);
      if (!p) return `<div class="hx-doc"><div class="hx-empty"><b>This video was not found</b><button type="button" class="hx-btn" data-a="go" data-p="studio">All videos</button></div></div>`;
      const sc = p.scenes[UI.scene] || p.scenes[0] || {say: '', look: {kind: 'none'}}, f = face(p.avatar_id), e = engine(p.engine);
      const brandC = /^#[0-9a-f]{6}$/i.test(D.brand?.color || '') ? D.brand.color : '#5B45E0';
      const lk = sc.look || {kind: 'none'};
      const lookText = lk.kind === 'title' ? lk.text : lk.kind === 'big_number' ? `${lk.value || '—'} ${lk.label || ''}` : lk.kind === 'price' ? `${lk.new || '—'}${lk.old ? ' · was ' + lk.old : ''}` : lk.kind === 'lower_third' ? `${lk.title || ''} · ${lk.sub || ''}` : lk.kind === 'bar_chart' ? (lk.bars || []).map(b => `${b.label} ${b.value}`).join(' · ') : '';
      return `<div class="hx-split hx-studio"><section class="hx-panel" aria-label="The script"><div class="hx-rh"><b class="hx-t">Script</b><span class="hx-grow"></span>
          <button type="button" class="hx-btn s" data-a="addsc">${ic('plus', 14)}Scene</button></div>
          <ol class="hx-script">${p.scenes.map((s, i) => `<li class="${i === UI.scene ? 'on' : ''}"><button type="button" class="hx-scn" data-a="scene" data-n="${i}" aria-label="Scene ${i + 1}">${i + 1}</button>
            <textarea class="hx-in hx-serifp" data-sc="${i}" rows="2" aria-label="Scene ${i + 1} words">${esc(s.say)}</textarea>
            ${s.needs ? `<small class="hx-why">${esc(s.needs)}</small>` : ''}</li>`).join('')}</ol>
          <label class="hx-fld"><span class="hx-lab">Closing line</span><input class="hx-in" data-f="closing" value="${esc(p.closing || '')}" maxlength="80"></label></section>
        <section class="hx-stage" aria-label="Preview"><div class="hx-stageb"><div class="hx-preview ${p.aspect === '9:16' ? 'tall' : p.aspect === '1:1' ? 'sq' : ''}" style="--brand:${esc(brandC)}">
            ${p.status === 'ready' ? `<video class="hx-player" controls playsinline preload="metadata" data-vid="${esc(p.id)}"></video>`
              : `<div class="hx-pvlook">${lookText ? `<b>${esc(lookText)}</b>` : ''}</div>${f ? `<span class="hx-pvface">${avImg(f, 'l')}</span>` : ''}<p class="hx-pvcap">${esc(sc.say)}</p>`}</div>
          <p class="hx-hint c">${p.status === 'ready' ? 'The finished video. Change a scene and make it again for a new version.' : `Scene ${UI.scene + 1} of ${p.scenes.length} · a sketch of the scene; the real one is drawn when you make it.`}</p>
          <div class="hx-strip">${p.scenes.map((s, i) => `<button type="button" class="hx-sthumb${i === UI.scene ? ' on' : ''}" data-a="scene" data-n="${i}">${i + 1}<small>${esc((s.say || '').slice(0, 28))}</small></button>`).join('')}</div>
          <div id="hxJob-${esc(p.id)}"></div>
          ${p.error && p.status === 'failed' ? `<p class="hx-why">${esc(scrub(p.error))}</p>` : ''}</div></section>
        <aside class="hx-stage hx-side2" aria-label="Tools"><div class="hx-stageb">
          <div class="hx-tabs" role="tablist">${['Look', 'Face', 'Voice', 'Engine', 'Video'].map(t => `<button type="button" role="tab" aria-selected="${UI.tool === t}" data-a="tool" data-val="${t}">${t}</button>`).join('')}</div>
          ${tool(p, sc)}
          <div class="hx-makebox"><span class="hx-price hx-num" id="hxQuote">Working out the price…</span>
            ${p.status === 'making' ? `<button type="button" class="hx-cta" data-a="stop" data-id="${esc(p.id)}">${ic('stop', 16)}<span>Stop</span></button>`
              : `<button type="button" class="hx-cta" data-a="make" data-id="${esc(p.id)}" id="hxMake">${ic('play', 16)}<span>${p.status === 'ready' ? 'Make it again' : 'Make the video'}</span></button>`}
            <span class="hx-hint">Engine: <b>${esc(e?.label || 'Hoola standard')}</b>. Nothing is spent until you tap.</span></div></div></aside></div>`;
    },
    templates() {
      const t = D.templates || [];
      return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Templates</h2><p class="hx-mut">Fill the blanks; every changing word is yours. Save any video as a template from Projects.</p></div></div>
        <div class="hx-grid3">${t.map(x => `<div class="hx-card hx-tpl"><b>${esc(x.name)}</b><small class="hx-mut">${esc(x.group || (x.mine ? 'Yours' : ''))} · ${(x.scenes || []).length} scenes</small>
          <p class="hx-serifp hx-mut">${esc((x.scenes || [])[0]?.say || '')}</p><div class="hx-acts"><button type="button" class="hx-btn s dark" data-a="tpluse" data-id="${esc(x.id)}">Use it</button>
          ${x.mine ? `<button type="button" class="hx-ib s" data-a="tpldel" data-id="${esc(x.id)}" aria-label="Remove">${ic('trash', 15)}</button>` : ''}</div></div>`).join('')}</div></div>`;
    },
    apps() {
      const A = [['Podcast with two hosts', 'A script from your document, two voices talking.', 'vocal', 'dialogue', 'Open in Hoola Vocal'],
        ['Clean up a recording', 'Background noise out, even loudness.', 'vocal', 'cleanup', 'Open in Hoola Vocal'],
        ['Your own voice', 'Copy your voice with your spoken consent, or design one.', 'vocal', 'mine', 'Open in Hoola Vocal'],
        ['Dub a video', 'Your video in other languages, in matched or its own voices.', 'vocal', 'dub', 'Open in Hoola Vocal'],
        ['Lip sync a video', 'A video of you, its lips moved to new words.', 'create', 'cinema', 'Open in Create'],
        ['An AI-made face', 'A face that is no real person, marked as AI.', 'create', 'image', 'Open in Create'],
        ['Music under a video', 'A jingle or a song for the video.', 'create', 'music', 'Open in Create'],
        ['A B-roll shot', 'A short shot of the shop or the product, no person.', 'here', 'engines', 'Make one'],
        ['A batch of videos', 'Many scripts at once, each a draft.', 'here', 'projects', 'Open Projects'],
        ['One video, many names', 'The same video with each customer’s name.', 'here', 'projects', 'Open Projects']];
      return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Apps</h2><p class="hx-mut">Each one is a real Hoola tool; nothing here is a placeholder.</p></div></div>
        <div class="hx-grid3">${A.map(([t, d, where, page, btn]) => `<div class="hx-card hx-app"><b>${esc(t)}</b><p class="hx-mut hx-sm">${esc(d)}</p>
          <button type="button" class="hx-btn s" data-a="app" data-w="${where}" data-p="${page}">${esc(btn)}</button></div>`).join('')}</div></div>`;
    },
    avatars() {
      const av = D.avatars || [], faces = (D.engines?.engines || []).filter(e => e.job === 'video' && e.face && e.ready).map(e => e.label);
      return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Avatars</h2><p class="hx-mut">Your faces. A face is used only with consent: it is you, or the person agreed.</p></div>
          <button type="button" class="hx-btn dark" data-a="avadd">${ic('plus', 14)}Add a face</button></div>
        <form class="hx-card hx-avform" id="hxAvForm" hidden><b class="hx-t">A new face</b><label class="hx-fld"><span class="hx-lab">Name</span><input class="hx-in" name="name" maxlength="40" placeholder="Meghana"></label>
          <div class="hx-filerow"><button type="button" class="hx-btn" data-a="avfile">Choose a photo</button><span id="hxAvName" class="hx-mut hx-sm">A clear photo facing the camera (png, jpg or webp)</span></div>
          <label class="hx-check"><input type="checkbox" name="consent"> <span>This is me, or the person in the photo agreed to be in AI videos. Never a public figure or anyone under 18.</span></label>
          <div class="hx-acts"><button type="button" class="hx-btn dark" data-a="avsave">Add the face</button><button type="button" class="hx-btn" data-a="avcancel">Cancel</button></div>
          <input type="file" accept="image/png,image/jpeg,image/webp" id="hxAvFile" hidden></form>
        ${av.length ? `<div class="hx-grid3">${av.map(a => `<div class="hx-card hx-avc">${avImg(a, 'xl')}<div class="hx-ct"><b>${esc(a.name)}</b><small>Consent on ${esc((a.consent_at || '').slice(0, 10))}</small></div>
            <p class="hx-hint">Can be made to talk by ${esc(faces.join(', ') || 'Hoola standard (still photo)')}.</p>
            <div class="hx-acts"><button type="button" class="hx-btn s" data-a="useface" data-id="${esc(a.id)}">Use in my next video</button>
            <button type="button" class="hx-ib s" data-a="avdel" data-id="${esc(a.id)}" aria-label="Remove ${esc(a.name)}">${ic('trash', 15)}</button></div></div>`).join('')}</div>`
          : `<div class="hx-empty"><b>No faces yet</b><span>Add your photo, and your videos can show you talking.</span></div>`}</div>`;
    },
    voices() {
      const Vv = UI.V || {mine: [], library: []};
      const row = v => `<div class="hx-vrow"><span class="hx-ct"><b>${esc(v.name)}</b><small>${esc([v.tone, v.gender, v.tier === 'premium' ? 'Premium' : 'Standard', v.ready ? '' : 'not connected'].filter(Boolean).join(' · '))}</small></span>
        <button type="button" class="hx-btn s${SET.voice === v.id ? ' dark' : ''}" data-a="setvoice" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}>${SET.voice === v.id ? 'Chosen' : 'Use this voice'}</button></div>`;
      return `<div class="hx-doc"><div class="hx-doch"><div class="hx-growf"><h2 class="hx-serif">Voices</h2><p class="hx-mut">The same voices as Hoola Vocal: 140 languages, premium voices, and your own.</p></div>
          <button type="button" class="hx-btn" data-a="app" data-w="vocal" data-p="mine">Make your own voice in Vocal</button></div>
        ${Vv.mine.length ? `<b class="hx-t">Your voices</b><div class="hx-card hx-list">${Vv.mine.map(row).join('')}</div>` : ''}
        <b class="hx-t">Ready-made voices</b><div class="hx-card hx-list">${Vv.library.slice(0, 80).map(row).join('') || '<p class="hx-mut">Loading voices…</p>'}</div></div>`;
    },
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
  function tool(p, sc) {
    const e = engine(p.engine), f = face(p.avatar_id);
    if (UI.tool === 'Look') {
      const lk = sc.look || {kind: 'none'};
      const field = (k, l) => `<label class="hx-fld"><span class="hx-lab">${l}</span><input class="hx-in" data-lk="${k}" value="${esc(lk[k] || '')}" maxlength="60"></label>`;
      const extra = {title: field('text', 'Title'), big_number: field('value', 'Number') + field('label', 'What it is'), price: field('new', 'Price now') + field('old', 'Price before') + field('label', 'Item'),
        lower_third: field('title', 'Name') + field('sub', 'Line under it'), bar_chart: (lk.bars || []).map((b, i) => `<div class="hx-row2"><input class="hx-in" data-bar="${i}" data-bk="label" value="${esc(b.label)}" aria-label="Bar ${i + 1} label"><input class="hx-in" data-bar="${i}" data-bk="value" value="${esc(b.value)}" aria-label="Bar ${i + 1} number"></div>`).join('')}[lk.kind] || '';
      return `<div class="hx-fld"><span class="hx-lab">Scene ${UI.scene + 1} look</span><button type="button" class="hx-dd" data-a="lookpick"><span>${esc(LOOK[lk.kind] || 'Just the words')}</span>${ic('down', 14)}</button></div>${extra}
        <p class="hx-hint">Numbers come only from you: a number you did not write is left for you to fill.</p>
        <button type="button" class="hx-btn s danger" data-a="delsc"${p.scenes.length < 2 ? ' disabled' : ''}>Remove this scene</button>`;
    }
    if (UI.tool === 'Face') return `<div class="hx-fld"><span class="hx-lab">Face</span><button type="button" class="hx-dd" data-a="ppick" data-k="avatar_id"><span>${esc(f ? f.name : 'No face')}</span>${ic('down', 14)}</button></div>
      ${e?.face ? `<div class="hx-fld"><span class="hx-lab">Where the person sits</span><div class="hx-seg" role="radiogroup">${[['corner', 'Over the scenes'], ['full', 'The whole frame']].map(([k, n]) => `<button type="button" role="radio" aria-checked="${(p.face_layout || 'corner') === k}" data-a="layout" data-val="${k}">${n}</button>`).join('')}</div></div>` : ''}
      <button type="button" class="hx-lnk" data-a="go" data-p="avatars">Add a face</button>`;
    if (UI.tool === 'Voice') return `<div class="hx-fld"><span class="hx-lab">Voice</span><button type="button" class="hx-dd" data-a="ppick" data-k="voice"><span>${esc(voiceName(p.voice))}</span>${ic('down', 14)}</button></div>
      <div class="hx-fld"><span class="hx-lab">Language</span><button type="button" class="hx-dd" data-a="ppick" data-k="lang"><span>${esc(langName(p.lang))}</span>${ic('down', 14)}</button></div>
      <p class="hx-hint">Your Hoola Vocal dictionary applies: names are said your way.</p>`;
    if (UI.tool === 'Engine') return `<div class="hx-list">${(D.engines?.engines || []).filter(x => x.job === 'video').map(x => `<label class="hx-opt${x.id === p.engine ? ' on' : ''}${x.ready ? '' : ' off'}"><input type="radio" name="peng" data-a="peng" value="${esc(x.id)}"${x.id === p.engine ? ' checked' : ''}${x.ready ? '' : ' disabled'}>
      <span class="hx-ct"><b>${esc(x.label)}</b><small>${esc(x.ready ? x.price + ' · ' + x.what : scrub(x.status))}</small></span></label>`).join('')}</div>`;
    return `<div class="hx-fld"><span class="hx-lab">Shape</span><div class="hx-seg" role="radiogroup">${Object.entries(SHAPE).map(([k, n]) => `<button type="button" role="radio" aria-checked="${p.shape === k}" data-a="pshape" data-val="${k}">${n}</button>`).join('')}</div></div>
      <label class="hx-fld"><span class="hx-lab">Title</span><input class="hx-in" data-f="title" value="${esc(p.title)}" maxlength="80"></label>`;
  }
  const ENTER = {
    chat() { (C.conv ? Promise.resolve() : openChat()).then(chatLoad).then(() => { if (PAGE !== 'chat') return; if ($('.hx-hero') && !fresh()) draw(); else paintChat(); chatPoll(); }); estimate(); },
    voices() { voicesLoad().then(() => { if (PAGE === 'voices') draw(); }); },
    studio() { if (ARG) { const p = (D.projects || []).find(x => x.id === ARG); if (p?.status === 'making') watchJob(ARG); studioQuote(); } },
    engines() { if (UI.etab === 'broll') brQuote(); },
  };
  const AFTER = {};

  // ------------------------------------------------------------------ studio edits ---
  const cur = () => (D.projects || []).find(x => x.id === ARG);
  async function save(body, redraw = true) {
    try { const p = await api('PUT', `${S}/project?id=${q(ARG)}`, body); const i = D.projects.findIndex(x => x.id === ARG); if (i >= 0) D.projects[i] = p; if (redraw) { draw(); } studioQuote(); }
    catch (e) { toast(e.message, true); }
  }
  let saveT = 0;
  function saveSoon(body) { clearTimeout(saveT); saveT = setTimeout(() => save(body, false), 600); }
  async function studioQuote() {
    if (PAGE !== 'studio' || !ARG) return;
    try { const r = await api('GET', `${X}/quote?id=${q(ARG)}`); const el = $('#hxQuote'); if (el) el.textContent = r.quote.line; const b = $('#hxMake'); if (b) { b.dataset.k = r.quote.key; b.disabled = !!(r.problems || []).length; if (r.problems?.length) el.textContent = scrub(r.problems.join(' ')); } }
    catch (e) { const el = $('#hxQuote'); if (el) el.textContent = e.message; }
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
      case 'newchat': clearTimeout(C.t); C.conv = ''; C.rows = []; C.items = []; C.files = []; C.ask = ''; UI.pv.id = ''; pvStop(); await openChat(true); recentLoad(); return go('chat');
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
      case 'cmp': return compare(b, id);
      case 'pvtab': UI.pv.tab = b.dataset.val; pvStop(); return paintPv();
      case 'pvscene': pvStop(); UI.pv.id = id; UI.pv.scene = +b.dataset.n; UI.pv.tab = 'sketch'; $$('.hx-sct.on').forEach(x => x.classList.remove('on')); b.classList.add('on'); return paintPv();
      case 'pvplay': return pvPlay();
      case 'pvwhich': return menu(b, C.items.map(i => ({label: i.title, sub: vstate(i)[1], checked: pvItem()?.id === i.id, run: () => { pvStop(); UI.pv.id = i.id; UI.pv.scene = 0; paintChat(); }})), {align: 'end', width: 300});
      case 'subdl': { const p = pvItem(); if (!p) return; const vtt = b.dataset.val === 'vtt';
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
      case 'openp': UI.scene = 0; return go('studio', id);
      case 'dlv': return download(id);
      case 'tr': return menu(b, [{search: 'Translate into', empty: 'No language matches'}, ...(UI.L || []).map(l => ({label: l.name, run: async () => {
        try { const p = await api('POST', `${H}/translate`, {id, lang: l.code}); toast('A translated draft is ready. Check it, then make it.'); await load(); go('studio', p.id); } catch (er) { toast(er.message, true); } }}))], {width: 260});
      case 'dup': try { const p = await api('POST', `${H}/duplicate`, {id}); await load(); go('studio', p.id); } catch (er) { toast(er.message, true); } return;
      case 'trash': try { await api('POST', `${H}/trash`, {id}); await load(); draw(); toast('Moved to the trash for 30 days.'); } catch (er) { toast(er.message, true); } return;
      case 'restore': try { await api('POST', `${H}/restore`, {id}); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'emptytrash': if (!confirm('Remove everything in the trash for good?')) return; try { await api('POST', `${H}/trash/empty`); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'scene': UI.scene = +b.dataset.n; return draw();
      case 'tool': UI.tool = b.dataset.val; return draw();
      case 'addsc': { const p = cur(); if (!p) return; UI.scene = p.scenes.length; return save({scenes: [...p.scenes, {say: '', look: {kind: 'none'}}]}); }
      case 'delsc': { const p = cur(); if (!p || p.scenes.length < 2) return; const sc = p.scenes.filter((_, i) => i !== UI.scene); UI.scene = Math.max(0, UI.scene - 1); return save({scenes: sc}); }
      case 'lookpick': { const p = cur(); return menu(b, Object.entries(LOOK).map(([k, n]) => ({label: n, checked: (p.scenes[UI.scene]?.look?.kind || 'none') === k, run: () => {
        const sc = p.scenes.map((s, i) => i === UI.scene ? {...s, look: {kind: k, ...(k === 'bar_chart' ? {bars: [{label: '', value: ''}, {label: '', value: ''}]} : {})}} : s); save({scenes: sc}); }}))); }
      case 'ppick': { const k = b.dataset.k, p = cur(); const map = {avatar_id: 'face', voice: 'voice', lang: 'lang'};
        return pickMenu(b, map[k], v => save({[k]: v}), true); }
      case 'layout': return save({face_layout: b.dataset.val});
      case 'pshape': return save({shape: b.dataset.val});
      case 'peng': return;
      case 'tpluse': { const t = (D.templates || []).find(x => x.id === id); const vars = [...new Set(JSON.stringify(t?.scenes || []).match(/\{([a-z][a-z0-9_]*)\}/g) || [])].map(v => v.slice(1, -1));
        const values = {}; for (const v of vars) { const x = prompt(`${v.replace(/_/g, ' ')}:`); if (x == null) return; values[v] = x; }
        try { const p = await api('POST', `${H}/template/use`, {id, values, lang: SET.lang, avatar_id: SET.face}); await load(); go('studio', p.id); } catch (er) { toast(er.message, true); } return; }
      case 'tpldel': try { await api('DELETE', `${H}/template?id=${q(id)}`); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'tplsave': try { await api('POST', `${H}/template`, {project: id}); await load(); toast('Saved as a template.'); } catch (er) { toast(er.message, true); } return;
      case 'app': { const w = b.dataset.w, pg = b.dataset.p;
        if (w === 'here') return go(pg === 'engines' ? (UI.etab = 'broll', 'engines') : pg);
        if (w === 'vocal') { window.__hvPage = pg; leave(); return ctx.go ? ctx.go('vocal') : back?.(); }
        location.assign(`/console/?v=creative&a=${q(pg)}`); return; }
      case 'avadd': { const f = $('#hxAvForm'); if (f) f.hidden = false; return; }
      case 'avcancel': { const f = $('#hxAvForm'); if (f) f.hidden = true; return; }
      case 'avfile': return $('#hxAvFile')?.click();
      case 'avsave': return avSave();
      case 'avdel': if (!confirm('Remove this face? Videos keep working; new ones will not use it.')) return; try { await api('DELETE', `${S}/avatar?id=${q(id)}`); await load(); draw(); } catch (er) { toast(er.message, true); } return;
      case 'useface': setPick('face', id); toast('Your next video uses this face.'); return;
      case 'setvoice': setPick('voice', id); return;
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
    const p = PAGE === 'studio' && cur(); if (!p) return;
    if (t.dataset.sc != null) { const sc = p.scenes.map((s, i) => i === +t.dataset.sc ? {...s, say: t.value} : s); p.scenes = sc; saveSoon({scenes: sc}); const c = $('.hx-pvcap'); if (c && +t.dataset.sc === UI.scene) c.textContent = t.value; return; }
    if (t.dataset.f) { saveSoon({[t.dataset.f]: t.value}); return; }
    if (t.dataset.lk) { const sc = p.scenes.map((s, i) => i === UI.scene ? {...s, look: {...s.look, [t.dataset.lk]: t.value}} : s); p.scenes = sc; saveSoon({scenes: sc}); return; }
    if (t.dataset.bar != null) { const sc = p.scenes.map((s, i) => i !== UI.scene ? s : {...s, look: {...s.look, bars: (s.look.bars || []).map((bb, j) => j === +t.dataset.bar ? {...bb, [t.dataset.bk]: t.value} : bb)}}); p.scenes = sc; saveSoon({scenes: sc}); }
  }
  function onChange(e) {
    const t = e.target;
    if (t.id === 'hxAvFile') { const f = t.files?.[0]; const n = $('#hxAvName'); if (n) n.textContent = f ? f.name : ''; return; }
    if (t.name === 'peng' && PAGE === 'studio') return save({engine: t.value});
    if (t.name === 'face' && t.closest('#hxLiveF')) { const f = new FormData($('#hxLiveF')); UI._draft = Object.fromEntries(f); }
  }
  async function avSave() {
    const f = $('#hxAvForm'), file = $('#hxAvFile')?.files?.[0], name = f.querySelector('[name=name]').value.trim(), consent = f.querySelector('[name=consent]').checked;
    if (!name) return toast('Give the face a name.');
    if (!file) return toast('Choose a photo first.');
    if (!consent) return toast('Tick that this is you, or that the person agreed.', true);
    try { const up = await upload(file); await api('POST', `${S}/avatar`, {file_id: up.file_id, name, consent, lang: SET.lang}); await load(); draw(); toast('Face added.'); }
    catch (er) { toast(er.message, true); }
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
