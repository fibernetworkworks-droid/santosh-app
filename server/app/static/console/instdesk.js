/* INSTITUTION DESK - the Institution employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE
   INSTITUTION DESK"). A thin top bar, then the Institution chat (its own conversation, kind 'institution') beside the desk's pages: Today,
   Financial crime, Compliance, Risk, Audit, Governance, Drafts (+ one draft), Team & settings. The pages call /api/institution/do/<part>,
   which runs the F9 engine AS the person of the institution she is on the desk; maker-checker sits under every draft. Hoola files,
   freezes and reports nothing. Routes: #/<page>[/<arg>]. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', inst: '<path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>', book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
    pulse: '<path d="M3 12h4l2-6 4 12 2-6h6"/>', check: '<path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/>',
    gavel: '<path d="M14 4l6 6M11 7l6 6M8 10l5-5M13 15l-9 9"/><path d="M4 21h8"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['crime', 'Financial crime'], ['compliance', 'Compliance'], ['risk', 'Risk'], ['audit', 'Audit'],
    ['governance', 'Governance'], ['drafts', 'Drafts'], ['team', 'Team & settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Summarise the five areas', 'Which drafts wait for a check?'],
    crime: ['Explain this alert', 'Draft a report from the top alert', 'Are my monitoring rules sensible?'],
    compliance: ['Which obligations are overdue?', 'Check this promotion', 'What do the complaints show?'],
    risk: ['Which risks are over my appetite?', 'When is the next incident report due?', 'Which suppliers have no exit plan?'],
    audit: ['How big should my sample be?', 'Which journals look unusual?', 'What is the audit still waiting for?'],
    governance: ['Which board papers are missing?', 'What does the new round do to the cap table?', 'Any related-party transactions?'],
    drafts: ['What should a checker look for?', 'Why does this need two checkers?', 'Summarise this draft'],
    team: ['Who should hold the checker role?', 'How do I give someone access?', 'How long should we keep records?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [],
    am: null, ob: null, cm: null, rc: null, tp: null, md: null, ec: null, pb: null, sl: null, je: null, bd: null, ct: null, rp: null, wb: null,
    ds: null, dr: null, drFor: '', out: {}, df: 'waiting', sarFor: null, editRoles: '', linkFor: ''};
  try { ST.side = localStorage.getItem('hoola.institution.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.institution.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const ME = () => (ST.d && ST.d.me) || null;
  const cur = () => (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString();
  const ROLES = () => (ST.d && ST.d.roles) || {};
  const RN = r => ROLES()[r] || r;
  const KINDS = () => (ST.d && ST.d.kinds) || {};
  const KN = k => KINDS()[k] || k;
  const mdFix = t => S(t).replace(/([^\n])\n(- )/g, '$1\n\n$2');   // a list right under a line still renders as a list
  const KS = k => ({sar: 'SAR', return: 'Return', limit: 'Limit', board: 'Board'}[k] || KN(k));
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const hrs = h => { const a = Math.abs(h); return a >= 48 ? `${Math.round(a / 24)} days` : `${a.toFixed(a < 10 ? 1 : 0)} h`; };
  const holds = r => !!ME() && ME().roles.includes(r);
  const has = (...rs) => !!ME() && (ME().roles.includes('admin') || rs.some(r => ME().roles.includes(r)));
  const AREA = {crime: ['mlro', 'compliance', 'maker'], compliance: ['compliance'], risk: ['risk', 'compliance'], audit: ['audit'], governance: ['secretary']};
  const canArea = a => has(...AREA[a]);
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16)).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/institution/do/' + part, {workspace: W().id, ...(a || {})});
  const SSAY = {waiting: ['warn', 'Waiting for a check'], approved: ['ok', 'Approved'], rejected: ['bad', 'Rejected']};
  const stTag = s => `<span class="cs-tag ${(SSAY[s] || [''])[0]}">${esc((SSAY[s] || ['', s])[1])}</span>`;
  const initials = n => S(n).split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase();
  const ROLE_CLS = {admin: 'partner', checker: 'reviewer', maker: 'preparer', mlro: 'manager', compliance: 'manager', risk: 'manager', audit: 'manager', secretary: 'client', viewer: ''};
  const avatar = (n, roles) => `<span class="fm-av ${ROLE_CLS[(roles || [])[0]] || ''}" aria-hidden="true">${esc(initials(n))}</span>`;
  const chips = roles => (roles || []).map(r => `<span class="ins-role ${esc(r)}">${esc(RN(r))}</span>`).join('');
  const RULE_SAY = {structuring: 'Just under the cash threshold', pass_through: 'Money passed straight through', high_risk_country: 'High-risk country',
    spike: 'Far above the usual month', dormant_reactivated: 'Dormant account woke up', fan_in: 'Many senders into one account'};
  const RULE_FIELDS = [['cash_threshold', 'Cash threshold'], ['structuring_band_pct', 'Band under it (%)'], ['structuring_count', 'Deposits to alert'],
    ['structuring_days', 'Within days'], ['pass_through_pct', 'Passed through (%)'], ['pass_through_days', 'Within days (pass-through)'],
    ['pass_through_min', 'Smallest deposit checked'], ['high_risk_countries', 'High-risk countries (comma)'], ['high_risk_min', 'High-risk total from'],
    ['spike_multiple', 'Month x its average'], ['spike_min', 'Spike from'], ['dormant_days', 'Dormant after days'], ['dormant_min', 'Dormant wake-up from'],
    ['fan_in_senders', 'Senders to alert'], ['fan_in_days', 'Within days (senders)']];
  const AREAS = [['crime', 'Financial crime', 'shield'], ['compliance', 'Compliance', 'book'], ['risk', 'Risk', 'pulse'], ['audit', 'Audit', 'check'],
    ['governance', 'Governance', 'gavel']];

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/institution/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.inst, '')}</div>
        <h1 class="sd-h">Your Institution employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="insHire">Hire Institution</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#insHire').onclick = async () => { try { await api('POST', '/api/employees/institution_desk/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.inst, '')}</div>
          <div style="min-width:0"><div class="sd-name">Institution</div><div class="sd-site" id="insSite"></div></div>
          <span id="insState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="insBiz" aria-label="Institution" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Institution chat">
          <div class="sd-chathead"><div class="t"><b>Institution chat</b><span>Ask about an alert, a draft or a register - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="insFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="insPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Institution desk" id="sdTabs"></nav>
          <div id="insPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola prepares, screens and counts. Nothing is filed, frozen or reported here.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your institution…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#insPick').click()});
    $('#insPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.institution.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.institution.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/institution/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#insBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/institution/workspace', {workspace: e.target.value}); clearCache(); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#insPage').addEventListener('click', onPageClick);
    $('#insPage').addEventListener('submit', onSubmit);
    $('#insPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function clearCache() { for (const k of ['am', 'ob', 'cm', 'rc', 'tp', 'md', 'ec', 'pb', 'sl', 'je', 'bd', 'ct', 'rp', 'wb', 'ds', 'dr']) ST[k] = null; ST.drFor = ''; }
  function stateLine() {
    const d = ST.d, el = $('#insState'); if (!el) return;
    const w = W(), k = K(), me = ME(), fm = ((k.drafts || {}).for_me || []).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your institution'] : !me ? ['warn', 'Not linked yet']
      : fm ? ['warn', `${fm} waiting for your check`] : (k.needs || []).some(x => x.bad) ? ['warn', 'Something is late'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#insSite').textContent = w ? `${w.name} · ${cur()}${me ? ' · you are ' + me.name : ''}` : 'No institution yet';
    const sel = $('#insBiz');
    sel.innerHTML = (d.institutions || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.institutions || []).length < 2;
  }
  function paintTabs() {
    const k = K(), a = k.areas || {}, ok = !!(W() && ME());
    const n = ok ? {crime: (a.crime || {}).alerts || '', compliance: ((a.compliance || {}).overdue || []).length || '',
      risk: ((a.risk || {}).incidents_open || 0) + ((a.risk || {}).over || []).length || '', audit: ((a.audit || {}).pbc_late || []).length || '',
      governance: ((a.governance || {}).papers_missing || []).length + ((a.governance || {}).whistle_open || 0) || '', drafts: ((k.drafts || {}).for_me || []).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/institution/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { clearCache(); showPage(true); } else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#insPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    if (!ME()) { box.innerHTML = pNotLinked(); starters(); return; }
    const fn = {today: pToday, crime: pCrime, compliance: pCompliance, risk: pRisk, audit: pAudit, governance: pGovernance, drafts: pDrafts,
      team: pTeam}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    if (typeof html === 'string') box.innerHTML = html;
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  /* a part of the page that arrives later redraws it: what she was typing stays where it was */
  const fkey = (f, i) => `${f.dataset.form}|${f.dataset.reg || f.dataset.kind || f.dataset.target || f.dataset.case || f.dataset.i || ''}|${i}`;
  function typed(box) {
    const out = {map: {}, focus: null}, act = document.activeElement;
    box.querySelectorAll('form[data-form]').forEach((f, i) => {
      const k = fkey(f, 0), vals = {};
      f.querySelectorAll('input:not([type=file]), textarea, select').forEach((el, j) => {
        if (!el.name && !el.dataset.note) return;
        const id = (el.name || el.dataset.note) + '#' + j;
        if (el.type === 'checkbox' || el.type === 'radio') { if (el.checked !== el.defaultChecked) vals[id] = {c: el.checked}; }
        else if (el.value !== el.defaultValue && !(el.tagName === 'SELECT')) vals[id] = {v: el.value};
        else if (el.tagName === 'SELECT' && el.dataset.touched) vals[id] = {v: el.value};
        if (el === act) out.focus = [k, id, el.selectionStart];
      });
      if (Object.keys(vals).length) out.map[k] = vals;
    });
    box.querySelectorAll('input[data-note]').forEach(el => { if (el.value) out.map['note|' + el.dataset.note] = {v: el.value}; });
    return out;
  }
  function retype(box, kept) {
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = fkey(f, 0), vals = kept.map[k]; if (!vals && !(kept.focus && kept.focus[0] === k)) return;
      f.querySelectorAll('input:not([type=file]), textarea, select').forEach((el, j) => {
        if (!el.name && !el.dataset.note) return;
        const id = (el.name || el.dataset.note) + '#' + j, v = vals && vals[id];
        if (v) { if ('c' in v) el.checked = v.c; else { el.value = v.v; if (el.tagName === 'SELECT') el.dataset.touched = '1'; } }
        if (kept.focus && kept.focus[0] === k && kept.focus[1] === id) { el.focus(); try { if (kept.focus[2] !== null) el.setSelectionRange(kept.focus[2], kept.focus[2]); } catch {} }
      });
    });
    box.querySelectorAll('input[data-note]').forEach(el => { const v = kept.map['note|' + el.dataset.note]; if (v) el.value = v.v; });
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const err = r => r && r.error ? `<p class="cs-neg" style="margin:8px 0 0">${esc(r.error)}</p>` : '';
  const ro = area => canArea(area) ? '' : `<p class="cs-note">You read this part. Changing it needs the ${esc(AREA[area].map(RN).join(' or '))} role (an admin adds it on Team).</p>`;
  async function lazy(key, part, a) {
    if (ST[key] !== null && ST[key] !== undefined) return ST[key];
    ST[key] = false;
    try { ST[key] = await run(part, a); } catch (e) { ST[key] = {error: e.message}; }
    showPage(true);
    return ST[key];
  }
  const got = (key, part, a) => { if (ST[key] === null) { lazy(key, part, a); return null; } return ST[key] === false ? null : ST[key]; };
  function uploader(kind, title, hint, area) {
    if (!canArea(area)) return '';
    return `<form class="ins-drop" data-form="upload" data-kind="${esc(kind)}"><div class="t"><b>${esc(title)}</b><span class="mut">${esc(hint)}</span></div>
      <label class="btn soft sm">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" data-upfile="1" hidden></label></form>`;
  }

  function pSetup() {
    const R = ['maker', 'checker', 'mlro', 'compliance', 'risk', 'audit', 'secretary'];
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.inst, '')}</div>
      <div><h1 class="sd-h">Set up your institution</h1><p class="lead">Financial crime, compliance, risk, audit and governance in one desk, with maker-checker under every draft. Your named people decide; Hoola prepares and counts.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your institution</h2><div class="md-form">
        <div class="md-field"><label for="insS1">Name</label><input class="in" id="insS1" name="name" required maxlength="80" placeholder="Northgate Bank"></div>
        <div class="md-field"><label for="insS2">Your name (the first admin)</label><input class="in" id="insS2" name="admin" required maxlength="80"></div>
        <div class="md-field"><label for="insS3">Country (two letters)</label><input class="in" id="insS3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="insS4">Currency (three letters)</label><input class="in" id="insS4" name="currency" required maxlength="3" placeholder="GBP"></div>
      </div>
      <div class="cr-sub" style="margin-top:16px">Roles you also hold (you are always an admin)</div>
      <div class="ins-checks">${R.map(r => `<label class="ins-check"><input type="checkbox" name="roles" value="${r}"><span>${esc(RN(r))}</span></label>`).join('')}</div>
      <div class="md-acts"><span class="mut" style="font-size:13px">A draft needs a checker who did not make it, so add at least one more person next.</span><button class="btn" type="submit">Set up the institution</button></div></form>`;
  }
  function pNotLinked() {
    const ppl = (ST.d && ST.d.people) || [];
    if (ST.d && ST.d.is_owner && ppl.length) return `<div><h1 class="sd-h">Who are you on this desk?</h1><p class="lead">Pick your person of the institution. Everything you do here is done as that person, with that person's roles.</p></div>
      <div class="fm-people">${ppl.map(p => `<button class="fm-person" type="button" data-be="${esc(p.id)}">${avatar(p.name, p.roles)}<b>${esc(p.name)}</b><span class="mut">${esc(p.roles.map(RN).join(', '))}</span></button>`).join('')}</div>`;
    return `<section class="card"><h1 class="sd-h">You are not linked yet</h1><p class="lead">An admin of ${esc(W().name)} links your Hoola login to your person of the institution on the Team page. Then this desk opens as you.</p></section>`;
  }

  /* ---------------------------------------------------------------- today */
  function areaCard(key, name, icon) {
    const a = (K().areas || {})[key] || {};
    let line = '', facts = [], lvl = 'ok';
    if (key === 'crime') { line = a.tx ? `${num(a.alerts)} alert${a.alerts === 1 ? '' : 's'} on ${num(a.customers)} customer${a.customers === 1 ? '' : 's'}` : 'No transactions on file';
      facts = [pl(a.tx, 'transaction'), pl(a.sar_waiting, 'report') + ' waiting']; lvl = a.alerts ? 'warn' : a.tx ? 'ok' : 'idle'; }
    if (key === 'compliance') { line = (a.overdue || []).length ? `${a.overdue.length} obligation${a.overdue.length > 1 ? 's' : ''} overdue` : a.obligations ? 'Obligations up to date' : 'No obligations yet';
      facts = [pl(a.obligations, 'obligation'), pl(a.complaints, 'complaint')]; lvl = (a.overdue || []).length ? 'bad' : (a.gaps || []).length ? 'warn' : a.obligations ? 'ok' : 'idle'; }
    if (key === 'risk') { const o = (a.over || []).length; line = a.incidents_open ? `${a.incidents_open} incident${a.incidents_open > 1 ? 's' : ''} with reports open` : o ? `${o} risk${o > 1 ? 's' : ''} over appetite` : a.risks ? 'Within your appetite' : 'No risks scored yet';
      facts = [pl(a.risks, 'risk'), pl((a.models_overdue || []).length, 'model') + ' overdue']; lvl = a.incidents_open || o ? 'bad' : (a.critical_no_exit || []).length || (a.models_overdue || []).length ? 'warn' : a.risks ? 'ok' : 'idle'; }
    if (key === 'audit') { const out = (a.pbc_outstanding || []).length; line = out ? `${out} request${out > 1 ? 's' : ''} outstanding` : 'Nothing outstanding';
      facts = [pl(a.samples, 'sample'), pl(a.journals, 'journal')]; lvl = (a.pbc_late || []).length ? 'bad' : out ? 'warn' : a.samples || a.journals ? 'ok' : 'idle'; }
    if (key === 'governance') { const pm = (a.papers_missing || []).length; line = pm ? `${pm} board paper${pm > 1 ? 's' : ''} missing` : a.whistle_open ? `${a.whistle_open} whistleblowing case${a.whistle_open > 1 ? 's' : ''} open` : 'Board pack complete';
      facts = [pl(a.open_actions, 'open action'), pl(a.holders, 'shareholder')]; lvl = pm ? 'warn' : a.whistle_open ? 'warn' : 'ok'; }
    return `<button class="ins-area ${lvl}" type="button" data-go="${key}"><span class="ico">${svg(IC[icon], '')}</span><span class="t"><b>${esc(name)}</b><span class="ln">${esc(line)}</span>
      <span class="f">${facts.map(x => `<i>${esc(x)}</i>`).join('')}</span></span><span class="lv" aria-label="${esc(lvl)}"></span></button>`;
  }
  function flowBox(dr) {
    const tot = Math.max(1, (dr.waiting || 0) + (dr.approved || 0) + (dr.rejected || 0));
    const seg = (n, cls) => n ? `<i class="${cls}" style="flex:${n}"></i>` : '';
    return `<div class="ins-mc"><div class="ins-mcbar">${seg(dr.waiting, 'warn')}${seg(dr.approved, 'ok')}${seg(dr.rejected, 'bad')}${tot === 1 && !(dr.waiting || dr.approved || dr.rejected) ? '<i class="none" style="flex:1"></i>' : ''}</div>
      <div class="cs-legend"><span><i class="w"></i>Waiting ${esc(dr.waiting || 0)}</span><span><i class="sg"></i>Approved ${esc(dr.approved || 0)}</span><span><i class="sb"></i>Rejected ${esc(dr.rejected || 0)}</span></div></div>`;
  }
  function clockChip(c, i, j) {
    const cls = c.reported ? (c.late ? 'late done' : 'done') : c.hours_left < 0 ? 'bad' : c.hours_left <= 24 ? 'warn' : '';
    const say = c.reported ? `reported ${dt(c.reported)}${c.late ? ' (late)' : ''}` : c.hours_left < 0 ? `${hrs(c.hours_left)} late` : `${hrs(c.hours_left)} left`;
    return `<div class="ins-clock ${cls}"><b>${esc(c.report)}</b><span>due ${esc(dt(c.due))}</span><em>${esc(say)}</em>${!c.reported && has('risk', 'compliance') && i !== undefined
      ? `<button class="btn soft sm" type="button" data-reported="${esc(i)}" data-rep="${esc(c.report)}">Mark reported now</button>` : ''}</div>`;
  }
  function pToday() {
    const k = K(), me = ME(), dr = k.drafts || {}, a = k.areas || {}, cr = a.crime || {}, co = a.compliance || {};
    const open = (k.incidents || []).flatMap(i => i.clocks.filter(c => !c.reported)).sort((x, y) => x.hours_left - y.hours_left);
    const fm = dr.for_me || [];
    const lead = fm.length ? `${fm.length} draft${fm.length > 1 ? 's' : ''} ${fm.length > 1 ? 'wait' : 'waits'} for your check.` : (k.needs || []).length ? `${(k.needs || []).length} thing${k.needs.length > 1 ? 's' : ''} on the desk need attention.` : 'Nothing is waiting on you.';
    const rules = Object.entries(cr.by_rule || {}).sort((x, y) => y[1] - x[1]), rmax = Math.max(1, ...rules.map(x => x[1]));
    return `<div><h1 class="sd-h">${greet()}, ${esc(S(me.name).split(' ')[0])}</h1><p class="lead">${esc(lead)} You are ${esc(me.roles.map(RN).join(', '))}.</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k${fm.length ? ' low' : ''}"><div class="l">Waiting for your check</div><div class="v">${esc(fm.length)}</div><div class="s">${esc(dr.waiting || 0)} waiting in all</div></div>
        <div class="k${cr.alerts ? ' low' : ''}"><div class="l">Monitoring alerts</div><div class="v">${esc(num(cr.alerts || 0))}</div><div class="s">${cr.tx ? `on ${esc(num(cr.tx))} transactions` : 'no transactions yet'}</div></div>
        <div class="k${(co.overdue || []).length ? ' low bad' : ''}"><div class="l">Obligations overdue</div><div class="v">${esc((co.overdue || []).length)}</div><div class="s">of ${esc(co.obligations || 0)} in your register</div></div>
        <div class="k${open.length && open[0].hours_left < 0 ? ' low bad' : open.length ? ' low' : ''}"><div class="l">Incident reports due</div><div class="v">${esc(open.length)}</div><div class="s">${open.length ? (open[0].hours_left < 0 ? 'one is late' : `next in ${esc(hrs(open[0].hours_left))}`) : 'none open'}</div></div></div></section>
      <div class="ins-areas">${AREAS.map(([k2, n, i]) => areaCard(k2, n, i)).join('')}</div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Maker-checker</h2><div class="r"><button class="btn soft sm" type="button" data-go="drafts">All drafts</button></div></div>
          ${flowBox(dr)}
          <div class="cr-sub" style="margin-top:14px">Waiting for your check</div>
          ${fm.map(d => `<div class="cs-row" data-go="drafts/${esc(d.id)}" style="cursor:pointer"><span class="fm-kind">${esc(KS(d.kind))}</span><span style="flex:1;min-width:0"><b>${esc(d.title || KN(d.kind))}</b><div class="mut" style="font-size:12.5px">made by ${esc(d.maker_name)} · ${esc(d.approvals)} of ${esc(pl(d.needs_checks, 'check'))}</div></span><span class="cs-tag warn">Check</span></div>`).join('') || empty(holds('checker') ? 'Nothing for you to check.' : 'You do not hold the checker role.')}</section>
      </div>
      ${(k.incidents || []).length || rules.length ? `<div class="md-2" style="align-items:start">
        ${(k.incidents || []).length ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Incident report clocks</h2><div class="r"><button class="btn soft sm" type="button" data-go="risk">Risk</button></div></div>
          ${(k.incidents || []).slice(0, 3).map(i => `<div class="ins-inc"><div class="h"><b>${esc(i.title)}</b>${i.severity ? `<span class="cs-tag">${esc(i.severity)}</span>` : ''}<span class="mut">found ${esc(dt(i.detected))}</span></div><div class="ins-clocks">${i.clocks.map(c => clockChip(c)).join('')}</div></div>`).join('')}</section>` : '<div></div>'}
        ${rules.length ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Alerts by rule</h2><div class="r"><button class="btn soft sm" type="button" data-go="crime">Financial crime</button></div></div>
          <div class="ins-hbars">${rules.map(([r, n]) => `<div><span>${esc(RULE_SAY[r] || r)}</span><i><b style="width:${(n / rmax * 100).toFixed(1)}%"></b></i><em>${esc(n)}</em></div>`).join('')}</div></section>` : ''}</div>` : ''}`;
  }

  /* ---------------------------------------------------------------- financial crime */
  function pCrime() {
    const k = K(), am = got('am', 'aml'), c = k.counts || {}, rules = k.rules || {}, def = k.rule_defaults || {};
    const yours = new Set(Object.keys(rules));
    const alerts = (am && am.alerts) || [];
    const rf = RULE_FIELDS.map(([key, l]) => { const v = key in rules ? rules[key] : def[key]; const sv = Array.isArray(v) ? v.join(', ') : S(v);
      return `<label class="ins-rule${yours.has(key) ? ' yours' : ''}"><span>${esc(l)}</span><input class="in" name="${esc(key)}" value="${esc(sv)}" ${key === 'high_risk_countries' ? 'placeholder="IR, KP"' : 'inputmode="decimal"'}${canArea('crime') ? '' : ' disabled'}><em>${yours.has(key) ? 'yours' : "Hoola's starting value - check this"}</em></label>`; }).join('');
    const sar = ST.out.sar;
    return `<div><h1 class="sd-h">Financial crime</h1><p class="lead">Your transactions checked against YOUR rules. Each alert is a signal for an analyst, not a finding. A report goes into maker-checker and the MLRO decides whether to file it - Hoola files nothing.</p></div>
      ${ro('crime')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Transactions</h2><div class="r">${c.tx && canArea('crime') ? `<button class="btn soft sm" type="button" data-clear="tx">Clear</button>` : ''}</div></div>
        <p class="mut" style="margin:6px 0 12px;font-size:14px">${c.tx ? `${esc(num(c.tx))} transactions on file.` : 'No transactions yet.'} Columns: id, customer, date, amount, direction (in / out), channel (cash, wire, card, transfer), country, counterparty.</p>
        ${uploader('transactions', 'Upload transactions', 'A CSV from your core system - up to 20,000 rows, replaces the last file', 'crime')}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Alerts</h2><div class="r">${am && !am.empty && !am.error ? `<span class="cs-tag">${esc(num(am.transactions))} checked</span>` : ''}</div></div>
        ${err(am)}${!am ? loading() : am.empty ? empty('Upload transactions to see alerts.') : ''}
        ${alerts.map((x, i) => `<div class="ins-alert${ST.sarFor === i ? ' open' : ''}"><div class="h"><span class="ins-rtag ${esc(x.rule)}">${esc(RULE_SAY[x.rule] || x.rule)}</span><b>${esc(x.customer)}</b>${x.rules_on_customer > 1 ? `<span class="cs-tag bad">${esc(x.rules_on_customer)} rules on this customer</span>` : ''}<span class="mut">${esc(x.count)} transaction${x.count > 1 ? 's' : ''}</span>
          <span class="r"><button class="btn soft sm" type="button" data-ask="${esc(`Alert ${x.rule} on customer ${x.customer}: ${x.why}`)}">Ask</button>${ST.sarFor === i ? '' : `<button class="btn sm" type="button" data-sar="${i}">Draft a report</button>`}</span></div>
          <div class="why">${esc(x.why)}</div>
          ${ST.sarFor === i ? `<form data-form="sar" data-i="${i}" class="ins-sarf"><div class="cr-grid">
            <input class="in" name="name" placeholder="Customer name" maxlength="80" aria-label="Customer name"><input class="in" name="occupation" placeholder="Occupation" maxlength="80" aria-label="Occupation">
            <input class="in" name="declared_income" placeholder="Declared income" maxlength="40" aria-label="Declared income"><input class="in wide" name="expected_activity" placeholder="Expected activity on file (e.g. salary, small card spend)" maxlength="200" aria-label="Expected activity">
            <textarea class="in wide" name="actions_taken" rows="2" placeholder="What was done: contact, review, restrictions" aria-label="What was done"></textarea></div>
            <div class="md-acts"><span class="mut" style="font-size:13px">${holds('maker') ? 'It goes into maker-checker as your draft.' : 'You are not a maker: you get a preview only.'} No accusation words; the analyst's assessment is left for a person.</span><span style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-sar="">Cancel</button><button class="btn" type="submit">Draft the report</button></span></div></form>` : ''}</div>`).join('')}
        ${am && !am.empty && !am.error && !alerts.length ? empty('No alert on these transactions with your rules.') : ''}
        ${sar ? `<div class="ins-sar"><div class="cs-head"><b>${sar.error ? 'Could not draft' : sar.draft ? 'Report drafted - waiting for a check' : 'Report preview'}</b><div class="r">${sar.draft ? `<button class="btn sm" type="button" data-go="drafts/${esc(sar.draft.id)}">Open the draft</button>` : ''}<button class="btn soft sm" type="button" data-closeout="sar">Close</button></div></div>
          ${err(sar)}${sar.checks ? `<div class="ins-checksum ${sar.checks.ok ? 'ok' : 'bad'}">${sar.checks.ok ? 'Machine checks passed: every amount and date is from the transactions, every part is there, no accusing words.' : esc(sar.checks.problems.join('; '))}</div>` : ''}
          ${sar.body ? `<div class="textmd ins-doc">${window.HoolaMD ? HoolaMD.render(mdFix(sar.body), false) : `<pre>${esc(sar.body)}</pre>`}</div>` : ''}</div>` : ''}</section>
      <section class="card"><h2 class="md-h2">Your monitoring rules</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Every alert uses these numbers. A value you set is marked yours; the rest are Hoola's starting values, not confirmed for your institution.</p>
        <form data-form="rules"><div class="ins-rules">${rf}</div>${canArea('crime') ? `<div class="md-acts"><span class="mut" style="font-size:13px">Leave a box as it is to keep Hoola's value.</span><button class="btn" type="submit">Save my rules</button></div>` : ''}</form></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Sanctions screening</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Names checked against YOUR watch list (Hoola keeps no list of its own). A score is name similarity, not identity.</p>
          <div class="cr-sub">Your watch list · ${esc((k.watch || []).length || c.watch || 0)}</div>
          ${(k.watch || []).map(w => `<div class="cs-row"><span style="flex:1"><b>${esc(w.name)}</b> <span class="mut">${esc(w.list || '')}${w.ref ? ' · ' + esc(w.ref) : ''}</span></span>${canArea('crime') ? `<button class="ib" type="button" aria-label="Remove ${esc(w.name)}" data-rmreg="watch" data-n="${esc(w.n)}">×</button>` : ''}</div>`).join('') || empty('No names on your watch list yet.')}
          ${canArea('crime') ? `<form data-form="reg" data-reg="watch" class="cr-grid"><input class="in" name="name" placeholder="Name" required maxlength="120" aria-label="Name"><input class="in" name="list" placeholder="List (e.g. UK, OFAC)" maxlength="60" aria-label="List"><button class="btn soft" type="submit">Add</button></form>` : ''}
          <form data-form="screen" style="margin-top:14px"><textarea class="in" name="names" rows="3" placeholder="Names to screen, one a line" style="width:100%" aria-label="Names to screen"></textarea>
            <div class="md-acts"><label class="mut" style="font-size:13px;display:flex;gap:6px;align-items:center">Threshold <input class="in sm" name="threshold" value="0.7" style="width:70px" aria-label="Threshold"></label><button class="btn" type="submit">Screen</button></div></form>
          ${ST.out.sn ? `<div class="fm-out">${err(ST.out.sn)}${(ST.out.sn.results || []).map(r => `<div class="cs-row" style="align-items:flex-start"><span style="flex:1"><b>${esc(r.name)}</b>${r.possible_matches.length ? r.possible_matches.map(m => `<div class="ins-match"><span>${esc(m.watch_name)} <span class="mut">${esc(m.list || '')}</span></span><i><b style="width:${(m.score * 100).toFixed(0)}%"></b></i><em>${esc(m.score)}</em></div>`).join('') : '<div class="mut" style="font-size:13px">No possible match.</div>'}</span></div>`).join('')}
            ${ST.out.sn.not_checked ? `<p class="cs-note">${esc(ST.out.sn.not_checked)} ${esc(ST.out.sn.decider || '')}</p>` : ''}</div>` : ''}</section>
        <section class="card"><h2 class="md-h2">Customer file review</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Documents present and in date, and a risk rating from YOUR factor weights.</p>
          <form data-form="kyc"><div class="md-form" style="grid-template-columns:minmax(0,1fr)">
            <div class="md-field"><label for="insK1">Documents needed (comma)</label><input class="in" id="insK1" name="required" value="identity, address, source of funds"></div>
            <div class="md-field"><label for="insK2">Documents on file: kind, expires (one a line)</label><textarea class="in" id="insK2" name="documents" rows="3" placeholder="identity, 2027-05-01&#10;address"></textarea></div>
            <div class="md-field"><label for="insK3">Risk factors: factor, weight, yes or no (one a line)</label><textarea class="in" id="insK3" name="factors" rows="3" placeholder="pep, 4, no&#10;high risk country, 3, yes&#10;cash business, 2, yes"></textarea></div></div>
            <div class="md-acts"><span class="mut" style="font-size:13px">Bands: low 0, medium 3, high 6 - unless you give your own in the chat.</span><button class="btn" type="submit">Review the file</button></div></form>
          ${ST.out.kyc ? `<div class="fm-out">${err(ST.out.kyc)}${ST.out.kyc.rating ? `<div class="cr-grid" style="margin-top:6px">${kpi('Rating', esc(cap(ST.out.kyc.rating)), `score ${ST.out.kyc.risk_score}`, ST.out.kyc.rating === 'high' ? 'bad' : '')}${kpi('Next review', esc(dmy(ST.out.kyc.next_review)), '')}${kpi('Missing / expired', esc(ST.out.kyc.missing.length + ST.out.kyc.expired.length), [...ST.out.kyc.missing, ...ST.out.kyc.expired.map(x => x + ' (expired)')].join(', '), ST.out.kyc.missing.length + ST.out.kyc.expired.length ? 'bad' : 'ok')}</div><p class="cs-note">${esc(ST.out.kyc.says || '')}</p>` : ''}</div>` : ''}</section>
      </div>`;
  }

  /* ---------------------------------------------------------------- compliance */
  function pCompliance() {
    const k = K(), ob = got('ob', 'obligations'), cm = got('cm', 'complaints');
    const rows = (ob && ob.obligations) || [];
    const late = rows.filter(o => o.overdue).length, okn = rows.length - late;
    const pol = ST.out.pol, pro = ST.out.pro;
    const cats = cm && cm.by_category ? Object.entries(cm.by_category).sort((a, b) => b[1].count - a[1].count) : [];
    const cmax = Math.max(1, ...cats.map(x => x[1].count));
    return `<div><h1 class="sd-h">Compliance</h1><p class="lead">Your obligation register with the rule each one comes from, what is due, your complaints against your deadline, and quick checks of a policy or a financial promotion.</p></div>
      ${ro('compliance')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Obligations</h2><div class="r">${rows.length ? `<span class="cs-tag ok">${esc(okn)} in date</span>${late ? `<span class="cs-tag bad">${esc(late)} overdue</span>` : ''}` : ''}</div></div>
        ${err(ob)}${!ob ? loading() : ''}
        ${rows.length ? `<div class="scroll"><table class="tb"><thead><tr><th>Obligation</th><th>From</th><th>Owner · control</th><th>Every</th><th>Last done</th><th>Due</th><th></th></tr></thead><tbody>
          ${rows.map((o, i) => `<tr><td><b>${esc(o.name)}</b>${o.overdue ? '<span class="cs-tag bad">Overdue</span>' : ''}${o.no_owner ? '<span class="cs-tag warn">No owner</span>' : ''}${o.no_control ? '<span class="cs-tag warn">No control</span>' : ''}</td>
            <td class="mut">${esc(o.source)}</td><td>${esc(o.owner || '—')}<div class="mut" style="font-size:12.5px">${esc(o.control || '')}</div></td><td class="nw">${esc(o.every_days)} days</td>
            <td class="nw">${esc(dmy(o.last_done))}</td><td class="nw ${o.overdue ? 'cs-neg' : ''}">${esc(dmy(o.due))}</td>
            <td>${has('compliance') ? `<button class="btn soft sm" type="button" data-obdone="${i}">Done today</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : ob && !ob.error ? empty('No obligations yet. Each one needs the rule it comes from.') : ''}
        ${has('compliance') ? `<form data-form="ob" class="fm-draftform"><div class="cr-sub" style="margin-top:12px">Add an obligation</div><div class="cr-grid">
          <input class="in" name="name" placeholder="What (e.g. AML policy review)" required maxlength="120" aria-label="Obligation">
          <input class="in" name="source" placeholder="The rule it comes from (needed)" required maxlength="160" aria-label="Source">
          <input class="in" name="owner" placeholder="Owner" maxlength="80" aria-label="Owner"><input class="in" name="control" placeholder="The control that meets it" maxlength="160" aria-label="Control">
          <input class="in" name="every_days" type="number" min="1" value="365" aria-label="Every how many days"><label class="ins-lab">Last done<input class="in" type="date" name="last_done"></label>
          </div><div class="md-acts"><span class="mut" style="font-size:13px">The register is only as good as its sources.</span><button class="btn" type="submit">Add</button></div></form>` : ''}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Complaints</h2><div class="r">${(k.counts || {}).complaints && canArea('compliance') ? `<button class="btn soft sm" type="button" data-clear="complaints">Clear</button>` : ''}</div></div>
        ${uploader('complaints', 'Upload complaints', 'Columns: category, received, closed, upheld (yes / no)', 'compliance')}
        ${err(cm)}${cm && !cm.empty && !cm.error ? `<div class="md-3" style="margin-top:14px">${kpi('Complaints', esc(cm.total), '')}${kpi('Upheld', cm.upheld_pct === null ? '—' : esc(cm.upheld_pct) + '%', '')}${kpi('Answered late', esc(cm.late), `deadline ${cm.deadline_days} days`, cm.late ? 'bad' : 'ok')}</div>
          <div class="ins-hbars" style="margin-top:14px">${cats.map(([n, v]) => `<div><span>${esc(cap(n))}</span><i><b style="width:${(v.count / cmax * 100).toFixed(1)}%"></b></i><em>${esc(v.count)}${v.late ? ` · ${v.late} late` : ''}</em></div>`).join('')}</div>
          <p class="cs-note">Median ${cm.median_days === null ? '—' : esc(cm.median_days) + ' days'} to close.</p>` : cm && cm.empty ? empty('No complaints uploaded yet.') : ''}
        ${canArea('compliance') ? `<form data-form="deadline" class="cr-filter" style="margin-top:10px"><label class="mut" style="font-size:13px;display:flex;gap:8px;align-items:center">Your response deadline (days) <input class="in sm" name="deadline_days" type="number" min="1" value="${esc(k.deadline_days || '')}" placeholder="56" style="width:90px"></label><button class="btn soft sm" type="submit">Save</button>${k.deadline_days ? '' : '<span class="cs-tag warn">Hoola\'s 56 days - check this</span>'}</form>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Check a policy</h2><form data-form="policy"><textarea class="in" name="text" rows="6" placeholder="Paste the policy (with its headings)" style="width:100%" required aria-label="Policy text"></textarea>
          <input class="in" name="required_sections" value="purpose, scope, roles, procedure, review, approval" style="width:100%;margin-top:8px" aria-label="Sections it needs">
          <div class="md-acts"><span class="mut" style="font-size:13px">Sections it needs (comma).</span><button class="btn" type="submit">Check</button></div></form>
          ${pol ? `<div class="fm-out">${err(pol)}${pol.missing_sections ? `<div class="ins-checksum ${pol.ok ? 'ok' : 'bad'}">${pol.ok ? 'Every section is there, an owner is named and a review date is set.' : 'Not complete yet.'}</div>
            <div class="cs-row"><span style="flex:1">Missing sections</span><b>${esc(pol.missing_sections.join(', ') || 'none')}</b></div><div class="cs-row"><span style="flex:1">Owner named</span><b>${pol.owner_named ? 'Yes' : 'No'}</b></div><div class="cs-row"><span style="flex:1">Next review</span><b>${esc(pol.review_date ? dmy(pol.review_date) : 'not set')}</b></div>` : ''}</div>` : ''}</section>
        <section class="card"><h2 class="md-h2">Check a financial promotion</h2><form data-form="promo"><textarea class="in" name="text" rows="6" placeholder="Paste the advert, email or post" style="width:100%" required aria-label="Promotion text"></textarea>
          <input class="in" name="banned_words" placeholder="Your banned words (comma)" style="width:100%;margin-top:8px" aria-label="Banned words">
          <div class="md-acts"><span class="mut" style="font-size:13px">Hoola's general checks; your rulebook decides.</span><button class="btn" type="submit">Check</button></div></form>
          ${pro ? `<div class="fm-out">${err(pro)}${pro.problems ? `<div class="ins-checksum ${pro.ok ? 'ok' : 'bad'}">${pro.ok ? 'No problem found by these checks.' : `${pro.problems.length} problem${pro.problems.length > 1 ? 's' : ''} found`}</div>${pro.problems.map(p => `<div class="cs-row"><span class="cs-dot bad"></span><span>${esc(cap(p))}</span></div>`).join('')}<p class="cs-note">${esc(pro.rules_from || '')}</p>` : ''}</div>` : ''}</section>
      </div>`;
  }

  /* ---------------------------------------------------------------- risk */
  function heat(rc, app) {
    const cnt = Array.from({length: 5}, () => Array(5).fill(0));
    for (const r of rc.risks || []) cnt[r.impact - 1][r.likelihood - 1] += 1;
    let g = '';
    for (let im = 5; im >= 1; im--) {
      g += `<span class="ax">${im}</span>`;
      for (let li = 1; li <= 5; li++) { const s = im * li, n = cnt[im - 1][li - 1];
        g += `<div class="c ${s > app ? 'hi' : s > app * 0.6 ? 'md' : 'lo'}${n ? ' has' : ''}" title="Likelihood ${li} x impact ${im} = ${s}${n ? `: ${n} risk${n > 1 ? 's' : ''}` : ''}">${n ? `<b>${n}</b>` : ''}</div>`; }
    }
    g += '<span></span>' + [1, 2, 3, 4, 5].map(x => `<span class="ax">${x}</span>`).join('');
    return `<div class="ins-heatw"><div class="ins-yl">Impact</div><div class="ins-heat">${g}</div><div class="ins-xl">Likelihood</div></div>`;
  }
  function pRisk() {
    const k = K(), rc = got('rc', 'rcsa'), tp = got('tp', 'third_party'), md = got('md', 'models'), ec = got('ec', 'ecl');
    const inc = k.incidents || [], cl = k.clocks || [], app = k.appetite || 12;
    const stages = ec && ec.by_stage ? ec.by_stage : null, stot = stages ? Math.max(1, ...Object.values(stages)) : 1;
    return `<div><h1 class="sd-h">Risk</h1><p class="lead">Incidents and their reporting clocks from your regulator's hours, your risks against your appetite, your third parties and models, and the ECL working paper.</p></div>
      ${ro('risk')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Incidents</h2><div class="r">${k.clocks_yours ? '<span class="cs-tag ok">Your clocks</span>' : '<span class="cs-tag warn">Hoola\'s starting clocks - check this</span>'}</div></div>
        ${inc.map(i => `<div class="ins-inc"><div class="h"><b>${esc(i.title)}</b>${i.severity ? `<span class="cs-tag ${i.severity === 'high' ? 'bad' : ''}">${esc(i.severity)}</span>` : ''}${i.closed ? '<span class="cs-tag ok">All reported</span>' : ''}<span class="mut">found ${esc(dt(i.detected))}</span></div>
          <div class="ins-clocks">${i.clocks.map(c => clockChip(c, i.n)).join('')}</div></div>`).join('') || empty('No incidents logged.')}
        ${has('risk', 'compliance') ? `<form data-form="incident" class="fm-draftform"><div class="cr-sub" style="margin-top:12px">Log an incident</div><div class="cr-grid">
          <input class="in" name="title" placeholder="What happened" required maxlength="160" aria-label="What happened"><label class="ins-lab">Found at<input class="in" type="datetime-local" name="detected" required value="${esc(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))}"></label>
          <select class="in" name="severity" aria-label="Severity"><option value="high">High</option><option value="medium" selected>Medium</option><option value="low">Low</option></select></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Clocks: ${esc(cl.map(c => `${c.report} ${c.hours} h`).join(' · '))}. Hoola reports nothing - you mark when you did.</span><button class="btn" type="submit">Log it</button></div></form>
          <details class="ins-more"><summary>Your report clocks</summary><form data-form="clocks"><textarea class="in" name="clocks" rows="3" style="width:100%" aria-label="Clocks">${esc(cl.map(c => `${c.report}, ${c.hours}`).join('\n'))}</textarea>
            <div class="md-acts"><span class="mut" style="font-size:13px">One a line: the report, the hours after it was found (from your regulator's rules).</span><button class="btn soft sm" type="submit">Save clocks</button></div></form></details>` : ''}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Risk and control self-assessment</h2><div class="r">${rc && rc.over_appetite && rc.over_appetite.length ? `<span class="cs-tag bad">${esc(rc.over_appetite.length)} over appetite</span>` : ''}</div></div>
        ${err(rc)}${!rc ? loading() : ''}
        <div class="ins-rcsa">${rc && !rc.error ? heat(rc, app) : ''}
          <div style="min-width:0;flex:1">${rc && rc.risks && rc.risks.length ? rc.risks.map(r => `<div class="cs-row"><span class="ins-score ${r.over_appetite ? 'bad' : r.residual > app * 0.6 ? 'warn' : 'ok'}">${esc(r.residual)}</span><span style="flex:1;min-width:0"><b>${esc(r.risk)}</b><div class="mut" style="font-size:12.5px">likelihood ${esc(r.likelihood)} x impact ${esc(r.impact)} = ${esc(r.inherent)} inherent${r.owner ? ' · ' + esc(r.owner) : ''}${r.control ? ' · ' + esc(r.control) : ''}</div></span>${r.over_appetite ? '<span class="cs-tag bad">Over appetite</span>' : ''}${canArea('risk') ? `<button class="ib" type="button" aria-label="Remove ${esc(r.risk)}" data-rmreg="risks" data-n="${esc(r.n)}">×</button>` : ''}</div>`).join('') : rc ? empty('No risks scored yet.') : ''}</div></div>
        ${canArea('risk') ? `<form data-form="reg" data-reg="risks" class="fm-draftform"><div class="cr-sub" style="margin-top:12px">Add a risk</div><div class="cr-grid">
          <input class="in" name="name" placeholder="The risk" required maxlength="120" aria-label="Risk"><label class="ins-lab">Likelihood 1-5<input class="in" name="likelihood" type="number" min="1" max="5" required value="3"></label><label class="ins-lab">Impact 1-5<input class="in" name="impact" type="number" min="1" max="5" required value="3"></label>
          <label class="ins-lab">Control takes off<input class="in" name="control_effect" type="number" min="0" max="24" value="0"></label><input class="in" name="owner" placeholder="Owner" maxlength="80" aria-label="Owner"><input class="in" name="control" placeholder="The control" maxlength="160" aria-label="Control"></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">Residual = likelihood x impact - what the control takes off.</span><button class="btn" type="submit">Add</button></div></form>
          <form data-form="appetite" class="cr-filter" style="margin-top:8px"><label class="mut" style="font-size:13px;display:flex;gap:8px;align-items:center">Your appetite (residual above it is flagged) <input class="in sm" name="appetite" type="number" min="1" max="25" value="${esc(app)}" style="width:80px"></label><button class="btn soft sm" type="submit">Save</button></form>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Third parties</h2>${err(tp)}
          ${tp && tp.vendors && tp.vendors.length ? tp.vendors.map(v => `<div class="cs-row" style="align-items:flex-start"><span style="flex:1;min-width:0"><b>${esc(v.vendor)}</b>${v.critical ? '<span class="cs-tag">Critical</span>' : ''}${v.critical_without_exit_plan ? '<span class="cs-tag bad">No exit plan</span>' : ''}
            <div class="mut" style="font-size:12.5px">${esc(v.service || '')}${v.contract_end ? ' · contract to ' + esc(dmy(v.contract_end)) : ''}${v.data_location ? ' · data in ' + esc(v.data_location) : ''}</div>${v.missing.length ? `<div class="ins-miss">Missing: ${esc(v.missing.join(', '))}</div>` : ''}</span>${canArea('risk') ? `<button class="ib" type="button" aria-label="Remove ${esc(v.vendor)}" data-rmreg="vendors" data-n="${esc(v.n)}">×</button>` : ''}</div>`).join('') : tp ? empty('No third parties yet.') : loading()}
          ${tp && tp.fields_from ? `<p class="cs-note">Fields: ${esc(tp.fields_from)}</p>` : ''}
          ${canArea('risk') ? `<form data-form="reg" data-reg="vendors" class="fm-draftform"><div class="cr-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">
            <input class="in" name="name" placeholder="Name" required maxlength="120" aria-label="Name"><input class="in" name="service" placeholder="Service" maxlength="120" aria-label="Service">
            <label class="ins-lab">Contract ends<input class="in" type="date" name="contract_end"></label><input class="in" name="data_location" placeholder="Where its data is" maxlength="60" aria-label="Data location">
            <input class="in" name="subcontractors" placeholder="Subcontractors" maxlength="160" aria-label="Subcontractors"><input class="in" name="exit_plan" placeholder="Exit plan" maxlength="160" aria-label="Exit plan">
            <label class="ins-lab">Last assessed<input class="in" type="date" name="last_assessed"></label><label class="ins-check"><input type="checkbox" name="critical" value="yes"><span>Critical</span></label></div>
            <div class="md-acts"><span></span><button class="btn" type="submit">Add</button></div></form>` : ''}</section>
        <section class="card"><h2 class="md-h2">Models and AI</h2>${err(md)}
          ${md && md.models && md.models.length ? md.models.map(m => `<div class="cs-row"><span style="flex:1;min-width:0"><b>${esc(m.model)}</b>${m.ai ? '<span class="cs-tag">AI</span>' : ''}${m.overdue ? '<span class="cs-tag bad">Validation overdue</span>' : ''}${!m.owner ? '<span class="cs-tag warn">No owner</span>' : ''}
            <div class="mut" style="font-size:12.5px">${m.owner ? esc(m.owner) + ' · ' : ''}${m.validated ? 'validated ' + esc(dmy(m.validated)) : 'never validated'}${m.validation_due ? ' · due ' + esc(dmy(m.validation_due)) : ''}</div></span>${canArea('risk') ? `<button class="ib" type="button" aria-label="Remove ${esc(m.model)}" data-rmreg="models" data-n="${esc(m.n)}">×</button>` : ''}</div>`).join('') : md ? empty('No models yet.') : loading()}
          ${canArea('risk') ? `<form data-form="reg" data-reg="models" class="fm-draftform"><div class="cr-grid" style="grid-template-columns:repeat(2,minmax(0,1fr))">
            <input class="in" name="name" placeholder="Model" required maxlength="120" aria-label="Model"><input class="in" name="owner" placeholder="Owner" maxlength="80" aria-label="Owner">
            <label class="ins-lab">Last validated<input class="in" type="date" name="validated"></label><label class="ins-lab">Validate every (days)<input class="in" name="validate_every_days" type="number" min="1" value="365"></label>
            <input class="in" name="use" placeholder="What it is used for" maxlength="160" aria-label="Use"><label class="ins-check"><input type="checkbox" name="ai" value="yes"><span>It is an AI model</span></label></div>
            <div class="md-acts"><span></span><button class="btn" type="submit">Add</button></div></form>` : ''}</section>
      </div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Expected credit loss</h2><div class="r">${(k.counts || {}).exposures && canArea('risk') ? `<button class="btn soft sm" type="button" data-clear="exposures">Clear</button>` : ''}</div></div>
        ${uploader('exposures', 'Upload exposures', 'Columns: id, ead, pd (0-1), lgd (0-1), dpd, and pd_lifetime or stage where you have them', 'risk')}
        ${err(ec)}${ec && !ec.empty && !ec.error ? `<div class="md-3" style="margin-top:14px">${kpi('Total ECL', esc(m2(ec.total_ecl)), `${ec.rows.length} exposures`)}${kpi('Stage 2', esc(m2(ec.by_stage.stage2)), '')}${kpi('Stage 3', esc(m2(ec.by_stage.stage3)), '', ec.by_stage.stage3 ? 'bad' : '')}</div>
          <div class="ins-hbars" style="margin-top:14px">${Object.entries(stages).map(([s, v]) => `<div><span>${esc(cap(s.replace('stage', 'stage ')))}</span><i><b style="width:${(v / stot * 100).toFixed(1)}%"></b></i><em>${esc(m2(v))}</em></div>`).join('')}</div>
          ${ec.flags.length ? `<div class="md-alert" style="margin-top:12px">${svg(IC.info)}<div><div class="t">${esc(ec.flags.length)} note${ec.flags.length > 1 ? 's' : ''}</div><div class="s">${esc(ec.flags.slice(0, 4).join(' '))}</div></div></div>` : ''}
          <p class="cs-note">${esc(ec.method)} ${esc(ec.decider)}</p>` : ec && ec.empty ? empty('No exposures uploaded yet.') : ''}</section>`;
  }

  /* ---------------------------------------------------------------- audit */
  function sampleCard(s) {
    const done = Object.keys(s.results || {}).length, fails = Object.values(s.results || {}).filter(r => !r.passed).length;
    return `<div class="ins-sample"><div class="h"><b>${esc(s.control)}</b>${s.conclusion ? `<span class="cs-tag ${s.conclusion === 'effective' ? 'ok' : 'bad'}">${esc(s.conclusion === 'effective' ? 'Effective' : 'Deficiency')}</span>` : `<span class="cs-tag">${esc(done)} of ${esc(s.sample.length)} tested</span>`}
        <span class="mut">${esc(s.sample.length)} of ${esc(num(s.population))} from ${esc(s.from === 'list' ? 'your list' : s.from)} · seed ${esc(s.seed)} · ${esc(s.by)} · ${esc(dmy(s.on))}</span></div>
      <div class="cr-prog" style="margin:8px 0"><span style="width:${(done / Math.max(1, s.sample.length) * 100).toFixed(0)}%"></span></div>
      <div class="ins-items">${s.sample.map(it => { const r = (s.results || {})[it];
        return `<div class="ins-item ${r ? (r.passed ? 'ok' : 'bad') : ''}"><code>${esc(it)}</code>${r ? `<span>${r.passed ? 'Passed' : 'Failed'}${r.note ? ' · ' + esc(r.note) : ''}</span>` : canArea('audit') ? `<input class="in sm" data-note="${esc(s.n)}|${esc(it)}" placeholder="Note" maxlength="200" aria-label="Note for ${esc(it)}">
          <span class="acts"><button class="btn soft sm" type="button" data-res="${esc(s.n)}" data-item="${esc(it)}" data-pass="1">Pass</button><button class="btn soft sm" type="button" data-res="${esc(s.n)}" data-item="${esc(it)}" data-pass="0">Fail</button></span>` : '<span class="mut">not tested</span>'}</div>`; }).join('')}</div>
      ${fails ? `<p class="cs-note">${esc(fails)} failure${fails > 1 ? 's' : ''}; ${esc(s.tolerated)} tolerated. Whether a deficiency is significant is the auditor's judgement.</p>` : ''}</div>`;
  }
  function pAudit() {
    const k = K(), pb = got('pb', 'pbc'), sl = got('sl', 'sample_list'), je = got('je', 'je_test');
    const items = (pb && pb.items) || [], rec = items.filter(x => x.received).length;
    return `<div><h1 class="sd-h">Audit</h1><p class="lead">What the auditors asked for, samples you can reproduce from their seed, each sampled item's result to the control test, and your journals tested for the usual warning signs.</p></div>
      ${ro('audit')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Prepared-by-client list</h2><div class="r">${items.length ? `<span class="cs-tag">${esc(rec)} of ${esc(items.length)} received</span>` : ''}</div></div>
        ${err(pb)}${items.length ? `<div class="cr-prog" style="margin:10px 0"><span style="width:${(rec / items.length * 100).toFixed(0)}%"></span></div>` : ''}
        ${items.map(x => `<div class="cs-row"><span class="cs-dot${x.late ? ' bad' : x.received ? ' ok' : ''}"></span><span style="flex:1;min-width:0"><b>${esc(x.item)}</b><div class="mut" style="font-size:12.5px">${esc(x.owner || 'no owner')}${x.due ? ' · due ' + esc(dmy(x.due)) : ''}${x.received_on ? ' · received ' + esc(dmy(x.received_on)) : ''}</div></span>
          ${x.late ? '<span class="cs-tag bad">Late</span>' : ''}${canArea('audit') ? (x.received ? `<button class="btn soft sm" type="button" data-pbc="${esc(x.n)}" data-got="0">Not received</button>` : `<button class="btn soft sm" type="button" data-pbc="${esc(x.n)}" data-got="1">Received</button>`) + `<button class="ib" type="button" aria-label="Remove ${esc(x.item)}" data-rmreg="pbc" data-n="${esc(x.n)}">×</button>` : ''}</div>`).join('') || (pb ? empty('Nothing asked for yet.') : loading())}
        ${canArea('audit') ? `<form data-form="reg" data-reg="pbc" class="cr-grid"><input class="in" name="item" placeholder="What the auditors need" required maxlength="160" aria-label="Item"><input class="in" name="owner" placeholder="Who provides it" maxlength="80" aria-label="Owner"><label class="ins-lab">Due<input class="in" type="date" name="due"></label><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">Samples and control tests</h2>
        ${canArea('audit') ? `<form data-form="sample"><div class="cr-grid">
          <input class="in" name="control" placeholder="The control tested (e.g. payment approval)" maxlength="120" aria-label="Control">
          <select class="in" name="from" aria-label="Population from"><option value="list">From a list I paste</option><option value="transactions"${(k.counts || {}).tx ? '' : ' disabled'}>From the transactions (${esc(num((k.counts || {}).tx || 0))})</option><option value="journals"${(k.counts || {}).journals ? '' : ' disabled'}>From the journals (${esc(num((k.counts || {}).journals || 0))})</option></select>
          <label class="ins-lab">Sample size<input class="in" name="size" type="number" min="1" required value="25"></label>
          <label class="ins-lab">Seed (to repeat a sample)<input class="in" name="seed" inputmode="numeric" placeholder="new"></label><label class="ins-lab">Failures tolerated<input class="in" name="tolerated" type="number" min="0" value="0"></label>
          <textarea class="in wide" name="population" rows="3" placeholder="The population, one id a line (only for a pasted list)" aria-label="Population"></textarea></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">The seed is recorded: the same seed and population give the same sample.</span><button class="btn" type="submit">Draw the sample</button></div></form>` : ''}
        ${err(sl)}${sl && sl.samples ? (sl.samples.length ? `<div class="ins-samples">${sl.samples.map(sampleCard).join('')}</div>` : empty('No sample drawn yet.')) : loading()}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Journal entry testing</h2><div class="r">${(k.counts || {}).journals && canArea('audit') ? `<button class="btn soft sm" type="button" data-clear="journals">Clear</button>` : ''}</div></div>
        ${uploader('journals', 'Upload journals', 'Columns: id, date, amount, user, description', 'audit')}
        ${canArea('audit') ? `<form data-form="period" class="cr-grid" style="margin-top:10px"><label class="ins-lab">Period end<input class="in" type="date" name="period_end" value="${esc(k.period_end || '')}"></label><label class="ins-lab" style="flex:2 1 220px">Usual users (comma)<input class="in" name="usual_users" value="${esc((k.usual_users || []).join(', '))}"></label><button class="btn soft sm" type="submit">Save</button></form>` : ''}
        ${err(je)}${je && !je.empty && !je.error ? `<p class="mut" style="font-size:14px;margin:12px 0 6px">${esc(je.flagged.length)} of ${esc(je.tested)} journals flagged.</p>
          ${je.flagged.length ? `<div class="scroll"><table class="tb"><thead><tr><th>Journal</th><th>Date</th><th class="num">Amount</th><th>User</th><th>Flags</th></tr></thead><tbody>${je.flagged.slice(0, 200).map(f => `<tr><td><b>${esc(f.id)}</b><div class="mut" style="font-size:12.5px">${esc(f.description || '')}</div></td><td class="nw">${esc(dmy(f.date))}</td><td class="num">${esc(m2(f.amount))}</td><td>${esc(f.user || '—')}</td><td>${f.flags.map(x => `<span class="cs-tag warn">${esc(x)}</span>`).join('')}</td></tr>`).join('')}</tbody></table></div>` : ''}` : je && je.empty ? empty('No journals uploaded yet.') : ''}</section>`;
  }

  /* ---------------------------------------------------------------- governance */
  function pGovernance() {
    const k = K(), bd = got('bd', 'board'), ctBase = (k.counts || {}).holders ? got('ct', 'cap_table') : null, ct = ST.out.round && ST.out.round.before ? ST.out.round : ctBase, rp = got('rp', 'related'), wb = got('wb', 'whistle_list');
    const miss = new Set((bd && bd.papers_missing) || []), canG = canArea('governance');
    const capRows = c => Object.entries(c || {}).sort((a, b) => b[1].shares - a[1].shares);
    return `<div><h1 class="sd-h">Governance</h1><p class="lead">The board's agenda with its papers, open actions, the cap table and a new round, transactions with your related parties, and whistleblowing cases kept by number only.</p></div>
      ${ro('governance')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Board pack</h2><div class="r">${bd && !bd.error ? (miss.size ? `<span class="cs-tag warn">${esc(miss.size)} paper${miss.size > 1 ? 's' : ''} missing</span>` : (bd.agenda || []).length ? '<span class="cs-tag ok">Every paper is in</span>' : '') : ''}</div></div>${err(bd)}
        <div class="md-2" style="align-items:start;margin-top:8px">
          <div><div class="cr-sub">Agenda</div>${((bd && bd.agenda) || []).map((a, i) => `<div class="cs-row"><span class="ins-num">${i + 1}</span><span style="flex:1;min-width:0"><b>${esc(a.item)}</b><div class="mut" style="font-size:12.5px">${a.paper ? 'paper: ' + esc(a.paper) : 'no paper needed'}${a.owner ? ' · ' + esc(a.owner) : ''}</div></span>${a.paper ? (a.paper_present ? '<span class="cs-tag ok">Paper in</span>' : '<span class="cs-tag warn">Missing</span>') : ''}${canG ? `<button class="ib" type="button" aria-label="Remove ${esc(a.item)}" data-rmreg="agenda" data-n="${esc(a.n)}">×</button>` : ''}</div>`).join('') || empty('No agenda items yet.')}
            ${canG ? `<form data-form="reg" data-reg="agenda" class="cr-grid"><input class="in" name="item" placeholder="Agenda item" required maxlength="160" aria-label="Agenda item"><input class="in" name="paper" placeholder="Its paper" maxlength="120" aria-label="Paper"><button class="btn soft" type="submit">Add</button></form>` : ''}
            <div class="cr-sub" style="margin-top:16px">Papers received</div>${((bd && bd.papers) || []).map(p => `<span class="fm-chip ins-paper">${esc(p.paper)}${canG ? `<button type="button" aria-label="Remove ${esc(p.paper)}" data-rmreg="papers" data-n="${esc(p.n)}">×</button>` : ''}</span>`).join(' ') || empty('None yet.')}
            ${canG ? `<form data-form="reg" data-reg="papers" class="cr-grid" style="margin-top:8px"><input class="in" name="paper" placeholder="Paper received" required maxlength="120" aria-label="Paper received"><button class="btn soft sm" type="submit">Add</button></form>` : ''}</div>
          <div><div class="cr-sub">Actions from the last minutes</div>${((bd && bd.actions) || []).map(a => `<div class="cs-row"><span class="cs-dot${a.done ? ' ok' : ''}"></span><span style="flex:1;min-width:0;${a.done ? 'text-decoration:line-through;color:var(--mut)' : ''}"><b>${esc(a.action)}</b><div class="mut" style="font-size:12.5px">${esc(a.owner || 'no owner')}${a.due ? ' · due ' + esc(dmy(a.due)) : ''}</div></span>${canG ? `<button class="btn soft sm" type="button" data-act="${esc(a.n)}" data-done="${a.done ? 0 : 1}">${a.done ? 'Reopen' : 'Done'}</button>` : ''}</div>`).join('') || empty('No actions.')}
            ${canG ? `<form data-form="reg" data-reg="actions" class="cr-grid"><input class="in" name="action" placeholder="Action" required maxlength="200" aria-label="Action"><input class="in" name="owner" placeholder="Owner" maxlength="80" aria-label="Owner"><button class="btn soft" type="submit">Add</button></form>` : ''}</div></div></section>
      <section class="card"><h2 class="md-h2">Cap table</h2>
        ${(k.counts || {}).holders ? '' : empty('No shareholders yet.')}${err(ST.out.round)}${err(ctBase)}
        ${ct && ct.before ? `<div class="md-2" style="align-items:start;margin-top:6px"><div><div class="cr-sub">Now · ${esc(num(ct.shares_before))} shares</div>${capRows(ct.before).map(([n, v]) => `<div class="ins-cap"><span>${esc(n)}</span><i><b style="width:${v.pct}%"></b></i><em>${esc(num(v.shares))} · ${esc(v.pct.toFixed(2))}%</em></div>`).join('')}</div>
          ${ct.after ? `<div><div class="cr-sub">After the round · ${esc(num(ct.shares_after))} shares</div>${capRows(ct.after).map(([n, v]) => `<div class="ins-cap after"><span>${esc(n)}</span><i><b style="width:${v.pct}%"></b></i><em>${esc(num(v.shares))} · ${esc(v.pct.toFixed(2))}%</em></div>`).join('')}
            <div class="cr-grid" style="margin-top:10px">${kpi('Price a share', esc(money(ct.price_per_share, cur(), 2)), '', 'sm')}${kpi('New shares', esc(num(ct.new_shares)), '', 'sm')}${kpi('Post-money', esc(money(ct.post_money)), '', 'sm')}</div></div>` : '<div></div>'}</div>` : ''}
        ${canG ? `<div class="md-2" style="align-items:start;margin-top:14px"><form data-form="reg" data-reg="holders"><div class="cr-sub">Add a shareholder</div><div class="cr-grid"><input class="in" name="name" placeholder="Name" required maxlength="80" aria-label="Name"><input class="in" name="shares" type="number" min="0" placeholder="Shares" required aria-label="Shares"><button class="btn soft" type="submit">Add</button></div>
            ${((k.holders) || []).length ? `<div class="fm-team" style="margin-top:10px">${k.holders.map(h => `<span class="fm-chip ins-paper">${esc(h.name)} · ${esc(num(h.shares))}<button type="button" aria-label="Remove ${esc(h.name)}" data-rmreg="holders" data-n="${esc(h.n)}">×</button></span>`).join('')}</div>` : ''}</form>
          <form data-form="round"><div class="cr-sub">A new round</div><div class="cr-grid"><input class="in" name="raise" type="number" min="0" step="any" placeholder="Money raised" required aria-label="Money raised"><input class="in" name="pre_money" type="number" min="0" step="any" placeholder="Pre-money value" required aria-label="Pre-money value"><input class="in" name="investor" placeholder="Investor" maxlength="80" aria-label="Investor"></div>
            <div class="md-acts"><span class="mut" style="font-size:13px">New shares at the pre-money price, rounded down.</span><button class="btn" type="submit">Work it out</button></div></form></div>` : ''}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Related parties</h2>
          ${(k.related || []).map(r => `<div class="cs-row"><span style="flex:1"><b>${esc(r.name)}</b> <span class="mut">${esc(r.relation || '')}</span></span>${canG ? `<button class="ib" type="button" aria-label="Remove ${esc(r.name)}" data-rmreg="related" data-n="${esc(r.n)}">×</button>` : ''}</div>`).join('') || empty('No related parties named.')}
          ${canG ? `<form data-form="reg" data-reg="related" class="cr-grid"><input class="in" name="name" placeholder="Name (as it shows on payments)" required maxlength="120" aria-label="Name"><input class="in" name="relation" placeholder="Relation (director, family)" maxlength="80" aria-label="Relation"><button class="btn soft" type="submit">Add</button></form>` : ''}
          ${err(rp)}${rp && rp.related_transactions && rp.related_transactions.length ? `<div class="cr-sub" style="margin-top:14px">In your transactions · ${esc(m2(rp.total))}</div>${rp.related_transactions.slice(0, 40).map(t => `<div class="cs-row"><span style="flex:1"><b>${esc(t.counterparty)}</b> <span class="mut">${esc(dmy(t.date))} · ref ${esc(t.id)}</span></span><b>${esc(t.direction === 'out' ? '−' : '')}${esc(m2(t.amount))}</b></div>`).join('')}<p class="cs-note">${esc(rp.says)}</p>` : rp && !rp.empty && !rp.error ? `<p class="cs-note">None in the transactions on file.</p>` : ''}</section>
        <section class="card"><h2 class="md-h2">Whistleblowing</h2><p class="mut" style="margin:0 0 10px;font-size:14px">A case keeps a number only - never the name or contact of the person reporting. Give them the number so they can follow it.</p>
          <form data-form="whistle"><div class="cr-grid" style="grid-template-columns:minmax(0,1fr)"><input class="in" name="area" placeholder="Area (finance, lending ...)" maxlength="80" aria-label="Area"><textarea class="in" name="what" rows="3" placeholder="What was reported" required maxlength="2000" aria-label="What was reported"></textarea></div><div class="md-acts"><span></span><button class="btn" type="submit">Log the case</button></div></form>
          ${ST.out.wcase ? `<div class="ins-case"><span>Case number</span><b>${esc(ST.out.wcase)}</b><em>Give this to the person who reported it.</em></div>` : ''}
          ${err(wb)}${((wb && wb.cases) || []).map(w => `<div class="ins-wb"><div class="h"><code>${esc(w.case)}</code><span class="cs-tag ${(w.status || 'open') === 'closed' ? 'ok' : (w.status || 'open') === 'looking' ? 'warn' : ''}">${esc(cap(w.status || 'open'))}</span><span class="mut">${w.area ? esc(w.area) + ' · ' : ''}${esc(dmy(w.on))}</span></div><div class="s">${esc(w.what)}</div>
            ${(w.notes || []).map(n => `<div class="mut" style="font-size:12.5px">${esc(dmy(n.on))} · ${esc(n.status)}${n.note ? ': ' + esc(n.note) : ''}</div>`).join('')}
            ${has('compliance') ? `<form data-form="wstatus" data-case="${esc(w.case)}" class="cr-filter"><select class="in sm" name="status" aria-label="Status"><option value="open">Open</option><option value="looking"${w.status === 'looking' ? ' selected' : ''}>Looking into it</option><option value="closed"${w.status === 'closed' ? ' selected' : ''}>Closed</option></select><input class="in sm" name="note" placeholder="Note" maxlength="300" style="flex:1;min-width:140px" aria-label="Note"><button class="btn soft sm" type="submit">Save</button></form>` : ''}</div>`).join('')}</section>
      </div>`;
  }

  /* ---------------------------------------------------------------- drafts */
  function pDrafts() {
    if (ST.arg) return draftPage(ST.arg);
    const ds = got('ds', 'drafts'), all = (ds && ds.drafts) || [];
    const show = all.filter(d => ST.df === 'all' || (ST.df === 'mine' ? d.for_me : d.state === ST.df));
    const cnt = f => all.filter(d => f === 'all' || (f === 'mine' ? d.for_me : d.state === f)).length;
    const lim = K().single_check_limit;
    return `<div><h1 class="sd-h">Drafts</h1><p class="lead">Every draft is made by one person and checked by another before it counts. The maker never checks it; a change drops every check${lim !== null && lim !== undefined ? `; above ${esc(money(lim))} it needs two checkers` : ''}.</p></div>
      <div class="fm-flow"><div class="warn"><b>${esc(cnt('waiting'))}</b><span>Waiting for a check</span></div><em>→</em><div class="ok"><b>${esc(cnt('approved'))}</b><span>Approved</span></div><div class="bad"><b>${esc(cnt('rejected'))}</b><span>Rejected</span></div><div><b>${esc(cnt('mine'))}</b><span>For you to check</span></div></div>
      ${holds('maker') ? `<section class="card"><h2 class="md-h2">A new draft</h2><form data-form="submit"><div class="cr-grid">
        <select class="in" name="kind" aria-label="Kind">${Object.entries(KINDS()).map(([k2, l]) => `<option value="${esc(k2)}">${esc(l)}</option>`).join('')}</select>
        <input class="in" name="title" placeholder="Title" maxlength="160" aria-label="Title"><input class="in" name="amount" type="number" step="any" placeholder="Amount (if it has one)" aria-label="Amount">
        <textarea class="in wide" name="body" rows="6" placeholder="The text (headings with #)" required aria-label="Text"></textarea></div>
        <div class="md-acts"><span class="mut" style="font-size:13px">You are its maker, so you cannot check it.</span><button class="btn" type="submit">Make the draft</button></div></form></section>` : ''}
      <div class="cr-filter"><div class="cs-seg" role="group">${[['waiting', 'Waiting'], ['mine', 'For you'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['all', 'All']].map(([k2, l]) => `<button type="button" data-df="${k2}" aria-pressed="${ST.df === k2}">${esc(l)} <span class="mut">${esc(cnt(k2))}</span></button>`).join('')}</div></div>
      ${err(ds)}${!ds ? loading() : `<div class="fm-cards">${show.map(d => `<button class="fm-card" type="button" data-go="drafts/${esc(d.id)}"><div class="t"><span class="fm-kind">${esc(KS(d.kind))}</span>${stTag(d.state)}</div>
        <b style="font-size:15px">${esc(d.title || KN(d.kind))}</b><div class="mut" style="font-size:13px">made by ${esc(d.maker_name)} · ${esc(dt(d.made))}${d.amount !== null && d.amount !== undefined ? ' · ' + esc(money(d.amount)) : ''}</div>
        <div class="ins-checksbar">${Array.from({length: d.needs_checks}, (_, i) => `<i class="${i < d.approvals ? 'ok' : ''}"></i>`).join('')}<span>${esc(d.approvals)} of ${esc(d.needs_checks)} check${d.needs_checks > 1 ? 's' : ''}</span>${d.for_me ? '<span class="cs-tag warn" style="margin-left:auto">Check it</span>' : ''}</div></button>`).join('') || `<section class="card">${empty('No draft here.')}</section>`}</div>`}`;
  }
  function draftPage(id) {
    if (ST.drFor !== id) { ST.dr = null; ST.drFor = id; ST.editing = false; }
    if (ST.dr === null) { lazy('dr', 'draft', {draft: id}); return loading(); }
    if (ST.dr === false) return loading();
    const d = ST.dr;
    if (d.error) return `<section class="card"><p class="cs-neg" style="margin:0">${esc(d.error)}</p><button class="btn soft sm" type="button" data-go="drafts" style="margin-top:10px">Back</button></section>`;
    const ok = (d.checks || []).filter(c => c.verdict === 'approve'), rej = (d.checks || []).find(c => c.verdict === 'reject');
    const steps = [['Made', d.maker_name, true]];
    for (let i = 0; i < d.needs_checks; i++) steps.push([d.needs_checks > 1 ? `Check ${i + 1}` : 'Checked', (ok[i] || {}).by_name, !!ok[i]]);
    steps.push(['Approved', d.state === 'approved' ? 'counts now' : '', d.state === 'approved']);
    const cn = d.can || {}, body = window.HoolaMD ? HoolaMD.render(mdFix(d.body), false) : `<pre>${esc(d.body)}</pre>`;
    const SC = [['facts_complete', 'Facts complete'], ['clear_and_ordered', 'Clear and in order'], ['why_suspicious', 'Says why it is suspicious'], ['no_accusation', 'No accusation'], ['ready_to_file', 'Ready to file']];
    return `<div class="cs-head"><div style="min-width:0"><button class="btn soft sm" type="button" data-go="drafts">← Drafts</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(d.title || KN(d.kind))}</h1><p class="lead" style="margin-top:4px">${esc(KN(d.kind))} · ${stTag(d.state)}${d.amount !== null && d.amount !== undefined ? ' · ' + esc(money(d.amount)) : ''}</p></div>
        <div class="r"><button class="btn soft sm" type="button" data-dl="draft">PDF</button><button class="btn soft sm" type="button" data-ask="${esc('Draft: ' + (d.title || d.kind))}">Ask about it</button></div></div>
      <div class="fm-steps" style="grid-template-columns:repeat(${steps.length},minmax(0,1fr))">${steps.map(([l, who, done], i) => `<div class="${done ? 'done' : ''}${!done && steps[i - 1] && steps[i - 1][2] && d.state === 'waiting' ? ' now' : ''}"><span class="dot">${done ? '✓' : i + 1}</span><b>${esc(l)}</b><span class="mut">${esc(who || '—')}</span></div>`).join('')}</div>
      ${d.state === 'rejected' && rej ? `<section class="md-alert">${svg(IC.info)}<div><div class="t">Rejected by ${esc(rej.by_name)}</div><div class="s">${esc(rej.reason)}</div></div></section>` : ''}
      <div class="fm-doc">
        <section class="card fm-paper">${ST.editing ? `<form data-form="revise"><textarea class="in" name="body" rows="18" style="width:100%">${esc(d.body)}</textarea><div class="md-acts"><span class="mut" style="font-size:13px">Saving a change drops every check: it waits for a checker again.</span><span style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-editing="0">Cancel</button><button class="btn" type="submit">Save the change</button></span></div></form>` : `<div class="textmd">${body}</div>`}
          ${d.state === 'approved' ? `<div class="fm-seal"><b>Approved by ${esc(ok.map(c => c.by_name).join(' and '))}</b><span>${esc(dmy((ok.slice(-1)[0] || {}).at))}</span><code>${esc(S(d.hash).slice(0, 16))}</code></div>` : ''}</section>
        <aside class="fm-side">
          <section class="card"><h2 class="md-h2">What you can do</h2>
            ${cn.check ? `<form data-form="check"><p class="cs-note" style="margin-top:0">You are checking the text <code>${esc(S(d.hash).slice(0, 12))}</code>. If it changes, your check no longer counts.</p><textarea class="in" name="reason" rows="3" placeholder="Why (needed to reject)" style="width:100%"></textarea><div class="fm-acts"><button class="btn soft" type="submit" data-verdict="reject">Reject</button><button class="btn" type="submit" data-verdict="approve">Approve this text</button></div></form>` : ''}
            ${cn.revise && !ST.editing ? `<button class="btn soft" type="button" data-editing="1" style="width:100%">Change the text</button>` : ''}
            ${d.why_not_check ? `<p class="cs-note">${esc(d.why_not_check)}</p>` : ''}
            ${!cn.check && !cn.revise && !cn.score ? empty(d.state === 'approved' ? 'Approved. An approved draft is not changed: make a new one.' : 'Nothing for you to do on this draft.') : ''}</section>
          ${d.kind === 'sar' ? `<section class="card"><h2 class="md-h2">The MLRO's score</h2>${(d.scores || []).map(s => `<div class="cs-row"><span style="flex:1"><b>${esc(s.by_name)}</b> <span class="mut">${esc(dmy(s.on))}${s.comment ? ' · ' + esc(s.comment) : ''}</span></span><span class="ins-score ${Object.values(s.scores).reduce((a, b) => a + b, 0) >= 20 ? 'ok' : 'warn'}">${esc(Object.values(s.scores).reduce((a, b) => a + b, 0))}/25</span></div>`).join('') || empty('Not scored yet.')}
            ${cn.score ? `<form data-form="score" style="margin-top:10px">${SC.map(([k2, l]) => `<label class="ins-sc"><span>${esc(l)}</span><select class="in sm" name="${k2}" aria-label="${esc(l)}">${[1, 2, 3, 4, 5].map(v => `<option${v === 3 ? ' selected' : ''}>${v}</option>`).join('')}</select></label>`).join('')}<input class="in" name="comment" placeholder="Comment" maxlength="1000" style="width:100%;margin-top:8px"><button class="btn" type="submit" style="width:100%;margin-top:8px">Save my score</button></form>` : ''}</section>` : ''}
          <section class="card"><h2 class="md-h2">History</h2><div class="fm-trail">${(d.history || []).map(h => `<div><i class="${h.did === 'approve' ? 'ok' : h.did === 'reject' ? 'bad' : ''}"></i><span class="mut nw">${esc(dt(h.at))}</span><span><b>${esc(h.by_name)}</b> ${esc(h.did === 'approve' ? 'approved' : h.did === 'reject' ? 'rejected' : h.did)}</span><code class="mut">${esc(S(h.hash).slice(0, 8))}</code></div>`).join('')}</div>
            ${rej ? `<p class="cs-note">Reason: ${esc(rej.reason)}</p>` : ''}<p class="cs-note">Needs ${esc(d.needs_checks)} check${d.needs_checks > 1 ? 's' : ''} · text ${esc(S(d.hash).slice(0, 12))}</p></section>
        </aside></div>`;
  }

  /* ---------------------------------------------------------------- team & settings */
  function pTeam() {
    const k = K(), ppl = (ST.d && ST.d.people) || [], logins = k.logins || {}, admin = holds('admin'), me = ME();
    const R = Object.keys(ROLES());
    return `<div><h1 class="sd-h">Team & settings</h1><p class="lead">The people of the institution and their roles, whose login is whose, the limit above which a draft needs two checkers, how long records are kept, keys for your systems and an export of every register.</p></div>
      ${ST.d.is_owner ? `<section class="card"><h2 class="md-h2">Who you are on this desk</h2><p class="mut" style="margin:0 0 10px;font-size:14px">It is your account, so you can act as any person of the institution. Everything is done and recorded as that person.</p>
        <div class="fm-people">${ppl.map(p => `<button class="fm-person${p.id === me.id ? ' on' : ''}" type="button" data-be="${esc(p.id)}">${avatar(p.name, p.roles)}<b>${esc(p.name)}</b><span class="mut">${esc(p.roles.map(RN).join(', '))}</span></button>`).join('')}</div></section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">People · ${esc(ppl.length)}</h2>${ppl.map(p => `<div class="ins-person"><div class="cs-row" style="border:0">${avatar(p.name, p.roles)}<span style="flex:1;min-width:0"><b>${esc(p.name)}</b>${p.id === me.id ? ' <span class="cs-tag">You</span>' : ''}<div class="ins-roles">${chips(p.roles)}</div>${logins[p.id] ? `<div class="mut" style="font-size:12.5px">login ${esc(logins[p.id])}</div>` : ''}</span>
            ${admin ? `<span style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end"><button class="btn soft sm" type="button" data-editroles="${esc(p.id)}">Roles</button><button class="btn soft sm" type="button" data-linkp="${esc(p.id)}">Login</button></span>` : ''}</div>
          ${ST.editRoles === p.id ? `<form data-form="roles" data-target="${esc(p.id)}" class="ins-inline"><div class="ins-checks">${R.map(r => `<label class="ins-check"><input type="checkbox" name="roles" value="${r}"${p.roles.includes(r) ? ' checked' : ''}><span>${esc(RN(r))}</span></label>`).join('')}</div><div class="md-acts"><span></span><span style="display:flex;gap:8px"><button class="btn soft sm" type="button" data-editroles="">Cancel</button><button class="btn sm" type="submit">Save roles</button></span></div></form>` : ''}
          ${ST.linkFor === p.id ? `<form data-form="link" data-target="${esc(p.id)}" class="ins-inline cr-filter"><input class="in" name="email" type="email" placeholder="Their Hoola login email" value="${esc(logins[p.id] || '')}" style="flex:1;min-width:180px" aria-label="Login email"><button class="btn sm" type="submit">${logins[p.id] ? 'Save' : 'Link'}</button>${logins[p.id] ? `<button class="btn soft sm" type="button" data-unlink="${esc(p.id)}">Unlink</button>` : ''}</form>` : ''}</div>`).join('')}
          ${admin ? `<form data-form="person" class="fm-draftform"><div class="cr-sub" style="margin-top:12px">Add a person</div><input class="in" name="name" placeholder="Their name" required maxlength="80" style="width:100%" aria-label="Name">
            <div class="ins-checks" style="margin-top:8px">${R.map(r => `<label class="ins-check"><input type="checkbox" name="roles" value="${r}"><span>${esc(RN(r))}</span></label>`).join('')}</div><div class="md-acts"><span class="mut" style="font-size:13px">Then link their login so they open the desk as themselves.</span><button class="btn" type="submit">Add</button></div></form>` : '<p class="cs-note">Only an admin adds people and changes roles.</p>'}</section>
        <div style="display:flex;flex-direction:column;gap:16px;min-width:0">
          <section class="card"><h2 class="md-h2">Two checkers above</h2><p class="mut" style="margin:0 0 10px;font-size:14px">A draft with an amount above this needs two different checkers.</p>
            ${admin ? `<form data-form="limit" class="cr-grid" style="margin-top:0"><input class="in" name="single_check_limit" type="number" min="0" step="any" value="${esc(k.single_check_limit ?? '')}" placeholder="Amount" required aria-label="Single-check limit"><button class="btn sm" type="submit">Save</button></form>` : `<b>${esc(k.single_check_limit === null || k.single_check_limit === undefined ? 'Not set' : money(k.single_check_limit))}</b>`}</section>
          <section class="card"><h2 class="md-h2">Keeping records</h2>${Object.entries(k.retention || {}).map(([x, y]) => `<div class="cs-row"><span style="flex:1">${esc(cap(x))}</span><b>${esc(y)} years</b></div>`).join('') || empty('No keep periods set.')}
            ${admin ? `<form data-form="retention" style="margin-top:8px"><textarea class="in" name="keep" rows="3" style="width:100%" placeholder="sar, 5&#10;kyc, 5&#10;board, 10" aria-label="Keep periods">${esc(Object.entries(k.retention || {}).map(([x, y]) => `${x}, ${y}`).join('\n'))}</textarea><div class="md-acts"><span class="mut" style="font-size:13px">Your periods; nothing is deleted before them.</span><button class="btn soft sm" type="submit">Save</button></div></form>` : ''}</section>
          <section class="card"><h2 class="md-h2">Keys for your systems</h2>${(k.keys || []).map(x => `<div class="cs-row"><code>${esc(x.id)}</code><span style="flex:1" class="mut">${esc((x.scopes || []).join(', '))} · ${esc(dmy(x.made))}</span>${x.revoked ? '<span class="cs-tag">Revoked</span>' : admin ? `<button class="btn soft sm" type="button" data-revoke="${esc(x.id)}">Revoke</button>` : ''}</div>`).join('') || empty('No keys.')}
            ${ST.out.key ? `<div class="ins-case"><span>Your new key - shown once</span><b style="font-size:14px;word-break:break-all">${esc(ST.out.key)}</b><em>Copy it now; only its hash is kept.</em></div>` : ''}
            ${admin ? `<form data-form="key" class="cr-filter" style="margin-top:8px">${['read', 'draft', 'check', 'admin'].map(s => `<label class="ins-check"><input type="checkbox" name="scopes" value="${s}"${s === 'read' ? ' checked' : ''}><span>${esc(cap(s))}</span></label>`).join('')}<button class="btn soft sm" type="submit">Make a key</button></form>` : ''}</section>
          <section class="card"><h2 class="md-h2">Export</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Every register, every draft with its checks and the activity record, as one file with its fingerprint.</p>
            ${admin ? `<button class="btn soft" type="button" data-dl="export">Download the registers</button>` : '<p class="cs-note">An admin downloads it.</p>'}</section>
          ${(k.files || []).length ? `<section class="card"><h2 class="md-h2">Files uploaded</h2>${k.files.map(f => `<div class="cs-row"><span style="flex:1;min-width:0"><b>${esc(f.name)}</b><div class="mut" style="font-size:12.5px">${esc(f.kind)} · ${esc(f.rows)} rows · ${esc(f.by)} · ${esc(f.at)}</div></span></div>`).join('')}</section>` : ''}
        </div></div>`;
  }

  /* ---------------------------------------------------------------- actions */
  async function download(what) {
    try {
      const r = await fetch(`/api/institution/download?workspace=${enc(W().id)}&what=${enc(what)}&draft=${enc(ST.drFor || '')}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.file`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); clearCache(); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const lines = t => S(t).split('\n').map(x => x.split(',').map(y => y.trim())).filter(x => x.join('').length);
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ask = t.closest('[data-ask]'); if (ask) { setCtx(ask.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const df = t.closest('[data-df]'); if (df) { ST.df = df.dataset.df; showPage(true); return; }
    const sr = t.closest('[data-sar]'); if (sr) { ST.sarFor = sr.dataset.sar === '' ? null : Number(sr.dataset.sar); showPage(true); return; }
    const co = t.closest('[data-closeout]'); if (co) { delete ST.out[co.dataset.closeout]; showPage(true); return; }
    const ed = t.closest('[data-editing]'); if (ed) { ST.editing = ed.dataset.editing === '1'; showPage(true); return; }
    const er = t.closest('[data-editroles]'); if (er) { ST.editRoles = er.dataset.editroles; ST.linkFor = ''; showPage(true); return; }
    const lp = t.closest('[data-linkp]'); if (lp) { ST.linkFor = ST.linkFor === lp.dataset.linkp ? '' : lp.dataset.linkp; ST.editRoles = ''; showPage(true); return; }
    try {
      const be = t.closest('[data-be]'); if (be) { await run('be', {person: be.dataset.be}); ST.out = {}; await changed('You are now ' + be.querySelector('b').textContent + ' on this desk.'); return; }
      const cl = t.closest('[data-clear]'); if (cl) { if (!confirm('Remove this file from the desk?')) return; await run('clear', {kind: cl.dataset.clear}); await changed('Cleared.'); return; }
      const rm = t.closest('[data-rmreg]'); if (rm) { if (rm.dataset.rmreg === 'holders') delete ST.out.round; await run('register', {register: rm.dataset.rmreg, remove: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const od = t.closest('[data-obdone]'); if (od) { await run('obligation_done', {i: Number(od.dataset.obdone)}); await changed('Marked done today.'); return; }
      const rp = t.closest('[data-reported]'); if (rp) { await run('incident_report', {n: Number(rp.dataset.reported), report: rp.dataset.rep}); await changed('Recorded as reported now.'); return; }
      const pb = t.closest('[data-pbc]'); if (pb) { await run('register', {register: 'pbc', edit: Number(pb.dataset.pbc), set: {received: pb.dataset.got === '1'}}); await changed(pb.dataset.got === '1' ? 'Marked as received.' : 'Marked as not received.'); return; }
      const ac = t.closest('[data-act]'); if (ac) { await run('register', {register: 'actions', edit: Number(ac.dataset.act), set: {done: ac.dataset.done === '1'}}); await changed('Updated.'); return; }
      const rs = t.closest('[data-res]'); if (rs) { const note = $('#insPage').querySelector(`[data-note="${rs.dataset.res}|${CSS.escape(rs.dataset.item)}"]`);
        if (rs.dataset.pass === '0' && note && !note.value.trim()) { toast('Say what failed in the note first.', true); note.focus(); return; }
        const r = await run('test_result', {n: Number(rs.dataset.res), item: rs.dataset.item, passed: rs.dataset.pass === '1', note: note ? note.value.trim() : ''});
        await changed(r.test ? `Control test: ${r.test.conclusion === 'effective' ? 'effective' : 'a deficiency'}.` : 'Recorded.'); return; }
      const rv = t.closest('[data-revoke]'); if (rv) { if (!confirm('Revoke this key? Your system loses access.')) return; await run('api_key', {revoke: rv.dataset.revoke}); await changed('Revoked.'); return; }
      const ul = t.closest('[data-unlink]'); if (ul) { await run('link', {target: ul.dataset.unlink, email: ''}); ST.linkFor = ''; await changed('Unlinked.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 8e6) { toast('Up to 8 MB.', true); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name}); fi.value = ''; await changed(`${r.rows} rows read from ${f.name}.`); }
    catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const sent = () => { form.reset(); form.querySelectorAll('select').forEach(x => { delete x.dataset.touched; }); };
    const done = async m => { sent(); await changed(m); };
    const keepOut = async (key, part, a) => { try { ST.out[key] = await run(part, a); } catch (err2) { ST.out[key] = {error: err2.message}; } showPage(true); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/institution/setup', {name: g('name'), admin: g('admin'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase(), roles: fd.getAll('roles')});
        await done('Your institution is set up.'); }
      else if (kind === 'rules') { const rules = {}; RULE_FIELDS.forEach(([key]) => { const v = g(key), d = (K().rule_defaults || {})[key];
          if (v === '') return; if (key in (K().rules || {}) || S(Array.isArray(d) ? d.join(', ') : d) !== v) rules[key] = v; });
        await run('settings', {rules}); await done('Your rules are saved.'); }
      else if (kind === 'sar') { const al = ((ST.am || {}).alerts || [])[Number(form.dataset.i)];
        const r = await run('sar_draft', {alert: al, customer: {name: g('name'), occupation: g('occupation'), declared_income: g('declared_income'), expected_activity: g('expected_activity')}, actions_taken: g('actions_taken')});
        ST.out.sar = r; ST.sarFor = null; if (r.draft) await done('The report is a draft waiting for a checker.'); else showPage(true); }
      else if (kind === 'screen') await keepOut('sn', 'sanctions', {names: g('names'), threshold: Number(g('threshold') || 0.7)});
      else if (kind === 'kyc') { const docs = lines(g('documents')).map(x => ({kind: x[0], expires: x[1] || undefined}));
        const factors = {}, weights = {}; lines(g('factors')).forEach(x => { factors[x[0]] = /^(y|yes|true|1)$/i.test(x[2] || ''); weights[x[0]] = Number(x[1] || 0); });
        await keepOut('kyc', 'kyc_review', {required: g('required').split(',').map(x => x.trim()).filter(Boolean), documents: docs, factors, weights}); }
      else if (kind === 'reg') { const item = {}; for (const [k2, v] of fd.entries()) item[k2] = S(v).trim();
        await run('register', {register: form.dataset.reg, item}); if (form.dataset.reg === 'holders') delete ST.out.round; await done('Added.'); }
      else if (kind === 'ob') { await run('obligation_add', {item: {name: g('name'), source: g('source'), owner: g('owner'), control: g('control'), every_days: Number(g('every_days') || 365), last_done: g('last_done')}}); await done('Obligation added.'); }
      else if (kind === 'deadline') { await run('settings', {deadline_days: g('deadline_days')}); await done('Saved.'); }
      else if (kind === 'policy') await keepOut('pol', 'policy_check', {text: g('text'), required_sections: g('required_sections').split(',').map(x => x.trim()).filter(Boolean)});
      else if (kind === 'promo') await keepOut('pro', 'promotion_check', {text: g('text'), banned_words: g('banned_words').split(',').map(x => x.trim()).filter(Boolean)});
      else if (kind === 'incident') { const r = await run('incident', {title: g('title'), detected: g('detected'), severity: g('severity')}); await done(r.says && r.says.includes('check this') ? 'Logged - using Hoola\'s starting clocks.' : 'Logged.'); }
      else if (kind === 'clocks') { await run('settings', {clocks: lines(g('clocks')).map(x => ({report: x[0], hours: Number(x[1])}))}); await done('Your clocks are saved.'); }
      else if (kind === 'appetite') { await run('settings', {appetite: g('appetite')}); await done('Saved.'); }
      else if (kind === 'sample') { const a = {control: g('control'), from: g('from'), size: Number(g('size')), seed: g('seed'), tolerated: Number(g('tolerated') || 0), population: g('population')};
        const r = await run('sample', a); await done(`Sample drawn with seed ${r.sample.seed}.`); }
      else if (kind === 'period') { await run('settings', {period_end: g('period_end'), usual_users: g('usual_users')}); await done('Saved.'); }
      else if (kind === 'round') await keepOut('round', 'cap_table', {raise: Number(g('raise')), pre_money: Number(g('pre_money')), investor: g('investor')});
      else if (kind === 'whistle') { const r = await run('whistle', {area: g('area'), what: g('what')}); ST.out.wcase = r.case; await done('Logged with a case number only.'); }
      else if (kind === 'wstatus') { await run('whistle_status', {case: form.dataset.case, status: g('status'), note: g('note')}); await done('Saved.'); }
      else if (kind === 'submit') { const a = {kind: g('kind'), title: g('title'), body: fd.get('body')}; if (g('amount') !== '') a.amount = Number(g('amount'));
        const r = await run('submit', a); location.hash = '#/drafts/' + r.draft.id; await done(r.says); }
      else if (kind === 'check') { const v = btn && btn.dataset.verdict; await run('check', {draft: ST.dr.id, verdict: v, hash: ST.dr.hash, reason: g('reason')}); await done(v === 'approve' ? 'Your check is recorded.' : 'Rejected - back to its maker.'); }
      else if (kind === 'revise') { await run('revise', {draft: ST.dr.id, body: fd.get('body')}); ST.editing = false; await done('Changed - it waits for a checker again.'); }
      else if (kind === 'score') { const scores = {}; ['facts_complete', 'clear_and_ordered', 'why_suspicious', 'no_accusation', 'ready_to_file'].forEach(k2 => { scores[k2] = Number(g(k2)); });
        await run('sar_score', {draft: ST.dr.id, scores, comment: g('comment')}); await done('Your score is saved.'); }
      else if (kind === 'roles') { await run('roles', {target: form.dataset.target, roles: fd.getAll('roles')}); ST.editRoles = ''; await done('Roles saved.'); }
      else if (kind === 'link') { await run('link', {target: form.dataset.target, email: g('email')}); ST.linkFor = ''; await done('Linked. Add them to the team in Books & Accounts too.'); }
      else if (kind === 'person') { await run('person_add', {name: g('name'), roles: fd.getAll('roles')}); await done('Added.'); }
      else if (kind === 'limit') { await run('limits', {single_check_limit: Number(g('single_check_limit'))}); await done('Saved.'); }
      else if (kind === 'retention') { const keep = {}; lines(g('keep')).forEach(x => { if (x[0]) keep[x[0]] = Number(x[1]); }); await run('retention', {keep_years: keep}); await done('Saved.'); }
      else if (kind === 'key') { const r = await run('api_key', {scopes: fd.getAll('scopes')}); await done('Key made.'); ST.out.key = r.key; showPage(true); }
    } catch (err2) { toast(err2.message, true); }
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
    const box = $('#insFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/institution/chat'); ST.chat = r.id; }
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
    if (!text && ready.length) text = ready.length > 1 ? 'Read these files' : 'Read this file';
    if (!text && ST.ctx) text = 'Help me with this';
    if (!text || ST.sending || !ST.chat) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = ST.ctx ? `About: ${ST.ctx}\n${text}` : text;
    const files = ready.map(f => f.id), names = ready.map(f => f.name);
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: names});
    setCtx(''); ST.files = []; paintFiles();
    paintThread();
    let ok = true;
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'in' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


