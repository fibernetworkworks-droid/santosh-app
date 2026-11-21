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

  const TABS = [['today', 'Today'], ['inbox', 'Inbox'], ['workflow', 'Workflow'], ['knowledge', 'Knowledge'], ['approvals', 'Approvals'], ['reports', 'Reports'],
    ['settings', 'Channels & settings']];
  const STARTERS = {
    today: ['What came in today?', 'Which tickets are late?', 'What needs my yes?'],
    inbox: ['Open a ticket for a caller', 'Which customers are waiting longest?', 'Join the duplicate tickets'],
    knowledge: ['Add my refund policy', 'Read my price list into answers', 'Which questions could you not answer?'],
    approvals: ['Why is this refund outside my policy?', 'How much did I refund this month?', 'Explain the waiting requests'],
    reports: ['How is support doing this month?', 'What do customers write about most?', 'What would help most?'],
    settings: ['Set reply times for a clinic', 'Refunds within 10 days', 'Who is my grievance officer?'],
    workflow: ['Which tickets are stuck?', 'Add an approval step to refunds', 'Who owns each stage?'],
    setup: ['Which kind of business should I pick?', 'What changes if I add more countries?', 'What does working on top of my helpdesk mean?']};
  const PRI = {urgent: 'bad', high: 'warn', normal: '', low: ''};
  const STATUS = {new: 'New', open: 'Open', pending: 'Waiting on customer', on_hold: 'On hold', resolved: 'Solved', closed: 'Closed', merged: 'Joined'};
  const CHANNEL = {whatsapp: 'WhatsApp', hoola: 'Hoola Network', phone: 'Phone call', walkin: 'Walk-in', email: 'Email', other: 'Other', test: 'Test',
    web: 'Website chat', app: 'Your app', telegram: 'Telegram', messenger: 'Messenger', instagram: 'Instagram', sms: 'SMS', line: 'LINE', viber: 'Viber', slack: 'Slack', x: 'X', zalo: 'Zalo', kakao: 'KakaoTalk', wechat: 'WeChat'};
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
    if (parts[0] === 'chat' && parts[1]) { ST.tab = 'chat'; ST.arg = decodeURIComponent(parts.slice(1).join('/')); return; }
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
    $('#spPage').addEventListener('change', e => {
      if (e.target.id !== 'spChKind') return;
      const k = (ST.chKinds || {})[e.target.value], box = $('#spChKeys');
      box.innerHTML = k ? `<p class="mut" style="margin:0;font-size:13px">${esc(k.how)}</p>${k.keys.map(x => field('k_' + x, (ST.keyNames || {})[x] || x, `type="${/secret|token|password/.test(x) && !/verify|^token$/.test(x) ? 'password' : 'text'}" autocomplete="off" required`)).join('')}` : '';
    });
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
    const d = ST.d || {}, cur = ST.tab === 'ticket' || ST.tab === 'chat' ? 'inbox' : ST.tab === 'setup' ? 'settings' : ST.tab;
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
    const seq = ST.pageSeq = (ST.pageSeq || 0) + 1;       // only the newest page load may draw (a slow one never overwrites it)
    const put = html => { if (seq !== ST.pageSeq) return false; box.innerHTML = html; return true; };
    try {
      const t = ST.tab;
      if (t === 'today') put(await pageToday());
      else if (t === 'inbox') put(await pageInbox());
      else if (t === 'ticket') { if (put(await pageTicket(ST.arg)) && ST.loadMoves) loadMoves(); }
      else if (t === 'setup') { if (put(await pageSetup())) setupWire(); }
      else if (t === 'chat') put(await pageChat(ST.arg));
      else if (t === 'knowledge') put(await pageKnowledge());
      else if (t === 'workflow') put(await pageWorkflow());
      else if (t === 'approvals') put(await pageApprovals());
      else if (t === 'reports') put(await pageReports());
      else if (t === 'settings') put(await pageSettings());
    } catch (e) { if (seq !== ST.pageSeq) return; box.innerHTML = `<div class="card"><p class="lead">${esc(e.message)}</p><button class="btn soft sm" type="button" data-act="reload">Try again</button></div>`; }
  }
  const tRow = t => `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/ticket/${enc(t.number)}">${esc(t.number)} · ${esc(t.customer || 'Customer')}</a> ${pill(PRI[t.priority], t.priority)} ${due(t)}</div>
    <div class="s">${esc(CHANNEL[t.channel] || t.channel)} · ${esc(t.category_label || '')} · ${esc(STATUS[t.status] || t.status)} · ${esc(S(t.text).slice(0, 140))}</div></div><a class="btn sm soft" href="#/ticket/${enc(t.number)}">Open</a></div>`;

  /* ---------------------------------------------------------------- Today */
  function packetHtml(h) {
    const p = h.packet || {}, c = p.customer || {}, dl = p.deadline || {};
    const li = (n, v) => v ? `<div class="s"><b>${esc(n)}:</b> ${v}</div>` : '';
    return `<div style="display:flex;flex-direction:column;gap:4px">
      ${li('Customer', esc([c.name, c.channel, c.language, c.country_time_zone ? `${c.country_time_zone}${c.their_time ? ', their time ' + c.their_time : ''}` : '', c.vip ? 'VIP' : ''].filter(Boolean).join(' · ')))}
      ${li('Problem', esc(p.problem))}${li('Why a person', esc(p.why_a_person))}${li('They feel', esc(p.feeling))}
      ${li('Hoola checked', esc((p.hoola_checked || []).map(x => `“${x.asked}” → ${x.found}`).join('; ')))}
      ${li('Hoola told them', esc((p.hoola_told || []).join(' / ')))}
      ${li('Other tickets', esc(((p.tickets || {}).others || []).map(x => `${x.number} (${x.status})`).join(', ')))}
      ${li('Deadline', dl.when ? esc(`${dl.what} by ${when(dl.when)}`) : '')}${li('Next step', esc(p.next_step))}
      ${li('Customer was told', esc(h.told))}
      ${p.draft ? `<label class="f"><span>A draft reply you can change</span><textarea class="in" rows="2" readonly>${esc(p.draft)}</textarea></label>` : ''}</div>`;
  }
  function handoverRow(h) {
    return `<div class="row" style="flex-direction:column;align-items:stretch;gap:8px">
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">${pill(h.urgent ? 'bad' : h.status === 'taken' ? 'ok' : 'warn', h.urgent ? 'Urgent' : h.status === 'taken' ? 'Taken' : 'Waiting')}
        <div style="flex:1;min-width:0"><div class="t">${esc(h.ticket)} · ${esc(((h.packet || {}).customer || {}).name || h.customer)} · for ${esc(h.to)}</div>
        <div class="s">${esc(h.rule_name)}${h.out_of_hours ? ' · came in while closed' : ''} · ${esc(when(h.at))}</div></div>
        <a class="btn sm soft" href="#/ticket/${enc(h.ticket)}">Open</a>${h.status === 'waiting' ? `<button class="btn sm" type="button" data-take="${esc(h.id)}">Take it</button>` : ''}</div>
      <details><summary class="mut" style="cursor:pointer;font-size:13px">The hand-over packet</summary>${packetHtml(h)}</details>
      <form class="spBack" data-id="${esc(h.id)}" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spBack-${esc(h.id)}">Instruction for Hoola</label><input class="in" id="spBack-${esc(h.id)}" name="note" placeholder="e.g. send the tracking link and close if they confirm" style="flex:1;min-width:200px"><button class="btn soft sm" type="submit">Give back to Hoola</button></form></div>`;
  }
  async function pageToday() {
    const d = ST.d || {}, w = d.week || {};
    const [tk, ex, dr, wt] = await Promise.all([api('GET', '/api/seva/tickets?status=open'), api('GET', '/api/seva/exceptions?status=pending'),
      api('GET', '/api/seva/drafts').catch(() => ({drafts: []})), api('GET', '/api/seva/watch').catch(() => ({}))]);
    const ho = await api('GET', '/api/seva/handovers').catch(() => ({open: []}));
    const hoSec = (ho.open || []).length ? sec(`Waiting for a person · ${num(ho.open.length)}`, `<p class="mut" style="margin:0">Hoola handed these customers to your team with everything it knows.${ho.wait_text ? ` Your team usually takes one within about ${esc(ho.wait_text)}.` : ''}</p>${ho.open.map(handoverRow).join('')}`) : '';
    const KIND = {before: 'Before the deadline', due: 'At the deadline', boss: 'Told you', repeat: 'Again', update: 'Customer updated', check: 'Asked "did this fix it?"', closed_quiet: 'Closed, no answer', reopen: 'Reopened', confirmed: 'Customer confirmed'};
    const watchSec = [
      (wt.stuck || []).length ? sec(`Stuck · ${num(wt.stuck.length)}`, wt.stuck.slice(0, 10).map(x => `<div class="row">${pill('bad', 'Stuck')}<div style="flex:1;min-width:0"><div class="t">${esc(x.number)} · ${esc(x.customer || '')}${x.stage ? ' · ' + esc(x.stage) : ''}</div><div class="s">${esc((x.reasons || []).join('; '))}</div></div><a class="btn sm soft" href="#/ticket/${enc(x.number)}">Open</a></div>`).join('')) : '',
      (wt.confirming || []).length ? sec(`Waiting for the customer to confirm · ${num(wt.confirming.length)}`, `<p class="mut" style="margin:0">Hoola asked "did this fix it?". YES closes the ticket, NO sends it back; no answer closes it on the date shown.</p>` + wt.confirming.map(x => `<div class="row">${pill('v', 'Asked')}<div style="flex:1;min-width:0"><div class="t">${esc(x.number)} · ${esc(x.customer || '')}</div><div class="s">Closes by itself ${esc(when(x.closes))} if no answer</div></div><a class="btn sm soft" href="#/ticket/${enc(x.number)}">Open</a></div>`).join('')) : '',
      (wt.digest || []).length ? sec('By person', wt.digest.map(x => `<div class="row">${x.late.length ? pill('bad', num(x.late.length) + ' late') : pill('ok', 'On time')}<div style="flex:1;min-width:0"><div class="t">${esc(x.person)}${x.supervisor ? ' (supervisor)' : ''}</div><div class="s">${num(x.open.length)} open${x.soon.length ? ` · ${num(x.soon.length)} due soon` : ''}${x.late.length ? ` · late: ${esc(x.late.slice(0, 6).join(', '))}` : ''}</div></div></div>`).join('')) : '',
      (wt.reminders || []).length ? sec(`Reminders in the last day · ${num(wt.reminders.length)}`, wt.reminders.slice(0, 12).map(x => `<div class="row">${pill(['boss', 'repeat', 'reopen'].includes(x.kind) ? 'bad' : x.kind === 'due' ? 'warn' : '', KIND[x.kind] || x.kind)}<div style="flex:1;min-width:0"><div class="t">${esc(x.text)}</div><div class="s">${esc(x.to ? 'To ' + x.to + ' · ' : '')}${esc(when(x.at))}</div></div></div>`).join('')) : ''].join('');
    const drafts = (dr.drafts || []).map(d => `<form class="spDraft row" data-id="${esc(d.id)}" style="flex-direction:column;align-items:stretch;gap:8px">
      <div class="s">${esc(CHANNEL[d.channel] || d.channel)} · ${esc(d.customer || 'customer')} asked: “${esc(d.question)}”</div>
      <label class="f"><span>Hoola's reply (from ${esc(d.source || 'your knowledge')}) - change it if you like</span><textarea class="in" name="text" rows="2">${esc(d.reply)}</textarea></label>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="submit">Send</button><button class="btn soft sm" type="button" data-draftact="sent" data-id="${esc(d.id)}">I sent it myself</button><button class="btn soft sm" type="button" data-draftact="discard" data-id="${esc(d.id)}">Discard</button></div></form>`).join('');
    const open = tk.tickets || [], late = open.filter(t => (t.sla || {}).late);
    const needs = [
      ...(ex.exceptions || []).map(e => `<div class="row">${pill('warn', e.kind_label.split(' (')[0])}<div style="flex:1;min-width:0"><div class="t">${esc(e.number)} · ${esc(e.customer || '')}${e.amount_text ? ' · ' + esc(e.amount_text) : ''}</div><div class="s">${esc((e.check || {}).within ? 'Within your rules - still your decision.' : 'Outside your rules: ' + ((e.check || {}).reasons || []).join(' '))}</div></div><a class="btn sm" href="#/approvals">Decide</a></div>`),
      ...late.slice(0, 6).map(t => `<div class="row">${pill('bad', 'Late')}<div style="flex:1;min-width:0"><div class="t">${esc(t.number)} · ${esc(t.customer || '')}</div><div class="s">${esc(S(t.text).slice(0, 120))}</div></div><a class="btn sm soft" href="#/ticket/${enc(t.number)}">Open</a></div>`),
      ...(d.drafts ? [`<div class="row">${pill('v', 'Draft')}<div style="flex:1"><div class="t">${num(d.drafts)} draft answer${d.drafts > 1 ? 's' : ''} to check</div></div><a class="btn sm soft" href="#/knowledge">Check</a></div>`] : []),
      ...(d.gaps ? [`<div class="row">${pill('warn', 'No answer')}<div style="flex:1"><div class="t">${num(d.gaps)} customer question${d.gaps > 1 ? 's' : ''} your knowledge could not answer</div></div><a class="btn sm soft" href="#/knowledge">Answer</a></div>`] : [])].join('');
    const nAns = w.answered_by_kb || 0, nQ = w.questions || 0;
    const setupCard = d.setup_done ? '' : `<section class="card" id="spSetupCard" style="display:flex;gap:14px;align-items:center;flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t" style="font-weight:600">Set up Customer Support for your business</div><div class="s">Eight short questions: your size, kind of business, countries, languages and channels. Hoola then shows only what you need.</div></div><a class="btn" href="#/setup">Start setup</a></section>`;
    return `${head(needs || drafts ? 'A few things need you.' : 'Nothing needs you right now.', esc(d.say || ''))}${setupCard}${drafts ? sec(`Replies waiting for a person · ${num((dr.drafts || []).length)}`, `<p class="mut" style="margin:0">On these topics Hoola drafts and a person sends (Channels & settings > How much Hoola may do).</p>${drafts}`) : ''}
      <div class="grid">${kpi(num(d.open), 'open tickets')}${kpi(num((d.late || []).length), 'past the reply time')}${kpi(nQ ? `${num(nAns)} of ${num(nQ)}` : '–', 'questions answered from knowledge (7 days)')}${kpi(w.csat_avg ? `${w.csat_avg} / 5` : '–', `rating (${num(w.csat_count)} replies)`)}</div>
      ${sec('Needs you', needs || '<p class="mut" style="margin:0">Nothing waits for you.</p>')}
      ${hoSec}${watchSec}
      ${sec('Open tickets', open.slice(0, 8).map(tRow).join('') || '<p class="mut" style="margin:0">No open tickets.</p>', '<a class="btn soft sm" href="#/inbox">Inbox</a>')}
      ${d.answers ? '' : sec('Start here', `<p class="mut" style="margin:0">Your knowledge is empty, so Hoola cannot answer customers yet. Add your timings, prices and refund rules on <a href="#/knowledge">Knowledge</a>, or attach your price list in the chat.</p>`)}`;
  }

  /* ---------------------------------------------------------------- Inbox */
  async function pageChat(cust) {
    const t = await api('GET', `/api/seva/chats/${enc(cust)}`);
    const msgs = (t.messages || []).map(m => `<div class="${m.direction === 'in' ? 'me' : 'ai'}"><span class="who">${m.direction === 'in' ? 'Customer' : esc(m.by === 'hoola' ? 'Hoola' : m.by)} · ${esc(when(m.at))}${m.status === 'failed' ? ' · not sent' : ''}</span>${esc(m.text)}${m.file ? ` <button class="btn soft sm" type="button" data-cfile="${esc(m.file)}">Open the file</button>` : ''}</div>`).join('');
    return `<div><a class="btn soft sm" href="#/inbox">← Inbox</a></div>${head(esc(cust), t.held ? 'A person has this chat; Hoola stays quiet.' : 'Hoola answers this chat; a reply from you takes it.', t.stopped ? pill('warn', 'Wrote STOP') : '')}
      ${sec('The conversation', `<div class="tline">${msgs || '<p class="mut" style="margin:0">No messages.</p>'}</div>`)}
      ${t.stopped ? '' : sec('Reply', `<form id="spChat" data-cust="${esc(cust)}" style="display:flex;flex-direction:column;gap:10px"><label class="f"><span>Your words (they see this on the same app)</span><textarea class="in" name="text" rows="3" required></textarea></label><div><button class="btn sm" type="submit">Send</button></div></form>`)}`;
  }
  async function pageInbox() {
    const f = ST.filter;
    const r = await api('GET', `/api/seva/tickets?status=${enc(f === 'all' ? '' : f)}&q=${enc(ST.q)}`);
    const chs = await api('GET', '/api/seva/channels').catch(() => ({conversations: []}));
    const convs = (chs.conversations || []).map(c => `<div class="row">${pill(c.held ? 'warn' : '', c.app || c.kind)}<div style="flex:1;min-width:0"><div class="t"><a href="#/chat/${enc(c.customer)}">${esc(c.name || c.customer)}</a>${c.held ? ' · with a person' : ''}</div><div class="s">${esc(c.last_by === 'customer' ? 'They said: ' : 'Last reply: ')}${esc(c.last)} · ${esc(when(c.at))}</div></div></div>`).join('');
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
      ${convs ? sec('Messages on your apps', convs) : ''}
      ${dup ? sec('Might be the same problem', dup) : ''}
      <section class="card" style="overflow-x:auto;padding:4px 16px">${rows ? `<table class="tb"><thead><tr><th>Ticket</th><th>Customer</th><th>Problem</th><th>Priority</th><th>Status</th><th>Opened</th></tr></thead><tbody>${rows}</tbody></table>` : '<p class="mut" style="padding:14px 0;margin:0">No tickets here.</p>'}</section>`;
  }
  async function pageTicket(ref) {
    const [t, mac, rm, hv] = await Promise.all([api('GET', `/api/seva/tickets/${enc(ref)}`), api('GET', '/api/seva/macros'),
      api('GET', `/api/seva/reminders?ticket=${enc(ref)}`).catch(() => ({reminders: []})),
      api('GET', `/api/seva/handovers?ticket=${enc(ref)}`).catch(() => ({handovers: []}))]);
    const hos = hv.handovers || [];
    const hoTicket = sec('A person', hos.length ? hos.slice(0, 3).map(handoverRow).join('') : `<form id="spHand" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spHandWhy">Why a person</label><input class="in" id="spHandWhy" name="reason" placeholder="Why a person should take it" style="flex:1;min-width:200px"><button class="btn soft sm" type="submit">Hand to a person</button></form>`);
    ST.ticket = t;
    const s = t.sla || {}, ck = t.clocks || {};
    const clockRows = [['Time so far', ck.total_h], ['First reply took', ck.first_reply_h], ['Customer waiting for a reply', ck.waiting_reply_h], ['At this stage', ck.stage_h]]
      .filter(x => x[1] !== undefined).map(([n, h]) => `<div class="row"><div class="t" style="flex:1">${esc(n)}</div><b>${esc(hours(h))}</b></div>`).join('');
    const clockSec = sec('Clocks', `${clockRows}${ck.next_reply_left_h !== undefined ? `<p class="mut" style="margin:0;font-size:13px">${ck.next_reply_left_h < 0 ? `The next reply is ${esc(hours(ck.next_reply_left_h))} late.` : `Next reply due in ${esc(hours(ck.next_reply_left_h))}.`}</p>` : ''}
      <p class="mut" style="margin:0;font-size:13px">${ck.working_hours ? `Counted in your working hours${ck.open_now ? '' : ' (you are closed now, the clocks wait)'}.` : 'Counted around the clock (set working hours in Channels & settings).'}${ck.reopens ? ` Reopened ${num(ck.reopens)} time${ck.reopens > 1 ? 's' : ''}.` : ''}</p>
      ${t.status === 'resolved' && ck.confirm_by ? `<div class="s">Waiting for the customer to confirm the fix (closes by itself ${esc(when(ck.confirm_by))}). If they told you:</div><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-confirm="yes">They say it is fixed</button><button class="btn soft sm" type="button" data-confirm="no">They say it is not fixed</button></div>` : ''}
      ${(rm.reminders || []).length ? `<details><summary class="mut" style="cursor:pointer;font-size:13px">Reminders and checks · ${num(rm.reminders.length)}</summary>${rm.reminders.map(x => `<div class="s">${esc(when(x.at))} · ${esc(x.text)}</div>`).join('')}</details>` : ''}`);
    const notes = (t.notes || []).map(n => `<div class="${n.public ? 'ai' : 'note'}"><span class="who">${n.public ? 'To the customer' : 'Internal note'} · ${esc(n.by || '')} · ${esc(when(n.at))}</span>${esc(n.text)}</div>`).join('');
    const macros = (mac.macros || []).filter(m => m.status === 'approved');
    const ex = (t.exceptions || []).map(e => `<div class="row">${pill(e.status === 'pending' ? 'warn' : e.status === 'rejected' ? 'bad' : 'ok', e.status)}<div style="flex:1"><div class="t">${esc(e.number)} · ${esc(e.kind_label)} ${esc(e.amount_text || '')}</div></div></div>`).join('');
    const legal = (t.legal || []).map(x => `<p class="mut" style="margin:0;font-size:13px">${esc(typeof x === 'string' ? x : (x.text || ''))}</p>`).join('');
    const open = ['new', 'open', 'pending', 'on_hold'].includes(t.status);
    const sg = t.stage;
    const stageSec = sg ? sec(`Where it is · ${esc(sg.flow_name)}`, `<div style="display:flex;gap:4px;flex-wrap:wrap" aria-label="Stages">${sg.stages.map((x, i) => {
        const at = sg.stages.findIndex(y => y.key === sg.stage); return `<span class="pill ${i < at ? 'ok' : i === at ? (sg.late ? 'bad' : 'warn') : ''}"${i === at ? ' aria-current="step"' : ''}>${i + 1}. ${esc(x.name)}</span>`; }).join('')}</div>
      <div class="s">Now: <b>${esc(sg.stage_name)}</b> · with ${esc(sg.owner_name)}${sg.since ? ` · since ${esc(when(sg.since))}` : ''}${sg.due ? ` · ${sg.late ? 'was due' : 'due'} ${esc(when(sg.due))}` : ''}</div>
      ${sg.next.length ? `<form id="spMove" style="display:flex;flex-direction:column;gap:10px">${(sg.needs || []).map(n => field('f_' + n, `${n.replace(/_/g, ' ')} (needed to move on)`, `value="${esc((sg.fields || {})[n] || '')}"`)).join('')}
        ${field('why', 'Note (optional)', '')}
        <div style="display:flex;gap:8px;flex-wrap:wrap">${sg.next.map(x => `<button class="btn sm${x === sg.next[0] ? '' : ' soft'}" type="submit" name="to" value="${esc(x.key)}">Move to ${esc(x.name)}</button>`).join('')}</div></form>` : '<p class="mut" style="margin:0">This is the last stage.</p>'}
      <details><summary class="mut" style="cursor:pointer;font-size:13px">Every move</summary><div id="spMoves" class="s">Loading…</div></details>`) : '';
    ST.loadMoves = !!sg;
    return `<div><a class="btn soft sm" href="#/inbox">← Inbox</a></div>
      ${head(`${esc(t.number)} · ${esc(t.customer || 'Customer')}`, esc(`${CHANNEL[t.channel] || t.channel} · ${t.category_label || ''} · opened ${when(t.created)}`), `${pill(PRI[t.priority], t.priority)} ${pill(open ? 'v' : 'ok', STATUS[t.status] || t.status)}`)}
      <div class="grid2">
        <div style="display:flex;flex-direction:column;gap:18px">
          ${stageSec}
          ${sec('The conversation', `<div class="tline"><div class="me"><span class="who">${esc(t.customer || 'Customer')}</span>${esc(t.text)}</div>${notes}</div>`)}
          ${open ? sec('Reply to the customer', `<form id="spReply" style="display:flex;flex-direction:column;gap:10px">
            ${macros.length ? `<label class="f"><span>Saved reply</span><select class="in" name="macro"><option value="">Write my own</option>${macros.map(m => `<option value="${esc(m.name)}">${esc(m.name)}</option>`).join('')}</select></label>` : ''}
            <label class="f"><span>Your words (they see this)</span><textarea class="in" name="text" rows="3"></textarea></label>
            <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="submit">Send</button><span class="mut" style="font-size:12.5px;align-self:center">Goes on WhatsApp or the Hoola Network when the customer came from there; otherwise it is a draft you send.</span></div></form>`) : ''}
          ${sec('Internal note', `<form id="spNote" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spNoteText">Internal note</label><input class="in" id="spNoteText" name="text" required placeholder="Only you and your team see this" style="flex:1;min-width:200px"><button class="btn soft sm" type="submit">Add note</button></form>`)}
        </div>
        <div style="display:flex;flex-direction:column;gap:18px">
          ${hoTicket}${clockSec}
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
    const [kb, mac, su, br] = await Promise.all([api('GET', '/api/seva/kb'), api('GET', '/api/seva/macros'), api('GET', '/api/support/setup').catch(() => ({})),
      api('GET', '/api/seva/brain').catch(() => ({}))]);
    ST.packQs = su.done ? ((su.pack || {}).knowledge_questions || []) : [];
    const entries = kb.entries || [], drafts = entries.filter(e => e.status === 'draft'), live = entries.filter(e => e.status !== 'draft');
    const gaps = (kb.gaps || []).map((g, i) => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">“${esc(g.question)}”</div><div class="s">asked ${num(g.times)} time${g.times > 1 ? 's' : ''}</div></div>
      <form class="spGap" data-q="${esc(g.question)}" style="display:flex;gap:6px;flex:1 1 320px"><label class="sr" for="spGap${i}">Answer for: ${esc(g.question)}</label><input class="in" id="spGap${i}" name="answer" required placeholder="Your answer" style="flex:1"><button class="btn sm" type="submit">Save answer</button></form></div>`).join('');
    const drows = drafts.map(e => `<label class="row" style="align-items:flex-start;cursor:pointer"><input type="checkbox" name="d" value="${esc(e.id)}" checked style="width:18px;height:18px;margin-top:3px"><div style="flex:1;min-width:0"><div class="t">${esc(e.question)}</div><div class="s">${esc(e.answer)}</div><div class="mut" style="font-size:12px">From: ${esc(e.source)}</div></div></label>`).join('');
    const today = new Date().toISOString().slice(0, 10);
    const lrows = live.map(e => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">${pill(e.kind === 'policy' ? 'v' : '', e.kind === 'policy' ? 'Policy' : 'Question')} ${esc(e.question)}${e.stale ? ' ' + pill('warn', 'Page changed') : ''}${e.review_by && e.review_by < today ? ' ' + pill('warn', 'Review date passed') : ''}</div><div class="s">${esc(e.answer)}</div>
      <div class="mut" style="font-size:12px">${esc(e.source)} · used ${num(e.hits)} time${e.hits === 1 ? '' : 's'}${e.version ? ` · version ${num(e.version)}` : ''}${e.owner ? ` · kept right by ${esc(e.owner)}` : ''}${e.review_by ? ` · review by ${esc(e.review_by)}` : ''}</div>
      <div id="spHist-${esc(e.id)}"></div></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-kbhist="${esc(e.id)}" aria-label="History: ${esc(e.question)}">History</button><button class="btn soft sm" type="button" data-kbmeta="${esc(e.id)}" data-owner="${esc(e.owner || '')}" data-review="${esc(e.review_by || '')}" aria-label="Owner and review date: ${esc(e.question)}">Owner, review date</button><button class="btn soft sm" type="button" data-kbdel="${esc(e.id)}" aria-label="Remove: ${esc(e.question)}">Remove</button></div></div>`).join('');
    const look = [...(br.stale || []), ...(br.review_due || [])].map(e => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">${esc(e.question)} ${pill('warn', e.stale ? 'Page changed' : 'Review date passed')}</div><div class="s">${esc(e.answer)}</div><div class="mut" style="font-size:12px">${esc(e.source)}. Hoola does not use it until you look.</div></div>
      <button class="btn sm" type="button" data-kbok="${esc(e.id)}">Still right</button></div>`).join('');
    const sugg = (br.suggestions || []).map((g, i) => `<form class="spSugg row" data-id="${esc(g.id)}" style="flex-direction:column;align-items:stretch;gap:8px">
      <div class="s">Solved ${num(g.count)} times (${esc(g.tickets.slice(0, 5).join(', '))}) with your team's reply:</div>
      <label class="f"><span>Customers ask</span><input class="in" name="question" value="${esc(g.question)}"></label>
      <label class="f"><span>Your team answered</span><textarea class="in" name="answer" rows="2">${esc(g.answer)}</textarea></label>
      <div style="display:flex;gap:8px"><button class="btn sm" type="submit">Use this answer</button><button class="btn soft sm" type="button" data-suggno="${esc(g.id)}">Dismiss</button></div></form>`).join('');
    const shared = (br.shared || []).map(x => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${esc(x.name)} ${pill(x.status === 'approved' ? 'ok' : 'warn', x.status === 'approved' ? 'In use' : x.status === 'waiting' ? 'Waits for your OK' : x.status)}</div>
      <div class="s">${esc({text: 'Your words', file: 'A file', url: 'A web page', sheet: 'A sheet', api: 'Your API', system: 'A joined system'}[x.kind] || x.kind)} · ${x.mode === 'live' ? 'asked live with the customer\'s own number' : `${num(x.facts)} facts`}</div></div></div>`).join('');
    const ms = (mac.macros || []).map(m => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${esc(m.name)} ${pill(m.status === 'approved' ? 'ok' : 'warn', m.status === 'approved' ? 'In use' : 'Waits for your OK')}</div><div class="s">${esc((m.texts || {}).english || Object.values(m.texts || {})[0] || '')}</div><div class="mut" style="font-size:12px">${esc(Object.keys(m.texts || {}).join(', '))} · used ${num(m.uses)}</div></div>${m.status !== 'approved' ? `<button class="btn sm" type="button" data-macok="${esc(m.id)}">Approve</button>` : ''}<button class="btn soft sm" type="button" data-macdel="${esc(m.id)}" aria-label="Remove saved reply ${esc(m.name)}">Remove</button></div>`).join('');
    const DEC = {answer: 'Hoola would answer', clarify: 'Hoola would ask one question', draft: 'Hoola would draft it for a person to send',
      person: 'Hoola would hand it to a person', request: 'Hoola would send it to you as a request', status: "Hoola would tell them their ticket's state",
      lookup: 'Hoola would look it up with their own number', refuse: 'Hoola would refuse it'};
    const tt = ST.test, tu = (tt || {}).understood || {};
    const tl = tt ? `<div class="card" style="background:var(--soft)" id="spTestLine"><b>${esc(DEC[tt.decision] || tt.decision || '')}</b>
      ${tt.reply ? `<p class="say" style="margin:6px 0 0">${esc(tt.reply)}</p>` : tt.say ? `<p class="mut" style="margin:6px 0 0">${esc(tt.say)}</p>` : ''}
      <p class="mut" style="margin:6px 0 0;font-size:12.5px">Understood: ${esc([tu.lang, tu.intent, tu.category, tu.priority].filter(Boolean).join(' · '))}${tt.confidence !== undefined && tt.confidence !== null ? ` · match ${Math.round(100 * tt.confidence)}%` : ''}</p>
      ${(tt.why || []).length ? `<ul style="margin:6px 0 0;padding-left:18px;font-size:13px">${tt.why.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}</div>` : '';
    const packQ = (ST.packQs || []).length ? sec('Questions most businesses like yours answer', `<p class="mut" style="margin:0">From your industry pack. Answer the ones that apply; each becomes a live answer.</p>${ST.packQs.map((q, i) => `<div class="row" style="flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="t">${esc(q)}</div></div><form class="spGap" data-q="${esc(q)}" style="display:flex;gap:6px;flex:1 1 320px"><label class="sr" for="spPq${i}">Answer for: ${esc(q)}</label><input class="in" id="spPq${i}" name="answer" required placeholder="Your answer" style="flex:1"><button class="btn sm" type="submit">Save answer</button></form></div>`).join('')}`) : '';
    return `${head('What Hoola may say', 'Customers are answered only from these answers, and Hoola names the one it used. Anything not here comes to you.')}${packQ}
      ${look ? sec('Needs a look', `<p class="mut" style="margin:0">The page these came from changed, or their review date passed. Hoola stops using them until you check.</p>${look}`) : ''}
      ${sugg ? sec('Suggested from solved tickets', `<p class="mut" style="margin:0">Your team answered these the same way again and again. Change the words if you like, then use it.</p>${sugg}`) : ''}
      ${gaps ? sec('Customers asked, Hoola could not answer', `<p class="mut" style="margin:0">Answer once and Hoola uses it from now on.</p>${gaps}`) : ''}
      ${drows ? sec(`Drafts to check · ${num(drafts.length)}`, `<form id="spApprove" style="display:flex;flex-direction:column;gap:0">${drows}<div style="padding-top:10px"><button class="btn sm" type="submit">Approve the ticked ones</button></div></form>`) : ''}
      ${sec('Try a question', `<form id="spTest" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spTestQ">A customer's question</label><input class="in" id="spTestQ" name="question" required placeholder="What are your timings?" style="flex:1;min-width:220px"><label class="sr" for="spTestCh">Channel</label><select class="in" id="spTestCh" name="channel" style="width:auto">${['whatsapp', 'sms', 'email', 'web', 'app', 'phone'].map(c => `<option value="${c}">${esc(CHANNEL[c] || {sms: 'SMS', web: 'Website chat', app: 'In-app chat'}[c] || c)}</option>`).join('')}</select><button class="btn soft sm" type="submit">Ask as a customer</button></form>${tl}`)}
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
      ${sec('Import a help center', `<form id="spHelp" class="grid2" style="gap:14px">
        ${field('url', 'Address of your public Zendesk help center', 'placeholder="https://help.yourbusiness.com"')}
        <label class="f"><span>Or an export file (.json or .csv with title and body: Freshdesk, Intercom, Confluence, Notion…)</span><input class="in" type="file" name="file" accept=".json,.csv"></label>
        <div style="grid-column:1/-1"><button class="btn sm" type="submit">Read as drafts</button></div></form>`)}
      ${sec('Shared with the Telecaller', `<p class="mut" style="margin:0">One business brain: the Telecaller's approved facts also answer your customers here, and your live answers are used on its calls. Add or approve these sources on the Telecaller desk.</p>${shared || '<p class="mut" style="margin:0">No Telecaller sources yet.</p>'}<a class="btn soft sm" href="/console/telecaller" style="align-self:flex-start">Open the Telecaller desk</a>`)}
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

  async function loadMoves() {
    const box = $('#spMoves'); if (!box || !ST.ticket) return;
    try { const r = await api('GET', `/api/seva/tickets/${enc(ST.ticket.number)}/moves`); const nm = Object.fromEntries(((ST.ticket.stage || {}).stages || []).map(x => [x.key, x.name]));
      box.innerHTML = (r.moves || []).map(m => `<div>${esc(when(m.at))} · ${m.from ? `${esc(nm[m.from] || m.from)} → ` : 'Opened at '}${esc(nm[m.to] || m.to)} · ${esc(m.by)}${m.why && m.why !== 'opened' ? ` · ${esc(m.why)}` : ''}</div>`).join('') || 'No moves yet.';
    } catch (e) { box.textContent = e.message; }
  }
  /* ---------------------------------------------------------------- Workflow (G8: her stages, arrows, owners, times) */
  const OWN = {hoola: 'Hoola', team: 'Support team', supervisor: 'A supervisor', approver: 'Whoever may approve', finance: 'Finance', field: 'Field staff', engineering: 'Engineering'};
  async function pageWorkflow() {
    const r = await api('GET', '/api/seva/flows'); ST.flows = r.flows || [];
    const board = (r.board || []).map(b => `<div class="card" style="display:flex;flex-direction:column;gap:8px"><b>${esc(b.name)}</b><div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:4px">${b.stages.map(x => `<div style="min-width:150px;border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;flex-direction:column;gap:4px">
      <div class="t" style="font-size:13.5px">${esc(x.name)}</div><div class="s">${esc(x.owner_name)}</div><div style="font-size:20px;font-weight:600">${num(x.open)}</div>${x.late ? pill('bad', `${num(x.late)} late`) : ''}
      <div style="display:flex;flex-wrap:wrap;gap:4px">${x.tickets.slice(0, 6).map(n => `<a href="#/ticket/${enc(n)}" style="font-size:12px">${esc(n)}</a>`).join('')}</div></div>`).join('')}</div></div>`).join('');
    const ed = ST.flows.map(f => flowEditor(f)).join('');
    return `${head('Your ticket workflow', 'Every ticket is always at one stage, with one owner and one time limit. It moves only along the arrows you draw, and customers who ask are told the real stage.')}
      ${sec('Where tickets are now', board || '<p class="mut" style="margin:0">No open tickets.</p>')}
      ${ed}
      ${sec('A new workflow', `<form id="spFlowNew" style="display:flex;gap:8px;flex-wrap:wrap"><label class="sr" for="spFlowNewName">Name</label><input class="in" id="spFlowNewName" name="name" required placeholder="e.g. Warranty claim" style="flex:1;min-width:200px"><button class="btn soft sm" type="submit">Add workflow</button></form>`)}`;
  }
  function flowEditor(f) {
    const keys = f.stages.map(x => x.key);
    const row = (x, i) => `<fieldset class="row" data-stage style="flex-direction:column;align-items:stretch;gap:8px;border:1px solid var(--line);border-radius:12px;padding:12px;margin:0">
      <legend class="mut" style="font-size:12px;padding:0 4px">Stage ${i + 1}</legend>
      <div class="grid2" style="gap:10px">
        <label class="f"><span>Name</span><input class="in" data-k="name" value="${esc(x.name)}" required></label>
        <label class="f"><span>Owner</span><input class="in" data-k="owner" value="${esc(x.owner)}" list="spOwners"></label>
        <label class="f"><span>Time limit (hours, 0 = none)</span><input class="in" data-k="hours" type="number" min="0" step="0.5" value="${esc(x.hours)}"></label>
        <label class="f"><span>Must be filled before it moves on (comma separated)</span><input class="in" data-k="needs" value="${esc((x.needs || []).join(', '))}"></label></div>
      <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:14px"><label style="display:flex;gap:6px;align-items:center"><input type="checkbox" data-k="customer_told"${x.customer_told ? ' checked' : ''}>Tell the customer when it gets here</label>
        <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" data-k="waiting"${x.waiting ? ' checked' : ''}>Waiting on someone outside (reply clock pauses)</label></div>
      <div style="font-size:14px"><span class="mut">Can move to:</span> ${f.stages.filter(y => y.key !== x.key).map(y => `<label style="display:inline-flex;gap:4px;align-items:center;margin:2px 8px 2px 0"><input type="checkbox" data-arrow="${esc(y.key)}"${(f.arrows[x.key] || []).includes(y.key) ? ' checked' : ''}>${esc(y.name)}</label>`).join('')}</div>
      <input type="hidden" data-k="key" value="${esc(x.key)}">
      ${i ? `<button class="btn soft sm" type="button" data-stagedel="1" style="align-self:flex-start">Remove this stage</button>` : ''}</fieldset>`;
    return sec(`${esc(f.name)}`, `<form class="spFlow" data-key="${esc(f.key)}" style="display:flex;flex-direction:column;gap:10px">
      <datalist id="spOwners">${Object.entries(OWN).map(([k, n]) => `<option value="${k}">${esc(n)}</option>`).join('')}<option value="person:">A named person (person:Meena)</option><option value="queue:">A queue (queue:Billing)</option></datalist>
      <label class="f"><span>Name</span><input class="in" name="name" value="${esc(f.name)}"></label>
      <label class="f"><span>Ticket categories that use it (comma separated; empty = tickets no other workflow takes)</span><input class="in" name="categories" value="${esc((f.categories || []).join(', '))}"></label>
      <div data-stages style="display:flex;flex-direction:column;gap:10px">${f.stages.map(row).join('')}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-stageadd="1">Add a stage</button><button class="btn sm" type="submit">Save the workflow</button>${ST.flows.length > 1 ? `<button class="btn soft sm" type="button" data-flowdel="${esc(f.key)}">Remove workflow</button>` : ''}</div></form>`);
  }
  function flowFrom(form) {
    const stages = [...form.querySelectorAll('[data-stage]')].map(fs => {
      const g = k => fs.querySelector(`[data-k=${k}]`);
      return {key: g('key').value || g('name').value, name: g('name').value, owner: g('owner').value.trim() || 'team', hours: Number(g('hours').value || 0),
        needs: g('needs').value.split(',').map(x => x.trim()).filter(Boolean), customer_told: g('customer_told').checked, waiting: g('waiting').checked,
        _to: [...fs.querySelectorAll('[data-arrow]')].filter(c => c.checked).map(c => c.dataset.arrow)};
    });
    const arrows = Object.fromEntries(stages.map(x => [x.key, x._to]));
    stages.forEach(x => delete x._to);
    return {key: form.dataset.key, name: form.querySelector('[name=name]').value, categories: form.querySelector('[name=categories]').value.split(',').map(x => x.trim()).filter(Boolean), stages, arrows};
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
    const tr = await api('GET', '/api/seva/trust').catch(() => ({rows: [], topics: {}, levels: {}}));
    const wr = (await api('GET', '/api/seva/watch').catch(() => ({}))).rules || {};
    const hr = await api('GET', '/api/seva/handover/rules').catch(() => ({on: {}, names: {}, fixed: []}));
    const cho = await api('GET', '/api/seva/channels').catch(() => ({channels: [], catalog: {kinds: [], not_built: {}}}));
    const wc = await api('GET', '/api/seva/webchat').catch(() => ({}));
    const em = (await api('GET', '/api/seva/email').catch(() => ({}))).email || null;
    const emSec = sec('Support email', `<p class="mut" style="margin:0">Mail to your support address comes into this desk; Hoola answers from your knowledge in the same thread, from your address, with your signature. Automatic mails, mailing lists and your own address are never answered. For Gmail or Microsoft 365 use an app password.</p>
      ${em ? `<div class="row">${pill(em.status === 'ok' ? 'ok' : em.status === 'error' ? 'bad' : 'warn', em.status === 'ok' ? 'Working' : em.status === 'error' ? 'Problem' : 'Saved')}<div style="flex:1;min-width:0"><div class="t">${esc(em.address)}</div><div class="s">${esc(em.note || '')}</div>${em.last_poll ? `<div class="s">Last read ${esc(when(em.last_poll))}</div>` : ''}</div><button class="btn soft sm" type="button" data-mailcheck="1">Check</button><button class="btn soft sm" type="button" data-mailpoll="1">Read now</button></div>
        ${em.forward ? `<div class="s"><b>Or forward your support mail to:</b> <code>${esc(em.forward)}</code></div>` : ''}` : ''}
      <form id="spMail" style="display:flex;flex-direction:column;gap:10px"><div class="grid2" style="gap:14px">
        ${field('address', 'Your support address', `type="email" value="${esc((em || {}).address || '')}" placeholder="help@yourshop.com" required`)}
        ${field('name', 'Name it is sent from', `value="${esc((em || {}).name || '')}" placeholder="Your shop support"`)}
        ${field('imap_host', 'Reading server (IMAP)', `value="${esc((em || {}).imap_host || '')}" placeholder="imap.gmail.com"`)}
        ${field('smtp_host', 'Sending server (SMTP)', `value="${esc((em || {}).smtp_host || '')}" placeholder="smtp.gmail.com"`)}
        ${field('smtp_port', 'Sending port (465 or 587)', `type="number" value="${esc((em || {}).smtp_port || '465')}" min="1" max="65535"`)}
        ${field('user', 'Mailbox user', `value="${esc((em || {}).user || '')}" autocomplete="off"`)}
        ${field('password', (em || {}).hints && em.hints.password ? 'App password (saved; type only to change it)' : 'App password', 'type="password" autocomplete="new-password"')}</div>
        <label class="f"><span>Signature under every mail</span><textarea class="in" name="signature" rows="2">${esc((em || {}).signature || '')}</textarea></label>
        <div><button class="btn sm" type="submit">Save the support email</button></div></form>`);
    const ws = (wc.web || {}).settings || {}, as = (wc.api || {}).settings || {};
    const once = ST.secretsOnce ? `<div class="row" style="flex-direction:column;align-items:stretch;border:1px solid var(--warnt, #b54708)">${pill('warn', 'Copy now - shown only once')}${Object.entries(ST.secretsOnce).map(([k, x]) => `<div class="s"><b>${esc(k.replace(/_/g, ' '))}:</b> <code style="word-break:break-all">${esc(x)}</code></div>`).join('')}</div>` : '';
    ST.secretsOnce = null;
    const wcSec = sec('Website & app chat', `${once}<p class="mut" style="margin:0">A chat on your website and inside your own app, answered the same way as every other channel. Only the website addresses you list may use the chat.</p>
      <form id="spWeb" style="display:flex;flex-direction:column;gap:10px"><div class="grid2" style="gap:14px">
        ${field('domains', 'Your website addresses (comma between, e.g. shop.example.com)', `value="${esc((ws.domains || []).join(', '))}"`)}
        ${field('title', 'Chat title', `value="${esc(ws.title || 'Chat with us')}"`)}
        ${field('greeting', 'First line visitors see', `value="${esc(ws.greeting || 'Hello! How can we help?')}"`)}
        ${field('colour', 'Colour', `type="color" value="${esc(ws.colour || '#5B45E0')}"`)}</div>
        <label class="row" style="cursor:pointer"><input type="checkbox" name="files"${ws.files !== false ? ' checked' : ''} style="width:18px;height:18px"><span class="t">Visitors may send a picture or PDF (5 MB)</span></label>
        <label class="row" style="cursor:pointer"><input type="checkbox" name="call_me"${ws.call_me !== false ? ' checked' : ''} style="width:18px;height:18px"><span class="t">Show a "Call me" button</span></label>
        <div><button class="btn sm" type="submit">${wc.web ? 'Save the website chat' : 'Make my website chat'}</button></div></form>
      ${wc.web ? `<div class="s"><b>Put this one line on every page of your website:</b></div><textarea class="in" rows="2" readonly>${esc(wc.web.snippet)}</textarea>
        <div class="s"><b>Chat page for an app's web view:</b> <code style="word-break:break-all">${esc(wc.web.page)}</code></div>
        <div class="s"><b>Contact form address (POST name, email or phone, message):</b> <code style="word-break:break-all">${esc(wc.web.form)}</code></div>
        <div class="s">Signed-in users: your server adds data-user-id and data-user-hash (HMAC-SHA256 of the user id with your identity secret ${esc((wc.web.hints || {}).identity_secret || '')}). <button class="btn soft sm" type="button" data-rotate="web:identity_secret">New identity secret</button></div>` : ''}
      <form id="spApi" style="display:flex;flex-direction:column;gap:10px;margin-top:8px"><div class="t">Your app or software</div>
        ${field('webhook_url', 'Your webhook (replies from a person and ticket updates are sent here, signed)', `value="${esc(as.webhook_url || '')}" placeholder="https://your-app.example/hoola"`)}
        <div><button class="btn soft sm" type="submit">${wc.api ? 'Save' : 'Make an API key for my app'}</button></div></form>
      ${wc.api ? `<div class="s"><b>API:</b> <code>POST ${esc(wc.api.api)}</code> with <code>Authorization: Bearer ${esc((wc.api.hints || {}).api_key || '')}</code> and {user_id, text}. <button class="btn soft sm" type="button" data-rotate="api:api_key">New API key</button> <button class="btn soft sm" type="button" data-rotate="api:webhook_secret">New webhook secret</button></div>` : ''}`);
    ST.chKinds = Object.fromEntries((cho.catalog.kinds || []).map(k => [k.kind, k]));
    ST.keyNames = {bot_token: 'Bot token', page_token: 'Page access token', app_secret: 'App secret', verify_token: 'Verify token (any words you choose)',
      account_sid: 'Account SID', auth_token: 'Auth token', from_number: 'Your sending number or sender ID', api_key: 'API key', api_secret: 'API secret',
      signature_secret: 'Signature secret', channel_token: 'Channel access token', channel_secret: 'Channel secret', sender_name: 'Name customers see',
      signing_secret: 'Signing secret', user_token: 'User access token', consumer_secret: 'Consumer secret', access_token: 'OA access token',
      app_id: 'App ID', oa_secret: 'OA secret key', token: 'Token (any words you choose)'};
    const chRows = (cho.channels || []).map(c => `<div class="row" style="flex-wrap:wrap">${pill(c.status === 'ok' ? 'ok' : c.status === 'error' ? 'bad' : 'warn', c.status === 'ok' ? 'Working' : c.status === 'error' ? 'Problem' : 'Joined')}<div style="flex:1;min-width:220px"><div class="t">${esc(c.name)}</div><div class="s">${esc(c.note || '')}</div>
      <div class="s">Webhook address: <code style="word-break:break-all">${esc(c.address)}</code></div></div><button class="btn soft sm" type="button" data-chcheck="${esc(c.id)}">Check</button><button class="btn soft sm" type="button" data-chdel="${esc(c.id)}">Remove</button></div>`).join('');
    const chSec = sec('Your messaging apps', `<p class="mut" style="margin:0">Customers write to you on these; Hoola answers from your knowledge, hands over by your rules and sends ticket updates back on the same app. Your keys are sealed when you save them and are never shown again. WhatsApp is joined in the WhatsApp inbox.</p>
      ${chRows || '<p class="mut" style="margin:0">None joined yet.</p>'}
      <form id="spChAdd" style="display:flex;flex-direction:column;gap:10px"><label class="f"><span>Join an app</span><select class="in" name="kind" id="spChKind"><option value="">Choose…</option>${(cho.catalog.kinds || []).map(k => `<option value="${esc(k.kind)}">${esc(k.name)}</option>`).join('')}</select></label>
        <div id="spChKeys"></div><div><button class="btn sm" type="submit">Join</button></div></form>
      <details><summary class="mut" style="cursor:pointer;font-size:13px">Apps Hoola cannot join</summary>${Object.values(cho.catalog.not_built || {}).map(x => `<div class="s">${esc(x)}</div>`).join('')}</details>`);
    const hoSet = `<form id="spHandRules" style="display:flex;flex-direction:column;gap:18px">${sec('When Hoola hands over to a person', `<p class="mut" style="margin:0">The person gets a hand-over packet: who the customer is, the problem, what Hoola checked and told them, the deadline and a draft reply. The customer is told a time only from your team's real waiting times.</p>
      ${Object.entries(hr.names || {}).map(([k, n]) => `<label class="row" style="cursor:pointer"><input type="checkbox" name="r_${k}"${(hr.on || {})[k] ? ' checked' : ''}${(hr.fixed || []).includes(k) ? ' disabled' : ''} style="width:18px;height:18px"><span class="t">${esc(n)}${(hr.fixed || []).includes(k) ? ' (always)' : ''}</span></label>`).join('')}
      <div class="grid2" style="gap:14px">${field('vip', 'VIP numbers (comma between)', `value="${esc((hr.vip || []).join(', '))}"`)}${field('words', 'Other words that always go to a person (comma between)', `value="${esc((hr.words || []).join(', '))}"`)}
      ${field('callback_h', 'Call-back window on a phone call (hours)', `type="number" min="0.5" max="48" step="0.5" value="${esc(hr.callback_h ?? 2)}"`)}</div>
      <label class="row" style="cursor:pointer"><input type="checkbox" name="page_urgent"${hr.page_urgent ? ' checked' : ''} style="width:18px;height:18px"><span class="t">Tell me at once about an urgent one, even when closed</span></label>
      <p class="mut" style="margin:0;font-size:13px">On a phone call Hoola gives a call-back time; a live transfer to a person's phone is not built yet.</p>`)}
      <div><button class="btn sm" type="submit">Save hand-over rules</button></div></form>`;
    const DN = {mon: 'Monday', tue: 'Tuesday', wed: 'Wednesday', thu: 'Thursday', fri: 'Friday', sat: 'Saturday', sun: 'Sunday'};
    const wchk = (name, label) => `<label class="row" style="cursor:pointer"><input type="checkbox" name="${name}"${wr[name] ? ' checked' : ''} style="width:18px;height:18px"><span class="t">${esc(label)}</span></label>`;
    const dayRow = d => { const w = (wr.week || {})[d] || []; return `<div class="row" style="flex-wrap:wrap"><b style="width:100px">${DN[d]}</b>
      <label class="f" style="flex:1;min-width:110px"><span>Opens</span><input class="in" name="w_${d}_0" type="time" value="${esc(w[0] || '')}"></label>
      <label class="f" style="flex:1;min-width:110px"><span>Closes</span><input class="in" name="w_${d}_1" type="time" value="${esc(w[1] || '')}"></label></div>`; };
    const watchSec = `<form id="spWatch" style="display:flex;flex-direction:column;gap:18px">${sec('Working hours', `<p class="mut" style="margin:0">Time zone: ${esc(wr.tz || '')}. When on, every clock and deadline counts only these hours. Leave a day empty when you are closed.</p>
        ${wchk('hours_on', 'Count only my working hours (off = around the clock)')}${(wr.days || Object.keys(DN)).map(dayRow).join('')}
        ${field('holidays', 'Holidays (YYYY-MM-DD, comma between)', `value="${esc((wr.holidays || []).join(', '))}"`)}`)}
      ${sec('Until it is really solved', `${wchk('confirm_on', 'Ask the customer "did this fix it?" before closing')}<div class="grid2" style="gap:14px">
        ${field('confirm_days', 'Close by itself after no answer for (days)', `type="number" min="0.5" step="0.5" value="${esc(wr.confirm_days ?? 3)}"`)}
        ${field('reopen_days', 'The same problem again within (days) reopens it', `type="number" min="0" step="1" value="${esc(wr.reopen_days ?? 7)}"`)}
        ${field('update_h', 'Tell the customer "still on it" when nothing moved for (hours, 0 = never)', `type="number" min="0" step="1" value="${esc(wr.update_h ?? 24)}"`)}</div>`)}
      ${sec('Reminders', `${wchk('ladder_on', 'Remind people until the ticket moves')}<div class="grid2" style="gap:14px">
        ${field('before_h', 'Remind the ticket owner this many hours before the deadline', `type="number" min="0" step="0.5" value="${esc(wr.before_h ?? 1)}"`)}
        ${field('supervisor', 'Supervisor told at the deadline', `value="${esc(wr.supervisor || '')}" placeholder="Name"`)}
        ${field('boss_after_h', 'Tell me when it is this many hours late', `type="number" min="0" step="0.5" value="${esc(wr.boss_after_h ?? 4)}"`)}
        ${field('repeat_h', 'Then again every (hours)', `type="number" min="0.5" step="0.5" value="${esc(wr.repeat_h ?? 4)}"`)}
        ${field('max_day', 'At most this many reminders a day per ticket', `type="number" min="1" max="48" value="${esc(wr.max_day ?? 6)}"`)}
        ${field('quiet_0', 'Quiet hours from', `type="time" value="${esc((wr.quiet || [])[0] || '')}"`)}${field('quiet_1', 'Quiet hours until', `type="time" value="${esc((wr.quiet || [])[1] || '')}"`)}</div>
        <p class="mut" style="margin:0;font-size:13px">Reminders reach your Hoola app and this desk; nothing is sent in quiet hours.</p>`)}
      <div><button class="btn sm" type="submit">Save hours and reminders</button></div></form>`;
    const lv = cur => Object.entries(tr.levels || {}).map(([k, n]) => `<option value="${k}"${cur === k ? ' selected' : ''}>${esc(n)}</option>`).join('');
    const trows = [['*', '*', 'Everything (the starting rule)'], ...Object.entries(tr.topics || {}).map(([k, n]) => [k, '*', n])].map(([topic, channel, name]) => {
      const cur = (tr.rows || []).find(r => r.topic === topic && r.channel === channel);
      return `<div class="row" data-trow data-topic="${esc(topic)}" data-channel="${esc(channel)}" style="flex-wrap:wrap"><div style="flex:1;min-width:180px"><div class="t">${esc(name)}</div>${cur ? '' : `<div class="s">${topic === '*' ? 'Default: Hoola answers alone' : 'Follows the starting rule'}</div>`}</div>
        <label class="sr" for="spTr-${esc(topic)}">How much Hoola may do: ${esc(name)}</label><select class="in" id="spTr-${esc(topic)}" style="width:auto">${cur || topic === '*' ? '' : '<option value="" selected>Same as the starting rule</option>'}${lv(cur ? cur.level : (topic === '*' ? tr.default : ''))}</select><button class="btn soft sm" type="button" data-trustsave="1">Save</button></div>`; }).join('');
    const trustSec = sec('How much Hoola may do', `<p class="mut" style="margin:0">Per topic: answer alone, draft for a person to send, or always hand over. A refund request, an angry or urgent message and "I want a person" always go to a person, whatever you set. Every reply is checked before it goes: its numbers must be in your knowledge, and it never promises a call-back or a refund that nobody made.</p>${trows}`);
    return `${head('Channels & settings', 'Where customers reach you, and the service rules Hoola follows.')}
      ${setupSec}${emSec}${wcSec}${chSec}${trustSec}${hoSet}${watchSec}
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
      if (b.dataset.mailcheck) { const r = await api('POST', '/api/seva/email/check', {}); toast(r.note || 'Checked.', r.status === 'error'); return showPage(true); }
      if (b.dataset.mailpoll) { const r = await api('POST', '/api/seva/email/poll', {}); toast(`${r.read} new mail${r.read === 1 ? '' : 's'} read.`); return showPage(true); }
      if (b.dataset.rotate) { const [k, w] = b.dataset.rotate.split(':'); if (!confirm('The old one stops working at once. Go on?')) return;
        const r = await api('POST', `/api/seva/webchat/${k}/rotate`, {what: w}); ST.secretsOnce = r.secrets_once || null; toast(r.say || 'Renewed.'); return showPage(true); }
      if (b.dataset.cfile) { const r = await fetch(`/api/seva/chatfiles/${enc(b.dataset.cfile)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, credentials: 'omit'});
        if (!r.ok) { toast('The file could not be opened.', true); return; }
        const u = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = u; a.download = ''; a.click(); setTimeout(() => URL.revokeObjectURL(u), 4000); return; }
      if (b.dataset.chcheck) { const r = await api('POST', `/api/seva/channels/${enc(b.dataset.chcheck)}/check`, {}); toast(r.note || 'Checked.', r.status === 'error'); return showPage(true); }
      if (b.dataset.chdel) { if (!confirm('Remove this app? Its keys are forgotten.')) return; const r = await api('DELETE', `/api/seva/channels/${enc(b.dataset.chdel)}`); toast(r.say || 'Removed.'); return showPage(true); }
      if (b.dataset.take) { const r = await api('POST', `/api/seva/handovers/${enc(b.dataset.take)}/take`, {}); toast(r.say || 'Taken.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.confirm) { const r = await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/confirm`, {yes: b.dataset.confirm === 'yes'}); toast(r.say || 'Saved.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.filter) { ST.filter = b.dataset.filter; return showPage(true); }
      if (b.dataset.days) { ST.days = Number(b.dataset.days); return showPage(true); }
      if (b.dataset.merge) { const r = await api('POST', `/api/seva/tickets/${enc(b.dataset.merge)}/merge`, {into: b.dataset.into}); toast(r.say || 'Joined.'); return showPage(true); }
      if (b.dataset.decide) return decide(b.dataset.decide, b.dataset.yes === '1');
      if (b.dataset.cancel) { await api('POST', `/api/seva/exceptions/${enc(b.dataset.cancel)}/cancel`); toast('Request withdrawn.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.stageadd) { const box = b.closest('form').querySelector('[data-stages]'); const n = box.querySelectorAll('[data-stage]').length;
        const f = flowFrom(b.closest('form')); f.stages.splice(n - 1, 0, {key: 'step_' + (n + 1), name: 'New step', owner: 'team', hours: 24, needs: [], customer_told: false, waiting: false});
        const prev = f.stages[n - 2]; if (prev) f.arrows[prev.key] = [...new Set([...(f.arrows[prev.key] || []), 'step_' + (n + 1)])]; f.arrows['step_' + (n + 1)] = [f.stages[f.stages.length - 1].key];
        const tmp = document.createElement('div'); tmp.innerHTML = flowEditor(f); b.closest('section').replaceWith(tmp.firstElementChild); return; }
      if (b.dataset.stagedel) { b.closest('[data-stage]').remove(); return; }
      if (b.dataset.flowdel) { if (!confirm('Remove this workflow? Tickets still open in it must be moved first.')) return; const r = await api('DELETE', `/api/seva/flows/${enc(b.dataset.flowdel)}`); toast(r.say || 'Removed.'); return showPage(true); }
      if (b.dataset.draftact) { const r = await api('POST', `/api/seva/drafts/${enc(b.dataset.id)}`, {action: b.dataset.draftact}); toast(r.say || 'Done.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.trustsave) { const row = b.closest('[data-trow]'); const level = row.querySelector('select').value;
        if (!level) { toast('Pick a level first.', true); return; }
        const r = await api('PUT', '/api/seva/trust', {level, topic: row.dataset.topic, channel: row.dataset.channel}); toast(r.say || 'Saved.'); return showPage(true); }
      if (b.dataset.kbhist) { const box = $('#spHist-' + b.dataset.kbhist); if (box.innerHTML) { box.innerHTML = ''; return; }
        const h = await api('GET', `/api/seva/kb/${enc(b.dataset.kbhist)}/history`);
        box.innerHTML = `<div class="tline" style="margin-top:8px">${(h.versions || []).map(v => `<div class="row" style="padding:8px 10px"><div style="flex:1;min-width:0"><div class="t">Version ${num(v.version)} · ${esc(v.why)} · ${esc(v.by)} · ${esc(when(v.at))}</div><div class="s">${esc(v.answer)}</div></div>${v.version !== h.entry.version ? `<button class="btn soft sm" type="button" data-kbrestore="${esc(b.dataset.kbhist)}" data-v="${v.version}">Put back</button>` : pill('ok', 'Now')}</div>`).join('')}</div>`; return; }
      if (b.dataset.kbrestore) { if (!confirm('Put this version back? It becomes the answer customers get.')) return;
        const r = await api('POST', `/api/seva/kb/${enc(b.dataset.kbrestore)}/restore`, {version: Number(b.dataset.v)}); toast(r.say || 'Put back.'); return showPage(true); }
      if (b.dataset.kbmeta) { const owner = prompt('Who keeps this answer right? (a name, or empty)', b.dataset.owner); if (owner === null) return;
        const rb = prompt('Review by (YYYY-MM-DD). After it Hoola stops using the answer until someone looks again. Empty = no date.', b.dataset.review); if (rb === null) return;
        const r = await api('POST', `/api/seva/kb/${enc(b.dataset.kbmeta)}/meta`, {owner, review_by: rb}); toast(r.say || 'Saved.'); return showPage(true); }
      if (b.dataset.kbok) { const r = await api('POST', `/api/seva/kb/${enc(b.dataset.kbok)}/meta`, {checked: true}); toast('Checked. Hoola uses it again.'); await refreshDesk(false); return showPage(true); }
      if (b.dataset.suggno) { await api('POST', `/api/seva/suggestions/${enc(b.dataset.suggno)}`, {yes: false}); toast('Dismissed.'); return showPage(true); }
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
      if (f.classList.contains('spSugg')) { const r = await api('POST', `/api/seva/suggestions/${enc(f.dataset.id)}`, {yes: true, question: v.question, answer: v.answer}); toast(r.say || 'Added.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spHelp') { const fd = new FormData(); const file = f.querySelector('[name=file]').files[0];
        if (file) fd.append('file', file); else if (S(v.url).trim()) fd.append('url', v.url.trim()); else { toast('Give the address or choose a file.', true); return; }
        toast('Reading…'); const r = await api('POST', '/api/seva/kb/helpcenter', undefined, {form: fd}); toast(r.say || 'Drafts are ready to check.'); await refreshDesk(false); return showPage(true); }
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
      if (f.classList.contains('spFlow')) { const body = flowFrom(f); const r = await api('PUT', `/api/seva/flows/${enc(body.key)}`, body); toast(r.say || 'Saved.'); return showPage(true); }
      if (f.id === 'spFlowNew') { const key = S(v.name).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 30) || 'flow';
        const r = await api('PUT', `/api/seva/flows/${enc(key)}`, {key, name: v.name, stages: [{key: 'new', name: 'New', owner: 'hoola', hours: 2}, {key: 'working', name: 'Being worked on', owner: 'team', hours: 48, customer_told: true}, {key: 'closed', name: 'Closed', owner: 'team', hours: 0}], arrows: {new: ['working'], working: ['closed'], closed: []}});
        toast(r.say || 'Added.'); return showPage(true); }
      if (f.id === 'spMail') { const body = {address: v.address, name: v.name, imap_host: v.imap_host, smtp_host: v.smtp_host, smtp_port: v.smtp_port,
          user: v.user, signature: v.signature}; if (v.password) body.password = v.password;
        const r = await api('PUT', '/api/seva/email', body); toast(r.say || 'Saved.'); return showPage(true); }
      if (f.id === 'spWeb') { const r = await api('PUT', '/api/seva/webchat/web', {domains: S(v.domains).split(',').map(x => x.trim()).filter(Boolean),
          title: v.title, greeting: v.greeting, colour: v.colour, files: !!f.files.checked, call_me: !!f.call_me.checked});
        ST.secretsOnce = r.secrets_once || null; toast(r.say || 'Saved.'); return showPage(true); }
      if (f.id === 'spApi') { const r = await api('PUT', '/api/seva/webchat/api', {webhook_url: v.webhook_url || ''}); ST.secretsOnce = r.secrets_once || null; toast(r.say || 'Saved.'); return showPage(true); }
      if (f.id === 'spChAdd') { if (!v.kind) { toast('Choose an app.', true); return; }
        const keys = Object.fromEntries(Object.entries(v).filter(([k]) => k.startsWith('k_')).map(([k, x]) => [k.slice(2), x]));
        const r = await api('POST', '/api/seva/channels', {kind: v.kind, keys}); toast(r.say || 'Joined.'); return showPage(true); }
      if (f.id === 'spChat') { const r = await api('POST', `/api/seva/chats/${enc(f.dataset.cust)}/send`, {text: v.text}); toast(r.say || 'Sent.'); return showPage(true); }
      if (f.id === 'spHandRules') {
        const on = {}; for (const el of f.querySelectorAll('input[name^="r_"]')) if (!el.disabled) on[el.name.slice(2)] = el.checked;
        const list = x => S(x).split(',').map(y => y.trim()).filter(Boolean);
        const r = await api('PUT', '/api/seva/handover/rules', {on, vip: list(v.vip), words: list(v.words), callback_h: Number(v.callback_h), page_urgent: !!f.page_urgent.checked});
        toast(r.say || 'Saved.'); return showPage(true);
      }
      if (f.classList.contains('spBack')) { const r = await api('POST', `/api/seva/handovers/${enc(f.dataset.id)}/back`, {note: v.note || ''}); toast(r.say || 'Given back.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spHand') { const r = await api('POST', '/api/seva/handovers', {ticket: ST.ticket.number, reason: v.reason || '', rule: 'asked'}); toast(r.say ? 'Handed to a person. ' + (r.customer_line ? 'The customer is told: ' + r.customer_line : '') : 'Handed over.'); return showPage(true); }
      if (f.id === 'spWatch') {
        const week = {}; for (const d of ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']) { const a = S(v[`w_${d}_0`]), z = S(v[`w_${d}_1`]); week[d] = a && z ? [a, z] : []; }
        const n = k => Number(v[k]);
        const body = {hours_on: !!f.hours_on.checked, confirm_on: !!f.confirm_on.checked, ladder_on: !!f.ladder_on.checked, week,
          holidays: S(v.holidays).split(',').map(x => x.trim()).filter(Boolean), confirm_days: n('confirm_days'), reopen_days: n('reopen_days'),
          update_h: n('update_h'), before_h: n('before_h'), boss_after_h: n('boss_after_h'), repeat_h: n('repeat_h'), max_day: n('max_day'),
          supervisor: S(v.supervisor), quiet: v.quiet_0 && v.quiet_1 ? [v.quiet_0, v.quiet_1] : []};
        const r = await api('PUT', '/api/seva/watch', body); toast(r.say || 'Saved.'); return showPage(true);
      }
      if (f.id === 'spMove') { const to = (e.submitter || {}).value; if (!to) return; const fields = Object.fromEntries(Object.entries(v).filter(([k]) => k.startsWith('f_')).map(([k, x]) => [k.slice(2), x]));
        const r = await api('POST', `/api/seva/tickets/${enc(ST.ticket.number)}/move`, {to, why: v.why || '', fields}); toast(r.say || 'Moved.'); await refreshDesk(false); return showPage(true); }
      if (f.id === 'spTest') { ST.test = await api('POST', '/api/seva/engine/try', {text: v.question, channel: v.channel || 'whatsapp'}); return showPage(true); }
      if (f.classList.contains('spDraft')) { const r = await api('POST', `/api/seva/drafts/${enc(f.dataset.id)}`, {action: 'send', text: v.text}); toast(r.say || 'Sent.'); await refreshDesk(false); return showPage(true); }
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
