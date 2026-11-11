/* v0.693 HOOLA APP STUDIO - the native-app builder as its OWN full-screen app (the owner-approved prototype, "GO BUILD").

   The Web Studio's twin, on the SAME app engine the chat uses (appmaker): nothing here designs or builds by itself, every
   button calls an existing /api/apps route.
   Home (own sidebar): one line + a Build | Plan switch.
     Build = the app is made (POST /api/apps) and, when the plan has no open question, her Haan is sent (POST /plan) so
             the THREE LOOKS start at once.
     Plan  = the app stops at its plan card: she reads the screens, data, roles and phone features first and says Haan.
   Workspace (#/app/<id>/<view>): her own Hoola thread for THIS app on the left (a conversation per app, never the home
   chat; the live work card with the server's own timed steps above the composer), and the app on the right:
   Plan · Looks · Screens · Prototype | Android · iPhone · Store | Data · Business · Health · Settings (+ History).

   Rules kept from the server, drawn: every server value goes through esc(); colours only as plain #hex; screen images
   are fetched with her token into blob: links; "Design pakka" sends the server's hash; Play production, App Store
   review, rollout steps and deletes ask first and send her_tap only from her own tap; keys are never asked for in chat. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  const N = v => Number(v) || 0;
  const HEX = v => /^#[0-9a-f]{3,8}$/i.test(S(v)) ? S(v) : '';
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const store = {get(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }, del(k) { try { localStorage.removeItem(k); } catch {} }};
  const TOKEN = store.get('hoola.console.token');
  const APP = $('#ws');
  if (!TOKEN) { location.replace('/console/'); return; }

  class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
  async function api(method, path, body, {raw = false} = {}) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (method === 'POST' && /\/conversations\/[^/]+\/messages$/.test(path) && body && typeof body.text === 'string') {
      const hints = L(body.hints).map(h => '\n\n[Web console ' + h + ']').join('');
      body = {...body, text: body.text + hints + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
      delete body.hints;
    }
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new ApiError(401, 'Please sign in again.'); }
    if (raw) { if (!r.ok) throw new ApiError(r.status, await r.text()); return r; }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) {
      const bad = data && Array.isArray(data.detail) && data.detail[0];
      const msg = (data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) ||
        (bad ? S(bad.msg) : '') || `The server refused the request (${r.status})`;
      const e = new ApiError(r.status, msg); e.data = data; throw e;
    }
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'ws-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }

  /* ---------- icons ---------- */
  const ICON = {
    home: '<path d="M4 11l8-7 8 7v9H4z"/>', grid: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18"/>',
    back: '<path d="M15 5l-7 7 7 7"/>', plus: '<path d="M12 5v14M5 12h14"/>', up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    chat: '<path d="M4 5h16v11H8l-4 4z"/>', pic: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 15l5-5 4 4 3-3 6 6"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>', tab: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M11 17h2"/>',
    hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>', check: '<path d="M5 12l5 5 9-10"/>', chev: '<path d="M6 9l6 6 6-6"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>', pause: '<path d="M9 5v14M15 5v14"/>', ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>', edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
    trash: '<path d="M4 7h16M10 7V4h4v3M6 7l1 13h10l1-13"/>', code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>', dl: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    reload: '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>', globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
    idea: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z"/>', sel: '<path d="M4 4l7 17 2-7 7-2z"/>',
    tpl: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    card: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h3"/>', doc: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
    book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>', box: '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4M12 11v10"/>',
    tag: '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.3"/>', truck: '<path d="M3 6h11v10H3zM14 9h4l3 3v4h-7"/><circle cx="7" cy="18" r="1.8"/><circle cx="17" cy="18" r="1.8"/>',
    rule: '<path d="M4 6h16M4 12h10M4 18h7"/><path d="M16 16l2 2 4-4"/>', chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    plan: '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    looks: '<circle cx="12" cy="12" r="9"/><path d="M12 3v18M3 12h9"/>', screens: '<rect x="3" y="4" width="8" height="16" rx="2"/><rect x="13" y="4" width="8" height="16" rx="2"/>',
    play: '<path d="M7 4l12 8-12 8z"/>', android: '<rect x="5" y="9" width="14" height="10" rx="2"/><path d="M8 9a4 4 0 0 1 8 0M8 5l1.5 2M16 5l-1.5 2"/>',
    apple: '<path d="M16 3c-1.5.2-3 1.4-3 3 1.6.1 3-1.2 3-3zM12 7c-2-1-6-.5-6 4.5 0 4 2.5 9 4.5 8 .8-.4 1.2-.4 2 0 2 1 4.5-4 4.5-6.5-2-1-2.5-4 0-5.5-1.5-2-3.5-1.5-5-.5z"/>',
    store: '<path d="M4 9l1-5h14l1 5M4 9v11h16V9M4 9h16M9 20v-6h6v6"/>', data: '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    biz: '<path d="M3 8h18v12H3zM8 8V5h8v3M3 13h18"/>', heart: '<path d="M3 12h4l2-5 4 10 2-5h6"/>', gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>'};
  const LANG = {hinglish: 'Hinglish', en: 'English', hi: 'Hindi', mr: 'Marathi', gu: 'Gujarati', ta: 'Tamil', te: 'Telugu', kn: 'Kannada', ml: 'Malayalam', bn: 'Bengali', pa: 'Punjabi', or: 'Odia', ur: 'Urdu'};
  const ico = (k, n = 18) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const tick = `<span class="tick" aria-hidden="true">${ico('check', 11)}</span>`;
  const pill = (t, c) => `<span class="pill ${c || ''}">${esc(t)}</span>`;
  const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');

  /* ---------- an app's state in plain words ---------- */
  const BUILDING = ['writing', 'building', 'fixing', 'uploading'];
  const anSt = v => S(M(M(v.builds).android).status), iosSt = v => S(M(M(v.builds).ios).status);
  const DESIGNING = v => ['designing', 'checking'].includes(S(v.status)) || (S(v.status) === 'looks' && Array.isArray(v.looks) && !v.looks.length);
  const WORKING = v => DESIGNING(v) || BUILDING.includes(anSt(v)) || BUILDING.includes(iosSt(v));
  const STATUS = {draft: ['Starting', ''], planned: ['Plan ready', 'v'], looks: ['Pick a look', 'warn'], designing: ['Designing', 'v'],
    checking: ['Checking', 'v'], ready: ['Design ready', 'ok'], approved: ['Design approved', 'ok'], failed: ['Needs attention', 'bad'], stopped: ['Paused', '']};
  function statusOf(v) {
    if (BUILDING.includes(anSt(v))) return ['Building Android', 'v'];
    if (BUILDING.includes(iosSt(v))) return ['Building iPhone', 'v'];
    if (S(v.status) === 'looks' && !L(v.looks).length && v.looks !== undefined) return ['Making 3 looks', 'v'];
    if (S(v.status) === 'designing' && N(M(v.board).pct)) return [`Designing · ${Math.round(N(M(v.board).pct))}%`, 'v'];
    if (S(v.status) === 'approved' && anSt(v) === 'ready') return ['Android app ready', 'ok'];
    const [t, c] = STATUS[S(v.status)] || [S(v.status) || 'Draft', ''];
    return [t + (N(v.version) && ['ready', 'approved'].includes(S(v.status)) ? ` · v${v.version}` : ''), c];
  }
  const statusPill = v => { const [t, c] = statusOf(v); return pill(t, c); };
  const dotCls = v => ({ok: 'ok', warn: 'warn', v: 'v', bad: 'bad'}[statusOf(v)[1]] || '');
  const name = v => S(v.name) || S(v.field_label) || S(v.number) || 'App';
  const isoS = x => { const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(S(x)) ? S(x) : S(x) + 'Z'); return isNaN(t) ? 0 : t / 1000; };
  const ago = x => { const t = isoS(x); if (!t) return ''; const d = Math.max(0, Date.now() / 1000 - t);
    return d < 60 ? 'just now' : d < 3600 ? `${Math.floor(d / 60)} min ago` : d < 86400 ? `${Math.floor(d / 3600)} h ago` : `${Math.floor(d / 86400)} d ago`; };
  const clockOf = t => t ? new Date(t * 1000).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}) : '';
  const tint = id => { let h = 0; for (const c of S(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return ['#6D4AFF', '#1F8A5B', '#C2407A', '#2E5BDB', '#E2562B', '#B7791F'][h % 6]; };
  const mb = n => N(n) ? (N(n) / 1048576).toFixed(1) + ' MB' : '';
  const inr = n => '₹' + Math.round(N(n)).toLocaleString('en-IN');

  /* ---------- screen images: fetched with her token, shown as blob: links ---------- */
  const IMG = new Map();
  const shot = (id, file) => `/api/apps/${enc(id)}/shots/${S(file).split('/').map(enc).join('/')}`;
  async function paintImgs(root = APP) {
    for (const img of root.querySelectorAll('img[data-src]')) {
      const src = img.dataset.src; img.removeAttribute('data-src');
      if (IMG.has(src)) { const u = IMG.get(src); if (u) img.src = u; else img.closest('[data-hide-missing]')?.classList.add('missing'); continue; }
      try {
        const r = await api('GET', src, undefined, {raw: true});
        const u = URL.createObjectURL(await r.blob()); IMG.set(src, u); img.src = u;
      } catch {
        IMG.set(src, ''); const box = img.parentElement;
        if (box && box.classList.contains('as-ph')) box.innerHTML = `<span class="wait">${esc(img.alt || 'Not drawn yet')}</span>`;
        else img.remove();
      }
    }
  }
  const imgTag = (src, alt) => `<img data-src="${esc(src)}" alt="${esc(alt)}" loading="lazy">`;
  function qrSvg(text) {
    try { const q = window.qrcode(0, 'M'); q.addData(S(text)); q.make(); return q.createSvgTag({cellSize: 4, margin: 2, scalable: true}); }
    catch { return '<span class="mut sm">QR not available</span>'; }
  }

  /* ---------- state ---------- */
  const MODE_KEY = 'hoola.as.mode', STAR_KEY = 'hoola.as.star';
  const convKey = id => 'hoola.as.conv.' + id;
  const VIEW_IC = {plan: 'plan', looks: 'looks', screens: 'screens', prototype: 'play', android: 'android', iphone: 'apple', store: 'store', data: 'data', business: 'biz', health: 'heart', settings: 'gear'};
  const VIEWS = [['plan', 'Plan'], ['looks', 'Looks'], ['screens', 'Screens'], ['prototype', 'Prototype'], '|',
    ['android', 'Android'], ['iphone', 'iPhone'], ['store', 'Store'], '|', ['data', 'Data'], ['business', 'Business'],
    ['health', 'Health'], ['settings', 'Settings']];
  const VIEW_KEYS = VIEWS.filter(x => x !== '|').map(x => x[0]).concat(['history']);
  let APPS = [], LIB = {}, CUR = null, VIEW = 'plan', POLL = null, SIG = '', PREFILL = '', PLAT = 'android', DEV = 'phone', DROP = new Set();
  let PANE_TOKEN = 0;
  const IDEAS = {q: '', aud: '', goal: '', rows: [], total: 0, all: 0, t: null, ask: ''};
  const THREAD = {app: '', conv: '', rows: [], live: '', waiting: false, since: 0, started: 0, startedS: 0, timer: null, sig: '', steps: [], stepsRead: false};

  const starred = () => { try { const x = JSON.parse(localStorage.getItem(STAR_KEY) || '[]'); return Array.isArray(x) ? x.map(String) : []; } catch { return []; } };
  const isStar = id => starred().includes(S(id));
  function setStar(id, on) { const cur = starred().filter(x => x !== S(id)); try { localStorage.setItem(STAR_KEY, JSON.stringify((on ? [S(id), ...cur] : cur).slice(0, 60))); } catch {} }

  /* ================= router ================= */
  function parts() { return S(location.hash).replace(/^#\/?/, '').split('/').filter(Boolean); }
  async function route() {
    stopPoll(); clearTimeout(THREAD.timer);
    const p = parts();
    try {
      if (p[0] === 'app' && p[1]) return await openApp(decodeURIComponent(p[1]), p[2] || '');
      CUR = null;
      await loadLists();
      const page = {apps: 'apps', search: 'apps', starred: 'starred', ideas: 'ideas'}[p[0]] || 'home';
      drawHome(page);
      if (p[0] === 'search') $('#asFind')?.focus();
    } catch (e) { APP.innerHTML = `<div class="empty">${esc(e.message)} · <a href="#/">App Studio home</a></div>`; }
  }
  addEventListener('hashchange', route);
  const go = h => { if (location.hash === h) route(); else location.hash = h; };
  async function loadLists() {
    const r = await api('GET', '/api/apps');
    APPS = L(r.apps); LIB = M(r.library);
  }

  /* ================= home with its own sidebar ================= */
  const recRow = v => `<div class="rec${CUR && S(CUR.id) === S(v.id) ? ' on' : ''}"><a class="rl" href="#/app/${enc(S(v.id))}"><span class="dot ${dotCls(v)}" aria-hidden="true"></span><span class="rt"><span class="ell">${esc(name(v))}</span><span class="rs">${esc(statusOf(v)[0])}</span></span></a>
    <button class="rm" type="button" data-menu="${esc(S(v.id))}" aria-label="More for ${esc(name(v))}" title="Rename, star, delete">${ico('more', 16)}</button></div>`;
  function sidebar(cur) {
    const st = APPS.filter(v => isStar(v.id)), rec = APPS.filter(v => !isStar(v.id)).slice(0, 8);
    const nav = (h, k, label, ic) => `<a class="nav" href="${h}" ${cur === k ? 'aria-current="page"' : ''}>${ico(ic)}${esc(label)}</a>`;
    return `<aside class="side" aria-label="App Studio">
      <div class="brand"><div class="mark" aria-hidden="true"><span></span></div><div><b>Hoola</b><span>App Studio</span></div></div>
      <button class="new" type="button" data-act="new" title="New app (${MAC ? '⌘' : 'Ctrl'} K)"><span>${ico('plus', 16)}New app</span><kbd>${MAC ? '⌘ K' : 'Ctrl K'}</kbd></button>
      ${nav('#/', 'home', 'Home', 'home')}${nav('#/search', 'search', 'Search', 'search')}${nav('#/apps', 'apps', 'All apps', 'grid')}${nav('#/starred', 'starred', 'Starred', 'star')}${nav('#/ideas', 'ideas', 'App ideas', 'idea')}
      ${st.length ? `<div class="lbl">Starred</div>${st.map(recRow).join('')}` : ''}
      ${rec.length ? `<div class="lbl">Recent</div>${rec.map(recRow).join('')}` : ''}
      <div class="sp"></div>
      <a class="nav" href="/console/">${ico('back')}Back to Hoola</a>
    </aside>`;
  }
  function firstThumb(v) {
    for (const p of L(M(v.board).pages)) for (const s of L(p.sections)) if (S(s.thumb)) return S(s.thumb);
    return '';
  }
  function appCard(v) {
    const th = firstThumb(v), c = tint(v.id);
    return `<div class="cw"><a class="card" href="#/app/${enc(S(v.id))}"><span class="shot as-shot" style="background:linear-gradient(160deg,${c}22,var(--sunk))" aria-hidden="true"><span class="as-mini">${th ? imgTag(shot(v.id, th), '') : `<i style="background:${c}"></i><i style="background:${c}"></i>`}</span></span>
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b class="ell">${esc(name(v))}</b>${isStar(v.id) ? `<span class="stard" title="Starred" aria-label="Starred">${ico('star', 14)}</span>` : ''}${statusPill(v)}</span>
      <span class="mut sm ell">${esc([S(v.number), S(v.field_label), S(v.goal_label)].filter(Boolean).join(' · '))}</span>${v.updated_at ? `<span class="ed">Edited ${esc(ago(v.updated_at))}</span>` : ''}</span></a>
      <button class="cm" type="button" data-menu="${esc(S(v.id))}" aria-label="More for ${esc(name(v))}" title="Rename, star, delete">${ico('more', 16)}</button></div>`;
  }
  const CHIPS = [['Shop & delivery', 'A grocery shop app: order, home delivery, pay by UPI'], ['Bookings', 'A salon app: book a slot with a stylist, reminders'],
    ['Memberships', 'A gym app: memberships, daily check-in, renewals'], ['Courses', 'A coaching app: courses, tests, a parents\' view'],
    ['Staff app', 'A staff app for my team: tasks, attendance, daily report'], ['Field service', 'A field service app: jobs, photo proof, customer signature'],
    ['Khata / udhaar', 'A khata app: udhaar for regular customers, reminders, UPI payments']];
  function drawHome(page) {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    const plans = APPS.filter(v => S(v.status) === 'planned');
    let main;
    if (page === 'ideas') {
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">App ideas</h2><span class="tplall">${IDEAS.all ? Number(IDEAS.all).toLocaleString('en-IN') : '1 crore+'} ideas</span></div>
        <p class="mut">Every idea says who the app is for, the one special thing it does, its scale and its market. Open one and Hoola starts its plan; nothing is built until you say Haan.</p>
        <div class="tplbar"><label class="find">${ico('search', 16)}<input id="asIdeaQ" type="search" placeholder="Search: kirana, gym, rider app, school, salon…" aria-label="Search app ideas" autocomplete="off" value="${esc(IDEAS.q)}"></label>
          <select id="asIdeaAud" aria-label="App for"><option value="">App for: anyone</option>${[['customer', 'Customers'], ['owner', 'The owner'], ['staff', 'Staff'], ['delivery', 'Delivery partners'], ['dealer', 'Dealers'], ['member', 'Members'], ['manager', 'Managers']].map(([k, n]) => `<option value="${k}"${IDEAS.aud === k ? ' selected' : ''}>${n}</option>`).join('')}</select></div>
        <p class="mut sm" id="asIdeaCount" aria-live="polite">Loading ideas…</p>
        <div class="igrid" id="asIdeas"></div>
        <div class="tplmore"><button class="b" type="button" data-act="ideas-more" hidden>Show more</button></div></section>`;
    } else if (page === 'apps' || page === 'starred') {
      const list = page === 'starred' ? APPS.filter(v => isStar(v.id)) : APPS;
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">${page === 'starred' ? 'Starred' : 'All apps'}</h2><button class="b" type="button" data-act="new">${ico('plus', 16)}New app</button></div>
        ${page === 'apps' ? `<label class="find">${ico('search', 16)}<input id="asFind" type="search" placeholder="Search your apps" aria-label="Search your apps" autocomplete="off"></label>` : ''}
        ${list.length ? `<div class="grid" id="asAll">${list.map(appCard).join('')}</div><p class="mut" id="asNone" hidden>No app matches.</p>`
          : `<div class="panel mut">${page === 'starred' ? `Nothing starred yet. Open the ${ico('more', 14)} menu on any app and choose Add to starred.` : 'No app yet. Write one line on the App Studio home.'}</div>`}</section>`;
    } else {
      main = `<div class="aura" aria-hidden="true"><i class="a1"></i><i class="a2"></i><i class="a3"></i><i class="a4"></i></div>
      <section class="hero"><span class="eyebrow"><b>New</b>Your own Android and iPhone app, designed in front of you${ico('arrow', 14)}</span><h1>What app should we make today?</h1>
        <p class="mut">Describe it in one line. Hoola plans every screen, shows you three looks, designs the whole app, then builds the real Android and iPhone app. Nothing reaches the store until you tap.</p>
        <form class="ask" data-form="ask">
          <label for="asAsk" class="sr">Describe your app</label>
          <textarea id="asAsk" rows="3" maxlength="2000" placeholder="An app for Sharma Kirana in Akola: order groceries, home delivery, pay by UPI, udhaar reminders">${esc(PREFILL)}</textarea>
          <div class="bar">
            <a class="b ghost" href="#/ideas">${ico('idea', 15)}Browse ideas</a>
            <span class="sp"></span>
            <span class="mut sm mnote" id="asModeNote">${mode === 'plan' ? 'Plan: read the plan first, then say Haan' : 'Build: plan, then 3 looks'}</span>
            <div class="seg" role="group" aria-label="Mode"><button type="button" data-mode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-mode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
            <button class="go" type="submit" aria-label="Start">${ico('up', 18)}</button>
          </div>
        </form>
        <div id="asAskWork" class="step wrap" role="status" aria-live="polite" style="max-width:780px;margin-top:10px" hidden></div>
        <div class="chips">${CHIPS.map(([t, d]) => `<button class="chip" type="button" data-fill="${esc(d)}">${esc(t)}</button>`).join('')}<a class="chip" href="#/ideas">More ideas</a></div>
      </section>
      ${plans.length ? `<section class="wrap"><div class="sec"><h2>Plans waiting for your Haan</h2></div><div class="grid">${plans.slice(0, 4).map(appCard).join('')}</div></section>` : ''}
      <section class="wrap"><div class="sec"><h2>Your apps</h2>${APPS.length ? `<a class="more" href="#/apps">View all ${ico('arrow', 13)}</a>` : ''}</div>
        ${APPS.length ? `<div class="grid">${APPS.slice(0, 8).map(appCard).join('')}</div>` : '<div class="panel mut">No app yet. Write one line above.</div>'}</section>
      <section class="wrap"><div class="sec"><h2>Or start from</h2></div><div class="starts">
        <button class="st" type="button" data-act="focus"><span class="si">${ico('chat')}</span><span><b>Describe it</b><span class="mut sm">One line in your own words.</span></span></button>
        <a class="st" href="#/ideas"><span class="si">${ico('idea')}</span><span><b>An app idea</b><span class="mut sm">${LIB.ideas ? Number(LIB.ideas).toLocaleString('en-IN') : 'Crores of'} ideas, each with who it is for.</span></span></a>
        <button class="st" type="button" data-fill="An app for my business with the same data and logins as my Hoola website"><span class="si">${ico('globe')}</span><span><b>My website</b><span class="mut sm">Same data and logins as your Hoola website.</span></span></button>
        <button class="st" type="button" data-fill="A complete system for my business: a customer app, a staff app and a delivery partner app on one backend"><span class="si">${ico('tpl')}</span><span><b>Whole system</b><span class="mut sm">Customer, staff and rider apps on one backend.</span></span></button>
      </div></section>`;
    }
    APP.innerHTML = `<div class="home">${sidebar(page)}<main class="hmain">${main}</main></div>`;
    PREFILL = '';
    paintImgs();
    if (page === 'ideas') loadIdeas(true);
    document.title = 'Hoola App Studio';
  }

  /* ---------- the idea library ---------- */
  function ideaCard(x) {
    return `<button class="icard" type="button" data-idea="${esc(S(x.id))}" data-idea-name="${esc(S(x.name))}"><span class="who">For ${esc(S(x.aud_label) || 'customers')}</span>
      <b style="font-size:15px">${esc(S(x.field_label))}: ${esc(S(x.goal_label))}</b>
      <span class="mut sm">${esc([S(x.scale_label), S(x.market_label), S(x.tier_label)].filter(Boolean).join(' · '))}</span>
      <span class="as-row" style="gap:6px">${x.twist_label ? `<span class="pill v">${ico('spark', 12)}${esc(S(x.twist_label))}</span>` : ''}${x.complex ? pill('Team app') : ''}<span class="pill">Android + iPhone</span></span></button>`;
  }
  async function loadIdeas(fresh) {
    const box = $('#asIdeas'); if (!box) return;
    const off = fresh ? 0 : IDEAS.rows.length;
    try {
      const r = await api('GET', `/api/apps-ideas?q=${enc(IDEAS.q)}&aud=${enc(IDEAS.aud)}&offset=${off}&limit=24`);
      const items = L(r.items);
      IDEAS.rows = fresh ? items : IDEAS.rows.concat(items);
      IDEAS.total = N(r.total); IDEAS.all = N(r.all_ideas) || IDEAS.all;
      const best = fresh && r.best && r.best.id ? [r.best] : [];
      const rows = best.concat(IDEAS.rows.filter(x => !best.length || x.id !== best[0].id));
      box.innerHTML = rows.length ? rows.map(ideaCard).join('') : `<div class="panel mut">${esc(S(r.ask) || 'No idea matches those words. Try a business type: kirana, gym, salon, school.')}</div>`;
      const c = $('#asIdeaCount');
      if (c) c.textContent = `Showing ${rows.length.toLocaleString('en-IN')} of ${IDEAS.total.toLocaleString('en-IN')} ideas${IDEAS.all ? ` · ${IDEAS.all.toLocaleString('en-IN')} in the library` : ''}`;
      const more = APP.querySelector('[data-act="ideas-more"]'); if (more) more.hidden = IDEAS.rows.length >= IDEAS.total;
    } catch (e) { box.innerHTML = `<div class="panel mut">${esc(e.message)}</div>`; }
  }

  /* ---------- start a new app ---------- */
  async function newConv(title) {
    const c = S((await api('POST', '/api/conversations')).id);
    if (title) api('PATCH', `/api/conversations/${enc(c)}`, {title}).catch(() => {});
    return c;
  }
  /* v0.707 SEEDHA WORKSPACE: the moment she sends, the page moves to the app's workspace (her words in the chat, a live
     work card on the real clock, the plan area filling in) instead of waiting on the home under a small line. */
  function drawPending(text) {
    const t0 = nowS(), plan = store.get(MODE_KEY) === 'plan';
    const steps = ['Reading your words', 'Planning every screen, tab and list', plan ? 'Writing the plan' : 'Starting three looks of the Home screen'];
    APP.innerHTML = `<div class="wsp" data-pending="1">
      <header class="top"><a href="#/" aria-label="App Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">New app</span>${pill(plan ? 'Writing the plan' : 'Starting', 'v')}<span class="sp"></span><a class="b ghost" href="#/apps">All apps</a></header>
      <div class="body"><section class="chat" aria-label="Chat with Hoola">
          <div class="msgs" aria-live="polite"><div class="me">${esc(text)}</div>
            <div class="chatact wcard"><div class="step whead"><span class="spin" aria-hidden="true"></span><span class="wt"><b>${plan ? 'Writing your plan' : 'Starting your app'}</b><span id="asPendNow">${esc(steps[0])}</span></span><span class="tm" data-t0="${t0}"></span></div>
              <div class="prog ind" role="progressbar" aria-label="Progress"><i style="width:30%"></i></div>
              <ol class="acts" id="asPendSteps">${steps.map((x, i) => `<li class="${i ? 'wait' : 'run'}" data-i="${i}">${i ? '<span class="tick off" aria-hidden="true"></span>' : '<span class="spin" aria-hidden="true"></span>'}<div class="sl"><span class="ell">${esc(x)}</span></div><span class="tm"${i ? '' : ` data-t0="${t0}"`}></span></li>`).join('')}</ol>
              <div class="wfoot"><span class="ell">Usually under a minute. Nothing is built until you say so.</span></div></div></div>
          <form class="comp" aria-disabled="true"><textarea rows="2" disabled placeholder="You can write here once the app opens…"></textarea><div class="cbar"><span class="sp"></span><button class="send" type="button" disabled aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" aria-label="App"><div class="ptop"><nav class="views" aria-label="Views"><button type="button" aria-current="page">Plan</button><button type="button" disabled>Looks</button><button type="button" disabled>Screens</button></nav></div>
          <div class="stage"><article class="doc skel" aria-busy="true" aria-label="The plan is being written"><i class="sk w40"></i><i class="sk h"></i><i class="sk"></i><i class="sk w80"></i><i class="sk w60"></i><i class="sk h"></i><i class="sk"></i><i class="sk w70"></i></article></div></section></div></div>`;
    document.title = 'New app · Hoola App Studio';
    startTick();
    let k = 0; clearInterval(drawPending._t);
    drawPending._t = setInterval(() => {
      const ol = $('#asPendSteps'); if (!ol) return clearInterval(drawPending._t);
      if (k >= steps.length - 1) return;
      const now = nowS(), cur = ol.querySelector(`[data-i="${k}"]`), nxt = ol.querySelector(`[data-i="${k + 1}"]`);
      if (cur) { cur.className = 'ok'; cur.firstElementChild.outerHTML = tick; const tm = cur.querySelector('.tm'); if (tm) { tm.removeAttribute('data-t0'); tm.textContent = dur(now - Number(tm.dataset.s || t0)); } }
      k++;
      if (nxt) { nxt.className = 'run'; nxt.firstElementChild.outerHTML = '<span class="spin" aria-hidden="true"></span>'; const tm = nxt.querySelector('.tm'); if (tm) { tm.dataset.t0 = now; tm.dataset.s = now; } }
      const nw = $('#asPendNow'); if (nw) nw.textContent = steps[k];
      tickClocks();
    }, 8000);
  }
  async function startApp(body) {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    let work = null;
    const say = t => { const n = $('#asPendNow'); if (n) n.textContent = t; };
    drawPending(S(body.brief));
    try {
      const conv = await newConv('');
      let v;
      try { v = await api('POST', '/api/apps', {...body, conversation_id: conv}); }
      catch (e) {
        if (!/ek sawaal|Pakka karne/i.test(e.message)) throw e;
        const fd = await dialog('One quick question', `<p class="sm">${esc(e.message.replace(/^Pakka karne ke liye ek sawaal:\s*/i, ''))}</p>
          <label class="sm mut" for="asSure">Your answer (or leave empty to go with the first meaning)</label><input class="in" id="asSure" name="a" maxlength="300">`);
        if (!fd) { clearInterval(drawPending._t); PREFILL = S(body.brief); drawHome('home'); return; }
        const a = S(fd.get('a')).trim();
        v = await api('POST', '/api/apps', {...body, brief: a ? `${body.brief}. ${a}` : body.brief, answers: {...M(body.answers), sure: true}, conversation_id: conv});
      }
      store.set(convKey(v.id), conv);
      api('PATCH', `/api/conversations/${enc(conv)}`, {title: `App · ${name(v)}`}).catch(() => {});
      if (mode === 'build' && !L(v.questions).length) {
        say('Plan ready. Starting the three looks…');
        try { await api('POST', `/api/apps/${enc(v.id)}/plan`, {conversation_id: conv}); go(`#/app/${enc(v.id)}/looks`); return; }
        catch (e) { toast(e.message, true); }
      }
      go(`#/app/${enc(v.id)}/plan`);
    } catch (e) {
      clearInterval(drawPending._t);
      PREFILL = S(body.brief); drawHome('home');          // back home with her words in the box and the reason under it
      work = $('#asAskWork');
      if (work) { work.hidden = false; work.innerHTML = `<span class="li bad">${esc(e.message)} · your words are still in the box, press send again</span>`; }
      else toast(e.message, true);
    } finally { clearInterval(drawPending._t); }
  }

  /* ---------- project menu (open, new tab, rename, star, delete) ---------- */
  function closeMenu() { document.getElementById('asMenu')?.remove(); }
  function openMenu(btn, id) {
    const open = document.getElementById('asMenu'); closeMenu();
    if (open && open.dataset.for === id) return;
    const v = APPS.find(x => S(x.id) === id) || (CUR && S(CUR.id) === id ? CUR : null); if (!v) return;
    const m = document.createElement('div');
    m.id = 'asMenu'; m.className = 'wsmenu'; m.dataset.for = id; m.setAttribute('role', 'menu'); m.setAttribute('aria-label', `${name(v)} options`);
    const it = (k, ic, label, cls = '') => `<button type="button" role="menuitem" class="${cls}" data-mi="${k}">${ico(ic, 16)}<span>${label}</span></button>`;
    m.innerHTML = it('open', 'chat', 'Open') + it('tab', 'ext', 'Open in new tab') + it('rename', 'edit', 'Rename') +
      it('star', 'star', isStar(id) ? 'Remove from starred' : 'Add to starred') + '<hr>' + it('delete', 'trash', 'Delete', 'bad');
    document.body.appendChild(m);
    const r = btn.getBoundingClientRect(), w = m.offsetWidth, h = m.offsetHeight;
    m.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.right - w)) + 'px';
    m.style.top = (r.bottom + h + 8 > innerHeight ? Math.max(8, r.top - h - 4) : r.bottom + 4) + 'px';
    m.querySelector('button')?.focus();
    m.addEventListener('click', ev => { const b = ev.target.closest('[data-mi]'); if (!b) return; closeMenu(); menuAct(b.dataset.mi, v); });
    m.addEventListener('keydown', ev => {
      const items = [...m.querySelectorAll('button')], i = items.indexOf(document.activeElement);
      if (ev.key === 'Escape') { closeMenu(); btn.focus(); }
      else if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { ev.preventDefault(); items[(i + (ev.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus(); }
    });
  }
  document.addEventListener('click', e => { const m = document.getElementById('asMenu'); if (m && !m.contains(e.target) && !e.target.closest('[data-menu]')) closeMenu(); });
  addEventListener('resize', closeMenu); addEventListener('hashchange', closeMenu);
  async function menuAct(k, v) {
    const id = S(v.id), inApp = CUR && S(CUR.id) === id;
    try {
      if (k === 'open') return go('#/app/' + enc(id));
      if (k === 'tab') return void window.open(location.pathname + '#/app/' + enc(id), '_blank', 'noopener');
      if (k === 'star') { const on = !isStar(id); setStar(id, on); toast(on ? 'Added to starred.' : 'Removed from starred.'); if (!inApp) route(); return; }
      if (k === 'rename') {
        const fd = await dialog('Rename app', `<label class="sm mut" for="asRename">The app's name</label><input class="in" id="asRename" name="name" maxlength="60" required value="${esc(name(v))}">
          <p class="mut sm">The name shown in your list and inside the app. The design is not redrawn; the next build carries the new name.</p>`);
        const nm = S(fd?.get('name')).trim(); if (!nm || nm === name(v)) return;
        const nv = await api('POST', `/api/apps/${enc(id)}/answers`, {answers: {name: nm}});
        toast('Renamed.');
        if (inApp) { CUR = nv; drawShell(); } else route();
        return;
      }
      if (k === 'delete') {
        if (!confirm(`Delete "${name(v)}"?\n\nIts design, screens and builds are removed from Hoola. An app already on the Play Store or App Store stays there. This cannot be undone.`)) return;
        await api('DELETE', `/api/apps/${enc(id)}`);
        setStar(id, false); store.del(convKey(id)); toast('Deleted.');
        if (inApp) go('#/apps'); else route();
      }
    } catch (er) { toast(er.message, true); }
  }

  /* ================= workspace ================= */
  async function openApp(id, view) {
    const v = await api('GET', `/api/apps/${enc(id)}`);
    const same = CUR && S(CUR.id) === S(v.id);
    CUR = v;
    if (!same) { DROP = new Set(); PLAT = 'android'; }
    VIEW = VIEW_KEYS.includes(view) ? view : defaultView(v);
    if (!APPS.length) { try { await loadLists(); } catch {} }
    if (!same || !$('#asPane')) { drawShell(); await openThread(); } else { drawTop(); drawState(); drawPane(); }
    startPoll();
  }
  function defaultView(v) {
    const st = S(v.status);
    if (BUILDING.includes(anSt(v)) || (st === 'approved' && anSt(v))) return 'android';
    if (BUILDING.includes(iosSt(v))) return 'iphone';
    return {planned: 'plan', draft: 'plan', looks: 'looks', designing: 'screens', checking: 'screens', ready: 'screens', approved: 'android'}[st] || 'screens';
  }
  function drawTop() {
    const t = APP.querySelector('.top'); if (!t || !CUR) return;
    t.querySelector('.pname').textContent = name(CUR);
    const p = $('#asPill'); if (p) p.innerHTML = statusPill(CUR);
  }
  function drawShell() {
    const v = CUR, mode = store.get(MODE_KEY + '.chat') === 'plan' ? 'plan' : 'build';
    APP.innerHTML = `<div class="wsp">
      <header class="top"><a href="#/" aria-label="App Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">${esc(name(v))}</span><button class="ib" type="button" data-menu="${esc(S(v.id))}" aria-label="App options" title="Rename, star, delete">${ico('chev', 16)}</button>
        <span id="asPill">${statusPill(v)}</span><span class="sp"></span>
        <span class="tsave">Every change is saved as a version</span>
        <button class="b" type="button" data-view="history">${ico('hist', 15)}<span>History</span></button>
        <button class="b" type="button" data-view="prototype">${ico('phone', 15)}<span>Try on phone</span></button>
        <button class="b dark" type="button" data-view="store"><span>Publish</span></button></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this app">
          <div class="msgs" id="asMsgs" aria-live="polite"></div>
          <div id="asState" style="padding:0 18px"></div>
          <form class="comp" data-form="thread"><label for="asTh" class="sr">Message Hoola about this app</label>
            <textarea id="asTh" rows="2" maxlength="4000" placeholder="Ask Hoola to change anything in the app…"></textarea>
            <div class="cbar">
              <div class="seg" role="group" aria-label="Mode"><button type="button" data-cmode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-cmode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
              <span class="sp"></span><button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" id="asPane" aria-label="App"></section>
      </div></div>`;
    document.title = `${name(v)} · Hoola App Studio`;
    drawState(); drawPane();
  }
  function viewsBar() {
    return `<div class="ptop"><nav class="views" aria-label="Views">${VIEWS.map(x => x === '|' ? '<span class="vsep" aria-hidden="true"></span>'
      : `<button type="button" data-view="${x[0]}" ${VIEW === x[0] ? 'aria-current="page"' : ''}>${ico(VIEW_IC[x[0]] || 'grid', 15)}<span>${esc(x[0] === 'looks' && S(CUR.status) === 'looks' && L(CUR.looks).length ? 'Looks · pick one' : x[1])}</span>${x[0] === 'looks' && S(CUR.status) === 'looks' && L(CUR.looks).length ? '<i class="vdot" aria-hidden="true"></i>' : ''}</button>`).join('')}</nav></div>`;
  }
  async function drawPane() {
    const pane = $('#asPane'); if (!pane || !CUR) return;
    const my = ++PANE_TOKEN;
    if (pane.dataset.view !== VIEW) { pane.dataset.view = VIEW; pane.dataset.fresh = '1'; }   // motion once per page, never on a redraw
    const keep = pane.querySelector('.pbody')?.scrollTop || 0;
    let inner;
    try { inner = await (PANES[VIEW] || PANES.plan)(CUR); }
    catch (e) { inner = `<div class="pbody"><div class="callout bad">${esc(e.message)}</div></div>`; }
    if (my !== PANE_TOKEN || !$('#asPane')) return;
    const fresh = pane.dataset.fresh === '1'; delete pane.dataset.fresh;
    pane.innerHTML = viewsBar() + inner;
    const pb = pane.querySelector('.pbody'); if (pb && keep && !fresh) pb.scrollTop = keep;
    if (pb && fresh) pb.classList.add('pin');
    paintImgs(pane);
    pane.querySelectorAll('[data-qr]').forEach(el => { el.innerHTML = qrSvg(el.dataset.qr); el.removeAttribute('data-qr'); });
  }
  const B = (k, label, cls = '', extra = '') => `<button class="b ${cls}" type="button" data-act="${k}"${extra}>${label}</button>`;
  const P = (inner, cls = '') => `<div class="pbody ${cls}">${inner}</div>`;
  // one header for every pane: title, a plain line under it, controls on the right (all aligned on one line)
  const head = (title, right = '', sub = '') => `<header class="phd"><div class="pht"><h2>${title}</h2>${sub ? `<p>${sub}</p>` : ''}</div>${right ? `<div class="pha">${right}</div>` : ''}</header>`;
  const ph = (title, right = '') => `<div class="pnh"><b>${title}</b>${right}</div>`;
  const emptyNote = t => `<div class="callout">${t}</div>`;
  const plural = (n, one, many) => `${N(n).toLocaleString('en-IN')} ${N(n) === 1 ? one : many || one + 's'}`;
  // the build runner's reason, readable: no setting names or file names in brackets, said once, ends with a full stop
  const iosWhy = w => { let t = S(w).replace(/\s*\([^()]*\)/g, '').replace(/\s+([.:,])/g, '$1').replace(/[.:]+$/, '').trim();
    return t ? (/mac/i.test(t) ? '' : 'iPhone apps compile on a Mac. ') + t + '.' : 'iPhone apps compile on a Mac, and your GitHub builds repo with the iPhone workflow is not set up yet.'; };
  const kv = o => `<dl class="kv">${Object.entries(o).filter(([, x]) => S(x)).map(([k, x]) => `<dt>${esc(k)}</dt><dd>${esc(x)}</dd>`).join('')}</dl>`;
  const phone = (src, alt, cls = '', on = false) => `<div class="as-ph ${cls}${on ? ' on' : ''}">${src ? imgTag(src, alt) : `<span class="wait">${esc(alt)}</span>`}</div>`;

  /* ---------- the panes ---------- */
  const PANES = {
    async plan(v) {
      const p = M(v.plan), st = S(v.status), open = st === 'planned' || st === 'stopped' || st === 'failed';
      const scr = L(p.screens), qs = L(v.questions), bp = M(p.blueprint);
      const lab = Object.fromEntries(scr.map(s => [S(s.id), S(s.label)]));
      const tables = L(bp.tables || bp.data).map(t => typeof t === 'string' ? {name: t} : M(t));
      const roles = L(bp.roles).map(r => typeof r === 'string' ? r : S(M(r).label || M(r).name || M(r).key));
      const feats = L(bp.features || bp.phone).map(f => M(f));
      return P(`${head('The plan', open ? pill('Waiting for your OK', 'v') : pill('Plan agreed', 'ok'), 'Every screen, the main flow and the rules the app keeps')}
        ${S(M(p.scope).request) || S(v.brief) ? `<div class="callout">${esc(S(M(p.scope).request) || S(v.brief))}</div>` : ''}
        <div class="col2"><div class="panel">${ph(`Screens <span class="cnt">${scr.length - DROP.size}</span>`)}
          <div class="chipset">${scr.map(s => open ? `<button type="button" data-drop="${esc(S(s.id))}" aria-pressed="${DROP.has(S(s.id))}" title="${esc(S(s.design))}">${esc(S(s.label))}${s.tab ? ' ·' : ''}</button>` : `<span title="${esc(S(s.design))}">${esc(S(s.label))}</span>`).join('')}</div>
          <span class="mut sm">${open ? 'Tap a screen to drop it (main tabs and login always stay). ' : ''}Privacy, delete-account and other legal screens are added by code${L(p.code_screens).length ? `: ${esc(L(p.code_screens).map(c => S(c.label)).join(', '))}` : ''}.</span></div>
          <div class="panel">${L(p.flow).length ? `<h4 class="psub">Main flow</h4><span class="sm">${esc(L(p.flow).map(x => lab[S(x)] || S(x)).join(' → '))}</span>` : ''}
            ${L(p.tabs).length ? `<h4 class="psub">Tabs</h4><span class="sm">${esc(L(p.tabs).map(x => lab[S(x)] || S(x)).join(' · '))}</span>` : ''}
            ${L(p.rules).length ? `<h4 class="psub">Rules</h4><ul class="sm" style="margin:0;padding-left:18px">${L(p.rules).map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}
            ${v.field_label || v.goal_label ? `<h4 class="psub">App type</h4><span class="sm">${esc([S(v.field_label), S(v.goal_label), S(v.style_label)].filter(Boolean).join(' · '))}</span>` : ''}</div></div>
        ${tables.length || roles.length || feats.length ? `<div class="col2">${tables.length ? `<div class="panel">${ph('Data')}<div class="chipset">${tables.map(t => `<span>${esc(S(t.label || t.name || t.key))}</span>`).join('')}</div></div>` : ''}
          ${roles.length || feats.length ? `<div class="panel">${roles.length ? `<h4 class="psub">Who uses it</h4><div class="chipset">${roles.map(r => `<span>${esc(r)}</span>`).join('')}</div>` : ''}
            ${feats.length ? `<h4 class="psub">Phone features</h4><div class="chipset">${feats.map(f => `<span>${esc(S(f.label || f.name || f.key))}</span>`).join('')}</div>` : ''}</div>` : ''}</div>` : ''}
        ${qs.length ? `<form class="panel as-form" data-form="answers">${ph(qs.length === 1 ? 'One question' : `${qs.length} questions`)}
          ${qs.map((q, i) => `<label>${esc(q)}<input name="${i}" maxlength="300"></label>`).join('')}
          <div class="as-row"><button class="b" type="submit">Save answers</button></div></form>` : ''}
        ${open ? `<div class="as-row">${B('plan', `${ico('check', 15)}Approve plan · make 3 looks`, 'pri')}<span class="mut sm">Want changes? Write them in the chat on the left.</span></div>` : ''}`);
    },
    async looks(v) {
      const looks = L(v.looks), st = S(v.status);
      if (!looks.length) return P(head('Three looks of your Home screen') + (st === 'looks' || st === 'planned'
        ? `${st === 'looks' ? '' : emptyNote('Approve the plan first; then three looks are drawn.')}<div class="looks">${[1, 2, 3].map(i => `<div class="lk">${phone('', st === 'looks' ? 'Drawing look ' + i + '…' : 'Look ' + i, 'md')}</div>`).join('')}</div>`
        : emptyNote('The looks were made earlier. Your chosen look is now in Screens.')));
      const can = st === 'looks';
      return P(`${head(`Pick a look for ${esc(name(v))}`, '', 'Each one is a real Android screenshot of your Home screen')}
        <div class="looks">${looks.map(l => { const on = v.chosen_look != null && N(v.chosen_look) === N(l.i);
          return `<div class="lk${on ? ' on' : ''}"><div class="lkh"><b>Look ${N(l.i) + 1} · ${esc(S(l.label) || S(l.style))}</b>${on ? pill('Chosen', 'ok') : ''}</div>
          ${phone(M(l.shots).android ? shot(v.id, M(l.shots).android) : '', 'Look ' + (N(l.i) + 1), 'md')}
          ${M(l.art).concept ? `<span class="mut sm" style="text-align:center">${esc(S(M(l.art).concept))}</span>` : ''}
          <div class="sw">${L(l.colors).map(HEX).filter(Boolean).map(c => `<i style="background:${c}"></i>`).join('')}</div>
          ${can ? B('look', `Use look ${N(l.i) + 1}`, N(l.i) === 0 ? 'pri' : '', ` data-i="${N(l.i)}"`) : ''}</div>`; }).join('')}</div>
        ${can ? '<div class="callout">Want a mix? Say it in the chat: "look 1 with the colours of look 2".</div>' : ''}`);
    },
    async screens(v) {
      const b = M(v.board), pages = L(b.pages), ch = M(v.checks), st = S(v.status);
      if (!pages.length) return P(head('Screens') + emptyNote(st === 'looks' ? 'Pick a look first; then every screen is designed here while you watch.' : 'Screens appear here once the design starts.'));
      const total = N(b.total), done = N(b.done), suf = PLAT === 'ios' ? '-ios.jpg' : PLAT === 'dark' ? '-android-alt.jpg' : '-android.jpg';
      const canOk = st === 'ready' && !L(ch.blocking).length && S(v.hash);
      const img = s => S(s.state) === 'done' ? (PLAT === 'android' && S(s.thumb) ? shot(v.id, S(s.thumb)) : shot(v.id, S(s.key) + suf)) : '';
      return P(`${head(`Screens`, `<div class="seg" role="group" aria-label="Platform">${[['android', 'Android'], ['ios', 'iPhone'], ['dark', 'Dark']].map(([k, n]) => `<button type="button" data-plat="${k}" aria-pressed="${PLAT === k}">${n}</button>`).join('')}</div>
          ${v.approved ? pill('Design approved', 'ok') : B('approve', `${ico('lock', 15)}Approve design`, 'pri', canOk ? '' : ' disabled title="Ready when every screen is designed and no check is blocking"')}`, `${done} of ${total} designed · tap a screen to see it large`)}
        ${pages.map(pg => `<div class="as-page">${esc(S(pg.title))}</div><div class="sgrid">${L(pg.sections).map(s => {
          const state = S(s.state), lbl = state === 'building' ? 'Designing now…' : state === 'fixing' ? 'Fixing…' : state === 'done' ? S(s.label) : 'Waiting';
          return `<div class="scrn" data-zoom="${state === 'done' ? esc(img(s).replace('thumb/', '')) : ''}">${phone(img(s), lbl, '', state === 'building' || state === 'fixing')}
            <span class="cap">${state === 'done' ? tick : state === 'building' || state === 'fixing' ? '<span class="spin" aria-hidden="true"></span>' : ''}${esc(S(s.label))}</span></div>`; }).join('')}</div>`).join('')}
        ${M(b.overview)[PLAT === 'dark' ? 'android-alt' : PLAT] ? `<div class="panel">${ph('All screens on one sheet')}<img data-src="${esc(shot(v.id, M(b.overview)[PLAT === 'dark' ? 'android-alt' : PLAT]))}" alt="Overview of every screen" style="width:100%;border-radius:12px"></div>` : ''}
        ${ch.passed != null || L(ch.blocking).length || L(ch.warnings).length ? `<div class="panel">${ph('Checks', `<span class="pills">${pill(`${L(ch.blocking).length} blocking`, L(ch.blocking).length ? 'bad' : 'ok')}${L(ch.warnings).length ? pill(`${L(ch.warnings).length} notes`, 'warn') : ''}${N(ch.blanks) ? pill(`${N(ch.blanks)} blanks to fill`, 'warn') : ''}</span>`)}
          ${L(ch.blocking).concat(L(ch.warnings)).slice(0, 10).map(x => `<span class="sm">${esc([S(M(x).screen), S(M(x).text)].filter(Boolean).join(': '))}</span>`).join('')}</div>` : ''}`);
    },
    async prototype(v) {
      const url = S(v.preview);
      if (!url || !N(v.version)) return P(head('Prototype') + emptyNote('The tap-through prototype appears once the first version of the design is ready.'));
      const frame = DEV === 'tablet' ? `<div class="as-tab"><iframe title="Prototype of ${esc(name(v))}" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="${esc(url)}"></iframe></div>`
        : `<div class="as-ph lg"><iframe title="Prototype of ${esc(name(v))}" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="${esc(url)}"></iframe></div>`;
      return P(`${head('Prototype', `<div class="seg" role="group" aria-label="Device"><button type="button" data-dev="phone" aria-pressed="${DEV === 'phone'}" aria-label="Phone">${ico('phone', 16)}</button><button type="button" data-dev="tablet" aria-pressed="${DEV === 'tablet'}" aria-label="Tablet">${ico('tab', 16)}</button></div>
          <a class="b" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${ico('ext', 14)}Open in a new tab</a>`, 'Tap through the app like a customer. Nothing here is saved.')}
        <div class="stage as-stage">${frame}
          <div class="panel as-qrp">${ph('Try it on your own phone')}<span class="mut sm">Scan with your phone camera: the same prototype opens in your phone's browser. Every screen links like the real app.</span>
          <div class="qr" data-qr="${esc(url)}"></div>${pill(`Version ${N(v.version)}`, 'v')}</div></div>`);
    },
    async android(v) {
      const a = await api('GET', `/api/apps/${enc(v.id)}/android`);
      const st = S(a.status), qa = M(a.qa), apk = M(a.apk), act = M(v.activity);
      if (!v.approved && !st) return P(head('Android app', '', 'Built in Kotlin from the approved design') + emptyNote(`The real Android app is built from the approved design. Finish the screens and tap <b>Approve design</b> first.`) + `<div>${B('to-screens', 'Go to Screens')}</div>`);
      const steps = [['Write screens', ['writing'].includes(st), ['building', 'fixing', 'ready', 'zip'].includes(st)],
        ['Compile', st === 'building' || (st === 'fixing' && !qa.ran), ['ready', 'zip'].includes(st)],
        ['Phone check', st === 'fixing' && qa.ran, st === 'ready' && qa.ran],
        ['APK ready', false, st === 'ready' && !!apk.file]];
      const andSteps = S(act.job) === 'android' ? L(act.steps) : [];
      return P(`${head(`Android app${N(a.build) ? ` · build ${N(a.build)}` : ''}`, BUILDING.includes(st) ? pill(S(a.now) ? 'Building' : 'Working', 'v') : st === 'ready' ? pill('Ready', 'ok') : st === 'failed' ? pill('Needs attention', 'bad') : st === 'zip' ? pill('Project ready', 'ok') : '', 'Built in Kotlin from the approved design, then opened on a phone before you get it')}
        ${st ? `<div class="pipe">${steps.map(([n, run, ok]) => `<div class="pp ${ok ? 'ok' : run ? 'run' : ''}"><i class="ppn" aria-hidden="true">${ok ? tick : run ? '<span class="spin"></span>' : ''}</i><b>${n}</b><span>${ok ? 'Done' : run ? 'Working now' : 'Waiting'}</span></div>`).join('')}</div>` : ''}
        ${S(a.error) ? `<div class="callout bad">${esc(S(a.error))}</div>` : ''}
        ${st === 'zip' ? `<div class="callout">No build machine is set up, so Hoola made the Android Studio project instead of an APK. ${esc(S(a.note))}</div>` : ''}
        ${andSteps.length ? `<div class="panel">${ph('Steps')}${stepList({steps: andSteps})}</div>` : ''}
        <div class="col2">${apk.file ? `<div class="panel">${ph('Install on a phone')}<div class="as-row top"><div class="qr" data-qr="${esc(S(a.apk_url))}"></div>
          <div style="display:flex;flex-direction:column;gap:6px;min-width:0"><span class="sm">${esc(S(apk.file))} · ${esc(mb(apk.size))}</span><span class="mut sm">${esc(S(apk.package))} · version ${esc(S(apk.version_name))}</span>
          ${a.apk_url ? `<a class="b" href="${esc(S(a.apk_url))}" target="_blank" rel="noopener noreferrer">${ico('dl', 15)}Download APK</a>` : ''}
          ${a.zip_url ? `<a class="b" href="${esc(S(a.zip_url))}" target="_blank" rel="noopener noreferrer">${ico('code', 15)}Android Studio project</a>` : ''}
          <span class="mut sm">Scan with your Android phone; Android asks you to allow the install. The links work for 7 days.</span></div></div></div>`
          : a.zip_url ? `<div class="panel">${ph('Project')}<a class="b" href="${esc(S(a.zip_url))}" target="_blank" rel="noopener noreferrer">${ico('code', 15)}Android Studio project${a.zip_size ? ` · ${mb(a.zip_size)}` : ''}</a></div>` : ''}
          ${qa.ran ? `<div class="panel">${ph(`Phone check · build ${N(qa.build)}`)}<div class="as-row">${pill(`${N(qa.opened)}/${N(qa.total)} screens opened`, N(qa.opened) === N(qa.total) ? 'ok' : 'warn')}${pill(`${L(qa.crashed).length} crashes`, L(qa.crashed).length ? 'bad' : 'ok')}
            ${M(qa.perf).cold_ms ? pill(`cold start ${(N(M(qa.perf).cold_ms) / 1000).toFixed(1)} s`, M(qa.budget).cold_ms === 'over' ? 'warn' : '') : ''}${M(qa.perf).apk_mb ? pill(`APK ${N(M(qa.perf).apk_mb).toFixed(1)} MB`) : ''}${N(qa.a11y_count) ? pill(`${N(qa.a11y_count)} accessibility notes`, 'warn') : ''}
            ${L(M(qa.flows).dead).length ? pill(`${L(M(qa.flows).dead).length} buttons do nothing`, 'warn') : ''}</div>
            <div class="as-row" style="gap:10px">${L(qa.shots).slice(0, 4).map(sid => phone(`/api/apps/${enc(v.id)}/android/qa/${enc(sid)}`, sid, 'sm')).join('')}</div></div>`
            : st === 'ready' ? `<div class="panel">${ph('Phone check')}<span class="mut sm">${esc(S(qa.why) || 'No phone emulator was available for this build, so the screens were not opened on a phone.')}</span></div>` : ''}</div>
        <div class="as-row">${['ready', 'zip', 'failed', ''].includes(st) && v.approved ? B('android', `${ico('reload', 15)}${N(a.build) ? 'Build again' : 'Build the Android app'}`, N(a.build) ? '' : 'pri') : ''}
          ${S(a.say) && !BUILDING.includes(st) ? `<span class="mut sm">${esc(S(a.say))}</span>` : ''}</div>
        ${L(a.history).length ? `<div class="panel">${ph('Builds')}<div class="tscroll"><table class="t"><tr><th>Build</th><th>Version</th><th>When</th><th>What changed</th><th></th></tr>
          ${L(a.history).map(h => `<tr><td>${N(h.build)}</td><td>${esc(S(h.version_name))}</td><td>${esc(ago(h.at))}</td><td>${esc(S(h.design_note) || L(h.changed).slice(0, 4).join(', '))}${h.rollback_of ? ` · brought back build ${N(h.rollback_of)}` : ''}</td>
            <td>${N(h.build) !== N(a.build) && L(a.kept_builds).map(Number).includes(N(h.build)) && !BUILDING.includes(st) ? B('rollback', 'Roll back to this', 'sm', ` data-build="${N(h.build)}"`) : N(h.build) === N(a.build) ? pill('current', 'v') : ''}</td></tr>`).join('')}</table></div></div>` : ''}`);
    },
    async iphone(v) {
      const a = await api('GET', `/api/apps/${enc(v.id)}/ios`);
      const st = S(a.status), qa = M(a.qa), run = M(a.runner), tf = M(a.testflight), act = M(v.activity);
      if (!v.approved && !st) return P(head('iPhone app', '', 'Built in SwiftUI from the approved design') + emptyNote('The iPhone app is built from the approved design, like Android. Tap <b>Approve design</b> on Screens first.') + `<div>${B('to-screens', 'Go to Screens')}</div>`);
      const iosSteps = S(act.job) === 'ios' ? L(act.steps) : [];
      return P(`${head(`iPhone app${N(a.build) ? ` · build ${N(a.build)}` : ''}`, BUILDING.includes(st) ? pill('Building', 'v') : st === 'ready' ? pill(qa.ran && qa.passed ? 'Simulator check passed' : 'Ready', 'ok') : st === 'failed' ? pill('Needs attention', 'bad') : '', 'Built in SwiftUI from the same design, with the same accounts and orders as Android')}
        ${run.ready === false ? `<div class="callout">${esc(iosWhy(run.why))} Until then Hoola makes the Xcode project for you to open on a Mac.</div>` : ''}
        ${S(a.error) ? `<div class="callout bad">${esc(S(a.error))}</div>` : ''}
        ${iosSteps.length ? `<div class="panel">${ph('Steps')}${stepList({steps: iosSteps})}</div>` : ''}
        <div class="col2"><div class="panel">${ph('Build and check')}<span class="sm">Every screen is opened in an iPhone simulator before you get it.</span>
          ${qa.ran ? `<div class="as-row">${pill(`${N(qa.opened)}/${N(qa.total)} screens`, N(qa.opened) === N(qa.total) ? 'ok' : 'warn')}${pill(`${L(qa.crashed).length} crashes`, L(qa.crashed).length ? 'bad' : 'ok')}</div>` : ''}
          ${tf.version ? `<span class="sm">TestFlight: version ${esc(S(tf.version))} (${esc(S(tf.build))}) · ${esc(ago(tf.at))}</span>` : ''}
          <div class="as-row">${a.zip_url ? `<a class="b" href="${esc(S(a.zip_url))}" target="_blank" rel="noopener noreferrer">${ico('code', 15)}Xcode project</a>` : ''}
            ${!BUILDING.includes(st) && v.approved ? B('ios', `${ico(N(a.build) ? 'reload' : 'phone', 15)}${N(a.build) ? 'Build again' : 'Build the iPhone app'}`, N(a.build) ? '' : 'pri') : ''}
            ${!BUILDING.includes(st) && v.approved && run.ready !== false ? B('testflight', 'Send to TestFlight…') : ''}</div>
          <div class="callout mt">TestFlight uses your App Store Connect key, kept as a secret in your own GitHub builds repo. Never type it in chat.</div></div>
          ${L(qa.shots).length ? `<div class="panel" style="align-items:center"><div class="as-row" style="gap:12px">${L(qa.shots).slice(0, 3).map(sid => phone(`/api/apps/${enc(v.id)}/ios/qa/${enc(sid)}`, sid)).join('')}</div><span class="mut sm">iPhone simulator · build ${N(qa.build)}</span></div>` : ''}</div>`);
    },
    async store(v) {
      const [p, a] = await Promise.allSettled([api('GET', `/api/apps/${enc(v.id)}/store`), api('GET', `/api/apps/${enc(v.id)}/appstore`)]);
      const g = p.status === 'fulfilled' ? p.value : {}, s = a.status === 'fulfilled' ? a.value : {};
      const gs = L(g.steps), done = gs.filter(x => x.done).length, ls = M(g.listing);
      const step = (x, i) => `<div><span class="n ${x.done ? 'ok' : ''}">${x.done ? '✓' : i + 1}</span><span style="flex:1">${esc(S(x.label))}${x.value ? ` <span class="mut">· ${esc(S(x.value))}</span>` : ''}</span></div>`;
      return P(`${head('Publish to the stores', '', 'Every step is listed. Production and review go out only when you tap and confirm.')}
        <div class="col2"><div class="panel">${ph(`<span class="sto g" aria-hidden="true">▶</span>Google Play`, gs.length ? pill(`${done} of ${gs.length} done`, done === gs.length ? 'ok' : 'v') : '')}
          ${p.status === 'rejected' ? `<div class="callout bad">${esc(p.reason.message)}</div>` : `<div class="steps8">${gs.map(step).join('')}</div>`}
          ${S(g.error) ? `<div class="callout bad">${esc(S(g.error))}</div>` : ''}${S(g.now) ? `<span class="mut sm"><span class="spin" aria-hidden="true" style="display:inline-block;vertical-align:middle"></span> ${esc(S(g.now))}</span>` : ''}
          <div class="acts2">${B('store-listing', ls.title ? 'Rewrite the listing' : 'Write the listing')}${B('store-build', 'Make the Play bundle (.aab)')}${B('store-internal', 'Internal testing')}</div>
          <div class="as-row">${B('store-production', `${ico('lock', 14)}Release to production…`, 'pri')}</div>
          ${gs.length && !(gs.find(x => S(x.id) === 'account') || {}).done ? `<form class="as-form linkbox" data-form="playkey"><b>Link your Play developer account</b>
            <span class="mut sm">In Google Play Console make a service account with release rights and download its key (a JSON file). Choose it here: it is sealed on the server and shown to no one, Hoola included. Never paste it in chat.</span>
            <div class="fpick"><label class="b">${ico('dl', 14)}Choose the key file<input type="file" name="key" accept="application/json,.json" required class="sr" data-fpick></label><span class="fname mut sm">No file chosen</span>
            <button class="b dark" type="submit">Link account</button></div></form>` : ''}
          <span class="mut sm">Security checks must pass before production.</span></div>
        <div class="panel">${ph(`<span class="sto a" aria-hidden="true"></span>App Store`, S(s.status) ? pill(S(s.status).replace(/_/g, ' '), S(s.status) === 'in_review' ? 'v' : '') : '')}
          ${a.status === 'rejected' ? `<div class="callout bad">${esc(a.reason.message)}</div>` : `<div class="steps8">${L(s.steps).map(step).join('')}</div>`}
          ${S(s.error) ? `<div class="callout bad">${esc(S(s.error))}</div>` : ''}
          <div class="acts2">${B('as-listing', 'Write the listing')}${B('as-push', 'Push listing + screenshots')}</div><div class="as-row">${B('as-submit', `${ico('lock', 14)}Submit for review…`, 'pri')}</div></div></div>
        ${ls.title ? `<div class="panel">${ph('Play listing')}<div class="as-row top" style="gap:18px"><div style="width:64px;height:64px;border-radius:16px;background:${tint(v.id)};flex:none"></div>
          <div style="flex:1;display:flex;flex-direction:column;gap:4px;min-width:0"><b style="font-size:16px">${esc(S(ls.title))}</b><span class="mut sm">${esc(S(ls.short))}</span><span class="sm" style="white-space:pre-wrap">${esc(S(ls.full).slice(0, 600))}${S(ls.full).length > 600 ? '…' : ''}</span></div></div></div>` : ''}
        ${L(g.releases).length ? `<div class="panel">${ph('Releases')}<div class="tscroll"><table class="t"><tr><th>Track</th><th>Version</th><th>Status</th><th>When</th></tr>${L(g.releases).map(r => `<tr><td>${esc(S(r.track))}</td><td>${esc(S(r.version_name))} (${esc(S(r.version_code))})</td><td>${esc(S(r.status))}</td><td>${esc(ago(r.at))}</td></tr>`).join('')}</table></div></div>` : ''}`);
    },
    async data(v) {
      const d = await api('GET', `/api/apps/${enc(v.id)}/data`);
      const cols = L(d.collections);
      if (!cols.length) return P(head('Data', '', 'The lists your app keeps') + emptyNote('This app keeps no lists yet. They appear here when the app is built.'));
      const key = cols.some(c => S(c.key) === DATA.coll) ? DATA.coll : S(cols[0].key);
      DATA.coll = key;
      const col = cols.find(c => S(c.key) === key) || {}, fields = L(col.fields).filter(f => !f.hidden).slice(0, 7);
      const [rows, mem] = await Promise.allSettled([api('GET', `/api/apps/${enc(v.id)}/data/${enc(key)}`), api('GET', `/api/apps/${enc(v.id)}/members`)]);
      const rs = rows.status === 'fulfilled' ? L(rows.value.rows) : [], ms = mem.status === 'fulfilled' ? L(mem.value.members) : [];
      return P(`${head('Data', `<div class="seg" role="group" aria-label="List">${cols.slice(0, 8).map(c => `<button type="button" data-coll="${esc(S(c.key))}" aria-pressed="${S(c.key) === key}">${esc(S(c.label))}<span class="cnt">${N(M(d.counts)[c.key])}</span></button>`).join('')}</div>`,
          d.live ? '<span class="livedot" aria-hidden="true"></span>Live · what customers add in the app shows here' : 'The app is not live yet: these lists fill once people use a built app')}
        <div class="panel flush"><div class="tscroll"><table class="t"><tr>${fields.map(f => `<th>${esc(S(f.label))}</th>`).join('')}<th>Added</th></tr>
          ${rs.length ? rs.slice(0, 100).map(r => `<tr>${fields.map(f => `<td>${esc(S(r[f.key]).slice(0, 120))}</td>`).join('')}<td>${esc(ago(r.created))}</td></tr>`).join('') : `<tr><td colspan="${fields.length + 1}" class="tempty">Nothing in ${esc(S(col.label))} yet.</td></tr>`}</table></div></div>
        <div class="col2"><div class="panel">${ph(`Members and roles <span class="cnt">${ms.length}</span>`)}${ms.length ? `<div class="tscroll"><table class="t"><tr><th>Name</th><th>Since</th><th>Role</th></tr>${ms.slice(0, 50).map(m => `<tr><td>${esc(S(m.name) || S(m.email) || S(m.phone))}</td><td>${esc(ago(m.since))}</td>
            <td><select data-role="${esc(S(m.id))}" aria-label="Role of ${esc(S(m.name))}">${['member', 'staff', 'admin'].map(r => `<option value="${r}"${S(m.role) === r ? ' selected' : ''}>${r === 'member' ? 'Customer' : r === 'staff' ? 'Staff' : 'Admin'}</option>`).join('')}</select></td></tr>`).join('')}</table></div>` : '<span class="mut sm">No one has an account yet.</span>'}</div>
          <div class="panel">${ph('Change what a list keeps')}<span class="mut sm">Say it in the chat, e.g. "add a gift wrap field to orders". Only safe changes (add, hide, rename); old rows keep working.</span>${d.api ? `<span class="kvline"><span class="mut sm">App backend</span><code>${esc(S(d.api))}</code></span>` : ''}</div></div>`);
    },
    async business(v) {
      const base = `/api/apps/${enc(v.id)}`;
      const keys = ['hisaab', 'stock', 'coupons', 'khata-yaad', 'delivery', 'gst', 'pay', 'logic', 'usage'];
      const res = await Promise.allSettled(keys.map(k => api('GET', `${base}/${k}`)));
      const R = Object.fromEntries(keys.map((k, i) => [k, res[i].status === 'fulfilled' ? res[i].value : null]));
      const h = M(M(R.hisaab).summary), st = M(R.stock), cp = M(R.coupons), kh = M(R['khata-yaad']), dl = M(R.delivery), gst = M(R.gst), pay = M(R.pay), lg = M(R.logic), us = M(R.usage);
      const due = L(kh.customers).reduce((a, c) => a + N(c.balance), 0);
      const lows = st.tracked ? L(st.products).filter(p => p.qty != null && (p.low || p.sold_out)) : [], low = lows.length;
      const mod = (title, ic, on, line, note, ask) => `<div class="mod${on ? ' on' : ''}"><div class="modh"><span class="mi" aria-hidden="true">${ico(ic, 16)}</span><b>${esc(title)}</b>${pill(on ? 'On' : 'Off', on ? 'ok' : '')}</div><span class="ml">${esc(line)}</span><span class="mut sm">${esc(note)}</span>${ask ? `<button class="b sm" type="button" data-ask="${esc(ask)}">${on ? 'Change' : 'Turn on'}</button>` : ''}</div>`;
      return P(`${head('Business', '', 'Everything your app runs on. Changes go through Hoola in the chat.')}
        <div class="col3"><div class="stat"><span class="k">Sales this month</span><span class="v2">${inr(h.sales)}</span><span class="mut sm">${plural(h.orders, 'order')}</span></div>
          <div class="stat"><span class="k">Credit (udhaar) due</span><span class="v2">${inr(due)}</span><span class="mut sm">${plural(L(kh.customers).length, 'customer')}</span></div>
          <div class="stat"><span class="k">Month file for your CA</span><span class="as-row">${B('hisaab-zip', `${ico('dl', 14)}Sales, GST + khata ZIP`, 'sm')}</span><span class="mut sm">${esc(S(M(R.hisaab).month))}</span></div></div>
        <div class="mods">
          ${mod('Payments', 'card', !!pay.on, pay.on ? `${S(pay.gateway) || 'Gateway'} · ${L(pay.payments).length} payments` : 'UPI to your own UPI ID', 'Paid only from the gateway\'s signed message; refunds are your tap.', pay.on ? 'Change the payment settings of this app' : 'Add online payments to this app with my own Razorpay')}
          ${mod('GST bills', 'doc', !!gst.on, gst.on ? `GSTIN ${S(gst.gstin)} · ${N(gst.issued)} invoices` : 'Not set up', 'Tax invoices for finished orders, on your own series.', gst.on ? '' : 'Turn on GST bills for this app')}
          ${mod('Khata (udhaar)', 'book', L(kh.customers).length > 0, `${inr(due)} due from ${plural(L(kh.customers).length, 'customer')}`, 'Reminders go only when you send them.', '')}
          ${mod('Stock', 'box', !!st.tracked, st.tracked ? `${N(st.tracked)} items tracked · ${low} low or sold out` : 'Not tracked: every item can always be ordered', 'Orders never oversell.', st.tracked ? '' : 'Track stock for the products in this app')}
          ${mod('Coupons', 'tag', L(cp.coupons).length > 0, L(cp.coupons).filter(c => c.live).map(c => S(c.code)).join(', ') || 'No coupon live', 'Checked and applied by the server.', 'Add a coupon to this app')}
          ${mod('Delivery', 'truck', !!dl.on, dl.on ? `Fee ${inr(dl.fee)}${dl.free_above ? ` · free above ${inr(dl.free_above)}` : ''} · ${L(dl.slots).length} slots` : 'Not set up', 'Holidays and slot limits honoured.', dl.on ? 'Change delivery settings of this app' : 'Add delivery fee and time slots to this app')}
          ${mod('Business rules', 'rule', !!lg.has_logic, lg.has_logic ? `${L(lg.summary).length} rules · ${L(lg.approvals).length} approvals waiting` : 'No rules yet', 'Every rule is tested both ways before it runs.', 'Add a business rule to this app')}
          ${mod('Usage', 'chart', true, `${plural(us.rows, 'row')} · ${plural(us.accounts, 'account')}`, `${N(us.percent)}% of the plan's limit`, '')}
        </div>
        ${lows.length ? `<div class="panel">${ph('Low stock')}<div class="chipset">${lows.slice(0, 20).map(p => `<span>${esc(S(p.name))} · ${p.sold_out ? 'sold out' : N(p.qty)}</span>`).join('')}</div></div>` : ''}`);
    },
    async health(v) {
      const base = `/api/apps/${enc(v.id)}`;
      const [o, c, r, j] = await Promise.allSettled([api('GET', `${base}/ops?days=7`), api('GET', `${base}/crashes`), api('GET', `${base}/rollout`), api('GET', `${base}/jaanch`)]);
      const ops = o.status === 'fulfilled' ? o.value : {}, cr = c.status === 'fulfilled' ? L(c.value.crashes) : [], ro = r.status === 'fulfilled' ? r.value : {}, ja = j.status === 'fulfilled' ? j.value : {};
      const tr = M(ops.traffic), cost = M(ops.cost), roll = M(ro.rollout), stages = L(ro.stages).length ? L(ro.stages) : [0.05, 0.2, 0.5, 1];
      const frac = N(roll.fraction), pct = x => Math.round(N(x) * 100) + '%';
      return P(`${head('Health', '', 'How the live app is doing for your customers')}
        <div class="col3"><div class="stat"><span class="k">Answers in (p95)</span><span class="v2">${esc(S(tr.p95) || '—')}</span><span class="mut sm">a band, last 7 days</span></div>
          <div class="stat"><span class="k">Failing calls</span><span class="v2">${tr.calls ? N(tr.error_percent).toFixed(1) + '%' : '—'}</span><span class="mut sm">${plural(tr.calls, 'call')}</span></div>
          <div class="stat"><span class="k">AI cost (30 days)</span><span class="v2">${inr(cost.inr)}</span><span class="mut sm">${L(cost.not_priced).length ? esc(L(cost.not_priced).join(', ')) + ' not priced' : 'all priced'}</span></div></div>
        ${L(ops.alerts).length ? L(ops.alerts).map(a => `<div class="callout${S(a.level) === 'bad' ? ' bad' : ''}">${esc(S(a.say))}</div>`).join('') : ''}
        <div class="col2"><div class="panel">${ph("Crashes from customers' phones", cr.filter(x => S(x.status) === 'new' || S(x.status) === 'back').length ? pill(`${cr.filter(x => S(x.status) === 'new' || S(x.status) === 'back').length} new`, 'bad') : pill('None open', 'ok'))}
          ${cr.length ? `<div class="tscroll"><table class="t"><tr><th>What</th><th>Times</th><th>Last</th><th></th></tr>${cr.slice(0, 12).map(x => `<tr><td><b>${S(x.kind) === 'anr' ? 'Froze' : S(x.kind) === 'native' ? 'Native crash' : 'Crash'}</b> · ${esc(L(x.screens).join(', ') || '')} ${esc(S(x.exception).slice(0, 80))}</td><td>${N(x.count)}</td><td>${esc(ago(x.last))}</td>
            <td>${S(x.status) === 'fixing' ? pill('fixing') : B('fix-crash', 'Fix it', 'sm pri', ` data-crash="${esc(S(x.id))}"`)}</td></tr>`).join('')}</table></div>` : '<span class="mut sm">No crash reported from any phone.</span>'}</div>
          <div class="panel">${ph('Release to customers (Play)')}
            ${roll.version_name ? `<span class="sm">Version ${esc(S(roll.version_name))} · ${esc(S(roll.status))}</span><div class="roll">${stages.map(s => `<span class="${N(s) < frac || (N(s) === frac && S(roll.status) === 'completed') ? 'done' : N(s) === frac ? 'on' : ''}">${pct(s)}</span>`).join('')}</div>
              <div class="as-row">${frac < 1 && S(roll.status) !== 'halted' ? B('roll-advance', `Go to ${pct(stages.find(s => N(s) > frac) || 1)}…`, 'pri') : ''}${S(roll.status) === 'inProgress' ? B('roll-halt', 'Halt', 'bad') : ''}${ro.can_rollback ? B('roll-back', 'Roll back…') : ''}</div>`
              : `<span class="mut sm">Nothing is rolling out. Start a staged release once a version is on Play.</span><div class="as-row">${B('roll-start', 'Start at 5%…')}</div>`}
            <span class="mut sm">Each step is your tap. Halt needs no tap. Play cannot take a version back from phones that already have it.</span></div></div>
        <div class="col2"><div class="panel">${ph('Feature switches')}${L(ro.flags).length ? `<table class="t">${L(ro.flags).map(f => `<tr><td>${esc(S(f.label) || S(f.key))}</td><td>${pill(f.on ? (N(f.percent) && N(f.percent) < 100 ? `On for ${N(f.percent)}%` : 'On') : 'Off', f.on ? 'ok' : '')}</td><td>${B('flag', f.on ? 'Turn off' : 'Turn on', 'sm', ` data-key="${esc(S(f.key))}" data-on="${f.on ? 0 : 1}"`)}</td></tr>`).join('')}</table>` : '<span class="mut sm">No switch yet. Ask in the chat: "show the new checkout to 10% of people".</span>'}
            <span class="mut sm">Switched on the server: works in minutes, no new app needed.</span></div>
          <div class="panel">${ph('Tested on a hidden copy of your app', M(ja.last_run).says ? pill(plural(ja.scenarios, 'story', 'stories'), 'v') : '')}
            <span class="sm">${esc(S(M(ja.last_run).says) || S(ja.says) || 'No test run yet.')}</span><div>${B('jaanch-run', 'Run every test', 'sm')}</div></div></div>`);
    },
    async settings(v) {
      const base = `/api/apps/${enc(v.id)}`;
      const [sg, bh, gh] = await Promise.allSettled([api('GET', `${base}/sign`), api('GET', `${base}/bhasha`), api('GET', `${base}/github`)]);
      const s = sg.status === 'fulfilled' ? sg.value : {}, b = bh.status === 'fulfilled' ? bh.value : {}, g = gh.status === 'fulfilled' ? gh.value : {};
      const f = M(v.facts);
      const WAYS = {email_password: 'Email + password', phone_otp: 'Mobile OTP', google: 'Google', apple: 'Apple'};
      return P(`${head('Settings', '', 'The details inside your app, its login, languages and code')}
        <div class="col2"><form class="panel as-form" data-form="facts">${ph('App details')}<span class="mut sm">Used inside the app (contact, payments). Prices and numbers are never invented: a blank stays blank until you fill it.</span>
          ${[['name', 'Name'], ['tagline', 'Tagline'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'], ['address', 'Address'], ['hours', 'Opening hours'], ['upi_id', 'UPI ID']].map(([k, n]) => `<label>${n}<input name="${k}" maxlength="200" value="${esc(S(f[k]))}" placeholder="${k === 'tagline' || k === 'hours' ? 'Blank until you fill it' : ''}"></label>`).join('')}
          <div class="as-row"><button class="b pri" type="submit">${ico('check', 15)}Save details</button></div></form>
        <div class="stack"><div class="panel">${ph('Login')}<div class="chipset">${L(s.ways).map(w => `<span>${esc(WAYS[S(w)] || S(w))}</span>`).join('') || '<span>Not set yet</span>'}${s.staff_2fa ? '<span>Staff 2-step code</span>' : ''}</div>
            ${Object.values(M(s.problems)).map(t => `<span class="mut sm">${esc(S(t))}</span>`).join('')}<span class="mut sm">Google and Apple sign-in are checked on the server.</span></div>
          <div class="panel">${ph('Languages')}<div class="chipset">${L(b.langs).map(l => `<span>${esc(LANG[S(l).toLowerCase()] || S(l))}</span>`).join('') || '<span>English</span>'}</div><span class="mut sm">Add one in the chat: "add Hindi and Marathi".</span></div>
          <div class="panel">${ph('Your code')}<span class="sm">${g.linked ? `Linked to ${esc(S(g.repo))} · ${N(g.exports)} exports` : 'Send the whole Android + iPhone code to your own GitHub. One commit per build.'}</span><div>${B('github', `${ico('code', 15)}Send to my GitHub…`)}</div></div>
          <div class="panel danger">${ph('Danger zone')}<span class="mut sm">Deleting removes the app, its design and its data on Hoola. Apps already on phones keep working until their backend is gone.</span><div>${B('delete', 'Delete this app…', 'bad')}</div></div></div></div>`);
    },
    async history(v) {
      const vs = L(v.versions);
      return P(`${head('History', '', 'Every design change is kept as a version')}
        ${vs.length ? `<div class="panel flush"><table class="t"><tr><th>Version</th><th>When</th><th>What changed</th><th>Checks</th></tr>${vs.map(x => `<tr><td>v${N(x.version)}</td><td>${esc(ago(x.at))}</td><td>${esc(S(x.note))}</td><td>${x.passed ? pill('passed', 'ok') : x.passed === false ? pill('notes', 'warn') : ''}</td></tr>`).join('')}</table></div>` : emptyNote('No version yet. The first one is saved when every screen is designed.')}
        ${v.approved_at ? `<span class="mut sm">Design approved ${esc(ago(v.approved_at))}.</span>` : ''}`);
    },
  };
  const DATA = {coll: ''};

  /* ---------- the live work card (the server's own timed steps) ---------- */
  let CLOCK = 0, TICK = null;
  const nowS = () => Date.now() / 1000 + CLOCK;
  const dur = s => { s = Math.max(0, Math.round(s)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s` : `${Math.floor(s / 3600)}h ${String(Math.floor(s / 60) % 60).padStart(2, '0')}m`; };
  const ACTV = v => { const a = M(v && v.activity); if (a.now) CLOCK = Number(a.now) - Date.now() / 1000; return a; };
  function stepRow(x) {
    const run = x.state === 'run', bad = x.state === 'error';
    const ic = run ? '<span class="spin" aria-hidden="true"></span>' : bad ? '<span class="xmark" aria-hidden="true">!</span>' : tick;
    const cnt = N(x.total) ? `<span class="cnt">${N(x.done)}/${N(x.total)}</span>` : '';
    const t = run ? `<span class="tm" data-t0="${N(x.at)}"></span>` : N(x.at) && N(x.end) - N(x.at) >= 1 ? `<span class="tm">${dur(N(x.end) - N(x.at))}</span>` : '<span class="tm"></span>';
    return `<li class="${run ? 'run' : bad ? 'bad' : 'ok'}">${ic}<div class="sl"><span class="ell">${esc(S(x.label))}</span>${x.note ? `<span class="sn ell">${esc(S(x.note))}</span>` : ''}</div>${cnt}${t}</li>`;
  }
  function stepList(a, last) {
    const st = L(a.steps).filter(x => !x.final || x.state === 'error');
    return `<ol class="acts" aria-label="What Hoola is doing">${(last ? st.slice(-last) : st).map(stepRow).join('')}</ol>`;
  }
  function tickClocks() { APP.querySelectorAll('[data-t0]').forEach(e => { const t0 = Number(e.dataset.t0); if (t0) e.textContent = dur(nowS() - t0); }); }
  function startTick() { if (!TICK) TICK = setInterval(tickClocks, 1000); tickClocks(); }
  function jobTitle(v) {
    if (BUILDING.includes(anSt(v))) return 'Building the Android app';
    if (BUILDING.includes(iosSt(v))) return 'Building the iPhone app';
    if (S(v.status) === 'looks') return 'Drawing three looks';
    if (S(v.status) === 'checking') return 'Checking every screen';
    return N(v.version) ? 'Updating your app' : 'Designing your app';
  }
  function drawState() {
    const box = $('#asState'); if (!box || !CUR) return;
    const v = CUR, a = ACTV(v), st = L(a.steps);
    if (WORKING(v)) {
      const cur = [...st].reverse().find(x => x.state === 'run');
      const stepPct = cur && N(cur.total) ? Math.round(100 * N(cur.done) / N(cur.total)) : null;
      const pct = DESIGNING(v) && N(M(v.board).pct) ? Math.max(3, Math.min(100, N(M(v.board).pct))) : stepPct;
      const last = st.filter(x => !x.final).slice(-1)[0];
      const sub = cur ? `Step ${st.indexOf(cur) + 1}${stepPct !== null ? ` · ${stepPct}% of this step` : ''} · ${S(cur.label)}` : last ? `After: ${S(last.label)}` : 'Starting…';
      box.innerHTML = `<div class="chatact wcard"><div class="step whead"><span class="spin" aria-hidden="true"></span><span class="wt"><b>${esc(jobTitle(v))}</b><span>${esc(sub)}</span></span>
          ${a.started ? `<span class="tm" data-t0="${N(a.started)}"></span>` : ''}</div>
        <div class="prog${pct === null ? ' ind' : ''}" role="progressbar" aria-label="Progress"${pct === null ? '' : ` aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"`}><i style="width:${pct === null ? 30 : pct}%"></i></div>
        ${st.length ? stepList(a, 6) : ''}
        ${st.length > 6 ? `<details class="actd"><summary>All ${st.length} steps so far</summary>${stepList(a)}</details>` : ''}
        <div class="wfoot"><span class="ell">You can keep chatting; changes wait for this job</span><span class="sp"></span>
          ${DESIGNING(v) ? `<button class="b sm" type="button" data-act="stop">${ico('pause', 14)}Pause</button>` : ''}</div></div>`;
    } else if (st.length && a.ended) {
      const ok = !st.some(x => x.state === 'error');
      const fresh = nowS() - N(a.ended) < 3600;
      const ready = ok && fresh && S(v.status) === 'ready' && N(v.version);
      box.innerHTML = `<details class="actd done"><summary>${ok ? tick : '<span class="xmark" aria-hidden="true">!</span>'}<span><b>${ok ? 'Worked' : 'Stopped'} for ${dur(N(a.ended) - N(a.started))} · ${st.filter(x => !x.final).length} steps</b></span><span class="chev" aria-hidden="true">${ico('chev', 14)}</span></summary>${stepList(a)}</details>
        ${ready ? `<div class="vcard"><span class="vth" aria-hidden="true"></span><span class="vt"><b>Version ${N(v.version)} is ready</b><span>${M(v.checks).passed ? 'Every check passed · ' : ''}tap through it or approve it</span></span>
          <button class="b dark sm" type="button" data-view="prototype">${ico('phone', 14)}Try it</button></div>
          <div class="sugg"><span>Next, you could</span>${['Add a khata (udhaar) screen', 'Add online payments', 'Add Hindi'].map(t => `<button type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}`;
    } else box.innerHTML = '';
    drawTop();
    startTick();
  }

  /* ---------- polling while the server works ---------- */
  const sig = v => [v.status, v.version, M(v.board).pct, M(v.board).now, M(v.board).done, L(v.looks).length, anSt(v), iosSt(v), M(M(v.builds).android).build, v.approved, v.error, L(M(v.activity).steps).length].join('|');
  function startPoll() {
    stopPoll(); SIG = sig(CUR);
    const id = CUR.id;
    POLL = setTimeout(async () => {
      POLL = null;
      if (!CUR || CUR.id !== id) return;
      try {
        const v = await api('GET', `/api/apps/${enc(id)}`);
        if (!CUR || CUR.id !== id) return;
        const changed = sig(v) !== SIG; CUR = v;
        drawState();
        if (changed && !['data', 'settings', 'business'].includes(VIEW)) drawPane();
      } catch {}
      startPoll();
    }, WORKING(CUR) ? 2000 : 8000);
  }
  function stopPoll() { if (POLL) { clearTimeout(POLL); POLL = null; } }
  async function reload() { if (!CUR) return; try { CUR = await api('GET', `/api/apps/${enc(CUR.id)}`); drawState(); drawPane(); startPoll(); } catch (e) { toast(e.message, true); } }

  /* ---------- the app's own Hoola thread (never the home chat) ---------- */
  async function ensureConv() {
    if (THREAD.conv && THREAD.app === CUR.id) return THREAD.conv;
    THREAD.app = CUR.id;
    let c = store.get(convKey(CUR.id));
    if (c) { try { await api('GET', `/api/conversations/${enc(c)}/messages?limit=1`); } catch { c = ''; } }
    if (!c) { c = await newConv(`App · ${name(CUR)}`); store.set(convKey(CUR.id), c); }
    THREAD.conv = c;
    return c;
  }
  async function openThread() {
    clearTimeout(THREAD.timer);
    Object.assign(THREAD, {app: CUR.id, conv: store.get(convKey(CUR.id)), rows: [], live: '', sig: '', waiting: false, since: 0, steps: [], stepsRead: false, startedS: 0});
    drawMsgs();
    if (THREAD.conv) await readThread();
  }
  const clean = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  const tsec = a => { const t = S(a); if (!t) return 0; const ms = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? t : t + 'Z'); return isNaN(ms) ? 0 : ms / 1000; };
  async function readSteps(c) {
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/timeline?limit=200&steps=1`);
      const by = new Map();
      for (const ev of L(r.events)) {
        if (ev.kind !== 'step') continue;
        const pl = M(ev.payload), k = S(pl.id) || ('e' + ev.id), at = tsec(ev.at), upd = tsec(ev.updated_at) || at;
        const x = by.get(k) || {label: S(pl.label) || S(pl.tool), at, state: 'run'};
        x.at = Math.min(x.at || at, at);
        if (pl.state !== 'running') { x.state = pl.state === 'error' ? 'error' : 'done'; x.end = Math.max(x.end || 0, upd); }
        if (pl.label) x.label = S(pl.label);
        by.set(k, x);
      }
      THREAD.steps = [...by.values()].filter(x => x.at).sort((a, b) => a.at - b.at);
    } catch {}
  }
  const stepsBetween = (a, b) => L(THREAD.steps).filter(x => x.at >= a - 2 && (!b || x.at <= b + 2));
  const md = t => window.HoolaMD ? window.HoolaMD.render(t, false) : `<p>${esc(t)}</p>`;
  function drawMsgs() {
    const box = $('#asMsgs'); if (!box) return;
    const all = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
    const first = all.findIndex(r => r.role === 'user');
    const rows = first < 0 ? [] : all.slice(first);
    const st = L(THREAD.steps), lastSt = st[st.length - 1] || {};
    const s = rows.map(r => r.id).join(',') + '|' + THREAD.live.length + '|' + THREAD.waiting + '|' + st.length + lastSt.state + (lastSt.end || '');
    if (s === THREAD.sig) return;
    THREAD.sig = s;
    const near = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    const shown = rows.slice(-40);
    let lastUser = 0;
    const who = t => `<div class="who"><span class="hm" aria-hidden="true"></span><b>Hoola</b>${t ? `<span>${esc(clockOf(t))}</span>` : ''}</div>`;
    const html = shown.map(r => {
      if (r.role === 'user') { lastUser = tsec(r.at) || lastUser; return `<div class="me">${esc(clean(r.text))}</div>`; }
      const end = tsec(r.at), steps = lastUser && end ? stepsBetween(lastUser, end) : [];
      const took = lastUser && end > lastUser ? end - lastUser : 0;
      const hd = steps.length || took >= 3 ? `<details class="actd turnw"><summary>Worked for ${dur(took)}${steps.length ? ` · ${steps.length} step${steps.length > 1 ? 's' : ''}` : ''}</summary>${steps.length ? stepList({steps}) : ''}</details>` : '';
      return hd + who(end) + `<div class="ho">${md(S(r.text))}</div>`;
    }).join('');
    const since = THREAD.startedS || lastUser || nowS();
    const live = THREAD.waiting ? (() => {
      const steps = stepsBetween(since);
      return `<div class="working wcard" aria-live="polite"><div class="step whead"><span class="spin" aria-hidden="true"></span><span class="wt"><b>${steps.length ? `Working · step ${steps.length}` : 'Hoola is working'}</b><span>${esc(S(steps[steps.length - 1]?.label) || 'Reading your ask')}</span></span><span class="tm" data-t0="${since}"></span></div>
        ${steps.length ? stepList({steps}) : ''}</div>${THREAD.live ? who(0) + `<div class="ho">${md(THREAD.live)}</div>` : ''}`;
    })() : '';
    box.innerHTML = rows.length || THREAD.waiting ? html + live
      : `${S(CUR?.brief).trim() ? `<div class="me">${esc(clean(S(CUR.brief)))}</div>` : ''}${who(0)}<div class="ho"><p>${esc(S(CUR?.say) || 'Ask for anything in this app.')}</p></div>
         <div class="mut sm">This chat is only about ${esc(name(CUR || {}))}. It stays here, not in your home chat.</div>
         ${N(CUR?.version) ? '' : `<div style="display:flex;flex-wrap:wrap;gap:6px">`}${N(CUR?.version) ? '' : ['Make the colours warmer', 'Add a khata (udhaar) screen', 'Add online payments', 'Add Hindi'].map(t => `<button class="chip" type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('') + '</div>'}`;
    if (near || THREAD.waiting) box.scrollTop = box.scrollHeight;
    if (THREAD.waiting) startTick();
  }
  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;
      THREAD.rows = L(r.messages);
    } catch { return; }
    if (!THREAD.waiting) {
      const talk = THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
      const last = talk[talk.length - 1];
      if (last && last.role === 'user' && nowS() - tsec(last.at) < 900) {
        THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = tsec(last.at);
        THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      }
    }
    if (THREAD.waiting || !THREAD.stepsRead) { await readSteps(c); THREAD.stepsRead = true; if (c !== THREAD.conv) return; }
    if (THREAD.waiting) {
      let snap = null;
      try { const res = await api('GET', `/api/conversations/${enc(c)}/live`, undefined, {raw: true}); if (res.status === 200) snap = await res.json(); } catch {}
      THREAD.live = S(snap?.text);
      const talk = THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
      let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
      const answered = lu >= 0 && Number(talk[lu].id) > THREAD.since && talk.slice(lu + 1).some(m => m.role === 'assistant');
      if (answered && !snap) { THREAD.waiting = false; THREAD.live = ''; THREAD.startedS = 0; await readSteps(c); reload(); }
      else if (Date.now() - THREAD.started > 15 * 60e3) THREAD.waiting = false;
    }
    drawMsgs();
    if (THREAD.waiting) { clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 1500); }
  }
  async function ask(text) {
    text = S(text).trim(); if (!text || !CUR) return;
    const v = CUR, plan = store.get(MODE_KEY + '.chat') === 'plan';
    try {
      const c = await ensureConv();
      THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      THREAD.rows.push({id: 'local-' + Date.now(), role: 'user', text});
      THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = nowS(); THREAD.live = ''; drawMsgs();
      const hints = [`App Studio: this chat is only about app ${S(v.number)} "${name(v)}" (app id ${S(v.id)}). Work on THIS app with app_banao (app=${S(v.id)}; action=change for design changes) and its other tools; never start a new app unless I ask for one.`];
      if (plan) hints.push('Plan mode: reply with a short plan for this change (what changes, what stays the same, anything you need from me) and change NOTHING until I say Haan.');
      await api('POST', `/api/conversations/${enc(c)}/messages`, {text, client_id: 'as-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8), hints});
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 900);
    } catch (e) { THREAD.waiting = false; drawMsgs(); toast(e.message, true); }
  }

  /* ---------- small dialog ---------- */
  function dialog(title, inner) {
    return new Promise(resolve => {
      const d = document.createElement('dialog'); d.className = 'dlg';
      d.innerHTML = `<form method="dialog"><b style="font-size:16px">${esc(title)}</b>${inner}<div class="inl" style="justify-content:flex-end"><button class="b" value="cancel" type="submit">Cancel</button><button class="b pri" value="ok" type="submit">OK</button></div></form>`;
      document.body.appendChild(d);
      d.addEventListener('close', () => { const ok = d.returnValue === 'ok'; const fd = ok ? new FormData(d.querySelector('form')) : null; d.remove(); resolve(fd); });
      d.showModal();
    });
  }
  function zoom(src) {
    const d = document.createElement('dialog'); d.className = 'dlg';
    d.innerHTML = `<form method="dialog" style="align-items:center"><img class="zoomimg" alt="Screen"><button class="b" value="close" type="submit">Close</button></form>`;
    document.body.appendChild(d);
    const img = d.querySelector('img'); img.dataset.src = src; paintImgs(d);
    d.addEventListener('close', () => d.remove()); d.showModal();
  }

  /* ---------- actions ---------- */
  const base = () => `/api/apps/${enc(CUR.id)}`;
  async function post(path, body, ok) {
    const r = await api('POST', base() + path, {conversation_id: THREAD.conv || store.get(convKey(CUR.id)) || '', ...(body || {})});
    if (ok) toast(S(r?.say || r?.says) || ok);
    return r;
  }
  async function download(path, fallbackName) {
    const r = await api('GET', path, undefined, {raw: true});
    const cd = S(r.headers.get('content-disposition')), m = cd.match(/filename="?([^";]+)"?/i);
    const u = URL.createObjectURL(await r.blob()), a = document.createElement('a');
    a.href = u; a.download = m ? m[1] : fallbackName; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 30e3);
  }
  async function act(k, el) {
    if (!CUR) return;
    try {
      if (k === 'plan') { await post('/plan', {drop: [...DROP]}, 'Haan sent. Drawing three looks…'); VIEW = 'looks'; return reload(); }
      if (k === 'look') { await post('/look', {index: N(el.dataset.i)}, 'Designing every screen in this look…'); VIEW = 'screens'; return reload(); }
      if (k === 'approve') {
        if (!confirm('Design pakka?\n\nThis freezes the design for the real Android and iPhone app. You can still change it later; a change makes a new version to approve.')) return;
        await post('/approve', {hash: S(CUR.hash)}, 'Design approved.'); VIEW = 'android'; return reload();
      }
      if (k === 'stop') { await post('/stop', {}, 'Paused.'); return reload(); }
      if (k === 'to-screens') { VIEW = 'screens'; return drawPane(); }
      if (k === 'android') { await post('/android', {}, 'Android build started.'); return reload(); }
      if (k === 'rollback') {
        const b = N(el.dataset.build);
        if (!confirm(`Bring back build ${b}?\n\nIt is re-released as a new version, so it installs over the current one.`)) return;
        await post('/rollback', {build: b}, `Bringing back build ${b}…`); return reload();
      }
      if (k === 'ios') { await post('/ios', {kind: 'sim'}, 'iPhone build started.'); return reload(); }
      if (k === 'testflight') {
        if (!confirm('Send this app to TestFlight?\n\nIt is built on your Mac runner and uploaded with your own App Store Connect key. Nobody outside your testers sees it.')) return;
        await post('/ios', {kind: 'testflight'}, 'Sending to TestFlight…'); return reload();
      }
      if (k === 'store-listing') { await post('/store/listing', {regen: true}, 'Listing written.'); return drawPane(); }
      if (k === 'store-build') { await post('/store/build', {}, 'Making the Play bundle…'); return drawPane(); }
      if (k === 'store-internal') { await post('/store/publish', {track: 'internal'}, 'Sent to internal testing.'); return drawPane(); }
      if (k === 'store-production') {
        if (!confirm('Release to production on Google Play?\n\nEveryone on Play can install it once Google approves. The security checks run first and stop it if anything fails.')) return;
        await post('/store/publish', {track: 'production', her_tap: true}, 'Sent to Play production.'); return drawPane();
      }
      if (k === 'as-listing') { await post('/appstore/listing', {regen: true}, 'App Store listing written.'); return drawPane(); }
      if (k === 'as-push') { await post('/appstore/push', {}, 'Pushing to App Store Connect…'); return drawPane(); }
      if (k === 'as-submit') {
        if (!confirm('Submit this version for App Store review?\n\nApple reviews it; you release it from App Store Connect when it is approved.')) return;
        await post('/appstore/submit', {her_tap: true}, 'Submitted for review.'); return drawPane();
      }
      if (k === 'fix-crash') { await post('/fix_crash', {crash: S(el.dataset.crash)}, 'Fixing it in the next build…'); return reload(); }
      if (k === 'roll-start' || k === 'roll-advance' || k === 'roll-back') {
        const what = {'roll-start': 'start', 'roll-advance': 'advance', 'roll-back': 'rollback'}[k];
        const msg = {start: 'Start a staged release at 5% of Play users?', advance: 'Release to more Play users?', rollback: 'Roll back the release?\n\nPhones that already have the new version keep it; Play stops giving it to more people.'}[what];
        if (!confirm(msg)) return;
        await post('/rollout/' + what, {her_tap: true}, 'Done.'); return drawPane();
      }
      if (k === 'roll-halt') { await post('/rollout/halt', {why: 'halted from App Studio'}, 'Halted.'); return drawPane(); }
      if (k === 'flag') { await post('/rollout/flag', {key: S(el.dataset.key), on: el.dataset.on === '1'}, 'Switched.'); return drawPane(); }
      if (k === 'jaanch-run') { toast('Running every test on a hidden copy…'); await post('/jaanch/all', {}, 'Tests finished.'); return drawPane(); }
      if (k === 'hisaab-zip') { return await download(`${base()}/hisaab?download=1`, 'hisaab.zip'); }
      if (k === 'github') {
        const fd = await dialog('Send the code to your GitHub', `<label class="sm mut" for="asRepo">Repository (owner/name, new or yours)</label><input class="in" id="asRepo" name="repo" maxlength="120" placeholder="yourname/${esc(name(CUR).toLowerCase().replace(/[^a-z0-9]+/g, '-'))}">
          <label class="sm" style="display:flex;gap:8px;align-items:center"><input type="checkbox" name="private" checked> Private repository</label><p class="mut sm">Hoola shows you a card with exactly what goes; nothing is pushed until you tap it.</p>`);
        if (!fd) return;
        await post('/github', {repo: S(fd.get('repo')).trim(), private: fd.get('private') === 'on'}, 'Check the card in the chat to send it.'); return;
      }
      if (k === 'delete') return menuAct('delete', CUR);
    } catch (e) { toast(e.message, true); }
  }

  /* ---------- one listener for everything ---------- */
  APP.addEventListener('click', e => {
    const t = e.target.closest('[data-menu],[data-act],[data-view],[data-mode],[data-cmode],[data-ask],[data-fill],[data-drop],[data-plat],[data-dev],[data-coll],[data-idea],[data-zoom]');
    if (!t) return;
    if (t.dataset.menu) { e.preventDefault(); return openMenu(t, t.dataset.menu); }
    if (t.dataset.mode) { store.set(MODE_KEY, t.dataset.mode); APP.querySelectorAll('[data-mode]').forEach(b => b.setAttribute('aria-pressed', String(b === t)));
      const n = $('#asModeNote'); if (n) n.textContent = t.dataset.mode === 'plan' ? 'Plan: read the plan first, then say Haan' : 'Build: plan, then 3 looks'; return; }
    if (t.dataset.cmode) { store.set(MODE_KEY + '.chat', t.dataset.cmode); APP.querySelectorAll('[data-cmode]').forEach(b => b.setAttribute('aria-pressed', String(b === t))); return; }
    if (t.dataset.fill) { const a = $('#asAsk'); if (a) { a.value = t.dataset.fill; a.focus(); } return; }
    if (t.dataset.ask) { const box = $('#asTh'); if (box) { box.value = t.dataset.ask; box.focus(); } return; }
    if (t.dataset.idea) return void startApp({brief: S(t.dataset.ideaName), idea: t.dataset.idea});
    if (t.dataset.view) { e.preventDefault(); VIEW = t.dataset.view; history.replaceState(null, '', `#/app/${enc(S(CUR.id))}/${VIEW}`); return drawPane(); }
    if (t.dataset.drop) { const k = t.dataset.drop; if (DROP.has(k)) DROP.delete(k); else DROP.add(k); return drawPane(); }
    if (t.dataset.plat) { PLAT = t.dataset.plat; return drawPane(); }
    if (t.dataset.dev) { DEV = t.dataset.dev; return drawPane(); }
    if (t.dataset.coll) { DATA.coll = t.dataset.coll; return drawPane(); }
    if (t.dataset.zoom) return zoom(t.dataset.zoom);
    if (t.dataset.act === 'new') { if (location.hash !== '#/' && location.hash !== '') { PREFILL = ''; go('#/'); setTimeout(() => $('#asAsk')?.focus(), 80); } else $('#asAsk')?.focus(); return; }
    if (t.dataset.act === 'focus') return void $('#asAsk')?.focus();
    if (t.dataset.act === 'ideas-more') return loadIdeas(false);
    if (t.dataset.act) return act(t.dataset.act, t);
  });
  APP.addEventListener('submit', async e => {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form;
    if (kind === 'ask') { const txt = S($('#asAsk')?.value).trim(); if (txt) startApp({brief: txt}); return; }
    if (kind === 'thread') { const box = $('#asTh'), txt = S(box?.value).trim(); if (!txt) return; box.value = ''; return ask(txt); }
    if (kind === 'playkey') {
      const file = f.querySelector('input[type=file]')?.files?.[0]; if (!file) return;
      try {
        const txt = await file.text(); let json; try { json = JSON.parse(txt); } catch { return toast('That file is not a JSON key.', true); }
        if (S(json.type) !== 'service_account') return toast('That is not a service account key. Download the key of a service account from Google Cloud.', true);
        await api('POST', `${base()}/store/credentials`, {json: txt}); toast('Play account linked.'); drawPane();
      } catch (er) { toast(er.message, true); }
      return;
    }
    if (kind === 'answers' || kind === 'facts') {
      const answers = {}; new FormData(f).forEach((val, k) => { if (S(val).trim()) answers[k] = S(val).trim(); });
      if (!Object.keys(answers).length) return toast('Nothing to save.');
      try { CUR = await api('POST', `${base()}/answers`, {answers, conversation_id: THREAD.conv || ''}); toast('Saved.'); drawShell(); }
      catch (er) { toast(er.message, true); }
    }
  });
  APP.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && e.target.matches('#asAsk, #asTh')) { e.preventDefault(); e.target.closest('form')?.requestSubmit(); }
  });
  APP.addEventListener('change', async e => {
    const t = e.target;
    if (t.id === 'asIdeaAud') { IDEAS.aud = t.value; return loadIdeas(true); }
    if (t.matches('[data-fpick]')) { const n = t.closest('.fpick')?.querySelector('.fname'); if (n) n.textContent = t.files && t.files[0] ? t.files[0].name : 'No file chosen'; return; }
    if (t.dataset.role) {
      try { await api('POST', `${base()}/members/${enc(t.dataset.role)}/role`, {role: t.value}); toast('Role changed. They sign in again to see it.'); }
      catch (er) { toast(er.message, true); drawPane(); }
    }
  });
  APP.addEventListener('input', e => {
    const t = e.target;
    if (t.id === 'asFind') {
      const q = t.value.trim().toLowerCase(); let shown = 0;
      APP.querySelectorAll('#asAll .cw').forEach(c => { const hit = !q || c.textContent.toLowerCase().includes(q); c.hidden = !hit; if (hit) shown++; });
      const none = $('#asNone'); if (none) none.hidden = shown > 0;
    }
    if (t.id === 'asIdeaQ') { clearTimeout(IDEAS.t); IDEAS.t = setTimeout(() => { IDEAS.q = t.value.trim(); loadIdeas(true); }, 300); }
  });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); if (location.hash && location.hash !== '#/') go('#/'); setTimeout(() => $('#asAsk')?.focus(), 80); }
  });

  window.HoolaAppStudio = {version: '0.693.0'};
  route();
})();
