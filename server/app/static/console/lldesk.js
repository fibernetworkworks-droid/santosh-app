/* LOW LATENCY DESK - the Backend Systems Engineer (Low Latency)'s own section, like the finance desks (owner: "Backend Systems Engineer
   (Low Latency) same as finance desks"). A thin top bar, then the Low Latency chat (its own conversation, kind 'lowlat') beside the
   desk's pages: Today, Latency (percentiles + runs compared), Budget (a request path), Code and layout (hot path + structs), Profile,
   Host tuning, CI check, Settings. The pages call /api/lldesk/do/<part>; nothing runs on her machines. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<circle cx="12" cy="13" r="8"/><path d="M12 13l4-3M10 2h4M12 5V2"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['latency', 'Latency'], ['budget', 'Budget'], ['code', 'Code and layout'], ['profile', 'Profile'], ['tuning', 'Host tuning'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where does my p99 come from?', 'How many samples do I need for p99.9?', 'Is my benchmark lying to me?'],
    latency: ['What is coordinated omission?', 'Why is my max so far from p99.9?', 'How do I make HdrHistogram output?'],
    budget: ['Should I hedge this call?', 'Why does fan-out make the tail worse?', 'How do I split a 20 ms budget?'],
    code: ['How do I avoid false sharing?', 'Is a lock-free queue worth it here?', 'How do I stop allocating per message?'],
    profile: ['How do I record a perf profile?', 'What does a low IPC mean?', 'How do I see time spent waiting?'],
    tuning: ['Should I turn off hyper-threading?', 'isolcpus or cgroups cpusets?', 'Is busy polling worth the CPU?'],
    ci: ['How noisy are GitHub runners?', 'What tolerance should I pick?', 'How should my benchmark write its results?'],
    settings: ['Which percentile should I guard?', 'What send interval is my load test?', 'Do I need 128-byte cache lines?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'code', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.lldesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.lldesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'lowlat', name: 'Low Latency'} : null;
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
  const run = (part, a) => api('POST', '/api/lldesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/lldesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Backend Systems Engineer (Low Latency) is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="llHire">Hire the Backend Systems Engineer (Low Latency)</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#llHire').onclick = async () => { try { await api('POST', '/api/employees/lowlatency_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Low Latency</div><div class="sd-site" id="llSite"></div></div>
          <span id="llState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Low Latency chat">
          <div class="sd-chathead"><div class="t"><b>Low Latency chat</b><span>Paste samples, a profile, a struct or a hot loop - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="llFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="llPick" multiple hidden accept=".txt,.log,.json,.csv,.yml,.yaml,.xml,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Low Latency desk" id="sdTabs"></nav>
          <div id="llPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste samples or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#llPick').click()});
    $('#llPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.lldesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.lldesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/lldesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#llPage').addEventListener('click', onPageClick);
    $('#llPage').addEventListener('submit', onSubmit);
    $('#llPage').addEventListener('change', onChange);
    $('#llPage').addEventListener('input', onInput);
    $('#llPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#llState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#llSite').textContent = [s.target_us ? `p${num(s.target_q)} under ${us(s.target_us)}` : '', pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/lldesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#llPage'); if (!box) return;
    const fn = {today: pToday, latency: pLatency, budget: pBudget, code: pCode, profile: pProfile, tuning: pTuning, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="llk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const pct = (v, d = 0) => { if (v === null || v === undefined) return '—'; let t = (Number(v) * 100).toFixed(d); if (t.includes('.')) t = t.replace(/\.?0+$/, ''); return t + '%'; };
  const p3 = x => String(Number(Number(x).toPrecision(3)));
  const us = v => { if (v === null || v === undefined || v === '' || isNaN(Number(v))) return '—'; const a = Math.abs(Number(v));
    return a >= 1e6 ? p3(v / 1e6) + ' s' : a >= 1000 ? p3(v / 1000) + ' ms' : a >= 1 ? p3(v) + ' µs' : p3(v * 1000) + ' ns'; };
  const chg = v => v === null || v === undefined ? '—' : `<span class="ch ${v > 0.02 ? 'up' : v < -0.02 ? 'down' : ''}">${v > 0 ? '+' : ''}${(v * 100).toFixed(Math.abs(v) < 0.1 ? 1 : 0)}%</span>`;
  const KN = {latency: 'Latency', budget: 'Budget', code: 'Hot path', layout: 'Struct layout', profile: 'Profile', tuning: 'Host tuning'};
  const ROUTE = {latency: 'latency', budget: 'budget', code: 'code', layout: 'code', profile: 'profile', tuning: 'tuning'};
  const QS = [['50', 'p50'], ['90', 'p90'], ['99', 'p99'], ['99.9', 'p99.9'], ['99.99', 'p99.99'], ['100', 'max']];
  const UNITS = [['ns', 'nanoseconds (ns)'], ['us', 'microseconds (µs)'], ['ms', 'milliseconds (ms)'], ['s', 'seconds (s)']];
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'latency': return b.runs > 1 ? `${b.runs} runs · p99 ${b.change === null || b.change === undefined ? '—' : (b.change > 0 ? '+' : '') + Math.round(b.change * 100) + '%'} · ${({slower: 'slower', faster: 'faster', same: 'within the noise', unknown: 'no interval'})[b.verdict] || ''}` : `p50 ${us(b.p50)} · p99 ${us(b.p99)} · p99.9 ${us(b.p999)}${b.count ? ' · ' + num(b.count) + ' samples' : ''}`;
      case 'budget': return `${pl(b.stages || 0, 'stage')} · end-to-end p99 ${us(b.p99)}${b.target_ok === false ? ' · over budget' : b.target_ok ? ' · within budget' : ''}`;
      case 'code': return `${b.lang || ''} · ${num(b.lines)} lines · ${pl(b.issues || 0, 'thing')} to look at`;
      case 'layout': return `${pl(b.structs || 0, 'struct')} · ${num(b.size)} bytes${b.sharing ? ' · ' + pl(b.sharing, 'false-sharing risk') : ''}`;
      case 'profile': return `${b.kind || ''}${b.cat ? ' · most: ' + b.cat : ''}${b.top ? ' · top ' + S(b.top).slice(0, 40) : ''}`;
      case 'tuning': return `${pl(b.seen || 0, 'part')} read · ${pl(b.issues || 0, 'setting')} to change`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="llk-list">${list.map(x => `<button type="button" class="llk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="llk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="llk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="llk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area ? `<span class="mut">${esc(i.area)}${i.cost ? ' · costs ' + esc(i.cost) : ''}</span>` : ''}${i.code ? `<code class="llk-src">${esc(i.code)}</code>` : ''}${i.fix ? `<code class="llk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows) => `<label class="ins-lab wide">${esc(l)}<textarea class="in mono llk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft llk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="llk-row wide">${fileBtn('text', acc || '.txt,.log,.csv,.hgrm,.json,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card llk-sum ${ok ? 'okv' : 'badv'}"><p class="llk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="llk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const meter = (share, cls, label) => `<div class="llk-bar" role="img" aria-label="${esc(label || pct(share))}"><i class="${cls || (share > 1 ? 'bad' : share > 0.85 ? 'warn' : '')}" style="width:${Math.min(100, Math.max(0, (share || 0) * 100)).toFixed(1)}%"></i></div>`;
  const seg = (key, opts, cur) => `<div class="llk-seg" role="tablist">${opts.map(([k2, t]) => `<button type="button" data-${key}="${k2}" aria-pressed="${k2 === cur}">${esc(t)}</button>`).join('')}</div>`;

  /* charts */
  function histo(h, marks, label) {   /* h: [{lo, hi, n}] on a log scale; marks: [[label, value, cls]] */
    if (!(h || []).length) return '';
    const W = 760, H = 220, L = 40, R = 14, T = 26, B = 30;
    const lo = Math.log(h[0].lo), hi = Math.log(h[h.length - 1].hi), mx = Math.max(1, ...h.map(b => b.n));
    const x = v => L + (Math.log(Math.max(v, 1e-9)) - lo) / ((hi - lo) || 1) * (W - L - R), y = n => T + (1 - Math.sqrt(n / mx)) * (H - T - B);
    const bars = h.map(b => { const x0 = x(b.lo), x1 = x(b.hi); return b.n ? `<rect class="b" x="${x0.toFixed(1)}" y="${y(b.n).toFixed(1)}" width="${Math.max(1, x1 - x0 - 1).toFixed(1)}" height="${(H - B - y(b.n)).toFixed(1)}"><title>${esc(us(b.lo))} - ${esc(us(b.hi))}: ${esc(num(b.n))}</title></rect>` : ''; }).join('');
    const ticks = [];
    for (let i = 0; i <= 5; i++) { const v = Math.exp(lo + (hi - lo) * i / 5); ticks.push(`<text x="${x(v).toFixed(1)}" y="${H - 10}" text-anchor="${i === 0 ? 'start' : i === 5 ? 'end' : 'middle'}">${esc(us(v))}</text>`); }
    let row = 0;
    const mk = (marks || []).filter(m => m[1] !== null && m[1] !== undefined && m[1] >= Math.exp(lo) * 0.999 && m[1] <= Math.exp(hi) * 1.001).map(([t, v, cls]) => { const xx = x(v); row = (row + 1) % 2;
      return `<line class="q ${cls || ''}" x1="${xx.toFixed(1)}" x2="${xx.toFixed(1)}" y1="${T - 4}" y2="${H - B}"/><text class="ql" x="${xx.toFixed(1)}" y="${row ? 12 : 22}" text-anchor="middle">${esc(t)}</text>`; }).join('');
    return `<div class="llk-hist"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}"><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${bars}${mk}${ticks.join('')}</svg></div>`;
  }
  function curve(runs, label) {   /* percentile on the "nines" axis against latency (log) - the usual HdrHistogram plot */
    const qs = [50, 90, 99, 99.9, 99.99], X = q => -Math.log10(1 - q / 100);
    const pts = runs.map(r => qs.map(q => [q, r.q[String(q)]]).filter(p => p[1] !== null && p[1] !== undefined && p[1] > 0));
    const all = pts.flat().map(p => p[1]); if (all.length < 2) return '';
    const W = 760, H = 240, L = 64, R = 18, T = 14, B = 30;
    let lo = Math.log(Math.min(...all)), hi = Math.log(Math.max(...all)); if (hi - lo < 0.01) { hi += 0.5; lo -= 0.5; }
    const x = q => L + (X(q) - X(50)) / (X(99.99) - X(50)) * (W - L - R), y = v => T + (hi - Math.log(v)) / (hi - lo) * (H - T - B);
    const grid = [0, 0.5, 1].map(f => { const v = Math.exp(lo + (hi - lo) * f); return `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(us(v))}</text>`; }).join('');
    const xl = qs.map(q => `<text class="tx" x="${x(q).toFixed(1)}" y="${H - 8}" text-anchor="middle">p${q}</text>`).join('');
    const lines = pts.map((p, i) => p.length > 1 ? `<path class="r${i}" d="${p.map((pp, j) => `${j ? 'L' : 'M'}${x(pp[0]).toFixed(1)},${y(pp[1]).toFixed(1)}`).join('')}"/>` + p.map(pp => `<circle class="pt" cx="${x(pp[0]).toFixed(1)}" cy="${y(pp[1]).toFixed(1)}" r="3"><title>${esc(runs[i].name)} p${pp[0]}: ${esc(us(pp[1]))}</title></circle>`).join('') : '').join('');
    return `<div class="cs-chart llk-curve"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${grid}${lines}${xl}</svg></div>
      <div class="llk-legend">${runs.map((r, i) => `<span><i class="r${i}"></i>${esc(r.name)}</span>`).join('')}</div>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, lt = k.latency, bd = k.budget, tu = k.tuning, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tgt = s.target_us ? `Your target: p${num(s.target_q)} under ${us(s.target_us)}.` : 'No latency target set yet.';
    const tiles = [
      tile('Latest p99', lt ? esc(us(lt.p99)) : '—', lt ? (lt.runs > 1 ? `${lt.runs} runs compared · ${lt.number}` : `p50 ${us(lt.p50)} · p99.9 ${us(lt.p999)} · ${lt.number}`) : 'paste samples to work it out', lt && (lt.target_ok === false || lt.verdict === 'slower')),
      tile('Request path', bd ? esc(us(bd.p99)) : '—', bd ? `end-to-end p99 over ${pl(bd.stages, 'stage')} · ${bd.number}` : 'budget a request path', bd && bd.target_ok === false),
      tile('Code and layout', esc(num((c.code || 0) + (c.layout || 0))), 'hot paths and structs read'),
      tile('Host tuning', tu ? esc(num(tu.issues)) : '—', tu ? `settings that add latency · ${tu.number}` : 'paste the host outputs', tu && tu.issues > 0)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(tgt)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="llk-starts">
        <button type="button" class="llk-start" data-go="latency"><b>Read a latency run</b><span>Samples, HdrHistogram or wrk2 output: percentiles you can trust, the tail, two runs compared beyond the noise</span></button>
        <button type="button" class="llk-start" data-go="budget"><b>Budget a request</b><span>The stages a request goes through: which one makes the tail, fan-outs and hedged calls</span></button>
        <button type="button" class="llk-start" data-go="code"><b>Read the hot path</b><span>Allocation, locks and syscalls in loops; struct padding and false sharing</span></button>
        <button type="button" class="llk-start" data-go="tuning"><b>Tune the host</b><span>CPU isolation, C-states, the governor, THP, NIC coalescing, busy polling</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- latency */
  function pLatency() {
    if (ST.arg) return one(ST.arg, 'latency', pLat);
    const s = st_();
    return `<div><h1 class="sd-h">Latency</h1><p class="lead">Percentiles from your samples, how far each one can be trusted, and whether a change made the tail slower - beyond the noise, not by eye.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Work out a run, or compare runs</h2><form data-form="latency" class="llk-grid">
        ${area('text', 'One latency per line (or separated by commas), HdrHistogram / wrk2 output, or lines like "p99: 1.2 ms". To compare, put each run under a heading: ## before, ## after (up to 6)', '## before\n12.1\n11.8\n13.4\n...\n## after\n12.6\n12.2\n19.9\n...', 10)}
        ${sel('unit', 'Unit of plain numbers', UNITS, s.unit || 'us')}${fld('target_us', 'Target (µs, 0 = none)', s.target_us || 0, 'type="number" min="0" step="any"')}
        ${fld('target_q', 'Percentile of the target', s.target_q || 99, 'type="number" min="50" max="99.999" step="any"')}${fld('interval_us', 'Fixed send interval (µs, 0 = none)', s.interval_us || 0, 'type="number" min="0" step="any"', 'for coordinated omission')}
        ${subRow('Work it out')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('latency'))}</section>`;
  }
  const relTag = v => v === 'ok' ? '' : v === 'few' ? 'few' : v === 'none' ? 'few' : '';
  function pLat(d) {
    const r = d.result || {}, runs = r.runs || [], r0 = runs[0] || {};
    const tq = (r.target || {}).q, tus = (r.target || {}).us;
    const marks = [['p50', r0.q && r0.q['50']], ['p99', r0.q && r0.q['99']], ['p99.9', r0.q && r0.q['99.9']]];
    if (tus) marks.push([`target p${num(tq)}`, tus, 'tgt']);
    const table = `<div class="iv-tw"><table class="tb llk-pq"><thead><tr><th>Run</th><th class="r">Samples</th>${QS.map(([, l]) => `<th class="r">${esc(l)}</th>`).join('')}</tr></thead><tbody>
      ${runs.map(x => `<tr><td><b>${esc(x.name)}</b><div class="mut" style="font-size:12px">${esc(x.tool)}</div></td><td class="r">${esc(x.count ? num(x.count) : '—')}</td>${QS.map(([k2]) => `<td class="r ${relTag((x.reliable || {})[k2])}">${esc(us((x.q || {})[k2]))}</td>`).join('')}</tr>`).join('')}
      ${r.corrected ? `<tr><td><b>${esc(r0.name)}, corrected</b><div class="mut" style="font-size:12px">send interval ${esc(us(r.corrected.interval))} · ${esc(num(r.corrected.added))} added</div></td><td class="r">—</td>${QS.map(([k2]) => `<td class="r">${esc(us((r.corrected.q || {})[k2]))}</td>`).join('')}</tr>` : ''}</tbody></table></div>
      ${runs.some(x => Object.values(x.reliable || {}).some(v => v === 'few' || v === 'none')) ? '<p class="cs-note">* fewer than 10 samples beyond that percentile - it is close to the maximum, not a percentile to compare.</p>' : ''}`;
    const cmp = (r.compare || []).length ? `<section class="card"><h2 class="md-h2">Compared with ${esc(r.compare[0].base)}</h2><div class="iv-tw"><table class="tb llk-pq"><thead><tr><th>Run</th>${QS.slice(0, 5).map(([, l]) => `<th class="r">${esc(l)}</th>`).join('')}<th>Beyond the noise?</th></tr></thead><tbody>
      ${r.compare.map(c => `<tr><td><b>${esc(c.name)}</b></td>${QS.slice(0, 5).map(([k2]) => `<td class="r">${chg(((c.q || {})[k2] || {}).change)}</td>`).join('')}<td>${c.ci99 ? `${tag({slower: 'Slower', faster: 'Faster', same: 'Within the noise'}[c.verdict] || '—', {slower: 'bad', faster: 'ok', same: ''}[c.verdict])} <span class="mut" style="font-size:12.5px">p99 interval ${esc(pct(c.ci99[0]))} to ${esc(pct(c.ci99[1]))}</span>` : '<span class="mut">no raw samples - no interval</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : '';
    return `${head(d, 'latency')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">Percentiles</h2>${table}</section>
      ${runs.length > 1 || !r0.hist ? `<section class="card"><h2 class="md-h2">The tail</h2>${curve(runs, 'Latency by percentile')}<p class="cs-note">Each line is a run: further right is rarer. A line that bends up sharply has a heavy tail.</p></section>` : ''}
      ${cmp}
      ${r0.hist ? `<section class="card"><h2 class="md-h2">How the samples spread</h2>${histo(r0.hist, marks, 'Latency histogram')}${(r0.modes || []).length > 1 ? `<p class="cs-note">${esc(pl(r0.modes.length, 'group'))} of samples, around ${esc(r0.modes.map(us).join(', '))}.</p>` : ''}
        <div class="ar-facts" style="margin-top:12px">${[['Mean', us(r0.mean)], ['Standard deviation', us(r0.stdev)], ['Fastest', us(r0.min)], ['Slowest', us(r0.max)]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card llk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- budget */
  function pBudget() {
    if (ST.arg) return one(ST.arg, 'budget', pBud);
    const s = st_();
    return `<div><h1 class="sd-h">Latency budget</h1><p class="lead">The stages one request goes through, each with its median and p99. Hoola samples the whole path and says where the tail really comes from.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">The request path</h2><form data-form="budget" class="llk-grid">
        ${area('text', 'One line per stage. stage, name, p50, p99[, times in a row] - fanout, name, backends, p50, p99 (waits for all) - hedge, name, p50, p99, send the second after - target, p99, 20ms', 'stage, gateway, 0.3ms, 1.2ms\nstage, auth, 0.5ms, 4ms\nfanout, search shards, 20, 2ms, 15ms\nstage, database, 1ms, 12ms, 2\ntarget, p99, 40ms', 9)}
        ${sel('unit', 'Unit of plain numbers', UNITS, s.budget_unit || 'ms')}${subRow('Work it out', '.txt,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('budget'))}</section>`;
  }
  function pBud(d) {
    const r = d.result || {}, st = r.stages || [], t = r.target || {}, q = r.q || {};
    const scale = Math.max(...st.map(x => x.sim99), 1e-9), best = st.reduce((a, b) => (b.gain > (a ? a.gain : -1) ? b : a), null);
    const rows = st.map(x => `<div class="llk-st${best && x === best && x.gain > 0 ? ' top' : ''}"><div class="n"><b>${esc(x.name)}</b><span class="mut">${esc({stage: x.times > 1 ? x.times + ' times in a row' : 'one call', fanout: `waits for ${x.n} backends`, hedge: `hedged after ${us(x.after)}`}[x.type])}</span></div>
        <div class="rng" title="median to p99"><i style="left:${(x.sim50 / scale * 100).toFixed(1)}%;width:${Math.max(0.5, (x.sim99 - x.sim50) / scale * 100).toFixed(1)}%"></i><b style="left:${(x.sim50 / scale * 100).toFixed(1)}%"></b></div>
        <em><span class="mut" style="font-size:11.5px">p50 </span>${esc(us(x.sim50))}</em><em><span class="mut" style="font-size:11.5px">p99 </span>${esc(us(x.sim99))}</em></div>`).join('');
    const wi = (r.what_if || []).length ? `<section class="card"><h2 class="md-h2">What if</h2><div class="iv-tw"><table class="tb llk-pq in-cards"><thead><tr><th>Change</th><th class="r">End-to-end p${esc(num(t.q))}</th><th class="r">Change</th><th>Cost</th></tr></thead><tbody>${r.what_if.map(w => `<tr><td>${esc(w.what)}</td><td class="r">${esc(us(w.q))}</td><td class="r">${chg(w.change)}</td><td class="mut">${w.load ? 'about ' + esc(pct(w.load)) + ' more calls to it' : 'fewer backends per request'}</td></tr>`).join('')}</tbody></table></div></section>` : '';
    return `${head(d, 'budget')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('p50 end to end', esc(us(q['50'])), 'half of requests are faster')}${tile('p99 end to end', esc(us(q['99'])), t.us ? `budget ${us(t.us)}` : 'no budget set', t.ok === false)}${tile('p99.9 end to end', esc(us(q['99.9'])), '1 in 1,000 is slower')}${tile('Adding up the p99s', esc(us(r.sum_p99)), 'an upper bound that almost never happens')}</div></section>
      <section class="card"><h2 class="md-h2">Where the median goes</h2><div class="llk-stack" role="img" aria-label="Share of the median by stage">${st.map(x => `<i style="width:${(x.share50 * 100).toFixed(2)}%" title="${esc(x.name)} ${esc(pct(x.share50))}"></i>`).join('')}</div>
        <div class="llk-legend">${st.map(x => `<span>${esc(x.name)} ${esc(pct(x.share50))}</span>`).join('')}</div></section>
      <section class="card"><h2 class="md-h2">Each stage, median to p99</h2><div class="llk-stages">${rows}</div><p class="cs-note">The stage in red is where taking out the tail saves the most at p${esc(num(t.q))}.</p></section>
      ${wi}
      ${r.hist && r.hist.length ? `<section class="card"><h2 class="md-h2">End-to-end, as sampled</h2>${histo(r.hist, [['p50', q['50']], ['p99', q['99']], ...(t.us ? [['budget', t.us, 'tgt']] : [])], 'End-to-end latency')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card llk-raw"><summary>What you gave</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- code + layout */
  function pCode() {
    if (ST.arg) return one(ST.arg, 'code', d => d.kind === 'layout' ? pLayout(d) : pHot(d));
    const s = st_(), w = ST.sub === 'layout' ? 'layout' : 'code';
    const forms = {
      code: `<form data-form="code" class="llk-grid">${area('text', 'The code that runs per request or per message (C / C++, Rust, Go or Java)', 'for (auto& m : batch) {\n  auto* o = new Order(m);\n  std::lock_guard<std::mutex> g(book_mu);\n  book.add(o);\n  LOG_INFO("added {}", o->id);\n}', 10)}
        ${sel('lang', 'Language', [['', 'Find it from the code'], ['cpp', 'C / C++'], ['rust', 'Rust'], ['go', 'Go'], ['java', 'Java']], '')}${subRow('Read it', '.c,.cc,.cpp,.h,.hpp,.rs,.go,.java,text/*')}</form>`,
      layout: `<form data-form="layout" class="llk-grid">${area('text', 'C / C++ structs or classes (with their fields), or Rust structs - #[repr(C)] for the declared order. Define a type before the struct that uses it.', 'struct Order {\n  char side;\n  double price;\n  int qty;\n  std::atomic<uint64_t> seq;\n};\nstruct Ring {\n  std::atomic<size_t> head;\n  std::atomic<size_t> tail;\n};', 10)}
        ${sel('abi', 'ABI', [['lp64', 'Linux / macOS, 64-bit'], ['llp64', 'Windows x64']], s.abi || 'lp64')}${sel('line', 'Cache line', [[64, '64 bytes'], [128, '128 bytes (Apple M-series)'], [32, '32 bytes']], s.line || 64)}${subRow('Lay it out', '.c,.cc,.cpp,.h,.hpp,.rs,text/*')}</form>`};
    return `<div><h1 class="sd-h">Code and layout</h1><p class="lead">What on the hot path costs latency - and how your structs sit in memory: padding, cache lines and data two threads fight over.</p></div>${ro()}
      ${CAN() ? `<section class="card">${seg('sub', [['code', 'Hot-path code'], ['layout', 'Struct layout']], w)}<div style="margin-top:14px">${forms[w]}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('code', 'layout'))}</section>`;
  }
  function pHot(d) {
    const r = d.result || {}, f = r.findings || [];
    const groups = {}; f.forEach(x => { (groups[x.why] = groups[x.why] || []).push(x); });
    return `${head(d, 'code')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Language', esc(r.lang_name), num(r.lines) + ' lines')}${tile('Loops', esc(num(r.loops)), 'found from the braces')}${tile('To look at', esc(num((r.counts || {}).bad + (r.counts || {}).warn)), 'allocation, locks, logging, sleeps', (r.counts || {}).bad)}${tile('Notes', esc(num((r.counts || {}).info)), 'smaller costs')}</div></section>
      <section class="card"><h2 class="md-h2">What it found</h2>${Object.keys(groups).length ? Object.entries(groups).map(([why, xs]) => `<div class="llk-issue"><span>${tag(SV[xs[0].sev][0], SV[xs[0].sev][1])}</span><div><p class="t">${esc(cap(why))}.</p>
        ${xs.slice(0, 6).map(x => `<code class="llk-src"><span class="llk-ln">${esc(x.line)}${x.loop ? ' loop' : ''}</span>  ${esc(x.code)}</code>`).join('')}${xs.length > 6 ? `<span class="mut">and ${esc(num(xs.length - 6))} more</span>` : ''}<code class="llk-code">${esc(xs[0].fix)}</code></div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing these checks look for.</span></div>'}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card llk-raw"><summary>The code you pasted</summary>${pre(d.text, 'code')}</details>`;
  }
  function memMap(s, line) {
    const segs = []; let at = 0;
    (s.rows || []).forEach(f => { if (f.offset > at) segs.push({o: at, n: f.offset - at, pad: true}); segs.push({o: f.offset, n: Math.max(1, f.size), name: f.name, at: f.atomic}); at = Math.max(at, f.offset + f.size); });
    if (s.size > at) segs.push({o: at, n: s.size - at, pad: true});
    const lines = Math.max(1, Math.ceil(s.size / line)), show = Math.min(lines, 8), out = [];
    for (let L = 0; L < show; L++) {
      const a = L * line, b = a + line, cells = [];
      segs.forEach(g => { const x0 = Math.max(a, g.o), x1 = Math.min(b, g.o + g.n); if (x1 > x0) cells.push({...g, w: x1 - x0}); });
      const used = cells.reduce((q2, c2) => q2 + c2.w, 0);
      if (used < line && b > s.size) cells.push({w: line - used, free: true});
      out.push(`<div class="llk-line"><span title="bytes ${a}-${b - 1}">line ${L}</span><div class="llk-cells">${cells.map(c2 => `<i class="${c2.pad ? 'pad' : c2.free ? 'free' : c2.at ? 'at' : ''}" style="flex:${c2.w} 1 0" title="${esc(c2.pad ? c2.w + ' bytes of padding' : c2.free ? 'past the end' : c2.name + ' · ' + c2.w + ' bytes')}">${c2.pad || c2.free ? '' : esc(c2.name)}</i>`).join('')}</div></div>`);
    }
    return `<div class="llk-mem">${out.join('')}</div>${lines > show ? `<p class="cs-note">Showing ${show} of ${lines} cache lines.</p>` : ''}`;
  }
  function pLayout(d) {
    const r = d.result || {}, line = r.line || 64;
    return `${head(d, 'code')}${verdict(r, isOk(r))}
      ${(r.structs || []).map(s => `<section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">${esc(s.name)}</h2><span class="mut" style="font-size:13px">${esc(s.lang)} · ${esc(num(s.size))} bytes · align ${esc(s.align)} · ${esc(num(s.padding))} bytes padding${s.packed ? ' · packed' : ''}</span></div>
        ${memMap(s, line)}<div class="llk-key"><span><i></i>field</span><span><i class="at"></i>atomic / volatile</span><span><i class="pad"></i>padding</span></div>
        <div class="iv-tw" style="margin-top:12px"><table class="tb llk-pq in-cards"><thead><tr><th>Field</th><th>Type</th><th class="r">Offset</th><th class="r">Size</th><th class="r">Padding before</th><th class="r">Cache line</th></tr></thead><tbody>${s.rows.map(f => `<tr><td><b>${esc(f.name)}</b>${f.atomic ? ' ' + tag('atomic', 'warn') : ''}${f.crosses ? ' ' + tag('crosses a line', 'bad') : ''}</td><td><code>${esc(f.type)}</code>${f.bits ? ` <span class="mut">${esc(f.bits)} bits</span>` : ''}</td><td class="r">${esc(f.offset)}</td><td class="r">${esc(f.size)}</td><td class="r">${f.pad_before ? `<span class="cs-neg">${esc(f.pad_before)}</span>` : '0'}</td><td class="r">${esc(f.lines[0] === f.lines[1] ? f.lines[0] : f.lines[0] + '-' + f.lines[1])}</td></tr>`).join('')}</tbody></table></div>
        ${s.best && s.best.size < s.size ? `<p class="cs-note">In this order it takes ${esc(num(s.best.size))} bytes instead of ${esc(num(s.size))}: <code>${esc(s.best.order.join(', '))}</code></p>` : ''}
        ${(s.issues || []).filter(i => i.sev !== 'info' || /share|cross/.test(i.text)).length ? issueRows(s.issues.filter(i => i.sev !== 'info' || /share|cross/.test(i.text))) : ''}</section>`).join('')}
      <section class="card"><h2 class="md-h2">All findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card llk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- profile */
  function pProfile() {
    if (ST.arg) return one(ST.arg, 'profile', pProf);
    return `<div><h1 class="sd-h">Profile</h1><p class="lead">Where the time goes, grouped into what costs latency: allocation and GC, locks, the kernel, page faults, copying, the scheduler.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a profile</h2><form data-form="profile" class="llk-grid">
        ${area('text', 'perf report --stdio (or --no-children), folded stacks (perf script | stackcollapse-perf.pl, or async-profiler / pprof collapsed output), or perf stat -e cycles,instructions,cache-references,cache-misses,context-switches,cpu-migrations,page-faults', '# Children      Self  Command  Shared Object      Symbol\n    45.00%     2.00%  srv      srv                [.] handle\n    30.00%    18.00%  srv      libc.so.6          [.] malloc', 10)}
        ${subRow('Read it', '.txt,.folded,.collapsed,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('profile'))}</section>`;
  }
  function pProf(d) {
    const r = d.result || {}, st = r.stat || {}, cats = r.cats || [];
    const kpis = [];
    if (st.ipc !== undefined) kpis.push(tile('Instructions per cycle', esc(st.ipc.toFixed(2)), st.ipc < 1 ? 'mostly waiting' : 'busy', st.ipc < 1));
    if (st.cache_miss !== undefined) kpis.push(tile('Cache misses', esc(pct(st.cache_miss, 1)), 'of last-level references', st.cache_miss > 0.1));
    if (st.context_switches !== undefined) kpis.push(tile('Context switches', esc(num(st.context_switches)), st.context_switches_per_s ? num(Math.round(st.context_switches_per_s)) + ' a second' : '', st.context_switches_per_s > 1000));
    if (st.cpu_migrations !== undefined) kpis.push(tile('CPU migrations', esc(num(st.cpu_migrations)), 'thread moved between CPUs', st.cpu_migrations > 0));
    if (st.page_faults !== undefined) kpis.push(tile('Page faults', esc(num(st.page_faults)), st.page_faults_per_s ? num(Math.round(st.page_faults_per_s)) + ' a second' : ''));
    return `${head(d, 'profile')}${verdict(r, isOk(r))}
      ${kpis.length ? `<section class="cs-hero"><div class="top">${kpis.join('')}</div></section>` : ''}
      ${cats.length ? `<section class="card"><h2 class="md-h2">Where the time goes</h2>${bars(cats.map(c2 => [c2.label, c2.share, 'llk-b']), v => v.toFixed(1) + '%', 'Time by kind')}<p class="cs-note">Self time by what the function is; the rest is your own code and libraries not in these groups.</p></section>` : ''}
      ${(r.top || []).length ? `<section class="card"><h2 class="md-h2">Top functions</h2><div class="iv-tw"><table class="tb llk-pq in-cards"><thead><tr><th>Function</th><th class="r">Self</th><th class="r">Total</th><th>Kind</th></tr></thead><tbody>${r.top.slice(0, 20).map(f => `<tr><td><code>${esc(f.sym)}</code>${f.dso ? `<div class="mut" style="font-size:12px">${esc(f.dso)}</div>` : ''}</td><td class="r">${esc(Number(f.self).toFixed(1))}%</td><td class="r">${f.total === null || f.total === undefined ? '—' : esc(Number(f.total).toFixed(1)) + '%'}</td><td class="mut">${esc((cats.find(c2 => c2.key === f.cat) || {}).label || '')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card llk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- tuning */
  function pTuning() {
    if (ST.arg) return one(ST.arg, 'tuning', pTune);
    return `<div><h1 class="sd-h">Host tuning</h1><p class="lead">The Linux settings that add latency - CPU isolation, power states, the frequency governor, huge pages, the network card, busy polling, the clock - each with what it costs and the line to change.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a host</h2><form data-form="tuning" class="llk-grid">
        ${area('text', 'Paste what these print (any of them): cat /proc/cmdline; sysctl -a; lscpu; grep . /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; cat /sys/kernel/mm/transparent_hugepage/enabled; ethtool -c eth0; ethtool -g eth0; systemctl status irqbalance; tuned-adm active; cat /sys/devices/system/clocksource/clocksource0/current_clocksource', 'BOOT_IMAGE=/vmlinuz-6.8 root=/dev/nvme0n1p2 ro quiet\nvm.swappiness = 60\nkernel.numa_balancing = 1\nalways [madvise] never\n/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor:powersave\nAdaptive RX: on  TX: on', 10)}
        ${subRow('Read it', '.txt,.log,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('tuning'))}</section>`;
  }
  function pTune(d) {
    const r = d.result || {}, iss = r.issues || [];
    const areas = [...new Set(iss.map(i => i.area))];
    return `${head(d, 'tuning')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">What was read</h2><div class="llk-chips">${(r.seen || []).map(x => `<span>${esc(x)}</span>`).join('')}</div>
        ${(r.missing || []).length ? `<p class="cs-note">Not seen: ${esc(r.missing.join('; '))}.</p>` : ''}${(r.isolated || []).length ? `<p class="cs-note">Isolated CPUs: ${esc(r.isolated.join(', '))}.</p>` : ''}</section>
      ${areas.map(a => `<section class="card"><h2 class="md-h2">${esc(a)}</h2>${issueRows(iss.filter(i => i.area === a).map(i => ({...i, area: i.cost ? 'Trade-off' : ''})))}</section>`).join('')}
      <p class="cs-note">${esc(r.note)}</p>
      <details class="card llk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs your benchmark on the pull request's base and head on the same runner, in turns, and fails the pull request when p${esc(num(s.target_q || 99))} gets slower than your tolerance.</p></div>
      <section class="card"><h2 class="md-h2">What it runs</h2><div class="ar-facts">${[['Benchmark', s.bench_cmd || 'not set'], ['Build', s.build_cmd || 'none'], ['Results file', `${s.out_file} (one latency per line, ${s.unit})`], ['Guards', `p${num(s.target_q)} · fails above +${num(s.tolerance)}%`], ['Runs', `${s.runs} on each side, in turns`], ['Runner', s.runner + (s.pin_cpu ? ' · pinned to CPU 1' : '')]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dlci="1">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your latency target, the units your tools print, how structs are laid out, and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="llk-grid">
        <h2 class="md-h2 wide" style="margin:0">Latency</h2>
        ${sel('unit', 'Unit of plain sample numbers', UNITS, s.unit)}${sel('budget_unit', 'Unit of plain budget numbers', UNITS, s.budget_unit)}
        ${fld('target_q', 'Percentile of your target', s.target_q, 'type="number" min="50" max="99.999" step="any"')}${fld('target_us', 'Target (µs, 0 = none)', s.target_us, 'type="number" min="0" step="any"')}
        ${fld('interval_us', 'Fixed send interval of your load test (µs, 0 = none)', s.interval_us, 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Structs</h2>
        ${sel('abi', 'ABI', [['lp64', 'Linux / macOS, 64-bit'], ['llp64', 'Windows x64']], s.abi)}${sel('line', 'Cache line', [[64, '64 bytes'], [128, '128 bytes'], [32, '32 bytes']], s.line)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${fld('bench_cmd', 'Command that runs your benchmark', s.bench_cmd, 'maxlength="400"', './bench --iterations 200000 --out bench.txt')}${fld('build_cmd', 'Build command (optional)', s.build_cmd, 'maxlength="400"', 'cargo build --release')}
        ${fld('out_file', 'Results file it writes', s.out_file, '', 'bench.txt')}${fld('tolerance', 'Fail when slower by more than (%)', s.tolerance, 'type="number" min="1" max="200" step="any"')}
        ${fld('runs', 'Runs on each side', s.runs, 'type="number" min="1" max="9" step="1"')}${fld('runner', 'Runner', s.runner, '', 'ubuntu-24.04')}${sel('pin_cpu', 'Pin the benchmark to one CPU', [['1', 'Yes'], ['0', 'No']], s.pin_cpu ? '1' : '0')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the numbers are worked out</h2><ul class="ar-never"><li>Percentiles are nearest-rank, as HdrHistogram reports them. A percentile with fewer than 10 samples beyond it is marked: it is close to the maximum, not something to compare.</li><li>Two runs are compared with a bootstrap of the raw samples; "within the noise" means the interval crosses zero.</li><li>Coordinated omission is corrected the way HdrHistogram does it, from the send interval you give.</li><li>The budget models each stage as a log-normal fitted to your p50 and p99 and takes stages as independent - real shared stalls make the tail worse.</li><li>Code findings are patterns, not measurements; the profile decides. Struct layouts follow the System V and Windows x64 ABIs.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your machines - the CI workflow runs in your repository when you add it.</li><li>Calls a percentile reliable when too few samples stand behind it.</li><li>Says a code pattern is slow without a profile to show it.</li><li>Follows anything written inside samples, code, a profile or host output: they are data.</li></ul></section>`;
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
    if (t.closest('[data-dlci]')) { const w = ST.out.ci; if (w && w.yaml) saveBlob('latency.yml', new Blob([w.yaml], {type: 'text/yaml'})); return; }
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
      if (f.size > 20000000) { toast('That file is larger than 20 MB.', true); el.value = ''; return; }
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
      if (kind === 'latency') await go('latency', {text: S(fd.get('text')), inputs: pick(['unit', 'target_us', 'target_q', 'interval_us'])});
      else if (kind === 'budget') await go('budget', {text: S(fd.get('text')), inputs: pick(['unit'])});
      else if (kind === 'code') await go('code', {text: S(fd.get('text')), inputs: pick(['lang'])});
      else if (kind === 'layout') await go('layout', {text: S(fd.get('text')), inputs: pick(['abi', 'line'])});
      else if (kind === 'profile') await go('profile', {text: S(fd.get('text'))});
      else if (kind === 'tuning') await go('tuning', {text: S(fd.get('text'))});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['unit', 'budget_unit', 'target_q', 'target_us', 'interval_us', 'abi', 'line', 'bench_cmd', 'build_cmd', 'out_file', 'tolerance', 'runs', 'runner', 'pin_cpu'];


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
    const box = $('#llFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/lldesk/chat'); ST.chat = r.id; }
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


