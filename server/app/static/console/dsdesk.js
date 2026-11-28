/* DISTRIBUTED DESK - the Distributed Systems Engineer's own section, like the finance desks (owner: "Distributed Systems Engineer
   same as finance desks"). A thin top bar, then the Distributed chat (its own conversation, kind 'distsys') beside the desk's pages:
   Today, Retries, Quorums, Histories (linearizability + the fault-injection simulator), Specs (TLA+), Settings. The pages call
   /api/dsdesk/do/<part>; nothing runs on her systems. */
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

  const TABS = [['today', 'Today'], ['retries', 'Retries'], ['quorums', 'Quorums'], ['histories', 'Histories'], ['specs', 'Specs'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What can you check for me?', 'Is my service safe to retry?', 'How do I test for split brain?'],
    retries: ['Which jitter should I use?', 'Where should retries live in my chain?', 'What is a retry budget?'],
    quorums: ['3 or 5 replicas?', 'How should I spread nodes across zones?', 'Is R + W > N enough?'],
    histories: ['Why is this not linearizable?', 'How do I record a history in my tests?', 'What does the simulator show?'],
    specs: ['Explain this spec line by line', 'How do I model my protocol in TLA+?', 'What should my invariant be?'],
    settings: ['What failure rate should I test with?', 'Where should specs live?', 'How long should TLC run in CI?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', spec: '', fixed: false, busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dsdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dsdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'distsys_eng', name: 'Distributed'} : null;
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
  const run = (part, a) => api('POST', '/api/dsdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dsdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Distributed Systems Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dsHire">Hire the Distributed Systems Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dsHire').onclick = async () => { try { await api('POST', '/api/employees/distsys_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Distributed</div><div class="sd-site" id="dsSite"></div></div>
          <span id="dsState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Distributed chat">
          <div class="sd-chathead"><div class="t"><b>Distributed chat</b><span>Paste a history, TLC output or a retry policy - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dsFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dsPick" multiple hidden accept=".txt,.log,.json,.edn,.tla,.cfg,.yml,.yaml,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Distributed desk" id="sdTabs"></nav>
          <div id="dsPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a history or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dsPick').click()});
    $('#dsPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dsdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dsdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dsdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dsPage').addEventListener('click', onPageClick);
    $('#dsPage').addEventListener('submit', onSubmit);
    $('#dsPage').addEventListener('change', onChange);
    $('#dsPage').addEventListener('input', onInput);
    $('#dsPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dsState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#dsSite').textContent = [s.system, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), h = k.histories || {};
    const n = {histories: h.fail || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dsdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dsPage'); if (!box) return;
    const fn = {today: pToday, retries: pRetries, quorums: pQuorums, histories: pHistories, specs: pSpecs, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="dsk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Check', 'warn'], info: ['Note', '']};
  const ms = v => v === null || v === undefined ? '—' : Number(v) >= 10000 ? num(Math.round(v / 100) / 10) + ' s' : num(Math.round(v)) + ' ms';
  const PNAME = {leader: 'One leader', quorum: 'Quorum, no read repair', quorum_repair: 'Quorum with read repair (ABD)', quorum_partition: 'Quorum + partition',
    lww: 'Last writer wins', lww_skew: 'Last writer wins + clock skew', async: 'Async primary-backup', async_failover: 'Async primary-backup + failover'};
  const RES = {ok: ['Linearizable', 'ok'], fail: ['Not linearizable', 'bad'], unknown: ['Could not decide', 'warn']};
  function brief(x) {
    const b = x.brief || {};
    if (x.kind === 'retry') return `worst ${ms(b.worst_ms)} · ${num(b.load)}x load when failing · ${b.jitter} jitter`;
    if (x.kind === 'chain') return `${pl(b.hops || 0, 'service')} · one request can become ${num(b.amplification)}`;
    if (x.kind === 'quorum') return b.mode === 'consensus' ? `${num(b.n)} voters` : `N=${num(b.n)} · ${b.overlap ? 'reads meet writes' : 'reads can be stale'}`;
    if (x.kind === 'history' || x.kind === 'sim') return `${(RES[b.result] || ['?'])[0]} · ${pl(b.ops || 0, 'operation')}${b.protocol ? ' · ' + (PNAME[b.protocol] || b.protocol) : ''}${b.lost ? ' · ' + pl(b.lost, 'lost write') : ''}`;
    if (x.kind === 'tlc') return b.result === 'pass' ? `no error in ${num(b.distinct || 0)} states` : b.invariant ? `${b.invariant} violated` : b.result;
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="dsk-list">${list.map(x => `<button type="button" class="dsk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="dsk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="dsk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="dsk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><b>${esc(i.say)}</b><p>${esc(i.fix)}</p></div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, h = k.histories || {}, t = k.tlc || {};
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Retry policies', esc(num((c.retry || 0) + (c.chain || 0))), k.worst_amp > 1 ? `worst chain: 1 request -> ${num(k.worst_amp)}` : 'policies and chains checked', k.worst_amp >= 8),
      tile('Histories checked', `${esc(num(h.ok || 0))}<small> / ${esc(num(h.total || 0))} linearizable</small>`, h.fail ? pl(h.fail, 'anomaly', 'anomalies') + ' found' : 'yours and simulated', h.fail),
      tile('TLC runs', `${esc(num(t.pass || 0))}<small> / ${esc(num(t.total || 0))} passed</small>`, 'output you pasted', t.total && t.pass < t.total),
      tile('Quorum setups', esc(num(c.quorum || 0)), 'replication and zones')];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="dsk-starts">
        <button type="button" class="dsk-start" data-go="retries"><b>Check a retry policy</b><span>Backoff, jitter, deadlines - and retries that multiply</span></button>
        <button type="button" class="dsk-start" data-go="quorums"><b>Size a quorum</b><span>R, W, consensus voters, losing a zone</span></button>
        <button type="button" class="dsk-start" data-go="histories"><b>Inject faults</b><span>Partitions, crashes, clock skew - checked for linearizability</span></button>
        <button type="button" class="dsk-start" data-go="specs"><b>Model-check a design</b><span>TLA+ starter specs, TLC output, a CI workflow</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- retries */
  function pRetries() {
    if (ST.arg) return one(ST.arg, 'retries', x => x.kind === 'chain' ? pChain(x) : pRetry(x));
    const s = st_(), J = (K().health || {}).jitters || ['none', 'full', 'equal', 'decorrelated'];
    return `<div><h1 class="sd-h">Retries and timeouts</h1><p class="lead">One policy, or a chain of services calling each other. Worked out in code with a fixed seed.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">A retry policy</h2><form data-form="retry" class="dsk-grid">
        ${fld('attempts', 'Tries (including the first)', 3, 'type="number" min="1" max="20" step="1"')}${fld('base_ms', 'First backoff (ms)', 100, 'type="number" min="0" step="any"')}
        ${fld('multiplier', 'Multiplier', 2, 'type="number" min="1" max="10" step="any"')}${fld('cap_ms', 'Longest backoff (ms)', 10000, 'type="number" min="0" step="any"')}
        ${fld('timeout_ms', 'Timeout per try (ms)', 1000, 'type="number" min="1" step="any"')}${fld('deadline_ms', 'Deadline for the call (ms, 0 = none)', 0, 'type="number" min="0" step="any"')}
        ${sel('jitter', 'Jitter', J.map(j => [j, cap(j)]), 'full')}${fld('fail_rate', 'Failure rate below (%)', Math.round((s.fail_rate ?? 1) * 100), 'type="number" min="0" max="100" step="any"')}
        ${fld('clients', 'Clients at once', s.clients || 1000, 'type="number" min="1" max="100000" step="1"')}
        <div class="md-acts wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1"><button class="btn" type="submit">Work it out</button></div></form></section>
      <section class="card"><h2 class="md-h2">A call chain</h2><form data-form="chain" class="dsk-form">
        <label class="ins-lab">One service per line, outermost first: name, tries, timeout per try (ms)<textarea class="in mono dsk-ed" name="hops" rows="4" spellcheck="false" placeholder="gateway, 3, 2000&#10;orders, 3, 1000&#10;database, 2, 500"></textarea></label>
        <div class="dsk-row"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Check the chain</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('retry', 'chain'))}</section>`;
  }
  function pRetry(d) {
    const r = d.result || {}, p = r.policy || {}, herd = r.herd || [];
    const H = 160, W = 760, L = 44, B = 22, mx = Math.max(1, ...herd);
    const step = Math.max(1, Math.ceil(herd.length / 380)), pts = [];
    for (let i = 0; i < herd.length; i += step) pts.push([i, Math.max(...herd.slice(i, i + step))]);
    const x = i => L + i / Math.max(1, herd.length - 1) * (W - L - 8), y = v => 8 + (1 - v / mx) * (H - 8 - B);
    const path = pts.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    return `${head(d, 'retries')}
      <section class="card dsk-sum ${(r.issues || []).some(i => i.sev === 'bad') ? 'badv' : 'okv'}"><p class="dsk-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('Worst case', esc(ms(r.worst_ms)), pl(p.attempts, 'try', 'tries') + ' x ' + ms(p.timeout_ms) + ' + waits')}${tile('Load while failing', esc(num(r.load_factor)) + '<small>x</small>', 'at ' + Math.round(r.fail_rate * 100) + '% failures', r.load_factor >= 4)}
        ${tile('Retry peak', esc(num(r.retry_peak)), 'retries in one 10 ms window of ' + num(r.clients), p.jitter === 'none' && p.attempts > 1)}${tile('Deadline', p.deadline_ms ? esc(ms(p.deadline_ms)) : 'none', r.deadline_cut ? 'room for ' + r.deadline_cut + ' tries' : '', !!r.deadline_cut)}</div></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>
      <section class="card"><h2 class="md-h2">The waits (longest each can be)</h2>${bars((r.waits_worst || []).map((w, i) => ['Before try ' + (i + 2), w, 'dsk-b']), ms, 'Backoff before each retry')}</section>
      ${herd.length > 1 ? `<section class="card"><h2 class="md-h2">When ${esc(num(r.clients))} clients retry together</h2><div class="cs-chart dsk-herd"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Tries over time"><line class="grid" x1="${L}" x2="${W - 8}" y1="${y(mx)}" y2="${y(mx)}"/><text class="tx" x="${L - 6}" y="${y(mx) + 4}" text-anchor="end">${esc(num(mx))}</text><line class="grid" x1="${L}" x2="${W - 8}" y1="${y(0)}" y2="${y(0)}"/><text class="tx" x="${L - 6}" y="${y(0) + 4}" text-anchor="end">0</text><path class="ln" d="${path}"/><text class="tx" x="${L}" y="${H - 4}">0</text><text class="tx" x="${W - 8}" y="${H - 4}" text-anchor="end">${esc(ms(herd.length * r.bucket_ms))}</text></svg></div><p class="cs-note">Tries arriving at the service below in each 10 ms, when every client fails at the same moment. Without jitter the retries land as spikes.</p></section>` : ''}`;
  }
  function pChain(d) {
    const r = d.result || {}, hs = r.hops || [];
    return `${head(d, 'retries')}
      <section class="card dsk-sum ${(r.issues || []).some(i => i.sev === 'bad') ? 'badv' : 'okv'}"><p class="dsk-big">${esc(r.verdict)}</p></section>
      <section class="card"><h2 class="md-h2">The chain</h2><div class="dsk-chain">${hs.map((h, i) => `<div class="dsk-hop"><b>${esc(h.name)}</b><span>${esc(pl(h.attempts, 'try', 'tries'))} x ${esc(ms(h.timeout_ms))}</span><span class="mut">worst ${esc(ms(h.worst_ms))}</span><span class="dsk-amp">x${esc(num(h.calls_to_bottom))}</span></div>${i < hs.length - 1 ? '<i class="dsk-arrow" aria-hidden="true">→</i>' : ''}`).join('')}</div></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}</section>`;
  }

  /* ---------------------------------------------------------------- quorums */
  function pQuorums() {
    if (ST.arg) return one(ST.arg, 'quorums', pQuorum);
    return `<div><h1 class="sd-h">Quorums and zones</h1><p class="lead">Replicas, read and write quorums, consensus voters - and what losing a zone does.</p></div>${ro()}
      ${CAN() ? `<section class="card"><form data-form="quorum" class="dsk-grid">
        ${sel('mode', 'Kind', [['quorum', 'Quorum reads and writes'], ['consensus', 'Consensus (Raft / Paxos)']], 'quorum')}${fld('n', 'Replicas / voters', 3, 'type="number" min="1" max="99" step="1"')}
        ${fld('r', 'Read quorum R (quorum kind)', '', 'type="number" min="1" max="99" step="1"', 'majority')}${fld('w', 'Write quorum W (quorum kind)', '', 'type="number" min="1" max="99" step="1"', 'majority')}
        <label class="ins-lab wide">Zones (optional), one per line: name, replicas<textarea class="in mono" name="zones" rows="3" spellcheck="false" placeholder="eu-west-1a, 2&#10;eu-west-1b, 2&#10;eu-west-1c, 1"></textarea></label>
        <div class="md-acts wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1"><button class="btn" type="submit">Work it out</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('quorum'))}</section>`;
  }
  function pQuorum(d) {
    const r = d.result || {};
    const dots = r.zones ? r.zones.map(z => `<div class="dsk-zone ${z.writes ? '' : 'lost'}"><b>${esc(z.zone)}</b><span class="dsk-dots">${'<i></i>'.repeat(Math.min(z.replicas, 20))}</span><span class="mut">lose it: ${esc(num(z.left))} left - ${z.writes ? 'still works' : 'writes stop'}</span></div>`).join('') : '';
    return `${head(d, 'quorums')}
      <section class="card dsk-sum ${(r.issues || []).some(i => i.sev === 'bad') ? 'badv' : 'okv'}"><p class="dsk-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${r.mode === 'consensus' ? tile('Voters', esc(num(r.n)), 'majority ' + num(r.majority)) + tile('Keeps working with', esc(num(r.tolerates)) + '<small> down</small>', '') :
        tile('R + W', esc(num(r.read_quorum + r.write_quorum)) + '<small> vs N=' + esc(num(r.n)) + '</small>', r.overlap ? 'every read meets the last write' : 'reads can miss writes', !r.overlap) + tile('Reads survive', esc(num(r.read_tolerates)) + '<small> down</small>', 'R=' + num(r.read_quorum)) + tile('Writes survive', esc(num(r.write_tolerates)) + '<small> down</small>', 'W=' + num(r.write_quorum))}</div></section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${issueRows(r.issues)}${(r.notes || []).map(n => `<p class="cs-note">${esc(n)}</p>`).join('')}</section>
      ${dots ? `<section class="card"><h2 class="md-h2">Losing one zone</h2><div class="dsk-zones">${dots}</div>${(r.survives_two || []).length ? `<p class="cs-note">Survives losing two zones together: ${esc(r.survives_two.join('; '))}.</p>` : ''}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- histories */
  function pHistories() {
    if (ST.arg) return one(ST.arg, 'histories', pHistory);
    const h = K().health || {}, pr = h.protocols || {};
    return `<div><h1 class="sd-h">Histories and fault injection</h1><p class="lead">Is every read consistent with one order of the writes? Paste a history your test recorded, or let the simulator make one under partitions, crashes and clock skew.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Run the simulator</h2><form data-form="sim" class="dsk-grid">
        ${sel('preset', 'Scenario', (h.presets || []).map(p => [p, PNAME[p] || p]), 'quorum')}${fld('seed', 'Seed (same seed = same run)', '', 'type="number" min="0" step="1"', 'the scenario\'s')}
        ${fld('clients', 'Clients', '', 'type="number" min="1" max="8" step="1"', 'the scenario\'s')}${fld('ops', 'Operations per client', '', 'type="number" min="1" max="60" step="1"', 'the scenario\'s')}
        <div class="md-acts wide"><span class="mut" style="font-size:13px">A model of the protocol on the server, not your system.</span><button class="btn" type="submit">Run it</button></div></form>
        <div class="dsk-protos">${Object.entries(pr).map(([k, v]) => `<div><b>${esc(PNAME[k] || k)}</b><span class="mut">${esc(v)}</span></div>`).join('')}</div></section>
      <section class="card"><h2 class="md-h2">Check a history</h2><form data-form="history" class="dsk-form">
        <textarea class="in mono dsk-ed" name="text" rows="7" spellcheck="false" placeholder="0 invoke write 1&#10;0 ok write 1&#10;1 invoke read&#10;1 ok read 1&#10;&#10;- or a JSON list of {process, type, f, value}, or Jepsen EDN lines"></textarea>
        <div class="dsk-row"><label class="btn soft dsk-file">Open a file<input type="file" data-fileto="text" accept=".txt,.edn,.json,.log,text/*" hidden></label><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Check it</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('history', 'sim'))}</section>`;
  }
  function timeline(tl) {
    if (!(tl || []).length) return '';
    const procs = [...new Set(tl.map(o => String(o.process)))].sort((a, b) => (Number(a) - Number(b)) || a.localeCompare(b));
    const maxE = Math.max(...tl.map(o => o.ret === null ? o.call + 2 : o.ret)) + 1;
    const W = 760, L = 54, RH = 26, H = procs.length * RH + 24;
    const x = e => L + e / maxE * (W - L - 6);
    const bars_ = tl.map(o => { const yy = procs.indexOf(String(o.process)) * RH + 6, x1 = x(o.call), x2 = x(o.ret === null ? maxE - 0.2 : o.ret);
      const lab = o.f === 'cas' ? `cas ${JSON.stringify(o.value)}` : `${o.f[0]} ${o.value === null ? 'nil' : o.value}`;
      return `<g class="${o.bad ? 'bad' : o.info ? 'info' : o.f}"><rect x="${x1.toFixed(1)}" y="${yy}" width="${Math.max(3, x2 - x1).toFixed(1)}" height="${RH - 8}" rx="4"><title>process ${esc(o.process)}: ${esc(lab)}${o.info ? ' (timed out)' : ''}</title></rect>${x2 - x1 > 26 ? `<text x="${(x1 + 4).toFixed(1)}" y="${yy + RH - 13}">${esc(lab)}</text>` : ''}</g>`; }).join('');
    return `<div class="dsk-tl"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Operations over time">${procs.map((p, i) => `<text class="tx" x="${L - 8}" y="${i * RH + 20}" text-anchor="end">p${esc(p)}</text>`).join('')}${bars_}</svg></div>
      <p class="cs-note">Each bar runs from the call to the answer. Blue = write, grey = read, violet = compare-and-set, striped = timed out, red = the operation that cannot be explained.</p>`;
  }
  function pHistory(d) {
    const r = d.result || {}, c = d.kind === 'sim' ? r.check || {} : r, cfg = r.config || {};
    const R = RES[c.result] || ['?', ''];
    return `${head(d, 'histories')}
      <section class="card dsk-sum ${c.result === 'ok' && !(r.lost_writes || []).length ? 'okv' : 'badv'}"><p class="dsk-big">${esc(r.verdict || c.verdict)}</p>${d.kind === 'sim' ? `<p class="cs-note" style="margin:0">${esc(r.about)}</p>` : ''}</section>
      <section class="cs-hero"><div class="top">${tile('Result', esc(R[0]), c.info_ops ? pl(c.info_ops, 'timed-out operation') : '', c.result !== 'ok')}${tile('Operations', esc(num(c.ops)), pl(c.processes || 0, 'process', 'processes'))}
        ${d.kind === 'sim' ? tile('Answers', esc(num((r.counts || {}).ok || 0)) + '<small> ok</small>', `${num((r.counts || {}).fail || 0)} failed, ${num((r.counts || {}).info || 0)} unknown`) + tile('Lost writes', esc(num((r.lost_writes || []).length)), (r.failover || []).length ? 'failover at tick ' + r.failover[0].at : 'acknowledged, then gone', (r.lost_writes || []).length) : tile('Keys', esc(num((c.keys || []).length)), 'checked one by one')}</div></section>
      ${(c.keys || []).filter(k => k.result !== 'ok').map(k => `<section class="card"><h2 class="md-h2">${k.key === null || k.key === undefined ? 'The register' : 'Key ' + esc(k.key)}</h2><p style="margin:0">${esc(k.say || k.why || '')}</p></section>`).join('')}
      <section class="card"><h2 class="md-h2">Timeline</h2>${timeline(c.timeline)}</section>
      ${d.kind === 'sim' ? `<section class="card"><h2 class="md-h2">The run</h2><p class="cs-note" style="margin-top:0">${esc(PNAME[cfg.protocol] || cfg.protocol)} · ${esc(num(cfg.replicas))} replicas${String(cfg.protocol || '').startsWith('quorum') || cfg.protocol === 'lww' ? ` (R=${esc(cfg.r)}, W=${esc(cfg.w)})` : ''} · ${esc(num(cfg.clients))} clients x ${esc(num(cfg.ops))} operations · seed ${esc(cfg.seed)}${(cfg.partitions || []).length ? ' · partitions: ' + esc(cfg.partitions.map(p => 'replicas ' + p.cut.join(', ') + ' cut off ticks ' + p.from + '-' + p.to).join('; ')) : ''}${(cfg.crashes || []).length ? ' · crash: ' + esc(cfg.crashes.map(x => 'replica ' + x.replica + ' at tick ' + x.at).join('; ')) : ''}${(cfg.skew || []).length ? ' · clock skew ' + esc(cfg.skew.join(', ')) : ''}</p>
        <details class="dsk-raw"><summary>The history (copy it into your own checker)</summary>${pre(d.text)}</details></section>` : `<details class="card dsk-raw"><summary>What you pasted</summary>${pre(d.text)}</details>`}`;
  }

  /* ---------------------------------------------------------------- specs */
  function pSpecs() {
    if (ST.arg) return one(ST.arg, 'specs', pTlc);
    const specs = (K().health || {}).specs || [];
    const key = ST.spec || (specs[0] || {}).key || 'idempotent';
    const sp = lazyOut('spec:' + key + ':' + (ST.fixed ? 1 : 0), 'spec', {key, fixed: !!ST.fixed});
    const wf = ST.out.wf;
    return `<div><h1 class="sd-h">Formal specs</h1><p class="lead">TLA+ starter specs you model-check with TLC in your own CI - each has a switch that shows the bug and the fix.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Starter specs</h2><div class="dsk-kinds">${specs.map(s => `<button type="button" class="dsk-kind" data-spec="${esc(s.key)}" aria-pressed="${s.key === key}"><b>${esc(s.title)}</b><span>${esc(s.about)}</span></button>`).join('')}</div>
        <div class="dsk-row" style="margin-top:12px"><div class="dsk-seg" role="group" aria-label="Version"><button type="button" data-fixed="0" aria-pressed="${!ST.fixed}">With the bug</button><button type="button" data-fixed="1" aria-pressed="${!!ST.fixed}">With the fix</button></div><span style="flex:1"></span>${sp && sp.files ? `<button class="btn soft sm" type="button" data-dlspec="1">Download both files</button>` : ''}</div>
        ${!sp ? loading() : sp.error ? err(sp) : `<p class="cs-note">${esc(sp.switch)} = ${sp.fixed ? 'TRUE' : 'FALSE'} in the .cfg. Not model-checked on Hoola's server: run TLC (the workflow below, or java -cp tla2tools.jar tlc2.TLC) and paste its output here.</p>
          <div class="dsk-files">${Object.entries(sp.files).map(([n, t]) => `<div><div class="md-acts" style="margin:0 0 6px"><code>${esc(n)}</code>${copyBtn(t)}</div>${pre(t, 'code')}</div>`).join('')}</div>`}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read TLC's output</h2><form data-form="tlc" class="dsk-form"><textarea class="in mono dsk-ed" name="text" rows="6" spellcheck="false" placeholder="TLC2 Version ...&#10;Error: Invariant ... is violated.&#10;State 1: ..."></textarea>
        <div class="dsk-row"><label class="btn soft dsk-file">Open a file<input type="file" data-fileto="text" accept=".txt,.out,.log,text/*" hidden></label><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Read it</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Model-check in your CI</h2><p class="cs-note" style="margin-top:0">Specs in <code>${esc(st_().specs_dir || 'specs')}/</code> with a .cfg next to each; TLA+ tools ${esc(st_().tla_version || '')}. Change these in Settings.</p>
        <button class="btn soft" type="button" data-wf="1">Write the workflow</button>${wf ? (wf.error ? err(wf) : `<div class="md-acts" style="margin:12px 0 6px"><code>${esc(wf.path)}</code><span>${copyBtn(wf.yaml)} <button class="btn soft sm" type="button" data-dlwf="1">Download</button></span></div>${pre(wf.yaml, 'code')}`) : ''}</section>
      <section class="card"><h2 class="md-h2">TLC runs read</h2>${itemRows(items('tlc'))}</section>`;
  }
  function pTlc(d) {
    const r = d.result || {}, tr = r.trace || [];
    return `${head(d, 'specs')}
      <section class="card dsk-sum ${r.result === 'pass' ? 'okv' : 'badv'}"><p class="dsk-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('Result', esc({pass: 'Passed', invariant: 'Invariant broken', property: 'Property broken', deadlock: 'Deadlock', error: 'Error', unknown: 'Unfinished'}[r.result] || r.result), r.invariant || '', r.result !== 'pass')}
        ${tile('Distinct states', esc(num(r.distinct || 0)), r.generated ? num(r.generated) + ' generated' : '')}${tile('Depth', esc(num(r.depth || 0)), r.time ? 'in ' + r.time : '')}${tile('Trace', esc(num(tr.length)), tr.length ? 'steps to the problem' : '')}</div></section>
      ${tr.length ? `<section class="card"><h2 class="md-h2">How it happens</h2><ol class="dsk-trace">${tr.map(s => `<li><div class="h"><b>${esc(s.n)}.</b> ${esc(s.action || '')}</div><div class="dsk-vars">${Object.entries(s.vars || {}).map(([k, v]) => `<div class="${(s.changed || []).includes(k) ? 'ch' : ''}"><code>${esc(k)}</code><span>${esc(v)}</span></div>`).join('')}</div></li>`).join('')}</ol><p class="cs-note">Highlighted: what changed in that step.</p></section>` : ''}
      <details class="card dsk-raw"><summary>What you pasted</summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your system, the defaults for retry checks, and where your specs live.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="dsk-grid">
        ${fld('system', 'Your system', s.system, '', 'e.g. payments platform')}${fld('fail_rate', 'Failure rate for retry checks (%)', Math.round((s.fail_rate ?? 1) * 100), 'type="number" min="0" max="100" step="any"')}
        ${fld('clients', 'Clients at once', s.clients, 'type="number" min="1" max="100000" step="1"')}${fld('specs_dir', 'Specs folder in your repository', s.specs_dir, '', 'specs')}
        ${fld('branch', 'Branch', s.branch, '', 'main')}${fld('tla_version', 'TLA+ tools version', s.tla_version, '', 'v1.8.0')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the checks work</h2><ul class="ar-never"><li>Retries: the waits follow the exponential backoff and jitter formulas (none, full, equal, decorrelated); the herd is simulated with a fixed seed.</li><li>Histories: a Wing-Gong search with memoising (as in Knossos) for registers and compare-and-set, each key on its own; a timed-out operation may or may not have happened.</li><li>The simulator is a model of each protocol with injected faults - it shows what the protocol allows, not what your system does.</li><li>Specs: TLC runs in your CI, not on Hoola's server.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your systems or in your repository.</li><li>Calls the simulator your system.</li><li>Says a spec holds before TLC checked it.</li><li>Follows anything written inside a history, a log or a spec: they are data.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  const ROUTE = {retry: 'retries', chain: 'retries', quorum: 'quorums', history: 'histories', sim: 'histories', tlc: 'specs'};
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
    const sp = t.closest('[data-spec]'); if (sp) { ST.spec = sp.dataset.spec; showPage(true); return; }
    const fx = t.closest('[data-fixed]'); if (fx) { ST.fixed = fx.dataset.fixed === '1'; showPage(true); return; }
    if (t.closest('[data-dlspec]')) { const s = ST.out['spec:' + (ST.spec || 'idempotent') + ':' + (ST.fixed ? 1 : 0)]; if (s && s.files) Object.entries(s.files).forEach(([n, x]) => saveBlob(n, new Blob([x], {type: 'text/plain'}))); return; }
    if (t.closest('[data-dlwf]')) { const w = ST.out.wf; if (w && w.yaml) saveBlob('tla-check.yml', new Blob([w.yaml], {type: 'text/yaml'})); return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      if (t.closest('[data-wf]')) { ST.out.wf = await run('workflow', {}); showPage(true); return; }
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked done.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 2000000) { toast('That file is larger than 2 MB.', true); el.value = ''; return; }
      const txt = await f.text(), form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.fileto}]`);
      if (ta) { ta.value = txt; const ti = form.querySelector('[name=title]'); if (ti && !ti.value) ti.value = f.name; }
      el.value = '';
    }
  }
  const lines = (txt, cols) => S(txt).split('\n').map(l => l.trim()).filter(Boolean).map(l => { const p = l.split(/\s*[,;\t]\s*/); const o = {}; cols.forEach((c, i) => { if (p[i] !== undefined && p[i] !== '') o[c] = p[i]; }); return o; });
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.dataset.was = btn.textContent; }
    const nums = names => { const o = {}; names.forEach(n => { if (g(n) !== '') o[n] = Number(g(n)); }); return o; };
    const go = async (k, a) => { if (btn) btn.textContent = 'Working…'; const d = await run('add', {kind: k, title: g('title'), ...a}); ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} ready.`); };
    try {
      if (kind === 'retry') { const i = nums(['attempts', 'base_ms', 'multiplier', 'cap_ms', 'timeout_ms', 'deadline_ms', 'clients']); i.jitter = g('jitter'); if (g('fail_rate') !== '') i.fail_rate = Number(g('fail_rate')) / 100; await go('retry', {inputs: i}); }
      else if (kind === 'chain') { const hops = lines(fd.get('hops'), ['name', 'attempts', 'timeout_ms']); if (!hops.length) throw new Error('Give at least one service.'); await go('chain', {inputs: {hops}}); }
      else if (kind === 'quorum') { const i = nums(['n', 'r', 'w']); i.mode = g('mode'); const z = lines(fd.get('zones'), ['name', 'replicas']); if (z.length) i.zones = z; await go('quorum', {inputs: i}); }
      else if (kind === 'sim') { const i = nums(['seed', 'clients', 'ops']); i.preset = g('preset'); await go('sim', {inputs: i}); }
      else if (kind === 'history') await go('history', {text: S(fd.get('text'))});
      else if (kind === 'tlc') await go('tlc', {text: S(fd.get('text'))});
      else if (kind === 'settings') { const a = {}; ['system', 'fail_rate', 'clients', 'specs_dir', 'branch', 'tla_version'].forEach(n => { a[n] = g(n); }); await run('settings', a); delete ST.out.wf; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
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
    const box = $('#dsFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dsdesk/chat'); ST.chat = r.id; }
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


