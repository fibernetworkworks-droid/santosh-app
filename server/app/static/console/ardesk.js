/* APP REVIEWER DESK - the App reviewer's own section, like the finance desks (owner: "App reviewer same as finance desks").
   A thin top bar, then the App review chat (its own conversation, kind 'appreview') beside the desk's pages: Today, Review
   something, Reviews, Fix lists, Websites, What is checked, Settings. The pages call /api/ardesk/do/<part>, which runs the App Review
   engine. Hoola only reads her app / code / website, sends it nowhere, and the fix list goes out only on her tap. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['new', 'Review something'], ['reviews', 'Reviews'], ['fixes', 'Fix lists'], ['sites', 'Websites'],
    ['rules', 'What is checked'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What should I fix first?', 'Will Google Play accept my next update?', 'Explain my score in simple words'],
    new: ['What can you review?', 'How do I make a source ZIP of my app?', 'Can you review a private GitHub repo?'],
    reviews: ['What changed since my last review?', 'Explain the most serious risk', 'Which of these can wait?'],
    fixes: ['Write a message for my developer', 'Which fix is quickest?', 'How long will these fixes take?'],
    sites: ['How do I add a DNS TXT record?', 'Why check exposed files only on my own site?', 'Is my website safe for payments?'],
    rules: ['What is the target API rule?', 'Which privacy law applies to me?', 'What does Data safety need?'],
    settings: ['Which country should I set?', 'How do I make a read-only GitHub token?', 'Why does it matter if the app is for children?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sevf: 'open', fid: '', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.ardesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.ardesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'app_review', name: 'Your apps'} : null;
  const CAN = () => !!(ST.d && ST.d.status === 'hired');
  const cur = () => 'USD';
  const money = (v, c, dec = 0) => {
    if (v === null || v === undefined || v === '') return '—';
    const n = Number(v);
    try { return n.toLocaleString(undefined, {style: 'currency', currency: c || cur(), minimumFractionDigits: dec, maximumFractionDigits: dec}); } catch { return n.toFixed(dec); }
  };
  const m2 = (v, c) => money(v, c, 2);
  const num = v => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: 6});
  const pl = (n, w, many) => `${num(n)} ${Number(n) === 1 ? w : (many || w + 's')}`;
  const dmy = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 10) + 'T00:00').toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch { return d; } };
  const dt = d => { if (!d) return '—'; try { return new Date(String(d).slice(0, 16).replace(' ', 'T')).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); } catch { return d; } };
  const cap = s => S(s).charAt(0).toUpperCase() + S(s).slice(1);
  const run = (part, a) => api('POST', '/api/ardesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/ardesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your App reviewer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="arHire">Hire the App reviewer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#arHire').onclick = async () => { try { await api('POST', '/api/employees/app_review/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">App reviewer</div><div class="sd-site" id="arSite"></div></div>
          <span id="arState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="App review chat">
          <div class="sd-chathead"><div class="t"><b>App review chat</b><span>Ask what to fix first or why Play might reject an update - or drop a screenshot of a rejection email here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="arFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="arPick" multiple hidden accept="image/*,.pdf,.csv,.xlsx,.txt,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="App review desk" id="sdTabs"></nav>
          <div id="arPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola only reads your app, sends it nowhere, and the fix list goes out only on your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask what to fix first…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#arPick').click()});
    $('#arPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.ardesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.ardesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/ardesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#arPage').addEventListener('click', onPageClick);
    $('#arPage').addEventListener('submit', onSubmit);
    $('#arPage').addEventListener('change', onChange);
    $('#arPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#arState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), st = k.settings || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : k.waiting ? ['warn', 'Waiting for your tap'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'On it'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#arSite').textContent = [pl((k.targets || []).length, 'app / site', 'apps / sites'), k.avg_score !== null && k.avg_score !== undefined ? 'average ' + k.avg_score + '/100' : '', st.country || ''].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), ser = (k.targets || []).reduce((a, t) => a + ((t.counts || {}).critical || 0) + ((t.counts || {}).high || 0), 0);
    const n = {fixes: k.waiting || '', reviews: ser || '', sites: (k.domains || []).filter(x => !x.verified).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/ardesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#arPage'); if (!box) return;
    const fn = {today: pToday, new: pNew, reviews: pReviews, fixes: pFixes, sites: pSites, rules: pRules, settings: pSettings}[ST.tab] || pToday;
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

  /* ---------------------------------------------------------------- helpers of this desk */
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const st_ = () => K().settings || {};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const filesBox = () => (ST.files_ready || []).length ? `<section class="card"><h2 class="md-h2">Files ready</h2><div class="md-acts" style="justify-content:flex-start;flex-wrap:wrap;gap:6px">${ST.files_ready.map((f, i) => `<button class="btn soft sm" type="button" data-file="${i}">${esc(f.name)}</button>`).join('')}</div><p class="cs-note">Also in your Docs and files.</p></section>` : '';
  const SEV = {critical: ['Critical', 'bad'], high: ['Serious', 'bad'], medium: ['Needs attention', 'warn'], low: ['Minor', ''], info: ['Information', '']};
  const sevTag = s => tag((SEV[s] || [cap(s)])[0], (SEV[s] || ['', ''])[1]);
  const KIND = {apk: 'Android app', aab: 'App bundle', source: 'Source code', repo: 'GitHub repo', web: 'Website'};
  const scoreCls = v => v === null || v === undefined ? '' : v >= 80 ? 'cs-pos' : v >= 50 ? '' : 'cs-neg';
  const counts = c => ['critical', 'high', 'medium', 'low'].filter(s => (c || {})[s]).map(s => `${num(c[s])} ${(SEV[s] || [s])[0].toLowerCase()}`).join(' · ') || 'no open risks';
  const serious = c => ((c || {}).critical || 0) + ((c || {}).high || 0);
  const HST = {card: ['Waiting for your tap', 'warn'], sent: ['Sent', 'ok'], rejected: ['Not sent', ''], failed: ['Not sent - see why', 'bad']};
  const sevRing = (c, label) => ring([['Critical', c.critical || 0, 'ar-crit'], ['Serious', c.high || 0, 'ar-high'], ['Needs attention', c.medium || 0, 'ar-med'],
    ['Minor', c.low || 0, 'ar-low']], num(serious(c)), 'serious', label);

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), tg = k.targets || [], tot = k.totals || {};
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order: nothing serious is open and every review is recent.';
    const tiles = [
      `<div class="k"><div class="l">Apps and sites</div><div class="v">${esc(num(tg.length))}</div><div class="s">${esc(pl((k.reviews || []).length, 'review'))} so far</div></div>`,
      `<div class="k"><div class="l">Average score</div><div class="v ${scoreCls(k.avg_score)}">${k.avg_score === null || k.avg_score === undefined ? '—' : esc(num(k.avg_score)) + '<small>/100</small>'}</div><div class="s">the latest review of each</div></div>`,
      `<div class="k${serious(tot) ? ' low bad' : ''}"><div class="l">Serious risks open</div><div class="v">${esc(num(serious(tot)))}</div><div class="s">${esc(num(tot.critical || 0))} critical</div></div>`,
      `<div class="k${k.waiting ? ' low bad' : ''}"><div class="l">Fix-list cards</div><div class="v">${esc(num(k.waiting || 0))}</div><div class="s">go out only on your tap</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Open risks by how serious</h2>${sevRing(tot, 'Open risks by severity') || empty('No open risks. Review an app to see them here.')}
          <p class="cs-note">Google Play now needs target API ${esc(k.play_target)} for every new app and update. Policies checked ${esc(dmy(k.checked_on))}.</p></section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Your apps and sites</h2><div class="r"><button class="btn soft sm" type="button" data-go="new">Review something</button></div></div>
        ${tg.length ? `<div class="ar-grid">${tg.map(t => targetCard(t)).join('')}</div>` : empty('Nothing reviewed yet. Upload your APK / AAB / source ZIP, give a GitHub repo or your website.')}</section>`;
  }
  function targetCard(t) {
    const k = K(), tr = (k.trend || {})[t.target] || [], f = (k.facts || {})[t.target] || {};
    const sub = t.kind === 'web' ? (f.host || '') : [f.package, f.version_name ? 'v' + f.version_name : '', f.target_sdk ? 'targets API ' + f.target_sdk : ''].filter(Boolean).join(' · ');
    const low = f.target_sdk && Number(f.target_sdk) < Number(k.play_target);
    return `<article class="ar-tg"><div class="h"><div style="min-width:0"><b>${esc(t.title)}</b><span class="mut">${esc(KIND[t.kind] || t.kind)}${sub ? ' · ' + esc(sub) : ''}</span></div>
      <div class="sc ${scoreCls(t.score)}">${esc(num(t.score))}<small>/100</small></div></div>
      <div class="ar-sev">${['critical', 'high', 'medium', 'low'].map(s => `<span class="${s}"><b>${esc(num((t.counts || {})[s] || 0))}</b>${esc((SEV[s] || [s])[0])}</span>`).join('')}</div>
      ${low ? `<p class="cs-neg" style="margin:0;font-size:13px">Targets API ${esc(f.target_sdk)} - Play needs ${esc(k.play_target)} for an update.</p>` : ''}
      ${tr.length > 1 ? line(tr.map(x => [x[0], x[1]]), 'Score over reviews', v => num(v) + '/100', 'ar-trend') : `<p class="mut" style="margin:0;font-size:13px">One review so far (${esc(t.number)}, ${esc(ago(t.created_at))}). Review again after a fix to see the score move.</p>`}
      <div class="md-acts"><span class="mut" style="font-size:13px">${esc(t.number)} · ${esc(ago(t.created_at))}</span><button class="btn soft sm" type="button" data-open="${esc(t.id)}">Open the review</button></div></article>`;
  }

  /* ---------------------------------------------------------------- new review */
  function pNew() {
    const s = st_(), gh = s.github || {};
    return `<div><h1 class="sd-h">Review something</h1><p class="lead">Hoola reads it without running it and sends it nowhere. A second review of the same app or site shows what you fixed.</p></div>${ro()}
      ${ST.busy ? `<section class="card ar-busy"><span class="cs-dot"></span><span>${esc(ST.busy)}</span></section>` : ''}
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Your app file</h2><p class="mut" style="margin:0 0 10px;font-size:14px">An APK, AAB or XAPK, or a ZIP of the source code (Android, Flutter, React Native, iOS or web).</p>
          ${CAN() ? `<form data-form="upload" class="ar-form"><label class="ar-drop"><input type="file" name="file" accept=".apk,.aab,.xapk,.apks,.zip" required>
            <span><b>Choose the file</b><em>It is kept on the server for 7 days, then removed.</em></span></label>
            <div class="md-acts"><span></span><button class="btn" type="submit">Review the file</button></div></form>` : ''}</section>
        <section class="card"><h2 class="md-h2">A GitHub repo</h2><p class="mut" style="margin:0 0 10px;font-size:14px">${gh.joined ? `Private repos work through your connection (${esc(gh.label || 'read-only token')}).` : 'Public repos work without a token. For a private one, connect GitHub in Settings.'}</p>
          ${CAN() ? `<form data-form="repo" class="ar-form"><label class="ins-lab">Repo<input class="in" name="repo" placeholder="owner/name or a github.com link" required></label>
            <label class="ins-lab">Branch (optional)<input class="in" name="ref" placeholder="main"></label>
            <div class="md-acts"><span></span><button class="btn" type="submit">Review the repo</button></div></form>` : ''}</section></div>
      <section class="card"><h2 class="md-h2">Your website</h2><p class="mut" style="margin:0 0 10px;font-size:14px">HTTPS, security headers, cookies, mixed content and the certificate. Hidden files (.git, .env, backups) are checked only on a website you verified on the Websites page.</p>
        ${CAN() ? `<form data-form="web" class="ar-form ar-row"><label class="ins-lab" style="flex:1">Address<input class="in" name="url" placeholder="your-shop.com" required></label>
          <button class="btn" type="submit">Review the website</button></form>` : ''}</section>
      <p class="cs-note">For a stranger's APK ("is this app safe to install?") use App Jaanch in the Hoola chat - this desk is for your own app.</p>`;
  }

  /* ---------------------------------------------------------------- reviews */
  function pReviews() {
    if (ST.arg) return pReview(ST.arg);
    const rs = K().reviews || [];
    return `<div><h1 class="sd-h">Reviews</h1><p class="lead">${rs.length ? esc(pl(rs.length, 'review')) + ', newest first.' : 'No reviews yet.'}</p></div>
      <section class="card">${rs.length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Review</th><th>What</th><th class="r">Score</th><th>Open risks</th><th>Since the last one</th><th>When</th><th></th></tr></thead><tbody>${rs.map(r => {
        const c = r.compare || {};
        return `<tr><td><b>${esc(r.number)}</b></td><td>${esc(r.title)}<div class="mut" style="font-size:12px">${esc(KIND[r.kind] || r.kind)}</div></td><td class="r"><b class="${scoreCls(r.score)}">${esc(num(r.score))}</b></td>
          <td>${esc(counts(r.counts))}</td><td>${c.previous ? esc(`${(c.fixed || []).length} fixed · ${c.still_open || 0} open · ${c.new || 0} new`) : '<span class="mut">first review</span>'}</td>
          <td>${esc(dmy(r.created_at))}</td><td class="r"><button class="btn soft sm" type="button" data-open="${esc(r.id)}">Open</button></td></tr>`; }).join('')}</tbody></table></div>`
        : `${empty('Nothing reviewed yet.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="new">Review something</button></div>`}</section>`;
  }
  function pReview(id) {
    const v = lazyOut('v:' + id, 'review_get', {id});
    const back = `<div><button class="btn soft sm" type="button" data-go="reviews">${svg(IC.back)}<span>All reviews</span></button></div>`;
    if (!v) return back + loading();
    if (v.error) return back + `<section class="card">${err(v)}</section>`;
    const c = v.compare || {}, f = v.facts || {}, risks = v.risks || [];
    const shown = risks.filter(r => ST.sevf === 'all' ? true : ST.sevf === 'ignored' ? r.status === 'ignored' : ST.sevf === 'serious' ? ['critical', 'high'].includes(r.sev) && r.status !== 'ignored' : r.status !== 'ignored');
    const facts = [['Package', f.package], ['Version', f.version_name], ['Targets API', f.target_sdk], ['Minimum API', f.min_sdk], ['Built with', f.built_with],
      ['Repo', f.repo], ['Website', f.host], ['SDKs found', (f.sdks || []).map(x => x.name || x).slice(0, 12).join(', ')]].filter(x => x[1] !== undefined && x[1] !== null && x[1] !== '');
    return `${back}
      <div class="ar-head"><div><h1 class="sd-h">${esc(v.title)}</h1><p class="lead">${esc(v.number)} · ${esc(KIND[v.kind] || v.kind)} · ${esc(dmy(v.created_at))}</p></div>
        <div class="ar-score ${scoreCls(v.score)}"><b>${esc(num(v.score))}</b><span>/100</span></div></div>
      <section class="card"><p style="margin:0 0 12px">${esc(v.say)}</p>
        <div class="ar-sev big">${['critical', 'high', 'medium', 'low'].map(s => `<span class="${s}"><b>${esc(num((v.counts || {})[s] || 0))}</b>${esc((SEV[s] || [s])[0])}</span>`).join('')}</div>
        ${c.previous ? `<div class="ar-cmp"><div><b class="cs-pos">${esc(num((c.fixed || []).length))}</b><span>fixed since ${esc(c.previous)}</span></div><div><b>${esc(num(c.still_open || 0))}</b><span>still open</span></div><div><b class="${c.new ? 'cs-neg' : ''}">${esc(num(c.new || 0))}</b><span>new</span></div><div><b>${esc(num(c.previous_score))} → ${esc(num(v.score))}</b><span>score</span></div></div>
          ${(c.fixed || []).length ? `<p class="mut" style="margin:10px 0 0;font-size:13px">Fixed: ${esc(c.fixed.slice(0, 5).map(x => x.title).join('; '))}${c.fixed.length > 5 ? esc(` and ${c.fixed.length - 5} more`) : ''}.</p>` : ''}` : ''}
        ${CAN() ? `<div class="md-acts" style="flex-wrap:wrap;gap:6px;justify-content:flex-start;margin-top:14px">
          <button class="btn" type="button" data-act="files" data-id="${esc(v.id)}">Make the report (PDF + Excel)</button>
          <button class="btn soft" type="button" data-fix="${esc(v.id)}">See the fix list</button>
          ${ask(`review ${v.number} ${v.title}`)}</div>` : ''}</section>
      ${filesBox()}
      ${facts.length ? `<section class="card"><h2 class="md-h2">What Hoola read</h2><dl class="ar-facts">${facts.map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join('')}</dl>
        ${(v.limits || []).length ? `<p class="cs-note">Limits of this review: ${esc(v.limits.join(' '))}</p>` : ''}</section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Risks</h2><div class="r"><select class="in sm" data-sevf="1" aria-label="Show">
          ${[['open', 'Open'], ['serious', 'Serious only'], ['ignored', 'Marked as intended'], ['all', 'All']].map(([a, b]) => `<option value="${a}"${ST.sevf === a ? ' selected' : ''}>${b}</option>`).join('')}</select></div></div>
        ${shown.length ? shown.map(r => riskRow(v, r)).join('') : empty(ST.sevf === 'ignored' ? 'Nothing marked as intended.' : 'No risks here.')}</section>`;
  }
  function riskRow(v, r) {
    const key = 'r:' + v.id + ':' + r.key, ev = r.evidence || [];
    return `<details class="ar-risk ${esc(r.sev)}${r.status === 'ignored' ? ' ign' : ''}" data-key="${esc(key)}"${ST.open.has(key) ? ' open' : ''}>
      <summary><span class="t"><b>${esc(r.title)}</b><span class="mut">${esc(r.area_label)}${r.masvs ? ' · ' + esc(r.masvs) : ''}</span></span>
        <span class="tags">${sevTag(r.sev)}${r.change === 'new' && (v.compare || {}).previous ? tag('New', 'warn') : ''}${r.check ? tag('Check this', 'warn') : ''}${r.status === 'ignored' ? tag('Intended', '') : ''}</span></summary>
      <div class="b"><p>${esc(r.explain)}</p>
        ${r.check ? `<p class="cs-note">This law was not checked by Hoola for your country - treat it as a starting point and check it.</p>` : ''}
        ${ev.length ? `<h3>Where</h3><ul class="ar-ev">${ev.slice(0, 8).map(e => `<li><code>${esc(e.where)}${e.line ? ':' + esc(e.line) : ''}</code>${e.text ? ` <span class="mut">${esc(S(e.text).slice(0, 160))}</span>` : ''}</li>`).join('')}</ul>${ev.length > 8 ? `<p class="mut" style="font-size:13px">and ${esc(num(ev.length - 8))} more</p>` : ''}` : ''}
        <h3>How to fix it</h3><p>${esc(r.fix)}</p>
        ${r.snippet && r.snippet.code ? `<pre class="ar-code"><code>${esc(r.snippet.code)}</code></pre>` : ''}
        ${(r.sources || []).length ? `<p class="mut" style="font-size:13px;margin:8px 0 0">Source: ${r.sources.map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a> (checked ${esc(dmy(s.date))})`).join('; ')}</p>` : ''}
        ${r.note ? `<p class="mut" style="font-size:13px">Your note: ${esc(r.note)}</p>` : ''}
        ${CAN() ? (r.status === 'ignored' ? `<div class="md-acts"><span></span><button class="btn soft sm" type="button" data-reopen="${esc(r.key)}" data-id="${esc(v.id)}">Open it again</button></div>`
          : r.sev === 'info' ? '' : `<form data-form="mark" data-which="${esc(r.key)}" data-id="${esc(v.id)}" class="ar-row"><label class="ins-lab" style="flex:1">It is intended because${r.sev === 'critical' ? ' (needed)' : ' (optional)'}<input class="in" name="note" maxlength="300" placeholder="For example: only our staff install this build"></label>
            <button class="btn soft sm" type="submit">Mark as intended</button>${ask(r.title)}</form>`) : ''}</div></details>`;
  }

  /* ---------------------------------------------------------------- fix lists and cards */
  function pFixes() {
    const k = K(), cards = k.handoffs || [], waiting = cards.filter(h => h.status === 'card'), done = cards.filter(h => h.status !== 'card');
    const rid = ST.fid || ((k.reviews || [])[0] || {}).id || '';
    const fl = rid ? lazyOut('f:' + rid, 'fixlist', {id: rid}) : null, rv = (k.reviews || []).find(r => r.id === rid) || {};
    return `<div><h1 class="sd-h">Fix lists</h1><p class="lead">The tasks for your developer, each with where it is, what to do and when it counts as done. Nothing goes to anyone without your tap.</p></div>${ro()}
      ${waiting.length ? `<section class="card ar-wait"><h2 class="md-h2">Waiting for your tap</h2>${waiting.map(h => `<div class="ar-card"><div style="flex:1;min-width:0"><b>${esc(pl(h.count, 'task'))} from ${esc(h.review)} ${esc(h.title)}</b>
          <span class="mut">${h.to === 'devsahayak' ? 'To the Developer Assistant: it prepares the changes in your code, which you approve there.' : 'To your developer: Hoola makes the message, you send it.'}</span></div>
          ${CAN() ? `<div class="md-acts" style="gap:6px"><button class="btn soft sm" type="button" data-dec="${esc(h.id)}" data-hash="${esc(h.hash)}" data-yes="0">Not now</button><button class="btn sm" type="button" data-dec="${esc(h.id)}" data-hash="${esc(h.hash)}" data-yes="1">Send it</button></div>` : ''}</div>`).join('')}</section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">${rv.number ? esc(rv.number) + ' · ' + esc(rv.title) : 'Fix list'}</h2>
          ${(k.reviews || []).length > 1 ? `<div class="r"><select class="in sm" data-fsel="1" aria-label="Which review">${k.reviews.map(r => `<option value="${esc(r.id)}"${r.id === rid ? ' selected' : ''}>${esc(r.number)} ${esc(r.title)}</option>`).join('')}</select></div>` : ''}</div>
        ${!rid ? empty('Review something first.') : !fl ? '<p class="mut" style="margin:0">Working it out…</p>' : fl.error ? err(fl)
          : !(fl.tasks || []).length ? empty('Nothing to fix: no open risk in this review.')
          : `<ol class="ar-tasks">${fl.tasks.map(t => `<li><div class="h"><b>${esc(t.title)}</b>${sevTag(t.severity)}</div><p>${esc(t.do)}</p>${(t.where || []).length ? `<p class="mut"><code>${esc(t.where.slice(0, 4).join(', '))}</code></p>` : ''}<p class="mut">Done when: ${esc(t.done_when)}</p></li>`).join('')}</ol>
            ${CAN() ? `<div class="md-acts" style="flex-wrap:wrap;gap:6px"><button class="btn soft sm" type="button" data-copy="${esc(rid)}">Copy as text</button>
              <button class="btn soft sm" type="button" data-hand="${esc(rid)}" data-to="developer">Prepare a message for my developer</button>
              <button class="btn sm" type="button" data-hand="${esc(rid)}" data-to="devsahayak">Give it to the Developer Assistant</button></div>
              <p class="cs-note">Either button only makes a card above - it goes out when you tap Send it.</p>` : ''}`}</section>
      ${done.length ? `<section class="card"><h2 class="md-h2">Earlier cards</h2>${done.map(h => `<div class="cs-row"><span class="cs-dot${h.status === 'failed' ? ' bad' : ''}"></span><span style="flex:1">${esc(h.review)} · ${esc(pl(h.count, 'task'))} · ${h.to === 'devsahayak' ? 'Developer Assistant' : 'your developer'}${(h.result || {}).error ? ' - ' + esc(h.result.error) : ''}</span>
          ${tag((HST[h.status] || [h.status])[0], (HST[h.status] || ['', ''])[1])}${(h.result || {}).wa ? `<a class="btn soft sm" href="${esc(h.result.wa)}" target="_blank" rel="noopener noreferrer">Open in WhatsApp</a>` : ''}</div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- websites */
  function pSites() {
    const k = K(), ds = k.domains || [], web = (k.reviews || []).filter(r => r.kind === 'web');
    return `<div><h1 class="sd-h">Websites</h1><p class="lead">Show Hoola a website is yours and the deeper checks (exposed .git, .env, backups) run on it too. Without it, only what any visitor sees is checked.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Your websites</h2>${ds.length ? ds.map(d => `<div class="ar-dom"><div class="h"><b>${esc(d.host)}</b>${d.verified ? tag('Verified' + (d.method ? ' by ' + (d.method === 'dns' ? 'DNS' : 'file') : ''), 'ok') : tag('Not verified yet', 'warn')}</div>
          ${d.verified ? `<p class="mut" style="margin:0;font-size:13px">Verified ${esc(dmy(d.verified_at))}.</p>` : `<div class="ar-how"><div><span class="mut">Either a DNS TXT record</span><code>${esc(d.how.dns.name)}</code><code>${esc(d.how.dns.value)}</code></div>
            <div><span class="mut">or a file</span><code>${esc(d.how.file.url)}</code><code>${esc(d.how.file.content)}</code></div></div>
            ${CAN() ? `<div class="md-acts"><span class="mut" style="font-size:13px">A DNS change can take some time to show.</span><button class="btn soft sm" type="button" data-verify="${esc(d.host)}">Verify now</button></div>` : ''}`}</div>`).join('') : empty('No website added yet.')}
        ${CAN() ? `<form data-form="domain" class="ar-row" style="margin-top:12px"><label class="ins-lab" style="flex:1">Add your website<input class="in" name="url" placeholder="your-shop.com" required></label><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
      ${web.length ? `<section class="card"><h2 class="md-h2">Website reviews</h2>${web.map(r => `<div class="cs-row"><span class="cs-dot${serious(r.counts) ? ' bad' : ''}"></span><span style="flex:1"><b>${esc(r.title)}</b> <span class="mut">${esc(r.number)} · ${esc(dmy(r.created_at))} · ${esc(counts(r.counts))}</span></span><b class="${scoreCls(r.score)}">${esc(num(r.score))}</b><button class="btn soft sm" type="button" data-open="${esc(r.id)}">Open</button></div>`).join('')}</section>` : ''}`;
  }

  /* ---------------------------------------------------------------- rules */
  function pRules() {
    const r = lazyOut('rules', 'rules', {});
    if (!r) return '<div><h1 class="sd-h">What is checked</h1></div>' + loading();
    if (r.error) return `<section class="card">${err(r)}</section>`;
    const c = (st_().country || 'IN').toUpperCase(), pt = r.play_target || {};
    return `<div><h1 class="sd-h">What is checked</h1><p class="lead">${esc(num(r.areas.reduce((s, a) => s + a.checks.length, 0)))} checks in ${esc(num(r.areas.length))} areas, policies checked ${esc(dmy(r.checked_on))}. Play changes its rules often - review again before every release.</p></div>
      <section class="card"><h2 class="md-h2">Google Play target API</h2><div class="ar-facts" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
        ${[['New apps and updates', 'API ' + pt.new_and_updates], ['Existing apps, at least', 'API ' + pt.existing_min], ['Since', dmy(pt.since)], ['Extension until', dmy(pt.extension_until)], ['Wear OS / Auto', 'API ' + pt.wear_auto], ['TV / XR', 'API ' + pt.tv_xr]].map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`).join('')}</div></section>
      <section class="card"><h2 class="md-h2">Privacy, children and payment law by country</h2><p class="mut" style="margin:0 0 10px;font-size:14px">Your country (${esc(c)}) decides which law is named in a review. Only India's is checked; the others are named as a starting point and marked "check this".</p>
        <div class="iv-tw"><table class="tb"><thead><tr><th>Country</th><th>Privacy</th><th>Children</th><th>Payments</th><th></th></tr></thead><tbody>${r.laws.map(l => `<tr${l.country === c ? ' class="ar-me"' : ''}><td><b>${esc(l.label)}</b></td><td>${esc(l.privacy)}</td><td>${esc(l.children)}</td><td>${esc(l.payments)}</td><td>${l.checked ? tag('Checked', 'ok') : tag('Check this', 'warn')}</td></tr>`).join('')}</tbody></table></div>
        <p class="cs-note">EU covers the 27 member states plus Iceland, Liechtenstein and Norway. Any other country: "your country's data protection law", always marked check this.</p></section>
      ${r.areas.map(a => `<details class="card ar-area" data-key="area:${esc(a.area)}"${ST.open.has('area:' + a.area) ? ' open' : ''}><summary><h2 class="md-h2" style="margin:0">${esc(a.label)}</h2><span class="mut">${esc(pl(a.checks.length, 'check'))}</span></summary>
        <div class="iv-tw"><table class="tb"><tbody>${a.checks.map(x => `<tr><td>${esc(x.title)}</td><td>${sevTag(x.sev)}</td><td class="mut">${esc(x.masvs || '')}</td></tr>`).join('')}</tbody></table></div></details>`).join('')}
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never">${r.never.map(n => `<li>${esc(n)}</li>`).join('')}</ul></section>
      <section class="card"><h2 class="md-h2">Sources</h2><ul class="ar-src">${r.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a><span class="mut"> · checked ${esc(dmy(s.date))}</span></li>`).join('')}</ul></section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), gh = s.github || {}, lw = s.law || {};
    const opt = (v, cur) => `value="${esc(v)}"${S(cur) === v ? ' selected' : ''}`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">About your app, and where you are.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Your app</h2>
        <form data-form="arset" class="ar-set"><label class="ins-lab">Country (two letters)<input class="in" name="country" maxlength="2" value="${esc(s.country || '')}" placeholder="IN, US, GB, DE…"></label>
          <label class="ins-lab">Built with<select class="in" name="stack"><option ${opt('', s.stack)}>Find out from the code</option><option ${opt('android', s.stack)}>Android (Kotlin / Java)</option><option ${opt('flutter', s.stack)}>Flutter</option><option ${opt('react_native', s.stack)}>React Native</option><option ${opt('web', s.stack)}>Website</option></select></label>
          <label class="ins-lab">Your developer's name (on the fix list)<input class="in" name="developer" maxlength="120" value="${esc(s.developer || '')}"></label>
          <label class="ar-chk"><input type="checkbox" name="kids"${s.kids ? ' checked' : ''}> The app is (also) for children under 18</label>
          <label class="ar-chk"><input type="checkbox" name="ios"${s.ios ? ' checked' : ''}> There is an iPhone version too</label>
          ${CAN() ? '<div class="md-acts"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <p class="cs-note">${esc(lw.say || '')}${lw.checked ? '' : ' - named as a starting point only.'}</p></section>
      <section class="card"><h2 class="md-h2">GitHub (private repos)</h2>
        ${gh.joined ? `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">Connected: ${esc(gh.label || 'read-only token')} (sealed, never shown again)</span>${CAN() ? '<button class="btn soft sm" type="button" data-act="github_forget">Remove</button>' : ''}</div>`
          : CAN() ? `<form data-form="github" class="ar-row"><label class="ins-lab" style="flex:1">A fine-grained, read-only token<input class="in" name="token" type="password" autocomplete="off" required placeholder="github_pat_…"></label><button class="btn soft" type="submit">Connect</button></form>
            <p class="cs-note">Make it on GitHub with only Contents: Read on the repos to review. Tokens that can write are refused. It is sealed on the server and never shown again - never paste it in the chat.</p>` : ''}</section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  async function getFile(f) {
    try {
      const r = await fetch(f.url, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
      if (!r.ok) throw new Error(`Could not download (${r.status})`);
      const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = f.name || 'file'; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 3000);
    } catch (e) { toast(e.message, true); }
  }
  const fileUrl = f => f.url || '';
  async function reviewed(v, msg) {
    ST.busy = ''; dropO('v:', 'f:'); ST.files_ready = [];
    await refreshDesk(false);
    if (v && v.id) { location.hash = '#/reviews/' + v.id; if (ST.tab === 'reviews') showPage(); }
    else showPage(true);
    toast(msg || (v && v.say) || 'Reviewed.');
  }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { ST.files_ready = []; delete ST.out['v:' + op.dataset.open]; location.hash = '#/reviews/' + op.dataset.open; return; }
    const fx = t.closest('[data-fix]'); if (fx) { ST.fid = fx.dataset.fix; delete ST.out['f:' + ST.fid]; location.hash = '#/fixes'; return; }
    const fl = t.closest('[data-file]'); if (fl) { const f = (ST.files_ready || [])[Number(fl.dataset.file)]; if (f) getFile({...f, url: fileUrl(f)}); return; }
    const btn = t.closest('button');
    try {
      const ro_ = t.closest('[data-reopen]'); if (ro_) { ro_.disabled = true; ST.out['v:' + ro_.dataset.id] = await run('mark', {id: ro_.dataset.id, key: ro_.dataset.reopen, status: 'open'}); await changed('Opened again.'); return; }
      const vf = t.closest('[data-verify]'); if (vf) { vf.disabled = true; toast('Looking for the record…'); const r = await run('domain_verify', {url: vf.dataset.verify}); await changed(r.verified ? 'Verified - the deeper checks will run on it.' : 'Not found yet - a DNS change can take some time.'); return; }
      const cp = t.closest('[data-copy]'); if (cp) { const fl2 = ST.out['f:' + cp.dataset.copy]; try { await navigator.clipboard.writeText((fl2 && fl2.markdown) || ''); toast('Copied.'); } catch { toast('Could not copy here.', true); } return; }
      const hd = t.closest('[data-hand]'); if (hd) { hd.disabled = true; const r = await run('handoff', {id: hd.dataset.hand, to: hd.dataset.to}); await changed(r.say || 'Card made - it waits for your tap.'); $('#sdDesk').scrollTop = 0; return; }
      const dc = t.closest('[data-dec]'); if (dc) {
        const yes = dc.dataset.yes === '1';
        dc.disabled = true;
        const r = await run('decide', {handoff: dc.dataset.dec, hash: dc.dataset.hash, yes});
        if (r.wa) { const w = window.open(r.wa, '_blank', 'noopener'); if (!w) toast('The message is ready - open it from Earlier cards.'); }
        await changed(r.say || (yes ? 'Sent.' : 'Not sent.')); return;
      }
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act;
        if (act === 'github_forget') { if (a.dataset.sure !== '1') { a.dataset.sure = '1'; a.textContent = 'Tap again to remove'; return; } }
        a.disabled = true;
        if (act === 'files') { toast('Making the report…'); const r = await run('files', {id: a.dataset.id}); ST.files_ready = (r.files || []).map(f => ({...f, url: fileUrl(f)})); showPage(true); toast(r.say || 'Files ready.'); }
        else await changed((await run(act, {id: a.dataset.id})).say || 'Done.');
        a.disabled = false;
        return;
      }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.sevf) { ST.sevf = el.value; showPage(true); return; }
    if (el.dataset.fsel) { ST.fid = el.value; showPage(true); return; }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) btn.disabled = true;
    try {
      if (kind === 'upload') {
        const f = fd.get('file'); if (!f || !f.size) throw new Error('Choose the file first.');
        ST.busy = `Uploading ${f.name} (${(f.size / 1048576).toFixed(1)} MB)…`; showPage(true);
        const body = new FormData(); body.append('file', f, f.name);
        const up = await api('POST', '/api/appreview/upload', undefined, {form: body});
        ST.busy = `Reading ${up.name} - a big app can take a minute…`; showPage(true);
        await reviewed(await run('review_file', {file: up.file}));
      }
      else if (kind === 'repo') { ST.busy = `Reading ${g('repo')} - a big repo can take a minute…`; showPage(true); await reviewed(await run('review_repo', {repo: g('repo'), ref: g('ref')})); }
      else if (kind === 'web') { ST.busy = `Checking ${g('url')}…`; showPage(true); await reviewed(await run('review_web', {url: g('url')})); }
      else if (kind === 'mark') { const r = await run('mark', {id: form.dataset.id, key: form.dataset.which, status: 'ignored', note: S(fd.get('note'))}); ST.out['v:' + form.dataset.id] = r; await changed('Marked as intended - later reviews keep it.'); }
      else if (kind === 'domain') { const r = await run('domain_add', {url: g('url')}); await changed(r.verified ? 'Already verified.' : 'Added - now add the record shown and tap Verify now.'); }
      else if (kind === 'arset') { await run('settings', {country: g('country').toUpperCase(), stack: g('stack'), developer: g('developer'), kids: fd.get('kids') === 'on', ios: fd.get('ios') === 'on'}); dropO('v:', 'rules'); await changed('Saved.'); }
      else if (kind === 'github') { const r = await run('github', {token: S(fd.get('token'))}); await changed(r.say || 'Connected.'); }
    } catch (err2) { ST.busy = ''; showPage(true); toast(err2.message, true); }
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
    const box = $('#arFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/ardesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'ar' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


