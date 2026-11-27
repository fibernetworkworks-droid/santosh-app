/* MARKETS DESK - the Markets & Post-Trade employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE
   MARKETS DESK"). A thin top bar, then the Markets chat (its own conversation, kind 'markets') beside the desk's pages: Today,
   Reconciliation, Trades & settlement, Corporate actions, Tax reclaims, Margin, Best execution, Instructions, Comparables & calendar,
   Settings. The pages call /api/markets/do/<part>, which runs the F10 engine on her desk. Hoola never places, cancels or affirms a trade and
   sends nothing to anyone. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', mkt: '<path d="M4 7h16M4 12h10M4 17h7"/><path d="M15 15l2 2 4-4"/><circle cx="19" cy="7" r="1.6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['recon', 'Reconcile'], ['settle', 'Settlement'], ['actions', 'Corporate actions'],
    ['reclaims', 'Reclaims'], ['margin', 'Margin'], ['bestex', 'Execution'], ['ssi', 'Instructions'], ['research', 'Comps & IR'],
    ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Summarise the breaks', 'What is failing to settle?'],
    recon: ['Why does this position break?', 'Which breaks are oldest?', 'Draft a query to the custodian'],
    settle: ['Which trades are not confirmed?', 'What do the fails cost?', 'Draft a chaser to the counterparty'],
    actions: ['Explain this corporate action', 'What happens to the fractions?', 'Should I take up the rights?'],
    reclaims: ['How do I file this reclaim?', 'Which claims are due soon?', 'Why is nothing reclaimable?'],
    margin: ['Explain this margin call', 'What if the haircut rises?', 'Draft the call email'],
    bestex: ['Which executions cost the most?', 'Is my slippage normal?', 'Explain basis points'],
    ssi: ['Why is this instruction flagged?', 'How do I confirm a change?', 'What is a valid BIC?'],
    research: ['Explain the multiples', 'What is due next?', 'Which peers stand out?'],
    settings: ['What penalty rate does my market use?', 'Where do I find treaty rates?', 'What haircuts are usual?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.markets.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.markets.folded') === '1'; } catch {}

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
  const run = (part, a) => api('POST', '/api/markets/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/markets/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.mkt, '')}</div>
        <h1 class="sd-h">Your Markets &amp; Post-Trade employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="mkHire">Hire Markets &amp; Post-Trade</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#mkHire').onclick = async () => { try { await api('POST', '/api/employees/markets_desk/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.mkt, '')}</div>
          <div style="min-width:0"><div class="sd-name">Markets</div><div class="sd-site" id="mkSite"></div></div>
          <span id="mkState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="mkBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Markets chat">
          <div class="sd-chathead"><div class="t"><b>Markets chat</b><span>Ask about a break, a fail or a corporate action - or drop a custodian file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mkFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mkPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Markets desk" id="sdTabs"></nav>
          <div id="mkPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the post-trade numbers. It never places, cancels or affirms a trade.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your positions and trades…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mkPick').click()});
    $('#mkPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.markets.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.markets.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/markets/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#mkBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/markets/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#mkPage').addEventListener('click', onPageClick);
    $('#mkPage').addEventListener('submit', onSubmit);
    $('#mkPage').addEventListener('change', onChange);
    $('#mkPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#mkState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#mkSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#mkBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), rc = k.recon || {}, cf = k.confirm || {}, fl = k.fails || {}, rl = k.reclaims || {}, sx = k.ssi || {}, bx = k.best_ex || {};
    const L = (o, f) => (!o.empty && !o.error) ? f(o) : 0;
    const n = ok ? {recon: L(rc, o => o.breaks.length + o.cash_breaks.length) || '', settle: (L(cf, o => o.breaks.length + o.confirms_with_no_trade.length) + L(fl, o => o.fails.length)) || '',
      reclaims: L(rl, o => o.soon.length) || '', ssi: L(sx, o => o.bad) || '', bestex: L(bx, o => o.over.length) || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/markets/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#mkPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, recon: pRecon, settle: pSettle, actions: pActions, reclaims: pReclaims, margin: pMargin, bestex: pBestex, ssi: pSsi,
      research: pResearch, settings: pSettings}[ST.tab] || pToday;
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
      t === 'side' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>`
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
  function slipChart(ex, lim) {   /* diverging bars: a cost to the right of the benchmark, better than it to the left */
    const rows = ex.slice(0, 12); if (!rows.length) return '';
    const W = 760, rowH = 30, LB = 170, H = rows.length * rowH + 30, x0 = LB + 70, x1 = W - 70, mid = (x0 + x1) / 2, half = (x1 - x0) / 2;
    const mx = Math.max(1, lim || 0, ...rows.map(r => Math.abs(r.slippage_bp)));
    const bs = rows.map((r, i) => { const w = Math.abs(r.slippage_bp) / mx * half, y = 8 + i * rowH, pos = r.slippage_bp >= 0;
      const cls = pos ? (lim !== null && lim !== undefined && r.slippage_bp > lim ? 'mk-worse' : 'mk-cost') : 'mk-gain';
      return `<g><text class="tx lb" x="0" y="${y + 13}">${esc(r.id)}${r.symbol ? ' · ' + esc(r.symbol) : ''}</text>
        <rect class="${cls}" x="${(pos ? mid : mid - w).toFixed(1)}" y="${y}" width="${Math.max(1.5, w).toFixed(1)}" height="18" rx="4"><title>${esc(r.id)} ${esc(r.slippage_bp)} bp</title></rect>
        <text class="tx" x="${(pos ? mid + w + 6 : mid - w - 6).toFixed(1)}" y="${y + 13}" text-anchor="${pos ? 'start' : 'end'}">${esc(sgn(r.slippage_bp))} bp</text></g>`; }).join('');
    const lx = lim ? mid + lim / mx * half : null;
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Slippage against the benchmark"><line class="zero" x1="${mid}" x2="${mid}" y1="2" y2="${H - 22}"/>${bs}
      <text class="tx" x="${mid}" y="${H - 6}" text-anchor="middle">benchmark</text>
      ${lx ? `<line class="min" x1="${lx.toFixed(1)}" x2="${lx.toFixed(1)}" y1="2" y2="${H - 22}"/><text class="minl" x="${(lx + 4).toFixed(1)}" y="${H - 6}">your ${esc(lim)} bp</text>` : ''}</svg></div>
      <div class="cs-legend"><span><i class="mk-gain-i"></i>Better than the benchmark</span><span><i class="mk-cost-i"></i>A cost</span>${lim ? '<span><i class="min"></i>Your limit</span>' : ''}</div>`;
  }
  function rangeBar(name, r, cur) {
    if (!r) return '';
    const lo = r.low, hi = r.high, md = r.median, span = (hi - lo) || 1, p = v => ((v - lo) / span * 100).toFixed(1);
    return `<div class="mk-range"><div class="h"><b>${esc(name)}</b><span class="mut">${esc(m0(lo))} – ${esc(m0(hi))}</span></div>
      <div class="bar"><i style="left:0;right:0"></i><u style="left:${p(md)}%" title="median"></u></div>
      <div class="ft"><span>low</span><span>median <b>${esc(m0(md))}</b></span><span>high</span></div></div>`;
  }
  function timeline(items) {
    if (!items.length) return '';
    return `<ol class="mk-tl">${items.map(x => `<li class="${x.days_left <= 7 ? 'bad' : x.days_left <= 30 ? 'soon' : ''}"><span class="d"><b>${esc(dmy(x.due))}</b><em>${x.days_left === 0 ? 'today' : x.days_left < 0 ? Math.abs(x.days_left) + ' days ago' : 'in ' + pl(x.days_left, 'day')}</em></span><span class="w">${esc(x.what)}<em>period to ${esc(dmy(x.period_end))}</em></span></li>`).join('')}</ol>`;
  }
  const m0 = v => money(v, null, 0);

  /* ---------------------------------------------------------------- setup */
  function pSetup() {
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.mkt, '')}</div>
      <div><h1 class="sd-h">Set up your markets desk</h1><p class="lead">Your books reconciled against the custodian's file, trades matched to confirmations, settlement fails with their cost, corporate actions applied to every account, withholding tax you can reclaim and by when, margin calls, best execution and your disclosure calendar. Hoola never places, cancels or affirms a trade and sends nothing to anyone.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('mkS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then drop your custodian's position file on the desk, or into the chat.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="Operations desk"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), rc = k.recon || {}, cf = k.confirm || {}, fl = k.fails || {}, rl = k.reclaims || {}, cl = k.calendar || {}, bx = k.best_ex || {};
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : (k.counts && Object.values(k.counts).some(Boolean)) ? 'Everything on the desk is in order.' : 'Add your positions and the custodian\'s file to start.';
    const okR = !rc.empty && !rc.error, okC = !cf.empty && !cf.error, okF = !fl.empty && !fl.error, okL = !rl.empty && !rl.error;
    const brk = okR ? rc.breaks.length + rc.cash_breaks.length : null;
    const pct = okR && rc.positions ? Math.round(rc.matched / rc.positions * 100) : null;
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k${brk ? ' low bad' : ''}"><div class="l">Reconciliation breaks</div><div class="v">${okR ? esc(num(brk)) : '—'}</div><div class="s">${okR ? (pct !== null ? `${esc(pct)}% of ${esc(pl(rc.positions, 'position'))} match` : 'cash only') : 'no positions yet'}</div></div>
        <div class="k${okC && cf.unconfirmed.length ? ' low' : ''}"><div class="l">Not confirmed</div><div class="v">${okC ? esc(num(cf.unconfirmed.length)) : '—'}</div><div class="s">${okC ? `${esc(pl(cf.breaks.length, 'confirmation'))} ${cf.breaks.length === 1 ? 'differs' : 'differ'}` : 'no trades yet'}</div></div>
        <div class="k${okF && fl.fails.length ? ' low bad' : ''}"><div class="l">Failed settlements</div><div class="v">${okF ? esc(m0(fl.value)) : '—'}</div><div class="s">${okF ? `${esc(pl(fl.fails.length, 'fail'))}${typeof fl.penalty === 'number' ? ' · penalty ' + esc(m2(fl.penalty)) : ''}` : 'no settlements yet'}</div></div>
        <div class="k${okL && rl.soon.length ? ' low' : ''}"><div class="l">Tax you can reclaim</div><div class="v">${okL ? esc(m0(rl.reclaimable)) : '—'}</div><div class="s">${okL ? (rl.soon.length ? `${esc(pl(rl.soon.length, 'claim'))} due within 120 days` : 'none due soon') : 'no dividends yet'}</div></div></div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Positions against ${esc(rc.custodian_name || 'the custodian')}</h2><div class="r"><button class="btn soft sm" type="button" data-go="recon">Reconciliation</button></div></div>
          ${okR && rc.positions ? ring([['Match', rc.matched, 'mk-ok'], ['Quantity breaks', rc.by_kind['quantity'], 'mk-q'], ['Missing at the custodian', rc.by_kind['missing at the custodian'], 'mk-mc'], ['Missing in our books', rc.by_kind['missing in our books'], 'mk-mb']], (pct ?? 0) + '%', 'match', 'Reconciliation') : empty(rc.error || 'Add the positions in your books and the custodian\'s file to see this.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Fails by age</h2><div class="r"><button class="btn soft sm" type="button" data-go="settle">Settlement</button></div></div>
          ${okF && fl.fails.length ? bars(Object.entries(fl.by_age).map(([n, v], i) => [n, v, 'mk-age' + i]), v => pl(v, 'fail'), 'Fails by age') : empty(fl.error || (okF ? 'No settlement has failed.' : 'Add the settlements you expect to see this.'))}
          ${okF && fl.due_soon.length ? `<p class="cs-note">${esc(pl(fl.due_soon.length, 'settlement'))} due in the next 5 days.</p>` : ''}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Coming up</h2><div class="r"><button class="btn soft sm" type="button" data-go="research">Calendar</button></div></div>
          ${!cl.empty && !cl.error && cl.next.length ? timeline(cl.next.slice(0, 5)) : empty(cl.error || 'Add your period ends and disclosure rules to see what is due.')}</section></div>
      ${!bx.empty && !bx.error ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Best execution</h2><div class="r"><span class="mut" style="font-size:13px">average ${esc(bx.average_bp)} bp · cost ${esc(m2(bx.total_cost))}</span><button class="btn soft sm" type="button" data-go="bestex">Open</button></div></div>${slipChart(bx.executions.slice(0, 6), bx.limit_bp)}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- reconciliation */
  function pRecon() {
    const k = K(), rc = k.recon || {}, okR = !rc.empty && !rc.error, s = k.settings || {};
    const kindTag = b => b === 'quantity' ? tag('quantity', 'warn') : b === 'missing at the custodian' ? tag('not at the custodian', 'bad') : tag('not in our books', 'bad');
    return `<div><h1 class="sd-h">Reconciliation</h1><p class="lead">The positions in your books against ${esc(s.custodian_name || 'the custodian\'s or broker\'s')} file, by account and instrument, and cash by account and currency. Every break needs an owner and a reason - Hoola does not adjust either side.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('books', 'Positions in your books', 'Account, instrument (ISIN or symbol), quantity. A new file replaces the list.')}
          ${uploader('custodian', 'The custodian\'s position file', 'The same columns from their statement. A new file replaces the list.', `<input class="in sm" name="custodian_name" placeholder="Custodian name" value="${esc(s.custodian_name || '')}" style="max-width:170px">`)}
          ${CAN() ? `<details class="ins-more"><summary>Cash balances too</summary>${uploader('cash_books', 'Cash in your books', 'Account, currency, amount.')}${uploader('cash_custodian', 'The custodian\'s cash', 'Account, currency, amount.')}</details>` : ''}</div>
        <section class="card"><h2 class="md-h2">Where it stands</h2>${okR ? `<div class="iv-kpis s3">${kpi('Match', esc(num(rc.matched)), `of ${pl(rc.positions, 'position')}`, 'cs-pos')}${kpi('Position breaks', esc(num(rc.breaks.length)), s.tolerance ? `tolerance ${num(s.tolerance)}` : 'exact match', rc.breaks.length ? 'cs-neg' : '')}${kpi('Cash breaks', esc(num(rc.cash_breaks.length)), 'by account and currency', rc.cash_breaks.length ? 'cs-neg' : '')}</div>
          ${rc.balanced ? '<div class="iv-verdict"><b>Your books agree with the custodian</b><span>Every position and every cash balance matches.</span></div>' : ''}
          ${!rc.have_books ? '<p class="cs-note">Add the positions in your books.</p>' : !rc.have_custodian ? '<p class="cs-note">Add the custodian\'s file.</p>' : ''}` : (err(rc) || empty('Nothing to reconcile yet.'))}</section></div>
      ${okR && rc.breaks.length ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Position breaks</h2><div class="r"><button class="btn soft sm" type="button" data-dl="breaks">Download CSV</button></div></div>
        <div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Account</th><th>Instrument</th><th>Break</th><th class="r">Our books</th><th class="r">Custodian</th><th class="r">Difference</th><th></th></tr></thead><tbody>${rc.breaks.map(b => `<tr><td>${esc(b.account)}</td><td><b>${esc(b.symbol)}</b></td><td>${kindTag(b.break)}</td><td class="r">${esc(num(b.ours))}</td><td class="r">${esc(num(b.theirs))}</td><td class="r ${sign(b.difference)}">${esc(sgn(b.difference))}</td><td class="r">${ask(`the ${b.break} break on ${b.symbol} in account ${b.account} (ours ${num(b.ours)}, custodian ${num(b.theirs)})`)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${okR && rc.cash_breaks.length ? `<section class="card"><h2 class="md-h2">Cash breaks</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Account</th><th>Currency</th><th class="r">Our books</th><th class="r">Custodian</th><th class="r">Difference</th><th></th></tr></thead><tbody>${rc.cash_breaks.map(c => `<tr><td>${esc(c.account)}</td><td>${esc(c.currency)}</td><td class="r">${esc(money(c.ours, c.currency, 2))}</td><td class="r">${esc(money(c.theirs, c.currency, 2))}</td><td class="r ${sign(c.difference)}">${esc(money(c.difference, c.currency, 2))}</td><td class="r">${ask(`the cash break in ${c.currency} on account ${c.account}`)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><details${ST.open.has('books') ? ' open' : ''} data-key="books"><summary class="mk-sum">Positions in your books <span class="mut">${esc(num((k.counts || {}).books || 0))}</span></summary>
          ${addForm('books', [['account', 'Account', 'text', 'A1'], ['symbol', 'Instrument', 'text', 'ISIN'], ['qty', 'Quantity', 'num']])}
          ${listRows('books', k.books, [['account', 'Account'], ['symbol', 'Instrument'], ['qty', 'Quantity', 1, v => esc(num(v))]])}</details></section>
        <section class="card"><details${ST.open.has('custodian') ? ' open' : ''} data-key="custodian"><summary class="mk-sum">The custodian's positions <span class="mut">${esc(num((k.counts || {}).custodian || 0))}</span></summary>
          ${addForm('custodian', [['account', 'Account', 'text', 'A1'], ['symbol', 'Instrument', 'text', 'ISIN'], ['qty', 'Quantity', 'num']])}
          ${listRows('custodian', k.custodian, [['account', 'Account'], ['symbol', 'Instrument'], ['qty', 'Quantity', 1, v => esc(num(v))]])}</details></section></div>`;
  }

  /* ---------------------------------------------------------------- trades & settlement */
  function pSettle() {
    const k = K(), cf = k.confirm || {}, fl = k.fails || {}, okC = !cf.empty && !cf.error, okF = !fl.empty && !fl.error, s = k.settings || {};
    const tcols = [['id', 'Trade'], ['side', 'Side', 0, v => `<span class="iv-side ${esc(v)}">${esc(cap(v))}</span>`], ['symbol', 'Instrument'], ['account', 'Account'], ['qty', 'Quantity', 1, v => esc(num(v))], ['price', 'Price', 1, v => esc(num(v))], ['trade_date', 'Trade date', 0, v => esc(dmy(v))]];
    return `<div><h1 class="sd-h">Trades &amp; settlement</h1><p class="lead">Your trades matched to the counterparties' confirmations, and the settlements past their intended date with what they cost at your market's daily penalty rate. Hoola never affirms a trade or instructs a settlement.</p></div>
      ${ro()}
      <h2 class="mk-h">Confirmations</h2>
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('trades', 'Your trades', 'Trade id, buy or sell, instrument, account, quantity, price, trade date.')}${uploader('confirms', 'The confirmations', 'The same columns from the counterparty or the matching platform.')}</div>
        <section class="card"><h2 class="md-h2">Matching</h2>${okC ? `<div class="iv-kpis mk-k2">${kpi('Matched', esc(num(cf.matched.length)), '', 'cs-pos')}${kpi('Differ', esc(num(cf.breaks.length)), s.price_tolerance ? `price tolerance ${num(s.price_tolerance)}` : 'exact price', cf.breaks.length ? 'cs-neg' : '')}${kpi('Not confirmed', esc(num(cf.unconfirmed.length)), 'no confirmation yet', cf.unconfirmed.length ? 'warn' : '')}${kpi('No trade', esc(num(cf.confirms_with_no_trade.length)), 'confirmations', cf.confirms_with_no_trade.length ? 'cs-neg' : '')}</div>
          ${cf.trades ? ring([['Matched', cf.matched.length, 'mk-ok'], ['Differ', cf.breaks.length, 'mk-q'], ['Not confirmed', cf.unconfirmed.length, 'mk-mc']], Math.round(cf.matched.length / cf.trades * 100) + '%', 'matched', 'Confirmation matching') : ''}` : (err(cf) || empty('Add your trades and the confirmations to match them.'))}</section></div>
      ${okC && cf.breaks.length ? `<section class="card"><h2 class="md-h2">Confirmations that differ from your trade</h2>${cf.breaks.map(b => `<div class="mk-diff"><div class="h"><b>${esc(b.id)}</b>${ask(`trade ${b.id}: the confirmation differs on ${b.differences.map(d => d.field).join(', ')}`)}</div>
          ${b.differences.map(d => `<div class="iv-part"><span><em>${esc(cap(S(d.field).replace('_', ' ')))}</em></span><span>ours <b>${esc(d.ours)}</b> · theirs <b>${esc(d.theirs)}</b></span></div>`).join('')}</div>`).join('')}</section>` : ''}
      ${okC && (cf.unconfirmed_rows.length || cf.orphan_rows.length) ? `<div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Not confirmed yet</h2>${cf.unconfirmed_rows.length ? cf.unconfirmed_rows.slice(0, 30).map(t => `<div class="cs-row"><span class="iv-side ${esc(t.side)}">${esc(cap(t.side))}</span><span style="flex:1"><b>${esc(t.id)}</b> ${esc(t.symbol)} · ${esc(num(t.qty))} @ ${esc(num(t.price))}</span><span class="mut nw">${esc(dmy(t.trade_date))}</span></div>`).join('') : empty('Every trade is confirmed.')}</section>
        <section class="card"><h2 class="md-h2">Confirmations with no trade</h2>${cf.orphan_rows.length ? cf.orphan_rows.slice(0, 30).map(t => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1"><b>${esc(t.id)}</b> ${esc(t.symbol)} · ${esc(num(t.qty))} @ ${esc(num(t.price))}</span>${ask(`confirmation ${t.id} has no trade in our books`)}</div>`).join('') : empty('None.')}</section></div>` : ''}
      <h2 class="mk-h">Settlement</h2>
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('settlements', 'Settlements you expect', 'Settlement id, instrument, counterparty, value, intended date, status (settled or not).')}
          ${addForm('settlements', [['id', 'Settlement id', 'text', 'S1'], ['symbol', 'Instrument', 'text'], ['counterparty', 'Counterparty', 'text'], ['value', 'Value', 'num'], ['intended', 'Intended date', 'date']], 'Add a settlement')}</div>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Fails</h2><div class="r">${okF && fl.fails.length ? '<button class="btn soft sm" type="button" data-dl="fails">Download CSV</button>' : ''}</div></div>
          ${okF ? `<div class="iv-kpis s3">${kpi('Failed', esc(num(fl.fails.length)), `${num(fl.open)} still open in all`, fl.fails.length ? 'cs-neg' : 'cs-pos')}${kpi('Value', esc(m0(fl.value)), 'past the intended date')}${kpi('Penalty', typeof fl.penalty === 'number' ? esc(m2(fl.penalty)) : '—', fl.penalty_bp !== null && fl.penalty_bp !== undefined ? `at your ${num(fl.penalty_bp)} bp a day` : 'set your market\'s rate in Settings')}</div>
          ${fl.fails.length ? bars(Object.entries(fl.by_age).map(([n, v], i) => [n, v, 'mk-age' + i]), v => pl(v, 'fail'), 'Fails by age') : '<div class="iv-verdict"><b>No settlement has failed</b><span>Everything due has settled.</span></div>'}` : (err(fl) || empty('Add the settlements you expect.'))}</section></div>
      ${okF && fl.fails.length ? `<section class="card"><h2 class="md-h2">Failed settlements</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Settlement</th><th>Instrument</th><th>Counterparty</th><th class="r">Days late</th><th class="r">Value</th><th class="r">Penalty</th><th></th></tr></thead><tbody>${fl.fails.map(f => `<tr><td><b>${esc(f.id)}</b></td><td>${esc(f.symbol || '')}</td><td>${esc(f.counterparty || '')}</td><td class="r">${f.days_late > 10 ? tag(f.days_late + ' days', 'bad') : f.days_late > 5 ? tag(f.days_late + ' days', 'warn') : esc(f.days_late + ' days')}</td><td class="r">${esc(m2(f.value))}</td><td class="r">${f.penalty !== null && f.penalty !== undefined ? esc(m2(f.penalty)) : '—'}</td><td class="r nw">${CAN() && f.n ? `<button class="btn soft sm" type="button" data-settle="${esc(f.n)}">Mark settled</button>` : ''}${ask(`settlement ${f.id} is ${f.days_late} days late`)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${okF && fl.due_soon.length ? `<section class="card"><h2 class="md-h2">Due in the next 5 days</h2>${fl.due_soon.map(x => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1"><b>${esc(x.id)}</b> ${esc(x.symbol || '')} ${x.counterparty ? '· ' + esc(x.counterparty) : ''}</span><span class="mut nw">${esc(dmy(x.intended))}</span><b class="nw">${x.value !== undefined && x.value !== null ? esc(m2(x.value)) : ''}</b></div>`).join('')}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><details${ST.open.has('trades') ? ' open' : ''} data-key="trades"><summary class="mk-sum">Your trades <span class="mut">${esc(num((k.counts || {}).trades || 0))}</span></summary>
          ${addForm('trades', [['id', 'Trade id', 'text', 'T1'], ['side', 'Side', 'side'], ['symbol', 'Instrument', 'text'], ['account', 'Account', 'text'], ['qty', 'Quantity', 'num'], ['price', 'Price', 'num'], ['trade_date', 'Trade date', 'date']], 'Add a trade')}
          ${listRows('trades', k.trades, tcols)}</details></section>
        <section class="card"><details${ST.open.has('settlements') ? ' open' : ''} data-key="settlements"><summary class="mk-sum">All settlements <span class="mut">${esc(num((k.counts || {}).settlements || 0))}</span></summary>
          ${listRows('settlements', k.settlements, [['id', 'Settlement'], ['symbol', 'Instrument'], ['intended', 'Intended', 0, v => esc(dmy(v))], ['value', 'Value', 1, v => v === undefined || v === null ? '' : esc(m2(v))], ['settled', 'Status', 0, (v, r) => v ? tag('settled', 'ok') + (CAN() ? ` <button class="btn soft sm" type="button" data-unsettle="${esc(r.n)}">Reopen</button>` : '') : tag('open')]])}</details></section></div>`;
  }

  /* ---------------------------------------------------------------- corporate actions */
  function pActions() {
    const k = K(), ca = ST.out.ca, evs = k.events || [];
    const tn = {split: 'Split', reverse_split: 'Reverse split', consolidation: 'Consolidation', cash_dividend: 'Cash dividend', stock_dividend: 'Stock dividend', bonus: 'Bonus issue', rights: 'Rights issue'};
    const syms = [...new Set((k.books || []).map(b => b.symbol))].slice(0, 300);
    const ent = (r, type) => `<div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Account</th><th class="r">Held</th>${type === 'cash_dividend' ? '<th class="r">Gross</th><th class="r">Withheld</th><th class="r">Net</th>' : `<th class="r">${['split', 'reverse_split', 'consolidation'].includes(type) ? 'After' : 'New shares'}</th><th class="r">Fraction</th><th class="r">Cash in lieu</th>${type === 'rights' ? '<th class="r">Cost to take up</th>' : ''}`}</tr></thead><tbody>${
      r.entitlements.map(e => `<tr><td>${esc(e.account)}</td><td class="r">${esc(num(e.held))}</td>${type === 'cash_dividend' ? `<td class="r">${esc(m2(e.gross))}</td><td class="r">${esc(m2(e.withheld))}</td><td class="r"><b>${esc(m2(e.net))}</b></td>` : `<td class="r"><b>${esc(num(e.after ?? e.new_shares))}</b></td><td class="r">${esc(num(e.fraction))}</td><td class="r">${e.cash_in_lieu !== undefined ? esc(m2(e.cash_in_lieu)) : '—'}</td>${type === 'rights' ? `<td class="r">${esc(m2(e.cost_to_take_up))}</td>` : ''}`}</tr>`).join('')}</tbody></table></div>`;
    return `<div><h1 class="sd-h">Corporate actions</h1><p class="lead">A split, consolidation, dividend, bonus or rights issue worked out on every account holding the instrument at the record date - entitlements, fractions and the cash in lieu at your price. Check the terms against the issuer's notice before you book it; Hoola books nothing.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <form class="card mk-caform" data-form="ca"><h2 class="md-h2">Work out a corporate action</h2><div class="iv-grid">
          <label class="ins-lab">Type<select class="in" name="type">${Object.entries(tn).map(([v, n]) => `<option value="${v}">${esc(n)}</option>`).join('')}</select></label>
          <label class="ins-lab">Instrument<input class="in" name="symbol" required list="mkSyms" placeholder="ISIN or symbol"></label>
          <label class="ins-lab">Record date<input class="in" type="date" name="record_date" required></label>
          <label class="ins-lab">Pay date<input class="in" type="date" name="pay_date"></label>
          <label class="ins-lab mk-ratio">Ratio (new for old)<input class="in" name="ratio" placeholder="2:1"></label>
          <label class="ins-lab mk-cash">Dividend a share<input class="in" name="rate" inputmode="decimal"></label>
          <label class="ins-lab mk-cash">Withholding %<input class="in" name="withholding_pct" inputmode="decimal"></label>
          <label class="ins-lab mk-rights">Subscription price<input class="in" name="subscription_price" inputmode="decimal"></label>
          <label class="ins-lab mk-ratio">Cash in lieu price<input class="in" name="cash_in_lieu_price" inputmode="decimal"></label></div>
          <datalist id="mkSyms">${syms.map(x => `<option value="${esc(x)}">`).join('')}</datalist>
          ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">On the ${esc(pl((k.counts || {}).books || 0, 'position'))} in your books.</span><button class="btn" type="submit">Work it out</button></div>` : ''}</form>
        <section class="card"><h2 class="md-h2">Result</h2>${ca ? (ca.error ? err(ca) : `<div class="cs-row"><b style="flex:1">${esc(tn[ca.event.type] || ca.event.type)} · ${esc(ca.event.symbol)}</b><span class="mut">record ${esc(dmy(ca.event.record_date))}</span></div>
          <div class="iv-kpis s3">${kpi('Held', esc(num(ca.total_held)), pl(ca.entitlements.length, 'account'))}${Object.entries(ca.totals || {}).slice(0, 2).map(([n, v]) => kpi(cap(n.replace(/_/g, ' ')), esc(n === 'new_shares' ? num(v) : m2(v)), 'in all')).join('')}</div>${ent(ca, ca.event.type)}<p class="cs-note">${esc(ca.says || '')}</p>`) : empty('Choose the action and the instrument; the accounts come from the positions in your books.')}</section></div>
      ${evs.length ? `<section class="card"><h2 class="md-h2">Worked out before</h2><div class="iv-sales">${evs.map(e => `<details class="iv-sale" data-key="ev${esc(e.n)}"${ST.open.has('ev' + e.n) ? ' open' : ''}><summary><span class="iv-ty">${esc(tn[e.event.type] || e.event.type)}</span><b>${esc(e.event.symbol)}</b><span class="mut">record ${esc(dmy(e.event.record_date))}${e.event.ratio ? ' · ' + esc(e.event.ratio) : ''}${e.event.rate !== undefined ? ' · ' + esc(num(e.event.rate)) + ' a share' : ''}</span><span class="r">${e.net !== undefined ? esc(m2(e.net)) + ' net' : e.new_shares !== undefined ? esc(num(e.new_shares)) + ' new' : ''}</span></summary>
          <div class="iv-parts">${(e.entitlements || []).map(x => `<div class="iv-part"><span><em>${esc(x.account)}</em> held ${esc(num(x.held))}</span><span>${x.net !== undefined ? 'net ' + esc(m2(x.net)) : (x.after !== undefined ? 'after ' + esc(num(x.after)) : 'new ' + esc(num(x.new_shares))) + (x.fraction ? ` · fraction ${esc(num(x.fraction))}` : '')}</span></div>`).join('')}
          <div class="md-acts"><span class="mut" style="font-size:12.5px">${esc(e.by || '')} · ${esc(dt(e.on))}</span>${rmBtn('events', e.n)}</div></div></details>`).join('')}</div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- tax reclaims */
  function pReclaims() {
    const k = K(), rl = k.reclaims || {}, ok = !rl.empty && !rl.error, s = k.settings || {};
    return `<div><h1 class="sd-h">Tax reclaims</h1><p class="lead">Dividend withholding tax against the treaty rate you give for each country: what was withheld too much, what can be reclaimed, and the date each claim must be in by from the claim period you give. The rates and periods are yours - check them with the tax office.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('dividends', 'Dividends received', 'Pay date, instrument, source country, gross, tax withheld.')}
          ${addForm('dividends', [['date', 'Pay date', 'date'], ['symbol', 'Instrument', 'text'], ['country', 'Country', 'text', 'US'], ['gross', 'Gross', 'num'], ['withheld', 'Withheld', 'num']], 'Add a dividend')}</div>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">What you can reclaim</h2><div class="r">${ok && rl.claims.length ? '<button class="btn soft sm" type="button" data-dl="reclaims">Download CSV</button>' : ''}</div></div>
          ${ok ? `<div class="iv-kpis s3">${kpi('Reclaimable', esc(m2(rl.reclaimable)), 'claims still open', 'cs-pos')}${kpi('Due within 120 days', esc(num(rl.soon.length)), rl.soon.length ? 'next ' + dmy(rl.soon.slice().sort((a, b) => a.days_left - b.days_left)[0].claim_by) : 'none', rl.soon.length ? 'warn' : '')}${kpi('Past the claim date', esc(m2(rl.expired)), 'can no longer be claimed', rl.expired ? 'cs-neg' : '')}</div>
            ${Object.keys(rl.by_country).length ? bars(Object.entries(rl.by_country).sort((a, b) => b[1] - a[1]).map(([c, v]) => [c, v, 'mk-b', s.treaty && s.treaty[c] !== undefined ? `treaty ${s.treaty[c]}%` : '']), v => m2(v), 'Reclaimable by country') : ''}
            ${rl.no_treaty_rate_given_for.length ? `<p class="cs-note">No treaty rate for ${esc(rl.no_treaty_rate_given_for.join(', '))} - give it in <a href="#/settings">Settings</a>.</p>` : ''}
            ${rl.no_period_for.length ? `<p class="cs-note">No claim period for ${esc(rl.no_period_for.join(', '))} - the deadline cannot be shown.</p>` : ''}` : (err(rl) || empty('Add the dividends you received and the tax withheld.'))}</section></div>
      ${ok && rl.claims.length ? `<section class="card"><h2 class="md-h2">Claims</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Paid</th><th>Instrument</th><th>Country</th><th class="r">Gross</th><th class="r">Withheld</th><th class="r">Treaty</th><th class="r">Reclaim</th><th>Claim by</th><th></th></tr></thead><tbody>${rl.claims.slice().sort((a, b) => (a.expired - b.expired) || ((a.days_left ?? 1e9) - (b.days_left ?? 1e9))).map(c => `<tr><td>${esc(dmy(c.date))}</td><td><b>${esc(c.symbol)}</b></td><td>${esc(c.country)}</td><td class="r">${esc(m2(c.gross))}</td><td class="r">${esc(m2(c.withheld))}</td><td class="r">${esc(c.treaty_rate_pct)}%</td><td class="r"><b>${esc(m2(c.reclaimable))}</b></td><td>${c.expired ? tag('expired', 'bad') : c.claim_by ? `${esc(dmy(c.claim_by))} ${c.days_left <= 30 ? tag(c.days_left + ' days', 'bad') : c.days_left <= 120 ? tag(c.days_left + ' days', 'warn') : ''}` : tag('no period')}</td><td class="r">${ask(`the reclaim on ${c.symbol} (${c.country}) paid ${c.date}`)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><details${ST.open.has('dividends') ? ' open' : ''} data-key="dividends"><summary class="mk-sum">All dividends <span class="mut">${esc(num((k.counts || {}).dividends || 0))}</span></summary>
        ${listRows('dividends', k.dividends, [['date', 'Paid', 0, v => esc(dmy(v))], ['symbol', 'Instrument'], ['country', 'Country'], ['gross', 'Gross', 1, v => esc(m2(v))], ['withheld', 'Withheld', 1, v => esc(m2(v))]])}</details></section>`;
  }

  /* ---------------------------------------------------------------- margin */
  function pMargin() {
    const k = K(), mg = ST.out.margin, s = k.settings || {}, hist = k.margins || [];
    const hc = Object.entries(s.haircuts || {}).map(([a, b]) => `${a}, ${b}`).join('\n');
    return `<div><h1 class="sd-h">Margin</h1><p class="lead">A margin call worked out: your collateral after your haircuts against the requirement, the shortfall or excess, and the notice text. Hoola sends nothing - you or your team send the call.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="margin"><h2 class="md-h2">Work out a call</h2><div class="cr-grid">
          <label class="ins-lab">Counterparty<input class="in" name="counterparty" maxlength="60" placeholder="Client or CCP"></label>
          <label class="ins-lab">Account<input class="in" name="account" maxlength="40"></label>
          <label class="ins-lab">Requirement<input class="in" name="requirement" required inputmode="decimal"></label>
          <label class="ins-lab">Due<input class="in" type="date" name="due"></label>
          <label class="ins-lab wide">Collateral: what it is, value, class (one a line)<textarea class="in" name="collateral" rows="4" required placeholder="UK Gilt 2030, 800000, bond&#10;ACME, 200000, equity"></textarea></label>
          <label class="ins-lab wide">Haircuts: instrument or class, % (one a line)<textarea class="in" name="haircuts" rows="3" placeholder="BOND, 5&#10;EQUITY, 25">${esc(hc)}</textarea></label></div>
          ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Haircuts come from Settings unless you change them here.</span><button class="btn" type="submit">Work out the call</button></div>' : ''}</form>
        <section class="card"><h2 class="md-h2">Result</h2>${mg ? (mg.error ? err(mg) : `<div class="iv-kpis s3">${kpi('Requirement', esc(m2(mg.requirement)), '')}${kpi('Collateral counts for', esc(m2(mg.collateral_after_haircuts)), 'after haircuts')}${mg.shortfall ? kpi('Shortfall', esc(m2(mg.shortfall)), 'to be called', 'cs-neg') : kpi('Excess', esc(m2(mg.excess)), 'no call needed', 'cs-pos')}</div>
          ${covBar(mg)}
          <table class="tb"><thead><tr><th>Collateral</th><th class="r">Value</th><th class="r">Haircut</th><th class="r">Counts for</th></tr></thead><tbody>${(mg.collateral || []).map(c => `<tr><td>${esc(c.item)}</td><td class="r">${esc(m2(c.value))}</td><td class="r">${esc(c.haircut_pct)}%</td><td class="r">${esc(m2(c.counts_for))}</td></tr>`).join('')}</tbody></table>
          ${mg.notice ? `<div class="mk-notice"><div class="h"><b>Notice text</b><button class="btn soft sm" type="button" data-copy="1">Copy</button></div><p id="mkNotice">${esc(mg.notice)}</p></div>` : ''}`) : empty('Enter the requirement and the collateral held.')}</section></div>
      ${hist.length ? `<section class="card"><h2 class="md-h2">Calls worked out</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>When</th><th>Counterparty</th><th class="r">Requirement</th><th class="r">Collateral</th><th class="r">Shortfall</th><th>Due</th><th></th></tr></thead><tbody>${hist.map(m => `<tr><td>${esc(dt(m.on))}</td><td>${esc(m.counterparty || '—')}${m.account ? ' <span class="mut">' + esc(m.account) + '</span>' : ''}</td><td class="r">${esc(m2(m.requirement))}</td><td class="r">${esc(m2(m.collateral_after_haircuts))}</td><td class="r">${m.shortfall ? `<b class="cs-neg">${esc(m2(m.shortfall))}</b>` : tag('covered', 'ok')}</td><td>${esc(m.due ? dmy(m.due) : '')}</td><td class="r">${rmBtn('margins', m.n)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}`;
  }
  function covBar(mg) {
    const req = Number(mg.requirement) || 0, col = Number(mg.collateral_after_haircuts) || 0, mx = Math.max(req, col) || 1;
    return `<div class="mk-cov"><div><span>Requirement</span><i><b class="req" style="width:${(req / mx * 100).toFixed(1)}%"></b></i></div><div><span>Collateral</span><i><b class="${col >= req ? 'ok' : 'bad'}" style="width:${(col / mx * 100).toFixed(1)}%"></b></i></div></div>`;
  }

  /* ---------------------------------------------------------------- best execution */
  function pBestex() {
    const k = K(), bx = k.best_ex || {}, ok = !bx.empty && !bx.error;
    return `<div><h1 class="sd-h">Best execution</h1><p class="lead">Each execution against its benchmark price (arrival, VWAP or the one you use): slippage in basis points, the worst ones and what they cost in all. A positive number is a cost to the client.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('executions', 'Executions', 'Execution id, buy or sell, instrument, quantity, price, benchmark price, date.')}
          ${addForm('executions', [['id', 'Execution id', 'text', 'E1'], ['side', 'Side', 'side'], ['symbol', 'Instrument', 'text'], ['qty', 'Quantity', 'num'], ['price', 'Price', 'num'], ['benchmark', 'Benchmark', 'num']], 'Add')}</div>
        <section class="card"><h2 class="md-h2">The picture</h2>${ok ? `<div class="iv-kpis mk-k2">${kpi('Average', esc(bx.average_bp) + ' bp', pl(bx.executions.length, 'execution'), sign(bx.average_bp) === 'cs-pos' ? 'cs-neg' : 'cs-pos')}${kpi('Total cost', esc(m2(bx.total_cost)), 'against the benchmarks', Number(bx.total_cost) > 0 ? 'cs-neg' : 'cs-pos')}${kpi('Better', esc(num(bx.better)), 'than the benchmark', 'cs-pos')}${kpi('Over your limit', bx.limit_bp !== null && bx.limit_bp !== undefined ? esc(num(bx.over.length)) : '—', bx.limit_bp !== null && bx.limit_bp !== undefined ? `${num(bx.limit_bp)} bp` : 'set it in Settings', bx.over.length ? 'cs-neg' : '')}</div>` : (err(bx) || empty('Add executions with their benchmark price.'))}</section></div>
      ${ok ? `<section class="card"><h2 class="md-h2">Worst first</h2>${slipChart(bx.executions, bx.limit_bp)}</section>
      <section class="card"><details${ST.open.has('ex') ? ' open' : ''} data-key="ex"><summary class="mk-sum">Every execution <span class="mut">${esc(num(bx.executions.length))}</span></summary>
        <div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Execution</th><th>Instrument</th><th>Side</th><th class="r">Slippage</th><th class="r">Cost</th><th></th></tr></thead><tbody>${bx.executions.map(x => `<tr><td><b>${esc(x.id)}</b></td><td>${esc(x.symbol || '')}</td><td><span class="iv-side ${esc(x.side)}">${esc(cap(x.side))}</span></td><td class="r ${x.slippage_bp > 0 ? 'cs-neg' : 'cs-pos'}">${esc(sgn(x.slippage_bp))} bp</td><td class="r">${esc(m2(x.cost))}</td><td class="r">${rmBtn('executions', x.n)}${ask(`execution ${x.id}: ${x.slippage_bp} bp against the benchmark`)}</td></tr>`).join('')}</tbody></table></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-rmall="executions">Clear all</button></div>' : ''}</details></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settlement instructions */
  function pSsi() {
    const k = K(), sx = k.ssi || {}, ok = !sx.empty && !sx.error;
    return `<div><h1 class="sd-h">Settlement instructions</h1><p class="lead">Standing settlement instructions checked: missing parts, the shape of the BIC, the IBAN check digits, and a second, different instruction for the same counterparty and currency. A changed instruction is confirmed by a call-back on a number already on file - never by the email that changed it.</p></div>
      ${ro()}
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('instructions', 'Instructions', 'Counterparty, currency, BIC, account, IBAN.')}
          ${addForm('instructions', [['counterparty', 'Counterparty', 'text'], ['currency', 'Currency', 'text', 'EUR'], ['bic', 'BIC', 'text', 'DEUTDEFF'], ['account', 'Account', 'text'], ['iban', 'IBAN', 'text']], 'Add')}</div>
        <section class="card"><h2 class="md-h2">Check</h2>${ok ? `<div class="iv-kpis s3">${kpi('Instructions', esc(num(sx.instructions.length)), '')}${kpi('With a problem', esc(num(sx.bad)), '', sx.bad ? 'cs-neg' : 'cs-pos')}${kpi('Problems', esc(num(sx.problems)), 'in all', sx.problems ? 'cs-neg' : '')}</div>
          ${sx.bad ? '' : '<div class="iv-verdict"><b>Every instruction checks out</b><span>No missing parts, the BICs and IBANs have the right shape.</span></div>'}` : (err(sx) || empty('Add your settlement instructions to check them.'))}</section></div>
      ${ok ? `<section class="card"><h2 class="md-h2">Instructions</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Counterparty</th><th>Currency</th><th>BIC</th><th>Account</th><th>IBAN</th><th>Check</th><th></th></tr></thead><tbody>${sx.instructions.map(x => `<tr><td><b>${esc(x.counterparty || '')}</b></td><td>${esc(x.currency || '')}</td><td class="mk-mono">${esc(x.bic || '')}</td><td>${esc(x.account || '')}</td><td class="mk-mono">${esc(x.iban || '')}</td><td>${x.ok ? tag('ok', 'ok') : x.problems.map(p => `<div class="mk-prob">${esc(p)}</div>`).join('')}</td><td class="r nw">${rmBtn('instructions', x.n)}${x.ok ? '' : ask(`the settlement instruction for ${x.counterparty} ${x.currency}: ${x.problems.join('; ')}`)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- comparables & IR calendar */
  function pResearch() {
    const k = K(), cp = k.comps || {}, cl = k.calendar || {}, s = k.settings || {}, t = s.target || {}, okP = !cp.empty && !cp.error, okC = !cl.empty && !cl.error;
    const MN = {ev_ebitda: 'EV / EBITDA', ev_revenue: 'EV / revenue', pe: 'P / E'};
    return `<div><h1 class="sd-h">Comparables &amp; disclosure calendar</h1><p class="lead">A comparables table from the peers you choose and the value range they imply for a target, and your investor-relations calendar from your period ends and your exchange's rules. Multiples describe the peers you picked; they are not a valuation opinion.</p></div>
      ${ro()}
      <h2 class="mk-h">Comparables</h2>
      <div class="md-2" style="align-items:start">
        <div class="card">${uploader('peers', 'Peers', 'Name, EV, EBITDA, revenue, price, EPS. A new file replaces the list.')}
          ${addForm('peers', [['name', 'Peer', 'text'], ['ev', 'EV', 'num'], ['ebitda', 'EBITDA', 'num'], ['revenue', 'Revenue', 'num'], ['price', 'Price', 'num'], ['eps', 'EPS', 'num']], 'Add a peer')}
          <form data-form="target" class="mk-target"><div class="cr-sub" style="margin-top:14px">The target</div><div class="iv-grid">
            <label class="ins-lab">Name<input class="in" name="name" value="${esc(t.name || '')}"></label>
            <label class="ins-lab">EBITDA<input class="in" name="ebitda" inputmode="decimal" value="${esc(t.ebitda ?? '')}"></label>
            <label class="ins-lab">Revenue<input class="in" name="revenue" inputmode="decimal" value="${esc(t.revenue ?? '')}"></label>
            <label class="ins-lab">EPS<input class="in" name="eps" inputmode="decimal" value="${esc(t.eps ?? '')}"></label></div>
            ${CAN() ? '<div class="md-acts"><span></span><button class="btn soft" type="submit">Save the target</button></div>' : ''}</form></div>
        <section class="card"><h2 class="md-h2">Implied for ${esc(t.name || 'the target')}</h2>${okP && Object.keys(cp.implied_for_target || {}).length ? Object.entries(cp.implied_for_target).map(([m, r]) => rangeBar(MN[m] || m, r)).join('') + `<p class="cs-note">${esc(cp.says || '')}</p>` : empty(okP ? 'Give the target\'s EBITDA, revenue or EPS to see the range.' : (cp.error || 'Add the peers you compare with.'))}</section></div>
      ${okP ? `<section class="card"><h2 class="md-h2">The table</h2><div class="iv-tw"><table class="tb iv-tb"><thead><tr><th>Peer</th>${Object.keys(MN).map(m => `<th class="r">${esc(MN[m])}</th>`).join('')}<th></th></tr></thead><tbody>${cp.peers.map(p => `<tr><td><b>${esc(p.name)}</b></td>${Object.keys(MN).map(m => `<td class="r">${p[m] !== undefined ? esc(p[m]) + 'x' : '—'}</td>`).join('')}<td class="r">${rmBtn('peers', p.n)}</td></tr>`).join('')}
        ${['median', 'mean', 'low', 'high'].map(st => `<tr class="mk-stat"><td>${esc(cap(st))}</td>${Object.keys(MN).map(m => `<td class="r">${cp.multiples[m] ? esc(cp.multiples[m][st]) + 'x' : '—'}</td>`).join('')}<td></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <h2 class="mk-h">Disclosure calendar</h2>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="cal"><h2 class="md-h2">Your periods and rules</h2><div class="mk-two">
          <label class="ins-lab">Period ends, one a line<textarea class="in" name="period_ends" rows="5" placeholder="2026-12-31&#10;2027-06-30">${esc((s.period_ends || []).join('\n'))}</textarea></label>
          <label class="ins-lab">Rules: what, days after the end<textarea class="in" name="ir_rules" rows="5" placeholder="Half-year report, 90&#10;Trading update, 30">${esc((s.ir_rules || []).map(r => `${r.name}, ${r.days_after}`).join('\n'))}</textarea></label></div>
          <p class="cs-note">From your exchange's rulebook - Hoola has no rule of its own.</p>
          ${CAN() ? `<div class="md-acts"><span></span><button class="btn" type="submit">Save and build the calendar</button></div>` : ''}</form>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Next due</h2><div class="r">${okC ? '<button class="btn soft sm" type="button" data-dl="calendar">Download CSV</button>' : ''}</div></div>
          ${okC ? (cl.next.length ? timeline(cl.next) : empty('Nothing still to come - add the next period end.')) : empty(cl.error || 'Add a period end and a rule.')}
          ${okC && cl.past.length ? `<details class="ins-more"><summary>Past</summary>${timeline(cl.past.slice().reverse())}</details>` : ''}</section></div>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, w = W();
    const lines = o => Object.entries(o || {}).map(([a, b]) => `${a}, ${b}`).join('\n');
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your tolerances, your market's penalty rate, your treaty rates and claim periods, your haircuts. Hoola brings none of its own - every rate here is yours.</p></div>
      ${ro()}
      <form class="card" data-form="settings"><h2 class="md-h2">Matching and limits</h2><div class="md-form">
        <div class="md-field"><label for="mkT1">Custodian or broker name</label><input class="in" id="mkT1" name="custodian_name" maxlength="60" value="${esc(s.custodian_name || '')}"></div>
        <div class="md-field"><label for="mkT2">Quantity tolerance (reconciliation)</label><input class="in" id="mkT2" name="tolerance" inputmode="decimal" value="${esc(s.tolerance ?? '')}" placeholder="0 = exact"></div>
        <div class="md-field"><label for="mkT3">Price tolerance (confirmations)</label><input class="in" id="mkT3" name="price_tolerance" inputmode="decimal" value="${esc(s.price_tolerance ?? '')}" placeholder="0 = exact"></div>
        <div class="md-field"><label for="mkT4">Settlement penalty, basis points a day</label><input class="in" id="mkT4" name="penalty_bp" inputmode="decimal" value="${esc(s.penalty_bp ?? '')}" placeholder="your market's rate"></div>
        <div class="md-field"><label for="mkT5">Slippage limit, basis points</label><input class="in" id="mkT5" name="slip_bp" inputmode="decimal" value="${esc(s.slip_bp ?? '')}" placeholder="e.g. 25"></div></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <form class="card" data-form="rates"><h2 class="md-h2">Treaty rates, claim periods and haircuts</h2><div class="mk-three">
          <label class="ins-lab">Treaty rate: country, % (one a line)<textarea class="in" name="treaty" rows="5" placeholder="US, 15&#10;DE, 15">${esc(lines(s.treaty))}</textarea></label>
          <label class="ins-lab">Claim period: country, years<textarea class="in" name="claim_years" rows="5" placeholder="US, 3&#10;DE, 4">${esc(lines(s.claim_years))}</textarea></label>
          <label class="ins-lab">Haircut: instrument or class, %<textarea class="in" name="haircuts" rows="5" placeholder="BOND, 5&#10;EQUITY, 25">${esc(lines(s.haircuts))}</textarea></label></div>
        <p class="cs-note">Check treaty rates and claim periods with the tax office of each country; they change.</p>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save the rates</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({books: 'positions in your books', custodian: 'custodian positions', cash_books: 'cash in your books', cash_custodian: 'custodian cash', confirms: 'confirmations', instructions: 'settlement instructions', events: 'corporate actions', margins: 'margin calls'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind.replace('_', ' '))} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('mkN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/markets/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
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
    if (t.closest('select, input, textarea, label, summary')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { setCtx(ak.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText($('#mkNotice').textContent); toast('Copied.'); } catch { toast('Select the text to copy it.', true); } return; }
    try {
      const rm = t.closest('[data-rm]'); if (rm) { await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
      const se = t.closest('[data-settle]'); if (se) { await run('settle', {n: Number(se.dataset.settle), settled: true}); await changed('Marked settled.'); return; }
      const us = t.closest('[data-unsettle]'); if (us) { await run('settle', {n: Number(us.dataset.unsettle), settled: false}); await changed('Open again.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 12e6) { toast('Up to 12 MB.', true); return; }
    const nm = form.querySelector('[name=custodian_name]');
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name, ...(nm && nm.value.trim() ? {custodian_name: nm.value.trim()} : {})}); fi.value = ''; await changed(r.says + ` from ${f.name}.`); }
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
    const keepOut = async (key, part, a) => { try { ST.out[key] = await run(part, a); await changed(''); } catch (err2) { ST.out[key] = {error: err2.message}; showPage(true); } };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/markets/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'ca') { await keepOut('ca', 'corp_action', pick(['type', 'symbol', 'record_date', 'pay_date', 'ratio', 'rate', 'withholding_pct', 'subscription_price', 'cash_in_lieu_price'])); }
      else if (kind === 'margin') { await keepOut('margin', 'margin', pick(['counterparty', 'account', 'requirement', 'due', 'collateral', 'haircuts'])); }
      else if (kind === 'target') { await run('settings', {target: pick(['name', 'ebitda', 'revenue', 'eps'])}); await changed('The target is saved.'); }
      else if (kind === 'cal') { await run('settings', {period_ends: g('period_ends'), ir_rules: g('ir_rules')}); await changed('Your calendar is built.'); }
      else if (kind === 'settings') { await run('settings', {custodian_name: g('custodian_name'), tolerance: g('tolerance'), price_tolerance: g('price_tolerance'), penalty_bp: g('penalty_bp'), slip_bp: g('slip_bp')}); await changed('Saved.'); }
      else if (kind === 'rates') { await run('settings', {treaty: g('treaty'), claim_years: g('claim_years'), haircuts: g('haircuts')}); await changed('Your rates are saved.'); }
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
    const box = $('#mkFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/markets/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'mk' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


