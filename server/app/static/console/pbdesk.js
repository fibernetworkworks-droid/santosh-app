/* PUBLIC FINANCE DESK - the Public Sector employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE
   PUBLIC FINANCE DESK"). A thin top bar, then the Public Finance chat (its own conversation, kind 'public') beside the desk's pages:
   Today, Casework, Overpayments, Payment runs, Deposit cover, Supervision, Inspections, Development projects, Settings. The pages call
   /api/public/do/<part>, which runs the F12 engine on her desk. Hoola never pays, awards, refuses or stops anything. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', pb: '<path d="M3 9.5L12 4l9 5.5"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8"/><path d="M3 20h18"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['cases', 'Casework'], ['overpay', 'Overpayments'], ['g2p', 'Payment runs'], ['deposit', 'Deposit cover'],
    ['supervision', 'Supervision'], ['inspections', 'Inspections'], ['devfin', 'Projects'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Summarise the payment run', 'Which banks are in breach?'],
    cases: ['Why does this case not meet the rules?', 'Draft the letter to the household', 'Which evidence is still missing?'],
    overpay: ['Explain this overpayment', 'Draft the overpayment notice', 'Which cases were underpaid?'],
    g2p: ['Explain the exceptions', 'Draft a note to the bank on the failures', 'Why does an account matter if it is shared?'],
    deposit: ['Explain the payout list', 'What happens above the cover limit?', 'Which records must be fixed?'],
    supervision: ['Explain this bank\'s breach', 'Draft the supervisory letter', 'Which banks moved most?'],
    inspections: ['Which findings are overdue?', 'Draft a reminder to the owners', 'Why is this a repeat finding?'],
    devfin: ['Why was this tranche released early?', 'Draft the progress report', 'Which lines are over budget?'],
    settings: ['What capital ratio is usual?', 'Explain liquidity coverage', 'What is an outlier here?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.public.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.public.folded') === '1'; } catch {}

  const W = () => (ST.d && ST.d.workspace) || null;
  const K = () => (ST.d && ST.d.desk) || {};
  const CAN = () => !!(ST.d && ST.d.can_write);
  const cur = () => (W() && W().currency) || 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 6});
  const RN = r => ((ST.d && ST.d.roles) || {})[r] || r;
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16).replace(' ', 'T')).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/public/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/public/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.pb, '')}</div>
        <h1 class="sd-h">Your Public Finance employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="pbHire">Hire Public Finance</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#pbHire').onclick = async () => { try { await api('POST', '/api/employees/public_finance/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.pb, '')}</div>
          <div style="min-width:0"><div class="sd-name">Public Finance</div><div class="sd-site" id="pbSite"></div></div>
          <span id="pbState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="pbBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Public Finance chat">
          <div class="sd-chathead"><div class="t"><b>Public Finance chat</b><span>Ask about a case, a payment run or a bank - or drop a file here; a reference is enough, never a full account number</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="pbFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="pbPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Public Finance desk" id="sdTabs"></nav>
          <div id="pbPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola checks against your rules. It never pays, awards, refuses or stops anything.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about a case, a payment run or a bank…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#pbPick').click()});
    $('#pbPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.public.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.public.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/public/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#pbBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/public/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#pbPage').addEventListener('click', onPageClick);
    $('#pbPage').addEventListener('submit', onSubmit);
    $('#pbPage').addEventListener('change', onChange);
    $('#pbPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#pbState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#pbSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#pbBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), gp = k.g2p || {}, sv = k.supervision || {}, ins = k.inspections || {}, dp = k.deposit || {}, op = k.overpay || {};
    const L = (o, f) => (o && !o.empty && !o.error) ? f(o) : 0;
    const n = ok ? {cases: (k.cases || []).filter(c => !c.decision).length || '', g2p: L(gp, o => o.clean ? 0 : 1) || '', supervision: L(sv, o => o.in_breach.length) || '',
      inspections: L(ins, o => o.overdue.length) || '', deposit: L(dp, o => o.records_to_fix.length) || '', overpay: L(op, o => o.cases.filter(c => c.overpaid).length) || '',
      devfin: ((k.projects || {}).projects || []).filter(p => (p.released_before_conditions || []).length || (p.over_budget || []).length).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/public/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#pbPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, cases: pCases, overpay: pOverpay, g2p: pG2p, deposit: pDeposit, supervision: pSupervision, inspections: pInspections,
      devfin: pDevfin, settings: pSettings}[ST.tab] || pToday;
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
  const ro = () => CAN() ? '' : `<p class="cs-note">You read this desk as ${esc(RN(ST.d.role))}. Changing it needs the owner, an officer or an approving official.</p>`;
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
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.pb, '')}</div>
      <div><h1 class="sd-h">Set up your public finance desk</h1><p class="lead">Households checked against your scheme rules, each rule with its source, for a caseworker to decide; over- and underpayments; a payment run reconciled against the approved list and the bank's return; a failed bank's depositors covered up to your limit; banks' returns against your thresholds; inspection findings and development projects. Hoola never pays, awards, refuses or stops anything.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('pbS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then add your scheme rules, or drop a payment file on Payment runs.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="Benefits office"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;
  const ok_ = o => o && !o.empty && !o.error;
  const STATE = {'meets the rules': ['Meets the rules', 'ok'], 'does not meet': ['Does not meet', 'bad'], 'cannot tell yet': ['Cannot tell yet', 'warn']};

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), op = k.overpay || {}, gp = k.g2p || {}, dp = k.deposit || {}, sv = k.supervision || {}, ins = k.inspections || {};
    const has = k.counts && Object.values(k.counts).some(Boolean);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : has ? 'Everything on the desk is in order.' : 'Add your scheme rules, or drop a payment file, to start.';
    const cases = k.cases || [], waiting = cases.filter(c => !c.decision).length;
    const exc = ok_(gp) ? gp.paid_twice.length + gp.not_on_the_list.length + gp.wrong_amount.length + gp.failed.length + gp.never_sent.length + gp.shared_accounts.length : null;
    const tiles = [];
    tiles.push(`<div class="k${waiting ? ' low' : ''}"><div class="l">Cases waiting</div><div class="v">${esc(num(waiting))}</div><div class="s">${esc(pl(cases.length, 'case'))} checked</div></div>`);
    tiles.push(`<div class="k${exc ? ' low bad' : ''}"><div class="l">Payment run</div><div class="v">${exc === null ? '—' : exc ? esc(pl(exc, 'exception')) : 'Clean'}</div><div class="s">${ok_(gp) ? `${esc(num(gp.paid))} of ${esc(num(gp.approved))} paid right` : 'no payment run yet'}</div></div>`);
    tiles.push(ok_(sv) ? `<div class="k${sv.in_breach.length ? ' low bad' : ''}"><div class="l">Banks in breach</div><div class="v">${esc(num(sv.in_breach.length))}</div><div class="s">of ${esc(pl(sv.banks.length, 'bank'))}${sv.period ? ' · ' + esc(sv.period) : ''}</div></div>`
      : `<div class="k${ok_(op) && op.overpaid ? ' low' : ''}"><div class="l">Overpaid</div><div class="v">${ok_(op) ? esc(m0(op.overpaid)) : '—'}</div><div class="s">${ok_(op) ? 'underpaid ' + esc(m0(op.underpaid)) : 'no payments yet'}</div></div>`);
    tiles.push(ok_(ins) ? `<div class="k${ins.overdue.length ? ' low bad' : ''}"><div class="l">Findings open</div><div class="v">${esc(num(ins.open))}</div><div class="s">${esc(num(ins.overdue.length))} overdue</div></div>`
      : `<div class="k"><div class="l">Deposit cover</div><div class="v">${ok_(dp) ? esc(m0(dp.covered_total)) : '—'}</div><div class="s">${ok_(dp) ? esc(pl(dp.n_depositors, 'depositor')) : 'no failed bank on the desk'}</div></div>`);
    const st = {meet: 0, miss: 0, tell: 0};
    cases.forEach(c => (c.result || []).forEach(s => { st[s.state === 'meets the rules' ? 'meet' : s.state === 'does not meet' ? 'miss' : 'tell']++; }));
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Cases against the rules</h2><div class="r"><button class="btn soft sm" type="button" data-go="cases">Casework</button></div></div>
          ${st.meet + st.miss + st.tell ? ring([['Meets the rules', st.meet, 'mk-ok'], ['Does not meet', st.miss, 'mk-mc'], ['Cannot tell yet', st.tell, 'mk-q']], num(cases.length), 'cases', 'Cases against the rules') : empty('Check a case against your scheme rules to see this.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The payment run</h2><div class="r"><button class="btn soft sm" type="button" data-go="g2p">Open</button></div></div>
          ${ok_(gp) ? g2pBars(gp) : empty(gp.error || 'Drop the approved list, the payment file and the bank return on Payment runs.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Banks against your thresholds</h2><div class="r"><button class="btn soft sm" type="button" data-go="supervision">Open</button></div></div>
          ${ok_(sv) ? carBars(sv) : empty(sv.error || (sv.need_thresholds ? 'Set your thresholds in Settings.' : 'Drop the banks\' returns on Supervision.'))}</section></div>`;
  }
  function g2pBars(g) {
    const rows = [['Paid right', g.paid, 'dg-up'], ['Paid twice', g.paid_twice.length, 'dg-dn'], ['Wrong amount', g.wrong_amount.length, 'dg-dn'], ['Failed', g.failed.length, 'mk-age1'],
      ['Never sent', g.never_sent.length, 'mk-age0'], ['Not on the list', g.not_on_the_list.length, 'dg-dn'], ['Shared account', g.shared_accounts.length, 'mk-age2']].filter(r => r[1]);
    return bars(rows, v => num(v), 'The payment run');
  }
  function carBars(sv) {
    const th = sv.thresholds || {}, rows = sv.banks.filter(b => b.car !== undefined).slice(0, 14);
    if (!rows.length) return bars(sv.banks.map(b => [b.bank, b.breaches.length, b.breaches.length ? 'dg-dn' : 'dg-up', b.breaches.join('; ')]), v => pl(v, 'breach', 'breaches'), 'Breaches by bank');
    const W = 480, rowH = 28, L = 120, H = rows.length * rowH + 30, mx = Math.max(th.car_min || 0, ...rows.map(b => b.car)) * 1.15 || 1, x = v => L + v / mx * (W - L - 40);
    return `<div class="cs-chart pb-car"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Capital ratio by bank">${rows.map((b, i) => { const y = 6 + i * rowH, bad = th.car_min !== undefined && b.car < th.car_min;
        return `<text class="tx lb" x="0" y="${y + 14}">${esc(S(b.bank).slice(0, 16))}</text><rect class="${bad ? 'bad' : 'ok'}" x="${L}" y="${y}" width="${Math.max(2, x(b.car) - L).toFixed(1)}" height="18" rx="4"><title>${esc(b.bank)} ${esc(b.car)}%</title></rect><text class="tx" x="${(x(b.car) + 6).toFixed(1)}" y="${y + 14}">${esc(b.car)}%</text>`; }).join('')}
      ${th.car_min !== undefined ? `<line class="min" x1="${x(th.car_min).toFixed(1)}" x2="${x(th.car_min).toFixed(1)}" y1="0" y2="${H - 20}"/><text class="minl" x="${(x(th.car_min) + 4).toFixed(1)}" y="${H - 6}">your minimum ${esc(th.car_min)}%</text>` : ''}</svg></div>
      <p class="mut" style="font-size:13px;margin:4px 0 0">Capital ratio (capital ÷ risk-weighted assets).</p>`;
  }

  /* ---------------------------------------------------------------- casework */
  function pCases() {
    const k = K(), sch = k.schemes || [], cs = k.cases || [], o = ST.out.case, ed = ST.out.editScheme ? sch.find(s => s.n === ST.out.editScheme) || {} : {};
    return `<div><h1 class="sd-h">Casework</h1><p class="lead">A household checked against your scheme rules - each rule with its legal or policy source. Hoola says which schemes it meets, by how much it misses the others, what cannot be told yet and which evidence is still missing; the caseworker decides and records the decision here.</p></div>
      ${ro()}
      <section class="card"><h2 class="md-h2">Scheme rules</h2>
        ${sch.length ? sch.map(s => `<div class="pb-scheme"><div class="h"><b>${esc(s.name)}</b><span class="mut">${esc(s.source)}</span><span style="flex:1"></span>${CAN() ? `<button class="btn soft sm" type="button" data-edits="${esc(s.n)}">Change</button>` : ''}${rmBtn('schemes', s.n)}</div>
          <div class="pb-tests">${s.tests.map(t => `<code>${esc(t.field.replace(/_/g, ' '))} ${esc(t.op)} ${esc(t.value)}</code>`).join('')}</div>
          <div class="mut" style="font-size:13px">${s.amount ? `Amount: ${s.amount.base !== undefined ? esc(m2(s.amount.base)) : '0'}${s.amount.per_field ? ` + ${esc(m2(s.amount.per_value || 0))} for each ${esc(s.amount.per_field.replace(/_/g, ' '))}` : ''}${s.amount.max !== undefined ? `, at most ${esc(m2(s.amount.max))}` : ''}` : 'No amount rule'}${s.evidence.length ? ' · evidence: ' + esc(s.evidence.join(', ')) : ''}</div></div>`).join('') : empty('No scheme rules yet.')}
        ${CAN() ? `<details class="ins-more"${ST.out.editScheme ? ' open' : ''}><summary>${ed.name ? 'Change ' + esc(ed.name) : 'Add a scheme'}</summary><form data-form="scheme">
          <div class="mk-two"><label class="ins-lab">Scheme<input class="in" name="name" required maxlength="80" value="${esc(ed.name || '')}" placeholder="Family help"></label>
            <label class="ins-lab">Its source (law, regulation or policy)<input class="in" name="source" required maxlength="200" value="${esc(ed.source || '')}" placeholder="Social Security Act 2021, s.4"></label></div>
          <div class="mk-two" style="margin-top:12px"><label class="ins-lab">Rules, one a line (field op value)<textarea class="in mk-mono" name="tests" rows="4" placeholder="income <= 12000&#10;children >= 1&#10;resident == yes">${esc((ed.tests || []).map(t => `${t.field} ${t.op} ${t.value}`).join('\n'))}</textarea></label>
            <label class="ins-lab">Evidence needed (one a line)<textarea class="in" name="evidence" rows="4" placeholder="proof of income&#10;birth certificate">${esc((ed.evidence || []).join('\n'))}</textarea></label></div>
          <div class="cm-grid5" style="margin-top:12px"><label class="ins-lab">Amount: base<input class="in" name="base" inputmode="decimal" value="${esc((ed.amount || {}).base ?? '')}"></label>
            <label class="ins-lab">Plus for each (field)<input class="in" name="per_field" value="${esc((ed.amount || {}).per_field || '')}" placeholder="children"></label>
            <label class="ins-lab">… this much<input class="in" name="per_value" inputmode="decimal" value="${esc((ed.amount || {}).per_value ?? '')}"></label>
            <label class="ins-lab">At most<input class="in" name="max" inputmode="decimal" value="${esc((ed.amount || {}).max ?? '')}"></label>
            <button class="btn" type="submit">Save the rules</button></div></form></details>` : ''}</section>
      ${CAN() && sch.length ? `<form class="card" data-form="case"><h2 class="md-h2">Check a case</h2>
        <div class="mk-three"><label class="ins-lab">Case reference (no name is needed)<input class="in" name="ref" required maxlength="40" placeholder="C-2026-0141"></label>
          <label class="ins-lab">The household, one 'field, value' a line<textarea class="in mk-mono" name="household" rows="4" placeholder="income, 9500&#10;children, 2&#10;resident, yes"></textarea></label>
          <label class="ins-lab">Evidence already held (one a line)<textarea class="in" name="evidence_held" rows="4" placeholder="proof of income"></textarea></label></div>
        <p class="mut" style="font-size:13px;margin:8px 0 0">Fields: ${esc([...new Set(sch.flatMap(s => s.tests.map(t => t.field)))].join(', '))}</p>
        <div class="md-acts"><span></span><button class="btn" type="submit">Check against the rules</button></div>
        ${o ? (o.error ? err(o) : `<div class="cm-res">${o.schemes.map(caseRes).join('')}<p class="cs-note" style="margin:0">${esc(o.says)}</p></div>`) : ''}</form>` : ''}
      <section class="card"><h2 class="md-h2">Cases</h2>${cs.length ? cs.map(c => `<details class="cm-mt" data-key="c${esc(c.n)}"${ST.open.has('c' + c.n) ? ' open' : ''}><summary class="mk-sum">${esc(c.ref)}<span class="pb-chips">${(c.result || []).map(s => tag(s.scheme + ': ' + STATE[s.state][0], STATE[s.state][1])).join('')}</span><span style="flex:1"></span>${c.decision ? tag('decided', 'v') : ''}<span class="mut nw" style="font-weight:400;font-size:13px">${esc(dt(c.on))}</span>${rmBtn('cases', c.n)}</summary>
          ${(c.result || []).map(caseRes).join('')}
          <div class="pb-hh">${Object.entries(c.household || {}).map(([f, v]) => `<span><em>${esc(f.replace(/_/g, ' '))}</em>${esc(v)}</span>`).join('')}</div>
          ${c.decision ? `<div class="pb-dec"><b>Decision:</b> ${esc(c.decision)} <span class="mut">- ${esc(S(c.decided_by).replace(/ <.*>$/, ''))}, ${esc(dt(c.decided_on))}</span></div>`
            : CAN() ? `<form class="mk-add" data-form="decision" data-n="${esc(c.n)}"><label class="ins-lab" style="flex:1 1 320px">The caseworker's decision, in her words<input class="in" name="decision" maxlength="200" placeholder="Awarded 90 a month from 1 June"></label><button class="btn soft" type="submit">Record the decision</button></form>` : ''}
          ${ask('Case ' + c.ref)}</details>`).join('') : empty('No case checked yet.')}</section>`;
  }
  function caseRes(s) {
    const [t, c] = STATE[s.state] || [s.state, ''];
    return `<div class="pb-res ${c}"><div class="h"><b>${esc(s.scheme)}</b>${tag(t, c)}${s.amount !== null && s.amount !== undefined ? `<span class="pb-amt">${esc(m2(s.amount))}</span>` : ''}</div>
      <div class="pb-tests">${s.met.map(x => `<code class="ok">${esc(x.field.replace(/_/g, ' '))} ${esc(x.rule)} · ${esc(x.household)}</code>`).join('')}${s.missed.map(x => `<code class="bad">${esc(x.field.replace(/_/g, ' '))} ${esc(x.rule)} · ${esc(x.household)}${x.by !== undefined ? ` (by ${esc(sgn(x.by))})` : ''}</code>`).join('')}${s.unknown_fields.map(f => `<code class="warn">${esc(f.replace(/_/g, ' '))}: not given</code>`).join('')}</div>
      ${s.evidence_missing.length ? `<div class="mut" style="font-size:13px">Evidence still missing: ${esc(s.evidence_missing.join(', '))}</div>` : ''}<div class="mut" style="font-size:12.5px">Source: ${esc(s.source)}</div></div>`;
  }

  /* ---------------------------------------------------------------- overpayments */
  function pOverpay() {
    const k = K(), op = k.overpay || {};
    return `<div><h1 class="sd-h">Overpayments</h1><p class="lead">What was due against what was paid, case by case and period by period. Whether an overpayment is recovered, and how, is the official's decision under your rules.</p></div>
      ${ro()}${err(op)}
      ${ok_(op) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Cases checked', esc(num(op.checked)))}${kpi('Overpaid', esc(m2(op.overpaid)), '', op.overpaid ? 'bad' : '')}${kpi('Underpaid', esc(m2(op.underpaid)), '', op.underpaid ? 'warn' : '')}${kpi('Net', esc(m2(op.net)))}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Cases with a difference</h2><div class="r"><button class="btn soft sm" type="button" data-dl="overpay">CSV</button></div></div>
          ${op.cases.length ? `${bars(op.cases.slice(0, 12).map(c => [c.case, c.overpaid || c.underpaid, c.overpaid ? 'dg-dn' : 'mk-age0', c.overpaid ? 'overpaid' : 'underpaid']), m2, 'Differences by case')}
            <div class="iv-tw" style="margin-top:12px"><table class="tb"><thead><tr><th>Case</th><th>Period</th><th class="r">Due</th><th class="r">Paid</th><th class="r">Difference</th><th></th></tr></thead><tbody>${op.cases.slice(0, 100).flatMap(c => c.periods.map((p, i) => `<tr><td>${i ? '' : `<b>${esc(c.case)}</b>`}</td><td>${esc(p.period)}</td><td class="r">${esc(m2(p.due))}</td><td class="r">${esc(m2(p.paid))}</td><td class="r ${p.difference > 0 ? 'cs-neg' : 'cs-pos'}">${esc(sgn(p.difference))}</td><td class="r">${i ? '' : ask('Overpayment on case ' + c.case)}</td></tr>`)).join('')}</tbody></table></div>` : '<p class="cs-pos" style="margin:0">Every period was paid what was due.</p>'}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What was due</h2>${uploader('due', 'Amounts due (CSV)', 'Columns: case, period, amount.')}${addForm('due', [['case', 'Case'], ['period', 'Period', '', '2026-06'], ['amount', 'Due', 'num']])}</section>
        <section class="card"><h2 class="md-h2">What was paid</h2>${uploader('paid', 'Payments made (CSV)', 'Columns: case, period, amount.')}${addForm('paid', [['case', 'Case'], ['period', 'Period', '', '2026-06'], ['amount', 'Paid', 'num']])}</section></div>`;
  }

  /* ---------------------------------------------------------------- payment run */
  function pG2p() {
    const k = K(), g = k.g2p || {}, hv = g.have || {};
    const list = (t, rows, f) => rows.length ? `<div class="pb-ex"><div class="h"><b>${esc(t)}</b><span class="mut">${esc(num(rows.length))}</span></div>${rows.slice(0, 50).map(f).join('')}</div>` : '';
    return `<div><h1 class="sd-h">Payment runs</h1><p class="lead">A government-to-person payment run: the approved beneficiary list against the payment file against the bank's return - paid right, paid twice, the wrong amount, failed, never sent, paid to someone not on the list, one account shared by several people. Account numbers are kept only as a fingerprint and the last 4.</p></div>
      ${ro()}${err(g)}
      ${ok_(g) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Approved', esc(num(g.approved)), m0(g.approved_total))}${kpi('Paid right', esc(num(g.paid)), '', g.clean ? 'ok' : '')}${kpi('Exceptions', esc(num(g.paid_twice.length + g.not_on_the_list.length + g.wrong_amount.length + g.failed.length + g.never_sent.length + g.shared_accounts.length)), '', g.clean ? '' : 'bad')}${kpi('In the file', esc(m0(g.sent_total)))}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${g.clean ? 'The run is clean' : 'Exceptions'}</h2><div class="r">${g.clean ? '' : '<button class="btn soft sm" type="button" data-dl="g2p">CSV</button>'}</div></div>
          ${g2pBars(g)}
          <div class="pb-exs">${list('Paid twice', g.paid_twice, x => `<div class="cs-row"><span style="flex:1">${esc(x.id)} <span class="mut">${esc(x.refs.join(', '))}</span></span><b class="cs-neg">${esc(m2(x.extra))} extra</b></div>`)}
            ${list('Not on the approved list', g.not_on_the_list, x => `<div class="cs-row"><span style="flex:1">${esc(x.id)}</span><b class="cs-neg">${esc(m2(x.amount))}</b></div>`)}
            ${list('Wrong amount', g.wrong_amount, x => `<div class="cs-row"><span style="flex:1">${esc(x.id)} <span class="mut">approved ${esc(m2(x.approved))}</span></span><b class="cs-neg">${esc(sgn(x.difference))}</b></div>`)}
            ${list('Failed at the bank', g.failed, x => `<div class="cs-row"><span style="flex:1">${esc(x.id)} <span class="mut">${esc(x.refs.join(', '))}</span></span>${tag(x.reason, 'warn')}</div>`)}
            ${list('Approved but never sent', g.never_sent, x => `<div class="cs-row"><span style="flex:1">${esc(x.id)}</span><b>${esc(m2(x.amount))}</b></div>`)}
            ${list('One account, several people', g.shared_accounts, x => `<div class="cs-row"><span class="mk-mono" style="flex:1">${esc(x.account)}</span><span>${esc(x.beneficiaries.join(', '))}</span></div>`)}
            ${list('No bank return yet', g.no_bank_return_for.map(r => ({r})), x => `<div class="cs-row"><span class="mk-mono" style="flex:1">${esc(x.r)}</span></div>`)}</div>
          <p class="cs-note">Hoola stops nothing and pays nothing back: the payment officer decides on each exception.</p></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The three files</h2>${CAN() ? `<form class="r" data-form="runname"><input class="in" name="run_name" maxlength="80" value="${esc((k.settings || {}).run_name || '')}" placeholder="June 2026 run" aria-label="Name of the run" style="width:200px"><button class="btn soft sm" type="submit">Name it</button></form>` : ''}</div>
        <div class="pb-three">${uploader('beneficiaries', `1. The approved list${hv.beneficiaries ? ' · ' + num(hv.beneficiaries) : ''}`, 'Columns: beneficiary id, amount, account number.')}
          ${uploader('payments', `2. The payment file${hv.payments ? ' · ' + num(hv.payments) : ''}`, 'Columns: beneficiary id, payment ref, amount, account number.')}
          ${uploader('bank_return', `3. The bank's return${hv.bank_return ? ' · ' + num(hv.bank_return) : ''}`, 'Columns: payment ref, status (success / failed / returned).')}</div>
        <p class="cs-note">A new file replaces the one before. Full account numbers are not kept.</p></section>`;
  }

  /* ---------------------------------------------------------------- deposit cover */
  function pDeposit() {
    const k = K(), dp = k.deposit || {}, rules = dp.rules || (k.settings || {}).deposit || {};
    return `<div><h1 class="sd-h">Deposit cover</h1><p class="lead">A failed bank's depositors: every account added up per depositor (a joint account split equally), set off against their loans if your law says so, covered up to your limit. Records a payout cannot go on are listed first. The insurer's officials approve the payout list.</p></div>
      ${ro()}${err(dp)}
      ${ok_(dp) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Depositors', esc(num(dp.n_depositors)), num(dp.fully_covered) + ' fully covered')}${kpi('Covered', esc(m0(dp.covered_total)), 'limit ' + m0(dp.limit))}${kpi('Above cover', esc(m0(dp.above_cover_total)), 'not paid out')}${kpi('Records to fix', esc(num(dp.records_to_fix.length)), '', dp.records_to_fix.length ? 'bad' : '')}</section>
        ${dp.records_to_fix.length ? `<section class="card"><h2 class="md-h2">Fix these before any payout</h2>${dp.records_to_fix.map(x => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">${esc(x.problem)}</span><span class="mk-mono">${esc(x.account || (x.depositors || []).join(', '))}</span></div>`).join('')}</section>` : ''}
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The payout list</h2><div class="r"><button class="btn soft sm" type="button" data-dl="deposit">CSV</button></div></div>
          ${coverBars(dp)}
          <div class="iv-tw" style="margin-top:12px"><table class="tb"><thead><tr><th>Depositor</th><th class="r">Deposits</th>${dp.set_off ? '<th class="r">Loans set off</th>' : ''}<th class="r">Eligible</th><th class="r">Covered</th><th class="r">Above cover</th></tr></thead><tbody>${dp.depositors.slice(0, 300).map(x => `<tr><td><b>${esc(x.depositor)}</b></td><td class="r">${esc(m2(x.deposits))}</td>${dp.set_off ? `<td class="r">${x.loans_set_off ? esc(m2(x.loans_set_off)) : '—'}</td>` : ''}<td class="r">${esc(m2(x.eligible))}</td><td class="r"><b>${esc(m2(x.covered))}</b></td><td class="r ${x.above_cover ? 'cs-neg' : ''}">${x.above_cover ? esc(m2(x.above_cover)) : '—'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${CAN() ? `<form class="card" data-form="deposit"><h2 class="md-h2">Your scheme's rules</h2><div class="cm-grid5">
          <label class="ins-lab">Failed bank<input class="in" name="bank" maxlength="80" value="${esc(rules.bank || '')}"></label>
          <label class="ins-lab">Cover per depositor<input class="in" name="limit" inputmode="decimal" value="${esc(rules.limit ?? '')}"></label>
          <label class="ins-lab">Set loans off against deposits?<select class="in" name="set_off"><option value="false"${rules.set_off ? '' : ' selected'}>No</option><option value="true"${rules.set_off ? ' selected' : ''}>Yes</option></select></label>
          <label class="ins-lab" style="grid-column:span 2">Source (the law)<input class="in" name="source" maxlength="200" value="${esc(rules.source || '')}" placeholder="Deposit Insurance Act, s.12"></label></div>
          <div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">The bank's records</h2><div class="pb-three">
        ${uploader('accounts', 'Deposit accounts', 'Columns: account, holders (depositor ids, ; between joint holders), balance, interest, type (excluded to leave out).')}
        ${uploader('loans', 'Loans to set off', 'Columns: depositor, due.')}
        ${uploader('depositors', 'Depositors', 'Columns: id, name, dob - the name and date of birth are kept only as a fingerprint, to find one person under two IDs.')}</div></section>`;
  }
  function coverBars(dp) {
    const rows = dp.depositors.slice(0, 10); if (!rows.length) return '';
    const mx = Math.max(dp.limit, ...rows.map(r => r.eligible)) || 1;
    return `<div class="pb-cov">${rows.map(r => `<div><span><b>${esc(r.depositor)}</b></span><i><b class="c" style="width:${(r.covered / mx * 100).toFixed(1)}%"></b><b class="a" style="width:${(r.above_cover / mx * 100).toFixed(1)}%"></b><u style="left:${(dp.limit / mx * 100).toFixed(1)}%"></u></i><em>${esc(m0(r.covered))}</em></div>`).join('')}</div>
      <div class="cs-legend"><span><i class="pb-c"></i>Covered</span><span><i class="pb-a"></i>Above cover</span><span><i class="min"></i>Your limit</span></div>`;
  }

  /* ---------------------------------------------------------------- supervision */
  function pSupervision() {
    const k = K(), sv = k.supervision || {};
    return `<div><h1 class="sd-h">Supervision</h1><p class="lead">Banks' returns against your thresholds: capital ratio, liquidity coverage, bad-loan ratio and the largest exposure - breaches, banks far from their peers, and the change since the period before. Hoola takes no supervisory action.</p></div>
      ${ro()}${err(sv)}
      ${sv.need_thresholds ? '<p class="cs-note">Set your thresholds in Settings to check the returns.</p>' : ''}
      ${ok_(sv) ? `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Capital ratio${sv.period ? ' · ' + esc(sv.period) : ''}</h2>${carBars(sv)}</section>
          <section class="card"><h2 class="md-h2">Breaches and outliers</h2>${sv.in_breach.length ? sv.banks.filter(b => b.breaches.length).map(b => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1"><b>${esc(b.bank)}</b> <span class="mut">${esc(b.breaches.join('; '))}</span></span>${ask('Bank ' + b.bank + ' breach')}</div>`).join('') : '<p class="cs-pos" style="margin:0">No bank is in breach.</p>'}
            ${sv.far_from_peers.length ? `<div class="cr-sub" style="margin-top:12px">Far from the peer group</div>${sv.far_from_peers.map(o => `<div class="cs-row"><span style="flex:1">${esc(o.bank)} · ${esc(o.measure.toUpperCase())}</span><b>${esc(o.value)}%</b><span class="mut">peers ${esc(o.peer_median)}%</span></div>`).join('')}` : ''}</section></div>
        <section class="card"><h2 class="md-h2">Every bank</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Bank</th><th class="r">Capital ratio</th><th class="r">Liquidity</th><th class="r">Bad loans</th><th class="r">Largest exposure</th>${sv.have_previous ? '<th class="r">Capital since ' + esc(sv.previous_period || 'last period') + '</th>' : ''}</tr></thead><tbody>${sv.banks.map(b => { const th = sv.thresholds;
            const c = (v, lim, low) => v === undefined ? '—' : `<span class="${lim !== undefined && (low ? v < lim : v > lim) ? 'cs-neg' : ''}">${esc(v)}%</span>`;
            return `<tr><td><b>${esc(b.bank)}</b></td><td class="r">${c(b.car, th.car_min, true)}</td><td class="r">${c(b.lcr, th.lcr_min, true)}</td><td class="r">${c(b.npl, th.npl_max, false)}</td><td class="r">${c(b.large_exposure, th.large_exposure_max, false)}</td>${sv.have_previous ? `<td class="r ${sign(b.moves.car_points)}">${b.moves.car_points !== undefined ? esc(sgn(b.moves.car_points)) + ' pts' : '—'}</td>` : ''}</tr>`; }).join('')}</tbody></table></div></section>` : ''}
      ${CAN() ? `<form class="card" data-form="returns"><h2 class="md-h2">This period's returns</h2>
          <div class="mk-three"><label class="ins-lab">Period<input class="in" name="period_label" maxlength="40" placeholder="2026 Q3"></label>
            <label class="ins-lab cm-check" style="align-self:end"><input type="checkbox" name="new_period"${(k.counts || {}).returns ? ' checked' : ''}> Keep the returns on the desk as the period before</label>
            <label class="btn soft" style="align-self:end;justify-content:center">Choose the returns (CSV)<input type="file" accept=".csv,text/csv,.txt" data-retfile="1" hidden></label></div>
          <p class="mut" style="font-size:13px;margin:8px 0 0">Columns: bank, capital, rwa, liquid assets, net outflows, npl, loans, largest exposure.</p></form>` : ''}`;
  }

  /* ---------------------------------------------------------------- inspections */
  function pInspections() {
    const k = K(), ins = k.inspections || {};
    return `<div><h1 class="sd-h">Inspections</h1><p class="lead">An inspection's findings with their owners and due dates: open, overdue, with no owner, and the ones in an area found before.</p></div>
      ${ro()}${err(ins)}
      ${ok_(ins) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Open', esc(num(ins.open)))}${kpi('Overdue', esc(num(ins.overdue.length)), '', ins.overdue.length ? 'bad' : '')}${kpi('No owner', esc(num(ins.without_owner.length)), '', ins.without_owner.length ? 'bad' : '')}${kpi('Repeat', esc(num(ins.repeat.length)), 'same area as before', ins.repeat.length ? 'warn' : '')}</section>
        <div class="md-2" style="align-items:start"><section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Findings</h2><div class="r"><button class="btn soft sm" type="button" data-dl="findings">CSV</button></div></div>
            ${ins.findings.map(f => `<div class="cs-row${f.status === 'closed' ? ' pb-done' : ''}"><span class="cs-dot${f.overdue_days ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(f.id)}</b> ${esc(f.area)} <span class="mut" style="display:block;font-size:13px">${esc(f.owner || 'no owner')}${f.due ? ' · due ' + esc(dmy(f.due)) : ''}${f.overdue_days ? ` · ${esc(pl(f.overdue_days, 'day'))} overdue` : ''}${f.repeat_of.length ? ' · repeat of ' + esc(f.repeat_of.join(', ')) : ''}</span></span>
              ${f.status === 'closed' ? tag('closed ' + dmy(f.closed_on || ''), 'ok') : ''}${CAN() ? (f.status === 'closed' ? `<button class="btn soft sm" type="button" data-reopen="${esc(f.n)}">Reopen</button>` : `<button class="btn soft sm" type="button" data-closef="${esc(f.n)}">Closed</button>`) : ''}${ask('Finding ' + f.id)}</div>`).join('')}</section>
          <section class="card"><h2 class="md-h2">Open, by owner</h2>${ins.by_owner.length ? bars(ins.by_owner.map(([o, v]) => [o, v, o === 'no owner' ? 'dg-dn' : 'mk-b']), v => pl(v, 'finding'), 'Open findings by owner') : '<p class="cs-pos" style="margin:0">Nothing open.</p>'}</section></div>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">This inspection</h2>${uploader('findings', 'Findings (CSV)', 'Columns: id, area, owner, due, status.')}${addForm('findings', [['id', 'ID'], ['area', 'Area'], ['owner', 'Owner'], ['due', 'Due', 'date']])}</section>
        <section class="card"><h2 class="md-h2">Earlier findings</h2>${uploader('earlier', 'Earlier findings (CSV)', 'Columns: id, area - to find repeats.')}<p class="mut" style="font-size:13px">${esc(pl((k.earlier || []).length, 'earlier finding'))} on the desk.</p></section></div>`;
  }

  /* ---------------------------------------------------------------- development projects */
  function pDevfin() {
    const k = K(), pj = k.projects || {}, ps = pj.projects || [], ed = ST.out.editProject ? ps.find(p => p.n === ST.out.editProject) : null, e = ed ? ed.setup : {};
    return `<div><h1 class="sd-h">Development projects</h1><p class="lead">Each project's tranches against the conditions met, spending against the budget lines, spending outside the eligible categories, and the indicators against their targets.</p></div>
      ${ro()}
      ${ps.map(p => `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(p.name)}${p.donor ? ` <span class="mut" style="font-weight:400">${esc(p.donor)}</span>` : ''}</h2><div class="r">${ask('Project ' + p.name)}${CAN() ? `<button class="btn soft sm" type="button" data-editp="${esc(p.n)}">Change</button>` : ''}${rmBtn('projects', p.n)}</div></div>
        ${p.error ? err(p) : `<div class="cm-rgrid"><div><span>Budget</span><b>${esc(m0(p.budget_total))}</b></div><div><span>Spent</span><b>${esc(m0(p.spent_total))}</b></div><div><span>Tranches released</span><b>${esc(num(p.tranches.filter(t => t.released).length))} of ${esc(num(p.tranches.length))}</b></div><div><span>Outside eligible</span><b class="${p.ineligible.length ? 'cs-neg' : ''}">${esc(m0(p.ineligible.reduce((s, x) => s + x.amount, 0)))}</b></div></div>
          <div class="md-2" style="align-items:start;margin-top:14px"><div><div class="cr-sub">Tranches</div>${p.tranches.map(t => `<div class="cs-row"><span style="flex:1"><b>${esc(t.tranche)}</b> ${esc(m0(t.amount))}${t.conditions_missing.length ? `<span class="mut" style="display:block;font-size:13px">missing: ${esc(t.conditions_missing.join(', '))}</span>` : ''}</span>${t.released_before_conditions ? tag('released early', 'bad') : t.released ? tag('released', 'ok') : t.conditions_missing.length ? tag('waiting', 'warn') : tag('ready', 'v')}</div>`).join('') || empty('No tranches.')}</div>
            <div><div class="cr-sub">Spending against budget</div>${p.budget_lines.length ? `<div class="pb-bud">${p.budget_lines.map(l => `<div><span><b>${esc(l.line)}</b><em>${esc(m0(l.spent))} of ${esc(m0(l.budget))}</em></span><i><b class="${l.over ? 'bad' : 'ok'}" style="width:${Math.min(100, l.used_pct ?? 100).toFixed(1)}%"></b></i></div>`).join('')}</div>` : empty('No budget lines.')}</div></div>
          ${p.indicators.length ? `<div class="cr-sub" style="margin-top:14px">Indicators</div>${bars(p.indicators.map(x => [x.indicator, Math.min(150, x.achieved_pct || 0), (x.achieved_pct || 0) >= 100 ? 'dg-up' : 'mk-b', `${num(x.actual)} of ${num(x.target)}`]), v => num(v) + '%', 'Indicators against targets')}` : ''}
          ${p.ineligible.length ? `<p class="cs-neg" style="margin:10px 0 0">Outside the eligible categories: ${esc(p.ineligible.slice(0, 8).map(x => `${x.item} ${x.category} ${m0(x.amount)}`).join('; '))}.</p>` : ''}`}</section>`).join('')}
      ${pj.unassigned_spending ? `<p class="cs-note">${esc(pl(pj.unassigned_spending, 'spending line'))} name no project on the desk.</p>` : ''}
      ${CAN() ? `<form class="card" data-form="project"><h2 class="md-h2">${ed ? 'Change ' + esc(ed.name) : 'Add a project'}</h2>
        <div class="mk-two"><label class="ins-lab">Project<input class="in" name="name" required maxlength="80" value="${esc(e.name || '')}" placeholder="Rural water"></label><label class="ins-lab">Funder<input class="in" name="donor" maxlength="60" value="${esc(e.donor || '')}"></label></div>
        <div class="mk-two" style="margin-top:12px"><label class="ins-lab">Tranches: name, amount, conditions (;), released yes/no<textarea class="in" name="tranches" rows="4" placeholder="T1, 1000000, baseline survey, yes&#10;T2, 2000000, audit; progress report, no">${esc((e.tranches || []).map(t => `${t.name}, ${t.amount}, ${t.conditions.join('; ')}, ${t.released ? 'yes' : 'no'}`).join('\n'))}</textarea></label>
          <label class="ins-lab">Conditions met (one a line)<textarea class="in" name="conditions_met" rows="4">${esc((e.conditions_met || []).join('\n'))}</textarea></label></div>
        <div class="mk-three" style="margin-top:12px"><label class="ins-lab">Budget: line, amount<textarea class="in" name="budget" rows="4" placeholder="pipes, 1500000&#10;training, 500000">${esc((e.budget || []).map(b => `${b.line}, ${b.amount}`).join('\n'))}</textarea></label>
          <label class="ins-lab">Indicators: name, target, actual<textarea class="in" name="indicators" rows="4" placeholder="households connected, 1000, 640">${esc((e.indicators || []).map(x => `${x.name}, ${x.target}, ${x.actual}`).join('\n'))}</textarea></label>
          <label class="ins-lab">Eligible spending categories<textarea class="in" name="eligible" rows="4" placeholder="goods&#10;works&#10;consulting">${esc((e.eligible || []).join('\n'))}</textarea></label></div>
        <div class="md-acts"><span>${ed ? '<button class="btn soft" type="button" data-editp="0">Cancel</button>' : ''}</span><button class="btn" type="submit">${ed ? 'Save the changes' : 'Add the project'}</button></div></form>
        <section class="card"><h2 class="md-h2">Spending</h2>${uploader('spending', 'Spending (CSV)', 'Columns: id, project, line, category, amount. ' + num(k.spending_n || 0) + ' lines on the desk.')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, th = s.thresholds || {}, w = W();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your supervisory thresholds. Every threshold, limit and rule on this desk is yours, from your own law or policy - Hoola brings none.</p></div>
      ${ro()}
      <form class="card" data-form="thresholds"><h2 class="md-h2">Supervisory thresholds, in percent</h2><div class="md-form">
        ${[['car_min', 'Capital ratio at least'], ['lcr_min', 'Liquidity coverage at least'], ['npl_max', 'Bad-loan ratio at most'], ['large_exposure_max', 'Largest exposure at most (of capital)'], ['outlier_mad', 'An outlier is this many deviations from peers']].map(([n, l], i) => `<div class="md-field"><label for="pbT${i}">${l}</label><input class="in" id="pbT${i}" name="${n}" inputmode="decimal" value="${esc(th[n] ?? '')}" placeholder="${n === 'outlier_mad' ? '3' : 'yours'}"></div>`).join('')}</div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({due: 'amounts due', paid: 'payments made', bank_return: 'bank return lines', accounts: 'deposit accounts', returns: 'bank returns', earlier: 'earlier findings', spending: 'spending lines', schemes: 'scheme rules', previous: 'returns of the period before'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind.replace('_', ' '))} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('pbN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/public/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) { let m = ''; try { m = (await r.json()).detail; } catch {} throw new Error(m || `Could not download (${r.status})`); }
      const name = ((r.headers.get('content-disposition') || '').match(/filename="([^"]+)"/) || [])[1] || `${what}.csv`;
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = name; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) { toast(e.message, true); }
  }
  async function changed(msg) { if (msg) toast(msg); await refreshDesk(false); showPage(true); }
  const val = (fd, n) => S(fd.get(n)).trim();
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label, summary') && !t.closest('[data-rm]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { setCtx(ak.dataset.ask); return; }
    const dl = t.closest('[data-dl]'); if (dl) { download(dl.dataset.dl); return; }
    const es = t.closest('[data-edits]'); if (es) { ST.out.editScheme = Number(es.dataset.edits) || 0; showPage(true); return; }
    const ep = t.closest('[data-editp]'); if (ep) { ST.out.editProject = Number(ep.dataset.editp) || 0; showPage(true); if (ST.out.editProject) $('#pbPage form[data-form=project]').scrollIntoView({behavior: 'smooth', block: 'start'}); return; }
    try {
      const rm = t.closest('[data-rm]'); if (rm) { e.preventDefault(); await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
      const cf = t.closest('[data-closef]'); if (cf) { await run('close_finding', {n: Number(cf.dataset.closef)}); await changed('Marked closed.'); return; }
      const rf = t.closest('[data-reopen]'); if (rf) { await run('close_finding', {n: Number(rf.dataset.reopen), reopen: true}); await changed('Open again.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const rt = e.target.closest('[data-retfile]');
    if (rt) { const form = rt.closest('form'), f = rt.files && rt.files[0]; if (!f) return;
      try { const r = await run('upload', {kind: 'returns', text: await f.text(), name: f.name, period_label: S(form.querySelector('[name=period_label]').value).trim(), new_period: form.querySelector('[name=new_period]').checked}); rt.value = ''; await changed(r.says + ` from ${f.name}.`); }
      catch (err2) { toast(err2.message, true); rt.value = ''; } return; }
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 20e6) { toast('Up to 20 MB.', true); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name}); fi.value = ''; await changed(r.says + ` from ${f.name}.`); }
    catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    if (form.dataset.form === 'upload' || form.dataset.form === 'returns') return;
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const sent = () => { form.reset(); form.querySelectorAll('select').forEach(x => { delete x.dataset.touched; }); };
    const done = async m => { sent(); await changed(m); };
    const pick = names => { const a = {}; names.forEach(n => { if (g(n) !== '') a[n] = g(n); }); return a; };
    const keepOut = async (key, part, a, msg) => { try { ST.out[key] = await run(part, a); await changed(msg || ''); } catch (err2) { ST.out[key] = {error: err2.message}; showPage(true); } };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/public/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'scheme') { await run('scheme', pick(['name', 'source', 'tests', 'evidence', 'base', 'per_field', 'per_value', 'max'])); ST.out.editScheme = 0; await done('The rules are saved.'); }
      else if (kind === 'case') { await keepOut('case', 'case', pick(['ref', 'household', 'evidence_held']), 'Checked.'); }
      else if (kind === 'decision') { await run('decision', {n: Number(form.dataset.n), decision: g('decision')}); await done('The decision is recorded.'); }
      else if (kind === 'runname') { await run('settings', {run_name: g('run_name')}); await changed('Named.'); }
      else if (kind === 'deposit') { await run('settings', {deposit: {limit: g('limit'), set_off: g('set_off') === 'true', source: g('source'), bank: g('bank')}}); await changed('Saved.'); }
      else if (kind === 'project') { await run('project', pick(['name', 'donor', 'tranches', 'conditions_met', 'budget', 'indicators', 'eligible'])); ST.out.editProject = 0; await done('Saved.'); }
      else if (kind === 'thresholds') { await run('settings', {thresholds: Object.fromEntries(['car_min', 'lcr_min', 'npl_max', 'large_exposure_max', 'outlier_mad'].map(n => [n, g(n)]))}); await changed('Saved.'); }
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
    const box = $('#pbFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/public/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'pb' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


