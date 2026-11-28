/* ROBOTICS DESK - the Robotics Software Engineer's own section, like the finance desks (owner: "Robotics Software Engineer same as
   finance desks"). A thin top bar, then the Robotics chat (its own conversation, kind 'robotics') beside the desk's pages: Today, Arm,
   Robot model, ROS graph, Control, Motion, CI check, Settings. The pages call /api/rbdesk/do/<part>; nothing runs on her robots. */
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

  const TABS = [['today', 'Today'], ['arm', 'Arm'], ['model', 'Robot model'], ['graph', 'ROS graph'], ['control', 'Control'], ['motion', 'Motion'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where do I start with a robot that drifts?', 'How do I find why a node gets no data?', 'What should I check before a first power-on?'],
    arm: ['Standard or modified DH - which is mine?', 'Why does my arm stall near a straight elbow?', 'How do I check my DH table on the real arm?'],
    model: ['How do I work out a link\'s inertia?', 'Why does my robot fly apart in Gazebo?', 'Should the root link have mass?'],
    graph: ['Why does my subscriber get nothing?', 'Which QoS for a camera or lidar?', 'What does REP 105 say about map and odom?'],
    control: ['How do I record a clean step?', 'P, PI or PID for a motor speed loop?', 'Why does my joint oscillate?'],
    motion: ['Trapezoid or S-curve?', 'How do I pick a jerk limit?', 'How much torque margin should I keep?'],
    ci: ['Should CI run simulation tests?', 'How do I test without the robot?', 'Which ROS 2 version should I target?'],
    settings: ['Which ROS 2 version should I use?', 'What payload should I put in?', 'Where does my URDF live in the repo?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'arm', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.rbdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.rbdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'robotics', name: 'Robotics'} : null;
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
  const run = (part, a) => api('POST', '/api/rbdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/rbdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Robotics Software Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="rbHire">Hire the Robotics Software Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#rbHire').onclick = async () => { try { await api('POST', '/api/employees/robotics_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Robotics</div><div class="sd-site" id="rbSite"></div></div>
          <span id="rbState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Robotics chat">
          <div class="sd-chathead"><div class="t"><b>Robotics chat</b><span>Paste a DH table, a URDF, ros2 output or a recorded step - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="rbFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="rbPick" multiple hidden accept=".txt,.urdf,.xacro,.xml,.csv,.yaml,.yml,.gv,.json,.md,.log,.py,.cpp,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Robotics desk" id="sdTabs"></nav>
          <div id="rbPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a model or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#rbPick').click()});
    $('#rbPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.rbdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.rbdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/rbdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#rbPage').addEventListener('click', onPageClick);
    $('#rbPage').addEventListener('submit', onSubmit);
    $('#rbPage').addEventListener('change', onChange);
    $('#rbPage').addEventListener('input', onInput);
    $('#rbPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#rbState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#rbSite').textContent = [s.ros_distro && 'ROS 2 ' + cap(s.ros_distro), s.packages, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/rbdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#rbPage'); if (!box) return;
    const fn = {today: pToday, arm: pArm, model: pModel, graph: pGraph, control: pControl, motion: pMotion, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="rbk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {arm: 'Arm', urdf: 'Robot model', graph: 'ROS graph', control: 'Control', motion: 'Motion'};
  const ROUTE = {arm: 'arm', urdf: 'model', graph: 'graph', control: 'control', motion: 'motion'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const M = v => { if (v === null || v === undefined) return '—'; const n = Number(v); return Math.abs(n) < 1 && n !== 0 ? P4(n * 1000) + ' mm' : P4(n) + ' m'; };
  const sec = v => { if (v === null || v === undefined) return '—'; const n = Number(v); return Math.abs(n) < 1 ? P4(n * 1000) + ' ms' : P4(n) + ' s'; };
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'arm': return `${pl(b.dof || 0, 'joint')} · tool at ${(b.xyz || []).map(P4).join(', ')} m${b.ik === true ? ' · target reached' : b.ik === false ? ' · target not reached' : ''}`;
      case 'urdf': return `${pl(b.links || 0, 'link')} · ${pl(b.moving || 0, 'moving joint')} · ${P4(b.mass)} kg`;
      case 'graph': return [b.nodes ? pl(b.nodes, 'node') : '', b.topics ? pl(b.topics, 'topic') : '', b.frames ? pl(b.frames, 'tf link') : ''].filter(Boolean).join(' · ');
      case 'control': return `${b.closed ? 'closed' : 'open'} loop · ${num(Math.round(b.overshoot || 0))}% overshoot${b.settle !== null && b.settle !== undefined ? ' · settles in ' + sec(b.settle) : ''}`;
      case 'motion': return `${pl(b.axes || 0, 'axis', 'axes')} · ${sec(b.T)}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="rbk-list">${list.map(x => `<button type="button" class="rbk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="rbk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="rbk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="rbk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="rbk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono rbk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft rbk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="rbk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card rbk-sum ${ok ? 'okv' : 'badv'}"><p class="rbk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="rbk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="rbk-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="rbk-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="rbk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), a = k.arm, u = k.urdf, g = k.graph, c = k.control, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Arm', a ? esc(num(a.dof)) + ' <small>joints</small>' : '—', a ? `tool at ${(a.xyz || []).map(P4).join(', ')} m · ${a.number}` : 'paste a DH table', a && a.bad),
      tile('Robot model', u ? (u.bad ? esc(num(u.issues)) + ' <small>to fix</small>' : 'Loads') : '—', u ? `${pl(u.links || 0, 'link')}, ${P4(u.mass)} kg · ${u.number}` : 'paste the URDF', u && u.bad),
      tile('ROS graph', g ? (g.bad ? esc(num(g.issues)) + ' <small>to fix</small>' : 'Connects') : '—', g ? [g.nodes ? pl(g.nodes, 'node') : '', g.topics ? pl(g.topics, 'topic') : '', g.frames ? pl(g.frames, 'tf link') : ''].filter(Boolean).join(', ') + ' · ' + g.number : 'paste ros2 node info', g && g.bad),
      tile('Control', c ? esc(num(Math.round(c.overshoot || 0))) + '<small>% overshoot</small>' : '—', c ? `${c.closed ? 'closed loop' : 'open loop step'}${c.settle !== null && c.settle !== undefined ? ', settles in ' + sec(c.settle) : ''} · ${c.number}` : 'paste a step response', c && c.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.packages ? `ROS 2 ${cap(s.ros_distro)} · ${s.packages}` : 'Set your ROS 2 version and packages in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="rbk-path">
        <li><button type="button" data-go="model"><b>Make the model load</b><span>One tree, joint limits, axes, and mass and inertia a simulator can use</span></button></li>
        <li><button type="button" data-go="arm"><b>Know where the tool goes</b><span>Forward and inverse kinematics, singularities and the torque each joint holds</span></button></li>
        <li><button type="button" data-go="graph"><b>Make the data flow</b><span>Topics nobody publishes, names and QoS that never connect, a broken tf tree</span></button></li>
        <li><button type="button" data-go="control"><b>Make it move well</b><span>PID gains from a recorded step, then moves that respect speed, acceleration and jerk</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- arm */
  const SAMPLE_ARM = "# Franka Panda, modified (Craig) table - lengths in m, angles in degrees\nj1 revolute d=0.333 a=0      alpha=0   min=-166 max=166\nj2 revolute d=0     a=0      alpha=-90 min=-101 max=101\nj3 revolute d=0.316 a=0      alpha=90  min=-166 max=166\nj4 revolute d=0     a=0.0825 alpha=90  min=-176 max=-4\nj5 revolute d=0.384 a=-0.0825 alpha=-90 min=-166 max=166\nj6 revolute d=0     a=0      alpha=90  min=-1   max=215\nj7 revolute d=0     a=0.088  alpha=90  min=-166 max=166\nflange d=0.107";
  function pArm() {
    if (ST.arg) return one(ST.arg, 'arm', pAr);
    const s = st_();
    return `<div><h1 class="sd-h">Arm</h1><p class="lead">An arm worked out from its Denavit-Hartenberg table: where the tool is, the joint values that reach a target, how close it is to a singularity, and the torque each joint holds.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Work out an arm</h2><form data-form="arm" class="rbk-grid">
        ${area('text', "One joint per line: name, revolute or prismatic, d= a= alpha= theta= (the offset) and min= max=; a last 'tool' (or flange) line for the fixed offset to the tool", SAMPLE_ARM, 10)}
        ${sel('dh', 'Table kind', [['standard', 'Standard (Denavit-Hartenberg)'], ['modified', 'Modified (Craig) - e.g. Franka']], s.dh)}
        ${fld('q', 'Joint values (one per moving joint)', '', '', '0 -30 0 -120 0 90 45')}
        ${fld('target', 'Target: x y z [roll pitch yaw]', '', '', '0.4 0.1 0.5 180 0 0')}${fld('payload', 'Payload at the tool (kg)', s.payload_kg || '', 'type="number" min="0" step="any"', '2')}
        ${subRow('Work it out', '.txt,.csv,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Worked out</h2>${itemRows(items('arm'))}</section>`;
  }
  function armView(frames, ix, iy, label) {
    if (!frames || frames.length < 2) return '';
    const xs = frames.map(f => f[ix]), ys = frames.map(f => f[iy]);
    const W = 360, H = 300, pad = 24;
    let x0 = Math.min(...xs, 0), x1 = Math.max(...xs, 0), y0 = Math.min(...ys, 0), y1 = Math.max(...ys, 0);
    const span = Math.max(x1 - x0, y1 - y0, 1e-6);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, sc = (Math.min(W, H) - 2 * pad) / span;
    const X = v => W / 2 + (v - cx) * sc, Y = v => H / 2 - (v - cy) * sc;
    const pts = frames.map(f => `${X(f[ix]).toFixed(1)},${Y(f[iy]).toFixed(1)}`).join(' ');
    const dots = frames.map((f, i) => `<circle class="${i === 0 ? 'base' : i === frames.length - 1 ? 'tool' : 'jt'}" cx="${X(f[ix]).toFixed(1)}" cy="${Y(f[iy]).toFixed(1)}" r="${i === frames.length - 1 ? 6 : 4.5}"><title>${i === 0 ? 'base' : i === frames.length - 1 ? 'tool' : 'frame ' + i} (${P4(f[0])}, ${P4(f[1])}, ${P4(f[2])})</title></circle>`).join('');
    const axl = ['x', 'y', 'z'];
    return `<figure class="rbk-armv"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}"><line class="ax" x1="${X(0)}" x2="${X(0) + 34}" y1="${Y(0)}" y2="${Y(0)}"/><line class="ax" x1="${X(0)}" x2="${X(0)}" y1="${Y(0)}" y2="${Y(0) - 34}"/><text class="tx" x="${X(0) + 38}" y="${Y(0) + 4}">${axl[ix]}</text><text class="tx" x="${X(0) - 4}" y="${Y(0) - 38}" text-anchor="end">${axl[iy]}</text><polyline class="link" points="${pts}"/>${dots}</svg><figcaption>${esc(label)}</figcaption></figure>`;
  }
  function jointRows(q) {
    return `<div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Joint</th><th class="r">Value</th><th>Within its limits</th><th class="r">Limits</th></tr></thead><tbody>${(q || []).map(j => {
      const lo = j.limit && j.limit[0], hi = j.limit && j.limit[1], has = lo !== null && lo !== undefined && hi !== null && hi !== undefined;
      const pct = has ? (j.value - lo) / (hi - lo) * 100 : null;
      return `<tr class="${j.out ? 'bad' : ''}"><td><b>${esc(j.name)}</b> <span class="mut">${esc(j.type)}</span></td><td class="r">${esc(P4(j.value))} ${esc(j.unit)}</td><td style="min-width:140px">${has ? `<div class="rbk-pos"><i style="left:${Math.min(100, Math.max(0, pct)).toFixed(1)}%" class="${j.out ? 'bad' : pct < 5 || pct > 95 ? 'warn' : ''}"></i></div>` : '<span class="mut">no limits given</span>'}</td><td class="r mut">${has ? esc(P4(lo)) + ' to ' + esc(P4(hi)) + ' ' + esc(j.unit) : '—'}</td></tr>`; }).join('')}</tbody></table></div>`;
  }
  function pAr(d) {
    const r = d.result || {}, p = r.pose || {}, ik = r.ik;
    const svals = r.singular_values || [], ratio = svals.length ? svals[svals.length - 1] / (svals[0] || 1) : 0;
    return `${head(d, 'arm')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Tool position', (p.xyz || []).map(v => esc(P4(v))).join(', ') + ' <small>m</small>', 'x, y, z from the base')}${tile('Tool orientation', (p.rpy || []).map(v => esc(P4(v))).join(', ') + '<small>°</small>', 'roll, pitch, yaw')}${tile('Freedom here', esc(num(r.rank)) + ' <small>of ' + esc(num(Math.min(6, r.dof))) + '</small>', 'directions the tool can move now', r.near_singular)}${tile('Reach', esc(M(r.reach)), 'at most, from the table')}</div></section>
      <section class="card"><h2 class="md-h2">The arm at these joint values</h2><div class="rbk-armvs">${armView(r.frames, 0, 2, 'From the side (x, z)')}${armView(r.frames, 0, 1, 'From above (x, y)')}</div><p class="mut" style="margin:6px 0 0;font-size:13px">Each dot is a joint frame, the large one the tool. Base at the origin, z up.</p></section>
      <section class="card"><h2 class="md-h2">Joints</h2>${jointRows(r.q)}</section>
      ${ik ? `<section class="card"><h2 class="md-h2">Reaching the target</h2><p style="margin:0 0 4px">Target <b>${esc(ik.target.map(P4).join(', '))} m</b>${ik.rpy ? ` turned <b>${esc(ik.rpy.map(P4).join(', '))}°</b>` : ''}</p>${stats([['Reached', ik.ok ? 'yes' : 'no', ik.ok ? '' : 'bad'], ['Position error', P4(ik.pos_err_mm) + ' mm'], ['Orientation error', ik.rpy ? P4(ik.ori_err_deg) + '°' : 'not asked'], ['Distance from base', M(ik.distance)]])}${ik.ok ? `<h3 class="rbk-h3">Joint values that reach it</h3>${jointRows(ik.q)}<p class="cs-note">One of the solutions - the one found from where the arm is now. Copy: <code>${esc(ik.q.map(j => P4(j.value)).join(' '))}</code></p>` : ''}</section>` : ''}
      ${(r.torque || []).length ? `<section class="card"><h2 class="md-h2">Holding ${esc(P4(r.payload))} kg at the tool</h2>${bars(r.torque.map(t => [t.name, Math.abs(t.value), 'rbk-b', t.unit]), v => P4(v), 'Torque each joint holds')}<p class="cs-note">For the payload held still at these joint values; the arm's own weight and its accelerations come on top.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Singularity</h2>${stats([['Manipulability', P4(r.manipulability)], ['Weakest / strongest direction', (ratio * 100).toFixed(1) + '%', ratio < 0.02 ? 'bad' : ''], ['Moving joints', r.dof]])}
        <details class="rbk-raw" data-key="jac:${esc(d.id)}"${ST.open.has('jac:' + d.id) ? ' open' : ''}><summary>The Jacobian</summary><div class="iv-tw"><table class="tb rbk-t rbk-jac"><thead><tr><th></th>${(r.q || []).map(j => `<th class="r">${esc(j.name)}</th>`).join('')}</tr></thead><tbody>${(r.jacobian || []).map((row, i) => `<tr><td class="mut">${['vx', 'vy', 'vz', 'wx', 'wy', 'wz'][i]}</td>${row.map(v => `<td class="r">${esc(P4(v))}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details></section>
      <section class="card"><h2 class="md-h2">The table</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Joint</th><th>Type</th><th class="r">d</th><th class="r">a</th><th class="r">alpha</th><th class="r">theta</th></tr></thead><tbody>${(r.joints || []).map(j => `<tr><td><b>${esc(j.name)}</b></td><td>${esc(j.type)}</td><td class="r">${esc(P4(j.d))}</td><td class="r">${esc(P4(j.a))}</td><td class="r">${esc(P4(j.alpha))}°</td><td class="r">${esc(P4(j.theta))}°</td></tr>`).join('')}</tbody></table></div><p class="mut" style="margin:8px 0 0;font-size:13px">${esc(r.mode === 'modified' ? 'Modified (Craig) table' : 'Standard (Denavit-Hartenberg) table')}, lengths in metres.</p></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card rbk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- robot model */
  const SAMPLE_URDF = '<robot name="my_arm">\n  <link name="base_link"/>\n  <link name="link1">\n    <inertial><mass value="1.2"/><inertia ixx="0.01" iyy="0.01" izz="0.005" ixy="0" ixz="0" iyz="0"/></inertial>\n  </link>\n  <joint name="joint1" type="revolute">\n    <parent link="base_link"/><child link="link1"/>\n    <axis xyz="0 0 1"/><limit lower="-2.9" upper="2.9" effort="40" velocity="2.0"/>\n  </joint>\n</robot>';
  function pModel() {
    if (ST.arg) return one(ST.arg, 'model', pUr);
    return `<div><h1 class="sd-h">Robot model</h1><p class="lead">A URDF checked the way loaders and simulators read it: one tree, every joint's links, limits and axes, and mass and inertia a physics engine can use.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a model</h2><form data-form="urdf" class="rbk-grid">
        ${area('text', 'The URDF - expand xacro first: xacro robot.urdf.xacro > robot.urdf', SAMPLE_URDF, 12)}${subRow('Check it', '.urdf,.xml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('urdf'))}</section>`;
  }
  const JT = {revolute: 'ok', continuous: 'ok', prismatic: 'ok', fixed: '', floating: 'warn', planar: 'warn'};
  function pUr(d) {
    const r = d.result || {}, bad = new Set((r.issues || []).filter(i => i.sev === 'bad').map(i => i.fn));
    const tree = (r.tree || []).map(t => `<div class="rbk-node${bad.has(t.name) || bad.has(t.joint) ? ' bad' : ''}" style="padding-left:${10 + t.depth * 20}px">${t.depth ? '<span class="br">└</span>' : ''}<b>${esc(t.name)}</b>${t.joint ? ` <span class="mut">via ${esc(t.joint)}</span> ${tag(t.type, JT[t.type])}` : ' <span class="cs-tag">root</span>'}</div>`).join('');
    const lim = l => !l ? '—' : `${P4(l.lower)} to ${P4(l.upper)} · ${P4(l.effort)} · ${P4(l.velocity)}`;
    return `${head(d, 'model')}${verdict(r, isOk(r))}
      <section class="card">${stats([['Links', r.links], ['Joints', r.joints], ['Moving', r.moving], ['Deepest chain', r.depth], ['Total mass', P4(r.mass) + ' kg'], ['Root', r.root || '—']])}</section>
      <section class="card"><h2 class="md-h2">The tree</h2><div class="rbk-tree">${tree || empty('No tree could be built.')}</div></section>
      <section class="card"><h2 class="md-h2">Joints</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Joint</th><th>Type</th><th>Parent → child</th><th>Axis</th><th>Limits (lower to upper · effort · velocity)</th></tr></thead><tbody>${(r.joint_rows || []).map(j => `<tr class="${bad.has(j.name) ? 'bad' : ''}"><td><b>${esc(j.name)}</b></td><td>${tag(j.type, JT[j.type])}</td><td>${esc(j.parent)} → ${esc(j.child)}</td><td><code>${esc(j.axis ? j.axis.map(P4).join(' ') : '—')}</code></td><td class="mut">${esc(lim(j.limit))}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Links</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Link</th><th class="r">Mass</th><th class="r">Drawn</th><th class="r">Collision</th></tr></thead><tbody>${(r.link_rows || []).map(l => `<tr class="${bad.has(l.name) ? 'bad' : ''}"><td><b>${esc(l.name)}</b></td><td class="r">${l.mass === null || l.mass === undefined ? '<span class="mut">none</span>' : esc(P4(l.mass)) + ' kg'}</td><td class="r">${esc(num(l.visual))}</td><td class="r">${l.collision ? esc(num(l.collision)) : tag('none', l.visual ? 'warn' : '')}</td></tr>`).join('')}</tbody></table></div></section>
      ${(r.meshes || []).length ? `<section class="card"><h2 class="md-h2">Meshes it needs</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Link</th><th>Use</th><th>File</th></tr></thead><tbody>${r.meshes.map(m => `<tr><td>${esc(m.link)}</td><td>${esc(m.use)}</td><td><code class="rbk-wrap">${esc(m.file)}</code></td></tr>`).join('')}</tbody></table></div><p class="cs-note">Make sure each of these ships in the package that the address names.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card rbk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 200000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- ROS graph */
  const SAMPLE_G = "/camera_driver\n  Subscribers:\n  Publishers:\n    /camera/image_raw: sensor_msgs/msg/Image\n  Service Servers:\n  Service Clients:\n  Action Servers:\n  Action Clients:\n/detector\n  Subscribers:\n    /image_raw: sensor_msgs/msg/Image\n  Publishers:\n    /detections: vision_msgs/msg/Detection2DArray\n  Service Servers:\n  Service Clients:\n  Action Servers:\n  Action Clients:";
  function pGraph() {
    if (ST.arg) return one(ST.arg, 'graph', pGr);
    return `<div><h1 class="sd-h">ROS graph</h1><p class="lead">Your ROS 2 system read from its own tools' output: topics nobody publishes, names that differ by a namespace, QoS settings that never connect, and a split or stale tf tree.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a system</h2><form data-form="graph" class="rbk-grid">
        ${area('text', 'Paste any of: `for n in $(ros2 node list); do ros2 node info $n; done`, `ros2 topic info -v /topic` (QoS), and the tf frames from `ros2 run tf2_tools view_frames` (frames .gv or the frame YAML it logs)', SAMPLE_G, 14)}
        ${subRow('Read it', '.txt,.gv,.yaml,.yml,.log,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('graph'))}</section>`;
  }
  function graphSvg(r) {
    const nodes = (r.nodes || []).slice(0, 30), tps = (r.topics || []).filter(t => !t.system && (t.pub.length || t.sub.length)).slice(0, 40);
    if (!nodes.length || !tps.length) return '';
    const W = 760, row = 30, h = Math.max(nodes.length, tps.length) * row + 20, NX = 200, TX = 470;
    const ny = {}, ty = {};
    nodes.forEach((n, i) => { ny[n.name] = 20 + i * row + (Math.max(0, tps.length - nodes.length) * row) / 2; });
    tps.forEach((t, i) => { ty[t.name] = 20 + i * row + (Math.max(0, nodes.length - tps.length) * row) / 2; });
    const edge = (n, t, sub) => ny[n] === undefined || ty[t] === undefined ? '' : `<path class="e${sub ? ' sub' : ''}" d="M${NX + 6},${ny[n]} C${NX + 120},${ny[n]} ${TX - 120},${ty[t]} ${TX - 6},${ty[t]}"/>`;
    const edges = tps.map(t => t.pub.map(n => edge(n, t.name, false)).join('') + t.sub.map(n => edge(n, t.name, true)).join('')).join('');
    const nl = nodes.map(n => `<g><circle class="n" cx="${NX}" cy="${ny[n.name]}" r="6"/><text class="nm" x="${NX - 12}" y="${ny[n.name] + 4}" text-anchor="end">${esc(n.name.slice(0, 26))}</text></g>`).join('');
    const tl = tps.map(t => `<g><rect class="t ${t.state || ''}" x="${TX - 6}" y="${ty[t.name] - 6}" width="12" height="12" rx="3"/><text class="nm" x="${TX + 14}" y="${ty[t.name] + 4}">${esc(t.name.slice(0, 34))}</text></g>`).join('');
    return `<div class="rbk-graph"><svg viewBox="0 0 ${W} ${h}" role="img" aria-label="Nodes and the topics they publish and subscribe">${edges}${nl}${tl}</svg><div class="rbk-lkey"><span><i class="c1"></i>publishes</span><span><i class="c1 dash"></i>subscribes</span><span><i class="sq bad"></i>problem</span></div></div>`;
  }
  function pGr(d) {
    const r = d.result || {}, tps = (r.topics || []).filter(t => !t.system);
    const tfT = () => { const kids = {}; (r.tf || []).forEach(x => (kids[x.parent] = kids[x.parent] || []).push(x)); const out = []; const walk = (f, dp, x) => { out.push(`<div class="rbk-node${x && x.stale ? ' bad' : ''}" style="padding-left:${10 + dp * 20}px">${dp ? '<span class="br">└</span>' : ''}<b>${esc(f)}</b>${x ? ` <span class="mut">${x.static ? 'static' : P4(x.rate) + ' Hz'}${x.broadcaster ? ' · ' + esc(x.broadcaster) : ''}</span>${x.stale ? ' ' + tag('stopped', 'bad') : ''}` : ' <span class="cs-tag">root</span>'}</div>`); (kids[f] || []).sort((a, b) => a.child.localeCompare(b.child)).forEach(c => { if (out.length < 400) walk(c.child, dp + 1, c); }); }; (r.tf_roots || []).forEach(rt => walk(rt, 0, null)); return out.join(''); };
    return `${head(d, 'graph')}${verdict(r, isOk(r))}
      <section class="card">${stats([['Nodes', (r.nodes || []).length], ['Topics', tps.length], ['Services and actions', (r.services || []).length], ['tf frames', (r.tf || []).length ? (r.tf || []).length + (r.tf_roots || []).length : 0], ['tf trees', (r.tf_roots || []).length, (r.tf_roots || []).length > 1 ? 'bad' : '']])}</section>
      ${graphSvg(r) ? `<section class="card"><h2 class="md-h2">Who talks to whom</h2>${graphSvg(r)}</section>` : ''}
      ${tps.length ? `<section class="card"><h2 class="md-h2">Topics</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Topic</th><th>Type</th><th>Published by</th><th>Subscribed by</th></tr></thead><tbody>${tps.map(t => `<tr class="${t.state || ''}"><td><code>${esc(t.name)}</code></td><td class="mut"><code class="rbk-wrap">${esc(t.types.join(', '))}</code></td><td>${t.pub.length ? esc(t.pub.join(', ')) : tag('nobody', t.sub.length ? 'warn' : '')}</td><td>${t.sub.length ? esc(t.sub.join(', ')) : '<span class="mut">nobody</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${(r.qos || []).length ? `<section class="card"><h2 class="md-h2">QoS between each publisher and subscriber</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Topic</th><th>Publisher</th><th>Subscriber</th><th>Connects</th></tr></thead><tbody>${r.qos.map(q => `<tr class="${q.ok ? '' : 'bad'}"><td style="white-space:nowrap"><code>${esc(q.topic)}</code></td><td>${esc(q.pub)}<div class="mut" style="font-size:12.5px">${esc(q.pub_qos)}</div></td><td>${esc(q.sub)}<div class="mut" style="font-size:12.5px">${esc(q.sub_qos)}</div></td><td>${q.ok ? tag('yes', 'ok') : tag('never', 'bad') + `<div class="mut" style="font-size:12.5px;margin-top:4px">${esc(q.why.join('; '))}</div>`}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${(r.tf_roots || []).length ? `<section class="card"><h2 class="md-h2">The tf tree</h2><div class="rbk-tree">${tfT()}</div></section>` : ''}
      ${(r.services || []).length ? `<section class="card"><h2 class="md-h2">Services and actions</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Name</th><th>Kind</th><th>Served by</th><th>Called by</th></tr></thead><tbody>${r.services.map(v => `<tr class="${v.cli.length && !v.srv.length ? 'warn' : ''}"><td><code>${esc(v.name)}</code></td><td>${esc(v.kind)}</td><td>${v.srv.length ? esc(v.srv.join(', ')) : tag('nobody', v.cli.length ? 'warn' : '')}</td><td>${v.cli.length ? esc(v.cli.join(', ')) : '<span class="mut">nobody</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card rbk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 200000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- control */
  const SAMPLE_C = "time,speed,command\n0.0,0.00,0\n0.5,0.00,0\n1.0,0.00,1\n1.5,0.00,1\n2.0,0.18,1\n2.5,0.52,1\n3.0,0.80,1\n3.5,1.02,1\n4.0,1.19,1\n...";
  function pControl() {
    if (ST.arg) return one(ST.arg, 'control', pCt);
    return `<div><h1 class="sd-h">Control</h1><p class="lead">A recorded step turned into rise time, overshoot and settling - and, for an open-loop step, a fitted model with PI / PID gains, each simulated before you try it.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a step response</h2><form data-form="control" class="rbk-grid">
        ${area('text', 'One sample per line: time, measured value, and the setpoint (loop closed) or the command (loop open, controller off) - a CSV from ros2 bag, PlotJuggler or a logger', SAMPLE_C, 10)}
        ${sel('mode', 'What stepped', [['auto', 'Work it out from the column name'], ['open', 'The command (loop open) - gives tuning'], ['closed', 'The setpoint (loop closed)']], 'auto')}
        ${fld('u_step', 'Size of the command step (when there is no third column)', '', 'type="number" step="any"', '1')}
        ${fld('kp', 'Your p gain (optional)', '', 'type="number" step="any"')}${fld('ki', 'Your i gain', '', 'type="number" step="any"')}${fld('kd', 'Your d gain', '', 'type="number" step="any"')}
        ${subRow('Read it', '.csv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('control'))}</section>`;
  }
  function pCt(d) {
    const r = d.result || {}, m = r.metrics || {}, md = r.model, tn = r.tunings || [];
    const series = [{name: 'Measured', pts: r.measured || [], cls: 'ink'}].concat(tn.filter(t => t.stable).map((t, i) => ({name: t.name + ' (simulated)', pts: t.trace, cls: CL[i % 6]})));
    if (r.yours && r.yours.stable) series.push({name: 'Your gains (simulated)', pts: r.yours.trace, cls: 'c6', dash: true});
    return `${head(d, 'control')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Rise (10-90%)', esc(sec(m.rise)), '')}${tile('Overshoot', esc(num(Math.round(m.overshoot || 0))) + '<small>%</small>', '', (m.overshoot || 0) > 20)}${tile('Settles (2%)', esc(sec(m.settle)), 'after the step')}${tile(r.closed ? 'Offset' : 'Swings', r.closed ? (m.sse_pct === null || m.sse_pct === undefined ? '—' : esc(P4(m.sse_pct)) + '<small>%</small>') : esc(num(m.swings)), r.closed ? 'short of the setpoint' : 'before settling', r.closed && Math.abs(m.sse_pct || 0) > 2)}</div></section>
      <section class="card"><h2 class="md-h2">${r.closed ? 'The response' : 'The response and the gains on the fitted model'}</h2>${lines(series, 'seconds after the step', 'share of the final change', 'Step response', {ref: 1, ymax: 2.2})}</section>
      ${md ? `<section class="card"><h2 class="md-h2">The fitted model</h2>${stats([['Gain (output per command)', P4(md.K)], ['Lag (time constant)', sec(md.tau)], ['Dead time', sec(md.theta)], ['Average fit error', (md.fit_pct < 0.1 ? '<0.1' : String(+md.fit_pct.toPrecision(2))) + '%', md.fit_pct > 8 ? 'warn' : '']])}<p class="mut" style="margin:0;font-size:13px">First order plus dead time, fitted from where the response passes 28% and 63% of its change (Smith's method).</p></section>` : r.model_note ? `<section class="card"><p class="mut" style="margin:0">${esc(r.model_note)}</p></section>` : ''}
      ${tn.length ? `<section class="card"><h2 class="md-h2">Gains to try</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Tuning</th><th class="r">p</th><th class="r">i</th><th class="r">d</th><th class="r">Kc · Ti · Td</th><th class="r">Overshoot</th><th class="r">Settles</th></tr></thead><tbody>${tn.map(t => `<tr class="${t.stable ? '' : 'bad'}"><td><b>${esc(t.name)}</b> <span class="mut">${esc(t.form)}</span><div class="mut" style="font-size:12.5px">${esc(t.note)}</div></td><td class="r">${esc(P4(t.p))}</td><td class="r">${esc(P4(t.i))}</td><td class="r">${esc(P4(t.d))}</td><td class="r mut">${esc(P4(t.Kc))} · ${esc(sec(t.Ti))} · ${t.Td ? esc(sec(t.Td)) : '—'}</td><td class="r">${t.stable ? esc(num(Math.round(t.overshoot || 0))) + '%' : tag('unstable', 'bad')}</td><td class="r">${esc(sec(t.settle))}</td></tr>`).join('')}${r.yours ? `<tr class="${r.yours.stable ? '' : 'bad'}"><td><b>Your gains</b></td><td class="r">${esc(P4(r.yours.p))}</td><td class="r">${esc(P4(r.yours.i))}</td><td class="r">${esc(P4(r.yours.d))}</td><td class="r mut">—</td><td class="r">${r.yours.stable ? esc(num(Math.round(r.yours.overshoot || 0))) + '%' : tag('unstable', 'bad')}</td><td class="r">${esc(sec(r.yours.settle))}</td></tr>` : ''}</tbody></table></div>
        <p class="cs-note">p, i, d are the parallel form ros2_control's PID takes (u = p·e + i·∫e + d·de/dt); Kc, Ti, Td the ideal form. Simulated on the fitted model only - try them on the robot with small steps, limits on.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card rbk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 200000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- motion */
  const SAMPLE_M = "x       0.5m   vmax=1    amax=2    jerk=20\ny       0.2m   vmax=1    amax=2    jerk=20\nshoulder 90deg vmax=180  amax=360  jerk=3600  inertia=0.5 torque=4\nlift    0.1m   vmax=0.5  amax=5    mass=10 force=200 vertical=1";
  function pMotion() {
    if (ST.arg) return one(ST.arg, 'motion', pMo);
    const s = st_();
    return `<div><h1 class="sd-h">Motion</h1><p class="lead">A move planned the way a motion controller plans it: trapezoid or S-curve per axis, the time each phase takes, every axis finishing together, and whether the drives can give the acceleration.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Plan a move</h2><form data-form="motion" class="rbk-grid">
        ${area('text', 'One axis per line: name, distance (m, mm, deg or rad), vmax=, amax=, jerk= (for an S-curve) - and inertia= torque= gear= (rotary) or mass= force= vertical=1 (linear) to check the drive', SAMPLE_M, 7)}
        ${sel('sync', 'Every axis finishes together', [['yes', 'Yes - slow the others to the slowest'], ['no', 'No - each as fast as it can']], s.sync)}
        ${subRow('Plan it')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Planned</h2>${itemRows(items('motion'))}</section>`;
  }
  function pMo(d) {
    const r = d.result || {}, ax = r.axes || [];
    const series = ax.map((a, i) => ({name: a.name, pts: (a.curve || []).map(p => [p[0], a.vmax ? Math.abs(p[1]) / a.vmax * 100 : 0]), cls: CL[i % 6]}));
    return `${head(d, 'motion')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('The move takes', esc(sec(r.T)), ax.length > 1 ? 'set by ' + r.slowest : '')}${tile('Axes', esc(num(ax.length)), r.sync && ax.length > 1 ? 'finishing together' : '')}${tile('S-curve', esc(num(ax.filter(a => a.jerk).length)) + ' <small>of ' + esc(num(ax.length)) + '</small>', 'axes with a jerk limit')}${tile('Drive limits', esc(num((r.issues || []).filter(i => i.area === 'Drive' && i.sev === 'bad').length)), 'exceeded', (r.issues || []).some(i => i.area === 'Drive' && i.sev === 'bad'))}</div></section>
      <section class="card"><h2 class="md-h2">Speed over the move</h2>${lines(series, 'seconds', '% of the axis top speed', 'Velocity profiles', {})}</section>
      <section class="card"><h2 class="md-h2">Each axis</h2><div class="iv-tw"><table class="tb in-cards rbk-t"><thead><tr><th>Axis</th><th class="r">Distance</th><th class="r">Alone</th><th class="r">Peak speed</th><th class="r">Speeding up</th><th class="r">At speed</th><th>Drive</th></tr></thead><tbody>${ax.map(a => { const u = a.unit, nd = a.need; return `<tr class="${nd && nd.have !== null && nd.have !== undefined && nd.value > nd.have ? 'bad' : ''}"><td><b>${esc(a.name)}</b>${a.jerk ? ' <span class="cs-tag">S-curve</span>' : ''}</td><td class="r">${esc(P4(a.d))} ${esc(u)}</td><td class="r">${esc(sec(a.T))}</td><td class="r">${esc(P4(a.vp))} ${esc(u)}/s${a.scaled_v ? '<div class="mut" style="font-size:12.5px">slowed to finish together</div>' : !a.full ? '<div class="mut" style="font-size:12.5px">short move: below top speed</div>' : ''}</td><td class="r">${esc(sec(a.Ta))}</td><td class="r">${esc(sec(a.Tv))}</td><td>${nd ? `${esc(P4(nd.value))} ${esc(nd.unit)} needed${nd.have !== null && nd.have !== undefined ? ' of ' + esc(P4(nd.have)) : ''}` : '<span class="mut">not given</span>'}</td></tr>`; }).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card rbk-raw"><summary>What you pasted</summary>${pre(d.text, 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions workflow that installs ROS 2, builds your packages with colcon and runs their tests on every pull request - and checks the robot description with the official URDF parser.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['ROS 2', cap(s.ros_distro)], ['Packages', s.packages || 'not set'], ['Robot description', s.urdf_path || 'none'], ['Extra apt packages', s.extra_deps || 'none'], ['Runner', s.runner || 'the one for this ROS 2 version']].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="ros2-ci.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">How your arm tables are written, the payload, and what the CI check builds.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="rbk-grid">
        <h2 class="md-h2 wide" style="margin:0">Arms</h2>
        ${sel('dh', 'Table kind', [['standard', 'Standard (Denavit-Hartenberg)'], ['modified', 'Modified (Craig)']], s.dh)}${sel('length_unit', 'Lengths without a unit are in', [['m', 'metres'], ['mm', 'millimetres'], ['cm', 'centimetres'], ['in', 'inches']], s.length_unit)}${fld('payload_kg', 'Payload at the tool (kg)', s.payload_kg || '', 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Motion</h2>
        ${sel('sync', 'Every axis finishes together', [['yes', 'Yes'], ['no', 'No']], s.sync)}
        <h2 class="md-h2 wide" style="margin:8px 0 0">CI check</h2>
        ${sel('ros_distro', 'ROS 2 version', [['humble', 'Humble (Ubuntu 22.04)'], ['jazzy', 'Jazzy (Ubuntu 24.04)'], ['kilted', 'Kilted (Ubuntu 24.04)'], ['rolling', 'Rolling']], s.ros_distro)}${fld('packages', 'Packages to build and test', s.packages, 'maxlength="400"', 'my_robot my_robot_bringup')}${fld('urdf_path', 'Robot description (optional)', s.urdf_path, 'maxlength="200"', 'my_robot_description/urdf/robot.urdf.xacro')}
        ${fld('extra_deps', 'Extra apt packages (optional)', s.extra_deps, 'maxlength="400"', 'ros-jazzy-ros2-control')}${fld('runner', 'Runner (optional)', s.runner, 'maxlength="40"', 'ubuntu-24.04')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Arms are worked out from the table you give, base at the origin and z up; one wrong sign moves every frame after it - check one known pose on the real arm.</li><li>Models are read from the URDF text: the structure and the numbers, not whether the meshes exist or the robot looks right.</li><li>The ROS graph is a snapshot of what was running when the output was printed.</li><li>Gains are checked on a model fitted to your step, not on the robot.</li><li>Safety rules for robots (ISO 10218, ISO/TS 15066 for cobots, your country's machinery rules) are not checked here - check them with whoever signs off the cell.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Connects to or runs anything on your robots or your machines.</li><li>Tells you to skip a safety limit, a guard or an emergency stop.</li><li>Calls gains safe from a model: only small steps on the real robot show that.</li><li>Follows anything written inside your files, models or logs: they are data.</li></ul></section>`;
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
      if (kind === 'arm') await go('arm', {text: S(fd.get('text')), inputs: pick(['dh', 'q', 'target', 'payload'])});
      else if (kind === 'urdf') await go('urdf', {text: S(fd.get('text'))});
      else if (kind === 'graph') await go('graph', {text: S(fd.get('text'))});
      else if (kind === 'control') await go('control', {text: S(fd.get('text')), inputs: pick(['mode', 'u_step', 'kp', 'ki', 'kd'])});
      else if (kind === 'motion') await go('motion', {text: S(fd.get('text')), inputs: pick(['sync'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['dh', 'length_unit', 'payload_kg', 'ros_distro', 'packages', 'urdf_path', 'extra_deps', 'runner', 'sync'];


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
    const box = $('#rbFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/rbdesk/chat'); ST.chat = r.id; }
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


