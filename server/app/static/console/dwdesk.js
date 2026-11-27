/* TECHNICAL WRITER DESK - the Technical writer's own section, like the finance desks (owner: "Technical writer same as finance desks").
   A thin top bar, then the Docs chat (its own conversation, kind 'docs') beside the desk's pages: Today, Write a doc, Docs, Sources,
   Screenshots, Settings. The pages call /api/dwdesk/do/<part>, which runs the docs engine. Hoola writes only what the product has,
   covers personal data in screenshots, and makes nothing public without her tap. */
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

  const TABS = [['today', 'Today'], ['write', 'Write a doc'], ['docs', 'Docs'], ['sources', 'Sources'], ['screens', 'Screenshots'],
    ['settings', 'Settings']];
  const STARTERS = {
    today: ['What should I document first?', 'Which docs are out of date?', 'Summarise my docs for the team'],
    write: ['Write a quick start for new users', 'Write release notes for this version', 'What should a FAQ cover?'],
    docs: ['Make this doc shorter', 'Translate it into Spanish', 'What is still [blank] in it?'],
    sources: ['How do I prove my website is mine?', 'Can you read a private GitHub repo?', 'What can you read from my files?'],
    screens: ['Write the steps for signing up', 'Why is a password not allowed in steps?', 'Which screens need pictures?'],
    settings: ['Which languages should my docs be in?', 'Suggest a tone for my users', 'What should go in the glossary?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', df: 'all', kind: '', prod: '', pk: 'hoola_app', edit: '', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.dwdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.dwdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'docs_writer', name: ((K().settings || {}).product_name) || 'Your product'} : null;
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
  const run = (part, a) => api('POST', '/api/dwdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/dwdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Technical writer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="dwHire">Hire the Technical writer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#dwHire').onclick = async () => { try { await api('POST', '/api/employees/docs_writer/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Technical writer</div><div class="sd-site" id="dwSite"></div></div>
          <span id="dwState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Docs chat">
          <div class="sd-chathead"><div class="t"><b>Docs chat</b><span>Ask for a quick start, a how-to or release notes - or drop a PRD, a spec or an OpenAPI file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="dwFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="dwPick" multiple hidden accept="image/*,.pdf,.csv,.xlsx,.txt,.docx,.md,.json,.yaml,.yml">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Docs desk" id="sdTabs"></nav>
          <div id="dwPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Hoola writes only what your product has and makes nothing public without your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Ask for a doc…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#dwPick').click()});
    $('#dwPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.dwdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.dwdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/dwdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#dwPage').addEventListener('click', onPageClick);
    $('#dwPage').addEventListener('submit', onSubmit);
    $('#dwPage').addEventListener('change', onChange);
    $('#dwPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#dwState'); if (!el) return;
    const k = K(), bad = (k.needs || []).some(x => x.bad), st = k.settings || {};
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : k.waiting ? ['warn', 'Waiting for your tap'] : bad ? ['warn', 'Something needs a look'] : ['ok', 'On it'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#dwSite').textContent = [st.product_name, pl((k.docs || []).length, 'doc'), (st.langs || ['en']).join(', ')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {docs: (k.stale || 0) + (k.waiting || 0) || '', sources: (k.products || []).filter(p => !p.verified).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/dwdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#dwPage'); if (!box) return;
    const fn = {today: pToday, write: pWrite, docs: pDocs, sources: pSources, screens: pScreens, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    box.innerHTML = html;
    if (kept) retype(box, kept);
    loadImgs(box);
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
  /* screenshots need the key: fetched once, shown from a blob */
  const IMG = {};
  const img = (url, alt, cls) => `<img class="${esc(cls || 'dw-img')}" alt="${esc(alt || '')}" data-src="${esc(url)}"${IMG[url] ? ` src="${IMG[url]}"` : ''}>`;
  function loadImgs(box) {
    box.querySelectorAll('img[data-src]:not([src])').forEach(el => {
      const u = el.dataset.src;
      if (IMG[u]) { el.src = IMG[u]; return; }
      fetch(u, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'}).then(r => r.ok ? r.blob() : null)
        .then(b => { if (b) { IMG[u] = URL.createObjectURL(b); box.querySelectorAll(`img[data-src="${CSS.escape(u)}"]`).forEach(x => { x.src = IMG[u]; }); } }).catch(() => {});
    });
  }
  const DST = {draft: ['Draft', ''], ready: ['Ready', 'ok'], stale: ['Out of date', 'warn'], waiting: ['Waiting for your tap', 'warn'], published: ['Public', 'v']};
  const dTag = d => tag((DST[d.status] || [cap(d.status)])[0], (DST[d.status] || ['', ''])[1]);
  const PK = {hoola_app: 'App made in Hoola', hoola_site: 'Website made in Hoola', web: 'Your live website', github: 'GitHub repo', files: 'Your files'};
  const LN = c => ((K().langs || []).find(x => x.code === c) || {}).name || c;
  const BY = {model: 'Written by Hoola', code: 'Made from the code', template: 'From the product facts', her: 'Your words'};
  const prodOpts = sel => (K().products || []).filter(p => p.verified).map(p => `<option value="${esc(p.id)}"${p.id === sel ? ' selected' : ''}>${esc(p.name)}</option>`).join('');
  const langOpts = (sel, only) => (K().langs || []).filter(l => !only || only.includes(l.code)).map(l => `<option value="${esc(l.code)}"${l.code === sel ? ' selected' : ''}>${esc(l.name)}</option>`).join('');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), ds = k.docs || [], ps = k.products || [];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order: every doc is in step with the product.';
    const tiles = [
      `<div class="k"><div class="l">Docs</div><div class="v">${esc(num(ds.length))}</div><div class="s">for ${esc(pl(ps.length, 'product'))}</div></div>`,
      `<div class="k"><div class="l">Public</div><div class="v">${esc(num(k.published || 0))}</div><div class="s">only ever by your tap</div></div>`,
      `<div class="k${k.stale ? ' low bad' : ''}"><div class="l">Out of date</div><div class="v">${esc(num(k.stale || 0))}</div><div class="s">the product changed since</div></div>`,
      `<div class="k${k.waiting ? ' low bad' : ''}"><div class="l">Waiting for your tap</div><div class="v">${esc(num(k.waiting || 0))}</div><div class="s">to go public</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Your docs by kind</h2>${(k.by_kind || []).length ? bars(k.by_kind.map(([n, v]) => [n, v, 'mk-b']), num, 'Docs by kind') : empty('No docs yet.')}
          ${(k.by_lang || []).length ? `<h3 class="dw-h3">In which languages</h3>${bars(k.by_lang.map(([n, v]) => [n, v, 'mk-b']), num, 'Docs by language')}` : ''}</section></div>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Latest docs</h2><div class="r"><button class="btn soft sm" type="button" data-go="write">Write a doc</button></div></div>
        ${ds.length ? docTable(ds.slice(0, 8)) : empty('No docs yet. Connect your product, then write a quick start.')}</section>`;
  }
  function docTable(ds) {
    return `<div class="iv-tw"><table class="tb"><thead><tr><th>Doc</th><th>Kind</th><th>Language</th><th>Status</th><th class="r">Sections</th><th>Updated</th><th></th></tr></thead><tbody>${ds.map(d => `<tr>
      <td><b>${esc(d.title)}</b><div class="mut" style="font-size:12px">${esc(d.number)} · version ${esc(d.version)}</div></td><td>${esc(d.kind_label)}</td><td>${esc(LN(d.lang))}</td>
      <td>${dTag(d)}${d.stale ? ` <span class="mut" style="font-size:12px">${esc(pl(d.stale, 'section'))} old</span>` : ''}</td><td class="r">${esc(num(d.sections))}</td><td>${esc(ago(d.updated_at))}</td>
      <td class="r"><button class="btn soft sm" type="button" data-doc="${esc(d.id)}">Open</button></td></tr>`).join('')}</tbody></table></div>`;
  }

  /* ---------------------------------------------------------------- write */
  function pWrite() {
    const k = K(), ps = (k.products || []).filter(p => p.verified), s = st_(), def = (s.langs || ['en'])[0];
    if (!ps.length) return `<div><h1 class="sd-h">Write a doc</h1><p class="lead">First connect your product - Hoola writes only from it.</p></div>
      <section class="card">${empty((k.products || []).length ? 'Your product is not verified yet: prove it is yours on Sources.' : 'No product connected yet.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="sources">Open Sources</button></div></section>`;
    return `<div><h1 class="sd-h">Write a doc</h1><p class="lead">Hoola writes only what your product really has. Anything it does not know stays [blank] for you to fill.</p></div>${ro()}
      ${ST.busy ? `<section class="card dw-busy"><span class="cs-dot"></span><span>${esc(ST.busy)}</span></section>` : ''}
      <section class="card"><h2 class="md-h2">What kind of doc</h2><div class="dw-kinds">${(k.kinds || []).filter(x => x.id !== 'changelog').map(x => `<label class="dw-kind"><input type="radio" name="dwkind" form="dwWrite" value="${esc(x.id)}"${(ST.kind || 'quickstart') === x.id ? ' checked' : ''}><span><b>${esc(x.label)}</b><em>${esc(x.goal)}</em></span></label>`).join('')}</div></section>
      ${CAN() ? `<section class="card"><form id="dwWrite" data-form="write" class="dw-grid"><label class="ins-lab">Product<select class="in" name="product">${prodOpts(ST.prod || ps[0].id)}</select></label>
        <label class="ins-lab">Language<select class="in" name="lang">${langOpts(def)}</select></label>
        <label class="ins-lab wide">Title (optional)<input class="in" name="title" maxlength="160" placeholder="Getting started with your account"></label>
        <label class="ins-lab wide">What should it cover? (your words)<textarea class="in" name="words" rows="3" placeholder="For shop owners who just signed up: add the first product and share the shop link"></textarea></label>
        <div class="md-acts wide"><span class="mut" style="font-size:13px">Usually under a minute. The doc opens when it is written.</span><button class="btn" type="submit">Write it</button></div></form></section>
      <section class="card"><h2 class="md-h2">Release notes</h2><p class="mut" style="margin:0 0 10px;font-size:14px">From merged pull requests since the last release (GitHub), from what changed in the app or site, or from your words.</p>
        <form data-form="notes" class="dw-grid"><label class="ins-lab">Product<select class="in" name="product">${prodOpts(ps[0].id)}</select></label>
          <label class="ins-lab">Version<input class="in" name="version" placeholder="2.4.0"></label><label class="ins-lab">Language<select class="in" name="lang">${langOpts(def)}</select></label>
          <label class="ins-lab wide">Anything to add (optional)<textarea class="in" name="words" rows="2"></textarea></label>
          <div class="md-acts wide"><span></span><button class="btn soft" type="submit">Write the release notes</button></div></form></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- docs */
  function pDocs() {
    if (ST.arg) return pDoc(ST.arg);
    const ds = (K().docs || []).filter(d => ST.df === 'all' || (ST.df === 'stale' ? d.stale || d.status === 'stale' : d.status === ST.df));
    return `<div class="cs-head"><div><h1 class="sd-h">Docs</h1><p class="lead">${esc(pl((K().docs || []).length, 'doc'))}, newest first.</p></div>
        <div class="r"><select class="in sm" data-df="1" aria-label="Show">${[['all', 'All'], ['draft', 'Drafts'], ['ready', 'Ready'], ['stale', 'Out of date'], ['waiting', 'Waiting for your tap'], ['published', 'Public']].map(([a, b]) => `<option value="${a}"${ST.df === a ? ' selected' : ''}>${b}</option>`).join('')}</select></div></div>
      <section class="card">${ds.length ? docTable(ds) : `${empty('Nothing here.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="write">Write a doc</button></div>`}</section>`;
  }
  function pDoc(id) {
    const v = lazyOut('d:' + id, 'doc_get', {doc: id});
    const back = `<div><button class="btn soft sm" type="button" data-go="docs">${svg(IC.back)}<span>All docs</span></button></div>`;
    if (!v) return back + loading();
    if (v.error) return back + `<section class="card">${err(v)}</section>`;
    const ck = v.check_list || {}, bl = ck.blocking || [], wn = ck.warnings || [], pend = v.pending;
    const langs = (st_().langs || []).filter(x => x !== v.lang);
    return `${back}
      <div class="dw-head"><div><h1 class="sd-h">${esc(v.title)}</h1><p class="lead">${esc(v.number)} · ${esc(v.kind_label)} · ${esc(LN(v.lang))} · version ${esc(v.version)}${v.translation_of ? ' · a translation' : ''}</p></div><div>${dTag(v)}</div></div>
      ${pend && CAN() ? `<section class="card dw-wait"><h2 class="md-h2">Waiting for your tap</h2><p style="margin:0 0 10px">Make it public on ${esc(pend.dest === 'page' ? 'a Hoola docs page (a public link)' : pend.dest === 'github' ? 'GitHub as a pull request in ' + (pend.repo || 'your repo') + ' (you merge it)' : 'your WordPress site as a new page')}?</p>
        ${wn.length ? `<p class="mut" style="font-size:13px;margin:0 0 10px">Still worth a look: ${esc(wn.slice(0, 3).map(x => x.text).join('; '))}</p>` : ''}
        <div class="md-acts" style="gap:6px"><span></span><button class="btn soft sm" type="button" data-dec="${esc(v.id)}" data-hash="${esc(pend.hash)}" data-yes="0">Not now</button><button class="btn sm" type="button" data-dec="${esc(v.id)}" data-hash="${esc(pend.hash)}" data-yes="1">Make it public</button></div></section>` : ''}
      ${v.page ? `<section class="card"><div class="cs-row"><span class="cs-dot"></span><span style="flex:1">Public at <a href="${esc(v.page)}" target="_blank" rel="noopener noreferrer">${esc(v.page)}</a></span>${CAN() ? `<button class="btn soft sm" type="button" data-unpage="${esc(v.id)}">Take it down</button>` : ''}</div></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Checks</h2><div class="r">${CAN() ? `<button class="btn soft sm" type="button" data-act="check" data-id="${esc(v.id)}">Check again</button>` : ''}</div></div>
        ${bl.length ? bl.map(x => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1">${esc(x.text)}</span>${tag('Must fix', 'bad')}</div>`).join('') : ''}
        ${wn.length ? wn.slice(0, 12).map(x => `<div class="cs-row"><span class="cs-dot${x.kind === 'stale' || x.kind === 'fact' ? ' bad' : ''}"></span><span style="flex:1">${esc(x.text)}</span>${x.section ? `<button class="btn soft sm" type="button" data-sec="${esc(x.section)}">Show</button>` : ''}</div>`).join('') : ''}
        ${!bl.length && !wn.length ? empty('No problems found: plain words, no unknown numbers, no personal data.') : ''}
        ${wn.length > 12 ? `<p class="mut" style="font-size:13px">and ${esc(num(wn.length - 12))} more</p>` : ''}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Do something with it</h2><div class="dw-acts">
        <form data-form="publish" data-id="${esc(v.id)}" class="ar-row"><label class="ins-lab" style="flex:1">Make it public on<select class="in" name="dest"><option value="page">A Hoola docs page (a link)</option><option value="github">GitHub (a pull request)</option><option value="wordpress">My WordPress site</option></select></label><button class="btn soft" type="submit"${bl.length ? ' disabled title="Fix the must-fix items first"' : ''}>Ask me first</button></form>
        <form data-form="translate" data-id="${esc(v.id)}" class="ar-row"><label class="ins-lab" style="flex:1">Translate into<select class="in" name="to">${langOpts(langs[0] || (v.lang === 'en' ? 'es' : 'en'))}</select></label><button class="btn soft" type="submit">Translate</button></form>
        <form data-form="revise" data-id="${esc(v.id)}" class="ar-row"><label class="ins-lab" style="flex:1">Change the whole doc<input class="in" name="instruction" placeholder="Shorter steps, friendlier tone"></label><button class="btn soft" type="submit">Change it</button></form>
        <div class="md-acts" style="justify-content:flex-start;gap:6px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-files="md,docx,pdf" data-id="${esc(v.id)}">Word + PDF + Markdown</button>
          <button class="btn soft sm" type="button" data-del="${esc(v.id)}">Delete the doc</button>${ask(`doc ${v.number} ${v.title}`)}</div></div></section>` : ''}
      ${filesBox()}
      <section class="card"><h2 class="md-h2">${esc(pl(v.section_list.length, 'section'))}</h2>${v.section_list.map(s => secRow(v, s)).join('') || empty('The doc is empty.')}</section>
      ${(v.versions || []).length ? `<section class="card"><h2 class="md-h2">Earlier versions</h2>${v.versions.slice().reverse().map(x => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">Version ${esc(x.version)} · ${esc(x.why || '')}</span><span class="mut" style="font-size:13px">${esc(dt(x.at))}</span></div>`).join('')}</section>` : ''}`;
  }
  function secRow(v, s) {
    const key = 's:' + v.id + ':' + s.id, editing = ST.edit === key;
    return `<details class="dw-sec${s.stale ? ' stale' : ''}" id="sec-${esc(s.id)}" data-key="${esc(key)}"${ST.open.has(key) || editing ? ' open' : ''}>
      <summary><span class="t"><b>${esc(s.title)}</b><span class="mut">${esc(BY[s.by] || s.by || '')}${s.edited ? ' · edited by you' : ''}</span></span>${s.stale ? tag('Out of date', 'warn') : ''}</summary>
      <div class="b">${s.stale && s.why ? `<p class="cs-note">Why: ${esc(s.why)}</p>` : ''}
        ${editing ? `<form data-form="edit" data-id="${esc(v.id)}" data-which="${esc(s.id)}" class="dw-edit"><label class="ins-lab">Heading<input class="in" name="title" value="${esc(s.title)}"></label>
            <label class="ins-lab">Text (Markdown)<textarea class="in" name="body" rows="10">${esc(s.body)}</textarea></label>
            <div class="md-acts" style="gap:6px"><span class="mut" style="font-size:13px">Your words are kept: an update never overwrites them by itself.</span><button class="btn soft sm" type="button" data-cancel="1">Cancel</button><button class="btn sm" type="submit">Save</button></div></form>`
          : `<div class="dw-body">${md(s.body)}</div>${(s.shots || []).length ? `<div class="dw-shots">${s.shots.map(x => `<figure>${img(x.url, x.alt)}<figcaption>${esc(x.alt)}</figcaption></figure>`).join('')}</div>` : ''}
            ${CAN() ? `<div class="md-acts" style="gap:6px"><span></span><button class="btn soft sm" type="button" data-editsec="${esc(key)}">Edit</button></div>` : ''}`}</div></details>`;
  }
  /* a small, safe Markdown view: escaped first, then headings / lists / bold / code / [blank] */
  function md(t) {
    const lines = esc(S(t)).replace(/!\[[^\]]*\]\([^)]*\)/g, '').split('\n'), out = [];
    let list = '';
    const inl = s => s.replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/\[blank\]/g, '<mark class="dw-blank">[blank]</mark>');
    for (const l of lines) {
      const m = l.match(/^\s*(\d+\.|[-*])\s+(.*)$/);
      if (m) { const tg = m[1].endsWith('.') ? 'ol' : 'ul'; if (list !== tg) { if (list) out.push(`</${list}>`); out.push(`<${tg}>`); list = tg; } out.push(`<li>${inl(m[2])}</li>`); continue; }
      if (list) { out.push(`</${list}>`); list = ''; }
      const h = l.match(/^(#{1,4})\s+(.*)$/);
      if (h) out.push(`<h4>${inl(h[2])}</h4>`); else if (l.trim()) out.push(`<p>${inl(l)}</p>`);
    }
    if (list) out.push(`</${list}>`);
    return out.join('');
  }

  /* ---------------------------------------------------------------- sources */
  function pSources() {
    const ps = K().products || [], gh = st_().github || {};
    return `<div><h1 class="sd-h">Sources</h1><p class="lead">What your docs are about. Hoola reads them; it never runs your code or changes your product.</p></div>${ro()}
      ${ST.busy ? `<section class="card dw-busy"><span class="cs-dot"></span><span>${esc(ST.busy)}</span></section>` : ''}
      ${ps.length ? ps.map(p => `<section class="card dw-prod"><div class="cs-head"><div style="min-width:0"><h2 class="md-h2" style="margin:0">${esc(p.name)}</h2><span class="mut" style="font-size:13px">${esc(PK[p.kind] || p.kind)}${p.host ? ' · ' + esc(p.host) : p.ref && p.kind === 'github' ? ' · ' + esc(p.ref) : ''}${p.version ? ' · version ' + esc(p.version) : ''}</span></div>
          <div class="r">${p.verified ? tag('Yours - verified', 'ok') : tag('Not verified yet', 'warn')}</div></div>
        <div class="dw-pstat"><span><b>${esc(num(p.parts))}</b> parts read</span><span><b>${esc(ago(p.checked_at))}</b> last read</span><span><b>${p.auto_sync ? 'On' : 'Off'}</b> keeps docs in step</span></div>
        ${!p.verified && p.verify ? `<p style="margin:0 0 8px;font-size:14px">${esc(p.verify.say)}</p><div class="ar-how"><div><span class="mut">A meta tag in the home page</span><code>${esc(p.verify.meta)}</code></div><div><span class="mut">or a file</span><code>${esc(p.verify.file)}</code></div><div><span class="mut">or a DNS record</span><code>${esc(p.verify.dns)}</code></div></div>` : ''}
        ${CAN() ? `<div class="md-acts" style="gap:6px;flex-wrap:wrap"><span></span>${!p.verified ? `<button class="btn sm" type="button" data-pact="verify" data-id="${esc(p.id)}">Check the proof</button>` : `<button class="btn soft sm" type="button" data-pact="snapshot" data-id="${esc(p.id)}">Read it again</button><button class="btn soft sm" type="button" data-pact="sync" data-id="${esc(p.id)}">Bring the docs in step</button>${p.kind === 'web' ? `<button class="btn soft sm" type="button" data-go="screens">Screenshots</button>` : ''}`}
          <button class="btn soft sm" type="button" data-pact="remove_product" data-id="${esc(p.id)}">Remove</button></div>` : ''}</section>`).join('') : ''}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Connect a product</h2><form data-form="addprod" class="dw-grid">
        <label class="ins-lab">What it is<select class="in" name="kind">${Object.entries(PK).map(([a, b]) => `<option value="${a}"${ST.pk === a ? ' selected' : ''}>${esc(b)}</option>`).join('')}</select></label>
        <label class="ins-lab">${esc({hoola_app: 'Its app number (A-…)', hoola_site: 'Its site number (S-…)', web: 'Its address', github: 'owner/name or a github.com link', files: 'File ids from the chat (comma separated)'}[ST.pk || 'hoola_app'])}<input class="in" name="ref" required placeholder="${esc({web: 'https://your-shop.com', github: 'me/my-app'}[ST.pk] || '')}"></label>
        <label class="ins-lab">Name (optional)<input class="in" name="name" maxlength="80"></label>
        <div class="md-acts wide"><span class="mut" style="font-size:13px">${ST.pk === 'web' ? 'You will prove the site is yours with a meta tag, a file or a DNS record.' : ST.pk === 'files' ? 'Drop a PRD, Word, PDF or OpenAPI file in the chat first; its id appears there.' : ST.pk === 'github' ? (gh.joined ? `Private repos through ${gh.label}.` : 'Public repos work now; private ones after you connect GitHub in Settings.') : 'Made in Hoola: already yours.'}</span><button class="btn" type="submit">Connect</button></div></form></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- screens (flows on her live site) */
  function pScreens() {
    const web = (K().products || []).filter(p => p.kind === 'web' && p.verified);
    if (!web.length) return `<div><h1 class="sd-h">Screenshots</h1><p class="lead">Step-by-step screenshots of your own live website, taken in a real browser, with numbered highlights and personal data covered.</p></div>
      <section class="card">${empty('Connect your live website on Sources and prove it is yours first. Apps and sites made in Hoola use their own screens already.')}<div class="md-acts"><span></span><button class="btn" type="button" data-go="sources">Open Sources</button></div></section>`;
    const pid = ST.prod && web.some(p => p.id === ST.prod) ? ST.prod : web[0].id, p = lazyOut('p:' + pid, 'product_get', {product: pid});
    return `<div><h1 class="sd-h">Screenshots</h1><p class="lead">Write the steps in plain lines; Hoola runs them in a real browser on your site and takes a picture of each one. Personal data that shows is covered, not blurred.</p></div>${ro()}
      ${web.length > 1 ? `<section class="card"><label class="ins-lab">Website<select class="in" data-prod="1">${web.map(x => `<option value="${esc(x.id)}"${x.id === pid ? ' selected' : ''}>${esc(x.name)}</option>`).join('')}</select></label></section>` : ''}
      ${ST.busy ? `<section class="card dw-busy"><span class="cs-dot"></span><span>${esc(ST.busy)}</span></section>` : ''}
      ${!p ? loading() : p.error ? `<section class="card">${err(p)}</section>` : (p.flows || []).map(f => `<section class="card"><div class="cs-head"><div><h2 class="md-h2" style="margin:0">${esc(f.name)}</h2><span class="mut" style="font-size:13px">${esc(cap(f.device))} · ${esc(pl((f.steps || []).length, 'step'))} · ${esc(ago(f.last_run))}</span></div>
          <div class="r">${CAN() ? `<button class="btn soft sm" type="button" data-reshoot="${esc(f.id)}" data-pid="${esc(pid)}">Take them again</button>` : ''}</div></div>
          ${f.error ? `<p class="cs-neg" style="margin:0 0 8px">${esc(f.error)}</p>` : ''}
          ${(f.shots || []).length ? `<div class="dw-shots">${f.shots.map(sh => `<figure>${img(`/api/docwriter/flows/${enc(f.id)}/img/${enc(sh.file)}`, sh.alt)}<figcaption><b>${esc(sh.n)}.</b> ${esc(sh.alt)}${sh.masked ? ` <span class="mut">· ${esc(pl(sh.masked, 'thing'))} covered</span>` : ''}</figcaption></figure>`).join('')}</div>` : empty('No screenshots yet.')}</section>`).join('')}
      ${CAN() ? `<section class="card"><h2 class="md-h2">New set of steps</h2><form data-form="flow" data-pid="${esc(pid)}" class="dw-grid">
        <label class="ins-lab">Name<input class="in" name="name" required placeholder="Sign up"></label>
        <label class="ins-lab">Screen<select class="in" name="device"><option value="phone">Phone</option><option value="tablet">Tablet</option><option value="desktop">Computer</option></select></label>
        <label class="ins-lab wide">Steps, one a line<textarea class="in dw-mono" name="steps" rows="6" placeholder='goto "/signup"&#10;fill "Email" = demo@example.com&#10;click "Create account"&#10;screenshot'></textarea></label>
        <div class="md-acts wide"><span class="mut" style="font-size:13px">Only ${esc((K().steps || []).join(' / '))}. Use demo values - a password, code or card number is refused.</span><button class="btn" type="submit">Take the screenshots</button></div></form></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), gh = s.github || {}, langs = s.langs || ['en'];
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Who reads your docs and how they should sound.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Your docs</h2><form data-form="dwset" class="dw-grid">
        <label class="ins-lab">Product name<input class="in" name="product_name" maxlength="120" value="${esc(s.product_name || '')}"></label>
        <label class="ins-lab">Who reads them<input class="in" name="audience" maxlength="200" value="${esc(s.audience || '')}" placeholder="Shop owners, first time with the app"></label>
        <label class="ins-lab">Tone<input class="in" name="tone" maxlength="200" value="${esc(s.tone || '')}" placeholder="Friendly, short sentences"></label>
        <label class="ins-lab">Support contact (allowed in docs)<input class="in" name="contact" maxlength="200" value="${esc(s.contact || '')}" placeholder="help@your-shop.com"></label>
        <fieldset class="dw-langs wide"><legend>Languages your users read (the first is the default)</legend>${(K().langs || []).map(l => `<label class="ar-chk"><input type="checkbox" name="langs" value="${esc(l.code)}"${langs.includes(l.code) ? ' checked' : ''}> ${esc(l.name)}</label>`).join('')}</fieldset>
        <label class="ins-lab wide">Words never translated (one a line)<textarea class="in" name="keep" rows="3">${esc((s.keep || []).join('\n'))}</textarea></label>
        <label class="ins-lab wide">Your writing rules (one a line)<textarea class="in" name="rules" rows="3">${esc((s.rules || []).join('\n'))}</textarea></label>
        ${CAN() ? '<div class="md-acts wide"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">Glossary</h2>${(s.glossary || []).length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Say</th><th>Not</th><th>Note</th></tr></thead><tbody>${s.glossary.map(g => `<tr><td><b>${esc(g.term)}</b></td><td>${esc(g.avoid || '')}</td><td class="mut">${esc(g.note || '')}</td></tr>`).join('')}</tbody></table></div>` : empty('No terms yet.')}
        ${CAN() ? `<form data-form="gloss" class="ar-row"><label class="ins-lab" style="flex:1">Say<input class="in" name="term" required placeholder="Sign in"></label><label class="ins-lab" style="flex:1">Not<input class="in" name="avoid" placeholder="Log in"></label><label class="ins-lab" style="flex:2">Note<input class="in" name="note"></label><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">GitHub</h2>
        ${gh.joined ? `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">Connected: ${esc(gh.label || 'read-only token')} (sealed, never shown again)</span>${CAN() ? '<button class="btn soft sm" type="button" data-act="github_forget">Remove</button>' : ''}</div>`
          : CAN() ? `<form data-form="github" class="ar-row"><label class="ins-lab" style="flex:1">A fine-grained token<input class="in" name="token" type="password" autocomplete="off" required placeholder="github_pat_…"></label><button class="btn soft" type="submit">Connect</button></form>
            <p class="cs-note">Contents: Read to read a private repo; to open docs pull requests it also needs Contents and Pull requests: Read and write on that repo. Sealed on the server and never shown again - never paste it in the chat.</p>` : ''}</section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never">${(K().never || []).map(n => `<li>${esc(n)}</li>`).join('')}</ul></section>`;
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
  function openDoc(r, msg) {
    ST.busy = ''; dropO('d:'); ST.files_ready = [];
    const id = ((r && r.doc) || {}).id;
    refreshDesk(false);
    if (id) { if (location.hash === '#/docs/' + id) showPage(); else location.hash = '#/docs/' + id; } else showPage(true);
    toast(msg || (r && r.say) || 'Done.');
  }
  /* a page action that asks twice instead of a browser dialog */
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const od = t.closest('[data-doc]'); if (od) { ST.files_ready = []; ST.edit = ''; delete ST.out['d:' + od.dataset.doc]; location.hash = '#/docs/' + od.dataset.doc; return; }
    const fl = t.closest('[data-file]'); if (fl) { const f = (ST.files_ready || [])[Number(fl.dataset.file)]; if (f) getFile(f); return; }
    const sc = t.closest('[data-sec]'); if (sc) { const el = document.getElementById('sec-' + sc.dataset.sec); if (el) { el.open = true; el.scrollIntoView({block: 'center', behavior: 'smooth'}); } return; }
    const es = t.closest('[data-editsec]'); if (es) { ST.edit = es.dataset.editsec; showPage(true); const ta = $('#dwPage form[data-form=edit] textarea'); if (ta) ta.focus(); return; }
    if (t.closest('[data-cancel]')) { ST.edit = ''; showPage(true); return; }
    const btn = t.closest('button');
    try {
      const dc = t.closest('[data-dec]'); if (dc) {
        const yes = dc.dataset.yes === '1'; if (yes && !sure(dc, 'Tap again to make it public')) return;
        dc.disabled = true; const r = await run('decide', {doc: dc.dataset.dec, hash: dc.dataset.hash, yes}); dropO('d:'); await changed(r.say || (yes ? 'Public.' : 'Not made public.')); return;
      }
      const up = t.closest('[data-unpage]'); if (up) { if (!sure(up, 'Tap again to take it down')) return; up.disabled = true; dropO('d:'); await changed((await run('unpage', {doc: up.dataset.unpage})).say); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {doc: dl.dataset.del}); dropO('d:'); location.hash = '#/docs'; await changed(r.say); return; }
      const fs = t.closest('[data-files]'); if (fs) { fs.disabled = true; toast('Making the files…'); const r = await run('files', {doc: fs.dataset.id, formats: fs.dataset.files.split(',')}); ST.files_ready = r.files || []; showPage(true); toast(r.say || 'Files ready.'); return; }
      const pa = t.closest('[data-pact]'); if (pa) {
        const act = pa.dataset.pact;
        if (act === 'remove_product' && !sure(pa, 'Tap again to remove (docs stay)')) return;
        pa.disabled = true;
        ST.busy = {verify: 'Looking for your proof…', snapshot: 'Reading your product…', sync: 'Comparing the docs with your product - this can take a minute…'}[act] || ''; if (ST.busy) showPage(true);
        const r = await run(act, {product: pa.dataset.id}); ST.busy = ''; dropO('d:', 'p:');
        await changed(r.say || (act === 'sync' ? `${num((r.stale || []).length || r.stale || 0)} sections out of date.` : 'Done.')); return;
      }
      const rs = t.closest('[data-reshoot]'); if (rs) {
        const p = ST.out['p:' + rs.dataset.pid] || {}, f = (p.flows || []).find(x => x.id === rs.dataset.reshoot); if (!f) return;
        rs.disabled = true; ST.busy = `Taking "${f.name}" again in a real browser…`; showPage(true);
        const r = await run('flow', {product: rs.dataset.pid, name: f.name, steps: f.steps, device: f.device}); ST.busy = ''; dropO('p:'); await changed(r.say || 'Done.'); return;
      }
      const a = t.closest('[data-act]');
      if (a) {
        const act = a.dataset.act;
        if (act === 'github_forget' && !sure(a, 'Tap again to remove')) return;
        a.disabled = true;
        if (act === 'check') { await run('check', {doc: a.dataset.id}); dropO('d:'); await changed('Checked.'); }
        else await changed((await run(act, {})).say || 'Done.');
        return;
      }
    } catch (err2) { ST.busy = ''; toast(err2.message, true); if (btn) btn.disabled = false; showPage(true); }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.df) { ST.df = el.value; showPage(true); return; }
    if (el.dataset.prod) { ST.prod = el.value; showPage(true); return; }
    if (el.name === 'dwkind') { ST.kind = el.value; return; }
    const f = el.closest('form[data-form=addprod]'); if (f && el.name === 'kind') { ST.pk = el.value; showPage(true); }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) btn.disabled = true;
    try {
      if (kind === 'write') { ST.prod = g('product'); ST.busy = 'Writing your doc from the product…'; showPage(true);
        openDoc(await run('write', {product: g('product'), kind: g('dwkind') || ST.kind || 'quickstart', lang: g('lang'), title: g('title'), words: S(fd.get('words'))})); }
      else if (kind === 'notes') { ST.busy = 'Writing the release notes…'; showPage(true); openDoc(await run('release_notes', {product: g('product'), version: g('version'), lang: g('lang'), words: S(fd.get('words'))})); }
      else if (kind === 'edit') { const r = await run('edit', {doc: form.dataset.id, section: form.dataset.which, title: g('title'), body: S(fd.get('body'))}); ST.edit = ''; ST.out['d:' + form.dataset.id] = r.doc; await changed(r.say); }
      else if (kind === 'revise') { toast('Changing the doc…'); const r = await run('revise', {doc: form.dataset.id, instruction: g('instruction')}); ST.out['d:' + form.dataset.id] = r.doc; await changed(r.say); }
      else if (kind === 'translate') { toast('Translating…'); openDoc(await run('translate', {doc: form.dataset.id, to: g('to')})); }
      else if (kind === 'publish') { const r = await run('publish', {doc: form.dataset.id, dest: g('dest')}); dropO('d:'); $('#sdDesk').scrollTop = 0; await changed(r.say || 'A card waits for your tap above.'); }
      else if (kind === 'addprod') { ST.busy = 'Reading your product…'; showPage(true); const r = await run('add_product', {kind: g('kind'), ref: g('ref'), name: g('name')}); ST.busy = ''; form.reset(); await changed(r.say || 'Connected.'); }
      else if (kind === 'flow') { ST.busy = 'Running the steps in a real browser and taking the pictures…'; showPage(true);
        const r = await run('flow', {product: form.dataset.pid, name: g('name'), steps: S(fd.get('steps')), device: g('device')}); ST.busy = ''; dropO('p:'); await changed(r.say || 'Done.'); }
      else if (kind === 'dwset') { const lines = n => S(fd.get(n)).split('\n').map(x => x.trim()).filter(Boolean);
        await run('settings', {product_name: g('product_name'), audience: g('audience'), tone: g('tone'), contact: g('contact'), langs: fd.getAll('langs'), keep: lines('keep'), rules: lines('rules')}); await changed('Saved.'); }
      else if (kind === 'gloss') { const r = await run('glossary', {term: g('term'), avoid: g('avoid'), note: g('note')}); await changed(r.say); }
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
    const box = $('#dwFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/dwdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'dw' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


