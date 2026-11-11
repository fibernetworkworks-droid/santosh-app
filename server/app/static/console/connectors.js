/* v0.774 CONNECTORS PAGE (owner: "LETS WORK ON CONNECTOR IN WEB CONSOLE --- CURRENTLY IT IS ONLY AT APP SIDE" ->
   "GO BUILD FULL CONNECTORS PAGE -- MAKE IT MORE PREMIUM, PROFESSIONAL AND ADVANCE AND A SHORT 1 LINER BELOW EVERY
   CONNECTOR -- AS WE USE COMPOSIO FOR THIS").

   The phone's Connect tab (bazar_screen.dart + mcp_screen.dart + publicapis_screen.dart) as one console page:
     Apps         - Composio's ~1,600 apps: search, categories, Connect (her own sign-in page) / Add key / Remove
     Connected    - everything she has linked, in one place
     MCP servers  - the featured official servers, her own servers (tools on / off / ask first, key, remove),
                    add a server by address, the worldwide directory (when the server has it on)
     Built in     - Hoola's own plugins and linked accounts (Swiggy, IndiaMART...)
     Public APIs  - the free API catalogue, a key saved for the ones that need one
     Limits       - spending limits (auto-approve) and delivery details
   Every card carries the server's one-line `line` (bazar/oneline.py) under its name.

   Laws kept from the phone: keys are typed HERE and go straight to the server (sealed there, never shown again,
   never in chat); a sign-in opens the app's own page in a window, and the sign-in done page (bazar/donepage.py)
   tells this tab through BroadcastChannel / localStorage, so the console refreshes by itself; every server value
   goes through esc(); no inline handlers (the console CSP is script-src 'self'). Talks only to routes the phone
   already uses. */
