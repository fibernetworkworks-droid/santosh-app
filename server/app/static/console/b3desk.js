/* 3D STUDIO DESK - the 3D Studio artist's own section, like the finance desks (owner: "3D Studio same as finance desks").
   A thin top bar, then the 3D chat (its own conversation, kind 'studio3d') beside the desk's pages: Today, Make a model, Models,
   Settings. The pages call /api/b3desk/do/<part>, which runs the 3D Studio engine (real Blender in a locked box). Renders carry an
   "AI-generated" label; nothing is sent anywhere. */
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

  const TABS = [['today', 'Today'], ['make', 'Make a model'], ['models', 'Models'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What can you make in 3D?', 'Which file should I use for WhatsApp?', 'Make a mockup of my product'],
    make: ['Help me describe my product', 'What size should a name plate be?', 'Can you use my label photo?'],
    models: ['Make it a little bigger', 'Change the colour to dark blue', 'Is this ready to 3D print?'],
    settings: ['Which files do I need for printing?', 'What is the difference between GLB and USDZ?', 'When do I need the final quality?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', mf: 'all', idea: '', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.b3desk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.b3desk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'blender_3d', name: '3D Studio'} : null;
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
  const run = (part, a) => api('POST', '/api/b3desk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/b3desk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your 3D Studio artist is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="b3Hire">Hire the 3D Studio artist</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#b3Hire').onclick = async () => { try { await api('POST', '/api/employees/blender_3d/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">3D Studio</div><div class="sd-site" id="b3Site"></div></div>
          <span id="b3State"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="3D chat">
          <div class="sd-chathead"><div class="t"><b>3D chat</b><span>Say what to build or what to change - or drop your label, logo or a reference photo here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="b3Files" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="b3Pick" multiple hidden accept="image/*,.pdf,.svg">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="3D Studio desk" id="sdTabs"></nav>
          <div id="b3Page"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Renders carry an AI-generated label; nothing is sent anywhere.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Describe a model…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#b3Pick').click()});
    $('#b3Pick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.b3desk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.b3desk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/b3desk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#b3Page').addEventListener('click', onPageClick);
    $('#b3Page').addEventListener('submit', onSubmit);
    $('#b3Page').addEventListener('change', onChange);
    $('#b3Page').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#b3State'); if (!el) return;
    const k = K(), b = (k.busy || []).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !(k.health || {}).ready ? ['warn', 'Blender not installed'] : b ? ['ok', pl(b, 'model') + ' building'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#b3Site').textContent = [pl((k.projects || []).length, 'model'), (k.settings || {}).units === 'imperial' ? 'inches' : 'mm / cm'].join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {models: (k.busy || []).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/b3desk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#b3Page'); if (!box) return;
    const fn = {today: pToday, make: pMake, models: pModels, settings: pSettings}[ST.tab] || pToday;
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
  const BUSY = ['queued', 'writing', 'building', 'rendering', 'checking'];
  const PST = {queued: ['Waiting to start', 'warn'], writing: ['Writing the script', 'v'], building: ['Building in Blender', 'v'], rendering: ['Rendering', 'v'],
    checking: ['Looking at the renders', 'v'], done: ['Ready', 'ok'], failed: ['Could not build', 'bad'], cancelled: ['Stopped', '']};
  const pTag = p => tag((PST[p.status] || [cap(p.status)])[0], (PST[p.status] || ['', ''])[1]);
  const VIEW = {three_quarter: 'Three-quarter', front: 'Front', side: 'Side', back: 'Back', top: 'Top', low: 'Low angle'};
  const FMT = {glb: 'GLB - web, AR, WhatsApp 3D', stl: 'STL - 3D printing', obj: 'OBJ - other 3D apps', fbx: 'FBX - games', usdz: 'USDZ - iPhone AR', blend: 'Blender file'};
  const imp = () => st_().units === 'imperial';
  const size = s => { const v = (s && s.size_m) || []; if (!v.length) return ''; return imp() ? v.map(x => (x * 39.3701).toFixed(x * 39.3701 < 10 ? 2 : 1)).join(' × ') + ' in' : v.map(x => x < 1 ? Math.round(x * 1000) : (x * 100).toFixed(0)).join(' × ') + (v.every(x => x < 1) ? ' mm' : ' cm'); };
  const IDEAS = [['Product mockup', 'A 250 ml glass jar with a gold lid and my label on the front, on a soft cream background'],
    ['Gift', 'A wooden name plate, 20 cm wide, with "The Sharma Family" carved in it and small flowers in the corners'],
    ['Shop layout', 'A small tea stall 3 m wide: a counter with a glass jar row, two benches and a menu board'],
    ['Part to 3D print', 'A wall hook for a 2 cm pipe, 6 cm long, strong enough for a bag, with two screw holes'],
    ['Original mark', 'A 3D version of a simple leaf-and-drop mark in green and white for a water brand'],
    ['Toy / figurine', 'A cute round robot figurine, 8 cm tall, soft blue with big eyes and a small antenna']];
  const optChecks = (name, all, sel, labels) => all.map(v => `<label class="ar-chk"><input type="checkbox" name="${name}" value="${esc(v)}"${(sel || []).includes(v) ? ' checked' : ''}> ${esc(labels[v] || v)}</label>`).join('');
  const optForm = (d) => `<fieldset class="b3-set wide"><legend>Files</legend>${optChecks('exports', K().formats || [], d.exports, FMT)}</fieldset>
    <fieldset class="b3-set wide"><legend>Views (up to 4)</legend>${optChecks('views', K().views || [], d.views, VIEW)}</fieldset>
    <label class="ins-lab">Quality<select class="in" name="quality"><option value="preview"${d.quality !== 'final' ? ' selected' : ''}>Preview - fast</option><option value="final"${d.quality === 'final' ? ' selected' : ''}>Final - sharper, slower</option></select></label>
    <label class="ins-lab">Picture shape<select class="in" name="aspect">${(K().aspects || []).map(a => `<option value="${esc(a)}"${a === d.aspect ? ' selected' : ''}>${esc(a)}</option>`).join('')}</select></label>
    <label class="ins-lab">Style (optional)<input class="in" name="style" maxlength="200" value="${esc(d.style || '')}" placeholder="clean studio product shot"></label>
    <label class="ins-lab">Background<input class="in" name="background" type="color" value="${esc(/^#[0-9a-f]{6}$/i.test(d.background || '') ? d.background : '#f4f4f6')}"></label>
    <label class="ar-chk wide"><input type="checkbox" name="turntable"${d.turntable ? ' checked' : ''}> A 360° spin video</label>
    <label class="ar-chk wide"><input type="checkbox" name="print"${d.print ? ' checked' : ''}> It will be 3D printed (closed solid + size check)</label>
    <label class="ar-chk wide"><input type="checkbox" name="transparent"${d.transparent ? ' checked' : ''}> Transparent background</label>`;
  const shot = (p, cls) => { const r = (p.renders || [])[0]; return r ? `<img class="${esc(cls || 'b3-thumb')}" src="${esc(r.url)}" alt="${esc(p.title)}" loading="lazy">` : `<div class="${esc(cls || 'b3-thumb')} empty">${BUSY.includes(p.status) ? `<span>${esc(p.pct || 0)}%</span>` : svg(IC.fo, 'i')}</div>`; };

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), ps = k.projects || [], h = k.health || {};
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : (k.busy || []).length ? `${pl(k.busy.length, 'model')} being built right now.` : 'All in order.';
    const tiles = [
      `<div class="k"><div class="l">Models</div><div class="v">${esc(num(ps.length))}</div><div class="s">${esc(num(k.done || 0))} ready</div></div>`,
      `<div class="k"><div class="l">Being built</div><div class="v">${esc(num((k.busy || []).length))}</div><div class="s">up to 3 at once</div></div>`,
      `<div class="k${h.ready ? '' : ' low bad'}"><div class="l">Blender</div><div class="v b3-sm">${h.ready ? 'Ready' : 'Not installed'}</div><div class="s">${h.ready ? (h.no_network ? 'in a locked box, no internet' : 'in a box') : 'on the server'}</div></div>`,
      `<div class="k"><div class="l">Sizes in</div><div class="v b3-sm">${imp() ? 'Inches' : 'mm / cm'}</div><div class="s">change in Settings</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.busy || []).length ? `<section class="card"><h2 class="md-h2">Being built</h2>${k.busy.map(p => `<div class="b3-run"><b>${esc(p.number)} ${esc(p.title)}</b><span class="mut">${esc(p.stage || (PST[p.status] || [''])[0])}</span><i><b style="width:${esc(Math.max(4, p.pct || 0))}%"></b></i><button class="btn soft sm" type="button" data-open="${esc(p.id)}">Open</button></div>`).join('')}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Files you take</h2>${(k.by_format || []).length ? bars(k.by_format.map(([n, v]) => [n, v, 'mk-b']), num, 'Files by format') : empty('No files yet.')}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Latest models</h2><div class="r"><button class="btn soft sm" type="button" data-go="make">Make a model</button></div></div>
        ${ps.length ? `<div class="b3-grid">${ps.slice(0, 8).map(card).join('')}</div>` : empty('No models yet.')}</section>`;
  }
  function card(p) {
    return `<button type="button" class="b3-card" data-open="${esc(p.id)}">${shot(p)}<span class="t"><b>${esc(p.title)}</b><span class="mut">${esc(p.number)} · version ${esc(p.version || 0)} · ${esc(ago(p.created_at))}</span></span>${pTag(p)}</button>`;
  }

  /* ---------------------------------------------------------------- make */
  function pMake() {
    const d = st_().defaults || {}, h = K().health || {};
    return `<div><h1 class="sd-h">Make a model</h1><p class="lead">Say what it is, its size, colours, material and what it is for. Hoola writes the Blender script, builds it, looks at the renders and gives you the files.</p></div>${ro()}
      ${!h.ready ? `<section class="card"><p class="cs-neg" style="margin:0">Blender is not installed on the server yet. The admin runs <code>deploy/setup_blender.sh</code> once; until then a model cannot be built.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Start from an idea</h2><div class="b3-ideas">${IDEAS.map(([t, b], i) => `<button type="button" class="b3-idea" data-idea="${i}"><b>${esc(t)}</b><span>${esc(b)}</span></button>`).join('')}</div></section>
      ${CAN() ? `<section class="card"><form data-form="make" class="nc-grid"><label class="ins-lab wide">What to build<textarea class="in" name="brief" rows="4" required placeholder="A 12 cm clay tea cup with a gold handle, warm studio light">${esc(ST.idea || '')}</textarea></label>
        <label class="ins-lab wide">Name (optional)<input class="in" name="title" maxlength="120"></label>
        ${optForm(d)}
        <div class="md-acts wide"><span class="mut" style="font-size:13px">It runs in the background - usually a few minutes. Renders carry an "AI-generated" label.</span><button class="btn" type="submit">Build it</button></div></form></section>` : ''}
      <p class="cs-note">Never famous characters, real brand logos, real people or working weapon parts. Your own photos (a label, a texture) can be added from the 3D chat.</p>`;
  }

  /* ---------------------------------------------------------------- models */
  function pModels() {
    if (ST.arg) return pModel(ST.arg);
    const ps = (K().projects || []).filter(p => ST.mf === 'all' || (ST.mf === 'busy' ? BUSY.includes(p.status) : p.status === ST.mf));
    return `<div class="cs-head"><div><h1 class="sd-h">Models</h1><p class="lead">${esc(pl((K().projects || []).length, 'model'))}, newest first.</p></div>
        <div class="r"><select class="in sm" data-mf="1" aria-label="Show">${[['all', 'All'], ['done', 'Ready'], ['busy', 'Being built'], ['failed', 'Could not build']].map(([a, b]) => `<option value="${a}"${ST.mf === a ? ' selected' : ''}>${b}</option>`).join('')}</select></div></div>
      <section class="card">${ps.length ? `<div class="b3-grid">${ps.map(card).join('')}</div>` : `${empty('Nothing here.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="make">Make a model</button></div>`}</section>`;
  }
  function pModel(id) {
    const p = lazyOut('p:' + id, 'get', {id});
    const back = `<div><button class="btn soft sm" type="button" data-go="models">${svg(IC.back)}<span>All models</span></button></div>`;
    if (!p) return back + loading();
    if (p.error && !p.id) return back + `<section class="card">${err(p)}</section>`;
    const busy = BUSY.includes(p.status), pc = p.print_check, st = p.stats || {}, ex = p.exports || {};
    return `${back}
      <div class="nc-head"><div><h1 class="sd-h">${esc(p.title)}</h1><p class="lead">${esc(p.number)} · version ${esc(p.version || 0)} · ${esc(dmy(p.created_at))}</p></div><div>${pTag(p)}</div></div>
      ${busy ? `<section class="card"><div class="b3-run"><b>${esc(p.stage || (PST[p.status] || [''])[0])}</b><span></span><i><b style="width:${esc(Math.max(4, p.pct || 0))}%"></b></i>${CAN() ? `<button class="btn soft sm" type="button" data-stop="${esc(p.id)}">Stop</button>` : ''}</div></section>` : ''}
      ${p.status === 'failed' ? `<section class="card"><p class="cs-neg" style="margin:0">${esc(p.error || 'It could not be built.')}</p></section>` : ''}
      ${(p.renders || []).length ? `<section class="card"><div class="b3-shots">${p.renders.map(r => `<figure><img src="${esc(r.url)}" alt="${esc((VIEW[r.view] || r.view) + ' view')}" loading="lazy"><figcaption>${esc(VIEW[r.view] || r.view)}</figcaption></figure>`).join('')}</div>
        ${p.video ? `<video class="b3-video" src="${esc(p.video.url)}" controls loop muted playsinline></video>` : ''}
        ${p.notes ? `<p class="mut" style="margin:10px 0 0;font-size:14px">${esc(p.notes)}</p>` : ''}</section>` : ''}
      ${p.version ? `<section class="cs-hero"><div class="top">
        <div class="k"><div class="l">Size</div><div class="v b3-sm">${esc(size(st) || '—')}</div><div class="s">width × depth × height</div></div>
        <div class="k"><div class="l">Parts</div><div class="v">${esc(num(st.count || 0))}</div><div class="s">${esc(num(st.materials || 0))} materials</div></div>
        <div class="k"><div class="l">Triangles</div><div class="v">${esc(num(st.tris || 0))}</div><div class="s">detail of the mesh</div></div>
        <div class="k${pc && !pc.closed ? ' low bad' : ''}"><div class="l">3D print</div><div class="v b3-sm">${pc ? (pc.closed ? 'Fine' : 'Check first') : '—'}</div><div class="s">${pc ? esc(pc.closed ? 'every part closed' : pc.open_parts.slice(0, 2).join(', ') + ' open') : 'not asked'}</div></div></div></section>` : ''}
      ${Object.keys(ex).length ? `<section class="card"><h2 class="md-h2">Files</h2>${Object.entries(ex).map(([f, x]) => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1"><b>${esc(f.toUpperCase())}</b> <span class="mut">${esc(FMT[f] || '')} · ${esc(x.mb < 0.1 ? 'under 0.1' : x.mb)} MB</span></span>${x.too_big ? tag('Too big to keep', 'warn') : `<a class="btn soft sm" href="${esc(x.url)}" download="${esc(x.name)}">Download</a>`}</div>`).join('')}
        ${p.video ? `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1"><b>MP4</b> <span class="mut">360° spin video</span></span><a class="btn soft sm" href="${esc(p.video.url)}" download>Download</a></div>` : ''}
        <p class="cs-note">Also in your Docs and files. Download links last 10 days; open the model again for fresh ones.</p></section>` : ''}
      ${(p.warnings || []).length ? `<section class="card"><h2 class="md-h2">Worth a look</h2><ul class="ar-never">${p.warnings.map(w => `<li>${esc(w)}</li>`).join('')}</ul></section>` : ''}
      ${CAN() && !busy && p.version ? `<section class="card"><h2 class="md-h2">Change it</h2><form data-form="change" data-id="${esc(p.id)}" class="nc-grid">
          <label class="ins-lab wide">What to change (in your words)<textarea class="in" name="words" rows="2" placeholder="Make the handle bigger and the cup dark blue"></textarea></label>
          <details class="b3-more wide"><summary>Other files, views or quality</summary><div class="nc-grid" style="margin-top:10px">${optForm(p.options || {})}</div></details>
          <div class="md-acts wide"><span class="mut" style="font-size:13px">Words = a new version from this one. No words = the same model with the new files / views.</span><button class="btn" type="submit">Make version ${esc((p.version || 0) + 1)}</button></div></form></section>` : ''}
      ${(p.history || []).length > 1 ? `<section class="card"><h2 class="md-h2">Versions</h2>${p.history.slice().reverse().map(v => `<div class="b3-ver">${(v.renders || [])[0] ? `<img src="${esc(v.renders[0].url)}" alt="" loading="lazy">` : '<div class="b3-thumb empty"></div>'}<span><b>Version ${esc(v.n)}</b><span class="mut">${esc(v.words || (v.n === 1 ? 'first build' : 'new files'))} · ${esc(ago(v.at))}</span></span></div>`).join('')}</section>` : ''}
      ${p.script ? `<details class="card b3-script" data-key="script:${esc(p.id)}"${ST.open.has('script:' + p.id) ? ' open' : ''}><summary><h2 class="md-h2" style="margin:0">The Blender script</h2><span class="mut">${esc(pl(p.script.split('\n').length, 'line'))}</span></summary><pre class="ar-code"><code>${esc(p.script)}</code></pre></details>` : ''}
      ${CAN() ? `<div class="md-acts" style="gap:6px">${ask(`model ${p.number} ${p.title}`)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(p.id)}">Delete the model</button></div>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), d = s.defaults || {}, h = K().health || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your usual choices for every new model, and how sizes are shown.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Sizes</h2><form data-form="units" class="ar-row"><label class="ins-lab" style="flex:1">Show sizes in<select class="in" name="units"><option value="metric"${!imp() ? ' selected' : ''}>Millimetres / centimetres</option><option value="imperial"${imp() ? ' selected' : ''}>Inches</option></select></label>${CAN() ? '<button class="btn soft" type="submit">Save</button>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">Usual choices</h2><form data-form="defs" class="nc-grid">${optForm(d)}${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Used for every new model; you can still change them on each one.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">Blender on the server</h2><div class="cs-row"><span class="cs-dot${h.ready ? '' : ' bad'}"></span><span style="flex:1">${h.ready ? `Installed${h.kind ? ' (' + esc(h.kind) + ')' : ''}${h.no_network ? ', in a locked box with no internet' : ''}.` : 'Not installed yet - the admin runs deploy/setup_blender.sh on the server once.'}</span></div>
        <p class="cs-note">Up to 3 models build at once and 40 builds a day. Each script is checked before it runs: no files, no network, no settings outside the scene.</p></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Makes famous characters, real brand logos or real people.</li><li>Makes working or printable weapon parts.</li><li>Runs anything outside the locked box, or sends your models anywhere.</li><li>Shows a render without its "AI-generated" label.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  /* while a model is being built, the page follows it */
  setInterval(() => {
    if (!ST.d) return;
    const cur = ST.tab === 'models' && ST.arg ? ST.out['p:' + ST.arg] : null;
    if (cur && BUSY.includes(cur.status)) run('get', {id: ST.arg}).then(r => { ST.out['p:' + ST.arg] = r; if (!BUSY.includes(r.status)) refreshDesk(false); showPage(true); }).catch(() => {});
    else if ((K().busy || []).length && !(ST.tab === 'models' && ST.arg)) refreshDesk(true);
  }, 4000);
  const opts = fd => ({exports: fd.getAll('exports'), views: fd.getAll('views').slice(0, 4), quality: S(fd.get('quality')) || 'preview', aspect: S(fd.get('aspect')) || '1:1',
    style: S(fd.get('style')).trim(), background: S(fd.get('background')) || '#f4f4f6', turntable: fd.get('turntable') === 'on', print: fd.get('print') === 'on', transparent: fd.get('transparent') === 'on'});
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { delete ST.out['p:' + op.dataset.open]; location.hash = '#/models/' + op.dataset.open; return; }
    const id = t.closest('[data-idea]'); if (id) { ST.idea = IDEAS[Number(id.dataset.idea)][1]; const ta = $('#b3Page form[data-form=make] [name=brief]'); if (ta) { ta.value = ST.idea; ta.focus(); } return; }
    const btn = t.closest('button');
    try {
      const sp = t.closest('[data-stop]'); if (sp) { sp.disabled = true; await run('cancel', {id: sp.dataset.stop}); dropO('p:'); await changed('Stopped.'); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete it and its files')) return; dl.disabled = true; const r = await run('delete', {id: dl.dataset.del}); dropO('p:'); location.hash = '#/models'; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.mf) { ST.mf = el.value; showPage(true); return; }
    if (el.name === 'views') { const f = el.closest('form'); if (f && f.querySelectorAll('input[name=views]:checked').length > 4) { el.checked = false; toast('Up to 4 views.', true); } }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) btn.disabled = true;
    try {
      if (kind === 'make') { const r = await run('make', {brief: g('brief'), title: g('title'), ...opts(fd)}); ST.idea = ''; dropO('p:'); await refreshDesk(false);
        location.hash = '#/models/' + r.id; toast(`${r.number} started - it is being built now.`); }
      else if (kind === 'change') { const o = form.querySelector('details[open]') ? opts(fd) : {}; const r = await run('change', {id: form.dataset.id, words: S(fd.get('words')), ...o});
        dropO('p:'); await changed(`${r.number}: version ${(r.version || 0) + 1} is being built.`); }
      else if (kind === 'defs') { await run('settings', {defaults: opts(fd)}); await changed('Saved.'); }
      else if (kind === 'units') { await run('settings', {units: g('units')}); dropO('p:'); await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) btn.disabled = false; }
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
    const box = $('#b3Files'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/b3desk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'b3' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


