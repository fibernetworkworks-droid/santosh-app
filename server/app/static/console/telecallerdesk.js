/* v0.999.67 AI TELECALLER DESK - the Telecaller employee's own section (the Lead desk's twin; owner: "WE DONT WANT HUMAN
   TO CALL ANY MORE --- EVERY CALL TO BE GENERATED AND TALK BY AI ONLY ON HUMAN PROVIDED DATA" -> the design
   claude.ai/artifact/4jWq9iSXTiSci6KkWdf1St + knowledge from APIs / connectors / documents + "MAKE IT GLOBAL").
   A thin top bar, then the Telecaller chat (its own conversation, kind 'telecall') beside the desk's pages: Today, Call
   lists (+ one list), Calls (+ one call), Knowledge, Script & test, Incoming, Settings. The chat column is never redrawn
   when a page changes. Starting a list, approving knowledge, keys, the line switch and a country's law stay her taps here.
   Routes: #/<page>, #/list/<id>, #/call/<id>, #/source/<id>. */
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
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['lists', 'Call lists'], ['calls', 'Calls'], ['knowledge', 'Knowledge'], ['script', 'Script & test'],
    ['incoming', 'Incoming'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['How are my calls going?', 'Who needs me today?', 'What is not ready yet?'],
    lists: ['Make a call list for my Diwali offer', 'Put my new enquiries on a list', 'Pause all calling'],
    calls: ['Summarise today’s calls', 'Who was interested?', 'Which questions could Hoola not answer?'],
    knowledge: ['Add my price list', 'Read my website for products and prices', 'What does Hoola know about my business?'],
    script: ['Write a call script for AMC renewals', 'Add a step to offer a free site visit', 'Make the opening shorter'],
    incoming: ['Who should I call back?', 'Turn on AI answering after hours', 'What did callers ask today?'],
    settings: ['How do I connect Twilio?', 'Which countries can I call?', 'What does a call cost?']};
  const OUT_PILL = {appointment: 'ok', answered: 'ok', interested: 'ok', converted: 'ok', message: 'warn', callback: 'warn', transferred: 'v',
    complaint: 'bad', no_answer: '', busy: '', voicemail: '', failed: 'bad', dnd: 'bad'};
  const ST_PILL = {running: 'ok', ready: 'v', draft: '', paused: 'warn', done: 'v', stopped: 'bad'};
  const MAXF = 20, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], test: [], card: null};
  try { ST.side = localStorage.getItem('hoola.tele.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.tele.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/telecaller/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.phone, '')}</div>
        <h1 class="sd-h">Your Telecaller is not hired yet</h1>
        <p class="lead">Hoola makes and speaks every call: to the people in your lists, and on your own number. Hire it here or from AI Employees.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="tcHire">Hire the Telecaller</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#tcHire').onclick = async () => { try { await api('POST', '/api/employees/telecaller/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame(); readTab(); paintTabs(); showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 30000));
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    if (['list', 'call', 'source'].includes(parts[0]) && parts[1]) { ST.tab = parts[0]; ST.arg = decodeURIComponent(parts[1]); return; }
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today'; ST.arg = '';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.phone, '')}</div>
          <div style="min-width:0"><div class="sd-name">Telecaller</div>
            <div class="sd-site">Hoola makes and speaks every call, only to people in your data.</div></div>
          <span id="tcState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Telecaller chat">
          <div class="sd-chathead"><div class="t"><b>Telecaller chat</b><span>Attach a sheet, price list or brochure · calls start only on your tap</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="ac-files" id="adFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="adPick" multiple hidden accept=".csv,.xlsx,.xlsm,.txt,.md,application/pdf,.pdf,.docx,image/*">
          <input type="file" id="tcPickOne" hidden accept=".csv,.xlsx,.xlsm,.txt,.md,application/pdf,.pdf,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Telecaller desk" id="sdTabs"></nav>
          <div id="tcPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or attach a sheet / price list…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#adPick').click()});
    $('#adPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.tele.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`; foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.tele.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon(); if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/telecaller/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#tcPage').addEventListener('click', onClick);
    $('#tcPage').addEventListener('submit', onSubmit);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d || {}, el = $('#tcState'); if (!el) return;
    const ready = !(d.problems || []).length;
    el.innerHTML = `<span class="pill ${d.running ? 'ok' : ready ? 'v' : 'warn'}"><span class="dt"></span>${d.running ? `${d.running} list${d.running > 1 ? 's' : ''} calling` : ready ? 'Ready' : 'Setup needed'}</span>`;
  }
  function paintTabs() {
    const d = ST.d || {}, cur = {list: 'lists', call: 'calls', source: 'knowledge'}[ST.tab] || ST.tab;
    const badge = {knowledge: (d.knowledge || {}).waiting, incoming: d.messages};
    $('#sdTabs').innerHTML = TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === cur}">${esc(n)}${
      badge[k] ? `<span class="n">${num(badge[k])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(all) {
    try { ST.d = await api('GET', '/api/telecaller/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (all || ST.tab === 'today' || (ST.tab === 'list' && ST.arg)) showPage(true);
  }

  /* ---------------------------------------------------------------- page helpers */
  const pill = (cls, name) => `<span class="pill ${cls || ''}">${esc(name)}</span>`;
  const when = v => { if (!v) return ''; const d = new Date(v); return isNaN(d) ? S(v) : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const sec = (title, body, right = '') => `<section class="card" style="display:flex;flex-direction:column;gap:12px"><div style="display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap"><h2 style="margin:0;font-size:16px;font-weight:600">${title}</h2>${right}</div>${body}</section>`;
  const head = (title, sub, right = '') => `<div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin:4px 0 2px"><div style="flex:1;min-width:220px"><h1 class="sd-h serif" style="margin:0">${title}</h1>${sub ? `<p class="mut" style="margin:6px 0 0">${sub}</p>` : ''}</div>${right}</div>`;
  const kpi = (v, n) => `<div class="card kpi"><div class="v">${esc(v)}</div><div class="n">${esc(n)}</div></div>`;
  const field = (name, label, attrs = '') => `<label class="f"><span>${esc(label)}</span><input class="in" name="${name}" ${attrs}></label>`;
  async function showPage(quiet) {
    const box = $('#tcPage'); if (!box) return;
    if (!quiet) { box.innerHTML = '<div class="empty" style="padding:28px">Loading…</div>'; $('#sdDesk').scrollTop = 0; }
    starters();
    try {
      const t = ST.tab;
      if (t === 'today') box.innerHTML = await pageToday();
      else if (t === 'lists') box.innerHTML = await pageLists();
      else if (t === 'list') box.innerHTML = await pageList(ST.arg);
      else if (t === 'calls') box.innerHTML = await pageCalls();
      else if (t === 'call') box.innerHTML = await pageCall(ST.arg);
      else if (t === 'knowledge') box.innerHTML = await pageKnowledge();
      else if (t === 'source') box.innerHTML = await pageSource(ST.arg);
      else if (t === 'script') box.innerHTML = await pageScript();
      else if (t === 'incoming') box.innerHTML = await pageIncoming();
      else if (t === 'settings') box.innerHTML = await pageSettings();
    } catch (e) { box.innerHTML = `<div class="card"><p class="lead">${esc(e.message)}</p><button class="btn soft sm" type="button" data-act="reload">Try again</button></div>`; }
  }

  /* ---------------------------------------------------------------- Today */
  async function pageToday() {
    const d = ST.d || {};
    const calls = (await api('GET', '/api/callcentre/calls?limit=30')).calls || [];
    const out = calls.filter(c => c.direction === 'out');
    const needs = calls.filter(c => ['message', 'transferred', 'complaint'].includes(c.outcome)).slice(0, 6);
    const prob = (d.problems || []).map(p => `<div class="row"><span class="pill warn"><span class="dt"></span></span><div style="flex:1"><div class="t">${esc(p[0].toUpperCase() + p.slice(1))}</div></div><a class="btn soft sm" href="#/${/script/.test(p) ? 'script' : /cap|list/.test(p) ? 'lists' : 'settings'}">Fix</a></div>`).join('');
    const lists = (d.lists || []).map(x => listRow(x)).join('');
    const nrow = needs.map(c => `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/call/${enc(c.id)}">${esc(c.caller_name || c.caller_masked || 'Caller')}</a> ${pill(OUT_PILL[c.outcome], c.outcome)}</div><div class="s">${esc(c.summary || '')}</div></div><a class="btn sm" href="#/call/${enc(c.id)}">Open</a></div>`).join('');
    return `${head(d.running ? 'Hoola is calling.' : 'Nobody is being called right now.', 'Every call says it is an AI. Calls start only when you tap Start on a list.')}
      <div class="grid">${kpi(num(out.length), 'calls made (recent)')}${kpi(num(d.calls_in), 'calls answered')}${kpi(num((d.knowledge || {}).facts), 'facts Hoola may use')}${kpi(`${num(d.spent_today)} ${S(d.currency)}`, 'spent in 24 h')}</div>
      ${prob ? sec('Before Hoola can call', prob) : ''}
      ${sec('Needs you', nrow || '<p class="mut" style="margin:0">Nothing waits for you.</p>')}
      ${sec('Call lists', lists || '<p class="mut" style="margin:0">No call list yet. Make one on Call lists, or ask in the chat.</p>', '<a class="btn soft sm" href="#/lists">All lists</a>')}`;
  }
  function listRow(x) {
    const p = x.people || {}, total = p.total || 0, done = (p.done || 0) + (p.dnd || 0) + (p.skipped || 0);
    return `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/list/${enc(x.id)}">${esc(x.name)}</a> ${pill(ST_PILL[x.status], x.status)}</div>
      <div class="s">${num(done)} of ${num(total)} done · ${num(p.retry || 0)} to try again · ${num(p.calling || 0)} on a call now</div>
      <div class="bar" style="margin-top:6px"><i style="width:${total ? Math.round(100 * done / total) : 0}%"></i></div></div><a class="btn sm" href="#/list/${enc(x.id)}">Open</a></div>`;
  }

  /* ---------------------------------------------------------------- Call lists */
  async function pageLists() {
    const r = await api('GET', '/api/callcentre/campaigns');
    const rows = (r.campaigns || []).map(listRow).join('');
    return `${head('Call lists', 'Hoola calls only the people on a list you made, from your approved script, inside their own calling hours.')}
      ${sec('Your lists', rows || '<p class="mut" style="margin:0">None yet.</p>')}
      ${sec('New call list', `<form id="tcNewList" class="grid2" style="gap:14px">
        ${field('name', 'Name', 'required placeholder="Diwali AC offer"')}
        ${field('goal', 'Why Hoola calls (said at the start)', 'placeholder="the AC enquiry you sent us"')}
        <label class="f"><span>Who they are</span><select class="in" name="basis"><option value="asked">They asked to be contacted</option><option value="customer">My customers</option><option value="cold">A list of people who never asked</option></select></label>
        <label class="f"><span>Purpose</span><select class="in" name="purpose">${['sales', 'followup', 'renewal', 'dues', 'appointment', 'feedback', 'reminder', 'survey', 'service'].map(x => `<option>${x}</option>`).join('')}</select></label>
        ${field('start_hour', 'Calls from', 'value="10:00"')}${field('end_hour', 'Calls until', 'value="19:00"')}
        ${field('daily_cap', `Money a day (${esc((ST.d || {}).currency || '')})`, 'type="number" min="0" step="1" required')}
        ${field('at_once', 'Calls at once', 'type="number" min="1" max="10" value="2"')}
        ${field('max_tries', 'Tries per person', 'type="number" min="1" max="6" value="3"')}
        ${field('fields', 'Answers to bring back (comma separated)', 'placeholder="need, budget, visit day"')}
        <label class="f" style="grid-column:1/-1"><span>Message for an answering machine</span><input class="in" name="voicemail" placeholder="This is Hoola for … about your enquiry. We will call again tomorrow."></label>
        <div><button class="btn sm" type="submit">Make the list</button></div></form>`)}`;
  }
  async function pageList(id) {
    const [camps, ppl, card] = await Promise.all([api('GET', '/api/callcentre/campaigns'), api('GET', `/api/callcentre/campaigns/${enc(id)}/people`),
      api('GET', `/api/callcentre/campaigns/${enc(id)}/card`)]);
    const c = (camps.campaigns || []).find(x => x.id === id); if (!c) throw new Error('No such call list.');
    ST.card = card;
    const held = Object.entries(card.held || {}).map(([k, v]) => `<div class="row"><span class="pill warn">${num(v)}</span><div style="flex:1" class="t">${esc(k)}</div></div>`).join('');
    const est = card.estimate || {};
    const startBox = c.status === 'running' ? `<div style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-camp="pause">Pause</button><button class="btn soft sm bad" type="button" data-camp="stop">Stop</button></div>`
      : `<div class="card" style="background:var(--soft);display:flex;flex-direction:column;gap:8px"><b>Start calling</b>
        <p class="mut" style="margin:0;font-size:13.5px">${num(card.callable)} people can be called · ${esc(card.hours)} their own time · ${num(card.at_once)} at once · up to ${num(card.max_tries)} tries · script v${esc(card.script_version || '-')} · about ${num(est.total)} ${esc(est.currency || '')} (${num(est.per_minute)} a minute, ~${num(est.minutes_each)} min a call). ${esc(est.note || '')} Stops each day at ${num(card.daily_cap)} ${esc(est.currency || '')}.</p>
        ${(card.problems || []).length ? `<p style="margin:0;font-size:13.5px;color:var(--badt)">Not ready: ${esc(card.problems.join('; '))}.</p>` : ''}
        <div><button class="btn sm" type="button" data-camp="start" ${(card.problems || []).length ? 'disabled' : ''}>Start calls</button></div></div>`;
    const rows = (ppl.people || []).map(p => `<tr><td><b>${esc(p.name || '–')}</b><div class="mut" style="font-size:12.5px">${esc(p.phone)} · ${esc(p.country || '')}</div></td>
      <td>${esc({asked: 'asked to be contacted', customer: 'customer', cold: 'never asked', unknown: 'not known'}[p.basis] || p.basis)}</td><td>${num(p.tries)}</td>
      <td>${p.outcome ? pill(OUT_PILL[p.outcome], p.outcome) : pill('', p.status)}${p.why ? `<div class="mut" style="font-size:12.5px">${esc(p.why)}</div>` : ''}</td>
      <td class="mut" style="font-size:12.5px">${esc(Object.entries(p.result || {}).map(([k, v]) => `${k}: ${v}`).join(' · '))}</td>
      <td>${p.call_id ? `<a class="btn soft sm" href="#/call/${enc(p.call_id)}">Call</a>` : ''}</td></tr>`).join('');
    return `<div><a class="btn soft sm" href="#/lists">← Call lists</a></div>
      ${head(esc(c.name), esc(c.goal ? `Why: ${c.goal}` : ''), pill(ST_PILL[c.status], c.status))}
      ${startBox}
      ${held ? sec('Held back (not called)', held) : ''}
      ${sec('Add people', `<p class="mut" style="margin:0">Only your own data: a sheet (CSV / Excel with a phone column; optional columns name, country, time zone, language, consent) or your Telecaller leads.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-act="sheet">Add a sheet</button><button class="btn soft sm" type="button" data-act="leads">Add my Telecaller leads</button></div>`)}
      ${sec(`People · ${num((c.people || {}).total)}`, rows ? `<div style="overflow-x:auto"><table class="tb"><thead><tr><th>Person</th><th>Why Hoola may call</th><th>Tries</th><th>Result</th><th>Answers</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="mut" style="margin:0">Nobody yet.</p>')}`;
  }

  /* ---------------------------------------------------------------- Calls */
  async function pageCalls() {
    const calls = (await api('GET', '/api/callcentre/calls?limit=80')).calls || [];
    const rows = calls.map(c => `<tr><td>${c.direction === 'out' ? 'Hoola called' : 'Called in'}</td><td><a href="#/call/${enc(c.id)}"><b>${esc(c.caller_name || c.caller_masked || '–')}</b></a></td>
      <td>${pill(OUT_PILL[c.outcome], c.outcome || c.status)}</td><td class="mut" style="font-size:12.5px">${esc((c.summary || '').slice(0, 140))}</td><td class="mut">${esc(when(c.started_at))}</td></tr>`).join('');
    return `${head('Calls', 'Every call Hoola made or answered. Numbers and card details are hidden in the written record.')}
      <section class="card" style="overflow-x:auto;padding:4px 16px">${rows ? `<table class="tb"><thead><tr><th>Way</th><th>Person</th><th>Result</th><th>Summary</th><th>When</th></tr></thead><tbody>${rows}</tbody></table>` : '<p class="mut" style="padding:14px 0;margin:0">No calls yet.</p>'}</section>`;
  }
  async function pageCall(id) {
    const c = await api('GET', `/api/callcentre/calls/${enc(id)}`);
    const tl = (c.transcript || []).map(([w, t]) => `<div class="${w === 'caller' ? 'me' : 'ai'}"><span class="who">${w === 'caller' ? esc(c.caller_name || 'Person') : 'Hoola'}</span>${esc(t)}</div>`).join('');
    return `<div><a class="btn soft sm" href="#/calls">← Calls</a></div>
      ${head(esc(c.caller_name || c.caller_masked || 'Call'), esc(`${c.direction === 'out' ? 'Hoola called' : 'Called in'} · ${when(c.started_at)} · ${Math.round(c.seconds || 0)} s`), pill(OUT_PILL[c.outcome], c.outcome || c.status))}
      <div class="grid2"><div style="display:flex;flex-direction:column;gap:18px">${sec('What was said', `<div class="tline">${tl || '<p class="mut" style="margin:0">No words were recorded.</p>'}</div>`)}</div>
      <div style="display:flex;flex-direction:column;gap:18px">${sec('Summary', `<p class="say" style="margin:0">${esc(c.summary || '–')}</p>`)}
      ${(c.flags || []).length ? sec('Checked after the call', (c.flags || []).map(f => `<div class="row"><span class="pill warn">${esc(f.kind || 'flag')}</span><div class="s">${esc(f.text || '')}</div></div>`).join('')) : sec('Checked after the call', '<p class="mut" style="margin:0">Nothing outside the script was said.</p>')}</div></div>`;
  }

  /* ---------------------------------------------------------------- Knowledge */
  async function pageKnowledge() {
    const r = await api('GET', '/api/callcentre/knowledge');
    const rows = (r.sources || []).map(x => `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/source/${enc(x.id)}">${esc(x.name)}</a> ${pill(x.status === 'approved' ? 'ok' : x.status === 'waiting' ? 'warn' : x.status === 'failed' ? 'bad' : '', x.status === 'waiting' ? 'waits for your OK' : x.status)}</div>
      <div class="s">${esc({text: 'Your words', file: 'A file', url: 'A web page', sheet: 'A sheet', api: 'Your API', system: 'A joined system'}[x.kind] || x.kind)}${x.mode === 'live' ? ' · asked live during a call' : ` · ${num(x.facts)} facts`}${x.synced_at ? ` · read ${when(x.synced_at)}` : ''}${x.error ? ' · ' + esc(x.error) : ''}</div></div><a class="btn sm" href="#/source/${enc(x.id)}">${x.status === 'waiting' ? 'Review' : 'Open'}</a></div>`).join('');
    return `${head('Business knowledge', 'Everything Hoola may tell people on a call. Nothing reaches a call until you approve it.')}
      ${sec('Sources', rows || '<p class="mut" style="margin:0">None yet. Add your price list, brochure, policies or website below - or tell the chat.</p>')}
      ${sec('Add knowledge', `<form id="tcKb" class="grid2" style="gap:14px">
        <label class="f"><span>From</span><select class="in" name="kind" id="tcKbKind"><option value="text">My words</option><option value="file">A file (PDF, Word, Excel, CSV)</option><option value="url">A page of my website</option><option value="sheet">A Google Sheet / CSV link</option><option value="api">My own API</option><option value="system">A system joined on the Systems page (SAP, Salesforce, an app)</option></select></label>
        ${field('name', 'Name', 'placeholder="Price list"')}
        <label class="f" style="grid-column:1/-1"><span>Words / address</span><textarea class="in" name="text" rows="3" placeholder="Paste text, or the https:// address"></textarea></label>
        ${field('api_key', 'API key (kept sealed, never shown again)', 'type="password" autocomplete="off"')}
        ${field('fields', 'Only these fields (comma separated)', 'placeholder="name, price"')}
        ${field('path', 'Where the list is in the answer (optional)', 'placeholder="items"')}
        ${field('system', 'System (for a joined system)', 'placeholder="sap"')}${field('target', 'What to read (for a joined system)', 'placeholder="A_Product"')}
        <label class="f"><span>Use</span><select class="in" name="mode"><option value="facts">Read in as facts</option><option value="live">Ask it live during a call (this caller's order / bill)</option></select></label>
        ${field('lookup', 'For a live lookup: what it answers', "placeholder=\"order status by the caller's number\"")}
        <div style="grid-column:1/-1;display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn sm" type="submit">Add</button><span class="mut" style="font-size:12.5px">A live lookup address carries {phone} (the caller's own number) or {value} (a number the caller says), e.g. https://api.example.com/orders?phone={phone}</span></div></form>`)}`;
  }
  async function pageSource(id) {
    const v = await api('GET', `/api/callcentre/knowledge/${enc(id)}`);
    ST.srcHash = v.pending_hash;
    const facts = (v.facts_preview || []).map(f => `<div class="row"><span class="pill">${esc(f.kind)}</span><div style="flex:1;min-width:0"><div class="t">${esc(f.title)}</div><div class="s">${esc(f.text)}</div></div></div>`).join('');
    return `<div><a class="btn soft sm" href="#/knowledge">← Knowledge</a></div>
      ${head(esc(v.name), esc(`${v.mode === 'live' ? 'Asked live during a call' : `${num(v.facts)} facts`} · ${v.status}`), '')}
      <div style="display:flex;gap:8px;flex-wrap:wrap">${v.status !== 'approved' ? '<button class="btn sm" type="button" data-src="yes">Approve: calls may use this</button>' : ''}<button class="btn soft sm" type="button" data-src="sync">Read it again</button><button class="btn soft sm" type="button" data-src="no">Switch off</button><button class="btn soft sm bad" type="button" data-src="del">Remove</button></div>
      ${v.error ? `<div class="card"><p style="margin:0;color:var(--badt)">${esc(v.error)}</p></div>` : ''}
      ${sec(v.mode === 'live' ? 'The lookup' : 'What Hoola will know', v.mode === 'live' ? `<p class="mut" style="margin:0">${esc((v.config || {}).url || (v.config || {}).target || '')} · only: ${esc(((v.config || {}).fields || []).join(', ') || 'every field')}</p>` : (facts || '<p class="mut" style="margin:0">No facts were found.</p>'))}`;
  }

  /* ---------------------------------------------------------------- Script & test */
  async function pageScript() {
    const r = await api('GET', '/api/callcentre/scripts');
    const run = r.running, drafts = (r.scripts || []).filter(x => x.status === 'draft' || x.status === 'waiting');
    const c = (run || {}).content || {};
    const steps = (c.steps || []).map((x, i) => `<div class="row"><span class="pill v">${i + 1}</span><div style="flex:1"><div class="t">${esc(x.name)}</div><div class="s">${esc(x.say)}</div></div></div>`).join('');
    const faqs = (c.faqs || []).slice(0, 30).map(f => `<div class="row"><div style="flex:1"><div class="t">${esc(f.q)}</div><div class="s">${esc(f.a)}</div></div></div>`).join('');
    const tl = ST.test.map(t => `<div class="${t.who === 'customer' ? 'me' : 'ai'}"><span class="who">${t.who === 'customer' ? 'You (as the customer)' : 'Hoola'}</span>${esc(t.text)}${t.flags && t.flags.length ? `<div style="color:var(--badt);font-size:12.5px;margin-top:4px">Not in your script: ${esc(t.flags.join(', '))}</div>` : ''}</div>`).join('');
    return `${head(run ? `Call script · v${esc(run.version)}` : 'No approved call script yet', 'Hoola speaks only what is here and in your approved knowledge. Change it in the chat; each change waits for your OK.')}
      ${drafts.length ? `<div class="card"><p style="margin:0">Draft v${esc(drafts[0].version)} waits for your approval in Hoola (the approval card). <a href="/console/">Open Hoola</a></p></div>` : ''}
      <div class="grid2"><div style="display:flex;flex-direction:column;gap:18px">
        ${sec('Call steps', steps || '<p class="mut" style="margin:0">No steps yet. Ask in the chat: “add steps: greet, ask the need, offer a site visit, book, close”.</p>')}
        ${sec('Answers in the script', faqs || '<p class="mut" style="margin:0">None yet.</p>')}
        ${c.never && c.never.length ? sec('Never says', c.never.map(x => `<span class="pill">${esc(x)}</span>`).join(' ')) : ''}</div>
      <div style="display:flex;flex-direction:column;gap:18px">${sec('Test chat · nobody is called', `<div class="tline" id="tcTestLine">${tl || '<p class="mut" style="margin:0">Type as a customer. Hoola answers from the script and knowledge, like on a real call.</p>'}</div>
        <form id="tcTest" style="display:flex;gap:8px"><input class="in" name="text" placeholder="Type as the customer" aria-label="Type as the customer" style="flex:1"><button class="btn sm" type="submit">Send</button><button class="btn soft sm" type="button" data-act="testclear">Clear</button></form>`)}</div></div>`;
  }

  /* ---------------------------------------------------------------- Incoming */
  async function pageIncoming() {
    const [st, m] = await Promise.all([api('GET', '/api/callcentre/settings'), api('GET', '/api/callcentre/messages')]);
    const rows = (m.messages || []).map(x => `<div class="row"><div style="flex:1;min-width:0"><div class="t">${esc(x.name || x.caller_masked)} ${pill(x.kind === 'callback' ? 'warn' : '', x.kind)}</div><div class="s">${esc(x.text)}${x.callback_at ? ` · asked for ${esc(x.callback_at)}` : ''}</div></div><button class="btn soft sm" type="button" data-msgdone="${esc(x.id)}">Done</button></div>`).join('');
    return `${head('Incoming calls', `Hoola answers ${esc(st.number || 'your number')} from your approved script and knowledge.`)}
      <div class="card" style="display:flex;align-items:center;gap:14px;justify-content:space-between;flex-wrap:wrap"><div><b>AI answers the line</b><div class="mut" style="font-size:13px">${esc(st.hours_text || '')} · after hours: ${esc(st.after_hours)}</div></div>
        <button class="btn ${st.line_on ? 'soft' : ''} sm" type="button" data-line="${st.line_on ? 'off' : 'on'}">${st.line_on ? 'Switch off' : 'Switch on'}</button></div>
      ${sec('Call-backs and messages', rows || '<p class="mut" style="margin:0">Nothing to call back.</p>')}`;
  }

  /* ---------------------------------------------------------------- Settings */
  async function pageSettings() {
    const [st, co] = await Promise.all([api('GET', '/api/callcentre/settings'), api('GET', '/api/callcentre/countries')]);
    const P = st.providers || {}, here = (st.providers_here || []).filter(k => P[k]);
    const opt = k => `<option value="${k}" ${st.provider === k ? 'selected' : ''}>${esc(P[k].name)}${P[k].calls_out === false ? ' (answers only)' : ''}</option>`;
    const rest = Object.keys(P).filter(k => !here.includes(k));
    const prov = (here.length ? `<optgroup label="Works in your country">${here.map(opt).join('')}</optgroup><optgroup label="Other companies">${rest.map(opt).join('')}</optgroup>` : Object.keys(P).map(opt).join(''));
    const keys = ((P[st.provider] || {}).keys || []).map(x => [x.name, x.label, x.multiline]);
    const keyField = ([k, n, ml]) => ml ? `<label class="f"><span>${esc(n)}</span><textarea class="in" name="${k}" rows="4" autocomplete="off" spellcheck="false" placeholder="-----BEGIN PRIVATE KEY-----"></textarea></label>` : field(k, n, 'type="password" autocomplete="off"');
    const conf = new Set(co.confirmed || []);
    const crow = (co.countries || []).map(c => `<tr><td><b>${esc(c.name)}</b> <span class="mut">${esc(c.dial)}</span></td><td>${esc(c.hours)}</td><td>${esc(c.cold_calls)}</td><td class="mut" style="font-size:12.5px">${esc(c.consent)}${c.dnc ? ` · check ${esc(c.dnc)}` : ''}</td>
      <td>${c.checked ? pill('ok', 'rules checked') : conf.has(c.code) ? `<button class="btn soft sm" type="button" data-country="${esc(c.code)}" data-yes="0">You confirmed · undo</button>` : `<button class="btn soft sm" type="button" data-country="${esc(c.code)}" data-yes="1">I checked this law</button>`}</td></tr>`).join('');
    return `${head('Settings', 'Your phone line, voice and the calling rules. Keys are typed here only and never shown again.')}
      <div class="grid2">
      ${sec('Phone line', `<form id="tcLine" style="display:flex;flex-direction:column;gap:12px">
        <label class="f"><span>Phone company</span><select class="in" name="provider">${prov}</select></label>
        ${field('number', 'Number Hoola calls from / answers', `value="${esc(st.number || '')}" placeholder="+91 20 4000 4410"`)}
        <label class="f"><span>Your country</span><select class="in" name="country">${(co.countries || []).map(c => `<option value="${c.code}" ${st.country === c.code ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></label>
        ${field('currency', 'Currency', `value="${esc(st.currency || '')}" maxlength="3"`)}
        ${field('rate', 'Your phone company’s rate per minute', `type="number" step="0.01" min="0" value="${esc(st.rate_per_min || 0)}"`)}
        <label style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="registered_line" ${st.registered_line ? 'checked' : ''}> I call from a registered telemarketing line (India 140 / 1600)</label>
        <div><button class="btn sm" type="submit">Save</button></div></form>`)}
      ${sec(`Keys · ${esc((st.providers || {})[st.provider]?.name || st.provider)}`, `<form id="tcKeys" style="display:flex;flex-direction:column;gap:12px">${(P[st.provider] || {}).where ? `<p class="mut" style="margin:0;font-size:13px">Works in: ${esc(P[st.provider].where)}${P[st.provider].machine_check ? ' · tells a person from an answering machine' : ''}</p>` : ''}${keys.map(keyField).join('')}
        <p class="mut" style="margin:0;font-size:13px">${st.creds_set ? 'Keys are saved. A box left empty keeps the saved key.' : 'No keys saved yet.'}</p><div><button class="btn sm" type="submit">Save keys</button></div></form>
        ${(st.setup || []).length ? `<div class="card" style="background:var(--soft)"><b>Set up at ${esc((P[st.provider] || {}).name || st.provider)}</b><ol style="margin:8px 0 0;padding-left:18px">${st.setup.map(x => `<li style="margin:4px 0">${esc(x)}</li>`).join('')}</ol>${st.urls ? `<p class="mut" style="font-size:12.5px;margin:8px 0 0">Answer URL: ${esc(st.urls.answer)}<br>Hangup URL: ${esc(st.urls.hangup)}</p>` : ''}</div>` : ''}`)}
      </div>
      ${sec('Countries Hoola may call', `<p class="mut" style="margin:0">Hours are the person's own local time. Only India's rules are checked by Hoola; for any other country, confirm you checked its law before Hoola calls there. Hoola cannot read national do-not-call registers: check your list against them.</p>
        <div style="overflow-x:auto"><table class="tb"><thead><tr><th>Country</th><th>Hours</th><th>People who never asked</th><th>Consent</th><th></th></tr></thead><tbody>${crow}</tbody></table></div>`)}`;
  }

  /* ---------------------------------------------------------------- actions */
  async function upload(file) {
    if (!ST.chat) throw new Error('The chat is not open yet.');
    const fd = new FormData(); fd.append('file', file, file.name || 'file');
    const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, {form: fd});
    return S(r.file_id || r.id);
  }
  function pickOne() {
    return new Promise(res => { const inp = $('#tcPickOne'); inp.value = ''; inp.onchange = () => res(inp.files[0] || null); inp.click(); });
  }
  async function onClick(e) {
    const b = e.target.closest('button,[data-act]'); if (!b) return;
    try {
      if (b.dataset.act === 'reload') return showPage();
      if (b.dataset.camp) {
        if (b.dataset.camp === 'start') {
          const c = ST.card || {};
          if (!confirm(`Start AI calls to ${c.callable} people? Hoola says it is an AI on every call, and stops each day at ${c.daily_cap} ${S((c.estimate || {}).currency)}.`)) return;
          await api('POST', `/api/callcentre/campaigns/${enc(ST.arg)}/start`, {hash: c.hash}); toast('Started. Calls go out inside each person’s calling hours.');
        } else { await api('POST', `/api/callcentre/campaigns/${enc(ST.arg)}/${b.dataset.camp}`); toast(b.dataset.camp === 'pause' ? 'Paused.' : 'Stopped.'); }
        return refreshDesk(true);
      }
      if (b.dataset.act === 'sheet') {
        const f = await pickOne(); if (!f) return;
        toast('Reading the sheet…'); const id = await upload(f);
        const r = await api('POST', `/api/callcentre/campaigns/${enc(ST.arg)}/people`, {file_id: id}); toast(r.say); return showPage(true);
      }
      if (b.dataset.act === 'leads') {
        const r0 = await api('GET', '/api/telecall/leads?stage=open');
        const ids = (r0.leads || []).map(x => x.id);
        if (!ids.length) return toast('You have no open Telecaller leads.', true);
        const r = await api('POST', `/api/callcentre/campaigns/${enc(ST.arg)}/people`, {lead_ids: ids}); toast(r.say); return showPage(true);
      }
      if (b.dataset.src) {
        const id = ST.arg;
        if (b.dataset.src === 'yes') { await api('POST', `/api/callcentre/knowledge/${enc(id)}/decide`, {yes: true, hash: ST.srcHash}); toast('Approved: calls may use it now.'); }
        else if (b.dataset.src === 'no') { await api('POST', `/api/callcentre/knowledge/${enc(id)}/decide`, {yes: false}); toast('Switched off.'); }
        else if (b.dataset.src === 'sync') { const r = await api('POST', `/api/callcentre/knowledge/${enc(id)}/sync`); toast(r.say || 'Read again.'); }
        else if (b.dataset.src === 'del') { if (!confirm('Remove this source and its facts?')) return; await api('DELETE', `/api/callcentre/knowledge/${enc(id)}`); location.hash = '#/knowledge'; return refreshDesk(false); }
        refreshDesk(false); return showPage(true);
      }
      if (b.dataset.act === 'testclear') { ST.test = []; return showPage(true); }
      if (b.dataset.line) { await api('POST', '/api/callcentre/line', {on: b.dataset.line === 'on'}); toast(b.dataset.line === 'on' ? 'Hoola answers the line now.' : 'The AI line is off.'); return showPage(true); }
      if (b.dataset.msgdone) { await api('POST', `/api/callcentre/messages/${enc(b.dataset.msgdone)}/done`, {}); return showPage(true); }
      if (b.dataset.country) {
        const yes = b.dataset.yes === '1';
        if (yes && !confirm('Confirm that you checked this country’s law on AI / automated calls and consent, and that your lists meet it?')) return;
        await api('POST', `/api/callcentre/countries/${enc(b.dataset.country)}/confirm`, {yes}); return showPage(true);
      }
    } catch (err) { toast(err.message, true); }
  }
  async function onSubmit(e) {
    const f = e.target; if (!(f instanceof HTMLFormElement)) return;
    e.preventDefault();
    const fd = new FormData(f), val = k => S(fd.get(k)).trim();
    try {
      if (f.id === 'tcNewList') {
        const r = await api('POST', '/api/callcentre/campaigns', {name: val('name'), goal: val('goal'), basis: val('basis'), purpose: val('purpose'),
          start_hour: val('start_hour'), end_hour: val('end_hour'), daily_cap: Number(val('daily_cap') || 0), at_once: Number(val('at_once') || 2),
          max_tries: Number(val('max_tries') || 3), voicemail: val('voicemail'), fields: val('fields').split(',').map(x => x.trim()).filter(Boolean)});
        toast('List made. Add people next.'); refreshDesk(false); location.hash = '#/list/' + r.id; return;
      }
      if (f.id === 'tcKb') {
        const kind = val('kind'), body = {kind, name: val('name'), mode: val('mode')};
        const t = val('text');
        if (kind === 'text') body.text = t;
        else if (['url', 'sheet', 'api'].includes(kind)) body.url = t;
        if (kind === 'file') { const file = await pickOne(); if (!file) return; toast('Reading the file…'); body.file_id = await upload(file); }
        if (kind === 'system') { body.system = val('system'); body.target = val('target'); }
        if (val('api_key')) body.api_key = val('api_key');
        if (val('fields')) body.fields = val('fields').split(',').map(x => x.trim()).filter(Boolean);
        if (val('path')) body.path = val('path');
        if (val('lookup')) body.lookup = val('lookup');
        const r = await api('POST', '/api/callcentre/knowledge', body); toast(r.say || 'Added.'); refreshDesk(false); location.hash = '#/source/' + r.id; return;
      }
      if (f.id === 'tcTest') {
        const text = val('text'); if (!text) return;
        ST.test.push({who: 'customer', text});
        const r = await api('POST', '/api/callcentre/test-chat', {turns: ST.test.map(({who, text}) => ({who, text}))});
        ST.test.push({who: 'hoola', text: r.reply, flags: r.flags}); return showPage(true);
      }
      if (f.id === 'tcLine') {
        await api('PUT', '/api/callcentre/settings', {provider: val('provider'), number: val('number'), country: val('country'), currency: val('currency'),
          rate_inr_per_min: Number(val('rate') || 0), registered_line: fd.get('registered_line') === 'on'});
        toast('Saved.'); refreshDesk(false); return showPage(true);
      }
      if (f.id === 'tcKeys') {
        const st = await api('GET', '/api/callcentre/settings'), body = {provider: st.provider};
        for (const [k, v] of fd.entries()) if (S(v).trim()) body[k] = S(v).trim();
        await api('PUT', '/api/callcentre/keys', body); toast('Keys saved and sealed.'); refreshDesk(false); return showPage(true);
      }
    } catch (err) { toast(err.message, true); }
  }

  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    const k = {list: 'lists', call: 'calls', source: 'knowledge'}[ST.tab] || ST.tab;
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
    try { const r = await api('GET', '/api/telecaller/chat'); ST.chat = r.id; }
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
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Working on your calls…';
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text, files, client_id: 'tc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
