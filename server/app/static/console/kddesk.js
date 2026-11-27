/* KERNEL DESK - the Kernel / OS Developer's own section, like the finance desks (owner: "Kernel / OS Developer same as finance desks").
   A thin top bar, then the Kernel chat (its own conversation, kind 'kernel') beside the desk's pages: Today, Crashes, Patches,
   Kernel config, Boot & CI, Drivers, Settings. The pages call /api/kddesk/do/<part>; everything is read in code, nothing is run,
   pushed or sent. */
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

  const TABS = [['today', 'Today'], ['crashes', 'Crashes'], ['patches', 'Patches'], ['config', 'Kernel config'], ['boot', 'Boot & CI'], ['drivers', 'Drivers'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What can you read for me?', 'Why does my driver crash on unload?', 'How do I send a patch upstream?'],
    crashes: ['What does this crash mean?', 'Which line of my code is it?', 'How do I reproduce it with KASAN?'],
    patches: ['Write the commit message for this fix', 'Who should I send this patch to?', 'What is a Fixes: tag?'],
    config: ['Which options make my kernel boot in QEMU?', 'Is my kernel hardened enough?', 'Why did an option disappear?'],
    boot: ['Why does it stop at mounting root?', 'What does error -517 mean?', 'Add my module to the boot test'],
    drivers: ['Which kind of driver do I need?', 'How do I add a device tree binding?', 'Explain this driver line by line'],
    settings: ['Which defconfig should I use?', 'What is a config fragment?', 'arm64 or x86_64 for testing?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', dkind: 'hello', dname: '', dwhat: '', dfile: '', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.kddesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.kddesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'kernel_dev', name: 'Kernel'} : null;
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
  const run = (part, a) => api('POST', '/api/kddesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/kddesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Kernel / OS Developer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="kdHire">Hire the Kernel / OS Developer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#kdHire').onclick = async () => { try { await api('POST', '/api/employees/kernel_dev/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Kernel</div><div class="sd-site" id="kdSite"></div></div>
          <span id="kdState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Kernel chat">
          <div class="sd-chathead"><div class="t"><b>Kernel chat</b><span>Paste a crash log, a patch or a .config - or drop the file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="kdFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="kdPick" multiple hidden accept=".txt,.log,.patch,.diff,.config,.mbox,.c,.h,.dts,.dtsi,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Kernel desk" id="sdTabs"></nav>
          <div id="kdPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a log or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#kdPick').click()});
    $('#kdPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.kddesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.kddesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/kddesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#kdPage').addEventListener('click', onPageClick);
    $('#kdPage').addEventListener('submit', onSubmit);
    $('#kdPage').addEventListener('change', onChange);
    $('#kdPage').addEventListener('input', onInput);
    $('#kdPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#kdState'); if (!el) return;
    const k = K();
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : k.open_crashes ? ['warn', pl(k.open_crashes, 'open crash', 'open crashes')] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#kdSite').textContent = [s.arch || 'x86_64', s.kernel ? 'Linux ' + s.kernel : '', pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {crashes: k.open_crashes || '', patches: k.patch_errors || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/kddesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#kdPage'); if (!box) return;
    const fn = {today: pToday, crashes: pCrashes, patches: pPatches, config: pConfig, boot: pBoot, drivers: pDrivers, settings: pSettings}[ST.tab] || pToday;
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
  const SST = {open: ['Open', 'warn'], fixed: ['Fixed', 'ok'], ignored: ['Ignored', '']};
  const sTag = s => tag((SST[s] || [cap(s)])[0], (SST[s] || ['', ''])[1]);
  const pre = (t, cls) => `<pre class="kd-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = kind => (K().items || []).filter(x => !kind || x.kind === kind);
  const fr = f => f && f.fn ? `<code class="kd-fn">${esc(f.fn)}</code>${f.off ? `<span class="mut">+${esc(f.off)}/${esc(f.size)}</span>` : ''}${f.mod ? ` <span class="kd-mod">${esc(f.mod)}</span>` : ''}` : '—';
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  function pasteForm(kind, title, ph, extra) {
    if (!CAN()) return '';
    return `<section class="card"><h2 class="md-h2">${esc(title)}</h2><form data-form="add" data-kind="${esc(kind)}" class="kd-form">
      ${extra || ''}<textarea class="in mono kd-ed" name="text" rows="7" spellcheck="false" placeholder="${esc(ph)}"></textarea>
      <div class="kd-row"><label class="btn soft kd-file">Open a file<input type="file" data-fileto="text" accept=".txt,.log,.patch,.diff,.config,.mbox,text/*" hidden></label>
      <input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Read it</button></div></form></section>`;
  }
  function itemRows(list, kind) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="kd-list">${list.map(x => {
      const b = x.brief || {}, kind_ = kind || x.kind;
      const line = kind_ === 'patch' ? `${pl(b.errors || 0, 'error')}, ${pl(b.warnings || 0, 'warning')} · ${pl(b.files || 0, 'file')}` :
        kind_ === 'config' ? `${pl(b.wrong || 0, 'option')} to change, ${num(b.absent || 0)} not in the file · ${esc(b.arch || '')}` :
        kind_ === 'boot' ? (b.passed ? 'Booted, marker printed' : 'Did not pass: ' + (b.furthest || '')) + (b.errors ? ` · ${pl(b.errors, 'problem')}` : '') :
        `${b.label || ''}${b.fn ? ' in ' + b.fn + '()' : ''}`;
      return `<button type="button" class="kd-item" data-open="${esc(kind_)}/${esc(x.id)}"><span class="cs-dot ${b.bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(line)} · ${esc(ago(x.created_at))}</span></span>${sTag(x.status)}</button>`;
    }).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="kd-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(ago(d.created_at))}${d.seen > 1 ? ` · seen ${esc(d.seen)} times` : ''}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note kd-warn">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="kd-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark fixed</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(kind, id, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(kind === 'crash' ? 'crashes' : kind === 'patch' ? 'patches' : kind)}">Back</button></div></section>`;
    return draw(d);
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, bo = k.boots || {};
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      `<div class="k${k.open_crashes ? ' low bad' : ''}"><div class="l">Open crash groups</div><div class="v">${esc(num(k.open_crashes || 0))}</div><div class="s">${esc(pl(c.crash || 0, 'crash log'))} read</div></div>`,
      `<div class="k${k.patch_errors ? ' low bad' : ''}"><div class="l">Patches with errors</div><div class="v">${esc(num(k.patch_errors || 0))}</div><div class="s">${esc(pl(c.patch || 0, 'patch', 'patches'))} checked</div></div>`,
      `<div class="k"><div class="l">Boot tests passed</div><div class="v">${esc(num(bo.passed || 0))}<small> / ${esc(num(bo.total || 0))}</small></div><div class="s">${k.last_boot ? 'last ' + esc(ago(k.last_boot.created_at)) : 'none yet'}</div></div>`,
      `<div class="k"><div class="l">Your setup</div><div class="v kd-sm">${esc(st_().arch || 'x86_64')}</div><div class="s">${esc(st_().kernel ? 'kernel ' + st_().kernel : 'kernel not set')} · ${esc(st_().defconfig || 'defconfig')}</div></div>`];
    const gs = (k.groups || []).slice(0, 6);
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><div class="md-acts" style="margin:0 0 10px"><h2 class="md-h2" style="margin:0">Crash groups</h2><button class="btn soft sm" type="button" data-go="crashes">Read a crash log</button></div>
        ${gs.length ? groupRows(gs) : empty('No crashes read yet. Paste a log from dmesg, journalctl -k or a serial console.')}</section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8), '')}</section>`;
  }
  function groupRows(gs) {
    return `<table class="tb kd-groups"><thead><tr><th>What</th><th>Where</th><th class="r">Times</th><th class="hide-sm">Kernels</th><th class="hide-sm">Last</th><th></th></tr></thead><tbody>${gs.map(g =>
      `<tr data-open="crash/${esc(g.latest_id)}" class="kd-tr"><td><b>${esc(g.label)}</b></td><td>${g.fn ? `<code class="kd-fn">${esc(g.fn)}</code>` : '—'}${g.mod ? ` <span class="kd-mod">${esc(g.mod)}</span>` : ''}</td><td class="r">${esc(g.count)}</td><td class="hide-sm">${esc((g.kernels || []).slice(0, 2).join(', ') || '—')}</td><td class="hide-sm nw">${esc(ago(g.last))}</td><td class="r">${sTag(g.status)}</td></tr>`).join('')}</tbody></table>`;
  }

  /* ---------------------------------------------------------------- crashes */
  function pCrashes() {
    if (ST.arg) return one('crash', ST.arg, pCrash);
    const gs = K().groups || [];
    return `<div><h1 class="sd-h">Crashes</h1><p class="lead">Kernel crash logs read in code: the kind, where it stopped, what the evidence points at and what to run next in your tree.</p></div>${ro()}
      ${pasteForm('crash', 'Read a crash log', '[  123.456] BUG: kernel NULL pointer dereference, address: 0000000000000018\n[  123.456] Oops: 0000 [#1] PREEMPT SMP PTI\n...  (from dmesg, journalctl -k or a serial console - from the first BUG / cut here line to ---[ end trace)')}
      <section class="card"><h2 class="md-h2">Grouped by signature</h2><p class="cs-note" style="margin-top:0">The same kind of crash stopping in the same functions is one bug, however many times it happened.</p>${gs.length ? groupRows(gs) : empty('Nothing yet.')}</section>`;
  }
  function pCrash(d) {
    const r = d.result || {}, p = r.parsed || {}, e = r.explain || {};
    if (!p.kind) return `${head(d, 'crashes')}<section class="card"><p style="margin:0">${esc(e.summary || 'No crash found.')}</p></section><details class="card"><summary>The text</summary>${pre(d.text)}</details>`;
    const k = p.kasan || {};
    const wh = e.where && e.where.fn ? e.where : (p.stopped || {});
    const me = wh.fn || '';
    return `${head(d, 'crashes')}
      <section class="card kd-sum"><p class="kd-big">${esc(e.summary)}</p>
        <div class="kd-facts"><div><span>Kind</span><b>${esc(p.label)}${p.detail ? ' · ' + esc(p.detail) : ''}</b></div><div><span>${p.stopped && p.stopped.fn === wh.fn ? 'Stopped in' : 'In your code'}</span><b>${fr(wh)}</b></div>
        ${p.lr && p.lr.fn ? `<div><span>Called from</span><b>${fr(p.lr)}</b></div>` : ''}${p.address ? `<div><span>Address</span><b><code>${esc(p.address)}</code></b></div>` : ''}
        ${p.file_line ? `<div><span>Source</span><b><code>${esc(p.file_line)}</code></b></div>` : ''}<div><span>Kernel</span><b>${esc(p.kernel || '—')}</b></div>
        <div><span>Task</span><b>${p.comm ? esc(p.comm) + ' · PID ' + esc(p.pid) : '—'}${p.cpu ? ' · CPU ' + esc(p.cpu) : ''}</b></div>${p.hardware ? `<div><span>Machine</span><b>${esc(p.hardware)}</b></div>` : ''}</div></section>
      <section class="card"><h2 class="md-h2">What the evidence points at</h2><ul class="kd-points">${(e.points || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
        ${p.poison ? `<p class="kd-poison"><b>Poison value:</b> ${esc(p.poison)}</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Next, in your tree</h2>${(e.commands || []).map(c => `<div class="kd-cmd"><code>${esc(c)}</code>${copyBtn(c)}</div>`).join('')}</section>
      <section class="card"><h2 class="md-h2">Call trace</h2>${(p.trace || []).length ? `<ol class="kd-trace">${p.trace.map(f => `<li class="${f.unsure ? 'unsure' : ''}${f.fn === me ? ' me' : ''}">${fr(f)}${f.unsure ? '<span class="mut"> · not reliable (?)</span>' : ''}</li>`).join('')}</ol>` : empty('No call trace in the log.')}</section>
      ${k.freed || k.allocated ? `<section class="card"><h2 class="md-h2">The object (KASAN)</h2><p style="margin:0 0 10px">${k.access ? `${esc(cap(k.access))} of ${esc(k.size)} bytes at <code>${esc(k.addr)}</code>` : ''}${k.cache ? ` in a ${esc(k.object_size)}-byte object from ${esc(k.cache)}` : ''}.</p>
        <div class="kd-two">${['allocated', 'freed'].map(n => k[n] ? `<div><div class="kd-lab">${n === 'allocated' ? 'Allocated in' : 'Freed in'}</div><ol class="kd-trace sm">${k[n].map(f => `<li>${fr(f)}</li>`).join('')}</ol></div>` : '').join('')}</div></section>` : ''}
      ${(p.lockdep || []).length ? `<section class="card"><h2 class="md-h2">The locks (lockdep)</h2>${pre(p.lockdep.join('\n'))}</section>` : ''}
      ${p.oom && p.oom.name ? `<section class="card"><h2 class="md-h2">Out of memory</h2><p style="margin:0">Killed ${esc(p.oom.name)} (PID ${esc(p.oom.pid)}), using ${esc(num(Math.round(p.oom.rss_kb / 1024)))} MB${p.oom.order !== undefined ? ` · the request was order ${esc(p.oom.order)} (${esc(p.oom.gfp || '')})` : ''}.</p></section>` : ''}
      ${(p.taint || []).length || (p.modules || []).length ? `<section class="card"><h2 class="md-h2">Taint and modules</h2>
        ${(p.taint || []).map(t => `<div class="cs-row"><span class="kd-flag">${esc(t.flag)}</span><span style="flex:1">${esc(cap(t.means))}</span></div>`).join('') || '<p class="mut" style="margin:0 0 8px">Not tainted.</p>'}
        ${(p.modules || []).length ? `<div class="kd-mods">${p.modules.map(m => `<code class="${(p.out_of_tree || []).includes(m) ? 'oot' : ''}">${esc(m)}</code>`).join('')}</div><p class="cs-note">Highlighted: out-of-tree modules.</p>` : ''}</section>` : ''}
      ${(d.same || []).length ? `<section class="card"><h2 class="md-h2">The same crash, other times</h2>${itemRows(d.same, 'crash')}</section>` : ''}
      <details class="card" data-key="raw:${esc(d.id)}"${ST.open.has('raw:' + d.id) ? ' open' : ''}><summary><b>The log</b> <span class="mut">${esc(pl(d.text.split('\n').length, 'line'))}</span></summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- patches */
  function pPatches() {
    if (ST.arg) return one('patch', ST.arg, pPatch);
    return `<div><h1 class="sd-h">Patches</h1><p class="lead">A patch checked against the kernel's rules before you send it: the subject, Signed-off-by, Fixes:, the licence line and the coding style.</p></div>${ro()}
      ${pasteForm('patch', 'Check a patch', 'git format-patch -1 output (From:, Subject: [PATCH] subsystem: summary, the message, Signed-off-by:, the diff)')}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('patch'), 'patch')}</section>`;
  }
  function pPatch(d) {
    const r = d.result || {}, c = r.counts || {}, s = r.stat || {};
    const SV = {error: ['Error', 'bad'], warning: ['Warning', 'warn'], check: ['Check', '']};
    return `${head(d, 'patches')}
      <section class="cs-hero"><div class="top">
        <div class="k${c.error ? ' low bad' : ''}"><div class="l">Errors</div><div class="v">${esc(c.error || 0)}</div><div class="s">${c.error ? 'fix before sending' : 'none'}</div></div>
        <div class="k"><div class="l">Warnings</div><div class="v">${esc(c.warning || 0)}</div><div class="s">maintainers will ask</div></div>
        <div class="k"><div class="l">Checks</div><div class="v">${esc(c.check || 0)}</div><div class="s">style suggestions</div></div>
        <div class="k"><div class="l">Change</div><div class="v kd-sm">${esc(pl(s.files || 0, 'file'))}</div><div class="s"><span class="kd-add">+${esc(s.plus || 0)}</span> <span class="kd-del">-${esc(s.minus || 0)}</span></div></div></div></section>
      <section class="card"><div class="kd-subj">${r.tag ? `<span class="kd-mod">${esc(r.tag)}</span>` : ''}<b>${esc(r.summary || r.subject || '(no subject)')}</b></div>${r.author ? `<p class="mut" style="margin:6px 0 0">${esc(r.author)}</p>` : ''}
        ${(r.files || []).length ? `<div class="kd-files">${r.files.map(f => `<div><code>${esc(f.file)}</code>${f.new ? tag('new', 'ok') : f.deleted ? tag('deleted', 'bad') : ''}<span><span class="kd-add">+${esc(f.plus)}</span> <span class="kd-del">-${esc(f.minus)}</span></span></div>`).join('')}</div>` : ''}</section>
      <section class="card"><h2 class="md-h2">What to fix</h2>${(r.issues || []).length ? r.issues.map(i => `<div class="kd-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><b>${esc(i.say)}</b>${i.file ? `<span class="mut"> · ${esc(i.file)}${i.line ? ':' + esc(i.line) : ''}</span>` : ''}${i.code ? `<code class="kd-code">${esc(i.code.replace(/\t/g, '→   '))}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these rules.</span></div>'}</section>
      <section class="card"><h2 class="md-h2">Before you send it</h2><p class="cs-note" style="margin-top:0">These rules are Hoola's own reading of Documentation/process. Run the kernel's tools in your tree too:</p>${(r.next || []).map(x => `<div class="kd-cmd"><code>${esc(x)}</code>${copyBtn(x)}</div>`).join('')}</section>
      <details class="card" data-key="raw:${esc(d.id)}"${ST.open.has('raw:' + d.id) ? ' open' : ''}><summary><b>The patch</b></summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- config */
  function pConfig() {
    if (ST.arg) return one('config', ST.arg, pConf);
    const prof = (K().health || {}).profiles || [];
    const extra = `<fieldset class="kd-prof"><legend>Check it for</legend>${prof.map((p, i) => `<label class="ar-chk"><input type="checkbox" name="profiles" value="${esc(p.key)}"${i < 2 ? ' checked' : ''}> ${esc(p.name)} <span class="mut">(${esc(p.count)})</span></label>`).join('')}</fieldset>`;
    return `<div><h1 class="sd-h">Kernel config</h1><p class="lead">A .config checked for hardening, booting in QEMU, debugging or a container host - and a fragment to merge for what is missing.</p></div>${ro()}
      ${pasteForm('config', 'Check a .config', 'The whole .config file (CONFIG_...=y and # CONFIG_... is not set lines)', extra + `<details class="kd-cmp"><summary>Compare with an older .config (optional)</summary><textarea class="in mono" name="compare" rows="4" spellcheck="false" placeholder="The older .config"></textarea></details>`)}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('config'), 'config')}</section>`;
  }
  function pConf(d) {
    const r = d.result || {}, df = r.diff || null;
    const ST2 = {ok: ['Right', 'ok'], wrong: ['Change it', 'bad'], absent: ['Not in the file', 'warn']};
    return `${head(d, 'config')}
      <section class="card"><p style="margin:0">${esc(num(r.options))} options · ${esc(r.arch || 'architecture not found')}${r.version ? ' · Linux ' + esc(r.version) : ''}</p><p class="cs-note">${esc(r.note || '')}</p></section>
      ${(r.results || []).map(x => `<section class="card"><div class="md-acts" style="margin:0 0 6px"><h2 class="md-h2" style="margin:0">${esc(x.name)}</h2><span class="mut" style="font-size:13px">${esc(x.ok)} right · ${esc(x.wrong)} to change · ${esc(x.absent)} not in the file</span></div>
        <p class="cs-note" style="margin-top:0">Source: ${esc(x.source)}</p>
        <table class="tb kd-cfg"><thead><tr><th>Option</th><th>Want</th><th>Have</th><th class="hide-sm">Why</th><th></th></tr></thead><tbody>${x.rows.slice().sort((a, b) => ({wrong: 0, absent: 1, ok: 2}[a.status] - {wrong: 0, absent: 1, ok: 2}[b.status])).map(y => `<tr><td><code>${esc(y.name)}</code></td><td>${esc(y.want)}</td><td>${esc(y.have)}</td><td class="hide-sm mut">${esc(y.why)}</td><td class="r">${tag(ST2[y.status][0], ST2[y.status][1])}</td></tr>`).join('')}</tbody></table></section>`).join('')}
      ${r.fragment ? `<section class="card"><div class="md-acts" style="margin:0 0 8px"><h2 class="md-h2" style="margin:0">A fragment to merge</h2>${copyBtn(r.fragment, 'Copy the fragment')}</div>${pre(r.fragment)}<div class="kd-cmd"><code>./scripts/kconfig/merge_config.sh -m .config fragment.config && make olddefconfig</code></div></section>` : ''}
      ${df && df.ok ? `<section class="card"><h2 class="md-h2">Compared with the older .config</h2><p style="margin:0 0 10px"><span class="kd-add">${esc(df.counts.added)} added</span> · <span class="kd-del">${esc(df.counts.removed)} removed</span> · ${esc(df.counts.changed)} changed</p>
        ${df.changed.length ? `<table class="tb"><thead><tr><th>Changed</th><th>Was</th><th>Now</th></tr></thead><tbody>${df.changed.slice(0, 80).map(y => `<tr><td><code>${esc(y.name)}</code></td><td>${esc(y.from)}</td><td>${esc(y.to)}</td></tr>`).join('')}</tbody></table>` : ''}
        ${df.added.length ? `<details class="kd-cmp"><summary>Added (${esc(df.added.length)})</summary>${pre(df.added.map(y => y.name + '=' + y.value).join('\n'))}</details>` : ''}${df.removed.length ? `<details class="kd-cmp"><summary>Removed (${esc(df.removed.length)})</summary>${pre(df.removed.map(y => y.name + '=' + y.value).join('\n'))}</details>` : ''}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- boot & CI */
  function pBoot() {
    if (ST.arg) return one('boot', ST.arg, pBootOne);
    const s = st_(), wf = ST.out.wf;
    return `<div><h1 class="sd-h">Boot &amp; CI</h1><p class="lead">A GitHub Actions file that builds your kernel and boots it in QEMU on every push - and the serial log read stage by stage.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">The boot test for your CI</h2><form data-form="wf" class="kd-row wrap">
        <label class="ins-lab">Architecture<select class="in" name="arch">${(K().health || {}).arches.map(a => `<option${a === s.arch ? ' selected' : ''}>${esc(a)}</option>`).join('')}</select></label>
        <label class="ins-lab" style="flex:1">Your module's folder (optional)<input class="in" name="module_dir" maxlength="120" value="${esc(s.module_dir || '')}" placeholder="drivers/hwmon/my_sensor"></label>
        <button class="btn" type="submit">Write it</button></form>
        ${wf ? (wf.error ? err(wf) : `<div class="kd-steps">${wf.steps.map((x, i) => `<span><b>${i + 1}</b>${esc(x)}</span>`).join('')}</div>
          <div class="md-acts" style="margin:12px 0 6px"><span class="mut" style="font-size:13px">Save it as <code>${esc(wf.path)}</code> in your kernel repository.</span><span>${copyBtn(wf.yaml, 'Copy')} <button class="btn soft sm" type="button" data-dlwf="1">Download</button></span></div>${pre(wf.yaml, 'yml')}<p class="cs-note">${esc(wf.note)}</p>`) : ''}</section>
      ${pasteForm('boot', 'Read a boot log', 'The serial log from the CI run (the serial-log artifact) or dmesg from a board')}
      <section class="card"><h2 class="md-h2">Boot logs read</h2>${itemRows(items('boot'), 'boot')}</section>`;
  }
  function pBootOne(d) {
    const r = d.result || {};
    const T = r.last_s || 1;
    return `${head(d, 'boot')}
      <section class="card kd-sum ${r.passed ? 'okv' : 'badv'}"><p class="kd-big">${esc(r.verdict)}</p><div class="kd-facts"><div><span>Kernel</span><b>${esc(r.kernel || '—')}</b></div>
        <div><span>To first program</span><b>${r.init_s != null ? esc(num(r.init_s)) + ' s' : '—'}</b></div><div><span>Problems</span><b>${esc(r.bad || 0)} serious, ${esc(r.warn || 0)} other</b></div>${r.cmdline ? `<div class="wide"><span>Command line</span><b><code>${esc(r.cmdline)}</code></b></div>` : ''}</div></section>
      <section class="card"><h2 class="md-h2">How far it got</h2><ol class="kd-stages">${(r.stages || []).map(s => `<li><span class="dot"></span><b>${esc(s.name)}</b><span class="mut">${s.t != null ? esc(num(s.t)) + ' s' : ''} · line ${esc(s.line)}</span><i style="width:${Math.max(2, Math.min(100, (s.t || 0) / T * 100)).toFixed(1)}%"></i></li>`).join('')}</ol>
        ${!r.passed ? `<p class="cs-neg" style="margin:10px 0 0">Not reached: the test marker <code>${esc(r.marker)}</code>.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Problems</h2>${(r.errors || []).length ? r.errors.map(e => `<div class="kd-issue"><span>${tag(e.sev === 'bad' ? 'Serious' : 'Check', e.sev === 'bad' ? 'bad' : 'warn')}</span><div><b>${esc(e.say)}</b><span class="mut"> · line ${esc(e.line)}${e.t != null ? ' · ' + esc(num(e.t)) + ' s' : ''}</span><code class="kd-code">${esc(e.raw)}</code></div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>No problems found.</span></div>'}</section>
      <details class="card" data-key="raw:${esc(d.id)}"${ST.open.has('raw:' + d.id) ? ' open' : ''}><summary><b>The log</b> <span class="mut">${esc(pl(r.lines || 0, 'line'))}</span></summary>${pre(d.text)}</details>`;
  }

  /* ---------------------------------------------------------------- drivers */
  function pDrivers() {
    const kinds = (K().health || {}).kinds || {}, dv = ST.out.drv, sel = ST.dkind || 'hello';
    const f = dv && !dv.error ? (dv.files || []) : [];
    const tab = ST.dfile && f.some(x => x.name === ST.dfile) ? ST.dfile : (f[0] || {}).name;
    return `<div><h1 class="sd-h">Drivers</h1><p class="lead">A starter driver from a tested template: the C file, its Makefile, a Kconfig entry and a device tree node where it needs one.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">What kind</h2><div class="kd-kinds">${Object.entries(kinds).map(([k2, s]) => `<button type="button" class="kd-kind" data-dkind="${esc(k2)}" aria-pressed="${k2 === sel}"><b>${esc({hello: 'Module', misc: 'Character device', platform: 'Platform driver', i2c: 'I2C driver'}[k2] || k2)}</b><span>${esc(s)}</span></button>`).join('')}</div>
        <form data-form="driver" class="kd-row wrap" style="margin-top:12px"><input type="hidden" name="kind" value="${esc(sel)}">
          <label class="ins-lab" style="flex:1">Name<input class="in" name="name" maxlength="24" required value="${esc(ST.dname || '')}" placeholder="my_sensor"></label>
          <label class="ins-lab" style="flex:2">What it is for (optional)<input class="in" name="what" maxlength="120" value="${esc(ST.dwhat || '')}" placeholder="Temperature sensor on the main board"></label>
          <button class="btn" type="submit">Make it</button></form></section>
      ${dv ? (dv.error ? `<section class="card">${err(dv)}</section>` : `<section class="card"><div class="md-acts" style="margin:0 0 10px"><h2 class="md-h2" style="margin:0">${esc(dv.name)}</h2><button class="btn" type="button" data-dzip="1">Download the zip</button></div>
        <nav class="kd-tabs">${f.map(x => `<button type="button" data-dfile="${esc(x.name)}" aria-current="${x.name === tab}">${esc(x.name)}</button>`).join('')}</nav>
        ${pre((f.find(x => x.name === tab) || {}).text || '', 'code')}
        <p class="cs-note">${(dv.style || []).length ? `Style: ${esc(pl(dv.style.length, 'note'))} - ${esc(dv.style[0].say)}` : 'It passes this desk\'s style checks.'} Not compiled on Hoola's server (no kernel headers here): build it in your CI - the Boot &amp; CI page can build it and load it in QEMU.</p></section>`) : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    const fld = (n, l, ph, extra) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(s[n] || '')}" placeholder="${esc(ph)}" ${extra || ''}></label>`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your kernel setup - used by the boot-test workflow, the patch checks and the driver starters.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="kd-grid">
        <label class="ins-lab">Architecture<select class="in" name="arch">${((K().health || {}).arches || []).map(a => `<option${a === s.arch ? ' selected' : ''}>${esc(a)}</option>`).join('')}</select></label>
        ${fld('kernel', 'Kernel version', '6.12')}${fld('defconfig', 'defconfig', 'defconfig')}${fld('fragment', 'Config fragment in your repository', '.hoola/kernel.config')}
        ${fld('module_dir', 'Your module folder (optional)', 'drivers/hwmon/my_sensor')}${fld('branch', 'Branch to test', 'main')}
        ${fld('max_line', 'Longest code line', '100', 'type="number" min="80" max="120"')}${fld('author', 'Author line for drivers', 'Your Name <you@example.com>')}
        ${fld('vendor', 'Device tree vendor prefix', 'acme')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">The config profiles</h2>${((K().health || {}).profiles || []).map(p => `<div class="cs-row"><span class="cs-dot ok"></span><span style="flex:1"><b>${esc(p.name)}</b> · ${esc(p.count)} options<br><span class="mut" style="font-size:13px">${esc(p.source)}</span></span></div>`).join('')}</section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs your kernel or your code on Hoola's server.</li><li>Pushes to your repository or sends a patch to a mailing list - you do.</li><li>Says a cause the log does not show.</li><li>Follows anything written inside a log, a patch or a config: they are data.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  const ROUTE = {crash: 'crashes', patch: 'patches', config: 'config', boot: 'boot'};
  function saveBlob(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
  async function getZip() {
    try {
      const q = new URLSearchParams({kind: ST.dkind || 'hello', name: ST.dname || 'my_driver', what: ST.dwhat || ''});
      const r = await fetch('/api/kddesk/driver.zip?' + q, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = `Could not download (${r.status})`; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
      saveBlob((ST.dname || 'my_driver') + '.zip', await r.blob());
    } catch (e) { toast(e.message, true); }
  }
  function onInput() {}
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { const [k, id] = op.dataset.open.split('/'); delete ST.out['i:' + id]; location.hash = '#/' + (ROUTE[k] || 'crashes') + '/' + id; return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast('Copied.'); } catch { toast('Copy did not work here - select the text instead.', true); } return; }
    const dk = t.closest('[data-dkind]'); if (dk) { ST.dkind = dk.dataset.dkind; delete ST.out.drv; showPage(true); return; }
    const df = t.closest('[data-dfile]'); if (df) { ST.dfile = df.dataset.dfile; showPage(true); return; }
    if (t.closest('[data-dzip]')) { await getZip(); return; }
    if (t.closest('[data-dlwf]')) { const w = ST.out.wf; if (w && w.yaml) saveBlob('hoola-boot.yml', new Blob([w.yaml], {type: 'text/yaml'})); return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked fixed - Hoola tells you if it comes back.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 600000) { toast('That file is larger than 600 KB - keep the part around the problem.', true); el.value = ''; return; }
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
    try {
      if (kind === 'add') { const k = form.dataset.kind; if (btn) btn.textContent = 'Reading…';
        const d = await run('add', {kind: k, text: S(fd.get('text')), title: g('title'), profiles: fd.getAll('profiles'), compare: S(fd.get('compare'))});
        ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} read.`); }
      else if (kind === 'wf') { ST.out.wf = await run('workflow', {arch: g('arch'), module_dir: g('module_dir')}); showPage(true); }
      else if (kind === 'driver') { ST.dkind = g('kind') || 'hello'; ST.dname = g('name'); ST.dwhat = g('what'); ST.dfile = '';
        ST.out.drv = await run('driver', {kind: ST.dkind, name: ST.dname, what: ST.dwhat}); ST.dname = ST.out.drv.name || ST.dname; showPage(true); }
      else if (kind === 'settings') { const a = {}; ['arch', 'kernel', 'defconfig', 'fragment', 'module_dir', 'branch', 'max_line', 'author', 'vendor'].forEach(n => { a[n] = g(n); });
        await run('settings', a); delete ST.out.wf; await changed('Saved.'); }
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
    const box = $('#kdFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/kddesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'kd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


