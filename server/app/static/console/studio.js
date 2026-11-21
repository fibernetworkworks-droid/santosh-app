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
  const fp = 'This card spends money: approving it needs your phone’s fingerprint. Approve it in the Hoola app.';

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
  // v0.320 a rail shows its arrow and a soft edge only on the side where more cards are hidden (the cut card read as broken)
  function rails(root = R) {
    $$('.rail', root).forEach(r => { const t = $('.rtrack', r); if (!t || t.dataset.rs) return; t.dataset.rs = '1';
      const sync = () => { r.classList.toggle('canl', t.scrollLeft > 4); r.classList.toggle('canr', t.scrollLeft + t.clientWidth < t.scrollWidth - 4); };
      t.addEventListener('scroll', sync, {passive: true}); if (window.ResizeObserver) new ResizeObserver(sync).observe(t); sync(); });
  }
  const art = (kind, seed, extra = '') => `<canvas class="art" data-art="${kind}" data-seed="${esc(seed)}" aria-hidden="true" ${extra}></canvas>`;
  // v0.320 the studio opens hidden, so on the FIRST open every picture had no size yet and stayed an unpainted 300x150 canvas
  // stretched over its card (squashed moons and records). A picture now paints when it gets a size, and again if it changes.
  const artRO = window.ResizeObserver ? new ResizeObserver(es => es.forEach(e => { if (e.target.clientWidth) paint(e.target); })) : null;
  // v0.329 SHOWCASE: a card whose real Hoola-made picture (or clip) exists shows it over the drawn placeholder
  const SC_SLOT = seed => { let m = /^t?q(\d+)$/.exec(seed); if (m) return 'film' + m[1];
    if ((m = /^t[pt](\d+)$/.exec(seed))) return 'tpl' + m[1]; if ((m = /^t(\d+)$/.exec(seed))) return 'tool' + m[1];
    if ((m = /^sty(\d+)$/.exec(seed))) return 'sty' + m[1];
    if ((m = /^lr(\d+)$/.exec(seed))) { const i = ALLTOOLS.findIndex(t => t[0] === GUIDES[+m[1]]?.[1]); return i >= 0 ? 'tool' + i : ''; }
    return ''; };
  function showcaseSwap(root = R) {
    const S = D.showcase?.slots; if (!S || !root) return;
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    $$('canvas[data-art][data-seed]', root).forEach(c => { const slot = SC_SLOT(c.dataset.seed), it = S[slot]; if (!it || c.dataset.sc) return; c.dataset.sc = '1';
      const base = `/api/studio/showcase/file/${slot}?kind=`, clip = it.clip && !still, el = document.createElement(clip ? 'video' : 'img');
      el.className = 'art sc'; el.setAttribute('aria-hidden', 'true');
      if (clip) { el.muted = true; el.loop = true; el.playsInline = true; el.autoplay = true; } else el.alt = '';
      c.after(el);
      blobURL(base + (clip ? 'clip' : 'pic')).then(u => { el.src = u; el.addEventListener(clip ? 'loadeddata' : 'load', () => el.classList.add('on'), {once: true}); })
        .catch(() => el.remove());
      if (clip && it.pic) blobURL(base + 'pic').then(u => { el.poster = u; }).catch(() => {}); });
  }
  const paintAll = (root = R) => requestAnimationFrame(() => $$('canvas[data-art]', root).forEach(c => { if (c.clientWidth) paint(c); artRO?.observe(c); }));

  /* ---------------- her files ---------------- */
  async function blobURL(path) {
    if (urls.has(path)) return urls.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const b = await r.blob(); const u = URL.createObjectURL(b);
    urls.set(path, u); blobs.set(path, b); return u;
  }
  const itemPath = id => `/api/create/items/${encodeURIComponent(id)}`;
  // fill every [data-src] (an authenticated path) inside root with its blob: URL
  function hydrate(root = R) {
    const n = alive; paintAll(root);   // v0.999.42 the stand-ins under every picture are painted with it
    $$('[data-src]', root).forEach(async el => {
      const p = el.dataset.src; el.removeAttribute('data-src');
      try { const u = await blobURL(p); if (n === alive || el.isConnected) { el.src = u; if (el.tagName === 'AUDIO') wave(el, blobs.get(p)); } }
      catch {   // v0.999.42 a missing file inside a drawn thumb keeps its drawing and gets a small chip; elsewhere a quiet line
        const th = el.closest('.thumb, .one, .cshot');
        if (th && th.querySelector('canvas.art')) { el.remove(); if (!th.querySelector('.gone')) th.insertAdjacentHTML('beforeend', '<span class="gone chip">File not available</span>'); }
        else el.replaceWith(Object.assign(document.createElement('span'), {className: 'gone', textContent: 'File not available'})); }
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
      if (what === 'showcase' && (force || !D.showcase)) D.showcase = await api('GET', '/api/studio/showcase');
    } catch (e) { if (what === 'items') D.items = D.items || []; if (what === 'studio') D.studio = D.studio || {projects: [], available: false, models: []}; if (what === 'conf') D.conf = D.conf || {ready: {}, voices: {male: {}, female: {}}}; if (what === 'showcase') D.showcase = D.showcase || {slots: {}}; }
    return D[what];
  }
  const items = kind => (D.items || []).filter(i => !kind || (Array.isArray(kind) ? kind.includes(i.kind) : i.kind === kind));

  // a Create job: start, then follow it; the page that asked re-renders its result area on every change
  async function startJob(body, onChange) {
    // v0.999.34 an engine the server says is not set up is said BEFORE a job starts (it used to start and fail a second later)
    const eng = {image: 'image', cast: 'image', song: 'song', voice: 'voice', dub: 'dub'}[body.kind], c = await load('conf');
    if (eng && c?.ready?.[eng] === false) throw new Error(c.need?.[eng] || 'This engine is not set up on the server. Check Create > Engines.');
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
    ['studio', 'Studio home', 'home'],
    ['l', 'Agents'], ['a', 'director', 'Director', 'Brief to finished film', 'clap', 'linear-gradient(135deg,#EE8F35,#B347E6)'],
    ['a', 'script', 'Script writer', 'Ads, films, episodes', 'pen', 'linear-gradient(135deg,#6E55F0,#2F6F8F)'],
    ['a', 'casting', 'AI casting', 'Characters that stay the same', 'cast', 'linear-gradient(135deg,#C2417A,#6E55F0)'],
    ['l', 'Tools'], ['t'],
    ['l', 'Assets'], ['projects', 'Film projects', 'folder'], ['brand', 'Brand kit', 'brand'], ['library', 'My creations', 'lib'],
    ['l', 'Inspire'], ['templates', 'Templates', 'tpl'], ['learn', 'How-to guides', 'book'],
    ['l', 'Setup'], ['engines', 'Engines', 'sliders'],
  ];
  const TOOLS = [['video','Video','video'],['image','Image','image'],['music','Music','music'],['voice','Voice','mic'],['dubbing','Dubbing','dub'],['editor','Editor','cut']];
  const tools = () => [...(ctx.cinema?.() && window.HoolaCinema ? [['cinema', 'Hoola Cinema', 'clap']] : []), ...TOOLS, ...(ctx.artcraft?.() ? [['artcraft', 'ArtCraft', 'spark']] : [])];   // v0.807 Hoola Cinema first, v0.752 ArtCraft when the server offers it   // v0.752 ArtCraft when the server offers it
  // v0.999.46 the product's own mark, never the avatar's face (owner: "USE HOOLA REAL LOGO NOT AVATAR")
  const markStill = () => window.HoolaMark ? HoolaMark.svg() : '<img src="/static/hoola-mark.png" alt="" width="26" height="26">';
  function markWork(on) { const m = $('#hmk'); if (!m || on === !!m.querySelector('.hm3')) return; m.innerHTML = on && window.HoolaMark ? HoolaMark.think(26) : markStill(); }
  const TITLE = {cinema:'Hoola Cinema', artcraft:'ArtCraft', engines:'Engines', studio:'Studio home', video:'Video', image:'Image', music:'Music studio', voice:'Voice studio', dubbing:'Dubbing', editor:'Video editor', director:'Director', script:'Script writer', casting:'AI casting', templates:'Templates', library:'My creations', projects:'Film projects', brand:'Brand kit', learn:'How-to guides'};
  function shellHTML() {
    return `<link rel="stylesheet" href="/static/console/chatkit.css?v=${esc(ctx.version || '')}">
<link rel="stylesheet" href="/static/console/studio.css?v=${esc(ctx.version || '')}">
<div id="shell">
  <aside class="side" aria-label="Create studio">
    <div class="shd"><div class="mark"><span class="hmk" id="hmk" aria-hidden="true">${markStill()}</span><span>Hoola</span><small>Studio</small></div>
      <button class="ib" id="collapse" aria-label="Collapse sidebar">${I('side')}</button></div>
    <button class="back" data-close>${I('left', 'width:16px;height:16px')}<span>Back to chat</span></button>
    <nav class="snav" id="snav"></nav>
    <div class="credits" id="credits"></div>
  </aside>
  <div class="rz rz-side" role="separator" aria-orientation="vertical" aria-label="Drag to resize the sidebar" tabindex="0"></div>
  <main class="main">
    <div class="top">
      <button class="ib menuBtn" id="menuBtn" aria-label="Open menu">${I('menu')}</button>
      <div class="crumb" id="crumb"></div>
    </div>
    <div class="view" id="view"></div>
  </main>
</div>
<div class="pop" id="pop" role="menu" hidden></div>
<div class="picker" id="picker" hidden></div>
<div class="lightbox" id="lightbox" hidden></div>
<div class="camsheet" id="camsheet" hidden></div>
${SPRITE}`;
  }
  function drawNav() {      // v0.306 each row carries --i so the sidebar fades in top to bottom once, when the studio opens
    let i = 0; const st = () => ` style="--i:${i++}"`;
    $('#snav').innerHTML = NAV.map(n => {
      if (n[0] === 'l') return `<div class="sl"${st()}>${n[1]}</div>`;
      if (n[0] === 'a') return `<button class="agent" data-go="${n[1]}"${st()}><span class="ai" style="background:${n[5]}">${I(n[4], 'width:16px;height:16px')}</span><div style="min-width:0;flex:1"><b>${n[2]}</b><small>${n[3]}</small></div><span class="ago" aria-hidden="true">${I('down', 'width:14px;height:14px;transform:rotate(-90deg)')}</span></button>`;
      // v0.318 tools are rows like every other item (one row style for the whole sidebar), not a bordered grid
      if (n[0] === 't') return tools().map(([k, t, ic]) => `<button class="sn" data-go="${k}"${st()}>${I(ic)}<span>${t}</span></button>`).join('');
      return `<button class="sn" data-go="${n[0]}"${st()}>${I(n[2])}<span>${n[1]}</span></button>`;
    }).join('');
  }
  function drawCredits() {
    const s = D.studio, el = $('#credits'); if (!el) return;
    if (!s || !s.month_limit_usd) { el.innerHTML = '<span class="mut">Your AI spend is in Account</span>'; return; }
    const k = s.usd_inr || 85, used = (s.month_spent_usd || 0) * k, lim = s.month_limit_usd * k;
    const pct = Math.min(100, used / lim * 100);   // v0.306 the meter fills from empty, and says how much is used
    // v0.318 what she has LEFT leads (600, never bold 700), the spend sits under the bar in the readable grey
    el.innerHTML = `<div class="crow1"><span class="mut">This month</span><b class="num">${inr(Math.max(0, lim - used))} left</b></div><div class="bar"><i style="width:0%"></i></div><small class="dim">${inr(used)} of ${inr(lim)} spent · ${pct < 1 && used > 0 ? '<1' : Math.round(pct)}%</small>`;
    requestAnimationFrame(() => requestAnimationFrame(() => { const b = el.querySelector('.bar i'); if (b) b.style.width = pct.toFixed(1) + '%'; }));
  }
  // v0.333 two dividers she can drag (owner: "SLIDER FROM BOTH SIDE ... PROMPT WORKING SECTION WILL GET BIGGER AREA"): the sidebar's edge
  // (200-360px) and the edge between the prompt panel and the results (320px up to the results keeping 360px). Arrow keys move them
  // 16px, Home / double-click put them back; the widths are remembered on this device.
  const RZ = {sbw: {min: 200, max: () => 360, def: 248, from: () => $('#shell').getBoundingClientRect().left, key: 'hoola.studio.sbw'},
    pw: {min: 320, max: () => Math.max(320, ($('.gen')?.clientWidth || 1200) - 360), def: 380, from: () => $('.gen').getBoundingClientRect().left, key: 'hoola.studio.pw'},
    // v0.999.43 the Video chat's own width (a chat needs more room than a settings panel)
    cw: {min: 400, max: () => Math.max(400, ($('.gen')?.clientWidth || 1200) - 360), def: 560, from: () => $('.gen').getBoundingClientRect().left, key: 'hoola.studio.cw'}};
  function rzSet(k, w, save) {
    const z = RZ[k]; w = Math.round(Math.max(z.min, Math.min(z.max(), w)));
    $('#shell').style.setProperty('--' + k, w + 'px');
    $$('.rz-' + (k === 'sbw' ? 'side' : 'pane')).forEach(h => { h.setAttribute('aria-valuenow', String(w)); h.setAttribute('aria-valuemin', String(z.min)); h.setAttribute('aria-valuemax', String(Math.round(z.max()))); });
    if (save) { try { localStorage.setItem(z.key, String(w)); } catch {} }
    return w;
  }
  function rzBind(h, k) {
    if (!h || h.dataset.rz) return; h.dataset.rz = '1';
    const cur = () => parseFloat(getComputedStyle($('#shell')).getPropertyValue('--' + k)) || RZ[k].def;
    h.addEventListener('pointerdown', e => { e.preventDefault(); h.setPointerCapture(e.pointerId); h.classList.add('on'); $('#shell').classList.add('rzing');
      const mv = ev => rzSet(k, ev.clientX - RZ[k].from()), up = () => { h.classList.remove('on'); $('#shell').classList.remove('rzing'); rzSet(k, cur(), true);
        h.removeEventListener('pointermove', mv); h.removeEventListener('pointerup', up); h.removeEventListener('pointercancel', up); };
      h.addEventListener('pointermove', mv); h.addEventListener('pointerup', up); h.addEventListener('pointercancel', up); });
    h.addEventListener('dblclick', () => rzSet(k, RZ[k].def, true));
    h.addEventListener('keydown', e => { const d = {ArrowLeft: -16, ArrowRight: 16}[e.key];
      if (d) { e.preventDefault(); rzSet(k, cur() + d, true); } else if (e.key === 'Home') { e.preventDefault(); rzSet(k, RZ[k].def, true); } });
    rzSet(k, cur());
  }
  function go(v, opts) {
    if (v === 'projects') { DIR.project = ''; DIR.view = null; v = 'director'; }   // v0.320 one film list: Film projects opens the Director's
    if (!V[v] || (v === 'cinema' && !ctx.cinema?.())) v = 'studio';
    clearTimeout(poll); poll = 0; clearTimeout(vPoll); clearTimeout(iPoll); clearTimeout(mPoll); camClose(); markWork(false); alive++; closeMenu(); if (!$('#picker').hidden) { $('#picker').hidden = true; $('#picker').innerHTML = ''; }
    artRO?.disconnect(); VIEW = v; const old = $('#view'), el = old.cloneNode(false); old.replaceWith(el);
    el.className = 'view enter'; el.innerHTML = V[v](opts || {}); el.scrollTop = 0;
    $$('#snav [data-go]').forEach(b => b.setAttribute('aria-current', b.dataset.go === v ? 'page' : 'false'));
    $('#crumb').innerHTML = v === 'studio' ? '<b>Create</b>' : `Create · <b>${TITLE[v]}</b>`;
    $('#shell').classList.remove('navon');
    (W[v] || (() => {}))(el, opts || {}); paintAll(el); hydrate(el); rails(el); showcaseSwap(el);
    const gen = $('.gen', el); if (gen) { gen.insertAdjacentHTML('beforeend', '<div class="rz rz-pane" role="separator" aria-orientation="vertical" aria-label="Drag to resize the prompt panel" tabindex="0"></div>'); rzBind($('.rz-pane', gen), gen.classList.contains('vchat') ? 'cw' : 'pw'); }
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
    if (!R) return;                     // v0.778 a console window resized before Create was ever opened threw (R is null until then)
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
  addEventListener('resize', () => { if (R) closeMenu(); });   // before Create is first opened there is no root: every window resize threw
  const opt = (L, fmt) => L.map(v => ({v, label: fmt ? fmt(v) : String(v)}));

  /* ---------------- shared result tiles ---------------- */
  function jobTile(j, tall) {
    return `<div class="res gening${tall ? ' tall' : ''}"><span class="thumb">${art(j.kind === 'song' ? 'music' : j.kind === 'voice' ? 'voice' : j.kind === 'dub' ? 'portrait' : 'abstract', j.id)}<span class="ring"></span><span class="pct">${j.step ? esc(j.step) : 'Making…'}</span></span><b class="rt">${esc(j.title)}</b><small>Hoola is working · stays here when you switch pages</small></div>`;
  }
  function failTile(j) {
    return `<div class="res failed"><span class="thumb"><span class="fail">${I('x', 'width:22px;height:22px')}<span>${esc(j.error || 'Did not work')}</span></span></span><b class="rt">${esc(j.title)}</b><small><button class="lnk" data-seen="${j.id}">Dismiss</button></small></div>`;
  }
  // v0.999.42 ONE tile for every creation, on every page (Studio home's row used a plain lilac box and a music note for a
  // script while My creations drew a record / waveform / page): a picture or clip sits over a painted stand-in with its mark,
  // so a loading or missing file never shows as a flat block.
  const STAND = {image: ['film', 'image'], cast: ['portrait', 'cast'], video: ['film', 'video'], dub: ['film', 'dub']};
  function standIn(it) {
    const [k, mark] = STAND[it.kind] || (it.mime.startsWith('video/') ? STAND.video : STAND.image);
    // a portrait already reads as a person, so it carries no mark (a mark sat on the drawn face)
    return k === 'portrait' ? art(k, it.id) : `${art(k, it.id)}<span class="ph-mark" aria-hidden="true">${I(mark)}</span>`;
  }
  function itemTile(it, tall) {
    const acts = `<span class="acts"><button data-dl="${it.id}" aria-label="Download">${I('dl')}</button>${it.mime.startsWith('image/') ? `<button data-ref="${it.id}" aria-label="Use as a reference">${I('layers')}</button>` : ''}${ctx.cinema?.() && window.HoolaCinema && /^(image|video)\//.test(it.mime) ? `<button data-cine="${it.id}" aria-label="Use in Hoola Cinema" title="Use in Hoola Cinema">${I('clap')}</button>` : ''}<button data-del="${it.id}" aria-label="Delete">${I('trash')}</button></span>`;
    if (it.kind === 'script') return `<div class="res${tall ? ' tall' : ''}" data-item="${it.id}"><button class="thumb doc-th" data-scopen="${it.id}" aria-label="Open ${esc(it.title)}"><span class="paper"><small>Script</small><b>${esc(it.title)}</b><i></i><i></i><i></i><i></i></span></button>${acts}<b class="rt">${esc(it.title)}</b><small>${when(it.created)}</small></div>`;
    const sound = !it.mime.startsWith('image/') && !it.mime.startsWith('video/');
    const media = it.mime.startsWith('image/') ? `${standIn(it)}<img alt="" data-src="${itemPath(it.id)}">`
      : it.mime.startsWith('video/') ? `${standIn(it)}<video muted playsinline preload="metadata" data-src="${itemPath(it.id)}"></video>`
      : art(it.kind === 'voice' ? 'voice' : 'music', it.id);
    const line = sound ? [it.kind === 'voice' ? 'Voice-over' : 'Song', when(it.created)] : [when(it.created), it.meta?.style, it.meta?.aspect].filter(Boolean);
    return `<div class="res${tall ? ' tall' : ''}" data-item="${it.id}"><button class="thumb" data-open="${it.id}" aria-label="Open ${esc(it.title)}">${media}${it.mime.startsWith('video/') ? `<span class="badge">${I('play', 'width:11px;height:11px')}${esc(it.kind)}</span>` : ''}</button>
      ${acts}<b class="rt">${esc(it.title)}</b><small>${line.filter(Boolean).map(esc).join(' · ')}</small></div>`;
  }
  async function openScript(id) {   // a script opens in the Script writer from any page
    try { const r = await api('GET', itemPath(id), undefined, {raw: true}); SC.text = await r.text(); SC.id = id; go('script'); } catch (er) { toast(er.message, true); }
  }
  // the hover actions on result tiles, shared by every page that lists her creations
  async function itemAction(b) {
    if (b.dataset.scopen) { await openScript(b.dataset.scopen); return true; }
    const id = b.dataset.dl || b.dataset.del || b.dataset.open || b.dataset.ref || b.dataset.cine; const it = (D.items || []).find(x => x.id === id); if (!it) return false;
    if (b.dataset.dl) { api('POST', '/api/prompting/runs/event', {ref: id, event: 'downloaded'}).catch(() => {}); download(itemPath(id), it.title + '.' + (it.mime.split('/')[1] || 'bin').replace('mpeg', 'mp3').replace('x-wav', 'wav')); return true; }
    if (b.dataset.del) { if (!confirm(`Delete "${it.title}"? This cannot be undone.`)) return true;
      try { await api('DELETE', itemPath(id)); D.items = D.items.filter(x => x.id !== id); b.closest('[data-item]')?.remove(); closeLb(); if (VIEW === 'image') drawPics(); toast('Deleted'); } catch (e) { toast(e.message, true); } return true; }
    if (b.dataset.ref) { closeLb(); iAddRef(it); if (VIEW === 'image') iTray(); else go('image'); toast('Added as a reference: write what to make and send'); return true; }   // v0.999.53 it rides the Image chat's tray
    if (b.dataset.cine) { closeLb(); CIN?.send(id); return true; }   // v0.807 a picture / video handed to Hoola Cinema
    if (b.dataset.open) { lightbox(it); return true; }
    return false;
  }
  function closeLb() { const lb = $('#lightbox'); if (!lb || lb.hidden) return; lb.querySelectorAll('video,audio').forEach(m => m.pause()); lb.hidden = true; lb.innerHTML = ''; }
  function lightbox(it) {
    const lb = $('#lightbox'); const p = itemPath(it.id);
    if (it.mime.startsWith('image/')) {   // v0.999.53 an opened picture: its words, settings, price and what to do next, like an opened clip
      const m = it.meta || {}, cine = ctx.cinema?.() && window.HoolaCinema, words = m.prompt || m.description || '';
      const rows = [['Style', m.style || (it.kind === 'cast' ? 'Character' : 'Auto')], ['Shape', m.aspect ? m.aspect + (ISHAPE[m.aspect] ? ' · ' + ISHAPE[m.aspect] : '') : ''],
        ['Quality', m.inr === 12 ? 'Best' : m.inr === 3 ? 'Standard' : ''], ['Made', when(it.created) + (m.inr ? ' · ' + inr(m.inr) : '')]].filter(r => r[1]);
      lb.innerHTML = `<div class="lbin vlb ilb" role="dialog" aria-modal="true" aria-label="${esc(it.title)}"><div class="lbh"><b>${esc(it.title)}</b><button class="ib" data-lbclose aria-label="Close">${I('x')}</button></div>
        <div class="vlbb"><div class="lbm"><img alt="${esc(it.title)}" data-src="${p}"></div>
          <aside class="vlbs"><span class="stchip ok">Ready</span>${words ? `<p class="vlbw">${esc(words)}</p><button class="lnk ilbc" data-icopy="${it.id}">${I('layers', 'width:14px;height:14px')}Copy the words</button>` : ''}
            <dl>${rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>
            <button class="btn pri" data-dl="${it.id}">${I('dl', 'width:15px;height:15px')}Download</button>
            <button class="btn sec" data-ichange="${it.id}">${I('pen', 'width:15px;height:15px')}Change this picture</button>
            <button class="btn sec" data-imore="${it.id}">${I('redo', 'width:15px;height:15px')}More like this</button>
            ${cine ? `<button class="btn sec" data-cine="${it.id}">${I('clap', 'width:15px;height:15px')}Bring it to life</button>` : ''}
            <button class="btn sec" data-ref="${it.id}">${I('layers', 'width:15px;height:15px')}Use as a reference</button>
            <button class="lnk ilbd" data-del="${it.id}">${I('trash', 'width:14px;height:14px')}Delete</button></aside></div></div>`;
      lb.hidden = false; hydrate(lb); $('[data-lbclose]', lb).focus(); return;
    }
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
    ['Founder intro voice-over','voice','voice','Hello! I am the founder of the Newtika team. We build AI for small businesses.'],
    ['Saree lookbook','image','portrait','A fashion lookbook photo of a woman in a deep red Banarasi silk saree at a heritage haveli courtyard, soft daylight'],
    ['Lo-fi study beat','music','music','A calm lo-fi study beat with soft keys, rain sounds and a slow tabla groove'],
    ['Temple at dawn','image','world','A South Indian temple gopuram at dawn, mist, golden rim light, birds in the sky, ultra detailed'],
    ['Street food promo','video','product','Close-up of pav bhaji being made on a big tawa at a Mumbai street stall at night, sizzling butter, bokeh lights'],
    ['Festive jingle','music','music','A 30-second festive jingle for a sweet shop, shehnai and dhol, joyful'],
    ['Podcast intro','voice','voice','Hello friends, welcome back to Business Talk, where we tell the big stories of small businesses!']];
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
    voice: 'Hello! This Diwali, Newtika Chai brings you a special offer…'};
  // v0.320 the ask box carries the few settings that matter for the chosen mode and what it costs, before she sends.
  // [key, state object, choices, menu title, label]; read lazily (the tools' state objects are declared further down)
  const hsList = m => ({
    director: [['aspect', DIR, ['16:9', '9:16', '1:1'], 'Shape', v => v], ['seconds', DIR, [15, 30, 45, 60, 90, 120], 'Length', v => v < 60 ? v + ' s' : v / 60 + ' min'],
      ['language', DIR, ['Hindi', 'Hinglish', 'English', 'Tamil', 'Telugu', 'Marathi', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'], 'Spoken language', v => v]],
    image: [['aspect', IMG, ASPECTS, 'Shape', v => v], ['count', IMG, [1, 2, 3, 4], 'How many', v => v + (v > 1 ? ' pictures' : ' picture')]],
    video: [['aspect', VID, ['9:16', '16:9', '1:1'], 'Shape', v => v], ['seconds', VID, [4, 5, 6, 8, 10, 12, 15], 'Length', v => v + ' s']],
    music: [['lang', MU, CYC.lang, 'Language', v => v]],
    voice: [['lang', VO, LANGS, 'Language', v => v]]}[m] || []);
  const hsPrice = m => ({director: 'Storyboard free', image: '~' + inr(imgCost()), video: 'Price before it starts', music: '~' + inr(mCost()), voice: 'A few paise a line'}[m] || '');
  const hsHTML = () => { const m = AGENTS[homeAgent][0];
    return hsList(m).map(([k, o, , , f], i) => `<button type="button" class="dd hs" data-hs="${i}">${i === 0 ? I('grid', 'width:15px;height:15px') : ''}<span>${esc(f(o[k]))}</span>${I('down', 'width:14px;height:14px')}</button>`).join('')
      + `<span class="hsp num">${esc(hsPrice(m))}</span>`; };
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
        <span class="hset" id="homeSet">${hsHTML()}</span>
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
  <section id="tools"><div class="sec-h"><h2>Studio tools</h2><span class="dim" style="font-size:14px">Every tool shares your cast and brand kit</span></div>
    <div class="tools">${[...(ctx.cinema?.() && window.HoolaCinema ? [['cinema', 'Hoola Cinema', 'Motion transfer, character swap, talking photos, content factory', 'film', 'new']] : []), ...ALLTOOLS, ...(ctx.artcraft?.() ? [['artcraft', 'ArtCraft', 'Seedance, Kling, Veo, FLUX… on your ArtCraft credits', 'abstract', 'new']] : [])].map(([v, t, s, k, tag], i) => `<button class="tool" data-go="${v}"><span class="thumb">${art(k, 't' + i)}</span><div style="min-width:0"><b>${t}${tag ? ` <span class="tag ${tag}">${tag === 'hot' ? 'Popular' : 'New'}</span>` : ''}</b><small>${s}</small></div></button>`).join('')}</div></section>
  <section><div class="sec-h"><h2>Your recent creations</h2><a data-go="library">See all</a></div><div class="row" id="recent"></div></section>
  <section><div class="sec-h"><h2>Start from a template</h2><a data-go="templates">See all</a></div>
    ${rail(STARTERS.map(([t, v, k], i) => `<button class="tpl" data-start="${i}"><span class="thumb">${art(k, 'tp' + i)}<span class="use">Use this</span></span><b>${t}</b><small>${TITLE[v]}</small></button>`).join(''), 'row')}</section>
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
      $('#homeq').placeholder = MODE_HINT[AGENTS[i][0]] || ''; $('#homeSet').innerHTML = hsHTML(); };
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
      if (b.dataset.hs) { const [k, o, L, title, f] = hsList(AGENTS[homeAgent][0])[+b.dataset.hs];
        menu(b, L.map(v => ({v, label: f(v)})), o[k], v => { o[k] = L.find(x => String(x) === String(v)) ?? v; $('#homeSet').innerHTML = hsHTML(); }, title); return; }
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
  /* v0.999.53 IMAGE CHAT (owner: "DESIGN SHOULD BE SAME AS HOOLA VIDEO SECTION -- SHOW DESIGN FIRST" -> design canvas
     claude.ai/artifact/MADqzZqiUDde71pFpJ95f7 -> "GO BUILD"): the Image page is the Video page's twin - its own Hoola chat on
     the left (/api/image/chat, Conversation kind 'image'), the same chat bar (+, ONE settings button, Improve, Send), Picture
     settings in a panel above the box (shape, style = a sheet of 9 looks, quality, how many, brand colours, what to leave
     out), every picture set inside the chat, Your pictures on the right in their real shapes, and an opened picture with its
     words, settings, price and what to do next. Hoola makes the pictures with create_studio action=image: the same engine and
     the same shelf as before. If Hoola cannot answer, "Make the pictures straight away" makes them directly. */
  const IMG = {prompt: '', files: [], aspect: '1:1', quality: 'fast', count: 1, style: '', brand: false, avoid: '',
    chat: '', title: '', thread: null, rows: [], turn: null, sending: false, working: false, loading: false, filter: 'all', q: '', lastSend: null, seq: 0, jobs: []};
  const STYLE_ART = {'': 'abstract', Photoreal: 'portrait', Cinematic: 'film', 'Festive glow': 'abstract', 'Product studio': 'product', Watercolour: 'world', Anime: 'cast', '3D clay': 'product', 'Indian folk art': 'city'};
  const STYLES = ['', 'Photoreal', 'Cinematic', 'Festive glow', 'Product studio', 'Watercolour', 'Anime', '3D clay', 'Indian folk art'];
  const STYLE_LINE = {'': 'Hoola picks the look from your words', Photoreal: 'Like a real photo', Cinematic: 'Film light, deep colour', 'Festive glow': 'Warm lights for festivals',
    'Product studio': 'Clean studio shot of a product', Watercolour: 'Soft painted look', Anime: 'Drawn, bright and bold', '3D clay': 'Soft 3D, like clay toys', 'Indian folk art': 'Madhubani, Warli and Gond lines'};
  const ASPECTS = ['1:1', '4:5', '9:16', '16:9', '3:4', '4:3'];
  const ISHAPE = {'1:1': 'Square · feed posts', '4:5': 'Instagram post', '9:16': 'Reels and Stories cover', '16:9': 'Banner · YouTube, websites', '3:4': 'Print · flyers', '4:3': 'Slides'};
  const IBOX = {'1:1': [10, 10], '4:5': [9, 11], '9:16': [7, 12], '16:9': [13, 7], '3:4': [9, 12], '4:3': [12, 9]};
  const IEACH = () => IMG.quality === 'best' ? 12 : 3;
  const imgCost = () => IEACH() * IMG.count;
  const arOf = a => (ASPECTS.includes(a) ? a : '1:1').replace(':', ' / ');
  const isum = () => `${IMG.aspect} · ${IMG.style || 'Auto'} · ${IMG.count}`;
  const ipriceLine = () => `About ${inr(imgCost())} · ${IMG.count} picture${IMG.count > 1 ? 's' : ''} × ${inr(IEACH())}`;
  function ioptsHTML() {
    const open = !$('#isetp')?.hidden;
    return `<button type="button" class="vset" data-iset aria-haspopup="dialog" aria-expanded="${open}" aria-controls="isetp" title="Picture settings">${I('sliders', 'width:16px;height:16px')}<span>${esc(isum())}</span>${I(open ? 'up' : 'down', 'width:14px;height:14px')}</button>`
      + `<span class="vmdl imdl" title="Hoola's picture engine: Hindi and other Indian words come out readable">${I('spark', 'width:15px;height:15px')}<span>Hoola image</span></span>`;
  }
  function isetHTML() {
    const seg = (k, list, cur, fmt) => `<div class="seg vsg" role="radiogroup">${list.map(v => `<button type="button" role="radio" aria-checked="${String(v) === String(cur)}" data-is="${k}" data-isv="${esc(String(v))}">${fmt ? fmt(v) : esc(String(v))}</button>`).join('')}</div>`;
    const row = (label, body, note) => `<div class="vsr"><span class="vsl">${label}</span><div class="vsc">${body}${note ? `<small>${note}</small>` : ''}</div></div>`;
    const shp = v => { const [w, h] = IBOX[v] || [10, 10]; return `<i class="vsh" style="width:${w}px;height:${h}px"></i>${esc(v)}`; };
    const kit = D.kit?.colors;
    return `<div class="vsh0"><b id="isetT">Picture settings</b><button type="button" class="lnk" data-isreset>Reset</button></div>`
      + row('Shape', seg('aspect', ASPECTS, IMG.aspect, shp), esc(ISHAPE[IMG.aspect] || ''))
      + row('Style', `<button type="button" class="vsb" data-istyopen><span class="isw">${art(STYLE_ART[IMG.style] || 'abstract', 'sty' + STYLES.indexOf(IMG.style))}</span><span>${esc(IMG.style || 'Auto')}</span>${I('right', 'width:14px;height:14px')}</button>`, '9 looks')
      + row('Quality', seg('quality', ['fast', 'best'], IMG.quality, v => v === 'best' ? 'Best · ₹12' : 'Standard · ₹3'), IMG.quality === 'best' ? 'Sharper detail and words' : '')
      + row('Pictures', seg('count', [1, 2, 3, 4], IMG.count), IMG.count > 1 ? 'Each picture is paid' : '')
      + row('Brand', `<button type="button" class="sw" role="switch" aria-checked="${IMG.brand}" data-ibrand aria-label="Use my brand colours"><i></i></button><span class="vstx">${IMG.brand ? (kit ? `${esc(kit.primary)} and ${esc(kit.accent)} from your Brand kit` : 'Your Brand kit colours') : 'Use my brand colours'}</span>`)
      + row('Leave out', `<label class="sr" for="iavoid">Things to leave out of the picture</label><input id="iavoid" class="ivin" maxlength="300" value="${esc(IMG.avoid)}" placeholder="e.g. text errors, people, a watermark">`)
      + `<div class="vsf"><span id="isetCost">${esc(ipriceLine())}</span><button type="button" class="vdone" data-isdone>Done</button></div>`;
  }
  function isetOpen(on) {
    const p = $('#isetp'); if (!p) return;
    if (on) { p.innerHTML = isetHTML(); p.hidden = false; requestAnimationFrame(() => p.classList.add('on')); ($('[aria-checked="true"]', p) || $('button', p))?.focus(); paintAll(p); }
    else { p.classList.remove('on'); p.hidden = true; p.innerHTML = ''; }
    const o = $('#iopts'); if (o) o.innerHTML = ioptsHTML();
    if (!on) $('[data-iset]')?.focus();
  }
  function iRedraw() {
    const o = $('#iopts'); if (o) o.innerHTML = ioptsHTML();
    const p = $('#isetp');
    if (p && !p.hidden) { const f = p.contains(p.getRootNode().activeElement) ? p.getRootNode().activeElement : null;
      const k = f?.dataset?.is ? `[data-is="${f.dataset.is}"][aria-checked="true"]` : f?.hasAttribute?.('data-ibrand') ? '[data-ibrand]' : '';
      p.innerHTML = isetHTML(); paintAll(p); if (k) $(k, p)?.focus(); }
    iPrice();
  }
  // the price under the box: Standard ₹3 / Best ₹12 a picture; made when she sends (the owner's design: no price card for a picture)
  function iPrice() {
    const el = $('#iprice'); if (!el) return; const c = D.conf;
    el.innerHTML = `<b class="num">≈ ${inr(imgCost())}</b> · <span>${IMG.count} picture${IMG.count > 1 ? 's' : ''} × ${inr(IEACH())} · made when you send</span>`
      + (c?.ready?.image === false ? ` <span class="warnl">${esc(c.need?.image || 'The picture engine is not set up on the server. Check Create > Engines.')}</span>` : '');
  }
  V.image = () => `<div class="gen vchat ichat">
  <section class="panel vcp" aria-label="Image chat">
    <div class="vch"><span class="vcm">${I('image', 'width:16px;height:16px')}</span><div class="vct"><b id="icTitle">${esc(IMG.title || 'Image chat')}</b><small>Describe a picture or add your photo with +.</small></div>
      <button class="ib" data-ihist aria-label="Earlier image chats" title="Earlier image chats">${I('redo')}</button><button class="ib" data-inew aria-label="New image chat" title="New image chat">${I('plus')}</button></div>
    <div class="vlog" id="ilog"><div id="ithread"></div><div id="ifail"></div></div>
    <div class="vcomp" id="icomp">
      <div class="vsetp" id="isetp" role="dialog" aria-labelledby="isetT" hidden></div>
      <div class="vbox" id="ibox">
        <div class="vtray" id="itray" role="list" aria-label="Pictures and files to send"></div>
        <label class="sr" for="imgq">Message Hoola about your picture</label>
        <textarea id="imgq" rows="2" maxlength="4000" placeholder="Describe a picture, or ask for a change…">${esc(IMG.prompt)}</textarea>
        <div class="vrow">
          <button type="button" class="vplus" data-iplus aria-label="Add your photos or files" title="Add your photos or files">${I('plus')}</button>
          <div class="vopts" id="iopts">${ioptsHTML()}</div>
          <button type="button" class="ib" data-improve aria-label="Improve my words" title="Improve my words">${I('wand')}</button>
          <button type="button" class="vsend" id="imgGo" aria-label="Send">${I('send')}</button>
        </div>
      </div>
      <p class="vfoot" id="iprice"></p>
    </div>
  </section>
  <div class="stage vst"><div class="sbar vsbar"><b>Your pictures</b><span class="mut num" id="icount"></span><span class="sp"></span>
      <div class="vseg" role="tablist" aria-label="Show">${[['all', 'All'], ['mk', 'Making'], ['ok', 'Ready']].map(([k, t]) => `<button type="button" role="tab" data-ifilt="${k}" aria-selected="${IMG.filter === k}">${t}<i class="num" data-in="${k}"></i></button>`).join('')}</div>
      <label class="vsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search your pictures</span><input id="iq" type="search" placeholder="Search" value="${esc(IMG.q)}"></label>
      <button class="ib" data-reload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div>
    <div class="sgrid pgrid" id="results"></div></div></div>`;
  // the music / voice / dubbing pages still list their work in one grid
  function drawResults(kinds, tall) {
    const el = $('#results'); if (!el) return;
    const its = items(kinds), jobs = running(kinds), bad = failed(kinds);
    el.innerHTML = jobs.map(j => jobTile(j, tall)).join('') + bad.map(failTile).join('') + its.map(it => itemTile(it, tall)).join('')
      || `<div class="empty" style="grid-column:1/-1"><div><h2>Your work appears here</h2><p class="mut">Describe it on the left and press Create.</p></div></div>`;
    paintAll(el); hydrate(el);
  }
  /* ---- Your pictures: in their real shapes, filters + search ---- */
  const iRunning = () => { const seen = new Set(), out = []; for (const j of [...IMG.jobs, ...D.jobs.values()]) { if (j.kind !== 'image' || j.status !== 'running' || seen.has(j.id)) continue; seen.add(j.id); out.push(j); } return out; };
  function picTile(it) { return itemTile(it, false).replace('<div class="res" data-item=', `<div class="res pic" style="--ar:${arOf(it.meta?.aspect)}" data-item=`); }
  function drawPics() {
    const el = $('#results'); if (!el || VIEW !== 'image') return;
    const all = items(['image', 'cast']), run = iRunning(), q = (IMG.q || '').toLowerCase();
    const cnt = {all: all.length + run.length, mk: run.length, ok: all.length};
    $$('[data-in]').forEach(n => { const v = cnt[n.dataset.in]; n.textContent = n.dataset.in !== 'all' && v ? ' · ' + v : ''; });
    const c = $('#icount'); if (c) c.textContent = all.length ? String(all.length) : '';
    const hit = it => !q || (it.title + ' ' + (it.meta?.prompt || '') + ' ' + (it.meta?.style || '')).toLowerCase().includes(q);
    const mk = IMG.filter === 'ok' ? [] : run.filter(j => !q || (j.title || '').toLowerCase().includes(q)).map(j => Array.from({length: j.count || 1}, (_, i) =>
      `<div class="res pic gening" style="--ar:${arOf(j.aspect)}"><span class="thumb">${art('abstract', j.id + i)}<span class="ring"></span><span class="pct">Painting ${i + 1} of ${j.count || 1}</span></span><b class="rt">${esc(j.title)}</b><small>About 15 seconds a picture</small></div>`).join('')).join('');
    const ready = IMG.filter === 'mk' ? '' : all.filter(hit).map(picTile).join('');
    patch(el, mk + failed(['image']).map(failTile).join('') + ready || (all.length || run.length
      ? `<div class="empty"><div><h2>Nothing here</h2><p class="mut">No picture matches this filter.</p></div></div>`
      : `<div class="empty"><div><h2>Your pictures appear here</h2><p class="mut">Describe a picture in the chat and send.</p></div></div>`));
    paintAll(el); hydrate(el);
    iDrawSets();
  }
  /* ---- a picture set in the chat: painting, ready (its pictures + what next) or could not be made ---- */
  function iSets() {
    const sets = new Map();
    for (const it of (D.items || [])) { const m = it.meta || {}; if (it.kind !== 'image' || !IMG.chat || m.chat !== IMG.chat) continue;
      const k = m.job || it.id, s = sets.get(k) || {id: k, created: it.created, items: [], aspect: m.aspect, style: m.style, inr: 0};
      s.items.push(it); s.created = Math.min(s.created, it.created); s.inr += m.inr || 0; sets.set(k, s); }
    for (const j of IMG.jobs) { if (j.kind !== 'image' || !IMG.chat || j.conv !== IMG.chat || sets.has(j.id) || j.status === 'done') continue;
      sets.set(j.id, {id: j.id, created: j.created, items: [], job: j, aspect: j.aspect, style: j.style}); }
    sets.forEach(s => s.items.reverse());
    return [...sets.values()].sort((a, b) => a.created - b.created);
  }
  function chatSet(s) {
    const j = s.job, meta = [s.aspect, s.style || 'Auto'];
    if (j && j.status === 'running') { const n = j.count || 1;
      return `<div class="iscard gening"><div class="isg">${Array.from({length: n}, (_, i) => `<span class="isp thumb" style="--ar:${arOf(j.aspect)}">${art('abstract', j.id + i)}<span class="ring"></span></span>`).join('')}</div>
        <div class="isf"><span class="stchip mk">Painting ${n} picture${n > 1 ? 's' : ''}${j.step ? ' · ' + esc(j.step) : ''}</span><small class="mut">${esc([...meta, inr((j.quality === 'best' ? 12 : 3) * n)].join(' · '))}</small></div>
        <span class="bar"><i class="indet"></i></span></div>`; }
    if (j) return `<div class="iscard"><div class="isf"><span class="stchip na">Could not be made</span><small class="mut">${esc(j.error || 'It did not work this time. Try again in a minute.')}</small></div></div>`;
    const cine = ctx.cinema?.() && window.HoolaCinema;
    return `<div class="iscard"><div class="isg">${s.items.map(it => `<button class="isp thumb" style="--ar:${arOf(it.meta?.aspect || s.aspect)}" data-open="${it.id}" aria-label="Open ${esc(it.title)}">${standIn(it)}<img alt="" data-src="${itemPath(it.id)}"></button>`).join('')}</div>
      <div class="isf"><span class="stchip ok">Ready</span><small class="mut">${esc([...meta, s.inr ? inr(s.inr) : ''].filter(Boolean).join(' · '))}</small><span class="sp"></span>
        <button class="btn sec" data-imore="${esc(s.items[0].id)}">${I('redo', 'width:14px;height:14px')}More like this</button>${cine ? `<button class="btn sec" data-cine="${esc(s.items[0].id)}">${I('clap', 'width:14px;height:14px')}Bring to life</button>` : ''}</div></div>`;
  }
  function iDrawSets() {
    const sets = new Map(iSets().map(s => [s.id, s]));
    $$('[data-iset-id]').forEach(n => { const s = sets.get(n.dataset.isetId); if (!s) return; const h = chatSet(s); if (n._h === h) return; n._h = h; n.innerHTML = h; hydrate(n); });
  }
  /* ---- the chat ---- */
  const ISENT = 'hoola.ichat.files';
  function iSentFiles() { try { return JSON.parse(sessionStorage.getItem(ISENT) || '{}'); } catch { return {}; } }
  function iKeepSent(text, files) { if (!files.length) return; try { const m = iSentFiles(); m[IMG.chat + '|' + text.trim()] = files.map(f => f.name); sessionStorage.setItem(ISENT, JSON.stringify(m)); } catch {} }
  function iThreadList() {
    const sf = iSentFiles();
    const msgs = IMG.rows.map(r => { const t = r.role === 'user' ? stripNotes(r.text) : String(r.text || '');
      return {id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: t, at: atOf(r.at), files: r.role === 'user' ? (sf[IMG.chat + '|' + t.trim()] || []) : undefined}; });
    const after = new Map();       // a set sits after the reply of the turn that made it (or after her message when none)
    for (const s of iSets()) { let i = -1; msgs.forEach((m, j) => { if (m.at <= s.created + 1) i = j; });
      if (i >= 0 && msgs[i].role === 'her' && msgs[i + 1]?.role === 'hoola') i++;
      (after.get(i) || after.set(i, []).get(i)).push(s); }
    const raw = s => ({id: 'iset:' + s.id, role: 'raw', html: `<div class="iset" data-iset-id="${esc(s.id)}"></div>`});
    const out = [...(after.get(-1) || []).map(raw)];
    msgs.forEach((m, j) => { out.push(m); (after.get(j) || []).forEach(s => out.push(raw(s))); });
    return out;
  }
  async function iJobs() {
    const before = new Set(IMG.jobs.filter(j => j.status === 'running').map(j => j.id));
    try { IMG.jobs = (await api('GET', '/api/create/jobs')).jobs || []; } catch { return; }
    if (IMG.jobs.some(j => before.has(j.id) && j.status !== 'running')) await load('items', true);
  }
  async function iLoad(first) {
    if (!IMG.chat || IMG.loading || !IMG.thread) return;
    const chat = IMG.chat; IMG.loading = true;
    try {
      const last = IMG.rows[IMG.rows.length - 1];
      if (IMG.sending || IMG.working || (last && last.role === 'user') || first) {
        try { IMG.turn = await api('GET', `/api/conversations/${encodeURIComponent(chat)}/result`); } catch {}
      }
      let rows; try { rows = (await api('GET', `/api/conversations/${encodeURIComponent(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      await iJobs();
      if (chat !== IMG.chat) return;
      IMG.rows = rows; iPaint(); drawPics();
    } finally { IMG.loading = false; }
  }
  function iPaint() {
    if (!IMG.thread || VIEW !== 'image') return;
    const st = IMG.turn ? String(IMG.turn.status || '') : null, last = IMG.rows[IMG.rows.length - 1];
    const working = IMG.sending || (st ? st === 'working' || st === 'queued' : !!last && last.role === 'user');
    const label = IMG.turn && working && IMG.turn.line ? String(IMG.turn.line) : 'Reading your words and pictures…';
    IMG.working = working;
    IMG.thread.sync({key: IMG.chat, working, label, steps: [], messages: iThreadList()});
    iDrawSets();
    // Hoola could not answer: the same pictures can still be made straight away
    const mine = iSets().some(s => s.created >= (IMG.lastSend?.at || 0) - 1);
    const fail = $('#ifail'), failed = !working && !!last && !!st && /fail|error|stuck/.test(st) && !mine;
    if (fail) fail.innerHTML = failed && IMG.lastSend ? `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>Hoola could not answer this time.</b><small>You can still make the pictures from your words and settings: ${esc(inr(IMG.lastSend.each * IMG.lastSend.count))} for ${IMG.lastSend.count}.</small>
      <button class="btn pri" data-idirect>${I('spark', 'width:15px;height:15px')}Make the pictures straight away</button></div></div>` : '';
    markWork(!!working && VIEW === 'image');
    const go = $('#imgGo'); if (go) { go.classList.toggle('stop', working && !IMG.sending); go.setAttribute('aria-label', working && !IMG.sending ? 'Stop' : 'Send'); go.innerHTML = working && !IMG.sending ? I('pause') : I('send'); }
  }
  async function iChat(id) {
    try {
      const c = id ? {id} : await api('GET', '/api/image/chat');
      IMG.chat = c.id; IMG.rows = []; IMG.turn = null; if (c.title) IMG.title = c.title;
      const t = $('#icTitle'); if (t) t.textContent = IMG.title || 'Image chat';
      IMG.thread?.clear(); await iLoad(true);
    } catch (e) { const f = $('#ifail'); if (f) f.innerHTML = `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>The image chat could not open.</b><small>${esc(e.message)}</small></div></div>`; }
  }
  // what she picked in Picture settings, said to Hoola beside her words (her bubble shows only her words)
  async function iHint() {
    let brand = '';
    if (IMG.brand) { const k = await load('kit'); if (k?.colors) brand = `, brand colours: primary ${k.colors.primary}, accent ${k.colors.accent}${k.name ? ' (brand ' + k.name + ')' : ''}`; }
    const refs = IMG.files.filter(f => f.kind === 'image' && f.file_id).map(f => f.file_id);
    const clean = t => String(t).replace(/[\]\[\n]/g, ' ');
    return `Image settings: shape ${IMG.aspect}, style ${IMG.style || 'Auto (you choose the look)'}, quality ${IMG.quality === 'best' ? 'best' : 'fast (standard)'}, ${IMG.count} picture${IMG.count > 1 ? 's' : ''}${clean(brand)}`
      + (IMG.avoid ? `, leave out: ${clean(IMG.avoid)}` : '') + (refs.length ? `, reference pictures file_ids ${refs.join(', ')}` : '') + '. Make them with create_studio action=image.';
  }
  async function iSend() {
    const q = $('#imgq'), text = (q?.value || '').trim();
    if (IMG.working && !IMG.sending && !text) { try { await api('POST', `/api/conversations/${encodeURIComponent(IMG.chat)}/stop`); toast('Stopping.'); } catch (e) { toast(e.message, true); } return; }
    if (!text) { q?.focus(); toast('Describe the picture first'); return; }
    if (IMG.files.some(f => f.up)) { toast('Wait for the files to finish uploading'); return; }
    load('conf').then(iPrice);   // v0.999.34 an engine that is not set up stays said under the box; Hoola says it too
    if (!IMG.chat) await iChat();
    if (!IMG.chat) return;
    const files = IMG.files.filter(f => f.file_id), hint = await iHint();   // read before the tray is emptied
    IMG.sending = true; IMG.turn = null;
    IMG.lastSend = {prompt: text, at: Date.now() / 1000, aspect: IMG.aspect, style: IMG.style, quality: IMG.quality, count: IMG.count, each: IEACH(), avoid: IMG.avoid, brand: IMG.brand, refs: files.filter(f => f.kind === 'image').map(f => f.file_id)};
    IMG.thread.her(text, {pending: true, files: files.map(f => f.name)}); iKeepSent(text, files);
    q.value = ''; IMG.prompt = ''; IMG.files = []; iTray(); iPaint();
    try {
      await api('POST', `/api/conversations/${encodeURIComponent(IMG.chat)}/messages`, {text, files: files.filter(f => !f.shelf).map(f => f.file_id), hints: [hint],
        client_id: 'ic' + Date.now().toString(36) + (++IMG.seq).toString(36)});   // no random ids in the studio
      IMG.turn = {status: 'queued', line: ''};
    } catch (e) { toast(e.message, true); q.value = IMG.prompt = text; IMG.files = files; iTray(); }
    IMG.sending = false; await iLoad(false); iChatPoll();
  }
  let iPoll = 0;
  function iChatPoll() {
    clearTimeout(iPoll);
    const busy = () => IMG.working || iRunning().length;
    const tick = async () => { if (VIEW !== 'image') return; await iLoad(false); iPoll = setTimeout(tick, busy() ? 2000 : 8000); };
    iPoll = setTimeout(tick, busy() ? 1500 : 8000);
  }
  // pictures made without a chat turn: "More like this" and "Make the pictures straight away" (her tap; the price is on the button's line)
  async function iMake(p) {
    const c = await load('conf');
    if (c?.ready?.image === false) { toast(c.need?.image || 'The picture engine is not set up on the server.', true); return; }
    if (!IMG.chat) await iChat();
    try {
      const j = await api('POST', '/api/create/jobs', {kind: 'image', conversation_id: IMG.chat || '', ...p});
      IMG.jobs = [j, ...IMG.jobs.filter(x => x.id !== j.id)]; drawPics(); iPaint(); iChatPoll();
      toast(`Making ${p.count} picture${p.count > 1 ? 's' : ''} · ${inr((p.quality === 'best' ? 12 : 3) * p.count)}`);
    } catch (e) { toast(e.message, true); }
  }
  function iMore(id) {
    const it = (D.items || []).find(x => x.id === id); if (!it) return;
    const m = it.meta || {}, n = m.job ? (D.items || []).filter(x => x.meta?.job === m.job).length : 1;
    iMake({prompt: m.prompt || m.description || it.title, aspect: ASPECTS.includes(m.aspect) ? m.aspect : '1:1', quality: m.inr === 12 ? 'best' : 'fast',
      count: Math.max(1, Math.min(4, n)), style: m.style || '', title: it.title.slice(0, 80)});
  }
  async function iDirect() {
    const s = IMG.lastSend; if (!s) return;
    let prompt = s.prompt; if (s.avoid) prompt += `\nAvoid: ${s.avoid}.`;
    if (s.brand) { const k = await load('kit'); if (k?.colors) prompt += `\nUse these brand colours: primary ${k.colors.primary}, accent ${k.colors.accent}.${k.name ? ' Brand: ' + k.name + '.' : ''}`; }
    IMG.lastSend = null;
    await iMake({prompt, aspect: s.aspect, quality: s.quality, count: s.count, style: s.style, file_ids: s.refs.slice(0, 3), title: s.prompt.slice(0, 48)});
  }
  // a picture handed here (Use as a reference / Change this picture): it rides the tray like a photo she added
  function iAddRef(it) {
    IMG.files = [...IMG.files.filter(f => f.file_id !== it.id), {name: it.title, kind: 'image', file_id: it.id, shelf: true}].slice(-10);
  }
  /* ---- her photos and files: a tray of tiles above the words; 10 at most, 30 MB each ---- */
  function iTray() {
    const t = $('#itray'); if (!t) return;
    t.innerHTML = IMG.files.map((f, i) => `<div class="vfile ${f.kind}${f.err ? ' err' : ''}" role="listitem" title="${esc(f.name)}">
      <span class="vfk">${esc(f.shelf ? 'YOURS' : (f.name.split('.').pop() || 'file').slice(0, 4).toUpperCase())}</span><span class="vfn">${esc(f.name)}</span>
      ${f.kind === 'image' && f.local ? `<img alt="" src="${esc(f.local)}">` : f.shelf ? `<img alt="" data-src="${itemPath(f.file_id)}">` : ''}
      ${f.up ? '<span class="vfu">Uploading…</span>' : f.err ? `<span class="vfu err">${esc(f.err)}</span>` : ''}
      <button type="button" class="vfx" data-ifx="${i}" aria-label="Remove ${esc(f.name)}">${I('x', 'width:11px;height:11px')}</button></div>`).join('');
    t.hidden = !IMG.files.length; hydrate(t);
    $$('img', t).forEach(m => m.addEventListener('error', () => { m.hidden = true; }, {once: true}));
  }
  async function iAddFiles(list) {
    const fs = [...list].slice(0, Math.max(0, 10 - IMG.files.length));
    if (list.length > fs.length) toast('Up to 10 files at a time');
    if (!IMG.chat) await iChat();
    if (!IMG.chat) return;
    for (const file of fs) {
      const f = {name: file.name || 'file', kind: VFILES(file.name || ''), size: file.size, up: true, local: /^image\//.test(file.type) ? URL.createObjectURL(file) : ''};
      if (f.local) urls.set('ic:' + f.local, f.local);
      IMG.files.push(f); iTray();
      if (file.size > 30 * 1024 * 1024) { f.up = false; f.err = 'Over 30 MB'; iTray(); continue; }
      try { const fd = new FormData(); fd.append('file', file, file.name);
        const r = await api('POST', `/api/conversations/${encodeURIComponent(IMG.chat)}/files`, undefined, {form: fd}); f.file_id = r.file_id; }
      catch (e) { f.err = 'Not uploaded'; toast(`${file.name}: ${e.message}`, true); }
      f.up = false; iTray();
    }
  }
  /* ---- the style sheet: the 9 looks, like the camera sheet ---- */
  function iStyleSheet() {
    const sh = $('#camsheet');
    sh.innerHTML = `<div class="csin" role="dialog" aria-modal="true" aria-labelledby="istT"><div class="csh"><div><h2 id="istT">Style</h2><p class="mut">How the picture looks. Auto lets Hoola choose from your words.</p></div><button class="ib" data-csclose aria-label="Close">${I('x')}</button></div>
      <div class="csb"><div class="csg istg">${STYLES.map((n, i) => `<button type="button" class="csm" data-isty="${i}" aria-pressed="${n === IMG.style}"><span class="ista">${art(STYLE_ART[n] || 'abstract', 'sty' + i)}</span><b>${esc(n || 'Auto')}</b><small>${esc(STYLE_LINE[n])}</small></button>`).join('')}</div></div></div>`;
    sh.hidden = false; paintAll(sh); requestAnimationFrame(() => sh.classList.add('on'));
    sh.onclick = e => { if (e.target === sh || e.target.closest('[data-csclose]')) { camClose(); return; }
      const c = e.target.closest('[data-isty]'); if (c) { IMG.style = STYLES[+c.dataset.isty]; camClose(); iRedraw(); ($('[data-istyopen]') || $('[data-iset]'))?.focus(); } };
    sh.onkeydown = e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); camClose(); ($('[data-istyopen]') || $('[data-iset]'))?.focus(); } };
    ($('.csm[aria-pressed="true"]', sh) || $('.csm', sh))?.focus();
  }
  W.image = (el, o) => {
    const q = $('#imgq'); q.addEventListener('input', () => { IMG.prompt = q.value; q.style.height = 'auto'; q.style.height = Math.min(180, q.scrollHeight) + 'px'; });
    q.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); iSend(); } });
    q.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); iAddFiles(fs); } });
    const box = $('#icomp'), dz = e => { e.preventDefault(); box.classList.toggle('drop', e.type === 'dragover' || e.type === 'dragenter'); };
    ['dragenter', 'dragover', 'dragleave'].forEach(t => $('.vcp', el).addEventListener(t, dz));
    $('.vcp', el).addEventListener('drop', e => { e.preventDefault(); box.classList.remove('drop'); if (e.dataTransfer?.files?.length) iAddFiles(e.dataTransfer.files); });
    $('#iq').addEventListener('input', e => { IMG.q = e.target.value; drawPics(); });
    el.addEventListener('input', e => { if (e.target.id === 'iavoid') IMG.avoid = e.target.value; });
    IMG.thread = window.HoolaChat ? HoolaChat.mount($('#ithread'), {acts: ['copy'], scroller: $('#ilog'), jump: true}) : null;
    iTray(); iPrice();
    load('conf').then(iPrice); load('kit');
    load('items').then(() => redraw('image', drawPics));
    (IMG.chat ? iLoad(true) : iChat()).then(iChatPoll);
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-iset')) { isetOpen($('#isetp').hidden); return; }
      if (b.hasAttribute('data-isdone')) { isetOpen(false); return; }
      if (b.dataset.is) { const k = b.dataset.is, v = b.dataset.isv; IMG[k] = k === 'count' ? +v : v; iRedraw(); return; }
      if (b.hasAttribute('data-isreset')) { Object.assign(IMG, {aspect: '1:1', style: '', quality: 'fast', count: 1, brand: false, avoid: ''}); iRedraw(); return; }
      if (b.hasAttribute('data-istyopen')) { iStyleSheet(); return; }
      if (b.hasAttribute('data-ibrand')) { IMG.brand = !IMG.brand; if (IMG.brand) await load('kit'); iRedraw(); return; }
      if (b.dataset.ifilt) { IMG.filter = b.dataset.ifilt; $$('[data-ifilt]').forEach(x => x.setAttribute('aria-selected', String(x === b))); drawPics(); return; }
      if (b.hasAttribute('data-iplus')) { iAddFiles(await pick('*/*', true)); return; }
      if (b.dataset.ifx) { IMG.files.splice(+b.dataset.ifx, 1); iTray(); return; }
      if (b.hasAttribute('data-inew')) { try { const c = await api('POST', '/api/image/chat/new'); IMG.title = c.title || 'Image chat'; await iChat(c.id); } catch (er) { toast(er.message, true); } return; }
      if (b.hasAttribute('data-ihist')) { let cs = []; try { cs = (await api('GET', '/api/image/chats')).chats || []; } catch (er) { toast(er.message, true); return; }
        if (!cs.length) { toast('No earlier image chats yet'); return; }
        menu(b, cs.map(c => ({v: c.id, label: c.title, sub: c.at ? new Date(c.at.endsWith('Z') || /[+-]\d\d:\d\d$/.test(c.at) ? c.at : c.at + 'Z').toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : ''})), IMG.chat,
          async v => { const c = cs.find(x => x.id === v); IMG.title = c?.title || 'Image chat'; await iChat(v); }, 'Earlier image chats'); return; }
      if (b.hasAttribute('data-idirect')) { b.disabled = true; await iDirect(); iPaint(); return; }
      if (b.dataset.imore) { iMore(b.dataset.imore); return; }
      if (b.hasAttribute('data-improve')) {
        if (!q.value.trim()) { q.focus(); toast('Write a few words first'); return; }
        if (window.HoolaImprove && window.HoolaImprove.ui) {   // HOOLA PROMPTING: the Improve sheet (she sees and edits what Hoola understood)
          window.HoolaImprove.ui.open(q.value, {section: 'image', onUse: t => { q.value = IMG.prompt = String(t).slice(0, 4000); q.focus(); toast('Words updated: edit them or send'); }}); return; }
        b.disabled = true;
        try { const r = await api('POST', '/api/studio/improve', {brief: q.value.trim(), language: 'Hindi', seconds: 30, kind: 'image'}); q.value = IMG.prompt = r.brief; } catch (er) { toast(er.message, true); }
        b.disabled = false; return; }
      if (await itemAction(b)) return;
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; drawPics(); return; }
      if (b.hasAttribute('data-reload')) { await load('items', true); await iJobs(); drawPics(); iLoad(false); return; }
      if (b.id === 'imgGo') iSend();
    });
    el.addEventListener('pointerdown', e => { const p = $('#isetp'); if (!p || p.hidden) return;
      if (e.target.closest('#isetp, [data-iset], #pop, #camsheet')) return; isetOpen(false); });
    $('#isetp').addEventListener('keydown', e => { if (e.key === 'Escape' && $('#camsheet').hidden && $('#pop').hidden) { e.preventDefault(); e.stopPropagation(); isetOpen(false); } });
    if (o.autostart) { IMG.prompt = IMG.prompt || q.value; if (IMG.prompt.trim()) { q.value = IMG.prompt; setTimeout(iSend, 300); } }
  };

  /* ---------------- v0.752 ARTCRAFT IN CREATE (owner: "now lets develop a artcraft in create section in hoola --- artcraft is
     already developed in backend"): the v0.730 shilp lane as a Create tool. ArtCraft's Omni API makes the video / picture with
     HER ArtCraft credits (the key sits in the server's settings, never here); Create = her tap, asked once more because it
     spends credits. Running jobs refresh every few seconds; a finished file is copied once onto her shelf (My creations), so it
     outlives ArtCraft's link. Model ids are ArtCraft's own (snake_case, e.g. seedance_2p0) - the catalog shows their names. */
  const AC = {kind: 'video', model: '', prompt: '', seconds: 5, aspect: 'wide_sixteen_by_nine', res: 'seven_twenty_p', audio: true,
    avoid: '', start: '', end: '', refs: '', ov: null};
  const AC_ASP = [['wide_sixteen_by_nine', '16:9'], ['tall_nine_by_sixteen', '9:16'], ['square', '1:1']];
  const AC_RES = [['seven_twenty_p', '720p'], ['ten_eighty_p', '1080p']];
  const AC_ST = {pending: 'Waiting in ArtCraft’s queue', started: 'Making', attempt_failed: 'Retrying at ArtCraft', unknown: 'Checking'};
  async function acLoad() { try { AC.ov = await api('GET', '/api/shilp'); } catch (e) { AC.ov = AC.ov || {error: e.message, jobs: [], catalog: {}}; } return AC.ov; }
  function acTile(j) {
    const title = esc((j.prompt || '').slice(0, 70) || (j.kind === 'video' ? 'ArtCraft video' : 'ArtCraft picture'));
    const sub = [esc(j.model || ''), j.kind === 'video' ? 'Video' : 'Picture', when(j.created)].filter(Boolean).join(' · ');
    if (!j.done) return `<div class="res gening tall"><span class="thumb">${art(j.kind === 'video' ? 'film' : 'portrait', 'ac' + j.token)}<span class="ring"></span><span class="pct">${esc(AC_ST[j.status] || 'Making')}${j.progress != null ? ' · ' + j.progress + '%' : ''}</span></span><b class="rt">${title}</b><small>${sub}</small></div>`;
    if (j.ok && j.item_id) { const it = (D.items || []).find(x => x.id === j.item_id); if (it) return itemTile(it, true); }
    if (j.ok) return `<div class="res tall"><span class="thumb"><span class="fail">${I(j.kind === 'video' ? 'video' : 'image', 'width:22px;height:22px')}<span>${j.save_error ? 'Made, but the copy for My creations failed: ' + esc(j.save_error) : 'Made - saving to My creations…'}</span></span></span><b class="rt">${title}</b><small>${sub}${j.cdn_url ? ` · <a class="lnk" href="${esc(j.cdn_url)}" target="_blank" rel="noopener noreferrer">Open at ArtCraft</a>` : ''} · <button class="lnk" data-acrm="${esc(j.token)}">Remove</button></small></div>`;
    return `<div class="res failed tall"><span class="thumb"><span class="fail">${I('x', 'width:22px;height:22px')}<span>ArtCraft could not make it (${esc(j.failure || j.status)}). Their rules decide whether credits were used.</span></span></span><b class="rt">${title}</b><small>${sub} · <button class="lnk" data-acrm="${esc(j.token)}">Remove</button></small></div>`;
  }
  function acResults() {
    const el = $('#acres'); if (!el) return; const o = AC.ov || {};
    el.innerHTML = (o.jobs || []).map(acTile).join('') || `<div class="empty" style="grid-column:1/-1"><div><h2>Your ArtCraft work appears here</h2><p class="mut">Pick a model, describe it on the left and press Create.</p></div></div>`;
    paintAll(el); hydrate(el);
  }
  V.artcraft = () => { const o = AC.ov || {}, ready = o.enabled && o.key_set, vid = AC.kind === 'video';
    const used = (o.used_models || []).filter(u => u.kind === AC.kind).map(u => u.model);
    const sugg = [...new Set([...used, ...(vid ? [o.documented_example || 'seedance_2p0'] : [])])];
    if (!AC.model && sugg.length) AC.model = sugg[0];
    const fam = o.catalog?.[vid ? 'video' : 'image'] || {};
    return `<div class="gen">
  <div class="panel"><div class="pbody">
    <div class="seg" role="group" aria-label="Kind"><button aria-pressed="${vid}" data-ackind="video">Video</button><button aria-pressed="${!vid}" data-ackind="image">Picture</button></div>
    <div class="prow"><span class="pi">${I('spark', 'width:16px;height:16px')}</span><div><small>Engine</small><b>ArtCraft · ${(o.counts?.video || 0) + (o.counts?.image || 0) || ''} models</b></div><span class="tag">Your ArtCraft credits</span></div>
    ${o.error ? `<div class="box"><h3>ArtCraft could not be read</h3><p class="note">${esc(o.error)}</p></div>` : !o.enabled ? `<div class="box"><h3>ArtCraft is switched off</h3><p class="note">${esc(o.lane_error || 'The owner turns it on in the server settings.')}</p></div>` : !o.key_set ? `<div class="box"><h3>Connect ArtCraft first</h3><p class="note">${esc(o.setup || 'The owner adds the ArtCraft API key to the server settings.')}</p><p class="note">The key is never typed here or in the chat.</p></div>` : ''}
    <div class="box">
      <h3>Model</h3>
      <label class="fld">ArtCraft model id<input id="acm" list="acml" maxlength="64" autocomplete="off" spellcheck="false" value="${esc(AC.model)}" placeholder="${vid ? 'seedance_2p0' : 'model id from your ArtCraft account'}"></label>
      <datalist id="acml">${sugg.map(m => `<option value="${esc(m)}">`).join('')}</datalist>
      <details class="adv"><summary>${I('down', 'width:14px;height:14px')}What ArtCraft has for ${vid ? 'video' : 'pictures'}</summary>
        <div class="note" style="margin-top:6px">${Object.entries(fam).map(([f, ms]) => `<b>${esc(f)}</b>: ${ms.map(esc).join(', ')}`).join('<br>')}</div>
        <p class="note">These are display names. ArtCraft takes a short id (letters, digits and _ like <b>seedance_2p0</b>); an id your account does not have comes back as ArtCraft’s own error.</p></details>
    </div>
    <div class="box">
      <h3>Describe it <span class="dim num" style="font-size:12.5px;font-weight:400;margin-left:auto" id="acCount">${AC.prompt.length} / 8000</span></h3>
      <textarea id="acq" rows="5" maxlength="8000" placeholder="${vid ? 'Slow dolly in on a clay kulhad of masala chai on a rainy Mumbai balcony, steam rising, warm evening light' : 'A premium product photo of a brass diya on marigold petals, soft morning light, shallow depth of field'}">${esc(AC.prompt)}</textarea>
    </div>
    ${vid ? `<div class="lbl">Shape</div><div class="grid-opts">${AC_ASP.map(([k, t]) => `<button class="go" aria-pressed="${k === AC.aspect}" data-acasp="${k}">${t}</button>`).join('')}</div>
    <div class="lbl">Length and quality</div><div class="grid-opts" style="grid-template-columns:1fr 1fr 1fr">
      <label class="fld" style="margin:0"><input id="acsec" type="number" min="1" max="30" value="${AC.seconds}" aria-label="Seconds"></label>
      ${AC_RES.map(([k, t]) => `<button class="go" aria-pressed="${k === AC.res}" data-acres="${k}">${t}</button>`).join('')}</div>
    <div class="btool" style="margin-top:4px"><span class="dim" style="font-size:14px">Sound from the model</span><span style="flex:1"></span><button class="sw" role="switch" aria-checked="${AC.audio}" data-acaudio aria-label="Sound from the model"><i></i></button></div>` : ''}
    <details class="adv"${AC.avoid || AC.start || AC.end || AC.refs ? ' open' : ''}><summary>${I('down', 'width:14px;height:14px')}Advanced</summary>
      ${vid ? `<label class="fld">Keep out<input id="acavoid" maxlength="200" value="${esc(AC.avoid)}" placeholder="text, watermark, blur"></label>
      <label class="fld">First frame (public link to a picture)<input id="acstart" maxlength="2048" value="${esc(AC.start)}" placeholder="https://…"></label>
      <label class="fld">Last frame (public link to a picture)<input id="acend" maxlength="2048" value="${esc(AC.end)}" placeholder="https://…"></label>` : ''}
      <label class="fld">Reference pictures (public links, one per line)<textarea id="acrefs" rows="3" placeholder="https://…">${esc(AC.refs)}</textarea></label>
      <p class="note">ArtCraft downloads these links itself, so they must be public web addresses. Links to private or local addresses are refused.</p></details>
    <p class="note">Every Create spends credits on your ArtCraft account. The finished ${vid ? 'video' : 'picture'} is saved to My creations.</p>
  </div>
  <div class="pfoot">
    <span style="flex:1"></span>
    <button class="create" id="acGo"${ready ? '' : ' disabled'}>${I('spark', 'width:17px;height:17px')}Create <small>ArtCraft credits</small></button>
  </div></div>
  <div class="stage"><div class="sbar"><b>Your ArtCraft work</b><span class="sp"></span><button class="ib" data-acreload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div>
    <div class="sgrid" id="acres"></div></div></div>`; };
  W.artcraft = el => {
    const me = alive;
    const keep = () => { const v = id => $('#' + id, el)?.value; AC.model = (v('acm') ?? AC.model).trim(); AC.prompt = v('acq') ?? AC.prompt;
      AC.avoid = v('acavoid') ?? AC.avoid; AC.start = v('acstart') ?? AC.start; AC.end = v('acend') ?? AC.end; AC.refs = v('acrefs') ?? AC.refs;
      const s = +(v('acsec') ?? AC.seconds); if (s > 0) AC.seconds = Math.round(s); };
    const tick = async () => {
      if (me !== alive || VIEW !== 'artcraft') return;
      await acLoad(); if ((AC.ov.jobs || []).some(j => j.item_id && !(D.items || []).some(x => x.id === j.item_id))) await load('items', true);
      if (me !== alive) return; acResults();
      if ((AC.ov.jobs || []).some(j => !j.done || (j.ok && !j.item_id && !j.save_error))) poll = setTimeout(tick, 6000);
    };
    if (!AC.ov) { acLoad().then(() => { if (me === alive) go('artcraft'); }); }
    else { load('items').then(() => { if (me === alive) acResults(); }); poll = setTimeout(tick, 1200); }
    $('#acq', el)?.addEventListener('input', e => { $('#acCount', el).textContent = e.target.value.length + ' / 8000'; });
    const create = async b => {
      keep();
      if (!AC.model) { $('#acm', el).focus(); toast('Type the ArtCraft model id first'); return; }
      if (!AC.prompt.trim()) { $('#acq', el).focus(); toast('Describe what ArtCraft should make'); return; }
      if (!confirm(`Start this on ArtCraft with ${AC.model}? It spends credits on your ArtCraft account.`)) return;
      const refs = AC.refs.split(/\s+/).map(x => x.trim()).filter(Boolean);
      const body = AC.kind === 'video'
        ? {kind: 'video', model: AC.model, prompt: AC.prompt.trim(), duration_seconds: AC.seconds, aspect_ratio: AC.aspect, resolution: AC.res,
           generate_audio: AC.audio, negative_prompt: AC.avoid.trim(), start_frame_image_url: AC.start.trim(), end_frame_image_url: AC.end.trim(),
           reference_image_urls: refs, confirm: true}
        : {kind: 'image', model: AC.model, prompt: AC.prompt.trim(), image_urls: refs, confirm: true};
      b.disabled = true; b.classList.add('busy');
      try { await api('POST', '/api/shilp/generate', body); toast('Started on ArtCraft'); await acLoad(); clearTimeout(poll); go('artcraft'); }
      catch (er) { toast(er.message, true); b.disabled = false; b.classList.remove('busy'); }
    };
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (await itemAction(b)) return;
      if (b.dataset.ackind) { keep(); AC.kind = b.dataset.ackind; AC.model = ''; go('artcraft'); return; }
      if (b.dataset.acasp) { AC.aspect = b.dataset.acasp; $$('[data-acasp]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.dataset.acres) { AC.res = b.dataset.acres; $$('[data-acres]', el).forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
      if (b.hasAttribute('data-acaudio')) { AC.audio = !AC.audio; b.setAttribute('aria-checked', String(AC.audio)); return; }
      if (b.hasAttribute('data-acreload')) { keep(); clearTimeout(poll); await tick(); return; }
      if (b.dataset.acrm) { try { await api('DELETE', '/api/shilp/jobs/' + encodeURIComponent(b.dataset.acrm)); await acLoad(); acResults(); } catch (er) { toast(er.message, true); } return; }
      if (b.id === 'acGo') create(b);
    });
  };

  /* ---------------- v0.807 HOOLA CINEMA (cinema.js): one view, its own tools inside; it borrows this studio's helpers ---------------- */
  const CIN = window.HoolaCinema ? window.HoolaCinema({api, esc, I, $, $$, toast, art, when, D, load, items, running, failed,
    jobTile, failTile, itemTile, itemAction, paintAll, hydrate, upload, pick, startJob, menu, go: v => go(v), token: () => alive, view: () => VIEW,
    later: (fn, ms) => { clearTimeout(poll); poll = setTimeout(fn, ms); }}) : null;
  if (CIN) { V.cinema = CIN.view; W.cinema = CIN.wire; }

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
  // v0.807 26 camera moves (were 8); the same list Hoola Cinema uses
  const CAMS = [['Auto', ''], ['Static', 'the camera holds still on a tripod'], ['Dolly in', 'slow dolly in towards the subject'], ['Dolly out', 'slow dolly out that reveals the scene'], ['Crash zoom', 'a sudden fast zoom into the subject'],
    ['Orbit', 'the camera orbits around the subject'], ['Arc', 'the camera moves in a slow arc around the subject'], ['Crane up', 'a crane shot rising up and over the scene'], ['Crane down', 'a crane shot coming down towards the subject'],
    ['Tracking', 'a tracking shot moving alongside the subject'], ['Follow', 'the camera follows close behind the subject'], ['Pan', 'smooth slow pan across the scene'], ['Whip pan', 'a very quick pan to the subject with motion blur'],
    ['Tilt up', 'the camera tilts up from the ground to the subject'], ['Tilt down', 'the camera tilts down from the sky to the subject'], ['Drone', 'a high aerial drone shot moving forward'], ['FPV drone', 'a fast swooping first-person drone flight'],
    ['Handheld', 'natural handheld camera, slight movement'], ['Bullet time', 'the action freezes while the camera sweeps around the subject'], ['Rack focus', 'the focus shifts from the foreground to the subject'],
    ['Dutch angle', 'a tilted frame with slow movement'], ['POV', 'a first-person point of view'], ['Low angle', 'a low hero angle looking up, slow push in'], ['Top down', 'an overhead shot looking straight down, turning slowly'],
    ['Zoom out', 'a slow zoom out that shows the wider place'], ['Slow motion', 'slow motion, smooth and dreamy']];
  const VID = {camera: 'Auto', prompt: '', aspect: '9:16', seconds: 8, res: '1080p', model: '', audio: true, takes: 1, language: 'Hindi', price: null, auto: 'quality', compare: [],
    chat: '', title: '', files: [], thread: null, rows: [], turn: null, sending: false, working: false, loading: false, filter: 'all', q: '', lastSend: null, seq: 0};   // v0.999.43 the Video chat
  const vm = () => mOf(VID.model);
  const lenOpts = m => { const a = m?.allowed_durations; if (a?.length) return a; const [lo, hi] = m?.durations?.length ? m.durations : [4, 30];
    return [4, 5, 6, 8, 10, 12, 15, 20, 25, 30].filter(x => x >= lo && x <= hi); };
  const resOpts = m => m ? resSort(m.resolutions || []) : ['480p', '720p', '1080p', '4k'];
  /* v0.999.43 VIDEO CHAT (owner, on the design canvas: "THIS IS TO BE A FULL CHAT PANEL -- AND AT BOTTOM THERE IS DIFFERENT
     OPTIONS REGARDING VIDEO -- ALSO IN THIS CHAT USER CAN UPLOAD IMAGES, VIDEOS, DOCUMENTS, EVERY FILE" -> "GO BUILD").
     Left: a real Hoola chat of its own (/api/video/chat, Conversation kind 'video') on the chat kit; her picks under the box
     ride each message as a "[Web console Video settings: ...]" note, her files as chat files; Hoola makes the clip with
     video_studio action=clip and the clip's card (plan, price card, progress, the clip) sits in the chat after the reply.
     Right: Your videos with filters + search. If Hoola cannot answer, "Make it straight away" makes the same clip directly. */
  const CAMG = [['Simple', ['Auto', 'Static', 'Handheld', 'Slow motion']], ['Closer or further', ['Dolly in', 'Dolly out', 'Crash zoom', 'Zoom out', 'Rack focus']],
    ['Around the subject', ['Orbit', 'Arc', 'Bullet time']], ['Up and down', ['Crane up', 'Crane down', 'Tilt up', 'Tilt down']],
    ['Side to side', ['Pan', 'Whip pan', 'Tracking', 'Follow']], ['From the air', ['Drone', 'FPV drone', 'Top down']], ['Angle', ['Dutch angle', 'POV', 'Low angle']]];
  const CAMD = {'Auto': 'M26 20h4M28 18v4', 'Static': 'M22 36h12M28 30v6', 'Handheld': 'M8 14q3-3 6 0M42 26q3 3 6 0', 'Slow motion': 'M7 16v8M11 16v8M45 16v8M49 16v8',
    'Dolly in': 'M4 20h8M9 17l3 3-3 3M52 20h-8M47 17l-3 3 3 3', 'Dolly out': 'M12 20H4M7 17l-3 3 3 3M44 20h8M49 17l3 3-3 3', 'Crash zoom': 'M4 5l10 7M52 5l-10 7M4 35l10-7M52 35l-10-7',
    'Zoom out': 'M14 12L6 6M42 12l8-6M14 28l-8 6M42 28l8 6', 'Rack focus': 'M28 15v10M23 20h10', 'Orbit': 'M4 20c0-8 48-8 48 0s-48 8-48 0M49 15l3 5-5 1',
    'Arc': 'M6 34C10 8 46 8 50 34M47 31l3 3 2-4', 'Bullet time': 'M4 20c0-8 48-8 48 0M24 20h8', 'Crane up': 'M6 36C10 22 16 14 24 6M20 6h4v4',
    'Crane down': 'M6 4c4 14 10 22 18 30M20 34h4v-4', 'Tilt up': 'M8 30V10M5 13l3-3 3 3', 'Tilt down': 'M8 10v20M5 27l3 3 3-3', 'Pan': 'M3 20h9M9 17l3 3-3 3M44 20h9',
    'Whip pan': 'M2 16h12M2 20h12M2 24h12', 'Tracking': 'M12 36h32M41 33l3 3-3 3', 'Follow': 'M28 32v6M24 36h8M28 8v-5', 'Drone': 'M6 5h10M40 5h10M11 5v4M45 5v4',
    'FPV drone': 'M4 36C14 10 30 36 52 6M48 6h4v4', 'Top down': 'M28 2v6M28 32v6M24 20h8', 'Dutch angle': 'M10 32L46 8', 'POV': 'M20 20c3-4 13-4 16 0-3 4-13 4-16 0z',
    'Low angle': 'M28 38l-10-6M28 38l10-6'};
  const camPic = n => `<svg class="cpic" viewBox="0 0 56 40" aria-hidden="true"><rect x="16" y="10" width="24" height="20" rx="3"/><path d="${CAMD[n] || ''}"/></svg>`;
  const camLine = n => n === 'Auto' ? 'The model chooses the best move' : ((CAMS.find(c => c[0] === n) || [])[1] || '').replace(/^./, c => c.toUpperCase());
  const AUTO_NAME = {quality: 'best quality', value: 'best value', cheap: 'lowest price'};
  const modelLabel = () => VID.compare.length ? VID.compare.map(k => mOf(k)?.name || k).join(' vs ') : vm() ? vm().name : 'Hoola Auto';
  const VFILES = n => /\.(png|jpe?g|webp|heic|heif|gif|bmp|avif)$/i.test(n) ? 'image' : /\.(mp4|mov|m4v|webm|mkv|3gp)$/i.test(n) ? 'video'
    : /\.(mp3|m4a|wav|ogg|opus|aac|flac)$/i.test(n) ? 'audio' : /\.pdf$/i.test(n) ? 'pdf' : /\.(xlsx?|csv|ods)$/i.test(n) ? 'sheet' : /\.(docx?|odt|rtf|txt|md)$/i.test(n) ? 'doc' : 'file';
  /* v0.999.46 THE CHAT BAR, option A (owner: "CHAT BAR HAVING HUGE OPTIONS ... LOOKS VERY BAD AND STALE" -> design canvas
     claude.ai/artifact/V8XevvPcwUSrXcCxiJrnLW -> "GO WITH A"): under her words only + , ONE quiet settings button that
     reads back shape · length · quality, the model, Improve and Send. The button opens "Video settings" above the box:
     shape, length, quality as rows of choices, camera (the 26-move sheet), sound + spoken language, takes, the price, Done. */
  const SHAPES = [['9:16', 'Reels, Shorts, Stories'], ['16:9', 'YouTube, websites'], ['1:1', 'Feed posts']];
  const SHAPE_BOX = {'9:16': [7, 12], '16:9': [13, 7], '1:1': [10, 10]};
  const setSummary = () => `${VID.aspect} · ${VID.seconds} s · ${VID.res}`;
  function voptsHTML() {
    const open = !$('#vsetp')?.hidden;
    return `<button type="button" class="vset" data-vset aria-haspopup="dialog" aria-expanded="${open}" aria-controls="vsetp" title="Video settings">${I('sliders', 'width:16px;height:16px')}<span>${esc(setSummary())}</span>${I(open ? 'up' : 'down', 'width:14px;height:14px')}</button>`
      + `<button type="button" class="vmdl" data-pickmodel title="Choose the model">${I('spark', 'width:15px;height:15px')}<span>${esc(modelLabel())}</span></button>`;
  }
  // the lengths a person picks (5 / 8 / 10 / 15 / 20 / 30 s) that this model makes, plus the one set now: one row, never two
  const lenShown = m => { const all = lenOpts(m), pick = all.filter(x => [5, 8, 10, 15, 20, 30].includes(x) || x === VID.seconds); return pick.length >= 3 ? pick : all; };
  function vsetHTML() {
    const m = vm(), seg = (k, list, cur, fmt) => `<div class="seg vsg" role="radiogroup">${list.map(v => `<button type="button" role="radio" aria-checked="${String(v) === String(cur)}" data-vs="${k}" data-vsv="${esc(String(v))}">${fmt ? fmt(v) : esc(String(v))}</button>`).join('')}</div>`;
    const row = (label, body, note) => `<div class="vsr"><span class="vsl">${label}</span><div class="vsc">${body}${note ? `<small>${note}</small>` : ''}</div></div>`;
    const shp = v => { const [w, h] = SHAPE_BOX[v] || [10, 10]; return `<i class="vsh" style="width:${w}px;height:${h}px"></i>${esc(v)}`; };
    return `<div class="vsh0"><b id="vsetT">Video settings</b><button type="button" class="lnk" data-vsreset>Reset</button></div>`
      + row('Shape', seg('aspect', SHAPES.map(x => x[0]), VID.aspect, shp), esc((SHAPES.find(x => x[0] === VID.aspect) || [])[1] || ''))
      + row('Length', seg('seconds', lenShown(m), VID.seconds, v => v + ' s'), 'Longer than 30 s? Use Director')
      + row('Quality', seg('res', resOpts(m), VID.res))
      + row('Camera', `<button type="button" class="vsb" data-vcamopen>${I('video', 'width:16px;height:16px')}<span>${esc(VID.camera === 'Auto' ? 'Auto · let Hoola choose' : VID.camera)}</span>${I('right', 'width:14px;height:14px')}</button>`, '26 drawn moves')
      + row('Sound', `<button type="button" class="sw" role="switch" aria-checked="${VID.audio}" data-vaudio aria-label="Sound"><i></i></button>`
          + (VID.audio ? `<span class="vstx">Spoken lines in</span><button type="button" class="vsb" data-vopt="lang" aria-haspopup="menu"><span>${esc(VID.language)}</span>${I('down', 'width:14px;height:14px')}</button>` : '<span class="vstx">A silent clip</span>'))
      + row('Takes', seg('takes', [1, 2, 3, 4], VID.takes), VID.takes > 1 ? 'Each take is paid; you pick the best' : '')
      + `<div class="vsf"><span id="vsetCost">${esc(VID.priceLine || 'The price shows here')}</span><button type="button" class="vdone" data-vsdone>Done</button></div>`;
  }
  function vsetOpen(on) {
    const p = $('#vsetp'); if (!p) return;
    if (on) { p.innerHTML = vsetHTML(); p.hidden = false; requestAnimationFrame(() => p.classList.add('on')); ($('[aria-checked="true"]', p) || $('button', p))?.focus(); }
    else { p.classList.remove('on'); p.hidden = true; p.innerHTML = ''; }
    const o = $('#vopts'); if (o) o.innerHTML = voptsHTML();
    if (!on) $('[data-vset]')?.focus();
  }
  const voptsRedraw = () => { const o = $('#vopts'); if (o) o.innerHTML = voptsHTML(); const p = $('#vsetp'); if (p && !p.hidden) { const f = p.contains(p.getRootNode().activeElement) ? p.getRootNode().activeElement : null, k = f?.dataset?.vs ? `[data-vs="${f.dataset.vs}"][aria-checked="true"]` : f?.hasAttribute?.('data-vaudio') ? '[data-vaudio]' : ''; p.innerHTML = vsetHTML(); if (k) $(k, p)?.focus(); } livePrice(); };
  V.video = () => `<div class="gen vchat">
  <section class="panel vcp" aria-label="Video chat">
    <div class="vch"><span class="vcm">${I('video', 'width:16px;height:16px')}</span><div class="vct"><b id="vcTitle">${esc(VID.title || 'Video chat')}</b><small>Describe a shot or add files. The price shows before anything is made.</small></div>
      <button class="ib" data-vhist aria-label="Earlier video chats" title="Earlier video chats">${I('redo')}</button><button class="ib" data-vnew aria-label="New video chat" title="New video chat">${I('plus')}</button></div>
    <div class="vlog" id="vlog"><div id="vthread"></div><div id="vfail"></div></div>
    <div class="vcomp" id="vcomp">
      <div class="vsetp" id="vsetp" role="dialog" aria-labelledby="vsetT" hidden></div>
      <div class="vbox" id="vbox">
        <div class="vtray" id="vtray" role="list" aria-label="Files to send"></div>
        <label class="sr" for="vidq">Message Hoola about your video</label>
        <textarea id="vidq" rows="2" maxlength="2000" placeholder="Describe a shot, or ask for a change…">${esc(VID.prompt)}</textarea>
        <div class="vrow">
          <button type="button" class="vplus" data-vplus aria-label="Add photos, videos, documents or any file" title="Add files">${I('plus')}</button>
          <div class="vopts" id="vopts">${voptsHTML()}</div>
          <button type="button" class="ib" data-improve aria-label="Improve my words" title="Improve my words">${I('wand')}</button>
          <button type="button" class="vsend" id="vidGo" aria-label="Send">${I('send')}</button>
        </div>
      </div>
      <p class="vfoot" id="vprice">Drop any file here: photos, videos, PDFs, sheets, audio. Nothing is spent until you tap Yes.</p>
    </div>
  </section>
  <div class="stage vst"><div class="sbar vsbar"><b>Your videos</b><span class="mut num" id="vcount"></span><span class="sp"></span>
      <div class="vseg" role="tablist" aria-label="Show">${[['all', 'All'], ['mk', 'Making'], ['ok', 'Ready'], ['na', 'Needs you']].map(([k, t]) => `<button type="button" role="tab" data-vfilt="${k}" aria-selected="${VID.filter === k}">${t}<i class="num" data-vn="${k}"></i></button>`).join('')}</div>
      <label class="vsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search your videos</span><input id="vq" type="search" placeholder="Search" value="${esc(VID.q)}"></label>
      <button class="ib" data-reload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button><button class="lnk vfilm" data-go="director">${I('clap', 'width:14px;height:14px')}Longer film</button></div>
    <div class="sgrid" id="results"></div></div></div>`;
  // one tile per Video Studio project: its newest picked take / output, its live state, and any price card waiting
  function projMedia(p) {
    const out = (p.outputs || []).slice(-1)[0];
    if (out?.url) return `<video muted playsinline preload="metadata" src="${esc(out.url)}"${out.thumb ? ` poster="${esc(out.thumb)}"` : ''}></video>`;
    for (const s of p.shots || []) { const t = (s.take_list || []).find(x => x.picked) || (s.take_list || []).slice(-1)[0]; if (t?.url) return `<video muted playsinline preload="metadata" src="${esc(t.url)}"></video>`; }
    const kf = (p.shots || []).find(s => s.keyframe); if (kf) return `<img alt="" src="${esc(kf.keyframe)}">`;
    return filmTile(p.project);
  }
  // v0.320 a film with no picture yet; v0.999.42 a painted scene + film mark (a big pink letter read as an empty block)
  function filmTile(name) {
    return `${art('film', 'f' + name)}<span class="ph-mark" aria-hidden="true">${I('clap')}</span>`;
  }
  // a voice's initial on a calm colour of its own (voice list)
  function initTile(name) {
    let h = 0; for (const c of String(name)) h = (h * 31 + c.codePointAt(0)) % 360;
    const ch = [...String(name).trim()][0] || '·';
    return `<span class="finit" style="--fh:${h}" aria-hidden="true"><b>${esc(ch.toUpperCase())}</b></span>`;
  }
  // the price card: line by line, the total on the Haan button; nothing runs before it, never more than it
  function approvalRow(a) {
    const what = {generate: `${a.shots || ''} shot${a.shots === 1 ? '' : 's'} · ${a.quality || ''}`, keyframes: `${a.shots} opening picture${a.shots === 1 ? '' : 's'}`, music: 'Music track (Google Lyria)', character: `Character picture · ${a.name || ''}`}[a.kind] || a.kind;
    const rows = (a.rows || []).map(r => `<tr><td>${esc(r.name)}${r.lipsync ? ' + lip sync' : ''}</td><td class="num">${r.seconds} s${r.takes > 1 ? ' × ' + r.takes : ''}</td><td>${esc(r.resolution)}${r.audio === false ? ' · silent' : ''}</td><td class="num">${money(r.inr)}</td></tr>`).join('');
    const extra = [a.keyframes ? `<tr><td>Opening pictures × ${a.keyframes}</td><td></td><td></td><td class="num">${money(a.keyframes_inr)}</td></tr>` : '', a.music ? `<tr><td>Music (${esc(a.music)})</td><td></td><td></td><td class="num">${money(a.music_inr)}</td></tr>` : ''].join('');
    return `<div class="appr"><div class="aph"><b class="num">${inr(a.inr)}</b><small>${esc(what)}</small></div>
      ${rows || extra ? `<table class="aprows">${rows}${extra}</table>` : ''}
      <small class="apn">Nothing is spent until you tap Yes. You are never charged more than ${inr(a.inr)}.</small>
      <div class="apb"><button class="btn sec" data-no="${esc(a.id)}">No</button><button class="btn pri" data-yes="${esc(a.id)}">Yes, make it · ${inr(a.inr)}</button></div></div>`;
  }
  // v0.325 what state a clip / film is in, in one word
  function projState(p) {
    const busy = p.working || p.planning || (p.painting || []).length;
    const made = (p.outputs || []).some(o => o.url) || (p.shots || []).some(x => (x.take_list || []).some(t => t.url));
    // v0.999.43 a price card waiting is "Needs your Yes" (it read "Draft" while the card sat right under it)
    return busy ? ['Making', 'mk'] : (p.approvals || []).length ? ['Needs your Yes', 'na'] : p.error ? ['Needs attention', 'na'] : made ? ['Ready', 'ok'] : ['Draft', 'dr'];
  }
  function projTile(p) {
    const busy = p.working || p.planning || (p.painting || []).length, [stl, stc] = projState(p);
    return `<div class="res${busy ? ' gening' : ''}" data-proj="${esc(p.project)}"><button class="thumb" data-openproj="${esc(p.project)}" aria-label="Open ${esc(p.project)}" title="${VIEW === 'video' ? 'Play' : 'Open in Director'}">${projMedia(p)}${busy ? `<span class="ring"></span><span class="pct">${p.progress?.pct != null ? p.progress.pct + '%' : p.planning ? 'Writing the plan' : 'Working'}</span>` : `<span class="badge">${I('play', 'width:11px;height:11px')}${esc(p.aspect)}</span>${stc === 'ok' ? `<span class="dur num">${p.seconds || 0} s</span>` : ''}`}</button>
      <b class="rt">${esc(p.project)}<span class="stchip ${stc}">${stl}</span></b><small>${esc((p.brief || '').slice(0, 80))}</small>${p.error && !busy && VIEW !== 'video' ? `<small class="perr">${I('x', 'width:13px;height:13px')}${esc(p.error)}</small>` : ''}${moneyLine(p.money)}${(p.approvals || []).map(approvalRow).join('')}</div>`;
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
  // v0.325 failures as ONE calm notice above the clips (a red line under every tile read as a gallery of failures)
  function vnote(ps) {
    const bad = ps.filter(p => p.error && !(p.working || p.planning || (p.painting || []).length)); if (!bad.length) return '';
    const why = [...new Set(bad.map(p => p.error))];
    return `<div class="vnote" style="grid-column:1/-1">${I('x', 'width:15px;height:15px')}<div><b>${bad.length} clip${bad.length > 1 ? 's' : ''} could not start.</b><small>${esc(why.length === 1 ? why[0] : 'Open a clip marked “Needs attention” to see why.')} Nothing was charged for them.</small></div></div>`;
  }
  // v0.333 a re-draw keeps every tile whose content did not change: the 4-15 s poll used to rebuild ALL tiles, so every video
  // reloaded and the whole "Your videos" grid blinked out and back. Unchanged tiles are kept as they are (playing, scrolled, loaded).
  function patch(el, html) {
    if (el._html === html) return false;
    el._html = html;
    const t = document.createElement('template'); t.innerHTML = html;
    const old = new Map(); [...el.children].forEach(c => { if (c._src && !old.has(c._src)) old.set(c._src, c); });
    const kids = [...t.content.children].map(n => { const src = n.outerHTML, keep = old.get(src); if (keep) { old.delete(src); return keep; } n._src = src; return n; });
    kids.forEach((k, i) => { if (el.children[i] !== k) el.insertBefore(k, el.children[i] || null); });
    while (el.children.length > kids.length) el.lastElementChild.remove();
    return true;
  }
  function drawVideos() {
    const el = $('#results'); if (!el) return;
    const all = (D.studio?.projects || []), q = (VID.q || '').toLowerCase();
    const cnt = {all: all.length, mk: 0, ok: 0, na: 0}; all.forEach(p => { const k = projState(p)[1]; if (k in cnt) cnt[k]++; });
    $$('[data-vn]').forEach(n => { const v = cnt[n.dataset.vn]; n.textContent = n.dataset.vn !== 'all' && v ? ' · ' + v : ''; });
    const c = $('#vcount'); if (c) c.textContent = all.length ? String(all.length) : '';
    // v0.999.43 the filters + search (a long list of clips had no way to find the one she wanted)
    const ps = all.filter(p => { const k = projState(p)[1];
      return (VID.filter === 'all' || k === VID.filter)
        && (!q || (p.project + ' ' + (p.brief || '')).toLowerCase().includes(q)); });
    patch(el, (D.studio && D.studio.available === false ? `<div class="empty" style="grid-column:1/-1"><div><h2>Video Studio is off on this server</h2><p class="mut">It needs ffmpeg and STUDIO_ON on the server.</p></div></div>` : '')
      + (VID.busy ? `<div class="res gening"><span class="thumb">${art('film', 'vb')}<span class="ring"></span><span class="pct">${esc(VID.busy)}</span></span><b class="rt">${esc(VID.prompt.slice(0, 48))}</b><small>Hoola is writing the shot plan; the price card comes next</small></div>` : '')
      + vnote(all) + (ps.map(projTile).join('') || (VID.busy ? '' : all.length ? `<div class="empty" style="grid-column:1/-1"><div><h2>Nothing here</h2><p class="mut">No clip matches this filter.</p></div></div>`
        : `<div class="empty" style="grid-column:1/-1"><div><h2>Your videos appear here</h2><p class="mut">Describe a shot in the chat, see the price, tap Yes.</p></div></div>`)));
    paintAll(el);
    drawChatClips();
  }
  // the card a clip has in the chat: its picture, what it is, the price card or its progress, the clip itself when made
  function chatClip(p) {
    const busy = p.working || p.planning || (p.painting || []).length, [stl, stc] = projState(p);
    const shot = (p.shots || [])[0] || {};
    const line = p.planning ? 'Writing the shot plan…' : busy && p.progress ? `Filming · ${p.progress.pct}%${p.progress.eta_s ? ' · about ' + Math.max(1, Math.ceil(p.progress.eta_s / 60)) + ' min' : ''}`
      : busy ? 'Working…' : (p.approvals || []).length ? 'Shot plan ready · the price is below' : stl;
    return `<div class="vcl${busy ? ' gening' : ''}"><button class="vclt thumb" data-openproj="${esc(p.project)}" aria-label="Open ${esc(p.project)}">${projMedia(p)}${busy ? '<span class="ring"></span>' : stc === 'ok' ? `<span class="badge">${I('play', 'width:11px;height:11px')}${esc(p.aspect)}</span>` : ''}</button>
      <div class="vclb"><b>${esc(p.project)}<span class="stchip ${stc}">${stl}</span></b>
        <small class="mut">${esc(shot.prompt || p.brief || '').slice(0, 220)}</small>
        <span class="vclm">${[p.aspect, p.seconds ? p.seconds + ' s' : '', p.start_frame ? 'starts on your photo' : ''].filter(Boolean).map(x => `<span class="tag">${esc(x)}</span>`).join('')}</span>
        <small class="vcll${p.error && !busy ? ' err' : ''}">${esc(p.error && !busy ? plainErr(p.error) : line)}</small>
        ${busy && p.progress ? `<span class="bar"><i style="width:${p.progress.pct}%"></i></span>` : p.planning ? '<span class="bar"><i class="indet"></i></span>' : ''}
        ${moneyLine(p.money)}</div>
      ${(p.approvals || []).map(approvalRow).join('')}</div>`;
  }
  function drawChatClips() {
    const ps = new Map((D.studio?.projects || []).map(p => [p.project, p]));
    $$('[data-vclip]').forEach(n => { const p = ps.get(n.dataset.vclip); if (!p) return; const h = chatClip(p); if (n._h === h) return; n._h = h; n.innerHTML = h; paintAll(n); });
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
  // the live price: asked from the server on every change (the same table the price card uses); v0.999.43 shown under the box
  let priceT = 0, priceN = 0;
  function livePrice() {
    clearTimeout(priceT); const n = ++priceN;
    priceT = setTimeout(async () => {
      try {
        const ask = mdl => api('POST', '/api/studio/price', {model: mdl, seconds: VID.seconds, resolution: VID.res, audio: VID.audio, takes: VID.takes, auto: VID.auto});
        const rs = VID.compare.length ? await Promise.all(VID.compare.map(ask)) : [await ask(VID.model)];
        if (n !== priceN || VIEW !== 'video') return; const r = rs[0], tot = rs.reduce((t, x) => t + x.inr, 0); VID.price = r;
        VID.priceLine = `About ${money(tot)}${VID.takes > 1 ? ' for ' + VID.takes + ' takes' : ''} · you approve the price first`; const pc = $('#vsetCost'); if (pc) pc.textContent = VID.priceLine;
        const el = $('#vprice'); if (!el) return;
        el.innerHTML = `<b class="num" id="vidCost">≈ ${money(tot)}</b> · <span>${rs.map(x => `${x.seconds} s × ${esc(x.resolution)}${x.takes > 1 ? ' × ' + x.takes + ' takes' : ''}${x.audio ? '' : ' · silent'}`).join(' + ')}${rs.length > 1 ? ' · each model makes the same shot' : ''} · nothing is spent until you tap Yes</span>`
          + (r.changed?.length ? ` <span class="warnl">This model makes ${r.changed.map(k => k === 'seconds' ? r.seconds + ' s' : r.resolution).join(' and ')}.</span>` : '')
          + (r.ready ? '' : ' <span class="warnl">This model is not switched on on the server yet.</span>');
      } catch (e) { /* the price line keeps its plain words */ }
    }, 220);
  }
  // what she picked under the box, said to Hoola beside her words (her bubble shows only her words)
  function settingsLine() {
    const cam = VID.camera === 'Auto' ? 'Auto (the model chooses)' : `${VID.camera} (${(CAMS.find(c => c[0] === VID.camera) || [])[1] || ''})`;
    const mdl = VID.compare.length ? `compare ${VID.compare.join(', ')}` : VID.model ? `model ${VID.model}` : `Hoola Auto, ${AUTO_NAME[VID.auto] || 'best quality'} (auto=${VID.auto})`;
    const first = VID.files.find(f => f.kind === 'image' && f.first && f.file_id);
    return `Video settings: shape ${VID.aspect}, length ${VID.seconds} s, camera ${cam}, ${mdl}, resolution ${VID.res}, `
      + `${VID.audio ? 'sound on' : 'no sound (audio=false)'}, ${VID.takes} take${VID.takes > 1 ? 's' : ''}, spoken lines in ${VID.language}`
      + (first ? `, first frame = ${first.name} (start_image_file_id ${first.file_id})` : '') + '. Make it with video_studio action=clip.';
  }
  // v0.309 ONE call (plan in the background, then the price card); v0.999.43 also the chat's "Make it straight away"
  async function newClip(preview, src) {
    const s = src || {brief: VID.prompt, files: VID.files};
    let brief = (s.brief || '').trim(); if (!brief) { $('#vidq')?.focus(); toast('Describe the shot first'); return; }
    const cam = (CAMS.find(c => c[0] === VID.camera) || [])[1]; if (cam) brief += `\nCamera: ${cam}.`;   // v0.304 the camera preset rides the brief
    if (VID.busy) return;
    VID.busy = 'Writing the plan'; drawVideos();
    const name = 'Clip ' + new Date().toLocaleString('en-IN', {day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false}).replace(',', '');
    const quality = preview ? 'preview' : QOF(VID.res);
    const first = (s.files || []).find(f => f.kind === 'image' && f.first && f.file_id);
    try {
      await api('POST', '/api/studio/projects', {name, brief, aspect: VID.aspect, seconds: VID.seconds, language: VID.language,
        quality: preview ? 'draft' : quality, model: VID.model, resolution: VID.res, auto: VID.auto,
        then: preview ? 'preview' : 'generate', variants: preview ? 1 : VID.takes, compare: !preview && VID.compare.length > 1 ? VID.compare : null,
        audio: VID.audio ? null : false, start_image_file_id: first?.file_id || '', conversation_id: VID.chat || ''});
      toast(preview ? 'Writing the shot plan, then your free preview starts.' : 'Writing the shot plan (about a minute). The price card appears on the clip; nothing is spent until you tap Yes.');
    } catch (e) { toast(e.status === 428 ? fp : e.message, true); }
    VID.busy = ''; await load('studio', true); redraw('video', drawVideos);
  }
  // v0.309 a clip PLAYS; v0.999.43 the player sits beside what it is, what it cost and what to do next
  function clipOpen(name) {
    const p = (D.studio?.projects || []).find(x => x.project === name); if (!p) return;
    const out = (p.outputs || []).slice(-1)[0];
    let url = out?.url || '';
    if (!url) for (const s of p.shots || []) { const t = (s.take_list || []).find(x => x.picked) || (s.take_list || []).slice(-1)[0]; if (t?.url) { url = t.url; break; } }
    if (url) {
      const lb = $('#lightbox'), shot = (p.shots || [])[0] || {};
      lb.innerHTML = `<div class="lbin vlb" role="dialog" aria-modal="true" aria-label="${esc(name)}"><div class="lbh"><b>${esc(name)}</b><button class="ib" data-lbclose aria-label="Close">${I('x')}</button></div>
        <div class="vlbb"><div class="lbm"><video controls autoplay playsinline src="${esc(url)}"></video></div>
          <aside class="vlbs"><span class="stchip ok">Ready</span><p class="vlbw">${esc(p.brief || shot.prompt || '')}</p>
            <dl><div><dt>Clip</dt><dd class="num">${esc([p.seconds ? p.seconds + ' s' : '', p.aspect].filter(Boolean).join(' · '))}</dd></div>${shot.model_label ? `<div><dt>Model</dt><dd>${esc(shot.model_label)}</dd></div>` : ''}${p.money?.takes ? `<div><dt>You paid</dt><dd class="num">${money(p.money.billed_inr)}${p.money.estimate_inr > p.money.billed_inr + 0.05 ? ` <span class="mut">· card said ${money(p.money.estimate_inr)}</span>` : ''}</dd></div>` : ''}</dl>
            <a class="btn pri" href="${esc(url)}" download="${esc(name)}.mp4">${I('dl', 'width:15px;height:15px')}Download</a>
            <button class="btn sec" data-vagain="${esc(name)}">${I('redo', 'width:15px;height:15px')}Change and make again</button>
            <button class="btn sec" data-openproj-dir="${esc(name)}">${I('clap', 'width:15px;height:15px')}Edit in Director</button></aside></div></div>`;
      lb.hidden = false; $('[data-lbclose]', lb).focus(); return;
    }
    if (p.planning) { toast('Hoola is still writing the shot plan. The price card appears on this clip in a moment.'); return; }
    if ((p.approvals || []).length) { R.querySelector(`[data-proj="${CSS.escape(name)}"] .appr`)?.scrollIntoView({block: 'nearest', behavior: 'smooth'}); toast('Check the price card under the picture, then tap Yes to make it.'); return; }
    if (p.working || (p.painting || []).length) { toast('Your clip is being made. It plays here when it is ready.'); return; }
    if (p.error) { toast(p.error, true); return; }
    DIR.project = name; DIR.view = null; go('director');
  }
  function fitToModel() {          // keep length / resolution inside what the chosen model makes
    const m = vm(); if (!m) return;
    const L = lenOpts(m); if (L.length && !L.includes(VID.seconds)) VID.seconds = L.reduce((a, b) => Math.abs(b - VID.seconds) < Math.abs(a - VID.seconds) ? b : a);
    const R = resOpts(m); if (R.length && !R.includes(VID.res)) VID.res = R.find(r => RES.indexOf(r) >= RES.indexOf(VID.res)) || R[R.length - 1];
  }

  /* ---- the chat ---- */
  const stripNotes = t => String(t || '').replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  const atOf = s => { s = String(s || ''); return s ? Date.parse(/[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : s + 'Z') / 1000 : 0; };
  const SENT_KEY = 'hoola.vchat.files';
  function sentFiles() { try { return JSON.parse(sessionStorage.getItem(SENT_KEY) || '{}'); } catch { return {}; } }
  function keepSent(text, files) { if (!files.length) return; try { const m = sentFiles(); m[VID.chat + '|' + text.trim()] = files.map(f => f.name); sessionStorage.setItem(SENT_KEY, JSON.stringify(m)); } catch {} }
  function threadList() {
    const sf = sentFiles();
    const msgs = VID.rows.map(r => { const t = r.role === 'user' ? stripNotes(r.text) : String(r.text || '');
      return {id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: t, at: atOf(r.at), files: r.role === 'user' ? (sf[VID.chat + '|' + t.trim()] || []) : undefined}; });
    const lastHer = [...msgs].reverse().find(m => m.role === 'her')?.at || 0;
    const clips = (D.studio?.projects || []).filter(p => p.chat && p.chat === VID.chat && !(VID.working && p.created_ts > lastHer - 1))
      .sort((a, b) => a.created_ts - b.created_ts);
    const after = new Map();       // a clip sits after the reply of the turn that made it (or after her message when none)
    for (const c of clips) { let i = -1; msgs.forEach((m, j) => { if (m.at <= c.created_ts + 1) i = j; });
      if (i >= 0 && msgs[i].role === 'her' && msgs[i + 1]?.role === 'hoola') i++;
      (after.get(i) || after.set(i, []).get(i)).push(c); }
    const out = [...(after.get(-1) || []).map(rawClip)];
    msgs.forEach((m, j) => { out.push(m); (after.get(j) || []).forEach(c => out.push(rawClip(c))); });
    return out;
  }
  const rawClip = p => ({id: 'clip:' + p.project, role: 'raw', html: `<div class="vclip" data-vclip="${esc(p.project)}"></div>`});
  async function vLoad(first) {
    if (!VID.chat || VID.loading || !VID.thread) return;
    const chat = VID.chat; VID.loading = true;
    try {
      const last = VID.rows[VID.rows.length - 1];
      if (VID.sending || VID.working || (last && last.role === 'user') || first) {
        try { VID.turn = await api('GET', `/api/conversations/${encodeURIComponent(chat)}/result`); } catch {}
      }
      let rows; try { rows = (await api('GET', `/api/conversations/${encodeURIComponent(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== VID.chat) return;
      VID.rows = rows; vPaint();
    } finally { VID.loading = false; }
  }
  function vPaint() {
    if (!VID.thread || VIEW !== 'video') return;
    const st = VID.turn ? String(VID.turn.status || '') : null, last = VID.rows[VID.rows.length - 1];
    const working = VID.sending || (st ? st === 'working' || st === 'queued' : !!last && last.role === 'user');
    const label = VID.turn && working && VID.turn.line ? String(VID.turn.line) : 'Reading your words and files…';
    VID.working = working;
    VID.thread.sync({key: VID.chat, working, label, steps: [], messages: threadList()});
    drawChatClips();
    // Hoola could not answer: the same clip can still be made straight away (nothing is spent before the price card)
    const mine = (D.studio?.projects || []).some(p => p.chat === VID.chat && p.created_ts >= (VID.lastSend?.at || 0) - 1);
    const fail = $('#vfail'), failed = !working && !!last && !!st && /fail|error|stuck/.test(st) && !mine;
    if (fail) fail.innerHTML = failed && VID.lastSend ? `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>Hoola could not answer this time.</b><small>You can still make the clip from your words and settings. The price card shows first; nothing is spent before you tap Yes.</small>
      <button class="btn pri" data-vdirect>${I('spark', 'width:15px;height:15px')}Make the clip straight away</button></div></div>` : '';
    markWork(!!working && VIEW === 'video');
    const go = $('#vidGo'); if (go) { go.classList.toggle('stop', working && !VID.sending); go.setAttribute('aria-label', working && !VID.sending ? 'Stop' : 'Send'); go.innerHTML = working && !VID.sending ? I('pause') : I('send'); }
  }
  async function vChat(id) {
    try {
      const c = id ? {id} : await api('GET', '/api/video/chat');
      VID.chat = c.id; VID.title = c.title || 'Video chat'; VID.rows = []; VID.turn = null;
      const t = $('#vcTitle'); if (t) t.textContent = VID.title;
      VID.thread?.clear(); await vLoad(true);
    } catch (e) { const f = $('#vfail'); if (f) f.innerHTML = `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>The video chat could not open.</b><small>${esc(e.message)}</small></div></div>`; }
  }
  async function vSend() {
    const q = $('#vidq'), text = (q?.value || '').trim();
    if (VID.working && !VID.sending && !text) { try { await api('POST', `/api/conversations/${encodeURIComponent(VID.chat)}/stop`); toast('Stopping.'); } catch (e) { toast(e.message, true); } return; }
    if (!text) { q?.focus(); toast('Describe the shot first'); return; }
    if (VID.files.some(f => f.up)) { toast('Wait for the files to finish uploading'); return; }
    if (!VID.chat) await vChat();
    if (!VID.chat) return;
    const files = VID.files.filter(f => f.file_id), say = text, hint = settingsLine();   // read before the tray is emptied
    VID.sending = true; VID.turn = null; VID.lastSend = {brief: text, files: files.map(f => ({...f})), at: Date.now() / 1000};
    VID.thread.her(say, {pending: true, files: files.map(f => f.name)}); keepSent(say, files);
    q.value = ''; VID.prompt = ''; VID.files = []; drawTray(); vPaint();
    try {
      await api('POST', `/api/conversations/${encodeURIComponent(VID.chat)}/messages`, {text: say, files: files.map(f => f.file_id), hints: [hint],
        client_id: 'vc' + Date.now().toString(36) + (++VID.seq).toString(36)});   // no random ids in the studio
      VID.turn = {status: 'queued', line: ''};
    } catch (e) { toast(e.message, true); q.value = VID.prompt = say; VID.files = files; drawTray(); }
    VID.sending = false; await vLoad(false); vChatPoll();
  }
  let vPoll = 0;
  function vChatPoll() {
    clearTimeout(vPoll);
    const tick = async () => { if (VIEW !== 'video') return; await vLoad(false); vPoll = setTimeout(tick, VID.working ? 2000 : 8000); };
    vPoll = setTimeout(tick, VID.working ? 1500 : 8000);
  }

  /* ---- her files: a tray of tiles above the words; any file, 20 at most, 30 MB each ---- */
  function drawTray() {
    const t = $('#vtray'); if (!t) return;
    t.innerHTML = VID.files.map((f, i) => `<div class="vfile ${f.kind}${f.err ? ' err' : ''}" role="listitem" title="${esc(f.name)}">
      <span class="vfk">${esc((f.name.split('.').pop() || 'file').slice(0, 4).toUpperCase())}</span><span class="vfn">${esc(f.name)}</span>
      ${f.kind === 'image' && f.local ? `<img alt="" src="${esc(f.local)}">` : f.kind === 'video' && f.local ? `<video muted playsinline preload="metadata" src="${esc(f.local)}"></video><span class="vfp">${I('play', 'width:14px;height:14px')}</span>` : ''}
      ${f.up ? '<span class="vfu">Uploading…</span>' : f.err ? `<span class="vfu err">${esc(f.err)}</span>` : ''}
      ${f.kind === 'image' && f.file_id ? `<button type="button" class="vff" data-vfirst="${i}" aria-pressed="${!!f.first}" title="Start the clip on this photo">${f.first ? 'First frame' : 'Use as first frame'}</button>` : ''}
      <button type="button" class="vfx" data-vfx="${i}" aria-label="Remove ${esc(f.name)}">${I('x', 'width:11px;height:11px')}</button></div>`).join('');
    t.hidden = !VID.files.length;
    $$('img,video', t).forEach(m => m.addEventListener('error', () => { m.hidden = true; }, {once: true}));   // a picture the browser cannot show: its name stays
  }
  async function addFiles(list) {
    const fs = [...list].slice(0, Math.max(0, 20 - VID.files.length));
    if (list.length > fs.length) toast('Up to 20 files at a time');
    if (!VID.chat) await vChat();
    if (!VID.chat) return;
    for (const file of fs) {
      const f = {name: file.name || 'file', kind: VFILES(file.name || ''), size: file.size, up: true, local: /^(image|video)\//.test(file.type) ? URL.createObjectURL(file) : ''};
      if (f.local) urls.set('vc:' + f.local, f.local);
      if (f.kind === 'image' && !VID.files.some(x => x.first)) f.first = true;
      VID.files.push(f); drawTray();
      if (file.size > 30 * 1024 * 1024) { f.up = false; f.err = 'Over 30 MB'; drawTray(); continue; }
      try { const fd = new FormData(); fd.append('file', file, file.name);
        const r = await api('POST', `/api/conversations/${encodeURIComponent(VID.chat)}/files`, undefined, {form: fd}); f.file_id = r.file_id; }
      catch (e) { f.err = 'Not uploaded'; toast(`${file.name}: ${e.message}`, true); }
      f.up = false; drawTray();
    }
  }

  /* ---- the camera sheet: 26 moves in seven groups, each drawn ---- */
  function camSheet() {
    const sh = $('#camsheet');
    sh.innerHTML = `<div class="csin" role="dialog" aria-modal="true" aria-labelledby="csT"><div class="csh"><div><h2 id="csT">Camera move</h2><p class="mut">Auto lets the model choose. The move rides your words to the video model.</p></div>
      <label class="vsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Find a move</span><input id="csq" type="search" placeholder="Find a move"></label><button class="ib" data-csclose aria-label="Close">${I('x')}</button></div>
      <div class="csb" id="csb">${CAMG.map(([g, ms]) => `<section data-csg><h3>${g}</h3><div class="csg">${ms.map(n => `<button type="button" class="csm" data-vcam="${esc(n)}" aria-pressed="${n === VID.camera}">${camPic(n)}<b>${esc(n)}</b><small>${esc(camLine(n))}</small></button>`).join('')}</div></section>`).join('')}</div></div>`;
    sh.hidden = false; requestAnimationFrame(() => sh.classList.add('on'));
    $('#csq', sh).addEventListener('input', e => { const v = e.target.value.toLowerCase();
      $$('.csm', sh).forEach(b => { b.hidden = !!v && !b.textContent.toLowerCase().includes(v); });
      $$('[data-csg]', sh).forEach(s => { s.hidden = !$$('.csm', s).some(b => !b.hidden); }); });
    sh.onclick = e => { if (e.target === sh || e.target.closest('[data-csclose]')) { camClose(); return; }
      const c = e.target.closest('[data-vcam]'); if (c) { VID.camera = c.dataset.vcam; camClose(); voptsRedraw(); ($('[data-vcamopen]') || $('[data-vset]'))?.focus(); } };
    sh.onkeydown = e => { if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); camClose(); ($('[data-vcamopen]') || $('[data-vset]'))?.focus(); } };
    ($('.csm[aria-pressed="true"]', sh) || $('.csm', sh))?.focus();
  }
  function camClose() { const sh = $('#camsheet'); if (!sh || sh.hidden) return; sh.classList.remove('on'); setTimeout(() => { if (!sh.classList.contains('on')) { sh.hidden = true; sh.innerHTML = ''; } }, 160); }
  function vOpt(b) {
    const k = b.dataset.vopt, m = vm(), set = (fn) => v => { fn(v); voptsRedraw(); };
    if (k === 'shape') return menu(b, [{v: '9:16', label: '9:16', sub: 'Reels, Shorts, Stories', icon: 'grid'}, {v: '16:9', label: '16:9', sub: 'YouTube, websites'}, {v: '1:1', label: '1:1', sub: 'Feed posts'}], VID.aspect, set(v => { VID.aspect = v; }), 'Shape');
    if (k === 'length') menu(b, opt(lenOpts(m), v => v + ' s'), VID.seconds, set(v => { VID.seconds = +v; }), 'Length · longer than 30 s? Use Director');
    if (k === 'res') menu(b, opt(resOpts(m)), VID.res, set(v => { VID.res = v; }), 'Resolution');
    if (k === 'takes') menu(b, [1, 2, 3, 4].map(v => ({v, label: v + ' take' + (v > 1 ? 's' : ''), sub: v > 1 ? 'Pick the best one; each take is paid' : 'One take'})), VID.takes, set(v => { VID.takes = +v; }), 'Takes');
    if (k === 'lang') menu(b, opt(['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi']), VID.language, set(v => { VID.language = v; }), 'Spoken lines in');
  }

  W.video = (el, o) => {
    const q = $('#vidq'); q.addEventListener('input', () => { VID.prompt = q.value; q.style.height = 'auto'; q.style.height = Math.min(180, q.scrollHeight) + 'px'; });
    q.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); vSend(); } });
    q.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    const box = $('#vcomp'), dz = e => { e.preventDefault(); box.classList.toggle('drop', e.type === 'dragover' || e.type === 'dragenter'); };
    ['dragenter', 'dragover', 'dragleave'].forEach(t => $('.vcp', el).addEventListener(t, dz));
    $('.vcp', el).addEventListener('drop', e => { e.preventDefault(); box.classList.remove('drop'); if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files); });
    $('#vq').addEventListener('input', e => { VID.q = e.target.value; drawVideos(); });
    VID.thread = window.HoolaChat ? HoolaChat.mount($('#vthread'), {acts: ['copy'], scroller: $('#vlog'), jump: true}) : null;
    drawTray();
    load('studio').then(() => redraw('video', drawVideos)); watchStudio('video', () => { drawVideos(); if (VID.thread) vPaint(); });
    models().then(() => { if (VIEW === 'video' && VID.model && !vm()) { VID.model = ''; } livePrice(); });
    (VID.chat ? vLoad(true) : vChat()).then(vChatPoll);
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-vset')) { vsetOpen($('#vsetp').hidden); return; }
      if (b.hasAttribute('data-vsdone')) { vsetOpen(false); return; }
      if (b.dataset.vs) { const k = b.dataset.vs, v = b.dataset.vsv; VID[k] = k === 'seconds' || k === 'takes' ? +v : v; voptsRedraw(); return; }
      if (b.hasAttribute('data-vsreset')) { Object.assign(VID, {aspect: '9:16', seconds: 8, res: '1080p', camera: 'Auto', audio: true, takes: 1, language: 'Hindi'}); fitToModel(); voptsRedraw(); return; }
      if (b.dataset.vopt) { vOpt(b); return; }
      if (b.dataset.vfilt) { VID.filter = b.dataset.vfilt; $$('[data-vfilt]').forEach(x => x.setAttribute('aria-selected', String(x === b))); drawVideos(); return; }
      if (b.hasAttribute('data-vplus')) { addFiles(await pick('*/*', true)); return; }
      if (b.dataset.vfx) { const f = VID.files.splice(+b.dataset.vfx, 1)[0]; if (f?.first) { const n = VID.files.find(x => x.kind === 'image' && x.file_id); if (n) n.first = true; } drawTray(); return; }
      if (b.dataset.vfirst) { const i = +b.dataset.vfirst; VID.files.forEach((f, j) => { f.first = j === i ? !f.first : false; }); drawTray(); return; }
      if (b.hasAttribute('data-vcamopen')) { camSheet(); return; }
      if (b.hasAttribute('data-vaudio')) { VID.audio = !VID.audio; voptsRedraw(); return; }
      if (b.hasAttribute('data-vnew')) { try { const c = await api('POST', '/api/video/chat/new'); await vChat(c.id); VID.title = c.title || 'Video chat'; $('#vcTitle').textContent = VID.title; } catch (er) { toast(er.message, true); } return; }
      if (b.hasAttribute('data-vhist')) { let cs = []; try { cs = (await api('GET', '/api/video/chats')).chats || []; } catch (er) { toast(er.message, true); return; }
        if (!cs.length) { toast('No earlier video chats yet'); return; }
        menu(b, cs.map(c => ({v: c.id, label: c.title, sub: c.at ? new Date(c.at.endsWith('Z') || /[+-]\d\d:\d\d$/.test(c.at) ? c.at : c.at + 'Z').toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : ''})), VID.chat,
          async v => { const c = cs.find(x => x.id === v); await vChat(v); VID.title = c?.title || 'Video chat'; $('#vcTitle').textContent = VID.title; }, 'Earlier video chats'); return; }
      if (b.hasAttribute('data-vdirect')) { const s = VID.lastSend; if (!s) return; b.disabled = true; await newClip(false, s); VID.lastSend = null; vPaint(); return; }
      if (b.hasAttribute('data-pickmodel')) { VID.prompt = q.value; picker({current: VID.compare.length ? null : VID.model, seconds: VID.seconds, res: VID.res, title: 'Choose the model for this video',
        auto: VID.auto, onAuto: mode => { VID.auto = mode; },
        onPick: k => { VID.model = k; VID.compare = []; fitToModel(); go('video'); },
        onCompare: keys => { VID.compare = keys.slice(0, 3); VID.model = ''; go('video'); }}); return; }
      if (b.hasAttribute('data-improve')) { if (!q.value.trim()) { q.focus(); return; } b.disabled = true;
        try { const r = await api('POST', '/api/studio/improve', {brief: q.value.trim(), language: VID.language, seconds: VID.seconds}); q.value = VID.prompt = r.brief; } catch (er) { toast(er.message, true); } b.disabled = false; return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await load('studio', true); drawVideos(); return; }
      if (b.dataset.openproj) { clipOpen(b.dataset.openproj); return; }
      if (b.hasAttribute('data-reload')) { await load('studio', true); drawVideos(); vLoad(false); return; }
      if (b.id === 'vidGo') { vSend(); }
    });
    el.addEventListener('pointerdown', e => { const p = $('#vsetp'); if (!p || p.hidden) return;
      if (e.target.closest('#vsetp, [data-vset], #pop, #camsheet')) return; vsetOpen(false); });
    $('#vsetp').addEventListener('keydown', e => { if (e.key === 'Escape' && $('#camsheet').hidden && $('#pop').hidden) { e.preventDefault(); e.stopPropagation(); vsetOpen(false); } });
    if (o.autostart) { VID.prompt = VID.prompt || q.value; if (VID.prompt.trim()) { q.value = VID.prompt; setTimeout(vSend, 300); } }
  };

  /* ---------------- director (a whole film on Video Studio) ---------------- */
  const DIR = {brief: '', project: '', aspect: '16:9', seconds: 45, language: 'Hindi', music: '', busy: '', view: null, model: '', res: '1080p'};
  const STEPS = [['brief', 'Brief'], ['plan', 'Storyboard'], ['cast', 'Cast'], ['keyframes', 'Pictures'], ['preview', 'Preview'], ['generate', 'Shots'], ['music', 'Music'], ['assemble', 'Final film']];
  function stepState(p) {
    const shots = p.shots || [], picked = shots.length && shots.every(s => s.picked);
    const real = shots.length && shots.every(s => s.quality && s.quality !== 'preview');
    return {brief: true, plan: shots.length > 0, cast: (p.character_list || []).length > 0 || !!p.prefs?.cast_skip, keyframes: (shots.length && p.keyframes >= shots.length) || (shots.length > 0 && !!p.prefs?.pics_skip),
      preview: shots.some(s => (s.take_list || []).length), generate: picked && real, music: !!p.music, assemble: (p.outputs || []).some(o => !o.preview)};
  }
  V.director = o => {
    const p = DIR.view;
    if (!DIR.project || !p) return `<div class="dir">
  <div class="dhero"><span class="tag hot">Director agent</span><h1>Brief in, finished film out</h1>
    <form class="compose" id="dirForm" style="width:min(760px,100%)"><label for="dirq" class="sr">Your film brief</label><textarea id="dirq" rows="3" placeholder="A 45-second Diwali ad for Newtika Chai: a family comes home, Dadi makes chai, ends on our logo">${esc(DIR.brief)}</textarea>
      <div class="crow"><button type="button" class="dd" data-dcyc="aspect">${I('grid', 'width:15px;height:15px')}<span>${DIR.aspect}</span></button><button type="button" class="dd" data-dcyc="seconds"><span>${DIR.seconds} s</span></button><button type="button" class="dd" data-dcyc="language"><span>${DIR.language}</span></button><button type="button" class="dd" data-dcyc="music">${I('music', 'width:15px;height:15px')}<span>${DIR.music || 'No music'}</span></button><button type="button" class="dd" data-dnewmodel>${I('spark', 'width:15px;height:15px')}<span>${esc(mOf(DIR.model)?.name || 'Hoola Auto')}</span>${I('down', 'width:14px;height:14px')}</button><button type="button" class="dd" data-dnewres><span>${DIR.res}</span>${I('down', 'width:14px;height:14px')}</button><span class="sp"></span><button class="send" aria-label="Plan the film">${I('send')}</button></div></form>
    <p class="mut" style="max-width:560px">Hoola writes the storyboard for free. Pictures, shots and music each show their price first; nothing is spent until you tap Yes.</p></div>
  ${DIR.busy ? `<div class="box"><b>${esc(DIR.busy)}…</b><div class="bar"><i class="indet"></i></div></div>` : ''}
  <section><div class="sec-h"><h2>Your films</h2><div class="fbar"><label class="fsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search your films</span><input id="fq" type="search" placeholder="Search films" value="${esc(DIR.fq || '')}"></label><button type="button" class="dd" data-fsort><span>${{new: 'Recent first', az: 'Name A–Z', step: 'Furthest along'}[DIR.fsort || 'new']}</span>${I('down', 'width:14px;height:14px')}</button></div></div><div class="films" id="films"></div></section></div>`;
    const st = stepState(p), cur = STEPS.find(([k]) => !st[k])?.[0] || 'done';
    const nx = p.next || {};
    return `<div class="dir">
  <div class="sec-h" style="margin:0;align-items:center"><div style="min-width:0"><button class="lnk" data-dirback>${I('left', 'width:14px;height:14px')} All films</button><h2 style="font:400 26px/1.25 var(--serif);margin-top:4px">${esc(p.project)}</h2><p class="mut" style="margin-top:4px;max-width:760px">${esc((p.brief || '').slice(0, 280))}</p></div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><button class="dd" data-pmodel title="The model for the whole film">${I('spark', 'width:15px;height:15px')}<span>${esc(mOf(p.prefs?.model)?.name || 'Hoola Auto')}</span>${I('down', 'width:14px;height:14px')}</button><button class="dd" data-pres title="Resolution of the shots"><span>${esc(p.prefs?.resolution || 'By quality')}</span>${I('down', 'width:14px;height:14px')}</button>${p.working ? `<button class="btn sec" data-dcancel>${I('x', 'width:15px;height:15px')}Stop</button>` : ''}</div></div>
  ${moneyLine(p.money) ? `<div class="moneybar">${moneyLine(p.money)}</div>` : ''}
  <div class="pipe" role="list">${STEPS.map(([k, t], i) => `<button role="listitem" class="${st[k] ? 'done' : ''}" ${k === cur ? 'aria-current="step"' : ''} data-step="${k}"><i>${st[k] ? '✓' : i + 1}</i>${t}</button>`).join('')}</div>
  <div class="nextc${['wait', 'done'].includes(nx.kind) ? ' quiet' : ''}"><div class="nxt"><small>${nx.kind === 'done' ? 'All steps done' : nx.kind === 'wait' ? 'Working' : 'Next step · ' + (NEXT_STEP[nx.kind] || '')}</small><b>${esc(nextLabel(nx))}</b><p>${NEXT_WHY[nx.kind] || ''}</p></div>
    ${nx.kind === 'done' ? '' : `<button class="create nxb" data-next="${esc(nx.kind || '')}" ${['wait', 'done'].includes(nx.kind) ? 'disabled' : ''}>${I('spark', 'width:17px;height:17px')}<span>${esc(nextLabel(nx))}</span>${nx.inr ? `<small class="num">${inr(nx.inr)}</small>` : nx.kind === 'plan' ? '<small>Free</small>' : ''}</button>`}</div>
  ${(p.approvals || []).length ? `<section class="box"><h3>Waiting for your approval</h3>${p.approvals.map(approvalRow).join('')}</section>` : ''}
  ${p.progress && p.working ? `<div class="box"><div style="display:flex;justify-content:space-between"><b>Making ${p.progress.total} shot${p.progress.total === 1 ? '' : 's'} · ${esc(p.progress.quality || '')}</b><span class="num mut">${p.progress.pct}%${p.progress.eta_s ? ' · about ' + Math.ceil(p.progress.eta_s / 60) + ' min' : ''}</span></div><div class="bar"><i style="width:${p.progress.pct}%"></i></div></div>` : ''}
  ${(p.outputs || []).length ? `<section><div class="sec-h"><h2>Your film</h2></div><div class="outs">${p.outputs.slice().reverse().map(o => `<div class="out"><video controls playsinline preload="metadata" src="${esc(o.url)}"${o.thumb ? ` poster="${esc(o.thumb)}"` : ''}></video><small>${o.preview ? 'Preview' : 'Final'} · ${o.seconds || ''} s · ${o.mb} MB <a href="${esc(o.url)}" download="${esc(o.name || 'hoola-film.mp4')}">Download</a></small></div>`).join('')}</div></section>` : ''}
  <section id="castsec" ${DIR.castOpen || o.cast ? '' : 'hidden'} class="box"><h3>Add a character <button class="ib" data-castclose aria-label="Close">${I('x', 'width:15px;height:15px')}</button></h3>
    <div class="prow2"><label class="fld">Name<input id="cname" maxlength="40" value="${esc(DIR.castDraft?.name || '')}"></label><label class="fld">Voice<select id="cvoice"><option value="female">Female</option><option value="male">Male</option></select></label></div>
    <label class="fld">Looks like<textarea id="cdesc" rows="2" maxlength="400" placeholder="28, warm smile, long black hair in a braid, mustard kurta">${esc(DIR.castDraft?.description || '')}</textarea></label>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button class="btn pri" data-castgo>${I('cast', 'width:15px;height:15px')}Make this character</button><button class="lnk" data-castskip>Skip: no fixed characters in this film</button></div><p class="note">An AI character keeps the same face in every shot. A real person needs their permission (add from the chat with their photo).</p></section>
  <section><div class="sec-h"><h2>Storyboard · ${(p.shots || []).length} shots · ${p.seconds || 0} s</h2><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sec" data-dpreview>${I('play', 'width:14px;height:14px')}Free preview</button><button class="btn sec" data-dmore aria-haspopup="menu">More${I('down', 'width:14px;height:14px')}</button><span hidden><button data-castopen></button><button data-dmusic></button><button data-replan></button></span></div></div>
    ${timeline(p.shots || [])}
    ${p.planning && !(p.shots || []).length ? `<div class="box"><b>Writing the storyboard…</b><div class="bar"><i class="indet"></i></div></div>` : ''}
    ${p.error && !p.planning && !(p.shots || []).length ? `<div class="box casterr" data-planerr>${I('x', 'width:15px;height:15px')}<div><b>${esc(p.error)}</b><small class="mut" style="display:block;margin-top:4px">Nothing was spent. Press Write the storyboard to try again.</small></div></div>` : ''}
    <div class="scenes story">${(() => { let t = 0; return (p.shots || []).map((s, i) => { const a = t; t += +s.duration || 0; return sceneCard(s, i, a); }).join(''); })()}</div></section>
  ${(p.painting || []).length ? `<div class="box castwait"><div><b>Painting ${p.painting.length} opening picture${p.painting.length > 1 ? 's' : ''}…</b><small class="mut">About 20-40 seconds each, three at a time. Each shot then starts from its picture.</small><div class="bar"><i class="indet"></i></div></div></div>` : ''}
  ${p.pics_error && !(p.painting || []).length && !p.prefs?.pics_skip ? `<div class="box casterr">${I('x', 'width:15px;height:15px')}<div><b>${esc(p.pics_error)}</b><div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap">${(p.shots || []).some(x => !x.keyframe) ? '<button class="btn sec" data-picsretry>Try again for the missing pictures</button>' : ''}<button class="lnk" data-picsskip>Skip pictures: make the shots from the words</button></div></div></div>` : ''}
  ${(p.casting || []).length ? `<div class="box castwait"><div><b>Painting ${p.casting.map(esc).join(', ')}'s picture…</b><small class="mut">About 20-40 seconds. The character then stays the same in every shot.</small><div class="bar"><i class="indet"></i></div></div></div>` : ''}
  ${p.cast_error && !(p.casting || []).length && !p.prefs?.cast_skip ? `<div class="box casterr">${I('x', 'width:15px;height:15px')}<div><b>${esc(p.cast_error)}</b><div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap"><button class="btn sec" data-castretry>Try again</button><button class="lnk" data-castskip>Skip: no fixed characters</button></div></div></div>` : ''}
  ${(p.character_list || []).length ? `<section><div class="sec-h"><h2>Cast</h2></div><div class="cast">${p.character_list.map(c => `<div class="actor"><span class="thumb">${art('portrait', c.name)}${c.image ? `<img alt="" src="${esc(c.image)}">` : `<span class="ph-mark" aria-hidden="true">${I('cast')}</span>`}</span><div><b>${esc(c.name)}</b><small>${esc(c.description.slice(0, 80))}</small></div></div>`).join('')}</div></section>` : ''}
</div>`;
  };
  // v0.320 the next step says what happens and what it costs, right under the steps (it sat alone in the top corner)
  const NEXT_STEP = {plan: 'Storyboard', keyframes: 'Pictures', generate: 'Shots', assemble: 'Final film'};
  const NEXT_WHY = {plan: 'Hoola writes the scenes, camera moves and spoken lines. The storyboard is free.',
    keyframes: 'Hoola paints the first frame of every shot, so faces and products stay the same across the film.',
    generate: 'Each shot is filmed from its picture by the best ready model. Pick the take you like on each shot.',
    assemble: 'The picked shots, music and titles are joined into one film you can download.',
    wait: 'Hoola is working on it. This page updates by itself; you can leave and come back.',
    done: 'Your film is below. Change any shot and make it again whenever you like.'};
  const clock = n => { n = Math.round(+n || 0); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`; };
  // v0.320 the film as a timeline: one segment per shot, as long as the shot, numbered; a tap jumps to that shot
  function timeline(shots) {
    if (!shots.length) return '';
    const tot = shots.reduce((a, x) => a + (+x.duration || 0), 0) || 1; let t = 0;
    return `<div class="tl"><div class="tlr" role="list" aria-label="Film timeline">${shots.map((x, i) => { const a = t; t += +x.duration || 0;
      const made = (x.take_list || []).some(k => k.picked) ? ' made' : x.keyframe ? ' pic' : '';
      return `<button role="listitem" class="tls${made}" style="flex:${+x.duration || 1}" data-jump="${esc(x.id)}" title="Scene ${i + 1} · ${clock(a)} to ${clock(t)}"><span>${i + 1}</span></button>`; }).join('')}</div>
      <div class="tlt num"><span>0:00</span><span>${clock(tot / 2)}</span><span>${clock(tot)}</span></div></div>`;
  }
  function nextLabel(n) {
    return {plan: 'Write the storyboard', keyframes: 'Paint the opening pictures', generate: 'Make the shots', assemble: 'Make the final film', wait: 'Working…', done: 'Film ready'}[n.kind] || 'Next';
  }
  // v0.320 a failed shot says what happened in plain words; the machine text (ffmpeg, hex addresses) stays on hover only
  const plainErr = e => /api.?key|unauthori[sz]ed|\b40[13]\b|invalid key/i.test(e) ? 'The video service refused the key. Check Create > Setup > Engines.'
    : /quota|\b429\b|rate.?limit|busy|overloaded/i.test(e) ? 'The video service is busy right now. Try again in a few minutes.'
    : /safety|blocked|policy|moderation/i.test(e) ? 'The video service would not make this shot. Change its words and try again.'
    : /0x[0-9a-f]{4,}|\[[a-z]+ @|traceback|filtergraph|errno|exception/i.test(e) ? 'This shot could not be made. Try again, or change its words.' : e.slice(0, 160);
  function sceneCard(s, i, t0 = 0) {
    const take = (s.take_list || []).find(t => t.picked) || (s.take_list || []).slice(-1)[0];
    const media = take?.url ? `<video controls playsinline preload="metadata" src="${esc(take.url)}"></video>` : s.keyframe ? `<img alt="" src="${esc(s.keyframe)}">` : art('film', s.id);
    const ph = {paint: 'Painting', video: 'Making', queued: 'Queued', lipsync: 'Lip sync', retrying: 'Retrying', failed: 'Failed', done: 'Picked', pictured: 'Picture ready'}[s.phase] || '';
    return `<div class="scene" data-shot="${esc(s.id)}"><div class="one">${media}${['paint', 'video', 'queued', 'lipsync', 'retrying'].includes(s.phase) ? `<span class="ring"></span><span class="pct">${s.pct != null ? s.pct + '%' : ph}</span>` : ''}</div>
      <div class="sb"><b>${i + 1} · ${esc(s.kind)}${ph ? ` <span class="tag${s.phase === 'failed' ? ' hot' : ''}">${ph}</span>` : ''}<span class="sct num">${clock(t0)} – ${clock(t0 + (+s.duration || 0))}</span></b>
        <small class="clamp" data-ptext>${esc(s.prompt)}</small>${take && take.billed_inr != null && take.quality !== 'preview' ? `<small class="moneyl num">${esc(take.model_label || '')} · you pay ${money(take.billed_inr)}${take.est_inr != null && take.est_inr > take.billed_inr + 0.05 ? ` (card ${money(take.est_inr)})` : ''}${take.actual_inr != null ? ` · provider ${money(take.actual_inr)}` : ''}</small>` : ''}${s.dialogue ? `<small>“${esc(s.dialogue)}”</small>` : ''}${s.error ? `<small class="bad clamp" title="${esc(s.error)}">${esc(plainErr(s.error))}</small>` : ''}
        <div class="sm"><span class="tag">${s.duration} s</span><button class="tag mchip" data-smodel="${esc(s.id)}" title="Model for this scene">${esc(s.model_label || 'Auto')} ▾</button>${(s.characters || []).map(c => `<span class="mention">@${esc(c)}</span>`).join('')}<span style="flex:1"></span>
          ${(s.take_list || []).length > 1 ? (s.take_list || []).map(t => `<button class="tk${t.picked ? ' on' : ''}" data-take="${t.n}" aria-label="Use take ${t.n}${t.model_label ? ' by ' + esc(t.model_label) : ''}" title="${esc(t.model_label || '')}">${t.n}${new Set((s.take_list || []).map(x => x.model)).size > 1 && t.model_label ? ' · ' + esc(t.model_label) : ''}</button>`).join('') : ''}
          <button class="ib" aria-label="Edit scene" data-edit>${I('pen', 'width:14px;height:14px')}</button></div></div></div>`;
  }
  async function dirLoad() {
    if (!DIR.project) return;
    try { DIR.view = await api('GET', `/api/studio/projects/${encodeURIComponent(DIR.project)}`); }
    catch (e) { toast(e.message, true); DIR.project = ''; DIR.view = null; }
  }
  function drawFilms() {
    const el = $('#films'); if (!el) return;
    const q = (DIR.fq || '').trim().toLowerCase(), done = p => Object.values(stepState(p)).filter(Boolean).length;
    let ps = (D.studio?.projects || []).filter(p => !q || (p.project + ' ' + (p.brief || '')).toLowerCase().includes(q));
    if (DIR.fsort === 'az') ps = ps.slice().sort((a, b) => a.project.localeCompare(b.project));
    if (DIR.fsort === 'step') ps = ps.slice().sort((a, b) => done(b) - done(a));
    // v0.320 each film says where it is ("Step 4 of 8 · Pictures") and offers Continue; a thin bar alone said nothing
    el.innerHTML = ps.map(p => { const st = stepState(p), i = STEPS.findIndex(([k]) => !st[k]), busy = p.working || p.planning || (p.painting || []).length;
      const where = i < 0 ? 'Film ready' : `Step ${i + 1} of ${STEPS.length} · ${STEPS[i][1]}`;
      return `<button class="fcard" data-openproj="${esc(p.project)}"><span class="one">${projMedia(p)}${busy ? '<span class="fwork">Working</span>' : ''}</span><span class="fb"><b>${esc(p.project)}</b><small class="clamp2">${esc((p.brief || '').slice(0, 140))}</small>
        <span class="fstep"><span class="bar"><i style="width:${Math.round(done(p) / STEPS.length * 100)}%"></i></span><small>${where}</small></span><span class="fgo">${i < 0 ? 'Open' : 'Continue'}${I('down', 'width:14px;height:14px;transform:rotate(-90deg)')}</span></span></button>`; }).join('')
      || (q ? `<p class="mut">No film matches “${esc(DIR.fq)}”.</p>` : `<p class="mut">No films yet. Write a brief above; the storyboard is free.</p>`);
    paintAll(el);
  }
  async function newFilm() {
    const brief = ($('#dirq')?.value || DIR.brief).trim(); if (!brief) { $('#dirq')?.focus(); toast('Write the brief first'); return; }
    DIR.brief = brief; DIR.busy = 'Writing your storyboard (about a minute)'; go('director');
    const name = brief.replace(/[^\p{L}\p{N} ]/gu, ' ').trim().split(/\s+/).slice(0, 5).join(' ').slice(0, 50) || 'My film';
    try {
      const p = await api('POST', '/api/studio/projects', {name, brief, aspect: DIR.aspect, seconds: DIR.seconds, language: DIR.language, music: DIR.music,
        quality: QOF(DIR.res), model: DIR.model, resolution: DIR.res});
      DIR.project = p.project; DIR.view = p; DIR.busy = ''; await load('studio', true);
      // v0.999.34 the storyboard is written in the background: "ready" only when its shots are really there
      toast((p.shots || []).length ? 'Storyboard ready. Check it, then paint the pictures.' : 'Writing your storyboard (about a minute). This page updates by itself.');
    } catch (e) { DIR.busy = ''; toast(e.message, true); }
    if (VIEW === 'director') go('director');
  }
  W.director = async (el, o) => {
    const n = alive;
    if (DIR.project && !DIR.view) { await dirLoad(); if (n !== alive) return; go('director', o); return; }
    if (!DIR.project) { load('studio').then(() => redraw('director', drawFilms));
      $('#fq', el)?.addEventListener('input', e => { DIR.fq = e.target.value; drawFilms(); }); }
    else { const tick = async () => { if (VIEW !== 'director' || !DIR.project) return; await dirLoad(); const p = DIR.view;
        const sig = p ? JSON.stringify(p) : '';
        if (p && sig === DIR.sig) { poll = setTimeout(tick, 5000); return; }        // v0.333 nothing changed: keep the page (and its videos) as it is
        if (p && VIEW === 'director' && !$(':focus', el)?.matches('textarea,input')) { const y = $('#view').scrollTop; go('director'); $('#view').scrollTop = y; }
        else poll = setTimeout(tick, 5000); };
      DIR.sig = DIR.view ? JSON.stringify(DIR.view) : '';
      const p = DIR.view; if (p && (p.working || p.planning || (p.painting || []).length || (p.casting || []).length || (p.approvals || []).length)) poll = setTimeout(tick, 5000); }
    $('#dirForm', el)?.addEventListener('submit', e => { e.preventDefault(); newFilm(); });
    const cyc = {aspect: ['16:9', '9:16', '1:1'], seconds: [15, 30, 45, 60, 90, 120, 180], language: ['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali'], music: ['', 'festive', 'cinematic', 'upbeat', 'calm', 'corporate', 'lofi']};
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      const P = DIR.project ? `/api/studio/projects/${encodeURIComponent(DIR.project)}` : '';
      const act = async (label, fn) => { b.disabled = true; try { const r = await fn(); if (r?.waiting_owner) toast(`Price ${inr(r.inr)}: tap Yes above to start`); else if (label) toast(label); } catch (er) { toast(er.status === 428 ? fp : er.message, true); } await dirLoad(); if (VIEW === 'director') go('director'); };
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
      if (b.hasAttribute('data-dmore')) { menu(b, [{v: 'castopen', label: 'Add a character', sub: 'The same face in every shot'}, {v: 'dmusic', label: 'Add music', sub: 'Google Lyria, the price shows first'},
        {v: 'replan', label: 'Rewrite the storyboard', sub: 'Shots made so far stay in the film'}], '', v => el.querySelector(`[data-${v}]`)?.click(), 'More for this film'); return; }
      if (b.dataset.jump) { const c = el.querySelector(`.scene[data-shot="${CSS.escape(b.dataset.jump)}"]`); if (c) { c.scrollIntoView({behavior: 'smooth', block: 'center'}); c.classList.remove('flash'); void c.offsetWidth; c.classList.add('flash'); } return; }
      if (b.hasAttribute('data-fsort')) { menu(b, [{v: 'new', label: 'Recent first'}, {v: 'az', label: 'Name A–Z'}, {v: 'step', label: 'Furthest along'}], DIR.fsort || 'new',
        v => { DIR.fsort = v; b.querySelector('span').textContent = {new: 'Recent first', az: 'Name A–Z', step: 'Furthest along'}[v]; drawFilms(); }, 'Sort films'); return; }
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
        DIR.lastCast = {name, description}; DIR.castOpen = false; DIR.castDraft = null; return act('', () => api('POST', P + '/characters', {name, description, voice: $('#cvoice').value, kind: 'person'})); }
      // v0.311 a failed picture says why on the page; Try again re-opens the form as she filled it; Skip = no fixed cast
      if (b.hasAttribute('data-castretry')) { DIR.castOpen = true; DIR.castDraft = DIR.lastCast || DIR.view?.cast_last || null; go('director'); $('#cname')?.focus(); return; }
      // v0.312 Pictures: repaint only the missing ones (a new card, only made pictures are charged), or go on without them
      if (b.hasAttribute('data-picsretry')) { const miss = (DIR.view?.shots || []).filter(x => !x.keyframe).map(x => x.id); return act('', () => api('POST', P + '/keyframes', {shot_ids: miss})); }
      if (b.hasAttribute('data-picsskip')) { return act('Going on without opening pictures', () => api('POST', P + '/settings', {pics_skip: true})); }
      if (b.hasAttribute('data-castskip')) { DIR.castOpen = false; DIR.castDraft = null; return act('Going on without a fixed cast', () => api('POST', P + '/settings', {cast_skip: true})); }
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
      l.innerHTML = its.map(it => `<button class="mrow${it.id === SC.id ? ' on' : ''}" data-scopen="${it.id}"><b>${esc(it.title)}</b><small>${when(it.created)}</small></button>`).join('') || '<p class="mut" style="font-size:14px">Scripts you write are kept here.</p>'; }));
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
      if (b.dataset.scopen) { await openScript(b.dataset.scopen); return; }
      if (b.hasAttribute('data-scdl')) { if (SC.id) api('POST', '/api/prompting/runs/event', {ref: SC.id, event: 'downloaded'}).catch(() => {}); const u = URL.createObjectURL(new Blob([SC.text], {type: 'text/plain'})); const a = document.createElement('a'); a.href = u; a.download = 'hoola-script.txt'; R.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 4000); return; }
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
    <section><div class="sec-h"><h2>Your cast</h2><span class="dim" style="font-size:14px">Same face and outfit in every shot</span></div><div class="cast" id="castgrid"></div></section></div></section></div>`;
  function drawCast() {
    const g = $('#castgrid'); if (!g) return;
    const its = items('cast'), jobs = running('cast');
    if (!CA.sel && its[0]) CA.sel = its[0].id;
    g.innerHTML = jobs.map(j => `<div class="actor gening"><span class="thumb">${art('cast', j.id)}<span class="ring"></span><span class="pct">Casting…</span></span><div><b>${esc(j.title.replace('Cast · ', ''))}</b><small>Drawing four views</small></div></div>`).join('')
      + failed('cast').map(j => `<div class="actor"><span class="thumb"><span class="fail">${esc(j.error)}</span></span><div><b>${esc(j.title)}</b><small><button class="lnk" data-seen="${j.id}">Dismiss</button></small></div></div>`).join('')
      + its.map(it => `<button class="actor${it.id === CA.sel ? ' on' : ''}" data-casel="${it.id}"><span class="thumb">${standIn(it)}<img alt="" data-src="${itemPath(it.id)}"></span><div><b>${esc(it.meta?.name || it.title)}</b><small>${esc((it.meta?.description || '').slice(0, 60))}</small></div></button>`).join('')
      || '<p class="mut">No characters yet. Describe one on the left.</p>';
    const s = its.find(x => x.id === CA.sel), d = $('#casel');
    d.innerHTML = s ? `<section class="box" style="padding:16px;gap:12px"><div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><b style="font-size:18px">${esc(s.meta?.name || s.title)}</b>${s.meta?.voice ? `<span class="tag">${esc(s.meta.voice)} voice</span>` : ''}<span style="flex:1"></span>
        <button class="pillbtn" data-castfilm="${s.id}">${I('clap', 'width:15px;height:15px')}Use in a film</button><button class="pillbtn" data-ref="${s.id}">${I('image', 'width:15px;height:15px')}Use in a picture</button><button class="pillbtn" data-dl="${s.id}">${I('dl', 'width:15px;height:15px')}Download</button><button class="ib" data-del="${s.id}" aria-label="Delete">${I('trash', 'width:16px;height:16px')}</button></div>
        <button class="sheetimg thumb" data-open="${s.id}">${standIn(s)}<img alt="Front, three-quarter, side and back views of ${esc(s.meta?.name || '')}" data-src="${itemPath(s.id)}"></button><p class="mut">${esc(s.meta?.description || '')}</p></section>` : '';
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
  /* v0.999.79 HOOLA MUSIC (owner: "WE WILL BUILD OUR OWN SUNO -- FOR MUSIC" -> "MAKE IT FOR GLOBAL ... ALL LANGUAGES" ->
     "ADD AI CHAT TO ALL BOARDS -- SAME LIKE VIDEOS AND IMAGE" -> "START THE BUILD"; canvas claude.ai/artifact/Qq4WmnjktJD7VS9torkejn,
     plan docs/HOOLA_MUSIC_PLAN.md): the Music page is the Image page's twin - its own Hoola chat on the left (/api/music/chat,
     Conversation kind 'music'), the same chat bar (+, ONE settings button, Improve, Send), Song settings above the box (kind,
     language = Auto or any of the world's, singers, style, mood, length, tempo, versions, keep out, lyrics by parts), every
     song set inside the chat with its versions to play, and Your songs on the right. Hoola makes songs with create_studio
     action=song and changes them for free with action=song_edit (a new version each time, the old one kept). */
  const MU = {tab: 'Song', brief: '', genre: '', lang: 'Auto', vox: 'Duet', mood: 'Auto', bpm: 0, len: '2 min', lyrics: '',
    versions: 2, keep: '', files: [], focus: '', chat: '', title: '', thread: null, rows: [], turn: null, sending: false,
    working: false, loading: false, filter: 'all', q: '', lastSend: null, seq: 0, jobs: [], writing: false};
  const GENRES = ['', 'Pop', 'Hip-hop', 'R&B', 'Rock', 'EDM', 'Lo-fi', 'Jazz', 'Country', 'Gospel', 'Reggaeton', 'Latin pop', 'Afrobeats',
    'Amapiano', 'K-pop', 'J-pop', 'Bollywood', 'Bhangra', 'Sufi', 'Arabic pop', 'Bossa nova', 'Flamenco', 'Classical', 'Devotional', 'Kids'];
  const MLANGS = ['Auto', 'English', 'Spanish', 'Portuguese', 'Hindi', 'Arabic', 'French', 'Japanese', 'Korean', 'Chinese (Mandarin)', 'German',
    'Italian', 'Russian', 'Turkish', 'Indonesian', 'Vietnamese', 'Thai', 'Filipino', 'Bengali', 'Tamil', 'Telugu', 'Marathi', 'Punjabi', 'Urdu',
    'Gujarati', 'Kannada', 'Malayalam', 'Hinglish', 'Swahili', 'Yoruba', 'Igbo', 'Hausa', 'Zulu', 'Amharic', 'Persian', 'Hebrew', 'Polish',
    'Dutch', 'Swedish', 'Greek', 'Ukrainian'];
  const CYC = {lang: MLANGS, vox: ['Duet', 'Female', 'Male', 'Group', 'Choir', 'Child'], mood: ['Auto', 'Warm', 'Joyful', 'Romantic', 'Energetic', 'Sad', 'Calm', 'Epic', 'Dreamy', 'Devotional'],
    len: ['30 s', '1 min', '2 min', '3 min']};
  const MKINDS = {Song: 'A song with singing', Instrumental: 'Music only, no singing', Jingle: 'A short catchy tune for a shop or an ad', Score: 'Music for a film, a game or a video'};
  const MTEMPO = [[0, 'Auto'], [76, 'Slow'], [100, 'Medium'], [124, 'Fast']];
  const vocal = () => MU.tab === 'Song';
  const MEACH = 7, MCRED = 80;               // Lyria: about Rs 7 (80 credits) a version - the Create page's own price
  const mCost = () => MEACH * MU.versions;
  const mSecs = () => MU.tab === 'Jingle' && MU.len !== '30 s' ? 30 : ({'30 s': 30, '1 min': 60, '2 min': 120, '3 min': 180}[MU.len] || 120);
  const msum = () => `${MU.tab} · ${MU.lang} · ${MU.versions} version${MU.versions > 1 ? 's' : ''}`;
  const mpriceLine = () => `${MU.versions * MCRED} credits ≈ ${inr(mCost())} · ${MU.versions} version${MU.versions > 1 ? 's' : ''} × ${inr(MEACH)}`;
  function moptsHTML() {
    const open = !$('#msetp')?.hidden;
    return `<button type="button" class="vset" data-mset aria-haspopup="dialog" aria-expanded="${open}" aria-controls="msetp" title="Song settings">${I('sliders', 'width:16px;height:16px')}<span>${esc(msum())}</span>${I(open ? 'up' : 'down', 'width:14px;height:14px')}</button>`
      + `<span class="vmdl imdl" title="Google Lyria makes the songs today; more engines come later">${I('music', 'width:15px;height:15px')}<span>Lyria</span></span>`;
  }
  function msetHTML() {
    const seg = (k, list, cur, fmt) => `<div class="seg vsg" role="radiogroup">${list.map(v => `<button type="button" role="radio" aria-checked="${String(v) === String(cur)}" data-ms="${k}" data-msv="${esc(String(v))}">${fmt ? fmt(v) : esc(String(v))}</button>`).join('')}</div>`;
    const row = (label, body, note) => `<div class="vsr"><span class="vsl">${label}</span><div class="vsc">${body}${note ? `<small>${note}</small>` : ''}</div></div>`;
    const pickb = (k, label) => `<button type="button" class="vsb" data-mpick="${k}"><span>${esc(label)}</span>${I('down', 'width:14px;height:14px')}</button>`;
    return `<div class="vsh0"><b id="msetT">Song settings</b><button type="button" class="lnk" data-msreset>Reset</button></div>`
      + row('Kind', seg('tab', Object.keys(MKINDS), MU.tab), esc(MKINDS[MU.tab]))
      + row('Language', pickb('lang', MU.lang === 'Auto' ? 'Auto · from your words' : MU.lang), MU.lang === 'Auto' ? 'Write in any language; mixed lyrics keep each part’s language' : '')
      + (vocal() ? row('Singers', seg('vox', CYC.vox, MU.vox)) : '')
      + row('Style', `<label class="sr" for="mgenre">Style of music</label><input id="mgenre" class="ivin" list="mgenres" maxlength="60" value="${esc(MU.genre)}" placeholder="Auto, or e.g. Afrobeats, K-pop, jazz, Sufi"><datalist id="mgenres">${GENRES.filter(Boolean).map(g => `<option value="${esc(g)}"></option>`).join('')}</datalist>`)
      + row('Mood', pickb('mood', MU.mood))
      + row('Length', seg('len', CYC.len, MU.len), MU.tab === 'Jingle' ? 'A jingle stays about 30 seconds' : '')
      + row('Tempo', seg('bpm', MTEMPO.map(t => t[0]), MU.bpm, v => esc((MTEMPO.find(t => t[0] === +v) || MTEMPO[0])[1])))
      + row('Versions', seg('versions', [1, 2, 4], MU.versions), MU.versions > 1 ? 'Pick the one you like; each is paid' : '')
      + row('Keep out', `<label class="sr" for="mkeep">Things to keep out of the song</label><input id="mkeep" class="ivin" maxlength="300" value="${esc(MU.keep)}" placeholder="e.g. autotune, heavy drums">`)
      + (vocal() ? row('Lyrics', `<div class="mlyr"><label class="sr" for="mlyrics">Your lyrics</label><textarea id="mlyrics" rows="6" maxlength="3000" placeholder="[Verse 1]\nYour words…\n\n[Chorus]\n…  (leave empty and Hoola writes them)">${esc(MU.lyrics)}</textarea>
          <span class="mlyf"><button type="button" class="lnk" data-write ${MU.writing ? 'disabled' : ''}>${I('pen', 'width:14px;height:14px')} ${MU.writing ? 'Writing…' : 'Write with Hoola'}</button><small>Each part on its own line in [brackets]; sung word for word</small></span></div>`) : '')
      + `<div class="vsf"><span id="msetCost">${esc(mpriceLine())}</span><button type="button" class="vdone" data-msdone>Done</button></div>`;
  }
  function msetOpen(on) {
    const p = $('#msetp'); if (!p) return;
    if (on) { p.innerHTML = msetHTML(); p.hidden = false; requestAnimationFrame(() => p.classList.add('on')); ($('[aria-checked="true"]', p) || $('button', p))?.focus(); }
    else { mReadSet(); p.classList.remove('on'); p.hidden = true; p.innerHTML = ''; }
    const o = $('#mopts'); if (o) o.innerHTML = moptsHTML();
    if (!on) $('[data-mset]')?.focus();
  }
  function mReadSet() {        // the typed fields of the open panel into MU
    const g = $('#mgenre'), k = $('#mkeep'), l = $('#mlyrics');
    if (g) MU.genre = g.value.trim(); if (k) MU.keep = k.value.trim(); if (l) MU.lyrics = l.value;
  }
  function mRedraw() {
    mReadSet();
    const o = $('#mopts'); if (o) o.innerHTML = moptsHTML();
    const p = $('#msetp');
    if (p && !p.hidden) { const f = p.contains(p.getRootNode().activeElement) ? p.getRootNode().activeElement : null;
      const k = f?.dataset?.ms ? `[data-ms="${f.dataset.ms}"][aria-checked="true"]` : '';
      p.innerHTML = msetHTML(); if (k) $(k, p)?.focus(); }
    mPrice();
  }
  // the price under the box: about Rs 7 a version; made when she sends (the Image page's rule)
  function mPrice() {
    const el = $('#mprice'); if (!el) return; const c = D.conf;
    el.innerHTML = `<b class="num">≈ ${inr(mCost())}</b> · <span>${MU.versions * MCRED} credits · ${MU.versions} version${MU.versions > 1 ? 's' : ''} · made when you send · changes to a made song are free</span>`
      + (c?.ready?.song === false ? ` <span class="warnl">${esc(c.need?.song || 'The music engine is not set up on the server. Check Create > Engines.')}</span>` : '');
  }
  V.music = () => `<div class="gen vchat mchat">
  <section class="panel vcp" aria-label="Music chat">
    <div class="vch"><span class="vcm">${I('music', 'width:16px;height:16px')}</span><div class="vct"><b id="mcTitle">${esc(MU.title || 'Music chat')}</b><small>Describe a song in any language, or ask for a change.</small></div>
      <button class="ib" data-mhist aria-label="Earlier music chats" title="Earlier music chats">${I('redo')}</button><button class="ib" data-mnew aria-label="New music chat" title="New music chat">${I('plus')}</button></div>
    <div class="vlog" id="mlog"><div id="mthread"></div><div id="mfail"></div></div>
    <div class="vcomp" id="mcomp">
      <div class="vsetp" id="msetp" role="dialog" aria-labelledby="msetT" hidden></div>
      <div class="vbox" id="mbox">
        <div class="vtray" id="mtray" role="list" aria-label="Files to send"></div>
        <label class="sr" for="muq">Message Hoola about your song</label>
        <textarea id="muq" rows="2" maxlength="4000" placeholder="Describe a song in any language, or ask for a change…">${esc(MU.brief)}</textarea>
        <div class="vrow">
          <button type="button" class="vplus" data-mplus aria-label="Add a recording, lyrics or a file" title="Add a recording, lyrics or a file">${I('plus')}</button>
          <div class="vopts" id="mopts">${moptsHTML()}</div>
          <button type="button" class="ib" data-improve aria-label="Improve my words" title="Improve my words">${I('wand')}</button>
          <button type="button" class="vsend" id="muGo" aria-label="Send">${I('send')}</button>
        </div>
      </div>
      <p class="vfoot" id="mprice"></p>
    </div>
  </section>
  <div class="stage vst"><div class="sbar vsbar"><b>Your songs</b><span class="mut num" id="mcount"></span><span class="sp"></span>
      <div class="vseg" role="tablist" aria-label="Show">${[['all', 'All'], ['mk', 'Making'], ['ok', 'Ready']].map(([k, t]) => `<button type="button" role="tab" data-mfilt="${k}" aria-selected="${MU.filter === k}">${t}<i class="num" data-mn="${k}"></i></button>`).join('')}</div>
      <label class="vsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search your songs</span><input id="msq" type="search" placeholder="Search" value="${esc(MU.q)}"></label>
      <button class="ib" data-reload aria-label="Refresh">${I('redo', 'width:16px;height:16px')}</button></div>
    <div class="pbody" id="tracks" style="padding:14px"></div></div></div>`;
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
  /* ---- Your songs on the right: making / ready, search, each with Change and Download ---- */
  const mRunning = () => { const seen = new Set(), out = []; for (const j of [...MU.jobs, ...D.jobs.values()]) { if (j.kind !== 'song' || j.status !== 'running' || seen.has(j.id)) continue; seen.add(j.id); out.push(j); } return out; };
  function mTrack(it) {
    const m = it.meta || {}, tag = m.parent ? `<span class="mver">Edited</span>` : m.version ? `<span class="mver">${esc(m.version)}</span>` : '';
    return trackHTML(it).replace('<b>', `<b>${tag}`).replace('<button class="ib" data-dl=', `<button class="ib" data-mchange="${esc(it.id)}" aria-label="Change ${esc(it.title)} in the chat" title="Change it in the chat">${I('pen', 'width:16px;height:16px')}</button><button class="ib" data-dl=`);
  }
  function drawSongs() {
    const el = $('#tracks'); if (!el || VIEW !== 'music') return;
    const all = items('song'), run = mRunning(), q = (MU.q || '').toLowerCase();
    const cnt = {all: all.length + run.length, mk: run.length, ok: all.length};
    $$('[data-mn]').forEach(n => { const v = cnt[n.dataset.mn]; n.textContent = n.dataset.mn !== 'all' && v ? ' · ' + v : ''; });
    const c = $('#mcount'); if (c) c.textContent = all.length ? String(all.length) : '';
    const hit = it => !q || [it.title, it.meta?.genre, it.meta?.language, it.meta?.lyrics, it.meta?.brief].join(' ').toLowerCase().includes(q);
    const mk = MU.filter === 'ok' ? '' : run.filter(j => !q || (j.title || '').toLowerCase().includes(q)).map(trackJob).join('');
    const ready = MU.filter === 'mk' ? '' : all.filter(hit).map(mTrack).join('');
    el.innerHTML = mk + failed(['song']).map(j => `<div class="track"><div class="tt"><b>${esc(j.title)}</b><small class="bad">${esc(j.error)}</small></div><button class="lnk" data-seen="${j.id}">Dismiss</button></div>`).join('') + ready
      || (all.length || run.length ? `<div class="empty"><div><h2>Nothing here</h2><p class="mut">No song matches this filter.</p></div></div>`
        : `<div class="empty"><div><h2>Your songs appear here</h2><p class="mut">Describe a song in the chat, in any language, and send.</p></div></div>`);
    paintAll(el); hydrate(el);
    mDrawSets();
  }
  /* ---- a song set in the chat: composing, its versions to play (or the edited version), or could not be made ---- */
  function mSets() {
    const sets = new Map();
    for (const it of (D.items || [])) { const m = it.meta || {}; if (it.kind !== 'song' || !MU.chat || m.chat !== MU.chat) continue;
      const k = m.job || it.id, s = sets.get(k) || {id: k, created: it.created, items: [], inr: 0, edit: m.edit || '', parent: m.parent || ''};
      s.items.push(it); s.created = Math.min(s.created, it.created); s.inr += m.inr || 0; sets.set(k, s); }
    for (const j of MU.jobs) { if (j.kind !== 'song' || !MU.chat || j.conv !== MU.chat || sets.has(j.id) || j.status === 'done') continue;
      sets.set(j.id, {id: j.id, created: j.created, items: [], job: j}); }
    sets.forEach(s => s.items.sort((a, b) => String(a.meta?.version || '').localeCompare(String(b.meta?.version || ''))));
    return [...sets.values()].sort((a, b) => a.created - b.created);
  }
  function mChatSet(s) {
    const j = s.job;
    if (j && j.status === 'running') { const n = j.count || 1;
      return `<div class="mscard gening"><div class="isf"><span class="stchip mk">Composing ${n} version${n > 1 ? 's' : ''}${j.step ? ' · ' + esc(j.step) : ''}</span><small class="mut">About a minute a version · ${esc(inr(MEACH * n))}</small></div>
        <span class="bar"><i class="indet"></i></span></div>`; }
    if (j) return `<div class="mscard"><div class="isf"><span class="stchip na">Could not be made</span><small class="mut">${esc(j.error || 'It did not work this time. Try again in a minute.')}</small></div></div>`;
    const from = s.parent ? (D.items || []).find(x => x.id === s.parent) : null;
    const first = s.items[0];
    const label = s.parent ? `Changed: ${esc(s.edit)}${from ? ' · from ' + esc(from.title) : ''} · free` : `${s.items.length} version${s.items.length > 1 ? 's' : ''}${s.inr ? ' · ' + esc(inr(s.inr)) : ''}`;
    return `<div class="mscard"><div class="msl">${s.items.map(mTrack).join('')}</div>
      <div class="isf"><span class="stchip ok">Ready</span><small class="mut">${label}</small><span class="sp"></span>
        <button class="btn sec" data-mask="Make a 30 second reel cut of ${esc(first.title)}: start on the chorus and fade out the end">${I('cut', 'width:14px;height:14px')}Reel cut</button>
        <button class="btn sec" data-mask="Fade out the last 3 seconds of ${esc(first.title)}">Fade the end</button>
        ${s.parent ? '' : `<button class="btn sec" data-mmore="${esc(first.id)}">${I('redo', 'width:14px;height:14px')}More like this</button>`}</div></div>`;
  }
  function mDrawSets() {
    const sets = new Map(mSets().map(s => [s.id, s]));
    $$('[data-mset-id]').forEach(n => { const s = sets.get(n.dataset.msetId); if (!s) return; const h = mChatSet(s); if (n._h === h) return; n._h = h; n.innerHTML = h; paintAll(n); hydrate(n); });
  }
  /* ---- the chat ---- */
  function mThreadList() {
    const msgs = MU.rows.map(r => { const t = r.role === 'user' ? stripNotes(r.text) : String(r.text || '');
      return {id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: t, at: atOf(r.at)}; });
    const after = new Map();       // a set sits after the reply of the turn that made it (or after her message when none)
    for (const s of mSets()) { let i = -1; msgs.forEach((m, j) => { if (m.at <= s.created + 1) i = j; });
      if (i >= 0 && msgs[i].role === 'her' && msgs[i + 1]?.role === 'hoola') i++;
      (after.get(i) || after.set(i, []).get(i)).push(s); }
    const raw = s => ({id: 'mset:' + s.id, role: 'raw', html: `<div class="iset" data-mset-id="${esc(s.id)}"></div>`});
    const out = [...(after.get(-1) || []).map(raw)];
    msgs.forEach((m, j) => { out.push(m); (after.get(j) || []).forEach(s => out.push(raw(s))); });
    return out;
  }
  async function mJobs() {
    const before = new Set(MU.jobs.filter(j => j.status === 'running').map(j => j.id));
    try { MU.jobs = (await api('GET', '/api/create/jobs')).jobs || []; } catch { return; }
    if (MU.jobs.some(j => before.has(j.id) && j.status !== 'running')) await load('items', true);
  }
  async function mLoad(first) {
    if (!MU.chat || MU.loading || !MU.thread) return;
    const chat = MU.chat; MU.loading = true;
    try {
      const last = MU.rows[MU.rows.length - 1];
      if (MU.sending || MU.working || (last && last.role === 'user') || first) {
        try { MU.turn = await api('GET', `/api/conversations/${encodeURIComponent(chat)}/result`); } catch {}
      }
      let rows; try { rows = (await api('GET', `/api/conversations/${encodeURIComponent(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      const had = (D.items || []).length; await mJobs();
      if (chat !== MU.chat) return;
      MU.rows = rows; mPaint(); if ((D.items || []).length !== had || first) drawSongs(); else mDrawSets();
    } finally { MU.loading = false; }
  }
  function mPaint() {
    if (!MU.thread || VIEW !== 'music') return;
    const st = MU.turn ? String(MU.turn.status || '') : null, last = MU.rows[MU.rows.length - 1];
    const working = MU.sending || (st ? st === 'working' || st === 'queued' : !!last && last.role === 'user');
    const label = MU.turn && working && MU.turn.line ? String(MU.turn.line) : 'Listening to your words…';
    MU.working = working;
    MU.thread.sync({key: MU.chat, working, label, steps: [], messages: mThreadList()});
    mDrawSets();
    // Hoola could not answer: the same song can still be made straight away
    const mine = mSets().some(s => s.created >= (MU.lastSend?.at || 0) - 1);
    const fail = $('#mfail'), bad = !working && !!last && !!st && /fail|error|stuck/.test(st) && !mine;
    if (fail) fail.innerHTML = bad && MU.lastSend && !MU.lastSend.edit ? `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>Hoola could not answer this time.</b><small>You can still make the song from your words and settings: ${esc(inr(MEACH * MU.lastSend.versions))} for ${MU.lastSend.versions} version${MU.lastSend.versions > 1 ? 's' : ''}.</small>
      <button class="btn pri" data-mdirect>${I('music', 'width:15px;height:15px')}Make the song straight away</button></div></div>` : '';
    markWork(!!working && VIEW === 'music');
    const go = $('#muGo'); if (go) { go.classList.toggle('stop', working && !MU.sending); go.setAttribute('aria-label', working && !MU.sending ? 'Stop' : 'Send'); go.innerHTML = working && !MU.sending ? I('pause') : I('send'); }
  }
  async function mChat(id) {
    try {
      const c = id ? {id} : await api('GET', '/api/music/chat');
      MU.chat = c.id; MU.rows = []; MU.turn = null; if (c.title) MU.title = c.title;
      const t = $('#mcTitle'); if (t) t.textContent = MU.title || 'Music chat';
      MU.thread?.clear(); await mLoad(true);
    } catch (e) { const f = $('#mfail'); if (f) f.innerHTML = `<div class="vfailc">${I('x', 'width:15px;height:15px')}<div><b>The music chat could not open.</b><small>${esc(e.message)}</small></div></div>`; }
  }
  // what she picked in Song settings, said to Hoola beside her words (her bubble shows only her words). Square brackets and
  // new lines cannot ride the note, so her lyrics' part names go as {Verse 1} and lines are split by " / ".
  function mHint() {
    mReadSet();
    const clean = t => String(t).replace(/\[/g, '{').replace(/\]/g, '}').replace(/\n+/g, ' / ');
    const lang = MU.lang === 'Auto' ? 'Auto (the language of her words or lyrics)' : MU.lang;
    const tempo = MU.bpm ? `about ${MU.bpm} BPM` : 'auto';
    const lyr = vocal() && MU.lyrics.trim() ? `, her lyrics word for word (part names in braces are part tags, " / " starts a new line): ${clean(MU.lyrics.trim()).slice(0, 2800)}` : '';
    const focus = MU.focus ? `, the song she means: id ${MU.focus}` : '';
    return `Song settings: kind ${MU.tab}, language ${lang}${vocal() ? ', singers ' + MU.vox.toLowerCase() : ', no singing'}, style ${clean(MU.genre) || 'auto (you choose from her words)'}, mood ${MU.mood === 'Auto' ? 'auto' : MU.mood.toLowerCase()}, about ${mSecs()} seconds, tempo ${tempo}, ${MU.versions} version${MU.versions > 1 ? 's' : ''}`
      + (MU.keep ? `, keep out: ${clean(MU.keep)}` : '') + lyr + focus + '. A new song = create_studio action=song; a change to a song made here = create_studio action=song_edit.';
  }
  async function mSend(textIn) {
    const q = $('#muq'), text = (textIn || q?.value || '').trim();
    if (MU.working && !MU.sending && !text) { try { await api('POST', `/api/conversations/${encodeURIComponent(MU.chat)}/stop`); toast('Stopping.'); } catch (e) { toast(e.message, true); } return; }
    if (!text) { q?.focus(); toast('Describe the song first'); return; }
    if (MU.files.some(f => f.up)) { toast('Wait for the files to finish uploading'); return; }
    load('conf').then(mPrice);
    if (!MU.chat) await mChat();
    if (!MU.chat) return;
    const files = MU.files.filter(f => f.file_id), hint = mHint();
    MU.sending = true; MU.turn = null;
    MU.lastSend = {brief: text, at: Date.now() / 1000, versions: MU.versions, edit: !!textIn || !!MU.focus, tab: MU.tab, lang: MU.lang, vox: MU.vox,
      genre: MU.genre, mood: MU.mood, bpm: MU.bpm, secs: mSecs(), keep: MU.keep, lyrics: vocal() ? MU.lyrics : ''};
    MU.thread.her(text, {pending: true, files: files.map(f => f.name)});
    if (!textIn) { q.value = ''; MU.brief = ''; }
    MU.files = []; MU.focus = ''; mTray(); mPaint();
    try {
      await api('POST', `/api/conversations/${encodeURIComponent(MU.chat)}/messages`, {text, files: files.map(f => f.file_id), hints: [hint],
        client_id: 'mc' + Date.now().toString(36) + (++MU.seq).toString(36)});
      MU.turn = {status: 'queued', line: ''};
    } catch (e) { toast(e.message, true); if (!textIn) { q.value = MU.brief = text; } MU.files = files; mTray(); }
    MU.sending = false; await mLoad(false); mChatPoll();
  }
  let mPoll = 0;
  function mChatPoll() {
    clearTimeout(mPoll);
    const busy = () => MU.working || mRunning().length;
    const tick = async () => { if (VIEW !== 'music') return; await mLoad(false); mPoll = setTimeout(tick, busy() ? 2000 : 8000); };
    mPoll = setTimeout(tick, busy() ? 1500 : 8000);
  }
  // a song made without a chat turn: "More like this" and "Make the song straight away" (her tap; the price is on the line)
  async function mMake(p) {
    const c = await load('conf');
    if (c?.ready?.song === false) { toast(c.need?.song || 'The music engine is not set up on the server.', true); return; }
    if (!MU.chat) await mChat();
    try {
      const j = await api('POST', '/api/create/jobs', {kind: 'song', conversation_id: MU.chat || '', ...p});
      MU.jobs = [j, ...MU.jobs.filter(x => x.id !== j.id)]; drawSongs(); mPaint(); mChatPoll();
      toast(`Making ${p.versions} version${p.versions > 1 ? 's' : ''} · ${inr(MEACH * p.versions)}`);
    } catch (e) { toast(e.message, true); }
  }
  function mBody(s) {
    const genre = s.tab === 'Jingle' ? ('Jingle' + (s.genre ? ', ' + s.genre : '')) : s.tab === 'Score' ? ('Film score' + (s.genre ? ', ' + s.genre : '')) : s.genre;
    return {brief: s.brief.slice(0, 1200), genre: (genre || '').slice(0, 60), language: s.lang, vocals: s.tab === 'Song' ? s.vox.toLowerCase() : 'none',
      mood: s.mood === 'Auto' ? '' : s.mood, bpm: s.bpm || 0, seconds: s.secs, lyrics: (s.lyrics || '').slice(0, 3000), keep_out: s.keep || '',
      versions: s.versions, title: s.brief.slice(0, 48)};
  }
  function mMore(id) {
    const it = (D.items || []).find(x => x.id === id); if (!it) return; const m = it.meta || {};
    const n = m.job ? (D.items || []).filter(x => x.meta?.job === m.job).length : 1;
    mMake({brief: (m.brief || it.title).slice(0, 1200), genre: (m.genre || '').slice(0, 60), language: m.language || 'Auto', vocals: m.vocals || 'duet', mood: m.mood || '',
      bpm: m.bpm || 0, seconds: m.asked_seconds || 0, lyrics: (m.lyrics || '').slice(0, 3000), keep_out: m.keep_out || '', versions: Math.max(1, Math.min(4, n)), title: it.title.replace(/ · [A-D]$/, '').slice(0, 48)});
  }
  /* ---- her recordings and files: a tray of tiles above the words; 10 at most, 30 MB each ---- */
  function mTray() {
    const t = $('#mtray'); if (!t) return;
    t.innerHTML = MU.files.map((f, i) => `<div class="vfile ${f.kind}${f.err ? ' err' : ''}" role="listitem" title="${esc(f.name)}">
      <span class="vfk">${esc((f.name.split('.').pop() || 'file').slice(0, 4).toUpperCase())}</span><span class="vfn">${esc(f.name)}</span>
      ${f.up ? '<span class="vfu">Uploading…</span>' : f.err ? `<span class="vfu err">${esc(f.err)}</span>` : ''}
      <button type="button" class="vfx" data-mfx="${i}" aria-label="Remove ${esc(f.name)}">${I('x', 'width:11px;height:11px')}</button></div>`).join('');
    t.hidden = !MU.files.length;
  }
  async function mAddFiles(list) {
    const fs = [...list].slice(0, Math.max(0, 10 - MU.files.length));
    if (list.length > fs.length) toast('Up to 10 files at a time');
    if (!MU.chat) await mChat();
    if (!MU.chat) return;
    for (const file of fs) {
      const f = {name: file.name || 'file', kind: VFILES(file.name || ''), size: file.size, up: true};
      MU.files.push(f); mTray();
      if (file.size > 30 * 1024 * 1024) { f.up = false; f.err = 'Over 30 MB'; mTray(); continue; }
      try { const fd = new FormData(); fd.append('file', file, file.name);
        const r = await api('POST', `/api/conversations/${encodeURIComponent(MU.chat)}/files`, undefined, {form: fd}); f.file_id = r.file_id; }
      catch (e) { f.err = 'Not uploaded'; toast(`${file.name}: ${e.message}`, true); }
      f.up = false; mTray();
    }
  }
  W.music = (el, o) => {
    const q = $('#muq'); q.addEventListener('input', () => { MU.brief = q.value; q.style.height = 'auto'; q.style.height = Math.min(180, q.scrollHeight) + 'px'; });
    q.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); mSend(); } });
    q.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); mAddFiles(fs); } });
    const box = $('#mcomp'), dz = e => { e.preventDefault(); box.classList.toggle('drop', e.type === 'dragover' || e.type === 'dragenter'); };
    ['dragenter', 'dragover', 'dragleave'].forEach(t => $('.vcp', el).addEventListener(t, dz));
    $('.vcp', el).addEventListener('drop', e => { e.preventDefault(); box.classList.remove('drop'); if (e.dataTransfer?.files?.length) mAddFiles(e.dataTransfer.files); });
    $('#msq').addEventListener('input', e => { MU.q = e.target.value; drawSongs(); });
    el.addEventListener('input', e => { if (e.target.id === 'mkeep') MU.keep = e.target.value; if (e.target.id === 'mgenre') MU.genre = e.target.value; if (e.target.id === 'mlyrics') MU.lyrics = e.target.value; });
    MU.thread = window.HoolaChat ? HoolaChat.mount($('#mthread'), {acts: ['copy'], scroller: $('#mlog'), jump: true}) : null;
    mTray(); mPrice();
    load('conf').then(mPrice);
    load('items').then(() => redraw('music', drawSongs));
    (MU.chat ? mLoad(true) : mChat()).then(mChatPoll);
    el.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-play')) { playToggle(b); return; }
      if (b.hasAttribute('data-mset')) { msetOpen($('#msetp').hidden); return; }
      if (b.hasAttribute('data-msdone')) { msetOpen(false); return; }
      if (b.dataset.ms) { const k = b.dataset.ms, v = b.dataset.msv; MU[k] = (k === 'versions' || k === 'bpm') ? +v : v; mRedraw(); return; }
      if (b.dataset.mpick) { const k = b.dataset.mpick;
        menu(b, opt(CYC[k], v => v === 'Auto' && k === 'lang' ? 'Auto · from your words' : v), MU[k], v => { MU[k] = v; mRedraw(); }, k === 'lang' ? 'Language of the song' : 'Mood'); return; }
      if (b.hasAttribute('data-msreset')) { Object.assign(MU, {tab: 'Song', lang: 'Auto', vox: 'Duet', genre: '', mood: 'Auto', len: '2 min', bpm: 0, versions: 2, keep: '', lyrics: ''}); mRedraw(); return; }
      if (b.dataset.mfilt) { MU.filter = b.dataset.mfilt; $$('[data-mfilt]').forEach(x => x.setAttribute('aria-selected', String(x === b))); drawSongs(); return; }
      if (b.hasAttribute('data-mplus')) { mAddFiles(await pick('audio/*,video/*,.txt,.pdf,.docx', true)); return; }
      if (b.dataset.mfx) { MU.files.splice(+b.dataset.mfx, 1); mTray(); return; }
      if (b.hasAttribute('data-mnew')) { try { const c = await api('POST', '/api/music/chat/new'); MU.title = c.title || 'Music chat'; await mChat(c.id); } catch (er) { toast(er.message, true); } return; }
      if (b.hasAttribute('data-mhist')) { let cs = []; try { cs = (await api('GET', '/api/music/chats')).chats || []; } catch (er) { toast(er.message, true); return; }
        if (!cs.length) { toast('No earlier music chats yet'); return; }
        menu(b, cs.map(c => ({v: c.id, label: c.title, sub: c.at ? new Date(c.at.endsWith('Z') || /[+-]\d\d:\d\d$/.test(c.at) ? c.at : c.at + 'Z').toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : ''})), MU.chat,
          async v => { const c = cs.find(x => x.id === v); MU.title = c?.title || 'Music chat'; await mChat(v); }, 'Earlier music chats'); return; }
      if (b.hasAttribute('data-mdirect')) { b.disabled = true; const s = MU.lastSend; MU.lastSend = null; if (s) await mMake(mBody(s)); mPaint(); return; }
      if (b.dataset.mmore) { mMore(b.dataset.mmore); return; }
      if (b.dataset.mask) { mSend(b.dataset.mask); return; }
      if (b.dataset.mchange) { const it = (D.items || []).find(x => x.id === b.dataset.mchange); MU.focus = b.dataset.mchange;
        q.value = MU.brief = `Change "${it ? it.title : 'this song'}": `; q.focus(); toast('Say the change and send - it is free'); return; }
      if (b.hasAttribute('data-write')) { const idea = q.value.trim(); if (idea.length < 4) { q.focus(); toast('Describe the song first, then Hoola writes the words'); return; }
        mReadSet(); MU.writing = true; mRedraw();
        try { const r = await api('POST', '/api/create/write', {kind: 'lyrics', brief: idea, genre: MU.genre, language: MU.lang === 'Auto' ? 'the language of these words' : MU.lang, mood: MU.mood === 'Auto' ? '' : MU.mood}); MU.lyrics = r.text; } catch (er) { toast(er.message, true); }
        MU.writing = false; mRedraw(); return; }
      if (b.hasAttribute('data-improve')) {
        if (!q.value.trim()) { q.focus(); toast('Write a few words first'); return; }
        if (window.HoolaImprove && window.HoolaImprove.ui) {
          window.HoolaImprove.ui.open(q.value, {section: 'music', onUse: t => { q.value = MU.brief = String(t).slice(0, 4000); q.focus(); toast('Words updated: edit them or send'); }}); return; }
        return; }
      if (await itemAction(b)) return;
      if (b.dataset.seen) { const j = D.jobs.get(b.dataset.seen); if (j) j.seen = true; drawSongs(); return; }
      if (b.hasAttribute('data-reload')) { await load('items', true); await mJobs(); drawSongs(); mLoad(false); return; }
      if (b.id === 'muGo') mSend();
    });
    el.addEventListener('pointerdown', e => { const p = $('#msetp'); if (!p || p.hidden) return;
      if (e.target.closest('#msetp, [data-mset], #pop')) return; msetOpen(false); });
    $('#msetp').addEventListener('keydown', e => { if (e.key === 'Escape' && $('#pop').hidden) { e.preventDefault(); e.stopPropagation(); msetOpen(false); } });
    if (o.autostart) { MU.brief = MU.brief || q.value; if (MU.brief.trim()) { q.value = MU.brief; setTimeout(() => mSend(), 300); } }
  };

  /* ---------------- voice ---------------- */
  const VO = {text: '', voice: 'mine', g: 'all', style: 'friendly', speed: 1, lang: 'Hindi'};
  V.voice = () => { const vs = D.conf?.voices || {male: {}, female: {}};
    const list = [['mine', 'Your Hoola’s voice', 'The voice your Hoola speaks with on calls', 'voice'],
      ...(VO.g !== 'male' ? Object.entries(vs.female).map(([n, d]) => [n, n, 'Female · ' + d, 'portrait']) : []),
      ...(VO.g !== 'female' ? Object.entries(vs.male).map(([n, d]) => [n, n, 'Male · ' + d, 'portrait']) : [])];
    return `<div class="gen"><div class="panel"><div class="pbody">
    <div class="box"><h3>Script <span class="dim num" style="font-size:12.5px;font-weight:400" id="voCount">${VO.text.length} / 5000</span></h3>
      <textarea id="voq" rows="6" maxlength="5000" placeholder="This Diwali, light up your home. With Newtika chai, every evening is special.">${esc(VO.text)}</textarea></div>
    <div class="lbl">Language</div><div class="chips">${['Hindi', 'Hinglish', 'English', 'Marathi', 'Tamil', 'Telugu', 'Bengali', 'Gujarati', 'Kannada', 'Malayalam', 'Punjabi'].map(l => `<button class="chip" aria-pressed="${l === VO.lang}" data-volang="${l}">${l}</button>`).join('')}</div>
    <div class="lbl">Voice</div><div class="seg"><button aria-pressed="${VO.g === 'all'}" data-vog="all">All</button><button aria-pressed="${VO.g === 'female'}" data-vog="female">Female</button><button aria-pressed="${VO.g === 'male'}" data-vog="male">Male</button></div>
    <div class="vlist">${list.map(([k, n, d, a]) => `<button class="opt" role="radio" aria-checked="${k === VO.voice}" data-vo="${esc(k)}"><span class="thumb">${k === 'mine' ? art(a, 'vo' + k) : initTile(n)}</span><div><b>${esc(n)}</b><small>${esc(d)}</small></div></button>`).join('')}</div>
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
  const DUB_TOP = ['Hindi', 'Tamil', 'Telugu', 'Bengali', 'Marathi', 'English'];
  V.dubbing = () => `<div class="split"><aside>
    <button class="refs" data-dubsrc>${DB.src ? `<span class="stack"><i>${I('video', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>${esc(DB.src.name)}</b><small>${(DB.src.size / 1048576).toFixed(1)} MB · tap to change</small></div>` : `<span class="stack"><i>${I('upload', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>Upload your video</b><small>MP4 / MOV / WebM · up to 25 MB and 3 minutes</small></div>`}</button>
    ${DB.src ? `<video class="srcv" controls playsinline src="${esc(DB.src.local)}"></video>` : ''}
    <div class="lbl">Dub into <span class="dim num" id="dubn" style="margin-left:auto">${DB.to.length} of 4 picked</span></div><div class="langs">${LANGS.filter(l => DUB_TOP.includes(l)).map(l => `<button class="chip" aria-pressed="${DB.to.includes(l)}" data-lang="${l}">${l}</button>`).join('')}</div>
    <details class="adv"${DB.to.some(l => !DUB_TOP.includes(l)) ? ' open' : ''}><summary>${I('down', 'width:14px;height:14px')}All languages</summary><div class="langs">${LANGS.filter(l => !DUB_TOP.includes(l)).map(l => `<button class="chip" aria-pressed="${DB.to.includes(l)}" data-lang="${l}">${l}</button>`).join('')}</div></details>
    <div class="prow"><div><b style="white-space:normal">Keep music and background sound</b><small>The original plays softly under the new voices</small></div><button class="sw" role="switch" aria-checked="${DB.keep}" data-dkeep aria-label="Keep music and background sound"><i></i></button></div>
    <button class="create" style="flex:none" id="dubGo">${I('dub', 'width:17px;height:17px')}Dub now</button>
    <p class="note">Hoola listens once, writes each line in the new language and speaks it in a voice matched to each speaker. Voices are matched, not cloned; lips are not re-synced (lip sync is a paid Video Studio step).</p>
    <div class="lbl">Your dubs</div><div class="mini" id="dublist"></div>
  </aside><section><div style="padding:16px;display:flex;flex-direction:column;gap:14px" id="dubview"></div></section></div>`;
  function drawDub() {
    const l = $('#dublist'), v = $('#dubview'); if (!l) return;
    const its = items('dub');
    l.innerHTML = its.map(it => `<button class="mrow${it.id === DB.sel ? ' on' : ''}" data-dubsel="${it.id}"><b>${esc(it.title)}</b><small>${when(it.created)}</small></button>`).join('') || '<p class="mut" style="font-size:14px">Your dubbed videos are kept here.</p>';
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
        $$('[data-lang]').forEach(x => x.setAttribute('aria-pressed', String(DB.to.includes(x.dataset.lang)))); const n = $('#dubn'); if (n) n.textContent = DB.to.length + ' of 4 picked'; return; }
      if (b.hasAttribute('data-dkeep')) { DB.keep = !DB.keep; b.setAttribute('aria-checked', String(DB.keep)); return; }
      if (b.dataset.dubsel) { DB.sel = b.dataset.dubsel; drawDub(); return; }
      if (b.id === 'dubGo') { if (!DB.src) { toast('Upload your video first'); return; } if (!DB.to.length) { toast('Pick a language'); return; }
        DB.sel = ''; try { await startJob({kind: 'dub', file_id: DB.src.file_id, languages: DB.to, keep_sound: DB.keep, title: DB.src.name.replace(/\.[^.]+$/, '').slice(0, 40) + ' · ' + DB.to.join(', ')}, refresh); } catch (er) { toast(er.message, true); } }
    });
  };

  /* ---------------- video editor (her clips, edited by words) ---------------- */
  const ED_STATUS = {queued: 'Waiting in line', watching: 'Watching your clips', planning: 'Planning the edit', rendering: 'Rendering', checking: 'Checking the result'};
  const ED = {clips: [], brief: '', platform: 'reel', length: '', captions: true, job: '', jobs: null, platforms: null};
  const edPlats = () => ED.platforms || [{id: 'reel', label: 'Instagram Reel'}];
  const edPlat = () => edPlats().find(p => p.id === ED.platform) || edPlats()[0];
  V.editor = () => { const j = ED.jobs?.find(x => x.id === ED.job), lt = j?.latest;
    return `<div class="ed">
  <div class="bin"><div class="sec-h" style="margin:0"><h2 style="font-size:14px">Your clips</h2><button class="ib" aria-label="Add clips" data-addclip>${I('upload', 'width:16px;height:16px')}</button></div>
    ${ED.clips.length ? ED.clips.map((c, i) => `<div class="clipcard"><span class="thumb">${c.type.startsWith('image/') ? `<img alt="" src="${esc(c.local)}">` : c.type.startsWith('video/') ? `<video muted preload="metadata" src="${esc(c.local)}"></video>` : I('music', 'width:22px;height:22px;margin:auto')}</span><div><b>${i + 1}. ${esc(c.name)}</b><small>${(c.size / 1048576).toFixed(1)} MB</small></div>
      <span class="ord"><button class="ib" data-mv="${i}|-1" aria-label="Move up" ${i ? '' : 'disabled'}>${I('send', 'width:13px;height:13px')}</button><button class="ib" data-rm="${i}" aria-label="Remove">${I('x', 'width:13px;height:13px')}</button></span></div>`).join('')
      : `<button class="refs" data-addclip><span class="stack"><i>${I('upload', 'width:16px;height:16px;margin:10px 6px')}</i></span><div><b>Add your clips</b><small>Videos, photos, music · up to 8 · 25 MB each</small></div></button>`}
    <div class="lbl">Recent edits</div><div class="mini" id="edjobs"></div></div>
  <div class="viewer"><div class="screen"><div class="frame">${lt?.url ? `<video controls playsinline src="${esc(lt.url)}"></video>` : j && j.status !== 'failed' ? `<div class="framemsg"><span class="ring"></span><b>${esc(ED_STATUS[j.status] || 'Working')}</b><small>${j.progress || 0}%</small></div>` : (ED.clips.length ? `<div class="framemsg">${I('cut', 'width:30px;height:30px')}<b>Your edit plays here</b><small>Say what you want below, then press Make the edit</small></div>` : `<button type="button" class="framemsg drop" data-addclip>${I('upload', 'width:30px;height:30px')}<b>Drop videos, photos or music here</b><small>or tap to choose · up to 8 · 25 MB each</small></button>`)}</div></div>
    ${j?.error ? `<p class="bad" style="padding:0 16px">${esc(j.error)}</p>` : ''}
    <form class="ask" id="edAsk">${I('spark', 'width:16px;height:16px;color:var(--pri)')}<input id="edq" maxlength="1500" placeholder="${lt ? 'Change it: make the intro shorter, add Hindi captions, slower music…' : 'Say what to make: a 30 s reel, fast cuts on the beat, captions in Hindi…'}" aria-label="Tell Hoola what to change" value="${esc(lt ? '' : ED.brief)}"><button class="send" style="width:32px;height:32px" aria-label="${lt ? 'Change' : 'Make the edit'}">${I('send', 'width:16px;height:16px')}</button></form></div>
  <div class="insp"><h3>Made for</h3><button class="prow" id="edplat" type="button" aria-haspopup="menu"><span class="pi">${I('grid', 'width:16px;height:16px')}</span><div><small>Where it goes</small><b>${esc(edPlat().label)}${edPlat().aspect ? ' · ' + esc(edPlat().aspect) : ''}</b></div>${I('down', 'width:14px;height:14px;margin-left:auto')}</button>
    <h3>Length</h3><div class="grid-opts four">${['', '15', '30', '60'].map(s => `<button class="go" aria-pressed="${s === ED.length}" data-edlen="${s}">${s ? s + ' s' : 'Auto'}</button>`).join('')}</div>
    <div class="prow"><div><b>Captions</b><small>Words on screen</small></div><button class="sw" role="switch" aria-checked="${ED.captions}" data-edcap aria-label="Captions"><i></i></button></div>
    <h3>Quick asks</h3><div class="aitools">${[['Cut the silences', 'cut'], ['Hindi captions', 'text'], ['Make it 9:16', 'grid'], ['Beat-synced cuts', 'music'], ['Brighter colours', 'wand'], ['Shorter intro', 'minus']].map(([t, ic]) => `<button data-ai="${t}">${I(ic, 'width:14px;height:14px')}${t}</button>`).join('')}</div>
    <button class="create" style="flex:none" id="edGo" ${ED.clips.length ? '' : 'disabled'}>${I('cut', 'width:16px;height:16px')}${ED.clips.length ? 'Make the edit' : 'Add clips to start'}</button>
    ${lt ? `<a class="btn sec" href="${esc(lt.url)}" download="${esc(lt.name || 'hoola-edit.mp4')}">${I('dl', 'width:16px;height:16px')}Download v${lt.n}</a>` : ''}
    ${j?.post_caption ? `<h3>Post caption</h3><p class="mut" style="font-size:14px">${esc(j.post_caption)}</p>` : ''}</div>
  <div class="timeline"><div class="tlbar"><span>Story order</span><span style="flex:1"></span><span class="num">${ED.clips.length} clip${ED.clips.length === 1 ? '' : 's'}${j?.versions?.length ? ' · ' + j.versions.length + ' version' + (j.versions.length > 1 ? 's' : '') : ''}</span></div>
    <div class="strip">${ED.clips.map((c, i) => `<span class="sclip" style="flex:${c.type.startsWith('video/') ? 3 : 1}"><b>${i + 1}</b>${esc(c.name)}</span>`).join('') || '<span class="mut" style="padding:10px">Clips play in this order. Move them up or down on the left.</span>'}</div>
    ${j?.versions?.length > 1 ? `<div class="vers">${j.versions.map(v => `<span class="tag">v${v.n}</span>`).join('')}</div>` : ''}</div></div>`; };
  function drawEdJobs() {
    const el = $('#edjobs'); if (!el) return;
    el.innerHTML = (ED.jobs || []).slice(0, 8).map(j => `<button class="mrow${j.id === ED.job ? ' on' : ''}" data-edjob="${esc(j.id)}"><b>${esc(j.title || j.brief || 'Edit')}</b><small>${esc(j.platform_label || '')} · ${esc(j.status)}</small></button>`).join('') || '<p class="mut" style="font-size:14px">Your edits are kept here.</p>';
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
    // v0.999.42 the studio's own drawn picker (it was the browser's plain dropdown, unlike every other picker in Create)
    $('#edplat').addEventListener('click', e => { const b = e.currentTarget;
      menu(b, edPlats().map(p => ({v: p.id, label: p.label, sub: p.aspect || ''})), edPlat().id, v => { ED.platform = v; b.querySelector('b').textContent = edPlat().label + (edPlat().aspect ? ' · ' + edPlat().aspect : ''); }, 'Made for'); });
    // v0.325 drop files straight onto the player
    const drop = $('.framemsg.drop', el);
    if (drop) { drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); }); drop.addEventListener('dragleave', () => drop.classList.remove('over'));
      drop.addEventListener('drop', async e => { e.preventDefault(); drop.classList.remove('over');
        const fs = [...(e.dataTransfer?.files || [])].filter(f => /^(video|image|audio)\//.test(f.type)).slice(0, 8 - ED.clips.length);
        for (const f of fs) { try { toast('Uploading ' + f.name); ED.clips.push(await upload(f)); } catch (er) { toast(er.message, true); } } if (fs.length) go('editor'); }); }
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
    <section><div class="sec-h"><h2>Starters</h2></div><div class="qs">${STARTERS.map((s, i) => [s, i]).filter(([s]) => TCAT[tplCat](s)).map(([[t, v, k], i]) => `<button class="tpl" data-start="${i}"><span class="thumb">${art(k, 'tt' + i)}<span class="use">Use this</span></span><b>${t}</b><small>${TITLE[v]}</small></button>`).join('')}</div></section>
    <section><div class="sec-h"><h2>Films with the Director</h2></div><div class="qs">${QUICK.map(([t, k, d], i) => `<button class="qcard" data-quick="${i}"><span class="thumb">${art(k, 'tq' + i)}<span class="dur">${d}</span></span><b>${t}</b></button>`).join('')}</div></section></div>`;
  W.templates = el => el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.cat) { tplCat = b.dataset.cat; go('templates'); }
    if (b.dataset.start) starter(+b.dataset.start);
    if (b.dataset.quick) { const q = QUICK[+b.dataset.quick]; DIR.brief = q[3]; DIR.project = ''; DIR.view = null; go('director', {focus: true}); } });
  let libF = 'all';
  let libQ = '', libSort = 'new';
  const LIBS = {new: 'Newest first', old: 'Oldest first', az: 'Name A–Z'};
  const LIBF = [['all', 'All'], ['image', 'Pictures'], ['cast', 'Cast'], ['song', 'Songs'], ['voice', 'Voice-overs'], ['dub', 'Dubs'], ['script', 'Scripts'], ['film', 'Films']];
  V.library = () => `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 26px/1.2 var(--serif)">My creations</h2><span class="dim" style="font-size:14px">Kept until you delete them</span></div>
    <div class="libbar"><div class="chips">${LIBF.map(([k, n]) => `<button class="chip" aria-pressed="${k === libF}" data-lib="${k}">${n}</button>`).join('')}</div>
      <span class="sp"></span><label class="lsearch">${I('search', 'width:15px;height:15px')}<span class="sr">Search my creations</span><input id="libq" type="search" placeholder="Search" value="${esc(libQ)}"></label>
      <button type="button" class="dd" id="libSort" aria-label="Sort">${I('layers', 'width:15px;height:15px')}<span>${LIBS[libSort]}</span>${I('down', 'width:14px;height:14px')}</button></div>
    <div class="selbar" id="selbar" hidden></div>
    <div class="sgrid lib" id="results"></div></div>`;
  function drawLib() {
    const el = $('#results'); if (!el) return;
    const q = libQ.trim().toLowerCase(), hit = t => !q || String(t || '').toLowerCase().includes(q);   // v0.304 search + sort, in the browser
    const order = (L, t, k) => L.sort((a, b) => libSort === 'az' ? String(t(a)).localeCompare(String(t(b))) : libSort === 'old' ? k(a) - k(b) : k(b) - k(a));
    const its = order((libF === 'film' ? [] : items(libF === 'all' ? '' : libF).filter(i => i.kind !== 'script' || libF === 'script' || libF === 'all')).filter(i => hit(i.title)), i => i.title, i => i.created || 0);
    const films = order(((libF === 'all' || libF === 'film') ? (D.studio?.projects || []).filter(p => (p.outputs || []).length) : []).filter(p => hit(p.title || p.name)), p => p.title || p.name, p => p.updated || p.created || 0);
    el.innerHTML = films.map(projTile).join('') + its.map(it => itemTile(it)).join('')
      || (q ? `<div class="empty" style="grid-column:1/-1"><div><h2>Nothing matches “${esc(libQ)}”</h2><p class="mut">Try another word, or clear the search.</p></div></div>` : '') || `<div class="empty" style="grid-column:1/-1"><div><h2>Nothing here yet</h2><p class="mut">Pictures, songs, voice-overs, dubs, scripts and films you make in Create are kept here.</p></div></div>`;
    // v0.327 every tile can be ticked; a bar appears with Download / Delete for all of them at once
    $$('.res[data-item]', el).forEach(t => { const id = t.dataset.item; if ($('.pick', t)) return;
      t.insertAdjacentHTML('afterbegin', `<button type="button" class="pick" data-pick="${esc(id)}" aria-pressed="${LSEL.has(id)}" aria-label="Select">${I('check', 'width:14px;height:14px')}</button>`); });
    selBar(); paintAll(el); hydrate(el);
  }
  const LSEL = new Set();
  function selBar() { const bar = $('#selbar'); if (!bar) return; const n = [...LSEL].filter(id => (D.items || []).some(x => x.id === id)).length;
    bar.hidden = !n; if (n) bar.innerHTML = `<b class="num">${n} selected</b><span class="sp"></span><button class="btn sec" data-seldl>${I('dl', 'width:15px;height:15px')}Download</button><button class="btn sec danger" data-seldel>${I('trash', 'width:15px;height:15px')}Delete</button><button class="ib" data-selclear aria-label="Clear the selection">${I('x', 'width:16px;height:16px')}</button>`; }
  W.library = el => {
    Promise.all([load('items'), load('studio')]).then(() => redraw('library', drawLib));
    $('#libq', el).addEventListener('input', e => { libQ = e.target.value; drawLib(); });
    $('#libSort', el).addEventListener('click', e => menu(e.currentTarget, Object.entries(LIBS).map(([v, label]) => ({v, label})), libSort,
      v => { libSort = v; $('#libSort span').textContent = LIBS[v]; drawLib(); }, 'Sort by'));
    el.addEventListener('click', async e => { const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.pick) { const id = b.dataset.pick; LSEL.has(id) ? LSEL.delete(id) : LSEL.add(id); b.setAttribute('aria-pressed', String(LSEL.has(id))); b.closest('.res')?.classList.toggle('picked', LSEL.has(id)); selBar(); return; }
      if (b.hasAttribute('data-selclear')) { LSEL.clear(); drawLib(); return; }
      if (b.hasAttribute('data-seldl')) { for (const id of LSEL) { const it = (D.items || []).find(x => x.id === id); if (it) download(itemPath(id), it.title + '.' + (it.mime.split('/')[1] || 'bin').replace('mpeg', 'mp3').replace('x-wav', 'wav')); } return; }
      if (b.hasAttribute('data-seldel')) { const ids = [...LSEL].filter(id => (D.items || []).some(x => x.id === id));
        if (!ids.length || !confirm(`Delete ${ids.length} item${ids.length > 1 ? 's' : ''}? This cannot be undone.`)) return; b.disabled = true; let gone = 0;
        for (const id of ids) { try { await api('DELETE', itemPath(id)); D.items = D.items.filter(x => x.id !== id); LSEL.delete(id); gone++; } catch (er) { toast(er.message, true); } }
        toast(`Deleted ${gone}`); drawLib(); return; }
      if (b.dataset.lib) { libF = b.dataset.lib; $$('[data-lib]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); drawLib(); return; }
      if (b.dataset.scopen) { await openScript(b.dataset.scopen); return; }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await load('studio', true); drawLib(); return; }
      await itemAction(b); });
  };
  /* ---------------- v0.308 ENGINES: the real AI services behind Create, checked live; keys never come to the browser ---------------- */
  const OWNER = () => !!ctx.owner?.();     // v0.327 the console tells the studio when the viewer is the owner
  const EST = {ready: ['Ready', 'ok'], unchecked: ['Key set', 'ok'], missing: ['No key', 'off'], refused: ['Key refused', 'bad'], unreachable: ['Not reachable', 'bad']};
  V.engines = () => `<div class="home eng">
    <div class="sec-h" style="margin:0"><div><h2 style="font:400 26px/1.2 var(--serif)">${OWNER() ? 'Engines' : 'What you can make'}</h2><p class="mut" style="margin-top:6px">${OWNER() ? 'The real AI services behind Create. Keys live only on your server (the .env), never in the app or the chat.' : 'Everything ticked is ready to use in Create right now.'}</p></div>
      <button class="btn sec" data-recheck>${I('redo', 'width:15px;height:15px')}Check again</button></div>
    ${OWNER() ? '<section class="box scbox" id="scbox"><p class="mut">Reading the showcase…</p></section>' : ''}
    <div id="engs"><p class="mut">Checking each engine…</p></div></div>`;
  // v0.329 the owner's showcase panel: the hidden "Hoola showcase" film's two normal price cards, right here
  function drawShowcase(o) {
    const el = $('#scbox'); if (!el) return;
    if (!o) { el.innerHTML = '<p class="mut">Could not read the showcase just now.</p>'; return; }
    const head = `<div class="sch"><h3>Showcase: real Hoola-made pictures and clips</h3><p class="mut">They replace the drawn pictures on Studio home, Templates, the Image styles and the guides, for everyone who uses Create. Made once with your own engines; each step shows its price card first and nothing is made until you tap Yes.</p></div>`;
    if (!o.set_up) { el.innerHTML = head + `<div><button class="btn pri" data-sc="setup">${I('spark', 'width:15px;height:15px')}Set up the showcase (free)</button></div>`; return; }
    const pend = (o.approvals || []).map(approvalRow).join(''), pp = Math.round(o.pictures_made / o.slots * 100), cp = Math.round(o.clips_made / o.clips * 100);
    el.innerHTML = head + `<div class="scrow"><div><b>Pictures</b><small class="num">${o.pictures_made} of ${o.slots} made · about ${inr(o.picture_inr)} each</small><span class="bar"><i style="width:${pp}%"></i></span></div>
        ${o.pictures_made < o.slots ? `<button class="btn sec" data-sc="pictures" ${(o.painting || []).length || pend ? 'disabled' : ''}>Make the ${o.slots - o.pictures_made} missing pictures</button>` : '<span class="stchip ok">All made</span>'}</div>
      <div class="scrow"><div><b>Clips</b><small class="num">${o.clips_made} of ${o.clips} made · 5 seconds each, they play on the film cards</small><span class="bar"><i style="width:${cp}%"></i></span></div>
        ${o.clips_made < o.clips ? `<button class="btn sec" data-sc="clips" ${o.working || pend || o.pictures_made < o.slots ? 'disabled' : ''} title="${o.pictures_made < o.slots ? 'Make the pictures first: each clip starts from its picture' : ''}">Make the ${o.clips - o.clips_made} clips</button>` : '<span class="stchip ok">All made</span>'}</div>
      ${(o.painting || []).length ? `<div class="box castwait"><div><b>Painting ${o.painting.length} picture${o.painting.length > 1 ? 's' : ''}…</b><small class="mut">About 20-40 seconds each, three at a time. This page updates by itself.</small><div class="bar"><i class="indet"></i></div></div></div>` : ''}
      ${o.working ? `<div class="box castwait"><div><b>Making the clips…</b><small class="mut">A few minutes. This page updates by itself.</small><div class="bar"><i class="indet"></i></div></div></div>` : ''}
      ${o.pics_error ? `<p class="perr">${esc(o.pics_error)}</p>` : ''}${o.error && !o.working ? `<p class="perr">${esc(o.error)}</p>` : ''}
      ${pend ? `<div class="scpend"><b>Waiting for your approval</b>${pend}</div>` : ''}`;
  }
  function drawEngines(r) {
    const el = $('#engs'); if (!el) return;
    if (!r) { el.innerHTML = '<p class="mut">Could not check the engines just now.</p>'; return; }
    el.innerHTML = `<div class="eg-feats">${r.features.map(f => `<span class="eg-feat ${f.ready ? 'eg-on' : ''}" title="${esc(f.why || 'Ready')}">${I(f.ready ? 'check' : 'x', 'width:13px;height:13px')}${esc(f.name)}</span>`).join('')}</div>
      <p class="dim" style="font-size:12.5px;margin:10px 0 2px">Checked ${when(r.checked_at).replace('Just now', 'just now')} with free calls only (a key or model list), never a paid job.${r.ffmpeg ? '' : ' ffmpeg is missing on the server: dubbing and the editor need it.'}</p>
      ${OWNER() ? '' : '<!-- engines: owner only -->'}<div class="eg-list"${OWNER() ? '' : ' hidden'}>${r.engines.map(e => { const [label, tone] = EST[e.state] || [e.state, 'off'], good = tone === 'ok';
        return `<div class="eg-card eg-${tone}"><div class="eg-h"><b>${esc(e.name)}</b><span class="eg-st eg-${tone}">${label}</span></div>
          <p class="mut eg-d">${esc(e.detail)}</p>
          <div class="eg-p">${e.powers.map(p => `<span>${esc(p)}</span>`).join('')}</div>
          <p class="dim eg-c">${esc(e.cost)}${e.need ? '' : ' · optional'}</p>
          ${good ? '' : `<details class="eg-how"><summary>${I('down', 'width:14px;height:14px')}How to switch it on</summary><ol>
            <li>Get a key: <a href="${esc(e.get)}" target="_blank" rel="noopener noreferrer">${esc(e.get.replace(/^https:\/\//, ''))}</a></li>
            <li>On the VPS, add one line to <code>~/apps/santosh-core/.env</code>: <code>${esc(e.env[0])}=your-key</code></li>
            <li>Restart: <code>pm2 restart santosh --update-env</code></li>
            <li>Press <b>Check again</b> (or run the VPS ops job <code>studio_apis</code>).</li></ol>
            <p class="dim" style="font-size:12.5px">Never paste a key into the chat. If one was ever shared, make a new one and delete the old.</p></details>`}</div>`; }).join('')}</div>`;
  }
  W.engines = el => {
    const sc = async () => { if (!OWNER() || VIEW !== 'engines') return; let o = null;
      try { const r = await api('GET', '/api/studio/showcase'); o = r.owner; D.showcase = {slots: r.slots}; } catch {}
      drawShowcase(o); clearTimeout(poll);
      if (o && ((o.painting || []).length || o.working || (o.approvals || []).length)) poll = setTimeout(sc, 5000); };
    sc();
    el.addEventListener('click', async e => { const b = e.target.closest('button'); if (!b || !b.closest('#scbox')) return;
      if (b.dataset.sc) { b.disabled = true;
        try { const r = await api('POST', '/api/studio/showcase/' + b.dataset.sc);
          if (r?.waiting_owner) toast(`Price ${inr(r.inr)}: tap Yes on the card below to start`); else if (b.dataset.sc === 'setup') toast('Showcase film set up. Nothing was made or charged.'); }
        catch (er) { toast(er.message, true); } await sc(); return; }
      if (b.dataset.yes || b.dataset.no) { b.disabled = true; await decide(b.dataset.yes || b.dataset.no, !!b.dataset.yes); await sc(); }
    });
    const run = async fresh => { try { drawEngines(await api('GET', '/api/studio/apis' + (fresh ? '?fresh=1' : ''))); } catch (e) { drawEngines(null); toast(e.message, true); } };
    run(false);
    el.addEventListener('click', async e => { const b = e.target.closest('[data-recheck]'); if (!b) return; b.disabled = true; $('#engs').style.opacity = '.55'; await run(true); $('#engs').style.opacity = ''; b.disabled = false; });
  };
  V.projects = () => `<div class="home"><div class="sec-h" style="margin:0"><h2 style="font:400 26px/1.2 var(--serif)">Film projects</h2><button class="btn pri" data-newfilm>${I('plus', 'width:16px;height:16px')}New film</button></div><div class="scenes" id="films"></div></div>`;
  W.projects = el => { load('studio', true).then(() => redraw('projects', drawFilms));
    el.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-newfilm')) { DIR.project = ''; DIR.view = null; go('director', {focus: true}); }
      if (b.dataset.openproj) { DIR.project = b.dataset.openproj; DIR.view = null; go('director'); } }); };
  // v0.327 BRAND KIT: her logo uploaded right here, real colour pickers with names, the font shown in her own tagline,
  // phone + website, and a LIVE preview (a poster and a reel end card) that changes as she types. Saved with one button.
  const BK_ROLES = [['primary', 'Main colour'], ['accent', 'Highlight'], ['dark', 'Dark text'], ['light', 'Light background']];
  const BK_FAM = {poppins: "'Poppins', var(--sans)", mukta: "'Mukta', var(--sans)"};
  const BK = {d: null, logo: ''};
  const lum = h => { const m = /^#?([0-9a-f]{6})$/i.exec(h || ''); if (!m) return 1; const n = parseInt(m[1], 16);
    return [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }).reduce((a, v, i) => a + v * [.2126, .7152, .0722][i], 0); };
  const onCol = (bg, d, l) => { const x = lum(bg), cr = c => { const y = lum(c); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); }; return cr(d) >= cr(l) ? d : l; };
  function bkDraft() { const k = D.kit || {};
    return BK.d || (BK.d = {name: k.name || '', tagline: k.tagline || '', tone: k.tone || '', font: k.font || 'poppins', colors: {...(k.colors || {})},
      phone: k.contact?.phone || '', website: k.contact?.website || ''}); }
  function bkPreview() { const d = bkDraft(), c = d.colors, p = c.primary || '#1565C0', a = c.accent || '#F5A623', dk = c.dark || '#111111', lt = c.light || '#FFFFFF';
    const tp = onCol(p, dk, lt), ta = onCol(a, dk, lt), fam = BK_FAM[d.font] || 'var(--sans)', name = esc(d.name || 'Your business'), tag = esc(d.tagline || 'Your tagline here');
    const logo = BK.logo ? `<img alt="" src="${esc(BK.logo)}">` : `<i>${esc((d.name || 'H').trim()[0] || 'H')}</i>`;
    return `<div class="bkph"><b>Live preview</b><small>Changes as you type. Saved only when you press Save.</small></div>
      <div class="bkpv"><div class="bkposter" style="background:${p};color:${tp};font-family:${fam}"><div class="bkp-top"><span class="bkp-logo">${logo}</span><b>${name}</b></div>
        <div class="bkp-mid"><small>Festive offer</small><h4>${tag}</h4></div><span class="bkp-cta" style="background:${a};color:${ta}">Order now</span>
        <small class="bkp-foot">${esc([d.phone, d.website].filter(Boolean).join(' · ') || 'Phone · website')}</small></div>
      <div class="bkend" style="background:${dk};color:${onCol(dk, dk, lt)};font-family:${fam}"><span class="bkp-logo">${logo}</span><b>${name}</b><small>${tag}</small><i style="background:${a}"></i></div></div>
      <small class="dim">Poster and reel end card, in your colours and font${d.font === 'mukta' ? ' (Mukta also writes Hindi and Marathi)' : ''}.</small>`; }
  V.brand = () => { const k = D.kit; if (!k) return `<div class="home"><p class="mut">Loading your brand kit…</p></div>`;
    const d = bkDraft(), c = d.colors;
    return `<div class="home bk"><div class="sec-h" style="margin:0"><div><h2 style="font:400 26px/1.2 var(--serif)">Brand kit</h2><p class="mut" style="margin-top:6px">Pictures, posters and films use it with one switch; the Brand tool in chat uses it everywhere.</p></div>
      <button class="btn pri" data-bksave>${I('check', 'width:16px;height:16px')}Save</button></div>
    <div class="bkgrid"><div class="bkform">
      <section class="box"><h3>Logo</h3><div class="bklogo"><span class="bklimg" id="bkLogo">${BK.logo ? `<img alt="Your logo" src="${esc(BK.logo)}">` : I('image', 'width:22px;height:22px')}</span>
        <div><b>${k.logo ? 'Your logo' : 'No logo yet'}</b><small>PNG, JPG, WebP or SVG, up to 15 MB. Hoola reads its colours.</small>
          <div class="bkbtns"><button class="btn sec" data-bklogo>${I('upload', 'width:15px;height:15px')}${k.logo ? 'Replace logo' : 'Upload logo'}</button><label class="bkchk"><input type="checkbox" id="bkclean"> Remove a plain background</label></div></div></div></section>
      <section class="box"><h3>Name and words</h3>
        <label class="fld">Business name<input id="bkname" maxlength="120" value="${esc(d.name)}" placeholder="Newtika Chai"></label>
        <label class="fld">Tagline<input id="bktag" maxlength="160" value="${esc(d.tagline)}" placeholder="Every evening, special"></label>
        <label class="fld">Tone<input id="bktone" maxlength="200" value="${esc(d.tone)}" placeholder="Warm, simple Hinglish"></label>
        <div class="prow2"><label class="fld">Phone<input id="bkphone" maxlength="40" inputmode="tel" value="${esc(d.phone)}" placeholder="98xxxxxx10"></label><label class="fld">Website<input id="bkweb" maxlength="140" value="${esc(d.website)}" placeholder="newtika.in"></label></div></section>
      <section class="box"><h3>Colours</h3><div class="bkcols">${BK_ROLES.map(([r, n]) => `<label class="bkcol"><input type="color" id="bkc-${r}" value="${esc((c[r] || '#888888').toLowerCase())}" aria-label="${n}"><span><b>${n}</b><small class="num" id="bkh-${r}">${esc((c[r] || '').toUpperCase())}</small></span></label>`).join('')}</div></section>
      <section class="box"><h3>Font</h3><div class="bkfonts">${Object.entries(k.fonts || {}).map(([f, l]) => `<button type="button" class="bkfont" aria-pressed="${f === d.font}" data-bkfont="${esc(f)}"><span style="font-family:${BK_FAM[f] || 'var(--sans)'}">${esc(d.tagline || d.name || 'Every evening, special')}</span><small>${esc(l)}</small></button>`).join('')}</div></section>
    </div><aside class="bkprev" id="bkPrev">${bkPreview()}</aside></div></div>`; };
  W.brand = el => {
    if (!D.kit) { load('kit').then(() => { if (VIEW === 'brand') go('brand'); }); return; }
    const redrawPrev = () => { const pv = $('#bkPrev'); if (pv) pv.innerHTML = bkPreview(); };
    if (D.kit.logo && !BK.logo) blobURL('/api/brand/logo?t=' + (D.kit.updated || 0)).then(u => { BK.logo = u; const L = $('#bkLogo'); if (L) L.innerHTML = `<img alt="Your logo" src="${esc(u)}">`; redrawPrev(); }).catch(() => {});
    const d = bkDraft();
    for (const [id, k] of [['bkname', 'name'], ['bktag', 'tagline'], ['bktone', 'tone'], ['bkphone', 'phone'], ['bkweb', 'website']])
      $('#' + id, el).addEventListener('input', e => { d[k] = e.target.value; redrawPrev(); });
    for (const [r] of BK_ROLES) $('#bkc-' + r, el).addEventListener('input', e => { d.colors[r] = e.target.value.toUpperCase(); $('#bkh-' + r).textContent = d.colors[r]; redrawPrev(); });
    el.addEventListener('click', async e => { const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.bkfont) { d.font = b.dataset.bkfont; $$('[data-bkfont]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); redrawPrev(); return; }
      if (b.hasAttribute('data-bklogo')) { const [f] = await pick('image/png,image/jpeg,image/webp,image/svg+xml'); if (!f) return;
        if (f.size > 15 * 1024 * 1024) { toast('The logo is bigger than 15 MB', true); return; }
        b.disabled = true; const fd = new FormData(); fd.append('file', f, f.name); fd.append('clean_bg', String(!!$('#bkclean')?.checked));
        try { const r = await api('POST', '/api/brand/logo', undefined, {form: fd}); D.kit = r.kit; BK.d = null; BK.logo = URL.createObjectURL(f); toast('Logo saved. Colours read from it.'); go('brand'); }
        catch (er) { toast(er.message, true); b.disabled = false; } return; }
      if (b.hasAttribute('data-bksave')) { b.disabled = true;
        try { D.kit = await api('PUT', '/api/brand/kit', {name: d.name.trim(), tagline: d.tagline.trim(), tone: d.tone.trim(), font: d.font,
            colors: Object.fromEntries(BK_ROLES.map(([r]) => [r, d.colors[r]]).filter(([, v]) => v)), contact: {phone: d.phone.trim(), website: d.website.trim()}});
          BK.d = null; toast('Brand kit saved'); go('brand'); } catch (er) { toast(er.message, true); b.disabled = false; } }
    });
  };
  const GUIDES = [['Make your first ad film', 'director', 'film', 'Write one line in Director. Hoola writes the storyboard for free. Paint the opening pictures, watch the free preview, then make the HD shots and the final film. Every paid step shows its price first.'],
    ['Keep a character the same in every shot', 'casting', 'cast', 'Cast the character once in AI casting. In your film, add it from Cast: Hoola keeps the face, hair and outfit the same in every shot.'],
    ['Write and sing a Hindi song', 'music', 'music', 'Describe the song, press Write with Hoola for the lyrics (or paste yours), pick the singers and mood, and press Create song.'],
    ['Dub a video into Tamil', 'dubbing', 'portrait', 'Upload your video (up to 3 minutes), pick up to 4 languages and press Dub now. Every language comes back as its own video with its words on screen here.'],
    ['Edit with words, not clicks', 'editor', 'city', 'Add your clips in order, say what you want (a 30 s reel, cuts on the beat, Hindi captions) and press Make the edit. Ask for changes in plain words.'],
    ['A voice-over in your Hoola’s voice', 'voice', 'voice', 'Write the script, pick Your Hoola’s voice or any of 22 voices, the language and the style, and press Make voice-over.']];
  // v0.327 each guide is a few numbered steps (the steps were buried in one paragraph) and the button that starts it
  const steps = t => t.split(/(?<=\.)\s+(?=[A-Z])/).filter(Boolean);
  V.learn = () => `<div class="home"><div class="sec-h" style="margin:0"><div><h2 style="font:400 26px/1.2 var(--serif)">How-to guides</h2><p class="mut" style="margin-top:6px">Short steps for each tool. Every paid step shows its price first.</p></div></div>
    <div class="guides">${GUIDES.map(([t, v, k, s], i) => `<div class="guide"><span class="thumb">${art(k, 'lr' + i)}</span><div><b>${t}</b><ol class="gsteps">${steps(s).map(x => `<li>${esc(x)}</li>`).join('')}</ol><button class="btn sec" data-go="${v}">Open ${TITLE[v]}${I('down', 'width:14px;height:14px;transform:rotate(-90deg)')}</button></div></div>`).join('')}</div></div>`;

  /* ---------------- icons ---------------- */
  const SPRITE = `<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <symbol id="i-side" viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="3"/><path d="M9.5 4.5v15"/></symbol>
  <symbol id="i-left" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></symbol>
  <symbol id="i-chev" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>
  <symbol id="i-down" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></symbol>
  <symbol id="i-up" viewBox="0 0 24 24"><path d="M6 15l6-6 6 6"/></symbol>
  <symbol id="i-right" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></symbol>
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
    for (const k of ['sbw', 'pw', 'cw']) { try { const w = +localStorage.getItem(RZ[k].key); if (w) $('#shell').style.setProperty('--' + k, w + 'px'); } catch {} }
    rzBind($('.rz-side'), 'sbw');
    load('showcase').then(() => showcaseSwap($('#view')));    // v0.329 real pictures over the drawn ones, once the list arrives
    { const sn = $('#snav'), fade = () => sn.classList.toggle('fadeb', sn.scrollTop + sn.clientHeight < sn.scrollHeight - 4);   // v0.306 fade only while more list is below
      sn.addEventListener('scroll', fade, {passive: true}); addEventListener('resize', fade); requestAnimationFrame(fade); }
    R.addEventListener('pointerdown', e => { if (popFor && !e.target.closest('#pop') && !popFor.contains(e.target)) closeMenu(); });
    R.addEventListener('scroll', e => { if (popFor && !e.target.closest?.('#pop')) closeMenu(); }, true);
    $('#picker').addEventListener('click', onPickerClick);
    R.addEventListener('click', e => {
      if (e.target.closest('#picker')) return;
      const t = e.target.closest('[data-close]'); if (t) { close(); return; }
      const ed = e.target.closest('[data-openproj-dir]'); if (ed) { const lb = $('#lightbox'); lb.hidden = true; lb.innerHTML = ''; DIR.project = ed.dataset.openprojDir; DIR.view = null; go('director'); return; }
      if (e.target.closest('[data-lbclose]') || e.target.id === 'lightbox') { const lb = $('#lightbox'); lb.hidden = true; lb.querySelectorAll('video,audio').forEach(m => m.pause()); lb.innerHTML = ''; return; }
      const lbdl = e.target.closest('#lightbox [data-dl]'); if (lbdl) { itemAction(lbdl); return; }
      const lbi = e.target.closest('#lightbox [data-ref], #lightbox [data-cine], #lightbox [data-del]'); if (lbi) { itemAction(lbi); return; }   // v0.999.53 the opened picture
      const lbm = e.target.closest('#lightbox [data-imore]'); if (lbm) { closeLb(); iMore(lbm.dataset.imore); return; }
      const lbc = e.target.closest('#lightbox [data-icopy]'); if (lbc) { const it = (D.items || []).find(x => x.id === lbc.dataset.icopy), m = it?.meta || {};
        navigator.clipboard?.writeText(m.prompt || m.description || '').then(() => toast('Copied'), () => toast('Could not copy', true)); return; }
      const lbx = e.target.closest('#lightbox [data-ichange]'); if (lbx) { const it = (D.items || []).find(x => x.id === lbx.dataset.ichange); closeLb(); if (!it) return;
        iAddRef(it); IMG.prompt = `Change this picture: `; if (VIEW === 'image') { iTray(); const q = $('#imgq'); q.value = IMG.prompt; q.focus(); } else go('image'); return; }
      const ag = e.target.closest('[data-vagain]'); if (ag) { const lb = $('#lightbox'); lb.querySelectorAll('video').forEach(m => m.pause()); lb.hidden = true; lb.innerHTML = '';   // v0.999.43 change a clip from its player
        VID.prompt = `Make "${ag.dataset.vagain}" again, but `; if (VIEW === 'video') { const q = $('#vidq'); q.value = VID.prompt; q.focus(); } else go('video'); return; }
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
    Object.assign(DIR, {brief: '', project: '', view: null, busy: '', castDraft: null}); IMG.prompt = ''; Object.assign(IMG, {chat: '', title: '', files: [], thread: null, rows: [], turn: null, lastSend: null, jobs: []}); VID.prompt = ''; Object.assign(VID, {chat: '', title: '', files: [], thread: null, rows: [], turn: null, lastSend: null}); SC.text = ''; SC.id = '';
    MU.lyrics = ''; MU.brief = ''; VO.text = ''; DB.src = null; ED.clips = []; ED.jobs = null; ED.job = '';
    if (host) { host.remove(); host = null; R = null; }
    try { sessionStorage.removeItem('hoola.create.view'); } catch {}
  }
  return {open, close, reset, isOpen: () => !!host && !host.hidden, go: v => open(v)};
};
