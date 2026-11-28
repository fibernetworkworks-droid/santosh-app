/* LABOUR & WAGES DESK - the Construction & Real Estate Labour & Wages Desk's own section, like the finance desks and the Material Store
   (owner: "NOW NEXT CONSTRUCTION EMPLOYEE SAME WAY -- Labour & Wages Desk" -> workflow + design canvas -> "GO BUILD ALL 7 VERSIONS").
   A thin top bar, then the Labour chat (its own conversation, kind 'labour': she sends a muster sheet photo, a voice note, asks who is
   due a renewal) beside the desk's pages: Today, Muster, Workers & papers, Wages, Levies & tax, Subcontractors, Reports, Settings.
   The pages call /api/lbdesk/do/<part>. A named person approves the muster, checks and approves a run, records it paid and decides -
   typed on these pages; the chat only drafts. The muster works offline on a phone: marks wait in this browser and go when it is back.
   Routes: #/<page>[/<id>]. */
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
    if (!r.ok) { const e = new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`); e.status = r.status; throw e; }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', crew: '<path d="M4 18v-3a4 4 0 0 1 4-4"/><path d="M5 10a7 7 0 0 1 14 0"/><path d="M3 10h18"/><circle cx="16" cy="16" r="3.5"/><path d="M16 14.5v1.6l1 .8"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>', cam: '<path d="M4 7h4l2-3h4l2 3h4v12H4z"/><circle cx="12" cy="13" r="3.5"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['muster', 'Muster'], ['workers', 'Workers & papers'], ['wages', 'Wages'], ['levies', 'Levies & tax'],
    ['subs', 'Subcontractors'], ['reports', 'Reports'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me today?', 'Who is on site today?', 'What wages are due this week?'],
    muster: ['Read this muster sheet', 'Who was on two sites?', 'Gang 3 has 42 people today'],
    workers: ['Whose papers run out this month?', 'Read this work permit', 'Import my worker list'],
    wages: ['Prepare this week\'s wages', 'Why did Raju get more this week?', 'Which lines are below the minimum?'],
    levies: ['What cess goes on RA bill 14?', 'What tax do I cut from Kumar?', 'What is due this month?'],
    subs: ['Which subcontractor is missing proof?', 'Draft the note to Kumar', 'Read this wage register'],
    reports: ['Give me the wage register for November', 'What is left to close the project?', 'Export the muster'],
    settings: ['Set up the desk for my company', 'Which overtime rule applies to me?', 'Add the minimum rate for masons']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;
  const QKEY = 'hoola.labour.queue';

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], cache: {}, day: '', site: '', q: '',
    pick: {}, period: null, reg: null};
  try { ST.side = localStorage.getItem('hoola.labour.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.labour.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const SET = () => K().settings || {};
  const CAN = () => !!(ST.d && ST.d.status === 'hired');
  const cur = () => SET().currency || 'USD';
  const money = (v, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 2});
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const iso = d => d.toISOString().slice(0, 10);
  const todayIso = () => K().today || iso(new Date());
  const shift = (d, n) => { const x = new Date(d + 'T00:00'); x.setDate(x.getDate() + n); return iso(new Date(x.getTime() - x.getTimezoneOffset() * 60000)); };
  const dmyy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); } catch { return d; } };
  const run = (part, a) => api('POST', '/api/lbdesk/do/' + part, a || {});
  const tag = (t, c) => `<span class="cs-tag ${c || ''}">${esc(t)}</span>`;
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const ro = () => CAN() ? '' : '<p class="cs-note">The desk is paused: resume it in AI Employees to make changes.</p>';
  const ask = about => `<button class="ib sk-ask" type="button" aria-label="Ask about this" title="Ask in the chat" data-ask="${esc(about)}">${svg(IC.chat)}</button>`;
  const fld = (n, l, v, extra, ph) => `<label class="sk-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v, extra) => `<label class="sk-lab">${esc(l)}<select class="in" name="${n}" ${extra || ''}>${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v ?? '') ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows) => `<label class="sk-lab wide">${esc(l)}<textarea class="in" name="${n}" rows="${rows || 5}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const sev = c => c === 'bad' ? 'bad' : c === 'warn' ? 'warn' : c === 'ok' ? 'ok' : '';
  const checkRows = list => (list || []).map(c => `<div class="sk-ck"><span class="sk-ic ${sev(c.sev)}">${c.sev === 'ok' ? '✓' : c.sev === 'info' ? 'i' : '!'}</span><span>${esc(c.text)}</span></div>`).join('');
  const siteOpts = first => [...(first ? [['', first]] : []), ...((K().sites || []).map(s => [s.id, s.name]))];
  const empOpts = () => (K().employers || []).map(e => [e.id, e.name + (e.kind === 'own' ? ' (own gangs)' : '')]);
  const who = ph => `<input class="in sk-who" name="who" maxlength="80" placeholder="${esc(ph || 'Your name')}" required>`;
  const initials = n => S(n).split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase();

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/lbdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.crew, '')}</div>
        <h1 class="sd-h">Your Labour &amp; Wages Desk is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="lbHire">Hire the Labour &amp; Wages Desk</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#lbHire').onclick = async () => { try { await api('POST', '/api/employees/const_labour/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
      return;
    }
    ST.day = todayIso();
    frame();
    readTab();
    paintTabs();
    showPage();
    await openChat();
    ST.timers.push(setInterval(() => loadMsgs(false), 2500));
    ST.timers.push(setInterval(() => refreshDesk(false), 60000));
    ST.timers.push(setInterval(flushQueue, 30000));
    window.addEventListener('online', flushQueue);
    flushQueue();
  }
  function readTab() {
    const parts = (location.hash.replace(/^#\/?/, '') || '').split('/');
    ST.arg = decodeURIComponent(parts.slice(1).join('/') || '');
    ST.tab = TABS.some(x => x[0] === parts[0]) ? parts[0] : 'today';
    if (ST.tab === 'muster' && /^\d{4}-\d{2}-\d{2}$/.test(ST.arg)) { ST.day = ST.arg; }
  }

  /* ---------------------------------------------------------------- the frame (drawn once) */
  function frame() {
    APP.innerHTML = `
      <header class="sd-top">
        <div class="sd-id">
          <a class="ib" href="/console/" aria-label="Back to Hoola" title="Back to Hoola">${svg(IC.back)}</a>
          <div class="sd-ico">${svg(IC.crew, '')}</div>
          <div style="min-width:0"><div class="sd-name">Labour &amp; Wages</div><div class="sd-site" id="lbSite"></div></div>
          <span id="lbState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Labour chat">
          <div class="sd-chathead"><div class="t"><b>Labour chat</b><span>Send a muster sheet photo, a voice note or a paper; every number shows the rule it came from</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="lbFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="lbPick" multiple hidden accept="image/*,application/pdf,.pdf,.csv,.txt,.xlsx,audio/*">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Labour and wages desk" id="sdTabs"></nav>
          <div id="lbPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'A named person approves; Hoola pays nobody and files nothing.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about muster, wages or levies…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#lbPick').click()});
    $('#lbPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.labour.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.labour.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/lbdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#lbPage').addEventListener('click', onPageClick);
    $('#lbPage').addEventListener('submit', onSubmit);
    $('#lbPage').addEventListener('change', onChange);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#lbState'); if (!el) return;
    const k = K(), nd = k.serious || 0;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = SET();
    $('#lbSite').textContent = [s.project || s.company, [s.country, s.region].filter(Boolean).join(' · '), cur(), s.pay_cycle ? s.pay_cycle + ' wages' : '',
      (k.sites || []).length ? pl((k.sites || []).length, 'site') : '', k.workers ? pl(k.workers, 'worker') : ''].filter(Boolean).join(' · ') || 'Set up your labour desk';
  }
  function paintTabs() {
    const n = K().counts || {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/lbdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) { ST.cache = {}; showPage(true); } else if (ST.tab === 'today') showPage(true);
  }
  async function changed(msg) { ST.cache = {}; await refreshDesk(false); showPage(true); if (msg) toast(msg); }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#lbPage'); if (!box) return;
    const fn = {today: pToday, muster: pMuster, workers: pWorkers, wages: pWages, levies: pLevies, subs: pSubs, reports: pReports, settings: pSettings}[ST.tab] || pToday;
    const kept = keep ? typed(box) : null;
    box.innerHTML = fn();
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  function typed(box) {
    const out = {}, act = document.activeElement;
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = f.dataset.form + '|' + (f.dataset.id || '');
      [...f.querySelectorAll('input:not([type=file]):not([type=checkbox]), textarea, select')].forEach((el, j) => {
        if (el.name && (el.value !== el.defaultValue || el === act)) out[k + '|' + el.name + '#' + j] = {v: el.value, f: el === act};
      });
    });
    return out;
  }
  function retype(box, kept) {
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = f.dataset.form + '|' + (f.dataset.id || '');
      [...f.querySelectorAll('input:not([type=file]):not([type=checkbox]), textarea, select')].forEach((el, j) => {
        const v = kept[k + '|' + el.name + '#' + j]; if (!v) return; el.value = v.v; if (v.f) el.focus();
      });
    });
  }
  function lazy(key, part, a) {
    if (ST.cache[key] === undefined) {
      ST.cache[key] = null;
      run(part, a).then(r => { ST.cache[key] = r; showPage(true); }).catch(e => { ST.cache[key] = {error: e.message}; showPage(true); });
    }
    return ST.cache[key];
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  const failed = r => r && r.error ? `<section class="card">${empty(r.error)}</section>` : '';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;

  function headChart(c) {
    if (!c || !c.rows || !c.rows.length) return '';
    const rows = c.rows, n = rows.length;
    const hi = Math.max(1, c.planned || 0, ...rows.map(r => r.own + r.subs));
    const W = 900, H = 220, L = 40, R = 10, T = 14, B = 28, bw = (W - L - R) / n;
    const y = v => T + (H - T - B) * (1 - v / hi);
    const bars = rows.map((r, i) => {
      const x = L + i * bw + 2, w = Math.max(2, bw - 4);
      return `<rect class="own${i === n - 1 ? ' today' : ''}" x="${x.toFixed(1)}" y="${y(r.own).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(0) - y(r.own)).toFixed(1)}" rx="2"/>` +
        `<rect class="sub" x="${x.toFixed(1)}" y="${y(r.own + r.subs).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(r.own) - y(r.own + r.subs)).toFixed(1)}" rx="2"/>`;
    }).join('');
    const ticks = [hi, Math.round(hi / 2), 0].map(v => `<text class="tx" x="0" y="${(y(v) + 4).toFixed(1)}">${esc(num(Math.round(v)))}</text><line class="ax" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`).join('');
    const labels = [0, Math.floor(n / 2), n - 1].map(i => `<text class="tx" x="${(L + i * bw + bw / 2).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(i === n - 1 ? 'today' : dmy(rows[i].day))}</text>`).join('');
    const plan = c.planned ? `<line class="plan" x1="${L}" x2="${W - R}" y1="${y(c.planned).toFixed(1)}" y2="${y(c.planned).toFixed(1)}"/><text class="minl" x="${L + 6}" y="${(y(c.planned) - 6).toFixed(1)}">Planned ${esc(num(c.planned))}</text>` : '';
    return `<div class="cs-chart lb-bars"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="People on site a day for the last 30 days: own gangs and subcontractors">${ticks}${bars}${plan}${labels}</svg></div>
      <div class="cs-legend"><span><i class="lb-own"></i>Own gangs</span><span><i class="lb-sub"></i>Subcontractors</span>${c.planned ? '<span><i class="lb-plan"></i>Planned headcount</span>' : ''}</div>`;
  }

  function pToday() {
    const k = K(), t = k.tiles || {};
    const lead = !(k.sites || []).length ? 'Set up your company, country and sites to start - or send me your worker list in the chat.'
      : t.sites_in < t.sites_total ? `${pl(t.sites_total - t.sites_in, 'site')} ${t.sites_total - t.sites_in === 1 ? 'has' : 'have'} not sent today's muster yet.`
      : t.serious ? `${pl(t.serious, 'thing')} on today's muster need a person to decide.` : 'Today\'s muster is in and nothing serious stands out.';
    return `<section><h1 class="sd-h sk-greet">${greet()}</h1><p class="lead">${esc(lead)}</p></section>${ro()}
      <section class="cs-hero">
        <div class="top">
          <div class="k"><div class="l">On site today</div><div class="v">${num(t.on_site || 0)}</div><div class="s">${num(t.own || 0)} own · ${num(t.subs || 0)} subcontractors${t.planned ? ` · planned ${num(t.planned)}` : ''}</div></div>
          <div class="cs-arrow">→</div>
          <div class="k"><div class="l">Wages so far this period</div><div class="v">${money(t.wages_due)}</div><div class="s">${pl(t.wages_people || 0, 'person', 'people')} since ${esc(dmy(t.wages_from))}</div></div>
          <div class="cs-arrow">→</div>
          <div class="k low${t.next_filing ? '' : ''}"><div class="l">Next filing or payment</div><div class="v" style="font-size:24px">${t.next_filing ? esc(dmy(t.next_filing.due)) : 'Nothing due'}</div><div class="s">${esc(t.next_filing ? t.next_filing.what : 'no levy, deposit or return on the calendar')}</div></div>
        </div>
        ${headChart(k.chart) || empty('The chart fills in once the muster comes in.')}
      </section>
      <section class="cs-4 grid" style="display:grid;gap:16px">
        ${kpi('Muster flags today', t.flags ? num(t.flags) : 'None', t.serious ? `${pl(t.serious, 'serious one')}` : 'two sites, gate, papers, hours', t.serious ? 'bad' : '')}
        ${kpi('Papers running out', num((t.papers_soon || 0) + (t.papers_lapsed || 0)), t.papers_lapsed ? `${num(t.papers_lapsed)} lapsed` : 'in the next 30-90 days', t.papers_lapsed ? 'bad' : '')}
        ${kpi('Overtime this period', `${num(t.ot_hours || 0)} h`, t.ot_rule || '')}
        ${kpi('Levies due', money(t.levies_due), 'cess and levies not yet paid')}
      </section>
      <section class="sk-2">
        <div class="card"><h2 class="sk-h">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</div>
        <div class="card"><h2 class="sk-h">Coming up</h2>${(k.coming || []).length ? k.coming.map(x => `<div class="cs-row"><span class="mut sk-when">${esc(dmy(x.due))}</span><span style="flex:1">${esc(x.what)}${x.amount ? ' · ' + money(x.amount) : ''}</span>${x.check ? tag('check this', 'warn') : ''}${x.late ? tag('late', 'bad') : ''}</div>`).join('') : empty('No levy, deposit or filing on the calendar yet.')}
          ${(k.radar || []).length ? `<h3 class="sk-h3">Renewals</h3>${k.radar.slice(0, 5).map(p => `<div class="cs-row"><span class="mut sk-when">${esc(dmy(p.valid_to))}</span><span style="flex:1">${esc(p.owner || 'Your company')} · ${esc(p.name)}</span>${tag(p.lapsed ? 'lapsed' : p.days_left + ' d', p.lapsed ? 'bad' : p.days_left <= 14 ? 'warn' : '')}</div>`).join('')}` : ''}</div>
      </section>
      ${!(k.workers) ? `<section class="card"><h2 class="sk-h">Start here</h2><div class="sk-steps"><a class="btn soft" href="#/settings">1 · Company, country and sites</a><a class="btn soft" href="#/workers">2 · Workers and papers</a><a class="btn soft" href="#/settings">3 · Pay rates and minimum rates</a><a class="btn soft" href="#/muster">4 · Today's muster</a></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- muster */
  function queue() { try { return JSON.parse(localStorage.getItem(QKEY) || '[]'); } catch { return []; } }
  function setQueue(q) { try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch {} }
  async function flushQueue() {
    const q = queue(); if (!q.length || !navigator.onLine) return;
    const left = [];
    for (const item of q) { try { await run('mark', item); } catch (e) { if (!e.status || e.status >= 500) left.push(item); else toast(e.message, true); } }
    setQueue(left);
    if (left.length < q.length) { toast(`${q.length - left.length} saved muster(s) sent.`); changed(); }
  }
  function pMuster() {
    const d = lazy('day:' + ST.day, 'day', {day: ST.day});
    const wk = lazy('workers', 'workers', {});
    if (!d || !wk) return loading();
    if (d.error) return failed(d);
    const sites = K().sites || [];
    if (!ST.site && sites.length) ST.site = sites[0].id;
    const site = sites.find(s => s.id === ST.site);
    const people = (wk.workers || []).filter(w => !site || !w.site_id || w.site_id === ST.site);
    const sx = (d.sites || []).find(x => x.site_id === ST.site);
    const marked = {};
    for (const g of (sx ? sx.gangs : [])) for (const p of g.people) marked[p.worker_id] = p.value;
    const gangs = {};
    for (const w of people) (gangs[w.gang || 'No gang'] = gangs[w.gang || 'No gang'] || []).push(w);
    const val = w => ST.pick[w.id] !== undefined ? ST.pick[w.id] : (marked[w.id] !== undefined ? marked[w.id] : null);
    const present = people.filter(w => (val(w) || 0) > 0).length;
    const q = queue();
    const flags = d.flags || [];
    const isToday = ST.day === todayIso();
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Muster</h1><p class="lead">${esc(dmy(d.day))}${isToday ? ' · today' : ''} · cut-off ${esc(d.cutoff)} · a correction never edits a mark: it adds a row with the reason and who.</p></div>
        <span class="cs-seg"><button type="button" data-day="${esc(shift(ST.day, -1))}">← Day before</button>${isToday ? '' : `<button type="button" data-day="${esc(todayIso())}">Today</button><button type="button" data-day="${esc(shift(ST.day, 1))}">Next day →</button>`}</span></section>${ro()}
      ${sites.length > 1 ? `<section class="sk-filters"><span class="cs-seg">${sites.map(s => `<button type="button" data-site="${esc(s.id)}" aria-pressed="${s.id === ST.site}">${esc(s.name)}</button>`).join('')}</span></section>` : ''}
      ${q.length ? `<p class="lb-queue">${pl(q.length, 'muster')} saved on this device while offline - they go as soon as it is back online.</p>` : ''}
      <section class="sk-split">
        <div class="card"><div class="lb-mk"><div style="flex:1"><div class="big">${num(present)} <span class="mut" style="font-size:15px;font-weight:400">of ${num(people.length)} present</span></div><div class="mut sk-sub">${esc(site ? site.name : 'Add a site in Settings')}</div></div>
            <button class="rb" type="button" data-voice="1" aria-label="Speak the muster" title="Speak the muster in the chat">${svg(IC.mic)}</button>
            <label class="rb" aria-label="Photo of a paper sheet" title="Photo of a paper sheet">${svg(IC.cam)}<input type="file" accept="image/*,application/pdf" capture="environment" data-sheet="1" hidden></label></div>
          ${people.length ? `<form data-form="mustermark">${Object.entries(gangs).map(([g, ws]) => `<h3 class="sk-h3">${esc(g)}</h3>${ws.map(w => {
            const v = val(w);
            return `<div class="lb-ln"><span class="lb-av">${esc(initials(w.name))}</span><span class="nm">${esc(w.name)}<small>${esc([w.trade, w.employer].filter(Boolean).join(' · '))}</small></span>
              <input class="in lb-ot" name="ot_${esc(w.id)}" inputmode="decimal" placeholder="OT h" aria-label="Overtime hours for ${esc(w.name)}">
              <span class="lb-tg" role="group" aria-label="${esc(w.name)}">${[['p', 1, 'P'], ['h', 0.5, '½'], ['a', 0, 'A']].map(([c, n, t]) => `<button type="button" class="${c}" data-mark="${esc(w.id)}" data-v="${n}" aria-pressed="${v === n}">${t}</button>`).join('')}</span></div>`; }).join('')}`).join('')}
            ${CAN() ? `<div class="sk-acts" style="margin-top:14px">${who('Foreman')}<button type="button" class="btn soft" data-allp="1">Everyone present</button><button class="btn" type="submit">Send muster</button></div>` : ''}</form>` : empty('No workers on this site yet. Add them on Workers & papers or send the list in the chat.')}
        </div>
        <div class="card"><h2 class="sk-h">Checks for ${esc(dmy(d.day))}</h2>${flags.length ? flags.map(f => `<div class="lb-flag"><span class="sk-ic ${sev(f.sev)}">!</span><span style="flex:1">${esc(f.text)}</span>${ask(f.text)}</div>`).join('') : empty('No flags: nobody on two sites, the gate agrees, papers in order.')}
          ${(d.unknown || []).length ? `<h3 class="sk-h3">Who is this?</h3>${d.unknown.map(u => `<form class="sk-inline" data-form="resolve" data-id="${esc(u.id)}" style="padding:6px 0"><b style="flex:1 1 100%">${esc(u.name)}</b>${u.guesses.length ? `<span class="mut sk-sub" style="flex:1 1 100%">Close: ${esc(u.guesses.join(', '))}</span>` : ''}
            ${sel('worker', 'Is', [['', 'Pick a worker'], ...(wk.workers || []).map(w => [w.id, w.name])], '')}${who()}<button class="btn soft sm" name="act" value="match">Match</button><button class="btn soft sm" name="act" value="drop">Leave out</button></form>`).join('')}` : ''}
          ${CAN() ? `<details class="sk-more"><summary>Gate count</summary><form data-form="gate" class="sk-inline">${fld('count', 'People through the gate', '', 'inputmode="numeric" required')}<input class="in" name="source" placeholder="Gate register / turnstile"><button class="btn soft sm">Save</button></form></details>
            <details class="sk-more"><summary>Attendance device file</summary><form data-form="device" class="sk-grid">${area('text', 'Paste the CSV: name, day, in, out', 'name,day,in,out\nRaju Kamble,2026-11-28,08:02,17:10', 4)}${fld('device', 'Device name', '', 'maxlength="60"')}<div class="wide sk-acts"><span></span><button class="btn soft">Read it</button></div></form></details>` : ''}
        </div>
      </section>
      <section class="card"><h2 class="sk-h">Every site, ${esc(dmy(d.day))}</h2>${(d.sites || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Site · gang</th><th>Employer</th><th class="num">Present</th><th class="num">Half</th><th class="num">Absent</th><th class="num">Overtime h</th><th></th></tr></thead><tbody>${d.sites.map(x =>
        `<tr><td colspan="7"><b>${esc(x.site)}</b> · ${num(x.total)} on the muster${x.gate !== null ? ` · gate ${num(x.gate)}` : ''} ${x.closed ? tag('approved by ' + x.closed.who, 'ok') : tag('not approved yet', 'warn')}${x.late ? ' ' + tag(pl(x.late, 'late mark'), 'warn') : ''}
          ${CAN() && !x.closed && x.total ? `<form class="sk-inline" data-form="closeday" data-id="${esc(x.site_id)}" style="margin-top:6px">${who('Site engineer')}<button class="btn soft sm">Approve the day</button></form>` : ''}</td></tr>` +
        x.gangs.map(g => `<tr><td>${esc(g.gang)}</td><td>${esc(g.employer)}</td><td class="num">${g.count ? num(g.count) + ' (head count)' : num(g.present)}</td><td class="num">${num(g.half)}</td><td class="num">${num(g.absent)}</td><td class="num">${num(g.ot)}</td>
          <td>${g.people.length ? `<details class="sk-rev"><summary>Correct a mark</summary>${g.people.map(p => `<form class="sk-inline" data-form="correct" data-id="${esc(p.mark_id)}"><span style="flex:1 1 120px">${esc(p.name)} ${tag(p.value === 1 ? 'P' : p.value === 0.5 ? '½' : 'A')}</span>${sel('status', 'To', [['P', 'Present'], ['half', 'Half'], ['A', 'Absent']], p.value === 1 ? 'P' : p.value === 0.5 ? 'half' : 'A')}<input class="in" name="reason" placeholder="Why" required>${who()}<button class="btn soft sm">Correct</button></form>`).join('')}</details>` : ''}</td></tr>`).join('')).join('')}</tbody></table></div>` : empty('Nothing marked for this day.')}</section>
      ${(d.corrections || []).length ? `<section class="card"><h2 class="sk-h">Corrections</h2>${d.corrections.map(c => `<div class="cs-row"><span style="flex:1">${esc(c.name)}: ${esc(c.reason)}</span><span class="mut">${esc(c.who)} · ${esc(S(c.at).slice(11, 16))}</span></div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- workers & papers */
  function pWorkers() {
    if (ST.arg) return pWorker(ST.arg);
    const wk = lazy('workers:' + ST.q, 'workers', {q: ST.q}), rd = lazy('radar', 'radar', {});
    if (!wk || !rd) return loading();
    if (wk.error) return failed(wk);
    const bands = [['lapsed', 'Lapsed', 'bad'], ['14', 'Next 14 days', ''], ['30', 'Next 30 days', ''], ['60', 'Company: 60-90 days', '']];
    const rows = rd.rows || [];
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Workers &amp; papers</h1><p class="lead">One row per person across every site - that is how a double muster is caught. Only the last 4 of any id or account are kept.</p></div></section>${ro()}
      <section class="card"><h2 class="sk-h">Renewals</h2><div class="lb-tl">${bands.map(([b, t, c]) => { const it = rows.filter(r => b === '60' ? ['60', '90'].includes(r.band) : r.band === b);
        return `<div class="col ${c}"><h3>${esc(t)} · ${it.length}</h3>${it.map(r => `<div class="it" title="${esc(r.owner + ' · ' + r.name)}">${esc(dmy(r.valid_to))} · ${esc(r.owner || 'Your company')} · ${esc(r.name)}</div>`).join('') || '<div class="it mut">None</div>'}</div>`; }).join('')}</div>
        <p class="cs-note">Company and subcontractor papers show from 90 days ahead, a person's from 30. A person with a lapsed required paper is flagged on the muster; the site engineer decides whether they work.</p></section>
      <section class="sk-filters"><form data-form="search" style="flex:1"><input class="in" name="q" value="${esc(ST.q)}" placeholder="Search names, codes, trades…"></form></section>
      <section class="card tight"><div class="sk-tw"><table class="tb lb-wk"><thead><tr><th>Name</th><th>Trade</th><th>Gang</th><th>Employer</th><th>Site</th><th>Id</th></tr></thead><tbody>${(wk.workers || []).map(w =>
        `<tr class="sk-click" data-go="workers/${esc(w.id)}"><td><b>${esc(w.name)}</b>${w.code ? ` <span class="mut">· ${esc(w.code)}</span>` : ''}</td><td>${esc(w.trade || '—')}</td><td>${esc(w.gang || '—')}</td><td>${esc(w.employer)}</td><td>${esc(w.site || '—')}</td><td>${w.id_last4 ? '…' + esc(w.id_last4) : '—'}</td></tr>`).join('') || `<tr><td colspan="6">${empty('No workers yet.')}</td></tr>`}</tbody></table></div></section>
      ${CAN() ? `<section class="sk-2"><div class="card"><h2 class="sk-h">Add a worker</h2><form data-form="worker" class="sk-grid">${fld('name', 'Name', '', 'required maxlength="120"')}${fld('trade', 'Trade', '', 'maxlength="60" placeholder="Mason, helper, bar bender"')}
          ${fld('skill', 'Skill grade', '', 'maxlength="30" placeholder="skilled, semi-skilled"')}${fld('gang', 'Gang', '', 'maxlength="60"')}${sel('employer', 'Employer', empOpts(), '')}${sel('site', 'Site', siteOpts('—'), '')}
          ${fld('code', 'Your code', '', 'maxlength="30"')}${fld('language', 'Payslip language', '', 'maxlength="10" placeholder="mr, hi, en"')}${fld('id_last4', 'Id - last 4 only', '', 'maxlength="4"')}${fld('bank_last4', 'Bank account - last 4 only', '', 'maxlength="4"')}
          <div class="wide sk-acts"><span class="mut">The full numbers stay in your Pehchaan Locker, never here.</span><button class="btn soft">Add</button></div></form>
          <form data-form="importworkers" class="sk-grid">${area('text', 'Or paste your sheet / the contractor\'s register (CSV)', 'name,trade,skill,gang,employer,site\nRaju Kamble,Mason,skilled,Gang 5,,Tower B', 4)}<div class="wide sk-acts"><span></span><button class="btn soft">Import</button></div></form></div>
        <div class="card"><h2 class="sk-h">Add a paper</h2><form data-form="paper" class="sk-grid">${sel('whose', 'Whose', [['worker', 'A worker'], ['employer', 'A subcontractor'], ['company', 'Your company'], ['site', 'A site']], 'worker')}${fld('owner', 'Name (worker / subcontractor / site)', '', 'maxlength="120"')}
          ${sel('kind', 'Kind', [['induction', 'Site induction'], ['work_permit', 'Work permit / visa'], ['skills', 'Skills card'], ['medical', 'Medical'], ['right_to_work', 'Right to work'], ['licence', 'Licence'], ['registration', 'Registration'], ['insurance', 'Insurance'], ['other', 'Other']], 'induction')}
          ${fld('name', 'Name on it', '', 'maxlength="120"')}${fld('number', 'Number (only the last 4 are kept)', '', 'maxlength="40"')}${fld('issuer', 'Issued by', '', 'maxlength="120"')}${fld('valid_from', 'Valid from', '', 'type="date"')}${fld('valid_to', 'Valid to', '', 'type="date"')}
          <div class="wide sk-acts"><span class="mut">Or send a photo of it to the chat: Hoola reads what it can and leaves the rest blank.</span><button class="btn soft">Save</button></div></form></div></section>` : ''}`;
  }
  function pWorker(id) {
    const d = lazy('worker:' + id, 'worker', {id});
    if (!d) return loading();
    if (d.error) return failed(d);
    return `<a class="md-back" href="#/workers">${svg(IC.back)}Workers &amp; papers</a>
      <section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">${esc(d.name)}</h1><p class="lead">${esc([d.trade, d.skill, d.gang, d.employer, d.site, d.id_last4 && 'id …' + d.id_last4, d.bank_last4 && 'bank …' + d.bank_last4, d.language && 'payslip in ' + d.language].filter(Boolean).join(' · '))}</p></div>${ask('Worker ' + d.name)}</section>
      <section class="sk-3">
        <div class="card"><h2 class="sk-h">Papers</h2>${(d.papers || []).length ? d.papers.map(p => `<div class="cs-row"><span style="flex:1">${esc(p.name)}${p.number_last4 ? ` <span class="mut">…${esc(p.number_last4)}</span>` : ''}<div class="mut sk-sub">${esc(p.valid_to ? 'to ' + dmy(p.valid_to) : 'no end date')}</div></span>${p.lapsed ? tag('lapsed', 'bad') : p.days_left !== null && p.days_left <= 30 ? tag(p.days_left + ' d', 'warn') : ''}</div>`).join('') : empty('No papers yet.')}</div>
        <div class="card"><h2 class="sk-h">Rates</h2>${(d.rates || []).length ? d.rates.map(r => `<div class="cs-row"><span style="flex:1">${esc(r.kind === 'floor' ? 'Minimum' : 'Pay')} · ${money(r.rate, 2)} a ${esc(r.basis)}<div class="mut sk-sub">${esc(r.source || 'no source written')} · from ${esc(dmy(r.wef))}</div></span></div>`).join('') : empty('No rate for this trade yet.')}</div>
        <div class="card"><h2 class="sk-h">Advances</h2>${(d.advances || []).length ? d.advances.map(a => `<div class="cs-row"><span style="flex:1">${money(a.amount)} on ${esc(dmy(a.day))}<div class="mut sk-sub">given by ${esc(a.given_by)} · ${money(a.left)} left</div></span></div>`).join('') : empty('No advance.')}
          ${CAN() ? `<details class="sk-more"><summary>Record an advance you gave</summary><form data-form="advance" data-id="${esc(d.id)}" class="sk-grid">${fld('amount', 'Amount', '', 'inputmode="decimal" required')}${fld('per_run', 'Recover per run (blank = as the cap allows)', '', 'inputmode="decimal"')}${fld('note', 'Note', '', 'maxlength="200"')}<label class="sk-lab">Given by${who()}</label><div class="wide sk-acts"><span class="mut">Recovered from wages, never above your cap.</span><button class="btn soft">Record</button></div></form></details>` : ''}</div>
      </section>
      <section class="card"><h2 class="sk-h">Last marks</h2>${(d.marks || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Day</th><th>Site</th><th>Mark</th><th class="num">OT h</th><th>By</th><th>Source</th></tr></thead><tbody>${d.marks.map(m => `<tr><td>${esc(dmy(m.day))}</td><td>${esc(m.site)}</td><td>${tag(m.value === 1 ? 'P' : m.value === 0.5 ? '½' : 'A', m.value ? 'ok' : '')}${m.corrects ? ' ' + tag('correction: ' + m.reason, 'warn') : ''}</td><td class="num">${num(m.ot_hours)}</td><td>${esc(m.who)}</td><td>${esc(m.source)}</td></tr>`).join('')}</tbody></table></div>` : empty('Not marked yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- wages */
  const RSTEP = ['Prepared', 'Checked', 'Approved', 'Payment file', 'Paid'];
  function rsteps(at) { return `<div class="sk-stepbar">${RSTEP.map((s, i) => `<span class="sk-step${i < at ? ' d' : i === at ? ' c' : ''}"><span class="n">${i < at ? '✓' : i + 1}</span>${esc(s)}</span>`).join('')}</div>`; }
  function pWages() {
    if (ST.arg) return pRun(ST.arg);
    const rn = lazy('runs', 'runs', {}), ad = lazy('advances', 'advances', {});
    if (!rn || !ad) return loading();
    const t0 = todayIso(), ws = new Date(t0 + 'T00:00'), wsd = ((ws.getDay() + 6) % 7 - (SET().week_start || 0) + 7) % 7;
    const pstart = shift(t0, -wsd - 7), pend = shift(t0, -wsd - 1);
    const st = {draft: '', checked: 'v', approved: 'ok', paid: 'ok', cancelled: ''};
    return `<section><h1 class="sd-h">Wages</h1><p class="lead">The working paper per person: units × your rate, overtime by ${esc((SET().ot || {}).source ? 'your country\'s rule' : 'your contract')}, deductions from your rows, advances under your ${num(SET().advance_cap)}% cap. Prepared, checked and approved by three people; any change afterwards sends it back to draft.</p></section>${ro()}
      ${CAN() ? `<section class="card"><h2 class="sk-h">Prepare a wage run</h2><form data-form="draftrun" class="sk-grid three">${fld('start', 'From', pstart, 'type="date" required')}${fld('end', 'To', pend, 'type="date" required')}${sel('employer', 'For', empOpts(), '')}${sel('site', 'Site', siteOpts('Every site'), '')}
        ${fld('who', 'Prepared by (blank = Hoola)', '', 'maxlength="80"')}<div class="wide sk-acts"><span class="mut">Built from the muster; every line is checked against the minimum rate.</span><button class="btn">Prepare</button></div></form></section>` : ''}
      <section class="card tight"><div class="sk-tw"><table class="tb"><thead><tr><th>Run</th><th>For</th><th>Period</th><th class="num">People</th><th class="num">Net</th><th>Status</th></tr></thead><tbody>${(rn.rows || []).map(r =>
        `<tr class="sk-click" data-go="wages/${esc(r.id)}"><td><b>${esc(r.number)}</b></td><td>${esc(r.employer)} · ${esc(r.site)}</td><td>${esc(dmy(r.start))} – ${esc(dmy(r.end))}</td><td class="num">${num(r.people)}</td><td class="num">${money(r.total)}</td><td>${tag(r.status, st[r.status])}${r.bad && r.status === 'draft' ? ' ' + tag(pl(r.bad, 'check'), 'bad') : ''}</td></tr>`).join('') || `<tr><td colspan="6">${empty('No wage run yet.')}</td></tr>`}</tbody></table></div></section>
      <section class="card"><h2 class="sk-h">Advances</h2>${(ad.rows || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Worker</th><th>Given</th><th class="num">Amount</th><th class="num">Recovered</th><th class="num">Left</th></tr></thead><tbody>${ad.rows.map(a => `<tr><td>${esc(a.worker)}</td><td>${esc(dmy(a.day))} · ${esc(a.given_by)}</td><td class="num">${money(a.amount)}</td><td class="num">${money(a.recovered)}</td><td class="num">${money(a.left)}</td></tr>`).join('')}</tbody></table></div>` : empty('No advances. Record one on the worker\'s page.')}</section>`;
  }
  function pRun(id) {
    const v = lazy('run:' + id, 'run', {id});
    if (!v) return loading();
    if (v.error) return failed(v);
    const at = {draft: 0, checked: 1, approved: 3, paid: 5, cancelled: 0}[v.status] ?? 0;
    const T = v.totals || {};
    const ps = ST.cache['slips:' + id];
    return `<a class="md-back" href="#/wages">${svg(IC.back)}Wages</a>
      <section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">${esc(v.number)} · ${esc(v.employer)}</h1><p class="lead">${esc(v.site)} · ${esc(dmy(v.start))} to ${esc(dmy(v.end))} · overtime: ${esc((v.ot || {}).say || '')}</p></div>${ask('Wage run ' + v.number)}</section>
      ${v.stale ? `<p class="lb-warn">This run changed after it was ${esc(v.log.length ? 'checked or approved' : 'signed')} - a mark, a rate or an advance moved - so it is a draft again and needs checking and approving again.</p>` : ''}
      ${rsteps(at)}
      <section class="cs-4 grid" style="display:grid;gap:16px">
        ${kpi('Net to pay', money(v.total), `${pl((v.lines || []).length, 'person', 'people')}`)}
        ${kpi('Gross', money(T.gross), `basic ${money(T.basic)} · overtime ${money(T.ot_pay)}`)}
        ${kpi('Deductions + advances', money((T.deduction_total || 0) + (T.advance || 0)), `employer contributions ${money(T.employer_contrib)}`)}
        ${kpi('Line checks to fix', v.bad ? num(v.bad) : 'None', v.bad ? 'fix before it can be checked' : 'every line checked', v.bad ? 'bad' : 'ok')}
      </section>
      <section class="card tight"><div class="sk-tw"><table class="tb"><thead><tr><th>Person</th><th class="num">Days</th><th class="num">OT h</th><th class="num">Rate</th><th class="num">Basic</th><th class="num">Overtime</th><th class="num">Deductions</th><th class="num">Advance</th><th class="num">Net</th><th>Checks</th></tr></thead><tbody>${(v.lines || []).map(ln =>
        `<tr><td><b>${esc(ln.name)}</b><div class="mut sk-sub">${esc(ln.trade || '')}</div></td><td class="num">${num(ln.days)}</td><td class="num">${num(ln.ot_hours)}${ln.ot_x ? `<div class="mut sk-sub">${num(ln.ot_x)}×</div>` : ''}</td><td class="num">${ln.rate === null ? '—' : money(ln.rate, 2)}<div class="mut sk-sub">a ${esc(ln.basis || '—')}</div></td>
          <td class="num">${money(ln.basic, 2)}</td><td class="num">${money(ln.ot_pay, 2)}</td><td class="num">${money(ln.deduction_total, 2)}</td><td class="num">${money(ln.advance, 2)}</td><td class="num"><b>${money(ln.net, 2)}</b></td>
          <td style="min-width:220px">${(ln.checks || []).filter(c => c.sev !== 'ok').map(c => `<div class="sk-ck"><span class="sk-ic ${sev(c.sev)}">${c.sev === 'info' ? 'i' : '!'}</span><span>${esc(c.text)}</span></div>`).join('') || tag('ok', 'ok')}</td></tr>`).join('') || `<tr><td colspan="10">${empty('Nobody was mustered for this employer in this period.')}</td></tr>`}</tbody></table></div></section>
      ${(v.changes || []).length ? `<section class="card"><h2 class="sk-h">Changes from the last period</h2>${v.changes.map(c => `<div class="cs-row"><span>${esc(c)}</span></div>`).join('')}</section>` : ''}
      ${CAN() ? `<section class="card"><h2 class="sk-h">${v.status === 'draft' ? 'Check the run' : v.status === 'checked' ? 'Approve the run' : v.status === 'approved' ? 'Pay it yourself, then record it' : v.status === 'paid' ? 'Paid' : 'Cancelled'}</h2>
        ${v.status === 'draft' ? `<form class="sk-inline" data-form="checkrun" data-id="${esc(v.id)}">${who('Checked by')}<button class="btn"${v.bad ? ' disabled' : ''}>Mark as checked</button></form><p class="cs-note">Prepared by ${esc(v.prepared_by)}. The checker must be another person.</p>` : ''}
        ${v.status === 'checked' ? `<form class="sk-inline" data-form="approverun" data-id="${esc(v.id)}">${who('Approved by')}${v.second_needed ? '<input class="in sk-who" name="who2" placeholder="Second approver" required>' : ''}<button class="btn">Approve</button></form><p class="cs-note">Checked by ${esc(v.checked_by)}. The approver must be a third person${v.second_needed ? '; above your limit a second approver signs too' : ''}.</p>` : ''}
        ${['approved', 'paid'].includes(v.status) ? `<div class="sk-acts"><span>Approved by ${esc(v.approved_by)}${v.approved_by2 ? ' and ' + esc(v.approved_by2) : ''}.</span><span style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-file="csv">Bank CSV</button>${v.rail.format !== 'csv' ? `<button class="btn soft sm" type="button" data-file="${esc(v.rail.format)}">${esc(v.rail.name)}</button>` : ''}<button class="btn soft sm" type="button" data-slips="${esc(v.id)}">Payslips</button></span></div>
          ${v.rail.note ? `<p class="cs-note">${esc(v.rail.note)}</p>` : ''}
          ${v.rail.format === 'in_bulk' ? `<details class="sk-more"><summary>Bank bulk file with account numbers (typed here, for this one file)</summary><form data-form="bulk" data-id="${esc(v.id)}" class="sk-grid">${(v.lines || []).filter(l => l.net > 0).map(l => `<label class="sk-lab">${esc(l.name)}${l.bank_last4 ? ' · …' + esc(l.bank_last4) : ''}<input class="in" name="acc_${esc(l.worker_id)}" inputmode="numeric" autocomplete="off" placeholder="Account number"></label><label class="sk-lab">IFSC<input class="in" name="ifsc_${esc(l.worker_id)}" autocomplete="off" maxlength="11"></label>`).join('')}<div class="wide sk-acts"><span class="mut">Never kept, never sent to the chat.</span><button class="btn soft">Make the file</button></div></form></details>` : ''}` : ''}
        ${v.status === 'approved' ? `<form class="sk-grid" data-form="paid" data-id="${esc(v.id)}" style="margin-top:12px">${fld('ref', 'The bank\'s reference (or the WPS report number)', '', 'required maxlength="80"')}${fld('on', 'Paid on', todayIso(), 'type="date"')}${fld('failed', 'Failed payments (name: reason; one a line)', '', 'maxlength="600"')}<label class="sk-lab">Recorded by${who()}</label><div class="wide sk-acts"><span class="mut">Hoola moves no money: record what your bank confirmed.</span><button class="btn">Record as paid</button></div></form>` : ''}
        ${v.status === 'paid' ? `<p class="cs-note">Paid on ${esc(dmy(v.paid.on))}, reference ${esc(v.paid.ref)}, recorded by ${esc(v.paid.by)}${Object.keys(v.paid.failed || {}).length ? ` · still to pay: ${esc(Object.keys(v.paid.failed).length)}` : ''}.</p>` : ''}
        ${!['paid', 'cancelled'].includes(v.status) ? `<details class="sk-rev" style="margin-top:10px"><summary>Cancel this run</summary><form class="sk-inline" data-form="cancelrun" data-id="${esc(v.id)}">${who()}<input class="in" name="reason" placeholder="Why"><button class="btn soft sm">Cancel the run</button></form></details>` : ''}
      </section>` : ''}
      ${ps ? `<section class="card"><h2 class="sk-h">Payslips</h2><div class="sk-3">${(ps.slips || []).map(p => `<div class="lb-slip"><h3>${esc(p.name)}</h3><p class="mut sk-sub" style="margin:0 0 6px">${esc(p.head)}${p.language && p.language !== 'en' ? ' · ask the chat for it in ' + esc(p.language) : ''}</p>${p.rows.map(([a, b]) => `<div><span>${esc(a)}</span><span>${esc(b)}</span></div>`).join('')}</div>`).join('')}</div></section>` : ''}
      <section class="card"><h2 class="sk-h">History</h2>${(v.log || []).map(x => `<div class="cs-row"><span class="mut sk-when">${esc(S(x.at).slice(5, 16).replace('T', ' '))}</span><span>${esc(x.text)}</span></div>`).join('') || empty('—')}</section>`;
  }

  /* ---------------------------------------------------------------- levies & tax */
  function pLevies() {
    const rl = lazy('rules', 'rules', {}), lv = lazy('levies', 'levies', {}), py = lazy('payments', 'payments', {}), cal = lazy('cal', 'calendar', {}), pk = lazy('pack', 'pack', {});
    if (!rl || !lv || !py || !cal || !pk) return loading();
    const mine = rl.rows || [], have = new Set(mine.map(r => r.pack_id));
    const prows = [...(pk.levies || []), ...(pk.withholding || [])];
    const levyRules = mine.filter(r => r.kind === 'levy'), whRules = mine.filter(r => r.kind === 'withholding');
    const due = (lv.rows || []).filter(x => x.status === 'due');
    const m = todayIso().slice(0, 7);
    const toDep = (py.rows || []).filter(p => p.withheld && !p.deposited);
    return `<section><h1 class="sd-h">Cess, levies and tax withheld</h1><p class="lead">Every figure from a rule row you can open. A country row nobody has checked says "check this" and is never used until a person writes its source. Paying and filing are yours.</p></section>${ro()}
      <section class="cs-4 grid" style="display:grid;gap:16px">
        ${kpi('Levies due', money(due.reduce((a, x) => a + x.amount, 0)), due.length ? `${pl(due.length, 'bill')} · first by ${dmy(due.map(x => x.due).sort()[0])}` : 'nothing due')}
        ${kpi('Levies paid', money((lv.rows || []).filter(x => x.status === 'paid').reduce((a, x) => a + x.amount, 0)), 'receipts kept (last 4)')}
        ${kpi('Tax to deposit', money(toDep.reduce((a, p) => a + p.withheld, 0)), toDep.length ? `${pl(toDep.length, 'payment')} withheld` : 'nothing waiting')}
        ${kpi('Next on the calendar', (cal.items || [])[0] ? esc(dmy(cal.items[0].due)) : '—', (cal.items || [])[0] ? cal.items[0].what : '')}
      </section>
      <section class="card"><h2 class="sk-h">Rules for ${esc(SET().country ? (new Intl.DisplayNames(undefined, {type: 'region'}).of(SET().country) || SET().country) : 'your country')}</h2>
        ${prows.map(r => { const own = mine.find(x => x.pack_id === r.id);
          return `<div class="cs-row" style="align-items:flex-start"><span style="flex:1"><b>${esc(r.name)}</b>${r.region ? ' · ' + esc(r.region) : ''}<div class="mut sk-sub">${esc(r.note || (r.rates ? Object.entries(r.rates).map(([k, v]) => `${k} ${v}%`).join(' · ') : ''))}</div><div class="mut sk-sub">${esc(r.source)}</div>
            ${own ? `<div class="sk-sub">${tag('yours', 'ok')} checked by ${esc(own.checked_by)} on ${esc(dmy(own.checked_on))} · review by ${esc(dmyy(own.review_by))}${own.stale ? ' ' + tag('past review - check again', 'bad') : ''}</div>` : ''}</span>
            ${r.check ? tag('check this', 'warn') : tag('checked', 'ok')}
            ${CAN() && (!own || own.stale) ? `<details class="sk-rev"><summary>Use it</summary><form class="sk-inline" data-form="usepack" data-id="${esc(r.id)}">${r.check ? '<input class="in" name="source" placeholder="The source you checked" required>' : ''}${r.rate_pct === null && !r.rates ? '<input class="in" name="rate_pct" inputmode="decimal" placeholder="Rate %" required>' : ''}${who('Checked by')}<button class="btn soft sm">Use it</button></form></details>` : ''}</div>`; }).join('') || empty('No country rows for your country yet: write your own rule with its source.')}
        ${CAN() ? `<details class="sk-more"><summary>Write your own rule</summary><form data-form="rule" class="sk-grid three">${sel('kind', 'Kind', [['levy', 'A levy'], ['withholding', 'Tax withheld']], 'levy')}${fld('name', 'Name', '', 'required maxlength="120"')}${sel('base', 'Levy base', [['cost_of_work', 'Cost of work'], ['gross_wages', 'Gross wages'], ['per_head', 'Per head'], ['per_permit', 'Per permit']], 'cost_of_work')}
          ${fld('rate_pct', 'Levy rate %', '', 'inputmode="decimal"')}${fld('per_unit', 'Amount per head / permit', '', 'inputmode="decimal"')}${fld('rates', 'Withholding rates (status=% ; …)', '', 'placeholder="individual=1; firm=2; no_id=20"')}
          ${fld('source', 'Source', '', 'required maxlength="300"')}<label class="sk-lab">Checked by${who()}</label><div class="wide sk-acts"><span></span><button class="btn soft">Save the rule</button></div></form></details>` : ''}</section>
      <section class="sk-2">
        <div class="card"><h2 class="sk-h">Levies</h2>${(lv.rows || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Bill</th><th class="num">Base</th><th class="num">Levy</th><th>Paid</th></tr></thead><tbody>${lv.rows.map(x => `<tr><td>${esc(x.ref)} · ${esc(dmy(x.day))}<div class="mut sk-sub">${esc(x.rule)}</div></td><td class="num">${money(x.base)}</td><td class="num">${money(x.amount)}</td>
            <td>${x.status === 'paid' ? `<span class="mut">receipt …${esc(x.receipt_last4)} · ${esc(dmy(x.paid_on))}</span>` : `${tag('due ' + dmy(x.due), x.late ? 'bad' : 'warn')}${CAN() ? `<details class="sk-rev"><summary>Record paid</summary><form class="sk-inline" data-form="levypaid" data-id="${esc(x.id)}"><input class="in" name="receipt" placeholder="Challan / receipt no." required>${who()}<button class="btn soft sm">Paid</button></form></details>` : ''}`}</td></tr>`).join('')}</tbody></table></div>` : empty('No levy yet.')}
          ${CAN() && levyRules.length ? `<form data-form="levy" class="sk-grid" style="margin-top:12px">${sel('rule', 'Rule', levyRules.map(r => [r.id, r.name]), '')}${fld('ref', 'Bill / certificate', '', 'required maxlength="80" placeholder="RA bill 14"')}${fld('base_amount', 'Base (cost of work / gross wages / heads)', '', 'inputmode="decimal" required')}${fld('day', 'Bill date', todayIso(), 'type="date"')}${fld('base_source', 'Where the base comes from', '', 'maxlength="200"')}<div class="wide sk-acts"><span></span><button class="btn soft">Work out the levy</button></div></form>` : ''}</div>
        <div class="card"><h2 class="sk-h">Tax withheld from subcontractors</h2>${(py.rows || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Subcontractor</th><th class="num">Paid</th><th class="num">Withheld</th></tr></thead><tbody>${py.rows.map(p => `<tr><td>${esc(p.employer)} · ${esc(dmy(p.day))}<div class="mut sk-sub">${esc(p.why)}</div></td><td class="num">${money(p.amount)}</td><td class="num">${money(p.withheld)}${p.deposited ? `<div class="mut sk-sub">deposited ${esc(dmy(p.deposited))}</div>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No subcontractor payment recorded yet.')}
          ${CAN() && whRules.length ? `<form data-form="payment" class="sk-grid" style="margin-top:12px">${sel('employer', 'Subcontractor', empOpts().filter(e => !e[1].includes('(own gangs)')), '')}${fld('amount', 'Payment', '', 'inputmode="decimal" required')}${fld('materials', 'Of which materials', '', 'inputmode="decimal"')}${fld('day', 'Date', todayIso(), 'type="date"')}${fld('ref', 'Reference', '', 'maxlength="80"')}<div class="wide sk-acts"><span class="mut">The rate follows the status you checked on Subcontractors.</span><button class="btn soft">Work out the tax</button></div></form>` : ''}
          ${CAN() && toDep.length ? `<details class="sk-more"><summary>Record the month's deposit</summary><form class="sk-inline" data-form="deposit">${fld('month', 'Month', m, 'type="month" required')}<input class="in" name="receipt" placeholder="Challan / receipt no." required>${who()}<button class="btn soft sm">Deposited</button></form></details>` : ''}</div>
      </section>
      <section class="card"><h2 class="sk-h">Filing calendar</h2>${(cal.items || []).length ? cal.items.map(i => `<div class="cs-row"><span class="mut sk-when">${esc(dmy(i.due))}</span><span style="flex:1">${esc(i.what)}${i.amount ? ' · ' + money(i.amount) : ''}${i.source ? `<div class="mut sk-sub">${esc(i.source)}</div>` : ''}</span>${i.check ? tag('check this', 'warn') : ''}${i.late ? tag('late', 'bad') : ''}
        ${CAN() && i.kind === 'file' && !i.filed ? `<details class="sk-rev"><summary>Filed</summary><form class="sk-inline" data-form="filed" data-id="${esc(i.key)}"><input class="in" name="ref" placeholder="Acknowledgement no.">${who()}<button class="btn soft sm">Record</button></form></details>` : ''}</div>`).join('') : empty('Nothing on the calendar.')}</section>`;
  }

  /* ---------------------------------------------------------------- subcontractors */
  function pSubs() {
    const t0 = todayIso(), wsd = ((new Date(t0 + 'T00:00').getDay() + 6) % 7 - (SET().week_start || 0) + 7) % 7;
    if (!ST.period) ST.period = {start: shift(t0, -wsd - 7), end: shift(t0, -wsd - 1)};
    const p = lazy(`period:${ST.period.start}|${ST.period.end}`, 'period', ST.period);
    const subs = (K().employers || []).filter(e => e.kind === 'sub');
    if (!p) return loading();
    if (p.error) return failed(p);
    const st = {ok: '✓', part: '½', missing: '–'};
    return `<section class="sk-headrow"><div style="flex:1"><h1 class="sd-h">Subcontractor labour</h1><p class="lead">Each period, proof that each subcontractor's people on your site were paid - tied to the muster of their people. Gaps are named; nothing is held by itself.</p></div></section>${ro()}
      <section class="sk-filters"><form data-form="period" class="sk-inline">${fld('start', 'From', ST.period.start, 'type="date"')}${fld('end', 'To', ST.period.end, 'type="date"')}<button class="btn soft sm">Show</button></form></section>
      <section class="card tight"><div class="sk-tw"><table class="tb lb-mx"><thead><tr><th>Subcontractor</th><th class="num">People</th><th>Wage register</th><th>Payment proof</th><th>Contributions</th><th>Headcount</th><th>Decision</th></tr></thead><tbody>${(p.rows || []).map(r =>
        `<tr><td><b>${esc(r.employer)}</b>${r.gaps.length ? `<div class="mut sk-sub">${esc(r.gaps.join('; '))}</div>` : '<div class="mut sk-sub">every paper is in</div>'}</td><td class="num">${num(r.people)}</td>${r.items.map(i => `<td class="st"><span class="lb-st ${i.state}" title="${esc(i.label + ': ' + i.cover + ' of ' + i.of)}">${st[i.state]}${i.state === 'part' ? ' ' + num(i.cover) + '/' + num(i.of) : ''}</span></td>`).join('')}
          <td>${r.decision ? tag(r.decision.status + (r.decision.who ? ' · ' + r.decision.who : ''), r.decision.status === 'hold' ? 'bad' : r.decision.status === 'release' ? 'ok' : 'warn') : ''}${CAN() ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"><button class="btn soft sm" type="button" data-hold="${esc(r.employer_id)}">Draft the note</button></div>` : ''}
            ${CAN() && r.decision && r.decision.status === 'draft' ? `<details class="sk-rev"><summary>Decide</summary><p class="mut sk-sub" style="white-space:pre-wrap">${esc(r.decision.text)}</p><form class="sk-inline" data-form="decide" data-id="${esc(r.decision.id)}">${who()}<input class="in" name="note" placeholder="Note"><button class="btn soft sm" name="act" value="release">Release</button><button class="btn soft sm" name="act" value="hold">Hold</button><button class="btn soft sm" name="act" value="direct">Pay their people directly</button></form></details>` : ''}</td></tr>`).join('') || `<tr><td colspan="7">${empty('No subcontractor had people on your sites in this period.')}</td></tr>`}</tbody></table></div></section>
      ${CAN() ? `<section class="sk-2"><div class="card"><h2 class="sk-h">Add evidence they sent</h2><form data-form="evidence" class="sk-grid">${sel('employer', 'Subcontractor', subs.map(e => [e.id, e.name]), '')}${sel('kind', 'Paper', [['register', 'Wage register'], ['payment', 'Payment proof'], ['contribution', 'Contribution receipts'], ['headcount', 'Headcount sheet']], 'payment')}
          ${fld('people', 'People it covers', '', 'inputmode="numeric"')}${fld('ref', 'Reference', '', 'maxlength="80"')}${area('names', 'Or the names on it (one a line)', 'Vinod Shinde\nPrakash Jadhav', 3)}
          <div class="wide sk-acts"><span class="mut">Or send the file to the chat: Hoola reads it as data and fills this in.</span><button class="btn soft">Save</button></div></form></div>
        <div class="card"><h2 class="sk-h">Subcontractors</h2>${subs.map(e => `<div class="cs-row"><span style="flex:1"><b>${esc(e.name)}</b><div class="mut sk-sub">${esc([e.status || 'tax status not set', e.tax_id_last4 && 'id …' + e.tax_id_last4, e.tax_id_ok ? `checked ${dmy(e.checked_on)} by ${e.checked_by}` : 'not verified'].filter(Boolean).join(' · '))}</div></span>${e.tax_id_ok ? tag('verified', 'ok') : tag('not verified', 'warn')}</div>`).join('') || empty('No subcontractors yet.')}
          <details class="sk-more"><summary>Add or verify a subcontractor</summary><form data-form="employer" class="sk-grid">${fld('name', 'Name', '', 'required maxlength="120"')}${sel('status', 'Tax status', [['', '—'], ['individual', 'Individual'], ['firm', 'Firm / company'], ['registered', 'Registered (UK CIS)'], ['unregistered', 'Unregistered'], ['gross', 'Gross payment status']], '')}
            ${fld('tax_id', 'Tax id (only the last 4 are kept)', '', 'maxlength="20"')}${sel('tax_id_ok', 'Verified', [['', 'Not yet'], ['1', 'Yes - I checked it']], '')}<label class="sk-lab">Checked by<input class="in" name="checked_by" maxlength="80"></label><div class="wide sk-acts"><span></span><button class="btn soft">Save</button></div></form></details></div></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- reports */
  function pReports() {
    const t0 = todayIso();
    if (!ST.reg) ST.reg = {start: t0.slice(0, 8) + '01', end: t0};
    const r = lazy(`reg:${ST.reg.start}|${ST.reg.end}`, 'registers', ST.reg), co = lazy('closeout', 'close_out', {});
    if (!r || !co) return loading();
    if (r.error) return failed(r);
    return `<section><h1 class="sd-h">Reports</h1><p class="lead">The muster register and the wage register for any period - what an inspector or the client's auditor asks for - and what is left before a project closes.</p></section>
      <section class="sk-filters"><form data-form="reg" class="sk-inline">${fld('start', 'From', ST.reg.start, 'type="date"')}${fld('end', 'To', ST.reg.end, 'type="date"')}<button class="btn soft sm">Show</button></form></section>
      <section class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Muster register</h2><button class="btn soft sm" type="button" data-csv="muster">Export</button></div>${(r.muster || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Person</th><th class="num">Days</th></tr></thead><tbody>${r.muster.map(x => `<tr><td>${esc(x.name)}</td><td class="num">${num(x.days)}</td></tr>`).join('')}</tbody></table></div>` : empty('Nobody marked in this period.')}</section>
      <section class="card"><div class="sk-ch"><h2 class="sk-h" style="flex:1">Wage register</h2><button class="btn soft sm" type="button" data-csv="wages">Export</button></div>${(r.wages || []).length ? `<div class="sk-tw"><table class="tb"><thead><tr><th>Run</th><th>Person</th><th class="num">Days</th><th class="num">Gross</th><th class="num">Net</th><th>Paid</th></tr></thead><tbody>${r.wages.map(x => `<tr><td>${esc(x.run)}</td><td>${esc(x.name)}</td><td class="num">${num(x.days)}</td><td class="num">${money(x.gross, 2)}</td><td class="num">${money(x.net, 2)}</td><td>${esc(x.paid_ref || x.status)}</td></tr>`).join('')}</tbody></table></div>` : empty('No approved run in this period.')}</section>
      <section class="card"><h2 class="sk-h">Close-out</h2><p class="lead" style="font-size:14px">${esc(co.say || '')}</p>
        ${[['Open wage runs', (co.open_runs || []).map(x => `${x.number} · ${x.status}`)], ['Levies not paid', (co.levies_due || []).map(x => `${x.ref} · ${money(x.amount)}`)],
           ['Advances not recovered', (co.advances_left || []).map(x => `${x.worker} · ${money(x.left)}`)], ['Filings', (co.filings || []).map(x => `${x.what} · ${dmy(x.due)}`)],
           ['Evidence missing', (co.evidence_gaps || []).map(x => x.say)], ['Licences to surrender', (co.licences || []).map(x => `${x.owner || 'Your company'} · ${x.name}`)]].map(([t, l]) =>
           `<h3 class="sk-h3">${esc(t)} · ${l.length}</h3>${l.slice(0, 8).map(x => `<div class="cs-row"><span>${esc(x)}</span></div>`).join('') || '<p class="mut" style="margin:0;font-size:13px">None</p>'}`).join('')}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = SET(), pk = lazy('pack', 'pack', {}), rt = lazy('rates', 'rates', {});
    if (!pk || !rt) return loading();
    const o = s.ot || {};
    return `<section><h1 class="sd-h">Settings</h1><p class="lead">Your country and region decide the overtime rule, the papers, the levies and the withholding. Minimum rates are yours to write, each with its source.</p></section>${ro()}
      ${CAN() ? `<section class="card"><h2 class="sk-h">Company</h2><form data-form="settings" class="sk-grid three">${fld('company', 'Company', s.company, 'maxlength="120"')}${fld('project', 'Project', s.project, 'maxlength="120"')}${fld('country', 'Country (2 letters)', s.country, 'maxlength="2" placeholder="IN, GB, US, AE"')}
        ${fld('region', 'State / region', s.region, 'maxlength="40" placeholder="MH, QLD, Bavaria"')}${fld('currency', 'Currency', s.currency, 'maxlength="3"')}${sel('pay_cycle', 'Pay period', [['weekly', 'Weekly'], ['fortnightly', 'Fortnightly'], ['monthly', 'Monthly']], s.pay_cycle)}
        ${sel('week_start', 'Week starts', [[0, 'Monday'], [6, 'Sunday'], [5, 'Saturday']], s.week_start)}${fld('day_hours', 'Normal hours a day', s.day_hours, 'inputmode="decimal"')}${fld('week_hours', 'Normal hours a week', s.week_hours, 'inputmode="decimal"')}
        ${fld('max_day_hours', 'Flag a day above (hours)', s.max_day_hours, 'inputmode="decimal"')}${fld('ot_x', 'Your contract\'s overtime multiplier', s.ot_x || '', 'inputmode="decimal" placeholder="0 = the country rule"')}${fld('cutoff', 'Muster cut-off', s.cutoff, 'maxlength="5"')}
        ${fld('advance_cap', 'Advance recovery cap (% of pay)', s.advance_cap, 'inputmode="decimal"')}${fld('second_limit', 'Second approver above', s.second_limit || '', 'inputmode="decimal"')}${fld('gate_tol', 'Gate count tolerance (people)', s.gate_tol, 'inputmode="numeric"')}
        <div class="wide sk-acts"><span class="mut">Overtime now: ${esc(o.basis === 'contract' ? 'your contract decides' : `${num(o.x)}× beyond ${num(o.after)} hours a ${o.basis}`)} - ${esc(o.source || '')}${o.check ? ' (check this)' : ''}</span><button class="btn">Save</button></div></form></section>` : ''}
      <section class="sk-2">
        <div class="card"><h2 class="sk-h">Sites</h2>${(K().sites || []).map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(x.name)}</b><div class="mut sk-sub">${esc([x.project, x.region, x.planned && 'planned ' + x.planned + ' a day'].filter(Boolean).join(' · '))}</div></span></div>`).join('') || empty('No site yet.')}
          ${CAN() ? `<form data-form="site" class="sk-grid" style="margin-top:10px">${fld('name', 'Site', '', 'required maxlength="80"')}${fld('project', 'Project', '', 'maxlength="120"')}${fld('region', 'State / region', '', 'maxlength="40"')}${fld('planned', 'Planned headcount a day', '', 'inputmode="numeric"')}<div class="wide sk-acts"><span></span><button class="btn soft">Add the site</button></div></form>` : ''}</div>
        <div class="card"><h2 class="sk-h">Pay rates and minimum rates</h2>${(rt.rows || []).map(r => `<div class="cs-row"><span style="flex:1">${tag(r.kind === 'floor' ? 'minimum' : 'pay', r.kind === 'floor' ? 'v' : '')} <b>${esc(r.trade || r.skill || r.worker)}</b> · ${money(r.rate, 2)} a ${esc(r.basis)}<div class="mut sk-sub">${esc(r.source || 'no source written')} · from ${esc(dmy(r.wef))}${r.site ? ' · ' + esc(r.site) : ''}</div></span></div>`).join('') || empty('No rates yet.')}
          ${CAN() ? `<form data-form="rate" class="sk-grid" style="margin-top:10px">${sel('kind', 'Kind', [['pay', 'What you pay'], ['floor', 'The minimum (floor)']], 'pay')}${fld('trade', 'Trade', '', 'maxlength="60"')}${fld('skill', 'Skill grade', '', 'maxlength="30"')}${fld('rate', 'Rate', '', 'inputmode="decimal" required')}${sel('basis', 'Per', [['day', 'Day'], ['hour', 'Hour'], ['piece', 'Piece']], 'day')}${fld('wef', 'From', todayIso(), 'type="date"')}
            ${fld('source', 'Source (the notification, determination, award, your rate card)', '', 'maxlength="240"')}<div class="wide sk-acts"><span class="mut">Hoola never supplies a minimum rate from memory.</span><button class="btn soft">Save the rate</button></div></form>` : ''}</div>
      </section>
      <section class="card"><h2 class="sk-h">Deductions you apply</h2>${(s.deductions || []).map(d => `<div class="cs-row"><span style="flex:1"><b>${esc(d.name)}</b> · ${num(d.pct)}% of ${esc(d.base)}${d.cap ? ' up to ' + money(d.cap) : ''}${d.employer_pct ? ` · employer ${num(d.employer_pct)}%` : ''}<div class="mut sk-sub">${esc(d.source)}</div></span></div>`).join('') || empty('None yet.')}
        ${(pk.deductions || []).length ? `<h3 class="sk-h3">In your country (shown, not applied)</h3>${pk.deductions.map(d => `<div class="cs-row"><span style="flex:1">${esc(d.name)}${d.pct ? ' · ' + num(d.pct) + '%' : ''}<div class="mut sk-sub">${esc(d.source)}</div></span>${d.check ? tag('check this', 'warn') : ''}</div>`).join('')}` : ''}
        ${CAN() ? `<form data-form="deduction" class="sk-grid three" style="margin-top:10px">${fld('name', 'Name', '', 'required maxlength="60"')}${fld('pct', 'Rate %', '', 'inputmode="decimal" required')}${sel('base', 'Of', [['basic', 'Basic pay'], ['gross', 'Gross pay']], 'basic')}${fld('cap', 'Wage ceiling (blank = none)', '', 'inputmode="decimal"')}${fld('employer_pct', 'Employer share %', '', 'inputmode="decimal"')}${fld('source', 'Source', '', 'required maxlength="240"')}<div class="wide sk-acts"><span></span><button class="btn soft">Add the deduction</button></div></form>` : ''}</section>
      <section class="card"><h2 class="sk-h">Papers in ${esc(s.country || 'your country')}</h2>${(pk.papers || []).map(p => `<div class="cs-row"><span style="flex:1">${esc(p.name)} <span class="mut">· ${esc(p.whose)}</span><div class="mut sk-sub">${esc(p.source)}</div></span>${p.required ? tag('required at muster') : ''}${p.check ? tag('check this', 'warn') : ''}</div>`).join('')}
        <p class="cs-note">${esc(pk.note || '')}</p><p class="cs-note">Payment rail: ${esc((pk.rail || {}).name || '')}${(pk.rail || {}).check ? ' (check this)' : ''}.</p></section>`;
  }

  /* ---------------------------------------------------------------- actions */
  function saveBlob(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
  const csvCell = v => { const s = S(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  function csv(name, head, rows) { saveBlob(name, new Blob([[head, ...rows].map(r => r.map(csvCell).join(',')).join('\n')], {type: 'text/csv'})); }
  async function onPageClick(e) {
    const t = e.target;
    const mk = t.closest('[data-mark]');
    if (mk) { ST.pick[mk.dataset.mark] = Number(mk.dataset.v); showPage(true); return; }
    if (t.closest('[data-allp]')) { $('#lbPage').querySelectorAll('[data-mark]').forEach(b => { ST.pick[b.dataset.mark] = 1; }); showPage(true); return; }
    if (t.closest('select, input, textarea, label, summary')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const dy = t.closest('[data-day]'); if (dy) { ST.day = dy.dataset.day; ST.pick = {}; location.hash = '#/muster/' + ST.day; return; }
    const si = t.closest('[data-site]'); if (si) { ST.site = si.dataset.site; ST.pick = {}; showPage(true); return; }
    if (t.closest('[data-voice]')) { setCtx('Muster ' + dmy(ST.day)); ST.bar.value = ''; toast('Say or type the muster in the chat - the names as the foreman says them.'); return; }
    const fl = t.closest('[data-file]');
    if (fl) { try { const r = await run('payment_file', {id: ST.arg, format: fl.dataset.file}); saveBlob(r.name, new Blob([r.file], {type: 'text/csv'})); toast(r.say); } catch (err) { toast(err.message, true); } return; }
    const sl = t.closest('[data-slips]');
    if (sl) { try { ST.cache['slips:' + sl.dataset.slips] = await run('payslips', {id: sl.dataset.slips}); showPage(true); } catch (err) { toast(err.message, true); } return; }
    const hd = t.closest('[data-hold]');
    if (hd) { hd.disabled = true; try { const r = await run('draft_hold', {employer: hd.dataset.hold, ...ST.period}); await changed(r.say); } catch (err) { toast(err.message, true); hd.disabled = false; } return; }
    const cv = t.closest('[data-csv]');
    if (cv) {
      const r = ST.cache[`reg:${ST.reg.start}|${ST.reg.end}`] || {};
      if (cv.dataset.csv === 'muster') csv(`muster-register-${ST.reg.start}.csv`, ['person', 'days', 'day', 'site', 'value', 'hours', 'overtime hours'], (r.muster || []).flatMap(x => x.marks.map(m => [x.name, x.days, m.day, m.site_id, m.value, m.hours, m.ot_hours])));
      if (cv.dataset.csv === 'wages') csv(`wage-register-${ST.reg.start}.csv`, ['run', 'employer', 'person', 'days', 'overtime hours', 'gross', 'deductions', 'advance', 'net', 'status', 'bank reference'], (r.wages || []).map(x => [x.run, x.employer, x.name, x.days, x.ot_hours, x.gross, x.deductions, x.advance, x.net, x.status, x.paid_ref]));
    }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.sheet && el.files && el.files[0]) { addFiles([el.files[0]]); el.value = ''; setTimeout(() => send(`Read this muster sheet for ${dmy(ST.day)} and mark it.`), 900); }
  }
  const val = (f, n) => S((f.querySelector(`[name="${n}"]`) || {}).value).trim();
  async function onSubmit(e) {
    const f = e.target; if (!f.dataset || !f.dataset.form) return;
    e.preventDefault();
    const kind = f.dataset.form, id = f.dataset.id, btn = e.submitter || f.querySelector('button');
    const choice = e.submitter && e.submitter.name ? e.submitter.value : '';
    if (kind === 'search') { ST.q = val(f, 'q'); showPage(true); return; }
    if (kind === 'period') { ST.period = {start: val(f, 'start'), end: val(f, 'end')}; showPage(true); return; }
    if (kind === 'reg') { ST.reg = {start: val(f, 'start'), end: val(f, 'end')}; showPage(true); return; }
    const call = async (part, a, msg) => { if (btn) btn.disabled = true; try { const r = await run(part, a); await changed((r && r.say) || msg || 'Done.'); return r; } catch (err) { toast(err.message, true); if (btn) btn.disabled = false; return null; } };
    if (kind === 'mustermark') {
      const marks = Object.entries(ST.pick).map(([wid, v]) => { const o = {worker_id: wid, status: v}; const ot = val(f, 'ot_' + wid); if (ot) o.ot_hours = ot; return o; });
      if (!marks.length) { toast('Tap P, ½ or A for at least one person.', true); return; }
      const a = {site: ST.site, day: ST.day, who: val(f, 'who'), source: 'phone', device: 'console', marks};
      if (!a.who) { toast('Write the foreman\'s name.', true); return; }
      if (btn) btn.disabled = true;
      try { const r = await run('mark', a); ST.pick = {}; await changed(r.say); }
      catch (err) { if (!err.status || err.status >= 500 || !navigator.onLine) { setQueue([...queue(), a]); ST.pick = {}; toast('No connection: the muster is saved on this device and goes when it is back.'); showPage(true); } else { toast(err.message, true); if (btn) btn.disabled = false; } }
      return;
    }
    if (kind === 'resolve') { await call('resolve', {id, worker: val(f, 'worker'), who: val(f, 'who'), drop: choice === 'drop'}); return; }
    if (kind === 'gate') { await call('gate', {site: ST.site, day: ST.day, count: val(f, 'count'), source: val(f, 'source')}); return; }
    if (kind === 'device') { await call('import_device', {site: ST.site, text: val(f, 'text'), device: val(f, 'device'), who: 'attendance device'}); return; }
    if (kind === 'closeday') { await call('close_day', {site: id, day: ST.day, who: val(f, 'who')}); return; }
    if (kind === 'correct') { await call('correct', {id, status: val(f, 'status'), reason: val(f, 'reason'), who: val(f, 'who')}); return; }
    if (kind === 'worker') {
      const a = {}; for (const k of ['name', 'trade', 'skill', 'gang', 'employer', 'site', 'code', 'language', 'id_last4', 'bank_last4']) if (val(f, k)) a[k] = val(f, k);
      await call('save_worker', a); return;
    }
    if (kind === 'importworkers') { await call('import_workers', {text: val(f, 'text')}); return; }
    if (kind === 'paper') { const a = {}; for (const k of ['whose', 'owner', 'kind', 'name', 'number', 'issuer', 'valid_from', 'valid_to']) if (val(f, k)) a[k] = val(f, k); await call('save_paper', a); return; }
    if (kind === 'advance') { await call('record_advance', {worker: id, amount: val(f, 'amount'), per_run: val(f, 'per_run') || undefined, note: val(f, 'note'), who: val(f, 'who')}); return; }
    if (kind === 'draftrun') { const r = await call('draft_run', {start: val(f, 'start'), end: val(f, 'end'), employer: val(f, 'employer'), site: val(f, 'site'), who: val(f, 'who')}); if (r) location.hash = '#/wages/' + r.id; return; }
    if (kind === 'checkrun') { await call('check_run', {id, who: val(f, 'who')}); return; }
    if (kind === 'approverun') { await call('approve_run', {id, who: val(f, 'who'), who2: val(f, 'who2')}); return; }
    if (kind === 'cancelrun') { await call('cancel_run', {id, who: val(f, 'who'), reason: val(f, 'reason')}); return; }
    if (kind === 'paid') {
      const failed = {}; val(f, 'failed').split('\n').forEach(l => { const [n, ...w] = l.split(':'); if (n && n.trim()) failed[n.trim()] = w.join(':').trim() || 'failed'; });
      await call('mark_paid', {id, ref: val(f, 'ref'), on: val(f, 'on'), who: val(f, 'who'), failed}); return;
    }
    if (kind === 'bulk') {
      const accounts = {}; [...f.querySelectorAll('input[name^=acc_]')].forEach(el => { const w = el.name.slice(4); accounts[w] = {account: el.value, ifsc: val(f, 'ifsc_' + w)}; });
      if (btn) btn.disabled = true;
      try { const r = await run('payment_file', {id, format: 'in_bulk', accounts}); saveBlob(r.name, new Blob([r.file], {type: 'text/csv'})); f.reset(); toast(r.say); }
      catch (err) { toast(err.message, true); } finally { if (btn) btn.disabled = false; }
      return;
    }
    if (kind === 'usepack') { await call('use_pack', {pack_id: id, who: val(f, 'who'), source: val(f, 'source'), rate_pct: val(f, 'rate_pct') || undefined}); return; }
    if (kind === 'rule') {
      const a = {kind: val(f, 'kind'), name: val(f, 'name'), base: val(f, 'base'), source: val(f, 'source'), who: val(f, 'who')};
      if (val(f, 'rate_pct')) a.rate_pct = val(f, 'rate_pct'); if (val(f, 'per_unit')) a.per_unit = val(f, 'per_unit');
      if (val(f, 'rates')) { a.rates = {}; val(f, 'rates').split(';').forEach(p => { const [k, v] = p.split('='); if (k && v) a.rates[k.trim()] = v.trim(); }); }
      await call('save_rule', a); return;
    }
    if (kind === 'levy') { await call('draft_levy', {rule: val(f, 'rule'), ref: val(f, 'ref'), base_amount: val(f, 'base_amount'), day: val(f, 'day'), base_source: val(f, 'base_source')}); return; }
    if (kind === 'levypaid') { await call('mark_levy_paid', {id, receipt: val(f, 'receipt'), who: val(f, 'who')}); return; }
    if (kind === 'payment') { await call('add_payment', {employer: val(f, 'employer'), amount: val(f, 'amount'), materials: val(f, 'materials') || undefined, day: val(f, 'day'), ref: val(f, 'ref')}); return; }
    if (kind === 'deposit') { await call('mark_deposited', {month: val(f, 'month'), receipt: val(f, 'receipt'), who: val(f, 'who')}); return; }
    if (kind === 'filed') { await call('mark_filed', {key: id, ref: val(f, 'ref'), who: val(f, 'who')}); return; }
    if (kind === 'evidence') { await call('add_evidence', {employer: val(f, 'employer'), kind: val(f, 'kind'), people: val(f, 'people') || undefined, ref: val(f, 'ref'), names: val(f, 'names').split('\n').map(x => x.trim()).filter(Boolean), ...ST.period}); return; }
    if (kind === 'decide') { await call('decide_hold', {id, decision: choice, who: val(f, 'who'), note: val(f, 'note')}); return; }
    if (kind === 'employer') { const a = {name: val(f, 'name'), status: val(f, 'status'), tax_id: val(f, 'tax_id')}; if (val(f, 'tax_id_ok')) { a.tax_id_ok = true; a.checked_by = val(f, 'checked_by'); } await call('save_employer', a); return; }
    if (kind === 'site') { await call('save_site', {name: val(f, 'name'), project: val(f, 'project'), region: val(f, 'region'), planned: val(f, 'planned') || undefined}); return; }
    if (kind === 'rate') { const a = {}; for (const k of ['kind', 'trade', 'skill', 'rate', 'basis', 'wef', 'source']) if (val(f, k)) a[k] = val(f, k); await call('save_rate', a); return; }
    if (kind === 'deduction') {
      const d = {name: val(f, 'name'), pct: val(f, 'pct'), base: val(f, 'base'), cap: val(f, 'cap') || 0, employer_pct: val(f, 'employer_pct') || 0, source: val(f, 'source')};
      await call('save_settings', {deductions: [...(SET().deductions || []), d]}, 'Deduction added.'); return;
    }
    if (kind === 'settings') {
      const a = {};
      for (const k of ['company', 'project', 'country', 'region', 'currency', 'pay_cycle', 'week_start', 'day_hours', 'week_hours', 'max_day_hours', 'ot_x', 'cutoff', 'advance_cap', 'second_limit', 'gate_tol']) if (val(f, k) !== '') a[k] = val(f, k);
      await call('save_settings', a, 'Settings saved.'); return;
    }
  }

  /* ---------------------------------------------------------------- files into the chat */
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
    const box = $('#lbFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/lbdesk/chat'); ST.chat = r.id; }
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
      const askR = async () => { const seq = ST.seq; let r = null;
        try { r = await api('GET', `/api/conversations/${enc(chat)}/result`); } catch {}
        if (seq === ST.seq) ST.res = r; };
      if (!first && (ST.sending || ST.working || lastIsHers() || (ST.res && ST.res.needs_you))) await askR();
      let rows;
      try { rows = (await api('GET', `/api/conversations/${enc(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== ST.chat) return;
      merge(rows);
      if (first && lastIsHers()) await askR();
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
    if (ST.working && !working) changed();
    ST.working = working;
    if (ST.bar) ST.bar.working = working && !ST.sending;
  }
  async function send(text) {
    text = S(text).trim();
    const ready = ST.files.filter(f => f.state === 'ok' && f.id);
    if (ST.files.some(f => f.state === 'up')) { setTimeout(() => send(text), 800); return; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'lb' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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
