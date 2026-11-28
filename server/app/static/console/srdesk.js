/* SRE DESK - the Site Reliability Engineer's own section, like the finance desks (owner: "Site Reliability Engineer same as finance
   desks"). A thin top bar, then the SRE chat (its own conversation, kind 'sre') beside the desk's pages: Today, SLOs (error budgets,
   burn rates, the Prometheus rules), Alerts (rules checked, noise counted), Incidents (timeline + blameless postmortem), Capacity
   (latency, histograms, growth, queues, availability), Settings. The pages call /api/srdesk/do/<part>; nothing changes on her systems. */
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

  const TABS = [['today', 'Today'], ['slos', 'SLOs'], ['alerts', 'Alerts'], ['incidents', 'Incidents'], ['capacity', 'Capacity'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What should my SLO be?', 'Where do I start with reliability?', 'How do I cut pager noise?'],
    slos: ['99.9 or 99.95?', 'What counts as a good event?', 'What do I do when the budget is spent?'],
    alerts: ['Which alerts should page?', 'How long should `for` be?', 'How do I alert on symptoms?'],
    incidents: ['Write the summary for this incident', 'What action items does this need?', 'How do we run a blameless review?'],
    capacity: ['How much headroom do I need?', 'Is my p99 good enough?', 'How many replicas do I need?'],
    settings: ['How long should the SLO window be?', 'Which metric should I use for errors?', 'What scrape interval is safe?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', cap: 'latency', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.srdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.srdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'sre', name: 'SRE'} : null;
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
  const run = (part, a) => api('POST', '/api/srdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/srdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Site Reliability Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="srHire">Hire the Site Reliability Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#srHire').onclick = async () => { try { await api('POST', '/api/employees/sre/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Site reliability</div><div class="sd-site" id="srSite"></div></div>
          <span id="srState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="SRE chat">
          <div class="sd-chathead"><div class="t"><b>SRE chat</b><span>Paste an alert, a timeline, rules or numbers - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="srFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="srPick" multiple hidden accept=".txt,.log,.json,.csv,.yml,.yaml,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="SRE desk" id="sdTabs"></nav>
          <div id="srPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste an incident or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#srPick').click()});
    $('#srPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.srdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.srdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/srdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#srPage').addEventListener('click', onPageClick);
    $('#srPage').addEventListener('submit', onSubmit);
    $('#srPage').addEventListener('change', onChange);
    $('#srPage').addEventListener('input', onInput);
    $('#srPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#srState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#srSite').textContent = [s.service, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), inc = k.incidents || {};
    const n = {incidents: inc.open || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/srdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#srPage'); if (!box) return;
    const fn = {today: pToday, slos: pSlos, alerts: pAlerts, incidents: pIncidents, capacity: pCapacity, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="srk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Check', 'warn'], info: ['Note', '']};
  const ms = v => v === null || v === undefined ? '—' : Number(v) >= 10000 ? num(Math.round(v / 100) / 10) + ' s' : num(Math.round(Number(v) * 10) / 10) + ' ms';
  const pct = (v, d = 2) => { if (v === null || v === undefined) return '—'; let t = (Number(v) * 100).toFixed(d); if (t.includes('.')) t = t.replace(/\.?0+$/, ''); return t + '%'; };
  const mins = m => m === null || m === undefined ? '—' : m < 1 ? Math.round(m * 60) + ' s' : m < 120 ? (Math.round(m * 10) / 10) + ' min' : (Math.round(m / 6) / 10) + ' h';
  const KN = {slo: 'SLO', burn: 'Burn rate', avail: 'Availability', latency: 'Latency', buckets: 'Histogram', capacity: 'Capacity', queue: 'Queue',
    rules: 'Alert rules', noise: 'Alert noise', incident: 'Incident'};
  const ROUTE = {slo: 'slos', burn: 'slos', rules: 'alerts', noise: 'alerts', incident: 'incidents', latency: 'capacity', buckets: 'capacity',
    capacity: 'capacity', queue: 'capacity', avail: 'capacity'};
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'slo': return b.used === null || b.used === undefined ? `target ${pct(b.target, 3)}` : `${pct(b.used, 1)} of the budget used · burn ${num(b.burn)}`;
      case 'burn': return `burn ${num(b.burn)} · ${pl(b.fired || 0, 'alert')} fired`;
      case 'avail': return `${pct(b.availability, 3)} · ${mins(b.down)} down a month`;
      case 'latency': case 'buckets': return `p99 ${ms(b.p99)}${b.under !== null && b.under !== undefined ? ' · ' + pct(b.under) + ' within the threshold' : ''}`;
      case 'capacity': return `${pct(b.share, 0)} of the limit${b.limit_on ? ' · reaches it ' + dmy(b.limit_on) : ''}`;
      case 'queue': return `${pct(b.utilisation, 0)} busy · response ${ms(b.response)}`;
      case 'rules': return `${pl(b.alerts || 0, 'alert')} · ${pl(b.problems || 0, 'problem')} · ${pl(b.warnings || 0, 'warning')}`;
      case 'noise': return `${num(b.per_week)} pages a week · noisiest ${b.top || '—'}`;
      case 'incident': return `${b.severity || 'no severity'} · impact ${b.impact || '—'} · ${b.resolved ? 'resolved' : 'not resolved'}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="srk-list">${list.map(x => `<button type="button" class="srk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="srk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="srk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="srk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><p>${esc(i.text)}</p></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows) => `<label class="ins-lab wide">${esc(l)}<textarea class="in mono srk-ed" name="${n}" rows="${rows || 6}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft srk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = label => `<div class="srk-row wide">${fileBtn('text', '.txt,.csv,.log,.yml,.yaml,.json,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card srk-sum ${ok ? 'okv' : 'badv'}"><p class="srk-big">${esc(r.verdict)}</p></section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad');
  function spark(pts, label, fmt, lines_, capAt) {   /* pts: [x, y]; lines_: [[y, label, cls]]; capAt: clip the scale there */
    if (!pts.length) return '';
    const W = 760, H = 170, L = 52, B = 22, xs = pts.map(p => p[0]), top = Math.max(...pts.map(p => p[1]));
    const x0 = Math.min(...xs), x1 = Math.max(...xs);
    const my = Math.max(1e-9, capAt ? Math.min(top, capAt) : top, ...(lines_ || []).map(l => l[0] * 1.15));
    const x = v => L + (x1 === x0 ? 0 : (v - x0) / (x1 - x0)) * (W - L - 8), y = v => 8 + (1 - Math.min(v, my) / my) * (H - 8 - B);
    const path = pts.map(([a, b], k) => `${k ? 'L' : 'M'}${x(a).toFixed(1)},${y(b).toFixed(1)}`).join('');
    const ls = (lines_ || []).map(([v, t, c], i) => `<line class="th ${c || ''}" x1="${L}" x2="${W - 8}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${i % 2 ? L + 6 : W - 10}" y="${(y(v) - 4).toFixed(1)}" text-anchor="${i % 2 ? 'start' : 'end'}">${esc(t)}</text>`).join('');
    const clip = top > my ? `<text class="tx" x="${W - 10}" y="18" text-anchor="end">peaks at ${esc(fmt(top))} - off the scale</text>` : '';
    return `<div class="cs-chart srk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}"><line class="grid" x1="${L}" x2="${W - 8}" y1="${y(0)}" y2="${y(0)}"/><text class="tx" x="${L - 6}" y="${y(0) + 4}" text-anchor="end">0</text><text class="tx" x="${L - 6}" y="${y(my) + 4}" text-anchor="end">${esc(fmt(my))}</text>${ls}<path class="srk-ln" d="${path}"/>${clip}</svg></div>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, b = k.budget, inc = k.incidents || {}, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Error budget', b ? `${esc(pct(1 - (b.used || 0), 1))}<small> left</small>` : '—', b ? `burn rate ${num(b.burn)} · ${b.number}` : 'set an SLO to see it', b && b.used >= 1),
      tile('Pages a week', k.pages_week === null || k.pages_week === undefined ? '—' : esc(num(k.pages_week)), 'from your alert history', k.pages_week > 14),
      tile('Incidents', esc(num(inc.count || 0)), inc.median && inc.median.resolve ? 'median to resolve ' + inc.median.resolve : 'timelines read', inc.open),
      tile('Alert rules checked', esc(num(c.rules || 0)), 'noisy rules found and fixed')];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}${s.service ? ' ' + esc(s.service) + ', SLO ' + esc(pct(s.target, 3)) + ' over ' + esc(s.window_days) + ' days.' : ''}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="srk-starts">
        <button type="button" class="srk-start" data-go="slos"><b>Set an SLO</b><span>Error budget, burn rate and the alert rules for it</span></button>
        <button type="button" class="srk-start" data-go="alerts"><b>Quiet the pager</b><span>Check alert rules, count the noise in your alert history</span></button>
        <button type="button" class="srk-start" data-go="incidents"><b>Read an incident</b><span>Timeline, the times between, a blameless postmortem</span></button>
        <button type="button" class="srk-start" data-go="capacity"><b>Plan capacity</b><span>Latency, growth, queue waits and availability</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- SLOs */
  function pSlos() {
    if (ST.arg) return one(ST.arg, 'slos', d => d.kind === 'burn' ? pBurn(d) : pSlo(d));
    const s = st_(), rules = ST.out.rules;
    return `<div><h1 class="sd-h">SLOs and error budgets</h1><p class="lead">How much unreliability you agreed to, how fast it is going, and the alerts that tell you before it is gone.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">An error budget</h2><form data-form="slo" class="srk-grid">
        ${fld('target', 'SLO target (%)', Number(((s.target ?? 0.999) * 100).toFixed(4)), 'type="number" min="50" max="99.9999" step="any"')}${fld('window_days', 'Window (days)', s.window_days || 30, 'type="number" min="1" max="366" step="1"')}
        ${fld('good', 'Good events so far', '', 'type="number" min="0" step="any"', 'optional')}${fld('total', 'All events so far', '', 'type="number" min="1" step="any"', 'optional')}
        ${fld('elapsed_days', 'Days of the window so far', '', 'type="number" min="0.001" step="any"', 'the whole window')}
        <div class="md-acts wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1"><button class="btn" type="submit">Work it out</button></div></form></section>
      <section class="card"><h2 class="md-h2">Burn rate over your samples</h2><form data-form="burn" class="srk-grid">
        ${area('text', 'One sample per line: time, good, total (counters or per-interval counts). Times: ISO 8601 or unix seconds.', '2026-11-27T10:00:00Z, 998812, 1000000\n2026-11-27T10:01:00Z, 999650, 1001000')}
        ${fld('target', 'SLO target (%)', Number(((s.target ?? 0.999) * 100).toFixed(4)), 'type="number" min="50" max="99.9999" step="any"')}${fld('window_days', 'Window (days)', s.window_days || 30, 'type="number" min="1" max="366" step="1"')}
        ${subRow('Check the burn')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Burn-rate alert rules for Prometheus</h2><p class="cs-note" style="margin-top:0">${s.bad_metric ? `From <code>${esc(s.bad_metric)}</code> / <code>${esc(s.total_metric)}</code>${s.selector ? ' ' + esc(s.selector) : ''}, SLO ${esc(pct(s.target, 3))} over ${esc(s.window_days)} days. Change these in Settings.` : 'Name your metrics in Settings first.'}</p>
        <button class="btn soft" type="button" data-rules="1">Write the rules</button>${rules ? (rules.error ? err(rules) : `<div class="md-acts" style="margin:12px 0 6px"><code>${esc(rules.file)}</code><span>${copyBtn(rules.yaml)} <button class="btn soft sm" type="button" data-dlrules="1">Download</button></span></div>${pre(rules.yaml, 'code')}<p class="cs-note">${esc(rules.note)}</p>`) : ''}</section>
      <section class="card"><h2 class="md-h2">What the nines allow</h2>${nines()}</section>
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('slo', 'burn'))}</section>`;
  }
  function nines() {
    const rows = (K().health || {}).nines || [];
    return `<table class="tb"><thead><tr><th>Target</th><th class="r">A day</th><th class="r">A week</th><th class="r">30 days</th><th class="r">A year</th></tr></thead><tbody>${rows.map(r => `<tr><td>${esc(pct(r.target, 3))}</td><td class="r">${esc(r.day)}</td><td class="r">${esc(r.week)}</td><td class="r">${esc(r.month30)}</td><td class="r">${esc(r.year)}</td></tr>`).join('')}</tbody></table>`;
  }
  function pSlo(d) {
    const r = d.result || {}, has = r.used !== undefined;
    const used = Math.min(1, Math.max(0, r.used || 0));
    return `${head(d, 'slos')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Target', esc(pct(r.target, 3)), 'over ' + num(r.window_days) + ' days')}${tile('Allowed', esc(r.allowed), 'of full outage in the window')}
        ${has ? tile('Budget used', esc(pct(r.used, 1)), num(r.bad) + ' bad of ' + num(r.allowed_bad) + ' allowed', r.used >= 1) + tile('Burn rate', esc(num(r.burn_rate)), r.runs_out_in_days !== null && r.runs_out_in_days !== undefined ? 'runs out in ' + num(r.runs_out_in_days) + ' days' : '1 = exactly on budget', r.burn_rate > 1) : ''}</div></section>
      ${has ? `<section class="card"><h2 class="md-h2">The budget</h2><div class="srk-meter" role="img" aria-label="${esc(pct(used, 0))} used"><i style="width:${(used * 100).toFixed(1)}%" class="${used >= 1 ? 'bad' : used > (r.elapsed_days / r.window_days) ? 'warn' : ''}"></i><b style="left:${(r.elapsed_days / r.window_days * 100).toFixed(1)}%" title="Where the window is now"></b></div><p class="cs-note">Bar = budget used; the line = how far through the window you are. Used faster than the line means the budget runs out early.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }
  function pBurn(d) {
    const r = d.result || {}, a = r.alerts || [], f = r.fired || [];
    const pts = (r.series || []).map(p => [p.t, p.fast]);
    return `${head(d, 'slos')}${verdict(r, !f.some(x => x.severity === 'page'))}
      <section class="cs-hero"><div class="top">${tile('SLI', esc(pct(r.sli, 3)), 'over ' + num(r.hours) + ' h')}${tile('Burn rate', esc(num(r.burn_overall)), 'over all the samples', r.burn_overall > 1)}
        ${tile('Budget used', esc(pct(r.budget_used, 1)), 'of the ' + num(r.window_days) + '-day budget', r.budget_used > 0.5)}${tile('Alerts fired', esc(num(f.length)), r.counters ? 'counters turned into steps' : 'per-interval counts', f.length)}</div></section>
      <section class="card"><h2 class="md-h2">Burn rate over the fast window</h2>${spark(pts, 'Burn rate', v => num(Math.round(v * 10) / 10), a.slice(0, 2).map(x => [x.burn, x.name + ' ' + x.burn + 'x', x.severity]), (a[0] || {}).burn * 3)}<p class="cs-note">The lines are the burn rates that page. The alert needs both its long and its short window above the line, so a short spike that is already over does not wake anyone.</p></section>
      <section class="card"><h2 class="md-h2">The alerts</h2><table class="tb"><thead><tr><th>Alert</th><th>Windows</th><th class="r">Burn rate</th><th>Goes to</th><th class="r">Fired</th></tr></thead><tbody>${a.map(x => `<tr><td>${esc(x.name)}</td><td>${esc(x.long_h >= 1 ? num(x.long_h) + ' h' : num(x.long_h * 60) + ' min')} and ${esc(x.short_h >= 1 ? num(x.short_h) + ' h' : num(Math.round(x.short_h * 60)) + ' min')}</td><td class="r">${esc(num(x.burn))}x</td><td>${tag(x.severity === 'page' ? 'Page' : 'Ticket', x.severity === 'page' ? 'bad' : 'warn')}</td><td class="r">${esc(num(x.fired))}</td></tr>`).join('')}</tbody></table>
        ${f.length ? `<div class="srk-fired">${f.slice(0, 20).map(x => `<div>${tag(x.alert, x.severity === 'page' ? 'bad' : 'warn')} <span>${esc(dt(x.at))}</span><span class="mut">long ${esc(num(x.long))}x, short ${esc(num(x.short))}x</span></div>`).join('')}</div>` : ''}</section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }

  /* ---------------------------------------------------------------- alerts */
  function pAlerts() {
    if (ST.arg) return one(ST.arg, 'alerts', d => d.kind === 'noise' ? pNoise(d) : pRules(d));
    const s = st_();
    return `<div><h1 class="sd-h">Alerts and on-call</h1><p class="lead">An alert should mean someone has to act now. Find the ones that wake people for nothing.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check alert rules</h2><form data-form="rules" class="srk-grid">
        ${area('text', 'A Prometheus rules file (YAML)', 'groups:\n  - name: api\n    rules:\n      - alert: HighErrorRate\n        expr: ...', 8)}
        ${fld('scrape_s', 'Scrape interval (s)', s.scrape_s || 30, 'type="number" min="1" max="3600" step="1"')}
        ${subRow('Check the rules')}</form></section>
      <section class="card"><h2 class="md-h2">Count the noise</h2><form data-form="noise" class="srk-grid">
        ${area('text', 'Your alert history as CSV: alert name, start, end - and severity, acknowledged if you have them', 'alertname,startsAt,endsAt,severity,acked\nDiskFull,2026-11-20T02:14:00Z,2026-11-20T02:16:00Z,page,yes')}
        <p class="cs-note wide" style="margin:0">Out of hours = outside ${esc(s.work_start)}:00-${esc(s.work_end)}:00 or on ${esc(s.weekend)} in ${esc(s.tz)} (Settings).</p>
        ${subRow('Count it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('rules', 'noise'))}</section>`;
  }
  function pRules(d) {
    const r = d.result || {}, rs = r.rules || [];
    const bad = rs.filter(x => x.issues.some(i => i.sev === 'bad' || i.sev === 'warn'));
    return `${head(d, 'alerts')}${verdict(r, !(r.counts || {}).bad)}
      <section class="cs-hero"><div class="top">${tile('Alerts', esc(num(r.alerts)), pl(r.records || 0, 'recording rule'))}${tile('Problems', esc(num((r.counts || {}).bad || 0)), 'will misfire or never fire', (r.counts || {}).bad)}
        ${tile('Warnings', esc(num((r.counts || {}).warn || 0)), 'noisy or hard to act on', (r.counts || {}).warn)}${tile('Nothing to fix', esc(num(r.clean)), 'of ' + num(rs.length))}</div></section>
      <section class="card"><h2 class="md-h2">Rule by rule</h2>${bad.length ? bad.map(x => `<details class="srk-rule" data-key="r:${esc(d.id)}:${esc(x.name)}"${ST.open.has('r:' + d.id + ':' + x.name) ? ' open' : ''}><summary><b>${esc(x.name)}</b>${x.severity ? tag(x.severity, '') : ''}<span class="mut">${esc(x.group)}</span><span style="flex:1"></span>${pl(x.issues.length, 'finding')}</summary>${pre(x.expr)}${issueRows(x.issues)}</details>`).join('') : empty('Every rule passed these checks.')}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card srk-raw"><summary>What you pasted</summary>${pre(d.text)}</details>`;
  }
  function pNoise(d) {
    const r = d.result || {}, t = r.table || [], mx = Math.max(1, ...(r.by_hour || [0]));
    const hrs = (r.by_hour || []).map((v, h) => `<div class="srk-hr ${(h < 7 || h >= 23) ? 'night' : (h < st_().work_start || h >= st_().work_end) ? 'off' : ''}" title="${h}:00 - ${num(v)}"><i style="height:${(v / mx * 100).toFixed(0)}%"></i><span>${h % 6 === 0 ? h : ''}</span></div>`).join('');
    return `${head(d, 'alerts')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Pages a week', esc(num(r.pages_per_week)), pl(r.pages, 'page') + ' in ' + num(r.days) + ' days', r.pages_per_week > 14)}${tile('Out of hours', esc(num(r.out_of_hours)), 'in ' + r.tz, r.out_of_hours > r.pages / 2)}
        ${tile('At night', esc(num(r.nights)), '23:00-07:00', r.nights)}${tile('Rules firing', esc(num(r.distinct)), pl(r.alerts, 'firing'))}</div></section>
      <section class="card"><h2 class="md-h2">When they fire (${esc(r.tz)})</h2><div class="srk-hours" role="img" aria-label="Alerts by hour of day">${hrs}</div><p class="cs-note">Darker = at night, mid = outside working hours.</p></section>
      <section class="card"><h2 class="md-h2">The noisiest</h2><table class="tb"><thead><tr><th>Alert</th><th class="r">Fired</th><th class="r">A week</th><th class="r">Typical length</th><th class="r">Flaps</th><th class="r">Acted on</th></tr></thead><tbody>${t.slice(0, 30).map(x => `<tr><td><b>${esc(x.name)}</b>${(x.advice || []).map(a => `<div class="mut" style="font-size:13px">${esc(a)}</div>`).join('')}</td><td class="r">${esc(num(x.count))}</td><td class="r">${esc(num(x.per_week))}</td><td class="r">${esc(mins(x.median_min))}</td><td class="r">${esc(num(x.flaps))}</td><td class="r">${x.acked_share === null || x.acked_share === undefined ? '—' : esc(pct(x.acked_share, 0))}</td></tr>`).join('')}</tbody></table></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }

  /* ---------------------------------------------------------------- incidents */
  function pIncidents() {
    if (ST.arg) return one(ST.arg, 'incidents', pIncident);
    const s = st_(), inc = K().incidents || {}, m = inc.median || {};
    return `<div><h1 class="sd-h">Incidents</h1><p class="lead">Paste the timeline - your chat, your notes, the incident channel - and get the times and a blameless postmortem draft.</p></div>${ro()}
      ${inc.count ? `<section class="cs-hero"><div class="top">${tile('Incidents', esc(num(inc.count)), pl(inc.open || 0, 'not resolved'), inc.open)}${tile('Median to detect', esc(m.detect || '—'), '')}${tile('Median to mitigate', esc(m.mitigate || '—'), '')}${tile('Median to resolve', esc(m.resolve || '—'), '')}</div></section>` : ''}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a timeline</h2><form data-form="incident" class="srk-grid">
        ${area('text', 'One line each, starting with the time (10:02 or 2026-11-27 10:02)', '2026-11-27 09:58 deploy v2.3 went out\n10:02 first errors in checkout, SEV2\n10:14 alert fired: CheckoutErrorBudgetBurnFast\n10:21 on it, investigating\n10:35 rolled back to v2.2\n10:50 resolved\n10:52 TODO add a canary step', 9)}
        ${fld('tz', 'Time zone of the times', s.tz || 'UTC', '', 'Europe/London')}${fld('day', 'Day (if the lines have only times)', '', 'type="date"')}
        ${fld('impact', 'Who was affected (optional)', '', '', 'e.g. 4% of checkouts failed')}${fld('root_cause', 'Root cause, if you know it (optional)', '')}
        ${subRow('Read it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('incident'))}</section>`;
  }
  function pIncident(d) {
    const r = d.result || {}, s = r.said || {}, ev = r.events || [];
    const STG = {start: ['Impact started', 'bad'], detect: ['Detected', 'warn'], ack: ['Acknowledged', ''], mitigate: ['Mitigated', 'ok'], resolve: ['Resolved', 'ok']};
    return `${head(d, 'incidents')}${verdict(r, 'resolve' in (r.marks || {}) && isOk(r))}
      <section class="cs-hero"><div class="top">${tile('To detect', esc(s.detect || '—'), 'from impact start', (r.times || {}).detect_s > 900)}${tile('To acknowledge', esc(s.ack || '—'), 'from the alert', (r.times || {}).ack_s > 900)}
        ${tile('To mitigate', esc(s.mitigate || '—'), 'users stop feeling it')}${tile('To resolve', esc(s.resolve || '—'), r.severity || '')}</div></section>
      <section class="card"><h2 class="md-h2">Timeline <span class="mut" style="font-weight:400;font-size:14px">${esc(r.tz)}</span></h2><ol class="srk-tl">${ev.map(e => `<li class="${e.mark ? 'mk ' + e.stage : ''}"><span class="t">${esc(e.local.slice(11))}</span><span class="x">${esc(e.text)}</span>${e.mark ? tag(STG[e.stage][0], STG[e.stage][1]) : ''}</li>`).join('')}</ol></section>
      ${(r.followups || []).length ? `<section class="card"><h2 class="md-h2">Follow-ups found</h2>${r.followups.map(t => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(t)}</span></div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>
      <section class="card"><h2 class="md-h2">Postmortem draft</h2><p class="cs-note" style="margin-top:0">Blameless: it names systems and decisions. The parts only you know are left as blanks - Hoola does not make them up.</p>
        <div class="md-acts" style="margin:0 0 6px"><code>postmortem-${esc(d.number.toLowerCase())}.md</code><span>${copyBtn(r.postmortem || '')} <button class="btn soft sm" type="button" data-dlpm="1">Download</button></span></div>${pre(r.postmortem || '', 'code')}</section>`;
  }

  /* ---------------------------------------------------------------- capacity */
  function pCapacity() {
    if (ST.arg) return one(ST.arg, 'capacity', d => ({latency: pLatency, buckets: pBuckets, capacity: pCap, queue: pQueue, avail: pAvail}[d.kind] || pLatency)(d));
    const s = st_(), w = ST.cap || 'latency';
    const W_ = [['latency', 'Latency'], ['buckets', 'Histogram'], ['capacity', 'Growth'], ['queue', 'Queue'], ['avail', 'Availability']];
    const forms = {
      latency: `<form data-form="latency" class="srk-grid">${area('text', 'Durations: one per line, a CSV with a latency column, or a log with "123ms" in each line', '84\n120\n97\n1430\n...')}
        ${fld('threshold_ms', 'Latency threshold (ms)', s.latency_ms || 300, 'type="number" min="0.001" step="any"')}${sel('unit', 'Plain numbers are in', [['ms', 'milliseconds'], ['s', 'seconds'], ['us', 'microseconds']], 'ms')}
        ${fld('objective', 'Share that must be within it (%)', '', 'type="number" min="1" max="100" step="any"', 'e.g. 99')}${subRow('Work it out')}</form>`,
      buckets: `<form data-form="buckets" class="srk-grid">${area('text', 'The _bucket lines of one histogram (from /metrics or a query)', 'http_request_duration_seconds_bucket{le="0.1"} 7341\nhttp_request_duration_seconds_bucket{le="0.25"} 9210\nhttp_request_duration_seconds_bucket{le="+Inf"} 9502')}
        ${fld('threshold_ms', 'Latency threshold (ms)', s.latency_ms || 300, 'type="number" min="0.001" step="any"')}${sel('unit', 'The le values are in', [['s', 'seconds'], ['ms', 'milliseconds']], 's')}${subRow('Work it out')}</form>`,
      capacity: `<form data-form="capacity" class="srk-grid">${area('text', 'One line per day or week: date, peak use', '2026-09-01, 41\n2026-09-08, 43.5\n2026-09-15, 46')}
        ${fld('limit', 'The limit (same unit)', '', 'type="number" min="0.000001" step="any" required', 'e.g. 100')}${fld('headroom', 'Headroom line (% of the limit)', 80, 'type="number" min="10" max="100" step="any"')}
        ${fld('unit', 'Unit (optional)', '', 'maxlength="12"', 'e.g. %, GB, req/s')}${fld('what', 'What it is (optional)', '', '', 'e.g. database CPU')}${subRow('Forecast it')}</form>`,
      queue: `<form data-form="queue" class="srk-grid">${fld('rps', 'Requests per second at peak', '', 'type="number" min="0.001" step="any" required')}${fld('service_ms', 'Time per request (ms)', '', 'type="number" min="0.001" step="any" required')}
        ${fld('servers', 'Servers / workers', 2, 'type="number" min="1" max="400" step="1"')}<div class="md-acts wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1"><button class="btn" type="submit">Work it out</button></div></form>`,
      avail: `<form data-form="avail" class="srk-grid">${area('tree', 'The system, one part per line, indented by 2 spaces. A part: name, availability %. A group: name: all (every part needed) or name: any (or any 2 of N).', 'shop: all\n  load balancer, 99.99\n  app: any\n    app 1, 99.5\n    app 2, 99.5\n  database, 99.95', 8)}
        ${fld('target', 'Target (%)', Number(((s.target ?? 0.999) * 100).toFixed(4)), 'type="number" min="50" max="99.9999" step="any"')}<div class="md-acts wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1"><button class="btn" type="submit">Work it out</button></div></form>`};
    return `<div><h1 class="sd-h">Latency and capacity</h1><p class="lead">How fast, how full, how long until it is not enough - and how available the whole system is from its parts.</p></div>${ro()}
      ${CAN() ? `<section class="card"><div class="srk-seg" role="tablist" aria-label="What to work out">${W_.map(([k, t]) => `<button type="button" data-cap="${k}" aria-pressed="${k === w}">${esc(t)}</button>`).join('')}</div><div style="margin-top:14px">${forms[w]}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('latency', 'buckets', 'capacity', 'queue', 'avail'))}</section>`;
  }
  function pLatency(d) {
    const r = d.result || {}, p = r.percentiles || {}, h = r.hist || {}, mx = Math.max(1, ...(h.counts || [0]));
    const lab = i => i === 0 ? '≤ ' + ms(h.edges[0]) : i < h.edges.length ? ms(h.edges[i - 1]) + '–' + ms(h.edges[i]) : '> ' + ms(h.edges[h.edges.length - 1]);
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Median', esc(ms(p.p50)), num(r.count) + ' requests')}${tile('p99', esc(ms(p.p99)), 'p95 ' + ms(p.p95))}${tile('Within ' + ms(r.threshold_ms), esc(pct(r.under_threshold)), r.objective ? 'objective ' + pct(r.objective) : '', r.objective && r.under_threshold < r.objective)}${tile('Apdex', esc(num(r.apdex)), 'satisfied ≤ T, tolerating ≤ 4T')}</div></section>
      <section class="card"><h2 class="md-h2">Percentiles</h2><table class="tb"><thead><tr>${Object.keys(p).map(k => `<th class="r">${esc(k)}</th>`).join('')}<th class="r">max</th></tr></thead><tbody><tr>${Object.values(p).map(v => `<td class="r">${esc(ms(v))}</td>`).join('')}<td class="r">${esc(ms(r.max_ms))}</td></tr></tbody></table></section>
      <section class="card"><h2 class="md-h2">Spread around your threshold</h2>${bars((h.counts || []).map((c, i) => [lab(i), c, i > 2 ? 'srk-b warn' : 'srk-b']), num, 'Requests by duration')}</section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }
  function pBuckets(d) {
    const r = d.result || {}, q = r.quantiles || {};
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('p50', esc(ms((q.p50 || {}).ms)), 'interpolated')}${tile('p99', esc(ms((q.p99 || {}).ms)), (q.p99 || {}).between_ms ? 'true value ' + ms(q.p99.between_ms[0]) + '–' + (q.p99.between_ms[1] === null ? 'above' : ms(q.p99.between_ms[1])) : '')}
        ${r.under_threshold !== undefined ? tile('Within ' + ms(r.threshold_ms), esc(pct(r.under_threshold)), r.estimated ? 'estimated: no bucket ends there' : 'exact: a bucket ends there', r.estimated) : ''}${tile('Requests', esc(num(r.total)), pl((r.buckets || []).length, 'bucket'))}</div></section>
      <section class="card"><h2 class="md-h2">Quantiles and where the true value lies</h2><table class="tb"><thead><tr><th>Quantile</th><th class="r">Estimate</th><th class="r">Bucket from</th><th class="r">to</th></tr></thead><tbody>${Object.entries(q).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="r">${esc(ms(v.ms))}</td><td class="r">${esc(ms(v.between_ms[0]))}</td><td class="r">${v.between_ms[1] === null ? '+Inf' : esc(ms(v.between_ms[1]))}</td></tr>`).join('')}</tbody></table></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }
  function pCap(d) {
    const r = d.result || {}, u = r.unit || '';
    const pts = (r.series || []).map(p => [new Date(p.d + 'T00:00').getTime(), p.v]);
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Now', esc(num(r.now)) + '<small>' + esc(u) + '</small>', pct(r.now_share, 0) + ' of ' + num(r.limit) + u, r.now_share >= r.headroom)}${tile('Growth', esc((r.slope_per_week > 0 ? '+' : '') + num(Math.round(r.slope_per_week * 1000) / 1000)) + '<small>' + esc(u) + '/week</small>', 'fit r2 ' + num(r.r2), r.r2 < 0.5)}
        ${tile(Math.round(r.headroom * 100) + '% line', r.hits_headroom ? esc(dmy(r.hits_headroom)) : '—', r.weeks_left !== undefined ? num(r.weeks_left) + ' weeks away' : '', r.weeks_left !== undefined && r.weeks_left < 8)}${tile('The limit', r.hits_limit ? esc(dmy(r.hits_limit)) : '—', 'at this trend')}</div></section>
      <section class="card"><h2 class="md-h2">Peak use and the trend</h2>${spark(pts, 'Peak use', v => num(Math.round(v * 10) / 10), [[r.limit, 'limit', 'bad'], [r.limit * r.headroom, Math.round(r.headroom * 100) + '%', 'warn']])}<p class="cs-note">A straight-line trend from ${esc(dmy(r.from))} to ${esc(dmy(r.to))}. Launches, seasons and one big customer do not follow lines.</p></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }
  function pQueue(d) {
    const r = d.result || {};
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Busy', esc(pct(r.utilisation, 0)), num(r.servers) + ' servers', r.utilisation > 0.8)}${tile('Requests that wait', r.p_wait !== undefined ? esc(pct(r.p_wait, 0)) : '—', '')}${tile('Response', esc(ms(r.response_ms)), 'wait ' + ms(r.wait_ms) + ' + work ' + ms(r.service_ms))}${tile('One server down', r.one_down_utilisation !== undefined ? esc(pct(r.one_down_utilisation, 0)) : '—', 'busy on the rest', r.one_down_utilisation >= 1)}</div></section>
      ${(r.curve || []).length ? `<section class="card"><h2 class="md-h2">Response time as it gets busier</h2>${bars(r.curve.map(c => [pct(c.utilisation, 0) + ' busy (' + num(c.rps) + ' req/s)', c.response_ms, c.utilisation >= 0.9 ? 'srk-b warn' : 'srk-b']), ms, 'Response time by utilisation')}</section>` : ''}
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }
  function pAvail(d) {
    const r = d.result || {}, ps = r.by_part || [];
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Availability', esc(pct(r.availability, 4)), r.target ? 'target ' + pct(r.target, 4) : '', r.target && r.availability < r.target)}${tile('Down a month', esc(mins(r.downtime_month_min)), 'about')}${tile('Costs the most', esc(r.weakest || '—'), '')}${tile('Parts', esc(num(r.parts)), '')}</div></section>
      <section class="card"><h2 class="md-h2">Where the downtime comes from</h2><table class="tb"><thead><tr><th>Part</th><th class="r">Its availability</th><th class="r">Minutes a month it costs</th><th class="r">A second copy saves</th></tr></thead><tbody>${ps.map(p => `<tr><td>${esc(p.name)}</td><td class="r">${esc(pct(p.availability, 3))}</td><td class="r">${esc(num(p.saves_min_month))}</td><td class="r">${esc(num(p.replica_saves_min_month))}</td></tr>`).join('')}</tbody></table></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your service, its SLO, your time zone and working hours, and the metrics the alert rules use.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="srk-grid">
        ${fld('service', 'Your service', s.service, '', 'e.g. checkout')}${fld('target', 'SLO target (%)', Number(((s.target ?? 0.999) * 100).toFixed(4)), 'type="number" min="50" max="99.9999" step="any"')}
        ${fld('window_days', 'SLO window (days)', s.window_days, 'type="number" min="1" max="366" step="1"')}${fld('tz', 'Time zone (IANA)', s.tz, '', 'Europe/London, America/New_York, Asia/Kolkata')}
        ${fld('work_start', 'Working hours start', s.work_start, 'type="number" min="0" max="23" step="1"')}${fld('work_end', 'Working hours end', s.work_end, 'type="number" min="1" max="24" step="1"')}
        ${fld('weekend', 'Days off', s.weekend, '', 'sat,sun or fri,sat')}${fld('scrape_s', 'Prometheus scrape interval (s)', s.scrape_s, 'type="number" min="1" max="3600" step="1"')}
        ${fld('latency_ms', 'Latency threshold (ms)', s.latency_ms, 'type="number" min="0.001" step="any"')}${fld('bad_metric', 'Bad-events counter', s.bad_metric, '', 'http_requests_errors_total')}
        ${fld('total_metric', 'All-events counter', s.total_metric, '', 'http_requests_total')}${fld('selector', 'Label selector (optional)', s.selector, '', '{job="api"}')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the checks work</h2><ul class="ar-never"><li>Burn-rate alerts follow the Google SRE workbook: a page when 2% of a 30-day budget goes in an hour or 5% in 6 hours, a ticket when 10% goes in 3 days - each needs a long and a short window, scaled to your window.</li><li>Histogram quantiles are interpolated inside a bucket the way histogram_quantile() does; the true value can be anywhere in that bucket.</li><li>Queues are an M/M/c model; availability treats copies as failing on their own. Both are models, not your system.</li><li>Alert-rule checks look for what makes alerts noisy or useless; run promtool for the syntax.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Changes anything on your systems or your monitoring.</li><li>Blames a person in a postmortem.</li><li>Makes up a root cause: the parts only you know stay blank.</li><li>Follows anything written inside a log, a rules file or a timeline: they are data.</li></ul></section>`;
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
    const cw = t.closest('[data-cap]'); if (cw) { ST.cap = cw.dataset.cap; showPage(true); return; }
    if (t.closest('[data-dlrules]')) { const w = ST.out.rules; if (w && w.yaml) saveBlob(w.file, new Blob([w.yaml], {type: 'text/yaml'})); return; }
    if (t.closest('[data-dlpm]')) { const d = ST.out['i:' + ST.arg]; if (d && d.result) saveBlob('postmortem-' + d.number.toLowerCase() + '.md', new Blob([d.result.postmortem || ''], {type: 'text/markdown'})); return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      if (t.closest('[data-rules]')) { try { ST.out.rules = await run('rules', {}); } catch (e2) { ST.out.rules = {error: e2.message}; } showPage(true); return; }
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked done.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 3000000) { toast('That file is larger than 3 MB.', true); el.value = ''; return; }
      const txt = await f.text(), form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.fileto}]`);
      if (ta) { ta.value = txt; const ti = form.querySelector('[name=title]'); if (ti && !ti.value) ti.value = f.name; }
      el.value = '';
    }
  }
  /* 'shop: all' / '  app 1, 99.5' lines -> the tree the server reads */
  function parseTree(txt) {
    const rows = S(txt).split('\n').filter(l => l.trim()).map(l => ({ind: l.match(/^\s*/)[0].replace(/\t/g, '  ').length, t: l.trim()}));
    if (!rows.length) throw new Error('Describe the system first.');
    const node = r => {
      const g = r.t.match(/^(.+?)\s*:\s*(all|any)(?:\s+(\d+))?\s*$/i);
      if (g) return {name: g[1], [g[2].toLowerCase()]: [], ...(g[3] ? {need: Number(g[3])} : {})};
      const p = r.t.split(/\s*,\s*/); if (p.length < 2) throw new Error(`"${r.t}": give name, availability % - or name: all / name: any.`);
      return {name: p.slice(0, -1).join(', '), availability: p[p.length - 1]};
    };
    const root = node(rows[0]), stack = [[rows[0].ind, root]];
    for (const r of rows.slice(1)) {
      const n = node(r);
      while (stack.length > 1 && stack[stack.length - 1][0] >= r.ind) stack.pop();
      const parent = stack[stack.length - 1][1], list = parent.all || parent.any;
      if (!list) throw new Error(`"${parent.name}" has parts under it: write "${parent.name}: all" or ": any".`);
      list.push(n); if (n.all || n.any) stack.push([r.ind, n]);
    }
    return root;
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
      if (kind === 'slo') await go('slo', {inputs: pick(['target', 'window_days', 'good', 'total', 'elapsed_days'])});
      else if (kind === 'burn') await go('burn', {text: S(fd.get('text')), inputs: pick(['target', 'window_days'])});
      else if (kind === 'rules') await go('rules', {text: S(fd.get('text')), inputs: pick(['scrape_s'])});
      else if (kind === 'noise') await go('noise', {text: S(fd.get('text'))});
      else if (kind === 'incident') await go('incident', {text: S(fd.get('text')), inputs: pick(['tz', 'day', 'impact', 'root_cause', 'title'])});
      else if (kind === 'latency') await go('latency', {text: S(fd.get('text')), inputs: pick(['threshold_ms', 'unit', 'objective'])});
      else if (kind === 'buckets') await go('buckets', {text: S(fd.get('text')), inputs: pick(['threshold_ms', 'unit'])});
      else if (kind === 'capacity') await go('capacity', {text: S(fd.get('text')), inputs: pick(['limit', 'headroom', 'unit', 'what'])});
      else if (kind === 'queue') await go('queue', {inputs: pick(['rps', 'service_ms', 'servers'])});
      else if (kind === 'avail') await go('avail', {inputs: {tree: parseTree(fd.get('tree')), ...pick(['target'])}});
      else if (kind === 'settings') { await run('settings', pick(FIELDS_SET)); delete ST.out.rules; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['service', 'target', 'window_days', 'tz', 'work_start', 'work_end', 'weekend', 'scrape_s', 'latency_ms', 'bad_metric', 'total_metric', 'selector'];



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
    const box = $('#srFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/srdesk/chat'); ST.chat = r.id; }
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


