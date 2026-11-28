/* CLOUD ENGINEER DESK - the Cloud Engineer's own section, like the finance desks (owner: "Cloud Engineer same as finance desks").
   A thin top bar, then the Cloud chat (its own conversation, kind 'cloudeng') beside the desk's pages: Today, Bill, Waste,
   Commitments, Access, Network, CI check, Settings. The pages call /api/cldesk/do/<part>; nothing runs on her cloud. */
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
    back: '<path d="M15 18l-6-6 6-6"/>', fo: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/><circle cx="16.5" cy="16.5" r="1"/>',
    swap: '<path d="M7 7h13l-3-3M17 17H4l3 3"/>', plus: '<path d="M12 5v14M5 12h14"/>', fold: '<path d="M9 6l6 6-6 6"/>',
    unfold: '<path d="M15 6l-6 6 6 6"/>', chat: '<path d="M4 5h16v11H9l-5 4z"/>', refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h0"/>'};
  window.HoolaQuality?.use(api);

  const TABS = [['today', 'Today'], ['bill', 'Bill'], ['waste', 'Waste'], ['commitments', 'Commitments'], ['access', 'Access'], ['network', 'Network'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where should I start cutting the cloud bill?', 'What should every account have from day one?', 'How do I stop surprise bills?'],
    bill: ['Why did the bill jump?', 'How do I make every team own its spend?', 'What should a monthly budget alert look like?'],
    waste: ['Is it safe to delete an unattached disk?', 'How do I schedule machines off at night?', 'How long should snapshots be kept?'],
    commitments: ['Savings plan or reserved instances?', 'One year or three?', 'How much of my usage should be committed?'],
    access: ['How do I get to least privilege?', 'How should GitHub Actions reach my cloud?', 'Who should have Owner?'],
    network: ['How big should a VPC be?', 'How do I plan addresses across accounts?', 'How do I reach machines without opening SSH?'],
    ci: ['How do I keep policies in a repository?', 'Should the guard block or warn?', 'What else should CI check for cloud changes?'],
    settings: ['Which tag should mark the owner?', 'What CPU line means idle?', 'Where do I find the committed price?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'bill', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.cldesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.cldesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'cloud', name: 'Cloud'} : null;
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
  const run = (part, a) => api('POST', '/api/cldesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/cldesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Cloud Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="clHire">Hire the Cloud Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#clHire').onclick = async () => { try { await api('POST', '/api/employees/cloud_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Cloud</div><div class="sd-site" id="clSite"></div></div>
          <span id="clState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Cloud chat">
          <div class="sd-chathead"><div class="t"><b>Cloud chat</b><span>Paste a cost export, an inventory, usage, a policy or a network - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="clFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="clPick" multiple hidden accept=".txt,.json,.csv,.tsv,.yaml,.yml,.log,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Cloud desk" id="sdTabs"></nav>
          <div id="clPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a bill or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#clPick').click()});
    $('#clPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.cldesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.cldesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/cldesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#clPage').addEventListener('click', onPageClick);
    $('#clPage').addEventListener('submit', onSubmit);
    $('#clPage').addEventListener('change', onChange);
    $('#clPage').addEventListener('input', onInput);
    $('#clPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#clState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#clSite').textContent = [s.provider && ({aws: 'AWS', azure: 'Azure', gcp: 'Google Cloud', other: ''}[s.provider]), s.currency, pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/cldesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#clPage'); if (!box) return;
    const fn = {today: pToday, bill: pBill, waste: pWaste, commitments: pCommitments, access: pAccess, network: pNetwork, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const st_ = () => K().settings || {};
  function lazyOut(key, part, a) {
    if (ST.out[key] === undefined) { ST.out[key] = null; run(part, a).then(r => { ST.out[key] = r; showPage(true); }).catch(e => { ST.out[key] = {error: e.message}; showPage(true); }); }
    return ST.out[key];
  }
  const ago = d => { if (!d) return '—'; const m = Math.round((Date.now() - new Date(d).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : dmy(d); };
  const SST = {open: ['Open', 'warn'], fixed: ['Done', 'ok'], ignored: ['Ignored', '']};
  const sTag = s => tag((SST[s] || [cap(s)])[0], (SST[s] || ['', ''])[1]);
  const pre = (t, cls) => `<pre class="clk-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {bill: 'Bill', waste: 'Waste', commit: 'Commitment', iam: 'Access', network: 'Network'};
  const ROUTE = {bill: 'bill', waste: 'waste', commit: 'commitments', iam: 'access', network: 'network'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(0);
  const MONEY = v => (v === null || v === undefined) ? '—' : Number(v).toLocaleString('en', {maximumFractionDigits: Math.abs(Number(v)) < 1000 ? 2 : 0});
  const M = (v, c) => (v === null || v === undefined) ? '—' : MONEY(v) + (c ? ' ' + c : '');
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'bill': return `${M(b.total, b.currency)} over ${pl(b.days || 0, 'day')}${b.spikes ? ` · ${pl(b.spikes, 'spike')}` : ''}`;
      case 'waste': return `${pl(b.found || 0, 'thing')} in ${pl(b.resources || 0, 'resource')}${b.save ? ` · ${M(b.save, b.currency)} a month` : ''}`;
      case 'commit': return b.best ? `commit ${P4(b.best)} · saves ${pc(b.save_pct)}%` : 'no commitment beats on demand';
      case 'iam': return `${pl(b.statements || 0, 'statement')} · ${num(b.flagged || 0)} with a problem`;
      case 'network': return [pl(b.vpcs || 0, 'network'), pl(b.subnets || 0, 'subnet'), b.rules ? pl(b.rules, 'rule') : '', b.plans ? pl(b.plans, 'plan') : ''].filter(Boolean).join(' · ');
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="clk-list">${list.map(x => `<button type="button" class="clk-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="clk-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="clk-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="clk-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="clk-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono clk-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft clk-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="clk-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card clk-sum ${ok ? 'okv' : 'badv'}"><p class="clk-big">${esc(r.verdict)}</p>${r.counts ? `<div class="clk-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="clk-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
  const nice = (lo, hi, n = 5) => { if (hi - lo < 1e-12) { hi = lo + 1; } const raw = (hi - lo) / n, p = Math.pow(10, Math.floor(Math.log10(raw))), st = [1, 2, 2.5, 5, 10].map(m => m * p).find(m => m >= raw) || raw; const out = []; for (let v = Math.ceil(lo / st) * st; v <= hi + st * 1e-6; v += st) out.push(+v.toPrecision(12)); return out; };
  /* series: [{name, pts: [[x, y]], cls, dash}] - a line chart with its own axes */
  function lines(series, xl, yl, aria, opt) {
    const all = series.flatMap(s2 => s2.pts); if (!all.length) return '';
    const W = 760, H = 300, L = 54, R = 14, T0 = 12, B = 40;
    let x0 = Math.min(...all.map(p => p[0])), x1 = Math.max(...all.map(p => p[0])), y0 = Math.min(0, ...all.map(p => p[1])), y1 = Math.max(...all.map(p => p[1]));
    if (opt && opt.ymax !== undefined) y1 = Math.min(y1, opt.ymax); if (y1 - y0 < 1e-9) y1 = y0 + 1;
    const xt = nice(x0, x1), yt = nice(y0, y1);
    x0 = Math.min(x0, xt[0]); x1 = Math.max(x1, xt[xt.length - 1]); y0 = Math.min(y0, yt[0]); y1 = Math.max(y1, yt[yt.length - 1]);
    const X = v => L + (v - x0) / (x1 - x0 || 1) * (W - L - R), Y = v => T0 + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T0 - B);
    const grid = yt.map(v => `<line class="g" x1="${L}" x2="${W - R}" y1="${Y(v).toFixed(1)}" y2="${Y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(Y(v) + 4).toFixed(1)}" text-anchor="end">${esc(P4(v))}</text>`).join('')
      + xt.map(v => `<text class="tx" x="${X(v).toFixed(1)}" y="${H - B + 16}" text-anchor="middle">${esc(P4(v))}</text>`).join('');
    const ref = opt && opt.ref !== undefined ? `<line class="ref" x1="${L}" x2="${W - R}" y1="${Y(opt.ref).toFixed(1)}" y2="${Y(opt.ref).toFixed(1)}"/>` : '';
    const paths = series.map(s2 => `<polyline class="ln ${s2.cls || ''}${s2.dash ? ' dash' : ''}" points="${s2.pts.map(p => `${X(p[0]).toFixed(1)},${Y(Math.min(y1, Math.max(y0, p[1]))).toFixed(1)}`).join(' ')}"><title>${esc(s2.name)}</title></polyline>`).join('');
    const key = `<div class="clk-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="clk-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];


  const meter = (v, warnAt, badAt) => `<span class="clk-meter"><i class="${v >= badAt ? 'bad' : v >= warnAt ? 'warn' : ''}" style="width:${Math.min(100, v * 100).toFixed(1)}%"></i></span>`;
  const shareRows = (list, cur) => bars((list || []).map(r => [r.name, r.cost, r.name.startsWith('(') ? 'clk-b warn' : 'clk-b', pc(r.share) + '%']), v => M(v, cur), 'Cost');

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), b = k.bill, w = k.waste, c = k.commit, a = k.iam, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Cloud bill', b ? esc(M(b.total, b.currency)) : '—', b ? `${b.forecast !== null && b.forecast !== undefined ? 'month heading for ' + M(b.forecast, b.currency) : pl(b.days, 'day')} · ${b.number}` : 'paste a cost export', b && b.bad),
      tile('Waste', w ? (w.save ? esc(M(w.save, w.currency)) + ' <small>a month</small>' : esc(num(w.found || 0)) + ' <small>to look at</small>') : '—', w ? `${pl(w.found || 0, 'thing')} in ${pl(w.resources, 'resource')} · ${w.number}` : 'paste an inventory', w && w.bad),
      tile('Commitment', c ? (c.best ? esc(pc(c.save_pct)) + '<small>% saved</small>' : 'none') : '—', c ? `${c.best ? 'commit ' + P4(c.best) : 'on demand is cheapest'} · ${c.number}` : 'paste hourly usage', c && c.bad),
      tile('Access', a ? esc(num(a.flagged || 0)) + ' <small>problems</small>' : '—', a ? `${pl(a.statements, 'statement')} · ${a.number}` : 'paste a policy', a && a.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc(s.budget ? 'Budget ' + M(s.budget, s.currency) + ' a month.' : 'Set your currency, budget and owner tag in Settings.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="clk-path">
        <li><button type="button" data-go="bill"><b>Know the bill</b><span>Where the money goes, who owns it, what jumped and where the month will land</span></button></li>
        <li><button type="button" data-go="waste"><b>Stop paying for nothing</b><span>Disks, addresses, machines and snapshots nobody uses</span></button></li>
        <li><button type="button" data-go="commitments"><b>Commit to the steady part</b><span>Savings plans and reserved capacity sized from your own hours</span></button></li>
        <li><button type="button" data-go="access"><b>Let in only what should be</b><span>Access policies and network rules read for what is too wide</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- bill */
  const SAMPLE_BILL = 'ChargePeriodStart,ServiceName,SubAccountName,RegionName,BilledCost,BillingCurrency,tag_team\n2026-11-01,Amazon EC2,prod,us-east-1,102.40,USD,web\n2026-11-01,Amazon S3,prod,us-east-1,19.80,USD,\n2026-11-02,Amazon EC2,prod,us-east-1,98.10,USD,web';
  function pBill() {
    if (ST.arg) return one(ST.arg, 'bill', pBl);
    const s = st_();
    return `<div><h1 class="sd-h">Bill</h1><p class="lead">Your cloud bill added up by day, service, account, region and owner: spend nobody owns, days that jumped and the service behind them, what grew this week, credits, and the month at its run rate against your budget.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a bill</h2><form data-form="bill" class="clk-grid">
        ${area('text', 'A cost export as CSV - FOCUS columns, AWS Cost and Usage Report, Google Cloud billing export, Azure cost details, or any table with a cost and a date', SAMPLE_BILL, 10)}
        ${fld('tag_key', 'Owner tag', s.tag_key, '', 'team')}${fld('budget', 'Budget a month', s.budget || '', 'type="number" min="0" step="any"', '5000')}${fld('currency', 'Currency (if the export has none)', s.currency, 'maxlength="3"', 'USD')}
        ${subRow('Read it', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('bill'))}</section>`;
  }
  function pBl(d) {
    const r = d.result || {}, m = r.month || {}, cur = r.currency, by = r.by || {};
    const spikes = new Set((r.spikes || []).map(x => x.day));
    return `${head(d, 'bill')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Total', esc(M(r.total, cur)), `${r.first} to ${r.last}`)}${tile(m.complete ? 'Month' : 'Month heading for', esc(M(m.forecast, cur)), m.budget ? 'budget ' + M(m.budget, cur) : m.month, m.budget && m.forecast > m.budget)}${tile('Per day lately', esc(M(m.rate, cur)), 'average of the last 7 days')}${tile('No owner', r.untagged !== null && r.untagged !== undefined ? esc(M(r.untagged, cur)) : '—', r.tag_key ? 'no ' + r.tag_key + ' tag' : 'set an owner tag', r.untagged && r.gross && r.untagged / r.gross > 0.1)}</div></section>
      <section class="card"><h2 class="md-h2">By day</h2>${line((r.series || []).map(x => [x.day.slice(5), x.cost]), 'Cost by day', v => M(v, cur), '', true)}${(r.spikes || []).length ? `<p class="cs-note">${pl(r.spikes.length, 'day')} jumped above ${r.spikes.length > 1 ? 'their' : 'its'} own recent level - see Spikes.</p>` : ''}</section>
      ${(r.spikes || []).length ? `<section class="card"><h2 class="md-h2">Spikes</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Day</th><th class="r">Cost</th><th class="r">Usual</th><th>Mostly</th><th class="r">Service over usual</th></tr></thead><tbody>${r.spikes.map(x => `<tr class="warn"><td>${esc(x.day)}</td><td class="r"><b>${esc(M(x.cost, cur))}</b></td><td class="r">${esc(M(x.base, cur))}</td><td>${esc(x.service)}</td><td class="r">+${esc(M(x.service_over, cur))}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <div class="clk-two">${[['service', 'By service'], ['account', 'By account'], ['region', 'By region'], ['owner', 'By owner']].filter(([k2]) => by[k2]).map(([k2, t]) => `<section class="card"><h2 class="md-h2">${t}</h2>${shareRows(by[k2], cur)}</section>`).join('')}</div>
      ${(r.movers || []).length ? `<section class="card"><h2 class="md-h2">Growing this week</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Service</th><th class="r">Last 7 days</th><th class="r">7 days before</th><th class="r">More</th></tr></thead><tbody>${r.movers.map(x => `<tr><td>${esc(x.service)}</td><td class="r">${esc(M(x.last7, cur))}</td><td class="r">${esc(M(x.prev7, cur))}</td><td class="r"><b>+${esc(M(x.change, cur))}</b>${x.ratio ? ` <span class="mut">${esc(pc(x.ratio - 1))}%</span>` : ' <span class="mut">new</span>'}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card clk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- waste */
  const SAMPLE_WASTE = 'id,type,state,attached,cpu_p95,age_days,instance_type,monthly_cost\nvol-0a1,EBS volume,available,no,,40,gp2,8.00\neipalloc-7,Elastic IP,,no,,10,,3.65\ni-0b2,EC2 instance,running,,2,200,m4.large,70.08';
  function pWaste() {
    if (ST.arg) return one(ST.arg, 'waste', pWs);
    const s = st_();
    return `<div><h1 class="sd-h">Waste</h1><p class="lead">Resources nobody uses, from an inventory you export: disks attached to nothing, addresses held by nothing, machines stopped or idle, snapshots past your keep days, and older generations - with each one's monthly cost from your table.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Look for waste</h2><form data-form="waste" class="clk-grid">
        ${area('text', 'A CSV per resource: id, type, state, attached, cpu_p95, age_days, size_gb, instance_type, monthly_cost', SAMPLE_WASTE, 10)}
        ${fld('idle_cpu', 'Idle when CPU stays under (%)', s.idle_cpu, 'type="number" min="0" max="100" step="any"')}${fld('keep_days', 'Keep snapshots and stopped machines (days)', s.keep_days, 'type="number" min="1" step="1"')}${fld('currency', 'Currency', s.currency, 'maxlength="3"', 'USD')}
        ${subRow('Look', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('waste'))}</section>`;
  }
  function pWs(d) {
    const r = d.result || {}, cur = r.currency, f = r.found || [];
    const SV2 = {bad: ['Serious', 'bad'], warn: ['Waste', 'warn'], info: ['Note', '']};
    return `${head(d, 'waste')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Resources', esc(num(r.resources)), Object.entries(r.kinds || {}).map(([k2, n]) => n + ' ' + k2).slice(0, 4).join(', '))}${tile('To look at', esc(num(f.length)), 'by these checks', f.some(x => x.sev === 'bad'))}${tile('A month', r.save ? esc(M(r.save, cur)) : '—', r.save ? 'if cleared' : 'add monthly costs')}${tile('Of the total', r.total ? esc(pc(r.save / r.total)) + '<small>%</small>' : '—', r.total ? 'of ' + M(r.total, cur) + ' a month' : '')}</div></section>
      ${(r.groups || []).length ? `<section class="card"><h2 class="md-h2">By kind</h2>${bars(r.groups.filter(g => !r.save || g.save > 0).map(g => [g.name, r.save ? g.save : g.count, g.name === 'Not deallocated' ? 'clk-b bad' : 'clk-b', pl(g.count, 'resource')]), v => r.save ? M(v, cur) : num(v), 'Waste by kind')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Each one</h2>${f.length ? `<div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Resource</th><th>Why</th><th>What to do</th><th class="r">A month</th><th></th></tr></thead><tbody>${f.map(x => `<tr class="${x.sev === 'bad' ? 'bad' : x.sev === 'warn' ? 'warn' : ''}"><td><code>${esc(x.id)}</code><br><span class="mut">${esc([x.type, x.itype, x.region].filter(Boolean).join(' · '))}</span></td><td>${esc(x.why)}${x.check ? ' <span class="cs-tag">check this</span>' : ''}</td><td class="mut">${esc(x.do)}</td><td class="r">${x.save ? esc(M(x.save, cur)) : '—'}</td><td>${tag(SV2[x.sev][0], SV2[x.sev][1])}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Nothing idle found by these checks.</p>'}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card clk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- commitments */
  const SAMPLE_CM = 'time,usage\n2026-11-01 00:00,10\n2026-11-01 01:00,10\n2026-11-01 09:00,15\n2026-11-01 10:00,15';
  function pCommitments() {
    if (ST.arg) return one(ST.arg, 'commitments', pCm);
    const s = st_();
    return `<div><h1 class="sd-h">Commitments</h1><p class="lead">Savings plans, reserved instances and committed use sized from your own hourly usage: the level that would have cost least, a safer level that keeps most of the saving, the use it needs to pay off, and how your current commitment did.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Size a commitment</h2><form data-form="commit" class="clk-grid">
        ${area('text', 'A CSV of time and usage per hour (instance-hours, vCPUs or normalised units) - or on-demand spend per hour; a month of hours is best', SAMPLE_CM, 10)}
        ${fld('od_rate', 'On-demand price per unit-hour', s.od_rate || '', 'type="number" min="0" step="any"', '0.096')}${fld('commit_rate', 'Committed price per unit-hour', s.commit_rate || '', 'type="number" min="0" step="any"', '0.060')}${fld('discount', 'Or the discount (0.28 = 28%)', s.discount || '', 'type="number" min="0" max="0.99" step="any"', '0.28')}
        ${fld('current', 'Commitment you have now (units an hour)', s.current_commit || '', 'type="number" min="0" step="any"', '12')}${fld('unit', 'Unit', '', 'maxlength="30"', 'instances')}${fld('currency', 'Currency', s.currency, 'maxlength="3"', 'USD')}
        ${subRow('Size it', '.csv,.tsv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Sized</h2>${itemRows(items('commit'))}</section>`;
  }
  function pCm(d) {
    const r = d.result || {}, b = r.best || {}, sf = r.safe || {}, c = r.current, cur = r.currency, u = r.use || {};
    const lvl = (t, x) => x ? `<tr><td><b>${esc(t)}</b></td><td class="r">${esc(P4(x.commit))}</td><td class="r">${esc(M(x.save, cur))}</td><td class="r">${esc(pc(x.save_pct))}%</td><td class="r">${x.util === null || x.util === undefined ? '—' : esc(pc(x.util)) + '%'}</td><td class="r">${esc(pc(x.coverage))}%</td></tr>` : '';
    return `${head(d, 'commitments')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Best level', b.commit ? esc(P4(b.commit)) : '0', r.unit)}${tile('Saved', esc(pc(b.save_pct)) + '<small>%</small>', M(b.save, cur) + ' over ' + P4(r.hours / 24) + ' days')}${tile('Break-even use', esc(pc(r.breakeven)) + '<small>%</small>', 'of the hours paid for')}${tile('Now', c ? (c.util === null ? '—' : esc(pc(c.util)) + '<small>% used</small>') : '—', c ? 'covers ' + pc(c.coverage) + '% of usage' : 'give your commitment', c && c.util !== null && c.util < r.breakeven)}</div></section>
      <section class="card"><h2 class="md-h2">Saving by level</h2>${lines([{name: 'Saved over the period', pts: (r.curve || []).map(p => [p.commit, p.save]), cls: 'c1'}], r.unit, 'saved', 'Saving by commitment level', {ref: 0})}<p class="cs-note">Usage ranged from ${esc(P4(u.min))} to ${esc(P4(u.max))} (median ${esc(P4(u.median))}). The saving rises while each added unit is used more than ${esc(pc(r.breakeven))}% of the time, then falls.</p></section>
      <section class="card"><h2 class="md-h2">Levels</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th></th><th class="r">Commit</th><th class="r">Saved</th><th class="r">%</th><th class="r">Used</th><th class="r">Covers</th></tr></thead><tbody>${lvl('Best', b)}${sf.commit !== b.commit ? lvl('Safer', sf) : ''}${lvl('Yours now', c)}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card clk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 40000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- access */
  const SAMPLE_IAM = '{\n  "Version": "2012-10-17",\n  "Statement": [\n    {"Sid": "Deploy", "Effect": "Allow", "Action": ["s3:*", "iam:PassRole"], "Resource": "*"}\n  ]\n}';
  function pAccess() {
    if (ST.arg) return one(ST.arg, 'access', pAc);
    return `<div><h1 class="sd-h">Access</h1><p class="lead">Access policies read for what lets too much in: full admin, every action of a service, the actions that let someone give themselves more access, PassRole to any role, anyone on the internet, GitHub trusted from any repository, allUsers, basic owner roles and Owner over a whole subscription.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read a policy</h2><form data-form="iam" class="clk-grid">
        ${area('text', 'AWS IAM policy JSON (identity, bucket or trust policy, or get-account-authorization-details), gcloud get-iam-policy --format=json, or az role assignment list. Several: put ## name before each.', SAMPLE_IAM, 12)}
        ${subRow('Read it', '.json,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('iam'))}</section>`;
  }
  function pAc(d) {
    const r = d.result || {}, rows = r.rows || [];
    return `${head(d, 'access')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Read', esc(num(r.statements)), (r.kinds || []).map(k2 => ({aws: 'AWS', gcp: 'Google Cloud', azure: 'Azure'}[k2] || k2)).join(', '))}${tile('With a problem', esc(num(r.flagged)), 'statements or grants', r.flagged > 0)}${tile('Serious', esc(num((r.counts || {}).bad || 0)), 'let too much in', ((r.counts || {}).bad || 0) > 0)}${tile('To fix', esc(num((r.counts || {}).warn || 0)), 'too wide')}</div></section>
      <section class="card"><h2 class="md-h2">Every statement</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Where</th><th>Allows</th><th>On</th><th>Who</th><th></th></tr></thead><tbody>${rows.map(x => `<tr class="${x.flags.length ? (x.flags.some(f => ['full admin', 'public', 'escalation', 'passrole *', 'github oidc, no subject', 'admin at subscription'].includes(f)) ? 'bad' : 'warn') : ''}"><td><b>${esc(x.where)}</b>${x.condition ? ' <span class="cs-tag">condition</span>' : ''}</td><td><code>${esc((x.actions || []).join(', '))}</code></td><td><code>${esc((x.resources || []).join(', '))}</code></td><td class="mut">${esc(x.principal || '—')}</td><td>${x.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card clk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- network */
  const SAMPLE_NET = 'vpc prod 10.0.0.0/16\nsubnet app-a 10.0.1.0/24 vpc=prod zone=a\nsubnet app-b 10.0.2.0/24 vpc=prod zone=b\nrule web-sg in tcp 22 0.0.0.0/0\nplan 10.20.0.0/16 zones=3 tiers=public,private,data';
  function pNetwork() {
    if (ST.arg) return one(ST.arg, 'network', pNw);
    const s = st_();
    return `<div><h1 class="sd-h">Network</h1><p class="lead">Networks and subnets checked before they are built or joined - overlaps, subnets outside their network, too small, the addresses each really gives and the space left - firewall rules that open admin and database ports to the internet, and a plan that splits a range across zones and tiers.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a network</h2><form data-form="network" class="clk-grid">
        ${area('text', "Lines: 'vpc prod 10.0.0.0/16', 'subnet app-a 10.0.1.0/24 vpc=prod zone=a', 'rule web-sg in tcp 22,80 0.0.0.0/0', 'plan 10.20.0.0/16 zones=3 tiers=public,private,data' - or aws ec2 describe-security-groups / gcloud compute firewall-rules list JSON", SAMPLE_NET, 10)}
        ${sel('provider', 'Provider', [['aws', 'AWS'], ['azure', 'Azure'], ['gcp', 'Google Cloud'], ['other', 'Other']], s.provider)}
        ${subRow('Check it', '.json,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('network'))}</section>`;
  }
  function pNw(d) {
    const r = d.result || {}, sp = r.space || [], sn = r.subnets || [], ru = r.rules || [], pls = r.plans || [];
    return `${head(d, 'network')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Networks', esc(num((r.vpcs || []).length)), (r.vpcs || []).map(v => v.name).slice(0, 3).join(', '))}${tile('Subnets', esc(num(sn.length)), num(sn.filter(x => x.flags.length).length) + ' with a problem', sn.some(x => x.flags.length))}${tile('Rules', esc(num(ru.length)), num(ru.filter(x => x.flags.length).length) + ' open to the internet', ru.some(x => x.flags.some(f => f !== 'internet')))}${tile('Provider', esc({aws: 'AWS', azure: 'Azure', gcp: 'Google Cloud', other: 'Other'}[r.provider] || r.provider), 'addresses kept per subnet')}</div></section>
      ${sp.length ? `<section class="card"><h2 class="md-h2">Space in each network</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Network</th><th>Range</th><th>Given to subnets</th><th>Largest free block</th><th>Free</th></tr></thead><tbody>${sp.map(x => `<tr><td><b>${esc(x.vpc)}</b></td><td><code>${esc(x.cidr)}</code></td><td>${meter(x.used_pct, 0.7, 0.85)} ${esc(pc(x.used_pct))}%</td><td class="r">${esc(num(x.largest_free))} addresses</td><td class="mut"><code>${esc(x.free.slice(0, 6).join(', '))}</code>${x.free.length > 6 ? ' …' : ''}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${sn.length ? `<section class="card"><h2 class="md-h2">Subnets</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Subnet</th><th>Range</th><th>Network</th><th>Zone</th><th class="r">Addresses</th><th class="r">Usable</th><th></th></tr></thead><tbody>${sn.map(x => `<tr class="${x.flags.length ? 'bad' : ''}"><td><b>${esc(x.name)}</b></td><td><code>${esc(x.cidr)}</code></td><td>${esc(x.vpc || '—')}</td><td>${esc(x.zone || '—')}</td><td class="r">${esc(num(x.size))}</td><td class="r">${esc(num(x.usable))}</td><td>${x.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${ru.length ? `<section class="card"><h2 class="md-h2">Rules</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Rule</th><th>Way</th><th>Protocol</th><th>Ports</th><th>From</th><th></th></tr></thead><tbody>${ru.map(x => `<tr class="${x.flags.some(f => f !== 'internet') ? 'bad' : x.flags.length ? 'warn' : ''}"><td><b>${esc(x.name)}</b></td><td>${x.dir === 'in' ? 'in' : 'out'}</td><td>${esc(x.proto)}</td><td><code>${esc(x.ports)}</code></td><td><code>${esc(x.src)}</code></td><td>${x.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${pls.map(p => `<section class="card"><h2 class="md-h2">Plan for ${esc(p.cidr)}</h2><div class="iv-tw"><table class="tb in-cards clk-t"><thead><tr><th>Tier</th><th>Zone</th><th>Range</th><th class="r">Usable</th></tr></thead><tbody>${p.subnets.map(x => `<tr><td><b>${esc(x.tier)}</b></td><td>${esc(x.zone)}</td><td><code>${esc(x.cidr)}</code></td><td class="r">${esc(num(x.usable))}</td></tr>`).join('')}</tbody></table></div><p class="cs-note">Each subnet a /${esc(p.prefix)}; ${esc(pl(p.spare_count, 'block'))} of the same size left for later${p.spare.length ? ': ' + esc(p.spare.slice(0, 4).join(', ')) + (p.spare_count > 4 ? ' …' : '') : ''}.</p></section>`).join('')}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card clk-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions access guard: every pull request that touches your policy files is read, and it fails when a policy allows every action on every resource, lets anyone in with no condition, passes any role, grants allUsers or trusts GitHub from any repository. It needs no cloud access.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Policy folder', s.policy_dir || 'not set'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : w.missing ? `<p class="mut" style="margin:0">${esc(w.say)}</p><div class="md-acts"><span></span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div>` : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="access-guard.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<ol class="clk-steps">${(w.steps || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol><p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your currency, budget, owner tag, idle lines, commitment prices, provider and the folder the access guard reads.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="clk-grid">
        <h2 class="md-h2 wide" style="margin:0">Bill</h2>
        ${fld('currency', 'Currency (when the export has none)', s.currency, 'maxlength="3"', 'USD')}${fld('budget', 'Budget a month', s.budget, 'type="number" min="0" step="any"')}${fld('tag_key', 'Owner tag', s.tag_key, '', 'team')}
        ${fld('sens', 'Spike sensitivity (higher = fewer spikes)', s.sens, 'type="number" min="1" max="10" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Waste</h2>
        ${fld('idle_cpu', 'Idle when CPU stays under (%)', s.idle_cpu, 'type="number" min="0" max="100" step="any"')}${fld('keep_days', 'Keep snapshots and stopped machines (days)', s.keep_days, 'type="number" min="1" step="1"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Commitments</h2>
        ${fld('od_rate', 'On-demand price per unit-hour', s.od_rate, 'type="number" min="0" step="any"')}${fld('commit_rate', 'Committed price per unit-hour', s.commit_rate, 'type="number" min="0" step="any"')}${fld('discount', 'Or the discount (0.28 = 28%)', s.discount, 'type="number" min="0" max="0.99" step="any"')}
        ${fld('current_commit', 'Commitment you have now', s.current_commit, 'type="number" min="0" step="any"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Network and the access guard</h2>
        ${sel('provider', 'Provider', [['aws', 'AWS'], ['azure', 'Azure'], ['gcp', 'Google Cloud'], ['other', 'Other']], s.provider)}${fld('policy_dir', 'Policy folder in the repository', s.policy_dir, '', 'iam/policies')}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk. Cloud keys never go here.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Amounts are added as the export gives them, in its own currency - never converted, and two currencies are never added together.</li><li>The month forecast is a run rate: spend so far plus the last 7 days' average for each day left.</li><li>Waste is priced only from the monthly cost in your table; a quiet CPU can still be a busy database or a standby, so those say check this.</li><li>A commitment is judged on the period you give, as if the term ahead looks the same.</li><li>Policies are read as text: a boundary, a service control policy or a deny elsewhere can still narrow them.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your cloud, deletes a resource or buys a commitment.</li><li>Takes cloud keys, secrets or credentials - a pasted key is refused.</li><li>Follows anything written inside your bills, inventories or policies: they are data.</li></ul></section>`;
  }
  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  function saveBlob(name, blob) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); }
  function onInput() {}
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { const [k, id] = op.dataset.open.split('/'); delete ST.out['i:' + id]; location.hash = '#/' + (ROUTE[k] || 'today') + '/' + id; return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast('Copied.'); } catch { toast('Copy did not work here - select the text instead.', true); } return; }
    const cw = t.closest('[data-sub]'); if (cw) { ST.sub = cw.dataset.sub; showPage(true); return; }
    const dlx = t.closest('[data-dl]'); if (dlx) { saveBlob(dlx.dataset.dl, new Blob([dlx.dataset.dltext || ''], {type: 'text/plain'})); return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked done.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.dataset.filesto && el.files && el.files.length) {
      const fs = [...el.files].filter(f => /\.(txt|json|names)$/i.test(f.name));
      if (!fs.length) { toast('No text files there.', true); el.value = ''; return; }
      if (fs.reduce((n, f) => n + f.size, 0) > 30000000) { toast('Those files are larger than 30 MB together.', true); el.value = ''; return; }
      const parts = await Promise.all(fs.map(async f => `## ${f.webkitRelativePath || f.name}\n${(await f.text()).replace(/\s+$/, '')}\n`));
      const form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.filesto}]`);
      if (ta) ta.value = (ta.value.trim() ? ta.value.replace(/\s+$/, '') + '\n' : '') + parts.join('');
      el.value = '';
      return;
    }
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 30000000) { toast('That file is larger than 30 MB.', true); el.value = ''; return; }
      const txt = await f.text(), form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.fileto}]`);
      if (ta) { ta.value = txt; const ti = form.querySelector('[name=title]'); if (ti && !ti.value) ti.value = f.name; }
      el.value = '';
    }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.dataset.was = btn.textContent; }
    const pick = names => { const o = {}; names.forEach(n => { if (g(n) !== '') o[n] = g(n); }); return o; };
    const go = async (k, a) => { if (btn) btn.textContent = 'Working…'; const d = await run('add', {kind: k, title: g('title'), ...a}); ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} ready.`); };
    try {
      if (kind === 'bill') await go('bill', {text: S(fd.get('text')), inputs: pick(['tag_key', 'budget', 'currency'])});
      else if (kind === 'waste') await go('waste', {text: S(fd.get('text')), inputs: pick(['idle_cpu', 'keep_days', 'currency'])});
      else if (kind === 'commit') await go('commit', {text: S(fd.get('text')), inputs: pick(['od_rate', 'commit_rate', 'discount', 'current', 'unit', 'currency'])});
      else if (kind === 'iam') await go('iam', {text: S(fd.get('text')), inputs: {}});
      else if (kind === 'network') await go('network', {text: S(fd.get('text')), inputs: pick(['provider'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['currency', 'budget', 'tag_key', 'sens', 'idle_cpu', 'keep_days', 'od_rate', 'commit_rate', 'discount', 'current_commit', 'provider', 'policy_dir', 'runner'];


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
    const box = $('#clFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/cldesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'ds' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


