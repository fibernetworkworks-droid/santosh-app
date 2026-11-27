/* DEVOPS DESK - the DevOps employee's own section, like the finance desks (owner: "DevOps same as finance desks"). A thin top bar,
   then the DevOps chat (its own conversation, kind 'devops') beside the desk's pages: Today, Builds, Deploys, Servers & logs,
   Scripts & checklists, Settings. The pages call /api/dvdesk/do/<part>, which runs the DevOps engine. Hoola never deploys, approves or
   re-runs without her tap, never runs a script and never logs in to her server. Routes: #/<page>. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const APP = $('#sd');
  if (!TOKEN) { location.replace('/console/'); return; }

  async function api(method, path, body, opts) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (opts && opts.form) payload = opts.form;
    else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M4 7h16M4 12h16M4 17h10"/><circle cx="18" cy="17" r="2"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['builds', 'Builds'], ['deploys', 'Deploys'], ['servers', 'Servers & logs'], ['scripts', 'Scripts & checklists'],
    ['settings', 'Settings']];
  const STARTERS = {
    today: ['What is broken right now?', 'Why did my last build fail?', 'Summarise this week for my team'],
    builds: ['Explain the last failed build', 'Which tests are flaky?', 'Why are my builds slower?'],
    deploys: ['Prepare a deploy of main', 'What changes if I deploy now?', 'How do I roll back safely?'],
    servers: ['What is this error in my logs?', 'Why is my site down?', 'How do I set up the log collector?'],
    scripts: ['Write a GitHub Actions workflow for my app', 'Make a backup script for my database', 'Is this script safe?'],
    settings: ['What token permissions does Hoola need?', 'How long should I keep server logs?', 'What deploy rules should I set?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', rf: '', tk: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dvdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dvdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'devops', name: ((K().settings || {}).team) || 'Your DevOps'} : null;
  const CAN = () => !!(ST.d && ST.d.status === 'hired');
  const cur = () => 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 6});
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16).replace(' ', 'T')).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/dvdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dvdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your DevOps is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dvHire">Hire DevOps</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dvHire').onclick = async () => { try { await api('POST', '/api/employees/devops/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame();
    readTab();
    paintTabs();
    showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 60000));
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    ST.arg = decodeURIComponent(parts.slice(1).join('/') || '');
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.fo, '')}</div>
          <div style="min-width:0"><div class="sd-name">DevOps</div><div class="sd-site" id="dvSite"></div></div>
          <span id="dvState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="DevOps chat">
          <div class="sd-chathead"><div class="t"><b>DevOps chat</b><span>Ask about a failed build, a deploy, a server error or a script - or drop a log or config file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dvFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dvPick" multiple hidden accept="image/*,.txt,.log,.md,.yml,.yaml,.json,.sh,.conf,.toml,.ini,.py,.csv,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="DevOps desk" id="sdTabs"></nav>
          <div id="dvPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola never deploys, approves or re-runs without your tap, and never runs anything on your server.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a build, a deploy or an error…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dvPick').click()});
    $('#dvPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dvdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dvdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dvdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dvPage').addEventListener('click', onPageClick);
    $('#dvPage').addEventListener('submit', onSubmit);
    $('#dvPage').addEventListener('change', onChange);
    $('#dvPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dvState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), gh = (k.settings || {}).github || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Watching'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#dvSite').textContent = [(k.settings || {}).team, gh.joined ? '@' + gh.login : 'GitHub not connected', pl((k.repos || []).length, 'repo'), (k.settings || {}).country].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), d = k.day || {}, rs = (k.runs || []).slice(0, 30);
    const n = {builds: (d.failed || []).length || '', deploys: (d.waiting || []).length || '',
      servers: ((d.down || []).length + (d.ssl_soon || []).length + (d.high_disk || []).length) || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dvdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dvPage'); if (!box) return;
    const fn = {today: pToday, builds: pBuilds, deploys: pDeploys, servers: pServers, scripts: pScripts, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    box.innerHTML = html;
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  /* a part of the page that arrives later redraws it: what she was typing stays where it was */
  const fkey = f => `${f.dataset.form}|${f.dataset.which || f.dataset.kind || ''}`;
  function typed(box) {
    const out = {map: {}, focus: null}, act = document.activeElement;
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = fkey(f), vals = {};
      [...f.querySelectorAll('input:not([type=file]), textarea, select'), ...box.querySelectorAll(`[form="${f.id || '-'}"]`)].forEach((el, j) => {
        if (!el.name) return;
        const id = el.name + '#' + j;
        if (el.value !== el.defaultValue && el.tagName !== 'SELECT') vals[id] = {v: el.value};
        else if (el.tagName === 'SELECT' && el.dataset.touched) vals[id] = {v: el.value};
        if (el === act) out.focus = [k, id, el.selectionStart];
      });
      if (Object.keys(vals).length) out.map[k] = vals;
    });
    return out;
  }
  function retype(box, kept) {
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = fkey(f), vals = kept.map[k]; if (!vals && !(kept.focus && kept.focus[0] === k)) return;
      [...f.querySelectorAll('input:not([type=file]), textarea, select'), ...box.querySelectorAll(`[form="${f.id || '-'}"]`)].forEach((el, j) => {
        if (!el.name) return;
        const id = el.name + '#' + j, v = vals && vals[id];
        if (v) { el.value = v.v; if (el.tagName === 'SELECT') el.dataset.touched = '1'; }
        if (kept.focus && kept.focus[0] === k && kept.focus[1] === id) { el.focus(); try { if (kept.focus[2] !== null) el.setSelectionRange(kept.focus[2], kept.focus[2]); } catch {} }
      });
    });
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const err = r => r && r.error ? `<p class="cs-neg" style="margin:8px 0 0">${esc(r.error)}</p>` : '';
  const ro = () => CAN() ? '' : '<p class="cs-note">The desk is paused: resume it in AI Employees to make changes.</p>';
  const sign = v => Number(v) > 0 ? 'cs-pos' : Number(v) < 0 ? 'cs-neg' : '';
  const sgn = v => (Number(v) > 0 ? '+' : '') + num(v);
  const ask = (about) => `<button class="ib mk-ask" type="button" aria-label="Ask about this" title="Ask in the chat" data-ask="${esc(about)}">${svg(IC.chat)}</button>`;
  const rmBtn = (reg, n) => CAN() ? `<button class="ib" type="button" aria-label="Remove" data-rm="${esc(reg)}" data-n="${esc(n)}">×</button>` : '';
  const tag = (t, c) => `<span class="cs-tag ${c || ''}">${esc(t)}</span>`;
  function uploader(kind, title, hint, extra) {
    if (!CAN()) return '';
    return `<form class="ins-drop" data-form="upload" data-kind="${esc(kind)}"><div class="t"><b>${esc(title)}</b><span class="mut">${esc(hint)}</span></div>
      ${extra || ''}<label class="btn soft sm">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" data-upfile="1" hidden></label></form>`;
  }
  const short = v => { const n = Math.abs(Number(v) || 0), s = Number(v) < 0 ? '-' : '';
    return s + (n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(0) + 'k' : n.toLocaleString(undefined, {maximumFractionDigits: 0})); };
  const listRows = (reg, rows, cols, max) => {
    if (!(rows || []).length) return empty('Nothing here yet.');
    return `<div class="iv-tw"><table class="tb mk-list"><thead><tr>${cols.map(c => `<th${c[2] ? ' class="r"' : ''}>${esc(c[1])}</th>`).join('')}<th></th></tr></thead><tbody>${
      rows.slice(0, max || 200).map(r => `<tr>${cols.map(c => `<td${c[2] ? ' class="r"' : ''}>${c[3] ? c[3](r[c[0]], r) : esc(r[c[0]] ?? '')}</td>`).join('')}<td class="r">${rmBtn(reg, r.n)}</td></tr>`).join('')}</tbody></table></div>
      ${rows.length > (max || 200) ? `<p class="mut" style="font-size:13px">Showing ${num(max || 200)} of ${num(rows.length)}.</p>` : ''}
      ${CAN() ? `<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-rmall="${esc(reg)}">Clear all</button></div>` : ''}`;
  };
  const addForm = (reg, fields, label) => CAN() ? `<form class="mk-add" data-form="add" data-which="${esc(reg)}">${fields.map(([n, l, t, ph]) =>
      Array.isArray(t) ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${t.map(([v, x]) => `<option value="${esc(v)}">${esc(x)}</option>`).join('')}</select></label>`
      : t === 'io' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="in">Money in</option><option value="out">Money out</option></select></label>`
      : t === 'freq' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="monthly">Monthly</option><option value="weekly">Weekly</option><option value="fortnightly">Fortnightly</option></select></label>`
      : `<label class="ins-lab">${esc(l)}<input class="in" name="${n}"${t === 'date' ? ' type="date"' : ''}${t === 'num' ? ' inputmode="decimal"' : ''} placeholder="${esc(ph || '')}"></label>`).join('')}
      <button class="btn soft" type="submit">${esc(label || 'Add')}</button></form>` : '';

  /* ---------------------------------------------------------------- charts (drawn in SVG, no library) */
  function ring(parts, mid, sub, label) {
    const rows = parts.filter(p => p[1] > 0), total = rows.reduce((s, p) => s + p[1], 0);
    if (!total) return '';
    const Rr = 54, C = 2 * Math.PI * Rr; let at = 0;
    const arcs = rows.map(([name, v, cls]) => { const len = v / total * C, gap = rows.length > 1 ? 2 : 0, l2 = Math.max(0, len - gap);
      const s = `<circle class="iv-seg ${esc(cls)}" r="${Rr}" cx="70" cy="70" stroke-dasharray="${l2.toFixed(2)} ${(C - l2).toFixed(2)}" stroke-dashoffset="${(-at).toFixed(2)}"><title>${esc(name)} ${num(v)}</title></circle>`;
      at += len; return s; }).join('');
    return `<div class="iv-donut"><svg viewBox="0 0 140 140" role="img" aria-label="${esc(label)}"><g transform="rotate(-90 70 70)"><circle class="iv-track" r="${Rr}" cx="70" cy="70"/>${arcs}</g>
      <text x="70" y="66" class="iv-dl">${esc(sub)}</text><text x="70" y="84" class="iv-dv">${esc(mid)}</text></svg>
      <div class="iv-dleg">${rows.map(([name, v, cls]) => `<div><i class="${esc(cls)}"></i><span>${esc(name)}</span><b>${esc(num(v))}</b></div>`).join('')}</div></div>`;
  }
  function bars(rows, fmt, label) {   /* rows: [name, value, cls, sub] - horizontal bars from 0 */
    if (!rows.length) return '';
    const mx = Math.max(1e-9, ...rows.map(r => Math.abs(r[1])));
    return `<div class="iv-w mk-bars" role="img" aria-label="${esc(label)}">${rows.map(([n, v, cls, sub]) => `<div><span><b>${esc(n)}</b>${sub ? `<em>${esc(sub)}</em>` : ''}</span><i><b class="${esc(cls || 'mk-b')}" style="width:${(Math.abs(v) / mx * 100).toFixed(1)}%"></b></i><em>${esc(fmt ? fmt(v) : num(v))}</em></div>`).join('')}</div>`;
  }
  function line(pts, label, fmt, cls, wide) {   /* pts: [label, value] - a filled line, the last value marked */
    if (pts.length < 2) return '';
    const W = wide ? 760 : 480, H = wide ? 200 : 210, L = wide ? 64 : 52, R = 14, T = 14, B = 30, vs = pts.map(p => Number(p[1]) || 0);
    let lo = Math.min(0, ...vs), hi = Math.max(...vs); if (hi === lo) hi = lo + 1;
    const x = i => L + i * (W - L - R) / (pts.length - 1), y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const d = vs.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    const area = `${d}L${x(vs.length - 1).toFixed(1)},${y(lo).toFixed(1)}L${x(0).toFixed(1)},${y(lo).toFixed(1)}Z`;
    const ticks = [hi, (hi + lo) / 2, lo].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`).join('');
    const every = Math.max(1, Math.ceil(pts.length / 6));
    const xl = pts.map((p, i) => (i % every === 0 || i === pts.length - 1) ? `<text class="tx" x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(p[0])}</text>` : '').join('');
    const zero = lo < 0 ? `<line class="zero" x1="${L}" x2="${W - R}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"/>` : '';
    const lx = x(vs.length - 1), ly = y(vs[vs.length - 1]);
    return `<div class="cs-chart cm-line ${esc(cls || '')}"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${ticks}${zero}<path class="ar" d="${area}"/><path class="ln" d="${d}"/>
      ${vs.map((v, i) => `<circle class="pt" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3"><title>${esc(pts[i][0])}: ${esc(fmt ? fmt(v) : num(v))}</title></circle>`).join('')}
      <circle class="end" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="5"/>${xl}</svg></div>`;
  }
  function gauge(share, limit) {   /* her repayments as a share of income, against her limit */
    if (share === null || share === undefined) return '';
    const p = Math.min(100, Math.max(0, Number(share))), lim = limit === null || limit === undefined ? null : Math.min(100, Number(limit));
    const over = lim !== null && p > lim;
    return `<div class="cm-gauge"><div class="h"><b class="${over ? 'cs-neg' : ''}">${esc(num(Math.round(p * 10) / 10))}%</b><span class="mut">of your income goes to repayments${lim !== null ? ` · your limit ${esc(lim)}%` : ''}</span></div>
      <div class="bar"><i class="${over ? 'bad' : p > (lim ?? 100) * 0.8 ? 'warn' : 'ok'}" style="width:${p.toFixed(1)}%"></i>${lim !== null ? `<u style="left:${lim}%" title="your limit"></u>` : ''}</div>
      <div class="ft"><span>0%</span><span>50%</span><span>100%</span></div></div>`;
  }
  const m0 = v => money(v, null, 0);
  const dd = d => { try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); } catch { return d; } };
  const tick = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>';

  /* ---------------------------------------------------------------- helpers of this desk */
  const pct = v => (v === null || v === undefined) ? '—' : `${num(Math.round(Number(v) * 10) / 10)}%`;
  const FAILED = ['failure', 'timed_out', 'startup_failure', 'action_required'];
  const CON = c => c === 'success' ? tag('Passed', 'ok') : FAILED.includes(c) ? tag('Failed', 'bad') : c === 'cancelled' ? tag('Cancelled', '') : c ? tag(cap(S(c).replace(/_/g, ' ')), '') : tag('Running', 'v');
  const DST = {card: 'warn', dispatched: 'v', running: 'v', waiting: 'warn', success: 'ok', failed: 'bad', rejected: '', cancelled: '', stale: ''};
  const LV = {block: ['Change before running', 'bad'], warn: ['Look at this', 'warn'], info: ['Note', 'v'], ok: ['Looks safe', 'ok']};
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const gh = () => ((K().settings || {}).github || {});
  const repoOpts = sel => (K().repos || []).map(r => `<option value="${esc(r.full_name)}"${r.full_name === sel ? ' selected' : ''}>${esc(r.full_name)}</option>`).join('');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), d = k.day || {}, eps = k.endpoints || [], rs = k.runs || [], dora = k.dora || {};
    const recent = rs.filter(r => r.status === 'completed').slice(0, 30), bad = recent.filter(r => FAILED.includes(r.conclusion)).length;
    const up = eps.filter(e => e.up).length;
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All good: no failed build, no site down, no deploy waiting.';
    const tiles = [
      `<div class="k${bad ? ' low bad' : ''}"><div class="l">Builds</div><div class="v">${recent.length ? esc(pct(100 * (recent.length - bad) / recent.length)) : '—'}</div><div class="s">${recent.length ? esc(pl(recent.length, 'recent run')) + ' passed' : 'no builds yet'}</div></div>`,
      `<div class="k${(d.waiting || []).length ? ' low bad' : ''}"><div class="l">Deploys waiting</div><div class="v">${esc(num((d.waiting || []).length))}</div><div class="s">go out only on your tap</div></div>`,
      `<div class="k${(d.down || []).length ? ' low bad' : ''}"><div class="l">Sites up</div><div class="v">${eps.length ? esc(up + ' / ' + eps.length) : '—'}</div><div class="s">${(d.ssl_soon || []).length ? esc(pl(d.ssl_soon.length, 'SSL')) + ' ending soon' : 'checked every 5 minutes'}</div></div>`,
      `<div class="k${(k.clusters || []).some(c => c.serious) ? ' low bad' : ''}"><div class="l">Error kinds open</div><div class="v">${esc(num((k.clusters || []).length))}</div><div class="s">from your server logs</div></div>`];
    const wf = ((k.health || {}).workflows || []).slice(0, 8);
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Delivery (30 days)</h2></div>
          <div class="dv-dora">${[['Deploys a week', dora.per_week], ['Commit to production', dora.lead_time_h === null || dora.lead_time_h === undefined ? null : dora.lead_time_h + ' h'], ['Changes that broke', dora.change_failure_pct === null || dora.change_failure_pct === undefined ? null : pct(dora.change_failure_pct)], ['Time to recover', dora.recovery_h === null || dora.recovery_h === undefined ? null : dora.recovery_h + ' h']].map(([l, v]) => `<div><span class="mut">${esc(l)}</span><b>${v === null || v === undefined || v === '' ? '—' : esc(v)}</b></div>`).join('')}</div>
          <p class="cs-note">${esc(dora.deploys ? dora.say || '' : 'Shows once your production deploy workflow has run.')}</p></section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Workflows: how often they fail</h2><div class="r"><button class="btn soft sm" type="button" data-go="builds">Open</button></div></div>
        ${wf.length ? bars(wf.map(w => [w.workflow, w.fail_pct, w.fail_pct >= 20 ? 'dv-bad' : 'mk-b', w.repo + (w.time && w.time.median_s ? ' · ' + w.say.split(': ').slice(1).join(': ') : '')]), pct, 'Failure rate by workflow') : empty('Builds show here once a repo is watched.')}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Recent deploys</h2><div class="r"><button class="btn soft sm" type="button" data-go="deploys">Open</button></div></div>
          ${(k.deploys || []).slice(0, 6).map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(x.number)}</b> ${esc(x.repo)} <span class="mut">${esc(x.environment)} · ${esc(x.sha)} · ${esc(ago(x.created_at))}</span></span>${tag(x.status_label, DST[x.status] || '')}</div>`).join('') || empty('No deploys yet.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your sites</h2><div class="r"><button class="btn soft sm" type="button" data-go="servers">Open</button></div></div>
          ${eps.map(e => `<div class="cs-row"><span class="cs-dot${e.up === false ? ' bad' : ''}"></span><span style="flex:1">${esc(e.name)} <span class="mut">${e.uptime_pct === null ? 'not checked yet' : esc(pct(e.uptime_pct)) + ' up'}${e.ssl_days !== null && e.ssl_days !== undefined ? ' · SSL ' + esc(e.ssl_days) + ' days' : ''}</span></span>${e.up === false ? tag('Down', 'bad') : e.up ? tag('Up', 'ok') : tag('—', '')}</div>`).join('') || empty('Add your site\'s address to watch it.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- builds */
  function pBuilds() {
    const k = K(), f = ST.rf || '', h = k.health || {};
    const rs = (k.runs || []).filter(r => !f || (f === 'failed' ? FAILED.includes(r.conclusion) : f === 'flaky' ? r.flaky : f === 'running' ? r.status !== 'completed' : r.repo === f));
    const diag = r => { const g = r.diagnosis || {}; if (!g.label && !FAILED.includes(r.conclusion)) return '';
      return `<div class="qa-body">${g.label ? `<p style="margin:0"><b>${esc(g.label)}</b>${g.step ? ` <span class="mut">at the step "${esc(g.step)}"${g.job ? ' in ' + esc(g.job) : ''}</span>` : ''}</p>` : '<p class="mut" style="margin:0">Not explained yet.</p>'}
        ${g.why ? `<p style="margin:6px 0 0">${esc(g.why)}</p>` : ''}${g.fix ? `<p style="margin:6px 0 0"><b>Fix:</b> ${esc(g.fix)}</p>` : ''}${g.hint ? `<p class="mut" style="margin:6px 0 0">${esc(g.hint)}</p>` : ''}
        ${(g.jobs || []).filter(j => (j.lines || []).length).slice(0, 2).map(j => `<pre class="qa-con">${esc(j.lines.slice(-12).join('\n'))}</pre>`).join('')}
        ${g.flaky_likely || r.flaky ? '<p class="cs-note">This looks flaky: the same code passed on another run.</p>' : ''}
        ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px;flex-wrap:wrap">${!g.label ? `<button class="btn soft sm" type="button" data-act="diagnose" data-run="${esc(r.key)}">Explain it</button>` : ''}${!r.is_deploy && !r.is_rollback ? `<button class="btn sm" type="button" data-act="rerun" data-run="${esc(r.key)}">Re-run the failed jobs</button>` : '<span class="mut" style="font-size:13px">A deploy run is re-done with a new deploy card.</span>'}${r.url ? `<a class="btn soft sm" href="${esc(r.url)}" target="_blank" rel="noopener">On GitHub</a>` : ''}${ask('Build ' + r.workflow + ' ' + r.sha + ' failed')}</div>` : ''}</div>`; };
    return `<div class="cs-head"><div><h1 class="sd-h">Builds</h1><p class="lead" style="margin-top:4px">Your GitHub Actions runs, checked every 5 minutes. A failed one is explained: the job, the exact step, the error lines, what kind of failure it is and the likely fix. Re-running is your tap.</p></div>
        <div class="r">${CAN() && gh().joined ? '<button class="btn soft sm" type="button" data-act="sync">Check now</button>' : ''}</div></div>
      ${!gh().joined ? `<section class="card"><p style="margin:0">Connect GitHub in Settings to watch your builds.</p><div class="md-acts"><span></span><button class="btn sm" type="button" data-go="settings">Settings</button></div></section>` : ''}
      ${gh().joined ? `<section class="card"><h2 class="md-h2">Repos watched</h2>${(k.repos || []).map(r => `<div class="cs-row"><span style="flex:1"><b>${esc(r.full_name)}</b> <span class="mut">${r.deploy_workflow ? 'deploys with ' + esc(r.deploy_workflow) + ' to ' + esc(r.environment) : 'no deploy workflow'}${r.rollback_workflow ? ' · rollback ' + esc(r.rollback_workflow) : ''}</span></span>${CAN() ? `<button class="btn soft sm" type="button" data-act="repo_remove" data-repo="${esc(r.full_name)}">Stop</button>` : ''}</div>`).join('') || empty('None yet.')}
        ${CAN() ? `<form class="iv-add" data-form="repo"><input class="in" name="repo" required maxlength="140" placeholder="owner/name" aria-label="Repo"><input class="in" name="deploy_workflow" maxlength="120" placeholder="Deploy workflow (deploy.yml)" aria-label="Deploy workflow"><input class="in" name="environment" maxlength="80" placeholder="Environment (production)" aria-label="Environment"><input class="in" name="rollback_workflow" maxlength="120" placeholder="Rollback workflow (optional)" aria-label="Rollback workflow"><button class="btn" type="submit">Watch it</button></form>` : ''}</section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Runs</h2><div class="r"><select class="in sm" data-rfilter="1" aria-label="Show"><option value="">All</option><option value="failed"${f === 'failed' ? ' selected' : ''}>Failed</option><option value="flaky"${f === 'flaky' ? ' selected' : ''}>Flaky</option><option value="running"${f === 'running' ? ' selected' : ''}>Running</option>${(k.repos || []).map(r => `<option value="${esc(r.full_name)}"${f === r.full_name ? ' selected' : ''}>${esc(r.full_name)}</option>`).join('')}</select></div></div>
        ${rs.length ? rs.map(r => `<details class="qa-case" data-key="r:${esc(r.key)}"${ST.open.has('r:' + r.key) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(r.workflow)}</b> ${esc(r.title || '')} <span class="mut">${esc(r.repo)} · ${esc(r.branch)} · ${esc(r.sha)} · ${esc(ago(r.started_at))}${r.duration ? ' · ' + esc(r.duration) : ''}${r.flaky ? ' · flaky' : ''}</span></span>${r.is_deploy ? tag('Deploy', 'v') : ''}${CON(r.conclusion)}</summary>${diag(r)}</details>`).join('') : empty('No runs yet.')}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Workflow health</h2>${(h.workflows || []).length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Workflow</th><th class="r">Fail</th><th class="r">Median time</th></tr></thead><tbody>${h.workflows.map(w => `<tr><td><b>${esc(w.workflow)}</b> <span class="mut">${esc(w.repo)}</span></td><td class="r ${w.fail_pct >= 20 ? 'cs-neg' : ''}">${esc(pct(w.fail_pct))}</td><td class="r">${esc((w.time || {}).median_s ? Math.round(w.time.median_s / 60 * 10) / 10 + ' min' : '—')}${(w.time || {}).slower ? ' <span class="cs-neg">slower</span>' : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('Shows after a few runs.')}
          ${(h.flaky_tests || []).length ? `<div class="cr-sub" style="margin-top:12px">Flaky tests</div>${h.flaky_tests.slice(0, 8).map(t => `<div class="cs-row"><span style="flex:1">${esc(t.name)} <span class="mut">${esc(t.repo)}</span></span><span class="mut">${esc(t.flips)} flips</span></div>`).join('')}` : ''}</section>
        <form class="card" data-form="cilog"><h2 class="md-h2">Explain a build log</h2><textarea class="in" name="text" rows="6" maxlength="200000" placeholder="Paste the failing part of a build log from any CI" style="width:100%"></textarea>
          <div class="md-acts"><span class="mut" style="font-size:13px">The log is read as data; keys in it are masked.</span><button class="btn soft" type="submit">Explain</button></div>
          ${ST.out.cilog ? `<div class="pb-res" style="margin-top:10px"><b>${esc(ST.out.cilog.label)}</b><p style="margin:6px 0 0">${esc(ST.out.cilog.why)}</p><p style="margin:6px 0 0"><b>Fix:</b> ${esc(ST.out.cilog.fix)}</p>${(ST.out.cilog.lines || []).length ? `<pre class="qa-con">${esc(ST.out.cilog.lines.slice(-10).join('\n'))}</pre>` : ''}</div>` : ''}</form></div>`;
  }

  /* ---------------------------------------------------------------- deploys */
  function pDeploys() {
    const k = K(), ds = k.deploys || [], waiting = ds.filter(x => x.status === 'card'), rest = ds.filter(x => x.status !== 'card');
    const card = x => { const c = x.changes || {}, ch = x.checks || {}, rb = x.rollback || {};
      return `<div class="pb-res${x.checks_ok ? '' : ' warn'}" style="margin-top:12px"><div class="cs-head"><div><b>${esc(x.number)} · ${x.kind === 'rollback' ? 'Roll back' : x.kind === 'review' ? 'GitHub asks for approval' : 'Deploy'} ${esc(x.repo)}</b>
          <div class="mut" style="font-size:12.5px">${esc(x.ref || '')} → ${esc(x.sha)} · to ${esc(x.environment)} · with ${esc(x.workflow || '—')}</div></div><div class="r">${tag(x.status_label, DST[x.status] || '')}</div></div>
        <div class="dv-grid"><div><span class="mut">What changes</span><p style="margin:4px 0 0">${esc(c.say || '—')}</p>${(c.commits || []).length ? `<ul class="dv-commits">${c.commits.slice(-8).reverse().map(m => `<li><code>${esc(m.sha)}</code> ${esc(m.msg)} <span class="mut">${esc(m.by)}</span></li>`).join('')}</ul>` : ''}${c.migration && !/migration/i.test(c.say || '') ? '<p class="cs-neg" style="margin:6px 0 0">Has a database migration: take a backup first.</p>' : ''}</div>
          <div><span class="mut">Checks</span><p style="margin:4px 0 0">${ch.state === 'success' ? '<span class="cs-pos">All green</span>' : ch.state === 'skip' ? 'Not needed for a rollback' : esc(cap(ch.state || 'unknown'))}${(ch.failed || []).length ? ' · failed: ' + esc(ch.failed.slice(0, 4).join(', ')) : ''}${(ch.pending || []).length ? ' · still running: ' + esc(ch.pending.slice(0, 4).join(', ')) : ''}</p>
            <span class="mut" style="display:block;margin-top:8px">If it goes wrong</span><p style="margin:4px 0 0">${esc(rb.say || (rb.sha ? 'Back to ' + rb.sha : 'No earlier good deploy known yet'))}</p></div></div>
        ${CAN() ? `<form class="iv-add" data-form="decide" data-id="${esc(x.id)}" data-h="${esc(x.hash)}">${x.checks_ok || x.kind === 'rollback' ? '' : '<input class="in" name="reason" maxlength="300" placeholder="Checks are not green - write why it should still go out" aria-label="Reason">'}
          <button class="btn soft" type="button" data-act="cancel" data-d="${esc(x.id)}">Close the card</button><button class="btn soft" type="submit" data-yes="0">Refuse</button>${x.kind === 'review' ? `<button class="btn soft" type="button" data-act="reject_github" data-d="${esc(x.id)}" data-h="${esc(x.hash)}">Reject on GitHub</button>` : ''}<button class="btn" type="submit" data-yes="1">${x.kind === 'rollback' ? 'Roll back now' : x.kind === 'review' ? 'Approve on GitHub' : 'Deploy now'}</button></form>
          <p class="cs-note">Your tap starts your own workflow on GitHub. If the branch moved after this card, it is refused and you ask for a new card.</p>` : ''}</div>`; };
    return `<div><h1 class="sd-h">Deploys</h1><p class="lead">A deploy or a rollback is a card: what changes, whether the checks are green, and the way back. Only your tap starts your deploy workflow; Hoola never deploys by itself.</p></div>
      ${waiting.length ? `<section class="card"><h2 class="md-h2">Waiting for your tap <span class="mut">${esc(num(waiting.length))}</span></h2>${waiting.map(card).join('')}</section>` : ''}
      ${CAN() && (k.repos || []).some(r => r.deploy_workflow) ? `<div class="md-2" style="align-items:start">
        <form class="card" data-form="deploy"><h2 class="md-h2">Prepare a deploy</h2><div class="md-form"><div class="md-field"><label for="dvD1">Repo</label><select class="in" id="dvD1" name="repo">${repoOpts()}</select></div>
          <div class="md-field"><label for="dvD2">Branch, tag or commit</label><input class="in" id="dvD2" name="ref" maxlength="120" placeholder="main"></div><div class="md-field"><label for="dvD3">Environment</label><input class="in" id="dvD3" name="environment" maxlength="80" placeholder="production"></div>
          <div class="md-field wide"><label for="dvD4">Note</label><input class="in" id="dvD4" name="note" maxlength="300"></div></div><div class="md-acts"><span class="mut" style="font-size:13px">Makes a card only.</span><button class="btn" type="submit">Prepare the card</button></div></form>
        <form class="card" data-form="rollback"><h2 class="md-h2">Prepare a rollback</h2><div class="md-form"><div class="md-field"><label for="dvR1">Repo</label><select class="in" id="dvR1" name="repo">${repoOpts()}</select></div>
          <div class="md-field"><label for="dvR2">Back to commit</label><input class="in" id="dvR2" name="to" maxlength="60" placeholder="the last good one if blank"></div><div class="md-field wide"><label for="dvR3">Why</label><input class="in" id="dvR3" name="note" maxlength="300"></div></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Makes a card only.</span><button class="btn soft" type="submit">Prepare the card</button></div></form></div>` : `<section class="card"><p style="margin:0">${gh().joined ? 'Add a deploy workflow to a repo (Builds) to prepare deploys here.' : 'Connect GitHub in Settings first.'}</p></section>`}
      <section class="card"><h2 class="md-h2">History</h2>${rest.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Deploy</th><th>When</th><th>Status</th><th></th></tr></thead><tbody>${rest.map(x => `<tr><td><b>${esc(x.number)}</b> ${esc(x.kind === 'rollback' ? 'rollback ' : '')}${esc(x.repo)} <span class="mut">${esc(x.environment)} · ${esc(x.sha)}${x.forced ? ' · went out with checks not green: ' + esc(x.reason) : ''}</span></td><td>${esc(dt(x.created_at))}</td><td>${tag(x.status_label, DST[x.status] || '')}</td><td class="r nw">${x.run_url ? `<a class="btn soft sm" href="${esc(x.run_url)}" target="_blank" rel="noopener">Run</a>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No deploys yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- servers and logs */
  function pServers() {
    const k = K(), eps = k.endpoints || [], cls = k.clusters || [], cols = k.collectors || [], made = ST.out.collector;
    return `<div><h1 class="sd-h">Servers &amp; logs</h1><p class="lead">Your sites checked every 5 minutes (two misses = an alert), their SSL certificates, your server's errors grouped by kind with a runbook, and a small read-only collector that sends logs and disk use from your server. Hoola never logs in to your server.</p></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Sites</h2><div class="r">${CAN() && eps.length ? '<button class="btn soft sm" type="button" data-act="watch">Check now</button>' : ''}</div></div>
        ${eps.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Site</th><th class="r">Up</th><th class="r">Answer</th><th class="r">SSL</th><th>Now</th><th></th></tr></thead><tbody>${eps.map(e => `<tr><td><b>${esc(e.name)}</b> <span class="mut">${esc(e.url)}</span>${e.problem && e.up === false ? `<div class="cs-neg" style="font-size:12.5px">${esc(e.problem)}${e.down_since_local ? ' · since ' + esc(e.down_since_local) : ''}</div>` : ''}</td><td class="r">${esc(e.uptime_pct === null ? '—' : pct(e.uptime_pct))}</td><td class="r">${e.last_ms ? esc(e.last_ms) + ' ms' : '—'}</td><td class="r ${e.ssl_days !== null && e.ssl_days <= 21 ? 'cs-neg' : ''}">${e.ssl_days === null || e.ssl_days === undefined ? '—' : esc(e.ssl_days) + ' days'}</td><td>${e.up === false ? tag('Down', 'bad') : e.up ? tag('Up', 'ok') : tag('Not checked', '')}</td><td class="r">${CAN() ? `<button class="btn soft sm" type="button" data-act="endpoint_remove" data-id="${esc(e.id)}">Stop</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No site yet.')}
        ${CAN() ? `<form class="iv-add" data-form="endpoint"><input class="in" name="url" required maxlength="300" placeholder="https://your-site.com/health" aria-label="Address"><input class="in" name="name" maxlength="120" placeholder="Name" aria-label="Name"><input class="in" name="keyword" maxlength="120" placeholder="A word the page must show (optional)" aria-label="Keyword"><button class="btn" type="submit">Watch it</button></form><p class="cs-note">Public https addresses only.</p>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="logs"><h2 class="md-h2">Read server logs</h2><textarea class="in" name="text" rows="6" maxlength="500000" placeholder="Paste log lines (pm2, nginx, docker, journalctl, stack traces)" style="width:100%"></textarea>
          <div class="iv-add" style="margin-top:8px"><input class="in" name="source" maxlength="80" placeholder="Server or app name" aria-label="Source"><label class="btn soft sm" style="flex:0 0 auto">Or choose a file<input type="file" data-upfile="1" accept=".log,.txt,text/plain" hidden></label><button class="btn" type="submit">Read them</button></div>
          <p class="cs-note">Only a masked sample of each error kind is kept, never the raw logs.</p></form>
        <section class="card"><h2 class="md-h2">Collectors on your servers</h2>${cols.map(c => `<div class="pb-res" style="margin-top:8px"><div class="cs-head"><b>${esc(c.name)}</b><div class="r">${c.active ? (c.last_seen ? tag('Sent ' + ago(c.last_seen), 'ok') : tag('Not heard from yet', 'warn')) : tag('Stopped', '')}</div></div>
            ${(c.disk || []).map(dk => `<div class="fo-rat"><span>${esc(dk.mount)}</span><i><b class="${dk.used_pct >= 85 ? 'bad' : 'ok'}" style="width:${Math.min(100, dk.used_pct).toFixed(1)}%"></b></i><em class="${dk.used_pct >= 85 ? 'cs-neg' : ''}">${esc(Math.round(dk.used_pct))}%</em></div>`).join('')}
            ${CAN() && c.active ? `<div class="md-acts" style="justify-content:flex-end;gap:8px"><button class="btn soft sm" type="button" data-script="${esc(c.id)}">Get the script</button><button class="btn soft sm" type="button" data-act="collector_revoke" data-id="${esc(c.id)}">Stop it</button></div>` : ''}</div>`).join('') || empty('None yet.')}
          ${made && !made.error ? `<div class="pb-res warn" style="margin-top:10px"><b>Secret for ${esc(made.name || 'the collector')} - shown only now</b><code class="qa-code" style="display:block;margin:6px 0">${esc(made.secret)}</code>${(made.steps || []).map((s, i) => `<div class="cs-row"><span class="fm-step">${i + 1}</span><span class="dv-step">${esc(s)}</span></div>`).join('')}</div>` : ''}
          ${CAN() ? `<form class="iv-add" data-form="collector"><input class="in" name="name" required maxlength="120" placeholder="Server name" aria-label="Server name"><button class="btn soft" type="submit">Add a collector</button></form>` : ''}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Error kinds <span class="mut">${esc(num(cls.length))}</span></h2><div class="r">${CAN() && cls.length ? '<button class="btn soft sm" type="button" data-act="forget_logs">Forget all</button>' : ''}</div></div>
        ${cls.length ? cls.map(c => { const rb = ST.out['rb:' + c.runbook]; return `<details class="qa-case" data-key="cl:${esc(c.id)}"${ST.open.has('cl:' + c.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(c.label)}</b> <span class="mut">${esc(c.source)} · ${esc(num(c.count))} times · last ${esc(ago(c.last_seen))}</span></span>${c.serious ? tag('Serious', 'bad') : ''}${tag(cap(c.status), c.status === 'new' ? 'warn' : '')}</summary>
          <div class="qa-body"><p style="margin:0">${esc(c.why)}</p><p style="margin:6px 0 0"><b>Fix:</b> ${esc(c.fix)}</p>${(c.samples || []).length ? `<pre class="qa-con">${esc(c.samples.slice(0, 3).join('\n'))}</pre>` : ''}
            ${rb && !rb.error ? `<div class="cr-sub" style="margin-top:10px">${esc(rb.title)}</div><ol>${(rb.steps || []).map(s => `<li>${esc(s)}</li>`).join('')}</ol><p class="cs-note">${esc(rb.note)}</p>` : c.runbook ? `<button class="btn soft sm" type="button" data-rb="${esc(c.runbook)}" style="margin-top:8px">Runbook: ${esc(c.runbook_title)}</button>` : ''}
            ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px"><button class="btn soft sm" type="button" data-act="cluster" data-id="${esc(c.id)}" data-st="fixed">Fixed</button><button class="btn soft sm" type="button" data-act="cluster" data-id="${esc(c.id)}" data-st="ignored">Ignore</button>${ask('Server error: ' + c.label)}</div>` : ''}</div></details>`; }).join('') : empty('No errors read yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- scripts and checklists */
  function pScripts() {
    const k = K(), tpl = k.templates || [], sel = ST.tk || (tpl[0] || {}).kind || '', t = tpl.find(x => x.kind === sel) || {}, view = ST.out.script, chk = ST.out.check;
    const finds = fs => (fs || []).map(f => `<div class="rk-flag ${f.level === 'block' ? 'stop' : f.level === 'warn' ? 'check' : ''}"><span>${esc((LV[f.level] || [f.level])[0])}</span><div>${esc(f.why || f.text || '')}${f.line ? ` <span class="mut">line ${esc(f.line)}</span>` : ''}${f.fix ? `<div class="mut" style="font-size:13px">${esc(f.fix)}</div>` : ''}</div></div>`).join('');
    return `<div><h1 class="sd-h">Scripts &amp; checklists</h1><p class="lead">Workflows, Dockerfiles, nginx, backups, services and more as files you review - each checked for dangerous lines first. Hoola never runs any of them. Checklists for deploys, releases, a new server, an incident and a restore test.</p></div>
      ${CAN() ? `<div class="md-2" style="align-items:start"><form class="card" data-form="script"><h2 class="md-h2">Make a file</h2>
          <select class="in" name="kind" data-tkind="1" aria-label="What" style="width:100%">${tpl.map(x => `<option value="${esc(x.kind)}"${x.kind === sel ? ' selected' : ''}>${esc(x.label)}</option>`).join('')}<option value="custom"${sel === 'custom' ? ' selected' : ''}>Something else (in your words)</option></select>
          <div class="md-form" style="margin-top:8px">${sel === 'custom' ? '<div class="md-field wide"><label for="dvC1">What it should do</label><textarea class="in" id="dvC1" name="ask" rows="3" maxlength="1500"></textarea></div>'
            : Object.entries(t.params || {}).map(([p, ex], i) => `<div class="md-field"><label for="dvP${i}">${esc(cap(p.replace(/_/g, ' ')))}</label><input class="in" id="dvP${i}" name="p_${esc(p)}" maxlength="200" placeholder="${esc(ex)}"></div>`).join('')}</div>
          <div class="md-acts"><span class="mut" style="font-size:13px">A secret goes in by its name, never its value.</span><button class="btn" type="submit">Make it</button></div></form>
        <form class="card" data-form="check"><h2 class="md-h2">Check my script</h2><input class="in" name="name" maxlength="120" placeholder="File name (deploy.sh)" aria-label="File name" style="width:100%"><textarea class="in" name="content" rows="6" maxlength="200000" placeholder="Paste your script, workflow, Dockerfile or config" style="width:100%;margin-top:8px"></textarea>
          <div class="md-acts"><span class="mut" style="font-size:13px">Read only, never run.</span><button class="btn soft" type="submit">Check it</button></div>
          ${chk ? `<div style="margin-top:10px">${tag((LV[chk.verdict] || [chk.verdict])[0], (LV[chk.verdict] || ['', ''])[1])}${finds(chk.findings) || '<p class="cs-pos" style="margin:8px 0 0">Nothing dangerous found.</p>'}</div>` : ''}</form></div>` : ''}
      ${view && !view.error ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(view.name)} <span class="mut">${esc(view.label)}</span></h2><div class="r"><button class="btn soft sm" type="button" data-copy="1">Copy</button><button class="btn soft sm" type="button" data-save="1">Download</button>${CAN() && view.status !== 'reviewed' ? `<button class="btn sm" type="button" data-act="reviewed" data-id="${esc(view.id)}">I reviewed it</button>` : ''}</div></div>
        ${finds(view.findings)}<pre class="dv-code">${esc(view.content || '')}</pre></section>` : ''}
      <section class="card"><h2 class="md-h2">Files made</h2>${(k.scripts || []).map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(x.name)}</b> <span class="mut">${esc(x.label)} · ${esc(ago(x.created_at))}</span></span>${tag((LV[x.verdict] || [x.verdict])[0], (LV[x.verdict] || ['', ''])[1])}${x.status === 'reviewed' ? tag('Reviewed', 'ok') : ''}<button class="btn soft sm" type="button" data-view="${esc(x.id)}">Open</button></div>`).join('') || empty('None yet.')}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Checklists</h2><div class="r">${CAN() ? `<select class="in sm" data-ckind="1" aria-label="Checklist">${Object.entries(k.checklist_kinds || {}).map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select><button class="btn soft sm" type="button" data-newcl="1">Start one</button>` : ''}</div></div>
        ${(k.checklists || []).map(c => `<details class="qa-case" data-key="ck:${esc(c.id)}"${ST.open.has('ck:' + c.id) ? ' open' : ''}><summary><span style="flex:1"><b>${esc(c.title)}</b> <span class="mut">${esc(ago(c.created_at))}</span></span>${tag(c.done + ' / ' + c.total, c.complete ? 'ok' : 'warn')}</summary>
          <div class="qa-body">${c.items.map(i => `<label class="dv-item"><input type="checkbox" data-tick="${esc(c.id)}" data-item="${esc(i.id)}"${i.done ? ' checked' : ''}${CAN() ? '' : ' disabled'}><span><span class="mut">${esc(i.section)}:</span> ${esc(i.text)}</span></label>`).join('')}</div></details>`).join('') || empty('None yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, g = s.github || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your GitHub connection, team, morning summary, your own deploy rules, and your country and how long your rules keep server logs.</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">GitHub</h2>${g.joined ? `<div class="cs-row"><span style="flex:1">Connected as <b>@${esc(g.login)}</b></span>${CAN() ? '<button class="btn soft sm" type="button" data-act="github_forget">Remove</button>' : ''}</div><p class="cs-note">Remove it here, and also revoke the token in GitHub > Settings > Developer settings.</p>`
          : CAN() ? `<form data-form="github"><input class="in" name="token" type="password" autocomplete="off" maxlength="300" placeholder="GitHub token (github_pat_...)" aria-label="GitHub token" style="width:100%"><p class="cs-note">A fine-grained token with Actions read and write, Contents read, Deployments read and write, on the repos you choose. It is checked with GitHub, sealed, and never shown again - also not in the chat.</p><div class="md-acts"><span></span><button class="btn" type="submit">Connect</button></div></form>` : ''}</section>
        <form class="card" data-form="dvset"><h2 class="md-h2">Your DevOps</h2><div class="md-form">
          <div class="md-field"><label for="dvS1">Team</label><input class="in" id="dvS1" name="team" maxlength="160" value="${esc(s.team || '')}"></div>
          <div class="md-field"><label for="dvS2">Morning summary at</label><input class="in" id="dvS2" name="morning_time" type="time" value="${esc(s.morning_time || '09:30')}"></div>
          <div class="md-field"><label for="dvS3">Country (two letters)</label><input class="in" id="dvS3" name="country" maxlength="2" value="${esc(s.country || '')}"></div>
          <div class="md-field"><label for="dvS4">Keep server logs for (days)</label><input class="in" id="dvS4" name="log_days" inputmode="numeric" value="${esc(s.log_days ?? '')}" placeholder="${s.country === 'IN' ? '180 (CERT-In)' : 'your rule'}"></div>
          <div class="md-field wide"><label for="dvS5">Your deploy rules (one per line - added to every deploy checklist)</label><textarea class="in" id="dvS5" name="rules" rows="4" maxlength="2000">${esc(s.rules || '')}</textarea></div></div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form></div>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Run a script or a command anywhere, or log in to your server', 'Deploy, approve or re-run without your tap', 'Show your token back - not here, not in the chat', 'Keep raw logs - only a masked sample of each error kind', 'Assume another country\'s log rules for yours'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  function saveText(name, text) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type: 'text/plain'})); a.download = name || 'file.txt'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  async function getScript(cid) {
    try {
      const r = await fetch(`/api/devops/collectors/${enc(cid)}/script`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      saveText('hoola_log_agent.py', await r.text());
    } catch (e) { toast(e.message, true); }
  }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const sc = t.closest('[data-script]'); if (sc) { getScript(sc.dataset.script); return; }
    const vw = t.closest('[data-view]'); if (vw) { try { ST.out.script = await run('script_view', {id: vw.dataset.view}); showPage(true); } catch (err) { toast(err.message, true); } return; }
    const rb = t.closest('[data-rb]'); if (rb) { try { ST.out['rb:' + rb.dataset.rb] = await run('runbook', {id: rb.dataset.rb}); showPage(true); } catch (err) { toast(err.message, true); } return; }
    if (t.closest('[data-copy]')) { try { await navigator.clipboard.writeText((ST.out.script || {}).content || ''); toast('Copied.'); } catch { toast('Could not copy here - use Download.', true); } return; }
    if (t.closest('[data-save]')) { const v = ST.out.script || {}; saveText(v.name, v.content || ''); return; }
    if (t.closest('[data-newcl]')) { const k = ($('[data-ckind]') || {}).value || 'deploy'; try { const r = await run('checklist', {kind: k}); ST.open.add('ck:' + ((r.checklist || r).id || '')); await changed('Checklist started.'); } catch (err) { toast(err.message, true); } return; }
    try {
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act, d = a.dataset;
        if (act === 'github_forget' && !confirm('Remove the GitHub connection from Hoola?')) return;
        if (act === 'forget_logs' && !confirm('Forget every error kind Hoola has read?')) return;
        if (act === 'collector_revoke' && !confirm('Stop this collector? Its secret stops working at once.')) return;
        if (act === 'rerun' && !confirm('Re-run the failed jobs of this build on GitHub?')) return;
        a.disabled = true;
        const say = r => (r && r.say) || 'Done.';
        if (act === 'sync') { toast('Checking GitHub…'); await changed(say(await run('sync'))); }
        else if (act === 'watch') { toast('Checking your sites…'); await changed(say(await run('watch'))); }
        else if (act === 'diagnose') { await run('diagnose', {run: d.run}); ST.open.add('r:' + d.run); await changed('Explained.'); }
        else if (act === 'rerun') await changed(say(await run('rerun', {run: d.run})));
        else if (act === 'repo_remove') await changed(say(await run('repo_remove', {repo: d.repo})));
        else if (act === 'endpoint_remove') await changed(say(await run('endpoint_remove', {id: d.id})));
        else if (act === 'collector_revoke') { delete ST.out.collector; await changed(say(await run('collector_revoke', {id: d.id}))); }
        else if (act === 'cluster') await changed(say(await run('cluster', {id: d.id, status: d.st})));
        else if (act === 'forget_logs') await changed(say(await run('forget_logs')));
        else if (act === 'cancel') await changed(say(await run('cancel', {deploy: d.d})));
        else if (act === 'reject_github') { if (!confirm('Reject this run on GitHub too? It stops there.')) { a.disabled = false; return; } await changed(say(await run('reject_github', {deploy: d.d, hash: d.h}))); }
        else if (act === 'reviewed') { await run('reviewed', {id: d.id}); ST.out.script = await run('script_view', {id: d.id}); await changed('Marked as reviewed.'); }
        else if (act === 'github_forget') await changed(say(await run('github_forget')));
        return;
      }
    } catch (err2) { toast(err2.message, true); const a = t.closest('[data-act]'); if (a) a.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    try {
      if (el.dataset.rfilter !== undefined) { ST.rf = el.value; showPage(true); return; }
      if (el.dataset.tkind) { ST.tk = el.value; showPage(true); return; }
      if (el.dataset.tick) { await run('tick', {checklist: el.dataset.tick, item: el.dataset.item, done: el.checked}); await changed(''); return; }
      if (el.dataset.upfile) { const f = el.files && el.files[0]; if (!f) return; if (f.size > 500000) throw new Error('That file is over 500 KB - paste the part with the errors.');
        const box = el.closest('form').querySelector('[name=text]'); box.value = await f.text(); toast('File read - tap Read them.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'github') { const tok = S(fd.get('token')).trim(); if (!tok) throw new Error('Paste the GitHub token.'); const r = await run('github', {token: tok}); await done(r.say || 'GitHub connected.'); }
      else if (kind === 'repo') { const r = await run('repo_add', {repo: g('repo'), deploy_workflow: g('deploy_workflow'), environment: g('environment'), rollback_workflow: g('rollback_workflow')}); await done(r.say || 'Watching it.'); }
      else if (kind === 'cilog') { if (!g('text')) throw new Error('Paste a build log.'); ST.out.cilog = await run('explain_log', {text: g('text')}); showPage(true); }
      else if (kind === 'deploy') { const r = await run('deploy', {repo: g('repo'), ref: g('ref'), environment: g('environment'), note: g('note')}); await done(r.say || 'Card ready - check it and tap.'); }
      else if (kind === 'rollback') { const r = await run('rollback', {repo: g('repo'), to: g('to'), note: g('note')}); await done(r.say || 'Rollback card ready.'); }
      else if (kind === 'decide') { const yes = btn && btn.dataset.yes === '1';
        if (yes && !confirm('Start your deploy workflow on GitHub now?')) return;
        const r = await run('decide', {deploy: form.dataset.id, hash: form.dataset.h, yes, reason: g('reason')}); await changed(r.say || (yes ? 'Started.' : 'Refused.')); }
      else if (kind === 'endpoint') { const r = await run('endpoint_add', {url: g('url'), name: g('name'), keyword: g('keyword')}); await done(r.say || 'Watching it.'); }
      else if (kind === 'logs') { if (!g('text')) throw new Error('Paste some log lines or choose a file.'); const r = await run('logs', {text: g('text'), source: g('source')}); await done(r.say || 'Read.'); }
      else if (kind === 'collector') { ST.out.collector = await run('collector', {name: g('name')}); ST.out.collector.name = g('name'); await done('Collector made - copy its secret now.'); }
      else if (kind === 'script') { const k = g('kind'), params = {};
        for (const [n, v] of fd.entries()) if (n.startsWith('p_') && S(v).trim()) params[n.slice(2)] = S(v).trim();
        ST.out.script = await run('script', {kind: k, params, ask: g('ask')}); await changed(ST.out.script.say || 'Made - review it below.'); }
      else if (kind === 'check') { if (!g('content')) throw new Error('Paste your script.'); ST.out.check = await run('check_script', {content: S(fd.get('content')), name: g('name')}); showPage(true); }
      else if (kind === 'dvset') { const ld = g('log_days'); const a = {team: g('team'), morning_time: g('morning_time'), rules: g('rules'), country: g('country').toUpperCase()};
        if (ld) a.log_days = Number(ld); await run('settings', a); await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn) btn.disabled = false; }
  }

  /* ---------------------------------------------------------------- files in the chat */
  function addFiles(list) {
    for (const f of list) {
      if (ST.files.length >= MAXF) { toast(`Up to ${MAXF} files in one message.`, true); break; }
      if (f.size > MAXB) { toast(`${f.name} is over 30 MB.`, true); continue; }
      const item = {name: f.name || 'file', id: '', state: 'up', key: Math.random().toString(36).slice(2)};
      ST.files.push(item); paintFiles();
      (async () => {
        try {
          if (!ST.chat) throw new Error('The chat is not open yet.');
          const fd = new FormData(); fd.append('file', f, f.name || 'file');
          const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, {form: fd});
          item.id = S(r.file_id || r.id); item.state = item.id ? 'ok' : 'bad';
        } catch (e) { item.state = 'bad'; item.err = e.message; toast(`${item.name}: ${e.message}`, true); }
        paintFiles();
      })();
    }
    if (ST.folded) $('#sdFold').click();
  }
  function paintFiles() {
    const box = $('#dvFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dvdesk/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (STARTERS[ST.tab] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-q]'); if (b) send(b.dataset.q); };
  }
  function setCtx(about) {
    ST.ctx = S(about);
    const box = $('#sdCtx');
    box.hidden = !ST.ctx;
    box.innerHTML = ST.ctx ? `<span class="pill">About: ${esc(ST.ctx)}<button type="button" aria-label="Remove">×</button></span>` : '';
    if (ST.ctx) box.querySelector('button').onclick = () => setCtx('');
    if (ST.folded) $('#sdFold').click();
    ST.bar.focus();
  }
  function merge(rows) {
    if (!ST.rows.length || !rows.length) { if (rows.length || !ST.rows.length) ST.rows = rows; return; }
    const got = new Set(rows.map(r => r.id)), have = new Map(ST.rows.map(r => [r.id, r]));
    if (ST.rows.some(r => r.id >= rows[0].id && !got.has(r.id))) { ST.rows = rows; return; }
    const max = ST.rows[ST.rows.length - 1].id;
    for (const r of rows) { if (r.id > max) ST.rows.push(r); else if (have.has(r.id)) have.get(r.id).text = r.text; }
  }
  const lastIsHers = () => { const l = ST.rows[ST.rows.length - 1]; return !!l && l.role === 'user'; };
  const stripHints = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  async function loadMsgs(first) {
    if (!ST.chat || ST.loading || !ST.thread) return;
    const chat = ST.chat; ST.loading = true;
    try {
      const ask = async () => { const seq = ST.seq; let r = null;
        try { r = await api('GET', `/api/conversations/${enc(chat)}/result`); } catch {}
        if (seq === ST.seq) ST.res = r; };
      if (!first && (ST.sending || ST.working || lastIsHers() || (ST.res && ST.res.needs_you))) await ask();
      let rows;
      try { rows = (await api('GET', `/api/conversations/${enc(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== ST.chat) return;
      merge(rows);
      if (first && lastIsHers()) await ask();
      paintThread();
    } finally { ST.loading = false; }
  }
  function paintThread() {
    if (!ST.thread) return;
    const st = ST.res ? S(ST.res.status) : null;
    const working = ST.sending || (st === null ? lastIsHers() : st === 'working' || st === 'queued');
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Working…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text),
      files: r.role === 'user' && Array.isArray(r.files) ? r.files : undefined}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) refreshDesk(true);      // a turn ended: a date or rate it set shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these files' : 'Read this file';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'dv' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
    catch (e) { ok = false; toast(e.message, true); mine.remove(); if (ST.bar) ST.bar.value = text; ST.files = ready; paintFiles(); }
    ST.sending = false;
    if (ok) { ST.seq++; ST.res = {status: 'queued', needs_you: false, line: ''}; await loadMsgs(false); }
    paintThread();
  }
  async function stopTurn() {
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/stop`); toast('Stopping.'); }
    catch (e) { toast(e.message, true); }
  }

  start();
})();


