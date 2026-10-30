/* v0.259 Hoola CREATE STUDIO (owner: "WHEN CLICK ON CREATE IT MUST LAND ON THIS PAGE DESIGN ... CREATE WILL GIVE USER
   VIDEO GENERATION ..., IMAGE GENERATION ..., HIGH END VIDEO EDITOR, MUSIC STUDIO, AI DUBBING ENGINE ... INSIDE IT VARIOUS
   CATEGORIES DIRECTOR, SCRIPT WRITER, AI CASTING", then "BUILD" on the prototype).
   OpenArt's layout and flow in Hoola's brand: the studio takes the whole screen with its own sidebar (Agents, Tools,
   Assets, Inspire), every tool is a settings panel on the left and her results on the right. It lives in a shadow root,
   so its class names never meet the console's; the console's colour tokens flow in (Light / Dark / System).
   Every button reaches a real engine - nothing here is pretend:
     Image / Casting  -> POST /api/create/jobs (photo_banao's engine; a cast is a four-view character sheet)
     Music / Voice    -> POST /api/create/jobs (Google Lyria song; Gemini voices)    lyrics + scripts -> /api/create/write
     Dubbing          -> POST /api/create/jobs kind=dub (her uploaded video; matched voices, original sound kept under)
     Video / Director -> the Video Studio API (/api/studio): storyboard, pictures, free preview, paid shots behind a price
                         card she taps here (money cards keep her phone's fingerprint rule: HTTP 428), music, final video
     Editor           -> the Video Editor API (/api/video/jobs): her clips in order + what to do, revisions by words
   Finished files stay on her Create shelf (/api/create/items) and also arrive in the open chat as cards. */
