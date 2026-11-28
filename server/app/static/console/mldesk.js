/* ML DESK - the Machine Learning Engineer's own section, like the finance desks (owner: "Machine Learning Engineer same as finance
   desks"). A thin top bar, then the ML chat (its own conversation, kind 'ml') beside the desk's pages: Today, Training, Data, Drift,
   Errors, Sizing, CI check, Settings. The pages call /api/mldesk/do/<part>; nothing runs on her machines. */
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

  const TABS = [['today', 'Today'], ['training', 'Training'], ['data', 'Data'], ['drift', 'Drift'], ['errors', 'Errors'], ['sizing', 'Sizing'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start with a model that is not good enough?', 'How should I split my data?', 'Which metric should I watch?'],
    training: ['Is my model overfitting?', 'What learning rate should I try?', 'When should training stop?'],
    data: ['How do I handle missing values?', 'Is this column leaking the answer?', 'What do I do with imbalanced classes?'],
    drift: ['How often should I check drift?', 'What PSI means I should retrain?', 'Drift or a broken pipeline?'],
    errors: ['MAE, RMSE or MAPE?', 'How do I beat the naive forecast?', 'Why is my bias not zero?'],
    sizing: ['Will a 70B model fit on two GPUs?', 'LoRA or full fine-tuning?', 'How long will training take?'],
    ci: ['How do I keep a fixed test set?', 'How much drop should I allow?', 'Can CI run on a GPU?'],
    settings: ['What is MFU?', 'What season length should I use?', 'What goes in the metrics file?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'training', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.mldesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.mldesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'ml', name: 'ML'} : null;
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
  const run = (part, a) => api('POST', '/api/mldesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/mldesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Machine Learning Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="mlHire">Hire the Machine Learning Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#mlHire').onclick = async () => { try { await api('POST', '/api/employees/ml_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">ML</div><div class="sd-site" id="mlSite"></div></div>
          <span id="mlState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="ML chat">
          <div class="sd-chathead"><div class="t"><b>ML chat</b><span>Paste a training log, a table, predictions or a model - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mlFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mlPick" multiple hidden accept=".txt,.json,.csv,.tsv,.yaml,.yml,.log,.md,.py,.ipynb,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="ML desk" id="sdTabs"></nav>
          <div id="mlPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a log or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mlPick').click()});
    $('#mlPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.mldesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.mldesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/mldesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#mlPage').addEventListener('click', onPageClick);
    $('#mlPage').addEventListener('submit', onSubmit);
    $('#mlPage').addEventListener('change', onChange);
    $('#mlPage').addEventListener('input', onInput);
    $('#mlPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#mlState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#mlSite').textContent = [s.target && 'target ' + s.target, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/mldesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#mlPage'); if (!box) return;
    const fn = {today: pToday, training: pTraining, data: pData, drift: pDrift, errors: pErrors, sizing: pSizing, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="mlk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {run: 'Training', data: 'Data', drift: 'Drift', regress: 'Errors', sizing: 'Sizing'};
  const ROUTE = {run: 'training', data: 'data', drift: 'drift', regress: 'errors', sizing: 'sizing'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(1);
  const GB = v => (v === null || v === undefined) ? '—' : (Number(v) >= 100 ? Number(v).toFixed(0) : Number(v).toFixed(1)) + ' GB';
  const big = v => { const n = Number(v); return n >= 1e12 ? P4(n / 1e12) + 'T' : n >= 1e9 ? P4(n / 1e9) + 'B' : n >= 1e6 ? P4(n / 1e6) + 'M' : num(n); };
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'run': return `${pl(b.points || 0, b.x || 'point')}${b.best !== null && b.best !== undefined ? ` · best validation loss ${P4(b.best)} at ${b.x} ${P4(b.best_at)}` : ''}`;
      case 'data': return `${num(b.rows)} rows · ${pl(b.columns || 0, 'column')}${b.target ? ' · target ' + b.target : ''}`;
      case 'drift': return `${num(b.moved)} of ${pl(b.cols || 0, 'column')} moved${b.top ? ` · most: ${b.top[0]} (PSI ${P4(b.top[1])})` : ''}`;
      case 'regress': return `MAE ${P4(b.mae)} · RMSE ${P4(b.rmse)}${b.r2 !== null && b.r2 !== undefined ? ' · R² ' + Number(b.r2).toFixed(3) : ''} · ${pl(b.n || 0, 'prediction')}`;
      case 'sizing': return `${big(b.params)} parameters · ${GB(b.weights)} of weights${b.total ? ' · ' + GB(b.total) + ' to serve' : ''}${b.fits === true ? ' · fits' : b.fits === false ? ' · does not fit' : ''}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="mlk-list">${list.map(x => `<button type="button" class="mlk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="mlk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="mlk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="mlk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="mlk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono mlk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft mlk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="mlk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card mlk-sum ${ok ? 'okv' : 'badv'}"><p class="mlk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="mlk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="mlk-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="mlk-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="mlk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  const sci = v => { const [m, e] = Number(v).toExponential(2).split('e'); return `${+m}e${+e}`; };
  const PSI = v => tag(P4(v), v > (st_().psi_alarm || 0.25) ? 'bad' : v > (st_().psi_warn || 0.1) ? 'warn' : 'ok');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), r = k.run, dt = k.data, f = k.drift, e = k.regress, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Training', r && r.best !== null && r.best !== undefined ? esc(P4(r.best)) + '<small> val loss</small>' : '—', r ? `best at ${r.x} ${P4(r.best_at)} · ${r.number}` : 'paste a training log', r && r.bad),
      tile('Data', dt ? (dt.bad ? esc(num(dt.issues)) + ' <small>to fix</small>' : 'Clean') : '—', dt ? `${num(dt.rows)} rows · ${dt.number}` : 'paste a table', dt && dt.bad),
      tile('Drift', f ? esc(num(f.moved)) + ' <small>of ' + esc(num(f.cols)) + ' moved</small>' : '—', f ? `${f.top ? 'most: ' + f.top[0] + ' · ' : ''}${f.number}` : 'paste two samples', f && f.bad),
      tile('Errors', e ? esc(P4(e.mae)) + '<small> MAE</small>' : '—', e ? `${e.r2 !== null && e.r2 !== undefined ? 'R² ' + Number(e.r2).toFixed(3) + ' · ' : ''}${e.number}` : 'paste predictions', e && e.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.target ? 'Target: ' + s.target + '.' : 'Set your target column in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="mlk-path">
        <li><button type="button" data-go="data"><b>Trust the data</b><span>Missing values, ID columns, duplicates and columns that give the answer away</span></button></li>
        <li><button type="button" data-go="training"><b>Train it well</b><span>The best epoch, overfitting, a learning rate too high, when to stop</span></button></li>
        <li><button type="button" data-go="errors"><b>Score it honestly</b><span>Errors against the baselines it must beat, by group, with interval coverage</span></button></li>
        <li><button type="button" data-go="drift"><b>Watch it live</b><span>Production data against training data, column by column, before accuracy drops</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- training */
  const SAMPLE_RUN = "epoch,loss,val_loss,val_accuracy,lr\n1,1.62,1.70,0.61,0.001\n2,1.21,1.33,0.68,0.001\n3,0.95,1.12,0.72,0.001\n4,0.77,1.05,0.74,0.001\n...";
  function pTraining() {
    if (ST.arg) return one(ST.arg, 'training', pRn);
    const s = st_();
    return `<div><h1 class="sd-h">Training</h1><p class="lead">A training run read from its log: the best epoch, overfitting, a loss that diverges or stalls, a learning rate that is too high, and when early stopping would have stopped.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a run</h2><form data-form="run" class="mlk-grid">
        ${area('text', 'A CSV of epochs (loss, val_loss, metrics, lr) - or the lines Keras, PyTorch Lightning, Hugging Face or your own loop prints', SAMPLE_RUN, 12)}
        ${fld('patience', 'Early-stopping patience (epochs)', s.patience, 'type="number" min="1" step="1"')}${subRow('Read it', '.csv,.log,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('run'))}</section>`;
  }
  function pRn(d) {
    const r = d.result || {}, se = r.series || {}, b = r.best, x = r.x || 'epoch';
    const lossS = [r.train && {name: r.train, pts: se[r.train] || [], cls: 'c2'}, r.val && {name: r.val, pts: se[r.val] || [], cls: 'c1'}].filter(Boolean);
    const metS = (r.metrics || []).slice(0, 4).map((m, i) => ({name: m, pts: se[m] || [], cls: CL[(i + 2) % 6]}));
    return `${head(d, 'training')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Best validation loss', b ? esc(P4(b.val)) : '—', b ? `at ${x} ${P4(b.at)}` : 'no validation loss in the log')}${tile('Since the best', b ? esc(num(r.since_best)) + ' <small>' + esc(x) + 's</small>' : '—', r.early_stop !== undefined ? `early stopping would stop at ${P4(r.early_stop)}` : '', b && r.since_best >= (st_().patience || 5))}${tile('Training loss fell', r.train_drop !== undefined ? esc(Math.round(r.train_drop)) + '<small>%</small>' : '—', 'from start to end')}${tile('Gap at the end', r.gap ? esc(P4(r.gap.at_end)) : '—', r.gap ? `validation minus training (${P4(r.gap.at_best)} at the best)` : '')}</div></section>
      <section class="card"><h2 class="md-h2">Loss</h2>${lines(lossS, x, 'loss', 'Training and validation loss', {})}${b ? `<p class="cs-note">Keep the checkpoint from ${esc(x)} ${esc(P4(b.at))}.</p>` : ''}</section>
      ${metS.length ? `<section class="card"><h2 class="md-h2">Metrics</h2>${lines(metS, x, '', 'Validation metrics', {})}${r.metric_best ? stats(Object.entries(r.metric_best).map(([k2, v]) => [k2, `${P4(v.value)} at ${P4(v.at)}`])) : ''}</section>` : ''}
      ${r.lr && se[r.lr] ? `<section class="card"><h2 class="md-h2">Learning rate</h2>${lines([{name: r.lr, pts: se[r.lr], cls: 'c3'}], x, '', 'Learning rate', {})}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mlk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- data */
  const SAMPLE_DATA = "customer_id,age,income,city,plan,churned,split\n1001,34,52000,Pune,b,0,train\n1002,51,,Lagos,c,1,train\n1003,27,31000,Berlin,a,0,test";
  function pData() {
    if (ST.arg) return one(ST.arg, 'data', pDa);
    const s = st_();
    return `<div><h1 class="sd-h">Data</h1><p class="lead">A training table profiled before modelling: each column's type and gaps, ID-like and constant columns, duplicates, the target's balance, columns that give the answer away, and the shift between train and test.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Profile a table</h2><form data-form="data" class="mlk-grid">
        ${area('text', 'A CSV with a header row (up to 300,000 rows) - include a train / test column to see the shift between them', SAMPLE_DATA, 10)}
        ${fld('target', 'Target column', s.target, '', 'churned')}${fld('split', 'Train / test column', s.split_col, '', 'split')}${subRow('Profile it', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Profiled</h2>${itemRows(items('data'))}</section>`;
  }
  function pDa(d) {
    const r = d.result || {}, cols = r.cols || [], t = r.target, bad = new Set((r.issues || []).filter(i => i.sev !== 'info').map(i => i.fn));
    return `${head(d, 'data')}${verdict(r, isOk(r))}
      <section class="card">${stats([['Rows', num(r.rows)], ['Columns', r.columns], ['Duplicated rows', num(r.duplicates), r.duplicates ? 'warn' : ''], ['Numbers', cols.filter(c => c.kind === 'number').length], ['Categories', cols.filter(c => c.kind === 'category').length], ['Mostly empty', cols.filter(c => c.missing > 0.5).length]])}</section>
      ${t ? `<section class="card"><h2 class="md-h2">The target: ${esc(r.target_name)}</h2>${t.type === 'classes' ? bars(t.counts.map(([k2, v]) => [k2, v, 'mlk-b', `${(v / r.rows * 100).toFixed(1)}%`]), v => num(v), 'Rows by class') : stats([['Mean', P4(t.mean)], ['Median', P4(t.median)], ['Spread (sd)', P4(t.sd)], ['Min', P4(t.min)], ['Max', P4(t.max)], ['Skew', P4(t.skew)]])}</section>` : ''}
      <section class="card"><h2 class="md-h2">Columns</h2><div class="iv-tw"><table class="tb in-cards mlk-t"><thead><tr><th>Column</th><th>Type</th><th class="r">Missing</th><th class="r">Distinct</th><th>Range or top values</th>${t ? '<th class="r">With target</th>' : ''}</tr></thead><tbody>${cols.map(c => `<tr class="${bad.has(c.name) ? 'warn' : ''}"><td><b>${esc(c.name)}</b>${c.target ? ' <span class="cs-tag">target</span>' : ''}${c.id ? ' <span class="cs-tag">ID</span>' : ''}</td><td>${esc(c.kind)}</td><td class="r"><div class="mlk-meter" style="width:70px;display:inline-block;vertical-align:middle;margin-right:6px"><i class="${c.missing > 0.5 ? 'bad' : c.missing > 0.05 ? 'warn' : ''}" style="width:${(c.missing * 100).toFixed(1)}%"></i></div>${esc((c.missing * 100).toFixed(1))}%</td><td class="r">${esc(num(c.unique))}</td><td class="mut">${c.kind === 'number' ? esc(`${P4(c.min)} to ${P4(c.max)} · median ${P4(c.median)}`) : esc((c.top || []).slice(0, 3).map(([v, p]) => `${v} ${(p * 100).toFixed(0)}%`).join(', '))}</td>${t ? `<td class="r">${c.corr_target !== undefined && c.corr_target !== null ? esc(Number(c.corr_target).toFixed(3)) : ''}</td>` : ''}</tr>`).join('')}</tbody></table></div></section>
      ${r.split && r.split.drift ? `<section class="card"><h2 class="md-h2">Train against test</h2>${stats(Object.entries(r.split.counts).map(([k2, v]) => [cap(k2) + ' rows', num(v)]))}${bars(r.split.drift.slice(0, 15).map(x => [x.name, x.psi, x.psi > 0.25 ? 'mlk-b warn' : 'mlk-b', 'PSI']), v => P4(v), 'Shift by column')}</section>` : ''}
      ${(r.redundant || []).length ? `<section class="card"><h2 class="md-h2">Features that say the same thing</h2><div class="iv-tw"><table class="tb in-cards mlk-t"><thead><tr><th>Feature</th><th>Feature</th><th class="r">Correlation</th></tr></thead><tbody>${r.redundant.map(p => `<tr><td>${esc(p.a)}</td><td>${esc(p.b)}</td><td class="r">${esc(Number(p.r).toFixed(3))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mlk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- drift */
  const SAMPLE_REF = "age,income,city\n34,52000,Pune\n51,61000,Lagos\n27,31000,Berlin";
  function pDrift() {
    if (ST.arg) return one(ST.arg, 'drift', pDr);
    const s = st_();
    return `<div><h1 class="sd-h">Drift</h1><p class="lead">Production data compared with the data the model learnt from, column by column - so a shift is caught before the accuracy quietly drops.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Compare two samples</h2><form data-form="drift" class="mlk-grid">
        ${area('text', 'The reference: a sample of the training data (CSV with a header)', SAMPLE_REF, 8)}
        ${area('current', 'The current data: recent production inputs, the same columns', SAMPLE_REF, 8)}
        ${fld('psi_warn', 'PSI to watch', s.psi_warn, 'type="number" min="0.01" step="any"')}${fld('psi_alarm', 'PSI to act on', s.psi_alarm, 'type="number" min="0.01" step="any"')}
        ${subRow('Compare', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Compared</h2>${itemRows(items('drift'))}</section>`;
  }
  function pDr(d) {
    const r = d.result || {}, cols = r.columns || [];
    const top = cols.find(c => c.bins) || null;
    return `${head(d, 'drift')}${verdict(r, isOk(r))}
      <section class="card">${stats([['Reference rows', num(r.ref_rows)], ['Current rows', num(r.cur_rows)], ['Columns compared', cols.length], ['Moved a lot', cols.filter(c => c.state === 'bad').length, cols.some(c => c.state === 'bad') ? 'bad' : ''], ['Moved a little', cols.filter(c => c.state === 'warn').length]])}</section>
      <section class="card"><h2 class="md-h2">Each column, most moved first</h2><div class="iv-tw"><table class="tb in-cards mlk-t"><thead><tr><th>Column</th><th>Type</th><th class="r">PSI</th><th class="r">KS</th><th class="r">p-value</th><th class="r">Mean moved</th><th class="r">Missing</th></tr></thead><tbody>${cols.map(c => `<tr class="${c.state === 'ok' ? '' : c.state}"><td><b>${esc(c.name)}</b></td><td>${esc(c.kind)}</td><td class="r">${PSI(c.psi)}</td><td class="r">${c.ks !== undefined ? esc(P4(c.ks)) : '—'}</td><td class="r">${c.p !== undefined ? esc(c.p < 1e-4 ? '< 0.0001' : P4(c.p)) : '—'}</td><td class="r">${c.shift_sd !== undefined ? esc((c.shift_sd > 0 ? '+' : '') + Number(c.shift_sd).toFixed(2)) + ' sd' : '—'}</td><td class="r">${esc((c.missing_ref * 100).toFixed(1))}% → ${esc((c.missing_cur * 100).toFixed(1))}%</td></tr>`).join('')}</tbody></table></div></section>
      ${top ? `<section class="card"><h2 class="md-h2">${esc(top.name)}: reference against current</h2><div class="iv-tw"><table class="tb in-cards mlk-t"><thead><tr><th>${top.kind === 'number' ? 'Range' : 'Value'}</th><th class="r">Reference</th><th class="r">Current</th><th style="min-width:160px"></th></tr></thead><tbody>${top.bins.map(b => `<tr><td>${top.kind === 'number' ? esc(`${Number.isFinite(b.lo) ? P4(b.lo) : 'below'} to ${Number.isFinite(b.hi) ? P4(b.hi) : 'above'}`) : esc(b.value) + (b.new ? ' <span class="cs-tag">new</span>' : '')}</td><td class="r">${esc((b.ref * 100).toFixed(1))}%</td><td class="r">${esc((b.cur * 100).toFixed(1))}%</td><td><div class="mlk-pair"><i class="a" style="width:${(b.ref * 100).toFixed(1)}%"></i><i class="b" style="width:${(b.cur * 100).toFixed(1)}%"></i></div></td></tr>`).join('')}</tbody></table></div><p class="cs-note">Upper bar: the reference; lower bar: the current data.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mlk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 50000), 'code')}${pre(S((d.inputs || {}).current).slice(0, 50000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- errors */
  const SAMPLE_REG = "date,store,actual,predicted,p10,p90\n2026-03-01,A,120,114,101,128\n2026-03-01,B,310,322,298,346\n2026-03-02,A,131,127,113,140";
  function pErrors() {
    if (ST.arg) return one(ST.arg, 'errors', pEr);
    const s = st_();
    return `<div><h1 class="sd-h">Errors</h1><p class="lead">Regression and forecast errors measured honestly: MAE, RMSE, WAPE, bias, and whether the model beats the simple baselines it must beat - by group, with interval coverage.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Score predictions</h2><form data-form="regress" class="mlk-grid">
        ${area('text', 'A CSV with the actual and predicted values - and if you have them a date, a group (store, product, region) and the interval bounds (p10 / p90)', SAMPLE_REG, 10)}
        ${fld('actual', 'Actual column (if not named actual)', s.actual_col)}${fld('predicted', 'Predicted column (if not named predicted)', s.pred_col)}${fld('group', 'Group column', s.group_col, '', 'store')}${fld('season', 'Season length for the naive forecast', s.season, 'type="number" min="1" step="1"')}
        ${subRow('Score it', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Scored</h2>${itemRows(items('regress'))}</section>`;
  }
  function pEr(d) {
    const r = d.result || {}, cal = r.calibration || [], g = r.groups || [];
    const pts = r.points || [], mx = Math.max(...pts.flat()), mn = Math.min(...pts.flat(), 0);
    return `${head(d, 'errors')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('MAE', esc(P4(r.mae)), `median ${P4(r.medae)}, 90% under ${P4(r.p90ae)}`)}${tile('RMSE', esc(P4(r.rmse)), `predicting the mean: ${P4(r.mean_rmse)}`)}${tile('R²', r.r2 === null || r.r2 === undefined ? '—' : esc(Number(r.r2).toFixed(3)), 'share of the variation explained', r.r2 !== null && r.r2 < 0)}${tile(r.mase !== undefined ? 'MASE' : 'WAPE', r.mase !== undefined ? esc(P4(r.mase)) : r.wape !== null ? esc(P4(r.wape)) + '<small>%</small>' : '—', r.mase !== undefined ? 'under 1 beats the naive forecast' : 'total error over total actual', r.mase > 1)}</div></section>
      <section class="card">${stats([['MAPE', r.mape === null || r.mape === undefined ? 'zeros in actuals' : P4(r.mape) + '%'], ['sMAPE', P4(r.smape) + '%'], ['WAPE', r.wape === null ? '—' : P4(r.wape) + '%'], ['Bias', (r.bias > 0 ? '+' : '') + P4(r.bias), Math.abs(r.bias) > 0.1 * r.mae ? 'warn' : ''], ['Largest error', P4(r.maxae)], ['Rows', num(r.n)], ...(r.interval ? [['Interval holds', (r.interval.coverage * 100).toFixed(1) + '%']] : [])])}</section>
      <section class="card"><h2 class="md-h2">Predicted against actual</h2>${scatter(pts, mn, mx)}</section>
      <section class="card"><h2 class="md-h2">Calibration</h2>${lines([{name: 'perfect', pts: [[mn, mn], [mx, mx]], cls: 'c5', dash: true}, {name: 'average actual for each tenth of predictions', pts: cal.map(c => [c.pred, c.actual]), cls: 'c1'}], 'predicted', 'actual', 'Calibration', {})}</section>
      ${g.length ? `<section class="card"><h2 class="md-h2">By ${esc(r.columns.group)}</h2><div class="iv-tw"><table class="tb in-cards mlk-t"><thead><tr><th>${esc(cap(r.columns.group))}</th><th class="r">Rows</th><th class="r">MAE</th><th class="r">WAPE</th><th class="r">Bias</th></tr></thead><tbody>${g.map(x => `<tr class="${r.wape && x.wape > 2 * r.wape && x.n >= 5 ? 'warn' : ''}"><td><b>${esc(x.group)}</b></td><td class="r">${esc(num(x.n))}</td><td class="r">${esc(P4(x.mae))}</td><td class="r">${esc(P4(x.wape))}%</td><td class="r">${esc((x.bias > 0 ? '+' : '') + P4(x.bias))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Errors (predicted minus actual)</h2>${bars((r.err_hist || []).map(([lo, c]) => [P4(lo), c, 'mlk-b', '']), v => num(v), 'Error histogram')}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mlk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }
  function scatter(pts, mn, mx) {
    if (!pts.length) return '';
    const W = 520, H = 360, L = 54, B = 36, R = 12, T0 = 10, sp = (mx - mn) || 1;
    const X = v => L + (v - mn) / sp * (W - L - R), Y = v => T0 + (1 - (v - mn) / sp) * (H - T0 - B);
    const tk = nice(mn, mx);
    return `<div class="mlk-scatter"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Predicted against actual">${tk.map(v => `<line class="g" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${esc(P4(v))}</text><text class="tx" x="${X(v).toFixed(1)}" y="${H - B + 16}" text-anchor="middle">${esc(P4(v))}</text>`).join('')}<line class="id" x1="${X(mn)}" y1="${Y(mn)}" x2="${X(mx)}" y2="${Y(mx)}"/>${pts.map(([a, p]) => `<circle cx="${X(a).toFixed(1)}" cy="${Y(p).toFixed(1)}" r="2.6"/>`).join('')}<text class="lab" x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">actual</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">predicted</text></svg><p class="mut" style="margin:4px 0 0;font-size:13px;text-align:center">Points on the dashed line are exact; above it the model predicted too much.</p></div>`;
  }

  /* ---------------------------------------------------------------- sizing */
  const SAMPLE_SZ = "model 8B bf16 layers=32 kv_heads=8 head_dim=128\nserve context=8192 batch=16\ngpu h100 x1\ntrain lora rank=16 hidden=4096 on 500M tokens";
  function pSizing() {
    if (ST.arg) return one(ST.arg, 'sizing', pSz);
    const s = st_();
    return `<div><h1 class="sd-h">Sizing</h1><p class="lead">How much GPU a model needs: weights at a precision, the KV cache for your context and batch, whether it fits, the largest batch, the speed limit from memory bandwidth, and training memory and GPU-hours.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Size a model</h2><form data-form="sizing" class="mlk-grid">
        ${area('text', "The model ('model 8B bf16 layers=32 kv_heads=8 head_dim=128' - the numbers are in its config.json), serving ('serve context=8192 batch=16'), the GPUs ('gpu h100 x2', or gpu_mem=48 bw=864 tflops=362) and training if any ('train full on 2B tokens', 'train qlora rank=16')", SAMPLE_SZ, 6)}
        ${fld('gpu_util', 'Share of GPU memory to use', s.gpu_util, 'type="number" min="0.1" max="1" step="any"')}${fld('mfu', 'Training utilisation (MFU)', s.mfu, 'type="number" min="0.01" max="1" step="any"')}
        ${subRow('Size it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Sized</h2>${itemRows(items('sizing'))}</section>`;
  }
  function pSz(d) {
    const r = d.result || {}, sv = r.serve, tr = r.train;
    const cap_ = r.mem_gb ? r.mem_gb * r.count * r.util : null;
    const seg = sv ? [['Weights', r.weights_gb, 'c1'], ['KV cache', sv.kv_gb, 'c2'], ['Runtime', sv.overhead_gb, 'c5']] : [['Weights', r.weights_gb, 'c1']];
    const tot = seg.reduce((a, s2) => a + s2[1], 0), scale = Math.max(tot, cap_ || 0) || 1;
    return `${head(d, 'sizing')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Parameters', esc(big(r.params)), r.precision)}${tile('Weights', esc(GB(r.weights_gb)), `${P4(r.weights_gb * 1e9 / r.params)} bytes a parameter`)}${tile('To serve', sv ? esc(GB(sv.total_gb)) : '—', sv ? `${num(r.batch)} x ${num(r.context)} tokens` : 'give the shape and a context', sv && sv.fits === false)}${tile('GPUs', r.mem_gb ? esc(num(r.count)) + ' <small>x ' + esc(r.mem_gb) + ' GB</small>' : '—', r.gpu ? cap(r.gpu) + (cap_ ? `, ${GB(cap_)} usable` : '') : 'name the GPU')}</div></section>
      <section class="card"><h2 class="md-h2">Memory</h2><div class="mlk-mem" role="img" aria-label="Memory against the GPUs">${seg.map(s2 => `<i class="${s2[2]}" style="width:${(s2[1] / scale * 100).toFixed(2)}%" title="${esc(s2[0])} ${esc(GB(s2[1]))}"></i>`).join('')}${cap_ ? `<b style="left:${Math.min(100, cap_ / scale * 100).toFixed(2)}%"></b>` : ''}</div>
        <div class="mlk-key">${seg.map(s2 => `<span><i class="${s2[2]}"></i>${esc(s2[0])} <b>${esc(GB(s2[1]))}</b></span>`).join('')}${cap_ ? `<span><i class="cap"></i>usable on the GPUs <b>${esc(GB(cap_))}</b></span>` : ''}</div>
        ${sv && sv.max_batch !== undefined ? stats([['Fits', sv.fits ? 'yes' : 'no', sv.fits ? '' : 'bad'], ['Largest batch at this context', num(sv.max_batch)], ['Longest context at this batch', num(sv.max_context)], ['GPUs needed', num(sv.gpus_needed)], ['KV cache a token', P4(r.kv_per_token_mb) + ' MB']]) : ''}</section>
      ${r.decode_tok_s ? `<section class="card"><h2 class="md-h2">Speed limit</h2>${stats([['Decoding, one sequence', 'up to ' + num(Math.round(r.decode_tok_s)) + ' tokens/s'], ['Memory bandwidth', num(r.bw * r.count) + ' GB/s']])}<p class="cs-note">Every weight is read once for each token, so bandwidth sets the ceiling for one sequence; batching raises the total throughput, not this.</p></section>` : ''}
      ${tr ? `<section class="card"><h2 class="md-h2">Training (${esc(tr.mode === 'full' ? 'full fine-tuning' : tr.mode.toUpperCase())})</h2>${stats([['Memory before activations', GB(tr.gb)], ['Trainable parameters', big(tr.trainable)], ...(tr.tokens ? [['Tokens', big(tr.tokens)], ['Compute', sci(tr.flops) + ' FLOPs']] : []), ...(tr.gpu_hours ? [['GPU-hours', num(Math.round(tr.gpu_hours))], ['Days on these GPUs', P4(tr.days)]] : [])])}<p class="cs-note">${esc(tr.what)}.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mlk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs your evaluation on every pull request and fails it when a score drops or an error or time rises more than you allow against the baseline in your repository.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Evaluation', s.eval_cmd || 'not set'], ['Metrics file', s.metrics_path], ['Baseline', s.baseline_path], ['Allowed drop in a score', P4(s.max_drop) + ' points'], ['Allowed rise in an error or time', P4(s.max_rise) + '%'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="model-check.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your columns, the drift limits, how training runs are judged, GPU figures and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="mlk-grid">
        <h2 class="md-h2 wide" style="margin:0">Columns</h2>
        ${fld('target', 'Target column', s.target, '', 'churned')}${fld('split_col', 'Train / test column', s.split_col, '', 'split')}${fld('group_col', 'Group column for errors', s.group_col, '', 'store')}
        ${fld('actual_col', 'Actual column', s.actual_col, '', 'actual')}${fld('pred_col', 'Predicted column', s.pred_col, '', 'predicted')}${fld('season', 'Season length (naive forecast)', s.season, 'type="number" min="1" step="1"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Judging</h2>
        ${fld('patience', 'Early-stopping patience', s.patience, 'type="number" min="1" step="1"')}${fld('psi_warn', 'PSI to watch', s.psi_warn, 'type="number" min="0.01" step="any"')}${fld('psi_alarm', 'PSI to act on', s.psi_alarm, 'type="number" min="0.01" step="any"')}
        ${fld('gpu_util', 'Share of GPU memory to use', s.gpu_util, 'type="number" min="0.1" max="1" step="any"')}${fld('mfu', 'Training utilisation (MFU)', s.mfu, 'type="number" min="0.01" max="1" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${fld('eval_cmd', 'Evaluation command (writes the metrics file)', s.eval_cmd, 'maxlength="400"', 'python eval.py --out eval/metrics.json')}${fld('setup_cmd', 'Setup command (optional)', s.setup_cmd, 'maxlength="400"', 'pip install -r requirements.txt')}
        ${fld('metrics_path', 'Metrics file', s.metrics_path)}${fld('baseline_path', 'Baseline file', s.baseline_path)}
        ${fld('max_drop', 'Allowed drop in a score (points)', s.max_drop, 'type="number" min="0" step="any"')}${fld('max_rise', 'Allowed rise in an error or time (%)', s.max_rise, 'type="number" min="0" step="any"')}${fld('python', 'Python', s.python)}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Training runs are read from the logged numbers; one run on one seed is not a result.</li><li>Profiles, drift and errors cover the rows you paste - use data the model never trained on to score it.</li><li>PSI limits (0.1 / 0.25) are rules of thumb, not tests; read the size of a shift before its p-value.</li><li>Sizing uses the model's shape and datasheet figures; real serving adds framework buffers and real speed is lower.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your machines or your GPUs.</li><li>Calls a model better from one run or a small gain within the noise.</li><li>Promises a fit or a speed beyond the figures given - measure on the hardware.</li><li>Follows anything written inside your logs or data: they are data.</li></ul></section>`;
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
      if (kind === 'run') await go('run', {text: S(fd.get('text')), inputs: pick(['patience'])});
      else if (kind === 'data') await go('data', {text: S(fd.get('text')), inputs: pick(['target', 'split'])});
      else if (kind === 'drift') await go('drift', {text: S(fd.get('text')), inputs: pick(['current', 'psi_warn', 'psi_alarm'])});
      else if (kind === 'regress') await go('regress', {text: S(fd.get('text')), inputs: pick(['actual', 'predicted', 'group', 'season'])});
      else if (kind === 'sizing') await go('sizing', {text: S(fd.get('text')), inputs: pick(['gpu_util', 'mfu'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['target', 'split_col', 'actual_col', 'pred_col', 'group_col', 'season', 'patience', 'psi_warn', 'psi_alarm', 'gpu_util', 'mfu', 'eval_cmd', 'metrics_path', 'baseline_path', 'max_drop', 'max_rise', 'setup_cmd', 'python', 'runner'];


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
    const box = $('#mlFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/mldesk/chat'); ST.chat = r.id; }
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


