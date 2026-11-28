/* VIRTUALIZATION DESK - the Virtualization / Hypervisor Engineer's own section, like the finance desks (owner: "Virtualization /
   Hypervisor Engineer same as finance desks"). A thin top bar, then the Virtualization chat (its own conversation, kind 'virt') beside
   the desk's pages: Today, Containers (Pod Security levels + hardened lines), Seccomp (check a profile, make one from a trace), VMs
   (libvirt XML), Capacity (hosts and VMs, CPU flags), CI check, Settings. The pages call /api/hvdesk/do/<part>; nothing changes on
   her hosts. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['containers', 'Containers'], ['seccomp', 'Seccomp'], ['vms', 'VMs'], ['capacity', 'Capacity'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start hardening my containers?', 'Containers or VMs for this workload?', 'gVisor, Kata or plain runc?'],
    containers: ['Why does my container need root?', 'How do I run nginx as non-root?', 'What does readOnlyRootFilesystem break?'],
    seccomp: ['Should I block io_uring?', 'How do I find what syscalls my app makes?', 'What is the RuntimeDefault profile?'],
    vms: ['cache=none or writeback?', 'host-passthrough or host-model?', 'Do I need huge pages?'],
    capacity: ['How much CPU overcommit is safe?', 'How do I plan for N+1?', 'Why does a VM span NUMA nodes?'],
    ci: ['How do I test the seccomp profile in CI?', 'Where do I put the workflow?', 'Can CI catch a container that needs root?'],
    settings: ['Restricted or baseline?', 'What user id should I use?', 'How much RAM should the host keep?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', cap: 'plan', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.hvdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.hvdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'virt', name: 'Virtualization'} : null;
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
  const run = (part, a) => api('POST', '/api/hvdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/hvdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Virtualization / Hypervisor Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="hvHire">Hire the Virtualization / Hypervisor Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#hvHire').onclick = async () => { try { await api('POST', '/api/employees/hypervisor_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Virtualization</div><div class="sd-site" id="hvSite"></div></div>
          <span id="hvState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Virtualization chat">
          <div class="sd-chathead"><div class="t"><b>Virtualization chat</b><span>Paste a config, a profile, a VM\'s XML or host sizes - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="hvFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="hvPick" multiple hidden accept=".txt,.log,.json,.csv,.yml,.yaml,.xml,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Virtualization desk" id="sdTabs"></nav>
          <div id="hvPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a config or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#hvPick').click()});
    $('#hvPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.hvdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.hvdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/hvdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#hvPage').addEventListener('click', onPageClick);
    $('#hvPage').addEventListener('submit', onSubmit);
    $('#hvPage').addEventListener('change', onChange);
    $('#hvPage').addEventListener('input', onInput);
    $('#hvPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#hvState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#hvSite').textContent = [s.arch, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/hvdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#hvPage'); if (!box) return;
    const fn = {today: pToday, containers: pContainers, seccomp: pSeccomp, vms: pVms, capacity: pCapacity, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="hvk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const pct = (v, d = 0) => { if (v === null || v === undefined) return '—'; let t = (Number(v) * 100).toFixed(d); if (t.includes('.')) t = t.replace(/\.?0+$/, ''); return t + '%'; };
  const KN = {container: 'Container config', seccomp: 'Seccomp profile', trace: 'Profile from a trace', domain: 'VM', plan: 'Capacity', cpu: 'CPU flags'};
  const ROUTE = {container: 'containers', seccomp: 'seccomp', trace: 'seccomp', domain: 'vms', plan: 'capacity', cpu: 'capacity'};
  const LV = {privileged: ['Privileged', 'bad'], baseline: ['Baseline', 'warn'], restricted: ['Restricted', 'ok']};
  const lvTag = l => l ? tag((LV[l] || [cap(l)])[0], (LV[l] || ['', ''])[1]) : '';
  const FMT = {kubernetes: 'Kubernetes', compose: 'Compose', docker: 'docker run', podman: 'podman run', nerdctl: 'nerdctl run', oci: 'OCI config.json', dockerfile: 'Dockerfile'};
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'container': return b.format === 'dockerfile' ? `Dockerfile · ${pl(b.issues || 0, 'thing')} to fix` : `${FMT[b.format] || b.format} · ${b.meets ?? 0} of ${b.n ?? 0} meet ${b.target || 'restricted'} · weakest ${b.level || '—'}`;
      case 'seccomp': return `${b.mode} · ${num(b.allowed)} of ${num(b.of)} syscalls open · ${pl(b.risky || 0, 'risky one')}`;
      case 'trace': return `${num(b.allowed)} syscalls allowed from ${num(b.seen)} seen`;
      case 'domain': return `${num(b.vcpus)} vCPUs · ${b.gib === null || b.gib === undefined ? '—' : num(b.gib) + ' GiB'} · migrates: ${b.migratable || '—'}`;
      case 'plan': return `${pl(b.vms || 0, 'VM')} on ${pl(b.hosts || 0, 'host')} · ${b.survives === null || b.survives === undefined ? 'no failover check' : b.survives ? 'survives a host loss' : 'does not survive a host loss'}`;
      case 'cpu': return `${pl(b.hosts || 0, 'host')} · ${b.same ? 'identical' : 'shared level ' + (b.level || '—')}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="hvk-list">${list.map(x => `<button type="button" class="hvk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="hvk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="hvk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = (list, showLevel) => (list || []).length ? list.map(i => `<div class="hvk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${showLevel && i.level && i.level !== 'extra' ? `<span class="mut">Pod Security ${esc(i.level)}</span>` : i.area ? `<span class="mut">${esc(cap(i.area))}</span>` : ''}${i.fix ? `<code class="hvk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows) => `<label class="ins-lab wide">${esc(l)}<textarea class="in mono hvk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft hvk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="hvk-row wide">${fileBtn('text', acc || '.txt,.log,.yml,.yaml,.json,.xml,Dockerfile,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card hvk-sum ${ok ? 'okv' : 'badv'}"><p class="hvk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="hvk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad') && !((r.counts || {}).bad);
  const meter = (share, cls, label) => `<div class="hvk-bar" role="img" aria-label="${esc(label || pct(share))}"><i class="${cls || (share > 1 ? 'bad' : share > 0.85 ? 'warn' : '')}" style="width:${Math.min(100, Math.max(0, (share || 0) * 100)).toFixed(1)}%"></i></div>`;
  const ARCH = [['x86_64', 'x86_64 (Intel / AMD)'], ['aarch64', 'aarch64 (ARM)']];

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, ct = k.containers, cp = k.capacity, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Containers', ct ? lvTag(ct.level) : '—', ct ? `${ct.meets} of ${ct.n} meet ${s.target || 'restricted'} · ${ct.number}` : 'paste a config to check it', ct && ct.level === 'privileged'),
      tile('Seccomp profiles', esc(num((c.seccomp || 0) + (c.trace || 0))), 'checked or made from a trace'),
      tile('VMs checked', esc(num(k.vms || 0)), 'libvirt definitions'),
      tile('Capacity', cp ? (cp.survives === false ? 'At risk' : cp.survives ? 'Survives' : '—') : '—', cp ? `${num(cp.vms)} VMs · ${num(cp.ratio)} vCPUs per core · ${cp.number}` : 'list your hosts and VMs', cp && cp.survives === false)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} Containers must meet ${esc(s.target || 'restricted')}; ${esc(s.arch || 'x86_64')} hosts.</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="hvk-starts">
        <button type="button" class="hvk-start" data-go="containers"><b>Harden a container</b><span>Kubernetes, Compose, docker run, config.json or a Dockerfile against the Pod Security Standards</span></button>
        <button type="button" class="hvk-start" data-go="seccomp"><b>Lock down syscalls</b><span>Check a seccomp profile, or make one from what the program really calls</span></button>
        <button type="button" class="hvk-start" data-go="vms"><b>Check a VM</b><span>libvirt XML: speed, safety, Secure Boot, live migration</span></button>
        <button type="button" class="hvk-start" data-go="capacity"><b>Plan the hosts</b><span>Where every VM goes, failover, NUMA, CPU flags across hosts</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- containers */
  function pContainers() {
    if (ST.arg) return one(ST.arg, 'containers', pContainer);
    const s = st_();
    return `<div><h1 class="sd-h">Containers</h1><p class="lead">Each container against the Kubernetes Pod Security Standards - privileged, baseline, restricted - with the hardened lines to put in place.</p></div>${ro()}
      <div class="hvk-ladder" aria-label="Pod Security levels">${[['privileged', 'No limits: the container can reach the host'], ['baseline', 'Stops the known ways out: privileged, host namespaces, host paths, extra capabilities'], ['restricted', 'Hardened: non-root, no privilege escalation, all capabilities dropped, seccomp on']].map(([l, t]) => `<div class="${l}">${lvTag(l)}<span>${esc(t)}</span></div>`).join('<i aria-hidden="true">→</i>')}</div>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a config</h2><form data-form="container" class="hvk-grid">
        ${area('text', 'Kubernetes YAML (several documents are fine), a docker-compose.yml, docker / podman run lines, an OCI config.json or a Dockerfile', 'apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\nspec:\n  template:\n    spec:\n      containers:\n      - name: app\n        image: nginx:1.27', 10)}
        ${sel('target', 'Level to meet', [['restricted', 'Restricted'], ['baseline', 'Baseline']], s.target || 'restricted')}${fld('uid', 'Non-root user id for the fixes', s.uid || 10001, 'type="number" min="1" step="1"')}
        ${subRow('Check it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('container'))}</section>`;
  }
  function pContainer(d) {
    const r = d.result || {};
    if (r.format === 'dockerfile') {
      return `${head(d, 'containers')}${verdict(r, isOk(r))}
        <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
        <details class="card hvk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
    }
    const cs = r.containers || [];
    const by = {privileged: 0, baseline: 0, restricted: 0}; cs.forEach(c => { by[c.level] = (by[c.level] || 0) + 1; });
    return `${head(d, 'containers')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">By level</h2>${bars(Object.entries(by).map(([l, n]) => [LV[l][0], n, 'hvk-b ' + l]), num, 'Containers by Pod Security level')}<p class="cs-note">${esc(r.note)}</p></section>
      ${cs.map((c, i) => { const k2 = 'c:' + d.id + ':' + i, bad = c.issues.filter(x => x.sev !== 'info'), nts = c.issues.filter(x => x.sev === 'info');
        return `<details class="card hvk-ct" data-key="${esc(k2)}"${ST.open.has(k2) || cs.length === 1 ? ' open' : ''}><summary><span class="t"><b>${esc(c.name)}</b><span class="mut">${esc(c.image || 'no image named')}${c.root === true ? ' · runs as root' : c.root === null ? ' · user not set' : ''}</span></span>${lvTag(c.level)}<span class="mut hide-sm">${pl(bad.length, 'finding')}</span></summary>
          <div class="hvk-caps"><span class="mut">Capabilities it has</span>${(c.caps_effective || []).length ? c.caps_effective.map(x => `<code class="${x === 'ALL' || ['SYS_ADMIN', 'SYS_PTRACE', 'SYS_MODULE', 'NET_ADMIN', 'DAC_READ_SEARCH', 'BPF'].includes(x) ? 'bad' : ''}">${esc(x)}</code>`).join('') : '<b>none</b>'}</div>
          ${issueRows(bad, true)}${nts.length ? `<details class="hvk-notes"><summary>${pl(nts.length, 'note')}</summary>${issueRows(nts, true)}</details>` : ''}
          <div class="hvk-fix"><div class="md-acts"><b>The hardened lines</b><span>${copyBtn(c.fix)}</span></div>${pre(c.fix, 'code')}</div></details>`; }).join('')}
      <details class="card hvk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- seccomp */
  function pSeccomp() {
    if (ST.arg) return one(ST.arg, 'seccomp', d => d.kind === 'trace' ? pTrace(d) : pSec(d));
    const s = st_();
    return `<div><h1 class="sd-h">Seccomp</h1><p class="lead">Which system calls a container may make. An allow-list refuses everything else - including calls the kernel adds later.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Make a profile from a trace</h2><form data-form="trace" class="hvk-grid">
        ${area('text', 'strace output (strace -f -o trace.txt your-program), strace -c, audit SECCOMP lines (syscall=N) or syscall names', '1234 execve("/app/server", ["server"], 0x7ffd...) = 0\n1234 openat(AT_FDCWD, "/etc/app.conf", O_RDONLY) = 3\n1234 read(3, "...", 4096) = 120\n1234 epoll_wait(4, [], 64, 1000) = 0')}
        ${sel('arch', 'Architecture', ARCH, s.arch)}${sel('base', 'Add what a container needs to start', [['1', 'Yes (recommended)'], ['0', 'No - only what the trace shows']], '1')}
        ${subRow('Make the profile', '.txt,.log,.json,text/*')}</form></section>
      <section class="card"><h2 class="md-h2">Check a profile</h2><form data-form="seccomp" class="hvk-grid">
        ${area('text', 'The profile JSON (Docker / containerd / Kubernetes Localhost, or an OCI config.json with linux.seccomp)', '{\n  "defaultAction": "SCMP_ACT_ERRNO",\n  "architectures": ["SCMP_ARCH_X86_64"],\n  "syscalls": [{"names": ["read", "write"], "action": "SCMP_ACT_ALLOW"}]\n}')}
        ${sel('arch', 'Architecture', ARCH, s.arch)}${subRow('Check it', '.json,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked and made</h2>${itemRows(items('seccomp', 'trace'))}</section>`;
  }
  const riskyRows = list => (list || []).length ? `<div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Syscall</th><th>What it gives</th><th>When</th><th></th></tr></thead><tbody>${list.map(x => `<tr><td><code>${esc(x.name)}</code></td><td>${esc(x.why)}</td><td class="mut">${esc(x.when || (x.times ? pl(x.times, 'call') + ' in the trace' : ''))}</td><td class="r">${tag(SV[x.sev][0], SV[x.sev][1])}</td></tr>`).join('')}</tbody></table></div>` : empty('None of the risky calls are open.');
  function pSec(d) {
    const r = d.result || {}, share = r.of ? r.allowed / r.of : 0;
    return `${head(d, 'seccomp')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">Open syscalls</h2><div class="hvk-big2"><b>${esc(num(r.allowed))}</b><span>of ${esc(num(r.of))} ${esc(r.arch)} syscalls · ${esc(r.mode)} · default ${esc(r.default)}</span></div>${meter(share, share > 0.6 ? 'bad' : share > 0.35 ? 'warn' : 'ok', pct(share) + ' open')}</section>
      <section class="card"><h2 class="md-h2">Risky calls</h2>${riskyRows(r.risky)}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      ${(r.conditional || []).length ? `<section class="card"><h2 class="md-h2">Allowed only sometimes</h2><div class="hvk-chips">${r.conditional.map(x => `<span title="${esc(x.when)}"><code>${esc(x.name)}</code> <em>${esc(x.when)}</em></span>`).join('')}</div></section>` : ''}
      <details class="card hvk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }
  function pTrace(d) {
    const r = d.result || {};
    return `${head(d, 'seccomp')}${verdict(r, true)}
      <section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">The profile</h2><span>${copyBtn(r.profile)} <button class="btn soft sm" type="button" data-dlprof="1">Download ${esc(r.file)}</button></span></div>
        ${pre(r.profile, 'code')}<p class="cs-note">${esc(r.note)}</p>
        <p class="cs-note">Docker: <code>--security-opt seccomp=${esc(r.file)}</code> · Kubernetes: put it in the kubelet's seccomp folder and use <code>seccompProfile: {type: Localhost, localhostProfile: ${esc(r.file)}}</code></p></section>
      ${(r.risky || []).length ? `<section class="card"><h2 class="md-h2">Risky calls it made</h2>${riskyRows(r.risky)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Most called</h2>${bars((r.top || []).slice(0, 15).map(([n, c]) => [n, c, 'hvk-b']), num, 'Syscalls by count')}
        ${(r.added || []).length ? `<p class="cs-note">Added so a container can start: ${esc(r.added.join(', '))}.</p>` : ''}${(r.unknown || []).length ? `<p class="cs-note">Left out (not ${esc(r.arch)} syscalls): ${esc(r.unknown.join(', '))}.</p>` : ''}</section>
      <details class="card hvk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- VMs */
  function pVms() {
    if (ST.arg) return one(ST.arg, 'vms', pDomain);
    return `<div><h1 class="sd-h">Virtual machines</h1><p class="lead">A libvirt definition read for speed, safety and live migration - and the XML to change.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a VM</h2><form data-form="domain" class="hvk-grid">
        ${area('text', 'The VM\'s XML: virsh dumpxml <name> (or the file in /etc/libvirt/qemu/)', "<domain type='kvm'>\n  <name>db1</name>\n  <memory unit='GiB'>16</memory>\n  <vcpu>4</vcpu>\n  ...\n</domain>", 10)}
        ${subRow('Check it', '.xml,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('domain'))}</section>`;
  }
  function pDomain(d) {
    const r = d.result || {}, iss = r.issues || [];
    const A = [['safety', 'Safety'], ['speed', 'Speed'], ['migration', 'Live migration'], ['config', 'Configuration'], ['space', 'Disk space']];
    const facts = [['vCPUs', num(r.vcpus)], ['Memory', r.memory_gib === null || r.memory_gib === undefined ? '—' : num(r.memory_gib) + ' GiB'], ['CPU', r.cpu_mode + (r.cpu_model ? ' · ' + r.cpu_model : '')],
      ['Hypervisor', r.hypervisor + (r.machine ? ' · ' + r.machine : '')], ['Firmware', r.firmware + (r.secure_boot ? ' · Secure Boot' : '') + (r.tpm ? ' · TPM' : '')],
      ['Huge pages', r.hugepages ? 'yes' : 'no'], ['Pinned', r.pinned ? 'yes' : 'no'], ['Live migration', r.migratable]];
    return `${head(d, 'vms')}${verdict(r, isOk(r))}
      <section class="card"><dl class="ar-facts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>${(r.why_not || []).length ? `<p class="cs-note">Live migration: ${esc(r.why_not.join('; '))}.</p>` : ''}</section>
      ${A.map(([a, t]) => { const l = iss.filter(i => i.area === a); return l.length ? `<section class="card"><h2 class="md-h2">${esc(t)}</h2>${issueRows(l)}</section>` : ''; }).join('')}
      ${(r.disks || []).length ? `<section class="card"><h2 class="md-h2">Disks</h2><div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Device</th><th>Bus</th><th>Format</th><th>Cache</th><th>I/O</th><th>Source</th></tr></thead><tbody>${r.disks.map(x => `<tr><td><code>${esc(x.dev)}</code>${x.device !== 'disk' ? ' <span class="mut">' + esc(x.device) + '</span>' : ''}</td><td>${esc(x.bus || '—')}</td><td>${esc(x.format || '—')}</td><td>${esc(x.cache)}</td><td>${esc(x.io || '—')}</td><td class="mut hvk-path">${esc(x.source || '—')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${(r.nics || []).length ? `<section class="card"><h2 class="md-h2">Network cards</h2><div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Type</th><th>Model</th><th class="r">Queues</th><th>MAC</th></tr></thead><tbody>${r.nics.map(x => `<tr><td>${esc(x.type)}</td><td>${esc(x.model)}</td><td class="r">${esc(x.queues)}</td><td class="mut"><code>${esc(x.mac || '—')}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <p class="cs-note">${esc(r.note)}</p>
      <details class="card hvk-raw"><summary>The XML you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- capacity */
  function pCapacity() {
    if (ST.arg) return one(ST.arg, 'capacity', d => d.kind === 'cpu' ? pCpu(d) : pPlan(d));
    const s = st_(), w = ST.cap === 'cpu' ? 'cpu' : 'plan';
    const forms = {
      plan: `<form data-form="plan" class="hvk-grid">${area('text', 'One line per host and per VM. host, name, physical cores, RAM GiB[, NUMA nodes] - vm, name, vCPUs, RAM GiB[, the host it is on]', 'host, node-1, 32, 256, 2\nhost, node-2, 32, 256, 2\nhost, node-3, 32, 256, 2\nvm, db-primary, 8, 64\nvm, web-1, 4, 16\nvm, web-2, 4, 16', 9)}
        ${fld('vcpu_ratio', 'vCPUs per physical core', s.vcpu_ratio, 'type="number" min="0.1" max="32" step="any"')}${fld('ram_ratio', 'RAM overcommit (1 = none)', s.ram_ratio, 'type="number" min="0.5" max="4" step="any"')}
        ${fld('reserve_gb', 'RAM kept for each host (GiB)', s.reserve_gb, 'type="number" min="0" step="any"')}${fld('reserve_cores', 'Cores kept for each host', s.reserve_cores, 'type="number" min="0" step="any"')}
        ${sel('failures', 'Must survive losing', [[0, 'No failover check'], [1, '1 host'], [2, '2 hosts']], s.failures)}${subRow('Work it out', '.txt,.csv,text/*')}</form>`,
      cpu: `<form data-form="cpu" class="hvk-grid">${area('text', 'Each host under its own heading: ## name, then its lscpu output or the flags line of /proc/cpuinfo (grep -m1 flags /proc/cpuinfo). Or one line per host: name: flags...', '## node-1\nModel name: Intel(R) Xeon(R) Gold 6338\nFlags: fpu vme de pse tsc msr pae ...\n## node-2\nFlags: fpu vme de pse tsc msr pae ...', 9)}
        ${subRow('Compare them', '.txt,text/*')}</form>`};
    return `<div><h1 class="sd-h">Capacity</h1><p class="lead">Where each VM fits at your overcommit limits, whether the cluster survives losing a host, and which CPU every host can share for live migration.</p></div>${ro()}
      ${CAN() ? `<section class="card"><div class="hvk-seg" role="tablist" aria-label="What to work out">${[['plan', 'Hosts and VMs'], ['cpu', 'CPU flags']].map(([k2, t]) => `<button type="button" data-cap="${k2}" aria-pressed="${k2 === w}">${esc(t)}</button>`).join('')}</div><div style="margin-top:14px">${forms[w]}</div></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('plan', 'cpu'))}</section>`;
  }
  function pPlan(d) {
    const r = d.result || {}, t = r.totals || {};
    const hostRows = (r.hosts || []).map(h => `<div class="hvk-host${h.over ? ' over' : ''}"><div class="h"><b>${esc(h.name)}</b><span class="mut">${esc(num(h.cores))} cores · ${esc(num(h.ram))} GiB${h.numa > 1 ? ' · ' + esc(h.numa) + ' NUMA nodes' : ''}</span></div>
        <div class="m"><span>CPU</span>${meter(h.cpu_share, '', 'CPU ' + pct(h.cpu_share))}<em>${esc(num(h.vcpu))} / ${esc(num(Math.round(h.vcpu_cap * 10) / 10))} vCPUs</em></div>
        <div class="m"><span>RAM</span>${meter(h.ram_share, '', 'RAM ' + pct(h.ram_share))}<em>${esc(num(h.ram_used))} / ${esc(num(Math.round(h.ram_cap * 10) / 10))} GiB</em></div>
        <div class="hvk-vms">${h.vms.length ? h.vms.map(v => `<span class="${(r.numa_span || []).includes(v) ? 'numa' : ''}">${esc(v)}</span>`).join('') : '<span class="mut">empty</span>'}</div></div>`).join('');
    const fail = r.fail || [];
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('vCPUs per core', esc(num(t.vcpu_per_core)), `limit ${num(r.ratio)}`, t.vcpu_per_core > r.ratio)}${tile('Memory used', esc(pct(t.ram_share)), `${num(t.vm_ram)} of ${num(t.ram)} GiB`, t.ram_share > 0.9)}
        ${tile('Host failure', r.survives === null || r.survives === undefined ? '—' : r.survives ? 'Survives' : 'At risk', r.failures ? `losing any ${pl(r.failures, 'host')}` : 'not checked', r.survives === false)}${tile('Placement', esc(r.mode === 'yours' ? 'Yours' : 'Worked out'), (r.unplaced || []).length ? pl(r.unplaced.length, 'VM') + ' fit nowhere' : 'every VM placed', (r.unplaced || []).length)}</div></section>
      <section class="card"><h2 class="md-h2">Hosts</h2><div class="hvk-hosts">${hostRows}</div><p class="cs-note">Kept for each host: ${esc(num(r.reserve_cores))} core(s), ${esc(num(r.reserve_gb))} GiB. Dotted VMs span NUMA nodes.</p></section>
      ${fail.length ? `<section class="card"><h2 class="md-h2">If a host fails</h2><div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Down</th><th class="r">VMs to restart</th><th>Nowhere to go</th></tr></thead><tbody>${fail.map(f => `<tr><td>${esc(f.down.join(' + '))}</td><td class="r">${esc(f.moved)}</td><td>${f.stranded.length ? `<span class="cs-neg">${esc(f.stranded.join(', '))}</span> <span class="mut">(${esc(num(f.ram_short))} GiB short)</span>` : '<span class="cs-pos">all restart</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }
  function pCpu(d) {
    const r = d.result || {}, hs = r.hosts || [];
    return `${head(d, 'capacity')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">Hosts</h2><div class="iv-tw"><table class="tb in-cards"><thead><tr><th>Host</th><th>Level</th><th>VT-x / AMD-V</th><th>EPT / NPT</th><th class="r">Flags</th><th class="r">Missing vs others</th></tr></thead><tbody>${hs.map(h => `<tr><td><b>${esc(h.name)}</b>${h.model ? `<div class="mut" style="font-size:12.5px">${esc(h.model)}</div>` : ''}</td><td>${esc(h.level || '—')}</td><td>${h.virt ? tag(h.virt, 'ok') : tag('off', 'bad')}</td><td>${h.slat ? tag('yes', 'ok') : tag('no', 'warn')}</td><td class="r">${esc(num(h.count))}</td><td class="r">${h.missing_n ? `<span class="cs-neg">${esc(num(h.missing_n))}</span>` : '0'}</td></tr>`).join('')}</tbody></table></div>
        <p class="cs-note">All of them share ${esc(num(r.common_n))} flags${r.common_level ? ' and reach ' + esc(r.common_level) : ''}.</p></section>
      ${(r.differ || []).length ? `<section class="card"><h2 class="md-h2">Flags that differ</h2><div class="hvk-chips">${r.differ.map(f => `<span><code>${esc(f)}</code> <em>${esc(hs.filter(h => !h.missing.includes(f)).map(h => h.name).join(', '))}</em></span>`).join('')}</div></section>` : ''}
      <section class="card"><div class="md-acts" style="margin-top:0"><h2 class="md-h2" style="margin:0">The CPU to give VMs</h2><span>${copyBtn(r.xml)}</span></div>${pre(r.xml, 'code')}<p class="cs-note">${esc(r.note)}</p></section>
      ${hs.some(h => (h.vulns || []).length) ? `<section class="card"><h2 class="md-h2">CPU vulnerabilities (from lscpu)</h2>${hs.filter(h => (h.vulns || []).length).map(h => `<h3 class="hvk-h3">${esc(h.name)}</h3><div class="hvk-vul">${h.vulns.map(v => `<div class="${/^vulnerable/i.test(v.state) ? 'bad' : ''}"><span>${esc(v.name)}</span><span class="mut">${esc(v.state)}</span></div>`).join('')}</div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}</section>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that runs your container the hardened way on every pull request - so a change that needs root, a capability or a syscall shows up before it ships.</p></div>
      <section class="card"><h2 class="md-h2">What it runs</h2><div class="ar-facts">${[['Image', s.image || 'built from ' + (s.dockerfile || 'Dockerfile')], ['User', s.uid], ['Seccomp', s.seccomp_file || 'the runtime default'], ['Limits', `${s.memory} memory · ${s.cpus} CPU · ${s.pids} processes`], ['Health check', s.health || 'still running after 20 s'], ['Port', s.port || 'none']].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dlci="1">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">The level your containers must meet, your hosts' architecture and overcommit limits, and what the CI check runs.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="hvk-grid">
        <h2 class="md-h2 wide" style="margin:0">Containers</h2>
        ${sel('target', 'Level to meet', [['restricted', 'Restricted'], ['baseline', 'Baseline']], s.target)}${fld('uid', 'Non-root user id', s.uid, 'type="number" min="1" step="1"')}${sel('arch', 'Architecture', ARCH, s.arch)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Hosts</h2>
        ${fld('vcpu_ratio', 'vCPUs per physical core', s.vcpu_ratio, 'type="number" min="0.1" max="32" step="any"')}${fld('ram_ratio', 'RAM overcommit (1 = none)', s.ram_ratio, 'type="number" min="0.5" max="4" step="any"')}
        ${fld('reserve_gb', 'RAM kept for each host (GiB)', s.reserve_gb, 'type="number" min="0" step="any"')}${fld('reserve_cores', 'Cores kept for each host', s.reserve_cores, 'type="number" min="0" step="any"')}
        ${sel('failures', 'Must survive losing', [[0, 'No failover check'], [1, '1 host'], [2, '2 hosts']], s.failures)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${fld('image', 'Image to pull (or leave empty to build)', s.image, '', 'ghcr.io/you/app:1.4')}${fld('dockerfile', 'Dockerfile', s.dockerfile, '', 'Dockerfile')}${fld('context', 'Build folder', s.context, '', '.')}
        ${fld('seccomp_file', 'Seccomp profile in the repo', s.seccomp_file, '', 'security/seccomp.json')}${fld('port', 'Port it listens on (0 = none)', s.port, 'type="number" min="0" max="65535" step="1"')}
        ${fld('health', 'Health check', s.health, '', 'http://127.0.0.1:8080/health or a command')}${fld('memory', 'Memory limit', s.memory, '', '512m')}${fld('cpus', 'CPUs', s.cpus, '', '1')}
        ${fld('pids', 'Process limit', s.pids, 'type="number" min="16" step="1"')}${sel('net_bind', 'Keep NET_BIND_SERVICE', [['0', 'No'], ['1', 'Yes']], s.net_bind ? '1' : '0')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the checks work</h2><ul class="ar-never"><li>Container levels follow the Kubernetes Pod Security Standards as written in the Kubernetes docs; Docker and Compose configs are read by the same rules in Docker's terms.</li><li>Seccomp: syscall names and numbers come from the Linux headers for x86_64 and aarch64; argument filters are noted, not evaluated.</li><li>VMs: only the XML is read - not the host, its storage or the guest.</li><li>Capacity: arithmetic on the numbers you give, biggest VM first onto the host with the most room; it is not a scheduler.</li><li>CPU levels are the x86-64 psABI's; the libvirt model name comes from virsh on your hosts.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Changes anything on your hosts, clusters or VMs.</li><li>Runs your containers or VMs itself - the CI workflow runs them in your repository.</li><li>Calls a config safe beyond what the checks read: they do not scan images for CVEs or test the kernel.</li><li>Follows anything written inside a config, a trace or an XML file: they are data.</li></ul></section>`;
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
    const cw = t.closest('[data-cap]'); if (cw) { ST.cap = cw.dataset.cap; showPage(true); return; }
    if (t.closest('[data-dlci]')) { const w = ST.out.ci; if (w && w.yaml) saveBlob('hardened-container.yml', new Blob([w.yaml], {type: 'text/yaml'})); return; }
    if (t.closest('[data-dlprof]')) { const d = ST.out['i:' + ST.arg]; if (d && d.result) saveBlob(d.result.file || 'seccomp.json', new Blob([d.result.profile || ''], {type: 'application/json'})); return; }
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
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 3000000) { toast('That file is larger than 3 MB.', true); el.value = ''; return; }
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
      if (kind === 'container') await go('container', {text: S(fd.get('text')), inputs: pick(['target', 'uid'])});
      else if (kind === 'seccomp') await go('seccomp', {text: S(fd.get('text')), inputs: pick(['arch'])});
      else if (kind === 'trace') await go('trace', {text: S(fd.get('text')), inputs: pick(['arch', 'base'])});
      else if (kind === 'domain') await go('domain', {text: S(fd.get('text'))});
      else if (kind === 'plan') await go('plan', {text: S(fd.get('text')), inputs: pick(['vcpu_ratio', 'ram_ratio', 'reserve_gb', 'reserve_cores', 'failures'])});
      else if (kind === 'cpu') await go('cpu', {text: S(fd.get('text'))});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['arch', 'target', 'uid', 'vcpu_ratio', 'ram_ratio', 'reserve_gb', 'reserve_cores', 'failures', 'image', 'dockerfile', 'context', 'seccomp_file', 'port', 'health', 'memory', 'pids', 'cpus', 'net_bind'];


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
    const box = $('#hvFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/hvdesk/chat'); ST.chat = r.id; }
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


