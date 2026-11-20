/* v0.999.43 ACCOUNTS DESK - the GST & Accounts employee's own section (the SEO / Social desks' twin; owner: "NOW LETS MOVE
   TO NEXT EMPLOYEE" -> the design claude.ai/artifact/SEsautNMYTn6DTx6S1DZH8 -> "GO BUILD... USE CAN EVEN ATTACH THE FILES,
   PHOTOS, DOC IN CHAT").
   A thin top bar, then the Accounts chat (its own conversation, kind 'accounts': she asks, attaches a bill photo / PDF / a
   statement / a sheet with + or by dropping it, and it reads it into a draft) beside the desk's screens. The screens are the
   desk's own (bahi.js, the same routes and buttons), grouped into six pages: Today, Bills & register, GST returns, Bank &
   payments, Month-end & CA, Settings. The chat column is never redrawn when a page changes. Adding a bill to the register,
   sending to the GST portal, filing (with her OTP), recording TDS, closing a month and paying stay her taps here, never the
   chat's. Routes: #/<page>. */
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
    if (opts && opts.raw) { if (!r.ok) throw new Error(`The server refused the request (${r.status})`); return r; }
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
    back: '<path d="M15 18l-6-6 6-6"/>', acc: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);              // credits + the quality tier under the chat's typing box

  // the page -> the desk's own tabs (bahi.js) it shows
  const TABS = [['today', 'Today', ['overview']], ['bills', 'Bills & register', ['bl', 'register']],
    ['returns', 'GST returns', ['itc', 'g1', 'g3', 'ei']], ['bank', 'Bank & payments', ['bk', 'py']],
    ['close', 'Month-end & CA', ['me', 'ca']], ['settings', 'Settings', ['connection', 'rules', 'plan']]];
  const TRUST = {seekh: ['Learning', 'Reads, checks and prepares. Every step that changes your books or the GST portal waits for your tap.'],
                 saathi: ['Partner', 'Also checks bills and proposes bank matches on its own. Anything sent to the GST portal still waits for you.'],
                 bharosa: ['Trusted', 'Does more on its own. Filing (with your OTP), paying and locking a month always stay yours.']};
  const STARTERS = {
    today: ['What needs me today?', 'How much GST do I pay this month?', 'Which due date is closest?'],
    bills: ['Read the bill I attached', 'Which bills have problems?', 'Is this supplier\'s GSTIN real?'],
    returns: ['Explain my credits this month', 'Prepare my GSTR-1', 'Why does my 3B differ from the portal?'],
    bank: ['Who owes me the most?', 'Match my bank lines', 'Do I cut TDS on this bill?'],
    close: ['Can I close last month?', 'What is still open?', 'What dates are coming up?'],
    settings: ['How do I connect my GSTIN?', 'What does Partner trust mean?', 'Which rules are not checked yet?']};
  const MAXF = 20, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], bahi: null, timers: []};
  try { ST.side = localStorage.getItem('hoola.accounts.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.accounts.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/accounts/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.acc, '')}</div>
        <h1 class="sd-h">Your GST &amp; Accounts employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="adHire">Hire GST &amp; Accounts</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#adHire').onclick = async () => { try { await api('POST', '/api/employees/accounts/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    frame();
    readTab();
    mountDesk();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(refreshDesk, 60000));
  }
  function readTab() {
    const t = (location.hash.replace(/^#\/?/, '') || '').split('/')[0];
    ST.tab = TABS.some(x => x[0] === t) ? t : 'today';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.acc, '')}</div>
          <div style="min-width:0"><div class="sd-name">GST &amp; Accounts</div>
            <div class="sd-site" id="adSite"></div></div>
          <span id="adState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Accounts chat">
          <div class="sd-chathead"><div class="t"><b>Accounts chat</b><span>Attach bills, photos, statements · files only on your tap</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="ac-files" id="adFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="adPick" multiple hidden accept="image/*,application/pdf,.pdf,.csv,.xls,.xlsx,.txt,.doc,.docx,.sta,.mt940,.zip,.xml,.json">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Accounts desk" id="sdTabs"></nav>
          <div id="adNeeds"></div>
          <div id="app"><div id="adBahi"></div></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or attach a bill or statement…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#adPick').click()});
    $('#adPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => {      // a screenshot pasted into the box is a file too
      const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); }
    });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.accounts.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.accounts.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/accounts/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#adNeeds').addEventListener('click', e => {
      const g = e.target.closest('[data-go]'); if (g) { location.hash = '#/' + g.dataset.go; return; }
      const a = e.target.closest('[data-ask]'); if (a) setCtx(a.dataset.ask);
    });
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); starters(); });
    stateLine();
    paintTabs();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#adState'); if (!el) return;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !(d.gstins || []).length ? ['warn', 'Connect your GSTIN'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = $('#adSite'); if (s) s.textContent = (d.gstins || []).join(' · ') || 'No GSTIN connected yet';
  }
  function needsCount() { const d = ST.d || {}; return Number(d.bills_to_check || 0) + Number(d.bank_to_confirm || 0); }
  function paintTabs() {
    const d = ST.d || {};
    $('#sdTabs').innerHTML = TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === ST.tab}">${esc(n)}${
      k === 'bills' && d.bills_to_check ? `<span class="n">${esc(d.bills_to_check)}</span>` : k === 'bank' && d.bank_to_confirm ? `<span class="n">${esc(d.bank_to_confirm)}</span>` : ''}</button>`).join('');
  }

  /* ---------------------------------------------------------------- the desk (bahi.js, grouped) */
  function mountDesk() {
    if (!window.HoolaBahi) { $('#adBahi').innerHTML = '<div class="card"><p class="lead">The desk screens did not load. Refresh the page.</p></div>'; return; }
    ST.bahi = HoolaBahi({api, esc, toast, bare: true, ask: what => setCtx(what),
      open: v => { if (v === 'hire') location.href = '/console/?v=hire'; }, title: () => {}});
    ST.bahi.show(page()[2]);
    ST.bahi.open($('#adBahi')).then(() => { ST.bahi.show(page()[2]); });
    showPage();
    starters();
  }
  const page = () => TABS.find(x => x[0] === ST.tab) || TABS[0];
  function showPage() {
    if (ST.bahi) ST.bahi.show(page()[2]);
    paintNeeds();
    paintSettings();
    $('#sdDesk').scrollTop = 0;
  }
  function paintNeeds() {
    const box = $('#adNeeds'); if (!box) return;
    if (ST.tab !== 'today') { box.innerHTML = ''; return; }
    const d = ST.d || {}, rows = [];
    if (!(d.gstins || []).length) rows.push(['warn', 'Connect your GSTIN', 'Your portal username and the OTP the portal sends you. Your password is never asked.', 'settings', 'Connect']);
    if (d.bills_to_check) rows.push(['warn', `Check ${d.bills_to_check} bill${d.bills_to_check > 1 ? 's' : ''} Hoola read`, 'Read from what you sent. A bill joins the register only when you tap Add to register.', 'bills', 'Check']);
    if (d.bank_to_confirm) rows.push(['warn', `Confirm ${d.bank_to_confirm} bank line${d.bank_to_confirm > 1 ? 's' : ''} Hoola matched`, 'Nothing is linked until you confirm.', 'bank', 'Confirm']);
    for (const x of (d.dues || []).filter(x => Number(x.days_left) >= 0 && Number(x.days_left) <= 7).slice(0, 3))
      rows.push([Number(x.days_left) <= 3 ? 'bad' : 'warn', `${x.name || x.what} ${Number(x.days_left) === 0 ? 'is due today' : `is due in ${x.days_left} day${x.days_left === 1 ? '' : 's'}`}`, `${x.date}${x.unconfirmed ? ' · date not yet checked on a government site' : ''}. ${x.what}`, 'returns', 'Open']);
    box.innerHTML = `<section class="card ac-needs" style="margin-top:4px"><h2 style="margin:0;font-size:16px;font-weight:600">Needs you</h2>${rows.length ? rows.map(([c, t, s, go, l]) => `
      <div class="row"><span class="pill ${c}"><span class="dt"></span></span><div style="min-width:0;flex:1"><div class="t">${esc(t)}</div><div class="s">${esc(s)}</div></div>
        <button class="btn soft sm" type="button" data-ask="${esc(t)}">Ask</button><button class="btn sm" type="button" data-go="${esc(go)}">${esc(l)}</button></div>`).join('')
      : '<p class="mut" style="margin:0">Nothing needs you right now. Attach a bill or a statement in the chat any time.</p>'}</section>`;
  }
  function paintSettings() {
    let box = $('#adEmp');
    if (ST.tab !== 'settings') { box?.remove(); return; }
    if (!box) { box = document.createElement('section'); box.id = 'adEmp'; box.className = 'card'; box.style.marginTop = '4px'; $('#adNeeds').after(box); }
    const d = ST.d || {}, cur = Object.keys(TRUST).find(k => TRUST[k][0] === d.trust) || 'seekh';
    box.innerHTML = `<h2 style="margin:0 0 10px;font-size:16px;font-weight:600">How much it does on its own</h2>
      <div role="radiogroup" aria-label="Trust" style="display:flex;gap:6px;flex-wrap:wrap">${Object.entries(TRUST).map(([k, [n]]) =>
        `<button type="button" class="btn ${k === cur ? '' : 'soft'} sm" role="radio" aria-checked="${k === cur}" data-trust="${k}">${esc(n)}</button>`).join('')}</div>
      <p class="mut" style="margin:10px 0 0;font-size:13.5px">${esc(TRUST[cur][1])}</p>
      <div style="display:flex;gap:8px;margin-top:12px">${d.status === 'paused' ? '<button class="btn soft sm" type="button" data-emp="resume">Resume</button>' : '<button class="btn soft sm" type="button" data-emp="pause">Pause</button>'}
        <button class="btn soft sm bad" type="button" data-emp="leave">Let go</button></div>`;
    box.onclick = async e => {
      const t = e.target.closest('[data-trust]'), m = e.target.closest('[data-emp]');
      try {
        if (t) { await api('PUT', '/api/employees/accounts/settings', {trust: t.dataset.trust}); toast('Saved.'); await refreshDesk(); }
        if (m) {
          if (m.dataset.emp === 'leave' && !confirm('Let your GST & Accounts employee go? Its desk closes. Your register and records stay.')) return;
          await api('POST', `/api/employees/accounts/${m.dataset.emp}`);
          if (m.dataset.emp === 'leave') { location.href = '/console/?v=hire'; return; }
          toast(m.dataset.emp === 'pause' ? 'Paused.' : 'Working again.'); await refreshDesk();
        }
      } catch (err) { toast(err.message, true); }
    };
  }
  async function refreshDesk(all) {
    try { ST.d = await api('GET', '/api/accounts/desk'); } catch { return; }
    stateLine(); paintTabs(); paintNeeds(); paintSettings();
    if (all && ST.bahi) ST.bahi.refresh();
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
    const box = $('#adFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="ac-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/accounts/chat'); ST.chat = r.id; }
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
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Reading your books…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text),
      files: r.role === 'user' && Array.isArray(r.files) ? r.files : undefined}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) refreshDesk(true);      // a turn ended: what it read / changed shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { toast('Wait a moment - a file is still uploading.'); if (text && ST.bar) ST.bar.value = text; return; }
    if (!text && ready.length) text = ready.length > 1 ? 'Read these files' : 'Read this file';
    if (!text && ST.ctx) text = 'Explain this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'ac' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
    catch (e) { ok = false; toast(e.message, true); mine.remove(); if (ST.bar) ST.bar.value = text; ST.files = ready; paintFiles(); }
    ST.sending = false;
    if (ok) { ST.seq++; ST.res = {status: 'queued', needs_you: false, line: ''}; await loadMsgs(false); }
    paintThread();
  }
  async function stopTurn() {
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/stop`); toast('Stopping. A step that was running may stop halfway.'); }
    catch (e) { toast(e.message, true); }
  }

  start();
})();
