/* INSURANCE AGENT DESK - the Insurance Agent Assistant's own section, like the other finance desks (owner: "now insurance agent
   assistant --- make it very powerful and advanced like other employee"). A thin top bar, then the Insurance chat (its own conversation,
   kind 'insurance') beside the desk's pages: Today, Customers, Renewals, Cover & quotes, Claims, Commission, Settings. The pages call
   /api/insdesk/do/<part>, which runs the insurance engine on her book. Hoola never takes a premium, signs a proposal, sends a message or
   decides a claim. Routes: #/<page>, #/clients/<id>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M12 16.5s-3.5-2.2-3.5-4.6a1.9 1.9 0 0 1 3.5-1 1.9 1.9 0 0 1 3.5 1c0 2.4-3.5 4.6-3.5 4.6z"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['clients', 'Customers'], ['renewals', 'Renewals'], ['sales', 'Cover & quotes'], ['claims', 'Claims'],
    ['commission', 'Commission'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first today?', 'Whose cover is about to stop?', 'Summarise my book this month'],
    clients: ['What cover is this family missing?', 'Draft a birthday message', 'Who has no nominee?'],
    renewals: ['Who is in the grace period?', 'Draft the reminders for this week', 'Which lapsed policies can be revived?'],
    sales: ['Compare these quotes in plain words', 'What papers does a term plan need?', 'Who should I review this month?'],
    claims: ['What documents are still missing?', 'Which claim is running late?', 'How do I escalate a late claim?'],
    commission: ['Which insurer paid me short?', 'What commission is coming next month?', 'Explain the missing lines'],
    settings: ['What is the grace period in my country?', 'What is a free-look period?', 'Where do I complain about an insurer?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', cq: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.insdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.insdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.set_up) ? {id: 'book', name: ((K().settings || {}).agent_name) || 'Your book', currency: K().currency} : null;
  const CAN = () => !!(ST.d && ST.d.status === 'hired');
  const cur = () => K().currency || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString((c || cur()) === 'INR' ? 'en-IN' : undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 6});
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16).replace(' ', 'T')).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/insdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/insdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Insurance Agent Assistant is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="inHire">Hire the Insurance Agent Assistant</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#inHire').onclick = async () => { try { await api('POST', '/api/employees/insurance_agent/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.fo, '')}</div>
          <div style="min-width:0"><div class="sd-name">Insurance Agent Assistant</div><div class="sd-site" id="inSite"></div></div>
          <span id="inState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Insurance chat">
          <div class="sd-chathead"><div class="t"><b>Insurance chat</b><span>Ask about a customer, a renewal, a quote or a claim - or drop a renewal list or a policy document here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="inFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="inPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.xls,.doc,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Insurance desk" id="sdTabs"></nav>
          <div id="inPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works from your book. The customer pays the insurer directly; you send every message.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a customer, a renewal or a claim…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#inPick').click()});
    $('#inPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.insdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.insdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/insdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#inPage').addEventListener('click', onPageClick);
    $('#inPage').addEventListener('submit', onSubmit);
    $('#inPage').addEventListener('change', onChange);
    $('#inPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    $('#inPage').addEventListener('input', e => { if (e.target.id === 'inCq') { ST.cq = e.target.value; const at = e.target.selectionStart; showPage(true); const q = $('#inCq'); if (q) { q.focus(); try { q.setSelectionRange(at, at); } catch {} } } });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#inState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#inSite').textContent = w ? [(k.settings || {}).agent_name, (k.pack || {}).name, cur()].filter(Boolean).join(' · ') : 'Not set up yet';
  }
  function paintTabs() {
    const k = K(), ok = !!W(), r = k.renewals || {}, cl = (k.claims || []).filter(c => c.overdue || ((c.missing || []).length && c.status === 'open')).length;
    const n = ok ? {renewals: ((r.grace || []).length + (r.lapsed || []).length) || '', claims: cl || '', sales: (k.advice || []).filter(a => a.status === 'ready').length || '',
      commission: ((k.commission || {}).short || 0) || '', clients: (k.birthdays || []).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/insdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#inPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, clients: pClients, renewals: pRenewals, sales: pSales, claims: pClaims, commission: pCommission, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    box.innerHTML = html;
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
  }
  /* a part of the page that arrives later redraws it: what she was typing stays where it was */
  const fkey = f => `${f.dataset.form}|${f.dataset.which || f.dataset.kind || ''}`;
  function typed(box) {
    const out = {map: {}, focus: null}, act = document.activeElement;
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = fkey(f), vals = {};
      [...f.querySelectorAll('input:not([type=file]), textarea, select'), ...box.querySelectorAll(`[form="${f.id || '-'}"]`)].forEach((el, j) => {
        if (!el.name) return;
        const id = el.name + '#' + j;
        if (el.value !== el.defaultValue && el.tagName !== 'SELECT') vals[id] = {v: el.value};
        else if (el.tagName === 'SELECT' && el.dataset.touched) vals[id] = {v: el.value};
        if (el === act) out.focus = [k, id, el.selectionStart];
      });
      if (Object.keys(vals).length) out.map[k] = vals;
    });
    return out;
  }
  function retype(box, kept) {
    box.querySelectorAll('form[data-form]').forEach(f => {
      const k = fkey(f), vals = kept.map[k]; if (!vals && !(kept.focus && kept.focus[0] === k)) return;
      [...f.querySelectorAll('input:not([type=file]), textarea, select'), ...box.querySelectorAll(`[form="${f.id || '-'}"]`)].forEach((el, j) => {
        if (!el.name) return;
        const id = el.name + '#' + j, v = vals && vals[id];
        if (v) { el.value = v.v; if (el.tagName === 'SELECT') el.dataset.touched = '1'; }
        if (kept.focus && kept.focus[0] === k && kept.focus[1] === id) { el.focus(); try { if (kept.focus[2] !== null) el.setSelectionRange(kept.focus[2], kept.focus[2]); } catch {} }
      });
    });
  }
  const loading = () => '<section class="card"><p class="mut" style="margin:0">Working it out…</p></section>';
  function greet() { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'; }
  const kpi = (l, v, s, cls) => `<div class="md-kpi"><div class="l">${esc(l)}</div><div class="v ${cls || ''}">${v}</div>${s ? `<div class="mut" style="font-size:13px;margin-top:4px">${esc(s)}</div>` : ''}</div>`;
  const needsRows = list => (list || []).map(x => `<div class="cs-row"><span class="cs-dot${x.bad ? ' bad' : ''}"></span><span style="flex:1">${esc(x.say)}</span><button class="btn soft sm" type="button" data-go="${esc(x.go)}">Open</button></div>`).join('');
  const empty = t => `<p class="mut" style="margin:0;font-size:14px">${esc(t)}</p>`;
  const err = r => r && r.error ? `<p class="cs-neg" style="margin:8px 0 0">${esc(r.error)}</p>` : '';
  const ro = () => CAN() ? '' : '<p class="cs-note">The desk is paused: resume it in AI Employees to make changes.</p>';
  const sign = v => Number(v) > 0 ? 'cs-pos' : Number(v) < 0 ? 'cs-neg' : '';
  const sgn = v => (Number(v) > 0 ? '+' : '') + num(v);
  const ask = (about) => `<button class="ib mk-ask" type="button" aria-label="Ask about this" title="Ask in the chat" data-ask="${esc(about)}">${svg(IC.chat)}</button>`;
  const rmBtn = (reg, n) => CAN() ? `<button class="ib" type="button" aria-label="Remove" data-rm="${esc(reg)}" data-n="${esc(n)}">×</button>` : '';
  const tag = (t, c) => `<span class="cs-tag ${c || ''}">${esc(t)}</span>`;
  function uploader(kind, title, hint, extra) {
    if (!CAN()) return '';
    return `<form class="ins-drop" data-form="upload" data-kind="${esc(kind)}"><div class="t"><b>${esc(title)}</b><span class="mut">${esc(hint)}</span></div>
      ${extra || ''}<label class="btn soft sm">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" data-upfile="1" hidden></label></form>`;
  }
  const short = v => { const n = Math.abs(Number(v) || 0), s = Number(v) < 0 ? '-' : '';
    return s + (n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(0) + 'k' : n.toLocaleString(undefined, {maximumFractionDigits: 0})); };
  const listRows = (reg, rows, cols, max) => {
    if (!(rows || []).length) return empty('Nothing here yet.');
    return `<div class="iv-tw"><table class="tb mk-list"><thead><tr>${cols.map(c => `<th${c[2] ? ' class="r"' : ''}>${esc(c[1])}</th>`).join('')}<th></th></tr></thead><tbody>${
      rows.slice(0, max || 200).map(r => `<tr>${cols.map(c => `<td${c[2] ? ' class="r"' : ''}>${c[3] ? c[3](r[c[0]], r) : esc(r[c[0]] ?? '')}</td>`).join('')}<td class="r">${rmBtn(reg, r.n)}</td></tr>`).join('')}</tbody></table></div>
      ${rows.length > (max || 200) ? `<p class="mut" style="font-size:13px">Showing ${num(max || 200)} of ${num(rows.length)}.</p>` : ''}
      ${CAN() ? `<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-rmall="${esc(reg)}">Clear all</button></div>` : ''}`;
  };
  const addForm = (reg, fields, label) => CAN() ? `<form class="mk-add" data-form="add" data-which="${esc(reg)}">${fields.map(([n, l, t, ph]) =>
      Array.isArray(t) ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${t.map(([v, x]) => `<option value="${esc(v)}">${esc(x)}</option>`).join('')}</select></label>`
      : t === 'io' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="in">Money in</option><option value="out">Money out</option></select></label>`
      : t === 'freq' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="monthly">Monthly</option><option value="weekly">Weekly</option><option value="fortnightly">Fortnightly</option></select></label>`
      : `<label class="ins-lab">${esc(l)}<input class="in" name="${n}"${t === 'date' ? ' type="date"' : ''}${t === 'num' ? ' inputmode="decimal"' : ''} placeholder="${esc(ph || '')}"></label>`).join('')}
      <button class="btn soft" type="submit">${esc(label || 'Add')}</button></form>` : '';

  /* ---------------------------------------------------------------- charts (drawn in SVG, no library) */
  function ring(parts, mid, sub, label) {
    const rows = parts.filter(p => p[1] > 0), total = rows.reduce((s, p) => s + p[1], 0);
    if (!total) return '';
    const Rr = 54, C = 2 * Math.PI * Rr; let at = 0;
    const arcs = rows.map(([name, v, cls]) => { const len = v / total * C, gap = rows.length > 1 ? 2 : 0, l2 = Math.max(0, len - gap);
      const s = `<circle class="iv-seg ${esc(cls)}" r="${Rr}" cx="70" cy="70" stroke-dasharray="${l2.toFixed(2)} ${(C - l2).toFixed(2)}" stroke-dashoffset="${(-at).toFixed(2)}"><title>${esc(name)} ${num(v)}</title></circle>`;
      at += len; return s; }).join('');
    return `<div class="iv-donut"><svg viewBox="0 0 140 140" role="img" aria-label="${esc(label)}"><g transform="rotate(-90 70 70)"><circle class="iv-track" r="${Rr}" cx="70" cy="70"/>${arcs}</g>
      <text x="70" y="66" class="iv-dl">${esc(sub)}</text><text x="70" y="84" class="iv-dv">${esc(mid)}</text></svg>
      <div class="iv-dleg">${rows.map(([name, v, cls]) => `<div><i class="${esc(cls)}"></i><span>${esc(name)}</span><b>${esc(num(v))}</b></div>`).join('')}</div></div>`;
  }
  function bars(rows, fmt, label) {   /* rows: [name, value, cls, sub] - horizontal bars from 0 */
    if (!rows.length) return '';
    const mx = Math.max(1e-9, ...rows.map(r => Math.abs(r[1])));
    return `<div class="iv-w mk-bars" role="img" aria-label="${esc(label)}">${rows.map(([n, v, cls, sub]) => `<div><span><b>${esc(n)}</b>${sub ? `<em>${esc(sub)}</em>` : ''}</span><i><b class="${esc(cls || 'mk-b')}" style="width:${(Math.abs(v) / mx * 100).toFixed(1)}%"></b></i><em>${esc(fmt ? fmt(v) : num(v))}</em></div>`).join('')}</div>`;
  }
  function line(pts, label, fmt, cls, wide) {   /* pts: [label, value] - a filled line, the last value marked */
    if (pts.length < 2) return '';
    const W = wide ? 760 : 480, H = wide ? 200 : 210, L = wide ? 64 : 52, R = 14, T = 14, B = 30, vs = pts.map(p => Number(p[1]) || 0);
    let lo = Math.min(0, ...vs), hi = Math.max(...vs); if (hi === lo) hi = lo + 1;
    const x = i => L + i * (W - L - R) / (pts.length - 1), y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const d = vs.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    const area = `${d}L${x(vs.length - 1).toFixed(1)},${y(lo).toFixed(1)}L${x(0).toFixed(1)},${y(lo).toFixed(1)}Z`;
    const ticks = [hi, (hi + lo) / 2, lo].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`).join('');
    const every = Math.max(1, Math.ceil(pts.length / 6));
    const xl = pts.map((p, i) => (i % every === 0 || i === pts.length - 1) ? `<text class="tx" x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(p[0])}</text>` : '').join('');
    const zero = lo < 0 ? `<line class="zero" x1="${L}" x2="${W - R}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"/>` : '';
    const lx = x(vs.length - 1), ly = y(vs[vs.length - 1]);
    return `<div class="cs-chart cm-line ${esc(cls || '')}"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${ticks}${zero}<path class="ar" d="${area}"/><path class="ln" d="${d}"/>
      ${vs.map((v, i) => `<circle class="pt" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3"><title>${esc(pts[i][0])}: ${esc(fmt ? fmt(v) : num(v))}</title></circle>`).join('')}
      <circle class="end" cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="5"/>${xl}</svg></div>`;
  }
  function gauge(share, limit) {   /* her repayments as a share of income, against her limit */
    if (share === null || share === undefined) return '';
    const p = Math.min(100, Math.max(0, Number(share))), lim = limit === null || limit === undefined ? null : Math.min(100, Number(limit));
    const over = lim !== null && p > lim;
    return `<div class="cm-gauge"><div class="h"><b class="${over ? 'cs-neg' : ''}">${esc(num(Math.round(p * 10) / 10))}%</b><span class="mut">of your income goes to repayments${lim !== null ? ` · your limit ${esc(lim)}%` : ''}</span></div>
      <div class="bar"><i class="${over ? 'bad' : p > (lim ?? 100) * 0.8 ? 'warn' : 'ok'}" style="width:${p.toFixed(1)}%"></i>${lim !== null ? `<u style="left:${lim}%" title="your limit"></u>` : ''}</div>
      <div class="ft"><span>0%</span><span>50%</span><span>100%</span></div></div>`;
  }
  const m0 = v => money(v, null, 0);
  const dd = d => { try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short'}); } catch { return d; } };
  const tick = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>';

  /* ---------------------------------------------------------------- setup */
  function pSetup() {
    const pk = (ST.d && ST.d.packs) || {};
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.fo, '')}</div>
      <div><h1 class="sd-h">Set up your insurance desk</h1><p class="lead">Your customers and their families, every policy, renewals with grace and revival dates, cover gaps, quotes compared with the advice record, claims with their documents and clock, and your commission checked against the insurer's statement - for any country. You send every message; the customer pays the insurer directly.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">About you</h2><div class="md-form">
        <div class="md-field"><label for="inS1">Your name (as customers know you)</label><input class="in" id="inS1" name="name" maxlength="120" placeholder="Asha Rao"></div>
        <div class="md-field"><label for="inS2">Agent / licence code</label><input class="in" id="inS2" name="code" maxlength="40" placeholder="optional"></div>
        <div class="md-field"><label for="inS3">Country (two letters)</label><input class="in" id="inS3" name="country" required maxlength="2" placeholder="GB" list="inPk"><datalist id="inPk">${Object.entries(pk).map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join('')}</datalist></div>
        <div class="md-field"><label for="inS4">Currency (three letters)</label><input class="in" id="inS4" name="currency" maxlength="3" placeholder="GBP"></div></div>
        <p class="cs-note">India's servicing rules (grace, free-look, claim times) are built in and checked. For any other country the desk shows a suggested value marked "check this" and uses none of them until you confirm it in Settings.</p>
        <div class="md-acts"><span class="mut" style="font-size:13px">Then drop the insurer's renewal list on Renewals.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const ok_ = o => o && !o.empty && !o.error;
  const pct = v => (v === null || v === undefined) ? '—' : `${num(Math.round(Number(v) * 100) / 100)}%`;
  const TYPE = t => ((K().types || {})[t]) || cap(t);
  const STATE = {due: ['Due', 'warn'], grace: ['Grace period', 'bad'], overdue: ['Past due', 'bad'], lapsed: ['Lapsed', 'bad'], lapsed_final: ['Revival over', ''],
    paid_up: ['Paid up', 'v'], no_due: ['No due date', 'warn'], inforce: ['In force', 'ok'], matured: ['Matured', 'v'], surrendered: ['Surrendered', ''], claimed: ['Claimed', 'v'], cancelled: ['Cancelled', '']};
  const stTag = st => { const [l, c] = STATE[st.state] || [cap(st.state), '']; return `<span class="cs-tag ${c}" title="${esc(st.label || '')}">${esc(l)}</span>`; };
  const SRC = {yours: ['Yours', 'ok'], checked: ['Checked', 'v'], 'check this': ['Check this', 'warn'], 'not set': ['Not set', '']};
  const CL = {open: ['Collecting documents', 'warn'], filed: ['With the insurer', 'v'], query: ['Insurer asked a question', 'bad'], settled: ['Settled', 'ok'], rejected: ['Rejected', 'bad']};
  const KINDS = {death: 'Death', health_cashless: 'Health - cashless', health_reimbursement: 'Health - reimbursement', motor: 'Motor', other: 'Other'};
  const MODES = [['yearly', 'Yearly'], ['half_yearly', 'Half-yearly'], ['quarterly', 'Quarterly'], ['monthly', 'Monthly'], ['single', 'Single premium']];
  const pname = id => { const c = (K().clients || []).find(x => x.id === id); return c ? c.name : ''; };
  const msgBtn = (d, label) => d ? (d.wa ? `<a class="btn soft sm" href="${esc(d.wa)}" target="_blank" rel="noopener" title="Opens WhatsApp with the message; you press send">${esc(label || 'Message')}</a>`
      : `<button class="btn soft sm" type="button" data-copy="${esc(d.text)}" title="No phone number: copy the message">Copy message</button>`) : '';
  function clock(c) {   /* a filed claim's days against her country's settlement time */
    if (!c.limit_days || c.days_since_filed === null || c.days_since_filed === undefined) return c.filed_on ? '<p class="mut" style="font-size:13px;margin:6px 0 0">No settlement time set for your country - set it in Settings to watch the clock.</p>' : '';
    const p = Math.min(100, c.days_since_filed / c.limit_days * 100), over = c.days_since_filed > c.limit_days;
    return `<div class="cm-gauge" style="margin-top:8px"><div class="h"><b class="${over ? 'cs-neg' : ''}">${esc(num(c.days_since_filed))} days</b><span class="mut">since every document was with the insurer · should settle within ${esc(num(c.limit_days))}</span></div>
      <div class="bar"><i class="${over ? 'bad' : p > 75 ? 'warn' : 'ok'}" style="width:${p.toFixed(1)}%"></i></div></div>`;
  }
  function gapBar(label, g) {   /* cover held against the cover needed */
    if (!g) return '';
    const need = Number(g.need) || 0, have = Number(g.existing) || 0, w = need ? Math.min(100, have / need * 100) : 100;
    return `<div class="fo-rat"><span>${esc(label)}<em class="mut" style="display:block;font-size:12.5px">needs about ${esc(m0(need))}</em></span><i><b class="${g.gap > 0 ? 'bad' : 'ok'}" style="width:${w.toFixed(1)}%"></b></i>
      <em class="${g.gap > 0 ? 'cs-neg' : 'cs-pos'}">${esc(m0(have))}${g.gap > 0 ? ` <span class="mut">gap ${esc(m0(g.gap))}</span>` : ''}</em></div>`;
  }

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), b = k.book || {}, r = k.renewals || {}, c = k.counts || {};
    const has = c.policies || c.clients;
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on your book ${k.needs.length > 1 ? 'need' : 'needs'} you.` : has ? 'Your book is in order today.' : 'Drop the insurer\'s renewal list on Renewals, or add your first customer.';
    const grace = (r.grace || []).length, lap = (r.lapsed || []).length;
    const tiles = [
      `<div class="k"><div class="l">In force</div><div class="v">${esc(num(b.inforce || 0))}</div><div class="s">${esc(m0(b.yearly_premium || 0))} premium a year</div></div>`,
      `<div class="k${(r.due || []).length ? ' low' : ''}"><div class="l">Due soon</div><div class="v">${esc(num((r.due || []).length))}</div><div class="s">${esc(m0((r.due || []).reduce((s, p) => s + p.premium, 0)))} in the next ${esc(num((k.settings || {}).remind_days || 15))} days</div></div>`,
      `<div class="k${grace + lap ? ' low bad' : ''}"><div class="l">Cover at risk</div><div class="v">${esc(num(grace + lap))}</div><div class="s">${esc(m0(k.at_risk_yearly || 0))} premium a year</div></div>`,
      `<div class="k${(k.needs || []).some(x => x.go === 'claims' && x.bad) ? ' low bad' : ''}"><div class="l">Open claims</div><div class="v">${esc(num(c.claims_open || 0))}</div><div class="s">${esc(b.persistency_pct === null || b.persistency_pct === undefined ? 'persistency —' : 'persistency ' + pct(b.persistency_pct))}</div></div>`];
    const cal = k.calendar || [];
    const types = Object.entries(b.by_type || {});
    return `<div><h1 class="sd-h">${greet()}${(k.settings || {}).agent_name ? ', ' + esc(S(k.settings.agent_name).split(' ')[0]) : ''}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your book</h2><div class="r"><button class="btn soft sm" type="button" data-dl="book">CSV</button></div></div>
          ${types.length ? ring(types.map(([t, n], i) => [t, n, 'rk-c' + (i % 6)]), num(b.inforce || 0), 'in force', 'Policies by type') : empty('No policies yet.')}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Premiums ahead</h2><div class="r"><span class="mut" style="font-size:13px">next 12 months · commission ${esc(m0(cal.reduce((s, x) => s + x.commission, 0)))}</span></div></div>
        ${cal.some(x => x.premium) ? cols(cal.map(x => [mon(x.month), x.premium, pl(x.count, 'premium')]), m0, 'Premiums falling due by month') : empty('Premiums show here once policies have a next due date.')}</section>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">In grace or lapsed</h2><div class="r"><button class="btn soft sm" type="button" data-go="renewals">Open</button></div></div>
          ${[...(r.grace || []), ...(r.lapsed || [])].slice(0, 6).map(p => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">${esc(p.client)} <span class="mut">${esc([p.insurer, p.number].filter(Boolean).join(' · '))}</span></span>${stTag(p.premium_state)}</div>`).join('') || empty('No policy is in grace or lapsed.')}</section>
        <section class="card"><h2 class="md-h2">Birthdays this week</h2>${(k.birthdays || []).map(x => `<div class="cs-row"><span style="flex:1">${esc(x.client)} <span class="mut">${esc(dd(x.on))}</span></span>${msgBtn(x, 'Send wishes')}</div>`).join('') || empty('No birthdays in the next 7 days.')}</section></div>`;
  }
  function cols(rows, fmt, label) {   /* rows: [label, value, sub] - one column per month */
    if (!rows.some(r => r[1])) return '';
    const W = 760, H = 210, L = 56, R = 10, T = 16, B = 30, mx = Math.max(...rows.map(r => r[1])) || 1, bw = (W - L - R) / rows.length;
    const y = v => T + (1 - v / mx) * (H - T - B);
    const ticks = [mx, mx / 2, 0].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(short(v))}</text>`).join('');
    const bars_ = rows.map((r, i) => { const x = L + i * bw + bw * 0.18, w = bw * 0.64, top = y(r[1]);
      return `<rect class="in-col${r[1] ? '' : ' z'}" x="${x.toFixed(1)}" y="${top.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(0, H - B - top).toFixed(1)}" rx="4"><title>${esc(r[0])}: ${esc(fmt ? fmt(r[1]) : num(r[1]))}${r[2] ? ' · ' + esc(r[2]) : ''}</title></rect>
        <text class="tx" x="${(x + w / 2).toFixed(1)}" y="${H - 9}" text-anchor="middle">${esc(r[0])}</text>`; }).join('');
    return `<div class="cs-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}">${ticks}${bars_}</svg></div>`;
  }
  const mon = m => { try { return new Date(m + '-01T00:00').toLocaleDateString(undefined, {month: 'short'}); } catch { return m; } };

  /* ---------------------------------------------------------------- customers */
  function pClients() {
    if (ST.arg) return clientPage(ST.arg);
    const k = K(), q = S(ST.cq).toLowerCase(), xs = new Map((k.cross_sell || []).map(x => [x.client_id, x]));
    const pols = k.policies || [];
    const rows = (k.clients || []).filter(c => !q || c.name.toLowerCase().includes(q) || S(c.phone).includes(q) || S(c.city).toLowerCase().includes(q));
    return `<div><h1 class="sd-h">Customers</h1><p class="lead">Each customer with their family, income and goals, their policies and what cover they are missing. Messages go only to customers who agreed to them, and you press send.</p></div>
      ${CAN() ? `<section class="card"><h2 class="md-h2">New customer</h2><form class="iv-add" data-form="client">
        <input class="in" name="name" required maxlength="120" placeholder="Full name" aria-label="Full name"><input class="in" name="phone" maxlength="20" placeholder="Phone (with country code)" aria-label="Phone">
        <input class="in" name="dob" type="date" aria-label="Date of birth"><input class="in" name="city" maxlength="60" placeholder="City" aria-label="City">
        <input class="in" name="income" inputmode="decimal" placeholder="Yearly income (${esc(cur())})" aria-label="Yearly income">
        <label class="ins-lab" style="flex:0 0 auto;flex-direction:row;align-items:center;gap:6px"><input type="checkbox" name="whatsapp_ok" checked> Agreed to messages</label>
        <button class="btn" type="submit">Add</button></form></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your customers <span class="mut">${esc(num(rows.length))}</span></h2><div class="r">${(k.clients || []).length > 6 ? `<input class="in sm" type="search" id="inCq" placeholder="Find a customer" value="${esc(ST.cq || '')}" style="max-width:240px">` : ''}</div></div>
        ${rows.length ? `<div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Customer</th><th>City</th><th class="r">Policies</th><th class="r">Premium a year</th><th>Cover gaps</th><th></th></tr></thead><tbody>${rows.map(c => {
          const ps = pols.filter(p => p.client_id === c.id && p.status === 'inforce'), yr = ps.reduce((s, p) => s + yearly(p), 0), x = xs.get(c.id);
          return `<tr><td><a href="#/clients/${esc(c.id)}"><b>${esc(c.name)}</b></a><div class="mut" style="font-size:12.5px">${esc(c.age ? c.age + ' years' : '')}${c.phone ? ' · ' + esc(c.phone) : ''}</div></td><td>${esc(c.city || '—')}</td><td class="r">${esc(num(ps.length))}</td><td class="r">${esc(m0(yr))}</td>
            <td>${x ? x.gaps.map(g => tag(g, 'warn')).join(' ') : tag('Covered', 'ok')}</td><td class="r">${ask('Customer: ' + c.name)}</td></tr>`; }).join('')}</tbody></table></div>` : empty(q ? 'No customer matches.' : 'No customers yet - add one, or drop the insurer\'s list on Renewals.')}</section>`;
  }
  const yearly = p => { const k = {monthly: 1, quarterly: 3, half_yearly: 6, yearly: 12}[p.mode]; return k ? p.premium * 12 / k : 0; };
  function clientPage(id) {
    const k = K(), c = (k.clients || []).find(x => x.id === id);
    if (!c) return `<section class="card">${empty('That customer is not on the desk.')}<button class="btn soft sm" type="button" data-go="clients" style="margin-top:10px">Back</button></section>`;
    const ps = (k.policies || []).filter(p => p.client_id === id), adv = (k.advice || []).filter(a => a.client_id === id), cls = (k.claims || []).filter(x => ps.some(p => p.number === x.policy));
    const nd = ST.out['needs:' + id];
    if (nd === undefined) { ST.out['needs:' + id] = null; run('needs', {client: id}).then(r => { ST.out['needs:' + id] = r; showPage(true); }).catch(e => { ST.out['needs:' + id] = {error: e.message}; showPage(true); }); }
    const fam = c.family || [];
    return `<div class="cs-head"><div><button class="btn soft sm" type="button" data-go="clients">← Customers</button>
        <h1 class="sd-h" style="margin-top:10px">${esc(c.name)}</h1><p class="lead" style="margin:2px 0 0">${esc([c.age ? c.age + ' years' : '', c.city, c.phone].filter(Boolean).join(' · ') || 'Add their details below')}${c.whatsapp_ok ? '' : ' · does not want messages'}</p></div>
        <div class="r">${ask('Customer: ' + c.name)}</div></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Cover they need</h2>${nd === null || nd === undefined ? loading() : nd.error ? `<p class="cs-neg">${esc(nd.error)}</p>` : `
          <div class="fo-rats">${gapBar('Life cover', nd.life)}${gapBar('Health cover', nd.health)}</div>
          ${(nd.gaps || []).length ? `<div style="margin-top:10px">${nd.gaps.map(g => `<div class="cs-row"><span class="cs-dot bad"></span><span>${esc(g)}</span></div>`).join('')}</div>` : '<p class="cs-pos" style="margin:10px 0 0">Their cover looks complete.</p>'}
          <p class="cs-note">A rule of thumb from their income, loans, goals and family - the customer decides what to buy.</p>`}</section>
        <form class="card" data-form="client" data-id="${esc(id)}"><h2 class="md-h2">Their details</h2><div class="md-form">
          <div class="md-field"><label for="inC1">Phone</label><input class="in" id="inC1" name="phone" value="${esc(c.phone)}"></div>
          <div class="md-field"><label for="inC2">Date of birth</label><input class="in" id="inC2" name="dob" type="date" value="${esc(c.dob)}"></div>
          <div class="md-field"><label for="inC3">City</label><input class="in" id="inC3" name="city" value="${esc(c.city)}"></div>
          <div class="md-field"><label for="inC4">Yearly income (${esc(cur())})</label><input class="in" id="inC4" name="income" inputmode="decimal" value="${esc(c.income || '')}"></div>
          <div class="md-field"><label for="inC5">Loans outstanding</label><input class="in" id="inC5" name="liabilities" inputmode="decimal" value="${esc(c.liabilities || '')}"></div>
          <div class="md-field"><label for="inC6">Goals to fund (education, home…)</label><input class="in" id="inC6" name="goals" inputmode="decimal" value="${esc(c.goals || '')}"></div>
          <div class="md-field"><label for="inC7">Savings and investments</label><input class="in" id="inC7" name="savings" inputmode="decimal" value="${esc(c.savings || '')}"></div>
          <div class="md-field"><label for="inC8">Messages</label><select class="in" id="inC8" name="whatsapp_ok"><option value="1"${c.whatsapp_ok ? ' selected' : ''}>Agreed to messages</option><option value="0"${c.whatsapp_ok ? '' : ' selected'}>No messages</option></select></div>
          <div class="md-field wide"><label for="inC9">Notes</label><input class="in" id="inC9" name="notes" maxlength="2000" value="${esc(c.notes || '')}"></div></div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn soft" type="submit">Save</button></div>' : ''}</form></div>
      <section class="card"><h2 class="md-h2">Family</h2>${fam.length ? fam.map(m => `<div class="cs-row"><span style="flex:1">${esc(m.name)} <span class="mut">${esc(m.relation)}${m.dob ? ' · born ' + esc(dmy(m.dob)) : ''}</span></span></div>`).join('') : empty('No family members yet - they shape the health cover.')}
        ${CAN() ? `<form class="iv-add" data-form="family" data-id="${esc(id)}"><input class="in" name="name" required maxlength="60" placeholder="Name" aria-label="Name"><select class="in" name="relation" aria-label="Relation"><option>spouse</option><option>son</option><option>daughter</option><option>father</option><option>mother</option><option>other</option></select><input class="in" name="dob" type="date" aria-label="Date of birth"><button class="btn soft" type="submit">Add to the family</button></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">Policies</h2>${ps.length ? policyTable(ps) : empty('No policies yet.')}
        ${CAN() ? `<details class="ins-more"${ps.length ? '' : ' open'}><summary>Add a policy</summary>${policyForm(id)}</details>` : ''}</section>
      ${adv.length ? `<section class="card"><h2 class="md-h2">Quotes compared</h2>${adv.map(adviceCard).join('')}</section>` : ''}
      ${cls.length ? `<section class="card"><h2 class="md-h2">Claims</h2>${cls.map(x => `<div class="cs-row"><span style="flex:1">${esc(KINDS[x.kind] || x.kind)} <span class="mut">${esc(x.insurer)} · ${esc(x.policy)}</span></span>${tag((CL[x.status] || [x.status])[0], (CL[x.status] || ['', ''])[1])}</div>`).join('')}<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="claims">Open claims</button></div></section>` : ''}`;
  }
  function policyTable(ps) {
    const drafts = new Map(((K().renewals || {}).drafts || []).map(d => [d.policy_id, d]));
    return `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Policy</th><th>Type</th><th class="r">Premium</th><th class="r">Cover</th><th>Next due</th><th>State</th><th></th></tr></thead><tbody>${ps.map(p => `<tr>
      <td><b>${esc(p.insurer)}</b> ${esc(p.plan)}<div class="mut" style="font-size:12.5px">${esc(p.number)}${p.nominee ? ' · nominee ' + esc(p.nominee) : ' · <span class="cs-neg">no nominee</span>'}</div></td>
      <td>${esc(p.type_label)}</td><td class="r">${esc(m0(p.premium))}<div class="mut" style="font-size:12px">${esc((MODES.find(x => x[0] === p.mode) || [0, p.mode])[1])}</div></td><td class="r">${esc(m0(p.cover))}</td>
      <td>${esc(dmy(p.next_due))}</td><td>${stTag(p.premium_state)}</td>
      <td class="r nw">${CAN() && ['due', 'grace', 'overdue', 'lapsed'].includes(p.premium_state.state) ? `${msgBtn(drafts.get(p.id), 'Remind')} <button class="btn soft sm" type="button" data-paid="${esc(p.id)}" title="The customer paid the insurer">Paid</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
  }
  function policyForm(cid) {
    const types = Object.entries(K().types || {});
    return `<form class="cr-grid" data-form="policy" data-id="${esc(cid)}" style="margin-top:10px">
      <input class="in" name="insurer" required maxlength="80" placeholder="Insurer" aria-label="Insurer"><input class="in" name="plan" maxlength="120" placeholder="Plan name" aria-label="Plan">
      <select class="in" name="type" aria-label="Type">${types.map(([t, l]) => `<option value="${esc(t)}">${esc(l)}</option>`).join('')}</select>
      <input class="in" name="number" required maxlength="40" placeholder="Policy number" aria-label="Policy number">
      <label class="ins-lab">Start<input class="in" name="start" type="date"></label><select class="in" name="mode" aria-label="Premium paid">${MODES.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select>
      <input class="in" name="premium" inputmode="decimal" placeholder="Premium (${esc(cur())})" aria-label="Premium"><input class="in" name="cover" inputmode="decimal" placeholder="Cover / sum assured" aria-label="Cover">
      <label class="ins-lab">Next due<input class="in" name="next_due" type="date"></label><input class="in" name="nominee" maxlength="120" placeholder="Nominee" aria-label="Nominee">
      <input class="in" name="commission_pct" inputmode="decimal" placeholder="Your commission %" aria-label="Commission percent">
      <input class="in" name="pay_link" maxlength="300" placeholder="Insurer's https payment page (optional)" aria-label="Payment page">
      <button class="btn" type="submit">Add the policy</button></form>`;
  }

  /* ---------------------------------------------------------------- renewals */
  function pRenewals() {
    const k = K(), r = k.renewals || {}, drafts = new Map((r.drafts || []).map(d => [d.policy_id, d])), st = k.settings || {};
    const row = p => `<tr><td><a href="#/clients/${esc(p.client_id)}"><b>${esc(p.client)}</b></a><div class="mut" style="font-size:12.5px">${esc([p.insurer, p.number].filter(Boolean).join(' · '))}</div></td>
      <td class="r">${esc(m0(p.premium))}</td><td>${esc(dmy(p.premium_state.due))}</td><td>${stTag(p.premium_state)}<div class="mut" style="font-size:12.5px">${esc(p.premium_state.label || '')}</div></td>
      <td class="r nw">${CAN() ? `${msgBtn(drafts.get(p.id), 'Remind')} <button class="btn soft sm" type="button" data-reminded="${esc(p.id)}" title="You reminded them">Reminded</button> <button class="btn sm" type="button" data-paid="${esc(p.id)}" title="The customer paid the insurer">Paid</button>` : ''}</td></tr>`;
    const tbl = (rows, none) => rows.length ? `<div class="iv-tw"><table class="tb mk-list in-cards"><thead><tr><th>Customer</th><th class="r">Premium</th><th>Due</th><th>State</th><th></th></tr></thead><tbody>${rows.map(row).join('')}</tbody></table></div>` : empty(none);
    return `<div><h1 class="sd-h">Renewals</h1><p class="lead">What is due in the next ${esc(num(st.remind_days || 15))} days, what is in the grace period, and what has lapsed but can still be revived. Reminders open in WhatsApp for you to send; "Paid" records that the customer paid the insurer.</p></div>
      ${uploader('import', 'Drop the insurer\'s renewal or policy list', 'A CSV from the agent portal: name and policy number at least; phone, premium, mode, due date, cover and nominee if it has them.', '<input class="in sm" name="insurer" maxlength="80" placeholder="Insurer (if not in the file)" style="max-width:220px">')}
      <section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Due soon', esc(num((r.due || []).length)), m0((r.due || []).reduce((s, p) => s + p.premium, 0)))}${kpi('Grace / past due', esc(num((r.grace || []).length)), '', (r.grace || []).length ? 'bad' : '')}${kpi('Lapsed', esc(num((r.lapsed || []).length)), 'still revivable', (r.lapsed || []).length ? 'bad' : '')}${kpi('Commission on these', esc(m0(r.commission || 0)))}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">In the grace period or past due</h2><div class="r"><button class="btn soft sm" type="button" data-dl="renewals">CSV</button></div></div>${tbl(r.grace || [], 'No premium is in the grace period.')}</section>
      <section class="card"><h2 class="md-h2">Due soon</h2>${tbl(r.due || [], 'Nothing is due in the next ' + num(st.remind_days || 15) + ' days.')}</section>
      <section class="card"><h2 class="md-h2">Lapsed - can be revived</h2>${tbl(r.lapsed || [], 'No lapsed policy.')}</section>`;
  }

  /* ---------------------------------------------------------------- cover and quotes */
  function adviceCard(a) {
    const out = ST.out['adv:' + a.id];
    return `<div class="pb-res" style="margin-top:10px"><div class="cs-head"><b>${esc(a.client)}</b><div class="r">${tag(a.status === 'ready' ? 'Waiting for your yes' : a.status === 'approved' ? 'You said yes' : a.status, a.status === 'ready' ? 'warn' : 'ok')} <span class="mut" style="font-size:12.5px">${esc(dt(a.at))}</span></div></div>
      <div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Insurer · plan</th><th class="r">Premium</th><th class="r">Cover</th><th class="r">Premium per ${esc(cur() === 'INR' ? 'lakh' : '100,000')}</th><th class="r">Claims paid</th></tr></thead><tbody>${(a.options || []).map((o, i) => `<tr${i === 0 ? ' class="best"' : ''}><td><b>${esc(o.insurer)}</b> ${esc(o.plan)}<div class="mut" style="font-size:12.5px">${esc(TYPE(o.type))}${o.guaranteed ? ' · guaranteed' : ''}${o.features ? ' · ' + esc(o.features) : ''}</div></td><td class="r">${esc(m0(o.premium))}</td><td class="r">${esc(m0(o.cover))}</td><td class="r">${esc(m2(o.per_lakh))}</td><td class="r">${o.csr ? esc(o.csr) + '%' : '—'}</td></tr>`).join('')}</tbody></table></div>
      ${out ? `<div class="pb-res" style="margin-top:10px"><b>Message for ${esc(a.client)}</b><p style="white-space:pre-wrap;margin:6px 0 0">${esc(out.draft)}</p><div class="md-acts"><span class="mut" style="font-size:13px">You send it.</span>${msgBtn({wa: out.wa, text: out.draft}, 'Open in WhatsApp')}</div></div>`
        : CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">It reaches the customer only after your yes - and you send it.</span><button class="btn soft sm" type="button" data-approve="${esc(a.id)}">Yes, prepare the message</button></div>` : ''}</div>`;
  }
  function pSales() {
    const k = K(), xs = k.cross_sell || [], cl = k.clients || [], types = Object.entries(k.types || {}), ck = ST.out.checklist;
    const opt = i => `<div class="in-qrow"><input class="in" name="insurer${i}" placeholder="Insurer ${i}" aria-label="Insurer ${i}"><input class="in" name="plan${i}" placeholder="Plan" aria-label="Plan ${i}">
      <select class="in" name="type${i}" aria-label="Type ${i}">${types.map(([t, l]) => `<option value="${esc(t)}">${esc(l)}</option>`).join('')}</select>
      <input class="in" name="premium${i}" inputmode="decimal" placeholder="Premium a year" aria-label="Premium ${i}"><input class="in" name="cover${i}" inputmode="decimal" placeholder="Cover" aria-label="Cover ${i}">
      <input class="in" name="csr${i}" inputmode="decimal" placeholder="Claims paid %" aria-label="Claims paid ${i}"><input class="in" name="features${i}" maxlength="300" placeholder="What stands out" aria-label="Features ${i}"></div>`;
    return `<div><h1 class="sd-h">Cover &amp; quotes</h1><p class="lead">Who is missing which cover, the quotes you got from insurers set side by side and kept as the advice record, and the papers a proposal needs. The customer chooses, and fills in their own proposal and health details.</p></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Cover gaps in your book <span class="mut">${esc(num(xs.length))}</span></h2><div class="r">${xs.length ? '<button class="btn soft sm" type="button" data-dl="cross_sell">CSV</button>' : ''}</div></div>
        ${xs.length ? xs.slice(0, 40).map(x => `<div class="cs-row"><span style="flex:1"><a href="#/clients/${esc(x.client_id)}"><b>${esc(x.client)}</b></a> <span class="mut">${esc(pl(x.policies, 'policy', 'policies'))}</span></span>${x.gaps.map(g => tag(g, 'warn')).join(' ')}</div>`).join('') : empty('Every customer has health, life and accident cover with a nominee.')}</section>
      ${CAN() && cl.length ? `<form class="card" data-form="quote"><h2 class="md-h2">Compare quotes</h2><div class="md-form"><div class="md-field"><label for="inQc">For</label><select class="in" id="inQc" name="client">${cl.map(c => `<option value="${esc(c.id)}">${esc(c.name)}</option>`).join('')}</select></div>
        <div class="md-field wide"><label for="inQn">Your note (why these)</label><input class="in" id="inQn" name="note" maxlength="2000"></div></div>${opt(1)}${opt(2)}${opt(3)}
        <div class="md-acts"><span class="mut" style="font-size:13px">Sorted by premium per unit of cover, then claims paid. Kept as the advice record.</span><button class="btn" type="submit">Compare</button></div></form>` : ''}
      ${(k.advice || []).length ? `<section class="card"><h2 class="md-h2">Quotes compared</h2>${k.advice.slice(0, 12).map(adviceCard).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">What a proposal needs</h2><form class="iv-add" data-form="checklist"><select class="in" name="type" aria-label="Type">${types.map(([t, l]) => `<option value="${esc(t)}">${esc(l)}</option>`).join('')}</select><input class="in" name="age" inputmode="numeric" placeholder="Age" aria-label="Age"><button class="btn soft" type="submit">Show the papers</button></form>
        ${ck ? `<div style="margin-top:12px">${(ck.documents || []).map(d => `<div class="cs-row"><span class="cr-chk"></span><span>${esc(d)}</span></div>`).join('')}${(ck.tips || []).map(t => `<p class="cs-note">${esc(t)}</p>`).join('')}</div>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- claims */
  function pClaims() {
    const k = K(), all = k.claims || [], open = all.filter(c => ['open', 'filed', 'query'].includes(c.status)), done = all.filter(c => !['open', 'filed', 'query'].includes(c.status));
    const pols = (k.policies || []).filter(p => p.status === 'inforce' || p.status === 'lapsed'), pk = k.pack || {};
    const card = c => `<div class="pb-res${c.overdue ? ' warn' : ''}" style="margin-top:12px"><div class="cs-head"><div><b>${esc(c.client)}</b> <span class="mut">${esc(KINDS[c.kind] || c.kind)} · ${esc(c.insurer)} · ${esc(c.policy)}</span>
        <div class="mut" style="font-size:12.5px">${c.event_on ? 'happened ' + esc(dmy(c.event_on)) : ''}${c.amount ? ' · claimed ' + esc(m0(c.amount)) : ''}${c.insurer_ref ? ' · insurer ref ' + esc(c.insurer_ref) : ''}</div></div>
        <div class="r">${tag((CL[c.status] || [c.status])[0], (CL[c.status] || ['', ''])[1])}</div></div>
      <div style="margin-top:8px">${Object.entries(c.docs || {}).map(([d, ok]) => `<div class="cs-row"><span class="cr-st ${ok ? 'received' : ''}">${ok ? '✓' : '!'}</span><span style="flex:1">${esc(d)}</span>${!ok && CAN() ? `<button class="btn soft sm" type="button" data-tick="${esc(c.id)}" data-doc="${esc(d)}">Have it</button>` : ''}</div>`).join('')}</div>
      ${clock(c)}
      ${c.overdue ? `<p class="cs-neg" style="margin:10px 0 0">Past the settlement time. Complaint ladder: ${esc(c.escalate)}</p>` : ''}
      ${CAN() ? `<form class="iv-add" data-form="claimup" data-id="${esc(c.id)}"><label class="ins-lab">Everything with the insurer on<input class="in" name="filed_on" type="date" value="${esc(c.filed_on || '')}"></label>
        <input class="in" name="insurer_ref" maxlength="60" placeholder="Claim ref" value="${esc(c.insurer_ref || '')}" aria-label="Insurer reference">
        <select class="in" name="status" aria-label="Status">${Object.entries(CL).map(([v, [l]]) => `<option value="${v}"${v === c.status ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
        <input class="in" name="settled_amount" inputmode="decimal" placeholder="Amount settled" aria-label="Amount settled" value="${esc(c.settled_amount || '')}"><input class="in" name="note" maxlength="300" placeholder="Note" aria-label="Note">
        <button class="btn soft" type="submit">Update</button></form>` : ''}</div>`;
    return `<div><h1 class="sd-h">Claims</h1><p class="lead">Each claim with the documents it needs, the clock against ${esc(pk.name || 'your country')}'s settlement time once everything is with the insurer, and the complaint ladder if it runs late. Hoola never decides or predicts a claim - the insurer does.</p></div>
      ${CAN() && pols.length ? `<section class="card"><h2 class="md-h2">Start a claim</h2><form class="iv-add" data-form="claim"><select class="in" name="policy" aria-label="Policy">${pols.map(p => `<option value="${esc(p.id)}">${esc(p.client)} · ${esc(p.insurer)} ${esc(p.number)}</option>`).join('')}</select>
        <select class="in" name="kind" aria-label="Kind">${Object.entries(KINDS).map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join('')}</select>
        <label class="ins-lab">It happened on<input class="in" name="event_on" type="date"></label><input class="in" name="amount" inputmode="decimal" placeholder="Amount claimed" aria-label="Amount claimed"><button class="btn" type="submit">Start</button></form>
        <p class="cs-note">Tell the insurer at once - many policies set a time limit for telling them.</p></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Open claims <span class="mut">${esc(num(open.length))}</span></h2><div class="r">${all.length ? '<button class="btn soft sm" type="button" data-dl="claims">CSV</button>' : ''}</div></div>${open.length ? open.map(card).join('') : empty('No open claims.')}</section>
      ${done.length ? `<section class="card"><h2 class="md-h2">Closed</h2><div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Customer</th><th>Claim</th><th>Outcome</th><th class="r">Claimed</th><th class="r">Settled</th></tr></thead><tbody>${done.map(c => `<tr><td>${esc(c.client)}</td><td>${esc(KINDS[c.kind] || c.kind)} <span class="mut">${esc(c.policy)}</span></td><td>${tag((CL[c.status] || [c.status])[0], (CL[c.status] || ['', ''])[1])}</td><td class="r">${esc(m0(c.amount))}</td><td class="r">${esc(m0(c.settled_amount))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">If a claim goes wrong</h2>${(pk.ladder || []).map((s, i) => `<div class="cs-row"><span class="fm-step">${i + 1}</span><span>${esc(s)}</span></div>`).join('')}<p class="cs-note">${esc(pk.ombudsman && !(pk.ladder || []).some(x => x.includes(pk.ombudsman)) ? 'Ombudsman: ' + pk.ombudsman + '. ' : '')}${pk.checked ? '' : 'From memory for ' + esc(pk.name || 'your country') + ' - check this.'}</p></section>`;
  }

  /* ---------------------------------------------------------------- commission */
  function pCommission() {
    const k = K(), c = k.commission || {}, cal = k.calendar || [];
    const ST2 = {ok: ['Matches', 'ok'], short: ['Short', 'bad'], over: ['More than expected', 'warn'], missing: ['Not on the statement', 'warn'], no_rate: ['No rate on the policy', '']};
    return `<div><h1 class="sd-h">Commission</h1><p class="lead">The commission you should get on every premium you recorded as paid, checked against what the insurer's statement says it paid - and what is coming in the next 12 months.</p></div>
      ${uploader('commission', 'Drop the insurer\'s commission statement', 'A CSV with the policy number, the month (YYYY-MM or a date) and the amount; the insurer\'s name if it has one.')}
      <section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Expected', esc(m0(c.expected_total || 0)))}${kpi('On the statements', esc(m0(c.received_total || 0)))}${kpi('Short', esc(num(c.short || 0)), '', c.short ? 'bad' : 'cs-pos')}${kpi('Not on a statement', esc(num(c.missing || 0)), '', c.missing ? 'warn' : '')}</section>
      ${(c.by_insurer || []).length ? `<section class="card"><h2 class="md-h2">By insurer</h2><div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Insurer</th><th class="r">Expected</th><th class="r">Received</th><th class="r">Short</th><th class="r">Missing</th></tr></thead><tbody>${c.by_insurer.map(b => `<tr><td><b>${esc(b.insurer)}</b></td><td class="r">${esc(m2(b.expected))}</td><td class="r">${esc(m2(b.received))}</td><td class="r ${b.short ? 'cs-neg' : ''}">${esc(num(b.short))}</td><td class="r">${esc(num(b.missing))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Premium by premium</h2><div class="r">${(c.rows || []).length ? '<button class="btn soft sm" type="button" data-dl="commission">CSV</button>' : ''}${CAN() && c.statement_lines ? ' <button class="btn soft sm" type="button" data-clearstmt="1">Clear the statements</button>' : ''}</div></div>
        ${(c.rows || []).length ? `<div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Policy</th><th>Month paid</th><th class="r">Expected</th><th class="r">Received</th><th>Check</th></tr></thead><tbody>${c.rows.slice().reverse().slice(0, 200).map(r => `<tr><td><b>${esc(r.number)}</b> <span class="mut">${esc(r.insurer)}</span></td><td>${esc(mon(r.period))} ${esc(S(r.period).slice(0, 4))}</td><td class="r">${esc(m2(r.expected))}</td><td class="r">${r.received === null ? '—' : esc(m2(r.received))}</td><td>${tag((ST2[r.state] || [r.state])[0], (ST2[r.state] || ['', ''])[1])}</td></tr>`).join('')}</tbody></table></div>` : empty('Commission shows here once you record premiums as paid ("Paid" on Renewals) and the policies carry your commission %.')}
        ${(c.extra || []).length ? `<p class="cs-note">${esc(pl(c.extra.length, 'statement line'))} for premiums not recorded as paid on the desk: ${c.extra.slice(0, 8).map(x => esc(x.number + ' ' + x.period)).join(', ')}.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Coming in the next 12 months</h2>${cal.some(x => x.commission) ? bars(cal.filter(x => x.commission).map(x => [mon(x.month) + ' ' + x.month.slice(2, 4), x.commission, 'mk-b', pl(x.count, 'premium')]), m0, 'Commission by month') : empty('Add your commission % to each policy to see what is coming.')}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, rl = k.rules || {}, pk = k.pack || {}, mine = s.rules || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">You, your country and the servicing rules the desk works to. India's rules are built in and checked; for any other country a value marked "check this" is a starting point from memory and is never used until you confirm it.</p></div>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="profile"><h2 class="md-h2">You</h2><div class="md-form">
          <div class="md-field"><label for="inP1">Your name</label><input class="in" id="inP1" name="agent_name" maxlength="120" value="${esc(s.agent_name || '')}"></div>
          <div class="md-field"><label for="inP2">Agent / licence code</label><input class="in" id="inP2" name="agent_code" maxlength="40" value="${esc(s.agent_code || '')}"></div>
          <div class="md-field"><label for="inP3">Remind this many days before a premium is due</label><input class="in" id="inP3" name="remind_days" inputmode="numeric" value="${esc(s.remind_days || 15)}"></div>
          <div class="md-field"><label for="inP4">Morning summary at</label><input class="in" id="inP4" name="morning_time" type="time" value="${esc(s.morning_time || '09:15')}"></div></div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <form class="card" data-form="country"><h2 class="md-h2">Country</h2><div class="md-form">
          <div class="md-field"><label for="inK1">Country (two letters)</label><input class="in" id="inK1" name="country" maxlength="2" value="${esc(s.country || '')}" list="inPk2"><datalist id="inPk2">${Object.entries(ST.d.packs || {}).map(([c, n]) => `<option value="${esc(c)}">${esc(n)}</option>`).join('')}</datalist></div>
          <div class="md-field"><label for="inK2">Currency</label><input class="in" id="inK2" name="currency" maxlength="3" value="${esc(s.currency || '')}"></div></div>
          <div class="cs-row"><span style="flex:1">Regulator</span><b>${esc(pk.regulator || '—')}</b></div><div class="cs-row"><span style="flex:1">Ombudsman</span><b>${esc(pk.ombudsman || '—')}</b></div>
          <p class="cs-note">${esc(pk.tax || '')}${pk.checked ? ' Source: ' + esc(pk.source || '') : ' From memory - check this.'}</p>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn soft" type="submit">Save</button></div>' : ''}</form></div>
      <form class="card" data-form="rules"><h2 class="md-h2">Servicing rules for ${esc(pk.name || 'your country')}</h2>
        <div class="iv-tw"><table class="tb mk-list"><thead><tr><th>Rule</th><th>Where it comes from</th><th class="r">Suggested</th><th>Yours</th><th></th></tr></thead><tbody>${Object.entries(rl).map(([key, v]) => `<tr><td>${esc(v.label)}</td><td>${tag((SRC[v.source] || [v.source])[0], (SRC[v.source] || ['', ''])[1])}</td>
          <td class="r">${v.suggested === null || v.suggested === undefined ? '—' : esc(num(v.suggested))}</td><td><input class="in" name="${esc(key)}" inputmode="decimal" value="${esc(mine[key] ?? '')}" placeholder="${v.source === 'checked' ? esc(v.value) : 'yours'}" style="max-width:120px" aria-label="${esc(v.label)}"></td>
          <td class="r">${CAN() && v.source === 'check this' ? `<button class="btn soft sm" type="button" data-use="${esc(key)}" data-v="${esc(v.suggested)}">Use this value</button>` : ''}</td></tr>`).join('')}</tbody></table></div>
        <div class="cr-sub" style="margin-top:14px">Your rules of thumb for health cover</div><div class="md-form">
          <div class="md-field"><label for="inR1">Health cover for a couple (${esc(cur())})</label><input class="in" id="inR1" name="health_base" inputmode="decimal" value="${esc(mine.health_base ?? '')}" placeholder="${s.country === 'IN' ? 'built in: 5-10 lakh' : 'yours'}"></div>
          <div class="md-field"><label for="inR2">Add for each extra family member</label><input class="in" id="inR2" name="health_member" inputmode="decimal" value="${esc(mine.health_member ?? '')}"></div></div>
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Empty = not used. Your value always wins.</span><button class="btn" type="submit">Save the rules</button></div>' : ''}</form>
      <section class="card"><h2 class="md-h2">What Hoola never does</h2>${['Take or pay a premium - the customer pays the insurer directly', 'Sign a proposal or fill in a health declaration for a customer', 'Send a message - it drafts, you send, only to customers who agreed', 'Promise a return the brochure does not guarantee', 'Decide or predict a claim'].map(x => `<div class="cs-row"><span class="cs-dot"></span><span>${esc(x)}</span></div>`).join('')}</section>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/insdesk/download?what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.csv`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const val = (fd, n) => S(fd.get(n)).trim();
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { setCtx(ak.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast('Copied - paste it into your message.'); } catch { toast('Could not copy.', true); } return; }
    try {
      const pd = t.closest('[data-paid]'); if (pd) { const r = await run('paid', {policy: pd.dataset.paid, paid_on: today()}); delete ST.out['needs:' + ST.arg]; await changed(r.say || 'Recorded as paid.'); return; }
      const rm = t.closest('[data-reminded]'); if (rm) { await run('reminded', {policy: rm.dataset.reminded}); await changed('Noted that you reminded them.'); return; }
      const ap = t.closest('[data-approve]'); if (ap) { const r = await run('advice_message', {advice_id: ap.dataset.approve}); ST.out['adv:' + ap.dataset.approve] = r; await changed('The message is ready - you send it.'); return; }
      const tk = t.closest('[data-tick]'); if (tk) { const r = await run('claim_update', {claim_id: tk.dataset.tick, have: [tk.dataset.doc]}); await changed(r.say); return; }
      const us = t.closest('[data-use]'); if (us) { await run('settings', {rules: {[us.dataset.use]: us.dataset.v}}); await changed('The value is yours now - the desk uses it.'); return; }
      const cs = t.closest('[data-clearstmt]'); if (cs) { if (!confirm('Remove every commission statement line from the desk?')) return; await run('commission_clear', {}); await changed('Cleared.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 20e6) { toast('Up to 20 MB.', true); return; }
    try {
      const txt = await f.text(), kind = form.dataset.kind;
      if (kind === 'import') { const ins = form.querySelector('[name=insurer]'); const r = await run('import', {text: txt, name: f.name, insurer: ins ? ins.value.trim() : ''});
        fi.value = ''; await changed(r.say + (r.errors && r.errors.length ? ' ' + r.errors.slice(0, 2).join(' ') : '')); }
      else { const r = await run('commission', {text: txt, name: f.name}); fi.value = ''; await changed(`${num(r.saved)} commission lines read from ${f.name}.`); }
    } catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    if (form.dataset.form === 'upload') return;
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const pick = names => { const a = {}; names.forEach(n => { if (g(n) !== '') a[n] = g(n); }); return a; };
    const done = async m => { form.reset(); await changed(m); };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/insdesk/setup', {name: g('name'), code: g('code'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await changed('Your desk is set up.'); await openChat(); }
      else if (kind === 'client') {
        const a = pick(['name', 'phone', 'dob', 'city', 'income', 'liabilities', 'goals', 'savings', 'notes']);
        if (form.dataset.id) { a.client = form.dataset.id; if (fd.has('whatsapp_ok')) a.whatsapp_ok = g('whatsapp_ok') === '1'; delete ST.out['needs:' + form.dataset.id];
          await run('client', a); await changed('Saved.'); }
        else { a.whatsapp_ok = fd.get('whatsapp_ok') === 'on'; const r = await run('client', a); form.reset(); await changed(r.say); location.hash = '#/clients/' + r.client.id; } }
      else if (kind === 'family') { const c = (K().clients || []).find(x => x.id === form.dataset.id) || {};
        await run('client', {client: form.dataset.id, family: [...(c.family || []), {name: g('name'), relation: g('relation'), dob: g('dob')}]}); delete ST.out['needs:' + form.dataset.id]; await done('Added to the family.'); }
      else if (kind === 'policy') { const r = await run('policy', {client: form.dataset.id, ...pick(['insurer', 'plan', 'type', 'number', 'start', 'mode', 'premium', 'cover', 'next_due', 'nominee', 'commission_pct', 'pay_link'])});
        delete ST.out['needs:' + form.dataset.id]; await done(r.say); }
      else if (kind === 'quote') { const options = [1, 2, 3].map(i => ({insurer: g('insurer' + i), plan: g('plan' + i), type: g('type' + i), premium: g('premium' + i), cover: g('cover' + i), csr: g('csr' + i) || null, features: g('features' + i)}))
          .filter(o => o.insurer && o.premium && o.cover);
        if (!options.length) throw new Error('Fill in at least one quote: insurer, premium and cover.');
        const r = await run('recommend', {client: g('client'), note: g('note'), options}); await done(r.say); }
      else if (kind === 'checklist') { ST.out.checklist = await run('checklist', {type: g('type'), age: g('age') ? Number(g('age')) : null}); showPage(true); }
      else if (kind === 'claim') { const r = await run('claim', pick(['policy', 'kind', 'event_on', 'amount'])); await done(r.say); }
      else if (kind === 'claimup') { const r = await run('claim_update', {claim_id: form.dataset.id, ...pick(['filed_on', 'insurer_ref', 'status', 'settled_amount', 'note'])}); await changed(r.say); }
      else if (kind === 'profile') { await run('settings', pick(['agent_name', 'agent_code', 'remind_days', 'morning_time'])); await changed('Saved.'); }
      else if (kind === 'country') { await run('settings', {country: g('country').toUpperCase(), currency: g('currency').toUpperCase()}); await changed('Saved - the rules below are now for this country.'); }
      else if (kind === 'rules') { const rules = {}; for (const [n, v] of fd.entries()) rules[n] = S(v).trim(); await run('settings', {rules}); await changed('Your rules are saved.'); }
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
    const box = $('#inFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/insdesk/chat'); ST.chat = r.id; }
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


