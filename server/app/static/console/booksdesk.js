/* v0.999.158 BOOKS DESK - the Books & Accounts employee's own section, like the business desks (owner: "NOW LETS WORK ON
   BOOKS AND ACCOUNT --- FIRST CHECK WANT IT HAS AND THEN A NEW DESIGN HERE" -> the design
   claude.ai/artifact/VZnFUmr3C1KtjrK3ESRnk3 -> "GO").
   A thin top bar (business picker), then the Books & Accounts chat (its own conversation, kind 'books': she asks about her
   figures or drops a bill, receipt or statement) beside the desk's pages: Today, Sales & bills, Bank & matching, Owed &
   owing, Reports & month-end, Settings & exports. The pages call the F3 engine (/api/fin/books/*) on the business picked
   here. Every figure comes from her books. Nothing here sends an invoice, pays a bill or files a return; a month locks only
   on her confirm of the checklist she saw (its hash). Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/><path d="M9 8h6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    warn: '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['docs', 'Sales & bills'], ['bank', 'Bank & matching'], ['owed', 'Owed & owing'],
    ['close', 'Reports & month-end'], ['settings', 'Settings & exports']];
  const TRUST = {Learning: 'Reads, drafts and proposes. Every posting waits for your tap.',
    Partner: 'Also keeps drafts and matches up to date on its own. Posting still waits for you.',
    Trusted: 'Does more on its own. Sending, paying and filing always stay yours.'};
  const STARTERS = {
    today: ['How did we do last month?', 'What do I owe this week?', 'Who is late paying me?'],
    docs: ['Make an invoice', 'Read this receipt into a bill', 'Which drafts are waiting?'],
    bank: ['Why did you match this line?', 'What is this payment?', 'Do bank and books agree?'],
    owed: ['Draft a reminder to my latest payer', 'Who is late paying me?', 'Which bills are due soon?'],
    close: ['Is last month ready to close?', 'Explain my profit and loss', 'What does my balance sheet say?'],
    settings: ['Add an account for travel', 'Which export does my accountant need?', 'What will you never do?']};
  const SIZES = {solo: 'My own work (sole trader, freelancer)', business: 'My business with a team', firm: 'Clients of my firm', institution: 'A regulated institution'};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    docKind: 'sales', docs: null, matches: null, recon: null, chart: null, ar: null, ap: null, ck: null, rep: null,
    period: '', lines: 1, setupPv: null, receipt: null};
  try { ST.side = localStorage.getItem('hoola.books.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.books.folded') === '1'; } catch {}

  const ws = () => (ST.d && ST.d.workspace) || null;
  const cur = () => (ST.d && ST.d.numbers && ST.d.numbers.currency) || (ws() && ws().currency) || '';
  const money = (v, c) => { const n = Number(v || 0); try { return new Intl.NumberFormat(undefined, {style: 'currency', currency: c || cur() || 'USD'}).format(n); } catch { return n.toFixed(2); } };
  const today = () => new Date().toISOString().slice(0, 10);
  const lastMonth = () => { const d = new Date(); d.setDate(1); d.setDate(0); return d.toISOString().slice(0, 7); };
  const thisMonth = () => today().slice(0, 7);
  async function books(part, a) { return api('POST', `/api/fin/books/${part}`, Object.assign({workspace: ws().id}, a || {})); }

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/books/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.book, '')}</div>
        <h1 class="sd-h">Books &amp; Accounts is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="bkHire">Hire Books &amp; Accounts</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#bkHire').onclick = async () => { try { await api('POST', '/api/employees/books_accounts/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    ST.period = lastMonth();
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
    if (!ws() && ST.tab !== 'settings') ST.tab = 'settings';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.book, '')}</div>
          <div style="min-width:0"><div class="sd-name">Books &amp; Accounts</div><div class="sd-site" id="bkSite"></div></div>
          <span id="bkState"></span>
        </div>
        <div class="sd-acts">
          <label class="hide-sm" for="bkBiz" style="position:absolute;width:1px;height:1px;overflow:hidden">Business</label>
          <select class="in bk-biz hide-sm" id="bkBiz"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Books & Accounts chat">
          <div class="sd-chathead"><div class="t"><b>Books &amp; Accounts chat</b><span>Drop a bill, receipt or statement · it never sends, pays or files</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="mdFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="mdPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.ofx,.qif,.sta,.xml,.xlsx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Books & Accounts desk" id="sdTabs"></nav>
          <div id="mdPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your books, or drop a file…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#mdPick').click()});
    $('#mdPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.books.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.books.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/books/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#bkBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/books/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); toast('Switched business.'); }
      catch (err) { toast(err.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => { clearCache(); refreshDesk(true); });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#mdPage').addEventListener('click', onPageClick);
    $('#mdPage').addEventListener('submit', onSubmit);
    $('#mdPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#bkState'); if (!el) return;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !ws() ? ['warn', 'Set up your business'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const w = ws();
    $('#bkSite').textContent = w ? `${w.name} · ${(w.countries || []).join(', ')} · ${w.currency}` : 'No business set up yet';
    const sel = $('#bkBiz');
    sel.hidden = (d.businesses || []).length < 2;
    sel.innerHTML = (d.businesses || []).map(b => `<option value="${esc(b.id)}"${w && b.id === w.id ? ' selected' : ''}>${esc(b.name)}</option>`).join('');
  }
  function paintTabs() {
    const n = (ST.d && ST.d.numbers) || {};
    $('#sdTabs').innerHTML = TABS.map(([k, name]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === ST.tab}"${!ws() && k !== 'settings' ? ' disabled' : ''}>${esc(name)}${
      k === 'bank' && n.bank_to_confirm ? `<span class="n">${esc(n.bank_to_confirm)}</span>` : ''}</button>`).join('');
  }
  function clearCache() { ST.docs = ST.matches = ST.recon = ST.chart = ST.ar = ST.ap = ST.ck = ST.rep = null; }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/books/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint || ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#mdPage'); if (!box) return;
    const fn = {today: pToday, docs: pDocs, bank: pBank, owed: pOwed, close: pClose, settings: pSettings}[ST.tab] || pToday;
    box.innerHTML = fn();
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
    load();
  }
  async function load() {           // a page draws first, then fills from the engine once
    if (!ws()) return;
    const t = ST.tab;
    if (ST.arg && (t === 'docs' || t === 'bank')) return;     // a form page (new invoice, receipt, import) needs nothing loaded
    try {
      if (t === 'docs' && !ST.docs) { ST.docs = (await books('documents')).documents || []; }
      else if (t === 'bank' && !ST.matches) {
        const [m, r, ch, dc] = await Promise.all([books('matches'), books('reconcile', {period: thisMonth()}), ST.chart ? ST.chart : books('chart'), ST.docs ? {documents: ST.docs} : books('documents')]);
        ST.matches = m; ST.recon = r; ST.chart = ch; ST.docs = dc.documents || [];
      } else if (t === 'owed' && !ST.ar) {
        const [ar, ap] = await Promise.all([books('ageing', {kind: 'receivables', as_of: today()}), books('ageing', {kind: 'payables', as_of: today()})]);
        ST.ar = ar; ST.ap = ap;
      } else if (t === 'close' && !ST.ck) {
        const [ck, rep] = await Promise.all([books('close_check', {period: ST.period}), books('reports', {since: ST.period + '-01', upto: monthEnd(ST.period)})]);
        ST.ck = ck; ST.rep = rep;
      } else if (t === 'settings' && !ST.chart) { ST.chart = await books('chart'); }
      else return;
    } catch (e) { toast(e.message, true); return; }
    if (ST.tab === t) { $('#mdPage').innerHTML = ({docs: pDocs, bank: pBank, owed: pOwed, close: pClose, settings: pSettings})[t](); }
  }
  const monthEnd = p => { const [y, m] = p.split('-').map(Number); return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10); };
  const loading = '<section class="card"><p class="mut" style="margin:0">Reading your books…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, cls, sub) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${esc(v)}</div>${sub ? `<div class="bk-sub">${esc(sub)}</div>` : ''}</div>`;

  function pToday() {
    const n = ST.d.numbers || {};
    if (ST.d.numbers_error) return `<section class="md-alert">${svg(IC.warn)}<div><div class="t">The books could not be read</div><div class="s">${esc(ST.d.numbers_error)}</div></div></section>`;
    const m = n.month || {}, od = n.overdue_docs || [], ck = n.close || {};
    const needs = [];
    if (n.bank_to_confirm) needs.push([`${n.bank_to_confirm} bank line${n.bank_to_confirm > 1 ? 's' : ''} to confirm`, n.bank_sure ? `Hoola found a sure match for ${n.bank_sure}` : 'Pick an invoice, a bill or an account', 'v', 'Matches ready', 'bank', 'Review']);
    if (od.length) needs.push([`${od.length} invoice${od.length > 1 ? 's' : ''} overdue`, od.slice(0, 2).map(x => `${x.party} ${money(x.open, x.currency)}`).join(' · '), 'warn', `Up to ${Math.max(...od.map(x => x.days))} days late`, 'owed', 'See who']);
    if (n.drafts) needs.push([`${n.drafts} draft${n.drafts > 1 ? 's' : ''} to check`, 'Invoices or bills not posted yet', '', 'Draft', 'docs', 'Check']);
    if (ck.of && !ck.locked) needs.push([`${ck.period} can be closed`, `${ck.done} of ${ck.of} checks done`, ck.ready ? 'ok' : 'warn', ck.ready ? 'Ready' : `${ck.of - ck.done} open`, 'close', 'Close it']);
    const rows = needs.map(([t, s, k, p, go, b]) => `<tr><td><b>${esc(t)}</b><div class="mut" style="font-size:13px">${esc(s)}</div></td><td><span class="pill ${k}">${esc(p)}</span></td><td style="text-align:right"><button class="btn soft sm" type="button" data-go="${go}">${esc(b)}</button></td></tr>`).join('');
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">Every figure comes from your books. Nothing here sends, pays or files - you do that.</p></div>
      <div class="bk-4">${kpi('In the bank', money(n.bank))}${kpi('Customers owe you', money(n.owed_to_you), '', n.overdue_to_you ? money(n.overdue_to_you) + ' overdue' : 'None overdue')}
        ${kpi('You owe suppliers', money(n.you_owe), '', n.overdue_you_owe ? money(n.overdue_you_owe) + ' overdue' : 'None overdue')}
        ${kpi('Profit this month', money(m.profit), Number(m.profit) < 0 ? 'bad' : 'ok', `Sales ${money(m.income)} · costs ${money(m.expenses)}`)}</div>
      <section class="card tight"><div style="padding:12px 0 4px"><h2 class="md-h2" style="margin:0">Needs you</h2></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><tbody>${rows}</tbody></table></div>` : '<p class="mut" style="margin:6px 0 12px">Nothing needs you. Your books are up to date.</p>'}</section>
      <section class="card"><h2 class="md-h2">Do something</h2><div class="md-mini">
        <button type="button" data-go="docs/new-sales">New invoice<br><span class="mut" style="font-size:12.5px">Numbered once, never reused</span></button>
        <button type="button" data-go="docs/new-purchase">Record a bill<br><span class="mut" style="font-size:12.5px">Or drop the PDF in the chat</span></button>
        <button type="button" data-go="bank/import">Import a bank statement<br><span class="mut" style="font-size:12.5px">CSV, OFX, QIF, MT940, CAMT</span></button>
        <button type="button" data-go="docs/receipt">Read a receipt<br><span class="mut" style="font-size:12.5px">Into a draft bill you check</span></button></div></section>`;
  }

  /* --- Sales & bills */
  const DSTATE = {draft: ['v', 'Draft - not posted'], open: ['', 'Open'], paid: ['ok', 'Paid']};
  function docPill(d) {
    if (d.status === 'open' && d.due < today()) { const days = Math.round((Date.parse(today()) - Date.parse(d.due)) / 864e5); return `<span class="pill warn">Overdue ${days} day${days > 1 ? 's' : ''}</span>`; }
    const [k, t] = DSTATE[d.status] || ['', d.status]; return `<span class="pill ${k}">${esc(t)}</span>`;
  }
  function pDocs() {
    const a = ST.arg;
    if (a === 'new-sales' || a === 'new-purchase') return docForm(a === 'new-sales' ? 'sales' : 'purchase');
    if (a === 'receipt') return receiptForm();
    if (!ST.docs) return head('Sales & bills') + loading;
    const all = ST.docs, list = ST.docKind === 'draft' ? all.filter(d => d.status === 'draft') : all.filter(d => d.kind === ST.docKind && d.status !== 'draft');
    const count = k => k === 'draft' ? all.filter(d => d.status === 'draft').length : all.filter(d => d.kind === k && d.status !== 'draft').length;
    const seg = [['sales', 'Invoices'], ['purchase', 'Bills'], ['draft', 'Drafts']].map(([k, t]) => `<button class="chip" type="button" data-dk="${k}" aria-pressed="${ST.docKind === k}">${t} ${count(k)}</button>`).join('');
    const rows = list.slice().reverse().map(d => `<tr><td>${esc(d.number || '-')}</td><td><b>${esc(d.party)}</b>${d.source === 'receipt' ? '<div class="mut" style="font-size:13px">From a receipt</div>' : ''}</td>
      <td class="nw">${esc(d.issue)}</td><td class="nw">${esc(d.due)}</td><td class="num">${esc(money(d.total, d.currency))}${d.status === 'open' && d.open !== d.total ? `<div class="mut" style="font-size:12.5px">${esc(money(d.open, d.currency))} open</div>` : ''}</td>
      <td>${docPill(d)}</td><td style="text-align:right">${d.status === 'draft' ? `<button class="btn sm" type="button" data-issue="${esc(d.id)}">${d.kind === 'sales' ? 'Issue' : 'Post'}</button>` : ''}</td></tr>`).join('');
    return `${head('Sales & bills', 'Every invoice and bill is numbered once. You send and pay them - Hoola keeps them in the books.')}
      <section class="card tight"><div class="bk-bar"><div role="group" aria-label="Show" style="display:flex;gap:6px;flex-wrap:wrap">${seg}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-go="docs/receipt">Read a receipt</button><button class="btn soft sm" type="button" data-go="docs/new-purchase">Record a bill</button><button class="btn sm" type="button" data-go="docs/new-sales">New invoice</button></div></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Number</th><th>${ST.docKind === 'purchase' ? 'Supplier' : 'Customer'}</th><th>Date</th><th>Due</th><th class="num">Amount</th><th></th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
          : `<p class="mut" style="margin:0 0 12px">Nothing here yet.</p>`}</section>`;
  }
  const head = (t, s) => `<div><h1 class="sd-h">${esc(t)}</h1>${s ? `<p class="lead">${esc(s)}</p>` : ''}</div>`;
  function docForm(kind) {
    const lines = Array.from({length: ST.lines}, (_, i) => `<div class="bk-line">
      <div class="md-field"><label for="bkD${i}">Description</label><input class="in" id="bkD${i}" name="d${i}" required></div>
      <div class="md-field"><label for="bkQ${i}">Qty</label><input class="in" id="bkQ${i}" name="q${i}" type="number" min="0" step="any" value="1"></div>
      <div class="md-field"><label for="bkP${i}">Price</label><input class="in" id="bkP${i}" name="p${i}" type="number" min="0" step="0.01" required></div>
      <div class="md-field"><label for="bkT${i}">Tax %</label><input class="in" id="bkT${i}" name="t${i}" type="number" min="0" step="0.01" value="0"></div></div>`).join('');
    const due = new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
    return `<a class="md-back" href="#/docs">← Sales &amp; bills</a>${head(kind === 'sales' ? 'New invoice' : 'Record a bill', kind === 'sales' ? 'It stays a draft until you issue it. Once issued, its number never changes. Hoola does not send it.' : 'It stays a draft until you post it. Hoola does not pay it.')}
      <form class="card" data-form="doc" data-kind="${kind}"><div class="md-form">
        <div class="md-field wide"><label for="bkParty">${kind === 'sales' ? 'Customer' : 'Supplier'}</label><input class="in" id="bkParty" name="party" required></div>
        <div class="md-field"><label for="bkIssue">Date</label><input class="in" id="bkIssue" name="issue" type="date" value="${today()}" required></div>
        <div class="md-field"><label for="bkDue">Due</label><input class="in" id="bkDue" name="due" type="date" value="${due}"></div>
        <div class="md-field"><label for="bkCur">Currency</label><input class="in" id="bkCur" name="currency" value="${esc(cur())}" maxlength="3" pattern="[A-Za-z]{3}"></div>
        <div class="md-field"><label for="bkRate">Exchange rate (only if foreign)</label><input class="in" id="bkRate" name="rate" type="number" min="0" step="any"></div></div>
        <h2 class="md-h2" style="margin-top:16px">Lines</h2>${lines}
        <button class="btn soft sm" type="button" data-addline="1">Add a line</button>
        <p class="mut" style="font-size:12.5px;margin:12px 0 0">Tax % is your own rate. A country's rate is shown in Hoola's rules, never used until checked.</p>
        <div class="md-acts"><button class="btn soft" type="button" data-go="docs">Cancel</button><div style="display:flex;gap:8px"><button class="btn soft" type="submit" name="how" value="draft">Save as draft</button><button class="btn" type="submit" name="how" value="issue">${kind === 'sales' ? 'Save and issue' : 'Save and post'}</button></div></div></form>`;
  }
  function receiptForm() {
    const r = ST.receipt;
    const got = r ? `<section class="card"><h2 class="md-h2">Read from the receipt <span class="pill">Draft - nothing posted</span></h2>
      ${[['Supplier', r.read.seller], ['Date', r.read.date || 'Not found - today used'], ['Tax', money(r.read.tax)], ['Total', money(r.read.total)]].map(([k, v]) => `<div class="bk-kv"><span class="mut">${esc(k)}</span><span>${esc(v)}</span></div>`).join('')}
      <div class="md-acts"><span class="mut" style="font-size:12.5px">Check it. Wrong? Delete the draft from Drafts and record it by hand.</span><button class="btn" type="button" data-issue="${esc(r.id)}">Post this bill</button></div></section>` : '';
    return `<a class="md-back" href="#/docs">← Sales &amp; bills</a>${head('Read a receipt', 'Paste the words of a receipt (or drop its picture in the chat). Hoola reads the supplier, date, tax and total into a draft bill.')}
      <form class="card" data-form="receipt"><div class="md-field"><label for="bkRc">The receipt's text</label><textarea class="in" id="bkRc" name="text" rows="8" required></textarea></div>
        <div class="md-acts"><span class="mut" style="font-size:12.5px">Nothing is posted until you tap Post.</span><button class="btn" type="submit">Read it</button></div></form>${got}`;
  }

  /* --- Bank & matching */
  function pBank() {
    if (ST.arg === 'import') return importForm();
    if (!ST.matches) return head('Bank & matching') + loading;
    const accts = (ST.chart && ST.chart.accounts) || [];
    const opts = sel => accts.map(a => `<option value="${esc(a.code)}"${a.code === sel ? ' selected' : ''}>${esc(a.code)} ${esc(a.name)}</option>`).join('');
    const byNum = Object.fromEntries((ST.docs || []).map(d => [d.number, d.id]));
    const rows = (ST.matches.lines || []).map(l => {
      const amt = Number(l.amount);
      let think, act;
      if (l.doc) { think = `<b>Pays ${esc(l.number)}</b><div class="mut" style="font-size:12.5px">${esc(l.why)}</div>`;
        act = `<button class="btn sm" type="button" data-apply="${esc(l.txn)}" data-doc="${esc(l.doc)}">Confirm</button>`; }
      else if (l.choices) { think = `<b class="bk-warn">Fits more than one</b><div class="mut" style="font-size:12.5px">${esc(l.why)}</div>`;
        act = `<div class="bk-pick"><label class="sr" for="bkCh_${esc(l.txn)}">Which document</label><select class="in sm" id="bkCh_${esc(l.txn)}">${l.choices.map(c => `<option value="${esc(byNum[c] || '')}">${esc(c)}</option>`).join('')}</select><button class="btn sm" type="button" data-applysel="${esc(l.txn)}">Confirm</button></div>`; }
      else { think = `<b>${esc(l.why.replace(/^no document; /, 'No invoice or bill - '))}</b><div class="mut" style="font-size:12.5px">Pick the account it goes to</div>`;
        act = `<div class="bk-pick"><label class="sr" for="bkAc_${esc(l.txn)}">Account</label><select class="in sm" id="bkAc_${esc(l.txn)}">${opts(l.propose_account)}</select><button class="btn sm" type="button" data-post="${esc(l.txn)}">Confirm</button></div>`; }
      return `<tr><td class="nw">${esc(l.day)}</td><td>${esc(l.narration)}</td><td class="num ${amt > 0 ? 'bk-in' : ''}">${amt > 0 ? '+' : ''}${esc(money(amt))}</td><td>${think}</td><td style="text-align:right">${act}</td></tr>`;
    }).join('');
    const r = ST.recon || {};
    return `${head('Bank & matching', 'Hoola matches each bank line to an invoice, a bill or an account and tells you why. Nothing is posted until you confirm.')}
      <section class="card tight"><div class="bk-bar"><h2 class="md-h2" style="margin:0">Bank lines to confirm</h2><button class="btn soft sm" type="button" data-go="bank/import">Import a statement</button></div>
        ${rows ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Date</th><th>On the statement</th><th class="num">Amount</th><th>Hoola thinks</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
          : '<p class="mut" style="margin:0 0 12px">Every bank line is in the books. Import a new statement when you have one.</p>'}</section>
      <section class="card"><h2 class="md-h2">Reconciliation, ${esc(r.period || thisMonth())}</h2>
        <div class="bk-4">${kpi('Bank says', money(r.statement_balance))}${kpi('Books say', money(r.book_balance))}${kpi('Waiting to confirm', String((r.bank_only || []).length) + ' lines', (r.bank_only || []).length ? 'bk-wv' : '')}${kpi('Still unexplained', money(r.unexplained), Number(r.unexplained) ? 'bad' : 'ok')}</div>
        <p class="mut" style="margin:12px 0 0;font-size:13.5px">${r.reconciled ? 'Bank and books agree.' : 'Once you confirm the lines above, bank and books agree - or the difference shows here.'}</p></section>`;
  }
  function importForm() {
    return `<a class="md-back" href="#/bank">← Bank &amp; matching</a>${head('Import a bank statement', 'Choose the file your bank gives you. Lines already in the books are skipped.')}
      <form class="card" data-form="import"><div class="md-form">
        <div class="md-field wide"><label for="bkFile">Statement file (CSV, OFX, QIF, MT940, CAMT.053)</label><input class="in" id="bkFile" name="file" type="file" accept=".csv,.ofx,.qif,.sta,.mt940,.xml,.txt" required></div>
        <div class="md-field"><label for="bkAcct">Bank account name</label><input class="in" id="bkAcct" name="account" value="Main account"></div>
        <div class="md-field"><label for="bkSCur">Currency</label><input class="in" id="bkSCur" name="currency" value="${esc(cur())}" maxlength="3"></div></div>
        <div class="md-acts"><span class="mut" style="font-size:12.5px">The file stays in your books. Hoola never logs in to your bank.</span><button class="btn" type="submit">Import</button></div></form>`;
  }

  /* --- Owed & owing */
  const BK = [['not_due', 'Not due', 'var(--ok)'], ['1_30', '1-30', '#C99A2E'], ['31_60', '31-60', '#D46A1F'], ['61_90', '61-90', '#B42318'], ['over_90', '90+', '#7A1A12']];
  function ageCard(a, title, isAr) {
    if (!a) return '';
    const tot = Number(a.total) || 0;
    const bar = tot ? `<div class="md-bar bk-agebar" role="img" aria-label="${esc(BK.map(([k, n]) => `${n}: ${money(a.buckets[k])}`).join(', '))}">${BK.map(([k, , c]) => Number(a.buckets[k]) ? `<div style="width:${(Number(a.buckets[k]) / tot * 100).toFixed(1)}%;background:${c}"></div>` : '').join('')}</div>` : '';
    const rows = Object.entries(a.by_party || {}).map(([p, b]) => { const sum = BK.reduce((s, [k]) => s + Number(b[k] || 0), 0); const late = sum - Number(b.not_due || 0);
      return `<tr><td><b>${esc(p)}</b></td>${BK.map(([k]) => `<td class="num${Number(b[k]) && k !== 'not_due' ? ' bk-late' : ''}">${Number(b[k]) ? esc(money(b[k])) : '-'}</td>`).join('')}<td class="num"><b>${esc(money(sum))}</b></td>
        <td style="text-align:right">${isAr && late > 0 ? `<button class="btn soft sm" type="button" data-remind="${esc(p)}">Draft reminder</button>` : ''}</td></tr>`; }).join('');
    return `<section class="card"><h2 class="md-h2">${esc(title)} ${esc(money(tot))}</h2>${bar}
      ${tot ? `<div class="md-legend" style="margin-top:10px">${BK.map(([, n, c]) => `<span><i style="background:${c}"></i>${n === 'Not due' ? n : n + ' days late'}</span>`).join('')}</div>` : ''}
      ${rows ? `<div style="overflow-x:auto;margin-top:12px"><table class="tb"><thead><tr><th>${isAr ? 'Customer' : 'Supplier'}</th>${BK.map(([, n]) => `<th class="num">${n}</th>`).join('')}<th class="num">Total</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
        : `<p class="mut" style="margin:10px 0 0">${isAr ? 'Nobody owes you anything.' : 'You owe nothing.'}</p>`}</section>`;
  }
  function pOwed() {
    if (!ST.ar) return head('Owed & owing') + loading;
    return `${head('Owed & owing', 'Who owes you and who you owe. A reminder is a draft in the chat - you send it. Hoola never pays.')}
      ${ageCard(ST.ar, 'Customers owe you', true)}${ageCard(ST.ap, 'You owe suppliers', false)}
      <form class="card" data-form="asset"><h2 class="md-h2">Add equipment</h2><div class="md-form">
        <div class="md-field"><label for="bkAN">What it is</label><input class="in" id="bkAN" name="name" required></div>
        <div class="md-field"><label for="bkAC">Cost</label><input class="in" id="bkAC" name="cost" type="number" min="0" step="0.01" required></div>
        <div class="md-field"><label for="bkAS">First month (YYYY-MM)</label><input class="in" id="bkAS" name="start" type="month" value="${thisMonth()}" required></div>
        <div class="md-field"><label for="bkAL">Life in months (straight line)</label><input class="in" id="bkAL" name="life_months" type="number" min="1" value="36"></div></div>
        <div class="md-acts"><span class="mut" style="font-size:12.5px">Each month's depreciation is posted once, at month-end.</span><button class="btn" type="submit">Add it</button></div></form>`;
  }

  /* --- Reports & month-end */
  function pClose() {
    const months = Array.from({length: 12}, (_, i) => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i); return d.toISOString().slice(0, 7); });
    const pickM = `<label class="sr" for="bkPer">Month</label><select class="in sm" id="bkPer" data-period="1">${months.map(m => `<option${m === ST.period ? ' selected' : ''}>${m}</option>`).join('')}</select>`;
    if (!ST.ck) return head('Reports & month-end') + `<div>${pickM}</div>` + loading;
    const ck = ST.ck, done = ck.items.filter(i => i.ok).length;
    const items = ck.items.map(i => `<div class="bk-ck"><span class="bk-dot ${i.ok ? 'ok' : 'warn'}" aria-hidden="true">${i.ok ? '✓' : '!'}</span><div><div>${esc(i.item)}</div>${
      !i.ok ? `<div class="mut" style="font-size:12.5px">${i.which && i.which.length ? esc(i.which.join(', ')) : i.count ? esc(i.count) + ' to do' : i.amount ? esc(money(i.amount)) : 'Not done'}</div>` : ''}</div></div>`).join('');
    const lockBox = ck.locked ? '<p class="mut" style="margin:14px 0 0">This month is locked. No new posting can change it.</p>'
      : `<form data-form="lock" class="bk-lock">${ck.ready ? '' : `<div class="md-field"><label for="bkEx">Closing anyway? Write why (your accountant sees it)</label><textarea class="in" id="bkEx" name="exceptions" rows="2"></textarea></div>`}
        <div class="md-acts"><span class="mut" style="font-size:12.5px;max-width:440px">Locking stops any new posting in ${esc(ck.period)}. It applies only to this exact checklist - if the books change, Hoola asks again.</span><button class="btn" type="submit">Lock ${esc(ck.period)}</button></div></form>`;
    const r = ST.rep || {}, pl = r.profit_and_loss || {}, bs = r.balance_sheet || {};
    const kv = (k, v, cls) => `<div class="bk-kv"><span>${esc(k)}</span><span class="num ${cls || ''}">${esc(v)}</span></div>`;
    return `${head('Reports & month-end', 'Your reports come straight from the books. A month locks only when you confirm its checklist.')}
      <div class="bk-bar" style="padding:0">${pickM}<span class="pill ${ck.locked ? 'ok' : ck.ready ? 'ok' : 'warn'}">${ck.locked ? 'Locked' : `${done} of ${ck.items.length} done`}</span></div>
      <section class="card"><h2 class="md-h2">${esc(ck.period)} checklist</h2>${items}${lockBox}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Profit and loss, ${esc(ck.period)}</h2>${kv('Sales and other income', money(pl.income))}${kv('Costs', money(-Number(pl.expenses || 0)))}${kv('Profit', money(pl.profit), Number(pl.profit) < 0 ? 'bk-late' : 'bk-in')}
          <h2 class="md-h2" style="margin-top:16px">Balance sheet at ${esc(bs.as_of || '')}</h2>${kv('What you own', money(bs.assets))}${kv('What you owe', money(bs.liabilities))}${kv('Owner\'s share', money(bs.equity))}
          <p class="mut" style="font-size:12.5px;margin:10px 0 0">${r.balanced ? 'The trial balance balances.' : 'The trial balance does not balance - ask in the chat.'}</p></section>
        <section class="card"><h2 class="md-h2">Files for your accountant</h2>
          ${[['csv', 'Journal (CSV)'], ['xero', 'For Xero (CSV)'], ['quickbooks', 'For QuickBooks (CSV)'], ['tally', 'For Tally (XML)']].map(([f, t]) => `<div class="bk-kv"><span>${esc(t)}</span><button class="btn soft sm" type="button" data-export="${f}">Download</button></div>`).join('')}
          <p class="mut" style="font-size:12.5px;margin:10px 0 0">${esc(ck.period)} only. Check an import in a test company first.</p></section></div>`;
  }

  /* --- Settings & exports */
  function pSettings() {
    const w = ws(), d = ST.d;
    const setup = `<form class="card" data-form="setup"><h2 class="md-h2">${w ? 'Add another business' : 'Set up your business'}</h2>
      <p class="mut" style="margin:0 0 12px;font-size:14px">Hoola keeps separate books for each business.</p><div class="md-form">
        <div class="md-field"><label for="bkSN">Business name</label><input class="in" id="bkSN" name="name" required></div>
        <div class="md-field"><label for="bkSZ">Who it is for</label><select class="in" id="bkSZ" name="size">${Object.entries(SIZES).slice(0, 2).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="bkSC">Country (two letters, e.g. GB)</label><input class="in" id="bkSC" name="country" maxlength="2" pattern="[A-Za-z]{2}" required></div>
        <div class="md-field"><label for="bkSK">Currency (three letters, e.g. GBP)</label><input class="in" id="bkSK" name="currency" maxlength="3" pattern="[A-Za-z]{3}"></div></div>
      ${ST.setupPv ? `<div class="bk-pv"><b>What turns on</b><ul>${(ST.setupPv.lines || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></div>` : ''}
      <div class="md-acts"><span class="mut" style="font-size:12.5px">${ST.setupPv ? 'Look it over, then confirm.' : 'You see what turns on before anything is made.'}</span>
        ${ST.setupPv ? `<div style="display:flex;gap:8px"><button class="btn soft" type="button" data-setupcancel="1">Change</button><button class="btn" type="button" data-setupok="1">Confirm</button></div>` : '<button class="btn" type="submit">Show me</button>'}</div></form>`;
    if (!w) return head('Set up your books', 'Tell Hoola which business these books are for.') + setup;
    const accts = (ST.chart && ST.chart.accounts) || [];
    return `${head('Settings & exports', 'How your books are set up. Nothing here touches a locked month.')}
      <section class="card"><h2 class="md-h2">This business</h2>
        ${[['Name', w.name], ['Countries', (w.countries || []).join(', ')], ['Books currency', w.currency], ['Kind', SIZES[w.size] || w.size]].map(([k, v]) => `<div class="bk-kv"><span class="mut">${esc(k)}</span><span>${esc(v)}</span></div>`).join('')}
        <p class="mut" style="font-size:12.5px;margin:10px 0 0">Tax rates are yours to set on each invoice or bill. A country's rate in Hoola's rules is shown, never used, until checked.</p></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Chart of accounts</h2>
          ${accts.length ? `<div class="bk-coa">${accts.map(a => `<div class="bk-kv"><span><span class="mut num">${esc(a.code)}</span> ${esc(a.name)}</span><span class="pill">${esc(a.type)}</span></div>`).join('')}</div>` : '<p class="mut">Reading…</p>'}
          <form data-form="account" class="bk-acc"><label class="sr" for="bkNC">Code</label><input class="in sm" id="bkNC" name="code" placeholder="Code" pattern="[0-9]{3,8}" required>
            <label class="sr" for="bkNN">Name</label><input class="in sm" id="bkNN" name="name" placeholder="Name" required>
            <label class="sr" for="bkNT">Type</label><select class="in sm" id="bkNT" name="type">${['expense', 'income', 'asset', 'liability', 'equity'].map(t => `<option>${t}</option>`).join('')}</select>
            <button class="btn soft sm" type="submit">Add</button></form></section>
        <div style="display:flex;flex-direction:column;gap:16px">
          <section class="card"><h2 class="md-h2">How much Hoola does</h2><p style="margin:0"><b>${esc(d.trust || 'Learning')}.</b> ${esc(TRUST[d.trust] || TRUST.Learning)}</p>
            <p class="mut" style="font-size:12.5px;margin:10px 0 0">Change it on AI Employees.</p></section>
          <section class="card"><h2 class="md-h2">Bring data in, take it out</h2>
            <div class="bk-kv"><span>Bank statements</span><button class="btn soft sm" type="button" data-go="bank/import">Import</button></div>
            <div class="bk-kv"><span>Files for your accountant</span><button class="btn soft sm" type="button" data-go="close">Choose</button></div>
            ${(w.countries || []).includes('IN') ? '<div class="bk-kv"><span>India: GST returns and Tally</span><a class="btn soft sm" href="/console/accounts">GST &amp; Accounts</a></div>' : ''}</section>
          ${setup}</div></div>`;
  }

  /* ---------------------------------------------------------------- page actions */
  function onChange(e) {
    if (e.target.dataset.period) { ST.period = e.target.value; ST.ck = ST.rep = null; showPage(true); }
  }
  async function onPageClick(e) {
    const t = e.target.closest('button,a'); if (!t) return;
    const ds = t.dataset;
    try {
      if (ds.go) { e.preventDefault(); if (ds.go === 'docs/receipt') ST.receipt = null; location.hash = '#/' + ds.go; return; }
      if (ds.dk) { ST.docKind = ds.dk; showPage(true); return; }
      if (ds.addline) { ST.lines = Math.min(ST.lines + 1, 20); keepForm(() => showPage(true)); return; }
      if (ds.issue) { t.disabled = true; const r = await books('issue', {doc: ds.issue}); toast((r.number ? r.number + ' - ' : '') + 'posted to the books. You send or pay it yourself.');
        ST.docs = null; ST.receipt = null; await refreshDesk(false); if (ST.tab === 'docs') { location.hash = '#/docs'; showPage(true); } return; }
      if (ds.apply || ds.applysel || ds.post) {
        t.disabled = true;
        if (ds.post) await books('post_bank', {txn: ds.post, code: $('#bkAc_' + CSS.escape(ds.post)).value});
        else await books('apply_match', {txn: ds.apply || ds.applysel, doc: ds.apply ? ds.doc : $('#bkCh_' + CSS.escape(ds.applysel)).value});
        toast('Posted to the books.'); ST.matches = ST.recon = ST.docs = ST.ar = ST.ap = ST.ck = null; await refreshDesk(false); showPage(true); return;
      }
      if (ds.remind) { send(`Draft a polite payment reminder to ${ds.remind} for what is overdue. I will send it myself.`); return; }
      if (ds.export) {
        t.disabled = true;
        const r = await books('export', {format: ds.export, since: ST.period + '-01', upto: monthEnd(ST.period)});
        const ext = ds.export === 'tally' ? 'xml' : 'csv';
        const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([r.text], {type: ext === 'xml' ? 'application/xml' : 'text/csv'}));
        a.download = `books-${ST.period}-${ds.export}.${ext}`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        toast(`${r.journals} journal${r.journals === 1 ? '' : 's'} in the file.`); t.disabled = false; return;
      }
      if (ds.setupcancel) { ST.setupPv = null; keepForm(() => showPage(true)); return; }
      if (ds.setupok) {
        t.disabled = true;
        const r = await api('POST', '/api/fin/setup/apply', {answers: ST.setupPv.answers, hash: ST.setupPv.hash});
        const id = r.id || (r.workspace && r.workspace.id);
        ST.setupPv = null;
        if (id) await api('PUT', '/api/books/workspace', {workspace: id});
        clearCache(); await refreshDesk(false); toast('Your books are ready.'); location.hash = '#/today'; showPage(); return;
      }
    } catch (err) { toast(err.message, true); t.disabled = false; }
  }
  function keepForm(fn) {     // redraw a form page without losing what she typed
    const vals = {}; $('#mdPage').querySelectorAll('input[id],select[id],textarea[id]').forEach(x => { if (x.type !== 'file') vals[x.id] = x.value; });
    fn();
    Object.entries(vals).forEach(([id, v]) => { const x = document.getElementById(id); if (x) x.value = v; });
  }
  async function onSubmit(e) {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form, fd = new FormData(f), v = k => S(fd.get(k)).trim();
    const btn = e.submitter || f.querySelector('button[type=submit]'); if (btn) btn.disabled = true;
    try {
      if (kind === 'doc') {
        const lines = []; for (let i = 0; i < ST.lines; i++) if (v('d' + i) && v('p' + i)) lines.push({description: v('d' + i), qty: v('q' + i) || 1, price: v('p' + i), tax_pct: v('t' + i) || 0});
        const a = {party: v('party'), issue: v('issue'), due: v('due') || v('issue'), currency: v('currency').toUpperCase(), lines, issue_now: btn && btn.value === 'issue'};
        if (v('rate')) a.rate = Number(v('rate'));
        const r = await books(f.dataset.kind === 'sales' ? 'invoice' : 'bill', a);
        toast(r.number ? `${r.number} posted to the books.` : 'Saved as a draft.'); ST.lines = 1; ST.docs = null; ST.docKind = r.status === 'draft' ? 'draft' : f.dataset.kind;
        await refreshDesk(false); location.hash = '#/docs'; return;
      }
      if (kind === 'receipt') { ST.receipt = await books('receipt', {text: v('text')}); ST.docs = null; keepForm(() => showPage(true)); return; }
      if (kind === 'import') {
        const file = fd.get('file'); if (!file || !file.size) throw new Error('Choose the statement file.');
        if (file.size > 10 * 1024 * 1024) throw new Error('The file is over 10 MB.');
        const r = await api('POST', `/api/fin/${enc(ws().id)}/import`, {text: await file.text(), account: v('account') || 'Main account', currency: v('currency').toUpperCase()});
        toast(`${r.added ?? r.imported ?? 0} new line${(r.added ?? r.imported) === 1 ? '' : 's'} read${r.already_there ? `, ${r.already_there} already there` : ''}.`);
        ST.matches = ST.recon = null; await refreshDesk(false); location.hash = '#/bank'; return;
      }
      if (kind === 'asset') { await books('asset', {name: v('name'), cost: v('cost'), start: v('start'), life_months: Number(v('life_months') || 36)}); toast('Added. Its depreciation is posted at month-end.'); f.reset(); return; }
      if (kind === 'lock') {
        await books('close_lock', {period: ST.ck.period, hash: ST.ck.hash, exceptions: v('exceptions')});
        toast(`${ST.ck.period} is locked.`); ST.ck = null; await refreshDesk(false); showPage(true); return;
      }
      if (kind === 'account') { await books('add_account', {code: v('code'), name: v('name'), type: v('type')}); ST.chart = null; toast('Account added.'); showPage(true); return; }
      if (kind === 'setup') {
        const cc = v('country').toUpperCase();
        ST.setupPv = await api('POST', '/api/fin/setup/preview', {answers: {size: v('size'), countries: [cc], currency: v('currency').toUpperCase(), name: v('name'), wants: ['books']}});
        keepForm(() => showPage(true)); return;
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
    const box = $('#mdFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/books/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    const key = ST.tab;
    box.innerHTML = (STARTERS[key] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
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
    if (ST.working && !working) { clearCache(); refreshDesk(true); }   // a turn ended: what it drafted or posted shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these into my books' : 'Read this into my books';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'bk' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
