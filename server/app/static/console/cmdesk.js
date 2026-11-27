/* COMMUNITY FINANCE DESK - the Community, Inclusive & Islamic Finance employee's own section, like the other finance desks (owner:
   "NOW LETS WORK ON NEXT EMPLOYEE COMMUNITY FINANCE DESK"). A thin top bar, then the Community chat (its own conversation, kind
   'community') beside the desk's pages: Today, Cash book, Savings group, Rotating group, Loans, Collections, Farm, Send money,
   Zakat & Islamic, Settings. The pages call /api/community/do/<part>, which runs the F11 engine on her desk. Hoola never collects,
   lends or sends money. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', cm: '<circle cx="12" cy="7" r="2.4"/><circle cx="5.5" cy="10" r="2"/><circle cx="18.5" cy="10" r="2"/><path d="M8 20c0-3 1.8-5 4-5s4 2 4 5"/><path d="M2.5 19c.3-2.3 1.4-3.6 3-3.6M21.5 19c-.3-2.3-1.4-3.6-3-3.6"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['cash', 'Cash book'], ['group', 'Savings group'], ['rosca', 'Rotating group'], ['loans', 'Loans'],
    ['field', 'Collections'], ['farm', 'Farm'], ['send', 'Send money'], ['zakat', 'Zakat & Islamic'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'How much did I make this week?', 'Who owes the group?'],
    cash: ['sold tea 250, paid rent 2000', 'Where does my money go?', 'Did I make a profit this month?'],
    group: ['Explain the share-out', 'Why does the box not match?', 'Can the group lend 5,000 today?'],
    rosca: ['Is it better to take the pot early or late?', 'What does a bid cost me?', 'Is this chit safe?'],
    loans: ['Which loan is the dearest?', 'Can I afford one more loan?', 'Which loan should I repay first?'],
    field: ['Who should I visit first?', 'Explain portfolio at risk', 'Draft a reminder I can read out'],
    farm: ['What price do I need to break even?', 'How do I file a crop claim?', 'What if the yield drops by a third?'],
    send: ['Which provider is cheapest today?', 'Is this message a scam?', 'Explain the mid-market rate'],
    zakat: ['Is my gold jewellery counted?', 'Explain the nisab', 'How does murabaha differ from a loan?'],
    settings: ['What loan rate do groups usually use?', 'How long is a usual cycle?', 'How is a share value chosen?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.community.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.community.folded') === '1'; } catch {}

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
  const run = (part, a) => api('POST', '/api/community/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/community/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.cm, '')}</div>
        <h1 class="sd-h">Your Community Finance employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="cmHire">Hire Community Finance</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#cmHire').onclick = async () => { try { await api('POST', '/api/employees/community_finance/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.cm, '')}</div>
          <div style="min-width:0"><div class="sd-name">Community</div><div class="sd-site" id="cmSite"></div></div>
          <span id="cmState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="cmBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Community chat">
          <div class="sd-chathead"><div class="t"><b>Community chat</b><span>Tell it what you sold and spent, a meeting's savings, or a loan offer - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="cmFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="cmPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Community desk" id="sdTabs"></nav>
          <div id="cmPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the money. It never collects, lends or sends money.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Say what came in and went out, or ask about your group…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#cmPick').click()});
    $('#cmPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.community.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.community.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/community/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#cmBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/community/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#cmPage').addEventListener('click', onPageClick);
    $('#cmPage').addEventListener('submit', onSubmit);
    $('#cmPage').addEventListener('change', onChange);
    $('#cmPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#cmState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#cmSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#cmBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), gr = k.group || {}, lo = k.loans || {}, fd = k.field || {}, ro = k.rosca || {};
    const L = (o, f) => (o && !o.empty && !o.error) ? f(o) : 0;
    const n = ok ? {group: (L(gr, o => (o.count_mismatches || []).length) || '') , loans: L(lo, o => (o.repayments || {}).over_your_limit && o.limit_set ? 1 : 0) || '',
      field: L(fd, o => (o.arrears || []).length) || '', rosca: L(ro, o => (o.flags || []).length) || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/community/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#cmPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, cash: pCash, group: pGroup, rosca: pRosca, loans: pLoans, field: pField, farm: pFarm, send: pSend, zakat: pZakat,
      settings: pSettings}[ST.tab] || pToday;
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
  const ro = () => CAN() ? '' : `<p class="cs-note">You read this desk as ${esc(RN(ST.d.role))}. Changing it needs the owner, the treasurer or the chair.</p>`;
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
      t === 'io' ? `<label class="ins-lab">${esc(l)}<select class="in" name="${n}"><option value="in">Money in</option><option value="out">Money out</option></select></label>`
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
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.cm, '')}</div>
      <div><h1 class="sd-h">Set up your community money desk</h1><p class="lead">A cash book you can speak into, a savings group's books with every meeting and the share-out to the last cent, a rotating group or chit with its rounds, the true cost of your loans, a field officer's collection sheet, crop plans, the cheapest way to send money home, and your zakat. Hoola never collects, lends or sends money.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('cmS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then tell the chat what you sold and spent today, or add your group's members.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="Umoja women's group"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="KE"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="KES"></div></div>`;
  const ok_ = o => o && !o.empty && !o.error;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), cb = k.cash || {}, gr = k.group || {}, ro = k.rosca || {}, lo = k.loans || {}, fd = k.field || {};
    const has = k.counts && Object.values(k.counts).some(Boolean);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : has ? 'Everything on the desk is in order.' : 'Tell the chat what came in and went out today, or add your group\'s members.';
    const owes = ok_(gr) ? Object.values(gr.owes || {}).reduce((s, v) => s + v, 0) : null;
    const rp = ok_(lo) ? lo.repayments || {} : {};
    const k4 = ok_(lo) && rp.share_of_income_pct !== null && rp.share_of_income_pct !== undefined
      ? `<div class="k${lo.limit_set && rp.over_your_limit ? ' low bad' : ''}"><div class="l">Repayments</div><div class="v">${esc(num(Math.round(rp.share_of_income_pct)))}%</div><div class="s">of your income · ${esc(m0(rp.per_month))} a month</div></div>`
      : ok_(ro) && ro.next ? `<div class="k"><div class="l">Next payout</div><div class="v cm-name">${esc(ro.next.takes)}</div><div class="s">round ${esc(ro.next.round)}${ro.next.date ? ' · ' + esc(dmy(ro.next.date)) : ''}</div></div>`
      : ok_(fd) ? `<div class="k${fd.par30_pct ? ' low' : ''}"><div class="l">Collected</div><div class="v">${fd.collection_rate_pct === null ? '—' : esc(num(fd.collection_rate_pct)) + '%'}</div><div class="s">PAR30 ${fd.par30_pct === null ? '—' : esc(num(fd.par30_pct)) + '%'}</div></div>`
      : `<div class="k"><div class="l">Repayments</div><div class="v">—</div><div class="s">no loans yet</div></div>`;
    const bal = ok_(cb) ? cb.by_day.slice(-30).map(d => [dd(d.date), d.balance]) : [];
    const sv = ok_(gr) ? Object.entries(gr.savings || {}).sort((a, b) => b[1] - a[1]).slice(0, 10) : [];
    const up = [];
    if (ok_(ro) && ro.next) up.push({d: ro.next.date, w: `${ro.next.takes} takes the pot`, s: `round ${ro.next.round} of ${(ro.schedule || ro.rounds || []).length}`});
    if (ok_(gr) && gr.rules && gr.rules.cycle_end) up.push({d: gr.rules.cycle_end, w: 'The cycle ends - the share-out', s: gr.days_to_cycle_end >= 0 ? 'in ' + pl(gr.days_to_cycle_end, 'day') : 'passed'});
    const z = (k.settings || {}).zakat || {}; if (z.hawl) up.push({d: z.hawl, w: 'Your zakat date', s: 'update the values on Zakat'});
    up.sort((a, b) => S(a.d || '9').localeCompare(S(b.d || '9')));
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k${ok_(cb) && cb.closing < 0 ? ' low bad' : ''}"><div class="l">Cash in hand</div><div class="v">${ok_(cb) ? esc(m0(cb.closing)) : '—'}</div><div class="s">${ok_(cb) ? `this week +${esc(m0(cb.week_in))} / −${esc(m0(cb.week_out))}` : 'no cash book yet'}</div></div>
        <div class="k"><div class="l">Group's box</div><div class="v">${ok_(gr) ? esc(m0(gr.cash_box)) : '—'}</div><div class="s">${ok_(gr) ? `${esc(m0(gr.loans_outstanding))} lent out · social ${esc(m0(gr.social_fund))}` : 'no savings group yet'}</div></div>
        <div class="k${owes ? ' low' : ''}"><div class="l">Members owe</div><div class="v">${owes === null ? '—' : esc(m0(owes))}</div><div class="s">${ok_(gr) ? (owes ? esc(pl(Object.keys(gr.owes).length, 'member')) : 'nobody owes the group') : 'no loans in a group'}</div></div>
        ${k4}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Coming up</h2></div>
          ${up.length ? `<ol class="mk-tl">${up.map(x => `<li><span class="d"><b>${esc(x.d ? dmy(x.d) : 'next')}</b><em>${esc(x.s)}</em></span><span class="w">${esc(x.w)}</span></li>`).join('')}</ol>` : empty('Rotating-group payouts, the end of the cycle and your zakat date show here.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Cash in hand, day by day</h2><div class="r"><button class="btn soft sm" type="button" data-go="cash">Cash book</button></div></div>
          ${bal.length > 1 ? line(bal, 'Cash in hand day by day', m0) : empty(cb.error || 'Two days on the cash book draw the line.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Savings by member</h2><div class="r"><button class="btn soft sm" type="button" data-go="group">Savings group</button></div></div>
          ${sv.length && sv.some(x => x[1]) ? bars(sv.map(([n, v]) => [n, v, 'cm-sv', (gr.owes || {})[n] ? 'owes ' + m0(gr.owes[n]) : '']), m0, 'Savings by member') : empty(gr.error || 'Record a meeting to see who has saved what.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- cash book */
  function pCash() {
    const k = K(), cb = k.cash || {}, o = ST.out.cash;
    const bal = ok_(cb) ? cb.by_day.slice(-45).map(d => [dd(d.date), d.balance]) : [];
    return `<div><h1 class="sd-h">Cash book</h1><p class="lead">Say or type what came in and went out, the way you would tell a friend: "sold tea 250", "paid rent 2000". Each line needs one amount; a line Hoola cannot read is shown back to you, never guessed.</p></div>
      ${ro()}
      ${CAN() ? `<form class="card" data-form="cash"><h2 class="md-h2">What came in and went out</h2>
        <textarea class="in cm-say" name="text" rows="4" placeholder="sold tea 250&#10;sold mandazi 300&#10;paid transport 80&#10;2026-11-20 bought stock 1500"></textarea>
        <div class="md-acts"><label class="ins-lab cm-inl">Date<input class="in" type="date" name="date" value="${esc(new Date().toISOString().slice(0, 10))}"></label><button class="btn" type="submit">Put on the cash book</button></div>
        ${o && o.could_not_read && o.could_not_read.length ? `<div class="cm-unread"><b>Could not read ${esc(pl(o.could_not_read.length, 'line'))}</b><span>Say each again with one amount and a word like sold, paid, bought or got. It is left in the box above.</span>${o.could_not_read.map(x => `<div class="mk-mono">${esc(x)}</div>`).join('')}</div>` : ''}
        ${o && o.error ? err(o) : ''}</form>` : ''}
      ${ok_(cb) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('In hand now', esc(m0(cb.closing)), 'opening ' + m0(cb.opening), cb.closing < 0 ? 'bad' : '')}${kpi('This month in', esc(m0(cb.month_in)))}${kpi('This month out', esc(m0(cb.month_out)))}${kpi('All in / out', esc(short(cb.money_in)) + ' / ' + esc(short(cb.money_out)))}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Day by day</h2><div class="r">${ok_(cb) ? '<button class="btn soft sm" type="button" data-dl="cashbook">CSV</button>' : ''}</div></div>
          ${bal.length > 1 ? line(bal, 'Cash in hand', m0) : empty(cb.error || 'Two days on the cash book draw the line.')}
          ${ok_(cb) ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Day</th><th class="r">In</th><th class="r">Out</th><th class="r">In hand</th></tr></thead><tbody>${cb.by_day.slice(-14).reverse().map(d => `<tr><td>${esc(dmy(d.date))}</td><td class="r cs-pos">${d.in ? esc(m0(d.in)) : ''}</td><td class="r cs-neg">${d.out ? esc(m0(d.out)) : ''}</td><td class="r"><b>${esc(m0(d.balance))}</b></td></tr>`).join('')}</tbody></table></div>` : ''}</section>
        <section class="card"><h2 class="md-h2">Where the money went</h2>
          ${ok_(cb) && cb.out_by_word.length ? bars(cb.out_by_word.map(([w, v]) => [cap(w), v, 'cm-out']), m0, 'Money out by word') : empty('Lines with "paid", "bought" or "spent" show here, grouped by the word after it.')}
          ${CAN() ? `<details class="ins-more" style="margin-top:14px"><summary>Add one line or a file</summary>${addForm('cash', [['date', 'Date', 'date'], ['kind', 'In or out', 'io'], ['amount', 'Amount', 'num'], ['note', 'What', '', 'sold eggs']])}${uploader('cash', 'A cash-book file (CSV)', 'Columns: date, in or out, amount, what.')}</details>` : ''}</section></div>
      <section class="card"><h2 class="md-h2">Every line</h2>${ok_(cb) ? listRows('cash', cb.rows, [['date', 'Date', 0, v => esc(dmy(v))], ['kind', '', 0, v => tag(v === 'in' ? 'In' : 'Out', v === 'in' ? 'ok' : 'warn')], ['note', 'What'], ['amount', 'Amount', 1, v => esc(m0(v))], ['src', 'From', 0, v => `<span class="mut">${esc({said: 'said', form: 'typed', file: 'file'}[v] || v || '')}</span>`]], 200) : empty('Nothing on the cash book yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- savings group */
  function pGroup() {
    const k = K(), gr = k.group || {}, rules = (k.settings || {}).group || {}, mem = k.members || [];
    const unit = rules.share_value ? 'shares' : 'amount';
    if (!mem.length) return `<div><h1 class="sd-h">Savings group</h1><p class="lead">A VSLA, self-help group, chama, susu or caja de ahorro: members save at each meeting, borrow from the box at the group's own rate, and share everything out at the end of the cycle in proportion to what each saved.${k.style ? ' In ' + esc(k.country) + ': ' + esc(k.style) + '.' : ''}</p></div>
      ${ro()}<section class="card"><h2 class="md-h2">Add the members</h2>${addForm('members', [['name', 'Name', '', 'Amina'], ['phone', 'Phone (optional)', '', '']], 'Add member')}${uploader('members', 'A members list (CSV)', 'Columns: name, phone.')}
      <p class="cs-note">Then set the group's rules in Settings: the value of one share (if you save in shares) and the loan rate each month.</p></section>`;
    const so = ok_(gr) ? gr.share_out : null, box = ok_(gr) ? gr.meetings.map(m => [S(m.meeting).slice(5), m.cash]) : [];
    const lastM = (k.meetings || [])[0];
    return `<div><h1 class="sd-h">${esc(rules.name || 'Savings group')}</h1><p class="lead">${esc(pl(mem.length, 'member'))}${rules.share_value ? ` · one share = ${esc(m0(rules.share_value))}` : ''}${rules.rate_pct !== null && rules.rate_pct !== undefined ? ` · loans at ${esc(rules.rate_pct)}% a month` : ' · set the loan rate in Settings'}${rules.cycle_end ? ` · the cycle ends ${esc(dmy(rules.cycle_end))}` : ''}.</p></div>
      ${ro()}${err(gr)}
      ${ok_(gr) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('In the box', esc(m0(gr.cash_box)), gr.last_meeting ? 'after ' + dmy(gr.last_meeting) : 'no meeting yet')}${kpi('Lent out', esc(m0(gr.loans_outstanding)), 'interest due ' + m0(gr.interest_due))}${kpi('Social fund', esc(m0(gr.social_fund)))}${kpi('Books', gr.balanced ? 'Balance' : 'Do not balance', pl(gr.meetings_n, 'meeting'), gr.balanced ? '' : 'bad')}</section>` : ''}
      ${(ok_(gr) ? gr.count_mismatches : []).map(mm => `<p class="cs-neg" style="margin:0">At the meeting of ${esc(dmy(mm.meeting))} the box was counted at ${esc(m2(mm.counted))}; the book says ${esc(m2(mm.book))} (${esc(sgn(mm.difference))}). Count again with two members watching.</p>`).join('')}
      ${CAN() ? `<form class="card" data-form="meeting"><div class="cs-head"><h2 class="md-h2" style="margin:0">Record a meeting</h2><div class="r"><input class="in" type="date" name="date" required value="${esc(new Date().toISOString().slice(0, 10))}" aria-label="Meeting date" style="width:auto"></div></div>
        <div class="iv-tw"><table class="tb cm-meet"><thead><tr><th>Member</th><th>Saved (${esc(unit)})</th><th>Social fund</th><th>Fine</th><th>Repaid</th><th class="r">Owes now</th></tr></thead><tbody>${mem.map(m => `<tr><td><b>${esc(m.name)}</b></td>${['savings', 'social', 'fine', 'repay'].map(f => `<td><input class="in" name="m.${esc(m.name)}.${f}" inputmode="decimal" aria-label="${esc(m.name)} ${f}"></td>`).join('')}<td class="r">${ok_(gr) && gr.owes[m.name] ? `<span class="cs-neg">${esc(m0(gr.owes[m.name]))}</span>` : '<span class="mut">—</span>'}</td></tr>`).join('')}</tbody></table></div>
        <div class="mk-three" style="margin-top:12px">
          <label class="ins-lab">Loans given: name, amount, months<textarea class="in" name="loans" rows="3" placeholder="Chiku, 500, 1"></textarea></label>
          <label class="ins-lab">Expenses: what, amount<textarea class="in" name="expenses" rows="3" placeholder="notebook, 50"></textarea></label>
          <label class="ins-lab">Social fund paid out: name, amount<textarea class="in" name="social_payouts" rows="3" placeholder="Baraka, 200"></textarea></label></div>
        <div class="mk-three" style="margin-top:12px"><label class="ins-lab">Loan rate this meeting (% a month)<input class="in" name="rate_pct" inputmode="decimal" placeholder="${esc(rules.rate_pct ?? 'your group\'s rate')}"></label>
          <label class="ins-lab">Cash counted in the box at the end<input class="in" name="counted" inputmode="decimal" placeholder="optional"></label>
          <label class="ins-lab">Note<input class="in" name="note" maxlength="200" placeholder="optional"></label></div>
        <div class="md-acts"><span class="mut" style="font-size:13px">A meeting cannot lend more than the box holds - Hoola refuses it.</span><button class="btn" type="submit">Save the meeting</button></div></form>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">The box, meeting by meeting</h2>${box.length > 1 ? line(box, 'Cash in the box by meeting', m0) : empty('Two meetings draw the line.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Savings and loans</h2><div class="r">${ok_(gr) ? '<button class="btn soft sm" type="button" data-dl="group">CSV</button>' : ''}</div></div>
          ${ok_(gr) ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Member</th><th class="r">Saved</th><th class="r">Owes</th>${so && so.possible ? '<th class="r">Share-out</th>' : ''}<th></th></tr></thead><tbody>${mem.map(m => `<tr><td>${esc(m.name)}${m.phone ? ` <span class="mut">${esc(m.phone)}</span>` : ''}</td><td class="r">${esc(m0(gr.savings[m.name]))}</td><td class="r">${gr.owes[m.name] ? `<span class="cs-neg">${esc(m2(gr.owes[m.name]))}</span>` : '<span class="mut">—</span>'}</td>${so && so.possible ? `<td class="r"><b>${esc(m2(so.per_member[m.name]))}</b></td>` : ''}<td class="r">${ask('Savings group member ' + m.name)}${rmBtn('members', m.n)}</td></tr>`).join('')}</tbody></table></div>` : empty('')}
          ${CAN() ? `<details class="ins-more"><summary>Add a member</summary>${addForm('members', [['name', 'Name', '', ''], ['phone', 'Phone (optional)', '', '']], 'Add member')}</details>` : ''}</section></div>
      <section class="card cm-share"><div class="cs-head"><h2 class="md-h2" style="margin:0">The share-out</h2></div>
        ${so ? (so.possible ? `<p style="margin:0 0 10px">The box holds <b>${esc(m2(so.pot))}</b>: savings plus <b>${esc(m2(so.profit))}</b> earned, a return of <b>${esc(so.return_on_savings_pct)}%</b> on what members saved. Each member takes a share in proportion to their savings, rounded so every cent is paid out.</p>
            ${bars(Object.entries(so.per_member).sort((a, b) => b[1] - a[1]).map(([n, v]) => [n, v, 'cm-sv']), m2, 'Share-out by member')}
            ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">When the group has shared the money out, close the cycle: it is kept below and a new cycle starts (the social fund carries over).</span><button class="btn" type="button" data-close="1">Close the cycle</button></div>` : ''}`
          : `<p class="mut" style="margin:0">${esc(so.says)}</p>`) : empty('Record a meeting first.')}</section>
      ${(k.meetings || []).length ? `<section class="card"><h2 class="md-h2">Meetings this cycle</h2>${k.meetings.map(m => `<details class="cm-mt" data-key="mt${esc(m.n)}"${ST.open.has('mt' + m.n) ? ' open' : ''}><summary class="mk-sum">${esc(dmy(m.date))}<span class="mut" style="font-weight:400;font-size:13px">${esc(meetLine(m))}</span><span style="flex:1"></span>${rmBtn('meetings', m.n)}</summary>${meetBody(m)}</details>`).join('')}</section>` : ''}
      ${ok_(gr) && gr.cycles.length ? `<section class="card"><h2 class="md-h2">Earlier cycles</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Cycle</th><th class="r">Meetings</th><th class="r">Shared out</th><th class="r">Earned</th><th class="r">Return</th></tr></thead><tbody>${gr.cycles.map(c => `<tr><td>${esc(dmy(c.from))} – ${esc(dmy(c.to))}</td><td class="r">${esc(c.meetings)}</td><td class="r"><b>${esc(m2(c.pot))}</b></td><td class="r">${esc(m2(c.profit))}</td><td class="r">${esc(c.return_on_savings_pct)}%</td></tr>`).join('')}</tbody></table></div></section>` : ''}`;
  }
  const sumv = o => Object.values(o || {}).reduce((s, v) => s + Number(v || 0), 0);
  const meetLine = m => [sumv(m.savings) ? 'saved ' + num(sumv(m.savings)) : '', (m.loans || []).length ? pl(m.loans.length, 'loan') : '', (m.repayments || []).length ? pl(m.repayments.length, 'repayment') : '', m.counted !== undefined ? 'counted ' + m0(m.counted) : ''].filter(Boolean).join(' · ');
  const meetBody = m => {
    const rows = [];
    Object.entries(m.savings || {}).forEach(([n, v]) => rows.push([n, 'saved', v]));
    Object.entries(m.social_fund || {}).forEach(([n, v]) => rows.push([n, 'social fund', v]));
    Object.entries(m.fines || {}).forEach(([n, v]) => rows.push([n, 'fine', v]));
    (m.repayments || []).forEach(r => rows.push([r.member, 'repaid', r.amount]));
    (m.loans || []).forEach(r => rows.push([r.member, `borrowed at ${r.rate_pct}% for ${r.months} month${r.months == 1 ? '' : 's'}`, r.amount]));
    (m.expenses || []).forEach(r => rows.push([r.what, 'expense', r.amount]));
    (m.social_payouts || []).forEach(r => rows.push([r.member, 'social fund paid', r.amount]));
    return `<table class="tb"><tbody>${rows.map(r => `<tr><td>${esc(r[0])}</td><td class="mut">${esc(r[1])}</td><td class="r">${esc(num(r[2]))}</td></tr>`).join('')}</tbody></table>${m.note ? `<p class="mut" style="font-size:13px">${esc(m.note)}</p>` : ''}<p class="mut" style="font-size:12.5px">Recorded by ${esc(S(m.by).replace(/ <.*>$/, ''))} · ${esc(dt(m.on))}</p>`;
  };

  /* ---------------------------------------------------------------- rotating group */
  function pRosca() {
    const k = K(), r = k.rosca || {}, s = ((k.settings || {}).rosca) || {};
    const form = CAN() ? `<form class="card" data-form="rosca"><h2 class="md-h2">${r.empty ? 'Set up the rotating group' : 'The group\'s terms'}</h2>
        <div class="mk-two"><label class="ins-lab">Members, in the order they take the pot (one a line)<textarea class="in" name="members" rows="6" placeholder="Asha&#10;Bina&#10;Cyra">${esc((s.members || []).join('\n'))}</textarea></label>
        <div class="cm-col"><label class="ins-lab">Name<input class="in" name="name" maxlength="60" value="${esc(s.name || '')}" placeholder="Friday committee"></label>
          <label class="ins-lab">Each member pays each round<input class="in" name="contribution" inputmode="decimal" required value="${esc(s.contribution ?? '')}"></label>
          <div class="mk-two"><label class="ins-lab">How often<select class="in" name="frequency">${['weekly', 'fortnightly', 'monthly'].map(f => `<option value="${f}"${(s.frequency || 'monthly') === f ? ' selected' : ''}>${cap(f)}</option>`).join('')}</select></label>
          <label class="ins-lab">First payout<input class="in" type="date" name="start" value="${esc(s.start || '')}"></label></div></div></div>
        <div class="mk-three" style="margin-top:12px"><label class="ins-lab cm-check"><input type="checkbox" name="auction"${s.auction ? ' checked' : ''}> An auction chit (members bid a discount for the pot)</label>
          <label class="ins-lab">Organiser's fee, % of the pot (auction)<input class="in" name="organiser_fee_pct" inputmode="decimal" value="${esc(s.organiser_fee_pct ?? '')}"></label>
          <label class="ins-lab">A return promised on top<input class="in" name="promised_return_pct" inputmode="decimal" value="${esc(s.promised_return_pct ?? '')}" placeholder="leave blank if none"></label></div>
        <div class="mk-three" style="margin-top:12px">${[['written_record', 'Is it written down?'], ['organiser_known', 'Do members know the organiser?'], ['registered', 'Registered where the law asks? (chits)']].map(([n, l]) => `<label class="ins-lab">${l}<select class="in" name="${n}"><option value="">Not said</option><option value="true"${s[n] === true ? ' selected' : ''}>Yes</option><option value="false"${s[n] === false ? ' selected' : ''}>No</option></select></label>`).join('')}</div>
        <div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div></form>` : '';
    if (r.empty) return `<div><h1 class="sd-h">Rotating group</h1><p class="lead">A tanda, paluwagan, esusu, hui, committee or chit fund: everyone pays the same each round and one member takes the whole pot. In an auction chit members bid a discount; Hoola works out each round's dividend and the true cost of taking the pot early.</p></div>${ro()}${form}`;
    const list = r.rounds || r.schedule || [], n = list.length;
    return `<div><h1 class="sd-h">${esc(r.name || 'Rotating group')}</h1><p class="lead">${esc(pl(n, 'member'))} · ${esc(m0(r.contribution))} each ${esc(r.frequency === 'monthly' ? 'month' : r.frequency === 'weekly' ? 'week' : 'fortnight')} · a pot of ${esc(m0(r.contribution * n))}${r.auction ? ` · an auction chit, organiser's fee ${esc(r.fee_pct ?? 0)}%` : ''}.</p></div>
      ${ro()}${err(r)}
      ${(r.flags || []).map(f => `<p class="cs-neg" style="margin:0">Take care: ${esc(f)}.</p>`).join('')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">The rounds</h2><div class="r"><span class="mut" style="font-size:13px">${esc(r.paid_rounds)} of ${esc(n)} paid out</span></div></div>
        <div class="cm-prog"><i style="width:${n ? (r.paid_rounds / n * 100).toFixed(1) : 0}%"></i></div>
        <ol class="cm-rounds">${(r.auction ? (s.members || []) : list.map(x => x.takes_the_pot)).map((who, i) => {
          const done = i < r.paid_rounds, now = i === r.paid_rounds, rd = (r.rounds || [])[i], bid = (r.bids || [])[i];
          return `<li class="${done ? 'done' : now ? 'now' : ''}"><span class="b">${done ? tick : esc(i + 1)}</span><span class="w"><b>${esc(who)}</b><em>${r.dates ? esc(dmy(r.dates[i])) : 'round ' + esc(i + 1)}</em></span>
            <span class="x">${rd ? `receives <b>${esc(m0(rd.taker_receives))}</b> · bid ${esc(m0(rd.bid))} · each pays ${esc(m0(rd.each_pays_net))}` : bid !== undefined ? `bid ${esc(m0(bid))}` : r.auction ? '<span class="mut">bid not in yet</span>' : `receives <b>${esc(m0(r.each_receives))}</b>`}</span></li>`; }).join('')}</ol>
        ${CAN() ? `<form class="md-acts" data-form="round">${r.next ? `${r.auction ? `<label class="ins-lab cm-inl">${esc(r.next.takes)}'s winning bid<input class="in" name="bid" inputmode="decimal" required></label>` : `<span class="mut" style="font-size:13px">When ${esc(r.next.takes)} has received the pot, mark the round paid out.</span>`}<span style="display:flex;gap:8px">${r.paid_rounds ? '<button class="btn soft" type="button" data-undo="1">Undo last round</button>' : ''}<button class="btn" type="submit">Round ${esc(r.next.round)} paid out</button></span>` : `<span class="mut">Every member has taken the pot - the cycle is complete.</span>${r.paid_rounds ? '<button class="btn soft" type="button" data-undo="1">Undo last round</button>' : ''}`}</form>` : ''}</section>
      ${r.auction && r.complete ? `<section class="card"><h2 class="md-h2">Who gained and who paid</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Member</th><th class="r">Paid in</th><th class="r">Received</th><th class="r">Gain</th><th>Role</th><th class="r">Rate a round</th></tr></thead><tbody>${Object.entries(r.members || {}).map(([nm, x]) => `<tr><td>${esc(nm)}</td><td class="r">${esc(m0(x.paid))}</td><td class="r">${esc(m0(x.received))}</td><td class="r ${sign(x.gain)}">${esc(m0(x.gain))}</td><td class="mut">${esc(x.role)}</td><td class="r">${x.rate_per_round_pct === null ? '—' : esc(x.rate_per_round_pct) + '%'}</td></tr>`).join('')}</tbody></table></div>
        <p class="cs-note">${esc(r.says || '')} Organiser's fees over the cycle: ${esc(m0(r.organiser_fees))}.</p></section>`
        : r.auction ? `<p class="cs-note">The full cost of each member's turn shows once every round's bid is in (${esc(r.bids_in)} of ${esc(n)} so far).</p>`
        : `<p class="cs-note">${esc(r.says || '')} ${r.first_taker_pays_per_round_pct ? `The first to take the pot effectively borrows at ${esc(r.first_taker_pays_per_round_pct)}% a round from the others; the last saves.` : ''}</p>`}
      <details class="ins-more"><summary>Change the group's terms</summary>${form}</details>`;
  }

  /* ---------------------------------------------------------------- her loans */
  function pLoans() {
    const k = K(), lo = k.loans || {}, rp = lo.repayments || {}, o = ST.out.offer, rows = k.loan_rows || [];
    return `<div><h1 class="sd-h">Your loans</h1><p class="lead">What each loan really costs a year once fees and the repayment schedule are counted, and how much of your income the repayments take.</p></div>
      ${ro()}${err(lo)}
      ${ok_(lo) ? `<div class="md-2" style="align-items:start"><section class="card"><h2 class="md-h2">Repayments against your income</h2>
          ${rp.share_of_income_pct !== null && rp.share_of_income_pct !== undefined ? gauge(rp.share_of_income_pct, lo.limit_set ? rp.limit_pct : null) : empty('Add your income a month in Settings to see what share the repayments take.')}
          <div class="cs-row"><span style="flex:1">Repayments a month (all loans)</span><b>${esc(m2(rp.per_month))}</b></div><div class="cs-row"><span style="flex:1">Lenders</span><b>${esc(rp.lenders)}</b></div>
          ${rp.flag ? `<p class="cs-neg" style="margin:8px 0 0">${esc(rp.flag)}</p>` : ''}${!lo.limit_set ? '<p class="cs-note">Set your own limit (a percent of income) in Settings.</p>' : ''}</section>
        <section class="card"><h2 class="md-h2">The dearest loan</h2>${lo.dearest ? `<div class="cm-big">${esc(lo.dearest.cost.effective_yearly_pct)}%<span>a year, all costs in</span></div><div class="cs-row"><span style="flex:1">${esc(lo.dearest.lender)}</span><span class="mut">you got ${esc(m0(lo.dearest.cost.you_receive))}, you repay ${esc(m0(lo.dearest.cost.you_repay))}</span></div>` : empty('Give a loan\'s amount and number of installments to see its true cost.')}</section></div>` : ''}
      <section class="card"><h2 class="md-h2">Each loan</h2>
        ${rows.length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Lender</th><th class="r">Installment</th><th>How often</th><th class="r">Borrowed</th><th class="r">You repay</th><th class="r">Cost a year</th><th></th></tr></thead><tbody>${(lo.loans || rows).map(x => `<tr><td><b>${esc(x.lender)}</b></td><td class="r">${esc(m0(x.installment))}</td><td>${esc(cap(x.frequency || 'monthly'))}</td><td class="r">${x.amount ? esc(m0(x.amount)) : '—'}</td><td class="r">${x.cost ? esc(m0(x.cost.you_repay)) : '—'}</td><td class="r">${x.cost ? `<b class="${x.cost.effective_yearly_pct > 36 ? 'cs-neg' : ''}">${esc(x.cost.effective_yearly_pct)}%</b>` : x.cost_error ? `<span class="cs-neg">${esc(x.cost_error)}</span>` : '<span class="mut">give amount + installments</span>'}</td><td class="r">${ask('My loan from ' + x.lender)}${rmBtn('loans', x.n)}</td></tr>`).join('')}</tbody></table></div>` : empty('No loans on the desk.')}
        ${CAN() ? addForm('loans', [['lender', 'Lender', '', 'MFI One'], ['installment', 'Installment', 'num'], ['frequency', 'How often', 'freq'], ['amount', 'Amount borrowed', 'num'], ['installments', 'Number of installments', 'num'], ['upfront_fees', 'Fees taken at the start', 'num']], 'Add loan') : ''}</section>
      <form class="card" data-form="offer"><h2 class="md-h2">Check an offer before you sign</h2>
        <div class="cm-grid5">${[['amount', 'Amount offered'], ['installment', 'Each installment'], ['installments', 'Number of installments']].map(([n, l]) => `<label class="ins-lab">${l}<input class="in" name="${n}" inputmode="decimal" required></label>`).join('')}
          <label class="ins-lab">How often<select class="in" name="frequency"><option value="weekly">Weekly</option><option value="fortnightly">Fortnightly</option><option value="monthly">Monthly</option></select></label>
          <label class="ins-lab">Fees at the start<input class="in" name="upfront_fees" inputmode="decimal" placeholder="0"></label></div>
        <div class="md-acts"><span></span><button class="btn" type="submit">Work out the true cost</button></div>
        ${o ? (o.error ? err(o) : `<div class="cm-res"><div class="cm-big">${esc(o.loan.effective_yearly_pct)}%<span>a year, all costs in</span></div><div class="cm-rgrid"><div><span>You receive</span><b>${esc(m2(o.loan.you_receive))}</b></div><div><span>You repay</span><b>${esc(m2(o.loan.you_repay))}</b></div><div><span>It costs you</span><b class="cs-neg">${esc(m2(o.loan.cost))}</b></div><div><span>Per period</span><b>${esc(o.loan.rate_per_period_pct)}%</b></div></div></div>`) : ''}</form>`;
  }

  /* ---------------------------------------------------------------- field collections */
  function pField() {
    const k = K(), f = k.field || {};
    return `<div><h1 class="sd-h">Collections</h1><p class="lead">For a microfinance field officer or a group's loan book: today's collection sheet (due against paid) and the loan book (balance and days late) - the collection rate, who paid short and the portfolio at risk over 30 days.</p></div>
      ${ro()}${err(f)}
      ${ok_(f) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Due', esc(m0(f.due)))}${kpi('Collected', esc(m0(f.collected)), f.collection_rate_pct === null ? '' : f.collection_rate_pct + '% of what was due', f.collection_rate_pct !== null && f.collection_rate_pct < 95 ? 'warn' : '')}${kpi('Loan book', esc(m0(f.portfolio)))}${kpi('At risk over 30 days', f.par30_pct === null ? '—' : esc(f.par30_pct) + '%', f.par_limit !== null && f.par_limit !== undefined ? 'your limit ' + f.par_limit + '%' : 'set your limit in Settings', f.par30_pct && f.par_limit !== null && f.par_limit !== undefined && f.par30_pct > f.par_limit ? 'bad' : '')}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Paid short today</h2><div class="r">${ok_(f) ? '<button class="btn soft sm" type="button" data-dl="arrears">CSV</button>' : ''}</div></div>
          ${ok_(f) && f.arrears.length ? `<div class="iv-tw"><table class="tb"><tbody>${f.arrears.map(x => `<tr><td>${esc(x.member)}</td><td class="r cs-neg">${esc(m2(x.short))}</td><td class="r">${ask('Collection: ' + x.member + ' paid short')}</td></tr>`).join('')}</tbody></table></div>` : empty(ok_(f) ? 'Everyone paid what was due.' : 'Add today\'s collection sheet.')}
          ${uploader('collections', 'Today\'s collection sheet (CSV)', 'Columns: member, due, paid. A new sheet replaces the old one.')}
          ${CAN() ? `<details class="ins-more"><summary>Add one line</summary>${addForm('collections', [['member', 'Member', '', ''], ['due', 'Due', 'num'], ['paid', 'Paid', 'num']])}</details>` : ''}</section>
        <section class="card"><h2 class="md-h2">The loan book by lateness</h2>
          ${ok_(f) && f.portfolio ? bars(Object.entries(f.by_age).map(([n, v], i) => [cap(n), v, 'mk-age' + Math.max(0, i - 1) + (i === 0 ? ' cm-ok' : '')]), m0, 'Loan book by days late') : empty('Add the loan book.')}
          ${uploader('portfolio', 'The loan book (CSV)', 'Columns: member, outstanding balance, days late.')}
          ${CAN() ? `<details class="ins-more"><summary>Add one loan</summary>${addForm('portfolio', [['member', 'Member', '', ''], ['outstanding', 'Outstanding', 'num'], ['days_late', 'Days late', 'num']])}</details>` : ''}</section></div>
      ${ok_(f) && f.late.length ? `<section class="card"><h2 class="md-h2">Late loans</h2>${listRows('portfolio', f.late, [['member', 'Member'], ['outstanding', 'Outstanding', 1, v => esc(m0(v))], ['days_late', 'Days late', 1, v => `<b class="${v > 30 ? 'cs-neg' : ''}">${esc(v)}</b>`]], 100)}<p class="cs-note">Visit or call each member yourself; Hoola contacts nobody.</p></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- farm */
  function pFarm() {
    const k = K(), c = (k.crops || {}).crops || [], ed = ST.out.editCrop;
    const e = ed ? c.find(x => x.n === ed) || {} : {};
    return `<div><h1 class="sd-h">Farm</h1><p class="lead">A crop plan - your costs, the yield and your price give the margin and the price you need to break even - and a crop-insurance claim worked out from your scheme's threshold and actual yields.</p></div>
      ${ro()}
      ${c.map(x => { const p = (x.result || {}).plan, cl = (x.result || {}).claim, u = x.unit || 'unit';
        return `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${esc(x.name)}${x.season ? ` <span class="mut" style="font-weight:400">${esc(x.season)}</span>` : ''}</h2><div class="r">${ask('Crop ' + x.name)}${CAN() ? `<button class="btn soft sm" type="button" data-edit="${esc(x.n)}">Change</button>` : ''}${rmBtn('crops', x.n)}</div></div>
          ${x.error ? `<p class="cs-neg">${esc(x.error)}</p>` : ''}
          ${p ? `<div class="cm-rgrid"><div><span>Costs</span><b>${esc(m0(p.cost))}</b></div><div><span>Harvest</span><b>${esc(num(p.harvest))} ${esc(u)}</b></div><div><span>Income at your price</span><b>${esc(m0(p.income))}</b></div><div><span>Margin</span><b class="${sign(p.margin)}">${esc(m0(p.margin))}</b></div></div>
            ${p.break_even_price !== null ? `<div class="mk-range"><div class="h"><b>Break-even price</b><span class="mut">${esc(m2(p.break_even_price))} a ${esc(u)} · your price ${esc(m2(x.price))}</span></div><div class="bar"><i style="left:0;right:0"></i><u style="left:${Math.min(100, p.break_even_price / Math.max(x.price, p.break_even_price) * 100).toFixed(1)}%"></u></div><div class="ft"><span>0</span><span>${p.margin >= 0 ? 'your price is above break-even' : 'your price is below break-even'}</span><span>${esc(m2(Math.max(x.price, p.break_even_price)))}</span></div></div>` : ''}
            ${(x.costs || []).length ? bars(x.costs.map(cc => [cap(cc.what), cc.amount, 'cm-out']), m0, 'Costs') : ''}` : ''}
          ${cl ? `<div class="cm-claim"><div class="h"><b>Insurance claim: ${esc(m2(cl.claim))}</b><span class="mut">shortfall ${esc(cl.shortfall_pct)}%</span></div><p class="mut" style="font-size:13px;margin:4px 0 6px">${esc(cl.formula)}</p><div class="mut" style="font-size:13px">Keep: ${esc(cl.keep.join(', '))}.</div></div>` : ''}</section>`; }).join('')}
      ${CAN() ? `<form class="card" data-form="crop">${ed ? `<input type="hidden" name="n" value="${esc(ed)}">` : ''}<h2 class="md-h2">${ed ? 'Change ' + esc(e.name) : 'Add a crop'}</h2>
        <div class="cm-grid5"><label class="ins-lab">Crop and season<input class="in" name="name" required maxlength="60" value="${esc(e.name || '')}" placeholder="Maize, long rains 2026"></label>
          <label class="ins-lab">Unit of yield<input class="in" name="unit" maxlength="20" value="${esc(e.unit || '')}" placeholder="kg"></label>
          <label class="ins-lab">Area (acres, hectares)<input class="in" name="area" inputmode="decimal" value="${esc(e.area ?? '')}"></label>
          <label class="ins-lab">Yield per area<input class="in" name="yield_per_unit" inputmode="decimal" value="${esc(e.yield_per_unit ?? '')}"></label>
          <label class="ins-lab">Your price per unit<input class="in" name="price" inputmode="decimal" value="${esc(e.price ?? '')}"></label></div>
        <label class="ins-lab" style="margin-top:12px">Costs: what, amount (one a line)<textarea class="in" name="costs" rows="3" placeholder="seed, 8000&#10;fertiliser, 12000&#10;labour, 6000">${esc((e.costs || []).map(cc => cc.what + ', ' + cc.amount).join('\n'))}</textarea></label>
        <div class="cr-sub" style="margin-top:12px">A crop-insurance claim (from your scheme's terms)</div>
        <div class="mk-three"><label class="ins-lab">Threshold yield<input class="in" name="threshold_yield" inputmode="decimal" value="${esc(e.threshold_yield ?? '')}"></label>
          <label class="ins-lab">Actual yield<input class="in" name="actual_yield" inputmode="decimal" value="${esc(e.actual_yield ?? '')}"></label>
          <label class="ins-lab">Sum insured<input class="in" name="sum_insured" inputmode="decimal" value="${esc(e.sum_insured ?? '')}"></label></div>
        <div class="md-acts"><span>${ed ? '<button class="btn soft" type="button" data-edit="0">Cancel</button>' : ''}</span><button class="btn" type="submit">${ed ? 'Save the changes' : 'Work it out'}</button></div></form>` : ''}`;
  }

  /* ---------------------------------------------------------------- send money + mobile money */
  function pSend() {
    const k = K(), rm = k.remit || {}, cfg = rm.remit || ((k.settings || {}).remit) || {}, o = ST.out.mm;
    const ps = ok_(rm) ? rm.providers : [];
    return `<div><h1 class="sd-h">Send money</h1><p class="lead">What arrives at home with each provider at today's rates: the fee plus what the exchange rate takes, against the mid-market rate. Type the rates each provider quotes you today - Hoola never sends the money.</p></div>
      ${ro()}${err(rm)}
      ${CAN() ? `<form class="card" data-form="remit"><h2 class="md-h2">What you send today</h2><div class="mk-three">
        <label class="ins-lab">Amount you send (${esc(cur())})<input class="in" name="send" inputmode="decimal" required value="${esc(cfg.send ?? '')}"></label>
        <label class="ins-lab">Today's mid-market rate<input class="in" name="mid_rate" inputmode="decimal" required value="${esc(cfg.mid_rate ?? '')}" placeholder="from a currency site"></label>
        <label class="ins-lab">Currency at home<input class="in" name="to_currency" maxlength="3" value="${esc(cfg.to_currency || '')}" placeholder="INR"></label></div>
        <div class="md-acts"><span class="mut" style="font-size:13px">${cfg.on ? 'Rates from ' + esc(dmy(cfg.on)) : ''}</span><button class="btn" type="submit">Compare</button></div></form>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What arrives</h2>
          ${ps.length ? `${bars(ps.map((p, i) => [p.provider, p.arrives, i ? 'cm-out' : 'cm-sv', 'costs ' + (p.true_cost_pct ?? '—') + '%']), v => num(Math.round(v * 100) / 100) + (cfg.to_currency ? ' ' + cfg.to_currency : ''), 'What arrives with each provider')}
            <p class="cs-note">${esc(rm.most_arrives_with)} gets the most home${rm.gap ? ` - ${esc(num(rm.gap))} ${esc(cfg.to_currency || '')} more than the dearest` : ''}. At the mid-market rate with no fee, ${esc(num(rm.ideal))} ${esc(cfg.to_currency || '')} would arrive.</p>` : empty(rm.have_providers ? 'Give the amount and today\'s mid-market rate above.' : 'Add the providers you could use, with the fee and rate each quotes today.')}</section>
        <section class="card"><h2 class="md-h2">Providers</h2>
          ${listRows('providers', k.providers || [], [['name', 'Provider'], ['fee', 'Fee', 1, v => v ? esc(m2(v)) : '—'], ['fee_pct', 'Fee %', 1, v => v ? esc(v) + '%' : '—'], ['rate', 'Rate', 1, v => esc(num(v))]], 40)}
          ${addForm('providers', [['name', 'Provider', '', 'Bank A'], ['fee', 'Fee', 'num'], ['fee_pct', 'Fee %', 'num'], ['rate', 'Rate they give', 'num']], 'Add')}</section></div>
      <section class="card"><h2 class="md-h2">Mobile money${(k.settings || {}).mm_provider ? ' · ' + esc(k.settings.mm_provider) : ''}</h2>
        <div class="md-2" style="align-items:start"><div><div class="cr-sub">Your provider's fee bands</div>${listRows('tariff', k.tariff || [], [['min', 'From', 1, v => esc(m0(v))], ['max', 'To', 1, v => esc(m0(v))], ['fee', 'Fee', 1, v => esc(m2(v))]], 40)}
          ${addForm('tariff', [['min', 'From', 'num'], ['max', 'To', 'num'], ['fee', 'Fee', 'num']], 'Add band')}${uploader('tariff', 'The fee table (CSV)', 'Columns: from, to, fee.')}</div>
        <form data-form="mm"><div class="cr-sub">Check a transfer or a message</div>
          <label class="ins-lab">Amount to send<input class="in" name="amount" inputmode="decimal"></label>
          <label class="ins-lab" style="margin-top:10px">A message you received (Hoola looks for the signs of a scam)<textarea class="in" name="message" rows="4" placeholder="You have received 5000 by mistake, please send it back…"></textarea></label>
          <div class="md-acts"><span></span><button class="btn" type="submit">Check</button></div>
          ${o ? (o.error ? err(o) : `${o.fee ? `<div class="cs-row"><span style="flex:1">The fee on ${esc(m0(o.fee.amount))}</span><b>${esc(m2(o.fee.fee))}</b><span class="mut">${esc(o.fee.fee_pct)}%</span></div>` : ''}${o.scam_signs ? (o.scam_signs.length ? `<div class="cm-warn"><b>Signs of a scam</b>${o.scam_signs.map(x => `<div>${esc(x)}</div>`).join('')}<div class="mut" style="margin-top:6px">Never share your PIN. Call your provider on the number on their own website - never the number in the message.</div></div>` : '<p class="cs-pos" style="margin:8px 0 0">No sign of the usual scams in this message - still check with your provider before you send anything.</p>') : ''}`) : ''}</form></div></section>`;
  }

  /* ---------------------------------------------------------------- zakat + Islamic */
  function pZakat() {
    const k = K(), z = (k.settings || {}).zakat || {}, o = ST.out.zakat, is = ST.out.islamic;
    const f = (n, l, ph) => `<label class="ins-lab">${l}<input class="in" name="${n}" inputmode="decimal" value="${esc(z[n] ?? '')}" placeholder="${esc(ph || '')}"></label>`;
    const sel = (n, l, opts) => `<label class="ins-lab">${l}<select class="in" name="${n}">${opts.map(([v, t]) => `<option value="${v}"${S(z[n]) === v ? ' selected' : ''}>${t}</option>`).join('')}</select></label>`;
    const ms = is && !is.error && is.schedule ? is.schedule.map(r => [S(r.period), r.your_share_pct]) : [];
    return `<div><h1 class="sd-h">Zakat &amp; Islamic finance</h1><p class="lead">Zakat worked out the usual way at your prices: what you hold, less debts due now, against the nisab on gold or silver, at 2.5% once a lunar year has passed. Where the schools differ (jewellery, long-term shares) you choose. The ruling for your case stays with your scholar.</p></div>
      ${ro()}
      <form class="card" data-form="zakat"><h2 class="md-h2">Your zakat</h2>
        <div class="cm-grid5">${sel('nisab_basis', 'Nisab on', [['gold', 'Gold (85 g)'], ['silver', 'Silver (595 g)']])}${f('gold_price_per_gram', 'Gold price a gram (24k, today)')}${f('silver_price_per_gram', 'Silver price a gram (today)')}${sel('school', 'Your school', [['', 'Not said'], ['hanafi', 'Hanafi'], ['shafii', 'Shafi\'i'], ['maliki', 'Maliki'], ['hanbali', 'Hanbali']])}${sel('lunar_year_passed', 'A lunar year has passed?', [['', 'Not said'], ['yes', 'Yes'], ['no', 'No']])}</div>
        <div class="cm-grid5" style="margin-top:12px">${f('cash', 'Cash')}${f('bank', 'In the bank')}${f('business_stock', 'Trade stock (sale value)')}${f('receivables', 'Owed to you, expected back')}${f('shares_trading', 'Shares held to trade')}</div>
        <div class="cm-grid5" style="margin-top:12px">${f('shares_longterm', 'Long-term shares')}${f('shares_longterm_pct', '% of them counted', 'your scholar\'s view')}${f('silver_grams', 'Silver (grams)')}${f('debts_due', 'Debts due now')}<label class="ins-lab">Your zakat date<input class="in" type="date" name="hawl" value="${esc(z.hawl || '')}"></label></div>
        <label class="ins-lab" style="margin-top:12px">Gold: grams, karat, jewellery (one piece or lot a line)<textarea class="in" name="gold" rows="2" placeholder="20, 22, jewellery&#10;10, 24">${esc(z.gold || '')}</textarea></label>
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">Your values are kept for next year.</span><button class="btn" type="submit">Work out the zakat</button></div>' : ''}
        ${o ? (o.error ? err(o) : `<div class="cm-res"><div class="cm-big">${esc(m2(o.zakat))}<span>${o.zakat ? 'zakat due' : o.above_nisab ? 'nothing due yet' : 'below the nisab - no zakat'}</span></div>
          <div class="cm-nisab"><div class="bar"><i class="${o.above_nisab ? 'ok' : ''}" style="width:${Math.min(100, o.net / Math.max(o.net, o.nisab * 1.4, 1) * 100).toFixed(1)}%"></i><u style="left:${Math.min(100, o.nisab / Math.max(o.net, o.nisab * 1.4, 1) * 100).toFixed(1)}%" title="nisab"></u></div><div class="ft"><span>your net ${esc(m0(o.net))}</span><span>nisab ${esc(m0(o.nisab))}</span></div></div>
          ${bars(o.assets.map(x => [cap(x.what), x.value, 'cm-sv']), m0, 'What counts')}
          <p class="cs-note">${esc(o.nisab_from)}. Jewellery ${esc(o.jewellery)}. Debts due ${esc(m0(o.debts_due))}.${o.note ? ' ' + esc(o.note) : ''} ${esc(o.says)}</p></div>`) : ''}</form>
      ${(k.zakat_log || []).length ? `<section class="card"><h2 class="md-h2">Earlier results</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Worked out</th><th class="r">Net</th><th class="r">Nisab</th><th class="r">Zakat</th></tr></thead><tbody>${k.zakat_log.map(x => `<tr><td>${esc(dmy(x.on))}</td><td class="r">${esc(m0(x.net))}</td><td class="r">${esc(m0(x.nisab))}</td><td class="r"><b>${esc(m2(x.zakat))}</b></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <form class="card cm-isform" data-form="islamic"><h2 class="md-h2">An Islamic structure, worked out</h2>
        <div class="cm-grid5"><label class="ins-lab">Structure<select class="in" name="structure"><option value="murabaha">Murabaha (cost-plus sale)</option><option value="ijara">Ijara (lease)</option><option value="diminishing_musharaka">Diminishing musharaka (home)</option><option value="mudaraba">Mudaraba (profit share)</option></select></label>
          <label class="ins-lab">A name<input class="in" name="label" maxlength="60" placeholder="Shop van"></label>
          <label class="ins-lab cm-s cm-mu cm-ij">Cost of the asset<input class="in" name="cost" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-mu">Agreed markup %<input class="in" name="markup_pct" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-mu">Installments<input class="in" name="installments" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-ij">Rent a period<input class="in" name="rent" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-ij">Periods<input class="in" name="periods" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-dm">Price<input class="in" name="price" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-dm">Your own part<input class="in" name="own_contribution" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-dm">Rent % a period (on their share)<input class="in" name="rent_pct_per_period" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-dm">You buy back a period<input class="in" name="buyback_per_period" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-md">Profit (a loss as minus)<input class="in" name="profit" inputmode="decimal"></label>
          <label class="ins-lab cm-s cm-md">Manager's share %<input class="in" name="manager_share_pct" inputmode="decimal"></label></div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Whether a contract is compliant is for your Shariah board, not Hoola.</span><button class="btn" type="submit">Work it out</button></div>
        ${is ? (is.error ? err(is) : `<div class="cm-res">${islamicOut(is)}${ms.length > 1 ? line(ms.length > 60 ? ms.filter((_, i) => i % Math.ceil(ms.length / 60) === 0 || i === ms.length - 1) : ms, 'Your share of the home', v => num(v) + '%', '', true) : ''}<p class="cs-note">${esc(cap(is.order || is.says || ''))}${is.order || is.says ? '. ' : ''}${esc(is.board)}</p></div>`) : ''}</form>
      ${(k.islamic_log || []).length ? `<section class="card"><h2 class="md-h2">Worked out before</h2>${k.islamic_log.map(x => `<div class="cs-row"><span style="flex:1"><b>${esc(cap(S(x.structure).replace('_', ' ')))}</b>${x.label ? ' · ' + esc(x.label) : ''} <span class="mut">${esc(x.headline)}</span></span><span class="mut nw">${esc(dt(x.on))}</span>${rmBtn('islamic', x.n)}</div>`).join('')}</section>` : ''}`;
  }
  function islamicOut(r) {
    const g = (l, v, c) => `<div><span>${esc(l)}</span><b class="${c || ''}">${esc(v)}</b></div>`;
    if (r.structure === 'murabaha') return `<div class="cm-rgrid">${g('Sale price', m2(r.sale_price))}${g('Profit to the seller', m2(r.profit))}${g('Each installment', m2(r.installment))}</div><p class="cs-note">${esc(r.late_payment)}.</p>`;
    if (r.structure === 'ijara') return `<div class="cm-rgrid">${g('Total rent', m2(r.total_rent))}${g('Over the cost', m2(r.over_cost))}</div>`;
    if (r.structure === 'diminishing_musharaka') return `<div class="cm-rgrid">${g('Periods to own it all', num(r.periods))}${g('Total rent', m2(r.total_rent))}</div>`;
    return `<div class="cm-rgrid">${g('To the manager', m2(r.manager))}${g('To the capital provider', m2(r.capital_provider), sign(r.capital_provider))}</div>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, g = s.group || {}, w = W();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your group's rules, your income and limits, your provider. Hoola brings none of its own: every rate and fee here is yours or your group's.</p></div>
      ${ro()}
      <form class="card" data-form="grules"><h2 class="md-h2">The savings group's rules</h2><div class="md-form">
        <div class="md-field"><label for="cmG1">Group name</label><input class="in" id="cmG1" name="name" maxlength="60" value="${esc(g.name || '')}"></div>
        <div class="md-field"><label for="cmG2">One share is worth (blank if you save amounts)</label><input class="in" id="cmG2" name="share_value" inputmode="decimal" value="${esc(g.share_value ?? '')}"></div>
        <div class="md-field"><label for="cmG3">Loan rate, % a month (the group's own)</label><input class="in" id="cmG3" name="rate_pct" inputmode="decimal" value="${esc(g.rate_pct ?? '')}"></div>
        <div class="md-field"><label for="cmG4">The cycle ends</label><input class="in" id="cmG4" type="date" name="cycle_end" value="${esc(g.cycle_end || '')}"></div>
        <div class="md-field"><label for="cmG5">Cash in the box at the start</label><input class="in" id="cmG5" name="opening_cash" inputmode="decimal" value="${esc(g.opening_cash ?? '')}"></div>
        <div class="md-field"><label for="cmG6">Social fund at the start</label><input class="in" id="cmG6" name="opening_social" inputmode="decimal" value="${esc(g.opening_social ?? '')}"></div></div>
        ${k.style ? `<p class="cs-note">In ${esc(k.country)}: ${esc(k.style)}.</p>` : ''}
        ${CAN() ? '<div class="md-acts"><span class="mut" style="font-size:13px">The share value and the opening balances are fixed once the cycle has meetings.</span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <form class="card" data-form="settings"><h2 class="md-h2">You and your limits</h2><div class="md-form">
        <div class="md-field"><label for="cmT1">Cash book opening balance</label><input class="in" id="cmT1" name="cash_opening" inputmode="decimal" value="${esc(s.cash_opening ?? '')}"></div>
        <div class="md-field"><label for="cmT2">Your income a month</label><input class="in" id="cmT2" name="income_monthly" inputmode="decimal" value="${esc(s.income_monthly ?? '')}"></div>
        <div class="md-field"><label for="cmT3">Your limit for repayments, % of income</label><input class="in" id="cmT3" name="max_share_pct" inputmode="decimal" value="${esc(s.max_share_pct ?? '')}" placeholder="yours"></div>
        <div class="md-field"><label for="cmT4">Portfolio-at-risk limit, % (field team)</label><input class="in" id="cmT4" name="par_limit" inputmode="decimal" value="${esc(s.par_limit ?? '')}"></div>
        <div class="md-field"><label for="cmT5">Your mobile-money provider</label><input class="in" id="cmT5" name="mm_provider" maxlength="40" value="${esc(s.mm_provider || '')}"></div>
        <div class="md-field"><label for="cmT6">Your zakat date</label><input class="in" id="cmT6" type="date" name="zakat_hawl" value="${esc((s.zakat || {}).hawl || '')}"></div></div>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({cash: 'cash-book lines', portfolio: 'loans in the book', collections: 'collection lines', tariff: 'fee bands', zakat_log: 'zakat results', islamic: 'Islamic structures', cycles: 'closed cycles'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind)} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('cmN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/community/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
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
    const edt = t.closest('[data-edit]'); if (edt) { ST.out.editCrop = Number(edt.dataset.edit) || 0; showPage(true); if (ST.out.editCrop) $('#cmPage form[data-form=crop]').scrollIntoView({behavior: 'smooth', block: 'start'}); return; }
    try {
      const rm = t.closest('[data-rm]'); if (rm) { e.preventDefault(); await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
      const cl = t.closest('[data-close]'); if (cl) { if (!confirm('Has the group shared the money out? Close the cycle and start a new one.')) return; await run('close_cycle', {}); await changed('The cycle is closed and kept below.'); return; }
      const un = t.closest('[data-undo]'); if (un) { await run('rosca_round', {undo: true}); await changed('The last round is open again.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 8e6) { toast('Up to 8 MB.', true); return; }
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
    const keepOut = async (key, part, a, msg) => { try { ST.out[key] = await run(part, a); await changed(msg || ''); } catch (err2) { ST.out[key] = {error: err2.message}; showPage(true); } };
    if (btn) btn.disabled = true;
    try {
      if (kind === 'setup') { await api('POST', '/api/community/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'cash') { try { ST.out.cash = await run('cash_lines', {text: g('text'), date: g('date')}); toast(ST.out.cash.says + '.'); if (!ST.out.cash.could_not_read.length) sent(); else form.querySelector('[name=text]').value = ST.out.cash.could_not_read.join('\n'); await refreshDesk(false); showPage(true); }
        catch (err2) { ST.out.cash = {error: err2.message}; showPage(true); } }
      else if (kind === 'meeting') {
        const members = {};
        for (const [n, v] of fd.entries()) { const m = n.match(/^m\.(.+)\.(savings|social|fine|repay)$/); if (m && S(v).trim() !== '') (members[m[1]] = members[m[1]] || {})[m[2]] = S(v).trim(); }
        await run('meeting', {date: g('date'), members, loans: g('loans'), expenses: g('expenses'), social_payouts: g('social_payouts'), rate_pct: g('rate_pct'), counted: g('counted'), note: g('note')});
        await done('The meeting is saved.'); }
      else if (kind === 'rosca') { await run('rosca_save', {...pick(['name', 'members', 'contribution', 'frequency', 'start', 'organiser_fee_pct', 'promised_return_pct']), members: g('members'), start: g('start'),
          auction: fd.get('auction') === 'on', written_record: g('written_record'), organiser_known: g('organiser_known'), registered: g('registered'), promised_return_pct: g('promised_return_pct')}); await changed('Saved.'); }
      else if (kind === 'round') { await run('rosca_round', pick(['bid'])); await done('Round recorded.'); }
      else if (kind === 'offer') { await keepOut('offer', 'loan_check', pick(['amount', 'installment', 'installments', 'frequency', 'upfront_fees'])); }
      else if (kind === 'crop') { await run('crop', {...pick(['n', 'name', 'unit', 'area', 'yield_per_unit', 'price', 'threshold_yield', 'actual_yield', 'sum_insured']), costs: g('costs')}); ST.out.editCrop = 0; await done('Worked out.'); }
      else if (kind === 'remit') { await run('remit_save', pick(['send', 'mid_rate', 'to_currency'])); await changed('Compared.'); }
      else if (kind === 'mm') { await keepOut('mm', 'mm_fee', pick(['amount', 'message'])); }
      else if (kind === 'zakat') { await keepOut('zakat', 'zakat', pick(['nisab_basis', 'gold_price_per_gram', 'silver_price_per_gram', 'cash', 'bank', 'silver_grams', 'school', 'business_stock', 'receivables', 'shares_trading', 'shares_longterm', 'shares_longterm_pct', 'debts_due', 'gold', 'lunar_year_passed', 'hawl'])); }
      else if (kind === 'islamic') { await keepOut('islamic', 'islamic', pick(['structure', 'label', 'cost', 'markup_pct', 'installments', 'rent', 'periods', 'price', 'own_contribution', 'rent_pct_per_period', 'buyback_per_period', 'profit', 'manager_share_pct'])); }
      else if (kind === 'grules') { await run('settings', {group: {name: g('name'), share_value: g('share_value'), rate_pct: g('rate_pct'), cycle_end: g('cycle_end'), opening_cash: g('opening_cash'), opening_social: g('opening_social')}}); await changed('The group\'s rules are saved.'); }
      else if (kind === 'settings') { await run('settings', {cash_opening: g('cash_opening'), income_monthly: g('income_monthly'), max_share_pct: g('max_share_pct'), par_limit: g('par_limit'), mm_provider: g('mm_provider'), zakat_hawl: g('zakat_hawl')}); await changed('Saved.'); }
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
    const box = $('#cmFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/community/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'cm' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


