/* v0.999.47 LEAD DESK - the Lead Generation employee's own section (the Accounts desk's twin; owner: "PERFECT GO WITH
   LEAD GENEARTION" -> the design claude.ai/artifact/FTaYVw37EiqT7gp1NAGGkg -> "GO BUILD").
   A thin top bar, then the Lead Generation chat (its own conversation, kind 'leads': she asks, attaches her own list as a
   CSV / Excel with + or by dropping it) beside the desk's pages: Today, Find leads, Leads (+ one lead), Lists, Quality &
   settings. The chat column is never redrawn when a page changes. Starting a paid search, handing a list to the campaign
   desk or the Telecaller, opting a business out and forgetting are her taps here; nothing is ever sent from this page.
   Routes: #/<page>, #/lead/<id>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', lead: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['find', 'Find leads'], ['leads', 'Leads'], ['lists', 'Lists'], ['quality', 'Quality & settings']];
  const STAGES = [['new', 'New'], ['contacted', 'Contacted'], ['interested', 'Interested'], ['not_interested', 'Not interested'], ['won', 'Won']];
  const STAGE_PILL = {new: 'v', contacted: 'warn', interested: 'ok', not_interested: 'bad', won: 'ok', opted_out: ''};
  const TRUST = {seekh: ['Learning', 'Finds and keeps leads, and drafts messages. Every paid search and every hand-over waits for your tap.'],
                 saathi: ['Partner', 'Also runs free searches and fills in contacts on its own. Paid searches and hand-overs still wait for you.'],
                 bharosa: ['Trusted', 'Does more on its own. Sending to anyone, opting out and forgetting always stay yours.']};
  const STARTERS = {
    today: ['Who should I follow up today?', 'Find dentists in Pune', 'How many leads have no phone?'],
    find: ['Get steel suppliers in Nagpur from IndiaMART', 'Find pharmacies in Akola on Google Maps', 'What does each source cost?'],
    leads: ['Which leads are interested?', 'Who have I not contacted yet?', 'Mark the ticked leads as contacted'],
    lead: ['Write a short follow-up message', 'Set a follow-up for next Monday', 'Summarise this lead'],
    lists: ['Which list should go to the campaign?', 'What was sent last week?', 'Save this search to run weekly'],
    quality: ['How clean is my store?', 'Fill in the missing phones', 'Which leads are the same business twice?']};
  const MAXF = 20, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], emp: null,
    f: {stage: '', q: '', city: '', lane: '', has_phone: false, due: false}, sel: new Set(), hand: null, tele: null, pageData: null};
  try { ST.side = localStorage.getItem('hoola.leads.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.leads.folded') === '1'; } catch {}

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/leads/desk/summary'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.lead, '')}</div>
        <h1 class="sd-h">Your Lead Generation employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="ldHire">Hire Lead Generation</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#ldHire').onclick = async () => { try { await api('POST', '/api/employees/leads/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
    if (parts[0] === 'lead' && parts[1]) { ST.tab = 'lead'; ST.arg = decodeURIComponent(parts[1]); return; }
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today'; ST.arg = '';
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.lead, '')}</div>
          <div style="min-width:0"><div class="sd-name">Lead Generation</div>
            <div class="sd-site" id="ldSite">It finds and keeps leads. Nothing is sent without your tap.</div></div>
          <span id="ldState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Lead Generation chat">
          <div class="sd-chathead"><div class="t"><b>Lead Generation chat</b><span>Attach your list as CSV or Excel · nothing is sent without your tap</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="ac-files" id="adFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="adPick" multiple hidden accept=".csv,.xlsx,.xlsm,.txt,.tsv,application/pdf,.pdf,image/*">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Lead Generation desk" id="sdTabs"></nav>
          <div id="ldPage"></div></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask, or attach your list (CSV / Excel)…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#adPick').click()});
    $('#adPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.leads.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.leads.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/leads/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#ldPage').addEventListener('click', onPageClick);
    $('#ldPage').addEventListener('change', onPageChange);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d || {}, el = $('#ldState'); if (!el) return;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
  }
  function paintTabs() {
    const d = ST.d || {}, due = (d.due || []).length, cur = ST.tab === 'lead' ? 'leads' : ST.tab;
    $('#sdTabs').innerHTML = TABS.map(([k, n]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="${k === cur}">${esc(n)}${
      k === 'today' && due ? `<span class="n" aria-label="${due} follow-ups due">${due}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(all) {
    try { ST.d = await api('GET', '/api/leads/desk/summary'); } catch { return; }
    stateLine(); paintTabs();
    if (all || ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  const pill = (stage, name) => `<span class="pill ${STAGE_PILL[stage] || ''}">${esc(name)}</span>`;
  const when = v => { if (!v) return ''; const d = new Date(v); return isNaN(d) ? S(v) : d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short'}); };
  const sec = (title, body, right = '') => `<section class="card" style="display:flex;flex-direction:column;gap:12px"><div style="display:flex;align-items:center;gap:10px;justify-content:space-between;flex-wrap:wrap"><h2 style="margin:0;font-size:16px;font-weight:600">${title}</h2>${right}</div>${body}</section>`;
  const head = (title, sub, right = '') => `<div style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin:4px 0 2px"><div style="flex:1;min-width:220px"><h1 class="sd-h serif" style="margin:0">${title}</h1>${sub ? `<p class="mut" style="margin:6px 0 0">${sub}</p>` : ''}</div>${right}</div>`;
  async function showPage(quiet) {
    const box = $('#ldPage'); if (!box) return;
    if (!quiet) { box.innerHTML = '<div class="empty" style="padding:28px">Loading…</div>'; $('#sdDesk').scrollTop = 0; }
    starters();
    const t = ST.tab;
    try {
      if (t === 'today') box.innerHTML = pageToday(await api('GET', '/api/leads/desk'));
      else if (t === 'find') box.innerHTML = pageFind(await api('GET', '/api/leads'), await api('GET', '/api/leads/desk/lists'));
      else if (t === 'leads') await paintLeads(box);
      else if (t === 'lead') box.innerHTML = pageLead(await api('GET', `/api/leads/desk/leads/${enc(ST.arg)}`));
      else if (t === 'lists') box.innerHTML = pageLists(await api('GET', '/api/leads/desk/lists'), await api('GET', '/api/leads/outreach?limit=60'));
      else if (t === 'quality') box.innerHTML = pageQuality(await api('GET', '/api/leads/desk/quality'), await api('GET', '/api/leads'));
    } catch (e) { box.innerHTML = `<div class="card"><p class="lead">${esc(e.message)}</p><button class="btn soft sm" type="button" data-act="reload">Try again</button></div>`; }
  }

  function leadRow(x, acts) {
    return `<div class="row"><div style="flex:1;min-width:0"><div class="t"><a href="#/lead/${enc(x.id)}">${esc(x.name)}</a> ${pill(x.stage, x.stage_name)}</div>
      <div class="s">${esc([x.category, x.city, x.follow_note && `“${x.follow_note}”`, x.follow_on && `due ${when(x.follow_on)}`].filter(Boolean).join(' · '))}</div></div>${acts || ''}</div>`;
  }
  function pageToday(d) {
    const c = d.counts || {};
    const kpi = (v, n) => `<div class="card kpi"><div class="v">${num(v)}</div><div class="n">${esc(n)}</div></div>`;
    const due = (d.due || []).map(x => leadRow(x, `<button class="btn soft sm" type="button" data-ask="Write a short follow-up message for ${esc(x.name)}" data-lid="${esc(x.id)}">Draft a message</button><button class="btn soft sm" type="button" data-done="${esc(x.id)}">Done</button><a class="btn sm" href="#/lead/${enc(x.id)}">Open</a>`)).join('');
    const run = (d.running || []).map(r => `<div class="row"><div style="flex:1"><div class="t">${esc(r.ask || 'Search')}</div><div class="s">${esc(r.status)} · ${num(r.found)} found · ${num(r.kept)} kept</div></div></div>`).join('');
    const recent = (d.recent_runs || []).slice(0, 5).map(r => `<div class="row"><div style="flex:1"><div class="t">${esc(r.ask || 'Search')}</div><div class="s">${esc(when(r.created_at))} · ${esc(r.status)} · ${num(r.kept)} kept of ${num(r.found)} found${r.duped ? ` · ${num(r.duped)} were the same business` : ''}${r.error ? ' · ' + esc(r.error) : ''}</div></div></div>`).join('');
    const needs = [];
    if (d.no_phone) needs.push(`<div class="row"><span class="pill warn"><span class="dt"></span></span><div style="flex:1"><div class="t">${num(d.no_phone)} lead${d.no_phone > 1 ? 's have' : ' has'} no phone</div><div class="s">Hoola can read their own websites for one, free.</div></div><a class="btn sm" href="#/quality">See them</a></div>`);
    const dl = (d.due || []).length;
    return `${head(dl ? `${dl} follow-up${dl > 1 ? 's are' : ' is'} due today.` : 'Nothing is due today.', 'Every search, hand-over and message waits for your tap.')}
      <div class="grid">${kpi(c.all, 'leads kept')}${kpi(d.new_this_week, 'new this week')}${kpi(c.interested, 'interested')}${kpi(c.won, 'won')}</div>
      ${sec('Follow-ups due', due || '<p class="mut" style="margin:0">No follow-up is due. Set one on any lead.</p>')}
      ${needs.length ? sec('Needs you', needs.join('')) : ''}
      ${run ? sec('Running now', run) : ''}
      ${sec('Recent searches', recent || '<p class="mut" style="margin:0">No search yet. Ask in the chat, for example “find dentists in Pune”, or open Find leads.</p>', '<a class="btn soft sm" href="#/find">Find leads</a>')}`;
  }

  function pageFind(o, l) {
    const built = o.lanes_built || {}, u = o.usage || {}, caps = o.caps || {};
    const left = Math.max(0, Number(u.per_day_left ?? ((caps.per_day || 0) - (u.rows_kept || 0))));
    const src = [['HER_DATA', 'Your own list', 'CSV or Excel. Free.'], ['REGISTRY', 'IndiaMART sellers', "IndiaMART's official connection. Free."],
      ['OFFICIAL_API', 'Google Maps', 'Official route on your Maps key. Phone and website details are paid per business.'],
      ['SCRAPE', 'Public Maps listings scan', 'Wider reach, slow and polite. Off until you switch it on.'],
      ['VENDOR', 'Paid lead seller', 'A data seller you choose. Priced before it runs.']];
    const sel = ST.findLane || 'REGISTRY';
    const card = ([k, n, s]) => `<button type="button" class="card choice" data-lane="${k}" aria-pressed="${k === sel}" style="text-align:left;display:flex;flex-direction:column;gap:6px;cursor:pointer;${k === sel ? 'border-color:var(--ink)' : ''}">
      <b>${esc(n)}</b><span class="mut" style="font-size:13px">${esc(s)}</span>${built[k] ? '<span class="pill ok" style="align-self:flex-start">Ready</span>' : '<span class="pill warn" style="align-self:flex-start">Not set up</span>'}</button>`;
    let form;
    if (sel === 'HER_DATA') form = `<p class="mut" style="margin:0">Attach your file in the chat (the + button, or drop it there). Hoola reads the columns (name, phone, city…), keeps one row per business and tells you what went in.</p><div><button class="btn sm" type="button" data-act="pick">Attach a CSV or Excel file</button></div>`;
    else if (sel === 'SCRAPE') form = `<p class="mut" style="margin:0">This reads public Google Maps listing pages one request a second. Businesses only, never behind a login, robots rules respected. Switch it on in Quality &amp; settings first; then ask in the chat.</p><div><a class="btn soft sm" href="#/quality">Open settings</a></div>`;
    else if (sel === 'VENDOR') form = `<p class="mut" style="margin:0">A paid seller is set up on the server (its name, price per row and a monthly limit). Ask in the chat once it is set up; the price is shown before anything runs.</p>`;
    else form = `<form id="ldFind" class="grid2" style="gap:14px">
        <label style="display:flex;flex-direction:column;gap:6px"><span class="mut" style="font-size:12.5px">What they sell or do</span><input class="in" name="term" required placeholder="${sel === 'REGISTRY' ? 'steel suppliers' : 'dentist'}"></label>
        <label style="display:flex;flex-direction:column;gap:6px"><span class="mut" style="font-size:12.5px">${sel === 'REGISTRY' ? 'City' : 'Near (city or area)'}</span><input class="in" name="city" required placeholder="Pune"></label>
        <label style="display:flex;flex-direction:column;gap:6px"><span class="mut" style="font-size:12.5px">Most businesses</span><input class="in" name="max" type="number" min="1" max="5000" value="${sel === 'REGISTRY' ? 200 : 50}"></label>
        ${sel === 'OFFICIAL_API' ? '<label style="display:flex;align-items:center;gap:8px;margin-top:22px"><input type="checkbox" name="details" checked> Buy phone + website for each (paid)</label>' : '<span></span>'}
      </form>
      <div class="card" style="background:var(--soft);display:flex;flex-direction:column;gap:8px"><b>The plan</b>
        <p class="mut" style="margin:0;font-size:13.5px">${sel === 'REGISTRY' ? 'IndiaMART is free.' : 'Google Maps place details are paid per business, under your Maps spending cap; the exact cost shows on the run.'} Left today: ${num(left)} rows. The same business found twice is kept once; an opted-out business is never brought back.</p>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-act="runfind">Start</button><button class="btn soft sm" type="button" data-act="savefind">Save this search${sel === 'REGISTRY' ? ' (weekly)' : ''}</button></div></div>`;
    const saved = (l.saved || []).map(x => `<div class="row"><div style="flex:1"><div class="t">${esc(x.name)}</div><div class="s">${esc(x.lane_name)}${x.weekly ? ' · runs every week' : ''}${x.last_run_at ? ` · last ${when(x.last_run_at)}, ${num(x.last_kept)} kept` : ' · not run yet'}</div></div>
      <button class="btn soft sm" type="button" data-runsaved="${esc(x.id)}">Run</button><button class="btn soft sm" type="button" data-dropsaved="${esc(x.id)}" aria-label="Remove ${esc(x.name)}">Remove</button></div>`).join('');
    return `${head('Find leads', 'Pick where to look. Each source says what it costs before anything runs.')}
      <div class="grid">${src.map(card).join('')}</div>
      ${sec(esc(src.find(x => x[0] === sel)[1]), form)}
      ${sec('Saved searches', saved || '<p class="mut" style="margin:0">None yet. Save a search above to run it again in one tap.</p>')}`;
  }

  async function paintLeads(box) {
    const f = ST.f, q = new URLSearchParams({stage: f.stage, q: f.q, city: f.city, lane: f.lane, has_phone: f.has_phone, due: f.due, limit: 100});
    const r = await api('GET', '/api/leads/desk/leads?' + q.toString());
    ST.pageData = r;
    const c = r.counts || {};
    const tabs = [['', 'All', c.all], ...STAGES.map(([k, n]) => [k, n, c[k]]), ['opted_out', 'Opted out', c.opted_out]]
      .map(([k, n, v]) => `<button type="button" class="btn ${f.stage === k ? '' : 'soft'} sm" data-stage="${k}">${esc(n)} ${num(v)}</button>`).join('');
    const rows = (r.rows || []).map(x => `<tr><td><input type="checkbox" data-sel="${esc(x.id)}" ${ST.sel.has(x.id) ? 'checked' : ''} ${x.opt_out ? 'disabled' : ''} aria-label="Select ${esc(x.name)}"></td>
      <td><a href="#/lead/${enc(x.id)}"><b>${esc(x.name)}</b></a><div class="mut" style="font-size:12.5px">${esc([x.category, x.rating ? `rating ${x.rating}${x.review_count ? ` (${x.review_count})` : ''}` : ''].filter(Boolean).join(' · '))}</div></td>
      <td>${x.phone ? esc(x.phone_shown) : '<span class="mut">No phone</span>'}</td><td>${esc(x.city || '–')}</td><td>${pill(x.stage, x.stage_name)}</td>
      <td>${x.follow_on ? esc(`Due ${when(x.follow_on)}`) : '<span class="mut">–</span>'}</td><td class="mut">${esc(x.source_name)}</td></tr>`).join('');
    const n = ST.sel.size;
    box.innerHTML = `${head('Leads', `${num(r.total)} match`, '<button class="btn soft sm" type="button" data-act="csv">Export CSV</button>')}
      <div style="display:flex;gap:6px;flex-wrap:wrap">${tabs}</div>
      <form id="ldFilter" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <input class="in" name="q" value="${esc(f.q)}" placeholder="Search name or category" aria-label="Search leads" style="flex:1 1 220px;width:auto">
        <input class="in" name="city" value="${esc(f.city)}" placeholder="City" aria-label="City" style="flex:0 1 160px;width:auto">
        <select class="in" name="lane" aria-label="Source" style="flex:0 1 180px;width:auto"><option value="">Any source</option>${[['HER_DATA', 'Your list'], ['REGISTRY', 'IndiaMART'], ['OFFICIAL_API', 'Google Maps'], ['SCRAPE', 'Public Maps listings'], ['VENDOR', 'Paid lead seller']].map(([k, v]) => `<option value="${k}" ${f.lane === k ? 'selected' : ''}>${v}</option>`).join('')}</select>
        <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" name="has_phone" ${f.has_phone ? 'checked' : ''}> Has phone</label>
        <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" name="due" ${f.due ? 'checked' : ''}> Follow-up due</label>
        <button class="btn soft sm" type="submit">Search</button></form>
      <section class="card" style="overflow-x:auto;padding:4px 16px">${rows ? `<table class="tb"><thead><tr><th><input type="checkbox" data-act="selall" aria-label="Select all shown"></th><th>Business</th><th>Phone</th><th>City</th><th>Stage</th><th>Next</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table>`
        : '<p class="mut" style="padding:14px 0;margin:0">No lead matches. Find some on Find leads, or attach your list in the chat.</p>'}</section>
      ${n ? `<div class="card" style="position:sticky;bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:var(--ink);color:var(--bg)"><b style="flex:1">${n} selected</b>
        <select class="in" id="ldBulkStage" aria-label="Set stage" style="width:auto">${STAGES.map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}</select>
        <button class="btn soft sm" type="button" data-act="bulkstage">Set stage</button>
        <input class="in" type="date" id="ldBulkDate" aria-label="Follow-up date" style="width:auto"><button class="btn soft sm" type="button" data-act="bulkfollow">Set follow-up</button>
        <button class="btn soft sm" type="button" data-act="handsel">Hand over…</button><button class="btn soft sm" type="button" data-act="clearsel">Clear</button></div>` : ''}
      <div id="ldHand"></div>`;
    if (ST.hand) $('#ldHand').innerHTML = ST.hand;
  }

  function pageLead(r) {
    const x = r.lead, tl = r.timeline || [];
    const kv = (k, v) => v ? `<dt class="mut">${esc(k)}</dt><dd style="margin:0">${v}</dd>` : '';
    const st = STAGES.map(([k, n]) => `<button type="button" class="btn ${x.stage === k ? '' : 'soft'} sm" data-setstage="${k}" ${x.opt_out ? 'disabled' : ''}>${esc(n)}</button>`).join('');
    return `<div><a class="btn soft sm" href="#/leads">← Leads</a></div>
      ${head(esc(x.name), esc([x.category, x.address || x.city, x.rating ? `rating ${x.rating}${x.review_count ? ` (${x.review_count} reviews)` : ''}` : ''].filter(Boolean).join(' · ')), pill(x.stage, x.stage_name))}
      <div style="display:flex;gap:6px;flex-wrap:wrap">${st}<button class="btn soft sm" type="button" data-ask="Write a short follow-up message for ${esc(x.name)}" ${x.opt_out ? 'disabled' : ''}>Draft a message</button><button class="btn soft sm" type="button" data-tele="${esc(x.id)}" ${x.opt_out || !x.phone ? 'disabled' : ''}>Hand to Telecaller</button></div>
      <div class="grid2">
        <div style="display:flex;flex-direction:column;gap:18px">
          ${sec('Follow-up', `<form id="ldFollow" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end"><label style="display:flex;flex-direction:column;gap:6px"><span class="mut" style="font-size:12.5px">Date</span><input class="in" type="date" name="on" value="${esc(x.follow_on || '')}" ${x.opt_out ? 'disabled' : ''}></label>
            <label style="display:flex;flex-direction:column;gap:6px;flex:1 1 200px"><span class="mut" style="font-size:12.5px">Why</span><input class="in" name="note" value="${esc(x.follow_note || '')}" placeholder="Call after Diwali" ${x.opt_out ? 'disabled' : ''}></label>
            <button class="btn sm" type="submit" ${x.opt_out ? 'disabled' : ''}>Save</button>${x.follow_on ? '<button class="btn soft sm" type="button" data-act="clearfollow">Clear</button>' : ''}</form>`)}
          ${sec('What happened', tl.map(e => `<div class="row"><span class="pill ${e.kind === 'note' ? 'v' : ''}"><span class="dt"></span></span><div style="flex:1;min-width:0"><div class="t">${esc(e.text)}</div><div class="s">${esc(when(e.at))}${e.by === 'hoola' ? ' · by Hoola' : ''}</div></div></div>`).join('') || '<p class="mut" style="margin:0">Nothing yet.</p>')}
          ${sec('Add a note', `<form id="ldNote" style="display:flex;flex-direction:column;gap:8px"><label for="ldNoteText" class="mut" style="font-size:12.5px">What did they say?</label><textarea class="in" id="ldNoteText" name="text" rows="2"></textarea><div><button class="btn sm" type="submit">Add note</button></div></form>`)}
        </div>
        <div style="display:flex;flex-direction:column;gap:18px">
          ${sec('Details', `<dl style="display:grid;grid-template-columns:110px 1fr;gap:8px 12px;margin:0">${kv('Phone', x.phone ? esc('+' + x.phone) : '<span class="mut">None found</span>')}${kv('Email', esc(x.email))}${kv('Website', x.website ? `<a href="${esc(/^https?:/i.test(x.website) ? x.website : 'https://' + x.website)}" target="_blank" rel="noopener noreferrer">${esc(x.website)}</a>` : '<span class="mut">None found</span>')}${kv('Address', esc(x.address))}${kv('City', esc(x.city))}${kv('Category', esc(x.category))}</dl>`)}
          ${sec('Where it came from', `<dl style="display:grid;grid-template-columns:110px 1fr;gap:8px 12px;margin:0">${kv('Source', esc(x.source_name))}${kv('Found', esc(when(x.found_at)))}${kv('Read from', esc(x.source_url))}${kv('Contact from', esc(x.enriched_from))}</dl>`)}
          ${sec('Privacy', `<p class="mut" style="margin:0;font-size:13.5px">They asked not to be contacted? Opt out keeps them out of every list, every draft and every send.</p><div style="display:flex;gap:8px;flex-wrap:wrap">${x.opt_out ? '<button class="btn soft sm" type="button" data-optin="1">Allow contact again</button>' : '<button class="btn soft sm" type="button" data-optout="1">Opt out</button>'}<button class="btn soft sm bad" type="button" data-forget="1">Forget this business</button></div>`)}
        </div></div>
      <div id="ldHand"></div>`;
  }

  function pageLists(l, out) {
    const lists = (l.lists || []).map(x => `<div class="row"><div style="flex:1"><div class="t">${esc(x.name)}</div><div class="s">${num(x.rows)} leads · made ${esc(when(x.made_at))}${x.sent ? ` · ${num(x.sent)} sent from the campaign desk` : ' · nothing sent yet'}</div></div><a class="btn soft sm" href="/console/?v=campaigns">Open campaign desk</a></div>`).join('');
    const smart = (l.smart || []).map(x => `<div class="row"><div style="flex:1"><div class="t">${esc(x.name)} leads</div><div class="s">${num(x.rows)} · fills itself from the stage</div></div><button class="btn soft sm" type="button" data-handstage="${esc(x.stage)}">Hand over…</button></div>`).join('');
    const ev = (out.events || []).slice(0, 20).map(v => `<div class="row"><div style="flex:1"><div class="t">${esc({campaign_list: 'Put in a campaign list', campaign_sent: 'WhatsApp sent', email_sent: 'Email sent'}[v.kind] || v.kind)} · ${esc(v.name || 'a removed business')}</div><div class="s">${esc(when(v.at))} · ${esc(v.desk || '')}</div></div></div>`).join('');
    return `${head('Lists', 'A list goes to the campaign desk or the Telecaller only after your two taps. The campaign desk still asks before it sends.')}
      ${sec('Lists by stage', smart || '<p class="mut" style="margin:0">Set stages on your leads and they gather here.</p>')}
      ${sec('Lists given to the campaign desk', lists || '<p class="mut" style="margin:0">None yet.</p>')}
      ${sec('Sent from these lists', ev || '<p class="mut" style="margin:0">Nothing has been sent. Every send is written here; a business that opted out is refused at send time.</p>')}
      <div id="ldHand"></div>`;
  }

  function pageQuality(q, o) {
    const blk = (n, title, sub, rows, act) => `<div class="row"><span class="pill ${n ? 'warn' : 'ok'}">${num(n)}</span><div style="flex:1;min-width:0"><div class="t">${esc(title)}</div><div class="s">${esc(sub)}</div>
      ${rows.length ? `<div class="s" style="margin-top:6px">${rows.slice(0, 8).map(x => `<a href="#/lead/${enc(x.id)}">${esc(x.name)}</a>`).join(' · ')}${rows.length > 8 ? ' …' : ''}</div>` : ''}</div>${n && act ? act : ''}</div>`;
    const pairs = (q.maybe_same || []).slice(0, 10).map(p => `<div class="row"><div style="flex:1"><div class="t">${esc(p.name)} · ${esc(p.city || '')}</div><div class="s">${p.leads.map(x => `<a href="#/lead/${enc(x.id)}">${esc(x.phone_shown || 'no phone')}</a> (${esc(x.source_name)})`).join(' · ')}</div></div></div>`).join('');
    const d = ST.d || {}, cur = Object.keys(TRUST).find(k => TRUST[k][0] === d.trust) || 'seekh', u = o.usage || {}, caps = o.caps || {};
    return `${head('Quality, sources and settings', '')}
      ${sec('Quality', blk(q.no_phone_count, 'No phone', 'Hoola can read their own websites for one, free.', q.no_phone || [], '<button class="btn soft sm" type="button" data-ask="Fill in the missing phones from their websites">Fill in</button>')
        + blk(q.dead_sites_count, 'Website did not open', 'Checked when the contact was filled in.', q.dead_sites || [])
        + blk(q.untouched_count, 'Not touched in 90 days', 'Still New three months after they were found.', q.untouched || [], '<button class="btn soft sm" type="button" data-ask="Which old untouched leads are worth a follow-up?">Ask</button>')
        + blk(q.maybe_same_count, 'Maybe the same business twice', 'Same name and city, different numbers. You decide; nothing is merged by itself.', []))}
      ${pairs ? sec('Check these pairs', pairs) : ''}
      ${sec('Sources', `<div class="row"><div style="flex:1"><div class="t">Public Maps listings scan</div><div class="s">Businesses only, never behind a login, one request a second, robots rules respected. Off until you switch it on.</div></div>
          <button class="btn ${d.scrape_on ? '' : 'soft'} sm" type="button" data-act="scrape" aria-pressed="${!!d.scrape_on}">${d.scrape_on ? 'On - switch off' : 'Off - switch on'}</button></div>
        <div class="row"><div style="flex:1"><div class="t">Limits</div><div class="s">${num(caps.per_run || 5000)} rows a search · ${num(u.per_day || caps.per_day || 20000)} a day · ${num(u.rows_kept)} kept today. A bigger ask is refused with the limit named.</div></div></div>`)}
      ${sec('How much it does on its own', `<div role="radiogroup" aria-label="Trust" style="display:flex;gap:6px;flex-wrap:wrap">${Object.entries(TRUST).map(([k, [n]]) => `<button type="button" class="btn ${k === cur ? '' : 'soft'} sm" role="radio" aria-checked="${k === cur}" data-trust="${k}">${esc(n)}</button>`).join('')}</div>
        <p class="mut" style="margin:0;font-size:13.5px">${esc(TRUST[cur][1])}</p>
        <div style="display:flex;gap:8px">${d.status === 'paused' ? '<button class="btn soft sm" type="button" data-emp="resume">Resume</button>' : '<button class="btn soft sm" type="button" data-emp="pause">Pause</button>'}<button class="btn soft sm bad" type="button" data-emp="leave">Let go</button></div>`)}
      ${sec('Forget', `<p class="mut" style="margin:0;font-size:13.5px">Removes businesses and their copies. The send log keeps its lines, shown as removed.</p><div><button class="btn soft sm bad" type="button" data-act="forgetall">Forget everything</button></div>`)}`;
  }

  /* ---------------------------------------------------------------- hand-over cards (two taps) */
  function handCard(target, c, body) {
    const where = target === 'tele' ? "the Telecaller's call list" : 'the WhatsApp campaign desk';
    return `<section class="card" style="border:2px solid var(--ink);display:flex;flex-direction:column;gap:10px;margin-top:4px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><b>Hand to ${esc(where)}</b><span class="pill">Tap 1 of 2 · nothing is built yet</span></div>
      <div class="grid"><div class="card kpi"><div class="v">${num(c.rows)}</div><div class="n">will go</div></div>
        <div class="card kpi"><div class="v">${num(c.rows_without_phone)}</div><div class="n">no phone, stay back</div></div>
        <div class="card kpi"><div class="v">${num(c.opt_out_excluded)}</div><div class="n">opted out, left out</div></div></div>
      <p class="mut" style="margin:0;font-size:13.5px">${target === 'tele' ? esc(c.say || '') : 'These are businesses, not your customers yet, so none has said yes to messages. The campaign desk uses your approved WhatsApp template and asks again before it sends.'}</p>
      ${target === 'camp' ? '<label style="display:flex;flex-direction:column;gap:6px"><span class="mut" style="font-size:12.5px">List name</span><input class="in" id="ldListName" value="Leads list"></label>' : ''}
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-confirm="${target}" data-body="${esc(JSON.stringify(body))}" ${c.rows ? '' : 'disabled'}>Confirm${target === 'tele' ? ', add to the call list' : ', build the list'}</button><button class="btn soft sm" type="button" data-act="cancelhand">Cancel</button></div></section>`;
  }
  async function startHand(body) {
    const pick = await chooseTarget(); if (!pick) return;
    try {
      const c = pick === 'tele' ? await api('POST', '/api/leads/desk/telecaller', body) : await api('POST', '/api/leads/campaign-list', {...body, name: 'Leads list'});
      ST.hand = handCard(pick, c, body);
      const box = $('#ldHand'); if (box) { box.innerHTML = ST.hand; box.scrollIntoView({block: 'nearest'}); }
    } catch (e) { toast(e.message, true); }
  }
  function chooseTarget() {
    return new Promise(res => {
      const box = $('#ldHand'); if (!box) { res(null); return; }
      box.innerHTML = `<section class="card" style="display:flex;flex-direction:column;gap:10px;margin-top:4px"><b>Where should this list go?</b>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn sm" type="button" data-t="camp">WhatsApp campaign desk</button><button class="btn soft sm" type="button" data-t="tele">Telecaller</button><button class="btn soft sm" type="button" data-t="">Cancel</button></div></section>`;
      box.querySelectorAll('[data-t]').forEach(b => b.addEventListener('click', ev => { ev.stopPropagation(); box.innerHTML = ''; res(b.dataset.t || null); }, {once: true}));
    });
  }

  /* ---------------------------------------------------------------- page actions */
  async function onPageClick(e) {
    const t = e.target;
    const g = sel => t.closest(sel);
    try {
      let b;
      if ((b = g('[data-ask]'))) { e.preventDefault(); if (ST.tab === 'lead' && ST.arg) setCtx(`the lead ${ST.arg}`); else if (b.dataset.lid) setCtx(`the lead ${b.dataset.lid}`); send(b.dataset.ask); return; }
      if ((b = g('[data-act="reload"]'))) { showPage(); return; }
      if ((b = g('[data-lane]'))) { ST.findLane = b.dataset.lane; showPage(true); return; }
      if ((b = g('[data-act="pick"]'))) { $('#adPick').click(); return; }
      if ((b = g('[data-act="runfind"]')) || (b = g('[data-act="savefind"]'))) { await findAction(b.dataset.act === 'savefind'); return; }
      if ((b = g('[data-runsaved]'))) { b.disabled = true; toast('Running the saved search…'); await api('POST', `/api/leads/desk/saved/${enc(b.dataset.runsaved)}/run`); toast('Done. New leads are in Leads.'); showPage(true); return; }
      if ((b = g('[data-dropsaved]'))) { if (!confirm('Remove this saved search? The leads it found stay.')) return; await api('DELETE', `/api/leads/desk/saved/${enc(b.dataset.dropsaved)}`); showPage(true); return; }
      if ((b = g('[data-stage]'))) { ST.f.stage = b.dataset.stage; ST.sel.clear(); ST.hand = null; showPage(true); return; }
      if ((b = g('[data-act="selall"]'))) { (ST.pageData?.rows || []).filter(x => !x.opt_out).forEach(x => b.checked ? ST.sel.add(x.id) : ST.sel.delete(x.id)); showPage(true); return; }
      if ((b = g('[data-act="clearsel"]'))) { ST.sel.clear(); ST.hand = null; showPage(true); return; }
      if ((b = g('[data-act="bulkstage"]'))) { const r = await api('POST', '/api/leads/desk/stage', {ids: [...ST.sel], stage: $('#ldBulkStage').value}); toast(`${r.changed} set to ${r.stage}.`); ST.sel.clear(); showPage(true); refreshDesk(false); return; }
      if ((b = g('[data-act="bulkfollow"]'))) { const on = $('#ldBulkDate').value; if (!on) { toast('Pick a date first.', true); return; } await api('POST', '/api/leads/desk/follow', {ids: [...ST.sel], on}); toast('Follow-up set.'); ST.sel.clear(); showPage(true); refreshDesk(false); return; }
      if ((b = g('[data-act="handsel"]'))) { await startHand({ids: [...ST.sel]}); return; }
      if ((b = g('[data-handstage]'))) { await startHand({stage: b.dataset.handstage}); return; }
      if ((b = g('[data-tele]'))) { ST.hand = null; const c = await api('POST', '/api/leads/desk/telecaller', {ids: [b.dataset.tele]}); ST.hand = handCard('tele', c, {ids: [b.dataset.tele]}); $('#ldHand').innerHTML = ST.hand; $('#ldHand').scrollIntoView({block: 'nearest'}); return; }
      if ((b = g('[data-act="cancelhand"]'))) { ST.hand = null; const h = $('#ldHand'); if (h) h.innerHTML = ''; return; }
      if ((b = g('[data-confirm]'))) {
        b.disabled = true;
        const body = JSON.parse(b.dataset.body || '{}');
        if (b.dataset.confirm === 'tele') { const r = await api('POST', '/api/leads/desk/telecaller', {...body, confirm: true}); toast(`${r.added} added to the Telecaller's call list. Nothing was called or sent.`); }
        else { const r = await api('POST', '/api/leads/campaign-list', {...body, name: ($('#ldListName')?.value || 'Leads list').trim(), confirm: true}); toast(`List built: ${r.rows} leads. Nothing was sent - send it from the campaign desk.`); }
        ST.hand = null; ST.sel.clear(); showPage(true); return;
      }
      if ((b = g('[data-done]'))) { await api('POST', '/api/leads/desk/follow', {ids: [b.dataset.done], on: ''}); toast('Follow-up cleared.'); refreshDesk(true); return; }
      if ((b = g('[data-setstage]'))) { await api('POST', '/api/leads/desk/stage', {ids: [ST.arg], stage: b.dataset.setstage}); toast('Stage saved.'); showPage(true); refreshDesk(false); return; }
      if ((b = g('[data-act="clearfollow"]'))) { await api('POST', '/api/leads/desk/follow', {ids: [ST.arg], on: ''}); showPage(true); refreshDesk(false); return; }
      if ((b = g('[data-optout]'))) { if (!confirm('Opt this business out? It will never be put in a list, drafted for or sent to.')) return; await api('POST', '/api/leads/opt-out', {contact_id: ST.arg, opt_out: true}); toast('Opted out.'); showPage(true); return; }
      if ((b = g('[data-optin]'))) { await api('POST', '/api/leads/opt-out', {contact_id: ST.arg, opt_out: false}); toast('They can be contacted again.'); showPage(true); return; }
      if ((b = g('[data-forget]'))) { if (!confirm('Forget this business completely? This cannot be undone.')) return; await api('POST', '/api/leads/forget', {row_ids: [ST.arg]}); toast('Forgotten.'); location.hash = '#/leads'; return; }
      if ((b = g('[data-act="forgetall"]'))) { if (!confirm('Forget EVERY lead in the store? This cannot be undone.')) return; const r = await api('POST', '/api/leads/forget', {all_rows: true}); toast(`Forgotten: ${r.deleted} leads.`); refreshDesk(true); return; }
      if ((b = g('[data-act="csv"]'))) { const f = ST.f, r = await api('POST', '/api/leads/export', {q: f.q, city: f.city, lane: f.lane, has_phone: f.has_phone});
        const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([r.csv || ''], {type: 'text/csv'})); a.download = r.filename || 'leads.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); return; }
      if ((b = g('[data-act="scrape"]'))) {
        const on = b.getAttribute('aria-pressed') !== 'true';
        if (on && !confirm('Switch on the public Maps listings scan? It reads public business listing pages one request a second, never behind a login, robots rules respected. Nothing is ever sent to anyone.')) return;
        await api('POST', '/api/leads/scrape-optin', {on}); toast(on ? 'Switched on.' : 'Switched off.'); await refreshDesk(true); return;
      }
      if ((b = g('[data-trust]'))) { await api('PUT', '/api/employees/leads/settings', {trust: b.dataset.trust}); toast('Saved.'); await refreshDesk(true); return; }
      if ((b = g('[data-emp]'))) {
        if (b.dataset.emp === 'leave' && !confirm('Let your Lead Generation employee go? Its desk closes. Your leads stay.')) return;
        await api('POST', `/api/employees/leads/${b.dataset.emp}`);
        if (b.dataset.emp === 'leave') { location.href = '/console/?v=hire'; return; }
        toast(b.dataset.emp === 'pause' ? 'Paused.' : 'Working again.'); await refreshDesk(true); return;
      }
    } catch (err) { toast(err.message, true); if (t.closest('button')) t.closest('button').disabled = false; }
  }
  function onPageChange(e) {
    const c = e.target.closest('[data-sel]');
    if (c) { c.checked ? ST.sel.add(c.dataset.sel) : ST.sel.delete(c.dataset.sel); ST.hand = null; showPage(true); }
  }
  document.addEventListener('submit', async e => {
    const f = e.target;
    if (!f.closest || !$('#ldPage')?.contains(f)) return;
    e.preventDefault();
    const fd = new FormData(f);
    try {
      if (f.id === 'ldFilter') { ST.f = {...ST.f, q: S(fd.get('q')).trim(), city: S(fd.get('city')).trim(), lane: S(fd.get('lane')), has_phone: fd.get('has_phone') === 'on', due: fd.get('due') === 'on'}; ST.sel.clear(); showPage(true); }
      if (f.id === 'ldFollow') { await api('POST', '/api/leads/desk/follow', {ids: [ST.arg], on: S(fd.get('on')), note: S(fd.get('note'))}); toast('Follow-up saved.'); showPage(true); refreshDesk(false); }
      if (f.id === 'ldNote') { await api('POST', '/api/leads/desk/note', {id: ST.arg, text: S(fd.get('text'))}); toast('Note added.'); showPage(true); }
      if (f.id === 'ldFind') await findAction(false);
    } catch (err) { toast(err.message, true); }
  });
  async function findAction(save) {
    const f = $('#ldFind'); if (!f) return;
    if (!f.reportValidity()) return;
    const fd = new FormData(f), lane = ST.findLane || 'REGISTRY', term = S(fd.get('term')).trim(), city = S(fd.get('city')).trim(), max = Number(fd.get('max') || 0) || undefined;
    if (save) {
      const weekly = lane === 'REGISTRY';
      await api('POST', '/api/leads/desk/saved', {name: `${term} · ${city}`, lane, weekly, params: lane === 'REGISTRY' ? {search_term: term, city, max_rows: max} : {kinds: [term], near: city, max_rows: max, details: fd.get('details') === 'on'}});
      toast(weekly ? 'Saved. It runs every week on IndiaMART (free) and only adds new businesses.' : 'Saved. Run it any time from Saved searches.');
      showPage(true); return;
    }
    if (lane === 'OFFICIAL_API' && fd.get('details') === 'on' && !confirm(`Search Google Maps for "${term}" near ${city}? Phone and website details are paid per business (up to ${max || 50}), under your Maps spending cap.`)) return;
    toast('Searching…');
    const r = lane === 'REGISTRY'
      ? await api('POST', '/api/leads/runs/indiamart', {ask: `${term} in ${city}`, search_term: term, city, max_rows: max})
      : await api('POST', '/api/leads/runs/places', {ask: `${term} near ${city}`, kinds: [term], near: city, details: fd.get('details') === 'on', max_rows: max});
    const run = r.run || {};
    toast(r.ok === false ? `Not run: ${(run.error || (r.plan && (r.plan.why || []).join('; ')) || 'refused')}` : `Done: ${run.kept || 0} kept of ${run.found || 0} found.`, r.ok === false);
    refreshDesk(false); location.hash = '#/today';
  }

  function starters() {
    const box = $('#sdStarters'); if (!box) return;
    box.innerHTML = (STARTERS[ST.tab] || STARTERS.today).map(q => `<button class="chip" type="button" data-q="${esc(q)}">${esc(q)}</button>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-q]'); if (!b) return;
      const q = b.dataset.q;
      if (ST.tab === 'lead' && ST.arg) setCtx(`the lead ${ST.arg}`);
      if (ST.tab === 'leads' && ST.sel.size) setCtx(`the ticked leads: ${[...ST.sel].join(', ')}`);
      send(q); };
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
    try { const r = await api('GET', '/api/leads/chat'); ST.chat = r.id; }
    catch (e) { toast(e.message, true); return; }
    await loadMsgs(true);
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
    const label = ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Working on your leads…';
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'ld' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
