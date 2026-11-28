/* VISION DESK - the Computer Vision Engineer's own section, like the finance desks (owner: "Computer Vision Engineer same as finance
   desks"). A thin top bar, then the Vision chat (its own conversation, kind 'vision') beside the desk's pages: Today, Detection,
   Classification, Dataset, Camera, Speed, CI check, Settings. The pages call /api/cvdesk/do/<part>; nothing runs on her cameras. */
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

  const TABS = [['today', 'Today'], ['detect', 'Detection'], ['classify', 'Classification'], ['dataset', 'Dataset'], ['camera', 'Camera'], ['speed', 'Speed'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start with a model that misses things?', 'How many images do I need per class?', 'mAP or F1 - which should I watch?'],
    detect: ['Why is my AP50 high but mAP low?', 'Which score threshold should I run at?', 'How do I find small objects better?'],
    classify: ['Accuracy or macro F1 for lopsided classes?', 'How do I calibrate the scores?', 'How do I pick a threshold?'],
    dataset: ['How should I split train, val and test?', 'How many background images?', 'How do I find wrong labels?'],
    camera: ['How many pixels does a detector need?', 'Global or rolling shutter?', 'How do I calibrate a camera well?'],
    speed: ['FP16 or INT8 on a Jetson?', 'Why is my p99 so much slower?', 'Should I tile big images?'],
    ci: ['How do I keep a fixed test set?', 'Can CI use a GPU?', 'How much drop should I allow?'],
    settings: ['What IoU threshold should I use?', 'Where do the class names come from?', 'What goes in the metrics file?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'detect', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.cvdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.cvdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'vision', name: 'Vision'} : null;
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
  const run = (part, a) => api('POST', '/api/cvdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/cvdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Computer Vision Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="cvHire">Hire the Computer Vision Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#cvHire').onclick = async () => { try { await api('POST', '/api/employees/cv_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Vision</div><div class="sd-site" id="cvSite"></div></div>
          <span id="cvState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Vision chat">
          <div class="sd-chathead"><div class="t"><b>Vision chat</b><span>Paste labels, predictions, a camera or timings - or drop a file or image here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="cvFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="cvPick" multiple hidden accept=".txt,.json,.csv,.yaml,.yml,.xml,.log,.md,.py,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Vision desk" id="sdTabs"></nav>
          <div id="cvPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste results or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#cvPick').click()});
    $('#cvPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.cvdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.cvdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/cvdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#cvPage').addEventListener('click', onPageClick);
    $('#cvPage').addEventListener('submit', onSubmit);
    $('#cvPage').addEventListener('change', onChange);
    $('#cvPage').addEventListener('input', onInput);
    $('#cvPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#cvState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#cvSite').textContent = [s.class_names && pl(s.class_names.split(',').length, 'class', 'classes'), pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/cvdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#cvPage'); if (!box) return;
    const fn = {today: pToday, detect: pDetect, classify: pClassify, dataset: pDataset, camera: pCamera, speed: pSpeed, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="cvk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {detect: 'Detection', classify: 'Classification', dataset: 'Dataset', camera: 'Camera', pipeline: 'Speed'};
  const ROUTE = {detect: 'detect', classify: 'classify', dataset: 'dataset', camera: 'camera', pipeline: 'speed'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(1);
  const ms = v => (v === null || v === undefined) ? '—' : P4(v) + ' ms';
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'detect': return `mAP ${pc(b.map)} · AP50 ${pc(b.map50)} · ${pl(b.classes || 0, 'class', 'classes')} · ${pl(b.images || 0, 'image')}`;
      case 'classify': return `${pc(b.acc)}% accurate · macro F1 ${P4(b.f1)} · ${pl(b.n || 0, 'image')}${b.auc !== null && b.auc !== undefined ? ' · AUC ' + P4(b.auc) : ''}`;
      case 'dataset': return `${b.fmt || ''} · ${pl(b.images || 0, 'image')} · ${pl(b.boxes || 0, 'box', 'boxes')} · ${pl(b.classes || 0, 'class', 'classes')}`;
      case 'camera': return `${b.W}x${b.H}${b.hfov ? ' · ' + Math.round(b.hfov) + '° wide' : ''}${b.calib ? ' · calibration' : ''} · ${pl(b.answers || 0, 'answer')}`;
      case 'pipeline': return [b.fps ? P4(b.fps) + ' fps' : '', b.latency ? ms(b.latency) + ' a frame' : '', b.p99 ? 'p99 ' + ms(b.p99) : ''].filter(Boolean).join(' · ');
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="cvk-list">${list.map(x => `<button type="button" class="cvk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="cvk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="cvk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="cvk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="cvk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono cvk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft cvk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="cvk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card cvk-sum ${ok ? 'okv' : 'badv'}"><p class="cvk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="cvk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="cvk-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="cvk-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="cvk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  const sec = v => { if (v === null || v === undefined) return '—'; const n = Number(v); return Math.abs(n) < 1 ? P4(n * 1000) + ' ms' : P4(n) + ' s'; };
  const shade = (v, max) => `background:color-mix(in srgb,var(--acc) ${Math.round(Math.min(1, max ? v / max : 0) * 70)}%,transparent)`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), d = k.detect, c = k.classify, ds = k.dataset, p = k.pipeline, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Detector', d ? esc(pc(d.map)) + '<small> mAP</small>' : '—', d ? `AP50 ${pc(d.map50)} · ${pl(d.images || 0, 'image')} · ${d.number}` : 'paste labels and predictions', d && d.bad),
      tile('Classifier', c ? esc(pc(c.acc)) + '<small>%</small>' : '—', c ? `macro F1 ${P4(c.f1)} · ${c.number}` : 'paste true and predicted', c && c.bad),
      tile('Dataset', ds ? (ds.bad ? esc(num(ds.issues)) + ' <small>to fix</small>' : 'Ready') : '—', ds ? `${pl(ds.images || 0, 'image')}, ${pl(ds.boxes || 0, 'box', 'boxes')} · ${ds.number}` : 'paste the labels', ds && ds.bad),
      tile('Speed', p && p.fps ? esc(P4(p.fps)) + '<small> fps</small>' : p && p.p99 ? esc(P4(p.p99)) + '<small> ms p99</small>' : '—', p ? `${p.latency ? ms(p.latency) + ' a frame · ' : ''}${p.number}` : 'paste stage times', p && p.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.class_names ? 'Classes: ' + s.class_names.slice(0, 120) : 'Set your class names in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="cvk-path">
        <li><button type="button" data-go="dataset"><b>Clean the labels</b><span>Bad and duplicate boxes, missing classes, the same image in two splits</span></button></li>
        <li><button type="button" data-go="camera"><b>Get enough pixels</b><span>The lens and distance that put enough pixels on the smallest object, without blur</span></button></li>
        <li><button type="button" data-go="detect"><b>Know how good it is</b><span>mAP the COCO way, per class and by size, and what kind of mistakes it makes</span></button></li>
        <li><button type="button" data-go="speed"><b>Make it keep up</b><span>Latency and frame rate against the camera, and objects after the resize</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- detection */
  const SAMPLE_GT = "# image class x1 y1 x2 y2 (or a COCO JSON)\nimg001.jpg person 120 80 260 400\nimg001.jpg car 400 210 620 330\nimg002.jpg person 30 40 90 210";
  const SAMPLE_PR = "# image class score x1 y1 x2 y2 (or a COCO results list)\nimg001.jpg person 0.93 118 84 255 398\nimg001.jpg car 0.71 410 205 610 335\nimg002.jpg car 0.40 30 40 90 210";
  function pDetect() {
    if (ST.arg) return one(ST.arg, 'detect', pDt);
    const s = st_();
    return `<div><h1 class="sd-h">Detection</h1><p class="lead">An object detector scored exactly the way COCO scores it - mAP over IoU 0.50 to 0.95, AP50, per class and by object size - and what kind of mistakes it makes.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Score a detector</h2><form data-form="detect" class="cvk-grid">
        ${area('text', 'Ground truth: one box per line (image class x1 y1 x2 y2), a line with just the image name for an image with no objects - or a COCO JSON', SAMPLE_GT, 8)}
        ${area('pred', "The model's predictions: image class score x1 y1 x2 y2 - or a COCO results list", SAMPLE_PR, 8)}
        ${sel('box_fmt', 'Box numbers are', [['xyxy', 'x1 y1 x2 y2 (corners)'], ['xywh', 'x y width height (COCO)']], s.box_fmt)}
        ${fld('score_thr', 'Score threshold you run at', s.score_thr, 'type="number" min="0" max="1" step="any"')}${fld('iou_thr', 'IoU for a match', s.iou_thr, 'type="number" min="0.05" max="0.95" step="any"')}
        ${subRow('Score it', '.txt,.json,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Scored</h2>${itemRows(items('detect'))}</section>`;
  }
  function pDt(d) {
    const r = d.result || {}, cls = r.classes || [], at = r.at || {}, best = r.best || {}, e = r.errors || {};
    const curves = Object.entries(r.curves || {}).slice(0, 6).map(([n, pts], i) => ({name: n, pts, cls: CL[i % 6]}));
    const sw = r.sweep || [];
    return `${head(d, 'detect')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('mAP', esc(pc(r.map)), 'IoU 0.50:0.95')}${tile('AP50', esc(pc(r.map50)), 'IoU 0.50')}${tile('AP75', esc(pc(r.map75)), 'IoU 0.75')}${tile('F1 at ' + P4(at.thr), esc(P4(at.f1)), `precision ${pc(at.p)}%, recall ${pc(at.r)}%`)}</div></section>
      <section class="card"><h2 class="md-h2">By object size</h2>${stats([['Small (under 32²)', pc(r.small)], ['Medium', pc(r.medium)], ['Large (over 96²)', pc(r.large)], ['Images', r.images], ['Objects', r.gt], ['Predictions', r.pred]])}</section>
      <section class="card"><h2 class="md-h2">Each class</h2>${bars(cls.filter(c => c.gt).map(c => [c.name, (c.ap50 || 0) * 100, 'cvk-b', `AP50 · mAP ${pc(c.ap)} · ${pl(c.gt, 'object')} · ${pl(c.pred, 'prediction')}`]), v => Number(v).toFixed(1), 'AP50 by class')}
        <div class="iv-tw"><table class="tb in-cards cvk-t"><thead><tr><th>Class</th><th class="r">Objects</th><th class="r">Predicted</th><th class="r">mAP</th><th class="r">AP50</th><th class="r">AP75</th><th class="r">Small</th><th class="r">Medium</th><th class="r">Large</th></tr></thead><tbody>${cls.map(c => `<tr class="${c.ap50 !== null && c.ap50 < 0.3 && c.gt >= 5 ? 'warn' : ''}"><td><b>${esc(c.name)}</b></td><td class="r">${esc(num(c.gt))}</td><td class="r">${esc(num(c.pred))}</td><td class="r">${esc(pc(c.ap))}</td><td class="r">${esc(pc(c.ap50))}</td><td class="r">${esc(pc(c.ap75))}</td><td class="r mut">${esc(pc(c.small))}</td><td class="r mut">${esc(pc(c.medium))}</td><td class="r mut">${esc(pc(c.large))}</td></tr>`).join('')}</tbody></table></div></section>
      ${curves.length ? `<section class="card"><h2 class="md-h2">Precision against recall (IoU ${P4(r.iou || 0.5)})</h2>${lines(curves, 'recall', 'precision', 'Precision-recall curves', {ymax: 1})}</section>` : ''}
      <section class="card"><h2 class="md-h2">Choosing the score threshold</h2>${lines([{name: 'precision', pts: sw.map(x => [x.thr, x.p]), cls: 'c2'}, {name: 'recall', pts: sw.map(x => [x.thr, x.r]), cls: 'c4'}, {name: 'F1', pts: sw.map(x => [x.thr, x.f1]), cls: 'ink'}], 'score threshold', '', 'Precision, recall and F1 by threshold', {ymax: 1})}
        <p class="cs-note">You run at ${esc(P4(at.thr))}: ${esc(num(at.tp))} found, ${esc(num(at.fp))} false, ${esc(num(at.fn))} missed. The best F1 is ${esc(P4(best.f1))} at ${esc(P4(best.thr))}.</p></section>
      <section class="card"><h2 class="md-h2">Where the mistakes are (score ${esc(P4(at.thr))} and up)</h2>${bars(Object.entries(e).map(([k2, v]) => [cap(k2), v, 'cvk-b warn', '']), v => num(v), 'Mistakes by kind')}
        ${(r.confusion || []).length ? `<h3 class="cvk-h3" style="margin-top:18px">Classes it mixes up</h3><div class="iv-tw"><table class="tb in-cards cvk-t"><thead><tr><th>Really</th><th>Called</th><th class="r">Times</th></tr></thead><tbody>${r.confusion.map(x => `<tr><td>${esc(x.truth)}</td><td>${esc(x.said)}</td><td class="r">${esc(num(x.n))}</td></tr>`).join('')}</tbody></table></div>` : ''}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card cvk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}${pre(S((d.inputs || {}).pred).slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- classification */
  const SAMPLE_CL = "image,true,predicted,score\nimg001.jpg,ok,ok,0.97\nimg002.jpg,defect,ok,0.61\nimg003.jpg,defect,defect,0.88";
  function pClassify() {
    if (ST.arg) return one(ST.arg, 'classify', pCl);
    return `<div><h1 class="sd-h">Classification</h1><p class="lead">A classifier scored from its results: accuracy you can trust, each class's precision and recall, what it confuses, how honest its scores are, and the threshold for the precision you need.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Score a classifier</h2><form data-form="classify" class="cvk-grid">
        ${area('text', "One image per line: image, true class, predicted class - and the model's score for its prediction (0 to 1) if you have it", SAMPLE_CL, 9)}
        ${fld('positive', 'With two classes, the one you look for', '', '', 'defect')}${fld('need', 'A target to reach', '', '', 'precision 95%')}
        ${subRow('Score it', '.csv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Scored</h2>${itemRows(items('classify'))}</section>`;
  }
  function pCl(d) {
    const r = d.result || {}, cls = r.classes || [], b = r.binary, cal = r.calibration, M_ = r.matrix, L = r.labels || [];
    const mx = M_ ? Math.max(...M_.map(row => Math.max(...row)), 1) : 1;
    return `${head(d, 'classify')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Accuracy', esc(pc(r.accuracy)) + '<small>%</small>', `95% interval ${pc((r.acc_ci || [])[0])}-${pc((r.acc_ci || [])[1])}`)}${tile('Macro F1', esc(P4(r.macro_f1)), 'every class counts the same')}${tile("Cohen's kappa", esc(P4(r.kappa)), 'agreement beyond chance')}${tile(b ? 'ROC AUC' : 'Calibration error', b ? esc(P4(b.auc)) : cal ? esc(pc(cal.ece)) + '<small> points</small>' : '—', b ? `${b.positive} against ${b.negative}` : cal ? 'scores against the real hit rate' : 'no scores given', cal && cal.ece > 0.1)}</div></section>
      <section class="card"><h2 class="md-h2">Each class</h2><div class="iv-tw"><table class="tb in-cards cvk-t"><thead><tr><th>Class</th><th class="r">Images</th><th class="r">Precision</th><th class="r">Recall</th><th class="r">F1</th><th style="min-width:120px">Recall</th></tr></thead><tbody>${cls.map(c => `<tr class="${c.r !== null && c.r < 0.5 && c.support >= 5 ? 'warn' : ''}"><td><b>${esc(c.cls)}</b></td><td class="r">${esc(num(c.support))}</td><td class="r">${esc(pc(c.p))}</td><td class="r">${esc(pc(c.r))}</td><td class="r">${esc(P4(c.f1))}</td><td>${c.r === null ? '' : `<div class="cvk-meter"><i class="${c.r < 0.5 ? 'bad' : c.r < 0.8 ? 'warn' : ''}" style="width:${(c.r * 100).toFixed(1)}%"></i></div>`}</td></tr>`).join('')}</tbody></table></div></section>
      ${M_ ? `<section class="card"><h2 class="md-h2">Confusion matrix</h2><div class="iv-tw"><table class="tb cvk-cm"><thead><tr><th class="mut">really ↓ / called →</th>${L.map(x => `<th class="r">${esc(x)}</th>`).join('')}</tr></thead><tbody>${M_.map((row, i) => `<tr><th>${esc(L[i])}</th>${row.map((v, j) => `<td class="r${i === j ? ' dg' : ''}" style="${v ? shade(v, mx) : ''}">${v ? esc(num(v)) : '<span class="mut">·</span>'}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>` : ''}
      ${cal ? `<section class="card"><h2 class="md-h2">Are the scores honest?</h2>${lines([{name: 'perfectly honest', pts: [[0, 0], [1, 1]], cls: 'c5', dash: true}, {name: 'this model', pts: cal.bins.map(x => [x.conf, x.acc]), cls: 'c1'}], 'what the score says', 'how often it is right', 'Reliability', {ymax: 1})}<p class="cs-note">Expected calibration error ${esc(pc(cal.ece))} points over ${esc(num(cal.scored))} scored images. Under the dashed line the model is overconfident.</p></section>` : ''}
      ${b ? `<section class="card"><h2 class="md-h2">${esc(b.positive)} against ${esc(b.negative)}</h2><div class="cvk-two">${lines([{name: 'ROC', pts: b.roc, cls: 'c1'}, {name: 'chance', pts: [[0, 0], [1, 1]], cls: 'c5', dash: true}], 'false positive rate', 'true positive rate', 'ROC curve', {ymax: 1})}${lines([{name: 'precision-recall', pts: b.pr, cls: 'c2'}], 'recall', 'precision', 'Precision-recall curve', {ymax: 1})}</div>
        ${b.need ? `<p class="cs-note">${b.need.thr === null ? `No threshold reaches ${esc(b.need.kind)} ${esc(pc(b.need.value))}%.` : `For ${esc(b.need.kind)} ${esc(pc(b.need.value))}%: call it ${esc(b.positive)} when its score is ${esc(P4(b.need.thr))} or more - precision ${esc(pc(b.need.p))}%, recall ${esc(pc(b.need.r))}%.`}</p>` : ''}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card cvk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- dataset */
  const SAMPLE_DS = "## train/labels/img001.txt\n0 0.512 0.430 0.210 0.380\n1 0.250 0.700 0.120 0.090\n## train/labels/img002.txt\n0 0.600 0.500 0.300 0.400\n## val/labels/img003.txt\n1 0.400 0.400 0.100 0.100";
  function pDataset() {
    if (ST.arg) return one(ST.arg, 'dataset', pDs);
    const s = st_();
    return `<div><h1 class="sd-h">Dataset</h1><p class="lead">Labels checked before anyone trains on them: boxes outside the image or with no size, objects labelled twice or with two classes, lopsided classes, and the same image in two splits.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check labels</h2><form data-form="dataset" class="cvk-grid">
        ${area('text', "YOLO label files, each under a '## path/name.txt' header with its train / val / test folder (open several files at once) - or a COCO JSON", SAMPLE_DS, 12)}
        ${fld('names', 'Class names in id order (YOLO)', s.class_names, '', 'person, car, bike')}${fld('img_size', 'Image size (YOLO)', s.img_size, '', '1920x1080')}
        <div class="cvk-row wide"><label class="btn soft cvk-file">Open label files<input type="file" data-filesto="text" accept=".txt,.json" multiple hidden></label><label class="btn soft cvk-file">Open a folder<input type="file" data-filesto="text" webkitdirectory multiple hidden></label><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Check them</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('dataset'))}</section>`;
  }
  function pDs(d) {
    const r = d.result || {}, cls = r.classes || [], sp = Object.keys(r.splits || {}), pi = r.per_image || {};
    return `${head(d, 'dataset')}${verdict(r, isOk(r))}
      <section class="card">${stats([['Format', r.format], ['Images', num(r.images)], ['Boxes', num(r.boxes)], ['Classes', cls.length], ['No labels', num(r.empty)], ['Most boxes in one image', num(pi.max)], ['Boxes per image', P4(pi.mean)]])}</section>
      <section class="card"><h2 class="md-h2">Classes</h2>${bars(cls.map(c => [c.name, c.boxes, c.unknown ? 'cvk-b warn' : 'cvk-b', `${pl(c.images, 'image')} · ${(c.share * 100).toFixed(1)}%${c.unknown ? ' · not in the class list' : ''}`]), v => num(v), 'Boxes by class')}
        ${sp.length > 1 || cls.some(c => Object.keys(c.sizes || {}).length) ? `<div class="iv-tw"><table class="tb in-cards cvk-t"><thead><tr><th>Class</th>${sp.map(x => `<th class="r">${esc(cap(x))}</th>`).join('')}<th class="r">Small</th><th class="r">Medium</th><th class="r">Large</th></tr></thead><tbody>${cls.map(c => `<tr><td><b>${esc(c.name)}</b></td>${sp.map(x => `<td class="r${(x === 'val' || x === 'test') && !(c.splits || {})[x] && !c.unknown ? ' cs-neg' : ''}">${esc(num((c.splits || {})[x] || 0))}</td>`).join('')}<td class="r mut">${esc(num((c.sizes || {}).small || 0))}</td><td class="r mut">${esc(num((c.sizes || {}).medium || 0))}</td><td class="r mut">${esc(num((c.sizes || {}).large || 0))}</td></tr>`).join('')}</tbody></table></div>` : ''}</section>
      ${sp.length > 1 ? `<section class="card"><h2 class="md-h2">Splits</h2>${stats(sp.map(x => [cap(x), pl(r.splits[x], 'image')]))}</section>` : ''}
      <section class="card"><h2 class="md-h2">Boxes per image</h2>${bars((pi.hist || []).map(([k2, v]) => [k2 >= 20 ? '20 or more' : String(k2), v, 'cvk-b', '']), v => num(v), 'Images by number of boxes')}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card cvk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- camera */
  const SAMPLE_CAM = "sensor pixel=2.9um res=1920x1080 lens=6mm\ndistance 10m\nobject 0.2m at 30m\nneed 30px on 0.2m at 40m\ncover 4m at 10m\nmotion 10m/s exposure 1ms at 5m\ndof f/2 at 3m\nstereo baseline=0.12m at 5m disparity 0.25px";
  function pCamera() {
    if (ST.arg) return one(ST.arg, 'camera', pCa);
    const s = st_();
    return `<div><h1 class="sd-h">Camera</h1><p class="lead">The camera and lens worked out for the job: field of view, pixels on the object, the lens you need, motion blur, depth of field, stereo depth error - or a calibration file checked.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Work it out</h2><form data-form="camera" class="cvk-grid">
        ${area('text', "First the camera ('sensor pixel=2.9um res=1920x1080 lens=6mm', or fov=90 instead of the lens, or a format like 1/2.8in), then one question a line - or paste a calibration file (ROS camera_info or OpenCV YAML)", SAMPLE_CAM, 10)}
        ${fld('ask', 'Questions for a calibration file', '', '', 'object 0.3m at 15m')}${fld('min_px', 'Fewest pixels a detector needs on an object', s.min_px, 'type="number" min="1" step="any"')}
        ${subRow('Work it out', '.yaml,.yml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('camera'))}</section>`;
  }
  function wedge(cam) {
    if (!cam.hfov) return '';
    const W = 360, H = 220, a = Math.min(cam.hfov, 170) / 2 * Math.PI / 180, L = 190, ox = W / 2, oy = H - 14;
    const x1 = ox - Math.sin(a) * L, x2 = ox + Math.sin(a) * L, y = oy - Math.cos(a) * L;
    return `<figure class="cvk-wedge"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Horizontal field of view"><path class="w" d="M${ox},${oy} L${x1.toFixed(1)},${y.toFixed(1)} A${L},${L} 0 0 1 ${x2.toFixed(1)},${y.toFixed(1)} Z"/><circle class="c" cx="${ox}" cy="${oy}" r="6"/><text class="tx" x="${ox}" y="${(oy - L * 0.45).toFixed(1)}" text-anchor="middle">${esc(P4(cam.hfov))}°</text></svg><figcaption>Horizontal field of view, from above</figcaption></figure>`;
  }
  function pCa(d) {
    const r = d.result || {}, cam = r.camera || {}, c = r.calib;
    return `${head(d, 'camera')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Resolution', esc(cam.W + ' x ' + cam.H), cam.src || '')}${tile('Field of view', cam.hfov ? esc(P4(cam.hfov)) + '<small>° x ' + esc(P4(cam.vfov)) + '°</small>' : '—', cam.dfov ? `${P4(cam.dfov)}° across the diagonal` : 'give the lens or fov')}${tile('Focal length', cam.fpx ? esc(P4(cam.fpx)) + '<small> px</small>' : '—', cam.f ? `${P4(cam.f * 1000)} mm lens` : '')}${tile('Detector needs', esc(P4(r.min_px)) + '<small> px</small>', 'on the smallest object')}</div></section>
      <section class="card cvk-camtop">${wedge(cam)}<div style="flex:1;min-width:0">${(r.answers || []).map(a => `<div class="cvk-ans ${a.state || ''}"><h3 class="cvk-h3">${esc(a.title)}</h3><dl>${a.rows.map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl></div>`).join('') || empty('Add questions under the camera line - distance 10m, object 0.2m at 30m ...')}</div></section>
      ${c ? `<section class="card"><h2 class="md-h2">The calibration</h2>${stats([['fx', P4(c.fx)], ['fy', P4(c.fy)], ['cx', P4(c.cx)], ['cy', P4(c.cy)], ['Reprojection error', c.rms === null || c.rms === undefined ? 'not in the file' : P4(c.rms) + ' px', c.rms > 1 ? 'bad' : ''], ['Corner moved by distortion', c.corner_px === null || c.corner_px === undefined ? '—' : P4(c.corner_px) + ' px']])}<p class="mut" style="margin:0;font-size:13px">Model ${esc(c.model || '—')} · coefficients <code>${esc((c.D || []).map(P4).join(', ') || 'none')}</code></p></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card cvk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- speed */
  const SAMPLE_SP = "camera 1920x1080 30fps\ndecode 6ms\npreprocess 4ms\ninference 28ms gpu\nnms 2ms\ntracking 3ms\nmodel input=640 object=24px";
  function pSpeed() {
    if (ST.arg) return one(ST.arg, 'speed', pSp);
    const s = st_();
    return `<div><h1 class="sd-h">Speed</h1><p class="lead">Whether the pipeline keeps up: latency of one frame, the frame rate with the stages overlapped, measured percentiles and late frames, and how small objects get after the resize.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a pipeline</h2><form data-form="pipeline" class="cvk-grid">
        ${area('text', "One stage per line with its time ('inference 18ms gpu', 'tracking 3ms every 2'), the camera ('camera 1920x1080 30fps'), the model ('model input=640 object=24px') - or latency samples, one number a line", SAMPLE_SP, 9)}
        ${fld('target_fps', 'Frame rate it must keep', s.target_fps || '', 'type="number" min="0" step="any"', '30')}${subRow('Check it', '.txt,.log,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('pipeline'))}</section>`;
  }
  function pSp(d) {
    const r = d.result || {}, st = r.stages || [], sm = r.samples, res = r.resolution;
    const need = r.target_fps || (r.camera || {}).fps;
    return `${head(d, 'speed')}${verdict(r, isOk(r))}
      ${st.length ? `<section class="cs-hero"><div class="top">${tile('One frame takes', esc(ms(r.latency)), 'all stages, one after another')}${tile('Frame rate, pipelined', esc(P4(r.par_fps)) + '<small> fps</small>', `held by ${r.slowest}`, need && r.par_fps < need)}${tile('Frame rate, in turn', esc(P4(r.seq_fps)) + '<small> fps</small>', 'stages one after another', need && r.seq_fps < need)}${tile('Needed', need ? esc(P4(need)) + '<small> fps</small>' : '—', need ? `a frame every ${ms(1000 / need)}` : 'set a target or a camera')}</div></section>
      <section class="card"><h2 class="md-h2">Where the time goes</h2><div class="cvk-stack" role="img" aria-label="Time by stage">${st.map((x, i) => `<i class="${CL[i % 6]}" style="width:${(x.share * 100).toFixed(2)}%" title="${esc(x.name)} ${esc(ms(x.per_frame))}"></i>`).join('')}</div>
        <div class="cvk-key">${st.map((x, i) => `<span><i class="${CL[i % 6]}"></i>${esc(x.name)} <b>${esc(ms(x.per_frame))}</b>${x.gpu ? ' <span class="cs-tag">GPU</span>' : ''}${x.every > 1 ? ` <span class="mut">every ${esc(x.every)} frames</span>` : ''}</span>`).join('')}</div></section>` : ''}
      ${sm ? `<section class="card"><h2 class="md-h2">Measured latency</h2>${stats([['Samples', num(sm.n)], ['p50', ms(sm.p50)], ['p90', ms(sm.p90)], ['p95', ms(sm.p95)], ['p99', ms(sm.p99), sm.p99 > 2 * sm.p50 ? 'warn' : ''], ['Slowest', ms(sm.max)], ...(sm.late !== undefined ? [['Late frames', num(sm.late), sm.late ? 'bad' : '']] : [])])}
        ${lines([{name: 'latency', pts: sm.series.map((v, i) => [i, v]), cls: 'c1'}], 'frame (sampled)', 'ms', 'Latency over the run', need ? {ref: 1000 / need} : {})}
        ${bars(sm.hist.map(([lo, c]) => [ms(lo), c, 'cvk-b', '']), v => num(v), 'Latency histogram')}</section>` : ''}
      ${res ? `<section class="card"><h2 class="md-h2">Resolution at the model</h2>${stats([['Model input', res.in_w + ' x ' + res.in_h], ['Scale', res.scale ? P4(res.scale) : 'give the camera size'], ['Object in the camera', res.obj ? P4(res.obj) + ' px' : '—'], ['Object at the model', res.obj_after !== undefined ? P4(res.obj_after) + ' px' : '—', res.obj_after < 10 ? 'bad' : ''], ...(res.tiles ? [['Tiles that would help', num(res.tiles)]] : [])])}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card cvk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 100000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs your evaluation on every pull request and fails it when a score drops or a time rises more than you allow against the baseline in your repository.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Evaluation', s.eval_cmd || 'not set'], ['Metrics file', s.metrics_path], ['Baseline', s.baseline_path], ['Allowed drop', P4(s.max_drop) + ' points'], ['Allowed rise in times', P4(s.max_rise) + '%'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="model-check.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your classes, how boxes are written, the thresholds you run at, and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="cvk-grid">
        <h2 class="md-h2 wide" style="margin:0">Labels and scoring</h2>
        <label class="ins-lab wide">Class names in id order<textarea class="in" name="class_names" rows="2" placeholder="person, car, bicycle">${esc(s.class_names)}</textarea></label>
        ${sel('box_fmt', 'Box numbers are', [['xyxy', 'x1 y1 x2 y2 (corners)'], ['xywh', 'x y width height (COCO)']], s.box_fmt)}${fld('score_thr', 'Score threshold you run at', s.score_thr, 'type="number" min="0" max="1" step="any"')}${fld('iou_thr', 'IoU for a match', s.iou_thr, 'type="number" min="0.05" max="0.95" step="any"')}
        ${fld('img_size', 'Image size for YOLO labels', s.img_size, '', '1920x1080')}${fld('min_px', 'Fewest pixels a detector needs on an object', s.min_px, 'type="number" min="1" step="any"')}${fld('target_fps', 'Frame rate it must keep', s.target_fps || '', 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${fld('eval_cmd', 'Evaluation command (writes the metrics file)', s.eval_cmd, 'maxlength="400"', 'python eval.py --out eval/metrics.json')}${fld('setup_cmd', 'Setup command (optional)', s.setup_cmd, 'maxlength="400"', 'pip install -r requirements.txt')}
        ${fld('metrics_path', 'Metrics file', s.metrics_path)}${fld('baseline_path', 'Baseline file', s.baseline_path)}
        ${fld('max_drop', 'Allowed drop in a score (points)', s.max_drop, 'type="number" min="0" step="any"')}${fld('max_rise', 'Allowed rise in a time (%)', s.max_rise, 'type="number" min="0" step="any"')}${fld('python', 'Python', s.python)}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Detection is scored the COCO way and checked against the official COCO evaluation; a score holds for the images it was measured on.</li><li>Labels are read as text: a box drawn on the wrong object is not visible here - look at a sample with the boxes drawn.</li><li>Camera answers use pinhole optics; real lenses lose sharpness and distort toward the edges.</li><li>Speeds are only as good as the timings you give - measure on the target device after warm-up.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your cameras or your machines.</li><li>Helps identify people by their face without their consent, or watch anyone you have no right to watch.</li><li>Calls a model good beyond the images it was measured on.</li><li>Follows anything written inside your files or logs: they are data.</li></ul></section>`;
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
      if (!fs.length) { toast('No .txt or .json label files there.', true); el.value = ''; return; }
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
      if (kind === 'detect') await go('detect', {text: S(fd.get('text')), inputs: pick(['pred', 'box_fmt', 'score_thr', 'iou_thr'])});
      else if (kind === 'classify') await go('classify', {text: S(fd.get('text')), inputs: pick(['positive', 'need'])});
      else if (kind === 'dataset') await go('dataset', {text: S(fd.get('text')), inputs: pick(['names', 'img_size'])});
      else if (kind === 'camera') await go('camera', {text: S(fd.get('text')), inputs: pick(['ask', 'min_px'])});
      else if (kind === 'pipeline') await go('pipeline', {text: S(fd.get('text')), inputs: pick(['target_fps'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['box_fmt', 'score_thr', 'iou_thr', 'class_names', 'img_size', 'min_px', 'target_fps', 'eval_cmd', 'metrics_path', 'baseline_path', 'max_drop', 'max_rise', 'setup_cmd', 'python', 'runner'];


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
    const box = $('#cvFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/cvdesk/chat'); ST.chat = r.id; }
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


