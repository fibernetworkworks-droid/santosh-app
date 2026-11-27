/* IT ADMIN DESK - the IT Admin employee's own section, like the finance desks (owner: "IT Admin same as finance desks"). A thin top
   bar, then the IT Admin chat (its own conversation, kind 'itadmin') beside the desk's pages: Today, Licences & spend, People &
   access, Changes, Guides & questions, Settings. The pages call /api/itdesk/do/<part>, which runs the IT Admin engine. Hoola never
   asks for a password, never creates a user or resets a password by API, and changes access only on her tap. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['licences', 'Licences & spend'], ['people', 'People & access'], ['changes', 'Changes'], ['guides', 'Guides & questions'],
    ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me this week?', 'Where am I wasting money on IT?', 'Summarise our IT for the team'],
    licences: ['Which licences renew next month?', 'Are we paying for unused seats?', 'Add our Microsoft 365 plan'],
    people: ['Someone joins on Monday - set them up', 'Ravi is leaving on Friday', 'Who has admin access?'],
    changes: ['What happens if I turn off this account?', 'Which changes are still to do?', 'Remove admin rights we do not need'],
    guides: ['Write a guide for the office Wi-Fi', 'What do staff ask most?', 'How do I set up email on a phone?'],
    settings: ['How do I link Google Workspace?', 'What permissions does Microsoft 365 need?', 'What good IT practices should I follow?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', pid: '', gid: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.itdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.itdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'it_admin', name: ((K().settings || {}).org_name) || 'Your office IT'} : null;
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
  const run = (part, a) => api('POST', '/api/itdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/itdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your IT Admin is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="itHire">Hire IT Admin</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#itHire').onclick = async () => { try { await api('POST', '/api/employees/it_admin/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">IT Admin</div><div class="sd-site" id="itSite"></div></div>
          <span id="itState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="IT Admin chat">
          <div class="sd-chathead"><div class="t"><b>IT Admin chat</b><span>Ask about a licence, a renewal, someone joining or leaving, or a staff IT question - or drop an invoice or user list here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="itFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="itPick" multiple hidden accept="image/*,.pdf,.csv,.xlsx,.txt,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="IT Admin desk" id="sdTabs"></nav>
          <div id="itPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola never asks for a password and changes access only on your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a licence, a person or access…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#itPick').click()});
    $('#itPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.itdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.itdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/itdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#itPage').addEventListener('click', onPageClick);
    $('#itPage').addEventListener('submit', onSubmit);
    $('#itPage').addEventListener('change', onChange);
    $('#itPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#itState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), st = k.settings || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : ((k.day || {}).waiting || []).length ? ['warn', 'Waiting for your tap'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Looking after it'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#itSite').textContent = [st.org_name, pl((k.licences || []).length, 'licence'), pl((k.people || []).length, 'person', 'people'), st.country || 'IN'].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), d = k.day || {};
    const n = {changes: ((d.waiting || []).length + (d.approved || []).length) || '', licences: ((d.renewals || {}).licences || []).length || '',
      people: (((k.access_stats || {}).leavers_active || 0) + (d.due_checklists || []).length) || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/itdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#itPage'); if (!box) return;
    const fn = {today: pToday, licences: pLicences, people: pPeople, changes: pChanges, guides: pGuides, settings: pSettings}[ST.tab] || pToday;
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
  const CS = {INR: '₹', USD: '$', EUR: '€', GBP: '£', SGD: 'S$', AUD: 'A$', CAD: 'C$', JPY: '¥', AED: 'AED ', ZAR: 'R ', NGN: '₦', KES: 'KSh ', BRL: 'R$', MYR: 'RM ', SAR: 'SAR '};
  const mon = v => (v === null || v === undefined || v === '') ? '—' : (CS[K().money_unit] || (K().money_unit || 'INR') + ' ') + Math.round(Number(v)).toLocaleString();
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const CST = {waiting: ['Waiting for your tap', 'warn'], approved: ['Approved - do it in the console', 'v'], done: ['Done', 'ok'], rejected: ['Refused', ''], failed: ['Failed', 'bad'], stale: ['Old', '']};
  const PST = {active: ['Active', 'ok'], joining: ['Joining', 'v'], leaving: ['Leaving', 'warn'], left: ['Left', '']};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const ppl = () => K().people || [];
  const personOpts = sel => ppl().map(p => `<option value="${esc(p.id)}"${p.id === sel ? ' selected' : ''}>${esc(p.name)}</option>`).join('');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), sp = k.spend || {}, ac = k.access_stats || {}, d = k.day || {}, ren = (d.renewals || {}).licences || [];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order: nothing renews soon, no change waiting, no leaver with open access.';
    const tiles = [
      `<div class="k"><div class="l">IT spend a year</div><div class="v">${esc(mon(sp.year))}</div><div class="s">${sp.per_person ? esc(mon(sp.per_person)) + ' a person' : 'from your prices'}</div></div>`,
      `<div class="k${sp.waste ? ' low bad' : ''}"><div class="l">Unused seats</div><div class="v">${esc(mon(sp.waste || 0))}</div><div class="s">a year you could save</div></div>`,
      `<div class="k${ren.some(l => l.days_left <= 7) ? ' low bad' : ''}"><div class="l">Renewing in 30 days</div><div class="v">${esc(num(ren.length))}</div><div class="s">${sp.next_90 ? esc(mon(sp.next_90)) + ' due in 90 days' : 'nothing due'}</div></div>`,
      `<div class="k${(d.waiting || []).length ? ' low bad' : ''}"><div class="l">Changes waiting</div><div class="v">${esc(num((d.waiting || []).length))}</div><div class="s">only your tap changes access</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Access at a glance</h2>
          <div class="it-mini">${[['Active accesses', ac.active], ['Admin accesses', ac.admins], ['Admins without 2-step', ac.admins_no_mfa, 1], ['Open for leavers', ac.leavers_active, 1], ['Shared logins', ac.shared], ['Never reviewed', ac.never_reviewed]].map(([l, v, bad]) => `<div><span class="mut">${esc(l)}</span><b class="${bad && v ? 'cs-neg' : ''}">${esc(num(v || 0))}</b></div>`).join('')}</div>
          ${(ac.by_system || []).length ? bars(ac.by_system.map(([n, v]) => [n, v, 'mk-b']), num, 'Accesses by system') : ''}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Spend by kind</h2><div class="r"><button class="btn soft sm" type="button" data-go="licences">Open</button></div></div>
          ${(sp.by_kind || []).length ? bars(sp.by_kind.map(([n, v]) => [n, v, 'mk-b']), mon, 'Yearly spend by kind') : empty('Add a price to your licences to see the spend.')}
          ${sp.unpriced ? `<p class="cs-note">${esc(pl(sp.unpriced, 'licence'))} without a price - not counted.</p>` : ''}</section>
        <section class="card"><h2 class="md-h2">Coming up</h2>${ren.map(l => `<div class="cs-row"><span style="flex:1"><b>${esc(l.name)}</b> <span class="mut">${esc(l.renews_on)}${l.auto_renew === false ? ' · auto-renew off' : l.auto_renew === null ? ' · auto-renew not known' : ''}</span></span>${tag(l.days_left + ' days', l.days_left <= 7 ? 'bad' : 'warn')}</div>`).join('')
          + ((d.renewals || {}).devices || []).map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(x.name)}</b> <span class="mut">${esc(x.what)} · ${esc(x.tag)}</span></span>${tag(x.days_left + ' days', 'warn')}</div>`).join('') || empty('Nothing renews in the next 30 days.')}</section></div>
      ${(k.gaps || []).length ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">What staff keep asking</h2><div class="r"><button class="btn soft sm" type="button" data-go="guides">Write a guide</button></div></div>${k.gaps.slice(0, 6).map(g => `<div class="cs-row"><span style="flex:1">${esc(g.topic)}</span>${tag(g.count + 'x', g.count >= 3 ? 'warn' : '')}</div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- licences */
  function licForm(l) {
    l = l || {};
    const kinds = K().lic_kinds || {};
    return `<form class="${l.id ? '' : 'card'}" data-form="lic"${l.id ? ` data-id="${esc(l.id)}"` : ''}>${l.id ? '' : '<h2 class="md-h2">Add a licence or subscription</h2>'}<div class="md-form">
      <div class="md-field"><label for="itL1${esc(l.id || '')}">Name</label><input class="in" id="itL1${esc(l.id || '')}" name="name" maxlength="160" value="${esc(l.name || '')}" ${l.id ? '' : 'required'}></div>
      <div class="md-field"><label for="itL2${esc(l.id || '')}">Kind</label><select class="in" id="itL2${esc(l.id || '')}" name="kind"><option value="">Find it by the name</option>${Object.entries(kinds).map(([v, n]) => `<option value="${esc(v)}"${l.kind === v ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></div>
      <div class="md-field"><label for="itL3${esc(l.id || '')}">Vendor</label><input class="in" id="itL3${esc(l.id || '')}" name="vendor" maxlength="120" value="${esc(l.vendor || '')}"></div>
      <div class="md-field"><label for="itL4${esc(l.id || '')}">Plan</label><input class="in" id="itL4${esc(l.id || '')}" name="plan" maxlength="120" value="${esc(l.plan || '')}"></div>
      <div class="md-field"><label for="itL5${esc(l.id || '')}">Seats bought</label><input class="in" id="itL5${esc(l.id || '')}" name="seats_bought" inputmode="numeric" value="${esc(l.seats_bought ?? '')}"></div>
      <div class="md-field"><label for="itL6${esc(l.id || '')}">Seats used</label><input class="in" id="itL6${esc(l.id || '')}" name="seats_used" inputmode="numeric" value="${esc(l.seats_used ?? '')}"></div>
      <div class="md-field"><label for="itL7${esc(l.id || '')}">Price (${esc(K().money_unit || 'INR')})</label><input class="in" id="itL7${esc(l.id || '')}" name="cost" inputmode="decimal" value="${esc(l.cost ?? '')}"></div>
      <div class="md-field"><label for="itL8${esc(l.id || '')}">Per</label><select class="in" id="itL8${esc(l.id || '')}" name="cost_per">${['month', 'year', 'once'].map(v => `<option value="${v}"${(l.cost_per || 'year') === v ? ' selected' : ''}>${v}</option>`).join('')}</select></div>
      <div class="md-field"><label for="itL9${esc(l.id || '')}">Renews on</label><input class="in" id="itL9${esc(l.id || '')}" name="renews_on" type="date" value="${esc(l.renews_on || '')}"></div>
      <div class="md-field"><label for="itL10${esc(l.id || '')}">Auto-renew</label><select class="in" id="itL10${esc(l.id || '')}" name="auto_renew"><option value="">Not known</option><option value="on"${l.auto_renew === true ? ' selected' : ''}>On</option><option value="off"${l.auto_renew === false ? ' selected' : ''}>Off</option></select></div>
      <div class="md-field"><label for="itL11${esc(l.id || '')}">Who looks after it</label><input class="in" id="itL11${esc(l.id || '')}" name="owner" maxlength="80" value="${esc(l.owner || '')}"></div>
      <div class="md-field"><label for="itL12${esc(l.id || '')}">Managed from (account, never a password)</label><input class="in" id="itL12${esc(l.id || '')}" name="login_with" maxlength="120" value="${esc(l.login_with || '')}"></div>
      <label class="md-field wide it-chk"><input type="checkbox" name="per_seat"${l.per_seat ? ' checked' : ''}> The price is for each seat</label></div>
      <div class="md-acts"><span class="mut" style="font-size:13px">Your own numbers; Hoola never guesses a price or date.</span><button class="btn" type="submit">${l.id ? 'Save' : 'Add it'}</button></div></form>`;
  }
  function pLicences() {
    const k = K(), lic = k.licences || [], sp = k.spend || {};
    return `<div class="cs-head"><div><h1 class="sd-h">Licences &amp; spend</h1><p class="lead" style="margin-top:4px">Every licence and subscription: seats bought vs used, renewal dates with reminders at your windows, what unused seats cost, and your IT spend. Hoola never pays or renews anything.</p></div>
        <div class="r">${CAN() ? '<button class="btn soft sm" type="button" data-act="register_file">Register as Excel</button>' : ''}</div></div>
      <section class="cs-hero"><div class="top">${[['A year', mon(sp.year)], ['A month', mon(sp.month)], ['A person', sp.per_person ? mon(sp.per_person) : '—'], ['Due in 90 days', mon(sp.next_90 || 0)]].map(([l, v]) => `<div class="k"><div class="l">${esc(l)}</div><div class="v">${esc(v)}</div></div>`).join('')}</div></section>
      ${CAN() ? licForm() : ''}
      <section class="card"><h2 class="md-h2">Your licences <span class="mut">${esc(num(lic.length))}</span></h2>${lic.map(l => `<details class="qa-case" data-key="l:${esc(l.id)}"${ST.open.has('l:' + l.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(l.number)}</b> ${esc(l.name)} <span class="mut">${esc(l.kind_label)}${l.vendor ? ' · ' + esc(l.vendor) : ''}${l.yearly !== null && l.yearly !== undefined ? ' · ' + esc(mon(l.yearly)) + ' a year' : ''}${l.source !== 'manual' ? ' · from ' + esc(l.source) : ''}</span></span>
          ${l.seats_bought ? `<span class="it-seat" title="${esc(l.seats_used ?? '?')} of ${esc(l.seats_bought)} seats used"><i style="width:${Math.min(100, 100 * (l.seats_used || 0) / l.seats_bought).toFixed(0)}%"></i></span><span class="mut nw">${esc(l.seats_used ?? '?')}/${esc(l.seats_bought)}</span>` : ''}
          ${l.days_left !== null && l.days_left !== undefined ? tag(l.days_left < 0 ? 'Overdue' : l.days_left + ' days', l.days_left <= 7 ? 'bad' : l.days_left <= 30 ? 'warn' : '') : ''}</summary>
        <div class="qa-body">${l.waste ? `<p class="cs-neg" style="margin:0">${esc(l.waste.free)} seats unused${l.waste.rupees_year ? ' - about ' + esc(mon(l.waste.rupees_year)) + ' a year' : ''}.</p>` : ''}
          ${(l.history || []).length ? `<p class="mut" style="margin:6px 0 0;font-size:13px">Earlier renewals: ${esc(l.history.map(h => (h.on || '?') + (h.cost ? ' at ' + mon(h.cost) : '')).join(', '))}</p>` : ''}
          ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px"><button class="btn sm" type="button" data-renew="${esc(l.id)}">I renewed it</button><button class="btn soft sm" type="button" data-act="licence_remove" data-id="${esc(l.id)}">Remove from the list</button>${ask('Licence ' + l.name)}</div>${licForm(l)}` : ''}</div></details>`).join('') || empty('No licences yet.')}</section>
      <section class="card"><h2 class="md-h2">Spend by vendor</h2>${(sp.by_vendor || []).length ? bars(sp.by_vendor.map(([n, v]) => [n, v, 'mk-b']), mon, 'Yearly spend by vendor') : empty('Add prices to see it.')}
        ${sp.auto_unknown ? `<p class="cs-note">${esc(pl(sp.auto_unknown, 'renewal'))} where auto-renew is not known - set it so nothing lapses or renews by surprise.</p>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- people & access */
  function pPeople() {
    const k = K(), people = ppl(), sel = ST.pid && people.find(p => p.id === ST.pid), pv = sel ? lazyOut('p:' + sel.id, 'person_get', {id: sel.id}) : null;
    const acc = (k.access || []).filter(a => a.status === 'active'), rv = (k.reviews || []).find(r => r.status === 'open');
    const kinds = {joiner: 'Joining', mover: 'Changing role', leaver: 'Leaving'};
    return `<div><h1 class="sd-h">People &amp; access</h1><p class="lead">Who works here, which systems each person can get into (never a password), joiner / mover / leaver checklists, and access reviews. Turning access off is a change card for your tap.</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">People <span class="mut">${esc(num(people.length))}</span></h2>${people.map(p => `<div class="cs-row${sel && p.id === sel.id ? ' cy-sel' : ''}"><span style="flex:1"><b>${esc(p.name)}</b> <span class="mut">${esc([p.role, p.department, p.email].filter(Boolean).join(' · '))}</span></span>${tag((PST[p.status] || [cap(p.status || 'active')])[0], (PST[p.status] || ['', ''])[1])}<button class="btn soft sm" type="button" data-pid="${esc(p.id)}">Open</button></div>`).join('') || empty('Nobody yet.')}</section>
        ${CAN() ? `<form class="card" data-form="person"><h2 class="md-h2">Add a person</h2><div class="md-form"><div class="md-field"><label for="itP1">Name</label><input class="in" id="itP1" name="name" required maxlength="120"></div>
          <div class="md-field"><label for="itP2">Work email</label><input class="in" id="itP2" name="email" maxlength="160"></div><div class="md-field"><label for="itP3">Role</label><input class="in" id="itP3" name="role" maxlength="80"></div>
          <div class="md-field"><label for="itP4">Department</label><input class="in" id="itP4" name="department" maxlength="80"></div><div class="md-field"><label for="itP5">Starts on</label><input class="in" id="itP5" name="join_date" type="date"></div></div>
          <div class="md-acts"><span></span><button class="btn" type="submit">Add</button></div></form>` : ''}</div>
      ${sel ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(sel.name)}</h2><div class="r">${CAN() ? Object.entries(kinds).map(([kk, l]) => `<button class="btn soft sm" type="button" data-cl="${kk}" data-p="${esc(sel.id)}">${esc(l)}</button>`).join('') + (sel.status === 'left' ? `<button class="btn soft sm" type="button" data-act="forget_person" data-id="${esc(sel.id)}">Erase their data</button>` : '') : ''}${ask('Person ' + sel.name)}</div></div>
        ${pv === null ? '<p class="mut">Loading…</p>' : pv && pv.error ? `<p class="cs-neg">${esc(pv.error)}</p>` : pv ? `
          <div class="cr-sub">Access</div>${(pv.access || []).map(a => `<div class="cs-row"><span style="flex:1"><b>${esc(a.system)}</b> <span class="mut">${esc(a.account || '')} · ${esc(a.level)}${a.shared ? ' · shared' : ''}${a.last_login ? ' · last login ' + esc(a.last_login) : ''}</span></span>${a.mfa === 'no' ? tag('No 2-step', a.level !== 'user' ? 'bad' : 'warn') : a.mfa === 'yes' ? tag('2-step', 'ok') : ''}${tag(cap(a.status), a.status === 'active' ? '' : 'ok')}${CAN() && a.status === 'active' ? `<button class="btn soft sm" type="button" data-off="${esc(a.id)}">Turn off</button>` : ''}</div>`).join('') || empty('No access recorded.')}
          <div class="cr-sub" style="margin-top:12px">Devices (from the IT Helpdesk register)</div>${(pv.devices || []).map(x => `<div class="cs-row"><span style="flex:1">${esc(x.name)} <span class="mut">${esc(x.tag || '')} ${esc(x.serial || '')}</span></span></div>`).join('') || empty('None.')}
          ${(pv.checklists || []).map(c => `<div class="cr-sub" style="margin-top:12px">${esc(cap(c.kind))} checklist <span class="mut">${esc(c.done)} / ${esc(c.total)} · due ${esc(c.due || '-')}</span></div>${(c.items || []).map(i => `<label class="dv-item"><input type="checkbox" data-tick="${esc(c.id)}" data-item="${esc(i.id)}"${i.done ? ' checked' : ''}${CAN() && !i.change ? '' : ' disabled'}><span>${esc(i.text)}${i.change ? ' <span class="mut">(a change card - done when you tap it and finish it)</span>' : ''}</span></label>`).join('')}`).join('')}` : ''}
        ${CAN() ? `<form class="iv-add" data-form="access" data-p="${esc(sel.id)}"><input class="in" name="system" required maxlength="120" placeholder="System (Tally, Wi-Fi, Google Workspace)" aria-label="System"><input class="in" name="account" maxlength="120" placeholder="Account / username" aria-label="Account">
          <select class="in" name="level" aria-label="Level"><option value="user">User</option><option value="admin">Admin</option><option value="owner">Owner</option></select><select class="in" name="mfa" aria-label="2-step"><option value="">2-step not known</option><option value="yes">2-step on</option><option value="no">No 2-step</option></select><button class="btn soft" type="submit">Record access</button></form><p class="cs-note">Only THAT the access exists - never a password.</p>` : ''}</section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Access review</h2><div class="r">${CAN() && !rv ? '<button class="btn soft sm" type="button" data-act="review_start">Start a review</button>' : ''}</div></div>
        ${rv ? `<p class="mut" style="margin:0 0 6px">${esc(rv.number)}: ${esc(rv.decided)} of ${esc(rv.total)} decided. Keep or remove each access.</p>${rv.items.map(i => `<div class="cs-row"><span style="flex:1"><b>${esc(i.person || '?')}</b> ${esc(i.system)} <span class="mut">${esc(i.account || '')} · ${esc(i.level)}</span>${(i.flags || []).length ? `<div class="cs-neg" style="font-size:13px">${esc(i.flags.join('; '))}</div>` : ''}</span>${i.decision ? tag(cap(i.decision), i.decision === 'keep' ? 'ok' : 'warn') : CAN() ? `<button class="btn soft sm" type="button" data-rv="${esc(rv.id)}" data-a="${esc(i.id)}" data-d="keep">Keep</button><button class="btn soft sm" type="button" data-rv="${esc(rv.id)}" data-a="${esc(i.id)}" data-d="remove">Remove</button>` : ''}</div>`).join('')}
          ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">Remove makes a change card for your tap.</span><button class="btn sm" type="button" data-act="review_close" data-id="${esc(rv.id)}">Close the review</button></div>` : ''}`
        : `<p class="mut" style="margin:0">${esc(num(acc.length))} active accesses. Last review: ${esc(((k.settings || {}).last_review) || 'never')}. Every ${esc((k.settings || {}).review_months || 3)} months is a good rhythm.</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- changes */
  function pChanges() {
    const k = K(), ch = k.changes || [], waiting = ch.filter(c => c.status === 'waiting'), appr = ch.filter(c => c.status === 'approved'), rest = ch.filter(c => !['waiting', 'approved'].includes(c.status));
    const card = c => `<div class="pb-res${c.status === 'waiting' ? ' warn' : ''}" style="margin-top:10px"><div class="cs-head"><b>${esc(c.number)} · ${esc(c.kind_label)}: ${esc(c.target || c.system)}</b><div class="r">${tag((CST[c.status] || [c.status])[0], (CST[c.status] || ['', ''])[1])}</div></div>
      ${c.what ? `<p style="margin:0">${esc(c.what)}</p>` : ''}<div class="dv-grid"><div><span class="mut">${c.by_api ? 'Your tap runs it through the official admin API' : 'Steps in your console after your yes'}</span><ol>${(c.steps || []).map(s => `<li>${esc(s)}</li>`).join('')}</ol></div>
        <div><span class="mut">What it means</span><p style="margin:4px 0 0">${esc(c.risk || '-')}</p><span class="mut" style="display:block;margin-top:8px">To undo</span><p style="margin:4px 0 0">${esc(c.undo || '-')}</p></div></div>
      ${CAN() && c.status === 'waiting' ? `<form class="iv-add" data-form="decide" data-id="${esc(c.id)}" data-h="${esc(c.hash)}"><button class="btn soft" type="submit" data-yes="0">No</button><button class="btn" type="submit" data-yes="1">Yes, do it</button></form>` : ''}
      ${CAN() && c.status === 'approved' ? `<div class="md-acts" style="justify-content:flex-start"><button class="btn sm" type="button" data-cdone="${esc(c.id)}">I did it in the console</button></div>` : ''}</div>`;
    return `<div><h1 class="sd-h">Changes</h1><p class="lead">Turning an account off or on, licences, admin rights, a shared password - each is a card with its steps, what it means and how to undo it. Nothing changes until you tap. Hoola never creates a user or resets a password by API.</p></div>
      ${waiting.length ? `<section class="card"><h2 class="md-h2">Waiting for your tap <span class="mut">${esc(num(waiting.length))}</span></h2>${waiting.map(card).join('')}</section>` : ''}
      ${appr.length ? `<section class="card"><h2 class="md-h2">Approved - still to do in the console</h2>${appr.map(card).join('')}</section>` : ''}
      ${CAN() ? `<form class="card" data-form="change"><h2 class="md-h2">Ask for a change</h2><div class="md-form"><div class="md-field"><label for="itC1">What</label><select class="in" id="itC1" name="kind">${Object.entries(k.change_kinds || {}).map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="itC2">Person</label><select class="in" id="itC2" name="person"><option value="">-</option>${personOpts()}</select></div>
        <div class="md-field"><label for="itC3">System</label><input class="in" id="itC3" name="system" maxlength="120"></div><div class="md-field"><label for="itC4">Account</label><input class="in" id="itC4" name="target" maxlength="160"></div>
        <div class="md-field wide"><label for="itC5">Why</label><input class="in" id="itC5" name="what" maxlength="400"></div></div><div class="md-acts"><span class="mut" style="font-size:13px">Makes a card only.</span><button class="btn" type="submit">Make the card</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">History</h2>${rest.map(c => `<div class="cs-row"><span style="flex:1"><b>${esc(c.number)}</b> ${esc(c.kind_label)}: ${esc(c.target || c.system)} <span class="mut">${esc(ago(c.created_at))}${c.reason ? ' · ' + esc(c.reason) : ''}</span></span>${tag((CST[c.status] || [c.status])[0], (CST[c.status] || ['', ''])[1])}</div>`).join('') || empty('None yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- guides */
  function pGuides() {
    const k = K(), gs = k.guides || [], sel = ST.gid && gs.find(g => g.id === ST.gid), gv = sel ? lazyOut('g:' + sel.id, 'guide_get', {id: sel.id}) : null, a = ST.out.ask;
    return `<div><h1 class="sd-h">Guides &amp; questions</h1><p class="lead">Short how-to guides for your staff, written only from your own words (a step Hoola cannot trace to them is dropped). Staff questions are answered from the published guides, else they become an IT Helpdesk ticket.</p></div>
      <div class="md-2" style="align-items:start">
        ${CAN() ? `<form class="card" data-form="guide"><h2 class="md-h2">Write a guide</h2><input class="in" name="topic" required maxlength="200" placeholder="Topic (set up office email on a new PC)" aria-label="Topic" style="width:100%"><textarea class="in" name="words" rows="5" maxlength="6000" placeholder="Describe the steps in your own words" style="width:100%;margin-top:8px"></textarea>
          <div class="md-acts"><span class="mut" style="font-size:13px">A password written here is removed.</span><button class="btn" type="submit">Write it</button></div></form>` : ''}
        <form class="card" data-form="ask"><h2 class="md-h2">A staff question</h2><input class="in" name="person" maxlength="80" placeholder="Who is asking" aria-label="Who" style="width:100%"><textarea class="in" name="text" rows="3" maxlength="1000" placeholder="Their question, in their words" style="width:100%;margin-top:8px"></textarea>
          <div class="md-acts"><span></span><button class="btn soft" type="submit">Answer it</button></div>
          ${a ? `<div class="pb-res" style="margin-top:10px">${tag(cap(String(a.answer).replace('_', ' ')), a.answer === 'guide' ? 'ok' : a.answer === 'refused' ? 'bad' : 'warn')}<p style="margin:6px 0 0;white-space:pre-line">${esc(a.say || '')}</p></div>` : ''}</form></div>
      <section class="card"><h2 class="md-h2">Guides <span class="mut">${esc(num(gs.length))}</span></h2>${gs.map(g => `<div class="cs-row${sel && g.id === sel.id ? ' cy-sel' : ''}"><span style="flex:1"><b>${esc(g.number)}</b> ${esc(g.title)} <span class="mut">v${esc(g.version)} · asked ${esc(g.asked)} · helped ${esc(g.helped)}${g.not_helped ? ' · did not help ' + esc(g.not_helped) : ''}</span></span>${tag(cap(g.status), g.status === 'published' ? 'ok' : 'warn')}<button class="btn soft sm" type="button" data-gid="${esc(g.id)}">Open</button></div>`).join('') || empty('No guides yet.')}</section>
      ${sel ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(sel.number)} · ${esc(sel.title)}</h2><div class="r">${CAN() && sel.status !== 'published' ? `<button class="btn sm" type="button" data-act="guide_publish" data-id="${esc(sel.id)}">Publish to staff</button>` : ''}${CAN() ? `<button class="btn soft sm" type="button" data-act="guide_file" data-id="${esc(sel.id)}">As Word</button>` : ''}</div></div>
        ${gv === null ? '<p class="mut">Loading…</p>' : gv && gv.error ? `<p class="cs-neg">${esc(gv.error)}</p>` : gv ? `<ol class="cy-pb">${(gv.steps || []).map((s, i) => `<li>${esc(s.text || s)}${CAN() ? ` <button class="ib" type="button" aria-label="Remove step" data-gstep="${esc(sel.id)}" data-n="${i + 1}">×</button>` : ''}</li>`).join('')}</ol>
          ${(gv.versions || []).length ? `<p class="cs-note">Earlier versions: ${gv.versions.map(v => CAN() ? `<button class="btn soft sm" type="button" data-grest="${esc(sel.id)}" data-v="${esc(v.version)}">v${esc(v.version)}</button>` : 'v' + esc(v.version)).join(' ')}</p>` : ''}` : ''}</section>` : ''}
      ${(k.gaps || []).length ? `<section class="card"><h2 class="md-h2">Questions without a guide (30 days)</h2>${k.gaps.map(g => `<div class="cs-row"><span style="flex:1">${esc(g.topic)} <span class="mut">${esc((g.examples || []).slice(1).join(' / '))}</span></span>${tag(g.count + 'x', g.count >= 3 ? 'warn' : '')}</div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, cn = k.connections || {}, g = cn.google, m = cn.microsoft;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your office, money unit and country (for the good-practice list), what every new person gets, when renewals remind you, and the read-only links to Google Workspace and Microsoft 365.</p></div>
      <form class="card" data-form="itset"><h2 class="md-h2">Your office</h2><div class="md-form">
        <div class="md-field"><label for="itS1">Organisation</label><input class="in" id="itS1" name="org_name" maxlength="160" value="${esc(s.org_name || '')}"></div>
        <div class="md-field"><label for="itS2">Email domain</label><input class="in" id="itS2" name="domain" maxlength="120" value="${esc(s.domain || '')}"></div>
        <div class="md-field"><label for="itS3">Country (two letters)</label><input class="in" id="itS3" name="country" maxlength="2" value="${esc(s.country || '')}" placeholder="IN"></div>
        <div class="md-field"><label for="itS4">Money unit (three letters)</label><input class="in" id="itS4" name="currency" maxlength="3" value="${esc(s.currency || '')}" placeholder="INR"></div>
        <div class="md-field"><label for="itS5">Who holds the admin consoles</label><input class="in" id="itS5" name="admin_name" maxlength="80" value="${esc(s.admin_name || '')}"></div>
        <div class="md-field"><label for="itS6">Morning note at</label><input class="in" id="itS6" name="morning_time" type="time" value="${esc(s.morning_time || '09:45')}"></div>
        <div class="md-field wide"><label for="itS7">Every new person gets (comma separated)</label><input class="in" id="itS7" name="standard_systems" maxlength="600" value="${esc((s.standard_systems || []).join(', '))}"></div>
        <div class="md-field"><label for="itS8">Renewal reminders (days before)</label><input class="in" id="itS8" name="windows" maxlength="60" value="${esc((s.windows || []).join(', '))}"></div>
        <div class="md-field"><label for="itS9">Access review every (months)</label><input class="in" id="itS9" name="review_months" inputmode="numeric" value="${esc(s.review_months || 3)}"></div>
        <div class="md-field wide"><label for="itS10">Your IT rules</label><textarea class="in" id="itS10" name="rules" rows="3" maxlength="600">${esc(s.rules || '')}</textarea></div></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <form class="card" data-form="practices"><h2 class="md-h2">Good practice</h2>${(s.practices || []).map(p => `<label class="dv-item"><input type="checkbox" name="${esc(p.id)}"${p.done ? ' checked' : ''}${CAN() ? '' : ' disabled'}><span>${esc(p.text)} <span class="mut">${esc(p.why)}</span>${p.checked === false ? ' ' + tag('Check this', 'warn') : ''}</span></label>`).join('')}
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Tick what you already do.</span><button class="btn soft" type="submit">Save</button></div>' : ''}</form>
      <section class="card"><h2 class="md-h2">Admin consoles (read with your consent)</h2>
        <div class="it-conn"><div style="flex:1;min-width:0"><b>Google Workspace</b><div class="mut" style="font-size:13px">${g ? `${esc(g.account || '')} · ${esc(g.mode)} · ${esc(g.status)}${g.last_sync ? ' · read ' + esc(g.last_sync) : ''}${g.last_error ? ' · ' + esc(g.last_error) : ''}` : cn.google_ready ? 'Not linked. Linking opens Google to give read-only consent.' : 'Google sign-in is not set up on this server.'}</div></div>
          ${CAN() ? (g ? `<button class="btn soft sm" type="button" data-sync="google">Read now</button><button class="btn soft sm" type="button" data-forget="google">Unlink</button>` : cn.google_ready ? `<button class="btn soft sm" type="button" data-glink="read">Link (read only)</button><button class="btn soft sm" type="button" data-glink="manage">Link (read + changes on tap)</button>` : '') : ''}</div>
        <div class="it-conn"><div style="flex:1;min-width:0"><b>Microsoft 365</b><div class="mut" style="font-size:13px">${m ? `${esc(m.mode)} · ${esc(m.status)}${m.last_sync ? ' · read ' + esc(m.last_sync) : ''}${m.last_error ? ' · ' + esc(m.last_error) : ''}` : 'Not linked. Uses your own Entra app (directory ID, client ID and secret).'}</div></div>
          ${CAN() && m ? `<button class="btn soft sm" type="button" data-sync="microsoft">Read now</button><button class="btn soft sm" type="button" data-forget="microsoft">Unlink</button>` : ''}</div>
        ${CAN() && !m ? `<form class="iv-add" data-form="ms"><input class="in" name="directory_id" required maxlength="80" placeholder="Directory (tenant) ID" aria-label="Directory ID"><input class="in" name="client_id" required maxlength="80" placeholder="Client ID" aria-label="Client ID"><input class="in" name="client_secret" type="password" autocomplete="off" required maxlength="200" placeholder="Client secret" aria-label="Client secret"><select class="in" name="mode" aria-label="Mode"><option value="read">Read only</option><option value="manage">Read + changes on tap</option></select><button class="btn soft" type="submit">Link</button></form>
          <p class="cs-note">The secret is sealed on arrival and never shown again. Permissions: ${esc(((cn.ms_permissions || {}).read || []).join(', '))}.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Ask for, write or keep a password, PIN or OTP', 'Create a user or reset a password by API', 'Change access or settings without your tap', 'Pay or renew anything', 'Guess a price or a date'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const dropP = () => { for (const k of Object.keys(ST.out)) if (k.startsWith('p:') || k.startsWith('g:')) delete ST.out[k]; };
  const numOrNull = v => (v === '' || v === null || v === undefined) ? null : Number(v);
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const pi = t.closest('[data-pid]'); if (pi) { ST.pid = pi.dataset.pid; delete ST.out['p:' + ST.pid]; showPage(true); return; }
    const gi = t.closest('[data-gid]'); if (gi) { ST.gid = gi.dataset.gid; delete ST.out['g:' + ST.gid]; showPage(true); return; }
    try {
      const rn = t.closest('[data-renew]'); if (rn) { const on = prompt('Next renewal date (YYYY-MM-DD) - blank = one period later'); if (on === null) return;
        const cost = prompt('The price you paid (blank = same as before)'); if (cost === null) return;
        await changed((await run('renewed', {id: rn.dataset.renew, renews_on: on, cost})).say); return; }
      const cl = t.closest('[data-cl]'); if (cl) { let new_role = ''; if (cl.dataset.cl === 'mover') { new_role = prompt('The new role') || ''; if (!new_role) return; }
        const when = prompt(cl.dataset.cl === 'leaver' ? 'Last working day (YYYY-MM-DD) - blank = today' : 'Date (YYYY-MM-DD) - blank = today'); if (when === null) return;
        const r = await run('checklist', {person: cl.dataset.p, kind: cl.dataset.cl, when, new_role}); dropP(); await changed(r.say); return; }
      const off = t.closest('[data-off]'); if (off) { const r = await run('change', {kind: 'access_remove', access: off.dataset.off}); dropP(); await changed(r.say || 'Card made - it waits for your tap on Changes.'); return; }
      const rv = t.closest('[data-rv]'); if (rv) { await changed((await run('review_item', {review: rv.dataset.rv, access: rv.dataset.a, decision: rv.dataset.d})).say || 'Saved.'); return; }
      const cd = t.closest('[data-cdone]'); if (cd) { const note = prompt('What did you do? (optional)') || ''; dropP(); await changed((await run('change_done', {change: cd.dataset.cdone, ok: true, note})).say || 'Done.'); return; }
      const gs = t.closest('[data-gstep]'); if (gs) { if (!confirm('Remove this step?')) return; await run('guide_step', {id: gs.dataset.gstep, n: Number(gs.dataset.n), remove: true}); dropP(); await changed('Step removed (a new version).'); return; }
      const gr = t.closest('[data-grest]'); if (gr) { await run('guide_restore', {id: gr.dataset.grest, version: Number(gr.dataset.v)}); dropP(); await changed('Brought back as a new version.'); return; }
      const gl = t.closest('[data-glink]'); if (gl) { const r = await run('google_start', {mode: gl.dataset.glink}); window.open(r.url, '_blank', 'noopener'); toast('Give the consent in the Google tab, then come back and refresh.'); return; }
      const sy = t.closest('[data-sync]'); if (sy) { toast('Reading…'); await changed((await run('sync', {provider: sy.dataset.sync})).say || 'Read.'); return; }
      const fg = t.closest('[data-forget]'); if (fg) { if (!confirm('Unlink this console? Hoola keeps no token after this.')) return; await changed((await run('conn_forget', {provider: fg.dataset.forget})).say); return; }
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act, d = a.dataset, say = r => (r && r.say) || 'Done.';
        if (act === 'licence_remove' && !confirm('Remove it from the list? Nothing changes with the vendor.')) return;
        if (act === 'forget_person' && !confirm('Erase this person\'s personal data? Counts stay.')) return;
        a.disabled = true;
        if (act === 'register_file') await changed(say(await run('register_file')));
        else if (act === 'review_start' || act === 'review_close') await changed(say(await run(act, {review: d.id})));
        else if (act === 'guide_publish' || act === 'guide_file') { dropP(); await changed(say(await run(act, {id: d.id}))); }
        else { dropP(); await changed(say(await run(act, {id: d.id}))); }
        return;
      }
    } catch (err2) { toast(err2.message, true); const a = t.closest('[data-act]'); if (a) a.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    try {
      if (el.dataset.tick) { await run('check_item', {checklist: el.dataset.tick, item: el.dataset.item, done: el.checked}); dropP(); await changed(''); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'lic') { const a = {name: g('name'), vendor: g('vendor'), plan: g('plan'), owner: g('owner'), login_with: g('login_with'), cost_per: g('cost_per'), per_seat: fd.get('per_seat') === 'on'};
        if (g('kind')) a.kind = g('kind'); for (const n of ['seats_bought', 'seats_used']) if (g(n) !== '') a[n] = Number(g(n)); if (g('cost') !== '') a.cost = Number(g('cost'));
        if (g('renews_on')) a.renews_on = g('renews_on'); if (g('auto_renew')) a.auto_renew = g('auto_renew') === 'on';
        if (form.dataset.id) a.id = form.dataset.id; const r = await run('licence_save', a); if (form.dataset.id) await changed(r.say); else await done(r.say); }
      else if (kind === 'person') { const r = await run('person_save', {name: g('name'), email: g('email'), role: g('role'), department: g('department'), join_date: g('join_date')}); ST.pid = (r.person || {}).id || ST.pid; await done(r.say || 'Added.'); }
      else if (kind === 'access') { const a = {person: form.dataset.p, system: g('system'), account: g('account'), level: g('level')}; if (g('mfa')) a.mfa = g('mfa');
        const r = await run('access_save', a); dropP(); await done(r.say || 'Recorded.'); }
      else if (kind === 'decide') { const yes = btn && btn.dataset.yes === '1'; if (yes && !confirm('Make this change?')) return;
        let reason = ''; if (!yes) reason = prompt('Why not? (optional)') || '';
        const r = await run('decide', {change: form.dataset.id, yes, hash: form.dataset.h, reason}); dropP(); await changed(r.say || (yes ? 'Approved.' : 'Refused.')); }
      else if (kind === 'change') { const r = await run('change', {kind: g('kind'), person: g('person'), system: g('system'), target: g('target'), what: g('what')}); await done(r.say || 'Card made.'); }
      else if (kind === 'guide') { const r = await run('guide_write', {topic: g('topic'), words: S(fd.get('words'))}); ST.gid = (r.guide || {}).id || ''; dropP(); await done(r.say || 'Written - check it, then publish.'); }
      else if (kind === 'ask') { if (!g('text')) throw new Error('Type the question.'); ST.out.ask = await run('ask', {text: S(fd.get('text')), person: g('person')}); await done(''); }
      else if (kind === 'itset') { await run('settings', {org_name: g('org_name'), domain: g('domain'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase(), admin_name: g('admin_name'),
          morning_time: g('morning_time'), standard_systems: g('standard_systems'), windows: g('windows').split(',').map(x => Number(x.trim())).filter(x => !isNaN(x)), review_months: Number(g('review_months') || 3), rules: g('rules')}); await changed('Saved.'); }
      else if (kind === 'practices') { const pr = {}; form.querySelectorAll('input[type=checkbox]').forEach(c => { pr[c.name] = c.checked; }); await run('settings', {practices: pr}); await changed('Saved.'); }
      else if (kind === 'ms') { const r = await run('ms_save', {directory_id: g('directory_id'), client_id: g('client_id'), client_secret: S(fd.get('client_secret')), mode: g('mode')}); await done(r.say || 'Linked.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn) btn.disabled = false; }
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
    const box = $('#itFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/itdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'it' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


