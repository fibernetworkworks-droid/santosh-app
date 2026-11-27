/* NOC DESK - the NOC (ISP network) employee's own section, like the finance desks (owner: "NOC same as finance desks").
   A thin top bar, then the NOC chat (its own conversation, kind 'noc') beside the desk's pages: Today, Faults, Tickets, Changes,
   Network, Collectors, Settings. The pages call /api/ncdesk/do/<part>, which runs the NOC engine. Nothing on her equipment changes
   without her tap, customer messages are hers to send, and device passwords never come to Hoola. */
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

  const TABS = [['today', 'Today'], ['faults', 'Faults'], ['tickets', 'Tickets'], ['changes', 'Changes'], ['network', 'Network'],
    ['collectors', 'Collectors'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['Who is down right now?', 'What should the field team do first?', 'Summarise the network for today'],
    faults: ['Is this a fibre cut or a power cut?', 'Write the customer message', 'Which splitter should we check?'],
    tickets: ['Which ticket is most late?', 'Remind the field team', 'How fast do we fix faults?'],
    changes: ['Is it safe to reset this PON?', 'Explain these commands', 'What is the way back if it fails?'],
    network: ['Which customers have weak light?', 'Is this route within the light budget?', 'Which PON fails most?'],
    collectors: ['How do I set up a collector?', 'Is the collector safe?', 'Why is my collector offline?'],
    settings: ['What SLA hours should I set?', 'Who should be on the field team?', 'Which rules apply in my country?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', ff: 'open', oq: '', cedit: '', ing: null, busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.ncdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.ncdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'noc', name: ((K().settings || {}).isp_name) || 'Your network'} : null;
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
  const run = (part, a) => api('POST', '/api/ncdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/ncdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your NOC is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="ncHire">Hire the NOC</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#ncHire').onclick = async () => { try { await api('POST', '/api/employees/noc/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">NOC</div><div class="sd-site" id="ncSite"></div></div>
          <span id="ncState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="NOC chat">
          <div class="sd-chathead"><div class="t"><b>NOC chat</b><span>Paste alarm lines, ask who is down or what to do next - or drop an OLT log or an alert email here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="ncFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="ncPick" multiple hidden accept="image/*,.pdf,.csv,.xlsx,.txt,.log,.eml,.docx">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="NOC desk" id="sdTabs"></nav>
          <div id="ncPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing on your equipment changes without your tap.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste alarms or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#ncPick').click()});
    $('#ncPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.ncdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.ncdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/ncdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#ncPage').addEventListener('click', onPageClick);
    $('#ncPage').addEventListener('submit', onSubmit);
    $('#ncPage').addEventListener('change', onChange);
    $('#ncPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#ncState'); if (!el) return;
    const k = K(), st = k.settings || {}, fs = (k.faults || []).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : k.waiting ? ['warn', 'Waiting for your tap'] : fs ? ['warn', pl(fs, 'open fault')] : ['ok', 'Network fine'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    $('#ncSite').textContent = [st.isp_name, pl(((k.network || {}).olts || []).length, 'OLT'), pl((k.network || {}).onts || 0, 'customer'), st.country || ''].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K();
    const n = {faults: (k.faults || []).length || '', tickets: k.late || '', changes: k.waiting || '', collectors: (k.collectors || []).filter(c => !c.online && c.last_seen).length || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/ncdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#ncPage'); if (!box) return;
    const fn = {today: pToday, faults: pFaults, tickets: pTickets, changes: pChanges, network: pNetwork, collectors: pCollectors, settings: pSettings}[ST.tab] || pToday;
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
  const FST = {open: ['Open', 'bad'], ticketed: ['Ticket made', 'warn'], resolved: ['Fixed', 'ok'], dismissed: ['Merged / removed', '']};
  const TST = {open: ['Open', 'bad'], assigned: ['Assigned', 'warn'], on_site: ['On site', 'warn'], fixed: ['Fixed', 'ok'], closed: ['Closed', ''], cancelled: ['Cancelled', '']};
  const CST = {waiting: 'warn', approved: 'v', queued: 'v', running: 'v', done: 'ok', failed: 'bad', rejected: '', cancelled: ''};
  const fTag = f => tag((FST[f.status] || [f.status_label || f.status])[0], (FST[f.status] || ['', ''])[1]);
  const tTag = t => tag((TST[t.status] || [cap(t.status)])[0], (TST[t.status] || ['', ''])[1]);
  const teamOpts = sel => Object.entries(K().teams || {}).map(([k, v]) => `<option value="${esc(k)}"${k === sel ? ' selected' : ''}>${esc(v)}</option>`).join('');
  const pasteBox = (lead) => CAN() ? `<section class="card"><h2 class="md-h2">Paste alarms</h2><p class="mut" style="margin:0 0 10px;font-size:14px">${esc(lead)}</p>
    <form data-form="alarms" class="nc-paste"><textarea class="in nc-mono" name="text" rows="5" placeholder="2026-11-27 10:15:01 OLT-1 GPON0/1:12 ONU LOS alarm&#10;2026-11-27 10:15:03 OLT-1 GPON0/1:13 dying gasp"></textarea>
      <div class="ar-row" style="margin-top:0"><label class="ins-lab" style="flex:1">Which OLT (if the lines do not say)<select class="in" name="olt"><option value="">Read it from the lines</option>${(((K().network || {}).olts) || []).map(o => `<option value="${esc(o.id)}">${esc(o.name)}</option>`).join('')}</select></label>
      <button class="btn" type="submit">Find the fault</button></div></form></section>` : '';

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), net = k.network || {}, rep = k.report || {}, fs = k.faults || [];
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : fs.length ? `${pl(fs.length, 'open fault')}, every one with a ticket - the teams are on it.` : 'All in order: no open faults.';
    const tiles = [
      `<div class="k${fs.length ? ' low bad' : ''}"><div class="l">Open faults</div><div class="v">${esc(num(fs.length))}</div><div class="s">${esc(pl(k.down || 0, 'customer'))} down</div></div>`,
      `<div class="k"><div class="l">Customers</div><div class="v">${esc(num(net.onts_active || 0))}</div><div class="s">${esc(num(net.weak_rx || 0))} with weak light</div></div>`,
      `<div class="k${k.late ? ' low bad' : ''}"><div class="l">Tickets past SLA</div><div class="v">${esc(num(k.late || 0))}</div><div class="s">${esc(pl((k.tickets || []).length, 'ticket'))} open</div></div>`,
      `<div class="k${k.waiting ? ' low bad' : ''}"><div class="l">Changes to approve</div><div class="v">${esc(num(k.waiting || 0))}</div><div class="s">nothing changes without your tap</div></div>`];
    return `<div><h1 class="sd-h">${greet()}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      <div class="md-2" style="align-items:start">
        <section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs) || empty('Nothing needs you right now.')}</section>
        <section class="card"><h2 class="md-h2">Open faults</h2>${fs.length ? fs.slice(0, 6).map(f => `<div class="cs-row"><span class="cs-dot bad"></span><span style="flex:1"><b>${esc(f.number)}</b> ${esc(f.title)} <span class="mut">· ${esc(f.olt || '?')}${f.pon ? ' PON ' + esc(f.pon) : ''} · ${esc(pl(f.n_affected, 'customer'))} · ${esc(f.duration)}</span></span><button class="btn soft sm" type="button" data-fault="${esc(f.number)}">Open</button></div>`).join('') : empty('No open faults.')}</section></div>
      ${pasteBox('An OLT alarm log, a syslog, an SNMP trap or an alert email - exactly as it is. It is read as data.')}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Last 30 days</h2><div class="r"><span class="mut" style="font-size:13px">${esc([rep.availability_pct !== null && rep.availability_pct !== undefined ? rep.availability_pct + '% service' : '', rep.mttr_hours !== null && rep.mttr_hours !== undefined ? 'fixed in ' + rep.mttr_hours + ' h on average' : ''].filter(Boolean).join(' · '))}</span></div></div>
        <div class="md-2" style="align-items:start"><div><h3 class="nc-h3">Faults by kind</h3>${(rep.by_kind || []).length ? bars(rep.by_kind.map(x => [x.title, x.count, 'mk-b', x.mttr_hours !== null ? 'fixed in ' + x.mttr_hours + ' h' : '']), num, 'Faults by kind') : empty('No faults in 30 days.')}</div>
          <div><h3 class="nc-h3">Where they happen</h3>${(rep.top_pons || []).length ? bars(rep.top_pons.map(x => [x.pon, x.count, 'mk-b']), num, 'Faults by PON') : empty('Nothing yet.')}
            ${(rep.teams || []).length ? `<h3 class="nc-h3">Teams</h3>${rep.teams.map(t => `<div class="cs-row"><span style="flex:1">${esc(t.label)}</span><span class="mut" style="font-size:13px">${esc(pl(t.tickets, 'ticket'))} · ${t.sla_pct !== null ? esc(t.sla_pct) + '% in SLA' : 'none fixed yet'}</span></div>`).join('')}` : ''}</div></div>
        ${(rep.tips || []).map(t => `<p class="cs-note">${esc(t)}</p>`).join('')}</section>`;
  }

  /* ---------------------------------------------------------------- faults */
  function pFaults() {
    if (ST.arg) return pFault(ST.arg);
    const all = lazyOut('fl:' + ST.ff, 'faults', {status: ST.ff});
    return `<div class="cs-head"><div><h1 class="sd-h">Faults</h1><p class="lead">What really broke, behind the alarms.</p></div>
        <div class="r"><select class="in sm" data-ff="1" aria-label="Show">${[['open', 'Open'], ['resolved', 'Fixed'], ['dismissed', 'Merged / removed'], ['all', 'All']].map(([a, b]) => `<option value="${a}"${ST.ff === a ? ' selected' : ''}>${b}</option>`).join('')}</select></div></div>
      ${pasteBox('New alarms join the open faults or make new ones; a cleared alarm can fix a fault by itself.')}
      ${ST.ing ? `<section class="card"><p style="margin:0">${esc(ST.ing.say)}</p></section>` : ''}
      <section class="card">${!all ? '<p class="mut" style="margin:0">Working it out…</p>' : all.error ? err(all) : (all.faults || []).length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Fault</th><th>Where</th><th class="r">Affected</th><th>Since</th><th>Status</th><th></th></tr></thead><tbody>${all.faults.map(f => `<tr>
        <td><b>${esc(f.number)}</b> ${esc(f.title)}<div class="mut" style="font-size:12px">${esc(f.confidence_label)}</div></td><td>${esc(f.olt || '?')}${f.pon ? ' · PON ' + esc(f.pon) : ''}</td>
        <td class="r">${esc(num(f.n_affected))}</td><td>${esc(f.started)}<div class="mut" style="font-size:12px">${esc(f.duration)}</div></td><td>${fTag(f)}</td>
        <td class="r"><button class="btn soft sm" type="button" data-fault="${esc(f.number)}">Open</button></td></tr>`).join('')}</tbody></table></div>` : empty('No faults here.')}</section>`;
  }
  function pFault(ref) {
    const f = lazyOut('f:' + ref, 'fault_get', {fault: ref});
    const back = `<div><button class="btn soft sm" type="button" data-go="faults">${svg(IC.back)}<span>All faults</span></button></div>`;
    if (!f) return back + loading();
    if (f.error) return back + `<section class="card">${err(f)}</section>`;
    const loc = f.location || {}, msg = ST.out['m:' + f.number], open = ['open', 'ticketed'].includes(f.status);
    return `${back}
      <div class="nc-head"><div><h1 class="sd-h">${esc(f.number)} · ${esc(f.title)}</h1><p class="lead">${esc(f.olt || '?')}${f.pon ? ' · PON ' + esc(f.pon) : ''}${f.target && ['splitter', 'ont', 'uplink'].includes(f.scope) ? ' · ' + esc(f.target) : ''} · since ${esc(f.started)} (${esc(f.duration)})</p></div><div>${fTag(f)}</div></div>
      <section class="cs-hero"><div class="top">
        <div class="k${open ? ' low bad' : ''}"><div class="l">Customers affected</div><div class="v">${esc(num(f.n_affected))}</div><div class="s">${f.n_total ? 'of ' + esc(num(f.n_total)) + ' on it' : '&nbsp;'}</div></div>
        <div class="k"><div class="l">How sure</div><div class="v nc-sm">${esc(f.confidence_label)}</div><div class="s">${esc(Math.round((f.confidence || 0) * 100))}%</div></div>
        <div class="k"><div class="l">Who fixes it</div><div class="v nc-sm">${esc(f.team_label)}</div><div class="s">${f.sla_hours ? 'within ' + esc(f.sla_hours) + ' h' : 'no SLA set'}</div></div>
        <div class="k"><div class="l">Due</div><div class="v nc-sm">${esc(f.due || '—')}</div><div class="s">from your SLA hours</div></div></div></section>
      <section class="card"><h2 class="md-h2">What happened</h2><p style="margin:0 0 10px">${esc(f.explain)}</p>
        ${(f.reasons || []).length ? `<h3 class="nc-h3">Why it looks so</h3><ul class="ar-never">${f.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}
        ${(f.notes || []).map(n => `<p class="cs-note">${esc(n)}</p>`).join('')}
        ${loc.site || loc.splitter ? `<h3 class="nc-h3">Where to go</h3><div class="nc-loc">${loc.site ? `<div><b>${esc(loc.site)}</b><span class="mut">${esc(loc.address || '')}${loc.power ? ' · power: ' + esc(loc.power) : ''}</span>${loc.maps ? `<a href="${esc(loc.maps)}" target="_blank" rel="noopener noreferrer">Open in Maps</a>` : ''}</div>` : ''}
          ${loc.splitter ? `<div><b>Splitter ${esc(loc.splitter)}</b><span class="mut">${esc(loc.splitter_location || '')}${loc.km ? ' · ' + esc(loc.km) + ' km' : ''}</span>${loc.splitter_maps ? `<a href="${esc(loc.splitter_maps)}" target="_blank" rel="noopener noreferrer">Open in Maps</a>` : ''}</div>` : ''}</div>` : ''}</section>
      ${(f.tickets || []).length ? `<section class="card"><h2 class="md-h2">Tickets</h2>${f.tickets.map(t => ticketRow(t)).join('')}</section>` : ''}
      ${open && CAN() ? `<section class="card"><h2 class="md-h2">Open a ticket</h2><form data-form="ticket" data-id="${esc(f.number)}" class="nc-grid">
          <label class="ins-lab">Team<select class="in" name="team">${teamOpts(f.team)}</select></label>
          <label class="ins-lab">Who<input class="in" name="assignee" placeholder="from your team list"></label>
          <label class="ins-lab">Phone<input class="in" name="phone" placeholder="+country code and number"></label>
          <label class="ins-lab">Expected fix<input class="in" name="eta" placeholder="2 hours, 6 pm, 18:30"></label>
          <label class="ins-lab wide">Note<input class="in" name="note"></label>
          <div class="md-acts wide"><span class="mut" style="font-size:13px">Hoola writes the ticket; you send it on WhatsApp or by phone.</span><button class="btn" type="submit">Make the ticket</button></div></form></section>` : ''}
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Message to customers</h2><div class="r"><button class="btn soft sm" type="button" data-msg="${esc(f.number)}" data-restored="${f.status === 'resolved' ? '1' : '0'}">${msg ? 'Write it again' : 'Write it'}</button></div></div>
        ${msg ? (msg.error ? err(msg) : `<p class="nc-msg">${esc(msg.text || 'No message is needed for this fault.')}</p><p class="mut" style="font-size:13px;margin:0">${esc(msg.say)}</p>
          ${msg.text ? `<div class="md-acts" style="gap:6px"><span></span><button class="btn soft sm" type="button" data-copy="${esc(f.number)}">Copy text${msg.count ? ' + ' + esc(pl(msg.count, 'number')) : ''}</button><a class="btn sm" href="${esc(msg.wa_link)}" target="_blank" rel="noopener noreferrer">Open in WhatsApp</a></div>` : ''}`)
          : '<p class="mut" style="margin:0;font-size:14px">For the customers it affects. You send it from your own WhatsApp or SMS - Hoola sends nothing.</p>'}</section>
      ${(f.suggest || []).length && open && CAN() ? `<section class="card"><h2 class="md-h2">A change that may help</h2>${f.suggest.map(sg => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">${esc((K().actions || {})[sg.action] || sg.action)} - ${esc(sg.why)}</span><button class="btn soft sm" type="button" data-sugg="${esc(JSON.stringify({...sg, fault: f.number}))}">Make a card</button></div>`).join('')}<p class="cs-note">A card only - it waits for your approval on Changes.</p></section>` : ''}
      ${(f.affected || []).length ? `<section class="card"><h2 class="md-h2">${esc(pl(f.affected.length, 'customer'))} affected</h2><div class="iv-tw"><table class="tb"><thead><tr><th>Customer</th><th>Phone</th><th>Where</th></tr></thead><tbody>${f.affected.slice(0, 60).map(x => `<tr><td>${esc(x.customer || x.label || '—')}</td><td>${esc(x.phone || '')}</td><td class="mut">${esc(x.address || x.splitter || '')}</td></tr>`).join('')}</tbody></table></div></section>` : ''}
      ${open && CAN() ? `<section class="card"><h2 class="md-h2">Close it</h2><form data-form="resolve" data-id="${esc(f.number)}" class="ar-row"><label class="ins-lab" style="flex:1">What fixed it<input class="in" name="note" placeholder="Fibre spliced at Market chowk"></label>
          <button class="btn soft" type="submit" data-how="dismiss">Not a real fault</button><button class="btn" type="submit" data-how="resolve">Fixed</button></form></section>` : ''}
      ${(f.log || []).length ? `<section class="card"><h2 class="md-h2">Log</h2>${f.log.slice().reverse().map(l => `<div class="cs-row"><span class="cs-dot"></span><span style="flex:1">${esc(l.text || l)}</span><span class="mut" style="font-size:12px">${esc(l.by || '')} ${esc(l.at ? dt(l.at) : '')}</span></div>`).join('')}</section>` : ''}`;
  }
  function ticketRow(t) {
    return `<div class="nc-tk"><div class="h"><b>${esc(t.number)}</b> <span class="mut">${esc(t.team_label)}${t.assignee ? ' · ' + esc(t.assignee) : ''}${t.fault ? ' · ' + esc(t.fault) : ''}</span><span style="flex:1"></span>${t.late ? tag('Past SLA', 'bad') : ''}${tTag(t)}</div>
      <div class="mut" style="font-size:13px">Made ${esc(t.created)}${t.eta ? ' · expected ' + esc(t.eta) : ''}${t.due ? ' · due ' + esc(t.due) : ''}${t.mttr_hours !== null && t.mttr_hours !== undefined ? ' · fixed in ' + esc(t.mttr_hours) + ' h' : ''}${t.ext_ref ? ' · ref ' + esc(t.ext_ref) : ''}</div>
      ${CAN() && !['fixed', 'closed', 'cancelled'].includes(t.status) ? `<div class="md-acts" style="gap:6px;flex-wrap:wrap"><span></span>${t.wa_link ? `<a class="btn soft sm" href="${esc(t.wa_link)}" target="_blank" rel="noopener noreferrer">Send on WhatsApp</a>` : ''}${t.tel ? `<a class="btn soft sm" href="${esc(t.tel)}">Call</a>` : ''}
        ${t.status === 'open' || t.status === 'assigned' ? `<button class="btn soft sm" type="button" data-tst="on_site" data-tk="${esc(t.number)}">On site</button>` : ''}<button class="btn sm" type="button" data-tst="fixed" data-tk="${esc(t.number)}">Fixed</button></div>` : ''}</div>`;
  }

  /* ---------------------------------------------------------------- tickets */
  function pTickets() {
    const ts = K().tickets || [];
    return `<div><h1 class="sd-h">Tickets</h1><p class="lead">${ts.length ? esc(pl(ts.length, 'open ticket')) + ', with their SLA from your hours.' : 'No open tickets.'}</p></div>
      <section class="card">${ts.length ? ts.map(ticketRow).join('') : empty('Open a ticket from a fault.')}</section>`;
  }

  /* ---------------------------------------------------------------- changes */
  function pChanges() {
    const cs = K().changes || [];
    return `<div><h1 class="sd-h">Changes</h1><p class="lead">A change on your equipment is only a card until you approve it - with the exact commands and the way back.</p></div>${ro()}
      ${cs.length ? cs.map(c => `<section class="card nc-ch${c.status === 'waiting' ? ' wait' : ''}"><div class="cs-head"><div><h2 class="md-h2" style="margin:0">${esc(c.number)} · ${esc(c.action_label)}</h2><span class="mut" style="font-size:13px">${esc(c.olt || '?')}${c.pon ? ' · PON ' + esc(c.pon) : ''}${c.onu ? ' ONU ' + esc(c.onu) : ''} · ${esc(c.created)}${c.reason ? ' · ' + esc(c.reason) : ''}</span></div>
          <div class="r">${tag(c.status_label, CST[c.status] || '')}</div></div>
        <p class="cs-note">${esc(c.risk || '')}</p>
        ${c.warn ? `<p class="cs-neg" style="margin:0 0 8px;font-size:13px">${esc(c.warn)}</p>` : ''}
        <div class="md-2" style="align-items:start"><div><h3 class="nc-h3">Commands</h3><pre class="ar-code"><code>${esc((c.commands || []).join('\n') || '—')}</code></pre></div>
          <div><h3 class="nc-h3">The way back</h3><pre class="ar-code"><code>${esc((c.rollback || []).join('\n') || '—')}</code></pre></div></div>
        ${c.steps ? `<details class="nc-steps"><summary>How to do it yourself</summary><pre class="ar-code"><code>${esc(c.steps)}</code></pre></details>` : ''}
        ${c.output ? `<h3 class="nc-h3">What the OLT said</h3><pre class="ar-code"><code>${esc(c.output)}</code></pre>` : ''}
        ${CAN() && c.status === 'waiting' ? `<div class="md-acts" style="gap:6px;flex-wrap:wrap"><button class="btn soft sm" type="button" data-cedit="${esc(c.number)}">Edit the commands</button><span style="flex:1"></span><button class="btn soft sm" type="button" data-cdec="${esc(c.number)}" data-hash="${esc(c.hash)}" data-yes="0">Decline</button><button class="btn sm" type="button" data-cdec="${esc(c.number)}" data-hash="${esc(c.hash)}" data-yes="1">Approve</button></div>
          ${ST.cedit === c.number ? `<form data-form="cedit" data-id="${esc(c.number)}" class="nc-grid" style="margin-top:10px"><label class="ins-lab wide">Commands (one a line)<textarea class="in nc-mono" name="commands" rows="4">${esc((c.commands || []).join('\n'))}</textarea></label><label class="ins-lab wide">The way back<textarea class="in nc-mono" name="rollback" rows="3">${esc((c.rollback || []).join('\n'))}</textarea></label><div class="md-acts wide"><span class="mut" style="font-size:13px">A new card is made; you approve that one.</span><button class="btn" type="submit">Save</button></div></form>` : ''}` : ''}
        ${CAN() && c.status === 'approved' ? `<form data-form="cdone" data-id="${esc(c.number)}" class="nc-grid" style="margin-top:10px"><label class="ins-lab wide">After you ran it: what the OLT said (optional)<textarea class="in nc-mono" name="output" rows="2"></textarea></label><div class="md-acts wide"><span></span><button class="btn soft sm" type="submit" data-ok="0">It did not work</button><button class="btn sm" type="submit" data-ok="1">Done, it worked</button></div></form>` : ''}</section>`).join('') : `<section class="card">${empty('No changes yet.')}</section>`}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Ask for a change</h2><form data-form="change" class="nc-grid">
        <label class="ins-lab">What<select class="in" name="action_kind">${Object.entries(K().actions || {}).map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join('')}</select></label>
        <label class="ins-lab">OLT<select class="in" name="olt">${(((K().network || {}).olts) || []).map(o => `<option value="${esc(o.id)}">${esc(o.name)}</option>`).join('')}</select></label>
        <label class="ins-lab">PON<input class="in" name="pon" placeholder="0/1"></label><label class="ins-lab">ONU<input class="in" name="onu" placeholder="12"></label>
        <label class="ins-lab wide">Why<input class="in" name="reason"></label>
        <div class="md-acts wide"><span class="mut" style="font-size:13px">Hoola writes the commands for your OLT's make and the way back; you approve the card.</span><button class="btn" type="submit">Make the card</button></div></form></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- network */
  function pNetwork() {
    const n = K().network || {}, onts = lazyOut('o:' + ST.oq, 'onts', {q: ST.oq}), opt = ST.out.optics;
    return `<div><h1 class="sd-h">Network</h1><p class="lead">${esc(pl((n.olts || []).length, 'OLT'))}, ${esc(pl(n.onts || 0, 'customer ONT'))} (${esc(num(n.onts_down || 0))} down, ${esc(num(n.weak_rx || 0))} weak light), ${esc(pl((n.splitters || []).length, 'splitter'))}, ${esc(pl((n.sites || []).length, 'site'))}.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">OLTs</h2>${(n.olts || []).length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>OLT</th><th>Make</th><th>Site</th><th class="r">PON ports</th><th class="r">Customers</th><th class="r">Down</th><th></th></tr></thead><tbody>${n.olts.map(o => `<tr><td><b>${esc(o.name)}</b><div class="mut" style="font-size:12px">${esc(o.ip || '')}${o.upstream ? ' · ' + esc(o.upstream) : ''}</div></td><td>${esc(cap(o.make || ''))} ${esc((o.tech || '').toUpperCase())}</td><td>${esc(o.site || '')}</td><td class="r">${esc(num(o.pon_ports))}</td><td class="r">${esc(num(o.onts))}</td><td class="r ${o.down ? 'cs-neg' : ''}">${esc(num(o.down || 0))}</td><td class="r">${CAN() ? `<button class="btn soft sm" type="button" data-rm="olt" data-ref="${esc(o.id)}">Remove</button>` : ''}</td></tr>`).join('')}</tbody></table></div>` : empty('No OLT yet.')}
        ${CAN() ? `<form data-form="olt" class="nc-grid" style="margin-top:12px"><label class="ins-lab">Name<input class="in" name="name" required placeholder="OLT-1"></label>
          <label class="ins-lab">Make<select class="in" name="make">${['huawei', 'zte', 'syrotech', 'vsol', 'cdata', 'bdcom', 'other'].map(m => `<option value="${m}">${esc(cap(m))}</option>`).join('')}</select></label>
          <label class="ins-lab">Type<select class="in" name="tech"><option value="gpon">GPON</option><option value="epon">EPON</option></select></label>
          <label class="ins-lab">IP<input class="in" name="ip" placeholder="10.0.0.2"></label><label class="ins-lab">PON ports<input class="in" name="pon_ports" inputmode="numeric" placeholder="8"></label>
          <label class="ins-lab">Site<input class="in" name="site"></label><div class="md-acts wide"><span></span><button class="btn soft" type="submit">Add the OLT</button></div></form>` : ''}</section>
      <section class="card"><div class="cs-head"><h2 class="md-h2" style="margin:0">Customers</h2><div class="r"><form data-form="oq" class="ar-row" style="margin:0"><input class="in" name="q" value="${esc(ST.oq)}" placeholder="Name, account, serial…" aria-label="Find a customer"><button class="btn soft sm" type="submit">Find</button></form></div></div>
        ${!onts ? '<p class="mut" style="margin:0">Working it out…</p>' : onts.error ? err(onts) : (onts.onts || []).length ? `<div class="iv-tw"><table class="tb"><thead><tr><th>Customer</th><th>Where</th><th class="r">Light</th><th>State</th></tr></thead><tbody>${onts.onts.map(o => `<tr><td><b>${esc(o.customer || o.account || o.sn || '—')}</b><div class="mut" style="font-size:12px">${esc(o.phone || '')}${o.plan ? ' · ' + esc(o.plan) : ''}</div></td><td>${esc(o.olt)} · PON ${esc(o.pon)} ONU ${esc(o.onu)}${o.splitter ? ' · ' + esc(o.splitter) : ''}</td><td class="r ${['weak', 'bad'].includes(o.rx_band) ? 'cs-neg' : ''}">${o.rx_last !== null && o.rx_last !== undefined ? esc(o.rx_last) + ' dBm' : '—'}</td><td>${o.state === 'down' ? tag('Down', 'bad') : tag(cap(o.state || 'unknown'), o.state === 'up' ? 'ok' : '')}</td></tr>`).join('')}</tbody></table></div>` : empty('No customers yet.')}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Import your network sheet</h2><p class="mut" style="margin:0 0 10px;font-size:14px">A CSV of customers (customer, mobile, olt, pon, onu, splitter, address…), OLTs, splitters or sites. A password column is ignored and never kept.</p>
        <form data-form="import" class="nc-paste"><label class="btn soft sm" style="align-self:flex-start">Choose a CSV<input type="file" accept=".csv,text/csv,.txt" name="file" hidden></label><textarea class="in nc-mono" name="text" rows="4" placeholder="customer,mobile,olt,pon,onu,splitter,address"></textarea>
          <div class="md-acts"><span></span><button class="btn soft" type="submit">Import</button></div></form></section>` : ''}
      <section class="card"><h2 class="md-h2">Light budget</h2><p class="mut" style="margin:0 0 10px;font-size:14px">The expected light at a customer's ONT for a route - typical figures; a power meter gives the real one.</p>
        <form data-form="optics" class="nc-grid"><label class="ins-lab">Optics<select class="in" name="class">${Object.entries(K().optics || {}).map(([k, v]) => `<option value="${esc(k)}"${k === (st_().optics || 'gpon_b+') ? ' selected' : ''}>${esc(v)}</option>`).join('')}</select></label>
          <label class="ins-lab">Fibre km<input class="in" name="km" inputmode="decimal" placeholder="3.5"></label><label class="ins-lab">Splitters<input class="in" name="splits" placeholder="8, 4"></label>
          <label class="ins-lab">Measured light (dBm, optional)<input class="in" name="rx" inputmode="decimal" placeholder="-21.5"></label><div class="md-acts wide"><span></span><button class="btn soft" type="submit">Work it out</button></div></form>
        ${opt ? (opt.error ? err(opt) : `<div class="nc-opt"><div><b>${esc(opt.loss_db)} dB</b><span>loss</span></div><div><b>${esc(opt.rx_expected)} dBm</b><span>expected light</span></div><div><b class="${opt.margin_db < 3 ? 'cs-neg' : 'cs-pos'}">${esc(opt.margin_db)} dB</b><span>margin</span></div>${opt.measured !== undefined ? `<div><b class="${opt.gap_db >= 3 ? 'cs-neg' : ''}">${esc(opt.measured)} dBm</b><span>measured (${esc(opt.measured_band)})</span></div>` : ''}</div><p class="mut" style="font-size:13px;margin:8px 0 0">${esc(opt.say)}</p>`) : ''}</section>`;
  }

  /* ---------------------------------------------------------------- collectors */
  function pCollectors() {
    const cs = K().collectors || [], made = ST.out.col;
    return `<div><h1 class="sd-h">Collectors</h1><p class="lead">A small program on a computer in your own network reads your OLTs and sends the alarms here. Device passwords stay on that computer - never with Hoola.</p></div>${ro()}
      ${made && made.secret ? `<section class="card nc-secret"><h2 class="md-h2">The collector's secret - shown only now</h2><p style="margin:0 0 8px;font-size:14px">Put it in the collector's config on your computer. Hoola keeps only a sealed copy and cannot show it again.</p><code class="nc-key">${esc(made.secret)}</code>
        <div class="md-acts" style="gap:6px"><span></span><button class="btn soft sm" type="button" data-copysecret="1">Copy</button><button class="btn sm" type="button" data-hidesecret="1">I have saved it</button></div></section>` : ''}
      <section class="card">${cs.length ? cs.map(c => `<div class="cs-row"><span class="cs-dot${c.online ? '' : ' bad'}"></span><span style="flex:1"><b>${esc(c.name)}</b> <span class="mut">${c.online ? 'online' : c.last_seen ? 'offline since ' + esc(c.last_seen) : 'never connected yet'}${c.changes_ok ? ' · may run approved changes' : ' · reads only'}</span></span>
          ${CAN() ? `<button class="btn soft sm" type="button" data-cok="${esc(c.id)}" data-v="${c.changes_ok ? '0' : '1'}">${c.changes_ok ? 'Reads only' : 'Allow approved changes'}</button><button class="btn soft sm" type="button" data-coff="${esc(c.id)}">Remove</button>` : ''}</div>`).join('') : empty('No collector yet - you can also paste alarms by hand.')}</section>
      ${CAN() ? `<section class="card"><h2 class="md-h2">Add a collector</h2><form data-form="col" class="ar-row"><label class="ins-lab" style="flex:1">Name<input class="in" name="name" required placeholder="POP office computer"></label>
        <label class="ar-chk" style="margin-bottom:10px"><input type="checkbox" name="changes_ok"> It may run changes I approve</label><button class="btn" type="submit">Make it</button></form>
        <p class="cs-note">Then download the collector program and run it on that computer: <a href="#" data-script="1">collector script</a>. It only talks out to Hoola, signed with its secret.</p></section>` : ''}`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), teams = s.teams || {}, sla = s.sla || {};
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your ISP, your teams and how fast each kind of fault must be fixed.</p></div>${ro()}
      <section class="card"><h2 class="md-h2">Your ISP</h2><form data-form="ncset" class="nc-grid">
        <label class="ins-lab">ISP name<input class="in" name="isp_name" value="${esc(s.isp_name || '')}"></label>
        <label class="ins-lab">Country (two letters)<input class="in" name="country" maxlength="2" value="${esc(s.country || '')}" placeholder="IN, US, NG, BR…"></label>
        <label class="ins-lab">You are<select class="in" name="model"><option value="isp"${s.model === 'isp' ? ' selected' : ''}>An ISP with its own licence</option><option value="franchise"${s.model === 'franchise' ? ' selected' : ''}>A franchise of a bigger ISP</option><option value="lco"${s.model === 'lco' ? ' selected' : ''}>A local cable operator</option></select></label>
        <label class="ins-lab">Upstream (bandwidth from)<input class="in" name="upstream" value="${esc(s.upstream || '')}"></label>
        <label class="ins-lab">Optics most OLTs use<select class="in" name="optics">${Object.entries(K().optics || {}).map(([k, v]) => `<option value="${esc(k)}"${k === s.optics ? ' selected' : ''}>${esc(v)}</option>`).join('')}</select></label>
        <label class="ins-lab">Morning summary at<input class="in" name="morning_time" value="${esc(s.morning_time || '09:00')}"></label>
        <label class="ins-lab">Alarms this close belong together (minutes)<input class="in" name="window_min" inputmode="numeric" value="${esc(s.window_min || 15)}"></label>
        <label class="ins-lab">SLA hours from your franchise agreement<input class="in" name="bsnl_sla_hours" inputmode="decimal" value="${esc(s.bsnl_sla_hours ?? '')}" placeholder="blank = not set"></label>
        <label class="ins-lab wide">Your rules<textarea class="in" name="rules" rows="2">${esc(s.rules || '')}</textarea></label>
        ${CAN() ? '<div class="md-acts wide"><span></span><button class="btn" type="submit">Save</button></div>' : ''}</form>
        <p class="cs-note">${s.india ? "India: TRAI's outage notes and the Telecom Cyber Security Rules are named on faults." : 'Outside India a large outage says "check this" for your own regulator - Hoola has checked only India\'s rules.'}</p></section>
      <section class="card"><h2 class="md-h2">Teams</h2>${Object.keys(teams).length ? Object.entries(teams).map(([k, ps]) => `<div class="cs-row"><span style="flex:1"><b>${esc((K().teams || {})[k] || k)}</b> <span class="mut">${esc((ps || []).map(p => p.name + (p.phone ? ' (' + p.phone + ')' : '')).join(', ') || '—')}</span></span></div>`).join('') : empty('No team yet.')}
        ${CAN() ? `<form data-form="team" class="ar-row"><label class="ins-lab">Team<select class="in" name="team">${teamOpts('field_fibre')}</select></label><label class="ins-lab" style="flex:1">Name<input class="in" name="name" required></label><label class="ins-lab" style="flex:1">Phone<input class="in" name="phone" placeholder="+country code and number"></label><button class="btn soft" type="submit">Add</button></form>` : ''}</section>
      <section class="card"><h2 class="md-h2">Hours to fix, by kind of fault</h2><form data-form="sla" class="nc-sla">${Object.entries(sla).map(([k, v]) => `<label class="ins-lab">${esc(cap(k.replace(/_/g, ' ')))}<input class="in" name="${esc(k)}" inputmode="decimal" value="${esc(v)}"></label>`).join('')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Starting hours - your own (or your agreement\'s) always win. 0 = no SLA.</span><button class="btn soft" type="submit">Save the hours</button></div>' : ''}</form></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  const dropO = (...pre) => { for (const k of Object.keys(ST.out)) if (pre.some(p => k.startsWith(p))) delete ST.out[k]; };
  /* a page action that asks twice instead of a browser dialog */
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  async function copy(t) { try { await navigator.clipboard.writeText(t); toast('Copied.'); } catch { toast('Could not copy here.', true); } }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    const sc = t.closest('[data-script]'); if (sc) { e.preventDefault();
      try { const r = await fetch('/api/ispnoc/collector-script', {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'}); if (!r.ok) throw new Error(`Could not download (${r.status})`);
        const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = 'hoola_noc_collector.py'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 3000); } catch (err2) { toast(err2.message, true); } return; }
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const fo = t.closest('[data-fault]'); if (fo) { delete ST.out['f:' + fo.dataset.fault]; location.hash = '#/faults/' + fo.dataset.fault; return; }
    if (t.closest('[data-copysecret]')) { copy((ST.out.col || {}).secret || ''); return; }
    if (t.closest('[data-hidesecret]')) { delete ST.out.col; showPage(true); return; }
    const cp = t.closest('[data-copy]'); if (cp) { const m = ST.out['m:' + cp.dataset.copy] || {}; copy((m.text || '') + ((m.phones || []).length ? '\n\n' + m.phones.join(', ') : '')); return; }
    const ce = t.closest('[data-cedit]'); if (ce) { ST.cedit = ST.cedit === ce.dataset.cedit ? '' : ce.dataset.cedit; showPage(true); return; }
    const btn = t.closest('button');
    try {
      const ms = t.closest('[data-msg]'); if (ms) { ms.disabled = true; ST.out['m:' + ms.dataset.msg] = await run('message', {fault: ms.dataset.msg, restored: ms.dataset.restored === '1'}); showPage(true); return; }
      const ts = t.closest('[data-tst]'); if (ts) { ts.disabled = true; const r = await run('ticket_update', {ticket: ts.dataset.tk, status: ts.dataset.tst}); dropO('f:', 'fl:'); await changed(r.say || 'Saved.'); return; }
      const sg = t.closest('[data-sugg]'); if (sg) { sg.disabled = true; const a = JSON.parse(sg.dataset.sugg); const r = await run('change', {action_kind: a.action, olt: a.olt, pon: a.pon, onu: a.onu, reason: a.why, fault: a.fault});
        location.hash = '#/changes'; await changed(r.say || 'A card waits for your approval.'); return; }
      const cd = t.closest('[data-cdec]'); if (cd) {
        const yes = cd.dataset.yes === '1'; if (yes && !sure(cd, 'Tap again to approve')) return;
        cd.disabled = true; const r = await run('decide', {change: cd.dataset.cdec, hash: cd.dataset.hash, yes}); await changed(r.say || (yes ? 'Approved.' : 'Declined.')); return;
      }
      const rm = t.closest('[data-rm]'); if (rm) { if (!sure(rm, 'Tap again to remove')) return; rm.disabled = true; const r = await run('remove', {what: rm.dataset.rm, ref: rm.dataset.ref}); dropO('o:'); await changed(r.say || 'Removed.'); return; }
      const ck = t.closest('[data-cok]'); if (ck) { if (ck.dataset.v === '1' && !sure(ck, 'Tap again: it may run what you approve')) return; ck.disabled = true; await run('collector_update', {id: ck.dataset.cok, changes_ok: ck.dataset.v === '1'}); await changed('Saved.'); return; }
      const co = t.closest('[data-coff]'); if (co) { if (!sure(co, 'Tap again to remove')) return; co.disabled = true; await run('collector_update', {id: co.dataset.coff, active: false}); await changed('Removed. Stop the program on that computer too.'); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.dataset.ff) { ST.ff = el.value; showPage(true); return; }
    if (el.type === 'file' && el.closest('form[data-form=import]')) {
      const f = el.files && el.files[0]; if (!f) return;
      if (f.size > 5 * 1024 * 1024) { toast('That file is over 5 MB.', true); return; }
      el.closest('form').querySelector('textarea').value = await f.text(); el.value = ''; toast(`${f.name} read - check it and tap Import.`);
    }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) btn.disabled = true;
    try {
      if (kind === 'alarms') { if (!g('text')) throw new Error('Paste the alarm lines first.'); toast('Reading the alarms…');
        const r = await run('alarms', {text: S(fd.get('text')), olt: g('olt')}); ST.ing = r; dropO('fl:', 'f:'); form.reset();
        if ((r.new || []).length === 1) location.hash = '#/faults/' + r.new[0].number; else if (ST.tab !== 'faults') location.hash = '#/faults';
        await changed(r.say); }
      else if (kind === 'ticket') { const r = await run('ticket', {fault: form.dataset.id, team: g('team'), assignee: g('assignee'), phone: g('phone'), eta: g('eta'), note: g('note')});
        dropO('f:', 'fl:'); await changed(r.say || 'Ticket made.'); }
      else if (kind === 'resolve') { const how = (e.submitter && e.submitter.dataset.how) || 'resolve'; const r = await run(how, {fault: form.dataset.id, note: g('note')}); dropO('f:', 'fl:'); await changed(r.say || 'Done.'); }
      else if (kind === 'change') { const r = await run('change', {action_kind: g('action_kind'), olt: g('olt'), pon: g('pon'), onu: g('onu'), reason: g('reason')}); await changed(r.say || 'A card waits for your approval above.'); $('#sdDesk').scrollTop = 0; }
      else if (kind === 'cedit') { const ls = n => S(fd.get(n)).split('\n').map(x => x.trim()).filter(Boolean); const r = await run('change_edit', {change: form.dataset.id, commands: ls('commands'), rollback: ls('rollback')}); ST.cedit = ''; await changed(r.say || 'Saved - approve the new card.'); }
      else if (kind === 'cdone') { const ok = !e.submitter || e.submitter.dataset.ok !== '0'; const r = await run('change_done', {change: form.dataset.id, ok, output: S(fd.get('output'))}); await changed(r.say || 'Saved.'); }
      else if (kind === 'olt') { const r = await run('olt', {name: g('name'), make: g('make'), tech: g('tech'), ip: g('ip'), pon_ports: g('pon_ports'), site: g('site')}); form.reset(); await changed(r.say || 'Saved.'); }
      else if (kind === 'oq') { ST.oq = g('q'); showPage(true); }
      else if (kind === 'import') { if (!g('text')) throw new Error('Choose a CSV or paste its lines first.'); const r = await run('import', {text: S(fd.get('text'))}); dropO('o:'); form.reset(); await changed(r.say || 'Imported.'); }
      else if (kind === 'optics') { const sp = g('splits').split(/[,\s]+/).map(x => x.replace(/^1:/, '')).filter(Boolean);
        ST.out.optics = await run('optics', {class: g('class'), km: Number(g('km') || 0), splits: sp, rx: g('rx')}); showPage(true); }
      else if (kind === 'col') { ST.out.col = await run('collector_new', {name: g('name'), changes_ok: fd.get('changes_ok') === 'on'}); form.reset(); await changed('Collector made - save its secret now.'); }
      else if (kind === 'ncset') { await run('settings', {isp_name: g('isp_name'), country: g('country').toUpperCase(), model: g('model'), upstream: g('upstream'), optics: g('optics'),
        morning_time: g('morning_time'), window_min: Number(g('window_min') || 15), bsnl_sla_hours: g('bsnl_sla_hours') === '' ? null : Number(g('bsnl_sla_hours')), rules: g('rules')}); await changed('Saved.'); }
      else if (kind === 'team') { const cur = JSON.parse(JSON.stringify(st_().teams || {})); const tm = g('team'); cur[tm] = [...(cur[tm] || []), {name: g('name'), phone: g('phone')}];
        await run('settings', {teams: {[tm]: cur[tm]}}); form.reset(); await changed('Added.'); }
      else if (kind === 'sla') { const sla = {}; for (const [k, v] of fd.entries()) if (S(v).trim() !== '') sla[k] = Number(v); await run('settings', {sla}); await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) btn.disabled = false; }
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
    const box = $('#ncFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/ncdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'nc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


