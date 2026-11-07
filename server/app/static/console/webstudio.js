/* v0.649 HOOLA WEB STUDIO - the website builder as its OWN full-screen app (owner-approved prototype, "PERFECT").

   Home (own sidebar): one line + a Build | Plan switch.
     Build = the site is made at once (POST /api/sites) and its plan is accepted (POST /plan) so the THREE LOOKS start.
     Plan  = Hoola's architect writes a plan from HER words (POST /api/site-architect): she reads it as a document,
             changes it in the chat (/revise), and only "Build this plan" (/approve, with the hash she saw) makes the site.
   Either way she first gets THREE COMPLETE LOOKS: every page of the site in each look (server: service._full_looks),
   clickable in a computer / tablet / phone frame, and only "Build in this look" builds (POST /look).
   Workspace (#/site/<id>): her own Hoola thread on the left (a conversation per site - never the home chat), the live
   preview and every tool on the right (Preview, Code, Cloud, Integrations, Health, Settings; History + Publish on top).

   Rules kept from the server, drawn: every server value goes through esc(); look colours only as plain #hex; going live,
   rollback, take-down, redirects and deletes ask first and send the server's hash; her keys are never asked for here. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' ? v : {};
  const HEX = v => /^#[0-9a-f]{3,8}$/i.test(S(v)) ? S(v) : '';
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const store = {get(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }, del(k) { try { localStorage.removeItem(k); } catch {} }};
  const TOKEN = store.get('hoola.console.token');
  const APP = $('#ws');
  if (!TOKEN) { location.replace('/console/'); return; }

  class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
  async function api(method, path, body, {raw = false, form = null} = {}) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (method === 'POST' && /\/conversations\/[^/]+\/messages$/.test(path) && body && typeof body.text === 'string') {
      const hints = L(body.hints).map(h => '\n\n[Web console ' + h + ']').join('');
      body = {...body, text: body.text + hints + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
      delete body.hints;
    }
    if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new ApiError(401, 'Please sign in again.'); }
    if (raw) { if (!r.ok) throw new ApiError(r.status, await r.text()); return r; }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) {
      const bad = data && Array.isArray(data.detail) && data.detail[0];
      const msg = (data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) ||
        (bad ? S(bad.msg) : '') || `The server refused the request (${r.status})`;
      const e = new ApiError(r.status, msg); e.data = data; throw e;
    }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'ws-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }

  const ICON = {
    home: '<path d="M4 11l8-7 8 7v9H4z"/>', grid: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18"/>',
    tpl: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    back: '<path d="M15 5l-7 7 7 7"/>', plus: '<path d="M12 5v14M5 12h14"/>', up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    chat: '<path d="M4 5h16v11H8l-4 4z"/>', move: '<path d="M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4"/>',
    pic: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 15l5-5 4 4 3-3 6 6"/>', sheet: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>', tab: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M11 18h2"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>', reload: '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>', lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>', sel: '<path d="M4 4l7 17 2-7 7-2z"/>', check: '<path d="M5 12l5 5 9-10"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    cart: '<path d="M4 6h2l2 10h10l2-7H8"/>', card: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>', blog: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 11h8M8 15h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>', pin: '<path d="M12 21s-7-6-7-12a7 7 0 0 1 14 0c0 6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'};
  const ico = (k, n = 18) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const tick = `<span class="tick" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5 9-10"/></svg></span>`;
  const STATUS = {draft: ['Starting', ''], planned: ['Plan ready', 'v'], looks: ['Pick a look', 'warn'], building: ['Building', 'v'],
    checking: ['Checking', 'v'], ready: ['Ready', 'ok'], failed: ['Needs attention', 'bad'], stopped: ['Paused', '']};
  const pill = (t, c) => `<span class="pill ${c || ''}">${esc(t)}</span>`;
  const statusPill = v => {
    if (S(v.status) === 'looks' && !L(v.looks).length) return pill('Making 3 looks', 'v');
    const [t, c] = STATUS[S(v.status)] || [S(v.status) || '…', ''];
    return pill(t + (Number(v.version) ? ` · v${v.version}` : ''), c);
  };
  const dotCls = v => ({ready: 'ok', looks: 'warn', planned: 'v', building: 'v', checking: 'v', failed: 'bad'}[S(v.status)] || '');
  const name = v => S(v.name) || S(v.field_label) || 'Website';
  const hasVersion = v => !!Number(v.version);
  const WORKING = v => ['building', 'checking'].includes(S(v.status)) || (S(v.status) === 'looks' && !L(v.looks).length) || !!v.mapping;
  const TYPES = [['Sweet shop', 'Menu, festival gift boxes, WhatsApp orders'], ['Clinic', 'Doctors, timings, booking slots you confirm'],
    ['Coaching classes', 'Batches, results, parent or student logins'], ['Restaurant', 'Menu with photos, table booking, directions'],
    ['Online shop', 'Catalogue, cart, COD and UPI, GST invoices'], ['Salon', 'Services, prices, appointment slots'],
    ['School admissions', 'Admissions form, fees, notices, logins'], ['Wedding or event', 'Story, gallery, RSVP form, venue map'],
    ['NGO or cause', 'Mission, projects, volunteer and donate pages'], ['Real estate', 'Projects, floor plans, site-visit booking'],
    ['Portfolio', 'Your work, about you, contact'], ['Personal page', 'About you, links, contact']];
  const MODE_KEY = 'hoola.ws.mode';
  const convKey = id => 'hoola.wdp.conv.' + id;           // the same per-site thread the v0.646 panel kept
  const DEV = {pc: [1280, 860, 'Computer'], tablet: [820, 1100, 'Tablet'], phone: [390, 800, 'Phone']};

  let SITES = [], SPECS = [], CUR = null, CARD = null, VIEW = 'preview', DEVICE = 'pc', LOOK = 0, EDIT = false;
  let POLL = null, SIG = '', PREFILL = '', BUSY = false, RO = null;
  const THREAD = {site: '', conv: '', rows: [], live: '', waiting: false, since: 0, started: 0, timer: null, sig: ''};

  /* ================= router ================= */
  function parts() { return S(location.hash).replace(/^#\/?/, '').split('/').filter(Boolean); }
  async function route() {
    stopPoll(); clearTimeout(THREAD.timer); EDIT = false;
    const p = parts();
    try {
      if (p[0] === 'site' && p[1]) return await openSite(decodeURIComponent(p[1]), p[2] || '');
      if (p[0] === 'plan' && p[1]) return await openPlan(decodeURIComponent(p[1]));
      CUR = null; CARD = null;
      await loadLists();
      drawHome(p[0] === 'sites' ? 'sites' : p[0] === 'templates' ? 'templates' : 'home');
    } catch (e) { APP.innerHTML = `<div class="empty">${esc(e.message)} · <a href="#/">Studio home</a></div>`; }
  }
  addEventListener('hashchange', route);
  const go = h => { if (location.hash === h) route(); else location.hash = h; };

  async function loadLists() {
    const [a, b] = await Promise.allSettled([api('GET', '/api/sites'), api('GET', '/api/site-architect')]);
    SITES = a.status === 'fulfilled' ? L(a.value.sites) : [];
    SPECS = b.status === 'fulfilled' ? L(b.value.specs).filter(x => S(x.status) !== 'built') : [];
  }

  /* ================= home with its own sidebar ================= */
  function sidebar(cur) {
    const rec = SITES.slice(0, 6).map(v => `<a class="rec" href="#/site/${enc(S(v.id))}"><span class="dot ${dotCls(v)}" aria-hidden="true"></span>${esc(name(v))}</a>`).join('');
    const nav = (h, k, label, ic) => `<a class="nav" href="${h}" ${cur === k ? 'aria-current="page"' : ''}>${ico(ic)}${esc(label)}</a>`;
    return `<aside class="side" aria-label="Web Studio">
      <div class="brand"><div class="mark" aria-hidden="true"><span></span></div><div><b>Hoola</b><span>Web Studio</span></div></div>
      <button class="new" type="button" data-act="new">${ico('plus', 16)}New website</button>
      ${nav('#/', 'home', 'Home', 'home')}${nav('#/sites', 'sites', 'All websites', 'grid')}${nav('#/templates', 'templates', 'Templates', 'tpl')}
      ${rec ? `<div class="lbl">Recent</div>${rec}` : ''}
      <div class="sp"></div>
      <a class="nav" href="/console/">${ico('back')}Back to Hoola</a>
    </aside>`;
  }

  function siteCard(v) {
    return `<a class="card" href="#/site/${enc(S(v.id))}"><span class="shot" aria-hidden="true"><i></i><i></i><b></b></span>
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b>${esc(name(v))}</b>${statusPill(v)}</span>
      <span class="mut sm ell">${esc([S(v.number), S(v.field_label), S(v.goal_label)].filter(Boolean).join(' · '))}</span></span></a>`;
  }
  function specCard(x) {
    return `<a class="card" href="#/plan/${enc(S(x.id))}"><span class="shot" aria-hidden="true"><i></i><i></i><b></b></span>
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b>${esc(S(x.name) || 'New plan')}</b>${pill('Plan · your Haan', 'v')}</span>
      <span class="mut sm ell">${esc(S(x.words))}</span></span></a>`;
  }

  function drawHome(page) {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    let main;
    if (page === 'templates') {
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">Templates</h2></div>
        <p class="mut">A starting point for your kind of business. Hoola still plans your own pages from your details; nothing is copied word for word.</p>
        <div class="starts">${TYPES.map(([t, d]) => `<button class="st" type="button" data-type="${esc(t)}"><span class="si">${ico('tpl')}</span><span><b>${esc(t)}</b><span class="mut sm">${esc(d)}</span></span></button>`).join('')}</div></section>`;
    } else if (page === 'sites') {
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">All websites</h2><button class="b" type="button" data-act="new">${ico('plus', 16)}New website</button></div>
        ${SPECS.length ? `<div class="sec"><h2>Plans waiting for your Haan</h2></div><div class="grid">${SPECS.map(specCard).join('')}</div>` : ''}
        ${SITES.length ? `<div class="grid">${SITES.map(siteCard).join('')}</div>` : '<div class="panel mut">No website yet. Write one line on the Studio home.</div>'}</section>`;
    } else {
      main = `<section class="hero"><h1>What should we build today?</h1>
        <p class="mut">Describe your business in one line. You get three complete looks of the whole website to click through first; only the one you pick is built, and nothing goes live until you tap.</p>
        <form class="ask" data-form="ask">
          <label for="wsAsk" class="sr">Describe your website</label>
          <textarea id="wsAsk" rows="3" maxlength="2000" placeholder="A website for Sharma Sweets in Akola: menu, Diwali gift boxes and a WhatsApp order button">${esc(PREFILL)}</textarea>
          <div class="bar">
            <button class="b ghost" type="button" data-src="old">${ico('move', 16)}Move my old site</button>
            <button class="b ghost" type="button" data-src="shot">${ico('pic', 16)}Design from a picture</button>
            <span class="sp"></span>
            <span class="mut sm mnote" id="wsModeNote">${mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: 3 full looks first'}</span>
            <div class="seg" role="group" aria-label="Mode"><button type="button" data-mode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-mode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
            <button class="go" type="submit" aria-label="Start">${ico('up', 18)}</button>
          </div>
        </form>
        <div id="wsSrc" class="wrap" style="max-width:780px"></div>
        <div class="chips">${TYPES.slice(0, 7).map(([t]) => `<button class="chip" type="button" data-type="${esc(t)}">${esc(t)}</button>`).join('')}<a class="chip" href="#/templates">More templates</a></div>
      </section>
      ${SPECS.length ? `<section class="wrap"><div class="sec"><h2>Plans waiting for your Haan</h2></div><div class="grid">${SPECS.slice(0, 4).map(specCard).join('')}</div></section>` : ''}
      <section class="wrap"><div class="sec"><h2>Your websites</h2>${SITES.length > 8 ? '<a class="b ghost" href="#/sites">See all</a>' : ''}</div>
        ${SITES.length ? `<div class="grid">${SITES.slice(0, 8).map(siteCard).join('')}</div>` : '<div class="panel mut">No website yet. Write one line above.</div>'}</section>
      <section class="wrap"><div class="sec"><h2>Or start from</h2></div><div class="starts">
        <button class="st" type="button" data-src="focus"><span class="si">${ico('chat')}</span><span><b>Describe it</b><span class="mut sm">One line in your own words.</span></span></button>
        <button class="st" type="button" data-src="old"><span class="si">${ico('move')}</span><span><b>Move my old site</b><span class="mut sm">Your own site; old links keep working.</span></span></button>
        <button class="st" type="button" data-src="shot"><span class="si">${ico('pic')}</span><span><b>A picture or screenshot</b><span class="mut sm">Colours and style are measured.</span></span></button>
        <button class="st" type="button" data-src="sheet"><span class="si">${ico('sheet')}</span><span><b>A product sheet</b><span class="mut sm">Excel or Google Sheet to a catalogue.</span></span></button>
      </div></section>`;
    }
    APP.innerHTML = `<div class="home">${sidebar(page)}<main class="hmain">${main}</main></div>`;
    PREFILL = '';
    document.title = 'Hoola Web Studio';
  }

  function drawSource(kind) {
    const box = $('#wsSrc'); if (!box) return;
    if (kind === 'old') box.innerHTML = `<form class="panel" data-form="old"><b>Move my old website</b>
        <p class="mut sm">Hoola reads your own site's pages, colours, photos and addresses. If it can't tell the site is yours, it shows one line to add first.</p>
        <div class="inl"><input class="in" name="url" type="url" inputmode="url" aria-label="Your old website address" placeholder="https://your-old-site.in" required>
        <button class="b pri" type="submit">Read my site</button></div><div data-out></div></form>`;
    else if (kind === 'shot') box.innerHTML = `<form class="panel" data-form="shot"><b>Use a design you like</b>
        <p class="mut sm">Write one line about the website in the box above. The picture's colours and style are measured; no words, logos or photos are taken from it.</p>
        <div class="inl"><input name="file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Picture" required>
        <button class="b pri" type="submit">Read the design</button></div><div data-out></div></form>`;
    else if (kind === 'sheet') box.innerHTML = `<div class="panel"><b>From a product sheet</b><p class="mut sm">Write one line about the shop above and put the sheet link in it. After the website is built, Cloud previews the catalogue before anything is written.</p></div>`;
    else box.innerHTML = '';
  }

  async function newConv(title) {
    const c = S((await api('POST', '/api/conversations')).id);
    if (title) api('PATCH', `/api/conversations/${enc(c)}`, {title}).catch(() => {});
    return c;
  }

  async function startFromAsk(text) {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    const conv = await newConv('');
    try {
      if (mode === 'plan') {
        const c = await api('POST', '/api/site-architect', {words: text, conversation_id: conv});
        store.set('hoola.ws.spec.conv.' + c.id, conv); store.set('hoola.ws.spec.words.' + c.id, text);
        api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Website plan · ${S(c.name) || 'new'}`}).catch(() => {});
        go('#/plan/' + enc(S(c.id)));
        return;
      }
      const v = await api('POST', '/api/sites', {brief: text, conversation_id: conv});
      store.set(convKey(v.id), conv);
      api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Website · ${name(v)}`}).catch(() => {});
      if (S(v.status) === 'planned' && !v.mapping) {         // Build mode: no plan step - the three full looks start now
        try { await api('POST', `/api/sites/${enc(v.id)}/plan`, {conversation_id: conv}); } catch (e) { toast(e.message, true); }
      }
      go('#/site/' + enc(S(v.id)));
    } catch (e) {
      api('DELETE', `/api/conversations/${enc(conv)}`).catch(() => {});
      throw e;
    }
  }

  async function readDesign(f, kind) {
    const out = f.querySelector('[data-out]'); out.innerHTML = '<p class="mut sm">Reading…</p>';
    let res;
    if (kind === 'old') {
      const url = S(f.url.value).trim(); if (!url) { out.innerHTML = ''; return toast('Write the address first.', true); }
      res = await api('POST', '/api/site-design/read', {source: 'site', url}, {raw: true}).then(async r => ({ok: true, data: await r.json()}))
        .catch(e => { let x = {}; try { x = JSON.parse(e.message); } catch {} return {ok: false, data: x, msg: S(x.detail || x.error) || e.message}; });
    } else {
      const file = f.file.files?.[0]; if (!file) { out.innerHTML = ''; return toast('Choose a picture first.', true); }
      const fd = new FormData(); fd.append('file', file);
      res = await api('POST', '/api/site-design/read', undefined, {form: fd}).then(data => ({ok: true, data})).catch(e => ({ok: false, msg: e.message}));
    }
    if (!res.ok) {
      const p = M(res.data?.proof);
      out.innerHTML = p.txt_value ? `<div class="launch"><b>First show the site is yours.</b><p class="sm">Add one of these, then press Read my site again.</p>
          <div class="kv"><span>DNS TXT record</span><code class="ell">${esc(S(p.txt_name))} = ${esc(S(p.txt_value))}</code></div>
          <div class="kv"><span>Or in the home page &lt;head&gt;</span><code class="ell">${esc(S(p.meta))}</code></div></div>`
        : `<p class="li bad">${esc(res.msg || 'Could not read it.')}</p>`;
      return;
    }
    const r = res.data;
    out.innerHTML = `<div class="launch"><p class="sm">${esc(S(r.say))}</p><div class="inl" style="justify-content:flex-end">
      ${kind === 'old' ? `<button class="b" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">New layout, my content</button>
        <button class="b pri" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="1">Keep my pages and order</button>`
        : `<button class="b pri" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">Use this design</button>`}</div></div>`;
  }

  /* ================= plan mode: a plan written from her words ================= */
  async function openPlan(id) {
    CARD = await api('GET', `/api/site-architect/${enc(id)}`);
    if (S(CARD.status) === 'built' && CARD.site) {
      const site = SITES.find(x => S(x.number) === S(CARD.site));
      if (site) return go('#/site/' + enc(S(site.id)));
    }
    const words = store.get('hoola.ws.spec.words.' + id);
    const log = (() => { try { return JSON.parse(sessionStorage.getItem('hoola.ws.spec.log.' + id) || '[]'); } catch { return []; } })();
    APP.innerHTML = `<div class="wsp">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a>
        <span class="pname">${esc(S(CARD.name) || 'New website')}</span>${pill('Plan mode · nothing built yet', 'v')}<span class="sp"></span>
        <a class="b ghost" href="#/sites">All websites</a></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this plan">
          <div class="msgs" id="wsPlanMsgs" aria-live="polite">
            ${words ? `<div class="me">${esc(words)}</div>` : ''}
            <div class="step">${tick}Plan written from your words · on the right</div>
            ${CARD.summary ? `<div class="ho"><p>${esc(S(CARD.summary))}</p></div>` : ''}
            ${L(CARD.questions).length ? `<div class="ho"><p>Before you build, tell me if you can:</p><ul>${L(CARD.questions).map(q => `<li>${esc(S(q))}</li>`).join('')}</ul></div>` : ''}
            ${log.map(x => `<div class="me">${esc(S(x.me))}</div><div class="step">${tick}${esc(S(x.done))}</div>`).join('')}
          </div>
          <form class="comp" data-form="revise"><label for="wsRev" class="sr">Change the plan</label>
            <textarea id="wsRev" rows="2" maxlength="2000" placeholder="Change the plan: e.g. teachers also mark attendance on the phone…"></textarea>
            <div class="cbar"><span class="mut sm">Plan mode · nothing is built until you say so</span><span class="sp"></span><button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" aria-label="Plan">
          <div class="ptop"><nav class="views" aria-label="Views"><button type="button" aria-current="page">Plan</button><button type="button" disabled>Preview</button><button type="button" disabled>Code</button></nav></div>
          <div class="stage">${planDoc(CARD, words)}</div>
        </section>
      </div></div>`;
    document.title = `${S(CARD.name) || 'Plan'} · Hoola Web Studio`;
    const m = $('#wsPlanMsgs'); if (m) m.scrollTop = m.scrollHeight;
  }

  function planDoc(c, words) {
    const mods = L(c.modules);
    return `<article class="doc">
      <div>${pill(`Plan ${S(c.number)}`, '')}<h2 style="margin-top:10px">${esc(S(c.name) || 'Your website')}</h2></div>
      ${words ? `<p class="quote">"${esc(words)}"</p>` : ''}
      ${c.summary ? `<section><h3>What I will build</h3><p>${esc(S(c.summary))}</p></section>` : ''}
      ${mods.map(m => `<section><h3>${esc(S(m.title))}${m.ready === false ? ` ${pill('Needs a fix', 'warn')}` : ''}</h3>
        <ul>${L(m.lines).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul></section>`).join('')}
      ${L(c.warnings).length ? `<section><h3>Worth checking</h3><ul>${L(c.warnings).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul></section>` : ''}
      ${L(c.questions).length ? `<section><h3>Open questions</h3><ul>${L(c.questions).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul></section>` : ''}
      <div class="dfoot"><span class="mut sm sp">Next: three complete looks of this whole site to click through. Only your pick is built.</span>
        ${S(c.status) === 'built' ? `<a class="b pri" href="#/sites">Open the website</a>` : `<button class="b pri" type="button" data-act="approve-plan" data-hash="${esc(S(c.hash))}">Build this plan</button>`}</div>
    </article>`;
  }

  /* ================= workspace ================= */
  async function openSite(id, view) {
    const v = await api('GET', `/api/sites/${enc(id)}`);
    const same = CUR && CUR.id === v.id;
    CUR = v; VIEW = view || (same ? VIEW : 'preview');
    if (!same) { LOOK = Math.max(0, Number(M(v).chosen_look) || 0); DEVICE = 'pc'; }
    drawShell();
    openThread();
  }

  const VIEWS = [['preview', 'Preview'], ['code', 'Code'], ['cloud', 'Cloud'], ['integrations', 'Integrations'], ['health', 'Health'], ['settings', 'Settings']];
  function drawShell() {
    const v = CUR, mode = store.get(MODE_KEY + '.chat') === 'plan' ? 'plan' : 'build';
    APP.innerHTML = `<div class="wsp">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a>
        <span class="pname">${esc(name(v))}</span><span id="wsPill">${statusPill(v)}</span><span class="sp"></span>
        <button class="b" type="button" data-view="history">${ico('hist', 15)}<span>History</span></button>
        <button class="b pri" type="button" data-view="publish"><span>Publish</span></button></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this website">
          <div class="msgs" id="wsMsgs" aria-live="polite"></div>
          <div id="wsState" style="padding:0 18px"></div>
          <form class="comp" data-form="thread"><label for="wsTh" class="sr">Message Hoola about this website</label>
            <textarea id="wsTh" rows="2" maxlength="4000" placeholder="Ask Hoola to change anything…"></textarea>
            <div class="cbar">
              <button class="ib" type="button" data-act="select" aria-label="Select on the page" title="Select on the page">${ico('sel', 16)}</button>
              <div class="seg" role="group" aria-label="Mode"><button type="button" data-cmode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-cmode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
              <span class="sp"></span><button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" id="wsPane" aria-label="Website"></section>
      </div></div>`;
    document.title = `${name(v)} · Hoola Web Studio`;
    drawState(); drawPane();
  }

  function drawState() {
    const box = $('#wsState'); if (!box || !CUR) return;
    const v = CUR, b = M(v.board);
    box.innerHTML = WORKING(v) ? `<div class="step" style="padding:4px 0 2px"><span class="spin" aria-hidden="true"></span><span class="ell">${esc(S(b.now) || S(v.say) || 'Working…')}</span>${b.total ? `<span class="sp"></span><span>${esc(S(b.pct || 0))}%</span>` : ''}</div>` : '';
    const p = $('#wsPill'); if (p) p.innerHTML = statusPill(v);
  }

  function viewsBar(extra = '') {
    const looks = S(CUR.status) === 'looks' && L(CUR.looks).length;
    return `<div class="ptop"><nav class="views" aria-label="Views">${VIEWS.map(([k, n]) => `<button type="button" data-view="${k}" ${VIEW === k ? 'aria-current="page"' : ''}>${esc(k === 'preview' && looks ? '3 looks' : n)}</button>`).join('')}</nav>${extra}</div>`;
  }
  const devSeg = () => `<div class="seg" role="group" aria-label="Device">${Object.entries(DEV).map(([k, d]) => `<button type="button" data-dev="${k}" aria-pressed="${DEVICE === k}" aria-label="${d[2]}" title="${d[2]}">${ico(k === 'pc' ? 'pc' : k === 'tablet' ? 'tab' : 'phone', 16)}</button>`).join('')}</div>`;
  const frame = (src, title) => `<div class="frame ${DEVICE}" data-w="${DEV[DEVICE][0]}" data-h="${DEV[DEVICE][1]}"><iframe title="${esc(title)}" sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>`;

  function drawPane() {
    const pane = $('#wsPane'); if (!pane || !CUR) return;
    stopPoll();
    const fn = {preview, code, cloud, integrations, health, settings, history: historyView, publish}[VIEW] || preview;
    fn(pane, CUR);
    if (WORKING(CUR)) startPoll();
  }

  function fit() {
    const f = APP.querySelector('.frame'); if (!f) return;
    const doit = () => {
      const fr = f.querySelector('iframe'); if (!fr) return;
      const w = Number(f.dataset.w), h = Number(f.dataset.h), k = Math.min(1, (f.clientWidth || w) / w);
      fr.style.width = w + 'px'; fr.style.height = h + 'px'; fr.style.transform = `scale(${k})`;
      f.style.height = Math.round(h * k) + 'px';
    };
    doit();
    if (window.ResizeObserver) { RO?.disconnect(); RO = new ResizeObserver(doit); RO.observe(f); }
  }

  function preview(pane, v) {
    const st = S(v.status), b = M(v.board);
    if (st === 'planned' && !v.mapping) {
      const pages = L(M(v.plan).pages);
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>The plan is ready</h2><p class="mut">${esc(S(v.say))}</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${pages.map(p => pill(S(p.title))).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b ghost bad" type="button" data-act="delete">Delete</button><button class="b pri" type="button" data-act="approve">Make the 3 looks</button></div></div></div>`;
      return;
    }
    if (st === 'looks' && L(v.looks).length) return looksView(pane, v);
    if (WORKING(v) && !hasVersion(v)) {
      const t = v.mapping ? 'Planning every page of a big site' : st === 'looks' ? 'Making three complete looks' : st === 'checking' ? 'Checking every page' : 'Building your website';
      const note = st === 'looks' ? 'Every page of your site is written once, then shown in three different designs. You click through all of them before anything is built.'
        : 'Each page is written, put together and checked on a phone and a computer.';
      const pct = Math.max(4, Math.min(100, Number(b.pct) || 0));
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><div style="display:flex;align-items:center;gap:10px"><h2 class="sp">${esc(t)}</h2><span class="spin" aria-hidden="true"></span></div>
        <p class="mut">${esc(note)}</p><div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}" aria-label="Progress"><i style="width:${pct}%"></i></div>
        <p class="mut sm">${esc(S(b.now) || S(v.say) || 'Working…')}</p>
        ${['building', 'checking'].includes(st) ? '<div class="inl" style="justify-content:flex-end"><button class="b" type="button" data-act="stop">Pause</button></div>' : ''}</div></div>`;
      return;
    }
    const src = S(v.preview) + (EDIT ? '__edit/' : '');
    const top = `<div class="url">${ico('lock', 14)}<span>${EDIT ? 'Edit mode · ' : ''}preview</span></div>${devSeg()}
      <button class="ib" type="button" data-act="reload" aria-label="Reload preview">${ico('reload', 16)}</button>
      ${v.preview ? `<a class="ib" href="${esc(S(v.preview))}" target="_blank" rel="noopener" aria-label="Open in a new tab">${ico('ext', 16)}</a>` : ''}`;
    pane.innerHTML = viewsBar(top)
      + (EDIT ? `<div class="edbar"><b>Edit mode</b><span>Click any words to type · click a picture to change it · free, no AI</span><span class="sp"></span>
          <button class="b sm" type="button" data-act="undo">Undo</button><button class="b sm pri" type="button" data-act="edit-done">Done</button></div>` : '')
      + (st === 'failed' || st === 'stopped' ? `<div class="edbar"><b>${st === 'failed' ? 'The last build stopped on a problem' : 'Building is paused'}</b><span class="ell">${esc(S(v.error))}</span><span class="sp"></span><button class="b sm pri" type="button" data-act="resume">${st === 'failed' ? 'Try again' : 'Continue'}</button></div>` : '')
      + (WORKING(v) ? `<div class="edbar"><span class="spin" aria-hidden="true"></span><span class="ell">${esc(S(b.now) || 'Updating your website…')}</span></div>` : '')
      + `<div class="stage">${v.preview ? frame(src, 'Website preview') : '<div class="empty">No preview yet.</div>'}</div>`;
    fit();
  }

  function looksView(pane, v) {
    const looks = L(v.looks);
    if (LOOK >= looks.length) LOOK = 0;
    const lk = M(looks[LOOK]);
    const est = M(v.estimate);
    pane.innerHTML = viewsBar(`<span class="sp"></span>${devSeg()}`)
      + `<div class="ptop"><div class="lks" role="group" aria-label="Look">${looks.map((x, i) => `<button type="button" data-look="${i}" aria-pressed="${i === LOOK}">
          <span class="sw" aria-hidden="true">${L(x.colors).map(HEX).filter(Boolean).slice(0, 4).map(c => `<i style="background:${c}"></i>`).join('')}</span><span>${i + 1} · ${esc(S(x.label))}</span></button>`).join('')}</div>
        <span class="sp"></span><span class="mut sm">${lk.full ? 'The whole site · every page works' : 'The top of the home page (the whole site is made after you pick)'}</span></div>`
      + `<div class="stage">${lk.preview ? frame(S(lk.preview), `Look ${LOOK + 1}`) : '<div class="empty">This look has no preview.</div>'}</div>`
      + `<div class="choose"><span class="sm"><b>${LOOK + 1} · ${esc(S(lk.label))}</b>${lk.concept ? ` <span class="mut">· ${esc(S(lk.concept))}</span>` : ''}</span><span class="sp"></span>
          ${est.say ? `<span class="mut sm">${esc(S(est.say))}</span>` : ''}<button class="b pri" type="button" data-act="pick-look">Build in this look</button></div>`;
    fit();
  }

  const studioBtn = (label, ask, pri) => `<button class="b ${pri ? 'pri' : ''}" type="button" data-ask="${esc(ask)}">${esc(label)}</button>`;

  async function code(pane, v) {
    if (!hasVersion(v) && !L(M(v.plan).pages).length) { pane.innerHTML = viewsBar() + '<div class="stage"><div class="box"><p class="mut">The code appears once pages are written.</p></div></div>'; return; }
    pane.innerHTML = viewsBar(`<span class="sp"></span><button class="b" type="button" data-act="export" data-fmt="zip">Download ZIP</button><button class="b" type="button" data-act="export" data-fmt="react">React + Vite</button>`) + '<div class="empty">Loading the files…</div>';
    let t;
    try { t = await api('GET', `/api/sites/${enc(v.id)}/code`); } catch (e) { pane.querySelector('.empty').textContent = e.message; return; }
    if (VIEW !== 'code' || CUR?.id !== v.id) return;
    const groups = L(t.files);
    pane.innerHTML = viewsBar(`<span class="sp"></span><button class="b" type="button" data-act="export" data-fmt="zip">Download ZIP</button><button class="b" type="button" data-act="export" data-fmt="react">React + Vite</button>`)
      + `<div class="split"><nav class="subnav" aria-label="Files">${groups.map(g => `<div class="h">${esc(S(g.title))}</div>${L(g.files).map(f => `<button type="button" data-file="${esc(S(f.path))}"><span class="mono ell">${esc(S(f.label))}</span></button>`).join('')}`).join('') || '<div class="h">No files yet</div>'}</nav>
        <div class="code" id="wsCode"><div class="empty">Choose a file on the left. Every save is checked for safety, becomes a version, and Undo brings it back.</div></div></div>`;
  }

  async function openFile(path) {
    const box = $('#wsCode'); if (!box) return;
    APP.querySelectorAll('[data-file]').forEach(b => b.setAttribute('aria-current', b.dataset.file === path ? 'page' : 'false'));
    box.innerHTML = '<div class="empty">Opening…</div>';
    try {
      const f = await api('GET', `/api/sites/${enc(CUR.id)}/code?path=${enc(path)}`);
      box.innerHTML = `<form data-form="code" data-path="${esc(path)}" style="display:flex;flex-direction:column;flex:1 1 auto;min-height:0"><label class="sr" for="wsCodeT">${esc(path)}</label>
        <textarea id="wsCodeT" spellcheck="false">${esc(S(f.code))}</textarea>
        <div class="cbar2"><code class="ell">${esc(path)}</code><span class="sp"></span><button class="b" type="button" data-act="undo">Undo</button><button class="b pri" type="submit">Save as a new version</button></div></form>`;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  async function cloud(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading your data…</div>';
    let a;
    try { a = await api('GET', `/api/sites/${enc(v.id)}/app`); } catch (e) { a = {error: e.message}; }
    if (VIEW !== 'cloud' || CUR?.id !== v.id) return;
    const cols = L(M(a.app).collections);
    if (!cols.length) {
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>No lists yet</h2><p class="mut">Orders, enquiries, members, bookings: ask for the ones you need and Hoola adds logins and the lists, with rules worked out by the server.</p>
        <div class="inl">${studioBtn('Add lists and logins', 'Is website mein logins aur ek list jodo: ', true)}</div>${a.error ? `<p class="mut sm">${esc(a.error)}</p>` : ''}</div></div>`;
      return;
    }
    pane.innerHTML = viewsBar() + `<div class="split"><nav class="subnav" aria-label="Lists"><div class="h">Data</div>${cols.map((c, i) => `<button type="button" data-coll="${esc(S(c.key))}" ${i ? '' : 'aria-current="page"'}>${esc(S(c.label))}${M(a.counts)[c.key] != null ? `<span class="sp"></span><span class="mut sm">${esc(S(M(a.counts)[c.key]))}</span>` : ''}</button>`).join('')}
        <div class="h">People</div><button type="button" data-coll="__members">Members and logins</button></nav><div class="main" id="wsCloud"></div></div>`;
    openColl(S(cols[0].key));
  }

  async function openColl(key) {
    const box = $('#wsCloud'); if (!box) return;
    APP.querySelectorAll('[data-coll]').forEach(b => b.setAttribute('aria-current', b.dataset.coll === key ? 'page' : 'false'));
    box.innerHTML = '<div class="empty">Loading…</div>';
    try {
      if (key === '__members') {
        const m = await api('GET', `/api/sites/${enc(CUR.id)}/app/members`);
        const rows = L(m.members);
        box.innerHTML = `<h2 style="font-size:18px">Members and logins</h2>${rows.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">Name</th><th scope="col">Mobile / email</th><th scope="col">Role</th></tr></thead><tbody>
          ${rows.map(x => `<tr><td>${esc(S(x.name) || '—')}</td><td>${esc(S(x.phone || x.email || x.login))}</td><td>${esc(S(x.role))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Nobody has signed up yet.</p>'}`;
        return;
      }
      const r = await api('GET', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}`);
      const c = M(r.collection), fields = L(c.fields).slice(0, 8), rows = L(r.rows);
      const val = (row, k) => { const d = M(row.data || row); const x = d[k]; return x == null ? '' : typeof x === 'object' ? JSON.stringify(x) : S(x); };
      box.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><h2 style="font-size:18px" class="sp">${esc(S(c.label) || key)}</h2><span class="mut sm">${rows.length} rows</span></div>
        ${rows.length ? `<div class="tbox"><table class="t"><thead><tr>${fields.map(f => `<th scope="col">${esc(S(f.label || f.key))}</th>`).join('')}</tr></thead>
          <tbody>${rows.slice(0, 200).map(row => `<tr>${fields.map(f => `<td>${esc(val(row, f.key))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p class="mut">No rows yet.</p>'}
        <p class="note">Totals and prices are worked out by the server, and visitors see only their own rows.</p>`;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  function integrations(pane, v) {
    const langs = L(v.languages), items = [['cart', 'Shop and cart', 'Prices and stock checked by the server, COD, pickup, coupons, GST invoices.', 'Is website mein shop chalu karo'],
      ['card', 'Online payments', 'UPI QR to your UPI ID, or your own Razorpay / Cashfree / PhonePe. Paid only when the gateway confirms.', 'Is website par online payment jodo'],
      ['cal', 'Booking slots', 'Real time slots with limits; you confirm each booking.', 'Is website mein booking slot lagao'],
      ['blog', 'Blog', 'Hoola drafts posts, you say Haan to publish. RSS and scheduling.', 'Is website par blog chalu karo'],
      ['globe', 'Languages', `Now: ${langs.join(', ') || 'en'}. Up to 4 more Indian languages with a switch in the menu.`, 'Is website mein Hindi version bhi jodo'],
      ['chat', 'Visitor chat', 'Visitors message your team from the site; your reply goes only on your tap.', 'Is website par visitor chat chalu karo'],
      ['pin', 'Map and directions', 'Loads only when the visitor taps, so the page stays fast.', 'Is website ke contact page par map lagao'],
      ['spark', 'Rich pieces', 'Quiz, configurator, comparison table, animation, 3D hero.', 'Is website mein ek quiz jodo: '],
      ['link', 'Your other apps', 'New orders to Google Sheets, HubSpot or Slack through your own account.', 'Is website ke naye orders meri Google Sheet mein bhejo']];
    pane.innerHTML = viewsBar() + `<div class="main"><p class="mut">Each one is asked in this website's chat on the left, so Hoola plans it first. Money never moves without your tap.</p>
      <div class="cards">${items.map(([k, t, d, ask]) => `<section class="cardp"><div style="display:flex;align-items:center;gap:10px"><span class="si">${ico(k)}</span><b style="font-size:14.5px">${esc(t)}</b></div>
        <p class="mut sm">${esc(d)}</p><div class="inl" style="margin-top:auto">${studioBtn('Add', ask, false)}</div></section>`).join('')}</div></div>`;
  }

  async function health(pane, v) {
    if (!hasVersion(v)) { pane.innerHTML = viewsBar() + '<div class="stage"><div class="box"><p class="mut">Health shows up once the website is built and live.</p></div></div>'; return; }
    pane.innerHTML = viewsBar() + '<div class="empty">Reading visits, speed and backups…</div>';
    let care = null, ops = null;
    try { care = await api('GET', `/api/sites/${enc(v.id)}/care?days=30`); } catch (e) { care = {error: e.message}; }
    try { ops = await api('GET', `/api/sites/${enc(v.id)}/ops?days=30`); } catch (e) { ops = {error: e.message}; }
    if (VIEW !== 'health' || CUR?.id !== v.id) return;
    const chk = M(v.checks), sp = M(care.speed || ops.speed), bk = M(ops.backup), rt = M(bk.restore_test);
    const band = g => g === 'good' ? 'ok' : g === 'poor' ? 'bad' : 'warn';
    const row = (k, label) => sp[k] ? `<div class="kv"><span>${esc(label)}</span>${pill(`${S(sp[k].p75)} · ${S(sp[k].grade)}`, band(S(sp[k].grade)))}</div>` : '';
    pane.innerHTML = viewsBar() + `<div class="main">${care.say ? `<section class="cardp acc"><p>${esc(S(care.say))}</p>${L(care.tips).map(t => `<p class="li">${esc(S(t))}</p>`).join('')}</section>` : ''}
      <div class="pc2">
      <section class="cardp"><h3>Visitors and results (30 days)</h3><p class="mut sm">No cookies, no trackers: pages counted per day only.</p>
        ${care.error ? `<p class="mut">${esc(care.error)}</p>` : `<div class="kv"><span>Page visits</span><b>${esc(S(care.views ?? '–'))}</b></div>
        <div class="kv"><span>Enquiries</span><b>${esc(S(care.leads ?? '–'))}</b></div>
        <div class="kv"><span>Uptime</span><b>${care.uptime_pct == null ? 'not measured yet' : esc(S(care.uptime_pct)) + '%'}</b></div>
        ${Object.entries(M(care.ssl_days)).map(([h, d]) => `<div class="kv"><span class="ell">HTTPS · <code>${esc(S(h))}</code></span><b>${d == null ? '–' : esc(S(d)) + ' days left'}</b></div>`).join('')}`}</section>
      <section class="cardp"><h3>Speed on real phones (p75)</h3>${row('lcp', 'Main picture shows') + row('fcp', 'First paint') + row('cls', 'Layout shift') + row('ttfb', 'Server answer') || '<p class="mut">No real visits measured yet.</p>'}</section>
      <section class="cardp"><h3>Checks before going live</h3>${chk.passed == null ? '<p class="mut">Not run yet.</p>' : `<div class="kv"><span>Blocking checks</span>${pill(chk.passed ? 'Passed' : L(chk.blocking).length + ' to fix', chk.passed ? 'ok' : 'bad')}</div>
        <div class="kv"><span>Notes</span>${pill(String(L(chk.warnings).length), L(chk.warnings).length ? 'warn' : 'ok')}</div><div class="kv"><span>Test visitor walks</span>${pill(String(L(chk.journeys).length))}</div>`}</section>
      <section class="cardp"><h3>Errors and backups</h3>${ops.error ? `<p class="mut">${esc(ops.error)}</p>` : `<div class="kv"><span>Visitor page errors</span>${pill(Number(ops.errors) ? String(ops.errors) : 'None', Number(ops.errors) ? 'warn' : 'ok')}</div>
        <div class="kv"><span>Backups</span>${pill(bk.enabled ? (bk.last_day ? 'Last ' + S(bk.last_day) : 'On') : 'Off', bk.enabled ? 'ok' : 'warn')}</div>
        <div class="kv"><span>Restore test</span>${rt.day ? pill(rt.ok ? 'Matched · ' + S(rt.day) : 'Did not match · ' + S(rt.day), rt.ok ? 'ok' : 'bad') : pill('Not run yet')}</div>`}</section></div></div>`;
  }

  function settings(pane, v) {
    const f = M(v.facts);
    const fields = [['name', 'Business name'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'], ['hours', 'Opening hours'], ['address', 'Address'], ['city', 'City'], ['instagram', 'Instagram']];
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:900px">
      <form class="cardp" data-form="facts"><h3>Business details</h3><p class="mut sm">Used on every page. A change here is used in the next version; ask in the chat to rebuild now.</p>
        <div class="g2">${fields.map(([k, l]) => `<label class="fld">${esc(l)}<input class="in" name="${k}" value="${esc(S(f[k]))}" autocomplete="off"></label>`).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save details</button></div></form>
      <section class="cardp"><h3>SEO and Google</h3><p class="mut">Page titles, descriptions, sitemap and Search Console are set by Hoola on every build.</p><div class="inl">${studioBtn('Check SEO now', 'Is website ka SEO check karo', false)}</div></section>
      <section class="cardp"><h3>Team</h3><p class="mut">Writers draft, editors review, publishers put live.</p><div class="inl">${studioBtn('Invite a team member', 'Is website ke CMS mein ek team member jodo: ', false)}</div></section>
      <section class="cardp danger"><h3>Take the site down</h3><p class="mut">The site stops answering; your pages, data and versions are kept.</p><div class="inl"><button class="b bad" type="button" data-act="takedown">Take down…</button></div></section></div>`;
  }

  async function historyView(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading versions…</div>';
    let host = null; try { host = await api('GET', `/api/sites/${enc(v.id)}/hosting`); } catch { host = {hosts: []}; }
    if (VIEW !== 'history' || CUR?.id !== v.id) return;
    const live = L(host.hosts).length > 0, vs = L(v.versions);
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:820px"><h2 style="font-size:18px">History</h2>
      <p class="mut">Every change is a checked version. ${live ? 'Bringing back an older version puts it on your live addresses after you confirm.' : 'Restoring opens once the site is live.'}</p>
      ${vs.length ? vs.map(x => `<div class="ver">${pill('v' + S(x.version), Number(x.version) === Number(v.version) ? 'ok' : '')}<span class="sp ell">${esc(S(x.note) || 'Version')} <span class="mut sm">· ${esc(S(x.at).slice(0, 16).replace('T', ' '))}</span></span>
        ${Number(x.version) !== Number(v.version) && live ? `<button class="b sm" type="button" data-act="rollback" data-ver="${esc(S(x.version))}">Restore…</button>` : ''}</div>`).join('') : '<p class="mut">No versions yet.</p>'}</div>`;
  }

  async function publish(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading the addresses…</div>';
    let host = null, moves = null;
    try { host = await api('GET', `/api/sites/${enc(v.id)}/hosting`); } catch (e) { host = {hosts: [], error: e.message}; }
    try { moves = await api('GET', `/api/sites/${enc(v.id)}/moves`); } catch { moves = null; }
    if (VIEW !== 'publish' || CUR?.id !== v.id) return;
    const hosts = L(host.hosts), rows = L(moves?.rows);
    pane.innerHTML = viewsBar() + `<div class="main"><div class="pc2">
      <section class="cardp acc"><h3>Put v${esc(S(v.version || '–'))} live</h3>
        ${hasVersion(v) ? `<p class="mut">Hoola checks the version and the addresses first and shows you what will happen. Nothing goes live until you tap.</p>
          <div class="inl"><button class="b pri" type="button" data-act="launch">Check and go live…</button></div><div id="wsLaunch"></div>` : '<p class="mut">There is nothing to put live yet: pick a look first.</p>'}</section>
      <section class="cardp"><h3>Addresses</h3>${host.error ? `<p class="mut">${esc(host.error)}</p>` : ''}
        ${hosts.length ? hosts.map(h => `<div class="kv"><code class="ell">${esc(S(h.host))}</code>${pill(S(h.stage) || S(h.status), S(h.stage) === 'Live' ? 'ok' : S(h.stage) === 'Offline' ? 'bad' : 'warn')}</div>${h.problem ? `<p class="li bad">${esc(S(h.problem))}</p>` : ''}`).join('') : '<p class="mut">Not live yet. Your free address is made when you first go live.</p>'}</section>
      <section class="cardp"><h3>Connect your domain</h3><p class="mut sm">Hoola gives you the exact records to add, checks them from three places, then sets up HTTPS.</p>
        <form data-form="domain" class="inl"><input class="in" id="wsDom" aria-label="Your domain" placeholder="yourname.in" autocomplete="off" style="flex:1 1 200px"><button class="b" type="submit">Connect</button></form>
        <div class="inl">${studioBtn('Find a domain to buy', 'Is website ke liye achha domain dhoondho', false)}</div></section>
      ${moves ? `<section class="cardp"><div style="display:flex;align-items:center;gap:8px"><h3 class="sp">Old site addresses</h3>${pill(moves.approved ? 'Approved' : `${rows.length} found`, moves.approved ? 'ok' : 'warn')}</div>
        <p class="mut sm">Links and Google results from your old site (${esc(S(moves.from_host))}) open the matching new page (301). Untick any you don't want.</p>
        <form data-form="moves" data-hash="${esc(S(moves.hash))}">${rows.slice(0, 200).map(r => `<label class="mv"><input type="checkbox" name="keep" value="${esc(S(r.old))}" ${r.guess ? '' : 'checked'}><code>${esc(S(r.old))}</code><span aria-hidden="true">→</span><code>${esc(S(r.new))}</code>${pill(S(r.how), r.guess ? 'warn' : '')}</label>`).join('') || '<p class="mut">Every old address already exists on the new site.</p>'}
          ${rows.length ? `<div class="inl" style="justify-content:flex-end;margin-top:8px"><button class="b pri" type="submit">Haan, jod do</button></div>` : ''}</form></section>` : ''}
    </div></div>`;
  }

  async function launch() {
    const out = $('#wsLaunch'); if (!out) return;
    try {
      const card = await api('POST', `/api/sites/${enc(CUR.id)}/launch-request`, {});
      const blk = L(card.blockers);
      out.innerHTML = `<div class="launch"><p class="sm">${esc(S(card.say))}</p>${blk.length ? blk.map(b => `<p class="li bad">${esc(S(b))}</p>`).join('')
        : `<div style="display:flex;flex-wrap:wrap;gap:6px">${L(card.hosts).map(h => `<code>${esc(S(h))}</code>`).join(' ')}</div>
          <div class="inl" style="justify-content:flex-end"><button class="b pri" type="button" data-act="golive" data-hash="${esc(S(card.hash))}">Haan, live karo</button></div>`}</div>`;
    } catch (e) { out.innerHTML = `<p class="li bad">${esc(e.message)}</p>`; }
  }

  /* ---------- polling while the server works ---------- */
  function sig(v) { return [v.status, v.version, M(v.board).pct, M(v.board).now, L(v.looks).length, L(v.looks).map(x => x.full).join(), v.error].join('|'); }
  function startPoll() {
    stopPoll(); SIG = sig(CUR);
    const id = CUR.id;
    POLL = setTimeout(async () => {
      POLL = null;
      if (!CUR || CUR.id !== id) return;
      try {
        const v = await api('GET', `/api/sites/${enc(id)}`);
        if (!CUR || CUR.id !== id) return;
        const changed = sig(v) !== SIG; CUR = v; drawState();
        if (changed && (VIEW === 'preview' || !WORKING(v))) drawPane(); else startPoll();
      } catch { startPoll(); }
    }, 3500);
  }
  function stopPoll() { if (POLL) { clearTimeout(POLL); POLL = null; } }
  async function reload() { if (!CUR) return; try { CUR = await api('GET', `/api/sites/${enc(CUR.id)}`); drawState(); drawPane(); } catch (e) { toast(e.message, true); } }

  /* ---------- the site's own Hoola thread (never the home chat) ---------- */
  async function ensureConv() {
    if (THREAD.conv && THREAD.site === CUR.id) return THREAD.conv;
    THREAD.site = CUR.id;
    let c = store.get(convKey(CUR.id));
    if (c) { try { await api('GET', `/api/conversations/${enc(c)}/messages?limit=1`); } catch { c = ''; } }
    if (!c) { c = await newConv(`Website · ${name(CUR)}`); store.set(convKey(CUR.id), c); }
    THREAD.conv = c;
    return c;
  }
  async function openThread() {
    clearTimeout(THREAD.timer);
    Object.assign(THREAD, {site: CUR.id, conv: store.get(convKey(CUR.id)), rows: [], live: '', sig: '', waiting: false, since: 0});
    drawMsgs();
    if (THREAD.conv) await readThread();
  }
  const clean = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  const md = t => window.HoolaMD ? window.HoolaMD.render(t, false) : `<p>${esc(t)}</p>`;
  function drawMsgs() {
    const box = $('#wsMsgs'); if (!box) return;
    const all = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
    const first = all.findIndex(r => r.role === 'user');
    const rows = first < 0 ? [] : all.slice(first);
    const s = rows.map(r => r.id).join(',') + '|' + THREAD.live.length + '|' + THREAD.waiting;
    if (s === THREAD.sig) return;
    THREAD.sig = s;
    const near = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    box.innerHTML = rows.length || THREAD.waiting ? rows.slice(-40).map(r => r.role === 'user' ? `<div class="me">${esc(clean(r.text))}</div>` : `<div class="ho">${md(S(r.text))}</div>`).join('')
        + (THREAD.waiting ? `<div class="ho">${THREAD.live ? md(THREAD.live) : '<span class="dots" aria-label="Hoola is working"><i></i><i></i><i></i></span>'}</div>` : '')
      : `<div class="ho"><p>${esc(S(CUR?.say) || 'Ask for anything on this website.')}</p></div>
         <div class="mut sm">This chat is only about ${esc(name(CUR || {}))}. It stays here, not in your home chat.</div>
         <div style="display:flex;flex-wrap:wrap;gap:6px">${['Add a shop with cart', 'Add online payments', 'Add a Hindi version', 'Add booking slots'].map(t => `<button class="chip" type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;
    if (near || THREAD.waiting) box.scrollTop = box.scrollHeight;
  }
  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;
      THREAD.rows = L(r.messages);
    } catch { return; }
    if (THREAD.waiting) {
      let snap = null;
      try { const res = await api('GET', `/api/conversations/${enc(c)}/live`, undefined, {raw: true}); if (res.status === 200) snap = await res.json(); } catch {}
      THREAD.live = S(snap?.text);
      const answered = THREAD.rows.some(m => m.role === 'assistant' && Number(m.id) > THREAD.since && S(m.text).trim());
      if (answered && !snap) { THREAD.waiting = false; THREAD.live = ''; reload(); }
      else if (Date.now() - THREAD.started > 15 * 60e3) THREAD.waiting = false;
    }
    drawMsgs();
    if (THREAD.waiting) { clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 1500); }
  }
  async function ask(text) {
    text = S(text).trim(); if (!text || !CUR) return;
    const v = CUR, plan = store.get(MODE_KEY + '.chat') === 'plan';
    try {
      const c = await ensureConv();
      THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      THREAD.rows.push({id: 'local-' + Date.now(), role: 'user', text});
      THREAD.waiting = true; THREAD.started = Date.now(); THREAD.live = ''; drawMsgs();
      const hints = [`Web Studio: this chat is only about website ${S(v.number)} "${name(v)}" (site id ${S(v.id)}). Work on THIS website with the website tool; never start a new website unless I ask for one.`];
      if (plan) hints.push('Plan mode: reply with a short plan for this change (what changes, what stays the same, anything you need from me) and change NOTHING until I say Haan.');
      await api('POST', `/api/conversations/${enc(c)}/messages`, {text, client_id: 'ws-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8), hints});
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 900);
    } catch (e) { THREAD.waiting = false; drawMsgs(); toast(e.message, true); }
  }

  /* ---------- small dialog ---------- */
  function dialog(title, inner) {
    return new Promise(resolve => {
      const d = document.createElement('dialog'); d.className = 'dlg';
      d.innerHTML = `<form method="dialog"><b style="font-size:16px">${esc(title)}</b>${inner}<div class="inl" style="justify-content:flex-end"><button class="b" value="cancel" type="submit">Cancel</button><button class="b pri" value="ok" type="submit">OK</button></div></form>`;
      document.body.appendChild(d);
      d.addEventListener('close', () => { const ok = d.returnValue === 'ok'; const fd = ok ? new FormData(d.querySelector('form')) : null; d.remove(); resolve(fd); });
      d.showModal();
    });
  }
  async function editSend(body) {
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/edit`, body); toast(S(r?.say) || 'Saved.'); }
    catch (e) { toast(e.message, true); }
    const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src;
  }
  async function upload(kind, file, about) {
    const fd = new FormData(); fd.append('file', file); fd.append('about', about || '');
    const r = await api('POST', `/api/sites/${enc(CUR.id)}/${kind === 'photo' ? 'photo' : 'media'}`, undefined, {form: fd});
    return S(r.name);
  }
  addEventListener('message', async ev => {
    const d = ev.data;
    if (!d || d.hoola !== 'edit' || !CUR || !EDIT) return;
    const fr = APP.querySelector('.frame iframe'); if (!fr || ev.source !== fr.contentWindow) return;   // only our own preview
    const k = S(d.k), e = S(d.e);
    if (d.t === 'text') return editSend({k, e, op: 'text', value: S(d.value)});
    if (d.t === 'remove') { if (confirm(`Remove "${S(d.text).slice(0, 60)}" from the page? (Undo brings it back)`)) editSend({k, e, op: 'remove'}); return; }
    if (d.t === 'link') {
      const f = await dialog('Link', `<label class="fld">Where should "${esc(S(d.text).slice(0, 40))}" go?<input class="in" name="href" value="${esc(S(d.href))}" placeholder="https://… · tel:+91… · contact/"></label>`);
      if (f) editSend({k, e, op: 'link', value: S(f.get('href')).trim()}); return;
    }
    if (d.t === 'image') {
      const ph = L(CUR.photos);
      const f = await dialog('Change the picture', `${ph.length ? `<label class="fld">Use one of your photos<select class="in" name="pick"><option value="">—</option>${ph.map(p => `<option value="${esc(S(p))}">${esc(S(p))}</option>`).join('')}</select></label>` : ''}
        <label class="fld">${ph.length ? 'Or upload' : 'Upload'} a photo (JPEG, PNG, WebP)<input type="file" name="file" accept="image/jpeg,image/png,image/webp"></label>`);
      if (!f) return;
      let pick = S(f.get('pick')); const file = f.get('file');
      try { if (file && file.size) pick = await upload('photo', file, ''); } catch (er) { return toast(er.message, true); }
      if (pick && pick !== S(d.img)) editSend({k, e, op: 'image', value: pick}); return;
    }
    if (d.t === 'add') {
      const f = await dialog('Add below this', `<label class="fld">What<select class="in" name="kind"><option value="photo">Photo</option><option value="video">Video (MP4)</option><option value="audio">Audio</option><option value="file">Download file</option><option value="youtube">YouTube link</option></select></label>
        <label class="fld">File<input type="file" name="file"></label><label class="fld">YouTube link<input class="in" name="url" placeholder="https://youtu.be/…"></label>
        <label class="fld">Caption (optional)<input class="in" name="caption" maxlength="160"></label>`);
      if (!f) return;
      const kind = S(f.get('kind')), spec = {kind, caption: S(f.get('caption')).trim()};
      try {
        if (kind === 'youtube') { spec.url = S(f.get('url')).trim(); if (!spec.url) return toast('Paste the YouTube link.', true); }
        else { const file = f.get('file'); if (!file || !file.size) return toast('Choose a file to add.', true); spec.name = await upload(kind, file, spec.caption); }
      } catch (er) { return toast(er.message, true); }
      return editSend({k, e, op: 'insert', value: JSON.stringify(spec)});
    }
    if (d.t === 'ai') { const t = $('#wsTh'); if (t) { t.value = `"${S(d.text).slice(0, 80)}" ko `; t.focus(); } }
  });

  /* ================= events ================= */
  APP.addEventListener('click', async e => {
    const b = e.target.closest('button, a'); if (!b || !APP.contains(b)) return;
    const d = b.dataset;
    if (d.mode) { store.set(MODE_KEY, d.mode); APP.querySelectorAll('[data-mode]').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.mode === d.mode)));
      const n = $('#wsModeNote'); if (n) n.textContent = d.mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: 3 full looks first'; return; }
    if (d.cmode) { store.set(MODE_KEY + '.chat', d.cmode); APP.querySelectorAll('[data-cmode]').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.cmode === d.cmode))); return; }
    if (d.type) { if (location.hash && location.hash !== '#/') { PREFILL = `${d.type} ki website banao: `; go('#/'); return; }
      const t = $('#wsAsk'); if (t) { t.value = `${d.type} ki website banao: `; t.focus(); t.setSelectionRange(t.value.length, t.value.length); } return; }
    if (d.src) { if (d.src === 'focus') { drawSource(''); $('#wsAsk')?.focus(); } else { drawSource(d.src); $('#wsSrc input')?.focus(); } return; }
    if (d.view) { VIEW = d.view; EDIT = false; history.replaceState(null, '', `#/site/${enc(CUR.id)}/${VIEW}`); drawPane(); return; }
    if (d.dev) { DEVICE = d.dev; drawPane(); return; }
    if (d.look) { LOOK = Number(d.look) || 0; drawPane(); return; }
    if (d.file) { openFile(d.file); return; }
    if (d.coll) { openColl(d.coll); return; }
    if (d.ask != null && d.ask !== '') {
      if (d.ask.endsWith(': ')) { const t = $('#wsTh'); if (t) { t.value = d.ask; t.focus(); } return; }
      ask(d.ask); return;
    }
    const act = d.act; if (!act) return;
    if (act === 'new') { if (location.hash && location.hash !== '#/') go('#/'); else $('#wsAsk')?.focus(); return; }
    if (act === 'reload') { const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src; return; }
    if (act === 'select') {
      if (!CUR || !hasVersion(CUR)) return toast('Selecting on the page opens once the first version is built.', true);
      VIEW = 'preview';
      try { await api('POST', `/api/sites/${enc(CUR.id)}/edit-mode`, {}); EDIT = true; drawPane(); } catch (er) { toast(er.message, true); }
      return;
    }
    if (act === 'edit-done') { EDIT = false; await reload(); return; }
    if (BUSY) return;
    const id = CUR ? enc(CUR.id) : '';
    BUSY = true; b.setAttribute('aria-disabled', 'true');
    try {
      if (act === 'approve') { await api('POST', `/api/sites/${id}/plan`, {conversation_id: await ensureConv().catch(() => '')}); toast('Making three complete looks.'); await reload(); }
      else if (act === 'pick-look') {
        await api('POST', `/api/sites/${id}/look`, {index: LOOK, conversation_id: await ensureConv().catch(() => '')});
        toast('Building your website in this look.'); await reload();
      } else if (act === 'approve-plan') {
        const pid = parts()[1];
        const conv = store.get('hoola.ws.spec.conv.' + pid);
        const r = await api('POST', `/api/site-architect/${enc(pid)}/approve`, {hash: d.hash, conversation_id: conv});
        await loadLists();
        const site = SITES.find(x => S(x.id) === S(r.site) || S(x.number) === S(r.number));
        if (site && conv) store.set(convKey(site.id), conv);
        toast(S(r.say).slice(0, 160) || 'Building the plan.');
        go(site ? '#/site/' + enc(S(site.id)) : '#/sites');
      } else if (act === 'use-design') {
        const brief = S($('#wsAsk')?.value).trim();
        const r = await api('POST', '/api/site-design/use', {token: d.token, keep: d.keep === '1', brief});
        toast(S(r.say).slice(0, 160) || 'Design added.');
        if (r.site) go('#/site/' + enc(S(r.site)));
      } else if (act === 'delete') {
        if (!confirm(`Delete ${name(CUR)}? Nothing has been built yet.`)) return;
        await api('DELETE', `/api/sites/${id}`); toast('Deleted.'); go('#/');
      } else if (act === 'resume') { await api('POST', `/api/sites/${id}/resume`, {}); toast('Building again.'); await reload(); }
      else if (act === 'stop') { await api('POST', `/api/sites/${id}/stop`, {}); toast('Pausing after the current part.'); await reload(); }
      else if (act === 'undo') { const r = await api('POST', `/api/sites/${id}/undo`, {}); toast(S(r?.say) || 'Undone.'); const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src; }
      else if (act === 'export') { const r = await api('POST', `/api/sites/${id}/export`, {format: d.fmt}); toast(S(r.say) || 'Ready: it is in your files.'); }
      else if (act === 'launch') await launch();
      else if (act === 'golive') {
        if (!confirm(`Put ${name(CUR)} v${S(CUR.version)} live now?`)) return;
        const r = await api('POST', `/api/sites/${id}/launch`, {hash: d.hash}); toast(S(r.say) || 'Live.'); await reload();
      } else if (act === 'rollback') {
        const card = await api('POST', `/api/sites/${id}/rollback-request`, {version: Number(d.ver)});
        if (!confirm(S(card.say) || `Bring back v${d.ver} on your live addresses?`)) return;
        const r = await api('POST', `/api/sites/${id}/rollback`, {version: Number(d.ver), hash: S(card.hash)}); toast(S(r.say) || 'Restored.'); await reload();
      } else if (act === 'takedown') {
        if (!confirm(`Take ${name(CUR)} off the internet? Your pages, data and versions are kept.`)) return;
        const r = await api('POST', `/api/sites/${id}/takedown`, {}); toast(S(r.say) || 'Taken down.'); await reload();
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (b.isConnected) b.removeAttribute('aria-disabled'); }
  });

  APP.addEventListener('keydown', e => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    if (e.target.matches?.('#wsAsk, #wsTh, #wsRev')) { e.preventDefault(); e.target.form?.requestSubmit(); }
  });

  APP.addEventListener('submit', async e => {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form;
    if (kind === 'thread') { const t = f.querySelector('textarea'); const x = S(t.value).trim(); if (!x) return; t.value = ''; return ask(x); }
    if (BUSY) return;
    const btn = f.querySelector('[type=submit]');
    BUSY = true; if (btn) btn.disabled = true;
    try {
      if (kind === 'ask') { const t = S(f.querySelector('textarea').value).trim(); if (!t) return toast('Write one line about the website.', true); await startFromAsk(t); }
      else if (kind === 'old' || kind === 'shot') await readDesign(f, kind);
      else if (kind === 'revise') {
        const t = S(f.querySelector('textarea').value).trim(); if (!t) return;
        const pid = parts()[1];
        CARD = await api('POST', `/api/site-architect/${enc(pid)}/revise`, {words: t});
        const key = 'hoola.ws.spec.log.' + pid;
        let log = []; try { log = JSON.parse(sessionStorage.getItem(key) || '[]'); } catch {}
        log.push({me: t, done: 'Plan updated'}); try { sessionStorage.setItem(key, JSON.stringify(log.slice(-20))); } catch {}
        await openPlan(pid);
      } else if (kind === 'code') {
        const path = f.dataset.path, codeText = S(f.querySelector('textarea').value);
        const r = await api('PUT', `/api/sites/${enc(CUR.id)}/code`, {path, code: codeText}); toast(S(r?.say) || 'Saved as a new version.');
      } else if (kind === 'facts') {
        const answers = {}; new FormData(f).forEach((val, key) => { const x = S(val).trim(); if (x && x !== S(M(CUR.facts)[key])) answers[key] = x; });
        if (!Object.keys(answers).length) return toast('Nothing changed.');
        await api('POST', `/api/sites/${enc(CUR.id)}/answers`, {answers}); toast('Details saved.'); await reload();
      } else if (kind === 'domain') {
        const dom = S(f.querySelector('input').value).trim(); if (!dom) return toast('Write the domain first.', true);
        const r = await api('POST', `/api/sites/${enc(CUR.id)}/domain`, {domain: dom}); toast(S(r.say) || 'Domain added: follow the records shown.'); await reload();
      } else if (kind === 'moves') {
        const keep = new Set([...f.querySelectorAll('input[name=keep]:checked')].map(x => x.value));
        const drop = [...f.querySelectorAll('input[name=keep]')].map(x => x.value).filter(x => !keep.has(x));
        if (!confirm(`Send ${keep.size} old address(es) to their new pages?`)) return;
        const r = await api('POST', `/api/sites/${enc(CUR.id)}/moves`, {hash: f.dataset.hash, drop}); toast(S(r.say) || 'Saved.'); await reload();
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (btn?.isConnected) btn.disabled = false; }
  });

  route();
})();
