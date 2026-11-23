/* v0.999.169 HOOLA INTERACTIVE, REBUILT (owner: "GO BUILD" on the design canvas claude.ai/artifact/38Ejw9Eekn9y8u8H8nEwGp;
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
  const SET = Object.assign({lang: 'hi', face: '', voice: '', engine: '', shape: 'talking_head'}, store.get('hx.set', {}));
  const C = {conv: '', title: '', rows: [], items: [], ask: '', files: [], sending: false, waitUntil: 0, t: 0};
  const UI = {slim: store.get('hx.slim', false), nav: false, etab: 'video', ptab: 'Videos', scene: 0, tool: 'Look', V: null, L: null,
    live: '', liveOut: [], newKey: null, newHook: null, pub: null, broll: {prompt: '', seconds: 6, aspect: '16:9', q: null}, jobs: {}};
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
  const langName = c => (UI.L || []).find(l => l.code === c)?.name || ({hi: 'Hindi', en: 'English', mr: 'Marathi'}[c] || c || 'Hindi');
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
  async function langsLoad() { if (UI.L) return; try { UI.L = (await api('GET', `${X}/langs`)).langs; } catch { UI.L = [{code: 'hi', name: 'Hindi'}, {code: 'en', name: 'English'}]; } }

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
  async function open() { mount(); await load(); go(PAGE, ARG); voicesLoad().then(() => { if (PAGE === 'chat') refreshBar(); }); langsLoad(); }
  function leave() { clearTimeout(C.t); Object.values(UI.jobs).forEach(clearTimeout); UI.jobs = {}; window.HoolaMenu?.close(); if (ROOT) { ROOT.querySelectorAll('audio,video').forEach(m => m.pause?.()); ROOT.hidden = true; } }
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
      <button type="button" class="hx-newchat" data-a="newchat">${ic('plus')}<span>New interactive chat</span></button>
      ${NAV.map(([g, rows]) => `<span class="hx-gh">${g}</span>${rows.map(row).join('')}`).join('')}
      <span class="hx-grow"></span>${creditCard()}`;
  }
  function crumb() {
    const p = PAGE === 'studio' && ARG ? ['Studio', (D.projects || []).find(x => x.id === ARG)?.title || 'Video'] : PAGE === 'chat' ? [C.title && C.title !== 'Interactive chat' ? C.title : 'Interactive chat'] : [TITLE[PAGE] || ''];
    $('#hxCrumb').innerHTML = `<span>Interactive ·${p.length > 1 ? ' ' + esc(p[0]) + ' ·' : ''}</span><h1 class="hx-h">${esc(p[p.length - 1])}</h1>`;
    const t = $('#hxTopR');
    t.innerHTML = PAGE === 'chat' ? `<button type="button" class="hx-ib" data-a="chats" aria-label="Earlier chats" title="Earlier chats">${ic('clock', 18)}</button>
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

  // ------------------------------------------------------------------ the chat ---
  const settingsNote = () => `[Interactive settings: language ${SET.lang || 'auto'}; face ${SET.face || 'none'}; voice ${SET.voice || 'auto'}; engine ${defEngine()}; shape ${SET.shape}]`;
  const IDEAS = ['A Diwali offer video for my shop, 20% off till 3 November, in Hindi', 'Welcome new students to my coaching class in Marathi',
    'Introduce my new product in 30 seconds with its price', 'A short reel: our shop timings changed to 9 am to 9 pm'];
  async function openChat(fresh) {
    try { const c = await api(fresh ? 'POST' : 'GET', fresh ? `${C0}/chat/new` : `${C0}/chat`); C.conv = c.id; C.title = c.title; }
    catch (e) { toast(e.message, true); }
  }
  async function chatLoad() {
    if (!C.conv) return;
    try { C.rows = (await api('GET', `/api/conversations/${q(C.conv)}/messages?limit=200`)).messages || []; } catch { return; }
    try { C.items = (await api('GET', `${C0}/chat/${q(C.conv)}/items`)).items || []; } catch { /* next time */ }
  }
  const fresh = () => !C.rows.some(r => r.role === 'user') && !C.items.length;
  function chatPoll() {
    clearTimeout(C.t);
    const tick = async () => {
      if (PAGE !== 'chat' || !ROOT || ROOT.hidden) return;
      const n = C.rows.length, m = C.items.map(i => i.id + i.status).join();
      await chatLoad();
      if (C.rows.length !== n || C.items.map(i => i.id + i.status).join() !== m) { if ($('.hx-hero') && !fresh()) draw(); else paintChat(); }
      const waiting = Date.now() < C.waitUntil && C.rows[C.rows.length - 1]?.role === 'user';
      C.t = setTimeout(tick, waiting || C.items.some(i => i.status === 'making') ? 2000 : 8000);
    };
    C.t = setTimeout(tick, 1500);
  }
  function chips() {
    const e = engine(defEngine()), f = face(SET.face);
    return `<button type="button" class="hx-chip s" data-a="pick" data-k="face" aria-haspopup="menu">${f ? avImg(f, 'xs') : ic('user', 14)}<span>${esc(f ? f.name : 'No face')}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="voice" aria-haspopup="menu">${ic('mic', 14)}<span>${esc(voiceName(SET.voice))}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="engine" aria-haspopup="menu">${ic('bolt', 14)}<span>${esc(e ? e.label : 'Hoola standard')}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="lang" aria-haspopup="menu">${ic('globe', 14)}<span>${esc(langName(SET.lang))}</span></button>
      <button type="button" class="hx-chip s" data-a="pick" data-k="shape" aria-haspopup="menu"><span>${esc(SHAPE[SET.shape] || 'Talking person')}</span></button>`;
  }
  function composer() {
    return `<div class="hx-comp" id="hxComp"><div class="hx-box"><label class="hx-sr" for="hxAsk">Say what the video should say</label>
      <textarea id="hxAsk" rows="2" placeholder="Say what the video should say, in any language">${esc(C.ask)}</textarea>
      <div class="hx-boxrow"><div class="hx-chips" id="hxChips">${chips()}</div><span class="hx-grow"></span>
        <button type="button" class="hx-send${C.ask.trim() ? ' on' : ''}" data-a="send" aria-label="Send">${ic('up', 18)}</button></div></div>
      <p class="hx-foot">Hoola plans the scenes and shows the price. <b>Nothing is made until you tap Make.</b></p></div>`;
  }
  function refreshBar() { const c = $('#hxChips'); if (c) { c.innerHTML = chips(); fillMedia(); } }
  function vidsRail() {
    const vids = (D.projects || []).filter(p => p.video).slice(0, 12);
    return vids.length ? vids.map(p => `<button type="button" class="hx-vcard" data-a="openp" data-id="${esc(p.id)}"><span class="hx-thumb">${ic('play', 18)}</span>
      <span class="hx-ct"><b>${esc(p.title)}</b><small>${esc(langName(p.lang))} · ${esc(p.video.engine_label || 'Hoola standard')} · ${esc(ago(p.video.made))}</small></span></button>`).join('')
      : `<p class="hx-mut hx-sm">Your finished videos appear here.</p>`;
  }
  function planCard(it) {
    const e = engine(it.engine) || engine('hoola'), f = face(it.avatar_id), qn = it.quote || {}, pr = it.problems || [];
    const total = (it.scenes || []).reduce((n, s) => n + Math.max(2, (s.say || '').split(/\s+/).filter(Boolean).length / 2.6) + .35, 0);
    const making = it.status === 'making', ready = it.status === 'ready';
    return `<div class="hx-plan" data-id="${esc(it.id)}"><div class="hx-planh">${avImg(f)}<span class="hx-ct"><b>${esc(it.title)}</b>
        <small>${(it.scenes || []).length} scenes · about ${secs(total)} · ${esc(langName(it.lang))}</small></span>${chip(it)}</div>
      ${ready ? `<video class="hx-player" controls playsinline preload="metadata" data-vid="${esc(it.id)}"></video>` : `<ol class="hx-scenes">${(it.scenes || []).slice(0, 7).map(s => `<li><span class="hx-serifp">${esc(s.say)}</span>${s.look?.kind && s.look.kind !== 'none' ? `<small>${esc(LOOK[s.look.kind] || '')}${s.needs ? ' · needs your numbers' : ''}</small>` : ''}</li>`).join('')}</ol>`}
      <div class="hx-facts"><span>${ic('user', 14)}${esc(f ? f.name : 'No face')}</span><span>${ic('mic', 14)}${esc(voiceName(it.voice))}</span><span>${ic('bolt', 14)}${esc(e ? e.label : '')}</span></div>
      ${pr.length && !ready ? `<ul class="hx-why">${pr.map(w => `<li>${esc(scrub(w))}</li>`).join('')}</ul>` : ''}
      <div id="hxJob-${esc(it.id)}">${making ? '<p class="hx-mut hx-sm">Making it…</p>' : ''}</div>
      ${ready ? `<div class="hx-acts"><button type="button" class="hx-btn s" data-a="dlv" data-id="${esc(it.id)}">${ic('dl', 14)}Download</button>
          <button type="button" class="hx-btn s" data-a="tr" data-id="${esc(it.id)}">${ic('globe', 14)}Translate</button>
          <button type="button" class="hx-btn s" data-a="dup" data-id="${esc(it.id)}">${ic('copy', 14)}Make a version</button></div>
          <p class="hx-hint">Made with AI: said in the video file too.</p>`
        : `<div class="hx-acts"><span class="hx-price hx-num">${esc(qn.line || '')}</span><span class="hx-grow"></span>
          <button type="button" class="hx-btn s" data-a="openp" data-id="${esc(it.id)}">Change</button>
          ${making ? `<button type="button" class="hx-btn s danger" data-a="stop" data-id="${esc(it.id)}">${ic('stop', 14)}Stop</button>`
            : `<button type="button" class="hx-btn s dark" data-a="make" data-id="${esc(it.id)}" data-k="${esc(qn.key || '')}"${pr.length ? ' disabled' : ''}>Make the video</button>`}</div>`}</div>`;
  }
  function thread() {
    const items = [...C.items].reverse();
    const out = [];
    let it = 0;
    const rows = C.rows.filter(r => r.role === 'user' || r.role === 'assistant');
    rows.forEach(r => {
      while (it < items.length && Date.parse(items[it].created) <= Date.parse(r.at)) out.push(planCard(items[it++]));
      out.push(r.role === 'user' ? `<div class="hx-me">${esc(strip(r.text))}</div>` : `<div class="hx-ho">${esc(r.text).replace(/\n/g, '<br>')}</div>`);
    });
    while (it < items.length) out.push(planCard(items[it++]));
    if (C.sending || (Date.now() < C.waitUntil && rows[rows.length - 1]?.role === 'user')) out.push(`<div class="hx-working"><span class="hx-mark s">${markSvg()}</span><span>Planning the video…</span></div>`);
    return out.join('');
  }
  function paintChat() { const t = $('#hxThread'); if (!t) return; const log = $('#hxLog'), atEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 80;
    t.innerHTML = thread(); fillMedia(); if (atEnd) log.scrollTop = log.scrollHeight; C.items.filter(i => i.status === 'making').forEach(i => watchJob(i.id)); }
  async function chatSend(textIn) {
    const text = String(textIn ?? $('#hxAsk')?.value ?? C.ask).trim();
    if (!text) { $('#hxAsk')?.focus(); toast('Say what the video should say first.'); return; }
    if (!C.conv) await openChat(); if (!C.conv) return;
    C.sending = true; C.ask = ''; const ta = $('#hxAsk'); if (ta) ta.value = '';
    C.rows.push({role: 'user', text, at: new Date().toISOString()});
    if ($('.hx-hero')) draw(); else paintChat();
    try {
      await api('POST', `/api/conversations/${q(C.conv)}/messages`, {text: `${text}\n\n${settingsNote()}`, client_id: 'ix' + Date.now().toString(36)});
      C.waitUntil = Date.now() + 180000;
    } catch (e) { toast(e.message, true); C.ask = text; }
    C.sending = false; await chatLoad(); paintChat(); chatPoll();
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
    return `<ol class="hx-steps">${j.steps.filter(s => s.k !== 'done' && (s.k !== 'face' || (j.engine && j.engine !== 'hoola'))).map(s => {
      const done = s.at != null && s.k !== j.current, now = s.k === j.current && !j.done;
      return `<li class="${done ? 'ok' : now ? 'now' : ''}">${done ? ic('check', 14) : now ? '<span class="hx-spin" aria-hidden="true"></span>' : '<span class="hx-dot"></span>'}
        <span>${esc(s.label)}</span>${s.detail ? `<small>${esc(scrub(s.detail))}</small>` : ''}</li>`; }).join('')}</ol>
      <div class="hx-acts"><span class="hx-mut hx-sm hx-num">${secs(j.elapsed)}${j.credits ? ' · ' + cr(j.credits) : ''}</span><span class="hx-grow"></span>
      ${j.done ? '' : `<button type="button" class="hx-btn s danger" data-a="stop" data-id="${esc(j.pid)}">${ic('stop', 14)}Stop</button>`}</div>
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
      if (fresh()) return `<div class="hx-hero"><div class="hx-herob"><span class="hx-mark l" aria-hidden="true">${markSvg()}</span>
          <h2 class="hx-serif">What should your video say?</h2>
          <p class="hx-mut">Any language. Your face, your voice, the engine you choose, and the price before anything is made.</p>
          ${composer()}<div class="hx-ideas">${IDEAS.map((t, i) => `<button type="button" class="hx-chip" data-a="idea" data-n="${i}">${esc(t)}</button>`).join('')}</div></div>
          <section class="hx-railw" aria-label="Your videos"><b class="hx-t">Your videos</b><div class="hx-rail">${vidsRail()}</div></section></div>`;
      return `<div class="hx-split"><div class="hx-chat"><div class="hx-log" id="hxLog"><div id="hxThread">${thread()}</div></div>${composer()}</div>
        <aside class="hx-stage hx-side2" aria-label="Your videos"><div class="hx-stageb"><b class="hx-t">Your videos</b>${vidsRail()}</div></aside></div>`;
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
    chat() { (C.conv ? Promise.resolve() : openChat()).then(chatLoad).then(() => { if (PAGE !== 'chat') return; if ($('.hx-hero') && !fresh()) draw(); else paintChat(); chatPoll(); }); },
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
  function pickMenu(el, k, onPick) {
    const cbs = v => () => onPick(v);
    if (k === 'face') return menu(el, [{label: 'No face', checked: !SET.face, run: cbs('')}, ...(D.avatars || []).map(a => ({label: a.name, sub: 'Consent on record', checked: SET.face === a.id, run: cbs(a.id)})),
      {sep: true}, {label: 'Add a face', icon: 'plus', run: () => go('avatars')}]);
    if (k === 'voice') { const Vv = UI.V || {mine: [], library: []};
      return menu(el, [{search: 'Find a voice', empty: 'No voice matches'}, {label: 'Hoola picks', checked: !SET.voice, run: cbs('')}, ...(Vv.mine.length ? [{header: 'Your voices'}] : []),
        ...Vv.mine.map(v => ({label: v.name, sub: 'Your own', disabled: !v.ready, run: cbs(v.id)})), {header: 'Ready-made'},
        ...Vv.library.slice(0, 120).map(v => ({label: v.name, sub: [v.gender, v.tier === 'premium' ? 'Premium' : ''].filter(Boolean).join(' · '), disabled: !v.ready, run: cbs(v.id)}))], {width: 300}); }
    if (k === 'engine') return menu(el, (D.engines?.engines || []).filter(e => e.job === 'video').map(e => ({label: e.label, sub: e.ready ? e.price : scrub(e.status), disabled: !e.ready, checked: defEngine() === e.id, run: cbs(e.id)})), {width: 300});
    if (k === 'lang') return menu(el, [{search: 'Find a language', empty: 'No language matches'}, ...(UI.L || []).map(l => ({label: l.native && l.native !== l.name ? `${l.name} · ${l.native}` : l.name, sub: l.region, run: cbs(l.code)}))], {width: 280});
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
      case 'newchat': C.conv = ''; C.rows = []; C.items = []; await openChat(true); return go('chat');
      case 'chats': { let list = []; try { list = (await api('GET', `${C0}/chats`)).chats || []; } catch (er) { return toast(er.message, true); }
        return menu(b, list.length ? list.map(c => ({label: c.title, sub: ago(c.at), run: async () => { C.conv = c.id; C.title = c.title; C.rows = []; C.items = []; await chatLoad(); go('chat'); }})) : [{note: 'No earlier chats yet.'}], {align: 'end', width: 300}); }
      case 'send': return chatSend();
      case 'idea': { C.ask = IDEAS[+b.dataset.n]; const t = $('#hxAsk'); if (t) { t.value = C.ask; t.focus(); } $('.hx-send')?.classList.add('on'); return; }
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
        return pickMenu(b, map[k], v => save({[k]: v})); }
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
      case 'lpick': { const k = b.dataset.k; return pickMenu(b, k, v => { const i = $(`#hxLiveF [name="${k}"]`); if (i) i.value = v; b.querySelector('span').textContent = k === 'lang' ? langName(v) : voiceName(v); }); }
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
