/* CYBER DESK - the Cyber security employee's own section, like the finance desks (owner: "100 % Cyber security same as finance desks").
   A thin top bar, then the Cyber chat (its own conversation, kind 'cyber') beside the desk's pages: Today, Alerts, Checks, Attack
   surface, Incidents, Programme, Settings. The pages call /api/cydesk/do/<part>, which runs the Cyber Suraksha engine and the programme.
   Hoola never scans anyone's systems, never opens a suspicious link, never uploads her file, and blocks / wipes only on her tap. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['alerts', 'Alerts'], ['checks', 'Checks'], ['surface', 'Attack surface'], ['incidents', 'Incidents'],
    ['programme', 'Programme'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me today?', 'How secure is my business?', 'Summarise this week for my team'],
    alerts: ['Which alert matters most?', 'Is this login attack serious?', 'What should I block?'],
    checks: ['Is this mail fake?', 'Someone clicked a link - what now?', 'Is it safe to share this config?'],
    surface: ['How do I fix my DMARC?', 'Which software needs updating first?', 'Were our emails in a breach?'],
    incidents: ['Who do I have to tell, and by when?', 'Walk me through the ransomware playbook', 'Write the incident summary'],
    programme: ['What are my three biggest gaps?', 'Which vendor is the riskiest?', 'Plan a phishing drill'],
    settings: ['Which keys does Hoola need?', 'What do my country\'s breach rules say?', 'What security rules should I set?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', af: 'matters', inc: '', pb: '', ps: 'controls', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.cydesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.cydesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'cyber', name: 'Your security'} : null;
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
  const run = (part, a) => api('POST', '/api/cydesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/cydesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Cyber security is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="cyHire">Hire Cyber security</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#cyHire').onclick = async () => { try { await api('POST', '/api/employees/cyber/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Cyber security</div><div class="sd-site" id="cySite"></div></div>
          <span id="cyState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Cyber chat">
          <div class="sd-chathead"><div class="t"><b>Cyber chat</b><span>Ask about an alert, a mail, a link or an incident - or drop alerts, a log or a suspicious mail here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="cyFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="cyPick" multiple hidden accept="image/*,.txt,.log,.csv,.json,.eml,.msg,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Cyber desk" id="sdTabs"></nav>
          <div id="cyPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola never scans anyone, never opens a suspicious link, and blocks or wipes only on your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about an alert, a mail or an incident…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#cyPick').click()});
    $('#cyPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.cydesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.cydesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/cydesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#cyPage').addEventListener('click', onPageClick);
    $('#cyPage').addEventListener('submit', onSubmit);
    $('#cyPage').addEventListener('change', onChange);
    $('#cyPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#cyState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), st = k.settings || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : (k.waiting || []).length ? ['warn', 'Waiting for your tap'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Watching'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#cySite').textContent = [k.score !== null && k.score !== undefined ? 'Score ' + k.score : '', pl((k.domains || []).length, 'domain'), st.country || 'IN'].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {alerts: (k.matters || []).length || '', incidents: ((k.incidents || []).length + (k.waiting || []).length) || '',
      surface: (k.advisories || []).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/cydesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#cyPage'); if (!box) return;
    const fn = {today: pToday, alerts: pAlerts, checks: pChecks, surface: pSurface, incidents: pIncidents, programme: pProgramme, settings: pSettings}[ST.tab] || pToday;
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
  const pct = v => (v === null || v === undefined) ? '—' : `${num(Math.round(Number(v)))}%`;
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const LVL = {matters: ['Matters', 'bad'], watch: ['Watch', 'warn'], noise: ['Noise', '']};
  const VER = {likely_phish: ['Looks like fraud', 'bad'], malicious: ['Dangerous', 'bad'], suspicious: ['Suspicious', 'warn'], unclear: ['No clear signs', ''], clean: ['No signs found', 'ok']};
  const FL = {bad: ['Bad', 'stop'], warn: ['Look at this', 'check'], info: ['Note', ''], ok: ['Fine', '']};
  const BAND = {high: 'bad', medium: 'warn', low: 'ok'};
  const ACT = {waiting: 'warn', approved: 'v', done: 'ok', rejected: '', failed: 'bad', stale: '', undone: ''};
  const NST = {open: ['To do', 'warn'], overdue: ['Overdue', 'bad'], done: ['Told', 'ok'], na: ['Not needed', '']};
  const ver = v => tag((VER[v] || [cap(S(v).replace(/_/g, ' ')), ''])[0], (VER[v] || ['', ''])[1]);
  const flags = fs => (fs || []).map(f => `<div class="rk-flag ${(FL[f.level] || ['', ''])[1]}"><span>${esc((FL[f.level] || [cap(f.level || '')])[0])}</span><div>${esc(f.text || f.say || '')}${f.fix ? `<div class="mut" style="font-size:13px">${esc(f.fix)}</div>` : ''}</div></div>`).join('');
  const P = () => K().programme || {};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const scoreRing = (v, label) => { const r = 34, c = 2 * Math.PI * r, f = v === null || v === undefined ? 0 : Math.max(0, Math.min(100, v)) / 100;
    return `<svg class="cy-ring" viewBox="0 0 84 84" role="img" aria-label="${esc(label)}: ${v === null || v === undefined ? 'not known' : v + ' of 100'}"><circle cx="42" cy="42" r="${r}" class="bg"/><circle cx="42" cy="42" r="${r}" class="fg ${v >= 75 ? 'ok' : v >= 50 ? 'warn' : 'bad'}" stroke-dasharray="${(c * f).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 42 42)"/><text x="42" y="47" text-anchor="middle">${v === null || v === undefined ? '—' : esc(v)}</text></svg>`; };

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), pr = P(), parts = k.score_parts || [];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All quiet: no alert that matters, no open incident, nothing waiting for you.';
    const tiles = [
      `<div class="k${(k.matters || []).length ? ' low bad' : ''}"><div class="l">Alerts that matter</div><div class="v">${esc(num((k.matters || []).length))}</div><div class="s">${esc(num((k.watch || []).length))} to watch</div></div>`,
      `<div class="k${(k.incidents || []).length ? ' low bad' : ''}"><div class="l">Open incidents</div><div class="v">${esc(num((k.incidents || []).length))}</div><div class="s">${(k.notify || []).length ? esc(pl(k.notify.length, 'notice')) + ' to send' : 'no notice due'}</div></div>`,
      `<div class="k${(k.waiting || []).length ? ' low bad' : ''}"><div class="l">Waiting for your tap</div><div class="v">${esc(num((k.waiting || []).length))}</div><div class="s">block / wipe cards</div></div>`,
      `<div class="k${(k.advisories || []).some(a => a.exploited) ? ' low bad' : ''}"><div class="l">Software threats</div><div class="v">${esc(num((k.advisories || []).length))}</div><div class="s">${esc(num((k.advisories || []).filter(a => a.exploited).length))} being attacked</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Security score</h2><div class="cy-score">${scoreRing(k.score, 'Security score')}
          <div style="flex:1;min-width:0">${parts.length ? bars(parts.map(([n, v]) => [n, v || 0, v >= 75 ? 'cy-ok' : v >= 50 ? 'cy-warn' : 'cy-bad']), pct, 'Score parts') : empty('Answer the controls check, add a domain or run an access review to see your score.')}</div></div>
          <p class="cs-note">An average of what is known - controls, domains, 2-step coverage, training and the password policy. Not a certification.</p></section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Alerts by kind</h2><div class="r"><button class="btn soft sm" type="button" data-go="alerts">Open</button></div></div>
          ${(k.by_kind || []).length ? bars(k.by_kind.map(([n, v]) => [n, v, 'mk-b']), num, 'Open alerts by kind') : empty('No open alerts. Paste or upload alerts on the Alerts page.')}</section>
        <section class="card"><h2 class="md-h2">What attackers tried (MITRE ATT&amp;CK)</h2>
          ${(k.by_tactic || []).length ? bars(k.by_tactic.map(([n, v]) => [n, v, 'cy-warn']), num, 'Open alerts by ATT&CK tactic') : empty('Shows once alerts come in.')}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Controls by area (NIST CSF 2.0)</h2><div class="r"><button class="btn soft sm" type="button" data-go="programme">Open</button></div></div>
        ${Object.keys((pr.controls || {}).functions || {}).length ? bars(Object.entries(pr.controls.functions).filter(([, v]) => v !== null).map(([n, v]) => [n, v || 0, v >= 75 ? 'cy-ok' : v >= 50 ? 'cy-warn' : 'cy-bad']), pct, 'Controls by function') : empty('Answer the controls self-check in Programme.')}</section>`;
  }

  /* ---------------------------------------------------------------- alerts */
  function pAlerts() {
    const k = K(), f = ST.af || 'matters', all = k.open_alerts || [], rs = all.filter(a => !f || a.level === f), res = ST.out.intake;
    const one = a => `<details class="qa-case" data-key="a:${esc(a.id)}"${ST.open.has('a:' + a.id) ? ' open' : ''}><summary>${tag((LVL[a.level] || [a.level])[0], (LVL[a.level] || ['', ''])[1])}<span style="flex:1;min-width:0"><b>${esc(a.number)}</b> ${esc(a.label)} <span class="mut">${esc(a.title)} · ${esc(a.source_label)}${a.count > 1 ? ' · x' + esc(a.count) : ''} · ${esc(ago(a.last_seen))}</span></span>${a.never_mute ? tag('Always shown', 'v') : ''}<span class="mut nw">${esc(a.score)}</span></summary>
      <div class="qa-body">${(a.why || []).length ? `<p style="margin:0"><b>Why:</b> ${esc(a.why.join('; '))}</p>` : ''}
        <div class="cy-meta">${a.host ? `<span><span class="mut">Device</span> ${esc(a.host)}</span>` : ''}${a.user ? `<span><span class="mut">User</span> ${esc(a.user)}</span>` : ''}${a.ip ? `<span><span class="mut">Address</span> ${esc(a.ip)}</span>` : ''}
        ${a.attack && a.attack.id ? `<span><span class="mut">ATT&amp;CK</span> <a href="${esc(a.attack.url)}" target="_blank" rel="noopener">${esc(a.attack.id)}</a> ${esc(a.attack.name)} (${esc(a.attack.tactic)})</span>` : ''}</div>
        ${(a.advice || []).length ? `<div class="cr-sub" style="margin-top:10px">What to do</div><ol>${a.advice.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : ''}
        ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px;flex-wrap:wrap"><button class="btn sm" type="button" data-inc="${esc(a.id)}">Open an incident</button>${a.ip ? `<button class="btn soft sm" type="button" data-block="${esc(a.ip)}" data-al="${esc(a.id)}">Card to block ${esc(a.ip)}</button>` : ''}<button class="btn soft sm" type="button" data-act="ack" data-id="${esc(a.id)}">Seen</button><button class="btn soft sm" type="button" data-act="dismiss" data-id="${esc(a.id)}">Dismiss</button>${a.never_mute ? '' : `<button class="btn soft sm" type="button" data-act="teach" data-id="${esc(a.id)}">This is normal</button>`}${ask('Alert ' + a.number + ': ' + a.label)}</div>` : ''}</div></details>`;
    return `<div><h1 class="sd-h">Alerts</h1><p class="lead">Paste or upload alerts from your antivirus / EDR, firewall or router, server logins, Google Workspace or Microsoft 365 alert mails and your WAF. Hoola groups and scores them, hides the noise with your own "this is normal" rules, and shows the few that matter with why and what to do.</p></div>
      ${CAN() ? `<form class="card" data-form="intake"><h2 class="md-h2">Bring in alerts</h2><textarea class="in" name="text" rows="6" maxlength="1000000" placeholder="Paste alerts or log lines (sshd, fail2ban, UFW, MikroTik, Defender / Quick Heal / Seqrite CSV, Workspace / M365 alert mails, Cloudflare events)" style="width:100%"></textarea>
        <div class="iv-add" style="margin-top:8px"><select class="in" name="source" aria-label="Source"><option value="">Find the source by itself</option><option value="antivirus">Antivirus / EDR</option><option value="firewall">Firewall / router</option><option value="server">Server logins</option><option value="workspace">Google Workspace</option><option value="m365">Microsoft 365</option><option value="waf">Cloudflare / WAF</option></select>
        <label class="btn soft sm" style="flex:0 0 auto">Or choose a file<input type="file" data-up="intake" accept=".csv,.json,.log,.txt,.eml,text/plain" hidden></label><button class="btn" type="submit">Read them</button></div>
        ${res ? `<div class="pb-res${res.matters && res.matters.length ? ' warn' : ''}" style="margin-top:10px"><b>${esc(res.say || '')}</b><span class="mut" style="font-size:13px">${esc(num(res.raw || 0))} lines · ${esc(num(res.new || 0))} new · ${esc(num(res.noise || 0))} noise hidden${res.format ? ' · read as ' + esc(res.format) : ''}</span></div>` : ''}</form>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Open alerts</h2><div class="r"><select class="in sm" data-afilter="1" aria-label="Show"><option value="matters"${f === 'matters' ? ' selected' : ''}>That matter</option><option value="watch"${f === 'watch' ? ' selected' : ''}>To watch</option><option value=""${!f ? ' selected' : ''}>All open</option></select></div></div>
        ${rs.length ? rs.map(one).join('') : empty(f === 'matters' ? 'No alert that matters right now.' : 'Nothing here.')}</section>
      <section class="card"><h2 class="md-h2">Your "this is normal" rules</h2>${(k.rule_list || []).map(r => `<div class="cs-row"><span style="flex:1"><b>${esc(r.label || 'Any kind')}</b> <span class="mut">${esc([r.ip, r.user, r.host].filter(Boolean).join(' · ') || 'everywhere')} · ${esc(r.reason || '')}${r.hits ? ' · hidden ' + esc(r.hits) + ' times' : ''}</span></span>${CAN() ? `<button class="btn soft sm" type="button" data-act="rule_remove" data-id="${esc(r.id)}">Remove</button>` : ''}</div>`).join('') || empty('None yet. Use "This is normal" on an alert.')}
        <p class="cs-note">Ransomware, logins after many failures, forwarding rules and leaked passwords are always shown, even with a rule.</p></section>`;
  }

  /* ---------------------------------------------------------------- checks */
  function pChecks() {
    const k = K(), m = ST.out.mail, l = ST.out.link, fl = ST.out.file, sc = ST.out.secrets;
    return `<div><h1 class="sd-h">Checks</h1><p class="lead">A suspicious mail, link or file - checked without opening the link or uploading the file (only its fingerprint is looked up). Code or config checked for keys and passwords before it is shared.</p></div>
      ${CAN() ? `<div class="md-2" style="align-items:start">
        <form class="card" data-form="mail"><h2 class="md-h2">A suspicious mail</h2><textarea class="in" name="text" rows="7" maxlength="300000" placeholder="Paste the whole mail - best with its headers ('Show original' in Gmail, 'View source' in Outlook)" style="width:100%"></textarea>
          <div class="cy-did">${[['clicked', 'Someone clicked a link'], ['entered_password', 'A password was typed'], ['opened_attachment', 'An attachment was opened'], ['money', 'Money was paid']].map(([n, l2]) => `<label><input type="checkbox" name="${n}"> ${esc(l2)}</label>`).join('')}</div>
          <div class="md-acts"><span class="mut" style="font-size:13px">If something was done, an incident opens with its clock.</span><button class="btn" type="submit">Check it</button></div>
          ${m ? `<div class="pb-res cy-verdict ${(VER[m.verdict] || ['', ''])[1]}" style="margin-top:10px"><div class="cs-head"><b>${esc(m.from || 'The mail')}</b><div class="r">${ver(m.verdict)}</div></div><p style="margin:0">${esc(m.say)}</p>
            ${m.auth && Object.keys(m.auth).length ? `<div class="cy-meta">${Object.entries(m.auth).map(([a, b]) => `<span><span class="mut">${esc(a.toUpperCase())}</span> ${esc(b)}</span>`).join('')}</div>` : ''}${flags(m.flags)}
            ${(m.actions || []).length ? `<div class="cr-sub" style="margin-top:8px">What to do</div><ol>${m.actions.map(x => `<li>${esc(x)}</li>`).join('')}</ol>` : ''}</div>` : ''}</form>
        <div style="display:flex;flex-direction:column;gap:20px">
          <form class="card" data-form="link"><h2 class="md-h2">A link</h2><input class="in" name="urls" maxlength="4000" placeholder="Paste one or more links (never opened)" style="width:100%">
            <div class="md-acts"><span class="mut" style="font-size:13px">Looked up on Google Web Risk / VirusTotal with your key.</span><button class="btn soft" type="submit">Look it up</button></div>
            ${l ? `<div class="pb-res cy-verdict ${(VER[l.verdict] || ['', ''])[1]}" style="margin-top:10px"><div class="cs-head"><b>${esc((l.urls || []).join(', ').slice(0, 120))}</b><div class="r">${ver(l.verdict)}</div></div><p style="margin:0">${esc(l.say)}</p>${flags(l.flags)}</div>` : ''}</form>
          <section class="card"><h2 class="md-h2">A file</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Only its SHA-256 fingerprint is looked up; the file never leaves this desk's server.</p>
            <label class="btn soft">Choose a file<input type="file" data-up="check_file" hidden></label>
            ${fl ? `<div class="pb-res cy-verdict ${(VER[fl.verdict] || ['', ''])[1]}" style="margin-top:10px"><div class="cs-head"><b>${esc(fl.name || 'File')}</b><div class="r">${ver(fl.verdict)}</div></div><p style="margin:0">${esc(fl.say)}</p><code class="qa-code">${esc(fl.sha256 || '')}</code>${flags(fl.flags)}</div>` : ''}</section></div></div>
      <form class="card" data-form="secrets"><h2 class="md-h2">Keys and passwords in code</h2><textarea class="in" name="text" rows="6" maxlength="500000" placeholder="Paste code, a config file or a .env before it goes to GitHub or a vendor" style="width:100%"></textarea>
        <div class="iv-add" style="margin-top:8px"><input class="in" name="name" maxlength="120" placeholder="File name" aria-label="File name"><label class="btn soft sm" style="flex:0 0 auto">Or choose a file<input type="file" data-up="secrets" hidden></label><button class="btn" type="submit">Scan it</button></div>
        <p class="cs-note">The text is not kept; any key found is shown masked. Rotate a found key - deleting it from the file does not remove it from history.</p>
        ${sc ? `<div class="pb-res${sc.found.length ? ' warn' : ' ok'}" style="margin-top:10px"><b>${esc(sc.say)}</b>${sc.found.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Found</th><th class="r">Line</th><th>Value</th><th>Do this</th></tr></thead><tbody>${sc.found.map(x => `<tr><td><b>${esc(x.type)}</b> ${x.level === 'low' ? tag('Test / low', '') : tag('Live-looking', 'bad')}</td><td class="r">${esc(x.line)}</td><td><code class="qa-code">${esc(x.value)}</code></td><td>${esc(x.fix)}</td></tr>`).join('')}</tbody></table></div>` : ''}</div>` : ''}</form>` : ''}
      <section class="card"><h2 class="md-h2">Recent checks</h2>${(k.checks || []).map(c => `<div class="cs-row"><span style="flex:1"><b>${esc(cap(c.kind))}</b> ${esc(c.subject)} <span class="mut">${esc(c.at_local || ago(c.at))}</span></span>${ver(c.verdict)}</div>`).join('') || empty('No checks yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- attack surface */
  function pSurface() {
    const k = K(), doms = k.domains || [], sw = k.software || [], adv = k.all_advisories || [];
    return `<div><h1 class="sd-h">Attack surface</h1><p class="lead">Your own domains, leaked work emails and the software you run - checked passively. Exposed files on a site are looked at only after you prove the domain is yours.</p></div>
      <section class="card"><h2 class="md-h2">Your domains</h2>${doms.map(d => `<details class="qa-case" data-key="d:${esc(d.id)}"${ST.open.has('d:' + d.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(d.domain)}</b> <span class="mut">${d.verified ? 'proved yours' : 'not proved yet'}${(d.tls || {}).days_left !== undefined && (d.tls || {}).days_left !== null ? ' · SSL ' + esc(d.tls.days_left) + ' days' : ''}${d.checked_at ? ' · checked ' + esc(ago(d.checked_at)) : ''}</span></span>${d.score === null || d.score === undefined ? tag('Not checked', '') : tag(d.score + ' / 100', d.score >= 75 ? 'ok' : d.score >= 50 ? 'warn' : 'bad')}</summary>
          <div class="qa-body">${!d.verified ? `<p style="margin:0">To prove it is yours, add this DNS record and tap Verify:</p><div class="cy-meta"><span><span class="mut">Name</span> <code class="qa-code">${esc(d.verify_record.name)}</code></span><span><span class="mut">Type</span> TXT</span><span><span class="mut">Value</span> <code class="qa-code">${esc(d.verify_record.value)}</code></span></div>` : ''}
            ${flags(d.flags)}${d.breach && (d.breach.rows || []).length ? `<div class="cr-sub" style="margin-top:8px">Breaches</div>${d.breach.rows.map(b => `<div class="cs-row"><span style="flex:1">${esc(b.email || '')} <span class="mut">${esc((b.breaches || []).map(x => x.name || x).join(', '))}</span></span></div>`).join('')}` : ''}
            ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px;flex-wrap:wrap"><button class="btn sm" type="button" data-act="posture" data-id="${esc(d.id)}">Check now</button>${!d.verified ? `<button class="btn soft sm" type="button" data-act="domain_verify" data-id="${esc(d.id)}">Verify</button>` : ''}<button class="btn soft sm" type="button" data-act="breach" data-id="${esc(d.id)}">Breach check</button><button class="btn soft sm" type="button" data-act="domain_remove" data-id="${esc(d.id)}">Stop</button>${ask('Domain ' + d.domain + ' settings')}</div>` : ''}</div></details>`).join('') || empty('No domain yet.')}
        ${CAN() ? `<form class="iv-add" data-form="domain"><input class="in" name="domain" required maxlength="200" placeholder="your-business.com" aria-label="Domain"><button class="btn" type="submit">Add my domain</button><button class="btn soft" type="button" data-act="breach" data-id="">Check work emails for breaches</button></form><p class="cs-note">Only your own domains. Hoola never scans anyone else's.</p>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Software you run <span class="mut">${esc(num(sw.length))}</span></h2><div class="r">${CAN() ? '<button class="btn soft sm" type="button" data-act="software_sync">From IT Helpdesk devices</button>' : ''}</div></div>
          ${sw.map(w => `<div class="cs-row"><span style="flex:1"><b>${esc(w.product)}</b> <span class="mut">${esc([w.vendor, w.version, w.where].filter(Boolean).join(' · '))}</span></span>${CAN() ? `<button class="ib" type="button" aria-label="Remove" data-act="software_remove" data-id="${esc(w.id)}">×</button>` : ''}</div>`).join('') || empty('None yet.')}
          ${CAN() ? `<form class="iv-add" data-form="software"><input class="in" name="product" required maxlength="120" placeholder="Product (e.g. Windows 10, Tally Prime, WordPress)" aria-label="Product"><input class="in" name="vendor" maxlength="80" placeholder="Maker" aria-label="Maker"><input class="in" name="version" maxlength="40" placeholder="Version" aria-label="Version"><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Threats in your software</h2><div class="r">${CAN() && sw.length ? '<button class="btn soft sm" type="button" data-act="advisories">Check now</button>' : ''}</div></div>
          ${adv.map(a => `<details class="qa-case" data-key="v:${esc(a.id)}"${ST.open.has('v:' + a.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(a.ref)}</b> ${esc(a.software)} <span class="mut">${esc(a.source.toUpperCase())}${a.score ? ' · ' + esc(a.score) : ''}</span></span>${a.exploited ? tag('Being attacked', 'bad') : ''}${tag(cap(a.status), a.status === 'new' ? 'warn' : '')}</summary>
            <div class="qa-body"><p style="margin:0">${esc(a.title)}</p><p class="mut" style="margin:6px 0 0">${esc(a.summary)}</p><p style="margin:6px 0 0">${esc(a.say)}</p>
            ${CAN() ? `<div class="md-acts" style="justify-content:flex-start;gap:6px">${a.url ? `<a class="btn soft sm" href="${esc(a.url)}" target="_blank" rel="noopener">Details</a>` : ''}<button class="btn sm" type="button" data-act="advisory_mark" data-id="${esc(a.id)}" data-st="patched">Patched</button><button class="btn soft sm" type="button" data-act="advisory_mark" data-id="${esc(a.id)}" data-st="not_ours">Not ours</button></div>` : ''}</div></details>`).join('') || empty(sw.length ? 'No threats found for your software.' : 'Add your software to match new threats (NVD, CISA KEV).')}</section></div>`;
  }

  /* ---------------------------------------------------------------- incidents */
  function pIncidents() {
    const k = K(), incs = k.incidents || [], sel = incs.find(i => i.id === ST.inc) || incs[0], waiting = k.waiting || [];
    const full = sel ? lazyOut('inc:' + sel.id, 'notify_plan', {incident: sel.id}) : null;
    const pb = ST.pb && ST.out['pb:' + ST.pb];
    const card = x => `<div class="pb-res warn" style="margin-top:10px"><div class="cs-head"><b>${esc(x.number)} · ${esc(x.label)}: ${esc(x.target)}</b><div class="r">${tag(x.status_label, ACT[x.status] || '')}</div></div>
      <p style="margin:0">${esc(x.reason || '')}</p><div class="dv-grid"><div><span class="mut">${x.via === 'cloudflare' ? 'Your tap runs it on Cloudflare' : 'Steps in your console after your yes'}</span><ol>${(x.steps || []).map(s => `<li>${esc(s)}</li>`).join('')}</ol></div><div><span class="mut">Risk</span><p style="margin:4px 0 0">${esc(x.risk)}</p><span class="mut" style="display:block;margin-top:8px">To undo</span><p style="margin:4px 0 0">${esc(x.undo)}</p></div></div>
      ${CAN() && x.status === 'waiting' ? `<form class="iv-add" data-form="decide" data-id="${esc(x.id)}" data-h="${esc(x.hash)}"><button class="btn soft" type="submit" data-yes="0">No</button><button class="btn" type="submit" data-yes="1">${x.wipe ? 'Yes, wipe it' : 'Yes, do it'}</button></form>${x.wipe ? '<p class="cs-note">A wipe also needs your fingerprint on your phone once it is set up.</p>' : ''}` : ''}
      ${CAN() && x.status === 'approved' && x.via !== 'cloudflare' ? `<div class="md-acts" style="justify-content:flex-start"><button class="btn sm" type="button" data-act="contain_done" data-id="${esc(x.id)}">I did it</button></div>` : ''}</div>`;
    return `<div><h1 class="sd-h">Incidents</h1><p class="lead">An incident keeps its timeline, what happened, the impact and what was done; the notices you must send in each country you work in, with their deadlines; the playbook to follow; and the block / wipe cards that only your tap decides.</p></div>
      ${waiting.length ? `<section class="card"><h2 class="md-h2">Waiting for your tap <span class="mut">${esc(num(waiting.length))}</span></h2>${waiting.map(card).join('')}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Open incidents</h2>${incs.map(i => `<div class="cs-row${sel && i.id === sel.id ? ' cy-sel' : ''}"><span style="flex:1"><b>${esc(i.number)}</b> ${esc(i.title)} <span class="mut">${esc(cap(i.kind))} · ${esc(i.detected_local)}</span></span><button class="btn soft sm" type="button" data-pick="${esc(i.id)}">Open</button></div>`).join('') || empty('No open incident.')}</section>
        ${CAN() ? `<form class="card" data-form="incident"><h2 class="md-h2">Open an incident</h2><div class="md-form"><div class="md-field wide"><label for="cyI1">What happened</label><input class="in" id="cyI1" name="title" required maxlength="200"></div>
          <div class="md-field"><label for="cyI2">Kind</label><select class="in" id="cyI2" name="kind">${['other', 'phishing', 'malware', 'ransomware', 'account', 'data_leak', 'payment', 'intrusion', 'website'].map(x => `<option value="${x}">${esc(cap(x.replace('_', ' ')))}</option>`).join('')}</select></div>
          <div class="md-field"><label for="cyI3">Systems</label><input class="in" id="cyI3" name="systems" maxlength="200"></div>
          <label class="md-field wide cy-chk"><input type="checkbox" name="personal_data"> Personal data of customers or staff may be involved</label></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Notice clocks start from now.</span><button class="btn" type="submit">Open it</button></div></form>` : ''}</div>
      ${sel ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(sel.number)} · ${esc(sel.title)}</h2><div class="r">${CAN() ? `<button class="btn soft sm" type="button" data-act="incident_note" data-id="${esc(sel.id)}">Word + PDF note</button>` : ''}${ask('Incident ' + sel.number)}</div></div>
        <div class="cr-sub" style="margin-top:6px">Notices to send</div>
        ${full === null ? '<p class="mut" style="margin:0">Working it out…</p>' : full && full.error ? `<p class="cs-neg">${esc(full.error)}</p>` : full ? `${(full.rows || []).filter(r => r.applies || r.maybe).map(r => `<div class="cy-notice"><div style="flex:1;min-width:0"><b>${esc(r.law)}</b> <span class="mut">(${esc(r.country)}) to ${esc(r.to)}</span>${r.checked ? '' : ' ' + tag('Check this', 'warn')}${r.maybe ? ' ' + tag('If it applies to you', '') : ''}
            <div class="mut" style="font-size:13px">${esc(r.note)} <a href="${esc(r.source)}" target="_blank" rel="noopener">Source</a></div></div>
            <div class="cy-due">${r.due ? `<b class="${r.status === 'overdue' ? 'cs-neg' : ''}">${esc(r.due_local)}</b><span class="mut">${r.hours_left !== null && r.hours_left > 0 ? esc(r.hours_left) + ' h left' : r.status === 'overdue' ? 'late' : ''}</span>` : '<span class="mut">no fixed time</span>'}</div>
            ${tag((NST[r.status] || [r.status])[0], (NST[r.status] || ['', ''])[1])}${CAN() && r.status !== 'done' ? `<button class="btn soft sm" type="button" data-notify="${esc(r.id)}" data-st="done">Told</button><button class="btn soft sm" type="button" data-notify="${esc(r.id)}" data-st="na">Not needed</button>` : ''}</div>`).join('') || empty('No notice applies on these facts.')}
            ${(full.unknown || []).length ? `<p class="cs-note">No rule kept for ${esc(full.unknown.join(', '))}: check with a local lawyer.</p>` : ''}` : ''}
        ${sel.cert_in_due ? `<p class="cs-note">CERT-In draft and reminders are on the IT Helpdesk incident.</p>` : ''}
        <div class="cr-sub" style="margin-top:12px">Playbook</div><div class="iv-add" style="margin-top:0"><select class="in" data-pbsel="1" aria-label="Playbook">${(P().playbooks || []).map(p => `<option value="${esc(p.id)}"${(ST.pb || '') === p.id ? ' selected' : ''}>${esc(p.title)}</option>`).join('')}</select><button class="btn soft" type="button" data-pbopen="1">Show the steps</button></div>
        ${pb && !pb.error ? `<ol class="cy-pb">${pb.steps.map(s => `<li><span class="mut">${esc(s.phase)}</span> ${esc(s.text)}</li>`).join('')}</ol>` : ''}
        ${CAN() ? `<div class="md-2" style="align-items:start;margin-top:12px"><form data-form="tl" data-id="${esc(sel.id)}"><div class="cr-sub">Add to the timeline</div><div class="iv-add" style="margin-top:4px"><input class="in" name="what" required maxlength="500" placeholder="What happened / what was done" aria-label="Timeline entry"><button class="btn soft" type="submit">Add</button></div></form>
          <form data-form="contain" data-incid="${esc(sel.id)}"><div class="cr-sub">Ask for a block / wipe card</div><div class="iv-add" style="margin-top:4px"><select class="in" name="kind" aria-label="Kind">${Object.entries(K().action_kinds || {}).map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select><input class="in" name="target" required maxlength="200" placeholder="IP, user, device" aria-label="Target"><button class="btn soft" type="submit">Make the card</button></div></form></div>` : ''}
        <div class="cr-sub" style="margin-top:12px">Timeline</div>${((ST.out['incv:' + sel.id] || {}).timeline || []).map(t => `<div class="cs-row"><span class="mut nw" style="min-width:120px">${esc(dt(t.at))}</span><span style="flex:1">${esc(t.what)}</span><span class="mut">${esc(t.by || '')}</span></div>`).join('') || (ST.out['incv:' + sel.id] === undefined ? lazyIncident(sel.id) : empty('No entries.'))}
        ${CAN() ? `<form class="iv-add" data-form="close" data-id="${esc(sel.id)}" style="margin-top:12px"><input class="in" name="lessons" required maxlength="2000" placeholder="What will change so it does not happen again" aria-label="Lessons"><button class="btn soft" type="submit">Close the incident</button></form>` : ''}</section>` : ''}
      <section class="card"><h2 class="md-h2">All block / wipe cards</h2>${(k.actions || []).filter(x => x.status !== 'waiting').slice(0, 20).map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(x.number)}</b> ${esc(x.label)}: ${esc(x.target)} <span class="mut">${esc(ago(x.created_at))}</span></span>${tag(x.status_label, ACT[x.status] || '')}</div>`).join('') || empty('None yet.')}</section>`;
  }
  function lazyIncident(id) { lazyOut('incv:' + id, 'incident_get', {incident: id}); return '<p class="mut" style="margin:0">Loading…</p>'; }

  /* ---------------------------------------------------------------- programme */
  const PS = [['controls', 'Controls'], ['risks', 'Risks'], ['access', 'Access review'], ['vendors', 'Vendors'], ['drills', 'Drills'], ['training', 'Training'], ['policy', 'Password policy']];
  function pProgramme() {
    const pr = P(), ps = ST.ps || 'controls';
    const body = {controls: psControls, risks: psRisks, access: psAccess, vendors: psVendors, drills: psDrills, training: psTraining, policy: psPolicy}[ps] || psControls;
    return `<div><h1 class="sd-h">Programme</h1><p class="lead">Your security programme: a controls self-check (CIS Controls v8, mapped to NIST CSF 2.0 and ISO 27001:2022), risks, access reviews, vendors, drills, training and your password policy. Your records - a self-check, not a certification.</p></div>
      <div class="cy-sub" role="tablist" aria-label="Programme">${PS.map(([k2, n]) => `<button type="button" role="tab" data-ps="${k2}" aria-selected="${k2 === ps}">${esc(n)}</button>`).join('')}</div>${body(pr)}`;
  }
  function psControls(pr) {
    const c = pr.controls || {};
    return `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Where you stand</h2><div class="cy-score">${scoreRing(c.score, 'Controls score')}<div style="flex:1;min-width:0"><p style="margin:0">${esc(c.say || '')}</p>
        ${Object.keys(c.functions || {}).length ? bars(Object.entries(c.functions).filter(([, v]) => v !== null).map(([n, v]) => [n, v || 0, v >= 75 ? 'cy-ok' : v >= 50 ? 'cy-warn' : 'cy-bad']), pct, 'By function') : ''}</div></div>
        ${(c.history || []).length > 1 ? line(c.history.map(h => [h.day.slice(5), h.score]), 'Score over time', pct, 'mk-l') : ''}<p class="cs-note">${esc(c.frameworks || '')}</p></section>
      <section class="card"><h2 class="md-h2">Biggest gaps</h2>${(c.gaps || []).slice(0, 10).map(g => `<div class="cs-row"><span class="cs-dot${g.a === 'no' ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(g.id)}</b> ${esc(g.q)}<div class="mut" style="font-size:13px">${esc(g.fix)}</div></span>${tag(cap(g.a), g.a === 'no' ? 'bad' : 'warn')}</div>`).join('') || empty('Answer the questions below.')}</section></div>
      <form class="card" data-form="controls"><div class="cs-head"><h2 class="md-h2" style="margin:0">The 18 controls <span class="mut">${esc(num(c.answered || 0))} of ${esc(num(c.total || 0))} answered</span></h2><div class="r">${CAN() ? '<button class="btn" type="submit">Save answers</button>' : ''}</div></div>
        ${(c.controls || []).map(x => `<details class="qa-case" data-key="ct:${x.no}"${ST.open.has('ct:' + x.no) ? ' open' : ''}><summary><span class="qa-pr">${x.no}</span><span style="flex:1;min-width:0"><b>${esc(x.title)}</b> <span class="mut">${esc(x.csf)} · ISO ${esc(x.iso)}</span></span>${x.score === null ? tag('Not answered', '') : tag(x.score + '%', x.score >= 75 ? 'ok' : x.score >= 50 ? 'warn' : 'bad')}</summary>
          <div class="qa-body">${x.questions.map(q => `<div class="cy-q"><label for="q${esc(q.id)}"><b>${esc(q.id)}</b> ${esc(q.q)}<span class="mut">${esc(q.fix)}</span></label><select class="in sm" id="q${esc(q.id)}" name="${esc(q.id)}"${CAN() ? '' : ' disabled'}><option value=""${!q.a ? ' selected' : ''}>-</option>${['yes', 'partial', 'no', 'na'].map(v => `<option value="${v}"${q.a === v ? ' selected' : ''}>${v === 'na' ? 'Not for us' : cap(v)}</option>`).join('')}</select></div>`).join('')}</div></details>`).join('')}</form>`;
  }
  function psRisks(pr) {
    const rs = pr.risks || [], open = rs.filter(r => r.status === 'open');
    const cell = (l, i) => { const n = open.filter(r => r.likelihood === l && r.impact === i).length, s = l * i; return `<td class="${s >= 15 ? 'h' : s >= 8 ? 'm' : 'l'}" title="Likelihood ${l}, impact ${i}">${n || ''}</td>`; };
    return `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Heat map</h2><table class="cy-heat" aria-label="Risks by likelihood and impact"><tbody>${[5, 4, 3, 2, 1].map(l => `<tr><th>${l}</th>${[1, 2, 3, 4, 5].map(i => cell(l, i)).join('')}</tr>`).join('')}<tr><th></th>${[1, 2, 3, 4, 5].map(i => `<th>${i}</th>`).join('')}</tr></tbody></table><p class="cs-note">Up: likelihood. Across: impact. Numbers are open risks.</p></section>
      ${CAN() ? `<form class="card" data-form="risk"><h2 class="md-h2">Add a risk</h2><div class="md-form"><div class="md-field wide"><label for="cyR1">What could go wrong</label><input class="in" id="cyR1" name="title" required maxlength="200"></div>
        <div class="md-field"><label for="cyR2">Asset</label><input class="in" id="cyR2" name="asset" maxlength="120"></div><div class="md-field"><label for="cyR3">Owner</label><input class="in" id="cyR3" name="owner" maxlength="80"></div>
        <div class="md-field"><label for="cyR4">Likelihood</label><select class="in" id="cyR4" name="likelihood">${[1, 2, 3, 4, 5].map(v => `<option${v === 3 ? ' selected' : ''}>${v}</option>`).join('')}</select></div>
        <div class="md-field"><label for="cyR5">Impact</label><select class="in" id="cyR5" name="impact">${[1, 2, 3, 4, 5].map(v => `<option${v === 3 ? ' selected' : ''}>${v}</option>`).join('')}</select></div>
        <div class="md-field"><label for="cyR6">Treatment</label><select class="in" id="cyR6" name="treatment"><option value="reduce">Reduce</option><option value="accept">Accept</option><option value="transfer">Transfer (insurance)</option><option value="avoid">Avoid</option></select></div>
        <div class="md-field"><label for="cyR7">Action</label><input class="in" id="cyR7" name="action" maxlength="200"></div></div><div class="md-acts"><span></span><button class="btn" type="submit">Add the risk</button></div></form>` : ''}</div>
      <section class="card"><h2 class="md-h2">Risk register</h2>${rs.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Risk</th><th class="r">Score</th><th>Treatment</th><th>Owner</th><th></th></tr></thead><tbody>${rs.map(r => `<tr><td><b>${esc(r.ref)}</b> ${esc(r.title)} <span class="mut">${esc(r.asset || '')}${r.action ? ' · ' + esc(r.action) : ''}</span></td><td class="r">${tag(r.score + ' ' + r.band, BAND[r.band])}</td><td>${esc(cap(r.treatment || '-'))}</td><td>${esc(r.owner || '-')}</td><td class="r nw">${CAN() && r.status === 'open' ? `<button class="btn soft sm" type="button" data-rclose="${esc(r.id)}">Close</button>` : tag(cap(r.status), '')}</td></tr>`).join('')}</tbody></table></div>` : empty('No risks yet.')}</section>`;
  }
  function psAccess(pr) {
    const last = (pr.access || [])[0], res = ST.out.access || last;
    return `${CAN() ? `<form class="card" data-form="access"><h2 class="md-h2">Review who can get in</h2><p class="mut" style="margin:0 0 8px;font-size:14px">Export your users from Google Workspace (Users > Download) or Microsoft 365 (Active users > Export) and paste the CSV. Read only - nothing is changed.</p>
        <textarea class="in" name="text" rows="6" maxlength="2000000" placeholder="Email,Name,Admin role,2SV enrolled,Last sign in,Status" style="width:100%"></textarea>
        <div class="iv-add" style="margin-top:8px"><input class="in" name="leavers" maxlength="4000" placeholder="People who left (emails, comma separated)" aria-label="Leavers"><label class="btn soft sm" style="flex:0 0 auto">Or choose a CSV<input type="file" data-up="access" accept=".csv,text/csv" hidden></label><button class="btn" type="submit">Review</button></div></form>` : ''}
      ${res ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(res.ref)} <span class="mut">${esc(res.title || '')}</span></h2></div>
        <div class="iv-kpis mk-k2" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px">${kpi('Active users', esc(num(res.summary.active)))}${kpi('Admins', esc(num(res.summary.admins)))}${kpi('2-step on', esc(pct(res.summary.mfa_pct)), '', res.summary.mfa_pct !== null && res.summary.mfa_pct < 100 ? 'warn' : '')}${kpi('Urgent', esc(num(res.summary.high)), '', res.summary.high ? 'warn' : '')}</div>
        ${(res.findings || []).map(f => `<div class="rk-flag ${f.level === 'high' ? 'stop' : f.level === 'medium' ? 'check' : ''}"><span>${esc(cap(f.level))}</span><div><b>${esc(f.user || 'All')}</b>: ${esc(f.say)}<div class="mut" style="font-size:13px">${esc(f.fix)}</div></div></div>`).join('') || '<p class="cs-pos">No problem found.</p>'}</section>` : ''}
      <section class="card"><h2 class="md-h2">Earlier reviews</h2>${(pr.access || []).map(a => `<div class="cs-row"><span style="flex:1"><b>${esc(a.ref)}</b> ${esc(a.title)} <span class="mut">${esc(ago(a.created_at))}</span></span><span class="mut">${esc(num(a.summary.active))} users · 2-step ${esc(pct(a.summary.mfa_pct))}</span>${a.summary.high ? tag(a.summary.high + ' urgent', 'bad') : tag('OK', 'ok')}</div>`).join('') || empty('None yet.')}</section>`;
  }
  function psVendors(pr) {
    return `${CAN() ? `<form class="card" data-form="vendor"><h2 class="md-h2">Review a vendor</h2><div class="md-form"><div class="md-field"><label for="cyV1">Vendor</label><input class="in" id="cyV1" name="name" required maxlength="160"></div><div class="md-field"><label for="cyV2">What they do for you</label><input class="in" id="cyV2" name="service" maxlength="200"></div>
        <div class="md-field"><label for="cyV3">Your data they hold</label><select class="in" id="cyV3" name="data_level"><option value="none">None</option><option value="internal" selected>Internal</option><option value="personal">Personal data</option><option value="sensitive">Sensitive (health, money, IDs)</option></select></div></div>
        <div class="cy-vq">${(pr.vendor_q || []).map(q => `<div class="cy-q"><label for="vq${esc(q.id)}">${esc(q.q)}</label><select class="in sm" id="vq${esc(q.id)}" name="q_${esc(q.id)}"><option value="unknown">Don't know</option><option value="yes">Yes</option><option value="no">No</option></select></div>`).join('')}</div>
        <div class="md-acts"><span></span><button class="btn" type="submit">Score it</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">Vendors</h2>${(pr.vendors || []).map(v => `<details class="qa-case" data-key="vd:${esc(v.id)}"${ST.open.has('vd:' + v.id) ? ' open' : ''}><summary><span style="flex:1;min-width:0"><b>${esc(v.ref)}</b> ${esc(v.title)} <span class="mut">${esc(v.service || '')} · ${esc(v.data_level)} data · review by ${esc(v.next_review)}</span></span><span class="mut nw">${esc(v.score)}/100</span>${tag(cap(v.tier) + ' risk', BAND[v.tier])}</summary>
        <div class="qa-body">${(v.gaps || []).map(g => `<div class="cs-row"><span class="cs-dot${g.a === 'no' ? ' bad' : ''}"></span><span style="flex:1">${esc(g.say)}</span>${tag(g.a === 'no' ? 'No' : "Don't know", g.a === 'no' ? 'bad' : 'warn')}</div>`).join('') || '<p class="cs-pos" style="margin:0">Every answer is yes.</p>'}</div></details>`).join('') || empty('No vendors yet.')}</section>`;
  }
  function psDrills(pr) {
    const tts = pr.tabletops || [], act = tts.find(t => t.status !== 'done');
    return `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Playbooks</h2>${(pr.playbooks || []).map(p => `<div class="cs-row"><span style="flex:1"><b>${esc(p.title)}</b> <span class="mut">${esc(p.steps)} steps</span></span>${CAN() ? `<button class="btn soft sm" type="button" data-tt="${esc(p.id)}">Practise it</button>` : ''}</div>`).join('')}</section>
      <section class="card"><h2 class="md-h2">${act ? esc(act.ref) + ' · ' + esc(act.title) : 'Drills'}</h2>${act ? act.steps.map((s, i) => `<div class="cy-step"><span class="mut">${esc(s.phase)}</span><span style="flex:1">${esc(s.text)}</span>${CAN() ? `<button class="btn ${s.ok === true ? '' : 'soft'} sm" type="button" data-tts="${esc(act.id)}" data-i="${i}" data-ok="1" aria-pressed="${s.ok === true}">We can</button><button class="btn ${s.ok === false ? '' : 'soft'} sm" type="button" data-tts="${esc(act.id)}" data-i="${i}" data-ok="0" aria-pressed="${s.ok === false}">Gap</button>` : ''}</div>`).join('')
        + (CAN() ? `<form class="iv-add" data-form="ttdone" data-id="${esc(act.id)}"><input class="in" name="lessons" required maxlength="2000" placeholder="What you learned" aria-label="Lessons"><input class="in" name="minutes" inputmode="numeric" maxlength="4" placeholder="Minutes" aria-label="Minutes" style="flex:0 0 100px"><button class="btn" type="submit">Finish</button></form>` : '')
        : empty('Pick a playbook to practise with your team - walk each step and mark what you could really do.')}
        ${tts.filter(t => t.status === 'done').map(t => `<div class="cs-row"><span style="flex:1"><b>${esc(t.ref)}</b> ${esc(t.title)} <span class="mut">${esc(ago(t.updated_at))} · ${esc(t.lessons || '')}</span></span>${tag(t.ready + ' / ' + t.total, t.gaps ? 'warn' : 'ok')}</div>`).join('')}</section></div>`;
  }
  function psTraining(pr) {
    const tr = pr.training || {};
    return `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Who did which topic (12 months)</h2>${(tr.topics || []).some(t => t.of) ? bars(tr.topics.map(t => [t.title, t.pct || 0, (t.pct || 0) >= 75 ? 'cy-ok' : 'cy-warn']), pct, 'Training coverage') : empty('Record the first training below.')}
        ${CAN() ? `<form class="iv-add" data-form="train"><input class="in" name="person" required maxlength="80" placeholder="Person" aria-label="Person"><select class="in" name="topic" aria-label="Topic">${(pr.topics || []).map(t => `<option value="${esc(t.id)}">${esc(t.title)}</option>`).join('')}</select><button class="btn soft" type="submit">Done</button></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">A plan for the year</h2><ol class="cy-pb">${(tr.plan || []).map(p => `<li><span class="mut">Month ${esc(p.month)}</span> ${esc(p.topic)}</li>`).join('')}</ol></section></div>
      <section class="card"><h2 class="md-h2">Quick quiz for your team</h2>${(tr.quiz || []).map((q, i) => `<details class="qa-case" data-key="qz:${i}"${ST.open.has('qz:' + i) ? ' open' : ''}><summary><span style="flex:1">${esc(q.q)}</span></summary><div class="qa-body"><p style="margin:0">${esc(q.a)}</p></div></details>`).join('')}</section>`;
  }
  function psPolicy(pr) {
    const p = pr.policy || {};
    return `<div class="md-2" style="align-items:start">${CAN() ? `<form class="card" data-form="policy"><h2 class="md-h2">Your password rules</h2><div class="md-form">
        <div class="md-field"><label for="cyP1">Minimum length</label><input class="in" id="cyP1" name="min_length" inputmode="numeric" value="${esc(p.min_length || 8)}"></div>
        <div class="md-field"><label for="cyP2">2-step sign-in</label><select class="in" id="cyP2" name="mfa">${[['all', 'Everyone'], ['some', 'Some people'], ['none', 'Nobody']].map(([v, l]) => `<option value="${v}"${(p.mfa || 'some') === v ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
        <div class="md-field"><label for="cyP3">Forced change every (days, 0 = never)</label><input class="in" id="cyP3" name="rotation_days" inputmode="numeric" value="${esc(p.rotation_days || 0)}"></div>
        <div class="md-field"><label for="cyP4">Lock after wrong attempts (0 = no limit)</label><input class="in" id="cyP4" name="lockout" inputmode="numeric" value="${esc(p.lockout || 0)}"></div>
        ${[['composition', 'Forced mix of symbols / numbers'], ['breached_check', 'New passwords checked against leaked lists'], ['manager', 'Staff have a password manager']].map(([n, l]) => `<label class="md-field wide cy-chk"><input type="checkbox" name="${n}"${p[n] ? ' checked' : ''}> ${esc(l)}</label>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Checked against NIST SP 800-63B.</span><button class="btn" type="submit">Check</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">Result</h2>${p.score !== undefined ? `<div class="cy-score">${scoreRing(p.score, 'Password policy')}<div style="flex:1">${flags((p.findings || []).map(f => ({level: f.level === 'high' ? 'bad' : f.level === 'medium' ? 'warn' : 'info', text: f.say, fix: f.fix})))}</div></div>` : empty('Fill in your rules to check them.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, keys = s.keys || {}, j = v => (v || []).join(', ');
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your country decides which incident notices are shown; your own addresses and important systems decide what matters; keys for link / breach / threat look-ups are sealed and never shown again.</p></div>
      <form class="card" data-form="cyset"><h2 class="md-h2">Your business</h2><div class="md-form">
        <div class="md-field"><label for="cyS1">Country (two letters)</label><input class="in" id="cyS1" name="country" maxlength="2" value="${esc(s.country || '')}" placeholder="IN"></div>
        <div class="md-field"><label for="cyS2">Sector</label><select class="in" id="cyS2" name="sector">${[['', 'General'], ['health', 'Health'], ['finance', 'Banking / finance'], ['listed', 'Listed company'], ['public', 'Public sector'], ['digital', 'Digital / cloud services'], ['energy', 'Energy'], ['transport', 'Transport'], ['manufacturing', 'Manufacturing'], ['telecom', 'Telecom']].map(([v, l]) => `<option value="${v}"${(s.sector || '') === v ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="cyS3">Other countries with your customers / data</label><input class="in" id="cyS3" name="extra_countries" maxlength="200" value="${esc(j(s.extra_countries))}" placeholder="GB, US"></div>
        <div class="md-field"><label for="cyS4">Morning summary at</label><input class="in" id="cyS4" name="morning_time" type="time" value="${esc(s.morning_time || '09:15')}"></div>
        <div class="md-field wide"><label for="cyS5">Your office / server IPs (never blocked; logins from them are normal)</label><input class="in" id="cyS5" name="own_ips" maxlength="1000" value="${esc(j(s.own_ips))}"></div>
        <div class="md-field wide"><label for="cyS6">Most important systems (Tally server, website …)</label><input class="in" id="cyS6" name="crown_hosts" maxlength="1000" value="${esc(j(s.crown_hosts))}"></div>
        <div class="md-field wide"><label for="cyS7">Names fraudsters pretend to be (owner, accountant …)</label><input class="in" id="cyS7" name="vip_names" maxlength="1000" value="${esc(j(s.vip_names))}"></div>
        <div class="md-field wide"><label for="cyS8">Work emails for the breach check</label><input class="in" id="cyS8" name="work_emails" maxlength="2000" value="${esc(j(s.work_emails))}"></div>
        <div class="md-field"><label for="cyS9">Link check with</label><select class="in" id="cyS9" name="link_provider"><option value="webrisk"${s.link_provider !== 'safebrowsing' ? ' selected' : ''}>Google Web Risk (business use)</option><option value="safebrowsing"${s.link_provider === 'safebrowsing' ? ' selected' : ''}>Safe Browsing (non-commercial only)</option></select></div>
        <div class="md-field wide"><label for="cyS10">Your security rules</label><textarea class="in" id="cyS10" name="rules" rows="3" maxlength="2000">${esc(s.rules || '')}</textarea></div></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <section class="card"><h2 class="md-h2">Keys</h2>${Object.entries(keys).map(([p, v]) => `<form class="cy-key" data-form="key" data-p="${esc(p)}"><div style="flex:1;min-width:0"><b>${esc(v.label)}</b>${v.note ? `<div class="mut" style="font-size:13px">${esc(v.note)}</div>` : ''}</div>
        ${v.set ? `${tag('Set', 'ok')}${CAN() ? `<button class="btn soft sm" type="button" data-kdel="${esc(p)}">Remove</button>` : ''}` : CAN() ? `<input class="in sm" name="token" type="password" autocomplete="off" maxlength="300" placeholder="Paste the key" aria-label="${esc(v.label)} key">${p === 'cloudflare' ? '<input class="in sm" name="extra" maxlength="40" placeholder="Zone ID" aria-label="Zone ID">' : ''}<button class="btn soft sm" type="submit">Save</button>` : tag('Not set', '')}</form>`).join('')}
        <p class="cs-note">Sealed on arrival, never shown again and never put in the chat. A key that ever went into a chat: change it.</p></section>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Scan or test anyone\'s systems, or write attack code', 'Open a suspicious link (looked up only)', 'Upload your file anywhere (only its fingerprint is looked up)', 'Take a password, OTP or key in the chat', 'Block, disable, quarantine or wipe without your tap', 'Hide ransomware, forwarding rules or leaked passwords', 'Assume another country\'s notice law for yours'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const dropInc = id => { for (const k of Object.keys(ST.out)) if (k.startsWith('inc:') || (id && k === 'incv:' + id)) delete ST.out[k]; };
  async function uploadFile(f, purpose) {
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) { toast('That file is over 8 MB.', true); return; }
    const buf = new Uint8Array(await f.arrayBuffer()); let bin = '';
    for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    toast(purpose === 'check_file' ? 'Looking up its fingerprint…' : 'Reading it…');
    const r = await api('POST', '/api/cydesk/upload', {name: f.name, purpose, data: btoa(bin)});
    if (purpose === 'check_file') ST.out.file = r; else if (purpose === 'secrets') ST.out.secrets = r; else if (purpose === 'access') ST.out.access = r; else ST.out.intake = r;
    await changed(r.say || '');
  }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const ps = t.closest('[data-ps]'); if (ps) { ST.ps = ps.dataset.ps; showPage(true); return; }
    const pk = t.closest('[data-pick]'); if (pk) { ST.inc = pk.dataset.pick; showPage(true); return; }
    if (t.closest('[data-pbopen]')) { const id = ($('[data-pbsel]') || {}).value; if (!id) return; ST.pb = id; try { ST.out['pb:' + id] = await run('playbook', {playbook: id}); } catch (err) { toast(err.message, true); } showPage(true); return; }
    try {
      const ic = t.closest('[data-inc]'); if (ic) { const r = await run('incident_new', {alert_ids: [ic.dataset.inc]}); ST.inc = r.incident.id; dropInc(); await changed(r.say); location.hash = '#/incidents'; return; }
      const bl = t.closest('[data-block]'); if (bl) { const r = await run('contain', {kind: 'block_ip', target: bl.dataset.block, alert: bl.dataset.al, reason: 'From an alert'}); await changed(r.say || 'Card made - it waits for your tap on Incidents.'); return; }
      const nt = t.closest('[data-notify]'); if (nt) { let ref = ''; if (nt.dataset.st === 'done') ref = prompt('Reference of the notice (optional)') || '';
        const r = await run('notify_mark', {incident: ST.inc || ((K().incidents || [])[0] || {}).id, rule_id: nt.dataset.notify, status: nt.dataset.st, reference: ref});
        ST.out['inc:' + r.incident] = r; await changed('Marked.'); return; }
      const rc = t.closest('[data-rclose]'); if (rc) { await changed((await run('risk_save', {id: rc.dataset.rclose, status: 'closed'})).say); return; }
      const tt = t.closest('[data-tt]'); if (tt) { const people = prompt('Who is taking part? (optional)') || ''; await changed((await run('tabletop_start', {playbook: tt.dataset.tt, people})).say); return; }
      const ts = t.closest('[data-tts]'); if (ts) { await run('tabletop_step', {id: ts.dataset.tts, i: Number(ts.dataset.i), ok: ts.dataset.ok === '1'}); await changed(''); return; }
      const kd = t.closest('[data-kdel]'); if (kd) { if (!confirm('Remove this key from Hoola?')) return; await changed((await run('key_del', {provider: kd.dataset.kdel})).say || 'Removed.'); return; }
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act, d = a.dataset, say = r => (r && r.say) || 'Done.';
        if (act === 'domain_remove' && !confirm('Stop watching this domain?')) return;
        let extra = {};
        if (act === 'teach') { const reason = prompt('Why is this normal? (for example: our office VPN)'); if (!reason) return; extra = {reason}; }
        a.disabled = true;
        if (['ack', 'dismiss', 'teach'].includes(act)) await changed(say(await run(act, {alert: d.id, ...extra})));
        else if (act === 'rule_remove') await changed(say(await run('rule_remove', {rule: d.id})));
        else if (['posture', 'domain_verify', 'domain_remove', 'breach', 'software_remove'].includes(act)) { if (act === 'posture') toast('Checking DNS, SSL and headers…'); await changed(say(await run(act, {id: d.id}))); }
        else if (act === 'software_sync' || act === 'advisories') { toast('Checking…'); await changed(say(await run(act))); }
        else if (act === 'advisory_mark') await changed(say(await run('advisory_mark', {id: d.id, status: d.st})));
        else if (act === 'incident_note') await changed(say(await run('incident_note', {incident: d.id})));
        else if (act === 'contain_done') { const note = prompt('What did you do? (optional)') || ''; await changed(say(await run('contain_done', {action: d.id, ok: true, note}))); }
        return;
      }
    } catch (err2) { toast(err2.message, true); const a = t.closest('[data-act]'); if (a) a.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    try {
      if (el.dataset.afilter !== undefined) { ST.af = el.value; showPage(true); return; }
      if (el.dataset.up) { const f = el.files && el.files[0]; el.value = ''; await uploadFile(f, el.dataset.up); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const did = {clicked: fd.get('clicked') === 'on', entered_password: fd.get('entered_password') === 'on', opened_attachment: fd.get('opened_attachment') === 'on', money: fd.get('money') === 'on'};
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'intake') { if (!g('text')) throw new Error('Paste alerts or choose a file.'); ST.out.intake = await run('intake', {text: S(fd.get('text')), source: g('source')}); ST.af = 'matters'; await done(ST.out.intake.say); }
      else if (kind === 'mail') { if (!g('text')) throw new Error('Paste the mail.'); ST.out.mail = await run('check_email', {text: S(fd.get('text')), ...did}); await changed(''); }
      else if (kind === 'link') { if (!g('urls')) throw new Error('Paste a link.'); ST.out.link = await run('check_link', {urls: g('urls')}); await changed(''); }
      else if (kind === 'secrets') { if (!g('text')) throw new Error('Paste the code.'); ST.out.secrets = await run('secrets_scan', {text: S(fd.get('text')), name: g('name')}); form.reset(); await changed(''); }
      else if (kind === 'domain') { const r = await run('domain_add', {domain: g('domain')}); await done(r.say); }
      else if (kind === 'software') { await done((await run('software_add', {product: g('product'), vendor: g('vendor'), version: g('version')})).say || 'Added.'); }
      else if (kind === 'incident') { const r = await run('incident_new', {title: g('title'), kind: g('kind'), systems: g('systems'), personal_data: fd.get('personal_data') === 'on'}); ST.inc = r.incident.id; dropInc(); await done(r.say); }
      else if (kind === 'tl') { await run('incident_add', {incident: form.dataset.id, what: g('what')}); dropInc(form.dataset.id); await done('Added to the timeline.'); }
      else if (kind === 'contain') { const r = await run('contain', {kind: g('kind'), target: g('target'), incident: form.dataset.incid}); dropInc(form.dataset.incid); await done(r.say || 'Card made - it waits for your tap.'); }
      else if (kind === 'decide') { const yes = btn && btn.dataset.yes === '1';
        if (yes && !confirm('Do this now?')) return;
        const r = await run('decide', {action: form.dataset.id, yes, hash: form.dataset.h}); dropInc(); await changed(r.say || (yes ? 'Approved.' : 'Refused.')); }
      else if (kind === 'close') { await run('incident_close', {incident: form.dataset.id, lessons: g('lessons')}); ST.inc = ''; dropInc(form.dataset.id); await done('Incident closed.'); }
      else if (kind === 'controls') { const ans = {}; for (const [n, v] of fd.entries()) ans[n] = S(v); const r = await run('controls_save', {answers: ans}); await changed(r.say); }
      else if (kind === 'access') { if (!g('text')) throw new Error('Paste your user list.'); ST.out.access = await run('access_review', {text: S(fd.get('text')), leavers: g('leavers')}); await done(ST.out.access.say); }
      else if (kind === 'risk') { const r = await run('risk_save', {title: g('title'), asset: g('asset'), owner: g('owner'), likelihood: Number(g('likelihood')), impact: Number(g('impact')), treatment: g('treatment'), action: g('action')}); await done(r.say); }
      else if (kind === 'vendor') { const ans = {}; for (const [n, v] of fd.entries()) if (n.startsWith('q_')) ans[n.slice(2)] = S(v);
        await done((await run('vendor_save', {name: g('name'), service: g('service'), data_level: g('data_level'), answers: ans})).say); }
      else if (kind === 'ttdone') { await done((await run('tabletop_finish', {id: form.dataset.id, lessons: g('lessons'), minutes: g('minutes')})).say); }
      else if (kind === 'train') { await done((await run('training_record', {person: g('person'), topic: g('topic')})).say); }
      else if (kind === 'policy') { const r = await run('policy_check', {min_length: Number(g('min_length') || 8), mfa: g('mfa'), rotation_days: Number(g('rotation_days') || 0), lockout: Number(g('lockout') || 0),
          composition: fd.get('composition') === 'on', breached_check: fd.get('breached_check') === 'on', manager: fd.get('manager') === 'on'}); await changed(r.say); }
      else if (kind === 'cyset') { await run('settings', {country: g('country').toUpperCase(), sector: g('sector'), extra_countries: g('extra_countries'), morning_time: g('morning_time'),
          own_ips: g('own_ips'), crown_hosts: g('crown_hosts'), vip_names: g('vip_names'), work_emails: g('work_emails'), link_provider: g('link_provider'), rules: g('rules')}); dropInc(); await changed('Saved.'); }
      else if (kind === 'key') { const tok = S(fd.get('token')).trim(); if (!tok) throw new Error('Paste the key.'); await run('key_set', {provider: form.dataset.p, token: tok, extra: g('extra')}); form.reset(); await changed('Key saved, sealed.'); }
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
    const box = $('#cyFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/cydesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'cy' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


