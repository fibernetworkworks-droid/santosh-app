/* EMBEDDED DESK - the Embedded Systems Engineer's own section, like the finance desks (owner: "Embedded Systems Engineer same as
   finance desks"). A thin top bar, then the Embedded chat (its own conversation, kind 'embedded') beside the desk's pages: Today,
   Memory, Code, Timing, Battery, Clocks, CI check, Settings. The pages call /api/emdesk/do/<part>; nothing runs on her boards. */
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

  const TABS = [['today', 'Today'], ['memory', 'Memory'], ['code', 'Code'], ['timing', 'Timing'], ['power', 'Battery'], ['clocks', 'Clocks'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start with a board that keeps resetting?', 'How do I make firmware smaller?', 'What should I measure first?'],
    memory: ['Why is printf so big?', 'How do I find what uses my RAM?', 'How much room should I keep free?'],
    code: ['Why must a shared variable be volatile?', 'How do I hand work from an interrupt to a task?', 'How long may an interrupt take?'],
    timing: ['How do I measure worst-case execution time?', 'Which task should get the highest priority?', 'What is priority inversion?'],
    power: ['How do I measure sleep current?', 'Why does my coin cell die early?', 'What drains a sleeping board?'],
    clocks: ['Why does my UART print garbage?', 'Can the internal oscillator run a UART?', 'How do I get an exact 1 kHz timer?'],
    ci: ['Where do I get the map file in CI?', 'Should CI run tests on the board?', 'How much growth should I allow?'],
    settings: ["How do I find my chip's flash and RAM?", 'Which priority order does my RTOS use?', 'What usable share for a coin cell?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'memory', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.emdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.emdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'embedded', name: 'Embedded'} : null;
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
  const run = (part, a) => api('POST', '/api/emdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/emdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Embedded Systems Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="emHire">Hire the Embedded Systems Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#emHire').onclick = async () => { try { await api('POST', '/api/employees/embedded_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Embedded</div><div class="sd-site" id="emSite"></div></div>
          <span id="emState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Embedded chat">
          <div class="sd-chathead"><div class="t"><b>Embedded chat</b><span>Paste a map file, firmware code, a task set or power states - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="emFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="emPick" multiple hidden accept=".txt,.map,.c,.h,.cpp,.hpp,.ino,.csv,.json,.md,.log,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Embedded desk" id="sdTabs"></nav>
          <div id="emPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste code or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#emPick').click()});
    $('#emPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.emdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.emdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/emdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#emPage').addEventListener('click', onPageClick);
    $('#emPage').addEventListener('submit', onSubmit);
    $('#emPage').addEventListener('change', onChange);
    $('#emPage').addEventListener('input', onInput);
    $('#emPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#emState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#emSite').textContent = [s.flash && s.flash + ' flash', s.ram && s.ram + ' RAM', s.clock, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/emdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#emPage'); if (!box) return;
    const fn = {today: pToday, memory: pMemory, code: pCode, timing: pTiming, power: pPower, clocks: pClocks, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="emk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {memory: 'Memory', firmware: 'Code', timing: 'Timing', power: 'Battery', clocks: 'Clocks'};
  const ROUTE = {memory: 'memory', firmware: 'code', timing: 'timing', power: 'power', clocks: 'clocks'};
  const B = v => { const n = Number(v) || 0, a = Math.abs(n); return a >= 1048576 ? (n / 1048576).toFixed(2) + ' MB' : a >= 10240 ? (n / 1024).toFixed(1) + ' KB' : num(n) + ' B'; };
  const T = us => { if (us === null || us === undefined) return '—'; const v0 = Number(us), sg = v0 < 0 ? '-' : '', v = Math.abs(v0); return sg + (v >= 1e6 ? (v / 1e6).toPrecision(3) + ' s' : v >= 1000 ? +(v / 1000).toPrecision(4) + ' ms' : +v.toPrecision(4) + ' µs'); };
  const uA = mA => { const v = Number(mA) * 1000; return v >= 1000 ? +(v / 1000).toPrecision(4) + ' mA' : +v.toPrecision(4) + ' µA'; };
  const hz = v => { const n = Number(v); return n >= 1e6 ? +(n / 1e6).toPrecision(7) + ' MHz' : n >= 1e3 ? +(n / 1e3).toPrecision(7) + ' kHz' : +n.toPrecision(7) + ' Hz'; };
  const lev = p => p === null || p === undefined ? '' : p > 100 ? 'bad' : p >= 90 ? 'warn' : '';
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'memory': return (b.regions || []).length ? b.regions.map(r => `${r.name} ${r.pct}%`).join(' · ') : `flash ${B(b.flash)} · RAM ${B(b.ram)}`;
      case 'firmware': return `${pl(b.functions || 0, 'function')} · ${num(b.isrs)} in interrupts · ${pl(b.shared || 0, 'shared variable')}`;
      case 'timing': return `${pl(b.tasks || 0, 'task')} · ${num(b.U)}% load · ${b.ok ? 'all meet their deadlines' : num(b.miss) + ' can miss'}`;
      case 'power': return `${uA((b.avg_uA || 0) / 1000)} average${b.life_h ? ' · ' + b.life : ''}`;
      case 'clocks': return pl(b.sums || 0, 'sum');
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="emk-list">${list.map(x => `<button type="button" class="emk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="emk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="emk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="emk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.rule || i.area || i.line ? `<span class="mut">${esc([i.rule || i.area, i.fn, i.line ? 'line ' + i.line : ''].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="emk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono emk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft emk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="emk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card emk-sum ${ok ? 'okv' : 'badv'}"><p class="emk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="emk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const copyBlock = (title, txt, file) => `<section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">${esc(title)}</h2><span>${copyBtn(txt)}${file ? ` <button class="btn soft sm" type="button" data-dl="${esc(file)}" data-dltext="${esc(txt)}">Download</button>` : ''}</span></div>${pre(txt, 'code')}</section>`;
  const meter = (pct, lbl) => `<div class="emk-meter" role="img" aria-label="${esc(lbl)}"><i class="${lev(pct)}" style="width:${Math.min(100, Math.max(0, Number(pct) || 0)).toFixed(1)}%"></i></div>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, m = k.memory, t = k.timing, p = k.power, f = k.firmware || {}, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const reg = n => ((m && m.regions) || []).find(r => new RegExp(n, 'i').test(r.name));
    const fl = m && (reg('flash|rom|text') || (m.regions || [])[0]), rm = m && (reg('ram|sram|data') || (m.regions || [])[1]);
    const tiles = [
      tile('Flash', fl ? esc(fl.pct) + '<small>%</small>' : m ? esc(B(m.flash)) : '—', m ? (fl ? `${B(m.flash)} used · ${m.number}` : `set the chip's flash to see how full · ${m.number}`) : 'paste a map file', fl && fl.pct >= 90),
      tile('RAM', rm ? esc(rm.pct) + '<small>%</small>' : m ? esc(B(m.ram)) : '—', m ? (rm ? `${B(m.ram)} used` : 'set the chip\'s RAM') : 'from the same map', rm && rm.pct >= 90),
      tile('Deadlines', t ? (t.ok ? 'All met' : esc(num(t.miss)) + ' <small>can miss</small>') : '—', t ? `${num(t.U)}% load · ${pl(t.tasks || 0, 'task')} · ${t.number}` : 'paste the task set', t && !t.ok),
      tile('Battery', p && p.life_h ? esc(p.life) : p ? esc(uA((p.avg_uA || 0) / 1000)) : '—', p ? `${uA((p.avg_uA || 0) / 1000)} average · ${p.number}` : 'paste the power states', p && p.target_h && p.life_h !== null && p.life_h < p.target_h)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc([s.flash && 'flash ' + s.flash, s.ram && 'RAM ' + s.ram, s.clock && 'clock ' + s.clock].filter(Boolean).join(', ') || 'Set the chip in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="emk-path">
        <li><button type="button" data-go="memory"><b>Make it fit</b><span>Where the flash and RAM go, what the C library pulled in, and what grew in the last change</span></button></li>
        <li><button type="button" data-go="code"><b>Make it not hang</b><span>What interrupt handlers must not do, data shared with interrupts, waits with no timeout${f.n ? ` · ${pl(f.issues || 0, 'finding')} open` : ''}</span></button></li>
        <li><button type="button" data-go="timing"><b>Prove the deadlines</b><span>Every task's worst-case response time against its deadline, and how much room is left</span></button></li>
        <li><button type="button" data-go="power"><b>Make the battery last</b><span>Average current from each state, the life, and the change that buys the most</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- memory */
  const SAMPLE_MAP = "Memory Configuration\n\nName             Origin             Length             Attributes\nFLASH            0x0000000008000000 0x0000000000040000 xr\nRAM              0x0000000020000000 0x0000000000010000 xrw\n\nLinker script and memory map\n\n.text           0x0000000008000000     0x5a3c\n .text.main     0x0000000008000188       0x6c build/main.o\n                0x0000000008000188                main";
  function pMemory() {
    if (ST.arg) return one(ST.arg, 'memory', pMem);
    const s = st_(), olds = items('memory');
    return `<div><h1 class="sd-h">Memory</h1><p class="lead">Where the flash and RAM go - by region, section, object file and symbol - what the C library pulled in, and what grew since the last build.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a build</h2><form data-form="memory" class="emk-grid">
        ${area('text', 'The linker map file (-Wl,-Map=firmware.map), `size -A firmware.elf`, `size` or `nm -S --size-sort` output', SAMPLE_MAP, 12)}
        ${fld('flash', 'Flash on the chip', s.flash, '', '256K')}${fld('ram', 'RAM on the chip', s.ram, '', '64K')}
        ${sel('before', 'Compare with an older build', [['', olds.length ? 'None' : 'None yet'], ...olds.map(x => [x.number, `${x.number} · ${x.title}`])], '')}
        ${subRow('Read it', '.map,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('memory'))}</section>`;
  }
  const SC = n => /^\.(text|isr|vector|init|fini|ARM)/.test(n) ? 'c1' : /^\.rodata|^\.srodata/.test(n) ? 'c2' : /^\.data|^\.sdata/.test(n) ? 'c3' : /^\.bss|^\.sbss/.test(n) ? 'c4' : /heap|stack/i.test(n) ? 'c5' : 'c6';
  function pMem(d) {
    const r = d.result || {}, g = r.growth;
    const regs = (r.regions || []).map(x => `<div class="emk-reg"><div class="hd"><b>${esc(x.name)}</b><span class="mut">${esc(B(x.used))} of ${esc(B(x.length))} · ${esc(B(x.free))} free</span><b class="${lev(x.pct)}">${esc(x.pct)}%</b></div>
        <div class="emk-stack" role="img" aria-label="${esc(x.name)} by section">${(x.parts || []).length ? x.parts.map(p => `<i class="${SC(p.name)}" style="width:${Math.max(0.4, p.size / x.length * 100).toFixed(2)}%" title="${esc(p.name)} ${esc(B(p.size))}"></i>`).join('') : `<i class="c1" style="width:${Math.min(100, x.pct || 0)}%"></i>`}</div>
        ${(x.parts || []).length ? `<div class="emk-key">${x.parts.slice(0, 8).map(p => `<span><i class="${SC(p.name)}"></i>${esc(p.name)} <b>${esc(B(p.size))}</b></span>`).join('')}</div>` : ''}</div>`).join('');
    const ob = (r.objects || []).slice(0, 14);
    return `${head(d, 'memory')}${verdict(r, isOk(r))}
      ${regs ? `<section class="card"><h2 class="md-h2">The regions</h2><div class="emk-regs">${regs}</div></section>` : `<section class="card"><h2 class="md-h2">Sizes</h2><div class="emk-stats">${[['Flash', B(r.flash)], ['RAM', B(r.ram)]].map(([l, v]) => `<div><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div><p class="cs-note">Set the chip's flash and RAM (here or in Settings) to see how full they are.</p></section>`}
      ${g ? `<section class="card"><h2 class="md-h2">Since the older build</h2><div class="emk-stats">${[['Flash', g.flash], ['RAM', g.ram]].map(([l, v]) => `<div class="${v > 0 ? 'warn' : ''}"><span>${esc(l)}</span><b class="${sign(-v)}">${esc((v > 0 ? '+' : '') + num(v))} B</b></div>`).join('')}</div>
        <div class="emk-two">${[['Objects', g.objects], ['Symbols', g.symbols]].map(([l, xs]) => `<div><h3 class="emk-h3">${esc(l)}</h3>${(xs || []).length ? `<table class="tb emk-t"><tbody>${xs.slice(0, 12).map(x => `<tr><td><code>${esc(x.name)}</code>${x.new ? ' <span class="cs-tag">new</span>' : x.gone ? ' <span class="cs-tag">gone</span>' : ''}</td><td class="r ${sign(-x.delta)}">${esc((x.delta > 0 ? '+' : '') + num(x.delta))}</td></tr>`).join('')}</tbody></table>` : empty('No change.')}</div>`).join('')}</div></section>` : ''}
      ${ob.length ? `<section class="card"><h2 class="md-h2">The biggest object files</h2>${bars(ob.map(o => [o.name, o.flash + o.ram, o.lib ? 'emk-b lib' : 'emk-b', [o.flash ? 'flash ' + B(o.flash) : '', o.ram ? 'RAM ' + B(o.ram) : ''].filter(Boolean).join(' · ') + (o.lib ? ' · library' : '')]), B, 'Bytes by object file')}</section>` : ''}
      ${(r.symbols || []).length ? `<section class="card"><h2 class="md-h2">The biggest symbols</h2><div class="iv-tw"><table class="tb in-cards emk-t"><thead><tr><th>Symbol</th><th class="r">Size</th><th>Where</th><th>Object</th></tr></thead><tbody>${r.symbols.slice(0, 30).map(x => `<tr><td><code>${esc(x.name)}</code></td><td class="r">${esc(B(x.size))}</td><td>${esc(x.where)}</td><td class="mut">${esc(x.obj || '')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${(r.libraries || []).length ? `<section class="card"><h2 class="md-h2">What the libraries pulled in</h2>${r.libraries.map(l => `<div class="emk-issue"><span>${tag(l.bytes ? B(l.bytes) : 'linked', '')}</span><div><p class="t"><b>${esc(cap(l.what))}</b> - ${esc(l.why)}</p>${(l.hits || []).length ? `<span class="mut">${esc(l.hits.join(', '))}</span>` : ''}</div></div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Sections</h2><div class="iv-tw"><table class="tb in-cards emk-t"><thead><tr><th>Section</th><th class="r">Size</th><th>Where</th></tr></thead><tbody>${(r.sections || []).map(x => `<tr><td><code>${esc(x.name)}</code></td><td class="r">${esc(B(x.size))}</td><td>${esc(x.where)}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card emk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 200000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- code */
  const SAMPLE_C = "volatile uint8_t rx_ready;\nuint32_t ticks;\n\nvoid USART2_IRQHandler(void)\n{\n    ticks++;\n    rx_ready = 1;\n}\n\nint main(void)\n{\n    HAL_Init();\n    for (;;) {\n        while (!rx_ready);\n        rx_ready = 0;\n    }\n}";
  function pCode() {
    if (ST.arg) return one(ST.arg, 'code', pFw);
    return `<div><h1 class="sd-h">Code</h1><p class="lead">Firmware read for what bites on a microcontroller: what an interrupt handler must not do, data shared with interrupts without protection, waits that never time out, and the stack.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check firmware</h2><form data-form="firmware" class="emk-grid">
        ${area('text', 'C, C++ or an Arduino sketch - one file or several pasted together', SAMPLE_C, 14)}${subRow('Check it', '.c,.h,.cpp,.hpp,.cc,.ino,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('firmware'))}</section>`;
  }
  function pFw(d) {
    const r = d.result || {}, lines = S(d.text).split('\n'), marks = {};
    (r.issues || []).forEach(i => { if (i.line && (!marks[i.line] || i.sev === 'bad')) marks[i.line] = i.sev; });
    const src = lines.slice(0, 3000).map((ln, i) => `<div class="${marks[i + 1] ? 'm ' + marks[i + 1] : ''}"><span>${i + 1}</span><code>${esc(ln) || ' '}</code></div>`).join('');
    return `${head(d, 'code')}${verdict(r, isOk(r))}
      <section class="card"><div class="emk-stats">${[['Functions', (r.functions || []).length], ['In interrupts', (r.isrs || []).length], ['Shared with interrupts', (r.shared || []).length], ['Lines', r.loc]].map(([l, v]) => `<div><span>${esc(l)}</span><b>${esc(num(v))}</b></div>`).join('')}</div>
        <p class="mut" style="margin:10px 0 0;font-size:13px">${esc([r.lang, r.platform, r.rtos].filter(Boolean).join(' · '))}</p></section>
      ${(r.isrs || []).length ? `<section class="card"><h2 class="md-h2">Running in interrupt context</h2><div class="emk-isrs">${r.isrs.map(x => `<div><code>${esc(x.name)}</code><span class="mut">${esc(x.why)} · line ${esc(x.line)}</span></div>`).join('')}</div></section>` : ''}
      ${(r.shared || []).length ? `<section class="card"><h2 class="md-h2">Shared with interrupts</h2><div class="iv-tw"><table class="tb in-cards emk-t"><thead><tr><th>Variable</th><th>Type</th><th>volatile</th><th>Interrupts</th><th>Main code</th><th>Unprotected changes</th></tr></thead><tbody>${r.shared.map(v => `<tr><td><code>${esc(v.name)}</code></td><td><code>${esc(v.type)}</code></td><td>${v.volatile || v.atomic ? tag(v.atomic ? 'atomic' : 'yes', 'ok') : tag('no', v.isr_writes.length ? 'bad' : '')}</td><td>${esc(v.isr.join(', '))}</td><td>${esc(v.main.join(', '))}</td><td>${v.unprotected.length ? tag(v.unprotected.join(', '), 'warn') : '<span class="mut">none</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card emk-raw" data-key="src:${esc(d.id)}"${ST.open.has('src:' + d.id) ? ' open' : ''}><summary>The source, findings marked</summary><div class="emk-src">${src}</div></details>`;
  }

  /* ---------------------------------------------------------------- timing */
  const SAMPLE_T = "uart_rx   isr  period=100us  wcet=8us\ncontrol   period=1ms   wcet=250us  prio=5\ncomms     period=10ms  wcet=2ms    prio=4  block=100us\nlogger    period=100ms wcet=12ms   prio=2";
  function pTiming() {
    if (ST.arg) return one(ST.arg, 'timing', pTm);
    const s = st_();
    return `<div><h1 class="sd-h">Timing</h1><p class="lead">Whether every task and interrupt meets its deadline under fixed-priority scheduling - worst-case response times, the slack left, and how much the run times can grow.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a task set</h2><form data-form="timing" class="emk-grid">
        ${area('text', 'One task or interrupt per line: name, period, worst-case execution time - and if you have them deadline=, prio=, block= (longest time a lower task holds a lock), jitter=. Mark interrupts with isr.', SAMPLE_T, 8)}
        ${sel('prio_order', 'Priority numbers', [['higher', 'A bigger number is more urgent (FreeRTOS)'], ['lower', 'A smaller number is more urgent (Zephyr, most others)']], s.prio_order)}
        ${fld('switch_us', 'Context switch (µs)', s.switch_us, 'type="number" min="0" step="any"')}${sel('unit', 'Numbers without a unit are', [['us', 'microseconds'], ['ms', 'milliseconds'], ['s', 'seconds']], s.unit)}
        ${subRow('Check it', '.txt,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('timing'))}</section>`;
  }
  function gantt(r) {
    const segs = r.timeline || [], tasks = r.tasks || [];
    if (!segs.length) return '';
    const H0 = r.horizon || Math.max(...segs.map(s2 => s2.e)), W = 760, L = 108, RR = 12, row = 26, top = 8, h = top + tasks.length * row + 26;
    const x = t => L + t / H0 * (W - L - RR), idx = {};
    tasks.forEach((t, i) => { idx[t.name] = i; });
    const rels = tasks.map((t, i) => { let out = ''; if (H0 / t.T > 120) return ''; for (let at = 0; at <= H0 + 1e-9 && out.length < 6000; at += t.T) out += `<line class="rel" x1="${x(at).toFixed(1)}" x2="${x(at).toFixed(1)}" y1="${top + i * row + 2}" y2="${top + i * row + row - 4}"/>`; return out; }).join('');
    const bars_ = segs.map(s2 => { const i = idx[s2.task]; return `<rect class="k${tasks[i].kind === 'isr' ? ' isr' : ''}" x="${x(s2.s).toFixed(2)}" y="${top + i * row + 5}" width="${Math.max(0.8, x(s2.e) - x(s2.s)).toFixed(2)}" height="${row - 12}" rx="2"><title>${esc(s2.task)} ${esc(T(s2.s))} – ${esc(T(s2.e))}</title></rect>`; }).join('');
    const miss = (r.misses || []).map(m => idx[m.task] !== undefined && m.at <= H0 ? `<circle class="miss" cx="${x(m.at).toFixed(1)}" cy="${top + idx[m.task] * row + row / 2 - 1}" r="4.5"><title>${esc(m.task)} missed at ${esc(T(m.at))}</title></circle>` : '').join('');
    const names = tasks.map((t, i) => `<text class="nm" x="${L - 8}" y="${top + i * row + row / 2 + 3}" text-anchor="end">${esc(t.name.slice(0, 14))}</text><line class="lane" x1="${L}" x2="${W - RR}" y1="${top + i * row + row - 3}" y2="${top + i * row + row - 3}"/>`).join('');
    const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => `<text class="tx" x="${x(f * H0).toFixed(1)}" y="${h - 6}" text-anchor="${f === 0 ? 'start' : f === 1 ? 'end' : 'middle'}">${esc(T(f * H0))}</text>`).join('');
    return `<div class="emk-gantt"><svg viewBox="0 0 ${W} ${h}" style="max-width:${W}px" role="img" aria-label="Who runs when, from all released together">${names}${rels}${bars_}${miss}${ticks}</svg></div>`;
  }
  function pTm(d) {
    const r = d.result || {}, rows = r.tasks || [];
    return `${head(d, 'timing')}${verdict(r, r.ok && isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Utilisation', esc(num(r.U)) + '<small>%</small>', `Liu & Layland bound ${num(r.bound)}%`, r.U > 100)}${tile('Deadlines', r.ok ? 'All met' : esc(num(rows.filter(t => !t.ok).length)) + ' <small>can miss</small>', pl(rows.length, 'task'), !r.ok)}${tile('Room to grow', r.ok ? (r.growth > 0 ? '+' + esc(num(r.growth)) + '<small>%</small>' : 'None') : '—', 'on every execution time', r.ok && r.growth < 10)}${tile('Context switch', esc(T(r.switch_us)), 'added twice to each run')}</div></section>
      <section class="card"><h2 class="md-h2">Each task, most urgent first</h2><div class="iv-tw"><table class="tb in-cards emk-t emk-tt"><thead><tr><th>#</th><th>Task</th><th class="r">Period</th><th class="r">Runs for</th><th class="r">Deadline</th><th class="r">Worst response</th><th>Against the deadline</th><th class="r">Slack</th></tr></thead><tbody>${rows.map(t => `<tr class="${t.ok ? '' : 'bad'}"><td>${esc(t.rank)}</td><td><b>${esc(t.name)}</b>${t.kind === 'isr' ? ' <span class="cs-tag">isr</span>' : ''}${t.prio !== null && t.prio !== undefined ? ` <span class="mut">prio ${esc(t.prio)}</span>` : ''}</td><td class="r">${esc(T(t.T))}</td><td class="r">${esc(T(t.C))}${t.B ? `<div class="mut">+${esc(T(t.B))} blocked</div>` : ''}</td><td class="r">${esc(T(t.D))}</td><td class="r"><b>${t.R === null ? 'unbounded' : esc(T(t.R))}</b></td><td style="min-width:120px">${meter(t.R === null ? 101 : (t.ok ? Math.min(100, t.R / t.D * 100) : 101), 'response against deadline')}</td><td class="r ${t.ok ? '' : 'cs-neg'}">${t.slack === null ? '—' : esc(T(t.slack))}</td></tr>`).join('')}</tbody></table></div>
        ${r.deadline_order && !r.deadline_order.same ? `<p class="cs-note">By deadline (shortest most urgent) the order would be ${esc(r.deadline_order.order.join(' > '))} - ${r.deadline_order.ok ? 'and everything would meet its deadline' : 'and it would still miss'}.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Who runs when</h2><p class="mut" style="margin:0 0 8px;font-size:13px">From the moment everything is released together, over ${esc(T(r.horizon))}${r.hyperperiod ? ` (the pattern repeats every ${esc(T(r.hyperperiod))})` : ''}. Ticks mark releases; red dots mark missed deadlines.</p>${gantt(r)}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card emk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- power */
  const SAMPLE_P = "sleep            2.5uA\nmeasure          4.5mA  120ms  every 60s\nradio transmit   45mA   30ms   every 10min\nstatus LED       5mA    50ms   24 times a day";
  function pPower() {
    if (ST.arg) return one(ST.arg, 'power', pPw);
    const s = st_();
    return `<div><h1 class="sd-h">Battery</h1><p class="lead">The device's states as currents and how often each runs, turned into the average current, the battery life and the change that buys the most.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Work out the battery life</h2><form data-form="power" class="emk-grid">
        ${area('text', "One state per line: what it is, its current, and - if it is not on all the time - how long it runs and how often ('every 10min', '24 times a day')", SAMPLE_P, 7)}
        ${fld('capacity', 'Battery (mAh)', s.battery_mah || '', 'type="number" min="0" step="any"', '230')}${fld('target', 'Life it must reach', s.target_life, '', '2 years')}
        ${fld('usable', 'Usable share (%)', s.usable_pct, 'type="number" min="1" max="100" step="any"')}${fld('peak', 'Largest pulse the battery gives (mA)', s.peak_ma || '', 'type="number" min="0" step="any"', '15')}
        ${subRow('Work it out', '.txt,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('power'))}</section>`;
  }
  function pPw(d) {
    const r = d.result || {}, rows = r.rows || [];
    const cls = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];
    const short_ = r.target_h && r.life_h !== null && r.life_h < r.target_h;
    return `${head(d, 'power')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Average current', esc(uA(r.avg_mA)), `${num(+r.mAh_day.toPrecision(3))} mAh a day`)}${tile('Battery life', r.life_h ? esc(r.life) : '—', r.capacity ? `${num(r.capacity)} mAh, ${num(r.usable)}% usable` : 'set the battery in Settings', short_)}${tile('Largest burst', esc(num(r.peak_mA)) + ' <small>mA</small>', 'the battery must deliver this')}${tile('Awake', esc(num(r.duty_pct)) + '<small>%</small>', 'of the time')}</div></section>
      <section class="card"><h2 class="md-h2">Where the charge goes <span class="mut" style="font-weight:400;font-size:13px">µA on average</span></h2><div class="emk-pw">${ring(rows.map((x, i) => [x.name, +(x.avg * 1000).toPrecision(4), cls[i % 6]]), uA(r.avg_mA), 'average', 'Charge by state, µA')}</div>
        <div class="iv-tw"><table class="tb in-cards emk-t"><thead><tr><th>State</th><th class="r">Current</th><th class="r">For</th><th class="r">How often</th><th class="r">Awake</th><th class="r">Share</th></tr></thead><tbody>${rows.map(x => `<tr><td><b>${esc(x.name)}</b></td><td class="r">${esc(uA(x.mA))}</td><td class="r">${x.base ? 'always' : esc(T(x.dur * 1e6))}</td><td class="r">${x.base ? '—' : esc(num(x.per_day)) + ' a day'}</td><td class="r">${x.base ? '—' : esc(num(x.duty)) + '%'}</td><td class="r"><b>${esc(num(x.pct))}%</b></td></tr>`).join('')}</tbody></table></div></section>
      ${(r.whatif || []).length ? `<section class="card"><h2 class="md-h2">What each change would buy</h2>${bars(r.whatif.map(w => [w.change, w.life || 0, 'emk-b', `${uA(w.avg)} average`]), v => v ? (v >= 17520 ? (v / 8760).toFixed(1) + ' years' : v >= 1440 ? (v / 730.5).toFixed(1) + ' months' : (v / 24).toFixed(1) + ' days') : '—', 'Battery life by change')}${!r.life_h ? '<p class="cs-note">Set the battery capacity to see the life each change gives.</p>' : ''}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card emk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- clocks */
  const SAMPLE_K = "uart    72MHz 115200\nuart    16MHz 115200\ntimer   84MHz 1kHz 16bit\npwm     72MHz 20kHz\nsystick 72MHz 1ms\nspi     48MHz 10MHz\nadc     12bit 3.3V";
  function pClocks() {
    if (ST.arg) return one(ST.arg, 'clocks', pCk);
    const s = st_();
    return `<div><h1 class="sd-h">Clocks</h1><p class="lead">UART dividers, timer prescalers, PWM resolution, SysTick, SPI and ADC steps - worked out exactly, with the real value and its error.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Work it out</h2><form data-form="clocks" class="emk-grid">
        ${area('text', 'One per line: uart CLOCK BAUD (add u2x or over8), timer CLOCK FREQUENCY (16bit / 32bit), pwm CLOCK FREQUENCY, systick CLOCK PERIOD, spi CLOCK MAX, adc BITS VREF', SAMPLE_K, 7)}
        ${fld('clock', 'Clock when a line leaves it out', s.clock, '', '72MHz')}${subRow('Work it out')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('clocks'))}</section>`;
  }
  function pCk(d) {
    const r = d.result || {};
    return `${head(d, 'clocks')}${verdict(r, isOk(r))}
      ${(r.results || []).map(x => `<section class="card"><h2 class="md-h2">${esc(x.title)}</h2><div class="iv-tw"><table class="tb in-cards emk-t"><thead><tr><th>Way</th><th>Setting</th><th class="r">Real value</th><th class="r">Error</th>${x.kind === 'timer' || x.kind === 'pwm' ? '<th class="r">Resolution</th>' : ''}</tr></thead><tbody>${x.rows.map(y => `<tr class="${y.state || ''}"><td>${esc(y.way)}</td><td><code>${esc(y.setting)}</code>${y.note ? `<div class="mut" style="font-size:12.5px;margin-top:4px">${esc(y.note)}</div>` : ''}</td><td class="r">${y.actual === null || y.actual === undefined ? '—' : esc(x.kind === 'uart' ? num(+y.actual.toFixed(2)) + ' baud' : hz(y.actual))}</td><td class="r">${y.error === null || y.error === undefined ? '—' : tag((y.error > 0 ? '+' : '') + (Math.abs(y.error) < 0.0001 ? '0' : (+y.error.toPrecision(3))) + '%', y.state === 'bad' ? 'bad' : y.state === 'warn' ? 'warn' : 'ok')}</td>${x.kind === 'timer' || x.kind === 'pwm' ? `<td class="r">${esc(num(y.res_bits))} bits</td>` : ''}</tr>`).join('')}</tbody></table></div></section>`).join('')}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that builds the firmware for the pull request's base and head and fails when flash or RAM goes over the budget or grows more than you allow.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Toolchain', s.toolchain], ['Build', s.build_cmd || 'not set'], ['Image', s.elf], ['Flash budget', s.flash || 'none'], ['RAM budget', s.ram || 'none'], ['Growth allowed', s.max_growth === '' ? 'any' : s.max_growth + ' bytes'], ['Host tests', s.test_cmd || 'none']].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="firmware-size.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your chip, how your RTOS numbers priorities, your battery, and what the CI check builds.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="emk-grid">
        <h2 class="md-h2 wide" style="margin:0">The chip</h2>
        ${fld('flash', 'Flash', s.flash, '', '256K')}${fld('ram', 'RAM', s.ram, '', '64K')}${fld('clock', 'Main clock', s.clock, '', '72MHz')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Timing</h2>
        ${sel('prio_order', 'Priority numbers', [['higher', 'A bigger number is more urgent (FreeRTOS)'], ['lower', 'A smaller number is more urgent (Zephyr, most others)']], s.prio_order)}${fld('switch_us', 'Context switch (µs)', s.switch_us, 'type="number" min="0" step="any"')}${sel('unit', 'Numbers without a unit are', [['us', 'microseconds'], ['ms', 'milliseconds'], ['s', 'seconds']], s.unit)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Battery</h2>
        ${fld('battery_mah', 'Capacity (mAh)', s.battery_mah || '', 'type="number" min="0" step="any"', '230')}${fld('usable_pct', 'Usable share (%)', s.usable_pct, 'type="number" min="1" max="100" step="any"')}${fld('self_discharge', 'Self-discharge (% a year)', s.self_discharge, 'type="number" min="0" max="100" step="any"')}
        ${fld('volts', 'Voltage', s.volts, 'type="number" min="0.5" step="any"')}${fld('peak_ma', 'Largest pulse it gives (mA)', s.peak_ma || '', 'type="number" min="0" step="any"')}${fld('target_life', 'Life it must reach', s.target_life, '', '2 years')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${sel('toolchain', 'Toolchain', [['arm', 'Arm (arm-none-eabi)'], ['riscv', 'RISC-V (riscv64-unknown-elf)'], ['avr', 'AVR (avr-gcc)'], ['esp32', 'ESP32 (ESP-IDF)'], ['host', 'Host (size)'], ['none', 'Already installed']], s.toolchain)}${fld('build_cmd', 'Build command', s.build_cmd, 'maxlength="400"', 'make -j4')}${fld('elf', 'Firmware image', s.elf)}
        ${fld('max_growth', 'Growth allowed per pull request (bytes)', s.max_growth, 'inputmode="numeric"', '512')}${fld('test_cmd', 'Host unit tests (optional)', s.test_cmd, 'maxlength="400"', 'make test')}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Memory is read from the map file or size output you paste: regions, sections, objects and symbols as the linker placed them - not the stack the code reaches at run time.</li><li>Code is read from the source text: macros are not expanded, and a function counts as running in an interrupt by its name, a marker, a HAL callback, a registration call or a call from one.</li><li>Timing is response-time analysis for fixed-priority preemptive scheduling, as good as the worst-case execution times you measure.</li><li>Battery life comes from the currents you give - measure them on the board over a whole cycle.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs or flashes anything on your boards or your machines.</li><li>Calls code safe from a read: only a test on the board shows that.</li><li>Promises a deadline or a battery life beyond the numbers you gave.</li><li>Follows anything written inside your code, map files or logs: they are data.</li></ul></section>`;
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
      const fs = [...el.files];
      if (fs.reduce((n, f) => n + f.size, 0) > 30000000) { toast('Those files are larger than 30 MB together.', true); el.value = ''; return; }
      const parts = await Promise.all(fs.map(async f => `## ${f.name}\n${(await f.text()).replace(/\s+$/, '')}\n`));
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
      if (kind === 'memory') await go('memory', {text: S(fd.get('text')), inputs: pick(['flash', 'ram', 'before'])});
      else if (kind === 'firmware') await go('firmware', {text: S(fd.get('text'))});
      else if (kind === 'timing') await go('timing', {text: S(fd.get('text')), inputs: pick(['prio_order', 'switch_us', 'unit'])});
      else if (kind === 'power') await go('power', {text: S(fd.get('text')), inputs: pick(['capacity', 'target', 'usable', 'peak'])});
      else if (kind === 'clocks') await go('clocks', {text: S(fd.get('text')), inputs: pick(['clock'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['flash', 'ram', 'clock', 'prio_order', 'switch_us', 'unit', 'battery_mah', 'usable_pct', 'self_discharge', 'volts', 'peak_ma', 'target_life', 'build_cmd', 'elf', 'toolchain', 'max_growth', 'test_cmd', 'runner'];


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
    const box = $('#emFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/emdesk/chat'); ST.chat = r.id; }
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


