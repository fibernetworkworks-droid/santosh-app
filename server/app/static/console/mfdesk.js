/* MAINFRAME DESK - the Mainframe Modernization Architect's own section, like the finance desks (owner: "Mainframe Modernization
   Architect same as finance desks"). A thin top bar, then the Mainframe chat (its own conversation, kind 'mainframe') beside the
   desk's pages: Today, Programs, Data layouts, Batch (JCL), Map and plan, Proof, CI check, Settings. The pages call
   /api/mfdesk/do/<part>; nothing runs on her mainframe or servers. */
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

  const TABS = [['today', 'Today'], ['programs', 'Programs'], ['data', 'Data layouts'], ['batch', 'Batch'], ['map', 'Map and plan'], ['proof', 'Proof'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start a mainframe migration?', 'Rehost, refactor or rewrite?', 'How do I prove the new system gives the same answers?'],
    programs: ['Is this dead code safe to drop?', 'How do I translate GO TO logic?', 'What does NEXT SENTENCE really do?'],
    data: ['How do I read a COMP-3 field in Java?', 'Why do my numbers come out wrong after FTP?', 'How do I map REDEFINES?'],
    batch: ['What replaces JCL in the new world?', 'How do I handle GDGs?', 'Why does this job fail on rerun?'],
    map: ['Which wave should go first?', 'How do I break a call cycle?', 'What about the CICS transactions?'],
    proof: ['Why is it off by a cent?', 'How do I compare EBCDIC files?', 'Which test inputs should I use?'],
    ci: ['How do I get the old output off the mainframe?', 'Should the golden file be in git?', 'Can CI run GnuCOBOL?'],
    settings: ['Which code page is my data in?', 'Java or C# for the target?', 'What should the tolerance be?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'program', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.mfdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.mfdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'mainframe', name: 'Mainframe'} : null;
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
  const run = (part, a) => api('POST', '/api/mfdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/mfdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Mainframe Modernization Architect is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="mfHire">Hire the Mainframe Modernization Architect</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#mfHire').onclick = async () => { try { await api('POST', '/api/employees/mainframe_arch/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Mainframe</div><div class="sd-site" id="mfSite"></div></div>
          <span id="mfState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Mainframe chat">
          <div class="sd-chathead"><div class="t"><b>Mainframe chat</b><span>Paste COBOL, a copybook, JCL or two outputs to compare - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mfFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mfPick" multiple hidden accept=".txt,.cbl,.cob,.cpy,.jcl,.csv,.dat,.json,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Mainframe desk" id="sdTabs"></nav>
          <div id="mfPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste COBOL or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mfPick').click()});
    $('#mfPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.mfdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.mfdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/mfdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#mfPage').addEventListener('click', onPageClick);
    $('#mfPage').addEventListener('submit', onSubmit);
    $('#mfPage').addEventListener('change', onChange);
    $('#mfPage').addEventListener('input', onInput);
    $('#mfPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#mfState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#mfSite').textContent = [s.encoding, s.target ? 'to ' + cap(s.target === 'csharp' ? 'C#' : s.target) : '', pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/mfdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#mfPage'); if (!box) return;
    const fn = {today: pToday, programs: pPrograms, data: pData, batch: pBatch, map: pMap, proof: pProof, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="mfk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const pct = (v, d = 0) => { if (v === null || v === undefined) return '—'; let t = (Number(v) * 100).toFixed(d); if (t.includes('.')) t = t.replace(/\.?0+$/, ''); return t + '%'; };
  const KN = {program: 'Program', copybook: 'Data layout', jcl: 'JCL', inventory: 'Map', proof: 'Proof'};
  const ROUTE = {program: 'programs', copybook: 'data', jcl: 'batch', inventory: 'map', proof: 'proof'};
  const ENC = [['cp037', 'EBCDIC cp037 (US / Canada)'], ['cp1140', 'EBCDIC cp1140 (with euro)'], ['cp500', 'EBCDIC cp500 (international)'], ['cp273', 'EBCDIC cp273 (Germany / Austria)'], ['cp1047', 'EBCDIC cp1047 (Open Systems)'], ['ascii', 'ASCII (already converted)']];
  const KC = {text: 'Text', zoned: 'Zoned decimal', packed: 'Packed (COMP-3)', binary: 'Binary (COMP)', edited: 'Edited', float: 'Floating', pointer: 'Pointer'};
  const AP = {'Retire?': '', 'Rewrite with tests': 'bad', 'Restructure, then translate': 'warn', 'Replatform the screens': 'warn', 'Translate (batch + DB2)': 'ok', 'Translate first (shared)': 'ok', 'Translate': 'ok'};
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'program': return b.programs > 1 ? `${b.programs} programs · ${num(b.loc)} lines` : `${num(b.loc)} lines · ${b.online ? 'online (CICS)' : 'batch'}${b.tables ? ' · ' + pl(b.tables, 'table') : ''}${b.dead ? ' · ' + num(b.dead) + ' never reached' : ''}`;
      case 'copybook': return `${num(b.length)} bytes · ${pl(b.fields || 0, 'field')}${b.packed ? ' · ' + num(b.packed) + ' packed' : ''}${b.decoded ? ' · a record decoded' : ''}`;
      case 'jcl': return `${pl(b.jobs || 0, 'job')} · ${pl(b.steps || 0, 'step')} · ${pl(b.programs || 0, 'program')}`;
      case 'inventory': return `${pl(b.programs || 0, 'program')} · ${num(b.loc)} lines · ${pl(b.waves || 0, 'wave')}${b.missing ? ' · ' + num(b.missing) + ' missing' : ''}`;
      case 'proof': return b.proved ? `proved the same · ${num(b.records)} records` : b.reordered ? 'same records, another order' : `${num(b.differ)} of ${num(b.records)} records differ${b.only ? ' · ' + num(b.only) + ' missing or added' : ''}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="mfk-list">${list.map(x => `<button type="button" class="mfk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="mfk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="mfk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="mfk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area ? `<span class="mut">${esc(i.area)}</span>` : ''}${i.fix ? `<code class="mfk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono mfk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft mfk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="mfk-row wide">${fileBtn('text', acc || '.cbl,.cob,.cpy,.jcl,.txt,.dat,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card mfk-sum ${ok ? 'okv' : 'badv'}"><p class="mfk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="mfk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const seg = (key, opts, cur) => `<div class="mfk-seg" role="tablist">${opts.map(([k2, t]) => `<button type="button" data-${key}="${k2}" aria-pressed="${k2 === cur}">${esc(t)}</button>`).join('')}</div>`;
  const copyBlock = (title, txt, file) => `<section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">${esc(title)}</h2><span>${copyBtn(txt)}${file ? ` <button class="btn soft sm" type="button" data-dl="${esc(file)}" data-dltext="${esc(txt)}">Download</button>` : ''}</span></div>${pre(txt, 'code')}</section>`;
  const copybooks = () => items('copybook');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, mp = k.map, pr = k.proofs || {}, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('The map', mp ? esc(num(mp.programs)) + ' <small>programs</small>' : '—', mp ? `${num(mp.loc)} lines · ${pl(mp.waves || 0, 'wave')} · ${mp.number}` : 'paste the inventory to map it', mp && mp.missing > 0),
      tile('Programs read', esc(num(k.programs || 0)), k.dead ? `${num(k.dead)} paragraph(s) never reached` : 'COBOL read for risks'),
      tile('Data layouts', esc(num(c.copybook || 0)), 'copybooks laid out'),
      tile('Proofs', pr.n ? esc(`${pr.proved} / ${pr.n}`) : '—', pr.n ? `proved the same · latest ${pr.latest} ${pr.latest_ok ? 'proved' : 'differs'}` : 'compare old and new output', pr.n && !pr.latest_ok)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} Files read as ${esc((ENC.find(e => e[0] === s.encoding) || ['', s.encoding])[1])}; target ${esc(cap(s.target || 'java'))}.</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="mfk-path">
        <li><button type="button" data-go="map"><b>Map the inventory</b><span>Programs, copybooks and JCL together: what calls what, what is missing, the waves</span></button></li>
        <li><button type="button" data-go="programs"><b>Read each program</b><span>Dead paragraphs, calls, DB2, CICS, and what makes it risky to translate</span></button></li>
        <li><button type="button" data-go="data"><b>Lay out the data</b><span>Copybooks into offsets and types; real records decoded from EBCDIC and packed bytes</span></button></li>
        <li><button type="button" data-go="proof"><b>Prove the translation</b><span>The new program's output against the old one's, field by field - then keep it proved in CI</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- programs */
  const SAMPLE_COBOL = "       IDENTIFICATION DIVISION.\n       PROGRAM-ID. PAYCALC.\n       DATA DIVISION.\n       WORKING-STORAGE SECTION.\n       01  WS-PAY   PIC S9(7)V99 COMP-3.\n       PROCEDURE DIVISION.\n       0000-MAIN.\n           PERFORM 1000-CALC\n           STOP RUN.\n       1000-CALC.\n           CALL 'TAXCALC' USING WS-PAY.";
  function pPrograms() {
    if (ST.arg) return one(ST.arg, 'programs', pProg);
    return `<div><h1 class="sd-h">Programs</h1><p class="lead">A COBOL program read for what it does and what it touches - and what makes it risky to translate.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a program</h2><form data-form="program" class="mfk-grid">
        ${area('text', 'COBOL source - one program or several, fixed format (columns 8-72) or free format', SAMPLE_COBOL, 12)}${subRow('Read it', '.cbl,.cob,.cobol,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('program'))}</section>`;
  }
  function pProg(d) {
    const r = d.result || {}, ps = r.programs || [];
    return `${head(d, 'programs')}${verdict(r, isOk(r))}
      ${ps.map((p, pi) => { const s2 = p.stats || {}, k2 = 'p:' + d.id + ':' + pi;
        const maxl = Math.max(1, ...p.paragraphs.map(x => x.lines));
        return `<section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">${esc(p.name)}</h2><span class="mut" style="font-size:13px">${esc(pl(p.loc, "line"))} · ${p.online ? 'online (CICS)' : 'batch'}</span></div>
        <div class="mfk-stats">${[['Paragraphs', s2.paragraphs], ['Decisions', s2.decisions], ['GO TO', s2.goto], ['ALTER', s2.alter], ['Never reached', p.dead.length], ['Packed fields', s2.comp3]].map(([l, v]) => `<div class="${(l === 'ALTER' && v) || (l === 'GO TO' && v > 3) ? 'bad' : ''}"><span>${esc(l)}</span><b>${esc(num(v))}</b></div>`).join('')}</div>
        <details class="mfk-paras" data-key="${esc(k2)}"${ST.open.has(k2) || ps.length === 1 ? ' open' : ''}><summary>The paragraphs, in order</summary><div class="mfk-plist">${p.paragraphs.map(x => `<div class="${x.dead ? 'dead' : ''}"><b>${esc(x.name)}</b><i style="width:${(x.lines / maxl * 100).toFixed(0)}%"></i><span class="mut">${esc(pl(x.lines, "line"))}${x.perform.length ? ' · performs ' + esc(x.perform.map(t => t.replace('>', ' thru ')).join(', ')) : ''}${x.goto.length ? ' · goes to ' + esc(x.goto.join(', ')) : ''}${x.dead ? ' · never reached' : ''}</span></div>`).join('')}</div></details>
        <div class="mfk-touch">
          ${[['Calls', (p.calls || []).map(c => c.to + (c.how !== 'static' ? ` (${c.how}${c.values && c.values.length ? ': ' + c.values.join(', ') : ''})` : ''))], ['Copybooks', p.copies], ['DB2 tables', p.tables], ['Files', (p.files || []).map(f => `${f.name} → ${f.dd}${f.status ? '' : ' (no FILE STATUS)'}`)], ['CICS', [...new Set((p.cics || []).map(c => c.cmd))]]].map(([l, xs]) => `<div><span class="mut">${esc(l)}</span>${(xs || []).length ? xs.slice(0, 30).map(x => `<code>${esc(x)}</code>`).join('') : '<em class="mut">none</em>'}</div>`).join('')}</div>
        ${(p.sql || []).length ? `<details class="mfk-sql"><summary>${esc(pl(p.sql.length, 'SQL statement'))}</summary>${p.sql.slice(0, 40).map(q => `<code class="mfk-code">${esc(q.text)}</code>`).join('')}</details>` : ''}</section>`; }).join('')}
      <section class="card"><h2 class="md-h2">Risks to translate</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mfk-raw"><summary>The source you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- data layouts */
  const SAMPLE_CPY = "       01  CUSTOMER-REC.\n           05  CUST-ID        PIC X(8).\n           05  CUST-NAME      PIC X(20).\n           05  CUST-BAL       PIC S9(7)V99 COMP-3.\n           05  CUST-STATUS    PIC X.\n               88  ACTIVE     VALUE 'A'.";
  function pData() {
    if (ST.arg) return one(ST.arg, 'data', pLay);
    const s = st_();
    return `<div><h1 class="sd-h">Data layouts</h1><p class="lead">A copybook laid out byte by byte, the type each field becomes in the new code, and a real record decoded from its bytes - so a translation can be checked against the data it reads.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Lay out a copybook</h2><form data-form="copybook" class="mfk-grid">
        ${area('text', 'The copybook (01 / 05 levels with PIC clauses), or a program\'s DATA DIVISION', SAMPLE_CPY, 10)}
        ${area('sample', 'One record to decode (optional): its bytes as hex, or its text if it is already ASCII', 'C3F0F0F0F0F0F0F1 C1D5D5C140E2D4C9E3C8 ... 000012345C C1', 3)}
        ${sel('encoding', 'Character set of the record', ENC, s.encoding || 'cp037')}${subRow('Lay it out', '.cpy,.cbl,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Laid out</h2>${itemRows(items('copybook'))}</section>`;
  }
  function byteBar(rows, len) {
    const leaves = rows.filter(r => !r.group && r.length && !r.redefines && !r.in_occurs);
    if (!len || !leaves.length) return '';
    return `<div class="mfk-bytes" role="img" aria-label="Where the bytes go">${leaves.map(r => `<i class="${esc(r.kind)}" style="flex:${r.length} 1 0" title="${esc(r.name)} · offset ${r.offset} · ${r.length} bytes · ${esc(KC[r.kind] || r.kind)}"></i>`).join('')}</div>
      <div class="mfk-key">${Object.entries(KC).filter(([k2]) => leaves.some(r => r.kind === k2)).map(([k2, t]) => `<span><i class="${k2}"></i>${esc(t)}</span>`).join('')}</div>`;
  }
  function pLay(d) {
    const r = d.result || {}, rows = r.rows || [], s = st_(), tg = s.target || 'java', dec = r.decoded;
    const dmap = {}; (dec && dec.fields || []).forEach(f => { dmap[f.name + '@' + f.offset] = f; });
    const code = {java: ['Java record', r.java, 'Record.java'], python: ['Python decoder', r.python, 'decode.py'], csharp: ['SQL table', r.ddl, 'table.sql']}[tg] || ['Java record', r.java, 'Record.java'];
    return `${head(d, 'data')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Record length', esc(num(r.length)) + ' <small>bytes</small>', (r.records || []).length > 1 ? pl(r.records.length, 'record') : '')}${tile('Fields', esc(num(r.fields)), 'elementary items')}${tile('Packed', esc(num((r.kinds || {}).packed || 0)), 'COMP-3 fields')}${tile('Binary', esc(num((r.kinds || {}).binary || 0)), 'COMP fields')}</div></section>
      <section class="card"><h2 class="md-h2">Where the bytes go</h2>${byteBar(rows, r.length)}</section>
      <section class="card"><h2 class="md-h2">The fields${dec ? ', with the record decoded' : ''}</h2><div class="iv-tw"><table class="tb mfk-fields in-cards"><thead><tr><th>Field</th><th>Picture</th><th class="r">Offset</th><th class="r">Length</th><th>Kind</th><th>${esc(cap(tg === 'csharp' ? 'C#' : tg))}</th><th>SQL</th>${dec ? '<th>Value</th>' : ''}</tr></thead><tbody>
        ${rows.map(f => { const v = dmap[f.name + '@' + f.offset]; return `<tr class="${f.group ? 'grp' : ''}"><td style="padding-left:${8 + (f.depth || 0) * 16}px"><b>${esc(f.name)}</b>${f.occurs > 1 ? ` <span class="mut">× ${esc(f.occurs)}</span>` : ''}${f.redefines ? ` <span class="mut">redefines ${esc(f.redefines)}</span>` : ''}${(f.conds || []).length ? `<div class="mut" style="font-size:12px">${esc(f.conds.map(c2 => c2.name + ' = ' + c2.values).join(' · '))}</div>` : ''}</td><td><code>${esc(f.pic || '')}</code>${f.usage && f.usage !== 'DISPLAY' && !f.group ? ` <span class="mut">${esc(f.usage)}</span>` : ''}</td><td class="r">${esc(f.offset)}</td><td class="r">${esc(f.length)}</td><td>${f.group ? '<span class="mut">group</span>' : esc(KC[f.kind] || f.kind)}</td><td style="white-space:nowrap"><code>${esc((f.type || {})[tg] || '')}</code></td><td style="white-space:nowrap"><code>${esc(((f.type || {}).sql || '').split('  --')[0])}</code></td>${dec ? `<td>${v ? (v.bad ? `<span class="cs-neg">${esc(v.bad)}</span>` : `<code>${esc(v.value === null ? '' : String(v.value))}</code>`) + `<div class="mut mfk-hex">${esc(v.hex.slice(0, 40))}</div>` : ''}</td>` : ''}</tr>`; }).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      ${copyBlock('SQL table', r.ddl, 'table.sql')}${copyBlock(code[0], code[1], code[2])}${tg !== 'python' ? copyBlock('Python decoder', r.python, 'decode.py') : ''}
      <details class="card mfk-raw"><summary>The copybook you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- batch (JCL) */
  const SAMPLE_JCL = "//PAYJOB   JOB (ACCT),'PAYROLL',CLASS=A\n//STEP010  EXEC PGM=SORT\n//SORTIN   DD DSN=PAY.EMP.MASTER,DISP=SHR\n//SORTOUT  DD DSN=PAY.WORK.SORTED,DISP=(NEW,CATLG,DELETE)\n//SYSIN    DD *\n  SORT FIELDS=(1,6,CH,A)\n/*\n//STEP020  EXEC PGM=PAYCALC\n//EMPIN    DD DSN=PAY.WORK.SORTED,DISP=SHR";
  function pBatch() {
    if (ST.arg) return one(ST.arg, 'batch', pJcl);
    return `<div><h1 class="sd-h">Batch</h1><p class="lead">JCL read into what each job runs, the data it reads and writes, and what would break a rerun.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a job</h2><form data-form="jcl" class="mfk-grid">${area('text', 'JCL: the JOB card, its EXEC steps and DD statements (in-stream SYSIN included)', SAMPLE_JCL, 11)}${subRow('Read it', '.jcl,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('jcl'))}</section>`;
  }
  function pJcl(d) {
    const r = d.result || {}, st = r.steps || [];
    return `${head(d, 'batch')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">The steps</h2><ol class="mfk-steps">${st.map(s => `<li><div class="h"><b>${esc(s.job)} · ${esc(s.step)}</b><span class="${s.util ? 'mut' : 'mfk-pg'}">${esc(s.program || '—')}</span>${s.via && s.via !== 'PGM' ? `<span class="mut">via ${esc(s.via)}</span>` : ''}${s.cond ? `<span class="mut">COND=${esc(s.cond)}</span>` : ''}</div>
        ${s.util ? `<p class="mut">${esc(s.util)}</p>` : ''}
        <div class="mfk-io">${s.reads.length ? `<div><span class="mut">reads</span>${s.reads.map(x => `<code>${esc(x)}</code>`).join('')}</div>` : ''}${s.writes.length ? `<div><span class="mut">writes</span>${s.writes.map(x => `<code class="w">${esc(x)}</code>`).join('')}</div>` : ''}${(s.deletes || []).length ? `<div><span class="mut">deletes</span>${s.deletes.map(x => `<code>${esc(x)}</code>`).join('')}</div>` : ''}${s.sort.length ? `<div><span class="mut">sort</span>${s.sort.map(x => `<code>${esc(x)}</code>`).join('')}</div>` : ''}</div></li>`).join('')}</ol></section>
      ${(r.flows || []).length ? `<section class="card"><h2 class="md-h2">Data passed between steps</h2><div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Dataset</th><th>Written by</th><th>Read by</th></tr></thead><tbody>${r.flows.map(f => `<tr><td><code>${esc(f.dsn)}</code></td><td>${esc(f.from)}</td><td>${esc(f.to)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mfk-raw"><summary>The JCL you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- map (inventory) */
  function pMap() {
    if (ST.arg) return one(ST.arg, 'map', pInv);
    return `<div><h1 class="sd-h">Map and plan</h1><p class="lead">Every program, copybook and job together: what calls what, what is missing, which programs share data, and the waves to move them in.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Map an inventory</h2><form data-form="inventory" class="mfk-grid">
        ${area('text', 'Paste each source under a heading with its name: ## PAYCALC.cbl, ## CUSTREC (a copybook), ## PAYJOB.jcl ...', '## PAYCALC.cbl\n       IDENTIFICATION DIVISION.\n       PROGRAM-ID. PAYCALC.\n       ...\n## CUSTREC\n       01  CUSTOMER-REC.\n       ...\n## PAYJOB.jcl\n//PAYJOB   JOB ...', 12)}
        <div class="mfk-row wide"><label class="btn soft mfk-file">Open files<input type="file" data-filesto="text" multiple accept=".cbl,.cob,.cpy,.jcl,.txt,text/*" hidden></label><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Map it</button></div></form>
        <p class="cs-note">Opening several files puts each under its own heading for you.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Mapped</h2>${itemRows(items('inventory'))}</section>`;
  }
  function graph(r) {
    const progs = r.programs || [], W0 = r.waves || [];
    if (!progs.length) return '';
    const cols = W0.length, colW = 190, rowH = 46, W = Math.max(560, cols * colW + 40), maxN = Math.max(...W0.map(w => w.programs.length));
    const H = Math.max(140, maxN * rowH + 50), pos = {};
    W0.forEach((w, i) => w.programs.forEach((p, j) => { pos[p] = [W - 30 - (i + 0.5) * colW, 40 + j * rowH + (maxN - w.programs.length) * rowH / 2]; }));
    const byName = {}; progs.forEach(p => { byName[p.name] = p; });
    const lines = progs.flatMap(p => (p.calls || []).filter(c => pos[c] && c !== p.name).map(c => { const [x1, y1] = pos[p.name], [x2, y2] = pos[c];
      if (Math.abs(x1 - x2) < 1) return `<path class="ed" d="M${(x1 + 70).toFixed(0)},${y1}C${(x1 + 110).toFixed(0)},${y1} ${(x1 + 110).toFixed(0)},${y2} ${(x1 + 70).toFixed(0)},${y2}"/>`;
      return `<path class="ed" d="M${(x1 - 70).toFixed(0)},${y1}C${((x1 + x2) / 2).toFixed(0)},${y1} ${((x1 + x2) / 2).toFixed(0)},${y2} ${(x2 + 70).toFixed(0)},${y2}"/>`; }));
    const boxes = progs.filter(p => pos[p.name]).map(p => { const [x, y] = pos[p.name]; const cls = AP[p.approach] || '';
      return `<g class="nd ${cls}${(p.callers || []).length || (p.started_by || []).length ? '' : ' orphan'}"><rect x="${x - 70}" y="${y - 15}" width="140" height="30" rx="8"/><text x="${x}" y="${y + 4}" text-anchor="middle">${esc(p.name.slice(0, 16))}</text><title>${esc(p.name)} · ${esc(p.approach)} · ${esc(num(p.loc))} lines</title></g>`; });
    const heads = W0.map((w, i) => `<text class="wv" x="${(W - 30 - (i + 0.5) * colW).toFixed(0)}" y="18" text-anchor="middle">Wave ${w.wave}</text>`).join('');
    return `<div class="mfk-graph"><svg viewBox="0 0 ${W} ${H}" style="max-width:${W}px" role="img" aria-label="Programs by wave, arrows to the programs they call">${heads}${lines.join('')}${boxes.join('')}</svg></div>
      <div class="mfk-key"><span><i class="ok"></i>translate</span><span><i class="warn"></i>restructure / replatform first</span><span><i class="bad"></i>rewrite with tests</span><span><i class="orphan"></i>nothing starts it</span></div>`;
  }
  function pInv(d) {
    const r = d.result || {}, t = r.totals || {}, m = r.missing || {};
    const miss = (m.program || []).length + (m.copybook || []).length + (m.proc || []).length;
    return `${head(d, 'map')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Programs', esc(num(t.programs)), `${num(t.loc)} lines · ${num(t.online)} online`)}${tile('Jobs', esc(num(t.jobs)), `${num(t.tables)} DB2 table(s)`)}${tile('Waves', esc(num((r.waves || []).length)), (r.cycles || []).length ? pl(r.cycles.length, 'cycle') : 'no cycles', (r.cycles || []).length > 0)}${tile('Missing', esc(num(miss)), 'referenced, not pasted', miss > 0)}</div></section>
      <section class="card"><h2 class="md-h2">The waves</h2>${graph(r)}<p class="cs-note">Read right to left: wave 1 calls nothing else on the map, so it can move first; each later wave calls only earlier ones.</p></section>
      <section class="card"><h2 class="md-h2">Each program</h2><div class="iv-tw"><table class="tb in-cards mfk-inv"><thead><tr><th>Program</th><th class="r">Wave</th><th class="r">Lines</th><th class="r">Size</th><th>Started by / called by</th><th>Suggested approach</th></tr></thead><tbody>
        ${(r.programs || []).map(p => `<tr><td><b>${esc(p.name)}</b><div class="mut" style="font-size:12px">${esc(p.kind)}${p.tables.length ? ' · ' + esc(p.tables.join(', ')) : ''}</div></td><td class="r">${esc(p.wave)}</td><td class="r">${esc(num(p.loc))}</td><td class="r">${esc(p.size)}</td><td class="mut">${esc([...(p.started_by || []), ...(p.callers || [])].join(', ') || 'nothing in the paste')}</td><td>${tag(p.approach, AP[p.approach] || '')}<div class="mut" style="font-size:12.5px;margin-top:3px">${esc(p.why)}</div></td></tr>`).join('')}</tbody></table></div></section>
      ${miss ? `<section class="card"><h2 class="md-h2">Referenced but not pasted</h2><div class="mfk-touch">${[['Programs', m.program], ['Copybooks', m.copybook], ['JCL procedures', m.proc]].map(([l, xs]) => `<div><span class="mut">${esc(l)}</span>${(xs || []).length ? xs.map(x => `<code>${esc(x)}</code>`).join('') : '<em class="mut">none</em>'}</div>`).join('')}</div></section>` : ''}
      ${(r.table_groups || []).length ? `<section class="card"><h2 class="md-h2">Data that moves together</h2>${r.table_groups.map(g => `<div class="mfk-grp"><div>${g.programs.map(x => `<code>${esc(x)}</code>`).join('')}</div><span class="mut">share</span><div>${g.tables.map(x => `<code class="w">${esc(x)}</code>`).join('')}</div></div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- proof */
  function pProof() {
    if (ST.arg) return one(ST.arg, 'proof', pPf);
    const s = st_(), cbs = copybooks();
    return `<div><h1 class="sd-h">Proof</h1><p class="lead">The new program's output against the old one's, for the same input - record by record, field by field, every difference named for what it usually is.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Compare the outputs</h2><form data-form="proof" class="mfk-grid">
        ${area('old', "The old program's output (text records, CSV or lines)", 'A00001ANNA      000123E\nA00002BEN       000200{', 8, false)}${area('new', "The new program's output", 'A00001ANNA      000123E\nA00002BEN       000200}', 8, false)}
        ${sel('copybook', 'Copybook for fixed-width records', [['', cbs.length ? 'None - compare as lines or CSV' : 'None yet (lay one out on Data layouts)'], ...cbs.map(x => [x.number, `${x.number} · ${x.title}`])], s.ci_copybook || '')}
        ${fld('keys', 'Match records by (fields)', s.keys, '', 'CUST-ID')}${fld('ignore', 'Leave out (fields)', s.ignore, '', 'RUN-DATE')}${fld('tolerance', 'Numbers equal within', s.tolerance, 'type="number" min="0" step="any"')}
        <div class="mfk-row wide"><input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Compare</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Compared</h2>${itemRows(items('proof'))}</section>`;
  }
  const DK = {rounding: ['Rounding', 'warn'], sign: ['Sign', 'warn'], truncation: ['Truncation', 'bad'], spaces: ['Spaces', ''], zeros: ['Zeros / spaces', ''], lowvalues: ['Low-values', 'warn'], case: ['Case', ''], precision: ['Decimals', 'warn'], value: ['Different', 'bad'], only_old: ['Only old', 'bad'], only_new: ['Only new', 'bad']};
  function pPf(d) {
    const r = d.result || {}, tot = r.pairs || 0;
    const parts = [['Same', r.equal, 'ok'], ['Differ', r.differ, 'bad'], ['Only old', r.only_old, 'warn'], ['Only new', r.only_new, 'nw']];
    return `${head(d, 'proof')}<section class="card mfk-sum ${r.proved ? 'okv' : 'badv'}"><div class="mfk-proved"><span class="${r.proved ? 'ok' : r.reordered ? 'warn' : 'bad'}">${r.proved ? 'Proved' : r.reordered ? 'Reordered' : 'Differs'}</span><p class="mfk-big">${esc(r.verdict)}</p></div>
        <div class="mfk-split" role="img" aria-label="Records by result">${parts.filter(p => p[1]).map(([l, v, c2]) => `<i class="${c2}" style="flex:${v} 1 0" title="${esc(l)}: ${esc(num(v))}"></i>`).join('')}</div>
        <div class="mfk-key">${parts.map(([l, v, c2]) => `<span><i class="${c2}"></i>${esc(l)} <b>${esc(num(v || 0))}</b></span>`).join('')}</div></section>
      <section class="card"><dl class="ar-facts">${[['Compared as', {fixed: 'fixed-width records (copybook)', csv: 'CSV with a header', lines: 'lines'}[r.mode] || r.mode], ['Old output', `${num(r.old.records)} record${r.old.records === 1 ? '' : 's'}`], ['New output', `${num(r.new.records)} record${r.new.records === 1 ? '' : 's'}`], ['Matched by', (r.keys || []).join(', ') || 'record order'], ['Fields compared', num(r.compared)], ['Left out', (r.ignored || []).join(', ') || 'none']].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl></section>
      ${(r.by_field || []).length ? `<section class="card"><h2 class="md-h2">Where the differences are</h2>${bars(r.by_field.slice(0, 12).map(f => [f.field, f.n, 'mfk-b', Object.entries(f.kinds).map(([k2, v]) => `${(DK[k2] || [k2])[0]} ${v}`).join(' · ')]), num, 'Differences by field')}</section>` : ''}
      ${(r.diffs || []).length ? `<section class="card"><h2 class="md-h2">The differences</h2><div class="iv-tw"><table class="tb in-cards mfk-diff"><thead><tr><th>Record</th><th>Field</th><th>Old</th><th>New</th><th>What it is</th></tr></thead><tbody>${r.diffs.slice(0, 120).map(x => `<tr><td>${esc(x.key || (x.old ?? x.new))}</td><td style="white-space:nowrap"><b>${esc(x.field)}</b></td><td><code>${esc(x.a)}</code></td><td><code>${esc(x.b)}</code></td><td>${tag((DK[x.kind] || [x.kind])[0], (DK[x.kind] || ['', ''])[1])} <span class="mut" style="font-size:12.5px">${esc(x.label)}</span></td></tr>`).join('')}</tbody></table></div>${r.diffs.length >= 200 ? '<p class="cs-note">The first 200 differences are kept.</p>' : ''}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card mfk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs the new code on a saved input on every pull request and fails when its output stops matching the old program's.</p></div>
      <section class="card"><h2 class="md-h2">What it runs</h2><div class="ar-facts">${[['Toolchain', s.setup || 'none'], ['Build', s.build_cmd || 'none'], ['Run', s.run_cmd || 'not set'], ['New output', s.out_file], ['Old output (saved)', s.golden], ['Compared', s.ci_copybook ? `field by field (${s.ci_copybook})${s.keys ? ', by ' + s.keys : ''}` : 'line by line']].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="output-check.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), cbs = copybooks();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">The character set of your files, the language you move to, how outputs are matched, and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="mfk-grid">
        <h2 class="md-h2 wide" style="margin:0">Data</h2>
        ${sel('encoding', 'Character set of your files', ENC, s.encoding)}${sel('target', 'Language you move to', [['java', 'Java'], ['python', 'Python'], ['csharp', 'C#']], s.target)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Proof</h2>
        ${fld('keys', 'Match records by (fields)', s.keys, '', 'CUST-ID')}${fld('ignore', 'Leave out (fields)', s.ignore, '', 'RUN-DATE, RUN-TIME')}${fld('tolerance', 'Numbers equal within', s.tolerance, 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${sel('setup', 'Toolchain', [['', 'None'], ['java', 'Java 21'], ['python', 'Python 3.12'], ['dotnet', '.NET 8'], ['gnucobol', 'GnuCOBOL']], s.setup)}${fld('build_cmd', 'Build command', s.build_cmd, 'maxlength="400"', 'mvn -q package')}
        ${fld('run_cmd', 'Run the new program on the saved input', s.run_cmd, 'maxlength="400"', 'java -jar target/pay.jar tests/input.txt > output.txt')}${fld('out_file', 'New output file', s.out_file)}
        ${fld('golden', 'Saved old output', s.golden)}${sel('ci_copybook', 'Copybook to compare by', [['', 'None - line by line'], ...cbs.map(x => [x.number, `${x.number} · ${x.title}`])], s.ci_copybook)}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Programs are read from the source text: ALTER, a GO TO ... DEPENDING ON and CALLs through data are listed, not followed.</li><li>Layouts follow IBM Enterprise COBOL with default options: no slack bytes unless SYNCHRONIZED, binary sizes from the digits, the longest OCCURS DEPENDING ON.</li><li>The map is what the pasted sources say; the scheduler, the CICS transaction table and other systems that share the data are not in it.</li><li>A proof holds for the records compared - feed both sides the same inputs, edge cases included.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your mainframe or your servers.</li><li>Calls a translation proved beyond the records it compared.</li><li>Decides the migration for you: every suggested approach comes with its reason.</li><li>Follows anything written inside a program, a copybook, JCL or an output file: they are data.</li></ul></section>`;
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
      if (kind === 'program') await go('program', {text: S(fd.get('text'))});
      else if (kind === 'copybook') await go('copybook', {text: S(fd.get('text')), inputs: pick(['encoding', 'sample'])});
      else if (kind === 'jcl') await go('jcl', {text: S(fd.get('text'))});
      else if (kind === 'inventory') await go('inventory', {text: S(fd.get('text'))});
      else if (kind === 'proof') {
        if (!S(fd.get('old')).trim() || !S(fd.get('new')).trim()) throw new Error('Paste both outputs: the old one and the new one.');
        await go('proof', {text: '## old\n' + S(fd.get('old')).replace(/\s+$/, '') + '\n## new\n' + S(fd.get('new')).replace(/\s+$/, '') + '\n', inputs: pick(['copybook', 'keys', 'ignore', 'tolerance'])});
      }
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['encoding', 'target', 'keys', 'ignore', 'tolerance', 'run_cmd', 'build_cmd', 'golden', 'out_file', 'ci_copybook', 'runner', 'setup'];


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
    const box = $('#mfFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/mfdesk/chat'); ST.chat = r.id; }
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


