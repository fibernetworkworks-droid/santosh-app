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
    subroute: '<rect x="3" y="4" width="8" height="7" rx="1.5"/><rect x="13" y="13" width="8" height="7" rx="1.5"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/>',
    stop: '<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
    respond: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 6 6v4"/>',
    ai: '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/><path d="M19 15l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/>',
    tform: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    tchat: '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
    terr: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/>',
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
    subroute: 'flow', stop: 'flow', ai: 'ai', set: 'data', code: 'data', http: 'core', respond: 'core'};
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
  const firstTile = r => (r.apps && r.apps[0]) ? appTile(r.apps[0]) : `<span class="ap k-core">${svg(TKIC(r.trigger))}</span>`;
  const LASTW = {done: ['ok', 'Done'], failed: ['bad', 'Failed'], incomplete: ['bad', 'Incomplete'], waiting_approval: ['warn', 'Waiting for you'],
    running: ['v', 'Running'], queued: ['v', 'Queued'], sleeping: ['v', 'Waiting'], stopped: ['', 'Stopped']};
  // tables become cards on a phone: every cell carries its own label (data-l), the CSS shows it there
  function routeRows(routes, empty) {
    if (!routes.length) return `<div class="empty">${empty || 'No routes yet. Describe one above, or start from a template.'}</div>`;
    return `<div class="tw"><table class="rt"><thead><tr><th>Route</th><th>Runs when</th><th>Last run</th><th class="nw">Last 7 days</th><th class="c-tog">On</th></tr></thead><tbody>${
      routes.map(r => { const lr = r.last_run ? (LASTW[r.last_run.status] || ['', r.last_run.status]) : null;
        return `<tr>
        <td class="c-name"><div class="rname">${firstTile(r)}<div><a class="rn" href="#/r/${enc(r.id)}">${esc(nice(r.name))}</a><div class="mut sm">${esc([r.folder, {manual: 'by hand', schedule: 'on a schedule', webhook: 'when data arrives', event: 'on an app event', form: 'from a form', chat: 'from a chat', error: 'when a route fails', route: 'from another route', tool: 'as a tool'}[r.trigger]].filter(Boolean).join(' · '))}</div>${(r.tags || []).length ? `<div class="rtags">${r.tags.map(t => `<span class="rtag">${esc(t)}</span>`).join('')}</div>` : ''}</div></div></td>
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
    MAIN.innerHTML = `<div class="top"><h1>All routes</h1><span class="sp"></span><a class="btn soft" href="#/import">Bring in from n8n</a><label class="btn soft" for="impFile">Bring in a file<input type="file" id="impFile" accept=".json,application/json" hidden></label><button class="btn" id="newR">${svg(IC.plus)}New route</button></div>
      <div class="filt"><label class="srch">${svg(IC.search)}<input type="search" id="rq" placeholder="Find a route" aria-label="Find a route"></label>
      <select id="rsort" aria-label="Sort"><option value="changed">Last changed</option><option value="name">Name</option><option value="runs">Most runs</option></select>
      ${folders.length ? `<div class="chips left" id="fchips"><button class="chip" aria-pressed="${!folderPick}" data-f="">All</button>${folders.map(f => `<button class="chip" aria-pressed="${f === folderPick}" data-f="${esc(f)}">${esc(f)}</button>`).join('')}</div>` : ''}</div>
      <section class="card flat" id="rtable"></section>`;
    let folder = folderPick || '';
    const draw = () => { const q = $('#rq').value.trim().toLowerCase(), so = $('#rsort').value;
      const rs = list.routes.filter(r => (!folder || r.folder === folder) && (!q || (nice(r.name) + ' ' + r.description + ' ' + (r.tags || []).join(' ')).toLowerCase().includes(q)));
      if (so === 'name') rs.sort((a, b) => a.name.localeCompare(b.name)); else if (so === 'runs') rs.sort((a, b) => b.runs_30d - a.runs_30d);
      $('#rtable').innerHTML = routeRows(rs, list.routes.length ? 'No route matches.' : ''); };
    draw();
    $('#rq').addEventListener('input', draw); $('#rsort').addEventListener('change', draw);
    const fc = $('#fchips');
    if (fc) fc.addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (!b) return;
      fc.querySelectorAll('[data-f]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); folder = b.dataset.f; draw(); });
    $('#newR').addEventListener('click', () => newRoute('New route', '', folder).catch(err => toast(err.message, true)));
    $('#impFile').addEventListener('change', async e => {     // v0.999.246 a route file: the engine's own checks, it lands off
      const f = e.target.files[0]; if (!f) return;
      try { const dsl = JSON.parse(await f.text()); const out = await api('POST', '/api/route/import', {dsl});
        toast('Brought in. It is off until you switch it on.'); location.hash = '#/r/' + enc(out.workflow_id); }
      catch (err) { toast(err.message || 'That is not a route file', true); }
      e.target.value = '';
    });
  }
  async function viewNeeds() {
    shell(false); setNav('needs');
    const sum = await api('GET', '/api/route/summary');
    MAIN.innerHTML = `<div class="top"><h1>Needs you</h1></div><p class="lead">Approvals your routes are waiting for, and runs that did not finish. Nothing big runs without your yes.</p>${needsList(sum.needs_you)}`;
  }

  // why a run is waiting, in words (v0.999.239 R4: long waits, a call to its link, another route)
  function pauseWords(x) {
    if (x.status !== 'sleeping' && x.status !== 'queued') return '';
    const t = x.next_wake_at ? at(x.next_wake_at) : '';
    return {retry: t && 'Trying again at ' + t, sleeping: t && 'Goes on at ' + t,
      waiting_call: 'Waiting for a call to its resume link' + (t ? ' (until ' + t + ')' : ''),
      waiting_subroute: 'Waiting for another route to finish'}[x.pause_reason] || '';
  }
  function runRows(runs, inRoute, empty) {
    if (!runs.length) return `<div class="empty">${empty || 'No runs yet.'}</div>`;
    const note = x => pauseWords(x) || human(x.error || '');
    return `<div class="tw"><table class="rt runs"><thead><tr><th>Status</th>${inRoute ? '<th>Run</th>' : '<th>Route</th>'}<th>Steps done</th><th>Started</th><th>Note</th></tr></thead><tbody>${
      runs.map(x => `<tr><td class="c-on">${runPill(x.status)}</td>
        <td class="c-name"><a class="rn" href="#/run/${enc(x.id)}">${inRoute ? 'Open this run' : esc(nice(x.route))}</a></td>
        <td data-l="Steps done" class="num">${fmtN(x.steps_done)}</td><td data-l="Started" class="nw">${esc(when(x.at))}</td>
        <td data-l="Note" class="mut sm${note(x) ? '' : ' blank'}">${esc(note(x))}</td></tr>`).join('')}</tbody></table></div>`;
  }
  async function viewRuns(filter, q) {
    shell(false); setNav('runs');
    q = S(q || '').trim();
    const qs = filter ? `&status=${enc(filter)}` : '';
    const runs = await api('GET', `/api/route/runs?limit=60${qs}${q ? '&q=' + enc(q) : ''}`);
    const F = [['', 'All'], ['waiting_approval', 'Waiting for you'], ['incomplete', 'Incomplete'], ['failed', 'Failed'], ['done', 'Done']];
    MAIN.innerHTML = `<div class="top"><h1>Runs</h1></div>
      <form class="filt" id="runFind" role="search"><label class="srch">${svg(IC.search)}<input type="search" id="runQ" value="${esc(q)}" placeholder="Find runs by a value - an order number, an email, an error word" aria-label="Find runs by a value"></label>
        <button class="btn soft s" type="submit">Find</button>${q ? '<a class="btn soft s" href="#/runs">Clear</a>' : ''}</form>
      ${q ? '' : `<div class="chips left">${F.map(([k, n]) => `<a class="chip" aria-pressed="${(filter || '') === k}" href="#/runs${k ? '/' + k : ''}">${esc(n)}</a>`).join('')}</div>`}
      <section class="card flat" id="runList">${q ? foundRows(runs.runs, q) : runRows(runs.runs, false, filter ? 'No runs in this list.' : 'No runs yet. A route runs when its time comes, when data arrives, or when you test it.')}</section>`;
    $('#runFind').addEventListener('submit', e => { e.preventDefault(); const v = $('#runQ').value.trim();
      if (v.length === 1) { toast('Type at least 2 characters.', true); return; }
      location.hash = v ? '#/runs/find/' + enc(v) : '#/runs'; });
  }
  // v0.999.248 R8: runs found by a value, with where in the run it is
  function foundRows(runs, q) {
    if (!runs.length) return `<div class="empty">No kept run holds "${esc(q)}". Runs are kept as long as each route's Settings say.</div>`;
    return `<div class="tw"><table class="rt runs"><thead><tr><th>Status</th><th>Route</th><th>Started</th><th>Found in</th><th>Around it</th></tr></thead><tbody>${
      runs.map(x => `<tr><td class="c-on">${runPill(x.status)}</td>
        <td class="c-name"><a class="rn" href="#/run/${enc(x.id)}">${esc(nice(x.route))}</a></td>
        <td data-l="Started" class="nw">${esc(when(x.at))}</td><td data-l="Found in" class="sm">${esc(x.found_in)}</td>
        <td data-l="Around it" class="mut sm mono found">${esc(x.match)}</td></tr>`).join('')}</tbody></table></div>`;
  }
  const pretty = v => { try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return S(v); } };
  // v0.999.253: steps inside a branch or loop are logged just before their parent step - show them under it
  function nestLog(list) {
    const out = []; let wait = [];
    (list || []).forEach(l => { if (l && l.in !== undefined) wait.push(l); else { out.push(l); out.push(...wait); wait = []; } });
    return out.concat(wait);
  }
  async function viewRun(id) {
    shell(false); setNav('runs');
    const x = await api('GET', `/api/route/runs/${enc(id)}`);
    const acts = [];
    if (x.status === 'waiting_approval') acts.push('<button class="btn" data-act="approve" data-run="' + esc(x.id) + '">Approve</button>');
    if (['queued', 'running', 'sleeping', 'waiting_approval'].includes(x.status)) acts.push('<button class="btn soft bad" data-act="stop" data-run="' + esc(x.id) + '">Stop the run</button>');
    if (['failed', 'stopped', 'incomplete'].includes(x.status)) acts.push('<button class="btn" data-act="retry" data-run="' + esc(x.id) + '">Retry from where it stopped</button>');
    // v0.999.248 R8: a new run with the same start data, and this run's data in the editor
    if (!['queued', 'running'].includes(x.status)) acts.push('<button class="btn soft" type="button" id="runAgain">Run again with the same data</button>');
    acts.push(`<a class="btn soft" id="runDebug" href="#/r/${enc(x.route_id)}/debug/${enc(x.id)}">Debug in the editor</a>`);
    acts.push(`<a class="btn soft" href="#/r/${enc(x.route_id)}">Open the route</a>`);
    const sm = x.summary || {};
    MAIN.innerHTML = `
      <div class="rhead"><a class="btn soft s ib" href="#/runs" aria-label="Back to runs">${svg(IC.back)}</a>
        <div class="rh-t"><h1 class="rtitle">${esc(nice(x.route))}</h1>
          <div class="rh-m">${runPill(x.status)}<span class="mut sm">Started ${esc(at(x.at))}</span></div></div>
        <div class="rh-a">${acts.join('')}</div></div>
      ${x.error ? `<div class="errbox"><b>What happened.</b> ${esc(human(x.error))}${x.pause_reason === 'retry' && x.next_wake_at ? `<br>Hoola will try again at ${esc(at(x.next_wake_at))}.` : ''}</div>` : ''}
      ${!x.error && pauseWords(x) ? `<div class="okbox">${esc(pauseWords(x))}.</div>` : ''}
      ${x.start && Object.keys(x.start).length ? `<section class="card"><details><summary><b>What it started with</b></summary><pre>${esc(JSON.stringify(x.start, null, 2))}</pre></details></section>` : ''}
      <section class="card"><div class="hd"><h2>Step by step</h2><span class="sp"></span>${sm.wall_ms ? `<span class="mut sm">${(sm.wall_ms / 1000).toFixed(1)} s${sm.cost && sm.cost.calls ? ` · ${sm.cost.calls} AI calls` : ''}</span>` : ''}</div>
        <div class="log">${nestLog(x.steps_log).map(l => {
          const st = {ok: 'done', error: 'failed', approved: 'done', retry: 'queued', skipped: 'stopped', filtered: 'stopped', ignored: 'done', resumed: 'done'}[l.status] || l.status;
          const word = {approved: 'You approved', retry: 'Tried again', skipped: 'Skipped', filtered: 'Did not pass', ignored: 'Failed, went on', resumed: 'Failed, used a value'}[l.status];
          const inner = l.in !== undefined;
          return `<div class="lrow${inner ? ' inner' : ''}"><span class="lp">${word ? `<span class="pill ${l.status === 'approved' ? 'ok' : 'v'}"><span class="dot"></span>${esc(word)}</span>` : runPill(st)}</span>
          <div class="w"><b>${esc(l.id === '...' ? '' : nice(l.id))}</b> <span class="mut sm">${l.id === '...' ? esc(S(l.output)) : esc(l.type)}${inner && l.in && l.in !== '...' ? ' · in ' + esc(l.in) : ''}${l.at && l.id !== '...' ? ' · ' + esc(l.at) : ''}${l.ms ? ' · ' + l.ms + ' ms' : ''}</span>
          ${l.error ? `<div class="sm errt">${esc(human(l.error))}</div>` : ''}${l.id === '...' ? '' : inner ? (l.output ? `<details><summary class="sm">What it gave back</summary><pre>${esc(pretty(l.output))}</pre></details>` : '') : (x.outputs && x.outputs[l.id] !== undefined) || l.output ? `<details><summary class="sm">What it gave back${(x.pinned || []).includes(l.id) ? ' (pinned test data)' : ''}</summary><pre>${esc(x.outputs && x.outputs[l.id] !== undefined ? JSON.stringify(x.outputs[l.id], null, 2) : pretty(l.output))}</pre></details>` : ''}</div></div>`; }).join('') || '<div class="empty">No step has run yet.</div>'}</div></section>`;
    const ra = $('#runAgain');
    if (ra) ra.addEventListener('click', async () => { ra.disabled = true;
      try { const o = await api('POST', `/api/route/runs/${enc(x.id)}/rerun`); toast('Running again with the same data.'); location.hash = '#/run/' + enc(o.run_id); }
      catch (err) { toast(err.message, true); ra.disabled = false; } });
  }
  // ---------------------------------------------------------------- v0.999.248 R8: insights
  async function viewInsights(days) {
    shell(false); setNav('insights');
    days = ['1', '7', '30', '90'].includes(S(days)) ? S(days) : '7';
    const tz = TZ || 'UTC';
    const x = await api('GET', `/api/route/insights?days=${days}&tz=${enc(tz)}`);
    const T = x.totals, D = [['1', 'Today'], ['7', '7 days'], ['30', '30 days'], ['90', '90 days']];
    const dur = s => s === null || s === undefined ? '—' : s < 60 ? s.toFixed(1) + ' s' : (s / 60).toFixed(1) + ' min';
    const saved = m => !m ? '—' : m < 120 ? Math.round(m) + ' min' : (m / 60).toFixed(1) + ' h';
    const trend = (now, was, lowerBetter) => { if (!was && !now) return ''; const d = now - was; if (!d) return '<span class="mut sm">same as before</span>';
      const good = lowerBetter ? d < 0 : d > 0; return `<span class="sm ${good ? 'okt' : 'errt'}">${d > 0 ? '+' : ''}${lowerBetter ? d.toFixed(1) + ' points' : fmtN(d)} vs the ${days === '1' ? 'day' : days + ' days'} before</span>`; };
    const top = Math.max(1, ...x.series.map(p => p.done + p.failed));
    MAIN.innerHTML = `<div class="top"><h1>Insights</h1><span class="sp"></span>
        <div class="chips">${D.map(([k, n]) => `<a class="chip" aria-pressed="${k === days}" href="#/insights/${k}">${esc(n)}</a>`).join('')}</div></div>
      <div class="stats">
        <div class="stat"><span class="k">Runs</span><b>${fmtN(T.runs)}</b>${trend(T.runs, T.before.runs, false)}</div>
        <div class="stat"><span class="k">Failed</span><b>${fmtN(T.failed)}<span class="sm mut"> · ${T.failure_rate}%</span></b>${trend(T.failure_rate, T.before.failure_rate, true)}</div>
        <div class="stat"><span class="k">Average working time</span><b>${dur(T.avg_s)}</b><span class="mut sm">Waits are not counted</span></div>
        <div class="stat"><span class="k">Time saved</span><b>${saved(T.minutes_saved)}</b><span class="mut sm">${T.minutes_saved ? 'From the minutes each route saves' : 'Set the minutes a run saves in a route\'s Settings'}</span></div></div>
      <section class="card"><div class="hd"><h2>Runs by day</h2><span class="sp"></span><span class="mut sm">${esc(x.tz)}</span></div>
        <div class="bars" role="img" aria-label="Runs by day: done and failed">${x.series.map(p => `<div class="bar" title="${esc(p.day)}: ${p.done} done, ${p.failed} failed">
          <span class="bf" style="height:${(p.failed / top) * 100}%"></span><span class="bd" style="height:${(p.done / top) * 100}%"></span>
          ${x.series.length <= 31 ? `<span class="bl">${esc(p.day.slice(8))}</span>` : ''}</div>`).join('')}</div>
        <div class="legend sm"><span><i class="bd"></i>Done</span><span><i class="bf"></i>Failed</span></div></section>
      <section class="card flat"><div class="hd"><h2>Each route</h2></div>${x.routes.length ? `<div class="tw"><table class="rt"><thead><tr><th>Route</th><th>Runs</th><th>Failed</th><th>Average time</th><th>Time saved</th></tr></thead><tbody>${
        x.routes.map(r => `<tr><td class="c-name"><a class="rn" href="#/r/${enc(r.id)}/runs">${esc(nice(r.name))}</a>${r.enabled ? '' : ' <span class="mut sm">(off)</span>'}</td>
          <td data-l="Runs" class="num">${fmtN(r.runs)}</td><td data-l="Failed" class="num">${fmtN(r.failed)} <span class="mut sm">${r.failure_rate}%</span></td>
          <td data-l="Average time" class="num">${dur(r.avg_s)}</td>
          <td data-l="Time saved" class="num">${r.minutes_per_run ? saved(r.minutes_saved) : `<a class="sm" href="#/r/${enc(r.id)}/settings">Set it</a>`}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="empty">No runs in this time yet.</div>'}</section>
      <div class="setgrid">
        <section class="card"><div class="hd"><h2>Slowest steps</h2></div>${x.slow_steps.length ? x.slow_steps.map(st => `<div class="kv"><span class="k"><a href="#/r/${enc(st.route_id)}">${esc(nice(st.route))}</a> › ${esc(nice(st.step))}</span><span>${(st.avg_ms / 1000).toFixed(1)} s <span class="mut sm">(${fmtN(st.runs)} runs)</span></span></div>`).join('') : '<p class="mut sm">Nothing yet.</p>'}</section>
        <section class="card"><div class="hd"><h2>Steps that fail most</h2></div>${x.failing_steps.length ? x.failing_steps.map(st => `<div class="kv"><span class="k"><a href="#/r/${enc(st.route_id)}">${esc(nice(st.route))}</a> › ${esc(nice(st.step))}</span><span>${fmtN(st.fails)} of ${fmtN(st.runs)}</span></div>`).join('') : '<p class="mut sm">No step failed in this time.</p>'}</section></div>
      <p class="mut sm">${esc(x.note)}</p>`;
  }

  // ---------------------------------------------------------------- v0.999.248 R8: bring in an n8n workflow
  async function viewImport() {
    shell(false); setNav('routes');
    MAIN.innerHTML = `<div class="rhead"><a class="btn soft s ib" href="#/routes" aria-label="Back to all routes">${svg(IC.back)}</a>
        <div class="rh-t"><h1 class="rtitle">Bring in from n8n</h1><div class="rh-m mut sm">In n8n: open the workflow, then Download (or select all nodes and copy). Paste it here.</div></div></div>
      <section class="card"><form id="n8nForm" class="pform">
        <div class="fld"><label for="n8nText">The n8n workflow (its JSON)</label><div class="fc"><textarea id="n8nText" rows="10" class="mono" placeholder='{"name": "...", "nodes": [...], "connections": {...}}'></textarea></div>
          <span class="fh">Or pick the file: <input type="file" id="n8nFile" accept=".json,application/json"></span></div>
        <div class="crow"><button class="btn s" type="submit">Look at it first</button><span class="mut sm">Nothing is saved yet.</span></div></form></section>
      <div id="n8nOut"></div>`;
    let raw = '';
    $('#n8nFile').addEventListener('change', async e => { const f = e.target.files[0]; if (f) { $('#n8nText').value = await f.text(); } });
    const list = (rows, cls) => rows.map(r => `<li class="${cls}"><b>${esc(r.node)}</b>${r.as ? ' → ' + esc(r.as) : ''}${r.why ? ' — ' + esc(r.why) : ''}</li>`).join('');
    $('#n8nForm').addEventListener('submit', async e => {
      e.preventDefault(); raw = $('#n8nText').value.trim();
      if (!raw) { toast('Paste the workflow first.', true); return; }
      let p; try { p = await api('POST', '/api/route/import/n8n', {workflow: raw}); } catch (err) { toast(err.message, true); return; }
      const R = p.report, c = p.counts;
      $('#n8nOut').innerHTML = `<section class="card"><div class="hd"><h2>What it becomes</h2></div>
          <div class="stats"><div class="stat"><span class="k">Came in</span><b>${c.converted}</b></div><div class="stat"><span class="k">To check</span><b>${c.check}</b></div>
            <div class="stat"><span class="k">To redo in Hoola</span><b>${c.placeholders}</b></div><div class="stat"><span class="k">Left out</span><b>${c.skipped}</b></div></div>
          <p class="sm">It starts: <b>${esc(((TKINDS.find(k => k[0] === p.trigger) || [])[1]) || p.trigger)}</b> · ${fmtN(p.steps.length)} step${p.steps.length === 1 ? '' : 's'} at the top level.</p>
          ${c.placeholders ? `<div class="psub">To redo in Hoola</div><p class="mut sm">Each one is a step that stops the run with its reason, so nothing half-done runs. Replace it in the editor.</p><ul class="rep">${list(R.placeholders, 'ph')}</ul>` : ''}
          ${c.check ? `<div class="psub">To check</div><ul class="rep">${list(R.check, 'ck')}</ul>` : ''}
          ${c.skipped ? `<div class="psub">Left out</div><ul class="rep">${list(R.skipped, 'sk')}</ul>` : ''}
          ${R.notes.length ? `<div class="psub">Good to know</div><ul class="rep">${R.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}
          <details><summary class="sm">Came in as</summary><ul class="rep">${list(R.converted, 'ok')}</ul></details>
          <form id="n8nSave" class="pform"><div class="two">${field('Name of the new route', p.name, {k: 'n8nname', ref: false})}</div>
            <div class="crow"><button class="btn s" type="submit">Bring it in</button><span class="mut sm">It stays off until you have read it and switch it on.</span></div></form></section>`;
      $('#n8nSave').addEventListener('submit', async ev => {
        ev.preventDefault();
        const nm = (MAIN.querySelector('[data-k="n8nname"]') || {}).value || p.name;
        try { const o = await api('POST', '/api/route/import/n8n', {workflow: raw, save: true, new_name: nm.trim().toLowerCase().replace(/\s+/g, '_')});
          toast('Brought in. It is off until you switch it on.'); location.hash = '#/r/' + enc(o.workflow_id); }
        catch (err) { toast(err.message, true); }
      });
    });
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
    date: 'Date and time', text: 'Text and formats', file: 'Make or read a file', crypto: 'Hash and IDs', merge: 'Merge two lists'};
  const OPIC = {sort: '<path d="M7 4v16M4 17l3 3 3-3M14 6h6M14 12h4M14 18h2"/>', limit: '<path d="M4 6h16M4 12h10M4 18h4"/>',
    dedupe: '<rect x="4" y="4" width="10" height="10" rx="2"/><rect x="10" y="10" width="10" height="10" rx="2"/>',
    aggregate: '<path d="M18 5H6l6 7-6 7h12"/>', split: '<path d="M12 4v6M12 10l-6 10M12 10l6 10"/>',
    compare: '<path d="M8 4v16M16 4v16M4 8h4M16 16h4"/>', keep_fields: '<path d="M4 6h16M4 12h16M4 18h9"/><path d="m15 17 2 2 4-4"/>',
    rename: '<path d="M4 20h4L19 9l-4-4L4 16z"/>', fields: '<path d="M4 7h16M4 12h10M4 17h7"/>',
    date: '<path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2z"/>', text: '<path d="M4 7V5h16v2M12 5v14M9 19h6"/>',
    merge: '<path d="M6 4v5a5 5 0 0 0 5 5h2M18 4v5a5 5 0 0 1-5 5M12 14v6"/>',
    file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>', crypto: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'};
  const KIND = {data: 'Data', tool: 'Uses a tool', http: 'Web request', code: 'Code', wait: 'Wait', notify: 'Tell me', approval: 'Ask me first',
    set: 'Set a value', filter: 'Filter', condition: 'If / else', loop: 'Repeat for each', router: 'Switch',
    subroute: 'Run another route', stop: 'Stop the run', respond: 'Answer the caller', ai: 'AI'};
  // v0.999.243 ROUTE R6: the AI steps (engine type "ai", told apart by op)
  const AIW = {write: 'Ask AI', summarise: 'Summarise', classify: 'Sort into categories', extract: 'Pull out fields',
    sentiment: 'How it feels', answer: 'Answer from my files', agent: 'AI agent'};
  const YN = [['', 'No'], ['true', 'Yes']];
  const QUAL = ['quality', 'Model', 'sel', [['fast', 'Fast (the everyday model)'], ['best', 'Best (the strongest model)']]];
  const INSTR = ['instructions', 'Extra instructions (optional)', 'area', 'Like: answer in Spanish, keep it formal'];
  const AIF = {
    write: [['prompt', 'Ask', 'area', 'Use values from earlier steps, like {{vars.form.message}}'], INSTR, QUAL],
    summarise: [['text', 'Text to summarise', 'area'], ['length', 'Length', 'sel', [['short', 'Short (1-2 sentences)'], ['medium', 'A paragraph'], ['long', 'Longer'], ['points', 'As points']]],
      ['language', 'In this language (optional)', 'plain', 'Empty = the text\'s own language'], INSTR, QUAL],
    classify: [['text', 'Text', 'area'], ['categories', 'Categories (with commas)', 'plain', 'Like: question, complaint, order, spam'],
      ['multi', 'More than one may fit', 'sel', YN], INSTR, QUAL],
    extract: [['text', 'Text', 'area'], ['fields', 'Fields to pull out (name: what it is)', 'obj'], INSTR, QUAL],
    sentiment: [['text', 'Text', 'area'], INSTR, QUAL],
    answer: [['question', 'Question', 'area'], ['files', 'From these files (file ids, with commas)', 'text', 'Like {{steps.mail.output.attachments[0].file_id}}'],
      ['text', 'Or from this text', 'area'], ['knowledge', 'Also from my Hoola Knowledge', 'sel', YN], INSTR, QUAL],
    agent: [['prompt', 'The task', 'area', 'What it should do, with values from earlier steps'], ['tools', 'Tools it may use (names, with commas)', 'plain', 'Like sheet_read, email_check - only these'],
      ['max_steps', 'At most this many steps', 'num'], ['memory', 'Remember earlier runs', 'sel', [['none', 'No'], ['on', 'Yes']]],
      ['memory_key', 'Remember per (optional)', 'text', 'Like {{vars.session}} - one memory for each chat; empty = one for the route'], INSTR, QUAL],
  };
  const AISHOW = {agent: {memory_key: s => s.memory === 'on'}};
  const DO = {'': 'Stop the run and show me why', break: 'Try again later, then keep it in Incomplete runs', resume: 'Use a value I give and carry on',
    ignore: 'Skip it and carry on', commit: 'Stop here and keep what was done', rollback: 'Stop the run', tell: 'Tell me and stop the run'};
  function fltWords(f) {
    if (!f) return 'Always';
    if (f.all) return f.all.map(fltWords).join(' and ');
    if (f.any) return '(' + f.any.map(fltWords).join(' or ') + ')';
    const r = Array.isArray(f.right) ? f.right.join(' – ') : S(f.right);
    return `${S(f.left).replace(/\{\{\s*|\s*\}\}/g, '') || '…'} ${OPW[f.op] || f.op}${r && !NO_RIGHT.has(f.op) ? ' ' + r : ''}`;
  }
  const UNITW = {seconds: 'second', minutes: 'minute', hours: 'hour', days: 'day', weeks: 'week'};
  const _toolsN = s => (Array.isArray(s.tools) ? s.tools : S(s.tools).split(',')).filter(x => S(x).trim()).length;
  function waitWords(s) {
    if (s.for === 'call') return 'until its link is called';
    if (s.amount !== undefined && s.amount !== '') { const n = S(s.amount), u = UNITW[s.unit || 'minutes'] || S(s.unit); return `${n} ${u}${n === '1' ? '' : 's'}`; }
    if (s.duration_s) return `${s.duration_s} seconds`;
    return `until ${S(s.until)}`;
  }
  function stepWords(s) {
    const t = s.type;
    if (t === 'tool') return s.app && s.app.kind === 'app' ? appName(s.app.slug) : nice(s.name);
    if (t === 'http') return `${S(s.method || 'GET')} ${S(s.url).replace(/^https?:\/\//, '').slice(0, 28)}`;
    if (t === 'wait') return waitWords(s);
    if (t === 'subroute') return nice(s.route) + (s.wait === false ? ' (goes on)' : '');
    if (t === 'stop') return (s.as === 'done' ? 'Ends as done' : 'Ends with an error') + (s.message ? ': ' + S(s.message).slice(0, 30) : '');
    if (t === 'respond') return `Answers ${S(s.status || 200)}`;
    if (t === 'notify') return S(s.text).slice(0, 40);
    if (t === 'approval') return S(s.question).slice(0, 40);
    if (t === 'set') return S(s.name);
    if (t === 'filter' || t === 'condition') return s.filter ? fltWords(s.filter).slice(0, 40) : `${S(s.left)} ${OPW[s.op] || s.op || ''} ${S(s.right)}`.slice(0, 40);
    if (t === 'loop') return S(s.items).replace(/\{\{\s*|\s*\}\}/g, '').slice(0, 34);
    if (t === 'router') return `${(s.routes || []).length} ways`;
    if (t === 'code') return 'Python';
    if (t === 'data') return DATAW[s.op] || S(s.op);
    if (t === 'ai') return s.op === 'agent' ? `${_toolsN(s)} tools` : s.op === 'classify' ? S(s.categories).slice(0, 34) : AIW[s.op] || S(s.op);
    if (t === 'router' && s.ai) return `AI picks of ${(s.routes || []).length} ways`;
    return '';
  }
  const titleOfStep = s => S(s.label) || (s.type === 'tool' ? nice(s.name) : s.type === 'data' ? (DATAW[s.op] || 'Data') : s.type === 'ai' ? (AIW[s.op] || 'AI') : KIND[s.type] || s.type);

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

  // a list of steps inside a step (a web request's / an answer's body is data, not steps)
  const subOf = (s, k) => Array.isArray(s[k]) && (k !== 'body' || s.type === 'loop') ? s[k] : null;
  // every list of steps by its place: [] = the route, [id,'then'] / [id,'else'] / [id,'body'] / [id,'fallback'] / [id,'routes',i]
  function find(id, list, path) {
    list = list || ED.steps; path = path || [];
    for (let i = 0; i < list.length; i++) {
      const s = list[i];
      if (s.id === id) return {step: s, list, i, path};
      const subs = [];
      for (const k of ['then', 'else', 'body', 'fallback']) if (subOf(s, k)) subs.push([s[k], [s.id, k]]);
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
    ['then', 'else', 'body', 'fallback'].forEach(k => subOf(s, k) && allSteps(s[k], out)); (s.routes || []).forEach(r => allSteps(r.steps, out)); }); return out; };
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
    if (t.kind === 'event') return [EVW[sp.app] || 'An app event', `Looks every ${sp.every_minutes || 15} minutes`];
    if (t.kind === 'form') return ['From a form', S(sp.title) || 'A form page'];
    if (t.kind === 'chat') return ['From a chat', S(sp.title) || 'A chat page'];
    if (t.kind === 'error') return ['When a route fails', (sp.routes || []).length ? (sp.routes || []).map(nice).join(', ') : 'Any route'];
    if (t.kind === 'route') return ['When another route runs it', (sp.inputs || []).length ? 'Takes ' + sp.inputs.map(x => x.name).join(', ') : 'A building block'];
    if (t.kind === 'tool') return ['As a tool for AI apps', S(sp.description).slice(0, 40) || 'Offered over MCP'];
    const at = (sp.at || []).join(', ');
    let w = sp.every_minutes ? `Every ${sp.every_minutes} minutes` : sp.every_hours ? `Every ${sp.every_hours} hours`
      : sp.days && sp.days.length ? sp.days.map(d => S(d).slice(0, 3).replace(/^./, c => c.toUpperCase())).join(' ') + (at ? ', ' + at : '')
      : sp.monthdays && sp.monthdays.length ? `Day ${sp.monthdays.join(', ')}${at ? ', ' + at : ''}` : sp.once ? `Once, ${S(sp.once).replace('T', ' ')}` : at ? `Every day, ${at}` : 'On a schedule';
    return ['On a schedule', w + (sp.skip_holidays ? ' · not on holidays' : '')];
  }
  const ST_CLS = {ok: 'ok', approved: 'ok', error: 'bad', skipped: 'skip', retry: 'run', waiting_approval: 'run', sleeping: 'run', retry_wait: 'run', filtered: 'skip', stopped: 'skip', ignored: 'skip', resumed: 'ok'};
  // v0.999.253: a run's log -> the state of each step on the canvas (a step that failed in any loop round stays failed)
  function logStates(list) {
    const o = {};
    (list || []).forEach(l => { if (!l || !l.id) return; if (o[l.id] && o[l.id].status === 'error') return; o[l.id] = l; });
    return o;
  }
  function nodeHtml(n) {
    const sel = ED.sel === n.id ? ' sel' : '';
    if (n.kind === 'trigger') {
      const [a, b] = trigWords();
      const ic = TKIC(ED.trig.kind);
      return `<div class="nd trig${sel}" data-node="trigger" style="left:${n.x}px;top:${n.y}px;width:${n.w}px" tabindex="0" role="button" aria-label="Starts: ${esc(a)}">
        <span class="ap k-trig">${svg(ic)}</span><span class="nt"><b>${esc(a)}</b><small>${esc(b)}</small></span></div>`;
    }
    const s = n.step, st = ED.runSt[s.id];
    return `<div class="nd${sel}${s.type === 'approval' ? ' warmk' : ''}${st && st.status === 'error' ? ' fail' : ''}" data-node="${esc(s.id)}" style="left:${n.x}px;top:${n.y}px;width:${n.w}px" tabindex="0" role="button" aria-label="${esc(titleOfStep(s))}">
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
    const re = s => { s.id = freshId(s.id); ['then', 'else', 'body', 'fallback'].forEach(k => (subOf(s, k) || []).forEach(re)); (s.routes || []).forEach(r => (r.steps || []).forEach(re)); };
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
    merge: [['mode', 'How', 'sel', [['append', 'One after the other'], ['by_key', 'Match by a field (join)'], ['by_position', 'Side by side, by position'],
      ['keep_matches', 'Keep items of the first that have a match'], ['keep_non_matches', 'Keep items of the first with no match']]],
      ['a', 'The first list', 'text', ROWS_HELP], ['b', 'The second list', 'text', ROWS_HELP],
      ['key', 'Field in the first list', 'plain', 'Like email'], ['key_b', 'Field in the second list', 'plain', 'Empty = the same name'],
      ['join', 'Keep', 'sel', [['inner', 'Only items found in both'], ['left', 'Every item of the first list'], ['outer', 'Every item of both']]],
      ['keep', 'Length', 'sel', [['', 'As long as the shorter list'], ['all', 'As long as the longer list']]]],
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
    merge: {key: s => ['by_key', 'keep_matches', 'keep_non_matches'].includes(s.mode), key_b: s => ['by_key', 'keep_matches', 'keep_non_matches'].includes(s.mode),
      join: s => s.mode === 'by_key', keep: s => s.mode === 'by_position'},
  };
  // the live result under a box that holds {{ }} (her route's newest data; nothing runs)
  function previewSoon(el, s) {
    const out = document.querySelector(`[data-prev="${CSS.escape(el.id)}"]`); if (!out || !ED) return;
    clearTimeout(el._pv);
    if (!/\{\{[\s\S]*?\}\}/.test(el.value)) { out.hidden = true; return; }
    el._pv = setTimeout(async () => {
      let r; try { r = await api('POST', `/api/route/routes/${enc(ED.r.id)}/eval`, {text: el.value, step: s.id, run_id: ED.debug || ''}); } catch { return; }
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
    // v0.999.246 ROUTE R7: which of her accounts a step uses, and the saved sign-in a web request uses
    if (tinfo && (tinfo.fields || []).some(f => f.name === 'account') && !ED.accts) ED.accts = ((await api('GET', '/api/route/accounts').catch(() => ({}))).accounts) || [];
    if (s.type === 'http' && !ED.creds) ED.creds = ((await api('GET', '/api/route/credentials').catch(() => ({}))).credentials) || [];
    if (!ED) return;
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
        if (f.name === 'account' && (ED.accts || []).length && !/\{\{/.test(txt)) parts.push(field('Which account', txt, {k: 'arg:account', options: [['', 'The main one']].concat(ED.accts.map(a => [a.value, a.label + (a.ok ? '' : ' (needs connecting again)')])), help: 'The account this step uses'}));
        else if (f.enum && f.enum.length) parts.push(field(lab, txt, {k: 'arg:' + f.name, options: [['', '—']].concat(f.enum.map(e => [e, e])), help: f.help, req: f.required}));
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
      parts.push(field('Sign in with', s.auth || '', {k: 'auth', options: [['', 'No sign-in']].concat((ED.creds || []).map(c => [c.name, `${c.name} (${c.host})`])),
        help: (ED.creds || []).length ? 'A saved sign-in is sent only to its own site.' : 'Save one under Sign-ins first.'}));
      if ((s.method || 'GET') === 'POST') parts.push(field('What it sends', typeof s.body === 'string' ? s.body : JSON.stringify(s.body ?? {}, null, 2), {k: 'body', area: true, mono: true, rows: 5}));
    } else if (s.type === 'data' || s.type === 'ai') {
      const spec = (s.type === 'ai' ? AIF : DATAF)[s.op] || [];
      spec.forEach(([key, lab, kind, extra]) => {
        const show = ((s.type === 'ai' ? AISHOW : SHOWIF)[s.op] || {})[key];
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
    else if (s.type === 'wait') {
      const mode = s.for === 'call' ? 'call' : s.until ? 'until' : 'time';
      parts.push(field('Wait', mode, {k: 'wkind', options: [['time', 'For some time'], ['until', 'Until a moment'], ['call', 'Until its link is called']]}));
      if (mode === 'time') {
        const amt = s.amount !== undefined ? s.amount : s.duration_s || '', unit = s.amount !== undefined ? (s.unit || 'minutes') : s.duration_s ? 'seconds' : 'minutes';
        parts.push(`<div class="two">${field('How long', S(amt), {k: 'wamount', num: true, help: 'Up to 30 days'})}${field('Unit', unit, {k: 'wunit', options: [['seconds', 'Seconds'], ['minutes', 'Minutes'], ['hours', 'Hours'], ['days', 'Days'], ['weeks', 'Weeks']]})}</div>`);
      } else if (mode === 'until') {
        parts.push(field('Until', s.until || '', {k: 'until', ph: '09:00 or 2026-12-24 18:00', help: 'A time of day (the next one), or a date and time, in the route\'s time zone. Up to 30 days ahead.'}));
      } else {
        parts.push('<p class="mut sm">The run waits until someone calls its link: send {{vars.resume_url}} in an earlier step (an email, a message). What the call sends becomes this step\'s result.</p>');
        parts.push(`<div class="two">${field('Wait at most (hours)', String(Math.round((s.timeout_s || 86400) / 360) / 10), {k: 'wtimeout', ref: false, num: true, help: 'Up to 720 hours (30 days)'})}${field('If nobody calls', s.on_timeout || 'continue', {k: 'on_timeout', options: [['continue', 'Go on anyway'], ['fail', 'Stop the run with an error']]})}</div>`);
      }
    }
    else if (s.type === 'loop') {
      parts.push(field('A list to go through', typeof s.items === 'string' ? s.items : JSON.stringify(s.items ?? ''), {k: 'items', mono: true, ph: '{{steps.rows.output}}', help: 'The steps inside run once for every item (up to 1,000), as {{item}}.'}));
      parts.push(field('Also call each item (optional)', s.as || '', {k: 'loopas', ref: false, mono: true, ph: 'order', help: 'A name, so a loop inside this one can still read it as {{vars.' + (s.as || 'order') + '}}'}));
    }
    else if (s.type === 'subroute') {
      parts.push(field('The route to run', s.route || '', {k: 'route', ref: false, ph: 'name of the route', help: 'One of your routes, by its name. It runs even when it is switched off.'}));
      parts.push(field('Data it starts with (name: value)', typeof s.vars === 'string' ? s.vars : JSON.stringify(s.vars || {}, null, 2), {k: 'svars', area: true, mono: true, rows: 4, help: 'That route reads them as {{vars.…}}'}));
      parts.push(field('Then', s.wait === false ? 'no' : 'yes', {k: 'swait', options: [['yes', 'Wait for its result, then go on'], ['no', 'Start it and go straight on']]}));
      parts.push('<p class="mut sm">Its result: {{steps.' + esc(s.id) + '.output.result}} (its last step) and {{steps.' + esc(s.id) + '.output.vars}}.</p>');
    }
    else if (s.type === 'stop') {
      parts.push(field('End the run', s.as || 'error', {k: 'as', options: [['error', 'As an error (it shows as failed)'], ['done', 'As done (nothing went wrong)']]}));
      parts.push(field('Message', s.message || '', {k: 'message', area: true, help: 'Shown in the run and sent to you.'}));
    }
    else if (s.type === 'respond') {
      parts.push('<p class="mut sm">When an app starts this route through its webhook, it gets this answer (it waits up to 25 seconds). The route goes on after answering.</p>');
      parts.push(field('Status', S(s.status ?? 200), {k: 'status', num: true, help: '200 = OK, 201 = made, 400 = wrong data'}));
      parts.push(field('Answer', typeof s.body === 'string' ? s.body : JSON.stringify(s.body ?? {}, null, 2), {k: 'body', area: true, mono: true, rows: 5}));
    }
    else if (s.type === 'condition' || s.type === 'filter') {
      parts.push(`<div class="psub">${s.type === 'filter' ? 'Goes on only when' : 'Takes “If yes” when'}</div>`);
      parts.push(filterRows(s.filter || (s.op ? {left: s.left, op: s.op, right: s.right} : null), 'main'));
    } else if (s.type === 'router') {
      parts.push(`<label class="chk"><input type="checkbox" data-aiway${s.ai ? ' checked' : ''}> Let AI pick the way (it reads a text and picks one way by its name)</label>`);
      if (s.ai) {
        parts.push(field('The text it reads', S(s.ai.text), {k: 'aiw:text', area: true, ph: '{{vars.message}}'}));
        parts.push(field('How to choose (optional)', S(s.ai.instructions), {k: 'aiw:instructions', area: true, rows: 2, ph: 'Like: orders go to Sales, problems to Support'}));
      }
      parts.push(`<div class="psub">${s.ai ? 'Ways (named clearly, so the AI can pick)' : 'Ways, tested in order'}</div>`);
      (s.routes || []).forEach((rt, j) => parts.push(`<div class="way" data-way="${j}">${field('Name of this way', rt.label || '', {k: 'rlabel:' + j, ref: false})}${s.ai ? '' : filterRows(rt.filter, 'r' + j)}
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
      else if (k === 'duration_s') { if (v.trim()) s.duration_s = Math.max(1, Math.min(2592000, parseInt(v, 10) || 0)); else delete s.duration_s; }
      else if (k === 'wkind') { ['for', 'timeout_s', 'on_timeout', 'until', 'amount', 'unit', 'duration_s'].forEach(x => delete s[x]);
        if (v === 'call') { s.for = 'call'; s.timeout_s = 86400; } else if (v === 'until') s.until = '09:00'; else { s.amount = 10; s.unit = 'minutes'; } }
      else if (k === 'wamount') { delete s.duration_s; const n = Number(v); s.amount = v.includes('{{') || isNaN(n) || v.trim() === '' ? v : n; s.unit = s.unit || 'minutes'; }
      else if (k === 'wunit') { if (s.amount === undefined) { s.amount = s.duration_s || 1; delete s.duration_s; } s.unit = v; }
      else if (k === 'wtimeout') { s.timeout_s = Math.max(60, Math.min(2592000, Math.round((Number(v) || 24) * 3600))); }
      else if (k === 'loopas') { if (v.trim()) s.as = v.trim(); else delete s.as; }
      else if (k === 'svars') { try { s.vars = v.trim() ? JSON.parse(v) : {}; el.classList.remove('err'); } catch { el.classList.add('err'); return; } }
      else if (k === 'swait') { if (v === 'no') s.wait = false; else delete s.wait; }
      else if (k === 'status') { const n = Number(v); s.status = v.includes('{{') || isNaN(n) ? v : n; }
      else if (k === 'until') { if (v.trim()) s.until = v.trim(); else delete s.until; }
      else if (k === 'value' || k === 'items') s[k] = v;
      else if (k === 'body') { try { s.body = v.trim() ? JSON.parse(v) : {}; } catch { s.body = v; } }
      else if (k === 'method') s.method = v;
      else if (k === 'auth') { if (v) s.auth = v; else delete s.auth; }
      else if (k.startsWith('rlabel:')) { const j = +k.split(':')[1]; s.routes[j].label = v; }
      else if (k === 'oe_do') { if (v) s.on_error = Object.assign({}, s.on_error || {}, {do: v}); else delete s.on_error; }
      else if (k === 'oe_retries') { s.on_error.retries = Math.max(0, Math.min(10, parseInt(v, 10) || 0)); }
      else if (k === 'oe_wait') { s.on_error.wait_min = Math.max(1, Math.min(1440, parseInt(v, 10) || 1)); }
      else if (k === 'oe_value') s.on_error.value = v;
      else if (k.startsWith('d:')) { const key = k.slice(2); if (v === '') delete s[key]; else if (v === 'true') s[key] = true;
        else s[key] = /^-?\d+(\.\d+)?$/.test(v.trim()) && ['count', 'amount', 'length', 'max_steps', 'max_tokens'].includes(key) ? Number(v) : v; }
      else if (k.startsWith('aiw:')) { s.ai = Object.assign({}, s.ai || {}); if (v) s.ai[k.slice(4)] = v; else delete s.ai[k.slice(4)]; }
      else if (k.startsWith('dobj:')) { try { s[k.slice(5)] = v.trim() ? JSON.parse(v) : {}; el.classList.remove('err'); } catch { el.classList.add('err'); return; } }
      else s[k] = v;
      ED.dirty = snap() !== ED.saved; draw(); topState();
      if (['method', 'oe_do', 'd:action', 'd:how', 'd:mode', 'wkind', 'd:memory'].includes(k)) stepPanel(box.parentNode);
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
    const aw = box.querySelector('[data-aiway]');
    if (aw) aw.addEventListener('change', () => { before(); if (aw.checked) s.ai = s.ai || {text: ''}; else delete s.ai; changed(false); stepPanel(box.parentNode); });
    const fb = box.querySelector('[data-fallback]');
    if (fb) fb.addEventListener('change', () => { before(); if (fb.checked) s.fallback = s.fallback || []; else delete s.fallback; changed(false); });
    const sid = box.querySelector('[data-sid]');
    sid.addEventListener('change', () => { const v = sid.value.trim(); if (v === s.id) return; if (!renameStep(s.id, v)) sid.value = s.id; });
  }

  // v0.999.240 ROUTE R5: every way a route can start
  const TKINDS = [['manual', 'By hand', 'When you run or test it', 'hand'], ['schedule', 'On a schedule', 'Times, days, every few minutes', 'cal'],
    ['webhook', 'When data arrives', 'Another app sends to its address', 'bolt'], ['event', 'When something happens in an app', 'New email, sheet row, form answer, feed item…', 'spark'],
    ['form', 'From a form', 'A form page you share', 'tform'], ['chat', 'From a chat', 'A chat page people write in', 'tchat'],
    ['error', 'When a route fails', 'Handle failures in one place', 'terr'], ['route', 'When another route runs it', 'Use it as a building block', 'subroute'],
    ['tool', 'As a tool for AI apps', 'AI apps can call it (MCP)', 'code']];
  const TKIC = k => IC[(TKINDS.find(x => x[0] === k) || [])[3] || 'hand'] || IC.hand;
  const EVW = {email: 'New email', sheet_row: 'New row in a sheet', form_answer: 'New answer to a Google form', calendar_event: 'New calendar event',
    drive_file: 'New file in Drive', rss: 'New item in a feed (RSS / Atom)', app: 'New item in another app'};
  const FTYPES = [['text', 'Short text'], ['textarea', 'Long text'], ['email', 'Email'], ['number', 'Number'], ['date', 'Date'], ['select', 'A choice'], ['checkbox', 'Tick box'], ['phone', 'Phone']];
  function trigDefault(k) {
    const nm = nice(ED.r.name);
    return {event: {app: 'email', every_minutes: 15}, form: {title: nm, button: 'Send', thanks: 'Thank you - it was sent.',
      fields: [{name: 'name', label: 'Your name', type: 'text', required: true}, {name: 'email', label: 'Email', type: 'email', required: true}, {name: 'message', label: 'Message', type: 'textarea'}]},
      chat: {title: nm, greeting: 'Hi! How can I help?'}, error: {routes: []}, route: {inputs: []}, tool: {description: S(ED.r.description), inputs: []}}[k] || {};
  }
  function addrBox(kind) {
    const has = ED.r.trigger === kind;
    if (!has) return '<span class="mut sm">Save first, then make its address here.</span>';
    const pub = kind !== 'webhook' && ED.r.public_url ? (/^https?:/.test(ED.r.public_url) ? ED.r.public_url : location.origin + ED.r.public_url) : '';
    return pub ? `<code class="addr">${esc(pub)}</code><div class="crow"><button class="btn soft s" type="button" data-copy="${esc(pub)}">Copy</button>
        <a class="btn soft s" href="${esc(pub)}" target="_blank" rel="noopener">Open it</a><button class="btn s soft" type="button" id="addrNew">Make a new address</button></div>`
      : `<button class="btn s soft" type="button" id="addrNew">${kind === 'webhook' ? 'Make a new address' : 'Make its address'}</button>`;
  }
  function rowsEditor(rows, cols, key, addLabel) {
    return `<div class="trows" data-rows="${key}">${rows.map((r, i) => `<div class="trow">${cols.map(([c, lab, kind, opts]) => kind === 'chk'
      ? `<label class="chk"><input type="checkbox" data-r="${key}:${i}:${c}"${r[c] ? ' checked' : ''}> ${esc(lab)}</label>`
      : kind === 'sel' ? `<label class="tc"><span>${esc(lab)}</span><select data-r="${key}:${i}:${c}">${opts.map(([v, t]) => `<option value="${esc(v)}"${S(r[c] || opts[0][0]) === v ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`
      : `<label class="tc"><span>${esc(lab)}</span><input data-r="${key}:${i}:${c}" value="${esc(Array.isArray(r[c]) ? r[c].join(', ') : S(r[c]))}"${c === 'name' ? ' class="mono"' : ''}></label>`).join('')}
      <button class="btn s soft bad ib" type="button" data-rdel="${key}:${i}" aria-label="Remove">${svg(IC.trash)}</button></div>`).join('')}
      <button class="btn s soft" type="button" data-radd="${key}">${svg(IC.plus)}${esc(addLabel)}</button></div>`;
  }
  async function trigCat() {
    if (!ED.trigCat) { try { ED.trigCat = await api('GET', '/api/route/triggers'); } catch { ED.trigCat = {events: [], mcp: {}}; } }
    return ED.trigCat;
  }
  async function trigPanel(box) {
    const t = ED.trig, sp = t.spec || {};
    const cat = await trigCat();
    if (!ED) return;
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    const dayW = {mon: 'Mon', tue: 'Tue', wed: 'Wed', thu: 'Thu', fri: 'Fri', sat: 'Sat', sun: 'Sun'};
    let zones = []; try { zones = Intl.supportedValuesOf('timeZone'); } catch {}
    let body = '';
    if (t.kind === 'manual') body = '<p class="mut sm">It runs when you test it here, run it from a chat, or another route calls for it.</p>';
    else if (t.kind === 'webhook') body = `<p class="mut sm">Another app starts it by sending data to a secret web address. What it sends is <code>{{vars.body}}</code> in your steps. An “Answer the caller” step sends the app an answer.</p><div id="addrBox">${addrBox('webhook')}</div>`;
    else if (t.kind === 'schedule') body = `
        ${field('At these times (HH:MM, 24-hour)', (sp.at || []).join(', '), {k: 'at', ref: false, ph: '09:00, 17:30'})}
        <div class="fld"><label>On these days <span class="mut sm">(none = every day)</span></label><div class="days">${days.map(d => `<button type="button" data-day="${d}" aria-pressed="${(sp.days || []).includes(d)}">${dayW[d]}</button>`).join('')}</div></div>
        <div class="two">${field('Or every N minutes', sp.every_minutes || '', {k: 'every_minutes', ref: false, num: true, help: '15 or more'})}${field('Or every N hours', sp.every_hours || '', {k: 'every_hours', ref: false, num: true})}</div>
        <div class="fld"><label for="tzIn">Time zone</label><div class="fc"><input id="tzIn" list="tzList" value="${esc(sp.timezone || '')}" placeholder="${esc(TZ || 'Europe/London')}"></div>
          <datalist id="tzList">${zones.map(z => `<option value="${esc(z)}">`).join('')}</datalist></div>
        ${field('Skip the public holidays of', sp.skip_holidays || '', {k: 'skip_holidays', ref: false, ph: 'A country code, like GB, US, DE', help: 'The run waits for the next working day.'})}
        <div class="two">${field('Quiet from', (sp.quiet || {}).from || '', {k: 'qfrom', ref: false, ph: '22:00'})}${field('Quiet until', (sp.quiet || {}).to || '', {k: 'qto', ref: false, ph: '08:00'})}</div>`;
    else if (t.kind === 'event') {
      const app = sp.app || 'email', P = [];
      P.push(field('When there is', app, {k: 'tg:app', options: Object.entries(EVW)}));
      if (app === 'email') { P.push(`<div class="two">${field('In this folder', sp.folder || '', {k: 'tg:folder', ref: false, ph: 'inbox'})}${field('Only emails that match', sp.search || '', {k: 'tg:search', ref: false, ph: 'from:shop@ or invoice'})}</div>`);
        P.push(`<label class="chk"><input type="checkbox" data-tgc="unread_only"${sp.unread_only ? ' checked' : ''}> Only unread emails</label>`); }
      if (app === 'sheet_row') P.push(`<div class="two">${field('The sheet', sp.spreadsheet || '', {k: 'tg:spreadsheet', ref: false, ph: 'Its name or link', req: true})}${field('Tab', sp.tab || '', {k: 'tg:tab', ref: false, ph: 'The first tab'})}</div>`);
      if (app === 'form_answer') P.push(field('The Google form', sp.form || '', {k: 'tg:form', ref: false, ph: 'Its name or link', req: true}));
      if (app === 'calendar_event') P.push(field('Only events with these words', sp.query || '', {k: 'tg:query', ref: false, ph: 'Optional'}));
      if (app === 'drive_file') P.push(`<div class="two">${field('Files with these words', sp.query || '', {k: 'tg:query', ref: false, ph: 'Optional'})}${field('In this folder', sp.folder || '', {k: 'tg:folder', ref: false, ph: 'Optional'})}</div>`);
      if (app === 'rss') P.push(field('The feed’s address', sp.url || '', {k: 'tg:url', ref: false, mono: true, ph: 'https://example.com/feed.xml', req: true}));
      if (app === 'app') {
        P.push(field('Tool that lists the items', sp.tool || '', {k: 'tg:tool', ref: false, mono: true, ph: 'composio_apps, sheet_read…', help: 'Only a tool or app action that reads (lists, gets, searches). A trigger never sends or changes anything.'}));
        P.push(field('What it sends (as data)', JSON.stringify(sp.args || {}, null, 2), {k: 'tg:args', ref: false, area: true, mono: true, rows: 4}));
        P.push(`<div class="two">${field('The list in its answer (optional)', sp.items || '', {k: 'tg:items', ref: false, mono: true, ph: 'data.items'})}${field('Each item’s id field (optional)', sp.id || '', {k: 'tg:id', ref: false, mono: true, ph: 'id'})}</div>`);
      }
      P.push(field('Look every (minutes)', S(sp.every_minutes || 15), {k: 'tg:every_minutes', ref: false, num: true, help: `${(cat.every || {}).min || 5} to ${(cat.every || {}).max || 1440}`}));
      const pl = ED.r.trigger === 'event' ? ED.r.poll : null;
      const pw = !pl ? 'Not looked yet. The first look only notes what is there - nothing runs for items that were already there.'
        : pl.error ? `Last look did not work: ${pl.error}` : !pl.looked ? 'It will look soon. The first look only notes what is there.'
        : `Last looked ${pl.last_at ? at(pl.last_at) : ''} · ${pl.seen} items known · ${pl.last_new} new last time`;
      P.push(`<p class="mut sm">Each new item starts one run; your steps read it as <code>{{vars.event}}</code>.</p><div class="okbox sm" id="pollBox">${esc(pw)}</div>
        ${ED.r.trigger === 'event' ? '<div class="crow"><button class="btn s soft" type="button" id="lookNow">Look now</button><span class="mut sm">Each new item starts a run.</span></div>' : ''}`);
      body = P.join('');
    } else if (t.kind === 'form') {
      body = `${field('Title', sp.title || '', {k: 'tg:title', ref: false})}${field('A line under the title', sp.intro || '', {k: 'tg:intro', ref: false, area: true, rows: 2})}
        <div class="psub">The questions</div>${rowsEditor(sp.fields || [], [['label', 'Question', 'txt'], ['name', 'Name', 'txt'], ['type', 'Kind', 'sel', FTYPES], ['options', 'Choices (with commas)', 'txt'], ['required', 'Needed', 'chk']], 'fields', 'Add a question')}
        <div class="two">${field('Button', sp.button || 'Send', {k: 'tg:button', ref: false})}${field('After sending, show', sp.thanks || '', {k: 'tg:thanks', ref: false})}</div>
        <p class="mut sm">Answers are <code>{{vars.form.name}}</code> and so on. An “Answer the caller” step's answer is shown to the person instead of the line above.</p>
        <div class="psub">Its address</div><div id="addrBox">${addrBox('form')}</div>`;
    } else if (t.kind === 'chat') {
      body = `${field('Title', sp.title || '', {k: 'tg:title', ref: false})}${field('First message', sp.greeting || '', {k: 'tg:greeting', ref: false, area: true, rows: 2})}
        ${field('Box hint', sp.placeholder || '', {k: 'tg:placeholder', ref: false, ph: 'Write a message'})}
        <p class="mut sm">Each message starts a run with <code>{{vars.message}}</code> and the conversation so far in <code>{{vars.history}}</code>. Put an “Answer the caller” step to reply - its answer (text, or <code>{"reply": …}</code>) is what the person sees.</p>
        <div class="psub">Its address</div><div id="addrBox">${addrBox('chat')}</div>`;
    } else if (t.kind === 'error') {
      body = `${field('Routes to watch (with commas)', (sp.routes || []).join(', '), {k: 'tg:routes', ref: false, ph: 'Empty = any route', help: 'When one of them fails, this route runs.'})}
        <p class="mut sm">Your steps read <code>{{vars.failed_route}}</code>, <code>{{vars.error}}</code> and <code>{{vars.failed_run}}</code>. A failing error route never starts another one.</p>`;
    } else if (t.kind === 'route' || t.kind === 'tool') {
      if (t.kind === 'tool') body += field('What it does (for the AI app)', sp.description || '', {k: 'tg:description', ref: false, area: true, rows: 2, req: true});
      body += `<div class="psub">What it takes</div>${rowsEditor(sp.inputs || [], [['name', 'Name', 'txt'], ['description', 'What it is', 'txt'], ...(t.kind === 'tool' ? [['type', 'Kind', 'sel', [['string', 'Text'], ['number', 'Number'], ['boolean', 'Yes / no'], ['object', 'Object'], ['array', 'List']]], ['required', 'Needed', 'chk']] : [])], 'inputs', 'Add an input')}
        <p class="mut sm">Your steps read them as <code>{{vars.name}}</code>.${t.kind === 'route' ? ' Another route runs it with a “Run another route” step.' : ' An answer step sends the AI app its answer; without one it gets the last step\'s result.'}</p>`;
      if (t.kind === 'tool') {
        const m = cat.mcp || {};
        body += `<div class="psub">Your routes as tools</div><p class="mut sm">One address for your account lists every switched-on route that starts “as a tool”. Add it to an AI app as an MCP server.</p>
          <div id="mcpBox">${m.made ? '<span class="mut sm">Your address is made (shown once). Making a new one stops the old one.</span>' : ''}<button class="btn s soft" type="button" id="mcpNew">${m.made ? 'Make a new address' : 'Make the address'}</button></div>`;
      }
    }
    box.innerHTML = `<div class="pform"><div class="phead"><span class="ap k-trig">${svg(TKIC(t.kind))}</span><div><div class="pk">What starts it</div><div class="pt">${esc(trigWords()[0])}</div></div></div>
      <div class="tkinds" role="radiogroup" aria-label="What starts the route">${TKINDS.map(([k, w, sub, ic]) =>
        `<button type="button" data-tk="${k}" role="radio" aria-checked="${t.kind === k}" aria-pressed="${t.kind === k}">${svg(IC[ic] || IC.hand)}<span><b>${esc(w)}</b><small>${esc(sub)}</small></span></button>`).join('')}</div>
      ${body}<p class="mut sm">Changes here count once you tap Save.</p></div>`;
    box.querySelectorAll('[data-tk]').forEach(b => b.addEventListener('click', () => {
      if (t.kind === b.dataset.tk) return;
      before(); t.kind = b.dataset.tk;
      if (t.kind === 'schedule') { if (!Object.keys(t.spec || {}).some(k => ['at', 'every_minutes', 'every_hours', 'days', 'monthdays', 'dates', 'once'].includes(k)) || t.spec.app) t.spec = {at: ['09:00'], timezone: TZ || ''}; }
      else t.spec = ED.r.trigger === t.kind ? clone(ED.r.trigger_spec || {}) : trigDefault(t.kind);
      changed(false); trigPanel(box);
    }));
    const tz = $('#tzIn');
    if (tz) tz.addEventListener('change', () => { before(); if (tz.value.trim()) t.spec.timezone = tz.value.trim(); else delete t.spec.timezone; changed(false); });
    box.querySelectorAll('[data-day]').forEach(b => b.addEventListener('click', () => {
      before(); const d = b.dataset.day, cur = new Set(t.spec.days || []);
      cur.has(d) ? cur.delete(d) : cur.add(d); const v = days.filter(x => cur.has(x)); if (v.length) t.spec.days = v; else delete t.spec.days;
      changed(false); trigPanel(box);
    }));
    const form = box.firstElementChild;
    form.addEventListener('change', e => {
      const el = e.target, k = el.dataset.k;
      if (el.dataset.tgc) { before(); if (el.checked) t.spec[el.dataset.tgc] = true; else delete t.spec[el.dataset.tgc]; changed(false); return; }
      if (el.dataset.r) {
        const [key, i, c] = el.dataset.r.split(':'); const row = (t.spec[key] || [])[+i]; if (!row) return; before();
        if (el.type === 'checkbox') row[c] = el.checked;
        else if (c === 'options') row.options = el.value.split(',').map(x => x.trim()).filter(Boolean);
        else row[c] = el.value.trim();
        if (c === 'label' && key === 'fields' && row._new && !row._named) { row.name = freshName(el.value, t.spec.fields, +i); }
        if (c === 'name') row._named = true;
        changed(false); if (c === 'type' || c === 'label') trigPanel(box); return;
      }
      if (!k) return;
      const v = el.value.trim(); before();
      if (k === 'at') { const a = v.split(/[,\s]+/).filter(Boolean); if (a.length) t.spec.at = a; else delete t.spec.at; }
      else if (k === 'every_minutes' || k === 'every_hours') { if (v) t.spec[k] = parseInt(v, 10) || v; else delete t.spec[k]; }
      else if (k === 'skip_holidays') { if (v) t.spec.skip_holidays = v.toUpperCase(); else delete t.spec.skip_holidays; }
      else if (k === 'qfrom' || k === 'qto') { const q = Object.assign({}, t.spec.quiet || {}); q[k === 'qfrom' ? 'from' : 'to'] = v; if (q.from || q.to) t.spec.quiet = q; else delete t.spec.quiet; }
      else if (k.startsWith('tg:')) {
        const key = k.slice(3);
        if (key === 'app') { t.spec = {app: v, every_minutes: t.spec.every_minutes || 15}; changed(false); trigPanel(box); return; }
        if (key === 'every_minutes') t.spec.every_minutes = parseInt(v, 10) || 15;
        else if (key === 'args') { try { t.spec.args = v ? JSON.parse(v) : {}; el.classList.remove('err'); } catch { el.classList.add('err'); return; } }
        else if (key === 'routes') t.spec.routes = v.split(',').map(x => x.trim().toLowerCase().replace(/\s+/g, '_')).filter(Boolean);
        else if (v) t.spec[key] = el.tagName === 'TEXTAREA' && key !== 'args' ? el.value : v; else delete t.spec[key];
      }
      changed(false);
    });
    box.querySelectorAll('[data-radd]').forEach(b => b.addEventListener('click', () => {
      const key = b.dataset.radd; before(); t.spec[key] = t.spec[key] || [];
      const n = t.spec[key].length + 1;
      t.spec[key].push(key === 'fields' ? {name: freshName('question ' + n, t.spec[key], -1), label: 'Question ' + n, type: 'text', _new: true} : {name: 'input_' + n, description: ''});
      changed(false); trigPanel(box);
    }));
    box.querySelectorAll('[data-rdel]').forEach(b => b.addEventListener('click', () => {
      const [key, i] = b.dataset.rdel.split(':'); before(); (t.spec[key] || []).splice(+i, 1); changed(false); trigPanel(box);
    }));
    box.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => navigator.clipboard.writeText(b.dataset.copy).then(() => toast('Copied.'), () => toast('Copy it by hand.', true))));
    const an = $('#addrNew');
    if (an) an.addEventListener('click', async () => {
      const had = /new/i.test(an.textContent);
      if (had && an.dataset.sure !== '1') { an.dataset.sure = '1'; an.textContent = 'The old address stops working. Make a new one?'; return; }
      an.disabled = true;
      try {
        const a = await api('POST', `/api/route/routes/${enc(ED.r.id)}/address`);
        const url = /^https?:/.test(a.url) ? a.url : location.origin + a.url;
        if (ED.trig.kind !== 'webhook') ED.r.public_url = a.url;
        $('#addrBox').innerHTML = `<code class="addr">${esc(url)}</code><span class="mut sm">${esc(a.note)}</span><div class="crow"><button class="btn soft s" type="button" id="addrCopy">Copy</button>${ED.trig.kind !== 'webhook' ? `<a class="btn soft s" href="${esc(url)}" target="_blank" rel="noopener">Open it</a>` : ''}</div>`;
        $('#addrCopy').addEventListener('click', () => navigator.clipboard.writeText(url).then(() => toast('Copied.'), () => toast('Copy it by hand.', true)));
      } catch (err) { toast(err.message, true); an.disabled = false; }
    });
    const mn = $('#mcpNew');
    if (mn) mn.addEventListener('click', async () => {
      if ((cat.mcp || {}).made && mn.dataset.sure !== '1') { mn.dataset.sure = '1'; mn.textContent = 'The old address stops working. Make a new one?'; return; }
      mn.disabled = true;
      try {
        const a = await api('POST', '/api/route/mcp');
        const url = /^https?:/.test(a.url) ? a.url : location.origin + a.url;
        cat.mcp = {made: true};
        $('#mcpBox').innerHTML = `<code class="addr">${esc(url)}</code><span class="mut sm">${esc(a.note)}</span><div class="crow"><button class="btn soft s" type="button" id="mcpCopy">Copy</button></div>`;
        $('#mcpCopy').addEventListener('click', () => navigator.clipboard.writeText(url).then(() => toast('Copied.'), () => toast('Copy it by hand.', true)));
      } catch (err) { toast(err.message, true); mn.disabled = false; }
    });
    const ln = $('#lookNow');
    if (ln) ln.addEventListener('click', async () => {
      ln.disabled = true; ln.textContent = 'Looking…';
      try {
        const r = await api('POST', `/api/route/routes/${enc(ED.r.id)}/look`);
        ED.r.poll = r.poll;
        toast(r.first_look ? `Looked: ${r.noted} items noted. New ones will start a run.` : r.ok === false ? 'The look did not work.' : `${r.new || 0} new, ${r.started || 0} runs started.`, r.ok === false);
      } catch (err) { toast(err.message, true); }
      if (ED && ED.sel === 'trigger') trigPanel(box);
    });
  }
  function freshName(label, rows, self) {
    let b = S(label).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 30) || 'field';
    if (!/^[a-z_]/.test(b)) b = 'f_' + b;
    const used = new Set((rows || []).filter((_, j) => j !== self).map(r => r.name));
    let n = b, i = 2; while (used.has(n)) n = `${b}_${i++}`; return n;
  }

  // the add-a-step panel: search + groups (step kinds and Hoola's tools / connected apps)
  const GROUPS = [['AI', IC.ai, 'k-ai'], ['Human in the loop', IC.approval, 'k-warm'], ['Flow', IC.route, 'k-flow'], ['Data', IC.store, 'k-data'], ['Core', IC.http, 'k-core']];
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
    const idx = l => { const o = {}; const w = x => (x || []).forEach(s => { o[s.id] = s; ['then', 'else', 'body', 'fallback'].forEach(k => w(subOf(s, k))); (s.routes || []).forEach(r => w(r.steps)); }); w(l); return o; };
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

  // ---------------------------------------------------------------- R8: a past run's data in the editor
  // v0.999.253: "boom: boom: ValueError" -> "ValueError" (the step's name is said once, before it)
  function dropStep(msg, id) {
    let m = S(msg); const q = S(id).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    if (!q) return m;
    const re = new RegExp('^(step )?[\'‘"]?' + q + '[\'’"]?( \\([a-z_]+\\))?:\\s*');
    for (let n = 0; n < 3 && re.test(m); n++) m = m.replace(re, '');
    return m;
  }
  function debugBanner(d, err) {
    const b = $('#edBanner'); if (!b || !ED) return;
    if (err) { b.innerHTML = `<span>${esc(err)}</span><a class="btn s soft" href="#/r/${enc(ED.r.id)}">Back to the newest data</a>`; b.hidden = false; return; }
    const why = d.error ? dropStep(human(d.error), d.failed_step) : '';
    const fail = d.failed_step ? ` It failed at <b>${esc(nice(d.failed_step))}</b>${why ? ': ' + esc(why) : ''}.` : '';
    b.innerHTML = `<span class="dbg">${svg(IC.play)}<span>Looking at the run from ${esc(at(d.at))} (${esc((RUNPILL[d.status] || ['', d.status || ''])[1])}).${fail} A step you test here works on that run's data.</span></span>
      <span class="crow"><button class="btn s" type="button" id="dbgPin">Pin this run's data</button>
      <button class="btn s soft" type="button" id="dbgAgain">Run again with the same data</button>
      <a class="btn s soft" href="#/run/${enc(d.run_id)}">Open the run</a>
      <a class="btn s soft" id="dbgOff" href="#/r/${enc(ED.r.id)}">Back to the newest data</a></span>`;
    b.hidden = false; b.classList.add('debug');
    $('#dbgPin').addEventListener('click', async () => {
      try { const o = await api('POST', `/api/route/routes/${enc(ED.r.id)}/pins/from-run`, {run_id: d.run_id});
        toast(`Pinned ${o.pinned.length} piece${o.pinned.length === 1 ? '' : 's'} of this run's data. Tests use it.${o.skipped.length ? ' ' + o.skipped.length + ' too big to pin.' : ''}`); }
      catch (e) { toast(e.message, true); } });
    $('#dbgAgain').addEventListener('click', async () => {
      try { const o = await api('POST', `/api/route/runs/${enc(d.run_id)}/rerun`); toast('Running again with the same data.'); location.hash = '#/run/' + enc(o.run_id); }
      catch (e) { toast(e.message, true); } });
  }

  // ---------------------------------------------------------------- R2: a step with its data (in · settings · out)
  async function loadData() {
    if (!ED || !ED.r) return;
    try { ED.data = await api('GET', `/api/route/routes/${enc(ED.r.id)}/data${ED.debug ? '?run_id=' + enc(ED.debug) : ''}`); }
    catch (err) { if (ED && ED.debug) debugBanner(null, err.message); return; }
    if (!ED) return;
    if (ED.debug) {
      debugBanner(ED.data);
      ED.runSt = {};                       // v0.999.253: the past run's steps marked on the canvas (done / failed / waiting)
      Object.entries(ED.data.log || {}).forEach(([k, v]) => { ED.runSt[k] = v; });
    }
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
    const s = h.step, decides = ['condition', 'router', 'loop', 'filter', 'approval', 'wait', 'stop', 'respond'].includes(s.type);
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
    const real = !['condition', 'router', 'loop', 'filter', 'approval', 'wait', 'stop', 'respond'].includes(h.step.type);
    if (real && !sure && !ED.realOk) { ED.realAsk = h.step.id; modalOut(); return; }
    if (ED.dirty && !(await save())) return;
    const b = $('#smTest'); if (b) { b.disabled = true; b.innerHTML = `<span class="dots"><i></i><i></i><i></i></span>Testing`; }
    let res;
    try { res = await api('POST', `/api/route/routes/${enc(ED.r.id)}/steps/${enc(h.step.id)}/test`, {use_pins: !ED.debug, run_id: ED.debug || ''}); }
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
      ED.runSt = logStates(r.steps_log);
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
  async function viewEditor(id, tab, runId) {
    const r = await api('GET', `/api/route/routes/${enc(id)}`);
    if (ED && ED.r && ED.r.id !== id) stopEditor();
    shell(true); setNav('routes');
    if (tab === 'runs' || tab === 'settings' || tab === 'versions') { await viewRouteTab(r, tab); return; }
    stopEditor();
    ED = {r: null, steps: [], trig: {}, pos: {}, notes: [], sel: null, hist: [], fut: [], z: 1, px: 40, py: 80, dirty: false, runSt: {}, tab: 'ask', chat: null,
          debug: tab === 'debug' ? S(runId || '') : ''};
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
      <div class="segtabs" role="tablist"><a role="tab" href="#/r/${enc(r.id)}" aria-selected="${tab === 'editor'}">Editor</a><a role="tab" href="#/r/${enc(r.id)}/runs" aria-selected="${tab === 'runs'}">Runs</a><a role="tab" href="#/r/${enc(r.id)}/versions" aria-selected="${tab === 'versions'}">Versions</a><a role="tab" href="#/r/${enc(r.id)}/settings" aria-selected="${tab === 'settings'}">Settings</a></div>
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
      MAIN.innerHTML = `<div class="ed tabbed">${edTop(r, tab)}<div class="edpage">${body}</div></div>`;
      return;
    }
    if (tab === 'versions') { await versionsTab(r); return; }
    // v0.999.246 ROUTE R7: every setting of the route on the page
    const st = r.settings || {};
    const [all, team] = await Promise.all([api('GET', '/api/route/routes').catch(() => ({routes: []})), api('GET', '/api/route/team').catch(() => ({team: []}))]);
    const others = (all.routes || []).filter(x => x.id !== r.id);
    let zones = []; try { zones = Intl.supportedValuesOf('timeZone'); } catch {}
    const shared = new Set(st.shared_with || []);
    const sh = r.share || {};
    const sp = r.trigger_spec || {};
    body = `<div class="setgrid">
      <section class="card"><div class="hd"><h2>How it runs</h2></div>
        <div class="kv"><span class="k">Runs when</span><span>${esc(r.when)}</span></div>
        ${sp.timezone || st.timezone ? `<div class="kv"><span class="k">Time zone</span><span>${esc(sp.timezone || st.timezone)}</span></div>` : ''}
        ${sp.quiet ? `<div class="kv"><span class="k">Quiet hours</span><span>${esc(sp.quiet.from)}–${esc(sp.quiet.to)}</span></div>` : ''}
        ${sp.skip_holidays ? `<div class="kv"><span class="k">Skips holidays of</span><span>${esc(sp.skip_holidays)}</span></div>` : ''}
        ${r.next_due_at ? `<div class="kv"><span class="k">Next run</span><span>${esc(at(r.next_due_at))}</span></div>` : ''}
        ${r.trigger === 'webhook' ? `<div class="kv"><span class="k">Address that starts it</span><span class="v" id="addrBox"><span class="mut">Kept secret. Make a new one to see it.</span><br><button class="btn soft s" id="addrNew" type="button">Make a new address</button></span></div>` : ''}
        ${r.public_url ? `<div class="kv"><span class="k">Its page</span><span class="v"><code class="addr">${esc(/^https?:/.test(r.public_url) ? r.public_url : location.origin + r.public_url)}</code></span></div>` : ''}
        <div class="kv"><span class="k">Money and sending</span><span>Always wait for your tap</span></div>
        <p class="mut sm">What starts it is changed in the editor (click the first step).</p></section>
      <section class="card"><div class="hd"><h2>Settings</h2></div><form id="setForm" class="pform">
        ${field('What it does (one line)', r.description || '', {k: 'description', ref: false})}
        <div class="two">${field('Folder', st.folder || '', {k: 'folder', ref: false, ph: 'Like Sales'})}${field('Tags (with commas)', (st.tags || []).join(', '), {k: 'tags', ref: false, ph: 'orders, daily'})}</div>
        <div class="fld"><label for="stTz">Time zone</label><div class="fc"><input id="stTz" data-k="timezone" list="stTzList" value="${esc(st.timezone || '')}" placeholder="${esc(TZ || 'Europe/London')}"></div>
          <datalist id="stTzList">${zones.map(z => `<option value="${esc(z)}">`).join('')}</datalist><span class="fh">Used by its schedule, its waits and its dates.</span></div>
        <div class="two">${field('Switch it off after this many failed runs in a row', S(st.stop_after_errors || ''), {k: 'stop_after_errors', ref: false, num: true, help: '1-20; empty = never'})}
          ${field('At most this many runs a day', S(st.runs_per_day || ''), {k: 'runs_per_day', ref: false, num: true, help: 'Empty = no limit'})}</div>
        <div class="two">${field('When it fails, run', st.error_route || '', {k: 'error_route', options: [['', 'Nothing'], ...others.map(x => [x.name, nice(x.name)])]})}
          ${field('Currency', st.currency || '', {k: 'currency', ref: false, ph: 'Like EUR, USD, INR'})}</div>
        <div class="two">${field('Keep its runs for (days)', S(st.keep_runs_days || ''), {k: 'keep_runs_days', ref: false, num: true, help: '1-3650; empty = the server default'})}
          ${field('Keep at most this many runs', S(st.keep_runs || ''), {k: 'keep_runs', ref: false, num: true, help: 'Empty = the server default'})}</div>
        ${field('Minutes one run saves you', S(st.minutes_saved || ''), {k: 'minutes_saved', ref: false, num: true, help: 'Used for Time saved in Insights; empty = not counted'})}
        <div class="crow"><button class="btn s" type="submit" id="setSave">Save settings</button><span class="mut sm" id="setNote"></span></div></form></section>
      <section class="card"><div class="hd"><h2>Share</h2></div>
        <p class="mut sm">A link to look at this route - its steps in words, without any of its data or sign-ins. It works for 30 days.</p>
        <div id="shareBox">${sh.on ? `<code class="addr">${esc(/^https?:/.test(sh.url) ? sh.url : location.origin + sh.url)}</code><div class="crow"><button class="btn soft s" type="button" data-copy="${esc(/^https?:/.test(sh.url) ? sh.url : location.origin + sh.url)}">Copy</button><button class="btn soft s bad" type="button" id="shareStop">Stop the link</button></div>`
          : '<button class="btn soft s" type="button" id="shareMake">Make a link</button>'}</div>
        <div class="psub">Team members who may run it</div>
        ${(team.team || []).length ? `<div class="tchk">${team.team.map(m => `<label class="chk"><input type="checkbox" data-member="${esc(m.id)}"${shared.has(m.id) ? ' checked' : ''}${m.active ? '' : ' disabled'}> ${esc(m.name)} <span class="mut sm">(${esc(m.role)})</span></label>`).join('')}</div>
          <p class="mut sm">They ask their own Hoola to run it. They can run it, never change it.</p>`
          : '<p class="mut sm">No team yet. Add people in AI Employees &gt; Team, then share routes with them here.</p>'}
        <div class="psub">As a file</div>
        <div class="crow"><button class="btn soft s" type="button" id="expFile">Download as a file</button><span class="mut sm">Keys and addresses are left out.</span></div></section>
      <section class="card danger"><div class="hd"><h2>Delete this route</h2></div>
        <p class="mut sm" id="delWords">Its steps and its run history go. This cannot be undone. A route with a run still going cannot be deleted.</p>
        <div class="crow"><button class="btn soft bad s" id="delAsk" type="button">Delete route</button>
          <span id="delSure" hidden><span class="sm">Delete <b>${esc(nice(r.name))}</b> for good?</span> <button class="btn s bad solid" id="delGo" type="button">Yes, delete</button> <button class="btn soft s" id="delNo" type="button">Keep it</button></span></div></section></div>`;
    MAIN.innerHTML = `<div class="ed tabbed">${edTop(r, tab)}<div class="edpage">${body}</div></div>`;
    const collect = () => {
      const o = {};
      MAIN.querySelectorAll('#setForm [data-k]').forEach(el => { const v = el.value.trim(); if (v) o[el.dataset.k] = v; });
      if (o.tags) o.tags = o.tags.split(',').map(x => x.trim()).filter(Boolean);
      ['stop_after_errors', 'runs_per_day', 'keep_runs_days', 'keep_runs'].forEach(k => { if (o[k]) o[k] = parseInt(o[k], 10) || o[k]; });
      if (o.minutes_saved) o.minutes_saved = parseFloat(o.minutes_saved) || o.minutes_saved;
      o.description = (MAIN.querySelector('#setForm [data-k="description"]') || {}).value || '';
      o.shared_with = Array.from(MAIN.querySelectorAll('[data-member]:checked')).map(x => x.dataset.member);
      return o;
    };
    const saveSet = async () => {
      const b = $('#setSave'); b.disabled = true;
      try { const nr = await api('PUT', `/api/route/routes/${enc(r.id)}/settings`, collect()); Object.assign(r, nr); toast('Settings saved.'); }
      catch (err) { toast(err.message, true); }
      b.disabled = false;
    };
    $('#setForm').addEventListener('submit', e => { e.preventDefault(); saveSet(); });
    MAIN.querySelectorAll('[data-member]').forEach(x => x.addEventListener('change', saveSet));
    MAIN.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => navigator.clipboard.writeText(b.dataset.copy).then(() => toast('Copied.'), () => toast('Copy it by hand.', true))));
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
    const sm = $('#shareMake');
    if (sm) sm.addEventListener('click', async () => { try { r.share = await api('POST', `/api/route/routes/${enc(r.id)}/share`); viewRouteTab(r, 'settings'); } catch (err) { toast(err.message, true); } });
    const ss = $('#shareStop');
    if (ss) ss.addEventListener('click', async () => { try { await api('DELETE', `/api/route/routes/${enc(r.id)}/share`); r.share = {on: false}; toast('The link has stopped.'); viewRouteTab(r, 'settings'); } catch (err) { toast(err.message, true); } });
    $('#expFile').addEventListener('click', async () => {
      try {
        const d = await api('GET', `/api/route/routes/${enc(r.id)}/export`);
        const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], {type: 'application/json'}));
        a.download = `${r.name}.route.json`; document.body.appendChild(a); a.click(); a.remove();
      } catch (err) { toast(err.message, true); }
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
  async function versionsTab(r) {
    const v = await api('GET', `/api/route/routes/${enc(r.id)}/versions`);
    const rows = (v.versions || []).map(x => `<tr><td class="nw">${esc(at(x.at))}</td><td>${esc(x.change)}${x.note ? `<div class="mut sm">${esc(x.note)}</div>` : ''}</td>
      <td class="num">${fmtN(x.steps)}</td><td class="c-act">${x.current ? '<span class="chipst">Now</span>' : `<button class="btn soft s" type="button" data-restore="${esc(x.id)}">Bring back</button>`}</td></tr>`).join('');
    MAIN.innerHTML = `<div class="ed tabbed">${edTop(r, 'versions')}<div class="edpage"><section class="card flat">
      <div class="hd"><h2>Versions</h2><span class="sp"></span><span class="mut sm">Every save is kept (the last 50). Bringing one back saves it as a new version.</span></div>
      ${rows ? `<div class="tw"><table class="rt"><thead><tr><th>Saved</th><th>What changed</th><th>Steps</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty">No versions yet - one is kept every time the route is saved.</div>'}
      </section></div></div>`;
    MAIN.querySelectorAll('[data-restore]').forEach(b => b.addEventListener('click', async () => {
      if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = 'Bring this one back?'; return; }
      b.disabled = true;
      try { const nr = await api('POST', `/api/route/routes/${enc(r.id)}/versions/${enc(b.dataset.restore)}/restore`); toast('Brought back. It is the newest version now.'); await versionsTab(nr); }
      catch (err) { toast(err.message, true); b.disabled = false; }
    }));
  }
  // v0.999.246 ROUTE R7: her variables ({{env.NAME}}) and saved sign-ins, for every route
  async function viewVariables() {
    shell(false); setNav('variables');
    const v = await api('GET', '/api/route/variables');
    const rows = (v.variables || []).map(x => `<tr><td class="c-name mono">${esc(x.name)}</td><td class="mono sm">${esc(typeof x.value === 'string' ? x.value : JSON.stringify(x.value)).slice(0, 200)}</td>
      <td class="mut sm">${esc(x.note)}</td><td class="c-act"><button class="btn soft s" type="button" data-vedit="${esc(x.name)}">Change</button><button class="btn soft s bad" type="button" data-vdel="${esc(x.name)}">Delete</button></td></tr>`).join('');
    MAIN.innerHTML = `<div class="top"><h1>Variables</h1></div><p class="lead">Values every route can read, like <code>{{env.SHOP_NAME}}</code>. Not for passwords or keys - those are sign-ins.</p>
      <section class="card"><form id="varForm" class="pform"><div class="two">${field('Name', '', {k: 'vname', ref: false, mono: true, ph: 'SHOP_NAME'})}${field('Value', '', {k: 'vvalue', ref: false})}</div>
        ${field('Note (optional)', '', {k: 'vnote', ref: false})}<div class="crow"><button class="btn s" type="submit">Save the variable</button></div></form></section>
      <section class="card flat">${rows ? `<div class="tw"><table class="rt"><thead><tr><th>Name</th><th>Value</th><th>Note</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty">No variables yet.</div>'}</section>`;
    const val = k => MAIN.querySelector(`[data-k="${k}"]`);
    $('#varForm').addEventListener('submit', async e => {
      e.preventDefault();
      const name = val('vname').value.trim(); let value = val('vvalue').value;
      if (/^-?\d+(\.\d+)?$/.test(value.trim())) value = Number(value);
      try { await api('PUT', `/api/route/variables/${enc(name)}`, {value, note: val('vnote').value}); toast('Saved.'); viewVariables(); } catch (err) { toast(err.message, true); }
    });
    MAIN.querySelectorAll('[data-vedit]').forEach(b => b.addEventListener('click', () => {
      const x = v.variables.find(y => y.name === b.dataset.vedit); val('vname').value = x.name;
      val('vvalue').value = typeof x.value === 'string' ? x.value : JSON.stringify(x.value); val('vnote').value = x.note; val('vvalue').focus();
    }));
    MAIN.querySelectorAll('[data-vdel]').forEach(b => b.addEventListener('click', async () => {
      if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = 'Delete it?'; return; }
      try { await api('DELETE', `/api/route/variables/${enc(b.dataset.vdel)}`); viewVariables(); } catch (err) { toast(err.message, true); }
    }));
  }
  const CREDW = {bearer: 'A token (Bearer)', header: 'A key in a header', basic: 'A user and a password', query: 'A key in the address', oauth2: 'OAuth2 (app sign-in)'};
  async function viewSignins(kind) {
    shell(false); setNav('signins');
    const c = await api('GET', '/api/route/credentials');
    kind = kind || 'bearer';
    const F = {bearer: [['token', 'The token', 1]], header: [['header', 'Header name'], ['value', 'The key', 1]], basic: [['user', 'User'], ['password', 'Password', 1]],
      query: [['param', 'Its name in the address'], ['value', 'The key', 1]], oauth2: [['token_url', 'Token address (https://)'], ['client_id', 'Client id'], ['client_secret', 'Client secret', 1], ['scope', 'Scope (optional)']]}[kind];
    const rows = (c.credentials || []).map(x => `<tr><td class="c-name mono">${esc(x.name)}</td><td>${esc(CREDW[x.kind] || x.kind)}</td><td class="mono sm">${esc(x.host)}</td>
      <td class="mono sm">${esc(x.hint)}</td><td class="mut sm">${x.used_at ? 'Used ' + esc(at(x.used_at)) : 'Not used yet'}</td><td class="c-act"><button class="btn soft s bad" type="button" data-cdel="${esc(x.name)}">Delete</button></td></tr>`).join('');
    MAIN.innerHTML = `<div class="top"><h1>Sign-ins</h1></div><p class="lead">For web request steps that need a key. Saved locked, never shown again (only the last 4), never seen by the AI, and only ever sent to the site you name.</p>
      <section class="card"><form id="credForm" class="pform" autocomplete="off">
        <div class="two">${field('Name', '', {k: 'name', ref: false, mono: true, ph: 'SHOP_API'})}${field('Kind', kind, {k: 'kind', options: Object.entries(CREDW)})}</div>
        ${field('For this site only', '', {k: 'host', ref: false, mono: true, ph: 'api.example.com'})}
        ${F.map(([k, lab, secret]) => `<div class="fld"><label for="cr_${k}">${esc(lab)}</label><div class="fc"><input id="cr_${k}" data-k="${k}" ${secret ? 'type="password" autocomplete="new-password"' : ''} class="mono"></div></div>`).join('')}
        <div class="crow"><button class="btn s" type="submit">Save the sign-in</button></div></form></section>
      <section class="card flat">${rows ? `<div class="tw"><table class="rt"><thead><tr><th>Name</th><th>Kind</th><th>Site</th><th>Key</th><th>Last use</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty">No sign-ins yet.</div>'}</section>`;
    MAIN.querySelector('#credForm [data-k="kind"]').addEventListener('change', e => viewSignins(e.target.value));
    $('#credForm').addEventListener('submit', async e => {
      e.preventDefault();
      const b = {}; MAIN.querySelectorAll('#credForm [data-k]').forEach(el => { b[el.dataset.k] = el.value.trim(); });
      try { await api('POST', '/api/route/credentials', b); toast('Saved.'); viewSignins(kind); } catch (err) { toast(err.message, true); }
    });
    MAIN.querySelectorAll('[data-cdel]').forEach(b => b.addEventListener('click', async () => {
      if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = 'Delete it?'; return; }
      try { await api('DELETE', `/api/route/credentials/${enc(b.dataset.cdel)}`); viewSignins(kind); } catch (err) { toast(err.message, true); }
    }));
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
    const [a, b, c, d] = h.split('/');
    if (ED && ED.dirty && !(a === 'r' && decodeURIComponent(b || '') === ED.r.id && (!c || c === 'debug')) && LEAVE_OK !== h) {
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
      else if (a === 'r' && b) await viewEditor(decodeURIComponent(b), c || '', d ? decodeURIComponent(d) : '');
      else if (a === 'needs') await viewNeeds();
      else if (a === 'runs') await viewRuns(b === 'find' ? '' : (b || ''), b === 'find' ? decodeURIComponent(c || '') : '');
      else if (a === 'insights') await viewInsights(b || '');
      else if (a === 'import') await viewImport();
      else if (a === 'run' && b) await viewRun(decodeURIComponent(b));
      else if (a === 'templates') await viewTemplates();
      else if (a === 'variables') await viewVariables();
      else if (a === 'signins') await viewSignins(b || '');
      else await viewHome();
    } catch (err) { shell(false); MAIN.innerHTML = `<div class="errbox">${esc(err.message)}</div>`; }
    needCount();
  }
  window.addEventListener('hashchange', route);
  route();
})();
