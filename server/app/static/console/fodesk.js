/* FINANCE DESK ASSISTANT - the Finance Desk Assistant employee's own section, like the other finance desks (owner: "NOW LETS WORK ON
   Finance Desk Assistant SAME WAY"). A thin top bar, then the Finance Desk chat (its own conversation, kind 'finops') beside the desk's
   pages: Today, Owed & owing, Three-way match, Tax withheld, Alerts & screening, Credit, Goals, Settings. The pages call
   /api/finops/do/<part>, which runs the finops engine on her desk. Hoola never pays, files, blocks or approves anything. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h2M12 11h2M16 11h0M8 15h2M12 15h2M8 19h0"/><path d="M16 15v4"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['money', 'Owed & owing'], ['match', 'Three-way match'], ['tax', 'Tax withheld'], ['aml', 'Alerts & screening'],
    ['credit', 'Credit'], ['goals', 'Goals'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'Who owes us the most?', 'Summarise the desk for my manager'],
    money: ['Who is most overdue?', 'Draft a polite reminder to the latest payer', 'Which bills should we pay first?'],
    match: ['Why is this bill on hold?', 'Draft a note to the supplier on the short delivery', 'What does a three-way match check?'],
    tax: ['Why does this party not match?', 'Draft a request for the tax certificate', 'What happens if the tax office does not show it?'],
    aml: ['Explain this alert', 'Is this name match likely the same person?', 'What should the analyst look at next?'],
    credit: ['Explain these ratios', 'What would strengthen this application?', 'Fill in the memo risks from what you know'],
    goals: ['How much more a month at the low scenario?', 'What if I wait two more years?', 'Explain inflation in this goal'],
    settings: ['What cash threshold do banks usually use?', 'What is a usual DSCR floor?', 'Why have a tolerance on rates?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.finops.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.finops.folded') === '1'; } catch {}

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
  const run = (part, a) => api('POST', '/api/finops/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/finops/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Finance Desk Assistant is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="foHire">Hire the Finance Desk Assistant</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#foHire').onclick = async () => { try { await api('POST', '/api/employees/vitt_sahayak/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Finance Desk</div><div class="sd-site" id="foSite"></div></div>
          <span id="foState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="foBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Finance Desk chat">
          <div class="sd-chathead"><div class="t"><b>Finance Desk chat</b><span>Ask about an invoice, a bill on hold, an alert or a borrower - or drop a file here; the last 4 of an account is enough</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="foFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="foPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Finance desk" id="sdTabs"></nav>
          <div id="foPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works from your rows. It never pays, files, blocks or approves anything.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about an invoice, a bill or a borrower…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#foPick').click()});
    $('#foPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.finops.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.finops.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/finops/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#foBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/finops/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#foPage').addEventListener('click', onPageClick);
    $('#foPage').addEventListener('submit', onSubmit);
    $('#foPage').addEventListener('change', onChange);
    $('#foPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#foState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#foSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#foBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), L = (o, f) => (o && !o.empty && !o.error) ? f(o) : 0;
    const rc = (k.money || {}).receivables, al = (k.aml || {}).alerts || {}, sc = (k.aml || {}).screen || {}, wh = (k.tax || {}).withheld;
    const n = ok ? {money: L(rc, o => Object.values(o.by_party).filter(p => p.oldest_days_late > 90).length) || '', match: L(k.match, o => o.to_decide) || '',
      tax: L(wh, o => o.to_check) || '', aml: ((al.alerts ? al.open : 0) + (sc.results ? sc.to_review : 0)) || '',
      credit: ((k.credit || {}).borrowers || []).filter(b => (b.flags || []).length && !b.decision).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/finops/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#foPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, money: pMoney, match: pMatch, tax: pTax, aml: pAml, credit: pCredit, goals: pGoals, settings: pSettings}[ST.tab] || pToday;
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
  const ro = () => CAN() ? '' : `<p class="cs-note">You read this desk as ${esc(RN(ST.d.role))}. Changing it needs the owner, an accountant or an approver.</p>`;
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
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.fo, '')}</div>
      <div><h1 class="sd-h">Set up your finance desk</h1><p class="lead">What you are owed and what you owe, aged by party; suppliers' bills matched to orders and goods received; tax withheld checked against the tax office's statement; transactions checked on your cash threshold and names against your own watch list; borrowers against your credit policy with a memo draft; money goals by scenario. Hoola never pays, files, blocks or approves anything.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('foS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then drop an invoice list on Owed &amp; owing, or a bills file on Three-way match.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="Acme finance team"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;
  const ok_ = o => o && !o.empty && !o.error;
  const BK = [['not_due', 'Not due yet', 'a0'], ['1-30', '1-30 days late', 'a1'], ['31-60', '31-60 days', 'a2'], ['61-90', '61-90 days', 'a3'], ['90+', 'Over 90 days', 'a4']];
  const RULE = {structuring_like: 'Cash just under your threshold', pass_through: 'Money in, money out', many_counterparties: 'Many counterparties', round_amounts: 'Round amounts'};
  const RAT = [['dscr', 'Debt service cover', 'min', 'x'], ['current_ratio', 'Current ratio', 'min', 'x'], ['interest_cover', 'Interest cover', 'min', 'x'],
    ['debt_to_equity', 'Debt to equity', 'max', 'x'], ['ebitda_margin_pct', 'EBITDA margin', '', '%'], ['net_margin_pct', 'Net margin', '', '%']];
  const STAT = {match: ['Matches', 'ok'], not_in_portal: ['Not with the tax office', 'bad'], not_in_books: ['Not in your books', 'warn'], difference: ['Amounts differ', 'bad']};

  /* ---- charts of this desk */
  function ageBar(ag) {   /* one stacked bar of the buckets, with its legend */
    const tot = Number(ag.total_outstanding) || 0;
    if (!tot) return '<p class="cs-pos" style="margin:0">Nothing outstanding.</p>';
    return `<div class="fo-age" role="img" aria-label="Outstanding by age">${BK.map(([k, n, c]) => ag.buckets[k] ? `<b class="${c}" style="width:${(ag.buckets[k] / tot * 100).toFixed(2)}%" title="${esc(n)} ${esc(m2(ag.buckets[k]))}"></b>` : '').join('')}</div>
      <div class="fo-leg">${BK.map(([k, n, c]) => `<span><i class="${c}"></i>${esc(n)}<b>${esc(m0(ag.buckets[k] || 0))}</b></span>`).join('')}</div>`;
  }
  function partyBars(ag, max) {
    const rows = Object.entries(ag.by_party || {}).slice(0, max || 8);
    return bars(rows.map(([p, v]) => [p, v.outstanding, v.oldest_days_late > 90 ? 'dg-dn' : v.oldest_days_late > 30 ? 'mk-age1' : v.oldest_days_late > 0 ? 'mk-age0' : 'dg-up',
      v.oldest_days_late > 0 ? `oldest ${v.oldest_days_late} days late` : 'not due yet']), m0, 'Outstanding by party');
  }
  function ratioRow(key, name, way, unit, v, lim) {   /* a ratio against her floor (or ceiling) */
    if (v === null || v === undefined) return `<div class="fo-rat"><span>${esc(name)}</span><em class="mut">not enough figures</em></div>`;
    const bad = lim !== undefined && lim !== null && (way === 'min' ? v < lim : v > lim);
    const top = Math.max(Math.abs(v), lim || 0) * 1.25 || 1, w = Math.min(100, Math.abs(v) / top * 100);
    return `<div class="fo-rat"><span>${esc(name)}</span><i><b class="${bad ? 'bad' : lim !== undefined && lim !== null ? 'ok' : ''}" style="width:${w.toFixed(1)}%"></b>${lim !== undefined && lim !== null ? `<u style="left:${(Math.min(100, lim / top * 100)).toFixed(1)}%" title="your ${way === 'min' ? 'floor' : 'ceiling'} ${esc(lim)}"></u>` : ''}</i>
      <em class="${bad ? 'cs-neg' : ''}">${esc(num(v))}${unit === '%' ? '%' : '×'}${lim !== undefined && lim !== null ? ` <span class="mut">· yours ${way === 'min' ? '≥' : '≤'} ${esc(lim)}</span>` : ''}</em></div>`;
  }
  const decided = d => d ? `<div class="pb-dec"><b>Decision:</b> ${esc(d.decision)} <span class="mut">- ${esc(S(d.by).replace(/ <.*>$/, ''))}, ${esc(dt(d.on))}</span>${CAN() ? ` <button class="btn soft sm" type="button" data-undec="1">Change</button>` : ''}</div>` : '';
  const decForm = (key, d, label, ph) => d ? `<div data-deckey="${esc(key)}">${decided(d)}</div>` : CAN() ? `<form class="mk-add" data-form="decide" data-key="${esc(key)}"><label class="ins-lab" style="flex:1 1 320px">${esc(label)}<input class="in" name="decision" maxlength="240" placeholder="${esc(ph)}"></label><button class="btn soft" type="submit">Record the decision</button></form>` : '';

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), rc = (k.money || {}).receivables || {}, py = (k.money || {}).payables || {}, mt = k.match || {}, wh = (k.tax || {}).withheld || {},
      al = (k.aml || {}).alerts || {}, sc = (k.aml || {}).screen || {};
    const has = k.counts && Object.values(k.counts).some(Boolean);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : has ? 'Everything on the desk is in order.' : 'Drop an invoice list or a bills file to start.';
    const tiles = [];
    tiles.push(`<div class="k${ok_(rc) && rc.buckets['90+'] ? ' low bad' : ''}"><div class="l">You are owed</div><div class="v">${ok_(rc) ? esc(m0(rc.total_outstanding)) : '—'}</div><div class="s">${ok_(rc) ? esc(m0(rc.buckets['90+'])) + ' over 90 days late' : 'no invoices yet'}</div></div>`);
    tiles.push(`<div class="k"><div class="l">You owe</div><div class="v">${ok_(py) ? esc(m0(py.total_outstanding)) : '—'}</div><div class="s">${ok_(py) ? esc(m0(py.total_outstanding - (py.buckets.not_due || 0))) + ' past due' : 'no bills yet'}</div></div>`);
    tiles.push(`<div class="k${ok_(mt) && mt.to_decide ? ' low bad' : ''}"><div class="l">Bills on hold</div><div class="v">${ok_(mt) ? esc(num(mt.hold)) : '—'}</div><div class="s">${ok_(mt) ? `${esc(m0(mt.held_value))} · ${esc(num(mt.to_decide))} to decide` : 'no bills matched yet'}</div></div>`);
    const open = (ok_(al) && !al.need_threshold ? al.open : 0) + (ok_(sc) && !sc.need_watch ? sc.to_review : 0);
    tiles.push(`<div class="k${open ? ' low bad' : ''}"><div class="l">To review</div><div class="v">${esc(num(open))}</div><div class="s">${ok_(wh) && wh.to_check ? esc(pl(wh.to_check, 'tax line')) + ' to check' : 'alerts and name matches'}</div></div>`);
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">What you are owed, by age</h2><div class="r"><button class="btn soft sm" type="button" data-go="money">Open</button></div></div>
          ${ok_(rc) ? ring(BK.map(([key, n, c]) => [n, rc.buckets[key] || 0, 'fo-' + c]), short(rc.total_outstanding), cur(), 'What you are owed, by age') || '<p class="cs-pos" style="margin:0">Nothing outstanding.</p>' : empty(rc.error || 'Drop the invoices you are owed on Owed & owing.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Who owes you most</h2><div class="r"><button class="btn soft sm" type="button" data-go="money">Open</button></div></div>
          ${ok_(rc) ? partyBars(rc, 6) : empty('No invoices yet.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Bills against orders</h2><div class="r"><button class="btn soft sm" type="button" data-go="match">Open</button></div></div>
          ${ok_(mt) ? ring([['Match', mt.match, 'mk-ok'], ['On hold', mt.hold, 'mk-mc']], num(mt.results.length), 'bills', 'Bills against orders') : empty(mt.error || 'Drop purchase orders, goods received and bills on Three-way match.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- owed and owing */
  function agePanel(side, title, who) {
    const k = K(), ag = (k.money || {})[side] || {};
    return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(title)}</h2><div class="r">${ok_(ag) ? `<button class="btn soft sm" type="button" data-dl="${side}">CSV</button>` : ''}</div></div>
      ${err(ag)}${ok_(ag) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(3,minmax(0,1fr));margin:0 0 14px">${kpi('Outstanding', esc(m2(ag.total_outstanding)))}${kpi('Past due', esc(m2(ag.total_outstanding - (ag.buckets.not_due || 0))), '', ag.total_outstanding - (ag.buckets.not_due || 0) ? 'warn' : '')}${kpi('Over 90 days', esc(m2(ag.buckets['90+'] || 0)), '', ag.buckets['90+'] ? 'bad' : '')}</section>
        ${ageBar(ag)}<div class="cr-sub" style="margin-top:16px">By ${esc(who)}</div>${partyBars(ag, 10)}
        <details class="ins-more" style="margin-top:12px"><summary>Every open invoice (${esc(num(ag.rows.length))})</summary><div class="iv-tw"><table class="tb"><thead><tr><th>${esc(cap(who))}</th><th>Invoice</th><th class="r">Outstanding</th><th class="r">Days late</th><th>Age</th><th></th></tr></thead><tbody>${ag.rows.slice(0, 300).map(r => `<tr><td>${esc(r.party)}</td><td>${esc(r.invoice_no)}</td><td class="r">${esc(m2(r.outstanding))}</td><td class="r">${esc(num(r.days_late))}</td><td>${tag((BK.find(b => b[0] === r.bucket) || [0, r.bucket])[1], r.bucket === '90+' ? 'bad' : r.bucket === 'not_due' ? 'ok' : 'warn')}</td><td class="r">${ask(`Invoice ${r.invoice_no} (${r.party})`)}</td></tr>`).join('')}</tbody></table></div></details>` : ''}
      ${uploader(side, side === 'receivables' ? 'Invoices you are owed (CSV)' : 'Bills you owe (CSV)', `Columns: ${who}, invoice no, due date, amount, paid.`)}
      ${addForm(side, [['party', cap(who)], ['invoice_no', 'Invoice'], ['due_date', 'Due', 'date'], ['amount', 'Amount', 'num'], ['paid', 'Paid', 'num']])}</section>`;
  }
  function pMoney() {
    return `<div><h1 class="sd-h">Owed &amp; owing</h1><p class="lead">Every open invoice aged by how late it is, and by party. A reminder or a payment run is the approver's tap in your own system - Hoola sends and pays nothing.</p></div>
      ${ro()}${agePanel('receivables', 'What you are owed', 'customer')}${agePanel('payables', 'What you owe', 'supplier')}`;
  }

  /* ---------------------------------------------------------------- three-way match */
  function pMatch() {
    const k = K(), mt = k.match || {}, c = k.counts || {};
    return `<div><h1 class="sd-h">Three-way match</h1><p class="lead">Each supplier's bill against its purchase order and the goods received - quantity and rate, within your tolerances. A bill on hold waits for the approver: release it or keep holding it, recorded here in their words.</p></div>
      ${ro()}${err(mt)}
      ${ok_(mt) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Bills', esc(num(mt.results.length)))}${kpi('Match', esc(num(mt.match)), '', 'cs-pos')}${kpi('On hold', esc(num(mt.hold)), m2(mt.held_value), mt.hold ? 'bad' : '')}${kpi('To decide', esc(num(mt.to_decide)), '', mt.to_decide ? 'warn' : '')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The bills</h2><div class="r"><button class="btn soft sm" type="button" data-dl="match">CSV</button></div></div>
          ${mt.results.map(x => `<div class="pb-res ${x.status === 'match' ? 'ok' : 'bad'}" data-deckey="bill:${esc(x.invoice)}"><div class="h"><b>${esc(x.invoice)}</b><span class="mut">PO ${esc(x.po)}</span>${tag(x.status === 'match' ? 'Match' : 'On hold', x.status === 'match' ? 'ok' : 'bad')}${x.amount !== null && x.amount !== undefined ? `<span class="pb-amt">${esc(m2(x.amount))}</span>` : ''}</div>
            ${x.issues.length ? `<div class="pb-tests">${x.issues.map(i => `<code class="bad">${esc(i)}</code>`).join('')}</div>` : ''}
            ${x.status === 'hold' ? decForm('bill:' + x.invoice, x.decision, "The approver's decision", 'Release - the rest arrives Friday') : ''}</div>`).join('')}
          <p class="cs-note" style="margin:12px 0 0">${esc(mt.not_checked)}</p></section>` : ''}
      <section class="card"><h2 class="md-h2">The files</h2><div class="pb-three">
        ${uploader('pos', `Purchase orders${c.pos ? ' · ' + num(c.pos) : ''}`, 'Columns: po, qty, price.')}
        ${uploader('grns', `Goods received${c.grns ? ' · ' + num(c.grns) : ''}`, 'Columns: po, qty.')}
        ${uploader('bills', `Suppliers' bills${c.bills ? ' · ' + num(c.bills) : ''}`, 'Columns: invoice no, po, qty, price.')}</div>
        ${CAN() ? '' : empty('Only the owner, an accountant or an approver adds files.')}</section>`;
  }

  /* ---------------------------------------------------------------- tax */
  function pTax() {
    const k = K(), tx = k.tax || {}, wh = tx.withheld || {}, adv = tx.advance || {}, s = k.settings || {};
    return `<div><h1 class="sd-h">Tax withheld</h1><p class="lead">The tax others withheld from your payments, in your books against the tax office's own statement (in India: Form 26AS / AIS), party by party. What to ask each party is listed; the claim itself is for your accountant.</p></div>
      ${ro()}${err(wh)}
      ${ok_(wh) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(3,minmax(0,1fr))">${kpi('Parties', esc(num(wh.rows.length)))}${kpi('Match', esc(num(wh.matched)), '', 'cs-pos')}${kpi('To check', esc(num(wh.to_check)), '', wh.to_check ? 'bad' : '')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your books against the tax office</h2><div class="r"><button class="btn soft sm" type="button" data-dl="withheld">CSV</button></div></div>
          ${bars(wh.rows.filter(r => r.status !== 'match').slice(0, 10).map(r => [r.party + (r.section ? ' · ' + r.section : ''), r.difference, r.difference > 0 ? 'dg-dn' : 'mk-age0', STAT[r.status][0]]), v => sgn(v), 'Differences by party')}
          <div class="iv-tw" style="margin-top:12px"><table class="tb"><thead><tr><th>Party</th><th>Section</th><th class="r">Your books</th><th class="r">Tax office</th><th class="r">Difference</th><th></th><th></th></tr></thead><tbody>${wh.rows.map(r => `<tr><td>${esc(r.party)}</td><td>${esc(r.section)}</td><td class="r">${esc(m2(r.books_tds))}</td><td class="r">${esc(m2(r.portal_tds))}</td><td class="r ${r.difference ? 'cs-neg' : ''}">${esc(sgn(r.difference))}</td><td>${tag(...STAT[r.status])}</td><td class="r">${r.status !== 'match' ? ask(`Tax withheld by ${r.party}`) : ''}</td></tr>`).join('')}</tbody></table></div>
          ${Object.keys(wh.what_to_ask || {}).length ? `<div class="cr-sub" style="margin-top:14px">What to ask</div>${Object.entries(wh.what_to_ask).map(([p, q]) => `<div class="cs-row"><span style="flex:0 0 auto;font-weight:600">${esc(p.replace(/\/$/, ''))}</span><span class="mut">${esc(q)}</span></div>`).join('')}` : ''}
          <p class="cs-note" style="margin:12px 0 0">${esc(wh.not_checked)}</p></section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">In your books</h2>${uploader('books_tds', 'Tax withheld, as you booked it (CSV)', 'Columns: party, section, tds.')}</section>
        <section class="card"><h2 class="md-h2">With the tax office</h2>${uploader('portal_tds', "The tax office's statement (CSV)", 'Columns: deductor, section, tax deducted.')}</section></div>
      <section class="card"><h2 class="md-h2">Advance tax</h2>
        ${adv.not_built ? empty(adv.say) : adv.need ? `<p class="mut" style="margin:0 0 10px">Give the year's tax and what was already withheld to see the instalments.</p>` : err(adv)}
        ${ok_(adv) && adv.instalments ? `${line(adv.instalments.map(x => [dd(x.due), x.cumulative_amount]), 'Advance tax, paid by each date', m0, '', true)}
          <div class="iv-tw"><table class="tb"><thead><tr><th>By</th><th class="r">Share</th><th class="r">This instalment</th><th class="r">Paid by then</th></tr></thead><tbody>${adv.instalments.map(x => `<tr><td>${esc(dmy(x.due))}</td><td class="r">${esc(x.cumulative_pct)}%</td><td class="r"><b>${esc(m2(x.this_instalment))}</b></td><td class="r">${esc(m2(x.cumulative_amount))}</td></tr>`).join('')}</tbody></table></div>
          <p class="cs-note" style="margin:10px 0 0">${esc(adv.note)}</p>` : ''}
        ${!adv.not_built && CAN() ? `<form class="mk-add" data-form="advance"><label class="ins-lab">Tax for the year<input class="in" name="adv_liability" inputmode="decimal" value="${esc(s.adv_liability ?? '')}"></label>
          <label class="ins-lab">Already withheld<input class="in" name="adv_tds" inputmode="decimal" value="${esc(s.adv_tds ?? '')}"></label>
          <label class="ins-lab">Year starting (April of)<input class="in" name="adv_fy" inputmode="numeric" value="${esc(s.adv_fy ?? '')}" placeholder="${new Date().getFullYear()}"></label>
          <button class="btn soft" type="submit">Work it out</button></form>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- AML + screening */
  function pAml() {
    const k = K(), al = (k.aml || {}).alerts || {}, sc = (k.aml || {}).screen || {}, c = k.counts || {};
    const alerts = ok_(al) && al.alerts ? al.alerts : [];
    const byRule = {}; alerts.forEach(a => { byRule[a.rule] = (byRule[a.rule] || 0) + 1; });
    return `<div><h1 class="sd-h">Alerts &amp; screening</h1><p class="lead">Transactions checked against your own cash threshold for patterns worth a look, and names screened against your own watch list. These are signals for the analyst and the compliance officer - Hoola files no report, blocks no account and freezes nothing. Account numbers are kept only as a fingerprint and the last 4.</p></div>
      ${ro()}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Transaction alerts</h2><div class="r">${alerts.length ? '<button class="btn soft sm" type="button" data-dl="alerts">CSV</button>' : ''}</div></div>
        ${al.need_threshold ? `<p class="cs-note" style="margin:0 0 10px">${esc(pl(al.txns, 'transaction'))} on the desk. Set your cash threshold in Settings - Hoola has no threshold of its own.</p>` : err(al)}
        ${ok_(al) && al.alerts ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr));margin:0 0 14px">${kpi('Accounts', esc(num(al.accounts)))}${kpi('Clean', esc(num(al.clean_accounts)), '', 'cs-pos')}${kpi('Alerts', esc(num(alerts.length)), '', alerts.length ? 'warn' : '')}${kpi('Open', esc(num(al.open)), 'threshold ' + m0(al.threshold), al.open ? 'bad' : '')}</section>
          ${alerts.length ? bars(Object.entries(byRule).map(([r, n]) => [RULE[r] || r, n, 'mk-age1']), v => pl(v, 'alert'), 'Alerts by pattern') : '<p class="cs-pos" style="margin:0">No pattern fired on your threshold.</p>'}
          ${alerts.map(a => `<details class="cm-mt" data-key="${esc(a.key)}"${ST.open.has(a.key) ? ' open' : ''}><summary class="mk-sum">Account ${esc(a.account)}<span class="pb-chips">${tag(RULE[a.rule] || a.rule, 'warn')}</span><span style="flex:1"></span>${a.decision ? tag('reviewed', 'v') : ''}</summary>
            <p style="margin:6px 0">${esc(a.why)}</p><div class="fo-draft"><div class="cr-sub">Draft note for the analyst</div><p>${esc(a.draft_narrative)}</p></div>
            ${decForm(a.key, a.decision, "The analyst's decision", 'Closed - matches the customer profile')}${ask('Alert on account ' + a.account)}</details>`).join('')}
          <p class="cs-note" style="margin:12px 0 0">${esc(al.kind_note)} ${esc(al.decider)}</p>` : ''}
        ${uploader('txns', `Transactions (CSV)${c.txns ? ' · ' + num(c.txns) + ' on the desk' : ''}`, 'Columns: account, date, amount, type (cash_in, cash_out, credit, debit), counterparty.')}</section>
      <section class="card"><h2 class="md-h2">Name screening</h2>
        ${sc.need_watch ? `<p class="cs-note" style="margin:0 0 10px">${esc(pl(sc.names, 'name'))} to screen. Add your own watch list - Hoola has no list of its own.</p>` : err(sc)}
        ${ok_(sc) && sc.results ? sc.results.map(r => `<div class="pb-res ${r.possible_matches.length ? 'bad' : 'ok'}"><div class="h"><b>${esc(r.name)}</b>${r.ref ? `<span class="mut">${esc(r.ref)}</span>` : ''}${tag(r.possible_matches.length ? pl(r.possible_matches.length, 'possible match', 'possible matches') : 'No match', r.possible_matches.length ? 'bad' : 'ok')}</div>
            ${r.possible_matches.map(m => `<div class="fo-hit"><span><b>${esc(m.watch_name)}</b> <span class="mut">${esc(m.list || '')}${m.ref ? ' · ' + esc(m.ref) : ''}</span></span><i><b style="width:${(m.score * 100).toFixed(0)}%"></b></i><em>${esc(Math.round(m.score * 100))}%</em><div class="pb-tests">${m.explained_by.map(x => `<code>${esc(x)}</code>`).join('')}</div></div>`).join('')}
            ${r.possible_matches.length ? decForm(r.key, r.decision, "The compliance officer's decision", 'Not the same person - different date of birth') : ''}</div>`).join('')
          + `<p class="cs-note" style="margin:12px 0 0">${esc(sc.not_checked)} ${esc(sc.decider)}</p>` : ''}
        <div class="md-2" style="align-items:start;margin-top:14px">
          <div>${uploader('names', `Names to screen${c.names ? ' · ' + num(c.names) : ''}`, 'Columns: name, ref.')}</div>
          <div>${uploader('watch', `Your watch list${c.watch ? ' · ' + num(c.watch) : ''}`, 'Columns: name, list, ref.')}</div></div></section>`;
  }

  /* ---------------------------------------------------------------- credit */
  function pCredit() {
    const k = K(), cr = k.credit || {}, pol = cr.policy || {}, ed = ST.out.editB ? ((k.credit || {}).borrowers || []).find(b => b.n === ST.out.editB) : null;
    return `<div><h1 class="sd-h">Credit</h1><p class="lead">A borrower's financials worked into ratios, set against your own policy floors, with a credit memo draft that leaves the judgement blanks for the analyst. Sanction or decline belongs to the credit committee - Hoola gives no score and no 'approve'.</p></div>
      ${ro()}
      ${cr.no_policy && !cr.empty ? '<p class="cs-note">No policy floors yet - set them in Settings to see each borrower against them.</p>' : ''}
      ${ok_(cr) ? cr.borrowers.map(b => b.error ? `<section class="card"><b>${esc(b.name)}</b>${err(b)}</section>` : `<section class="card fo-bor"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(b.name)}</h2><div class="r">${b.flags.length ? tag(pl(b.flags.length, 'policy flag'), 'bad') : Object.keys(pol).length ? tag('Within your floors', 'ok') : ''}<button class="btn soft sm" type="button" data-dl="memo:${esc(b.n)}">Memo</button>${CAN() ? `<button class="btn soft sm" type="button" data-editb="${esc(b.n)}">Change</button>` : ''}${rmBtn('borrowers', b.n)}</div></div>
          <p class="mut" style="margin:0 0 12px">${esc(b.purpose || 'Purpose not given')}${b.amount ? ' · ' + esc(m0(b.amount)) : ''}${b.trend.length ? ' · ' + esc(b.trend.join(', ')) : ''}</p>
          <div class="fo-rats">${RAT.map(([key, n, way, u]) => ratioRow(key, n, way, u, b.ratios[key], way ? pol[key] : undefined)).join('')}</div>
          ${b.flags.length ? `<div class="pb-tests" style="margin-top:10px">${b.flags.map(f => `<code class="bad">${esc(f)}</code>`).join('')}</div>` : ''}
          <details class="ins-more" style="margin-top:12px"><summary>The memo draft</summary><div class="fo-memo">${window.HoolaMD ? HoolaMD.render(S(b.memo).replace(/^(#.*)$/gm, '\n$1\n')) : `<pre>${esc(b.memo)}</pre>`}</div><p class="cs-note">${esc(b.not_checked)}</p></details>
          ${decForm(b.key, b.decision, "The credit committee's decision", 'Sanctioned 4,00,000 for 3 years at the committee of 12 June')}${ask('Borrower ' + b.name)}</section>`).join('') : ''}
      ${CAN() ? `<form class="card" data-form="borrower"><h2 class="md-h2">${ed ? 'Change ' + esc(ed.name) : 'Add a borrower'}</h2>
        <div class="mk-three"><label class="ins-lab">Borrower<input class="in" name="name" required maxlength="80" value="${esc(ed ? ed.name : '')}" placeholder="Bolt Traders Ltd"></label>
          <label class="ins-lab">Purpose<input class="in" name="purpose" maxlength="120" value="${esc(ed ? ed.purpose || '' : '')}" placeholder="Working capital"></label>
          <label class="ins-lab">Amount asked<input class="in" name="amount" inputmode="decimal" value="${esc(ed ? ed.amount ?? '' : '')}"></label></div>
        <div class="cr-sub" style="margin-top:14px">This year's financials</div>
        <div class="fo-grid">${[['revenue', 'Revenue'], ['ebitda', 'EBITDA'], ['net_profit', 'Net profit'], ['interest', 'Interest'], ['debt_service', 'Debt service (instalments due)'], ['current_assets', 'Current assets'], ['current_liabilities', 'Current liabilities'], ['total_debt', 'Total debt'], ['net_worth', 'Net worth']].map(([n, l]) => `<label class="ins-lab">${l}<input class="in" name="${n}" inputmode="decimal"></label>`).join('')}</div>
        <div class="cr-sub" style="margin-top:14px">Last year (for the trend)</div>
        <div class="fo-grid">${[['prev_revenue', 'Revenue'], ['prev_ebitda', 'EBITDA'], ['prev_net_profit', 'Net profit']].map(([n, l]) => `<label class="ins-lab">${l}<input class="in" name="${n}" inputmode="decimal"></label>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">From the borrower's own accounts - Hoola does not check whether they are true.</span><button class="btn" type="submit">Work out the ratios</button></div></form>` : ''}
      ${cr.empty && !CAN() ? empty('No borrower yet.') : ''}`;
  }

  /* ---------------------------------------------------------------- goals */
  function pGoals() {
    const k = K(), gl = k.goals || {};
    return `<div><h1 class="sd-h">Goals</h1><p class="lead">A money goal worked into the monthly saving it needs, at three return scenarios - low, mid and high. The returns are scenarios only, never a promise; choosing a product is for you or a registered adviser.</p></div>
      ${ro()}
      ${ok_(gl) ? gl.goals.map(g => g.error ? `<section class="card"><b>${esc(g.name)}</b>${err(g)}</section>` : `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(g.name)}</h2><div class="r">${rmBtn('goals', g.n)}</div></div>
          <p class="mut" style="margin:0 0 12px">${esc(m0(g.goal_amount))} in today's money, in ${esc(num(g.years))} years at ${esc(num(g.inflation_pct))}% a year price rise = <b>${esc(m0(g.amount_needed_then))}</b> then.</p>
          ${bars(g.scenarios.map(s => [cap(s.scenario) + ' · ' + num(s.annual_return_pct) + '%', s.monthly_sip_needed, s.scenario === 'low' ? 'mk-age1' : s.scenario === 'high' ? 'dg-up' : 'mk-b', 'a month']), m0, 'Monthly saving needed')}
          ${ask('Goal ' + g.name)}</section>`).join('') + `<p class="cs-note">${esc(gl.assumed)}${gl.rates_yours ? '' : ' The scenarios are Hoola\'s starting points (6%, 9%, 12%) - change them in Settings.'}</p>` : ''}
      ${CAN() ? `<form class="card" data-form="goal"><h2 class="md-h2">Add a goal</h2>
        <div class="cm-grid5"><label class="ins-lab">For<input class="in" name="name" required maxlength="60" placeholder="School fees"></label>
          <label class="ins-lab">Amount, in today's money<input class="in" name="target" required inputmode="decimal"></label>
          <label class="ins-lab">In how many years<input class="in" name="years" required inputmode="decimal"></label>
          <label class="ins-lab">Saved already<input class="in" name="current" inputmode="decimal" placeholder="0"></label>
          <label class="ins-lab">Price rise a year, %<input class="in" name="inflation" required inputmode="decimal" placeholder="yours"></label></div>
        <div class="md-acts"><span></span><button class="btn" type="submit">Work it out</button></div></form>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, pol = s.policy || {}, rt = s.rates || {}, w = W();
    const fld = (n, l, v, ph, i) => `<div class="md-field"><label for="foT${i}">${l}</label><input class="in" id="foT${i}" name="${n}" inputmode="decimal" value="${esc(v ?? '')}" placeholder="${esc(ph || 'yours')}"></div>`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your thresholds, tolerances and policy floors. Every one is yours, from your own policy - Hoola brings none, and says so wherever one is missing.</p></div>
      ${ro()}
      <form class="card" data-form="checks"><h2 class="md-h2">Checks</h2><div class="md-form">
        ${fld('cash_threshold', `Cash threshold (${esc(cur())})`, s.cash_threshold, '', 1)}${fld('match_threshold', 'Name match from (0 to 1)', s.match_threshold, '0.7', 2)}
        ${fld('qty_tol_pct', 'Quantity tolerance, %', s.qty_tol_pct, '0', 3)}${fld('price_tol_pct', 'Rate tolerance, %', s.price_tol_pct, '0', 4)}
        ${fld('tds_tolerance', `Tax-withheld tolerance (${esc(cur())})`, s.tds_tolerance, '1', 5)}
        <div class="md-field"><label for="foT6">Age invoices as of</label><input class="in" id="foT6" name="as_of" type="date" value="${esc(s.as_of || '')}"></div></div>
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Empty = today, for the ageing date.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <form class="card" data-form="policy"><h2 class="md-h2">Credit policy floors</h2><div class="md-form">
          ${fld('dscr', 'Debt service cover at least', pol.dscr, '', 7)}${fld('current_ratio', 'Current ratio at least', pol.current_ratio, '', 8)}
          ${fld('interest_cover', 'Interest cover at least', pol.interest_cover, '', 9)}${fld('debt_to_equity', 'Debt to equity at most', pol.debt_to_equity, '', 10)}</div>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <form class="card" data-form="rates"><h2 class="md-h2">Goal return scenarios, % a year</h2><div class="md-form">
          ${fld('low', 'Low', rt.low, '6', 11)}${fld('mid', 'Mid', rt.mid, '9', 12)}${fld('high', 'High', rt.high, '12', 13)}</div>
          ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Scenarios, never promises.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({receivables: 'invoices you are owed', payables: 'bills you owe', pos: 'purchase orders', grns: 'goods received lines', bills: "suppliers' bills", books_tds: 'tax withheld in your books', portal_tds: 'tax office lines', txns: 'transactions', watch: 'watch-list names', names: 'names to screen'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind.replace('_', ' '))} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">Country</span><b>${esc(k.country || '—')}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('foN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/finops/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
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
    const eb = t.closest('[data-editb]'); if (eb) { ST.out.editB = Number(eb.dataset.editb) || 0; showPage(true); const f = $('#foPage form[data-form=borrower]'); if (f) f.scrollIntoView({behavior: 'smooth', block: 'start'}); return; }
    try {
      const ud = t.closest('[data-undec]'); if (ud) { const box = ud.closest('[data-deckey]'); await run('decide', {key: box.dataset.deckey, clear: true}); await changed('The decision can be recorded again.'); return; }
      const rm = t.closest('[data-rm]'); if (rm) { e.preventDefault(); await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 20e6) { toast('Up to 20 MB.', true); return; }
    try { const r = await run('upload', {kind: form.dataset.kind, text: await f.text(), name: f.name}); fi.value = ''; await changed(r.says + ` from ${f.name}.`); }
    catch (err2) { toast(err2.message, true); fi.value = ''; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    if (form.dataset.form === 'upload') return;
    const fd = new FormData(form), kind = form.dataset.form, btn = e.submitter || form.querySelector('[type=submit]'), g = n => val(fd, n);
    const sent = () => { form.reset(); form.querySelectorAll('select').forEach(x => { delete x.dataset.touched; }); };
    const done = async m => { sent(); await changed(m); };
    const pick = names => { const a = {}; names.forEach(n => { if (g(n) !== '') a[n] = g(n); }); return a; };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/finops/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'decide') { await run('decide', {key: form.dataset.key, decision: g('decision')}); await done('The decision is recorded.'); }
      else if (kind === 'borrower') { await run('borrower', pick(['name', 'purpose', 'amount', 'revenue', 'ebitda', 'net_profit', 'interest', 'debt_service', 'current_assets', 'current_liabilities', 'total_debt', 'net_worth', 'prev_revenue', 'prev_ebitda', 'prev_net_profit'])); ST.out.editB = 0; await done('The ratios are worked out.'); }
      else if (kind === 'goal') { await run('goal', pick(['name', 'target', 'years', 'current', 'inflation'])); await done('Worked out.'); }
      else if (kind === 'advance') { await run('settings', {adv_liability: g('adv_liability'), adv_tds: g('adv_tds'), adv_fy: g('adv_fy')}); await changed('Worked out.'); }
      else if (kind === 'checks') { await run('settings', Object.fromEntries(['cash_threshold', 'match_threshold', 'qty_tol_pct', 'price_tol_pct', 'tds_tolerance', 'as_of'].map(n => [n, g(n)]))); await changed('Saved.'); }
      else if (kind === 'policy') { await run('settings', {policy: Object.fromEntries(['dscr', 'current_ratio', 'interest_cover', 'debt_to_equity'].map(n => [n, g(n)]))}); await changed('Saved.'); }
      else if (kind === 'rates') { await run('settings', {rates: Object.fromEntries(['low', 'mid', 'high'].map(n => [n, g(n)]))}); await changed('Saved.'); }
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
    const box = $('#foFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/finops/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'fo' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


