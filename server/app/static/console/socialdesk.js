/* v0.999.38 SOCIAL DESK - the Social Media Manager's own section (the SEO desk's twin; owner: "NOW LETS MOVE TO NEXT AI
   EMPLOYEE SECTION" -> the design claude.ai/artifact/MkKK3knH9dzYJJWh7kyAfT -> "GO BUILD").
   A thin top bar, then the Social chat (its own conversation, kind 'social': she asks, tells it what to post, and it edits
   the drafts) beside the desk's screens: Today, Calendar, Inbox, Growth, Ads, Reports & settings - or the setup the first
   time. The chat column is never redrawn when a tab changes. Every number is the server's; where it has none the screen
   says so. Posting, sending a reply, approving and starting an ad are her taps here, never the chat's. Routes: #/<tab>. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const num = v => (v === null || v === undefined || v === '') ? '–' : (typeof v === 'number' ? v.toLocaleString('en-IN', {maximumFractionDigits: 1}) : esc(v));
  const when = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? esc(iso) : d.toLocaleString('en-IN', {weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const day = iso => { if (!iso) return ''; const d = new Date(iso); if (isNaN(d)) return ''; const m = Math.floor((Date.now() - d) / 86400000);
    return m < 1 ? 'Today' : m < 2 ? 'Yesterday' : m < 7 ? d.toLocaleDateString('en-IN', {weekday: 'short'}) : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
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
    back: '<path d="M15 18l-6-6 6-6"/>', social: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);              // credits + the quality tier under the chat's typing box

  const TABS = [['today', 'Today'], ['calendar', 'Calendar'], ['inbox', 'Inbox'], ['growth', 'Growth'], ['ads', 'Ads'], ['reports', 'Reports & settings']];
  const PLAT = {instagram: 'Instagram', facebook: 'Facebook Page', linkedin: 'LinkedIn', whatsapp: 'WhatsApp Business', youtube: 'YouTube'};
  const PST = {draft: ['warn', 'Draft'], approved: ['v', 'Approved'], skipped: ['', 'Skipped'], publishing: ['v', 'Posting…'],
               published: ['ok', 'Posted'], failed: ['bad', 'Not posted'], missed: ['', 'Missed']};
  const TRUST = {seekh: ['Learning', 'Plans, writes and drafts replies. Every post and every reply waits for your tap.'],
                 saathi: ['Partner', 'Approved plan posts go at their time (6 a day at most, never at night). Simple replies go on their own; complaints always wait.'],
                 bharosa: ['Trusted', 'More posts and replies a day on their own. Money, complaints and offers still wait for you.']};
  const BOX = [['needs', 'Needs you'], ['leads', 'Leads'], ['complaints', 'Complaints'], ['done', 'Done']];
  const CLS = {lead: ['ok', 'Lead'], question: ['v', 'Question'], praise: ['v', 'Praise'], complaint: ['warn', 'Complaint · always waits for you'],
               spam: ['bad', 'Spam'], abuse: ['bad', 'Abuse'], other: ['', 'Other']};
  const ADS = {draft: ['warn', 'Draft'], checked: ['ok', 'Checked'], created: ['v', 'Made, paused'], running: ['ok', 'Running'],
               paused: ['', 'Paused'], ended: ['', 'Finished'], failed: ['bad', 'Needs a fix']};
  const STARTERS = {
    today: ['What needs me today?', 'How did my posts do this week?', 'What should I post next?'],
    calendar: ['Make this week stronger', 'Add a festival post', 'Write the captions in Hindi too'],
    inbox: ['Draft replies to the leads', 'Which comments need me?', 'Make the replies friendlier'],
    growth: ['What are my competitors doing that works?', 'Which hook style works for me?', 'Which hashtags should I use?'],
    ads: ['Which post is worth a boost?', 'What did my ads bring me?', 'Plan a small ad for this month'],
    reports: ['Summarise this month in 3 lines', 'What did you do this week?', 'Should I move you to Partner?']};

  const ST = {tab: 'today', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, sig: '', drawn: false, seq: 0, ctx: '', side: 'left', folded: false, box: 'needs', inbox: null,
    meta: null, yt: null, adsErr: '', calView: 'list', setup: {}, timers: []};
  try { ST.side = localStorage.getItem('hoola.social.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.social.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/social/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.social, '')}</div>
        <h1 class="sd-h">Your Social Media Manager is not hired yet</h1>
        <p class="lead">Hire it from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div><a class="btn" href="/console/?v=hire">Go to AI Employees</a></div></div>`;
      return;
    }
    frame();
    readTab();
    paintDesk();
    await openChat();
    loadSide();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(refreshDesk, ST.d.state === 'first_run' ? 10000 : 60000));
  }
  function readTab() {
    const t = (location.hash.replace(/^#\/?/, '') || '').split('/')[0];
    ST.tab = TABS.some(x => x[0] === t) ? t : 'today';
  }
  const accs = () => (ST.d.accounts || []);
  const linked = () => accs().length > 0;

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.social, '')}</div>
          <div style="min-width:0"><div class="sd-name">Social Media Manager</div>
            <div class="sd-site" id="sdSite"></div></div>
          <span id="sdState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Social chat">
          <div class="sd-chathead"><div class="t"><b>Social chat</b><span>Edits drafts · posts only after your tap</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Social desk" id="sdTabs"></nav>
          <div id="sdPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or tell it what to post…', quality: true, onSend: t => send(t), onStop: stopTurn});
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.social.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.social.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/social/chat/new'); ST.chat = r.id; ST.rows = []; ST.sig = ''; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => { refreshDesk(); loadSide(); });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    window.addEventListener('hashchange', () => { readTab(); paintDesk(true); loadSide(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#sdState'); if (!el) return;
    const m = {first_run: ['v', 'First read running'], ready: ['ok', 'Working'], error: ['bad', 'Stopped'], new: ['warn', 'Starting']};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !d.onboarded ? ['v', 'Setting up'] : !linked() ? ['warn', 'Connect an account'] : (m[d.state] || ['', S(d.state)]);
    const tr = TRUST[d.trust] || TRUST.seekh;
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(tr[0])}</span>`;
    const p = d.profile || {}, s = $('#sdSite');
    if (s) s.textContent = [p.business, accs().map(a => PLAT[a.platform] || a.platform).join(', ')].filter(Boolean).join(' · ') || 'Not set up yet';
  }

  /* ---------------------------------------------------------------- data */
  async function refreshDesk() {
    try { ST.d = await api('GET', '/api/social/desk'); } catch { return; }
    stateLine(); paintDesk();
  }
  async function loadSide() {           // what one tab needs beyond the desk: the inbox list, the ads
    if (!ST.d.onboarded || !linked()) return;
    if (ST.tab === 'inbox') {
      try { ST.inbox = await api('GET', `/api/social/inbox?box=${ST.box}`); } catch (e) { ST.inbox = {items: [], error: e.message}; }
      if (ST.tab === 'inbox') paintDesk();
    }
    if (ST.tab === 'ads') {
      const [m, y] = await Promise.allSettled([api('GET', '/api/ads/metaads'), api('GET', '/api/social/ytads')]);
      ST.meta = m.status === 'fulfilled' ? m.value : {error: m.reason.message};
      ST.yt = y.status === 'fulfilled' ? y.value : {error: y.reason.message};
      if (ST.tab === 'ads') paintDesk();
    }
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/social/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    starters();
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
      ST.sig = rows.map(r => r.id).join(','); merge(rows);
      if (first && lastIsHers()) await ask();
      paintThread();
    } finally { ST.loading = false; }
  }
  function paintThread() {
    if (!ST.thread) return;
    const st = ST.res ? S(ST.res.status) : null;
    const working = ST.sending || (st === null ? lastIsHers() : st === 'working' || st === 'queued');
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Reading your posts and numbers…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text)}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) { refreshDesk(); loadSide(); }      // a turn ended: what it changed shows on the desk
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    if (!text && ST.ctx) text = 'Explain this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true});
    setCtx('');
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, client_id: 'so' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
    catch (e) { ok = false; toast(e.message, true); mine.remove(); if (ST.bar) ST.bar.value = text; }
    ST.sending = false;
    if (ok) { ST.seq++; ST.res = {status: 'queued', needs_you: false, line: ''}; await loadMsgs(false); }
    paintThread();
  }
  async function stopTurn() {
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/stop`); toast('Stopping. A step that was running may stop halfway.'); }
    catch (e) { toast(e.message, true); }
  }

  /* ---------------------------------------------------------------- the desk */
  function paintDesk(changed) {
    const tabs = $('#sdTabs'); if (!tabs) return;
    const d = ST.d, pl = d.pulse || {};
    const waitOk = (pl.waiting_ok || []).length + (d.calendar_status === 'draft' && (d.calendar || []).length ? 1 : 0);
    const needs = Number((d.inbox || {}).needs || 0);
    tabs.innerHTML = d.onboarded ? TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === ST.tab}">${esc(n)}${
      k === 'calendar' && waitOk ? `<span class="n">${waitOk}</span>` : k === 'inbox' && needs ? `<span class="n">${needs}</span>` : ''}</button>`).join('')
      : '<button type="button" role="tab" aria-selected="true">Setup</button>';
    const page = $('#sdPage');
    if (changed) {
      page.innerHTML = '<div style="display:flex;flex-direction:column;gap:14px;padding-top:4px"><div class="sk" style="height:30px;width:55%"></div><div class="sk" style="height:140px"></div><div class="sk" style="height:200px"></div></div>';
      starters();
      $('#sdDesk').scrollTop = 0;
      clearTimeout(paintDesk._t); paintDesk._t = setTimeout(() => paintDesk(false), 180);
      return;
    }
    const keep = keepInputs(page);
    try {
      const body = !d.onboarded ? setupPage() : !linked() && !['reports'].includes(ST.tab) ? connectPage()
        : ({today, calendar, inbox, growth, ads, reports}[ST.tab] || today)();
      page.innerHTML = `<div class="in-anim" style="display:flex;flex-direction:column;gap:22px">${body}</div>`;
    } catch (e) { page.innerHTML = `<div class="card"><p class="lead">This screen could not be drawn: ${esc(e.message)}</p></div>`; }
    restoreInputs(page, keep);
    wirePage(page);
  }
  function keepInputs(page) {          // a 60-second refresh never wipes what she is typing in a reply box
    const out = {};
    page.querySelectorAll('textarea[data-keep],input[data-keep]').forEach(x => { if (x.value !== x.defaultValue) out[x.dataset.keep] = x.value; });
    return out;
  }
  function restoreInputs(page, keep) {
    page.querySelectorAll('textarea[data-keep],input[data-keep]').forEach(x => { if (keep[x.dataset.keep] !== undefined) x.value = keep[x.dataset.keep]; });
  }
  const askBtn = (about, label = 'Ask') => `<button class="ask" type="button" data-ask="${esc(about)}">${esc(label)}</button>`;
  const tag = (c, n) => `<span class="pill ${c}">${esc(n)}</span>`;
  const kpiChange = k => k.change_pct == null ? '' : `<span class="c ${k.good ? 'up' : 'down'}">${k.change_pct >= 0 ? '+' : ''}${esc(k.change_pct)}%</span>`;
  const evDot = l => ({bad: 'bad', warn: 'warn', ok: 'ok'}[l] || '');
  const thumb = p => { const m = (p.media || [])[0];
    return m && m.kind !== 'video' && m.url ? `<img class="so-th" src="${esc(m.url)}" alt="" loading="lazy">` : `<span class="so-th so-ph">${esc((p.format || 'post').slice(0, 1).toUpperCase())}</span>`; };

  function needsList() {
    const d = ST.d, pl = d.pulse || {}, cal = d.calendar || [], out = [];
    if (!linked()) out.push({t: 'Connect Instagram or your Facebook Page', s: 'You log in on their own page. Hoola never sees your password.', b: '<a class="btn sm" href="#/reports">Connect</a>'});
    if (d.calendar_status === 'draft' && cal.length) out.push({t: `Approve your calendar (${cal.length} posts)`, s: 'Read the posts, ask about any in the chat, then approve. Nothing goes out before.', b: '<a class="btn sm" href="#/calendar">Review the calendar</a>'});
    for (const p of (pl.waiting_ok || []).slice(0, 3)) out.push({t: `OK today's post: ${p.hook || p.format || 'post'}`, s: `${when(p.slot)} · ${(p.platforms || []).map(x => PLAT[x] || x).join(' + ')}`, b: `<button class="btn sm" type="button" data-ok="${esc(p.id)}">OK to post</button>`});
    const n = Number((d.inbox || {}).needs || 0);
    if (n) out.push({t: `${n} comment${n > 1 ? 's' : ''} or DM${n > 1 ? 's' : ''} wait for you`, s: 'Replies are drafted from your facts. Nothing is sent without your tap.', b: '<a class="btn sm soft" href="#/inbox">Open the inbox</a>'});
    if ((pl.settings || {}).paused) out.push({t: 'Posting is paused', s: S(pl.settings.pause_reason) || 'Nothing goes out and no reply is sent on its own until you resume.', b: '<button class="btn sm" type="button" data-pause="0">Resume</button>'});
    if (d.state === 'first_run') out.push({t: 'The first read is running', s: 'It reads your last 50 posts and their numbers. This screen fills in by itself in a few minutes.', b: ''});
    return out;
  }

  function today() {
    const d = ST.d, k = d.kpis || [], ev = d.events || [], nd = needsList(), pl = d.pulse || {}, cal = d.calendar || [], b = d.baseline || {};
    const hi = new Date().getHours(), greet = hi < 12 ? 'Good morning' : hi < 17 ? 'Good afternoon' : 'Good evening';
    const now = Date.now(), soon = cal.filter(p => { const t = new Date(p.slot).getTime(); return !isNaN(t) && t > now - 3 * 86400000 && t < now + 7 * 86400000; }).slice(0, 8);
    const boosts = pl.boosts || [];
    return `<h1 class="sd-h" style="margin-top:6px">${greet}. ${nd.length ? `${nd.length} thing${nd.length > 1 ? 's' : ''} need${nd.length > 1 ? '' : 's'} you today.` : 'Nothing needs you today.'}</h1>
      <section class="card tight"><div class="hd"><h3>Needs you ${nd.length ? `<span class="pill v" style="margin-left:6px">${nd.length}</span>` : ''}</h3><span class="mut" style="font-size:13px">Nothing is posted or sent until you tap.</span></div>
        ${nd.length ? nd.map((n, i) => `<div class="need"><div class="l"><span class="no">${i + 1}</span><div><div style="font-size:14px;font-weight:500">${esc(n.t)}</div><div class="mut" style="font-size:13px;margin-top:2px">${esc(n.s)}</div></div></div>${n.b}</div>`).join('')
          : '<div class="empty">Nothing needs you today.</div>'}</section>
      <section><div class="hd"><h3>Your numbers</h3><span class="mut" style="font-size:13px">${b.date ? `Compared with ${esc(b.date)}` : ''}${b.posts_read ? ` · ${num(b.posts_read)} posts read` : ''}</span></div>
        ${k.length ? `<div class="grid">${k.map(x => `<div class="card kpi"><span class="n">${esc(x.name)}</span><span class="v">${num(x.now)}</span>
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="mut" style="font-size:12.5px">from ${num(x.baseline)} ${kpiChange(x)}</span>${askBtn(x.name)}</div></div>`).join('')}</div>`
          : '<div class="card"><p class="lead">Numbers appear after the first read of your posts.</p></div>'}</section>
      <div class="grid2">
        <section class="card tight"><div class="hd"><h3>This week</h3><a href="#/calendar" style="font-size:13px">Calendar →</a></div>
          ${soon.length ? soon.map(p => { const [c, n] = PST[p.status] || ['', p.status];
            return `<div class="row"><div style="display:flex;gap:12px;align-items:center;min-width:0">${thumb(p)}<div style="min-width:0"><div class="t">${esc(p.hook || p.format)}</div>
              <div class="s">${esc(p.format)} · ${(p.platforms || []).map(x => esc(PLAT[x] || x)).join(' + ')} · ${when(p.slot)}</div></div></div>
              <div class="r">${tag(c, p.plan_only && ST.d.trust === 'seekh' ? 'Needs your OK' : n)}${askBtn('post "' + (p.hook || p.format) + '"')}</div></div>`; }).join('')
            : '<div class="empty">No posts planned for this week.</div>'}</section>
        <div style="display:flex;flex-direction:column;gap:18px">
          <section class="card tight"><div class="hd"><h3>Inbox</h3><a href="#/inbox" style="font-size:13px">Open →</a></div>
            ${[['needs', 'Needs you', 'warn'], ['leads', 'New leads', 'ok'], ['complaints', 'Complaints', 'bad']].map(([x, n, c]) =>
              `<div class="row"><span class="t">${n}</span>${tag(c, num((d.inbox || {})[x] || 0))}</div>`).join('')}</section>
          <section class="card tight"><div class="hd"><h3>Worth a boost</h3></div>
            ${boosts.length ? boosts.slice(0, 3).map(x => `<div class="row"><div><div class="t"><a href="${esc(x.permalink)}" target="_blank" rel="noopener">${esc(x.fmt)} · ${esc(x.date)}</a></div>
                <div class="s">${esc(x.times)}x your normal interactions</div></div>${askBtn('boosting the ' + x.fmt + ' from ' + x.date)}</div>`).join('')
              + '<p class="mut" style="font-size:12.5px;margin:6px 0 10px">A boost spends money, so it is always your tap in Ads.</p>'
              : '<div class="empty">No post stands out yet.</div>'}</section>
        </div>
      </div>
      <section class="card"><h3 style="margin-bottom:6px">What your Social Media Manager did</h3>
        ${ev.length ? `<div class="feed">${ev.slice(0, 8).map(e => `<div><time>${esc(day(e.at))}</time><span><span class="dot ${evDot(e.level)}"></span>${esc(e.text)}</span></div>`).join('')}</div>` : '<div class="empty">Nothing yet.</div>'}</section>`;
  }

  function post(p) {
    const [c, n] = PST[p.status] || ['', p.status];
    const done = ['published', 'publishing'].includes(p.status);
    const needOk = p.plan_only && ST.d.trust === 'seekh';
    const res = p.result || {}, probs = p.problems || [];
    const hasYt = accs().some(a => a.platform === 'youtube' && a.status === 'ok'), hasLi = accs().some(a => a.platform === 'linkedin' && a.status === 'ok');
    return `<article class="card so-post" data-pid="${esc(p.id)}">
      <div class="so-pic">${(p.media || []).length ? (p.media[0].kind === 'video' ? '<span class="so-ph">Video</span>' : `<img src="${esc(p.media[0].url)}" alt="Picture for this post" loading="lazy">`) : `<span class="so-ph">${esc(p.format)}</span>`}</div>
      <div class="so-meta"><span class="mut num" style="font-size:12.5px">${when(p.slot)}</span>${needOk ? tag('warn', 'Needs your OK') : tag(c, n)}</div>
      <b class="so-hook">${esc(p.hook || p.format)}</b>
      <div class="mut" style="font-size:12.5px">${esc(p.format)} · ${(p.platforms || []).map(x => esc(PLAT[x] || x)).join(' + ')}${p.pillar ? ' · ' + esc(p.pillar) : ''}${p.occasion ? ' · ' + esc(p.occasion) : ''}</div>
      <details><summary>Caption and picture brief</summary>
        ${done ? `<p class="so-cap">${esc(p.caption)}</p>` : `<textarea class="in" rows="5" data-keep="cap-${esc(p.id)}" aria-label="Caption">${esc(p.caption)}</textarea>`}
        <p class="mut" style="font-size:12.5px">${(p.hashtags || []).map(esc).join(' ')}</p>
        ${p.visual ? `<p style="font-size:13px"><b>Picture / video:</b> ${esc(p.visual)}</p>` : ''}${p.cta ? `<p style="font-size:13px"><b>Ask:</b> ${esc(p.cta)}</p>` : ''}
        ${done ? '' : `<button class="btn soft sm" type="button" data-save="${esc(p.id)}">Save caption</button>`}</details>
      ${Object.entries(res).map(([pf, r]) => r.link ? `<p class="up" style="font-size:13px;margin:0">Posted on <a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(PLAT[pf] || pf)}</a>${r.note ? ` <span class="mut">${esc(r.note)}</span>` : ''}</p>`
          : r.error ? `<p class="down" style="font-size:13px;margin:0">${esc(PLAT[pf] || pf)}: ${esc(r.error)}</p>` : '').join('')}
      ${!done && probs.length ? `<p style="font-size:13px;color:var(--warn);margin:0">${probs.map(esc).join(' ')}</p>` : ''}
      ${done ? `<div class="so-acts">${askBtn('post "' + (p.hook || p.format) + '"')}</div>` : `<div class="so-acts">
        ${p.status === 'draft' || needOk ? `<button class="btn sm" type="button" data-ok="${esc(p.id)}">OK</button>` : ''}
        <button class="btn soft sm" type="button" data-pub="${esc(p.id)}"${probs.length ? ' disabled title="Fix the problems first"' : ''}>Publish now</button>
        <label class="btn soft sm">Picture<input type="file" accept="image/*,video/mp4,video/quicktime" data-up="${esc(p.id)}" hidden></label>
        <button class="btn soft sm" type="button" data-poster="${esc(p.id)}">Make poster</button>
        ${hasYt && ['reel', 'video'].includes(p.format) ? `<button class="btn soft sm" type="button" data-plat="youtube" data-id="${esc(p.id)}">${(p.platforms || []).includes('youtube') ? 'No YouTube' : '+ YouTube'}</button>` : ''}
        ${hasLi ? `<button class="btn soft sm" type="button" data-plat="linkedin" data-id="${esc(p.id)}">${(p.platforms || []).includes('linkedin') ? 'No LinkedIn' : '+ LinkedIn'}</button>` : ''}
        ${p.status !== 'skipped' ? `<button class="btn soft sm" type="button" data-skip="${esc(p.id)}">Skip</button>` : `<button class="btn soft sm" type="button" data-draft="${esc(p.id)}">Bring back</button>`}
        ${askBtn('post "' + (p.hook || p.format) + '"')}</div>`}</article>`;
  }
  function calendar() {
    const d = ST.d, cal = d.calendar || [], stg = d.strategy || {}, b = d.baseline || {};
    const live = cal.filter(p => p.status !== 'skipped'), skipped = cal.filter(p => p.status === 'skipped');
    const r = stg.rhythm || {};
    return `<div class="hd" style="padding:0"><div><h1 class="sd-h">Calendar</h1>
          <div class="mut" style="font-size:13.5px;margin-top:4px">${num(cal.length)} posts${r.feed_per_week ? ` · ${num(r.feed_per_week)} feed posts + ${num(r.stories_per_week)} Stories a week` : ''}${(stg.best_hours || b.best_hours || []).length ? ` · best hours ${(stg.best_hours || b.best_hours).map(h => esc(String(h).padStart(2, '0') + ':00')).join(', ')}` : ''}</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">${tag(d.calendar_status === 'approved' ? 'ok' : 'v', d.calendar_status === 'approved' ? 'Approved' : 'Draft')}
          <button class="btn soft sm" type="button" data-run="plan">Rewrite draft</button>
          ${d.calendar_status === 'draft' && cal.length ? '<button class="btn sm" type="button" data-act="approve">Approve calendar</button>' : ''}</div></div>
      ${(stg.pillars || []).length ? `<div style="display:flex;gap:6px;flex-wrap:wrap">${stg.pillars.map(p => `<span class="pill v" title="${esc(p.why || '')}">${esc(p.name)}</span>`).join('')}${stg.goal_metric ? `<span class="pill">Judged on: ${esc(stg.goal_metric)}</span>` : ''}</div>` : ''}
      ${live.length ? `<div class="so-grid">${live.map(post).join('')}</div>` : '<div class="card"><p class="lead">The calendar is written after the first read of your posts. Or ask in the chat: "plan my month".</p></div>'}
      ${skipped.length ? `<details class="card"><summary style="cursor:pointer;font-weight:500">Skipped (${skipped.length})</summary><div class="so-grid" style="margin-top:14px">${skipped.map(post).join('')}</div></details>` : ''}
      <p class="mut" style="font-size:13px;margin:0">Every post is checked before it can go: no prices or offers you have not told it, Instagram's 25-a-day limit, a picture where the format needs one. An edit after your OK needs your OK again. Publish now sends exactly what you see.</p>`;
  }

  function msg(m) {
    const [c, n] = CLS[m.cls] || ['', m.cls];
    const open = ['new', 'drafted', 'failed'].includes(m.status);
    const where = `${PLAT[m.platform] || m.platform} ${m.kind === 'dm' ? 'DM' : 'comment'}`;
    const doneLine = m.status === 'replied' ? `<p class="up" style="font-size:13px;margin:0">${m.auto ? 'Hoola replied' : 'You replied'}: ${esc(m.reply)}</p>`
      : m.status === 'hidden' ? `<p class="mut" style="font-size:13px;margin:0">${m.auto ? 'Hidden by Hoola' : 'Hidden'} (not deleted) <button class="btn soft sm" type="button" data-unhide="${esc(m.id)}">Unhide</button></p>`
      : `<p class="mut" style="font-size:13px;margin:0">No reply needed <button class="btn soft sm" type="button" data-back="${esc(m.id)}">Bring back</button></p>`;
    return `<article class="card so-msg" data-mid="${esc(m.id)}">
      <div class="hd" style="padding:0"><div><b style="font-size:14px">${esc(m.author || 'Someone')}</b> <span class="mut" style="font-size:12.5px">${esc(where)}${m.at ? ' · ' + when(m.at) : ''}${m.permalink ? ` · <a href="${esc(m.permalink)}" target="_blank" rel="noopener">post</a>` : ''}</span></div>${tag(c, n)}</div>
      ${m.post ? `<p class="mut" style="font-size:12.5px;margin:0">On: ${esc(m.post)}</p>` : ''}
      <p style="font-size:14.5px;line-height:1.5;margin:0">${esc(m.text)}</p>
      ${m.note ? `<p class="mut" style="font-size:13px;margin:0">${esc(m.note)}</p>` : ''}${m.error ? `<p class="down" style="font-size:13px;margin:0">${esc(m.error)}</p>` : ''}
      ${open ? (m.dm_closed ? '<p style="font-size:13px;color:var(--warn);margin:0">Meta lets a business answer a DM only within 24 hours. Reply from the Instagram / Facebook app yourself.</p>'
          : `<label class="mut" style="font-size:12.5px;display:flex;flex-direction:column;gap:6px">Drafted reply (from your facts)<textarea class="in" rows="2" data-keep="rep-${esc(m.id)}" data-reply="${esc(m.id)}">${esc(m.draft)}</textarea></label>
            ${m.needs_her ? '<p style="font-size:13px;color:var(--warn);margin:0">Check this one: it may need a fact only you know.</p>' : ''}`)
        + `<div class="so-acts">${m.dm_closed ? '' : `<button class="btn sm" type="button" data-send="${esc(m.id)}">Send reply</button>`}
            ${m.kind === 'comment' ? `<button class="btn soft sm" type="button" data-hide="${esc(m.id)}">Hide</button>` : ''}
            <button class="btn soft sm" type="button" data-ignore="${esc(m.id)}">No reply needed</button>${askBtn('the ' + where + ' from ' + (m.author || 'someone'))}</div>` : doneLine}</article>`;
  }
  function inbox() {
    const d = ST.d, cn = (ST.inbox && ST.inbox.counts) || d.inbox || {}, items = (ST.inbox && ST.inbox.items) || null;
    const auto = ST.d.trust === 'seekh' ? 'Nothing is sent without your tap.' : 'Simple thank-you replies go on their own (your trust setting); complaints and money questions always wait for you.';
    return `<div class="hd" style="padding:0"><h1 class="sd-h">Inbox</h1><button class="btn soft sm" type="button" data-run="inbox">Check now</button></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap" role="group" aria-label="Box">${BOX.map(([k, n]) => `<button class="chip" type="button" data-box="${k}" aria-pressed="${ST.box === k}">${esc(n)}${k !== 'done' ? ` · ${num(cn[k] || 0)}` : ''}</button>`).join('')}</div>
      ${items === null ? '<div class="sk" style="height:160px"></div>' : ST.inbox.error ? `<div class="card"><p class="lead">${esc(ST.inbox.error)}</p></div>`
        : items.length ? `<div class="so-list">${items.map(msg).join('')}</div>` : `<div class="card"><p class="lead">${ST.box === 'needs' ? 'Nothing waiting for you.' : 'Nothing here yet.'}</p></div>`}
      <p class="mut" style="font-size:13px;margin:0">Comments and DMs are read every 15 minutes. Replies are drafted only from the facts you gave. ${esc(auto)} Spam is hidden, never deleted.</p>`;
  }

  const UGS = {new: ['warn', 'New'], asked: ['v', 'Asked'], granted: ['ok', 'They said yes'], refused: ['', 'They said no'], reposted: ['ok', 'Draft made'], ignored: ['', 'Ignored']};
  function growth() {
    const g = ST.d.growth || {}, w = g.watch || {hashtags: [], competitors: []}, ab = g.ab || {}, lk = g.link || {};
    const comp = c => { const l = c.last || {}, p = c.prev || {}; const df = l.followers != null && p.followers != null ? l.followers - p.followers : null;
      return `<tr><td>@${esc(l.username || c.name)}${c.error ? `<div class="down" style="font-size:12.5px">${esc(c.error)}</div>` : ''}</td><td class="num">${l.followers != null ? num(l.followers) + (df ? ` <span class="mut">(${df > 0 ? '+' : ''}${num(df)})</span>` : '') : '–'}</td>
        <td class="num">${l.posts_7d != null ? num(l.posts_7d) : '–'}</td><td class="num">${l.avg_eng != null ? num(l.avg_eng) : '–'}</td><td>${esc(((l.formats || [])[0] || {}).fmt || '–')}</td><td style="text-align:right">${askBtn('competitor @' + (l.username || c.name))}</td></tr>`; };
    return `<div class="hd" style="padding:0"><h1 class="sd-h">Growth</h1><button class="btn soft sm" type="button" data-run="growth">Check now</button></div>
      <p class="mut" style="font-size:13px;margin:0">${lk.ok ? `Listening through your Page's Instagram @${esc(lk.username)}.` : esc(lk.reason || '')} Public business numbers only, never scraping.</p>
      <section class="card tight"><div class="hd"><h3>Competitors</h3></div>
        ${w.competitors.length ? `<div class="scroll"><table class="tb"><thead><tr><th>Account</th><th>Followers</th><th>Posts this week</th><th>Interactions a post</th><th>Best format</th><th></th></tr></thead><tbody>${w.competitors.map(comp).join('')}</tbody></table></div>`
          : '<div class="empty">Add up to 5 Instagram business accounts you compete with.</div>'}</section>
      <section class="card"><h3 style="margin-bottom:10px">What to follow</h3>
        <div class="form"><label>Competitors (usernames, comma separated)<input class="in" id="soComp" data-keep="comp" value="${esc(w.competitors.map(c => c.name).join(', '))}" placeholder="smiledentalakola, citydental"></label>
          <label>Hashtags (comma separated)<input class="in" id="soTags" data-keep="tags" value="${esc(w.hashtags.map(h => h.name).join(', '))}" placeholder="akoladentist, dentalcare"></label></div>
        <div style="margin-top:12px"><button class="btn soft sm" type="button" data-act="watch">Save</button></div></section>
      <div class="grid2">
        <section class="card tight"><div class="hd"><h3>Hashtags of your niche</h3></div>
          ${w.hashtags.map(h => { const l = h.last || {}; return `<div class="row"><div><div class="t">#${esc(h.name)}</div><div class="s">${l.posts ? `${num(l.avg_eng)} interactions a top post · best ${esc(((l.formats || [])[0] || {}).fmt || '–')}` : esc(h.error || 'Read on Monday')}</div></div>${askBtn('hashtag #' + h.name)}</div>`; }).join('') || '<div class="empty">Add up to 5 hashtags.</div>'}</section>
        <section class="card tight"><div class="hd"><h3>Hook styles you tried</h3></div>
          ${(ab.styles || []).length ? ab.styles.map(r => `<div class="row"><span class="t">${esc(r.style)}</span><span class="num" style="font-size:14px">${num(r.avg_eng)} <span class="mut">· ${num(r.posts)} posts</span></span></div>`).join('') : '<div class="empty">After a few more posts.</div>'}
          ${ab.note ? `<p class="mut" style="font-size:12.5px;margin:6px 0 10px">${esc(ab.note)}</p>` : ''}</section>
      </div>
      <div class="grid2">
        <section class="card tight"><div class="hd"><h3>Customers tagging you</h3></div>
          ${(g.ugc || []).map(u => { const [c, n] = UGS[u.status] || ['', u.status];
            return `<div class="row"><div style="min-width:0"><div class="t">@${esc(u.username)} <a class="mut" href="${esc(u.permalink)}" target="_blank" rel="noopener" style="font-size:12.5px">open</a></div><div class="s">${esc((u.caption || '').slice(0, 120))}</div>${u.proof ? `<div class="s up">Their yes: ${esc(u.proof)}</div>` : ''}</div>
              <div class="r">${tag(c, n)}${['new', 'asked', 'refused'].includes(u.status) ? `<button class="btn soft sm" type="button" data-ug="ask" data-id="${esc(u.id)}">${u.status === 'new' ? 'Ask to repost' : 'Ask again'}</button>` : ''}
                ${['new', 'asked'].includes(u.status) ? `<button class="btn soft sm" type="button" data-ug="permission" data-id="${esc(u.id)}">They said yes</button>` : ''}
                ${u.status === 'granted' ? `<button class="btn sm" type="button" data-ug="repost" data-id="${esc(u.id)}">Make a credited draft</button>` : ''}</div></div>`; }).join('')
            || '<div class="empty">When customers tag you, their posts appear here. A repost is a credited draft only after they say yes.</div>'}</section>
        <section class="card"><h3 style="margin-bottom:10px">Check a creator before a collab</h3>
          <div class="form"><label>Instagram username<input class="in" id="soCrUser" data-keep="cru" placeholder="foodie_akola"></label>
            <label>Collab caption (optional, checked for #ad)<input class="in" id="soCrCap" data-keep="crc"></label></div>
          <div style="margin-top:12px"><button class="btn soft sm" type="button" data-act="creator">Check</button></div><div id="soCrOut"></div></section>
      </div>`;
  }

  function ads() {
    const m = ST.meta, y = ST.yt;
    const full = '<a class="ask" href="/console/?v=socialdesk&full=1">Edit the ad details</a>';
    const metaCard = () => {
      if (!m) return '<div class="sk" style="height:120px"></div>';
      if (m.error) return `<p class="lead">${esc(m.error)}</p>`;
      if (!m.configured) return '<div class="empty">Not set up on the server yet (Meta app keys).</div>';
      const a = m.account;
      if (!a) return '<button class="btn sm" type="button" data-act="metaconn">Connect with Facebook</button>';
      const cur = a.currency || '';
      const acct = a.via === 'login' && !a.account ? `<p class="mut" style="font-size:13px">Which ad account pays for your ads?</p><div class="so-acts">${(a.accounts || []).map(c => `<button class="btn soft sm" type="button" data-maacct="${esc(c.id)}"${c.active ? '' : ' disabled'}>${esc(c.name || c.id)} (${esc(c.currency || '')})</button>`).join('') || '<span class="mut">No ad account found in this Facebook login.</span>'}</div>` : '';
      const drafts = (m.drafts || []).map(dr => { const [c, n] = ADS[dr.status] || ['', dr.status];
        return `<div class="row"><div style="min-width:0"><div class="t">${esc(dr.goal_label)}</div><div class="s">${num(dr.daily)} ${esc(cur)} a day x ${num(dr.days)} days = ${num(dr.total)} · ${esc((dr.cities || []).join(', ') || 'all India')}${dr.stop_on ? ' · until ' + esc(dr.stop_on) : ''}</div>
          ${(dr.problems || []).length ? `<div class="s" style="color:var(--warn)">${dr.problems.map(esc).join(' ')}</div>` : ''}${dr.error ? `<div class="s down">${esc(dr.error)}</div>` : ''}</div>
          <div class="r">${tag(c, n)}${['draft', 'failed'].includes(dr.status) ? `<button class="btn soft sm" type="button" data-ma="check" data-id="${esc(dr.id)}">Check with Meta</button>` : ''}
            ${['draft', 'checked', 'failed'].includes(dr.status) ? `<button class="btn soft sm" type="button" data-ma="create" data-id="${esc(dr.id)}"${(dr.problems || []).length ? ' disabled' : ''}>Create (paused)</button>` : ''}
            ${['created', 'paused'].includes(dr.status) ? `<button class="btn sm" type="button" data-ma="start" data-id="${esc(dr.id)}" data-total="${esc(dr.total)} ${esc(cur)}" data-days="${esc(dr.days)}">Start</button>` : ''}
            ${dr.status === 'running' ? `<button class="btn soft sm" type="button" data-ma="pause" data-id="${esc(dr.id)}">Pause</button>` : ''}</div></div>`; }).join('');
      return `<p class="mut" style="font-size:13px;margin:0 0 6px">${esc(a.name || 'No ad account chosen')}${a.account ? ' · ' + esc(a.account) : ''}</p>${acct}
        ${a.account ? `<div class="so-acts">${Object.entries(m.goals || {}).filter(([k]) => k !== 'boost').map(([k, t]) => `<button class="btn soft sm" type="button" data-manew="${esc(k)}">${esc(t)}</button>`).join('')}${askBtn('boosting a post', 'Boost a post')}</div>` : ''}
        ${drafts || '<div class="empty">No Meta ads yet.</div>'}`;
    };
    const ytCard = () => {
      if (!y) return '<div class="sk" style="height:120px"></div>';
      if (y.error) return `<p class="lead">${esc(y.error)}</p>`;
      if (!y.configured) return '<div class="empty">Not set up on the server yet (Google sign-in).</div>';
      const a = y.account;
      if (!a) return '<button class="btn sm" type="button" data-act="ytconn">Connect Google Ads</button>';
      const pick = !a.customer_id ? `<p class="mut" style="font-size:13px">Which ad account runs your Google ads?</p><div class="so-acts">${(a.customers || []).filter(c => !c.manager).map(c => `<button class="btn soft sm" type="button" data-ytcust="${esc(c.id)}">${esc(c.name || c.id)} (${esc(c.currency || '')})</button>`).join('') || '<span class="mut">No ad account found in this Google login.</span>'}</div>` : '';
      const drafts = (y.drafts || []).map(dr => { const [c, n] = ADS[dr.status] || ['', dr.status];
        return `<div class="row"><div style="min-width:0"><div class="t">${esc(dr.title || dr.kind_label || 'New ad')}</div><div class="s">${esc(dr.kind_label || '')} · ${num(dr.daily)} ${esc(a.currency || '')} a day x ${num(dr.days)} days = ${num(dr.total)}${dr.stop_on ? ' · until ' + esc(dr.stop_on) : ''}</div>
          ${(dr.problems || []).length ? `<div class="s" style="color:var(--warn)">${dr.problems.map(esc).join(' ')}</div>` : ''}${dr.error ? `<div class="s down">${esc(dr.error)}</div>` : ''}</div>
          <div class="r">${tag(c, n)}${['draft', 'failed'].includes(dr.status) ? `<button class="btn soft sm" type="button" data-yt="check" data-id="${esc(dr.id)}">Check with Google</button>` : ''}
            ${['draft', 'checked', 'failed'].includes(dr.status) ? `<button class="btn soft sm" type="button" data-yt="create" data-id="${esc(dr.id)}"${(dr.problems || []).length ? ' disabled' : ''}>Create (paused)</button>` : ''}
            ${['created', 'paused'].includes(dr.status) ? `<button class="btn sm" type="button" data-yt="start" data-id="${esc(dr.id)}" data-total="${esc(dr.total)}">Start</button>` : ''}
            ${dr.status === 'running' ? `<button class="btn soft sm" type="button" data-yt="pause" data-id="${esc(dr.id)}">Pause</button>` : ''}</div></div>`; }).join('');
      return `<p class="mut" style="font-size:13px;margin:0 0 6px">Google account ${esc(a.email || '')}${a.customer_id ? ' · ad account ' + esc(a.customer_id) : ''}${a.error ? ' · ' + esc(a.error) : ''}</p>${pick}
        ${a.customer_id ? `<div class="so-acts"><button class="btn soft sm" type="button" data-ytnew="search">New Search ad</button><button class="btn soft sm" type="button" data-ytnew="pmax">New Performance Max</button>
          <button class="btn soft sm" type="button" data-ytnew="youtube"${(y.videos || []).length ? '' : ' disabled title="Connect YouTube first"'}>New YouTube ad</button></div>` : ''}
        ${drafts || '<div class="empty">No Google ads yet.</div>'}`;
    };
    return `<h1 class="sd-h">Ads</h1>
      <div class="card" style="border-color:var(--warns);background:var(--warns)"><b>Ads spend your money, so every start is your tap</b>
        <div class="mut" style="font-size:13.5px;margin-top:4px">It drafts and checks with Meta / Google for free. Create puts the ad in your account paused. Only Start runs it, with an end date set.</div></div>
      <section class="card"><div class="hd" style="padding-top:0"><h3>Facebook &amp; Instagram ads</h3>${full}</div>${metaCard()}</section>
      <section class="card"><div class="hd" style="padding-top:0"><h3>Google &amp; YouTube ads</h3>${full}</div>${ytCard()}</section>`;
  }

  function reports() {
    const d = ST.d, pl = d.pulse || {}, pst = pl.settings || {}, q = pst.quiet || [23, 7];
    const hasYt = accs().some(a => a.platform === 'youtube' && a.status === 'ok');
    return `<h1 class="sd-h">Reports &amp; settings</h1>
      <div class="grid2">
        <section class="card"><h3 style="margin-bottom:10px">How much may it do on its own?</h3>
          ${Object.entries(TRUST).map(([k, [t, s]]) => `<label class="choice${k === 'bharosa' ? ' off' : ''}" style="margin-top:8px"><input type="radio" name="trust" value="${k}"${(d.trust || 'seekh') === k ? ' checked' : ''}${k === 'bharosa' ? ' disabled' : ''}>
            <span><b style="font-size:14px">${esc(t)}</b><span class="mut" style="display:block;font-size:13px;margin-top:2px">${esc(s)}${k === 'bharosa' ? ' Opens after a month as Partner.' : ''}</span></span></label>`).join('')}</section>
        <section class="card tight"><div class="hd"><h3>Posting controls</h3></div>
          <div class="row"><span class="t">Posting</span>${pst.paused ? tag('warn', 'Paused') : tag('ok', 'On')}</div>
          <div class="row"><span class="t">Plan posts today</span><span class="num" style="font-size:14px">${d.trust === 'seekh' ? 'each waits for your OK' : `${num(pl.auto_today || 0)} of ${num(pl.post_cap || 0)}`}</span></div>
          <div class="row"><span class="t">Quiet hours (nothing on its own)</span><span style="display:flex;gap:6px;align-items:center"><input class="in" type="number" min="0" max="23" id="soQ0" data-keep="q0" value="${esc(q[0])}" style="width:64px" aria-label="From hour"> to <input class="in" type="number" min="0" max="23" id="soQ1" data-keep="q1" value="${esc(q[1])}" style="width:64px" aria-label="To hour"><button class="btn soft sm" type="button" data-act="quiet">Save</button></span></div>
          ${hasYt ? `<div class="row"><span class="t">YouTube: are your videos made for kids?</span><select class="in" id="soKids" style="width:auto"><option value="" ${pst.yt_kids == null ? 'selected' : ''} disabled>Choose</option><option value="no" ${pst.yt_kids === false ? 'selected' : ''}>No</option><option value="yes" ${pst.yt_kids === true ? 'selected' : ''}>Yes</option></select></div>` : ''}
          <div class="so-acts" style="padding:10px 0">${pst.paused ? '<button class="btn sm" type="button" data-pause="0">Resume posting</button>' : '<button class="btn soft sm" type="button" data-pause="1">Pause all posting</button>'}
            <button class="btn soft sm bad" type="button" data-act="stop">Emergency stop</button></div>
          <p class="mut" style="font-size:12.5px;margin:0 0 10px">Pause also stops automatic replies. Emergency stop sends every queued post back to draft.</p></section>
      </div>
      <div class="grid2">
        <section class="card tight"><div class="hd"><h3>Reports</h3></div>
          <div class="row"><div><div class="t">This month's report (PDF)</div><div class="s">Reach, enquiries, best posts, what changes next month. It arrives in your Hoola chat.</div></div><button class="btn soft sm" type="button" data-run="monthly">Make it</button></div>
          <div class="row"><div><div class="t">Fresh numbers</div><div class="s">Read every day by itself.</div></div><button class="btn soft sm" type="button" data-run="daily">Refresh now</button></div>
          ${((pl.best_times || {}).slots || []).length ? `<div class="row"><div><div class="t">Best times for you</div><div class="s">${pl.best_times.slots.slice(0, 3).map(x => `${esc(x.day)} ${esc(x.band)} (${esc(x.lift)}x)`).join(' · ')} · certainty ${esc(pl.best_times.sure)}</div></div></div>` : ''}</section>
        <section class="card tight"><div class="hd"><h3>Runs 24/7</h3></div>
          ${(d.schedule || []).map(x => `<div class="row"><span class="t">${esc(x.job)}</span><span class="mut" style="font-size:13px">${esc(x.every)} · last ${when(x.last)}</span></div>`).join('') || '<div class="empty">Starts after setup.</div>'}</section>
      </div>
      <section class="card tight"><div class="hd"><h3>Accounts</h3><span class="mut" style="font-size:12.5px">You log in on each app's own page. Hoola never sees your password.</span></div>${accountRows()}</section>
      <section class="card tight"><div class="hd"><h3>The employee</h3></div>
        <div class="row"><div><div class="t">${d.status === 'paused' ? 'Paused' : 'Working'}</div><div class="s">Pausing stops every job, post and reply. Your posts and numbers stay.</div></div>
          <div class="r">${d.status === 'paused' ? '<button class="btn sm" type="button" data-emp="resume">Resume</button>' : '<button class="btn soft sm" type="button" data-emp="pause">Pause</button>'}<button class="btn soft sm bad" type="button" data-emp="leave">Let go</button></div></div></section>`;
  }
  function accountRows() {
    const d = ST.d, list = accs();
    const rows = list.map(a => `<div class="row"><div><div class="t">${esc(PLAT[a.platform] || a.platform)} · ${esc(a.handle || a.name)}</div>
        <div class="s">${a.platform === 'whatsapp' ? 'Messages reach your Business inbox' : a.platform === 'linkedin' ? 'Your profile' : a.followers != null ? num(a.followers) + (a.platform === 'youtube' ? ' subscribers' : ' followers') : ''}
        ${a.status !== 'ok' ? `<span class="down"> · ${esc(a.status === 'expired' ? 'Connection ended: connect again' : a.error || a.status)}</span>` : ''}
        ${a.status === 'ok' && (a.can_post === false || a.can_reply === false) ? '<span style="color:var(--warn)"> · Reconnect to allow posting and replies</span>' : ''}</div></div>
        <button class="btn soft sm" type="button" data-off="${esc(a.id)}">Disconnect</button></div>`).join('');
    const con = ['instagram', 'facebook', 'whatsapp', 'linkedin', 'youtube'].map(p => (d.connect || {})[p]
      ? `<button class="btn ${list.some(a => a.platform === p) ? 'soft' : ''} sm" type="button" data-con="${p}">${list.some(a => a.platform === p) ? 'Reconnect' : 'Connect'} ${esc(PLAT[p])}</button>`
      : `<button class="btn soft sm" type="button" disabled title="Not set up on the server yet">${esc(PLAT[p])}: not set up yet</button>`).join('');
    return `${rows}<div class="so-acts" style="padding:12px 0">${con}</div>
      <p class="mut" style="font-size:12.5px;margin:0 0 10px">Instagram must be a Business or Creator account (a free switch in Instagram settings). LinkedIn posts go to your own profile.</p>`;
  }
  function connectPage() {
    return `<h1 class="sd-h">Connect your accounts</h1>
      <p class="lead">Connect Instagram or your Facebook Page. Your Social Media Manager then reads your last 50 posts, finds what works and plans your month.</p>
      <section class="card tight">${accountRows()}</section>`;
  }
  function setupPage() {
    const p = ST.d.profile || {}, v = ST.setup;
    const val = k => esc(v[k] !== undefined ? v[k] : (k === 'languages' ? (p.languages || ['English']).join(', ') : p[k] || ''));
    return `<div class="steps"><span class="on"></span><span></span></div>
      <h1 class="sd-h">Tell it about your business</h1>
      <p class="lead">A few questions. Then connect Instagram or your Facebook Page, and it reads your posts and plans your month.</p>
      <section class="card"><div class="form">
        <label>Business name<input class="in" data-s="business" value="${val('business')}" placeholder="Sharma Dental Clinic"></label>
        <label>City<input class="in" data-s="city" value="${val('city')}" placeholder="Akola"></label>
        <label class="wide">What you sell<input class="in" data-s="sells" value="${val('sells')}" placeholder="Root canal, implants, braces"></label>
        <label class="wide">Who are your customers?<input class="in" data-s="customers" value="${val('customers')}" placeholder="Families and office workers nearby"></label>
        <label class="wide">What do you want from social media?<input class="in" data-s="goal" value="${val('goal')}" placeholder="More WhatsApp enquiries for implants"></label>
        <label class="wide">Languages for posts (comma separated)<input class="in" data-s="languages" value="${val('languages')}"></label>
        <label class="wide">Facts for replies: prices, timings, address, WhatsApp (only these are ever quoted)<textarea class="in" rows="3" data-s="facts" placeholder="Cleaning Rs 800. Open 10 am - 8 pm, Sunday closed.">${val('facts')}</textarea></label>
      </div></section>
      <section class="card"><h3 style="margin-bottom:8px">How much may it do on its own?</h3>
        ${['seekh', 'saathi'].map(k => `<label class="choice" style="margin-top:8px"><input type="radio" name="strust" value="${k}"${(v.trust || ST.d.trust || 'seekh') === k ? ' checked' : ''}><span><b style="font-size:14px">${esc(TRUST[k][0])}</b><span class="mut" style="display:block;font-size:13px;margin-top:2px">${esc(TRUST[k][1])}</span></span></label>`).join('')}</section>
      <div><button class="btn" type="button" data-act="onboard">Save and connect accounts</button></div>`;
  }

  /* ---------------------------------------------------------------- the buttons */
  async function go(btn, fn, done, desk, side) {
    if (btn) btn.disabled = true;
    try { const r = await fn(); toast((r && r.say) || done || 'Done.'); if (desk) await refreshDesk(); if (side) await loadSide(); }
    catch (e) { toast(e.message, true); }
    if (btn && btn.isConnected) btn.disabled = false;
  }
  const postOf = id => (ST.d.calendar || []).find(x => x.id === id) || {};
  function wirePage(page) {
    page.onclick = async e => {
      const b = e.target.closest('button,a[data-ask]'); if (!b) return;
      const ds = b.dataset;
      if (ds.ask) return setCtx(ds.ask);
      if (ds.box) { ST.box = ds.box; ST.inbox = null; paintDesk(); return loadSide(); }
      if (ds.ok) return go(b, () => api('POST', `/api/social/posts/${enc(ds.ok)}`, {status: 'approved'}), 'OK. It goes out at its time.', true);
      if (ds.skip) return go(b, () => api('POST', `/api/social/posts/${enc(ds.skip)}`, {status: 'skipped'}), 'Skipped.', true);
      if (ds.draft) return go(b, () => api('POST', `/api/social/posts/${enc(ds.draft)}`, {status: 'draft'}), 'Back in the calendar as a draft.', true);
      if (ds.save) { const ta = b.closest('.so-post').querySelector('textarea');
        return go(b, () => api('POST', `/api/social/posts/${enc(ds.save)}`, {caption: ta.value}), 'Saved. An edited post needs your OK again.', true); }
      if (ds.pub) { const p = postOf(ds.pub), where = (p.platforms || []).map(x => PLAT[x] || x).join(' and ');
        if (!confirm(`Post this now on ${where}? It goes out exactly as shown, to everyone who follows you.`)) return;
        return go(b, () => api('POST', `/api/social/posts/${enc(ds.pub)}/publish`, {}), 'Posting… the link appears here in a minute.', true); }
      if (ds.poster) { b.textContent = 'Making…'; return go(b, () => api('POST', `/api/social/posts/${enc(ds.poster)}/poster`, {}), 'Poster made from your Brand kit.', true); }
      if (ds.plat) { const p = postOf(ds.id), on = (p.platforms || []).includes(ds.plat);
        const pl = on ? p.platforms.filter(x => x !== ds.plat) : [...(p.platforms || []), ds.plat];
        return go(b, () => api('POST', `/api/social/posts/${enc(ds.id)}`, {platforms: pl}), `${on ? 'Removed' : 'Added'}. Approve the post again.`, true); }
      if (ds.send) { const ta = page.querySelector(`textarea[data-reply="${CSS.escape(ds.send)}"]`), text = S(ta && ta.value).trim();
        if (!text) return toast('Write a reply first.', true);
        return go(b, () => api('POST', `/api/social/inbox/${enc(ds.send)}/reply`, {text}), 'Reply sent.', true, true); }
      if (ds.hide) return go(b, () => api('POST', `/api/social/inbox/${enc(ds.hide)}/hide`, {hidden: true}), 'Hidden. Nothing deleted.', true, true);
      if (ds.unhide) return go(b, () => api('POST', `/api/social/inbox/${enc(ds.unhide)}/hide`, {hidden: false}), 'Shown again.', true, true);
      if (ds.ignore) return go(b, () => api('POST', `/api/social/inbox/${enc(ds.ignore)}`, {status: 'ignored'}), 'Moved to Done.', true, true);
      if (ds.back) return go(b, () => api('POST', `/api/social/inbox/${enc(ds.back)}`, {status: 'drafted'}), 'Back in Needs you.', true, true);
      if (ds.run) return go(b, () => api('POST', `/api/social/run/${ds.run}`, {}), {plan: 'Rewriting the draft. Approved posts stay.', inbox: 'Checking comments and DMs now.',
        monthly: 'Making the PDF - it arrives in your Hoola chat.', growth: 'Reading tags, hashtags and competitors now.', daily: 'Reading your latest numbers.'}[ds.run], false);
      if (ds.pause !== undefined) { const on = ds.pause === '1';
        return go(b, () => api('POST', '/api/social/settings', {paused: on}), on ? 'Paused. Nothing goes out until you resume.' : 'Resumed.', true); }
      if (ds.con) return go(b, async () => { const r = await api('GET', `/api/social/connect/${ds.con}`); window.open(r.url, '_blank', 'noopener'); }, 'Log in on the page that opened, then come back here.');
      if (ds.off) { if (!confirm('Disconnect this account? Hoola deletes its token and the posts it read.')) return;
        return go(b, () => api('POST', `/api/social/accounts/${enc(ds.off)}/disconnect`, {}), 'Disconnected.', true); }
      if (ds.ug) { let body = {};
        if (ds.ug === 'ask' && !confirm('Post a polite comment from your account asking to repost it with credit?')) return;
        if (ds.ug === 'permission') { const p = prompt('What did they say, and where? (kept as proof)'); if (!p) return; body = {granted: true, proof: p}; }
        return go(b, () => api('POST', `/api/social/ugc/${enc(ds.id)}/${ds.ug}`, body), {ask: 'Asked. When they reply YES, tap They said yes.', permission: 'Saved their yes.', repost: 'A credited draft is in your calendar.'}[ds.ug], true); }
      if (ds.ma) return metaAct(b, ds);
      if (ds.yt) return ytAct(b, ds);
      if (ds.manew) return go(b, () => api('POST', '/api/ads/metaads/drafts', {goal: ds.manew}), 'Draft made from your business facts. Add a photo in the ad details, then Check with Meta.', false, true);
      if (ds.ytnew) return go(b, () => api('POST', '/api/social/ytads/drafts', ds.ytnew === 'youtube' ? {video_id: ((ST.yt || {}).videos || [])[0]?.id || ''} : {kind: ds.ytnew}), 'Draft made - change anything in the ad details, then Check with Google.', false, true);
      if (ds.maacct) return go(b, () => api('POST', '/api/ads/metaads/account', {account: ds.maacct}), 'Ad account chosen.', false, true);
      if (ds.ytcust) return go(b, () => api('POST', '/api/social/ytads/account', {customer_id: ds.ytcust}), 'Ad account chosen.', false, true);
      if (ds.emp) return employee(b, ds.emp);
      if (ds.act) return action(b, ds.act, page);
    };
    page.querySelectorAll('input[name=trust]').forEach(r => r.addEventListener('change', () =>
      go(null, () => api('PUT', '/api/employees/social/settings', {trust: r.value}), `Now: ${TRUST[r.value][0]}.`, true)));
    page.querySelector('#soKids')?.addEventListener('change', ev => go(null, () => api('POST', '/api/social/settings', {yt_kids: ev.target.value === 'yes'}), 'Saved for YouTube.'));
    page.querySelectorAll('input[data-up]').forEach(inp => inp.addEventListener('change', () => {
      const f = inp.files && inp.files[0]; if (!f) return;
      const fd = new FormData(); fd.append('file', f);
      go(null, async () => { const a = await api('POST', '/api/social/media', undefined, {form: fd});
        return api('POST', `/api/social/posts/${enc(inp.dataset.up)}/media`, {assets: [a.id]}); }, 'Added. Approve the post again when it looks right.', true);
    }));
  }
  async function metaAct(b, ds) {
    const act = ds.ma;
    if (act === 'create' && !confirm('Create this ad in your Meta ad account? It is made PAUSED - nothing is spent until you tap Start.')) return;
    if (act === 'start' && !confirm(`Start this ad? Meta can spend up to its daily budget every day, about ${ds.total} in total, and stops it after ${ds.days} days. You can Pause any time.`)) return;
    return go(b, () => api('POST', `/api/ads/metaads/drafts/${enc(ds.id)}/${act}`, act === 'start' ? {confirm: true} : {}),
      {check: 'Meta checked it.', create: 'Made in Meta, paused.', start: 'Started.', pause: 'Paused.'}[act], false, true);
  }
  async function ytAct(b, ds) {
    const act = ds.yt;
    if (act === 'create' && !confirm('Create this ad in your Google Ads account? It is made PAUSED - nothing is spent until you tap Start.')) return;
    if (act === 'start' && !confirm(`Start this ad? Google can spend up to its daily budget every day, about ${ds.total} in total, and it stops after its days. You can Pause any time.`)) return;
    return go(b, () => api('POST', `/api/social/ytads/drafts/${enc(ds.id)}/${act}`, act === 'start' ? {confirm: true} : {}),
      {check: 'Google checked it.', create: 'Made in Google, paused.', start: 'Started.', pause: 'Paused.'}[act], false, true);
  }
  async function action(b, act, page) {
    if (act === 'approve') return go(b, async () => { const r = await api('POST', '/api/social/calendar/approve', {}); return {say: `Approved ${r.approved} posts.`}; }, '', true);
    if (act === 'quiet') return go(b, () => api('POST', '/api/social/settings', {quiet: [Number($('#soQ0').value), Number($('#soQ1').value)]}), 'Quiet hours saved.', true);
    if (act === 'stop') { if (!confirm('Emergency stop? All posting and automatic replies stop, and every queued post goes back to draft.')) return;
      return go(b, async () => { const r = await api('POST', '/api/social/settings', {stop: true}); return {say: `Stopped. ${r.back_to_draft} post(s) back to draft.`}; }, '', true); }
    if (act === 'watch') { const list = id => S($(id).value).split(',').map(x => x.trim()).filter(Boolean);
      return go(b, () => api('POST', '/api/social/growth/watch', {competitors: list('#soComp'), hashtags: list('#soTags')}), 'Saved. Tap Check now or wait for Monday.', true); }
    if (act === 'creator') {
      const out = $('#soCrOut'); out.innerHTML = '<p class="mut">Checking…</p>';
      try {
        const r = await api('POST', '/api/social/creator/check', {username: $('#soCrUser').value, caption: $('#soCrCap').value});
        out.innerHTML = `<div style="margin-top:12px;font-size:14px"><b>@${esc(r.username)}</b> <span class="mut">${esc(r.name || '')}</span>
          <p style="margin:6px 0">${num(r.followers)} followers · ${r.avg_likes != null ? num(r.avg_likes) : '–'} likes + ${r.avg_comments != null ? num(r.avg_comments) : '–'} comments a post${r.eng_rate != null ? ` · ${esc(r.eng_rate)}%` : ''}</p>
          ${(r.signals || []).map(x => `<p style="margin:4px 0;color:var(--warn)">${esc(x)}</p>`).join('') || '<p class="up" style="margin:4px 0">No warning signals in the public numbers.</p>'}
          <p class="mut" style="font-size:12.5px">${esc(r.note || '')}</p></div>`;
      } catch (e) { out.innerHTML = `<p class="down">${esc(e.message)}</p>`; }
      return;
    }
    if (act === 'metaconn') return go(b, async () => { const r = await api('GET', '/api/ads/meta/connect'); window.open(r.url, '_blank', 'noopener'); }, 'Sign in on Facebook, then come back here.');
    if (act === 'ytconn') return go(b, async () => { const r = await api('GET', '/api/social/ytads/connect'); window.open(r.url, '_blank', 'noopener'); }, 'Sign in on Google, then come back here.');
    if (act === 'onboard') {
      page.querySelectorAll('[data-s]').forEach(x => { ST.setup[x.dataset.s] = x.value; });
      ST.setup.trust = page.querySelector('input[name=strust]:checked')?.value || 'seekh';
      const v = ST.setup;
      if (!S(v.business).trim()) return toast('Type your business name first.', true);
      return go(b, async () => {
        await api('POST', '/api/social/onboard', {business: v.business, city: v.city || '', sells: v.sells || '', customers: v.customers || '',
          goal: v.goal || '', languages: v.languages || '', facts: v.facts || '', trust: v.trust});
        location.hash = '#/reports'; return {say: 'Saved. Now connect Instagram or your Facebook Page.'};
      }, '', true);
    }
  }
  async function employee(b, act) {
    if (act === 'leave' && !confirm('Let your Social Media Manager go? Its jobs stop and nothing more is posted. Your posts and numbers stay.')) return;
    try { await api('POST', `/api/employees/social/${act}`); toast({pause: 'Paused.', resume: 'Working again.', leave: 'Let go.'}[act]);
      if (act === 'leave') { location.href = '/console/?v=hire'; return; } await refreshDesk(); }
    catch (e) { toast(e.message, true); }
  }

  start();
})();
