/* QA DESK - the App tester (QA)'s own section, like the finance desks (owner: "App tester (QA) same as finance desks"). A thin top
   bar, then the QA chat (its own conversation, kind 'qa') beside the desk's pages: Today, What I test, Test cases, Runs, Bugs, Release,
   Settings. The pages call /api/qadesk/do/<part>, which runs the QA engine. Hoola tests only what is hers, never pays, never uses a
   real password and files nothing without her tap. Routes: #/<page>, #/runs/<run id>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M9 3h6M10 3v5L5 18a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3L14 8V3"/><path d="M7.5 14h9"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['targets', 'What I test'], ['cases', 'Test cases'], ['runs', 'Runs'], ['bugs', 'Bugs'], ['release', 'Release'],
    ['settings', 'Settings']];
  const STARTERS = {
    today: ['What is broken right now?', 'Is my site ready to release?', 'Summarise this week\'s testing'],
    targets: ['How do I prove my site is mine?', 'What does Hoola look for on a site?', 'Add my website to test'],
    cases: ['Write cases for my booking form', 'Which cases matter most?', 'Make this case automatic'],
    runs: ['Why did this run fail?', 'Run the quick check now', 'What changed since the last run?'],
    bugs: ['Explain this bug for my developer', 'Which bug should be fixed first?', 'Draft a GitHub issue'],
    release: ['Can I release today?', 'What blocks the release?', 'What is the accessibility law for me?'],
    settings: ['What testing rules should I set?', 'Which accessibility law applies to me?', 'When should the daily tests run?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', tid: '', cf: '', bf: 'open', repo: '', shots: {}, d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.qadesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.qadesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'qa', name: ((K().settings || {}).team_name) || 'Your testing'} : null;
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
  const run = (part, a) => api('POST', '/api/qadesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/qadesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your App tester (QA) is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="qaHire">Hire the App tester</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#qaHire').onclick = async () => { try { await api('POST', '/api/employees/qa/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">App tester (QA)</div><div class="sd-site" id="qaSite"></div></div>
          <span id="qaState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="QA chat">
          <div class="sd-chathead"><div class="t"><b>QA chat</b><span>Ask about a bug, a test or a release - or drop a spec or requirements file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="qaFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="qaPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.md,.csv,.xlsx,.doc,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="QA desk" id="sdTabs"></nav>
          <div id="qaPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola tests only what is yours. It never pays, never uses a real password and files nothing without your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a bug, a test or a release…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#qaPick').click()});
    $('#qaPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.qadesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.qadesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/qadesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#qaPage').addEventListener('click', onPageClick);
    $('#qaPage').addEventListener('submit', onSubmit);
    $('#qaPage').addEventListener('change', onChange);
    $('#qaPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#qaState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : (k.running || []).length ? ['v', 'Running tests'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#qaSite').textContent = [(k.settings || {}).team_name, pl((k.targets || []).length, 'target'), (k.settings || {}).country].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), oc = k.open_counts || {};
    const n = {bugs: ((oc.critical || 0) + (oc.major || 0)) || '', targets: (k.targets || []).filter(t => !t.verified).length || '',
      release: Object.values(k.readiness || {}).filter(r => r.verdict === 'not_ready').length || '', runs: (k.running || []).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/qadesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#qaPage'); if (!box) return;
    const fn = {today: pToday, targets: pTargets, cases: pCases, runs: pRuns, bugs: pBugs, release: pRelease, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    box.innerHTML = html;
    if (kept) retype(box, kept);
    starters();
    loadShots();
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
  const pct = v => (v === null || v === undefined) ? '—' : `${num(Math.round(Number(v) * 100) / 100)}%`;
  const SEV = {critical: ['Critical', 'bad'], major: ['Major', 'bad'], minor: ['Minor', 'warn'], trivial: ['Trivial', '']};
  const BST = {open: ['Open', 'bad'], reopened: ['Reopened', 'bad'], fixed: ['Fixed - check pending', 'warn'], verified: ['Verified', 'ok'], wont_fix: ['Will not fix', ''], duplicate: ['Duplicate', ''], closed: ['Closed', '']};
  const RES = {pass: ['Pass', 'ok'], fail: ['Fail', 'bad'], blocked: ['Blocked', 'warn'], manual: ['By hand', 'v'], error: ['Error', 'bad'], not_run: ['Not run', '']};
  const VER = {ready: ['Ready', 'ok'], risky: ['Risky', 'warn'], not_ready: ['Not ready', 'bad'], unknown: ['—', '']};
  const KINDL = {site: 'Hoola website', app: 'Hoola app', url: 'Your website', apk: 'Android preview'};
  const T_ = (m, k) => { const [l, c] = m[k] || [cap(S(k).replace(/_/g, ' ')), '']; return tag(l, c); };
  const tgt = () => { const ts = K().targets || []; return ts.find(t => t.id === ST.tid) || ts[0] || null; };
  const tgtPick = (form) => { const ts = K().targets || []; if (ts.length < 2) return ''; const t = tgt();
    return `<select class="in sm" data-tpick="1" aria-label="What to test" style="max-width:280px">${ts.map(x => `<option value="${esc(x.id)}"${t && x.id === t.id ? ' selected' : ''}>${esc(x.number)} · ${esc(x.name)}</option>`).join('')}</select>`; };
  const shot = (path, alt) => path ? `<img class="qa-shot" data-shot="${esc(path)}" alt="${esc(alt || 'Screenshot')}" loading="lazy">` : '';
  async function loadShots() {
    for (const img of document.querySelectorAll('#qaPage img[data-shot]:not([src])')) {
      const k = img.dataset.shot;
      if (ST.shots[k]) { img.src = ST.shots[k]; continue; }
      try { const r = await fetch('/api/qa/shots/' + k.split('/').map(enc).join('/'), {headers: {Authorization: 'Bearer ' + TOKEN}});
        if (!r.ok) { img.remove(); continue; } ST.shots[k] = URL.createObjectURL(await r.blob()); img.src = ST.shots[k]; } catch { img.remove(); }
    }
  }
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  function stack(rows) {   /* runs as stacked pass / fail / blocked columns */
    const rs = rows.filter(r => r.counts && r.counts.total).slice(0, 12).reverse();
    if (!rs.length) return '';
    const W = 760, H = 200, L = 40, R = 10, T = 14, B = 30, mx = Math.max(...rs.map(r => r.counts.total)) || 1, bw = Math.min(90, (W - L - R) / rs.length);
    const y = v => T + (1 - v / mx) * (H - T - B);
    const g = [mx, Math.round(mx / 2), 0].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(v)}</text>`).join('');
    const cols = rs.map((r, i) => { const x = L + i * bw + bw * 0.2, w = bw * 0.6; let at = 0; const c = r.counts;
      const seg = [['pass', 'qa-p'], ['fail', 'qa-f'], ['blocked', 'qa-b']].map(([k, cls]) => { const v = c[k] || 0; if (!v) return ''; const top = y(at + v), h = y(at) - top; at += v;
        return `<rect class="${cls}" x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}"><title>${esc(r.number)}: ${esc(v)} ${esc(k)}</title></rect>`; }).join('');
      return seg + `<text class="tx" x="${(x + w / 2).toFixed(1)}" y="${H - 9}" text-anchor="middle">${esc(r.number)}</text>`; }).join('');
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Pass and fail by run">${g}${cols}</svg></div>
      <div class="fo-leg" style="margin-top:6px"><span><i class="qa-p"></i>Pass</span><span><i class="qa-f"></i>Fail</span><span><i class="qa-b"></i>Blocked</span></div>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), ts = k.targets || [], oc = k.open_counts || {}, lr = k.last_run, run_ = (k.running || [])[0];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : ts.length ? 'Everything you test is in order.' : 'Tell me what to test to start.';
    const tiles = [
      `<div class="k"><div class="l">Testing</div><div class="v">${esc(num(ts.length))}</div><div class="s">${esc(pl(ts.reduce((s, t) => s + t.cases.active, 0), 'test case'))}</div></div>`,
      `<div class="k${(oc.critical || 0) + (oc.major || 0) ? ' low bad' : ''}"><div class="l">Bugs open</div><div class="v">${esc(num(k.open || 0))}</div><div class="s">${esc(num((oc.critical || 0) + (oc.major || 0)))} critical or major</div></div>`,
      `<div class="k${k.fixed_waiting ? ' low' : ''}"><div class="l">Fixes to check</div><div class="v">${esc(num(k.fixed_waiting || 0))}</div><div class="s">tested again on your tap</div></div>`,
      `<div class="k"><div class="l">Last run</div><div class="v">${lr && lr.counts.total ? esc(pct(Math.round(100 * (lr.counts.pass || 0) / lr.counts.total))) : '—'}</div><div class="s">${run_ ? esc(run_.number) + ' running now' : lr ? esc(lr.number + ' · ' + lr.target) : 'no run yet'}</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Open bugs</h2><div class="r"><button class="btn soft sm" type="button" data-go="bugs">Open</button></div></div>
          ${k.open ? ring(Object.keys(SEV).map((s, i) => [SEV[s][0], oc[s] || 0, 'qa-s' + i]), num(k.open), 'open', 'Open bugs by severity') : '<p class="cs-pos" style="margin:0">No open bugs.</p>'}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Release readiness</h2><div class="r"><button class="btn soft sm" type="button" data-go="release">Open</button></div></div>
        ${ts.length ? ts.map(t => { const r = (k.readiness || {})[t.id] || {}; return `<div class="cs-row"><span class="cs-dot${r.verdict === 'not_ready' ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(t.name)}</b> <span class="mut">${esc(KINDL[t.kind] || t.kind)} · pass ${esc(pct(r.pass_rate))}</span></span>${T_(VER, r.verdict || 'unknown')}</div>`; }).join('') : empty('Nothing is being tested yet.')}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Recent runs</h2><div class="r"><button class="btn soft sm" type="button" data-go="runs">Open</button></div></div>
        ${stack(k.runs || []) || empty('Runs show here once you start one.')}</section>`;
  }

  /* ---------------------------------------------------------------- what I test */
  function pTargets() {
    const k = K(), ts = k.targets || [], m = k.mine || {}, sec = k.sectors || [];
    const card = t => `<div class="pb-res${t.verified ? '' : ' warn'}" style="margin-top:12px">
      <div class="cs-head"><div><b>${esc(t.number)} · ${esc(t.name)}</b> <span class="mut">${esc(KINDL[t.kind] || t.kind)}${t.host ? ' · ' + esc(t.host) : ''}</span>
        <div class="mut" style="font-size:12.5px">${esc(pl(t.cases.active, 'case'))} (${esc(num(t.cases.auto))} automatic)${t.pages ? ' · ' + esc(pl(t.pages, 'page')) + ' found' : ''}${t.schedule ? ' · daily at ' + esc(t.schedule) : ''}</div></div>
        <div class="r">${t.verified ? tag('Yours - proved', 'ok') : tag('Not proved yet', 'warn')}</div></div>
      ${!t.verified && t.verify ? `<div style="margin-top:8px"><p style="margin:0 0 6px">${esc(t.verify.say)}</p>${t.verify.ways.map(w => `<div class="cs-row"><span class="cr-chk"></span><code class="qa-code">${esc(w)}</code></div>`).join('')}
        ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">Nothing on this site is tested until it is proved yours.</span><button class="btn sm" type="button" data-act="verify" data-t="${esc(t.id)}">Check now</button></div>` : ''}</div>` : ''}
      <p class="cs-note">${esc(t.standard)}${t.standard_source === 'check this' ? ' (check this)' : ''}</p>
      ${CAN() && t.verified ? `<div class="md-acts" style="justify-content:flex-start;flex-wrap:wrap;gap:6px">${t.kind !== 'apk' ? `<button class="btn soft sm" type="button" data-act="discover" data-t="${esc(t.id)}">Look through it again</button>` : ''}<button class="btn soft sm" type="button" data-tgo="cases" data-t="${esc(t.id)}">Test cases</button>${t.kind !== 'apk' ? `<button class="btn sm" type="button" data-act="run" data-t="${esc(t.id)}">Run all tests</button>` : ''}</div>` : ''}
      ${CAN() ? `<details class="ins-more"><summary>Settings and test accounts</summary>
        <form class="iv-add" data-form="tedit" data-id="${esc(t.id)}"><label class="ins-lab">Name<input class="in" name="name" value="${esc(t.name)}"></label>
          <label class="ins-lab">Who it is for<select class="in" name="sector">${sec.map(x => `<option value="${esc(x)}"${x === t.sector ? ' selected' : ''}>${esc(cap(x))}</option>`).join('')}</select></label>
          <label class="ins-lab">Daily tests at (your time)<input class="in" name="schedule" type="time" value="${esc(t.schedule || '')}"></label>
          <label class="ins-lab" style="flex:0 0 auto;flex-direction:row;align-items:center;gap:6px"><input type="checkbox" name="govt_facing"${t.govt_facing ? ' checked' : ''}> Government-facing</label>
          <button class="btn soft" type="submit">Save</button></form>
        <div class="cr-sub" style="margin-top:12px">Test accounts</div>${(t.accounts || []).map(a => `<div class="cs-row"><span style="flex:1">${esc(a.label)} <span class="mut">${esc(a.hint)}</span></span><button class="btn soft sm" type="button" data-act="account_remove" data-t="${esc(t.id)}" data-label="${esc(a.label)}">Remove</button></div>`).join('') || empty('None - tests that need a sign-in are skipped.')}
        <form class="iv-add" data-form="account" data-id="${esc(t.id)}"><input class="in" name="label" maxlength="40" placeholder="Label (test)" aria-label="Label"><input class="in" name="username" maxlength="120" placeholder="Test username" aria-label="Test username" autocomplete="off"><input class="in" name="password" type="password" maxlength="200" placeholder="Test password" aria-label="Test password" autocomplete="new-password"><button class="btn soft" type="submit">Add the test account</button></form>
        <p class="cs-note">Only a test account made for testing - never a real person's password. It is sealed and never shown again.</p>
        <div class="md-acts"><span></span><button class="btn soft sm" type="button" data-act="target_remove" data-t="${esc(t.id)}">Stop testing this</button></div></details>` : ''}</div>`;
    return `<div><h1 class="sd-h">What I test</h1><p class="lead">Your Hoola websites and apps, your own website once you prove it is yours, or an Android preview checked by hand. Hoola looks through each one in a real browser to find its pages, forms and screens.</p></div>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Add something to test</h2><form class="iv-add" data-form="tadd">
        <select class="in" name="pick" aria-label="What">${(m.sites || []).filter(x => x.built).map(x => `<option value="site:${esc(x.id)}">Website · ${esc(x.name)}</option>`).join('')}${(m.apps || []).filter(x => x.built).map(x => `<option value="app:${esc(x.id)}">App design · ${esc(x.name)}</option>`).join('')}${(m.apps || []).filter(x => x.apk).map(x => `<option value="apk:${esc(x.id)}">Android preview · ${esc(x.name)}</option>`).join('')}<option value="url:">My own website (by address)</option></select>
        <input class="in" name="url" maxlength="300" placeholder="https://your-site.com (for your own website)" aria-label="Address">
        <select class="in" name="sector" aria-label="Who it is for">${sec.map(x => `<option value="${esc(x)}">${esc(cap(x))}</option>`).join('')}</select>
        <button class="btn" type="submit">Add</button></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Testing now <span class="mut">${esc(num(ts.length))}</span></h2>${ts.length ? ts.map(card).join('') : empty('Nothing yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- test cases */
  function pCases() {
    const k = K(), t = tgt();
    if (!t) return `<div><h1 class="sd-h">Test cases</h1></div><section class="card">${empty('Add something to test first.')}<button class="btn soft sm" type="button" data-go="targets" style="margin-top:10px">What I test</button></section>`;
    const cs = lazyOut('cases:' + t.id, 'cases', {target: t.id});
    const types = Object.entries(k.types || {}), f = ST.cf || '';
    const rows = cs && cs.cases ? cs.cases.filter(c => !f || c.type === f || c.last_result === f) : [];
    return `<div class="cs-head"><div><h1 class="sd-h">Test cases</h1><p class="lead" style="margin-top:4px">Written from what Hoola found in a real browser and from your requirements. Automatic cases run in the browser; the others you check by hand and mark.</p></div><div class="r">${tgtPick()}</div></div>
      ${!t.verified ? '<p class="cs-note">This target is not proved yours yet - see What I test.</p>' : ''}
      ${CAN() && t.verified ? `<form class="card" data-form="write" data-id="${esc(t.id)}"><h2 class="md-h2">Write test cases</h2>
        <textarea class="in" name="text" rows="4" maxlength="20000" placeholder="Your requirements in your own words (optional) - for example: a visitor can book a table for 2-10 people; the phone number must be 10 digits; the menu shows prices." style="width:100%"></textarea>
        <div class="md-acts"><span class="mut" style="font-size:13px">Hoola adds cases for every page and form it finds, plus your requirements. You can edit or retire any.</span><button class="btn" type="submit">Write the cases</button></div></form>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(t.name)} <span class="mut">${cs && cs.cases ? esc(num(cs.cases.length)) : ''}</span></h2>
        <div class="r"><select class="in sm" data-cfilter="1" aria-label="Show"><option value="">All</option><option value="fail"${f === 'fail' ? ' selected' : ''}>Failing</option><option value="not_run"${f === 'not_run' ? ' selected' : ''}>Not run</option>${types.map(([v, l]) => `<option value="${esc(v)}"${f === v ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
          ${cs && cs.cases && cs.cases.length ? `<button class="btn soft sm" type="button" data-dl="cases" data-t="${esc(t.id)}">CSV</button>` : ''}</div></div>
        ${cs === null || cs === undefined ? loading() : cs.error ? `<p class="cs-neg">${esc(cs.error)}</p>` : rows.length ? rows.map(c => `<details class="qa-case" data-key="c:${esc(c.id)}"${ST.open.has('c:' + c.id) ? ' open' : ''}><summary><span class="qa-pr ${esc(c.priority)}">${esc(c.priority)}</span><span style="flex:1;min-width:0"><b>${esc(c.number)}</b> ${esc(c.title)} <span class="mut">${esc(c.type_label)}${c.area ? ' · ' + esc(c.area) : ''}${c.auto ? '' : ' · by hand'}</span></span>${T_(RES, c.last_result || 'not_run')}</summary>
          <div class="qa-body">${c.preconditions ? `<p class="mut" style="margin:0 0 6px">Before: ${esc(c.preconditions)}</p>` : ''}<ol>${c.steps_text.map(s => `<li>${esc(s)}</li>`).join('')}</ol><p style="margin:6px 0 0"><b>Expected:</b> ${esc(c.expected || '—')}</p>${c.note ? `<p class="mut" style="margin:6px 0 0">Note: ${esc(c.note)}</p>` : ''}
          ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;flex-wrap:wrap;gap:6px">${!c.auto ? `<button class="btn soft sm" type="button" data-mark="pass" data-c="${esc(c.id)}">It passed</button><button class="btn soft sm" type="button" data-mark="fail" data-c="${esc(c.id)}">It failed</button>` : `<button class="btn soft sm" type="button" data-act="run_case" data-c="${esc(c.id)}" data-t="${esc(t.id)}">Run this one</button>`}<button class="btn soft sm" type="button" data-act="case_retire" data-c="${esc(c.id)}">Retire</button>${ask('Test case ' + c.number + ': ' + c.title)}</div>` : ''}</div></details>`).join('') : empty(cs.cases && cs.cases.length ? 'No case matches.' : 'No cases yet - write them above.')}</section>
      ${CAN() && t.verified ? `<details class="card ins-more"><summary>Add a case by hand</summary><form class="cr-grid" data-form="case" data-id="${esc(t.id)}" style="margin-top:10px">
        <input class="in wide" name="title" required maxlength="200" placeholder="What is checked" aria-label="Title">
        <textarea class="in wide" name="steps_text" rows="3" placeholder="One step per line" aria-label="Steps"></textarea>
        <input class="in wide" name="expected" maxlength="600" placeholder="What should happen" aria-label="Expected">
        <select class="in" name="type" aria-label="Type">${types.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select><select class="in" name="priority" aria-label="Priority"><option>P1</option><option>P2</option><option selected>P3</option><option>P4</option></select>
        <input class="in" name="area" maxlength="80" placeholder="Area (page or screen)" aria-label="Area"><button class="btn" type="submit">Add the case</button></form>
        <p class="cs-note">A case added here is checked by hand; ask in the chat to make it automatic.</p></details>` : ''}`;
  }

  /* ---------------------------------------------------------------- runs */
  function pRuns() {
    const k = K(), ts = k.targets || [], rs = k.runs || [];
    if (ST.arg) {
      const r = lazyOut('run:' + ST.arg, 'run_view', {run: ST.arg});
      if (r === null || r === undefined) return loading();
      if (r.error) return `<section class="card"><p class="cs-neg">${esc(r.error)}</p></section>`;
      const run_ = r.run || r, c = run_.counts || {};
      return `<div><button class="btn soft sm" type="button" data-go="runs">← Runs</button><h1 class="sd-h" style="margin-top:10px">${esc(run_.number)} · ${esc(run_.target)}</h1><p class="lead" style="margin-top:2px">${esc(dt(run_.started_at))} · ${esc(run_.which)}${run_.error ? ' · ' + esc(run_.error) : ''}</p></div>
        <section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Pass', esc(num(c.pass || 0)), '', 'cs-pos')}${kpi('Fail', esc(num(c.fail || 0)), '', c.fail ? 'bad' : '')}${kpi('Blocked', esc(num(c.blocked || 0)), '', c.blocked ? 'warn' : '')}${kpi('By hand', esc(num((c.manual || 0) + (c.not_auto || 0))))}</section>
        ${(run_.results || []).some(x => x.status === 'pass') ? `<section class="card"><h2 class="md-h2">Passed <span class="mut">${esc(num(run_.results.filter(x => x.status === 'pass').length))}</span></h2><div class="qa-chips">${run_.results.filter(x => x.status === 'pass').map(x => `<span class="cs-tag ok">${esc(x.number)}</span>`).join('')}</div></section>` : ''}
        <section class="card"><h2 class="md-h2">Needs a look <span class="mut">${esc(num((run_.results || []).filter(x => x.status !== 'pass').length))}</span></h2>${(run_.results || []).filter(x => x.status !== 'pass').map(x => `<div class="qa-res"><div class="cs-head"><span><b>${esc(x.number)}</b> ${esc(x.message || '')}</span>${T_(RES, x.status)}</div>
          ${x.status !== 'pass' ? `<div class="qa-ea"><div><span class="mut">Expected</span>${esc(x.expected || '—')}</div><div><span class="mut">Actual</span>${esc(x.actual || '—')}</div></div>${x.step_text ? `<p class="mut" style="margin:4px 0 0;font-size:13px">At the step: ${esc(x.step_text)}</p>` : ''}${shot(x.shot ? run_.id + '/' + x.shot : '', x.number)}` : ''}</div>`).join('') || '<p class="cs-pos" style="margin:0">Everything passed.</p>'}</section>`;
    }
    return `<div><h1 class="sd-h">Runs</h1><p class="lead">Every run of the tests in a real browser, with what passed and what failed. A run works in the background - its result also comes to the chat.</p></div>
      ${CAN() && ts.filter(t => t.verified && t.kind !== 'apk').length ? `<section class="card"><h2 class="md-h2">Start a run</h2><form class="iv-add" data-form="run"><select class="in" name="target" aria-label="What">${ts.filter(t => t.verified && t.kind !== 'apk').map(t => `<option value="${esc(t.id)}">${esc(t.number)} · ${esc(t.name)}</option>`).join('')}</select>
        <select class="in" name="which" aria-label="Which tests"><option value="all">All tests</option><option value="smoke">Quick check (smoke)</option><option value="regression">Regression</option><option value="failed">Only the failing ones</option>${Object.entries(k.types || {}).map(([v, l]) => `<option value="${esc(v)}">Only ${esc(l)}</option>`).join('')}</select><button class="btn" type="submit">Run</button></form></section>` : ''}
      ${(k.running || []).length ? `<section class="card qa-live"><span class="qa-spin"></span><span>${esc(k.running.map(r => r.number + ' on ' + r.target).join(', '))} - running now</span></section>` : ''}
      <section class="card"><h2 class="md-h2">Pass and fail by run</h2>${stack(rs) || empty('No finished run yet.')}</section>
      <section class="card"><h2 class="md-h2">All runs</h2>${rs.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Run</th><th>When</th><th class="r">Pass</th><th class="r">Fail</th><th>Status</th><th></th></tr></thead><tbody>${rs.map(r => `<tr><td><b>${esc(r.number)}</b> <span class="mut">${esc(r.target)} · ${esc(r.which)}</span></td><td>${esc(dt(r.started_at))}</td><td class="r">${esc(num((r.counts || {}).pass || 0))}</td><td class="r ${(r.counts || {}).fail ? 'cs-neg' : ''}">${esc(num((r.counts || {}).fail || 0))}</td><td>${tag(r.status === 'done' ? 'Done' : r.status === 'running' ? 'Running' : 'Did not run', r.status === 'done' ? 'ok' : r.status === 'running' ? 'v' : 'bad')}</td><td class="r nw">${r.status === 'done' ? `<a class="btn soft sm" href="#/runs/${esc(r.id)}">Open</a>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No run yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- bugs */
  function pBugs() {
    const k = K(), f = ST.bf || 'open';
    const all = k.bugs || [], rows = all.filter(b => f === 'all' || (f === 'open' ? ['open', 'reopened', 'fixed'].includes(b.status) : b.status === f || b.severity === f));
    const card = b => `<details class="qa-bug" data-key="b:${esc(b.id)}"${ST.open.has('b:' + b.id) ? ' open' : ''}><summary>${T_(SEV, b.severity)}<span style="flex:1;min-width:0"><b>${esc(b.number)}</b> ${esc(b.title)} <span class="mut">${esc(b.target)}${b.seen > 1 ? ' · seen ' + esc(b.seen) + 'x' : ''}${b.regression ? ' · came back' : ''}</span></span>${T_(BST, b.status)}</summary>
      <div class="qa-body">${(b.steps || []).length ? `<ol>${b.steps.map(s => `<li>${esc(typeof s === 'string' ? s : JSON.stringify(s))}</li>`).join('')}</ol>` : ''}
        <div class="qa-ea"><div><span class="mut">Expected</span>${esc(b.expected || '—')}</div><div><span class="mut">Actual</span>${esc(b.actual || '—')}</div></div>
        ${b.page_url ? `<p class="mut" style="margin:6px 0 0;font-size:13px">On ${esc(b.page_url)}${b.viewport ? ' · ' + esc(b.viewport) + ' px wide' : ''} · found in ${esc(b.found_run ? (((K().runs || []).find(r => r.id === b.found_run) || {}).number || 'a run') : 'a hand check')}</p>` : ''}
        ${(b.console || []).length ? `<pre class="qa-con">${esc(b.console.slice(0, 6).join('\n'))}</pre>` : ''}${shot(b.shot, b.number)}
        ${(b.tracker || {}).github ? `<p style="margin:8px 0 0">GitHub issue: <a href="${esc(b.tracker.github.url)}" target="_blank" rel="noopener">#${esc(b.tracker.github.number)}</a></p>` : ''}
        ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;flex-wrap:wrap;gap:6px">${['open', 'reopened'].includes(b.status) ? `<button class="btn soft sm" type="button" data-bug="fixed" data-b="${esc(b.id)}">It is fixed</button>` : ''}${b.status === 'fixed' ? `<button class="btn sm" type="button" data-act="retest" data-b="${esc(b.id)}">Test it again</button>` : ''}${['open', 'reopened', 'fixed'].includes(b.status) ? `<button class="btn soft sm" type="button" data-bug="wont_fix" data-b="${esc(b.id)}">Will not fix</button><button class="btn soft sm" type="button" data-bug="closed" data-b="${esc(b.id)}">Close</button>` : `<button class="btn soft sm" type="button" data-bug="open" data-b="${esc(b.id)}">Open again</button>`}
          <select class="in sm" data-sev="${esc(b.id)}" aria-label="Severity">${Object.entries(SEV).map(([v, [l]]) => `<option value="${v}"${v === b.severity ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>${ask('Bug ' + b.number + ': ' + b.title)}</div>
          ${!(b.tracker || {}).github ? `<form class="iv-add" data-form="github" data-b="${esc(b.id)}"><input class="in" name="repo" maxlength="140" placeholder="GitHub repo (owner/name)" value="${esc(ST.repo || '')}" aria-label="GitHub repo"><button class="btn soft" type="submit">Prepare a GitHub issue</button></form>` : ''}` : ''}
        ${(b.log || []).length ? `<details class="ins-more"><summary>History</summary>${b.log.slice().reverse().map(l => `<div class="cs-row"><span style="flex:1">${esc(l.what || '')}</span><span class="mut nw">${esc(S(l.by || ''))} ${esc(dt(l.at))}</span></div>`).join('')}</details>` : ''}</div></details>`;
    return `<div class="cs-head"><div><h1 class="sd-h">Bugs</h1><p class="lead" style="margin-top:4px">Every failure is a numbered bug with its steps, expected vs actual, the page and a screenshot. The same failure again is the same bug. A fix is verified only when its test passes again.</p></div>
        <div class="r"><select class="in sm" data-bfilter="1" aria-label="Show"><option value="open"${f === 'open' ? ' selected' : ''}>Open</option><option value="all"${f === 'all' ? ' selected' : ''}>All</option>${Object.entries(BST).map(([v, [l]]) => `<option value="${v}"${f === v ? ' selected' : ''}>${esc(l)}</option>`).join('')}${Object.entries(SEV).map(([v, [l]]) => `<option value="${v}"${f === v ? ' selected' : ''}>${esc(l)} only</option>`).join('')}</select>
        ${all.length ? '<button class="btn soft sm" type="button" data-dl="bugs">CSV</button>' : ''}</div></div>
      ${(k.exports || []).length ? `<section class="card"><h2 class="md-h2">GitHub issues waiting for your tap</h2>${k.exports.map(e => `<div class="pb-res" style="margin-top:10px"><b>${esc(e.title)}</b> <span class="mut">${esc(e.repo)}</span><p class="mut" style="margin:6px 0 0;white-space:pre-wrap;font-size:13px;max-height:120px;overflow:auto">${esc(e.body)}</p>
        ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">Filed in your repo only when you tap.</span><button class="btn soft sm" type="button" data-act="github_cancel" data-e="${esc(e.id)}">Not now</button><button class="btn sm" type="button" data-act="github_push" data-e="${esc(e.id)}" data-h="${esc(e.hash)}">File it on GitHub</button></div>` : ''}</div>`).join('')}</section>` : ''}
      <section class="card">${rows.length ? rows.map(card).join('') : empty(f === 'open' ? 'No open bugs.' : 'No bug matches.')}</section>`;
  }

  /* ---------------------------------------------------------------- release */
  function pRelease() {
    const k = K(), ts = k.targets || [];
    return `<div class="cs-head"><div><h1 class="sd-h">Release</h1><p class="lead" style="margin-top:4px">Is each one ready to go out? Blockers stop a release (a failing P1 case, a critical or major bug); risks are worth a look. You decide.</p></div><div class="r">${ts.length ? '<button class="btn soft sm" type="button" data-dl="readiness">CSV</button>' : ''}</div></div>
      ${ts.length ? ts.map(t => { const r = (k.readiness || {})[t.id] || {}, c = r.counts || {};
        return `<section class="card"><div class="cs-head"><div><h2 class="md-h2" style="margin:0">${esc(t.name)}</h2><p class="mut" style="margin:2px 0 0">${esc(r.say || '')}</p></div><div class="r">${T_(VER, r.verdict || 'unknown')}</div></div>
          <div class="qa-meter" role="img" aria-label="Cases by result">${[['pass', 'qa-p'], ['fail', 'qa-f'], ['blocked', 'qa-b'], ['manual', 'qa-m'], ['not_run', 'qa-n']].map(([kk, cls]) => c[kk] ? `<b class="${cls}" style="flex:${c[kk]}" title="${esc(kk)} ${esc(c[kk])}"></b>` : '').join('')}</div>
          <div class="fo-leg" style="margin-top:8px">${[['pass', 'qa-p', 'Pass'], ['fail', 'qa-f', 'Fail'], ['blocked', 'qa-b', 'Blocked'], ['manual', 'qa-m', 'By hand'], ['not_run', 'qa-n', 'Not run']].map(([kk, cls, l]) => `<span><i class="${cls}"></i>${esc(l)}<b>${esc(num(c[kk] || 0))}</b></span>`).join('')}</div>
          ${(r.blockers || []).length ? `<div class="cr-sub" style="margin-top:12px">Blockers</div>${r.blockers.map(x => `<div class="cs-row"><span class="cs-dot bad"></span><span>${esc(x)}</span></div>`).join('')}` : ''}
          ${(r.risks || []).length ? `<div class="cr-sub" style="margin-top:12px">Risks</div>${r.risks.map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}` : ''}
          <p class="cs-note">${esc(r.standard || t.standard)}${t.standard_source === 'check this' ? ' (check this)' : ''}</p></section>`; }).join('') : `<section class="card">${empty('Nothing is being tested yet.')}</section>`}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, cs = k.country_standard || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your team name, your own testing rules (Hoola follows them when it writes cases) and your country, which sets the accessibility law shown.</p></div>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="qset"><h2 class="md-h2">Your QA</h2><div class="md-form">
          <div class="md-field"><label for="qaS1">Team name</label><input class="in" id="qaS1" name="team_name" maxlength="120" value="${esc(s.team_name || '')}"></div>
          <div class="md-field"><label for="qaS2">Country (two letters)</label><input class="in" id="qaS2" name="country" maxlength="2" value="${esc(s.country || '')}"></div>
          <div class="md-field wide"><label for="qaS3">Your testing rules</label><textarea class="in" id="qaS3" name="rules" rows="6" maxlength="3000" placeholder="For example: every form must show an error in plain words; phone numbers are 10 digits; test on 360 px phones first.">${esc(s.rules || '')}</textarea></div></div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <section class="card"><h2 class="md-h2">Accessibility in ${esc(s.country || '—')}</h2><p style="margin:0">${esc(cs.text || '')}</p><p class="cs-note">${cs.source === 'checked' ? 'Checked from the official sources.' : 'From memory - check this with your own adviser.'}</p></section></div>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Test a website you have not proved is yours', 'Pay, or go past a payment page', 'Use a real person\'s password, an OTP or a card number - test accounts only', 'Submit forms on a live site unless you allow it for a staging site', 'File a GitHub issue without your tap'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function download(what, target) {
    try {
      const r = await fetch(`/api/qadesk/download?what=${enc(what)}&target=${enc(target || '')}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.csv`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  const dropCases = () => { for (const k of Object.keys(ST.out)) if (k.startsWith('cases:')) delete ST.out[k]; };
  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl, dl.dataset.t || (tgt() || {}).id); return; }
    const tg = t.closest('[data-tgo]'); if (tg) { ST.tid = tg.dataset.t; location.hash = '#/' + tg.dataset.tgo; return; }
    try {
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act, d = a.dataset;
        if (act === 'target_remove' && !confirm('Stop testing this? Its cases and bugs stay in the history.')) return;
        a.disabled = true;
        if (act === 'verify') { const r = await run('verify', {target: d.t}); await changed(r.say || (r.verified ? 'Proved yours.' : 'Not found yet.')); }
        else if (act === 'discover') { toast('Looking through it in a real browser - this can take a minute.'); const r = await run('discover', {target: d.t}); dropCases(); await changed(r.say); }
        else if (act === 'run') { const r = await run('run', {target: d.t, which: 'all'}); await changed(r.say); }
        else if (act === 'run_case') { const r = await run('run', {target: d.t, cases: [d.c]}); await changed(r.say); }
        else if (act === 'account_remove') { await run('account_remove', {target: d.t, label: d.label}); await changed('Test account removed.'); }
        else if (act === 'target_remove') { await run('target_remove', {target: d.t}); ST.tid = ''; await changed('No longer tested.'); }
        else if (act === 'case_retire') { await run('case_retire', {case: d.c}); dropCases(); await changed('Retired.'); }
        else if (act === 'retest') { const r = await run('retest', {bug: d.b}); await changed(r.say); }
        else if (act === 'github_push') { const r = await run('github_push', {export: d.e, hash: d.h}); await changed(r.say); }
        else if (act === 'github_cancel') { await run('github_cancel', {export: d.e}); await changed('Not filed.'); }
        return;
      }
      const mk = t.closest('[data-mark]'); if (mk) { let note = ''; if (mk.dataset.mark === 'fail') { note = prompt('What went wrong? (one line)') || ''; }
        const r = await run('mark', {case: mk.dataset.c, result: mk.dataset.mark, note}); dropCases(); await changed(r.say); return; }
      const bg = t.closest('[data-bug]'); if (bg) { const st = bg.dataset.bug; let reason = '';
        if (st === 'wont_fix' || st === 'closed') { reason = prompt(st === 'wont_fix' ? 'Why will it not be fixed?' : 'Why is it closed?') || ''; if (!reason) return; }
        const r = await run('bug', {bug: bg.dataset.b, status: st, reason}); await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); const a = t.closest('[data-act]'); if (a) a.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    try {
      if (el.dataset.tpick) { ST.tid = el.value; showPage(true); return; }
      if (el.dataset.cfilter !== undefined) { ST.cf = el.value; showPage(true); return; }
      if (el.dataset.bfilter !== undefined) { ST.bf = el.value; showPage(true); return; }
      if (el.dataset.sev) { const r = await run('bug', {bug: el.dataset.sev, severity: el.value}); await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'tadd') { const [k, ref] = g('pick').split(':'); const a = {kind: k, sector: g('sector')};
        if (k === 'url') { if (!g('url')) throw new Error('Type the address of your website.'); a.url = g('url'); } else a.ref = ref;
        const r = await run('target_add', a); ST.tid = r.target.id; await done(r.say); }
      else if (kind === 'tedit') { const r = await run('target_edit', {target: form.dataset.id, name: g('name'), sector: g('sector'), schedule: g('schedule'), govt_facing: fd.get('govt_facing') === 'on'}); await changed(r.say); }
      else if (kind === 'account') { const r = await run('account', {target: form.dataset.id, label: g('label') || 'test', username: g('username'), password: S(fd.get('password'))}); await done(r.say || 'Test account added, sealed.'); }
      else if (kind === 'write') { toast('Writing the cases - Hoola looks through it in a real browser first. This can take a minute.'); const r = await run('write', {target: form.dataset.id, text: g('text')}); dropCases(); await done(r.say); }
      else if (kind === 'case') { const r = await run('case_add', {target: form.dataset.id, title: g('title'), steps_text: g('steps_text'), expected: g('expected'), type: g('type'), priority: g('priority'), area: g('area')}); dropCases(); await done(r.say); }
      else if (kind === 'run') { const r = await run('run', {target: g('target'), which: g('which')}); await changed(r.say); }
      else if (kind === 'github') { ST.repo = g('repo'); const r = await run('github', {bug: form.dataset.b, repo: g('repo')}); await changed(r.say); }
      else if (kind === 'qset') { await run('settings', {team_name: g('team_name'), rules: g('rules'), country: g('country').toUpperCase()}); await changed('Saved.'); }
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
    const box = $('#qaFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/qadesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'qa' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


