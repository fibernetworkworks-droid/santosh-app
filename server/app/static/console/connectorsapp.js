/* v0.999.183 CONNECTORS PAGE - her connected apps as their own section (owner: "MAKE THIS CONNECTOR SECTION SEPERATE PAGE
   PERFCTLY AS WE DID FOR DIRREENT TOOL SECTIONS -- MAKE IT MORE PREMIUM, ADVANCE" -> design canvas
   claude.ai/artifact/G51SEVNTHqsK9TD9DKxHfS -> "GO").

   Views (hash routes): #/ Overview (needs you, numbers, your apps, suggested) · #/google (accounts, everyday apps, more
   apps) · #/google/<app> one Google app (what it does on its own / after your yes / never, accounts + used first,
   activity, this week) · #/apps every Composio app (search, groups, show, sort) · #/app/<slug> one app · #/activity
   everything Hoola did in her apps · #/limits her Pause switch, the rules that are always on, spending limits ·
   #/connected #/mcp #/builtin #/apis = connectors.js's own sections, embedded.

   Laws kept: keys are typed here and go straight to the server (sealed, never shown again, never in chat); a sign-in
   opens the app's own page in a window and the done page tells this tab (BroadcastChannel 'hoola-connect'); Google
   connects on Google's own page; every server value goes through esc(); no inline handlers (CSP script-src 'self'). */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const n0 = n => Number(n || 0).toLocaleString();
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  if (!TOKEN) { location.replace('/console/'); return; }
  const MAIN = $('#kmain');

  async function api(method, path, body, opts) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store', signal: opts && opts.signal});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#ktoast'); t.textContent = S(msg); t.className = 'k-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4600);
  }
  const say = text => { try { localStorage.setItem('hoola.flow.toChat', S(text)); } catch {} location.assign('/console/'); };
  const svg = d => `<svg class="k-i" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    grid: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    apps: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/>',
    mcp: '<path d="M4 5h16v6H4zM4 13h16v6H4zM8 8h.01M8 16h.01"/>',
    star: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.1 1.2 6.1L12 16.6 6.6 19.5l1.2-6.1L3.3 9.3l6.1-.7z"/>',
    api: '<path d="M8 4c-2 0-2 2-2 4s-2 4-2 4 2 0 2 4 0 4 2 4M16 4c2 0 2 2 2 4s2 4 2 4-2 0-2 4 0 4-2 4"/>',
    pulse: '<path d="M3 12h4l3 8 4-16 3 8h4"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', search: '<path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4"/>',
    chat: '<path d="M4 5h16v11H9l-5 4z"/>', key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3"/>',
    down: '<path d="M12 4v12M6 10l6 6 6-6M5 20h14"/>', check: '<path d="M5 12l5 5 9-10"/>', back: '<path d="M15 18l-6-6 6-6"/>'};

  try { $('#kmark').innerHTML = window.HoolaMark ? HoolaMark.svg({color: '#FFFFFF'}) : ''; } catch {}

  /* ------------------------------------------------------------------ logos */
  const GKEYS = ['gmail', 'calendar', 'drive', 'docs', 'sheets', 'forms', 'slides', 'photos', 'youtube', 'business', 'searchconsole', 'appsscript', 'bigquery', 'driveactivity'];
  const gSrc = k => `/static/console/google/${GKEYS.includes(k) ? k : 'google'}.png`;
  const TINTS = [['#F3ECF8', '#5B2A7A'], ['#FDEEEA', '#9A3412'], ['#E7F6EC', '#1E6B40'], ['#E8EEFB', '#2340A0'], ['#FFF1DD', '#8A5300'], ['#E8F4FB', '#1A5F8B']];
  const tint = name => { let h = 0; for (const c of S(name)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return TINTS[h % TINTS.length]; };
  const letterTile = (name, size) => { const [b, f] = tint(name); return `<span class="k-logo letter ${size || ''}" style="--k-l:${b};--k-lt:${f}" aria-hidden="true">${esc(S(name).trim().charAt(0).toUpperCase() || '?')}</span>`; };
  const gLogo = (k, size) => `<span class="k-logo ${size || ''}" aria-hidden="true"><img src="${gSrc(k)}" alt="" decoding="async"></span>`;
  const appLogo = (a, size) => a && a.logo && /^\/|^https:/.test(a.logo)
    ? `<span class="k-logo ${size || ''}" aria-hidden="true"><img src="${esc(a.logo)}" alt="" decoding="async" data-fb="${esc(S(a.name).charAt(0).toUpperCase())}"></span>`
    : letterTile(a && a.name, size);
  document.addEventListener('error', e => {   // a logo that does not load becomes the app's first letter
    const im = e.target;
    if (im && im.tagName === 'IMG' && im.dataset.fb !== undefined) {
      const box = im.parentNode; if (!box) return;
      const [b, f] = tint(im.dataset.fb); box.classList.add('letter'); box.style.setProperty('--k-l', b); box.style.setProperty('--k-lt', f);
      box.textContent = im.dataset.fb || '?';
    }
  }, true);

  /* ------------------------------------------------------------------ data */
  const D = {google: null, home: null, sum: null, safe: null, calls: null, loaded: false};
  async function loadAll() {
    const [g, h, s, f, c] = await Promise.allSettled([api('GET', '/api/google'), api('GET', '/api/composio/home'),
      api('GET', '/api/connectors/summary'), api('GET', '/api/connectors/safety'), api('GET', '/api/composio/apps?limit=1')]);
    D.google = g.status === 'fulfilled' ? g.value : {error: g.reason?.message || 'Google did not load.', accounts: [], apps: []};
    D.home = h.status === 'fulfilled' ? h.value : {error: h.reason?.message || 'Apps did not load.', mine: [], featured: [], groups: [], total: 0};
    D.sum = s.status === 'fulfilled' ? s.value : {month: {total: 0, done: 0, asked: 0, failed: 0, paused: 0}, week: {}, last: {}, paused: false};
    D.safe = f.status === 'fulfilled' ? f.value : {paused: false, always: []};
    D.calls = c.status === 'fulfilled' ? {used: c.value.calls_this_month || 0, cap: c.value.monthly_cap || 0, configured: c.value.configured !== false} : null;
    D.loaded = true;
  }
  const gApps = () => (D.google && D.google.apps) || [];
  const gAcc = () => (D.google && D.google.accounts) || [];
  const mine = () => (D.home && D.home.mine) || [];
  const ACT_KEY = k => k === 'gmail' ? 'mail' : k;                 // the Activity log calls every mail account 'mail'
  function needs() {
    const out = [];
    for (const a of gAcc()) if (a.state === 'expired') out.push({title: `${a.email} needs you`, why: `Google ended Hoola’s access. ${a.apps.length ? a.apps.map(gName).join(', ') + ' stopped.' : ''}`, act: 'Reconnect', g: (a.apps.join(',') || 'core'), hint: a.email});
    for (const a of mine()) if (a.status === 'pending' || a.status === 'expired') out.push({title: `${a.name} needs you`, why: a.status === 'pending' ? 'The sign-in was not finished.' : 'The sign-in ended.', act: 'Sign in again', app: a.toolkit});
    if (D.sum && D.sum.paused) out.unshift({title: 'Every app is paused', why: 'Hoola is not using any of your apps until you turn this off.', act: 'Turn on', go: 'limits'});
    return out;
  }
  const gName = k => (gApps().find(a => a.key === k) || {}).name || k;
  function connectedCount() {
    return gApps().filter(a => a.state === 'ok').length + mine().filter(a => a.status === 'ready').length;
  }

  /* ------------------------------------------------------------------ time */
  function ago(iso) {
    const t = Date.parse(iso); if (!t) return '';
    const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'Just now';
    if (s < 3600) return `${Math.round(s / 60)} min ago`;
    if (s < 86400) return `${Math.round(s / 3600)} h ago`;
    const d = new Date(t), y = new Date(); y.setDate(y.getDate() - 1);
    if (d.toDateString() === y.toDateString()) return 'Yesterday';
    return d.toLocaleDateString(undefined, {day: 'numeric', month: 'short'});
  }

  /* ------------------------------------------------------------------ sidebar */
  const NAV = [['', 'Overview', IC.grid], ['google', 'Google', ''], ['apps', 'All apps', IC.apps], ['connected', 'Connected', IC.link],
    ['mcp', 'MCP servers', IC.mcp], ['builtin', 'Built in', IC.star], ['apis', 'Public APIs', IC.api], ['-'],
    ['activity', 'Activity', IC.pulse], ['limits', 'Limits & safety', IC.shield]];
  function drawSide(route) {
    const top = route.split('/')[0];
    const cnt = {google: gApps().filter(a => a.state === 'ok').length ? `${gApps().filter(a => a.state === 'ok').length} apps` : '',
      apps: D.home && D.home.total ? n0(D.home.total) : '', connected: connectedCount() ? String(connectedCount()) : '',
      activity: D.sum && D.sum.month.total ? n0(D.sum.month.total) : ''};
    $('#knav').innerHTML = NAV.map(([k, label, d]) => {
      if (k === '-') return '<div class="k-navgap" role="separator"></div>';
      const on = top === k || (top === 'app' && k === 'apps');
      const ico = k === 'google' ? `<img src="/static/console/google/google.png" alt="" width="18" height="18">` : svg(d);
      const extra = k === 'limits' && D.sum && D.sum.paused ? '<span class="k-cnt warn">Paused</span>' : (cnt[k] ? `<span class="k-cnt">${esc(cnt[k])}</span>` : '');
      return `<a class="k-nav" href="#/${k}"${on ? ' aria-current="page"' : ''}>${ico}<span>${esc(label)}</span>${extra}</a>`;
    }).join('');
    const n = needs();
    const box = $('#kneed');
    if (n.length) {
      box.hidden = false;
      box.innerHTML = `<b>${n.length === 1 ? '1 needs you' : `${n.length} need you`}</b><span>${esc(n[0].why || n[0].title)}</span>
        <button type="button" class="k-btn sm pri" data-need="0">${esc(n[0].act)}</button>`;
    } else box.hidden = true;
  }

  /* ------------------------------------------------------------------ router */
  let EMBED = null, EMBED_EL = null;
  function route() { return decodeURIComponent((location.hash || '').replace(/^#\/?/, '')); }
  async function draw() {
    const r = route();
    if (!D.loaded) { MAIN.innerHTML = '<div class="k-wrap"><div class="k-loading">Opening Connectors…</div></div>'; await loadAll(); }
    drawSide(r);
    const [top, arg] = [r.split('/')[0], r.split('/').slice(1).join('/')];
    if (['connected', 'mcp', 'builtin', 'apis'].includes(top)) return drawEmbed(top);
    if (EMBED) EMBED.leave();
    const v = {'': overview, google: arg ? gAppView.bind(null, arg) : googleView, apps: browse, app: appView.bind(null, arg),
      activity: activityView, limits: limitsView}[top] || overview;
    await v();
    MAIN.focus({preventScroll: true});
  }
  window.addEventListener('hashchange', () => { window.scrollTo(0, 0); draw(); });

  function drawEmbed(tab) {
    const titles = {connected: ['Connected', 'Everything Hoola can use for you, in one place.'],
      mcp: ['MCP servers', 'Official servers and your own. Turn tools on or off, or make Hoola ask first.'],
      builtin: ['Built in', 'Hoola’s own plugins and the accounts you linked to them.'],
      apis: ['Public APIs', 'Free data APIs Hoola can call. Add a key for the ones that need one.']}[tab];
    MAIN.innerHTML = `<div class="k-wrap"><header class="k-head"><div><h1>${esc(titles[0])}</h1><p>${esc(titles[1])}</p></div></header><div class="k-embed" id="kembed"></div></div>`;
    if (!EMBED && window.HoolaConnectors) EMBED = window.HoolaConnectors({api, esc, toast, say});
    EMBED_EL = $('#kembed');
    if (EMBED) EMBED.open(EMBED_EL, tab);
    else EMBED_EL.innerHTML = '<p class="k-p">This section did not load. Refresh the page.</p>';
  }

  /* ------------------------------------------------------------------ pieces */
  const pill = st => ({ok: '<span class="k-pill ok"><i></i>Connected</span>', ready: '<span class="k-pill ok"><i></i>Connected</span>',
    expired: '<span class="k-pill warn">Reconnect</span>', pending: '<span class="k-pill warn">Finish sign-in</span>',
    needs_link: '', needs_key: '', none: '<span class="k-pill mute">Not connected</span>',
    needs_setup: '<span class="k-pill mute">Not available yet</span>', not_configured: '<span class="k-pill mute">Not on this server</span>'}[st] || '');
  const OUT = {done: ['own', 'Done'], asked: ['yes', 'Asked you'], failed: ['bad', 'Failed'], paused: ['warn', 'Paused']};
  const FROM = {chat: 'Chat', call: 'Call', routine: 'Routine', employee: 'AI employee'};
  function weekLine(k) {
    const w = (D.sum && D.sum.week && D.sum.week[k]) || null, last = D.sum && D.sum.last && D.sum.last[k];
    const n = w ? (w.done || 0) + (w.asked || 0) : 0;
    return [last ? `Used ${ago(last).toLowerCase()}` : 'Not used yet', n ? `${n} this week` : ''].filter(Boolean).join(' · ');
  }
  const head = (h, p, right) => `<header class="k-head"><div><h1>${esc(h)}</h1>${p ? `<p>${p}</p>` : ''}</div>${right ? `<div class="k-row">${right}</div>` : ''}</header>`;
  const empty = (b, t) => `<div class="k-empty"><b>${esc(b)}</b><span>${esc(t)}</span></div>`;

  function needsBlock() {
    const n = needs(); if (!n.length) return '';
    return `<section class="k-sec"><div class="k-sech"><h2>Needs you</h2></div><div class="k-needs">${n.map((x, i) => `<div class="k-needrow">
      ${x.g ? gLogo('google', 'sm') : x.app ? appLogo(mine().find(a => a.toolkit === x.app), 'sm') : `<span class="k-logo sm">${svg(IC.shield)}</span>`}
      <div class="k-t"><b>${esc(x.title)}</b><span>${esc(x.why)}</span></div>
      <button type="button" class="k-btn sm pri" data-need="${i}">${esc(x.act)}</button></div>`).join('')}</div></section>`;
  }
  function onNeed(i) {
    const x = needs()[i]; if (!x) return;
    if (x.go) location.hash = '#/' + x.go;
    else if (x.g) gConnect(x.g.split(','), x.hint);
    else if (x.app) appConnect(x.app);
  }

  /* ------------------------------------------------------------------ Overview */
  async function overview() {
    const G = D.google, M = D.sum.month, c = connectedCount();
    const yours = [
      ...gApps().filter(a => a.state === 'ok' || a.state === 'expired').map(a => ({href: `#/google/${a.key}`, logo: gLogo(a.key), name: a.name, sub: 'Google', line: a.does, st: a.state, k: ACT_KEY(a.key)})),
      ...mine().map(a => ({href: `#/app/${a.toolkit}`, logo: appLogo(a), name: a.name, sub: a.category || a.group_name || 'App', line: a.line || a.does, st: a.status, k: a.toolkit}))];
    const card = y => `<a class="k-card" href="${y.href}"><div class="k-top">${y.logo}<div class="k-nm"><b>${esc(y.name)}</b><span>${esc(y.sub)}</span></div>${pill(y.st)}</div>
      <span class="k-ln">${esc(y.line || '')}</span><div class="k-ft"><span>${esc(weekLine(y.k))}</span></div></a>`;
    const sug = ((D.home && D.home.featured) || []).slice(0, 3);
    const calls = D.calls && D.calls.cap ? Math.min(100, Math.round(D.calls.used * 100 / D.calls.cap)) : 0;
    MAIN.innerHTML = `<div class="k-wrap">
      ${head('Connectors', `${c ? `${c} app${c === 1 ? '' : 's'} connected` : 'No apps connected yet'} · Hoola did ${n0(M.total)} thing${M.total === 1 ? '' : 's'} in your apps this month.`,
        `<a class="k-btn" href="#/activity">${svg(IC.pulse)}Activity</a><a class="k-btn pri" href="#/apps">${svg(IC.plus)}Connect an app</a>`)}
      ${needsBlock()}
      <div class="k-stats">
        <div class="k-stat"><b>${n0(c)}</b><span>Apps connected</span></div>
        <div class="k-stat"><b>${n0(M.done)}</b><span>Done on its own this month</span></div>
        <div class="k-stat"><b>${n0(M.asked)}</b><span>Asked for your yes</span></div>
        <div class="k-stat"><b class="k-num">${D.calls ? n0(D.calls.used) : '—'}<span class="k-mut" style="font-size:14px;font-weight:500"> / ${D.calls && D.calls.cap ? n0(D.calls.cap) : '—'}</span></b><span>App calls this month</span>
          <div class="k-meter" role="meter" aria-label="App calls used this month" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${calls}"><i style="width:${calls}%"></i></div></div>
      </div>
      ${G && !G.error && G.ready !== false ? `<section class="k-sec"><div class="k-sech"><div><h2>Google</h2><p>${gAcc().length ? `${gAcc().length} account${gAcc().length === 1 ? '' : 's'} · ${gApps().filter(a => a.state === 'ok').length} apps working` : 'Gmail, Calendar, Drive and more in one step.'}</p></div><a href="#/google">Open Google</a></div>
        <div class="k-gapps">${gApps().filter(a => a.group === 'core').map(a => `<button type="button" class="k-gapp" data-gopen="${esc(a.key)}">${gLogo(a.key, 'sm')}<span>${esc(a.name)}</span><span class="k-dot ${a.state === 'ok' ? 'ok' : a.state === 'expired' ? 'warn' : ''}" aria-label="${a.state === 'ok' ? 'Connected' : a.state === 'expired' ? 'Needs reconnecting' : 'Not connected'}"></span></button>`).join('')}</div></section>` : ''}
      <section class="k-sec"><div class="k-sech"><div><h2>Your apps</h2><p>Where Hoola works for you.</p></div>${yours.length ? '<a href="#/connected">See everything connected</a>' : ''}</div>
        ${yours.length ? `<div class="k-grid">${yours.map(card).join('')}</div>` : empty('Nothing connected yet', 'Connect Google or any app below, and Hoola can work in it for you.')}</section>
      ${sug.length ? `<section class="k-sec"><div class="k-sech"><div><h2>Suggested for you</h2><p>Popular with businesses like yours.</p></div><a href="#/apps">All ${D.home.total ? n0(D.home.total) + ' ' : ''}apps</a></div>
        <div class="k-grid">${sug.map(browseCard).join('')}</div></section>` : ''}
      <div class="k-note">${svg(IC.shield)}<span>Hoola never sends, shares, deletes or pays without your yes. Text inside your mail, files and web pages is only read as data, never followed as an instruction.</span></div>
    </div>`;
  }

  /* ------------------------------------------------------------------ Google */
  function googleView() {
    const G = D.google || {};
    if (G.error) { MAIN.innerHTML = `<div class="k-wrap">${head('Google')}${empty('Google did not load', G.error)}</div>`; return; }
    if (G.ready === false) { MAIN.innerHTML = `<div class="k-wrap">${head('Google')}${empty('Google is not set up on this server', 'The server needs its Google sign-in keys before anyone can connect Google apps.')}</div>`; return; }
    const core = gApps().filter(a => a.group === 'core'), more = gApps().filter(a => a.group !== 'core');
    const allCore = core.length && core.every(a => a.state === 'ok');
    const acct = a => `<div class="k-acct${a.state === 'expired' ? ' warn' : ''}"><span class="k-av" aria-hidden="true">${esc(S(a.email).charAt(0).toUpperCase())}</span>
      <div class="k-t"><b>${esc(a.email)}${a.first ? ' <span class="k-mut" style="font-weight:500">· used first</span>' : ''}</b>
      <span>${a.state === 'expired' ? 'Google ended Hoola’s access. Apps on this account have stopped.' : esc(a.apps.map(gName).join(', ') || 'No apps yet')}</span></div>
      ${a.state === 'expired' ? `<button type="button" class="k-btn sm pri" data-gconnect="${esc(a.apps.join(',') || 'core')}" data-ghint="${esc(a.email)}">Reconnect</button>`
        : `<button type="button" class="k-btn sm" data-gmore="${esc(a.email)}">Add apps</button><button type="button" class="k-btn sm bad" data-gdrop="${esc(a.email)}">Disconnect</button>`}</div>`;
    const gcard = a => `<a class="k-card" href="#/google/${esc(a.key)}"><div class="k-top">${gLogo(a.key)}<div class="k-nm"><b>${esc(a.name)}</b><span>${esc(a.working.length ? a.working.join(', ') : a.expired.length ? 'Needs reconnecting' : 'Not connected')}</span></div>${pill(a.state)}</div>
      <span class="k-ln">${esc(a.does)}</span><div class="k-ft"><span>${esc(a.state === 'ok' ? weekLine(ACT_KEY(a.key)) : '')}</span>${a.state === 'ok' ? '' : `<button type="button" class="k-btn sm ${a.state === 'expired' ? 'pri' : ''}" data-gconnect="${esc(a.key)}"${a.expired[0] ? ` data-ghint="${esc(a.expired[0])}"` : ''}>${a.state === 'expired' ? 'Reconnect' : 'Connect'}</button>`}</div></a>`;
    const row = a => `<div class="k-li click" data-gopen="${esc(a.key)}">${gLogo(a.key, 'sm')}<div class="k-t"><b>${esc(a.name)}</b><span>${esc(a.does)}</span></div>${a.state === 'none' ? '' : pill(a.state)}
      ${a.state === 'ok' ? '<span class="k-mut" aria-hidden="true">›</span>' : `<button type="button" class="k-btn sm ${a.state === 'expired' ? 'pri' : ''}" data-gconnect="${esc(a.key)}">${a.state === 'expired' ? 'Reconnect' : 'Connect'}</button>`}</div>`;
    MAIN.innerHTML = `<div class="k-wrap">
      ${head('Google', 'Gmail, Calendar, Drive and every other Google app, on your own Google accounts. Each app is off until you switch it on, and Google asks you first.',
        `<button type="button" class="k-btn${gAcc().length ? '' : ' pri'}" data-gconnect="core" data-ghint="">${svg(IC.plus)}${gAcc().length ? 'Add a Google account' : 'Connect Google'}</button>`)}
      ${needs().filter(x => x.g).length ? needsBlock() : ''}
      <section class="k-sec"><div class="k-sech"><div><h2>Your Google accounts</h2><p>${gAcc().length ? 'Hoola works in these accounts for you.' : 'None yet.'}</p></div></div>
        ${gAcc().length ? `<div class="k-sec" style="gap:10px">${gAcc().map(acct).join('')}</div>` : (G.signin ? `<p class="k-p">You signed in to Hoola with ${esc(G.signin)}. Signing in only shares your name and email, so the apps still need connecting.</p>` : '')}</section>
      <section class="k-sec"><div class="k-sech"><div><h2>Everyday apps</h2><p>One step connects all of them. On Google’s page you can untick any you don’t want.</p></div>${allCore ? '' : '<button type="button" class="k-btn pri" data-gconnect="core">Connect everyday apps</button>'}</div>
        <div class="k-grid">${core.map(gcard).join('')}</div></section>
      ${more.length ? `<section class="k-sec"><div class="k-sech"><div><h2>More Google apps</h2><p>Connect each one only when you need it.</p></div></div><div class="k-list">${more.map(row).join('')}</div></section>` : ''}
      <div class="k-note">${svg(IC.shield)}<span>Disconnecting an account also removes Hoola’s access in your Google account. You can also remove it at myaccount.google.com/permissions.</span></div>
    </div>`;
  }

  const GDO = {
    gmail: ['Reads, searches and sorts your mail · labels and archives · writes drafts · reads attachments', 'Sends a mail · forwards · mail to many people · deletes', 'Reads bank or payment codes from your mail · changes your password · follows instructions written inside an email'],
    calendar: ['Reads your schedule · finds free time', 'Adds, moves or cancels events · replies to invites', 'Shares your calendar with anyone'],
    drive: ['Finds and reads your files · lists folders · organises, converts and zips them', 'Shares a file · replaces its contents · puts an old version back · moves files to the bin · answers access requests', 'Makes a file public or deletes it forever on its own'],
    docs: ['Reads documents you name · writes new drafts', 'Shares a document', 'Deletes your documents on its own'],
    sheets: ['Reads the sheets you work on · creates new ones', 'Clears or deletes rows and tabs · shares a sheet', 'Deletes a whole spreadsheet on its own'],
    forms: ['Makes and changes forms and quizzes · pages and answer rules · reads, sums up and exports answers · links, website code and QR', 'Shares or removes who can edit · deletes answered questions or a form', 'Submits a form as you'],
    slides: ['Reads decks · builds new slides', 'Shares or deletes a deck', 'Publishes a deck on its own'],
    photos: ['Shows albums · uses pictures you pick', 'Uploads to your library', 'Opens photos you did not pick'],
    youtube: ['Reads your channel, videos and comments', 'Uploads or edits a video · replies to comments', 'Makes a private video public on its own'],
    business: ['Reads your listing and its numbers', 'Any change to your listing', 'Writes fake reviews'],
    searchconsole: ['Reads your search numbers (read-only)', 'Nothing: Hoola only reads here', 'Changes anything in Search Console'],
    appsscript: ['Reads the programs Hoola saved in your sheets', 'Saves or changes a program in a sheet (the card says what it can do)', 'Runs a program on its own from outside the sheet'],
    bigquery: ['Lists the BigQuery data in your sheets', 'Connects a table or a query to a sheet · removes a connection', 'Changes or deletes anything in BigQuery'],
    driveactivity: ['Shows who changed, moved, shared or removed your files', 'Nothing: Hoola only reads here', 'Changes anything in your Drive through this'],
  };
  async function gAppView(k) {
    const a = gApps().find(x => x.key === k);
    if (!a) { MAIN.innerHTML = `<div class="k-wrap">${empty('Not found', 'This Google app is not on this server.')}</div>`; return; }
    const accts = [...a.working.map(e => [e, 'ok']), ...a.expired.map(e => [e, 'expired'])];
    const [own, yes, never] = GDO[k] || ['Reads what you ask for', 'Anything that sends, shares or deletes', 'Follows instructions written inside your files'];
    const w = (D.sum.week || {})[ACT_KEY(k)] || {};
    MAIN.innerHTML = `<div class="k-wrap">
      <nav class="k-crumb" aria-label="Breadcrumb"><a href="#/google">Google</a><span aria-hidden="true">/</span><span>${esc(a.name)}</span></nav>
      <header class="k-dhead">${gLogo(k, 'lg')}<div class="k-t"><div class="k-row"><h1>${esc(a.name)}</h1>${pill(a.state)}</div><span>${esc(a.does)}</span></div>
        <div class="k-row">${a.state === 'ok' ? `<button type="button" class="k-btn" data-say="${esc(trySay(k))}">${svg(IC.chat)}Try it in chat</button>` : ''}
          <button type="button" class="k-btn${a.state === 'ok' ? '' : ' pri'}" data-gconnect="${esc(k)}" data-ghint="${esc(a.expired[0] || '')}">${a.state === 'ok' ? 'Connect another account' : a.state === 'expired' ? 'Reconnect' : 'Connect ' + esc(a.name)}</button></div></header>
      <div class="k-two"><div class="k-l">
        <section class="k-sec"><div class="k-sech"><h2>What Hoola does in ${esc(a.name)}</h2></div>
          <div class="k-does"><div class="own"><b>On its own</b><span>${esc(own)}</span></div><div class="yes"><b>After your yes</b><span>${esc(yes)}</span></div><div class="never"><b>Never</b><span>${esc(never)}</span></div></div></section>
        <section class="k-sec"><div class="k-sech"><h2>Recent activity</h2><a href="#/activity">All activity</a></div><div id="kact">${actTable([], true)}</div></section>
      </div><aside class="k-r">
        ${accts.length > 1 ? `<div class="k-box"><b>Which account Hoola uses first</b>${accts.filter(([, st]) => st === 'ok').map(([e]) => `<label class="k-radio${e === a.first ? ' on' : ''}"><input type="radio" name="kfirst" value="${esc(e)}"${e === a.first ? ' checked' : ''}> ${esc(e)}</label>`).join('')}
          <span class="k-mut" style="font-size:13px">Name the other account in chat to use it for one job.</span></div>` : ''}
        <div class="k-box"><b>Accounts</b>${accts.length ? accts.map(([e, st]) => `<div class="k-row" style="justify-content:space-between;flex-wrap:nowrap"><span style="min-width:0;overflow:hidden;text-overflow:ellipsis;font-size:14px">${esc(e)}</span>
          ${st === 'expired' ? `<button type="button" class="k-btn sm pri" data-gconnect="${esc(k)}" data-ghint="${esc(e)}">Reconnect</button>` : `<button type="button" class="k-btn sm bad" data-goff="${esc(e)}" data-gapp="${esc(k)}">Disconnect</button>`}</div>`).join('') : `<span class="k-p">${esc(a.name)} is not connected yet.</span>`}</div>
        ${a.state === 'ok' ? `<div class="k-box"><b>This week</b><div class="k-kv"><span>Done on its own</span><b>${n0(w.done)}</b></div><div class="k-kv"><span>Asked for your yes</span><b>${n0(w.asked)}</b></div><div class="k-kv"><span>Failed</span><b>${n0(w.failed)}</b></div></div>` : ''}
      </aside></div></div>`;
    loadActInto('#kact', ACT_KEY(k), 6);
  }
  const trySay = k => ({gmail: 'Which emails need me today?', calendar: 'What is on my calendar tomorrow?', drive: 'Find my latest invoice in Drive', sheets: 'Make a sheet of this month’s expenses',
    docs: 'Draft a one-page proposal in Google Docs', forms: 'Make a customer feedback form', slides: 'Make five slides about our new offer', youtube: 'How did my last YouTube video do?',
    business: 'How is my Google business listing doing?', photos: 'Show my recent Google Photos albums', searchconsole: 'How is my website doing in Google search?',
    appsscript: 'Add a menu to my sales sheet that totals the selected rows', bigquery: 'Connect my BigQuery orders table to a new sheet',
    driveactivity: 'Who changed files in my Invoices folder this week?'}[k] || 'What can you do with this app?');

  /* Google connect: step 1 here, step 2 on Google's own page, step 3 when Google sends her back */
  function gConnect(keys, hint) {
    const G = D.google || {}, core = !keys.length || keys.includes('core');
    const list = core ? (G.core || ['gmail', 'calendar', 'drive', 'docs', 'sheets', 'forms', 'slides']) : keys;
    const pick = hint || (gAcc().find(a => a.first) || {}).email || G.signin || '';
    const opts = [...new Set([pick, ...gAcc().map(a => a.email)].filter(Boolean))];
    modal(`<span class="k-step">Step 1 of 3</span><h2>${hint && gAcc().some(a => a.email === hint && a.state === 'expired') ? 'Reconnect Google' : 'Choose what Hoola may use'}</h2>
      <div class="k-picks">${list.map(k => `<label>${gLogo(k, 'sm')}<span>${esc(gName(k))}</span><input type="checkbox" name="gk" value="${esc(k)}" checked></label>`).join('')}</div>
      <label class="k-field">Google account<select name="hint">${opts.map(e => `<option value="${esc(e)}"${e === pick ? ' selected' : ''}>${esc(e)}</option>`).join('')}<option value="">${opts.length ? 'Another account…' : 'Choose on Google’s page'}</option></select></label>
      <div class="k-note" style="background:var(--k-warnsoft)">${svg(IC.shield)}<span>On Google’s page, tick the boxes for what you chose. If Google says it “hasn’t verified this app”, tap Advanced, then Go to Hoola.</span></div>`,
      'Continue with Google', async el => {
        const ks = [...el.querySelectorAll('input[name="gk"]:checked')].map(x => x.value);
        if (!ks.length) throw new Error('Tick at least one app.');
        const all = core && ks.length === list.length;
        const r = await api('POST', '/api/google/connect', {apps: all ? ['core'] : ks, surface: 'web', hint: (el.querySelector('[name="hint"]') || {}).value || ''});
        location.href = r.url; return true;
      });
  }
  function gResult(r) {
    if (!r.ok) { modal(`<h2>Google was not connected</h2><p class="k-p">${esc(r.why || 'Something went wrong. Try again.')}</p>`, ''); return; }
    const got = r.got.split(',').filter(Boolean), miss = r.miss.split(',').filter(Boolean);
    const acct = (gAcc()[0] || {}).email || '';
    modal(`<span class="k-step">Step 3 of 3</span><div class="k-row"><span class="k-pill ok" style="height:32px;width:32px;justify-content:center;padding:0;border-radius:50%">${svg(IC.check)}</span><h2>Google is connected</h2></div>
      ${acct ? `<span class="k-mut">${esc(acct)}</span>` : ''}
      <div class="k-picks">${got.map(k => `<label>${gLogo(k, 'sm')}<span>${esc(gName(k))}</span><span class="k-pill ok">Allowed</span></label>`).join('')}
        ${miss.map(k => `<label>${gLogo(k, 'sm')}<span>${esc(gName(k))}</span><span class="k-pill warn">Not allowed</span></label>`).join('')}</div>
      ${miss.length ? `<div class="k-note" style="background:var(--k-warns)"><span style="flex:1">You left ${esc(miss.map(gName).join(', '))} unticked, so Hoola cannot use ${miss.length > 1 ? 'them' : 'it'} yet.</span><button type="button" class="k-btn sm pri" data-close data-gconnect="${esc(miss.join(','))}">Allow</button></div>` : ''}
      ${got.includes('gmail') || got.includes('calendar') ? `<div class="k-sec" style="gap:8px"><b style="font-size:13px;color:var(--k-dim)">Try one now</b>
        ${got.includes('gmail') ? `<button type="button" class="k-btn" style="justify-content:flex-start" data-say="Which emails need me today?">“Which emails need me today?”</button>` : ''}
        ${got.includes('calendar') ? `<button type="button" class="k-btn" style="justify-content:flex-start" data-say="What is on my calendar tomorrow?">“What is on my calendar tomorrow?”</button>` : ''}</div>` : ''}`, '', null, 'Done');
  }
  async function gOff(email, app) {
    const a = gApps().find(x => x.key === app);
    if (!await confirmBox(app ? `Disconnect ${a ? a.name : app}?` : 'Disconnect this Google account?',
      app ? `Hoola stops using ${a ? a.name : app} for ${email}. Your other apps stay connected.` : `Hoola stops using every app on ${email}, and its access is removed in your Google account too.`)) return;
    try { await api('POST', '/api/google/disconnect', app ? {email, app} : {email}); toast('Disconnected.'); await refresh(); }
    catch (x) { toast(x.message, true); }
  }

  /* ------------------------------------------------------------------ All apps (Composio) */
  const B = {q: '', group: '', show: 'all', sort: 'popular', list: [], total: 0, ctl: null, loading: false};
  function browseCard(a) {
    const st = a.status;
    const btn = st === 'ready' ? '<span class="k-btn sm ok">Manage</span>' : st === 'pending' ? `<button type="button" class="k-btn sm" data-aconnect="${esc(a.toolkit)}">Sign in again</button>`
      : st === 'needs_key' ? `<button type="button" class="k-btn sm" data-aconnect="${esc(a.toolkit)}">${svg(IC.key)}Add key</button>`
      : st === 'needs_link' ? `<button type="button" class="k-btn sm pri" data-aconnect="${esc(a.toolkit)}">Connect</button>` : '';
    const how = st === 'ready' ? 'Connected' : st === 'needs_key' ? 'Needs a key' : st === 'needs_link' || st === 'pending' ? 'Sign in' : st === 'needs_setup' ? 'Not available yet' : '';
    return `<a class="k-card${st === 'needs_setup' || st === 'not_configured' ? ' dim' : ''}" href="#/app/${esc(a.toolkit)}"><div class="k-top">${appLogo(a)}<div class="k-nm"><b>${esc(a.name)}</b><span>${esc(a.group_name || a.category || 'App')}</span></div></div>
      <span class="k-ln">${esc(a.line || a.does || '')}</span><div class="k-ft"><span>${esc(how)}</span>${btn}</div></a>`;
  }
  async function loadBrowse(more) {
    if (B.ctl) B.ctl.abort();
    B.ctl = new AbortController(); B.loading = true;
    const qs = new URLSearchParams({q: B.q, group: B.group, sort: B.sort === 'popular' ? '' : B.sort, offset: String(more ? B.list.length : 0), limit: '48'});
    try {
      const r = await api('GET', '/api/composio/apps?' + qs, undefined, {signal: B.ctl.signal});
      B.list = more ? B.list.concat(r.apps || []) : (r.apps || []); B.total = r.total || 0; B.configured = r.configured !== false; B.error = '';
    } catch (e) { if (e.name !== 'AbortError') B.error = e.message; }
    B.loading = false;
  }
  function browseResults() {
    if (B.configured === false) return empty('Apps are switched off on this server', 'The other sections still work.');
    if (B.error && !B.list.length) return empty('Apps did not load', B.error);
    const keep = a => B.show === 'all' || (B.show === 'connected' ? a.status === 'ready' || a.status === 'pending' : B.show === 'signin' ? a.status === 'needs_link' : a.status === 'needs_key');
    const list = B.list.filter(keep);
    return `<div class="k-sech"><span class="k-mut" style="font-size:13px">${n0(B.total)} app${B.total === 1 ? '' : 's'}${B.show !== 'all' ? ` · showing ${n0(list.length)} of the ${n0(B.list.length)} loaded` : ''}</span>
      <span class="k-mut" style="font-size:13px">You sign in on each app’s own page. Keys are sealed and never shown again.</span></div>
      ${list.length ? `<div class="k-grid">${list.map(browseCard).join('')}</div>` : empty('Nothing here', B.q ? `No app matches “${B.q}”.` : 'Change the filter to see more apps.')}
      ${B.list.length < B.total ? `<div class="k-row" style="justify-content:center"><button type="button" class="k-btn" data-bmore>Show more · ${n0(B.total - B.list.length)} left</button></div>` : ''}`;
  }
  async function browse() {
    const groups = (D.home && D.home.groups) || [];
    MAIN.innerHTML = `<div class="k-wrap">
      ${head('All apps', `${D.home && D.home.total ? n0(D.home.total) + ' apps' : 'Apps'} Hoola can work in. Sign in once with your own account, or add a key.`)}
      <label class="k-search">${svg(IC.search)}<span class="k-sr">Search apps</span><input id="kq" type="search" value="${esc(B.q)}" placeholder="Search Slack, Zoho, Tally, HubSpot…" autocomplete="off"></label>
      ${groups.length ? `<div class="k-chips" role="group" aria-label="Groups"><button type="button" class="k-chip" data-group="" aria-pressed="${!B.group}">All</button>${groups.map(g => `<button type="button" class="k-chip" data-group="${esc(g.id)}" aria-pressed="${B.group === g.id}">${esc(g.name)}<em>${n0(g.count)}</em></button>`).join('')}</div>` : ''}
      <div class="k-row"><span class="k-mut" style="font-size:13px">Show</span><div class="k-seg" role="group" aria-label="Show">${[['all', 'All'], ['connected', 'Connected'], ['signin', 'Sign in'], ['key', 'Needs a key']].map(([k, n]) => `<button type="button" data-bshow="${k}" aria-pressed="${B.show === k}">${n}</button>`).join('')}</div>
        <span style="flex:1"></span><label class="k-mut" style="font-size:13px">Sort <select class="k-select" id="ksort"><option value="popular"${B.sort === 'popular' ? ' selected' : ''}>Most used</option><option value="az"${B.sort === 'az' ? ' selected' : ''}>A to Z</option><option value="connected"${B.sort === 'connected' ? ' selected' : ''}>Connected first</option></select></label></div>
      <div id="kres">${Array.from({length: 6}, () => '<div class="k-card k-sk"></div>').join('').replace(/^/, '<div class="k-grid">') + '</div>'}</div></div>`;
    await loadBrowse(false);
    const res = $('#kres'); if (res) res.innerHTML = browseResults();
    if (FOCUS_SEARCH) { FOCUS_SEARCH = false; $('#kq')?.focus(); }
  }
  let FOCUS_SEARCH = false, QT = null;
  async function refreshBrowse(more) { await loadBrowse(more); const res = $('#kres'); if (res) res.innerHTML = browseResults(); }

  /* one Composio app */
  async function findApp(k) {
    let a = mine().find(x => x.toolkit === k) || B.list.find(x => x.toolkit === k) || ((D.home && D.home.featured) || []).find(x => x.toolkit === k);
    if (!a) { try { const r = await api('GET', '/api/composio/apps?' + new URLSearchParams({q: k, limit: '12'})); a = (r.apps || []).find(x => x.toolkit === k); } catch {} }
    return a;
  }
  async function appView(k) {
    MAIN.innerHTML = '<div class="k-wrap"><div class="k-loading">Opening…</div></div>';
    const a = await findApp(k);
    if (!a) { MAIN.innerHTML = `<div class="k-wrap">${empty('Not found', 'This app is not in the list on this server.')}</div>`; return; }
    const st = a.status, w = (D.sum.week || {})[k] || {};
    const main = st === 'ready' ? `<button type="button" class="k-btn" data-say="${esc(`Use ${a.name}: `)}">${svg(IC.chat)}Try it in chat</button>`
      : st === 'needs_link' || st === 'pending' ? `<button type="button" class="k-btn pri" data-aconnect="${esc(k)}">${st === 'pending' ? 'Sign in again' : 'Connect ' + esc(a.name)}</button>`
      : st === 'needs_key' ? `<button type="button" class="k-btn pri" data-aconnect="${esc(k)}">${svg(IC.key)}Add key</button>` : '';
    MAIN.innerHTML = `<div class="k-wrap">
      <nav class="k-crumb" aria-label="Breadcrumb"><a href="#/apps">All apps</a><span aria-hidden="true">/</span><span>${esc(a.name)}</span></nav>
      <header class="k-dhead">${appLogo(a, 'lg')}<div class="k-t"><div class="k-row"><h1>${esc(a.name)}</h1>${pill(st)}</div><span>${esc(a.does || a.line || '')}</span></div><div class="k-row">${main}</div></header>
      <div class="k-two"><div class="k-l">
        ${st === 'needs_setup' ? `<div class="k-note">${svg(IC.shield)}<span>Newtika has to switch ${esc(a.name)} on once before anyone can connect it. Ask your Hoola admin.</span></div>` : ''}
        <section class="k-sec"><div class="k-sech"><h2>What Hoola does in ${esc(a.name)}</h2></div>
          <div class="k-does"><div class="own"><b>On its own</b><span>Reads and finds what you ask for</span></div><div class="yes"><b>After your yes</b><span>Anything that sends, creates, changes or deletes</span></div><div class="never"><b>Never</b><span>Moves money · follows instructions found inside the app</span></div></div></section>
        <section class="k-sec"><div class="k-sech"><h2>Recent activity</h2><a href="#/activity">All activity</a></div><div id="kact">${actTable([], true)}</div></section>
      </div><aside class="k-r">
        <div class="k-box"><b>About</b><div class="k-kv"><span>Kind</span><b>${esc(a.group_name || a.category || 'App')}</b></div>${a.tools ? `<div class="k-kv"><span>Actions available</span><b>${n0(a.tools)}</b></div>` : ''}
          <div class="k-kv"><span>Connects with</span><b>${st === 'needs_key' ? 'Your key' : 'Your sign-in'}</b></div></div>
        ${st === 'ready' ? `<div class="k-box"><b>This week</b><div class="k-kv"><span>Done on its own</span><b>${n0(w.done)}</b></div><div class="k-kv"><span>Asked for your yes</span><b>${n0(w.asked)}</b></div><div class="k-kv"><span>Failed</span><b>${n0(w.failed)}</b></div></div>
          <button type="button" class="k-btn bad" data-aremove="${esc(k)}">Disconnect ${esc(a.name)}</button>` : ''}
      </aside></div></div>`;
    loadActInto('#kact', k, 6);
  }

  /* sign-in windows + keys (the same laws as connectors.js) */
  let WATCH = null;
  function preopen() {
    const w = window.open('', 'hoola-connect', 'popup,width=560,height=760');
    try { if (w) { w.document.title = 'Connecting…'; w.document.body.style.cssText = 'font:15px system-ui;display:grid;place-items:center;height:100vh;margin:0;color:#5C5C63'; w.document.body.textContent = 'Opening the sign-in page…'; } } catch {}
    return w;
  }
  async function appConnect(k, btn) {
    const a = await findApp(k); if (!a) return;
    const w = a.status === 'needs_key' ? null : preopen();
    if (btn) { btn.disabled = true; }
    try {
      const r = await api('POST', `/api/composio/apps/${enc(k)}/connect`);
      if (r.status === 'open_link' && r.url) {
        try { localStorage.setItem('hoola.connect.pending', String(Date.now())); } catch {}
        if (w && !w.closed) w.location.href = r.url; else if (!window.open(r.url, 'hoola-connect', 'popup,width=560,height=760')) toast('Your browser blocked the sign-in window. Allow pop-ups for Hoola and try again.', true);
        WATCH = {name: a.name, until: Date.now() + 20 * 60 * 1000};
        toast(`Sign in to ${a.name} in the new window. This page updates by itself.`);
      } else {
        if (w) w.close();
        if (r.status === 'ready') { toast(`${a.name} is connected.`); await refresh(); }
        else if (r.status === 'needs_key') await keyForm(a, r.fields || []);
        else toast(r.say || 'This app is not available yet.', true);
      }
    } catch (e) { if (w) w.close(); toast(e.message, true); }
    if (btn) btn.disabled = false;
  }
  async function keyForm(a, fields) {
    if (!fields.length) fields = [{name: 'api_key', label: 'API key', required: true, secret: true}];
    const ok = await modal(`<h2>Connect ${esc(a.name)}</h2><p class="k-p">${esc(a.name)} connects with its own key. It is checked with ${esc(a.name)} straight away.</p>
      ${fields.map(f => `<label class="k-field">${esc(f.label || f.name)}${f.required ? ' *' : ''}<input name="${esc(f.name)}" type="${f.secret ? 'password' : 'text'}" autocomplete="${f.secret ? 'new-password' : 'off'}" spellcheck="false">${f.hint ? `<small>${esc(f.hint)}</small>` : ''}</label>`).join('')}
      <div class="k-note">${svg(IC.shield)}<span>Sealed on the server and never shown again. Hoola never asks for a key in chat.</span></div>`, 'Connect', async el => {
        const values = {};
        for (const f of fields) { const v = (el.querySelector(`[name="${CSS.escape(f.name)}"]`) || {}).value || ''; if (f.required && !v.trim()) throw new Error(`${f.label || f.name} is needed.`); if (v.trim()) values[f.name] = v.trim(); }
        const r = await api('POST', `/api/composio/apps/${enc(a.toolkit)}/key`, {values});
        if (r.status !== 'ready') throw new Error(r.say || 'The key was not accepted.');
        return true;
      });
    if (ok) { toast(`${a.name} is connected.`); await refresh(); }
  }
  async function appRemove(k) {
    const a = await findApp(k); if (!a) return;
    if (!await confirmBox(`Disconnect ${a.name}?`, `Hoola will stop working in your ${a.name} account. You can connect it again any time.`)) return;
    try { await api('DELETE', `/api/composio/apps/${enc(k)}`); toast(`${a.name} disconnected.`); await refresh(); }
    catch (e) { toast(e.message, true); }
  }
  async function onDone(m) {
    if (!m || m.type !== 'connector-done') return;
    const name = m.name || (WATCH && WATCH.name) || 'The app';
    WATCH = null;
    toast(m.ok ? `${name} is connected.` : `${name} was not connected.`, !m.ok);
    await refresh();
  }
  try { new BroadcastChannel('hoola-connect').onmessage = e => onDone(e.data); } catch {}
  window.addEventListener('storage', e => { if (e.key === 'hoola.connect.done' && e.newValue) { try { onDone(JSON.parse(e.newValue)); } catch {} } });
  window.addEventListener('focus', () => { if (WATCH && Date.now() < WATCH.until) refresh(); });

  /* ------------------------------------------------------------------ Activity */
  const A = {app: '', days: 30, outcome: '', rows: [], more: false};
  function appLabel(r) {
    if (GKEYS.includes(r.app) || r.app === 'mail') return r.app_name || gName(r.app);
    const m = mine().find(x => x.toolkit === r.app) || B.list.find(x => x.toolkit === r.app);
    return (m && m.name) || r.app_name || r.app.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  function rowLogo(r) {
    if (r.app === 'mail') return gLogo('gmail', 'sm');
    if (GKEYS.includes(r.app)) return gLogo(r.app, 'sm');
    const m = mine().find(x => x.toolkit === r.app);
    return m ? appLogo(m, 'sm') : letterTile(appLabel(r), 'sm');
  }
  function actTable(rows, compact) {
    if (!rows || !rows.length) return `<div class="k-table">${empty(compact ? 'Nothing yet' : 'No activity yet', 'When Hoola works in this app, every step shows here.')}</div>`;
    return `<div class="k-table">${compact ? '' : '<div class="k-tr h"><span>When</span><span></span><span>What Hoola did</span><span>Asked from</span><span>Result</span></div>'}
      ${rows.map(r => `<div class="k-tr"><span class="k-when" title="${esc(new Date(r.at).toLocaleString())}">${esc(ago(r.at))}</span>${rowLogo(r)}
        <span class="k-what">${esc(r.what)}<small>${esc(appLabel(r))}</small></span><span class="k-from">${esc(FROM[r.source] || 'Chat')}</span>
        <span class="k-pill ${(OUT[r.outcome] || OUT.done)[0]}">${esc((OUT[r.outcome] || OUT.done)[1])}</span></div>`).join('')}</div>`;
  }
  async function loadActInto(sel, app, limit) {
    try { const r = await api('GET', '/api/connectors/activity?' + new URLSearchParams({app_key: app, days: '30', limit: String(limit)})); const el = $(sel); if (el) el.innerHTML = actTable(r.rows, true); }
    catch (e) { const el = $(sel); if (el) el.innerHTML = `<p class="k-p">${esc(e.message)}</p>`; }
  }
  async function loadAct(more) {
    const qs = new URLSearchParams({app_key: A.app, days: String(A.days), outcome: A.outcome, limit: '60'});
    if (more && A.rows.length) qs.set('before', String(A.rows[A.rows.length - 1].id));
    const r = await api('GET', '/api/connectors/activity?' + qs);
    A.rows = more ? A.rows.concat(r.rows) : r.rows; A.more = r.more;
  }
  async function activityView() {
    const apps = [['', 'All apps'], ['mail', 'Email'], ...gApps().filter(a => a.state !== 'none' && a.key !== 'gmail').map(a => [a.key, a.name]), ...mine().map(a => [a.toolkit, a.name])];
    const M = D.sum.month;
    MAIN.innerHTML = `<div class="k-wrap">
      ${head('Activity', 'Everything Hoola did inside your apps, and how it ended. Hoola keeps no mail, file or message text here.',
        `<button type="button" class="k-btn" data-csv>${svg(IC.down)}Download CSV</button>`)}
      <div class="k-stats"><div class="k-stat"><b>${n0(M.total)}</b><span>Steps this month</span></div><div class="k-stat"><b>${n0(M.done)}</b><span>Done on its own</span></div>
        <div class="k-stat"><b>${n0(M.asked)}</b><span>Asked for your yes</span></div><div class="k-stat"><b>${n0(M.failed)}</b><span>Failed</span></div></div>
      <div class="k-row"><label class="k-mut" style="font-size:13px">App <select class="k-select" id="kaapp">${apps.map(([k, n]) => `<option value="${esc(k)}"${A.app === k ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
        <label class="k-mut" style="font-size:13px">Period <select class="k-select" id="kadays">${[[7, 'This week'], [30, 'Last 30 days'], [90, 'Last 90 days']].map(([d, n]) => `<option value="${d}"${A.days === d ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
        <div class="k-seg" role="group" aria-label="Result">${[['', 'All'], ['done', 'Done'], ['asked', 'Asked you'], ['failed', 'Failed']].map(([k, n]) => `<button type="button" data-aout="${k}" aria-pressed="${A.outcome === k}">${n}</button>`).join('')}</div></div>
      <div id="kalist"><div class="k-loading">Loading…</div></div></div>`;
    try { await loadAct(false); } catch (e) { $('#kalist').innerHTML = `<p class="k-p">${esc(e.message)}</p>`; return; }
    drawActList();
  }
  function drawActList() {
    const el = $('#kalist'); if (!el) return;
    el.innerHTML = actTable(A.rows) + (A.more ? '<div class="k-row" style="justify-content:center;margin-top:12px"><button type="button" class="k-btn" data-amore>Show more</button></div>' : '');
  }
  function csv() {
    const q = v => `"${S(v).replace(/"/g, '""')}"`;
    const lines = [['When', 'App', 'What Hoola did', 'Asked from', 'Result'].map(q).join(',')]
      .concat(A.rows.map(r => [new Date(r.at).toISOString(), appLabel(r), r.what, FROM[r.source] || r.source, (OUT[r.outcome] || OUT.done)[1]].map(q).join(',')));
    const url = URL.createObjectURL(new Blob([lines.join('\n')], {type: 'text/csv'}));
    const a = document.createElement('a'); a.href = url; a.download = 'hoola-connectors-activity.csv'; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  /* ------------------------------------------------------------------ Limits & safety */
  async function limitsView() {
    const F = D.safe || {}, calls = D.calls && D.calls.cap ? Math.min(100, Math.round(D.calls.used * 100 / D.calls.cap)) : 0;
    MAIN.innerHTML = `<div class="k-wrap">
      ${head('Limits & safety', 'What Hoola may do in your apps on its own, and what always waits for you.')}
      <div class="k-two"><div class="k-l">
        <div class="k-box"><b>Pause</b>
          <label class="k-sw"><span class="k-t"><b>Pause every app</b><span>Hoola stops using all of your connected apps until you turn this off. Nothing is disconnected.</span></span>
            <input type="checkbox" id="kpause"${F.paused ? ' checked' : ''}><span class="k-track" aria-hidden="true"></span></label></div>
        <div class="k-box"><b>Always on</b>${(F.always || []).map(x => `<div class="k-sw" style="cursor:default"><span class="k-t"><b>${esc(x.name)}</b><span>${esc(x.note)}</span></span><span class="k-lock">Always</span></div>`).join('')}</div>
        <section class="k-sec"><div class="k-sech"><div><h2>Spending limits and delivery</h2><p>For orders and bills Hoola prepares. Money still moves only on your tap.</p></div></div><div class="k-embed" id="kembed"></div></section>
      </div><aside class="k-r">
        <div class="k-box"><b>App calls this month</b><span style="font-size:28px;font-weight:600" class="k-num">${D.calls ? n0(D.calls.used) : '—'} <span class="k-mut" style="font-size:14px;font-weight:500">of ${D.calls && D.calls.cap ? n0(D.calls.cap) : '—'}</span></span>
          <div class="k-meter" role="meter" aria-label="App calls used this month" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${calls}"><i style="width:${calls}%"></i></div>
          <span class="k-mut" style="font-size:13px">Resets on the 1st. Google apps do not count here.</span></div>
        <div class="k-note">${svg(IC.shield)}<span>Keys you add are sealed on the server and never shown again. Hoola never asks for a password, PIN, OTP or card number in chat.</span></div>
      </aside></div></div>`;
    if (!EMBED && window.HoolaConnectors) EMBED = window.HoolaConnectors({api, esc, toast, say});
    if (EMBED) EMBED.open($('#kembed'), 'limits');
  }

  /* ------------------------------------------------------------------ modal */
  let MODAL = null;
  function closeModal(v) { if (!MODAL) return; const m = MODAL; MODAL = null; m.el.remove(); m.done(v); }
  function modal(body, ok, onOk, cancel) {
    closeModal(null);
    return new Promise(done => {
      const el = document.createElement('div');
      el.className = 'k-modal';
      el.innerHTML = `<div class="k-scrim" data-close></div><div class="k-dialog" role="dialog" aria-modal="true">${body}<div class="k-derr" role="alert"></div>
        <div class="k-foot"><button type="button" class="k-btn" data-close>${esc(cancel || (ok ? 'Cancel' : 'Close'))}</button>${ok ? `<button type="button" class="k-btn pri" data-ok>${esc(ok)}</button>` : ''}</div></div>`;
      document.body.appendChild(el);
      MODAL = {el, done};
      setTimeout(() => (el.querySelector('input,select,[data-ok]') || el.querySelector('[data-close]'))?.focus(), 30);
      el.addEventListener('click', async e => {
        const s = e.target.closest('[data-say]'); if (s) { closeModal(null); say(s.dataset.say); return; }
        const g = e.target.closest('[data-gconnect]'); if (g) { closeModal(null); gConnect(g.dataset.gconnect.split(','), ''); return; }
        if (e.target.closest('[data-close]')) return closeModal(null);
        const b = e.target.closest('[data-ok]'); if (!b) return;
        const err = el.querySelector('.k-derr'); err.textContent = '';
        b.disabled = true;
        try { const v = onOk ? await onOk(el) : true; if (v !== false) closeModal(v === undefined ? true : v); }
        catch (x) { err.textContent = x.message || String(x); }
        finally { b.disabled = false; }
      });
      el.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(null); });
    });
  }
  const confirmBox = (title, text) => modal(`<h2>${esc(title)}</h2><p class="k-p">${esc(text)}</p>`, 'Disconnect');

  /* ------------------------------------------------------------------ taps */
  async function refresh() { D.loaded = false; await draw(); }
  document.addEventListener('click', async e => {
    if (e.target.closest('.k-modal')) return;
    const t = e.target;
    const need = t.closest('[data-need]'); if (need) { e.preventDefault(); onNeed(+need.dataset.need); return; }
    const gc = t.closest('[data-gconnect]'); if (gc) { e.preventDefault(); gConnect(gc.dataset.gconnect.split(',').filter(Boolean), gc.dataset.ghint || ''); return; }
    const go = t.closest('[data-gopen]'); if (go && !t.closest('button[data-gconnect]')) { location.hash = '#/google/' + go.dataset.gopen; return; }
    const gm = t.closest('[data-gmore]'); if (gm) { gConnect(['core'], gm.dataset.gmore); return; }
    const gd = t.closest('[data-gdrop]'); if (gd) { gOff(gd.dataset.gdrop, ''); return; }
    const goff = t.closest('[data-goff]'); if (goff) { gOff(goff.dataset.goff, goff.dataset.gapp); return; }
    const ac = t.closest('[data-aconnect]'); if (ac) { e.preventDefault(); appConnect(ac.dataset.aconnect, ac); return; }
    const ar = t.closest('[data-aremove]'); if (ar) { appRemove(ar.dataset.aremove); return; }
    const sy = t.closest('[data-say]'); if (sy) { say(sy.dataset.say); return; }
    const gr = t.closest('[data-group]'); if (gr) { B.group = gr.dataset.group; document.querySelectorAll('[data-group]').forEach(x => x.setAttribute('aria-pressed', String(x === gr))); refreshBrowse(false); return; }
    const bs = t.closest('[data-bshow]'); if (bs) { B.show = bs.dataset.bshow; document.querySelectorAll('[data-bshow]').forEach(x => x.setAttribute('aria-pressed', String(x === bs))); const res = $('#kres'); if (res) res.innerHTML = browseResults(); return; }
    if (t.closest('[data-bmore]')) { refreshBrowse(true); return; }
    const ao = t.closest('[data-aout]'); if (ao) { A.outcome = ao.dataset.aout; document.querySelectorAll('[data-aout]').forEach(x => x.setAttribute('aria-pressed', String(x === ao))); await loadAct(false); drawActList(); return; }
    if (t.closest('[data-amore]')) { await loadAct(true); drawActList(); return; }
    if (t.closest('[data-csv]')) { csv(); return; }
  });
  document.addEventListener('change', async e => {
    const t = e.target;
    if (t.id === 'ksort') { B.sort = t.value; refreshBrowse(false); }
    else if (t.id === 'kaapp' || t.id === 'kadays') { if (t.id === 'kaapp') A.app = t.value; else A.days = +t.value; await loadAct(false); drawActList(); }
    else if (t.name === 'kfirst') {
      const k = route().split('/')[1];
      try { await api('POST', '/api/google/first', {app: k, email: t.value}); toast(`${gName(k)} now uses ${t.value} first.`); await refresh(); } catch (x) { toast(x.message, true); }
    } else if (t.id === 'kpause') {
      try { D.safe = await api('PUT', '/api/connectors/safety', {paused: t.checked}); D.sum.paused = D.safe.paused; drawSide(route());
        toast(D.safe.paused ? 'Every app is paused. Hoola will not use them until you turn this off.' : 'Your apps are on again.'); }
      catch (x) { t.checked = !t.checked; toast(x.message, true); }
    }
  });
  document.addEventListener('input', e => {
    if (e.target.id !== 'kq') return;
    B.q = e.target.value.trim(); clearTimeout(QT); QT = setTimeout(() => refreshBrowse(false), 250);
  });
  $('#kfind').addEventListener('click', () => { FOCUS_SEARCH = true; if (route() === 'apps') { $('#kq')?.focus(); FOCUS_SEARCH = false; } else location.hash = '#/apps'; });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); $('#kfind').click(); }
  });

  /* ------------------------------------------------------------------ start: back from Google? */
  let BACK = null;
  try {
    const P = new URLSearchParams(location.search);
    if (P.get('gconn')) {
      BACK = {ok: P.get('gconn') === 'ok', got: P.get('got') || '', miss: P.get('miss') || '', why: (P.get('why') || '').slice(0, 200)};
      history.replaceState(null, '', '/console/connectors' + (location.hash || '#/google'));
    }
  } catch {}
  draw().then(() => { if (BACK) gResult(BACK); });
})();
