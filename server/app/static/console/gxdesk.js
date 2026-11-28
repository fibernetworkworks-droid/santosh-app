/* GRAPHICS DESK - the Graphics Engine Programmer's own section, like the finance desks (owner: "Graphics Engine Programmer same
   as finance desks"). A thin top bar, then the Graphics chat (its own conversation, kind 'graphics') beside the desk's pages: Today,
   Shaders (checked in code, compiled + drawn by THIS browser's WebGL2, golden pictures), Images (reference renders, PSNR / SSIM),
   Validation, Frame times, Settings. The pages call /api/gxdesk/do/<part>; nothing is run on her machines or sent. */
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

  const TABS = [['today', 'Today'], ['shaders', 'Shaders'], ['images', 'Images'], ['validation', 'Validation'], ['frames', 'Frame times'], ['settings', 'Settings']];
  const STARTERS = {
    today: ['What can you check for me?', 'Why is my frame time spiky?', 'How do I find a GPU hang?'],
    shaders: ['Why does this shader look different on mobile?', 'Make this shader faster', 'Explain this shader line by line'],
    images: ['Why is my render darker than the reference?', 'Is the difference just noise?', 'What is SSIM telling me?'],
    validation: ['How do I fix the first error?', 'What barrier do I need here?', 'Which of these matter most?'],
    frames: ['Am I CPU- or GPU-bound?', 'What causes these stutters?', 'Where should I start optimising?'],
    settings: ['Which PSNR limit should I use?', 'Vulkan or D3D12 for my engine?', 'What target FPS for a phone?']};
  const MAXF = 10, MAXB = 30 * 1024 * 1024;

  const ST = {tab: 'today', arg: '', sv: null, img: {}, busy: '', files_ready: [], d: null, chat: '', thread: null, bar: null, rows: [], res: null, sending: false, working: false,
    loading: false, drawn: false, seq: 0, ctx: '', side: 'left', folded: false, files: [], timers: [], out: {}, open: new Set()};
  try { ST.side = localStorage.getItem('hoola.gxdesk.side') === 'right' ? 'right' : 'left'; ST.folded = localStorage.getItem('hoola.gxdesk.folded') === '1'; } catch {}

  const K = () => (ST.d && ST.d.desk) || {};
  const W = () => (ST.d && ST.d.hired) ? {id: 'graphics_eng', name: 'Graphics'} : null;
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
  const run = (part, a) => api('POST', '/api/gxdesk/do/' + part, a || {});

  /* ---------------------------------------------------------------- start */
  async function start() {
    try { ST.d = await api('GET', '/api/gxdesk/desk'); }
    catch (e) { APP.innerHTML = `<div class="empty" style="padding:48px">${esc(e.message)}</div>`; return; }
    if (!ST.d.hired) {
      APP.innerHTML = `<div style="max-width:560px;margin:80px auto;padding:0 20px;display:flex;flex-direction:column;gap:14px">
        <div class="sd-ico" style="width:52px;height:52px">${svg(IC.fo, '')}</div>
        <h1 class="sd-h">Your Graphics Engine Programmer is not hired yet</h1>
        <p class="lead">Hire it here or from AI Employees in Hoola. Then this page opens with its own chat and every screen.</p>
        <div style="display:flex;gap:8px"><button class="btn" type="button" id="gxHire">Hire the Graphics Engine Programmer</button><a class="btn soft" href="/console/?v=hire">AI Employees</a></div></div>`;
      $('#gxHire').onclick = async () => { try { await api('POST', '/api/employees/graphics_eng/hire', {trust: 'seekh'}); location.reload(); } catch (e) { toast(e.message, true); } };
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
          <div style="min-width:0"><div class="sd-name">Graphics</div><div class="sd-site" id="gxSite"></div></div>
          <span id="gxState"></span>
        </div>
        <div class="sd-acts">
          <button class="btn soft sm hide-sm" type="button" id="sdSwap" title="Move the chat to the other side">${svg(IC.swap)}<span>Chat on the ${ST.side === 'left' ? 'right' : 'left'}</span></button>
          <button class="ib" type="button" id="sdRefresh" aria-label="Refresh" title="Refresh">${svg(IC.refresh)}</button>
        </div>
      </header>
      <div class="sd-body${ST.side === 'right' ? ' right' : ''}" id="sdBody">
        <aside class="sd-chat${ST.folded ? ' folded' : ''}" id="sdChat" aria-label="Graphics chat">
          <div class="sd-chathead"><div class="t"><b>Graphics chat</b><span>Paste a shader, a validation log or frame times - or drop a file here</span></div>
            <div style="display:flex;gap:2px;flex-direction:inherit">
              <button class="ib" type="button" id="sdNew" aria-label="New conversation" title="New conversation">${svg(IC.plus)}</button>
              <button class="ib" type="button" id="sdFold" aria-label="${ST.folded ? 'Open the chat' : 'Fold the chat'}" title="${ST.folded ? 'Open the chat' : 'Fold the chat'}">${svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold))}</button></div></div>
          <div class="sd-msgs" id="sdMsgs"><div id="sdThread" class="hck-tight"></div></div>
          <div class="sd-starters" id="sdStarters"></div>
          <div class="sd-ctx" id="sdCtx" hidden></div>
          <div class="md-files" id="gxFiles" hidden></div>
          <div class="sd-bar"><div id="sdBar"></div></div>
          <input type="file" id="gxPick" multiple hidden accept=".txt,.log,.csv,.glsl,.frag,.vert,.wgsl,.hlsl,.json,image/*,.pdf">
        </aside>
        <main class="sd-desk" id="sdDesk"><div class="sd-inner">
          <nav class="sd-tabs" role="tablist" aria-label="Graphics desk" id="sdTabs"></nav>
          <div id="gxPage"></div>
          <p class="cs-foot">${svg(IC.info)}<span>${esc((ST.d && ST.d.foot) || 'Nothing is run, pushed or sent - you do those.')}</span></p></div></main>
      </div>`;
    ST.thread = HoolaChat.mount($('#sdThread'), {scroller: $('#sdMsgs'), jump: true});
    ST.bar = HoolaChat.bar($('#sdBar'), {placeholder: 'Paste a log or shader, or ask…', plus: true, quality: true,
      onSend: t => send(t), onStop: stopTurn, onPlus: () => $('#gxPick').click()});
    $('#gxPick').addEventListener('change', e => { addFiles([...e.target.files]); e.target.value = ''; });
    const chat = $('#sdChat');
    chat.addEventListener('dragover', e => { if ([...(e.dataTransfer?.types || [])].includes('Files')) { e.preventDefault(); chat.classList.add('drop'); } });
    chat.addEventListener('dragleave', e => { if (!chat.contains(e.relatedTarget)) chat.classList.remove('drop'); });
    chat.addEventListener('drop', e => { e.preventDefault(); chat.classList.remove('drop'); addFiles([...(e.dataTransfer?.files || [])]); });
    ST.bar.input.addEventListener('paste', e => { const fs = [...(e.clipboardData?.files || [])]; if (fs.length) { e.preventDefault(); addFiles(fs); } });
    $('#sdSwap').addEventListener('click', () => {
      ST.side = ST.side === 'left' ? 'right' : 'left';
      try { localStorage.setItem('hoola.gxdesk.side', ST.side); } catch {}
      $('#sdBody').classList.toggle('right', ST.side === 'right');
      $('#sdSwap span').textContent = `Chat on the ${ST.side === 'left' ? 'right' : 'left'}`;
      foldIcon();
    });
    $('#sdFold').addEventListener('click', () => {
      ST.folded = !ST.folded;
      try { localStorage.setItem('hoola.gxdesk.folded', ST.folded ? '1' : '0'); } catch {}
      $('#sdChat').classList.toggle('folded', ST.folded); foldIcon();
      if (!ST.folded) ST.bar.focus();
    });
    $('#sdNew').addEventListener('click', async () => {
      try { const r = await api('POST', '/api/gxdesk/chat/new'); ST.chat = r.id; ST.rows = []; ST.drawn = false; ST.res = null;
        ST.thread.clear(); await loadMsgs(true); } catch (e) { toast(e.message, true); }
    });
    $('#sdRefresh').addEventListener('click', () => refreshDesk(true));
    $('#sdTabs').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) location.hash = '#/' + b.dataset.tab; });
    $('#gxPage').addEventListener('click', onPageClick);
    $('#gxPage').addEventListener('submit', onSubmit);
    $('#gxPage').addEventListener('change', onChange);
    $('#gxPage').addEventListener('input', onInput);
    $('#gxPage').addEventListener('toggle', e => { const d = e.target; if (d.dataset && d.dataset.key) { if (d.open) ST.open.add(d.dataset.key); else ST.open.delete(d.dataset.key); } }, true);
    window.addEventListener('hashchange', () => { readTab(); paintTabs(); showPage(); });
    stateLine();
  }
  function foldIcon() {
    const b = $('#sdFold'); if (!b) return;
    b.innerHTML = svg(ST.folded ? IC.chat : (ST.side === 'left' ? IC.unfold : IC.fold));
    const t = ST.folded ? 'Open the chat' : 'Fold the chat'; b.setAttribute('aria-label', t); b.title = t;
  }
  function stateLine() {
    const d = ST.d, el = $('#gxState'); if (!el) return;
    const k = K(), nd = (k.needs || []).filter(x => x.bad).length;
    const [c, n] = d.status === 'paused' ? ['warn', 'Paused'] : nd ? ['warn', pl(nd, 'thing') + ' to look at'] : ['ok', 'Ready'];
    el.innerHTML = `<span class="pill ${c}"><span class="dt"></span>${esc(n)}</span> <span class="pill v hide-sm">${esc(d.trust || 'Learning')}</span>`;
    const s = k.settings || {};
    $('#gxSite').textContent = [({vulkan: 'Vulkan', d3d12: 'Direct3D 12', metal: 'Metal', opengl: 'OpenGL', webgpu: 'WebGPU'})[s.api] || s.api, s.engine, s.target_fps ? s.target_fps + ' FPS' : '', pl((k.items || []).length, 'item')].filter(Boolean).join(' · ');
  }
  function paintTabs() {
    const k = K(), sh = k.shaders || {};
    const n = {shaders: sh.failing || '', validation: k.validation_errors || ''};
    $('#sdTabs').innerHTML = TABS.map(([key, name]) => `<button type="button" role="tab" data-tab="${key}" aria-selected="${key === ST.tab}">${esc(name)}${
      n[key] ? `<span class="n">${esc(n[key])}</span>` : ''}</button>`).join('');
  }
  async function refreshDesk(repaint) {
    try { ST.d = await api('GET', '/api/gxdesk/desk'); } catch { return; }
    stateLine(); paintTabs();
    if (repaint) showPage(true); else if (ST.tab === 'today') showPage(true);
  }

  /* ---------------------------------------------------------------- pages */
  function showPage(keep) {
    const box = $('#gxPage'); if (!box) return;
    glStop();
    const fn = {today: pToday, shaders: pShaders, images: pImages, validation: pValidation, frames: pFrames, settings: pSettings}[ST.tab] || pToday;
    const html = fn();
    const kept = keep ? typed(box) : null;
    box.innerHTML = html;
    if (kept) retype(box, kept);
    starters();
    if (!keep) $('#sdDesk').scrollTop = 0;
    if ($('#gxCanvas')) setTimeout(() => { const r = glBuild(srcNow()); glNote(r); if (r.ok) glDraw(1.0); }, 0);
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
  const pre = (t, cls) => `<pre class="gx-pre ${cls || ''}"><code>${esc(t)}</code></pre>`;
  const items = kind => (K().items || []).filter(x => !kind || x.kind === kind);
  const copyBtn = (txt, label) => `<button class="btn soft sm" type="button" data-copy="${esc(txt)}">${esc(label || 'Copy')}</button>`;
  const SV = {error: ['Error', 'bad'], corruption: ['Corruption', 'bad'], warning: ['Warning', 'warn'], performance: ['Performance', ''], info: ['Note', '']};
  const API_N = {vulkan: 'Vulkan', d3d12: 'Direct3D 12', metal: 'Metal', opengl: 'OpenGL', webgpu: 'WebGPU'};
  const db = v => v === null || v === undefined ? '∞' : num(v) + ' dB';
  function pasteForm(kind, title, ph, extra) {
    if (!CAN()) return '';
    return `<section class="card"><h2 class="md-h2">${esc(title)}</h2><form data-form="add" data-kind="${esc(kind)}" class="gx-form">
      ${extra || ''}<textarea class="in mono gx-ed" name="text" rows="7" spellcheck="false" placeholder="${esc(ph)}"></textarea>
      <div class="gx-row"><label class="btn soft gx-file">Open a file<input type="file" data-fileto="text" accept=".txt,.log,.csv,text/*" hidden></label>
      <input class="in" name="title" maxlength="200" placeholder="A name (optional)" style="flex:1;min-width:140px"><button class="btn" type="submit">Read it</button></div></form></section>`;
  }
  function brief(x) {
    const b = x.brief || {};
    if (x.kind === 'shader') return `${(b.lang || 'glsl').toUpperCase()} · ${pl(b.versions || 1, 'version')} · ${b.errors ? pl(b.errors, 'error') : 'no errors'}${b.golden ? ' · golden: ' + (b.test || 'set') : ''}`;
    if (x.kind === 'compare') return `PSNR ${db(b.psnr)} · SSIM ${num(b.ssim)} · ${b.passed ? 'within your limits' : 'different'}`;
    if (x.kind === 'vklog') return `${pl(b.errors || 0, 'error')}, ${pl(b.warnings || 0, 'warning')} in ${pl(b.kinds || 0, 'kind')}${(b.apis || []).length ? ' · ' + b.apis.join(', ') : ''}`;
    if (x.kind === 'frames') return `${num(b.avg_fps)} FPS · 1% low ${num(b.low1_fps)}${b.stutters ? ' · ' + pl(b.stutters, 'stutter') : ''}${b.bound ? ' · ' + b.bound + '-bound' : ''}`;
    if (x.kind === 'passes') return `${num(b.total_ms)} ms${b.biggest ? ' · biggest ' + b.biggest : ''}${b.over ? ' · over budget' : ''}`;
    return '';
  }
  function itemRows(list) {
    if (!list.length) return empty('Nothing here yet.');
    return `<div class="gx-list">${list.map(x => `<button type="button" class="gx-item" data-open="${esc(x.kind)}/${esc(x.id)}"><span class="cs-dot ${(x.brief || {}).bad ? 'bad' : 'ok'}"></span><span class="t"><b>${esc(x.number)} · ${esc(x.title)}</b><span class="mut">${esc(brief(x))} · ${esc(ago(x.updated_at || x.created_at))}</span></span>${sTag(x.status)}</button>`).join('')}</div>`;
  }
  function head(d, back) {
    return `<div class="gx-head"><button class="ib" type="button" data-go="${esc(back)}" aria-label="Back">${svg(IC.back)}</button>
      <div style="min-width:0;flex:1"><h1 class="sd-h">${esc(d.title)}</h1><p class="lead" style="margin:2px 0 0">${esc(d.number)} · ${esc(ago(d.created_at))}</p></div>${sTag(d.status)}</div>
      ${d.note ? `<p class="cs-note">${esc(d.note)}</p>` : ''}
      ${CAN() ? `<div class="gx-acts">${d.status !== 'fixed' ? `<button class="btn soft sm" type="button" data-mark="fixed">Mark done</button>` : ''}${d.status !== 'ignored' ? `<button class="btn soft sm" type="button" data-mark="ignored">Ignore</button>` : ''}${d.status !== 'open' ? `<button class="btn soft sm" type="button" data-mark="open">Open again</button>` : ''}<span style="flex:1"></span><button class="btn soft sm" type="button" data-del="${esc(d.id)}">Delete</button></div>` : ''}`;
  }
  function one(id, back, draw) {
    const d = lazyOut('i:' + id, 'get', {id});
    if (!d) return loading();
    if (d.error) return `<section class="card">${err(d)}<div class="md-acts"><span></span><button class="btn soft" type="button" data-go="${esc(back)}">Back</button></div></section>`;
    return draw(d);
  }
  const tile = (l, v, s, bad) => `<div class="k${bad ? ' low bad' : ''}"><div class="l">${esc(l)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`;

  /* ---------------------------------------------------------------- today */
  function pToday() {
    const k = K(), c = k.counts || {}, sh = k.shaders || {}, im = k.images || {}, lf = k.last_frames;
    const lead = (k.needs || []).length ? `${pl(k.needs.length, 'thing')} ${k.needs.length > 1 ? 'need' : 'needs'} you.` : 'All in order.';
    const tiles = [
      tile('Shaders', `${esc(num(sh.total || 0))}`, `${num(sh.golden || 0)} with a golden picture${sh.failing ? ' · ' + num(sh.failing) + ' failing' : ''}`, sh.failing),
      tile('Validation errors', esc(num(k.validation_errors || 0)), `${pl(c.vklog || 0, 'log')} read`, k.validation_errors),
      tile('Images within limits', `${esc(num(im.passed || 0))}<small> / ${esc(num(im.total || 0))}</small>`, `PSNR ≥ ${num(st_().psnr_min)} dB, SSIM ≥ ${num(st_().ssim_min)}`),
      tile('Last frame times', lf ? `${esc(num(lf.brief.avg_fps))}<small> FPS</small>` : '—', lf ? `1% low ${num(lf.brief.low1_fps)} · target ${num(st_().target_fps)}` : `target ${num(st_().target_fps)} FPS`, lf && lf.brief.bad)];
    return `<div><h1 class="sd-h">${esc(greet())}</h1><p class="lead">${esc(lead)}</p></div>
      <section class="cs-hero"><div class="top">${tiles.join('')}</div></section>
      ${(k.needs || []).length ? `<section class="card"><h2 class="md-h2">Needs you</h2>${needsRows(k.needs)}</section>` : ''}
      <section class="card"><h2 class="md-h2">Start here</h2><div class="gx-starts">
        <button type="button" class="gx-start" data-go="shaders"><b>Write a shader</b><span>GLSL checked in code, compiled and run in this browser</span></button>
        <button type="button" class="gx-start" data-go="images"><b>Compare a render</b><span>Your picture against a reference: PSNR, SSIM, heat map</span></button>
        <button type="button" class="gx-start" data-go="validation"><b>Read validation output</b><span>Vulkan, Direct3D 12, Metal or OpenGL messages, grouped</span></button>
        <button type="button" class="gx-start" data-go="frames"><b>Read frame times</b><span>PresentMon or plain milliseconds: FPS, lows, stutters</span></button></div></section>
      <section class="card"><h2 class="md-h2">Latest on the desk</h2>${itemRows((k.items || []).slice(0, 8))}</section>`;
  }

  /* ---------------------------------------------------------------- shaders */
  function pShaders() {
    if (ST.arg) return one(ST.arg, 'shaders', pShader);
    return `<div><h1 class="sd-h">Shaders</h1><p class="lead">Every version kept. Checked in code here; compiled and drawn by this browser's WebGL2 - the same driver your users have.</p></div>${ro()}
      ${CAN() ? `<section class="card"><div class="md-acts" style="margin:0"><div><h2 class="md-h2" style="margin:0">A new shader</h2><p class="mut" style="margin:4px 0 0;font-size:14px">Starts from a lit ray-marched sphere, or paste your own fragment shader.</p></div><button class="btn" type="button" data-newshader="1">New shader</button></div></section>` : ''}
      <section class="card"><h2 class="md-h2">Your shaders</h2>${itemRows(items('shader'))}</section>`;
  }
  function pShader(d) {
    const r = d.result || {}, vs = d.versions || [], latest = vs[vs.length - 1] || {src: ''}, c = r.counts || {}, cmp = r.compile, g = d.golden || {}, df = r.diff;
    const view = ST.sv && ST.sv.id === d.id ? ST.sv : (ST.sv = {id: d.id, n: latest.n, src: latest.src});
    const shown = vs.find(v => v.n === view.n) || latest;
    const isOld = shown.n !== latest.n;
    const testTag = r.test === 'passed' ? tag('Matches the golden picture', 'ok') : r.test === 'failed' ? tag('Does not match the golden picture', 'bad') : r.test === 'does not compile' ? tag('Does not compile', 'bad') : r.test === 'not run' ? tag('Test not run on this version', 'warn') : r.test === 'golden set' ? tag('Golden picture set', 'ok') : '';
    return `${head(d, 'shaders')}
      <section class="card gx-shbox"><div class="gx-sh">
        <div class="gx-edwrap"><div class="gx-edbar"><b>${esc((r.lang || 'glsl').toUpperCase())}${r.version ? ' · #version ' + esc(r.version) : ''}</b><span class="mut">version ${esc(shown.n)}${isOld ? ' (older)' : ''} of ${esc(latest.n)}</span></div>
          <textarea class="in mono gx-code" id="gxSrc" spellcheck="false" ${CAN() && !isOld ? '' : 'readonly'}>${esc(view.src !== undefined && !isOld ? view.src : shown.src)}</textarea>
          ${CAN() ? `<div class="gx-row">${isOld ? `<button class="btn soft" type="button" data-sv="${esc(latest.n)}">Back to the latest</button><button class="btn" type="button" data-restore="${esc(shown.n)}">Make this the latest</button>` : `<input class="in" id="gxNote" maxlength="200" placeholder="What changed (optional)" style="flex:1;min-width:140px"><button class="btn soft" type="button" data-shsave="1">Save version</button>`}</div>` : ''}</div>
        <div class="gx-view"><div class="gx-canvas"><canvas id="gxCanvas" width="256" height="256" aria-label="Shader preview"></canvas><span class="gx-glnote" id="gxGlNote" hidden></span></div>
          <div class="gx-row"><button class="btn" type="button" data-shrun="1">Run</button><button class="btn soft" type="button" data-shplay="1" id="gxPlay">Play</button>${CAN() ? `<button class="btn soft" type="button" data-shgold="1">Set golden picture</button>${g.png ? '<button class="btn soft" type="button" data-shtest="1">Test against golden</button>' : ''}` : ''}</div>
          <p class="cs-note" style="margin:0">Uniforms: <code>u_res</code> (vec2), <code>u_time</code> (float, seconds). The golden picture and the test are taken at u_time = 1.0.</p>
          ${testTag ? `<div>${testTag}</div>` : ''}</div></div></section>
      ${cmp ? `<section class="card"><h2 class="md-h2">What your browser's compiler said</h2>${cmp.ok ? '<div class="cs-row"><span class="cs-dot ok"></span><span>Compiled and linked' + (cmp.version ? ' (version ' + esc(cmp.version) + ')' : '') + '.</span></div>' : `<div class="cs-row"><span class="cs-dot bad"></span><span>Did not compile${cmp.version ? ' (version ' + esc(cmp.version) + ')' : ''}.</span></div>`}
        ${(cmp.errors || []).length ? cmp.errors.map(e => `<div class="gx-issue"><span>${tag(SV[e.sev] ? SV[e.sev][0] : e.sev, SV[e.sev] ? SV[e.sev][1] : '')}</span><div><b>${esc(e.text)}</b><span class="mut"> · line ${esc(e.line)}</span></div></div>`).join('') : (cmp.log ? pre(cmp.log) : '')}</section>` : ''}
      ${df ? `<section class="card"><h2 class="md-h2">Against the golden picture</h2><p style="margin:0 0 10px">${esc(df.verdict)}</p><div class="gx-trio">
        <figure><img alt="Golden picture" src="${esc(g.png)}"><figcaption>Golden (version ${esc(g.version)})</figcaption></figure>
        <figure><img alt="This version" src="${esc(df.png)}"><figcaption>This version</figcaption></figure>
        <figure><img alt="Where they differ" src="${esc(df.heatmap)}"><figcaption>Where they differ</figcaption></figure></div></section>` : g.png ? `<section class="card"><h2 class="md-h2">Golden picture</h2><div class="gx-trio"><figure><img alt="Golden picture" src="${esc(g.png)}"><figcaption>Version ${esc(g.version)} · ${esc(ago(g.at))}</figcaption></figure></div></section>` : ''}
      <section class="card"><h2 class="md-h2">The check in code</h2><p class="cs-note" style="margin-top:0">${esc(r.note || '')}</p>
        ${(r.issues || []).length ? r.issues.map(i => `<div class="gx-issue"><span>${tag(SV[i.sev][0], SV[i.sev][1])}</span><div><b>${esc(i.text)}</b><span class="mut"> · line ${esc(i.line)}</span>${i.code ? `<code class="gx-code1">${esc(i.code)}</code>` : ''}</div></div>`).join('') : '<div class="cs-row"><span class="cs-dot ok"></span><span>Nothing found by the check.</span></div>'}</section>
      <section class="card"><h2 class="md-h2">Versions</h2><div class="gx-vers">${vs.slice().reverse().map(v => `<button type="button" data-sv="${esc(v.n)}" aria-current="${v.n === shown.n}"><b>${esc(v.n)}</b><span>${esc(v.note || '—')}</span><span class="mut">${esc(ago(v.at))}</span></button>`).join('')}</div></section>`;
  }

  /* the WebGL2 runner - her browser compiles and draws; nothing here runs on the server */
  const VS = '#version 300 es\nin vec2 p;\nvoid main() { gl_Position = vec4(p, 0.0, 1.0); }\n';
  const GL = {gl: null, prog: null, raf: 0, t0: 0, playing: false};
  function glCtx() {
    const cv = $('#gxCanvas'); if (!cv) return null;
    if (GL.cv !== cv) { GL.cv = cv; GL.gl = cv.getContext('webgl2', {preserveDrawingBuffer: true, antialias: false}); GL.prog = null; }
    return GL.gl;
  }
  function glBuild(src) {
    const gl = glCtx();
    if (!gl) return {ok: false, nogl: true, log: 'This browser has no WebGL2, so the shader cannot be compiled here.'};
    const mk = (type, s) => { const sh = gl.createShader(type); gl.shaderSource(sh, s); gl.compileShader(sh); return sh; };
    const v = mk(gl.VERTEX_SHADER, VS), f = mk(gl.FRAGMENT_SHADER, src);
    const flog = gl.getShaderInfoLog(f) || '';
    if (!gl.getShaderParameter(f, gl.COMPILE_STATUS)) { gl.deleteShader(f); return {ok: false, log: flog || 'The shader did not compile.'}; }
    const p = gl.createProgram(); gl.attachShader(p, v); gl.attachShader(p, f); gl.bindAttribLocation(p, 0, 'p'); gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) return {ok: false, log: gl.getProgramInfoLog(p) || 'The shader did not link.'};
    if (GL.prog) gl.deleteProgram(GL.prog);
    GL.prog = p;
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    return {ok: true, log: flog};
  }
  function glDraw(t) {
    const gl = GL.gl; if (!gl || !GL.prog) return;
    gl.viewport(0, 0, GL.cv.width, GL.cv.height); gl.useProgram(GL.prog);
    const r = gl.getUniformLocation(GL.prog, 'u_res'); if (r) gl.uniform2f(r, GL.cv.width, GL.cv.height);
    const tt = gl.getUniformLocation(GL.prog, 'u_time'); if (tt) gl.uniform1f(tt, t);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  function glStop() { GL.playing = false; cancelAnimationFrame(GL.raf); const b = $('#gxPlay'); if (b) b.textContent = 'Play'; }
  function glPlay() {
    if (GL.playing) { glStop(); return; }
    const res = glBuild(srcNow()); if (!res.ok) { glNote(res); return; }
    GL.playing = true; GL.t0 = performance.now(); const b = $('#gxPlay'); if (b) b.textContent = 'Pause';
    const step = () => { if (!GL.playing || !$('#gxCanvas')) { GL.playing = false; return; } glDraw((performance.now() - GL.t0) / 1000); GL.raf = requestAnimationFrame(step); };
    step();
  }
  function glNote(res) { const n = $('#gxGlNote'); if (!n) return; n.hidden = res.ok; n.textContent = res.nogl ? res.log : 'Did not compile - see below.'; }
  const srcNow = () => { const ta = $('#gxSrc'); return ta ? ta.value : ''; };
  async function shRun(golden, test) {
    const d = ST.out['i:' + ST.arg]; if (!d || d.error) return;
    glStop();
    const vs = d.versions || [], latest = vs[vs.length - 1] || {};
    if ((golden || test) && srcNow() !== latest.src) { toast('Save this as a version first: the golden picture belongs to a saved version.', true); return; }
    const res = glBuild(srcNow());
    glNote(res);
    if (res.nogl) { toast(res.log, true); return; }
    let png = '';
    if (res.ok) { glDraw(1.0); try { png = GL.cv.toDataURL('image/png'); } catch {} }
    if (!CAN()) return;
    try {
      ST.out['i:' + d.id] = await run('run', {id: d.id, ok: res.ok, log: res.log, png: (golden || test) ? png : '', version: latest.n, time: 1.0, golden: !!golden});
      if (golden) toast('Golden picture set from version ' + latest.n + '.');
      else if (test) toast(ST.out['i:' + d.id].result.test === 'passed' ? 'Matches the golden picture.' : 'Does not match the golden picture.', ST.out['i:' + d.id].result.test !== 'passed');
      await refreshDesk(false); showPage(true); setTimeout(() => { if (res.ok) { glBuild(srcNow()); glDraw(1.0); } }, 0);
    } catch (e) { toast(e.message, true); }
  }

  /* ---------------------------------------------------------------- images */
  function pImages() {
    if (ST.arg) return one(ST.arg, 'images', pCompare);
    const sc = (K().health || {}).scenes || [];
    const refs = sc.map(s => { const r = ST.out['ref:' + s.name];
      return `<div class="gx-ref"><div class="gx-refimg">${r && r.png ? `<img alt="${esc(s.title)}" src="${esc(r.png)}">` : r === null ? '<span class="mut">Rendering on the CPU…</span>' : `<button class="btn soft sm" type="button" data-ref="${esc(s.name)}">Render it</button>`}</div>
        <div class="t"><b>${esc(s.title)}</b><span class="mut">${esc(s.width)} x ${esc(s.height)} · ${esc(s.samples)} samples${r && r.seconds ? ' · ' + num(r.seconds) + ' s' : ''}</span><p>${esc(s.about)}</p>
        ${r && r.furnace ? `<p class="gx-ok">Energy ${esc(r.furnace.energy)}: mean ${esc(r.furnace.mean)} (expected ${esc(r.furnace.expected)})</p>` : ''}
        ${r && r.png ? `<a class="btn soft sm" href="${esc(r.png)}" download="hoola-${esc(s.name)}.png">Download PNG</a>` : ''}</div></div>`; }).join('');
    const opt = sc.map(s => `<option value="ref:${esc(s.name)}">Hoola reference: ${esc(s.title)}</option>`).join('');
    return `<div><h1 class="sd-h">Images</h1><p class="lead">Compare your engine's render with a reference. Same size, linear or sRGB the same way on both sides.</p></div>${ro()}
      ${CAN() ? `<section class="card"><h2 class="md-h2">Compare two images</h2><form data-form="compare" class="gx-cmpf">
        <label class="ins-lab">Reference<select class="in" name="a" id="gxA"><option value="">An image from your computer…</option>${opt}</select></label>
        <label class="btn soft gx-file" id="gxAfile">Choose the reference<input type="file" accept="image/*" data-imgto="a" hidden></label>
        <label class="btn soft gx-file">Choose your render<input type="file" accept="image/*" data-imgto="b" hidden></label>
        <label class="ins-lab">Blur first<select class="in" name="blur"><option value="">As in Settings</option><option value="0">None</option><option value="1">1 px</option><option value="2">2 px (noisy renders)</option><option value="4">4 px</option></select></label>
        <div class="gx-picked"><span id="gxApick" class="mut">${esc(ST.img.a ? ST.img.an : 'No reference chosen')}</span><span id="gxBpick" class="mut">${esc(ST.img.b ? ST.img.bn : 'No render chosen')}</span></div>
        <input class="in" name="title" maxlength="200" placeholder="A name (optional)"><button class="btn" type="submit">Compare</button></form>
        <p class="cs-note">Pictures stay on this desk. A path-traced reference is noisy: use a blur of 2 or judge by SSIM.</p></section>` : ''}
      <section class="card"><h2 class="md-h2">Hoola's reference scenes</h2><p class="cs-note" style="margin-top:0">Rendered on Hoola's own CPU path tracer with a fixed seed - the same picture every time. Render the same scene in your engine and compare.</p><div class="gx-refs">${refs}</div></section>
      <section class="card"><h2 class="md-h2">Comparisons</h2>${itemRows(items('compare'))}</section>`;
  }
  function pCompare(d) {
    const r = d.result || {};
    const w = r.worst || [];
    return `${head(d, 'images')}
      <section class="card gx-sum ${r.passed ? 'okv' : 'badv'}"><p class="gx-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('PSNR', esc(db(r.psnr)), 'your limit ' + num(r.psnr_min) + ' dB', !r.identical && r.psnr !== null && r.psnr < r.psnr_min)}${tile('SSIM', esc(num(r.ssim)), 'your limit ' + num(r.ssim_min), r.ssim < r.ssim_min)}
        ${tile('Mean error', esc(num(r.mean_error)), 'max ' + num(r.max_error))}${tile('Pixels over ' + num(r.threshold), esc(num(Math.round((r.over_share || 0) * 1000) / 10)) + '%', r.width + ' x ' + r.height + (r.blur ? ' · blur ' + r.blur : ''), r.over_share > 0.01)}</div></section>
      <section class="card"><div class="gx-trio">${r.a ? `<figure><img alt="${esc(r.a_name)}" src="${esc(r.a)}"><figcaption>${esc(r.a_name)}</figcaption></figure>` : ''}${r.b ? `<figure><img alt="${esc(r.b_name)}" src="${esc(r.b)}"><figcaption>${esc(r.b_name)}</figcaption></figure>` : ''}
        <figure><img alt="Where they differ" src="${esc(r.heatmap)}"><figcaption>Where they differ (dark = same, yellow = most)</figcaption></figure></div>
        ${w.length ? `<h3 class="gx-h3">Where most of the difference is</h3>${w.map(x => `<div class="cs-row"><span class="cs-dot warn"></span><span style="flex:1">x ${esc(x.x)}-${esc(x.x + x.w)}, y ${esc(x.y)}-${esc(x.y + x.h)}</span><b>${esc(num(x.mean))}</b></div>`).join('')}` : ''}</section>`;
  }

  /* ---------------------------------------------------------------- validation */
  function pValidation() {
    if (ST.arg) return one(ST.arg, 'validation', pLog);
    return `<div><h1 class="sd-h">Validation</h1><p class="lead">The output of the Vulkan validation layers, the Direct3D 12 debug layer, Metal API validation or OpenGL debug messages - grouped by message, explained.</p></div>${ro()}
      ${pasteForm('vklog', 'Read validation output', 'Validation Error: [ VUID-... ] ...\nD3D12 ERROR: ... [ EXECUTION ERROR #538: ... ]\n-[MTL... ]: failed assertion `...`')}
      <section class="card"><h2 class="md-h2">Logs read</h2>${itemRows(items('vklog'))}</section>`;
  }
  function pLog(d) {
    const r = d.result || {}, gs = r.groups || [];
    const cats = (r.by_category || []);
    return `${head(d, 'validation')}
      <section class="card gx-sum ${r.errors ? 'badv' : 'okv'}"><p class="gx-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('Errors', esc(num(r.errors || 0)), (r.apis || []).join(', '), r.errors)}${tile('Warnings', esc(num(r.warnings || 0)), 'incl. performance')}${tile('Kinds', esc(num(r.kinds || 0)), pl(r.messages || 0, 'message') + ' in all')}</div></section>
      ${cats.length ? `<section class="card"><h2 class="md-h2">By kind of problem</h2>${bars(cats.map(([n, v]) => [n, v, 'gx-b']), null, 'Messages by kind')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Messages</h2>${gs.length ? `<div class="gx-msgs">${gs.map((g, i) => `<details class="gx-msg" data-key="m${i}"${ST.open.has('m' + i) ? ' open' : ''}><summary>${tag(SV[g.sev] ? SV[g.sev][0] : g.sev, SV[g.sev] ? SV[g.sev][1] : '')}<code>${esc(g.id)}</code><span class="mut">${esc(g.api)}${(g.calls || []).length ? ' · ' + esc(g.calls.slice(0, 2).join(', ')) : ''}</span><b class="gx-n">x${esc(g.count)}</b></summary>
          <div class="gx-mbody"><p><span class="gx-cat">${esc(g.category_name)}</span> ${esc(g.fix)}</p>${g.rule ? `<p class="gx-rule"><b>The rule:</b> ${esc(g.rule)}</p>` : ''}${pre(g.text)}${g.link ? `<a class="btn soft sm" href="${esc(g.link)}" target="_blank" rel="noopener noreferrer">${g.api === 'Vulkan' ? 'Open in the Vulkan spec' : 'Open the documentation'}</a>` : ''}</div></details>`).join('')}</div>` : empty('No messages found.')}</section>`;
  }

  /* ---------------------------------------------------------------- frames */
  function pFrames() {
    if (ST.arg) return one(ST.arg, 'frames', x => x.kind === 'passes' ? pPasses(x) : pFrame(x));
    return `<div><h1 class="sd-h">Frame times</h1><p class="lead">A PresentMon CSV, a CSV with a frame-time column, or frame times in milliseconds - against your target of ${esc(num(st_().target_fps))} FPS.</p></div>${ro()}
      ${pasteForm('frames', 'Read frame times', 'Application,ProcessID,...,MsBetweenPresents,...\nor: 16.6 16.8 17.1 33.4 16.7 ...')}
      ${pasteForm('passes', 'Read GPU pass timings', 'Shadows, 2.1\nGBuffer, 4.0\nLighting, 6.5\nPost, 1.2')}
      <section class="card"><h2 class="md-h2">Read so far</h2>${itemRows([...items('frames'), ...items('passes')].sort((a, b) => S(b.updated_at).localeCompare(S(a.updated_at))))}</section>`;
  }
  function frameChart(r) {
    const s = r.series || []; if (s.length < 2) return '';
    const W = 760, H = 220, L = 52, R = 12, T = 12, B = 26;
    const hi = Math.max(r.budget_ms * 1.5, ...s), x = i => L + i * (W - L - R) / (s.length - 1), y = v => T + (hi - v) / hi * (H - T - B);
    const d = s.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('');
    const tk = [0, r.budget_ms, hi].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/><text class="tx" x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${esc(num(Math.round(v * 10) / 10))}</text>`).join('');
    return `<div class="cs-chart gx-fchart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Frame time over the run">${tk}<line class="gx-bud" x1="${L}" x2="${W - R}" y1="${y(r.budget_ms).toFixed(1)}" y2="${y(r.budget_ms).toFixed(1)}"/><path class="ln" d="${d}"/>
      <text class="tx" x="${W - R}" y="${(y(r.budget_ms) - 6).toFixed(1)}" text-anchor="end">budget ${esc(num(r.budget_ms))} ms</text><text class="tx" x="${L}" y="${H - 6}">start</text><text class="tx" x="${W - R}" y="${H - 6}" text-anchor="end">${esc(num(r.seconds))} s</text></svg></div>`;
  }
  function pFrame(d) {
    const r = d.result || {}, hist = r.hist || [];
    const labels = hist.map((_, i) => i === hist.length - 1 ? `≥ ${num(Math.round(r.budget_ms * 11 / 4 * 10) / 10)} ms` : `${num(Math.round(r.budget_ms * i / 4 * 10) / 10)}-${num(Math.round(r.budget_ms * (i + 1) / 4 * 10) / 10)} ms`);
    return `${head(d, 'frames')}
      <section class="card gx-sum ${(r.over_budget > 0.05 || r.stutters) ? 'badv' : 'okv'}"><p class="gx-big">${esc(r.verdict)}</p></section>
      <section class="cs-hero"><div class="top">${tile('Average', esc(num(r.avg_fps)) + '<small> FPS</small>', 'median ' + num(r.median_ms) + ' ms', r.avg_fps < r.target_fps)}${tile('1% low', esc(num(r.low1_fps)) + '<small> FPS</small>', '0.1% low ' + num(r.low01_fps) + ' FPS', r.low1_fps < r.target_fps * 0.5)}
        ${tile('p95 / p99', esc(num(r.p95_ms)) + '<small> / ' + esc(num(r.p99_ms)) + ' ms</small>', 'worst ' + num(r.max_ms) + ' ms')}${tile('Over budget', esc(num(Math.round((r.over_budget || 0) * 1000) / 10)) + '%', pl(r.stutters || 0, 'stutter') + ' · ' + pl(r.frames || 0, 'frame'), r.over_budget > 0.05)}</div></section>
      ${r.bound ? `<section class="card"><h2 class="md-h2">CPU or GPU</h2><p style="margin:0">Looks <b>${esc(r.bound)}</b>-bound: the CPU is busy ${esc(num(r.cpu_ms))} ms and the GPU ${esc(num(r.gpu_ms))} ms in a median frame.</p>${bars([['CPU', r.cpu_ms, 'gx-b'], ['GPU', r.gpu_ms, 'gx-b2']], v => num(v) + ' ms', 'CPU and GPU busy time')}</section>` : ''}
      <section class="card"><h2 class="md-h2">Over the run</h2>${frameChart(r)}<p class="cs-note">Each point is the slowest frame of its slice, so a short stutter stays visible.</p></section>
      <section class="card"><h2 class="md-h2">How the frames spread</h2>${bars(hist.map((v, i) => [labels[i], v, i >= 4 ? 'gx-b2' : 'gx-b']), num, 'Frame-time histogram')}</section>
      ${(r.stutter_list || []).length ? `<section class="card"><h2 class="md-h2">Stutters</h2><table class="tb"><thead><tr><th>Frame</th><th class="r">Took</th><th class="r">Around it</th></tr></thead><tbody>${r.stutter_list.map(s => `<tr><td>${esc(num(s.i))}</td><td class="r">${esc(num(s.ms))} ms</td><td class="r">${esc(num(s.typical))} ms</td></tr>`).join('')}</tbody></table></section>` : ''}`;
  }
  function pPasses(d) {
    const r = d.result || {};
    return `${head(d, 'frames')}
      <section class="card gx-sum ${r.over ? 'badv' : 'okv'}"><p class="gx-big">${esc(r.verdict)}</p></section>
      <section class="card"><h2 class="md-h2">Each pass</h2>${bars((r.passes || []).map(p => [p.name, p.ms, p.of_budget > 0.4 ? 'gx-b2' : 'gx-b', Math.round(p.share * 100) + '% of the frame']), v => num(v) + ' ms', 'GPU passes')}
        <div class="gx-budget"><i style="width:${Math.min(100, r.total_ms / r.budget_ms * 100).toFixed(1)}%" class="${r.over ? 'bad' : ''}"></i></div><p class="cs-note">${esc(num(r.total_ms))} ms of the ${esc(num(r.budget_ms))} ms budget.</p></section>`;
  }

  /* ---------------------------------------------------------------- settings */
  function pSettings() {
    const s = st_(), h = K().health || {};
    const fld = (n, l, ph, extra) => `<label class="ins-lab">${esc(l)}<input class="in" name="${n}" value="${esc(s[n] ?? '')}" placeholder="${esc(ph)}" ${extra || ''}></label>`;
    return `<div><h1 class="sd-h">Settings</h1><p class="lead">Your renderer, your frame budget and how close two pictures must be to count as the same.</p></div>${ro()}
      <section class="card"><form data-form="settings" class="gx-grid">
        <label class="ins-lab">Graphics API<select class="in" name="api">${(h.apis || []).map(a => `<option value="${esc(a)}"${a === s.api ? ' selected' : ''}>${esc(API_N[a] || a)}</option>`).join('')}</select></label>
        ${fld('engine', 'Your engine or renderer', 'My engine')}${fld('gpu', 'The GPU you test on', 'e.g. RTX 4070, Apple M3, Adreno 750')}
        ${fld('target_fps', 'Target FPS', '60', 'type="number" step="any" min="10" max="1000"')}${fld('psnr_min', 'PSNR at least (dB)', '35', 'type="number" step="any" min="10" max="80"')}
        ${fld('ssim_min', 'SSIM at least', '0.98', 'type="number" step="any" min="0.5" max="1"')}${fld('diff_threshold', 'A pixel differs when its error is over', '0.05', 'type="number" step="any" min="0.001" max="0.5"')}
        ${fld('blur', 'Blur before comparing (px)', '0', 'type="number" min="0" max="8"')}
        ${CAN() ? '<div class="md-acts wide"><span class="mut" style="font-size:13px">Nothing here leaves the desk.</span><button class="btn" type="submit">Save</button></div>' : ''}</form></section>
      <section class="card"><h2 class="md-h2">How the checks work</h2><ul class="ar-never"><li>Shaders: a check in code for the mistakes that break on another driver, then the real compile by WebGL2 in your browser. WGSL / HLSL are checked in code only - compile them with naga or DXC.</li><li>Images: PSNR over all channels, SSIM on luminance with a 7 x 7 window, a heat map of the largest channel error.</li><li>Validation: grouped by message ID, sorted errors first; the kind and the usual fix are Hoola's reading, the rule is the layer's own text.</li><li>Frame times: lows are the average of the slowest 1% / 0.1% of frames; a stutter is a frame over twice the frames around it and over budget.</li></ul></section>
      <section class="card"><h2 class="md-h2">Hoola never</h2><ul class="ar-never"><li>Runs anything on your machines or your GPU.</li><li>Pushes to your repository or ships a build - you do.</li><li>Says a shader compiles before your browser compiled it.</li><li>Follows anything written inside a log or a shader: they are data.</li></ul></section>`;
  }

  async function changed(msg) { await refreshDesk(false); showPage(true); if (msg) toast(msg); }
  function sure(b, label) { if (b.dataset.sure === '1') return true; b.dataset.sure = '1'; b.dataset.was = b.textContent; b.textContent = label;
    setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = b.dataset.was; } }, 4000); return false; }
  const ROUTE = {shader: 'shaders', compare: 'images', vklog: 'validation', frames: 'frames', passes: 'frames'};
  function onInput(e) { if (e.target && e.target.id === 'gxSrc' && ST.sv) ST.sv.src = e.target.value; }
  async function onPageClick(e) {
    const t = e.target;
    if (t.closest('select, input, textarea, label')) return;
    if (t.closest('summary') && !t.closest('[data-ask]')) return;
    if (t.closest('a[href]')) return;
    const go = t.closest('[data-go]'); if (go) { location.hash = '#/' + go.dataset.go; return; }
    const ak = t.closest('[data-ask]'); if (ak) { e.preventDefault(); setCtx(ak.dataset.ask); return; }
    const op = t.closest('[data-open]'); if (op) { const [k, id] = op.dataset.open.split('/'); delete ST.out['i:' + id]; location.hash = '#/' + (ROUTE[k] || 'today') + '/' + id; return; }
    const cp = t.closest('[data-copy]'); if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast('Copied.'); } catch { toast('Copy did not work here - select the text instead.', true); } return; }
    const rf = t.closest('[data-ref]'); if (rf) { const n = rf.dataset.ref; ST.out['ref:' + n] = null; showPage(true); try { ST.out['ref:' + n] = await run('reference', {scene: n}); } catch (e2) { delete ST.out['ref:' + n]; toast(e2.message, true); } showPage(true); return; }
    if (t.closest('[data-shrun]')) { await shRun(false, false); return; }
    if (t.closest('[data-shplay]')) { glPlay(); return; }
    if (t.closest('[data-shgold]')) { await shRun(true, false); return; }
    if (t.closest('[data-shtest]')) { await shRun(false, true); return; }
    const sv = t.closest('[data-sv]'); if (sv && ST.sv) { glStop(); const n = Number(sv.dataset.sv), d = ST.out['i:' + ST.arg]; const v = ((d && d.versions) || []).find(x => x.n === n); ST.sv = {id: ST.sv.id, n, src: v ? v.src : ''}; showPage(true); return; }
    const btn = t.closest('button');
    const id = ST.arg;
    try {
      if (t.closest('[data-newshader]')) { btn.disabled = true; const d = await run('add', {kind: 'shader', title: 'Shader'}); ST.out['i:' + d.id] = d; ST.sv = null; await refreshDesk(false); location.hash = '#/shaders/' + d.id; return; }
      const rs = t.closest('[data-restore]'); if (rs) { const d = ST.out['i:' + id], v = (d.versions || []).find(x => x.n === Number(rs.dataset.restore)); btn.disabled = true;
        ST.out['i:' + id] = await run('save_shader', {id, src: v.src, note: 'Back to version ' + v.n}); ST.sv = null; await changed('Version ' + v.n + ' is the latest again.'); return; }
      if (t.closest('[data-shsave]')) { btn.disabled = true; const before = (ST.out['i:' + id].versions || []).length;
        ST.out['i:' + id] = await run('save_shader', {id, src: srcNow(), note: S(($('#gxNote') || {}).value)}); ST.sv = null;
        await changed((ST.out['i:' + id].versions || []).length > before ? 'Saved as version ' + ST.out['i:' + id].versions.slice(-1)[0].n + '.' : 'No change since the last version.'); return; }
      const mk = t.closest('[data-mark]'); if (mk) { mk.disabled = true; ST.out['i:' + id] = await run('mark', {id, status: mk.dataset.mark}); await changed({fixed: 'Marked done.', ignored: 'Ignored.', open: 'Open again.'}[mk.dataset.mark]); return; }
      const dl = t.closest('[data-del]'); if (dl) { if (!sure(dl, 'Tap again to delete')) return; dl.disabled = true; const r = await run('delete', {id}); delete ST.out['i:' + id]; location.hash = '#/' + ST.tab; await changed(r.say); return; }
    } catch (err2) { toast(err2.message, true); if (btn) btn.disabled = false; }
  }
  async function onChange(e) {
    const el = e.target;
    if (el.tagName === 'SELECT') el.dataset.touched = '1';
    if (el.id === 'gxA') { const f = $('#gxAfile'); if (f) f.hidden = !!el.value;
      const p = $('#gxApick'); if (p) { p.textContent = el.value ? el.options[el.selectedIndex].textContent : (ST.img.a ? ST.img.an : 'No reference chosen'); p.classList.toggle('mut', !el.value && !ST.img.a); } }
    if (el.dataset.fileto && el.files && el.files[0]) {
      const f = el.files[0];
      if (f.size > 2000000) { toast('That file is larger than 2 MB - keep the part around the problem.', true); el.value = ''; return; }
      const txt = await f.text(), form = el.closest('form'), ta = form && form.querySelector(`[name=${el.dataset.fileto}]`);
      if (ta) { ta.value = txt; const ti = form.querySelector('[name=title]'); if (ti && !ti.value) ti.value = f.name; }
      el.value = '';
    }
    if (el.dataset.imgto && el.files && el.files[0]) {
      const f = el.files[0], w = el.dataset.imgto;
      if (f.size > 12 * 1024 * 1024) { toast('An image may be at most 12 MB.', true); el.value = ''; return; }
      const url = await new Promise((ok, no) => { const fr = new FileReader(); fr.onload = () => ok(fr.result); fr.onerror = () => no(new Error('Could not read the file.')); fr.readAsDataURL(f); });
      ST.img[w] = url; ST.img[w + 'n'] = f.name; el.value = '';
      const p = $(w === 'a' ? '#gxApick' : '#gxBpick'); if (p) { p.textContent = f.name; p.classList.remove('mut'); }
      if (w === 'a') { const sel = $('#gxA'); if (sel) sel.value = ''; }
    }
  }
  async function onSubmit(e) {
    const form = e.target.closest('form[data-form]'); if (!form) return;
    e.preventDefault();
    const kind = form.dataset.form, fd = new FormData(form), g = n => S(fd.get(n)).trim();
    const btn = e.submitter || form.querySelector('button[type=submit]');
    if (btn) { btn.disabled = true; btn.dataset.was = btn.textContent; }
    try {
      if (kind === 'add') { const k = form.dataset.kind; if (btn) btn.textContent = 'Reading…';
        const d = await run('add', {kind: k, text: S(fd.get('text')), title: g('title')});
        ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/' + ROUTE[k] + '/' + d.id; toast(`${d.number} read.`); }
      else if (kind === 'compare') {
        const a = g('a') || ST.img.a, b = ST.img.b;
        if (!a) throw new Error('Choose the reference: a Hoola scene or an image.');
        if (!b) throw new Error('Choose your render.');
        if (btn) btn.textContent = 'Comparing…';
        const d = await run('add', {kind: 'compare', a, b, blur: g('blur'), title: g('title'), a_name: g('a') ? '' : ST.img.an, b_name: ST.img.bn});
        ST.img = {}; ST.out['i:' + d.id] = d; await refreshDesk(false); location.hash = '#/images/' + d.id; toast(`${d.number}: ${d.result.passed ? 'within your limits' : 'different'}.`); }
      else if (kind === 'settings') { const a = {}; ['api', 'engine', 'gpu', 'target_fps', 'psnr_min', 'ssim_min', 'diff_threshold', 'blur'].forEach(n => { a[n] = g(n); });
        await run('settings', a); await changed('Saved.'); }
    } catch (err2) { toast(err2.message, true); }
    finally { if (btn && btn.isConnected) { btn.disabled = false; if (btn.dataset.was) btn.textContent = btn.dataset.was; } }
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
    const box = $('#gxFiles'); if (!box) return;
    box.hidden = !ST.files.length;
    box.innerHTML = ST.files.map(f => `<span class="md-file ${f.state === 'up' ? 'up' : f.state === 'bad' ? 'bad' : ''}" title="${esc(f.err || f.name)}"><span>${esc(f.state === 'up' ? 'Uploading ' + f.name : f.name)}</span><button type="button" aria-label="Remove ${esc(f.name)}" data-k="${esc(f.key)}">×</button></span>`).join('');
    box.onclick = e => { const b = e.target.closest('[data-k]'); if (!b) return; ST.files = ST.files.filter(f => f.key !== b.dataset.k); paintFiles(); };
  }

  /* ---------------------------------------------------------------- the chat */
  async function openChat() {
    try { const r = await api('GET', '/api/gxdesk/chat'); ST.chat = r.id; }
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
    try { await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files, client_id: 'gx' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)}); }
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


