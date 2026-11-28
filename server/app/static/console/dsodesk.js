/* DEVSECOPS ENGINEER DESK - the DevSecOps Engineer's own section, like the finance desks (owner: "DevSecOps Engineer same as
   finance desks"). A thin top bar, then the DevSecOps chat (its own conversation, kind 'devsecops') beside the desk's pages: Today,
   Workflows, SBOM, Dependencies, Repository, Fix times, CI check, Settings. The pages call /api/dsodesk/do/<part>; nothing is run. */
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

  const TABS = [['today', 'Today'], ['workflows', 'Workflows'], ['sbom', 'SBOM'], ['dependencies', 'Dependencies'], ['repository', 'Repository'], ['fix-times', 'Fix times'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where should DevSecOps start in a small team?', 'What does SLSA ask for?', 'What should block a merge?'],
    workflows: ['Why pin actions to a commit SHA?', 'When is pull_request_target safe?', 'How should CI reach the cloud without keys?'],
    sbom: ['Which SBOM format should we use?', 'What does AGPL mean for a web service?', 'How do we keep SBOMs current?'],
    dependencies: ['Should we pin exact versions?', 'How does dependency confusion work?', 'How do we review a new dependency?'],
    repository: ['What should protect the main branch?', 'Rulesets or branch protection?', 'How do code owners work?'],
    'fix-times': ['What fix times are reasonable?', 'How do we handle accepted risks?', 'Why is the backlog growing?'],
    ci: ['Should the guard block or warn?', 'How do we keep pinned actions up to date?', 'What else belongs in a secure pipeline?'],
    settings: ['Which licences do companies usually deny?', 'How many reviews should be required?', 'Which owners can we trust?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'workflows', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dsodesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dsodesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'devsecops', name: 'DevSecOps'} : null;
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
  const run = (part, a) => api('POST', '/api/dsodesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dsodesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your DevSecOps Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dsoHire">Hire the DevSecOps Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dsoHire').onclick = async () => { try { await api('POST', '/api/employees/devsecops_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">DevSecOps</div><div class="sd-site" id="dsoSite"></div></div>
          <span id="dsoState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="DevSecOps chat">
          <div class="sd-chathead"><div class="t"><b>DevSecOps chat</b><span>Paste a workflow, an SBOM, a manifest, repository settings or an export - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dsoFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dsoPick" multiple hidden accept=".txt,.json,.csv,.yaml,.yml,.toml,.mod,.log,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="DevSecOps desk" id="sdTabs"></nav>
          <div id="dsoPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a workflow or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dsoPick').click()});
    $('#dsoPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dsodesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dsodesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dsodesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dsoPage').addEventListener('click', onPageClick);
    $('#dsoPage').addEventListener('submit', onSubmit);
    $('#dsoPage').addEventListener('change', onChange);
    $('#dsoPage').addEventListener('input', onInput);
    $('#dsoPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dsoState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#dsoSite').textContent = ['guard on ' + (s.fail_level === 'bad' ? 'serious' : 'any finding'), pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dsodesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dsoPage'); if (!box) return;
    const fn = {today: pToday, workflows: pWorkflows, sbom: pSbom, dependencies: pDependencies, repository: pRepository, 'fix-times': pFixTimes, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="dok-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {workflows: 'Workflows', sbom: 'SBOM', deps: 'Dependencies', repo: 'Repository', metrics: 'Fix times'};
  const ROUTE = {workflows: 'workflows', sbom: 'sbom', deps: 'dependencies', repo: 'repository', metrics: 'fix-times'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(0);
  const meter = (v, warnAt, badAt) => `<span class="dok-meter"><i class="${v < warnAt ? 'bad' : v < badAt ? 'warn' : ''}" style="width:${Math.min(100, v * 100).toFixed(1)}%"></i></span>`;
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'workflows': return `${pl(b.files || 0, 'workflow')} · ${pl(b.actions || 0, 'action')} · ${num(b.unpinned || 0)} not pinned`;
      case 'sbom': return `${pl(b.components || 0, 'component')} · ${num(b.strong || 0)} strong copyleft · ${num(b.unknown || 0)} unknown`;
      case 'deps': return `${pl(b.deps || 0, 'dependency', 'dependencies')} · ${num(b.unpinned || 0)} not pinned${b.lookalike ? ' · ' + num(b.lookalike) + ' lookalike' : ''}`;
      case 'repo': return `${b.repo ? b.repo + ' · ' : ''}${num(b.passed || 0)} of ${num(b.total || 0)} guard rails${b.protected === false ? ' · not protected' : ''}`;
      case 'metrics': return `${num(b.open || 0)} open of ${num(b.findings || 0)} · ${num(b.late || 0)} past due`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="dok-list">${list.map(x => `<button type="button" class="dok-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="dok-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="dok-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="dok-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="dok-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono dok-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft dok-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="dok-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card dok-sum ${ok ? 'okv' : 'badv'}"><p class="dok-big">${esc(r.verdict)}</p>${r.counts ? `<div class="dok-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="dok-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="dok-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="dok-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];


  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), w = k.workflows, b = k.sbom, d = k.deps, r = k.repo, m = k.metrics, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Workflows', w ? esc(num(w.unpinned || 0)) + ' <small>unpinned</small>' : '—', w ? `${pl(w.files, 'file')}, ${pl(w.actions, 'action')} · ${w.number}` : 'paste a workflow', w && w.bad),
      tile('Dependencies', d ? esc(num(d.unpinned || 0)) + ' <small>not pinned</small>' : '—', d ? `${pl(d.deps, 'dependency', 'dependencies')}${d.lookalike ? ', ' + num(d.lookalike) + ' lookalike' : ''} · ${d.number}` : 'paste a manifest', d && d.bad),
      tile('Repository', r ? esc(num(r.passed)) + `<small> of ${num(r.total)}</small>` : '—', r ? `${r.repo || 'guard rails'} · ${r.number}` : 'paste gh api output', r && r.bad),
      tile('Fix times', m ? esc(num(m.late || 0)) + ' <small>past due</small>' : '—', m ? `${num(m.open)} open of ${num(m.findings)} · ${m.number}` : 'paste a findings export', m && m.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(b ? 'Last SBOM: ' + pl(b.components, 'component') + '.' : 'Paste an SBOM to see what ships inside.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="dok-path">
        <li><button type="button" data-go="workflows"><b>Lock the pipeline</b><span>Actions pinned, no script injection, no pull request code run with secrets</span></button></li>
        <li><button type="button" data-go="dependencies"><b>Choose what comes in</b><span>Pinned versions, known sources, names checked, licences you can ship</span></button></li>
        <li><button type="button" data-go="repository"><b>Guard the branch</b><span>Reviews, checks and push protection that nobody can skip</span></button></li>
        <li><button type="button" data-go="fix-times"><b>Fix on time</b><span>What is past due, how long fixes take and whether the backlog grows</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- workflows */
  const SAMPLE_W = '## .github/workflows/ci.yml\nname: ci\non: pull_request\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: some-org/setup-tool@v2\n      - run: echo "${{ github.event.pull_request.title }}"';
  function pWorkflows() {
    if (ST.arg) return one(ST.arg, 'workflows', pWf);
    const s = st_();
    return `<div><h1 class="sd-h">Workflows</h1><p class="lead">Your GitHub Actions workflows read for the ways pipelines are attacked: actions not pinned to a commit, event text put into a shell, privileged triggers that run pull request code with secrets, missing permissions, secrets every step can read, self-hosted runners on pull requests and scripts piped into a shell.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read workflows</h2><form data-form="workflows" class="dok-grid">
        ${area('text', "Workflow YAML from .github/workflows - several: put '## path' before each", SAMPLE_W, 14)}
        ${fld('trusted_owners', 'Owners you trust like GitHub (not asked to pin)', s.trusted_owners, '', 'my-org, docker')}
        ${subRow('Read them', '.yml,.yaml,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('workflows'))}</section>`;
  }
  function pWf(d) {
    const r = d.result || {}, fs = r.files || [], ac = r.actions || [];
    return `${head(d, 'workflows')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Workflows', esc(num(fs.length)), pl(fs.reduce((a, f) => a + f.jobs, 0), 'job'))}${tile('Actions', esc(num(ac.length)), num(r.pinned) + ' pinned to a commit')}${tile('Not pinned', esc(num(r.unpinned)), 'third-party, on a tag or branch', r.unpinned > 0)}${tile('Serious', esc(num((r.counts || {}).bad || 0)), 'injection, PR code with secrets', ((r.counts || {}).bad || 0) > 0)}</div></section>
      <section class="card"><h2 class="md-h2">Each workflow</h2><div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>File</th><th>Runs on</th><th class="r">Jobs</th><th>Permissions</th><th></th></tr></thead><tbody>${fs.map(f => `<tr class="${f.flags.some(x => ['runs PR code with secrets', 'self-hosted on PRs', 'script injection', 'write-all'].includes(x)) ? 'bad' : f.flags.length ? 'warn' : ''}"><td><b>${esc(f.name)}</b><br><code class="mut">${esc(f.path)}</code></td><td>${esc(f.triggers.join(', '))}</td><td class="r">${esc(num(f.jobs))}</td><td><code>${esc(f.permissions === null ? 'not set' : typeof f.permissions === 'string' ? f.permissions : Object.entries(f.permissions).map(([k2, v]) => k2 + ': ' + v).join(', '))}</code></td><td>${f.flags.map(x => `<span class="cs-tag">${esc(x)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>
      ${ac.length ? `<section class="card"><h2 class="md-h2">Actions used</h2><div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Action</th><th>Version</th><th>Pinned</th><th>Used in</th></tr></thead><tbody>${ac.map(a => `<tr class="${!a.pinned && !a.trusted ? 'warn' : ''}"><td><b>${esc(a.action)}</b>${a.trusted ? ' <span class="cs-tag">trusted owner</span>' : ''}</td><td><code>${esc(a.ref)}</code></td><td>${a.pinned ? '<span class="dok-v" aria-label="yes">✓</span>' : a.trusted ? '<span class="mut">not needed</span>' : '<span class="dok-x" aria-label="no">✕</span>'}</td><td class="mut">${esc(a.files.join(', '))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card dok-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- sbom */
  const SAMPLE_S = '{"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [{"name": "lodash", "version": "4.17.21", "purl": "pkg:npm/lodash@4.17.21", "licenses": [{"license": {"id": "MIT"}}]}]}';
  function pSbom() {
    if (ST.arg) return one(ST.arg, 'sbom', pSb);
    const s = st_();
    return `<div><h1 class="sd-h">SBOM</h1><p class="lead">What ships inside: components by ecosystem and licence family, licences against your own allow and deny lists, components with no licence, version or package URL, and packages present at several versions. A guide, not legal advice.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read an SBOM</h2><form data-form="sbom" class="dok-grid">
        ${area('text', 'CycloneDX JSON or SPDX JSON (syft -o cyclonedx-json, cdxgen, trivy --format cyclonedx, the GitHub dependency graph export)', SAMPLE_S, 12)}
        ${fld('deny', 'Licences you do not allow (SPDX ids, * allowed)', s.deny_licenses, '', 'AGPL-*, SSPL-*')}${fld('allow', 'Licences you allow (empty = all but the denied)', s.allow_licenses, '', 'MIT, Apache-2.0, BSD-*')}
        ${subRow('Read it', '.json,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('sbom'))}</section>`;
  }
  function pSb(d) {
    const r = d.result || {}, fm = r.families || {}, rows = r.rows || [];
    const FN = {permissive: 'Permissive', weak: 'Weak copyleft', strong: 'Strong copyleft', unknown: 'Unknown'};
    const flagged = rows.filter(c => c.flags.length);
    return `${head(d, 'sbom')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Components', esc(num(r.components)), r.format)}${tile('Strong copyleft', esc(num(fm.strong || 0)), 'GPL / AGPL family', fm.strong > 0)}${tile('Unknown licence', esc(num(fm.unknown || 0)), 'no permission named', fm.unknown > 0)}${tile('No supplier', esc(num(r.no_supplier)), 'who made it is not said')}</div></section>
      <div class="dok-two"><section class="card"><h2 class="md-h2">Licence families</h2>${bars(['permissive', 'weak', 'strong', 'unknown'].map(f => [FN[f], fm[f] || 0, f === 'strong' || f === 'unknown' ? 'dok-b warn' : 'dok-b', '']), v => num(v), 'Components by licence family')}</section>
      <section class="card"><h2 class="md-h2">Licences</h2>${bars((r.licenses || []).slice(0, 10).map(([l, n]) => [l, n, 'dok-b', '']), v => num(v), 'Components by licence')}</section></div>
      <section class="card"><h2 class="md-h2">To look at</h2>${flagged.length ? `<div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Component</th><th>Version</th><th>Licence</th><th>Ecosystem</th><th></th></tr></thead><tbody>${flagged.slice(0, 300).map(c => `<tr class="${c.flags.includes('denied licence') ? 'bad' : c.family === 'strong' || c.flags.includes('no licence') ? 'warn' : ''}"><td><b>${esc(c.name)}</b></td><td><code>${esc(c.version || '—')}</code></td><td>${esc(c.license || '—')} <span class="mut">${esc(FN[c.family])}</span></td><td>${esc(c.eco)}</td><td>${c.flags.map(x => `<span class="cs-tag">${esc(x)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Every component has a licence you allow, a version and a package URL.</p>'}</section>
      ${(r.multi || []).length ? `<section class="card"><h2 class="md-h2">Several versions</h2><div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Package</th><th>Versions</th></tr></thead><tbody>${r.multi.map(([n, v]) => `<tr><td><b>${esc(n)}</b></td><td><code>${esc(v.join(', '))}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- dependencies */
  const SAMPLE_D = '## package.json\n{"dependencies": {"react": "^18.2.0", "lodahs": "4.17.21"}}\n## requirements.txt\n--extra-index-url https://pypi.example.internal/simple\nrequests==2.32.3\nflask>=2';
  function pDependencies() {
    if (ST.arg) return one(ST.arg, 'dependencies', pDp);
    const s = st_();
    return `<div><h1 class="sd-h">Dependencies</h1><p class="lead">Your manifests read for supply-chain risk: versions that are not pinned, dependencies from git, a URL or a path, extra package indexes that open the door to dependency confusion, names one or two letters from a well-known package, and packages that run code when installed.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read manifests</h2><form data-form="deps" class="dok-grid">
        ${area('text', "package.json, package-lock.json, requirements.txt, go.mod or Cargo.toml - several: put '## path' before each", SAMPLE_D, 12)}
        ${sel('pin_dev', 'Development dependencies', [['0', 'May use ranges'], ['1', 'Must be pinned too']], String(s.pin_dev || 0))}
        ${subRow('Read them', '.json,.txt,.mod,.toml,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('deps'))}</section>`;
  }
  function pDp(d) {
    const r = d.result || {}, rows = r.rows || [], flagged = rows.filter(x => x.flags.length);
    return `${head(d, 'dependencies')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Dependencies', esc(num(r.deps)), Object.entries(r.ecosystems || {}).map(([k2, n]) => n + ' ' + k2).join(', '))}${tile('Not pinned', esc(num(r.unpinned)), 'take the newest release', r.unpinned > 0)}${tile('From git or a URL', esc(num(r.git)), 'outside the registry', r.git > 0)}${tile('Lookalike names', esc(num(r.lookalike)), 'check the spelling', r.lookalike > 0)}</div></section>
      <section class="card"><h2 class="md-h2">To look at</h2>${flagged.length ? `<div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Package</th><th>Version or source</th><th>Ecosystem</th><th>File</th><th></th></tr></thead><tbody>${flagged.slice(0, 400).map(x => `<tr class="${x.flags.some(f => f.startsWith('looks like') || f === 'extra index') ? 'bad' : 'warn'}"><td><b>${esc(x.name)}</b>${x.dev ? ' <span class="cs-tag">dev</span>' : ''}</td><td><code>${esc(x.spec || '(no version)')}</code></td><td>${esc(x.eco)}</td><td class="mut">${esc(x.file)}</td><td>${x.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Everything is pinned, from the registry, with names that match nothing well-known.</p>'}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card dok-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- repository */
  function pRepository() {
    if (ST.arg) return one(ST.arg, 'repository', pRp);
    const s = st_();
    return `<div><h1 class="sd-h">Repository</h1><p class="lead">The guard rails on your repository and its default branch: reviews and who may approve, required checks, admins, force pushes and deletion, signed commits - and secret scanning, push protection and Dependabot.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a repository</h2><form data-form="repo" class="dok-grid">
        ${area('text', "Paste `gh api repos/OWNER/REPO` and `gh api repos/OWNER/REPO/branches/main/protection` output - put '## repo' and '## protection' before each", '## repo\n{"full_name": "acme/shop", ...}\n## protection\n{"required_pull_request_reviews": {...}}', 12)}
        ${fld('min_reviews', 'Reviews required at least', s.min_reviews, 'type="number" min="0" max="6" step="1"')}${fld('need_checks', 'Checks that must be required', s.need_checks, '', 'test, Pipeline guard')}
        ${subRow('Check it', '.json,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('repo'))}</section>`;
  }
  function pRp(d) {
    const r = d.result || {}, ck = r.checks || [];
    const areas = [...new Set(ck.map(c => c.area))];
    return `${head(d, 'repository')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Guard rails', esc(num(r.passed)) + `<small> of ${num(r.total)}</small>`, 'in place', r.passed < r.total)}${tile('Branch', r.protected ? 'protected' : 'not protected', r.default_branch || '', !r.protected)}${tile('Repository', esc(r.repo || '—'), r.visibility || '')}${tile('Serious', esc(num((r.counts || {}).bad || 0)), 'gaps anyone can use', ((r.counts || {}).bad || 0) > 0)}</div></section>
      ${areas.map(a => `<section class="card"><h2 class="md-h2">${esc(a)}</h2>${ck.filter(c => c.area === a).map(c => `<div class="cs-row"><span class="cs-dot ${c.ok === true ? 'ok' : c.ok === false ? 'bad' : ''}"></span><span><b>${esc(c.name)}</b> - ${esc(c.say)}</span></div>`).join('')}</section>`).join('')}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- fix times */
  const SAMPLE_M = 'id,severity,opened,closed,team\nVULN-1,critical,2026-11-01,2026-11-03,web\nVULN-2,high,2026-09-01,,web\nVULN-3,medium,2026-11-20,,data';
  function pFixTimes() {
    if (ST.arg) return one(ST.arg, 'fix-times', pMe);
    const s = st_();
    return `<div><h1 class="sd-h">Fix times</h1><p class="lead">How fast findings get fixed, from an export over time: what is open and past your fix-time rule, the median and slowest fixes per severity, the share fixed on time, opened against closed week by week, and whether the backlog is growing.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Measure fix times</h2><form data-form="metrics" class="dok-grid">
        ${area('text', 'A CSV of findings: id, severity, opened, closed (blank while open) - and team or source if you have them', SAMPLE_M, 10)}
        ${fld('today', 'As of', '', 'type="date"')}
        ${subRow('Measure', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Measured</h2>${itemRows(items('metrics'))}</section>`;
  }
  function pMe(d) {
    const r = d.result || {}, per = r.per || [], wk = r.weeks || [];
    const SN = {critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low'};
    return `${head(d, 'fix-times')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Open', esc(num(r.open)), 'of ' + num(r.findings) + ' findings')}${tile('Past the fix time', esc(num(r.late)), 'open and late', r.late > 0)}${tile('Critical fixed in', per[0] && per[0].mttr !== null ? esc(P4(per[0].mttr)) + ' <small>days</small>' : '—', 'median, rule ' + (r.sla || {}).critical + ' days', per[0] && per[0].mttr > (r.sla || {}).critical)}${tile('Backlog, 8 weeks', r.trend === null || r.trend === undefined ? '—' : (r.trend > 0 ? '+' : '') + esc(num(r.trend)), r.trend > 0 ? 'growing' : 'steady or falling', r.trend > 0)}</div></section>
      <section class="card"><h2 class="md-h2">By severity</h2><div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Severity</th><th class="r">Rule</th><th class="r">Open</th><th class="r">Late</th><th class="r">Fixed</th><th class="r">Median</th><th class="r">90%</th><th>On time</th></tr></thead><tbody>${per.map(p => `<tr class="${p.open_late && (p.sev === 'critical' || p.sev === 'high') ? 'bad' : p.open_late ? 'warn' : ''}"><td><b>${esc(SN[p.sev])}</b></td><td class="r">${esc(p.sla)} d</td><td class="r">${esc(num(p.open))}</td><td class="r">${esc(num(p.open_late))}</td><td class="r">${esc(num(p.closed))}</td><td class="r">${p.mttr === null ? '—' : esc(P4(p.mttr)) + ' d'}</td><td class="r">${p.p90 === null ? '—' : esc(P4(p.p90)) + ' d'}</td><td>${p.in_sla === null ? '—' : meter(p.in_sla, 0.8, 0.95) + ' ' + esc(pc(p.in_sla)) + '%'}</td></tr>`).join('')}</tbody></table></div></section>
      ${wk.length > 1 ? `<section class="card"><h2 class="md-h2">Open backlog by week</h2>${line(wk.map(w => [w.week.slice(5), w.backlog]), 'Open findings by week', v => num(v), '', true)}<p class="cs-note">${esc(num(wk.reduce((a, w) => a + w.opened, 0)))} opened and ${esc(num(wk.reduce((a, w) => a + w.closed, 0)))} closed over ${esc(pl(wk.length, 'week'))}.</p></section>` : ''}
      <div class="dok-two"><section class="card"><h2 class="md-h2">Age of what is open</h2>${bars(Object.entries(r.buckets || {}).map(([b, n]) => [b + ' days', n, b === '91-180' || b === '180+' ? 'dok-b warn' : 'dok-b', '']), v => num(v), 'Open findings by age')}</section>
      <section class="card"><h2 class="md-h2">By team</h2>${(r.teams || []).length ? bars(r.teams.slice(0, 10).map(t => [t.team, t.open, t.late ? 'dok-b warn' : 'dok-b', num(t.late) + ' late']), v => num(v) + ' open', 'Open findings by team') : '<p class="mut">Add a team column to see this.</p>'}</section></div>
      ${(r.late_list || []).length ? `<section class="card"><h2 class="md-h2">Past the fix time</h2><div class="iv-tw"><table class="tb in-cards dok-t"><thead><tr><th>Finding</th><th>Severity</th><th>Opened</th><th class="r">Days open</th><th>Team</th></tr></thead><tbody>${r.late_list.map(x => `<tr class="${x.sev === 'critical' || x.sev === 'high' ? 'bad' : 'warn'}"><td><b>${esc(x.id)}</b></td><td>${esc(SN[x.sev])}</td><td>${esc(x.opened)}</td><td class="r">${esc(num(x.days))}</td><td>${esc(x.team || '—')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions pipeline guard: every pull request that changes a workflow is read with the same rules as the Workflows page, and the check fails on what you choose. It needs no keys and changes nothing.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Fails on', s.fail_level === 'bad' ? 'serious findings only' : 'anything to fix'], ['Trusted owners', s.trusted_owners || 'GitHub only'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="pipeline-guard.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<ol class="dok-steps">${(w.steps || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol><p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">The owners you trust, your licence lists, your repository minimum, your fix-time rules and the pipeline guard.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="dok-grid">
        <h2 class="md-h2 wide" style="margin:0">Workflows and dependencies</h2>
        ${fld('trusted_owners', 'Action owners trusted like GitHub', s.trusted_owners, '', 'my-org')}${sel('pin_dev', 'Development dependencies', [['0', 'May use ranges'], ['1', 'Must be pinned too']], String(s.pin_dev || 0))}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Licences</h2>
        ${fld('deny_licenses', 'Not allowed (SPDX ids, * allowed)', s.deny_licenses, '', 'AGPL-*, SSPL-*')}${fld('allow_licenses', 'Allowed (empty = all but the denied)', s.allow_licenses, '', 'MIT, Apache-2.0, BSD-*')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Repository</h2>
        ${fld('min_reviews', 'Reviews required at least', s.min_reviews, 'type="number" min="0" max="6" step="1"')}${fld('need_checks', 'Checks that must be required', s.need_checks, '', 'test, Pipeline guard')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Fix within (days)</h2>
        ${fld('sla_critical', 'Critical', s.sla_critical, 'type="number" min="1" step="1"')}${fld('sla_high', 'High', s.sla_high, 'type="number" min="1" step="1"')}${fld('sla_medium', 'Medium', s.sla_medium, 'type="number" min="1" step="1"')}${fld('sla_low', 'Low', s.sla_low, 'type="number" min="1" step="1"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Pipeline guard</h2>
        ${sel('fail_level', 'Fail the check on', [['warn', 'Anything to fix'], ['bad', 'Serious findings only']], s.fail_level)}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk. Keys and tokens never go here.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Workflows are read as text: what a step really does at run time is not checked.</li><li>Licence families are a guide, not legal advice - what a licence asks of you depends on how you ship.</li><li>Lookalike names are compared with a short list of well-known packages: a near miss is a reason to look.</li><li>Repository settings are what the API answered; rulesets can add more rules.</li><li>Fix times are counted in calendar days from the dates you give.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs, installs or changes anything in your pipelines or repositories.</li><li>Takes keys or tokens - a pasted key is refused.</li><li>Follows anything written inside your workflows, SBOMs or manifests: they are data.</li></ul></section>`;
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
      if (kind === 'workflows') await go('workflows', {text: S(fd.get('text')), inputs: pick(['trusted_owners'])});
      else if (kind === 'sbom') await go('sbom', {text: S(fd.get('text')), inputs: pick(['deny', 'allow'])});
      else if (kind === 'deps') await go('deps', {text: S(fd.get('text')), inputs: pick(['pin_dev'])});
      else if (kind === 'repo') await go('repo', {text: S(fd.get('text')), inputs: pick(['min_reviews', 'need_checks'])});
      else if (kind === 'metrics') await go('metrics', {text: S(fd.get('text')), inputs: pick(['today'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['trusted_owners', 'deny_licenses', 'allow_licenses', 'pin_dev', 'min_reviews', 'need_checks', 'sla_critical', 'sla_high', 'sla_medium', 'sla_low', 'fail_level', 'runner'];


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
    const box = $('#dsoFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dsodesk/chat'); ST.chat = r.id; }
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


