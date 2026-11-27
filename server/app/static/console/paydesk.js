/* PAYMENTS DESK - the Payments employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE PAYMENTS
   DESK"). A thin top bar, then the Payments chat (its own conversation, kind 'payments') beside the desk's pages: Today, Disputes (+ one
   case), Payouts & fees, Recurring & sellers, Payment firm, Settings. The pages call /api/payments/do/<part>, which runs the F8 engine on
   the business she picked with the files she uploaded and the deposits in her imported bank statements. Hoola never submits a dispute
   response, charges a card or pays anyone. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', payments: '<path d="M4 7h12l-3-3M20 17H8l3 3"/><circle cx="19" cy="7" r="1.5"/><circle cx="5" cy="17" r="1.5"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['disputes', 'Disputes'], ['reconcile', 'Payouts & fees'], ['recurring', 'Recurring & sellers'],
    ['firm', 'Payment firm'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Which payout is missing?', 'How much did fees cost me?'],
    disputes: ['What does this reason code need?', 'Write my response letter', 'Is my compelling evidence enough?'],
    reconcile: ['Why is this payout short?', 'Which orders are missing?', 'Am I overcharged?'],
    recurring: ['Write the reminder for a failed payment', 'What do I owe each seller?', 'When do I retry?'],
    firm: ['Who are the beneficial owners?', 'Check my payment file', 'Any safeguarding shortfall?'],
    settings: ['What should my dispute limit be?', 'Where do I find my contract rate?', 'How long is my response window?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    rc: null, fa: null, dn: null, po: null, dp: null, dpFor: '', out: {}, df: 'open'};
  try { ST.side = localStorage.getItem('hoola.payments.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.payments.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const cur = () => (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const can = () => !!(ST.d && ST.d.can_write);
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/payments/do/' + part, {workspace: W().id, ...(a || {})});
  const NET = {visa: 'Visa', mastercard: 'Mastercard', amex: 'Amex'};
  const SSAY = {open: ['warn', 'Open'], responded: ['', 'Responded'], won: ['ok', 'Won'], lost: ['bad', 'Lost'], accepted: ['', 'Accepted']};
  const stTag = s => `<span class="cs-tag ${(SSAY[s] || [''])[0]}">${esc((SSAY[s] || ['', s])[1])}</span>`;
  const left = d => d.days_left === null || d.days_left === undefined ? '<span class="mut">no date</span>'
    : d.days_left < 0 ? '<span class="cs-tag bad">Date passed</span>' : `<span class="py-clock${d.days_left <= 3 ? ' bad' : ''}"><b>${esc(d.days_left)}</b> day${d.days_left === 1 ? '' : 's'} left</span>`;

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/payments/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.payments, '')}</div>
        <h1 class="sd-h">Your Payments employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="pyHire">Hire Payments</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#pyHire').onclick = async () => { try { await api('POST', '/api/employees/payments_desk/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.payments, '')}</div>
          <div style="min-width:0"><div class="sd-name">Payments</div><div class="sd-site" id="pySite"></div></div>
          <span id="pyState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="pyBiz" aria-label="Business" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Payments chat">
          <div class="sd-chathead"><div class="t"><b>Payments chat</b><span>Ask about a chargeback or a payout - or drop a settlement file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="pyFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="pyPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Payments desk" id="sdTabs"></nav>
          <div id="pyPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the payments. It submits, charges and pays nothing.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your payments…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#pyPick').click()});
    $('#pyPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.payments.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.payments.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/payments/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#pyBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/payments/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#pyPage').addEventListener('click', onPageClick);
    $('#pyPage').addEventListener('submit', onSubmit);
    $('#pyPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { ST.keepT = null; readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function clearCache() { ST.rc = null; ST.fa = null; ST.dn = null; ST.po = null; ST.dp = null; ST.dpFor = ''; }
  function stateLine() {
    const d = ST.d, el = $('#pyState'); if (!el) return;
    const w = W(), k = K(), open = (k.disputes || []).filter(x => x.status === 'open').length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your business'] : open ? ['warn', `${open} open dispute${open > 1 ? 's' : ''}`]
      : ((k.reconcile || {}).payouts_without_deposit || []).length ? ['warn', 'A payout is missing'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#pySite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + (d.roles[d.role] || d.role) : ''}` : 'No business yet';
    const sel = $('#pyBiz');
    sel.innerHTML = (d.businesses || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.businesses || []).length < 2;
  }
  function paintTabs() {
    const k = K();
    const n = {disputes: (k.disputes || []).filter(x => x.status === 'open').length || '', reconcile: ((k.reconcile || {}).payouts_without_deposit || []).length || '',
      recurring: (k.failed_chasing || {}).count || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/payments/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  // what she is still typing in other boxes survives a save that redraws the page; a form just sent starts clean
  function keepTyping(box) {
    const out = [], act = document.activeElement, now = Date.now();
    box.querySelectorAll('form[data-form]').forEach(f => {
      if (f.dataset.sent && now - Number(f.dataset.sent) < 30000) return;
      f.querySelectorAll('input[name], textarea[name], select[name]').forEach(el => {
        if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'file' || el.type === 'hidden') return;
        const typed = el.tagName === 'SELECT' ? [...el.options].some(o => o.selected !== o.defaultSelected) : el.value !== el.defaultValue;
        if (typed) out.push({f: f.dataset.form, n: el.name, v: el.value, focus: el === act, s: el.selectionStart, e: el.selectionEnd});
      });
    });
    return out;
  }
  function putTyping(box, kept) {   // returns what could not go back yet (the page is still loading)
    const later = [];
    kept.forEach(k => {
      const el = box.querySelector(`form[data-form="${k.f}"] [name="${k.n}"]`); if (!el) { later.push(k); return; }
      el.value = k.v;
      if (k.focus) { el.focus(); try { if (k.s != null) el.setSelectionRange(k.s, k.e); } catch (_) {} }
    });
    return later.length ? later : null;
  }
  function showPage(keep) {
    const box = $('#pyPage'); if (!box) return;
    if (!W()) { box.innerHTML = noBiz(); starters(); return; }
    const fn = {today: pToday, disputes: pDisputes, reconcile: pReconcile, recurring: pRecurring, firm: pFirm, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    if (typeof html === 'string') { const kept = keepTyping(box).concat(ST.keepT || []); box.innerHTML = html; ST.keepT = putTyping(box, kept); }
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function noBiz() {
    return `<div><h1 class="sd-h">Set up your business first</h1><p class="lead">The Payments desk works on a business in Books & Accounts (name, country, currency). Make one there, then come back.</p></div>
      <div><a class="btn" href="/console/books">Open Books & Accounts</a></div>`;
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  async function lazy(key, part, a) {
    if (ST[key] !== null && ST[key] !== undefined) return ST[key];
    ST[key] = false;
    try { ST[key] = await run(part, a); } catch (e) { ST[key] = {error: e.message}; }
    showPage(true);
    return ST[key];
  }
  function uploader(kind, title, hint, gw) {
    if (!can()) return '';
    return `<form class="py-drop" data-form="upload" data-kind="${esc(kind)}"><div class="t"><b>${esc(title)}</b><span class="mut">${esc(hint)}</span></div>
      ${gw ? `<input class="in sm2" name="gateway" placeholder="Gateway (stripe, razorpay ...)" required maxlength="40" list="pyGws"><datalist id="pyGws">${Object.keys(K().gateways || {}).map(g => `<option value="${esc(g)}">`).join('')}</datalist>` : ''}
      <label class="btn soft sm">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" data-upfile="1" hidden></label></form>`;
  }

  /* the dispute rate by month against her limit */
  function rateChart(pv) {
    const ms = (pv && pv.months) || []; if (!ms.length) return '';
    const thr = (K().thresholds || {}).all;
    const vals = ms.map(m => m.dispute_pct || 0), hi = Math.max(thr || 0, ...vals, 0.1) * 1.2;
    const Wd = 760, Hd = 170, L = 44, R = 10, Tp = 10, Bt = 24, iw = Wd - L - R, ih = Hd - Tp - Bt, step = iw / ms.length, bw = Math.min(34, step * 0.5);
    const y = v => Tp + ih - (v / hi) * ih;
    let g = '';
    for (let i = 0; i <= 2; i++) { const v = hi * i / 2; g += `<line class="ax" x1="${L}" x2="${Wd - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v.toFixed(1)}%</text>`; }
    ms.forEach((m, i) => { const x = L + step * (i + 0.5), v = m.dispute_pct || 0, over = thr !== undefined && thr !== null && v >= thr;
      g += `<rect class="${over ? 'bover' : 'brate'}" x="${(x - bw / 2).toFixed(1)}" y="${y(v).toFixed(1)}" width="${bw.toFixed(1)}" height="${(Tp + ih - y(v)).toFixed(1)}" rx="3"><title>${esc(m.month)}: ${esc(m.disputes)} disputes on ${esc(m.sales)} sales (${esc(v)}%)</title></rect>`
        + `<text class="tx" x="${x.toFixed(1)}" y="${Hd - 6}" text-anchor="middle">${esc(new Date(m.month + '-01T00:00').toLocaleDateString(undefined, {month: 'short', year: '2-digit'}))}</text>`; });
    if (thr !== undefined && thr !== null) g += `<line class="min" x1="${L}" x2="${Wd - R}" y1="${y(thr).toFixed(1)}" y2="${y(thr).toFixed(1)}"/><text class="minl" x="${L + 6}" y="${(y(thr) - 5).toFixed(1)}">Your limit ${esc(thr)}%</text>`;
    return `<div class="cs-chart py-chart"><svg viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Disputes as a share of sales">${g}</svg></div>`;
  }

  function pToday() {
    const k = K(), ds = k.disputes || [], open = ds.filter(d => d.status === 'open');
    const stake = open.reduce((a, d) => a + d.amount, 0), rc = k.reconcile || {}, fe = k.fees || {}, fc = k.failed_chasing || {};
    const won = ds.filter(d => d.status === 'won').length, lost = ds.filter(d => d.status === 'lost').length;
    const soon = open.slice().sort((a, b) => (a.days_left ?? 999) - (b.days_left ?? 999)).slice(0, 5);
    const lead = open.length ? `${open.length} open dispute${open.length > 1 ? 's' : ''}, ${money(stake, cur(), 2)} at stake.`
      : (rc.payouts_without_deposit || []).length ? 'A gateway payout has not reached your bank.' : ds.length || k.counts.settlements ? 'Nothing is waiting on you.'
      : 'Add a chargeback, or upload a gateway settlement file, to start.';
    const gws = Object.entries(rc.by_gateway || {});
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k${open.length ? ' low bad' : ''}"><div class="l">Disputes open</div><div class="v">${esc(money(stake))}</div><div class="s">${esc(open.length)} open${won + lost ? ` · won ${won} · lost ${lost}` : ''}</div></div>
        <div class="k${(rc.payouts_without_deposit || []).length ? ' low bad' : ''}"><div class="l">Payouts not in the bank</div><div class="v">${esc((rc.payouts_without_deposit || []).length)}</div><div class="s">${rc.empty ? 'no settlement files yet' : rc.balanced ? 'everything matches' : `${esc(rc.orders_off || 0)} order(s) do not match`}</div></div>
        <div class="k${fe.overcharged_total ? ' low bad' : ''}"><div class="l">Fees above your contract</div><div class="v">${esc(money(fe.overcharged_total || 0, cur(), 2))}</div><div class="s">${fe.empty ? 'give your contract rates' : `on ${esc(fe.checked || 0)} sales checked`}</div></div>
        <div class="k"><div class="l">Failed payments</div><div class="v">${esc(fc.count || 0)}</div><div class="s">${esc(money(fc.amount || 0, cur(), 2))} to recover</div></div></div>
        ${(k.prevention || {}).months && k.prevention.months.length ? `<div><div class="cr-sub">Disputes as a share of sales, by month</div>${rateChart(k.prevention)}</div>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Respond soonest</h2><div class="r"><button class="btn soft sm" type="button" data-go="disputes">All disputes</button></div></div>
          <div style="margin-top:6px">${soon.map(d => `<div class="cs-row" data-go="disputes/${esc(d.n)}" style="cursor:pointer"><span class="py-net ${esc(d.network)}">${esc(NET[d.network])}</span><span style="flex:1;min-width:0"><b>${esc(d.reason_code)}</b> ${esc(d.reason || '')}<div class="mut" style="font-size:12.5px">${esc(m2(d.amount, d.currency || cur()))}${d.customer ? ' · ' + esc(d.customer) : ''}</div></span>${left(d)}</div>`).join('') || empty('No open dispute.')}</div></section>
      </div>
      ${gws.length ? `<section class="card"><h2 class="md-h2">By gateway</h2><div class="py-gws">${gws.map(([g, v]) => `<div class="py-gw"><div class="t"><b>${esc(cap(g))}</b><span class="cs-tag">${v.effective_fee_pct === null ? '—' : esc(v.effective_fee_pct) + '% fees'}</span></div>
        <div class="py-flow"><span><em>Sales</em>${esc(m2(v.sales))}</span><span class="${v.refunds ? 'neg' : ''}"><em>Refunds</em>${v.refunds ? '−' : ''}${esc(m2(v.refunds))}</span><span class="${v.chargebacks ? 'neg' : ''}"><em>Chargebacks</em>${v.chargebacks ? '−' : ''}${esc(m2(v.chargebacks))}</span><span class="${v.fees ? 'neg' : ''}"><em>Fees</em>${v.fees ? '−' : ''}${esc(m2(v.fees))}</span><span class="net"><em>Paid out</em>${esc(m2(v.net))}</span></div></div>`).join('')}</div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- disputes */
  function pDisputes() {
    if (ST.arg) return disputePage(ST.arg);
    const ds = (K().disputes || []).slice().reverse(), show = ds.filter(d => ST.df === 'all' || (ST.df === 'open' ? d.status === 'open' : d.status !== 'open'));
    const cnt = s => ds.filter(d => s === 'all' || (s === 'open' ? d.status === 'open' : d.status !== 'open')).length;
    return `<div><h1 class="sd-h">Disputes</h1><p class="lead">Each chargeback's reason code, the evidence that answers it, and your response date. You submit the response through your processor - Hoola submits nothing.</p></div>
      ${can() ? `<section class="card"><h2 class="md-h2">A new chargeback</h2><form data-form="dispute" class="cr-grid" style="margin-top:0">
        <select class="in" name="network" aria-label="Network">${Object.entries(NET).map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select>
        <input class="in" name="reason_code" placeholder="Reason code (13.1, 4855, C08 ...)" required maxlength="10" aria-label="Reason code">
        <input class="in" name="amount" type="number" step="0.01" min="0" placeholder="Amount" required aria-label="Amount">
        <input class="in" name="gateway" placeholder="Gateway" maxlength="40" aria-label="Gateway" list="pyGws2"><datalist id="pyGws2">${Object.keys(K().gateways || {}).map(g => `<option value="${esc(g)}">`).join('')}</datalist>
        <input class="in" name="transaction_id" placeholder="Transaction id" maxlength="60" aria-label="Transaction id">
        <input class="in" name="customer" placeholder="Customer" maxlength="80" aria-label="Customer">
        <label class="py-lab">Received<input class="in" type="date" name="received" value="${esc(new Date().toISOString().slice(0, 10))}"></label>
        <input class="in" name="window_days" type="number" min="1" placeholder="Days to respond (your processor's)" aria-label="Days to respond">
        <button class="btn" type="submit">Add</button></form></section>` : ''}
      <div class="cr-filter"><div class="cs-seg" role="group">${[['open', 'Open'], ['done', 'Closed'], ['all', 'All']].map(([k, l]) => `<button type="button" data-df="${k}" aria-pressed="${ST.df === k}">${esc(l)} <span class="mut">${esc(cnt(k))}</span></button>`).join('')}</div></div>
      <div class="py-cases">${show.map(d => `<button class="py-case" type="button" data-go="disputes/${esc(d.n)}"><div class="t"><span class="py-net ${esc(d.network)}">${esc(NET[d.network])}</span><b>${esc(d.reason_code)}</b>${stTag(d.status)}</div>
        <div class="v">${esc(m2(d.amount, d.currency || cur()))}</div><div class="mut" style="font-size:13px">${esc(d.reason || '')}</div>
        <div class="f"><span>${d.missing ? `${esc(d.missing)} evidence missing` : 'Evidence complete'}</span>${d.status === 'open' ? left(d) : d.reference ? `<span class="mut">ref ${esc(d.reference)}</span>` : ''}</div></button>`).join('') || `<section class="card">${empty('No dispute here.')}</section>`}</div>`;
  }
  function disputePage(n) {
    if (ST.dpFor !== String(n)) { ST.dp = null; ST.dpFor = String(n); }
    if (ST.dp === null) { lazy('dp', 'dispute', {n: Number(n)}); return loading(); }
    if (ST.dp === false) return loading();
    const d = ST.dp;
    if (d.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(d.error)}</p></section>`;
    const r = d.read || {}, keys = K().evidence_keys || {}, have = d.evidence || {}, need = r.evidence_needed || [];
    const others = Object.keys(keys).filter(k => !need.includes(k));
    const ev = list => list.map(k => `<label class="py-ev${have[k] || (k === 'prior_transactions' && (r.evidence_you_have || []).includes(k)) ? ' on' : ''}"><input type="checkbox" data-ev="${esc(k)}"${have[k] ? ' checked' : ''}${can() ? '' : ' disabled'}><span><b>${esc(cap(keys[k]))}</b>${need.includes(k) ? '<em>answers this code</em>' : ''}</span></label>`).join('');
    const ok = /answers|refunded/.test(r.verdict || '');
    const ce = r.compelling_evidence;
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="disputes">← Disputes</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(NET[d.network])} ${esc(d.reason_code)} · ${esc(r.reason || '')}</h1><p class="lead" style="margin-top:4px">${esc(m2(d.amount, d.currency || cur()))}${d.transaction_id ? ' · ' + esc(d.transaction_id) : ''}${d.customer ? ' · ' + esc(d.customer) : ''}${d.gateway ? ' · ' + esc(cap(d.gateway)) : ''} · ${stTag(d.status)}</p></div>
        <div class="r"><button class="btn soft sm" type="button" data-dl="letter">Response letter PDF</button><button class="btn soft sm" type="button" data-ask="${esc('Dispute #' + d.n + ' ' + d.network + ' ' + d.reason_code)}">Ask about it</button></div></div>
      <section class="cs-hero"><div class="top">
        <div class="k${d.days_left !== null && d.days_left <= 3 ? ' low bad' : ''}"><div class="l">Respond by</div><div class="v">${esc(d.respond_by ? dmy(d.respond_by) : '—')}</div><div class="s">${d.respond_by ? (d.days_left < 0 ? 'the date has passed' : `${esc(d.days_left)} days left`) : 'give your processor\'s window below'}</div></div>
        <div class="k${ok ? '' : ' low bad'}"><div class="l">Evidence</div><div class="v">${esc((r.evidence_you_have || []).length)} / ${esc(need.length)}</div><div class="s">${esc(r.verdict || '')}</div></div>
        <div class="k"><div class="l">Kind of dispute</div><div class="v sm">${esc(cap(r.kind || ''))}</div><div class="s">${esc(r.codes_from || '')}</div></div></div>
        <div class="py-meter"><span style="width:${need.length ? (100 * (r.evidence_you_have || []).length / need.length).toFixed(0) : 0}%" class="${ok ? 'ok' : 'warn'}"></span></div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">The evidence for this code</h2><div class="py-evs">${ev(need)}</div>
          ${others.length ? `<details class="py-more"><summary>Other evidence you have</summary><div class="py-evs">${ev(others)}</div></details>` : ''}
          ${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Tick what you can send your processor.</span><button class="btn" type="button" data-saveev="1">Save</button></div>' : ''}</section>
        <section class="card"><h2 class="md-h2">The response letter</h2><pre class="py-letter">${esc(r.letter || '')}</pre><p class="cs-note">${esc(r.says || '')}</p></section>
      </div>
      ${d.reason_code === '10.4' ? `<section class="card"><h2 class="md-h2">Compelling evidence - her earlier payments</h2>
        ${ce ? `<div class="cr-verdict ${ce.qualifies ? 'ok' : 'bad'}"><b>${ce.qualifies ? 'Qualifies' : 'Does not qualify yet'}</b><span>${esc(ce.rule)}</span></div>${(ce.not_counted || []).map(x => `<p class="cs-note">${esc(x)}</p>`).join('')}` : ''}
        ${can() ? `<form data-form="prior"><div class="cr-sub" style="margin-top:12px">The disputed payment</div><div class="cr-grid">${['ip', 'device', 'shipping', 'account'].map(x => `<input class="in" name="d_${x}" placeholder="${x === 'ip' ? 'IP address' : cap(x)}" value="${esc((d.disputed_tx || {})[x] || '')}" aria-label="${x}">`).join('')}</div>
          <div class="cr-sub" style="margin-top:12px">Earlier undisputed payments (one per line: date, IP, device, shipping, account)</div>
          <textarea class="in" name="prior" rows="3" style="width:100%" placeholder="2026-05-01, 1.2.3.4, iphone-1, 1 High St, mia@x.com">${esc((d.prior || []).map(p => [p.date, p.ip, p.device, p.shipping, p.account].join(', ')).join('\n'))}</textarea>
          <div class="md-acts"><span></span><button class="btn soft sm" type="submit">Check them</button></div></form>` : ''}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What happened</h2>
          ${(d.history || []).map(h => `<div class="cs-row">${stTag(h.status)}<span style="flex:1" class="mut">${esc(h.on)}${h.reference ? ' · ref ' + esc(h.reference) : ''}</span><span class="mut">${esc(S(h.by).replace(/\s*<[^>]*>$/, ''))}</span></div>`).join('') || empty('Nothing recorded yet.')}
          ${can() ? `<form data-form="status" class="cs-form"><select class="in sm2" name="status" aria-label="Status">${['responded', 'won', 'lost', 'accepted', 'open'].map(s => `<option value="${s}">${esc(SSAY[s][1])}</option>`).join('')}</select><input class="in" name="reference" placeholder="Your processor's reference" maxlength="80" aria-label="Reference"><button class="btn soft sm" type="submit">Record</button></form><p class="cs-note">Accepted = you let the chargeback stand. Hoola never submits for you.</p>` : ''}</section>
        <section class="card"><h2 class="md-h2">Notes and window</h2>${can() ? `<form data-form="dnotes"><textarea class="in" name="notes" rows="3" style="width:100%" placeholder="Tracking numbers, what the customer said ...">${esc(d.notes || '')}</textarea>
          <div class="cs-form"><label class="py-lab">Days to respond<input class="in sm2" name="window_days" type="number" min="1" value="${esc(d.window_days ?? '')}"></label><button class="btn soft sm" type="submit">Save</button><button class="btn soft sm" type="button" data-undispute="1">Remove</button></div></form>` : `<p>${esc(d.notes || '')}</p>`}</section>
      </div>`;
  }

  /* ---------------------------------------------------------------- payouts & fees */
  function pReconcile() {
    if (ST.rc === null) { lazy('rc', 'reconcile', {}); }
    if (ST.fa === null) { lazy('fa', 'fee_audit', {}); }
    const r = ST.rc, f = ST.fa, k = K();
    const files = (k.files || []).filter(x => ['settlements', 'orders'].includes(x.kind));
    const head = `<div><h1 class="sd-h">Payouts & fees</h1><p class="lead">Your orders against each gateway's settlement lines against the deposits in your bank statements - and every fee against your contract rate.</p></div>
      <div class="md-2">${uploader('settlements', 'A gateway settlement file', 'payout id, payout date, order id, type, amount', true)}${uploader('orders', 'Your orders', 'id, amount, date (from your shop or invoices)', false)}</div>
      ${files.length ? `<div class="py-files">${files.slice(0, 6).map(x => `<span class="fm-chip"><b>${esc(x.kind === 'orders' ? 'Orders' : cap(x.gateway))}</b> ${esc(x.rows)} rows <span class="mut">${esc(x.on)}</span></span>`).join('')}</div>` : ''}`;
    if (!r || r === false) return head + loading();
    if (r.error) return head + `<section class="card"><p class="cs-neg" style="margin:0">${esc(r.error)}</p></section>`;
    if (r.empty) return head + `<section class="card">${empty(r.says)}</section>`;
    const o = r.orders || {};
    const pays = (r.payouts || []).map(p => `<tr class="${p.deposit ? '' : 'cr-late'}"><td><b>${esc(p.payout)}</b><div class="mut" style="font-size:12.5px">${esc(cap(p.gateway))}</div></td><td class="nw">${esc(dmy(p.date))}</td><td class="num">${esc(m2(p.net))}</td>
      <td>${p.deposit ? `<span class="cs-tag ok">In the bank</span> <span class="mut" style="font-size:12.5px">${esc(dmy(p.deposit_date))}${p.days ? ` · ${esc(p.days)}d later` : ''}</span>` : '<span class="cs-tag bad">Not found</span>'}</td></tr>`).join('');
    const fl = f && !f.error && !f.empty ? (f.overcharged_lines || []).map(x => `<tr><td>${esc(x.id)}</td><td>${esc(cap(x.gateway))}</td><td class="num">${esc(m2(x.amount))}</td><td class="num">${esc(m2(x.contract))}</td><td class="num cs-neg">${esc(m2(x.charged))}</td><td class="num cs-neg">+${esc(m2(x.over))}</td></tr>`).join('') : '';
    return head + `
      <section class="cs-hero"><div class="top">
        <div class="k"><div class="l">Status</div><div class="v sm">${r.balanced ? 'Everything matches' : 'Not balanced'}</div><div class="s">${esc(r.deposits_read)} bank deposits read</div></div>
        <div class="k${(r.payouts_without_deposit || []).length ? ' low bad' : ''}"><div class="l">Payouts not in the bank</div><div class="v">${esc((r.payouts_without_deposit || []).length)}</div><div class="s">of ${esc((r.payouts || []).length)} payouts</div></div>
        <div class="k${(o.missing_at_gateway || []).length + (o.amount_differs || []).length ? ' low bad' : ''}"><div class="l">Orders off</div><div class="v">${esc((o.missing_at_gateway || []).length + (o.amount_differs || []).length + (o.gateway_sale_without_order || []).length)}</div><div class="s">${r.no_orders ? 'upload your orders to check them' : `of ${esc(r.orders_read)} orders`}</div></div>
        <div class="k${f && f.overcharged_total ? ' low bad' : ''}"><div class="l">Fees above contract</div><div class="v">${esc(m2(f && f.overcharged_total || 0))}</div><div class="s">${f && f.empty ? 'give your contract rates' : `${esc((f && f.checked) || 0)} sales checked`}</div></div></div></section>
      <section class="card tight"><div class="cs-head" style="padding:16px 18px 0"><h2 class="md-h2" style="margin:0">Payouts</h2></div><div style="overflow-x:auto;margin-top:8px"><table class="tb"><thead><tr><th>Payout</th><th>Date</th><th class="num">Net</th><th>Your bank</th></tr></thead><tbody>${pays}</tbody></table></div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Orders that do not match</h2>
          ${(o.missing_at_gateway || []).map(x => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">Order <b>${esc(x.order)}</b> - not in any settlement</span><span class="num">${esc(m2(x.amount))}</span></div>`).join('')}
          ${(o.amount_differs || []).map(x => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">Order <b>${esc(x.order)}</b> - ${esc(m2(x.order_amount))} in your shop, ${esc(m2(x.gateway_amount))} at the gateway</span></div>`).join('')}
          ${(o.gateway_sale_without_order || []).map(x => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">The gateway has a sale <b>${esc(x)}</b> with no order</span></div>`).join('')}
          ${!(o.missing_at_gateway || []).length && !(o.amount_differs || []).length && !(o.gateway_sale_without_order || []).length ? empty(r.no_orders ? 'Upload your orders to check them.' : 'Every order matches.') : ''}</section>
        <section class="card"><h2 class="md-h2">Deposits with no payout</h2>${(r.unmatched_deposits || []).slice(0, 8).map(x => `<div class="cs-row"><span class="mut nw" style="width:92px">${esc(dmy(x.date))}</span><span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(x.narration)}</span><span class="num">${esc(m2(x.amount))}</span></div>`).join('') || empty('None.')}
          <p class="cs-note">Money in from other places shows here too - only a payout's own deposit matters.</p></section>
      </div>
      <section class="card tight"><div class="cs-head" style="padding:16px 18px 0"><h2 class="md-h2" style="margin:0">Fees above your contract</h2>${f && f.by_gateway ? `<div class="r">${Object.entries(f.by_gateway).map(([g, v]) => `<span class="cs-tag bad">${esc(cap(g))} +${esc(m2(v))}</span>`).join(' ')}</div>` : ''}</div>
        ${f && f.empty ? `<div style="padding:12px 18px 18px">${empty(f.says)}</div>` : fl ? `<div style="overflow-x:auto;margin-top:8px"><table class="tb"><thead><tr><th>Order</th><th>Gateway</th><th class="num">Sale</th><th class="num">Contract fee</th><th class="num">Charged</th><th class="num">Over</th></tr></thead><tbody>${fl}</tbody></table></div><p class="cs-note" style="padding:0 18px 16px">${esc(f.says)}</p>` : `<div style="padding:12px 18px 18px">${empty('Every fee is within your contract rate.')}</div>`}</section>`;
  }

  /* ---------------------------------------------------------------- recurring & sellers */
  function pRecurring() {
    if (ST.dn === null) lazy('dn', 'dunning', {});
    if (ST.po === null) lazy('po', 'payouts', {});
    const dn = ST.dn || {}, po = ST.po || {}, k = K();
    const fails = (dn.failed || []).slice().reverse();
    const plan = {}; (dn.customers || []).forEach(c => { plan[c.n] = c; });
    return `<div><h1 class="sd-h">Recurring & sellers</h1><p class="lead">Failed recurring payments and the retry plan, and what each seller on your marketplace is owed. Hoola charges and pays nothing.</p></div>
      <div class="md-2">${uploader('failed', 'Failed payments', 'customer, amount, plan, date, reason', false)}${uploader('market', 'Marketplace sales', 'seller, amount, type (sale / refund), fee', false)}</div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Failed payments</h2><div class="r"><span class="mut" style="font-size:13px">Retry on day ${esc((k.retry_days || []).join(', '))} - change in Settings</span></div></div>
        <div style="margin-top:8px">${fails.map(f => { const p = plan[f.n]; return `<div class="py-fail"><div class="h"><b>${esc(f.customer)}</b><span class="num">${esc(m2(f.amount))}</span><span class="mut">${esc(f.plan || '')} · failed ${esc(dmy(f.date))}${f.reason ? ' · ' + esc(f.reason) : ''}</span>
          ${f.status === 'chasing' ? '<span class="cs-tag warn">Chasing</span>' : `<span class="cs-tag ${f.status === 'recovered' ? 'ok' : ''}">${esc(cap(f.status))}</span>`}
          ${can() && f.status === 'chasing' ? `<span class="r"><button class="btn soft sm" type="button" data-fstat="recovered" data-n="${esc(f.n)}">Recovered</button><button class="btn soft sm" type="button" data-fstat="cancelled" data-n="${esc(f.n)}">Cancelled</button></span>` : ''}</div>
          ${p ? `<div class="py-steps">${p.plan.map((s, i) => `<div><span class="dot">${i + 1}</span><b>${esc(dmy(s.retry_on))}</b><span class="mut">${esc(s.message)}</span></div>`).join('')}<div><span class="dot">✕</span><b>${esc(dmy(p.stop_after))}</b><span class="mut">Stop and cancel if still unpaid</span></div></div>` : ''}</div>`; }).join('') || empty('No failed payment.')}</div>
        ${can() ? `<form data-form="failed" class="cr-grid"><input class="in" name="customer" placeholder="Customer" required maxlength="80" aria-label="Customer"><input class="in" name="amount" type="number" step="0.01" min="0" placeholder="Amount" required aria-label="Amount"><input class="in" name="plan" placeholder="Plan" maxlength="60" aria-label="Plan"><input class="in" name="date" type="date" required aria-label="Date"><input class="in" name="reason" placeholder="Reason" maxlength="80" aria-label="Reason"><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
      <section class="card tight"><div class="cs-head" style="padding:16px 18px 0"><h2 class="md-h2" style="margin:0">What each seller is owed</h2><div class="r">${(po.sellers || []).length ? '<button class="btn soft sm" type="button" data-dl="payouts">Download CSV</button>' : ''}<span class="mut" style="font-size:13px">Your commission ${k.commission_pct === null || k.commission_pct === undefined ? 'not set' : esc(k.commission_pct) + '%'}</span></div></div>
        ${po.error ? `<div style="padding:12px 18px 18px"><p class="cs-neg" style="margin:0">${esc(po.error)}</p></div>` : (po.sellers || []).length ? `<div style="overflow-x:auto;margin-top:8px"><table class="tb"><thead><tr><th>Seller</th><th class="num">Sales</th><th class="num">Refunds</th><th class="num">Commission</th><th class="num">Fees</th><th class="num">Owed</th></tr></thead><tbody>
          ${po.sellers.map(s => `<tr class="${s.carry_forward ? 'cr-late' : ''}"><td><b>${esc(s.seller)}</b>${s.carry_forward ? ' <span class="cs-tag warn">Carried forward</span>' : ''}</td><td class="num">${esc(m2(s.sales))}</td><td class="num">${esc(m2(s.refunds))}</td><td class="num">${esc(m2(s.commission))}</td><td class="num">${esc(m2(s.fees))}</td><td class="num"><b>${esc(m2(s.owed))}</b></td></tr>`).join('')}</tbody></table></div><p class="cs-note" style="padding:0 18px 16px">${esc(po.says)}</p>`
          : `<div style="padding:12px 18px 18px">${empty('Upload your marketplace sales to see each seller.')}</div>`}</section>`;
  }

  /* ---------------------------------------------------------------- payment firm tools */
  function pFirm() {
    const o = ST.out;
    const kb = o.kyb, iso = o.iso, sg = o.sg;
    return `<div><h1 class="sd-h">Payment firm</h1><p class="lead">For a payment firm: who really owns a business you onboard, whether a payment file is well formed, and whether customer money is safeguarded day by day. The decisions are your compliance officer's.</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Beneficial owners (KYB)</h2><form data-form="kyb">
          <div class="cr-grid" style="margin-top:0"><input class="in" name="business" placeholder="The business onboarded" required aria-label="Business"><input class="in" name="threshold_pct" type="number" min="0" max="100" placeholder="Your threshold %" required aria-label="Threshold"><input class="in" name="documents" placeholder="Documents you have (comma separated)" aria-label="Documents"></div>
          <textarea class="in" name="ownership" rows="4" style="width:100%;margin-top:8px" placeholder="One line each: owner, owned, percent, person (yes / no)&#10;Holdco, Shop Ltd, 60, no&#10;Ann, Holdco, 50, yes"></textarea>
          <div class="md-acts"><span class="mut" style="font-size:13px">Shares are multiplied through the chain.</span><button class="btn soft sm" type="submit">Work them out</button></div></form>
          ${kb ? (kb.error ? `<p class="cs-note cs-neg">${esc(kb.error)}</p>` : `<div class="fm-out">${(kb.all_end_owners || []).map(b => `<div class="cs-row"><span class="cr-st ${b.pct >= kb.threshold_pct ? 'received' : ''}">${b.person ? '●' : '?'}</span><span style="flex:1"><b>${esc(b.owner)}</b>${b.person ? '' : ' <span class="cs-tag warn">trace further</span>'}</span><span class="py-share"><i style="width:${Math.min(100, b.pct)}%"></i></span><b>${esc(b.pct)}%</b></div>`).join('')}
            ${(kb.documents_missing || []).length ? `<p class="cs-note">Documents missing: ${esc(kb.documents_missing.join(', '))}</p>` : ''}<p class="cs-note">${esc(kb.says)}</p></div>`) : ''}</section>
        <section class="card"><h2 class="md-h2">ISO 20022 payment file</h2><form data-form="iso"><textarea class="in" name="xml" rows="7" style="width:100%;font-family:var(--mono,monospace);font-size:12.5px" placeholder="Paste a pain.001 or pacs.008 message"></textarea>
          <div class="md-acts"><span class="mut" style="font-size:13px">The parts a bank needs, IBAN check digits, BIC shape, the count and the sum.</span><button class="btn soft sm" type="submit">Check it</button></div></form>
          ${iso ? (iso.error ? `<p class="cs-note cs-neg">${esc(iso.error)}</p>` : `<div class="cr-verdict ${iso.ok ? 'ok' : 'bad'}"><b>${iso.ok ? 'Looks right' : `${esc((iso.problems || []).length)} problem(s)`}</b><span>${esc(iso.kind || '')}${iso.transactions !== undefined ? ` · ${esc(iso.transactions)} payments · total ${esc(iso.total)}` : ''}</span></div>${(iso.problems || []).map(p => `<div class="cs-row"><span class="cs-dot bad"></span><span>${esc(p)}</span></div>`).join('')}${iso.says ? `<p class="cs-note">${esc(iso.says)}</p>` : ''}`) : ''}</section>
      </div>
      <section class="card"><h2 class="md-h2">Safeguarding, day by day</h2><form data-form="sg"><textarea class="in" name="days" rows="4" style="width:100%" placeholder="One line each: date, owed to customers, held in safeguarding accounts&#10;2026-11-01, 120000, 118500"></textarea>
        <div class="md-acts"><span></span><button class="btn soft sm" type="submit">Check the days</button></div></form>
        ${sg ? (sg.error ? `<p class="cs-note cs-neg">${esc(sg.error)}</p>` : `<div class="py-sg">${(sg.days || []).map(x => `<div class="${x.shortfall ? 'bad' : 'ok'}" title="${esc(x.date)}: owed ${esc(m2(x.owed))}, held ${esc(m2(x.safeguarded))}"><b>${esc(dmy(x.date))}</b><span>${x.shortfall ? 'Short ' : 'Covered '}${esc(m2(Math.abs(x.difference)))}</span></div>`).join('')}</div><p class="cs-note">${esc(sg.says)}</p>`) : ''}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), gws = Object.entries(k.gateways || {}), ro = can() ? '' : ' disabled';
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your own figures: the rates in your contracts, your processor's windows, your limits.</p></div>
      <section class="card"><h2 class="md-h2">Gateways and your contract rates</h2>
        ${gws.length ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Gateway</th><th class="num">Percent</th><th class="num">Fixed</th><th class="num">Days to respond to a dispute</th><th>From</th><th></th></tr></thead><tbody>${gws.map(([g, v]) => `<tr><td><b>${esc(cap(g))}</b></td><td class="num">${v.pct === null || v.pct === undefined ? '<span class="cs-tag warn">not set</span>' : esc(v.pct) + '%'}</td><td class="num">${v.fixed === null || v.fixed === undefined ? '—' : esc(m2(v.fixed))}</td><td class="num">${esc(v.window_days ?? '—')}</td><td class="mut">${esc(v.source || '')}</td><td>${can() ? `<button class="btn soft sm" type="button" data-editgw="${esc(g)}">Change</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No gateway yet - add one, or upload a settlement file.')}
        ${can() ? `<form data-form="gw" class="cr-grid"><input class="in" name="gateway" placeholder="Gateway" required maxlength="40" value="${esc(ST.editgw || '')}" aria-label="Gateway"><input class="in" name="pct" type="number" step="0.001" min="0" placeholder="Percent per sale" value="${esc(ST.editgw ? ((k.gateways || {})[ST.editgw] || {}).pct ?? '' : '')}" aria-label="Percent"><input class="in" name="fixed" type="number" step="0.01" min="0" placeholder="Fixed per sale" value="${esc(ST.editgw ? ((k.gateways || {})[ST.editgw] || {}).fixed ?? '' : '')}" aria-label="Fixed"><input class="in" name="window_days" type="number" min="1" placeholder="Days to respond to disputes" value="${esc(ST.editgw ? ((k.gateways || {})[ST.editgw] || {}).window_days ?? '' : '')}" aria-label="Window"><input class="in wide" name="source" placeholder="Where it is written (your agreement, schedule 2)" maxlength="160" aria-label="Source"><button class="btn" type="submit">Save</button></form>` : ''}</section>
      <form class="card" data-form="limits"><h2 class="md-h2">Your limits and rules</h2><div class="md-form">
        <div class="md-field"><label for="pyL1">Disputes as a share of sales - your limit (%)</label><input class="in" id="pyL1" name="threshold_pct" type="number" step="0.01" min="0" value="${esc((k.thresholds || {}).all ?? '')}" placeholder="Not set"${ro}></div>
        <div class="md-field"><label for="pyL2">Days a payout may take to reach your bank</label><input class="in" id="pyL2" name="window_days" type="number" min="0" value="${esc(k.window_days ?? 5)}"${ro}></div>
        <div class="md-field"><label for="pyL3">Retry failed payments on these days</label><input class="in" id="pyL3" name="retry_days" value="${esc((k.retry_days || []).join(', '))}"${ro}></div>
        <div class="md-field"><label for="pyL4">Your marketplace commission (%)</label><input class="in" id="pyL4" name="commission_pct" type="number" step="0.01" min="0" value="${esc(k.commission_pct ?? '')}" placeholder="Not set"${ro}></div>
      </div>${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">The card networks\' own monitoring limits are not Hoola\'s to set - check this with your processor.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function download(what) {
    try {
      const r = await fetch(`/api/payments/download?workspace=${enc(W().id)}&what=${enc(what)}&n=${enc(ST.arg || 0)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `payments-${what}`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const lines = t => S(t).split('\n').map(x => x.split(',').map(y => y.trim())).filter(x => x.join('').length);
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const df = t.closest('[data-df]'); if (df) { ST.df = df.dataset.df; showPage(true); return; }
    const eg = t.closest('[data-editgw]'); if (eg) { ST.editgw = eg.dataset.editgw; showPage(true); return; }
    try {
      if (t.closest('[data-saveev]')) { const ev = {}; $('#pyPage').querySelectorAll('[data-ev]').forEach(x => { if (x.checked) ev[x.dataset.ev] = true; });
        ST.dp = await run('edit_dispute', {n: Number(ST.arg), evidence: ev}).then(r => r.dispute); await changed('Saved.'); return; }
      if (t.closest('[data-undispute]')) { if (!confirm('Remove this dispute from the desk?')) return; await run('remove_dispute', {n: Number(ST.arg)}); await changed('Removed.'); location.hash = '#/disputes'; return; }
      const fs = t.closest('[data-fstat]'); if (fs) { await run('failed', {n: Number(fs.dataset.n), status: fs.dataset.fstat}); await changed('Updated.'); return; }
    } catch (err) { toast(err.message, true); }
  }
  async function onChange(e) {
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 8e6) { toast('Up to 8 MB.', true); return; }
    const gw = form.querySelector('[name=gateway]');
    if (gw && !gw.value.trim()) { toast('Say which gateway the file is from first.', true); fi.value = ''; gw.focus(); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, gateway: gw ? gw.value.trim() : '', text: await f.text(), name: f.name}); fi.value = ''; await changed(`${r.rows} rows read from ${f.name}.`); }
    catch (err) { toast(err.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return; form.dataset.sent = Date.now();
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = form.querySelector('[type=submit]'), g = n => val(fd, n);
    if (btn) btn.disabled = true;
    try {
      if (kind === 'dispute') { const a = {network: g('network'), reason_code: g('reason_code'), amount: Number(g('amount')), gateway: g('gateway'), transaction_id: g('transaction_id'), customer: g('customer'), received: g('received')};
        if (g('window_days')) a.window_days = Number(g('window_days'));
        const r = await run('add_dispute', a); location.hash = '#/disputes/' + r.dispute.n; await changed('Dispute added.'); }
      else if (kind === 'status') { await run('status', {n: Number(ST.arg), status: g('status'), reference: g('reference')}); await changed('Recorded.'); }
      else if (kind === 'dnotes') { await run('edit_dispute', {n: Number(ST.arg), notes: g('notes'), window_days: g('window_days')}); await changed('Saved.'); }
      else if (kind === 'prior') { const prior = lines(g('prior')).map(x => ({date: x[0], ip: x[1] || '', device: x[2] || '', shipping: x[3] || '', account: x[4] || ''}));
        await run('edit_dispute', {n: Number(ST.arg), prior, disputed: {ip: g('d_ip'), device: g('d_device'), shipping: g('d_shipping'), account: g('d_account')}}); await changed('Checked.'); }
      else if (kind === 'failed') { await run('failed', {customer: g('customer'), amount: Number(g('amount')), plan: g('plan'), date: g('date'), reason: g('reason')}); await changed('Added.'); }
      else if (kind === 'gw') { await run('settings', {gateway: g('gateway'), pct: g('pct'), fixed: g('fixed'), window_days: g('window_days'), source: g('source')}); ST.editgw = ''; await changed('Saved.'); }
      else if (kind === 'limits') { await run('settings', {threshold_pct: g('threshold_pct'), window_days: g('window_days') || 0, retry_days: g('retry_days'), commission_pct: g('commission_pct')}); await changed('Saved.'); }
      else if (kind === 'kyb') { const own = lines(g('ownership')).map(x => ({owner: x[0], owned: x[1], pct: x[2], person: /^y/i.test(x[3] || '')}));
        try { ST.out.kyb = await run('kyb', {business: g('business'), threshold_pct: g('threshold_pct'), documents: g('documents').split(',').map(x => x.trim()).filter(Boolean), ownership: own}); } catch (err) { ST.out.kyb = {error: err.message}; } showPage(true); }
      else if (kind === 'iso') { try { ST.out.iso = await run('iso20022', {xml: g('xml')}); } catch (err) { ST.out.iso = {error: err.message}; } showPage(true); }
      else if (kind === 'sg') { const days = lines(g('days')).map(x => ({date: x[0], owed_to_customers: x[1], safeguarded: x[2]}));
        try { ST.out.sg = await run('safeguarding', {days}); } catch (err) { ST.out.sg = {error: err.message}; } showPage(true); }
    } catch (err) { toast(err.message, true); }
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
    const box = $('#pyFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/payments/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'py' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


