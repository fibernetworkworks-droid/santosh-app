/* MATERIAL STORE DESK - the Construction & Real Estate Material Store Manager's own section, like the finance desks (owner: "Material
   Store Manager ... GENERALIZE FOR WORLD ... A PERFECT WORKFLOW FOR AI STORE MANAGER" -> design canvas -> "GO BUILD ALL 7 VERSIONS").
   A thin top bar, then the Store chat (its own conversation, kind 'store': she sends a delivery paper, asks what runs short, says what
   to issue) beside the desk's pages: Today, Receive, Stock, Issue & returns, Transfers, Indents, Counts, Reconcile, Reports, Settings.
   The pages call /api/stdesk/do/<part>. A named person confirms receipts and slips, decides quality and approves - typed on these
   pages; the chat only drafts. Routes: #/<page>[/<id>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', store: '<path d="M3 9l9-5 9 5v11H3z"/><path d="M8 20v-6h8v6M8 17h8"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>', cam: '<path d="M4 7h4l2-3h4l2 3h4v12H4z"/><circle cx="12" cy="13" r="3.5"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['receive', 'Receive'], ['stock', 'Stock'], ['issue', 'Issue & returns'], ['transfers', 'Transfers'],
    ['indents', 'Indents'], ['counts', 'Counts'], ['reconcile', 'Reconcile'], ['reports', 'Reports'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What is running short?', 'What needs me today?', 'How much is the store worth?'],
    receive: ['Read this delivery note', 'What is on quality hold?', 'Which deliveries are late?'],
    stock: ['Which items are below reorder?', 'Which heats went into column C4?', 'What has not moved for weeks?'],
    issue: ['Issue 40 bags of cement to slab L6', 'What does each subcontractor hold?', 'Return unused steel from L5'],
    transfers: ['Send 2 t of 16 mm to Site B', 'What is in transit?', 'Why did the transfer arrive short?'],
    indents: ['Raise an indent for 900 bags', 'Will cement last till Thursday?', 'What should I reorder?'],
    counts: ['Which items are due a count?', 'Start a count of yard 2', 'Read this count sheet'],
    reconcile: ['Why is steel over on slab L5?', 'Which subcontractor is over allowance?', 'Draft the recovery'],
    reports: ['What did we receive this month?', 'What is received but not invoiced?', 'Close out Site B'],
    settings: ['Set up my store', 'Import my item list', 'What approval limits should I use?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], cache: {}, store: '', q: '', only: '',
    chartItem: '', recItem: '', month: ''};
  try { ST.side = localStorage.getItem('hoola.store.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.store.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const SET = () => K().settings || {};
  const CAN = () => !!(ST.d && ST.d.status === 'hired');
  const cur = () => SET().currency || 'USD';
  const money = (v, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 3});
  const qty = (v, u) => `${num(v)} ${esc(u || '')}`;
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(d).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/stdesk/do/' + part, a || {});
  const tag = (t, c) => `<span class="cs-tag ${c || ''}">${esc(t)}</span>`;
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const ro = () => CAN() ? '' : '<p class="cs-note">The desk is paused: resume it in AI Employees to make changes.</p>';
  const ask = about => `<button class="ib sk-ask" type="button" aria-label="Ask about this" title="Ask in the chat" data-ask="${esc(about)}">${svg(IC.chat)}</button>`;
  const fld = (n, l, v, extra, ph) => `<label class="sk-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v, extra) => `<label class="sk-lab">${esc(l)}<select class="in" name="${n}" ${extra || ''}>${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v ?? '') ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows) => `<label class="sk-lab wide">${esc(l)}<textarea class="in" name="${n}" rows="${rows || 5}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const sev = c => c === 'bad' ? 'bad' : c === 'warn' ? 'warn' : c === 'ok' ? 'ok' : '';
  const checkRows = list => (list || []).map(c => `<div class="sk-ck"><span class="sk-ic ${sev(c.sev)}">${c.sev === 'ok' ? '✓' : c.sev === 'info' ? 'i' : '!'}</span><span>${esc(c.text)}</span></div>`).join('');
  const storeOpts = (all, first) => [...(first ? [['', first]] : []), ...((K().stores || []).map(s => [s.id, s.name]))];
  const itemOpts = () => (ST.cache.items || []).map(i => [i.name, `${i.name} · ${i.unit}`]);
  const who = (ph) => `<input class="in sk-who" name="who" maxlength="80" placeholder="${esc(ph || 'Your name')}" required>`;

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/stdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.store, '')}</div>
        <h1 class="sd-h">Your Material Store Manager is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="stHire">Hire the Material Store Manager</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#stHire').onclick = async () => { try { await api('POST', '/api/employees/const_store/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame();
    readTab();
    paintTabs();
    await loadItems();
    showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 60000));
  }
  async function loadItems() { try { ST.cache.items = (await run('items', {})).items || []; } catch { ST.cache.items = []; } }
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
          <div class="sd-ico">${svg(IC.store, '')}</div>
          <div style="min-width:0"><div class="sd-name">Material Store</div><div class="sd-site" id="stSite"></div></div>
          <span id="stState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Store chat">
          <div class="sd-chathead"><div class="t"><b>Store chat</b><span>Ask about stock, or drop a delivery note, a weighbridge ticket or a count sheet here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="stFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="stPick" multiple hidden accept="image/*,application/pdf,.pdf,.csv,.txt,.xlsx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Material store desk" id="sdTabs"></nav>
          <div id="stPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'A named person confirms and approves; Hoola orders, pays and deducts nothing.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your store…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#stPick').click()});
    $('#stPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.store.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.store.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/stdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#stPage').addEventListener('click', onPageClick);
    $('#stPage').addEventListener('submit', onSubmit);
    $('#stPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#stState'); if (!el) return;
    const k = K(), nd = k.serious || 0;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = SET();
    $('#stSite').textContent = [s.project || s.company, s.country, cur(), (k.stores || []).length ? pl((k.stores || []).length, 'store') : '', k.items ? pl(k.items, 'item') : ''].filter(Boolean).join(' · ') || 'Set up your store';
  }
  function paintTabs() {
    const n = K().counts || {};
    const b = {receive: n.receive, transfers: n.transfers, indents: n.indents, counts: n.counts, issue: n.issue};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      b[key] ? `<span class="n">${esc(b[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/stdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { ST.cache = {items: ST.cache.items}; await loadItems(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }
  async function changed(msg) { ST.cache = {items: ST.cache.items}; await refreshDesk(false); await loadItems(); showPage(true); if (msg) toast(msg); }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#stPage'); if (!box) return;
    const fn = {today: pToday, receive: pReceive, stock: pStock, issue: pIssue, transfers: pTransfers, indents: pIndents, counts: pCounts,
      reconcile: pReconcile, reports: pReports, settings: pSettings}[ST.tab] || pToday;
    const kept = keep ? typed(box) : null;
    box.innerHTML = fn();
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  /* what she is typing survives a redraw */
  function typed(box) {
    const out = {}, act = document.activeElement;
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = f.dataset.form + '|' + (f.dataset.id || '');
      [...f.querySelectorAll('input:not([type=file]):not([type=checkbox]), textarea, select')].forEach((el, j) => {
        if (el.name && (el.value !== el.defaultValue || el === act)) out[k + '|' + el.name + '#' + j] = {v: el.value, f: el === act};
      });
    });
    return out;
  }
  function retype(box, kept) {
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = f.dataset.form + '|' + (f.dataset.id || '');
      [...f.querySelectorAll('input:not([type=file]):not([type=checkbox]), textarea, select')].forEach((el, j) => {
        const v = kept[k + '|' + el.name + '#' + j]; if (!v) return; el.value = v.v; if (v.f) el.focus();
      });
    });
  }
  /* a part of the page that comes from the server: fetched once, then the page redraws */
  function lazy(key, part, a) {
    if (ST.cache[key] === undefined) {
      ST.cache[key] = null;
      run(part, a).then(r => { ST.cache[key] = r; showPage(true); }).catch(e => { ST.cache[key] = {error: e.message}; showPage(true); });
    }
    return ST.cache[key];
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;

  function stockChart(c) {
    if (!c || !c.history) return '';
    const pts = [...c.history.map(p => ({d: p.day, q: p.qty, f: false})), ...c.forecast.map(p => ({d: p.day, q: p.qty, f: true}))];
    const vals = pts.map(p => p.q).concat([c.rop || 0, 0]);
    let hi = Math.max(...vals), lo = Math.min(...vals);
    if (hi === lo) hi = lo + 1;
    const W = 900, H = 220, L = 52, R = 10, T = 14, B = 30, n = pts.length;
    const x = i => L + (W - L - R) * (i / Math.max(n - 1, 1)), y = v => T + (H - T - B) * (1 - (v - lo) / (hi - lo));
    const hist = pts.map((p, i) => [x(i), y(p.q), p]).filter(a => !a[2].f), fut = pts.map((p, i) => [x(i), y(p.q), p]).filter((a, i) => a[2].f || i === hist.length - 1);
    const path = a => a.map((q, i) => (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join(' ');
    const ticks = [hi, (hi + lo) / 2, lo].map(v => `<text class="tx" x="0" y="${(y(v) + 4).toFixed(1)}">${esc(num(Math.round(v)))}</text><line class="ax" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`).join('');
    const ti = hist.length - 1;
    const labels = [0, Math.floor(ti / 2), ti, n - 1].map(i => `<text class="tx" x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(i === ti ? 'today' : dmy(pts[i].d))}</text>`).join('');
    const marks = (c.marks || []).map(m => { const i = pts.findIndex(p => p.d === m.day); if (i < 0) return '';
      return `<circle class="sk-m ${m.kind}" cx="${x(i).toFixed(1)}" cy="${y(pts[i].q).toFixed(1)}" r="5"/><text class="tx sk-ml ${m.kind}" x="${(x(i) + 8).toFixed(1)}" y="${(y(pts[i].q) - 8).toFixed(1)}">${esc(m.label)}</text>`; }).join('');
    const low = c.short && c.lowest ? (() => { const i = pts.findIndex(p => p.d === c.lowest.day); return i < 0 ? '' : `<circle class="pt under low" cx="${x(i).toFixed(1)}" cy="${y(pts[i].q).toFixed(1)}" r="6"/>`; })() : '';
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(c.item)} available over the last 30 days and the next 14 days">
      ${ticks}${c.rop ? `<line class="min" x1="${L}" x2="${W - R}" y1="${y(c.rop).toFixed(1)}" y2="${y(c.rop).toFixed(1)}"/><text class="minl" x="${L + 6}" y="${(y(c.rop) - 6).toFixed(1)}">Reorder at ${esc(num(c.rop))} ${esc(c.unit)}</text>` : ''}
      <path class="area" d="${path(hist)} L${hist[hist.length - 1][0].toFixed(1)} ${y(lo).toFixed(1)} L${L} ${y(lo).toFixed(1)}Z"/>
      <path class="line" d="${path(hist)}"/><path class="line sk-fc" d="${path(fut)}"/>
      <line class="ax" x1="${x(ti).toFixed(1)}" x2="${x(ti).toFixed(1)}" y1="${T}" y2="${H - B}"/>${marks}${low}${labels}</svg></div>
      <div class="cs-legend"><span><i></i>On hand</span><span><i class="sk-fcl"></i>Forecast from orders and the look-ahead</span>${c.rop ? '<span><i class="min"></i>Your reorder point</span>' : ''}</div>`;
  }

  function pToday() {
    const k = K(), t = k.tiles || {};
    const sh = k.short || [];
    const lead = sh.length ? `${pl(sh.length, 'item')} run short before ${sh.length === 1 ? 'it is' : 'they are'} needed; check the orders below.`
      : (k.items ? 'Everything with a look-ahead is covered for the next two weeks.' : 'Set up your company, stores and items to start - or send me your item list in the chat.');
    let c = k.chart;
    if (ST.chartItem && ST.chartItem !== (c && c.item_id)) { const x = lazy('chart:' + ST.chartItem, 'chart', {item: ST.chartItem}); c = x && !x.error ? x : c; }
    const choices = (ST.cache.items || []).slice(0, 5);
    return `<section><h1 class="sd-h sk-greet">${greet()}</h1><p class="lead">${esc(lead)}</p></section>${ro()}
      <section class="cs-hero">
        <div class="top">
          <div class="k"><div class="l">Stock value today</div><div class="v">${money(k.value)}</div><div class="s">${pl((k.stores || []).length, 'store')} · ${esc({fifo: 'FIFO', wavg: 'weighted average cost', lifo: 'LIFO'}[k.method] || '')}${(k.unpriced || []).length ? ` · ${pl(k.unpriced.length, 'item')} with no price` : ''}</div></div>
          <div class="cs-arrow">→</div>
          <div class="k"><div class="l">Needed in the next 14 days</div><div class="v">${money(k.need14)}</div><div class="s">from your look-ahead × your prices</div></div>
          <div class="cs-arrow">→</div>
          <div class="k low${sh.length ? ' bad' : ''}"><div class="l">Short before need-by</div><div class="v">${sh.length ? pl(sh.length, 'item') : 'None'}</div><div class="s">${esc(sh.slice(0, 2).map(x => `${x.item} (−${num(x.short.short)} ${x.unit})`).join(' · ') || 'covered by stock and orders')}</div></div>
        </div>
        ${choices.length ? `<div class="sk-segrow"><span class="mut">Item</span><span class="cs-seg">${choices.map(i => `<button type="button" data-chart="${esc(i.id)}" aria-pressed="${(c && c.item_id) === i.id}">${esc(i.name)}</button>`).join('')}</span></div>` : ''}
        ${c && c.history ? stockChart(c) : empty('The chart appears once an item has stock or a look-ahead.')}
      </section>
      <section class="cs-4 grid" style="display:grid;gap:16px">
        ${kpi('Deliveries today', t.due_today ? `${num(t.due_today)} due` : 'None due', `${num(t.received_today || 0)} received`)}
        ${kpi('On quality hold', t.on_hold ? pl(t.on_hold, 'lot') : 'None', (t.hold_lots || []).join(' · ') || 'nothing waiting for QC')}
        ${kpi('Wastage this month', t.wastage === null || t.wastage === undefined ? '—' : `${num(t.wastage)}%`, `against your ${num(t.allowance)}% allowance`, t.wastage > t.allowance ? 'warn' : '')}
        ${kpi('Count accuracy', t.accuracy === null || t.accuracy === undefined ? '—' : `${(t.accuracy * 100).toFixed(1)}%`, t.count_lines ? `${pl(t.count_lines, 'line')} counted in 90 days` : 'no count yet', t.accuracy >= 0.98 ? 'ok' : '')}
      </section>
      <section class="sk-2">
        <div class="card"><h2 class="sk-h">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</div>
        <div class="card"><h2 class="sk-h">Coming in</h2>${(k.coming || []).length ? k.coming.map(x => `<div class="cs-row"><span class="mut sk-when">${esc(x.due ? dmy(x.due) : 'no date')}</span><span style="flex:1">${esc(x.item)} · ${qty(x.qty, x.unit)} · ${esc(x.supplier)}</span>${tag(x.late ? 'late' : x.po, x.late ? 'bad' : '')}</div>`).join('') : empty('No open purchase orders. Record one on Indents.')}</div>
      </section>
      ${!(k.items) ? `<section class="card"><h2 class="sk-h">Start here</h2><div class="sk-steps"><a class="btn soft" href="#/settings">1 · Company, country and currency</a><a class="btn soft" href="#/settings">2 · Stores and item list</a><a class="btn soft" href="#/receive">3 · Receive the first delivery</a></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- receive */
  const STEP = ['Read the papers', 'Match the order', 'Count and check', 'Confirm', 'Quality', 'Put away'];
  function steps(at) { return `<div class="sk-stepbar">${STEP.map((s, i) => `<span class="sk-step${i < at ? ' d' : i === at ? ' c' : ''}"><span class="n">${i < at ? '✓' : i + 1}</span>${esc(s)}</span>`).join('')}</div>`; }
  function pReceive() {
    if (ST.arg) return pReceipt(ST.arg);
    const grn = lazy('grn', 'docs', {kind: 'grn'}), qq = lazy('qq', 'quality_queue', {}), pos = lazy('po', 'docs', {kind: 'po'});
    if (!grn || !qq || !pos) return loading();
    const drafts = (grn.rows || []).filter(r => r.status === 'draft'), done = (grn.rows || []).filter(r => r.status !== 'draft').slice(0, 20);
    const openPo = (pos.rows || []).filter(p => ['open', 'part'].includes(p.status));
    return `<section class="sk-headrow"><div><h1 class="sd-h">Receive</h1><p class="lead">Every delivery is matched three ways - your order, the supplier's paper and your count - before anything enters stock.</p></div></section>${ro()}
      <section class="card sk-cam"><div style="flex:1"><h2 class="sk-h">Read a delivery paper</h2><p class="mut" style="margin:0;font-size:14px">Send a photo of the ${esc((SET().pack || {}).delivery_word || 'delivery note')}, the weighbridge ticket or the mill certificate to the Store chat - Hoola reads it and drafts the receipt here.</p></div>
        ${CAN() ? `<label class="btn">${svg(IC.cam)}<span>Take or choose a photo</span><input type="file" accept="image/*,application/pdf" capture="environment" data-photo="1" hidden></label>` : ''}</section>
      ${drafts.length ? `<section class="card"><h2 class="sk-h">Waiting to be confirmed</h2>${drafts.map(d => `<div class="cs-row"><span class="cs-dot${d.data.bad ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(d.number)}</b> · ${esc(d.party)} · ${pl(d.lines.length, 'line')}${d.data.bad ? ` · ${pl(d.data.bad, 'serious check')}` : ''}</span><button class="btn soft sm" type="button" data-go="receive/${esc(d.id)}">Open</button></div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="sk-h">On quality hold and blocked</h2>${(qq.rows || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Item and lot</th><th>Store</th><th class="num">Quantity</th><th>Days</th><th></th></tr></thead><tbody>${
        qq.rows.map(r => `<tr><td>${esc(r.item)}<div class="mut sk-sub">${esc(r.lot ? (r.lot + (r.cert ? ' · ' + r.cert : ' · no certificate')) : 'no lot number')}</div></td><td>${esc(r.store)}</td><td class="num">${qty(r.qty, r.unit)}</td><td>${r.pos === 'blocked' ? tag('blocked', 'bad') : tag(num(r.days ?? 0) + ' d', (r.days || 0) >= 3 ? 'warn' : '')}</td>
          <td>${CAN() ? (r.pos === 'hold' ? `<form class="sk-inline" data-form="quality" data-id="${esc(r.lot_id)}">${who('QC engineer')}${r.cert ? '' : '<input class="in" name="cert" placeholder="Certificate no.">'}<button class="btn soft sm" name="decision" value="accept">Accept</button><button class="btn soft sm" name="decision" value="reject">Reject</button></form>`
            : `<form class="sk-inline" data-form="return" data-id="${esc(r.lot_id)}">${who()}<input class="in" name="reason" placeholder="Reason"><button class="btn soft sm">Send back</button></form>`) : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing is on hold. Items you mark "needs inspection" and heats with no certificate land here.')}</section>
      ${CAN() ? `<section class="card"><h2 class="sk-h">Or type the delivery</h2>
        <form data-form="receipt" class="sk-grid">
          ${fld('supplier', 'Supplier', '', 'required maxlength="160"')}${fld('doc_no', (cap((SET().pack || {}).delivery_word || 'delivery note')) + ' number', '', 'maxlength="60"')}
          ${sel('po', 'Against order', [['', 'No order'], ...openPo.map(p => [p.number, `${p.number} · ${p.party}`])], '')}${sel('store', 'Into store', storeOpts(), '')}
          ${area('text', 'Lines: item, quantity, unit, lot or heat, certificate', 'Rebar B500B 16 mm, 7.4, t, 7G39, MTC 39-2211', 4)}
          <div class="wide sk-acts"><span class="mut">The paper's quantity is taken as counted here - change it on the receipt if your count differs.</span><button class="btn" type="submit">Draft the receipt</button></div>
        </form></section>` : ''}
      <section class="card"><h2 class="sk-h">Received</h2>${done.length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Receipt</th><th>Supplier</th><th>Day</th><th>Status</th></tr></thead><tbody>${done.map(d => `<tr class="sk-click" data-go="receive/${esc(d.id)}"><td><b>${esc(d.number)}</b></td><td>${esc(d.party)}</td><td>${dmy(d.day)}</td><td>${tag(d.status, d.status === 'rejected' ? 'bad' : 'ok')}${d.data.invoiced ? ' ' + tag('invoiced', '') : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No deliveries yet.')}</section>`;
  }
  function pReceipt(id) {
    const d = lazy('doc:' + id, 'doc', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${empty(d.error)}</section>`;
    const x = d.data || {}, draft = d.status === 'draft';
    const lines = d.lines || [];
    const tot = k => lines.reduce((a, l) => a + (Number(l[k]) || 0), 0);
    const at = draft ? (lines.every(l => l.counted !== null && l.counted !== undefined) ? 3 : 2) : 5;
    const checks = [...(x.checks || []), ...lines.flatMap(l => (l.checks || []).map(c => ({...c, text: (lines.length > 1 ? l.item + (l.src && l.src.lot ? ' ' + l.src.lot : '') + ': ' : '') + c.text})))];
    return `<a class="md-back" href="#/receive">${svg(IC.back)}Receive</a>
      <section class="sk-headrow"><div style="flex:1;min-width:0"><h1 class="sd-h">${esc(d.number)} · ${esc(x.doc_no || 'no paper number')}</h1>
        <p class="lead">${esc(d.party)}${x.vehicle ? ' · ' + esc(x.vehicle) : ''} · ${esc(d.store)}${x.po ? ' · against ' + esc(x.po) : ''} · ${dmy(d.day)}</p></div>
        ${draft && CAN() ? `<form class="sk-inline" data-form="confirm" data-id="${esc(d.id)}">${who('Received by (name)')}<button class="btn soft" name="act" value="reject">Reject the delivery</button><button class="btn" name="act" value="confirm">Confirm the receipt</button></form>` : tag(d.status, d.status === 'rejected' ? 'bad' : 'ok')}</section>
      ${steps(at)}
      <section class="sk-split">
        <div class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">What arrived${x.po ? ', against ' + esc(x.po) : ''}</h2>${tag(pl(lines.length, 'line'))}</div>
          <div class="sk-tw"><table class="tb"><thead><tr><th>Item and lot</th><th class="num">Paper says</th><th class="num">Counted / weighed</th><th class="num">Accept</th><th>Goes to</th></tr></thead><tbody>${lines.map(l => {
            const s = l.src || {};
            const bad = (l.checks || []).some(c => c.sev === 'bad');
            return `<tr><td>${esc(l.item)}<div class="mut sk-sub">${esc([s.lot && (l.unit === 't' ? 'heat ' : 'lot ') + s.lot, s.cert, s.made && 'made ' + s.made].filter(Boolean).join(' · ') || '—')}</div></td>
              <td class="num">${l.doc_qty === null || l.doc_qty === undefined ? '—' : qty(l.doc_qty, l.unit)}</td><td class="num">${l.counted === null || l.counted === undefined ? tag('not counted', 'warn') : qty(l.counted, l.unit)}</td>
              <td class="num"><b>${qty(l.accept, l.unit)}</b></td><td>${l.short > 0 ? tag('−' + num(l.short) + ' short', 'bad') + ' ' : ''}${tag(l.to === 'hold' ? 'quality hold' : 'available', l.to === 'hold' ? 'warn' : bad ? 'bad' : 'ok')}</td></tr>`; }).join('')}</tbody>
            <tfoot><tr><td><b>Total</b></td><td class="num">${num(tot('doc_qty'))}</td><td class="num">${num(tot('counted'))}</td><td class="num"><b>${num(tot('accept'))}</b></td><td></td></tr></tfoot></table></div>
          ${draft && CAN() ? `<details class="sk-more"><summary>Change a count or add the weighbridge figures</summary>
            <form data-form="recount" data-id="${esc(d.id)}" class="sk-grid">${lines.map((l, i) => `<div class="wide sk-lrow"><b>${esc(l.item)} ${esc((l.src || {}).lot || '')}</b>
              ${fld('qty_' + i, 'Counted (' + l.unit_in + ')', (l.src || {}).qty ?? '')}${fld('gross_' + i, 'Gross', (l.src || {}).gross ?? '')}${fld('tare_' + i, 'Tare', (l.src || {}).tare ?? '')}${fld('damaged_' + i, 'Damaged', (l.src || {}).damaged ?? '')}${fld('cert_' + i, 'Certificate', (l.src || {}).cert ?? '')}</div>`).join('')}
              <div class="wide sk-acts"><span></span><button class="btn soft" type="submit">Check again</button></div></form></details>` : ''}
        </div>
        <div class="card"><h2 class="sk-h">Checks</h2>${checkRows(checks) || empty('No checks.')}
          ${x.read_from ? `<p class="cs-note">Read from ${esc(x.read_from)}. A field that could not be read was left blank.</p>` : ''}${x.reject ? `<p class="cs-neg">Rejected: ${esc(x.reject)}</p>` : ''}</div>
      </section>
      <section class="card sk-after"><div style="flex:1"><h2 class="sk-h">${draft ? 'After you confirm' : 'What happened'}</h2><p class="mut" style="margin:0;font-size:14px">${esc(
        lines.filter(l => l.to === 'available').length ? `${num(lines.filter(l => l.to === 'available').reduce((a, l) => a + l.accept, 0))} goes to available` : '')}${
        lines.filter(l => l.to === 'hold').length ? ` · ${esc(num(lines.filter(l => l.to === 'hold').reduce((a, l) => a + l.accept, 0)))} to quality hold for the QC engineer` : ''} · the receipt goes to Books for the invoice match.</p></div>
        <div class="sk-tags">${d.approver ? tag('Received by: ' + d.approver) : ''}${x.driver ? tag('Driver: ' + x.driver) : ''}${!draft && d.status === 'confirmed' && !x.invoiced && CAN() ? `<form class="sk-inline" data-form="invoiced" data-id="${esc(d.id)}"><input class="in" name="invoice" placeholder="Supplier invoice no."><button class="btn soft sm">Matched to invoice</button></form>` : ''}</div></section>`;
  }

  /* ---------------------------------------------------------------- stock */
  function pStock() {
    if (ST.arg) return pItem(ST.arg);
    const key = `stock:${ST.store}|${ST.q}|${ST.only}`;
    const r = lazy(key, 'stock', {store: ST.store, q: ST.q, only: ST.only});
    const fil = [['', 'Everything'], ['below', 'Below reorder'], ['hold', 'On hold'], ['ageing', 'Ageing'], ['stale', 'Not moving']];
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Stock</h1><p class="lead">${r && !r.error ? `${pl(r.items.length, 'item')} · ${money(r.total)} at ${esc({fifo: 'FIFO', wavg: 'weighted average cost', lifo: 'LIFO'}[SET().valuation] || '')}` : 'What is in each store, on hold, with subcontractors and in transit.'}</p></div>
        <span class="cs-seg">${[['', 'All stores'], ...(K().stores || []).map(s => [s.id, s.name])].map(([v, t]) => `<button type="button" data-store="${esc(v)}" aria-pressed="${ST.store === v}">${esc(t)}</button>`).join('')}</span></section>
      <section class="sk-filters"><form data-form="search" style="flex:1"><input class="in" name="q" value="${esc(ST.q)}" placeholder="Search items, codes, heat numbers, lots…"></form>
        <span class="cs-seg">${fil.map(([v, t]) => `<button type="button" data-only="${v}" aria-pressed="${ST.only === v}">${esc(t)}</button>`).join('')}</span></section>
      ${!r ? loading() : r.error ? `<section class="card">${empty(r.error)}</section>` : `<section class="card tight"><div class="sk-tw"><table class="tb sk-stock"><thead><tr><th>Item</th><th>Class</th><th class="num">Available</th><th class="num">On hold</th><th class="num">With subcontractors</th><th class="num">In transit</th><th style="width:150px">Cover vs reorder</th><th class="num">Value</th></tr></thead><tbody>${
        r.items.map(i => `<tr class="sk-click" data-go="stock/${esc(i.id)}"><td><b>${esc(i.item)}</b> <span class="mut">· ${esc(i.unit)}</span>${i.flags.length ? '<div>' + i.flags.map(f => tag(f, f.startsWith('below') ? 'bad' : 'warn')).join(' ') + '</div>' : ''}</td><td>${tag(i.class)}</td>
          <td class="num">${num(i.available)}</td><td class="num">${i.hold ? num(i.hold) : '—'}</td><td class="num">${i.holder ? num(i.holder) : '—'}</td><td class="num">${i.transit ? num(i.transit) : '—'}</td>
          <td>${i.cover === null ? '<span class="mut">—</span>' : `<div class="sk-bar"><span class="${i.cover < 1 ? 'bad' : i.cover < 1.5 ? 'warn' : ''}" style="width:${Math.min(100, Math.round(i.cover / 2 * 100))}%"></span></div>`}</td><td class="num">${money(i.value)}</td></tr>`).join('') || `<tr><td colspan="8">${empty('Nothing here.')}</td></tr>`}</tbody></table></div></section>`}`;
  }
  const KIND = {receive: ['Receive', ''], accept: ['Accepted', 'ok'], reject: ['Rejected', 'bad'], return_vendor: ['Sent back', 'bad'], issue: ['Issue', 'v'],
    issue_free: ['Free issue', 'v'], return: ['Return', 'ok'], transfer_out: ['Transfer out', ''], transfer_in: ['Transfer in', ''], adjust: ['Adjustment', 'warn'],
    scrap: ['Scrap', 'warn'], reverse: ['Reverse', 'bad']};
  function pItem(id) {
    const d = lazy('item:' + id, 'item', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${empty(d.error)}</section>`;
    const r = d.reorder || {};
    return `<a class="md-back" href="#/stock">${svg(IC.back)}Stock</a>
      <section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">${esc(d.name)}</h1><p class="lead">${esc([d.code, 'base unit ' + d.unit, Object.keys(d.conv || {}).map(u => `1 ${u} = ${d.conv[u]} ${d.unit}`).join(', '), 'class ' + d.class, d.trace !== 'none' ? 'traced by ' + d.trace : ''].filter(Boolean).join(' · '))}</p></div>${ask('Item ' + d.name)}</section>
      <section class="sk-3">
        <div class="card"><h2 class="sk-h">Where it is</h2>${(d.places || []).length ? d.places.map(p => `<div class="cs-row"><span style="flex:1">${esc(p.where === 'holder' ? 'with ' + p.holder : p.store + (p.where !== 'available' ? ' · ' + p.where : ''))}${p.lot ? ' <span class="mut">· ' + esc(p.lot) + '</span>' : ''}</span><b>${qty(p.qty, d.unit)}</b></div>`).join('') : empty('None in stock.')}</div>
        <div class="card"><h2 class="sk-h">Reorder</h2><div class="sk-big">${qty(r.rop, d.unit)}</div><p class="cs-note">${esc(r.basis || '')}</p></div>
        <div class="card"><h2 class="sk-h">Lots, oldest first</h2>${(d.lots || []).length ? d.lots.map(l => `<div class="cs-row"><span style="flex:1">${esc(l.ref || 'no number')}<div class="mut sk-sub">${esc([l.received && 'in ' + dmy(l.received), l.cert || (d.trace === 'heat' ? 'no certificate' : ''), l.expires && 'expires ' + dmy(l.expires)].filter(Boolean).join(' · '))}</div></span><b>${qty(l.qty, d.unit)}</b></div>`).join('') : empty('No lots in stock.')}</div>
      </section>
      ${(d.storage || []).length || (d.docs_needed || []).length ? `<section class="card"><h2 class="sk-h">Rules for this item in ${esc(SET().country || 'your country')}</h2>${[...(d.storage || []).map(s => ({t: s.rule, src: s.source, c: s.check})), ...(d.docs_needed || []).map(s => ({t: s.need, src: s.source, c: s.check}))].map(s => `<div class="cs-row"><span style="flex:1">${esc(s.t)}<div class="mut sk-sub">${esc(s.src)}</div></span>${s.c ? tag('check this', 'warn') : ''}</div>`).join('')}</section>` : ''}
      <section class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Every movement</h2><button class="btn soft sm" type="button" data-csv="ledger">Export</button></div>
        <div class="sk-tw"><table class="tb"><thead><tr><th>When</th><th>Movement</th><th>Lot</th><th>From → to</th><th>For</th><th class="num">Quantity</th><th>By</th><th></th></tr></thead><tbody>${(d.ledger || []).map(m => {
          const k = KIND[m.kind] || [m.kind, ''];
          const out = ['available', 'hold', 'blocked', 'transit', 'holder'].includes(m.from_pos) && !['available', 'hold', 'blocked', 'transit', 'holder'].includes(m.to_pos);
          const inn = !['available', 'hold', 'blocked', 'transit', 'holder'].includes(m.from_pos);
          return `<tr${m.reversed ? ' class="sk-struck"' : ''}><td class="nw">${dt(m.at)}</td><td>${tag(k[0], k[1])}</td><td>${esc(m.lot || '—')}</td><td>${esc(m.from)} → ${esc(m.to)}</td><td>${esc(m.work || (m.doc && (m.doc.grn || m.doc.slip || m.doc.adjust)) || '—')}</td>
            <td class="num">${inn ? '+' : out ? '−' : ''}${qty(m.qty, m.unit)}</td><td>${esc(m.who || '—')}${m.approver && m.approver !== m.who ? `<div class="mut sk-sub">approved: ${esc(m.approver)}</div>` : ''}</td>
            <td>${CAN() && !m.reversed && m.kind !== 'reverse' ? `<details class="sk-rev"><summary>Reverse</summary><form class="sk-inline" data-form="reverse" data-id="${esc(m.id)}">${who('Approved by')}<input class="in" name="reason" placeholder="Why" required><button class="btn soft sm">Reverse</button></form></details>` : ''}</td></tr>`; }).join('')}</tbody></table></div>
        <p class="cs-note">Nothing is ever edited: a mistake gets a reverse row with the approver's name.</p></section>`;
  }

  /* ---------------------------------------------------------------- issue & returns */
  function pIssue() {
    const sl = lazy('slips', 'docs', {kind: 'slip'}), held = lazy('held', 'reconcile', {}), hs = lazy('holders', 'holders', {});
    if (!sl || !held || !hs) return loading();
    const drafts = (sl.rows || []).filter(r => r.status === 'draft');
    const today = (sl.rows || []).filter(r => r.status === 'posted' && r.day === new Date().toISOString().slice(0, 10)).slice(0, 20);
    const H = held.holders || [];
    return `<section><h1 class="sd-h">Issue &amp; returns</h1><p class="lead">Every issue names the work it is for, so it can be reconciled later. Oldest stock goes first.</p></section>${ro()}
      <section class="sk-split wide">
        ${CAN() ? `<div class="card"><h2 class="sk-h">New slip</h2><form data-form="slip" class="sk-grid">
          ${sel('type', 'Slip', [['issue', 'Issue to the work'], ['return', 'Return to the store'], ['transfer', 'Transfer to another store']], 'issue')}
          ${sel('item', 'Item', itemOpts(), '')}${fld('qty', 'Quantity', '', 'inputmode="decimal" required')}${fld('unit', 'Unit (blank = the item\'s)', '', 'maxlength="12"')}
          ${fld('work', 'For the work (work package / cost code)', '', 'maxlength="80"')}${sel('holder', 'To (free issue)', [['', 'Own gang'], ...(hs.rows || []).map(h => [h.name, h.name])], '')}
          ${fld('person', 'Tool issued to (person)', '', 'maxlength="80"')}${sel('from_holder', 'Return from', [['', 'The work'], ...(hs.rows || []).map(h => [h.name, h.name])], '')}
          ${sel('store', 'From store', storeOpts(), '')}${sel('to_store', 'To store (transfer)', storeOpts(false, '—'), '')}
          <div class="wide sk-acts"><span class="mut">Drafted first; a named person confirms it.</span><button class="btn" type="submit">Draft the slip</button></div></form></div>` : ''}
        <div class="card"><h2 class="sk-h">Held by subcontractors (free issue)</h2>${H.length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Holder</th><th>Item</th><th class="num">Used</th><th>Use vs allowance</th></tr></thead><tbody>${H.map(h => `<tr><td>${esc(h.holder)}</td><td>${esc(h.item)}</td><td class="num">${qty(h.actual, h.unit)}</td><td>${tag(h.pct === null ? 'no QS quantity' : `${h.pct > 0 ? '+' : ''}${num(h.pct)}% / ${num(h.allowance)}%`, h.excess > 0 ? 'bad' : h.pct !== null && h.pct > h.allowance * 0.8 ? 'warn' : 'ok')}</td></tr>`).join('')}</tbody></table></div>` : empty('No free-issue material yet.')}
          <p class="cs-note">Allowances and recovery rates come from each subcontract. A recovery is drafted for the Contracts desk; deducting is your call.</p>
          ${CAN() ? `<details class="sk-more"><summary>Add a subcontractor</summary><form data-form="holder" class="sk-grid">${fld('name', 'Name', '', 'required maxlength="120"')}${fld('allowance', 'Allowance %', '', 'inputmode="decimal"')}${fld('uplift', 'Recovery uplift %', '', 'inputmode="decimal"')}${fld('clause', 'Clause in the subcontract', '', 'maxlength="200"')}${sel('rate_item', 'Rate for item', [['', '—'], ...itemOpts()], '')}${fld('rate', 'Rate per base unit', '', 'inputmode="decimal"')}<div class="wide sk-acts"><span></span><button class="btn soft">Save</button></div></form></details>` : ''}</div>
      </section>
      ${drafts.length ? `<section class="card"><h2 class="sk-h">Waiting to be confirmed</h2>${drafts.map(d => slipRow(d)).join('')}</section>` : ''}
      <section class="card"><h2 class="sk-h">Today's slips</h2>${today.length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Slip</th><th>Item</th><th>To · for</th><th class="num">Quantity</th></tr></thead><tbody>${today.map(d => `<tr><td>${esc(d.number)}</td><td>${esc(d.data.item)}</td><td>${esc([d.data.holder || d.data.person || (d.data.type === 'return' ? 'returned' : 'own gang'), d.data.work].filter(Boolean).join(' · '))}</td><td class="num">${qty(d.data.qty_in, d.data.unit_in)}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing issued today yet.')}</section>`;
  }
  function slipRow(d) {
    const x = d.data || {};
    return `<div class="sk-slip"><div style="flex:1;min-width:0"><b>${esc(d.number)}</b> · ${esc(cap(x.type))} · ${esc(x.item)} ${qty(x.qty_in, x.unit_in)}${x.work ? ' · for ' + esc(x.work) : ''}${x.holder ? ' · to ' + esc(x.holder) : ''}${x.person ? ' · to ' + esc(x.person) : ''}
        ${(x.warn || []).map(w => `<div class="cs-neg sk-sub">${esc(w)}</div>`).join('')}${x.budget ? `<div class="sk-bar sm"><span class="${x.budget.over ? 'bad' : ''}" style="width:${Math.min(100, Math.round((x.budget.share || 0) * 100))}%"></span></div><div class="mut sk-sub">${esc(x.budget.work)}: ${num(x.budget.after)} of ${num(x.budget.budget)} ${esc(x.unit)} after this</div>` : ''}</div>
      ${CAN() ? `<form class="sk-inline" data-form="confirmslip" data-id="${esc(d.id)}">${who('Confirmed by')}<button class="btn soft sm" name="act" value="cancel">Cancel</button><button class="btn sm" name="act" value="confirm">Confirm</button></form>` : ''}</div>`;
  }

  /* ---------------------------------------------------------------- transfers */
  function pTransfers() {
    const tr = lazy('transit', 'transit', {});
    if (!tr) return loading();
    return `<section><h1 class="sd-h">Transfers</h1><p class="lead">Two steps: sent (in transit) and received at the other store. A short arrival stays as a named difference until a person settles it.</p></section>${ro()}
      <section class="card"><h2 class="sk-h">In transit</h2>${(tr.rows || []).length ? tr.rows.map(d => `<div class="sk-slip"><div style="flex:1"><b>${esc(d.number)}</b> · ${esc(d.data.item)} ${qty(d.data.qty, d.data.unit)} · ${esc(d.from)} → ${esc(d.to)} ${tag(d.status === 'short' ? `arrived ${num(d.data.short)} short` : pl(d.days, 'day'), d.status === 'short' ? 'bad' : d.days >= 2 ? 'warn' : '')}</div>
        ${CAN() && d.status === 'transit' ? `<form class="sk-inline" data-form="rcvtransfer" data-id="${esc(d.id)}">${who('Received by')}<input class="in" name="qty" inputmode="decimal" placeholder="Received (${esc(d.data.unit)})"><button class="btn sm">Received</button></form>` : ''}</div>`).join('') : empty('Nothing in transit. Draft a transfer on Issue & returns.')}</section>`;
  }

  /* ---------------------------------------------------------------- indents, orders, look-ahead */
  function pIndents() {
    const ind = lazy('indents', 'docs', {kind: 'indent'}), sf = lazy('shortfall', 'shortfall', {}), ro_ = lazy('reorder', 'reorder', {}), pos = lazy('po', 'docs', {kind: 'po'}), bud = lazy('budgets', 'budgets', {});
    if (!ind || !sf || !ro_ || !pos || !bud) return loading();
    const wait = (ind.rows || []).filter(r => r.status === 'waiting');
    const below = (ro_.rows || []).filter(r => r.below);
    return `<section><h1 class="sd-h">Indents</h1><p class="lead">What runs short before it is needed, indents raised against the budget, and your purchase orders. Hoola never places an order.</p></section>${ro()}
      <section class="card"><h2 class="sk-h">Runs short before it is needed</h2>${(sf.rows || []).filter(r => r.short).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Item</th><th class="num">Available</th><th class="num">Needed</th><th>Short</th><th>Coming</th></tr></thead><tbody>${sf.rows.filter(r => r.short).map(r => `<tr><td>${esc(r.item)}</td><td class="num">${qty(r.available, r.unit)}</td><td class="num">${qty(r.demand, r.unit)}</td><td>${tag(`−${num(r.short.short)} by ${dmy(r.short.date)}`, 'bad')} <span class="mut sk-sub">${esc(r.short.work)}</span></td><td>${(r.incoming || []).map(i => esc(`${i.po} ${num(i.qty)} on ${dmy(i.due)}`)).join('<br>') || '—'}</td></tr>`).join('')}</tbody></table></div>` : empty((bud.rows || []).some(b => b.need_qty) ? 'Nothing runs short: stock and orders cover the look-ahead.' : 'Add your look-ahead (need-by dates) to the budgets below to see what runs short.')}</section>
      ${wait.length ? `<section class="card"><h2 class="sk-h">Indents waiting</h2>${wait.map(d => `<div class="sk-slip"><div style="flex:1"><b>${esc(d.number)}</b> · ${esc(d.party || 'site')} · ${esc(d.data.item)} ${qty(d.data.qty_in, d.data.unit_in)}${d.data.work ? ' · ' + esc(d.data.work) : ''}${d.data.need_by ? ' · by ' + dmy(d.data.need_by) : ''}${(d.data.warn || []).map(w => `<div class="cs-neg sk-sub">${esc(w)}</div>`).join('')}</div>
        ${CAN() ? `<form class="sk-inline" data-form="indent" data-id="${esc(d.id)}">${who('Decided by')}<button class="btn soft sm" name="decision" value="reject">Turn down</button><button class="btn sm" name="decision" value="approve">Approve</button></form>` : ''}</div>`).join('')}</section>` : ''}
      <section class="sk-split wide">
        <div class="card"><h2 class="sk-h">Below the reorder point</h2>${below.length ? below.map(r => `<div class="cs-row"><span style="flex:1">${esc(r.item)}<div class="mut sk-sub">${esc(r.basis)}</div></span><b>${qty(r.available, r.unit)}</b>${r.suggest ? tag('order ~' + num(r.suggest)) : ''}</div>`).join('') : empty('Nothing is below its reorder point.')}
          ${CAN() ? `<details class="sk-more"><summary>Raise an indent</summary><form data-form="newindent" class="sk-grid">${sel('item', 'Item', itemOpts(), '')}${fld('qty', 'Quantity', '', 'inputmode="decimal" required')}${fld('work', 'For the work', '', 'maxlength="80"')}${fld('need_by', 'Need by', '', 'type="date"')}${fld('by', 'Raised by', '', 'maxlength="80"')}<div class="wide sk-acts"><span></span><button class="btn soft">Raise</button></div></form></details>` : ''}</div>
        <div class="card"><h2 class="sk-h">Purchase orders</h2>${(pos.rows || []).length ? (pos.rows || []).slice(0, 20).map(p => `<div class="cs-row"><span style="flex:1"><b>${esc(p.number)}</b> · ${esc(p.party)}${p.data.due ? ' · due ' + dmy(p.data.due) : ''}<div class="mut sk-sub">${esc(p.lines.map(l => `${l.item} ${num(l.received)}/${num(l.qty)} ${l.unit}`).join(' · '))}</div></span>${tag(p.status, p.status === 'received' ? 'ok' : '')}</div>`).join('') : empty('No orders recorded.')}
          ${CAN() ? `<details class="sk-more"><summary>Record a purchase order</summary><form data-form="po" class="sk-grid">${fld('number', 'Order number', '', 'required maxlength="20"')}${fld('supplier', 'Supplier', '', 'required maxlength="160"')}${fld('due', 'Due', '', 'type="date"')}${area('lines', 'Lines: item, quantity, unit, rate', 'Cement CEM I 42.5N, 800, bag, 18', 3)}<div class="wide sk-acts"><span></span><button class="btn soft">Record</button></div></form></details>` : ''}</div>
      </section>
      <section class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Budgets and look-ahead (from your QS)</h2></div>${(bud.rows || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Work</th><th>Item</th><th class="num">Should use</th><th class="num">Done</th><th>Needed by</th></tr></thead><tbody>${bud.rows.map(b => `<tr><td>${esc(b.work)}</td><td>${esc(b.item)}</td><td class="num">${qty(b.qty, b.unit)}</td><td class="num">${num(b.done)}%</td><td>${b.need_by ? `${qty(b.need_qty, b.unit)} by ${dmy(b.need_by)}` : '—'}</td></tr>`).join('')}</tbody></table></div>` : empty('No QS quantities yet.')}
        ${CAN() ? `<details class="sk-more"><summary>Paste the take-off (CSV)</summary><form data-form="budgets" class="sk-grid">${area('text', 'work, item, qty, unit, allowance, done, need_by, need_qty', 'work,item,qty,unit,allowance,done,need_by,need_qty\nSlab L6,Cement CEM I 42.5N,1000,bag,3,40,2026-12-03,600', 4)}<div class="wide sk-acts"><span></span><button class="btn soft">Save</button></div></form>
          <form data-form="progress" class="sk-grid">${fld('work', 'Work package', '', 'required')}${fld('done', '% done (your number)', '', 'inputmode="decimal" required')}<div class="wide sk-acts"><span></span><button class="btn soft">Update progress</button></div></form></details>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- counts */
  function pCounts() {
    if (ST.arg) return pCount(ST.arg);
    const plan = lazy('plan', 'plan', {}), cs = lazy('counts', 'docs', {kind: 'count'}), adj = lazy('adjusts', 'docs', {kind: 'adjust'}), acc = lazy('acc', 'accuracy', {});
    if (!plan || !cs || !adj || !acc) return loading();
    const due = (plan.rows || []).filter(r => r.due), wait = (adj.rows || []).filter(a => a.status === 'waiting');
    const recount = (cs.rows || []).filter(c => c.status === 'recount');
    const tiers = SET().tiers || [];
    const cd = SET().count_days || {};
    return `<section><h1 class="sd-h">Counts</h1><p class="lead">A items every ${num(cd.A)} days, B every ${num(cd.B)}, C every ${num(cd.C)} - your plan. Sheets never show the book quantity until both counters have entered theirs.</p></section>${ro()}
      <section class="cs-4 grid" style="display:grid;gap:16px">${kpi('Due', pl(due.length, 'item'), [...new Set(due.map(d => d.store))].join(' · ') || 'nothing due')}${kpi('Waiting for a recount', num(recount.length), recount.map(r => r.number).join(' · ') || '—', recount.length ? 'warn' : '')}
        ${kpi('Adjustments to approve', num(wait.length), wait.length ? money(wait.reduce((a, x) => a + Math.abs(x.data.value || 0), 0)) + ' in total' : '—')}${kpi('Accuracy, 90 days', acc.accuracy === null ? '—' : (acc.accuracy * 100).toFixed(1) + '%', 'by value', acc.accuracy >= 0.98 ? 'ok' : '')}</section>
      <section class="sk-split">
        <div class="card"><h2 class="sk-h">Counts</h2>${(cs.rows || []).length ? cs.rows.slice(0, 20).map(c => `<div class="cs-row sk-click" data-go="counts/${esc(c.id)}"><span style="flex:1"><b>${esc(c.number)}</b> · ${esc(c.store)} · ${pl(c.lines.length, 'item')} · ${dmy(c.day)}</span>${tag(c.status, c.status === 'recount' ? 'warn' : c.status === 'closed' ? 'ok' : '')}</div>`).join('') : empty('No counts yet.')}
          ${CAN() ? `<details class="sk-more" open><summary>Start a count</summary><form data-form="opencount" class="sk-grid">${sel('store', 'Store', storeOpts(), '')}${fld('c1', 'Counter 1', '', 'required maxlength="80"')}${fld('c2', 'Counter 2 (not reporting to the storekeeper)', '', 'required maxlength="80"')}<div class="wide sk-acts"><span class="mut">Due items of that store, or everything in it.</span><button class="btn">Start</button></div></form></details>` : ''}</div>
        <div style="display:flex;flex-direction:column;gap:16px">
          <div class="card"><h2 class="sk-h">Who approves an adjustment</h2>${tiers.map((t, i) => `<div class="cs-row"><span style="flex:1">${t[0] === null ? 'Above ' + money(tiers[i - 1] ? tiers[i - 1][0] : 0) : 'Up to ' + money(t[0])}</span><span class="mut">${esc(t[1])}</span></div>`).join('')}<p class="cs-note">Your tiers, from Settings. Hoola never posts an adjustment.</p></div>
          <div class="card"><h2 class="sk-h">Waiting for you</h2>${wait.length ? wait.map(a => `<div class="sk-slip"><div style="flex:1">${esc(a.data.item)} · ${a.data.qty > 0 ? '+' : ''}${qty(a.data.qty, a.data.unit)} · ${money(a.data.value)}<div class="mut sk-sub">${esc(a.number)} from ${esc(a.data.count)} · approved by the ${esc((a.data.tier || {}).who || '')}</div></div>
            ${CAN() ? `<form class="sk-inline" data-form="adjust" data-id="${esc(a.id)}">${who('Approver')}<input class="in" name="role" value="${esc((a.data.tier || {}).who || '')}" aria-label="Role"><input class="in" name="reason" placeholder="Reason" required><button class="btn soft sm" name="decision" value="reject">Turn down</button><button class="btn sm" name="decision" value="approve">Approve</button></form>` : ''}</div>`).join('') : empty('Nothing waiting.')}</div>
        </div>
      </section>
      <section class="card"><h2 class="sk-h">Due a count</h2>${due.length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Item</th><th>Store</th><th>Class</th><th>Why</th></tr></thead><tbody>${due.map(r => `<tr><td>${esc(r.item)}</td><td>${esc(r.store)}</td><td>${tag(r.class)}</td><td class="mut">${esc(r.why)}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing is due.')}</section>`;
  }
  function pCount(id) {
    const c = lazy('doc:' + id, 'doc', {id});
    if (!c) return loading();
    if (c.error) return `<section class="card">${empty(c.error)}</section>`;
    const cs = (c.data || {}).counters || [];
    const open = ['counting', 'recount'].includes(c.status);
    const slot = c.status === 'recount' ? 'c3' : null;
    const res = {matches: ['matches', 'ok'], within: ['within tolerance', 'ok'], recount: ['recount', 'bad'], adjust: ['to approve', 'warn'], 'to count': ['to count', '']};
    return `<a class="md-back" href="#/counts">${svg(IC.back)}Counts</a>
      <section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Count ${esc(c.number)} · ${esc(c.store)}</h1><p class="lead">${esc(cs.join(' and '))} count blind${c.data.recounter ? `; ${esc(c.data.recounter)} recounts` : ''} · ${dmy(c.day)}</p></div>${tag(c.status, c.status === 'closed' ? 'ok' : c.status === 'recount' ? 'warn' : '')}</section>
      <section class="card"><div class="sk-tw"><table class="tb"><thead><tr><th>Item</th><th class="num">${esc(cs[0] || 'Counter 1')}</th><th class="num">${esc(cs[1] || 'Counter 2')}</th>${c.status !== 'counting' || !c.blind ? '<th class="num">Recount</th><th class="num">Book</th><th class="num">Difference</th>' : ''}<th>Result</th></tr></thead><tbody>${(c.lines || []).map(l => `<tr><td>${esc(l.item)} <span class="mut">· ${esc(l.unit)}</span></td><td class="num">${l.c1 === null ? '—' : num(l.c1)}</td><td class="num">${l.c2 === null ? '—' : num(l.c2)}</td>${c.blind ? '' : `<td class="num">${l.c3 === null || l.c3 === undefined ? '—' : num(l.c3)}</td><td class="num">${num(l.book)}</td><td class="num">${l.diff === undefined ? '—' : (l.diff > 0 ? '+' : '') + num(l.diff)}${l.pct !== undefined ? ` <span class="mut">(${num(l.pct)}%)</span>` : ''}</td>`}<td>${tag(...(res[l.result] || [l.result, '']))}${l.adjust ? ' ' + tag(l.adjust) : ''}</td></tr>`).join('')}</tbody></table></div>
        ${c.blind ? '<p class="cs-note">The book column appears only after both counters submit.</p>' : ''}</section>
      ${open && CAN() ? `<section class="card"><h2 class="sk-h">${slot ? 'Recount' : 'Enter a count'}</h2>
        ${c.status === 'recount' && !c.data.recounter ? `<form class="sk-inline" data-form="recounter" data-id="${esc(c.id)}"><input class="in" name="who" placeholder="A third person (not ${esc(cs.join(' or '))})" required><button class="btn soft sm">Name the recounter</button></form>` : `
        <form data-form="entercount" data-id="${esc(c.id)}" class="sk-grid">${slot ? `<input type="hidden" name="who" value="${esc(c.data.recounter)}">` : sel('who', 'Counter', cs.map(x => [x, x]), cs[0])}
          ${(c.lines || []).filter(l => !slot || l.result === 'recount').map(l => fld('n_' + l.item_id, `${l.item} (${l.unit})`, '', 'inputmode="decimal"')).join('')}
          <div class="wide sk-acts"><span></span><button class="btn">Submit the count</button></div></form>`}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- reconcile */
  function pReconcile() {
    const r = lazy('recon', 'reconcile', {}), rc = lazy('recov', 'docs', {kind: 'recovery'}), me = lazy('me', 'month_end', {});
    if (!r || !rc || !me) return loading();
    if (r.error) return `<section class="card">${empty(r.error)}</section>`;
    const items = r.items || [];
    const pick = items.find(i => i.item_id === ST.recItem) || items[0];
    const rows = (r.rows || []).filter(x => pick && x.item_id === pick.item_id);
    const max = Math.max(1, ...rows.map(x => Math.max(x.actual, x.theoretical * (1 + x.allowance / 100))));
    const unit = pick ? pick.unit : '';
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Reconcile</h1><p class="lead">What the work should have used, against what it did use.</p></div>
        ${items.length ? `<span class="cs-seg">${items.slice(0, 5).map(i => `<button type="button" data-rec="${esc(i.item_id)}" aria-pressed="${pick && pick.item_id === i.item_id}">${esc(i.item)}</button>`).join('')}</span>` : ''}<button class="btn soft sm" type="button" data-csv="recon">Sheet for signing</button></section>
      ${pick ? `<section class="cs-hero"><div class="top">
          <div class="k"><div class="l">Should have used</div><div class="v">${qty(pick.theoretical, unit)}</div><div class="s">work done × your QS quantities</div></div>
          <div class="k"><div class="l">Did use</div><div class="v">${qty(pick.actual, unit)}</div><div class="s">issued − returned − left at the work front</div></div>
          <div class="k low${pick.excess > 0 ? ' bad' : ''}"><div class="l">Over</div><div class="v">${pick.pct === null ? '—' : (pick.pct > 0 ? '+' : '') + num(pick.pct) + '%'}</div><div class="s">${pick.excess > 0 ? `${qty(pick.excess, unit)} beyond the allowance · ${money(pick.value)}` : 'within the allowance'}</div></div></div>
        <div class="sk-bars">${rows.map(x => { const al = x.theoretical * (1 + x.allowance / 100);
          return `<div class="sk-brow"><span class="nm">${esc(x.work)}</span><span class="tr"><span class="th" style="width:${(x.theoretical / max * 100).toFixed(1)}%"></span><span class="ac${x.excess > 0 ? ' bad' : ''}" style="width:${(x.actual / max * 100).toFixed(1)}%"></span><span class="al" style="left:${(al / max * 100).toFixed(1)}%"></span></span><span class="pc${x.excess > 0 ? ' cs-neg' : ''}">${x.pct === null ? '—' : (x.pct > 0 ? '+' : '') + num(x.pct) + '%'}</span></div>`; }).join('')}</div>
        <div class="cs-legend"><span><i class="sk-lt"></i>Should have used</span><span><i></i>Did use</span><span><i class="min"></i>Your allowance</span></div></section>` : `<section class="card">${empty('Add your QS quantities and % done on Indents to reconcile.')}</section>`}
      ${(r.rows || []).some(x => x.hints.length) ? `<section class="card"><h2 class="sk-h">What the records show</h2>${r.rows.filter(x => x.hints.length).map(x => x.hints.map(h => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1"><b>${esc(x.work)} · ${esc(x.item)}:</b> ${esc(h)}</span>${ask(`${x.work} ${x.item}`)}</div>`).join('')).join('')}</section>` : ''}
      <section class="sk-split">
        <div class="card"><h2 class="sk-h">By subcontractor (free issue)</h2>${(r.holders || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Holder</th><th>Item</th><th class="num">Should use</th><th class="num">Used</th><th class="num">Beyond allowance</th><th class="num">At contract rate</th><th></th></tr></thead><tbody>${r.holders.map(h => `<tr><td>${esc(h.holder)}</td><td>${esc(h.item)}</td><td class="num">${qty(h.theoretical, h.unit)}</td><td class="num">${qty(h.actual, h.unit)}</td><td class="num">${h.excess ? qty(h.excess, h.unit) : '—'}</td><td class="num">${h.recovery === null ? (h.excess ? '<span class="mut">no rate</span>' : '—') : money(h.recovery, 2)}</td><td>${CAN() && h.excess > 0 && h.recovery !== null ? `<button class="btn soft sm" type="button" data-recover="${esc(h.holder)}|${esc(h.item)}">Draft recovery</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No free-issue material yet.')}
          ${(rc.rows || []).length ? `<h3 class="sk-h3">Recovery drafts</h3>${rc.rows.map(d => `<div class="sk-slip"><div style="flex:1"><b>${esc(d.number)}</b> · ${esc(d.party)} · ${esc(d.data.item)} · ${money(d.data.recovery, 2)}<div class="mut sk-sub">${esc(d.data.clause || '')}</div></div>${d.status === 'draft' && CAN() ? `<form class="sk-inline" data-form="recovery" data-id="${esc(d.id)}">${who('Decided by')}<button class="btn soft sm" name="decision" value="waive">Waive</button><button class="btn soft sm" name="decision" value="sent">Send to Contracts</button><button class="btn sm" name="decision" value="deduct">Deduct</button></form>` : tag(d.status)}</div>`).join('')}` : ''}</div>
        <div class="card"><h2 class="sk-h">Month-end · ${esc(me.month || '')}</h2>
          <div class="cs-row"><span style="flex:1">Stock value (${esc({fifo: 'FIFO', wavg: 'weighted average', lifo: 'LIFO'}[(me.valuation || {}).method] || '')})</span><b>${money((me.valuation || {}).total)}</b></div>
          <div class="cs-row"><span style="flex:1">Received, not yet invoiced</span><b>${money(me.grni_value)}</b></div>
          <div class="cs-row"><span style="flex:1">Write-offs approved</span><b>${money(me.write_offs)}</b></div>
          <div class="cs-row"><span style="flex:1">Scrap sold</span><b>${money(me.scrap_sales)}</b></div>
          <div class="md-acts" style="margin-top:12px"><a class="btn soft sm" href="#/reports">Month-end report</a></div></div>
      </section>`;
  }

  /* ---------------------------------------------------------------- reports */
  function pReports() {
    const m = ST.month || '';
    const me = lazy('me:' + m, 'month_end', {month: m}), co = lazy('close', 'close_out', {});
    if (!me || !co) return loading();
    if (me.error) return `<section class="card">${empty(me.error)}</section>`;
    const v = me.valuation || {};
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Reports</h1><p class="lead">The stock statement, what came in, what was used and where, and what is left at the end of a project.</p></div>
        <form data-form="month" class="sk-inline"><input class="in" type="month" name="month" value="${esc(me.month)}"><button class="btn soft sm">Show</button></form></section>
      <section class="cs-4 grid" style="display:grid;gap:16px">${kpi('Received in ' + me.month, money(me.received))}${kpi('Stock value', money(v.total), v.note ? '' : '')}${kpi('Received, not invoiced', money(me.grni_value), pl((me.grni || []).length, 'receipt'))}${kpi('Write-offs', money(me.write_offs), me.scrap_sales ? 'scrap sold ' + money(me.scrap_sales) : '')}</section>
      <section class="sk-split">
        <div class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Stock statement</h2><button class="btn soft sm" type="button" data-csv="stock">Export</button></div>
          <div class="sk-tw"><table class="tb"><thead><tr><th>Item</th><th class="num">Quantity</th><th class="num">Unit cost</th><th class="num">Value</th></tr></thead><tbody>${(v.items || []).map(i => `<tr><td>${esc(i.item)}</td><td class="num">${qty(i.qty, i.unit)}</td><td class="num">${money(i.unit_cost, 2)}</td><td class="num">${money(i.value)}</td></tr>`).join('') || `<tr><td colspan="4">${empty('Nothing in stock.')}</td></tr>`}</tbody></table></div>
          <p class="cs-note">${esc(v.note || '')}${(v.unpriced || []).length ? ' No price yet: ' + esc(v.unpriced.join(', ')) + '.' : ''}</p></div>
        <div class="card"><h2 class="sk-h">Used by work package</h2>${(me.by_work || []).length ? me.by_work.map(w => `<div class="cs-row"><span style="flex:1">${esc(w.work)}</span><b>${money(w.value)}</b></div>`).join('') : empty('Nothing issued this month.')}
          <h3 class="sk-h3">Received, not yet invoiced</h3>${(me.grni || []).length ? me.grni.map(g => `<div class="cs-row"><span style="flex:1">${esc(g.number)} · ${esc(g.supplier)} · ${dmy(g.day)}</span><b>${money(g.value)}</b></div>`).join('') : empty('Every receipt is matched to an invoice.')}</div>
      </section>
      <section class="card"><h2 class="sk-h">Close-out</h2><p class="mut" style="margin:0 0 8px;font-size:14px">${esc(co.say || '')}</p>
        ${(co.surplus || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Store</th><th>Item</th><th>Where</th><th class="num">Quantity</th><th class="num">Value</th></tr></thead><tbody>${co.surplus.map(x => `<tr><td>${esc(x.store)}</td><td>${esc(x.item)}</td><td>${esc(x.where)}</td><td class="num">${qty(x.qty, x.unit)}</td><td class="num">${money(x.value)}</td></tr>`).join('')}</tbody></table></div>` : empty('No stock left.')}
        ${(co.holders || []).length ? `<h3 class="sk-h3">Still with subcontractors</h3>${co.holders.map(h => `<div class="cs-row"><span style="flex:1">${esc(h.holder)} · ${esc(h.item)}</span><b>${qty(h.qty, h.unit)}</b></div>`).join('')}` : ''}
        ${(co.open || []).length ? `<h3 class="sk-h3">Papers still open</h3><p class="mut" style="margin:0;font-size:14px">${esc(co.open.map(o => `${o.number} (${o.status})`).join(', '))}</p>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = SET();
    const its = ST.cache.items || [];
    const pk = s.pack || {};
    const tiers = s.tiers || [];
    return `<section><h1 class="sd-h">Settings</h1><p class="lead">Your company, your country and currency, your rules. Everything the desk works out follows these.</p></section>${ro()}
      ${CAN() ? `<section class="card"><h2 class="sk-h">Company and rules</h2><form data-form="settings" class="sk-grid three">
        ${fld('company', 'Company', s.company, 'maxlength="120"')}${fld('project', 'Project', s.project, 'maxlength="120"')}${fld('country', 'Country (2 letters)', s.country, 'maxlength="2" placeholder="AE"')}
        ${fld('currency', 'Currency (3 letters)', s.currency, 'maxlength="3"')}${sel('units', 'Units', [['metric', 'Metric'], ['imperial', 'Imperial']], s.units)}${sel('gaap', 'Your accounts follow', [['ifrs', 'IFRS'], ['usgaap', 'US GAAP'], ['local', 'Local rules']], s.gaap)}
        ${sel('valuation', 'Stock value', [['wavg', 'Weighted average'], ['fifo', 'FIFO'], ['lifo', 'LIFO (US GAAP only)']], s.valuation)}${fld('receive_tol', 'Delivery tolerance %', s.receive_tol, 'inputmode="decimal"')}${fld('tolerance', 'Count tolerance %', s.tolerance, 'inputmode="decimal"')}
        ${fld('wastage', 'Wastage allowance %', s.wastage, 'inputmode="decimal"')}${fld('lead_days', 'Supplier lead time (days)', s.lead_days, 'inputmode="numeric"')}${fld('service_z', 'Safety factor (1.65 ≈ 95% of days)', s.service_z, 'inputmode="decimal"')}
        ${fld('stale_days', 'Not moving after (days)', s.stale_days, 'inputmode="numeric"')}${fld('transit_days', 'Chase a transfer after (days)', s.transit_days, 'inputmode="numeric"')}${fld('hold_days', 'Chase a quality hold after (days)', s.hold_days, 'inputmode="numeric"')}
        <div class="wide sk-sub2">Who approves an adjustment or a scrap, by value</div>
        ${[0, 1, 2].map(i => `${fld('tier_lim_' + i, i < 2 ? `Up to (${s.currency})` : 'Anything above', i < 2 ? (tiers[i] || [])[0] ?? '' : 'above', i < 2 ? 'inputmode="decimal"' : 'readonly')}${fld('tier_who_' + i, 'Approved by', (tiers[i] || [])[1] || '', 'maxlength="60"')}`).join('').replace(/<\/label><label/g, '</label><label')}
        <div class="wide sk-sub2">Count plan (days between counts)</div>
        ${fld('cd_A', 'Class A', (s.count_days || {}).A, 'inputmode="numeric"')}${fld('cd_B', 'Class B', (s.count_days || {}).B, 'inputmode="numeric"')}${fld('cd_C', 'Class C', (s.count_days || {}).C, 'inputmode="numeric"')}
        <div class="wide sk-acts"><span></span><button class="btn">Save</button></div></form></section>` : ''}
      <section class="sk-split">
        <div class="card"><h2 class="sk-h">Stores</h2>${(K().stores || []).map(st => `<div class="cs-row"><span style="flex:1">${esc(st.name)} <span class="mut">· ${esc(st.kind)}${st.project ? ' · ' + esc(st.project) : ''}</span></span></div>`).join('') || empty('No stores yet.')}
          ${CAN() ? `<form data-form="store" class="sk-grid">${fld('name', 'Name', '', 'required maxlength="80" placeholder="Yard 2"')}${sel('kind', 'Kind', [['main', 'Main store'], ['yard', 'Yard'], ['sub', 'Sub-store'], ['container', 'Container']], 'main')}${fld('project', 'Project', '', 'maxlength="120"')}<div class="wide sk-acts"><span></span><button class="btn soft">Add a store</button></div></form>` : ''}</div>
        <div class="card"><h2 class="sk-h">Your country's rows${pk.country && pk.country !== '-' ? ' · ' + esc(pk.country) : ''}</h2>${[...(pk.docs || []), ...(pk.storage || [])].map(r => `<div class="cs-row"><span style="flex:1">${esc(r.need || r.rule)}<div class="mut sk-sub">${esc(r.source)}</div></span>${r.check ? tag('check this', 'warn') : ''}${CAN() ? `<label class="sk-sw"><input type="checkbox" data-packoff="${esc(r.id)}"${(s.packs_off || []).includes(r.id) ? '' : ' checked'}> on</label>` : ''}</div>`).join('') || empty('Set your country to see its rows.')}
          <p class="cs-note">${esc(pk.note || '')}</p></div>
      </section>
      <section class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Items</h2>${tag(pl(its.length, 'item'))}</div>
        ${its.length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Item</th><th>Unit</th><th>Other units</th><th>Traced</th><th class="num">Min</th><th class="num">Price</th></tr></thead><tbody>${its.map(i => `<tr class="sk-click" data-go="stock/${esc(i.id)}"><td>${esc(i.name)}${i.code ? ' <span class="mut">· ' + esc(i.code) + '</span>' : ''}</td><td>${esc(i.unit)}</td><td class="mut">${esc(Object.entries(i.conv || {}).map(([u, n]) => `1 ${u} = ${n}`).join(', ') || '—')}</td><td>${i.trace === 'none' ? '—' : tag(i.trace)}${i.inspect ? ' ' + tag('inspect', 'warn') : ''}</td><td class="num">${num(i.min_qty)}</td><td class="num">${money(i.price, 2)}</td></tr>`).join('')}</tbody></table></div>` : empty('No items yet.')}
        ${CAN() ? `<details class="sk-more"${its.length ? '' : ' open'}><summary>Add an item</summary><form data-form="item" class="sk-grid three">${fld('name', 'Name', '', 'required maxlength="120" placeholder="Cement CEM I 42.5N"')}${fld('unit', 'Base unit', '', 'required maxlength="12" placeholder="bag, kg, t, m3, no"')}${fld('conv', 'Other units', '', 'placeholder="t=20; pallet=60"')}
            ${sel('category', 'Kind', [['bulk', 'Bulk material'], ['consumable', 'Consumable'], ['tool', 'Returnable tool'], ['client', 'Client-supplied']], 'bulk')}${sel('trace', 'Traced by', [['none', 'Nothing'], ['batch', 'Batch'], ['heat', 'Heat number + certificate'], ['serial', 'Serial']], 'none')}${sel('inspect', 'On arrival', [['', 'Straight to stock'], ['1', 'Quality hold first']], '')}
            ${fld('min_qty', 'Minimum', '', 'inputmode="decimal"')}${fld('price', `Price per base unit (${s.currency})`, '', 'inputmode="decimal"')}${fld('shelf_days', 'Shelf life (days)', '', 'inputmode="numeric"')}
            ${fld('mass_per_m', 'Bar mass (kg/m, your standard)', '', 'inputmode="decimal"')}${fld('mass_src', 'Where that mass comes from', '', 'maxlength="200"')}${fld('max_minutes', 'Ready-mix limit (minutes)', '', 'inputmode="numeric"')}
            <div class="wide sk-acts"><span></span><button class="btn soft">Add the item</button></div></form>
          <form data-form="importitems" class="sk-grid">${area('text', 'Or paste your item list (CSV)', 'name,unit,code,category,min,price,trace,conv\nCement CEM I 42.5N,bag,CEM42,bulk,1000,18,none,t=20', 4)}<div class="wide sk-acts"><span></span><button class="btn soft">Import</button></div></form></details>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- actions */
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { b.dataset.sure = ''; if (b.dataset.was) b.textContent = b.dataset.was; }, 4000); return false; }
  function saveBlob(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
  const csvCell = v => { const s = S(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  function csv(name, head, rows) { saveBlob(name, new Blob([[head, ...rows].map(r => r.map(csvCell).join(',')).join('\n')], {type: 'text/csv'})); }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const ch = t.closest('[data-chart]'); if (ch) { ST.chartItem = ch.dataset.chart; showPage(true); return; }
    const rc = t.closest('[data-rec]'); if (rc) { ST.recItem = rc.dataset.rec; showPage(true); return; }
    const sb = t.closest('[data-store]'); if (sb) { ST.store = sb.dataset.store; showPage(true); return; }
    const ob = t.closest('[data-only]'); if (ob) { ST.only = ob.dataset.only; showPage(true); return; }
    const cv = t.closest('[data-csv]');
    if (cv) {
      const k = cv.dataset.csv;
      if (k === 'ledger') { const d = ST.cache['item:' + ST.arg]; if (d) csv(`ledger-${d.name}.csv`, ['when', 'movement', 'lot', 'from', 'to', 'for', 'quantity', 'unit', 'by', 'approver'], (d.ledger || []).map(m => [m.at, m.kind, m.lot, m.from, m.to, m.work, m.qty, m.unit, m.who, m.approver])); }
      if (k === 'stock') { const v = (ST.cache['me:' + (ST.month || '')] || {}).valuation || {}; csv('stock-statement.csv', ['item', 'quantity', 'unit', 'unit cost', 'value', 'currency'], (v.items || []).map(i => [i.item, i.qty, i.unit, i.unit_cost, i.value, v.currency])); }
      if (k === 'recon') { const r = ST.cache.recon || {}; csv('reconciliation.csv', ['work', 'item', 'unit', 'should have used', 'issued', 'unused', 'did use', 'variance %', 'allowance %', 'beyond allowance', 'value', 'signed by'], (r.rows || []).map(x => [x.work, x.item, x.unit, x.theoretical, x.issued, x.unused, x.actual, x.pct, x.allowance, x.excess, x.value, ''])); }
      return;
    }
    const rv = t.closest('[data-recover]');
    if (rv) {
      const [h, it] = rv.dataset.recover.split('|'); rv.disabled = true;
      try { const r = await run('draft_recovery', {holder: h, item: it}); await changed(r.say); } catch (err) { toast(err.message, true); rv.disabled = false; }
    }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.photo && el.files && el.files[0]) { addFiles([el.files[0]]); el.value = ''; setTimeout(() => send('Read this delivery paper and draft the receipt.'), 900); return; }
    if (el.dataset.packoff !== undefined) {
      const off = new Set(SET().packs_off || []); if (el.checked) off.delete(el.dataset.packoff); else off.add(el.dataset.packoff);
      try { await run('save_settings', {packs_off: [...off]}); await changed('Saved.'); } catch (err) { toast(err.message, true); }
    }
  }
  const val = (f, n) => S((f.querySelector(`[name="${n}"]`) || {}).value).trim();   // not f.elements[n]: 'item' is the collection's own method
  function lines(txt, keys) { return S(txt).split('\n').map(l => l.trim()).filter(l => l && !/^item\b/i.test(l)).map(l => { const p = l.split(',').map(x => x.trim()); const o = {}; keys.forEach((k, i) => { if (p[i]) o[k] = p[i]; }); return o; }); }
  async function onSubmit(e) {
    const f = e.target; if (!f.dataset || !f.dataset.form) return;
    e.preventDefault();
    const kind = f.dataset.form, id = f.dataset.id, btn = e.submitter || f.querySelector('button');
    const choice = e.submitter && e.submitter.name ? e.submitter.value : '';
    if (kind === 'search') { ST.q = val(f, 'q'); showPage(true); return; }
    if (kind === 'month') { ST.month = val(f, 'month'); showPage(true); return; }
    const call = async (part, a, msg) => { if (btn) btn.disabled = true; try { const r = await run(part, a); await changed((r && r.say) || msg || 'Done.'); return r; } catch (err) { toast(err.message, true); if (btn) btn.disabled = false; return null; } };
    if (kind === 'receipt') {
      const ls = lines(val(f, 'text'), ['item', 'qty', 'unit', 'lot', 'cert']).map(x => ({...x, doc_qty: x.qty}));
      if (!ls.length) { toast('Add at least one line: item, quantity.', true); return; }
      const r = await call('draft_receipt', {supplier: val(f, 'supplier'), doc_no: val(f, 'doc_no'), po: val(f, 'po'), store: val(f, 'store'), lines: ls});
      if (r) location.hash = '#/receive/' + r.id;
      return;
    }
    if (kind === 'recount') {
      const d = ST.cache['doc:' + id]; if (!d) return;
      const ls = d.lines.map((l, i) => { const s = {...(l.src || {})}; for (const k of ['qty', 'gross', 'tare', 'damaged', 'cert']) { const v = val(f, k + '_' + i); if (v !== '') s[k] = v; else if (k !== 'qty') delete s[k]; } if (s.gross && s.tare && !val(f, 'qty_' + i)) delete s.qty; return s; });
      delete ST.cache['doc:' + id];
      await call('draft_receipt', {id, supplier: d.party, doc_no: d.data.doc_no, po: d.data.po, store: d.store_id, vehicle: d.data.vehicle, lines: ls}, 'Checked again.');
      return;
    }
    if (kind === 'confirm') { delete ST.cache['doc:' + id];
      if (choice === 'reject') { const why = prompt('Why is the delivery rejected?'); if (!why) return; await call('reject_receipt', {id, who: val(f, 'who'), reason: why}); }
      else await call('confirm_receipt', {id, who: val(f, 'who')});
      return; }
    if (kind === 'invoiced') { delete ST.cache['doc:' + id]; await call('invoiced', {id, invoice: val(f, 'invoice')}); return; }
    if (kind === 'quality') { await call('quality', {lot: id, decision: choice, who: val(f, 'who'), cert: val(f, 'cert')}); return; }
    if (kind === 'return') { await call('return_vendor', {lot: id, who: val(f, 'who'), reason: val(f, 'reason')}); return; }
    if (kind === 'reverse') { delete ST.cache['item:' + ST.arg]; await call('reverse', {id, who: val(f, 'who'), reason: val(f, 'reason')}); return; }
    if (kind === 'slip') {
      const a = {type: val(f, 'type'), item: val(f, 'item'), qty: val(f, 'qty'), unit: val(f, 'unit'), work: val(f, 'work'), holder: val(f, 'holder'), person: val(f, 'person'),
        from_holder: val(f, 'from_holder'), store: val(f, 'store'), to_store: val(f, 'to_store')};
      if (a.type !== 'transfer') delete a.to_store; if (a.type !== 'return') delete a.from_holder;
      await call('draft_slip', a); return;
    }
    if (kind === 'confirmslip') { await call(choice === 'cancel' ? 'cancel_slip' : 'confirm_slip', {id, who: val(f, 'who')}); return; }
    if (kind === 'rcvtransfer') { await call('receive_transfer', {id, who: val(f, 'who'), qty: val(f, 'qty') || undefined}); return; }
    if (kind === 'holder') { const a = {name: val(f, 'name'), allowance: val(f, 'allowance'), uplift: val(f, 'uplift'), clause: val(f, 'clause')};
      if (val(f, 'rate_item') && val(f, 'rate')) a.rates = {[val(f, 'rate_item')]: val(f, 'rate')}; await call('save_holder', a); return; }
    if (kind === 'indent') { await call('decide_indent', {id, decision: choice, who: val(f, 'who')}); return; }
    if (kind === 'newindent') { await call('draft_indent', {item: val(f, 'item'), qty: val(f, 'qty'), work: val(f, 'work'), need_by: val(f, 'need_by'), by: val(f, 'by')}); return; }
    if (kind === 'po') { await call('save_po', {number: val(f, 'number'), supplier: val(f, 'supplier'), due: val(f, 'due'), lines: lines(val(f, 'lines'), ['item', 'qty', 'unit', 'rate'])}); return; }
    if (kind === 'budgets') { await call('import_budgets', {text: val(f, 'text')}); return; }
    if (kind === 'progress') { await call('progress', {work: val(f, 'work'), done: val(f, 'done')}); return; }
    if (kind === 'opencount') { const r = await call('open_count', {store: val(f, 'store'), counters: [val(f, 'c1'), val(f, 'c2')]}); if (r) location.hash = '#/counts/' + r.id; return; }
    if (kind === 'entercount') { const counts = {}; [...f.elements].forEach(el => { if (el.name && el.name.startsWith('n_') && el.value !== '') counts[el.name.slice(2)] = el.value; });
      delete ST.cache['doc:' + id]; await call('enter_count', {id, who: val(f, 'who'), counts}); return; }
    if (kind === 'recounter') { delete ST.cache['doc:' + id]; await call('recounter', {id, who: val(f, 'who')}); return; }
    if (kind === 'adjust') { await call('approve_adjust', {id, decision: choice, who: val(f, 'who'), role: val(f, 'role'), reason: val(f, 'reason')}); return; }
    if (kind === 'recovery') { await call('decide_recovery', {id, decision: choice, who: val(f, 'who')}); return; }
    if (kind === 'store') { await call('save_store', {name: val(f, 'name'), kind: val(f, 'kind'), project: val(f, 'project')}); return; }
    if (kind === 'item') {
      const conv = {}; val(f, 'conv').split(/[;,]/).forEach(p => { const [u, n] = p.split('='); if (u && n) conv[u.trim()] = n.trim(); });
      const a = {name: val(f, 'name'), unit: val(f, 'unit'), category: val(f, 'category'), trace: val(f, 'trace'), inspect: !!val(f, 'inspect'), conv};
      for (const k of ['min_qty', 'price', 'shelf_days', 'mass_per_m', 'mass_src', 'max_minutes']) if (val(f, k) !== '') a[k] = val(f, k);
      await call('save_item', a); return;
    }
    if (kind === 'importitems') { await call('import_items', {text: val(f, 'text')}); return; }
    if (kind === 'settings') {
      const a = {};
      for (const k of ['company', 'project', 'country', 'currency', 'units', 'gaap', 'valuation', 'receive_tol', 'tolerance', 'wastage', 'lead_days', 'service_z', 'stale_days', 'transit_days', 'hold_days']) a[k] = val(f, k);
      a.tiers = [0, 1, 2].map(i => [i < 2 ? (val(f, 'tier_lim_' + i) || null) : null, val(f, 'tier_who_' + i)]).filter(t => t[1]);
      a.count_days = {A: val(f, 'cd_A'), B: val(f, 'cd_B'), C: val(f, 'cd_C')};
      await call('save_settings', a, 'Settings saved.'); return;
    }
  }

  /* ---------------------------------------------------------------- files into the chat */
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
    const box = $('#stFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/stdesk/chat'); ST.chat = r.id; }
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
      const askR = async () => { const seq = ST.seq; let r = null;
        try { r = await api('GET', `/api/conversations/${enc(chat)}/result`); } catch {}
        if (seq === ST.seq) ST.res = r; };
      if (!first && (ST.sending || ST.working || lastIsHers() || (ST.res && ST.res.needs_you))) await askR();
      let rows;
      try { rows = (await api('GET', `/api/conversations/${enc(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== ST.chat) return;
      merge(rows);
      if (first && lastIsHers()) await askR();
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
    if (ST.working && !working) changed();      // a turn ended: a draft it made shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { setTimeout(() => send(text), 800); return; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'st' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
