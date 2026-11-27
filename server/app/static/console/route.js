/* v0.999.232 HOOLA ROUTE, THE EDITOR (R1 of the Route plan; owner: design canvas -> "GO BUILD").
   (v0.999.87 HOOLA ROUTE first drew her automations as one page; v0.999.128 checked every part of it.)

   Views (hash routes): #/ home (ask in words, numbers, Needs you, your routes, templates) · #/routes all routes ·
   #/needs what waits for her · #/r/<id> THE EDITOR (a canvas of the route's steps: drag, add, change, delete, notes,
   undo, zoom, mini-map, Test route, Ask Hoola beside it) · #/r/<id>/runs · #/r/<id>/settings · #/runs every run ·
   #/run/<id> one run step by step · #/templates.
   The engine is DHARA (agent/dhara_tools.py). The canvas saves through the engine's own validation
   (PUT /api/route/routes/<id>/graph); Ask Hoola is the route's own chat (kind 'route'), Hoola changes the same route
   with dhara_save and the canvas redraws it, with Keep / Undo. A route made here starts OFF: nothing runs until she
   switches it on. Money and sending still wait for her tap inside the engine.
   Global by design: times show in her browser's own time zone; nothing on the page assumes a country. */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const fmtN = v => Number(v || 0).toLocaleString();
  const clone = v => JSON.parse(JSON.stringify(v));
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  if (!TOKEN) { location.replace('/console/'); return; }
  const MAIN = $('#main');
  const TZ = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch { return ''; } })();

  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) { const e = new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`); e.status = r.status; throw e; }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = d => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>', play: '<path d="M7 5l12 7-12 7z"/>', plus: '<path d="M12 5v14M5 12h14"/>',
    route: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/><path d="M8 6h3a5 5 0 0 1 5 5M8 18h3a5 5 0 0 0 5-5"/>',
    back: '<path d="M15 6l-6 6 6 6"/>', check: '<path d="M5 12l5 5 9-10"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>',
    http: '<path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
    code: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4"/>', wait: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', notify: '<path d="M4 5h16v11H9l-5 4z"/>',
    router: '<path d="M4 12h6M10 12l6-6M10 12l6 6M10 12h10"/>', filter: '<path d="M4 5h16l-6 8v6l-4-2v-4z"/>', loop: '<path d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3M18 3v4h-4M6 21v-4h4"/>',
    set: '<path d="M4 7h16M4 12h10M4 17h7"/>', approval: '<path d="M15 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM3 21a8 8 0 0 1 16 0"/>',
    bolt: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>', cal: '<path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2z"/>',
    hook: '<path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c.01-.7.2-1.4.57-2"/><path d="m6 17 3.13-5.78c.53-.97.1-2.18-.5-3.1a4 4 0 1 1 6.89-4.06"/><path d="m12 6 3.13 5.73C15.66 12.7 16.9 13 18 13a4 4 0 0 1 0 8"/>',
    hand: '<path d="M7 11V5a2 2 0 0 1 4 0v5M11 10V4a2 2 0 0 1 4 0v6M15 10V6a2 2 0 0 1 4 0v8a7 7 0 0 1-7 7h-1a7 7 0 0 1-6-3.4L3 15a2 2 0 0 1 3.4-2L7 14"/>',
    note: '<path d="M5 3h14v14l-4 4H5z"/><path d="M15 21v-4h4"/>', undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 0 10h-3"/>',
    redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h3"/>', fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    tidy: '<rect x="3" y="4" width="6" height="5" rx="1"/><rect x="15" y="4" width="6" height="5" rx="1"/><rect x="9" y="15" width="6" height="5" rx="1"/><path d="M6 9v3h12V9M12 12v3"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>', trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    spark: '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/>', more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    store: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    pin: '<path d="M12 17v5M9 3h6l-1 7 4 3H6l4-3z"/>', expand: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>'};
  const MARK = c => (window.HoolaMark ? HoolaMark.svg({color: c || '#FFFFFF'}) : '');
  try { $('#brandMark').innerHTML = MARK('#FFFFFF'); } catch {}

  // a broken logo becomes the app's first letter (no inline handlers: the page's CSP allows none)
  document.addEventListener('error', e => {
    const im = e.target;
    if (im && im.tagName === 'IMG' && im.dataset.fb !== undefined) { const p = im.parentNode; if (p) p.textContent = im.dataset.fb || '?'; }
  }, true);
  const APP_NAME = {gmail: 'Gmail', googlesheets: 'Google Sheets', googledrive: 'Google Drive', googlecalendar: 'Google Calendar',
    googledocs: 'Google Docs', google: 'Google', whatsapp: 'WhatsApp', slack: 'Slack', notion: 'Notion', hubspot: 'HubSpot',
    quickbooks: 'QuickBooks', xero: 'Xero', stripe: 'Stripe', shopify: 'Shopify', instagram: 'Instagram', youtube: 'YouTube',
    telegram: 'Telegram', trello: 'Trello', airtable: 'Airtable', github: 'GitHub', zoom: 'Zoom', salesforce: 'Salesforce'};
  const appName = slug => APP_NAME[S(slug).toLowerCase()] || S(slug).replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  // the engine's error text, said plainly: "step 'x' (tool): route 'Paid online': ..." -> "Paid online › x: ..."
  const human = e => S(e).replace(/route '([^']+)': /g, '$1 › ').replace(/step '([^']+)' \([a-z_]+\): /g, (m, id) => id.replace(/_/g, ' ') + ': ')
    .replace(/^([^›:]+): ([^:]+ › )/, '$2');
  const KIND_TILE = {data: 'data', approval: 'warm', notify: 'warm', condition: 'flow', router: 'flow', filter: 'flow', loop: 'flow', wait: 'flow',
    set: 'data', code: 'data', http: 'core'};
  function appTile(a, type, op) {
    a = a || {};
    if (a.kind === 'hoola') return `<span class="ap hoola" title="Hoola">${MARK('#FFFFFF')}</span>`;
    if (a.kind === 'app' && a.slug) return `<span class="ap" title="${esc(appName(a.slug))}"><img src="/api/logo/cmp/${enc(a.slug)}" alt="${esc(appName(a.slug))}" data-fb="${esc(appName(a.slug).split(' ').map(w => w[0]).join('').slice(0, 2))}"></span>`;
    const t = type || a.kind || '';
    const ic = (op && OPIC[op]) || {condition: IC.router, router: IC.route}[t] || IC[t] || IC.set;
    return `<span class="ap k-${KIND_TILE[t] || 'core'}" title="${esc(t)}">${svg(ic)}</span>`;
  }
  const PILL = {ok: 'ok', running: 'v', waiting: 'warn', error: 'bad', stopped: 'bad', off: ''};
  const RUNPILL = {done: ['ok', 'Done'], failed: ['bad', 'Failed'], incomplete: ['bad', 'Incomplete'], waiting_approval: ['warn', 'Waiting for you'],
    sleeping: ['v', 'Waiting'], running: ['v', 'Running'], queued: ['v', 'Queued'], stopped: ['', 'Stopped']};
  const runPill = st => { const [c, t] = RUNPILL[st] || ['', st]; return `<span class="pill ${c}"><span class="dot"></span>${esc(t)}</span>`; };
  const when = ts => { if (!ts) return ''; const d = new Date(Number(ts) * 1000), m = Math.round((Date.now() - d) / 60000);
    if (m < 1) return 'just now'; if (m < 60) return m + ' min ago'; if (m < 1440) return Math.floor(m / 60) + ' h ago';
    return d.toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); };
  const at = ts => ts ? new Date(Number(ts) * 1000).toLocaleString(undefined, {weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';
  const nice = n => S(n).replace(/_/g, ' ');

  // a tiny, safe reader for Hoola's replies (paragraphs, **bold**, `code`, lists) - text is escaped first
  function md(t) {
    const inline = s => esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');
    const out = []; let list = null;
    S(t).replace(/```[\s\S]*?```/g, m => '\n' + m.replace(/```\w*\n?|```/g, '') + '\n').split('\n').forEach(line => {
      const li = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/);
      if (li) { if (!list) { list = []; } list.push(`<li>${inline(li[1])}</li>`); return; }
      if (list) { out.push(`<ul>${list.join('')}</ul>`); list = null; }
      const h = line.match(/^#{1,4}\s+(.*)$/);
      if (h) out.push(`<p><b>${inline(h[1])}</b></p>`); else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
    });
    if (list) out.push(`<ul>${list.join('')}</ul>`);
    return out.join('');
  }

  function setNav(k) {
    document.querySelectorAll('.side [data-nav]').forEach(a => a.setAttribute('aria-current', a.dataset.nav === k ? 'page' : 'false'));
  }
  let SUM = null;
  async function needCount() {
    try {
      SUM = await api('GET', '/api/route/summary');
      const n = $('#needCount'); n.textContent = SUM.needs_count; n.hidden = !SUM.needs_count;
      const a = $('#allCount'); if (a) { a.textContent = SUM.routes_total; a.hidden = !SUM.routes_total; }
      const fl = $('#folders');
      if (fl) fl.innerHTML = (SUM.folders || []).length ? `<div class="sl">Folders</div>${SUM.folders.map(f =>
        `<a class="nav sub" href="#/routes/${enc(f)}">${svg('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>')}${esc(f)}</a>`).join('')}` : '';
      const ft = $('#sideFoot'); if (ft) ft.innerHTML = `Runs today <b>${fmtN(SUM.runs_today)}</b>${TZ ? `<br>Time zone <b>${esc(TZ)}</b>` : ''}`;
    } catch {}
  }

  // ---------------------------------------------------------------- a new route, then into the editor
  const ASK_KEY = 'hoola.route.ask';
  async function newRoute(title, ask, folder) {
    const r = await api('POST', '/api/route/routes', {title: title || 'New route', folder: folder || ''});
    if (ask) { try { sessionStorage.setItem(ASK_KEY, JSON.stringify({id: r.id, text: ask})); } catch {} }
    location.hash = '#/r/' + enc(r.id);
  }
  const titleOf = t => { const w = S(t).replace(/[^\p{L}\p{N}\s]/gu, ' ').trim().split(/\s+/).slice(0, 7).join(' '); return w || 'New route'; };

  // ---------------------------------------------------------------- tables
  const tog = (id, on, name) => `<button class="tog" role="switch" aria-checked="${on}" aria-label="${on ? 'Switch off' : 'Switch on'} ${esc(nice(name))}" data-switch="${esc(id)}" data-name="${esc(nice(name))}"><span></span></button>`;
  const bars = d => `<span class="d7" aria-label="Last 7 days">${(d || []).map(x => {
    const n = x.ok + x.bad; const h = n ? Math.min(22, 6 + n * 3) : 3;
    return `<i class="${x.bad ? 'bad' : n ? 'ok' : ''}" style="height:${h}px" title="${n ? `${x.ok} went well, ${x.bad} did not` : 'No runs'}"></i>`; }).join('')}</span>`;
  const firstTile = r => (r.apps && r.apps[0]) ? appTile(r.apps[0]) : `<span class="ap k-core">${svg(r.trigger === 'schedule' ? IC.cal : r.trigger === 'webhook' ? IC.bolt : IC.hand)}</span>`;
  const LASTW = {done: ['ok', 'Done'], failed: ['bad', 'Failed'], incomplete: ['bad', 'Incomplete'], waiting_approval: ['warn', 'Waiting for you'],
    running: ['v', 'Running'], queued: ['v', 'Queued'], sleeping: ['v', 'Waiting'], stopped: ['', 'Stopped']};
  // tables become cards on a phone: every cell carries its own label (data-l), the CSS shows it there
  function routeRows(routes, empty) {
    if (!routes.length) return `<div class="empty">${empty || 'No routes yet. Describe one above, or start from a template.'}</div>`;
    return `<div class="tw"><table class="rt"><thead><tr><th>Route</th><th>Runs when</th><th>Last run</th><th class="nw">Last 7 days</th><th class="c-tog">On</th></tr></thead><tbody>${
      routes.map(r => { const lr = r.last_run ? (LASTW[r.last_run.status] || ['', r.last_run.status]) : null;
        return `<tr>
        <td class="c-name"><div class="rname">${firstTile(r)}<div><a class="rn" href="#/r/${enc(r.id)}">${esc(nice(r.name))}</a><div class="mut sm">${esc([r.folder, {manual: 'by hand', schedule: 'on a schedule', webhook: 'when data arrives'}[r.trigger]].filter(Boolean).join(' · '))}</div></div></div></td>
        <td data-l="Runs when">${esc(r.when)}</td>
        <td data-l="Last run" class="nw">${lr ? `<span class="lr ${lr[0]}">${esc(lr[1])}</span> <span class="mut sm">${esc(when(r.last_run.at))}</span>` : `<span class="mut">${esc(r.status.text)}</span>`}</td>
        <td data-l="Last 7 days">${bars(r.days7)}</td>
        <td class="c-tog">${tog(r.id, r.enabled, r.name)}</td></tr>`; }).join('')}</tbody></table></div>`;
  }
  function needsList(items) {
    if (!items.length) return `<div class="nocard mut">Nothing needs you right now.</div>`;
    return `<div class="needs">${items.map(n => `<div class="need ${n.kind === 'approval' ? 'warn' : 'bad'}">
      <div class="t"><b>${esc(n.kind === 'approval' ? (n.text || 'Waiting for your OK') : n.kind === 'stopped' ? 'Switched off after errors' : n.kind === 'incomplete' ? 'Incomplete run' : 'A run failed')}</b>
      <span class="mut sm">${esc(nice(n.route))}${n.kind === 'approval' ? '' : ' · ' + esc(human(n.text))}</span></div>
      <span class="acts">${n.kind === 'approval' ? `<button class="btn s" data-act="approve" data-run="${esc(n.run_id)}">Approve</button><button class="btn s soft" data-act="stop" data-run="${esc(n.run_id)}">Stop the run</button>`
        : n.kind === 'stopped' ? `<a class="btn s soft" href="#/r/${enc(n.route_id)}">Open</a><button class="btn s" data-switch="${esc(n.route_id)}" aria-checked="false" data-name="${esc(nice(n.route))}">Switch back on</button>`
        : `<a class="btn s soft" href="#/run/${enc(n.run_id)}">See why</a>`}</span></div>`).join('')}</div>`;
  }

  // ---------------------------------------------------------------- views
  function shell(editing) { document.body.classList.toggle('editing', !!editing); if (!editing) stopEditor(); }
  async function viewHome() {
    shell(false); setNav('home');
    const [sum, list, tp] = await Promise.all([api('GET', '/api/route/summary'), api('GET', '/api/route/routes'), api('GET', '/api/route/templates')]);
    SUM = sum;
    MAIN.innerHTML = `
      <section class="hero">
        <h1>What should run by itself?</h1>
        <form class="comp" id="askForm">
          <textarea id="askText" rows="2" placeholder="When a new order comes in, add it to my sheet and message me if it is a big one…" aria-label="Describe a route"></textarea>
          <div class="crow"><a class="sb" href="#/templates">${svg(IC.grid)}Start from a template</a><button class="sb" type="button" id="blank">${svg(IC.plus)}Blank canvas</button>
            <span class="sp"></span><button class="go" type="submit" aria-label="Build the route" id="askGo" disabled>${svg(IC.up)}</button></div>
        </form>
        <p class="mut sm center">Hoola draws the route on the canvas first. Nothing runs until you switch it on.</p>
      </section>
      <div class="kpis">
        <div class="card kpi"><span>Routes on</span><b>${fmtN(sum.routes_on)}</b><small>of ${fmtN(sum.routes_total)} routes</small></div>
        <div class="card kpi"><span>Runs this week</span><b>${fmtN(sum.runs_7d)}</b><small>${sum.failed_7d ? `<span class="badt">${fmtN(sum.failed_7d)} did not finish</span>` : 'none failed'}</small></div>
        <div class="card kpi"><span>Went well</span><b>${sum.success_30d === null || sum.success_30d === undefined ? '–' : sum.success_30d + '%'}</b><small>of runs in 30 days</small></div>
        <a class="card kpi${sum.needs_count ? ' hot' : ''}" href="#/needs"><span>Needs you</span><b>${fmtN(sum.needs_count)}</b><small>${sum.needs_count ? 'open the list' : 'all clear'}</small></a>
      </div>
      ${sum.needs_count ? `<section aria-label="Needs you"><div class="hd"><h2>Needs you</h2><span class="cnum">${fmtN(sum.needs_count)}</span></div>${needsList(sum.needs_you.slice(0, 4))}</section>` : ''}
      <section aria-label="Your routes"><div class="hd"><h2>Your routes</h2><span class="sp"></span>${list.routes.length > 8 ? '<a class="btn soft s" href="#/routes">All routes</a>' : ''}</div>
        <div class="card flat">${routeRows(list.routes.slice(0, 8))}</div></section>
      <section aria-label="Templates"><div class="hd"><h2>Start from a template</h2><span class="sp"></span><a class="btn soft s" href="#/templates">See all</a></div>
        <div class="tgal">${tp.templates.slice(0, 4).map(tplCard).join('')}</div></section>`;
    const ta = $('#askText'), go = $('#askGo');
    ta.addEventListener('input', () => { go.disabled = !ta.value.trim(); });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#askForm').requestSubmit(); } });
    $('#askForm').addEventListener('submit', async e => {
      e.preventDefault(); if (!ta.value.trim()) return; go.disabled = true;
      try { await newRoute(titleOf(ta.value), ta.value.trim()); } catch (err) { toast(err.message, true); go.disabled = false; }
    });
    $('#blank').addEventListener('click', () => newRoute('New route').catch(err => toast(err.message, true)));
    tplClicks(MAIN, tp.templates);
    needCount();
  }
  const tplCard = x => `<section class="card tc">
      <div class="apps">${x.apps.map(a => appTile({kind: 'app', slug: a, label: a})).join('')}</div>
      <h3>${esc(x.title)}</h3><span class="mut sm">${esc(x.ask.replace(/^Build a route: /, '').replace(/^./, ch => ch.toUpperCase()))}</span>
      <div class="tf"><span class="mut sm">${esc(x.category)}</span><span class="sp"></span><button class="btn s" data-use="${esc(x.id)}">Use this</button></div></section>`;
  function tplClicks(root, list) {
    root.addEventListener('click', e => { const b = e.target.closest('[data-use]'); if (!b) return;
      const x = list.find(y => y.id === b.dataset.use); b.disabled = true;
      newRoute(x.title, x.ask).catch(err => { toast(err.message, true); b.disabled = false; }); });
  }

  async function viewRoutes(folderPick) {
    shell(false); setNav('routes');
    const list = await api('GET', '/api/route/routes');
    const folders = [...new Set(list.routes.map(r => r.folder).filter(Boolean))];
    MAIN.innerHTML = `<div class="top"><h1>All routes</h1><span class="sp"></span><button class="btn" id="newR">${svg(IC.plus)}New route</button></div>
      <div class="filt"><label class="srch">${svg(IC.search)}<input type="search" id="rq" placeholder="Find a route" aria-label="Find a route"></label>
      <select id="rsort" aria-label="Sort"><option value="changed">Last changed</option><option value="name">Name</option><option value="runs">Most runs</option></select>
      ${folders.length ? `<div class="chips left" id="fchips"><button class="chip" aria-pressed="${!folderPick}" data-f="">All</button>${folders.map(f => `<button class="chip" aria-pressed="${f === folderPick}" data-f="${esc(f)}">${esc(f)}</button>`).join('')}</div>` : ''}</div>
      <section class="card flat" id="rtable"></section>`;
    let folder = folderPick || '';
    const draw = () => { const q = $('#rq').value.trim().toLowerCase(), so = $('#rsort').value;
      const rs = list.routes.filter(r => (!folder || r.folder === folder) && (!q || (nice(r.name) + ' ' + r.description).toLowerCase().includes(q)));
      if (so === 'name') rs.sort((a, b) => a.name.localeCompare(b.name)); else if (so === 'runs') rs.sort((a, b) => b.runs_30d - a.runs_30d);
      $('#rtable').innerHTML = routeRows(rs, list.routes.length ? 'No route matches.' : ''); };
    draw();
    $('#rq').addEventListener('input', draw); $('#rsort').addEventListener('change', draw);
    const fc = $('#fchips');
    if (fc) fc.addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (!b) return;
      fc.querySelectorAll('[data-f]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); folder = b.dataset.f; draw(); });
    $('#newR').addEventListener('click', () => newRoute('New route', '', folder).catch(err => toast(err.message, true)));
  }
  async function viewNeeds() {
    shell(false); setNav('needs');
    const sum = await api('GET', '/api/route/summary');
    MAIN.innerHTML = `<div class="top"><h1>Needs you</h1></div><p class="lead">Approvals your routes are waiting for, and runs that did not finish. Nothing big runs without your yes.</p>${needsList(sum.needs_you)}`;
  }

  function runRows(runs, inRoute, empty) {
    if (!runs.length) return `<div class="empty">${empty || 'No runs yet.'}</div>`;
    const note = x => x.pause_reason === 'retry' && x.next_wake_at ? 'Trying again at ' + at(x.next_wake_at) : human(x.error || '');
    return `<div class="tw"><table class="rt runs"><thead><tr><th>Status</th>${inRoute ? '<th>Run</th>' : '<th>Route</th>'}<th>Steps done</th><th>Started</th><th>Note</th></tr></thead><tbody>${
      runs.map(x => `<tr><td class="c-on">${runPill(x.status)}</td>
        <td class="c-name"><a class="rn" href="#/run/${enc(x.id)}">${inRoute ? 'Open this run' : esc(nice(x.route))}</a></td>
        <td data-l="Steps done" class="num">${fmtN(x.steps_done)}</td><td data-l="Started" class="nw">${esc(when(x.at))}</td>
        <td data-l="Note" class="mut sm${note(x) ? '' : ' blank'}">${esc(note(x))}</td></tr>`).join('')}</tbody></table></div>`;
  }
  async function viewRuns(filter) {
    shell(false); setNav('runs');
    const q = filter ? `&status=${enc(filter)}` : '';
    const runs = await api('GET', `/api/route/runs?limit=60${q}`);
    const F = [['', 'All'], ['waiting_approval', 'Waiting for you'], ['incomplete', 'Incomplete'], ['failed', 'Failed'], ['done', 'Done']];
    MAIN.innerHTML = `<div class="top"><h1>Runs</h1></div>
      <div class="chips left">${F.map(([k, n]) => `<a class="chip" aria-pressed="${(filter || '') === k}" href="#/runs${k ? '/' + k : ''}">${esc(n)}</a>`).join('')}</div>
      <section class="card flat">${runRows(runs.runs, false, filter ? 'No runs in this list.' : 'No runs yet. A route runs when its time comes, when data arrives, or when you test it.')}</section>`;
  }
  const pretty = v => { try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return S(v); } };
  async function viewRun(id) {
    shell(false); setNav('runs');
    const x = await api('GET', `/api/route/runs/${enc(id)}`);
    const acts = [];
    if (x.status === 'waiting_approval') acts.push('<button class="btn" data-act="approve" data-run="' + esc(x.id) + '">Approve</button>');
    if (['queued', 'running', 'sleeping', 'waiting_approval'].includes(x.status)) acts.push('<button class="btn soft bad" data-act="stop" data-run="' + esc(x.id) + '">Stop the run</button>');
    if (['failed', 'stopped', 'incomplete'].includes(x.status)) acts.push('<button class="btn" data-act="retry" data-run="' + esc(x.id) + '">Retry from where it stopped</button>');
    acts.push(`<a class="btn soft" href="#/r/${enc(x.route_id)}">Open the route</a>`);
    const sm = x.summary || {};
    MAIN.innerHTML = `
      <div class="rhead"><a class="btn soft s ib" href="#/runs" aria-label="Back to runs">${svg(IC.back)}</a>
        <div class="rh-t"><h1 class="rtitle">${esc(nice(x.route))}</h1>
          <div class="rh-m">${runPill(x.status)}<span class="mut sm">Started ${esc(at(x.at))}</span></div></div>
        <div class="rh-a">${acts.join('')}</div></div>
      ${x.error ? `<div class="errbox"><b>What happened.</b> ${esc(human(x.error))}${x.pause_reason === 'retry' && x.next_wake_at ? `<br>Hoola will try again at ${esc(at(x.next_wake_at))}.` : ''}</div>` : ''}
      <section class="card"><div class="hd"><h2>Step by step</h2><span class="sp"></span>${sm.wall_ms ? `<span class="mut sm">${(sm.wall_ms / 1000).toFixed(1)} s${sm.cost && sm.cost.calls ? ` · ${sm.cost.calls} AI calls` : ''}</span>` : ''}</div>
        <div class="log">${(x.steps_log || []).map(l => {
          const st = {ok: 'done', error: 'failed', approved: 'done', retry: 'queued', skipped: 'stopped'}[l.status] || l.status;
          const word = {approved: 'You approved', retry: 'Tried again', skipped: 'Skipped'}[l.status];
          return `<div class="lrow"><span class="lp">${word ? `<span class="pill ${l.status === 'approved' ? 'ok' : 'v'}"><span class="dot"></span>${esc(word)}</span>` : runPill(st)}</span>
          <div class="w"><b>${esc(nice(l.id))}</b> <span class="mut sm">${esc(l.type)}${l.at ? ' · ' + esc(l.at) : ''}${l.ms ? ' · ' + l.ms + ' ms' : ''}</span>
          ${l.error ? `<div class="sm errt">${esc(human(l.error))}</div>` : ''}${(x.outputs && x.outputs[l.id] !== undefined) || l.output ? `<details><summary class="sm">What it gave back${(x.pinned || []).includes(l.id) ? ' (pinned test data)' : ''}</summary><pre>${esc(x.outputs && x.outputs[l.id] !== undefined ? JSON.stringify(x.outputs[l.id], null, 2) : pretty(l.output))}</pre></details>` : ''}</div></div>`; }).join('') || '<div class="empty">No step has run yet.</div>'}</div></section>`;
  }
  async function viewTemplates() {
    shell(false); setNav('templates');
    const t = await api('GET', '/api/route/templates');
    const cats = [...new Set(t.templates.map(x => x.category))];
    const draw = cat => t.templates.filter(x => !cat || x.category === cat).map(tplCard).join('');
    MAIN.innerHTML = `<div class="top"><div><h1>Templates</h1><p class="lead sm">Hoola fits each one to your own apps, time zone and currency, and draws it on the canvas before anything switches on.</p></div></div>
      <div class="chips left" id="tc"><button class="chip" aria-pressed="true" data-c="">All</button>${cats.map(c => `<button class="chip" aria-pressed="false" data-c="${esc(c)}">${esc(c)}</button>`).join('')}</div>
      <div class="tgal" id="tg">${draw('')}</div>`;
    $('#tc').addEventListener('click', e => { const b = e.target.closest('[data-c]'); if (!b) return;
      $('#tc').querySelectorAll('[data-c]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); $('#tg').innerHTML = draw(b.dataset.c); });
    tplClicks($('#tg'), t.templates);
  }

  // ================================================================ THE EDITOR
  const NW = 220, NH = 64, GX = 56, GY = 36, TW = 200;
  const OPW = {exists: 'exists', not_exists: 'does not exist', empty: 'is empty', not_empty: 'is not empty', eq: 'is', ne: 'is not', contains: 'contains',
    not_contains: 'does not contain', starts_with: 'starts with', ends_with: 'ends with', matches: 'matches the pattern', gt: 'is more than', gte: 'is at least',
    lt: 'is less than', lte: 'is at most', between: 'is between', before: 'is before', after: 'is after', is_true: 'is true', is_false: 'is false',
    in: 'is one of', not_in: 'is not one of', length_eq: 'has length', length_gt: 'is longer than', length_lt: 'is shorter than'};
  const NO_RIGHT = new Set(['exists', 'not_exists', 'empty', 'not_empty', 'is_true', 'is_false']);
  // v0.999.237 ROUTE R3: the data steps (engine type "data", told apart by op)
  const DATAW = {fields: 'Set several fields', sort: 'Sort', limit: 'Limit', dedupe: 'Remove duplicates', aggregate: 'Summarise',
    split: 'Split out a list', compare: 'Compare two lists', keep_fields: 'Keep or drop fields', rename: 'Rename fields',
    date: 'Date and time', text: 'Text and formats', file: 'Make or read a file', crypto: 'Hash and IDs'};
  const OPIC = {sort: '<path d="M7 4v16M4 17l3 3 3-3M14 6h6M14 12h4M14 18h2"/>', limit: '<path d="M4 6h16M4 12h10M4 18h4"/>',
    dedupe: '<rect x="4" y="4" width="10" height="10" rx="2"/><rect x="10" y="10" width="10" height="10" rx="2"/>',
    aggregate: '<path d="M18 5H6l6 7-6 7h12"/>', split: '<path d="M12 4v6M12 10l-6 10M12 10l6 10"/>',
    compare: '<path d="M8 4v16M16 4v16M4 8h4M16 16h4"/>', keep_fields: '<path d="M4 6h16M4 12h16M4 18h9"/><path d="m15 17 2 2 4-4"/>',
    rename: '<path d="M4 20h4L19 9l-4-4L4 16z"/>', fields: '<path d="M4 7h16M4 12h10M4 17h7"/>',
    date: '<path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2z"/>', text: '<path d="M4 7V5h16v2M12 5v14M9 19h6"/>',
    file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>', crypto: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'};
  const KIND = {data: 'Data', tool: 'Uses a tool', http: 'Web request', code: 'Code', wait: 'Wait', notify: 'Tell me', approval: 'Ask me first',
    set: 'Set a value', filter: 'Filter', condition: 'If / else', loop: 'Repeat for each', router: 'Switch'};
  const DO = {'': 'Stop the run and show me why', break: 'Try again later, then keep it in Incomplete runs', resume: 'Use a value I give and carry on',
    ignore: 'Skip it and carry on', commit: 'Stop here and keep what was done', rollback: 'Stop the run', tell: 'Tell me and stop the run'};
  function fltWords(f) {
    if (!f) return 'Always';
    if (f.all) return f.all.map(fltWords).join(' and ');
    if (f.any) return '(' + f.any.map(fltWords).join(' or ') + ')';
    const r = Array.isArray(f.right) ? f.right.join(' – ') : S(f.right);
    return `${S(f.left).replace(/\{\{\s*|\s*\}\}/g, '') || '…'} ${OPW[f.op] || f.op}${r && !NO_RIGHT.has(f.op) ? ' ' + r : ''}`;
  }
  function stepWords(s) {
    const t = s.type;
    if (t === 'tool') return s.app && s.app.kind === 'app' ? appName(s.app.slug) : nice(s.name);
    if (t === 'http') return `${S(s.method || 'GET')} ${S(s.url).replace(/^https?:\/\//, '').slice(0, 28)}`;
    if (t === 'wait') return s.duration_s ? `${s.duration_s} seconds` : `until ${S(s.until)}`;
    if (t === 'notify') return S(s.text).slice(0, 40);
    if (t === 'approval') return S(s.question).slice(0, 40);
    if (t === 'set') return S(s.name);
    if (t === 'filter' || t === 'condition') return s.filter ? fltWords(s.filter).slice(0, 40) : `${S(s.left)} ${OPW[s.op] || s.op || ''} ${S(s.right)}`.slice(0, 40);
    if (t === 'loop') return S(s.items).replace(/\{\{\s*|\s*\}\}/g, '').slice(0, 34);
    if (t === 'router') return `${(s.routes || []).length} ways`;
    if (t === 'code') return 'Python';
    if (t === 'data') return DATAW[s.op] || S(s.op);
    return '';
  }
  const titleOfStep = s => S(s.label) || (s.type === 'tool' ? nice(s.name) : s.type === 'data' ? (DATAW[s.op] || 'Data') : KIND[s.type] || s.type);

  let ED = null;
  function stopEditor() {
    if (!ED) return;
    clearTimeout(ED.layT); clearInterval(ED.runT); clearTimeout(ED.chatT); ED.dead = true;
    if (ED.ro) ED.ro.disconnect();
    window.removeEventListener('keydown', edKeys); window.removeEventListener('beforeunload', edLeave);
    ED = null;
  }
  function edLeave(e) { if (ED && ED.dirty) { e.preventDefault(); e.returnValue = ''; } }
  const snap = () => JSON.stringify({steps: ED.steps, trig: ED.trig});
  function norm(list) {
    (list || []).forEach(s => {
      if (s.type === 'condition') { s.then = Array.isArray(s.then) ? s.then : []; s.else = Array.isArray(s.else) ? s.else : []; norm(s.then); norm(s.else); }
      if (s.type === 'loop') { s.body = Array.isArray(s.body) ? s.body : []; norm(s.body); }
      if (s.type === 'router') { (s.routes || []).forEach(r => { r.steps = Array.isArray(r.steps) ? r.steps : []; norm(r.steps); }); if (s.fallback) norm(s.fallback); }
    });
    return list;
  }
  function load(r) {
    ED.r = r; ED.base = r.version;
    ED.steps = norm(clone(r.graph || []));
    ED.trig = {kind: r.trigger, spec: clone(r.trigger_spec || {})};
    ED.pos = clone((r.layout && r.layout.pos) || {}); ED.notes = clone((r.layout && r.layout.notes) || []);
    ED.saved = snap(); ED.dirty = false;
  }

  // every list of steps by its place: [] = the route, [id,'then'] / [id,'else'] / [id,'body'] / [id,'fallback'] / [id,'routes',i]
  function find(id, list, path) {
    list = list || ED.steps; path = path || [];
    for (let i = 0; i < list.length; i++) {
      const s = list[i];
      if (s.id === id) return {step: s, list, i, path};
      const subs = [];
      for (const k of ['then', 'else', 'body', 'fallback']) if (Array.isArray(s[k])) subs.push([s[k], [s.id, k]]);
      (s.routes || []).forEach((rt, j) => subs.push([rt.steps || [], [s.id, 'routes', j]]));
      for (const [l, p] of subs) { const hit = find(id, l, p); if (hit) return hit; }
    }
    return null;
  }
  function listAt(path) {
    if (!path || !path.length) return ED.steps;
    const h = find(path[0]); if (!h) return null;
    if (path[1] === 'routes') { const rt = (h.step.routes || [])[path[2]]; if (!rt) return null; rt.steps = rt.steps || []; return rt.steps; }
    h.step[path[1]] = h.step[path[1]] || []; return h.step[path[1]];
  }
  const allSteps = (list, out) => { out = out || []; (list || ED.steps).forEach(s => { out.push(s);
    ['then', 'else', 'body', 'fallback'].forEach(k => s[k] && allSteps(s[k], out)); (s.routes || []).forEach(r => allSteps(r.steps, out)); }); return out; };
  const idsUsed = () => new Set(allSteps().map(s => s.id));
  function freshId(base) {
    let b = S(base).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'step';
    if (!/^[a-z_]/.test(b)) b = 's_' + b;
    const used = idsUsed(); let id = b, n = 2;
    while (used.has(id)) id = `${b}_${n++}`;
    return id;
  }

  // ---------------------------------------------------------------- history (undo / redo) and dirty state
  function before() { ED.hist.push(JSON.stringify({steps: ED.steps, trig: ED.trig, pos: ED.pos, notes: ED.notes})); if (ED.hist.length > 80) ED.hist.shift(); ED.fut = []; }
  function restore(js) { const o = JSON.parse(js); ED.steps = o.steps; ED.trig = o.trig; ED.pos = o.pos; ED.notes = o.notes; }
  function undo() { if (!ED.hist.length) return; ED.fut.push(JSON.stringify({steps: ED.steps, trig: ED.trig, pos: ED.pos, notes: ED.notes})); restore(ED.hist.pop()); changed(true); }
  function redo() { if (!ED.fut.length) return; ED.hist.push(JSON.stringify({steps: ED.steps, trig: ED.trig, pos: ED.pos, notes: ED.notes})); restore(ED.fut.pop()); changed(true); }
  function changed(layoutToo) {
    ED.dirty = snap() !== ED.saved;
    if (ED.sel && ED.sel !== 'trigger' && !find(ED.sel)) ED.sel = null;
    draw(); topState();
    if (layoutToo) saveLayoutSoon();
    if (ED.tab === 'step') panel();
    if (ED.modal) modalDraw(true);
  }
  function topState() {
    const st = $('#edState'); if (!st) return;
    st.textContent = ED.saving ? 'Saving…' : ED.dirty ? 'Not saved' : 'Saved';
    st.className = 'chipst' + (ED.dirty ? ' warn' : '');
    $('#edSave').disabled = !ED.dirty || ED.saving;
    $('#edUndo').disabled = !ED.hist.length; $('#edRedo').disabled = !ED.fut.length;
  }
  function saveLayoutSoon() {
    clearTimeout(ED.layT);
    ED.layT = setTimeout(async () => {
      if (!ED) return;
      const ids = idsUsed(); ids.add('trigger');
      const pos = {}; Object.entries(ED.pos).forEach(([k, v]) => { if (ids.has(k)) pos[k] = v; });
      try { await api('PUT', `/api/route/routes/${enc(ED.r.id)}/layout`, {pos, notes: ED.notes}); } catch (e) { toast(e.message, true); }
    }, 600);
  }
  async function save() {
    if (!ED || !ED.dirty || ED.saving) return true;
    ED.saving = true; topState();
    try {
      const r = await api('PUT', `/api/route/routes/${enc(ED.r.id)}/graph`, {steps: ED.steps, trigger: ED.trig.kind, trigger_spec: ED.trig.spec, base: ED.base});
      const keepPos = ED.pos, keepNotes = ED.notes;
      load(r); ED.pos = keepPos; ED.notes = keepNotes; ED.saving = false;
      changed(false); toast('Saved.'); return true;
    } catch (e) {
      ED.saving = false; topState();
      if (e.status === 409) banner(e.message, true); else toast(e.message, true);
      return false;
    }
  }
  function banner(msg, reload) {
    const b = $('#edBanner'); if (!b) return;
    b.innerHTML = `<span>${esc(msg)}</span>${reload ? '<button class="btn s" id="edReload" type="button">Reload</button>' : ''}<button class="btn s soft ib" id="edBanX" type="button" aria-label="Close">${svg(IC.x)}</button>`;
    b.hidden = false;
    const rl = $('#edReload'); if (rl) rl.addEventListener('click', () => { ED.dirty = false; route(); });
    $('#edBanX').addEventListener('click', () => { b.hidden = true; });
  }

  // ---------------------------------------------------------------- layout: where every node sits
  function layout() {
    const nodes = [], edges = [], adds = [];
    const P = (id, x, y) => ED.pos[id] ? {x: ED.pos[id][0], y: ED.pos[id][1]} : {x, y};
    const trig = P('trigger', 0, 0);
    nodes.push({id: 'trigger', kind: 'trigger', x: trig.x, y: trig.y, w: TW});
    function lane(list, x, y, path, prev, label) {
      let ends = prev, maxY = y + NH, cx = x, first = true;
      if (!list.length) {
        adds.push({path, i: 0, x, y: y + 8, from: prev, label});
        prev.forEach(p => edges.push({from: p, toAdd: adds.length - 1, label}));
        return {x: x + 40 + GX, y: y + NH, ends: [], empty: true};
      }
      list.forEach((s, i) => {
        const p = P(s.id, cx, y);
        nodes.push({id: s.id, kind: 'step', step: s, x: p.x, y: p.y, w: NW, path, i});
        ends.forEach(e => edges.push({from: e, to: s.id, label: first ? label : ''}));
        first = false;
        let nx = cx + NW + GX, branches = null;
        if (s.type === 'condition') branches = [['If yes', [s.id, 'then'], s.then], ['If no', [s.id, 'else'], s.else]];
        else if (s.type === 'router') { branches = (s.routes || []).map((rt, j) => [rt.label || ('Way ' + (j + 1)), [s.id, 'routes', j], rt.steps || []]);
          if (Array.isArray(s.fallback)) branches.push(['Anything else', [s.id, 'fallback'], s.fallback]); }
        else if (s.type === 'loop') branches = [['For each item', [s.id, 'body'], s.body]];
        if (branches) {
          let by = y, mx = nx, bends = [];
          branches.forEach(([lab, bp, bl]) => {
            const r = lane(bl, nx, by, bp, [s.id], lab);
            mx = Math.max(mx, r.x); by = Math.max(r.y, by + NH) + GY;
            bends = bends.concat(r.empty ? [s.id] : r.ends);
          });
          if (s.type === 'router' && !Array.isArray(s.fallback)) bends.push(s.id);   // no way matched: it goes straight on
          maxY = Math.max(maxY, by - GY);
          cx = mx; ends = [...new Set(bends.length ? bends : [s.id])];
        } else { cx = nx; ends = [s.id]; }
      });
      adds.push({path, i: list.length, x: cx, y: y + 8, from: ends, end: true});
      ends.forEach(e => edges.push({from: e, toAdd: adds.length - 1}));
      return {x: cx + 40, y: maxY, ends};
    }
    lane(ED.steps, TW + GX, 0, [], ['trigger'], '');
    return {nodes, edges, adds};
  }

  function trigWords() {
    const t = ED.trig, sp = t.spec || {};
    if (t.kind === 'webhook') return ['When data arrives', 'A secret web address starts it'];
    if (t.kind === 'manual') return ['By hand', 'When you run or test it'];
    const at = (sp.at || []).join(', ');
    let w = sp.every_minutes ? `Every ${sp.every_minutes} minutes` : sp.every_hours ? `Every ${sp.every_hours} hours`
      : sp.days && sp.days.length ? sp.days.map(d => S(d).slice(0, 3).replace(/^./, c => c.toUpperCase())).join(' ') + (at ? ', ' + at : '')
      : sp.monthdays && sp.monthdays.length ? `Day ${sp.monthdays.join(', ')}${at ? ', ' + at : ''}` : sp.once ? `Once, ${S(sp.once).replace('T', ' ')}` : at ? `Every day, ${at}` : 'On a schedule';
    return ['On a schedule', w + (sp.skip_holidays ? ' · not on holidays' : '')];
  }
  const ST_CLS = {ok: 'ok', approved: 'ok', error: 'bad', skipped: 'skip', retry: 'run'};
  function nodeHtml(n) {
    const sel = ED.sel === n.id ? ' sel' : '';
    if (n.kind === 'trigger') {
      const [a, b] = trigWords();
      const ic = ED.trig.kind === 'schedule' ? IC.cal : ED.trig.kind === 'webhook' ? IC.bolt : IC.hand;
      return `<div class="nd trig${sel}" data-node="trigger" style="left:${n.x}px;top:${n.y}px;width:${n.w}px" tabindex="0" role="button" aria-label="Starts: ${esc(a)}">
        <span class="ap k-trig">${svg(ic)}</span><span class="nt"><b>${esc(a)}</b><small>${esc(b)}</small></span></div>`;
    }
    const s = n.step, st = ED.runSt[s.id];
    return `<div class="nd${sel}${s.type === 'approval' ? ' warmk' : ''}" data-node="${esc(s.id)}" style="left:${n.x}px;top:${n.y}px;width:${n.w}px" tabindex="0" role="button" aria-label="${esc(titleOfStep(s))}">
      ${appTile(s.app, s.type, s.op)}<span class="nt"><b>${esc(titleOfStep(s))}</b><small>${esc(KIND[s.type] || s.type)}${stepWords(s) ? ' · ' + esc(stepWords(s)) : ''}</small></span>
      ${s.on_error ? `<span class="oe" title="${esc(DO[s.on_error.do] || '')}">${esc(s.on_error.do === 'break' ? 'retries' : s.on_error.do)}</span>` : ''}
      ${st ? `<span class="sd ${ST_CLS[st.status] || ''}" title="${esc(st.status)}"></span>` : ''}
      ${ED.data && ED.data.pins && ED.data.pins[s.id] !== undefined ? `<span class="pinb" title="Pinned test data">${svg(IC.pin)}</span>` : ''}
      <button class="addaf" type="button" data-addafter="${esc(s.id)}" aria-label="Add a step after this" title="Add a step after this">${svg(IC.plus)}</button></div>`;
  }
  function edgePath(a, b) {
    const dx = Math.max(30, (b.x - a.x) / 2);
    return `M${a.x} ${a.y} C ${a.x + dx} ${a.y}, ${b.x - dx} ${b.y}, ${b.x} ${b.y}`;
  }
  function draw() {
    const L = ED.L = layout();
    const byId = {}; L.nodes.forEach(n => { byId[n.id] = n; });
    const out = n => ({x: n.x + n.w, y: n.y + NH / 2}), inn = n => ({x: n.x, y: n.y + NH / 2});
    const paths = [], labels = [];
    L.edges.forEach(e => {
      const a = byId[e.from]; if (!a) return;
      const b = e.to ? inn(byId[e.to] || {x: 0, y: 0}) : {x: L.adds[e.toAdd].x, y: L.adds[e.toAdd].y + 16};
      if (e.to && !byId[e.to]) return;
      const A = out(a), bad = e.to && ED.runSt[e.to] && ED.runSt[e.to].status === 'error', ok = e.to && ED.runSt[e.to] && ['ok', 'approved'].includes(ED.runSt[e.to].status);
      paths.push(`<path d="${edgePath(A, b)}" class="${e.to ? (bad ? 'bad' : ok ? 'ok' : '') : 'ghost'}"/>`);
      if (e.label) labels.push(`<span class="elab" style="left:${A.x + 14}px;top:${(A.y + b.y) / 2 - 10 + (b.y > A.y ? 8 : b.y < A.y ? -8 : -16)}px">${esc(e.label)}</span>`);
    });
    const addH = L.adds.map((d, k) => `<button class="addn${d.end ? ' end' : ''}" type="button" data-add="${k}" style="left:${d.x}px;top:${d.y}px" aria-label="Add a step here" title="Add a step here">${svg(IC.plus)}${d.end ? '' : '<span>Add a step</span>'}</button>`).join('');
    const notes = ED.notes.map(n => `<div class="sticky c-${esc(n.color)}" data-note="${esc(n.id)}" style="left:${n.x}px;top:${n.y}px;width:${n.w}px">
      <div class="sh"><span>Note</span><span class="sp"></span>${['yellow', 'blue', 'green', 'pink', 'grey'].map(c => `<button type="button" class="nc c-${c}" data-ncolor="${c}" aria-label="${c}"></button>`).join('')}
      <button type="button" class="nx" data-ndel="${esc(n.id)}" aria-label="Delete the note">${svg(IC.x)}</button></div>
      <textarea data-ntext="${esc(n.id)}" aria-label="Note" rows="3" placeholder="Write a note for whoever reads this route">${esc(n.text)}</textarea></div>`).join('');
    const fa = document.activeElement, keep = fa && fa.dataset && fa.dataset.ntext ? [fa.dataset.ntext, fa.selectionStart, fa.selectionEnd] : null;
    $('#world').innerHTML = `<svg class="edges" aria-hidden="true">${paths.join('')}</svg>${labels.join('')}${notes}${L.nodes.map(nodeHtml).join('')}${addH}`;
    if (keep) { const t = document.querySelector(`[data-ntext="${CSS.escape(keep[0])}"]`); if (t) { t.focus({preventScroll: true}); try { t.setSelectionRange(keep[1], keep[2]); } catch {} } }
    view(); mini();
  }
  function view() {
    const w = $('#world'); if (!ED || !w) return;
    w.style.transform = `translate(${ED.px}px, ${ED.py}px) scale(${ED.z})`;
    const zl = $('#zl'); if (zl) zl.textContent = Math.round(ED.z * 100) + '%';
    mini();
  }
  function bounds() {
    const L = ED.L; let x0 = 0, y0 = 0, x1 = 400, y1 = 200;
    L.nodes.forEach(n => { x0 = Math.min(x0, n.x); y0 = Math.min(y0, n.y); x1 = Math.max(x1, n.x + n.w); y1 = Math.max(y1, n.y + NH); });
    L.adds.forEach(a => { x1 = Math.max(x1, a.x + 140); y1 = Math.max(y1, a.y + 40); });
    ED.notes.forEach(n => { x0 = Math.min(x0, n.x); y0 = Math.min(y0, n.y); x1 = Math.max(x1, n.x + n.w); y1 = Math.max(y1, n.y + 120); });
    return {x0, y0, x1, y1};
  }
  function fit() {
    const c = $('#canvas'); if (!c) return;
    // the whole route when it fits at a readable size; otherwise readable, from its start, and the mini-map shows the rest
    const b = bounds(), W = c.clientWidth, H = c.clientHeight - (ED.logOpen ? 150 : 0), small = W < 700;
    const want = Math.min(1, (W - 120) / (b.x1 - b.x0), (H - 80) / (b.y1 - b.y0));
    ED.z = Math.max(small ? 0.62 : 0.8, want);
    const left = small ? 68 : 76;
    ED.px = want >= ED.z ? (W - (b.x1 - b.x0) * ED.z) / 2 - b.x0 * ED.z : left - b.x0 * ED.z;
    ED.py = Math.max(small ? 24 : 40, (H - (b.y1 - b.y0) * ED.z) / 2) - b.y0 * ED.z;
    view();
  }
  function zoomAt(f, cx, cy) {
    const nz = Math.max(0.3, Math.min(2, ED.z * f));
    ED.px = cx - (cx - ED.px) * nz / ED.z; ED.py = cy - (cy - ED.py) * nz / ED.z; ED.z = nz; view();
  }
  function mini() {
    const m = $('#mini'), c = $('#canvas'); if (!ED || !m || !c || !ED.L) return;
    const g = bounds(), W = 168, H = 100, pad = 8;
    const vx = -ED.px / ED.z, vy = -ED.py / ED.z, vw = c.clientWidth / ED.z, vh = c.clientHeight / ED.z;
    const b = {x0: Math.min(g.x0, vx), y0: Math.min(g.y0, vy), x1: Math.max(g.x1, vx + vw), y1: Math.max(g.y1, vy + vh)};
    const k = Math.min((W - 2 * pad) / (b.x1 - b.x0 || 1), (H - 2 * pad) / (b.y1 - b.y0 || 1));
    const X = x => pad + (x - b.x0) * k, Y = y => pad + (y - b.y0) * k;
    m.innerHTML = `<svg width="${W}" height="${H}" aria-hidden="true">${ED.L.nodes.map(n => `<rect x="${X(n.x)}" y="${Y(n.y)}" width="${Math.max(3, n.w * k)}" height="${Math.max(3, NH * k)}" rx="2" class="${ED.sel === n.id ? 'sel' : ''}"/>`).join('')}
      <rect class="vp" x="${X(vx)}" y="${Y(vy)}" width="${vw * k}" height="${vh * k}" rx="3"/></svg>`;
    ED.miniK = {k, b, pad};
  }

  // ---------------------------------------------------------------- editing the steps
  function addAt(path, i) { ED.addAt = {path, i}; ED.tab = 'add'; panel(); }
  function insertStep(step) {
    const lst = listAt(ED.addAt.path); if (!lst) return;
    before();
    lst.splice(Math.min(ED.addAt.i, lst.length), 0, step);
    ED.sel = step.id; ED.tab = 'step'; ED.addAt = null;
    changed(false);
  }
  function makeKind(k) {
    const st = Object.assign({id: freshId(k.title), type: k.type, label: k.title}, clone(k.make || {}));
    if (st.type === 'router') st.routes.forEach(r => { r.steps = r.steps || []; });
    return st;
  }
  function makeTool(t) { return {id: freshId(t.name), type: 'tool', name: t.name, label: t.label, args: {}, app: t.app}; }
  function delStep(id) {
    const h = find(id); if (!h) return;
    before(); h.list.splice(h.i, 1);
    delete ED.pos[id]; if (ED.sel === id) ED.sel = null;
    changed(true);
  }
  function dupStep(id) {
    const h = find(id); if (!h) return;
    before();
    const c = clone(h.step);
    const re = s => { s.id = freshId(s.id); ['then', 'else', 'body', 'fallback'].forEach(k => (s[k] || []).forEach(re)); (s.routes || []).forEach(r => (r.steps || []).forEach(re)); };
    re(c); if (c.label) c.label = c.label + ' (copy)';
    h.list.splice(h.i + 1, 0, c); ED.sel = c.id; changed(false);
  }
  function renameStep(oldId, newId) {
    const used = idsUsed();
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(newId)) { toast('A step name uses letters, numbers and _ only, and starts with a letter.', true); return false; }
    if (used.has(newId)) { toast('Another step already has that name.', true); return false; }
    before();
    const rx = new RegExp(`(steps\\.)${oldId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=[.\\]\\s}])`, 'g');
    const walk = v => typeof v === 'string' ? v.replace(rx, '$1' + newId) : Array.isArray(v) ? v.map(walk) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, walk(x)])) : v;
    ED.steps = walk(ED.steps);
    const h = find(oldId); if (h) h.step.id = newId;
    if (ED.pos[oldId]) { ED.pos[newId] = ED.pos[oldId]; delete ED.pos[oldId]; }
    ED.sel = newId; changed(true); return true;
  }

  // ---------------------------------------------------------------- the right panel: Ask Hoola · Step · Add a step
  function panel() {
    const box = $('#edPanel'); if (!box || !ED) return;
    document.querySelectorAll('.ptab').forEach(b => b.setAttribute('aria-selected', String(b.dataset.ptab === (ED.tab === 'add' ? 'step' : ED.tab))));
    if (ED.tab === 'ask') { askPanel(box); return; }
    if (ED.tab === 'add') { addPanel(box); return; }
    if (ED.modal) { box.innerHTML = '<div class="pempty"><div class="pe-t">Open in the large view</div><p class="mut sm">Close it to set the step here.</p></div>'; return; }
    stepPanel(box);
  }
  // the values earlier steps leave behind, to put into a box
  function refsFor(id) {
    const out = [];
    const flat = allSteps();
    const idx = id ? flat.findIndex(s => s.id === id) : flat.length;
    const h = id ? find(id) : null;
    if (h && h.path[1] === 'body') out.push(['The item in this round', '{{item}}']);
    if (ED.trig.kind === 'webhook') out.push(['The data that arrived', '{{vars}}']);
    flat.slice(0, idx < 0 ? flat.length : idx).forEach(s => {
      if (s.type === 'set') out.push([`${titleOfStep(s)} (value)`, `{{vars.${s.name}}}`]);
      else if (!['condition', 'router', 'filter', 'wait', 'approval'].includes(s.type)) out.push([`What ${titleOfStep(s)} gave back`, `{{steps.${s.id}.output}}`]);
    });
    return out;
  }
  function refMenu(btn) {
    const old = $('#refm'); if (old) old.remove();
    const target = document.getElementById(btn.dataset.ref); if (!target) return;
    const refs = refsFor(ED.sel === 'trigger' ? '' : ED.sel);
    const m = document.createElement('div'); m.id = 'refm'; m.className = 'refm'; m.setAttribute('role', 'menu');
    m.innerHTML = refs.length ? refs.map(([t, v], i) => `<button type="button" role="menuitem" data-ri="${i}"><b>${esc(t)}</b><code>${esc(v)}</code></button>`).join('')
      : '<div class="mut sm">No earlier step leaves a value yet.</div>';
    btn.parentNode.appendChild(m);
    m.addEventListener('click', e => { const b = e.target.closest('[data-ri]'); if (!b) return;
      const v = refs[+b.dataset.ri][1], s0 = target.selectionStart ?? target.value.length, s1 = target.selectionEnd ?? s0;
      target.value = target.value.slice(0, s0) + v + target.value.slice(s1); target.dispatchEvent(new Event('input', {bubbles: true}));
      target.dispatchEvent(new Event('change', {bubbles: true})); target.focus(); m.remove(); });
    setTimeout(() => document.addEventListener('click', function off(e) { if (!m.contains(e.target) && e.target !== btn) { m.remove(); document.removeEventListener('click', off); } }), 0);
  }
  let FID = 0;
  const fid = () => 'f' + (++FID);
  function field(label, value, opts) {
    opts = opts || {};
    const id = fid();
    const help = opts.help ? `<span class="fh">${esc(opts.help)}</span>` : '';
    const ref = opts.ref === false ? '' : `<button class="refb" type="button" data-ref="${id}" title="Use a value from an earlier step" aria-label="Use a value from an earlier step">{ }</button>`;
    let ctl;
    if (opts.options) ctl = `<select id="${id}" data-k="${esc(opts.k)}">${opts.options.map(([v, t]) => `<option value="${esc(v)}"${S(value) === S(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>`;
    else if (opts.area) ctl = `<textarea id="${id}" data-k="${esc(opts.k)}" rows="${opts.rows || 3}"${opts.mono ? ' class="mono"' : ''} placeholder="${esc(opts.ph || '')}" spellcheck="${opts.mono ? 'false' : 'true'}">${esc(value)}</textarea>`;
    else ctl = `<input id="${id}" data-k="${esc(opts.k)}" value="${esc(value)}" placeholder="${esc(opts.ph || '')}"${opts.mono ? ' class="mono"' : ''}${opts.num ? ' inputmode="decimal"' : ''}>`;
    return `<div class="fld"><label for="${id}">${esc(label)}${opts.req ? ' <span class="req">needed</span>' : ''}</label><div class="fc">${ctl}${opts.options ? '' : ref}</div>${help}${opts.ref === false || opts.options ? '' : `<div class="fprev" data-prev="${id}" hidden></div>`}</div>`;
  }
  const TOOLS = {};
  async function toolInfo(name) {
    if (TOOLS[name] !== undefined) return TOOLS[name];
    try { TOOLS[name] = await api('GET', `/api/route/catalog/tool/${enc(name)}`); } catch { TOOLS[name] = null; }
    return TOOLS[name];
  }
  function filterRows(f, prefix) {
    // one group of conditions (all / any); anything deeper is edited as text
    const g = f && (f.all || f.any) ? f : f && f.op ? {all: [f]} : {all: [{left: '', op: 'exists'}]};
    const items = g.all || g.any;
    const deep = items.some(x => x.all || x.any);
    if (deep) return `<div class="fld"><label>Test (written as data)</label><textarea class="mono" rows="5" data-fjson="${prefix}">${esc(JSON.stringify(f, null, 2))}</textarea></div>`;
    const ops = Object.entries(OPW);
    return `<div class="fgroup" data-fg="${prefix}">
      <div class="seg sm" role="radiogroup" aria-label="How the tests join"><button type="button" data-fmode="all" aria-pressed="${!!g.all}">All of these</button><button type="button" data-fmode="any" aria-pressed="${!!g.any}">Any of these</button></div>
      ${items.map((c, j) => { const lid = fid(), rid = fid(); return `<div class="frow" data-fi="${j}">
        <div class="fc"><input id="${lid}" data-fl="${j}" value="${esc(c.left)}" placeholder="A value, like {{steps.order.output.total}}" aria-label="Value to test">
        <button class="refb" type="button" data-ref="${lid}" aria-label="Use a value from an earlier step">{ }</button></div>
        <select data-fo="${j}" aria-label="Test">${ops.map(([k, t]) => `<option value="${k}"${c.op === k ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select>
        <div class="fc"${NO_RIGHT.has(c.op) ? ' hidden' : ''}><input id="${rid}" data-fr="${j}" value="${esc(Array.isArray(c.right) ? c.right.join(', ') : c.right)}" placeholder="${c.op === 'between' ? 'low, high' : ['in', 'not_in'].includes(c.op) ? 'a, b, c' : 'Compared with'}" aria-label="Compared with">
        <button class="refb" type="button" data-ref="${rid}" aria-label="Use a value from an earlier step">{ }</button></div>
        <button class="btn s soft ib" type="button" data-fdel="${j}" aria-label="Remove this test"${items.length < 2 ? ' disabled' : ''}>${svg(IC.x)}</button></div>`; }).join('')}
      <button class="btn s soft" type="button" data-fadd>${svg(IC.plus)}Add a test</button></div>`;
  }
  function readFilter(root, cur) {
    const fg = root; const mode = fg.querySelector('[data-fmode="any"]').getAttribute('aria-pressed') === 'true' ? 'any' : 'all';
    const rows = [...fg.querySelectorAll('.frow')].map(r => {
      const op = r.querySelector('[data-fo]').value, left = r.querySelector('[data-fl]').value;
      let right = r.querySelector('[data-fr]').value;
      const c = {left, op};
      if (!NO_RIGHT.has(op)) {
        if (op === 'between' || op === 'in' || op === 'not_in') c.right = right.split(',').map(x => x.trim()).filter(x => x !== '');
        else c.right = right;
      }
      return c;
    });
    return rows.length === 1 && mode === 'all' ? rows[0] : {[mode]: rows};
  }

  const ROWS_HELP = 'A list, like {{steps.rows.output}}';
  const DATAF = {
    fields: [['values', 'Fields (name: value)', 'obj']],
    sort: [['items', 'The list', 'text', ROWS_HELP], ['by', 'Sort by field', 'plain', 'A field name, like total (empty = the items themselves)'],
      ['order', 'Order', 'sel', [['asc', 'Smallest first (A to Z)'], ['desc', 'Largest first (Z to A)']]]],
    limit: [['items', 'The list', 'text', ROWS_HELP], ['count', 'How many', 'num'], ['keep', 'Keep', 'sel', [['first', 'The first'], ['last', 'The last']]]],
    dedupe: [['items', 'The list', 'text', ROWS_HELP], ['by', 'The same when this field matches', 'plain', 'Empty = the whole item']],
    aggregate: [['items', 'The list', 'text', ROWS_HELP], ['field', 'Field', 'plain', 'Like total; empty counts the items'],
      ['how', 'Work out', 'sel', [['sum', 'Sum'], ['count', 'Count'], ['avg', 'Average'], ['min', 'Smallest'], ['max', 'Largest'], ['list', 'List of the values'], ['unique', 'Each value once'], ['join', 'Join as text']]],
      ['sep', 'Join with', 'plain', 'Like , or a new line']],
    split: [['items', 'The list', 'text', ROWS_HELP], ['field', 'The list inside each item', 'plain', 'Like lines']],
    compare: [['a', 'The old list', 'text'], ['b', 'The new list', 'text'], ['key', 'Match items by field', 'plain', 'Like id or email']],
    keep_fields: [['items', 'The list (or one item)', 'text'], ['fields', 'Fields', 'plain', 'With commas, like name, email'],
      ['mode', 'Keep or drop', 'sel', [['keep', 'Keep only these'], ['drop', 'Drop these']]]],
    rename: [['items', 'The list (or one item)', 'text'], ['map', 'New names (old: new)', 'obj']],
    date: [['action', 'Do', 'sel', [['format', 'Format a date'], ['add', 'Add time'], ['subtract', 'Take away time'], ['diff', 'Time between two dates'], ['parse', 'Read a date'], ['now', 'The time now']]],
      ['value', 'The date', 'text', 'Like {{vars.due}} or 2026-12-01'], ['amount', 'How much', 'num'],
      ['unit', 'Unit', 'sel', [['days', 'Days'], ['weeks', 'Weeks'], ['months', 'Months'], ['years', 'Years'], ['hours', 'Hours'], ['minutes', 'Minutes']]],
      ['other', 'The other date', 'text'], ['format', 'Format', 'plain', '%d %b %Y = 05 Dec 2026 · %Y-%m-%d = 2026-12-05 · %H:%M = 14:30'], ['tz', 'Time zone', 'plain', 'Like Europe/London (optional)']],
    text: [['action', 'Do', 'sel', [['html_text', 'Text of a web page'], ['html_select', 'Pick parts of a web page'], ['xml_to_data', 'Read XML'], ['csv_to_rows', 'CSV text to rows'],
      ['rows_to_csv', 'Rows to CSV text'], ['json_parse', 'Read JSON text'], ['json_text', 'Turn into JSON text'], ['base64_encode', 'Base64 encode'], ['base64_decode', 'Base64 decode'],
      ['url_encode', 'Encode for a web address'], ['url_decode', 'Decode a web address part']]],
      ['value', 'The text', 'area'], ['selector', 'Part to pick (CSS)', 'plain', 'Like h2 or .price'], ['attr', 'Take this attribute', 'plain', 'Like href (empty = the text)'], ['separator', 'Separator', 'plain', 'Like , or ;']],
    file: [['action', 'Do', 'sel', [['make_xlsx', 'Make an Excel file'], ['make_csv', 'Make a CSV file'], ['make_pdf', 'Make a PDF'], ['read', 'Read a file']]],
      ['items', 'Rows', 'text', 'A list of objects, like {{steps.rows.output}}'], ['name', 'File name', 'plain'], ['sheet', 'Sheet name', 'plain'],
      ['title', 'Title', 'text'], ['value', 'Text', 'area'], ['file_id', 'The file', 'text', 'Its file id, like {{steps.mail.output.file_id}}']],
    crypto: [['action', 'Do', 'sel', [['sha256', 'SHA-256'], ['sha1', 'SHA-1'], ['md5', 'MD5'], ['hmac_sha256', 'HMAC SHA-256 (signed)'], ['uuid', 'A new random id (UUID)'], ['random', 'A random code']]],
      ['value', 'Value', 'text'], ['secret', 'Secret', 'text'], ['length', 'Length', 'num']],
  };
  const A = s => s.action;
  const SHOWIF = {
    date: {value: s => A(s) !== 'now', amount: s => ['add', 'subtract'].includes(A(s)), unit: s => ['add', 'subtract', 'diff'].includes(A(s)),
      other: s => A(s) === 'diff', format: s => A(s) === 'format', tz: s => ['format', 'parse', 'now'].includes(A(s))},
    text: {selector: s => A(s) === 'html_select', attr: s => A(s) === 'html_select', separator: s => A(s) === 'csv_to_rows'},
    file: {items: s => ['make_csv', 'make_xlsx'].includes(A(s)), name: s => A(s) !== 'read', sheet: s => A(s) === 'make_xlsx',
      title: s => A(s) === 'make_pdf', value: s => A(s) === 'make_pdf', file_id: s => A(s) === 'read'},
    crypto: {value: s => !['uuid', 'random'].includes(A(s)), secret: s => A(s) === 'hmac_sha256', length: s => A(s) === 'random'},
    aggregate: {sep: s => s.how === 'join'},
  };
  // the live result under a box that holds {{ }} (her route's newest data; nothing runs)
  function previewSoon(el, s) {
    const out = document.querySelector(`[data-prev="${CSS.escape(el.id)}"]`); if (!out || !ED) return;
    clearTimeout(el._pv);
    if (!/\{\{[\s\S]*?\}\}/.test(el.value)) { out.hidden = true; return; }
    el._pv = setTimeout(async () => {
      let r; try { r = await api('POST', `/api/route/routes/${enc(ED.r.id)}/eval`, {text: el.value, step: s.id}); } catch { return; }
      if (!document.body.contains(out)) return;
      out.hidden = false;
      if (r.errors && r.errors.length) { out.className = 'fprev bad'; out.textContent = r.errors.map(x => x.error).join(' · '); return; }
      out.className = 'fprev';
      const v = r.value, txt = v === null || v === undefined ? 'empty' : typeof v === 'string' ? v : JSON.stringify(v);
      out.textContent = r.has_data ? `= ${txt.length > 180 ? txt.slice(0, 180) + '…' : txt}` : 'Test the route once to see the result here.';
    }, 350);
  }
  async function stepPanel(box) {
    if (!ED.sel) {
      box.innerHTML = `<div class="pempty"><div class="pe-t">Pick a step on the canvas</div><p class="mut sm">Its settings open here. Use the <b>+</b> after a step to add the next one, or ask Hoola to build the route for you.</p>
        <button class="btn s" type="button" data-addend>${svg(IC.plus)}Add a step</button></div>`;
      box.querySelector('[data-addend]').addEventListener('click', () => addAt([], ED.steps.length));
      return;
    }
    if (ED.sel === 'trigger') { trigPanel(box); return; }
    const h = find(ED.sel); if (!h) { ED.sel = null; stepPanel(box); return; }
    const s = h.step;
    const parts = [];
    let tinfo = null;
    if (s.type === 'tool') tinfo = await toolInfo(s.name);
    if (!ED || ED.sel !== s.id || (box.id === 'edPanel' ? (ED.tab !== 'step' || ED.modal) : ED.modal !== s.id)) return;
    if (box.id === 'edPanel') parts.push(`<div class="phead">${appTile(s.app || (tinfo && tinfo.app), s.type, s.op)}<div><div class="pk">${esc(KIND[s.type] || s.type)}</div><div class="pt">${esc(titleOfStep(s))}</div></div>
      <span class="sp"></span><button class="btn s soft" type="button" data-big title="Open with its data (double-click a step)">Open with data</button></div>`);
    parts.push(field('What this step does', s.label || '', {k: 'label', ref: false, ph: 'In your own words, like "Add the order to my sheet"'}));
    if (s.type === 'tool') {
      parts.push(`<div class="tbox"><div><b>${esc(tinfo ? tinfo.label : nice(s.name))}</b><span class="mut sm">${esc(tinfo ? tinfo.desc : 'This tool is not on this server any more.')}</span></div>
        <button class="btn s soft" type="button" data-change-tool>Change</button></div>`);
      const args = s.args || {};
      const fields = tinfo ? tinfo.fields : [];
      const known = new Set(fields.map(f => f.name));
      fields.forEach(f => {
        const v = args[f.name];
        const txt = v === undefined ? '' : typeof v === 'string' ? v : JSON.stringify(v);
        const lab = f.name.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
        if (f.enum && f.enum.length) parts.push(field(lab, txt, {k: 'arg:' + f.name, options: [['', '—']].concat(f.enum.map(e => [e, e])), help: f.help, req: f.required}));
        else if (f.type === 'boolean') parts.push(field(lab, txt, {k: 'arg:' + f.name, options: [['', '—'], ['true', 'Yes'], ['false', 'No']], help: f.help, req: f.required}));
        else parts.push(field(lab, txt, {k: 'arg:' + f.name + ':' + f.type, area: ['object', 'array'].includes(f.type) || txt.length > 60, mono: ['object', 'array'].includes(f.type), help: f.help, req: f.required,
          ph: ['object', 'array'].includes(f.type) ? (f.type === 'array' ? '[ ]' : '{ }') : ''}));
      });
      const other = Object.fromEntries(Object.entries(args).filter(([k]) => !known.has(k)));
      if (Object.keys(other).length || !fields.length) parts.push(field(fields.length ? 'Other values it sends' : 'What it sends (as data)', Object.keys(other).length ? JSON.stringify(other, null, 2) : '', {k: 'argsjson', area: true, mono: true, rows: 5, ph: '{ }'}));
    } else if (s.type === 'notify') parts.push(field('Message to you', s.text || '', {k: 'text', area: true}));
    else if (s.type === 'approval') parts.push(field('The question', s.question || '', {k: 'question', area: true, help: 'The run waits here until you tap Approve.'}));
    else if (s.type === 'set') { parts.push(field('Value name', s.name || '', {k: 'name', ref: false, mono: true, help: 'Later steps read it as {{vars.' + (s.name || 'name') + '}}'})); parts.push(field('Value', typeof s.value === 'string' ? s.value : JSON.stringify(s.value ?? ''), {k: 'value', area: true})); }
    else if (s.type === 'http') {
      parts.push(field('Method', s.method || 'GET', {k: 'method', options: [['GET', 'GET (read)'], ['POST', 'POST (send)']]}));
      parts.push(field('Address', s.url || '', {k: 'url', mono: true, ph: 'https://'}));
      if ((s.method || 'GET') === 'POST') parts.push(field('What it sends', typeof s.body === 'string' ? s.body : JSON.stringify(s.body ?? {}, null, 2), {k: 'body', area: true, mono: true, rows: 5}));
    } else if (s.type === 'data') {
      const spec = DATAF[s.op] || [];
      spec.forEach(([key, lab, kind, extra]) => {
        const show = (SHOWIF[s.op] || {})[key];
        if (show && !show(s)) return;
        const v = s[key];
        if (kind === 'sel') parts.push(field(lab, v === undefined ? extra[0][0] : v, {k: 'd:' + key, options: extra}));
        else if (kind === 'obj') parts.push(field(lab, typeof v === 'string' ? v : JSON.stringify(v || {}, null, 2), {k: 'dobj:' + key, area: true, mono: true, rows: 5,
          help: 'Each line a name and a value; values can use {{ }}'}));
        else parts.push(field(lab, v === undefined || v === null ? '' : typeof v === 'string' ? v : JSON.stringify(v), {k: 'd:' + key, area: kind === 'area', rows: 4,
          ref: kind !== 'plain', mono: kind === 'plain' && /field|by|key|attr|selector/.test(key), num: kind === 'num', help: typeof extra === 'string' ? extra : ''}));
      });
      if (s.op === 'file') parts.push('<p class="mut sm">A file it makes is kept for 24 hours: send it on in a later step (its file id is {{steps.' + esc(s.id) + '.output.file_id}}).</p>');
    } else if (s.type === 'code') parts.push(field('Python', s.code || '', {k: 'code', area: true, mono: true, rows: 10, help: 'Runs in a locked sandbox. Print what you want the next steps to read.'}));
    else if (s.type === 'wait') { parts.push(field('Seconds to wait', s.duration_s || '', {k: 'duration_s', ref: false, num: true, help: 'Up to 3600, or leave empty and give a time'})); parts.push(field('Or until (HH:MM)', s.until || '', {k: 'until', ref: false, ph: '09:00'})); }
    else if (s.type === 'loop') parts.push(field('A list to go through', typeof s.items === 'string' ? s.items : JSON.stringify(s.items ?? ''), {k: 'items', mono: true, ph: '{{steps.rows.output}}', help: 'The steps inside run once for every item (up to 50).'}));
    else if (s.type === 'condition' || s.type === 'filter') {
      parts.push(`<div class="psub">${s.type === 'filter' ? 'Goes on only when' : 'Takes “If yes” when'}</div>`);
      parts.push(filterRows(s.filter || (s.op ? {left: s.left, op: s.op, right: s.right} : null), 'main'));
    } else if (s.type === 'router') {
      parts.push('<div class="psub">Ways, tested in order</div>');
      (s.routes || []).forEach((rt, j) => parts.push(`<div class="way" data-way="${j}">${field('Name of this way', rt.label || '', {k: 'rlabel:' + j, ref: false})}${filterRows(rt.filter, 'r' + j)}
        <button class="btn s soft bad" type="button" data-wdel="${j}"${(s.routes || []).length < 2 ? ' disabled' : ''}>Remove this way</button></div>`));
      parts.push(`<div class="crow"><button class="btn s soft" type="button" data-wadd${(s.routes || []).length >= 8 ? ' disabled' : ''}>${svg(IC.plus)}Add a way</button>
        <label class="chk"><input type="checkbox" data-fallback${Array.isArray(s.fallback) ? ' checked' : ''}> “Anything else” way</label></div>`);
    }
    const oe = s.on_error || {};
    parts.push('<div class="psub">If this step fails</div>');
    parts.push(field('Then', oe.do || '', {k: 'oe_do', options: Object.entries(DO)}));
    if (oe.do === 'break') parts.push(`<div class="two">${field('Tries', oe.retries ?? 3, {k: 'oe_retries', ref: false, num: true})}${field('Minutes apart', oe.wait_min ?? 10, {k: 'oe_wait', ref: false, num: true})}</div>`);
    if (oe.do === 'resume') parts.push(field('Value to use', typeof oe.value === 'string' ? oe.value : JSON.stringify(oe.value ?? ''), {k: 'oe_value'}));
    parts.push('<div class="psub">Name</div>');
    const sidId = fid();
    parts.push(`<div class="fld"><label for="${sidId}">Step name (later steps read its result by this)</label><div class="fc"><input id="${sidId}" data-sid class="mono" value="${esc(s.id)}"></div></div>`);
    parts.push(`<div class="pfoot"><button class="btn s soft" type="button" data-dup>${svg(IC.copy)}Duplicate</button><span class="sp"></span><button class="btn s soft bad" type="button" data-del>${svg(IC.trash)}Delete step</button></div>`);
    box.innerHTML = `<div class="pform">${parts.join('')}</div>`;
    wireStep(box.firstElementChild, s);
  }
  function setArg(s, name, typ, raw) {
    s.args = s.args || {};
    if (raw === '') { delete s.args[name]; return; }
    if (typ === 'integer' || typ === 'number') { const n = Number(raw); s.args[name] = raw.includes('{{') || isNaN(n) ? raw : n; return; }
    if (typ === 'object' || typ === 'array') { try { s.args[name] = JSON.parse(raw); } catch { s.args[name] = raw; } return; }
    if (raw === 'true' || raw === 'false') { s.args[name] = raw === 'true'; return; }
    s.args[name] = raw;
  }
  function wireStep(box, s) {
    let snapped = false;
    const once = () => { if (!snapped) { before(); snapped = true; } };
    box.addEventListener('focusin', () => { snapped = false; });
    const apply = el => {
      const k = el.dataset.k; if (!k) return;
      const v = el.value;
      once();
      if (k.startsWith('arg:')) { const [, name, typ] = k.split(':'); setArg(s, name, typ || 'string', v); }
      else if (k === 'argsjson') { try { const o = v.trim() ? JSON.parse(v) : {}; const known = new Set(((TOOLS[s.name] || {}).fields || []).map(f => f.name));
        Object.keys(s.args || {}).forEach(x => { if (!known.has(x)) delete s.args[x]; }); s.args = Object.assign(s.args || {}, o); el.classList.remove('err'); } catch { el.classList.add('err'); return; } }
      else if (k === 'label') { if (v.trim()) s.label = v; else delete s.label; }
      else if (k === 'duration_s') { if (v.trim()) s.duration_s = Math.max(1, Math.min(3600, parseInt(v, 10) || 0)); else delete s.duration_s; }
      else if (k === 'until') { if (v.trim()) s.until = v.trim(); else delete s.until; }
      else if (k === 'value' || k === 'items') s[k] = v;
      else if (k === 'body') { try { s.body = v.trim() ? JSON.parse(v) : {}; } catch { s.body = v; } }
      else if (k === 'method') s.method = v;
      else if (k.startsWith('rlabel:')) { const j = +k.split(':')[1]; s.routes[j].label = v; }
      else if (k === 'oe_do') { if (v) s.on_error = Object.assign({}, s.on_error || {}, {do: v}); else delete s.on_error; }
      else if (k === 'oe_retries') { s.on_error.retries = Math.max(0, Math.min(10, parseInt(v, 10) || 0)); }
      else if (k === 'oe_wait') { s.on_error.wait_min = Math.max(1, Math.min(1440, parseInt(v, 10) || 1)); }
      else if (k === 'oe_value') s.on_error.value = v;
      else if (k.startsWith('d:')) { const key = k.slice(2); if (v === '') delete s[key]; else s[key] = /^-?\d+(\.\d+)?$/.test(v.trim()) && ['count', 'amount', 'length'].includes(key) ? Number(v) : v; }
      else if (k.startsWith('dobj:')) { try { s[k.slice(5)] = v.trim() ? JSON.parse(v) : {}; el.classList.remove('err'); } catch { el.classList.add('err'); return; } }
      else s[k] = v;
      ED.dirty = snap() !== ED.saved; draw(); topState();
      if (['method', 'oe_do', 'd:action', 'd:how', 'd:mode'].includes(k)) stepPanel(box.parentNode);
      if (el.tagName !== 'SELECT') previewSoon(el, s);
    };
    box.addEventListener('input', e => { if (e.target.dataset.k && e.target.tagName !== 'SELECT') apply(e.target); else if (e.target.closest('.fgroup')) applyFilter(e.target); });
    box.addEventListener('change', e => { if (e.target.dataset.k && e.target.tagName === 'SELECT') apply(e.target); else if (e.target.closest('.fgroup')) applyFilter(e.target, true);
      else if (e.target.dataset.fjson !== undefined) { try { const f = JSON.parse(e.target.value); once(); if (e.target.dataset.fjson === 'main') { s.filter = f; delete s.left; delete s.op; delete s.right; } else s.routes[+e.target.dataset.fjson.slice(1)].filter = f; e.target.classList.remove('err'); ED.dirty = snap() !== ED.saved; draw(); topState(); } catch { e.target.classList.add('err'); } } });
    function setF(fg, f) {
      const key = fg.dataset.fg;
      if (key === 'main') { s.filter = f; delete s.left; delete s.op; delete s.right; } else s.routes[+key.slice(1)].filter = f;
    }
    function applyFilter(el, redraw) {
      const fg = el.closest('.fgroup'); once(); setF(fg, readFilter(fg));
      ED.dirty = snap() !== ED.saved; draw(); topState();
      if (redraw && el.dataset.fo !== undefined) stepPanel(box.parentNode);
    }
    box.addEventListener('click', e => {
      const t = e.target.closest('button'); if (!t) return;
      if (t.dataset.ref) { refMenu(t); return; }
      const fg = t.closest('.fgroup');
      if (t.dataset.fmode && fg) { fg.querySelectorAll('[data-fmode]').forEach(x => x.setAttribute('aria-pressed', String(x === t))); applyFilter(t); return; }
      if (t.dataset.fadd !== undefined && fg) { const f = readFilter(fg); const g = f.all || f.any ? f : {all: [f]}; (g.all || g.any).push({left: '', op: 'exists'}); once(); setF(fg, g); changed(false); return; }
      if (t.dataset.fdel !== undefined && fg) { const f = readFilter(fg); const g = f.all || f.any ? f : {all: [f]}; (g.all || g.any).splice(+t.dataset.fdel, 1); once(); const l = g.all || g.any; setF(fg, l.length === 1 ? l[0] : g); changed(false); return; }
      if (t.dataset.wadd !== undefined) { before(); s.routes.push({label: 'Way ' + (s.routes.length + 1), filter: {left: '', op: 'exists'}, steps: []}); changed(false); return; }
      if (t.dataset.wdel !== undefined) { before(); s.routes.splice(+t.dataset.wdel, 1); changed(false); return; }
      if (t.dataset.dup !== undefined) { dupStep(s.id); return; }
      if (t.dataset.big !== undefined) { openModal(s.id); return; }
      if (t.dataset.del !== undefined) {
        if (t.dataset.sure !== '1') { t.dataset.sure = '1'; t.innerHTML = `${svg(IC.trash)}${['condition', 'router', 'loop'].includes(s.type) ? 'Delete it and the steps inside?' : 'Delete this step?'}`; return; }
        delStep(s.id); return;
      }
      if (t.dataset.changeTool !== undefined) { const h = find(s.id); ED.replace = s.id; addAt(h.path, h.i); }
    });
    const fb = box.querySelector('[data-fallback]');
    if (fb) fb.addEventListener('change', () => { before(); if (fb.checked) s.fallback = s.fallback || []; else delete s.fallback; changed(false); });
    const sid = box.querySelector('[data-sid]');
    sid.addEventListener('change', () => { const v = sid.value.trim(); if (v === s.id) return; if (!renameStep(s.id, v)) sid.value = s.id; });
  }

  function trigPanel(box) {
    const t = ED.trig, sp = t.spec || {};
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    const dayW = {mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun'};
    let zones = []; try { zones = Intl.supportedValuesOf('timeZone'); } catch {}
    box.innerHTML = `<div class="pform"><div class="phead"><span class="ap k-trig">${svg(IC.bolt)}</span><div><div class="pk">What starts it</div><div class="pt">${esc(trigWords()[0])}</div></div></div>
      <div class="seg" role="radiogroup" aria-label="What starts the route">${[['manual', 'By hand'], ['schedule', 'On a schedule'], ['webhook', 'When data arrives']].map(([k, w]) =>
        `<button type="button" data-tk="${k}" aria-pressed="${t.kind === k}">${w}</button>`).join('')}</div>
      ${t.kind === 'manual' ? '<p class="mut sm">It runs when you test it here, run it from a chat, or another route calls for it.</p>' : ''}
      ${t.kind === 'webhook' ? `<p class="mut sm">Another app starts it by sending data to a secret web address. What it sends is <code>{{vars}}</code> in your steps.</p>
        <div id="addrBox">${ED.r.trigger === 'webhook' ? '<button class="btn s soft" type="button" id="addrNew">Make a new address</button>' : '<span class="mut sm">Save first, then make its address here.</span>'}</div>` : ''}
      ${t.kind === 'schedule' ? `
        ${field('At these times (HH:MM, 24-hour)', (sp.at || []).join(', '), {k: 'at', ref: false, ph: '09:00, 17:30'})}
        <div class="fld"><label>On these days <span class="mut sm">(none = every day)</span></label><div class="days">${days.map(d => `<button type="button" data-day="${d}" aria-pressed="${(sp.days || []).includes(d)}">${dayW[d]}</button>`).join('')}</div></div>
        <div class="two">${field('Or every N minutes', sp.every_minutes || '', {k: 'every_minutes', ref: false, num: true, help: '15 or more'})}${field('Or every N hours', sp.every_hours || '', {k: 'every_hours', ref: false, num: true})}</div>
        <div class="fld"><label for="tzIn">Time zone</label><div class="fc"><input id="tzIn" list="tzList" value="${esc(sp.timezone || '')}" placeholder="${esc(TZ || 'Europe/London')}"></div>
          <datalist id="tzList">${zones.map(z => `<option value="${esc(z)}">`).join('')}</datalist></div>
        ${field('Skip the public holidays of', sp.skip_holidays || '', {k: 'skip_holidays', ref: false, ph: 'A country code, like GB, US, DE', help: 'The run waits for the next working day.'})}
        <div class="two">${field('Quiet from', (sp.quiet || {}).from || '', {k: 'qfrom', ref: false, ph: '22:00'})}${field('Quiet until', (sp.quiet || {}).to || '', {k: 'qto', ref: false, ph: '08:00'})}</div>` : ''}
      <p class="mut sm">Changes here count once you tap Save.</p></div>`;
    box.querySelectorAll('[data-tk]').forEach(b => b.addEventListener('click', () => {
      if (t.kind === b.dataset.tk) return;
      before(); t.kind = b.dataset.tk;
      if (t.kind === 'schedule' && !Object.keys(t.spec || {}).some(k => ['at', 'every_minutes', 'every_hours', 'days', 'monthdays', 'dates', 'once'].includes(k))) t.spec = {at: ['09:00'], timezone: TZ || ''};
      changed(false); trigPanel(box);
    }));
    const tz = $('#tzIn');
    if (tz) tz.addEventListener('change', () => { before(); if (tz.value.trim()) t.spec.timezone = tz.value.trim(); else delete t.spec.timezone; changed(false); });
    box.querySelectorAll('[data-day]').forEach(b => b.addEventListener('click', () => {
      before(); const d = b.dataset.day, cur = new Set(t.spec.days || []);
      cur.has(d) ? cur.delete(d) : cur.add(d); const v = days.filter(x => cur.has(x)); if (v.length) t.spec.days = v; else delete t.spec.days;
      changed(false); trigPanel(box);
    }));
    box.firstElementChild.addEventListener('change', e => {
      const k = e.target.dataset.k; if (!k) return;
      const v = e.target.value.trim(); before();
      if (k === 'at') { const a = v.split(/[,\s]+/).filter(Boolean); if (a.length) t.spec.at = a; else delete t.spec.at; }
      else if (k === 'every_minutes' || k === 'every_hours') { if (v) t.spec[k] = parseInt(v, 10) || v; else delete t.spec[k]; }
      else if (k === 'skip_holidays') { if (v) t.spec.skip_holidays = v.toUpperCase(); else delete t.spec.skip_holidays; }
      else if (k === 'qfrom' || k === 'qto') { const q = Object.assign({}, t.spec.quiet || {}); q[k === 'qfrom' ? 'from' : 'to'] = v; if (q.from || q.to) t.spec.quiet = q; else delete t.spec.quiet; }
      changed(false);
    });
    const an = $('#addrNew');
    if (an) an.addEventListener('click', async () => {
      if (an.dataset.sure !== '1') { an.dataset.sure = '1'; an.textContent = 'The old address stops working. Make a new one?'; return; }
      an.disabled = true;
      try {
        const a = await api('POST', `/api/route/routes/${enc(ED.r.id)}/address`);
        const url = /^https?:/.test(a.url) ? a.url : location.origin + a.url;
        $('#addrBox').innerHTML = `<code class="addr">${esc(url)}</code><span class="mut sm">${esc(a.note)}</span><button class="btn soft s" type="button" id="addrCopy">Copy</button>`;
        $('#addrCopy').addEventListener('click', () => navigator.clipboard.writeText(url).then(() => toast('Copied.'), () => toast('Copy it by hand.', true)));
      } catch (err) { toast(err.message, true); an.disabled = false; }
    });
  }

  // the add-a-step panel: search + groups (step kinds and Hoola's tools / connected apps)
  const GROUPS = [['Human in the loop', IC.approval, 'k-warm'], ['Flow', IC.route, 'k-flow'], ['Data', IC.store, 'k-data'], ['Core', IC.http, 'k-core']];
  async function addPanel(box) {
    const q0 = ED.addQ || '';
    box.innerHTML = `<div class="pform"><div class="phead"><span class="ap k-trig">${svg(IC.plus)}</span><div><div class="pk">${ED.replace ? 'Change the tool' : 'Add a step'}</div><div class="pt">${esc(addWhere())}</div></div>
      <span class="sp"></span><button class="btn s soft ib" type="button" id="addX" aria-label="Close">${svg(IC.x)}</button></div>
      <label class="srch big">${svg(IC.search)}<input id="addQ" value="${esc(q0)}" placeholder="Search, like “sheet”, “email”, “wait”" aria-label="Search steps" autocomplete="off"></label>
      <div id="addList" class="alist"><div class="mut sm">Loading…</div></div>
      <p class="mut sm">Can't find it? Ask Hoola for what you need and it picks the step.</p></div>`;
    $('#addX').addEventListener('click', () => { ED.tab = 'step'; ED.replace = null; ED.addAt = null; panel(); });
    const inp = $('#addQ');
    const fill = async () => {
      const q = inp.value.trim(); ED.addQ = q;
      let cat; try { cat = await api('GET', `/api/route/catalog?q=${enc(q)}`); } catch (e) { $('#addList').innerHTML = `<div class="errbox">${esc(e.message)}</div>`; return; }
      if (!ED || ED.tab !== 'add' || inp.value.trim() !== q) return;
      ED.cat = cat;
      const kw = q.toLowerCase();
      const kinds = ED.replace ? [] : cat.kinds.filter(k => !kw || (k.title + ' ' + k.sub + ' ' + k.group + ' ' + k.type).toLowerCase().includes(kw));
      const row = (attr, tile, t, sub, tag) => `<button type="button" class="arow" ${attr}>${tile}<span class="at"><b>${esc(t)}</b><small>${esc(sub)}</small></span>${tag ? `<span class="atag">${esc(tag)}</span>` : ''}</button>`;
      const toolRows = cat.tools.map((t, i) => row(`data-tool="${i}"`, appTile(t.app), t.label, t.desc, t.app && t.app.kind === 'app' ? appName(t.app.slug) : 'Hoola'));
      let html = '';
      if (!kw) {
        if (!ED.replace) GROUPS.forEach(([g, ic, cls]) => { const ks = kinds.filter(k => k.group === g); if (!ks.length) return;
          html += `<div class="agrp">${esc(g)}</div>` + ks.map(k => row(`data-kind="${esc(k.key || k.type)}"`, `<span class="ap ${cls}">${svg(OPIC[k.key] || IC[k.type] || ic)}</span>`, k.title, k.sub)).join(''); });
        html += `<div class="agrp">App actions <span class="mut">· every Hoola tool and your connected apps</span></div>` + toolRows.join('');
      } else {
        html = kinds.map(k => row(`data-kind="${esc(k.key || k.type)}"`, `<span class="ap k-${KIND_TILE[k.type] || 'core'}">${svg(OPIC[k.key] || IC[k.type] || IC.set)}</span>`, k.title, k.sub, k.group)).join('') + toolRows.join('');
        if (!html) html = '<div class="mut sm">Nothing found. Try other words, or ask Hoola.</div>';
      }
      $('#addList').innerHTML = html;
    };
    inp.addEventListener('input', () => { clearTimeout(ED.addT); ED.addT = setTimeout(fill, 180); });
    $('#addList').addEventListener('click', e => {
      const b = e.target.closest('.arow'); if (!b || !ED.cat) return;
      if (b.dataset.kind) { const k = ED.cat.kinds.find(x => (x.key || x.type) === b.dataset.kind); insertStep(makeKind(k)); return; }
      const t = ED.cat.tools[+b.dataset.tool];
      TOOLS[t.name] = t;
      if (ED.replace) { const h = find(ED.replace); ED.replace = null; if (!h) return; before(); Object.assign(h.step, {name: t.name, app: t.app, args: {}}); if (!h.step.label) h.step.label = t.label;
        ED.tab = 'step'; ED.addAt = null; changed(false); return; }
      insertStep(makeTool(t));
    });
    fill(); setTimeout(() => inp.focus(), 30);
  }
  function addWhere() {
    const a = ED.addAt; if (!a) return '';
    const lst = listAt(a.path) || [];
    const prev = a.i > 0 ? lst[a.i - 1] : null;
    if (prev) return `after “${titleOfStep(prev)}”`;
    if (!a.path.length) return 'as the first step';
    const h = find(a.path[0]);
    const lab = a.path[1] === 'then' ? 'If yes' : a.path[1] === 'else' ? 'If no' : a.path[1] === 'body' ? 'For each item' : a.path[1] === 'fallback' ? 'Anything else'
      : ((h && h.step.routes[a.path[2]] || {}).label || 'this way');
    return `inside “${lab}”`;
  }

  // ---------------------------------------------------------------- Ask Hoola (the route's own chat)
  async function askPanel(box) {
    if (!ED.chat) {
      box.innerHTML = '<div class="mut sm pempty">Opening the chat…</div>';
      try { ED.chat = (await api('GET', `/api/route/routes/${enc(ED.r.id)}/chat`)).id; } catch (e) { box.innerHTML = `<div class="errbox">${esc(e.message)}</div>`; return; }
      if (!ED || ED.tab !== 'ask') return;
    }
    if (!$('#askList')) {
      box.innerHTML = `<div class="askwrap"><div class="asklist" id="askList" aria-live="polite"></div>
        <div id="askChange"></div>
        <form class="askbox" id="askBox"><textarea id="askIn" rows="2" placeholder="Change this route… like “if it is over 5,000, ask me first”" aria-label="Ask Hoola to change the route"></textarea>
        <button class="go" type="submit" id="askSend" aria-label="Send" disabled>${svg(IC.up)}</button></form>
        <div class="tries">${['Explain this route', 'Run it only on weekdays', 'If a step fails, tell me'].map(t => `<button type="button" class="chip" data-try="${esc(t)}">${esc(t)}</button>`).join('')}</div></div>`;
      const ta = $('#askIn'), go = $('#askSend');
      ta.addEventListener('input', () => { go.disabled = !ta.value.trim() || ED.asking; });
      ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#askBox').requestSubmit(); } });
      $('#askBox').addEventListener('submit', e => { e.preventDefault(); sendAsk(ta.value.trim()); });
      box.querySelector('.tries').addEventListener('click', e => { const b = e.target.closest('[data-try]'); if (b) sendAsk(b.dataset.try); });
    }
    await chatDraw();
    let pending = null; try { pending = JSON.parse(sessionStorage.getItem(ASK_KEY) || 'null'); } catch {}
    if (pending && pending.id === ED.r.id) { try { sessionStorage.removeItem(ASK_KEY); } catch {} sendAsk(pending.text); }
  }
  async function chatDraw() {
    if (!ED || !ED.chat) return;
    let m; try { m = await api('GET', `/api/conversations/${enc(ED.chat)}/messages?limit=40`); } catch { return; }
    const L = $('#askList'); if (!L) return m.messages;
    L.innerHTML = m.messages.map(x => x.role === 'user' ? `<div class="mu">${esc(x.text)}</div>` : `<div class="ma">${md(x.text)}</div>`).join('') +
      (ED.asking ? `<div class="ma working"><span class="dots"><i></i><i></i><i></i></span> ${esc(ED.askLine || 'Working on it')}</div>` : '');
    L.scrollTop = L.scrollHeight;
    return m.messages;
  }
  async function sendAsk(text) {
    if (!text || !ED || ED.asking) return;
    if (ED.dirty && !(await save())) { toast('Save your changes first, so Hoola works on the newest route.', true); return; }
    ED.asking = true; ED.askLine = 'Working on it';
    ED.before = {steps: clone(ED.steps), trig: clone(ED.trig), version: ED.base};
    const ta = $('#askIn'); if (ta) { ta.value = ''; $('#askSend').disabled = true; }
    const ch = $('#askChange'); if (ch) ch.innerHTML = '';
    try {
      if (!ED.chat) ED.chat = (await api('GET', `/api/route/routes/${enc(ED.r.id)}/chat`)).id;
      await api('POST', `/api/conversations/${enc(ED.chat)}/messages`, {text: text + (TZ ? `\n(My time zone is ${TZ}.)` : '')});
    } catch (e) { ED.asking = false; toast(e.message, true); chatDraw(); return; }
    chatDraw(); pollAsk(0);
  }
  async function pollAsk(n) {
    if (!ED || ED.dead) return;
    let res = null; try { res = await api('GET', `/api/conversations/${enc(ED.chat)}/result`); } catch {}
    const st = res && res.status;
    ED.askLine = (res && res.line && res.status !== 'done') ? res.line : 'Working on it';
    const msgs = (await chatDraw()) || [];
    const last = msgs.length ? msgs[msgs.length - 1].role : '';
    if ((st === 'queued' || st === 'working' || !st || (last === 'user' && n < 60)) && n < 400) { ED.chatT = setTimeout(() => pollAsk(n + 1), n < 4 ? 900 : 1500); return; }
    ED.asking = false; await chatDraw();
    const go = $('#askSend'), ta = $('#askIn'); if (go && ta) go.disabled = !ta.value.trim();
    // did Hoola change the route?
    let r; try { r = await api('GET', `/api/route/routes/${enc(ED.r.id)}`); } catch { return; }
    if (!ED || r.version === ED.base) return;
    const was = ED.before;
    const keepPos = ED.pos, keepNotes = ED.notes;
    load(r); ED.pos = keepPos; ED.notes = keepNotes; ED.hist = []; ED.fut = [];
    draw(); topState();
    showChanges(was);
  }
  function showChanges(was) {
    const box = $('#askChange'); if (!box || !was) return;
    const idx = l => { const o = {}; const w = x => (x || []).forEach(s => { o[s.id] = s; ['then', 'else', 'body', 'fallback'].forEach(k => w(s[k])); (s.routes || []).forEach(r => w(r.steps)); }); w(l); return o; };
    const strip = s => { const c = Object.assign({}, s); delete c.app; ['then', 'else', 'body', 'fallback', 'routes'].forEach(k => delete c[k]); return JSON.stringify(c); };
    const A = idx(was.steps), B = idx(ED.steps), rows = [];
    Object.keys(B).forEach(k => { if (!A[k]) rows.push(['+', titleOfStep(B[k])]); else if (strip(A[k]) !== strip(B[k])) rows.push(['~', titleOfStep(B[k])]); });
    Object.keys(A).forEach(k => { if (!B[k]) rows.push(['−', titleOfStep(A[k])]); });
    if (JSON.stringify(was.trig) !== JSON.stringify(ED.trig)) rows.push(['~', 'What starts it: ' + trigWords()[0]]);
    if (!rows.length) return;
    box.innerHTML = `<div class="chg"><div class="chg-h">${rows.length} change${rows.length === 1 ? '' : 's'} on the canvas</div>
      ${rows.slice(0, 12).map(([k, t]) => `<div class="chg-r"><span class="ck ${k === '+' ? 'add' : k === '−' ? 'del' : 'mod'}">${k}</span>${esc(t)}</div>`).join('')}
      <div class="chg-a"><button class="btn s" type="button" id="chgKeep">Keep changes</button><button class="btn s soft" type="button" id="chgUndo">Undo</button></div></div>`;
    $('#chgKeep').addEventListener('click', () => { box.innerHTML = ''; });
    $('#chgUndo').addEventListener('click', async () => {
      $('#chgUndo').disabled = true;
      try {
        const r = await api('PUT', `/api/route/routes/${enc(ED.r.id)}/graph`, {steps: was.steps, trigger: was.trig.kind, trigger_spec: was.trig.spec, base: ED.base});
        const keepPos = ED.pos, keepNotes = ED.notes; load(r); ED.pos = keepPos; ED.notes = keepNotes; draw(); topState(); box.innerHTML = ''; toast('Put back as it was.');
      } catch (e) { toast(e.message, true); $('#chgUndo').disabled = false; }
    });
  }

  // ---------------------------------------------------------------- R2: a step with its data (in · settings · out)
  async function loadData() {
    if (!ED || !ED.r) return;
    try { ED.data = await api('GET', `/api/route/routes/${enc(ED.r.id)}/data`); } catch { return; }
    if (!ED) return;
    draw();
    if (ED.modal) { modalIn(); modalOut(); }
  }
  const TYPEW = v => v === null || v === undefined ? 'empty' : Array.isArray(v) ? 'list' : typeof v === 'object' ? 'object' : typeof v === 'number' ? '#' : typeof v === 'boolean' ? 'yes/no' : 'text';
  const prev = v => v === null || v === undefined ? '—' : Array.isArray(v) ? `${v.length} item${v.length === 1 ? '' : 's'}` : typeof v === 'object' ? `${Object.keys(v).length} field${Object.keys(v).length === 1 ? '' : 's'}` : S(v).slice(0, 80);
  // a value as rows of fields she can drag into a box: {path, key, depth, type, preview}
  function flatten(v, base, out, depth, label) {
    out = out || []; depth = depth || 0;
    if (out.length > 400) return out;
    if (depth === 0 && (v === null || typeof v !== 'object')) { out.push({path: base, key: label || 'value', depth: 0, type: TYPEW(v), prev: prev(v)}); return out; }
    if (v && v._too_big) { out.push({path: base, key: 'too big to show whole', depth, type: 'text', prev: S(v.first_part).slice(0, 80)}); return out; }
    const keys = Array.isArray(v) ? v.slice(0, 3).map((_, i) => String(i)) : Object.keys(v || {}).slice(0, 80);
    keys.forEach(k => {
      const x = v[k], p = `${base}.${k}`;
      out.push({path: p, key: Array.isArray(v) ? `item ${Number(k) + 1}` : k, depth, type: TYPEW(x), prev: prev(x)});
      if (x && typeof x === 'object' && depth < 4) flatten(x, p, out, depth + 1);
    });
    if (Array.isArray(v) && v.length > 3) out.push({path: '', key: `… ${v.length - 3} more`, depth, type: '', prev: ''});
    return out;
  }
  function fieldRows(rows, drag) {
    return rows.map(r => r.path && drag ? `<div class="fr" draggable="true" data-expr="{{${esc(r.path)}}}" style="padding-left:${10 + r.depth * 16}px" title="Drag into a box, or click to put it in the box you were in">
        <span class="fk">${esc(r.key)}</span><span class="ft">${esc(r.type)}</span><span class="fv">${esc(r.prev)}</span></div>`
      : `<div class="fr ro" style="padding-left:${10 + r.depth * 16}px"><span class="fk">${esc(r.key)}</span><span class="ft">${esc(r.type)}</span><span class="fv">${esc(r.prev)}</span></div>`).join('');
  }
  function sourcesFor(id) {
    const d = ED.data || {vars: {}, steps: {}, pins: {}};
    const out = [];
    const pinsT = d.pins && d.pins.trigger;
    const vars = pinsT !== undefined ? pinsT : d.vars;
    if (vars && Object.keys(vars).length) out.push({title: pinsT !== undefined ? 'The data a test starts with (pinned)' : 'The data it started with', base: 'vars', v: vars});
    const h = id ? find(id) : null;
    if (h && h.path[1] === 'body') {
      const lp = find(h.path[0]), lo = lp && d.steps[lp.step.id] && d.steps[lp.step.id].output;
      const it = lo && Array.isArray(lo.items) ? lo.items[0] : undefined;
      out.push({title: 'The item in this round', base: 'item', v: it, none: it === undefined ? 'Test “' + titleOfStep(lp.step) + '” to see an item here.' : ''});
    }
    const flat = allSteps(); const idx = flat.findIndex(x => x.id === id);
    flat.slice(0, idx < 0 ? flat.length : idx).forEach(x => {
      if (['condition', 'router', 'filter', 'wait', 'approval'].includes(x.type)) return;
      if (x.type === 'set') { const sv = (d.vars || {})[x.name] !== undefined ? d.vars[x.name] : ((d.steps[x.id] || {}).output || {}).value;
        out.push({title: `${titleOfStep(x)} (value)`, base: `vars.${x.name}`, v: sv, label: x.name, none: 'Test this step to see its value.'}); return; }
      const pinned = d.pins && d.pins[x.id] !== undefined;
      const st = pinned ? {output: d.pins[x.id]} : d.steps[x.id];
      out.push({title: titleOfStep(x) + (pinned ? ' (pinned)' : ''), base: `steps.${x.id}.output`, v: st ? st.output : undefined,
        none: st ? '' : 'No data yet - test this step or the route.'});
    });
    return out;
  }
  function openModal(id) {
    if (!ED || !id) return;
    ED.sel = id; ED.modal = id; ED.mview = ED.mview || {in: 'fields', out: 'fields'}; ED.stepRes = null;
    draw(); panel(); modalDraw();
    if (!ED.data) loadData();
  }
  function closeModal() { if (!ED) return; ED.modal = null; const m = $('#smodal'); if (m) { m.hidden = true; m.innerHTML = ''; } panel(); draw(); }
  function modalDraw(keepMid) {
    const m = $('#smodal'); if (!m || !ED.modal) return;
    const id = ED.modal, trig = id === 'trigger', h = trig ? null : find(id);
    if (!trig && !h) { closeModal(); return; }
    if (keepMid && m.querySelector('.sm-mid')) { modalMid(); modalIn(); modalOut(); return; }
    const s = h && h.step;
    const [tt, ts] = trig ? trigWords() : [titleOfStep(s), KIND[s.type] || s.type];
    m.hidden = false;
    m.innerHTML = `<div class="sm-card">
      <div class="sm-top">${trig ? `<span class="ap k-trig">${svg(IC.bolt)}</span>` : appTile(s.app, s.type, s.op)}<div class="sm-t"><div class="pk">${esc(trig ? 'What starts it' : ts)}</div><div class="pt">${esc(tt)}</div></div>
        <span class="sp"></span>${trig ? '' : `<button class="btn s" type="button" id="smTest">${svg(IC.play)}Test step</button>`}
        <button class="btn s soft ib" type="button" id="smX" aria-label="Close">${svg(IC.x)}</button></div>
      <div class="sm-cols"><section class="sm-in" aria-label="What comes in"></section><section class="sm-mid" aria-label="Settings"></section><section class="sm-out" aria-label="What goes out"></section></div></div>`;
    $('#smX').addEventListener('click', closeModal);
    const tb = $('#smTest'); if (tb) tb.addEventListener('click', () => testStep(false));
    modalMid(); modalIn(); modalOut();
    m.querySelector('.sm-in').addEventListener('dragstart', e => { const r = e.target.closest('[data-expr]'); if (!r) return;
      e.dataTransfer.setData('text/plain', r.dataset.expr); e.dataTransfer.effectAllowed = 'copy'; });
    m.querySelector('.sm-in').addEventListener('click', e => {
      const v = e.target.closest('[data-mview]'); if (v) { ED.mview.in = v.dataset.mview; modalIn(); return; }
      const g = e.target.closest('[data-tg]'); if (g) { ED.fold = ED.fold || {}; ED.fold[g.dataset.tg] = !ED.fold[g.dataset.tg]; modalIn(); return; }
      if (e.target.closest('#inTest')) { testRoute(false); return; }
      const r = e.target.closest('[data-expr]'); if (!r) return;
      const f = ED.lastFld && document.body.contains(ED.lastFld) ? ED.lastFld : null;
      if (!f) { toast('Click in a box in the middle first, or drag the field onto it.'); return; }
      const a = f.selectionStart ?? f.value.length, b = f.selectionEnd ?? a;
      f.value = f.value.slice(0, a) + r.dataset.expr + f.value.slice(b);
      f.dispatchEvent(new Event('input', {bubbles: true})); f.dispatchEvent(new Event('change', {bubbles: true})); f.focus();
    });
    const mid = m.querySelector('.sm-mid');
    mid.addEventListener('focusin', e => { if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) ED.lastFld = e.target; });
    mid.addEventListener('dragover', e => { if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) e.target.classList.add('dropok'); });
    mid.addEventListener('dragleave', e => e.target.classList && e.target.classList.remove('dropok'));
    mid.addEventListener('drop', e => { e.target.classList && e.target.classList.remove('dropok');
      if (/^(INPUT|TEXTAREA)$/.test(e.target.tagName)) setTimeout(() => { e.target.dispatchEvent(new Event('change', {bubbles: true})); }, 0); });
    m.querySelector('.sm-out').addEventListener('click', outClick);
  }
  function modalMid() {
    const mid = document.querySelector('#smodal .sm-mid'); if (!mid) return;
    if (ED.modal === 'trigger') trigPanel(mid); else stepPanel(mid);
  }
  function modalIn() {
    const box = document.querySelector('#smodal .sm-in'); if (!box) return;
    const v = ED.mview.in;
    const srcs = ED.modal === 'trigger' ? [] : sourcesFor(ED.modal);
    const head = `<div class="smh"><b>What comes in</b><span class="sp"></span><span class="seg sm"><button type="button" data-mview="fields" aria-pressed="${v === 'fields'}">Fields</button><button type="button" data-mview="json" aria-pressed="${v === 'json'}">JSON</button></span></div>`;
    if (ED.modal === 'trigger') { box.innerHTML = '<div class="smh"><b>What comes in</b></div><p class="mut sm sm-pad">Nothing comes before the start. The data a test starts with is on the right.</p>'; return; }
    if (!ED.data) { box.innerHTML = head + '<p class="mut sm sm-pad">Loading…</p>'; return; }
    const any = srcs.some(x => x.v !== undefined);
    box.innerHTML = head + (srcs.length ? srcs.map(x => {
      const folded = (ED.fold || {})[x.base];
      return `<div class="src"><button type="button" class="srct" data-tg="${esc(x.base)}" aria-expanded="${!folded}">${esc(x.title)}</button>
        ${folded ? '' : x.v === undefined ? `<p class="mut sm sm-pad">${esc(x.none || 'No data yet.')}</p>`
          : v === 'json' ? `<pre class="sm-json">${esc(JSON.stringify(x.v, null, 2))}</pre>` : `<div class="frs">${fieldRows(flatten(x.v, x.base, [], 0, x.label), true)}</div>`}</div>`; }).join('')
      : '<p class="mut sm sm-pad">This is the first step: it gets the data the route starts with.</p>') +
      (any ? '<p class="mut sm sm-pad hint">Drag a field into a box in the middle, or click a box and then the field.</p>'
        : `<div class="sm-pad"><p class="mut sm">No data yet. Test the route once, and what each step gave back shows here.</p><button class="btn s soft" type="button" id="inTest">${svg(IC.play)}Test route</button></div>`);
  }
  function modalOut() {
    const box = document.querySelector('#smodal .sm-out'); if (!box) return;
    const d = ED.data || {steps: {}, pins: {}, log: {}};
    const v = ED.mview.out;
    if (ED.modal === 'trigger') {
      const pin = d.pins && d.pins.trigger;
      const cur = pin !== undefined ? pin : (d.vars || {});
      box.innerHTML = `<div class="smh"><b>The data a test starts with</b>${pin !== undefined ? `<span class="pinl">${svg(IC.pin)}Pinned</span>` : ''}</div>
        <p class="mut sm sm-pad">${ED.trig.kind === 'webhook' ? 'What the app that starts it sends. Write an example to test with.' : 'Values your steps read as {{vars.…}}. Optional.'}</p>
        <div class="sm-pad"><textarea class="mono sm-edit" id="trigData" rows="12" spellcheck="false">${esc(JSON.stringify(cur, null, 2))}</textarea>
        <div class="crow"><button class="btn s" type="button" data-pin="trigger">${svg(IC.pin)}Pin as test data</button>${pin !== undefined ? '<button class="btn s soft" type="button" data-unpin="trigger">Unpin</button>' : ''}</div></div>`;
      return;
    }
    const h = find(ED.modal); if (!h) return;
    const s = h.step, decides = ['condition', 'router', 'loop', 'filter', 'approval', 'wait'].includes(s.type);
    const pinned = d.pins && d.pins[s.id] !== undefined;
    const res = ED.stepRes && ED.stepRes.id === s.id ? ED.stepRes : null;
    const lg = (d.log || {})[s.id];
    const val = res ? res.output : pinned ? d.pins[s.id] : (d.steps[s.id] || {}).output;
    const has = val !== undefined && val !== null;
    const state = res ? (res.ok ? `<span class="lr ok">Tested · ${(res.ms / 1000).toFixed(1)} s</span>` : '<span class="lr bad">Did not work</span>')
      : pinned ? `<span class="pinl">${svg(IC.pin)}Pinned</span>` : lg ? `<span class="lr ${lg.status === 'error' ? 'bad' : 'ok'}">From the last run</span>` : '';
    box.innerHTML = `<div class="smh"><b>What goes out</b>${state}<span class="sp"></span>${has && !ED.editOut ? `<span class="seg sm"><button type="button" data-oview="fields" aria-pressed="${v === 'fields'}">Fields</button><button type="button" data-oview="json" aria-pressed="${v === 'json'}">JSON</button></span>` : ''}</div>
      ${ED.realAsk === s.id ? `<div class="sm-pad warnbox"><b>Testing runs this step for real.</b><span class="mut sm">A message is really sent, a row really added. Steps before it are not run - their latest data is used.</span>
        <div class="crow"><button class="btn s" type="button" id="realGo">Test now</button><button class="btn s soft" type="button" id="realNo">Not now</button></div></div>` : ''}
      ${res && !res.ok ? `<div class="sm-pad"><div class="errbox">${esc(human(res.error))}</div></div>` : ''}
      ${ED.editOut ? `<div class="sm-pad"><textarea class="mono sm-edit" id="outEdit" rows="14" spellcheck="false">${esc(JSON.stringify(has ? val : {}, null, 2))}</textarea>
        <div class="crow"><button class="btn s" type="button" data-pin="${esc(s.id)}" data-from="edit">${svg(IC.pin)}Pin this</button><button class="btn s soft" type="button" id="editNo">Cancel</button></div></div>`
      : has ? (v === 'json' ? `<pre class="sm-json">${esc(JSON.stringify(val, null, 2))}</pre>` : `<div class="frs">${fieldRows(flatten(val, `steps.${s.id}.output`), false)}</div>`)
      : `<p class="mut sm sm-pad">${decides ? 'Test it to see which way it goes with the latest data.' : 'Nothing yet. Tap Test step, or test the route.'}</p>`}
      ${decides || ED.editOut ? (decides ? '<p class="mut sm sm-pad">This step decides or waits - it has no data to pin.</p>' : '')
        : `<div class="sm-pad crow">${has && !pinned ? `<button class="btn s soft" type="button" data-pin="${esc(s.id)}">${svg(IC.pin)}Pin this output</button>` : ''}
           ${pinned ? `<button class="btn s soft" type="button" data-unpin="${esc(s.id)}">Unpin</button>` : ''}<button class="btn s soft" type="button" id="editOut">Write test data</button></div>
           ${pinned ? '<p class="mut sm sm-pad">While pinned, a test uses this data instead of running the step. A real run always runs it.</p>' : ''}`}`;
  }
  async function outClick(e) {
    const t = e.target.closest('button'); if (!t || !ED) return;
    const id = ED.modal;
    if (t.dataset.oview) { ED.mview.out = t.dataset.oview; modalOut(); return; }
    if (t.id === 'realGo') { ED.realAsk = null; ED.realOk = true; testStep(true); return; }
    if (t.id === 'realNo') { ED.realAsk = null; modalOut(); return; }
    if (t.id === 'editOut') { ED.editOut = true; modalOut(); return; }
    if (t.id === 'editNo') { ED.editOut = false; modalOut(); return; }
    if (t.dataset.pin) {
      let value;
      try {
        if (t.dataset.pin === 'trigger') value = JSON.parse($('#trigData').value || '{}');
        else if (t.dataset.from === 'edit') value = JSON.parse($('#outEdit').value || 'null');
        else { const d = ED.data || {}; value = ED.stepRes && ED.stepRes.id === id ? ED.stepRes.output : (d.steps[id] || {}).output; }
      } catch { toast('That is not valid data. Check the brackets and quotes.', true); return; }
      if (ED.dirty && !(await save())) return;
      t.disabled = true;
      try { await api('PUT', `/api/route/routes/${enc(ED.r.id)}/pins/${enc(t.dataset.pin)}`, {value}); ED.editOut = false; toast('Pinned. Tests use this data.'); await loadData(); }
      catch (err) { toast(err.message, true); t.disabled = false; }
      return;
    }
    if (t.dataset.unpin) {
      try { await api('DELETE', `/api/route/routes/${enc(ED.r.id)}/pins/${enc(t.dataset.unpin)}`); toast('Unpinned.'); await loadData(); } catch (err) { toast(err.message, true); }
    }
  }
  async function testStep(sure) {
    if (!ED || !ED.modal || ED.modal === 'trigger') return;
    const h = find(ED.modal); if (!h) return;
    const real = !['condition', 'router', 'loop', 'filter', 'approval', 'wait'].includes(h.step.type);
    if (real && !sure && !ED.realOk) { ED.realAsk = h.step.id; modalOut(); return; }
    if (ED.dirty && !(await save())) return;
    const b = $('#smTest'); if (b) { b.disabled = true; b.innerHTML = `<span class="dots"><i></i><i></i><i></i></span>Testing`; }
    let res;
    try { res = await api('POST', `/api/route/routes/${enc(ED.r.id)}/steps/${enc(h.step.id)}/test`, {use_pins: true}); }
    catch (e) { res = {ok: false, error: e.message, ms: 0}; }
    if (!ED) return;
    ED.stepRes = Object.assign({id: h.step.id}, res);
    ED.runSt = Object.assign({}, ED.runSt, {[h.step.id]: {status: res.ok ? 'ok' : 'error'}});
    if (b) { b.disabled = false; b.innerHTML = `${svg(IC.play)}Test step`; }
    await loadData(); modalOut();
  }

  // ---------------------------------------------------------------- Test route
  async function testRoute(sure) {
    if (!ED) return;
    if (!sure && !ED.testedOnce) {
      const p = $('#testAsk'); p.hidden = false; return;
    }
    $('#testAsk').hidden = true; ED.testedOnce = true;
    if (ED.dirty && !(await save())) return;
    let x; try { x = await api('POST', `/api/route/routes/${enc(ED.r.id)}/test`, {}); } catch (e) { toast(e.message, true); return; }
    ED.runId = x.run_id; ED.runSt = {}; ED.logOpen = true; ED.runStart = Date.now();
    logDraw({status: 'queued', steps_log: []}); draw();
    clearInterval(ED.runT);
    ED.runT = setInterval(async () => {
      if (!ED) return;
      let r; try { r = await api('GET', `/api/route/runs/${enc(ED.runId)}`); } catch { return; }
      ED.runSt = {}; (r.steps_log || []).forEach(l => { ED.runSt[l.id] = l; });
      logDraw(r); draw();
      if (['done', 'failed', 'incomplete', 'stopped'].includes(r.status)) { clearInterval(ED.runT); loadData(); }
    }, 1000);
  }
  function logDraw(r) {
    const L = $('#edLog'); if (!L) return;
    L.hidden = !ED.logOpen;
    const word = {done: ['ok', 'Done'], failed: ['bad', 'Failed'], incomplete: ['bad', 'Incomplete'], waiting_approval: ['warn', 'Waiting for your OK'], queued: ['v', 'Starting'], running: ['v', 'Running'], sleeping: ['v', 'Waiting'], stopped: ['', 'Stopped']}[r.status] || ['', r.status];
    const ms = r.summary && r.summary.wall_ms ? ` in ${(r.summary.wall_ms / 1000).toFixed(1)} s` : '';
    L.innerHTML = `<div class="lh"><b>Last test</b><span class="lr ${word[0]}">${esc(word[1])}${esc(ms)}</span><span class="mut sm">${(r.steps_log || []).length} steps · this test ran the real steps</span><span class="sp"></span>
      ${r.status === 'waiting_approval' ? `<button class="btn s" data-act="approve" data-run="${esc(ED.runId)}">Approve</button>` : ''}
      <a class="btn s soft" href="#/run/${enc(ED.runId)}">Open the full run</a><button class="btn s soft ib" type="button" id="logX" aria-label="Hide">${svg(IC.x)}</button></div>
      ${r.error ? `<div class="errt sm lerr">${esc(human(r.error))}</div>` : ''}
      <div class="lcards">${(r.steps_log || []).map(l => { const h = find(l.id); return `<button type="button" class="lc ${ST_CLS[l.status] || ''}" data-node-go="${esc(l.id)}">
        <span class="lt"><span class="sd ${ST_CLS[l.status] || ''}"></span>${esc(h ? titleOfStep(h.step) : nice(l.id))}</span>
        <code>${esc(l.error ? human(l.error) : S(l.output).slice(0, 90))}</code><span class="mut sm">${l.ms ? (l.ms / 1000).toFixed(1) + ' s' : ''}</span></button>`; }).join('') || '<span class="mut sm">Starting…</span>'}</div>`;
    $('#logX').addEventListener('click', () => { ED.logOpen = false; L.hidden = true; });
  }

  // ---------------------------------------------------------------- the editor page
  async function viewEditor(id, tab) {
    const r = await api('GET', `/api/route/routes/${enc(id)}`);
    if (ED && ED.r && ED.r.id !== id) stopEditor();
    shell(true); setNav('routes');
    if (tab === 'runs' || tab === 'settings') { await viewRouteTab(r, tab); return; }
    stopEditor();
    ED = {r: null, steps: [], trig: {}, pos: {}, notes: [], sel: null, hist: [], fut: [], z: 1, px: 40, py: 80, dirty: false, runSt: {}, tab: 'ask', chat: null};
    load(r);
    MAIN.innerHTML = `<div class="ed">
      ${edTop(r, 'editor')}
      <div class="edbody">
        <div class="canvas" id="canvas" tabindex="-1">
          <div class="world" id="world"></div>
          <div class="tools" role="toolbar" aria-label="Canvas">
            <button type="button" class="tb ink" id="tAdd" title="Add a step" aria-label="Add a step">${svg(IC.plus)}</button>
            <button type="button" class="tb" id="tNote" title="Add a note" aria-label="Add a note">${svg(IC.note)}</button>
            <button type="button" class="tb" id="tTidy" title="Tidy up" aria-label="Tidy up">${svg(IC.tidy)}</button></div>
          <div class="zoom"><button type="button" id="zOut" aria-label="Zoom out">−</button><span id="zl">100%</span><button type="button" id="zIn" aria-label="Zoom in">+</button><button type="button" id="zFit">Fit</button></div>
          <div class="mini" id="mini" aria-label="Map of the route"></div>
          <div class="testask" id="testAsk" hidden><b>A test runs the real steps.</b><span class="mut sm">Messages are really sent and rows really added. Steps that ask you first still wait for your tap.</span>
            <div class="crow"><button class="btn s" type="button" id="testGo">Test now</button><button class="btn s soft" type="button" id="testNo">Not now</button></div></div>
          <div class="edlog" id="edLog" hidden></div>
        </div>
        <div class="smodal" id="smodal" hidden role="dialog" aria-modal="true" aria-label="Step with its data"></div>
        <aside class="edside" aria-label="Side panel">
          <div class="ptabs" role="tablist"><button class="ptab" role="tab" data-ptab="ask" aria-selected="true">${MARK('#5B45E0')}Ask Hoola</button><button class="ptab" role="tab" data-ptab="step" aria-selected="false">Step</button></div>
          <div class="edpanel" id="edPanel"></div>
        </aside>
      </div></div>`;
    $('#edSave').addEventListener('click', save);
    $('#edUndo').addEventListener('click', undo); $('#edRedo').addEventListener('click', redo);
    $('#edTest').addEventListener('click', () => testRoute(false));
    $('#testGo').addEventListener('click', () => testRoute(true)); $('#testNo').addEventListener('click', () => { $('#testAsk').hidden = true; });
    $('#tAdd').addEventListener('click', () => { const h = ED.sel && ED.sel !== 'trigger' ? find(ED.sel) : null; if (h) addAt(h.path, h.i + 1); else addAt([], ED.steps.length); });
    $('#tNote').addEventListener('click', addNote);
    $('#smodal').addEventListener('click', e => { if (e.target.id === 'smodal') closeModal(); });
    $('#tTidy').addEventListener('click', () => { before(); ED.pos = {}; changed(true); fit(); });
    $('#zIn').addEventListener('click', () => { const c = $('#canvas'); zoomAt(1.2, c.clientWidth / 2, c.clientHeight / 2); });
    $('#zOut').addEventListener('click', () => { const c = $('#canvas'); zoomAt(1 / 1.2, c.clientWidth / 2, c.clientHeight / 2); });
    $('#zFit').addEventListener('click', fit);
    document.querySelectorAll('.ptab').forEach(b => b.addEventListener('click', () => { ED.tab = b.dataset.ptab; if (ED.tab === 'step') ED.addAt = null; panel(); }));
    canvasWire();
    window.addEventListener('keydown', edKeys); window.addEventListener('beforeunload', edLeave);
    draw(); fit(); topState(); panel(); loadData();
    if (r.steps === 1 && (r.graph[0] || {}).id === 'tell_me' && !sessionStorage.getItem(ASK_KEY)) setTimeout(() => { const a = $('#askIn'); if (a) a.focus(); }, 300);
  }
  function edTop(r, tab) {
    return `<div class="edtop">
      <a class="btn soft s ib" href="#/routes" aria-label="Back to all routes">${svg(IC.back)}</a>
      <div class="edname"><span class="mut sm">${esc(r.folder || 'Routes')} /</span><b title="${esc(nice(r.name))}">${esc(nice(r.name))}</b>${tab === 'editor' ? '<span class="chipst" id="edState">Saved</span>' : ''}</div>
      <div class="segtabs" role="tablist"><a role="tab" href="#/r/${enc(r.id)}" aria-selected="${tab === 'editor'}">Editor</a><a role="tab" href="#/r/${enc(r.id)}/runs" aria-selected="${tab === 'runs'}">Runs</a><a role="tab" href="#/r/${enc(r.id)}/settings" aria-selected="${tab === 'settings'}">Settings</a></div>
      <span class="sp"></span>
      <label class="onl">${r.enabled ? 'On' : 'Off'}${tog(r.id, r.enabled, r.name)}</label>
      ${tab === 'editor' ? `<button class="btn soft s ib" type="button" id="edUndo" aria-label="Undo" title="Undo (Ctrl Z)">${svg(IC.undo)}</button><button class="btn soft s ib" type="button" id="edRedo" aria-label="Redo" title="Redo (Ctrl Shift Z)">${svg(IC.redo)}</button>
      <button class="btn soft s" type="button" id="edSave" disabled title="Save (Ctrl S)">Save</button>
      <button class="btn s" type="button" id="edTest">${svg(IC.play)}Test route</button>` : ''}
    </div><div class="edbanner" id="edBanner" hidden></div>`;
  }
  function edKeys(e) {
    if (!ED) return;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || '');
    const mod = e.ctrlKey || e.metaKey;
    if (mod && (e.key === 's' || e.key === 'S')) { e.preventDefault(); save(); return; }
    if (typing) return;
    if (mod && (e.key === 'z' || e.key === 'Z')) { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
    if (mod && (e.key === 'y' || e.key === 'Y')) { e.preventDefault(); redo(); return; }
    if ((e.key === 'Delete' || e.key === 'Backspace') && ED.sel && ED.sel !== 'trigger') { e.preventDefault(); delStep(ED.sel); return; }
    if (e.key === 'Escape' && ED.modal) { closeModal(); return; }
    if (e.key === 'Escape') { ED.sel = null; draw(); if (ED.tab !== 'ask') { ED.tab = 'step'; panel(); } return; }
    if (e.key === 'Enter' && document.activeElement && document.activeElement.dataset.node) { select(document.activeElement.dataset.node); }
  }
  function select(id) {
    ED.sel = id; ED.tab = 'step'; ED.addAt = null; ED.replace = null;
    draw(); panel();
    const el = document.querySelector(`[data-node="${CSS.escape(id)}"]`); if (el) el.focus({preventScroll: true});
  }
  function addNote() {
    const c = $('#canvas');
    before();
    const id = 'n' + Date.now().toString(36);
    ED.notes.push({id, x: (c.clientWidth / 2 - ED.px) / ED.z - 110, y: (c.clientHeight / 3 - ED.py) / ED.z, w: 220, text: '', color: 'yellow'});
    changed(true);
    setTimeout(() => { const t = document.querySelector(`[data-ntext="${id}"]`); if (t) t.focus(); }, 30);
  }
  function canvasWire() {
    const c = $('#canvas');
    let drag = null;
    c.addEventListener('pointerdown', e => {
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      if (e.target.closest('.tools, .zoom, .mini, .edlog, .testask, textarea, .sh button, .addaf, .addn')) {
        if (e.target.closest('.mini')) { miniJump(e); }
        return;
      }
      const nd = e.target.closest('[data-node]'), nt = e.target.closest('.sticky .sh');
      if (nd) { const id = nd.dataset.node; const n = ED.L.nodes.find(x => x.id === id);
        drag = {kind: 'node', id, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y, moved: false}; }
      else if (nt) { const id = nt.parentNode.dataset.note; const n = ED.notes.find(x => x.id === id);
        drag = {kind: 'note', id, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y, moved: false}; }
      else drag = {kind: 'pan', sx: e.clientX, sy: e.clientY, ox: ED.px, oy: ED.py, moved: false};
      c.setPointerCapture(e.pointerId);
    });
    c.addEventListener('pointermove', e => {
      if (!drag) return;
      const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
      if (!drag.moved && Math.hypot(dx, dy) < 4) return;
      if (!drag.moved) { drag.moved = true; if (drag.kind !== 'pan') before(); c.classList.add(drag.kind === 'pan' ? 'panning' : 'dragging'); }
      if (drag.kind === 'pan') { ED.px = drag.ox + dx; ED.py = drag.oy + dy; view(); return; }
      const nx = Math.round((drag.ox + dx / ED.z) / 4) * 4, ny = Math.round((drag.oy + dy / ED.z) / 4) * 4;
      if (drag.kind === 'node') ED.pos[drag.id] = [nx, ny];
      else { const n = ED.notes.find(x => x.id === drag.id); if (n) { n.x = nx; n.y = ny; } }
      draw();
    });
    const end = e => {
      if (!drag) return;
      c.classList.remove('panning', 'dragging');
      const d = drag; drag = null;
      if (d.moved) { if (d.kind !== 'pan') saveLayoutSoon(); return; }
      if (d.kind === 'node') {
        // a double click: the first click redraws the canvas, so the browser's own dblclick never reaches the step
        const now = Date.now();
        if (ED.lastTap && ED.lastTap.id === d.id && now - ED.lastTap.t < 420) { ED.lastTap = null; openModal(d.id); return; }
        ED.lastTap = {id: d.id, t: now}; select(d.id);
      }
      else if (d.kind === 'pan') { if (ED.sel) { ED.sel = null; draw(); if (ED.tab === 'step') panel(); } }
    };
    c.addEventListener('pointerup', end); c.addEventListener('pointercancel', end);
    c.addEventListener('wheel', e => {
      e.preventDefault();
      const rc = c.getBoundingClientRect();
      if (e.ctrlKey || e.metaKey) zoomAt(Math.exp(-e.deltaY / 300), e.clientX - rc.left, e.clientY - rc.top);
      else { ED.px -= e.deltaX; ED.py -= e.deltaY; view(); }
    }, {passive: false});
    c.addEventListener('click', e => {
      const af = e.target.closest('[data-addafter]');
      if (af) { e.stopPropagation(); const h = find(af.dataset.addafter); if (h) addAt(h.path, h.i + 1); return; }
      const ad = e.target.closest('[data-add]');
      if (ad) { const a = ED.L.adds[+ad.dataset.add]; addAt(a.path, a.i); return; }
      const go = e.target.closest('[data-node-go]');
      if (go) { select(go.dataset.nodeGo); return; }
      const nc = e.target.closest('[data-ncolor]');
      if (nc) { const n = ED.notes.find(x => x.id === nc.closest('[data-note]').dataset.note); before(); n.color = nc.dataset.ncolor; changed(true); return; }
      const nd = e.target.closest('[data-ndel]');
      if (nd) { before(); ED.notes = ED.notes.filter(x => x.id !== nd.dataset.ndel); changed(true); }
    });
    c.addEventListener('focusin', e => { const t = e.target.closest('[data-ntext]'); if (t) { t.dataset.snap = '0'; } });
    c.addEventListener('input', e => {
      const t = e.target.closest('[data-ntext]'); if (!t) return;
      if (t.dataset.snap !== '1') { before(); t.dataset.snap = '1'; }
      const n = ED.notes.find(x => x.id === t.dataset.ntext); if (n) { n.text = t.value.slice(0, 2000); saveLayoutSoon(); topState(); }
    });
    c.addEventListener('keydown', e => { const nd = e.target.closest('[data-node]'); if (nd && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(nd.dataset.node); } });
    ED.ro = new ResizeObserver(() => mini()); ED.ro.observe(c);
  }
  function miniJump(e) {
    const m = $('#mini'), c = $('#canvas'); if (!ED.miniK) return;
    const rc = m.getBoundingClientRect(), {k, b, pad} = ED.miniK;
    const wx = (e.clientX - rc.left - pad) / k + b.x0, wy = (e.clientY - rc.top - pad) / k + b.y0;
    ED.px = c.clientWidth / 2 - wx * ED.z; ED.py = c.clientHeight / 2 - wy * ED.z; view();
  }

  async function viewRouteTab(r, tab) {
    stopEditor();
    let body = '';
    if (tab === 'runs') {
      const runs = await api('GET', `/api/route/runs?workflow_id=${enc(r.id)}&limit=40`);
      body = `<section class="card flat">${runRows(runs.runs, true, 'No runs yet. Test the route in the editor, or switch it on.')}</section>`;
    } else {
      const sp = r.trigger_spec || {}, st = r.settings || {};
      body = `<div class="setgrid"><section class="card"><div class="hd"><h2>How it runs</h2></div>
          <div class="kv"><span class="k">Runs when</span><span>${esc(r.when)}</span></div>
          ${sp.timezone || st.timezone ? `<div class="kv"><span class="k">Time zone</span><span>${esc(sp.timezone || st.timezone)}</span></div>` : ''}
          ${sp.quiet ? `<div class="kv"><span class="k">Quiet hours</span><span>${esc(sp.quiet.from)}–${esc(sp.quiet.to)}</span></div>` : ''}
          ${sp.skip_holidays ? `<div class="kv"><span class="k">Skips holidays of</span><span>${esc(sp.skip_holidays)}</span></div>` : ''}
          ${r.next_due_at ? `<div class="kv"><span class="k">Next run</span><span>${esc(at(r.next_due_at))}</span></div>` : ''}
          <div class="kv"><span class="k">Switch off after</span><span>${st.stop_after_errors ? esc(st.stop_after_errors) + ' failed runs in a row' : 'Never (not set)'}</span></div>
          ${st.error_route ? `<div class="kv"><span class="k">Error route</span><span>${esc(nice(st.error_route))}</span></div>` : ''}
          ${st.runs_per_day ? `<div class="kv"><span class="k">Runs per day, at most</span><span>${esc(st.runs_per_day)}</span></div>` : ''}
          ${r.trigger === 'webhook' ? `<div class="kv"><span class="k">Address that starts it</span><span class="v" id="addrBox"><span class="mut">Kept secret. Make a new one to see it.</span><br><button class="btn soft s" id="addrNew" type="button">Make a new address</button></span></div>` : ''}
          <div class="kv"><span class="k">Money and sending</span><span>Always wait for your tap</span></div>
          <p class="mut sm">To change these, ask Hoola in the editor. More settings come to this page next.</p></section>
        <section class="card danger"><div class="hd"><h2>Delete this route</h2></div>
          <p class="mut sm" id="delWords">Its steps and its run history go. This cannot be undone. A route with a run still going cannot be deleted.</p>
          <div class="crow"><button class="btn soft bad s" id="delAsk" type="button">Delete route</button>
            <span id="delSure" hidden><span class="sm">Delete <b>${esc(nice(r.name))}</b> for good?</span> <button class="btn s bad solid" id="delGo" type="button">Yes, delete</button> <button class="btn soft s" id="delNo" type="button">Keep it</button></span></div></section></div>`;
    }
    MAIN.innerHTML = `<div class="ed tabbed">${edTop(r, tab)}<div class="edpage">${body}</div></div>`;
    const an = $('#addrNew');
    if (an) an.addEventListener('click', async () => {
      if (an.dataset.sure !== '1') { an.dataset.sure = '1'; an.textContent = 'The old address stops working. Make a new one?'; return; }
      an.disabled = true;
      try {
        const a = await api('POST', `/api/route/routes/${enc(r.id)}/address`);
        const url = /^https?:/.test(a.url) ? a.url : location.origin + a.url;
        $('#addrBox').innerHTML = `<code class="addr">${esc(url)}</code><br><span class="mut sm">${esc(a.note)}</span><br><button class="btn soft s" type="button" id="addrCopy">Copy</button>`;
        $('#addrCopy').addEventListener('click', () => navigator.clipboard.writeText(url).then(() => toast('Copied.'), () => toast('Copy it by hand.', true)));
      } catch (err) { toast(err.message, true); an.disabled = false; }
    });
    const da = $('#delAsk');
    if (da) {
      da.addEventListener('click', () => { $('#delSure').hidden = false; da.hidden = true; });
      $('#delNo').addEventListener('click', () => { $('#delSure').hidden = true; da.hidden = false; });
      $('#delGo').addEventListener('click', async () => {
        $('#delGo').disabled = true;
        try { await api('DELETE', `/api/route/routes/${enc(r.id)}`, {confirm: r.name}); toast('Deleted.'); location.hash = '#/routes'; }
        catch (err) { toast(err.message, true); $('#delGo').disabled = false; }
      });
    }
  }

  // ---------------------------------------------------------------- shared clicks: switches + run actions
  document.addEventListener('click', async e => {
    const sw = e.target.closest('[data-switch]');
    if (sw) {
      const on = sw.getAttribute('aria-checked') !== 'true';
      sw.disabled = true;
      try {
        await api('POST', `/api/route/routes/${enc(sw.dataset.switch)}/switch`, {on});
        toast(`${sw.dataset.name || 'The route'} is ${on ? 'on' : 'off'}.`);
        if (!sw.classList.contains('tog')) { route(); return; }      // "Switch back on" in Needs you: redraw the list
        sw.setAttribute('aria-checked', String(on));
        sw.setAttribute('aria-label', `${on ? 'Switch off' : 'Switch on'} ${sw.dataset.name || ''}`);
        const l = sw.closest('.onl'); if (l && l.firstChild && l.firstChild.nodeType === 3) l.firstChild.textContent = on ? 'On' : 'Off';
        if (ED && ED.r) ED.r.enabled = on;
      } catch (err) { toast(err.message, true); }
      sw.disabled = false; return;
    }
    const act = e.target.closest('[data-act]');
    if (act) {
      act.disabled = true;
      try { await api('POST', `/api/route/runs/${enc(act.dataset.run)}/${act.dataset.act}`);
        toast(act.dataset.act === 'approve' ? 'Approved. The run carries on.' : act.dataset.act === 'stop' ? 'Stopped.' : 'Retrying from where it stopped.');
        if (!ED) route(); }
      catch (err) { toast(err.message, true); act.disabled = false; }
    }
  });
  document.addEventListener('keydown', e => {
    if (ED) return;
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); location.hash = '#/'; setTimeout(() => { const t = $('#askText'); if (t) t.focus(); }, 60); }
  });
  $('#newRoute').addEventListener('click', () => setTimeout(() => { const t = $('#askText'); if (t) t.focus(); }, 60));

  let LEAVE_OK = '';
  async function route() {
    const h = location.hash.replace(/^#\/?/, '');
    const [a, b, c] = h.split('/');
    if (ED && ED.dirty && !(a === 'r' && decodeURIComponent(b || '') === ED.r.id && !c) && LEAVE_OK !== h) {
      // unsaved canvas changes: ask in the page before leaving
      banner('You have changes that are not saved.', false);
      const bn = $('#edBanner');
      bn.insertAdjacentHTML('beforeend', `<button class="btn s" type="button" id="lvSave">Save and go</button><button class="btn s soft bad" type="button" id="lvDrop">Leave without saving</button>`);
      const target = location.hash; history.replaceState(null, '', '#/r/' + enc(ED.r.id));
      $('#lvSave').addEventListener('click', async () => { if (await save()) { LEAVE_OK = target.replace(/^#\/?/, ''); location.hash = target; } });
      $('#lvDrop').addEventListener('click', () => { ED.dirty = false; LEAVE_OK = target.replace(/^#\/?/, ''); location.hash = target; });
      return;
    }
    LEAVE_OK = '';
    try {
      if (a === 'routes') await viewRoutes(b ? decodeURIComponent(b) : '');
      else if (a === 'r' && b) await viewEditor(decodeURIComponent(b), c || '');
      else if (a === 'needs') await viewNeeds();
      else if (a === 'runs') await viewRuns(b || '');
      else if (a === 'run' && b) await viewRun(decodeURIComponent(b));
      else if (a === 'templates') await viewTemplates();
      else await viewHome();
    } catch (err) { shell(false); MAIN.innerHTML = `<div class="errbox">${esc(err.message)}</div>`; }
    needCount();
  }
  window.addEventListener('hashchange', route);
  route();
})();
