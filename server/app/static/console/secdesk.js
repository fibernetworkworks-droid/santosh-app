/* SECURITY ENGINEER DESK - the Security Engineer's own section, like the finance desks (owner: "Security Engineer same as
   finance desks"). A thin top bar, then the Security chat (its own conversation, kind 'seceng') beside the desk's pages: Today,
   Findings, Headers, Certificates, Tokens, Code, CI check, Settings. The pages call /api/secdesk/do/<part>; nothing is fetched or run. */
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

  const TABS = [['today', 'Today'], ['findings', 'Findings'], ['headers', 'Headers'], ['certificates', 'Certificates'], ['tokens', 'Tokens'], ['code', 'Code'], ['ci', 'CI check'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Where should an application security programme start?', 'Which scanners do I need?', 'What should block a release?'],
    findings: ['Which findings should I fix first?', 'How do I handle false positives?', 'What fix times are reasonable?'],
    headers: ['How do I roll out a Content-Security-Policy without breaking the site?', 'What should a session cookie look like?', 'Is HSTS preload worth it?'],
    certificates: ['How do I automate renewal?', 'RSA or ECDSA?', 'How do I check the chain a server sends?'],
    tokens: ['How long should access tokens live?', 'RS256 or HS256?', 'How should tokens be revoked?'],
    code: ['How do I stop SQL injection for good?', 'Is this pattern really exploitable?', 'How do I keep secrets out of code?'],
    ci: ['Should the gate block or warn?', 'What else should CI check for security?', 'How do I add CodeQL?'],
    settings: ['What fix times do standards ask for?', 'Which hosts should the certificate cover?', 'What is a sane token lifetime?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sub: 'findings', busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.secdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.secdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'security', name: 'Security'} : null;
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
  const run = (part, a) => api('POST', '/api/secdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/secdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Security Engineer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="secHire">Hire the Security Engineer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#secHire').onclick = async () => { try { await api('POST', '/api/employees/security_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Security</div><div class="sd-site" id="secSite"></div></div>
          <span id="secState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Security chat">
          <div class="sd-chathead"><div class="t"><b>Security chat</b><span>Paste a scanner report, headers, a certificate, a token or a diff - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="secFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="secPick" multiple hidden accept=".txt,.json,.sarif,.csv,.pem,.crt,.diff,.patch,.yaml,.yml,.log,.md,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Security desk" id="sdTabs"></nav>
          <div id="secPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a report or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#secPick').click()});
    $('#secPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.secdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.secdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/secdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#secPage').addEventListener('click', onPageClick);
    $('#secPage').addEventListener('submit', onSubmit);
    $('#secPage').addEventListener('change', onChange);
    $('#secPage').addEventListener('input', onInput);
    $('#secPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#secState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#secSite').textContent = [s.hosts && s.hosts.split(/[,\s]+/)[0], 'gate at ' + (s.fail_level || 'high'), pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), c = k.counts || {};
    const n = {};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/secdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#secPage'); if (!box) return;
    const fn = {today: pToday, findings: pFindings, headers: pHeaders, certificates: pCertificates, tokens: pTokens, code: pCode, ci: pCi, settings: pSettings}[ST.tab] || pToday;
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
  const pre = (t, cls) => `<pre class="sek-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = (...kinds) => (K().items || []).filter(x => !kinds.length || kinds.includes(x.kind));
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {bad: ['Serious', 'bad'], warn: ['Fix', 'warn'], info: ['Note', '']};
  const KN = {findings: 'Findings', headers: 'Headers', certs: 'Certificate', tokens: 'Tokens', code: 'Code'};
  const ROUTE = {findings: 'findings', headers: 'headers', certs: 'certificates', tokens: 'tokens', code: 'code'};
  const P4 = v => (v === null || v === undefined) ? '—' : String(+Number(v).toPrecision(4));
  const pc = v => (v === null || v === undefined) ? '—' : (Number(v) * 100).toFixed(0);
  const SEVT = {critical: ['Critical', 'bad'], high: ['High', 'bad'], medium: ['Medium', 'warn'], low: ['Low', ''], info: ['Info', '']};
  const sevTag = s => tag((SEVT[s] || [s])[0], (SEVT[s] || ['', ''])[1]);
  function brief(x) {
    const b = x.brief || {};
    switch (x.kind) {
      case 'findings': return `${pl(b.findings || 0, 'finding')} · ${num(b.critical || 0)} critical, ${num(b.high || 0)} high${b.new !== null && b.new !== undefined ? ` · ${num(b.new)} new, ${num(b.fixed || 0)} fixed` : ''}`;
      case 'headers': return `${num(b.passed || 0)} of ${num(b.total || 0)} checks pass${b.cookies ? ` · ${pl(b.cookies, 'cookie')}` : ''}`;
      case 'certs': return `${b.subject || ''} · ${b.days < 0 ? 'expired' : num(b.days) + ' days left'}`;
      case 'tokens': return `${pl(b.tokens || 0, 'token')} · ${num(b.flagged || 0)} with a problem`;
      case 'code': return `${pl(b.hits || 0, 'risky place')} · ${num(b.high || 0)} high · ${pl(b.lines || 0, b.diff ? 'added line' : 'line')}`;
    }
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="sek-list">${list.map(x => `<button type="button" class="sek-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(KN[x.kind])} · ${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="sek-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(KN[d.kind])} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="sek-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}${ask(d.number + ' ' + d.title)}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;
  const issueRows = list => (list || []).length ? list.map(i => `<div class="sek-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><p class="t">${esc(i.text)}</p>${i.area || i.fn ? `<span class="mut">${esc([i.area, i.fn].filter(Boolean).join(' · '))}</span>` : ''}${i.fix ? `<code class="sek-code">${esc(i.fix)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by these checks.</span></div>';
  const fld = (n, l, v, extra, ph) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(v ?? '')}" placeholder="${esc(ph || '')}" ${extra || ''}></label>`;
  const sel = (n, l, opts, v) => `<label class="ins-lab">${esc(l)}<select class="in" name="${n}">${opts.map(([k, t]) => `<option value="${esc(k)}"${String(k) === String(v) ? ' selected' : ''}>${esc(t)}</option>`).join('')}</select></label>`;
  const area = (n, l, ph, rows, wide = true) => `<label class="ins-lab${wide ? ' wide' : ''}">${esc(l)}<textarea class="in mono sek-ed" name="${n}" rows="${rows || 8}" spellcheck="false" placeholder="${esc(ph)}"></textarea></label>`;
  const fileBtn = (to, acc) => `<label class="btn soft sek-file">Open a file<input type="file" data-fileto="${to}" accept="${acc}" hidden></label>`;
  const subRow = (label, acc) => `<div class="sek-row wide">${fileBtn('text', acc || '.txt,text/*')}<input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">${esc(label)}</button></div>`;
  const verdict = (r, ok) => `<section class="card sek-sum ${ok ? 'okv' : 'badv'}"><p class="sek-big">${esc(r.verdict)}</p>${r.counts ? `<div class="sek-cnt">${['bad', 'warn', 'info'].map(s => `<span class="${s}"><b>${esc(num(r.counts[s] || 0))}</b>${esc({bad: 'serious', warn: 'to fix', info: 'notes'}[s])}</span>`).join('')}</div>` : ''}</section>`;
  const isOk = r => !(r.issues || []).some(i => i.sev === 'bad' || i.sev === 'warn');
  const stats = rows => `<div class="sek-stats">${rows.map(([l, v, c]) => `<div class="${c || ''}"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join('')}</div>`;
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
    const key = `<div class="sek-lkey">${series.map(s2 => `<span><i class="${s2.cls || ''}${s2.dash ? ' dash' : ''}"></i>${esc(s2.name)}</span>`).join('')}</div>`;
    return `<div class="sek-chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(aria)}">${grid}${ref}<line class="ax" x1="${L}" x2="${L}" y1="${T0}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>${paths}<text class="lab" x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle">${esc(xl)}</text><text class="lab" x="12" y="${(T0 + H - B) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(T0 + H - B) / 2})">${esc(yl)}</text></svg>${key}</div>`;
  }
  const CL = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];


  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), f = k.findings, h = k.headers, c = k.certs, d = k.code, s = st_();
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Findings', f ? esc(num((f.critical || 0) + (f.high || 0))) + ' <small>critical + high</small>' : '—', f ? `${pl(f.findings, 'finding')}${f.new !== null && f.new !== undefined ? ', ' + num(f.new) + ' new' : ''} · ${f.number}` : 'paste a scanner report', f && f.bad),
      tile('Headers', h ? esc(num(h.passed)) + `<small> of ${num(h.total)}</small>` : '—', h ? `checks pass · ${h.number}` : 'paste curl -sI output', h && h.bad),
      tile('Certificate', c ? (c.days < 0 ? 'expired' : esc(num(c.days)) + ' <small>days left</small>') : '—', c ? `${c.subject} · ${c.number}` : 'paste a chain', c && c.bad),
      tile('Code', d ? esc(num(d.high || 0)) + ' <small>high</small>' : '—', d ? `${pl(d.hits, 'risky place')} · ${d.number}` : 'paste a diff', d && d.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)} ${esc('Critical fixed within ' + s.sla_critical + ' days, high within ' + s.sla_high + '.')}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">The way through</h2><ol class="sek-path">
        <li><button type="button" data-go="findings"><b>Cut the noise</b><span>Every scanner's report in one list: what is serious, what is new, which upgrade closes most</span></button></li>
        <li><button type="button" data-go="headers"><b>Harden the edge</b><span>Security headers, cookies and certificates that hold up</span></button></li>
        <li><button type="button" data-go="code"><b>Catch it in review</b><span>Risky patterns in a change, before it ships</span></button></li>
        <li><button type="button" data-go="ci"><b>Make it automatic</b><span>A security gate on every pull request</span></button></li></ol></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- findings */
  const SAMPLE_F = '{"Results": [{"Target": "package-lock.json", "Vulnerabilities": [{"VulnerabilityID": "CVE-2024-0001", "PkgName": "lodash", "InstalledVersion": "4.17.20", "FixedVersion": "4.17.21", "Severity": "HIGH", "Title": "Prototype pollution"}]}]}';
  function pFindings() {
    if (ST.arg) return one(ST.arg, 'findings', pFi);
    return `<div><h1 class="sd-h">Findings</h1><p class="lead">Your scanners' reports read together: duplicates across tools merged, counted by severity, tool, rule and place, the package upgrades that close the most - and, against an older scan, what is new, fixed and still open, with due dates from your fix-time rules.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Triage a report</h2><form data-form="findings" class="sek-grid">
        ${area('text', "SARIF (CodeQL, Semgrep...), Trivy, Grype, Semgrep or ZAP JSON, or a CSV. Several reports: put '## name' before each. To compare, put the older scan after a '## baseline' line.", SAMPLE_F, 12)}
        ${fld('scan_date', 'Scan date (for due dates)', '', 'type="date"')}
        ${subRow('Triage it', '.json,.sarif,.csv,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Triaged</h2>${itemRows(items('findings'))}</section>`;
  }
  function pFi(d) {
    const r = d.result || {}, cs = r.counts_sev || {}, rows = r.rows || [];
    return `${head(d, 'findings')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Critical', esc(num(cs.critical || 0)), 'fix within ' + (r.sla || {}).critical + ' days', cs.critical > 0)}${tile('High', esc(num(cs.high || 0)), 'fix within ' + (r.sla || {}).high + ' days', cs.high > 0)}${tile('Medium and low', esc(num((cs.medium || 0) + (cs.low || 0))), num(cs.info || 0) + ' info')}${tile(r.baseline ? 'New' : 'Merged', r.baseline ? esc(num(r.new)) : esc(num(r.merged)), r.baseline ? num((r.fixed || []).length) + ' fixed since the baseline' : 'duplicates across tools', r.baseline && r.new > 0)}</div></section>
      ${(r.upgrades || []).length ? `<section class="card"><h2 class="md-h2">Upgrades that close the most</h2><div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>Package</th><th>Now</th><th>Upgrade to</th><th class="r">Closes</th><th>Worst</th></tr></thead><tbody>${r.upgrades.map(u => `<tr><td><b>${esc(u.pkg)}</b></td><td><code>${esc(u.now)}</code></td><td><code>${esc(u.to)}</code></td><td class="r">${esc(num(u.closes))}</td><td>${sevTag(u.worst)}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Every finding</h2><div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>Severity</th><th>Finding</th><th>Where</th><th>Fix in</th><th>Tools</th>${r.baseline ? '<th></th>' : ''}<th>Due</th></tr></thead><tbody>${rows.slice(0, 300).map(f => `<tr class="${f.sev === 'critical' || f.sev === 'high' ? 'bad' : ''}"><td>${sevTag(f.sev)}</td><td><b>${esc(f.rule)}</b><br><span class="mut">${esc(f.title)}</span></td><td><code>${esc(f.pkg || f.where)}</code></td><td><code>${esc(f.fixed_in || '—')}</code></td><td class="mut">${esc((f.tools || []).join(', '))}</td>${r.baseline ? `<td>${f.status === 'new' ? tag('New', 'warn') : ''}</td>` : ''}<td class="mut">${esc(f.due || '')}</td></tr>`).join('')}</tbody></table></div>${rows.length > 300 ? `<p class="cs-note">${num(rows.length - 300)} more not shown.</p>` : ''}</section>
      ${r.baseline && (r.fixed || []).length ? `<section class="card"><h2 class="md-h2">Fixed since the baseline</h2><div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>Severity</th><th>Finding</th><th>Where</th></tr></thead><tbody>${r.fixed.map(f => `<tr><td>${sevTag(f.sev)}</td><td>${esc(f.rule)}</td><td><code>${esc(f.pkg || f.where)}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <div class="sek-two"><section class="card"><h2 class="md-h2">By tool</h2>${bars((r.by_tool || []).map(x => [x.name, x.count, 'sek-b', num(x.serious) + ' critical / high']), v => num(v), 'Findings by tool')}</section>
      <section class="card"><h2 class="md-h2">By place</h2>${bars((r.by_where || []).slice(0, 10).map(x => [x.name, x.count, x.serious ? 'sek-b bad' : 'sek-b', num(x.serious) + ' critical / high']), v => num(v), 'Findings by place')}</section></div>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card sek-raw"><summary>What you pasted</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- headers */
  const SAMPLE_H = 'HTTP/2 200\ncontent-type: text/html\nstrict-transport-security: max-age=31536000; includeSubDomains\ncontent-security-policy: default-src \'self\'\nset-cookie: sid=abc; Path=/; HttpOnly';
  function pHeaders() {
    if (ST.arg) return one(ST.arg, 'headers', pHe);
    const s = st_();
    return `<div><h1 class="sd-h">Headers</h1><p class="lead">A response's security headers and cookies: HSTS, the Content-Security-Policy's script rules, framing, sniffing, referrer and permissions, version banners, cross-origin rules, and each cookie's flags and prefix rules.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check headers</h2><form data-form="headers" class="sek-grid">
        ${area('text', 'The output of `curl -sI https://your.site` (redirects included), or the response headers from the browser', SAMPLE_H, 10)}
        ${fld('url', 'Address', '', '', 'https://your.site')}${fld('hsts_days', 'HSTS at least (days)', s.hsts_days, 'type="number" min="1" step="1"')}
        ${subRow('Check them', '.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('headers'))}</section>`;
  }
  function pHe(d) {
    const r = d.result || {}, ck = r.checks || [], co = r.cookies || [];
    const yn = v => v ? '<span class="sek-v" aria-label="yes">✓</span>' : '<span class="sek-x" aria-label="no">✕</span>';
    return `${head(d, 'headers')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Checks', esc(num(r.passed)) + `<small> of ${num(r.total)}</small>`, 'pass', r.passed < r.total)}${tile('Cookies', esc(num(co.length)), num(co.filter(c => c.flags.length).length) + ' with a problem', co.some(c => c.flags.length))}${tile('Status', esc(r.status || '—'), (r.hops || []).length > 1 ? pl(r.hops.length - 1, 'redirect') : 'no redirects')}${tile('Address', r.url ? esc(r.url.replace(/^https?:\/\//, '').slice(0, 24)) : '—', r.url && r.url.startsWith('https') ? 'HTTPS' : '')}</div></section>
      <section class="card"><h2 class="md-h2">Checks</h2>${ck.map(c => `<div class="cs-row"><span class="cs-dot ${c.ok ? 'ok' : 'bad'}"></span><span><b>${esc(c.name)}</b> - ${esc(c.say)}</span></div>`).join('')}</section>
      ${co.length ? `<section class="card"><h2 class="md-h2">Cookies</h2><div class="iv-tw"><table class="tb in-cards sek-t sek-sc"><thead><tr><th>Cookie</th><th class="c">Secure</th><th class="c">HttpOnly</th><th>SameSite</th><th></th></tr></thead><tbody>${co.map(c => `<tr class="${c.flags.length ? 'warn' : ''}"><td><b>${esc(c.name)}</b>${c.session ? ' <span class="cs-tag">session</span>' : ''}</td><td class="c">${yn(c.secure)}</td><td class="c">${yn(c.httponly)}</td><td>${esc(c.samesite || '—')}</td><td>${c.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${Object.keys(r.csp || {}).length ? `<section class="card"><h2 class="md-h2">Content-Security-Policy</h2><div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>Directive</th><th>Sources</th></tr></thead><tbody>${Object.entries(r.csp).map(([k2, v]) => `<tr><td><b>${esc(k2)}</b></td><td><code>${esc(v.join(' '))}</code></td></tr>`).join('')}</tbody></table></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card sek-raw"><summary>All headers</summary><div class="iv-tw"><table class="tb in-cards sek-t"><tbody>${(r.headers || []).map(x => `<tr><td><b>${esc(x.name)}</b></td><td><code>${esc(x.value)}</code></td></tr>`).join('')}</tbody></table></div></details>`;
  }

  /* ---------------------------------------------------------------- certificates */
  function pCertificates() {
    if (ST.arg) return one(ST.arg, 'certificates', pCe);
    const s = st_();
    return `<div><h1 class="sd-h">Certificates</h1><p class="lead">A TLS certificate chain checked: days left, the names it covers, the key and the signature, whether it is in order and self-signed, and a leaf valid longer than browsers accept. Only public certificates - never a private key.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Check a chain</h2><form data-form="certs" class="sek-grid">
        ${area('text', 'PEM certificates (-----BEGIN CERTIFICATE-----), leaf first - or `openssl s_client -connect host:443 -servername host -showcerts </dev/null` output', '-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----', 12)}
        ${fld('hosts', 'Host names it must cover', s.hosts, '', 'www.example.com, api.example.com')}${fld('cert_warn_days', 'Warn before expiry (days)', s.cert_warn_days, 'type="number" min="1" step="1"')}
        ${subRow('Check it', '.pem,.crt,.cer,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Checked</h2>${itemRows(items('certs'))}</section>`;
  }
  function pCe(d) {
    const r = d.result || {}, cs = r.certs || [], lf = cs[0] || {};
    return `${head(d, 'certificates')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('Days left', lf.days_left < 0 ? 'expired' : esc(num(lf.days_left)), 'until ' + lf.not_after, lf.days_left < 30)}${tile('Key', esc(lf.key || '—'), lf.hash ? 'signed ' + lf.hash.toUpperCase() : '', lf.weak_key)}${tile('Chain', esc(num(r.count)), r.chain_ok ? 'in order' : 'out of order', !r.chain_ok)}${tile('Names', esc(num((lf.san || []).length)), (r.cover || []).length ? num(r.cover.filter(c => c.ok).length) + ' of ' + num(r.cover.length) + ' hosts covered' : 'set your hosts', (r.cover || []).some(c => !c.ok))}</div></section>
      <section class="card"><h2 class="md-h2">The chain</h2><ol class="sek-chain">${cs.map(c => `<li class="${c.days_left < 0 || c.weak_key ? 'bad' : c.days_left < 30 ? 'warn' : ''}"><div><b>${esc(c.subject)}</b> <span class="cs-tag">${esc(c.role)}</span>${c.self_signed ? ' <span class="cs-tag">self-signed</span>' : ''}</div><span class="mut">issued by ${esc(c.issuer)} · ${esc(c.not_before)} to ${esc(c.not_after)} · ${esc(c.key)} · ${esc((c.hash || '').toUpperCase())}</span>${c.san.length ? `<code class="sek-code">${esc(c.san.slice(0, 12).join(', '))}${c.san.length > 12 ? ' …' : ''}</code>` : ''}</li>`).join('')}</ol></section>
      ${(r.cover || []).length ? `<section class="card"><h2 class="md-h2">Host names</h2>${r.cover.map(c => `<div class="cs-row"><span class="cs-dot ${c.ok ? 'ok' : 'bad'}"></span><span><code>${esc(c.host)}</code> ${c.ok ? 'is covered' : 'is not covered'}</span></div>`).join('')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- tokens */
  function pTokens() {
    if (ST.arg) return one(ST.arg, 'tokens', pTo);
    const s = st_();
    return `<div><h1 class="sd-h">Tokens</h1><p class="lead">JWTs decoded without trusting them: algorithm none, keys taken from the token, no expiry, a life longer than your rule, missing issuer or audience, and personal data anyone holding it can read. The signature is removed before anything is saved.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Read tokens</h2><form data-form="tokens" class="sek-grid">
        ${area('text', 'One or more JWTs (eyJ...). Use test or expired tokens - a live token is a key to the account.', 'eyJhbGciOi...', 6)}
        ${fld('token_hours', 'Longest life (hours)', s.token_hours, 'type="number" min="0.01" step="any"')}${fld('expect_alg', 'Expected algorithm', s.expect_alg, 'maxlength="10"', 'RS256')}
        ${subRow('Read them', '.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Read</h2>${itemRows(items('tokens'))}</section>`;
  }
  function pTo(d) {
    const r = d.result || {}, rows = r.rows || [];
    return `${head(d, 'tokens')}${verdict(r, isOk(r))}
      <section class="card"><h2 class="md-h2">Each token</h2><div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>#</th><th>Algorithm</th><th>Issuer</th><th>Audience</th><th>Expires</th><th class="r">Life</th><th>Claims</th><th></th></tr></thead><tbody>${rows.map(t => `<tr class="${t.flags.some(f => ['alg none', 'no expiry', 'no signature'].includes(f)) ? 'bad' : t.flags.length ? 'warn' : ''}"><td>${esc(t.n)}</td><td><code>${esc(t.alg || '—')}</code></td><td>${esc(t.iss || '—')}</td><td>${esc(Array.isArray(t.aud) ? t.aud.join(', ') : (t.aud || '—'))}</td><td>${esc(t.exp)}</td><td class="r">${t.life_h === null || t.life_h === undefined ? '—' : esc(P4(t.life_h)) + ' h'}</td><td class="mut">${esc(t.claims.join(', '))}</td><td>${t.flags.map(f => `<span class="cs-tag">${esc(f)}</span>`).join(' ')}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>`;
  }

  /* ---------------------------------------------------------------- code */
  const SAMPLE_C = 'diff --git a/app/api.py b/app/api.py\n--- a/app/api.py\n+++ b/app/api.py\n@@ -10,2 +10,3 @@\n def get(uid):\n+    cur.execute(f"SELECT * FROM users WHERE id={uid}")';
  function pCode() {
    if (ST.arg) return one(ST.arg, 'code', pCo);
    return `<div><h1 class="sd-h">Code</h1><p class="lead">A change read for risky code the way a first security review pass does: code built from strings and run, unsafe deserialisation, shell and SQL built from input, HTML from data, certificate checks off, weak hashes and random numbers, debug modes, unverified tokens and passwords in the code - each with its CWE and the safe way.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Review a change</h2><form data-form="code" class="sek-grid">
        ${area('text', "A unified diff (`git diff` - only the added lines are read), or code with '## path/to/file.py' before each file", SAMPLE_C, 12)}
        ${sel('lang', 'Language (when the file names do not say)', [['', 'From the file names'], ['py', 'Python'], ['js', 'JavaScript / TypeScript'], ['java', 'Java / Kotlin'], ['go', 'Go'], ['php', 'PHP'], ['rb', 'Ruby'], ['cs', 'C#']], '')}
        ${subRow('Review it', '.diff,.patch,.py,.js,.ts,.java,.go,.php,.rb,.cs,.txt,text/*')}</form></section>` : ''}
      <section class="card"><h2 class="md-h2">Reviewed</h2>${itemRows(items('code'))}</section>`;
  }
  function pCo(d) {
    const r = d.result || {}, hs = r.hits || [], sv = r.sev || {};
    const ST2 = {high: ['High', 'bad'], medium: ['Medium', 'warn'], low: ['Low', '']};
    return `${head(d, 'code')}${verdict(r, isOk(r))}
      <section class="cs-hero"><div class="top">${tile('High', esc(num(sv.high || 0)), 'fix before it ships', sv.high > 0)}${tile('Medium', esc(num(sv.medium || 0)), 'look at each')}${tile('Low', esc(num(sv.low || 0)), '')}${tile(r.diff ? 'Added lines' : 'Lines', esc(num(r.lines)), pl((r.files || []).length, 'file'))}</div></section>
      ${(r.by_rule || []).length ? `<section class="card"><h2 class="md-h2">By kind</h2>${bars(r.by_rule.map(x => [x.what, x.count, x.sev === 'high' ? 'sek-b bad' : 'sek-b', x.cwe]), v => num(v), 'Risky places by kind')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Each place</h2>${hs.length ? `<div class="iv-tw"><table class="tb in-cards sek-t"><thead><tr><th>Where</th><th>Code</th><th>What</th><th>The safe way</th><th></th></tr></thead><tbody>${hs.map(h => `<tr class="${h.sev === 'high' ? 'bad' : h.sev === 'medium' ? 'warn' : ''}"><td><code>${esc((h.file || '') + ':' + h.line)}</code></td><td><code>${esc(h.code)}</code></td><td>${esc(h.what)} <span class="mut">${esc(h.cwe)}</span></td><td class="mut">${esc(h.fix)}</td><td>${tag(ST2[h.sev][0], ST2[h.sev][1])}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">No risky pattern found - which is not proof the code is safe.</p>'}</section>
      <section class="card"><h2 class="md-h2">Findings</h2>${issueRows(r.issues)}<p class="cs-note">${esc(r.note)}</p></section>
      <details class="card sek-raw"><summary>What you pasted (secrets cut)</summary>${pre(d.text.slice(0, 60000), 'code')}</details>`;
  }

  /* ---------------------------------------------------------------- CI */
  function pCi() {
    const s = st_(), w = ST.out.ci;
    if (w === undefined) lazyOut('ci', 'ci', {});
    return `<div><h1 class="sd-h">CI check</h1><p class="lead">A GitHub Actions security gate: every pull request's added lines are read with the same risky-code rules as the Code page, and the check fails at your level. It needs no keys and changes nothing.</p></div>
      <section class="card"><h2 class="md-h2">What it holds</h2><div class="ar-facts">${[['Fails at', s.fail_level + ' and above'], ['Branches', s.branches || 'every pull request'], ['Runner', s.runner]].map(([k2, v]) => `<div><dt>${esc(k2)}</dt><dd>${esc(v)}</dd></div>`).join('')}</div>
        <div class="md-acts"><span class="mut" style="font-size:13px">Change these in Settings.</span><button class="btn soft sm" type="button" data-go="settings">Settings</button></div></section>
      <section class="card">${!w ? loading() : w.error ? err(w) : `<div class="md-acts" style="margin-top:0"><code>${esc(w.file)}</code><span>${copyBtn(w.yaml)} <button class="btn soft sm" type="button" data-dl="security-gate.yml" data-dltext="${esc(w.yaml)}">Download</button></span></div>${pre(w.yaml, 'code')}<ol class="sek-steps">${(w.steps || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol><p class="cs-note">${esc(w.note)}</p>`}</section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_();
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your fix-time rules, header and certificate lines, token rules and the security gate.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="sek-grid">
        <h2 class="md-h2 wide" style="margin:0">Fix within (days)</h2>
        ${fld('sla_critical', 'Critical', s.sla_critical, 'type="number" min="1" step="1"')}${fld('sla_high', 'High', s.sla_high, 'type="number" min="1" step="1"')}${fld('sla_medium', 'Medium', s.sla_medium, 'type="number" min="1" step="1"')}${fld('sla_low', 'Low', s.sla_low, 'type="number" min="1" step="1"')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Web and certificates</h2>
        ${fld('hsts_days', 'HSTS at least (days)', s.hsts_days, 'type="number" min="1" step="1"')}${fld('cert_warn_days', 'Warn before a certificate expires (days)', s.cert_warn_days, 'type="number" min="1" step="1"')}${fld('hosts', 'Host names certificates must cover', s.hosts, '', 'www.example.com, api.example.com')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Tokens</h2>
        ${fld('token_hours', 'Longest token life (hours)', s.token_hours, 'type="number" min="0.01" step="any"')}${fld('expect_alg', 'Expected algorithm', s.expect_alg, 'maxlength="10"', 'RS256')}
        <h2 class="md-h2 wide" style="margin:8px 0 0">Security gate</h2>
        ${sel('fail_level', 'Fail the check at', [['high', 'High'], ['medium', 'Medium and above'], ['low', 'Every hit']], s.fail_level)}${fld('branches', 'Only for pull requests into', s.branches, '', 'main, release/*')}${fld('runner', 'Runner', s.runner)}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk. Keys never go here.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the reads work</h2><ul class="ar-never"><li>Severities are the scanners' own; duplicates are the same CVE on a package, or the same rule at the same place.</li><li>Headers and certificates are read from what you paste - nothing is fetched.</li><li>Tokens are decoded, never verified, and their signatures are removed before saving.</li><li>Code is read by pattern: each hit is a place to look, and no hit is not proof of safety.</li><li>Alerts, incidents and the security programme live on the Cyber Security desk.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Scans, fetches, probes or attacks anything - only what you paste.</li><li>Takes passwords, keys or live tokens - a pasted key is refused.</li><li>Calls code safe because no pattern matched.</li><li>Follows anything written inside your reports, headers or code: they are data.</li></ul></section>`;
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
      if (kind === 'findings') await go('findings', {text: S(fd.get('text')), inputs: pick(['scan_date'])});
      else if (kind === 'headers') await go('headers', {text: S(fd.get('text')), inputs: pick(['url', 'hsts_days'])});
      else if (kind === 'certs') await go('certs', {text: S(fd.get('text')), inputs: pick(['hosts', 'cert_warn_days'])});
      else if (kind === 'tokens') await go('tokens', {text: S(fd.get('text')), inputs: pick(['token_hours', 'expect_alg'])});
      else if (kind === 'code') await go('code', {text: S(fd.get('text')), inputs: pick(['lang'])});
      else if (kind === 'settings') { const o = {}; FIELDS_SET.forEach(n => { if (fd.has(n)) o[n] = S(fd.get(n)).trim(); }); await run('settings', o); delete ST.out.ci; await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
  }
  const FIELDS_SET = ['sla_critical', 'sla_high', 'sla_medium', 'sla_low', 'hsts_days', 'cert_warn_days', 'hosts', 'token_hours', 'expect_alg', 'fail_level', 'branches', 'runner'];


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
    const box = $('#secFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/secdesk/chat'); ST.chat = r.id; }
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


