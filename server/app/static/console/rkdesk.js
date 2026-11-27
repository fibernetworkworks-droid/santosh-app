/* RISK DESK - the Risk Desk employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE RISK DESK
   SAME WAY"). A thin top bar, then the Risk Desk chat (its own conversation, kind 'risk') beside the desk's pages: Today, Portfolio &
   orders, Applications, Loan book, Surveillance, Valuation, Settings. The pages call /api/riskdesk/do/<part>, which runs the riskdesk
   engine on her desk. Hoola never places an order, decides a loan, blocks a payment or accuses anyone. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M8 13l3-3 2 2 3-3"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['portfolio', 'Portfolio & orders'], ['credit', 'Applications'], ['book', 'Loan book'], ['watch', 'Surveillance'],
    ['value', 'Valuation'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Summarise the desk for the risk committee', 'What is outside our limits?'],
    portfolio: ['Why is this outside the mandate?', 'Explain the rebalance proposal', 'What does this order ticket check?'],
    credit: ['Why did this application miss a rule?', 'What should we ask the applicant for?', 'Explain the key facts in plain words'],
    book: ['Which accounts are slipping?', 'Explain the expected loss by stage', 'What does SMA-2 mean?'],
    watch: ['Explain this rule hit', 'What should the analyst check next?', 'Why can a round trip be genuine?'],
    value: ['Which assumption moves the value most?', 'Explain the sensitivity grid', 'Why is the terminal value so large?'],
    settings: ['What drift tolerance do managers use?', 'What is a usual velocity limit?', 'Why set a price-deviation check?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.riskdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.riskdesk.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const CAN = () => !!(ST.d && ST.d.can_write);
  const cur = () => (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 6});
  const RN = r => ((ST.d && ST.d.roles) || {})[r] || r;
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16).replace(' ', 'T')).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/riskdesk/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/riskdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Risk Desk is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="rkHire">Hire the Risk Desk</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#rkHire').onclick = async () => { try { await api('POST', '/api/employees/risk_desk/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Risk Desk</div><div class="sd-site" id="rkSite"></div></div>
          <span id="rkState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="rkBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Risk Desk chat">
          <div class="sd-chathead"><div class="t"><b>Risk Desk chat</b><span>Ask about a holding, an order ticket, an application, an account or a hit - or drop a file here; the last 4 of an account is enough</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="rkFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="rkPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Risk desk" id="sdTabs"></nav>
          <div id="rkPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works from your rows. It never places, decides, blocks or accuses.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a ticket, an application or an account…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#rkPick').click()});
    $('#rkPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.riskdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.riskdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/riskdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#rkBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/riskdesk/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#rkPage').addEventListener('click', onPageClick);
    $('#rkPage').addEventListener('submit', onSubmit);
    $('#rkPage').addEventListener('change', onChange);
    $('#rkPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#rkState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#rkSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#rkBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), pf = (k.portfolio || {}).drift || {}, tk = (k.portfolio || {}).tickets || {}, dp = (k.book || {}).dpd || {},
      vc = (k.watch || {}).velocity || {}, tr = (k.watch || {}).trips || {};
    const n = ok ? {portfolio: ((pf.alerts || []).length + (tk.to_decide || 0)) || '', credit: ((k.credit || {}).applicants || []).filter(a => (a.exceptions || []).length && !a.decision).length || '',
      book: dp.to_decide || '', watch: ((vc.rule_hits ? vc.open : 0) + (tr.round_trips ? tr.open : 0)) || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/riskdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#rkPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, portfolio: pPortfolio, credit: pCredit, book: pBook, watch: pWatch, value: pValue, settings: pSettings}[ST.tab] || pToday;
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
  const ro = () => CAN() ? '' : `<p class="cs-note">You read this desk as ${esc(RN(ST.d.role))}. Changing it needs the owner, an accountant or an approver.</p>`;
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

  /* ---------------------------------------------------------------- setup */
  function pSetup() {
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.fo, '')}</div>
      <div><h1 class="sd-h">Set up your risk desk</h1><p class="lead">A portfolio checked against your mandate limits, with rebalance proposals for the manager; order tickets prepared with checks on your limits; applications run against your own credit rules; key fact statements; the loan book by days past due and an expected-loss working paper; payments and trades checked for patterns on your limits; a valuation of your own assumptions. Hoola never places an order, decides a loan, blocks a payment or accuses anyone.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('rkS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then drop your holdings on Portfolio &amp; orders, or your loan book on Loan book.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="Acme risk desk"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;
  const ok_ = o => o && !o.empty && !o.error;
  const BANDS = [['standard(0)', 'Not overdue', 'a0'], ['SMA-0(1-30)', '1-30 days', 'a1'], ['SMA-1(31-60)', '31-60 days', 'a2'], ['SMA-2(61-90)', '61-90 days', 'a3'], ['NPA-suggested', 'Past your NPA line', 'a4']];
  const BAND = b => (BANDS.find(x => x[0] === b) || [b, b])[1];
  const FIELD = {foir_pct: 'Repayments to income %', income_monthly: 'Monthly income', obligations_monthly: 'Repayments now', requested_emi: 'New repayment'};
  const fname = f => FIELD[f] || cap(S(f).replace(/_/g, ' '));
  const LV = {stop: ['Stop', 'bad'], check: ['Check', 'warn'], caution: ['Caution', 'warn'], info: ['Note', 'v']};
  const pct = v => (v === null || v === undefined) ? '—' : `${num(Math.round(Number(v) * 100) / 100)}%`;
  const decided = d => d ? `<div class="pb-dec"><b>Decision:</b> ${esc(d.decision)} <span class="mut">- ${esc(S(d.by).replace(/ <.*>$/, ''))}, ${esc(dt(d.on))}</span>${CAN() ? ` <button class="btn soft sm" type="button" data-undec="1">Change</button>` : ''}</div>` : '';
  const decForm = (key, d, label, ph) => d ? `<div data-deckey="${esc(key)}">${decided(d)}</div>` : CAN() ? `<form class="mk-add" data-form="decide" data-key="${esc(key)}"><label class="ins-lab" style="flex:1 1 320px">${esc(label)}<input class="in" name="decision" maxlength="240" placeholder="${esc(ph)}"></label><button class="btn soft" type="submit">Record the decision</button></form>` : '';

  /* ---- charts of this desk */
  function bandBar(b) {   /* the loan book as one stacked bar of days-past-due bands */
    const tot = BANDS.reduce((s, x) => s + (Number(b.buckets[x[0]]) || 0), 0);
    if (!tot) return '<p class="cs-pos" style="margin:0">Nothing outstanding.</p>';
    return `<div class="fo-age" role="img" aria-label="The loan book by days past due">${BANDS.map(([k, n, c]) => b.buckets[k] ? `<b class="${c}" style="width:${(b.buckets[k] / tot * 100).toFixed(2)}%" title="${esc(n)} ${esc(m2(b.buckets[k]))}"></b>` : '').join('')}</div>
      <div class="fo-leg">${BANDS.map(([k, n, c]) => `<span><i class="${c}"></i>${esc(k === 'NPA-suggested' ? `Past ${b.npa_days_used} days` : n)}<b>${esc(m0(b.buckets[k] || 0))}</b></span>`).join('')}</div>`;
  }
  function driftRow(d) {   /* current weight against her target, with the tolerance band */
    const top = Math.max(d.current_pct, d.target_pct) * 1.25 || 1, w = Math.min(100, d.current_pct / top * 100), t = Math.min(100, d.target_pct / top * 100);
    return `<div class="fo-rat"><span>${esc(d.name)}<em class="mut" style="display:block;font-size:12.5px">target ${esc(pct(d.target_pct))}</em></span><i><b class="${d.outside_tolerance ? 'bad' : 'ok'}" style="width:${w.toFixed(1)}%"></b><u style="left:${t.toFixed(1)}%" title="your target ${esc(d.target_pct)}%"></u></i>
      <em class="${d.outside_tolerance ? 'cs-neg' : ''}">${esc(pct(d.current_pct))} <span class="mut">${esc(sgn(d.drift_pct))}</span></em></div>`;
  }
  function sensGrid(m) {   /* equity value at each discount rate (rows) x terminal growth (columns), coloured against the base */
    const base = m.equity_value, vals = m.sensitivity.flatMap(r => r.equity_value.map(c => c.value)).filter(v => v !== null);
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const shade = v => v === null ? 'na' : v === base ? 'base' : v > base ? 'up' + Math.min(3, Math.ceil((v - base) / ((hi - base) || 1) * 3)) : 'dn' + Math.min(3, Math.ceil((base - v) / ((base - lo) || 1) * 3));
    const g = m.sensitivity[0].equity_value.map(c => c.growth_pct);
    return `<div class="iv-tw"><table class="tb rk-sens"><thead><tr><th>Discount rate ↓ · growth →</th>${g.map(x => `<th class="r">${esc(pct(x))}</th>`).join('')}</tr></thead><tbody>${m.sensitivity.map(r => `<tr><th>${esc(pct(r.discount_pct))}</th>${r.equity_value.map(c => `<td class="r ${shade(c.value)}">${c.value === null ? '—' : esc(short(c.value))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), pf = (k.portfolio || {}).drift || {}, tk = (k.portfolio || {}).tickets || {}, cr = k.credit || {}, dp = (k.book || {}).dpd || {},
      el = (k.book || {}).ecl || {}, vc = (k.watch || {}).velocity || {}, tr = (k.watch || {}).trips || {};
    const has = k.counts && Object.values(k.counts).some(Boolean);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : has ? 'Everything on the desk is within your limits.' : 'Drop your holdings or your loan book to start.';
    const tiles = [];
    tiles.push(`<div class="k${ok_(pf) && pf.alerts.length ? ' low bad' : ''}"><div class="l">Portfolio</div><div class="v">${ok_(pf) ? esc(m0(pf.total_value)) : '—'}</div><div class="s">${ok_(pf) ? (pf.alerts.length ? esc(pl(pf.alerts.length, 'mandate breach', 'mandate breaches')) : 'within your mandate') : 'no holdings yet'}</div></div>`);
    tiles.push(`<div class="k${tk.to_decide ? ' low bad' : ''}"><div class="l">Order tickets</div><div class="v">${esc(num((tk.rows || []).length))}</div><div class="s">${tk.to_decide ? esc(pl(tk.to_decide, 'check')) + ' to clear' : 'none placed from here'}</div></div>`);
    const npa = ok_(dp) ? dp.buckets['NPA-suggested'] || 0 : null;
    tiles.push(`<div class="k${npa ? ' low bad' : ''}"><div class="l">Loan book</div><div class="v">${ok_(dp) ? esc(m0(dp.total)) : '—'}</div><div class="s">${ok_(dp) ? esc(m0(npa)) + ` past ${dp.npa_days_used} days` : 'no loan accounts yet'}</div></div>`);
    const open = (ok_(vc) && !vc.need_limits ? vc.open : 0) + (ok_(tr) ? tr.open : 0);
    tiles.push(`<div class="k${open ? ' low bad' : ''}"><div class="l">To review</div><div class="v">${esc(num(open))}</div><div class="s">${ok_(el) ? 'expected loss ' + esc(m0(el.total_ecl)) : 'payment and trade patterns'}</div></div>`);
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Where the money sits</h2><div class="r"><button class="btn soft sm" type="button" data-go="portfolio">Open</button></div></div>
          ${ok_(pf) ? ring(Object.keys(pf.groups).length ? Object.entries(pf.groups).map(([g, w], i) => [g + ' %', Math.round(w * 10) / 10, 'rk-c' + (i % 6)]) : pf.weights.slice(0, 6).map((x, i) => [x.symbol + ' %', Math.round(x.weight_pct * 10) / 10, 'rk-c' + (i % 6)]), short(pf.total_value), cur(), 'Portfolio by group') : empty(pf.error || 'Drop your holdings on Portfolio & orders.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The loan book</h2><div class="r"><button class="btn soft sm" type="button" data-go="book">Open</button></div></div>
          ${ok_(dp) ? bandBar(dp) : empty(dp.error || 'Drop your loan accounts on Loan book.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Applications</h2><div class="r"><button class="btn soft sm" type="button" data-go="credit">Open</button></div></div>
          ${(cr.applicants || []).length ? (cr.applicants.slice(0, 6).map(a => `<div class="cs-row"><span class="cs-dot${(a.exceptions || []).length && !a.decision ? ' bad' : ''}"></span><span style="flex:1">${esc(a.name)}</span>${a.need_rules ? tag('no rules yet', 'warn') : a.decision ? tag('decided', 'v') : (a.exceptions || []).length ? tag(pl(a.exceptions.length, 'exception'), 'bad') : tag('meets your rules', 'ok')}</div>`).join('')) : empty('No applications yet.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- portfolio + tickets */
  function pPortfolio() {
    const k = K(), pf = (k.portfolio || {}).drift || {}, tk = (k.portfolio || {}).tickets || {}, c = k.counts || {};
    return `<div><h1 class="sd-h">Portfolio &amp; orders</h1><p class="lead">Your holdings weighed, set against your target mix and your mandate limits, with rebalance proposals for the portfolio manager. Order tickets are prepared and checked on your limits - an order is placed only by your own tap at your broker. Hoola never says what to buy or sell.</p></div>
      ${ro()}${err(pf)}
      ${ok_(pf) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Total value', esc(m0(pf.total_value)))}${kpi('Holdings', esc(num(pf.weights.length)))}${kpi('Outside your mandate', esc(num(pf.alerts.length)), '', pf.alerts.length ? 'bad' : 'cs-pos')}${kpi('Margin used', pf.margin ? esc(pct(pf.margin.utilisation_pct)) : '—', pf.margin ? '' : 'set in Settings', pf.margin && pf.margin.alert ? 'bad' : '')}</section>
        ${pf.no_limits ? '<p class="cs-note">No mandate limits yet - set the largest single holding and the largest group in Settings to check against them.</p>' : ''}
        ${pf.alerts.length ? `<section class="card"><h2 class="md-h2">Outside your mandate</h2><div class="pb-tests">${pf.alerts.map(a => `<code class="bad">${esc(a)}</code>`).join('')}</div></section>` : ''}
        <div class="md-2" style="align-items:start">
          <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Weights</h2><div class="r"><button class="btn soft sm" type="button" data-dl="weights">CSV</button></div></div>
            ${bars(pf.weights.slice(0, 12).map(x => [x.symbol, x.weight_pct, 'mk-b', x.group]), pct, 'Weights by holding')}</section>
          <section class="card"><h2 class="md-h2">Against your targets</h2>
            ${pf.drift.length ? `<div class="fo-rats">${pf.drift.map(driftRow).join('')}</div>${pf.no_tolerance ? '<p class="cs-note" style="margin:10px 0 0">No tolerance set - every difference counts. Set yours in Settings.</p>' : ''}` : empty('Drop your target mix to see the drift.')}</section></div>
        ${pf.proposals.length ? `<section class="card"><h2 class="md-h2">Rebalance proposals</h2>${pf.proposals.map(p => `<div class="pb-res ${p.decision ? 'ok' : 'bad'}" data-deckey="${esc(p.key)}"><div class="h"><b>${esc(p.name)}</b>${tag(p.move_value > 0 ? 'Add' : 'Reduce', p.move_value > 0 ? 'ok' : 'warn')}<span class="pb-amt">${esc(m0(Math.abs(p.move_value)))}</span></div>
            <p class="mut" style="margin:4px 0 0">${esc(p.note)}</p>${decForm(p.key, p.decision, "The portfolio manager's decision", 'Trim next week, after results')}</div>`).join('')}</section>` : ''}
        <p class="cs-note">${esc(pf.not_checked)} ${esc(pf.decider)}</p>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Holdings</h2>${uploader('holdings', `Holdings (CSV)${c.holdings ? ' · ' + num(c.holdings) : ''}`, 'Columns: symbol, qty, price, group (sector or asset class).')}</section>
        <section class="card"><h2 class="md-h2">Your target mix</h2>${uploader('targets', `Target weights (CSV)${c.targets ? ' · ' + num(c.targets) : ''}`, 'Columns: name (a holding or a group), target %.')}
          ${(k.targets || []).length ? listRows('targets', k.targets, [['name', 'Name'], ['pct', 'Target %', 1]]) : ''}</section></div>
      <section class="card"><h2 class="md-h2">Order tickets</h2>
        ${(tk.missing_limits || []).length ? `<p class="cs-note" style="margin:0 0 10px">Not checked yet - set in Settings: ${esc(tk.missing_limits.join('; '))}.</p>` : ''}
        ${(tk.rows || []).map(t => t.error ? `<div class="pb-res bad"><b>${esc(t.ticket.symbol)}</b>${err(t)}</div>` : `<div class="pb-res rk-tk ${t.worst === 'stop' ? 'bad' : t.worst ? 'warn' : 'ok'}" data-deckey="${esc(t.key)}">
          <div class="h"><b>${esc(t.confirm_text)}</b>${tag(t.ticket.product, 'v')}${t.worst ? tag(LV[t.worst][0], LV[t.worst][1]) : tag('No check fired', 'ok')}<span style="flex:1"></span>${rmBtn('tickets', t.n)}</div>
          ${t.note ? `<p class="mut" style="margin:4px 0">${esc(t.note)}</p>` : ''}
          ${t.flags.map(f => `<div class="rk-flag ${esc(f.level)}"><span>${esc(LV[f.level][0])}</span>${esc(f.text)}</div>`).join('')}
          <div class="rk-tkf"><span>Value <b>${esc(t.ticket.est_value ? m0(t.ticket.est_value) : '—')}</b></span><span>Charges <b>${esc(t.ticket.est_charges ? m2(t.ticket.est_charges.total) : '—')}</b></span><span class="mut">${esc(t.ticket.est_charges ? t.ticket.est_charges.basis : t.charges_note)}</span></div>
          <p class="cs-note" style="margin:6px 0 0">Not sent. ${esc(t.not_checked)}</p>
          ${t.worst === 'stop' || t.worst === 'check' ? decForm(t.key, t.decision, 'What the investor decided', 'Cancelled - the quantity was a typo') : ''}${ask('Order ticket ' + t.confirm_text)}</div>`).join('') || empty('No order ticket yet.')}
        ${CAN() ? `<form class="mk-add" data-form="ticket" style="margin-top:12px">
          <label class="ins-lab">Symbol<input class="in" name="symbol" required maxlength="30" placeholder="INFY"></label>
          <label class="ins-lab">Side<select class="in" name="side"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
          <label class="ins-lab">Qty<input class="in" name="qty" required inputmode="numeric"></label>
          <label class="ins-lab">Type<select class="in" name="order_type"><option value="limit">Limit</option><option value="market">Market</option><option value="stoploss">Stop-loss</option></select></label>
          <label class="ins-lab">Price<input class="in" name="price" inputmode="decimal"></label>
          <label class="ins-lab">Last price<input class="in" name="ltp" inputmode="decimal"></label>
          <label class="ins-lab">Product<select class="in" name="product"><option value="delivery">Delivery</option><option value="intraday">Intraday</option><option value="margin">Margin</option></select></label>
          <label class="ins-lab" style="flex:1 1 220px">Note<input class="in" name="note" maxlength="160" placeholder="Why this order"></label>
          <button class="btn soft" type="submit">Prepare the ticket</button></form>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- applications */
  function pCredit() {
    const k = K(), cr = k.credit || {}, c = k.counts || {};
    return `<div><h1 class="sd-h">Applications</h1><p class="lead">Each application run against your own policy rules: which rule was missed, the reason code to explain to the customer, and what is missing. Rules on religion, caste, gender, locality or their proxies are refused. Approving or declining is the credit officer's - Hoola gives no score and no 'approve'.</p></div>
      ${ro()}
      ${!cr.rules ? '<p class="cs-note">No policy rules yet - add yours below. Hoola has no rules of its own.</p>' : ''}
      ${(cr.applicants || []).map(a => `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(a.name)}</h2><div class="r">${a.need_rules ? tag('no rules yet', 'warn') : (a.exceptions || []).length ? tag(pl(a.exceptions.length, 'exception'), 'bad') : a.error ? '' : tag('Meets your rules', 'ok')}${rmBtn('applicants', a.n)}</div></div>
          <p class="mut" style="margin:0 0 12px">${esc(a.product || 'Product not given')}${a.amount ? ' · ' + esc(m0(a.amount)) : ''}${a.foir_pct !== undefined && a.foir_pct !== null ? ` · repayments ${esc(pct(a.foir_pct))} of income` : ''}</p>
          ${err(a)}${a.foir_pct !== undefined && a.foir_pct !== null ? gauge(a.foir_pct, ((k.rules || []).find(r => r.field === 'foir_pct') || {}).value) : ''}
          ${(a.rule_hits || []).length ? `<div class="iv-tw" style="margin-top:12px"><table class="tb"><thead><tr><th>Reason code</th><th>Check</th><th>Your rule</th><th>The applicant</th><th></th></tr></thead><tbody>${a.rule_hits.map(h => `<tr><td><b>${esc(h.code)}</b></td><td>${esc(fname(h.field))}</td><td>${esc(h.required)}</td><td class="cs-neg">${esc(h.actual)}</td><td>${tag(h.severity, h.severity === 'decline' ? 'bad' : h.severity === 'info' ? 'v' : 'warn')}</td></tr>`).join('')}</tbody></table></div>` : ''}
          ${(a.missing_inputs || []).length ? `<p class="cs-note" style="margin:10px 0 0">Not run - missing: ${esc(a.missing_inputs.map(m => fname(m.field)).join(', '))}.</p>` : ''}
          ${!a.need_rules && !a.error ? decForm(a.key, a.decision, "The credit officer's decision", 'Referred to committee on 12 June') : ''}${ask('Application ' + a.name)}</section>`).join('')}
      ${CAN() ? `<form class="card" data-form="applicant"><h2 class="md-h2">Add an application</h2>
        <div class="fo-grid"><label class="ins-lab">Applicant<input class="in" name="name" required maxlength="80" placeholder="Asha Rao"></label>
          <label class="ins-lab">Product<input class="in" name="product" maxlength="60" placeholder="Personal loan"></label>
          <label class="ins-lab">Amount asked<input class="in" name="amount" inputmode="decimal"></label>
          <label class="ins-lab">Monthly income<input class="in" name="income_monthly" inputmode="decimal"></label>
          <label class="ins-lab">Monthly repayments now<input class="in" name="obligations_monthly" inputmode="decimal"></label>
          <label class="ins-lab">New repayment asked<input class="in" name="requested_emi" inputmode="decimal"></label></div>
        <label class="ins-lab" style="margin-top:10px">Other details your rules use<input class="in" name="fields" maxlength="600" placeholder="bureau_score = 742; age = 34; years_in_job = 3"></label>
        <div class="md-acts"><span class="mut" style="font-size:13px">From the applicant's own papers - Hoola does not check whether they are true.</span><button class="btn" type="submit">Run your rules</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">Your policy rules</h2>
        ${(k.rules || []).length ? listRows('rules', k.rules, [['code', 'Code'], ['field', 'Check', 0, v => esc(fname(v))], ['op', 'Rule'], ['value', 'Value'], ['severity', 'If missed']]) : ''}
        ${uploader('rules', `Policy rules (CSV)${c.rules ? ' · ' + num(c.rules) : ''}`, 'Columns: field, op (>= <= > < == !=), value, code, severity (info, refer, decline). The rule is what must hold.')}
        ${addForm('rules', [['code', 'Code', '', 'LOW_SCORE'], ['field', 'Check', '', 'bureau_score'], ['op', 'Rule', [['>=', '≥'], ['<=', '≤'], ['>', '>'], ['<', '<'], ['==', '='], ['!=', '≠']]], ['value', 'Value', '', '700'], ['severity', 'If missed', [['refer', 'Refer'], ['decline', 'Decline'], ['info', 'Note']]]], 'Add the rule')}</section>
      <section class="card"><h2 class="md-h2">Key fact statements</h2>
        ${(cr.offers || []).map(o => o.error ? `<div class="pb-res bad"><b>${esc(o.borrower)}</b>${err(o)}</div>` : `<div class="pb-res ok"><div class="h"><b>${esc(o.borrower)}</b><span class="mut">${esc(o.product_name || 'loan')} · ${esc(m0(o.amount))} · ${esc(num(o.rate))}% · ${esc(num(o.months))} months</span><span style="flex:1"></span><button class="btn soft sm" type="button" data-dl="kfs:${esc(o.n)}">Draft</button>${rmBtn('offers', o.n)}</div>
          <div class="rk-tkf"><span>Instalment <b>${esc(m2(o.computed.emi))}</b></span><span>Money received <b>${esc(m0(o.computed.money_received))}</b></span><span>APR <b>${esc(pct(o.computed.apr_nominal_pct))}</b></span><span>Total paid <b>${esc(m0(o.computed.total_paid))}</b></span></div>
          ${o.fee_tax_pct === null || o.fee_tax_pct === undefined ? '<p class="cs-note" style="margin:6px 0 0">No tax on fees added - give your rate if your country charges one.</p>' : ''}
          <details class="ins-more"><summary>The draft</summary><div class="fo-memo">${window.HoolaMD ? HoolaMD.render(S(o.kfs).replace(/^(#.*)$/gm, '\n$1\n')) : `<pre>${esc(o.kfs)}</pre>`}</div></details></div>`).join('') || empty('No offer yet.')}
        ${CAN() ? `<form class="mk-add" data-form="offer" style="margin-top:12px">
          <label class="ins-lab">Borrower<input class="in" name="borrower" required maxlength="80"></label><label class="ins-lab">Lender<input class="in" name="lender" maxlength="80"></label>
          <label class="ins-lab">Product<input class="in" name="product_name" maxlength="60"></label><label class="ins-lab">Amount<input class="in" name="amount" required inputmode="decimal"></label>
          <label class="ins-lab">Rate % a year<input class="in" name="rate" required inputmode="decimal"></label><label class="ins-lab">Months<input class="in" name="months" required inputmode="numeric"></label>
          <label class="ins-lab">Fee %<input class="in" name="fee_pct" inputmode="decimal"></label><label class="ins-lab">Fixed fee<input class="in" name="fee_fixed" inputmode="decimal"></label>
          <label class="ins-lab">Tax on fees %<input class="in" name="fee_tax_pct" inputmode="decimal" placeholder="yours"></label><label class="ins-lab">Insurance<input class="in" name="insurance" inputmode="decimal"></label>
          <label class="ins-lab">Cooling-off days<input class="in" name="cooling_off_days" inputmode="numeric"></label><label class="ins-lab" style="flex:1 1 220px">Grievance contact<input class="in" name="grievance" maxlength="160"></label>
          <button class="btn soft" type="submit">Draft the key facts</button></form>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- loan book */
  function pBook() {
    const k = K(), dp = (k.book || {}).dpd || {}, el = (k.book || {}).ecl || {}, c = k.counts || {};
    return `<div><h1 class="sd-h">Loan book</h1><p class="lead">Every loan account by days past due, and an expected credit loss working paper on your own PD and LGD. Declaring an account non-performing, and any notice or recovery step, is the credit and legal teams'; the provision is the risk committee's.</p></div>
      ${ro()}${err(dp)}
      ${ok_(dp) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Outstanding', esc(m0(dp.total)))}${kpi('Accounts', esc(num(dp.accounts.length)))}${kpi('61-90 days', esc(m0(dp.buckets['SMA-2(61-90)'])), '', dp.buckets['SMA-2(61-90)'] ? 'warn' : '')}${kpi(`Past ${dp.npa_days_used} days`, esc(m0(dp.buckets['NPA-suggested'])), pl(dp.to_decide, 'to classify', 'to classify'), dp.buckets['NPA-suggested'] ? 'bad' : '')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">By days past due</h2><div class="r"><button class="btn soft sm" type="button" data-dl="dpd">CSV</button></div></div>
          ${bandBar(dp)}
          <p class="cs-note" style="margin:12px 0 0">${esc(dp.note)}${dp.npa_yours ? '' : ' The 90-day line is the default - set yours in Settings.'}</p>
          ${dp.accounts.filter(x => x.bucket === 'SMA-2(61-90)' || x.bucket === 'NPA-suggested').map(x => `<div class="pb-res ${x.bucket === 'NPA-suggested' ? 'bad' : 'warn'}" data-deckey="${esc(x.key)}"><div class="h"><b>${esc(x.id)}</b><span class="mut">${esc(num(x.dpd))} days past due</span>${tag(x.bucket === 'NPA-suggested' ? `Past ${dp.npa_days_used} days` : BAND(x.bucket), x.bucket === 'NPA-suggested' ? 'bad' : 'warn')}<span class="pb-amt">${esc(m2(x.outstanding))}</span></div>
            ${decForm(x.key, x.decision, "The credit team's decision", x.bucket === 'NPA-suggested' ? 'Classified NPA from 1 July - notice by legal' : 'On the watch list - calling the borrower this week')}${ask('Loan account ' + x.id)}</div>`).join('')}
          <details class="ins-more" style="margin-top:12px"><summary>Every account (${esc(num(dp.accounts.length))})</summary><div class="iv-tw"><table class="tb"><thead><tr><th>Account</th><th class="r">Outstanding</th><th class="r">Days past due</th><th>Band</th></tr></thead><tbody>${dp.accounts.slice(0, 400).map(x => `<tr><td>${esc(x.id)}</td><td class="r">${esc(m2(x.outstanding))}</td><td class="r">${esc(num(x.dpd))}</td><td>${tag(BAND(x.bucket), x.bucket === 'standard(0)' ? 'ok' : x.bucket === 'NPA-suggested' ? 'bad' : 'warn')}</td></tr>`).join('')}</tbody></table></div></details></section>` : ''}
      ${uploader('loans', `Loan accounts (CSV)${c.loans ? ' · ' + num(c.loans) + ' on the desk' : ''}`, 'Columns: id, outstanding, oldest due date.')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Expected credit loss</h2><div class="r">${ok_(el) ? '<button class="btn soft sm" type="button" data-dl="ecl">CSV</button>' : ''}</div></div>
        ${err(el)}${ok_(el) ? `<div class="md-2" style="align-items:center">${ring([['Stage 1', el.by_stage.stage1, 'rk-c0'], ['Stage 2', el.by_stage.stage2, 'rk-c3'], ['Stage 3', el.by_stage.stage3, 'rk-c1']], short(el.total_ecl), cur(), 'Expected loss by stage')}
          <div><div class="cs-row"><span style="flex:1">Exposure</span><b>${esc(m0(el.ead))}</b></div><div class="cs-row"><span style="flex:1">Expected loss</span><b>${esc(m0(el.total_ecl))}</b></div><div class="cs-row"><span style="flex:1">Coverage</span><b>${esc(pct(el.ead ? el.total_ecl / el.ead * 100 : 0))}</b></div></div></div>
          ${el.flags.length ? `<div class="pb-tests" style="margin-top:10px">${el.flags.map(f => `<code class="bad">${esc(f)}</code>`).join('')}</div>` : ''}
          <p class="cs-note" style="margin:12px 0 0">${esc(el.method)} ${esc(el.not_checked)}</p>` : ''}
        ${uploader('exposures', `Exposures (CSV)${c.exposures ? ' · ' + num(c.exposures) : ''}`, 'Columns: id, ead, pd (0-1), lgd (0-1), dpd or stage, pd lifetime. Your PD and LGD.')}</section>`;
  }

  /* ---------------------------------------------------------------- surveillance */
  function pWatch() {
    const k = K(), vc = (k.watch || {}).velocity || {}, tr = (k.watch || {}).trips || {}, c = k.counts || {};
    const hits = ok_(vc) && vc.rule_hits ? vc.rule_hits : [];
    return `<div><h1 class="sd-h">Surveillance</h1><p class="lead">Payments checked against your own velocity limits, and trades for the same client buying and selling the same share in a short time. These are rule hits and patterns - evidence for the fraud analyst and the surveillance officer, never a block and never an accusation. Account numbers are kept only as a fingerprint and the last 4.</p></div>
      ${ro()}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Payment velocity</h2><div class="r">${hits.length || (tr.round_trips || []).length ? '<button class="btn soft sm" type="button" data-dl="hits">CSV</button>' : ''}</div></div>
        ${vc.need_limits ? `<p class="cs-note" style="margin:0 0 10px">${esc(pl(vc.txns, 'payment'))} on the desk. Set your window and count in Settings - Hoola has no limits of its own.</p>` : err(vc)}
        ${ok_(vc) && vc.rule_hits ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(3,minmax(0,1fr));margin:0 0 14px">${kpi('Accounts', esc(num(vc.accounts_seen)))}${kpi('Rule hits', esc(num(hits.length)), '', hits.length ? 'warn' : 'cs-pos')}${kpi('Open', esc(num(vc.open)), `more than ${num(vc.limits.max_count)} in ${num(vc.limits.window_minutes)} min`, vc.open ? 'bad' : '')}</section>
          ${hits.length ? bars(hits.map(h => [h.rule === 'velocity' ? 'Account ' + h.account : 'Device ' + h.device, h.count, h.rule === 'velocity' ? 'dg-dn' : 'mk-age1', h.rule === 'velocity' ? 'payments in the window' : 'accounts on one device']), num, 'Rule hits') : '<p class="cs-pos" style="margin:0">No rule fired on your limits.</p>'}
          ${hits.map(h => `<div class="pb-res ${h.decision ? 'ok' : 'bad'}" data-deckey="${esc(h.key)}"><div class="h"><b>${h.rule === 'velocity' ? 'Account ' + esc(h.account) : 'Device ' + esc(h.device)}</b>${tag(h.rule === 'velocity' ? 'Velocity' : 'Shared device', 'warn')}${h.amount !== undefined ? `<span class="pb-amt">${esc(m2(h.amount))}</span>` : ''}</div>
            <p class="mut" style="margin:4px 0">${h.rule === 'velocity' ? `${esc(pl(h.count, 'payment'))} between ${esc(dt(h.from))} and ${esc(dt(h.to))}.` : `Used by ${esc(pl(h.count, 'account'))}: ${esc(h.accounts.join(', '))}.`}</p>
            ${decForm(h.key, h.decision, "The fraud analyst's decision", h.rule === 'velocity' ? 'Released - the customer confirmed by call' : 'Checked - one family shares the phone')}${ask(h.rule === 'velocity' ? 'Velocity on account ' + h.account : 'Shared device ' + h.device)}</div>`).join('')}
          <p class="cs-note" style="margin:12px 0 0">${esc(vc.not_checked)} ${esc(vc.decider)}</p>` : ''}
        ${uploader('txns', `Payments (CSV)${c.txns ? ' · ' + num(c.txns) + ' on the desk' : ''}`, 'Columns: account, time (2026-11-05 14:30), amount, device.')}</section>
      <section class="card"><h2 class="md-h2">Round-trip trades</h2>${err(tr)}
        ${ok_(tr) ? `${(tr.round_trips || []).map(t => `<div class="pb-res ${t.decision ? 'ok' : 'warn'}" data-deckey="${esc(t.key)}"><div class="h"><b>${esc(t.client)}</b><span class="mut">${esc(t.symbol)}</span>${tag('Round trip', 'warn')}</div>
            <div class="rk-tkf"><span>Bought <b>${esc(num(t.buy.qty))} @ ${esc(num(t.buy.price))}</b> ${esc(dt(t.buy.ts))}</span><span>Sold <b>${esc(num(t.sell.qty))} @ ${esc(num(t.sell.price))}</b> ${esc(dt(t.sell.ts))}</span></div>
            <p class="mut" style="margin:4px 0">${esc(t.why)}</p>${decForm(t.key, t.decision, "The surveillance officer's decision", 'Closed - a hedge, documents on file')}</div>`).join('') || `<p class="cs-pos" style="margin:0">No round trip across ${esc(pl(tr.clients, 'client'))}.</p>`}
          <p class="cs-note" style="margin:12px 0 0">${esc(tr.note)} ${esc(tr.not_checked)}</p>` : ''}
        ${uploader('trades', `Trades (CSV)${c.trades ? ' · ' + num(c.trades) : ''}`, 'Columns: client, symbol, side, qty, price, time.')}</section>`;
  }

  /* ---------------------------------------------------------------- valuation */
  function pValue() {
    const k = K(), vl = k.value || {};
    return `<div><h1 class="sd-h">Valuation</h1><p class="lead">A discounted cash flow of your own cash flows, discount rate and terminal growth, with a grid of how the value moves when they change. This is the arithmetic of your assumptions - an opinion on value is a registered valuer's, and it is never a view on whether to buy or sell.</p></div>
      ${ro()}
      ${ok_(vl) ? vl.models.map(m => m.error ? `<section class="card"><b>${esc(m.name)}</b>${err(m)}</section>` : `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(m.name)}</h2><div class="r">${rmBtn('models', m.n)}</div></div>
          <p class="mut" style="margin:0 0 12px">${esc(m.inputs.cashflows.map(short).join(' · '))} · discount ${esc(pct(m.inputs.discount_pct))} · growth ${esc(pct(m.inputs.terminal_growth_pct))}</p>
          <section class="iv-kpis mk-k2" style="grid-template-columns:repeat(${m.per_share !== undefined ? 4 : 3},minmax(0,1fr));margin:0 0 14px">${kpi('Enterprise value', esc(m0(m.enterprise_value)))}${kpi('Equity value', esc(m0(m.equity_value)), 'after net debt ' + m0(m.inputs.net_debt))}${m.per_share !== undefined ? kpi('Per share', esc(m2(m.per_share))) : ''}${kpi('In the terminal value', esc(pct(m.terminal_share_pct)), '', m.terminal_share_pct > 75 ? 'warn' : '')}</section>
          <div class="md-2" style="align-items:start"><div>${ring([['The years you forecast', Math.round(m.pv_explicit), 'rk-c0'], ['After them (terminal)', Math.round(m.pv_terminal), 'rk-c3']], short(m.enterprise_value), cur(), 'Where the value comes from')}</div><div>${sensGrid(m)}</div></div>
          ${m.flags.length ? `<div class="pb-tests" style="margin-top:10px">${m.flags.map(f => `<code class="bad">${esc(f)}</code>`).join('')}</div>` : ''}
          <p class="cs-note" style="margin:12px 0 0">${esc(m.not_checked)} ${esc(m.decider)}</p>${ask('Valuation of ' + m.name)}</section>`).join('') : ''}
      ${CAN() ? `<form class="card" data-form="model"><h2 class="md-h2">Value a business</h2>
        <div class="fo-grid"><label class="ins-lab">What<input class="in" name="name" required maxlength="80" placeholder="Acme Ltd"></label>
          <label class="ins-lab" style="grid-column:span 2">Free cash flow, year by year<input class="in" name="cashflows" required placeholder="120, 135, 150, 160, 170"></label>
          <label class="ins-lab">Discount rate %<input class="in" name="discount_pct" required inputmode="decimal" placeholder="yours"></label>
          <label class="ins-lab">Terminal growth %<input class="in" name="terminal_growth_pct" required inputmode="decimal" placeholder="yours"></label>
          <label class="ins-lab">Net debt<input class="in" name="net_debt" inputmode="decimal" placeholder="0"></label>
          <label class="ins-lab">Shares<input class="in" name="shares" inputmode="decimal"></label></div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Your forecast and your rates - Hoola does not check them.</span><button class="btn" type="submit">Work it out</button></div></form>` : ''}
      ${vl.empty && !CAN() ? empty('No valuation yet.') : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, l = s.limits || {}, rt = s.rates || {}, w = W();
    const fld = (n, lab, v, ph, i) => `<div class="md-field"><label for="rkT${i}">${lab}</label><input class="in" id="rkT${i}" name="${n}" inputmode="decimal" value="${esc(v ?? '')}" placeholder="${esc(ph || 'yours')}"></div>`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your mandate limits, order checks, velocity limits and the loan-book line. Every one is yours, from your own policy - Hoola brings none, and says so wherever one is missing.</p></div>
      ${ro()}
      <form class="card" data-form="limits"><h2 class="md-h2">Portfolio mandate</h2><div class="md-form">
        ${fld('tolerance_pct', 'Drift tolerance, points', l.tolerance_pct, '', 1)}${fld('max_single_pct', 'Largest single holding, %', l.max_single_pct, '', 2)}
        ${fld('max_group_pct', 'Largest group, %', l.max_group_pct, '', 3)}${fld('margin_used', `Margin used (${esc(cur())})`, l.margin_used, '', 4)}
        ${fld('margin_available', `Margin available (${esc(cur())})`, l.margin_available, '', 5)}${fld('margin_alert_pct', 'Margin alert at, %', l.margin_alert_pct, '', 6)}</div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="orders"><h2 class="md-h2">Order checks</h2><div class="md-form">
          ${fld('max_pct_of_portfolio', 'One order at most, % of the portfolio', l.max_pct_of_portfolio, '', 7)}${fld('max_price_deviation_pct', 'Limit price within, % of the last price', l.max_price_deviation_pct, '', 8)}
          ${fld('brokerage_pct', 'Brokerage, %', rt.brokerage_pct, '', 9)}${fld('brokerage_cap', `Brokerage cap (${esc(cur())})`, rt.brokerage_cap, '', 10)}
          ${fld('other_pct', 'Other charges, %', rt.other_pct, '', 11)}</div>
          ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">From your broker\'s rate card.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <form class="card" data-form="watchset"><h2 class="md-h2">Velocity and loan book</h2><div class="md-form">
          ${fld('window_minutes', 'Window, minutes', l.window_minutes, '', 12)}${fld('max_count', 'More than this many payments', l.max_count, '', 13)}
          ${fld('max_amount', `Or more than this in the window (${esc(cur())})`, l.max_amount, '', 14)}${fld('npa_days', 'Days past due for the NPA line', l.npa_days, '90', 15)}
          <div class="md-field"><label for="rkT16">Age the loan book as of</label><input class="in" id="rkT16" name="as_of" type="date" value="${esc(s.as_of || '')}"></div></div>
          ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Empty date = today.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({holdings: 'holdings', targets: 'target weights', rules: 'policy rules', loans: 'loan accounts', exposures: 'exposures', txns: 'payments', trades: 'trades', applicants: 'applications', tickets: 'order tickets', offers: 'loan offers', models: 'valuations'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind)} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">Country</span><b>${esc(k.country || '—')}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('rkN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/riskdesk/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.csv`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary') && !t.closest('[data-rm]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { setCtx(ak.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    try {
      const ud = t.closest('[data-undec]'); if (ud) { const box = ud.closest('[data-deckey]'); await run('decide', {key: box.dataset.deckey, clear: true}); await changed('The decision can be recorded again.'); return; }
      const rm = t.closest('[data-rm]'); if (rm) { e.preventDefault(); await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 20e6) { toast('Up to 20 MB.', true); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name}); fi.value = ''; await changed(r.says + ` from ${f.name}.`); }
    catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    if (form.dataset.form === 'upload') return;
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const sent = () => { form.reset(); form.querySelectorAll('select').forEach(x => { delete x.dataset.touched; }); };
    const done = async m => { sent(); await changed(m); };
    const pick = names => { const a = {}; names.forEach(n => { if (g(n) !== '') a[n] = g(n); }); return a; };
    const all = names => Object.fromEntries(names.map(n => [n, g(n)]));
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/riskdesk/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'decide') { await run('decide', {key: form.dataset.key, decision: g('decision')}); await done('The decision is recorded.'); }
      else if (kind === 'ticket') { await run('ticket', pick(['symbol', 'side', 'qty', 'order_type', 'price', 'ltp', 'product', 'note'])); await done('The ticket is prepared - nothing was sent.'); }
      else if (kind === 'applicant') { await run('applicant', pick(['name', 'product', 'amount', 'income_monthly', 'obligations_monthly', 'requested_emi', 'fields'])); await done('Your rules are run.'); }
      else if (kind === 'offer') { await run('offer', pick(['borrower', 'lender', 'product_name', 'amount', 'rate', 'months', 'fee_pct', 'fee_fixed', 'fee_tax_pct', 'insurance', 'cooling_off_days', 'grievance'])); await done('The key facts are drafted.'); }
      else if (kind === 'model') { await run('model', pick(['name', 'cashflows', 'discount_pct', 'terminal_growth_pct', 'net_debt', 'shares'])); await done('Worked out.'); }
      else if (kind === 'limits') { await run('settings', all(['tolerance_pct', 'max_single_pct', 'max_group_pct', 'margin_used', 'margin_available', 'margin_alert_pct'])); await changed('Saved.'); }
      else if (kind === 'orders') { await run('settings', {...all(['max_pct_of_portfolio', 'max_price_deviation_pct']), rates: all(['brokerage_pct', 'brokerage_cap', 'other_pct'])}); await changed('Saved.'); }
      else if (kind === 'watchset') { await run('settings', all(['window_minutes', 'max_count', 'max_amount', 'npa_days', 'as_of'])); await changed('Saved.'); }
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
    const box = $('#rkFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/riskdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'rk' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


