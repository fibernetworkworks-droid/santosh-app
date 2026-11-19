/* v0.999.34 SEO DESK - the SEO Specialist's own section (owner: "MAKE A SEPERATE SECTION. DONT SHOW HOOLA MAIN SIDE BAR
   ... IN RIGHT A CHAT PANEL IN LEFT A SEO DECK WITH SCREENS --- CHAT SECTION WILL STAY THERE EVEN PAGES IN LOADED").
   A thin top bar, then the chat (its own conversation, kind 'seo': she asks, tells it what to improve, and it makes the
   change after her yes) beside the desk's screens: Overview, Plan, Site health, Search, Local & Maps, Reports & settings,
   or the 4-step setup the first time. The chat column is never redrawn when a tab changes. Every number on the screens
   is the server's; where the server has none the screen says so. Routes: #/<tab>. Same sign-in as the console. */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const num = v => (v === null || v === undefined || v === '') ? '–' : (typeof v === 'number' ? v.toLocaleString('en-IN', {maximumFractionDigits: 1}) : esc(v));
  const when = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? '–' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const day = iso => { if (!iso) return ''; const d = new Date(iso); if (isNaN(d)) return ''; const m = Math.floor((Date.now() - d) / 86400000);
    return m < 1 ? 'Today' : m < 2 ? 'Yesterday' : m < 7 ? d.toLocaleDateString('en-IN', {weekday: 'short'}) : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const APP = $('#sd');
  if (!TOKEN) { location.replace('/console/'); return; }

  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
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
    back: '<path d="M15 18l-6-6 6-6"/>', seo: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2M8.5 11h5M11 8.5v5"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);              // credits + the quality tier under the chat's typing box

  const TABS = [['overview', 'Overview'], ['plan', 'Plan'], ['health', 'Site health'], ['search', 'Search'], ['local', 'Local & Maps'], ['reports', 'Reports & settings']];
  const WS = {technical: 'Technical', content: 'Content', local: 'Local', authority: 'Authority', ai_search: 'AI search', reporting: 'Reporting'};
  const COLS = [['planned', 'Planned'], ['doing', 'Doing'], ['waiting_her', 'Waiting for you'], ['done', 'Done']];
  const TRUST = {seekh: ['Learning', 'Asks you before every change.'], saathi: ['Partner', 'Makes small changes that can be undone, and tells you the same day.'],
                 bharosa: ['Trusted', 'Works on its own inside your limits. Opens after a month as Partner.']};
  const ENG = {openai: 'ChatGPT', gemini: 'Gemini', perplexity: 'Perplexity'};
  const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const STARTERS = {
    overview: ['What needs me today?', 'Why did my clicks change?', 'Improve my home page'],
    plan: ["Explain this week's steps", "Do this week's steps for me", 'Which step brings the most customers?'],
    health: ['Fix what you can', 'What should I fix first?', 'Is my site fast enough on phones?'],
    search: ['Which searches should I follow?', 'Why do AI answers name my competitors?', 'Write a page for my main service'],
    local: ['Why am I not in the top 3 near my shop?', 'How do I get more Google reviews?', 'What should my Google profile say?'],
    reports: ['Summarise this month in 3 lines', 'What did you do this week?', 'What will the next report show?']};

  const ST = {tab: 'overview', d: null, v: null, vErr: '', chat: '', canChange: false, where: '', thread: null, bar: null,
    rows: [], res: null, sending: false, working: false, loading: false, sig: '', drawn: false, seq: 0, ctx: '',
    side: 'left', folded: false, planWs: 'all', planWeek: 0, planSel: '', sev: 'all', open: {}, search: 'google',
    grid: 0, spot: -1, setup: {step: 0, v: {}}, timers: []};
  try { ST.side = localStorage.getItem('hoola.seo.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.seo.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/seo/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.seo, '')}</div>
        <h1 class="sd-h">Your SEO Specialist is not hired yet</h1>
        <p class="lead">Hire it from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div><a class="btn" href="/console/?v=hire">Go to AI Employees</a></div></div>`;
      return;
    }
    frame();
    readTab();
    paintDesk();
    await openChat();
    loadIntel();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(refreshDesk, ST.d.state === 'first_run' ? 10000 : 60000));
  }
  function readTab() {
    const t = (location.hash.replace(/^#\/?/, '') || '').split('/')[0];
    ST.tab = TABS.some(x => x[0] === t) ? t : 'overview';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    const d = ST.d, site = d.site || {};
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.seo, '')}</div>
          <div style="min-width:0"><div class="sd-name">SEO Specialist</div>
            <div class="sd-site" id="sdSite">${esc([site.name, site.url].filter(Boolean).join(' · ') || 'Not set up yet')}</div></div>
          <span id="sdState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="SEO chat">
          <div class="sd-chathead"><div class="t"><b>SEO chat</b><span id="sdWhere">Knows your site, plan and Google numbers</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="SEO desk" id="sdTabs"></nav>
          <div id="sdPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or tell it what to improve…', quality: true, onSend: t => send(t), onStop: stopTurn});
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.seo.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.seo.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/seo/chat/new'); ST.chat = r.id; ST.rows = []; ST.sig = ''; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => { refreshDesk(); loadIntel(); });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    window.addEventListener('hashchange', () => { readTab(); paintDesk(true); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#sdState'); if (!el) return;
    const m = {first_run: ['v', 'First check running'], ready: ['ok', 'Working'], error: ['bad', 'Stopped'], new: ['warn', 'Starting']};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !d.onboarded ? ['v', 'Setting up'] : (m[d.state] || ['', S(d.state)]);
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span>`;
    const site = d.site || {}; const s = $('#sdSite'); if (s) s.textContent = [site.name, site.url].filter(Boolean).join(' · ') || 'Not set up yet';
  }

  /* ---------------------------------------------------------------- data */
  async function refreshDesk() {
    try { ST.d = await api('GET', '/api/seo/desk'); } catch { return; }
    stateLine(); paintDesk();
  }
  async function loadIntel() {
    if (!ST.d.onboarded) return;
    try { ST.v = await api('GET', '/api/seo/intel'); ST.vErr = ''; } catch (e) { ST.v = null; ST.vErr = e.message; }
    if (['overview', 'search', 'local', 'reports'].includes(ST.tab)) paintDesk();
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/seo/chat'); ST.chat = r.id; ST.canChange = !!r.can_change; ST.where = r.change_where || ''; }
    catch (e) { toast(e.message, true); return; }
    $('#sdWhere').textContent = ST.canChange ? `Can change ${ST.where} · asks before each change` : 'Writes the fixes for you to paste';
    starters();
    await loadMsgs(true);
  }
  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (STARTERS[ST.tab] || STARTERS.overview).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
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
      const sig = rows.map(r => r.id).join(',');
      ST.sig = sig; merge(rows);
      if (first && lastIsHers()) await ask();
      paintThread();
    } finally { ST.loading = false; }
  }
  function paintThread() {
    if (!ST.thread) return;
    const st = ST.res ? S(ST.res.status) : null;
    const working = ST.sending || (st === null ? lastIsHers() : st === 'working' || st === 'queued');
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Reading your site and numbers…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text)}));
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: [], messages});
    if (ST.working && !working) { refreshDesk(); loadIntel(); }      // a turn ended: what it changed shows on the desk
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, client_id: 'sd' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
    const d = ST.d;
    const waiting = (d.board?.waiting_her || []).length + (d.roadmap_status === 'draft' ? 1 : 0);
    tabs.innerHTML = d.onboarded ? TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === ST.tab}">${esc(n)}${k === 'plan' && waiting ? `<span class="n">${waiting}</span>` : ''}</button>`).join('')
      : '<button type="button" role="tab" aria-selected="true">Setup</button>';
    const page = $('#sdPage');
    if (changed) {
      page.innerHTML = '<div style="display:flex;flex-direction:column;gap:14px;padding-top:4px"><div class="sk" style="height:30px;width:55%"></div><div class="sk" style="height:140px"></div><div class="sk" style="height:200px"></div></div>';
      starters();
      $('#sdDesk').scrollTop = 0;
      clearTimeout(paintDesk._t); paintDesk._t = setTimeout(() => paintDesk(false), 180);
      return;
    }
    try {
      page.innerHTML = `<div class="in-anim" style="display:flex;flex-direction:column;gap:22px">${!d.onboarded ? setupPage() : ({overview, plan, health, search, local, reports}[ST.tab] || overview)()}</div>`;
    } catch (e) { page.innerHTML = `<div class="card"><p class="lead">This screen could not be drawn: ${esc(e.message)}</p></div>`; }
    wirePage(page);
  }
  const askBtn = (about, label = 'Ask') => `<button class="ask" type="button" data-ask="${esc(about)}">${esc(label)}</button>`;
  const fixBtn = (what) => `<button class="ask" type="button" data-fix="${esc(what)}">Fix it</button>`;
  const ring = (score, size = 112) => {
    const r = size / 2 - 10, c = 2 * Math.PI * r, v = Math.max(0, Math.min(100, Number(score) || 0));
    const col = v >= 80 ? 'var(--ok)' : v >= 50 ? 'var(--warn)' : 'var(--bad)';
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="${v} out of 100">
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--seg)" stroke-width="10"/>
      <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${col}" stroke-width="10" stroke-linecap="round"
        stroke-dasharray="${(c * v / 100).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 ${size / 2} ${size / 2})"/>
      <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle" font-size="${size / 4}" font-weight="600" fill="currentColor">${score == null ? '–' : v}</text></svg>`;
  };
  const bar = (label, score, max = 100, unit = '') => `<div class="bar"><span>${esc(label)}</span><i><b style="width:${Math.max(0, Math.min(100, Math.round(100 * (Number(score) || 0) / (max || 100))))}%"></b></i><em>${score == null ? '–' : esc(score) + (unit ? ' ' + unit : max !== 100 ? '/' + max : '')}</em></div>`;
  const kpiChange = k => k.change_pct == null ? '' : `<span class="c ${k.good ? 'up' : 'down'}">${k.change_pct >= 0 ? '+' : ''}${esc(k.change_pct)}%</span>`;
  const evDot = l => ({bad: 'bad', warn: 'warn', ok: 'ok'}[l] || '');

  function needs() {
    const d = ST.d, out = [];
    if (!(d.google || {}).connected) out.push({t: 'Connect Google Search Console', s: 'Real clicks and searches instead of estimates. Read-only: nothing in your Google account can be changed.', b: '<button class="btn sm" type="button" data-act="google">Connect Google</button>'});
    if (d.roadmap_status === 'draft') out.push({t: `Approve your 90-day plan (${num(d.roadmap_count)} steps)`, s: 'Read it, ask about any step in the chat, then approve. The weekly work starts after that.', b: '<a class="btn sm" href="#/plan">Review the plan</a>'});
    for (const it of (d.board?.waiting_her || []).slice(0, 3)) out.push({t: it.title, s: it.why || 'A step in your plan that needs you.', b: askBtn(it.title, 'Ask how')});
    if (d.state === 'first_run') out.push({t: 'The first full check is running', s: 'It reads every page of your website. This screen fills in by itself in 10 to 15 minutes.', b: ''});
    return out;
  }
  function overview() {
    const d = ST.d, k = d.kpis || [], h = (d.pro || {}).health, ev = d.events || [], nd = needs();
    const clicks = k.find(x => /^Clicks from Google/.test(x.name));
    const hi = new Date().getHours(), greet = hi < 12 ? 'Good morning' : hi < 17 ? 'Good afternoon' : 'Good evening';
    const headline = clicks && clicks.now != null ? `${greet}. Google sent you <b>${num(clicks.now)} clicks</b> in the last 28 days.`
      : `${greet}. ${(d.google || {}).connected ? 'Your Google numbers arrive after the next daily run.' : 'Connect Google to see your real clicks here.'}`;
    const rk = ((ST.v || {}).ranks || {}).keywords || [];
    return `<h1 class="sd-h" style="margin-top:6px">${headline}</h1>
      <section class="card tight"><div class="hd"><h3>Needs you ${nd.length ? `<span class="pill v" style="margin-left:6px">${nd.length}</span>` : ''}</h3><span class="mut" style="font-size:13px">Nothing changes on your site until you say so.</span></div>
        ${nd.length ? nd.map((n, i) => `<div class="need"><div class="l"><span class="no">${i + 1}</span><div><div style="font-size:14px;font-weight:500">${esc(n.t)}</div><div class="mut" style="font-size:13px;margin-top:2px">${esc(n.s)}</div></div></div>${n.b}</div>`).join('')
          : '<div class="empty">Nothing needs you today.</div>'}</section>
      <section><div class="hd"><h3>From Google</h3><span class="mut" style="font-size:13px">Last 28 days · baseline ${esc(d.baseline_at ? day(d.baseline_at) : '–')} · Google's numbers run three days behind</span></div>
        ${k.length ? `<div class="grid">${k.map(x => `<div class="card kpi"><span class="n">${esc(x.name)}</span><span class="v">${num(x.now)}</span>
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="mut" style="font-size:12.5px">from ${num(x.baseline)} ${kpiChange(x)}</span>${askBtn(x.name)}</div></div>`).join('')}</div>`
          : '<div class="card"><p class="lead">Numbers appear after the first check.</p></div>'}</section>
      <div class="grid2">
        <section class="card"><div class="hd"><h3>Website health</h3><a href="#/health" style="font-size:13px">All problems →</a></div>
          ${h ? `<div class="ring">${ring(h.total)}<div style="display:flex;flex-direction:column;gap:8px">
              <div>${h.total >= 80 ? '<b>Good.</b>' : h.total >= 50 ? '<b>Fair.</b>' : '<b>Needs work.</b>'} <span class="mut">Out of 100.</span></div>
              <div style="display:flex;gap:6px;flex-wrap:wrap">${['critical', 'high', 'medium', 'low'].map(s => `<span class="pill ${s === 'critical' || s === 'high' ? 'bad' : s === 'medium' ? 'warn' : ''}">${num(h.counts?.[s] || 0)} ${s}</span>`).join('')}</div>
              <div><button class="ask" type="button" data-send="Fix what you can">Fix what you can</button></div></div></div>`
            : '<p class="lead">The health score appears after the first full check.</p>'}</section>
        <section class="card"><h3 style="margin-bottom:6px">What your SEO Specialist did</h3>
          ${ev.length ? `<div class="feed">${ev.slice(0, 6).map(e => `<div><time>${esc(day(e.at))}</time><span><span class="dot ${evDot(e.level)}"></span>${esc(e.text)}</span></div>`).join('')}</div>` : '<div class="empty">Nothing yet.</div>'}</section>
      </div>
      <section class="card tight"><div class="hd"><h3>Searches to watch</h3><a href="#/search" style="font-size:13px">All searches →</a></div>
        ${rk.length ? `<div class="scroll"><table class="tb"><thead><tr><th>Search</th><th>Your place on Google</th><th>7 days</th><th>Clicks (7 days)</th><th></th></tr></thead><tbody>${rk.slice(0, 5).map(r =>
          `<tr><td>${esc(r.keyword)}</td><td class="num">${r.position == null ? '–' : '#' + esc(r.position)}</td><td class="num">${move(r.move_7d)}</td><td class="num">${num(r.clicks_7d)}</td><td style="text-align:right">${askBtn('search "' + r.keyword + '"')}</td></tr>`).join('')}</tbody></table></div>`
          : `<div class="empty">${ST.vErr ? esc(ST.vErr) : 'Add the searches you want to win in Search.'}</div>`}</section>`;
  }
  const move = m => m == null || m === 0 ? '<span class="mut">–</span>' : `<span class="${m > 0 ? 'up' : 'down'}">${m > 0 ? '▲' : '▼'} ${esc(Math.abs(m))}</span>`;

  function plan() {
    const d = ST.d, board = d.board || {};
    const all = COLS.flatMap(([k]) => board[k] || []);
    const weeks = [...new Set(all.map(i => Number(i.week) || 0))].sort((a, b) => a - b);
    const keep = i => (ST.planWs === 'all' || i.workstream === ST.planWs) && (!ST.planWeek || Number(i.week) === ST.planWeek);
    const sel = all.find(i => S(i.id) === ST.planSel);
    const wsUsed = [...new Set(all.map(i => i.workstream))];
    return `${d.roadmap_status === 'draft' ? `<div class="card" style="display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;border-color:var(--acce);background:var(--accs)">
        <div><b>Your 90-day plan is ready</b><div class="mut" style="font-size:13px;margin-top:2px">${num(d.roadmap_count)} steps from the real check. Ask about any step in the chat, then approve.</div></div>
        <button class="btn" type="button" data-act="approve">Approve plan</button></div>` : ''}
      <div class="hd" style="padding:0"><h1 class="sd-h">90-day plan</h1><span class="pill ${d.roadmap_status === 'approved' ? 'ok' : 'v'}">${d.roadmap_status === 'approved' ? 'Approved' : 'Draft'}</span></div>
      ${!all.length ? '<div class="card"><p class="lead">The plan is written after the first full check.</p></div>' : `
      <div class="weeks" role="group" aria-label="Week"><button type="button" data-week="0" aria-pressed="${!ST.planWeek}"><b>All</b>weeks</button>${weeks.map(w => `<button type="button" data-week="${w}" aria-pressed="${ST.planWeek === w}"><b>${w}</b>week</button>`).join('')}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap" role="group" aria-label="Area"><button class="chip" type="button" data-ws="all" aria-pressed="${ST.planWs === 'all'}">All areas</button>${wsUsed.map(w => `<button class="chip" type="button" data-ws="${esc(w)}" aria-pressed="${ST.planWs === w}">${esc(WS[w] || w)}</button>`).join('')}</div>
      <div style="display:grid;grid-template-columns:${sel ? 'minmax(0,1fr) 320px' : '1fr'};gap:16px;align-items:start">
        <div class="board">${COLS.map(([k, n]) => { const items = (board[k] || []).filter(keep);
          return `<div class="col"><h4>${esc(n)} <span>${items.length}</span></h4>${items.map(it => `<button class="task" type="button" data-sel="${esc(it.id)}" aria-pressed="${S(it.id) === ST.planSel}">
            <span class="pill" style="height:22px;font-size:11.5px;align-self:flex-start">${esc(WS[it.workstream] || it.workstream)}</span><b>${esc(it.title)}</b>
            <small>Week ${esc(it.week)}${it.owner === 'her' ? ' · needs you' : ''}</small></button>`).join('') || '<small class="mut" style="padding:4px">Nothing here.</small>'}</div>`; }).join('')}</div>
        ${sel ? `<aside class="card detail"><div class="hd" style="padding-top:0"><span class="pill">${esc(WS[sel.workstream] || sel.workstream)} · week ${esc(sel.week)}</span>
            <button class="ib" type="button" data-sel="" aria-label="Close">×</button></div>
          <h3 style="font-size:17px;line-height:1.35">${esc(sel.title)}</h3>
          ${sel.why ? `<p class="mut">${esc(sel.why)}</p>` : ''}
          ${sel.signal ? `<p><b>Early sign it works:</b> ${esc(sel.signal)}</p>` : ''}${sel.fail_check ? `<p><b>Not working if:</b> ${esc(sel.fail_check)}</p>` : ''}
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
            ${sel.status !== 'doing' && sel.status !== 'done' ? `<button class="btn sm" type="button" data-item="${esc(sel.id)}" data-st="doing">Start</button>` : ''}
            ${sel.status !== 'done' ? `<button class="btn soft sm" type="button" data-item="${esc(sel.id)}" data-st="done">Mark done</button>` : ''}
            ${sel.status !== 'skipped' && sel.status !== 'done' ? `<button class="btn soft sm" type="button" data-item="${esc(sel.id)}" data-st="skipped">Skip</button>` : ''}</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">${askBtn('plan step "' + sel.title + '"')}<button class="ask" type="button" data-send="Do this plan step for me: ${esc(sel.title)}">Do it for me</button></div></aside>` : ''}
      </div>`}`;
  }

  function health() {
    const d = ST.d, p = d.pro || {}, h = p.health, t = d.open_tasks || [], ix = d.index || {}, bots = p.ai_bots || [], c = (d.latest || {}).cwv || {};
    const sevOf = x => S(x.priority || ({bad: 'high', warn: 'medium', info: 'low'}[x.level] || 'low'));
    const counts = {}; t.forEach(x => { const s = sevOf(x); counts[s] = (counts[s] || 0) + 1; });
    const list = t.filter(x => ST.sev === 'all' || sevOf(x) === ST.sev);
    const pc = {critical: 'bad', high: 'bad', medium: 'warn', low: ''};
    const weeks = (d.crux || {}).weeks || [];
    const kinds = {google: 'Google', search: 'AI search', user: 'On request', training: 'Training only'};
    return `<div class="hd" style="padding:0"><h1 class="sd-h">Site health</h1>
        <div style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-run="weekly">Check the whole site now</button><button class="btn sm" type="button" data-send="Fix what you can">Fix what you can</button></div></div>
      <div class="grid2">
        <section class="card">${h ? `<div class="ring">${ring(h.total, 128)}<div style="flex:1;min-width:200px">${(h.parts || []).map(x => bar(x.label, x.score)).join('')}</div></div>` : '<p class="lead">The score appears after the first full check.</p>'}</section>
        <section class="card"><h3>Speed on phones</h3>
          ${c.lcp_ms ? `<p style="font-size:14px;margin:8px 0">The main content shows in <b>${(c.lcp_ms / 1000).toFixed(1)} s</b>. Good is 2.5 s or less.</p>${(c.lcp_parts || []).map(x => bar(x.label, x.ms, Math.max(...c.lcp_parts.map(y => y.ms)), 'ms')).join('')}` : '<p class="lead" style="margin-top:8px">Speed appears after the weekly check.</p>'}
          ${weeks.length > 1 ? `<p class="mut" style="font-size:13px">Real visitors over ${weeks.length} weeks (Chrome data).</p>` : ''}
          ${ix.checked ? `<p style="font-size:14px;margin:10px 0 0"><b>${num(ix.indexed)} of ${num(ix.checked)}</b> key pages are in Google (Google's own answer). <button class="ask" type="button" data-run="index">Check again</button></p>` : ''}</section>
      </div>
      <section class="card tight"><div class="hd"><h3>Problems on your website <span class="mut" style="font-weight:400">${t.length}</span></h3>
          <div style="display:flex;gap:6px;flex-wrap:wrap">${['all', 'critical', 'high', 'medium', 'low'].map(s => `<button class="chip" type="button" data-sev="${s}" aria-pressed="${ST.sev === s}">${s === 'all' ? 'All' : s[0].toUpperCase() + s.slice(1)}${s !== 'all' && counts[s] ? ` · ${counts[s]}` : ''}</button>`).join('')}</div></div>
        ${list.length ? list.slice(0, 40).map((x, i) => { const key = S(x.url) + '|' + S(x.text), open = !!ST.open[key], sv = sevOf(x);
          return `<div class="prob"><button type="button" data-open="${esc(key)}" aria-expanded="${open}"><span class="pill ${pc[sv] || ''}">${esc(sv)}</span><span class="t">${esc(x.text)}</span><span class="p">${esc(S(x.url).replace(/^https?:\/\/[^/]+/, '') || '/')}</span></button>
            ${open ? `<div class="more"><div><b>Fix:</b> ${esc(x.fix || 'Ask in the chat for the exact fix.')}</div>
              <div class="acts">${fixBtn(x.text + ' on ' + (S(x.url).replace(/^https?:\/\/[^/]+/, '') || '/'))}${askBtn(x.text)}</div></div>` : ''}</div>`; }).join('')
          : '<div class="empty">No open problems' + (ST.sev === 'all' ? '.' : ' at this level.') + '</div>'}</section>
      ${bots.length ? `<section class="card tight"><div class="hd"><h3>Can AI search read your site?</h3><span class="mut" style="font-size:13px">These decide if ChatGPT, Claude or Perplexity can show you</span></div>
        <div class="scroll"><table class="tb"><tbody>${bots.filter(b => b.kind !== 'training').map(b => `<tr><td>${esc(b.bot)}</td><td class="mut">${esc(kinds[b.kind] || b.kind)}</td><td style="text-align:right"><span class="pill ${b.allowed ? 'ok' : 'bad'}">${b.allowed ? 'Allowed' : 'Blocked'}</span></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${p.eeat || p.local ? `<div class="grid2">
        ${p.eeat ? `<section class="card"><div class="hd" style="padding-top:0"><h3>Trust signals</h3><b class="num">${num(p.eeat.total)}/100</b></div>${(p.eeat.parts || []).map(x => bar(x.key[0].toUpperCase() + x.key.slice(1), x.score, x.max)).join('')}</section>` : ''}
        ${p.local ? `<section class="card"><div class="hd" style="padding-top:0"><h3>Local search</h3><b class="num">${num(p.local.total)}/100</b></div>${(p.local.parts || []).map(x => bar(x.label, x.score, x.max)).join('')}</section>` : ''}</div>` : ''}
      ${d.shots && (d.shots.mobile || d.shots.desktop) ? `<section class="card"><h3 style="margin-bottom:10px">How Google sees your home page</h3><div class="shots">${['mobile', 'desktop'].filter(k => d.shots[k]).map(k =>
        `<figure style="margin:0"><img src="${esc(d.shots[k].img)}" alt="${k === 'mobile' ? 'Phone' : 'Computer'} view of your home page" loading="lazy"><figcaption class="mut" style="font-size:12px">${k === 'mobile' ? 'Phone' : 'Computer'} · ${esc(when(d.shots[k].at))}</figcaption></figure>`).join('')}</div></section>` : ''}`;
  }

  function search() {
    const v = ST.v;
    if (!v) return `<h1 class="sd-h">Search</h1><div class="card"><p class="lead">${esc(ST.vErr || 'Loading…')}</p></div>`;
    const rk = (v.ranks || {}).keywords || [], ai = v.ai || {}, df = v.dataforseo || {}, sp = v.spend || {}, be = ai.by_engine || {};
    const google = `<section class="card tight"><div class="hd"><h3>Searches you follow</h3><span class="mut" style="font-size:13px">${rk.length} of ${num((v.ranks || {}).max || 100)}</span></div>
        ${rk.length ? `<div class="scroll"><table class="tb"><thead><tr><th>Search</th><th>Place</th><th>7 days</th><th>Clicks (7d)</th><th>Page</th><th></th></tr></thead><tbody>${rk.map(k =>
          `<tr><td>${esc(k.keyword)}</td><td class="num">${k.position == null ? '–' : '#' + esc(k.position)}</td><td class="num">${move(k.move_7d)}</td><td class="num">${num(k.clicks_7d)}</td>
            <td class="mut">${esc(S(k.url).replace(/^https?:\/\/[^/]+/, '') || '–')}</td><td style="text-align:right;white-space:nowrap">${askBtn('search "' + k.keyword + '"')} <button class="ask" type="button" data-untrack="${esc(k.keyword)}">Stop</button></td></tr>`).join('')}</tbody></table></div>`
          : '<div class="empty">Add the searches your customers type.</div>'}
        <div style="display:flex;gap:8px;flex-wrap:wrap;padding:12px 0"><input class="in" id="kwIn" placeholder="e.g. dentist in akola (comma for more)" style="flex:1 1 260px">
          <button class="btn sm" type="button" data-act="track">Follow</button><button class="btn soft sm" type="button" data-act="ideas">Ideas</button>
          <button class="btn soft sm" type="button" data-act="gsc">Refresh from Google</button>
          <button class="btn soft sm" type="button" data-act="serp" ${df.connected ? '' : 'disabled title="Join DataForSEO below first"'}>Exact Google check</button></div>
        <div id="ideasOut"></div><p class="mut" style="font-size:12.5px;margin:0 0 10px">${esc((v.ranks || {}).note || '')}</p></section>`;
    const engines = Object.entries(ai.engines || {});
    const active = (ai.prompts || []).filter(p => p.active).length, ready = Object.values(ai.engines || {}).filter(e => e.ready).length;
    const aiBox = `<section class="card"><div class="hd" style="padding-top:0"><h3>Are you named in AI answers?</h3><span style="display:flex;gap:6px;flex-wrap:wrap">${engines.map(([k, e]) => `<span class="pill ${e.ready ? 'ok' : ''}">${esc(ENG[k] || k)}${e.ready ? '' : ' · not set up'}</span>`).join('')}</span></div>
        ${ai.last_run ? `<div class="grid" style="margin:8px 0 14px"><div class="card kpi"><span class="n">Answers that name you</span><span class="v">${num(ai.summary?.mentioned_pct)}%</span></div>
            <div class="card kpi"><span class="n">Answers that link your site</span><span class="v">${num(ai.summary?.cited_pct)}%</span></div>
            ${Object.entries(be).map(([k, x]) => `<div class="card kpi"><span class="n">${esc(ENG[k] || k)}</span><span class="v">${num(x.mentioned_pct)}%</span><span class="mut" style="font-size:12.5px">links you ${num(x.cited_pct)}%</span></div>`).join('')}</div>
          ${(ai.cited_instead || []).length ? `<p style="font-size:14px"><b>Sites the AI links instead of you:</b> ${ai.cited_instead.map(([dm, n]) => `${esc(dm)} <span class="mut">${n}</span>`).join(' · ')} ${askBtn('the sites AI answers link instead of me')}</p>` : ''}
          ${(ai.competitors_named || []).length ? `<p style="font-size:14px"><b>Competitors named:</b> ${ai.competitors_named.map(([dm, n]) => `${esc(dm)} <span class="mut">${n}</span>`).join(' · ')}</p>` : ''}`
          : '<p class="lead">No answers read yet. Add the questions your customers ask an AI, then ask the AIs.</p>'}
        ${(ai.prompts || []).length ? `<div class="scroll"><table class="tb"><thead><tr><th>Question</th>${Object.keys(ENG).map(k => `<th>${ENG[k]}</th>`).join('')}<th></th></tr></thead><tbody>${ai.prompts.map(p => {
          const r = Object.fromEntries((p.results || []).map(x => [x.engine, x]));
          return `<tr><td>${esc(p.prompt)}${p.active ? '' : ' <span class="mut">(paused)</span>'}</td>${Object.keys(ENG).map(k => `<td>${r[k] ? (r[k].mentioned ? `<span class="up">named${r[k].rank ? ' #' + esc(r[k].rank) : ''}</span>` : '<span class="down">not named</span>') + (r[k].cited ? ' · linked' : '') : '<span class="mut">–</span>'}</td>`).join('')}
            <td><button class="ask" type="button" data-pr="${esc(p.id)}" data-on="${p.active ? '0' : '1'}">${p.active ? 'Pause' : 'Resume'}</button></td></tr>`; }).join('')}</tbody></table></div>` : ''}
        <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:12px"><input class="in" id="qIn" placeholder="A question your customers ask an AI" style="flex:1 1 260px">
          <button class="btn soft sm" type="button" data-act="addq">Add</button><button class="btn soft sm" type="button" data-act="suggest">Suggest questions</button>
          <button class="btn sm" type="button" data-act="airun" ${active && ready ? '' : 'disabled'}>Ask the AIs now</button></div>
        <div id="sugOut"></div>
        <p class="mut" style="font-size:12.5px;margin:10px 0 0">${esc(ai.note || '')} This month ${num(sp.ai_inr)} of ${num(sp.ai_cap_inr)} spent on AI checks.
          <label style="margin-left:8px"><input type="checkbox" id="aiWeekly" ${(v.settings || {}).ai_weekly ? 'checked' : ''}> ask every week</label></p></section>`;
    const dfs = `<section class="card"><div class="hd" style="padding-top:0"><h3>Competitors and links to your site</h3><span class="mut" style="font-size:13px">${df.connected ? `DataForSEO joined · this month $${esc(df.spent_usd)} of $${esc(df.cap_usd)}` : 'Uses your own DataForSEO account'}</span></div>
        ${df.connected ? `<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-dfs="overview">My site</button><button class="btn soft sm" type="button" data-dfs="competitors">Who competes with me</button>
            <button class="btn soft sm" type="button" data-dfs="backlinks">Sites linking to me</button><input class="in" id="gapIn" placeholder="competitor.com" style="flex:0 1 200px"><button class="btn soft sm" type="button" data-dfs="gap">Searches they win</button></div><div id="dfsOut"></div>`
          : `<div class="form"><label>DataForSEO login (email)<input class="in" id="dfLogin" autocomplete="off"></label><label>API password<input class="in" id="dfPw" type="password" autocomplete="new-password"></label></div>
            <div style="padding-top:10px"><button class="btn sm" type="button" data-act="dfjoin">Join DataForSEO</button></div><p class="mut" style="font-size:12.5px">Checked once, then kept sealed. Hoola never shows it again.</p>`}</section>`;
    return `<div class="hd" style="padding:0"><h1 class="sd-h">Search</h1><div class="seg" role="group" aria-label="Where"><button type="button" data-seg="google" aria-pressed="${ST.search === 'google'}">On Google</button><button type="button" data-seg="ai" aria-pressed="${ST.search === 'ai'}">In AI answers</button></div></div>
      ${ST.search === 'google' ? google + dfs : aiBox}`;
  }

  function local() {
    const v = ST.v, d = ST.d, lo = (d.pro || {}).local;
    if (!v) return `<h1 class="sd-h">Local & Maps</h1><div class="card"><p class="lead">${esc(ST.vErr || 'Loading…')}</p></div>`;
    const mp = v.maps || {}, grids = mp.grids || [], g = grids[Math.min(ST.grid, grids.length - 1)];
    const cls = r => r == null ? 'g0' : r <= 3 ? 'g1' : r <= 10 ? 'g2' : 'g3';
    const spot = g && ST.spot >= 0 ? g.points[ST.spot] : null;
    const shop = mp.place && mp.place.id;
    return `<h1 class="sd-h">Local & Maps</h1>
      <section class="card"><div class="hd" style="padding-top:0"><h3>Where you show on Google Maps</h3><span class="mut" style="font-size:13px">${shop ? esc(mp.place.name + (mp.place.address ? ' · ' + mp.place.address : '')) : 'Pick your shop first'}</span></div>
        ${!mp.ready ? '<p class="lead">Google Maps is not set up on the server yet.</p>' : !shop ? `<div><button class="btn sm" type="button" data-act="find">Find my shop on Google Maps</button></div><div id="findOut"></div>` : `
          ${grids.length ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">${grids.map((x, i) => `<button class="chip" type="button" data-grid="${i}" aria-pressed="${i === ST.grid}">${esc(x.keyword)}</button>`).join('')}</div>
            <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start">
              <div class="mgrid" style="grid-template-columns:repeat(${g.size},46px)" role="group" aria-label="Your place at each spot around your shop">${g.points.map((p, i) => `<button type="button" class="${cls(p.rank)}" data-spot="${i}" aria-pressed="${i === ST.spot}" title="${p.rank == null ? 'Not in the first 20' : 'Number ' + p.rank}">${p.rank == null ? '20+' : p.rank}</button>`).join('')}</div>
              <div style="flex:1;min-width:220px;display:flex;flex-direction:column;gap:8px;font-size:14px">
                <div><b>${num(g.top3)} of ${g.points.length}</b> spots show you in the top 3 · average place ${g.average == null ? '–' : esc(g.average)}${g.previous ? ` <span class="mut">(was ${num(g.previous.top3)} top-3)</span>` : ''}</div>
                <div class="mut" style="font-size:13px">Checked ${esc(when(g.at))}. Green = top 3, amber = 4 to 10, red = lower, grey = not in the first 20.</div>
                ${spot ? `<div class="card" style="padding:12px 14px"><b>${spot.rank == null ? 'Not in the first 20 here' : 'You are number ' + esc(spot.rank) + ' here'}</b>
                    <div class="mut" style="font-size:12.5px">${esc(spot.lat)}, ${esc(spot.lng)}</div><div style="margin-top:8px">${askBtn(`my Maps place for "${g.keyword}" at this spot (number ${spot.rank == null ? '20+' : spot.rank})`, 'Ask why')}</div></div>` : '<div class="mut" style="font-size:13px">Tap a square to see that spot.</div>'}
                ${(g.leaders || []).length ? `<div style="font-size:13px"><b>Shown first at your shop:</b> ${g.leaders.map((x, i) => `${i + 1}. ${x.you ? '<b>you</b>' : esc(x.name)}`).join(' · ')}</div>` : ''}</div></div>` : '<p class="lead">No grid yet. Type a search your customers use and check it.</p>'}
          <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:14px"><input class="in" id="gridKw" placeholder="e.g. dentist near me" style="flex:1 1 220px">
            <select class="in" id="gridSize" style="width:auto">${[3, 5, 7].map(n => `<option value="${n}" ${n === ((v.settings || {}).grid_size || 5) ? 'selected' : ''}>${n} × ${n}</option>`).join('')}</select>
            <button class="btn sm" type="button" data-act="grid">Check this search</button><button class="btn soft sm" type="button" data-act="find">Change shop</button></div><div id="findOut"></div>`}
        <p class="mut" style="font-size:12.5px;margin:10px 0 0">${esc(mp.note || '')}</p></section>
      ${lo ? `<section class="card"><div class="hd" style="padding-top:0"><h3>Local search score</h3><b class="num">${num(lo.total)}/100</b></div>${(lo.parts || []).map(x => bar(x.label, x.score, x.max)).join('')}<p class="mut" style="font-size:13px">${esc(lo.note || '')}</p></section>` : ''}
      <section class="card"><h3>Google profile, reviews and listings</h3>
        <p class="lead" style="margin-top:8px">Hoola cannot read or change your Google Business Profile, reply to reviews or check your name, address and phone on Justdial and Practo yet. Ask in the chat and it will write the review replies and profile text for you to paste.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><button class="ask" type="button" data-send="Write my Google Business Profile description">Write my profile description</button>
          <button class="ask" type="button" data-send="Write a WhatsApp message asking happy customers for a Google review">Message asking for reviews</button></div></section>`;
  }

  function reports() {
    const d = ST.d, ev = d.events || [], v = ST.v || {}, df = v.dataforseo || {}, sp = v.spend || {};
    const weekly = ev.filter(e => e.kind === 'run'), monthly = ev.filter(e => e.kind === 'report');
    const tr = d.trust || 'seekh';
    return `<h1 class="sd-h">Reports & settings</h1>
      <div class="grid2">
        <section class="card"><div class="hd" style="padding-top:0"><h3>Monthly reports</h3><button class="btn soft sm" type="button" data-run="monthly">Make one now</button></div>
          ${monthly.length ? `<div class="feed">${monthly.map(e => `<div><time>${esc(day(e.at))}</time><span>${esc(e.text)}</span></div>`).join('')}</div>` : '<p class="lead">The first report is made on the 1st of next month. It arrives as a PDF in your Hoola chat.</p>'}</section>
        <section class="card"><h3 style="margin-bottom:6px">Weekly checks</h3>
          ${weekly.length ? `<div class="feed">${weekly.slice(0, 6).map(e => `<div><time>${esc(day(e.at))}</time><span><span class="dot ${evDot(e.level)}"></span>${esc(e.text)}</span></div>`).join('')}</div>` : '<div class="empty">Nothing yet.</div>'}</section>
      </div>
      <section class="card tight"><div class="hd"><h3>Works around the clock</h3></div>
        <div class="scroll"><table class="tb"><thead><tr><th>Job</th><th>When</th><th>Last run</th></tr></thead><tbody>${(d.schedule || []).map(x => `<tr><td>${esc(x.job)}</td><td>${esc(x.every)}</td><td class="mut">${esc(when(x.last))}</td></tr>`).join('')}</tbody></table></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;padding:12px 0"><button class="btn soft sm" type="button" data-run="daily">Refresh Google numbers</button><button class="btn soft sm" type="button" data-run="roadmap">Rewrite the plan draft</button></div></section>
      <section class="card tight"><div class="hd"><h3>Connections</h3></div>
        <div class="row"><div><div class="t">Google Search Console${(d.google || {}).analytics ? ' and Analytics' : ''}</div><div class="s">Real clicks, searches and leads. Read-only.</div></div><div class="r">${(d.google || {}).connected ? '<span class="pill ok">Connected</span>' : '<button class="btn sm" type="button" data-act="google">Connect</button>'}</div></div>
        <div class="row"><div><div class="t">Changes to your website</div><div class="s">${ST.canChange ? `Hoola built ${esc(ST.where)}, so it can make changes after your yes.` : 'Your site was not built by Hoola, so it writes each fix for you to paste.'}</div></div><div class="r"><span class="pill ${ST.canChange ? 'ok' : ''}">${ST.canChange ? 'Can change' : 'Fixes to paste'}</span></div></div>
        <div class="row"><div><div class="t">DataForSEO</div><div class="s">Competitors and links to your site, on your own account.</div></div><div class="r"><span class="pill ${df.connected ? 'ok' : ''}">${df.connected ? 'Joined' : 'Not joined'}</span>${df.connected ? '' : '<a class="ask" href="#/search">Join</a>'}</div></div>
        <div class="row"><div><div class="t">Bing and other engines (IndexNow)</div><div class="s">${(d.indexnow || {}).key ? `Put a file named ${esc(d.indexnow.key)}.txt with only that text at the top of your website.` : 'Tells Bing about changed pages every week. Google does not use it.'}</div></div><div class="r"><button class="btn soft sm" type="button" data-act="indexnow">${(d.indexnow || {}).key ? 'Check the file' : 'Turn on'}</button></div></div></section>
      <section class="card"><h3>How much it may do on its own</h3>
        <div style="display:flex;flex-direction:column;gap:10px;margin-top:12px">${Object.entries(TRUST).map(([k, [n, s]]) => `<label class="choice${k === 'bharosa' ? ' off' : ''}"><input type="radio" name="trust" value="${k}" ${k === tr ? 'checked' : ''} ${k === 'bharosa' ? 'disabled' : ''}><span><b>${n}</b><br><span class="mut" style="font-size:13px">${esc(s)}</span></span></label>`).join('')}</div></section>
      <section class="card"><h3>Spending</h3>
        <p style="font-size:14px;margin:8px 0">AI answer checks this month: <b>${num(sp.ai_inr)}</b> of ${num(sp.ai_cap_inr)}.${df.connected ? ` DataForSEO: $${esc(df.spent_usd)} of $${esc(df.cap_usd)}.` : ''}</p>
        ${df.connected ? `<label style="font-size:13px" class="mut">DataForSEO monthly limit $ <input class="in" id="capIn" type="number" min="0.5" step="0.5" value="${esc(df.cap_usd)}" style="width:100px;display:inline-block"></label>` : ''}</section>
      <section class="card"><h3>Your SEO Specialist</h3>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">${d.status === 'paused' ? '<button class="btn sm" type="button" data-emp="resume">Resume work</button>' : '<button class="btn soft sm" type="button" data-emp="pause">Pause work</button>'}
          <button class="btn soft sm bad" type="button" data-emp="leave">Let go</button></div>
        <p class="mut" style="font-size:12.5px">Pausing stops every check and job until you resume. Letting go keeps your reports.</p></section>`;
  }

  function setupPage() {
    const s = ST.setup, v = s.v, n = s.step;
    const field = (id, label, ph, wide, type = 'text') => `<label class="${wide ? 'wide' : ''}">${label}<input class="in" id="${id}" type="${type}" placeholder="${esc(ph)}" value="${esc(v[id] || '')}"></label>`;
    const steps = [
      ['Your website', 'Where should your SEO Specialist work?', `<div class="form">${field('url', 'Website address', 'yourbusiness.in', true)}${field('name', 'Business name', 'Sharma Dental Clinic')}${field('city', 'City', 'Akola')}</div>`],
      ['What you sell', 'This decides which searches it works on.', `<div class="form">${field('services', 'What you sell (comma between)', 'Root canal, implants, braces', true)}${field('goal', 'What do you want from Google?', 'More calls for implants in Akola', true)}${field('customers', 'Who are your customers?', 'Families in Akola and nearby towns', true)}</div>`],
      ['Competitors', 'Optional. It compares your site with theirs.', `<div class="form">${field('competitors', "Competitors' websites (comma between)", 'smiledental.in, citydentist.in', true)}</div>`],
      ['How it works with you', 'You can change this later.', `<div style="display:flex;flex-direction:column;gap:10px">${['seekh', 'saathi'].map(k => `<label class="choice"><input type="radio" name="sTrust" value="${k}" ${(v.trust || 'seekh') === k ? 'checked' : ''}><span><b>${TRUST[k][0]}</b><br><span class="mut" style="font-size:13px">${esc(TRUST[k][1])}</span></span></label>`).join('')}</div>
        <div class="form" style="margin-top:14px"><label>Weekly note on<select class="in" id="weekday">${DAYS.map((x, i) => `<option value="${i}" ${String(v.weekday || 0) === String(i) ? 'selected' : ''}>${x}</option>`).join('')}</select></label>${field('time', 'At', '', false, 'time').replace('value=""', `value="${esc(v.time || '09:30')}"`)}</div>`]];
    const [t, sub, body] = steps[n];
    return `<div style="max-width:640px;width:100%;margin:12px auto 0;display:flex;flex-direction:column;gap:18px">
      <div class="steps">${steps.map((_, i) => `<span class="${i <= n ? 'on' : ''}"></span>`).join('')}</div>
      <div><div class="mut" style="font-size:13px">Step ${n + 1} of ${steps.length}</div><h1 class="sd-h">${esc(t)}</h1><p class="lead" style="margin-top:6px">${esc(sub)}</p></div>
      <div class="card">${body}</div>
      <div style="display:flex;justify-content:space-between;gap:10px">${n ? '<button class="btn soft" type="button" data-step="-1">Back</button>' : '<span></span>'}
        ${n < steps.length - 1 ? '<button class="btn" type="button" data-step="1">Next</button>' : '<button class="btn" type="button" data-act="onboard">Start work</button>'}</div>
      <p class="mut" style="font-size:13px">Then it checks every page, reads your Google numbers and writes a 90-day plan for you to approve. You can also tell the chat your website.</p></div>`;
  }
  function keepSetup(page) {
    page.querySelectorAll('.card input.in, .card select.in').forEach(i => { ST.setup.v[i.id] = i.value; });
    const tr = page.querySelector('input[name=sTrust]:checked'); if (tr) ST.setup.v.trust = tr.value;
  }

  /* ---------------------------------------------------------------- the desk's buttons */
  function wirePage(page) {
    page.onclick = async e => {
      const b = e.target.closest('button,a[data-ask]'); if (!b) return;
      const ds = b.dataset;
      if (ds.ask) return setCtx(ds.ask);
      if (ds.fix) return send('Fix this: ' + ds.fix);
      if (ds.send) return send(ds.send);
      if (ds.week !== undefined) { ST.planWeek = Number(ds.week); return paintDesk(); }
      if (ds.ws) { ST.planWs = ds.ws; return paintDesk(); }
      if (ds.sel !== undefined) { ST.planSel = ds.sel === ST.planSel ? '' : ds.sel; return paintDesk(); }
      if (ds.sev) { ST.sev = ds.sev; return paintDesk(); }
      if (ds.open) { ST.open[ds.open] = !ST.open[ds.open]; return paintDesk(); }
      if (ds.seg) { ST.search = ds.seg; return paintDesk(); }
      if (ds.grid !== undefined) { ST.grid = Number(ds.grid); ST.spot = -1; return paintDesk(); }
      if (ds.spot !== undefined) { ST.spot = Number(ds.spot) === ST.spot ? -1 : Number(ds.spot); return paintDesk(); }
      if (ds.step) { keepSetup(page); ST.setup.step = Math.max(0, Math.min(3, ST.setup.step + Number(ds.step)));
        if (ST.setup.step === 1 && !S(ST.setup.v.url).trim()) { ST.setup.step = 0; toast('Type your website address first.', true); } return paintDesk(); }
      if (ds.item) return go(b, () => api('POST', `/api/seo/roadmap/item/${enc(ds.item)}`, {status: ds.st}), 'Updated.', true);
      if (ds.run) return go(b, () => api('POST', `/api/seo/run/${ds.run}`, {}), {weekly: 'Full check started. Results land here in a few minutes.', daily: 'Refreshing the Google numbers.',
        monthly: 'Making the report. The PDF arrives in your Hoola chat.', roadmap: 'Plan draft rewritten.', index: 'Asking Google about your key pages.'}[ds.run], true);
      if (ds.untrack) return go(b, () => api('POST', '/api/seo/intel/track', {keywords: [ds.untrack], remove: true}), 'Stopped following it.', false, true);
      if (ds.pr) return go(b, () => api('POST', '/api/seo/intel/ai/prompt', {id: ds.pr, active: ds.on === '1'}), 'Saved.', false, true);
      if (ds.dfs) return dfsCall(b, ds.dfs);
      if (ds.emp) return employee(b, ds.emp);
      if (ds.act) return action(b, ds.act, page);
    };
    page.querySelectorAll('input[name=trust]').forEach(r => r.addEventListener('change', () =>
      go(null, () => api('PUT', '/api/employees/seo/settings', {trust: r.value}), `Now: ${TRUST[r.value][0]}.`, true)));
    const w = page.querySelector('#aiWeekly'); if (w) w.addEventListener('change', () => go(null, () => api('POST', '/api/seo/intel/settings', {ai_weekly: w.checked}), 'Saved.', false, true));
    const cap = page.querySelector('#capIn'); if (cap) cap.addEventListener('change', () => go(null, () => api('POST', '/api/seo/intel/settings', {dfs_cap_usd: Number(cap.value)}), 'Limit saved.', false, true));
  }
  async function go(btn, fn, done, desk, intel) {
    if (btn) btn.disabled = true;
    try { const r = await fn(); toast((r && r.say) || done || 'Done.'); if (desk) await refreshDesk(); if (intel) await loadIntel(); }
    catch (e) { toast(e.message, true); }
    if (btn && btn.isConnected) btn.disabled = false;
  }
  const lines = id => S($(id)?.value).split(/[,\n]/).map(x => x.trim()).filter(Boolean);
  async function action(b, act, page) {
    if (act === 'google') { try { const r = await api('GET', '/api/seo/gsc/link'); window.open(r.url, '_blank', 'noopener'); toast('Sign in on Google, then come back here.'); } catch (e) { toast(e.message, true); } return; }
    if (act === 'approve') return go(b, () => api('POST', '/api/seo/roadmap/approve', {}), 'Plan approved. Work starts this week.', true);
    if (act === 'indexnow') return go(b, async () => { const r = await api('POST', '/api/seo/run/indexnow', {}); return r; }, '', true);
    if (act === 'track') { const k = lines('#kwIn'); if (!k.length) return toast('Type a search first.', true); return go(b, () => api('POST', '/api/seo/intel/track', {keywords: k}), 'Following.', false, true); }
    if (act === 'gsc') return go(b, () => api('POST', '/api/seo/intel/ranks/gsc', {}), 'Places refreshed from Google.', false, true);
    if (act === 'serp') { if (!confirm('Check every search on Google through DataForSEO? It costs a little per search on your DataForSEO balance.')) return; return go(b, () => api('POST', '/api/seo/intel/ranks/serp', {}), '', false, true); }
    if (act === 'ideas') {
      const out = $('#ideasOut'); out.innerHTML = '<p class="mut">Finding ideas…</p>';
      try { const r = await api('POST', '/api/seo/intel/keywords', {seeds: lines('#kwIn')});
        out.innerHTML = `<p class="mut" style="font-size:12.5px">${esc(r.source || '')}</p><div style="display:flex;gap:6px;flex-wrap:wrap;padding-bottom:10px">${(r.ideas || []).slice(0, 24).map(x => `<button class="chip" type="button" data-addkw="${esc(x.text)}">+ ${esc(x.text)} <span class="mut">${num(x.searches)}</span></button>`).join('') || '<span class="mut">No ideas.</span>'}</div>`;
        out.onclick = ev => { const c = ev.target.closest('[data-addkw]'); if (c) go(c, () => api('POST', '/api/seo/intel/track', {keywords: [c.dataset.addkw]}), 'Following.', false, true); };
      } catch (e) { out.innerHTML = `<p class="down">${esc(e.message)}</p>`; }
      return;
    }
    if (act === 'addq') { const q = S($('#qIn')?.value).trim(); if (!q) return toast('Type a question first.', true); return go(b, () => api('POST', '/api/seo/intel/ai/prompts', {prompts: [q]}), 'Question added.', false, true); }
    if (act === 'suggest') {
      const out = $('#sugOut'); out.innerHTML = '<p class="mut">Thinking of questions…</p>';
      try { const r = await api('POST', '/api/seo/intel/ai/suggest', {});
        out.innerHTML = `<div style="display:flex;gap:6px;flex-wrap:wrap;padding-top:10px">${(r.suggestions || []).map(q => `<button class="chip" type="button" data-sug="${esc(q)}">+ ${esc(q)}</button>`).join('') || '<span class="mut">No ideas.</span>'}</div>`;
        out.onclick = ev => { const c = ev.target.closest('[data-sug]'); if (c) go(c, () => api('POST', '/api/seo/intel/ai/prompts', {prompts: [c.dataset.sug]}), 'Added.', false, true); };
      } catch (e) { out.innerHTML = `<p class="down">${esc(e.message)}</p>`; }
      return;
    }
    if (act === 'airun') { if (!confirm('Ask ChatGPT, Gemini and Perplexity every active question now? Each answer counts toward your monthly limit.')) return; return go(b, () => api('POST', '/api/seo/intel/ai/run', {}), '', false, true); }
    if (act === 'dfjoin') return go(b, () => api('POST', '/api/seo/intel/dataforseo', {login: S($('#dfLogin')?.value), password: S($('#dfPw')?.value)}), 'Joined.', false, true);
    if (act === 'find') {
      const out = $('#findOut'); out.innerHTML = '<p class="mut">Searching Google Maps…</p>';
      try { const r = await api('POST', '/api/seo/intel/maps/find', {});
        out.innerHTML = (r.candidates || []).map((c, i) => `<div class="row"><div><div class="t">${esc(c.name)}</div><div class="s">${esc(c.address)}</div></div><button class="btn soft sm" type="button" data-place="${i}">This is my shop</button></div>`).join('') || '<p class="mut">Not found. Check the business name and city.</p>';
        out.onclick = ev => { const c = ev.target.closest('[data-place]'); if (c) go(c, () => api('POST', '/api/seo/intel/maps/place', {place: r.candidates[+c.dataset.place]}), 'Shop saved.', false, true); };
      } catch (e) { out.innerHTML = `<p class="down">${esc(e.message)}</p>`; }
      return;
    }
    if (act === 'grid') {
      const kw = S($('#gridKw')?.value).trim(), size = Number($('#gridSize')?.value || 5);
      if (!kw) return toast('Type the search, for example "dentist near me".', true);
      const sv = (ST.v || {}).settings || {};
      return go(b, async () => { await api('POST', '/api/seo/intel/settings', {grid_keywords: [...new Set([...(sv.grid_keywords || []), kw])].slice(-5), grid_size: size});
        return api('POST', '/api/seo/intel/maps/grid', {keyword: kw, size}); }, 'Checking. The grid fills in a minute.', false, true);
    }
    if (act === 'onboard') {
      keepSetup(page);
      const v = ST.setup.v;
      if (!S(v.url).trim()) { ST.setup.step = 0; paintDesk(); return toast('Type your website address first.', true); }
      return go(b, async () => {
        const r = await api('POST', '/api/seo/onboard', {url: v.url, name: v.name || '', city: v.city || '', services: v.services || '', goal: v.goal || '',
          customers: v.customers || '', competitors: v.competitors || '', weekday: Number(v.weekday || 0), morning_time: v.time || '09:30', trust: v.trust || 'seekh'});
        await openChat(); loadIntel(); return r; }, 'Started. The first check takes 10 to 15 minutes.', true);
    }
  }
  async function dfsCall(b, what) {
    const out = $('#dfsOut'); out.innerHTML = '<p class="mut">Asking DataForSEO…</p>';
    try {
      const r = await api('POST', `/api/seo/intel/dfs/${what}`, {competitor: S($('#gapIn')?.value).trim()});
      const tbl = (h, rows) => `<div class="scroll"><table class="tb"><thead><tr>${h.map(x => `<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
      out.innerHTML = (what === 'overview' ? `<p style="font-size:14px"><b>${esc(r.domain)}</b>: ${num(r.keywords)} searches in Google India, ${num(r.top3)} in the top 3, ${num(r.top10)} in the top 10, about ${num(r.traffic)} visits a month.</p>`
        : what === 'competitors' ? tbl(['Competitor', 'Shared searches', 'Their average place', 'Their searches', 'Their visits'], (r.competitors || []).map(c => `<tr><td>${esc(c.domain)}</td><td>${num(c.shared_keywords)}</td><td>${esc(c.avg_position)}</td><td>${num(c.keywords)}</td><td>${num(c.traffic)}</td></tr>`))
        : what === 'gap' ? `<p style="font-size:14px">${esc(r.say || '')}</p>` + tbl(['Search', 'Searches a month', 'Their place', 'Yours', 'Their page'], (r.gap || []).map(g => `<tr><td>${esc(g.keyword)}</td><td>${num(g.volume)}</td><td>${esc(g.their_position)}</td><td>${g.your_position == null ? '–' : esc(g.your_position)}</td><td class="mut">${esc(g.their_url)}</td></tr>`))
        : `<p style="font-size:14px"><b>${esc(r.domain)}</b>: ${num(r.backlinks)} links from ${num(r.referring_domains)} sites, ${num(r.broken)} broken.</p>` + tbl(['Site linking to you', 'Its rank', 'Links', 'First seen'], (r.top_referrers || []).map(x => `<tr><td>${esc(x.domain)}</td><td>${num(x.rank)}</td><td>${num(x.backlinks)}</td><td>${esc(x.first_seen)}</td></tr>`)))
        + `<p class="mut" style="font-size:12.5px">This month $${esc((r.spend || {}).spent_usd)} of $${esc((r.spend || {}).cap_usd)}.</p>`;
    } catch (e) { out.innerHTML = `<p class="down">${esc(e.message)}</p>`; }
  }
  async function employee(b, act) {
    if (act === 'leave' && !confirm('Let your SEO Specialist go? Its checks and jobs stop. Your reports stay.')) return;
    try { await api('POST', `/api/employees/seo/${act}`); toast({pause: 'Paused.', resume: 'Working again.', leave: 'Let go.'}[act]);
      if (act === 'leave') { location.href = '/console/?v=hire'; return; } await refreshDesk(); }
    catch (e) { toast(e.message, true); }
  }

  start();
})();
