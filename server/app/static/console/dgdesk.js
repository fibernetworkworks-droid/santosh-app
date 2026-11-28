/* DIGITAL ASSETS DESK - the Digital Assets employee's own section, like the other finance desks (owner: "NOW LETS WORK ON NEXT EMPLOYEE
   DIGITAL ASSETS DESK"). A thin top bar, then the Digital Assets chat (its own conversation, kind 'digital') beside the desk's pages:
   Today, Gains, Wallets & safety, Stablecoin pay, Token checks, Reserve, Custody, Transfers, Surveillance, Settings. The pages call
   /api/digital/do/<part>, which runs the F11 engine on her desk. Hoola never holds a key, signs or sends anything. Routes: #/<page>. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', dg: '<path d="M12 3l7.5 4.3v9.4L12 21l-7.5-4.3V7.3z"/><path d="M12 3v18M4.5 7.3L12 11.6l7.5-4.3"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['gains', 'Gains'], ['wallets', 'Wallets & safety'], ['pay', 'Stablecoin pay'], ['tokens', 'Token checks'],
    ['reserve', 'Reserve'], ['custody', 'Custody'], ['transfers', 'Transfers'], ['watch', 'Surveillance'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What needs me first?', 'What do I owe tax on this year?', 'What do I hold?'],
    gains: ['Explain how my gains were matched', 'Which sale made the biggest gain?', 'Is a swap taxed?'],
    wallets: ['Is this address safe to send to?', 'What is address poisoning?', 'I think I shared my seed phrase'],
    pay: ['How many coins should I ask for?', 'What if the coin loses its peg?', 'How do I record a stablecoin payment?'],
    tokens: ['Is this token a rug pull?', 'Explain mint authority', 'What makes a token risky?'],
    reserve: ['Why is the reserve short?', 'What assets are usually eligible?', 'Draft the reserve note'],
    custody: ['Why is BTC short?', 'What should I do about a shortfall?', 'Draft the incident note'],
    transfers: ['Which transfers must I hold?', 'What does the travel rule ask for?', 'Explain the return counts'],
    watch: ['Explain this alert', 'Is a round trip always abuse?', 'Draft a note for the compliance officer'],
    settings: ['Which tax method applies to me?', 'When does my tax year start?', 'What is the travel-rule threshold?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.digital.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.digital.folded') === '1'; } catch {}

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
  const run = (part, a) => api('POST', '/api/digital/do/' + part, {workspace: W().id, ...(a || {})});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/digital/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.dg, '')}</div>
        <h1 class="sd-h">Your Digital Assets employee is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dgHire">Hire Digital Assets</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dgHire').onclick = async () => { try { await api('POST', '/api/employees/digital_assets/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div class="sd-ico">${svg(IC.dg, '')}</div>
          <div style="min-width:0"><div class="sd-name">Digital Assets</div><div class="sd-site" id="dgSite"></div></div>
          <span id="dgState"></span>
        </div>
        <div class="sd-acts">
          <select class="in sm hide-sm" id="dgBiz" aria-label="Desk" style="max-width:220px"></select>
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Digital Assets chat">
          <div class="sd-chathead"><div class="t"><b>Digital Assets chat</b><span>Drop an exchange export, ask about a gain, or paste an address to check - never a seed phrase</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dgFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dgPick" multiple hidden accept="image/*,application/pdf,.pdf,.txt,.csv,.xlsx,.ofx,.qif,.sta,.mt940,.xml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Digital Assets desk" id="sdTabs"></nav>
          <div id="dgPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola works out the gains and the checks. It never holds a key, signs or sends anything.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask about your coins, a gain or an address…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dgPick').click()});
    $('#dgPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.digital.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.digital.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/digital/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#dgBiz').addEventListener('change', async e => {
      try { await api('PUT', '/api/digital/workspace', {workspace: e.target.value}); await refreshDesk(true); } catch (err) { toast(err.message, true); }
    });
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dgPage').addEventListener('click', onPageClick);
    $('#dgPage').addEventListener('submit', onSubmit);
    $('#dgPage').addEventListener('change', onChange);
    $('#dgPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dgState'); if (!el) return;
    const w = W(), k = K(), bad = (k.needs || []).some(x => x.bad);
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : !w ? ['warn', 'Set up your desk'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'Working'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#dgSite').textContent = w ? `${w.name} · ${cur()}${d.role && d.role !== 'owner' ? ' · you are ' + RN(d.role) : ''}` : 'No desk yet';
    const sel = $('#dgBiz');
    sel.innerHTML = (d.desks || []).map(x => `<option value="${esc(x.id)}"${w && x.id === w.id ? ' selected' : ''}>${esc(x.name)}</option>`).join('');
    sel.hidden = (d.desks || []).length < 2;
  }
  function paintTabs() {
    const k = K(), ok = !!W(), cu = k.custody || {}, tf = k.transfers || {}, wt = k.watch || {}, rs = k.reserve || {}, py = k.pay || {};
    const L = (o, f) => (o && !o.empty && !o.error) ? f(o) : 0;
    const n = ok ? {custody: L(cu, o => o.short.length) || '', transfers: L(tf, o => o.travel ? o.travel.held.length : 0) || '',
      watch: L(wt, o => o.self_trades.length + o.round_trips.length + o.volume_spikes.length) || '', reserve: L(rs, o => o.fully_backed ? 0 : 1) || '',
      pay: L(py, o => o.peg.off_peg.length) || '', wallets: (k.checks || []).slice(0, 10).filter(c => c.poison).length || ''} : {};
    const tabs = ok ? TABS : TABS.slice(0, 1);
    $('#sdTabs').innerHTML = tabs.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/digital/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dgPage'); if (!box) return;
    if (!W()) { box.innerHTML = pSetup(); starters(); return; }
    const fn = {today: pToday, gains: pGains, wallets: pWallets, pay: pPay, tokens: pTokens, reserve: pReserve, custody: pCustody,
      transfers: pTransfers, watch: pWatch, settings: pSettings}[ST.tab] || pToday;
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
    return `<section class="fm-hero"><div class="fm-hero-ill">${svg(IC.dg, '')}</div>
      <div><h1 class="sd-h">Set up your digital assets desk</h1><p class="lead">Your crypto gains worked out by your country's method from an exchange or wallet export, every address checked before you send, stablecoin payments at your rate, token checks - and for a crypto firm, the reserve, custody against the wallets, the travel rule and market surveillance. Hoola never holds a key, signs or sends anything.</p></div></section>
      <form class="card" data-form="setup"><h2 class="md-h2">Your desk</h2>${setupFields('dgS')}
      <div class="md-acts"><span class="mut" style="font-size:13px">Then drop your exchange's transaction export on Gains, or into the chat.</span><button class="btn" type="submit">Set up the desk</button></div></form>`;
  }
  const setupFields = id => `<div class="md-form">
        <div class="md-field"><label for="${id}1">Name</label><input class="in" id="${id}1" name="name" maxlength="80" placeholder="My coins"></div>
        <div class="md-field"><label for="${id}2">Who it is for</label><select class="in" id="${id}2" name="size">${Object.entries((ST.d && ST.d.sizes) || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></div>
        <div class="md-field"><label for="${id}3">Country (two letters)</label><input class="in" id="${id}3" name="country" required maxlength="2" placeholder="GB"></div>
        <div class="md-field"><label for="${id}4">Currency (three letters)</label><input class="in" id="${id}4" name="currency" required maxlength="3" placeholder="GBP"></div></div>`;
  const ok_ = o => o && !o.empty && !o.error;
  const coin = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 8});
  const short_ = a => S(a).length > 18 ? S(a).slice(0, 8) + '…' + S(a).slice(-6) : S(a);
  const yrs = g => Object.entries((g && g.years) || {}).sort((a, b) => b[0].localeCompare(a[0]));   /* newest tax year first (the browser sorts year keys oldest first) */
  const TYPE_SAY = {buy: ['Buy', 'ok'], sell: ['Sell', 'warn'], swap: ['Swap', 'v'], income: ['Income', 'ok'], fee: ['Fee', ''], transfer: ['Own transfer', '']};

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), g = k.gains || {}, cu = k.custody || {}, tf = k.transfers || {}, rs = k.reserve || {}, wt = k.watch || {};
    const has = k.counts && Object.values(k.counts).some(Boolean);
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} on the desk ${k.needs.length > 1 ? 'need' : 'needs'} a look.` : has ? 'Everything on the desk is in order.' : 'Drop your exchange\'s transaction export on Gains to start.';
    const yr = ok_(g) ? yrs(g)[0] : null;
    const firm = ok_(cu) || ok_(rs) || ok_(tf);
    const k3 = ok_(cu) ? `<div class="k${cu.short.length ? ' low bad' : ''}"><div class="l">Custody</div><div class="v">${cu.short.length ? esc(pl(cu.short.length, 'coin')) + ' short' : 'Matched'}</div><div class="s">${esc(pl(cu.clients, 'client'))} · ${esc(pl(cu.assets.length, 'coin'))}</div></div>`
      : `<div class="k"><div class="l">Wallets</div><div class="v">${esc(num((k.wallets || []).length))}</div><div class="s">${esc(pl((k.checks || []).length, 'address check'))}</div></div>`;
    const k4 = ok_(rs) ? `<div class="k${rs.fully_backed ? '' : ' low bad'}"><div class="l">Reserve cover</div><div class="v">${esc(rs.coverage_pct)}%</div><div class="s">${rs.fully_backed ? 'fully backed by eligible assets' : 'short ' + esc(m0(rs.shortfall))}</div></div>`
      : ok_(tf) && tf.travel ? `<div class="k${tf.travel.held.length ? ' low bad' : ''}"><div class="l">Transfers held</div><div class="v">${esc(num(tf.travel.held.length))}</div><div class="s">of ${esc(pl(tf.count, 'transfer'))}</div></div>`
      : `<div class="k"><div class="l">Coin income</div><div class="v">${ok_(g) ? esc(m0(g.income_total)) : '—'}</div><div class="s">staking, airdrops, pay</div></div>`;
    const hold = ok_(g) ? (g.holdings || []).filter(h => h.qty > 1e-12).sort((a, b) => b.cost - a.cost).slice(0, 8) : [];
    const ya = ok_(g) ? yrs(g).slice(0, 6).reverse() : [];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">
        <div class="k${yr && yr[1].gains + yr[1].losses < 0 ? ' low' : ''}"><div class="l">Net gain${yr ? ', ' + esc(yr[0]) : ''}</div><div class="v">${yr ? esc(m0(yr[1].gains + yr[1].losses)) : '—'}</div><div class="s">${yr ? `${esc(pl(yr[1].disposals, 'disposal'))} · gains ${esc(m0(yr[1].gains))}` : 'no transactions yet'}</div></div>
        <div class="k"><div class="l">Holdings at cost</div><div class="v">${ok_(g) ? esc(m0(hold.reduce((s, h) => s + h.cost, 0))) : '—'}</div><div class="s">${ok_(g) ? esc(pl(hold.length, 'coin')) : 'no holdings yet'}</div></div>
        ${k3}${k4}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Gains by tax year</h2><div class="r"><button class="btn soft sm" type="button" data-go="gains">Gains</button></div></div>
          ${ya.length ? yearBars(ya) : empty(g.error || 'Add your transactions to see gains by year.')}</section></div>
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">What you hold, at cost</h2></div>
          ${hold.length ? ring(hold.map((h, i) => [h.symbol, Math.round(h.cost), 'dg-c' + (i % 8)]), short(hold.reduce((s, h) => s + h.cost, 0)), 'cost', 'Holdings at cost') : empty('Holdings show once you have bought coins.')}</section>
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${firm ? 'The firm' : 'Recent address checks'}</h2></div>
          ${firm ? [ok_(cu) ? `<div class="cs-row"><span style="flex:1">Custody</span>${cu.short.length ? tag(cu.short.join(', ') + ' short', 'bad') : tag('matched', 'ok')}<button class="btn soft sm" type="button" data-go="custody">Open</button></div>` : '',
              ok_(rs) ? `<div class="cs-row"><span style="flex:1">Reserve ${esc(rs.coverage_pct)}% covered</span>${rs.fully_backed ? tag('backed', 'ok') : tag('short', 'bad')}<button class="btn soft sm" type="button" data-go="reserve">Open</button></div>` : '',
              ok_(tf) ? `<div class="cs-row"><span style="flex:1">${esc(pl(tf.count, 'transfer'))}</span>${tf.travel ? (tf.travel.held.length ? tag(tf.travel.held.length + ' held', 'bad') : tag('travel rule complete', 'ok')) : tag('no threshold', 'warn')}<button class="btn soft sm" type="button" data-go="transfers">Open</button></div>` : '',
              ok_(wt) ? `<div class="cs-row"><span style="flex:1">${esc(pl(wt.trades, 'trade'))} watched</span>${wt.self_trades.length + wt.round_trips.length + wt.volume_spikes.length ? tag((wt.self_trades.length + wt.round_trips.length + wt.volume_spikes.length) + ' alerts', 'bad') : tag('no alerts', 'ok')}<button class="btn soft sm" type="button" data-go="watch">Open</button></div>` : ''].join('')
            : ((k.checks || []).slice(0, 5).map(c => `<div class="cs-row"><span class="mk-mono" style="flex:1">${esc(short_(c.address))}</span>${c.poison ? tag('look-alike', 'bad') : c.valid ? tag('valid', 'ok') : tag('not valid', 'bad')}<span class="mut nw">${esc(dt(c.on))}</span></div>`).join('') || empty('Check an address on Wallets & safety before you send.'))}</section></div>`;
  }
  function yearBars(ya) {   /* gains above the line, losses below it, by tax year */
    const W = 480, H = 220, L = 52, B = 28, T = 12, mx = Math.max(1, ...ya.map(([, y]) => Math.max(y.gains, -y.losses)));
    const mid = T + (H - T - B) / 2, h = (H - T - B) / 2, bw = Math.min(56, (W - L - 20) / ya.length * 0.6);
    const x = i => L + 10 + (i + 0.5) * (W - L - 20) / ya.length;
    return `<div class="cs-chart dg-years"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Gains and losses by tax year">
      <line class="zero" x1="${L}" x2="${W - 8}" y1="${mid}" y2="${mid}"/><text class="tx" x="${L - 8}" y="${T + 8}" text-anchor="end">${esc(short(mx))}</text><text class="tx" x="${L - 8}" y="${H - B}" text-anchor="end">-${esc(short(mx))}</text>
      ${ya.map(([n, y], i) => { const gh = y.gains / mx * h, lh = -y.losses / mx * h, net = y.gains + y.losses;
        return `<g><rect class="gn" x="${(x(i) - bw / 2).toFixed(1)}" y="${(mid - gh).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(gh, 0.5).toFixed(1)}" rx="4"><title>${esc(n)} gains ${esc(m0(y.gains))}</title></rect>
          <rect class="ls" x="${(x(i) - bw / 2).toFixed(1)}" y="${mid}" width="${bw.toFixed(1)}" height="${Math.max(lh, 0.5).toFixed(1)}" rx="4"><title>${esc(n)} losses ${esc(m0(y.losses))}</title></rect>
          <text class="tx" x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle">${esc(n)}</text><text class="tx nt" x="${x(i).toFixed(1)}" y="${(mid - gh - 6).toFixed(1)}" text-anchor="middle">${esc(short(net))}</text></g>`; }).join('')}</svg></div>
      <div class="cs-legend"><span><i class="dg-gn"></i>Gains</span><span><i class="dg-ls"></i>Losses</span><span class="mut">the figure above each year is the net</span></div>`;
  }

  /* ---------------------------------------------------------------- gains */
  function pGains() {
    const k = K(), g = k.gains || {}, s = k.settings || {};
    const meth = s.method ? ({fifo: 'first in, first out', average: 'average cost', uk_share_id: 'same day, 30 days, then the pool'})[s.method] + ' (your choice)' : (k.method_name ? k.method_name : 'not known for ' + (k.country || 'your country') + ' - choose one in Settings');
    return `<div><h1 class="sd-h">Gains</h1><p class="lead">Every buy, sell, swap, coin income and fee, matched by ${esc(meth)}. A swap is a sale of one coin and a buy of the other at the day's value; a transfer between your own wallets is not a sale. ${s.method ? '' : esc(k.method_note || '')}</p></div>
      ${ro()}${err(g)}
      ${ok_(g) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Gains', esc(m2(g.gains)), pl(g.disposals.length, 'disposal'), 'ok')}${kpi('Losses', esc(m2(g.losses)), g.note ? 'not set off' : '', g.losses ? 'warn' : '')}${kpi('Net', esc(m2(g.net)), g.exempt_gain ? 'exempt (held over a year) ' + m0(g.exempt_gain) : '')}${kpi('Coin income', esc(m2(g.income_total)), pl(g.income.length, 'receipt'))}</section>
        ${g.note ? `<p class="cs-note">${esc(g.note)}.</p>` : ''}<p class="cs-note">${esc(g.tax)} ${g.own_transfers_ignored ? esc(pl(g.own_transfers_ignored, 'transfer')) + ' between your own wallets ' + (g.own_transfers_ignored === 1 ? 'was' : 'were') + ' left out.' : ''}</p>` : ''}
      ${uploader('events', 'An exchange or wallet export (CSV)', 'Coinbase, Kraken, Binance and most others: date, type, asset, quantity, value in your currency. The title lines at the top are skipped.')}
      <div class="md-2" style="align-items:start">
        <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">By tax year</h2><div class="r">${ok_(g) ? '<button class="btn soft sm" type="button" data-dl="gains">CSV for your return</button>' : ''}</div></div>
          ${ok_(g) && Object.keys(g.years).length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Tax year</th><th class="r">Disposals</th><th class="r">Proceeds</th><th class="r">Gains</th><th class="r">Losses</th><th class="r">Income</th></tr></thead><tbody>${yrs(g).map(([n, y]) => `<tr><td><b>${esc(n)}</b></td><td class="r">${esc(y.disposals)}</td><td class="r">${esc(m0(y.proceeds))}</td><td class="r cs-pos">${esc(m0(y.gains))}</td><td class="r cs-neg">${esc(m0(y.losses))}</td><td class="r">${esc(m0(y.income))}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing sold yet.')}</section>
        <section class="card"><h2 class="md-h2">What you hold</h2>
          ${ok_(g) && g.holdings.length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Coin</th><th class="r">Quantity</th><th class="r">Cost</th><th class="r">Cost each</th></tr></thead><tbody>${g.holdings.map(h => `<tr><td><b>${esc(h.symbol)}</b></td><td class="r ${h.qty < 0 ? 'cs-neg' : ''}">${esc(coin(h.qty))}</td><td class="r">${esc(m2(h.cost))}</td><td class="r mut">${h.qty > 0 ? esc(m2(h.cost / h.qty)) : '—'}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing held.')}
          ${ok_(g) && Object.keys(g.by_asset).length ? `<div class="cr-sub" style="margin-top:12px">Gain or loss by coin</div>${bars(Object.entries(g.by_asset).sort((a, b) => b[1] - a[1]).map(([n, v]) => [n, Math.abs(v), v >= 0 ? 'dg-up' : 'dg-dn', v >= 0 ? 'gain' : 'loss']), v => m0(v), 'Gain or loss by coin')}` : ''}</section></div>
      ${ok_(g) && g.disposals.length ? `<section class="card"><h2 class="md-h2">Each disposal</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Date</th><th>Coin</th><th class="r">Quantity</th><th class="r">Proceeds</th><th class="r">Cost</th><th class="r">Gain</th><th>Matched</th></tr></thead><tbody>${g.disposals.slice().reverse().slice(0, 200).map(d => `<tr><td>${esc(dmy(d.date))}</td><td><b>${esc(d.symbol)}</b></td><td class="r">${esc(coin(d.qty))}</td><td class="r">${esc(m2(d.proceeds))}</td><td class="r">${esc(m2(d.cost))}</td><td class="r ${sign(d.gain)}">${esc(m2(d.gain))}</td><td class="mut" style="font-size:13px">${esc((d.parts || []).map(p => p.rule || (p.acquired ? 'bought ' + dmy(p.acquired) + (p.term ? ' · ' + p.term : '') + (p.exempt ? ' · exempt' : '') : '')).filter(Boolean).join('; '))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Every transaction</h2>
        ${ok_(g) || (g.error && (k.counts || {}).events) ? listRows('events', g.rows || [], [['date', 'Date', 0, v => esc(dmy(v))], ['type', '', 0, v => tag((TYPE_SAY[v] || [v])[0], (TYPE_SAY[v] || [])[1])], ['asset', 'Coin', 0, (v, r) => `<b>${esc(v)}</b>${r.type === 'swap' ? ` → ${esc(coin(r.get_qty))} ${esc(r.get_asset)}` : ''}`], ['qty', 'Quantity', 1, v => esc(coin(v))], ['value', 'Value', 1, v => esc(m2(v))], ['kind', 'Note', 0, v => `<span class="mut">${esc(v || '')}</span>`]], 300) : empty('No transactions yet.')}
        ${addForm('events', [['date', 'Date', 'date'], ['type', 'Type', [['buy', 'Buy'], ['sell', 'Sell'], ['swap', 'Swap'], ['income', 'Income'], ['fee', 'Fee'], ['transfer', 'Own transfer']]], ['asset', 'Coin', '', 'BTC'], ['qty', 'Quantity', 'num'], ['value', `Value (${cur()})`, 'num'], ['get_asset', 'Got (swap)', '', 'ETH'], ['get_qty', 'Got quantity', 'num']], 'Add')}</section>`;
  }

  /* ---------------------------------------------------------------- wallets + safety */
  function pWallets() {
    const k = K(), o = ST.out.check;
    const chains = (k.chains || []).map(c => [c, cap(c)]);
    return `<div><h1 class="sd-h">Wallets &amp; safety</h1><p class="lead">Check an address before you send: its shape and checksum for the chain, and whether it only looks like one of yours - the trick scammers use by sending you a tiny amount from a look-alike. Paste a message to see the signs of a wallet-draining scam. Never share your seed phrase or private key - not with anyone, not with Hoola.</p></div>
      ${ro()}
      <form class="card" data-form="check"><h2 class="md-h2">Check before you send</h2>
        <div class="dg-check"><label class="ins-lab">Chain<select class="in" name="chain">${chains.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('')}</select></label>
          <label class="ins-lab">The address you are about to send to<input class="in mk-mono" name="address" maxlength="120" autocomplete="off" spellcheck="false" placeholder="paste the full address"></label></div>
        <label class="ins-lab" style="margin-top:12px">Or a message you received<textarea class="in" name="message" rows="3" placeholder="Your wallet needs to be validated - connect and approve…"></textarea></label>
        <div class="md-acts"><span class="mut" style="font-size:13px">Compared with the ${esc(pl((k.wallets || []).length, 'address', 'addresses'))} you saved below.</span><button class="btn" type="submit">Check</button></div>
        ${o ? (o.error ? err(o) : `<div class="cm-res">${o.address ? `<div class="dg-verdict ${o.looks_like_yours_but_is_not && o.looks_like_yours_but_is_not.length ? 'bad' : o.address.valid_shape ? 'ok' : 'bad'}"><b>${o.looks_like_yours_but_is_not && o.looks_like_yours_but_is_not.length ? 'Stop - this looks like your address but is not' : !o.address.valid_shape ? 'Not a valid address for this chain' : o.is_yours ? 'Valid - this is your ' + esc(o.label) : 'Valid shape'}</b><span>${esc(o.address.checked)}${o.warning ? ' · ' + esc(o.warning) : ''}</span>${(o.looks_like_yours_but_is_not || []).map(x => `<span class="mk-mono">yours: ${esc(x)}</span>`).join('')}</div>` : ''}
          ${o.signs ? (o.signs.length ? `<div class="cm-warn"><b>Signs of a draining scam</b>${o.signs.map(x => `<div>${esc(x)}</div>`).join('')}</div>` : '<p class="cs-pos" style="margin:0">None of the usual draining signs in this message.</p>') : ''}
          <p class="cs-note" style="margin:0">A valid shape does not mean the address is safe or right: send a small test amount first, and copy the address from its source, never from your history.</p></div>`) : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Your addresses</h2>
          ${listRows('wallets', k.wallets || [], [['label', 'Name', 0, v => `<b>${esc(v)}</b>`], ['chain', 'Chain', 0, v => esc(cap(v))], ['address', 'Address', 0, v => `<span class="mk-mono" title="${esc(v)}">${esc(short_(v))}</span>`]], 100)}
          ${addForm('wallets', [['label', 'Name', '', 'Cold wallet'], ['chain', 'Chain', chains], ['address', 'Address', '', '']], 'Save address')}
          <p class="cs-note">Only public addresses - never a seed phrase or a private key.</p></section>
        <section class="card"><h2 class="md-h2">Addresses checked</h2>${(k.checks || []).length ? `<div class="iv-tw"><table class="tb"><tbody>${k.checks.map(c => `<tr><td class="mk-mono" title="${esc(c.address)}">${esc(short_(c.address))}</td><td class="mut">${esc(cap(c.chain))}</td><td>${c.poison ? tag('look-alike', 'bad') : c.valid ? tag('valid', 'ok') : tag('not valid', 'bad')}</td><td class="r mut nw">${esc(dt(c.on))}</td></tr>`).join('')}</tbody></table></div>` : empty('Nothing checked yet.')}</section></div>`;
  }

  /* ---------------------------------------------------------------- stablecoin pay */
  function pPay() {
    const k = K(), p = k.pay || {}, cfg = p.pay || ((k.settings || {}).pay) || {}, q = ST.out.quote;
    const px = ok_(p) ? p.prices.map(x => [S(x.at).slice(5, 10) || S(x.at), x.price]) : [];
    return `<div><h1 class="sd-h">Stablecoin pay</h1><p class="lead">Taking payment in a stablecoin: how many coins to ask for an invoice at your rate, and the coin's price against its peg. Your rate comes from where you will convert the coins - Hoola never quotes one.</p></div>
      ${ro()}
      <form class="card" data-form="quote"><h2 class="md-h2">Ask for an invoice in coins</h2><div class="cm-grid5">
        <label class="ins-lab">Invoice (${esc(cur())})<input class="in" name="invoice" inputmode="decimal" required></label>
        <label class="ins-lab">Coin<input class="in" name="coin" maxlength="10" value="${esc(cfg.coin || '')}" placeholder="USDC"></label>
        <label class="ins-lab">Your rate (${esc(cur())} for one coin)<input class="in" name="rate" inputmode="decimal" value="${esc(cfg.rate ?? '')}"></label>
        <label class="ins-lab">Network fee (coins)<input class="in" name="network_fee" inputmode="decimal" value="${esc(cfg.network_fee ?? '')}"></label>
        <button class="btn" type="submit">Work it out</button></div>
        ${cfg.rate_on ? `<p class="cs-note">Your rate was set on ${esc(dmy(cfg.rate_on))} - update it before each invoice.</p>` : ''}
        ${q ? (q.error ? err(q) : `<div class="cm-res"><div class="cm-big">${esc(coin(q.payment.with_fee))} ${esc(q.coin || '')}<span>to ask for ${esc(m2(q.invoice))} (${esc(coin(q.payment.coins))} + the network fee)</span></div></div>`) : ''}</form>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Against the peg</h2><div class="r"><span class="mut" style="font-size:13px">peg ${esc(cfg.peg ?? 1)} · tolerance ${esc(cfg.tolerance_pct ?? 0.5)}%</span></div></div>
        ${px.length > 1 ? line(px, 'Coin price against its peg', v => num(v), 'dg-peg', true) : empty(p.error || 'Add the coin\'s prices (a CSV of date and price) to watch the peg.')}
        ${ok_(p) && p.peg.off_peg.length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>When</th><th class="r">Price</th><th class="r">Off the peg</th></tr></thead><tbody>${p.peg.off_peg.map(x => `<tr><td>${esc(x.at)}</td><td class="r">${esc(num(x.price))}</td><td class="r cs-neg">${esc(sgn(x.off_pct))}%</td></tr>`).join('')}</tbody></table></div>` : ok_(p) ? '<p class="cs-pos" style="margin:8px 0 0">Every price is within your tolerance.</p>' : ''}
        ${uploader('prices', 'The coin\'s prices (CSV)', 'Columns: date or time, price. A new file replaces the list.')}
        ${CAN() ? `<form class="mk-add" data-form="peg"><label class="ins-lab">Peg<input class="in" name="peg" inputmode="decimal" value="${esc(cfg.peg ?? '')}" placeholder="1"></label><label class="ins-lab">Tolerance %<input class="in" name="tolerance_pct" inputmode="decimal" value="${esc(cfg.tolerance_pct ?? '')}" placeholder="0.5"></label><button class="btn soft" type="submit">Save</button></form>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- tokens */
  function pTokens() {
    const k = K(), o = ST.out.token, yn = (n, l) => `<label class="ins-lab">${l}<select class="in" name="${n}"><option value="">Not known</option><option value="true">Yes</option><option value="false">No</option></select></label>`;
    return `<div><h1 class="sd-h">Token checks</h1><p class="lead">Before you buy or list a token: how much of the supply its biggest wallets hold, whether new tokens can still be minted or yours frozen, whether the contract can be changed, and whether it is audited and its team known. Checks on what you give; the token's own contract and documents decide.</p></div>
      ${ro()}
      <form class="card" data-form="token"><h2 class="md-h2">Check a token</h2><div class="cm-grid5">
        <label class="ins-lab">Token<input class="in" name="name" required maxlength="60" placeholder="MOON"></label>
        <label class="ins-lab">Chain<input class="in" name="chain" maxlength="20" placeholder="solana"></label>
        <label class="ins-lab">Total supply<input class="in" name="supply" inputmode="decimal"></label>
        <label class="ins-lab">Your limit for the top 10 wallets, %<input class="in" name="max_top10_pct" inputmode="decimal" placeholder="yours"></label>
        <label class="ins-lab">Contract address<input class="in mk-mono" name="contract" maxlength="120"></label></div>
        <div class="dg-tk"><label class="ins-lab">The biggest wallets' amounts (one a line, up to 10)<textarea class="in" name="top_holders" rows="5" placeholder="400000&#10;250000&#10;90000"></textarea></label>
          <div class="cm-grid5 dg-yn">${yn('mint_authority_open', 'New tokens can be minted')}${yn('freeze_authority_open', 'Holders can be frozen')}${yn('upgradeable', 'The contract can be changed')}${yn('audited', 'Audited')}${yn('team_known', 'The team is known')}${yn('liquidity_locked', 'Liquidity is locked')}</div></div>
        <div class="md-acts"><span></span><button class="btn" type="submit">Check</button></div>
        ${o ? (o.error ? err(o) : `<div class="cm-res"><div class="dg-verdict ${o.level === 'high' ? 'bad' : o.level === 'some' ? 'warn' : 'ok'}"><b>${o.level === 'none found' ? 'No warning signs in what you gave' : (o.level === 'high' ? 'High-risk signs' : 'Some warning signs')}</b>${o.flags.map(f => `<span>${esc(f)}</span>`).join('')}</div><p class="cs-note" style="margin:0">${esc(o.says)}</p></div>`) : ''}</form>
      <section class="card"><h2 class="md-h2">Tokens checked</h2>${(k.tokens || []).length ? k.tokens.map(t => `<div class="cs-row"><span style="flex:1"><b>${esc(t.name)}</b>${t.chain ? ` <span class="mut">${esc(t.chain)}</span>` : ''}${t.flags.length ? `<span class="mut" style="display:block;font-size:13px">${esc(t.flags.join('; '))}</span>` : ''}</span>${tag(t.level, t.level === 'high' ? 'bad' : t.level === 'some' ? 'warn' : 'ok')}<span class="mut nw">${esc(dt(t.on))}</span>${ask('Token ' + t.name)}${rmBtn('tokens', t.n)}</div>`).join('') : empty('No token checked yet.')}</section>`;
  }

  /* ---------------------------------------------------------------- reserve */
  function pReserve() {
    const k = K(), r = k.reserve || {}, rules = r.rules || ((k.settings || {}).reserve) || {};
    return `<div><h1 class="sd-h">Reserve</h1><p class="lead">For a stablecoin issuer: the reserve against the coins in circulation, counting only the asset types your rules allow, with how much sits at each holder against your limit.</p></div>
      ${ro()}${err(r)}
      ${ok_(r) ? `<section class="card"><div class="dg-cover"><div class="cm-big">${esc(r.coverage_pct)}%<span>of ${esc(m0(r.supply))} in circulation is covered by eligible assets</span></div>
          <div class="cm-gauge"><div class="bar"><i class="${r.fully_backed ? 'ok' : 'bad'}" style="width:${Math.min(100, r.coverage_pct).toFixed(1)}%"></i><u style="left:${Math.min(100, 100 / Math.max(1, r.coverage_pct / 100)).toFixed(1)}%" title="fully backed"></u></div>
          <div class="ft"><span>eligible ${esc(m0(r.eligible_reserve))}</span><span>${r.fully_backed ? 'fully backed' : 'short ' + esc(m0(r.shortfall))}</span><span>all assets ${esc(m0(r.reserve))}</span></div></div></div></section>
        <div class="md-2" style="align-items:start">
          <section class="card"><h2 class="md-h2">By asset type</h2>${bars(r.by_type.map(([t, v]) => [cap(t.replace(/_/g, ' ')), v, (rules.eligible || []).includes(t.toLowerCase()) ? 'dg-up' : 'dg-dn', (rules.eligible || []).includes(t.toLowerCase()) ? 'eligible' : 'not eligible']), m0, 'Reserve by type')}</section>
          <section class="card"><h2 class="md-h2">By holder</h2>${bars(r.by_holder.map(h => [h.held_at, h.pct, r.over_holder_limit.includes(h.held_at) ? 'dg-dn' : 'dg-up', r.over_holder_limit.includes(h.held_at) ? 'over your limit' : '']), v => num(v) + '%', 'Reserve by holder')}
            ${rules.max_per_holder_pct !== null && rules.max_per_holder_pct !== undefined ? `<p class="cs-note">Your limit: ${esc(rules.max_per_holder_pct)}% at one holder.</p>` : ''}</section></div>` : ''}
      ${CAN() ? `<form class="card" data-form="reserve"><h2 class="md-h2">Your reserve rules</h2><div class="mk-three">
          <label class="ins-lab">Coins in circulation (in ${esc(cur())})<input class="in" name="supply" inputmode="decimal" value="${esc(rules.supply ?? '')}"></label>
          <label class="ins-lab">Eligible asset types (one a line)<textarea class="in" name="eligible" rows="3" placeholder="cash&#10;tbill_3m&#10;reverse_repo">${esc((rules.eligible || []).join('\n'))}</textarea></label>
          <label class="ins-lab">Limit at one holder, %<input class="in" name="max_per_holder_pct" inputmode="decimal" value="${esc(rules.max_per_holder_pct ?? '')}"></label></div>
          <div class="md-acts"><span class="mut" style="font-size:13px">From your licence or your reserve policy.</span><button class="btn" type="submit">Save</button></div></form>` : ''}
      <section class="card"><h2 class="md-h2">The reserve's assets</h2>${listRows('assets', r.assets || [], [['type', 'Type'], ['held_at', 'Held at'], ['value', 'Value', 1, v => esc(m0(v))]], 200)}
        ${uploader('assets', 'A reserve statement (CSV)', 'Columns: type, value, held at. A new statement replaces the list.')}${addForm('assets', [['type', 'Type', '', 'tbill_3m'], ['value', 'Value', 'num'], ['held_at', 'Held at', '', 'Bank A']])}</section>`;
  }

  /* ---------------------------------------------------------------- custody */
  function pCustody() {
    const k = K(), c = k.custody || {};
    return `<div><h1 class="sd-h">Custody</h1><p class="lead">What your clients are owed in each coin (your ledger) against what your wallets hold. A shortfall is an incident, not a rounding.</p></div>
      ${ro()}${err(c)}
      ${ok_(c) ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Owed against held</h2><div class="r"><button class="btn soft sm" type="button" data-dl="custody">CSV</button></div></div>
          <div class="dg-cust">${c.assets.map(a => { const mx = Math.max(a.clients_are_owed, a.wallets_hold, 1e-12);
            return `<div class="${a.status}"><div class="h"><b>${esc(a.asset)}</b>${tag(a.status, a.status === 'short' ? 'bad' : a.status === 'surplus' ? 'warn' : 'ok')}<span class="mut">difference ${esc(sgn(a.difference))}</span>${ask('Custody ' + a.asset)}</div>
              <div class="r2"><span>Clients are owed</span><i><b class="ow" style="width:${(a.clients_are_owed / mx * 100).toFixed(1)}%"></b></i><em>${esc(coin(a.clients_are_owed))}</em></div>
              <div class="r2"><span>Wallets hold</span><i><b class="hd" style="width:${(a.wallets_hold / mx * 100).toFixed(1)}%"></b></i><em>${esc(coin(a.wallets_hold))}</em></div></div>`; }).join('')}</div>
          ${c.negative_client_lines.length ? `<p class="cs-neg">Client lines below zero: ${esc(c.negative_client_lines.map(x => x.client + ' ' + coin(x.qty) + ' ' + x.asset).join('; '))}.</p>` : ''}</section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Client ledger</h2>${listRows('ledger', c.ledger || [], [['client', 'Client'], ['asset', 'Coin'], ['qty', 'Owed', 1, v => `<span class="${v < 0 ? 'cs-neg' : ''}">${esc(coin(v))}</span>`]], 100)}
          ${uploader('ledger', 'The client ledger (CSV)', 'Columns: client, asset, quantity. A new file replaces the list.')}</section>
        <section class="card"><h2 class="md-h2">Wallet balances</h2>${listRows('balances', c.balances || [], [['wallet', 'Wallet'], ['asset', 'Coin'], ['balance', 'Holds', 1, v => esc(coin(v))]], 100)}
          ${uploader('balances', 'Wallet balances (CSV)', 'Columns: wallet, asset, balance - read from the chain at the same moment as the ledger.')}
          ${addForm('balances', [['wallet', 'Wallet', '', 'cold-1'], ['asset', 'Coin', '', 'BTC'], ['balance', 'Balance', 'num']])}</section></div>`;
  }

  /* ---------------------------------------------------------------- transfers */
  function pTransfers() {
    const k = K(), t = k.transfers || {}, tr = t.travel;
    const rt = ok_(t) ? Object.entries(t.returns || {}) : [];
    return `<div><h1 class="sd-h">Transfers</h1><p class="lead">Each transfer checked for the originator and beneficiary details the travel rule asks for above your threshold, and every transfer counted by period for your licensing return. Accounts are kept as their last 4 here - the full details stay in your own system.</p></div>
      ${ro()}${err(t)}
      ${ok_(t) && t.threshold === null ? '<p class="cs-note">Set your threshold (your country\'s rule) in Settings to check the travel-rule details.</p>' : ''}
      ${tr ? `<section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Travel rule</h2><div class="r"><span class="mut" style="font-size:13px">threshold ${esc(m0(t.threshold))}</span></div></div>
          ${tr.held.length ? `<p class="cs-neg" style="margin:0 0 8px">Hold ${esc(pl(tr.held.length, 'transfer'))} until the details are complete.</p>` : '<p class="cs-pos" style="margin:0 0 8px">Every transfer has the details it needs.</p>'}
          <div class="iv-tw"><table class="tb"><thead><tr><th>Transfer</th><th>Date</th><th class="r">Value</th><th>From → to</th><th>Missing</th><th></th></tr></thead><tbody>${tr.transfers.slice().sort((a, b) => a.ok - b.ok).slice(0, 200).map(x => `<tr><td><b>${esc(x.id)}</b></td><td>${esc(dmy(x.date))}</td><td class="r">${esc(m0(x.value))}${x.above_threshold ? ' ' + tag('above', 'v') : ''}</td><td>${esc(x.originator_name || '—')} → ${esc(x.beneficiary_name || '—')}</td><td>${x.ok ? tag('complete', 'ok') : `<span class="mk-prob">${esc(x.missing.map(m => m.replace(/_/g, ' ')).join(', '))}</span>`}</td><td class="r">${ask('Transfer ' + x.id)}${rmBtn('transfers', x.n)}</td></tr>`).join('')}</tbody></table></div>
          <p class="cs-note">${esc(tr.from)}.</p></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">For your licensing return</h2><div class="r">${rt.length ? '<button class="btn soft sm" type="button" data-dl="returns">CSV</button>' : ''}</div></div>
        ${rt.length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Period</th><th>Type</th><th class="r">Count</th><th class="r">Value</th></tr></thead><tbody>${rt.slice().reverse().map(([p, ts]) => Object.entries(ts).map(([ty, v], i) => `<tr><td>${i ? '' : `<b>${esc(p)}</b>`}</td><td>${esc(cap(ty))}</td><td class="r">${esc(num(v.count))}</td><td class="r">${esc(m0(v.value))}</td></tr>`).join('')).join('')}</tbody></table></div>` : empty('Add your transfers to count them.')}</section>
      <section class="card"><h2 class="md-h2">Add transfers</h2>${uploader('transfers', 'Transfers (CSV)', 'Columns: id, date, type, value, originator name / account / address, beneficiary name / account.')}
        ${addForm('transfers', [['id', 'ID'], ['date', 'Date', 'date'], ['type', 'Type', '', 'withdrawal'], ['value', 'Value', 'num'], ['originator_name', 'Originator'], ['originator_account', 'Originator account'], ['beneficiary_name', 'Beneficiary'], ['beneficiary_account', 'Beneficiary account']])}</section>`;
  }

  /* ---------------------------------------------------------------- surveillance */
  function pWatch() {
    const k = K(), w = k.watch || {}, s = k.settings || {};
    const row = t => t ? `${esc(t.id)} · ${esc(dt(t.time))} · ${esc(coin(t.qty))} ${esc(t.asset)} · ${esc(t.buyer)} ← ${esc(t.seller)}` : '';
    return `<div><h1 class="sd-h">Surveillance</h1><p class="lead">Trades on your venue watched for self-trades (the same owner or linked accounts on both sides), round trips between two accounts inside your window, and a coin's volume far above its own normal. Alerts to look at, not findings - a person decides whether anything is reported.</p></div>
      ${ro()}${err(w)}
      ${ok_(w) ? `<section class="iv-kpis mk-k2" style="grid-template-columns:repeat(4,minmax(0,1fr))">${kpi('Trades watched', esc(num(w.trades)))}${kpi('Self-trades', esc(num(w.self_trades.length)), '', w.self_trades.length ? 'bad' : '')}${kpi('Round trips', esc(num(w.round_trips.length)), '', w.round_trips.length ? 'bad' : '')}${kpi('Volume spikes', esc(num(w.volume_spikes.length)), '', w.volume_spikes.length ? 'warn' : '')}</section>
        <div class="md-2" style="align-items:start">
          <section class="card"><h2 class="md-h2">Self-trades</h2>${w.self_rows.length ? w.self_rows.map(t => `<div class="cs-row"><span class="mk-mono" style="flex:1">${row(t)}</span>${ask('Self-trade ' + t.id)}</div>`).join('') : empty('None.')}</section>
          <section class="card"><h2 class="md-h2">Round trips</h2>${w.round_rows.length ? w.round_rows.map(([a, b]) => `<div class="dg-pair"><span class="mk-mono">${row(a)}</span><span class="mk-mono">${row(b)}</span></div>`).join('') : empty('None.')}</section></div>
        ${w.volume_spikes.length ? `<section class="card"><h2 class="md-h2">Volume spikes</h2>${bars(w.volume_spikes.map(x => [x.asset + ' ' + dmy(x.date), x.volume, 'dg-dn', 'usual ' + coin(x.usual)]), v => coin(v), 'Volume spikes')}</section>` : ''}` : ''}
      <section class="card"><h2 class="md-h2">Trades</h2>${uploader('trades', 'Trades (CSV)', 'Columns: id, time, asset, quantity, buyer account, seller account.')}
        ${CAN() ? `<form data-form="watchset" style="margin-top:12px"><div class="mk-three"><label class="ins-lab">Linked accounts (one group a line, commas)<textarea class="in" name="linked" rows="3" placeholder="acc-1, acc-7&#10;acc-3, acc-4">${esc((s.linked || []).map(g => g.join(', ')).join('\n'))}</textarea></label>
          <label class="ins-lab">Round-trip window (minutes)<input class="in" name="window_minutes" inputmode="decimal" value="${esc(s.window_minutes ?? '')}" placeholder="30"></label>
          <label class="ins-lab">A spike is how many times normal<input class="in" name="spike_multiple" inputmode="decimal" value="${esc(s.spike_multiple ?? '')}" placeholder="5"></label></div>
          <div class="md-acts"><span></span><button class="btn soft" type="submit">Save</button></div></form>` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const k = K(), s = k.settings || {}, w = W();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your tax method and tax year, your travel-rule threshold and your return's period. The method Hoola knows for ${esc(k.country || 'your country')} is from memory until you check it with your tax office or adviser.</p></div>
      ${ro()}
      <form class="card" data-form="settings"><h2 class="md-h2">Tax and rules</h2><div class="md-form">
        <div class="md-field"><label for="dgT1">Tax method</label><select class="in" id="dgT1" name="method"><option value="">${esc(k.method_name ? 'My country\'s: ' + k.method_name : 'My country\'s (not known for ' + (k.country || 'it') + ')')}</option>${[['fifo', 'First in, first out'], ['average', 'Average cost'], ['uk_share_id', 'Same day, 30 days, then the pool']].map(([v, l]) => `<option value="${v}"${s.method === v ? ' selected' : ''}>${l}</option>`).join('')}</select></div>
        <div class="md-field"><label for="dgT2">Tax year starts (MM-DD)</label><input class="in" id="dgT2" name="tax_year_start" maxlength="5" value="${esc(s.tax_year_start || '')}" placeholder="01-01 (calendar year)"></div>
        <div class="md-field"><label for="dgT3">Travel-rule threshold (${esc(cur())})</label><input class="in" id="dgT3" name="threshold" inputmode="decimal" value="${esc(s.threshold ?? '')}" placeholder="your country's rule"></div>
        <div class="md-field"><label for="dgT4">Licensing return period</label><select class="in" id="dgT4" name="period"><option value="quarter"${s.period !== 'month' ? ' selected' : ''}>Quarter</option><option value="month"${s.period === 'month' ? ' selected' : ''}>Month</option></select></div></div>
        <p class="cs-note">Hoola knows a method for ${esc((k.known_countries || []).join(', '))}${k.method_note ? esc(k.method_note) : ''}.</p>
        ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">What is on the desk</h2>${Object.entries(k.counts || {}).filter(x => x[1]).map(([n, v]) => `<div class="cs-row"><span style="flex:1">${esc(cap(({events: 'transactions', assets: 'reserve assets', ledger: 'client ledger lines', balances: 'wallet balances', tokens: 'token checks', checks: 'address checks'})[n] || n))}</span><b>${esc(num(v))}</b></div>`).join('') || empty('Nothing yet.')}
          ${(k.files || []).length ? `<div class="cr-sub" style="margin-top:12px">Files read</div>${k.files.map(f => `<div class="cs-row"><span style="flex:1">${esc(f.name)} <span class="mut">${esc(f.kind)} · ${esc(f.rows)} rows</span></span><span class="mut nw">${esc(dt(f.on))}</span></div>`).join('')}` : ''}</section>
        <section class="card"><h2 class="md-h2">This desk</h2><div class="cs-row"><span style="flex:1">${esc(w.name)}</span><span class="mut">${esc((ST.d.sizes || {})[w.size] || w.size || '')}</span></div><div class="cs-row"><span style="flex:1">Currency</span><b>${esc(w.currency)}</b></div><div class="cs-row"><span style="flex:1">You are</span><b>${esc(RN(ST.d.role))}</b></div>
          <details class="ins-more"><summary>Set up another desk</summary><form data-form="setup">${setupFields('dgN')}<div class="md-acts"><span></span><button class="btn soft" type="submit">Set it up</button></div></form></details></section></div>`;
  }

  async function download(what) {
    try {
      const r = await fetch(`/api/digital/download?workspace=${enc(W().id)}&what=${enc(what)}`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
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
    try {
      const rm = t.closest('[data-rm]'); if (rm) { e.preventDefault(); await run('remove', {register: rm.dataset.rm, n: Number(rm.dataset.n)}); await changed('Removed.'); return; }
      const ra = t.closest('[data-rmall]'); if (ra) { if (!confirm('Remove the whole list from the desk?')) return; await run('remove', {register: ra.dataset.rmall, all: true}); await changed('Cleared.'); return; }
    } catch (err2) { toast(err2.message, true); }
  }
  async function onChange(e) {
    if (e.target.tagName === 'SELECT') e.target.dataset.touched = '1';
    const fi = e.target.closest('[data-upfile]'); if (!fi) return;
    const form = fi.closest('form'), f = fi.files && fi.files[0]; if (!f) return;
    if (f.size > 12e6) { toast('Up to 12 MB.', true); return; }
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
      if (kind === 'setup') { await api('POST', '/api/digital/setup', {name: g('name'), size: g('size'), country: g('country').toUpperCase(), currency: g('currency').toUpperCase()});
        await done('Your desk is set up.'); await openChat(true); }
      else if (kind === 'add') { const a = {register: form.dataset.which}; for (const [n, v] of fd.entries()) if (S(v).trim() !== '') a[n] = S(v).trim();
        await run('add', a); await done('Added.'); }
      else if (kind === 'check') { await keepOut('check', 'check', pick(['chain', 'address', 'message'])); }
      else if (kind === 'quote') { await keepOut('quote', 'quote', pick(['invoice', 'coin', 'rate', 'network_fee'])); }
      else if (kind === 'peg') { await run('settings', {pay: {peg: g('peg'), tolerance_pct: g('tolerance_pct')}}); await changed('Saved.'); }
      else if (kind === 'token') { await keepOut('token', 'token', pick(['name', 'chain', 'supply', 'max_top10_pct', 'contract', 'top_holders', 'mint_authority_open', 'freeze_authority_open', 'upgradeable', 'audited', 'team_known', 'liquidity_locked'])); }
      else if (kind === 'reserve') { await run('settings', {reserve: {supply: g('supply'), eligible: g('eligible'), max_per_holder_pct: g('max_per_holder_pct')}}); await changed('Your reserve rules are saved.'); }
      else if (kind === 'watchset') { await run('settings', {linked: g('linked'), window_minutes: g('window_minutes'), spike_multiple: g('spike_multiple')}); await changed('Saved.'); }
      else if (kind === 'settings') { await run('settings', {method: g('method'), tax_year_start: g('tax_year_start'), threshold: g('threshold'), period: g('period')}); await changed('Saved.'); }
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
    const box = $('#dgFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/digital/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'dg' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


