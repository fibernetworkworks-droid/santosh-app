/* v0.999.87 HOOLA ROUTE - her automations as one page (owner: "GO" on the Hoola Route panel canvas).

   Views (hash routes): #/ home (ask in words, numbers, Needs you, your routes) · #/routes all routes · #/r/<id> one route
   (its steps as a flow, the router's routes with their filters, step details, recent runs) · #/runs every run ·
   #/run/<id> one run's step-by-step log · #/templates ready starting points.
   The engine is DHARA; this page only reads it and relays HER taps (switch, run once, approve, stop, retry).
   Building or changing a route is a chat job: her words go to Hoola in a real conversation (it calls dhara_save).
   Global by design: times show in her browser's own time zone; nothing on the page assumes a country. */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const fmtN = v => Number(v || 0).toLocaleString();
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  if (!TOKEN) { location.replace('/console/'); return; }
  const MAIN = $('#main');

  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) { throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`); }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = d => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>', play: '<path d="M7 5l12 7-12 7z"/>', route: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/><path d="M8 6h3a5 5 0 0 1 5 5M8 18h3a5 5 0 0 0 5-5"/>',
    back: '<path d="M15 6l-6 6 6 6"/>', check: '<path d="M5 12l5 5 9-10"/>', http: '<path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c.01-.7.2-1.4.57-2"/><path d="m6 17 3.13-5.78c.53-.97.1-2.18-.5-3.1a4 4 0 1 1 6.89-4.06"/><path d="m12 6 3.13 5.73C15.66 12.7 16.9 13 18 13a4 4 0 0 1 0 8"/>',
    code: '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4"/>', wait: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', notify: '<path d="M4 5h16v11H9l-5 4z"/>',
    router: '<path d="M4 12h6M10 12l6-6M10 12l6 6M10 12h10"/>', filter: '<path d="M4 5h16l-6 8v6l-4-2v-4z"/>', loop: '<path d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3M18 3v4h-4M6 21v-4h4"/>',
    set: '<path d="M4 7h16M4 12h10M4 17h7"/>', store: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>'};
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
  function appTile(a) {
    a = a || {};
    if (a.kind === 'hoola') return `<span class="ap hoola" title="Hoola">${MARK('#FFFFFF')}</span>`;
    if (a.kind === 'app' && a.slug) return `<span class="ap" title="${esc(appName(a.slug))}"><img src="/api/logo/cmp/${enc(a.slug)}" alt="${esc(appName(a.slug))}" data-fb="${esc(appName(a.slug).split(' ').map(w => w[0]).join('').slice(0, 2))}"></span>`;
    if (a.kind === 'approval') return `<span class="ap dark" title="Your approval">${svg(IC.check)}</span>`;
    if (a.kind === 'router') return `<span class="ap dark" title="Router">${svg(IC.route)}</span>`;
    return `<span class="ap" title="${esc(a.kind || '')}">${svg(IC[a.kind] || IC.set)}</span>`;
  }
  const PILL = {ok: 'ok', running: 'v', waiting: 'warn', error: 'bad', stopped: 'bad', off: ''};
  const RUNPILL = {done: ['ok', 'Done'], failed: ['bad', 'Failed'], incomplete: ['bad', 'Incomplete'], waiting_approval: ['warn', 'Waiting for you'],
    sleeping: ['v', 'Waiting'], running: ['v', 'Running'], queued: ['v', 'Queued'], stopped: ['', 'Stopped']};
  const runPill = st => { const [c, t] = RUNPILL[st] || ['', st]; return `<span class="pill ${c}"><span class="dot"></span>${esc(t)}</span>`; };
  const when = ts => { if (!ts) return ''; const d = new Date(Number(ts) * 1000), m = Math.round((Date.now() - d) / 60000);
    if (m < 1) return 'just now'; if (m < 60) return m + ' min ago'; if (m < 1440) return Math.floor(m / 60) + ' h ago';
    return d.toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); };
  const at = ts => ts ? new Date(Number(ts) * 1000).toLocaleString(undefined, {weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}) : '';

  // ---------------------------------------------------------------- ask in words -> a real chat with Hoola
  async function askHoola(text, change) {
    text = S(text).trim();
    if (!text) return;
    const c = await api('POST', '/api/conversations');
    const tz = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch { return ''; } })();
    const words = (change ? `${text}\n(Change that saved Hoola Route with dhara_save; keep everything else as it is.)`
      : `Build me a Hoola Route (a saved automation, dhara_save) for this: ${text}`) +
      (tz ? `\n\nMy time zone is ${tz}.` : '') +
      `\nUse my own apps, my time zone and my currency. Show me the steps first and test it before you switch it on.`;
    await api('POST', `/api/conversations/${enc(c.id)}/messages`, {text: words});
    location.assign('/console/c/' + enc(c.id));
  }

  function setNav(k) {
    document.querySelectorAll('.side [data-nav]').forEach(a => a.setAttribute('aria-current', a.dataset.nav === k ? 'page' : 'false'));
  }
  let SUM = null;
  async function needCount() {
    try { SUM = await api('GET', '/api/route/summary'); const n = $('#needCount'); n.textContent = SUM.needs_count; n.hidden = !SUM.needs_count; } catch {}
  }

  // ---------------------------------------------------------------- tables
  const nice = n => S(n).replace(/_/g, ' ');
  const tog = (id, on, name) => `<button class="tog" role="switch" aria-checked="${on}" aria-label="${on ? 'Switch off' : 'Switch on'} ${esc(nice(name))}" data-switch="${esc(id)}" data-name="${esc(nice(name))}"><span></span></button>`;
  // tables become cards on a phone: every cell carries its own label (data-l), the CSS shows it there
  function routeRows(routes, empty) {
    if (!routes.length) return `<div class="empty">${empty || 'No routes yet. Describe one above, or start from a template.'}</div>`;
    return `<div class="tw"><table class="rt"><thead><tr><th>On</th><th>Route</th><th>Apps</th><th>Runs when</th><th>Last run</th><th class="nw">Runs in 30 days</th><th>Status</th></tr></thead><tbody>${
      routes.map(r => `<tr>
        <td class="c-on">${tog(r.id, r.enabled, r.name)}</td>
        <td class="c-name"><a class="rn" href="#/r/${enc(r.id)}">${esc(nice(r.name))}</a><div class="mut sm">${esc(r.folder || r.description || '')}</div></td>
        <td data-l="Apps"><div class="apps">${(r.apps || []).map(appTile).join('') || '<span class="mut sm">Hoola only</span>'}</div></td>
        <td data-l="Runs when">${esc(r.when)}</td>
        <td data-l="Last run" class="nw">${r.last_run ? esc(when(r.last_run.at)) : '<span class="mut">Never</span>'}</td>
        <td data-l="Runs in 30 days" class="num">${fmtN(r.runs_30d)}</td>
        <td data-l="Status"><span class="pill ${PILL[r.status.key] || ''}"><span class="dot"></span>${esc(r.status.text)}</span></td></tr>`).join('')}</tbody></table></div>`;
  }
  function needsList(items) {
    if (!items.length) return `<div class="need"><span class="t mut">Nothing needs you right now.</span></div>`;
    return items.map(n => `<div class="need">
      <span class="pill ${n.kind === 'approval' ? 'warn' : 'bad'}"><span class="dot"></span>${n.kind === 'approval' ? 'Approval' : n.kind === 'stopped' ? 'Switched off' : n.kind === 'incomplete' ? 'Incomplete' : 'Failed'}</span>
      <span class="t"><b>${esc(S(n.route).replace(/_/g, ' '))}</b> · ${esc(n.kind === 'approval' ? n.text : human(n.text))}</span>
      <span class="acts">${n.kind === 'approval' ? `<button class="btn s" data-act="approve" data-run="${esc(n.run_id)}">Approve</button><button class="btn s soft" data-act="stop" data-run="${esc(n.run_id)}">Stop the run</button>`
        : n.kind === 'stopped' ? `<a class="btn s soft" href="#/r/${enc(n.route_id)}">Open</a><button class="btn s" data-switch="${esc(n.route_id)}" aria-checked="false" data-name="${esc(nice(n.route))}">Switch back on</button>`
        : `<a class="btn s soft" href="#/run/${enc(n.run_id)}">See why</a>`}</span></div>`).join('');
  }

  // ---------------------------------------------------------------- views
  const GREET = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; };
  async function viewHome() {
    setNav('home');
    const [sum, list] = await Promise.all([api('GET', '/api/route/summary'), api('GET', '/api/route/routes')]);
    SUM = sum;
    MAIN.innerHTML = `
      <section class="hero">
        <h1>${GREET()}. What should run by itself?</h1>
        <p class="lead">Describe a job you repeat, in one line and in any language. Hoola builds the route, tests it on your real data, and nothing switches on until you say so.</p>
        <form class="comp" id="askForm">
          <label><span class="sr" hidden>Describe a route</span><textarea id="askText" rows="2" placeholder="Every time a new order comes in, send the customer a WhatsApp receipt and add a row to my sheet…" aria-label="Describe a route"></textarea></label>
          <div class="crow"><a class="sb" href="#/templates">From a template</a><span class="sp"></span><button class="go" type="submit" aria-label="Build the route" id="askGo" disabled>${svg(IC.up)}</button></div>
        </form>
        <div class="chips" id="chips">${['Shop orders', 'Invoices and payments', 'Reminders', 'New leads', 'Reviews', 'Weekly reports'].map(c => `<button class="chip" type="button" data-chip="${esc(c)}">${esc(c)}</button>`).join('')}</div>
      </section>
      <div class="kpis">${(() => {
        const auto = list.routes.filter(r => r.trigger !== 'manual' && r.enabled).length;
        const pc = n => sum.routes_total ? Math.round(100 * n / sum.routes_total) : 0;
        return `<div class="card kpi"><b>${fmtN(sum.routes_on)}</b><span>of ${fmtN(sum.routes_total)} routes switched on</span><div class="bar"><i style="width:${pc(sum.routes_on)}%"></i></div></div>
        <div class="card kpi"><b>${fmtN(auto)}</b><span>start by themselves</span><div class="bar"><i style="width:${pc(auto)}%"></i></div></div>
        <div class="card kpi"><b>${fmtN(sum.runs_today)}</b><span>runs in the last 24 hours</span></div>
        <a class="card kpi${sum.needs_count ? ' hot' : ''}" href="#/runs"><b>${fmtN(sum.needs_count)}</b><span>${sum.needs_count === 1 ? 'needs you' : 'need you'}</span></a>`; })()}
      </div>
      <section class="card" aria-label="Needs you"><div class="hd"><h2>Needs you</h2><span class="sp"></span><span class="mut sm">Nothing big runs without your yes</span></div>${needsList(sum.needs_you)}</section>
      <section class="card" aria-label="Your routes"><div class="hd"><h2>Your routes</h2><span class="sp"></span><a class="btn soft s" href="#/routes">All routes</a></div>${routeRows(list.routes.slice(0, 8))}</section>`;
    const ta = $('#askText'), go = $('#askGo');
    ta.addEventListener('input', () => { go.disabled = !ta.value.trim(); });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#askForm').requestSubmit(); } });
    $('#askForm').addEventListener('submit', async e => {
      e.preventDefault(); go.disabled = true;
      try { await askHoola(ta.value); } catch (err) { toast(err.message, true); go.disabled = false; }
    });
    $('#chips').addEventListener('click', e => { const b = e.target.closest('[data-chip]'); if (!b) return;
      ta.value = `${b.dataset.chip}: `; ta.focus(); go.disabled = false; });
    needCount();
  }

  async function viewRoutes() {
    setNav('routes');
    const list = await api('GET', '/api/route/routes');
    const folders = [...new Set(list.routes.map(r => r.folder).filter(Boolean))];
    MAIN.innerHTML = `<div class="top"><h1>All routes</h1><span class="sp"></span><a class="btn" href="#/" id="newR">New route</a></div>
      <div class="filt"><input type="search" id="rq" placeholder="Find a route" aria-label="Find a route">
      ${folders.length ? `<div class="chips left" id="fchips"><button class="chip" aria-pressed="true" data-f="">All</button>${folders.map(f => `<button class="chip" aria-pressed="false" data-f="${esc(f)}">${esc(f)}</button>`).join('')}</div>` : ''}</div>
      <section class="card" id="rtable">${routeRows(list.routes)}</section>`;
    let folder = '';
    const draw = () => { const q = $('#rq').value.trim().toLowerCase();
      const rs = list.routes.filter(r => (!folder || r.folder === folder) && (!q || (nice(r.name) + ' ' + r.description).toLowerCase().includes(q)));
      $('#rtable').innerHTML = routeRows(rs, list.routes.length ? 'No route matches.' : ''); };
    $('#rq').addEventListener('input', draw);
    const fc = $('#fchips');
    if (fc) fc.addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (!b) return;
      fc.querySelectorAll('[data-f]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); folder = b.dataset.f; draw(); });
    $('#newR').addEventListener('click', () => setTimeout(() => { const t = $('#askText'); if (t) t.focus(); }, 80));
  }

  // one step as a node card
  function stepWords(s) {
    const t = s.type;
    if (t === 'tool') return [s.app && s.app.kind === 'app' ? appName(s.app.slug) : 'Hoola', S(s.name).replace(/_/g, ' ')];
    if (t === 'http') return ['Web request', `${S(s.method || 'GET')} ${S(s.url).replace(/^https?:\/\//, '').slice(0, 30)}`];
    if (t === 'code') return ['Code', 'Python, in a locked sandbox'];
    if (t === 'wait') return ['Wait', s.duration_s ? `${s.duration_s} s` : `until ${S(s.until)}`];
    if (t === 'notify') return ['Tell you', S(s.text).slice(0, 40)];
    if (t === 'approval') return ['Your approval', S(s.question).slice(0, 40)];
    if (t === 'set') return ['Set a value', S(s.name)];
    if (t === 'filter') return ['Filter', 'Stop here unless it passes'];
    if (t === 'condition') return ['If / else', s.filter ? fltWords(s.filter).slice(0, 40) : `${S(s.left)} ${OPW[s.op] || s.op || ''} ${S(s.right)}`.slice(0, 40)];
    if (t === 'loop') return ['Repeat for each', S(s.items).slice(0, 34)];
    return [t, ''];
  }
  let STEPS = {};
  function nodeHtml(s, first) {
    STEPS[s.id] = s;
    const [b, sm] = stepWords(s);
    const oe = s.on_error ? `<span class="oe">${esc(s.on_error.do === 'break' ? `retry ${s.on_error.retries}×` : s.on_error.do)}</span>` : '';
    return `<button type="button" class="node" data-step="${esc(s.id)}" aria-pressed="false">${first ? '<span class="start">Start</span>' : ''}${appTile(s.app)}<span><b>${esc(b)}</b><small>${esc(sm)}</small></span>${oe}</button>`;
  }
  function lane(steps, firstLane) {
    const parts = [];
    (steps || []).forEach((s, i) => {
      if (i) parts.push('<span class="link"></span>');
      const line = (label, title, steps) => `<div class="rline"><span class="ask rflt" title="${esc(title)}">${esc(label)}</span><span class="link"></span>${
        steps && steps.length ? lane(steps) : '<span class="mut sm none">Nothing</span>'}</div>`;
      if (s.type === 'router') {
        STEPS[s.id] = s;
        const rs = (s.routes || []).map((rt, j) => line(rt.label || ('Route ' + (j + 1)), fltWords(rt.filter), rt.steps));
        if (s.fallback && s.fallback.length) rs.push(line('Anything else', 'When no route above matched', s.fallback));
        parts.push(`<div class="router">${firstLane && i === 0 ? '<span class="start">Start</span>' : ''}<button type="button" class="rhub" data-step="${esc(s.id)}" aria-label="Router: ${(s.routes || []).length} routes, show its settings" title="Router">${svg(IC.route)}</button><div class="routes">${rs.join('')}</div></div>`);
      } else if (s.type === 'condition') {   // v0.999.128: both ways of an if / else are drawn (they were hidden)
        STEPS[s.id] = s;
        const test = s.filter ? fltWords(s.filter) : `${S(s.left)} ${OPW[s.op] || s.op || ''} ${S(s.right)}`;
        parts.push(`<div class="router">${nodeHtml(s, firstLane && i === 0)}<div class="routes">${line('If yes', test, s.then)}${line('If no', 'Otherwise', s.else)}</div></div>`);
      } else if (s.type === 'loop') {        // v0.999.128: the steps a loop repeats are drawn inside it
        parts.push(`<div class="loopbox">${nodeHtml(s, firstLane && i === 0)}<div class="lbody"><span class="mut sm">For each item</span>${lane(s.body)}</div></div>`);
      } else parts.push(nodeHtml(s, firstLane && i === 0));
    });
    return `<div class="lane">${parts.join('')}</div>`;
  }
  const OPW = {exists: 'exists', not_exists: 'does not exist', empty: 'is empty', not_empty: 'is not empty', eq: '=', ne: '≠', contains: 'contains',
    not_contains: 'does not contain', starts_with: 'starts with', ends_with: 'ends with', matches: 'matches', gt: '>', gte: '≥', lt: '<', lte: '≤',
    between: 'between', before: 'before', after: 'after', is_true: 'is true', is_false: 'is false', in: 'is one of', not_in: 'is not one of',
    length_eq: 'length =', length_gt: 'length >', length_lt: 'length <'};
  function fltWords(f) {
    if (!f) return 'Always';
    if (f.all) return f.all.map(fltWords).join(' AND ');
    if (f.any) return '(' + f.any.map(fltWords).join(' OR ') + ')';
    const r = Array.isArray(f.right) ? f.right.join(' – ') : S(f.right);
    return `${S(f.left).replace(/\{\{\s*|\s*\}\}/g, '')} ${OPW[f.op] || f.op}${r ? ' ' + r : ''}`;
  }
  function stepDetail(s) {
    if (!s) return '<div class="mut">Pick a step to see its settings.</div>';
    const KIND = {tool: 'Uses a tool', http: 'Web request', code: 'Code', wait: 'Wait', notify: 'Tells you', approval: 'Asks for your OK',
      set: 'Sets a value', filter: 'Filter', condition: 'If / else', loop: 'Repeat for each', router: 'Router'};
    const DO = {resume: 'Carry on with the next step', ignore: 'Skip it and carry on', commit: 'Stop here and keep what was done',
      rollback: 'Stop the run', tell: 'Tell you and stop the run'};
    const rows = [['Kind', KIND[s.type] || s.type], ['Step name', s.id]];
    if (s.name) rows.push([s.type === 'set' ? 'Value name' : 'Tool', s.name]);
    if (s.question) rows.push(['Question', s.question]);
    if (s.text) rows.push(['Message', s.text]);
    if (s.url) rows.push(['Address', `${S(s.method || 'GET')} ${s.url}`]);
    if (s.value !== undefined) rows.push(['Value', typeof s.value === 'string' ? s.value : JSON.stringify(s.value)]);
    if (s.items !== undefined) rows.push(['For each item in', typeof s.items === 'string' ? s.items : JSON.stringify(s.items)]);
    if (s.duration_s) rows.push(['Waits', `${s.duration_s} seconds`]);
    if (s.until) rows.push(['Waits until', s.until]);
    if (s.filter) rows.push([s.type === 'condition' ? 'Yes when' : 'Goes on only when', fltWords(s.filter)]);
    if (s.type === 'router') (s.routes || []).forEach((rt, j) => rows.push([rt.label || 'Route ' + (j + 1), fltWords(rt.filter)]));
    rows.push(['If it fails', !s.on_error ? 'The run stops and shows you why'
      : s.on_error.do === 'break' ? `Try again ${s.on_error.retries} times, ${s.on_error.wait_min} min apart, then keep it in Incomplete runs` : (DO[s.on_error.do] || s.on_error.do)]);
    const rest = {}; for (const k of ['args', 'body', 'code']) if (s[k] !== undefined && s[k] !== null && s[k] !== '') rest[k] = s[k];
    return rows.map(([k, v]) => `<div class="kv"><span class="k">${esc(k)}</span><span class="v">${esc(v)}</span></div>`).join('') +
      Object.entries(rest).map(([k, v]) => `<div class="mut sm pk">${{args: 'What it sends', body: 'Body', code: 'Code'}[k]}</div><pre>${esc(typeof v === 'string' ? v : JSON.stringify(v, null, 2))}</pre>`).join('');
  }
  async function viewRoute(id) {
    setNav('routes');
    const [r, runs] = await Promise.all([api('GET', `/api/route/routes/${enc(id)}`), api('GET', `/api/route/runs?workflow_id=${enc(id)}&limit=10`)]);
    STEPS = {};
    const sp = r.trigger_spec || {}, st = r.settings || {};
    MAIN.innerHTML = `
      <div class="rhead"><a class="btn soft s ib" href="#/routes" aria-label="Back to all routes">${svg(IC.back)}</a>
        <div class="rh-t"><h1 class="rtitle">${esc(nice(r.name))}</h1>
          <div class="rh-m"><span class="pill ${PILL[r.status.key] || ''}"><span class="dot"></span>${esc(r.status.text)}</span>${r.description ? `<span class="mut sm">${esc(r.description)}</span>` : ''}</div></div>
        <div class="rh-a"><label class="onl">${tog(r.id, r.enabled, r.name)}<span id="onWord">${r.enabled ? 'On' : 'Off'}</span></label>
          <button class="btn soft" id="changeIt">Change it</button><button class="btn" id="runOnce">${svg(IC.play)}Run once</button></div></div>
      <form class="card chg" id="chgBox" hidden><label class="sm" for="chgText"><b>What should change?</b> Hoola changes the route in a chat and shows you the new steps first.</label>
        <textarea id="chgText" rows="2" placeholder="For example: also email me a copy, and skip orders under 100"></textarea>
        <div class="crow"><span class="sp"></span><button type="button" class="btn soft s" id="chgCancel">Cancel</button><button class="btn s" id="chgGo" disabled>Ask Hoola</button></div></form>
      <section class="flow" aria-label="The route's steps">${lane(r.graph, true)}</section>
      <div class="detail">
        <section class="card"><div class="hd"><h2>Step</h2></div><div id="stepBox">${stepDetail(null)}</div></section>
        <section class="card"><div class="hd"><h2>How it runs</h2></div>
          <div class="kv"><span class="k">Runs when</span><span>${esc(r.when)}</span></div>
          ${sp.timezone || st.timezone ? `<div class="kv"><span class="k">Time zone</span><span>${esc(sp.timezone || st.timezone)}</span></div>` : ''}
          ${sp.quiet ? `<div class="kv"><span class="k">Quiet hours</span><span>${esc(sp.quiet.from)}–${esc(sp.quiet.to)}</span></div>` : ''}
          ${sp.skip_holidays ? `<div class="kv"><span class="k">Skips holidays of</span><span>${esc(sp.skip_holidays)}</span></div>` : ''}
          ${r.next_due_at ? `<div class="kv"><span class="k">Next run</span><span>${esc(at(r.next_due_at))}</span></div>` : ''}
          <div class="kv"><span class="k">Switch off after</span><span>${st.stop_after_errors ? esc(st.stop_after_errors) + ' failed runs in a row' : 'Never (not set)'}</span></div>
          ${st.error_route ? `<div class="kv"><span class="k">Error route</span><span>${esc(st.error_route)}</span></div>` : ''}
          ${st.runs_per_day ? `<div class="kv"><span class="k">Runs per day, at most</span><span>${esc(st.runs_per_day)}</span></div>` : ''}
          ${r.trigger === 'webhook' ? `<div class="kv"><span class="k">Address that starts it</span><span class="v" id="addrBox"><span class="mut">Kept secret. Make a new one to see it.</span><br><button class="btn soft s" id="addrNew" type="button">Make a new address</button></span></div>` : ''}
          <div class="kv"><span class="k">Money and sending</span><span>Always wait for your tap</span></div></section>
      </div>
      <section class="card"><div class="hd"><h2>Recent runs</h2><span class="sp"></span><a class="btn soft s" href="#/runs">All runs</a></div>${runRows(runs.runs, true)}</section>
      <section class="card danger"><div class="hd"><h2>Delete this route</h2></div>
        <p class="mut sm" id="delWords">Its steps and its run history go. This cannot be undone. A route with a run still going cannot be deleted.</p>
        <div class="crow"><button class="btn soft bad s" id="delAsk" type="button">Delete route</button>
          <span id="delSure" hidden><span class="sm">Delete <b>${esc(nice(r.name))}</b> for good?</span> <button class="btn s bad solid" id="delGo" type="button">Yes, delete</button> <button class="btn soft s" id="delNo" type="button">Keep it</button></span></div></section>`;
    MAIN.querySelector('.flow').addEventListener('click', e => {
      const b = e.target.closest('[data-step]'); if (!b) return;
      MAIN.querySelectorAll('.node').forEach(n => n.setAttribute('aria-pressed', String(n === b)));
      $('#stepBox').innerHTML = stepDetail(STEPS[b.dataset.step]);
    });
    $('#runOnce').addEventListener('click', async () => {
      try { const x = await api('POST', `/api/route/routes/${enc(id)}/run`); toast('Started.'); location.hash = '#/run/' + enc(x.run_id); }
      catch (e) { toast(e.message, true); }
    });
    const box = $('#chgBox'), ct = $('#chgText'), cg = $('#chgGo');
    $('#changeIt').addEventListener('click', () => { box.hidden = false; ct.focus(); });
    $('#chgCancel').addEventListener('click', () => { box.hidden = true; ct.value = ''; cg.disabled = true; });
    ct.addEventListener('input', () => { cg.disabled = !ct.value.trim(); });
    box.addEventListener('submit', async e => {
      e.preventDefault(); cg.disabled = true;
      try { await askHoola(`Change my route "${r.name}": ${ct.value.trim()}`, true); } catch (err) { toast(err.message, true); cg.disabled = false; }
    });
    const an = $('#addrNew');
    if (an) an.addEventListener('click', async () => {
      if (an.dataset.sure !== '1') { an.dataset.sure = '1'; an.textContent = 'The old address stops working. Make a new one?'; return; }
      an.disabled = true;
      try {
        const a = await api('POST', `/api/route/routes/${enc(id)}/address`);
        const url = /^https?:/.test(a.url) ? a.url : location.origin + a.url;
        $('#addrBox').innerHTML = `<code class="addr">${esc(url)}</code><br><span class="mut sm">${esc(a.note)}</span><br><button class="btn soft s" type="button" id="addrCopy">Copy</button>`;
        $('#addrCopy').addEventListener('click', () => navigator.clipboard.writeText(url).then(() => toast('Copied.'), () => toast('Copy it by hand.', true)));
      } catch (err) { toast(err.message, true); an.disabled = false; }
    });
    $('#delAsk').addEventListener('click', () => { $('#delSure').hidden = false; $('#delAsk').hidden = true; });
    $('#delNo').addEventListener('click', () => { $('#delSure').hidden = true; $('#delAsk').hidden = false; });
    $('#delGo').addEventListener('click', async () => {
      $('#delGo').disabled = true;
      try { await api('DELETE', `/api/route/routes/${enc(id)}`, {confirm: r.name}); toast('Deleted.'); location.hash = '#/routes'; }
      catch (err) { toast(err.message, true); $('#delGo').disabled = false; }
    });
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
    setNav('runs');
    const q = filter ? `&status=${enc(filter)}` : '';
    const runs = await api('GET', `/api/route/runs?limit=60${q}`);
    const F = [['', 'All'], ['waiting_approval', 'Waiting for you'], ['incomplete', 'Incomplete'], ['failed', 'Failed'], ['done', 'Done']];
    MAIN.innerHTML = `<div class="top"><h1>Runs</h1></div>
      <div class="chips left">${F.map(([k, n]) => `<a class="chip" aria-pressed="${(filter || '') === k}" href="#/runs${k ? '/' + k : ''}">${esc(n)}</a>`).join('')}</div>
      <section class="card">${runRows(runs.runs, false, filter ? 'No runs in this list.' : 'No runs yet. A route runs when its time comes, when data arrives, or when you tap Run once.')}</section>`;
  }
  const pretty = v => { try { return JSON.stringify(JSON.parse(v), null, 2); } catch { return S(v); } };
  async function viewRun(id) {
    setNav('runs');
    const x = await api('GET', `/api/route/runs/${enc(id)}`);
    const acts = [];
    if (x.status === 'waiting_approval') acts.push('<button class="btn" data-act="approve" data-run="' + esc(x.id) + '">Approve</button>');
    if (['queued', 'running', 'sleeping', 'waiting_approval'].includes(x.status)) acts.push('<button class="btn soft bad" data-act="stop" data-run="' + esc(x.id) + '">Stop the run</button>');
    if (['failed', 'stopped', 'incomplete'].includes(x.status)) acts.push('<button class="btn" data-act="retry" data-run="' + esc(x.id) + '">Retry from where it stopped</button>');
    const sm = x.summary || {};
    MAIN.innerHTML = `
      <div class="rhead"><a class="btn soft s ib" href="#/r/${enc(x.route_id)}" aria-label="Back to the route">${svg(IC.back)}</a>
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
          ${l.error ? `<div class="sm errt">${esc(human(l.error))}</div>` : ''}${l.output ? `<details><summary class="sm">What it gave back</summary><pre>${esc(pretty(l.output))}</pre></details>` : ''}</div></div>`; }).join('') || '<div class="empty">No step has run yet.</div>'}</div></section>`;
  }
  async function viewTemplates() {
    setNav('templates');
    const t = await api('GET', '/api/route/templates');
    const cats = [...new Set(t.templates.map(x => x.category))];
    const draw = cat => t.templates.filter(x => !cat || x.category === cat).map(x => `<section class="card tc">
      <div class="apps">${x.apps.map(a => appTile({kind: 'app', slug: a, label: a})).join('')}</div>
      <h3>${esc(x.title)}</h3><span class="mut sm">${esc(x.ask)}</span>
      <div class="tf"><span class="mut sm">${esc(x.category)}</span><span class="sp"></span><button class="btn s" data-use="${esc(x.id)}">Use this</button></div></section>`).join('');
    MAIN.innerHTML = `<div class="top"><div><h1>Templates</h1><p class="lead sm">Hoola fits each one to your own apps, time zone and currency, and shows you the steps before anything switches on.</p></div></div>
      <div class="chips left" id="tc"><button class="chip" aria-pressed="true" data-c="">All</button>${cats.map(c => `<button class="chip" aria-pressed="false" data-c="${esc(c)}">${esc(c)}</button>`).join('')}</div>
      <div class="tgal" id="tg">${draw('')}</div>`;
    $('#tc').addEventListener('click', e => { const b = e.target.closest('[data-c]'); if (!b) return;
      $('#tc').querySelectorAll('[data-c]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); $('#tg').innerHTML = draw(b.dataset.c); });
    $('#tg').addEventListener('click', e => { const b = e.target.closest('[data-use]'); if (!b) return;
      const x = t.templates.find(y => y.id === b.dataset.use); b.disabled = true;
      askHoola(x.ask).catch(err => { toast(err.message, true); b.disabled = false; }); });
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
        const w = $('#onWord'); if (w && sw.closest('.onl')) w.textContent = on ? 'On' : 'Off';
      } catch (err) { toast(err.message, true); }
      sw.disabled = false; return;
    }
    const act = e.target.closest('[data-act]');
    if (act) {
      act.disabled = true;
      try { await api('POST', `/api/route/runs/${enc(act.dataset.run)}/${act.dataset.act}`);
        toast(act.dataset.act === 'approve' ? 'Approved. The run carries on.' : act.dataset.act === 'stop' ? 'Stopped.' : 'Retrying from where it stopped.');
        route(); }
      catch (err) { toast(err.message, true); act.disabled = false; }
    }
  });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); location.hash = '#/'; setTimeout(() => { const t = $('#askText'); if (t) t.focus(); }, 60); }
  });
  $('#newRoute').addEventListener('click', () => setTimeout(() => { const t = $('#askText'); if (t) t.focus(); }, 60));

  async function route() {
    const h = location.hash.replace(/^#\/?/, '');
    const [a, b] = h.split('/');
    try {
      if (a === 'routes') await viewRoutes();
      else if (a === 'r' && b) await viewRoute(decodeURIComponent(b));
      else if (a === 'runs') await viewRuns(b || '');
      else if (a === 'run' && b) await viewRun(decodeURIComponent(b));
      else if (a === 'templates') await viewTemplates();
      else await viewHome();
    } catch (err) { MAIN.innerHTML = `<div class="errbox">${esc(err.message)}</div>`; }
    needCount();
  }
  window.addEventListener('hashchange', route);
  route();
})();