'use strict';
window.HoolaCreate = ctx => {
  const {api, esc, toast} = ctx;
  let host = null, R = null;            // the shadow root
  let VIEW = '', poll = 0, alive = 0;   // alive: bumps on every render so late answers from an old page are dropped
  const urls = new Map();               // her files as blob: URLs (they need her login), revoked on reset
  const blobs = new Map();              // the same files as Blobs (the waveform reads them; CSP keeps fetch() off blob: URLs)
  const $ = (s, r = R) => r.querySelector(s);
  const $$ = (s, r = R) => [...r.querySelectorAll(s)];
  const I = (n, st = '') => `<svg class="ic" style="${st}" aria-hidden="true"><use href="#i-${n}"/></svg>`;
  const inr = n => '₹' + Math.round(Number(n) || 0).toLocaleString('en-IN');
  const when = t => { const d = new Date((t || 0) * 1000), s = (Date.now() - d) / 1000;
    return s < 60 ? 'Just now' : s < 3600 ? Math.floor(s / 60) + ' min ago' : s < 86400 ? Math.floor(s / 3600) + ' h ago' : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
  const fp = 'This card spends money: Haan needs your phone’s fingerprint. Approve it in the Hoola app.';

  /* ---------------- decorative artwork (quick starts and templates only; her results are always her real files) ---------------- */
  function rng(seed) {   // v0.304 FNV-1a + a mix: neighbouring seeds ('q0', 'q1'...) used to land on the same palette
    let s = 2166136261; for (const c of String(seed)) { s ^= c.charCodeAt(0); s = Math.imul(s, 16777619) >>> 0; }
    s ^= s >>> 15; s = Math.imul(s, 2246822519) >>> 0; s ^= s >>> 13; s >>>= 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
  const PAL = [['#FF9A62','#C2417A','#2B1B54'],['#7FD1C7','#2F6F8F','#13233F'],['#FFD27A','#E2603C','#5B1E3F'],['#B7A6FF','#6C4BD8','#1E1646'],['#9BE3A4','#2E8A6B','#0F2D2A'],['#F6B7C8','#B4537A','#3A1630'],['#FFE2A8','#D98E3B','#3B2412'],['#A9D2FF','#4D74D6','#16234A']];
  function paint(cv) {
    const kind = cv.dataset.art, r = rng(cv.dataset.seed || kind);
    const dpr = Math.min(devicePixelRatio || 1, 2), w = Math.max(40, cv.clientWidth), h = Math.max(30, cv.clientHeight);
    cv.width = w * dpr; cv.height = h * dpr; const x = cv.getContext('2d'); x.scale(dpr, dpr);
    const p = PAL[Math.floor(r() * PAL.length)];
    const g = x.createLinearGradient(0, 0, w * .3, h); g.addColorStop(0, p[0]); g.addColorStop(.55, p[1]); g.addColorStop(1, p[2]);
    x.fillStyle = g; x.fillRect(0, 0, w, h);
    const blob = (cx, cy, rad, col, a) => { const rg = x.createRadialGradient(cx, cy, 0, cx, cy, rad); rg.addColorStop(0, col); rg.addColorStop(1, 'transparent'); x.globalAlpha = a; x.fillStyle = rg; x.fillRect(0, 0, w, h); x.globalAlpha = 1; };
    if (kind === 'film' || kind === 'city' || kind === 'world') {
      blob(w * (.2 + r() * .6), h * .35, Math.max(w, h) * .45, p[0], .8);
      x.fillStyle = 'rgba(255,240,210,.92)'; x.beginPath(); x.arc(w * (.25 + r() * .5), h * (.32 + r() * .12), Math.min(w, h) * (.08 + r() * .05), 0, 7); x.fill();
      for (let l = 0; l < 3; l++) {
        x.fillStyle = `rgba(10,8,30,${.25 + l * .22})`; x.beginPath(); x.moveTo(0, h);
        const base = h * (.55 + l * .12);
        if (kind === 'city' && l === 2) { let xx = 0; while (xx < w) { const bw = w * (.05 + r() * .08), bh = h * (.1 + r() * .35); x.rect(xx, base - bh, bw, h); xx += bw + 2; } x.fill(); continue; }
        for (let i = 0; i <= 8; i++) x.lineTo(w * i / 8, base - r() * h * .18);
        x.lineTo(w, h); x.fill();
      }
    } else if (kind === 'portrait' || kind === 'cast') {
      blob(w * .7, h * .2, w * .9, p[0], .7);
      const cx = w * (.42 + r() * .16), cy = h * .42, hr = Math.min(w, h) * .19;
      x.fillStyle = 'rgba(15,10,25,.55)'; x.beginPath(); x.ellipse(cx, h * 1.02, hr * 2.1, h * .38, 0, 0, 7); x.fill();
      x.fillStyle = ['#E8B796','#C98E6B','#A86B4C','#8A5538','#F1CBAE'][Math.floor(r() * 5)]; x.beginPath(); x.ellipse(cx, cy, hr * .82, hr, 0, 0, 7); x.fill();
      x.fillStyle = ['#1B120E','#3A2418','#0F0B10','#5A3A22'][Math.floor(r() * 4)];
      x.beginPath(); x.ellipse(cx, cy - hr * .45, hr * .92, hr * .62, 0, Math.PI, 0); x.fill();
      blob(cx - hr * .3, cy - hr * .3, hr * 1.2, 'rgba(255,255,255,.35)', .5);
    } else if (kind === 'product') {
      blob(w * .5, h * .55, w * .6, 'rgba(255,255,255,.55)', .6);
      const bw = w * .2, bx = w * .5 - bw / 2, by = h * .28, bh = h * .52;
      const bg = x.createLinearGradient(bx, 0, bx + bw, 0); bg.addColorStop(0, p[2]); bg.addColorStop(.5, p[1]); bg.addColorStop(1, p[2]);
      x.fillStyle = bg; x.beginPath(); x.roundRect(bx, by, bw, bh, 10); x.fill();
      x.fillStyle = p[0]; x.fillRect(bx + bw * .3, by - h * .07, bw * .4, h * .08);
      x.fillStyle = 'rgba(255,255,255,.85)'; x.fillRect(bx + bw * .12, by + bh * .4, bw * .76, bh * .18);
    } else if (kind === 'music') {
      const cx = w * .5, cy = h * .5, R2 = Math.min(w, h) * .38;
      x.fillStyle = '#0e0b16'; x.beginPath(); x.arc(cx, cy, R2, 0, 7); x.fill();
      for (let i = 1; i < 9; i++) { x.strokeStyle = `rgba(255,255,255,${.04 + i * .01})`; x.beginPath(); x.arc(cx, cy, R2 * i / 9, 0, 7); x.stroke(); }
      const lg = x.createLinearGradient(cx - R2, 0, cx + R2, 0); lg.addColorStop(0, p[0]); lg.addColorStop(1, p[1]);
      x.fillStyle = lg; x.beginPath(); x.arc(cx, cy, R2 * .32, 0, 7); x.fill();
    } else if (kind === 'wave' || kind === 'voice') {
      x.fillStyle = 'rgba(255,255,255,.85)';
      const n = Math.floor(w / 6); for (let i = 0; i < n; i++) { const a = (Math.sin(i * .35 + r() * 3) * .5 + .5) * (.3 + r() * .7); const bh = Math.max(3, a * h * .6); x.beginPath(); x.roundRect(i * 6 + 2, h / 2 - bh / 2, 3, bh, 2); x.fill(); }
    } else {
      for (let i = 0; i < 5; i++) blob(w * r(), h * r(), Math.max(w, h) * (.25 + r() * .4), p[Math.floor(r() * 3)], .75);
    }
  }
  // v0.304 a shape button draws its shape; a rail scrolls sideways with arrows (no orphan card on its own row)
  const ratioI = a => { const [w, h] = a.split(':').map(Number), k = 16 / Math.max(w, h); return `<i class="rbox" style="width:${Math.round(w * k)}px;height:${Math.round(h * k)}px" aria-hidden="true"></i>`; };
  const rail = (inner, cls) => `<div class="rail"><button type="button" class="rarr prev" data-rail="-1" aria-label="Scroll back">${I('down', 'width:16px;height:16px;transform:rotate(90deg)')}</button><div class="${cls} rtrack">${inner}</div><button type="button" class="rarr next" data-rail="1" aria-label="Scroll on">${I('down', 'width:16px;height:16px;transform:rotate(-90deg)')}</button></div>`;
  const art = (kind, seed, extra = '') => `<canvas class="art" data-art="${kind}" data-seed="${esc(seed)}" aria-hidden="true" ${extra}></canvas>`;
  const paintAll = (root = R) => requestAnimationFrame(() => $$('canvas[data-art]', root).forEach(c => { if (c.clientWidth) paint(c); }));

  /* ---------------- her files ---------------- */
  async function blobURL(path) {
    if (urls.has(path)) return urls.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const b = await r.blob(); const u = URL.createObjectURL(b);
    urls.set(path, u); blobs.set(path, b); return u;
  }
  const itemPath = id => `/api/create/items/${encodeURIComponent(id)}`;
  // fill every [data-src] (an authenticated path) inside root with its blob: URL
  function hydrate(root = R) {
    const n = alive;
    $$('[data-src]', root).forEach(async el => {
      const p = el.dataset.src; el.removeAttribute('data-src');
      try { const u = await blobURL(p); if (n === alive || el.isConnected) { el.src = u; if (el.tagName === 'AUDIO') wave(el, blobs.get(p)); } }
      catch { el.replaceWith(Object.assign(document.createElement('span'), {className: 'gone', textContent: 'File not available'})); }
    });
  }
  async function download(path, name) {
    try { const u = path.startsWith('/api/create/') ? await blobURL(path) : path;
      const a = document.createElement('a'); a.href = u; a.download = name || 'hoola'; a.rel = 'noopener'; R.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); }
  }
  async function convId() {
    let c = ctx.conv(); if (c) return c;
    c = await ctx.newConv(); return c;
  }
  async function upload(file, accept) {
    if (file.size > 25 * 1024 * 1024) throw new Error(`${file.name}: up to 25 MB`);
    if (accept && !accept.test(file.type)) throw new Error(`${file.name}: this file type is not supported here`);
    const fd = new FormData(); fd.append('file', file, file.name);
    const r = await api('POST', `/api/conversations/${encodeURIComponent(await convId())}/files`, undefined, {form: fd});
    return {file_id: r.file_id, name: file.name, type: file.type, size: file.size, local: URL.createObjectURL(file)};
  }
  function pick(accept, multiple) {
    return new Promise(res => { const i = document.createElement('input'); i.type = 'file'; i.accept = accept; i.multiple = !!multiple;
      i.onchange = () => res([...i.files]); i.click(); });
  }

  /* ---------------- data ---------------- */
  const D = {conf: null, studio: null, items: null, kit: null, jobs: new Map()};
  async function load(what, force) {
    try {
      if (what === 'conf' && (force || !D.conf)) D.conf = await api('GET', '/api/create');
      if (what === 'studio' && (force || !D.studio)) D.studio = await api('GET', '/api/studio');
      if (what === 'items' && (force || !D.items)) D.items = (await api('GET', '/api/create/items')).items || [];
      if (what === 'kit' && (force || !D.kit)) D.kit = await api('GET', '/api/brand/kit');
    } catch (e) { if (what === 'items') D.items = D.items || []; if (what === 'studio') D.studio = D.studio || {projects: [], available: false, models: []}; if (what === 'conf') D.conf = D.conf || {ready: {}, voices: {male: {}, female: {}}}; }
    return D[what];
  }
  const items = kind => (D.items || []).filter(i => !kind || (Array.isArray(kind) ? kind.includes(i.kind) : i.kind === kind));

  // a Create job: start, then follow it; the page that asked re-renders its result area on every change
  async function startJob(body, onChange) {
    const conversation_id = await convId().catch(() => '');
    const j = await api('POST', '/api/create/jobs', {...body, conversation_id});
    D.jobs.set(j.id, j); onChange?.();
    const follow = async () => {
      try { const x = await api('GET', `/api/create/jobs/${encodeURIComponent(j.id)}`); D.jobs.set(j.id, x);
        if (x.status === 'running') { setTimeout(follow, 2500); onChange?.(); return; }
        if (x.status === 'done') { await load('items', true); toast(`${x.title}: ready`); }
        else toast(x.error || 'It did not work', true);
        onChange?.();
      } catch (e) { const x = D.jobs.get(j.id); if (x) { x.status = 'failed'; x.error = e.message; } onChange?.(); }
    };
    setTimeout(follow, 2500);
    return j;
  }
  const running = kind => [...D.jobs.values()].filter(j => j.status === 'running' && (!kind || [].concat(kind).includes(j.kind)));
  const failed = kind => [...D.jobs.values()].filter(j => j.status === 'failed' && !j.seen && [].concat(kind).includes(j.kind));

  /* ---------------- shell ---------------- */
  const NAV = [
    ['l', 'Studio'], ['studio', 'Studio home', 'home'],
    ['l', 'Agents'], ['a', 'director', 'Director', 'Brief to finished film', 'clap', 'linear-gradient(135deg,#EE8F35,#B347E6)'],
    ['a', 'script', 'Script writer', 'Ads, films, episodes', 'pen', 'linear-gradient(135deg,#6E55F0,#2F6F8F)'],
    ['a', 'casting', 'AI casting', 'Characters that stay the same', 'cast', 'linear-gradient(135deg,#C2417A,#6E55F0)'],
    ['l', 'Tools'], ['t'],
    ['l', 'Assets'], ['projects', 'Film projects', 'folder'], ['brand', 'Brand kit', 'brand'], ['library', 'My creations', 'lib'],
    ['l', 'Inspire'], ['templates', 'Templates', 'tpl'], ['learn', 'How-to guides', 'book'],
    ['l', 'Setup'], ['engines', 'Engines', 'sliders'],
  ];
  const TOOLS = [['video','Video','video'],['image','Image','image'],['music','Music','music'],['voice','Voice','mic'],['dubbing','Dubbing','dub'],['editor','Editor','cut']];
  const TITLE = {engines:'Engines', studio:'Studio home', video:'Video', image:'Image', music:'Music studio', voice:'Voice studio', dubbing:'Dubbing', editor:'Video editor', director:'Director', script:'Script writer', casting:'AI casting', templates:'Templates', library:'My creations', projects:'Film projects', brand:'Brand kit', learn:'How-to guides'};
  function shellHTML() {
    return `<link rel="stylesheet" href="/static/console/studio.css?v=${esc(ctx.version || '')}">
<div id="shell">
  <aside class="side" aria-label="Create studio">
    <div class="shd"><div class="mark"><img class="av" src="${esc(ctx.avatar?.() || '/static/santosh-head.png')}" alt=""><span>Hoola</span><small>Studio</small></div>
      <button class="ib" id="collapse" aria-label="Collapse sidebar">${I('side')}</button></div>
    <button class="back" data-close>${I('left', 'width:16px;height:16px')}<span>Back to chat</span></button>
    <nav class="snav" id="snav"></nav>
    <div class="credits" id="credits"></div>
  </aside>
  <main class="main">
    <div class="top">
      <button class="ib menuBtn" id="menuBtn" aria-label="Open menu">${I('menu')}</button>
      <div class="crumb" id="crumb"></div>
      <button class="pillbtn" data-close>${I('chat', 'width:15px;height:15px')}<span>Chat</span></button>
      <button class="pillbtn" data-go="library">${I('lib', 'width:15px;height:15px')}<span>My creations</span></button>
    </div>
    <div class="view" id="view"></div>
  </main>
</div>
<div class="pop" id="pop" role="menu" hidden></div>
<div class="picker" id="picker" hidden></div>
<div class="lightbox" id="lightbox" hidden></div>
${SPRITE}`;
  }
  function drawNav() {      // v0.306 each row carries --i so the sidebar fades in top to bottom once, when the studio opens
    let i = 0; const st = () => ` style="--i:${i++}"`;
    $('#snav').innerHTML = NAV.map(n => {
      if (n[0] === 'l') return `<div class="sl"${st()}>${n[1]}</div>`;
      if (n[0] === 'a') return `<button class="agent" data-go="${n[1]}"${st()}><span class="ai" style="background:${n[5]}">${I(n[4], 'width:16px;height:16px')}</span><div style="min-width:0;flex:1"><b>${n[2]}</b><small>${n[3]}</small></div><span class="ago" aria-hidden="true">${I('down', 'width:14px;height:14px;transform:rotate(-90deg)')}</span></button>`;
      if (n[0] === 't') return `<div class="tgrid"${st()}>${TOOLS.map(([k, t, ic]) => `<button class="tg" data-go="${k}">${I(ic, 'width:16px;height:16px')}<span>${t}</span></button>`).join('')}</div>`;
      return `<button class="sn" data-go="${n[0]}"${st()}>${I(n[2])}<span>${n[1]}</span></button>`;
    }).join('');
  }
  function drawCredits() {
    const s = D.studio, el = $('#credits'); if (!el) return;
    if (!s || !s.month_limit_usd) { el.innerHTML = '<span class="mut">Your AI spend is in Account</span>'; return; }
    const k = s.usd_inr || 85, used = (s.month_spent_usd || 0) * k, lim = s.month_limit_usd * k;
    const pct = Math.min(100, used / lim * 100);   // v0.306 the meter fills from empty, and says how much is used
    el.innerHTML = `<div class="crow1"><span class="mut">Video Studio</span><b class="num">${inr(used)} <span class="dim">/ ${inr(lim)}</span></b></div><div class="bar"><i style="width:0%"></i></div><small class="dim">${pct < 1 && used > 0 ? '<1' : Math.round(pct)}% of this month’s limit used</small>`;
    requestAnimationFrame(() => requestAnimationFrame(() => { const b = el.querySelector('.bar i'); if (b) b.style.width = pct.toFixed(1) + '%'; }));
  }
  function go(v, opts) {
    if (!V[v]) v = 'studio';
    clearTimeout(poll); poll = 0; alive++; closeMenu(); if (!$('#picker').hidden) { $('#picker').hidden = true; $('#picker').innerHTML = ''; }
    VIEW = v; const old = $('#view'), el = old.cloneNode(false); old.replaceWith(el);
    el.className = 'view enter'; el.innerHTML = V[v](opts || {}); el.scrollTop = 0;
    $$('#snav [data-go]').forEach(b => b.setAttribute('aria-current', b.dataset.go === v ? 'page' : 'false'));
    $('#crumb').innerHTML = v === 'studio' ? '<b>Create</b>' : `Create · <b>${TITLE[v]}</b>`;
    $('#shell').classList.remove('navon');
    (W[v] || (() => {}))(el, opts || {}); paintAll(el); hydrate(el);
    try { sessionStorage.setItem('hoola.create.view', v); } catch {}
  }
  const V = {}, W = {};
  const redraw = (v, fn) => { if (VIEW === v) fn(); };
  const empty = (title, line, cta = '') => `<div class="empty"><div><h2>${title}</h2><p class="mut">${line}</p>${cta}</div></div>`;

  /* ---------------- v0.261 dropdown menus (owner: "WHEN CLICK ON DIRECTOR IT MUST OPEN DROPDOWN PROPERLY AND SMOOTHLY") ----------------
     One popover for every picker: anchored under its button (above when there is no room), fades + slides in, the
     current choice ticked, Arrow keys / Home / End / Enter / Esc, closes on a pick, an outside click, scroll or resize. */
  let popFor = null;
  function closeMenu(focus) {
    const pop = $('#pop'); if (!pop || pop.hidden) return;
    pop.classList.remove('on'); popFor?.setAttribute('aria-expanded', 'false');
    const b = popFor; popFor = null;
    setTimeout(() => { if (!popFor) { pop.hidden = true; pop.innerHTML = ''; } }, 160);
    if (focus) b?.focus();
  }
  // opts: [{v, label, sub?, icon?}]; cur: the current value; pick(v, opt) runs after the menu closes
  function menu(btn, opts, cur, pick, title) {
    const pop = $('#pop');
    if (popFor === btn) { closeMenu(true); return; }
    closeMenu(); popFor = btn;
    pop.innerHTML = (title ? `<div class="poph">${esc(title)}</div>` : '') + opts.map((o, i) => `<button type="button" role="menuitemradio" aria-checked="${String(o.v) === String(cur)}" data-i="${i}" tabindex="-1">${o.icon ? `<span class="pic">${I(o.icon, 'width:16px;height:16px')}</span>` : ''}<span class="ptx"><b>${esc(o.label)}</b>${o.sub ? `<small>${esc(o.sub)}</small>` : ''}</span><span class="tick">${I('check', 'width:15px;height:15px')}</span></button>`).join('');
    pop.hidden = false; pop.classList.remove('on');
    const r = btn.getBoundingClientRect(), w = Math.max(r.width, opts.some(o => o.sub) ? 280 : 200);
    pop.style.minWidth = w + 'px';
    const ph = pop.offsetHeight, below = innerHeight - r.bottom - 12, up = below < Math.min(ph, 320) && r.top > below;
    pop.style.maxHeight = Math.max(160, (up ? r.top : below) - 12) + 'px';
    pop.style.left = Math.max(8, Math.min(r.left, innerWidth - w - 8)) + 'px';
    pop.style.top = up ? '' : (r.bottom + 6) + 'px'; pop.style.bottom = up ? (innerHeight - r.top + 6) + 'px' : '';
    pop.classList.toggle('up', up);
    btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => pop.classList.add('on'));
    const items = $$('[role=menuitemradio]', pop);
    (items.find(x => x.getAttribute('aria-checked') === 'true') || items[0])?.focus({preventScroll: true});
    pop.onclick = e => { const b = e.target.closest('[data-i]'); if (!b) return; const o = opts[+b.dataset.i]; closeMenu(true); pick(o.v, o); };
    pop.onkeydown = e => {
      const i = items.indexOf(R.activeElement);
      const to = {ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: items.length - 1}[e.key];
      if (to !== undefined) { e.preventDefault(); items[(to + items.length) % items.length].focus(); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(true); }
      else if (e.key === 'Tab') closeMenu();
    };
  }
  addEventListener('resize', () => closeMenu());
  const opt = (L, fmt) => L.map(v => ({v, label: fmt ? fmt(v) : String(v)}));

  /* ---------------- shared result tiles ---------------- */
  function jobTile(j, tall) {
    return `<div class="res gening${tall ? ' tall' : ''}"><span class="thumb">${art(j.kind === 'song' ? 'music' : j.kind === 'voice' ? 'voice' : j.kind === 'dub' ? 'portrait' : 'abstract', j.id)}<span class="ring"></span><span class="pct">${j.step ? esc(j.step) : 'Making…'}</span></span><b class="rt">${esc(j.title)}</b><small>Hoola is working · stays here when you switch pages</small></div>`;
  }
  function failTile(j) {
    return `<div class="res failed"><span class="thumb"><span class="fail">${I('x', 'width:22px;height:22px')}<span>${esc(j.error || 'Did not work')}</span></span></span><b class="rt">${esc(j.title)}</b><small><button class="lnk" data-seen="${j.id}">Dismiss</button></small></div>`;
  }
  function itemTile(it, tall) {
    const media = it.mime.startsWith('image/') ? `<img alt="" data-src="${itemPath(it.id)}">`
      : it.mime.startsWith('video/') ? `<video muted playsinline preload="metadata" data-src="${itemPath(it.id)}"></video>`
      : `<span class="audio-ic">${I(it.kind === 'voice' ? 'mic' : 'music', 'width:28px;height:28px')}</span>`;
    return `<div class="res${tall ? ' tall' : ''}" data-item="${it.id}"><button class="thumb" data-open="${it.id}" aria-label="Open ${esc(it.title)}">${media}${it.mime.startsWith('video/') ? `<span class="badge">${I('play', 'width:11px;height:11px')}${esc(it.kind)}</span>` : ''}</button>
      <span class="acts"><button data-dl="${it.id}" aria-label="Download">${I('dl')}</button>${it.mime.startsWith('image/') ? `<button data-ref="${it.id}" aria-label="Use as a reference">${I('layers')}</button>` : ''}<button data-del="${it.id}" aria-label="Delete">${I('trash')}</button></span>
      <b class="rt">${esc(it.title)}</b><small>${when(it.created)}${it.meta?.model ? ' · ' + esc(it.meta.model) : ''}</small></div>`;
  }
  // the hover actions on result tiles, shared by every page that lists her creations
  async function itemAction(b) {
    const id = b.dataset.dl || b.dataset.del || b.dataset.open || b.dataset.ref; const it = (D.items || []).find(x => x.id === id); if (!it) return false;
    if (b.dataset.dl) { download(itemPath(id), it.title + '.' + (it.mime.split('/')[1] || 'bin').replace('mpeg', 'mp3').replace('x-wav', 'wav')); return true; }
    if (b.dataset.del) { if (!confirm(`Delete "${it.title}"? This cannot be undone.`)) return true;
      try { await api('DELETE', itemPath(id)); D.items = D.items.filter(x => x.id !== id); b.closest('[data-item]')?.remove(); toast('Deleted'); } catch (e) { toast(e.message, true); } return true; }
    if (b.dataset.ref) { IMG.refs = [...IMG.refs.filter(r => r.file_id !== id), {file_id: id, name: it.title, type: it.mime}].slice(0, 3); go('image'); toast('Added as a reference'); return true; }
    if (b.dataset.open) { lightbox(it); return true; }
    return false;
  }
  function lightbox(it) {
    const lb = $('#lightbox'); const p = itemPath(it.id);
    const m = it.mime.startsWith('image/') ? `<img alt="${esc(it.title)}" data-src="${p}">` : it.mime.startsWith('video/') ? `<video controls playsinline data-src="${p}"></video>`
      : it.mime.startsWith('audio/') ? `<audio controls data-src="${p}"></audio>` : `<pre class="lbtext">Open from My creations</pre>`;
    lb.innerHTML = `<div class="lbin" role="dialog" aria-modal="true" aria-label="${esc(it.title)}"><div class="lbh"><b>${esc(it.title)}</b><button class="pillbtn" data-dl="${it.id}">${I('dl', 'width:15px;height:15px')}Download</button><button class="ib" data-lbclose aria-label="Close">${I('x')}</button></div><div class="lbm">${m}</div>${it.meta?.description ? `<p class="mut lbp">${esc(it.meta.description)}</p>` : ''}</div>`;
    lb.hidden = false; hydrate(lb); $('[data-lbclose]', lb).focus();
  }

  /* ---------------- studio home ---------------- */
  const QUICK = [['Ad film','product','30 s','A 30-second ad film for my product: hook in 2 seconds, the product in use, happy customers, ends on the logo.'],
    ['Short film','film','3 min','A 3-minute short film: '],['Music video','music','2 min','A 2-minute music video for my song: '],
    ['Wedding film','portrait','60 s','A 60-second wedding highlights film: '],['Real estate tour','city','60 s','A 60-second walkthrough of a new flat: '],
    ['Product launch','product','45 s','A 45-second product launch film: '],['Micro drama','portrait','90 s','A 90-second micro drama episode with a twist: '],
    ['Festival greeting','abstract','20 s','A 20-second festival greeting video from my business: ']];
  const STARTERS = [['Diwali sale reel','video','abstract','A 15-second Diwali sale reel for my shop, diyas and fairy lights, warm gold light, 9:16'],
    ['Chai brand poster','image','product','A premium poster of a clay kulhad of masala chai on a wooden table, steam rising, warm morning light, space for a headline'],
    ['Monsoon road trip','video','film','A car on a wet ghat road in the monsoon, mist over green hills, cinematic drone shot'],
    ['Founder intro voice-over','voice','voice','Namaste! Main hoon aapki Newtika team ki founder. Hum chhote business ke liye AI banate hain.'],
    ['Saree lookbook','image','portrait','A fashion lookbook photo of a woman in a deep red Banarasi silk saree at a heritage haveli courtyard, soft daylight'],
    ['Lo-fi study beat','music','music','A calm lo-fi study beat with soft keys, rain sounds and a slow tabla groove'],
    ['Temple at dawn','image','world','A South Indian temple gopuram at dawn, mist, golden rim light, birds in the sky, ultra detailed'],
    ['Street food promo','video','product','Close-up of pav bhaji being made on a big tawa at a Mumbai street stall at night, sizzling butter, bokeh lights'],
    ['Festive jingle','music','music','A 30-second festive jingle for a sweet shop, shehnai and dhol, joyful'],
    ['Hinglish podcast intro','voice','voice','Hello doston, welcome back to Business Ki Baat, jahan hum chhote business ki badi kahaniyan sunte hain!']];
  const ALLTOOLS = [['video','Video generator','Words to video with the best model per shot','film','new'],['image','Image generator','Posters, product shots, characters','portrait',''],
    ['music','Music studio','Whole songs, instrumentals and jingles','music','new'],['voice','Voice studio','Voice-overs in 22 voices, Indian languages','voice',''],
    ['dubbing','Dubbing','Your video in another language','portrait','new'],['editor','Video editor','Your clips, edited by your words','film',''],
    ['director','Director','From a one-line brief to a finished film','city','hot'],['script','Script writer','Ads, short films and web episodes','abstract',''],
    ['casting','AI casting','Characters that look the same in every shot','cast','']];
  const AGENTS = [['director','Director','clap','A whole film: story, shots, music'],['image','Image','image','Posters, product shots, characters'],['video','Video','video','One clip from your words'],['music','Song','music','A full song or a jingle'],['voice','Voice-over','mic','Your script in any voice']];
  let homeAgent = 0;
  const MODE_HINT = {director: 'A 30-second Diwali ad for my chai brand, warm family moments, ends on our logo…',
    image: 'A premium poster of a clay kulhad of masala chai on a wooden table, steam rising, warm morning light…',
    video: 'Steam rising from a kulhad of chai on a rainy Mumbai balcony, slow dolly in, warm evening light…',
    music: 'A happy Bollywood-style jingle for my sweet shop, dhol and shehnai, 30 seconds…',
    voice: 'Namaste! Is Diwali, Newtika Chai laaya hai ek khaas offer…'};
  V.studio = () => `
<div class="home">
  <div class="hero">
    <span class="eyebrow">${I('spark', 'width:13px;height:13px')}Hoola Create</span>
    <h1>What shall we create today?</h1>
    <p class="hsub">Films, pictures, songs and voice-overs from one line. Every price shows before anything is spent.</p>
    <div class="modes" role="tablist" aria-label="What to make">${AGENTS.map(([, label, icon], i) => `<button type="button" role="tab" aria-selected="${i === homeAgent}" data-mode="${i}">${I(icon, 'width:15px;height:15px')}<span>${label}</span></button>`).join('')}</div>
    <form class="compose" id="homeForm">
      <label for="homeq" class="sr">Describe what to make</label>
      <textarea id="homeq" rows="2" placeholder="A 30-second Diwali ad for my chai brand, warm family moments, ends on our logo…"></textarea>
      <div class="crow">
        <button type="button" class="dd" id="homeAgent" aria-label="Who makes it">${I(AGENTS[homeAgent][2], 'width:15px;height:15px')}<span>${AGENTS[homeAgent][1]}</span>${I('down', 'width:14px;height:14px')}</button>
        <span class="sp"></span>
        <button class="send" aria-label="Start">${I('send')}</button>
      </div>
    </form>
    <div class="chips" style="justify-content:center">
      ${[['Make a product ad', 0], ['Write a song for my reel', 3], ['Design a film poster', 1], ['A voice-over for my shop', 4]].map(([c, a]) => `<button class="chip" data-fill="${esc(c)}" data-agent="${a}">${c}</button>`).join('')}
    </div>
  </div>
  <section><div class="sec-h"><h2>Direct your film</h2><a data-go="director">Open Director</a></div>
    ${rail(QUICK.map(([t, k, d], i) => `<button class="qcard" data-quick="${i}"><span class="thumb">${art(k, 'q' + i)}<span class="dur">${d}</span></span><b>${t}</b></button>`).join(''), 'qs')}</section>
  <section id="tools"><div class="sec-h"><h2>Studio tools</h2><span class="dim" style="font-size:13px">Every tool shares your cast and brand kit</span></div>
    <div class="tools">${ALLTOOLS.map(([v, t, s, k, tag], i) => `<button class="tool" data-go="${v}"><span class="thumb">${art(k, 't' + i)}</span><div style="min-width:0"><b>${t}${tag ? ` <span class="tag ${tag}">${tag === 'hot' ? 'Popular' : 'New'}</span>` : ''}</b><small>${s}</small></div></button>`).join('')}</div></section>
  <section><div class="sec-h"><h2>Your recent creations</h2><a data-go="library">See all</a></div><div class="row" id="recent"></div></section>
  <section><div class="sec-h"><h2>Start from a template</h2><a data-go="templates">See all</a></div>
    ${rail(STARTERS.map(([t, v, k], i) => `<button class="tpl" data-start="${i}"><span class="thumb">${art(k, 'tp' + i)}<span class="use">Use</span></span><b>${t}</b><small>${TITLE[v]}</small></button>`).join(''), 'row')}</section>
</div>`;
  function drawRecent() {
    const el = $('#recent'); if (!el) return;
    const its = items().slice(0, 10);
    el.innerHTML = its.length ? its.map(it => itemTile(it, true)).join('') : `<p class="mut" style="padding:8px 2px">Nothing yet. Everything you make here shows up in this row.</p>`;
    hydrate(el);
  }
  W.studio = el => {
    load('items').then(() => redraw('studio', drawRecent));
    const agent = i => { homeAgent = i; $('#homeAgent').innerHTML = `${I(AGENTS[i][2], 'width:15px;height:15px')}<span>${AGENTS[i][1]}</span>${I('down', 'width:14px;height:14px')}`;
      $$('[data-mode]', el).forEach(t => t.setAttribute('aria-selected', String(+t.dataset.mode === i)));
      $('#homeq').placeholder = MODE_HINT[AGENTS[i][0]] || ''; };
    $('#homeAgent', el).addEventListener('click', e => menu(e.currentTarget, AGENTS.map(([v, label, icon, sub]) => ({v, label, icon, sub})), AGENTS[homeAgent][0],
      v => { agent(AGENTS.findIndex(a => a[0] === v)); $('#homeq').focus(); }, 'Who makes it'));
    $('#homeForm', el).addEventListener('submit', e => {
      e.preventDefault(); const q = $('#homeq').value.trim(); if (!q) { $('#homeq').focus(); return; }
      const a = AGENTS[homeAgent][0];
      if (a === 'director') { DIR.brief = q; DIR.project = ''; go('director', {autostart: true}); }
      else if (a === 'image') { IMG.prompt = q; go('image', {autostart: true}); }
      else if (a === 'video') { VID.prompt = q; go('video', {autostart: true}); }
      else if (a === 'music') { MU.brief = q; go('music', {autostart: true}); }
      else { VO.text = q; go('voice', {autostart: true}); }
    });
    el.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.mode) { agent(+b.dataset.mode); $('#homeq').focus(); return; }
      if (b.dataset.rail) { const t = b.parentElement.querySelector('.rtrack'); t.scrollBy({left: +b.dataset.rail * t.clientWidth * .8, behavior: 'smooth'}); return; }
      if (b.dataset.fill) { agent(+b.dataset.agent); const t = $('#homeq'); t.value = b.dataset.fill + ': '; t.focus(); }
      if (b.dataset.quick) { const q = QUICK[+b.dataset.quick]; DIR.brief = q[3]; DIR.project = ''; DIR.seconds = parseInt(q[2]) * (q[2].includes('min') ? 60 : 1); go('director', {focus: true}); }
      if (b.dataset.start) starter(+b.dataset.start);
    });
  };
  function starter(i) {
    const [, v, , text] = STARTERS[i];
    if (v === 'video') VID.prompt = text; if (v === 'image') IMG.prompt = text; if (v === 'music') MU.brief = text; if (v === 'voice') VO.text = text;
    go(v);
  }

  /* ---------------- image ---------------- */
  const IMG = {prompt: '', refs: [], aspect: '1:1', quality: 'fast', count: 1, style: '', brand: false, avoid: ''};
  const STYLE_ART = {'': 'abstract', Photoreal: 'portrait', Cinematic: 'film', 'Festive glow': 'abstract', 'Product studio': 'product', Watercolour: 'world', Anime: 'cast', '3D clay': 'product', 'Indian folk art': 'city'};
  const STYLES = ['', 'Photoreal', 'Cinematic', 'Festive glow', 'Product studio', 'Watercolour', 'Anime', '3D clay', 'Indian folk art'];
  const ASPECTS = ['1:1', '4:5', '9:16', '16:9', '3:4', '4:3'];
  const imgCost = () => (IMG.quality === 'best' ? 12 : 3) * IMG.count;
  function toolTabs(k) { return `<div class="seg" role="group" aria-label="Studio">${TOOLS.slice(0, 5).map(([v, tt]) => `<button aria-pressed="${v === k}" data-go="${v}">${tt}</button>`).join('')}</div>`; }
  V.image = () => `<div class="gen">
  <div class="panel"><div class="pbody">
    ${toolTabs('image')}
    <div class="seg" role="group" aria-label="Kind"><button aria-pressed="${!IMG.refs.length}" data-imode="new">New picture</button><button aria-pressed="${!!IMG.refs.length}" data-imode="edit">Change my photo</button></div>
    <div class="prow"><span class="pi">${I('spark', 'width:16px;height:16px')}</span><div><small>Engine</small><b>Hoola image engine</b></div><span class="tag">Readable Indian scripts</span></div>
    <div class="box">
      <h3>Describe your picture <span class="dim num" style="font-size:12px;font-weight:400;margin-left:auto" id="imgCount">${IMG.prompt.length} / 4000</span><button type="button" class="lnk" data-ienh>${I('wand', 'width:14px;height:14px')} Enhance</button></h3>
      <button class="refs" type="button" data-addref><span class="stack">${IMG.refs.length ? IMG.refs.map(r => `<i><img alt="" ${r.local ? `src="${esc(r.local)}"` : `data-src="${itemPath(r.file_id)}"`}></i>`).join('') : `<i>${I('image', 'width:16px;height:16px;margin:10px 6px')}</i>`}</span><div><b>${IMG.refs.length ? IMG.refs.length + ' reference' + (IMG.refs.length > 1 ? 's' : '') : 'Add references'}</b> <span class="dim" style="font-size:12px">${IMG.refs.length ? '' : 'optional'}</span><small>Your photo, product or character · PNG, JPG, WebP · up to 3</small></div>${IMG.refs.length ? `<span class="ib" data-clearrefs aria-label="Remove references">${I('x', 'width:15px;height:15px')}</span>` : ''}</button>
      <textarea id="imgq" rows="5" maxlength="4000" placeholder="A festive Diwali poster for Newtika Chai: a clay kulhad with steam, diyas, marigold, headline 'Har shaam khaas' in Hindi">${esc(IMG.prompt)}</textarea>
      <div class="btool">
        <button class="ib" aria-label="Clear" data-iclear>${I('trash', 'width:16px;height:16px')}</button>
        <span style="flex:1"></span><span class="dim" style="font-size:12.5px">Brand colours</span><button class="sw" role="switch" aria-checked="${IMG.brand}" data-ibrand aria-label="Use my brand colours"><i></i></button>
      </div>
    </div>
    <div class="lbl">Style <span class="dim" style="margin-left:auto">${esc(IMG.style || 'Auto')}</span></div><div class="stys" role="group" aria-label="Style">${STYLES.map((st, i) => `<button class="sty" aria-pressed="${st === IMG.style}" data-isty="${i}"><span class="thumb">${art(STYLE_ART[st] || 'abstract', 'sty' + i)}</span><small>${st || 'Auto'}</small></button>`).join('')}</div>
    <div class="lbl">Shape</div><div class="grid-opts">${ASPECTS.map(a => `<button class="go shp" aria-pressed="${a === IMG.aspect}" data-iasp="${a}">${ratioI(a)}<span>${a}</span></button>`).join('')}</div>
    <div class="lbl">Quality</div><div class="grid-opts" style="grid-template-columns:1fr 1fr"><button class="go" aria-pressed="${IMG.quality === 'fast'}" data-iq="fast">Standard · ₹3</button><button class="go" aria-pressed="${IMG.quality === 'best'}" data-iq="best">Best · ₹12</button></div>
    <details class="adv"${IMG.avoid ? ' open' : ''}><summary>${I('down', 'width:14px;height:14px')}Advanced</summary>
      <label class="fld">Keep out of the picture<input id="iavoid" maxlength="300" value="${esc(IMG.avoid)}" placeholder="text errors, extra fingers, watermark, blur"></label></details>
    <p class="note">Every picture carries a small “AI se bana” label. Prices are estimates; the real cost shows in AI spend.</p>
  </div>
  <div class="pfoot">
    <div class="stepper"><button data-icount="-1" aria-label="Fewer">${I('minus', 'width:15px;height:15px')}</button><b class="num" style="min-width:34px;text-align:center" id="icount">${IMG.count} / 4</b><button data-icount="1" aria-label="More">${I('plus', 'width:15px;height:15px')}</button></div>
    <button class="create" id="imgGo">${I('spark', 'width:17px;height:17px')}Create <small class="num" id="imgCost">~₹${imgCost()}</small></button>
  </div></div>
  <div class="stage"><div class="sbar"><b>Your pictures</b><span class="sp"></span><button class="ib" data-reload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div>
    <div class="sgrid" id="results"></div></div></div>`;
  function drawResults(kinds, tall) {
    const el = $('#results'); if (!el) return;
    const its = items(kinds), jobs = running(kinds), bad = failed(kinds);
    el.innerHTML = jobs.map(j => jobTile(j, tall)).join('') + bad.map(failTile).join('') + its.map(it => itemTile(it, tall)).join('')
      || `<div class="empty" style="grid-column:1/-1"><div><h2>Your work appears here</h2><p class="mut">Describe it on the left and press Create.</p></div></div>`;
    paintAll(el); hydrate(el);
  }
  W.image = (el, o) => {
    const q = $('#imgq'); const refresh = () => redraw('image', () => drawResults(['image'], true));
    load('items').then(refresh);
    q.addEventListener('input', () => { IMG.prompt = q.value; $('#imgCount').textContent = q.value.length + ' / 4000'; });
    const cost = () => { $('#imgCost').textContent = '~₹' + imgCost(); $('#icount').textContent = IMG.count + ' / 4'; };
    const create = async () => {
      IMG.prompt = q.value.trim(); if (!IMG.prompt) { q.focus(); toast('Describe the picture first'); return; }
      let prompt = IMG.prompt;
      IMG.avoid = ($('#iavoid')?.value || '').trim(); if (IMG.avoid) prompt += `\nAvoid: ${IMG.avoid}.`;
      if (IMG.brand) { const k = await load('kit'); if (k?.colors) prompt += `\nUse these brand colours: primary ${k.colors.primary}, accent ${k.colors.accent}.${k.name ? ' Brand: ' + k.name + '.' : ''}`; }
      try { await startJob({kind: 'image', prompt, file_ids: IMG.refs.map(r => r.file_id), aspect: IMG.aspect, quality: IMG.quality, count: IMG.count, style: IMG.style, title: IMG.prompt.slice(0, 48)}, refresh); }
      catch (e) { toast(e.message, true); }
    };
    el.addEventListener('click', async e => {
      const b = e.target.closest('button,[data-clearrefs]'); if (!b) return;
      if (await itemAction(b)) return;
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; refresh(); return; }
      if (b.hasAttribute('data-clearrefs')) { e.stopPropagation(); IMG.refs = []; go('image'); return; }
      if (b.hasAttribute('data-addref') || b.dataset.imode === 'edit') {
        const fs = await pick('image/png,image/jpeg,image/webp', true);
        for (const f of fs.slice(0, 3 - IMG.refs.length)) { try { toast('Uploading ' + f.name); IMG.refs.push(await upload(f, /^image\/(png|jpeg|webp)$/)); } catch (er) { toast(er.message, true); } }
        IMG.prompt = q.value; go('image'); return; }
      if (b.dataset.imode === 'new') { IMG.refs = []; IMG.prompt = q.value; go('image'); return; }
      if (b.dataset.isty) { IMG.style = STYLES[+b.dataset.isty]; $$('[data-isty]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); const l = b.closest('.pbody').querySelector('.stys')?.previousElementSibling?.querySelector('.dim'); if (l) l.textContent = IMG.style || 'Auto'; return; }
      if (b.hasAttribute('data-ienh')) { if (!q.value.trim()) { q.focus(); toast('Write a few words first'); return; } b.disabled = true; b.classList.add('busy');
        try { const r = await api('POST', '/api/studio/improve', {brief: q.value.trim(), language: 'Hindi', seconds: 30, kind: 'image'}); q.value = IMG.prompt = r.brief; $('#imgCount').textContent = q.value.length + ' / 4000'; toast('Prompt enhanced: edit it or press Create'); } catch (er) { toast(er.message, true); }
        b.disabled = false; b.classList.remove('busy'); return; }
      if (b.hasAttribute('data-iclear')) { q.value = IMG.prompt = ''; q.focus(); return; }
      if (b.hasAttribute('data-ibrand')) { IMG.brand = !IMG.brand; b.setAttribute('aria-checked', String(IMG.brand)); return; }
      if (b.dataset.iasp) { IMG.aspect = b.dataset.iasp; $$('[data-iasp]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.iq) { IMG.quality = b.dataset.iq; $$('[data-iq]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); cost(); return; }
      if (b.dataset.icount) { IMG.count = Math.max(1, Math.min(4, IMG.count + +b.dataset.icount)); cost(); return; }
      if (b.hasAttribute('data-reload')) { await load('items', true); refresh(); return; }
      if (b.id === 'imgGo') create();
    });
    if (o.autostart) create();
  };

  /* ---------------- v0.262 EVERY MODEL, PRICE FIRST (owner: "IT MUST INCLUDE ALL MODEL IN IT LETS USER CHOOSE THE RIGHT ONE
     FOR THEM ... USER WILL SEE THE PRICING OF EVERY VIDEO BEFORE GENERATION"): the picker lists every model (ready ones, the
     ones a server key switches on, and the rest of the market) with its rupee price per second at every resolution and
     the price of THIS clip; the Create button carries the live price; every paid run still stops at the price card. */
  const RES = ['360p', '480p', '540p', '720p', '768p', '1080p', '2k', '4k'];
  const QOF = r => ({'360p': 'draft', '480p': 'draft', '540p': 'draft', '720p': 'draft', '768p': 'draft', '1080p': 'final', '2k': 'premium', '4k': 'premium'})[r] || 'final';
  async function models(force) {
    if (force || !D.models) { try { D.models = await api('GET', '/api/studio/models'); } catch { D.models = D.models || {models: [], not_offered: []}; } }
    return D.models;
  }
  const mOf = k => (D.models?.models || []).find(m => m.key && m.key === k);
  const resSort = L => [...new Set(L)].sort((a, b) => RES.indexOf(a) - RES.indexOf(b));
  function rateAt(m, res) {
    const t = m?.inr_per_s || {}; if (t[res] != null) return t[res];
    const ks = resSort(Object.keys(t)); if (!ks.length) return 0;
    return t[ks.find(k => RES.indexOf(k) >= RES.indexOf(res)) || ks[ks.length - 1]];
  }
  const topRes = m => resSort(m.resolutions || Object.keys(m.inr_per_s || {})).slice(-1)[0] || '';
  const money = n => '₹' + (n < 100 ? (Math.round(n * 10) / 10).toLocaleString('en-IN') : Math.round(n).toLocaleString('en-IN'));
  const TIERS = [['all', 'All models'], ['top', 'Top quality'], ['strong', 'Strong'], ['budget', 'Budget'], ['talk', 'Talking people']];
  const MP = {tier: 'all', only: false, sort: 'quality', feat: new Set(), q: '', cmp: [], view: 'grid', ctx: null};
  /* open the picker. ctx = {current, seconds, res, onPick(key), title, auto, onAuto(mode)?, onCompare(keys)?} */
  const AUTOS = [['quality', 'Best quality', 'The best ready model for each shot'], ['value', 'Best value', 'The cheapest of the 3 best for each shot'], ['cheap', 'Lowest price', 'The cheapest ready model']];
  async function picker(ctx) {
    MP.ctx = ctx; MP.view = 'grid'; MP.cmp = [];
    const pk = $('#picker'); pk.hidden = false; pk.innerHTML = `<div class="pkin"><p class="mut" style="padding:30px">Loading every model…</p></div>`;
    await models(); drawPicker(); requestAnimationFrame(() => pk.classList.add('on'));
  }
  function closePicker() { const pk = $('#picker'); pk.classList.remove('on'); setTimeout(() => { if (!pk.classList.contains('on')) { pk.hidden = true; pk.innerHTML = ''; } }, 180); }
  function pickerList() {
    const order = {top: 0, strong: 1, budget: 2, talk: 3};
    const c = MP.ctx, f = MP.feat, q = MP.q.toLowerCase();
    let L = (D.models?.models || []).filter(m => (MP.tier === 'all' || m.tier === MP.tier) && (!MP.only || m.ready)
      && (!f.has('sound') || m.audio) && (!f.has('4k') || topRes(m) === '4k') && (!f.has('long') || (m.durations?.[1] || 0) >= 20)
      && (!f.has('refs') || (m.references || 0) >= 4) && (!q || (m.name + ' ' + m.maker + ' ' + m.best).toLowerCase().includes(q)));
    const price = m => rateAt(m, c.res) * c.seconds;
    L.sort((a, b) => (b.ready - a.ready) || (MP.sort === 'price' ? price(a) - price(b) : MP.sort === 'long' ? (b.durations?.[1] || 0) - (a.durations?.[1] || 0)
      : (order[a.tier] ?? 9) - (order[b.tier] ?? 9) || (a.q ?? 99) - (b.q ?? 99)));
    return L;
  }
  function modelCard(m) {
    const c = MP.ctx, res = (m.resolutions || []).includes(c.res) || !m.resolutions?.length ? c.res : resSort(m.resolutions).find(r => RES.indexOf(r) >= RES.indexOf(c.res)) || topRes(m);
    const ps = rateAt(m, res), clip = ps * c.seconds, on = m.key && m.key === c.current, ck = MP.cmp.includes(m.name);
    const mine = (m.mine || []).length ? `<div class="mine"><small>Your clips with it</small><div>${m.mine.map(x => `<video muted playsinline preload="metadata" src="${esc(x.url)}" title="${esc(x.project)}"></video>`).join('')}</div></div>` : '';
    const st = m.status === 'ready' ? '' : m.status === 'coming' ? '<span class="tag">Coming</span>' : '<span class="tag hot">Not switched on</span>';
    return `<div class="mcard${on ? ' on' : ''}${m.ready ? '' : ' off'}">
      <div class="mh"><div><b>${esc(m.name)}</b><small>${esc(m.maker)}${m.via ? ' · via ' + esc(m.via) : ''}</small></div>${st}<label class="cmpck" title="Compare"><input type="checkbox" data-cmp="${esc(m.name)}" ${ck ? 'checked' : ''}><span>Compare</span></label></div>
      ${m.rank ? `<span class="rank">${I('star', 'width:13px;height:13px')}${esc(m.rank)}</span>` : ''}
      <p class="mbest">${esc(m.best)}</p>
      <div class="specs">${m.durations?.length ? `<span>${I('video', 'width:13px;height:13px')}up to ${m.durations[1]} s</span>` : ''}${topRes(m) ? `<span>${I('grid', 'width:13px;height:13px')}${topRes(m)}</span>` : ''}${m.audio ? `<span>${I('sound', 'width:13px;height:13px')}sound</span>` : ''}${m.references ? `<span>${I('layers', 'width:13px;height:13px')}${m.references} refs</span>` : ''}</div>
      ${mine}
      <div class="mprice"><div><b class="num">${money(ps)}</b><small>/ second at ${esc(res)}${m.estimate_only ? ' · about' : m.price_live ? ' · live price' : ''}</small></div><div><b class="num">${money(clip)}</b><small>for your ${c.seconds} s clip</small></div></div>
      ${m.ready ? `<button class="btn ${on ? 'sec' : 'pri'}" data-mpick="${esc(m.key)}">${on ? I('check', 'width:15px;height:15px') + 'Chosen' : 'Choose'}</button>` : `<p class="why">${esc(m.why)}</p>`}
    </div>`;
  }
  function drawPicker() {
    const pk = $('#picker'), c = MP.ctx; if (!pk || !c) return;
    const L = pickerList(), dm = D.models || {};
    const am = c.auto || 'quality';
    const auto = `<div class="mcard auto${!c.current ? ' on' : ''}"><div class="mh"><div><b>Hoola Auto</b><small>Recommended</small></div></div><p class="mbest">Hoola picks for each shot: scenes, products, talking people and Hindi lip sync. The price card shows which model and the exact price.</p>
      ${c.onAuto ? `<div class="amodes" role="radiogroup" aria-label="How Hoola Auto chooses">${AUTOS.map(([k, t, d]) => `<button role="radio" aria-checked="${k === am}" data-amode="${k}" title="${esc(d)}">${t}</button>`).join('')}</div><small class="mut">${esc(AUTOS.find(a => a[0] === am)[2])}</small>` : ''}
      <button class="btn ${!c.current ? 'sec' : 'pri'}" data-mpick="">${!c.current ? I('check', 'width:15px;height:15px') + 'Chosen' : 'Use Hoola Auto'}</button></div>`;
    const body = MP.view === 'compare' ? compareHTML() : `<div class="mgrid">${MP.tier === 'all' || MP.tier === 'top' ? auto : ''}${L.map(modelCard).join('') || '<p class="mut">No model matches these filters.</p>'}</div>
      ${(dm.not_offered || []).length ? `<p class="note" style="margin-top:14px">Not offered: ${dm.not_offered.map(x => `<b>${esc(x.name)}</b> (${esc(x.why)})`).join(' · ')}</p>` : ''}`;
    pk.innerHTML = `<div class="pkin" role="dialog" aria-modal="true" aria-label="Choose a video model">
      <div class="pkh"><div><h2>${esc(c.title || 'Choose a video model')}</h2><small class="mut">${(dm.models || []).filter(m => m.ready).length} ready · ${(dm.models || []).length} in the market list · prices for ${c.seconds} s at ${esc(c.res)}${dm.synced_at ? ' · live prices checked' : ' · prices checked ' + esc(dm.prices_checked || '')}</small></div>
        <label class="pks">${I('search', 'width:15px;height:15px')}<input id="pkq" placeholder="Search models" value="${esc(MP.q)}" aria-label="Search models"></label><button class="ib" data-pkclose aria-label="Close">${I('x')}</button></div>
      <div class="pkf"><div class="chips">${TIERS.map(([k, n]) => `<button class="chip" aria-pressed="${k === MP.tier}" data-tier="${k}">${n}</button>`).join('')}</div>
        <div class="chips">${[['sound', 'Sound'], ['4k', '4K'], ['long', '20 s or longer'], ['refs', '4+ references']].map(([k, n]) => `<button class="chip" aria-pressed="${MP.feat.has(k)}" data-feat="${k}">${n}</button>`).join('')}<button class="chip" aria-pressed="${MP.only}" data-only>Ready only</button>
        <button class="dd" data-sort>${I('filter', 'width:14px;height:14px')}<span>${{quality: 'Best quality first', price: 'Lowest price first', long: 'Longest clips first'}[MP.sort]}</span>${I('down', 'width:14px;height:14px')}</button></div></div>
      ${(dm.price_changes || []).length ? `<div class="pchg">${I('redo', 'width:14px;height:14px')}<span>Prices changed: ${dm.price_changes.slice(0, 3).map(x => `<b>${esc(x.name)}</b> ${esc(x.resolution)} ${money(x.old_usd * dm.usd_inr)} → ${money(x.new_usd * dm.usd_inr)}`).join(' · ')}${dm.price_changes.length > 3 ? ` · and ${dm.price_changes.length - 3} more` : ''}</span></div>` : ''}
      <div class="pkb">${body}</div>
      <div class="pkfoot"><span class="mut">${c.onCompare && MP.view !== 'compare' ? 'Tick 2 or 3 models and press Compare to make the same shot with each. ' : ''}${dm.note ? esc(dm.note) : ''}</span><span class="sp"></span>${MP.view === 'compare' ? `<button class="btn sec" data-pkgrid>Back to all models</button>` : `<button class="btn sec" data-pkcmp ${MP.cmp.length < 2 ? 'disabled' : ''}>Compare ${MP.cmp.length ? '(' + MP.cmp.length + ')' : ''}</button>`}</div></div>`;
    $('#pkq', pk)?.addEventListener('input', e => { MP.q = e.target.value; const y = $('.pkb', pk).scrollTop; drawPicker(); const i = $('#pkq', pk); i.focus(); i.setSelectionRange(i.value.length, i.value.length); $('.pkb', pk).scrollTop = y; });
  }
  function compareHTML() {
    const c = MP.ctx, L = MP.cmp.map(n => (D.models?.models || []).find(m => m.name === n)).filter(Boolean);
    const row = (t, f) => `<tr><th>${t}</th>${L.map(m => `<td>${f(m)}</td>`).join('')}</tr>`;
    return `<table class="cmp"><thead><tr><th></th>${L.map(m => `<th><b>${esc(m.name)}</b><small>${esc(m.maker)}</small></th>`).join('')}</tr></thead><tbody>
      ${row(`Your ${c.seconds} s clip at ${esc(c.res)}`, m => `<b class="num">${money(rateAt(m, c.res) * c.seconds)}</b>`)}
      ${row('Per second', m => money(rateAt(m, c.res)) + (m.estimate_only ? ' (about)' : ''))}
      ${row('Longest clip', m => m.durations?.length ? m.durations[1] + ' s' : '—')}
      ${row('Best resolution', m => topRes(m) || '—')}
      ${row('Sound', m => m.audio ? 'Yes' : 'No')}
      ${row('References', m => m.references || '—')}
      ${row('Ranking', m => esc(m.rank || '—'))}
      ${row('Best for', m => esc(m.best))}
      ${row('', m => m.ready ? `<button class="btn pri" data-mpick="${esc(m.key)}">Choose</button>` : `<span class="why">${esc(m.why)}</span>`)}</tbody></table>
      ${c.onCompare ? (L.filter(m => m.ready).length >= 2 ? `<div class="cmpgo"><div><b>Make it with ${L.filter(m => m.ready).length} models side by side</b><small>One price card: ${money(L.filter(m => m.ready).reduce((t, m) => t + rateAt(m, c.res) * c.seconds, 0))} for all of them. You keep the take you like.</small></div><button class="btn pri" data-cmpgo>${I('layers', 'width:15px;height:15px')}Make them side by side</button></div>` : '<p class="note">Pick at least 2 models that are switched on to make them side by side.</p>') : ''}`;
  }
  async function onPickerClick(e) {
    const b = e.target.closest('button,input'); const pk = $('#picker');
    if (e.target === pk) { closePicker(); return; }
    if (!b) return;
    if (b.dataset.cmp !== undefined) { const n = b.dataset.cmp; if (b.checked) { if (MP.cmp.length >= 3) { b.checked = false; toast('Compare up to 3 models'); return; } MP.cmp.push(n); } else MP.cmp = MP.cmp.filter(x => x !== n);
      const f = $('[data-pkcmp]', pk); if (f) { f.disabled = MP.cmp.length < 2; f.textContent = 'Compare' + (MP.cmp.length ? ` (${MP.cmp.length})` : ''); } return; }
    if (b.hasAttribute('data-pkclose')) { closePicker(); return; }
    if (b.dataset.tier) { MP.tier = b.dataset.tier; drawPicker(); return; }
    if (b.dataset.feat) { MP.feat.has(b.dataset.feat) ? MP.feat.delete(b.dataset.feat) : MP.feat.add(b.dataset.feat); drawPicker(); return; }
    if (b.hasAttribute('data-only')) { MP.only = !MP.only; drawPicker(); return; }
    if (b.hasAttribute('data-sort')) { menu(b, [{v: 'quality', label: 'Best quality first'}, {v: 'price', label: 'Lowest price first'}, {v: 'long', label: 'Longest clips first'}], MP.sort, v => { MP.sort = v; drawPicker(); }, 'Sort'); return; }
    if (b.hasAttribute('data-pkcmp')) { MP.view = 'compare'; drawPicker(); return; }
    if (b.hasAttribute('data-pkgrid')) { MP.view = 'grid'; drawPicker(); return; }
    if (b.dataset.amode) { MP.ctx.auto = b.dataset.amode; MP.ctx.onAuto?.(b.dataset.amode); drawPicker(); return; }
    if (b.hasAttribute('data-cmpgo')) { const keys = MP.cmp.map(n => (D.models?.models || []).find(m => m.name === n)).filter(m => m?.ready).map(m => m.key), cb = MP.ctx.onCompare; closePicker(); cb(keys); return; }
    if (b.dataset.mpick !== undefined) { const k = b.dataset.mpick, cb = MP.ctx.onPick; closePicker(); cb(k); }
  }

  /* ---------------- video (Video Studio, one clip per project) ---------------- */
  const CAMS = [['Auto', ''], ['Static', 'the camera holds still on a tripod'], ['Dolly in', 'slow dolly in towards the subject'], ['Pan', 'smooth slow pan across the scene'], ['Orbit', 'the camera orbits around the subject'], ['Drone', 'a high aerial drone shot moving forward'], ['Handheld', 'natural handheld camera, slight movement'], ['Slow motion', 'slow motion, smooth and dreamy']];
  const VID = {camera: 'Auto', prompt: '', aspect: '9:16', seconds: 8, res: '1080p', model: '', audio: true, takes: 1, language: 'Hindi', price: null, auto: 'quality', compare: []};
  const vm = () => mOf(VID.model);
  const lenOpts = m => { const a = m?.allowed_durations; if (a?.length) return a; const [lo, hi] = m?.durations?.length ? m.durations : [4, 30];
    return [4, 5, 6, 8, 10, 12, 15, 20, 25, 30].filter(x => x >= lo && x <= hi); };
  const resOpts = m => m ? resSort(m.resolutions || []) : ['480p', '720p', '1080p', '4k'];
  V.video = () => { const m = vm();
    return `<div class="gen">
  <div class="panel" style="position:relative"><div class="pbody">
    ${toolTabs('video')}
    <button class="prow" data-pickmodel><span class="pi">${I('spark', 'width:16px;height:16px')}</span><div><small>Model</small><b>${VID.compare.length ? VID.compare.map(k => esc(mOf(k)?.name || k)).join(' vs ') : m ? esc(m.name) : 'Hoola Auto · ' + {quality: 'best quality', value: 'best value', cheap: 'lowest price'}[VID.auto]}</b></div>${VID.compare.length ? '<span class="tag">Side by side</span>' : m ? `<span class="tag num">${money(rateAt(m, VID.res))}/s</span>` : '<span class="tag">Recommended</span>'}${I('chev', 'color:var(--dim)')}</button>
    ${VID.compare.length ? `<button class="lnk" data-uncompare style="align-self:flex-start">${I('x', 'width:13px;height:13px')} Stop comparing, use one model</button>` : ''}
    <div class="box">
      <h3>Describe your shot <button type="button" class="lnk" data-improve>${I('wand', 'width:14px;height:14px')} Improve</button></h3>
      <textarea id="vidq" rows="5" maxlength="2000" placeholder="Steam rising from a clay kulhad of chai on a rainy balcony in Mumbai, slow dolly in, warm evening light">${esc(VID.prompt)}</textarea>
    </div>
    <div class="lbl">Camera</div><div class="chips cams">${CAMS.map(([c, d]) => `<button class="chip" aria-pressed="${c === VID.camera}" data-vcam="${esc(c)}" title="${esc(d)}">${esc(c)}</button>`).join('')}</div>
    <div class="lbl">Shape</div><div class="grid-opts">${['9:16', '16:9', '1:1'].map(a => `<button class="go shp" aria-pressed="${a === VID.aspect}" data-vasp="${a}">${ratioI(a)}<span>${a}</span></button>`).join('')}</div>
    <div class="lbl">Length</div><div class="grid-opts" style="grid-template-columns:repeat(4,1fr)">${lenOpts(m).map(s => `<button class="go" aria-pressed="${s === VID.seconds}" data-vsec="${s}">${s} s</button>`).join('')}</div>
    <div class="lbl">Resolution</div><div class="grid-opts" style="grid-template-columns:repeat(4,1fr)">${resOpts(m).map(r => `<button class="go" aria-pressed="${r === VID.res}" data-vres="${r}">${r}</button>`).join('')}</div>
    <div class="prow2"><div class="prow"><span class="pi">${I('sound', 'width:16px;height:16px')}</span><div><small>Sound</small><b>${VID.audio ? 'On' : 'Off'}</b></div><button class="sw" role="switch" aria-checked="${VID.audio}" data-vaudio aria-label="Sound"><i></i></button></div>
      <div class="prow"><span class="pi">${I('layers', 'width:16px;height:16px')}</span><div><small>Takes</small><b class="num">${VID.takes}</b></div><span class="stepper" style="height:32px;border:0;padding:0"><button data-vtake="-1" aria-label="Fewer takes">${I('minus', 'width:14px;height:14px')}</button><button data-vtake="1" aria-label="More takes">${I('plus', 'width:14px;height:14px')}</button></span></div></div>
    <div class="lbl">Spoken lines in</div><div class="chips">${['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu'].map(l => `<button class="chip" aria-pressed="${l === VID.language}" data-vlang="${l}">${l}</button>`).join('')}</div>
    <div class="pricebox" id="vprice"></div>
  </div>
  <div class="pfoot"><button class="btn sec" id="vidPrev" title="An animatic from pictures, to check the story">Free preview</button><button class="create" id="vidGo">${I('spark', 'width:17px;height:17px')}<span>Create</span><small class="num" id="vidCost">…</small></button></div></div>
  <div class="stage"><div class="sbar"><b>Your videos</b><span class="sp"></span><button class="ib" data-reload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div>
    <div class="sgrid" id="results"></div></div></div>`; };
  // one tile per Video Studio project: its newest picked take / output, its live state, and any price card waiting
  function projMedia(p) {
    const out = (p.outputs || []).slice(-1)[0];
    if (out?.url) return `<video muted playsinline preload="metadata" src="${esc(out.url)}"${out.thumb ? ` poster="${esc(out.thumb)}"` : ''}></video>`;
    for (const s of p.shots || []) { const t = (s.take_list || []).find(x => x.picked) || (s.take_list || []).slice(-1)[0]; if (t?.url) return `<video muted playsinline preload="metadata" src="${esc(t.url)}"></video>`; }
    const kf = (p.shots || []).find(s => s.keyframe); if (kf) return `<img alt="" src="${esc(kf.keyframe)}">`;
    return art('film', p.project);
  }
  // the price card: line by line, the total on the Haan button; nothing runs before it, never more than it
  function approvalRow(a) {
    const what = {generate: `${a.shots || ''} shot${a.shots === 1 ? '' : 's'} · ${a.quality || ''}`, keyframes: `${a.shots} opening picture${a.shots === 1 ? '' : 's'}`, music: 'Music track (Google Lyria)', character: `Character picture · ${a.name || ''}`}[a.kind] || a.kind;
    const rows = (a.rows || []).map(r => `<tr><td>${esc(r.name)}${r.lipsync ? ' + lip sync' : ''}</td><td class="num">${r.seconds} s${r.takes > 1 ? ' × ' + r.takes : ''}</td><td>${esc(r.resolution)}${r.audio === false ? ' · silent' : ''}</td><td class="num">${money(r.inr)}</td></tr>`).join('');
    const extra = [a.keyframes ? `<tr><td>Opening pictures × ${a.keyframes}</td><td></td><td></td><td class="num">${money(a.keyframes_inr)}</td></tr>` : '', a.music ? `<tr><td>Music (${esc(a.music)})</td><td></td><td></td><td class="num">${money(a.music_inr)}</td></tr>` : ''].join('');
    return `<div class="appr"><div class="aph"><b class="num">${inr(a.inr)}</b><small>${esc(what)}</small></div>
      ${rows || extra ? `<table class="aprows">${rows}${extra}</table>` : ''}
      <small class="apn">Nothing is spent until you tap Haan. You are never charged more than ${inr(a.inr)}.</small>
      <div class="apb"><button class="btn sec" data-no="${esc(a.id)}">Na</button><button class="btn pri" data-yes="${esc(a.id)}">Haan, make it · ${inr(a.inr)}</button></div></div>`;
  }
  function projTile(p) {
    const busy = p.working || p.planning || (p.painting || []).length;
    return `<div class="res${busy ? ' gening' : ''}" data-proj="${esc(p.project)}"><button class="thumb" data-openproj="${esc(p.project)}" aria-label="Open ${esc(p.project)}">${projMedia(p)}${busy ? `<span class="ring"></span><span class="pct">${p.progress?.pct != null ? p.progress.pct + '%' : p.planning ? 'Writing the plan' : 'Working'}</span>` : `<span class="badge">${I('play', 'width:11px;height:11px')}${esc(p.aspect)}</span><span class="dur num">${p.seconds || 0} s</span>`}</button>
      <b class="rt">${esc(p.project)}</b><small>${esc((p.brief || '').slice(0, 80))}</small>${moneyLine(p.money)}${(p.approvals || []).map(approvalRow).join('')}</div>`;
  }
  // v0.263 estimate vs what she pays vs what the providers reported, for a film / clip
  function moneyLine(mo) {
    if (!mo || !mo.takes) return '';
    return `<small class="moneyl num">You pay ${money(mo.billed_inr)}${mo.estimate_inr > mo.billed_inr + 0.05 ? ` · estimate was ${money(mo.estimate_inr)} · saved ${money(mo.saved_inr)}` : ''}${mo.actual_inr != null ? ` · provider charged ${money(mo.actual_inr)}` : ''}</small>`;
  }
  async function decide(aid, yes) {
    try { await api('POST', `/api/studio/approvals/${encodeURIComponent(aid)}`, {yes}); toast(yes ? 'Started. Nothing more is spent without you.' : 'Declined, nothing spent'); return true; }
    catch (e) { toast(e.status === 428 ? fp : e.message, true); return false; }
  }
  function drawVideos() {
    const el = $('#results'); if (!el) return;
    const ps = (D.studio?.projects || []);
    el.innerHTML = (D.studio && D.studio.available === false ? `<div class="empty" style="grid-column:1/-1"><div><h2>Video Studio is off on this server</h2><p class="mut">It needs ffmpeg and STUDIO_ON on the server.</p></div></div>` : '')
      + (VID.busy ? `<div class="res gening"><span class="thumb">${art('film', 'vb')}<span class="ring"></span><span class="pct">${esc(VID.busy)}</span></span><b class="rt">${esc(VID.prompt.slice(0, 48))}</b><small>Hoola is writing the shot plan; the price card comes next</small></div>` : '')
      + (ps.map(projTile).join('') || (VID.busy ? '' : `<div class="empty" style="grid-column:1/-1"><div><h2>Your videos appear here</h2><p class="mut">Describe a shot, pick a model, see the price, press Create.</p></div></div>`));
    paintAll(el);
  }
  function watchStudio(view, draw) {
    const tick = async () => {
      if (VIEW !== view) return;
      await load('studio', true); drawCredits(); draw();
      const live = (D.studio?.projects || []).some(p => p.working || p.planning || (p.painting || []).length || (p.approvals || []).length);
      poll = setTimeout(tick, live ? 4000 : 15000);
    };
    poll = setTimeout(tick, 4000);
  }
  // the live price: asked from the server on every change (the same table the price card uses)
  let priceT = 0, priceN = 0;
  function livePrice() {
    clearTimeout(priceT); const n = ++priceN; const c = $('#vidCost'); if (c) c.textContent = '…';
    priceT = setTimeout(async () => {
      try {
        const ask = mdl => api('POST', '/api/studio/price', {model: mdl, seconds: VID.seconds, resolution: VID.res, audio: VID.audio, takes: VID.takes, auto: VID.auto});
        const rs = VID.compare.length ? await Promise.all(VID.compare.map(ask)) : [await ask(VID.model)];
        if (n !== priceN || VIEW !== 'video') return; const r = rs[0], tot = rs.reduce((t, x) => t + x.inr, 0); VID.price = r;
        $('#vidCost').textContent = '≈ ' + money(tot);
        $('#vprice').innerHTML = `<div><b class="num">≈ ${money(tot)}</b>${rs.map(x => `<small>${esc(x.name)} · ${x.seconds} s × ${money(x.inr_per_s)}/s at ${esc(x.resolution)}${x.takes > 1 ? ' × ' + x.takes + ' takes' : ''}${x.audio ? '' : ' · silent'} = ${money(x.inr)}</small>`).join('')}</div>
          ${r.why ? `<small>${esc(r.why)}</small>` : ''}${rs.length > 1 ? '<small>The same shot is made by each model; one price card for all, and you keep the take you like.</small>' : ''}
          ${r.changed?.length ? `<small class="warnl">This model makes ${r.changed.map(k => k === 'seconds' ? r.seconds + ' s' : r.resolution).join(' and ')}, so the price is for that.</small>` : ''}
          ${r.ready ? '' : '<small class="warnl">This model is not switched on on the server yet.</small>'}
          <small>You see the exact price card before anything is spent, and you are never charged more than it.</small>`;
      } catch (e) { if (n === priceN && $('#vidCost')) $('#vidCost').textContent = ''; }
    }, 220);
  }
  async function newClip(preview) {
    let brief = VID.prompt.trim(); if (!brief) { $('#vidq')?.focus(); toast('Describe the shot first'); return; }
    const cam = (CAMS.find(c => c[0] === VID.camera) || [])[1]; if (cam) brief += `\nCamera: ${cam}.`;   // v0.304 the camera preset rides the brief
    if (VID.busy) return;
    VID.busy = 'Writing the plan'; drawVideos();
    const name = 'Clip ' + new Date().toLocaleString('en-IN', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false}).replace(',', '');
    const quality = preview ? 'preview' : QOF(VID.res);
    try {
      const p = await api('POST', '/api/studio/projects', {name, brief, aspect: VID.aspect, seconds: VID.seconds, language: VID.language,
        quality: preview ? 'draft' : quality, model: VID.model, resolution: VID.res, auto: VID.auto});
      VID.busy = preview ? 'Making the free preview' : 'Working out the price';
      const r = await api('POST', `/api/studio/projects/${encodeURIComponent(p.project)}/generate`, {quality, model: VID.model || null, variants: preview ? 1 : VID.takes,
        compare: !preview && VID.compare.length > 1 ? VID.compare : null});
      toast(r.waiting_owner ? `Price ${inr(r.inr)}: tap Haan on the tile to make it.` : 'Making your free preview');
    } catch (e) { toast(e.status === 428 ? fp : e.message, true); }
    VID.busy = ''; await load('studio', true); redraw('video', drawVideos);
  }
  function fitToModel() {          // keep length / resolution inside what the chosen model makes
    const m = vm(); if (!m) return;
    const L = lenOpts(m); if (L.length && !L.includes(VID.seconds)) VID.seconds = L.reduce((a, b) => Math.abs(b - VID.seconds) < Math.abs(a - VID.seconds) ? b : a);
    const R = resOpts(m); if (R.length && !R.includes(VID.res)) VID.res = R.find(r => RES.indexOf(r) >= RES.indexOf(VID.res)) || R[R.length - 1];
  }
  W.video = (el, o) => {
    const q = $('#vidq'); q.addEventListener('input', () => VID.prompt = q.value);
    load('studio').then(() => redraw('video', drawVideos)); watchStudio('video', drawVideos);
    models().then(() => { if (VIEW === 'video' && VID.model && !vm()) { VID.model = ''; } livePrice(); });
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.vcam) { VID.camera = b.dataset.vcam; $$('[data-vcam]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.vasp) { VID.aspect = b.dataset.vasp; $$('[data-vasp]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.vsec) { VID.seconds = +b.dataset.vsec; $$('[data-vsec]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); livePrice(); return; }
      if (b.dataset.vres) { VID.res = b.dataset.vres; $$('[data-vres]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); livePrice(); return; }
      if (b.hasAttribute('data-vaudio')) { VID.audio = !VID.audio; b.setAttribute('aria-checked', String(VID.audio)); b.closest('.prow').querySelector('b').textContent = VID.audio ? 'On' : 'Off'; livePrice(); return; }
      if (b.dataset.vtake) { VID.takes = Math.max(1, Math.min(4, VID.takes + +b.dataset.vtake)); b.closest('.prow').querySelector('b').textContent = VID.takes; livePrice(); return; }
      if (b.dataset.vlang) { VID.language = b.dataset.vlang; $$('[data-vlang]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.hasAttribute('data-pickmodel')) { VID.prompt = q.value; picker({current: VID.compare.length ? null : VID.model, seconds: VID.seconds, res: VID.res, title: 'Choose the model for this video',
        auto: VID.auto, onAuto: mode => { VID.auto = mode; },
        onPick: k => { VID.model = k; VID.compare = []; fitToModel(); go('video'); },
        onCompare: keys => { VID.compare = keys.slice(0, 3); VID.model = ''; go('video'); }}); return; }
      if (b.hasAttribute('data-uncompare')) { VID.compare = []; VID.prompt = q.value; go('video'); return; }
      if (b.hasAttribute('data-improve')) { if (!q.value.trim()) { q.focus(); return; } b.disabled = true;
        try { const r = await api('POST', '/api/studio/improve', {brief: q.value.trim(), language: VID.language, seconds: VID.seconds}); q.value = VID.prompt = r.brief; } catch (er) { toast(er.message, true); } b.disabled = false; return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await load('studio', true); drawVideos(); return; }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); return; }
      if (b.hasAttribute('data-reload')) { await load('studio', true); drawVideos(); return; }
      if (b.id === 'vidPrev') { VID.prompt = q.value; newClip(true); return; }
      if (b.id === 'vidGo') { VID.prompt = q.value; newClip(false); }
    });
    if (o.autostart) { VID.prompt = VID.prompt || q.value; newClip(false); }
  };

  /* ---------------- director (a whole film on Video Studio) ---------------- */
  const DIR = {brief: '', project: '', aspect: '16:9', seconds: 45, language: 'Hindi', music: '', busy: '', view: null, model: '', res: '1080p'};
  const STEPS = [['brief', 'Brief'], ['plan', 'Storyboard'], ['cast', 'Cast'], ['keyframes', 'Pictures'], ['preview', 'Preview'], ['generate', 'Shots'], ['music', 'Music'], ['assemble', 'Final film']];
  function stepState(p) {
    const shots = p.shots || [], picked = shots.length && shots.every(s => s.picked);
    const real = shots.length && shots.every(s => s.quality && s.quality !== 'preview');
    return {brief: true, plan: shots.length > 0, cast: (p.character_list || []).length > 0, keyframes: shots.length && p.keyframes >= shots.length,
      preview: shots.some(s => (s.take_list || []).length), generate: picked && real, music: !!p.music, assemble: (p.outputs || []).some(o => !o.preview)};
  }
  V.director = o => {
    const p = DIR.view;
    if (!DIR.project || !p) return `<div class="dir">
  <div class="dhero">${art('film', 'dirhero')}<span class="tag hot">Director agent</span><h1>Brief in, finished film out</h1>
    <form class="compose" id="dirForm" style="width:min(760px,100%)"><label for="dirq" class="sr">Your film brief</label><textarea id="dirq" rows="3" placeholder="A 45-second Diwali ad for Newtika Chai: a family comes home, Dadi makes chai, ends on our logo">${esc(DIR.brief)}</textarea>
      <div class="crow"><button type="button" class="dd" data-dcyc="aspect">${I('grid', 'width:15px;height:15px')}<span>${DIR.aspect}</span></button><button type="button" class="dd" data-dcyc="seconds"><span>${DIR.seconds} s</span></button><button type="button" class="dd" data-dcyc="language"><span>${DIR.language}</span></button><button type="button" class="dd" data-dcyc="music">${I('music', 'width:15px;height:15px')}<span>${DIR.music || 'No music'}</span></button><button type="button" class="dd" data-dnewmodel>${I('spark', 'width:15px;height:15px')}<span>${esc(mOf(DIR.model)?.name || 'Hoola Auto')}</span>${I('down', 'width:14px;height:14px')}</button><button type="button" class="dd" data-dnewres><span>${DIR.res}</span>${I('down', 'width:14px;height:14px')}</button><span class="sp"></span><button class="send" aria-label="Plan the film">${I('send')}</button></div></form>
    <p class="mut" style="max-width:560px">Hoola writes the storyboard for free. Pictures, shots and music each show their price first; nothing is spent until you tap Haan.</p></div>
  ${DIR.busy ? `<div class="box"><b>${esc(DIR.busy)}…</b><div class="bar"><i class="indet"></i></div></div>` : ''}
  <section><div class="sec-h"><h2>Your films</h2><span class="dim" style="font-size:13px">${(D.studio?.projects || []).length} projects</span></div><div class="scenes" id="films"></div></section></div>`;
    const st = stepState(p), cur = STEPS.find(([k]) => !st[k])?.[0] || 'done';
    const nx = p.next || {};
    return `<div class="dir">
  <div class="sec-h" style="margin:0;align-items:center"><div style="min-width:0"><button class="lnk" data-dirback>${I('left', 'width:14px;height:14px')} All films</button><h2 style="font:400 26px/1.25 var(--serif);margin-top:4px">${esc(p.project)}</h2><p class="mut" style="margin-top:4px;max-width:760px">${esc((p.brief || '').slice(0, 280))}</p></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><button class="dd" data-pmodel title="The model for the whole film">${I('spark', 'width:15px;height:15px')}<span>${esc(mOf(p.prefs?.model)?.name || 'Hoola Auto')}</span>${I('down', 'width:14px;height:14px')}</button><button class="dd" data-pres title="Resolution of the shots"><span>${esc(p.prefs?.resolution || 'By quality')}</span>${I('down', 'width:14px;height:14px')}</button>${p.working ? `<button class="btn sec" data-dcancel>${I('x', 'width:15px;height:15px')}Stop</button>` : ''}<button class="btn pri" data-next="${esc(nx.kind || '')}" ${['wait', 'done'].includes(nx.kind) ? 'disabled' : ''}>${esc(nextLabel(nx))}${nx.inr ? ` <small class="num">${inr(nx.inr)}</small>` : ''}</button></div></div>
  ${moneyLine(p.money) ? `<div class="moneybar">${moneyLine(p.money)}</div>` : ''}
  <div class="pipe" role="list">${STEPS.map(([k, t], i) => `<button role="listitem" class="${st[k] ? 'done' : ''}" ${k === cur ? 'aria-current="step"' : ''} data-step="${k}"><i>${st[k] ? '✓' : i + 1}</i>${t}</button>`).join('')}</div>
  ${(p.approvals || []).length ? `<section class="box"><h3>Waiting for your Haan</h3>${p.approvals.map(approvalRow).join('')}</section>` : ''}
  ${p.progress && p.working ? `<div class="box"><div style="display:flex;justify-content:space-between"><b>Making ${p.progress.total} shot${p.progress.total === 1 ? '' : 's'} · ${esc(p.progress.quality || '')}</b><span class="num mut">${p.progress.pct}%${p.progress.eta_s ? ' · about ' + Math.ceil(p.progress.eta_s / 60) + ' min' : ''}</span></div><div class="bar"><i style="width:${p.progress.pct}%"></i></div></div>` : ''}
  ${(p.outputs || []).length ? `<section><div class="sec-h"><h2>Your film</h2></div><div class="outs">${p.outputs.slice().reverse().map(o => `<div class="out"><video controls playsinline preload="metadata" src="${esc(o.url)}"${o.thumb ? ` poster="${esc(o.thumb)}"` : ''}></video><small>${o.preview ? 'Preview' : 'Final'} · ${o.seconds || ''} s · ${o.mb} MB <a href="${esc(o.url)}" download="${esc(o.name || 'hoola-film.mp4')}">Download</a></small></div>`).join('')}</div></section>` : ''}
  <section id="castsec" ${DIR.castOpen || o.cast ? '' : 'hidden'} class="box"><h3>Add a character <button class="ib" data-castclose aria-label="Close">${I('x', 'width:15px;height:15px')}</button></h3>
    <div class="prow2"><label class="fld">Name<input id="cname" maxlength="40" value="${esc(DIR.castDraft?.name || '')}"></label><label class="fld">Voice<select id="cvoice"><option value="female">Female</option><option value="male">Male</option></select></label></div>
    <label class="fld">Looks like<textarea id="cdesc" rows="2" maxlength="400" placeholder="28, warm smile, long black hair in a braid, mustard kurta">${esc(DIR.castDraft?.description || '')}</textarea></label>
    <button class="btn pri" data-castgo>${I('cast', 'width:15px;height:15px')}Make this character</button><p class="note">An AI character keeps the same face in every shot. A real person needs their permission (add from the chat with their photo).</p></section>
  <section><div class="sec-h"><h2>Storyboard · ${(p.shots || []).length} shots · ${p.seconds || 0} s</h2><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sec" data-dpreview>${I('play', 'width:14px;height:14px')}Free preview</button><button class="btn sec" data-castopen>${I('cast', 'width:15px;height:15px')}Cast</button><button class="btn sec" data-dmusic>${I('music', 'width:15px;height:15px')}Music</button><button class="btn sec" data-replan>${I('redo', 'width:15px;height:15px')}Rewrite</button></div></div>
    ${p.planning && !(p.shots || []).length ? `<div class="box"><b>Writing the storyboard…</b><div class="bar"><i class="indet"></i></div></div>` : ''}
    <div class="scenes">${(p.shots || []).map((s, i) => sceneCard(s, i)).join('')}</div></section>
  ${(p.character_list || []).length ? `<section><div class="sec-h"><h2>Cast</h2></div><div class="cast">${p.character_list.map(c => `<div class="actor"><span class="thumb">${c.image ? `<img alt="" src="${esc(c.image)}">` : art('cast', c.name)}</span><div><b>${esc(c.name)}</b><small>${esc(c.description.slice(0, 80))}</small></div></div>`).join('')}</div></section>` : ''}
</div>`;
  };
  function nextLabel(n) {
    return {plan: 'Write the storyboard', keyframes: 'Paint the opening pictures', generate: 'Make the shots', assemble: 'Make the final film', wait: 'Working…', done: 'Film ready'}[n.kind] || 'Next';
  }
  function sceneCard(s, i) {
    const take = (s.take_list || []).find(t => t.picked) || (s.take_list || []).slice(-1)[0];
    const media = take?.url ? `<video controls playsinline preload="metadata" src="${esc(take.url)}"></video>` : s.keyframe ? `<img alt="" src="${esc(s.keyframe)}">` : art('film', s.id);
    const ph = {paint: 'Painting', video: 'Making', queued: 'Queued', lipsync: 'Lip sync', retrying: 'Retrying', failed: 'Failed', done: 'Picked', pictured: 'Picture ready'}[s.phase] || '';
    return `<div class="scene" data-shot="${esc(s.id)}"><div class="one">${media}${['paint', 'video', 'queued', 'lipsync', 'retrying'].includes(s.phase) ? `<span class="ring"></span><span class="pct">${s.pct != null ? s.pct + '%' : ph}</span>` : ''}</div>
      <div class="sb"><b>${i + 1} · ${esc(s.kind)}${ph ? ` <span class="tag${s.phase === 'failed' ? ' hot' : ''}">${ph}</span>` : ''}</b>
        <small class="clamp" data-ptext>${esc(s.prompt)}</small>${take && take.billed_inr != null && take.quality !== 'preview' ? `<small class="moneyl num">${esc(take.model_label || '')} · you pay ${money(take.billed_inr)}${take.est_inr != null && take.est_inr > take.billed_inr + 0.05 ? ` (card ${money(take.est_inr)})` : ''}${take.actual_inr != null ? ` · provider ${money(take.actual_inr)}` : ''}</small>` : ''}${s.dialogue ? `<small>“${esc(s.dialogue)}”</small>` : ''}${s.error ? `<small class="bad clamp" title="${esc(s.error)}">${esc(s.error.slice(0, 160))}</small>` : ''}
        <div class="sm"><span class="tag">${s.duration} s</span><button class="tag mchip" data-smodel="${esc(s.id)}" title="Model for this scene">${esc(s.model_label || 'Auto')} ▾</button>${(s.characters || []).map(c => `<span class="mention">@${esc(c)}</span>`).join('')}<span style="flex:1"></span>
          ${(s.take_list || []).length > 1 ? (s.take_list || []).map(t => `<button class="tk${t.picked ? ' on' : ''}" data-take="${t.n}" aria-label="Use take ${t.n}${t.model_label ? ' by ' + esc(t.model_label) : ''}" title="${esc(t.model_label || '')}">${t.n}${new Set((s.take_list || []).map(x => x.model)).size > 1 && t.model_label ? ' · ' + esc(t.model_label) : ''}</button>`).join('') : ''}
          <button class="ib" style="width:28px;height:28px" aria-label="Edit scene" data-edit>${I('pen', 'width:14px;height:14px')}</button></div></div></div>`;
  }
  async function dirLoad() {
    if (!DIR.project) return;
    try { DIR.view = await api('GET', `/api/studio/projects/${encodeURIComponent(DIR.project)}`); }
    catch (e) { toast(e.message, true); DIR.project = ''; DIR.view = null; }
  }
  function drawFilms() {
    const el = $('#films'); if (!el) return;
    const ps = D.studio?.projects || [];
    el.innerHTML = ps.map(p => `<button class="scene" data-openproj="${esc(p.project)}" style="text-align:left"><div class="one">${projMedia(p)}</div><div class="sb"><b>${esc(p.project)}</b><small>${esc((p.brief || '').slice(0, 90))}</small><span class="bar" style="margin-top:6px"><i style="width:${Math.round(Object.values(stepState(p)).filter(Boolean).length / STEPS.length * 100)}%"></i></span></div></button>`).join('')
      || `<p class="mut">No films yet. Write a brief above.</p>`;
    paintAll(el);
  }
  async function newFilm() {
    const brief = ($('#dirq')?.value || DIR.brief).trim(); if (!brief) { $('#dirq')?.focus(); toast('Write the brief first'); return; }
    DIR.brief = brief; DIR.busy = 'Writing your storyboard (about a minute)'; go('director');
    const name = brief.replace(/[^\p{L}\p{N} ]/gu, ' ').trim().split(/\s+/).slice(0, 5).join(' ').slice(0, 50) || 'My film';
    try {
      const p = await api('POST', '/api/studio/projects', {name, brief, aspect: DIR.aspect, seconds: DIR.seconds, language: DIR.language, music: DIR.music,
        quality: QOF(DIR.res), model: DIR.model, resolution: DIR.res});
      DIR.project = p.project; DIR.view = p; DIR.busy = ''; await load('studio', true); toast('Storyboard ready. Check it, then paint the pictures.');
    } catch (e) { DIR.busy = ''; toast(e.message, true); }
    if (VIEW === 'director') go('director');
  }
  W.director = async (el, o) => {
    const n = alive;
    if (DIR.project && !DIR.view) { await dirLoad(); if (n !== alive) return; go('director', o); return; }
    if (!DIR.project) { load('studio').then(() => redraw('director', drawFilms)); }
    else { const tick = async () => { if (VIEW !== 'director' || !DIR.project) return; await dirLoad(); const p = DIR.view;
        if (p && VIEW === 'director' && !$(':focus', el)?.matches('textarea,input')) { const y = $('#view').scrollTop; go('director'); $('#view').scrollTop = y; }
        else poll = setTimeout(tick, 5000); };
      const p = DIR.view; if (p && (p.working || p.planning || (p.painting || []).length || (p.approvals || []).length)) poll = setTimeout(tick, 5000); }
    $('#dirForm', el)?.addEventListener('submit', e => { e.preventDefault(); newFilm(); });
    const cyc = {aspect: ['16:9', '9:16', '1:1'], seconds: [15, 30, 45, 60, 90, 120, 180], language: ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali'], music: ['', 'festive', 'cinematic', 'upbeat', 'calm', 'corporate', 'lofi']};
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      const P = DIR.project ? `/api/studio/projects/${encodeURIComponent(DIR.project)}` : '';
      const act = async (label, fn) => { b.disabled = true; try { const r = await fn(); if (r?.waiting_owner) toast(`Price ${inr(r.inr)}: tap Haan above to start`); else if (label) toast(label); } catch (er) { toast(er.status === 428 ? fp : er.message, true); } await dirLoad(); if (VIEW === 'director') go('director'); };
      const resItems = m => resSort(m ? m.resolutions : ['480p', '720p', '1080p', '2k', '4k']).map(r => ({v: r, label: r, sub: m ? money(rateAt(m, r)) + ' per second' : ({'480p': 'Drafts', '720p': 'Quick and cheap', '1080p': 'HD, for posting', '2k': 'Premium', '4k': 'Premium 4K'})[r]}));
      if (b.hasAttribute('data-dnewmodel')) { await models(); picker({current: DIR.model, seconds: DIR.seconds, res: DIR.res, title: 'Choose the model for this film',
        onPick: k => { DIR.model = k; DIR.brief = $('#dirq')?.value || DIR.brief; go('director'); }}); return; }
      if (b.hasAttribute('data-dnewres')) { await models(); menu(b, resItems(mOf(DIR.model)), DIR.res, v => { DIR.res = v; b.querySelector('span').textContent = v; }, 'Resolution'); return; }
      if (b.hasAttribute('data-pmodel')) { await models(); const p = DIR.view;
        picker({current: p.prefs?.model || '', seconds: p.seconds || DIR.seconds, res: p.prefs?.resolution || '1080p', title: 'The model for the whole film',
          auto: p.prefs?.auto || 'quality', onAuto: mode => act('', () => api('POST', P + '/settings', {auto: mode, model: ''})),
          onPick: k => act('', () => api('POST', P + '/settings', {model: k}))}); return; }
      if (b.hasAttribute('data-pres')) { await models(); const p = DIR.view;
        menu(b, [{v: '', label: 'By quality', sub: 'Draft 720p, HD 1080p'}, ...resItems(mOf(p.prefs?.model))], p.prefs?.resolution || '', v => act('', () => api('POST', P + '/settings', {resolution: v})), 'Resolution'); return; }
      if (b.dataset.smodel) { await models(); const sid = b.dataset.smodel, s = DIR.view.shots.find(x => x.id === sid), res = DIR.view.prefs?.resolution || '1080p';
        const ready = (D.models?.models || []).filter(m => m.ready && m.tier !== 'talk');
        menu(b, [{v: '', label: 'Same as the film', sub: 'Hoola Auto or the film model'}, {v: '__cmp', label: 'Try 2 or 3 models side by side…', sub: 'One price card, keep the take you like'}, ...ready.map(m => ({v: m.key, label: m.name, sub: `${money(rateAt(m, res) * s.duration)} for this ${s.duration} s scene`}))],
          s.model || '', v => {
            if (v !== '__cmp') return act('Scene model set', () => api('PATCH', `${P}/shots/${encodeURIComponent(sid)}`, {model: v}));
            picker({current: null, seconds: s.duration, res, title: `Scene ${DIR.view.shots.indexOf(s) + 1}: tick 2-3 models, then Compare`,
              onPick: k => act('Scene model set', () => api('PATCH', `${P}/shots/${encodeURIComponent(sid)}`, {model: k})),
              onCompare: keys => act('', () => api('POST', P + '/generate', {quality: DIR.view.quality_pref || 'final', shot_ids: [sid], compare: keys}))});
          }, 'Model for scene'); return; }
      if (b.dataset.dcyc) { const k = b.dataset.dcyc, L = cyc[k];
        const fmt = {aspect: v => ({'16:9': '16:9 · Wide (YouTube)', '9:16': '9:16 · Reel / Short', '1:1': '1:1 · Square post'})[v], seconds: v => v < 60 ? v + ' seconds' : v / 60 + ' minute' + (v > 60 ? 's' : ''),
          music: v => v ? v[0].toUpperCase() + v.slice(1) : 'No music'}[k];
        menu(b, opt(L, fmt), DIR[k], v => { DIR[k] = v; b.querySelector('span').textContent = k === 'seconds' ? v + ' s' : (v || 'No music'); },
          {aspect: 'Shape', seconds: 'Length', language: 'Spoken language', music: 'Music (Google Lyria)'}[k]); return; }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); return; }
      if (b.hasAttribute('data-dirback')) { DIR.project = ''; DIR.view = null; go('director'); return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await dirLoad(); go('director'); return; }
      if (b.dataset.next) { const k = b.dataset.next;
        if (k === 'plan') return act('Storyboard written', () => api('POST', P + '/plan', {brief: DIR.view.brief, seconds: DIR.view.seconds || DIR.seconds}));
        if (k === 'keyframes') return act('', () => api('POST', P + '/keyframes', {}));
        if (k === 'generate') return act('', () => api('POST', P + '/generate', {quality: DIR.view.quality_pref || 'final'}));
        if (k === 'assemble') return act('Putting the film together', () => api('POST', P + '/assemble', {})); return; }
      if (b.dataset.step) { const k = b.dataset.step; if (k === 'cast') { DIR.castOpen = true; go('director'); } else if (k === 'music') b.closest('.dir')?.querySelector('[data-dmusic]')?.click(); return; }
      if (b.hasAttribute('data-dpreview')) return act('Making the free preview', () => api('POST', P + '/generate', {quality: 'preview'}));
      if (b.hasAttribute('data-replan')) { if (!confirm('Rewrite the whole storyboard? Shots made so far stay in the project.')) return; return act('Storyboard rewritten', () => api('POST', P + '/plan', {brief: DIR.view.brief, seconds: DIR.view.seconds || DIR.seconds})); }
      if (b.hasAttribute('data-dmusic')) { const mood = prompt('Music mood: festive, cinematic, upbeat, calm, corporate, lofi, or describe it', 'cinematic'); if (!mood) return; return act('', () => api('POST', P + '/music', {mood, volume: 0.25})); }
      if (b.hasAttribute('data-dcancel')) return act('Stopped', () => api('POST', P + '/cancel', {}));
      if (b.hasAttribute('data-castopen')) { DIR.castOpen = true; go('director'); $('#cname')?.focus(); return; }
      if (b.hasAttribute('data-castclose')) { DIR.castOpen = false; DIR.castDraft = null; $('#castsec').hidden = true; return; }
      if (b.hasAttribute('data-castgo')) { const name = $('#cname').value.trim(), description = $('#cdesc').value.trim(); if (!name || !description) { toast('Give the character a name and a look'); return; }
        DIR.castOpen = false; DIR.castDraft = null; return act('', () => api('POST', P + '/characters', {name, description, voice: $('#cvoice').value, kind: 'person'})); }
      if (b.dataset.take) { const sh = b.closest('[data-shot]').dataset.shot; return act('Take picked', () => api('POST', P + '/pick', {shot_id: sh, take: +b.dataset.take})); }
      if (b.hasAttribute('data-edit')) { const card = b.closest('[data-shot]'), sid = card.dataset.shot, s = DIR.view.shots.find(x => x.id === sid);
        const box = card.querySelector('[data-ptext]'); const ta = document.createElement('textarea'); ta.className = 'ptedit'; ta.value = s.prompt; ta.rows = 5; box.replaceWith(ta); ta.focus();
        const save = document.createElement('button'); save.className = 'btn pri'; save.textContent = 'Save'; save.style.marginTop = '6px'; ta.after(save);
        save.onclick = () => act('Scene saved', () => api('PATCH', `${P}/shots/${encodeURIComponent(sid)}`, {prompt: ta.value.trim()})); return; }
    });
    if (o.autostart) newFilm();
    if (o.focus) $('#dirq')?.focus();
  };

  /* ---------------- script writer ---------------- */
  const SC = {fmt: 'Ad film', len: '45 seconds', lang: 'Hinglish', tone: 'Warm', brief: '', text: '', id: '', busy: false};
  V.script = () => `<div class="split"><aside>
    <div class="box"><h3>What is it about?</h3><textarea rows="5" id="scq" maxlength="3000" placeholder="Diwali ad for Newtika Chai. A family comes home, Dadi makes chai, ends on the logo.">${esc(SC.brief)}</textarea></div>
    ${[['fmt', 'Format', ['Ad film', 'Short film', 'Web episode', 'Music video', 'Reel', 'Explainer']], ['len', 'Length', ['15 seconds', '30 seconds', '45 seconds', '2 minutes', '10 minutes']], ['lang', 'Dialogue in', ['Hinglish', 'Hindi', 'English', 'Marathi', 'Tamil', 'Telugu']], ['tone', 'Tone', ['Warm', 'Funny', 'Dramatic', 'Premium', 'Emotional']]].map(([k, t, L]) => `<div class="lbl">${t}</div><div class="chips">${L.map(o => `<button class="chip" aria-pressed="${SC[k] === o}" data-sc="${k}|${o}">${o}</button>`).join('')}</div>`).join('')}
    <button class="create" style="flex:none;margin-top:6px" id="scGo" ${SC.busy ? 'disabled' : ''}>${I('pen', 'width:16px;height:16px')}${SC.busy ? 'Writing…' : SC.text ? 'Write a new draft' : 'Write the script'}</button>
    <div class="lbl">Your scripts</div><div id="sclist" class="mini"></div>
  </aside><section>
    <div class="sbar" style="position:sticky;top:0;background:var(--bg);z-index:2"><b>${SC.text ? 'Your script · edits save by themselves' : 'Script'}</b><span class="sp"></span>
      ${SC.text ? `<button class="pillbtn" data-scdl>${I('dl', 'width:15px;height:15px')}Download</button><button class="btn pri" data-todir>${I('clap', 'width:15px;height:15px')}Send to Director</button>` : ''}</div>
    ${SC.busy ? `<div class="doc"><p class="mut">Hoola is writing your ${esc(SC.fmt.toLowerCase())}…</p><div class="bar"><i class="indet"></i></div></div>`
      : SC.text ? `<article class="doc" id="scdoc" contenteditable="plaintext-only" spellcheck="false" aria-label="Script">${esc(SC.text)}</article>`
      : empty('A screenplay, ready to shoot', 'Scene headings, action, characters and dialogue in your language. Send it to the Director to turn it into a film.')}
  </section></div>`;
  W.script = el => {
    const q = $('#scq'); q.addEventListener('input', () => SC.brief = q.value);
    load('items').then(() => redraw('script', () => { const l = $('#sclist'); if (!l) return; const its = items('script');
      l.innerHTML = its.map(it => `<button class="mrow${it.id === SC.id ? ' on' : ''}" data-scopen="${it.id}"><b>${esc(it.title)}</b><small>${when(it.created)}</small></button>`).join('') || '<p class="mut" style="font-size:13px">Scripts you write are kept here.</p>'; }));
    let t = 0; const doc = $('#scdoc');
    doc?.addEventListener('input', () => { SC.text = doc.innerText; clearTimeout(t); t = setTimeout(() => SC.id && api('PUT', `/api/create/items/${encodeURIComponent(SC.id)}/text`, {text: SC.text}).catch(e => toast(e.message, true)), 800); });
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.sc) { const [k, v] = b.dataset.sc.split('|'); SC[k] = v; $$(`[data-sc^="${k}|"]`).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.id === 'scGo') { SC.brief = q.value.trim(); if (SC.brief.length < 4) { q.focus(); toast('Write a line about the story first'); return; }
        SC.busy = true; go('script');
        try { const r = await api('POST', '/api/create/write', {kind: 'script', brief: SC.brief, format: SC.fmt, length: SC.len, language: SC.lang, tone: SC.tone});
          SC.text = r.text; SC.id = r.item?.id || ''; await load('items', true); }
        catch (er) { toast(er.message, true); }
        SC.busy = false; if (VIEW === 'script') go('script'); return; }
      if (b.dataset.scopen) { try { const r = await api('GET', itemPath(b.dataset.scopen), undefined, {raw: true}); SC.text = await r.text(); SC.id = b.dataset.scopen; go('script'); } catch (er) { toast(er.message, true); } return; }
      if (b.hasAttribute('data-scdl')) { const u = URL.createObjectURL(new Blob([SC.text], {type: 'text/plain'})); const a = document.createElement('a'); a.href = u; a.download = 'hoola-script.txt'; R.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000); return; }
      if (b.hasAttribute('data-todir')) { DIR.brief = ('Film this screenplay exactly, scene by scene:\n' + SC.text).slice(0, 2000); DIR.project = ''; DIR.view = null;
        const m = /(\d+)\s*(second|minute)/i.exec(SC.len); if (m) DIR.seconds = Math.min(600, +m[1] * (/min/i.test(m[2]) ? 60 : 1)); go('director', {focus: true}); }
    });
  };

  /* ---------------- AI casting ---------------- */
  const CA = {sel: '', style: 'Photoreal cinematic', voice: 'female'};
  V.casting = () => `<div class="split"><aside>
    <div class="box"><h3>New character</h3>
      <label class="fld">Name<input id="caname" maxlength="40" placeholder="Riya"></label>
      <label class="fld">Looks like<textarea id="cadesc" rows="4" maxlength="600" placeholder="28, warm smile, long black hair in a braid, mustard cotton kurta, small gold earrings"></textarea></label>
      <div class="lbl">Style</div><div class="chips">${['Photoreal cinematic', 'Animated 3D', 'Anime', 'Illustrated'].map(s => `<button class="chip" aria-pressed="${s === CA.style}" data-cast="style|${s}">${s}</button>`).join('')}</div>
      <div class="lbl">Voice</div><div class="seg"><button aria-pressed="${CA.voice === 'female'}" data-cast="voice|female">Female</button><button aria-pressed="${CA.voice === 'male'}" data-cast="voice|male">Male</button></div>
      <button class="create" style="flex:none" id="caGo">${I('cast', 'width:16px;height:16px')}Cast this character <small>~₹12</small></button>
      <p class="note">Hoola draws a four-view sheet (front, three-quarter, side, back) so the face stays the same in every shot. Only fictional people here; a real person needs their permission.</p></div>
  </aside><section><div class="dir" style="padding-top:18px">
    <div id="casel"></div>
    <section><div class="sec-h"><h2>Your cast</h2><span class="dim" style="font-size:13px">Same face and outfit in every shot</span></div><div class="cast" id="castgrid"></div></section></div></section></div>`;
  function drawCast() {
    const g = $('#castgrid'); if (!g) return;
    const its = items('cast'), jobs = running('cast');
    if (!CA.sel && its[0]) CA.sel = its[0].id;
    g.innerHTML = jobs.map(j => `<div class="actor gening"><span class="thumb">${art('cast', j.id)}<span class="ring"></span><span class="pct">Casting…</span></span><div><b>${esc(j.title.replace('Cast · ', ''))}</b><small>Drawing four views</small></div></div>`).join('')
      + failed('cast').map(j => `<div class="actor"><span class="thumb"><span class="fail">${esc(j.error)}</span></span><div><b>${esc(j.title)}</b><small><button class="lnk" data-seen="${j.id}">Dismiss</button></small></div></div>`).join('')
      + its.map(it => `<button class="actor${it.id === CA.sel ? ' on' : ''}" data-casel="${it.id}"><span class="thumb"><img alt="" data-src="${itemPath(it.id)}"></span><div><b>${esc(it.meta?.name || it.title)}</b><small>${esc((it.meta?.description || '').slice(0, 60))}</small></div></button>`).join('')
      || '<p class="mut">No characters yet. Describe one on the left.</p>';
    const s = its.find(x => x.id === CA.sel), d = $('#casel');
    d.innerHTML = s ? `<section class="box" style="padding:16px;gap:12px"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><b style="font-size:18px">${esc(s.meta?.name || s.title)}</b><span class="tag">${esc(s.meta?.voice || 'voice')} voice</span><span style="flex:1"></span>
        <button class="pillbtn" data-castfilm="${s.id}">${I('clap', 'width:15px;height:15px')}Use in a film</button><button class="pillbtn" data-ref="${s.id}">${I('image', 'width:15px;height:15px')}Use in a picture</button><button class="pillbtn" data-dl="${s.id}">${I('dl', 'width:15px;height:15px')}Download</button><button class="ib" data-del="${s.id}" aria-label="Delete">${I('trash', 'width:16px;height:16px')}</button></div>
        <button class="sheetimg" data-open="${s.id}"><img alt="Front, three-quarter, side and back views of ${esc(s.meta?.name || '')}" data-src="${itemPath(s.id)}"></button><p class="mut">${esc(s.meta?.description || '')}</p></section>` : '';
    paintAll(g); hydrate(g); hydrate(d);
  }
  W.casting = el => {
    const refresh = () => redraw('casting', drawCast);
    load('items').then(refresh);
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.castfilm) { const it = items('cast').find(x => x.id === b.dataset.castfilm); DIR.castDraft = {name: it.meta?.name || '', description: it.meta?.description || ''};
        if (DIR.project) { DIR.castOpen = true; DIR.view = null; go('director'); } else { toast('Open or start a film, then add the character'); go('director', {focus: true}); } return; }
      if (await itemAction(b)) { refresh(); return; }
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; refresh(); return; }
      if (b.dataset.cast) { const [k, v] = b.dataset.cast.split('|'); CA[k] = v; $$(`[data-cast^="${k}|"]`).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.casel) { CA.sel = b.dataset.casel; drawCast(); return; }
      if (b.id === 'caGo') { const name = $('#caname').value.trim(), desc = $('#cadesc').value.trim(); if (!name || desc.length < 6) { toast('Give a name and describe the look'); return; }
        try { await startJob({kind: 'cast', name, prompt: desc, style: CA.style, voice: CA.voice, quality: 'best'}, refresh); $('#caname').value = $('#cadesc').value = ''; } catch (er) { toast(er.message, true); } }
    });
  };

  /* ---------------- music ---------------- */
  const MU = {tab: 'Song', brief: '', genre: 'Bollywood romantic', lang: 'Hindi', vox: 'Duet', mood: 'Warm', bpm: 92, len: '2 min', lyrics: ''};
  const GENRES = ['Bollywood romantic', 'Punjabi pop', 'Sufi', 'Indie pop', 'Lo-fi', 'Carnatic fusion', 'Garba', 'Ghazal', 'Hip-hop', 'Devotional', 'Film score', 'Jingle'];
  const CYC = {lang: ['Hindi', 'Hinglish', 'Punjabi', 'Tamil', 'Telugu', 'Marathi', 'Bengali', 'English'], vox: ['Duet', 'Female', 'Male', 'Choir'], mood: ['Warm', 'Joyful', 'Romantic', 'Energetic', 'Sad', 'Devotional', 'Epic', 'Calm'], len: ['30 s', '1 min', '2 min', '3 min']};
  const vocal = () => MU.tab === 'Song';
  V.music = () => `<div class="gen"><div class="panel"><div class="pbody">
    ${toolTabs('music')}
    <div class="seg" role="group" aria-label="Kind">${['Song', 'Instrumental', 'Jingle', 'Score'].map(t => `<button aria-pressed="${t === MU.tab}" data-mtab="${t}">${t}</button>`).join('')}</div>
    <div class="box"><h3>Describe the ${MU.tab.toLowerCase()}</h3><textarea id="muq" rows="3" maxlength="1200" placeholder="A warm Hindi duet about a chai shop where two strangers meet every rainy evening, soft guitar, tabla, big chorus">${esc(MU.brief)}</textarea></div>
    <div class="lbl">Genre</div><div class="chips">${GENRES.map(g => `<button class="chip" aria-pressed="${g === MU.genre}" data-genre="${esc(g)}">${g}</button>`).join('')}</div>
    <div class="prow2">${vocal() ? `<button class="prow" data-cyc="lang"><span class="pi">${I('globe', 'width:16px;height:16px')}</span><div><small>Language</small><b>${MU.lang}</b></div></button><button class="prow" data-cyc="vox"><span class="pi">${I('mic', 'width:16px;height:16px')}</span><div><small>Singers</small><b>${MU.vox}</b></div></button>` : ''}
      <button class="prow" data-cyc="mood"><span class="pi">${I('spark', 'width:16px;height:16px')}</span><div><small>Mood</small><b>${MU.mood}</b></div></button><button class="prow" data-cyc="len"><span class="pi">${I('sliders', 'width:16px;height:16px')}</span><div><small>Length</small><b>${MU.len}</b></div></button></div>
    <div class="box"><h3>Tempo <span class="num mut" id="bpmv">${MU.bpm} BPM</span></h3><input class="slider" type="range" min="60" max="180" value="${MU.bpm}" id="bpm" aria-label="Tempo"></div>
    ${vocal() ? `<div class="box"><h3>Lyrics <button class="lnk" data-write ${MU.writing ? 'disabled' : ''}>${I('pen', 'width:14px;height:14px')} ${MU.writing ? 'Writing…' : 'Write with Hoola'}</button></h3><textarea id="lyr" rows="7" maxlength="3000" placeholder="Leave empty and the song gets its own words, or paste yours">${esc(MU.lyrics)}</textarea></div>` : ''}
    <p class="note">Made by Google Lyria. Your own lyrics stay word for word.</p>
  </div><div class="pfoot"><button class="create" id="muGo">${I('music', 'width:17px;height:17px')}Create ${MU.tab.toLowerCase()} <small class="num">~₹7</small></button></div></div>
  <div class="stage"><div class="sbar"><b>Your tracks</b><span class="sp"></span></div><div class="pbody" id="tracks" style="padding:14px"></div></div></div>`;
  function trackHTML(it) {
    const m = it.meta || {};
    return `<div class="track" data-item="${it.id}"><span class="cover">${art(it.kind === 'voice' ? 'voice' : 'music', it.id)}</span><div class="tt"><b>${esc(it.title)}</b><small>${esc([m.genre, m.language, m.vocals || m.voice, m.style, m.mood].filter(Boolean).join(' · ') || when(it.created))}</small>
      <canvas class="wave" aria-hidden="true"></canvas><audio preload="metadata" data-src="${itemPath(it.id)}" hidden></audio></div>
      <button class="play" data-play aria-label="Play">${I('play', 'width:16px;height:16px')}</button><button class="ib" data-dl="${it.id}" aria-label="Download">${I('dl')}</button><button class="ib" data-del="${it.id}" aria-label="Delete">${I('trash', 'width:16px;height:16px')}</button></div>`;
  }
  function trackJob(j) { return `<div class="track gening"><span class="cover">${art(j.kind === 'voice' ? 'voice' : 'music', j.id)}</span><div class="tt"><b>${esc(j.title)}</b><small>${j.kind === 'song' ? 'Composing and singing… about a minute' : 'Recording…'}</small><div class="bar"><i class="indet"></i></div></div></div>`; }
  // a real waveform from the decoded audio (falls back to a flat line), with the played part in the brand gradient
  async function wave(audio, blob) {
    const cv = audio.parentElement?.querySelector('canvas.wave'); if (!cv) return;
    let peaks = null;
    try { const buf = await blob.arrayBuffer(); const ac = new (window.AudioContext || window.webkitAudioContext)();
      const d = (await ac.decodeAudioData(buf)).getChannelData(0); ac.close?.(); const n = 120, step = Math.floor(d.length / n) || 1;
      peaks = Array.from({length: n}, (_, i) => { let m = 0; for (let k = i * step; k < (i + 1) * step && k < d.length; k += 16) m = Math.max(m, Math.abs(d[k])); return m; });
      const top = Math.max(...peaks) || 1; peaks = peaks.map(v => v / top); } catch {}
    const draw = () => { const dpr = Math.min(devicePixelRatio || 1, 2), w = cv.clientWidth, h = cv.clientHeight; if (!w) return;
      cv.width = w * dpr; cv.height = h * dpr; const x = cv.getContext('2d'); x.scale(dpr, dpr);
      const prog = audio.duration ? audio.currentTime / audio.duration : 0, n = Math.floor(w / 4), cs = getComputedStyle(host);
      for (let i = 0; i < n; i++) { const v = peaks ? peaks[Math.floor(i / n * peaks.length)] : .15; const bh = Math.max(2, Math.min(1, v) * h * .9);
        x.fillStyle = i / n < prog ? cs.getPropertyValue('--pri').trim() || '#5B45E0' : cs.getPropertyValue('--hair2').trim() || '#ccc'; x.beginPath(); x.roundRect(i * 4, h / 2 - bh / 2, 2.5, bh, 1.5); x.fill(); } };
    audio.addEventListener('timeupdate', draw); audio.addEventListener('loadedmetadata', draw); draw();
    cv.addEventListener('click', e => { if (!audio.duration) return; const r = cv.getBoundingClientRect(); audio.currentTime = (e.clientX - r.left) / r.width * audio.duration; draw(); });
  }
  function playToggle(b) {
    const a = b.closest('.track')?.querySelector('audio'); if (!a || !a.src) return;
    $$('audio').forEach(x => { if (x !== a && !x.paused) { x.pause(); x.closest('.track').querySelector('[data-play]').innerHTML = I('play', 'width:16px;height:16px'); } });
    if (a.paused) { a.play(); b.innerHTML = I('pause', 'width:16px;height:16px'); a.onended = () => b.innerHTML = I('play', 'width:16px;height:16px'); }
    else { a.pause(); b.innerHTML = I('play', 'width:16px;height:16px'); }
  }
  function drawTracks(kind) {
    const el = $('#tracks'); if (!el) return;
    el.innerHTML = running(kind).map(trackJob).join('') + failed(kind).map(j => `<div class="track"><div class="tt"><b>${esc(j.title)}</b><small class="bad">${esc(j.error)}</small></div><button class="lnk" data-seen="${j.id}">Dismiss</button></div>`).join('')
      + items(kind).map(trackHTML).join('') || empty(kind === 'song' ? 'Your songs appear here' : 'Your voice-overs appear here', 'Each one comes with a download, and a copy in your chat.');
    paintAll(el); hydrate(el);
  }
  W.music = (el, o) => {
    const refresh = () => redraw('music', () => drawTracks('song'));
    load('items').then(refresh);
    const q = $('#muq'); q.addEventListener('input', () => MU.brief = q.value);
    $('#lyr')?.addEventListener('input', e => MU.lyrics = e.target.value);
    $('#bpm').addEventListener('input', e => { MU.bpm = +e.target.value; $('#bpmv').textContent = MU.bpm + ' BPM'; });
    const create = async () => {
      MU.brief = q.value.trim(); if (!MU.brief && !MU.lyrics.trim()) { q.focus(); toast('Describe the song first'); return; }
      const secs = {'30 s': 30, '1 min': 60, '2 min': 120, '3 min': 180}[MU.len];
      const genre = MU.tab === 'Jingle' ? 'Jingle, ' + MU.genre : MU.tab === 'Score' ? 'Film score, ' + MU.genre : MU.genre;
      try { await startJob({kind: 'song', brief: MU.brief, genre, language: MU.lang, vocals: vocal() ? MU.vox.toLowerCase() : 'none', mood: MU.mood, bpm: MU.bpm, seconds: secs, lyrics: vocal() ? MU.lyrics : '', title: (MU.brief || MU.genre).slice(0, 48)}, refresh); }
      catch (e) { toast(e.message, true); }
    };
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-play')) { playToggle(b); return; }
      if (await itemAction(b)) return;
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; refresh(); return; }
      if (b.dataset.mtab) { MU.tab = b.dataset.mtab; MU.brief = q.value; go('music'); return; }
      if (b.dataset.genre) { MU.genre = b.dataset.genre; $$('[data-genre]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.cyc) { const k = b.dataset.cyc;
        menu(b, opt(CYC[k]), MU[k], v => { MU[k] = v; b.querySelector('b').textContent = v; }, {lang: 'Language', vox: 'Singers', mood: 'Mood', len: 'Length'}[k]); return; }
      if (b.hasAttribute('data-write')) { const idea = q.value.trim(); if (idea.length < 4) { q.focus(); toast('Describe the song first, then Hoola writes the words'); return; }
        MU.writing = true; MU.brief = idea; go('music');
        try { const r = await api('POST', '/api/create/write', {kind: 'lyrics', brief: idea, genre: MU.genre, language: MU.lang, mood: MU.mood}); MU.lyrics = r.text; } catch (er) { toast(er.message, true); }
        MU.writing = false; if (VIEW === 'music') go('music'); return; }
      if (b.id === 'muGo') create();
    });
    if (o.autostart) create();
  };

  /* ---------------- voice ---------------- */
  const VO = {text: '', voice: 'mine', g: 'all', style: 'friendly', speed: 1, lang: 'Hindi'};
  V.voice = () => { const vs = D.conf?.voices || {male: {}, female: {}};
    const list = [['mine', 'Your Hoola’s voice', 'The voice your Hoola speaks with on calls', 'voice'],
      ...(VO.g !== 'male' ? Object.entries(vs.female).map(([n, d]) => [n, n, 'Female · ' + d, 'portrait']) : []),
      ...(VO.g !== 'female' ? Object.entries(vs.male).map(([n, d]) => [n, n, 'Male · ' + d, 'portrait']) : [])];
    return `<div class="gen"><div class="panel"><div class="pbody">
    ${toolTabs('voice')}
    <div class="box"><h3>Script <span class="dim num" style="font-size:12px;font-weight:400" id="voCount">${VO.text.length} / 5000</span></h3>
      <textarea id="voq" rows="6" maxlength="5000" placeholder="Is Diwali, apne ghar ko roshan kijiye. Newtika chai ke saath, har shaam khaas.">${esc(VO.text)}</textarea></div>
    <div class="lbl">Language</div><div class="chips">${['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'].map(l => `<button class="chip" aria-pressed="${l === VO.lang}" data-volang="${l}">${l}</button>`).join('')}</div>
    <div class="lbl">Voice</div><div class="seg"><button aria-pressed="${VO.g === 'all'}" data-vog="all">All</button><button aria-pressed="${VO.g === 'female'}" data-vog="female">Female</button><button aria-pressed="${VO.g === 'male'}" data-vog="male">Male</button></div>
    <div class="vlist">${list.map(([k, n, d, a]) => `<button class="opt" role="radio" aria-checked="${k === VO.voice}" data-vo="${esc(k)}"><span class="thumb">${art(a, 'vo' + k)}</span><div><b>${esc(n)}</b><small>${esc(d)}</small></div></button>`).join('')}</div>
    <div class="lbl">Style</div><div class="grid-opts">${Object.keys(D.conf?.styles ? Object.fromEntries(D.conf.styles.map(s => [s, 1])) : {friendly: 1, calm: 1, excited: 1, news: 1, story: 1, ad: 1}).map(s => `<button class="go" aria-pressed="${s === VO.style}" data-vostyle="${s}">${s[0].toUpperCase() + s.slice(1)}</button>`).join('')}</div>
    <div class="lbl">Pace <span class="num" id="spd">${VO.speed.toFixed(1)}x</span></div><input class="slider" type="range" min="0.6" max="1.6" step="0.1" value="${VO.speed}" id="voSpeed" aria-label="Pace">
  </div><div class="pfoot"><button class="create" id="voGo">${I('sound', 'width:17px;height:17px')}Make voice-over</button></div></div>
  <div class="stage"><div class="sbar"><b>Your voice-overs</b><span class="sp"></span></div><div class="pbody" id="tracks" style="padding:14px"></div></div></div>`; };
  W.voice = (el, o) => {
    const refresh = () => redraw('voice', () => drawTracks('voice'));
    load('items').then(refresh);
    if (!D.conf) load('conf').then(() => { if (VIEW === 'voice') { VO.text = $('#voq').value; go('voice'); } });
    const q = $('#voq'); q.addEventListener('input', () => { VO.text = q.value; $('#voCount').textContent = q.value.length + ' / 5000'; });
    $('#voSpeed').addEventListener('input', e => { VO.speed = +e.target.value; $('#spd').textContent = VO.speed.toFixed(1) + 'x'; });
    const create = async () => { VO.text = q.value.trim(); if (!VO.text) { q.focus(); toast('Write what to say first'); return; }
      try { await startJob({kind: 'voice', text: VO.text, voice: VO.voice, language: VO.lang, style: VO.style, speed: VO.speed, title: VO.text.split(/[.!?\n]/)[0].slice(0, 48)}, refresh); } catch (e) { toast(e.message, true); } };
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-play')) { playToggle(b); return; }
      if (await itemAction(b)) return;
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; refresh(); return; }
      if (b.dataset.vo) { VO.voice = b.dataset.vo; $$('[data-vo]').forEach(x => x.setAttribute('aria-checked', String(x === b))); return; }
      if (b.dataset.vog) { VO.g = b.dataset.vog; VO.text = q.value; go('voice'); return; }
      if (b.dataset.volang) { VO.lang = b.dataset.volang; $$('[data-volang]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.vostyle) { VO.style = b.dataset.vostyle; $$('[data-vostyle]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.id === 'voGo') create();
    });
    if (o.autostart) create();
  };

  /* ---------------- dubbing ---------------- */
  const LANGS = ['Hindi', 'Hinglish', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi', 'Odia', 'Urdu', 'English', 'Spanish', 'Arabic'];
  const DB = {src: null, to: ['Tamil'], keep: true, sel: '', tab: ''};
  V.dubbing = () => `<div class="split"><aside>
    <button class="refs" data-dubsrc>${DB.src ? `<span class="stack"><i>${I('video', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>${esc(DB.src.name)}</b><small>${(DB.src.size / 1048576).toFixed(1)} MB · tap to change</small></div>` : `<span class="stack"><i>${I('upload', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>Upload your video</b><small>MP4 / MOV / WebM · up to 25 MB and 3 minutes</small></div>`}</button>
    ${DB.src ? `<video class="srcv" controls playsinline src="${esc(DB.src.local)}"></video>` : ''}
    <div class="lbl">Dub into · up to 4</div><div class="langs">${LANGS.map(l => `<button class="chip" aria-pressed="${DB.to.includes(l)}" data-lang="${l}">${l}</button>`).join('')}</div>
    <div class="prow"><div><b style="white-space:normal">Keep music and background sound</b><small>The original plays softly under the new voices</small></div><button class="sw" role="switch" aria-checked="${DB.keep}" data-dkeep aria-label="Keep music and background sound"><i></i></button></div>
    <button class="create" style="flex:none" id="dubGo">${I('dub', 'width:17px;height:17px')}Dub now</button>
    <p class="note">Hoola listens once, writes each line in the new language and speaks it in a voice matched to each speaker. Voices are matched, not cloned; lips are not re-synced (lip sync is a paid Video Studio step).</p>
    <div class="lbl">Your dubs</div><div class="mini" id="dublist"></div>
  </aside><section><div style="padding:16px;display:flex;flex-direction:column;gap:14px" id="dubview"></div></section></div>`;
  function drawDub() {
    const l = $('#dublist'), v = $('#dubview'); if (!l) return;
    const its = items('dub');
    l.innerHTML = its.map(it => `<button class="mrow${it.id === DB.sel ? ' on' : ''}" data-dubsel="${it.id}"><b>${esc(it.title)}</b><small>${when(it.created)}</small></button>`).join('') || '<p class="mut" style="font-size:13px">Your dubbed videos are kept here.</p>';
    const jobs = running('dub'), bad = failed('dub');
    const it = its.find(x => x.id === DB.sel) || (!jobs.length && its[0]); if (it) DB.sel = it.id;
    if (jobs.length) { v.innerHTML = jobs.map(j => `<div class="box"><b>${esc(j.title)}</b><small class="mut">${esc(j.step === 'listening' ? 'Listening to who says what' : j.step ? j.step[0].toUpperCase() + j.step.slice(1) : 'Starting')}…</small><div class="bar"><i class="indet"></i></div></div>`).join(''); return; }
    if (bad.length) { v.innerHTML = bad.map(j => `<div class="box"><b class="bad">${esc(j.error)}</b><button class="lnk" data-seen="${j.id}">Dismiss</button></div>`).join(''); return; }
    if (!it) { v.innerHTML = empty('Your video, in another language', 'Upload a video on the left, pick languages and press Dub now. Each language comes back as its own video.'); return; }
    const m = it.meta || {}, lang = m.language;
    v.innerHTML = `<div class="player"><video controls playsinline data-src="${itemPath(it.id)}"></video></div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><b>${esc(it.title)}</b><span class="tag">${esc(m.source_language || 'Original')} → ${esc(lang)}</span><span style="flex:1"></span><button class="pillbtn" data-dl="${it.id}">${I('dl', 'width:15px;height:15px')}Download</button><button class="ib" data-del="${it.id}" aria-label="Delete">${I('trash', 'width:16px;height:16px')}</button></div>
      ${(m.lines || []).length ? `<div class="trans"><div class="trow head"><span>Time</span><span>Speaker</span><span class="src">Original</span><span>${esc(lang)}</span></div>
        ${m.lines.map(ln => `<div class="trow"><span class="t num">${Math.floor((ln.start || 0) / 60)}:${String(Math.floor((ln.start || 0) % 60)).padStart(2, '0')}</span><span class="spk"><i style="background:${ln.speaker === 'S1' ? 'var(--mag)' : ln.speaker === 'S2' ? 'var(--vio)' : 'var(--saf)'}"></i>${esc(ln.speaker || '')}</span><span class="src mut">${esc(ln.text || '')}</span><span>${esc((ln.tr || {})[lang] || '')}</span></div>`).join('')}</div>` : ''}`;
    hydrate(v);
  }
  W.dubbing = el => {
    const refresh = () => redraw('dubbing', drawDub);
    load('items').then(refresh);
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (await itemAction(b)) { refresh(); return; }
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; refresh(); return; }
      if (b.hasAttribute('data-dubsrc')) { const [f] = await pick('video/mp4,video/quicktime,video/webm,video/x-matroska'); if (!f) return;
        b.disabled = true; toast('Uploading ' + f.name);
        try { DB.src = await upload(f, /^video\//); go('dubbing'); } catch (er) { toast(er.message, true); b.disabled = false; } return; }
      if (b.dataset.lang) { const l = b.dataset.lang; if (DB.to.includes(l)) DB.to = DB.to.filter(x => x !== l); else if (DB.to.length < 4) DB.to.push(l); else { toast('Up to 4 languages at a time'); return; }
        $$('[data-lang]').forEach(x => x.setAttribute('aria-pressed', String(DB.to.includes(x.dataset.lang)))); return; }
      if (b.hasAttribute('data-dkeep')) { DB.keep = !DB.keep; b.setAttribute('aria-checked', String(DB.keep)); return; }
      if (b.dataset.dubsel) { DB.sel = b.dataset.dubsel; drawDub(); return; }
      if (b.id === 'dubGo') { if (!DB.src) { toast('Upload your video first'); return; } if (!DB.to.length) { toast('Pick a language'); return; }
        DB.sel = ''; try { await startJob({kind: 'dub', file_id: DB.src.file_id, languages: DB.to, keep_sound: DB.keep, title: DB.src.name.replace(/\.[^.]+$/, '').slice(0, 40) + ' · ' + DB.to.join(', ')}, refresh); } catch (er) { toast(er.message, true); } }
    });
  };

  /* ---------------- video editor (her clips, edited by words) ---------------- */
  const ED_STATUS = {queued: 'Waiting in line', watching: 'Watching your clips', planning: 'Planning the edit', rendering: 'Rendering', checking: 'Checking the result'};
  const ED = {clips: [], brief: '', platform: 'reel', length: '', captions: true, job: '', jobs: null, platforms: null};
  V.editor = () => { const j = ED.jobs?.find(x => x.id === ED.job), lt = j?.latest;
    return `<div class="ed">
  <div class="bin"><div class="sec-h" style="margin:0"><h2 style="font-size:14px">Your clips</h2><button class="ib" aria-label="Add clips" data-addclip>${I('upload', 'width:16px;height:16px')}</button></div>
    ${ED.clips.length ? ED.clips.map((c, i) => `<div class="clipcard"><span class="thumb">${c.type.startsWith('image/') ? `<img alt="" src="${esc(c.local)}">` : c.type.startsWith('video/') ? `<video muted preload="metadata" src="${esc(c.local)}"></video>` : I('music', 'width:22px;height:22px;margin:auto')}</span><div><b>${i + 1}. ${esc(c.name)}</b><small>${(c.size / 1048576).toFixed(1)} MB</small></div>
      <span class="ord"><button class="ib" data-mv="${i}|-1" aria-label="Move up" ${i ? '' : 'disabled'}>${I('send', 'width:13px;height:13px')}</button><button class="ib" data-rm="${i}" aria-label="Remove">${I('x', 'width:13px;height:13px')}</button></span></div>`).join('')
      : `<button class="refs" data-addclip><span class="stack"><i>${I('upload', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>Add your clips</b><small>Videos, photos, music · up to 8 · 25 MB each</small></div></button>`}
    <div class="lbl">Recent edits</div><div class="mini" id="edjobs"></div></div>
  <div class="viewer"><div class="screen"><div class="frame">${lt?.url ? `<video controls playsinline src="${esc(lt.url)}"></video>` : j && j.status !== 'failed' ? `<div class="framemsg"><span class="ring"></span><b>${esc(ED_STATUS[j.status] || 'Working')}</b><small>${j.progress || 0}%</small></div>` : `<div class="framemsg">${I('cut', 'width:30px;height:30px')}<b>Your edit plays here</b><small>Add clips, say what you want, press Make the edit</small></div>`}</div></div>
    ${j?.error ? `<p class="bad" style="padding:0 16px">${esc(j.error)}</p>` : ''}
    <form class="ask" id="edAsk">${I('spark', 'width:16px;height:16px;color:var(--pri)')}<input id="edq" maxlength="1500" placeholder="${lt ? 'Change it: make the intro shorter, add Hindi captions, slower music…' : 'Say what to make: a 30 s reel, fast cuts on the beat, captions in Hindi…'}" aria-label="Tell Hoola what to change" value="${esc(lt ? '' : ED.brief)}"><button class="send" style="width:32px;height:32px" aria-label="${lt ? 'Change' : 'Make the edit'}">${I('send', 'width:16px;height:16px')}</button></form></div>
  <div class="insp"><h3>Made for</h3><select id="edplat" class="sel">${(ED.platforms || [{id: 'reel', label: 'Instagram Reel'}]).map(p => `<option value="${esc(p.id)}"${p.id === ED.platform ? ' selected' : ''}>${esc(p.label)}${p.aspect ? ' · ' + p.aspect : ''}</option>`).join('')}</select>
    <h3>Length</h3><div class="grid-opts">${['', '15', '30', '60'].map(s => `<button class="go" aria-pressed="${s === ED.length}" data-edlen="${s}">${s ? s + ' s' : 'Auto'}</button>`).join('')}</div>
    <div class="prow"><div><b>Captions</b><small>Words on screen</small></div><button class="sw" role="switch" aria-checked="${ED.captions}" data-edcap aria-label="Captions"><i></i></button></div>
    <h3>Quick asks</h3><div class="aitools">${[['Cut the silences', 'cut'], ['Hindi captions', 'text'], ['Make it 9:16', 'grid'], ['Beat-synced cuts', 'music'], ['Brighter colours', 'wand'], ['Shorter intro', 'minus']].map(([t, ic]) => `<button data-ai="${t}">${I(ic, 'width:14px;height:14px')}${t}</button>`).join('')}</div>
    <button class="create" style="flex:none" id="edGo" ${ED.clips.length ? '' : 'disabled'}>${I('cut', 'width:16px;height:16px')}Make the edit</button>
    ${lt ? `<a class="btn sec" href="${esc(lt.url)}" download="${esc(lt.name || 'hoola-edit.mp4')}">${I('dl', 'width:16px;height:16px')}Download v${lt.n}</a>` : ''}
    ${j?.post_caption ? `<h3>Post caption</h3><p class="mut" style="font-size:13px">${esc(j.post_caption)}</p>` : ''}</div>
  <div class="timeline"><div class="tlbar"><span>Story order</span><span style="flex:1"></span><span class="num">${ED.clips.length} clip${ED.clips.length === 1 ? '' : 's'}${j?.versions?.length ? ' · ' + j.versions.length + ' version' + (j.versions.length > 1 ? 's' : '') : ''}</span></div>
    <div class="strip">${ED.clips.map((c, i) => `<span class="sclip" style="flex:${c.type.startsWith('video/') ? 3 : 1}"><b>${i + 1}</b>${esc(c.name)}</span>`).join('') || '<span class="mut" style="padding:10px">Clips play in this order. Move them up or down on the left.</span>'}</div>
    ${j?.versions?.length > 1 ? `<div class="vers">${j.versions.map(v => `<span class="tag">v${v.n}</span>`).join('')}</div>` : ''}</div></div>`; };
  function drawEdJobs() {
    const el = $('#edjobs'); if (!el) return;
    el.innerHTML = (ED.jobs || []).slice(0, 8).map(j => `<button class="mrow${j.id === ED.job ? ' on' : ''}" data-edjob="${esc(j.id)}"><b>${esc(j.title || j.brief || 'Edit')}</b><small>${esc(j.platform_label || '')} · ${esc(j.status)}</small></button>`).join('') || '<p class="mut" style="font-size:13px">Your edits are kept here.</p>';
  }
  async function edLoad() {
    try { const r = await api('GET', '/api/video/jobs'); ED.jobs = r.jobs || []; ED.platforms = r.platforms || ED.platforms; } catch { ED.jobs = ED.jobs || []; }
  }
  W.editor = el => {
    const n = alive;
    if (!ED.jobs) { edLoad().then(() => { if (n === alive) go('editor'); }); }
    else drawEdJobs();
    const j = ED.jobs?.find(x => x.id === ED.job);
    if (j && ['queued', 'watching', 'planning', 'rendering', 'checking'].includes(j.status)) poll = setTimeout(async () => { await edLoad(); if (VIEW === 'editor') go('editor'); }, 4000);
    $('#edplat').addEventListener('change', e => ED.platform = e.target.value);
    $('#edAsk').addEventListener('submit', async e => { e.preventDefault(); const t = $('#edq').value.trim(); if (!t) return;
      const cur = ED.jobs?.find(x => x.id === ED.job);
      if (cur?.latest) { try { await api('POST', `/api/video/jobs/${encodeURIComponent(cur.id)}/revise`, {instruction: t}); toast('Making the change'); await edLoad(); go('editor'); } catch (er) { toast(er.message, true); } }
      else { ED.brief = t; $('#edGo').click(); } });
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b || b.disabled) return;
      if (b.hasAttribute('data-addclip')) { const fs = await pick('video/*,image/png,image/jpeg,image/webp,audio/*', true);
        for (const f of fs.slice(0, 8 - ED.clips.length)) { try { toast('Uploading ' + f.name); ED.clips.push(await upload(f)); } catch (er) { toast(er.message, true); } } go('editor'); return; }
      if (b.dataset.rm) { ED.clips.splice(+b.dataset.rm, 1); go('editor'); return; }
      if (b.dataset.mv) { const [i] = b.dataset.mv.split('|').map(Number); [ED.clips[i - 1], ED.clips[i]] = [ED.clips[i], ED.clips[i - 1]]; go('editor'); return; }
      if (b.dataset.edlen !== undefined) { ED.length = b.dataset.edlen; $$('[data-edlen]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.hasAttribute('data-edcap')) { ED.captions = !ED.captions; b.setAttribute('aria-checked', String(ED.captions)); return; }
      if (b.dataset.ai) { const q = $('#edq'); q.value = (q.value ? q.value.replace(/[.\s]*$/, '. ') : '') + b.dataset.ai; q.focus(); return; }
      if (b.dataset.edjob) { ED.job = b.dataset.edjob; go('editor'); return; }
      if (b.id === 'edGo') { const brief = ($('#edq').value.trim() || ED.brief || 'Make a polished edit from these clips').slice(0, 3000);
        b.disabled = true;
        try { const r = await api('POST', '/api/video/jobs', {file_ids: ED.clips.map(c => c.file_id), brief, platform: ED.platform, length_s: ED.length ? +ED.length : null, captions: ED.captions, title: brief.slice(0, 48), conversation_id: await convId().catch(() => '')});
          ED.job = r.id; ED.brief = ''; toast('Editing your video'); await edLoad(); } catch (er) { toast(er.message, true); }
        go('editor'); }
    });
  };

  /* ---------------- templates / library / projects / brand / learn ---------------- */
  let tplCat = 'All';
  const TCAT = {All: () => true, Video: s => s[1] === 'video', Image: s => s[1] === 'image', Music: s => s[1] === 'music', Voice: s => s[1] === 'voice'};
  V.templates = () => `<div class="home"><div class="hero" style="padding-top:0"><h1>Templates</h1><p class="mut">Pick one, change the words, press Create.</p><div class="chips" style="justify-content:center">${Object.keys(TCAT).map(c => `<button class="chip" aria-pressed="${c === tplCat}" data-cat="${c}">${c}</button>`).join('')}</div></div>
    <section><div class="sec-h"><h2>Starters</h2></div><div class="qs">${STARTERS.map((s, i) => [s, i]).filter(([s]) => TCAT[tplCat](s)).map(([[t, v, k], i]) => `<button class="tpl" data-start="${i}"><span class="thumb">${art(k, 'tt' + i)}<span class="use">Use</span></span><b>${t}</b><small>${TITLE[v]}</small></button>`).join('')}</div></section>
    <section><div class="sec-h"><h2>Films with the Director</h2></div><div class="qs">${QUICK.map(([t, k, d], i) => `<button class="qcard" data-quick="${i}"><span class="thumb">${art(k, 'tq' + i)}<span class="dur">${d}</span></span><b>${t}</b></button>`).join('')}</div></section></div>`;
  W.templates = el => el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.cat) { tplCat = b.dataset.cat; go('templates'); }
    if (b.dataset.start) starter(+b.dataset.start);
    if (b.dataset.quick) { const q = QUICK[+b.dataset.quick]; DIR.brief = q[3]; DIR.project = ''; DIR.view = null; go('director', {focus: true}); } });
  let libF = 'all';
  let libQ = '', libSort = 'new';
  const LIBS = {new: 'Newest first', old: 'Oldest first', az: 'Name A–Z'};
  const LIBF = [['all', 'All'], ['image', 'Pictures'], ['cast', 'Cast'], ['song', 'Songs'], ['voice', 'Voice-overs'], ['dub', 'Dubs'], ['script', 'Scripts'], ['film', 'Films']];
  V.library = () => `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 28px/1.2 var(--serif)">My creations</h2><span class="dim" style="font-size:13px">Kept until you delete them</span></div>
    <div class="libbar"><div class="chips">${LIBF.map(([k, n]) => `<button class="chip" aria-pressed="${k === libF}" data-lib="${k}">${n}</button>`).join('')}</div>
      <span class="sp"></span><label class="lsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search my creations</span><input id="libq" type="search" placeholder="Search" value="${esc(libQ)}"></label>
      <button type="button" class="dd" id="libSort" aria-label="Sort">${I('layers', 'width:15px;height:15px')}<span>${LIBS[libSort]}</span>${I('down', 'width:14px;height:14px')}</button></div>
    <div class="sgrid lib" id="results"></div></div>`;
  function drawLib() {
    const el = $('#results'); if (!el) return;
    const q = libQ.trim().toLowerCase(), hit = t => !q || String(t || '').toLowerCase().includes(q);   // v0.304 search + sort, in the browser
    const order = (L, t, k) => L.sort((a, b) => libSort === 'az' ? String(t(a)).localeCompare(String(t(b))) : libSort === 'old' ? k(a) - k(b) : k(b) - k(a));
    const its = order((libF === 'film' ? [] : items(libF === 'all' ? '' : libF).filter(i => i.kind !== 'script' || libF === 'script' || libF === 'all')).filter(i => hit(i.title)), i => i.title, i => i.created || 0);
    const films = order(((libF === 'all' || libF === 'film') ? (D.studio?.projects || []).filter(p => (p.outputs || []).length) : []).filter(p => hit(p.title || p.name)), p => p.title || p.name, p => p.updated || p.created || 0);
    el.innerHTML = films.map(projTile).join('') + its.map(it => it.kind === 'script' ? `<div class="res" data-item="${it.id}"><button class="thumb doc-th" data-scopen="${it.id}">${I('pen', 'width:26px;height:26px')}</button><span class="acts"><button data-dl="${it.id}" aria-label="Download">${I('dl')}</button><button data-del="${it.id}" aria-label="Delete">${I('trash')}</button></span><b class="rt">${esc(it.title)}</b><small>${when(it.created)}</small></div>` : it.kind === 'song' || it.kind === 'voice' ? `<div class="res" data-item="${it.id}"><button class="thumb" data-open="${it.id}">${art(it.kind === 'voice' ? 'voice' : 'music', it.id)}</button><span class="acts"><button data-dl="${it.id}" aria-label="Download">${I('dl')}</button><button data-del="${it.id}" aria-label="Delete">${I('trash')}</button></span><b class="rt">${esc(it.title)}</b><small>${esc(it.kind === 'song' ? 'Song' : 'Voice-over')} · ${when(it.created)}</small></div>` : itemTile(it)).join('')
      || (q ? `<div class="empty" style="grid-column:1/-1"><div><h2>Nothing matches “${esc(libQ)}”</h2><p class="mut">Try another word, or clear the search.</p></div></div>` : '') || `<div class="empty" style="grid-column:1/-1"><div><h2>Nothing here yet</h2><p class="mut">Pictures, songs, voice-overs, dubs, scripts and films you make in Create are kept here.</p></div></div>`;
    paintAll(el); hydrate(el);
  }
  W.library = el => {
    Promise.all([load('items'), load('studio')]).then(() => redraw('library', drawLib));
    $('#libq', el).addEventListener('input', e => { libQ = e.target.value; drawLib(); });
    $('#libSort', el).addEventListener('click', e => menu(e.currentTarget, Object.entries(LIBS).map(([v, label]) => ({v, label})), libSort,
      v => { libSort = v; $('#libSort span').textContent = LIBS[v]; drawLib(); }, 'Sort by'));
    el.addEventListener('click', async e => { const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.lib) { libF = b.dataset.lib; $$('[data-lib]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); drawLib(); return; }
      if (b.dataset.scopen) { try { const r = await api('GET', itemPath(b.dataset.scopen), undefined, {raw: true}); SC.text = await r.text(); SC.id = b.dataset.scopen; go('script'); } catch (er) { toast(er.message, true); } return; }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await load('studio', true); drawLib(); return; }
      await itemAction(b); });
  };
  /* ---------------- v0.307 ENGINES: the real AI services behind Create, checked live; keys never come to the browser ---------------- */
  const EST = {ready: ['Ready', 'ok'], unchecked: ['Key set', 'ok'], missing: ['No key', 'off'], refused: ['Key refused', 'bad'], unreachable: ['Not reachable', 'bad']};
  V.engines = () => `<div class="home eng">
    <div class="sec-h" style="margin:0"><div><h2 style="font:400 28px/1.2 var(--serif)">Engines</h2><p class="mut" style="margin-top:6px">The real AI services behind Create. Keys live only on your server (the .env), never in the app or the chat.</p></div>
      <button class="btn sec" data-recheck>${I('redo', 'width:15px;height:15px')}Check again</button></div>
    <div id="engs"><p class="mut">Checking each engine…</p></div></div>`;
  function drawEngines(r) {
    const el = $('#engs'); if (!el) return;
    if (!r) { el.innerHTML = '<p class="mut">Could not check the engines just now.</p>'; return; }
    el.innerHTML = `<div class="eg-feats">${r.features.map(f => `<span class="eg-feat ${f.ready ? 'eg-on' : ''}" title="${esc(f.why || 'Ready')}">${I(f.ready ? 'check' : 'x', 'width:13px;height:13px')}${esc(f.name)}</span>`).join('')}</div>
      <p class="dim" style="font-size:12.5px;margin:10px 0 2px">Checked ${when(r.checked_at).replace('Just now', 'just now')} with free calls only (a key or model list), never a paid job.${r.ffmpeg ? '' : ' ffmpeg is missing on the server: dubbing and the editor need it.'}</p>
      <div class="eg-list">${r.engines.map(e => { const [label, tone] = EST[e.state] || [e.state, 'off'], good = tone === 'ok';
        return `<div class="eg-card eg-${tone}"><div class="eg-h"><b>${esc(e.name)}</b><span class="eg-st eg-${tone}">${label}</span></div>
          <p class="mut eg-d">${esc(e.detail)}</p>
          <div class="eg-p">${e.powers.map(p => `<span>${esc(p)}</span>`).join('')}</div>
          <p class="dim eg-c">${esc(e.cost)}${e.need ? '' : ' · optional'}</p>
          ${good ? '' : `<details class="eg-how"${e.need ? ' open' : ''}><summary>${I('down', 'width:14px;height:14px')}How to switch it on</summary><ol>
            <li>Get a key: <a href="${esc(e.get)}" target="_blank" rel="noopener noreferrer">${esc(e.get.replace(/^https:\/\//, ''))}</a></li>
            <li>On the VPS, add one line to <code>~/apps/santosh-core/.env</code>: <code>${esc(e.env[0])}=your-key</code></li>
            <li>Restart: <code>pm2 restart santosh --update-env</code></li>
            <li>Press <b>Check again</b> (or run the VPS ops job <code>studio_apis</code>).</li></ol>
            <p class="dim" style="font-size:12px">Never paste a key into the chat. If one was ever shared, make a new one and delete the old.</p></details>`}</div>`; }).join('')}</div>`;
  }
  W.engines = el => {
    const run = async fresh => { try { drawEngines(await api('GET', '/api/studio/apis' + (fresh ? '?fresh=1' : ''))); } catch (e) { drawEngines(null); toast(e.message, true); } };
    run(false);
    el.addEventListener('click', async e => { const b = e.target.closest('[data-recheck]'); if (!b) return; b.disabled = true; $('#engs').style.opacity = '.55'; await run(true); $('#engs').style.opacity = ''; b.disabled = false; });
  };
  V.projects = () => `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 28px/1.2 var(--serif)">Film projects</h2><button class="btn pri" data-newfilm>${I('plus', 'width:16px;height:16px')}New film</button></div><div class="scenes" id="films"></div></div>`;
  W.projects = el => { load('studio', true).then(() => redraw('projects', drawFilms));
    el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-newfilm')) { DIR.project = ''; DIR.view = null; go('director', {focus: true}); }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); } }); };
  V.brand = () => { const k = D.kit; if (!k) return `<div class="home"><p class="mut">Loading your brand kit…</p></div>`;
    const c = k.colors || {};
    return `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 28px/1.2 var(--serif)">Brand kit</h2><span class="dim" style="font-size:13px">Pictures can use it with one switch; the Brand tool in chat uses it everywhere</span></div>
    <div class="tools">
      <div class="box"><h3>Name</h3><input id="bkname" maxlength="120" value="${esc(k.name || '')}" placeholder="Your business name"></div>
      <div class="box"><h3>Tagline</h3><input id="bktag" maxlength="160" value="${esc(k.tagline || '')}" placeholder="Har shaam khaas"></div>
      <div class="box"><h3>Colours</h3><div style="display:flex;gap:8px;flex-wrap:wrap">${['primary', 'accent', 'dark', 'light'].filter(x => c[x]).map(x => `<span class="swatch"><i style="background:${esc(c[x])}"></i><small>${x} ${esc(c[x])}</small></span>`).join('')}</div></div>
      <div class="box"><h3>Font</h3><b>${esc((k.fonts || {})[k.font] || k.font || 'Default')}</b></div>
      <div class="box"><h3>Tone</h3><input id="bktone" maxlength="200" value="${esc(k.tone || '')}" placeholder="Warm, simple Hinglish"></div>
      <div class="box"><h3>Logo</h3><span class="mut">${k.logo ? 'Your logo is set ✓' : 'No logo yet: send it in chat and say “brand logo set karo”.'}</span></div>
    </div><div><button class="btn pri" data-bksave>${I('check', 'width:16px;height:16px')}Save</button></div></div>`; };
  W.brand = el => { if (!D.kit) load('kit').then(() => { if (VIEW === 'brand') go('brand'); });
    el.addEventListener('click', async e => { const b = e.target.closest('[data-bksave]'); if (!b) return; b.disabled = true;
      try { D.kit = await api('PUT', '/api/brand/kit', {name: $('#bkname').value.trim(), tagline: $('#bktag').value.trim(), tone: $('#bktone').value.trim()}); toast('Brand kit saved'); } catch (er) { toast(er.message, true); } b.disabled = false; }); };
  const GUIDES = [['Make your first ad film', 'director', 'film', 'Write one line in Director. Hoola writes the storyboard for free. Paint the opening pictures, watch the free preview, then make the HD shots and the final film. Every paid step shows its price first.'],
    ['Keep a character the same in every shot', 'casting', 'cast', 'Cast the character once in AI casting. In your film, add it from Cast: Hoola keeps the face, hair and outfit the same in every shot.'],
    ['Write and sing a Hindi song', 'music', 'music', 'Describe the song, press Write with Hoola for the lyrics (or paste yours), pick the singers and mood, and press Create song.'],
    ['Dub a video into Tamil', 'dubbing', 'portrait', 'Upload your video (up to 3 minutes), pick up to 4 languages and press Dub now. Every language comes back as its own video with its words on screen here.'],
    ['Edit with words, not clicks', 'editor', 'city', 'Add your clips in order, say what you want (a 30 s reel, cuts on the beat, Hindi captions) and press Make the edit. Ask for changes in plain words.'],
    ['A voice-over in your Hoola’s voice', 'voice', 'voice', 'Write the script, pick Your Hoola’s voice or any of 22 voices, the language and the style, and press Make voice-over.']];
  V.learn = () => `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 28px/1.2 var(--serif)">How-to guides</h2></div>
    <div class="guides">${GUIDES.map(([t, v, k, s], i) => `<div class="guide"><span class="thumb">${art(k, 'lr' + i)}</span><div><b>${t}</b><p class="mut">${s}</p><button class="btn sec" data-go="${v}">Open ${TITLE[v]}</button></div></div>`).join('')}</div></div>`;

  /* ---------------- icons ---------------- */
  const SPRITE = `<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-side" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="3"/><path d="M9.5 4.5v15"/></symbol>
  <symbol id="i-left" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></symbol>
  <symbol id="i-chev" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>
  <symbol id="i-down" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></symbol>
  <symbol id="i-menu" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h10"/></symbol>
  <symbol id="i-home" viewBox="0 0 24 24"><path d="M4 11l8-6.5 8 6.5V19a1.5 1.5 0 0 1-1.5 1.5h-3.5v-6h-6v6H5.5A1.5 1.5 0 0 1 4 19z"/></symbol>
  <symbol id="i-video" viewBox="0 0 24 24"><rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="M16 10.5l5-3v9l-5-3z"/></symbol>
  <symbol id="i-image" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="M4 17l5-4.5 4 3.5 3-2.5 4 3.5"/></symbol>
  <symbol id="i-music" viewBox="0 0 24 24"><path d="M9 18V6l11-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/></symbol>
  <symbol id="i-mic" viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/></symbol>
  <symbol id="i-dub" viewBox="0 0 24 24"><path d="M4 6h9M8.5 4v2c0 4-2 7-5 8M6 9c1 2.5 3.5 4.5 6 5M13 20l4-9 4 9M14.5 17h5"/></symbol>
  <symbol id="i-cut" viewBox="0 0 24 24"><circle cx="6" cy="7" r="2.5"/><circle cx="6" cy="17" r="2.5"/><path d="M8 8.5L20 17M8 15.5L20 7"/></symbol>
  <symbol id="i-clap" viewBox="0 0 24 24"><path d="M4 10h16v8.5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M4 10L3.3 7a1.3 1.3 0 0 1 1-1.6l12.9-2.8a1.3 1.3 0 0 1 1.6 1L19.4 6.5 4 10"/><path d="M8.2 4.7l2.4 3.7M12.6 3.7l2.4 3.7M4 14h16"/></symbol>
  <symbol id="i-pen" viewBox="0 0 24 24"><path d="M4 20l4-1 11-11-3-3L5 16z"/><path d="M14 6l3 3"/></symbol>
  <symbol id="i-cast" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><circle cx="17.5" cy="9" r="2.5"/><path d="M16 14.5a5 5 0 0 1 6 4.5"/></symbol>
  <symbol id="i-folder" viewBox="0 0 24 24"><path d="M3.5 7a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/></symbol>
  <symbol id="i-brand" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3"/></symbol>
  <symbol id="i-lib" viewBox="0 0 24 24"><path d="M5 4.5h4v15H5zM10.5 4.5h4v15h-4zM16 5.5l3.5-.8 2 14.5-3.5.8z"/></symbol>
  <symbol id="i-tpl" viewBox="0 0 24 24"><rect x="3.5" y="3.5" width="7" height="9" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="5" rx="1.5"/><rect x="13.5" y="11.5" width="7" height="9" rx="1.5"/><rect x="3.5" y="15.5" width="7" height="5" rx="1.5"/></symbol>
  <symbol id="i-book" viewBox="0 0 24 24"><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5zM20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z"/></symbol>
  <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
  <symbol id="i-minus" viewBox="0 0 24 24"><path d="M5 12h14"/></symbol>
  <symbol id="i-send" viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></symbol>
  <symbol id="i-spark" viewBox="0 0 24 24"><path d="M12 3l2.2 5.3L20 10l-5.8 1.7L12 17l-2.2-5.3L4 10l5.8-1.7z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/></symbol>
  <symbol id="i-wand" viewBox="0 0 24 24"><path d="M4 20L15 9M14 4v3M17.5 5.5l-2 2M20 9h-3M11 7l2 2"/></symbol>
  <symbol id="i-trash" viewBox="0 0 24 24"><path d="M5 7h14M10 7V4.5h4V7M6.5 7l1 13h9l1-13"/></symbol>
  <symbol id="i-sound" viewBox="0 0 24 24"><path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/></symbol>
  <symbol id="i-sliders" viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/></symbol>
  <symbol id="i-layers" viewBox="0 0 24 24"><path d="M12 4l8.5 4.5L12 13 3.5 8.5z"/><path d="M3.5 12.5L12 17l8.5-4.5M3.5 16.5L12 21l8.5-4.5"/></symbol>
  <symbol id="i-play" viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></symbol>
  <symbol id="i-pause" viewBox="0 0 24 24"><path d="M8 5h3v14H8zM13 5h3v14h-3z" fill="currentColor"/></symbol>
  <symbol id="i-dl" viewBox="0 0 24 24"><path d="M12 4v11M7 10.5l5 5 5-5M5 19.5h14"/></symbol>
  <symbol id="i-redo" viewBox="0 0 24 24"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></symbol>
  <symbol id="i-grid" viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/></symbol>
  <symbol id="i-upload" viewBox="0 0 24 24"><path d="M12 16V5M7 9.5l5-5 5 5M5 19.5h14"/></symbol>
  <symbol id="i-text" viewBox="0 0 24 24"><path d="M5 6h14M12 6v13M9 19h6"/></symbol>
  <symbol id="i-check" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></symbol>
  <symbol id="i-star" viewBox="0 0 24 24"><path d="M12 4l2.4 5 5.4.7-4 3.8 1 5.4L12 16.3 7.2 19l1-5.4-4-3.8 5.4-.7z"/></symbol>
  <symbol id="i-filter" viewBox="0 0 24 24"><path d="M4 6h16M7 12h10M10 18h4"/></symbol>
  <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></symbol>
  <symbol id="i-x" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></symbol>
  <symbol id="i-chat" viewBox="0 0 24 24"><path d="M5 5.5h14a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H10l-4.5 3.5V17.5H5A1.5 1.5 0 0 1 3.5 16V7A1.5 1.5 0 0 1 5 5.5z"/></symbol>
  <symbol id="i-globe" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.5 3.5 5.5 3.5 8.5s-1 6-3.5 8.5c-2.5-2.5-3.5-5.5-3.5-8.5s1-6 3.5-8.5z"/></symbol>
</svg>`;

  /* ---------------- mount ---------------- */
  function mount() {
    if (host) return;
    host = document.createElement('div'); host.id = 'cstudio'; host.hidden = true;
    host.setAttribute('role', 'region'); host.setAttribute('aria-label', 'Create studio');
    document.body.appendChild(host);
    R = host.attachShadow({mode: 'open'});
    R.innerHTML = shellHTML(); drawNav(); drawCredits();
    { const sn = $('#snav'), fade = () => sn.classList.toggle('fadeb', sn.scrollTop + sn.clientHeight < sn.scrollHeight - 4);   // v0.306 fade only while more list is below
      sn.addEventListener('scroll', fade, {passive: true}); addEventListener('resize', fade); requestAnimationFrame(fade); }
    R.addEventListener('pointerdown', e => { if (popFor && !e.target.closest('#pop') && !popFor.contains(e.target)) closeMenu(); });
    R.addEventListener('scroll', e => { if (popFor && !e.target.closest?.('#pop')) closeMenu(); }, true);
    $('#picker').addEventListener('click', onPickerClick);
    R.addEventListener('click', e => {
      if (e.target.closest('#picker')) return;
      const t = e.target.closest('[data-close]'); if (t) { close(); return; }
      if (e.target.closest('[data-lbclose]') || e.target.id === 'lightbox') { const lb = $('#lightbox'); lb.hidden = true; lb.querySelectorAll('video,audio').forEach(m => m.pause()); lb.innerHTML = ''; return; }
      const lbdl = e.target.closest('#lightbox [data-dl]'); if (lbdl) { itemAction(lbdl); return; }
      const g = e.target.closest('[data-go]'); if (g) { e.preventDefault(); go(g.dataset.go); return; }
    });
    R.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('#picker').hidden && !popFor) { closePicker(); return; } if (e.key === 'Escape') { const lb = $('#lightbox'); if (!lb.hidden) { lb.hidden = true; lb.innerHTML = ''; } else if ($('#shell').classList.contains('navon')) $('#shell').classList.remove('navon'); } });
    $('#collapse').addEventListener('click', () => $('#shell').classList.toggle('collapsed'));
    $('#menuBtn').addEventListener('click', () => $('#shell').classList.toggle('navon'));
    load('studio').then(drawCredits); load('conf');
  }
  function open(view, opts) {
    mount(); host.hidden = false; document.documentElement.classList.add('create-on');
    let v = view; if (!v) { try { v = sessionStorage.getItem('hoola.create.view') || 'studio'; } catch { v = 'studio'; } }
    go(v, opts); setTimeout(() => $('#view')?.focus?.(), 50);
  }
  function close() {
    if (!host) return; clearTimeout(poll); poll = 0; host.hidden = true; document.documentElement.classList.remove('create-on');
    $$('video,audio').forEach(m => m.pause());
    ctx.onClose?.();
  }
  function reset() {      // sign-out / another account: nothing of hers stays in memory
    close(); urls.forEach(u => URL.revokeObjectURL(u)); urls.clear(); blobs.clear();
    D.conf = D.studio = D.items = D.kit = null; D.jobs.clear();
    Object.assign(DIR, {brief: '', project: '', view: null, busy: '', castDraft: null}); IMG.refs = []; IMG.prompt = ''; VID.prompt = ''; SC.text = ''; SC.id = '';
    MU.lyrics = ''; MU.brief = ''; VO.text = ''; DB.src = null; ED.clips = []; ED.jobs = null; ED.job = '';
    if (host) { host.remove(); host = null; R = null; }
    try { sessionStorage.removeItem('hoola.create.view'); } catch {}
  }
  return {open, close, reset, isOpen: () => !!host && !host.hidden, go: v => open(v)};
};