'use strict';
window.HoolaConnectors = function ({api, esc, toast, say}) {
  const TABS = [['apps', 'Apps'], ['connected', 'Connected'], ['mcp', 'MCP servers'], ['builtin', 'Built in'], ['apis', 'Public APIs'], ['limits', 'Limits & safety']];
  const LS_TAB = 'hoola.connectors.tab', LS_PENDING = 'hoola.connect.pending';
  let ROOT = null, TAB = 'apps';
  try { const t = localStorage.getItem(LS_TAB); if (TABS.some(([k]) => k === t)) TAB = t; } catch {}

  const S = {
    apps: {list: [], total: 0, all: 0, q: '', cat: '', show: 'all', cats: [], live: false, configured: true, calls: 0, cap: 0, loaded: false, ctl: null},
    joined: [],                 // her Composio apps (ready / pending), for Connected + the count
    feat: [], mine: [], conn: [], cat: null, settings: null,
    dir: {q: '', list: [], note: '', stats: null},
    apis: {q: '', cat: '', auth: 'any', list: [], count: 0, cats: [], ctl: null},
    built: {q: '', show: 'all', open: new Set()},
    loaded: {mcp: false, builtin: false, apis: false, limits: false, connected: false},
  };

  /* ------------------------------------------------------------------ small helpers */
  const $ = (sel, el = ROOT) => el && el.querySelector(sel);
  const n0 = n => Number(n || 0).toLocaleString('en-IN');
  const slugOf = s => String(s || '').replace(/[^a-z0-9_-]/gi, '');
  const ICON = {
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
    plug: '<path d="M9 7V3M15 7V3M7 7h10v4a5 5 0 0 1-10 0zM12 16v5"/>',
    check: '<path d="M5 12.5l4.2 4.2L19 7"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M15 8l2 2"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.4-8 9-4.6-.6-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    more: '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>',
    spark: '<path d="M12 3l2.2 5.4L20 10.5l-5.8 2.1L12 18l-2.2-5.4L4 10.5l5.8-2.1z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    server: '<rect x="4" y="4" width="16" height="7" rx="2"/><rect x="4" y="13" width="16" height="7" rx="2"/><path d="M8 7.5h.01M8 16.5h.01"/>',
    tools: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
  };
  const ic = (k, sz = 16) => `<svg class="cx-ic" width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const logo = (src, name, big) => `<span class="cx-logo${big ? ' big' : ''}${src ? '' : ' mono'}" data-mono="${esc(String(name || '?').trim().charAt(0).toUpperCase() || '?')}">${src ? `<img src="${esc(src)}" alt="" loading="lazy" decoding="async">` : ''}</span>`;
  const line = x => esc(x.line || x.does || x.desc || '');
  const more = x => !!x.does && String(x.does).length > String(x.line || '').replace(/…$/, '').length + 12;   // the full text only when it says more

  // one pill for every state the server can answer, in plain words
  const STATE = {
    ready: ['ok', 'Connected'], core: ['ok', 'Built in'], pending: ['warn', 'Waiting for sign-in'],
    needs_link: ['', ''], needs_key: ['', ''], needs_setup: ['mute', 'Not available yet'],
    not_configured: ['mute', 'Not on this server'], no_shop_yet: ['mute', 'Add from the phone'], demo: ['mute', 'Demo'],
    no_device: ['mute', 'Needs a device'], pc_not_paired: ['mute', 'Needs your PC'], pc_offline: ['mute', 'PC offline'],
    not_connected: ['mute', 'Not linked'], expired: ['bad', 'Sign-in expired'], error: ['bad', 'Not reachable'], auth: ['warn', 'Needs sign-in'],
  };
  const pill = st => { const p = STATE[st]; return p && p[1] ? `<span class="cx-pill ${p[0]}">${p[0] === 'ok' ? '<i></i>' : ''}${esc(p[1])}</span>` : ''; };

  function busy(btn, on, label) {
    if (!btn) return;
    if (on) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.classList.add('busy'); btn.innerHTML = `<span class="cx-spin" aria-hidden="true"></span>${esc(label || 'Working…')}`; }
    else { btn.disabled = false; btn.classList.remove('busy'); if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
  }
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  /* ------------------------------------------------------------------ the sign-in window + the done signal */
  let WATCH = null;   // {name, kind, until}
  function preopen() {   // opened inside the click, so no popup blocker; the address comes after the server answers
    const w = window.open('', 'hoola-connect', 'popup,width=560,height=760');
    try { if (w) { w.document.title = 'Connecting…'; w.document.body.style.cssText = 'font:15px system-ui;display:grid;place-items:center;height:100vh;margin:0;color:#5C5C63'; w.document.body.textContent = 'Opening the sign-in page…'; } } catch {}
    return w;
  }
  function signin(w, url, name, kind) {
    try { localStorage.setItem(LS_PENDING, String(Date.now())); } catch {}
    if (w && !w.closed) w.location.href = url; else w = window.open(url, 'hoola-connect', 'popup,width=560,height=760');
    if (!w) { toast('Your browser blocked the sign-in window. Allow pop-ups for Hoola and try again.', true); return; }
    WATCH = {name, kind, until: Date.now() + 20 * 60 * 1000};
    toast(`Sign in to ${name} in the new window. This page updates by itself.`);
  }
  async function onDone(m) {
    if (!m || m.type !== 'connector-done') return;
    const name = m.name || WATCH?.name || 'The app';
    WATCH = null;
    toast(m.ok ? `${name} is connected.` : `${name} was not connected.`, !m.ok);
    await refreshAll();
  }
  try { new BroadcastChannel('hoola-connect').onmessage = e => onDone(e.data); } catch {}
  window.addEventListener('storage', e => { if (e.key === 'hoola.connect.done' && e.newValue) { try { onDone(JSON.parse(e.newValue)); } catch {} } });
  window.addEventListener('focus', () => { if (WATCH && Date.now() < WATCH.until && ROOT && ROOT.isConnected) refreshAll(); });

  /* ------------------------------------------------------------------ modal + drawer */
  let MODAL = null, DRAWER = null;
  function closeModal(v) { if (!MODAL) return; const m = MODAL; MODAL = null; m.el.remove(); m.done(v); }
  function modal({title, sub, body, ok = 'Save', danger = false, wide = false, onOk}) {
    closeModal(null);
    return new Promise(done => {
      const el = document.createElement('div');
      el.className = 'cx-modal';
      el.innerHTML = `<div class="cx-scrim" data-cx="close"></div><div class="cx-dialog${wide ? ' wide' : ''}" role="dialog" aria-modal="true" aria-label="${esc(title)}">
        <div class="cx-dhead"><div><h2>${esc(title)}</h2>${sub ? `<p>${sub}</p>` : ''}</div><button class="cx-iconbtn" data-cx="close" aria-label="Close">${ic('x')}</button></div>
        <div class="cx-dbody">${body || ''}</div><div class="cx-derr" role="alert"></div>
        ${ok ? `<div class="cx-dfoot"><button class="cx-btn ghost" data-cx="close">Cancel</button><button class="cx-btn ${danger ? 'danger' : 'pri'}" data-cx="ok">${esc(ok)}</button></div>` : ''}</div>`;
      document.body.appendChild(el);
      MODAL = {el, done};
      const first = el.querySelector('input,select,textarea,button[data-cx="ok"]'); if (first) setTimeout(() => first.focus(), 30);
      el.addEventListener('click', async e => {
        const a = e.target.closest('[data-cx]'); if (!a) return;
        if (a.dataset.cx === 'close') return closeModal(null);
        if (a.dataset.cx !== 'ok') return;
        const err = el.querySelector('.cx-derr'); err.textContent = '';
        try { busy(a, true, 'Saving…'); const v = onOk ? await onOk(el) : true; if (v !== false) closeModal(v ?? true); }
        catch (x) { err.textContent = x.message || String(x); }
        finally { if (MODAL && MODAL.el === el) busy(a, false); }
      });
      el.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeModal(null);
        if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); el.querySelector('[data-cx="ok"]')?.click(); }
      });
    });
  }
  const confirmBox = (title, text, ok = 'Remove') => modal({title, body: `<p class="cx-p">${esc(text)}</p>`, ok, danger: true});
  const field = (name, label, {type = 'text', value = '', hint = '', ph = '', req = false} = {}) => `<label class="cx-field"><span>${esc(label)}${req ? ' <b>*</b>' : ''}</span>
    <input name="${esc(name)}" type="${type}" value="${esc(value)}" placeholder="${esc(ph)}" autocomplete="${type === 'password' ? 'new-password' : 'off'}" spellcheck="false">${hint ? `<small>${esc(hint)}</small>` : ''}</label>`;
  const check = (name, label, on, hint = '') => `<label class="cx-check"><input type="checkbox" name="${esc(name)}" ${on ? 'checked' : ''}><span><b>${esc(label)}</b>${hint ? `<small>${esc(hint)}</small>` : ''}</span></label>`;
  const val = (el, n) => (el.querySelector(`[name="${CSS.escape(n)}"]`)?.value || '').trim();
  const on = (el, n) => !!el.querySelector(`[name="${CSS.escape(n)}"]`)?.checked;
  const KEYNOTE = `<div class="cx-note">${ic('shield', 15)}<span>Sealed on the server and never shown again. Hoola never asks for a key in chat.</span></div>`;

  function closeDrawer() { if (DRAWER) { DRAWER.remove(); DRAWER = null; } }
  function drawer(html) {
    closeDrawer();
    const el = document.createElement('div');
    el.className = 'cx-drawer';
    el.innerHTML = `<div class="cx-scrim" data-cd="close"></div><aside class="cx-panel" role="dialog" aria-modal="true">${html}</aside>`;
    document.body.appendChild(el);
    DRAWER = el;
    el.addEventListener('keydown', e => { if (e.key === 'Escape') closeDrawer(); });
    el.addEventListener('error', fixLogo, true);
    setTimeout(() => el.querySelector('.cx-panel button')?.focus(), 30);
    return el;
  }
  function fixLogo(e) {   // a logo that does not load becomes the app's initial on a soft tile
    const img = e.target; if (!(img instanceof HTMLImageElement)) return;
    const box = img.closest('.cx-logo'); if (box) { box.classList.add('mono'); img.remove(); }
  }

  /* ------------------------------------------------------------------ loading */
  async function loadApps(more) {
    const A = S.apps;
    if (A.ctl) A.ctl.abort();
    A.ctl = new AbortController();
    const off = more ? A.list.length : 0;
    const qs = new URLSearchParams({q: A.q, category: A.cat, offset: String(off), limit: '48'});
    try {
      const r = await api('GET', '/api/composio/apps?' + qs, undefined, {signal: A.ctl.signal});
      A.list = more ? A.list.concat(r.apps || []) : (r.apps || []);
      Object.assign(A, {total: r.total || 0, all: r.all || A.all, live: !!r.live, configured: r.configured !== false,
                        calls: r.calls_this_month || 0, cap: r.monthly_cap || 0, loaded: true});
      if ((r.categories || []).length) A.cats = r.categories;
      if (!A.q && !A.cat && !more) S.joined = A.list.filter(a => a.status === 'ready' || a.status === 'pending');
    } catch (e) { if (e.name !== 'AbortError') { A.loaded = true; A.error = e.message; } }
  }
  async function loadMcp() {
    const [f, m] = await Promise.allSettled([api('GET', '/api/bazar/mcp/featured'), api('GET', '/api/bazar/mcp')]);
    S.feat = f.status === 'fulfilled' ? f.value.connectors || [] : S.feat;
    S.mine = m.status === 'fulfilled' ? m.value.servers || [] : S.mine;
    S.mcpErr = f.status === 'rejected' ? (f.reason?.message || 'The list did not load.') : '';
    S.loaded.mcp = !S.mcpErr;                       // a failed list is asked again next time, never shown as empty
  }
  async function loadBuiltin() {
    const [c, k] = await Promise.allSettled([api('GET', '/api/bazar/catalog'), api('GET', '/api/bazar/connections')]);
    S.cat = c.status === 'fulfilled' ? c.value : (S.cat || {packs: [], total: 0});
    S.conn = k.status === 'fulfilled' ? k.value.apps || [] : S.conn;
    S.builtErr = c.status === 'rejected' ? (c.reason?.message || 'The list did not load.') : '';
    S.loaded.builtin = !S.builtErr;
  }
  async function loadApis() {
    const P = S.apis;
    if (P.ctl) P.ctl.abort();
    P.ctl = new AbortController();
    const qs = new URLSearchParams({q: P.q, cat: P.cat, auth: P.auth});
    try {
      const r = await api('GET', '/api/publicapis?' + qs, undefined, {signal: P.ctl.signal});
      P.list = r.results || []; P.count = r.count || 0; P.total = r.total || 0;
      if ((r.categories || []).length) P.cats = r.categories;
    } catch (e) { if (e.name !== 'AbortError') P.error = e.message; }
    S.loaded.apis = true;
  }
  async function loadLimits() {
    try { S.settings = await api('GET', '/api/bazar/settings'); } catch (e) { S.settings = {error: e.message}; }
    S.loaded.limits = true;
  }
  async function refreshAll() {
    const jobs = [loadApps(false)];
    if (S.loaded.mcp || TAB === 'mcp' || TAB === 'connected') jobs.push(loadMcp());
    if (S.loaded.builtin || TAB === 'builtin' || TAB === 'connected') jobs.push(loadBuiltin());
    await Promise.all(jobs);
    if (ROOT && ROOT.isConnected) { drawHead(); drawBody(); }
  }

  /* ------------------------------------------------------------------ the frame */
  function connectedCount() {
    const feat = S.feat.filter(f => f.status === 'ready').length;
    const own = S.mine.filter(m => !String(m.directory_ref || '').startsWith('featured:') && m.status === 'ready').length;
    const linked = S.conn.filter(c => c.status === 'ready' && !c.custom && !c.no_login).length;
    return S.joined.filter(a => a.status === 'ready').length + feat + own + linked;
  }
  function drawHead() {
    const A = S.apps, c = connectedCount();
    const meter = A.cap ? Math.min(100, Math.round(A.calls * 100 / A.cap)) : 0;
    $('.cx-stats').innerHTML = `
      <div class="cx-stat"><b>${n0(c)}</b><span>Connected</span></div>
      <div class="cx-stat"><b>${A.all ? n0(A.all) : '—'}</b><span>Apps available</span></div>
      <div class="cx-stat wide"><b>${n0(A.calls)}<em> / ${A.cap ? n0(A.cap) : '—'}</em></b><span>App actions this month</span>
        <div class="cx-meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${meter}" aria-label="App actions used this month"><i style="width:${meter}%"></i></div></div>`;
    ROOT.querySelectorAll('.cx-tab').forEach(b => {
      b.setAttribute('aria-selected', String(b.dataset.tab === TAB));
      b.tabIndex = b.dataset.tab === TAB ? 0 : -1;
      if (b.dataset.tab === 'connected') b.querySelector('.cx-count').textContent = c ? String(c) : '';
    });
  }
  function frame() {
    ROOT.innerHTML = `<div class="cx">
      <header class="cx-hero">
        <div class="cx-hero-t">
          <div class="cx-eyebrow">${ic('plug', 14)}<span>Connectors</span></div>
          <h1>Your apps, worked by Hoola</h1>
          <p>Link the accounts you already use. Hoola reads and works inside them, and asks you before it sends, changes, deletes or pays.</p>
        </div>
        <div class="cx-stats" aria-live="polite"></div>
      </header>
      <div class="cx-tabs" role="tablist" aria-label="Connector sections">
        ${TABS.map(([k, n]) => `<button class="cx-tab" role="tab" data-tab="${k}" aria-selected="${k === TAB}">${esc(n)}<span class="cx-count"></span></button>`).join('')}
      </div>
      <div class="cx-body" role="tabpanel"></div>
    </div>`;
  }
  async function drawBody() {
    const body = $('.cx-body'); if (!body) return;
    const need = {mcp: 'mcp', builtin: 'builtin', apis: 'apis', limits: 'limits'}[TAB];
    if (TAB === 'connected' && (!S.loaded.mcp || !S.loaded.builtin)) {
      body.innerHTML = skeleton(6);
      await Promise.all([S.loaded.mcp ? 0 : loadMcp(), S.loaded.builtin ? 0 : loadBuiltin()]);
      drawHead();
    } else if (need && !S.loaded[need]) {
      body.innerHTML = TAB === 'limits' ? skeleton(2) : skeleton(9);
      await {mcp: loadMcp, builtin: loadBuiltin, apis: loadApis, limits: loadLimits}[need]();
      if (TAB === 'mcp' || TAB === 'builtin') drawHead();
    } else if (TAB === 'apps' && !S.apps.loaded) {
      body.innerHTML = appsBar() + skeleton(12);
      await loadApps(false); drawHead();
    }
    if (!body.isConnected) return;
    body.innerHTML = {apps: appsView, connected: connectedView, mcp: mcpView, builtin: builtinView, apis: apisView, limits: limitsView}[TAB]();
  }
  const skeleton = n => `<div class="cx-grid">${Array.from({length: n}, () => '<div class="cx-card sk"><span></span><span></span><span></span></div>').join('')}</div>`;

  /* ------------------------------------------------------------------ Apps (Composio) */
  function appAction(a) {
    const k = esc(a.toolkit);
    switch (a.status) {
      case 'ready': return `<button class="cx-btn soft" data-app-open="${k}">Manage</button>`;
      case 'pending': return `<button class="cx-btn soft" data-app-go="${k}">Sign in again</button>`;
      case 'needs_link': return `<button class="cx-btn pri" data-app-go="${k}">Connect</button>`;
      case 'needs_key': return `<button class="cx-btn pri" data-app-go="${k}">${ic('key', 14)}Add key</button>`;
      default: return `<button class="cx-btn ghost" data-app-open="${k}">Details</button>`;
    }
  }
  function appCard(a) {
    const dim = a.status === 'needs_setup' || a.status === 'not_configured';
    return `<article class="cx-card${dim ? ' dim' : ''}${a.status === 'ready' ? ' on' : ''}" data-app="${esc(a.toolkit)}" tabindex="0" aria-label="${esc(a.name)}">
      <div class="cx-ctop">${logo(a.logo, a.name)}<div class="cx-cname"><h3>${esc(a.name)}</h3><span>${esc(a.category || 'App')}</span></div>${pill(a.status)}</div>
      <p class="cx-line">${line(a)}</p>
      <div class="cx-cfoot"><span class="cx-meta">${a.tools ? `${ic('tools', 13)}${n0(a.tools)} actions` : ''}</span>${appAction(a)}</div>
    </article>`;
  }
  function appsBar() {
    const A = S.apps;
    const show = [['all', 'All apps'], ['ready', 'Connected'], ['open', 'Ready to connect']];
    return `<div class="cx-bar">
      <label class="cx-search">${ic('search')}<input id="cxq" type="search" placeholder="Search ${A.all ? n0(A.all) + ' ' : ''}apps: Slack, Notion, Tally, HubSpot…" value="${esc(A.q)}" aria-label="Search apps"></label>
      <div class="cx-seg" role="group" aria-label="Show">${show.map(([k, n]) => `<button data-show="${k}" aria-pressed="${A.show === k}">${n}</button>`).join('')}</div>
    </div>
    ${A.cats.length ? `<div class="cx-chips" role="group" aria-label="Categories"><button class="cx-chip" data-cat="" aria-pressed="${!A.cat}">All</button>${A.cats.slice(0, 24).map(([c, n]) => `<button class="cx-chip" data-cat="${esc(c)}" aria-pressed="${A.cat === c}">${esc(c)}<em>${n0(n)}</em></button>`).join('')}</div>` : ''}`;
  }
  function appsView() { return appsBar() + `<div id="cxres">${appsResults()}</div>`; }
  function appsResults() {
    const A = S.apps;
    if (!A.configured) return empty('plug', 'Apps are switched off on this server', 'Composio is not set up here yet (COMPOSIO_API_KEY). The other sections still work.');
    if (A.error && !A.list.length) return empty('plug', 'Apps did not load', A.error);
    const list = A.list.filter(a => A.show === 'all' || (A.show === 'ready' ? (a.status === 'ready' || a.status === 'pending') : (a.status === 'needs_link' || a.status === 'needs_key')));
    const more = A.list.length < A.total;
    return `<div class="cx-subhead"><span>${A.q || A.cat ? `${n0(A.total)} match${A.total === 1 ? '' : 'es'}` : `${n0(A.total)} apps`}${A.show !== 'all' ? ` · showing ${n0(list.length)} of the ${n0(A.list.length)} loaded` : ''}</span>
      <span class="cx-by">${ic('shield', 13)}Secure sign-in through Composio · you sign in on each app's own page</span></div>`
      + (list.length ? `<div class="cx-grid">${list.map(appCard).join('')}</div>` : empty('search', 'Nothing here yet', A.q ? `No app matches “${A.q}”. Try another name.` : 'Change the filter to see more apps.'))
      + (more ? `<div class="cx-more"><button class="cx-btn ghost" data-more="apps">Show more · ${n0(A.total - A.list.length)} left</button></div>` : '');
  }
  const findApp = k => S.apps.list.find(a => a.toolkit === k) || S.joined.find(a => a.toolkit === k);
  async function appGo(k, btn) {
    const a = findApp(k); if (!a) return;
    const w = a.status === 'needs_link' || a.status === 'pending' ? preopen() : null;
    busy(btn, true, 'Connecting…');
    try {
      const r = await api('POST', `/api/composio/apps/${encodeURIComponent(k)}/connect`);
      if (r.status === 'open_link' && r.url) { a.status = 'pending'; signin(w, r.url, a.name, 'app'); }
      else {
        if (w) w.close();
        if (r.status === 'ready') { a.status = 'ready'; toast(`${a.name} is connected.`); }
        else if (r.status === 'needs_key') await keyForm(a, r.fields || []);
        else toast(r.say || 'This app is not available yet.', true);
      }
    } catch (e) { if (w) w.close(); toast(e.message, true); }
    busy(btn, false);
    await refreshAll();
  }
  async function keyForm(a, fields) {
    if (!fields.length) fields = [{name: 'api_key', label: 'API key', required: true, secret: true}];
    const ok = await modal({
      title: `Connect ${a.name}`, sub: `${esc(a.name)} connects with its own key. It is checked with ${esc(a.name)} straight away.`,
      body: fields.map(f => field(f.name, f.label || f.name, {type: f.secret ? 'password' : 'text', hint: f.hint || '', req: f.required})).join('') + KEYNOTE,
      ok: 'Connect',
      onOk: async el => {
        const values = {};
        for (const f of fields) { const v = val(el, f.name); if (f.required && !v) throw new Error(`${f.label || f.name} is needed.`); if (v) values[f.name] = v; }
        const r = await api('POST', `/api/composio/apps/${encodeURIComponent(a.toolkit)}/key`, {values});
        if (r.status !== 'ready') throw new Error(r.say || 'The key was not accepted.');
        return true;
      }});
    if (ok) toast(`${a.name} is connected.`);
  }
  async function appRemove(a) {
    if (!await confirmBox(`Remove ${a.name}?`, `Hoola will stop working in your ${a.name} account. You can connect it again any time.`)) return;
    try { await api('DELETE', `/api/composio/apps/${encodeURIComponent(a.toolkit)}`); toast(`${a.name} removed.`); closeDrawer(); }
    catch (e) { toast(e.message, true); }
    await refreshAll();
  }
  function appDrawer(k) {
    const a = findApp(k); if (!a) return;
    const st = a.status;
    const actions = st === 'ready'
      ? `<button class="cx-btn pri" data-d="try">${ic('chat', 14)}Ask Hoola to use it</button><button class="cx-btn danger ghost" data-d="remove">Remove</button>`
      : st === 'needs_link' || st === 'pending' || st === 'needs_key'
        ? `<button class="cx-btn pri" data-d="go">${st === 'needs_key' ? ic('key', 14) + 'Add key' : st === 'pending' ? 'Sign in again' : 'Connect ' + esc(a.name)}</button>`
        : `<p class="cx-p mute">${st === 'needs_setup' ? 'Newtika has to switch this app on once in Composio before anyone can connect it. Ask your Hoola admin.' : 'Apps are not available on this server right now.'}</p>`;
    const el = drawer(`<div class="cx-phead">${logo(a.logo, a.name, true)}<div><h2>${esc(a.name)}</h2><span>${esc(a.category || 'App')}${a.tools ? ` · ${n0(a.tools)} actions` : ''}</span></div>
        <button class="cx-iconbtn" data-cd="close" aria-label="Close">${ic('x')}</button></div>
      <div class="cx-pbody">
        <div class="cx-prow">${pill(st) || '<span class="cx-pill">Not connected</span>'}<span class="cx-pill">${ic('shield', 12)}via Composio</span></div>
        <p class="cx-lead">${line(a)}</p>
        ${more(a) ? `<p class="cx-p">${esc(a.does)}</p>` : ''}
        <div class="cx-actions">${actions}</div>
        <div class="cx-facts">
          <div>${ic('shield', 15)}<span><b>Your own account.</b> You sign in on ${esc(a.name)}'s official page. Hoola never sees your password; the link is held by Composio for you only.</span></div>
          <div>${ic('check', 15)}<span><b>Reads run straight away.</b> Anything that sends, changes, deletes or pays shows you a card first.</span></div>
          <div>${ic('x', 15)}<span><b>Remove any time.</b> Hoola loses access the moment you remove it.</span></div>
        </div>
        ${st === 'ready' ? `<div class="cx-try"><span>Try saying</span>${tryLines(a.name, a.category).map(t => `<button class="cx-trybtn" data-say="${esc(t)}">${ic('spark', 13)}${esc(t)}</button>`).join('')}</div>` : ''}
      </div>`);
    el.addEventListener('click', async e => {
      if (e.target.closest('[data-cd="close"]')) return closeDrawer();
      const s = e.target.closest('[data-say]'); if (s) { closeDrawer(); say(s.dataset.say); return; }
      const d = e.target.closest('[data-d]')?.dataset.d; if (!d) return;
      if (d === 'go') { closeDrawer(); appGo(a.toolkit, null); }
      if (d === 'remove') appRemove(a);
      if (d === 'try') { closeDrawer(); say(`In ${a.name}, `); }
    });
  }
  function tryLines(name, cat) {
    const c = String(cat || '').toLowerCase();
    if (/crm|sales/.test(c)) return [`Show my latest 10 leads in ${name}`, `Add a follow-up task in ${name} for tomorrow`];
    if (/commun|chat|messag/.test(c)) return [`Summarise today's unread messages in ${name}`, `Draft a message in ${name} for the team`];
    if (/product|note|project|task/.test(c)) return [`List my open tasks in ${name}`, `Create a page in ${name} with today's meeting notes`];
    if (/account|financ|payment|invoic/.test(c)) return [`Show this month's unpaid invoices in ${name}`, `Total sales in ${name} last week`];
    if (/support|help|ticket/.test(c)) return [`Show open tickets in ${name}`, `Draft a reply to the newest ${name} ticket`];
    return [`What can you do in ${name}?`, `Show my latest items in ${name}`];
  }

  /* ------------------------------------------------------------------ Connected */
  function connectedView() {
    const rows = [];
    S.joined.forEach(a => rows.push({kind: 'app', key: a.toolkit, name: a.name, logo: a.logo, line: a.line, st: a.status, sub: (a.category || 'App') + ' · via Composio'}));
    S.feat.filter(f => f.status).forEach(f => rows.push({kind: 'feat', key: f.id, name: f.name, logo: f.logo, line: f.line, st: f.status, sub: f.category + ' · MCP server'}));
    S.mine.filter(m => !String(m.directory_ref || '').startsWith('featured:')).forEach(m => rows.push({kind: 'mine', key: m.pack_id, name: m.name, logo: m.logo, line: m.line, st: m.status, sub: 'Your MCP server'}));
    S.conn.filter(c => !c.custom && (c.status === 'ready' || c.no_login)).forEach(c => rows.push({kind: 'conn', key: c.pack_id, name: c.name, logo: c.logo, line: c.line, st: c.status, sub: c.no_login ? 'Built in · no login' : 'Linked account'}));
    if (!rows.length) return empty('plug', 'Nothing connected yet', 'Connect the apps you use every day: Hoola then reads and works inside them for you.', `<button class="cx-btn pri" data-tab-go="apps">Browse ${S.apps.all ? n0(S.apps.all) + ' ' : ''}apps</button>`);
    return `<div class="cx-subhead"><span>${n0(rows.length)} connection${rows.length === 1 ? '' : 's'}</span><span class="cx-by">${ic('shield', 13)}Remove any connection and Hoola loses access at once</span></div>
      <div class="cx-grid">${rows.map(r => `<article class="cx-card on" tabindex="0" data-cn-kind="${r.kind}" data-cn-key="${esc(r.key)}">
        <div class="cx-ctop">${logo(r.logo, r.name)}<div class="cx-cname"><h3>${esc(r.name)}</h3><span>${esc(r.sub)}</span></div>${pill(r.st)}</div>
        <p class="cx-line">${esc(r.line || '')}</p>
        <div class="cx-cfoot"><span class="cx-meta"></span><button class="cx-btn soft" data-cn-manage>Manage</button></div></article>`).join('')}</div>`;
  }
  function manageConnected(kind, key) {
    if (kind === 'app') return appDrawer(key);
    if (kind === 'feat') { const f = S.feat.find(x => x.id === key); if (f) featDrawer(f); return; }
    if (kind === 'mine') { const m = S.mine.find(x => x.pack_id === key); if (m) serverDrawer(m); return; }
    if (kind === 'conn') { const c = S.conn.find(x => x.pack_id === key); if (c) linkedDrawer(c); }
  }

  /* ------------------------------------------------------------------ MCP servers */
  function featAction(f) {
    const k = esc(f.id);
    if (f.native) return `<span class="cx-pill ok"><i></i>Built in</span>`;
    if (f.auth === 'oauth_partner') return `<span class="cx-pill mute">Partner access pending</span>`;
    if (f.status === 'ready') return `<button class="cx-btn soft" data-feat-open="${k}">Manage</button>`;
    if (f.status === 'needs_link' || f.status === 'auth') return `<button class="cx-btn pri" data-feat-go="${k}">Sign in</button>`;
    if (f.auth === 'api_key') return `<button class="cx-btn pri" data-feat-go="${k}">${ic('key', 14)}Add key</button>`;
    if (f.auth === 'per_user_url') return `<button class="cx-btn pri" data-feat-go="${k}">Connect</button>`;
    return `<button class="cx-btn pri" data-feat-go="${k}">Connect</button>`;
  }
  function featCard(f) {
    const tags = [f.caution ? '<span class="cx-tag warn" title="Money or codes: every action waits for your tap">Asks first</span>' : '',
      f.india ? '<span class="cx-tag">India</span>' : ''].join('');
    return `<article class="cx-card${f.status === 'ready' ? ' on' : ''}${f.auth === 'oauth_partner' ? ' dim' : ''}" data-feat="${esc(f.id)}" tabindex="0">
      <div class="cx-ctop">${logo(f.logo, f.name)}<div class="cx-cname"><h3>${esc(f.name)}</h3><span>${esc(f.category)}</span></div>${pill(f.status)}</div>
      <p class="cx-line">${line(f)}</p>
      <div class="cx-cfoot"><span class="cx-meta">${tags}</span>${featAction(f)}</div></article>`;
  }
  function serverRow(m) {
    return `<div class="cx-row" data-srv="${esc(m.pack_id)}">${logo(m.logo, m.name)}
      <div class="cx-rmain"><h3>${esc(m.name)}</h3><p>${esc(m.line || m.url || '')}</p></div>${pill(m.status)}
      <button class="cx-btn soft" data-srv-open="${esc(m.pack_id)}">Manage</button></div>`;
  }
  function mcpView() {
    const own = S.mine.filter(m => !String(m.directory_ref || '').startsWith('featured:'));
    const cats = [...new Set(S.feat.map(f => f.category))];
    const D = S.dir;
    return `<section class="cx-sec">
        <div class="cx-sechead"><div><h2>Your servers</h2><p>Any MCP server with an https address. Turn each of its tools on or off, or make it ask you first.</p></div>
          <button class="cx-btn pri" data-mcp="add">${ic('plus', 14)}Add a server</button></div>
        ${own.length ? `<div class="cx-rows">${own.map(serverRow).join('')}</div>` : `<div class="cx-emptyline">${ic('server', 16)}<span>No servers of your own yet. Add one by its address, or pick a ready one below.</span></div>`}
      </section>
      <section class="cx-sec">
        <div class="cx-sechead"><div><h2>Official servers</h2><p>Run by the app makers themselves. Most connect with one sign-in.</p></div></div>
        ${cats.map(c => `<h4 class="cx-group">${esc(c)}</h4><div class="cx-grid">${S.feat.filter(f => f.category === c).map(featCard).join('')}</div>`).join('')
          || (S.mcpErr ? empty('server', 'The official servers did not load', S.mcpErr, retryBtn) : empty('server', 'No official servers listed', ''))}
      </section>
      <section class="cx-sec">
        <div class="cx-sechead"><div><h2>Worldwide directory</h2><p>Community MCP servers from npm, PyPI, GitHub lists and more: not individually verified.</p></div></div>
        <label class="cx-search">${ic('search')}<input id="cxdir" type="search" placeholder="Search the MCP directory: weather, invoices, maps…" value="${esc(D.q)}" aria-label="Search the MCP directory"></label>
        <div id="cxdirres">${dirResults()}</div>
      </section>`;
  }
  function dirResults() {
    const D = S.dir;
    if (D.note) return `<div class="cx-emptyline">${ic('server', 16)}<span>${esc(D.note.split(' For apps')[0])} Use <b>Apps</b> for your accounts, or <b>Add a server</b> if you know its address.</span></div>`;
    if (!D.q) return '';
    if (!D.list.length) return `<div class="cx-emptyline">${ic('search', 16)}<span>No server matches “${esc(D.q)}”.</span></div>`;
    return `<div class="cx-rows">${D.list.map((x, i) => `<div class="cx-row">${logo(x.logo, x.name)}
      <div class="cx-rmain"><h3>${esc(x.name)}${x.official ? ' <span class="cx-tag">Official</span>' : ''}${x.verified ? ' <span class="cx-tag">Verified</span>' : ''}</h3><p>${line(x)}</p><small>${esc(x.source || '')}${x.pricing ? ' · ' + esc(x.pricing) : ''}</small></div>
      ${x.mcp_url || x.one_tap ? `<button class="cx-btn pri" data-dir-go="${i}">Connect</button>` : x.link ? `<a class="cx-btn ghost" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer">${ic('ext', 13)}View</a>` : ''}</div>`).join('')}</div>`;
  }
  async function searchDir(q) {
    S.dir.q = q;
    if (!q) { S.dir.list = []; S.dir.note = ''; }
    else {
      try { const r = await api('GET', '/api/bazar/mcp/directory?' + new URLSearchParams({q, limit: '20'})); S.dir.list = r.servers || []; S.dir.note = r.note || ''; }
      catch (e) { S.dir.list = []; S.dir.note = e.message; }
    }
    const box = $('#cxdirres'); if (box) box.innerHTML = dirResults();
  }
  async function afterAdd(r, w, name) {   // what a new MCP server answered: ready, or a sign-in first
    if (r.status === 'needs_link' && r.pack_id) {
      const l = await api('POST', `/api/bazar/connections/${encodeURIComponent(r.pack_id)}/link`);
      signin(w, l.url, name, 'mcp');
      return;
    }
    if (w) w.close();
    if (r.status === 'ready' || !r.status) toast(r.say || `${name} is connected.`);
    else toast(r.say || r.note || `${name}: ${r.status}`, r.status === 'error');
    if (r.note) toast(r.note);
  }
  async function featGo(f, btn) {
    const sign = f.status === 'needs_link' || f.status === 'auth';
    if (!sign && f.auth === 'api_key') return featKey(f);
    if (!sign && f.auth === 'per_user_url') return featUrl(f);
    const w = preopen();
    busy(btn, true, 'Connecting…');
    try {
      if (sign && f.pack_id) { const l = await api('POST', `/api/bazar/connections/${encodeURIComponent(f.pack_id)}/link`); signin(w, l.url, f.name, 'mcp'); }
      else await afterAdd(await api('POST', `/api/bazar/mcp/featured/${encodeURIComponent(f.id)}`, {}), w, f.name);
    } catch (e) { if (w) w.close(); toast(e.message, true); }
    busy(btn, false);
    await loadMcp(); drawHead(); if (TAB === 'mcp' || TAB === 'connected') drawBody();
  }
  async function featKey(f) {
    const kind = (f.options || {}).kind;
    const gh = f.id === 'github', sb = kind === 'supabase';
    let body = `<p class="cx-p">${esc(f.how_to_connect || '')}</p>`;
    if (sb) body += field('project', 'Project ref', {ph: 'abcd1234efgh', hint: 'Dashboard > Project Settings > General. Keep one project so Hoola does not touch the others.'})
      + check('readonly', 'Read-only', true, 'SQL runs as a read-only user. Keep this on in production.')
      + field('key', 'Personal access token (optional)', {type: 'password', ph: 'sbp_…', hint: 'Leave empty to sign in with Supabase instead.'});
    else body += field('key', `${f.name} API key`, {type: 'password', req: true, hint: f.id === 'razorpay' ? 'Format key_id:key_secret (Razorpay Dashboard > API Keys).' : ''});
    if (gh) body += check('readonly', 'Read only', true, 'Hoola will not be able to write or change anything.');
    body += KEYNOTE + (f.docs ? `<a class="cx-link" href="${esc(f.docs)}" target="_blank" rel="noopener noreferrer">${ic('ext', 13)}Where do I find it?</a>` : '');
    let w = null;
    const r = await modal({title: `Connect ${f.name}`, body, ok: 'Connect', onOk: async el => {
      const key = val(el, 'key');
      if (!sb && !key) throw new Error('The key is needed.');
      const payload = {key};
      if (gh || sb) payload.readonly = on(el, 'readonly');
      if (sb) payload.project = val(el, 'project');
      if (sb && !key) w = preopen();
      return api('POST', `/api/bazar/mcp/featured/${encodeURIComponent(f.id)}`, payload);
    }});
    if (r && typeof r === 'object') { try { await afterAdd(r, w, f.name); } catch (e) { toast(e.message, true); } }
    else if (w) w.close();
    await loadMcp(); drawHead(); drawBody();
  }
  async function featUrl(f) {
    const steps = String(f.how_to_connect || '').split(/\s(?=\d\)\s)/).map(s => s.trim()).filter(Boolean);
    const body = `${steps.length > 1 ? `<ol class="cx-steps">${steps.map(s => `<li>${esc(s.replace(/^\d\)\s*/, ''))}</li>`).join('')}</ol>` : `<p class="cx-p">${esc(f.how_to_connect || '')}</p>`}
      ${field('url', 'Your personal MCP address', {req: true, ph: f.url_hint || 'https://…', hint: 'It carries a private key: Hoola keeps it locked and never shows it.'})}${KEYNOTE}`;
    const r = await modal({title: `Connect ${f.name}`, body, ok: 'Connect', wide: true, onOk: async el => {
      const url = val(el, 'url'); if (!/^https:\/\//i.test(url)) throw new Error('Paste the full https address.');
      return api('POST', `/api/bazar/mcp/featured/${encodeURIComponent(f.id)}`, {url});
    }});
    if (r && typeof r === 'object') { try { await afterAdd(r, null, f.name); } catch (e) { toast(e.message, true); } }
    await loadMcp(); drawHead(); drawBody();
  }
  function featDrawer(f) {
    const m = f.pack_id ? S.mine.find(x => x.pack_id === f.pack_id) : null;
    const el = drawer(`<div class="cx-phead">${logo(f.logo, f.name, true)}<div><h2>${esc(f.name)}</h2><span>${esc(f.category)} · official MCP server</span></div>
        <button class="cx-iconbtn" data-cd="close" aria-label="Close">${ic('x')}</button></div>
      <div class="cx-pbody"><div class="cx-prow">${pill(f.status) || '<span class="cx-pill">Not connected</span>'}${f.caution ? '<span class="cx-tag warn">Your tap on every action</span>' : ''}${f.india ? '<span class="cx-tag">India</span>' : ''}</div>
        <p class="cx-lead">${line(f)}</p>${more(f) ? `<p class="cx-p">${esc(f.does)}</p>` : ''}
        ${f.native ? `<p class="cx-p mute">${esc(f.native)}</p>` : ''}
        <div class="cx-actions">${f.pack_id ? `<button class="cx-btn soft" data-d="tools">${ic('tools', 14)}Tools</button>${f.auth === 'api_key' ? `<button class="cx-btn soft" data-d="key">${ic('key', 14)}Change key</button>` : ''}<button class="cx-btn danger ghost" data-d="remove">Remove</button>`
          : f.native || f.auth === 'oauth_partner' ? '' : `<button class="cx-btn pri" data-d="go">Connect ${esc(f.name)}</button>`}
          ${f.docs ? `<a class="cx-btn ghost" href="${esc(f.docs)}" target="_blank" rel="noopener noreferrer">${ic('ext', 13)}Docs</a>` : ''}</div>
        ${f.status === 'ready' ? `<div class="cx-try"><span>Try saying</span>${tryLines(f.name, f.category).map(t => `<button class="cx-trybtn" data-say="${esc(t)}">${ic('spark', 13)}${esc(t)}</button>`).join('')}</div>` : ''}</div>`);
    el.addEventListener('click', async e => {
      if (e.target.closest('[data-cd="close"]')) return closeDrawer();
      const s = e.target.closest('[data-say]'); if (s) { closeDrawer(); say(s.dataset.say); return; }
      const d = e.target.closest('[data-d]')?.dataset.d; if (!d) return;
      if (d === 'go') { closeDrawer(); featGo(f, null); }
      if (d === 'tools') toolsModal(f.pack_id, f.name);
      if (d === 'key') keyChange(f.pack_id, f.name);
      if (d === 'remove') serverRemove(m || {pack_id: f.pack_id, name: f.name});
    });
  }
  function serverDrawer(m) {
    const el = drawer(`<div class="cx-phead">${logo(m.logo, m.name, true)}<div><h2>${esc(m.name)}</h2><span>Your MCP server</span></div>
        <button class="cx-iconbtn" data-cd="close" aria-label="Close">${ic('x')}</button></div>
      <div class="cx-pbody"><div class="cx-prow">${pill(m.status)}${m.caution ? '<span class="cx-tag warn">Your tap on every action</span>' : ''}</div>
        ${m.line ? `<p class="cx-lead">${esc(m.line)}</p>` : ''}<p class="cx-p mono">${esc(m.url || '')}</p>
        <div class="cx-actions">${m.status === 'needs_link' || m.status === 'auth' ? `<button class="cx-btn pri" data-d="link">Sign in</button>` : ''}
          <button class="cx-btn soft" data-d="tools">${ic('tools', 14)}Tools</button><button class="cx-btn soft" data-d="key">${ic('key', 14)}Change key</button>
          <button class="cx-btn danger ghost" data-d="remove">Remove</button></div></div>`);
    el.addEventListener('click', async e => {
      if (e.target.closest('[data-cd="close"]')) return closeDrawer();
      const d = e.target.closest('[data-d]')?.dataset.d; if (!d) return;
      if (d === 'tools') toolsModal(m.pack_id, m.name);
      if (d === 'key') keyChange(m.pack_id, m.name);
      if (d === 'remove') serverRemove(m);
      if (d === 'link') { const w = preopen(); try { const l = await api('POST', `/api/bazar/connections/${encodeURIComponent(m.pack_id)}/link`); signin(w, l.url, m.name, 'mcp'); } catch (x) { if (w) w.close(); toast(x.message, true); } }
    });
  }
  async function serverRemove(m) {
    if (!await confirmBox(`Remove ${m.name}?`, `Hoola will stop using ${m.name}. Its saved key is deleted too.`)) return;
    try { await api('DELETE', `/api/bazar/mcp/${encodeURIComponent(m.pack_id)}`); toast(`${m.name} removed.`); closeDrawer(); }
    catch (e) { toast(e.message, true); }
    await loadMcp(); drawHead(); drawBody();
  }
  async function keyChange(pack, name) {
    await modal({title: `${name}: change key`, body: field('key', 'New key', {type: 'password', req: true}) + field('header', 'Header (optional)', {ph: 'Authorization', hint: 'Only if the server reads the key from a different header.'}) + KEYNOTE,
      ok: 'Save key', onOk: async el => { const key = val(el, 'key'); if (!key) throw new Error('The key is needed.'); await api('PUT', `/api/bazar/mcp/${encodeURIComponent(pack)}/key`, {key, header: val(el, 'header')}); toast('Key saved.'); }});
    await loadMcp(); drawHead(); drawBody();
  }
  async function toolsModal(pack, name) {
    const p = modal({title: `${name}: tools`, sub: 'Turn a tool off and Hoola never uses it. <b>Ask first</b> makes it wait for your yes.', body: '<div class="cx-tools-list"><div class="cx-card sk"><span></span><span></span></div></div>', ok: '', wide: true});
    const box = MODAL.el.querySelector('.cx-tools-list');
    let tools = [];
    try { tools = (await api('GET', `/api/bazar/mcp/${encodeURIComponent(pack)}/tools`)).tools || []; }
    catch (e) { box.innerHTML = `<p class="cx-p bad">${esc(e.message)}</p>`; return p; }
    const draw = () => { box.innerHTML = tools.length ? tools.map((t, i) => `<div class="cx-trow"><div><b>${esc(t.name)}</b><small>${esc(t.description || '')}</small></div>
      <label class="cx-switch" title="Use this tool"><input type="checkbox" data-t="${i}" data-f="enabled" ${t.enabled ? 'checked' : ''}><span></span><em>On</em></label>
      <label class="cx-switch" title="${t.locked ? 'Sends, deletes, pays or shares: always asks you' : 'Wait for your yes'}"><input type="checkbox" data-t="${i}" data-f="ask" ${t.ask ? 'checked' : ''} ${t.locked ? 'disabled' : ''}><span></span><em>Ask first</em></label></div>`).join('')
      : '<p class="cx-p mute">This server lists no tools.</p>'; };
    draw();
    box.addEventListener('change', async e => {
      const i = e.target.dataset.t; if (i === undefined) return;
      const t = tools[+i], f = e.target.dataset.f, v = e.target.checked;
      try { await api('PATCH', `/api/bazar/mcp/${encodeURIComponent(pack)}/tools/${encodeURIComponent(t.name)}`, {[f]: v}); t[f] = v; }
      catch (x) { e.target.checked = !v; toast(x.message, true); }
    });
    return p;
  }
  async function addServer(entry) {
    const r = await modal({title: entry ? `Connect ${entry.name}` : 'Add an MCP server', sub: entry ? esc(entry.how_to_connect || '') : 'Any MCP server reachable on an https address. A key only if the server asks for one.',
      body: field('url', 'Server address', {req: true, value: entry?.mcp_url || '', ph: 'https://example.com/mcp'}) + field('name', 'Name (optional)', {value: entry?.name || ''})
        + field('key', 'API key (optional)', {type: 'password'}) + field('header', 'Key header', {value: 'Authorization'}) + KEYNOTE,
      ok: 'Connect', onOk: async el => {
        const url = val(el, 'url'); if (!/^https:\/\//i.test(url)) throw new Error('Use the full https address.');
        return api('POST', '/api/bazar/mcp', {url, name: val(el, 'name'), ref: entry?.ref || '', key: val(el, 'key'), key_header: val(el, 'header')});
      }});
    if (r && typeof r === 'object') { try { await afterAdd(r, null, r.name || 'The server'); } catch (e) { toast(e.message, true); } }
    await loadMcp(); drawHead(); drawBody();
  }
  async function dirGo(x, btn, keys = {}, accept = false) {
    if (!x.one_tap && x.mcp_url && !Object.keys(keys).length && !accept && !String(x.source || '').startsWith('Apify')) return addServer(x);
    busy(btn, true, 'Checking…');
    let r;
    try { r = await api('POST', '/api/bazar/mcp/one_tap', {ref: x.ref, keys, accept_caution: accept}); }
    catch (e) { busy(btn, false); return x.mcp_url ? addServer(x) : toast(e.message, true); }
    busy(btn, false);
    if (r.status === 'ready') toast(r.say || `${x.name} is connected.`);
    else if (r.status === 'needs_link') { const l = await api('POST', `/api/bazar/connections/${encodeURIComponent(r.pack_id)}/link`); signin(null, l.url, x.name, 'mcp'); }
    else if (r.status === 'needs_keys') {
      const need = r.keys || [];
      const got = await modal({title: `${x.name}: keys`, sub: esc(r.say || 'This server needs these to run.'), body: need.map(k => field(k.name, k.name, {type: k.kind === 'secret' ? 'password' : 'text', req: true})).join('') + KEYNOTE, ok: 'Connect',
        onOk: el => { const o = {}; need.forEach(k => { const v = val(el, k.name); if (v) o[k.name] = v; }); if (!Object.keys(o).length) throw new Error('Fill in the keys.'); return o; }});
      if (got && typeof got === 'object') return dirGo(x, btn, {...keys, ...got}, accept);
    } else if (r.status === 'caution') {
      const go = await modal({title: `${x.name}: be careful`, body: `<ul class="cx-steps">${(r.reasons || []).map(s => `<li>${esc(s)}</li>`).join('')}</ul><p class="cx-p">Hoola runs it in a locked box and asks for your yes before every write or send.</p>`, ok: 'Connect anyway', danger: true});
      if (go) return dirGo(x, btn, keys, true);
    } else toast(r.say || (r.reasons || []).join(' ') || 'Could not connect.', true);
    await loadMcp(); drawHead();
  }

  /* ------------------------------------------------------------------ Built in */
  function builtAction(p) {
    if (p.executor === 'mcp' && p.status === 'needs_link') return `<button class="cx-btn pri" data-pk-link="${esc(p.pack_id)}">Link</button>`;
    if (p.android_package) return `<span class="cx-pill mute">On your phone</span>`;
    if (p.status === 'ready' || p.status === 'core') return `<button class="cx-btn soft" data-say="${esc(`Use ${p.name}: `)}" data-prefill>${ic('chat', 13)}Ask Hoola</button>`;
    return pill(p.status);
  }
  function builtinView() {
    const B = S.built, C = S.cat || {packs: []};
    const linked = S.conn.filter(c => !c.custom);
    return `${linked.length ? `<section class="cx-sec"><div class="cx-sechead"><div><h2>Linked accounts</h2><p>Your own accounts on apps Hoola works with directly.</p></div></div>
        <div class="cx-rows">${linked.map(c => `<div class="cx-row">${logo(c.logo, c.name)}<div class="cx-rmain"><h3>${esc(c.name)}</h3><p>${esc(c.line || c.does || '')}</p></div>${pill(c.status)}
          ${c.no_login ? '' : c.status === 'ready' ? `<button class="cx-btn ghost" data-conn-un="${esc(c.pack_id)}">Unlink</button>` : c.status === 'needs_link' ? `<button class="cx-btn pri" data-pk-link="${esc(c.pack_id)}">Link</button>` : ''}</div>`).join('')}</div></section>` : ''}
      ${S.builtErr ? empty('plug', 'The plugins did not load', S.builtErr, retryBtn) : ''}
      <section class="cx-sec"><div class="cx-sechead"><div><h2>Hoola's own plugins</h2><p>${n0(C.total || (C.packs || []).length)} jobs Hoola does itself: bills, UPI, cabs, shops, government services and more.</p></div></div>
        <div class="cx-bar"><label class="cx-search">${ic('search')}<input id="cxbq" type="search" placeholder="Search plugins: electricity, kirana, Uber…" value="${esc(B.q)}" aria-label="Search plugins"></label>
          <div class="cx-seg" role="group" aria-label="Show">${[['all', 'All'], ['ready', 'Ready'], ['link', 'Needs your link']].map(([k, n]) => `<button data-bshow="${k}" aria-pressed="${B.show === k}">${n}</button>`).join('')}</div></div>
        <div id="cxbres">${builtResults()}</div></section>`;
  }
  function builtResults() {
    const B = S.built, C = S.cat || {packs: []};
    const q = B.q.trim().toLowerCase();
    const packs = (C.packs || []).filter(p => (!q || (p.name + ' ' + (p.does || '') + ' ' + p.category).toLowerCase().includes(q))
      && (B.show === 'all' || (B.show === 'ready' ? (p.status === 'ready' || p.status === 'core') : p.status === 'needs_link')));
    const groups = {};
    packs.forEach(p => (groups[p.category] = groups[p.category] || []).push(p));
    return `${Object.keys(groups).length ? Object.entries(groups).map(([g, list]) => `<details class="cx-fold" ${B.open.has(g) || q ? 'open' : ''} data-grp="${esc(g)}"><summary><span>${esc(g)}</span><em>${n0(list.length)}</em></summary>
          <div class="cx-rows">${list.map(p => `<div class="cx-row">${logo(p.logo, p.name)}<div class="cx-rmain"><h3>${esc(p.name)}</h3><p>${line(p)}</p></div>${builtAction(p)}</div>`).join('')}</div></details>`).join('')
          : empty('search', 'No plugin matches', 'Try another word.')}`;
  }
  function linkedDrawer(c) {
    const el = drawer(`<div class="cx-phead">${logo(c.logo, c.name, true)}<div><h2>${esc(c.name)}</h2><span>${c.no_login ? 'Built in · no login' : 'Linked account'}</span></div>
      <button class="cx-iconbtn" data-cd="close" aria-label="Close">${ic('x')}</button></div>
      <div class="cx-pbody"><div class="cx-prow">${pill(c.status)}</div><p class="cx-lead">${esc(c.line || c.does || '')}</p>
      <div class="cx-actions"><button class="cx-btn pri" data-say="${esc(`Use ${c.name}: `)}">${ic('chat', 14)}Ask Hoola to use it</button>${c.no_login ? '' : `<button class="cx-btn danger ghost" data-d="unlink">Unlink</button>`}</div></div>`);
    el.addEventListener('click', async e => {
      if (e.target.closest('[data-cd="close"]')) return closeDrawer();
      const s = e.target.closest('[data-say]'); if (s) { closeDrawer(); say(s.dataset.say); return; }
      if (e.target.closest('[data-d="unlink"]')) { closeDrawer(); unlink(c.pack_id); }
    });
  }
  async function linkPack(pack, name) {
    const w = preopen();
    try { const l = await api('POST', `/api/bazar/connections/${encodeURIComponent(pack)}/link`); signin(w, l.url, name, 'pack'); }
    catch (e) { if (w) w.close(); toast(e.message, true); }
  }
  async function unlink(pack) {
    const c = S.conn.find(x => x.pack_id === pack); const name = c ? c.name : 'this account';
    if (!await confirmBox(`Unlink ${name}?`, 'Hoola will not be able to use this account until you link it again.', 'Unlink')) return;
    try { await api('DELETE', `/api/bazar/connections/${encodeURIComponent(pack)}`); toast(`${name} unlinked.`); }
    catch (e) { toast(e.message, true); }
    await loadBuiltin(); drawHead(); drawBody();
  }

  /* ------------------------------------------------------------------ Public APIs */
  function apisView() {
    const P = S.apis;
    return `<div class="cx-bar"><label class="cx-search">${ic('search')}<input id="cxaq" type="search" placeholder="Search ${P.total ? n0(P.total) + ' ' : ''}free APIs: IFSC, pincode, cricket, holidays…" value="${esc(P.q)}" aria-label="Search public APIs"></label>
        <select class="cx-select" id="cxacat" aria-label="Category"><option value="">All categories</option>${P.cats.map(c => `<option value="${esc(c.cat)}" ${P.cat === c.cat ? 'selected' : ''}>${esc(c.cat)} (${n0(c.count)})</option>`).join('')}</select>
        <div class="cx-seg" role="group" aria-label="Key">${[['any', 'All'], ['none', 'No key'], ['key', 'Needs a key']].map(([k, n]) => `<button data-aauth="${k}" aria-pressed="${P.auth === k}">${n}</button>`).join('')}</div></div>
      <div id="cxares">${apisResults()}</div>`;
  }
  function apisResults() {
    const P = S.apis;
    return `<div class="cx-subhead"><span>${n0(P.count)} API${P.count === 1 ? '' : 's'}${P.list.length < P.count ? ` · top ${n0(P.list.length)} shown` : ''}</span><span class="cx-by">${ic('spark', 13)}Hoola picks and calls these by itself when your ask needs one</span></div>
      ${P.error && !P.list.length ? empty('search', 'APIs did not load', P.error) : P.list.length ? `<div class="cx-rows">${P.list.map(a => `<div class="cx-row">${logo('', a.name)}
        <div class="cx-rmain"><h3>${esc(a.name)} <span class="cx-tag">${esc(a.cat)}</span></h3><p>${line(a)}</p></div>
        ${a.free_no_key ? '<span class="cx-pill ok"><i></i>No key needed</span>' : a.key_saved ? `<span class="cx-pill ok"><i></i>Key saved</span><button class="cx-btn ghost" data-api-del="${esc(a.id)}">Remove key</button>` : `<button class="cx-btn soft" data-api-key="${esc(a.id)}">${ic('key', 13)}Add key</button>`}
        ${a.link ? `<a class="cx-iconbtn" href="${esc(a.link)}" target="_blank" rel="noopener noreferrer" aria-label="${esc(a.name)} docs">${ic('ext', 15)}</a>` : ''}</div>`).join('')}</div>` : empty('search', 'No API matches', 'Try another word.')}`;
  }
  async function apiKey(id) {
    const a = S.apis.list.find(x => x.id === id); if (!a) return;
    const ok = await modal({title: `${a.name}: API key`, sub: `Get it from ${esc(a.name)}'s own site. Hoola adds it to every call it makes to this API.`,
      body: field('key', 'API key', {type: 'password', req: true}) + `<label class="cx-field"><span>Where the key goes</span><select name="place" class="cx-select"><option value="query">In the address (?key=…)</option><option value="header">In a header</option></select></label>`
        + field('field', 'Parameter or header name (optional)', {ph: 'api_key / X-API-Key'}) + KEYNOTE
        + (a.link ? `<a class="cx-link" href="${esc(a.link)}" target="_blank" rel="noopener noreferrer">${ic('ext', 13)}Open ${esc(a.name)} docs</a>` : ''),
      ok: 'Save key', onOk: async el => { const key = val(el, 'key'); if (key.length < 4) throw new Error('That key looks too short.'); await api('PUT', `/api/publicapis/${encodeURIComponent(id)}/key`, {key, place: val(el, 'place') || 'query', field: val(el, 'field')}); }});
    if (ok) { toast('Key saved.'); await loadApis(); drawBody(); }
  }

  /* ------------------------------------------------------------------ Limits & safety */
  function limitsView() {
    const s = S.settings || {};
    if (s.error) return empty('shield', 'Settings did not load', s.error);
    const rs = v => (v ? String(+v) : '');
    return `<div class="cx-two">
      <section class="cx-panelcard"><div class="cx-sechead"><div><h2>Spending limit</h2><p>0 means your tap for every expense. Within the limit, only orders to shops and billers you approved before go through by themselves.</p></div></div>
        <form id="cxlim" class="cx-form">
          <label class="cx-field"><span>Per order</span><div class="cx-money"><b>₹</b><input name="cap_per_order_rupees" inputmode="decimal" value="${esc(rs(s.cap_per_order_rupees))}" placeholder="0"></div></label>
          <label class="cx-field"><span>Per day</span><div class="cx-money"><b>₹</b><input name="cap_per_day_rupees" inputmode="decimal" value="${esc(rs(s.cap_per_day_rupees))}" placeholder="0"></div></label>
          <h3 class="cx-h3">Delivery details</h3>
          ${field('pincode', 'PIN code', {value: s.pincode || '', ph: '444001'})}
          <label class="cx-field"><span>Address</span><textarea name="address" rows="3" placeholder="House, street, area, city">${esc(s.address || '')}</textarea></label>
          ${field('phone', 'Phone for deliveries', {value: s.phone || '', ph: '+91 …'})}
          <div class="cx-formfoot"><button class="cx-btn pri" type="submit">Save</button></div>
        </form></section>
      <section class="cx-panelcard soft"><div class="cx-sechead"><div><h2>How Hoola stays safe</h2><p>The same rules on every app, every server and every surface.</p></div></div>
        <ul class="cx-rules">
          <li>${ic('check', 15)}<span><b>Money only on your tap.</b> Payments are always a card you approve; Hoola never moves money by itself.</span></li>
          <li>${ic('check', 15)}<span><b>Sending, deleting, sharing</b> and public changes show you a confirm card first.</span></li>
          <li>${ic('check', 15)}<span><b>Keys stay sealed.</b> Typed only on this page or in the phone app, stored encrypted, never shown again, never asked for in chat.</span></li>
          <li>${ic('check', 15)}<span><b>No PIN, OTP, CVV or password</b> is ever asked for or typed by Hoola for your accounts.</span></li>
          <li>${ic('check', 15)}<span><b>Words inside apps are data.</b> Text in mails, files, pages and app records never gives Hoola orders.</span></li>
          <li>${ic('check', 15)}<span><b>Remove any connection</b> and Hoola loses access at once.</span></li>
        </ul></section></div>`;
  }
  async function saveLimits(form) {
    const btn = form.querySelector('button[type="submit"]');
    const num = n => { const v = (form.elements[n].value || '').replace(/[,₹\s]/g, ''); if (v && !/^\d+(\.\d{1,2})?$/.test(v)) throw new Error('Limits are rupee amounts, like 500.'); return v ? +v : 0; };
    busy(btn, true, 'Saving…');
    try {
      const body = {cap_per_order_rupees: num('cap_per_order_rupees'), cap_per_day_rupees: num('cap_per_day_rupees'),
                    pincode: form.elements.pincode.value.trim(), address: form.elements.address.value.trim(), phone: form.elements.phone.value.trim()};
      S.settings = await api('PUT', '/api/bazar/settings', body);
      toast('Saved.');
    } catch (e) { toast(e.message, true); }
    busy(btn, false);
  }

  const retryBtn = '<button class="cx-btn soft" data-retry>Try again</button>';
  /* ------------------------------------------------------------------ empty state */
  function empty(icon, title, text, extra = '') {
    return `<div class="cx-empty"><div class="cx-emptyic">${ic(icon, 22)}</div><h3>${esc(title)}</h3>${text ? `<p>${esc(text)}</p>` : ''}${extra}</div>`;
  }

  /* ------------------------------------------------------------------ events (one listener on the page) */
  const appSearch = debounce(async q => { S.apps.q = q; await loadApps(false); const r = $('#cxres'); if (r && TAB === 'apps') r.innerHTML = appsResults(); }, 260);
  const dirSearch = debounce(q => searchDir(q), 300);
  const apiSearch = debounce(async q => { S.apis.q = q; await loadApis(); const r = $('#cxares'); if (r && TAB === 'apis') r.innerHTML = apisResults(); }, 280);
  function wire() {
    ROOT.addEventListener('error', fixLogo, true);
    ROOT.addEventListener('click', async e => {
      const t = e.target;
      const tab = t.closest('.cx-tab'); if (tab) { setTab(tab.dataset.tab); return; }
      const tg = t.closest('[data-tab-go]'); if (tg) { setTab(tg.dataset.tabGo); return; }
      const sh = t.closest('[data-show]'); if (sh) { S.apps.show = sh.dataset.show; drawBody(); return; }
      const ct = t.closest('[data-cat]'); if (ct) { S.apps.cat = ct.dataset.cat; S.apps.loaded = false; drawBody(); return; }
      const mo = t.closest('[data-more]'); if (mo) { busy(mo, true, 'Loading…'); await loadApps(true); drawBody(); return; }
      const ag = t.closest('[data-app-go]'); if (ag) { appGo(ag.dataset.appGo, ag); return; }
      const ao = t.closest('[data-app-open]'); if (ao) { appDrawer(ao.dataset.appOpen); return; }
      const fg = t.closest('[data-feat-go]'); if (fg) { const f = S.feat.find(x => x.id === fg.dataset.featGo); if (f) featGo(f, fg); return; }
      const fo = t.closest('[data-feat-open]'); if (fo) { const f = S.feat.find(x => x.id === fo.dataset.featOpen); if (f) featDrawer(f); return; }
      const so = t.closest('[data-srv-open]'); if (so) { const m = S.mine.find(x => x.pack_id === so.dataset.srvOpen); if (m) serverDrawer(m); return; }
      if (t.closest('[data-mcp="add"]')) { addServer(null); return; }
      const dg = t.closest('[data-dir-go]'); if (dg) { const x = S.dir.list[+dg.dataset.dirGo]; if (x) dirGo(x, dg); return; }
      const cm = t.closest('[data-cn-manage]'); if (cm) { const c = cm.closest('[data-cn-kind]'); manageConnected(c.dataset.cnKind, c.dataset.cnKey); return; }
      const pl = t.closest('[data-pk-link]'); if (pl) { const p = (S.cat?.packs || []).find(x => x.pack_id === pl.dataset.pkLink) || S.conn.find(x => x.pack_id === pl.dataset.pkLink); linkPack(pl.dataset.pkLink, p ? p.name : 'the app'); return; }
      const cu = t.closest('[data-conn-un]'); if (cu) { unlink(cu.dataset.connUn); return; }
      const bs = t.closest('[data-bshow]'); if (bs) { S.built.show = bs.dataset.bshow; drawBody(); return; }
      const aa = t.closest('[data-aauth]'); if (aa) { S.apis.auth = aa.dataset.aauth; await loadApis(); drawBody(); return; }
      const ak = t.closest('[data-api-key]'); if (ak) { apiKey(ak.dataset.apiKey); return; }
      const ad = t.closest('[data-api-del]'); if (ad) { try { await api('DELETE', `/api/publicapis/${encodeURIComponent(ad.dataset.apiDel)}/key`); toast('Key removed.'); await loadApis(); drawBody(); } catch (x) { toast(x.message, true); } return; }
      const sy = t.closest('[data-say]'); if (sy) { say(sy.dataset.say); return; }
      const rt = t.closest('[data-retry]'); if (rt) { busy(rt, true, 'Loading…'); S.loaded.mcp = S.loaded.builtin = false; await drawBody(); drawHead(); return; }
      if (t.closest('button,a,input,select,textarea,summary,label')) return;
      const card = t.closest('[data-app]'); if (card) { appDrawer(card.dataset.app); return; }
      const fc = t.closest('[data-feat]'); if (fc) { const f = S.feat.find(x => x.id === fc.dataset.feat); if (f) featDrawer(f); return; }
      const cn = t.closest('[data-cn-kind]'); if (cn) { manageConnected(cn.dataset.cnKind, cn.dataset.cnKey); return; }
    });
    ROOT.addEventListener('keydown', e => {
      const tab = e.target.closest('.cx-tab');
      if (tab && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
        const i = TABS.findIndex(([k]) => k === tab.dataset.tab), j = (i + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length;
        setTab(TABS[j][0]); ROOT.querySelector(`.cx-tab[data-tab="${TABS[j][0]}"]`)?.focus(); return;
      }
      if (e.key === 'Enter' && e.target.matches('.cx-card[tabindex]')) e.target.click();
    });
    ROOT.addEventListener('input', e => {
      if (e.target.id === 'cxq') appSearch(e.target.value.trim());
      if (e.target.id === 'cxdir') dirSearch(e.target.value.trim());
      if (e.target.id === 'cxaq') apiSearch(e.target.value.trim());
      if (e.target.id === 'cxbq') { S.built.q = e.target.value; const r = $('#cxbres'); if (r) r.innerHTML = builtResults(); }
    });
    ROOT.addEventListener('change', async e => { if (e.target.id === 'cxacat') { S.apis.cat = e.target.value; await loadApis(); drawBody(); } });
    ROOT.addEventListener('toggle', e => { const d = e.target.closest?.('[data-grp]'); if (d) d.open ? S.built.open.add(d.dataset.grp) : S.built.open.delete(d.dataset.grp); }, true);
    ROOT.addEventListener('submit', e => { if (e.target.id === 'cxlim') { e.preventDefault(); saveLimits(e.target); } });
  }
  function setTab(k) {
    if (!TABS.some(([x]) => x === k)) return;
    TAB = k; try { localStorage.setItem(LS_TAB, k); } catch {}
    drawHead(); drawBody();
  }

  /* ------------------------------------------------------------------ the door */
  async function open(el, tab) {
    if (tab && TABS.some(([k]) => k === tab)) TAB = tab;
    if (ROOT !== el || !el.querySelector('.cx')) { ROOT = el; frame(); wire(); }
    drawHead(); await drawBody();
    if (!S.apps.loaded) { await loadApps(false); drawHead(); }                 // the counts in the header need every list
    if (!S.loaded.mcp) { await loadMcp(); drawHead(); }
    if (!S.loaded.builtin) { await loadBuiltin(); drawHead(); }
  }
  return {open, leave: () => { closeDrawer(); closeModal(null); }};
};
