/* PRODUCT MANAGER DESK - the Product manager's own section, like the finance desks (owner: "Product manager same as finance desks").
   A thin top bar, then the Product chat (its own conversation, kind 'product') beside the desk's pages: Today, Backlog, Roadmap,
   Specs, Releases, KPIs & results, Settings. The pages call /api/prdesk/do/<part>, which runs the product engine. Hoola never makes
   up a reach, impact, effort or revenue number, and nothing is published without her tap. */
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

  const TABS = [['today', 'Today'], ['backlog', 'Backlog'], ['roadmap', 'Roadmap'], ['specs', 'Specs'], ['releases', 'Releases'],
    ['metrics', 'KPIs & results'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What should we build next?', 'What are customers asking for most?', 'Summarise the roadmap for the team'],
    backlog: ['Bring in this week\'s feedback', 'Which problems have no score yet?', 'Are any of these the same problem?'],
    roadmap: ['Does Now fit our capacity?', 'Suggest a plan from the scores', 'What depends on what?'],
    specs: ['Write a spec for the top problem', 'What is missing from this spec?', 'Turn this spec into test cases'],
    releases: ['Write release notes for this version', 'Shorten the Play Store text', 'What shipped since the last release?'],
    metrics: ['Did the last feature move our north star?', 'Set a north star for us', 'Which KPI is off target?'],
    settings: ['How do I connect GitHub?', 'RICE or ICE - which suits us?', 'How much can my team build in a cycle?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sid: '', rid: '', bf: 'open', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.prdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.prdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'product', name: ((K().settings || {}).product) || 'Your product'} : null;
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
  const run = (part, a) => api('POST', '/api/prdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/prdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Product manager is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="prHire">Hire the Product manager</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#prHire').onclick = async () => { try { await api('POST', '/api/employees/product/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Product manager</div><div class="sd-site" id="prSite"></div></div>
          <span id="prState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Product chat">
          <div class="sd-chathead"><div class="t"><b>Product chat</b><span>Ask what to build next, for a spec or release notes - or drop feedback, interview notes or a competitor page here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="prFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="prPick" multiple hidden accept="image/*,.pdf,.csv,.xlsx,.txt,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Product desk" id="sdTabs"></nav>
          <div id="prPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola never makes up a number and publishes only on your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask what to build next…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#prPick').click()});
    $('#prPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.prdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.prdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/prdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#prPage').addEventListener('click', onPageClick);
    $('#prPage').addEventListener('submit', onSubmit);
    $('#prPage').addEventListener('change', onChange);
    $('#prPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#prState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), st = k.settings || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : (k.day || {}).waiting ? ['warn', 'Waiting for your tap'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'On it'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#prSite').textContent = [st.product, pl(((k.backlog || {}).items || []).length, 'problem'), st.repo, st.country || ''].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), d = k.day || {};
    const n = {backlog: (k.backlog || {}).unscored || '', releases: d.waiting || '', roadmap: ((k.roadmap || {}).problems || []).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/prdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#prPage'); if (!box) return;
    const fn = {today: pToday, backlog: pBacklog, roadmap: pRoadmap, specs: pSpecs, releases: pReleases, metrics: pMetrics, settings: pSettings}[ST.tab] || pToday;
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
  const CS = {INR: '₹', USD: '$', EUR: '€', GBP: '£', SGD: 'S$', AUD: 'A$', CAD: 'C$', JPY: '¥', AED: 'AED ', ZAR: 'R ', NGN: '₦', KES: 'KSh ', BRL: 'R$'};
  const mon = v => (v === null || v === undefined || v === '') ? '—' : (CS[K().money_unit] || (K().money_unit || 'INR') + ' ') + Math.round(Number(v)).toLocaleString();
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const OST = {new: ['New', 'warn'], backlog: ['Backlog', ''], now: ['Now', 'v'], next: ['Next', ''], later: ['Later', ''], building: ['Building', 'v'], shipped: ['Shipped', 'ok'], merged: ['Merged', ''], dropped: ['Dropped', '']};
  const BL = () => (K().backlog || {}).items || [];
  const st_ = () => K().settings || {};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const filesBox = () => (ST.files_ready || []).length ? `<section class="card"><h2 class="md-h2">Files ready</h2><div class="md-acts" style="justify-content:flex-start;flex-wrap:wrap;gap:6px">${ST.files_ready.map((f, i) => `<button class="btn soft sm" type="button" data-file="${i}">${esc(f.name)}</button>`).join('')}</div><p class="cs-note">Also in your Docs and files.</p></section>` : '';
  const oTag = o => tag((OST[o.status] || [cap(o.status)])[0], (OST[o.status] || ['', ''])[1]);

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), items = BL(), rm = k.roadmap || {}, mt = (k.metrics || {}).kpis || [], ns = mt.find(x => x.north_star);
    const open = items.filter(x => !['shipped', 'merged', 'dropped'].includes(x.status));
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order: the backlog is scored and the roadmap fits your capacity.';
    const tiles = [
      `<div class="k"><div class="l">${esc(ns ? ns.name : 'North star')}</div><div class="v">${ns && ns.latest !== null ? esc(num(ns.latest)) + (ns.unit ? ' ' + esc(ns.unit) : '') : '—'}</div><div class="s">${ns && ns.target !== null && ns.target !== undefined ? 'target ' + esc(num(ns.target)) : 'set it on KPIs'}</div></div>`,
      `<div class="k${(k.day || {}).new && k.day.new.length ? ' low bad' : ''}"><div class="l">Open problems</div><div class="v">${esc(num(open.length))}</div><div class="s">${esc(num(((k.day || {}).new || []).length))} new from customers</div></div>`,
      `<div class="k${(k.backlog || {}).unscored ? ' low bad' : ''}"><div class="l">Without a score</div><div class="v">${esc(num((k.backlog || {}).unscored || 0))}</div><div class="s">your estimates needed</div></div>`,
      `<div class="k${(k.day || {}).waiting ? ' low bad' : ''}"><div class="l">Publish cards</div><div class="v">${esc(num((k.day || {}).waiting || 0))}</div><div class="s">go out only on your tap</div></div>`];
    const bk = rm.buckets || {};
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Highest scores</h2><div class="r"><button class="btn soft sm" type="button" data-go="backlog">Open</button></div></div>
          ${(k.top || []).length ? bars(k.top.map(x => [x.number + ' ' + x.title, x.score, 'mk-b', 'seen ' + x.seen + (x.bucket ? ' · ' + x.bucket : '')]), num, (st_().scoring || 'rice').toUpperCase() + ' score') : empty('Score the backlog with your numbers.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Roadmap vs capacity</h2><div class="r"><button class="btn soft sm" type="button" data-go="roadmap">Open</button></div></div>
          ${['now', 'next', 'later'].map(b => { const v = bk[b] || {}; const c = v.capacity, e = v.effort || 0;
            return `<div class="pr-cap"><span><b>${esc(v.label || cap(b))}</b> <span class="mut">${esc(pl((v.items || []).length, 'item'))}</span></span><i><b class="${v.over ? 'cy-bad' : 'cy-ok'}" style="width:${c ? Math.min(100, 100 * e / c).toFixed(0) : (e ? 100 : 0)}%"></b></i><em class="${v.over ? 'cs-neg' : ''}">${esc(e)}${c !== null && c !== undefined ? ' of ' + esc(c) : ''} mo</em></div>`; }).join('')}
          <p class="cs-note">Work in person-months from your estimates, against the capacity you set in Settings.</p></section>
        <section class="card"><h2 class="md-h2">Where problems come from</h2>${(k.by_source || []).length ? bars(k.by_source.map(([n, v]) => [n, v, 'mk-b']), num, 'Problems by source') : empty('Harvest to bring in feedback, support and sales.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- backlog */
  function scoreForm(o) {
    const ice = (st_().scoring || 'rice') === 'ice';
    if (ice) return `<form class="iv-add" data-form="score" data-id="${esc(o.id)}"><input class="in" name="ice_impact" inputmode="numeric" placeholder="Impact 1-10" value="${esc(o.ice_impact ?? '')}" aria-label="Impact"><input class="in" name="ice_confidence" inputmode="numeric" placeholder="Confidence 1-10" value="${esc(o.ice_confidence ?? '')}" aria-label="Confidence"><input class="in" name="ease" inputmode="numeric" placeholder="Ease 1-10" value="${esc(o.ease ?? '')}" aria-label="Ease"><button class="btn soft" type="submit">Score</button></form>`;
    return `<form class="iv-add" data-form="score" data-id="${esc(o.id)}"><input class="in" name="reach" inputmode="numeric" placeholder="Reach (people a quarter)" value="${esc(o.reach ?? '')}" aria-label="Reach">
      <select class="in" name="impact" aria-label="Impact"><option value="">Impact</option>${Object.entries(K().impact_labels || {}).sort((a, b) => b[0] - a[0]).map(([v, l]) => `<option value="${esc(v)}"${o.impact !== null && o.impact !== undefined && Number(o.impact) === Number(v) ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
      <select class="in" name="confidence" aria-label="Confidence"><option value="">Confidence</option>${[100, 80, 50].map(v => `<option value="${v}"${Number(o.confidence) === v || Number(o.confidence) * 100 === v ? ' selected' : ''}>${v}%</option>`).join('')}</select>
      <input class="in" name="effort" placeholder="Effort (e.g. 2 weeks, 1.5 months)" value="${esc(o.effort ?? '')}" aria-label="Effort"><button class="btn soft" type="submit">Score</button></form>`;
  }
  function pBacklog() {
    const k = K(), f = ST.bf || 'open', items = BL().filter(x => f === 'all' ? true : f === 'open' ? !['shipped', 'merged', 'dropped'].includes(x.status) : f === 'unscored' ? x.score === null : x.status === f);
    const det = o => { const full = ST.open.has('o:' + o.id) ? lazyOut('o:' + o.id, 'opp_get', {id: o.id}) : undefined, fo = full && !full.error ? (full.opportunity || full) : null;
      return `<div class="qa-body">${o.problem ? `<p style="margin:0">${esc(o.problem)}</p>` : ''}<div class="cy-meta">${o.who ? `<span><span class="mut">Who</span> ${esc(o.who)}</span>` : ''}<span><span class="mut">Seen</span> ${esc(o.seen)} times</span>${o.rupees ? `<span><span class="mut">Money at stake</span> ${esc(mon(o.rupees))}</span>` : ''}${o.kano ? `<span><span class="mut">Kano</span> ${esc(o.kano_label)}</span>` : ''}${(o.depends || []).length ? `<span><span class="mut">Needs first</span> ${esc(o.depends.join(', '))}</span>` : ''}</div>
        ${fo ? `${(fo.evidence || []).length ? `<div class="cr-sub" style="margin-top:8px">Evidence</div>${fo.evidence.slice(0, 6).map(e => `<div class="pr-ev"><span class="mut">${esc((K().sources || {})[e.source] || e.source)}${e.count ? ' · x' + esc(e.count) : ''}</span>${(e.quotes || []).slice(0, 2).map(q => `<q>${esc(q)}</q>`).join('')}${e.note ? `<span>${esc(e.note)}</span>` : ''}</div>`).join('')}` : ''}
          ${(fo.solutions || []).length ? `<div class="cr-sub" style="margin-top:8px">Ideas to solve it</div>${fo.solutions.map(x => `<div class="cs-row"><span style="flex:1">${esc(x.text)}${x.assumption ? ` <span class="mut">assumes: ${esc(x.assumption)}</span>` : ''}</span>${x.chosen ? tag('Chosen', 'ok') : ''}</div>`).join('')}` : ''}
          ${fo.result && Object.keys(fo.result).length ? `<div class="cr-sub" style="margin-top:8px">30 days before / after</div><p style="margin:0">${esc(fo.result.say || '')}</p>` : ''}` : full === null ? '<p class="mut" style="margin:6px 0 0">Loading evidence…</p>' : ''}
        <div class="cr-sub" style="margin-top:10px">Score (${esc((o.scoring || 'rice').toUpperCase())}) ${o.score !== null ? tag(String(o.score), 'ok') : tag('Not scored', 'warn')}</div>
        ${o.ask ? `<p class="mut" style="margin:2px 0 0;font-size:13px">${esc(o.ask)}</p>` : ''}${o.formula ? `<p class="mut" style="margin:2px 0 0;font-size:13px">${esc(o.formula)}</p>` : ''}
        ${CAN() && !['shipped', 'merged', 'dropped'].includes(o.status) ? scoreForm(o) + `<div class="md-acts" style="justify-content:flex-start;gap:6px;flex-wrap:wrap">
          <select class="in sm" data-place="${esc(o.id)}" aria-label="Roadmap"><option value="">Put on the roadmap…</option>${['now', 'next', 'later', 'none'].map(b => `<option value="${b}">${b === 'none' ? 'Back to backlog' : cap(b)}</option>`).join('')}</select>
          <select class="in sm" data-kano="${esc(o.id)}" aria-label="Kano"><option value="">Kano…</option>${Object.entries(K().kano_labels || {}).map(([v, l]) => `<option value="${esc(v)}"${o.kano === v ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
          <button class="btn sm" type="button" data-spec="${esc(o.id)}">Write the spec</button><button class="btn soft sm" type="button" data-sol="${esc(o.id)}">Add an idea</button><button class="btn soft sm" type="button" data-dep="${esc(o.id)}">Needs first…</button>
          <button class="btn soft sm" type="button" data-ship="${esc(o.id)}">Shipped</button><button class="btn soft sm" type="button" data-merge="${esc(o.id)}">Same as…</button><button class="btn soft sm" type="button" data-drop="${esc(o.id)}">Drop</button>${ask(o.number + ' ' + o.title)}</div>` : ''}
        ${CAN() && o.status === 'shipped' ? `<div class="md-acts" style="justify-content:flex-start"><button class="btn soft sm" type="button" data-ba="${esc(o.id)}">Before / after now</button></div>` : ''}</div>`; };
    return `<div class="cs-head"><div><h1 class="sd-h">Backlog</h1><p class="lead" style="margin-top:4px">Customer problems with their evidence - from feedback, support tickets, questions nobody could answer, sales objections and your own ideas. Scored only with your numbers.</p></div>
        <div class="r">${CAN() ? '<button class="btn sm" type="button" data-act="harvest">Harvest now</button>' : ''}</div></div>
      ${CAN() ? `<div class="md-2" style="align-items:start"><form class="card" data-form="opp"><h2 class="md-h2">Add a problem</h2><div class="md-form"><div class="md-field wide"><label for="prO1">The problem (not the solution)</label><input class="in" id="prO1" name="title" required maxlength="200"></div>
          <div class="md-field wide"><label for="prO2">More about it</label><input class="in" id="prO2" name="problem" maxlength="600"></div><div class="md-field"><label for="prO3">Who has it</label><input class="in" id="prO3" name="who" maxlength="160"></div>
          <div class="md-field"><label for="prO4">A customer's words</label><input class="in" id="prO4" name="quote" maxlength="400"></div></div><div class="md-acts"><span></span><button class="btn" type="submit">Add</button></div></form>
        <form class="card" data-form="ideas"><h2 class="md-h2">Your notes and ideas</h2><textarea class="in" name="text" rows="5" maxlength="20000" placeholder="Paste ideas, competitor notes, complaints - Hoola finds the problems behind them" style="width:100%"></textarea>
          <div class="iv-add" style="margin-top:8px"><input class="in" name="competitor" maxlength="120" placeholder="Competitor (if these are their features)" aria-label="Competitor"><button class="btn soft" type="submit">Find the problems</button></div></form></div>` : ''}
      ${(k.duplicates || []).length ? `<section class="card"><h2 class="md-h2">Look like the same problem</h2>${k.duplicates.map(d => `<div class="cs-row"><span style="flex:1"><b>${esc(d.a)}</b> ${esc(d.a_title || '')} <span class="mut">and</span> <b>${esc(d.b)}</b> ${esc(d.b_title || '')}</span>${CAN() ? `<button class="btn soft sm" type="button" data-mergeto="${esc(d.b)}" data-into="${esc(d.a)}">Merge into ${esc(d.a)}</button>` : ''}</div>`).join('')}</section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Problems</h2><div class="r"><select class="in sm" data-bfilter="1" aria-label="Show">${[['open', 'Open'], ['unscored', 'Not scored'], ['new', 'New'], ['now', 'Now'], ['next', 'Next'], ['later', 'Later'], ['shipped', 'Shipped'], ['all', 'All']].map(([v, l]) => `<option value="${v}"${f === v ? ' selected' : ''}>${l}</option>`).join('')}</select></div></div>
        ${items.length ? items.map(o => `<details class="qa-case" data-key="o:${esc(o.id)}"${ST.open.has('o:' + o.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(o.number)}</b> ${esc(o.title)} <span class="mut">seen ${esc(o.seen)}${o.sources.length ? ' · ' + esc(o.sources.map(s => ((K().sources || {})[s] || s).split(' ')[0]).join(', ')) : ''}</span></span>${o.score !== null ? `<span class="mut nw">${esc(o.score)}</span>` : ''}${oTag(o)}</summary>${det(o)}</details>`).join('') : empty('Nothing here.')}</section>`;
  }

  /* ---------------------------------------------------------------- roadmap */
  function pRoadmap() {
    const k = K(), rm = k.roadmap || {}, bk = rm.buckets || {}, pl_ = ST.out.plan;
    return `<div class="cs-head"><div><h1 class="sd-h">Roadmap</h1><p class="lead" style="margin-top:4px">Now / Next / Later, checked against your capacity and the order things depend on. Hoola suggests a plan from the scores; it changes only when you say so.</p></div>
        <div class="r">${CAN() ? '<button class="btn soft sm" type="button" data-act="plan">Suggest a plan</button><button class="btn soft sm" type="button" data-act="roadmap_files">Word, Excel + Markdown</button>' : ''}</div></div>${filesBox()}
      ${(rm.problems || []).length ? `<section class="card"><h2 class="md-h2">To fix</h2>${rm.problems.map(p => `<div class="cs-row"><span class="cs-dot${p.id.startsWith('over_') || p.id === 'cycle' ? ' bad' : ''}"></span><span>${esc(p.say)}</span></div>`).join('')}</section>` : ''}
      ${pl_ && !pl_.error ? `<section class="card"><h2 class="md-h2">Suggested plan</h2><p style="margin:0">${esc(pl_.say)}</p>${(pl_.moves || []).filter(m => m.from !== m.to).map(m => `<div class="cs-row"><span style="flex:1"><b>${esc(m.number)}</b> ${esc(m.title || '')}</span><span class="mut">${esc(m.from || 'backlog')} → ${esc(m.to)}</span></div>`).join('')}
        ${CAN() && !pl_.applied ? '<div class="md-acts"><span></span><button class="btn" type="button" data-act="plan_apply">Use this plan</button></div>' : ''}</section>` : ''}
      <div class="pr-board">${['now', 'next', 'later'].map(b => { const v = bk[b] || {items: []};
        return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(v.label || cap(b))}</h2><div class="r">${tag((v.effort || 0) + (v.capacity !== null && v.capacity !== undefined ? ' of ' + v.capacity : '') + ' months', v.over ? 'bad' : '')}</div></div>
          ${(v.items || []).map(o => `<div class="pr-card"><b>${esc(o.number)}</b> ${esc(o.title)}<div class="mut" style="font-size:12.5px">${o.score !== null ? 'score ' + esc(o.score) : 'no score'}${o.effort ? ' · ' + esc(pl(o.effort, 'month')) : ''}${o.goal ? ' · moves ' + esc(o.goal) : ''}${(o.depends || []).length ? ' · after ' + esc(o.depends.join(', ')) : ''}</div></div>`).join('') || empty('Empty.')}</section>`; }).join('')}</div>`;
  }

  /* ---------------------------------------------------------------- specs */
  function pSpecs() {
    const k = K(), sps = k.specs || [], sel = ST.sid && sps.find(x => x.id === ST.sid), sv = sel ? lazyOut('s:' + sel.id, 'spec_get', {id: sel.id}) : null, b = sv && !sv.error ? ((sv.spec || sv).body || {}) : null;
    const li = a => (a || []).map(x => `<li>${esc(typeof x === 'string' ? x : JSON.stringify(x))}</li>`).join('');
    return `<div><h1 class="sd-h">Specs</h1><p class="lead">A short spec for each problem you build: users, goals, what you will NOT do, user stories with Given / When / Then a tester can check, edge cases and the events to track. Hoola writes [blank] where a fact is missing.</p></div>
      ${filesBox()}<section class="card"><h2 class="md-h2">Specs <span class="mut">${esc(num(sps.length))}</span></h2>${sps.map(x => `<div class="cs-row${sel && x.id === sel.id ? ' cy-sel' : ''}"><span style="flex:1"><b>${esc(x.number)}</b> ${esc(x.title)} <span class="mut">v${esc(x.version)} · ${esc(pl(x.stories, 'story', 'stories'))}</span></span>${x.blocks ? tag(x.blocks + ' to fix', 'warn') : tag(cap(x.status), x.status === 'ready' ? 'ok' : 'warn')}<button class="btn soft sm" type="button" data-sid="${esc(x.id)}">Open</button></div>`).join('') || empty('Write a spec from a problem in the Backlog.')}</section>
      ${sel ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(sel.number)} · ${esc(sel.title)}</h2><div class="r">${CAN() ? `<button class="btn soft sm" type="button" data-act="spec_files" data-id="${esc(sel.id)}">Word, Markdown + tests</button>` : ''}${ask('Spec ' + sel.number)}</div></div>
        ${sv === null ? '<p class="mut">Loading…</p>' : !b ? `<p class="cs-neg">${esc((sv || {}).error || '')}</p>` : `
          ${(sel.checks || []).length ? (sel.checks || []).map(c => `<div class="rk-flag ${c.level === 'block' ? 'stop' : 'check'}"><span>${c.level === 'block' ? 'Fix' : 'Look'}</span><div>${esc(c.say)}</div></div>`).join('') : ''}
          <p style="margin:8px 0 0">${esc(b.problem || '')}</p>
          <div class="dv-grid"><div><span class="mut">Users</span><ul class="pr-ul">${li(b.users)}</ul><span class="mut">Goals</span><ul class="pr-ul">${li(b.goals)}</ul></div><div><span class="mut">Not doing</span><ul class="pr-ul">${li(b.non_goals)}</ul><span class="mut">Measures</span><ul class="pr-ul">${li(b.metrics)}</ul></div></div>
          <div class="cr-sub" style="margin-top:10px">User stories</div>${(b.stories || []).map(s => `<div class="pr-story"><b>${esc(s.id)}</b> As ${esc(s.as_a)}, I want ${esc(s.i_want)}${s.so_that ? ', so that ' + esc(s.so_that) : ''}.${(s.criteria || []).map(c => `<div class="pr-gwt"><span><i>Given</i> ${esc(c.given)}</span><span><i>When</i> ${esc(c.when)}</span><span><i>Then</i> ${esc(c.then)}</span></div>`).join('')}</div>`).join('') || empty('No stories yet.')}
          ${(b.edge_cases || []).length ? `<div class="cr-sub" style="margin-top:10px">Edge cases</div><ul class="pr-ul">${li(b.edge_cases)}</ul>` : ''}
          ${(b.events || []).length ? `<div class="cr-sub" style="margin-top:10px">Events to track</div>${b.events.map(e => `<div class="cs-row"><code class="qa-code">${esc(e.name)}</code><span class="mut">${esc(e.when)}</span></div>`).join('')}` : ''}
          ${(b.open_questions || []).length ? `<div class="cr-sub" style="margin-top:10px">Open questions</div><ul class="pr-ul">${li(b.open_questions)}</ul>` : ''}
          ${CAN() ? `<form class="iv-add" data-form="revise" data-id="${esc(sel.id)}"><input class="in" name="instruction" required maxlength="1000" placeholder="What to change (Hoola keeps only facts you gave)" aria-label="Change"><button class="btn soft" type="submit">Revise</button></form>` : ''}`}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- releases */
  function pReleases() {
    const k = K(), rels = k.all_releases || [], sel = ST.rid && rels.find(x => x.id === ST.rid), rv = sel ? lazyOut('r:' + sel.id, 'release_get', {id: sel.id}) : null, n = rv && !rv.error ? ((rv.release || rv).notes || {}) : null;
    const pubs = k.all_publishes || [], waiting = pubs.filter(p => p.status === 'waiting'), sl = st_().second_lang || '';
    return `<div><h1 class="sd-h">Releases</h1><p class="lead">Release notes from what really shipped - your words, shipped problems and merged pull requests - in plain English${sl ? ' and ' + esc(sl) : ''}, the store texts within their limits and a changelog. Publishing is a card you tap.</p></div>
      ${filesBox()}${waiting.length ? `<section class="card"><h2 class="md-h2">Waiting for your tap</h2>${waiting.map(p => `<div class="pb-res warn" style="margin-top:8px"><div class="cs-head"><b>${esc(cap(p.what))} → ${esc({github: 'GitHub release', page: 'public page', copy: 'copy to paste yourself'}[p.dest] || p.dest)}</b></div><pre class="dv-code" style="max-height:220px">${esc(p.text)}</pre>
        ${CAN() ? `<form class="iv-add" data-form="decide" data-id="${esc(p.id)}" data-h="${esc(p.hash)}"><button class="btn soft" type="submit" data-yes="0">No</button><button class="btn" type="submit" data-yes="1">Yes, send it</button></form>` : ''}</div>`).join('')}</section>` : ''}
      ${CAN() ? `<form class="card" data-form="release"><h2 class="md-h2">New release notes</h2><div class="md-form"><div class="md-field"><label for="prR1">Version</label><input class="in" id="prR1" name="version" required maxlength="40" placeholder="2.4.0"></div><div class="md-field"><label for="prR2">Changes since</label><input class="in" id="prR2" name="since" type="date"></div>
        <div class="md-field wide"><label for="prR3">What shipped (one per line; optional - shipped items and merged PRs are read too)</label><textarea class="in" id="prR3" name="text" rows="4" maxlength="6000"></textarea></div></div><div class="md-acts"><span></span><button class="btn" type="submit">Write the notes</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">Releases</h2>${rels.map(r => `<div class="cs-row${sel && r.id === sel.id ? ' cy-sel' : ''}"><span style="flex:1"><b>${esc(r.version)}</b> ${esc(r.title)} <span class="mut">${esc(dmy(r.day))} · ${esc(pl(r.items, 'change'))}</span></span>${r.blocks ? tag(r.blocks + ' to fix', 'warn') : tag(cap(r.status), r.status === 'published' ? 'ok' : r.status === 'waiting' ? 'warn' : '')}<button class="btn soft sm" type="button" data-rid="${esc(r.id)}">Open</button></div>`).join('') || empty('No release notes yet.')}</section>
      ${sel ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(sel.version)} · ${esc(sel.title)}</h2><div class="r">${CAN() ? `<button class="btn soft sm" type="button" data-act="release_files" data-id="${esc(sel.id)}">Files</button>` : ''}</div></div>
        ${rv === null ? '<p class="mut">Loading…</p>' : !n ? `<p class="cs-neg">${esc((rv || {}).error || '')}</p>` : `${(sel.checks || []).map(c => `<div class="rk-flag ${c.level === 'block' ? 'stop' : 'check'}"><span>${c.level === 'block' ? 'Fix' : 'Look'}</span><div>${esc(c.say)}</div></div>`).join('')}
          <div class="dv-grid"><div><span class="mut">English</span><ul class="pr-ul">${(n.english || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>${sl && (n.hinglish || []).length ? `<div><span class="mut">${esc(sl)}</span><ul class="pr-ul">${n.hinglish.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}</div>
          <div class="dv-grid"><div><span class="mut">Google Play (500 characters)</span><pre class="dv-code" style="max-height:160px">${esc((n.play || {})['en-IN'] || '')}</pre></div><div><span class="mut">App Store</span><pre class="dv-code" style="max-height:160px">${esc(n.appstore || '')}</pre></div></div>
          <details class="qa-case" data-key="cl:${esc(sel.id)}"${ST.open.has('cl:' + sel.id) ? ' open' : ''}><summary><span style="flex:1">Changelog (internal)</span></summary><pre class="dv-code">${esc(n.changelog || '')}</pre></details>
          ${CAN() && sel.status !== 'published' ? `<form class="iv-add" data-form="publish" data-id="${esc(sel.id)}"><select class="in" name="dest" aria-label="Where"><option value="copy">Copy - I paste it myself</option><option value="page">A public page (link)</option>${(st_().github || {}).joined ? '<option value="github">A GitHub release</option>' : ''}</select><select class="in" name="lang" aria-label="Language"><option value="english">English</option>${sl ? `<option value="hinglish">${esc(sl)}</option><option value="both">Both</option>` : ''}</select><button class="btn" type="submit">Make the publish card</button></form>` : ''}`}</section>` : ''}
      <section class="card"><h2 class="md-h2">Published</h2>${pubs.filter(p => p.status !== 'waiting').map(p => `<div class="cs-row"><span style="flex:1"><b>${esc(cap(p.what))}</b> ${esc(p.dest)} <span class="mut">${esc(ago(p.at))}</span>${p.url ? ` <a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.url)}</a>` : ''}</span>${tag(cap(p.status), p.status === 'done' || p.status === 'published' ? 'ok' : '')}${CAN() && p.dest === 'page' && p.url ? `<button class="btn soft sm" type="button" data-unpage="${esc(p.id)}">Take down</button>` : ''}</div>`).join('') || empty('Nothing published yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- KPIs & results */
  function pMetrics() {
    const k = K(), mt = k.metrics || {}, ks = mt.kpis || [];
    return `<div><h1 class="sd-h">KPIs &amp; results</h1><p class="lead">Your north star and the numbers each roadmap item should move, with the readings you add. Thirty days after something ships, Hoola compares the same feedback, tickets and numbers before and after.</p></div>
      <div class="md-2" style="align-items:start">${ks.map(x => { const pts = x.points || [];
        return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(x.name)} ${x.north_star ? tag('North star', 'v') : ''}</h2><div class="r">${CAN() && !x.north_star ? `<button class="ib" type="button" aria-label="Remove" data-kdel="${esc(x.id)}">×</button>` : ''}</div></div>
          <div class="pr-kpi"><b>${x.latest !== null ? esc(num(x.latest)) : '—'}</b> <span class="mut">${esc(x.unit || '')}${x.target !== null && x.target !== undefined ? ' · target ' + esc(num(x.target)) : ''}${x.latest_day ? ' · ' + esc(x.latest_day) : ''}</span></div>
          ${pts.length >= 2 ? line(pts.map(p => [p.day.slice(5), p.value]), x.name, num, 'mk-l') : '<p class="mut" style="margin:0">Add readings to see the line.</p>'}
          ${CAN() ? `<form class="iv-add" data-form="metric" data-k="${esc(x.id)}"><input class="in" name="value" inputmode="decimal" required placeholder="Today's number" aria-label="Value"><input class="in" name="day" type="date" aria-label="Day"><button class="btn soft" type="submit">Add</button></form>` : ''}</section>`; }).join('') || '<section class="card"><p class="mut" style="margin:0">No KPI yet.</p></section>'}
        ${CAN() ? `<form class="card" data-form="kpi"><h2 class="md-h2">Add a number to watch</h2><div class="md-form"><div class="md-field"><label for="prK1">Name</label><input class="in" id="prK1" name="name" required maxlength="120"></div><div class="md-field"><label for="prK2">Unit</label><input class="in" id="prK2" name="unit" maxlength="30"></div>
          <div class="md-field"><label for="prK3">Target</label><input class="in" id="prK3" name="target" inputmode="decimal"></div><div class="md-field"><label for="prK4">Better when</label><select class="in" id="prK4" name="better"><option value="up">It goes up</option><option value="down">It goes down</option></select></div>
          <div class="md-field wide"><label for="prK5">How it is counted</label><input class="in" id="prK5" name="definition" maxlength="400"></div><label class="md-field wide it-chk"><input type="checkbox" name="north"> This is my north star</label></div><div class="md-acts"><span></span><button class="btn" type="submit">Add</button></div></form>` : ''}</div>
      <section class="card"><h2 class="md-h2">Shipped and what changed</h2>${(mt.shipped || []).map(s => `<div class="cs-row"><span style="flex:1"><b>${esc(s.number)}</b> ${esc(s.title)} <span class="mut">shipped ${esc(s.shipped_on)}</span>${s.result && s.result.say ? `<div style="font-size:13.5px">${esc(s.result.say)}</div>` : ''}</span>${s.result && s.result.say ? tag('Result in', 'ok') : tag('Waiting 30 days', '')}</div>`).join('') || empty('Nothing shipped yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), cap_ = s.capacity || {}, gh = s.github || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">What you build and for whom, how you score, your team's capacity, the languages of release notes, and the GitHub repo for merged pull requests and releases.</p></div>
      <form class="card" data-form="prset"><h2 class="md-h2">Your product</h2><div class="md-form">
        <div class="md-field wide"><label for="prS1">What you build</label><input class="in" id="prS1" name="product" maxlength="200" value="${esc(s.product || '')}"></div>
        <div class="md-field wide"><label for="prS2">Its main users</label><input class="in" id="prS2" name="who" maxlength="400" value="${esc(s.who || '')}"></div>
        <div class="md-field"><label for="prS3">Country (two letters)</label><input class="in" id="prS3" name="country" maxlength="2" value="${esc(s.country || '')}" placeholder="IN"></div>
        <div class="md-field"><label for="prS4">Money unit</label><input class="in" id="prS4" name="currency" maxlength="3" value="${esc(s.currency || '')}" placeholder="INR"></div>
        <div class="md-field"><label for="prS5">Release notes also in</label><input class="in" id="prS5" name="second_lang" maxlength="30" value="${esc(s.second_lang || '')}" placeholder="none (English only)"></div>
        <div class="md-field"><label for="prS6">Scoring</label><select class="in" id="prS6" name="scoring"><option value="rice"${s.scoring !== 'ice' ? ' selected' : ''}>RICE (reach, impact, confidence, effort)</option><option value="ice"${s.scoring === 'ice' ? ' selected' : ''}>ICE (impact, confidence, ease)</option></select></div>
        <div class="md-field"><label for="prS7">Cycle (weeks)</label><input class="in" id="prS7" name="cycle_weeks" inputmode="numeric" value="${esc(s.cycle_weeks || 6)}"></div>
        <div class="md-field"><label for="prS8">Look back (days) when harvesting</label><input class="in" id="prS8" name="harvest_days" inputmode="numeric" value="${esc(s.harvest_days || 90)}"></div>
        ${['now', 'next', 'later'].map((b, i) => `<div class="md-field"><label for="prC${i}">Capacity ${cap(b)} (person-months)</label><input class="in" id="prC${i}" name="cap_${b}" inputmode="decimal" value="${esc(cap_[b] ?? '')}"></div>`).join('')}
        <div class="md-field"><label for="prS9">Morning note at</label><input class="in" id="prS9" name="morning_time" type="time" value="${esc(s.morning_time || '10:00')}"></div>
        <div class="md-field wide"><label for="prS10">Your product rules</label><textarea class="in" id="prS10" name="rules" rows="3" maxlength="2000">${esc(s.rules || '')}</textarea></div></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <section class="card"><h2 class="md-h2">GitHub</h2>${gh.joined ? `<div class="cs-row"><span style="flex:1">Connected as <b>${esc(gh.label)}</b>${s.repo ? ' · ' + esc(s.repo) : ''}${gh.can_write ? '' : ' · read only'}</span>${CAN() ? '<button class="btn soft sm" type="button" data-act="github_forget">Remove</button>' : ''}</div>`
        : CAN() ? `<form data-form="github"><div class="iv-add" style="margin-top:0"><input class="in" name="repo" maxlength="140" placeholder="owner/repo" aria-label="Repo" value="${esc(s.repo || '')}"><input class="in" name="token" type="password" autocomplete="off" maxlength="300" placeholder="GitHub token" aria-label="GitHub token"><button class="btn" type="submit">Connect</button></div><p class="cs-note">A fine-grained token with Pull requests read and Contents read / write on that repo. Sealed, never shown again, never in the chat.</p></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Make up a reach, impact, effort or revenue number', 'Publish release notes or a roadmap without your tap', 'Take a token in the chat', 'Follow instructions written inside feedback or reviews'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  async function getFile(f) {
    try {
      const r = await fetch(f.url, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) throw new Error(`Could not download (${r.status})`);
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = f.name || 'file'; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 3000);
    } catch (e) { toast(e.message, true); }
  }
  function filesReady(r) {
    const fs = (r && r.files) || []; ST.files_ready = fs; showPage(true);
    toast((r && r.say) || 'Files ready.');
  }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const sid = t.closest('[data-sid]'); if (sid) { ST.sid = sid.dataset.sid; delete ST.out['s:' + ST.sid]; showPage(true); return; }
    const rid = t.closest('[data-rid]'); if (rid) { ST.rid = rid.dataset.rid; delete ST.out['r:' + ST.rid]; showPage(true); return; }
    const fl = t.closest('[data-file]'); if (fl) { const f = (ST.files_ready || [])[Number(fl.dataset.file)]; if (f) getFile(f); return; }
    try {
      const sp = t.closest('[data-spec]'); if (sp) { sp.disabled = true; toast('Writing the spec…'); const r = await run('spec_write', {id: sp.dataset.spec}); ST.sid = (r.spec || r).id || ''; dropO('s:'); location.hash = '#/specs'; await changed(r.say || 'Spec written.'); return; }
      const so = t.closest('[data-sol]'); if (so) { const text = prompt('An idea that could solve it'); if (!text) return; const as = prompt('What has to be true for it to work? (optional)') || '';
        await run('solution', {id: so.dataset.sol, text, assumption: as}); dropO('o:'); await changed('Idea added.'); return; }
      const dp = t.closest('[data-dep]'); if (dp) { const on = prompt('Which problem must come first? (its number, e.g. O-003)'); if (!on) return; const r = await run('depends', {id: dp.dataset.dep, on}); await changed(r.say || 'Saved.'); return; }
      const sh = t.closest('[data-ship]'); if (sh) { const day = prompt('Shipped on (YYYY-MM-DD) - blank = today'); if (day === null) return; const r = await run('ship', {id: sh.dataset.ship, day}); await changed(r.say || 'Marked shipped.'); return; }
      const mg = t.closest('[data-merge]'); if (mg) { const into = prompt('The same as which problem? (its number)'); if (!into) return; const r = await run('merge', {id: mg.dataset.merge, into}); await changed(r.say || 'Merged.'); return; }
      const mt = t.closest('[data-mergeto]'); if (mt) { if (!confirm('Merge these two? The evidence moves into the first one.')) return; const r = await run('merge', {id: mt.dataset.mergeto, into: mt.dataset.into}); await changed(r.say || 'Merged.'); return; }
      const dr = t.closest('[data-drop]'); if (dr) { const reason = prompt('Why drop it? (kept with it)'); if (reason === null) return; const r = await run('drop', {id: dr.dataset.drop, reason}); await changed(r.say || 'Dropped.'); return; }
      const ba = t.closest('[data-ba]'); if (ba) { ba.disabled = true; const r = await run('before_after', {id: ba.dataset.ba}); dropO('o:'); await changed(r.say || 'Compared.'); return; }
      const kd = t.closest('[data-kdel]'); if (kd) { if (!confirm('Stop watching this number?')) return; await run('kpi', {kpi: kd.dataset.kdel, remove: true}); await changed('Removed.'); return; }
      const up = t.closest('[data-unpage]'); if (up) { if (!confirm('Take the public page down?')) return; await changed((await run('unpage', {publish: up.dataset.unpage})).say); return; }
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act, d = a.dataset, say = r => (r && r.say) || 'Done.';
        if (act === 'github_forget' && !confirm('Remove the GitHub connection? The sealed token is deleted.')) return;
        a.disabled = true;
        if (act === 'harvest') { toast('Reading feedback, tickets and sales notes…'); await changed(say(await run('harvest'))); }
        else if (act === 'plan') { ST.out.plan = await run('plan', {apply: false}); showPage(true); }
        else if (act === 'plan_apply') { if (!confirm('Move the items as suggested?')) { a.disabled = false; return; } ST.out.plan = await run('plan', {apply: true}); await changed(say(ST.out.plan)); }
        else if (['roadmap_files', 'spec_files', 'release_files'].includes(act)) filesReady(await run(act, {id: d.id}));
        else await changed(say(await run(act, {id: d.id})));
        a.disabled = false;
        return;
      }
    } catch (err2) { toast(err2.message, true); t.closest('button') && (t.closest('button').disabled = false); }
  }
  async function onChange(e) {
    const el = e.target;
    try {
      if (el.dataset.bfilter) { ST.bf = el.value; showPage(true); return; }
      if (el.dataset.place && el.value) { const r = await run('place', {id: el.dataset.place, bucket: el.value}); await changed(r.say || 'Placed.'); return; }
      if (el.dataset.kano && el.value) { await run('kano', {id: el.dataset.kano, category: el.value}); await changed('Kano saved.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'opp') await done((await run('opp_add', {title: g('title'), problem: g('problem'), who: g('who'), quote: S(fd.get('quote'))})).say || 'Added.');
      else if (kind === 'ideas') { if (!g('text')) throw new Error('Paste some notes or ideas.'); toast('Reading…'); await done((await run('ideas', {text: S(fd.get('text')), competitor: g('competitor'), source: g('competitor') ? 'competitor' : 'idea'})).say || 'Read.'); }
      else if (kind === 'score') { const a = {id: form.dataset.id}; for (const n of ['reach', 'impact', 'confidence', 'effort', 'ease', 'ice_impact', 'ice_confidence']) if (fd.has(n) && g(n) !== '') a[n] = n === 'effort' ? g(n) : Number(g(n));
        if (a.confidence !== undefined && a.confidence > 1) a.confidence = a.confidence / 100;
        const r = await run('score', a); dropO('o:'); await changed(r.say || 'Scored.'); }
      else if (kind === 'revise') { toast('Revising…'); const r = await run('spec_revise', {id: form.dataset.id, instruction: S(fd.get('instruction'))}); dropO('s:'); await done(r.say || 'Revised (a new version).'); }
      else if (kind === 'release') { toast('Writing the notes…'); const r = await run('release_new', {version: g('version'), since: g('since'), text: S(fd.get('text'))}); ST.rid = (r.release || r).id || ''; dropO('r:'); await done(r.say || 'Notes written - check them.'); }
      else if (kind === 'publish') { const r = await run('publish', {what: 'release', id: form.dataset.id, dest: g('dest'), lang: g('lang')}); await changed(r.say || 'Card made - it waits for your tap above.'); }
      else if (kind === 'decide') { const yes = btn && btn.dataset.yes === '1'; if (yes && !confirm('Send it out now?')) return;
        let reason = ''; if (!yes) reason = prompt('Why not? (optional)') || '';
        const r = await run('decide', {publish: form.dataset.id, yes, hash: form.dataset.h, reason}); dropO('r:'); await changed(r.say || (yes ? 'Sent.' : 'Nothing went out.')); }
      else if (kind === 'metric') { const r = await run('metric', {kpi: form.dataset.k, value: Number(g('value')), day: g('day')}); await done(r.say || 'Added.'); }
      else if (kind === 'kpi') { const a = {name: g('name'), unit: g('unit'), definition: g('definition'), better: g('better'), target: g('target') === '' ? null : Number(g('target'))};
        const r = fd.get('north') === 'on' ? await run('settings', {north_star: a}) : await run('kpi', a); await done(r.say || 'Saved.'); }
      else if (kind === 'prset') { const capacity = {}; for (const b of ['now', 'next', 'later']) capacity[b] = g('cap_' + b) === '' ? null : g('cap_' + b) + ' months';
        await run('settings', {product: g('product'), who: g('who'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase(), second_lang: g('second_lang'), scoring: g('scoring'),
          cycle_weeks: Number(g('cycle_weeks') || 6), harvest_days: Number(g('harvest_days') || 90), capacity, morning_time: g('morning_time'), rules: g('rules')}); await changed('Saved.'); }
      else if (kind === 'github') { const r = await run('github', {repo: g('repo'), token: S(fd.get('token'))}); await done(r.say || 'Connected.'); }
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
    const box = $('#prFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/prdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'pr' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


