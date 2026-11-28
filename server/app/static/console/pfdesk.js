/* PLATFORM ENGINEER DESK - the Platform Engineer's own section, like the finance desks (owner: "Platform Engineer same as finance
   desks"). A thin top bar, then the Platform chat (its own conversation, kind 'platform') beside the desk's pages: Today, Terraform,
   Rightsizing, Capacity, Catalog, Upgrades, CI check, Settings. The pages call /api/pfdesk/do/<part>; nothing runs on her clusters or cloud. */
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

  const TABS = [['today', 'Today'], ['terraform', 'Terraform'], ['rightsizing', 'Rightsizing'], ['capacity', 'Capacity'], ['catalog', 'Catalog'], ['upgrades', 'Upgrades'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where should a platform team start?', 'How do I stop a plan from deleting a database?', 'How much headroom should a cluster keep?'],
    terraform: ['Why does this resource need replacing?', 'How do I rename a resource without destroying it?', 'How should I split state?'],
    rightsizing: ['Should I set CPU limits at all?', 'How much memory headroom do I need?', 'VPA or setting requests by hand?'],
    capacity: ['Few big nodes or many small ones?', 'How do I survive losing a zone?', 'How does the cluster autoscaler decide?'],
    catalog: ['What should every service in the catalog have?', 'How do I get teams to fill the catalog in?', 'What is a golden path?'],
    upgrades: ['How do I upgrade a cluster safely?', 'How do I find removed APIs in the live cluster?', 'How far behind can nodes be?'],
    ci: ['How do I give CI read-only cloud access?', 'Should the plan run on every pull request?', 'Where should state live?'],
    settings: ['What destroy limit is sensible?', 'Which tags should be required?', 'What does the system reserve on a node?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'terraform', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.pfdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.pfdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'platform', name: 'Platform'} : null;
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
  const run = (part, a) => api('POST', '/api/pfdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/pfdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Platform Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="pfHire">Hire the Platform Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#pfHire').onclick = async () => { try { await api('POST', '/api/employees/platform_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Platform</div><div class="sd-site" id="pfSite"></div></div>
          <span id="pfState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Platform chat">
          <div class="sd-chathead"><div class="t"><b>Platform chat</b><span>Paste a Terraform plan, usage, a cluster, a catalog or manifests - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="pfFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="pfPick" multiple hidden accept=".txt,.json,.csv,.tsv,.tf,.hcl,.yaml,.yml,.log,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Platform desk" id="sdTabs"></nav>
          <div id="pfPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a plan or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#pfPick').click()});
    $('#pfPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.pfdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.pfdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/pfdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#pfPage').addEventListener('click', onPageClick);
    $('#pfPage').addEventListener('submit', onSubmit);
    $('#pfPage').addEventListener('change', onChange);
    $('#pfPage').addEventListener('input', onInput);
    $('#pfPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#pfState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#pfSite').textContent = [s.k8s_current && 'Kubernetes ' + s.k8s_current, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/pfdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#pfPage'); if (!box) return;
    const fn = {today: pToday, terraform: pTerraform, rightsizing: pRightsizing, capacity: pCapacity, catalog: pCatalog, upgrades: pUpgrades, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="pfk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {tfplan: 'Terraform', rightsize: 'Rightsizing', capacity: 'Capacity', catalog: 'Catalog', upgrade: 'Upgrade'};
  const ROUTE = {tfplan: 'terraform', rightsize: 'rightsizing', capacity: 'capacity', catalog: 'catalog', upgrade: 'upgrades'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(0);
  const CO = v => (v === null || v === undefined) ? '—' : Number(v) < 1 ? Math.round(Number(v) * 1000) + 'm' : P4(v);
  const GI = v => (v === null || v === undefined) ? '—' : Number(v) < 1 ? Math.round(Number(v) * 1024) + 'Mi' : P4(v) + 'Gi';
  const MONEY = v => Number(v).toLocaleString('en', {maximumFractionDigits: 2});
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'tfplan': return `${num(b.create || 0)} create · ${num(b.update || 0)} change · ${num(b.replace || 0)} replace · ${num(b.delete || 0)} destroy${b.lost ? ` · ${pl(b.lost, 'data store')} at risk` : ''}`;
      case 'rightsize': return `${pl(b.containers || 0, 'container')}${b.eff_cpu !== null && b.eff_cpu !== undefined ? ` · ${pc(b.eff_cpu)}% of CPU used` : ''}${b.save_cpu ? ` · ${CO(b.save_cpu)} cores to give back` : ''}`;
      case 'capacity': return b.unplaced ? `${num(b.unplaced)} of ${pl(b.pods || 0, 'pod')} do not fit` : `${pl(b.pods || 0, 'pod')} on ${pl(b.nodes || 0, 'node')} · ${pc(b.util_cpu)}% CPU, ${pc(b.util_mem)}% memory`;
      case 'catalog': return `${pl(b.scored || 0, 'entity', 'entities')} · average ${pc(b.avg)}%`;
      case 'upgrade': return `${pl(b.objects || 0, 'object')} · ${num(b.breaks || 0)} break${b.target ? ' at ' + b.target : ''}${b.later ? ` · ${num(b.later)} later` : ''}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="pfk-list">${list.map(x => `<button type="button" class="pfk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="pfk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="pfk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="pfk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="pfk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono pfk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft pfk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="pfk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card pfk-sum ${ok ? 'okv' : 'badv'}"><p class="pfk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="pfk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="pfk-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="pfk-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="pfk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  const ACT = {create: ['Create', 'ok'], update: ['Change', ''], replace: ['Replace', 'warn'], delete: ['Destroy', 'bad']};
  const meter = (v, warnAt, badAt) => `<span class="pfk-meter"><i class="${v >= badAt ? 'bad' : v >= warnAt ? 'warn' : ''}" style="width:${Math.min(100, v * 100).toFixed(1)}%"></i></span>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), t = k.tfplan, r = k.rightsize, c = k.capacity, u = k.upgrade, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Terraform', t ? (t.lost ? esc(num(t.lost)) + ' <small>at risk</small>' : esc(num((t.delete || 0) + (t.replace || 0))) + ' <small>destroyed</small>') : '—', t ? `${num(t.create || 0)} create, ${num(t.update || 0)} change · ${t.number}` : 'paste a plan', t && t.bad),
      tile('Rightsizing', r && r.eff_cpu !== null && r.eff_cpu !== undefined ? esc(pc(r.eff_cpu)) + '<small>% CPU used</small>' : '—', r ? `${r.save_cpu ? CO(r.save_cpu) + ' cores to give back' : pl(r.containers, 'container')} · ${r.number}` : 'paste requests and use', r && r.bad),
      tile('Capacity', c ? (c.unplaced ? esc(num(c.unplaced)) + ' <small>do not fit</small>' : esc(pc(Math.max(c.util_cpu || 0, c.util_mem || 0))) + '<small>% full</small>') : '—', c ? `${pl(c.pods, 'pod')} on ${pl(c.nodes, 'node')} · ${c.number}` : 'describe the cluster', c && c.bad),
      tile('Upgrade', u ? esc(num(u.breaks || 0)) + ' <small>break</small>' : '—', u ? `${u.target ? 'at ' + u.target : 'no target set'} · ${u.number}` : 'paste manifests', u && u.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.k8s_target ? 'Next Kubernetes: ' + s.k8s_target + '.' : 'Set your Kubernetes versions and destroy limit in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="pfk-path">
        <li><button type="button" data-go="terraform"><b>Change safely</b><span>Read a plan before apply: data lost, the internet let in, permissions wide open</span></button></li>
        <li><button type="button" data-go="rightsizing"><b>Pay for what runs</b><span>Requests against real use: waste given back, tight ones raised before they crash</span></button></li>
        <li><button type="button" data-go="capacity"><b>Keep room</b><span>Does it fit - and does it still fit after losing a node or a zone</span></button></li>
        <li><button type="button" data-go="upgrades"><b>Upgrade without surprises</b><span>The APIs the next Kubernetes version removes, and what to move to</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- terraform */
  const SAMPLE_TF = '# aws_db_instance.main must be replaced\n-/+ resource "aws_db_instance" "main" {\n      ~ engine_version = "14.7" -> "15.4" # forces replacement\n    }\n\nPlan: 1 to add, 0 to change, 1 to destroy.';
  function pTerraform() {
    if (ST.arg) return one(ST.arg, 'terraform', pTf);
    const s = st_();
    return `<div><h1 class="sd-h">Terraform</h1><p class="lead">A plan read before anyone applies it: data stores that would be destroyed or replaced and why, network rules opened to the internet, permissions that allow everything, encryption or protection switched off, missing tags.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a plan</h2><form data-form="tfplan" class="pfk-grid">
        ${area('text', '`terraform show -json plan.out` (full detail) or the text `terraform plan` prints - OpenTofu too', SAMPLE_TF, 12)}
        ${fld('max_destroy', 'Destroy limit', s.set ? s.max_destroy : '', 'type="number" min="0" step="1"', '0')}${fld('required_tags', 'Required tags', s.required_tags, '', 'env, team, cost-center')}${fld('protected', 'Also treat as data stores', s.protected, '', 'aws_route53_zone')}
        ${subRow('Read it', '.json,.txt,.plan,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('tfplan'))}</section>`;
  }
  function pTf(d) {
    const r = d.result || {}, a = r.actions || {}, ch = r.changes || [];
    const order = {delete: 0, replace: 1, update: 2, create: 3};
    const rows = ch.slice().sort((x, y) => (order[x.kind] - order[y.kind]) || (y.stateful - x.stateful));
    const types = Object.entries(r.types || {}).map(([t, v]) => [t, v.create + v.update + v.replace + v.delete, v]).sort((x, y) => y[1] - x[1]).slice(0, 12);
    return `${head(d, 'terraform')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Create', esc(num(a.create || 0)), 'new resources')}${tile('Change', esc(num(a.update || 0)), 'in place')}${tile('Replace', esc(num(a.replace || 0)), 'destroyed, then created', (a.replace || 0) > 0)}${tile('Destroy', esc(num(a.delete || 0)), (r.lost || []).length ? pl(r.lost.length, 'data store') + ' at risk' : 'removed', (r.lost || []).length > 0)}</div></section>
      ${rows.length ? `<section class="card"><h2 class="md-h2">Every change</h2><div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>Resource</th><th>Action</th><th>Why replaced</th></tr></thead><tbody>${rows.slice(0, 200).map(c => `<tr class="${c.stateful && (c.kind === 'delete' || c.kind === 'replace') ? 'bad' : c.kind === 'replace' ? 'warn' : ''}"><td><code>${esc(c.address)}</code>${c.stateful ? ' <span class="cs-tag">data</span>' : ''}</td><td>${tag(ACT[c.kind][0], ACT[c.kind][1])}</td><td class="mut">${esc((c.why || []).join(', ') || (c.reason || ''))}</td></tr>`).join('')}</tbody></table></div>${rows.length > 200 ? `<p class="cs-note">${num(rows.length - 200)} more not shown.</p>` : ''}</section>` : ''}
      ${types.length ? `<section class="card"><h2 class="md-h2">By resource type</h2>${bars(types.map(([t, n, v]) => [t, n, (v.delete || v.replace) ? 'pfk-b warn' : 'pfk-b', [v.create && v.create + ' create', v.update && v.update + ' change', v.replace && v.replace + ' replace', v.delete && v.delete + ' destroy'].filter(Boolean).join(', ')]), v => num(v), 'Changes by type')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}${r.terraform ? ' Terraform ' + esc(r.terraform) + '.' : ''}</p></section>
      <details class="card pfk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- rightsizing */
  const SAMPLE_RS = 'namespace,workload,container,cpu_request,cpu_limit,mem_request,mem_limit,cpu_p95,mem_p95,replicas\nshop,api,app,1,2,2Gi,2Gi,150m,1.9Gi,6\nshop,worker,app,500m,500m,512Mi,1Gi,480m,800Mi,3';
  function pRightsizing() {
    if (ST.arg) return one(ST.arg, 'rightsizing', pRs);
    const s = st_();
    return `<div><h1 class="sd-h">Rightsizing</h1><p class="lead">Each container's requests and limits against what it really uses: cores and memory paid for and never used, containers placed too tight, memory close to its limit, CPU slowed by its limit - with the request to set and what it saves.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Size containers</h2><form data-form="rightsize" class="pfk-grid">
        ${area('text', 'A CSV per container: namespace, workload, container, cpu_request, cpu_limit, mem_request, mem_limit, cpu_p95, mem_p95, replicas (use = p95 over a busy week from your monitoring)', SAMPLE_RS, 10)}
        ${fld('headroom', 'Headroom above use (0.2 = 20%)', s.headroom, 'type="number" min="0" max="5" step="any"')}${fld('cpu_price', 'Price per core a month', s.cpu_price || '', 'type="number" min="0" step="any"', '25')}${fld('mem_price', 'Price per GiB a month', s.mem_price || '', 'type="number" min="0" step="any"', '3.5')}
        ${subRow('Size them', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Sized</h2>${itemRows(items('rightsize'))}</section>`;
  }
  function pRs(d) {
    const r = d.result || {}, t = r.totals || {}, rows = r.rows || [];
    const cell = (req, use, lim) => `<td class="r">${esc(req)}</td><td class="r">${esc(use)}</td><td class="r mut">${esc(lim)}</td>`;
    return `${head(d, 'rightsizing')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('CPU used', r.eff_cpu !== null && r.eff_cpu !== undefined ? esc(pc(r.eff_cpu)) + '<small>%</small>' : '—', `${CO(t.cpu_use)} of ${CO(t.cpu_req)} cores requested`, r.eff_cpu !== null && r.eff_cpu < 0.3)}${tile('Memory used', r.eff_mem !== null && r.eff_mem !== undefined ? esc(pc(r.eff_mem)) + '<small>%</small>' : '—', `${GI(t.mem_use)} of ${GI(t.mem_req)} requested`, r.eff_mem !== null && r.eff_mem < 0.3)}${tile('To give back', esc(CO(r.save_cpu)) + ' <small>cores</small>', `and ${GI(r.save_mem)} of memory`)}${tile('A month', r.save_money !== null && r.save_money !== undefined ? esc(MONEY(r.save_money)) : '—', r.save_money !== null && r.save_money !== undefined ? 'saved at your prices' : 'set prices in Settings')}</div></section>
      <section class="card"><h2 class="md-h2">Each container</h2><div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>Container</th><th class="r">x</th><th class="r">CPU request</th><th class="r">use</th><th class="r">limit</th><th class="r">Memory request</th><th class="r">use</th><th class="r">limit</th><th class="r">Set request to</th><th></th></tr></thead><tbody>${rows.map(c => `<tr class="${c.flags.includes('near memory limit') ? 'bad' : c.flags.length ? 'warn' : ''}"><td><b>${esc(c.name)}</b></td><td class="r">${esc(num(c.replicas))}</td>${cell(CO(c.cpu_req), CO(c.cpu_use), CO(c.cpu_lim))}${cell(GI(c.mem_req), GI(c.mem_use), GI(c.mem_lim))}<td class="r"><b>${esc(CO(c.cpu_rec))}</b> / <b>${esc(GI(c.mem_rec))}</b></td><td>${c.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Where the waste is</h2>${bars(rows.filter(c => c.save_cpu > 0).slice(0, 12).map(c => [c.name, c.save_cpu, 'pfk-b', GI(c.save_mem) + ' memory too']), v => CO(v) + ' cores', 'Cores to give back') || '<p class="mut">Nothing requests much more than it uses.</p>'}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card pfk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- capacity */
  const SAMPLE_CP = 'node m5.xlarge cpu=4 mem=16Gi pods=58 x3 zone=a\nnode m5.xlarge cpu=4 mem=16Gi pods=58 x3 zone=b\ndaemonset cpu=100m mem=200Mi\npod api cpu=500m mem=1Gi x20\npod worker cpu=1 mem=3Gi x6';
  function pCapacity() {
    if (ST.arg) return one(ST.arg, 'capacity', pCp);
    const s = st_();
    return `<div><h1 class="sd-h">Capacity</h1><p class="lead">Do the pods fit the cluster: node pools less what the system and the DaemonSets take, every pod placed by its requests, what fits nowhere, how full each pool is - and whether everything still fits after losing a node or a zone.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a cluster</h2><form data-form="capacity" class="pfk-grid">
        ${area('text', "Lines: 'node m5.xlarge cpu=4 mem=16Gi pods=58 x6 zone=a', 'daemonset cpu=100m mem=200Mi', 'pod api cpu=500m mem=1Gi x20'", SAMPLE_CP, 10)}
        ${fld('reserve_cpu', 'System reserve per node, cores (empty = the GKE rule)', s.reserve_cpu || '', 'type="number" min="0" step="any"', '0.1')}${fld('reserve_mem', 'System reserve per node, GiB', s.reserve_mem || '', 'type="number" min="0" step="any"', '1.5')}
        ${subRow('Check it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('capacity'))}</section>`;
  }
  function pCp(d) {
    const r = d.result || {}, pools = r.pools || [], ds = r.daemonsets || {};
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Pods', esc(num(r.pods)), r.unplaced ? num(r.unplaced) + ' fit nowhere' : 'all placed', r.unplaced > 0)}${tile('Nodes', esc(num(r.node_count)), `at least ${num(r.need_nodes)} of ${r.need_pool} needed`)}${tile('CPU requested', esc(pc(r.util_cpu)) + '<small>%</small>', `${CO(r.req_cpu)} of ${CO(r.cap_cpu)} cores`, r.util_cpu > 0.85)}${tile('Memory requested', esc(pc(r.util_mem)) + '<small>%</small>', `${GI(r.req_mem)} of ${GI(r.cap_mem)}`, r.util_mem > 0.85)}</div></section>
      <section class="card"><h2 class="md-h2">Pools</h2><div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>Pool</th><th class="r">Nodes</th><th class="r">Each node</th><th class="r">Usable</th><th>CPU</th><th>Memory</th></tr></thead><tbody>${pools.map(p => `<tr><td><b>${esc(p.pool)}</b></td><td class="r">${esc(num(p.nodes))}</td><td class="r">${esc(CO(p.cpu))} / ${esc(GI(p.mem))}</td><td class="r">${esc(CO(p.alloc_cpu))} / ${esc(GI(p.alloc_mem))}</td><td>${meter(p.used_cpu / p.cap_cpu, 0.75, 0.9)} ${esc(pc(p.used_cpu / p.cap_cpu))}%</td><td>${meter(p.used_mem / p.cap_mem, 0.75, 0.9)} ${esc(pc(p.used_mem / p.cap_mem))}%</td></tr>`).join('')}</tbody></table></div>${ds.count ? `<p class="cs-note">${pl(ds.count, 'DaemonSet')} take ${CO(ds.cpu)} CPU and ${GI(ds.mem)} on every node.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Each node</h2><div class="pfk-nodes">${(r.nodes || []).slice(0, 200).map(n => `<div title="${esc(n.pool)} #${n.i + 1}: ${pc(n.cpu)}% CPU, ${pc(n.mem)}% memory, ${n.pods} pods"><i style="height:${(Math.min(1, n.cpu) * 100).toFixed(0)}%" class="c${n.cpu > 0.9 ? ' hi' : ''}"></i><i style="height:${(Math.min(1, n.mem) * 100).toFixed(0)}%" class="m${n.mem > 0.9 ? ' hi' : ''}"></i></div>`).join('')}</div><div class="pfk-key"><span><i class="c"></i>CPU</span><span><i class="m"></i>Memory</span></div></section>
      <section class="card"><h2 class="md-h2">Losing capacity</h2>${(r.loss || []).length ? `<div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>If we lose</th><th class="r">Pods with nowhere to go</th></tr></thead><tbody>${r.loss.map(l => `<tr class="${l.left ? (l.what.startsWith('zone') ? 'bad' : 'warn') : ''}"><td>${esc(l.what)}</td><td class="r">${l.left ? esc(num(l.left)) : 'none - still fits'}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">No pools to lose.</p>'}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card pfk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 50000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- catalog */
  const SAMPLE_CAT = 'apiVersion: backstage.io/v1alpha1\nkind: Component\nmetadata:\n  name: checkout\n  annotations:\n    github.com/project-slug: acme/checkout\nspec:\n  type: service\n  owner: payments\n  lifecycle: production';
  function pCatalog() {
    if (ST.arg) return one(ST.arg, 'catalog', pCa);
    const s = st_();
    return `<div><h1 class="sd-h">Catalog</h1><p class="lead">Your service catalog scored against the golden path: every component with an owner that exists, a lifecycle, docs, an on-call, its repository and a runbook - plus references that point at nothing and services depending on deprecated ones.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Score the catalog</h2><form data-form="catalog" class="pfk-grid">
        ${area('text', 'Backstage catalog-info.yaml - one or many entities separated by --- (paste several files one after another)', SAMPLE_CAT, 12)}
        ${fld('checks', 'Checks (empty = owner, owner_known, lifecycle, system, description, docs, oncall, repo, runbook)', s.catalog_checks, '', 'owner, oncall, runbook')}
        ${subRow('Score it', '.yaml,.yml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Scored</h2>${itemRows(items('catalog'))}</section>`;
  }
  function pCa(d) {
    const r = d.result || {}, rows = r.rows || [], ck = r.checks || [];
    return `${head(d, 'catalog')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Average score', esc(pc(r.avg)) + '<small>%</small>', `${pl(r.scored, 'entity', 'entities')} scored`, r.avg < 0.6)}${tile('Owners', esc(num((r.owners || []).length)), 'groups and users')}${tile('Broken references', esc(num((r.broken || []).length)), 'point at nothing', (r.broken || []).length > 0)}${tile('Systems', esc(num(Object.keys(r.systems || {}).length)), 'with components')}</div></section>
      <section class="card"><h2 class="md-h2">Checks across the catalog</h2>${bars(ck.map(c => [c.say, c.pass, c.pass < 0.6 ? 'pfk-b warn' : 'pfk-b', '']), v => pc(v) + '%', 'Share passing each check')}</section>
      <section class="card"><h2 class="md-h2">Scorecard</h2><div class="iv-tw"><table class="tb in-cards pfk-t pfk-sc"><thead><tr><th>Entity</th><th>Owner</th><th>Lifecycle</th>${ck.map(c => `<th class="c" title="${esc(c.say)}">${esc(c.key.replace('_', ' '))}</th>`).join('')}<th class="r">Score</th></tr></thead><tbody>${rows.map(e => `<tr><td><b>${esc(e.name)}</b> <span class="mut">${esc(e.kind)}</span></td><td>${esc(e.owner || '—')}</td><td>${esc(e.lifecycle || '—')}</td>${ck.map(c => `<td class="c">${e.missing.includes(c.key) ? '<span class="pfk-x" aria-label="missing">✕</span>' : '<span class="pfk-v" aria-label="passes">✓</span>'}</td>`).join('')}<td class="r"><b>${esc(pc(e.score))}%</b></td></tr>`).join('')}</tbody></table></div></section>
      ${(r.broken || []).length ? `<section class="card"><h2 class="md-h2">Broken references</h2><div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>From</th><th>Field</th><th>Points at</th></tr></thead><tbody>${r.broken.map(b => `<tr><td>${esc(b[0])}</td><td>${esc(b[1])}</td><td><code>${esc(b[2])}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card pfk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- upgrades */
  const SAMPLE_UP = 'apiVersion: networking.k8s.io/v1beta1\nkind: Ingress\nmetadata:\n  name: web\n---\napiVersion: batch/v1beta1\nkind: CronJob\nmetadata:\n  name: nightly';
  function pUpgrades() {
    if (ST.arg) return one(ST.arg, 'upgrades', pUp);
    const s = st_();
    return `<div><h1 class="sd-h">Upgrades</h1><p class="lead">Your manifests against the Kubernetes APIs each release removes: what already fails, what stops applying at your target version, what goes later - with the version to move to and what else changes.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check manifests</h2><form data-form="upgrade" class="pfk-grid">
        ${area('text', 'Kubernetes YAML (documents separated by ---), `kubectl get ... -o yaml` or `helm template` output', SAMPLE_UP, 12)}
        ${fld('current', 'Cluster version now', s.k8s_current, '', '1.29')}${fld('target', 'Upgrading to', s.k8s_target, '', '1.31')}
        ${subRow('Check them', '.yaml,.yml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('upgrade'))}</section>`;
  }
  function pUp(d) {
    const r = d.result || {}, f = r.found || [];
    const W = {'already gone': ['Already gone', 'bad'], 'breaks at the target': ['Breaks at the target', 'bad'], 'removed later': ['Removed later', 'warn']};
    return `${head(d, 'upgrades')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Objects', esc(num(r.objects)), r.current || r.target ? `${r.current || '?'} → ${r.target || '?'}` : 'no versions given')}${tile('Already gone', esc(num(r.gone)), 'fail to apply today', r.gone > 0)}${tile('Break at the target', esc(num(r.breaks)), r.target ? 'removed by ' + r.target : 'set a target', r.breaks > 0)}${tile('Removed later', esc(num(r.later)), 'move them now')}</div></section>
      ${f.length ? `<section class="card"><h2 class="md-h2">Objects to move</h2><div class="iv-tw"><table class="tb in-cards pfk-t"><thead><tr><th>Object</th><th>Uses</th><th>Removed in</th><th>Move to</th><th>Also changes</th><th></th></tr></thead><tbody>${f.map(x => `<tr class="${x.when === 'removed later' ? '' : 'bad'}"><td><b>${esc(x.kind)}</b> ${esc(x.name)}</td><td><code>${esc(x.api)}</code></td><td>${esc(x.removed)}</td><td><code>${esc(x.to)}</code></td><td class="mut">${esc(x.note || '')}</td><td>${tag(W[x.when][0], W[x.when][1])}</td></tr>`).join('')}</tbody></table></div></section>` : `<section class="card"><p class="mut" style="margin:0">None of these objects use a removed API.</p></section>`}
      <section class="card"><h2 class="md-h2">What was read</h2>${bars((r.kinds || []).slice(0, 15).map(([k2, n]) => [k2, n, 'pfk-b', '']), v => num(v), 'Objects by kind')}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card pfk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions plan guard: every pull request is planned, and it fails when the plan would destroy or replace a data store or destroy more than you allow. It never applies.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Terraform folder', s.tf_dir || 'not set'], ['Tool', s.tool === 'tofu' ? 'OpenTofu' : 'Terraform'], ['Version', s.tf_version], ['Destroy limit', s.max_destroy], ['Also data stores', s.protected || 'none'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="plan-guard.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your destroy limit, required tags, prices, cluster reserve, Kubernetes versions and what the plan guard runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="pfk-grid">
        <h2 class="md-h2 wide" style="margin:0">Plans</h2>
        ${fld('max_destroy', 'Destroy limit (0 = none at all)', s.max_destroy, 'type="number" min="0" step="1"')}${fld('required_tags', 'Required tags', s.required_tags, '', 'env, team, cost-center')}${fld('protected', 'Also treat as data stores', s.protected, '', 'aws_route53_zone')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Kubernetes</h2>
        ${fld('headroom', 'Headroom above use', s.headroom, 'type="number" min="0" max="5" step="any"')}${fld('cpu_price', 'Price per core a month', s.cpu_price, 'type="number" min="0" step="any"')}${fld('mem_price', 'Price per GiB a month', s.mem_price, 'type="number" min="0" step="any"')}
        ${fld('reserve_cpu', 'System reserve per node, cores (0 = the GKE rule)', s.reserve_cpu, 'type="number" min="0" step="any"')}${fld('reserve_mem', 'System reserve per node, GiB (0 = the GKE rule)', s.reserve_mem, 'type="number" min="0" step="any"')}
        ${fld('k8s_current', 'Cluster version now', s.k8s_current, '', '1.29')}${fld('k8s_target', 'Upgrading to', s.k8s_target, '', '1.31')}${fld('catalog_checks', 'Catalog checks', s.catalog_checks, '', 'owner, oncall, runbook')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Plan guard</h2>
        ${fld('tf_dir', 'Terraform folder in the repository', s.tf_dir, '', 'infra/prod')}${sel('tool', 'Tool', [['terraform', 'Terraform'], ['tofu', 'OpenTofu']], s.tool)}${fld('tf_version', 'Version', s.tf_version)}
        ${fld('var_file', 'Variables file (optional)', s.var_file, '', 'prod.tfvars')}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk. Cloud keys never go here - use your cloud\'s OIDC role in GitHub.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>A plan shows what Terraform intends; the cloud can still refuse it, and the text plan carries no values - the JSON does.</li><li>Rightsizing uses the use you paste: take the p95 over a busy week, not an average.</li><li>Capacity places pods by their requests; the real scheduler also weighs affinity, spreading, taints and volumes.</li><li>API removals come from the Kubernetes deprecated API migration guide up to 1.32; add-ons have their own.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your clusters or your cloud, or applies a plan.</li><li>Asks for cloud keys, kubeconfigs or tokens.</li><li>Lowers a request for you - you change it, a few workloads at a time.</li><li>Follows anything written inside your plans, manifests or tables: they are data.</li></ul></section>`;
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
      if (kind === 'tfplan') await go('tfplan', {text: S(fd.get('text')), inputs: pick(['max_destroy', 'required_tags', 'protected'])});
      else if (kind === 'rightsize') await go('rightsize', {text: S(fd.get('text')), inputs: pick(['headroom', 'cpu_price', 'mem_price'])});
      else if (kind === 'capacity') await go('capacity', {text: S(fd.get('text')), inputs: pick(['reserve_cpu', 'reserve_mem'])});
      else if (kind === 'catalog') await go('catalog', {text: S(fd.get('text')), inputs: pick(['checks'])});
      else if (kind === 'upgrade') await go('upgrade', {text: S(fd.get('text')), inputs: pick(['current', 'target'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['max_destroy', 'protected', 'required_tags', 'headroom', 'cpu_price', 'mem_price', 'reserve_cpu', 'reserve_mem', 'k8s_current', 'k8s_target', 'catalog_checks', 'tf_dir', 'tf_version', 'var_file', 'tool', 'runner'];


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
    const box = $('#pfFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/pfdesk/chat'); ST.chat = r.id; }
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


