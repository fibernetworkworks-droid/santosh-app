/* DATABASE DESK - the Database Engine Developer's own section, like the finance desks (owner: "Database Engine Developer same as
   finance desks"). A thin top bar, then the Database chat (its own conversation, kind 'dbengine') beside the desk's pages: Today,
   Plans, Queries, Schema, Lab (indexes proved in a throwaway SQLite database on generated rows), Benchmarks, Settings. The pages call
   /api/dbdesk/do/<part>; nothing connects to her database. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['plans', 'Plans'], ['queries', 'Queries'], ['schema', 'Schema'], ['lab', 'Lab'], ['bench', 'Benchmarks'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What can you check for me?', 'Why is my query slow?', 'Which index should I add first?'],
    plans: ['Explain this plan step by step', 'Why is the estimate so far off?', 'Would a different join help?'],
    queries: ['Rewrite this query to use an index', 'Is a covering index worth it here?', 'How do I page without OFFSET?'],
    schema: ['Which indexes can I drop?', 'Should this be a partial index?', 'How do I add an index without locking the table?'],
    lab: ['Why was my index not used?', 'Which column order is better?', 'How close is SQLite to my database?'],
    bench: ['Is this slowdown real or noise?', 'How do I run a fair pgbench?', 'What should I tune next?'],
    settings: ['Which settings matter most for PostgreSQL?', 'What counts as a slow query?', 'MySQL or PostgreSQL for this?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', prefill: null, busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dbdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dbdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'dbengine_dev', name: 'Database'} : null;
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
  const run = (part, a) => api('POST', '/api/dbdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dbdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Database Engine Developer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dbHire">Hire the Database Engine Developer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dbHire').onclick = async () => { try { await api('POST', '/api/employees/dbengine_dev/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Database</div><div class="sd-site" id="dbSite"></div></div>
          <span id="dbState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Database chat">
          <div class="sd-chathead"><div class="t"><b>Database chat</b><span>Paste an EXPLAIN, a query or a schema - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dbFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dbPick" multiple hidden accept=".txt,.log,.csv,.sql,.json,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Database desk" id="sdTabs"></nav>
          <div id="dbPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a plan or query, or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dbPick').click()});
    $('#dbPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dbdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dbdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dbdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dbPage').addEventListener('click', onPageClick);
    $('#dbPage').addEventListener('submit', onSubmit);
    $('#dbPage').addEventListener('change', onChange);
    $('#dbPage').addEventListener('input', onInput);
    $('#dbPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dbState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#dbSite').textContent = [({postgres: 'PostgreSQL', mysql: 'MySQL', mariadb: 'MariaDB', sqlite: 'SQLite', sqlserver: 'SQL Server', oracle: 'Oracle', other: 'Other'})[s.engine] || s.engine, s.version, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {plans: k.plans_bad || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dbdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dbPage'); if (!box) return;
    const fn = {today: pToday, plans: pPlans, queries: pQueries, schema: pSchema, lab: pLab, bench: pBench, settings: pSettings}[ST.tab] || pToday;
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
  const st_ = () => K().settings || {};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const SST = {open: ['Open', 'warn'], fixed: ['Done', 'ok'], ignored: ['Ignored', '']};
  const sTag = s => tag((SST[s] || [cap(s)])[0], (SST[s] || ['', ''])[1]);
  const pre = (t, cls) => `<pre class="dbk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = kind => (K().items || []).filter(x => !kind || x.kind === kind);
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Check', 'warn'], info: ['Note', '']};
  const ENG = {postgres: 'PostgreSQL', mysql: 'MySQL', mariadb: 'MariaDB', sqlite: 'SQLite', sqlserver: 'SQL Server', oracle: 'Oracle', other: 'Other'};
  const ms = v => v === null || v === undefined ? '—' : Number(v) < 1 ? num(Math.round(v * 1000) / 1000) + ' ms' : Number(v) < 10 ? num(Math.round(v * 100) / 100) + ' ms' : num(Math.round(v * 10) / 10) + ' ms';
  const rws = v => v === null || v === undefined ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 0});
  function pasteForm(kind, title, ph, extra, btn) {
    if (!CAN()) return '';
    return `<section class="card"><h2 class="md-h2">${esc(title)}</h2><form data-form="add" data-kind="${esc(kind)}" class="dbk-form">
      <textarea class="in mono dbk-ed" name="text" rows="8" spellcheck="false" placeholder="${esc(ph)}"></textarea>${extra || ''}
      <div class="dbk-row"><label class="btn soft dbk-file">Open a file<input type="file" data-fileto="text" accept=".txt,.log,.sql,.json,.csv,text/*" hidden></label>
      <input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(btn || 'Read it')}</button></div></form></section>`;
  }
  function brief(x) {
    const b = x.brief || {};
    if (x.kind === 'plan') return `${b.engine || ''}${b.ms ? ' · ' + ms(b.ms) : ''} · ${b.findings ? pl(b.findings, 'finding') : 'nothing serious'}`;
    if (x.kind === 'query') return `${b.errors ? pl(b.errors, 'serious finding') : 'no serious finding'}${b.suggest ? ' · ' + pl(b.suggest, 'index suggestion') : ''}`;
    if (x.kind === 'schema') return `${pl(b.tables || 0, 'table')} · ${b.errors ? pl(b.errors, 'serious finding') : 'no serious finding'}${b.warnings ? ', ' + pl(b.warnings, 'to check', 'to check') : ''}`;
    if (x.kind === 'lab') return b.after !== null && b.after !== undefined ? `${ms(b.before)} → ${ms(b.after)}${b.used ? '' : ' · index not used'}${b.same === false ? ' · result changed' : ''}` : `${ms(b.before)} without an index`;
    if (x.kind === 'bench') return `${b.tool || ''}${b.tps ? ' · ' + num(Math.round(b.tps)) + ' tps' : b.qps ? ' · ' + num(Math.round(b.qps)) + ' ops/s' : ''}${b.lat ? ' · ' + ms(b.lat) : ''}${b.worse ? ' · slower than baseline' : ''}`;
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="dbk-list">${list.map(x => `<button type="button" class="dbk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="dbk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="dbk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = (list, labBtn) => (list || []).length ? list.map(i => `<div class="dbk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><b>${esc(i.say)}</b><p>${esc(i.fix)}</p>${i.code ? `<code class="dbk-code1">${esc(i.code)}</code>` : ''}${i.sql ? `<div class="dbk-cmd"><code>${esc(i.sql)}</code>${copyBtn(i.sql)}</div>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  function suggestRows(sg, query) {
    if (!(sg || []).length) return '';
    return `<section class="card"><h2 class="md-h2">The index this query asks for</h2><p class="cs-note" style="margin-top:0">Equality columns first, then one range column or the ORDER BY. A suggestion until the lab or your own EXPLAIN shows it is used.</p>
      ${sg.map(x => `<div class="dbk-sug"><div><b>${esc(x.table)}</b> (${esc(x.cols.join(', '))})<span class="mut"> · ${esc(x.why)}</span></div><div class="dbk-cmd"><code>${esc(x.sql)}</code>${copyBtn(x.sql)}${CAN() && query ? `<button class="btn sm" type="button" data-tolab="${esc(x.sql)}" data-q="${esc(query)}">Prove it in the lab</button>` : ''}</div></div>`).join('')}</section>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, lb = k.last_bench;
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Plans with a serious finding', esc(num(k.plans_bad || 0)), `${pl(c.plan || 0, 'plan')} read`, k.plans_bad),
      tile('Indexes proved in the lab', esc(num(k.proved || 0)), k.best_speedup ? `best ${num(k.best_speedup)}x faster in SQLite` : `${pl(c.lab || 0, 'lab run')}`),
      tile('Queries and schemas', esc(num((c.query || 0) + (c.schema || 0))), `${pl(c.query || 0, 'query', 'queries')}, ${pl(c.schema || 0, 'schema')}`),
      tile('Last benchmark', lb ? (lb.brief.tps ? esc(num(Math.round(lb.brief.tps))) + '<small> tps</small>' : lb.brief.qps ? esc(num(Math.round(lb.brief.qps))) + '<small> ops/s</small>' : esc(ms(lb.brief.lat))) : '—', lb ? (lb.brief.worse ? 'slower than its baseline' : lb.brief.tool) : 'none yet', lb && lb.brief.worse)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="dbk-starts">
        <button type="button" class="dbk-start" data-go="plans"><b>Read a query plan</b><span>PostgreSQL, MySQL or SQLite EXPLAIN - where the time goes</span></button>
        <button type="button" class="dbk-start" data-go="queries"><b>Check a slow query</b><span>What stops an index, and the index it asks for</span></button>
        <button type="button" class="dbk-start" data-go="schema"><b>Review a schema</b><span>Keys, foreign-key indexes, redundant indexes, types</span></button>
        <button type="button" class="dbk-start" data-go="lab"><b>Prove an index</b><span>Before and after, in a throwaway SQLite lab</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- plans */
  function pPlans() {
    if (ST.arg) return one(ST.arg, 'plans', pPlan);
    return `<div><h1 class="sd-h">Query plans</h1><p class="lead">Paste what your database printed. Hoola reads it in code - it never connects to your database.</p></div>${ro()}
      ${pasteForm('plan', 'Read a plan', 'EXPLAIN (ANALYZE, BUFFERS) SELECT ...      -- PostgreSQL (text or FORMAT JSON)\nEXPLAIN ANALYZE SELECT ...                 -- MySQL 8\nEXPLAIN QUERY PLAN SELECT ...              -- SQLite')}
      <section class="card"><h2 class="md-h2">Plans read</h2>${itemRows(items('plan'))}</section>`;
  }
  function planTree(n, total, out) {
    const rows = n.rows, est = n.est_rows, loops = n.loops || 1;
    const ratio = rows !== null && rows !== undefined && est !== null && est !== undefined ? (rows + 1) / (est + 1) : null;
    const off = ratio !== null && (ratio >= 10 || ratio <= 0.1);
    const share = total && n.self_ms !== undefined ? Math.min(100, n.self_ms / total * 100) : 0;
    out.push(`<div class="dbk-node" style="--d:${n.depth || 0}"><div class="h"><b>${esc(n.op)}</b>${n.rel ? ` <span class="dbk-rel">${esc(n.rel)}${n.alias && n.alias !== n.rel ? ' ' + esc(n.alias) : ''}</span>` : ''}${n.index ? ` <span class="mut">using</span> <code>${esc(n.index)}</code>` : ''}</div>
      <div class="m"><span title="Rows the planner expected">plan ${esc(rws(est))}</span>${rows !== null && rows !== undefined ? `<span class="${off ? 'dbk-off' : ''}" title="Rows really returned">real ${esc(rws(rows))}${loops > 1 ? ' x ' + esc(rws(loops)) : ''}</span>` : ''}${n.self_ms !== undefined ? `<span>${esc(ms(n.self_ms))} here</span>` : ''}${n.never ? '<span class="mut">never executed</span>' : ''}</div>
      ${share ? `<i class="dbk-time" style="width:${share.toFixed(1)}%"></i>` : ''}
      ${(n.detail || []).length ? `<div class="dbk-det">${n.detail.slice(0, 8).map(x => `<span>${esc(x)}</span>`).join('')}</div>` : ''}</div>`);
    (n.children || []).forEach(c => planTree(c, total, out));
    return out;
  }
  function pPlan(d) {
    const r = d.result || {}, fs = r.findings || [];
    const tot = r.root && r.root.total_ms ? r.root.total_ms : r.total_ms;
    return `${head(d, 'plans')}
      <section class="card dbk-sum ${fs.some(f => f.sev === 'bad') ? 'badv' : 'okv'}"><p class="dbk-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('Total', esc(ms(r.total_ms)), r.planning_ms ? 'planning ' + ms(r.planning_ms) : (r.analyzed ? '' : 'estimates only'))}${tile('Steps', esc(num(r.steps)), r.engine)}
        ${tile('Findings', esc(num(fs.filter(f => f.sev !== 'info').length)), pl(fs.filter(f => f.sev === 'bad').length, 'serious', 'serious'), fs.some(f => f.sev === 'bad'))}${tile('Tables', esc(num((r.tables || []).length)), (r.tables || []).slice(0, 3).join(', '))}</div></section>
      <section class="card"><h2 class="md-h2">What to look at</h2>${fs.length ? fs.map(f => `<div class="dbk-issue"><span>${tag(SV[f.sev][0], SV[f.sev][1])}</span><div><b>${esc(f.say)}</b><p>${esc(f.fix)}</p>${f.cols && f.cols.length && f.rel ? `<div class="dbk-cmd"><code>CREATE INDEX ON ${esc(f.rel)} (${esc(f.cols.join(', '))});</code>${copyBtn(`CREATE INDEX ON ${f.rel} (${f.cols.join(', ')});`)}</div>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>'}</section>
      <section class="card"><h2 class="md-h2">The plan, step by step</h2><p class="cs-note" style="margin-top:0">Indented steps feed the step above them. The bar is the time spent in the step itself; red rows are far from the planner's estimate.</p><div class="dbk-tree">${r.root ? planTree(r.root, tot, []).join('') : ''}</div></section>
      <details class="card dbk-raw"><summary>What you pasted</summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- queries */
  function pQueries() {
    if (ST.arg) return one(ST.arg, 'queries', pQuery);
    return `<div><h1 class="sd-h">Queries</h1><p class="lead">One query at a time: what stops an index being used, and the index it asks for.</p></div>${ro()}
      ${pasteForm('query', 'Check a query', "SELECT ... FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.status = 'paid' ORDER BY o.created_at DESC LIMIT 50", '', 'Check it')}
      <section class="card"><h2 class="md-h2">Queries checked</h2>${itemRows(items('query'))}</section>`;
  }
  function pQuery(d) {
    const r = d.result || {};
    return `${head(d, 'queries')}
      <section class="card dbk-sum ${(r.counts || {}).bad ? 'badv' : 'okv'}"><p class="dbk-big">${esc(r.verdict)}</p>${pre(r.sql || d.text, 'sql')}</section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>
      ${suggestRows(r.suggest, r.sql || d.text)}`;
  }

  /* ---------------------------------------------------------------- schema */
  function pSchema() {
    if (ST.arg) return one(ST.arg, 'schema', pSch);
    return `<div><h1 class="sd-h">Schema</h1><p class="lead">CREATE TABLE and CREATE INDEX statements - from pg_dump --schema-only, SHOW CREATE TABLE or .schema. The lab uses your latest schema.</p></div>${ro()}
      ${pasteForm('schema', 'Review a schema', 'CREATE TABLE orders (\n  id bigint PRIMARY KEY,\n  customer_id bigint REFERENCES customers(id),\n  ...\n);\nCREATE INDEX ...;', '', 'Review it')}
      <section class="card"><h2 class="md-h2">Schemas reviewed</h2>${itemRows(items('schema'))}</section>`;
  }
  function pSch(d) {
    const r = d.result || {};
    const ixOf = t => (r.indexes || []).filter(i => i.table.toLowerCase() === t.name.toLowerCase());
    return `${head(d, 'schema')}
      <section class="card dbk-sum ${(r.counts || {}).bad ? 'badv' : 'okv'}"><p class="dbk-big">${esc(r.verdict)}</p></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>
      <section class="card"><h2 class="md-h2">Tables</h2><div class="dbk-tables">${(r.tables || []).map(t => `<div class="dbk-tbl"><div class="h"><b>${esc(t.name)}</b><span class="mut">${esc(pl(t.columns.length, 'column'))}</span></div>
        <table class="tb"><tbody>${t.columns.map(c => `<tr><td><code>${esc(c.name)}</code>${t.pk.includes(c.name) ? ' ' + tag('PK', 'ok') : ''}${t.fks.some(f => f.cols.includes(c.name)) ? ' ' + tag('FK → ' + t.fks.find(f => f.cols.includes(c.name)).ref, '') : ''}</td><td class="mut">${esc(c.type)}${c.null ? '' : ' · not null'}</td></tr>`).join('')}</tbody></table>
        ${ixOf(t).length ? `<div class="dbk-ix">${ixOf(t).map(i => `<span>${i.unique ? 'unique ' : ''}<code>${esc(i.name || 'index')}</code> (${esc(i.cols.join(', '))})</span>`).join('')}</div>` : ''}</div>`).join('')}</div></section>`;
  }

  /* ---------------------------------------------------------------- lab */
  function pLab() {
    if (ST.arg) return one(ST.arg, 'lab', pLabOne);
    const hasSchema = items('schema').length > 0, pf = ST.prefill || {};
    return `<div><h1 class="sd-h">Lab</h1><p class="lead">Your schema, built in a throwaway SQLite database on the server and filled with generated rows - none of your data. Your query runs before and after the index.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Prove an index</h2><form data-form="lab" class="dbk-form">
        <label class="ins-lab">The query (SELECT)<textarea class="in mono dbk-ed" name="text" rows="5" spellcheck="false" placeholder="SELECT ... FROM ... WHERE ...">${esc(pf.q || '')}</textarea></label>
        <label class="ins-lab">The index to try<textarea class="in mono" name="indexes" rows="2" spellcheck="false" placeholder="CREATE INDEX ON orders (customer_id, status, created_at);">${esc(pf.ix || '')}</textarea></label>
        <details class="dbk-cmp"${hasSchema ? '' : ' open'}><summary>${hasSchema ? 'Use another schema (optional - else your latest one)' : 'Your schema (CREATE TABLE statements)'}</summary><textarea class="in mono" name="schema" rows="6" spellcheck="false" placeholder="CREATE TABLE ..."></textarea></details>
        <div class="dbk-row"><label class="ins-lab">Rows per table<select class="in" name="rows">${[10000, 50000, 100000, 200000].map(n => `<option value="${n}"${n === Number(st_().lab_rows) ? ' selected' : ''}>${num(n)}</option>`).join('')}</select></label>
        <input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Run the lab</button></div></form>
        <p class="cs-note">SQLite ${esc((K().health || {}).sqlite || '')} on generated rows: it shows whether the index is used and how the work changes - not your server's timings. Tables a foreign key points at get a twentieth of the rows.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Lab runs</h2>${itemRows(items('lab'))}</section>`;
  }
  function pLabOne(d) {
    const r = d.result || {}, b = r.before || {}, a = r.after;
    const mx = Math.max(b.ms || 0, (a && a.ms) || 0) || 1;
    const side = (x, name) => `<div class="dbk-side"><div class="h"><b>${esc(name)}</b><span>${esc(ms(x.ms))}</span></div><i class="dbk-bar" style="width:${Math.max(1, x.ms / mx * 100).toFixed(1)}%"></i>
      <div class="dbk-eqp">${(x.plan || []).map(p => `<code class="${p.startsWith('SCAN') && !p.includes('USING') ? 'scan' : p.startsWith('SEARCH') || p.includes('USING') ? 'seek' : ''}">${esc(p)}</code>`).join('')}</div><span class="mut">${esc(rws(x.rows))} row(s) returned</span></div>`;
    return `${head(d, 'lab')}
      <section class="card dbk-sum ${a ? (r.used && r.same_result ? 'okv' : 'badv') : 'okv'}"><p class="dbk-big">${esc(r.verdict)}</p><p class="cs-note" style="margin:0">${esc(r.note)}</p></section>
      ${a ? `<section class="cs-hero"><div class="top">${tile('Without', esc(ms(b.ms)), b.full_scans && b.full_scans.length ? 'full scan' : '')}${tile('With the index', esc(ms(a.ms)), r.used ? 'index used' : 'index not used', !r.used)}${tile('Faster', r.speedup ? esc(num(r.speedup)) + '<small>x</small>' : '—', 'in SQLite')}${tile('Same rows', r.same_result ? 'Yes' : 'No', '', r.same_result === false)}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">${a ? 'Before and after' : 'The run'}</h2><div class="dbk-two">${side(b, 'Without the index')}${a ? side(a, 'With the index') : ''}</div></section>
      <section class="card"><h2 class="md-h2">What ran</h2>${pre(r.query || '', 'sql')}${(r.indexes || []).length ? pre(r.indexes.join(';\n') + ';', 'sql') : ''}<p class="cs-note">Generated rows: ${esc(Object.entries(r.rows || {}).map(([t, n]) => t + ' ' + rws(n)).join(', '))} · schema from ${esc(r.schema_from || '')}${(r.existing || []).length ? ' · your indexes built too: ' + esc(r.existing.join(', ')) : ''}.</p></section>`;
  }

  /* ---------------------------------------------------------------- benchmarks */
  function pBench() {
    if (ST.arg) return one(ST.arg, 'bench', pBenchOne);
    const bs = items('bench');
    return `<div><h1 class="sd-h">Benchmarks</h1><p class="lead">pgbench, sysbench, YCSB or HammerDB output, or latencies in ms - and how a run compares with its baseline.</p></div>${ro()}
      ${pasteForm('bench', 'Read a run', 'pgbench (16.2)\n...\ntps = 8538.9 (without initial connection time)', bs.length ? `<label class="ins-lab">Compare with<select class="in" name="baseline"><option value="">No baseline</option>${bs.map(x => `<option value="${esc(x.id)}">${esc(x.number)} · ${esc(x.title)}</option>`).join('')}</select></label>` : '')}
      <section class="card"><h2 class="md-h2">Runs</h2>${itemRows(bs)}</section>`;
  }
  function pBenchOne(d) {
    const r = d.result || {}, c = r.compare;
    return `${head(d, 'bench')}
      ${c ? `<section class="card dbk-sum ${c.rows.some(x => x.verdict === 'worse') ? 'badv' : 'okv'}"><p class="dbk-big">${esc(c.verdict)}</p><p class="cs-note" style="margin:0">Against ${esc(r.baseline.number)} · ${esc(r.baseline.title)} · noise ±${esc(num(c.noise_pct))}%</p>${c.notes.map(n => `<p class="cs-note kd-warn">${esc(n)}</p>`).join('')}</section>` : ''}
      <section class="cs-hero"><div class="top">${r.tps ? tile('Transactions / s', esc(num(Math.round(r.tps))), r.clients ? pl(r.clients, 'client') : '') : ''}${r.qps ? tile('Queries / s', esc(num(Math.round(r.qps))), '') : ''}
        ${r.lat_avg !== null && r.lat_avg !== undefined ? tile('Average latency', esc(ms(r.lat_avg)), r.lat_p95 ? 'p95 ' + ms(r.lat_p95) : '') : ''}${r.lat_max ? tile('Worst', esc(ms(r.lat_max)), r.lat_p99 ? 'p99 ' + ms(r.lat_p99) : '') : ''}${r.errors !== null && r.errors !== undefined ? tile('Errors', esc(num(r.errors)), r.tool, r.errors > 0) : ''}</div></section>
      ${c ? `<section class="card"><h2 class="md-h2">Change</h2><table class="tb"><thead><tr><th>Measure</th><th class="r">Baseline</th><th class="r">This run</th><th class="r">Change</th><th></th></tr></thead><tbody>${c.rows.map(x => `<tr><td>${esc(x.name)}</td><td class="r">${esc(num(x.a))}</td><td class="r">${esc(num(x.b))}</td><td class="r ${x.verdict === 'worse' ? 'cs-neg' : x.verdict === 'better' ? 'cs-pos' : ''}">${esc((x.change_pct > 0 ? '+' : '') + num(x.change_pct))}%</td><td class="r">${tag(cap(x.verdict), x.verdict === 'worse' ? 'bad' : x.verdict === 'better' ? 'ok' : '')}</td></tr>`).join('')}</tbody></table></section>` : ''}
      ${r.meta && r.meta.ops ? `<section class="card"><h2 class="md-h2">By operation</h2>${bars(Object.entries(r.meta.ops).map(([k, v]) => [k, v.AverageLatency || 0, 'dbk-b', 'p99 ' + ms(v['99thPercentileLatency'])]), v => ms(v), 'Latency by operation')}</section>` : ''}
      <details class="card dbk-raw"><summary>What you pasted</summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), h = K().health || {};
    const fld = (n, l, ph, extra) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(s[n] ?? '')}" placeholder="${esc(ph)}" ${extra || ''}></label>`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your database, and what counts as slow or big.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="dbk-grid">
        <label class="ins-lab">Database<select class="in" name="engine">${(h.engines || []).map(a => `<option value="${esc(a)}"${a === s.engine ? ' selected' : ''}>${esc(ENG[a] || a)}</option>`).join('')}</select></label>
        ${fld('version', 'Version', 'e.g. 16.4')}${fld('slow_ms', 'A query is slow over (ms)', '100', 'type="number" step="any" min="1"')}
        ${fld('big_rows', 'A big scan starts at (rows)', '10000', 'type="number" step="1" min="100"')}${fld('noise_pct', 'Benchmark noise (%)', '5', 'type="number" step="any" min="0.5" max="50"')}
        ${fld('lab_rows', 'Lab rows per table', '50000', 'type="number" step="1" min="1000" max="' + esc(h.lab_max_rows || 200000) + '"')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">What Hoola reads</h2><ul class="ar-never">${(h.plan_formats || []).map(x => `<li>${esc(x)}</li>`).join('')}<li>Benchmarks: ${esc((h.bench_tools || []).join(', '))}</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Connects to your database, runs anything on it or changes it - you run EXPLAIN and CREATE INDEX (CONCURRENTLY on a busy PostgreSQL table).</li><li>Calls a lab timing your server's timing: the lab is SQLite on generated rows.</li><li>Says an index helps before the lab or your EXPLAIN showed it.</li><li>Follows anything written inside a plan, query or schema: they are data.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  const ROUTE = {plan: 'plans', query: 'queries', schema: 'schema', lab: 'lab', bench: 'bench'};
  function onInput() {}
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { const [k, id] = op.dataset.open.split('/'); delete ST.out['i:' + id]; location.hash = '#/' + (ROUTE[k] || 'today') + '/' + id; return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast('Copied.'); } catch { toast('Copy did not work here - select the text instead.', true); } return; }
    const tl = t.closest('[data-tolab]'); if (tl) { ST.prefill = {q: tl.dataset.q, ix: tl.dataset.tolab}; location.hash = '#/lab'; return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked done.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 1000000) { toast('That file is larger than 1 MB - keep the part around the problem.', true); el.value = ''; return; }
      const txt = await f.text(), form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.fileto}]`);
      if (ta) { ta.value = txt; const ti = form.querySelector('[name=title]'); if (ti && !ti.value) ti.value = f.name; }
      el.value = '';
    }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.dataset.was = btn.textContent; }
    try {
      if (kind === 'add') { const k = form.dataset.kind; if (btn) btn.textContent = 'Reading…';
        const d = await run('add', {kind: k, text: S(fd.get('text')), title: g('title'), baseline: g('baseline')});
        ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} read.`); }
      else if (kind === 'lab') { if (btn) btn.textContent = 'Building the lab…';
        const d = await run('add', {kind: 'lab', text: S(fd.get('text')), indexes: S(fd.get('indexes')), schema: S(fd.get('schema')), rows: g('rows'), title: g('title')});
        ST.prefill = null; ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/lab/' + d.id; toast(`${d.number}: ${d.result.verdict}`); }
      else if (kind === 'settings') { const a = {}; ['engine', 'version', 'slow_ms', 'big_rows', 'noise_pct', 'lab_rows'].forEach(n => { a[n] = g(n); });
        await run('settings', a); await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
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
    const box = $('#dbFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dbdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'db' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


