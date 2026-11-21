/* v0.999.81 CUSTOMER SUPPORT DESK - the Customer Support employee's own section (the Telecaller desk's twin; owner: "NOW
   LETS MOVE TO NEXT EMPLOYEE" -> the 7-screen design claude.ai/artifact/EhbGoFv5QCxmbvkBQw8y5F -> "GO BUILD").
   A thin top bar, then the Support chat (its own conversation, kind 'support') beside the desk's pages: Today, Inbox (+ one
   ticket), Knowledge (+ saved replies), Approvals, Reports, Channels & settings. The chat column is never redrawn when a page
   changes. Approving drafts, deciding a refund or exception and the service rules stay her taps here; a money decision whose
   fingerprint is set up is finished on her phone. Engine: /api/seva/*. Routes: #/<page>, #/ticket/<number>. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const num = v => Number(v || 0).toLocaleString('en-IN');
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
    if (!r.ok) { const e = new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`); e.status = r.status; throw e; }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', head: '<path d="M4 13a8 8 0 0 1 16 0v4a2 2 0 0 1-2 2h-1v-6h3M4 13v4a2 2 0 0 0 2 2h1v-6H4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['inbox', 'Inbox'], ['knowledge', 'Knowledge'], ['approvals', 'Approvals'], ['reports', 'Reports'],
    ['settings', 'Channels & settings']];
  const STARTERS = {
    today: ['What came in today?', 'Which tickets are late?', 'What needs my yes?'],
    inbox: ['Open a ticket for a caller', 'Which customers are waiting longest?', 'Join the duplicate tickets'],
    knowledge: ['Add my refund policy', 'Read my price list into answers', 'Which questions could you not answer?'],
    approvals: ['Why is this refund outside my policy?', 'How much did I refund this month?', 'Explain the waiting requests'],
    reports: ['How is support doing this month?', 'What do customers write about most?', 'What would help most?'],
    settings: ['Set reply times for a clinic', 'Refunds within 10 days', 'Who is my grievance officer?'],
    setup: ['Which kind of business should I pick?', 'What changes if I add more countries?', 'What does working on top of my helpdesk mean?']};
  const PRI = {urgent: 'bad', high: 'warn', normal: '', low: ''};
  const STATUS = {new: 'New', open: 'Open', pending: 'Waiting on customer', on_hold: 'On hold', resolved: 'Solved', closed: 'Closed', merged: 'Joined'};
  const CHANNEL = {whatsapp: 'WhatsApp', hoola: 'Hoola Network', phone: 'Phone call', walkin: 'Walk-in', email: 'Email', other: 'Other', test: 'Test'};
  const MAXF = 20, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, side: 'left', folded: false, files: [], timers: [], filter: 'open', q: '', days: 30, test: null,
    exc: {}};
  try { ST.side = localStorage.getItem('hoola.support.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.support.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/support/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.head, '')}</div>
        <h1 class="sd-h">Your Customer Support is not hired yet</h1>
        <p class="lead">It answers your customers only from your own knowledge, opens a ticket for every real problem, and brings every refund or exception to you. Hire it here or from AI Employees.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="spHire">Hire Customer Support</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#spHire').onclick = async () => { try { await api('POST', '/api/employees/support/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame(); readTab(); paintTabs(); showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 30000));
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    if (parts[0] === 'ticket' && parts[1]) { ST.tab = 'ticket'; ST.arg = decodeURIComponent(parts[1]); return; }
    if (parts[0] === 'setup') { ST.tab = 'setup'; ST.arg = ''; return; }
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today'; ST.arg = '';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.head, '')}</div>
          <div style="min-width:0"><div class="sd-name">Customer Support</div>
            <div class="sd-site">Answers only from your knowledge. Refunds and exceptions wait for you.</div></div>
          <span id="spState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Support chat">
          <div class="sd-chathead"><div class="t"><b>Support chat</b><span>Ask, change or add answers · attach a price list or policy</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="ac-files" id="adFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="adPick" multiple hidden accept=".csv,.xlsx,.xlsm,.txt,.md,application/pdf,.pdf,.docx,image/*">
          <input type="file" id="spPickOne" hidden accept=".txt,.md,application/pdf,.pdf,.docx,.csv,.xlsx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Customer Support desk" id="sdTabs"></nav>
          <div id="spPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or attach a price list / policy…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#adPick').click()});
    $('#adPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.support.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`; foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.support.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon(); if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/support/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#spPage').addEventListener('click', onClick);
    $('#spPage').addEventListener('submit', onSubmit);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d || {}, el = $('#spState'); if (!el) return;
    const need = (d.waiting || 0) + (d.late || []).length;
    el.innerHTML = `<span class="pill ${d.status === 'paused' ? 'warn' : need ? 'warn' : 'ok'}"><span class="dt"></span>${d.status === 'paused' ? 'Paused' : need ? `${need} need${need > 1 ? '' : 's'} you` : 'Working'}</span>`;
  }
  function paintTabs() {
    const d = ST.d || {}, cur = ST.tab === 'ticket' ? 'inbox' : ST.tab === 'setup' ? 'settings' : ST.tab;
    const badge = {inbox: d.open, knowledge: (d.drafts || 0) + (d.gaps || 0), approvals: d.waiting};
    $('#sdTabs').innerHTML = TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === cur}">${esc(n)}${
      badge[k] ? `<span class="n">${num(badge[k])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(all) {
    try { ST.d = await api('GET', '/api/support/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (all || ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- page helpers */
  const pill = (cls, name) => `<span class="pill ${cls || ''}">${esc(name)}</span>`;
  const when = v => { if (!v) return ''; const d = new Date(v); return isNaN(d) ? S(v) : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const hours = h => { if (h === null || h === undefined) return '–'; const a = Math.abs(h); const t = a < 1 ? `${Math.round(a * 60)} min` : a < 48 ? `${Math.round(a * 10) / 10} h` : `${Math.round(a / 24)} days`; return t; };
  const sec = (title, body, right = '') => `<section class="card" style="display:flex;flex-direction:column;gap:12px"><div style="display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap"><h2 style="margin:0;font-size:16px;font-weight:600">${title}</h2>${right}</div>${body}</section>`;
  const head = (title, sub, right = '') => `<div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin:4px 0 2px"><div style="flex:1;min-width:220px"><h1 class="sd-h serif" style="margin:0">${title}</h1>${sub ? `<p class="mut" style="margin:6px 0 0">${sub}</p>` : ''}</div>${right}</div>`;
  const kpi = (v, n) => `<div class="card kpi"><div class="v">${esc(v)}</div><div class="n">${esc(n)}</div></div>`;
  const field = (name, label, attrs = '') => `<label class="f"><span>${esc(label)}</span><input class="in" name="${name}" ${attrs}></label>`;
  const due = t => {
    const s = t.sla || {};
    if (!['new', 'open', 'pending', 'on_hold'].includes(t.status)) return '';
    if (s.late) return pill('bad', 'Late');
    const left = s.first_response_left_h !== undefined ? s.first_response_left_h : s.resolve_left_h;
    if (left === undefined) return '';
    return pill(left < 2 ? 'warn' : '', `${s.first_response_left_h !== undefined ? 'Reply' : 'Solve'} in ${hours(left)}`);
  };
  async function showPage(quiet) {
    const box = $('#spPage'); if (!box) return;
    if (!quiet) { box.innerHTML = '<div class="empty" style="padding:28px">Loading…</div>'; $('#sdDesk').scrollTop = 0; }
    starters();
    try {
      const t = ST.tab;
      if (t === 'today') box.innerHTML = await pageToday();
      else if (t === 'inbox') box.innerHTML = await pageInbox();
      else if (t === 'ticket') box.innerHTML = await pageTicket(ST.arg);
      else if (t === 'setup') { box.innerHTML = await pageSetup(); setupWire(); }
      else if (t === 'knowledge') box.innerHTML = await pageKnowledge();
      else if (t === 'approvals') box.innerHTML = await pageApprovals();
      else if (t === 'reports') box.innerHTML = await pageReports();
      else if (t === 'settings') box.innerHTML = await pageSettings();
    } catch (e) { box.innerHTML = `<div class="card"><p class="lead">${esc(e.message)}</p><button class="btn soft sm" type="button" data-act="reload">Try again</button></div>`; }
  }
  const tRow = t => `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/ticket/${enc(t.number)}">${esc(t.number)} · ${esc(t.customer || 'Customer')}</a> ${pill(PRI[t.priority], t.priority)} ${due(t)}</div>
    <div class="s">${esc(CHANNEL[t.channel] || t.channel)} · ${esc(t.category_label || '')} · ${esc(STATUS[t.status] || t.status)} · ${esc(S(t.text).slice(0, 140))}</div></div><a class="btn sm soft" href="#/ticket/${enc(t.number)}">Open</a></div>`;

  /* ---------------------------------------------------------------- Today */
  async function pageToday() {
    const d = ST.d || {}, w = d.week || {};
    const [tk, ex] = await Promise.all([api('GET', '/api/seva/tickets?status=open'), api('GET', '/api/seva/exceptions?status=pending')]);
    const open = tk.tickets || [], late = open.filter(t => (t.sla || {}).late);
    const needs = [
      ...(ex.exceptions || []).map(e => `<div class="row">${pill('warn', e.kind_label.split(' (')[0])}<div style="flex:1;min-width:0"><div class="t">${esc(e.number)} · ${esc(e.customer || '')}${e.amount_text ? ' · ' + esc(e.amount_text) : ''}</div><div class="s">${esc((e.check || {}).within ? 'Within your rules - still your decision.' : 'Outside your rules: ' + ((e.check || {}).reasons || []).join(' '))}</div></div><a class="btn sm" href="#/approvals">Decide</a></div>`),
      ...late.slice(0, 6).map(t => `<div class="row">${pill('bad', 'Late')}<div style="flex:1;min-width:0"><div class="t">${esc(t.number)} · ${esc(t.customer || '')}</div><div class="s">${esc(S(t.text).slice(0, 120))}</div></div><a class="btn sm soft" href="#/ticket/${enc(t.number)}">Open</a></div>`),
      ...(d.drafts ? [`<div class="row">${pill('v', 'Draft')}<div style="flex:1"><div class="t">${num(d.drafts)} draft answer${d.drafts > 1 ? 's' : ''} to check</div></div><a class="btn sm soft" href="#/knowledge">Check</a></div>`] : []),
      ...(d.gaps ? [`<div class="row">${pill('warn', 'No answer')}<div style="flex:1"><div class="t">${num(d.gaps)} customer question${d.gaps > 1 ? 's' : ''} your knowledge could not answer</div></div><a class="btn sm soft" href="#/knowledge">Answer</a></div>`] : [])].join('');
    const nAns = w.answered_by_kb || 0, nQ = w.questions || 0;
    const setupCard = d.setup_done ? '' : `<section class="card" id="spSetupCard" style="display:flex;gap:14px;align-items:center;flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t" style="font-weight:600">Set up Customer Support for your business</div><div class="s">Eight short questions: your size, kind of business, countries, languages and channels. Hoola then shows only what you need.</div></div><a class="btn" href="#/setup">Start setup</a></section>`;
    return `${head(needs ? 'A few things need you.' : 'Nothing needs you right now.', esc(d.say || ''))}${setupCard}
      <div class="grid">${kpi(num(d.open), 'open tickets')}${kpi(num((d.late || []).length), 'past the reply time')}${kpi(nQ ? `${num(nAns)} of ${num(nQ)}` : '–', 'questions answered from knowledge (7 days)')}${kpi(w.csat_avg ? `${w.csat_avg} / 5` : '–', `rating (${num(w.csat_count)} replies)`)}</div>
      ${sec('Needs you', needs || '<p class="mut" style="margin:0">Nothing waits for you.</p>')}
      ${sec('Open tickets', open.slice(0, 8).map(tRow).join('') || '<p class="mut" style="margin:0">No open tickets.</p>', '<a class="btn soft sm" href="#/inbox">Inbox</a>')}
      ${d.answers ? '' : sec('Start here', `<p class="mut" style="margin:0">Your knowledge is empty, so Hoola cannot answer customers yet. Add your timings, prices and refund rules on <a href="#/knowledge">Knowledge</a>, or attach your price list in the chat.</p>`)}`;
  }

  /* ---------------------------------------------------------------- Inbox */
  async function pageInbox() {
    const f = ST.filter;
    const r = await api('GET', `/api/seva/tickets?status=${enc(f === 'all' ? '' : f)}&q=${enc(ST.q)}`);
    const rows = (r.tickets || []).map(t => `<tr><td><a href="#/ticket/${enc(t.number)}"><b>${esc(t.number)}</b></a></td><td>${esc(t.customer || '–')}<div class="mut" style="font-size:12.5px">${esc(CHANNEL[t.channel] || t.channel)}</div></td>
      <td>${esc(S(t.text).slice(0, 110))}</td><td>${pill(PRI[t.priority], t.priority)}</td><td>${esc(STATUS[t.status] || t.status)} ${due(t)}</td><td class="mut">${esc(when(t.created))}</td></tr>`).join('');
    const dup = (r.duplicates || []).map(x => `<div class="row"><div style="flex:1"><div class="t">${esc(x.a)} and ${esc(x.b)} look like one problem</div><div class="s">${esc(x.customer || '')}</div></div><button class="btn sm soft" type="button" data-merge="${esc(x.b)}" data-into="${esc(x.a)}">Join ${esc(x.b)} into ${esc(x.a)}</button></div>`).join('');
    const fb = (k, n) => `<button class="chip${f === k ? ' on' : ''}" type="button" data-filter="${k}" aria-pressed="${f === k}">${esc(n)}</button>`;
    return `${head('Inbox', 'Every ticket from WhatsApp, Hoola Network, calls, email and walk-ins. Late ones first.', '<button class="btn sm" type="button" data-act="newticket">New ticket</button>')}
      <div id="spNewTicket" hidden>${sec('New ticket', `<form id="spTicketForm" class="grid2" style="gap:14px">
        ${field('name', 'Customer name')}${field('phone', 'Phone (optional)', 'inputmode="tel"')}
        <label class="f"><span>How they reached you</span><select class="in" name="channel">${['phone', 'walkin', 'email', 'whatsapp', 'other'].map(c => `<option value="${c}">${esc(CHANNEL[c])}</option>`).join('')}</select></label>
        <label class="f"><span>Priority</span><select class="in" name="priority"><option value="">Let Hoola set it</option><option>urgent</option><option>high</option><option>normal</option><option>low</option></select></label>
        <label class="f" style="grid-column:1/-1"><span>The problem, in their words</span><textarea class="in" name="text" rows="3" required></textarea></label>
        <div><button class="btn sm" type="submit">Open the ticket</button></div></form>`)}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">${fb('open', 'Open')}${fb('pending', 'Waiting on customer')}${fb('resolved', 'Solved')}${fb('all', 'All')}
        <form id="spFind" style="margin-left:auto;display:flex;gap:6px"><label class="sr" for="spQ">Search tickets</label><input class="in" id="spQ" name="q" value="${esc(ST.q)}" placeholder="Name, number or words" style="min-width:220px"><button class="btn soft sm" type="submit">Search</button></form></div>
      ${dup ? sec('Might be the same problem', dup) : ''}
      <section class="card" style="overflow-x:auto;padding:4px 16px">${rows ? `<table class="tb"><thead><tr><th>Ticket</th><th>Customer</th><th>Problem</th><th>Priority</th><th>Status</th><th>Opened</th></tr></thead><tbody>${rows}</tbody></table>` : '<p class="mut" style="padding:14px 0;margin:0">No tickets here.</p>'}</section>`;
  }
  async function pageTicket(ref) {
    const [t, mac] = await Promise.all([api('GET', `/api/seva/tickets/${enc(ref)}`), api('GET', '/api/seva/macros')]);
    ST.ticket = t;
    const s = t.sla || {};
    const notes = (t.notes || []).map(n => `<div class="${n.public ? 'ai' : 'note'}"><span class="who">${n.public ? 'To the customer' : 'Internal note'} · ${esc(n.by || '')} · ${esc(when(n.at))}</span>${esc(n.text)}</div>`).join('');
    const macros = (mac.macros || []).filter(m => m.status === 'approved');
    const ex = (t.exceptions || []).map(e => `<div class="row">${pill(e.status === 'pending' ? 'warn' : e.status === 'rejected' ? 'bad' : 'ok', e.status)}<div style="flex:1"><div class="t">${esc(e.number)} · ${esc(e.kind_label)} ${esc(e.amount_text || '')}</div></div></div>`).join('');
    const legal = (t.legal || []).map(x => `<p class="mut" style="margin:0;font-size:13px">${esc(typeof x === 'string' ? x : (x.text || ''))}</p>`).join('');
    const open = ['new', 'open', 'pending', 'on_hold'].includes(t.status);
    return `<div><a class="btn soft sm" href="#/inbox">← Inbox</a></div>
      ${head(`${esc(t.number)} · ${esc(t.customer || 'Customer')}`, esc(`${CHANNEL[t.channel] || t.channel} · ${t.category_label || ''} · opened ${when(t.created)}`), `${pill(PRI[t.priority], t.priority)} ${pill(open ? 'v' : 'ok', STATUS[t.status] || t.status)}`)}
      <div class="grid2">
        <div style="display:flex;flex-direction:column;gap:18px">
          ${sec('The conversation', `<div class="tline"><div class="me"><span class="who">${esc(t.customer || 'Customer')}</span>${esc(t.text)}</div>${notes}</div>`)}
          ${open ? sec('Reply to the customer', `<form id="spReply" style="display:flex;flex-direction:column;gap:10px">
            ${macros.length ? `<label class="f"><span>Saved reply</span><select class="in" name="macro"><option value="">Write my own</option>${macros.map(m => `<option value="${esc(m.name)}">${esc(m.name)}</option>`).join('')}</select></label>` : ''}
            <label class="f"><span>Your words (they see this)</span><textarea class="in" name="text" rows="3"></textarea></label>
            <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="submit">Send</button><span class="mut" style="font-size:12.5px;align-self:center">Goes on WhatsApp or the Hoola Network when the customer came from there; otherwise it is a draft you send.</span></div></form>`) : ''}
          ${sec('Internal note', `<form id="spNote" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spNoteText">Internal note</label><input class="in" id="spNoteText" name="text" required placeholder="Only you and your team see this" style="flex:1;min-width:200px"><button class="btn soft sm" type="submit">Add note</button></form>`)}
        </div>
        <div style="display:flex;flex-direction:column;gap:18px">
          ${sec('Deadline', `<div class="t">${s.late ? '<b style="color:var(--badt)">Past the reply time</b>' : s.first_response_left_h !== undefined ? `First reply due in ${hours(s.first_response_left_h)}` : s.resolve_left_h !== undefined ? `Solve within ${hours(s.resolve_left_h)}` : 'Closed'}</div>
            <p class="mut" style="margin:0;font-size:13px">Reply within ${hours(s.first_response_h)}, solve within ${hours(s.resolve_h)}${s.paused ? ' · clock paused while you wait on the customer' : ''}.</p>${legal}`)}
          ${sec('Change', `<form id="spUpdate" class="grid2" style="gap:12px">
            <label class="f"><span>Status</span><select class="in" name="status">${['open', 'pending', 'on_hold', 'resolved', 'closed'].map(x => `<option value="${x}"${t.status === x ? ' selected' : ''}>${esc(STATUS[x])}</option>`).join('')}</select></label>
            <label class="f"><span>Priority</span><select class="in" name="priority">${['urgent', 'high', 'normal', 'low'].map(x => `<option${t.priority === x ? ' selected' : ''}>${x}</option>`).join('')}</select></label>
            ${field('assignee', 'Given to', `value="${esc(t.assignee || '')}" placeholder="Hoola"`)}
            ${field('public', 'Line the customer sees with the status', `value="${esc(t.customer_line || '')}"`)}
            <div><button class="btn soft sm" type="submit">Save</button></div></form>`)}
          ${sec('Refund or exception', `${ex}<form id="spAsk" class="grid2" style="gap:12px">
            <label class="f"><span>What</span><select class="in" name="kind"><option value="refund">Refund</option><option value="waiver">Waive a charge</option><option value="goodwill">Discount or credit</option><option value="replacement">Replacement</option><option value="extension">More time / outside warranty</option><option value="other">Something else</option></select></label>
            ${field('amount', 'Amount (if money)', 'type="number" min="0" step="1"')}
            <label class="f" style="grid-column:1/-1"><span>Why</span><input class="in" name="reason" required></label>
            <div><button class="btn soft sm" type="submit">Put it on Approvals</button></div></form>`)}
        </div></div>`;
  }

  /* ---------------------------------------------------------------- Knowledge */
  async function pageKnowledge() {
    const [kb, mac, su] = await Promise.all([api('GET', '/api/seva/kb'), api('GET', '/api/seva/macros'), api('GET', '/api/support/setup').catch(() => ({}))]);
    ST.packQs = su.done ? ((su.pack || {}).knowledge_questions || []) : [];
    const entries = kb.entries || [], drafts = entries.filter(e => e.status === 'draft'), live = entries.filter(e => e.status !== 'draft');
    const gaps = (kb.gaps || []).map((g, i) => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">“${esc(g.question)}”</div><div class="s">asked ${num(g.times)} time${g.times > 1 ? 's' : ''}</div></div>
      <form class="spGap" data-q="${esc(g.question)}" style="display:flex;gap:6px;flex:1 1 320px"><label class="sr" for="spGap${i}">Answer for: ${esc(g.question)}</label><input class="in" id="spGap${i}" name="answer" required placeholder="Your answer" style="flex:1"><button class="btn sm" type="submit">Save answer</button></form></div>`).join('');
    const drows = drafts.map(e => `<label class="row" style="align-items:flex-start;cursor:pointer"><input type="checkbox" name="d" value="${esc(e.id)}" checked style="width:18px;height:18px;margin-top:3px"><div style="flex:1;min-width:0"><div class="t">${esc(e.question)}</div><div class="s">${esc(e.answer)}</div><div class="mut" style="font-size:12px">From: ${esc(e.source)}</div></div></label>`).join('');
    const lrows = live.map(e => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${pill(e.kind === 'policy' ? 'v' : '', e.kind === 'policy' ? 'Policy' : 'Question')} ${esc(e.question)}</div><div class="s">${esc(e.answer)}</div><div class="mut" style="font-size:12px">${esc(e.source)} · used ${num(e.hits)} time${e.hits === 1 ? '' : 's'}</div></div><button class="btn soft sm" type="button" data-kbdel="${esc(e.id)}" aria-label="Remove: ${esc(e.question)}">Remove</button></div>`).join('');
    const ms = (mac.macros || []).map(m => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${esc(m.name)} ${pill(m.status === 'approved' ? 'ok' : 'warn', m.status === 'approved' ? 'In use' : 'Waits for your OK')}</div><div class="s">${esc((m.texts || {}).english || Object.values(m.texts || {})[0] || '')}</div><div class="mut" style="font-size:12px">${esc(Object.keys(m.texts || {}).join(', '))} · used ${num(m.uses)}</div></div>${m.status !== 'approved' ? `<button class="btn sm" type="button" data-macok="${esc(m.id)}">Approve</button>` : ''}<button class="btn soft sm" type="button" data-macdel="${esc(m.id)}" aria-label="Remove saved reply ${esc(m.name)}">Remove</button></div>`).join('');
    const tl = ST.test ? `<div class="card" style="background:var(--soft)" id="spTestLine"><b>${esc({answered: 'Hoola would answer', clarify: 'Hoola would ask which one', unknown: 'Hoola would not guess'}[ST.test.status] || ST.test.status)}</b><p class="say" style="margin:6px 0 0">${esc(ST.test.reply || ST.test.say || '')}</p>${ST.test.source ? `<p class="mut" style="margin:6px 0 0;font-size:12.5px">From: ${esc(ST.test.source)}${ST.test.confidence !== undefined ? ` · match ${Math.round(100 * ST.test.confidence)}%` : ''}</p>` : ''}</div>` : '';
    const packQ = (ST.packQs || []).length ? sec('Questions most businesses like yours answer', `<p class="mut" style="margin:0">From your industry pack. Answer the ones that apply; each becomes a live answer.</p>${ST.packQs.map((q, i) => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">${esc(q)}</div></div><form class="spGap" data-q="${esc(q)}" style="display:flex;gap:6px;flex:1 1 320px"><label class="sr" for="spPq${i}">Answer for: ${esc(q)}</label><input class="in" id="spPq${i}" name="answer" required placeholder="Your answer" style="flex:1"><button class="btn sm" type="submit">Save answer</button></form></div>`).join('')}`) : '';
    return `${head('What Hoola may say', 'Customers are answered only from these answers, and Hoola names the one it used. Anything not here comes to you.')}${packQ}
      ${gaps ? sec('Customers asked, Hoola could not answer', `<p class="mut" style="margin:0">Answer once and Hoola uses it from now on.</p>${gaps}`) : ''}
      ${drows ? sec(`Drafts to check · ${num(drafts.length)}`, `<form id="spApprove" style="display:flex;flex-direction:column;gap:0">${drows}<div style="padding-top:10px"><button class="btn sm" type="submit">Approve the ticked ones</button></div></form>`) : ''}
      ${sec('Try a question', `<form id="spTest" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spTestQ">A customer's question</label><input class="in" id="spTestQ" name="question" required placeholder="What are your timings?" style="flex:1;min-width:220px"><button class="btn soft sm" type="submit">Ask as a customer</button></form>${tl}`)}
      ${sec(`Live answers · ${num(live.length)}`, lrows || '<p class="mut" style="margin:0">None yet.</p>')}
      ${sec('Add an answer', `<form id="spKbAdd" class="grid2" style="gap:14px">
        <label class="f"><span>Kind</span><select class="in" name="kind"><option value="faq">A question customers ask</option><option value="policy">A rule (refunds, delivery, warranty)</option></select></label>
        ${field('question', 'Question or rule name', 'required placeholder="What are your timings?"')}
        <label class="f" style="grid-column:1/-1"><span>The answer, in your words</span><textarea class="in" name="answer" rows="2" required></textarea></label>
        ${field('aliases', 'Other ways people ask it (comma separated)', 'placeholder="when are you open, office hours"')}
        <div style="align-self:end"><button class="btn sm" type="submit">Add - goes live now</button></div></form>`)}
      ${sec('Read a file or a page into drafts', `<form id="spImport" class="grid2" style="gap:14px">
        ${field('url', 'A page of your own website', 'placeholder="https://"')}
        <label class="f"><span>Or paste text</span><textarea class="in" name="text" rows="2" placeholder="Q: … A: …"></textarea></label>
        <div style="display:flex;gap:8px;flex-wrap:wrap;grid-column:1/-1"><button class="btn sm" type="submit">Read into drafts</button><button class="btn soft sm" type="button" data-act="kbfile">Choose a file (PDF, Word, Excel, text)</button><span class="mut" style="font-size:12.5px;align-self:center">Drafts go live only after you approve them. An answer with a number that is not in your file is dropped.</span></div></form>`)}
      ${sec('Saved replies', `${ms || '<p class="mut" style="margin:0">None yet.</p>'}<form id="spMacro" class="grid2" style="gap:14px">
        ${field('name', 'Name', 'required placeholder="First answer to a complaint"')}
        <label class="f"><span>Text (you may use {name} {ticket} {status} {business})</span><input class="in" name="text" required></label>
        <div><button class="btn soft sm" type="submit">Add - Hoola translates it, you approve</button></div></form>`)}`;
  }

  /* ---------------------------------------------------------------- Approvals */
  async function pageApprovals() {
    const r = await api('GET', '/api/seva/exceptions');
    const all = r.exceptions || [];
    ST.exc = Object.fromEntries(all.map(e => [e.id, e]));
    const pend = all.filter(e => e.status === 'pending');
    const toPay = all.filter(e => e.status === 'approved' && e.amount && ['refund', 'goodwill', 'waiver'].includes(e.kind));
    const done = all.filter(e => !['pending'].includes(e.status)).slice(0, 30);
    const card = e => { const c = e.check || {};
      return `<article class="card" style="display:flex;flex-direction:column;gap:10px" aria-label="${esc(e.number)}">
        <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="mut" style="font-size:12.5px">${esc(e.number)}${e.ticket_id ? ' · from a ticket' : ''} · ${esc(when(e.created))}</div>
          <h2 style="margin:4px 0 0;font-size:17px;font-weight:600">${esc(e.kind_label)} · ${esc(e.customer || 'Customer')}</h2>
          <p style="margin:6px 0 0;font-size:14px;line-height:1.55">${esc(e.reason)}</p></div>${e.amount_text ? `<div style="font-size:24px;font-weight:600">${esc(e.amount_text)}</div>` : ''}</div>
        <div class="row" style="padding:8px 0">${pill(c.within ? 'ok' : 'warn', c.within ? 'Within your rules' : 'Outside your rules')}<div class="s" style="flex:1">${esc((c.reasons || []).join(' ') || (c.within ? 'It fits your written policy - the decision is still yours.' : ''))}${e.days_since !== null && e.days_since !== undefined ? ` Asked ${num(e.days_since)} days after.` : ''}</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end"><button class="btn soft sm" type="button" data-cancel="${esc(e.id)}">Withdraw</button><button class="btn soft sm" type="button" data-decide="${esc(e.id)}" data-yes="0">No</button><button class="btn sm" type="button" data-decide="${esc(e.id)}" data-yes="1">Yes</button></div>
        <p class="mut" style="margin:0;font-size:12.5px">Hoola never moves money. After a yes you pay from your bank or gateway; then mark it paid and Hoola tells the customer.</p></article>`; };
    const pay = toPay.map(e => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:220px"><div class="t">${esc(e.number)} · ${esc(e.kind_label)} ${esc(e.amount_text)} · ${esc(e.customer)}</div><div class="s">You said yes on ${esc(when(e.decided))}</div></div>
      <form class="spSent" data-id="${esc(e.id)}" style="display:flex;gap:6px"><label class="sr" for="spRef${esc(e.id)}">Payment reference</label><input class="in" id="spRef${esc(e.id)}" name="ref" placeholder="UTR / reference (optional)"><button class="btn sm" type="submit">I have paid</button></form></div>`).join('');
    const rows = done.map(e => `<tr><td>${esc(e.number)}</td><td>${esc(e.kind_label)} ${esc(e.amount_text || '')}</td><td>${esc(e.customer || '')}</td><td>${pill(e.status === 'rejected' || e.status === 'cancelled' ? 'bad' : 'ok', {approved: 'Yes - to pay', rejected: 'No', sent: 'Paid', cancelled: 'Withdrawn'}[e.status] || e.status)}</td><td class="mut">${esc(when(e.decided || e.created))}</td></tr>`).join('');
    return `${head('Waiting for your yes', 'Refunds, waivers, discounts, replacements and anything else outside your written policy. Hoola never promises these to a customer.')}
      ${pend.map(card).join('') || '<section class="card"><p class="mut" style="margin:0">Nothing waits for you.</p></section>'}
      ${pay ? sec('Approved - still to pay', pay) : ''}
      ${rows ? sec('Decided', `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Number</th><th>What</th><th>Customer</th><th>You said</th><th>When</th></tr></thead><tbody>${rows}</tbody></table></div>`) : ''}`;
  }

  /* ---------------------------------------------------------------- Reports */
  async function pageReports() {
    const r = await api('GET', `/api/seva/report?days=${ST.days}`);
    const dbtn = n => `<button class="chip${ST.days === n ? ' on' : ''}" type="button" data-days="${n}" aria-pressed="${ST.days === n}">${n} days</button>`;
    const pct = v => v === null || v === undefined ? '–' : `${v}%`;
    const max = Math.max(1, ...(r.by_category || []).map(x => x.count));
    const cats = (r.by_category || []).map(x => `<div style="display:flex;gap:12px;align-items:center;font-size:14px"><span style="width:150px">${esc(x.label)}</span><div class="bar" style="flex:1;height:12px"><i style="width:${Math.round(100 * x.count / max)}%;height:12px"></i></div><span style="width:40px;text-align:right">${num(x.count)}</span></div>`).join('');
    const top = (r.top_questions || []).map(x => `<div class="row"><div style="flex:1" class="t">${esc(x.question)}</div><span class="mut">${num(x.times)}×</span></div>`).join('');
    const gaps = (r.gaps || []).map(x => `<div class="row"><div style="flex:1" class="t">“${esc(x.question)}”</div><span class="mut">${num(x.times)}×</span></div>`).join('');
    const ex = r.exceptions || {};
    return `${head(`Last ${num(r.days)} days`, esc(r.say || ''), `<div style="display:flex;gap:6px">${dbtn(7)}${dbtn(30)}${dbtn(90)}</div>`)}
      <div class="grid">${kpi(num(r.tickets), 'tickets')}${kpi(pct(r.deflection_pct), 'questions answered from knowledge')}${kpi(r.first_response_median_h === null ? '–' : hours(r.first_response_median_h), 'first reply (median)')}${kpi(pct(r.resolution_sla_pct), 'solved in time')}${kpi(r.csat_avg ? `${r.csat_avg} / 5` : '–', `rating (${num(r.csat_count)})`)}</div>
      <div class="grid2">${sec('Why customers wrote', cats || '<p class="mut" style="margin:0">No tickets in this time.</p>')}
        ${sec('Refunds and exceptions', `<p style="margin:0">${num(ex.asked)} asked · ${num(ex.approved)} yes · ${num(ex.rejected)} no · ${num(ex.pending)} waiting${ex.approved_amount ? ` · ${num(ex.approved_amount)} approved in money` : ''}</p>`)}</div>
      <div class="grid2">${sec('Answered most often', top || '<p class="mut" style="margin:0">None yet.</p>')}${sec('Asked, but not in your knowledge', gaps || '<p class="mut" style="margin:0">None - every question had an answer.</p>', gaps ? '<a class="btn soft sm" href="#/knowledge">Answer them</a>' : '')}</div>
      <p class="mut" style="margin:0;font-size:12.5px">Counted from your tickets and the questions Hoola answered. Nothing is estimated.</p>`;
  }

  /* ---------------------------------------------------------------- Setup (G0: 8 questions -> profile + industry pack) */
  async function pageSetup() {
    const su = await api('GET', '/api/support/setup'); ST.setup = su; ST.preview = null;
    const a = su.answers || {}, Q = Object.fromEntries((su.questions || []).map(q => [q.key, q]));
    const radios = (key, opts) => Object.entries(opts).map(([k, n]) => `<label class="row" style="cursor:pointer;padding:8px 10px"><input type="radio" name="${key}" value="${esc(k)}"${a[key] === k ? ' checked' : ''} style="width:18px;height:18px"><span class="t">${esc(n)}</span></label>`).join('');
    const ticks = (key, opts, have) => `<div class="grid2" style="gap:4px 14px">${(Array.isArray(opts) ? opts.map(x => [x, x]) : Object.entries(opts)).map(([k, n]) => `<label style="display:flex;gap:8px;align-items:center;cursor:pointer;font-size:14px;min-height:32px"><input type="checkbox" name="${key}" value="${esc(k)}"${(have || []).includes(k) ? ' checked' : ''} style="width:18px;height:18px">${esc(n)}</label>`).join('')}</div>`;
    const ctry = (su.countries || []).map(c => `<option value="${esc(c.code)}"${(a.countries || []).includes(c.code) ? ' selected' : ''}>${esc(c.name)}</option>`).join('');
    const m = a.money || {}, t = a.team || {};
    const q = (n, key, body) => sec(`${n}. ${esc((Q[key] || {}).q || '')}`, body);
    return `${head('Set up Customer Support', 'Eight questions. Skip any you like: the usual answer is used. Nothing changes until you see the preview and tap Apply.')}
      <form id="spSetup" style="display:flex;flex-direction:column;gap:18px">
      ${q(1, 'size', `<div class="grid2" style="gap:6px">${radios('size', Q.size.options)}</div>`)}
      ${q(2, 'industry', `<label class="f"><span>Kind of business</span><select class="in" name="industry">${(su.packs || []).map(p => `<option value="${esc(p.key)}"${a.industry === p.key ? ' selected' : ''}>${esc(p.name)}</option>`).join('')}</select></label><p class="mut" style="margin:0;font-size:13px" id="spPackNote"></p>`)}
      ${q(3, 'countries', `<label class="f"><span>Find a country</span><input class="in" id="spCtryFind" placeholder="Type to filter" autocomplete="off"></label>
        <label class="sr" for="spCtry">Countries</label><select class="in" id="spCtry" name="countries" multiple size="8" style="height:auto">${ctry}</select>
        <p class="mut" style="margin:0;font-size:13px">Hold Ctrl (Cmd on a Mac) to pick several. Chosen: <span id="spCtryN"></span></p>`)}
      ${q(4, 'languages', ticks('languages', Q.languages.options, a.languages))}
      ${q(5, 'channels', ticks('channels', Q.channels.options, a.channels))}
      ${q(6, 'helpdesk', `<label class="f"><span>Helpdesk</span><select class="in" name="helpdesk">${Object.entries(Q.helpdesk.options).map(([k, n]) => `<option value="${k}"${a.helpdesk === k ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label><p class="mut" style="margin:0;font-size:13px">With a helpdesk, Hoola can work on top of it later: your tickets stay in your tool.</p>`)}
      ${q(7, 'team', `${field('people', 'People who answer customers', `type="number" min="1" value="${esc(t.people || 1)}"`)}${ticks('split', Q.team.options, t.split)}`)}
      ${q(8, 'money', `<p class="mut" style="margin:0">Leave a box empty and those requests come to you. Hoola never moves money; every step is a person's tap.</p><div class="grid2" style="gap:14px">
        ${field('agent', 'A staff member may agree up to', `type="number" min="0" value="${esc(m.agent ?? '')}"`)}${field('supervisor', 'A supervisor may agree up to', `type="number" min="0" value="${esc(m.supervisor ?? '')}"`)}
        ${field('currency', 'Currency', `value="${esc(m.currency || 'INR')}" maxlength="3" style="text-transform:uppercase"`)}</div>`)}
      ${q(9, 'data', `<label class="f"><span>Where they live</span><select class="in" name="data">${Object.entries(Q.data.options).map(([k, n]) => `<option value="${k}"${a.data === k ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>`)}
      <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn" type="submit">See what changes</button>${su.done ? '<a class="btn soft" href="#/settings">Back</a>' : ''}</div>
      </form>
      <div id="spPreview"></div>`;
  }
  function setupWire() {
    const su = ST.setup || {}, sel = $('#spCtry'), find = $('#spCtryFind'), n = $('#spCtryN'), ind = $('#spSetup [name=industry]');
    const count = () => { const c = [...sel.selectedOptions].map(o => o.textContent); n.textContent = c.length ? c.slice(0, 6).join(', ') + (c.length > 6 ? ` and ${c.length - 6} more` : '') : 'your own country'; };
    sel.addEventListener('change', count); count();
    find.addEventListener('input', () => { const w = find.value.trim().toLowerCase(); [...sel.options].forEach(o => { o.hidden = !!w && !o.textContent.toLowerCase().includes(w); }); });
    const note = () => { const p = (su.packs || []).find(x => x.key === ind.value); $('#spPackNote').textContent = p ? `Comes with ticket stages for: ${p.flows.join(', ')}.` : ''; };
    ind.addEventListener('change', note); note();
  }
  function setupAnswers(f) {
    const fd = new FormData(f), num0 = v => (S(v).trim() === '' ? null : Number(v));
    return {size: fd.get('size') || '', industry: fd.get('industry') || '', countries: fd.getAll('countries'), languages: fd.getAll('languages'),
      channels: fd.getAll('channels'), helpdesk: fd.get('helpdesk') || '', team: {people: Number(fd.get('people') || 1), split: fd.getAll('split')},
      money: {agent: num0(fd.get('agent')), supervisor: num0(fd.get('supervisor')), currency: S(fd.get('currency')).toUpperCase()}, data: fd.get('data') || ''};
  }
  function drawPreview(p) {
    const rows = (p.changes || []).map(c => `<div class="row" style="flex-wrap:wrap"><div style="flex:1 1 200px"><div class="t">${esc(c.what)}</div>${c.note ? `<div class="s">${esc(c.note)}</div>` : ''}</div>
      <div style="flex:2 1 300px;font-size:14px">${c.from ? `<span class="mut" style="text-decoration:line-through">${esc(String(c.from))}</span> → ` : ''}${esc(String(c.to))}</div></div>`).join('');
    $('#spPreview').innerHTML = sec('What setup will change', (rows || '<div class="s">Nothing changes.</div>') + `<p class="mut" style="margin:0;font-size:13px">Reply times, rules and saved replies you already set are kept. Saved replies arrive as drafts for you to check.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn" type="button" data-act="applysetup">Apply</button><button class="btn soft" type="button" data-act="editsetup">Change answers</button></div>`);
    $('#spPreview').scrollIntoView({behavior: 'smooth', block: 'start'});
  }
  /* ---------------------------------------------------------------- Channels & settings */
  async function pageSettings() {
    const [st, d] = [await api('GET', '/api/seva/settings'), ST.d || {}];
    const chs = (d.channels || []).map(c => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${esc(c.name)} ${pill({on: 'ok', off: 'warn', manual: '', soon: ''}[c.state], {on: 'On', off: 'Off', manual: 'You add tickets', soon: 'Not joined yet'}[c.state] || c.state)}</div><div class="s">${esc(c.line)}</div></div>${c.key === 'phone' ? '<a class="btn soft sm" href="/console/telecaller">Telecaller</a>' : ''}</div>`).join('');
    const sla = st.sla || {}, pol = st.policy || {};
    ST.setKind = st.kind;
    const slaRow = p => `<div class="row" style="flex-wrap:wrap"><b style="width:80px;text-transform:capitalize">${p}</b>
      <label class="f" style="flex:1;min-width:120px"><span>First reply within (hours)</span><input class="in" name="sla_${p}_0" type="number" min="0.25" step="0.25" value="${esc((sla[p] || [])[0])}"></label>
      <label class="f" style="flex:1;min-width:120px"><span>Solve within (hours)</span><input class="in" name="sla_${p}_1" type="number" min="0.25" step="0.25" value="${esc((sla[p] || [])[1])}"></label></div>`;
    const chk = (name, label) => `<label class="row" style="cursor:pointer"><input type="checkbox" name="${name}"${st[name] ? ' checked' : ''} style="width:18px;height:18px"><span class="t">${esc(label)}</span></label>`;
    const su = await api('GET', '/api/support/setup');
    const law = su.done ? ((su.pack || {}).law || []).map(l => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${pill('', l.region)} ${esc(l.text)}</div><div class="s">${esc(l.source)}</div></div>${pill('warn', 'Check this')}</div>`).join('') : '';
    const setupSec = su.done
      ? sec('Your setup', `<div class="s">${esc((su.pack || {}).name)} · ${esc(((su.questions[0] || {}).options || {})[su.answers.size] || '')} · ${esc(su.answers.countries.join(', '))} · ${esc(su.answers.languages.join(', '))}</div>
        <div class="s">Shown for you: ${esc((su.parts_on || []).join(', ') || 'the simple desk')}</div>`, `<a class="btn soft sm" href="#/setup">Change setup</a>`)
        + (law ? sec('Rules that may apply where your customers live', `<p class="mut" style="margin:0">From your industry and countries. Each has its source; check it before you rely on it. Hoola does not apply these by itself.</p>${law}`) : '')
      : sec('Your setup', `<div class="s">Not done yet.</div>`, `<a class="btn sm" href="#/setup">Start setup</a>`);
    return `${head('Channels & settings', 'Where customers reach you, and the service rules Hoola follows.')}
      ${setupSec}
      ${sec('Where customers reach you', chs)}
      <form id="spSettings" style="display:flex;flex-direction:column;gap:18px">
      ${sec('Reply times', `<label class="f"><span>Start from the usual times for</span><select class="in" name="kind">${(st.presets || []).map(k => `<option value="${k}"${st.kind === k ? ' selected' : ''}>${esc({shop: 'A shop or service business', isp: 'An internet / cable provider', ecommerce: 'An online seller', clinic: 'A clinic'}[k] || k)}</option>`).join('')}</select></label>
        ${['urgent', 'high', 'normal', 'low'].map(slaRow).join('')}`)}
      ${sec('Your refund and exception rules', `<p class="mut" style="margin:0">Anything outside these always comes to Approvals. Leave a box empty if you have no such rule.</p><div class="grid2" style="gap:14px">
        ${field('refund_days', 'Refunds allowed within (days)', `type="number" min="0" value="${esc(pol.refund_days ?? '')}"`)}
        ${field('refund_max', 'Largest refund without asking you', `type="number" min="0" value="${esc(pol.refund_max ?? '')}"`)}
        ${field('replace_days', 'Replacement within (days)', `type="number" min="0" value="${esc(pol.replace_days ?? '')}"`)}
        ${field('goodwill_max', 'Largest goodwill discount', `type="number" min="0" value="${esc(pol.goodwill_max ?? '')}"`)}
        ${field('cancel_hours', 'Free cancellation within (hours)', `type="number" min="0" value="${esc(pol.cancel_hours ?? '')}"`)}
        ${field('refund_mode', 'How refunds are paid', `value="${esc(pol.refund_mode ?? '')}" placeholder="Back to the same UPI / card"`)}</div>`)}
      ${sec('Customers and language', `<div class="grid2" style="gap:14px">
        <label class="f"><span>Default language of replies</span><select class="in" name="lang">${['english', 'hindi', 'marathi', 'hinglish'].map(l => `<option value="${l}"${st.lang === l ? ' selected' : ''}>${l[0].toUpperCase() + l.slice(1)}</option>`).join('')}</select></label>
        ${field('morning_time', 'Morning note at', `value="${esc(st.morning_time || '09:00')}" pattern="[0-2][0-9]:[0-5][0-9]"`)}</div>
        ${chk('auto_ack', 'Tell the customer at once that the ticket is open')}${chk('csat_on', 'Ask for a 1-5 rating when a ticket is solved')}${chk('ecommerce', 'I sell online (E-Commerce Rules: acknowledge in 48 hours, show a grievance officer)')}
        <div class="grid2" style="gap:14px">${field('officer', 'Grievance officer name', `value="${esc(st.officer || '')}"`)}${field('officer_contact', 'Grievance officer contact', `value="${esc(st.officer_contact || '')}"`)}</div>`)}
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><button class="btn sm" type="submit">Save the rules</button><span class="mut" style="font-size:12.5px">How much Hoola may do on its own (Learning, Partner, Trusted) is set on <a href="/console/?v=hire">AI Employees</a>. Refunds and exceptions wait for you at every level.</span></div>
      </form>`;
  }

  /* ---------------------------------------------------------------- actions */
  async function upload(file) {
    if (!ST.chat) throw new Error('The chat is not open yet.');
    const fd = new FormData(); fd.append('file', file, file.name || 'file');
    const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, {form: fd});
    return S(r.file_id || r.id);
  }
  function pickOne() {
    return new Promise(res => { const inp = $('#spPickOne'); inp.value = ''; inp.onchange = () => res(inp.files[0] || null); inp.click(); });
  }
  async function decide(id, yes) {
    const e = ST.exc[id]; if (!e) return;
    try {
      await api('POST', `/api/seva/exceptions/${enc(id)}/decide`, {yes, hash: e.hash});
      toast(yes ? `${e.number}: yes. Hoola tells the customer.` : `${e.number}: no. Hoola tells the customer politely.`);
    } catch (err) {
      if (err.status === 428) { toast('This one needs your fingerprint: open the card on your phone to finish it.', true); return; }
      throw err;
    }
    await refreshDesk(false); showPage(true);
  }
  async function onClick(e) {
    const b = e.target.closest('button,[data-act]'); if (!b) return;
    try {
      if (b.dataset.act === 'reload') return showPage();
      if (b.dataset.act === 'editsetup') { $('#spPreview').innerHTML = ''; ST.preview = null; $('#spSetup').scrollIntoView({behavior: 'smooth'}); return; }
      if (b.dataset.act === 'applysetup') { const p = ST.preview; if (!p) return; b.disabled = true;
        const r = await api('POST', '/api/support/setup/apply', {answers: p.answers, hash: p.hash}); toast(r.say || 'Setup saved.');
        await refreshDesk(false); location.hash = '#/today'; return; }
      if (b.dataset.act === 'newticket') { const box = $('#spNewTicket'); box.hidden = !box.hidden; if (!box.hidden) box.querySelector('input').focus(); return; }
      if (b.dataset.filter) { ST.filter = b.dataset.filter; return showPage(true); }
      if (b.dataset.days) { ST.days = Number(b.dataset.days); return showPage(true); }
      if (b.dataset.merge) { const r = await api('POST', `/api/seva/tickets/${enc(b.dataset.merge)}/merge`, {into: b.dataset.into}); toast(r.say || 'Joined.'); return showPage(true); }
      if (b.dataset.decide) return decide(b.dataset.decide, b.dataset.yes === '1');
      if (b.dataset.cancel) { await api('POST', `/api/seva/exceptions/${enc(b.dataset.cancel)}/cancel`); toast('Request withdrawn.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.kbdel) { if (!confirm('Remove this answer? Hoola will stop using it.')) return; await api('DELETE', `/api/seva/kb/${enc(b.dataset.kbdel)}`); toast('Removed.'); return showPage(true); }
      if (b.dataset.macok) { await api('POST', `/api/seva/macros/${enc(b.dataset.macok)}/approve`, {}); toast('Saved reply approved.'); return showPage(true); }
      if (b.dataset.macdel) { if (!confirm('Remove this saved reply?')) return; await api('DELETE', `/api/seva/macros/${enc(b.dataset.macdel)}`); return showPage(true); }
      if (b.dataset.act === 'kbfile') {
        const f = await pickOne(); if (!f) return;
        if (f.size > 20 * 1024 * 1024) { toast('The file is larger than 20 MB.', true); return; }
        toast('Reading the file…');
        const fd = new FormData(); fd.append('file', f, f.name || 'file');
        const r = await api('POST', '/api/seva/kb/import', undefined, {form: fd});
        toast(r.say || 'Drafts are ready to check.'); await refreshDesk(false); return showPage(true);
      }
    } catch (err) { toast(err.message, true); }
  }
  async function onSubmit(e) {
    const f = e.target; e.preventDefault();
    const v = Object.fromEntries(new FormData(f).entries());
    const btn = f.querySelector('button[type=submit]'); if (btn) btn.disabled = true;
    try {
      if (f.id === 'spFind') { ST.q = S(v.q).trim(); return showPage(true); }
      if (f.id === 'spSetup') { ST.preview = await api('POST', '/api/support/setup/preview', {answers: setupAnswers(f)}); drawPreview(ST.preview); return; }
      if (f.id === 'spTicketForm') { const r = await api('POST', '/api/seva/tickets', v); toast(r.say || 'Ticket opened.'); await refreshDesk(false); location.hash = '#/ticket/' + enc((r.ticket || {}).number || ''); return; }
      if (f.id === 'spReply') { if (!S(v.text).trim() && !v.macro) { toast('Write a reply or pick a saved reply.', true); return; }
        const r = await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/reply`, {text: v.text, macro: v.macro || ''}); toast(r.say || 'Sent.'); return showPage(true); }
      if (f.id === 'spNote') { await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/note`, {text: v.text}); toast('Note added.'); return showPage(true); }
      if (f.id === 'spUpdate') { const r = await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/update`, v); toast(r.say || 'Saved.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spAsk') { const r = await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/exception`, {kind: v.kind, amount: Number(v.amount || 0), reason: v.reason}); toast(r.say || 'Sent to Approvals.'); await refreshDesk(false); return showPage(true); }
      if (f.classList.contains('spGap')) { await api('POST', '/api/seva/kb', {question: f.dataset.q, answer: v.answer, kind: 'faq'}); toast('Saved. Hoola uses it from now on.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spApprove') { const ids = [...f.querySelectorAll('input[name=d]:checked')].map(x => x.value); if (!ids.length) { toast('Tick at least one.', true); return; }
        const r = await api('POST', '/api/seva/kb/approve', {ids}); toast(r.say || 'Approved.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spTest') { ST.test = await api('POST', '/api/seva/kb/ask', {question: v.question}); return showPage(true); }
      if (f.id === 'spKbAdd') { const r = await api('POST', '/api/seva/kb', {question: v.question, answer: v.answer, kind: v.kind, aliases: S(v.aliases).split(',').map(x => x.trim()).filter(Boolean)}); toast(r.say || 'Added. It is live now.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spImport') { if (!S(v.url).trim() && !S(v.text).trim()) { toast('Give a page address or paste text - or choose a file.', true); return; }
        toast('Reading…'); const r = await api('POST', '/api/seva/kb/import_link', {url: v.url, text: v.text}); toast(r.say || 'Drafts are ready to check.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spMacro') { const r = await api('POST', '/api/seva/macros', {name: v.name, text: v.text}); toast(r.say || 'Saved reply added; approve it to use it.'); return showPage(true); }
      if (f.classList.contains('spSent')) { const r = await api('POST', `/api/seva/exceptions/${enc(f.dataset.id)}/sent`, {ref: v.ref || ''}); toast(r.say || 'Marked paid.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spSettings') {
        const sla = {};
        for (const p of ['urgent', 'high', 'normal', 'low']) { const a = Number(v[`sla_${p}_0`]), z = Number(v[`sla_${p}_1`]); if (a && z) sla[p] = [a, z]; }
        const pol = {};
        for (const k of ['refund_days', 'refund_max', 'replace_days', 'goodwill_max', 'cancel_hours']) pol[k] = S(v[k]).trim() === '' ? '' : Number(v[k]);
        pol.refund_mode = S(v.refund_mode);
        const body = {kind: v.kind, sla, policy: pol, lang: v.lang, morning_time: v.morning_time, officer: v.officer, officer_contact: v.officer_contact,
          auto_ack: !!f.auto_ack.checked, csat_on: !!f.csat_on.checked, ecommerce: !!f.ecommerce.checked};
        if (v.kind !== ST.setKind) delete body.sla;   // a new kind of business starts from its usual reply times
        const r = await api('PUT', '/api/seva/settings', body); toast(r.say || 'Saved.'); await refreshDesk(false); return showPage(true);
      }
    } catch (err) { toast(err.message, true); }
    finally { if (btn && btn.isConnected) btn.disabled = false; }
  }

  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    const k = {ticket: 'inbox'}[ST.tab] || ST.tab;
    box.innerHTML = (STARTERS[k] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-q]'); if (b) send(b.dataset.q); };
  }

  /* ---------------------------------------------------------------- files in the chat */
  function addFiles(list) {
    for (const f of list) {
      if (ST.files.length >= MAXF) { toast(`Up to ${MAXF} files in one message.`, true); break; }
      if (f.size > MAXB) { toast(`${f.name} is over 30 MB.`, true); continue; }
      const item = {name: f.name || 'file', id: '', state: 'up', key: Math.random().toString(36).slice(2)};
      ST.files.push(item); paintFiles();
      (async () => {
        try { item.id = await upload(f); item.state = item.id ? 'ok' : 'bad'; }
        catch (e) { item.state = 'bad'; item.err = e.message; toast(`${item.name}: ${e.message}`, true); }
        paintFiles();
      })();
    }
    if (ST.folded) $('#sdFold').click();
  }
  function paintFiles() {
    const box = $('#adFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="ac-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/support/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
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
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Working on it…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text),
      files: r.role === 'user' && Array.isArray(r.files) ? r.files : undefined}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) refreshDesk(true);
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these files' : 'Read this file';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(text, {pending: true, files: names});
    ST.files = []; paintFiles(); paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text, files, client_id: 'sp' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
