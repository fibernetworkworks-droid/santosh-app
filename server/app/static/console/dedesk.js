/* DATA ENGINEER DESK - the Data Engineer's own section, like the finance desks (owner: "Data Engineer same as finance desks").
   A thin top bar, then the Data chat (its own conversation, kind 'dataeng') beside the desk's pages: Today, Pipelines, Contracts,
   Reconcile, Runs, Storage, CI check, Settings. The pages call /api/dedesk/do/<part>; nothing runs on her machines or warehouse. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/><circle cx="16.5" cy="16.5" r="1"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['pipelines', 'Pipelines'], ['contracts', 'Contracts'], ['reconcile', 'Reconcile'], ['runs', 'Runs'], ['storage', 'Storage'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start with a pipeline that keeps failing?', 'How do I make a load safe to run twice?', 'What should a data contract hold?'],
    pipelines: ['Why does my DAG take so long?', 'How do I backfill safely?', 'Should this be one task or two?'],
    contracts: ['How do I rename a column without breaking readers?', 'Is changing int to bigint safe?', 'How do I version a schema?'],
    reconcile: ['Why do the row counts not match?', 'How do I reconcile a huge table?', 'Where do duplicates come from?'],
    runs: ['How do I stop a flaky job?', 'What should I alert on?', 'How do I catch a load with no rows?'],
    storage: ['What file size should Parquet files be?', 'How should I partition this table?', 'How do I cut scan costs?'],
    ci: ['How do I test dbt models in CI?', 'Where do warehouse keys go?', 'How do I keep CI fast?'],
    settings: ['What key should I reconcile on?', 'What freshness limit is sensible?', 'What goes in a contract file?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'pipelines', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dedesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dedesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'data', name: 'Data'} : null;
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
  const run = (part, a) => api('POST', '/api/dedesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dedesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Data Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="deHire">Hire the Data Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#deHire').onclick = async () => { try { await api('POST', '/api/employees/data_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Data</div><div class="sd-site" id="deSite"></div></div>
          <span id="deState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Data chat">
          <div class="sd-chathead"><div class="t"><b>Data chat</b><span>Paste a pipeline, a schema, tables, a run history or a listing - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="deFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dePick" multiple hidden accept=".txt,.json,.csv,.tsv,.sql,.yaml,.yml,.avsc,.log,.md,.py,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Data desk" id="sdTabs"></nav>
          <div id="dePage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a pipeline or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dePick').click()});
    $('#dePick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dedesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dedesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dedesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dePage').addEventListener('click', onPageClick);
    $('#dePage').addEventListener('submit', onSubmit);
    $('#dePage').addEventListener('change', onChange);
    $('#dePage').addEventListener('input', onInput);
    $('#dePage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#deState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#deSite').textContent = [s.key_cols && 'key ' + s.key_cols, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dedesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dePage'); if (!box) return;
    const fn = {today: pToday, pipelines: pPipelines, contracts: pContracts, reconcile: pReconcile, runs: pRuns, storage: pStorage, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="dek-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {dag: 'Pipeline', schema: 'Contract', recon: 'Reconcile', runs: 'Runs', storage: 'Storage'};
  const ROUTE = {dag: 'pipelines', schema: 'contracts', recon: 'reconcile', runs: 'runs', storage: 'storage'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(1);
  const MIN = v => { if (v === null || v === undefined) return '—'; const x = Number(v); return x < 1 ? Math.round(x * 60) + ' s' : x < 120 ? P4(x) + ' min' : P4(x / 60) + ' h'; };
  const HB = v => { const b = Number(v); for (const [u, d] of [['TB', 1024 ** 4], ['GB', 1024 ** 3], ['MB', 1024 ** 2], ['KB', 1024]]) if (b >= d) return P4(b / d) + ' ' + u; return Math.round(b) + ' B'; };
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'dag': return b.loop ? `${pl(b.tasks || 0, 'task')} · has a loop` : `${pl(b.tasks || 0, 'task')} · ${pl(b.levels || 0, 'level')}${b.crit !== null && b.crit !== undefined ? ' · critical path ' + MIN(b.crit) : ''}`;
      case 'schema': return b.mode === 'one' ? `${pl(b.cols || 0, 'column')} · on its own` : `${pl(b.changes || 0, 'change')} · ${num(b.breaking || 0)} breaking`;
      case 'recon': return `${num(b.rows)} source rows · ${num(b.missing)} missing · ${num(b.extra)} extra · ${num(b.changed)} changed`;
      case 'runs': return `${pl(b.jobs || 0, 'job')} · ${num(b.runs)} runs · ${num(b.failed)} failed${b.failing ? ` · ${b.failing} failing now` : ''}`;
      case 'storage': return `${pl(b.files || 0, 'file')} · ${HB(b.total || 0)}${b.small ? ` · ${num(b.small)} small` : ''}${b.parts ? ` · ${pl(b.parts, 'partition')}` : ''}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="dek-list">${list.map(x => `<button type="button" class="dek-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="dek-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="dek-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="dek-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="dek-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono dek-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft dek-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="dek-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card dek-sum ${ok ? 'okv' : 'badv'}"><p class="dek-big">${esc(r.verdict)}</p>${r.counts ? `<div class="dek-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="dek-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
  const nice = (lo, hi, n = 5) => { if (hi - lo < 1e-12) { hi = lo + 1; } const raw = (hi - lo) / n, p = Math.pow(10, Math.floor(Math.log10(raw))), st = [1, 2, 2.5, 5, 10].map(m => m * p).find(m => m >= raw) || raw; const out = []; for (let v = Math.ceil(lo / st) * st; v <= hi + st * 1e-6; v += st) out.push(+v.toPrecision(12)); return out; };
  /* series: [{name, pts: [[x, y]], cls, dash}] - a line chart with its own axes */
  function lines(series, xl, yl, aria, opt) {
    const all = series.flatMap(s2 => s2.pts); if (!all.length) return '';
    const W = 760, H = 300, L = 54, R = 14, T0 = 12, B = 40;
    let x0 = Math.min(...all.map(p => p[0])), x1 = Math.max(...all.map(p => p[0])), y0 = Math.min(0, ...all.map(p => p[1])), y1 = Math.max(...all.map(p => p[1]));
    if (opt && opt.ymax !== undefined) y1 = Math.min(y1, opt.ymax); if (y1 - y0 < 1e-9) y1 = y0 + 1;
    const xt = nice(x0, x1), yt = nice(y0, y1);
    x0 = Math.min(x0, xt[0]); x1 = Math.max(x1, xt[xt.length - 1]); y0 = Math.min(y0, yt[0]); y1 = Math.max(y1, yt[yt.length - 1]);
    const X = v => L + (v - x0) / (x1 - x0 || 1) * (W - L - R), Y = v => T0 + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T0 - B);
    const grid = yt.map(v => `<line class="g" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${esc(P4(v))}</text>`).join('')
      + xt.map(v => `<text class="tx" x="${X(v).toFixed(1)}" y="${H - B + 16}" text-anchor="middle">${esc(P4(v))}</text>`).join('');
    const ref = opt && opt.ref !== undefined ? `<line class="ref" x1="${L}" x2="${W - R}" y1="${Y(opt.ref).toFixed(1)}" y2="${Y(opt.ref).toFixed(1)}"/>` : '';
    const paths = series.map(s2 => `<polyline class="ln ${s2.cls || ''}${s2.dash ? ' dash' : ''}" points="${s2.pts.map(p => `${X(p[0]).toFixed(1)},${Y(Math.min(y1, Math.max(y0, p[1]))).toFixed(1)}`).join(' ')}"><title>${esc(s2.name)}</title></polyline>`).join('');
    const key = `<div class="dek-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="dek-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  const N2 = v => Number(v).toLocaleString('en', {maximumFractionDigits: 2});
  const SEVC = {breaking: 'bad', warn: 'warn', safe: 'ok'};

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), g = k.dag, c = k.schema, r = k.recon, j = k.runs, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Pipeline', g ? (g.loop ? 'Loop' : g.crit !== null && g.crit !== undefined ? esc(MIN(g.crit)) : esc(num(g.tasks)) + ' <small>tasks</small>') : '—', g ? `${g.loop ? 'it cannot run' : g.crit !== null && g.crit !== undefined ? 'critical path · ' + pl(g.tasks, 'task') : pl(g.levels, 'level')} · ${g.number}` : 'paste a pipeline', g && g.bad),
      tile('Contract', c ? (c.mode === 'one' ? esc(num(c.cols)) + ' <small>columns</small>' : esc(num(c.breaking || 0)) + ' <small>breaking</small>') : '—', c ? `${c.mode === 'one' ? 'checked on its own' : pl(c.changes || 0, 'change')} · ${c.number}` : 'paste a schema', c && c.bad),
      tile('Reconcile', r ? (r.missing || r.extra || r.changed ? esc(num((r.missing || 0) + (r.extra || 0) + (r.changed || 0))) + ' <small>rows off</small>' : 'Match') : '—', r ? `${num(r.rows)} source rows · ${r.number}` : 'paste two tables', r && r.bad),
      tile('Runs', j ? (j.failing ? esc(num(j.failing)) + ' <small>failing now</small>' : esc(num(j.failed)) + ' <small>failed</small>') : '—', j ? `${pl(j.jobs, 'job')}, ${num(j.runs)} runs · ${j.number}` : 'paste a run history', j && j.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.key_cols ? 'Key: ' + s.key_cols + '.' : 'Set your key columns and time limits in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="dek-path">
        <li><button type="button" data-go="pipelines"><b>Make it finish</b><span>Loops, lone tasks and the chain that sets how long a run takes</span></button></li>
        <li><button type="button" data-go="contracts"><b>Keep the shape</b><span>Schema changes against the contract: what breaks readers, what is safe</span></button></li>
        <li><button type="button" data-go="reconcile"><b>Prove the load</b><span>Source against target on the key: missing, extra, duplicate and changed rows</span></button></li>
        <li><button type="button" data-go="runs"><b>Watch it run</b><span>Failing and slow jobs, zero-row loads and data that has gone stale</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- pipelines */
  const SAMPLE_DAG = "extract_orders >> clean_orders >> join >> load\nextract_customers >> clean_customers >> join\nextract_orders = 12m\nclean_orders = 25m\njoin = 18m\nload = 9m";
  function pPipelines() {
    if (ST.arg) return one(ST.arg, 'pipelines', pPl);
    const s = st_();
    return `<div><h1 class="sd-h">Pipelines</h1><p class="lead">A pipeline read as a graph: loops that stop it running, tasks linked to nothing, what runs side by side, and the critical path - the chain that sets how long a run takes - against your run window.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a pipeline</h2><form data-form="dag" class="dek-grid">
        ${area('text', "Airflow lines (a >> b, [a, b] >> c), arrows (a -> b), lists (orders: stg_orders, stg_customers) or a dbt manifest.json - add durations as 'task = 12m'", SAMPLE_DAG, 12)}
        ${fld('window', 'Run window (minutes)', s.window_min || '', 'type="number" min="0" step="any"', '60')}${subRow('Read it', '.py,.json,.txt,.yml,.yaml,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('dag'))}</section>`;
  }
  function graph(r) {
    const lv = r.levels || [];
    const n = lv.reduce((a, l) => a + l.length, 0);
    if (!n || n > 90) return n ? `<p class="mut">${esc(num(n))} tasks - too many to draw; the levels are listed below.</p>` : '';
    const hot = new Set(r.critical ? r.critical.path : []);
    const W = 168, H = 34, GX = 70, GY = 16, P = 10;
    const pos = {};
    const tallest = Math.max(...lv.map(l => l.length));
    lv.forEach((l, i) => l.forEach((t, j) => { pos[t] = [P + i * (W + GX), P + j * (H + GY) + (tallest - l.length) * (H + GY) / 2]; }));
    const VW = P * 2 + lv.length * W + (lv.length - 1) * GX, VH = P * 2 + tallest * H + (tallest - 1) * GY;
    const edges = (r.edges || []).map(([a, b]) => { const [x1, y1] = pos[a], [x2, y2] = pos[b]; const sx = x1 + W, sy = y1 + H / 2, ex = x2, ey = y2 + H / 2, mx = (sx + ex) / 2; const h = hot.has(a) && hot.has(b) && r.critical.path.indexOf(b) === r.critical.path.indexOf(a) + 1; return `<path class="e${h ? ' hot' : ''}" d="M${sx},${sy} C${mx},${sy} ${mx},${ey} ${ex},${ey}"/>`; }).join('');
    const dur = r.durations || {};
    const nodes = Object.entries(pos).map(([t, [x, y]]) => `<g class="nd${hot.has(t) ? ' hot' : ''}${(r.lone || []).includes(t) ? ' lone' : ''}"><rect x="${x}" y="${y}" width="${W}" height="${H}" rx="9"/><text x="${x + 10}" y="${y + 21}">${esc(t.length > 19 ? t.slice(0, 18) + '…' : t)}</text>${dur[t] !== undefined ? `<text class="d" x="${x + W - 8}" y="${y + 21}" text-anchor="end">${esc(MIN(dur[t]))}</text>` : ''}<title>${esc(t)}</title></g>`).join('');
    return `<div class="dek-dag"><svg viewBox="0 0 ${VW} ${VH}" width="${VW}" role="img" aria-label="Pipeline graph"><defs><marker id="dekA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z"/></marker></defs>${edges}${nodes}</svg></div>`;
  }
  function gantt(r) {
    const c = r.critical; if (!c || !c.finish) return '';
    const dur = r.durations || {}, order = (r.levels || []).flat(), end = c.minutes || 1;
    const rows = order.map(t => { const f = c.finish[t], d = dur[t] || 0, s0 = f - d; return `<div class="${c.path.includes(t) ? 'hot' : ''}"><span title="${esc(t)}">${esc(t)}</span><i><b style="left:${(s0 / end * 100).toFixed(2)}%;width:${Math.max(0.4, d / end * 100).toFixed(2)}%"></b></i><em>${d ? esc(MIN(d)) : '—'}${c.slack && c.slack[t] > 0.01 ? ` · ${esc(MIN(c.slack[t]))} spare` : ''}</em></div>`; }).join('');
    return `<div class="dek-gantt" role="img" aria-label="When each task runs">${rows}</div><p class="cs-note">Each task drawn from the earliest it can start; the critical path is dark. 'Spare' is how late a task can finish without delaying the run.</p>`;
  }
  function pPl(d) {
    const r = d.result || {}, c = r.critical;
    return `${head(d, 'pipelines')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Tasks', esc(num(r.tasks)), `${pl((r.edges || []).length, 'link')}`)}${tile('Levels', r.cycle ? '—' : esc(num(r.depth)), r.cycle ? 'a loop' : `up to ${r.widest} side by side`)}${tile('Critical path', c ? esc(MIN(c.minutes)) : '—', c ? `${pl(c.path.length, 'task')}; ${MIN(c.serial)} if run one by one` : 'add durations: task = 12m', c && st_().window_min && c.minutes > st_().window_min)}${tile('Lone tasks', esc(num((r.lone || []).length)), 'linked to nothing', (r.lone || []).length > 0)}</div></section>
      ${r.cycle ? `<section class="card"><h2 class="md-h2">The loop</h2><p class="dek-chain">${r.cycle.map(esc).join(' <span>→</span> ')}</p></section>` : `<section class="card"><h2 class="md-h2">The graph</h2>${graph(r)}</section>`}
      ${c ? `<section class="card"><h2 class="md-h2">Critical path</h2><p class="dek-chain">${c.path.map(t => `<b>${esc(t)}</b>`).join(' <span>→</span> ')}</p>${gantt(r)}</section>` : ''}
      ${!r.cycle && (r.levels || []).length ? `<section class="card"><h2 class="md-h2">What runs side by side</h2><div class="dek-levels">${r.levels.map((l, i) => `<div><span>Level ${i + 1}</span><p>${l.map(esc).join(', ')}</p></div>`).join('')}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <section class="card"><h2 class="md-h2">Mermaid drawing</h2><p class="mut" style="margin:0 0 8px">Paste into a README or any Mermaid viewer.</p>${pre(r.mermaid || '', 'code')}<div class="md-acts"><span></span>${copyBtn(r.mermaid || '')}</div></section>
      <details class="card dek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- contracts */
  const SAMPLE_OLD = "CREATE TABLE orders (\n  order_id BIGINT NOT NULL,\n  amount DECIMAL(12,2),\n  status VARCHAR(20),\n  PRIMARY KEY (order_id)\n);";
  function pContracts() {
    if (ST.arg) return one(ST.arg, 'contracts', pCt);
    return `<div><h1 class="sd-h">Contracts</h1><p class="lead">A table's new schema against its contract - the shape its readers rely on. Every change is sorted into breaking (a column gone, a type changed or narrowed, made required) and safe (a nullable column added, a type widened).</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a schema</h2><form data-form="schema" class="dek-grid">
        ${area('text', 'The contract (today\'s schema): CREATE TABLE, JSON Schema, Avro, dbt YAML columns or lines "name type not null"', SAMPLE_OLD, 9)}
        ${area('new', 'The new schema, the same way (leave empty to check the contract on its own)', SAMPLE_OLD.replace('amount DECIMAL(12,2)', 'amount DECIMAL(10,2) NOT NULL'), 9)}
        ${subRow('Check it', '.sql,.json,.avsc,.yml,.yaml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('schema'))}</section>`;
  }
  function pCt(d) {
    const r = d.result || {}, ch = r.changes || [];
    const cols = `<div class="iv-tw"><table class="tb in-cards dek-t"><thead><tr><th>Column</th><th>Type</th><th>Family</th><th>Empty allowed</th></tr></thead><tbody>${(r.columns || []).map(c => `<tr><td><b>${esc(c.name)}</b>${(r.pk || []).includes(c.name) ? ' <span class="cs-tag">key</span>' : ''}</td><td><code>${esc(c.type)}</code></td><td class="mut">${esc(c.family)}</td><td>${c.nullable ? 'yes' : 'no'}</td></tr>`).join('')}</tbody></table></div>`;
    return `${head(d, 'contracts')}${verdict(r, isOk(r))}
      ${r.mode === 'two' ? `<section class="cs-hero"><div class="top">${tile('Breaking', esc(num(r.breaking)), 'readers or writers fail', r.breaking > 0)}${tile('Safe', esc(num(r.safe)), 'nothing downstream breaks')}${tile('Columns', esc(num(r.old_cols)) + ' <small>→ ' + esc(num(r.new_cols)) + '</small>', r.format === r.format_new ? r.format : r.format + ' → ' + r.format_new)}${tile('Renames?', esc(num((r.renames || []).length)), (r.renames || []).map(x => x[0] + ' → ' + x[1]).join(', ').slice(0, 60) || 'none guessed')}</div></section>
      <section class="card"><h2 class="md-h2">Every change</h2>${ch.length ? `<div class="iv-tw"><table class="tb in-cards dek-t"><thead><tr><th>Column</th><th>Change</th><th>Before</th><th>After</th><th></th></tr></thead><tbody>${ch.map(x => `<tr class="${x.sev === 'breaking' ? 'bad' : x.sev === 'warn' ? 'warn' : ''}"><td><b>${esc(x.column)}</b></td><td>${esc(cap(x.kind))}</td><td><code>${esc(x.old)}</code></td><td><code>${esc(x.new)}</code></td><td>${tag(cap(x.say), SEVC[x.sev] || '')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">The two schemas are the same.</p>'}</section>
      <section class="card"><h2 class="md-h2">The new schema</h2>${cols}</section>` : `<section class="card">${stats([['Columns', (r.columns || []).length], ['Format', r.format], ['Key', (r.pk || []).join(', ') || 'none']])}</section><section class="card"><h2 class="md-h2">Columns</h2>${cols}</section>`}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card dek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 50000), 'code')}${(d.inputs || {}).new ? pre(S(d.inputs.new).slice(0, 50000), 'code') : ''}</details>`;
  }

  /* ---------------------------------------------------------------- reconcile */
  const SAMPLE_SRC = "order_id,amount,status\n1001,250.00,paid\n1002,99.50,paid\n1003,12.00,refunded";
  function pReconcile() {
    if (ST.arg) return one(ST.arg, 'reconcile', pRc);
    const s = st_();
    return `<div><h1 class="sd-h">Reconcile</h1><p class="lead">The source and what landed in the target, matched row by row on the key: rows missing or extra, keys that appear twice, values that changed, and the totals on each side.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Reconcile two tables</h2><form data-form="recon" class="dek-grid">
        ${area('text', 'The source: a CSV with a header row', SAMPLE_SRC, 8)}
        ${area('target', 'The target: the same columns, what landed', SAMPLE_SRC, 8)}
        ${fld('key', 'Key column(s), comma separated', s.key_cols, '', 'order_id')}${fld('tolerance', 'Numbers may differ by', s.tolerance || '', 'type="number" min="0" step="any"', '0.01')}${fld('ignore', 'Columns to leave out', '', '', 'loaded_at')}
        ${subRow('Reconcile', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Reconciled</h2>${itemRows(items('recon'))}</section>`;
  }
  function pRc(d) {
    const r = d.result || {}, dc = Object.entries(r.diff_cols || {});
    const share = (v, of) => of ? (v / of * 100).toFixed(1) + '%' : '';
    return `${head(d, 'reconcile')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Matched', esc(num(r.matched)), `of ${num(r.source_rows)} source rows`)}${tile('Missing', esc(num(r.missing)), share(r.missing, r.source_rows) + ' not in the target', r.missing > 0)}${tile('Extra', esc(num(r.extra)), 'only in the target', r.extra > 0)}${tile('Changed', esc(num(r.changed)), share(r.changed, r.matched) + ' of matched rows', r.changed > 0)}</div></section>
      <section class="card">${stats([['Source rows', num(r.source_rows)], ['Target rows', num(r.target_rows)], ['Key', (r.key || []).join(' + ')], ['Duplicate keys in the source', num(r.dup_source), r.dup_source ? 'warn' : ''], ['Duplicate keys in the target', num(r.dup_target), r.dup_target ? 'bad' : ''], ['Columns compared', (r.compared || []).length]])}</section>
      ${dc.length ? `<section class="card"><h2 class="md-h2">Where values differ</h2>${bars(dc.slice(0, 15).map(([c, n]) => [c, n, 'dek-b warn', share(n, r.matched) + ' of matched']), v => num(v), 'Differences by column')}</section>` : ''}
      ${(r.samples || []).length ? `<section class="card"><h2 class="md-h2">Rows that differ</h2><div class="iv-tw"><table class="tb in-cards dek-t"><thead><tr><th>Key</th><th>Column</th><th>Source</th><th>Target</th></tr></thead><tbody>${r.samples.slice(0, 25).map(x => `<tr><td><b>${esc(x.key)}</b></td><td>${esc(x.column)}</td><td><code>${esc(x.source)}</code></td><td><code>${esc(x.target)}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${r.missing || r.extra ? `<section class="card dek-two"><div><h2 class="md-h2">Missing from the target</h2>${(r.missing_keys || []).length ? `<p class="dek-keys">${r.missing_keys.slice(0, 50).map(esc).join(', ')}${r.missing > 50 ? ' …' : ''}</p>` : '<p class="mut">None.</p>'}</div><div><h2 class="md-h2">Only in the target</h2>${(r.extra_keys || []).length ? `<p class="dek-keys">${r.extra_keys.slice(0, 50).map(esc).join(', ')}${r.extra > 50 ? ' …' : ''}</p>` : '<p class="mut">None.</p>'}</div></section>` : ''}
      ${(r.totals || []).length ? `<section class="card"><h2 class="md-h2">Totals</h2><div class="iv-tw"><table class="tb in-cards dek-t"><thead><tr><th>Column</th><th class="r">Source</th><th class="r">Target</th><th class="r">Difference</th></tr></thead><tbody>${r.totals.map(t => `<tr class="${Math.abs(t.diff) > 1e-9 ? 'warn' : ''}"><td><b>${esc(t.column)}</b></td><td class="r">${esc(N2(t.source))}</td><td class="r">${esc(N2(t.target))}</td><td class="r">${esc((t.diff > 0 ? '+' : '') + N2(t.diff))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card dek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 50000), 'code')}${pre(S((d.inputs || {}).target).slice(0, 50000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- runs */
  const SAMPLE_RUNS = "job,start,end,status,rows\nload_orders,2026-11-20T02:00:00,2026-11-20T02:21:10,success,10432\nbuild_marts,2026-11-20T02:25:00,2026-11-20T03:10:42,success,8810";
  function pRuns() {
    if (ST.arg) return one(ST.arg, 'runs', pRu);
    const s = st_();
    return `<div><h1 class="sd-h">Runs</h1><p class="lead">A run history read job by job: what is failing now and what fails now and then, typical and slow durations, jobs getting slower, loads that succeeded with no rows, and data that has gone stale.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a run history</h2><form data-form="runs" class="dek-grid">
        ${area('text', 'A CSV of runs: job, start, end (or duration), status, rows - from Airflow, dbt, Dagster or your scheduler', SAMPLE_RUNS, 10)}
        ${fld('sla', 'Time limit a run (minutes)', s.sla_min || '', 'type="number" min="0" step="any"', '60')}${fld('freshness', 'Data must be newer than (hours)', s.freshness_h || '', 'type="number" min="0" step="any"', '24')}${fld('as_of', 'As of (default: the latest time in the history)', '', '', '2026-11-27T09:00')}
        ${subRow('Read it', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('runs'))}</section>`;
  }
  function spark(j) {
    const pts = (j.series || []).filter(x => x[1] !== null && x[1] !== undefined);
    if (pts.length < 2) return '';
    const W = 220, H = 36, mx = Math.max(...pts.map(x => x[1])) || 1;
    const X = i => 2 + i * (W - 4) / ((j.series || []).length - 1 || 1), Y = v => H - 3 - v / mx * (H - 6);
    const all = j.series || [];
    const line = all.map((x, i) => x[1] === null || x[1] === undefined ? '' : `${X(i).toFixed(1)},${Y(x[1]).toFixed(1)}`).filter(Boolean).join(' ');
    return `<svg class="dek-spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Durations"><polyline points="${line}"/>${all.map((x, i) => x[2] ? '' : `<circle cx="${X(i).toFixed(1)}" cy="${(x[1] === null || x[1] === undefined ? H - 4 : Y(x[1])).toFixed(1)}" r="3"/>`).join('')}</svg>`;
  }
  function pRu(d) {
    const r = d.result || {}, jobs = r.jobs || [];
    const now = jobs.filter(j => j.failing_now).length, slow = jobs.filter(j => j.last && j.median && j.last > 2 * j.median).length;
    return `${head(d, 'runs')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Jobs', esc(num(jobs.length)), `${num(r.runs)} runs`)}${tile('Failing now', esc(num(now)), 'their last run failed', now > 0)}${tile('Failed', esc(num(r.failed)), r.runs ? (r.failed / r.runs * 100).toFixed(1) + '% of runs' : '')}${tile('Slow last run', esc(num(slow)), 'over twice the usual time', slow > 0)}</div></section>
      <section class="card"><h2 class="md-h2">Each job</h2><div class="iv-tw"><table class="tb in-cards dek-t"><thead><tr><th>Job</th><th class="r">Runs</th><th class="r">Failed</th><th class="r">Usual</th><th class="r">Slow (p95)</th><th class="r">Last</th><th class="r">Data age</th><th>Durations (failed runs as dots)</th></tr></thead><tbody>${jobs.map(j => `<tr class="${j.failing_now ? 'bad' : j.fail_rate >= 0.1 ? 'warn' : ''}"><td><b>${esc(j.job)}</b>${j.failing_now ? ` <span class="cs-tag">failing ${esc(j.failing_now)}x</span>` : ''}</td><td class="r">${esc(num(j.runs))}</td><td class="r">${esc(num(j.failed))}</td><td class="r">${esc(MIN(j.median))}</td><td class="r">${esc(MIN(j.p95))}</td><td class="r">${esc(MIN(j.last))}</td><td class="r">${j.age_h !== undefined ? esc(P4(j.age_h)) + ' h' : '—'}</td><td>${spark(j)}</td></tr>`).join('')}</tbody></table></div><p class="cs-note">As of ${esc(r.as_of ? dmy(r.as_of) + ' ' + r.as_of.slice(11, 16) : '—')}.</p></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card dek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- storage */
  const SAMPLE_LS = "2026-11-20 02:10:44    2104331 warehouse/orders/dt=2026-11-20/part-00000.snappy.parquet\n2026-11-20 02:10:45    1988201 warehouse/orders/dt=2026-11-20/part-00001.snappy.parquet";
  function pStorage() {
    if (ST.arg) return one(ST.arg, 'storage', pSg);
    const s = st_();
    return `<div><h1 class="sd-h">Storage</h1><p class="lead">A table's files read from a listing: how many and how big, the small-file problem and how many files compaction would leave, partitions and how lopsided they are, formats, and what a full scan costs.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a listing</h2><form data-form="storage" class="dek-grid">
        ${area('text', 'aws s3 ls --recursive, gsutil ls -l, hdfs dfs -ls -R or az storage blob list output - or lines "path,size"', SAMPLE_LS, 10)}
        ${fld('small_mb', 'Small file under (MB)', s.small_mb, 'type="number" min="0.01" step="any"')}${fld('target_mb', 'Target file size (MB)', s.target_mb, 'type="number" min="1" step="any"')}${fld('price_tb', 'Price per TB scanned', s.price_tb || '', 'type="number" min="0" step="any"', '6.25')}
        ${subRow('Read it', '.txt,.csv,.log,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('storage'))}</section>`;
  }
  function pSg(d) {
    const r = d.result || {}, p = r.partitions;
    const fm = Object.entries(r.formats || {});
    return `${head(d, 'storage')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Size', esc(r.total_h || HB(r.total)), `${num(r.files)} files`)}${tile('Median file', esc(HB(r.median)), `largest ${HB(r.max)}`, r.median < (r.small_mb || 32) * 1048576)}${tile('Small files', esc(num(r.small)), `under ${P4(r.small_mb)} MB · ${r.files ? (r.small / r.files * 100).toFixed(0) : 0}%`, r.small > 0.5 * r.files && r.files >= 20)}${tile('After compaction', esc(num(r.after)), `files of ~${P4(r.target_mb)} MB`)}</div></section>
      <section class="card"><h2 class="md-h2">File sizes</h2>${bars((r.hist || []).map(([l, n]) => [l, n, 'dek-b', '']), v => num(v), 'Files by size')}</section>
      ${p ? `<section class="card"><h2 class="md-h2">Partitions${p.keys && p.keys.length ? ' by ' + esc(p.keys.join(', ')) : ''}</h2>${stats([['Partitions', num(p.count)], ['Median size', HB(p.median)], ['Largest', HB(p.max)], ['Files in each (median)', num(p.files_median)], ['Under ' + P4(r.small_mb) + ' MB', num(p.small)]])}${bars((p.top || []).map(x => [x.partition, x.bytes, x.bytes > 10 * p.median ? 'dek-b warn' : 'dek-b', pl(x.files, 'file')]), v => HB(v), 'Largest partitions')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Formats</h2>${bars(fm.map(([k2, v]) => [k2, v.bytes, ['csv', 'json', 'text'].includes(k2) ? 'dek-b warn' : 'dek-b', pl(v.files, 'file')]), v => HB(v), 'Bytes by format')}${r.scan_cost !== undefined ? stats([['A full scan costs', P4(r.scan_cost)], ['At, per TB', P4(r.price_tb)]]) : ''}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}${r.skipped ? ` ${pl(r.skipped, 'line')} could not be read and were left out.` : ''}</p></section>
      <details class="card dek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs your data tests on every pull request and fails it when a column is removed or its type changes against the contract in your repository.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Data tests', s.test_cmd || 'not set'], ['Schema your tests write', s.schema_path || 'not set'], ['Contract', s.contract_path || 'not set'], ['Setup', s.setup_cmd || 'none'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="data-checks.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your key columns, time limits, file sizes and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="dek-grid">
        <h2 class="md-h2 wide" style="margin:0">Checks</h2>
        ${fld('key_cols', 'Key column(s) for reconciling', s.key_cols, '', 'order_id')}${fld('tolerance', 'Numbers may differ by', s.tolerance, 'type="number" min="0" step="any"')}
        ${fld('window_min', 'Run window (minutes, 0 = none)', s.window_min, 'type="number" min="0" step="any"')}${fld('sla_min', 'Time limit a run (minutes, 0 = none)', s.sla_min, 'type="number" min="0" step="any"')}${fld('freshness_h', 'Freshness limit (hours, 0 = none)', s.freshness_h, 'type="number" min="0" step="any"')}
        ${fld('small_mb', 'Small file under (MB)', s.small_mb, 'type="number" min="0.01" step="any"')}${fld('target_mb', 'Target file size (MB)', s.target_mb, 'type="number" min="1" step="any"')}${fld('price_tb', 'Price per TB scanned (0 = none)', s.price_tb, 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${fld('test_cmd', 'Data test command', s.test_cmd, 'maxlength="400"', 'dbt build --select state:modified+')}${fld('setup_cmd', 'Setup command (optional)', s.setup_cmd, 'maxlength="400"', 'pip install dbt-duckdb')}
        ${fld('schema_path', 'Schema file your tests write (optional)', s.schema_path, '', 'target/schema.json')}${fld('contract_path', 'Contract file in the repository (optional)', s.contract_path, '', 'contracts/orders.json')}
        ${fld('python', 'Python', s.python)}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk. Warehouse passwords never go here - keep them in GitHub secrets.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Pipelines are read from the links and durations you give; real runs add queueing, retries and pool limits.</li><li>A reconciliation covers the rows you paste - reconcile the whole table before you trust a load.</li><li>Schema types are compared by family and size as written; check how your warehouse names them.</li><li>Storage is read from the listing; the warehouse may bill a different number of bytes.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your machines or your warehouse.</li><li>Asks for a warehouse password, key or connection string.</li><li>Calls a load good from a sample.</li><li>Follows anything written inside your pipelines, logs or data: they are data.</li></ul></section>`;
  }
  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  function saveBlob(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
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
    const cw = t.closest('[data-sub]'); if (cw) { ST.sub = cw.dataset.sub; showPage(true); return; }
    const dlx = t.closest('[data-dl]'); if (dlx) { saveBlob(dlx.dataset.dl, new Blob([dlx.dataset.dltext || ''], {type: 'text/plain'})); return; }
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
    if (el.dataset.filesto && el.files && el.files.length) {
      const fs = [...el.files].filter(f => /\.(txt|json|names)$/i.test(f.name));
      if (!fs.length) { toast('No text files there.', true); el.value = ''; return; }
      if (fs.reduce((n, f) => n + f.size, 0) > 30000000) { toast('Those files are larger than 30 MB together.', true); el.value = ''; return; }
      const parts = await Promise.all(fs.map(async f => `## ${f.webkitRelativePath || f.name}\n${(await f.text()).replace(/\s+$/, '')}\n`));
      const form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.filesto}]`);
      if (ta) ta.value = (ta.value.trim() ? ta.value.replace(/\s+$/, '') + '\n' : '') + parts.join('');
      el.value = '';
      return;
    }
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 30000000) { toast('That file is larger than 30 MB.', true); el.value = ''; return; }
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
    const pick = names => { const o = {}; names.forEach(n => { if (g(n) !== '') o[n] = g(n); }); return o; };
    const go = async (k, a) => { if (btn) btn.textContent = 'Working…'; const d = await run('add', {kind: k, title: g('title'), ...a}); ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} ready.`); };
    try {
      if (kind === 'dag') await go('dag', {text: S(fd.get('text')), inputs: pick(['window'])});
      else if (kind === 'schema') await go('schema', {text: S(fd.get('text')), inputs: pick(['new'])});
      else if (kind === 'recon') await go('recon', {text: S(fd.get('text')), inputs: pick(['target', 'key', 'tolerance', 'ignore'])});
      else if (kind === 'runs') await go('runs', {text: S(fd.get('text')), inputs: pick(['sla', 'freshness', 'as_of'])});
      else if (kind === 'storage') await go('storage', {text: S(fd.get('text')), inputs: pick(['small_mb', 'target_mb', 'price_tb'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['key_cols', 'tolerance', 'window_min', 'sla_min', 'freshness_h', 'small_mb', 'target_mb', 'price_tb', 'test_cmd', 'setup_cmd', 'schema_path', 'contract_path', 'python', 'runner'];


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
    const box = $('#deFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dedesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'ds' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


