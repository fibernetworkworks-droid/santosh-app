/* FIRM PRACTICE DESK - the Firm Practice employee's own section, like Payroll, Tax, Cash & Treasury and Credit & Lending (owner: "NOW LETS
   WORK ON NEXT EMPLOYEE FIRM PRACTICE -- MAKE IT SAME PREMIUM AND ADVANCE AS WE DONE WITH OTHER SECTIONS"). A thin top bar, then the Firm
   chat (its own conversation, kind 'firm') beside the desk's pages: Today, Clients (+ one client), Drafts & reviews (+ one draft), Team,
   Settings - or, for a client of the firm, only their own page. The pages call /api/firm/do/<part>, which runs the F7 engine AS the
   person of the firm she is on this desk. Only the named signer signs; nobody reviews their own draft; a client sees only their own.
   Hoola files nothing, sends nothing to a client and pays nothing. Routes: #/<page>[/<arg>], #/draft/<id>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', firm: '<path d="M3 21h18M5 21V8l7-4 7 4v13M9 21v-6h6v6M9 11h.01M15 11h.01"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const STAFF_TABS = [['today', 'Today'], ['clients', 'Clients'], ['work', 'Drafts & reviews'], ['team', 'Team'], ['settings', 'Settings']];
  const CLIENT_TABS = [['today', 'Your page']];
  const STARTERS = {
    today: ['What needs me first?', 'Which clients are late with papers?', 'What is waiting for my signature?'],
    clients: ['Draft an engagement letter', 'Ask this client for their papers', 'Read these meeting notes'],
    work: ['What changed since it was sent back?', 'Summarise this draft', 'Who signs what this week?'],
    team: ['Who has the most drafts open?', 'Who looks after which client?', 'Add a reviewer'],
    client: ['What did my firm ask me for?', 'Explain the document they shared', 'When are my dates?'],
    settings: ['How does signing work here?', 'Who can see which client?', 'How do I link my team?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    cl: null, clFor: '', dr: null, drFor: '', audit: null, out: {}, wf: 'all', cq: '', newd: false, editing: false};
  try { ST.side = localStorage.getItem('hoola.firm.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.firm.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const ME = () => (ST.d && ST.d.me) || null;
  const isClient = () => !!(ME() && ME().role === 'client');
  const isPM = () => !!(ME() && ['partner', 'manager'].includes(ME().role));
  const isPartner = () => !!(ME() && ME().role === 'partner');
  const TABS_NOW = () => isClient() ? CLIENT_TABS : STAFF_TABS;
  let TABS = STAFF_TABS;
  const cur = () => (W() && W().currency) || 'USD';
  const can = () => !!ME() && !isClient();
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/firm/do/' + part, {workspace: W().id, ...(a || {})});
  const ROLE = r => ((ST.d && ST.d.roles) || {})[r] || cap(r);
  const KIND = k => ((ST.d && ST.d.kinds) || {})[k] || cap(S(k).replace(/_/g, ' '));
  const pname = id => { const p = ((ST.d && ST.d.people) || []).find(x => x.id === id); return p ? p.name : (id || '—'); };
  const initials = n => S(n).split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase() || '?';
  const STATE = {waiting: ['warn', 'Waiting for review'], sent_back: ['bad', 'Sent back'], approved: ['', 'Approved - to sign'], signed: ['ok', 'Signed']};
  const stTag = d => { const [c, l] = STATE[d.state] || ['', d.state]; return `<span class="cs-tag ${c}">${esc(l)}</span>${d.shared ? '<span class="cs-tag ok">Shared</span>' : ''}`; };
  const avatar = (n, role) => `<span class="fm-av ${esc(role || '')}" title="${esc(n)}">${esc(initials(n))}</span>`;
  const FF = {full_name: 'Full name', date_of_birth: 'Date of birth', dependants: 'Dependants', income: 'Income', spending: 'Spending', assets: 'Assets',
    debts: 'Debts', objectives: 'Objectives', time_horizon: 'Time horizon', attitude_to_risk: 'Attitude to risk', capacity_for_loss: 'Capacity for loss',
    knowledge_experience: 'Knowledge and experience', health: 'Health', existing_cover: 'Existing cover'};

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/firm/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    TABS = TABS_NOW();
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.firm, '')}</div>
        <h1 class="sd-h">Your Firm Practice employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="fmHire">Hire Firm Practice</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#fmHire').onclick = async () => { try { await api('POST', '/api/employees/firm_practice/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.firm, '')}</div>
          <div style="min-width:0"><div class="sd-name">Firm Practice</div><div class="sd-site" id="fmSite"></div></div>
          <span id="fmState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="fmBiz" aria-label="Business" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Firm chat">
          <div class="sd-chathead"><div class="t"><b>Firm chat</b><span>Ask about a client, a draft or your queue - or drop a client's papers here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="fmFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="fmPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Firm Practice desk" id="sdTabs"></nav>
          <div id="fmPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola prepares. The named people of the firm review and sign.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your clients…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#fmPick').click()});
    $('#fmPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.firm.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.firm.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/firm/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#fmBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/firm/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#fmPage').addEventListener('click', onPageClick);
    $('#fmPage').addEventListener('submit', onSubmit);
    $('#fmPage').addEventListener('input', onInput);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function clearCache() { ST.cl = null; ST.clFor = ''; ST.dr = null; ST.drFor = ''; ST.audit = null; }
  function stateLine() {
    const d = ST.d, el = $('#fmState'); if (!el) return;
    const w = W(), me = ME(), q = K().queue || {};
    const todo = (q.to_review || []).length + (q.to_sign || []).length + (q.sent_back_to_me || []).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your firm'] : !me ? ['warn', 'Not linked yet']
      : todo ? ['warn', `${todo} waiting on you`] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#fmSite').textContent = w ? `${w.name}${me ? ` · you are ${me.name}, ${ROLE(me.role).toLowerCase()}` : ''}` : 'No firm yet';
    const sel = $('#fmBiz');
    sel.innerHTML = (d.firms || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.firms || []).length < 2;
  }
  function paintTabs() {
    TABS = TABS_NOW();
    if (!TABS.some(x => x[0] === ST.tab)) ST.tab = 'today';
    const q = K().queue || {}, late = (K().overdue || []).length;
    const n = {work: (q.to_review || []).length + (q.to_sign || []).length + (q.sent_back_to_me || []).length || '', clients: late || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/firm/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#fmPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    if (!ME()) { box.innerHTML = pNotLinked(); starters(); return; }
    if (ST.tab === 'draft' || location.hash.startsWith('#/draft/')) { box.innerHTML = draftPage(ST.arg); starters(); if (!keep) $('#sdDesk').scrollTop = 0; return; }
    const fn = isClient() ? pPortal : ({today: pToday, clients: pClients, work: pWork, team: pTeam, settings: pSettings}[ST.tab] || pToday);
    const html = fn();
    if (typeof html === 'string') box.innerHTML = html;
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
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

  function pSetup() {
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.firm, '')}</div>
      <div><h1 class="sd-h">Set up your firm</h1><p class="lead">Your firm's clients each get their own books inside it. Your people prepare, review and sign - Hoola checks who may do what.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your firm</h2><div class="md-form">
        <div class="md-field"><label for="fmS1">Firm name</label><input class="in" id="fmS1" name="name" required maxlength="80" placeholder="Bright & Co"></div>
        <div class="md-field"><label for="fmS2">Your name (the first partner)</label><input class="in" id="fmS2" name="partner" required maxlength="80"></div>
        <div class="md-field"><label for="fmS3">Country (two letters)</label><input class="in" id="fmS3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="fmS4">Currency (three letters)</label><input class="in" id="fmS4" name="currency" required maxlength="3" placeholder="GBP"></div>
      </div><div class="md-acts"><span class="mut" style="font-size:13px">You can add partners, managers, preparers, reviewers and clients next.</span><button class="btn" type="submit">Set up the firm</button></div></form>`;
  }
  function pNotLinked() {
    const ppl = (ST.d && ST.d.people) || [];
    if (ST.d && ST.d.is_owner && ppl.length) return `<div><h1 class="sd-h">Who are you on this desk?</h1><p class="lead">Pick your person of the firm. Everything you do here is done as that person.</p></div>
      <div class="fm-people">${ppl.map(p => `<button class="fm-person" type="button" data-be="${esc(p.id)}">${avatar(p.name, p.role)}<b>${esc(p.name)}</b><span class="mut">${esc(ROLE(p.role))}</span></button>`).join('')}</div>`;
    return `<section class="card"><h1 class="sd-h">You are not linked yet</h1><p class="lead">A partner of ${esc(W().name)} links your Hoola login to your person of the firm on the Team page. Then this desk opens as you.</p></section>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), me = ME(), q = k.queue || {}, cl = k.clients || [], ds = k.drafts || [], db = k.dashboard;
    const tot = {papers: cl.reduce((a, c) => a + c.papers_outstanding, 0), review: cl.reduce((a, c) => a + c.drafts_waiting_review, 0),
      sign: cl.reduce((a, c) => a + c.drafts_to_sign, 0)};
    const lane = (title, list, cls, empt) => `<div class="fm-lane ${cls}"><div class="h"><b>${esc(title)}</b><span class="cs-tag">${esc(list.length)}</span></div>
      ${list.map(d => `<button class="fm-mini" type="button" data-go="draft/${esc(d.id)}"><b>${esc(d.title || KIND(d.kind))}</b><span class="mut">${esc(d.client)}${d.notes ? ' · ' + esc(d.notes) : ''}</span></button>`).join('') || `<div class="fm-empty">${esc(empt)}</div>`}</div>`;
    const pipe = ['waiting', 'sent_back', 'approved', 'signed'].map(s => [s, ds.filter(d => d.state === s).length]);
    const pmax = Math.max(1, ...pipe.map(x => x[1]));
    const lead = (q.to_sign || []).length ? `${q.to_sign.length} draft${q.to_sign.length > 1 ? 's wait' : ' waits'} for your signature.`
      : (q.to_review || []).length ? `${q.to_review.length} draft${q.to_review.length > 1 ? 's wait' : ' waits'} for your review.`
      : (q.sent_back_to_me || []).length ? 'A reviewer sent a draft back to you.' : cl.length ? 'Nothing is waiting on you.' : 'Add your first client to begin.';
    return `<div><h1 class="sd-h">${greet()}, ${esc(S(me.name).split(' ')[0])}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero fm-top"><div class="top">
        <div class="k"><div class="l">Clients</div><div class="v">${esc(cl.length)}</div><div class="s">${isPM() ? 'in the firm' : 'you look after'}</div></div>
        <div class="k${tot.papers ? ' low' : ''}"><div class="l">Papers outstanding</div><div class="v">${esc(tot.papers)}</div><div class="s">${(k.overdue || []).length ? `${esc(k.overdue.length)} request${k.overdue.length > 1 ? 's' : ''} past due` : 'none past due'}</div></div>
        <div class="k"><div class="l">Waiting for review</div><div class="v">${esc(tot.review)}</div><div class="s">across your clients</div></div>
        <div class="k"><div class="l">To sign</div><div class="v">${esc(tot.sign)}</div><div class="s">approved, not signed</div></div></div>
        ${ds.length ? `<div><div class="cr-sub">Where the drafts are</div><div class="fm-pipe">${pipe.map(([s, n]) => `<div class="${esc((STATE[s] || ['', ''])[0])}"><span class="l">${esc(STATE[s][1])}</span><span class="b"><i style="width:${(100 * n / pmax).toFixed(0)}%"></i></span><b>${esc(n)}</b></div>`).join('')}</div></div>` : ''}
      </section>
      <div class="fm-lanes">
        ${lane('To review', q.to_review || [], 'rev', ['partner', 'manager', 'reviewer'].includes(me.role) ? 'Nothing to review.' : 'Reviewers review; you prepare.')}
        ${lane('To sign', q.to_sign || [], 'sig', 'Nothing waits for your signature.')}
        ${lane('Sent back to you', q.sent_back_to_me || [], 'back', 'Nothing sent back.')}
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Clients</h2><div class="r"><button class="btn soft sm" type="button" data-go="clients">All clients</button></div></div>
          <div style="margin-top:6px">${cl.slice(0, 8).map(c => `<div class="cs-row" data-go="clients/${esc(c.id)}" style="cursor:pointer">${avatar(c.name, 'client')}<span style="flex:1;min-width:0"><b>${esc(c.name)}</b></span>
            ${c.papers_outstanding ? `<span class="cs-tag warn">${esc(c.papers_outstanding)} papers</span>` : ''}${c.drafts_waiting_review ? `<span class="cs-tag">${esc(c.drafts_waiting_review)} in review</span>` : ''}${c.drafts_to_sign ? `<span class="cs-tag ok">${esc(c.drafts_to_sign)} to sign</span>` : ''}</div>`).join('') || empty('No clients yet.')}</div></section>
      </div>
      ${db ? `<section class="card"><h2 class="md-h2">Drafts by preparer</h2>${byPreparer(db)}</section>` : ''}`;
  }
  function byPreparer(db) {
    const rows = Object.entries(db.by_preparer || {});
    if (!rows.length) return empty('No drafts yet.');
    const mx = Math.max(1, ...rows.map(([, v]) => Object.values(v).reduce((a, b) => a + b, 0)));
    return `<div class="fm-stack">${rows.map(([pid, v]) => { const t = Object.values(v).reduce((a, b) => a + b, 0);
      return `<div class="row">${avatar(pname(pid), (((ST.d.people || []).find(p => p.id === pid)) || {}).role)}<span class="n">${esc(pname(pid))}</span><span class="fm-bar" style="width:${(100 * t / mx).toFixed(1)}%">${['waiting', 'sent_back', 'approved', 'signed'].filter(s => v[s]).map(s => `<i class="${esc(STATE[s][0] || 'acc')}" style="flex:${v[s]}" title="${esc(STATE[s][1])}: ${esc(v[s])}"></i>`).join('')}</span><b>${esc(t)}</b></div>`; }).join('')}</div>
      <div class="cs-legend"><span><i class="w"></i>Waiting</span><span><i class="sb"></i>Sent back</span><span><i class="ap"></i>Approved</span><span><i class="sg"></i>Signed</span></div>`;
  }

  /* ---------------------------------------------------------------- clients */
  function pClients() {
    if (ST.arg) return clientPage(ST.arg);
    const cl = (K().clients || []).filter(c => !ST.cq || S(c.name).toLowerCase().includes(ST.cq.toLowerCase()));
    return `<div class="cs-head"><div><h1 class="sd-h">Clients</h1><p class="lead" style="margin-top:4px">Each client has their own books inside the firm. ${isPM() ? 'You see every client.' : 'You see the clients you look after.'}</p></div></div>
      ${isPM() ? `<section class="card"><h2 class="md-h2">New client</h2><form data-form="client" class="cr-grid" style="margin-top:0"><input class="in wide" name="name" placeholder="Client name" required maxlength="80" aria-label="Client name"><select class="in" name="size" aria-label="Kind"><option value="business">A business</option><option value="solo">A sole trader</option><option value="personal">A person</option></select><input class="in" name="currency" placeholder="Currency (${esc(cur())})" maxlength="3" aria-label="Currency"><button class="btn" type="submit">Add client</button></form></section>` : ''}
      ${(K().clients || []).length > 6 ? `<input class="in" type="search" id="fmCq" placeholder="Find a client" value="${esc(ST.cq)}" style="max-width:320px">` : ''}
      <div class="fm-cards">${cl.map(c => { const busy = c.papers_outstanding + c.drafts_waiting_review + c.drafts_to_sign;
        return `<button class="fm-card" type="button" data-go="clients/${esc(c.id)}"><div class="t">${avatar(c.name, 'client')}<div style="min-width:0"><b>${esc(c.name)}</b><div class="mut" style="font-size:12.5px">${esc((c.countries || []).join(', '))} · ${esc(c.currency)}</div></div></div>
          <div class="fm-stats"><div><span>${esc(c.papers_outstanding)}</span>papers out</div><div><span>${esc(c.drafts_waiting_review)}</span>in review</div><div><span>${esc(c.drafts_to_sign)}</span>to sign</div></div>
          <div class="mut" style="font-size:12.5px">${busy ? 'Work open' : 'All clear'}</div></button>`; }).join('') || `<section class="card">${empty('No clients yet.')}</section>`}</div>`;
  }
  function clientPage(cid) {
    if (ST.clFor !== cid) { ST.cl = null; ST.clFor = cid; ST.audit = null; }
    if (ST.cl === null) { lazy('cl', 'client', {client: cid}); return loading(); }
    if (ST.cl === false) return loading();
    const v = ST.cl;
    if (v.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(v.error)}</p><button class="btn soft sm" type="button" data-go="clients" style="margin-top:10px">Back</button></section>`;
    const c = v.client, today = new Date().toISOString().slice(0, 10);
    const reqs = v.requests.map(r => { const got = r.items.filter(i => i.sent).length, late = r.due && r.due < today && got < r.items.length;
      return `<div class="fm-req${late ? ' late' : ''}"><div class="h"><b>Asked ${esc(dmy(r.on))}</b><span class="mut">${r.due ? `due ${esc(dmy(r.due))}` : 'no date'}</span>${late ? '<span class="cs-tag bad">Late</span>' : got === r.items.length ? '<span class="cs-tag ok">All in</span>' : ''}<span class="cr-prog"><span style="width:${(100 * got / r.items.length).toFixed(0)}%"></span></span></div>
        ${r.items.map(i => `<div class="cs-row"><span class="cr-st ${i.sent ? 'received' : ''}">${i.sent ? '✓' : '!'}</span><span style="flex:1">${esc(i.item)}${i.sent_on ? `<span class="mut" style="font-size:12.5px"> · in ${esc(dmy(i.sent_on))}</span>` : ''}</span>${!i.sent ? `<button class="btn soft sm" type="button" data-provide="${esc(r.id)}" data-item="${esc(i.item)}">Mark received</button>` : ''}</div>`).join('')}</div>`; }).join('');
    const ds = v.drafts.map(d => `<button class="fm-row" type="button" data-go="draft/${esc(d.id)}"><span class="fm-kind">${esc(KIND(d.kind))}</span><b>${esc(d.title)}</b><span class="mut">by ${esc(pname(d.prepared_by))} · signs ${esc(pname(d.signer))}</span>${stTag(d)}</button>`).join('');
    const ff = v.factfind || {}, miss = v.factfind_missing || [];
    const ffPct = Math.round(100 * (Object.keys(FF).length - miss.length) / Object.keys(FF).length);
    const signers = v.signers || [];
    const sOpt = signers.map(s => `<option value="${esc(s.id)}">${esc(s.name)} (${esc(ROLE(s.role))})</option>`).join('');
    const out = ST.out[cid] || {};
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="clients">← Clients</button>
        <div class="fm-title">${avatar(c.name, 'client')}<div><h1 class="sd-h">${esc(c.name)}</h1><p class="lead" style="margin:2px 0 0">${esc((c.countries || []).join(', '))} · ${esc(c.currency)}</p></div></div></div>
        <div class="r"><button class="btn soft sm" type="button" data-ask="${esc('Client: ' + c.name)}">Ask about them</button></div></div>
      <div class="fm-team">${(v.team || []).map(t => `<span class="fm-chip">${avatar(t.name, t.role)}${esc(t.name)} <span class="mut">${esc(ROLE(t.role))}</span></span>`).join('')}${(v.client_people || []).map(t => `<span class="fm-chip">${avatar(t.name, 'client')}${esc(t.name)} <span class="mut">Client</span></span>`).join('')}</div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Papers asked for</h2></div><div style="margin-top:10px">${reqs || empty('Nothing asked for yet.')}</div>
          <form data-form="request" class="cs-form"><input class="in" name="items" placeholder="Bank statements, payroll summary, receipts" required maxlength="400" aria-label="Papers (comma separated)"><input class="in sm2" type="date" name="due" aria-label="Due"><button class="btn soft sm" type="submit">Ask for them</button></form>
          <p class="cs-note">The client sees this on their page. Hoola sends no message.</p></section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Drafts</h2><div class="r"><button class="btn sm" type="button" data-newd="1">New draft</button></div></div>
          ${ST.newd ? `<form data-form="draft" class="fm-draftform"><div class="cr-grid" style="margin-top:12px"><select class="in" name="kind" aria-label="Kind">${Object.entries((ST.d && ST.d.kinds) || {}).map(([k, l]) => `<option value="${esc(k)}">${esc(l)}</option>`).join('')}</select><input class="in" name="title" placeholder="Title" maxlength="120" aria-label="Title" required><select class="in" name="signer" aria-label="Who signs" required>${sOpt || '<option value="">No partner or manager looks after this client</option>'}</select></div>
            <textarea class="in" name="body" rows="7" required placeholder="The text of the draft (Markdown: # headings, - lists)" style="width:100%;margin-top:8px"></textarea>
            <div class="md-acts"><span class="mut" style="font-size:13px">It goes to a reviewer; the person you name signs it once approved.</span><button class="btn" type="submit">Send for review</button></div></form>` : ''}
          <div class="fm-rows" style="margin-top:10px">${ds || empty('No drafts for this client yet.')}</div></section>
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Engagement letter</h2>
          <form data-form="engagement" class="md-form"><div class="md-field wide"><label for="fmE1">What the firm will do (one per line)</label><textarea class="in" id="fmE1" name="services" rows="3" required placeholder="Year-end accounts&#10;Tax return"></textarea></div>
            <div class="md-field"><label for="fmE2">Fee</label><input class="in" id="fmE2" name="fee" placeholder="1,800 a year"></div><div class="md-field"><label for="fmE3">Period</label><input class="in" id="fmE3" name="period" placeholder="Year to 31 March 2027"></div>
            <div class="md-field"><label for="fmE4">Who signs</label><select class="in" id="fmE4" name="signer" required>${sOpt}</select></div><div class="md-field"><label for="fmE5">What the client gives us</label><input class="in" id="fmE5" name="client_duties" placeholder="Statements by the 10th"></div></form>
          <div class="md-acts"><span class="mut" style="font-size:13px">A draft that goes through review like any other.</span><button class="btn soft" type="button" data-engage="1">Draft the letter</button></div></section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Fact-find</h2><div class="r"><span class="fm-ring" style="--p:${ffPct}"><span>${esc(ffPct)}%</span></span></div></div>
          <form data-form="factfind" class="md-form" style="margin-top:10px">${Object.entries(FF).map(([key, l]) => `<div class="md-field"><label for="fmF_${key}">${esc(l)}</label><input class="in" id="fmF_${key}" name="${key}" value="${esc(ff[key] || '')}" maxlength="500"></div>`).join('')}</form>
          <div class="md-acts"><span class="mut" style="font-size:13px">${miss.length ? `${esc(miss.length)} still missing` : 'Complete'}</span><button class="btn soft" type="button" data-ff="1">Save the fact-find</button></div></section>
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Meeting notes</h2><form data-form="meeting"><textarea class="in" name="text" rows="5" required placeholder="Action: send payslips by 2026-12-05&#10;Decided: move to quarterly VAT" style="width:100%"></textarea><div class="md-acts"><span class="mut" style="font-size:13px">Lines starting Action: or Decided: are read.</span><button class="btn soft sm" type="submit">Read the notes</button></div></form>
          ${out.meeting ? `<div class="fm-out">${(out.meeting.actions || []).map(x => `<div class="cs-row"><span class="cr-chk"></span><span style="flex:1">${esc(x.action)}</span>${x.due ? `<span class="cs-tag warn">${esc(dmy(x.due))}</span>` : ''}</div>`).join('') || empty('No action lines found.')}
            ${(out.meeting.decisions || []).map(x => `<div class="cs-row"><span class="cr-st received">✓</span><span>${esc(x)}</span></div>`).join('')}<p class="cs-note">${esc(out.meeting.says)}</p></div>` : ''}</section>
        <section class="card"><h2 class="md-h2">Suitability report</h2><form data-form="suit"><div class="md-field"><label for="fmR1">The adviser's own recommendation</label><textarea class="in" id="fmR1" name="recommendation" rows="3" required placeholder="Hoola never makes the recommendation." style="width:100%"></textarea></div>
          <div class="md-acts"><select class="in sm" name="signer" aria-label="Who signs"><option value="">Just check it - no draft</option>${sOpt}</select><button class="btn soft sm" type="submit">Check the parts</button></div></form>
          ${out.suit ? `<div class="fm-out">${(out.suit.missing || []).length ? `<p class="cs-note cs-neg">Still to write: ${esc(out.suit.missing.join(', '))}</p>` : '<p class="cs-note cs-pos">Every required part is there.</p>'}${out.suit.draft ? `<button class="btn soft sm" type="button" data-go="draft/${esc(out.suit.draft.id)}">Open the draft</button>` : ''}</div>` : ''}</section>
      </div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">CFO pack</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Profit and loss, balance sheet and cash from ${esc(c.name)}'s own books - for the partner's review.</p><button class="btn soft sm" type="button" data-cfo="1">Make the pack</button>
          ${out.cfo ? (out.cfo.error ? `<p class="cs-note cs-neg">${esc(out.cfo.error)}</p>` : cfoView(out.cfo, c.currency)) : ''}</section>
        <section class="card"><h2 class="md-h2">Audit trail</h2>${ST.audit ? (ST.audit.error ? `<p class="cs-note cs-neg">${esc(ST.audit.error)}</p>` : `<div class="fm-trail">${(ST.audit.events || []).slice(0, 30).map(e => `<div><i></i><span class="mut nw">${esc(S(e.at).slice(0, 16).replace('T', ' '))}</span><span>${esc(e.what || e.kind)}</span><span class="mut">${esc(pname(S(e.actor).replace(/\s*<[^>]*>$/, '')))}</span></div>`).join('') || empty('Nothing yet.')}</div>${ST.audit.chain ? `<p class="cs-note">Chain check: ${esc(ST.audit.chain.ok ? 'every entry links to the one before' : 'a link is broken')}</p>` : ''}`)
          : ['partner', 'manager', 'reviewer'].includes(ME().role) ? '<button class="btn soft sm" type="button" data-audit="1">Show who did what</button>' : empty('Partners, managers and reviewers see the trail.')}</section>
      </div>`;
  }
  function cfoView(r, c) {
    const fm = v => { try { return Number(v).toLocaleString(undefined, {style: 'currency', currency: c, maximumFractionDigits: 0}); } catch { return v; } };
    const pl = r.profit_and_loss || {}, bs = r.balance_sheet || {}, cash = r.cash || {};
    const pick = (o, ks) => ks.map(k => o[k] !== undefined ? `<div><span class="mut">${esc(cap(k.replace(/_/g, ' ')))}</span><b>${esc(fm(o[k]))}</b></div>` : '').join('');
    return `<div class="fm-cfo">${pick(pl, ['income', 'expenses', 'profit', 'net_profit'])}${pick(bs, ['assets', 'liabilities', 'equity'])}${cash.lowest ? `<div><span class="mut">Lowest cash (13 weeks)</span><b>${esc(fm(cash.lowest.closing))}</b></div>` : ''}</div>
      ${cash.not_available ? `<p class="cs-note">Cash: ${esc(cash.not_available)}</p>` : ''}<p class="cs-note">${esc(r.says)}</p>`;
  }

  /* ---------------------------------------------------------------- drafts & reviews */
  function pWork() {
    const ds = K().drafts || [], q = ST.cq.trim().toLowerCase();
    const show = ds.filter(d => (ST.wf === 'all' || d.state === ST.wf) && (!q || `${d.title} ${d.client_name}`.toLowerCase().includes(q)));
    const cnt = s => ds.filter(d => s === 'all' || d.state === s).length;
    return `<div class="cs-head"><div><h1 class="sd-h">Drafts & reviews</h1><p class="lead" style="margin-top:4px">Preparer → reviewer → the named signer → the client's page. An approval holds only for the exact text it was given on.</p></div></div>
      <div class="fm-flow">${['waiting', 'sent_back', 'approved', 'signed'].map((s, i) => `<div class="${esc(STATE[s][0])}"><b>${esc(cnt(s))}</b><span>${esc(STATE[s][1])}</span></div>${i < 3 ? '<em>→</em>' : ''}`).join('')}</div>
      <div class="cr-filter"><div class="cs-seg" role="group" aria-label="Show">${[['all', 'All'], ['waiting', 'Waiting'], ['sent_back', 'Sent back'], ['approved', 'To sign'], ['signed', 'Signed']].map(([k, l]) => `<button type="button" data-wf="${k}" aria-pressed="${ST.wf === k}">${esc(l)} <span class="mut">${esc(cnt(k))}</span></button>`).join('')}</div><input class="in" type="search" id="fmWq" placeholder="Find a draft" value="${esc(ST.cq)}"></div>
      <section class="card tight"><div class="fm-rows">${show.map(d => `<button class="fm-row" type="button" data-go="draft/${esc(d.id)}"><span class="fm-kind">${esc(KIND(d.kind))}</span><b>${esc(d.title)}</b><span class="mut">${esc(d.client_name)} · by ${esc(pname(d.prepared_by))} · signs ${esc(pname(d.signer))}</span>${stTag(d)}</button>`).join('') || `<div style="padding:18px">${empty(ds.length ? 'No draft matches.' : 'No drafts yet - make one from a client\'s page.')}</div>`}</div></section>`;
  }
  function draftPage(id) {
    if (ST.drFor !== id) { ST.dr = null; ST.drFor = id; ST.editing = false; }
    if (ST.dr === null) { lazy('dr', 'draft', {draft: id}); return loading(); }
    if (ST.dr === false) return loading();
    const d = ST.dr;
    if (d.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(d.error)}</p><button class="btn soft sm" type="button" data-go="work" style="margin-top:10px">Back</button></section>`;
    const steps = [['Prepared', d.prepared_by_name, true], ['Reviewed', (d.reviews.slice(-1)[0] || {}).by_name, ['approved', 'signed'].includes(d.state)],
      ['Signed', d.signed ? d.signed.name : d.signer_name, !!d.signed], ['Shared', 'the client', d.shared]];
    const cn = d.can || {};
    const body = window.HoolaMD ? HoolaMD.render(S(d.body), false) : `<pre>${esc(d.body)}</pre>`;
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="${isClient() ? 'today' : 'work'}">← ${isClient() ? 'Your page' : 'Drafts'}</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(d.title)}</h1><p class="lead" style="margin-top:4px">${esc(KIND(d.kind))} for <a href="#/clients/${esc(d.client)}">${esc(d.client_name)}</a> · ${stTag(d)}</p></div>
        <div class="r"><button class="btn soft sm" type="button" data-dl="pdf">PDF</button><button class="btn soft sm" type="button" data-dl="md">Text</button>${isClient() ? '' : `<button class="btn soft sm" type="button" data-ask="${esc('Draft: ' + d.title + ' for ' + d.client_name)}">Ask about it</button>`}</div></div>
      <div class="fm-steps">${steps.map(([l, who, done], i) => `<div class="${done ? 'done' : ''}${!done && (i === 0 || steps[i - 1][2]) ? ' now' : ''}"><span class="dot">${done ? '✓' : i + 1}</span><b>${esc(l)}</b><span class="mut">${esc(who || '—')}</span></div>`).join('')}</div>
      ${d.state === 'sent_back' ? `<section class="md-alert">${svg(IC.info)}<div><div class="t">Sent back by ${esc((d.reviews.slice(-1)[0] || {}).by_name)}</div><div class="s">${esc((d.reviews.slice(-1)[0] || {}).notes)}</div></div></section>` : ''}
      <div class="fm-doc">
        <section class="card fm-paper">${ST.editing ? `<form data-form="edit"><textarea class="in" name="body" rows="18" style="width:100%">${esc(d.body)}</textarea><div class="md-acts"><span class="mut" style="font-size:13px">${d.state === 'approved' ? 'Changing an approved draft sends it back to review.' : 'Saving sends it to review.'}</span><span style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-editing="0">Cancel</button><button class="btn" type="submit">Save</button></span></div></form>` : `<div class="textmd">${body}</div>`}
          ${d.signed ? `<div class="fm-seal"><b>Signed by ${esc(d.signed.name)}</b><span>${esc(ROLE(d.signed.role))} · ${esc(dmy(d.signed.on))}</span><code>${esc(S(d.signed.hash).slice(0, 16))}</code></div>` : ''}</section>
        <aside class="fm-side">
          ${!isClient() ? `<section class="card"><h2 class="md-h2">What you can do</h2>
            ${cn.review ? `<form data-form="review"><textarea class="in" name="notes" rows="3" placeholder="Notes (needed to send it back)" style="width:100%"></textarea><div class="fm-acts"><button class="btn soft" type="submit" data-verdict="send_back">Send back</button><button class="btn" type="submit" data-verdict="approve">Approve this text</button></div></form>` : ''}
            ${cn.sign ? `<button class="btn fm-big" type="button" data-sign="1">Sign as ${esc(ME().name)}</button><p class="cs-note">Your signature records who, when and this exact text.</p>` : ''}
            ${cn.share ? `<button class="btn fm-big" type="button" data-share="1">Share to ${esc(d.client_name)}'s page</button>` : ''}
            ${cn.edit && !ST.editing ? `<button class="btn soft" type="button" data-editing="1" style="width:100%">Change the text</button>` : ''}
            ${d.why_not_review ? `<p class="cs-note">${esc(d.why_not_review)}</p>` : ''}
            ${!cn.review && !cn.sign && !cn.share && !cn.edit ? empty('Nothing for you to do on this draft.') : ''}</section>` : ''}
          <section class="card"><h2 class="md-h2">History</h2><div class="fm-trail">${d.reviews.map(r => `<div><i class="${r.verdict === 'approve' ? 'ok' : 'bad'}"></i><span class="mut nw">${esc(dmy(r.on))}</span><span><b>${esc(r.by_name)}</b> ${r.verdict === 'approve' ? 'approved' : 'sent it back'}${r.notes ? `: ${esc(r.notes)}` : ''}</span></div>`).join('') || empty('Not reviewed yet.')}</div>
            <p class="cs-note">Prepared by ${esc(d.prepared_by_name)} · signer ${esc(d.signer_name)} · text ${esc(S(d.hash).slice(0, 12))}</p></section>
        </aside></div>`;
  }

  /* ---------------------------------------------------------------- team */
  function pTeam() {
    const ppl = (ST.d && ST.d.people) || [], logins = K().logins || {}, cl = K().clients || [], db = K().dashboard;
    const order = ['partner', 'manager', 'reviewer', 'preparer', 'client'];
    const groups = order.map(r => [r, ppl.filter(p => p.role === r)]).filter(([, l]) => l.length);
    const cname = id => (cl.find(c => c.id === id) || {}).name || id;
    return `<div><h1 class="sd-h">Team</h1><p class="lead">Who is in the firm, which clients each person looks after, and whose login is whose.</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card">${groups.map(([r, list]) => `<div class="cr-sub" style="margin-top:6px">${esc(ROLE(r))}s</div>${list.map(p => `<div class="cs-row">${avatar(p.name, p.role)}<span style="flex:1;min-width:0"><b>${esc(p.name)}</b>${p.id === ME().id ? ' <span class="cs-tag">You</span>' : ''}<div class="mut" style="font-size:12.5px">${p.clients === 'all' ? 'Every client' : (p.clients || []).length ? esc((p.clients || []).map(cname).join(', ')) : 'No clients yet'}${logins[p.id] ? ` · login ${esc(logins[p.id])}` : ''}</div></span>
          ${isPartner() && p.id !== ME().id ? `<button class="btn soft sm" type="button" data-linkp="${esc(p.id)}">${logins[p.id] ? 'Change login' : 'Link login'}</button>` : ''}</div>`).join('')}`).join('')}
          ${ST.linking ? `<form data-form="link" class="cs-form"><input class="in" name="email" type="email" placeholder="Their Hoola account email" value="${esc(logins[ST.linking] || '')}" aria-label="Email"><button class="btn soft sm" type="submit">Link ${esc(pname(ST.linking))}</button></form><p class="cs-note">They also need to be on this firm's team in Books & Accounts, so they can open it.</p>` : ''}</section>
        <section class="card"><h2 class="md-h2">Add a person</h2>${isPartner() ? `<form data-form="person" class="md-form">
          <div class="md-field"><label for="fmP1">Name</label><input class="in" id="fmP1" name="name" required maxlength="80"></div>
          <div class="md-field"><label for="fmP2">Role</label><select class="in" id="fmP2" name="role">${order.map(r => `<option value="${r}">${esc(ROLE(r))}</option>`).join('')}</select></div>
          <div class="md-field wide"><label>Clients they look after</label><div class="cr-days">${cl.map(c => `<label><input type="checkbox" name="clients" value="${esc(c.id)}">${esc(c.name)}</label>`).join('') || '<span class="mut" style="font-size:13px">No clients yet</span>'}<label><input type="checkbox" name="all" value="1">Every client</label></div></div>
        </form><div class="md-acts"><span class="mut" style="font-size:13px">A client person belongs to exactly one client.</span><button class="btn" type="button" data-addp="1">Add</button></div>` : empty('Only a partner adds people.')}</section>
      </div>
      ${db ? `<section class="card"><h2 class="md-h2">Drafts by preparer</h2>${byPreparer(db)}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const ppl = (ST.d && ST.d.people) || [], w = W();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">${esc(w.name)} · ${esc((w.countries || []).join(', '))} · ${esc(w.currency)}</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Who you are on this desk</h2>
          ${ST.d.is_owner ? `<p class="mut" style="margin:0 0 12px;font-size:14px">The firm is yours, so you choose which person you act as. Everything you do is recorded as that person.</p><div class="fm-people">${ppl.map(p => `<button class="fm-person${p.id === ME().id ? ' on' : ''}" type="button" data-be="${esc(p.id)}">${avatar(p.name, p.role)}<b>${esc(p.name)}</b><span class="mut">${esc(ROLE(p.role))}</span></button>`).join('')}</div>`
            : `<p class="mut" style="margin:0;font-size:14px">You are ${esc(ME().name)} (${esc(ROLE(ME().role))}). A partner linked your login.</p>`}</section>
        <section class="card"><h2 class="md-h2">How the firm works here</h2>
          <div class="cs-row"><span class="cr-st received">1</span><span>A preparer makes a draft and names the partner or manager who signs.</span></div>
          <div class="cs-row"><span class="cr-st received">2</span><span>A reviewer approves it or sends it back. Nobody reviews their own draft.</span></div>
          <div class="cs-row"><span class="cr-st received">3</span><span>Only the named signer signs, and only the approved text. A change sends it back to review.</span></div>
          <div class="cs-row"><span class="cr-st received">4</span><span>A partner or manager shares the signed draft to the client's page. A client sees only their own.</span></div>
          <p class="cs-note">${esc((ST.d && ST.d.foot) || '')}</p></section>
      </div>`;
  }

  /* ---------------------------------------------------------------- a client's own page */
  function pPortal() {
    const p = K().portal || {}, today = new Date().toISOString().slice(0, 10);
    const open = (p.requests || []).flatMap(r => r.items.filter(i => !i.sent).map(i => ({...i, rid: r.id, due: r.due})));
    return `<div><h1 class="sd-h">${greet()}, ${esc(S(ME().name).split(' ')[0])}</h1><p class="lead">Your page with ${esc(W().name)}: what they asked you for, and the documents they shared with you.</p></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Papers your firm asked for</h2>${open.map(i => `<div class="cs-row"><span class="cr-st">!</span><span style="flex:1">${esc(i.item)}${i.due ? `<div class="mut${i.due < today ? ' cs-neg' : ''}" style="font-size:12.5px">by ${esc(dmy(i.due))}</div>` : ''}</span><button class="btn soft sm" type="button" data-provide="${esc(i.rid)}" data-item="${esc(i.item)}">I sent it</button></div>`).join('') || empty('Nothing asked for right now.')}
          <p class="cs-note">Send the papers to your firm the way you agreed, then mark them here.</p></section>
        <section class="card"><h2 class="md-h2">Shared with you</h2>${(p.shared_with_you || []).map(d => `<button class="fm-row" type="button" data-go="draft/${esc(d.id)}"><span class="fm-kind">${esc(KIND(d.kind))}</span><b>${esc(d.title)}</b>${d.signed ? `<span class="cs-tag ok">Signed by ${esc(d.signed.name)}</span>` : ''}</button>`).join('') || empty('Nothing shared yet.')}</section>
      </div>
      ${(p.dates || []).length ? `<section class="card"><h2 class="md-h2">Your dates</h2>${p.dates.map(x => `<div class="cs-row"><span class="mut nw" style="width:110px">${esc(dmy(x.due))}</span><span>${esc(x.what)}</span></div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- page actions */
  async function download(what) {
    try {
      const r = await fetch(`/api/firm/download?workspace=${enc(W().id)}&draft=${enc(ST.drFor)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `draft.${what}`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const formOf = sel => { const f = $(sel); if (!f) return null; if (!f.reportValidity()) return false; return new FormData(f); };
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    const go = t.closest('[data-go]'); if (go) { e.preventDefault(); location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const wf = t.closest('[data-wf]'); if (wf) { ST.wf = wf.dataset.wf; showPage(true); return; }
    if (t.closest('[data-newd]')) { ST.newd = !ST.newd; showPage(true); return; }
    const ed = t.closest('[data-editing]'); if (ed) { ST.editing = ed.dataset.editing === '1'; showPage(true); return; }
    const lp = t.closest('[data-linkp]'); if (lp) { ST.linking = lp.dataset.linkp; showPage(true); return; }
    try {
      const be = t.closest('[data-be]'); if (be) { await run('be', {person: be.dataset.be}); location.hash = '#/today'; await changed('You are now ' + pname(be.dataset.be) + '.'); return; }
      const pv = t.closest('[data-provide]'); if (pv) { await run('provide', {request: pv.dataset.provide, item: pv.dataset.item}); await changed('Marked as received.'); return; }
      if (t.closest('[data-sign]')) { await run('sign', {draft: ST.drFor}); await changed('Signed.'); return; }
      if (t.closest('[data-share]')) { await run('share', {draft: ST.drFor}); await changed('Shared to the client\'s page.'); return; }
      if (t.closest('[data-audit]')) { ST.audit = false; showPage(true); try { ST.audit = await run('audit', {client: ST.arg}); } catch (err) { ST.audit = {error: err.message}; } showPage(true); return; }
      if (t.closest('[data-cfo]')) { const cid = ST.arg; ST.out[cid] = {...(ST.out[cid] || {}), cfo: null}; try { ST.out[cid].cfo = await run('cfo_pack', {client: cid}); } catch (err) { ST.out[cid].cfo = {error: err.message}; } showPage(true); return; }
      if (t.closest('[data-engage]')) {
        const fd = formOf('form[data-form=engagement]'); if (!fd) return;
        const r = await run('engagement', {client: ST.arg, client_name: (ST.cl && ST.cl.client.name) || '', services: val(fd, 'services').split('\n').map(x => x.trim()).filter(Boolean),
          fee: val(fd, 'fee'), period: val(fd, 'period'), client_duties: val(fd, 'client_duties'), signer: val(fd, 'signer')});
        await changed('Engagement letter drafted - it goes to review.'); location.hash = '#/draft/' + r.draft.id; return;
      }
      if (t.closest('[data-ff]')) {
        const fd = new FormData($('form[data-form=factfind]')); const answers = {};
        for (const [k, v] of fd.entries()) if (S(v).trim()) answers[k] = S(v).trim();
        await run('factfind', {client: ST.arg, answers}); await changed('Fact-find saved.'); return;
      }
      if (t.closest('[data-addp]')) {
        const fd = formOf('form[data-form=person]'); if (!fd) return;
        const role = val(fd, 'role'), picked = fd.getAll('clients');
        const a = {name: val(fd, 'name'), role, clients: role === 'client' ? picked.slice(0, 1) : fd.get('all') ? 'all' : picked};
        await run('person_add', a); await changed('Added.'); return;
      }
    } catch (err) { toast(err.message, true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/firm/setup', {name: g('name'), partner: g('partner'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()}); location.hash = '#/today'; await changed('Your firm is set up.'); }
      else if (kind === 'client') { const r = await run('client_add', {name: g('name'), size: g('size'), currency: g('currency').toUpperCase() || undefined}); await changed('Client added.'); location.hash = '#/clients/' + r.client.id; }
      else if (kind === 'request') { await run('request', {client: ST.arg, items: g('items').split(/[,\n]/).map(x => x.trim()).filter(Boolean), due: g('due')}); await changed('Asked. It shows on their page.'); }
      else if (kind === 'draft') { const r = await run('new_draft', {client: ST.arg, kind: g('kind'), title: g('title'), body: g('body'), signer: g('signer')}); ST.newd = false; await changed('Sent for review.'); location.hash = '#/draft/' + r.draft.id; }
      else if (kind === 'meeting') { const cid = ST.arg; const r = await run('meeting', {client: cid, text: g('text')}); ST.out[cid] = {...(ST.out[cid] || {}), meeting: r}; showPage(true); }
      else if (kind === 'suit') { const cid = ST.arg; const a = {client: cid, recommendation: g('recommendation')}; if (g('signer')) a.signer = g('signer');
        const r = await run('suitability', a); ST.out[cid] = {...(ST.out[cid] || {}), suit: r}; if (r.draft) await changed('Suitability draft made - it goes to review.'); else showPage(true); }
      else if (kind === 'edit') { await run('edit', {draft: ST.drFor, body: g('body')}); ST.editing = false; await changed('Saved - it goes to review.'); }
      else if (kind === 'review') { const v = (btn && btn.dataset.verdict) || 'approve'; await run('review', {draft: ST.drFor, verdict: v, notes: g('notes'), hash: ST.dr && ST.dr.hash}); await changed(v === 'approve' ? 'Approved.' : 'Sent back.'); }
      else if (kind === 'link') { await run('link', {target: ST.linking, email: g('email')}); ST.linking = ''; await changed('Linked.'); }
    } catch (err) { toast(err.message, true); }
    finally { if (btn) btn.disabled = false; }
  }
  function onInput(e) {
    if (!['fmCq', 'fmWq'].includes(e.target.id)) return;
    ST.cq = e.target.value; const id = e.target.id, at = e.target.selectionStart;
    showPage(true); const q = $('#' + id); if (q) { q.focus(); try { q.setSelectionRange(at, at); } catch {} }
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
    const box = $('#fmFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/firm/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (isClient() ? STARTERS.client : (STARTERS[ST.tab] || STARTERS.today)).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
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
    if (!text && ready.length) text = ready.length > 1 ? 'Read these papers' : 'Read this file';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'fm' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


