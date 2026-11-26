/* INVESTMENTS DESK - the Investments & Wealth employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE
   INVESTMENTS DESK"). A thin top bar, then the Investments chat (its own conversation, kind 'investments') beside the desk's pages: Today,
   Portfolio, Gains & tax lots, Plans, Options & futures, Scam check, Fund NAV, Settings. The pages call /api/investments/do/<part>, which
   runs the F10 engine on her portfolio. Hoola never places an order and never says what to buy or sell. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', inv: '<path d="M4 19V5M4 19h16"/><path d="M7 15l4-4 3 3 5-6"/><path d="M15 8h4v4"/>',
    scale: '<path d="M12 4v16M5 8h14M8 20h8"/><path d="M5 8l-3 6a3 3 0 0 0 6 0zM19 8l-3 6a3 3 0 0 0 6 0z"/>',
    pulse: '<path d="M3 12h4l2-6 4 12 2-6h6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['portfolio', 'Portfolio'], ['gains', 'Gains & tax lots'], ['plans', 'Plans'], ['derivatives', 'Options & futures'],
    ['scam', 'Scam check'], ['funds', 'Fund NAV'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'How did my portfolio do?', 'What did I realise this tax year?'],
    portfolio: ['Is anything too big a share?', 'How far am I from my target mix?', 'Which losses could I realise?'],
    gains: ['Explain how my sales were matched', 'Why does a loss not count yet?', 'What goes on my tax return?'],
    plans: ['What do my fees cost me?', 'How long does my pot last?', 'What if inflation is higher?'],
    derivatives: ['What is the most I can lose?', 'Explain the break-even', 'What does a 1% move do?'],
    scam: ['Is this offer a scam?', 'How do I check a firm is registered?', 'What are the common signs?'],
    funds: ['Why is there a NAV break?', 'What tolerance should I use?', 'Explain this NAV'],
    settings: ['Which method does my country use?', 'What is a sensible limit for one holding?', 'How does the buy-back rule work?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], gn: null, rk: null, out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.investments.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.investments.folded') === '1'; } catch {}

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
  const run = (part, a) => api('POST', '/api/investments/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/investments/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.inv, '')}</div>
        <h1 class="sd-h">Your Investments employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="ivHire">Hire Investments &amp; Wealth</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#ivHire').onclick = async () => { try { await api('POST', '/api/employees/investments_desk/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.inv, '')}</div>
          <div style="min-width:0"><div class="sd-name">Investments</div><div class="sd-site" id="ivSite"></div></div>
          <span id="ivState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="ivBiz" aria-label="Portfolio" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Investments chat">
          <div class="sd-chathead"><div class="t"><b>Investments chat</b><span>Ask about a holding, a sale or a plan - or drop your broker's file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="ivFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="ivPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Investments desk" id="sdTabs"></nav>
          <div id="ivPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the numbers. It never places an order or says what to buy or sell.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your investments…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#ivPick').click()});
    $('#ivPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.investments.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.investments.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/investments/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#ivBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/investments/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#ivPage').addEventListener('click', onPageClick);
    $('#ivPage').addEventListener('submit', onSubmit);
    $('#ivPage').addEventListener('change', onChange);
    $('#ivPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function clearCache() { ST.gn = null; ST.rk = null; }
  function stateLine() {
    const d = ST.d, el = $('#ivState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your portfolio'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#ivSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No portfolio yet';
    const sel = $('#ivBiz');
    sel.innerHTML = (d.portfolios || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.portfolios || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), p = k.portfolio || {};
    const n = ok ? {portfolio: ((p.over_your_limit || []).length + (p.no_price || []).length) || '', gains: (k.gains || {}).error ? '!' : '',
      derivatives: ((k.risk || {}).soon || []).length || '', funds: (k.funds || []).slice(0, 5).filter(f => f.break).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/investments/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#ivPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, portfolio: pPortfolio, gains: pGains, plans: pPlans, derivatives: pDerivatives, scam: pScam, funds: pFunds,
      settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    if (typeof html === 'string') box.innerHTML = html;
    if (kept) retype(box, kept);
    tgSum();
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function tgSum() {
    const el = $('#ivTgSum'), f = el && el.closest('form'); if (!el) return;
    let s = 0, any = false; f.querySelectorAll('input').forEach(i => { if (i.value.trim() !== '') { any = true; s += Number(i.value) || 0; } });
    el.textContent = any ? `Adds up to ${Math.round(s * 10) / 10}%` : 'No target mix';
    el.className = any && Math.abs(s - 100) > 0.5 ? 'cs-neg' : 'mut'; el.style.fontSize = '13px';
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
  const ro = () => CAN() ? '' : `<p class="cs-note">You read this portfolio as ${esc(RN(ST.d.role))}. Changing it needs the owner, an accountant or an approver.</p>`;
  const sign = v => Number(v) > 0 ? 'cs-pos' : Number(v) < 0 ? 'cs-neg' : '';
  const signed = (v, dec = 2) => (Number(v) > 0 ? '+' : '') + money(v, null, dec);
  async function lazy(key, part, a) {
    if (ST[key] !== null && ST[key] !== undefined) return ST[key];
    ST[key] = false;
    try { ST[key] = await run(part, a); } catch (e) { ST[key] = {error: e.message}; }
    showPage(true);
    return ST[key];
  }
  const got = (key, part, a) => { if (ST[key] === null) { lazy(key, part, a); return null; } return ST[key] === false ? null : ST[key]; };
  function uploader(kind, title, hint) {
    if (!CAN()) return '';
    return `<form class="ins-drop" data-form="upload" data-kind="${esc(kind)}"><div class="t"><b>${esc(title)}</b><span class="mut">${esc(hint)}</span></div>
      <label class="btn soft sm">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" data-upfile="1" hidden></label></form>`;
  }

  /* ---------------------------------------------------------------- charts (drawn in SVG, no library) */
  const CLS_ORDER = ['shares', 'funds', 'bonds', 'cash', 'property', 'crypto', 'commodities', 'other'];
  function donut(alloc, total) {
    const rows = Object.entries(alloc || {}).filter(x => x[1] > 0).sort((a, b) => CLS_ORDER.indexOf(a[0]) - CLS_ORDER.indexOf(b[0]));
    if (!rows.length) return '';
    const R = 54, C = 2 * Math.PI * R; let at = 0;
    const arcs = rows.map(([k, p]) => { const len = p / 100 * C, gap = rows.length > 1 ? 2 : 0;
      const s = `<circle class="iv-seg c-${esc(k)}" r="${R}" cx="70" cy="70" stroke-dasharray="${Math.max(0, len - gap).toFixed(2)} ${(C - Math.max(0, len - gap)).toFixed(2)}" stroke-dashoffset="${(-at).toFixed(2)}"><title>${esc(cap(k))} ${p}%</title></circle>`;
      at += len; return s; }).join('');
    return `<div class="iv-donut"><svg viewBox="0 0 140 140" role="img" aria-label="Allocation by asset class"><g transform="rotate(-90 70 70)"><circle class="iv-track" r="${R}" cx="70" cy="70"/>${arcs}</g>
      <text x="70" y="66" class="iv-dl">Value</text><text x="70" y="84" class="iv-dv">${esc(short(total))}</text></svg>
      <div class="iv-dleg">${rows.map(([k, p]) => `<div><i class="c-${esc(k)}"></i><span>${esc(cap(k))}</span><b>${esc(p)}%</b></div>`).join('')}</div></div>`;
  }
  const short = v => { const n = Math.abs(Number(v) || 0), s = Number(v) < 0 ? '-' : '';
    return s + (n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(0) + 'k' : n.toLocaleString(undefined, {maximumFractionDigits: 0})); };
  function yearBars(years) {
    if (!(years || []).length) return '';
    const W = 440, H = 170, P = 24, mx = Math.max(1, ...years.map(y => Math.max(y.gains, -y.losses)));
    const mid = H / 2, bw = Math.min(46, (W - P * 2) / years.length / 2.6), step = (W - P * 2) / years.length;
    const bars = years.map((y, i) => { const x = P + step * i + step / 2, hg = y.gains / mx * (mid - 22), hl = -y.losses / mx * (mid - 22);
      return `<g><rect class="iv-g" x="${(x - bw - 2).toFixed(1)}" y="${(mid - hg).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(0, hg).toFixed(1)}" rx="4"><title>${esc(y.year)} gains ${esc(m2(y.gains))}</title></rect>
        <rect class="iv-l" x="${(x + 2).toFixed(1)}" y="${mid}" width="${bw.toFixed(1)}" height="${Math.max(0, hl).toFixed(1)}" rx="4"><title>${esc(y.year)} losses ${esc(m2(y.losses))}</title></rect>
        <text class="tx" x="${x.toFixed(1)}" y="${H - 4}" text-anchor="middle">${esc(y.year)}</text>
        <text class="iv-net ${y.net >= 0 ? 'p' : 'n'}" x="${x.toFixed(1)}" y="12" text-anchor="middle">${esc((y.net >= 0 ? '+' : '') + short(y.net))}</text></g>`; }).join('');
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Gains and losses by tax year"><line class="zero" x1="${P}" x2="${W - P}" y1="${mid}" y2="${mid}"/>${bars}</svg></div>
      <div class="cs-legend"><span><i class="in"></i>Gains</span><span><i class="out"></i>Losses</span><span>Net above each year</span></div>`;
  }
  function lines(series, opts) {
    const all = series.flatMap(s => s.pts.map(p => p[1]));
    if (!all.length) return '';
    const W = 560, H = 210, L = 46, R = 12, T = 12, B = 26, n = Math.max(...series.map(s => s.pts.length)), mx = Math.max(1, ...all), mn = Math.min(0, ...all);
    const X = i => L + (W - L - R) * (n > 1 ? i / (n - 1) : 0), Y = v => T + (H - T - B) * (1 - (v - mn) / (mx - mn || 1));
    const grid = [0, .5, 1].map(f => { const v = mn + (mx - mn) * f; return `<line class="ax" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`; }).join('');
    const xl = [0, Math.floor((n - 1) / 2), n - 1].filter((v, i, a) => a.indexOf(v) === i).map(i => `<text class="tx" x="${X(i).toFixed(1)}" y="${H - 6}" text-anchor="middle">${esc((opts && opts.xl) ? opts.xl(i) : 'year ' + (i + 1))}</text>`).join('');
    const paths = series.map(s => { const d = s.pts.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(p[1]).toFixed(1)}`).join('');
      return (s.area ? `<path class="area" d="${d}L${X(s.pts.length - 1).toFixed(1)},${Y(mn).toFixed(1)}L${X(0).toFixed(1)},${Y(mn).toFixed(1)}Z"/>` : '') + `<path class="line ${s.cls || ''}" d="${d}"/>`; }).join('');
    const mark = opts && opts.mark != null ? `<line class="min" x1="${X(opts.mark).toFixed(1)}" x2="${X(opts.mark).toFixed(1)}" y1="${T}" y2="${H - B}"/><text class="minl" x="${(X(opts.mark) + 4).toFixed(1)}" y="${T + 10}">${esc(opts.markSay || '')}</text>` : '';
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc((opts && opts.label) || 'Chart')}">${grid}${paths}${mark}${xl}</svg></div>
      <div class="cs-legend">${series.map(s => `<span><i class="${s.cls || ''}"></i>${esc(s.name)}</span>`).join('')}</div>`;
  }
  function weights(hs, lim) {
    const top = (hs || []).slice(0, 8); if (!top.length) return '';
    const mx = Math.max(lim || 0, ...top.map(h => h.weight_pct));
    return `<div class="iv-w">${top.map(h => `<div class="${h.over_limit ? 'over' : ''}"><span><b>${esc(h.symbol)}</b><em>${esc(cap(h.class))}</em></span><i><b class="c-${esc(h.class)}" style="width:${(h.weight_pct / mx * 100).toFixed(1)}%"></b>${lim ? `<u style="left:${(lim / mx * 100).toFixed(1)}%"></u>` : ''}</i><em>${esc(h.weight_pct)}%</em></div>`).join('')}</div>
      ${lim ? `<div class="cs-legend"><span><i class="min"></i>Your ${esc(lim)}% limit</span></div>` : ''}`;
  }

  /* ---------------------------------------------------------------- setup */
  function pSetup() {
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.inv, '')}</div>
      <div><h1 class="sd-h">Set up your portfolio</h1><p class="lead">Your gains worked out by tax lot the way your country does it, what you hold and how it is spread, what fees cost you over the years, and how long a pot lasts. Hoola never places an order or says what to buy or sell.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your portfolio</h2>${setupFields('ivS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then drop your broker's trades or holdings file on the desk, or into the chat.</span><button class="btn" type="submit">Set up the portfolio</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="My investments"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), p = k.portfolio || {}, g = k.gains || {}, hv = k.harvest || {};
    const yr = (g.years || []).find(y => y.year === g.this_year);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : p.total ? 'Nothing needs you on your investments right now.' : 'Add what you hold or your trades to start.';
    const hasP = p.total !== undefined && !p.empty && !p.error;
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)} ${k.method_name ? `Sales matched by ${esc(k.method_name.replace(/ \(Hoola's table.*\)$/, ''))}.` : ''}</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k"><div class="l">Portfolio value</div><div class="v">${hasP ? esc(money(p.total)) : '—'}</div><div class="s">${hasP ? (k.prices_on ? `at your prices of ${esc(dmy(k.prices_on))}` : 'at your prices') : 'no priced holdings yet'}</div></div>
        <div class="k${hasP && p.unrealised < 0 ? ' low bad' : ''}"><div class="l">Unrealised gain</div><div class="v ${hasP ? sign(p.unrealised) : ''}">${hasP ? esc(signed(p.unrealised, 0)) : '—'}</div><div class="s">${hasP && p.unrealised_pct !== null ? `${esc(p.unrealised_pct)}% on ${esc(money(p.cost))} cost` : 'needs your cost'}</div></div>
        <div class="k"><div class="l">This tax year (${esc(g.this_year || '—')})</div><div class="v ${yr ? sign(yr.net) : ''}">${yr ? esc(signed(yr.net, 0)) : '—'}</div><div class="s">${yr ? `${esc(pl(yr.sales, 'sale'))} · net realised` : 'no sales this tax year'}</div></div>
        <div class="k${hv.total ? ' low' : ''}"><div class="l">Losses you could look at</div><div class="v">${hv.total ? esc(money(Math.abs(hv.total))) : '—'}</div><div class="s">${hv.total ? `on ${esc(pl((hv.losses || []).length, 'holding'))}, not realised` : 'none'}</div></div></div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">How it is spread</h2><div class="r"><button class="btn soft sm" type="button" data-go="portfolio">Portfolio</button></div></div>
          ${hasP ? donut(p.allocation, p.total) : empty(p.error || 'Add your holdings with a price to see this.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Gains by tax year</h2><div class="r"><button class="btn soft sm" type="button" data-go="gains">Gains</button></div></div>
          ${(g.years || []).length ? yearBars(g.years) : empty(g.error || 'No sales yet. Add your trades to see your gains.')}
          ${g.disallowed_losses ? `<p class="cs-note">${esc(m2(g.disallowed_losses))} of losses do not count yet: you bought the same shares back inside the window, so they moved into the new shares' cost.</p>` : ''}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Largest holdings</h2><div class="r">${k.max_pct ? `<span class="cs-tag">limit ${esc(k.max_pct)}%</span>` : ''}</div></div>
          ${hasP ? weights(p.holdings, k.max_pct) : empty('Nothing priced yet.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- portfolio */
  function pPortfolio() {
    const k = K(), p = k.portfolio || {}, hs = k.holdings || [], hv = k.harvest || {};
    const byS = {}; (p.holdings || []).forEach(h => { byS[h.symbol] = h; });
    const rows = hs.map(h => { const s = byS[h.symbol] || {}, v = s.value;
      return `<tr><td><b>${esc(h.symbol)}</b><div class="mut" style="font-size:12.5px">${esc(cap(h.asset_class || 'other'))}</div></td>
        <td class="r">${esc(num(h.qty))}</td>
        <td class="r">${CAN() ? `<input class="in sm iv-px" name="${esc(h.symbol)}" value="${esc(h.price === null || h.price === undefined ? '' : h.price)}" inputmode="decimal" aria-label="Price of ${esc(h.symbol)}" placeholder="price">` : esc(h.price === null ? '—' : m2(h.price))}</td>
        <td class="r">${v === undefined ? '<span class="cs-tag warn">no price</span>' : esc(money(v))}</td>
        <td>${s.weight_pct !== undefined ? `<div class="iv-wc"><i><b class="c-${esc(s.class)}" style="width:${Math.min(100, s.weight_pct)}%"></b></i><span${s.over_limit ? ' class="cs-neg"' : ''}>${esc(s.weight_pct)}%</span></div>` : ''}</td>
        <td class="r ${sign(s.unrealised)}">${s.unrealised === null || s.unrealised === undefined ? '—' : esc(signed(s.unrealised, 0))}</td>
        <td>${CAN() ? `<button class="ib" type="button" aria-label="Remove ${esc(h.symbol)}" data-rm="holdings" data-n="${esc(h.n)}">×</button>` : ''}</td></tr>`; }).join('');
    const drift = p.drift || [];
    return `<div><h1 class="sd-h">Portfolio</h1><p class="lead">What you hold, at the prices you give - Hoola fetches no prices. Your weights, how it is spread, what is over your limit and how far it is from your target mix.</p></div>
      ${ro()}
      <section class="cs-hero"><div class="top">
        <div class="k"><div class="l">Value</div><div class="v">${p.total ? esc(money(p.total)) : '—'}</div><div class="s">${k.prices_on ? 'prices of ' + esc(dmy(k.prices_on)) : 'no prices yet'}</div></div>
        <div class="k"><div class="l">Cost</div><div class="v">${p.cost ? esc(money(p.cost)) : '—'}</div><div class="s">what you paid, from your file or your trades</div></div>
        <div class="k"><div class="l">Unrealised</div><div class="v ${sign(p.unrealised)}">${p.total ? esc(signed(p.unrealised, 0)) : '—'}</div><div class="s">${p.unrealised_pct !== null && p.unrealised_pct !== undefined ? esc(p.unrealised_pct) + '%' : ''}</div></div>
        <div class="k${(p.over_your_limit || []).length ? ' low bad' : ''}"><div class="l">Over your limit</div><div class="v">${esc((p.over_your_limit || []).length)}</div><div class="s">${k.max_pct ? `above ${esc(k.max_pct)}% each` : 'set a limit in Settings'}</div></div></div></section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Holdings · ${esc(hs.length)}</h2><div class="r">
          ${hs.length ? `<button class="btn soft sm" type="button" data-dl="holdings">Download CSV</button>` : ''}
          ${CAN() && k.trades_count ? `<button class="btn soft sm" type="button" data-fromtrades="1">Build from my trades</button>` : ''}
          ${CAN() && hs.length ? `<button class="btn soft sm" type="button" data-rmall="holdings">Clear</button>` : ''}</div></div>
        ${hs.length ? `<form data-form="prices" id="ivPrices"><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Holding</th><th class="r">Quantity</th><th class="r">Price</th><th class="r">Value</th><th>Weight</th><th class="r">Unrealised</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
          ${CAN() ? `<div class="md-acts"><label class="mut iv-pon">Prices as of <input class="in sm" type="date" name="prices_on" value="${esc(new Date().toISOString().slice(0, 10))}" aria-label="Prices as of"></label><button class="btn" type="submit">Save the prices</button></div>` : ''}</form>`
          : empty('No holdings yet. Upload your broker\'s holdings file, add them one by one, or build them from your trades.')}
        ${uploader('holdings', 'Upload holdings', 'Columns: symbol, quantity, price, cost, asset class - replaces the list')}
        ${CAN() ? `<form data-form="hold" class="cr-grid iv-add"><input class="in" name="symbol" placeholder="Symbol" required maxlength="40" aria-label="Symbol"><input class="in" name="qty" placeholder="Quantity" required inputmode="decimal" aria-label="Quantity"><input class="in" name="price" placeholder="Price" required inputmode="decimal" aria-label="Price">
          <input class="in" name="cost" placeholder="Cost (optional)" inputmode="decimal" aria-label="Total cost"><select class="in" name="asset_class" aria-label="Asset class">${(k.classes || []).map(c => `<option value="${esc(c)}">${esc(cap(c))}</option>`).join('')}</select><button class="btn soft" type="submit">Add or update</button></form>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Against your target mix</h2>${drift.length ? `<div class="iv-drift">${drift.map(d => `<div><span>${esc(cap(d.class))}</span><i><b class="c-${esc(d.class)}" style="width:${Math.min(100, d.now)}%"></b><u style="left:${Math.min(100, d.target)}%"></u></i><em class="${Math.abs(d.off) >= 5 ? 'cs-neg' : ''}">${esc(d.now)}% <span class="mut">/ ${esc(d.target)}%</span></em></div>`).join('')}</div>
          <p class="cs-note">The line is your target. A gap is a fact to look at, not an instruction to trade.</p>` : empty('Set your target mix in Settings to see how far you are from it.')}</section>
        <section class="card"><h2 class="md-h2">Losses you could realise</h2><p class="mut" style="margin:0 0 6px;font-size:14px">Holdings worth less than you paid. Buying the same thing back inside your country's window may stop the loss counting.</p>
          ${err(hv)}${(hv.losses || []).map(x => `<div class="cs-row" style="align-items:flex-start"><span style="flex:1"><b>${esc(x.symbol)}</b><div class="mut" style="font-size:12.5px">${esc(x.warning || '')}</div></span><span class="cs-neg">${esc(m2(x.unrealised_loss))}</span></div>`).join('') || empty(hv.empty ? 'Needs holdings with a price and a cost.' : 'No holding is below what you paid.')}
          ${(hv.losses || []).length ? `<p class="cs-note">A list to look at, not a plan to sell. Hoola never places an order.</p>` : ''}</section></div>`;
  }

  /* ---------------------------------------------------------------- gains */
  function pGains() {
    const k = K(), g = got('gn', 'gains'), tr = k.trades || [];
    const ds = (g && g.disposals) || [];
    return `<div><h1 class="sd-h">Gains &amp; tax lots</h1><p class="lead">Every sale matched to the shares it came from, the way ${esc(k.country || 'your country')} does it, grouped by tax year. The tax on the gains is not worked out - it needs your rate and allowances.</p></div>
      ${ro()}
      <section class="card iv-meth"><div class="ico">${svg(IC.scale, '')}</div><div style="flex:1;min-width:0"><b>${esc(cap(k.method_name) || 'No matching method yet')}</b>
        <div class="mut" style="font-size:13px">Tax year: ${esc(k.tax_year_is || '')}${k.rule_days !== null && k.rule_days !== undefined ? ` · your ${esc(k.rule_days)}-day rule` : ''}</div>${k.method_note ? `<div class="cs-neg" style="font-size:13px">${esc(k.method_note)}</div>` : ''}</div>
        <button class="btn soft sm" type="button" data-go="settings">Change</button></section>
      ${g && !g.empty && !g.error ? `<div class="iv-kpis">${kpi('Gains', esc(m2(g.gains)), `${esc(pl(ds.filter(d => d.gain >= 0).length, 'sale'))}`, 'cs-pos')}${kpi('Losses', esc(m2(g.losses)), `${esc(pl(ds.filter(d => d.gain < 0).length, 'sale'))}`, 'cs-neg')}${kpi('Net', esc(signed(g.net)), 'all years', sign(g.net))}${kpi('Losses not allowed now', esc(m2(g.disallowed_losses)), 'moved into the shares bought back', g.disallowed_losses ? 'warn' : '')}</div>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">By tax year</h2><div class="r">${g && !g.empty && !g.error ? `<button class="btn soft sm" type="button" data-dl="gains">Download for your tax return</button>` : ''}</div></div>
          ${!g ? loading() : g.empty ? empty('No trades yet.') : g.error ? err(g) : `${yearBars(g.years)}<table class="tb" style="margin-top:12px"><thead><tr><th>Tax year</th><th class="r">Sales</th><th class="r">Gains</th><th class="r">Losses</th><th class="r">Net</th></tr></thead><tbody>
            ${g.years.map(y => `<tr${y.year === g.this_year ? ' class="iv-now"' : ''}><td><b>${esc(y.year)}</b>${y.year === g.this_year ? '<span class="cs-tag">now</span>' : ''}</td><td class="r">${esc(y.sales)}</td><td class="r cs-pos">${esc(m2(y.gains))}</td><td class="r cs-neg">${esc(m2(y.losses))}</td><td class="r ${sign(y.net)}"><b>${esc(signed(y.net))}</b></td></tr>`).join('')}</tbody></table>
            ${Object.keys(g.by_term || {}).length ? `<div class="iv-terms">${Object.entries(g.by_term).map(([t, v]) => `<span><b>${esc(cap(t))} term</b> ${esc(signed(v))}</span>`).join('')}</div>` : ''}`}</section>
        <section class="card"><h2 class="md-h2">Your trades · ${esc(k.trades_count || 0)}</h2>
          ${uploader('trades', 'Upload trades', 'Your broker\'s export: date, buy or sell, symbol, quantity, price, fees. Lines already on the desk are skipped.')}
          ${CAN() ? `<form data-form="trade" class="cr-grid iv-add"><input class="in" type="date" name="date" required aria-label="Date"><select class="in" name="side" aria-label="Buy or sell"><option value="buy">Buy</option><option value="sell">Sell</option></select><input class="in" name="symbol" placeholder="Symbol" required maxlength="40" aria-label="Symbol">
            <input class="in" name="qty" placeholder="Quantity" required inputmode="decimal" aria-label="Quantity"><input class="in" name="price" placeholder="Price" required inputmode="decimal" aria-label="Price"><input class="in" name="fees" placeholder="Fees" inputmode="decimal" aria-label="Fees"><button class="btn soft wide" type="submit">Add the trade</button></form>` : ''}
          ${tr.length ? `<div class="iv-trades">${tr.slice(0, 60).map(t => `<div class="cs-row"><span class="iv-side ${esc(t.side)}">${esc(t.side === 'buy' ? 'Buy' : 'Sell')}</span><span style="flex:1;min-width:0"><b>${esc(t.symbol)}</b> <span class="mut">${esc(num(t.qty))} at ${esc(m2(t.price))}${t.fees ? ' + ' + esc(m2(t.fees)) + ' fees' : ''}</span></span><span class="mut nw">${esc(dmy(t.date))}</span>${CAN() ? `<button class="ib" type="button" aria-label="Remove this trade" data-rm="trades" data-n="${esc(t.n)}">×</button>` : ''}</div>`).join('')}</div>
            ${tr.length > 60 ? `<p class="mut" style="font-size:13px">Showing the latest 60 of ${esc(k.trades_count)}.</p>` : ''}${CAN() ? `<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-rmall="trades">Clear all trades</button></div>` : ''}` : ''}</section></div>
      ${ds.length ? `<section class="card"><h2 class="md-h2">Each sale · ${esc(ds.length)}</h2><div class="iv-sales">${ds.slice().reverse().map(d => `<details class="iv-sale" data-key="${esc(d.symbol + d.date + d.qty)}"${ST.open.has(d.symbol + d.date + d.qty) ? ' open' : ''}><summary><span class="iv-ty">${esc(d.tax_year)}</span><b>${esc(d.symbol)}</b><span class="mut">${esc(num(d.qty))} sold ${esc(dmy(d.date))}</span>${d.disallowed ? '<span class="cs-tag warn">loss waits</span>' : ''}<span class="r ${sign(d.gain)}">${esc(signed(d.gain))}</span></summary>
          <div class="iv-parts"><div class="mut" style="font-size:13px">Proceeds ${esc(m2(d.proceeds))} − cost ${esc(m2(d.cost))}${d.disallowed ? ` + ${esc(m2(d.disallowed))} loss not allowed now` : ''}${d.average_cost ? ` · average cost ${esc(m2(d.average_cost))} a share` : ''}</div>
          ${(d.parts || []).map(p => `<div class="iv-part"><span>${esc(num(p.qty))} ${p.rule ? `<em>${esc(p.rule)}</em>` : ''}${p.acquired ? ` bought ${esc(dmy(p.acquired))}` : ''}${p.days_held !== undefined ? ` · held ${esc(p.days_held)} days` : ''}${p.term ? ` · <b>${esc(p.term)} term</b>` : ''}</span><span class="${sign(p.gain)}">${esc(signed(p.gain))}</span></div>`).join('')}</div></details>`).join('')}</div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- plans */
  function pPlans() {
    const k = K(), a = k.assume || {}, fp = k.fee_plan || {}, rp = k.retire_plan || {}, fo = ST.out.fees, rt = ST.out.retire, tot = (k.portfolio || {}).total;
    const fChart = fo && fo.years ? lines([{name: 'Without fees', cls: 'wi', pts: fo.years.map(y => [y.year, y.without_fees])}, {name: 'With your fees', area: true, pts: fo.years.map(y => [y.year, y.with_fees])}], {label: 'Growth with and without fees', xl: i => 'year ' + fo.years[i].year}) : '';
    const rChart = rt && rt.years ? lines([{name: 'Left in the pot', area: true, pts: rt.years.map(y => [y.year, y.left])}, {name: 'Taken out that year', cls: 'wi', pts: rt.years.map(y => [y.year, y.withdrawn])}],
      {label: 'Retirement pot by year', xl: i => 'year ' + rt.years[i].year, mark: rt.runs_out_in_year ? rt.years.length - 1 : null, markSay: rt.runs_out_in_year ? 'runs out' : ''}) : '';
    return `<div><h1 class="sd-h">Plans</h1><p class="lead">What fees cost you over the years and how long a pot lasts - at the return and inflation YOU assume. Hoola never assumes one; real returns go up and down.</p></div>
      ${ro()}
      <form class="card iv-assume" data-form="assume"><div class="ico">${svg(IC.pulse, '')}</div><div style="flex:1;min-width:0"><b>Your assumptions</b><div class="mut" style="font-size:13px">Used by both plans below until you change them.</div></div>
        <label class="ins-lab">Yearly return %<input class="in sm" name="return_pct" value="${esc(a.return_pct ?? '')}" inputmode="decimal" placeholder="e.g. 5"></label>
        <label class="ins-lab">Inflation %<input class="in sm" name="inflation_pct" value="${esc(a.inflation_pct ?? '')}" inputmode="decimal" placeholder="e.g. 2.5"></label>${CAN() ? '<button class="btn soft" type="submit">Save</button>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What fees cost you</h2>
          <form data-form="plan" data-which="fees"><div class="cr-grid">
            <label class="ins-lab">Amount<input class="in" name="amount" value="${esc(fp.amount ?? '')}" inputmode="decimal" placeholder="${tot ? esc(Math.round(tot)) + ' (your portfolio)' : 'amount'}"></label>
            <label class="ins-lab">Years<input class="in" name="years" value="${esc(fp.years ?? 20)}" inputmode="numeric"></label>
            <label class="ins-lab">Fund fee % a year<input class="in" name="fee_pct" value="${esc(fp.fee_pct ?? '')}" inputmode="decimal" placeholder="0.2"></label>
            <label class="ins-lab">Platform fee % a year<input class="in" name="platform_pct" value="${esc(fp.platform_pct ?? '')}" inputmode="decimal" placeholder="0.25"></label>
            <label class="ins-lab">Entry charge %<input class="in" name="entry_pct" value="${esc(fp.entry_pct ?? '')}" inputmode="decimal" placeholder="0"></label></div>
            <div class="md-acts"><span class="mut" style="font-size:13px">${a.return_pct !== undefined ? `At ${esc(a.return_pct)}% a year, yours.` : 'Give your yearly return above first.'}</span><button class="btn" type="submit">Work it out</button></div></form>
          ${fo ? `<div class="fm-out">${err(fo)}${fo.years ? `<div class="iv-kpis s3">${kpi('Fees cost you', esc(money(fo.fees_cost)), `over ${esc(fo.years.length)} years`, 'cs-neg')}${kpi('Share of growth lost', esc(fo.share_lost_pct) + '%', 'of the end value without fees')}${kpi('You end with', esc(money(fo.end_with_fees)), 'instead of ' + money(fo.end_without_fees))}</div>${fChart}` : ''}</div>` : ''}</section>
        <section class="card"><h2 class="md-h2">How long a pot lasts</h2>
          <form data-form="plan" data-which="retire"><div class="cr-grid">
            <label class="ins-lab">Pot<input class="in" name="pot" value="${esc(rp.pot ?? '')}" inputmode="decimal" placeholder="${tot ? esc(Math.round(tot)) + ' (your portfolio)' : 'pot'}"></label>
            <label class="ins-lab">Taken out a year<input class="in" name="withdraw" value="${esc(rp.withdraw ?? '')}" inputmode="decimal" required placeholder="e.g. 20000"></label>
            <label class="ins-lab">Years to show<input class="in" name="years" value="${esc(rp.years ?? 40)}" inputmode="numeric"></label></div>
            <div class="md-acts"><span class="mut" style="font-size:13px">The amount taken out rises with your inflation each year.</span><button class="btn" type="submit">Work it out</button></div></form>
          ${rt ? `<div class="fm-out">${err(rt)}${rt.years ? `<div class="iv-kpis s3">${kpi('Runs out', rt.runs_out_in_year ? 'in year ' + esc(rt.runs_out_in_year) : 'does not', rt.runs_out_in_year ? '' : `in ${rt.years.length} years`, rt.runs_out_in_year ? 'cs-neg' : 'cs-pos')}${kpi('Left at the end', esc(money(rt.left_at_end)), '')}${kpi('Taken out in all', esc(money(rt.years.reduce((s, y) => s + y.withdrawn, 0))), '')}</div>${rChart}<p class="cs-note">${esc(rt.assumed || '')}</p>` : ''}</div>` : ''}</section></div>`;
  }

  /* ---------------------------------------------------------------- options & futures */
  function pDerivatives() {
    const k = K(), rk = got('rk', 'risk'), ps = (rk && rk.positions) || [], st = rk && rk.your_results;
    const lose = x => esc(typeof x.most_you_can_lose === 'string' ? cap(x.most_you_can_lose) : m2(x.most_you_can_lose));
    return `<div><h1 class="sd-h">Options &amp; futures</h1><p class="lead">The reality check on each position: the most you can lose, the most you can gain, the break-even, and what a 1% move does. No view on the market.</p></div>
      ${ro()}
      <section class="card"><h2 class="md-h2">Your positions · ${esc(ps.length)}</h2>${!rk ? loading() : err(rk)}
        <div class="iv-pos">${ps.map(x => `<div class="iv-p ${x.type === 'future' || typeof x.most_you_can_lose === 'string' ? 'risk' : ''}"><div class="h"><span class="iv-side ${x.side === 'long' ? 'buy' : 'sell'}">${esc(cap(x.side))}</span><b>${esc(x.symbol || '')} ${esc(cap(x.type))}</b>${x.strike ? `<span class="mut">strike ${esc(num(x.strike))}</span>` : ''}${x.days_left !== undefined ? `<span class="cs-tag ${x.days_left <= 14 ? 'warn' : ''}">${x.days_left < 0 ? 'expired' : esc(x.days_left) + ' days left'}</span>` : ''}
            ${CAN() ? `<button class="ib" type="button" aria-label="Remove this position" data-rm="positions" data-n="${esc(x.n)}" style="margin-left:auto">×</button>` : ''}</div>
          <div class="iv-pf">${x.type === 'future' ? `<div><span>Notional</span><b>${esc(m2(x.notional))}</b></div><div><span>A 1% move</span><b>${esc(m2(x.per_1pct_move))}</b></div>${x.leverage ? `<div><span>Leverage</span><b>${esc(x.leverage)}×</b></div><div><span>Move that wipes the margin</span><b class="cs-neg">${esc(x.move_that_wipes_the_margin_pct)}%</b></div>` : ''}`
            : `<div><span>Break-even</span><b>${esc(m2(x.break_even))}</b></div><div><span>Most you can gain</span><b class="cs-pos">${esc(typeof x.most_you_can_gain === 'string' ? cap(x.most_you_can_gain) : m2(x.most_you_can_gain))}</b></div>`}
            <div class="lose"><span>Most you can lose</span><b>${lose(x)}</b></div></div><p class="cs-note" style="margin:8px 0 0">${esc(x.says || '')}</p></div>`).join('') || (rk ? empty('No positions yet.') : '')}</div>
        ${CAN() ? `<form data-form="position" class="iv-pform"><div class="cr-sub" style="margin:18px 0 8px">Add a position</div><div class="iv-grid">
          <label class="ins-lab">Type<select class="in" name="type"><option value="call">Call option</option><option value="put">Put option</option><option value="future">Future</option></select></label>
          <label class="ins-lab">Side<select class="in" name="side"><option value="long">Long (bought)</option><option value="short">Short (sold)</option></select></label>
          <label class="ins-lab">Symbol<input class="in" name="symbol" maxlength="40" placeholder="ACME"></label>
          <label class="ins-lab opt">Strike<input class="in" name="strike" inputmode="decimal"></label>
          <label class="ins-lab opt">Premium a unit<input class="in" name="premium" inputmode="decimal"></label>
          <label class="ins-lab fut">Price<input class="in" name="price" inputmode="decimal"></label>
          <label class="ins-lab fut">Margin paid<input class="in" name="margin" inputmode="decimal"></label>
          <label class="ins-lab">Contracts<input class="in" name="qty" value="1" inputmode="decimal"></label>
          <label class="ins-lab">Units a contract<input class="in" name="multiplier" value="1" inputmode="decimal"></label>
          <label class="ins-lab">Expiry<input class="in" type="date" name="expiry"></label></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Nothing is traded: this only works out the risk.</span><button class="btn" type="submit">Add the position</button></div></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">Your results</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Paste what each closed trade made or lost (one number a line or comma-separated) to see how often trading has lost money for you.</p>
        <form data-form="results"><textarea class="in" name="results" rows="3" style="width:100%" placeholder="120, -340, 55, -80" aria-label="Your results">${esc((k.results || []).join(', '))}</textarea>${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save my results</button></div>' : ''}</form>
        ${st ? `<div class="iv-kpis">${kpi('Trades', esc(st.trades), '')}${kpi('Losing trades', esc(st.losing) + ' · ' + esc(st.losing_pct) + '%', '', st.losing_pct >= 50 ? 'cs-neg' : '')}${kpi('Net', esc(signed(st.net)), '', sign(st.net))}</div>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- scam check */
  function pScam() {
    const k = K(), sc = ST.out.scam, lv = {high: 'bad', some: 'warn'};
    return `<div><h1 class="sd-h">Scam check</h1><p class="lead">Paste an offer you were sent. Hoola reads it for the signs of investment fraud and checks the firm against the entries you paste from your regulator's own register.</p></div>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="scam"><h2 class="md-h2">The offer</h2><div class="md-form" style="grid-template-columns:minmax(0,1fr)">
          <div class="md-field"><label for="ivC1">What they sent</label><textarea class="in" id="ivC1" name="text" rows="6" placeholder="Paste the message, the advert or the email"></textarea></div>
          <div class="md-field"><label for="ivC2">Who is offering it</label><input class="in" id="ivC2" name="firm" maxlength="120" placeholder="The firm's name"></div>
          <div class="md-field"><label for="ivC3">Entries from your regulator's register (one name a line)</label><textarea class="in" id="ivC3" name="register" rows="3" placeholder="Search the firm on the register and paste what it shows"></textarea></div></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Never pay to take your own money out.</span><button class="btn" type="submit">Check it</button></div></form>
        <section class="card"><h2 class="md-h2">What Hoola found</h2>
          ${sc ? `${err(sc)}${sc.level ? `<div class="iv-verdict ${lv[sc.level] || 'ok'}"><b>${sc.level === 'high' ? 'Many signs of fraud' : sc.level === 'some' ? 'Some signs of fraud' : 'No sign found'}</b><span>${esc(sc.says || '')}</span></div>
            ${(sc.flags || []).map(f => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">${esc(cap(f))}</span></div>`).join('')}
            <p class="cs-note">Check the firm on ${esc(sc.check_on || 'your regulator\'s register')}.</p>` : ''}` : empty('Paste an offer to check it.')}</section></div>
      ${(k.scams || []).length ? `<section class="card"><h2 class="md-h2">Offers you checked</h2>${k.scams.map(s => `<div class="cs-row" style="align-items:flex-start"><span class="cs-dot${s.level === 'high' ? ' bad' : ''}"></span><span style="flex:1;min-width:0"><b>${esc(s.firm || 'Unnamed')}</b> <span class="cs-tag ${lv[s.level] || 'ok'}">${esc(s.level)}</span>${s.on_register === false ? '<span class="cs-tag bad">not on the register</span>' : s.on_register ? '<span class="cs-tag ok">on the register</span>' : ''}<div class="mut" style="font-size:12.5px">${esc(s.excerpt)}</div></span><span class="mut nw">${esc(dt(s.on))}</span>${CAN() ? `<button class="ib" type="button" aria-label="Remove" data-rm="scams" data-n="${esc(s.n)}">×</button>` : ''}</div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- fund NAV */
  function pFunds() {
    const k = K(), fs = k.funds || [], nv = ST.out.nav;
    const byFund = {}; fs.slice().reverse().forEach(f => { (byFund[f.fund] = byFund[f.fund] || []).push(f); });
    return `<div><h1 class="sd-h">Fund NAV</h1><p class="lead">For a fund you run or administer: the NAV per unit worked out from its assets, liabilities and units, against the NAV that was reported - a break when they differ by more than your tolerance.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="nav"><h2 class="md-h2">Check a NAV</h2><div class="cr-grid">
          <label class="ins-lab wide">Fund<input class="in" name="fund" maxlength="80" placeholder="Growth Fund" value="${esc(Object.keys(byFund)[0] || '')}"></label>
          <label class="ins-lab">As of<input class="in" type="date" name="as_of" value="${esc(new Date().toISOString().slice(0, 10))}"></label>
          <label class="ins-lab">Units in issue<input class="in" name="units" required inputmode="decimal"></label>
          <label class="ins-lab">Reported NAV a unit<input class="in" name="reported_nav" inputmode="decimal"></label>
          <label class="ins-lab wide">Assets: name, value (one a line)<textarea class="in" name="assets" rows="4" required placeholder="Shares, 1000000&#10;Cash, 50000"></textarea></label>
          <label class="ins-lab wide">Liabilities: name, value (one a line)<textarea class="in" name="liabilities" rows="2" placeholder="Fees due, 10000"></textarea></label>
          <label class="ins-lab">Tolerance (basis points)<input class="in" name="tolerance_bp" value="1" inputmode="decimal"></label></div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Work out the NAV</button></div>' : ''}</form>
        <section class="card"><h2 class="md-h2">Result</h2>${nv ? `${err(nv)}${nv.nav_per_unit !== undefined ? `<div class="iv-kpis s3">${kpi('NAV a unit', esc(nv.nav_per_unit), `net assets ${money(nv.net_assets)}`)}${nv.reported !== undefined ? kpi('Reported', esc(nv.reported), `${nv.difference_bp} bp apart`, nv.break ? 'cs-neg' : 'cs-pos') : ''}${nv.reported !== undefined ? kpi('Verdict', nv.break ? 'Break' : 'Within tolerance', `tolerance ${nv.tolerance_bp} bp`, nv.break ? 'cs-neg' : 'cs-pos') : ''}</div>` : ''}` : empty('Enter the fund\'s assets, liabilities and units to check its NAV.')}</section></div>
      ${Object.keys(byFund).length ? `<section class="card"><h2 class="md-h2">History</h2>${Object.entries(byFund).map(([name, rows]) => `<div class="iv-fund"><div class="cs-head"><b>${esc(name)}</b><div class="r"><span class="mut" style="font-size:12.5px">${esc(pl(rows.length, 'check'))}</span></div></div>
          ${rows.length > 1 ? lines([{name: 'NAV a unit', area: true, pts: rows.map((r, i) => [i, r.nav_per_unit])}], {label: name + ' NAV', xl: i => dmy(rows[i].as_of)}) : ''}
          <table class="tb"><thead><tr><th>As of</th><th class="r">NAV a unit</th><th class="r">Reported</th><th class="r">Apart</th><th></th><th></th></tr></thead><tbody>${rows.slice().reverse().map(r => `<tr><td>${esc(dmy(r.as_of))}</td><td class="r">${esc(r.nav_per_unit)}</td><td class="r">${esc(r.reported ?? '—')}</td><td class="r">${r.difference_bp !== undefined && r.difference_bp !== null ? esc(r.difference_bp) + ' bp' : '—'}</td><td>${r.break ? '<span class="cs-tag bad">break</span>' : r.reported !== undefined && r.reported !== null ? '<span class="cs-tag ok">ok</span>' : ''}</td><td>${CAN() ? `<button class="ib" type="button" aria-label="Remove" data-rm="funds" data-n="${esc(r.n)}">×</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), tg = k.targets || {}, w = W();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">How your sales are matched, your limit for one holding, and the mix you aim for. Every rule Hoola brings is from its own table until you check it.</p></div>
      ${ro()}
      <form class="card" data-form="settings"><h2 class="md-h2">Matching your sales</h2><div class="md-form">
        <div class="md-field"><label for="ivT1">Country (two letters)</label><input class="in" id="ivT1" name="country" maxlength="2" value="${esc(k.country || '')}" placeholder="GB"></div>
        <div class="md-field"><label for="ivT2">Method</label><select class="in" id="ivT2" name="method"><option value="">Your country's method${k.methods && k.methods[k.country] ? ' - ' + esc(k.methods[k.country]) : ''}</option>
          ${[['fifo', 'First in, first out'], ['average', 'Average cost'], ['uk_share_id', 'UK share matching and the pool']].map(([v, n]) => `<option value="${v}"${k.method === v ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="ivT3">Buy-back window in days (blank = your country's)</label><input class="in" id="ivT3" name="rule_days" value="${esc(k.rule_days ?? '')}" inputmode="numeric"></div>
        <div class="md-field"><label for="ivT4">Limit for one holding (% of the portfolio)</label><input class="in" id="ivT4" name="max_pct" value="${esc(k.max_pct ?? '')}" inputmode="decimal" placeholder="e.g. 10"></div></div>
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">' + esc(k.tax_year_is ? 'Tax year: ' + k.tax_year_is : '') + '</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <form class="card" data-form="targets"><h2 class="md-h2">Your target mix</h2><p class="mut" style="margin:0 0 10px;font-size:14px">The share of each asset class you aim for. It should add up to 100%. Leave it all blank to have none.</p>
        <div class="iv-tg">${(k.classes || []).map(c => `<label class="ins-lab"><span><i class="iv-sw c-${esc(c)}"></i>${esc(cap(c))} %</span><input class="in" name="${esc(c)}" value="${esc(tg[c] ?? '')}" inputmode="decimal"></label>`).join('')}</div>
        ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px" id="ivTgSum"></span><button class="btn" type="submit">Save the mix</button></div>` : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Matching methods Hoola knows</h2>${Object.entries(k.methods || {}).map(([c, n]) => `<div class="cs-row"><b style="width:34px">${esc(c)}</b><span style="flex:1">${esc(n)}</span>${c === k.country ? '<span class="cs-tag">yours</span>' : ''}</div>`).join('')}<p class="cs-note">From Hoola's memory, not confirmed - check them with your tax rules.</p></section>
        <section class="card"><h2 class="md-h2">This portfolio</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind)} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}
          <details class="ins-more"><summary>Set up another portfolio</summary><form data-form="setup">${setupFields('ivN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/investments/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.csv`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    try {
      const rm = t.closest('[data-rm]'); if (rm) { await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm(`Remove all your ${ra.dataset.rmall} from the desk?`)) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
      const ft = t.closest('[data-fromtrades]'); if (ft) { if (K().holdings && K().holdings.length && !confirm('Replace your holdings with what your trades leave? Prices you gave are kept.')) return;
        const r = await run('from_trades'); await changed(`${pl(r.holdings, 'holding')} built from your trades${r.no_price.length ? ` - give a price for ${r.no_price.join(', ')}` : ''}.`); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    if (e.target.closest('form[data-form="targets"]')) tgSum();
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 8e6) { toast('Up to 8 MB.', true); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name}); fi.value = ''; await changed(r.says + ` from ${f.name}.`); }
    catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const sent = () => { form.reset(); form.querySelectorAll('select').forEach(x => { delete x.dataset.touched; }); };
    const done = async m => { sent(); await changed(m); };
    const keepOut = async (key, part, a, after) => { try { ST.out[key] = await run(part, a); if (after) await changed(after); } catch (err2) { ST.out[key] = {error: err2.message}; } showPage(true); };
    const pick = names => { const a = {}; names.forEach(n => { if (g(n) !== '') a[n] = g(n); }); return a; };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/investments/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your portfolio is set up.'); ST.rows = []; ST.drawn = false; ST.thread.clear(); await loadMsgs(true); }
      else if (kind === 'trade') { await run('trade', pick(['date', 'side', 'symbol', 'qty', 'price', 'fees'])); await done('Trade added.'); }
      else if (kind === 'hold') { await run('hold', {...pick(['symbol', 'qty', 'price', 'cost', 'asset_class']), prices_on: new Date().toISOString().slice(0, 10)}); await done('Holding saved.'); }
      else if (kind === 'prices') { const prices = {}; document.querySelectorAll('input.iv-px').forEach(i => { if (i.value.trim() !== '') prices[i.name] = i.value.trim(); });
        if (!Object.keys(prices).length) { toast('Type a price first.', true); return; }
        const r = await run('prices', {prices, prices_on: g('prices_on')}); await done(`${pl(r.updated, 'price')} saved.`); }
      else if (kind === 'position') { const a = pick(['type', 'side', 'symbol', 'strike', 'premium', 'price', 'margin', 'qty', 'multiplier', 'expiry']); await run('position', a); await done('Position added.'); }
      else if (kind === 'results') { await run('settings', {results: g('results')}); await done('Your results are saved.'); }
      else if (kind === 'assume') { await run('settings', {assume: {return_pct: g('return_pct'), inflation_pct: g('inflation_pct')}}); await changed('Your assumptions are saved.'); }
      else if (kind === 'plan') { const which = form.dataset.which;
        const a = {which, ...pick(which === 'fees' ? ['amount', 'years', 'fee_pct', 'platform_pct', 'entry_pct'] : ['pot', 'withdraw', 'years'])};
        await keepOut(which === 'fees' ? 'fees' : 'retire', 'plan', a); refreshDesk(false); }
      else if (kind === 'scam') { if (!g('text') && !g('firm')) { toast('Paste the offer or name the firm first.', true); return; }
        await keepOut('scam', 'scam', {text: g('text'), firm: g('firm'), register: g('register')}); if (!ST.out.scam.error) { sent(); await changed(''); } }
      else if (kind === 'nav') { await keepOut('nav', 'nav', pick(['fund', 'as_of', 'units', 'reported_nav', 'assets', 'liabilities', 'tolerance_bp'])); if (!ST.out.nav.error) await changed(''); }
      else if (kind === 'settings') { await run('settings', {country: g('country').toUpperCase(), method: g('method'), rule_days: g('rule_days'), max_pct: g('max_pct')}); await changed('Saved.'); }
      else if (kind === 'targets') { const targets = {}; (K().classes || []).forEach(c => { if (g(c) !== '') targets[c] = g(c); }); await run('settings', {targets}); await changed('Your target mix is saved.'); }
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
    const box = $('#ivFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/investments/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'iv' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


