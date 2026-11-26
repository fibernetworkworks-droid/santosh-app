/* CREDIT & LENDING DESK - the Credit & Lending employee's own section, like Payroll, Tax and Cash & Treasury (owner: "NOW LETS WORK ON
   NEXT EMPLOYEE CREDIT AND LENDING"). A thin top bar, then the Credit chat (its own conversation, kind 'credit': she asks the real cost
   of a loan or drops a borrower's statement) beside the desk's pages: Today, Borrowing, Applications, Loan book, Risk, Settings. The
   pages call /api/credit/do/<part>, which runs the F6 engine on the business she picked. Hoola gives no score, approves or declines
   nothing, pays out nothing and never sends a collections contact - the decision is the named person's. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', credit: '<rect x="2.5" y="5.5" width="19" height="13" rx="2.5"/><path d="M2.5 10h19M6 15h4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['borrow', 'Borrowing'], ['apps', 'Applications'], ['loans', 'Loan book'], ['risk', 'Risk'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Who is behind on payments?', 'What do I owe this month?'],
    borrow: ['What does this loan really cost?', 'Which offer is cheapest?', 'Am I ready to ask a bank for a loan?'],
    apps: ['Read this borrower\'s statement', 'Write the credit memo', 'Which conditions are still missing?'],
    loans: ['Who is past due and by how much?', 'Can I call this borrower now?', 'Record a payment I received'],
    risk: ['Which loans are getting worse?', 'Explain the ECL working paper', 'What PD and LGD do I need?'],
    settings: ['What APR method does my country use?', 'Help me write my contact rules', 'Which policy limits should I set?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    cmp: null, app: null, appFor: '', risk: null, aprRes: null, aprIn: null, ifRes: null, ifIn: null, ready: null, coll: null, sched: null, schedFor: '', schedAll: false, lf: 'all', lq: ''};
  try { ST.side = localStorage.getItem('hoola.credit.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.credit.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const B = () => K().book || {loans: [], lent: {}, borrowed: {}};
  const cur = () => (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const pct = v => (v === null || v === undefined || v === '') ? '—' : `${Number(v).toLocaleString(undefined, {maximumFractionDigits: 2})}%`;
  const can = () => !!(ST.d && ST.d.can_write);
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/credit/do/' + part, {workspace: W().id, ...(a || {})});
  const loanOf = n => (B().loans || []).find(x => String(x.n) === String(n));
  const appsOf = () => K().apps || [];
  const BUCKETS = [['current', 'Up to date', 'ok'], ['1-30', '1–30 days late', 'warn1'], ['31-60', '31–60 days', 'warn'], ['61-90', '61–90 days', 'bad1'], ['90+', 'Over 90 days', 'bad']];
  const METH = {eu_annual: 'Annual equivalent', us_actuarial: 'US actuarial', nominal_irr: 'Nominal rate', effective_irr: 'Effective rate'};
  const dpdCls = d => d === 0 ? 'ok' : d <= 30 ? 'warn' : 'bad';
  const SEV = {refer: 'Refer', stop: 'Stop', info: 'Info'};
  const RATIO_SAY = {current_ratio: 'Current ratio (at least)', debt_to_equity: 'Debt to equity (at most)', interest_cover: 'Interest cover (at least)',
    dscr: 'Debt service cover (at least)', ebitda_margin_pct: 'EBITDA margin % (at least)', net_margin_pct: 'Net margin % (at least)',
    debt_to_income: 'Debt to income % (at most)'};
  const RATIO_NAME = {current_ratio: 'Current ratio', debt_to_equity: 'Debt to equity', interest_cover: 'Interest cover', dscr: 'Debt service cover',
    ebitda_margin_pct: 'EBITDA margin', net_margin_pct: 'Net margin', debt_to_income: 'Debt to income'};
  const FIG_SAY = {revenue: 'Revenue', ebitda: 'EBITDA', net_profit: 'Net profit', interest: 'Interest a year', debt_service: 'Debt service a year',
    total_debt: 'Total debt', net_worth: 'Net worth', current_assets: 'Current assets', current_liabilities: 'Current liabilities',
    income_monthly: 'Income a month', obligations_monthly: 'Debt payments a month'};
  const figName = k => FIG_SAY[k] || cap(S(k).replace(/^statement_/, 'Statement: ').replace(/_/g, ' '));

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/credit/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.credit, '')}</div>
        <h1 class="sd-h">Your Credit & Lending employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="crHire">Hire Credit & Lending</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#crHire').onclick = async () => { try { await api('POST', '/api/employees/credit_lending/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.credit, '')}</div>
          <div style="min-width:0"><div class="sd-name">Credit & Lending</div><div class="sd-site" id="crSite"></div></div>
          <span id="crState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="crBiz" aria-label="Business" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Credit chat">
          <div class="sd-chathead"><div class="t"><b>Credit chat</b><span>Ask the real cost of a loan, or drop a borrower's statement here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="crFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="crPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Credit & Lending desk" id="sdTabs"></nav>
          <div id="crPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the loan figures. It decides nothing.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a loan…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#crPick').click()});
    $('#crPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.credit.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.credit.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/credit/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#crBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/credit/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#crPage').addEventListener('click', onPageClick);
    $('#crPage').addEventListener('submit', onSubmit);
    $('#crPage').addEventListener('change', onChange);
    $('#crPage').addEventListener('mousemove', onChartMove);
    $('#crPage').addEventListener('mouseleave', () => { const t = $('#crTip'); if (t) t.hidden = true; }, true);
    $('#crPage').addEventListener('input', e => { if (e.target.id !== 'crLq') return; ST.lq = e.target.value; const at = e.target.selectionStart;
      showPage(true); const q = $('#crLq'); if (q) { q.focus(); try { q.setSelectionRange(at, at); } catch {} } });
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function clearCache() { ST.cmp = null; ST.app = null; ST.appFor = ''; ST.risk = null; ST.ready = null; ST.sched = null; ST.schedFor = ''; }
  function stateLine() {
    const d = ST.d, el = $('#crState'); if (!el) return;
    const w = W(), b = B();
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your business'] : (b.lent || {}).in_arrears ? ['warn', `${b.lent.in_arrears} in arrears`]
      : (b.borrowed || {}).missed && b.borrowed.missed.length ? ['warn', 'A payment is late'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#crSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + (d.roles[d.role] || d.role) : ''}` : 'No business yet';
    const sel = $('#crBiz');
    sel.innerHTML = (d.businesses || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.businesses || []).length < 2;
  }
  function paintTabs() {
    const b = B(), k = K();
    const late = appsOf().filter(a => a.status !== 'closed' && ((a.checklist || {}).items || []).some(i => i.late)).length;
    const n = {loans: ((b.lent || {}).in_arrears || 0) + (((b.borrowed || {}).missed || []).length), apps: late || '',
      risk: (b.loans || []).filter(v => v.side === 'lent' && v.rising).length || '', settings: (k.method && !k.method.method) ? '!' : ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/credit/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#crPage'); if (!box) return;
    if (!W()) { box.innerHTML = noBiz(); starters(); return; }
    const fn = {today: pToday, borrow: pBorrow, apps: pApps, loans: pLoans, risk: pRisk, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    if (typeof html === 'string') box.innerHTML = html;
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function noBiz() {
    return `<div><h1 class="sd-h">Set up your business first</h1><p class="lead">The Credit & Lending desk works on a business in Books & Accounts (name, country, currency). Make one there, then come back.</p></div>
      <div><a class="btn" href="/console/books">Open Books & Accounts</a></div>`;
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const side = s => s === 'lent' ? '<span class="cs-tag ok">You lent</span>' : '<span class="cs-tag">You owe</span>';
  const dpdTag = v => v.days_past_due ? `<span class="cs-tag ${dpdCls(v.days_past_due)}">${esc(v.days_past_due)} days late</span>` : '<span class="cs-tag ok">Up to date</span>';
  async function lazy(key, part, a, after) {
    if (ST[key] !== null && ST[key] !== undefined) return ST[key];
    ST[key] = false;
    try { ST[key] = await run(part, a); } catch (e) { ST[key] = {error: e.message}; }
    if (after !== false) showPage(true);
    return ST[key];
  }

  /* the age of the money owed to her: one bar in five parts (up to date -> over 90 days late) */
  function ageBar(bk) {
    const tot = BUCKETS.reduce((s, [k]) => s + ((bk[k] || {}).outstanding || 0), 0);
    if (!tot) return '';
    const parts = BUCKETS.filter(([k]) => (bk[k] || {}).outstanding).map(([k, l, c]) => `<span class="${c}" style="width:${(100 * bk[k].outstanding / tot).toFixed(2)}%" title="${esc(l)}: ${esc(money(bk[k].outstanding))}"></span>`).join('');
    const leg = BUCKETS.map(([k, l, c]) => { const n = (bk[k] || {}).count || 0;
      return `<div class="cr-leg${n ? '' : ' none'}"><i class="${c}"></i><div><span>${esc(l)}<em> · ${esc(n)} loan${n === 1 ? '' : 's'}</em></span><b>${esc(money((bk[k] || {}).outstanding || 0))}</b></div></div>`; }).join('');
    return `<div class="cr-age">${parts}</div><div class="cr-legs">${leg}</div>`;
  }

  /* the next 12 months: money the schedules bring in (loans she lent) against money going out (loans she owes) */
  function outlookChart(o) {
    const ms = (o && o.months) || []; if (!ms.length) return '';
    const Wd = 760, Hd = 210, L = 52, R = 10, Tp = 12, Bt = 26, iw = Wd - L - R, ih = Hd - Tp - Bt;
    const hi = Math.max(1, ...ms.map(m => Math.max(m.in + m.late_in, m.out)));
    const y = v => Tp + ih - (v / hi) * ih, step = iw / ms.length, bw = Math.max(5, Math.min(18, step * 0.3));
    let g = '';
    for (let i = 0; i <= 3; i++) { const v = hi * i / 3; g += `<line class="ax" x1="${L}" x2="${Wd - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`; }
    ms.forEach((m, i) => {
      const x = L + step * (i + 0.5), base = Tp + ih;
      g += `<rect class="hit" data-m="${i}" x="${(L + step * i).toFixed(1)}" y="${Tp}" width="${step.toFixed(1)}" height="${ih}"/><rect class="hl" x="${(L + step * i).toFixed(1)}" y="${Tp}" width="${step.toFixed(1)}" height="${ih}"/>`;
      if (m.late_in) g += `<rect class="blate" x="${(x - bw - 1).toFixed(1)}" y="${y(m.in + m.late_in).toFixed(1)}" width="${bw}" height="${(base - y(m.late_in)).toFixed(1)}" rx="2"/>`;
      g += `<rect class="bin" x="${(x - bw - 1).toFixed(1)}" y="${y(m.in).toFixed(1)}" width="${bw}" height="${(base - y(m.in)).toFixed(1)}" rx="2"/>`
        + `<rect class="bout" x="${(x + 1).toFixed(1)}" y="${y(m.out).toFixed(1)}" width="${bw}" height="${(base - y(m.out)).toFixed(1)}" rx="2"/>`
        + `<text class="tx" x="${x.toFixed(1)}" y="${Hd - 8}" text-anchor="middle">${esc(mon(m.month))}</text>`;
    });
    return `<div class="cs-chart cr-chart"><svg viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Repayments over the next 12 months">${g}</svg><div class="cs-tip" id="crTip" hidden></div></div>
      <div class="cs-legend"><span><i class="in"></i>Coming in to you</span><span><i class="late"></i>Behind, owed to you now</span><span><i class="out"></i>Going out from you</span></div>`;
  }
  const mon = ym => { try { return new Date(ym + '-01T00:00').toLocaleDateString(undefined, {month: 'short'}); } catch { return ym; } };
  const short = v => { const n = Math.abs(Number(v) || 0); return n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? Math.round(n / 1e3) + 'k' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(Math.round(n)); };
  function onChartMove(e) {
    const h = e.target.closest && e.target.closest('.hit'), tip = $('#crTip'); if (!tip) return;
    $('#crPage').querySelectorAll('.cr-chart .hl.on').forEach(x => x.classList.remove('on'));
    if (!h) { tip.hidden = true; return; }
    const m = ((K().outlook || {}).months || [])[Number(h.dataset.m)]; if (!m) return;
    h.nextElementSibling && h.nextElementSibling.classList.add('on');
    const box = h.closest('.cs-chart').getBoundingClientRect(), r = h.getBoundingClientRect();
    tip.innerHTML = `<b>${esc(new Date(m.month + '-01T00:00').toLocaleDateString(undefined, {month: 'long', year: 'numeric'}))}</b><br>In ${esc(m2(m.in))}${m.late_in ? ` + ${esc(m2(m.late_in))} behind` : ''}<br>Out ${esc(m2(m.out))}<br>Net <b>${esc(m2(m.in + m.late_in - m.out))}</b>`;
    tip.style.left = Math.min(box.width - 90, Math.max(90, r.left - box.left + r.width / 2)) + 'px'; tip.style.top = (e.clientY - box.top) + 'px'; tip.hidden = false;
  }
  function matchCard(compact) {
    const ps = ((K().matches || {}).proposals) || [];
    if (!ps.length) return compact ? '' : `<section class="card"><h2 class="md-h2">Found in your bank statements</h2>${empty('Nothing waiting. When you import a statement in Books & Accounts, Hoola looks for each loan\'s payments there.')}</section>`;
    const rows = ps.slice(0, compact ? 4 : 50).map(p => `<div class="cs-row cr-match"><span class="mut nw" style="width:96px">${esc(dmy(p.day))}</span>
      <span style="flex:1;min-width:0"><b>${esc(p.loan)}</b> ${p.named ? '<span class="cs-tag ok">Name matches</span>' : '<span class="cs-tag warn">Amount only</span>'}<div class="mut" style="font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(p.narration)}</div></span>
      <span class="num ${p.side === 'lent' ? 'cs-pos' : 'cs-neg'}">${p.side === 'lent' ? '+' : '−'}${esc(m2(p.amount))}</span>
      ${can() ? `<button class="btn sm" type="button" data-okmatch="${esc(p.txn)}" data-n="${esc(p.n)}">Confirm</button><button class="ib sm" type="button" data-nomatch="${esc(p.txn)}" aria-label="Not this loan">×</button>` : ''}</div>`).join('');
    return `<section class="card cr-found"><div class="cs-head"><h2 class="md-h2" style="margin:0">Found in your bank statements <span class="cs-tag ok">${esc(ps.length)}</span></h2>${compact && ps.length > 4 ? '<div class="r"><button class="btn soft sm" type="button" data-go="loans">See all</button></div>' : ''}</div>
      <div style="margin-top:6px">${rows}</div><p class="cs-note">${esc((K().matches || {}).says || '')}</p></section>`;
  }

  function pToday() {
    const k = K(), b = B(), L = b.lent || {}, M = b.borrowed || {};
    const open = appsOf().filter(a => a.status !== 'closed');
    const t = new Date(), in30 = new Date(t.getTime() + 30 * 864e5).toISOString().slice(0, 10);
    const up = (b.loans || []).filter(v => v.next_due && v.next_due <= in30).sort((a, c) => a.next_due < c.next_due ? -1 : 1).slice(0, 8);
    const upRows = up.map(v => `<div class="cs-row" data-go="loans/${esc(v.n)}" style="cursor:pointer"><span class="mut nw" style="width:92px">${esc(dmy(v.next_due))}</span><span style="flex:1;min-width:0">${esc(v.name)} ${side(v.side)}</span><span class="num ${v.side === 'lent' ? 'cs-pos' : 'cs-neg'}">${v.side === 'lent' ? '+' : '−'}${esc(m2(v.payment))}</span></div>`).join('');
    const apRows = open.slice(0, 6).map(a => { const ck = a.checklist || {}, tot = (ck.items || []).length, got = tot - (ck.missing || []).length;
      return `<div class="cs-row" data-go="apps/${esc(a.n)}" style="cursor:pointer"><span style="flex:1;min-width:0"><b>${esc(a.borrower)}</b><div class="mut" style="font-size:12.5px">${esc(money(a.amount))}${a.purpose ? ' · ' + esc(a.purpose) : ''}</div></span>
        ${tot ? `<span class="cr-prog" title="${esc(got)} of ${esc(tot)} conditions in"><span style="width:${(100 * got / tot).toFixed(0)}%"></span></span><span class="mut nw" style="font-size:12.5px">${esc(got)}/${esc(tot)}</span>` : '<span class="mut" style="font-size:12.5px">No conditions yet</span>'}</div>`; }).join('');
    const lead = L.in_arrears ? `${L.in_arrears} loan${L.in_arrears > 1 ? 's are' : ' is'} behind, ${money(L.arrears, cur(), 2)} owed to you.`
      : (M.missed || []).length ? `A payment on your own loan is late.` : (b.loans || []).length ? 'Every loan on this desk is up to date.'
      : 'Add your loans - the ones you took and the ones you gave - and Hoola keeps them on time.';
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero cr-hero">
        <div class="top">
          <div class="k"><div class="l">Owed to you</div><div class="v">${esc(money(L.outstanding || 0))}</div><div class="s">${esc(L.count || 0)} loan${L.count === 1 ? '' : 's'} you lent</div></div>
          <div class="k low${L.in_arrears ? ' bad' : ''}"><div class="l">Behind</div><div class="v">${esc(money(L.arrears || 0))}</div><div class="s">${L.in_arrears ? `${esc(L.in_arrears)} loan${L.in_arrears > 1 ? 's' : ''} · worst ${esc(L.worst_dpd)} days late` : 'nobody is late'}</div></div>
          <div class="k"><div class="l">You owe</div><div class="v">${esc(money(M.outstanding || 0))}</div><div class="s">${esc(money(M.monthly || 0, cur(), 2))} a month · ${esc(M.count || 0)} loan${M.count === 1 ? '' : 's'}</div></div>
        </div>
        ${L.count ? `<div><div class="cr-sub">How late the money owed to you is</div>${ageBar(L.buckets || {})}</div>` : ''}
      </section>
      ${matchCard(true)}
      ${(K().outlook || {}).months && ((K().outlook.total_in || 0) + (K().outlook.total_out || 0)) ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The next 12 months</h2><div class="r"><span class="mut" style="font-size:13px">${esc(m2(K().outlook.total_in))} in · ${esc(m2(K().outlook.total_out))} out</span></div></div>${outlookChart(K().outlook)}</section>` : ''}
      <div class="md-3 cs-4">
        ${kpi('Open applications', esc(open.length), open.length ? 'Waiting for the decider' : 'None open')}
        ${kpi('Conditions missing', esc(open.reduce((s, a) => s + (((a.checklist || {}).missing) || []).length, 0)), 'Across open applications')}
        ${kpi('Contacts this week', esc(k.contacts_this_week || 0), 'Planned and checked - never sent by Hoola')}
        ${kpi('APR method', esc(k.method && k.method.method ? METH[k.method.method] : 'Not set'), k.method && k.method.checked ? 'You chose it' : 'Your country\'s usual one - check this', k.method && k.method.method ? 'sm' : 'bad')}
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Payments in the next 30 days</h2>${upRows || empty('No payment is due in the next 30 days.')}
          <div style="margin-top:10px"><button class="btn soft sm" type="button" data-go="loans">Open the loan book</button></div></section>
      </div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Open applications</h2><div class="r"><button class="btn soft sm" type="button" data-go="apps">All applications</button></div></div>
        <div style="margin-top:8px">${apRows || empty('No application open. Add one on the Applications page.')}</div></section>`;
  }

  /* ---------------------------------------------------------------- borrowing */
  function aprForm() {
    const v = ST.aprIn || {amount: 20000, rate: 8, term: 36, frequency: 'monthly', fee_pct: '', fees_upfront: ''};
    const r = ST.aprRes;
    const res = !r ? '<p class="cs-note">Fill in the loan as the lender wrote it. Hoola works the APR out from the payments.</p>'
      : r.error ? `<p class="cs-note cs-neg">${esc(r.error)}</p>`
      : `<div class="cr-apr"><div><div class="l">APR</div><div class="v">${esc(pct(r.apr_pct))}</div></div>
          <div><div class="l">Cost of the loan</div><div class="v sm">${esc(m2(r.cost_of_credit))}</div></div>
          <div><div class="l">Money in your hand</div><div class="v sm">${esc(m2(r.money_received))}</div></div>
          <div><div class="l">You pay back</div><div class="v sm">${esc(m2(r.total_paid))}</div></div></div>
        <div class="cr-how">${(r.how || []).map(h => `<span>${esc(h)}</span>`).join('')}</div>
        <p class="cs-note"><b>${esc(METH[r.method] || r.method)}</b> - ${esc(r.method_from)}. ${esc(r.says)} <button class="linkbtn" type="button" data-go="settings">Change the method</button></p>`;
    return `<section class="card"><h2 class="md-h2">What a loan really costs</h2>
      <form data-form="apr" class="md-form">
        <div class="md-field"><label for="crA1">Loan amount</label><input class="in" id="crA1" name="amount" type="number" step="0.01" min="0" required value="${esc(v.amount)}"></div>
        <div class="md-field"><label for="crA2">Interest rate a year (%)</label><input class="in" id="crA2" name="rate" type="number" step="0.01" min="0" value="${esc(v.rate)}"></div>
        <div class="md-field"><label for="crA3">Number of payments</label><input class="in" id="crA3" name="term" type="number" min="1" required value="${esc(v.term)}"></div>
        <div class="md-field"><label for="crA4">How often</label><select class="in" id="crA4" name="frequency">${['monthly', 'fortnightly', 'weekly', 'quarterly', 'yearly'].map(f => `<option${f === v.frequency ? ' selected' : ''}>${f}</option>`).join('')}</select></div>
        <div class="md-field"><label for="crA5">Fee as % of the loan</label><input class="in" id="crA5" name="fee_pct" type="number" step="0.01" min="0" value="${esc(v.fee_pct)}" placeholder="0"></div>
        <div class="md-field"><label for="crA6">Fixed fees at the start</label><input class="in" id="crA6" name="fees_upfront" type="number" step="0.01" min="0" value="${esc(v.fees_upfront)}" placeholder="0"></div>
      </form>
      <div class="md-acts"><span class="mut" style="font-size:13px">Fees taken from the loan lower the money you get.</span><button class="btn" type="button" data-aprgo="1">Work it out</button></div>
      <div id="crAprOut" style="margin-top:14px">${res}</div></section>`;
  }
  function offersCard() {
    const k = K(), offers = k.offers || [];
    if (offers.length && ST.cmp === null) lazy('cmp', 'compare', {});
    const c = ST.cmp;
    const rows = !offers.length ? '' : !c ? loading() : c.error ? `<p class="cs-note cs-neg">${esc(c.error)}</p>` : (() => {
      const mx = Math.max(...c.offers.map(o => o.cost_of_credit), 1);
      return `<div class="cr-offers">${c.offers.map((o, i) => `<div class="cr-offer${i === 0 ? ' best' : ''}">
          <div class="t"><b>${esc(o.name)}</b>${i === 0 ? '<span class="cs-tag ok">Cheapest overall</span>' : ''}${can() ? `<button class="ib sm" type="button" data-unoffer="${esc(o.n)}" aria-label="Remove ${esc(o.name)}">×</button>` : ''}</div>
          <div class="nums"><div><span class="l">APR</span><b>${esc(pct(o.apr_pct))}</b></div><div><span class="l">Costs you</span><b>${esc(m2(o.cost_of_credit))}</b></div><div><span class="l">In your hand</span><b>${esc(m2(o.money_received))}</b></div></div>
          <div class="cs-bar" style="grid-template-columns:minmax(0,1fr)"><div class="tr"><span class="${i === 0 ? 'ok' : ''}" style="width:${(100 * o.cost_of_credit / mx).toFixed(1)}%"></span></div></div>
          <div class="mut" style="font-size:12.5px">${esc(money(o.amount))} over ${esc(o.term)} ${esc(o.frequency)} payments${o.rate !== undefined && o.rate !== null ? ` at ${esc(o.rate)}%` : ''}</div></div>`).join('')}</div>
        <p class="cs-note">${esc(c.says)} ${esc(c.method_from || '')}</p>`; })();
    return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Offers side by side</h2></div>
      <div style="margin-top:10px">${rows || empty('Add each offer you have. Hoola puts them on the same footing: what you really pay.')}</div>
      ${can() ? `<form data-form="offer" class="cr-grid"><input class="in wide" name="name" placeholder="Who offers it" required maxlength="60" aria-label="Who offers it"><input class="in" name="amount" type="number" step="0.01" min="0" placeholder="Amount" required aria-label="Amount"><input class="in" name="rate" type="number" step="0.01" min="0" placeholder="Rate % a year" aria-label="Rate"><input class="in" name="term" type="number" min="1" placeholder="Monthly payments" required aria-label="Payments"><input class="in" name="fee_pct" type="number" step="0.01" min="0" placeholder="Fee %" aria-label="Fee %"><input class="in" name="fees_upfront" type="number" step="0.01" min="0" placeholder="Fixed fees" aria-label="Fixed fees"><button class="btn soft" type="submit">Add offer</button></form>` : ''}</section>`;
  }
  function invoiceCard() {
    const v = ST.ifIn || {invoice: 10000, advance_pct: 80, fee_pct: 2, days: 45, discount_rate_pct: ''};
    const r = ST.ifRes;
    return `<section class="card"><h2 class="md-h2">Invoice finance</h2>
      <form data-form="invfin" class="md-form">
        <div class="md-field"><label for="crI1">Invoice amount</label><input class="in" id="crI1" name="invoice" type="number" step="0.01" min="0" required value="${esc(v.invoice)}"></div>
        <div class="md-field"><label for="crI2">Advance (% of the invoice)</label><input class="in" id="crI2" name="advance_pct" type="number" step="0.1" min="0" max="100" value="${esc(v.advance_pct)}"></div>
        <div class="md-field"><label for="crI3">Fee (% of the invoice)</label><input class="in" id="crI3" name="fee_pct" type="number" step="0.01" min="0" value="${esc(v.fee_pct)}"></div>
        <div class="md-field"><label for="crI4">Days until your customer pays</label><input class="in" id="crI4" name="days" type="number" min="1" required value="${esc(v.days)}"></div>
        <div class="md-field wide"><label for="crI5">Interest on the advance (% a year, if any)</label><input class="in" id="crI5" name="discount_rate_pct" type="number" step="0.01" min="0" value="${esc(v.discount_rate_pct)}" placeholder="0"></div>
      </form>
      <div class="md-acts"><span></span><button class="btn soft" type="button" data-ifgo="1">Work it out</button></div>
      ${!r ? '' : r.error ? `<p class="cs-note cs-neg">${esc(r.error)}</p>` : `<div class="cr-apr" style="margin-top:12px"><div><div class="l">Costs a year</div><div class="v">${esc(pct(r.cost_a_year_pct))}</div></div>
        <div><div class="l">Money now</div><div class="v sm">${esc(m2(r.money_now))}</div></div><div><div class="l">It costs</div><div class="v sm">${esc(m2(r.cost))}</div></div></div>
        <p class="cs-note">${esc(r.how)}. Simple rate a year ${esc(pct(r.simple_a_year_pct))}. ${esc(r.says)}</p>`}</section>`;
  }
  function readyCard() {
    const r = ST.ready;
    if (!r) return `<section class="card"><h2 class="md-h2">Ready to ask a lender?</h2><p class="mut" style="margin:0 0 12px;font-size:14px">Your last 12 months from your own bank statements and books - what a lender will look at, and what is missing.</p><button class="btn soft" type="button" data-ready="1">Make my readiness pack</button></section>`;
    if (r === false) return loading();
    if (r.error) return `<section class="card"><h2 class="md-h2">Ready to ask a lender?</h2><p class="cs-note cs-neg">${esc(r.error)}</p><button class="btn soft sm" type="button" data-ready="1">Try again</button></section>`;
    const f = (r.statements || {}).figures || {}, bm = (r.statements || {}).by_month || {};
    const mx = Math.max(...Object.values(bm).map(m => Math.max(m.in, m.out)), 1);
    const months = Object.entries(bm).map(([m, v]) => `<div title="${esc(m)}: in ${esc(money(v.in))}, out ${esc(money(v.out))}"><span class="pair"><b class="in" style="height:${(100 * v.in / mx).toFixed(1)}%"></b><b class="out" style="height:${(100 * v.out / mx).toFixed(1)}%"></b></span><span>${esc(m.slice(5))}</span></div>`).join('');
    return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your readiness pack</h2><div class="r"><button class="btn soft sm" type="button" data-ready="1">Make it again</button></div></div>
      <div class="md-3 cs-4" style="margin-top:12px">
        ${kpi('Money in a month', esc(money((f.average_monthly_in || {}).value)), `Over ${(f.months_read || {}).value || 0} months`)}
        ${kpi('Money out a month', esc(money((f.average_monthly_out || {}).value)), 'On your statements')}
        ${kpi('Lowest balance', esc(money((f.lowest_balance || {}).value)), 'From the balance you started with')}
        ${kpi('Returned items', esc((f.bounced_items || {}).value || 0), 'Bounced or unpaid', (f.bounced_items || {}).value ? 'bad' : 'ok')}
      </div>
      ${months ? `<div class="cr-months">${months}</div><div class="cs-legend"><span><i class="in"></i>Money in</span><span><i class="out"></i>Money out</span></div>` : ''}
      ${r.books ? `<p class="cs-note">From your books for the same months: income ${esc(m2(r.books.income))}, costs ${esc(m2(r.books.costs))}, profit <b>${esc(m2(r.books.profit))}</b>.</p>` : ''}
      <div class="md-2" style="margin-top:14px;align-items:start">
        <div><div class="cr-sub">Still missing</div>${(r.gaps || []).map(g => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(cap(g))}</span></div>`).join('') || empty('Nothing missing from your statements and books.')}</div>
        <div><div class="cr-sub">Papers a lender asks for</div>${(r.papers_a_lender_asks_for || []).map(p => `<div class="cs-row"><span class="cr-chk"></span><span>${esc(cap(p))}</span></div>`).join('')}</div>
      </div><p class="cs-note">${esc(r.says)}</p></section>`;
  }
  function pBorrow() {
    return `<div><h1 class="sd-h">Borrowing</h1><p class="lead">The real cost of a loan, by the method your country uses, and every offer on the same footing.</p></div>
      <div class="md-2" style="align-items:start">${aprForm()}${offersCard()}</div>
      <div class="md-2" style="align-items:start">${invoiceCard()}${readyCard()}</div>`;
  }

  /* ---------------------------------------------------------------- applications */
  function pApps() {
    if (ST.arg) return appOne(ST.arg);
    const apps = appsOf();
    const card = a => { const ck = a.checklist || {}, tot = (ck.items || []).length, got = tot - (ck.missing || []).length, late = (ck.items || []).filter(i => i.late).length;
      return `<button class="cr-app" type="button" data-go="apps/${esc(a.n)}">
        <div class="t"><b>${esc(a.borrower)}</b>${a.status === 'closed' ? '' : late ? `<span class="cs-tag bad">${esc(late)} late</span>` : tot && got === tot ? '<span class="cs-tag ok">Papers in</span>' : ''}</div>
        <div class="v">${esc(money(a.amount))}</div>
        <div class="mut" style="font-size:13px">${esc(a.purpose || 'No purpose given')}${a.rate !== null && a.rate !== undefined ? ` · ${esc(a.rate)}% over ${esc(a.term)} months` : ''}</div>
        <div class="f"><span>${esc(Object.keys(a.figures || {}).length)} figures</span><span>${esc(a.rows_count || 0)} statement rows</span><span>${tot ? `${esc(got)}/${esc(tot)} conditions` : 'No conditions'}</span></div>
        ${a.status === 'closed' ? `<div class="mut" style="font-size:12.5px">${esc(a.decided_by)}: ${esc(a.outcome)}</div>` : ''}</button>`; };
    const open = apps.filter(a => a.status !== 'closed'), done = apps.filter(a => a.status === 'closed');
    const col = (key, title, list, note) => `<div class="cr-col"><div class="cr-colh"><b>${esc(title)}</b><span class="cs-tag">${esc(list.length)}</span></div>${list.map(card).join('') || `<div class="cr-colempty">${esc(note)}</div>`}</div>`;
    return `<div class="cs-head"><div><h1 class="sd-h">Applications</h1><p class="lead" style="margin-top:4px">Each borrower's figures with their sources, their statement, your rules, the memo and the key facts. The decision is the named person's.</p></div></div>
      ${can() ? `<section class="card"><h2 class="md-h2">New application</h2><form data-form="app" class="cs-form" style="margin-top:0"><input class="in" name="borrower" placeholder="Borrower" required maxlength="80"><input class="in sm2" name="amount" type="number" step="0.01" min="0" placeholder="Amount asked" required><input class="in" name="purpose" placeholder="What it is for" maxlength="160"><input class="in sm2" name="rate" type="number" step="0.01" min="0" placeholder="Rate % (proposed)"><input class="in sm2" name="term" type="number" min="1" placeholder="Months"><button class="btn" type="submit">Add</button></form></section>` : ''}
      <div class="cr-board">${col('gathering', 'Gathering papers', open.filter(a => a.stage !== 'with_decider'), 'Nothing being gathered')}${col('with_decider', 'With the decider', open.filter(a => a.stage === 'with_decider'), 'Nothing waiting for a decision')}${col('decided', 'Decided', done, 'No decision recorded yet')}</div>`;
  }
  function appOne(n) {
    if (ST.appFor !== String(n)) { ST.app = null; ST.appFor = String(n); }
    if (ST.app === null) { lazy('app', 'app', {n: Number(n)}); return loading(); }
    if (ST.app === false) return loading();
    const a = ST.app;
    if (a.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(a.error)}</p><button class="btn soft sm" type="button" data-go="apps" style="margin-top:10px">Back</button></section>`;
    const closed = a.status === 'closed', ro = can() && !closed;
    const memo = a.memo || null, rules = a.rules, kfs = a.kfs, ck = a.checklist, an = a.analysis;
    const figs = Object.entries(a.figures || {}).map(([k, v]) => `<tr><td>${esc(figName(k))}</td><td class="num">${esc(m2(v.value))}</td><td class="mut">${esc(v.source)}</td><td>${ro ? `<button class="ib sm" type="button" data-unfig="${esc(k)}" aria-label="Remove ${esc(k)}">×</button>` : ''}</td></tr>`).join('');
    const sug = ((ST.d && ST.d.figures_suggested) || []).filter(x => !(a.figures || {})[x]);
    const ratios = memo && !memo.error ? Object.entries(memo.ratios || {}).map(([k, v]) => { const bad = (memo.policy_flags || []).some(f => f.startsWith(k + ' '));
      return `<div class="cr-ratio${bad ? ' bad' : ''}"><div class="l">${esc(RATIO_NAME[k] || cap(k.replace(/_/g, ' ')))}</div><div class="v">${esc(v.value)}${v.unit === '%' ? '%' : '×'}</div><div class="s">${esc(figName(v.from[0]))} ÷ ${esc(figName(v.from[1]))} · ${esc(v.sources.join(', '))}</div>${bad ? '<span class="cs-tag bad">Outside your policy</span>' : ''}</div>`; }).join('') : '';
    const srcs = memo && !memo.error ? Object.entries(memo.sources || {}).map(([k, v]) => `<div class="cs-row"><b style="width:34px">${esc(k)}</b><span>${esc(v)}</span></div>`).join('') : '';
    const hits = rules && !rules.error ? (rules.rule_hits || []).map(h => `<div class="cs-row"><span class="cs-dot${h.severity === 'stop' ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(h.code)}</b> needs ${esc(h.field)} ${esc(h.required)} - is ${esc(h.actual)}</span><span class="cs-tag ${h.severity === 'stop' ? 'bad' : 'warn'}">${esc(SEV[h.severity] || h.severity)}</span></div>`).join('') : '';
    const miss = rules && !rules.error ? (rules.missing_inputs || []).map(m => `<span class="cs-tag">${esc(m.field)}</span>`).join(' ') : '';
    const fields = Object.entries(a.applicant || {}).map(([k, v]) => `<span class="pill">${esc(k)}: ${esc(v)}${ro ? `<button type="button" data-unfield="${esc(k)}" aria-label="Remove">×</button>` : ''}</span>`).join(' ');
    const conds = (ck && ck.items || []).map(i => `<div class="cs-row"><span class="cr-st ${esc(i.status)}">${i.status === 'received' ? '✓' : i.status === 'waived' ? '–' : '!'}</span><span style="flex:1;min-width:0">${esc(i.name)}${i.waived_by ? `<div class="mut" style="font-size:12.5px">Waived by ${esc(i.waived_by)}</div>` : ''}${i.due ? `<div class="mut${i.late ? ' cs-neg' : ''}" style="font-size:12.5px">Due ${esc(dmy(i.due))}${i.late ? ' · late' : ''}</div>` : ''}</span>
      ${ro ? `<select class="in sm" data-cond="${esc(i.name)}" aria-label="Status of ${esc(i.name)}">${['missing', 'received', 'waived'].map(s => `<option${s === i.status ? ' selected' : ''}>${s}</option>`).join('')}</select><button class="ib sm" type="button" data-uncond="${esc(i.name)}" aria-label="Remove">×</button>` : `<span class="cs-tag">${esc(i.status)}</span>`}</div>`).join('');
    const bm = an && !an.error ? an.by_month || {} : {};
    const mx = Math.max(...Object.values(bm).map(m => Math.max(m.in, m.out)), 1);
    const months = Object.entries(bm).map(([m, v]) => `<div title="${esc(m)}"><span class="pair"><b class="in" style="height:${(100 * v.in / mx).toFixed(1)}%"></b><b class="out" style="height:${(100 * v.out / mx).toFixed(1)}%"></b></span><span>${esc(m.slice(2))}</span></div>`).join('');
    const af = an && !an.error ? an.figures || {} : {};
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="apps">← Applications</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(a.borrower)}</h1><p class="lead" style="margin-top:4px">${esc(money(a.amount, cur(), 2))}${a.purpose ? ' for ' + esc(a.purpose) : ''}${a.rate !== null && a.rate !== undefined ? ` · proposed ${esc(a.rate)}% over ${esc(a.term)} months${a.requested_emi ? `, ${esc(m2(a.requested_emi))} a month` : ''}` : ''}</p></div>
        <div class="r">${memo && !memo.error ? `<button class="btn soft sm" type="button" data-dl="memo">Memo PDF</button><button class="btn soft sm" type="button" data-dl="memo_md">Memo text</button>` : ''}${kfs && !kfs.error ? '<button class="btn soft sm" type="button" data-dl="kfs">Key facts</button>' : ''}<button class="btn soft sm" type="button" data-ask="${esc('Application: ' + a.borrower)}">Ask about it</button></div></div>
      <section class="card cr-stagebar"><div class="cs-seg" role="group" aria-label="Stage">${[['gathering', 'Gathering papers'], ['with_decider', 'With the decider'], ['decided', 'Decided']].map(([k, l]) => `<button type="button" ${k === 'decided' ? 'disabled' : `data-stage="${k}"`} aria-pressed="${(closed ? 'decided' : (a.stage || 'gathering')) === k}"${!can() || closed ? ' disabled' : ''}>${esc(l)}</button>`).join('')}</div>
        <span class="mut" style="font-size:13px">${closed ? 'Recorded below.' : a.stage === 'with_decider' ? 'Waiting for the credit officer or committee.' : 'Collecting figures, the statement and the conditions.'}</span>
        ${ro ? '<button class="btn soft sm" type="button" data-terms="1">Change the terms</button>' : ''}</section>
      ${ro && ST.terms ? `<section class="card"><h2 class="md-h2">Proposed terms</h2><form data-form="terms" class="cr-grid"><input class="in" name="amount" type="number" step="0.01" min="0" value="${esc(a.amount)}" aria-label="Amount" placeholder="Amount" required><input class="in" name="rate" type="number" step="0.01" min="0" value="${esc(a.rate ?? '')}" aria-label="Rate" placeholder="Rate % a year"><input class="in" name="term" type="number" min="1" value="${esc(a.term ?? '')}" aria-label="Months" placeholder="Months"><input class="in" name="fee_pct" type="number" step="0.01" min="0" value="${esc(a.fee_pct ?? '')}" aria-label="Fee %" placeholder="Fee %"><input class="in" name="purpose" value="${esc(a.purpose || '')}" aria-label="Purpose" placeholder="What it is for" maxlength="160"><button class="btn" type="submit">Save</button></form></section>` : ''}
      ${closed ? `<section class="md-alert" style="border-color:var(--line);background:var(--soft);color:var(--ink)">${svg(IC.info)}<div><div class="t">Decided by ${esc(a.decided_by)}</div><div class="s">${esc(a.outcome)} · recorded by ${esc(a.closed_by)} on ${esc(a.closed_on)}</div></div>${can() ? '<button class="btn soft sm" type="button" data-reopen="1">Reopen</button>' : ''}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Figures and where they come from</h2>
          ${figs ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Figure</th><th class="num">Value</th><th>Source</th><th></th></tr></thead><tbody>${figs}</tbody></table></div>` : empty('A figure with no source is not used. Add each one with the document and page it is on.')}
          ${ro ? `<form data-form="afig" class="cs-form"><input class="in sm2" name="name" placeholder="Figure" required list="crFigs" maxlength="40"><datalist id="crFigs">${sug.map(x => `<option value="${esc(x)}">${esc(figName(x))}</option>`).join('')}</datalist><input class="in sm2" name="value" type="number" step="0.01" placeholder="Value" required><input class="in" name="source" placeholder="Source - e.g. 2025 accounts, page 3" required maxlength="120"><button class="btn soft sm" type="submit">Add</button></form>` : ''}</section>
        <section class="card"><h2 class="md-h2">Ratios</h2>${ratios ? `<div class="cr-ratios">${ratios}</div>` : empty('Ratios appear once the figures they divide are in (for example EBITDA and debt service).')}
          ${memo && !memo.error && (memo.policy_flags || []).length ? `<p class="cs-note cs-neg">${esc(memo.policy_flags.join('; '))}</p>` : ''}
          ${srcs ? `<div class="cr-sub" style="margin-top:12px">Sources</div>${srcs}` : ''}</section>
      </div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The borrower's statement</h2>${an && !an.error ? `<div class="r"><span class="mut" style="font-size:13px">${esc(a.rows_count)} rows</span></div>` : ''}</div>
        ${an && !an.error ? `<div class="md-3 cs-4" style="margin-top:12px">${kpi('Money in a month', esc(money((af.average_monthly_in || {}).value)), `${((af.average_monthly_in || {}).rows || []).length} rows`)}${kpi('Debt payments a month', esc(money((af.regular_debt_payments_monthly || {}).value)), `${((af.regular_debt_payments_monthly || {}).rows || []).length} rows seen in 2+ months`)}${kpi('Lowest balance', esc(money((af.lowest_balance || {}).value)), 'From zero at the start')}${kpi('Returned items', esc((af.bounced_items || {}).value || 0), 'Bounced or unpaid', (af.bounced_items || {}).value ? 'bad' : 'ok')}</div>
          ${months ? `<div class="cr-months">${months}</div>` : ''}${(an.bounced || []).length ? `<div class="cr-sub" style="margin-top:12px">Returned items</div>${an.bounced.map(x => `<div class="cs-row"><span class="mut nw" style="width:92px">${esc(dmy(x.day))}</span><span style="flex:1">${esc(x.narration)}</span><span class="num cs-neg">${esc(m2(x.amount))}</span></div>`).join('')}` : ''}<p class="cs-note">${esc(an.says)}</p>`
          : an && an.error ? `<p class="cs-note cs-neg">${esc(an.error)}</p>` : `<p class="mut" style="margin:8px 0 0;font-size:14px">Paste the borrower's statement as date, narration, amount (money out as minus), or drop the file in the chat.</p>`}
        ${ro ? `<form data-form="rows" style="margin-top:12px"><textarea class="in" name="rows_csv" rows="4" placeholder="2026-06-01, SALES, 9000&#10;2026-06-05, LOAN EMI, -800" style="width:100%;font-family:var(--mono, monospace);font-size:13px"></textarea><div class="md-acts" style="margin-top:8px"><span class="mut" style="font-size:13px">Replaces the rows kept for this application. <label class="linkbtn">Choose a CSV file<input type="file" accept=".csv,.txt,text/csv,text/plain" data-rowsfile="1" hidden></label></span><button class="btn soft sm" type="submit">Read the statement</button></div></form>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Your rules</h2>
          ${rules === null ? empty('No underwriting rules yet - add yours in Settings.') : rules.error ? `<p class="cs-note cs-neg">${esc(rules.error)}</p>` : (hits || '<div class="cs-row"><span class="cr-st received">✓</span><span>Every rule that could be run is met.</span></div>')}
          ${miss ? `<p class="cs-note">Not known yet: ${miss}</p>` : ''}
          <div class="cr-sub" style="margin-top:12px">Details from the application form</div><div style="display:flex;gap:6px;flex-wrap:wrap">${fields || '<span class="mut" style="font-size:13px">None yet</span>'}</div>
          ${ro ? `<form data-form="afield" class="cs-form"><input class="in sm2" name="field" placeholder="months_trading" required maxlength="40"><input class="in sm2" name="value" placeholder="Value" required maxlength="60"><button class="btn soft sm" type="submit">Add</button></form>` : ''}
          <p class="cs-note">A rule on religion, caste, gender, race, marital status, disability, area or surname is refused.</p></section>
        <section class="card"><h2 class="md-h2">Conditions before the money goes out</h2>
          ${conds || empty('No conditions yet - add each document or condition the decider needs.')}
          ${ck && ck.says ? `<p class="cs-note">${esc(ck.says)}</p>` : ''}
          ${ro ? `<form data-form="cond" class="cs-form"><input class="in" name="name" placeholder="Signed guarantee" required maxlength="120"><input class="in sm2" type="date" name="due" aria-label="Due"><button class="btn soft sm" type="submit">Add</button></form>` : ''}</section>
      </div>
      ${kfs && !kfs.error ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Key facts draft</h2><div class="r"><span class="cs-tag">APR ${esc(pct((kfs.apr || {}).apr_pct))} · ${esc(METH[(kfs.apr || {}).method] || '')}</span></div></div><div class="cr-md textmd">${window.HoolaMD ? HoolaMD.render(S(kfs.kfs_markdown).replace(/^# .*\n/, '').replace(/\n\|/, '\n\n|').replace(/\|\n([^|\n])/, '|\n\n$1'), false) : `<pre>${esc(kfs.kfs_markdown)}</pre>`}</div><p class="cs-note">${esc(kfs.not_checked)} ${esc(kfs.decider)}</p></section>`
        : `<section class="card"><h2 class="md-h2">Key facts draft</h2>${empty(kfs && kfs.error ? kfs.error : 'Give the proposed rate and term (and choose an APR method in Settings) to draft the key facts.')}</section>`}
      ${can() && !closed ? `<section class="card"><h2 class="md-h2">Record the decision</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Hoola gives no score and does not decide. When the credit officer or committee decides, write down who and what, in their words.</p>
        <form data-form="decide" class="cs-form" style="margin-top:0"><input class="in" name="decided_by" placeholder="Who decided (name or committee)" required maxlength="80"><input class="in" name="outcome" placeholder="What they decided" required maxlength="160"><button class="btn soft sm" type="submit">Record it</button></form>
        <div class="md-acts"><span></span><button class="btn soft sm" type="button" data-unapp="1">Remove this application</button></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- the loan book */
  function pLoans() {
    if (ST.arg) return loanOne(ST.arg);
    const b = B(), all = b.loans || [], q = ST.lq.trim().toLowerCase();
    const loans = all.filter(v => (ST.lf === 'all' || (ST.lf === 'late' ? v.arrears > 0 : v.side === ST.lf)) && (!q || S(v.name).toLowerCase().includes(q)));
    const cnt = {all: all.length, lent: all.filter(v => v.side === 'lent').length, borrowed: all.filter(v => v.side === 'borrowed').length, late: all.filter(v => v.arrears > 0).length};
    const rows = loans.slice().sort((x, y) => (y.days_past_due - x.days_past_due) || ((x.next_due || '9') < (y.next_due || '9') ? -1 : 1))
      .map(v => `<tr class="cs-wk${v.days_past_due > 30 ? ' under' : ''}" data-go="loans/${esc(v.n)}"><td><b>${esc(v.name)}</b><div>${side(v.side)}</div></td><td class="num">${esc(m2(v.outstanding))}</td><td class="num">${esc(m2(v.payment))}</td>
        <td class="num ${v.arrears ? 'cs-neg' : ''}">${v.arrears ? esc(m2(v.arrears)) : '—'}</td><td>${dpdTag(v)}</td><td class="nw">${esc(dmy(v.next_due))}</td><td class="nw mut">${esc(v.term - v.instalments_left)} / ${esc(v.term)}</td></tr>`).join('');
    return `<div class="cs-head"><div><h1 class="sd-h">Loan book</h1><p class="lead" style="margin-top:4px">What was due against what was paid, for every loan you gave and every loan you took.</p></div>
        <div class="r">${all.length ? '<button class="btn soft sm" type="button" data-dl="book">Download CSV</button>' : ''}</div></div>
      ${matchCard(false)}
      ${all.length ? `<div class="cr-filter"><div class="cs-seg" role="group" aria-label="Show">${[['all', 'All'], ['lent', 'You lent'], ['borrowed', 'You owe'], ['late', 'Behind']].map(([k, l]) => `<button type="button" data-lf="${k}" aria-pressed="${ST.lf === k}">${esc(l)} <span class="mut">${esc(cnt[k])}</span></button>`).join('')}</div><input class="in" type="search" id="crLq" placeholder="Find a loan" value="${esc(ST.lq)}" aria-label="Find a loan"></div>` : ''}
      <section class="card tight"><div style="overflow-x:auto"><table class="tb"><thead><tr><th>Loan</th><th class="num">Still owed</th><th class="num">A month</th><th class="num">Behind</th><th>Status</th><th>Next due</th><th>Paid</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="7" class="mut">${all.length ? 'No loan matches.' : 'No loans yet.'}</td></tr>`}</tbody></table></div></section>
      ${can() ? `<section class="card"><h2 class="md-h2">Add a loan</h2><form data-form="loan" class="md-form">
        <div class="md-field"><label for="crL1">Borrower (or, for your loan, the lender)</label><input class="in" id="crL1" name="name" required maxlength="80"></div>
        <div class="md-field"><label for="crL2">Which side</label><select class="in" id="crL2" name="side"><option value="lent">You lent it</option><option value="borrowed">You owe it</option></select></div>
        <div class="md-field"><label for="crL3">Amount</label><input class="in" id="crL3" name="amount" type="number" step="0.01" min="0" required></div>
        <div class="md-field"><label for="crL4">Interest rate a year (%)</label><input class="in" id="crL4" name="rate" type="number" step="0.01" min="0"></div>
        <div class="md-field"><label for="crL5">Number of monthly payments</label><input class="in" id="crL5" name="term" type="number" min="1" max="600" required></div>
        <div class="md-field"><label for="crL6">First payment due</label><input class="in" id="crL6" name="start" type="date" required></div>
        <div class="md-field"><label for="crL7">Monthly payment (if the agreement fixes it)</label><input class="in" id="crL7" name="payment" type="number" step="0.01" min="0" placeholder="Worked out from the rate"></div>
        <div class="md-field"><label for="crL8">Borrower's time zone</label><input class="in" id="crL8" name="tz" placeholder="Europe/London" maxlength="60"></div>
      </form><div class="md-acts"><span class="mut" style="font-size:13px">Monthly loans. Payments you receive or make are recorded on the loan.</span><button class="btn" type="button" data-addloan="1">Add the loan</button></div></section>` : ''}`;
  }
  function schedCard(v) {
    if (ST.schedFor !== String(v.n)) { ST.sched = null; ST.schedFor = String(v.n); ST.schedAll = false; }
    if (ST.sched === null) { lazy('sched', 'schedule', {n: Number(v.n)}); return `<section class="card"><h2 class="md-h2">Repayment schedule</h2>${loading()}</section>`; }
    if (!ST.sched || ST.sched.error) return `<section class="card"><h2 class="md-h2">Repayment schedule</h2>${empty((ST.sched && ST.sched.error) || 'Working it out…')}</section>`;
    const rows = ST.sched.rows || [], firstOpen = Math.max(0, rows.findIndex(r => r.status !== 'paid'));
    const show = ST.schedAll ? rows : rows.slice(Math.max(0, firstOpen - 2), Math.max(0, firstOpen - 2) + 8);
    const SAY = {paid: ['ok', 'Paid'], part: ['warn', 'Part paid'], late: ['bad', 'Late'], upcoming: ['', 'To come']};
    const tot = rows.reduce((a, r) => a + r.interest, 0);
    return `<section class="card tight"><div class="cs-head" style="padding:16px 18px 0"><h2 class="md-h2" style="margin:0">Repayment schedule</h2><div class="r"><span class="mut" style="font-size:13px">Interest over the loan ${esc(m2(tot))}</span></div></div>
      <div style="overflow-x:auto;margin-top:8px"><table class="tb"><thead><tr><th>#</th><th>Due</th><th class="num">Payment</th><th class="num">Interest</th><th class="num">Principal</th><th class="num">Balance after</th><th>Status</th></tr></thead><tbody>
      ${show.map(r => `<tr class="${r.status === 'late' ? 'cr-late' : ''}"><td class="mut">${esc(r.k)}</td><td class="nw">${esc(dmy(r.due))}</td><td class="num">${esc(m2(r.payment))}</td><td class="num mut">${esc(m2(r.interest))}</td><td class="num">${esc(m2(r.principal))}</td><td class="num">${esc(m2(r.balance))}</td><td><span class="cs-tag ${SAY[r.status][0]}">${esc(SAY[r.status][1])}${r.status === 'part' ? ' · ' + esc(m2(r.paid)) : ''}</span></td></tr>`).join('')}
      </tbody></table></div>${rows.length > show.length || ST.schedAll ? `<div style="padding:10px 18px 16px"><button class="btn soft sm" type="button" data-schedall="1">${ST.schedAll ? 'Show fewer' : `Show all ${esc(rows.length)} payments`}</button></div>` : ''}</section>`;
  }
  function loanOne(n) {
    const v = loanOf(n);
    if (!v) return `<section class="card"><p style="margin:0">That loan is not on this desk.</p><button class="btn soft sm" type="button" data-go="loans" style="margin-top:10px">Back</button></section>`;
    const done = v.term - v.instalments_left, lent = v.side === 'lent';
    const pays = (v.paid || []).map((p, i) => `<div class="cs-row"><span class="mut nw" style="width:100px">${esc(dmy(p.date))}</span><span style="flex:1" class="mut">${esc(S(p.by).replace(/\s*<[^>]*>$/, ''))}</span><span class="num cs-pos">${esc(m2(p.amount))}</span>${can() ? `<button class="ib sm" type="button" data-unpay="${esc(i)}" aria-label="Remove this payment">×</button>` : ''}</div>`).reverse().join('');
    const hist = v.dpd_history || [], hmx = Math.max(...hist, 30);
    const hbars = hist.map((d, i) => `<div><em>${esc(d)}</em><span class="pair"><b class="${dpdCls(d)}" style="height:${Math.max(3, 100 * d / hmx).toFixed(1)}%"></b></span><span>${i === hist.length - 1 ? 'Now' : esc((hist.length - 1 - i) + ' mo ago')}</span></div>`).join('');
    const log = ((K().contacts || {}).log || []).filter(c => S(c.borrower).toLowerCase() === S(v.name).toLowerCase());
    const c = ST.coll && ST.coll.n === String(v.n) ? ST.coll : null;
    const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 16);
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="loans">← Loan book</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(v.name)} ${side(v.side)}</h1><p class="lead" style="margin-top:4px">${esc(money(v.amount, cur(), 2))} over ${esc(v.term)} months${v.rate ? ` at ${esc(v.rate)}%` : ''} · first due ${esc(dmy(v.start))}</p></div>
        <div class="r"><button class="btn soft sm" type="button" data-dl="loan">Statement PDF</button><button class="btn soft sm" type="button" data-ask="${esc('Loan: ' + v.name)}">Ask about it</button></div></div>
      <section class="cs-hero cr-hero"><div class="top">
        <div class="k"><div class="l">Still owed</div><div class="v">${esc(m2(v.outstanding))}</div><div class="s">principal, after the payments made</div></div>
        <div class="k low${v.arrears ? ' bad' : ''}"><div class="l">Behind</div><div class="v">${esc(m2(v.arrears))}</div><div class="s">${v.days_past_due ? `${esc(v.days_past_due)} days past due · since ${esc(dmy(v.oldest_unpaid_due))}` : 'up to date'}</div></div>
        <div class="k"><div class="l">Next due</div><div class="v">${esc(m2(v.payment))}</div><div class="s">${esc(dmy(v.next_due))}</div></div></div>
        <div><div class="cr-sub">${esc(done)} of ${esc(v.term)} payments due so far · ${esc(m2(v.paid_so_far))} paid of ${esc(m2(v.due_so_far))}</div><div class="cr-age"><span class="${v.arrears ? 'warn' : 'ok'}" style="width:${(100 * done / v.term).toFixed(1)}%"></span></div></div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Payments ${lent ? 'received' : 'made'}</h2>${pays || empty('None recorded yet.')}
          ${can() ? `<form data-form="pay" class="cs-form"><input class="in sm2" name="amount" type="number" step="0.01" min="0" placeholder="Amount" required value="${esc(v.payment)}"><input class="in sm2" type="date" name="date" value="${esc(new Date().toISOString().slice(0, 10))}" required><button class="btn soft sm" type="submit">Record payment</button></form><p class="cs-note">Only money that has already moved - from your bank statement. Hoola pays and collects nothing.</p>` : ''}</section>
        <section class="card"><h2 class="md-h2">Days past due, month by month</h2>${hist.length ? `<div class="cr-months dpd">${hbars}</div>` : empty('Too early to show.')}
          ${v.rising ? '<p class="cs-note cs-neg">Getting worse: more days past due than at the last month-end.</p>' : ''}</section>
      </div>
      ${schedCard(v)}
      ${lent ? `<section class="card"><h2 class="md-h2">Before you contact ${esc(v.name)}</h2><p class="mut" style="margin:0 0 12px;font-size:14px">Hoola checks the contact against your contact rules (and its own floor): the hour where the borrower lives, how often, the channel, the words. An allowed contact is logged as planned - the person collecting sends it.</p>
        ${can() ? `<form data-form="collect" class="md-form">
          <div class="md-field"><label for="crC1">Channel</label><select class="in" id="crC1" name="channel">${['call', 'sms', 'email', 'letter', 'whatsapp'].map(x => `<option>${x}</option>`).join('')}</select></div>
          <div class="md-field"><label for="crC2">When (the borrower's local time)</label><input class="in" id="crC2" name="when" type="datetime-local" value="${esc(nowLocal)}" required></div>
          <div class="md-field"><label for="crC3">Their time zone</label><input class="in" id="crC3" name="tz" value="${esc(v.tz || '')}" placeholder="Europe/London" required></div>
          <div class="md-field"><label for="crC4">Who</label><select class="in" id="crC4" name="to"><option value="borrower">The borrower</option><option value="family">Family or friends</option><option value="employer">Their employer</option></select></div>
          <div class="md-field wide"><label for="crC5">What you will say</label><textarea class="in" id="crC5" name="message" rows="2" maxlength="600" placeholder="Hello, a payment of ... was due on ... Can we agree a date?"></textarea></div>
        </form><div class="md-acts"><label class="mut" style="font-size:13px;display:flex;gap:6px;align-items:center"><input type="checkbox" name="legal_stage" id="crLegal"> The account is at the legal stage</label><button class="btn" type="button" data-collect="${esc(v.n)}">Check this contact</button></div>` : ''}
        ${c ? (c.error ? `<div class="cr-verdict bad"><b>Not allowed</b><span>${esc(c.error.replace(/^Refused - this contact would break the contact rules: /, ''))}</span></div>` : `<div class="cr-verdict ok"><b>Allowed</b><span>${esc(c.says)}</span></div>`) : ''}
        ${log.length ? `<div class="cr-sub" style="margin-top:14px">Contacts logged</div>${log.slice(0, 10).map(x => `<div class="cs-row"><span class="mut nw" style="width:150px">${esc(x.when.replace('T', ' '))}</span><span style="flex:1">${esc(x.channel)}</span><span class="mut">${esc(x.tz)}</span></div>`).join('')}` : ''}</section>` : ''}
      ${can() ? `<section class="card"><h2 class="md-h2">Change this loan</h2><form data-form="editloan" class="md-form">
        <div class="md-field"><label for="crE1">Interest rate a year (%)</label><input class="in" id="crE1" name="rate" type="number" step="0.01" min="0" value="${esc(v.rate || '')}"></div>
        <div class="md-field"><label for="crE2">Borrower's time zone</label><input class="in" id="crE2" name="tz" value="${esc(v.tz || '')}" placeholder="Europe/London"></div>
        ${lent ? `<div class="md-field"><label for="crE3">PD - chance of default in 12 months (0 to 1)</label><input class="in" id="crE3" name="pd" type="number" step="0.0001" min="0" max="1" value="${esc(v.pd ?? '')}" placeholder="0.02"></div>
        <div class="md-field"><label for="crE4">LGD - share lost if it defaults (0 to 1)</label><input class="in" id="crE4" name="lgd" type="number" step="0.01" min="0" max="1" value="${esc(v.lgd ?? '')}" placeholder="0.45"></div>
        <div class="md-field wide"><label for="crE5">Lifetime PD (for stage 2, if you have it)</label><input class="in" id="crE5" name="pd_lifetime" type="number" step="0.0001" min="0" max="1" value="${esc(v.pd_lifetime ?? '')}"></div>` : ''}
      </form><div class="md-acts"><button class="btn soft sm" type="button" data-unloan="${esc(v.n)}">Remove this loan</button><button class="btn" type="button" data-editloan="${esc(v.n)}">Save</button></div>
      ${lent ? '<p class="cs-note">PD and LGD are your own figures (your model or your risk team\'s). Hoola does not guess them.</p>' : ''}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- risk */
  function pRisk() {
    const b = B(), lent = (b.loans || []).filter(v => v.side === 'lent');
    if (!lent.length) return `<div><h1 class="sd-h">Risk</h1><p class="lead">Early-warning signals and the ECL working paper, for the loans you gave.</p></div><section class="card">${empty('No loan you lent is on this desk yet. Add one in the loan book.')}</section>`;
    if (ST.risk === null) { lazy('risk', 'risk', {}); return loading(); }
    if (ST.risk === false) return loading();
    const r = ST.risk;
    if (r.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(r.error)}</p></section>`;
    const ews = (r.ews || []).map(x => `<div class="cr-ews"><div class="t"><b>${esc(x.name)}</b><button class="btn soft sm" type="button" data-go="loans/${esc(x.n)}">Open</button></div>${x.signals.map(s => `<div class="cs-row"><span class="cs-dot${/rising|arrears/.test(s.signal) ? ' bad' : ''}"></span><span style="flex:1">${esc(cap(s.signal))}</span><span class="mut">${esc(s.detail)}</span></div>`).join('')}</div>`).join('');
    const e = r.ecl;
    const stages = e ? [['stage1', 'Stage 1', 'Performing'], ['stage2', 'Stage 2', 'Risen a lot'], ['stage3', 'Stage 3', 'In default']] : [];
    const tot = e ? Math.max(e.total_ecl, 0.01) : 1;
    return `<div><h1 class="sd-h">Risk</h1><p class="lead">Signals to look at and the ECL working paper - not a classification. The provision is the risk committee's figure.</p></div>
      <div class="md-3 cs-4">
        ${kpi('Loans to watch', esc((r.ews || []).length), 'With at least one signal', (r.ews || []).length ? 'bad' : 'ok')}
        ${kpi('Expected credit loss', e ? esc(m2(e.total_ecl)) : '—', e ? 'Working paper' : 'Needs PD and LGD')}
        ${kpi('Owed to you', esc(money((b.lent || {}).outstanding)), `${lent.length} loans`)}
        ${kpi('Without PD / LGD', esc((r.needs_pd_lgd || []).length), 'Not in the ECL yet', (r.needs_pd_lgd || []).length ? 'bad' : '')}
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Early warning</h2>${ews || empty('No signal on any loan.')}<p class="cs-note">${esc(r.says)}</p></section>
        <section class="card"><h2 class="md-h2">ECL working paper</h2>
          ${e ? `<div class="cr-stages">${stages.map(([k, l, s]) => `<div><div class="l">${esc(l)} <span class="mut">· ${esc(s)}</span></div><div class="v">${esc(m2(e.by_stage[k]))}</div><div class="cs-bar" style="grid-template-columns:minmax(0,1fr)"><div class="tr"><span class="${k === 'stage3' ? 'bad' : k === 'stage2' ? 'warn' : 'ok'}" style="width:${(100 * e.by_stage[k] / tot).toFixed(1)}%"></span></div></div></div>`).join('')}</div>
            <div style="overflow-x:auto;margin-top:12px"><table class="tb"><thead><tr><th>Loan</th><th>Stage</th><th class="num">Exposure</th><th class="num">PD used</th><th class="num">LGD</th><th class="num">ECL</th></tr></thead><tbody>${e.rows.map(x => `<tr><td>${esc(x.id)}</td><td>${esc(x.stage)}</td><td class="num">${esc(m2(x.ead))}</td><td class="num">${esc(x.pd_used)}</td><td class="num">${esc(x.lgd)}</td><td class="num">${esc(m2(x.ecl))}</td></tr>`).join('')}</tbody></table></div>
            ${(e.flags || []).length ? `<p class="cs-note cs-neg">${esc(e.flags.join(' '))}</p>` : ''}<p class="cs-note">${esc(e.method)} ${esc(e.not_checked)}</p>`
            : empty('Give each loan its PD and LGD (on the loan page) to make the working paper.')}
          ${(r.needs_pd_lgd || []).length ? `<div class="cr-sub" style="margin-top:12px">Needs PD and LGD</div>${r.needs_pd_lgd.map(x => `<div class="cs-row"><span style="flex:1">${esc(x.name)}</span><button class="btn soft sm" type="button" data-go="loans/${esc(x.n)}">Add</button></div>`).join('')}` : ''}</section>
      </div>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), m = k.method || {}, co = k.contacts || {}, mine = co.rules || {}, eff = co.effective || {}, fl = co.floor || {}, ro = can() ? '' : ' disabled';
    const pol = k.policy || {}, rules = k.uw_rules || [];
    const meth = Object.entries(m.methods || {}).map(([key, say]) => `<label class="cr-meth"><input type="radio" name="method" value="${esc(key)}"${m.method === key ? ' checked' : ''}${ro}><span><b>${esc(METH[key] || key)}</b><span class="mut">${esc(say)}</span></span></label>`).join('');
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your own rules. Where Hoola only remembers a country's rule, it says “check this”.</p></div>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="method"><h2 class="md-h2">APR method</h2>
          <div class="md-alert" style="margin-bottom:12px${m.checked ? ';border-color:var(--line);background:var(--soft);color:var(--ink)' : ''}">${svg(IC.info)}<div><div class="t">${m.method ? esc(METH[m.method] || m.method) : 'No method'}</div><div class="s">${esc(m.from)}</div></div></div>
          <div class="cr-meths">${meth}</div>
          <div class="md-field" style="margin-top:12px"><label for="crMs">Where your rule is written (law or regulator page)</label><input class="in" id="crMs" name="source" maxlength="160" placeholder="Consumer Credit (Total Charge for Credit) Regulations 2010"${ro}></div>
          ${can() ? `<div class="md-acts">${m.checked ? '<button class="btn soft sm" type="button" data-unmethod="1">Use my country\'s usual method</button>' : '<span></span>'}<button class="btn" type="submit">Save</button></div>` : ''}</form>
        <form class="card" data-form="crules"><h2 class="md-h2">Collections contact rules</h2>
          <p class="mut" style="margin:0 0 12px;font-size:14px">Your rules can only be stricter than Hoola's floor (${esc(fl.from_hour ?? 8)}:00–${esc(fl.to_hour ?? 21)}:00, ${esc(fl.per_day ?? 1)} a day, ${esc(fl.per_week ?? 3)} a week, only the borrower, no threats).</p>
          <div class="md-form">
            <div class="md-field"><label for="crR1">Not before (hour)</label><input class="in" id="crR1" name="from_hour" type="number" min="0" max="23" value="${esc(mine.from_hour ?? '')}" placeholder="${esc(eff.from_hour)}"${ro}></div>
            <div class="md-field"><label for="crR2">Not after (hour)</label><input class="in" id="crR2" name="to_hour" type="number" min="1" max="24" value="${esc(mine.to_hour ?? '')}" placeholder="${esc(eff.to_hour)}"${ro}></div>
            <div class="md-field"><label for="crR3">Contacts a day at most</label><input class="in" id="crR3" name="per_day" type="number" min="0" value="${esc(mine.per_day ?? '')}" placeholder="${esc(eff.per_day)}"${ro}></div>
            <div class="md-field"><label for="crR4">Contacts a week at most</label><input class="in" id="crR4" name="per_week" type="number" min="0" value="${esc(mine.per_week ?? '')}" placeholder="${esc(eff.per_week)}"${ro}></div>
            <div class="md-field wide"><label>No contact on</label><div class="cr-days">${days.map(d => `<label><input type="checkbox" name="no_days" value="${d}"${(mine.no_days || []).includes(d) ? ' checked' : ''}${ro}>${esc(cap(d))}</label>`).join('')}</div></div>
            <div class="md-field wide"><label>Channels allowed</label><div class="cr-days">${['call', 'sms', 'email', 'letter', 'whatsapp'].map(c => `<label><input type="checkbox" name="channels" value="${c}"${(eff.channels || []).includes(c) ? ' checked' : ''}${ro}>${esc(c === 'sms' ? 'SMS' : cap(c))}</label>`).join('')}</div></div>
            <div class="md-field wide"><label for="crR5">Where these rules come from</label><input class="in" id="crR5" name="source" value="${esc(mine.source || '')}" maxlength="160" placeholder="Your collections policy, section 4"${ro}></div>
          </div>${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Checked before every contact. Hoola sends none.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      </div>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="policy"><h2 class="md-h2">Your policy limits for the memo</h2>
          <div class="md-form">${Object.entries(RATIO_SAY).map(([key, say]) => `<div class="md-field"><label for="crP_${key}">${esc(say)}</label><input class="in" id="crP_${key}" name="${key}" type="number" step="0.01" value="${esc(pol[key] ?? '')}" placeholder="No limit"${ro}></div>`).join('')}</div>
          ${can() ? '<div class="md-acts"><span class="mut" style="font-size:13px">A ratio outside your limit is flagged on the memo.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <section class="card"><h2 class="md-h2">Your underwriting rules</h2>
          ${rules.length ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Rule</th><th>Needs</th><th>If not met</th><th></th></tr></thead><tbody>${rules.map(r => `<tr><td><b>${esc(r.code)}</b></td><td>${esc(r.field)} ${esc(r.op)} ${esc(r.value)}</td><td><span class="cs-tag ${r.severity === 'stop' ? 'bad' : r.severity === 'info' ? '' : 'warn'}">${esc(SEV[r.severity] || r.severity)}</span></td><td>${can() ? `<button class="ib sm" type="button" data-unrule="${esc(r.code)}" aria-label="Remove ${esc(r.code)}">×</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('Your policy\'s rules, written the way the policy says them. Hoola has no built-in rules.')}
          ${can() ? `<form data-form="rule" class="cs-form"><input class="in sm2" name="code" placeholder="MIN_TRADING" required maxlength="40"><input class="in sm2" name="field" placeholder="months_trading" required maxlength="40"><select class="in sm2" name="op" aria-label="Test">${['>=', '>', '<=', '<', '==', '!='].map(o => `<option>${o}</option>`).join('')}</select><input class="in sm2" name="value" placeholder="24" required maxlength="40"><select class="in sm2" name="severity" aria-label="If not met"><option value="refer">Refer</option><option value="stop">Stop</option><option value="info">Info</option></select><button class="btn soft sm" type="submit">Add rule</button></form>` : ''}
          <p class="cs-note">foir_pct (debt payments plus the new payment, as % of income) is worked out for you when income and debts are known. Rules on religion, caste, gender, race, marital status, disability, area or surname are refused.</p></section>
      </div>`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function download(what) {
    const extra = (what === 'book') ? '' : '&n=' + enc(ST.arg);
    try {
      const r = await fetch(`/api/credit/download?workspace=${enc(W().id)}&what=${enc(what)}${extra}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `credit-${what}`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  const formOf = sel => { const f = $(sel); if (!f) return null; if (!f.reportValidity()) return false; return new FormData(f); };
  const val = (fd, n) => S(fd.get(n)).trim();
  const nums = (fd, names) => { const o = {}; for (const n of names) { const v = val(fd, n); if (v !== '') o[n] = Number(v); } return o; };
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const lf = t.closest('[data-lf]'); if (lf) { ST.lf = lf.dataset.lf; showPage(true); return; }
    if (t.closest('[data-schedall]')) { ST.schedAll = !ST.schedAll; showPage(true); return; }
    if (t.closest('[data-terms]')) { ST.terms = !ST.terms; showPage(true); return; }
    try {
      if (t.closest('[data-aprgo]')) {
        const fd = formOf('form[data-form=apr]'); if (!fd) return;
        ST.aprIn = Object.fromEntries(fd.entries());
        try { ST.aprRes = await run('apr', {...nums(fd, ['amount', 'rate', 'term', 'fee_pct', 'fees_upfront']), frequency: val(fd, 'frequency')}); } catch (err) { ST.aprRes = {error: err.message}; }
        showPage(true); return;
      }
      if (t.closest('[data-ifgo]')) {
        const fd = formOf('form[data-form=invfin]'); if (!fd) return;
        ST.ifIn = Object.fromEntries(fd.entries());
        try { ST.ifRes = await run('invoice_finance', nums(fd, ['invoice', 'advance_pct', 'fee_pct', 'days', 'discount_rate_pct'])); } catch (err) { ST.ifRes = {error: err.message}; }
        showPage(true); return;
      }
      if (t.closest('[data-ready]')) { ST.ready = false; showPage(true); try { ST.ready = await run('readiness', {}); } catch (err) { ST.ready = {error: err.message}; } showPage(true); return; }
      const sg = t.closest('[data-stage]'); if (sg) { await run('stage', {n: Number(ST.arg), stage: sg.dataset.stage}); await changed(sg.dataset.stage === 'with_decider' ? 'Sent to the decider.' : 'Back to gathering.'); return; }
      const om = t.closest('[data-okmatch]'); if (om) { om.disabled = true; await run('confirm_match', {n: Number(om.dataset.n), txn: om.dataset.okmatch}); await changed('Payment recorded from your bank statement.'); return; }
      const nm = t.closest('[data-nomatch]'); if (nm) { await run('dismiss_match', {txn: nm.dataset.nomatch}); await changed('Dismissed.'); return; }
      const uo = t.closest('[data-unoffer]'); if (uo) { await run('remove_offer', {n: Number(uo.dataset.unoffer)}); await changed('Removed.'); return; }
      if (t.closest('[data-addloan]')) {
        const fd = formOf('form[data-form=loan]'); if (!fd) return;
        const a = {name: val(fd, 'name'), side: val(fd, 'side'), start: val(fd, 'start'), tz: val(fd, 'tz'), ...nums(fd, ['amount', 'rate', 'term', 'payment'])};
        const r = await run('add_loan', a); await changed('Loan added.'); location.hash = '#/loans/' + r.loan.n; return;
      }
      const el = t.closest('[data-editloan]'); if (el) {
        const fd = formOf('form[data-form=editloan]'); if (!fd) return;
        const a = {n: Number(el.dataset.editloan), tz: val(fd, 'tz')};
        for (const k of ['rate', 'pd', 'lgd', 'pd_lifetime']) if (fd.has(k)) a[k] = val(fd, k) === '' ? '' : Number(val(fd, k));
        await run('edit_loan', a); await changed('Saved.'); return;
      }
      const ul = t.closest('[data-unloan]'); if (ul) { if (!confirm('Remove this loan and its payments from the desk?')) return; await run('remove_loan', {n: Number(ul.dataset.unloan)}); await changed('Removed.'); location.hash = '#/loans'; return; }
      const up = t.closest('[data-unpay]'); if (up) { await run('remove_payment', {n: Number(ST.arg), i: Number(up.dataset.unpay)}); await changed('Payment removed.'); return; }
      const co = t.closest('[data-collect]'); if (co) {
        const fd = formOf('form[data-form=collect]'); if (!fd) return;
        const a = {borrower: (loanOf(co.dataset.collect) || {}).name, channel: val(fd, 'channel'), when: val(fd, 'when'), tz: val(fd, 'tz'), to: val(fd, 'to'),
          message: val(fd, 'message'), legal_stage: $('#crLegal') && $('#crLegal').checked ? true : undefined};
        try { const r = await run('collect', a); ST.coll = {n: String(co.dataset.collect), ...r}; await refreshDesk(false); }
        catch (err) { ST.coll = {n: String(co.dataset.collect), error: err.message}; }
        showPage(true); return;
      }
      const uf = t.closest('[data-unfig]'); if (uf) { await run('app_figure', {n: Number(ST.arg), name: uf.dataset.unfig, value: ''}); await changed('Removed.'); return; }
      const ufd = t.closest('[data-unfield]'); if (ufd) { await run('app_field', {n: Number(ST.arg), field: ufd.dataset.unfield, value: ''}); await changed('Removed.'); return; }
      const uc = t.closest('[data-uncond]'); if (uc) { await run('condition', {n: Number(ST.arg), name: uc.dataset.uncond, remove: true}); await changed('Removed.'); return; }
      if (t.closest('[data-reopen]')) { await run('reopen_app', {n: Number(ST.arg)}); await changed('Reopened.'); return; }
      if (t.closest('[data-unapp]')) { if (!confirm('Remove this application?')) return; await run('remove_app', {n: Number(ST.arg)}); await changed('Removed.'); location.hash = '#/apps'; return; }
      const ur = t.closest('[data-unrule]'); if (ur) { await run('rule', {code: ur.dataset.unrule, remove: true}); await changed('Removed.'); return; }
      if (t.closest('[data-unmethod]')) { await run('method', {method: ''}); await changed('Using your country\'s usual method.'); return; }
    } catch (err) { toast(err.message, true); }
  }
  async function onChange(e) {
    const fi = e.target.closest('[data-rowsfile]');
    if (fi) { const f = fi.files && fi.files[0]; if (!f) return; if (f.size > 2e6) { toast('Up to 2 MB.', true); return; }
      const ta = $('form[data-form=rows] textarea'); if (ta) ta.value = await f.text(); toast(`${f.name} loaded - press Read the statement.`); return; }
    const s = e.target.closest('[data-cond]'); if (!s) return;
    let a = {n: Number(ST.arg), name: s.dataset.cond, status: s.value};
    const item = ((ST.app && ST.app.checklist) || {}).items?.find(i => i.name === s.dataset.cond);
    if (item && item.due) a.due = item.due;
    if (s.value === 'waived') { const who = prompt('Who waived it? (their name)'); if (!who) { showPage(true); return; } a.waived_by = who; }
    try { await run('condition', a); await changed('Updated.'); } catch (err) { toast(err.message, true); showPage(true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = form.querySelector('[type=submit]');
    const g = n => val(fd, n), n = Number(ST.arg);
    if (kind === 'apr' || kind === 'invfin') { $(`[data-${kind === 'apr' ? 'aprgo' : 'ifgo'}]`)?.click(); return; }
    if (btn) btn.disabled = true;
    try {
      if (kind === 'offer') { await run('add_offer', {name: g('name'), ...nums(fd, ['amount', 'rate', 'term', 'fee_pct', 'fees_upfront'])}); await changed('Offer added.'); }
      else if (kind === 'app') { const r = await run('add_app', {borrower: g('borrower'), purpose: g('purpose'), ...nums(fd, ['amount', 'rate', 'term'])}); await changed('Application added.'); location.hash = '#/apps/' + r.app.n; }
      else if (kind === 'terms') { ST.terms = false; await run('edit_app', {n, amount: Number(g('amount')), rate: g('rate'), term: g('term'), fee_pct: g('fee_pct'), purpose: g('purpose')}); await changed('Terms saved.'); }
      else if (kind === 'afig') { await run('app_figure', {n, name: g('name'), value: Number(g('value')), source: g('source')}); await changed('Figure added.'); }
      else if (kind === 'afield') { await run('app_field', {n, field: g('field'), value: g('value')}); await changed('Added.'); }
      else if (kind === 'rows') { await run('edit_app', {n, rows_csv: g('rows_csv')}); await changed('Statement read.'); }
      else if (kind === 'cond') { await run('condition', {n, name: g('name'), status: 'missing', due: g('due') || undefined}); await changed('Condition added.'); }
      else if (kind === 'decide') { await run('close_app', {n, decided_by: g('decided_by'), outcome: g('outcome')}); await changed('Decision recorded.'); }
      else if (kind === 'pay') { await run('payment', {n, amount: Number(g('amount')), date: g('date')}); await changed('Payment recorded.'); }
      else if (kind === 'method') { await run('method', {method: g('method'), source: g('source')}); await changed('Saved.'); }
      else if (kind === 'policy') {
        for (const k of Object.keys(RATIO_SAY)) { const v = g(k), had = (K().policy || {})[k];
          if (v !== '' || had !== undefined) await run('policy', {ratio: k, limit: v === '' ? '' : Number(v)}); }
        await changed('Saved.');
      }
      else if (kind === 'rule') { await run('rule', {code: g('code'), field: g('field'), op: g('op'), value: g('value'), severity: g('severity')}); await changed('Rule added.'); }
      else if (kind === 'crules') {
        const a = {...nums(fd, ['from_hour', 'to_hour', 'per_day', 'per_week']), no_days: fd.getAll('no_days'), channels: fd.getAll('channels'), source: g('source')};
        await run('contact_rules', a); await changed('Saved.');
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
    const box = $('#crFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/credit/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'cr' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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

