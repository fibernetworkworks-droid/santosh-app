/* CASH & TREASURY DESK - the Cash & Treasury employee's own section, like Payroll and Tax (owner: "NOW LETS WORK ON NEXT EMPLOYEE CASH
   AND TRESARY ---- MAKE IT FULLY FUCTIONAL SAME AS PAYROLL SECTION. ALSO MAKE DESIGN ADVANCE AND PREMIUM SAME AS OTHER SECTIONS").
   A thin top bar, then the Cash chat (its own conversation, kind 'cash': she asks what moves her cash or drops a bank statement) beside
   the desk's pages: Today, Forecast, Spare cash, Bank fees, Currencies, Covenants, Settings. The pages call /api/cash/do/<part>, which
   runs the F5 engine on the business she picked. A covenant is tested only once a person checks it against the loan agreement;
   exchange rates are hers, with the day she gave them. Hoola moves no money and names no product. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', cash: '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M7 9v0M17 15v0"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['forecast', 'Forecast'], ['spare', 'Spare cash'], ['fees', 'Bank fees'], ['currencies', 'Currencies'],
    ['covenants', 'Covenants'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What moves my cash most?', 'When is my cash lowest?', 'Am I safe for the next 3 months?'],
    forecast: ['Why does week 6 drop?', 'What if my biggest customer pays a month late?', 'Add my tax payment'],
    spare: ['How much can I set aside?', 'How big should my buffer be?', 'How long is the cash not needed?'],
    fees: ['Which fees could I avoid?', 'What do fees cost me a year?', 'Compare my fees by month'],
    currencies: ['What happens if the euro falls 10%?', 'Which currency is my biggest risk?', 'What do I hold abroad?'],
    covenants: ['Am I close to breaking a covenant?', 'Explain my leverage covenant', 'What headroom do I have?'],
    settings: ['What should my minimum cash be?', 'Which statement lines repeat?', 'How late do my customers pay?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    fc: null, fcFor: '', open: {}, bt: null, idle: null, idleFor: '', fees: null, fx: null, fxFor: '', cov: null};
  try { ST.side = localStorage.getItem('hoola.cash.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.cash.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const F = () => K().forecast || {};
  const cur = () => F().currency || (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const short = v => { const n = Math.abs(Number(v) || 0), s = Number(v) < 0 ? '−' : '';
    return s + (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? Math.round(n / 1e3) + 'k' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : Math.round(n)); };
  const can = () => !!(ST.d && ST.d.can_write);
  const dmy = d => { try { return new Date(d + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/cash/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/cash/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.cash, '')}</div>
        <h1 class="sd-h">Your Cash & Treasury employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="csHire">Hire Cash & Treasury</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#csHire').onclick = async () => { try { await api('POST', '/api/employees/cash_treasury/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.cash, '')}</div>
          <div style="min-width:0"><div class="sd-name">Cash & Treasury</div><div class="sd-site" id="csSite"></div></div>
          <span id="csState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="csBiz" aria-label="Business" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Cash chat">
          <div class="sd-chathead"><div class="t"><b>Cash chat</b><span>Ask what moves your cash, or drop a bank statement here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="csFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="csPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Cash & Treasury desk" id="sdTabs"></nav>
          <div id="csPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out your cash figures. It moves no money.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your cash…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#csPick').click()});
    $('#csPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.cash.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.cash.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/cash/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#csBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/cash/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#csPage').addEventListener('click', onPageClick);
    $('#csPage').addEventListener('submit', onSubmit);
    $('#csPage').addEventListener('change', onChange);
    $('#csPage').addEventListener('mousemove', onChartMove);
    $('#csPage').addEventListener('mouseleave', () => { const t = $('#csTip'); if (t) t.hidden = true; }, true);
    window.addEventListener('hashchange', () => { ST.keepT = null; readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function clearCache() { ST.fc = null; ST.fcFor = ''; ST.bt = null; ST.idle = null; ST.idleFor = ''; ST.fees = null; ST.fx = null; ST.fxFor = ''; ST.cov = null; }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#csState'); if (!el) return;
    const k = K(), w = W(), f = F();
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your business'] : f.error ? ['warn', 'Needs your statements']
      : (f.under_minimum_weeks || []).length ? ['warn', 'Cash runs low'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#csSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + (d.roles[d.role] || d.role) : ''}` : 'No business yet';
    const sel = $('#csBiz');
    sel.innerHTML = (d.businesses || []).map(b => `<option value="${esc(b.id)}"${w && b.id === w.id ? ' selected' : ''}>${esc(b.name)}</option>`).join('');
    sel.hidden = (d.businesses || []).length < 2;
    void k;
  }
  function paintTabs() {
    const k = K(), cv = k.covenants || {};
    const n = {covenants: (cv.to_check || []).length + (cv.breached || []).length, currencies: ((k.fx || {}).rates_missing || []).length,
      forecast: (F().under_minimum_weeks || []).length ? '!' : ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/cash/desk'); } catch { return; }
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
    const box = $('#csPage'); if (!box) return;
    if (!W()) { box.innerHTML = noBiz(); starters(); return; }
    const fn = {today: pToday, forecast: pForecast, spare: pSpare, fees: pFees, currencies: pCurrencies, covenants: pCovenants, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    if (typeof html === 'string') { const kept = keepTyping(box).concat(ST.keepT || []); box.innerHTML = html; ST.keepT = putTyping(box, kept); }
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function noBiz() {
    return `<div><h1 class="sd-h">Set up your business first</h1><p class="lead">The Cash & Treasury desk works on the books and bank statements of a business in Books & Accounts. Make one there (name, country, currency) and import a statement, then come back.</p></div>
      <div><a class="btn" href="/console/books">Open Books & Accounts</a></div>`;
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${/overdrawn|not met/.test(x.say) ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');

  function hero(f) {
    const lo = f.lowest || {}, mn = f.minimum, bad = mn !== null && mn !== undefined && lo.closing < mn;
    return `<section class="cs-hero">
      <div class="top">
        <div class="k"><div class="l">Cash today</div><div class="v">${esc(money(f.opening))}</div><div class="s">${esc(f.opening_from || '')}${f.opening_stale ? ' · old figure' : ''}</div></div>
        <div class="cs-arrow">→</div>
        <div class="k low${bad || lo.closing < 0 ? ' bad' : ''}"><div class="l">Lowest point</div><div class="v">${esc(money(lo.closing))}</div><div class="s">week ${esc(lo.week)}${mn !== null && mn !== undefined ? ` · your minimum ${esc(money(mn))}` : ''}</div></div>
        <div class="cs-arrow">→</div>
        <div class="k"><div class="l">After ${esc((f.weeks || []).length)} weeks</div><div class="v">${esc(money(f.closing))}</div><div class="s">${esc(money(f.total_in))} in · ${esc(money(f.total_out))} out</div></div>
      </div>
      ${chart(f, null)}
    </section>`;
  }

  /* the cash chart: weekly closing as a line over in / out bars, the minimum as a dashed line, a what-if as a second line */
  function chart(f, wi) {
    const wk = f.weeks || []; if (!wk.length) return '';
    const Wd = 760, Hd = 220, L = 52, R = 12, Tp = 14, B = 28, iw = Wd - L - R, ih = Hd - Tp - B;
    const vals = wk.map(x => x.closing).concat([f.opening], wi ? (wi.weeks || []).map(x => x.closing) : [], f.minimum !== null && f.minimum !== undefined ? [f.minimum] : []);
    const flows = wk.map(x => Math.max(x.in, x.out));
    let hi = Math.max(...vals, 0), lo = Math.min(...vals, 0);
    if (hi === lo) hi = lo + 1;
    const pad = (hi - lo) * 0.08; hi += pad; if (lo < 0) lo -= pad;
    const y = v => Tp + ih - ((v - lo) / (hi - lo)) * ih;
    const step = iw / wk.length, x = i => L + step * (i + 0.5);
    const fmax = Math.max(...flows, 1), bh = v => (v / fmax) * ih * 0.32, bw = Math.max(4, Math.min(14, step * 0.28));
    const ticks = 4; let grid = '';
    for (let i = 0; i <= ticks; i++) { const v = lo + (hi - lo) * i / ticks; grid += `<line class="ax" x1="${L}" x2="${Wd - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`; }
    const base = Tp + ih;
    let bars = '';
    wk.forEach((w, i) => { bars += `<rect class="bin" x="${(x(i) - bw - 1).toFixed(1)}" y="${(base - bh(w.in)).toFixed(1)}" width="${bw}" height="${bh(w.in).toFixed(1)}" rx="2"/>`
      + `<rect class="bout" x="${(x(i) + 1).toFixed(1)}" y="${(base - bh(w.out)).toFixed(1)}" width="${bw}" height="${bh(w.out).toFixed(1)}" rx="2"/>`; });
    const pts = wk.map((w, i) => [x(i), y(w.closing)]);
    const path = 'M' + pts.map(p => p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' L');
    const area = path + ` L${pts[pts.length - 1][0].toFixed(1)} ${base} L${pts[0][0].toFixed(1)} ${base} Z`;
    const mn = f.minimum, lowW = (f.lowest || {}).week;
    const minLine = mn !== null && mn !== undefined ? `<line class="min" x1="${L}" x2="${Wd - R}" y1="${y(mn).toFixed(1)}" y2="${y(mn).toFixed(1)}"/><text class="minl" x="${L + 6}" y="${(y(mn) - 6).toFixed(1)}">Your minimum</text>` : '';
    const zero = lo < 0 ? `<line class="zero" x1="${L}" x2="${Wd - R}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"/>` : '';
    const wiPath = wi && (wi.weeks || []).length ? `<path class="line wi" d="M${wi.weeks.map((w, i) => x(i).toFixed(1) + ' ' + y(w.closing).toFixed(1)).join(' L')}"/>` : '';
    const dots = pts.map((p, i) => `<circle class="pt${mn !== null && mn !== undefined && wk[i].closing < mn ? ' under' : ''}${wk[i].week === lowW ? ' low' : ''}" cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="${wk[i].week === lowW ? 6 : 3.5}"/>`).join('');
    const labels = wk.map((w, i) => (wk.length <= 13 || i % 2 === 0) ? `<text class="tx" x="${x(i).toFixed(1)}" y="${Hd - 8}" text-anchor="middle">${esc(dmy(w.from))}</text>` : '').join('');
    const hits = wk.map((w, i) => `<rect class="hit" data-w="${i}" x="${(x(i) - step / 2).toFixed(1)}" y="${Tp}" width="${step.toFixed(1)}" height="${ih}"/>`).join('');
    return `<div class="cs-chart" data-chart="1"><svg viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Cash at the end of each week">${grid}${zero}${bars}<path class="area" d="${area}"/>${minLine}${wiPath}<path class="line" d="${path}"/>${dots}${labels}${hits}</svg>
      <div class="cs-tip" id="csTip" hidden></div></div>
      <div class="cs-legend"><span><i></i>Cash at the end of the week</span><span><i class="in"></i>Money in</span><span><i class="out"></i>Money out</span>${mn !== null && mn !== undefined ? '<span><i class="min"></i>Your minimum</span>' : ''}${wiPath ? '<span><i class="wi"></i>What if</span>' : ''}</div>`;
  }
  function onChartMove(e) {
    const h = e.target.closest && e.target.closest('.hit'); const tip = $('#csTip'); if (!tip) return;
    if (!h) { tip.hidden = true; return; }
    const f = ST.tab === 'forecast' && ST.fc && !Number(ST.arg) ? ST.fc : F(), w = (f.weeks || [])[Number(h.dataset.w)]; if (!w) return;
    const box = h.closest('.cs-chart').getBoundingClientRect(), r = h.getBoundingClientRect();
    tip.innerHTML = `<b>Week ${esc(w.week)}</b> · ${esc(dmy(w.from))} – ${esc(dmy(w.to))}<br>In ${esc(money(w.in))} · Out ${esc(money(w.out))}<br>Closing <b>${esc(money(w.closing))}</b>`;
    tip.style.left = (r.left - box.left + r.width / 2) + 'px'; tip.style.top = (e.clientY - box.top) + 'px'; tip.hidden = false;
  }

  function pToday() {
    const k = K(), f = F(), id = k.idle || {}, fe = k.fees, cv = k.covenants || {};
    if (f.error) {
      return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">Hoola needs your bank statements to see your cash.</p></div>
        <section class="md-alert">${svg(IC.info)}<div><div class="t">${esc(f.error)}</div><div class="s">Import a statement in Books & Accounts > Bank, drop one in the chat, or give today's cash in Settings.</div></div><button class="btn sm" type="button" data-go="settings">Give today's cash</button></section>
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || '<p class="mut" style="margin:0">Nothing else needs you.</p>'}</section>`;
    }
    const lo = f.lowest || {}, h3 = f.view_30_60_90 || {};
    const big = (f.weeks || []).flatMap(w => w.lines).filter(l => Math.abs(l.amount) > 0).sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount)).slice(0, 6)
      .sort((a, b) => a.day < b.day ? -1 : 1);
    const bigRows = big.map(l => `<div class="cs-row"><span class="mut" style="width:56px">${esc(dmy(l.day))}</span><span style="flex:1;min-width:0">${esc(cap(l.what))}${l.overdue ? '<span class="cs-tag bad">overdue</span>' : ''}<div class="mut" style="font-size:12px">${esc(l.source)}</div></span><span class="num ${l.amount < 0 ? 'cs-neg' : 'cs-pos'}">${esc(money(l.amount))}</span></div>`).join('');
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${(f.under_minimum_weeks || []).length ? `Your cash goes under your minimum in week ${esc(f.under_minimum_weeks[0])}.`
      : lo.closing < 0 ? `The bank goes overdrawn in week ${esc(lo.week)}.` : `Your cash stays above ${esc(money(lo.closing))} for the next ${esc((f.weeks || []).length)} weeks.`}</p></div>
      ${hero(f)}
      <div class="md-3 cs-4">
        ${kpi('In 30 days', esc(money(h3['30_days'])), 'Cash after the first month')}
        ${kpi('In 60 days', esc(money(h3['60_days'])), 'Cash after two months')}
        ${kpi('In 90 days', esc(money(h3['90_days'])), 'Cash after three months')}
        ${kpi('Spare cash', id.error ? '—' : esc(money(id.idle)), id.error ? id.error : id.idle > 0 ? `Not needed in any week, after a ${money(id.buffer)} buffer` : 'None after your buffer', id.idle > 0 ? 'ok' : '')}
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || '<p class="mut" style="margin:0">Nothing needs you right now.</p>'}</section>
        <section class="card"><h2 class="md-h2">The biggest movements</h2>${bigRows || '<p class="mut" style="margin:0">Nothing big is coming in or going out.</p>'}
          <div style="margin-top:10px"><button class="btn soft sm" type="button" data-go="forecast">See every week</button></div></section>
      </div>
      <div class="md-3">
        <section class="card"><h2 class="md-h2">Bank fees</h2>${fe && fe.total ? `<div class="cs-big">${esc(money(fe.total, cur(), 2))}</div><p class="cs-note">In ${esc(fe.months_read)} month(s) of statements · about ${esc(money(fe.a_year_at_this_rate))} a year</p>` : '<p class="mut" style="margin:0">No bank charges found in your statements.</p>'}<div style="margin-top:10px"><button class="btn soft sm" type="button" data-go="fees">Open</button></div></section>
        <section class="card"><h2 class="md-h2">Covenants</h2>${(cv.breached || []).length ? `<div class="cs-big cs-neg">${esc(cv.breached.length)} not met</div><p class="cs-note">${esc(cv.breached.join(', '))}</p>` : (cv.results || []).length ? `<div class="cs-big cs-pos">All met</div><p class="cs-note">${esc(cv.results.length)} checked on your figures</p>` : '<p class="mut" style="margin:0">No covenant checked yet.</p>'}${(cv.to_check || []).length ? `<p class="cs-note">${esc(cv.to_check.length)} waiting to be checked against your loan agreement</p>` : ''}<div style="margin-top:10px"><button class="btn soft sm" type="button" data-go="covenants">Open</button></div></section>
        <section class="card"><h2 class="md-h2">Other currencies</h2>${k.fx && k.fx.positions ? `<div class="cs-big">${esc(k.fx.positions)} currenc${k.fx.positions === 1 ? 'y' : 'ies'}</div><p class="cs-note">${(k.fx.rates_missing || []).length ? 'Give a rate for ' + esc(k.fx.rates_missing.join(', ')) : 'If all fall 10%: ' + esc(money(k.fx.total_if_all_fall, cur(), 2))}</p>` : '<p class="mut" style="margin:0">Everything is in your own currency.</p>'}<div style="margin-top:10px"><button class="btn soft sm" type="button" data-go="currencies">Open</button></div></section>
      </div>`;
  }

  const WHATIF = [[0, 'As expected'], [15, 'Customers pay 15 days later'], [30, '30 days later'], [60, '60 days later']];
  function pForecast() {
    const late = Number(ST.arg || 0) || 0;
    const key = String(late);
    if (ST.fcFor !== key) { ST.fcFor = key; ST.fc = null; run('forecast', late ? {pay_later_days: late} : {}).then(r => { ST.fc = r; if (ST.tab === 'forecast') showPage(true); }).catch(e => { ST.fc = {error: e.message}; if (ST.tab === 'forecast') showPage(true); }); }
    if (ST.bt === null) { ST.bt = false; run('backtest').then(r => { ST.bt = r; if (ST.tab === 'forecast') showPage(true); }).catch(e => { ST.bt = {error: e.message}; }); }
    const f = ST.fc, base = F();
    const seg = `<div class="cs-seg" role="group" aria-label="What if">${WHATIF.map(([d, n]) => `<button type="button" data-late="${d}" aria-pressed="${d === late}">${esc(n)}</button>`).join('')}</div>`;
    const head = `<div class="cs-head"><h1 class="sd-h">13-week cash forecast</h1><span class="r"><button class="btn soft sm" type="button" data-dl="csv">CSV</button><button class="btn sm" type="button" data-dl="pdf">Download (PDF)</button></span></div>`;
    if (!f) return head + seg + loading();
    if (f.error) return head + `<section class="md-alert">${svg(IC.info)}<div><div class="t">${esc(f.error)}</div></div></section>`;
    const mn = f.minimum;
    const rows = (f.weeks || []).map(w => {
      const under = mn !== null && mn !== undefined && w.closing < mn, open = !!ST.open[w.week];
      const lines = open ? w.lines.map(l => `<tr class="cs-lines"><td></td><td>${esc(dmy(l.day))}</td><td colspan="2">${esc(cap(l.what))}${l.overdue ? '<span class="cs-tag bad">overdue</span>' : ''}<div class="src">${esc(cap(l.source))}</div></td><td class="num ${l.amount < 0 ? 'cs-neg' : 'cs-pos'}">${esc(m2(l.amount))}</td></tr>`).join('') || '<tr class="cs-lines"><td></td><td colspan="4" class="mut">Nothing in or out this week.</td></tr>' : '';
      return `<tr class="cs-wk${under ? ' under' : ''}${open ? ' open' : ''}" data-wk="${w.week}"><td><span class="chev">›</span>${esc(w.week)}</td><td class="nw">${esc(dmy(w.from))} – ${esc(dmy(w.to))}</td><td class="num cs-pos">${w.in ? esc(money(w.in)) : '—'}</td><td class="num cs-neg">${w.out ? esc(money(-w.out)) : '—'}</td><td class="num"><b>${esc(money(w.closing))}</b>${under ? '<span class="cs-tag bad">under</span>' : ''}</td></tr>${lines}`;
    }).join('');
    const items = (K().items || []).map(x => `<div class="cs-it"><span class="mut">${esc(dmy(x.date))}</span><span>${esc(x.label)}</span><span class="num ${x.amount < 0 ? 'cs-neg' : 'cs-pos'}">${esc(money(x.amount))}</span>${can() ? `<button class="ib" type="button" aria-label="Remove ${esc(x.label)}" title="Remove" data-unitem="${esc(x.n)}">×</button>` : '<span></span>'}</div>`).join('');
    const bt = ST.bt;
    const btBox = !bt ? '<p class="mut" style="margin:0">Checking…</p>' : bt.error ? `<p class="mut" style="margin:0;font-size:14px">${esc(bt.error)}</p>` :
      `<div class="cs-big">${bt.mean_error_pct_of_spending === null ? '—' : esc(bt.mean_error_pct_of_spending) + '%'}</div><p class="cs-note">Average miss, as a share of the month's spending, on ${esc(bt.months.length)} month(s) you already lived. ${esc(bt.says)}</p>`;
    const wi = late ? f : null, chartF = late ? {...base, weeks: base.weeks, minimum: f.minimum, lowest: base.lowest} : f;
    return head + `<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span class="mut" style="font-size:13px">What if</span>${seg}</div>
      ${late ? `<section class="md-alert">${svg(IC.info)}<div><div class="t">If customers pay ${esc(late)} days later than usual</div><div class="s">${f.lowest.closing === base.lowest.closing && f.closing === base.closing ? 'No change on these figures: the money your customers owe is already overdue or lands after these 13 weeks.' : `Lowest point ${esc(money(f.lowest.closing))} in week ${esc(f.lowest.week)} (was ${esc(money(base.lowest.closing))}). After 13 weeks ${esc(money(f.closing))} (was ${esc(money(base.closing))}).`}</div></div></section>` : ''}
      <section class="card">${chart(late ? chartF : f, wi)}</section>
      <div class="cs-split">
        <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Week</th><th>Dates</th><th class="num">Money in</th><th class="num">Money out</th><th class="num">Closing</th></tr></thead>
          <tbody><tr><td></td><td class="mut">Opening</td><td></td><td></td><td class="num"><b>${esc(money(f.opening))}</b></td></tr>${rows}</tbody></table></div>
          <p class="cs-note" style="padding:0 0 12px">Tap a week to see each line and where it came from. ${esc(f.says || '')}</p></section>
        <div class="cs-side">
          <section class="card"><h2 class="md-h2">Money you expect</h2>${items || '<p class="mut" style="margin:0;font-size:14px">Add a tax payment, a loan coming in, a big order - anything your books do not know yet.</p>'}
            ${can() ? `<form data-form="item" class="cs-form"><input class="in" name="label" placeholder="What it is" required maxlength="80"><input class="in sm2" name="amount" type="number" step="0.01" min="0.01" placeholder="Amount" required>
              <select class="in sm2" name="direction"><option value="out">Going out</option><option value="in">Coming in</option></select><input class="in sm2" type="date" name="date" required><button class="btn soft sm" type="submit">Add</button></form>` : ''}</section>
          <section class="card"><h2 class="md-h2">How good is the forecast</h2>${btBox}</section>
          ${(f.other_currency_accounts || []).length ? `<section class="card"><h2 class="md-h2">Not counted</h2><p class="cs-note" style="margin:0">Accounts in other currencies: ${esc(f.other_currency_accounts.map(a => a.account + ' ' + a.currency).join(', '))}. See Currencies.</p></section>` : ''}
        </div>
      </div>`;
  }

  function pSpare() {
    const k = ST.arg || '';
    if (ST.idleFor !== k || ST.idle === null) { ST.idleFor = k; ST.idle = false; run('idle', k ? {weeks_buffer: Number(k)} : {}).then(r => { ST.idle = r; if (ST.tab === 'spare') showPage(true); }).catch(e => { ST.idle = {error: e.message}; if (ST.tab === 'spare') showPage(true); }); }
    const r = ST.idle, wb = k ? Number(k) : Number((K().settings || {}).weeks_buffer ?? 4);
    const head = `<div><h1 class="sd-h">Spare cash</h1><p class="lead">The part of your cash that was not needed in any of the next 13 weeks, after a buffer you choose.</p></div>`;
    if (!r) return head + loading();
    if (r.error) return head + `<section class="md-alert">${svg(IC.info)}<div><div class="t">${esc(r.error)}</div></div></section>`;
    const lo = r.lowest_week || {}, tot = Math.max(lo.closing, 1);
    const pb = Math.max(0, Math.min(100, 100 * r.buffer / tot)), pi = Math.max(0, Math.min(100 - pb, 100 * r.idle / tot));
    return head + `<div class="md-3 cs-4">
        ${kpi('Spare cash', esc(money(r.idle)), r.idle > 0 ? 'You could put it aside for 13 weeks' : 'None after your buffer', r.idle > 0 ? 'ok' : '')}
        ${kpi('Lowest week', esc(money(lo.closing)), 'week ' + S(lo.week))}
        ${kpi('Your buffer', esc(money(r.buffer)), r.buffer_rule)}
        ${kpi('Average a week out', esc(money(r.average_weekly_out)), 'Money going out')}
      </div>
      <section class="card"><h2 class="md-h2">At the lowest point</h2>
        <div class="md-bar" style="height:16px"><div class="unk" style="width:${pb.toFixed(1)}%"></div><div class="in" style="width:${pi.toFixed(1)}%"></div></div>
        <div class="cs-legend"><span><i class="min"></i>Buffer ${esc(money(r.buffer))}</span><span><i class="in"></i>Spare ${esc(money(r.idle))}</span></div>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px"><span class="mut" style="font-size:13px">Buffer</span>
          <div class="cs-seg" role="group" aria-label="Weeks of spending to keep">${[0, 2, 4, 8, 12].map(n => `<button type="button" data-wb="${n}" aria-pressed="${n === wb}">${n ? n + ' weeks' : 'Minimum only'}</button>`).join('')}</div></div>
        <p class="cs-note">${esc(r.says)}</p></section>
      <section class="card"><h2 class="md-h2">What to do with it is yours</h2><p style="margin:0;font-size:14px;color:var(--ink2)">Hoola does not pick a bank, an account or a product, and moves nothing. Ask in the chat how long the cash is free, or what a deposit at a rate you were offered would earn.</p>
        <div style="margin-top:12px"><button class="btn soft sm" type="button" data-ask="What would my spare cash earn at a rate I was offered?">Work it out in the chat</button></div></section>`;
  }

  function pFees() {
    if (ST.fees === null) { ST.fees = false; run('fees').then(r => { ST.fees = r; if (ST.tab === 'fees') showPage(true); }).catch(e => { ST.fees = {error: e.message}; if (ST.tab === 'fees') showPage(true); }); }
    const r = ST.fees, head = `<div><h1 class="sd-h">Bank fees</h1><p class="lead">Every bank charge found in your statements, by kind and month.</p></div>`;
    if (!r) return head + loading();
    if (r.error) return head + `<section class="card"><p style="margin:0">${esc(r.error)}</p></section>`;
    const kinds = Object.entries(r.by_kind || {}).sort((a, b) => b[1] - a[1]), mx = Math.max(1, ...kinds.map(x => x[1]));
    const months = Object.entries(r.by_month || {}), mm = Math.max(1, ...months.map(x => x[1]));
    const lines = (r.lines || []).map(l => `<tr><td>${esc(l.day)}</td><td>${esc(l.narration)}</td><td><span class="cs-tag">${esc(l.kind)}</span></td><td class="num">${esc(m2(l.amount))}</td></tr>`).join('');
    return head + `<div class="md-3 cs-4">
        ${kpi('Fees found', esc(m2(r.total)), `In ${r.months_read} month(s)`)}
        ${kpi('A year at this rate', esc(money(r.a_year_at_this_rate)), 'If nothing changes')}
        ${kpi('Kinds', esc(kinds.length), kinds.length ? cap(kinds[0][0]) + ' is the biggest' : 'None found')}
        ${kpi('Lines', esc((r.lines || []).length), 'Check each one')}
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">By kind</h2><div class="cs-bars">${kinds.map(([k, v]) => `<div class="cs-bar"><span>${esc(cap(k))}</span><div class="tr"><span style="width:${(100 * v / mx).toFixed(1)}%"></span></div><span class="num">${esc(m2(v))}</span></div>`).join('') || '<p class="mut" style="margin:0">None.</p>'}</div></section>
        <section class="card"><h2 class="md-h2">By month</h2>${months.length ? `<div class="cs-months">${months.map(([k, v]) => `<div title="${esc(k)}: ${esc(m2(v))}"><b style="height:${Math.max(4, 100 * v / mm).toFixed(0)}%"></b><span>${esc(k.slice(5))}/${esc(k.slice(2, 4))}</span></div>`).join('')}</div>` : '<p class="mut" style="margin:0">None.</p>'}</section>
      </div>
      <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Day</th><th>On your statement</th><th>Kind</th><th class="num">Amount</th></tr></thead><tbody>${lines || '<tr><td colspan="4" class="mut">No bank charges found.</td></tr>'}</tbody></table></div>
        <p class="cs-note" style="padding:0 0 12px">${esc(r.says)}</p></section>
      <div><button class="btn soft sm" type="button" data-ask="Which of my bank fees could I avoid?">Ask which fees you could avoid</button></div>`;
  }

  function pCurrencies() {
    const mv = ST.arg || '10';
    if (ST.fxFor !== mv || ST.fx === null) { ST.fxFor = mv; ST.fx = false; run('fx', {move_pct: Number(mv)}).then(r => { ST.fx = r; if (ST.tab === 'currencies') showPage(true); }).catch(e => { ST.fx = {error: e.message}; if (ST.tab === 'currencies') showPage(true); }); }
    const r = ST.fx, head = `<div><h1 class="sd-h">Money in other currencies</h1><p class="lead">What you are owed, owe and hold in other currencies, valued at the rates you give.</p></div>`;
    if (!r) return head + loading();
    if (r.error) return head + `<section class="card"><p style="margin:0">${esc(r.error)}</p></section>`;
    const bc = r.book_currency, rates = K().rates || {};
    const rows = (r.positions || []).map(p => {
      const val = p['value_in_' + bc], fall = p[`if_${p.currency}_falls_${r.move_pct}pct`] ?? Object.entries(p).find(([k2]) => k2.startsWith(`if_${p.currency}_falls`))?.[1];
      return `<tr><td><b>${esc(p.currency)}</b></td><td class="num">${esc(m2(p.owed_to_you, p.currency))}</td><td class="num">${esc(m2(p.you_owe, p.currency))}</td><td class="num">${esc(m2(p.held, p.currency))}</td><td class="num"><b>${esc(m2(p.net, p.currency))}</b></td>
        <td class="num">${p.rate !== undefined ? esc(p.rate) + (p.rate_on ? `<div class="mut" style="font-size:11.5px">${esc(p.rate_on)}${p.rate_stale ? ' · old' : ''}</div>` : '') : '<span class="cs-tag warn">give a rate</span>'}</td>
        <td class="num">${val !== undefined ? esc(m2(val, bc)) : '—'}</td><td class="num cs-neg">${fall !== undefined ? esc(m2(fall, bc)) : '—'}</td></tr>`;
    }).join('');
    const rateRows = Object.entries(rates).map(([c, g]) => `<div class="cs-it"><span><b>${esc(c)}</b></span><span>${esc(g.rate)} ${esc(bc)} for 1 ${esc(c)}</span><span class="mut" style="font-size:12.5px">${esc(g.on)}</span>${can() ? `<button class="ib" type="button" aria-label="Remove ${esc(c)}" title="Remove" data-unrate="${esc(c)}">×</button>` : '<span></span>'}</div>`).join('');
    return head + `<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span class="mut" style="font-size:13px">If a currency moves</span>
        <div class="cs-seg" role="group" aria-label="Move">${['5', '10', '20'].map(n => `<button type="button" data-mv="${n}" aria-pressed="${n === mv}">${n}%</button>`).join('')}</div>
        <span style="margin-left:auto" class="mut">If all fall ${esc(mv)}%: <b class="cs-neg">${esc(m2(r.total_if_all_fall, bc))}</b></span></div>
      ${(r.rates_missing || []).length ? `<section class="md-alert">${svg(IC.info)}<div><div class="t">Give a rate for ${esc(r.rates_missing.join(', '))}</div><div class="s">Hoola never guesses an exchange rate. Use the rate from your bank or a source you trust, with its date.</div></div></section>` : ''}
      <div class="cs-split">
        <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Currency</th><th class="num">Owed to you</th><th class="num">You owe</th><th class="num">Held</th><th class="num">Net</th><th class="num">Rate</th><th class="num">In ${esc(bc)}</th><th class="num">If it falls ${esc(mv)}%</th></tr></thead>
          <tbody>${rows || `<tr><td colspan="8" class="mut">Everything is in ${esc(bc)}.</td></tr>`}</tbody></table></div><p class="cs-note" style="padding:0 0 12px">${esc(r.says)}</p></section>
        <div class="cs-side"><section class="card"><h2 class="md-h2">Your rates</h2>${rateRows || '<p class="mut" style="margin:0;font-size:14px">No rates yet.</p>'}
          ${can() ? `<form data-form="rate" class="cs-form"><input class="in sm2" name="currency" placeholder="EUR" required maxlength="3" style="text-transform:uppercase"><input class="in sm2" name="rate" type="number" step="0.000001" min="0.000001" placeholder="${esc(bc)} for 1" required><input class="in sm2" type="date" name="on"><button class="btn soft sm" type="submit">Save</button></form>` : ''}</section></div>
      </div>`;
  }

  function pCovenants() {
    if (ST.cov === null) { ST.cov = false; run('covenants').then(r => { ST.cov = r; if (ST.tab === 'covenants') showPage(true); }).catch(e => { ST.cov = {error: e.message}; if (ST.tab === 'covenants') showPage(true); }); }
    const r = ST.cov, head = `<div><h1 class="sd-h">Loan covenants</h1><p class="lead">The tests in your loan agreement, checked on your own figures. A covenant is tested only once a person checks it against the agreement.</p></div>`;
    if (!r) return head + loading();
    if (r.error && !r.covenants) return head + `<section class="card"><p style="margin:0">${esc(r.error)}</p></section>`;
    const res = {}; (r.results || []).forEach(x => { res[x.name] = x; });
    const cards = (r.covenants || []).map(c => {
      const x = res[c.name];
      let gauge = '', state = '';
      if (!c.checked) state = can() ? `<button class="btn sm" type="button" data-cvcheck="${esc(c.name)}">I checked it against the agreement</button>` : '<span class="cs-tag warn">check this</span>';
      else if (!x) state = '<span class="cs-tag">checked</span>';
      else if (x.ok === null) state = `<span class="cs-tag warn">${esc(x.says)}</span>`;
      else {
        state = x.ok ? `<span class="cs-tag ok">Met · headroom ${esc(x.headroom)}</span>` : `<span class="cs-tag bad">Not met · short by ${esc(Math.abs(x.headroom))}</span>`;
        const lim = Number(c.limit), act = Number(x.actual), top = Math.max(lim, act) * 1.25 || 1;
        gauge = `<div class="gauge" title="Actual ${esc(act)} · limit ${esc(lim)}"><span class="${x.ok ? '' : 'bad'}" style="width:${Math.min(100, 100 * act / top).toFixed(1)}%"></span><i style="left:${Math.min(100, 100 * lim / top).toFixed(1)}%"></i></div>
          <div class="mut" style="font-size:12.5px">Actual <b>${esc(c.kind === 'min_cash' ? money(act) : act)}</b> · limit ${esc(c.kind === 'min_cash' ? money(lim) : lim)}${x.from ? ' · ' + esc(x.from) : ''}</div>`;
      }
      return `<div class="cs-cov"><div class="t"><div style="flex:1;min-width:0"><b>${esc(c.name)}</b><div class="mut" style="font-size:13px">${esc(c.test)}</div></div>${can() ? `<button class="ib" type="button" aria-label="Remove ${esc(c.name)}" title="Remove" data-uncov="${esc(c.name)}">×</button>` : ''}</div>
        ${gauge}<div>${state}</div>${c.checked ? `<div class="mut" style="font-size:12px">Checked ${esc(S(c.checked_on).slice(0, 10))} by ${esc(S(c.checked_by).replace(/ <.*/, ''))}</div>` : ''}</div>`;
    }).join('');
    const figs = Object.entries(r.figures || {}).map(([n, g]) => `<div class="cs-it"><span><b>${esc(n)}</b></span><span class="num">${esc(g.value.toLocaleString())}</span><span class="mut" style="font-size:12.5px">${esc(g.as_of)}</span>${can() ? `<button class="ib" type="button" aria-label="Remove ${esc(n)}" title="Remove" data-unfig="${esc(n)}">×</button>` : '<span></span>'}</div>`).join('');
    const need = [...new Set((r.covenants || []).filter(c => c.kind !== 'min_cash').flatMap(c => [c.numerator, c.denominator]))].filter(n => !(r.figures || {})[n]);
    return head + `${(r.breached || []).length ? `<section class="md-alert" style="border-color:var(--bads);background:var(--bads);color:var(--badt)">${svg(IC.info)}<div><div class="t">Not met on these figures: ${esc(r.breached.join(', '))}</div><div class="s">Talk to your lender before the test date. Your lender's own calculation decides.</div></div></section>` : ''}
      <div class="cs-covs">${cards || '<section class="card"><p class="mut" style="margin:0">No covenants yet. Add the tests from your loan agreement.</p></section>'}</div>
      <div class="md-2" style="align-items:start">
        ${can() ? `<form class="card" data-form="cov"><h2 class="md-h2">Add a covenant</h2>
          <div class="md-form"><div class="md-field wide"><label for="csCn">Name in your agreement</label><input class="in" id="csCn" name="name" required maxlength="80" placeholder="Leverage"></div>
            <div class="md-field"><label for="csCk">Test</label><select class="in" id="csCk" name="kind"><option value="max_ratio">A ratio at most</option><option value="min_ratio">A ratio at least</option><option value="min_cash">Cash at least</option></select></div>
            <div class="md-field"><label for="csCl">Limit</label><input class="in" id="csCl" name="limit" type="number" step="0.01" required placeholder="3"></div>
            <div class="md-field"><label for="csCa">Figure on top</label><input class="in" id="csCa" name="numerator" placeholder="net_debt"></div>
            <div class="md-field"><label for="csCb">Divided by</label><input class="in" id="csCb" name="denominator" placeholder="ebitda"></div></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Copy it from the agreement. It is tested once you tap “I checked it”.</span><button class="btn" type="submit">Add</button></div></form>` : ''}
        <section class="card"><h2 class="md-h2">Your figures</h2>${figs || '<p class="mut" style="margin:0;font-size:14px">The figures your ratios divide, as of a date (from your accounts or your accountant).</p>'}
          ${need.length ? `<p class="cs-note">Still needed: ${esc(need.join(', '))}</p>` : ''}
          ${can() ? `<form data-form="fig" class="cs-form"><input class="in sm2" name="name" placeholder="net_debt" required maxlength="40" list="csFigs"><datalist id="csFigs">${need.map(n => `<option value="${esc(n)}">`).join('')}</datalist><input class="in sm2" name="value" type="number" step="0.01" placeholder="Value" required><input class="in sm2" type="date" name="as_of"><button class="btn soft sm" type="submit">Save</button></form>` : ''}
          <p class="cs-note">${esc(r.says || 'A cash covenant uses the lowest week of your forecast unless you give a cash figure.')}</p></section>
      </div>`;
  }

  function pSettings() {
    const k = K(), s = k.settings || {}, op = k.opening, ro = can() ? '' : ' disabled';
    return `<div class="md-2" style="align-items:start">
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <h1 class="sd-h">Cash in the bank today</h1>
        <form class="card" data-form="opening"><p class="mut" style="margin:0 0 12px;font-size:14px">${op ? `You said ${esc(money(op.amount, cur(), 2))} on ${esc(op.as_of)}.` : 'Hoola uses the balance of your imported statements. If they are behind, give today\'s figure from your bank.'}</p>
          <div class="md-form"><div class="md-field"><label for="csOa">Cash in all ${esc(cur())} accounts</label><input class="in" id="csOa" name="amount" type="number" step="0.01" value="${esc(op ? op.amount : '')}"${ro}></div>
            <div class="md-field"><label for="csOd">On</label><input class="in" id="csOd" type="date" name="as_of" value="${esc(op ? op.as_of : new Date().toISOString().slice(0, 10))}"${ro}></div></div>
          ${can() ? `<div class="md-acts">${op ? '<button class="btn soft sm" type="button" data-clearop="1">Use my statements again</button>' : '<span></span>'}<button class="btn" type="submit">Save</button></div>` : ''}</form>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
        <h1 class="sd-h">Settings</h1>
        <form class="card" data-form="settings">
          <div class="md-form">
            <div class="md-field"><label for="csMc">Least cash you want in the bank</label><input class="in" id="csMc" name="min_cash" type="number" step="0.01" min="0" value="${esc(s.min_cash ?? '')}" placeholder="Not set"${ro}></div>
            <div class="md-field"><label for="csLg">How many days late customers usually pay</label><input class="in" id="csLg" name="lag_days" type="number" min="0" max="365" value="${esc(s.lag_days ?? 0)}"${ro}></div>
            <div class="md-field"><label for="csWb">Weeks of spending to keep as a buffer</label><input class="in" id="csWb" name="weeks_buffer" type="number" min="0" max="52" value="${esc(s.weeks_buffer ?? 4)}"${ro}></div>
            <div class="md-field wide"><label for="csEx">Statement words to leave out of repeating items (a one-off)</label><input class="in" id="csEx" name="exclude" value="${esc((s.exclude || []).join(', '))}" placeholder="refund, insurance claim"${ro}></div>
          </div>
          ${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Your own figures. Hoola does not guess them.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <section class="card"><h2 class="md-h2">Where the forecast comes from</h2>
          <div class="cs-row"><span style="flex:1">Your open invoices, on their due date${s.lag_days ? ` + ${esc(s.lag_days)} days` : ''}</span><span class="mut">Books & Accounts</span></div>
          <div class="cs-row"><span style="flex:1">Your open bills, on their due date</span><span class="mut">Books & Accounts</span></div>
          <div class="cs-row"><span style="flex:1">Your last payroll, on your pay day</span><span class="mut">Payroll</span></div>
          <div class="cs-row"><span style="flex:1">What repeats in your last 3 months of statements</span><span class="mut">Your bank</span></div>
          <div class="cs-row"><span style="flex:1">Money you expect, that you added</span><span class="mut">Forecast page</span></div></section>
      </div></div>`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function download(what) {
    const late = ST.tab === 'forecast' ? Number(ST.arg || 0) || 0 : 0;
    try {
      const r = await fetch(`/api/cash/download?workspace=${enc(W().id)}&what=${enc(what)}${late ? '&pay_later_days=' + late : ''}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `cash-${what}`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  async function onPageClick(e) {
    const t = e.target;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const lt = t.closest('[data-late]'); if (lt) { location.hash = '#/forecast' + (Number(lt.dataset.late) ? '/' + lt.dataset.late : ''); return; }
    const wb = t.closest('[data-wb]'); if (wb) { location.hash = '#/spare/' + wb.dataset.wb; return; }
    const mv = t.closest('[data-mv]'); if (mv) { location.hash = '#/currencies/' + mv.dataset.mv; return; }
    const wk = t.closest('[data-wk]'); if (wk) { const n = wk.dataset.wk; ST.open[n] = !ST.open[n]; showPage(true); return; }
    try {
      const ui = t.closest('[data-unitem]'); if (ui) { await run('remove_item', {n: Number(ui.dataset.unitem)}); await changed('Removed.'); return; }
      const ur = t.closest('[data-unrate]'); if (ur) { await run('rate', {currency: ur.dataset.unrate, rate: null}); await changed('Removed.'); return; }
      const uf = t.closest('[data-unfig]'); if (uf) { await run('figure', {name: uf.dataset.unfig, value: null}); await changed('Removed.'); return; }
      const uc = t.closest('[data-uncov]'); if (uc) { if (!confirm(`Remove the covenant ${uc.dataset.uncov}?`)) return; await run('remove_covenant', {name: uc.dataset.uncov}); await changed('Removed.'); return; }
      const ck = t.closest('[data-cvcheck]'); if (ck) { await run('check_covenant', {name: ck.dataset.cvcheck}); await changed('Marked as checked by you.'); return; }
      if (t.closest('[data-clearop]')) { await run('opening', {amount: null}); await changed('Using your statements again.'); return; }
    } catch (err) { toast(err.message, true); }
  }
  function onChange() {}
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return; form.dataset.sent = Date.now();
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = form.querySelector('[type=submit]');
    const g = n => S(fd.get(n)).trim();
    if (btn) btn.disabled = true;
    try {
      if (kind === 'item') { await run('add_item', {label: g('label'), amount: Number(g('amount')), direction: g('direction'), date: g('date')}); await changed('Added to the forecast.'); }
      else if (kind === 'rate') { await run('rate', {currency: g('currency'), rate: Number(g('rate')), on: g('on') || undefined}); await changed('Rate saved.'); }
      else if (kind === 'fig') { await run('figure', {name: g('name'), value: Number(g('value')), as_of: g('as_of') || undefined}); await changed('Saved.'); }
      else if (kind === 'cov') { await run('set_covenant', {name: g('name'), kind: g('kind'), limit: Number(g('limit')), numerator: g('numerator'), denominator: g('denominator')}); await changed('Added. Check it against your agreement before it is tested.'); }
      else if (kind === 'opening') { await run('opening', {amount: g('amount') === '' ? null : Number(g('amount')), as_of: g('as_of')}); await changed('Saved.'); }
      else if (kind === 'settings') {
        const a = {lag_days: Number(g('lag_days') || 0), weeks_buffer: Number(g('weeks_buffer') || 0), exclude: g('exclude')};
        if (g('min_cash') !== '') a.min_cash = Number(g('min_cash'));
        await run('settings', a); await changed('Saved.');
      }
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
    const box = $('#csFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/cash/chat'); ST.chat = r.id; }
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
    if (!text && ready.length) text = ready.length > 1 ? 'Read these statements' : 'Read this file';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'cs' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
