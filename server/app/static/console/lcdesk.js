/* COMPILER DESK - the Compiler Construction Engineer's own section, like the finance desks (owner: "Compiler Construction Engineer
   -- TOP DEVLOPENT OF IT AND DESIGN SAME AS OTHER SECTIONS"). A thin top bar, then the Compiler chat (its own conversation, kind
   'langlab') beside the desk's pages: Today, Design a language, Languages (grammar, playground, tests, interpreter, check, release,
   versions), Settings. The pages call /api/lcdesk/do/<part>; her interpreter runs only in the locked sandbox. */
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

  const TABS = [['today', 'Today'], ['new', 'Design a language'], ['langs', 'Languages'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What kind of language could help my work?', 'What is a DSL, in plain words?', 'Design a language for my pricing rules'],
    new: ['Help me describe my language', 'Should it be an interpreter or a compiler?', 'Write three example programs for me'],
    langs: ['Why does this test fail?', 'Add while loops to this language', 'Make the error messages friendlier'],
    settings: ['What does the sandbox stop?', 'When do I need a compiler?', 'How long may a program run?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', play: {}, edit: '', newsrc: '', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.lcdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.lcdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'compiler_eng', name: 'Compiler'} : null;
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
  const run = (part, a) => api('POST', '/api/lcdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/lcdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Compiler Construction Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="lcHire">Hire the Compiler Construction Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#lcHire').onclick = async () => { try { await api('POST', '/api/employees/compiler_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Compiler</div><div class="sd-site" id="lcSite"></div></div>
          <span id="lcState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Compiler chat">
          <div class="sd-chathead"><div class="t"><b>Compiler chat</b><span>Say what your language is for, paste a program that fails, or drop an example file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="lcFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="lcPick" multiple hidden accept=".txt,.md,.json,.csv,.py,.js,.sql,.yaml,.yml,.toml,.ini,.xml,.pdf,image/*">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Compiler desk" id="sdTabs"></nav>
          <div id="lcPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Your interpreter runs only in a locked sandbox.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Describe a language…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#lcPick').click()});
    $('#lcPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.lcdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.lcdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/lcdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#lcPage').addEventListener('click', onPageClick);
    $('#lcPage').addEventListener('submit', onSubmit);
    $('#lcPage').addEventListener('change', onChange);
    $('#lcPage').addEventListener('input', onInput);
    $('#lcPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#lcState'); if (!el) return;
    const k = K(), b = (k.busy || []).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : b ? ['ok', pl(b, 'language') + ' being designed'] : k.failing ? ['warn', pl(k.failing, 'test') + ' failing'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#lcSite').textContent = [pl((k.langs || []).length, 'language'), `${num(k.passing || 0)} / ${num(k.tests || 0)} tests pass`].join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {langs: (k.busy || []).length || k.failing || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/lcdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#lcPage'); if (!box) return;
    const fn = {today: pToday, new: pNew, langs: pLangs, settings: pSettings}[ST.tab] || pToday;
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
  const BUSY = ['designing', 'improving'];
  const LST = {designing: ['Being designed', 'v'], improving: ['Being changed', 'v'], failed: ['Could not design', 'bad']};
  const lTag = L => LST[L.status] ? tag(LST[L.status][0], LST[L.status][1]) : !L.grammar ? tag('No grammar yet', '') :
    L.last_run && L.last_run.grammar_ok === false ? tag('Grammar problem', 'bad') : L.failed ? tag(`${L.failed} failing`, 'bad') :
    L.total ? tag('All tests pass', 'ok') : tag('No tests yet', 'warn');
  const SECS = [['grammar', 'Grammar'], ['play', 'Playground'], ['tests', 'Tests'], ['code', 'Interpreter'], ['check', 'Check'], ['release', 'Release'], ['versions', 'Versions']];
  const TST = {pass: ['Passes', 'ok'], fail: ['Fails', 'bad'], new: ['Needs your yes', 'warn']};
  const KIND = {output: 'What it prints', error: 'Must be refused', tree: 'The tree'};
  const lang = id => ST.out['L:' + id] || (K().langs || []).find(x => x.id === id) || null;
  function passBar(L) {
    const t = L.total || 0, p = L.passed || 0, f = L.failed || 0, n = Math.max(0, t - p - f);
    if (!t) return '<div class="lc-bar empty"><i></i></div>';
    return `<div class="lc-bar" role="img" aria-label="${esc(p)} of ${esc(t)} tests pass"><i class="p" style="width:${(p / t * 100).toFixed(1)}%"></i><i class="f" style="width:${(f / t * 100).toFixed(1)}%"></i><i class="n" style="width:${(n / t * 100).toFixed(1)}%"></i></div>`;
  }
  function card(L) {
    return `<button type="button" class="lc-card" data-open="${esc(L.id)}"><span class="lc-glyph" aria-hidden="true">${esc((L.ext || L.name || '?').slice(0, 3))}</span>
      <span class="t"><b>${esc(L.name)}</b><span class="mut">${esc(L.number)} · version ${esc(L.version || 0)} · ${esc(ago(L.updated_at))}</span>
      <span class="p">${esc((L.purpose || '').slice(0, 120))}</span>${passBar(L)}<span class="mut s">${L.total ? `${esc(L.passed)} of ${esc(L.total)} tests pass` : 'No tests yet'}</span></span>${lTag(L)}</button>`;
  }
  const starterCards = () => (K().starters || []).map(s => `<button type="button" class="lc-idea" data-starter="${esc(s.i)}"><b>${esc(s.name)}</b><span>${esc(s.say)}</span><em>${s.ready ? 'Ready to try' : 'Hoola designs it (about a minute)'}</em></button>`).join('');
  const pre = (t, cls) => `<pre class="lc-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  function treeView(n, depth) {
    if (!n) return '';
    if (n.tok !== undefined) return `<li class="tk"><span class="k">${esc(n.tok)}</span> <code>${esc(n.text)}</code> <span class="mut">${esc(n.line)}:${esc(n.col)}</span></li>`;
    const kids = (n.children || []).map(c => treeView(c, depth + 1)).join('');
    return `<li><details${depth < 3 ? ' open' : ''}><summary><b>${esc(n.rule)}</b> <span class="mut">${esc(n.line)}:${esc(n.col)}</span></summary><ul>${kids}</ul></details></li>`;
  }
  const errBox = e => `<div class="lc-err"><b>${esc(e.message || e)}</b>${e.pointer ? pre(e.pointer, 'ptr') : ''}</div>`;
  const busyCard = L => `<section class="card"><div class="lc-run"><b>${esc((LST[L.status] || [''])[0])}</b><span class="mut">${esc(L.job || '')}</span><i><b></b></i></div><p class="cs-note">It takes about a minute. You can keep chatting meanwhile; this page shows the result by itself.</p></section>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), ls = k.langs || [];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : (k.busy || []).length ? `${pl(k.busy.length, 'language')} being worked on.` : ls.length ? 'All in order.' : 'Design your first language.';
    const tiles = [
      `<div class="k"><div class="l">Languages</div><div class="v">${esc(num(ls.length))}</div><div class="s">${esc(pl((k.busy || []).length, 'being designed', 'being designed'))}</div></div>`,
      `<div class="k"><div class="l">Tests passing</div><div class="v">${esc(num(k.passing || 0))}<small> / ${esc(num(k.tests || 0))}</small></div><div class="s">golden tests across all</div></div>`,
      `<div class="k${k.failing ? ' low bad' : ''}"><div class="l">Failing</div><div class="v">${esc(num(k.failing || 0))}</div><div class="s">${k.failing ? 'open them below' : 'nothing failing'}</div></div>`,
      `<div class="k"><div class="l">Programs run in</div><div class="v lc-sm">Locked sandbox</div><div class="s">${(k.health || {}).net_isolated ? 'no network, no server files' : 'no server files, network blocked'}</div></div>`];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      ${(k.busy || []).length ? `<section class="card"><h2 class="md-h2">Being worked on</h2>${k.busy.map(L => `<div class="lc-run"><b>${esc(L.number)} ${esc(L.name)}</b><span class="mut">${esc(L.job || '')}</span><i><b></b></i><button class="btn soft sm" type="button" data-open="${esc(L.id)}">Open</button></div>`).join('')}</section>` : ''}
      <section class="card"><div class="md-acts" style="margin:0 0 12px"><h2 class="md-h2" style="margin:0">Your languages</h2>${CAN() ? '<button class="btn soft sm" type="button" data-go="new">Design a language</button>' : ''}</div>
        ${ls.length ? `<div class="lc-grid">${ls.slice(0, 8).map(card).join('')}</div>` : empty('No languages yet.')}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Start from an example</h2><div class="lc-ideas">${starterCards()}</div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- design a language */
  function pNew() {
    return `<div><h1 class="sd-h">Design a language</h1><p class="lead">Say what it is for and show two or three programs you would like to write in it. Hoola designs the grammar, writes the ${st_().target === 'compiler' ? 'compiler' : 'interpreter'} and the golden tests, checks them and runs them.</p></div>${ro()}
      ${CAN() ? `<section class="card"><form data-form="design" class="lc-form">
        <label class="ins-lab">What the language is for<textarea class="in" name="words" rows="3" maxlength="3000" required placeholder="Pricing rules for my shop: discounts by amount, by customer type and by festival, so my staff can change them without a developer"></textarea></label>
        <label class="ins-lab">Programs you would like to write (optional, the best help)<textarea class="in mono" name="examples" rows="6" maxlength="6000" spellcheck="false" placeholder="when total > 1000 then discount 10%\nwhen customer is member then discount 5%\nwhen festival is diwali and total > 500 then discount 15%"></textarea></label>
        <div class="md-acts"><span class="mut" style="font-size:13px">About a minute. The grammar is checked by Hoola's own parser generator before you see it.</span><button class="btn" type="submit">Design it</button></div></form></section>` : ''}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Or start from an example</h2><div class="lc-ideas">${starterCards()}</div></section>
      <section class="card"><h2 class="md-h2">Or write it yourself</h2><form data-form="blank" class="ar-row"><label class="ins-lab" style="flex:1">Name<input class="in" name="name" maxlength="80" required placeholder="My language"></label><button class="btn soft" type="submit">Start empty</button></form></section>` : ''}
      <section class="card"><h2 class="md-h2">What you get</h2><div class="lc-gets">
        <div><b>A grammar</b><span>Checked for undefined names, left recursion, choices that can never win, endless loops and slow patterns.</span></div>
        <div><b>Clear errors</b><span>The line, the column, what was expected and a pointer - for the people who will write in it.</span></div>
        <div><b>An interpreter or compiler</b><span>Plain Python, run only in a locked sandbox with a time limit per test.</span></div>
        <div><b>Golden tests</b><span>You say yes to what each program should do; a change is kept only when no more tests fail.</span></div>
        <div><b>Fuzzing</b><span>Programs made from the grammar must read; broken programs must not crash the interpreter.</span></div>
        <div><b>A release</b><span>Railroad diagrams, a language reference, VS Code colours and a zip that runs anywhere Python runs.</span></div></div></section>`;
  }

  /* ---------------------------------------------------------------- languages */
  function pLangs() {
    const ls = K().langs || [];
    if (ST.arg) return pLang(ST.arg.split('/')[0], ST.arg.split('/')[1] || '');
    return `<div><h1 class="sd-h">Languages</h1><p class="lead">${esc(pl(ls.length, 'language'))}. Open one to edit its grammar, try programs and run the tests.</p></div>
      <section class="card">${ls.length ? `<div class="lc-grid">${ls.map(card).join('')}</div>` : `${empty('Nothing here.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="new">Design a language</button></div>`}</section>`;
  }
  function pLang(id, sec) {
    const L = lazyOut('L:' + id, 'get', {id});
    if (!L) return loading();
    if (L.error) return `<section class="card">${err(L)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="langs">Back</button></div></section>`;
    sec = sec || (L.grammar ? 'play' : 'grammar');
    const busy = BUSY.includes(L.status);
    const nav = `<nav class="lc-secs" aria-label="Parts of the language">${SECS.map(([k2, n]) => `<button type="button" data-sec="${esc(k2)}" aria-current="${k2 === sec}">${esc(n)}${k2 === 'tests' && L.failed ? `<span class="n bad">${esc(L.failed)}</span>` : k2 === 'tests' && L.last_run && L.last_run.new ? `<span class="n">${esc(L.last_run.new)}</span>` : ''}</button>`).join('')}</nav>`;
    const P = L.proposal || {};
    const prop = P.error ? `<section class="card lc-prop bad"><b>Hoola could not make the change.</b><span>${esc(P.error)}</span>${CAN() ? '<button class="btn soft sm" type="button" data-prop="0">Dismiss</button>' : ''}</section>` :
      P.at ? `<section class="card lc-prop"><div><b>A change waits for you.</b><span>${esc(P.summary || '')}</span><span class="mut">With it ${esc(pl(P.failed, 'test'))} would fail (${esc(P.before_failed || 0)} now)${P.grammar_ok === false ? ' and the grammar has a problem' : ''}, so Hoola did not keep it by itself.</span></div>${CAN() ? '<div class="lc-acts"><button class="btn soft sm" type="button" data-prop="0">Drop it</button><button class="btn sm" type="button" data-prop="1">Use it anyway</button></div>' : ''}</section>` : '';
    const body = busy ? busyCard(L) : L.status === 'failed' ? `<section class="card"><p class="cs-neg" style="margin:0">${esc(L.job || 'It could not be designed.')}</p><div class="md-acts"><span class="mut" style="font-size:13px">Say it again with an example program or two - it helps the most.</span><button class="btn soft" type="button" data-go="new">Try again</button></div></section>` :
      ({grammar: sGrammar, play: sPlay, tests: sTests, code: sCode, check: sCheck, release: sRelease, versions: sVersions}[sec] || sPlay)(L);
    return `<div class="lc-head"><button class="ib" type="button" data-go="langs" aria-label="All languages">${svg(IC.back)}</button>
        <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(L.name)}</h1><p class="lead" style="margin:2px 0 0">${esc(L.number)} · version ${esc(L.version)} · files .${esc(L.ext)}${L.total ? ` · ${esc(L.passed)} of ${esc(L.total)} tests pass` : ''}</p></div>${lTag(L)}</div>
      ${L.purpose ? `<p class="lc-purpose">${esc(L.purpose)}</p>` : ''}${ro()}${nav}${prop}${body}`;
  }

  /* grammar: the editor, the checks, the diagrams, a change in words */
  function sGrammar(L) {
    const live = ST.out['chk:' + L.id];
    const chk = live || lazyOut('chkS:' + L.id, 'check', {id: L.id}) || {};
    const errs = chk.errors || [], warns = chk.warnings || [];
    const rr = lazyOut('rr:' + L.id, 'railroads', {id: L.id});
    return `<section class="card"><div class="md-acts" style="margin:0 0 10px"><h2 class="md-h2" style="margin:0">Grammar</h2><span class="mut" style="font-size:13px">${live ? 'Checked as typed (not saved yet)' : 'The saved grammar'}</span></div>
        <form data-form="grammar" data-id="${esc(L.id)}">
          <textarea class="in mono lc-ed" name="grammar" rows="${Math.min(28, Math.max(10, (L.grammar || '').split('\n').length + 2))}" spellcheck="false" ${CAN() ? '' : 'readonly'} aria-label="The grammar">${esc(L.grammar || '')}</textarea>
          <div class="lc-row"><label class="ins-lab">Start rule<select class="in" name="start">${(chk.rules || []).map(r => `<option value="${esc(r.name)}"${r.name === (L.start || chk.start) ? ' selected' : ''}>${esc(r.name)}</option>`).join('') || `<option>${esc(L.start || '')}</option>`}</select></label>
          ${CAN() ? '<span style="flex:1"></span><button class="btn soft" type="button" data-checknow="1">Check</button><button class="btn" type="submit">Save and run the tests</button>' : ''}</div></form>
        <details class="lc-help"><summary>How to write a grammar</summary><div class="qa-body">
          <p><code>program : statement* ;</code> lower case = a rule. <code>NAME : /[^\\W\\d]\\w*/ ;</code> UPPER CASE = a token (a /pattern/ or a "fixed text"). <code>"let"</code> a fixed word, <code>( )</code> groups, <code>*</code> many, <code>+</code> one or more, <code>?</code> optional, <code>|</code> or (the first that fits wins).</p>
          <p><code>%ignore /\\s+/</code> skips spaces; add <code>%ignore /#[^\\n]*/</code> for comments. <code>?rule</code> is left out of the tree when it has one child, <code>!rule</code> keeps every fixed word. No left recursion: write <code>expr : term (("+" | "-") term)* ;</code>. Names may use any script.</p></div></details></section>
      <section class="card"><h2 class="md-h2">Checks</h2>
        ${errs.length || warns.length ? [...errs.map(x => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">${x.line ? `<b>Line ${esc(x.line)}</b> · ` : ''}${esc(x.say)}</span></div>`),
          ...warns.map(x => `<div class="cs-row"><span class="cs-dot warn"></span><span style="flex:1">${x.line ? `<b>Line ${esc(x.line)}</b> · ` : ''}${esc(x.say)}</span></div>`)].join('') :
          (chk.rules ? '<div class="cs-row"><span class="cs-dot ok"></span><span style="flex:1">No problems found: every name is defined, no left recursion, no endless loops, no choice that can never win.</span></div>' : empty('Checking…'))}
        ${(chk.keywords || []).length ? `<div class="lc-kw"><span class="mut">Fixed words</span>${chk.keywords.map(w => `<code>${esc(w)}</code>`).join('')}</div>` : ''}
        ${(chk.tokens || []).length ? `<table class="tb lc-tok"><thead><tr><th>Token</th><th>Pattern</th><th>Example</th></tr></thead><tbody>${chk.tokens.map(t => `<tr><td><b>${esc(t.name)}</b></td><td><code>${esc(t.regex ? '/' + t.pattern + '/' : '"' + t.pattern + '"')}</code></td><td><code>${esc(t.example)}</code></td></tr>`).join('')}</tbody></table>` : ''}</section>
      <section class="card"><h2 class="md-h2">Railroad diagrams</h2><p class="cs-note" style="margin-top:0">Each rule drawn as the paths a program can take, left to right. Rounded boxes are fixed words, blue boxes tokens, violet boxes other rules.</p>
        ${!rr ? empty('Drawing…') : rr.error ? err(rr) : (rr.items || []).length ? `<div class="lc-rr">${rr.items.map(x => `<figure><figcaption><b>${esc(x.rule)}</b></figcaption><div class="lc-svg">${x.svg}</div></figure>`).join('')}</div>` : empty('The grammar does not read yet.')}</section>
      ${CAN() && L.grammar ? `<section class="card"><h2 class="md-h2">Ask Hoola to change it</h2><form data-form="improve" data-id="${esc(L.id)}" class="lc-form">
        <textarea class="in" name="words" rows="2" maxlength="2000" placeholder="Add while loops; allow comments with //; numbers with commas like 1,000"></textarea>
        <div class="md-acts"><span class="mut" style="font-size:13px">${L.failed ? `Empty = make the ${esc(pl(L.failed, 'failing test'))} pass. ` : ''}The change is kept only when no more tests fail.</span><button class="btn" type="submit">Change it</button></div></form></section>` : ''}`;
  }

  /* playground */
  function sPlay(L) {
    const r = ST.out['play:' + L.id] || null;
    const src = ST.play[L.id] !== undefined ? ST.play[L.id] : ((L.tests || []).find(t => t.kind !== 'error') || {}).src || '';
    const res = !r ? empty('Type a program - it is read as you type. Run sends it to the interpreter.') : r.error && !r.json && !r.tree && typeof r.error === 'string' ? err(r) :
      !r.ok ? errBox(r.error || {}) :
      `<div class="lc-out">${r.ran ? `<div><div class="lc-lab">${r.outcome === 'ok' ? 'Output' : r.outcome === 'error' ? 'Refused by the language' : r.outcome === 'timeout' ? 'Stopped' : 'The interpreter crashed'}</div>
          ${r.load_error ? `<p class="cs-neg">${esc(r.load_error)}</p>` : r.outcome === 'ok' ? pre(r.output || '(nothing printed)', 'out') : `<p class="${r.outcome === 'error' ? '' : 'cs-neg'}" style="margin:4px 0">${esc(r.message || '')}${r.line ? ` (line ${esc(r.line)})` : ''}</p>${r.output ? pre(r.output, 'out') : ''}`}<span class="mut s">ran in ${esc(r.run_ms)} ms</span></div>` : ''}
        <div><div class="lc-lab">The tree <span class="mut">read in ${esc(r.ms)} ms</span></div><ul class="lc-tree">${treeView(r.json, 0)}</ul>
        <details class="lc-help"><summary>As text</summary>${pre(r.tree || '')}</details></div></div>`;
    return `<section class="card"><form data-form="play" data-id="${esc(L.id)}">
        <textarea class="in mono lc-ed" name="src" rows="8" spellcheck="false" aria-label="A program" data-live="${esc(L.id)}">${esc(src)}</textarea>
        <div class="lc-row"><span class="mut" style="font-size:13px;flex:1">${(L.interpreter || '').trim() ? 'Run reads it and runs it in the locked sandbox.' : 'No interpreter yet - the playground shows the tree.'}</span>
        ${CAN() ? '<button class="btn soft" type="button" data-savetest="1">Save as a test</button>' : ''}<button class="btn" type="submit">${(L.interpreter || '').trim() ? 'Run' : 'Read'}</button></div></form></section>
      <section class="card">${res}</section>`;
  }

  /* golden tests */
  function sTests(L) {
    const res = {}; ((L.last_run || {}).results || []).forEach(x => { res[x.id] = x; });
    const run_ = L.last_run || {};
    const rows = (L.tests || []).map(t => {
      const x = res[t.id] || {}, s = TST[x.status] || ['Not run', ''];
      const got = x.parsed === false ? (x.error || {}).message || '' : t.kind === 'tree' ? x.tree || '' : x.outcome === 'ok' ? x.output || '' : x.message || '';
      const editing = ST.edit === t.id;
      return `<details class="lc-test" data-key="t:${esc(t.id)}"${ST.open.has('t:' + t.id) || editing ? ' open' : ''}><summary><span class="cs-dot ${s[1] || ''}"></span><b>${esc(t.name)}</b><span class="mut hide-sm">${esc(KIND[t.kind])}</span><span style="flex:1"></span>${tag(s[0], s[1])}</summary>
        <div class="qa-body">${editing ? testForm(L, t) : `<div class="lc-tri"><div><div class="lc-lab">Program</div>${pre(t.src || '(empty)')}</div>
          <div><div class="lc-lab">${t.kind === 'error' ? 'The error should mention' : 'Expected'}</div>${pre(t.expect || (t.kind === 'error' ? '(any error)' : '(not set yet)'), t.expect ? '' : 'dim')}</div>
          <div><div class="lc-lab">It gives now</div>${pre(got || '(nothing)', x.status === 'fail' ? 'bad' : '')}</div></div>
          ${x.why ? `<p class="${x.status === 'fail' ? 'cs-neg' : 'mut'}" style="margin:8px 0 0;font-size:13.5px">${esc(x.why)}</p>` : ''}
          ${CAN() ? `<div class="lc-acts">${(x.status === 'new' || x.status === 'fail') && t.kind !== 'error' && (x.outcome === 'ok' || (t.kind === 'tree' && x.tree)) ? `<button class="btn sm" type="button" data-accept="${esc(t.id)}">Keep this answer</button>` : ''}<button class="btn soft sm" type="button" data-edit="${esc(t.id)}">Edit</button><button class="btn soft sm" type="button" data-try="${esc(t.id)}">Open in the playground</button><button class="btn soft sm" type="button" data-tdel="${esc(t.id)}">Delete</button></div>` : ''}`}</div></details>`;
    }).join('');
    return `<section class="card"><div class="lc-sum">${passBar(L)}<span><b>${esc(L.passed)}</b> pass · <b class="${L.failed ? 'cs-neg' : ''}">${esc(L.failed)}</b> fail · <b>${esc(run_.new || 0)}</b> need your yes</span><span class="mut">${run_.at ? 'run ' + esc(ago(run_.at)) : 'not run yet'}</span>
        ${CAN() ? '<span style="flex:1"></span><button class="btn soft sm" type="button" data-more="1">More tests from Hoola</button><button class="btn sm" type="button" data-runall="1">Run all</button>' : ''}</div>
        ${run_.load_error ? `<p class="cs-neg">The interpreter does not load: ${esc(run_.load_error)}</p>` : ''}${run_.grammar_ok === false ? `<p class="cs-neg">The grammar has problems, so nothing reads: ${esc(((run_.grammar_errors || [])[0] || {}).say || '')}</p>` : ''}
        ${rows || empty('No tests yet. Add a program and what it should do - or ask Hoola for some.')}</section>
      ${CAN() && ST.edit !== 'new' ? '<div class="md-acts"><span></span><button class="btn soft" type="button" data-edit="new">Add a test</button></div>' : ''}
      ${CAN() && ST.edit === 'new' ? `<section class="card"><h2 class="md-h2">A new test</h2>${testForm(L, {id: '', name: '', kind: 'output', src: ST.newsrc || '', expect: ''})}</section>` : ''}`;
  }
  function testForm(L, t) {
    return `<form data-form="test" data-id="${esc(L.id)}" data-tid="${esc(t.id)}" class="lc-form">
      <div class="lc-row"><label class="ins-lab" style="flex:2">Name<input class="in" name="name" maxlength="80" value="${esc(t.name)}" placeholder="Precedence"></label>
      <label class="ins-lab" style="flex:1">Kind<select class="in" name="kind">${Object.entries(KIND).map(([k2, n]) => `<option value="${k2}"${t.kind === k2 ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label></div>
      <label class="ins-lab">Program<textarea class="in mono" name="src" rows="5" spellcheck="false">${esc(t.src)}</textarea></label>
      <label class="ins-lab">Expected (what it prints, a word of the error, or the tree; empty = Hoola runs it and you say yes)<textarea class="in mono" name="expect" rows="3" spellcheck="false">${esc(t.expect)}</textarea></label>
      <div class="md-acts"><button class="btn soft" type="button" data-edit="">Cancel</button><button class="btn" type="submit">Save and run</button></div></form>`;
  }

  /* interpreter / compiler */
  function sCode(L) {
    const comp = st_().target === 'compiler';
    return `<section class="card"><div class="md-acts" style="margin:0 0 10px"><h2 class="md-h2" style="margin:0">${comp ? 'Compiler' : 'Interpreter'}</h2><span class="mut" style="font-size:13px">Python · runs only in the locked sandbox</span></div>
      ${(L.last_run || {}).load_error ? `<p class="cs-neg" style="margin-top:0">It does not load: ${esc(L.last_run.load_error)}</p>` : ''}
      <form data-form="code" data-id="${esc(L.id)}"><textarea class="in mono lc-ed" name="interpreter" rows="${Math.min(34, Math.max(14, (L.interpreter || '').split('\n').length + 2))}" spellcheck="false" ${CAN() ? '' : 'readonly'} aria-label="The interpreter">${esc(L.interpreter || '')}</textarea>
      ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Saving makes a new version and runs every test.</span><button class="btn" type="submit">Save and run the tests</button></div>' : ''}</form>
      <details class="lc-help" open><summary>How it is called</summary><div class="qa-body"><p><code>def run(tree):</code> is called once per program. What it prints is the program's output${comp ? ' - for a compiler, the code it makes (Python, JavaScript, SQL ...)' : ''}. <code>raise LangError("message", node)</code> for a mistake in the program - a clean error with its line, not a crash.</p>
      <p><code>tree.rule</code>, <code>tree.children</code> (nodes and tokens), <code>node.nodes("rule")</code>, <code>node.toks("NAME")</code>; a token has <code>.kind</code>, <code>.text</code>, <code>.line</code>. Standard library only; no files, no network, ${esc(st_().limit_s || 2)} s per program.</p></div></details></section>`;
  }

  /* check: fuzzing and speed */
  function sCheck(L) {
    const f = L.fuzz || {};
    return `<section class="card"><div class="md-acts" style="margin:0 0 6px"><h2 class="md-h2" style="margin:0">Check it hard</h2>${CAN() ? '<button class="btn" type="button" data-fuzz="1">Check it now</button>' : ''}</div>
        <p class="cs-note" style="margin-top:0">Hoola makes ${esc(st_().fuzz_n || 40)} programs from the grammar (each must read), breaks your test programs on purpose (each must give a clean error, never crash the interpreter) and measures how fast it reads.</p>
        ${f.at ? `<section class="cs-hero lc-hero"><div class="top">
          <div class="k${f.unreadable ? ' low bad' : ''}"><div class="l">Made-up programs</div><div class="v">${esc(f.made - f.unreadable)}<small> / ${esc(f.made)}</small></div><div class="s">read back by the grammar</div></div>
          <div class="k${f.crashes ? ' low bad' : ''}"><div class="l">Broken programs</div><div class="v">${esc(f.crashes)}</div><div class="s">${f.broken_ran ? `crashes in ${esc(pl(f.broken_ran, 'run'))}` : 'none reached the interpreter'}</div></div>
          <div class="k"><div class="l">Reading speed</div><div class="v lc-sm">${esc(num(f.kb_per_s))} KB/s</div><div class="s">on this server</div></div>
          <div class="k"><div class="l">Checked</div><div class="v lc-sm">${esc(ago(f.at))}</div><div class="s">${f.ok ? 'all fine' : 'see below'}</div></div></div></section>
          ${(f.unreadable_examples || []).map(x => `<div class="lc-fz"><b>A program the grammar made but cannot read</b>${pre(x.src)}<span class="cs-neg">${esc(x.error)}</span><span class="mut">Often a choice where an earlier one wins too early, or a fixed word that a token also matches.</span></div>`).join('')}
          ${(f.crash_examples || []).map(x => `<div class="lc-fz"><b>${x.outcome === 'timeout' ? 'It never stopped on' : 'The interpreter crashed on'}</b>${x.src ? pre(x.src) : ''}<span class="cs-neg">${esc(x.error)}</span><span class="mut">Raise LangError for wrong programs instead of letting Python fail.</span></div>`).join('')}
          ${(f.parser_faults || []).map(x => `<div class="lc-fz"><b>The parser itself failed</b>${pre(x.src)}<span class="cs-neg">${esc(x.error)}</span></div>`).join('')}` : empty('Not checked yet.')}</section>`;
  }

  /* release: spec, download */
  function sRelease(L) {
    const sp = lazyOut('spec:' + L.id + ':' + L.version, 'spec', {id: L.id});
    return `<section class="card"><div class="md-acts" style="margin:0 0 6px"><h2 class="md-h2" style="margin:0">Download</h2><button class="btn" type="button" data-zip="${esc(L.id)}">Download the zip</button></div>
        <p class="cs-note" style="margin-top:0">Everything to use and share the language, plain Python 3.9+ with no other packages.</p>
        <div class="lc-files">${[['cli.py', `python cli.py program.${L.ext} reads and runs a program`], ['run_tests.py', `the ${pl(L.total, 'golden test')}`], ['grammar.hg', 'the grammar'],
          ['interpreter.py', st_().target === 'compiler' ? 'the compiler' : 'the interpreter'], ['hoola_lang.py', 'the parser'], ['SPEC.md', 'the language reference'], ['railroad/', 'a diagram per rule'], ['editor/', 'VS Code colours for .' + L.ext]]
          .map(([n, d]) => `<div><code>${esc(n)}</code><span class="mut">${esc(d)}</span></div>`).join('')}</div></section>
      <section class="card"><h2 class="md-h2">Language reference</h2><p class="cs-note" style="margin-top:0">SPEC.md as it ships in the zip: the words of the language, its tokens, every rule with its railroad diagram (the Grammar tab shows them drawn) and the examples that pass.</p>${!sp ? empty('Writing…') : sp.error ? err(sp) : pre(sp.md, 'lc-spec')}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">About it</h2><form data-form="meta" data-id="${esc(L.id)}" class="lc-row wrap">
        <label class="ins-lab" style="flex:2">Name<input class="in" name="name" maxlength="80" value="${esc(L.name)}"></label>
        <label class="ins-lab" style="flex:1">File ending<input class="in" name="ext" maxlength="10" value="${esc(L.ext)}"></label>
        <label class="ins-lab" style="flex:1 1 100%">What it is for<textarea class="in" name="purpose" rows="2" maxlength="600">${esc(L.purpose)}</textarea></label>
        <div class="md-acts" style="flex:1 1 100%"><span></span><button class="btn soft" type="submit">Save</button></div></form></section>` : ''}`;
  }

  function sVersions(L) {
    const vs = (L.versions || []).slice().reverse();
    return `<section class="card"><h2 class="md-h2">Versions</h2>${vs.map(v => `<div class="cs-row"><span class="lc-vn">${esc(v.n)}</span><span style="flex:1"><b>${esc(v.note || 'Saved')}</b><span class="mut"> · ${esc(ago(v.at))} · ${esc(v.passed)} pass, ${esc(v.failed)} fail</span></span>${CAN() && v.n !== L.version ? `<button class="btn soft sm" type="button" data-restore="${esc(v.n)}">Bring back</button>` : v.n === L.version ? tag('Now', 'ok') : ''}</div>`).join('') || empty('No versions yet.')}
        <p class="cs-note">Every save of the grammar or the interpreter is a version. Bringing one back makes a new version, so nothing is lost.</p></section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Remove</h2><div class="md-acts" style="margin:0"><span class="mut" style="font-size:13px">The language, its tests and its versions.</span><button class="btn soft" type="button" data-del="${esc(L.id)}">Remove this language</button></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), h = K().health || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">How programs are tested and what running one means.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="lc-form">
        <fieldset class="lc-radio"><legend>When a program runs, it</legend>
          <label><input type="radio" name="target" value="interpreter"${s.target !== 'compiler' ? ' checked' : ''}><span><b>Is run</b> - an interpreter computes the answer and prints it</span></label>
          <label><input type="radio" name="target" value="compiler"${s.target === 'compiler' ? ' checked' : ''}><span><b>Is compiled</b> - a compiler prints the code it makes (Python, JavaScript, SQL ...)</span></label></fieldset>
        <div class="lc-row"><label class="ins-lab" style="flex:1">Time per program (seconds)<input class="in" name="limit_s" type="number" min="1" max="10" value="${esc(s.limit_s || 2)}"></label>
        <label class="ins-lab" style="flex:1">Made-up programs per check<input class="in" name="fuzz_n" type="number" min="10" max="200" value="${esc(s.fuzz_n || 40)}"></label></div>
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Used by every language on this desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">The sandbox</h2><div class="cs-row"><span class="cs-dot ok"></span><span style="flex:1">Programs and interpreters run in a locked child process: ${h.net_isolated ? 'its own empty network' : 'network calls refused'}, no keys, no server files, CPU / memory / time limits. Grammar engine ${esc(h.runtime || '')}.</span></div></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs your interpreter or your programs outside the locked sandbox.</li><li>Keeps a change that makes more tests fail without your tap.</li><li>Says a test passes before it has run.</li><li>Publishes your language or sends it anywhere.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  const curId = () => ST.tab === 'langs' && ST.arg ? ST.arg.split('/')[0] : '';
  const curSec = () => ST.tab === 'langs' && ST.arg ? (ST.arg.split('/')[1] || '') : '';
  function setLang(L) { ST.out['L:' + L.id] = L; for (const k of Object.keys(ST.out)) if (/^(chkS|rr|spec):/.test(k) && k.includes(L.id)) delete ST.out[k]; delete ST.out['chk:' + L.id]; }
  async function langDone(L, msg) { setLang(L); await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  /* while a language is being designed or changed, the page follows it */
  setInterval(() => {
    if (!ST.d) return;
    const id = curId(), L = id ? ST.out['L:' + id] : null;
    if (L && BUSY.includes(L.status)) run('get', {id}).then(r => { if (!BUSY.includes(r.status)) { setLang(r); refreshDesk(false); } else ST.out['L:' + id] = r; showPage(true); }).catch(() => {});
    else if ((K().busy || []).length && !id) refreshDesk(true);
  }, 4000);
  /* the playground reads as she types */
  let liveT = 0;
  function onInput(e) {
    const el = e.target;
    if (el.dataset.live) {
      const id = el.dataset.live; ST.play[id] = el.value; clearTimeout(liveT);
      liveT = setTimeout(() => run('parse', {id, src: el.value}).then(r => { const o = ST.out['play:' + id]; if (o && o.ran && o.src === el.value) return; ST.out['play:' + id] = {...r, src: el.value}; showPage(true); }).catch(() => {}), 450);
    }
  }
  async function getZip(id) {
    try {
      const r = await fetch('/api/lcdesk/zip/' + enc(id), {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = `Could not download (${r.status})`; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
      const cd = r.headers.get('Content-Disposition') || '', m = /filename="([^"]+)"/.exec(cd);
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = m ? m[1] : 'language.zip'; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 3000);
    } catch (e) { toast(e.message, true); }
  }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { delete ST.out['L:' + op.dataset.open]; location.hash = '#/langs/' + op.dataset.open; return; }
    const sc = t.closest('[data-sec]'); if (sc) { location.hash = '#/langs/' + curId() + '/' + sc.dataset.sec; return; }
    const ed = t.closest('[data-edit]'); if (ed) { ST.edit = ed.dataset.edit; if (ST.edit !== 'new') ST.newsrc = ''; showPage(true); return; }
    const tr = t.closest('[data-try]'); if (tr) { const L = lang(curId()), x = ((L && L.tests) || []).find(y => y.id === tr.dataset.try); if (x) { ST.play[L.id] = x.src; delete ST.out['play:' + L.id]; } location.hash = '#/langs/' + curId() + '/play'; return; }
    const btn = t.closest('button');
    const id = curId();
    try {
      const st = t.closest('[data-starter]'); if (st) { st.disabled = true; const L = await run('starter', {i: Number(st.dataset.starter)}); setLang(L); await refreshDesk(false);
        location.hash = '#/langs/' + L.id; toast(BUSY.includes(L.status) ? `${L.number} is being designed - about a minute.` : `${L.number} ${L.name}: ${L.passed} of ${L.total} tests pass.`); return; }
      if (t.closest('[data-checknow]')) { const f = t.closest('form'); const fd = new FormData(f); btn.disabled = true;
        ST.out['chk:' + id] = await run('check', {id, grammar: S(fd.get('grammar')), start: S(fd.get('start'))}); showPage(true); return; }
      if (t.closest('[data-savetest]')) { const f = t.closest('form'); ST.newsrc = S(new FormData(f).get('src')); ST.edit = 'new'; location.hash = '#/langs/' + id + '/tests'; return; }
      const ac = t.closest('[data-accept]'); if (ac) { ac.disabled = true; await langDone(await run('test_accept', {id, tid: ac.dataset.accept}), 'Kept as the expected answer.'); return; }
      const td = t.closest('[data-tdel]'); if (td) { if (!sure(td, 'Tap again to delete')) return; td.disabled = true; await langDone(await run('test_delete', {id, tid: td.dataset.tdel}), 'Test deleted.'); return; }
      if (t.closest('[data-runall]')) { btn.disabled = true; btn.textContent = 'Running…'; const L = await run('test', {id}); await langDone(L, `${L.passed} of ${L.total} pass.`); return; }
      if (t.closest('[data-more]')) { btn.disabled = true; btn.textContent = 'Writing tests…'; const L = await run('more_tests', {id}); await langDone(L, `${L.added || 0} new test(s) - say yes to what each should give.`); return; }
      if (t.closest('[data-fuzz]')) { btn.disabled = true; btn.textContent = 'Checking…'; await run('fuzz', {id}); delete ST.out['L:' + id]; await changed('Checked.'); return; }
      const zp = t.closest('[data-zip]'); if (zp) { await getZip(zp.dataset.zip); return; }
      const rs = t.closest('[data-restore]'); if (rs) { if (!sure(rs, 'Tap again to bring it back')) return; rs.disabled = true; await langDone(await run('restore', {id, n: Number(rs.dataset.restore)}), `Version ${rs.dataset.restore} is back (as a new version).`); return; }
      const pr = t.closest('[data-prop]'); if (pr) { pr.disabled = true; await langDone(await run('proposal', {id, use: pr.dataset.prop === '1'}), pr.dataset.prop === '1' ? 'Hoola\'s change is in.' : 'Dropped.'); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to remove it for good')) return; dl.disabled = true; const r = await run('delete', {id}); dropO('L:'); location.hash = '#/langs'; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } showPage(true); }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim(), id = form.dataset.id || curId();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.dataset.was = btn.textContent; }
    try {
      if (kind === 'design') { if (btn) btn.textContent = 'Designing…'; const L = await run('design', {words: g('words'), examples: S(fd.get('examples'))}); setLang(L); await refreshDesk(false);
        location.hash = '#/langs/' + L.id; toast(`${L.number} is being designed - about a minute.`); }
      else if (kind === 'blank') { const L = await run('blank', {name: g('name')}); setLang(L); await refreshDesk(false); location.hash = '#/langs/' + L.id + '/grammar'; toast(`${L.number} started - write its grammar.`); }
      else if (kind === 'grammar') { if (btn) btn.textContent = 'Saving…'; const L = await run('save', {id, grammar: S(fd.get('grammar')), start: g('start'), note: 'Grammar changed by hand'});
        await langDone(L, L.last_run && L.last_run.grammar_ok === false ? 'Saved - the grammar still has a problem.' : `Saved: ${L.passed} of ${L.total} tests pass.`); }
      else if (kind === 'code') { if (btn) btn.textContent = 'Saving…'; const L = await run('save', {id, interpreter: S(fd.get('interpreter')), note: 'Interpreter changed by hand'});
        await langDone(L, L.last_run && L.last_run.load_error ? 'Saved - it does not load yet.' : `Saved: ${L.passed} of ${L.total} tests pass.`); }
      else if (kind === 'meta') { await langDone(await run('save', {id, name: g('name'), ext: g('ext'), purpose: g('purpose')}), 'Saved.'); }
      else if (kind === 'improve') { if (btn) btn.textContent = 'Starting…'; const L = await run('improve', {id, words: g('words')}); setLang(L); showPage(true); toast('Hoola is changing it - about a minute.'); }
      else if (kind === 'play') { if (btn) btn.textContent = 'Running…'; const src = S(fd.get('src')); ST.play[id] = src; const r = await run('run', {id, src}); ST.out['play:' + id] = {...r, src}; showPage(true); }
      else if (kind === 'test') { const L = await run('test_save', {id, test: {id: form.dataset.tid || '', name: g('name'), kind: g('kind'), src: S(fd.get('src')), expect: S(fd.get('expect'))}});
        ST.edit = ''; ST.newsrc = ''; await langDone(L, 'Saved and run.'); }
      else if (kind === 'settings') { await run('settings', {target: g('target'), limit_s: g('limit_s'), fuzz_n: g('fuzz_n')}); await changed('Saved.'); }
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
    const box = $('#lcFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/lcdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'lc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


