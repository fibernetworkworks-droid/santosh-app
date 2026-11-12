/* v0.649 HOOLA WEB STUDIO - the website builder as its OWN full-screen app (owner-approved prototype, "PERFECT").

   Home (own sidebar): one line + a Build | Plan switch.
     Build = the site is made at once (POST /api/sites) and its plan is accepted (POST /plan) so the THREE LOOKS start.
     Plan  = Hoola's architect writes a plan from HER words (POST /api/site-architect): she reads it as a document,
             changes it in the chat (/revise), and only "Build this plan" (/approve, with the hash she saw) makes the site.
   Either way she first gets THREE COMPLETE LOOKS: every page of the site in each look (server: service._full_looks),
   clickable in a computer / tablet / phone frame, and only "Build in this look" builds (POST /look).
   Workspace (#/site/<id>): her own Hoola thread on the left (a conversation per site - never the home chat), the live
   preview and every tool on the right (Preview, Code, Cloud, Integrations, Health, Settings; History + Publish on top).

   Rules kept from the server, drawn: every server value goes through esc(); look colours only as plain #hex; going live,
   rollback, take-down, redirects and deletes ask first and send the server's hash; her keys are never asked for here. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' ? v : {};
  const HEX = v => /^#[0-9a-f]{3,8}$/i.test(S(v)) ? S(v) : '';
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  const store = {get(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }, del(k) { try { localStorage.removeItem(k); } catch {} }};
  const TOKEN = store.get('hoola.console.token');
  const APP = $('#ws');
  if (!TOKEN) { location.replace('/console/'); return; }

  class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
  async function api(method, path, body, {raw = false, form = null} = {}) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (method === 'POST' && /\/conversations\/[^/]+\/messages$/.test(path) && body && typeof body.text === 'string') {
      const hints = L(body.hints).map(h => '\n\n[Web console ' + h + ']').join('');
      body = {...body, text: body.text + hints + '\n\n[Web console language preference: Reply in English unless I explicitly request another language.]'};
      delete body.hints;
    }
    if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
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

  const ICON = {
    home: '<path d="M4 11l8-7 8 7v9H4z"/>',
    app: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M8 13l-2 2 2 2M16 13l2 2-2 2"/>',
    clip: '<path d="M20 11l-8.5 8.5a5 5 0 0 1-7-7L13 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L14 7"/>', down: '<path d="M12 5v14M5 12l7 7 7-7"/>',
    list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>', doc: '<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h7M9 16h7"/>', grid: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18"/>',
    tpl: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>',
    back: '<path d="M15 5l-7 7 7 7"/>', plus: '<path d="M12 5v14M5 12h14"/>', up: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    chat: '<path d="M4 5h16v11H8l-4 4z"/>', move: '<path d="M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4"/>',
    pic: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 15l5-5 4 4 3-3 6 6"/>', sheet: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>', tab: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M11 18h2"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>', reload: '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>', lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>', sel: '<path d="M4 4l7 17 2-7 7-2z"/>', check: '<path d="M5 12l5 5 9-10"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>', code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>', chev: '<path d="M6 9l6 6 6-6"/>', arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>', pause: '<path d="M9 5v14M15 5v14"/>',
    cart: '<path d="M4 6h2l2 10h10l2-7H8"/>', card: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>', blog: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 11h8M8 15h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>', pin: '<path d="M12 21s-7-6-7-12a7 7 0 0 1 14 0c0 6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>', pen: '<path d="M3 21c3-1 5-3 7-6l7-7a2.1 2.1 0 0 0-3-3l-7 7c-3 2-5 4-6 7z"/>',
    note: '<path d="M5 4h14v12l-5 4H5z"/><path d="M14 20v-4h5"/>', trash: '<path d="M4 7h16M10 7V4h4v3M6 7l1 13h10l1-13"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'};
  const ico = (k, n = 18) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const tick = `<span class="tick" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5 9-10"/></svg></span>`;
  const STATUS = {draft: ['Starting', ''], planned: ['Plan ready', 'v'], looks: ['Pick a look', 'warn'], building: ['Building', 'v'],
    checking: ['Checking', 'v'], ready: ['Ready', 'ok'], failed: ['Needs attention', 'bad'], stopped: ['Paused', '']};
  const pill = (t, c) => `<span class="pill ${c || ''}">${esc(t)}</span>`;
  const statusPill = v => {
    if (S(v.status) === 'looks' && !L(v.looks).length) return pill('Making 3 looks', 'v');
    const [t, c] = STATUS[S(v.status)] || [S(v.status) || '…', ''];
    return pill(t + (Number(v.version) ? ` · v${v.version}` : ''), c);
  };
  const dotCls = v => ({ready: 'ok', looks: 'warn', planned: 'v', building: 'v', checking: 'v', failed: 'bad'}[S(v.status)] || '');
  const name = v => S(v.name) || S(v.field_label) || 'Website';
  const hasVersion = v => !!Number(v.version);
  /* v0.667 PREMIUM STUDIO helpers: a site's status in a few words, how long ago, a time of day, the thumbnail tint */
  const statusText = v => S(v.status) === 'building' && Number(M(v.board).pct) ? `Building · ${Math.round(Number(M(v.board).pct))}%`
    : S(v.status) === 'looks' && !L(v.looks).length ? 'Making 3 looks' : (STATUS[S(v.status)] || [S(v.status) || 'Draft'])[0] + (S(v.status) === 'ready' && Number(v.version) ? ` · v${v.version}` : '');
  const isoS = x => { const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(S(x)) ? S(x) : S(x) + 'Z'); return isNaN(t) ? 0 : t / 1000; };
  const ago = x => { const t = isoS(x); if (!t) return ''; const d = Math.max(0, Date.now() / 1000 - t);
    return d < 60 ? 'just now' : d < 3600 ? `${Math.floor(d / 60)} min ago` : d < 86400 ? `${Math.floor(d / 3600)} h ago` : `${Math.floor(d / 86400)} d ago`; };
  const clockOf = t => t ? new Date(t * 1000).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}) : '';
  const tint = id => { let h = 0; for (const c of S(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return 'g' + (h % 4); };
  const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
  const WORKING = v => ['building', 'checking'].includes(S(v.status)) || (S(v.status) === 'looks' && !L(v.looks).length) || !!v.mapping;
  const TYPES = [['Sweet shop', 'Menu, festival gift boxes, WhatsApp orders'], ['Clinic', 'Doctors, timings, booking slots you confirm'],
    ['Coaching classes', 'Batches, results, parent or student logins'], ['Restaurant', 'Menu with photos, table booking, directions'],
    ['Online shop', 'Catalogue, cart, COD and UPI, GST invoices'], ['Salon', 'Services, prices, appointment slots'],
    ['School admissions', 'Admissions form, fees, notices, logins'], ['Wedding or event', 'Story, gallery, RSVP form, venue map'],
    ['NGO or cause', 'Mission, projects, volunteer and donate pages'], ['Real estate', 'Projects, floor plans, site-visit booking'],
    ['Portfolio', 'Your work, about you, contact'], ['Personal page', 'About you, links, contact']];
  const MODE_KEY = 'hoola.ws.mode';
  const convKey = id => 'hoola.wdp.conv.' + id;           // the same per-site thread the v0.646 panel kept
  const DEV = {pc: [1280, 860, 'Computer'], tablet: [820, 1100, 'Tablet'], phone: [390, 800, 'Phone']};

  let SITES = [], SPECS = [], CUR = null, CARD = null, VIEW = 'preview', DEVICE = 'pc', LOOK = 0, EDIT = false;
  let POLL = null, SIG = '', PREFILL = '', BUSY = false, RO = null;
  let IMPUI = null, IMP_BACK = null, IMP_DONE = '';     // HOOLA PROMPTING: the Improve sheet + her original words for Undo
  try {                                                  // "Open in Web Studio" from the Prompting page: lands in the box, never sent
    const d = localStorage.getItem('hoola.prompt.toWeb');
    if (d) { localStorage.removeItem('hoola.prompt.toWeb'); PREFILL = String(d).slice(0, 2000); if (location.hash && location.hash !== '#/') location.hash = '#/'; }
  } catch (e) { /* private window */ }
  /* v0.683 the 1,00,000-prompt template library: her filters, the rows shown, the template she picked */
  const TPL = {q: '', sector: '', kind: '', style: '', rows: [], total: 0, all: 100000, meta: null, t: null};
  let TPLSEL = null;
  const lakh = n => Number(n || 0).toLocaleString('en-IN');
  const THREAD = {site: '', conv: '', rows: [], live: '', waiting: false, since: 0, started: 0, timer: null, sig: '', steps: [], stepMap: new Map(),
    costs: [], queue: [], files: [], thoughts: new Map(), stream: null, connected: false, pinned: false, think: null, detail: null};

  /* ================= router ================= */
  function parts() { return S(location.hash).replace(/^#\/?/, '').split('/').filter(Boolean); }
  async function route() {
    stopPoll(); clearTimeout(THREAD.timer); EDIT = false;
    const p = parts();
    if (!(p[0] === 'site' && p[1])) stopStream();                 // v0.777 the thread's live stream ends with the site
    if (!(p[0] === 'site' && p[1] && LIVE.site === decodeURIComponent(p[1]))) stopLive();
    try {
      if (p[0] === 'site' && p[1]) return await openSite(decodeURIComponent(p[1]), p[2] || '');
      if (p[0] === 'plan' && p[1]) return await openPlan(decodeURIComponent(p[1]));
      if ((p[0] === 'apps' || p[0] === 'app') && window.HoolaAppEngine) {   // v0.814 APP ENGINE 1: the React app lane
        CUR = null; CARD = null; await loadLists(); return await window.HoolaAppEngine.open(p);
      }
      CUR = null; CARD = null;
      await loadLists();
      drawHome(p[0] === 'sites' ? 'sites' : p[0] === 'starred' ? 'starred' : p[0] === 'templates' ? 'templates' : 'home');
      if (p[0] === 'sites' && p[1] === 'search') $('#wsFind')?.focus();
    } catch (e) { APP.innerHTML = `<div class="empty">${esc(e.message)} · <a href="#/">Studio home</a></div>`; }
  }
  addEventListener('hashchange', route);
  const go = h => { if (location.hash === h) route(); else location.hash = h; };

  async function loadLists() {
    const [a, b] = await Promise.allSettled([api('GET', '/api/sites'), api('GET', '/api/site-architect')]);
    SITES = a.status === 'fulfilled' ? L(a.value.sites) : [];
    SPECS = b.status === 'fulfilled' ? L(b.value.specs).filter(x => S(x.status) !== 'built') : [];
  }

  /* ================= home with its own sidebar ================= */
  /* v0.658 the project list like Lovable: search, starred, and a menu on every project (open, new tab, rename, star,
     delete). Stars are this browser's own choice (kept in localStorage); rename and delete go to the server. */
  const STAR_KEY = 'hoola.ws.star';
  const starred = () => { try { const x = JSON.parse(localStorage.getItem(STAR_KEY) || '[]'); return Array.isArray(x) ? x.map(String) : []; } catch { return []; } };
  const isStar = id => starred().includes(S(id));
  function setStar(id, on) {
    const cur = starred().filter(x => x !== S(id));
    try { localStorage.setItem(STAR_KEY, JSON.stringify((on ? [S(id), ...cur] : cur).slice(0, 60))); } catch {}
  }
  const recRow = v => `<div class="rec${CUR && S(CUR.id) === S(v.id) ? ' on' : ''}"><a class="rl" href="#/site/${enc(S(v.id))}"><span class="dot ${dotCls(v)}" aria-hidden="true"></span><span class="rt"><span class="ell">${esc(name(v))}</span><span class="rs">${esc(statusText(v))}</span></span></a>
    <button class="rm" type="button" data-menu="${esc(S(v.id))}" aria-label="More for ${esc(name(v))}" title="Rename, star, delete">${ico('more', 16)}</button></div>`;
  function sidebar(cur) {
    const st = SITES.filter(v => isStar(v.id));
    const rec = SITES.filter(v => !isStar(v.id)).slice(0, 8).map(recRow).join('');
    const nav = (h, k, label, ic) => `<a class="nav" href="${h}" ${cur === k ? 'aria-current="page"' : ''}>${ico(ic)}${esc(label)}</a>`;
    return `<aside class="side" aria-label="Web Studio">
      <div class="brand"><div class="mark" aria-hidden="true"><span></span></div><div><b>Hoola</b><span>Web Studio</span></div></div>
      <button class="new" type="button" data-act="new" title="New website (${MAC ? '⌘' : 'Ctrl'} K)"><span>${ico('plus', 16)}New website</span><kbd>${MAC ? '⌘ K' : 'Ctrl K'}</kbd></button>
      ${nav('#/', 'home', 'Home', 'home')}${nav('#/sites/search', 'search', 'Search', 'search')}${nav('#/sites', 'sites', 'All websites', 'grid')}${nav('#/starred', 'starred', 'Starred', 'star')}${nav('#/apps', 'apps', 'Apps', 'app')}${nav('#/templates', 'templates', 'Templates', 'tpl')}
      ${st.length ? `<div class="lbl">Starred</div>${st.map(recRow).join('')}` : ''}
      ${rec ? `<div class="lbl">Recent</div>${rec}` : ''}
      <div class="sp"></div>
      <a class="nav" href="/console/">${ico('back')}Back to Hoola</a>
    </aside>`;
  }

  function closeMenu() { document.getElementById('wsMenu')?.remove(); }
  function openMenu(btn, id) {
    const open = document.getElementById('wsMenu'); closeMenu();
    if (open && open.dataset.for === id) return;               // the same button again closes it
    const v = SITES.find(x => S(x.id) === id) || (CUR && S(CUR.id) === id ? CUR : null); if (!v) return;
    const star = isStar(id);
    const m = document.createElement('div');
    m.id = 'wsMenu'; m.className = 'wsmenu'; m.dataset.for = id; m.setAttribute('role', 'menu'); m.setAttribute('aria-label', `${name(v)} options`);
    const it = (k, ic, label, cls = '') => `<button type="button" role="menuitem" class="${cls}" data-mi="${k}">${ico(ic, 16)}<span>${label}</span></button>`;
    m.innerHTML = it('open', 'chat', 'Open') + it('tab', 'ext', 'Open in new tab') + it('rename', 'edit', 'Rename') +
      it('star', 'star', star ? 'Remove from starred' : 'Add to starred') + '<hr>' + it('delete', 'trash', 'Delete', 'bad');
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
  document.addEventListener('click', e => { const m = document.getElementById('wsMenu'); if (m && !m.contains(e.target) && !e.target.closest('[data-menu]')) closeMenu(); });
  addEventListener('resize', closeMenu); addEventListener('hashchange', closeMenu);
  async function menuAct(k, v) {
    const id = S(v.id), inSite = CUR && S(CUR.id) === id;
    try {
      if (k === 'open') return go('#/site/' + enc(id));
      if (k === 'tab') return void window.open(location.pathname + '#/site/' + enc(id), '_blank', 'noopener');
      if (k === 'star') { const on = !isStar(id); setStar(id, on); toast(on ? 'Added to starred.' : 'Removed from starred.'); if (!inSite) route(); return; }
      if (k === 'rename') {
        const fd = await dialog('Rename project', `<label class="sm mut" for="wsRename">Name in your project list</label><input class="in" id="wsRename" name="name" maxlength="80" required value="${esc(name(v))}">
          <p class="mut sm">Only the name in this list changes. Your pages and your address stay the same.</p>`);
        const nm = S(fd?.get('name')).trim(); if (!nm || nm === name(v)) return;
        const nv = await api('PATCH', `/api/sites/${enc(id)}`, {name: nm});
        toast('Renamed.');
        if (inSite) { CUR = nv; const p = APP.querySelector('.pname'); if (p) p.textContent = name(nv); document.title = `${name(nv)} · Hoola Web Studio`; }
        else route();
        return;
      }
      if (k === 'delete') {
        if (!confirm(`Delete "${name(v)}"?\n\nIts pages, data and versions are removed. If it is live, it is taken off the internet first. This cannot be undone.`)) return;
        await api('DELETE', `/api/sites/${enc(id)}`);
        setStar(id, false); toast('Deleted.');
        if (inSite) go('#/sites'); else route();
      }
    } catch (er) { toast(er.message, true); }
  }

  function siteCard(v) {
    return `<div class="cw"><a class="card" href="#/site/${enc(S(v.id))}"><span class="shot ${tint(v.id)}" aria-hidden="true"><i></i><i></i><b></b></span>
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b class="ell">${esc(name(v))}</b>${isStar(v.id) ? `<span class="stard" title="Starred" aria-label="Starred">${ico('star', 14)}</span>` : ''}${statusPill(v)}</span>
      <span class="mut sm ell">${esc([S(v.number), S(v.field_label), S(v.goal_label)].filter(Boolean).join(' · '))}</span>${v.updated_at ? `<span class="ed">Edited ${esc(ago(v.updated_at))}</span>` : ''}</span></a>
      <button class="cm" type="button" data-menu="${esc(S(v.id))}" aria-label="More for ${esc(name(v))}" title="Rename, star, delete">${ico('more', 16)}</button></div>`;
  }
  function specCard(x) {
    return `<a class="card" href="#/plan/${enc(S(x.id))}"><span class="shot" aria-hidden="true"><i></i><i></i><b></b></span>
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b>${esc(S(x.name) || 'New plan')}</b>${pill('Plan · your Haan', 'v')}</span>
      <span class="mut sm ell">${esc(S(x.words))}</span></span></a>`;
  }

  function drawHome(page) {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    let main;
    if (page === 'templates') {
      main = `<section class="wrap tplw"><div class="sec"><h2 style="font-size:24px">Templates</h2><span class="tplall">${lakh(TPL.all)} websites</span></div>
        <p class="mut">1,00,000 different websites from around the world: software, schools, hospitals, studios, shops, non-profits, climate tech and more, in 50 sectors and 10 cities. Every template is its own business with its own name, website type and design, and a deep prompt for the pages, design and build. Open one, use it as it is or change any line.</p>
        <div class="tplbar"><label class="find">${ico('search', 16)}<input id="wsTplQ" type="search" placeholder="Search: AI tool, school, cafe Berlin, eco-friendly, online store…" aria-label="Search templates" autocomplete="off" value="${esc(TPL.q)}"></label>
          <select id="wsTplInd" aria-label="Sector"><option value="">All sectors</option></select>
          <select id="wsTplGoal" aria-label="Website type"><option value="">Any website type</option></select>
          <select id="wsTplStyle" aria-label="Design style"><option value="">Any style</option></select></div>
        <p class="mut sm" id="wsTplCount" aria-live="polite">Loading templates…</p>
        <div class="tgrid" id="wsTplGrid"></div>
        <div class="tplmore"><button class="b" type="button" data-act="tpl-more" hidden>Show more</button></div></section>
      <section class="wrap"><div class="sec"><h2>Quick starts</h2></div>
        <div class="starts">${TYPES.map(([t, d]) => `<button class="st" type="button" data-type="${esc(t)}"><span class="si">${ico('tpl')}</span><span><b>${esc(t)}</b><span class="mut sm">${esc(d)}</span></span></button>`).join('')}</div></section>`;
    } else if (page === 'sites') {
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">All websites</h2><button class="b" type="button" data-act="new">${ico('plus', 16)}New website</button></div>
        <label class="find">${ico('search', 16)}<input id="wsFind" type="search" placeholder="Search your websites" aria-label="Search your websites" autocomplete="off"></label>
        ${SPECS.length ? `<div class="sec"><h2>Plans waiting for your Haan</h2></div><div class="grid">${SPECS.map(specCard).join('')}</div>` : ''}
        ${SITES.length ? `<div class="grid" id="wsAll">${SITES.map(siteCard).join('')}</div><p class="mut" id="wsNone" hidden>No website matches.</p>` : '<div class="panel mut">No website yet. Write one line on the Studio home.</div>'}</section>`;
    } else if (page === 'starred') {
      const st = SITES.filter(v => isStar(v.id));
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">Starred</h2></div>
        ${st.length ? `<div class="grid">${st.map(siteCard).join('')}</div>` : `<div class="panel mut">Nothing starred yet. Open the ${ico('more', 14)} menu on any website and choose Add to starred.</div>`}</section>`;
    } else {
      main = `<div class="aura" aria-hidden="true"><i class="a1"></i><i class="a2"></i><i class="a3"></i><i class="a4"></i></div>
      <section class="hero"><span class="eyebrow"><b>New</b>Watch your website being built, live${ico('arrow', 14)}</span><h1 id="wsGreet">${esc(greetLine(''))}</h1>
        <p class="mut">Describe your business in one line. Hoola writes every page, shows you three complete designs, and builds the one you pick, right in front of you. Nothing goes live until you tap.</p>
        <form class="ask" data-form="ask">
          <label for="wsAsk" class="sr">Describe your website</label>
          <textarea id="wsAsk" rows="3" maxlength="2000" placeholder="Ask Hoola to build a website for my clinic..." data-type-ph>${esc(PREFILL)}</textarea>
          <div class="bar">
            <button class="b ghost" type="button" data-src="old">${ico('globe', 15)}Use my old site</button>
            <button class="b ghost" type="button" data-src="shot">${ico('pic', 15)}From a screenshot</button>
            ${window.HoolaImprove ? `<button class="b ghost" type="button" data-improve title="See what Hoola understood and turn this into a complete website prompt">Improve</button>` : ''}
            <span class="sp"></span>
            <span class="mut sm mnote" id="wsModeNote">${mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: 3 full looks first'}</span>
            <div class="seg" role="group" aria-label="Mode"><button type="button" data-mode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-mode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
            <button class="go" type="submit" aria-label="Start">${ico('up', 18)}</button>
          </div>
        </form>
        <div id="wsAskWork" class="step wrap" role="status" aria-live="polite" style="max-width:780px;margin-top:10px" hidden></div>
        <div id="wsSrc" class="wrap" style="max-width:780px"></div>
        <div class="chips" role="group" aria-label="What are you making?">${CHIPS.map(t => `<button class="chip" type="button" data-chip="${esc(t)}" aria-pressed="false">${esc(t)}</button>`).join('')}<a class="chip" href="#/templates">Ideas</a></div>
      </section>
      <section class="wrap" id="wsStarters" hidden><div class="sec"><h2 id="wsStartersH">Starting points</h2><span class="mut sm">Pick one, change any word, then send. Thumbnails show the look each one is built in.</span></div>
        <div class="sgrid" id="wsStartGrid"></div></section>
      ${SPECS.length ? `<section class="wrap"><div class="sec"><h2>Plans waiting for your Haan</h2></div><div class="grid">${SPECS.slice(0, 4).map(specCard).join('')}</div></section>` : ''}
      <section class="wrap"><div class="sec"><h2>Your websites</h2>${SITES.length ? `<a class="more" href="#/sites">View all ${ico('arrow', 13)}</a>` : ''}</div>
        ${SITES.length ? `<div class="grid">${SITES.slice(0, 8).map(siteCard).join('')}</div>` : '<div class="panel mut">No website yet. Write one line above.</div>'}</section>
      <section class="wrap"><div class="sec"><h2>Or start from</h2></div><div class="starts">
        <button class="st" type="button" data-src="focus"><span class="si">${ico('chat')}</span><span><b>Describe it</b><span class="mut sm">One line in your own words.</span></span></button>
        <button class="st" type="button" data-src="old"><span class="si">${ico('move')}</span><span><b>Move my old site</b><span class="mut sm">Your own site; old links keep working.</span></span></button>
        <button class="st" type="button" data-src="shot"><span class="si">${ico('pic')}</span><span><b>A picture or screenshot</b><span class="mut sm">Colours and style are measured.</span></span></button>
        <button class="st" type="button" data-src="sheet"><span class="si">${ico('sheet')}</span><span><b>A product sheet</b><span class="mut sm">Excel or Google Sheet to a catalogue.</span></span></button>
      </div></section>`;
    }
    APP.innerHTML = `<div class="home">${sidebar(page)}<main class="hmain">${main}</main></div>`;
    PREFILL = '';
    if (page === 'home') homeLife();
    if (page === 'templates') loadTpl(true);
    document.title = 'Hoola Web Studio';
  }


  /* ================= v0.835 GHAR + SHURUAAT (L12): greeting, typewriter, chips, real starters ================= */
  const CHIPS = ['Website', 'Online store', 'Dashboard', 'Booking site', 'Portal', 'Landing page', 'Blog', 'Internal tool'];
  const ENDS = ['a website for my clinic...', 'a dashboard to track my sales...', 'an online store that takes UPI...', 'a portal where parents see marks...',
    'a booking page for my salon...', 'a landing page for my new course...', 'a tool my staff use to log visits...'];
  const GREETS = {
    morning: ['Good morning{n}. What should we build?', 'Morning{n}. Got an idea to start the day?', 'Good morning{n}. What are we making today?'],
    afternoon: ['Good afternoon{n}. What should we build?', 'Afternoon{n}. Got an idea?', 'Hello{n}. What are we making today?'],
    evening: ['Good evening{n}. What should we build?', 'Evening{n}. Got an idea?', 'Hello{n}. What shall we make tonight?'],
  };
  const HOME = {name: null, starters: null, kind: '', pick: Math.floor(Math.random() * 3)};
  function greetLine(name) {
    const h = new Date().getHours(), part = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening';
    const first = S(name).trim().split(/\s+/)[0];
    return GREETS[part][HOME.pick % GREETS[part].length].replace('{n}', first ? ', ' + first : '');
  }
  function typewriter(ta) {
    clearTimeout(typewriter._t);
    if (!ta || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const base = 'Ask Hoola to build ';
    let i = Math.floor(Math.random() * ENDS.length), n = 0, del = false;
    const step = () => {
      if (!ta.isConnected) return;
      if (ta.value || document.activeElement === ta) { ta.placeholder = base + ENDS[i]; typewriter._t = setTimeout(step, 1500); return; }
      const t = ENDS[i];
      if (!del) {
        n++; ta.placeholder = base + t.slice(0, n);
        if (n >= t.length) { del = true; typewriter._t = setTimeout(step, 1600); return; }
        typewriter._t = setTimeout(step, 45);
      } else {
        n = Math.max(0, n - 2); ta.placeholder = base + t.slice(0, n);
        if (n === 0) { del = false; i = (i + 1) % ENDS.length; typewriter._t = setTimeout(step, 400); return; }
        typewriter._t = setTimeout(step, 22);
      }
    };
    step();
  }
  function thumb(x) {
    const c = x.palette, A = `fill="${c.accent}"`, I = `fill="${c.ink}" opacity=".78"`, So = `fill="${c.soft}"`;
    const bar = `<rect x="6" y="6" width="108" height="7" rx="3" ${So}/><circle cx="12" cy="9.5" r="2" ${A}/><rect x="84" y="8" width="10" height="3" rx="1.5" ${I} opacity=".35"/><rect x="98" y="8" width="10" height="3" rx="1.5" ${I} opacity=".35"/>`;
    const L = {
      hero: `<rect x="26" y="26" width="68" height="8" rx="3" ${I}/><rect x="36" y="38" width="48" height="4" rx="2" ${I} opacity=".4"/><rect x="48" y="48" width="24" height="9" rx="4.5" ${A}/><rect x="12" y="62" width="30" height="8" rx="3" ${So}/><rect x="45" y="62" width="30" height="8" rx="3" ${So}/><rect x="78" y="62" width="30" height="8" rx="3" ${So}/>`,
      split: `<rect x="10" y="22" width="50" height="8" rx="3" ${I}/><rect x="10" y="34" width="40" height="4" rx="2" ${I} opacity=".4"/><rect x="10" y="41" width="34" height="4" rx="2" ${I} opacity=".4"/><rect x="10" y="52" width="22" height="9" rx="4.5" ${A}/><rect x="68" y="20" width="42" height="46" rx="5" ${So}/><circle cx="89" cy="43" r="9" ${A} opacity=".55"/>`,
      grid: [0, 1, 2, 3, 4, 5].map(k => `<rect x="${10 + (k % 3) * 35}" y="${20 + Math.floor(k / 3) * 28}" width="31" height="20" rx="4" ${k === 0 ? A : So}${k === 0 ? ' opacity=".7"' : ''}/><rect x="${10 + (k % 3) * 35}" y="${43 + Math.floor(k / 3) * 28}" width="20" height="3" rx="1.5" ${I} opacity=".5"/>`).join(''),
      list: [0, 1, 2, 3].map(k => `<rect x="10" y="${20 + k * 13}" width="100" height="10" rx="3" ${So}/><rect x="14" y="${23.5 + k * 13}" width="${34 + (k * 9) % 22}" height="3" rx="1.5" ${I} opacity=".6"/><rect x="92" y="${23 + k * 13}" width="14" height="4" rx="2" ${A}/>`).join(''),
      board: [0, 1, 2].map(k => `<rect x="${10 + k * 36}" y="20" width="32" height="50" rx="4" ${So}/><rect x="${13 + k * 36}" y="25" width="26" height="9" rx="2.5" ${k === 0 ? A : I} opacity="${k === 0 ? 0.8 : 0.45}"/><rect x="${13 + k * 36}" y="38" width="26" height="9" rx="2.5" ${I} opacity=".3"/>${k < 2 ? `<rect x="${13 + k * 36}" y="51" width="26" height="9" rx="2.5" ${I} opacity=".3"/>` : ''}`).join(''),
      chart: `<rect x="10" y="20" width="30" height="14" rx="3" ${So}/><rect x="45" y="20" width="30" height="14" rx="3" ${So}/><rect x="80" y="20" width="30" height="14" rx="3" ${So}/><polyline points="12,66 30,56 48,60 66,46 84,50 108,38" fill="none" stroke="${c.accent}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><rect x="10" y="40" width="100" height="1" ${I} opacity=".15"/>`,
      form: `<rect x="30" y="20" width="60" height="6" rx="2" ${I}/><rect x="30" y="31" width="60" height="9" rx="3" ${So}/><rect x="30" y="44" width="60" height="9" rx="3" ${So}/><rect x="30" y="57" width="34" height="10" rx="5" ${A}/>`,
      feed: `<rect x="10" y="20" width="62" height="7" rx="2.5" ${I}/><rect x="10" y="31" width="62" height="3.5" rx="1.75" ${I} opacity=".4"/><rect x="10" y="38" width="50" height="3.5" rx="1.75" ${I} opacity=".4"/><rect x="10" y="48" width="62" height="7" rx="2.5" ${I}/><rect x="10" y="59" width="62" height="3.5" rx="1.75" ${I} opacity=".4"/><rect x="80" y="20" width="30" height="42" rx="4" ${So}/><rect x="83" y="24" width="24" height="16" rx="3" ${A} opacity=".6"/>`,
    }[x.layout] || '';
    return `<svg viewBox="0 0 120 76" class="sthumb" role="img" aria-label="${esc(x.title)} preview" style="background:${c.bg}"><rect width="120" height="76" fill="${c.bg}"/>${bar}${L}</svg>`;
  }
  function drawStarters() {
    const box = $('#wsStarters'), grid = $('#wsStartGrid'); if (!box || !grid || !HOME.starters) return;
    const list = HOME.starters.filter(x => !HOME.kind || x.kind === HOME.kind);
    box.hidden = !HOME.kind;
    $('#wsStartersH').textContent = HOME.kind ? `${HOME.kind} starting points` : 'Starting points';
    grid.innerHTML = list.map(x => `<button class="scard" type="button" data-starter="${esc(x.id)}">${thumb(x)}<b>${esc(x.title)}</b><span class="mut sm">${esc(x.line)}</span></button>`).join('');
    APP.querySelectorAll('[data-chip]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.chip === HOME.kind)));
  }
  async function homeLife() {
    const ta = $('#wsAsk'); typewriter(ta);
    const g = $('#wsGreet');
    if (HOME.name === null) { try { const m = await api('GET', '/api/console/me'); HOME.name = S(m.owner); } catch (e) { HOME.name = ''; } }
    if (g && g.isConnected) g.textContent = greetLine(HOME.name);
    if (!HOME.starters) { try { HOME.starters = L((await api('GET', '/api/site-starters')).starters); } catch (e) { HOME.starters = []; } }
    drawStarters();
  }
  function chooseStarter(id) {
    const x = L(HOME.starters).find(y => y.id === id); if (!x) return;
    const t = $('#wsAsk'); if (!t) return;
    t.value = x.prompt; t.dispatchEvent(new Event('input', {bubbles: true})); t.focus(); t.setSelectionRange(t.value.length, t.value.length);
    t.scrollIntoView({block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }

  function tplCard(r) {
    return `<button class="tcard" type="button" data-tpl="${esc(r.id)}"><span class="tn">#${lakh(r.n)}</span><b>${esc(r.title)}</b>
      <span class="tl">${esc(r.line)}</span><span class="mut sm">${esc(r.sector_label)} · ${esc(r.city)}</span><span class="tchips"><i>${esc(r.type_label)}</i><i>${esc(r.style_label)}</i></span></button>`;
  }
  function tplOptions(sel, list, val, first) {
    const el = $(sel); if (!el || el.options.length > 1) { if (el) el.value = val; return; }
    el.innerHTML = `<option value="">${first}</option>` + list.map(o => `<option value="${esc(o.id)}">${esc(o.label)}</option>`).join('');
    el.value = val;
  }
  async function loadTpl(reset) {
    const grid = $('#wsTplGrid'); if (!grid) return;
    if (reset) TPL.rows = [];
    const qs = new URLSearchParams({q: TPL.q, sector: TPL.sector, kind: TPL.kind, style: TPL.style, offset: String(TPL.rows.length), limit: '30'});
    let r;
    try { r = await api('GET', '/api/site-templates?' + qs); } catch (e) { $('#wsTplCount').textContent = e.message; return; }
    if (!$('#wsTplGrid')) return;
    TPL.rows = TPL.rows.concat(r.rows || []); TPL.total = r.total || 0; TPL.all = r.all || TPL.all;
    tplOptions('#wsTplInd', r.sectors || [], TPL.sector, 'All sectors');
    tplOptions('#wsTplGoal', r.types || [], TPL.kind, 'Any website type');
    tplOptions('#wsTplStyle', r.styles || [], TPL.style, 'Any style');
    const all = APP.querySelector('.tplall'); if (all) all.textContent = `${lakh(TPL.all)} websites`;
    $('#wsTplCount').textContent = TPL.total ? `${lakh(TPL.total)} templates${TPL.q || TPL.sector || TPL.kind || TPL.style ? ' match' : ''} · showing ${lakh(TPL.rows.length)}`
      : 'No template matches. Try a simpler word, like "clinic" or "shop".';
    grid.innerHTML = TPL.rows.map(tplCard).join('');
    const more = APP.querySelector('[data-act="tpl-more"]'); if (more) more.hidden = TPL.rows.length >= TPL.total;
  }
  async function openTpl(id) {
    let p;
    try { p = await api('GET', '/api/site-templates/' + enc(id)); } catch (e) { return toast(e.message, true); }
    const d = document.createElement('dialog'); d.className = 'dlg tpld';
    d.innerHTML = `<div class="tpldh"><span class="tn">Template #${lakh(p.n)} of ${lakh(TPL.all)}</span><b>${esc(p.title)}</b><span class="tl">${esc(p.line)}${p.country && p.country !== p.city ? ', ' + esc(p.country) : ''}</span>
        <span class="tchips"><i>${esc(p.sector_label)}</i><i>${esc(p.type_label)}</i><i>${esc(p.style_label)}</i></span></div>
      <pre class="tpre" tabindex="0">${esc(p.prompt)}</pre>
      <p class="mut sm">${lakh(p.chars)} characters · ${p.pages.length} pages · you can change any line after you tap Use.</p>
      <div class="inl" style="justify-content:flex-end"><button class="b" type="button" data-x="close">Close</button><button class="b" type="button" data-x="copy">Copy</button><button class="b pri" type="button" data-x="use">Use this prompt</button></div>`;
    document.body.appendChild(d);
    d.addEventListener('close', () => d.remove());
    d.addEventListener('click', async ev => {
      const x = ev.target.closest('[data-x]')?.dataset.x; if (!x) return;
      if (x === 'close') return d.close();
      if (x === 'copy') { try { await navigator.clipboard.writeText(p.prompt); toast('Prompt copied.'); } catch { toast('Select the text and copy it.', true); } return; }
      if (x === 'use') { TPLSEL = {field: p.field, goal: p.goal, style: p.style, text: p.prompt}; PREFILL = p.prompt; d.close(); go('#/'); }
    });
    d.showModal();
  }

  function drawSource(kind) {
    const box = $('#wsSrc'); if (!box) return;
    if (kind === 'old') box.innerHTML = `<form class="panel" data-form="old"><b>Move my old website</b>
        <p class="mut sm">Hoola reads your own site's pages, colours, photos and addresses. If it can't tell the site is yours, it shows one line to add first.</p>
        <div class="inl"><input class="in" name="url" type="url" inputmode="url" aria-label="Your old website address" placeholder="https://your-old-site.in" required>
        <button class="b pri" type="submit">Read my site</button></div><div data-out></div></form>`;
    else if (kind === 'shot') box.innerHTML = `<form class="panel" data-form="shot"><b>Use a design you like</b>
        <p class="mut sm">Write one line about the website in the box above. The picture's colours and style are measured; no words, logos or photos are taken from it.</p>
        <div class="inl"><input name="file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Picture" required>
        <button class="b pri" type="submit">Read the design</button></div><div data-out></div></form>`;
    else if (kind === 'sheet') box.innerHTML = `<div class="panel"><b>From a product sheet</b><p class="mut sm">Write one line about the shop above and put the sheet link in it. After the website is built, Cloud previews the catalogue before anything is written.</p></div>`;
    else box.innerHTML = '';
  }

  async function newConv(title) {
    const c = S((await api('POST', '/api/conversations')).id);
    if (title) api('PATCH', `/api/conversations/${enc(c)}`, {title}).catch(() => {});
    return c;
  }

  /* v0.707 SEEDHA WORKSPACE: the moment she sends, the page moves to the workspace (her words in the chat, a live work
     card with the real clock, the plan / site area filling in) - it never sits on the home under a small note while
     the server writes the plan. When the server answers, the real plan / website opens in the same place. */
  function drawPending(plan, text, ticket = '') {
    const steps = plan ? ['Reading your words', 'Choosing the pages, users and data', 'Writing the plan document']
      : ['Reading your idea.', 'Planning the pages and what each one holds.', 'Choosing colours and fonts, and setting up the website.'];
    const t0 = nowS();
    APP.innerHTML = `<div class="wsp wsp-in" data-pending="${plan ? 'plan' : 'build'}">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">${plan ? 'New plan' : 'New website'}</span>${pill(plan ? 'Writing the plan' : 'Starting', 'v')}<span class="sp"></span>
        <a class="b ghost" href="#/sites">All websites</a></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola">
          <div class="msgs" id="wsPendMsgs" aria-live="polite"><div class="me">${esc(text)}</div>
            <div class="chatact wcard"><div class="step whead"><span class="spin" aria-hidden="true"></span><span class="wt"><b>${plan ? 'Writing your plan' : 'Setting the stage'}</b><span id="wsPendNow">${esc(steps[0])}</span></span><span class="tm" data-t0="${t0}"></span></div>
              <div class="prog ind" role="progressbar" aria-label="Progress"><i style="width:30%"></i></div>
              <ol class="acts" id="wsPendSteps">${steps.map((x, i) => `<li class="${i ? 'wait' : 'run'}" data-i="${i}">${i ? '<span class="tick off" aria-hidden="true"></span>' : '<span class="spin" aria-hidden="true"></span>'}<div class="sl"><span class="ell">${esc(x)}</span></div><span class="tm"${i ? '' : ` data-t0="${t0}"`}></span></li>`).join('')}</ol>
              <div class="wfoot"><span class="ell">${plan ? 'About a minute. Nothing is built until you say so.' : 'About a minute, then the three looks appear here.'}</span></div></div></div>
          <form class="comp" aria-disabled="true"><textarea rows="2" disabled placeholder="You can write here once ${plan ? 'the plan' : 'the website'} opens…"></textarea>
            <div class="cbar"><span class="mut sm">${plan ? 'Plan mode' : 'Build mode'}</span><span class="sp"></span><button class="send" type="button" disabled aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" aria-label="${plan ? 'Plan' : 'Website'}">
          <div class="ptop"><nav class="views" aria-label="Views"><button type="button" aria-current="page">${plan ? 'Plan' : 'Preview'}</button><button type="button" disabled>${plan ? 'Preview' : 'Code'}</button></nav></div>
          <div class="stage"><article class="doc skel" aria-busy="true" aria-label="${plan ? 'The plan is being written' : 'The website is starting'}">
            <i class="sk w40"></i><i class="sk h"></i><i class="sk"></i><i class="sk w80"></i><i class="sk w60"></i><i class="sk h"></i><i class="sk"></i><i class="sk w70"></i><i class="sk w50"></i></article></div>
        </section></div></div>`;
    document.title = `${plan ? 'New plan' : 'New website'} · Hoola Web Studio`;
    startTick();
    clearInterval(drawPending._t);
    if (ticket) {          // v0.835 L12: the steps are the server's own (what the call is really doing), never client-timed labels
      let seq = 0;
      drawPending._t = setInterval(async () => {
        const ol = $('#wsPendSteps'); if (!ol) return clearInterval(drawPending._t);
        let r; const me = ++seq;
        try { r = await api('GET', `/api/sites/stage/${enc(ticket)}`); } catch (e) { return; }
        if (me !== seq || !$('#wsPendSteps') || !L(r.steps).length) return;
        CLOCK = Number(r.now) - Date.now() / 1000;
        ol.innerHTML = L(r.steps).map(x => {
          const run = x.state === 'run', end = x.end || r.now;
          return `<li class="${run ? 'run' : x.state === 'error' ? 'bad' : 'ok'}">${run ? '<span class="spin" aria-hidden="true"></span>' : tick}<div class="sl"><span class="ell">${esc(S(x.label))}</span></div><span class="tm">${esc(dur(end - x.at))}</span></li>`;
        }).join('');
        const cur = L(r.steps).filter(x => x.state === 'run').pop() || L(r.steps).pop();
        const nw = $('#wsPendNow'); if (nw && cur) nw.textContent = S(cur.label);
      }, 1200);
      return;
    }
    // plan mode only: the steps move on the real clock while the one server call runs (labels only; the server answer decides)
    let k = 0;
    drawPending._t = setInterval(() => {
      const ol = $('#wsPendSteps'); if (!ol) return clearInterval(drawPending._t);
      if (k >= steps.length - 1) return;
      const now = nowS(), cur = ol.querySelector(`[data-i="${k}"]`), nxt = ol.querySelector(`[data-i="${k + 1}"]`);
      if (cur) { cur.className = 'ok'; cur.firstElementChild.outerHTML = tick; const tm = cur.querySelector('.tm'); if (tm) { tm.removeAttribute('data-t0'); tm.textContent = dur(now - Number(tm.dataset.s || t0)); } }
      k++;
      if (nxt) { nxt.className = 'run'; nxt.firstElementChild.outerHTML = '<span class="spin" aria-hidden="true"></span>'; const tm = nxt.querySelector('.tm'); if (tm) { tm.dataset.t0 = now; tm.dataset.s = now; } }
      const nw = $('#wsPendNow'); if (nw) nw.textContent = steps[k];
      tickClocks();
    }, plan ? 14000 : 6000);
  }

  /* ================= v0.784 SAWAAL CARD (L3): a few design choices she can SEE before a Build ================= */
  const WIRES = {               // the top of the home page as a wireframe (from the hero's own description, server side)
    split: '<rect x="8" y="14" width="46" height="7" rx="2"/><rect x="8" y="25" width="38" height="4" rx="2" class="l"/><rect x="8" y="33" width="30" height="4" rx="2" class="l"/><rect x="8" y="44" width="20" height="8" rx="4" class="a"/><rect x="64" y="10" width="48" height="56" rx="4" class="p"/>',
    full: '<rect x="4" y="6" width="112" height="64" rx="4" class="p"/><rect x="22" y="26" width="76" height="8" rx="2" class="w"/><rect x="34" y="38" width="52" height="4" rx="2" class="w"/><rect x="48" y="48" width="24" height="8" rx="4" class="a"/>',
    grid: '<rect x="8" y="8" width="60" height="7" rx="2"/><rect x="8" y="19" width="40" height="4" rx="2" class="l"/><rect x="8" y="30" width="32" height="18" rx="3" class="p"/><rect x="44" y="30" width="32" height="18" rx="3" class="p"/><rect x="80" y="30" width="32" height="18" rx="3" class="p"/><rect x="8" y="52" width="32" height="14" rx="3" class="p"/><rect x="44" y="52" width="32" height="14" rx="3" class="p"/><rect x="80" y="52" width="32" height="14" rx="3" class="p"/>',
    type: '<rect x="8" y="12" width="104" height="14" rx="3"/><rect x="8" y="30" width="86" height="14" rx="3"/><rect x="8" y="50" width="50" height="4" rx="2" class="l"/><rect x="8" y="58" width="22" height="8" rx="4" class="a"/>',
    centre: '<rect x="24" y="14" width="72" height="8" rx="2"/><rect x="32" y="26" width="56" height="4" rx="2" class="l"/><rect x="48" y="36" width="24" height="8" rx="4" class="a"/><rect x="14" y="50" width="92" height="18" rx="4" class="p"/>',
  };
  const wire = k => `<svg class="wire" viewBox="0 0 120 76" aria-hidden="true">${WIRES[k] || WIRES.centre}</svg>`;
  function qFont(o) {           // each font pair shown in its own type (the bundled woff2 files, nothing from outside)
    if (!o) return {h: 'inherit', b: 'inherit'};
    let st = $('#wsQFonts'); if (!st) { st = document.createElement('style'); st.id = 'wsQFonts'; document.head.appendChild(st); }
    const h = `hq-${o.id}-h`, b = `hq-${o.id}-b`;
    if (!st.textContent.includes(`'${h}'`)) {
      st.textContent += (o.head_url ? `@font-face{font-family:'${h}';src:url(${o.head_url}) format('woff2');font-display:swap}` : '')
        + (o.body_url ? `@font-face{font-family:'${b}';src:url(${o.body_url}) format('woff2');font-display:swap}` : '');
    }
    return {h: o.head_url ? `'${h}',serif` : 'inherit', b: o.body_url ? `'${b}',sans-serif` : 'inherit'};
  }
  function qOption(q, o, i) {
    const c = M(o.colours), id = `wsq-${q.id}-${i}`;
    let art = '';
    if (q.kind === 'style') {
      const f = qFont(o.font);
      art = `<span class="qart qstyle" style="background:${HEX(c.bg)};color:${HEX(c.ink)};border-radius:${Math.min(16, Number(o.radius) || 0)}px">
        <b style="font-family:${esc(f.h)}">Aa</b><i style="background:${HEX(c.primary)};border-radius:${Math.min(12, Number(o.radius) || 0)}px"></i><i class="ac" style="background:${HEX(c.accent)}"></i></span>`;
    } else if (q.kind === 'palette') {
      art = `<span class="qart qpal">${['bg', 'surface', 'ink', 'primary', 'accent'].map(k => `<i style="background:${HEX(c[k])}" title="${k} ${HEX(c[k])}"></i>`).join('')}</span>`;
    } else if (q.kind === 'fonts') {
      const f = qFont(o);
      art = `<span class="qart qfont"><b style="font-family:${esc(f.h)}">${esc(S(o.head))}</b><span style="font-family:${esc(f.b)}">Fresh every morning, made with care.</span></span>`;
    } else if (q.kind === 'hero') art = `<span class="qart qhero">${wire(S(o.wire))}</span>`;
    return `<label class="qopt" for="${id}"><input type="radio" id="${id}" name="${esc(q.id)}" value="${esc(S(o.id))}"${i === 0 ? ' checked' : ''}>
      ${art}<span class="qtxt"><b>${esc(S(o.label))}</b>${o.line && q.kind !== 'palette' ? `<span class="mut sm">${esc(S(o.line))}</span>` : ''}</span></label>`;
  }
  async function askDesign(text) {
    // resolves {design} (null = Hoola picks) or null (she went back); a failed read never blocks her Build
    const q = await api('GET', '/api/site-design/questions?brief=' + encodeURIComponent(text)).catch(() => null);
    if (!q || q.skip || !L(q.questions).length) return {design: null};
    APP.innerHTML = `<div class="wsp wsp-in" data-questions="1">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">New website</span>${pill('A few choices', 'v')}<span class="sp"></span></header>
      <form class="wsq" id="wsQ" aria-labelledby="wsQh">
        <div class="qhead"><h1 id="wsQh">A few quick choices</h1>
          <p class="mut">So the first design is yours. Pick what you like, or skip and Hoola picks. Two more designs come with it, so you can still compare.</p>
          <blockquote class="qask">${esc(text.length > 220 ? text.slice(0, 220) + '…' : text)}</blockquote></div>
        ${L(q.questions).map(x => `<fieldset class="qset qk-${esc(S(x.kind))}"><legend>${esc(S(x.title))}</legend>
          <div class="qopts">${L(x.options).map((o, i) => qOption(x, o, i)).join('')}</div></fieldset>`).join('')}
        <div class="qbar"><button class="b ghost" type="button" data-q="back">${ico('back', 16)}Back</button><span class="sp"></span>
          <button class="b" type="button" data-q="skip">Skip, Hoola picks</button>
          <button class="b pri" type="submit">Build with these${ico('arrow', 16)}</button></div>
      </form></div>`;
    document.title = 'A few choices · Hoola Web Studio';
    const f = $('#wsQ');
    f.querySelector('input')?.focus();
    return new Promise(res => {
      const done = v => { removeEventListener('keydown', esc_); res(v); };
      const esc_ = e => { if (e.key === 'Escape' && $('#wsQ')) { e.preventDefault(); done(null); } };
      addEventListener('keydown', esc_);
      f.addEventListener('submit', e => { e.preventDefault(); e.stopPropagation(); done({design: Object.fromEntries(new FormData(f))}); });
      f.addEventListener('click', e => {
        const b = e.target.closest('[data-q]'); if (!b) return;
        e.stopPropagation();
        done(b.dataset.q === 'skip' ? {design: null} : null);
      });
    });
  }

  async function startFromAsk(text, design = null, ticket = '') {
    const mode = store.get(MODE_KEY) === 'plan' ? 'plan' : 'build';
    const conv = await newConv('');
    try {
      if (mode === 'plan') {
        const c = await api('POST', '/api/site-architect', {words: text, conversation_id: conv});
        store.set('hoola.ws.spec.conv.' + c.id, conv); store.set('hoola.ws.spec.words.' + c.id, text);
        api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Website plan · ${S(c.name) || 'new'}`}).catch(() => {});
        go('#/plan/' + enc(S(c.id)));
        return;
      }
      const body = {brief: text, conversation_id: conv, deep: true, ticket};   // v0.708 a system ask is planned deep first
      if (TPLSEL && text.includes('[Hoola template #')) Object.assign(body, {field: TPLSEL.field, goal: TPLSEL.goal, style: TPLSEL.style});   // v0.686 the template's library card
      TPLSEL = null;
      if (design) body.design = design;                // v0.784 her picks on the question card = look 1
      const v = await api('POST', '/api/sites', body);
      store.set(convKey(v.id), conv);
      api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Website · ${name(v)}`}).catch(() => {});
      if (S(v.status) === 'planned' && !v.mapping) {         // Build mode: no plan step - the three full looks start now
        try { await api('POST', `/api/sites/${enc(v.id)}/plan`, {conversation_id: conv}); } catch (e) { toast(e.message, true); }
      }
      go('#/site/' + enc(S(v.id)));
    } catch (e) {
      api('DELETE', `/api/conversations/${enc(conv)}`).catch(() => {});
      throw e;
    }
  }

  async function readDesign(f, kind) {
    const out = f.querySelector('[data-out]'); out.innerHTML = '<p class="mut sm">Reading…</p>';
    let res;
    if (kind === 'old') {
      const url = S(f.url.value).trim(); if (!url) { out.innerHTML = ''; return toast('Write the address first.', true); }
      res = await api('POST', '/api/site-design/read', {source: 'site', url}, {raw: true}).then(async r => ({ok: true, data: await r.json()}))
        .catch(e => { let x = {}; try { x = JSON.parse(e.message); } catch {} return {ok: false, data: x, msg: S(x.detail || x.error) || e.message}; });
    } else {
      const file = f.file.files?.[0]; if (!file) { out.innerHTML = ''; return toast('Choose a picture first.', true); }
      const fd = new FormData(); fd.append('file', file);
      res = await api('POST', '/api/site-design/read', undefined, {form: fd}).then(data => ({ok: true, data})).catch(e => ({ok: false, msg: e.message}));
    }
    if (!res.ok) {
      const p = M(res.data?.proof);
      out.innerHTML = p.txt_value ? `<div class="launch"><b>First show the site is yours.</b><p class="sm">Add one of these, then press Read my site again.</p>
          <div class="kv"><span>DNS TXT record</span><code class="ell">${esc(S(p.txt_name))} = ${esc(S(p.txt_value))}</code></div>
          <div class="kv"><span>Or in the home page &lt;head&gt;</span><code class="ell">${esc(S(p.meta))}</code></div></div>`
        : `<p class="li bad">${esc(res.msg || 'Could not read it.')}</p>`;
      return;
    }
    const r = res.data;
    out.innerHTML = `<div class="launch"><p class="sm">${esc(S(r.say))}</p><div class="inl" style="justify-content:flex-end">
      ${kind === 'old' ? `<button class="b" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">New layout, my content</button>
        <button class="b pri" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="1">Keep my pages and order</button>`
        : `<button class="b pri" type="button" data-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">Use this design</button>`}</div></div>`;
  }

  /* ================= plan mode: a plan written from her words ================= */
  async function openPlan(id) {
    CARD = await api('GET', `/api/site-architect/${enc(id)}`);
    if (S(CARD.status) === 'built' && CARD.site) {
      const site = SITES.find(x => S(x.number) === S(CARD.site));
      if (site) return go('#/site/' + enc(S(site.id)));
    }
    const words = store.get('hoola.ws.spec.words.' + id);
    const log = (() => { try { return JSON.parse(sessionStorage.getItem('hoola.ws.spec.log.' + id) || '[]'); } catch { return []; } })();
    APP.innerHTML = `<div class="wsp">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a>
        <span class="pname">${esc(S(CARD.name) || 'New website')}</span>${pill('Plan mode · nothing built yet', 'v')}<span class="sp"></span>
        <a class="b ghost" href="#/sites">All websites</a></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this plan">
          <div class="msgs" id="wsPlanMsgs" aria-live="polite">
            ${words ? `<div class="me">${esc(words)}</div>` : ''}
            <div class="step">${tick}Plan written from your words · on the right</div>
            ${CARD.summary ? `<div class="ho"><p>${esc(S(CARD.summary))}</p></div>` : ''}
            ${L(CARD.questions).length ? `<div class="ho"><p>Before you build, tell me if you can:</p><ul>${L(CARD.questions).map(q => `<li>${esc(S(q))}</li>`).join('')}</ul></div>` : ''}
            ${log.map(x => `<div class="me">${esc(S(x.me))}</div><div class="step">${tick}${esc(S(x.done))}</div>`).join('')}
          </div>
          <form class="comp" data-form="revise"><label for="wsRev" class="sr">Change the plan</label>
            <textarea id="wsRev" rows="2" maxlength="2000" placeholder="Change the plan: e.g. teachers also mark attendance on the phone…"></textarea>
            <div class="cbar"><span class="mut sm">Plan mode · nothing is built until you say so</span><span class="sp"></span><button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" aria-label="Plan">
          <div class="ptop"><nav class="views" aria-label="Views"><button type="button" aria-current="page">Plan</button><button type="button" disabled>Preview</button><button type="button" disabled>Code</button></nav></div>
          <div class="stage">${planDoc(CARD, words)}</div>
        </section>
      </div></div>`;
    document.title = `${S(CARD.name) || 'Plan'} · Hoola Web Studio`;
    const m = $('#wsPlanMsgs'); if (m) m.scrollTop = m.scrollHeight;
  }

  /* v0.708 the plan as a real architecture document: every page with its own sections, every journey step by step */
  const FOR = {public: 'Everyone', member: 'After sign-in', staff: 'Staff'};
  function depthLine(c) {
    const d = M(c.depth); if (!Number(d.total)) return '';
    const kind = S(c.kind).replace(/_/g, ' ');
    return `<section class="depth" data-depth><p class="sm"><b>${esc(kind ? kind[0].toUpperCase() + kind.slice(1) : 'Website')}</b> · ${esc(S(c.complexity) || 'simple')} plan · ${esc(S(d.passed))}/${esc(S(d.total))} architecture checks passed</p>
      ${L(d.gaps).length ? `<ul class="gaps">${L(d.gaps).map(x => `<li>Still thin: ${esc(S(x))}</li>`).join('')}</ul>` : ''}</section>`;
  }
  function modBody(m) {
    if (S(m.key) === 'pages' && L(m.items).length) {
      return `<ul>${L(m.lines).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul>
        <div class="pgs">${L(m.items).map(x => `<div class="pg" data-page><div class="pgh"><b>${esc(S(x.title))}</b>${x.main ? pill('Main screen', 'ok') : ''}${pill(FOR[S(x.for)] || 'Everyone', S(x.for) === 'public' ? '' : 'v')}</div>
          ${x.sub ? `<p class="sm mut">${esc(S(x.sub))}</p>` : ''}
          ${L(x.lines).length ? `<ol class="secs">${L(x.lines).map(y => `<li>${esc(S(y))}</li>`).join('')}</ol>` : ''}</div>`).join('')}</div>`;
    }
    if (S(m.key) === 'flows' && L(m.items).length) {
      return `<div class="pgs">${L(m.items).map(x => `<div class="pg" data-flow><div class="pgh"><b>${esc(S(x.title))}</b>${pill(S(x.sub), '')}</div>
        <ol class="secs">${L(x.steps).map(y => `<li>${esc(S(y))}</li>`).join('')}</ol></div>`).join('')}</div>`;
    }
    return `<ul>${L(m.lines).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul>`;
  }

  function planDoc(c, words) {
    const mods = L(c.modules);
    return `<article class="doc">
      <div>${pill(`Plan ${S(c.number)}`, '')}<h2 style="margin-top:10px">${esc(S(c.name) || 'Your website')}</h2></div>
      ${words ? `<p class="quote">"${esc(words)}"</p>` : ''}
      ${c.summary ? `<section><h3>What I will build</h3><p>${esc(S(c.summary))}</p></section>` : ''}
      ${depthLine(c)}
      ${mods.map(m => `<section data-mod="${esc(S(m.key))}"><h3>${esc(S(m.title))}${m.ready === false ? ` ${pill('Needs a fix', 'warn')}` : ''}</h3>
        ${modBody(m)}</section>`).join('')}
      ${L(c.warnings).length ? `<section><h3>Worth checking</h3><ul>${L(c.warnings).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul></section>` : ''}
      ${L(c.questions).length ? `<section><h3>Open questions</h3><ul>${L(c.questions).map(x => `<li>${esc(S(x))}</li>`).join('')}</ul></section>` : ''}
      <div class="dfoot"><span class="mut sm sp">Next: three complete looks of this whole site to click through. Only your pick is built.</span>
        ${S(c.status) === 'built' ? `<a class="b pri" href="#/sites">Open the website</a>` : `<button class="b pri" type="button" data-act="approve-plan" data-hash="${esc(S(c.hash))}">Build this plan</button>`}</div>
    </article>`;
  }

  /* ================= workspace ================= */
  async function openSite(id, view) {
    const v = await api('GET', `/api/sites/${enc(id)}`);
    const same = CUR && CUR.id === v.id;
    CUR = v; VIEW = view || (same ? VIEW : 'preview');
    if (!same) { LOOK = Math.max(0, Number(M(v).chosen_look) || 0); DEVICE = 'pc'; LIVE.justDone = null; LIVE.compare = false; LIVE.from = 0; LIVE.page = 'home'; }
    startLive(S(v.id));
    drawShell();
    openThread();
    if (!same) { GALTI.site = S(v.id); GALTI.errors = []; GALTI.q = []; }
    loadErrors();                                        // v0.802 GALTI PAKDO
  }

  const VIEWS = [['preview', 'Preview'], ['code', 'Code'], ['drafts', 'Drafts'], ['cloud', 'Cloud'], ['integrations', 'Integrations'], ['health', 'Health'], ['settings', 'Settings']];
  function drawShell() {
    const v = CUR, mode = chatMode();
    APP.innerHTML = `<div class="wsp">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true"><span></span></div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">${esc(name(v))}</span>${v.draft_of ? pill('Draft · ' + S(v.draft_name), 'v') : ''}<button class="ib" type="button" data-menu="${esc(S(v.id))}" aria-label="Project options" title="Rename, star, delete">${ico('chev', 16)}</button>${v.name_by === 'hoola' ? `<button class="namedby" type="button" data-menu="${esc(S(v.id))}" title="Hoola picked this brand name. Tap to rename it.">✦ Named by Hoola</button>` : ''}<span id="wsPill">${statusPill(v)}</span><span class="sp"></span>
        <span class="tsave">Every change is saved as a version</span>
        <button class="b" type="button" data-view="history">${ico('hist', 15)}<span>History</span></button>
        ${v.draft_of ? `<a class="b" href="#/site/${enc(S(v.draft_of))}">Back to the website</a><button class="b dark" type="button" data-view="drafts"><span>Accept or discard</span></button>`
          : '<button class="b dark" type="button" data-view="publish"><span>Publish</span></button>'}</header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this website">
          <div class="msgs" id="wsMsgs" aria-live="polite"></div>
          <div id="wsState" style="padding:0 18px"></div>
          <div id="wsErr" style="padding:0 18px" aria-live="polite"></div>
          <form class="comp" data-form="thread"><label for="wsTh" class="sr">Message Hoola about this website</label>
            <div class="pills" id="wsPills" hidden></div>
            <div class="tray" id="wsTray" hidden></div>
            <textarea id="wsTh" rows="2" maxlength="4000" placeholder="${esc(MODE_PH[mode])}"></textarea>
            <div class="cbar">
              <button class="ib" type="button" data-act="attach" aria-label="Attach files or photos" title="Attach files or photos">${ico('clip', 16)}</button>
              <input type="file" id="wsFile" multiple hidden>
              <button class="ib" type="button" data-act="select" aria-label="Select on the page" title="Select on the page">${ico('sel', 16)}</button>
              <div class="seg" role="group" aria-label="Mode (Alt+P)" title="Build changes the site · Plan writes a plan first · Chat only talks (Alt+P)">${MODES.map(m => `<button type="button" data-cmode="${m}" aria-pressed="${mode === m}">${MODE_NAME[m]}</button>`).join('')}</div>
              <span class="sp"></span><button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
        </section>
        <section class="pane" id="wsPane" aria-label="Website"></section>
      </div></div>`;
    document.title = `${name(v)} · Hoola Web Studio`;
    drawState(); drawPane();
  }

  /* ---------- v0.655 the job's real steps with live timers (server clock, corrected for this screen) ---------- */
  let CLOCK = 0, TICK = null, ACT_OPEN = false;
  const nowS = () => Date.now() / 1000 + CLOCK;
  const dur = s => { s = Math.max(0, Math.round(s)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s` : `${Math.floor(s / 3600)}h ${String(Math.floor(s / 60) % 60).padStart(2, '0')}m`; };
  const ACTV = v => { const a = M(v && v.activity); if (a.now) CLOCK = Number(a.now) - Date.now() / 1000; return a; };
  function actSig(v) { const a = M(v && v.activity), st = L(a.steps), l = st[st.length - 1] || {}; return [st.length, l.state, l.done, l.note, a.ended].join('|'); }
  function stepRow(x) {
    const run = x.state === 'run', bad = x.state === 'error';
    const ic = run ? '<span class="spin" aria-hidden="true"></span>' : bad ? `<span class="xmark" aria-hidden="true">!</span>` : `<span class="tick" aria-hidden="true">${ico('check', 11)}</span>`;
    const cnt = Number(x.total) ? `<span class="cnt">${esc(S(x.done || 0))}/${esc(S(x.total))}</span>` : '';
    const t = run ? `<span class="tm" data-t0="${Number(x.at)}"></span>` : `<span class="tm">${dur((Number(x.end) || Number(x.at)) - Number(x.at))}</span>`;
    return `<li class="${run ? 'run' : bad ? 'bad' : 'ok'}">${ic}<div class="sl"><span class="ell">${esc(pastLabel(x.label, x.state))}</span>${x.note ? `<span class="sn ell">${esc(S(x.note))}</span>` : ''}</div>${cnt}${t}</li>`;
  }
  function stepList(a, last) {
    const st = L(a.steps).filter(x => !x.final || x.state === 'error');
    return `<ol class="acts" aria-label="What Hoola is doing">${(last ? st.slice(-last) : st).map(stepRow).join('')}</ol>`;
  }
  function actPanel(v) {
    const a = ACTV(v), st = L(a.steps); if (!st.length) return '';
    const cur = [...st].reverse().find(x => x.state === 'run');
    const pct = cur && Number(cur.total) ? Math.round(100 * Number(cur.done || 0) / Number(cur.total)) : null;
    return `<div class="acthead"><span class="mut sm">Working for <b class="tm" data-t0="${Number(a.started)}"></b></span><span class="sp"></span>
        ${cur ? `<span class="mut sm ell">Step ${st.indexOf(cur) + 1}${pct !== null ? ` · ${pct}% of this step` : ''}</span>` : ''}</div>
      <div class="prog${pct === null ? ' ind' : ''}" role="progressbar" aria-label="Progress of this step"${pct === null ? '' : ` aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"`}><i style="width:${pct === null ? 30 : Math.max(3, pct)}%"></i></div>
      ${stepList(a)}`;
  }
  function tickClocks() {
    APP.querySelectorAll('[data-t0]').forEach(e => { const t0 = Number(e.dataset.t0); if (t0) e.textContent = dur(nowS() - t0); });
  }
  function startTick() { if (!TICK) { TICK = setInterval(tickClocks, 1000); } tickClocks(); }

  function drawState() {
    const box = $('#wsState'); if (!box || !CUR) return;
    const v = CUR, b = M(v.board), a = ACTV(v), st = L(a.steps);
    if (WORKING(v)) {                    // v0.667 the live work card: what is running, every step's own time, the whole clock
      const cur = [...st].reverse().find(x => x.state === 'run');
      const title = S(v.status) === 'looks' ? 'Making three designs' : S(v.status) === 'checking' ? 'Checking every page'
        : hasVersion(v) ? 'Updating your website' : 'Building your website';
      const stepPct = cur && Number(cur.total) ? Math.round(100 * Number(cur.done || 0) / Number(cur.total)) : null;
      const sub = cur ? `Step ${st.indexOf(cur) + 1}${stepPct !== null ? ` · ${stepPct}% of this step` : ''} · ${S(cur.label)}` : S(b.now) || S(v.say) || 'Starting…';
      const pct = Number(b.pct) ? Math.max(3, Math.min(100, Number(b.pct))) : stepPct;
      const writingN = LIVE.site === S(v.id) ? Object.values(LIVE.slots).filter(writing).length : 0;
      const shown = stepList(a, 6);
      box.innerHTML = `<div class="chatact wcard"><div class="step whead"><span class="spin" aria-hidden="true"></span><span class="wt"><b>${esc(title)}</b><span>${esc(sub)}</span></span>
          ${a.started ? `<span class="tm" data-t0="${Number(a.started)}"></span>` : ''}</div>
        <div class="prog${pct === null ? ' ind' : ''}" role="progressbar" aria-label="Progress"${pct === null ? '' : ` aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"`}><i style="width:${pct === null ? 30 : pct}%"></i></div>
        ${st.length ? shown : ''}
        ${st.length > 6 ? `<details class="actd"${ACT_OPEN ? ' open' : ''}><summary>All ${st.length} steps so far</summary>${stepList(a)}</details>` : ''}
        <div class="wfoot"><span class="ell">${writingN > 1 ? `${writingN} parts writing at once` : writingN === 1 ? '1 part writing now' : 'You can keep chatting; changes wait for this build'}</span><span class="sp"></span>
          ${['building', 'checking'].includes(S(v.status)) ? `<button class="b sm" type="button" data-act="stop">${ico('pause', 14)}Pause</button>` : ''}</div></div>`;
    } else if (st.length && a.ended) {
      const ok = !st.some(x => x.state === 'error'), chk = M(v.checks);
      const fresh = nowS() - Number(a.ended) < 3600 && ok && S(v.status) === 'ready' && hasVersion(v);
      box.innerHTML = `<details class="actd done"${ACT_OPEN ? ' open' : ''}><summary>${ok ? `<span class="tick" aria-hidden="true">${ico('check', 11)}</span>` : '<span class="xmark" aria-hidden="true">!</span>'}<span><b>${ok ? 'Worked' : 'Stopped'} for ${dur(Number(a.ended) - Number(a.started))} · ${st.filter(x => !x.final).length} steps</b></span><span class="chev" aria-hidden="true">${ico('chev', 14)}</span></summary>${stepList(a)}</details>
        ${fresh ? `<div class="vcard"><span class="vth" aria-hidden="true"></span><span class="vt"><b>Version ${esc(S(v.version))} is ready</b><span>${S(chk.tier) === 'quick' ? `Quick check of ${esc(L(chk.checked_pages).join(', ') || 'this page')}${chk.quick_s != null ? ` in ${esc(S(chk.quick_s))}s` : ''} · the full check runs before going live` : chk.passed === true ? 'Every check passed · not live until you publish' : 'not live until you publish'}</span></span>
          <button class="b dark sm" type="button" data-view="publish">${ico('globe', 14)}Go live…</button></div>
          <div class="sugg"><span>Next, you could</span>${['Add a shop with cart', 'Add online payments', 'Add a Hindi version'].map(t => `<button type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}`;
    } else box.innerHTML = '';
    const p = $('#wsPill'); if (p) p.innerHTML = statusPill(v);
    startTick();
  }
  const OPEN_T = new Set();
  APP.addEventListener('toggle', e => {
    const t = e.target; if (!t.matches?.('details.actd')) return;
    if (t.dataset.k) { if (t.open) OPEN_T.add(t.dataset.k); else OPEN_T.delete(t.dataset.k); } else ACT_OPEN = t.open;
  }, true);
  function drawActivity() {
    const el = $('#wsAct'); if (el && CUR) el.innerHTML = actPanel(CUR);
    drawState();
  }

  function viewsBar(extra = '') {
    const looks = S(CUR.status) === 'looks' && L(CUR.looks).length;
    return `<div class="ptop"><nav class="views" aria-label="Views">${VIEWS.map(([k, n]) => `<button type="button" data-view="${k}" ${VIEW === k ? 'aria-current="page"' : ''}>${esc(k === 'preview' && looks ? '3 looks' : n)}</button>`).join('')}</nav>${extra}</div>`;
  }
  const devSeg = () => `<div class="seg" role="group" aria-label="Device">${Object.entries(DEV).map(([k, d]) => `<button type="button" data-dev="${k}" aria-pressed="${DEVICE === k}" aria-label="${d[2]}" title="${d[2]}">${ico(k === 'pc' ? 'pc' : k === 'tablet' ? 'tab' : 'phone', 16)}</button>`).join('')}</div>`;
  const frame = (src, title) => `<div class="frame ${DEVICE}" data-w="${DEV[DEVICE][0]}" data-h="${DEV[DEVICE][1]}"><iframe title="${esc(title)}" sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>`;

  function drawPane() {
    const pane = $('#wsPane'); if (!pane || !CUR) return;
    stopPoll();
    const fn = {preview, code, cloud, integrations, health, settings, history: historyView, drafts: draftsView, publish, details: detailsView, plans: planView}[VIEW] || preview;
    if (fn !== preview) delete pane.dataset.live;
    fn(pane, CUR);
    if (WORKING(CUR)) startPoll();
  }

  function fit() {
    const fs = [...APP.querySelectorAll('.frame')]; if (!fs.length) return;
    const doit = () => fs.forEach(f => {
      const fr = f.querySelector('iframe'); if (!fr) return;
      const w = Number(f.dataset.w), h = Number(f.dataset.h), k = Math.min(1, (f.clientWidth || w) / w);
      fr.style.width = w + 'px'; fr.style.height = h + 'px'; fr.style.transform = `scale(${k})`;
      f.style.height = Math.round(h * k) + 'px';
    });
    doit();
    if (window.ResizeObserver) { RO?.disconnect(); RO = new ResizeObserver(doit); fs.forEach(f => RO.observe(f)); }
  }

  function preview(pane, v) {
    const st = S(v.status), b = M(v.board);
    if (WORKING(v) && !EDIT && !v.mapping && st !== 'planned') return liveView(pane, v);
    if (pane.dataset.live && LIVE.from && st === 'ready' && Number(v.version) > LIVE.from) { LIVE.justDone = {site: S(v.id), from: LIVE.from, to: Number(v.version)}; LIVE.compare = false; }
    if (pane.dataset.live) LIVE.from = 0;
    delete pane.dataset.live;
    if (st === 'planned' && !v.mapping) {
      const pages = L(M(v.plan).pages);
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>The plan is ready</h2><p class="mut">${esc(S(v.say))}</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${pages.map(p => pill(S(p.title))).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b ghost bad" type="button" data-act="delete">Delete</button><button class="b pri" type="button" data-act="approve">Make the 3 looks</button></div></div></div>`;
      return;
    }
    if (st === 'looks' && L(v.looks).length) return looksView(pane, v);
    if (WORKING(v) && !hasVersion(v)) {
      const t = v.mapping ? 'Planning every page of a big site' : st === 'looks' ? 'Making three complete looks' : st === 'checking' ? 'Checking every page' : 'Building your website';
      const note = st === 'looks' ? 'Every page of your site is written once, then shown in three different designs. You click through all of them before anything is built.'
        : 'Each page is written, put together and checked on a phone and a computer.';
      const pct = Math.max(4, Math.min(100, Number(b.pct) || 0));
      const acts = actPanel(v);
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><div style="display:flex;align-items:center;gap:10px"><h2 class="sp">${esc(t)}</h2><span class="spin" aria-hidden="true"></span></div>
        <p class="mut">${esc(note)}</p>
        <div id="wsAct">${acts || `<div class="prog" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}" aria-label="Progress"><i style="width:${pct}%"></i></div>
        <p class="mut sm">${esc(S(b.now) || S(v.say) || 'Working…')}</p>`}</div>
        ${['building', 'checking'].includes(st) ? '<div class="inl" style="justify-content:flex-end"><button class="b" type="button" data-act="stop">Pause</button></div>' : ''}</div></div>`;
      startTick();
      return;
    }
    const src = S(v.preview) + (EDIT ? '__edit/' : '');
    const top = `<div class="url">${ico('lock', 14)}<span>${EDIT ? 'Edit mode · ' : ''}preview</span></div>${devSeg()}
      <button class="ib" type="button" data-act="reload" aria-label="Reload preview">${ico('reload', 16)}</button>
      ${v.preview ? `<a class="ib" href="${esc(S(v.preview))}" target="_blank" rel="noopener" aria-label="Open in a new tab">${ico('ext', 16)}</a>` : ''}`;
    const jd = LIVE.justDone && LIVE.justDone.site === S(v.id) ? LIVE.justDone : null;
    if (jd && LIVE.compare) return compareView(pane, v, jd, top);
    pane.innerHTML = viewsBar(top)
      + (jd ? `<div class="edbar okbar"><b>New version v${esc(S(jd.to))} is ready</b><span class="ell">You are looking at it now. Nothing is live until you publish.</span><span class="sp"></span>
          <button class="b sm" type="button" data-act="compare">Before / after</button><button class="ib" type="button" data-act="jd-close" aria-label="Close">×</button></div>` : '')

      + (st === 'failed' || st === 'stopped' ? `<div class="edbar"><b>${st === 'failed' ? 'The last build stopped on a problem' : 'Building is paused'}</b><span class="ell">${esc(S(v.error))}</span><span class="sp"></span><button class="b sm pri" type="button" data-act="resume">${st === 'failed' ? 'Try again' : 'Continue'}</button></div>` : '')
      + (WORKING(v) ? `<div class="edbar"><span class="spin" aria-hidden="true"></span><span class="ell">${esc(S(b.now) || 'Updating your website…')}</span></div>` : '')
      + '<div class="perrbar" id="wsPerr" role="alert" hidden></div>'
      + `<div class="stage">${v.preview ? frame(src, 'Website preview') : '<div class="empty">No preview yet.</div>'}</div>`
      + (EDIT ? '<div id="wsYW"></div>' : '');
    fit();
    drawErrors();
    if (EDIT) ywDraw();                                  // v0.795 YEH WALA: the preview toolbar, style panel, draw layer
  }

  function looksView(pane, v) {
    const looks = L(v.looks);
    if (LOOK >= looks.length) LOOK = 0;
    const lk = M(looks[LOOK]);
    const est = M(v.estimate);
    pane.innerHTML = viewsBar(`<span class="sp"></span>${devSeg()}`)
      + `<div class="ptop"><div class="lks" role="group" aria-label="Look">${looks.map((x, i) => `<button type="button" data-look="${i}" aria-pressed="${i === LOOK}">
          <span class="sw" aria-hidden="true">${L(x.colors).map(HEX).filter(Boolean).slice(0, 4).map(c => `<i style="background:${c}"></i>`).join('')}</span><span>${i + 1} · ${esc(S(x.label))}</span></button>`).join('')}</div>
        <span class="sp"></span><span class="mut sm">${lk.full ? 'The whole site · every page works' : 'The top of the home page (the whole site is made after you pick)'}</span></div>`
      + `<div class="stage">${lk.preview ? frame(S(lk.preview), `Look ${LOOK + 1}`) : '<div class="empty">This look has no preview.</div>'}</div>`
      + `<div class="choose"><span class="sm"><b>${LOOK + 1} · ${esc(S(lk.label))}</b>${lk.concept ? ` <span class="mut">· ${esc(S(lk.concept))}</span>` : ''}</span><span class="sp"></span>
          ${est.say ? `<span class="mut sm">${esc(S(est.say))}</span>` : ''}<button class="b pri" type="button" data-act="pick-look">Build in this look</button></div>`;
    fit();
  }

  /* ================= v0.795 YEH WALA (L5): point at the page instead of describing it ================= */
  const YW = {mode: 'select', sel: [], tokens: {}, comments: [], strokes: [], notes: [], pen: 'pen', min: false, site: '',
    pos: (() => { try { return localStorage.getItem('hoola.ws.ptb') || 'center'; } catch { return 'center'; } })(), page: '', wait: null, cmOpen: false, el: null};
  const PT = [['select', 'S', 'Select', 'sel'], ['text', 'T', 'Text', 'edit'], ['draw', 'D', 'Draw', 'pen'], ['comment', 'C', 'Comment', 'note']];
  const ywFrame = () => APP.querySelector('.frame iframe');
  function ywPost(m) { const f = ywFrame(); if (f && f.contentWindow) f.contentWindow.postMessage({hoola: 'edit-cmd', ...m}, '*'); }
  function ywPins() {
    let n = 0;
    return L(YW.comments).map(c => ({k: S(c.k), e: S(c.e), n: Number(c.n) || ++n, done: S(c.status) === 'resolved'}));
  }
  function ywSync() {
    ywPost({mode: YW.mode === 'draw' ? 'view' : YW.mode});
    ywPost({t: 'selected', items: YW.sel});
    ywPost({t: 'pins', pins: ywPins()});
  }
  function drawPills() {
    const p = $('#wsPills'); if (!p) return;
    p.hidden = !YW.sel.length;
    p.innerHTML = YW.sel.map((x, i) => `<span class="pill2" title="${esc(x.name)}">${ico('sel', 12)}<span class="ell">${esc(x.label || x.name || 'Selected part')}</span><button type="button" class="x" data-act="pill-x" data-i="${i}" aria-label="Remove ${esc(x.label || x.name)}">×</button></span>`).join('')
      + (YW.sel.length ? '<span class="mut sm">Your next message is about these</span>' : '');
  }
  function ywDraw() {
    const host = $('#wsYW'); if (!host || !CUR) return;
    YW.site = S(CUR.id);
    const open = L(YW.comments).filter(c => S(c.status) === 'open').length;
    host.innerHTML = `<div class="ptb pos-${esc(YW.pos)}${YW.min ? ' min' : ''}" role="toolbar" aria-label="Preview tools">
        ${YW.min ? `<button type="button" class="ptmax" data-act="pt-min" aria-label="Show the preview tools">${ico('sel', 16)}</button>` : `
        <span class="grip" aria-hidden="true" title="Drag to move">⋮⋮</span>
        ${PT.map(([m, key, label, ic]) => `<button type="button" data-act="pt-mode" data-m="${m}" aria-pressed="${YW.mode === m}" title="${label} (${key})">${ico(ic, 16)}<span>${label}</span><kbd>${key}</kbd></button>`).join('')}
        <span class="ptsep" aria-hidden="true"></span>
        <button type="button" data-act="pt-cm" aria-pressed="${YW.cmOpen}" title="Comments for your team">${ico('note', 16)}<span>${open || ''}</span></button>
        <button type="button" data-act="undo" title="Undo your last change">${ico('back', 16)}</button>
        <button type="button" class="ptdone" data-act="edit-done">Done</button>
        <button type="button" data-act="pt-min" aria-label="Hide the preview tools" title="Hide">–</button>`}</div>
      <div class="ptnote" aria-live="polite">${esc({select: 'Select: click a part of the page · Ctrl / Shift adds more · the style panel is free', text: 'Text: click any words and type · free, no AI', draw: 'Draw: mark the page, add a note, send it to Hoola', comment: 'Comment: click the part your note is about · for your team, not sent to Hoola'}[YW.mode])}</div>
      <div id="wsStyle"></div><div id="wsCm"></div><div id="wsDraw"></div>`;
    const f = APP.querySelector('.frame');
    if (f && !f.querySelector('canvas.drawc')) { const c = document.createElement('canvas'); c.className = 'drawc'; c.setAttribute('aria-label', 'Draw on the page'); f.appendChild(c); ywCanvas(c); }
    const cv = f?.querySelector('canvas.drawc'); if (cv) cv.hidden = YW.mode !== 'draw';
    ywDrag(host.querySelector('.ptb'));
    ywPanel(); ywCmList(); ywDrawBar(); ywPaint();
  }
  function ywDrag(bar) {
    const g = bar?.querySelector('.grip'); if (!g) return;
    g.addEventListener('pointerdown', ev => {
      ev.preventDefault();
      const host = bar.parentElement.getBoundingClientRect(), w = bar.offsetWidth;
      bar.classList.add('dragging');
      const move = e2 => { bar.style.left = Math.max(8, Math.min(host.width - w - 8, e2.clientX - host.left - 14)) + 'px'; bar.style.transform = 'none'; };
      const up = e2 => {
        removeEventListener('pointermove', move); removeEventListener('pointerup', up);
        const x = (e2.clientX - host.left) / host.width;
        YW.pos = x < 0.34 ? 'left' : x > 0.66 ? 'right' : 'center';            // snap to a third
        try { localStorage.setItem('hoola.ws.ptb', YW.pos); } catch {}
        bar.classList.remove('dragging'); bar.style.left = ''; bar.style.transform = '';
        bar.className = bar.className.replace(/pos-\w+/, 'pos-' + YW.pos);
      };
      addEventListener('pointermove', move); addEventListener('pointerup', up);
    });
  }
  function setPT(m) {
    if (!PT.some(x => x[0] === m)) return;
    YW.mode = m; if (m !== 'select') { YW.sel = YW.sel; }
    ywSync(); ywDraw();
  }
  async function ywPanel() {
    const box = $('#wsStyle'); if (!box) return;
    if (!EDIT || YW.mode !== 'select' || YW.sel.length !== 1) { box.innerHTML = ''; YW.el = null; return; }
    const one = YW.sel[0];
    let el;
    try { el = await api('GET', `/api/sites/${enc(CUR.id)}/element?k=${encodeURIComponent(one.k)}&e=${encodeURIComponent(one.e)}`); }
    catch (er) { box.innerHTML = `<div class="stylep"><p class="li bad">${esc(er.message)}</p></div>`; return; }
    if (YW.sel.length !== 1 || YW.sel[0].e !== one.e || YW.sel[0].k !== one.k) return;
    YW.el = el; one.label = S(el.label); drawPills();
    const t = YW.tokens, has = M(el.styles);
    const sw = (prop, val, col, label) => `<button type="button" class="sw2${has[prop] === val ? ' on' : ''}" data-act="sty" data-p="${prop}" data-v="${val}" title="${esc(label)}" aria-label="${esc(label)}" aria-pressed="${has[prop] === val}"><i style="background:${HEX(col) || 'transparent'}"></i></button>`;
    const chip = (prop, val, label) => `<button type="button" class="chip2${has[prop] === val ? ' on' : ''}" data-act="sty" data-p="${prop}" data-v="${val}" aria-pressed="${has[prop] === val}">${esc(label)}</button>`;
    const reset = prop => has[prop] ? `<button type="button" class="chip2 ghost" data-act="sty" data-p="${prop}" data-v="default">As designed</button>` : '';
    const textual = !['img', 'picture', 'video'].includes(S(el.tag));
    box.innerHTML = `<aside class="stylep" aria-label="Style">
      <div class="sph"><b class="ell">${esc(S(el.label))}</b><span class="pfree">Free · no AI</span></div>
      ${textual ? `<div class="spr"><span>Text colour</span><div class="sws">${sw('color', 'primary', t.primary, 'Brand colour')}${sw('color', 'accent', t.accent, 'Accent')}${sw('color', 'ink', t.ink, 'Text colour')}${sw('color', 'muted', t.ink, 'Soft text')}${sw('color', 'bg', t.bg, 'Page colour')}${reset('color')}</div></div>` : ''}
      <div class="spr"><span>Background</span><div class="sws">${sw('bg', 'primary', t.primary, 'Brand colour')}${sw('bg', 'accent', t.accent, 'Accent')}${sw('bg', 'surface', t.surface, 'Soft panel')}${sw('bg', 'ink', t.ink, 'Dark')}${chip('bg', 'none', 'None')}${reset('bg')}</div></div>
      ${textual ? `<div class="spr"><span>Size</span><div class="sws">${chip('size', 'm1', 'Smaller')}${chip('size', '1', '+1')}${chip('size', '2', '+2')}${chip('size', '3', '+3')}${reset('size')}</div></div>
      <div class="spr"><span>Weight</span><div class="sws">${chip('weight', '400', 'Regular')}${chip('weight', '600', 'Semi-bold')}${chip('weight', '700', 'Bold')}${reset('weight')}</div></div>
      <div class="spr"><span>Align</span><div class="sws">${chip('align', 'left', 'Left')}${chip('align', 'center', 'Centre')}${chip('align', 'right', 'Right')}${reset('align')}</div></div>` : ''}
      <div class="spr"><span>Padding</span><div class="sws">${['0', '1', '2', '3', '4'].map(n => chip('space', n, n)).join('')}${reset('space')}</div></div>
      <div class="spr"><span>Corners</span><div class="sws">${[['0', 'Square'], ['sm', 'S'], ['md', 'M'], ['lg', 'L'], ['full', 'Pill']].map(([v2, l2]) => chip('radius', v2, l2)).join('')}${reset('radius')}</div></div>
      <p class="mut sm">Only your site's own colours. Every change is a version you can Undo. For anything else, write it in the chat: your message will be about this part.</p></aside>`;
  }
  async function ywLoadComments() {
    if (!CUR) return;
    try { YW.comments = L((await api('GET', `/api/sites/${enc(CUR.id)}/comments`)).comments); } catch { YW.comments = []; }
    if (EDIT) { ywPost({t: 'pins', pins: ywPins()}); ywCmList(); const b = APP.querySelector('[data-act="pt-cm"] span'); if (b) b.textContent = L(YW.comments).filter(c => S(c.status) === 'open').length || ''; }
  }
  async function ywComment(k, e, nm) {
    const f = await dialog('Comment for your team', `<p class="mut sm">On ${esc(nm || 'this part')} · not sent to Hoola</p><label class="fld">Comment<textarea class="in" name="text" rows="3" maxlength="1000" required></textarea></label>`);
    if (!f) return;
    const text = S(f.get('text')).trim(); if (!text) return;
    try { await api('POST', `/api/sites/${enc(CUR.id)}/comments`, {k, e, text}); YW.cmOpen = true; await ywLoadComments(); toast('Comment added.'); }
    catch (er) { toast(er.message, true); }
  }
  function ywCmList() {
    const box = $('#wsCm'); if (!box) return;
    if (!YW.cmOpen || YW.mode === 'draw') { box.innerHTML = ''; return; }      // drawing gets the whole page
    const cs = L(YW.comments);
    box.innerHTML = `<aside class="cmtp" aria-label="Comments"><div class="sph"><b>Comments</b><span class="mut sm">${cs.filter(c => S(c.status) === 'open').length} open</span><span class="sp"></span><button type="button" class="ib" data-act="pt-cm" aria-label="Close comments">×</button></div>
      ${cs.length ? cs.map(c => `<div class="cmi${S(c.status) === 'resolved' ? ' done' : ''}"><span class="cmn">${esc(S(c.n))}</span><div class="cmb"><span class="mut sm ell">${esc(S(c.label))}</span><p>${esc(S(c.text))}</p>
          <span class="mut sm">${esc(S(c.author))}</span><div class="inl">${S(c.status) === 'open' ? `<button type="button" class="b sm" data-act="cm-res" data-id="${esc(S(c.id))}">Resolve</button>` : `<button type="button" class="b sm" data-act="cm-open" data-id="${esc(S(c.id))}">Reopen</button>`}<button type="button" class="b sm ghost" data-act="cm-del" data-id="${esc(S(c.id))}">Delete</button></div></div></div>`).join('')
        : '<p class="mut sm">No comments yet. Pick Comment, then click a part of the page.</p>'}</aside>`;
  }
  /* ----- Draw: strokes and numbered notes over the frame, sent as a marked-up screenshot ----- */
  function ywCanvas(c) {
    let cur = null;
    const pt = ev => { const r = c.getBoundingClientRect(); return [Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)), Math.max(0, Math.min(1, (ev.clientY - r.top) / r.height))]; };
    c.addEventListener('pointerdown', async ev => {
      if (YW.mode !== 'draw') return;
      ev.preventDefault();
      if (YW.pen === 'note') {
        const p = pt(ev), f = await dialog(`Note ${YW.notes.length + 1}`, '<label class="fld">What should change here?<input class="in" name="text" maxlength="200"></label>');
        if (f) { YW.notes.push({x: p[0], y: p[1], text: S(f.get('text')).trim()}); ywPaint(); ywDrawBar(); }
        return;
      }
      cur = [pt(ev)]; YW.strokes.push(cur); c.setPointerCapture(ev.pointerId); ywPaint();
    });
    c.addEventListener('pointermove', ev => { if (!cur) return; cur.push(pt(ev)); ywPaint(); });
    const end = () => { if (cur) { cur = null; ywDrawBar(); } };
    c.addEventListener('pointerup', end); c.addEventListener('pointercancel', end);
  }
  function ywPaint() {
    const c = APP.querySelector('canvas.drawc'); if (!c) return;
    const r = c.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (!r.width) return;
    c.width = Math.round(r.width * dpr); c.height = Math.round(r.height * dpr);
    const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, r.width, r.height);
    g.strokeStyle = '#6D4AFF'; g.lineWidth = 3; g.lineCap = 'round'; g.lineJoin = 'round';
    YW.strokes.forEach(st => { g.beginPath(); st.forEach(([x, y], i) => i ? g.lineTo(x * r.width, y * r.height) : g.moveTo(x * r.width, y * r.height)); if (st.length === 1) g.lineTo(st[0][0] * r.width + 0.1, st[0][1] * r.height); g.stroke(); });
    YW.notes.forEach((n, i) => { g.fillStyle = '#6D4AFF'; g.beginPath(); g.arc(n.x * r.width, n.y * r.height, 11, 0, 7); g.fill(); g.fillStyle = '#fff'; g.font = '600 12px system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(String(i + 1), n.x * r.width, n.y * r.height); });
  }
  function ywDrawBar() {
    const box = $('#wsDraw'); if (!box) return;
    if (YW.mode !== 'draw') { box.innerHTML = ''; return; }
    const n = YW.strokes.length + YW.notes.length;
    box.innerHTML = `<div class="drawbar"><div class="seg" role="group" aria-label="Draw tool"><button type="button" data-act="dr-pen" aria-pressed="${YW.pen === 'pen'}">${ico('pen', 14)}Pen</button><button type="button" data-act="dr-note" aria-pressed="${YW.pen === 'note'}">${ico('note', 14)}Note</button></div>
      <input class="in" id="wsDrawText" maxlength="600" placeholder="What should change? (optional)" aria-label="What should change">
      <button type="button" class="b sm" data-act="dr-clear"${n ? '' : ' disabled'}>Clear</button>
      <button type="button" class="b sm pri" data-act="dr-send"${n ? '' : ' disabled'}>Send to Hoola</button></div>`;
  }
  function ywWhere() {
    return new Promise(res => { YW.wait = res; ywPost({t: 'where'}); setTimeout(() => { if (YW.wait === res) { YW.wait = null; res({y: 0, page: YW.page}); } }, 900); });
  }
  async function ywSend() {
    const f = APP.querySelector('.frame'); if (!f || !CUR) return;
    const text = S($('#wsDrawText')?.value).trim();
    const w = await ywWhere();
    toast('Taking a screenshot of this page…');
    try {
      const r = await api('POST', `/api/sites/${enc(CUR.id)}/markup`, {page: w.page.replace(/\/$/, '') || 'home', width: Number(f.dataset.w), height: Number(f.dataset.h), y: w.y, strokes: YW.strokes, notes: YW.notes});
      THREAD.files.push({label: 'Marked-up screenshot', kind: 'file', state: 'ok', id: S(r.file_id)}); drawTray();
      YW.strokes = []; YW.notes = []; ywPaint(); ywDrawBar();
      await ask(text || 'Please change what I marked on this screenshot.');
    } catch (er) { toast(er.message, true); }
  }
  async function ywAct(act, b) {
    const d = b.dataset;
    if (act === 'pt-mode') return setPT(d.m);
    if (act === 'pt-min') { YW.min = !YW.min; return ywDraw(); }
    if (act === 'pt-cm') { YW.cmOpen = !YW.cmOpen; if (YW.cmOpen) await ywLoadComments(); return ywDraw(); }
    if (act === 'pill-x') { YW.sel.splice(Number(d.i), 1); drawPills(); ywPost({t: 'selected', items: YW.sel}); return ywPanel(); }
    if (act === 'sty') {
      const one = YW.sel[0]; if (!one) return;
      await editSend({k: one.k, e: one.e, op: 'style', value: JSON.stringify({prop: d.p, value: d.v})});
      return ywPanel();
    }
    if (act === 'cm-res' || act === 'cm-open' || act === 'cm-del') {
      if (act === 'cm-del' && !confirm('Delete this comment?')) return;
      try { await api('POST', `/api/sites/${enc(CUR.id)}/comments/${enc(d.id)}/${act === 'cm-res' ? 'resolved' : act === 'cm-open' ? 'open' : 'deleted'}`, {}); }
      catch (er) { return toast(er.message, true); }
      return ywLoadComments();
    }
    if (act === 'dr-pen' || act === 'dr-note') { YW.pen = act === 'dr-pen' ? 'pen' : 'note'; return ywDrawBar(); }
    if (act === 'dr-clear') { YW.strokes = []; YW.notes = []; ywPaint(); return ywDrawBar(); }
    if (act === 'dr-send') return ywSend();
  }
  addEventListener('keydown', e => {                        // S / T / D / C while the preview tools are open
    if (!EDIT || e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target; if (t && (t.closest('input, textarea, select, [contenteditable]') || t.closest('dialog'))) return;
    const m = {s: 'select', t: 'text', d: 'draw', c: 'comment'}[e.key.toLowerCase()];
    if (m) { e.preventDefault(); setPT(m); }
    else if (e.key === 'Escape' && YW.sel.length) { YW.sel = []; drawPills(); ywPost({t: 'selected', items: []}); ywPanel(); }
  });
  addEventListener('resize', () => { if (EDIT) ywPaint(); });

  /* ================= v0.664 ASLI SAMAY: the website built in front of her ================= */
  const LIVE = {site: '', ctl: null, seq: 0, slots: {}, looks: [], page: 'home', follow: true, code: false, codeKey: '',
    moved: 0, pend: new Set(), timer: null, fin: {}, from: 0, justDone: null, compare: false, retry: null};
  const pageRel = slug => (!slug || slug === 'home') ? '' : S(slug).replace(/^\/+|\/+$/g, '') + '/';
  const liveSrc = (v, page, look) => S(v.preview) + (look >= 0 ? `__build/__look/${look}/` : '__build/' + pageRel(page));
  const writing = s => s.state === 'think' || s.state === 'write';

  function startLive(id) {
    if (LIVE.site === id && LIVE.ctl) return;
    stopLive();
    Object.assign(LIVE, {site: id, seq: 0, slots: {}, looks: [], fin: {}});
    readLive(id);
  }
  function stopLive() { try { LIVE.ctl?.abort(); } catch {} LIVE.ctl = null; clearTimeout(LIVE.retry); LIVE.site = ''; }
  async function readLive(id) {
    const ctl = new AbortController(); LIVE.ctl = ctl;
    try {
      const r = await fetch(`/api/sites/${enc(id)}/live?since=${LIVE.seq}`, {headers: {Authorization: 'Bearer ' + TOKEN}, signal: ctl.signal, cache: 'no-store'});
      if (!r.ok || !r.body) throw new Error('live ' + r.status);
      const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
      for (;;) {
        const {value, done} = await rd.read(); if (done) break;
        buf += dec.decode(value, {stream: true});
        let i;
        while ((i = buf.indexOf('\n\n')) >= 0) {
          const block = buf.slice(0, i); buf = buf.slice(i + 2);
          const data = block.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5).trim()).join('');
          if (data && data !== '{}') { try { liveEvent(JSON.parse(data)); } catch {} }
        }
      }
    } catch (e) { if (ctl.signal.aborted) return; }
    if (LIVE.ctl === ctl && LIVE.site === id) { LIVE.ctl = null; LIVE.retry = setTimeout(() => { if (CUR?.id === id && !LIVE.ctl) { LIVE.site = id; readLive(id); } }, 1500); }
  }
  function liveEvent(ev) {
    LIVE.seq = Math.max(LIVE.seq, Number(ev.seq) || 0);
    if (L(ev.looks).length) LIVE.looks = L(ev.looks);
    L(ev.slots).forEach(x => {
      const k = S(x.key), sl = LIVE.slots[k] || (LIVE.slots[k] = {key: k, html: '', css: ''});
      if (x.h != null) sl.html = S(x.h); else if (x.ha != null && sl.html.length === Number(x.ho)) sl.html += S(x.ha);
      if (x.c != null) sl.css = S(x.c); else if (x.ca != null && sl.css.length === Number(x.co)) sl.css += S(x.ca);
      if (x.state && x.state !== sl.state) sl.final = false;
      ['label', 'page', 'look', 'kind', 'state', 'at', 'end'].forEach(f => { if (x[f] !== undefined) sl[f] = x[f]; });
      sl.look = Number(sl.look ?? -1);
      LIVE.pend.add(k);
      if (sl.state === 'done') finalSoon(sl);
    });
    if (!LIVE.timer) LIVE.timer = setTimeout(flushLive, 110);
    // a change started elsewhere (her chat, a fix round): the first word written switches the screen to the live build
    if (CUR && S(CUR.id) === LIVE.site && !WORKING(CUR) && L(ev.slots).some(x => x.state === 'think' || x.state === 'write')) {
      clearTimeout(LIVE.wake); LIVE.wake = setTimeout(() => { if (CUR && !WORKING(CUR)) reload(); }, 300);
    }
  }
  function liveFrames() { return [...APP.querySelectorAll('iframe[data-live]')]; }
  const frameWants = (fr, sl) => sl.look >= 0 ? Number(fr.dataset.look) === sl.look : (Number(fr.dataset.look) < 0 && S(fr.dataset.page) === S(sl.page));
  const toMsg = (sl, follow) => ({hoola: 'build', t: 'slot', key: sl.key, label: sl.label, state: sl.state, kind: sl.kind,
    html: sl.html, css: sl.css, follow: follow && LIVE.follow && writing(sl)});
  function flushLive() {
    LIVE.timer = null;
    const keys = [...LIVE.pend]; LIVE.pend.clear();
    const frames = liveFrames();
    keys.forEach(k => { const sl = LIVE.slots[k]; frames.forEach(fr => { if (frameWants(fr, sl)) fr.contentWindow?.postMessage(toMsg(sl, frames.length === 1), '*'); }); });
    followPage();
    drawLiveBits();
  }
  function followPage() {
    if (!LIVE.follow || !CUR || $('#wsPane')?.dataset.live !== 'site:' + CUR.id) return;
    const all = Object.values(LIVE.slots).filter(x => x.look < 0);
    if (all.some(x => writing(x) && S(x.page) === LIVE.page)) return;
    const next = all.filter(writing).sort((a, b) => Number(b.at) - Number(a.at))[0];
    if (next && S(next.page) !== LIVE.page && Date.now() - LIVE.moved > 4000) { LIVE.moved = Date.now(); setLivePage(S(next.page)); }
  }
  function setLivePage(slug) {
    LIVE.page = slug || 'home';
    const fr = APP.querySelector('iframe[data-live]'); if (fr && CUR) { fr.dataset.page = LIVE.page; fr.src = liveSrc(CUR, LIVE.page, -1); }
    const u = $('#wsLUrl'); if (u) u.textContent = 'preview · ' + LIVE.page;
    drawLiveBits();
  }
  function finalSoon(sl, tries = 0) {          // the finished section, as the real page shows it (photos, icons)
    const id = sl.look >= 0 ? 'look' + sl.look : 'p:' + S(sl.page);
    clearTimeout(LIVE.fin[id]);
    LIVE.fin[id] = setTimeout(async () => {
      if (!CUR) return;
      let missing = false;
      try {
        const r = await fetch(liveSrc(CUR, sl.page, sl.look), {cache: 'no-store'}); if (!r.ok) return;
        const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
        Object.values(LIVE.slots).filter(x => x.state === 'done' && !x.final && x.look === sl.look && (sl.look >= 0 || S(x.page) === S(sl.page))).forEach(x => {
          const n = [...doc.querySelectorAll('[data-slot]')].find(e => e.getAttribute('data-slot') === x.key);
          if (n && !n.classList.contains('hb-wait')) { x.html = n.innerHTML; x.final = true; x.end = nowS(); LIVE.pend.add(x.key); } else missing = true;
        });
        if (!LIVE.timer) LIVE.timer = setTimeout(flushLive, 50);
      } catch { missing = true; }
      if (missing && tries < 3) finalSoon(sl, tries + 1);
    }, tries ? 2500 : 1200);
  }
  addEventListener('message', ev => {
    const d = ev.data; if (!d || d.hoola !== 'build' || d.t !== 'ready') return;
    const fr = liveFrames().find(f => f.contentWindow === ev.source); if (!fr) return;
    // a page read now already has every section finished before it: only what is being written (or just finished) is sent
    const mine = Object.values(LIVE.slots).filter(sl => frameWants(fr, sl) && (writing(sl) || nowS() - Number(sl.end || 0) < 20));
    if (mine.length) fr.contentWindow.postMessage({hoola: 'build', t: 'slots', slots: mine.map(sl => toMsg(sl, false))}, '*');
  });

  function liveFrame(src, title, page, look, dev) {
    const d = DEV[dev || DEVICE];
    return `<div class="frame ${dev || DEVICE}" data-w="${d[0]}" data-h="${d[1]}"><iframe title="${esc(title)}" data-live="1" data-page="${esc(page)}" data-look="${look}"
      sandbox="allow-scripts" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>`;
  }
  function liveView(pane, v) {
    const mode = S(v.status) === 'looks' && !L(v.looks).length ? 'looks' : 'site';
    const sig = mode + ':' + v.id;
    if (!LIVE.site || LIVE.site !== S(v.id)) startLive(S(v.id));
    if (pane.dataset.live === sig && pane.dataset.dev === DEVICE && pane.dataset.code === String(LIVE.code)) { drawLiveBits(); return; }
    if (!pane.dataset.live) LIVE.from = hasVersion(v) ? Number(v.version) : 0;     // a change to a built site: before / after later
    pane.dataset.live = sig; pane.dataset.dev = DEVICE; pane.dataset.code = String(LIVE.code);
    const tools = `<span class="sp"></span>${mode === 'site' ? devSeg() : ''}
      <button class="b sm" type="button" data-live="follow" aria-pressed="${LIVE.follow}" title="Keep the part being written in view">Follow</button>
      <button class="b sm" type="button" data-live="code" aria-pressed="${LIVE.code}">${ico('code', 14)}<span>Code</span></button>`;
    let stage;
    if (mode === 'looks') {
      const n = Math.max(3, LIVE.looks.length);
      stage = `<div class="lgrid">${Array.from({length: n}, (_, i) => `<div class="lcol"><div class="lhead"><b>Look ${i + 1}</b><span class="mut sm ell" data-lklabel="${i}">${esc(S(LIVE.looks[i]?.label))}</span><span class="sp"></span><span class="lstate" data-lkstate="${i}"></span></div>
        ${liveFrame(liveSrc(v, 'home', i), `Look ${i + 1} being made`, 'home', i, 'pc')}</div>`).join('')}</div>`;
    } else {
      const fr = liveFrame(liveSrc(v, LIVE.page, -1), 'Your website being built', LIVE.page, -1);
      stage = `<nav class="lpages" id="wsLPages" aria-label="Pages being built"></nav>
        <div class="stage">${DEVICE === 'pc' ? `<div class="bwin"><div class="bchrome" aria-hidden="true"><i></i><i></i><i></i><span class="burl">${ico('lock', 12)}<span id="wsLUrl">preview · ${esc(S(LIVE.page))}</span></span></div>${fr}</div>` : fr}</div>`;
    }
    pane.innerHTML = viewsBar(tools) + `<div class="lbar" id="wsLBar" aria-live="polite"></div>`
      + `<div class="lwrap${LIVE.code ? ' withcode' : ''}"><div class="lmain">${stage}</div>${LIVE.code ? '<aside class="lcode" aria-label="Code being written"><nav class="ltabs" id="wsLTabs"></nav><pre id="wsLCode" tabindex="0"></pre></aside>' : ''}</div>`;
    fit(); drawLiveBits(); startTick();
  }
  function drawLiveBits() {
    if (!CUR) return;
    const pane = $('#wsPane'); if (!pane?.dataset.live) return;
    const all = Object.values(LIVE.slots), act = all.filter(writing), looksMode = pane.dataset.live.startsWith('looks:');
    const b = M(CUR.board), a = ACTV(CUR);
    const bar = $('#wsLBar');
    if (bar) {
      const lead = act.sort((x, y) => Number(y.at) - Number(x.at))[0];
      bar.innerHTML = `<span class="livetag"><i aria-hidden="true"></i>LIVE</span><span class="ell sp">${lead ? `${esc(lead.kind === 'fix' ? '' : lead.state === 'think' ? 'Designing ' : 'Writing ')}<b>${esc(S(lead.label))}</b>${act.length > 1 ? ` <span class="mut">· ${act.length} parts at once</span>` : ''}`
        : esc(S([...L(a.steps)].reverse().find(x => x.state === 'run')?.label) || S(b.now) || 'Working…')}</span>
        ${Number(b.total) ? `<span class="mut sm">${esc(S(b.done || 0))}/${esc(S(b.total))} parts</span>` : ''}${a.started ? `<span class="tm" data-t0="${Number(a.started)}"></span>` : ''}
        ${['building', 'checking'].includes(S(CUR.status)) ? '<button class="b sm" type="button" data-act="stop">Pause</button>' : ''}`;
    }
    if (looksMode) {
      LIVE.looks.forEach((lk, i) => { const e = APP.querySelector(`[data-lklabel="${i}"]`); if (e) e.textContent = S(lk.label); });
      [0, 1, 2].forEach(i => {
        const mine = all.filter(x => x.look === i), e = APP.querySelector(`[data-lkstate="${i}"]`);
        if (e) e.innerHTML = mine.some(writing) ? '<span class="dot v"></span>Writing' : mine.length && mine.every(x => x.state === 'done') ? `${tick}Top ready` : '';
      });
    }
    const pg = $('#wsLPages');
    if (pg) {
      const pages = L(M(CUR.plan).pages).filter(p => !p.template_of);
      pg.innerHTML = pages.map(p => {
        const mine = all.filter(x => x.look < 0 && S(x.page) === S(p.slug)), w = mine.some(writing);
        const done = mine.length && !w && mine.every(x => x.state === 'done');
        return `<button type="button" data-lpage="${esc(S(p.slug))}" aria-current="${S(p.slug) === LIVE.page ? 'page' : 'false'}">${w ? '<span class="dot v"></span>' : done ? tick : ''}<span class="ell">${esc(S(p.title) || S(p.slug))}</span></button>`;
      }).join('');
    }
    const tabs = $('#wsLTabs'), pre = $('#wsLCode');
    if (tabs && pre) {
      const list = all.filter(x => !looksMode || x.look >= 0).sort((x, y) => Number(x.at) - Number(y.at));
      const show = [...list.filter(writing), ...list.filter(x => !writing(x)).slice(-6)];
      if (!LIVE.codeKey || !LIVE.slots[LIVE.codeKey] || (!writing(LIVE.slots[LIVE.codeKey]) && act.length && !LIVE.codePinned)) LIVE.codeKey = S((act[0] || show[show.length - 1] || {}).key);
      tabs.innerHTML = show.map(x => `<button type="button" data-lcode="${esc(x.key)}" aria-current="${x.key === LIVE.codeKey ? 'page' : 'false'}">${writing(x) ? '<span class="dot v"></span>' : ''}<span class="ell">${esc(S(x.label))}</span></button>`).join('') || '<span class="mut sm">The code shows here as it is written.</span>';
      const sl = LIVE.slots[LIVE.codeKey];
      const txt = !sl ? '' : sl.state === 'think' && !sl.html ? '// Opus is designing this section…' : (S(sl.html) + (sl.css ? '\n\n/* styles */\n' + S(sl.css) : ''));
      const atEnd = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
      if (pre.dataset.k !== S(LIVE.codeKey) || pre.textContent.length !== txt.length) {
        pre.textContent = txt; pre.dataset.k = S(LIVE.codeKey);
        if (sl && writing(sl)) { const c = document.createElement('span'); c.className = 'hb-cursor'; pre.appendChild(c); }
        if (atEnd || (sl && writing(sl))) pre.scrollTop = pre.scrollHeight;
      }
    }
  }

  function compareView(pane, v, jd, top) {
    delete pane.dataset.live;
    const page = pageRel(LIVE.page);
    pane.innerHTML = viewsBar(top) + `<div class="edbar okbar"><b>Before and after</b><span class="ell">v${esc(S(jd.from))} on the left, the new v${esc(S(jd.to))} on the right</span><span class="sp"></span>
        <button class="b sm" type="button" data-act="compare">Show the new one only</button></div>
      <div class="cmp"><div><div class="lhead"><b>Before · v${esc(S(jd.from))}</b></div>${frame(S(v.preview) + `__v/${Number(jd.from)}/` + page, 'Before')}</div>
        <div><div class="lhead"><b>After · v${esc(S(jd.to))}</b></div>${frame(S(v.preview) + page, 'After')}</div></div>`;
    fit();
  }

  const studioBtn = (label, ask, pri) => `<button class="b ${pri ? 'pri' : ''}" type="button" data-ask="${esc(ask)}">${esc(label)}</button>`;

  async function code(pane, v) {
    if (!hasVersion(v) && !L(M(v.plan).pages).length) { pane.innerHTML = viewsBar() + '<div class="stage"><div class="box"><p class="mut">The code appears once pages are written.</p></div></div>'; return; }
    pane.innerHTML = viewsBar(`<span class="sp"></span><button class="b" type="button" data-act="export" data-fmt="zip">Download ZIP</button><button class="b" type="button" data-act="export" data-fmt="react">React + Vite</button>`) + '<div class="empty">Loading the files…</div>';
    let t;
    try { t = await api('GET', `/api/sites/${enc(v.id)}/code`); } catch (e) { pane.querySelector('.empty').textContent = e.message; return; }
    if (VIEW !== 'code' || CUR?.id !== v.id) return;
    const groups = L(t.files);
    pane.innerHTML = viewsBar(`<span class="sp"></span><button class="b" type="button" data-act="export" data-fmt="zip">Download ZIP</button><button class="b" type="button" data-act="export" data-fmt="react">React + Vite</button>`)
      + `<div class="split"><nav class="subnav" aria-label="Files">${groups.map(g => `<div class="h">${esc(S(g.title))}</div>${L(g.files).map(f => `<button type="button" data-file="${esc(S(f.path))}"><span class="mono ell">${esc(S(f.label))}</span></button>`).join('')}`).join('') || '<div class="h">No files yet</div>'}</nav>
        <div class="code" id="wsCode"><div class="empty">Choose a file on the left. Every save is checked for safety, becomes a version, and Undo brings it back.</div></div></div>`;
  }

  async function openFile(path) {
    const box = $('#wsCode'); if (!box) return;
    APP.querySelectorAll('[data-file]').forEach(b => b.setAttribute('aria-current', b.dataset.file === path ? 'page' : 'false'));
    box.innerHTML = '<div class="empty">Opening…</div>';
    try {
      const f = await api('GET', `/api/sites/${enc(CUR.id)}/code?path=${enc(path)}`);
      box.innerHTML = `<form data-form="code" data-path="${esc(path)}" style="display:flex;flex-direction:column;flex:1 1 auto;min-height:0"><label class="sr" for="wsCodeT">${esc(path)}</label>
        <textarea id="wsCodeT" spellcheck="false">${esc(S(f.code))}</textarea>
        <div class="cbar2"><code class="ell">${esc(path)}</code><span class="sp"></span><button class="b" type="button" data-act="undo">Undo</button><button class="b pri" type="submit">Save as a new version</button></div></form>`;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  async function cloud(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading your data…</div>';
    let a;
    try { a = await api('GET', `/api/sites/${enc(v.id)}/app`); } catch (e) { a = {error: e.message}; }
    if (VIEW !== 'cloud' || CUR?.id !== v.id) return;
    const cols = L(M(a.app).collections);
    if (!cols.length) {
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>No lists yet</h2><p class="mut">Orders, enquiries, members, bookings: ask for the ones you need and Hoola adds logins and the lists, with rules worked out by the server.</p>
        <div class="inl">${studioBtn('Add lists and logins', 'Is website mein logins aur ek list jodo: ', true)}</div>${a.error ? `<p class="mut sm">${esc(a.error)}</p>` : ''}</div></div>`;
      return;
    }
    pane.innerHTML = viewsBar() + `<div class="split"><nav class="subnav" aria-label="Lists"><div class="h">Data</div>${cols.map((c, i) => `<button type="button" data-coll="${esc(S(c.key))}" ${i ? '' : 'aria-current="page"'}>${esc(S(c.label))}${M(a.counts)[c.key] != null ? `<span class="sp"></span><span class="mut sm">${esc(S(M(a.counts)[c.key]))}</span>` : ''}</button>`).join('')}
        <div class="h">People</div><button type="button" data-coll="__members">Members and logins</button></nav><div class="main" id="wsCloud"></div></div>`;
    openColl(S(cols[0].key));
  }

  async function openColl(key) {
    const box = $('#wsCloud'); if (!box) return;
    APP.querySelectorAll('[data-coll]').forEach(b => b.setAttribute('aria-current', b.dataset.coll === key ? 'page' : 'false'));
    box.innerHTML = '<div class="empty">Loading…</div>';
    try {
      if (key === '__members') {
        const m = await api('GET', `/api/sites/${enc(CUR.id)}/app/members`);
        const rows = L(m.members);
        box.innerHTML = `<h2 style="font-size:18px">Members and logins</h2>${rows.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">Name</th><th scope="col">Mobile / email</th><th scope="col">Role</th></tr></thead><tbody>
          ${rows.map(x => `<tr><td>${esc(S(x.name) || '—')}</td><td>${esc(S(x.phone || x.email || x.login))}</td><td>${esc(S(x.role))}</td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Nobody has signed up yet.</p>'}`;
        return;
      }
      const r = await api('GET', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}`);
      const c = M(r.collection), fields = L(c.fields).slice(0, 8), rows = L(r.rows);
      const val = (row, k) => { const d = M(row.data || row); const x = d[k]; return x == null ? '' : typeof x === 'object' ? JSON.stringify(x) : S(x); };
      box.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><h2 style="font-size:18px" class="sp">${esc(S(c.label) || key)}</h2><span class="mut sm">${rows.length} rows</span></div>
        ${rows.length ? `<div class="tbox"><table class="t"><thead><tr>${fields.map(f => `<th scope="col">${esc(S(f.label || f.key))}</th>`).join('')}</tr></thead>
          <tbody>${rows.slice(0, 200).map(row => `<tr>${fields.map(f => `<td>${esc(val(row, f.key))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<p class="mut">No rows yet.</p>'}
        <p class="note">Totals and prices are worked out by the server, and visitors see only their own rows.</p>`;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  function integrations(pane, v) {
    const langs = L(v.languages), items = [['cart', 'Shop and cart', 'Prices and stock checked by the server, COD, pickup, coupons, GST invoices.', 'Is website mein shop chalu karo'],
      ['card', 'Online payments', 'UPI QR to your UPI ID, or your own Razorpay / Cashfree / PhonePe. Paid only when the gateway confirms.', 'Is website par online payment jodo'],
      ['cal', 'Booking slots', 'Real time slots with limits; you confirm each booking.', 'Is website mein booking slot lagao'],
      ['blog', 'Blog', 'Hoola drafts posts, you say Haan to publish. RSS and scheduling.', 'Is website par blog chalu karo'],
      ['globe', 'Languages', `Now: ${langs.join(', ') || 'en'}. Up to 4 more Indian languages with a switch in the menu.`, 'Is website mein Hindi version bhi jodo'],
      ['chat', 'Visitor chat', 'Visitors message your team from the site; your reply goes only on your tap.', 'Is website par visitor chat chalu karo'],
      ['pin', 'Map and directions', 'Loads only when the visitor taps, so the page stays fast.', 'Is website ke contact page par map lagao'],
      ['spark', 'Rich pieces', 'Quiz, configurator, comparison table, animation, 3D hero.', 'Is website mein ek quiz jodo: '],
      ['link', 'Your other apps', 'New orders to Google Sheets, HubSpot or Slack through your own account.', 'Is website ke naye orders meri Google Sheet mein bhejo']];
    pane.innerHTML = viewsBar() + `<div class="main"><p class="mut">Each one is asked in this website's chat on the left, so Hoola plans it first. Money never moves without your tap.</p>
      <div class="cards">${items.map(([k, t, d, ask]) => `<section class="cardp"><div style="display:flex;align-items:center;gap:10px"><span class="si">${ico(k)}</span><b style="font-size:14.5px">${esc(t)}</b></div>
        <p class="mut sm">${esc(d)}</p><div class="inl" style="margin-top:auto">${studioBtn('Add', ask, false)}</div></section>`).join('')}</div></div>`;
  }

  async function health(pane, v) {
    if (!hasVersion(v)) { pane.innerHTML = viewsBar() + '<div class="stage"><div class="box"><p class="mut">Health shows up once the website is built and live.</p></div></div>'; return; }
    pane.innerHTML = viewsBar() + '<div class="empty">Reading visits, speed and backups…</div>';
    let care = null, ops = null;
    try { care = await api('GET', `/api/sites/${enc(v.id)}/care?days=30`); } catch (e) { care = {error: e.message}; }
    try { ops = await api('GET', `/api/sites/${enc(v.id)}/ops?days=30`); } catch (e) { ops = {error: e.message}; }
    if (VIEW !== 'health' || CUR?.id !== v.id) return;
    const chk = M(v.checks), sp = M(care.speed || ops.speed), bk = M(ops.backup), rt = M(bk.restore_test);
    const band = g => g === 'good' ? 'ok' : g === 'poor' ? 'bad' : 'warn';
    const row = (k, label) => sp[k] ? `<div class="kv"><span>${esc(label)}</span>${pill(`${S(sp[k].p75)} · ${S(sp[k].grade)}`, band(S(sp[k].grade)))}</div>` : '';
    pane.innerHTML = viewsBar() + `<div class="main">${care.say ? `<section class="cardp acc"><p>${esc(S(care.say))}</p>${L(care.tips).map(t => `<p class="li">${esc(S(t))}</p>`).join('')}</section>` : ''}
      <div class="pc2">
      <section class="cardp"><h3>Visitors and results (30 days)</h3><p class="mut sm">No cookies, no trackers: pages counted per day only.</p>
        ${care.error ? `<p class="mut">${esc(care.error)}</p>` : `<div class="kv"><span>Page visits</span><b>${esc(S(care.views ?? '–'))}</b></div>
        <div class="kv"><span>Enquiries</span><b>${esc(S(care.leads ?? '–'))}</b></div>
        <div class="kv"><span>Uptime</span><b>${care.uptime_pct == null ? 'not measured yet' : esc(S(care.uptime_pct)) + '%'}</b></div>
        ${Object.entries(M(care.ssl_days)).map(([h, d]) => `<div class="kv"><span class="ell">HTTPS · <code>${esc(S(h))}</code></span><b>${d == null ? '–' : esc(S(d)) + ' days left'}</b></div>`).join('')}`}</section>
      <section class="cardp"><h3>Speed on real phones (p75)</h3>${row('lcp', 'Main picture shows') + row('fcp', 'First paint') + row('cls', 'Layout shift') + row('ttfb', 'Server answer') || '<p class="mut">No real visits measured yet.</p>'}</section>
      <section class="cardp"><h3>Checks before going live</h3>${chk.passed == null ? '<p class="mut">Not run yet.</p>' : `<div class="kv"><span>Blocking checks</span>${pill(chk.passed ? 'Passed' : L(chk.blocking).length + ' to fix', chk.passed ? 'ok' : 'bad')}</div>
        <div class="kv"><span>Notes</span>${pill(String(L(chk.warnings).length), L(chk.warnings).length ? 'warn' : 'ok')}</div><div class="kv"><span>Test visitor walks</span>${pill(String(L(chk.journeys).length))}</div>`}</section>
      <section class="cardp"><h3>Errors and backups</h3>${ops.error ? `<p class="mut">${esc(ops.error)}</p>` : `<div class="kv"><span>Visitor page errors</span>${pill(Number(ops.errors) ? String(ops.errors) : 'None', Number(ops.errors) ? 'warn' : 'ok')}</div>
        <div class="kv"><span>Backups</span>${pill(bk.enabled ? (bk.last_day ? 'Last ' + S(bk.last_day) : 'On') : 'Off', bk.enabled ? 'ok' : 'warn')}</div>
        <div class="kv"><span>Restore test</span>${rt.day ? pill(rt.ok ? 'Matched · ' + S(rt.day) : 'Did not match · ' + S(rt.day), rt.ok ? 'ok' : 'bad') : pill('Not run yet')}</div>`}</section></div></div>`;
  }

  function settings(pane, v) {
    const f = M(v.facts);
    const fields = [['name', 'Business name'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'], ['hours', 'Opening hours'], ['address', 'Address'], ['city', 'City'], ['instagram', 'Instagram']];
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:900px">
      <form class="cardp" data-form="facts"><h3>Business details</h3><p class="mut sm">Used on every page. A change here is used in the next version; ask in the chat to rebuild now.</p>
        <div class="g2">${fields.map(([k, l]) => `<label class="fld">${esc(l)}<input class="in" name="${k}" value="${esc(S(f[k]))}" autocomplete="off"></label>`).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save details</button></div></form>
      <form class="cardp" data-form="instr"><h3>Instructions for Hoola</h3><p class="mut sm">Your standing brief for this website: who it is for, tone, colours, words to use or avoid, what must never change. Hoola reads it on every message about this site, in every mode.</p>
        <textarea id="wsInstr" class="in" rows="7" maxlength="10000" placeholder="Example: For families in Nagpur. Warm and simple English. Never change the phone number or the Book now button."></textarea>
        <div class="inl"><span class="mut sm" id="wsInstrN">0 / 10,000</span><span class="sp"></span><button class="b pri" type="submit">Save instructions</button></div></form>
      <section class="cardp"><h3>SEO and Google</h3><p class="mut">Page titles, descriptions, sitemap and Search Console are set by Hoola on every build.</p><div class="inl">${studioBtn('Check SEO now', 'Is website ka SEO check karo', false)}</div></section>
      <section class="cardp"><h3>Team</h3><p class="mut">Writers draft, editors review, publishers put live.</p><div class="inl">${studioBtn('Invite a team member', 'Is website ke CMS mein ek team member jodo: ', false)}</div></section>
      <section class="cardp danger"><h3>Take the site down</h3><p class="mut">The site stops answering; your pages, data and versions are kept.</p><div class="inl"><button class="b bad" type="button" data-act="takedown">Take down…</button></div></section></div>`;
    loadInstr();
  }

  /* ---------- v0.808 WAPAS (L7): any version back, bookmarks, what changed, undo per reply, revert and resend ---------- */
  const versionsIn = (a, b) => L(CUR?.versions).filter(x => !/^(Restored v\d+|Full check before going live)/.test(S(x.note)))   // a restore is not this answer's change
    .map(x => ({v: Number(x.version), t: tsec(x.at)})).filter(x => a && x.t >= a - 2 && (!b || x.t < b)).map(x => x.v);
  const verBefore = a => Math.max(0, ...L(CUR?.versions).filter(x => a && tsec(x.at) < a - 2).map(x => Number(x.version)));
  const restorable = n => L(CUR?.versions).some(x => Number(x.version) === Number(n) && x.restorable);
  async function restoreVer(n, why) {
    if (!CUR) return false;
    if (!confirm(`${why || `Put the site back to v${n}?`} It becomes a new version (you can undo it from History). Enquiries, orders and other data are not touched.`)) return false;
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/versions/${n}/restore`, {}); toast(S(r.say).slice(0, 180)); await reload(); return true; }
    catch (er) { toast(er.message, true); return false; }
  }
  async function bookmarkVer(n) {
    const cur = L(CUR?.versions).find(x => Number(x.version) === Number(n));
    const f = await dialog(`Bookmark v${n}`, `<label class="fld">Name (empty removes it)<input class="in" name="name" maxlength="80" value="${esc(S(cur?.bookmark))}" placeholder="Before the Diwali changes"></label>`);
    if (!f) return;
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/versions/${n}/bookmark`, {name: S(f.get('name')).trim()}); toast(S(r.say)); await reload(); }
    catch (er) { toast(er.message, true); }
  }
  const DIFFS = {};
  async function diffVer(n) {
    const box = APP.querySelector(`[data-diff="${n}"]`); if (!box) return;
    if (!box.hidden && box.innerHTML) { box.hidden = true; return; }
    box.hidden = false; box.innerHTML = '<p class="mut sm">Reading the changes…</p>';
    try {
      const r = DIFFS[CUR.id + ':' + n] || (DIFFS[CUR.id + ':' + n] = await api('GET', `/api/sites/${enc(CUR.id)}/versions/${n}/diff`));
      box.innerHTML = `<p class="sm">${esc(S(r.say))}</p>` + L(r.files).map(f => `<details class="dfile"><summary><code class="ell">${esc(S(f.path))}</code><span class="sp"></span><span class="dadd">+${esc(S(f.added))}</span><span class="drem">−${esc(S(f.removed))}</span></summary>
          ${f.diff ? `<pre class="dpre">${S(f.diff).split('\n').map(ln => `<span class="${ln.startsWith('+') && !ln.startsWith('+++') ? 'a' : ln.startsWith('-') && !ln.startsWith('---') ? 'r' : ''}">${esc(ln)}</span>`).join('\n')}</pre>` : '<p class="mut sm">Too long to show here; open the Code tab.</p>'}</details>`).join('');
    } catch (er) { box.innerHTML = `<p class="li bad">${esc(er.message)}</p>`; }
  }

  async function historyView(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading versions…</div>';
    let host = null; try { host = await api('GET', `/api/sites/${enc(v.id)}/hosting`); } catch { host = {hosts: []}; }
    if (VIEW !== 'history' || CUR?.id !== v.id) return;
    const live = L(host.hosts).length > 0, vs = L(v.versions);
    const onAir = Math.max(0, ...L(host.hosts).filter(h => S(h.stage) !== 'Offline').map(h => Number(h.live_version) || 0));   // v0.663 the version people really see
    const bm = vs.filter(x => S(x.bookmark));
    const row = x => { const n = Number(x.version), cur = n === Number(v.version);
      return `<div class="verw"><div class="ver">${pill('v' + S(x.version), cur ? 'ok' : '')}${onAir && n === onAir ? pill('Live', 'ok') : ''}${S(x.bookmark) ? `<span class="vbm" title="Bookmark">${ico('star', 12)}${esc(S(x.bookmark))}</span>` : ''}<span class="sp ell">${esc(S(x.note) || 'Version')} <span class="mut sm">· ${esc(S(x.at).slice(0, 16).replace('T', ' '))}${cur ? ' · current' : ''}</span></span>
        ${x.restorable ? `<button class="b sm ghost" type="button" data-act="ver-diff" data-ver="${n}">Changes</button>` : ''}
        <button class="ib sm" type="button" data-act="ver-bm" data-ver="${n}" aria-label="Bookmark v${n}" title="Bookmark">${ico('star', 14)}</button>
        ${!cur && x.restorable ? `<button class="b sm" type="button" data-act="ver-restore" data-ver="${n}">Restore</button>` : ''}
        ${live && n !== onAir ? `<button class="b sm ghost" type="button" data-act="rollback" data-ver="${n}">Put live…</button>` : ''}</div>
        <div class="vdiff" data-diff="${n}" hidden></div></div>`; };
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:860px"><h2 style="font-size:18px">History</h2>
      <p class="mut">Every change is a checked version. Restore puts the site's code and design back to that version as a new version (undo it the same way); enquiries, orders and other data are never touched.${live ? ' Put live shows a version on your live address after you confirm.' : ''}</p>
      ${bm.length ? `<h3 class="vh">Bookmarks</h3>${bm.map(row).join('')}<h3 class="vh">All versions</h3>` : ''}
      ${vs.length ? vs.map(row).join('') : '<p class="mut">No versions yet.</p>'}
      ${vs.some(x => !x.restorable) ? '<p class="mut sm">Versions made before this update kept only their built pages, so they cannot be restored here.</p>' : ''}</div>`;
  }


  /* ================= v0.837 DRAFT (L13, E6): try a big change in a copy; Accept merges by section, conflicts named ================= */
  const DFT = {list: null, open: ''};
  async function draftsView(pane, v) {
    const parent = S(v.draft_of) || v.id;
    pane.innerHTML = viewsBar() + '<div class="empty">Loading drafts…</div>';
    let r; try { r = await api('GET', `/api/sites/${enc(parent)}/drafts`); } catch (e) { pane.innerHTML = viewsBar() + `<div class="empty">${esc(e.message)}</div>`; return; }
    if (VIEW !== 'drafts' || CUR?.id !== v.id) return;
    DFT.list = L(r.drafts);
    const card = d => {
      const me = d.id === v.id, ch = L(d.changed), cf = L(d.conflicts);
      return `<section class="cardp ${me ? 'acc' : ''}" data-draft="${esc(d.id)}"><h3>${esc(d.name)} ${me ? pill('you are here', 'v') : ''}</h3>
        <p class="mut sm">Started from v${esc(d.base)}${d.site_moved ? ' · the website has changed since' : ''} · ${ch.length} part${ch.length === 1 ? '' : 's'} changed${cf.length ? ` · ${cf.length} conflict${cf.length === 1 ? '' : 's'}` : ''}</p>
        ${ch.length ? `<ul class="dflist">${ch.slice(0, 12).map(x => `<li>${esc(x.say)} <span class="mut sm">${esc(x.what)}</span></li>`).join('')}${ch.length > 12 ? `<li class="mut sm">and ${ch.length - 12} more</li>` : ''}</ul>` : '<p class="mut sm">Nothing changed in this draft yet.</p>'}
        ${cf.length ? `<div class="dfconf"><b>Both changed - you choose:</b>${cf.map(c => `<fieldset class="dfc" data-item="${esc(c.item)}"><legend>${esc(c.say)}</legend>
          <label><input type="radio" name="c-${esc(d.id)}-${esc(c.item)}" value="site" checked> Keep the website's</label>
          <label><input type="radio" name="c-${esc(d.id)}-${esc(c.item)}" value="draft"> Use the draft's</label></fieldset>`).join('')}</div>` : ''}
        <div class="inl">${me ? '' : `<a class="b" href="#/site/${enc(d.id)}">Open the draft</a>`}
          <button class="b pri" type="button" data-act="dft-accept" data-did="${esc(d.id)}">Accept into the website…</button>
          <button class="b ghost" type="button" data-act="dft-discard" data-did="${esc(d.id)}">Discard</button></div></section>`;
    };
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:860px"><h2 style="font-size:18px">Drafts</h2>
      <p class="mut">A draft is a copy of the website where you can try a big change. Your website is not touched until you accept. Accepting merges section by section; if you and the draft both changed the same part, it is named and you choose. A draft has its own data: nothing visitors sent is copied in, and accepting never moves data.</p>
      ${DFT.list.length ? DFT.list.map(card).join('') : '<p class="mut">No drafts yet.</p>'}
      ${v.draft_of ? '' : `<form class="inl" data-form="dft-new" style="margin-top:14px"><input class="in" name="name" maxlength="60" placeholder="Name this draft, e.g. New look for Diwali" aria-label="Draft name" required><button class="b pri" type="submit" ${DFT.list.length >= Number(r.max) ? 'disabled' : ''}>Start a draft</button></form>
        ${DFT.list.length >= Number(r.max) ? `<p class="mut sm">There are already ${esc(r.max)} drafts; accept or discard one first.</p>` : ''}`}</div>`;
  }
  async function draftAct(act, did, card) {
    const parent = S(CUR.draft_of) || CUR.id;
    if (act === 'dft-discard') {
      if (!confirm('Discard this draft? Its changes are deleted. Your website is not touched.')) return;
      try { const r = await api('DELETE', `/api/sites/${enc(parent)}/drafts/${enc(did)}`); toast(S(r.say)); }
      catch (er) { return toast(er.message, true); }
      if (CUR.id === did) { go('#/site/' + enc(parent) + '/drafts'); return; }
      return drawPane();
    }
    const res = {}; (card || document).querySelectorAll('.dfc').forEach(f => { res[f.dataset.item] = f.querySelector('input:checked')?.value || 'site'; });
    if (!confirm('Merge this draft into the website? It becomes one new version of the website (undo it from History). No data is moved.')) return;
    try { const r = await api('POST', `/api/sites/${enc(parent)}/drafts/${enc(did)}/accept`, {confirm: true, resolutions: res}); toast(S(r.say).slice(0, 200)); }
    catch (er) { return toast(er.message, true); }
    go('#/site/' + enc(parent));
  }

  async function publish(pane, v) {
    pane.innerHTML = viewsBar() + '<div class="empty">Loading the addresses…</div>';
    let host = null, moves = null;
    try { host = await api('GET', `/api/sites/${enc(v.id)}/hosting`); } catch (e) { host = {hosts: [], error: e.message}; }
    try { moves = await api('GET', `/api/sites/${enc(v.id)}/moves?quiet=1`); if (moves?.none) moves = null; } catch { moves = null; }
    if (VIEW !== 'publish' || CUR?.id !== v.id) return;
    const hosts = L(host.hosts), rows = L(moves?.rows);
    pane.innerHTML = viewsBar() + `<div class="main"><div class="pc2">
      <section class="cardp acc"><h3>Put v${esc(S(v.version || '–'))} live</h3>
        ${hasVersion(v) ? `<p class="mut">Hoola checks the version and the addresses first and shows you what will happen. Nothing goes live until you tap.</p>
          <div class="inl"><button class="b pri" type="button" data-act="launch">Check and go live…</button></div><div id="wsLaunch"></div>` : '<p class="mut">There is nothing to put live yet: pick a look first.</p>'}</section>
      <section class="cardp"><h3>Addresses</h3>${host.error ? `<p class="mut">${esc(host.error)}</p>` : ''}
        ${hosts.length ? hosts.map(h => `<div class="kv"><code class="ell">${esc(S(h.host))}</code>${pill(S(h.stage) || S(h.status), S(h.stage) === 'Live' ? 'ok' : S(h.stage) === 'Offline' ? 'bad' : 'warn')}</div>${h.problem ? `<p class="li bad">${esc(S(h.problem))}</p>` : ''}`).join('') : '<p class="mut">Not live yet. Your free address is made when you first go live.</p>'}</section>
      ${dnsCard(host)}
      <section class="cardp"><h3>Connect your domain</h3><p class="mut sm">Hoola gives you the exact records to add, checks them from three places, then sets up HTTPS.</p>
        <form data-form="domain" class="inl"><input class="in" id="wsDom" aria-label="Your domain" placeholder="yourname.in" autocomplete="off" style="flex:1 1 200px"><button class="b" type="submit">Connect</button></form>
        <div class="inl">${studioBtn('Find a domain to buy', 'Is website ke liye achha domain dhoondho', false)}</div></section>
      ${moves ? `<section class="cardp"><div style="display:flex;align-items:center;gap:8px"><h3 class="sp">Old site addresses</h3>${pill(moves.approved ? 'Approved' : `${rows.length} found`, moves.approved ? 'ok' : 'warn')}</div>
        <p class="mut sm">Links and Google results from your old site (${esc(S(moves.from_host))}) open the matching new page (301). Untick any you don't want.</p>
        <form data-form="moves" data-hash="${esc(S(moves.hash))}">${rows.slice(0, 200).map(r => `<label class="mv"><input type="checkbox" name="keep" value="${esc(S(r.old))}" ${r.guess ? '' : 'checked'}><code>${esc(S(r.old))}</code><span aria-hidden="true">→</span><code>${esc(S(r.new))}</code>${pill(S(r.how), r.guess ? 'warn' : '')}</label>`).join('') || '<p class="mut">Every old address already exists on the new site.</p>'}
          ${rows.length ? `<div class="inl" style="justify-content:flex-end;margin-top:8px"><button class="b pri" type="submit">Haan, jod do</button></div>` : ''}</form></section>` : ''}
    </div></div>`;
  }

  // v0.663 the DNS records her domain needs, drawn here (they only went to the chat before), with her tap to apply
  function dnsCard(host) {
    const seen = new Set();
    const plans = L(M(host).dns).filter(p => S(p.purpose) === 'website' && !['undone'].includes(S(p.status)) && !seen.has(S(p.domain)) && seen.add(S(p.domain)));
    if (!plans.length) return '';
    return plans.slice(0, 2).map(p => {
      const st = S(p.status), todo = L(p.changes).filter(c => S(c.op) !== 'keep');
      const what = {planned: ['Ready to add', 'warn'], manual: ['Add these yourself', 'warn'], applied: ['Added', 'ok'], failed: ['Could not add', 'bad']}[st] || [st, ''];
      return `<section class="cardp" data-dns="${esc(S(p.id))}"><div style="display:flex;align-items:center;gap:8px"><h3 class="sp">DNS for ${esc(S(p.domain))}</h3>${pill(what[0], what[1])}</div>
        <p class="mut sm">${st === 'planned' ? `Hoola can add these at ${esc(S(p.provider))} for you after your tap.` : st === 'applied' ? 'Added. It takes 5 to 30 minutes to show everywhere; then HTTPS is set up by itself.'
          : `Add these at the company where you bought ${esc(S(p.domain))} (GoDaddy, Hostinger, BigRock…): open DNS / Manage DNS, add each record, keep TTL as it is.`}</p>
        ${todo.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">Change</th><th scope="col">Type</th><th scope="col">Name</th><th scope="col">Value</th></tr></thead><tbody>
          ${todo.map(c => `<tr><td>${esc({add: 'Add', update: 'Change', delete: 'Remove'}[S(c.op)] || S(c.op))}</td><td>${esc(S(c.type))}</td><td><code>${esc(S(c.name))}</code></td><td><code class="ell">${esc(S(c.content))}</code></td></tr>`).join('')}</tbody></table></div>` : '<p class="mut sm">Nothing to change: the records are already right.</p>'}
        ${L(p.risks).map(r => `<p class="li bad">${esc(S(r))}</p>`).join('')}${p.error ? `<p class="li bad">${esc(S(p.error))}</p>` : ''}
        <div class="inl" style="justify-content:flex-end">${st === 'planned' && todo.length ? `<button class="b pri" type="button" data-act="dns-apply" data-plan="${esc(S(p.id))}" data-hash="${esc(S(p.hash))}">Haan, add them for me</button>` : ''}
          ${st === 'applied' ? `<button class="b" type="button" data-act="dns-undo" data-plan="${esc(S(p.id))}">Undo</button>` : ''}
          ${st !== 'planned' ? `<button class="b" type="button" data-act="dns-check" data-plan="${esc(S(p.id))}">${st === 'manual' ? "I've added them · check" : 'Check now'}</button>` : ''}</div>
        <div data-dnsout></div></section>`;
    }).join('');
  }

  async function launch() {
    const out = $('#wsLaunch'); if (!out) return;
    try {
      const card = await api('POST', `/api/sites/${enc(CUR.id)}/launch-request`, {});
      const blk = L(card.blockers);
      out.innerHTML = `<div class="launch"><p class="sm">${esc(S(card.say))}</p>${blk.length ? blk.map(b => `<p class="li bad">${esc(S(b))}</p>`).join('')
        : `<div style="display:flex;flex-wrap:wrap;gap:6px">${L(card.hosts).map(h => `<code>${esc(S(h))}</code>`).join(' ')}</div>
          <div class="inl" style="justify-content:flex-end"><button class="b pri" type="button" data-act="golive" data-hash="${esc(S(card.hash))}">Haan, live karo</button></div>`}</div>`;
    } catch (e) { out.innerHTML = `<p class="li bad">${esc(e.message)}</p>`; }
  }

  /* ---------- polling while the server works ---------- */
  function sig(v) { return [v.status, v.version, M(v.board).pct, M(v.board).now, L(v.looks).length, L(v.looks).map(x => x.full).join(), v.error].join('|'); }
  function startPoll() {
    stopPoll(); SIG = sig(CUR);
    const id = CUR.id;
    POLL = setTimeout(async () => {
      POLL = null;
      if (!CUR || CUR.id !== id) return;
      try {
        const v = await api('GET', `/api/sites/${enc(id)}`);
        if (!CUR || CUR.id !== id) return;
        const changed = sig(v) !== SIG, moved = actSig(v) !== actSig(CUR); CUR = v;
        if (changed && (VIEW === 'preview' || !WORKING(v))) { drawState(); drawPane(); }
        else { if (moved) drawActivity(); else drawState(); startPoll(); }
      } catch { startPoll(); }
    }, 2000);
  }
  function stopPoll() { if (POLL) { clearTimeout(POLL); POLL = null; } }
  async function reload() {
    if (!CUR) return;
    try {
      const was = Number(CUR.version) || 0;
      CUR = await api('GET', `/api/sites/${enc(CUR.id)}`); drawState(); drawPane(); loadErrors();
      if ((Number(CUR.version) || 0) !== was && THREAD.site === S(CUR.id)) { THREAD.sig = ''; drawMsgs(); }   // v0.808 the reply's Version / Undo footer
    } catch (e) { toast(e.message, true); }
  }

  /* ---------- v0.802 GALTI PAKDO (L6): the preview tells Hoola when it breaks; Try to fix follows a ladder ----------
     The preview frame posts its errors (hoola-site.js, preview only); they are relayed with her login, one card per
     fingerprint: Page error / Data error / Build problem, Show details, Try to fix (Ctrl+Enter), Ignore. After two
     fixes that did not hold, the button becomes Plan for root cause (the server decides; the ledger rides the turn). */
  const GALTI = {site: '', errors: [], q: [], t: null, open: {}};
  addEventListener('message', ev => {
    const d = ev.data;
    if (!d || d.hoola !== 'perr' || !CUR) return;
    const fr = APP.querySelector('.frame iframe'); if (!fr || ev.source !== fr.contentWindow) return;   // only her preview
    if (GALTI.q.length < 20) GALTI.q.push({kind: S(d.kind), m: S(d.m), f: S(d.f), l: Number(d.l) || 0, s: S(d.s), p: S(d.p)});
    clearTimeout(GALTI.t); GALTI.t = setTimeout(sendErrors, 1200);
  });
  async function sendErrors() {
    const q = GALTI.q.splice(0); if (!q.length || !CUR) return;
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/preview-errors`, {items: q}); GALTI.errors = L(r.errors); drawErrors(); }
    catch { /* the next load tries again */ }
  }
  async function loadErrors() {
    if (!CUR) return;
    try { GALTI.errors = L((await api('GET', `/api/sites/${enc(CUR.id)}/errors`)).errors); } catch { GALTI.errors = []; }
    drawErrors();
  }
  function drawErrors() {
    const box = $('#wsErr'); if (!box) return;
    const es = L(GALTI.errors).filter(e => S(e.state) === 'open');
    const seen = L(GALTI.errors).filter(e => S(e.state) === 'not_seen');
    box.innerHTML = es.slice(0, 3).map((e, i) => `<div class="errcard" data-eid="${esc(S(e.id))}"${i === 0 ? ' data-first="1"' : ''}>
        <div class="eh"><span class="ek ${esc(S(e.kind))}">${esc(S(e.title))}</span><span class="mut sm ell">${esc(S(e.page))} · seen ${esc(S(e.count))}×${e.version ? ' · v' + esc(S(e.version)) : ''}</span></div>
        <p class="em">${esc(S(e.message))}</p>${e.note ? `<p class="mut sm">${esc(S(e.note))}</p>` : ''}
        ${GALTI.open[e.id] ? `<div class="ed"><div class="kv"><span>Where</span><code class="ell">${esc(e.file ? `${S(e.file)}${e.line ? ':' + S(e.line) : ''}` : S(e.page))}</code></div>
          ${e.stack ? `<pre class="est">${esc(S(e.stack))}</pre>` : ''}
          ${L(e.attempts).length ? `<ol class="tries">${L(e.attempts).map(a => `<li>${esc(a.mode === 'plan' ? 'Plan' : 'Fix')} from v${esc(S(a.from_version))} · ${esc(S(a.result) || 'waiting for the next preview')}</li>`).join('')}</ol>` : ''}</div>` : ''}
        <div class="inl"><button type="button" class="b sm pri" data-act="err-fix" data-id="${esc(S(e.id))}" title="Ctrl+Enter">${S(e.next) === 'plan' ? 'Plan for root cause' : 'Try to fix'}</button>
          <button type="button" class="b sm" data-act="err-more" data-id="${esc(S(e.id))}" aria-expanded="${!!GALTI.open[e.id]}">${GALTI.open[e.id] ? 'Hide details' : 'Show details'}</button><span class="sp"></span>
          <button type="button" class="b sm ghost" data-act="err-ign" data-id="${esc(S(e.id))}">Ignore</button></div></div>`).join('')
      + (es.length > 3 ? `<p class="mut sm">${es.length - 3} more problem(s) · website_dekho can list them all</p>` : '')
      + (seen.length && !es.length ? `<p class="errok">${ico('check', 12)} ${seen.length === 1 ? 'The last problem' : seen.length + ' problems'} not seen since v${esc(S(CUR?.version))}</p>` : '');
    const bar = $('#wsPerr');
    if (bar) {
      const top = es[0];
      bar.hidden = !top;
      if (top) bar.innerHTML = `<span class="ek ${esc(S(top.kind))}">${esc(S(top.title))}</span><span class="ell"><b>This page hit a problem.</b> ${esc(S(top.message))}</span><span class="sp"></span>
        <button type="button" class="b sm pri" data-act="err-fix" data-id="${esc(S(top.id))}">${S(top.next) === 'plan' ? 'Plan for root cause' : 'Try to fix'}</button>
        <button type="button" class="b sm" data-act="err-more" data-id="${esc(S(top.id))}">Show details</button>`;
    }
  }
  async function fixError(id) {
    if (!CUR || THREAD.waiting) { if (THREAD.waiting) toast('Hoola is working; press Try to fix when this step ends.', true); return; }
    try {
      const r = await api('POST', `/api/sites/${enc(CUR.id)}/errors/${enc(id)}/fix`, {});
      toast(S(r.say));
      await ask(S(r.text), {mode: S(r.mode) === 'plan' ? 'plan' : 'build', hints: [`fixing a preview error (try ${S(r.attempt)}), details in your rules as error_to_fix`]});
      loadErrors();
    } catch (er) { toast(er.message, true); }
  }
  addEventListener('keydown', e => {                       // Ctrl+Enter = Try to fix the first problem (when the box is empty)
    if (!(e.ctrlKey || e.metaKey) || e.key !== 'Enter') return;
    const first = APP.querySelector('#wsErr .errcard[data-first]'); if (!first) return;
    const t = $('#wsTh'); if (t && S(t.value).trim()) return;
    e.preventDefault(); fixError(first.dataset.eid);
  });

  /* ---------- the site's own Hoola thread (never the home chat) ----------
     v0.777 CHAT JAISA (built as 0.771) (L1 of docs/LOVABLE_STUDIO_PLAN.md): the thread rides the conversation's LIVE event stream
     (stream.js, /events?live=1) instead of polling every 1.5 s: the reply arrives word by word (HoolaStream.Pacer) and
     each new word fades in out of a soft focus (HoolaMD.Live soft); "Thinking…" shimmers while the model reasons and
     folds into "Thought for 12s"; each tool step shows live (present tense) and turns past tense when done ("Reading
     the site" -> "Read the site"); a finished turn keeps "Worked for 42s · 5 steps · Rs 3.10" with a Details button
     that opens the Timeline + Changes where the preview sits; her new message scrolls to the TOP of the view (the
     stream never yanks her down; a "Latest" button appears instead); a message sent while Hoola works waits greyed
     ("Runs after this") with Interrupt; files / photos attach (paperclip, drop, paste) and a long paste becomes a
     chip that travels as a text file. Polling stays only as the fallback when the stream is down (and a slow safety
     read every 4 s while a turn runs). Rupees are the server's own meter for that turn (/api/conversations/{c}/costs). */
  const PAST = {Checking: 'Checked', Working: 'Worked', Viewing: 'Viewed', Reading: 'Read', Managing: 'Managed',
    Searching: 'Searched', Doing: 'Did', Creating: 'Created', Writing: 'Wrote', Running: 'Ran', Building: 'Built',
    Making: 'Made', Preparing: 'Prepared', Finding: 'Found', Sending: 'Sent', Getting: 'Got', Asking: 'Asked',
    Setting: 'Set', Adding: 'Added', Looking: 'Looked', Opening: 'Opened', Handling: 'Handled', Fetching: 'Fetched',
    Reviewing: 'Reviewed', Noting: 'Noted', Changing: 'Changed', Talking: 'Talked', Logging: 'Logged',
    Removing: 'Removed', Compiling: 'Compiled', Updating: 'Updated', Editing: 'Edited', Extracting: 'Extracted',
    Applying: 'Applied', Replying: 'Replied', Pulling: 'Pulled', Starting: 'Started', Uploading: 'Uploaded',
    Moving: 'Moved', Turning: 'Turned', Posting: 'Posted', Remembering: 'Remembered', Learning: 'Learned',
    Planning: 'Planned', Cleaning: 'Cleaned', Recalling: 'Recalled', Watching: 'Watched', Designing: 'Designed',
    Using: 'Used', Booking: 'Booked', Cancelling: 'Cancelled', Calling: 'Called', Recording: 'Recorded',
    Stopping: 'Stopped', Calculating: 'Calculated', Deploying: 'Deployed', Controlling: 'Controlled',
    Previewing: 'Previewed', Organizing: 'Organized', Retrieving: 'Retrieved', Forwarding: 'Forwarded',
    Snoozing: 'Snoozed', Sorting: 'Sorted', Forgetting: 'Forgot', Exporting: 'Exported', Summarizing: 'Summarized',
    Teaching: 'Taught', Approving: 'Approved', Acting: 'Acted', Listening: 'Listened', Deleting: 'Deleted',
    Verifying: 'Verified', Importing: 'Imported', Fixing: 'Fixed', Testing: 'Tested', Digging: 'Dug',
    Browsing: 'Browsed', Mapping: 'Mapped', Saving: 'Saved', Copying: 'Copied', Duplicating: 'Duplicated',
    Merging: 'Merged', Matching: 'Matched', Helping: 'Helped', Arranging: 'Arranged', Switching: 'Switched',
    Operating: 'Operated', Cloning: 'Cloned', Playing: 'Played', Thinking: 'Thought', Drawing: 'Drew',
    Generating: 'Generated', Loading: 'Loaded', Assembling: 'Assembled', Choosing: 'Chose', Picking: 'Picked',
    Painting: 'Painted', Shooting: 'Shot', Putting: 'Put', Linking: 'Linked', Connecting: 'Connected'};
  const pastLabel = (label, state) => {
    const t = S(label); if (state === 'run' || state === 'running') return t;
    const m = /^([A-Z][a-z]+ing)\b/.exec(t);
    return m && PAST[m[1]] ? PAST[m[1]] + t.slice(m[1].length) : t;
  };
  const LONG_PASTE = 1500;                                   // a paste longer than this travels as a text file
  async function ensureConv() {
    if (THREAD.conv && THREAD.site === CUR.id) return THREAD.conv;
    THREAD.site = CUR.id;
    let c = store.get(convKey(CUR.id));
    if (c) { try { await api('GET', `/api/conversations/${enc(c)}/messages?limit=1`); } catch { c = ''; } }
    if (!c) { c = await newConv(`Website · ${name(CUR)}`); store.set(convKey(CUR.id), c); }
    THREAD.conv = c;
    startStream(c);
    return c;
  }
  async function openThread() {
    clearTimeout(THREAD.timer); stopStream();
    Object.assign(THREAD, {site: CUR.id, conv: store.get(convKey(CUR.id)), rows: [], live: '', sig: '', waiting: false,
      since: 0, steps: [], stepMap: new Map(), stepsRead: false, startedS: 0, turn: '', costs: [], think: null,
      queue: [], files: [], pinned: true, thoughts: new Map()});
    drawMsgs(); drawTray();
    await loadPlans(); THREAD.sig = ''; drawMsgs();
    if (THREAD.conv) { startStream(THREAD.conv); await readThread(); }
  }
  /* ----- the live stream ----- */
  function stopStream() { if (THREAD.stream) { THREAD.stream.abort(); THREAD.stream = null; } THREAD.connected = false; }
  function startStream(c) {
    if (!window.HoolaStream || (THREAD.stream && THREAD.streamConv === c)) return;
    stopStream();
    THREAD.streamConv = c;
    const s = window.HoolaStream.open({url: `/api/conversations/${enc(c)}/events`, token: TOKEN, after: 0,
      onState: st => { THREAD.connected = st === 'ok'; },
      onAuth: () => location.replace('/console/'),
      onEvent: ev => { if (THREAD.stream === s && THREAD.conv === c) onThreadEvent(ev); }});
    THREAD.stream = s;
  }
  function liveBox() {
    let b = $('#wsLiveBox'); if (!b) return null;
    if (!THREAD.liveR || THREAD.liveR.el !== b.querySelector('.ho')) {
      b.innerHTML = `<div class="who"><span class="hm" aria-hidden="true"></span><b>Hoola</b></div><div class="ho textmd"></div>`;
      const el = b.querySelector('.ho');
      THREAD.liveR = window.HoolaMD && window.HoolaMD.Live ? new window.HoolaMD.Live(el, {soft: true}) : {el, update(t) { el.textContent = t; }, clear() { el.textContent = ''; }};
    }
    return b;
  }
  function showLive(text, streaming) {
    THREAD.live = text;
    const b = liveBox(); if (!b) return;
    b.hidden = !S(text).trim();
    THREAD.liveR.update(S(text).replace(/\n?\s*\[\[start-building:[^\]\n]*\]?\]?\s*$/, ''), streaming);   // the marker never shows while it streams
    keepPinned();
  }
  function endLive() {
    THREAD.pacer?.flush?.(); THREAD.pacer = null; THREAD.live = ''; THREAD.turn = '';
    const b = $('#wsLiveBox'); if (b) { b.hidden = true; b.innerHTML = ''; } THREAD.liveR = null;
  }
  function onThreadEvent(ev) {
    const p = M(ev.payload);
    switch (ev.kind) {
      case 'reply_start':
        THREAD.waiting = true; THREAD.turn = S(p.turn);
        if (window.HoolaStream) THREAD.pacer = new window.HoolaStream.Pacer((t, fin) => showLive(t, !fin));
        drawWork(); return;
      case 'delta':
        if (!THREAD.pacer) THREAD.pacer = new window.HoolaStream.Pacer((t, fin) => showLive(t, !fin));
        if (p.seq && p.seq <= (THREAD.seq || 0)) return; THREAD.seq = p.seq || 0;
        if (THREAD.think && !THREAD.think.end) { THREAD.think.end = nowS(); drawWork(); }
        THREAD.pacer.push(S(p.text)); return;
      case 'delta_reset': THREAD.pacer?.reset?.(); return;
      case 'reply_end': THREAD.pacer?.flush?.(); return;
      case 'think':
        if (p.clear) return;
        if (!THREAD.think || THREAD.think.end) THREAD.think = {t0: nowS(), end: 0};
        drawWork(); return;
      case 'step': {
        const k = S(p.id) || ('e' + ev.id), t = ev.at ? tsec(ev.at) : nowS();
        const x = THREAD.stepMap.get(k) || {label: S(p.label) || S(p.tool), at: t, state: 'run'};
        if (p.label) x.label = S(p.label);
        if (p.state && p.state !== 'running') { x.state = p.state === 'error' ? 'error' : 'done'; x.end = t; }
        THREAD.stepMap.set(k, x);
        THREAD.steps = [...THREAD.stepMap.values()].filter(y => y.at).sort((a, b) => a.at - b.at);
        THREAD.waiting = true; drawWork(); return;
      }
      case 'typing':
        if (p.on) { if (!THREAD.waiting) { THREAD.waiting = true; THREAD.startedS = THREAD.startedS || nowS(); drawWork(); } }
        return;
      case 'message': {
        if (S(p.source) === 'greeting') return;
        const row = {id: ev.id, role: p.role, text: S(p.text), at: ev.at, source: p.source, files: p.files};
        if (p.role === 'user') {
          if (THREAD.queue.some(q => clean(q.text) === clean(row.text))) return;   // still waiting its turn (drawn greyed below)
          const mine = THREAD.rows.findIndex(r => S(r.id).startsWith('local-') && clean(r.text) === clean(row.text));
          if (mine >= 0) THREAD.rows[mine] = {...THREAD.rows[mine], ...row};
          else if (!THREAD.rows.some(r => r.id === row.id)) THREAD.rows.push(row);
          drawMsgs(); return;
        }
        if (p.role !== 'assistant' || p.ack || !row.text.trim()) return;
        if (!THREAD.rows.some(r => r.id === row.id)) THREAD.rows.push(row);
        endLive(); THREAD.seq = 0;
        if (THREAD.think && !THREAD.think.end) THREAD.think.end = nowS();
        if (THREAD.think) { THREAD.lastThink = THREAD.think; thoughtFor(row.text); } THREAD.think = null;
        finishTurn();
        return;
      }
      default: return;   // cards and other kinds belong to the main console; the Studio shows its own work card
    }
  }
  const tkey = t => clean(t).trim().slice(0, 240);
  function thoughtFor(text) { const k = THREAD.lastThink; if (text && k && k.end && k.end > k.t0) THREAD.thoughts.set(tkey(text), k.end - k.t0); }
  async function finishTurn() {
    const c = THREAD.conv;
    if (THREAD.queue.length) {                               // the next message she queued now runs: it moves into the thread
      const nx = THREAD.queue.shift(); THREAD.rows.push({...nx, at: new Date(nowS() * 1000).toISOString()});
      THREAD.startedS = nowS(); THREAD.scrollTo = nx.id; THREAD.pinned = false;
    } else { THREAD.waiting = false; THREAD.startedS = 0; }
    await Promise.all([readSteps(c), readCosts(c)]);
    if (c !== THREAD.conv) return;
    drawMsgs(); reload();
  }
  async function readCosts(c) {
    try { const r = await api('GET', `/api/conversations/${enc(c)}/costs?limit=60`); THREAD.costs = L(r.costs); } catch { /* the rupee line is extra */ }
  }
  const costFor = (a, b) => {
    let inr = 0, n = 0;
    for (const x of L(THREAD.costs)) { const e = tsec(x.end) || tsec(x.start); if (e >= a - 2 && e <= b + 120) { inr += Number(x.inr) || 0; n++; } }
    return n ? inr : null;
  };
  const rs = v => v == null ? '' : v < 0.01 ? 'under Rs 0.01' : 'Rs ' + v.toFixed(v < 10 ? 2 : 0);
  const clean = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  /* v0.658 the chat's own work feed, like Lovable: every tool step a turn ran (the timeline's step events), with a live
     timer while Hoola works and "Worked for 42s · 5 steps" kept above each answer. Times are the server's clock. */
  const tsec = a => { const t = S(a); if (!t) return 0; const ms = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? t : t + 'Z'); return isNaN(ms) ? 0 : ms / 1000; };
  async function readSteps(c) {
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/timeline?limit=200&steps=1`);
      const by = new Map();
      for (const ev of L(r.events)) {
        if (ev.kind !== 'step') continue;
        // the timeline keeps one row per step: `at` = when it started, `updated_at` = its latest state (the end)
        const pl = M(ev.payload), k = S(pl.id) || ('e' + ev.id), at = tsec(ev.at), upd = tsec(ev.updated_at) || at;
        const x = by.get(k) || {label: S(pl.label) || S(pl.tool), at, state: 'run'};
        x.at = Math.min(x.at || at, at);
        if (pl.state !== 'running') { x.state = pl.state === 'error' ? 'error' : 'done'; x.end = Math.max(x.end || 0, upd); }
        if (pl.label) x.label = S(pl.label);
        by.set(k, x);
      }
      THREAD.stepMap = by;
      THREAD.steps = [...by.values()].filter(x => x.at).sort((a, b) => a.at - b.at);
    } catch { /* the feed is extra: the chat still works without it */ }
  }
  const stepsBetween = (a, b) => L(THREAD.steps).filter(x => x.at >= a - 2 && (!b || x.at <= b + 2));
  const md = t => window.HoolaMD ? window.HoolaMD.render(t, false) : `<p>${esc(t)}</p>`;
  const who = t => `<div class="who"><span class="hm" aria-hidden="true"></span><b>Hoola</b>${t ? `<span>${esc(clockOf(t))}</span>` : ''}</div>`;
  const fileChips = fs => L(fs).length ? `<div class="mfiles">${L(fs).map(f => `<span class="fchip">${ico('clip', 12)}<span class="ell">${esc(S(M(f).name) || 'File')}</span></span>`).join('')}</div>` : '';
  /* the turns in her thread: [{user row, assistant row, start, end, steps}] */
  function turnsOf(rows) {
    const out = []; let cur = null;
    for (const r of rows) {
      if (r.role === 'user') { cur = {user: r, start: tsec(r.at) || 0}; out.push(cur); continue; }
      if (cur && !cur.reply) { cur.reply = r; cur.end = tsec(r.at); cur.steps = cur.start && cur.end ? stepsBetween(cur.start, cur.end) : []; }
      else out.push({reply: r, start: tsec(r.at), end: tsec(r.at), steps: []});
    }
    return out;
  }
  /* ---------- v0.782 TEEN MODE (L2): Build / Plan / Chat, plans as versions, her instructions ----------
     Build changes the website. Plan writes a plan (a numbered version kept on the site, /api/sites/{id}/plans) that
     she opens, edits, comments on, then APPROVES - one Build message carries the approved text - or skips. Chat only
     talks; a reply that ends with [[start-building: ...]] gets a Start building card (Build / Skip). The server refuses
     every changing tool in Plan / Chat (agent/turnmode.py) - the switch is not just a polite hint. Alt+P cycles; a
     message starting /plan, /chat or /build runs in that mode once. */
  const MODES = ['build', 'plan', 'chat'];
  const MODE_NAME = {build: 'Build', plan: 'Plan', chat: 'Chat'};
  const MODE_PH = {build: 'Ask Hoola to change anything…', plan: 'Describe the change - Hoola writes a plan first, nothing changes yet…',
    chat: 'Ask anything about this website - nothing changes…'};
  function chatMode() { const m = store.get(MODE_KEY + '.chat'); return MODES.includes(m) ? m : 'build'; }
  function setChatMode(m) {
    if (!MODES.includes(m)) return;
    store.set(MODE_KEY + '.chat', m);
    APP.querySelectorAll('[data-cmode]').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.cmode === m)));
    const t = $('#wsTh'); if (t) t.placeholder = MODE_PH[m];
  }
  const modeOfRow = r => { if (!r) return ''; if (r.mode) return r.mode; const m = /\[Web console mode: (build|plan|chat)\]/.exec(S(r.text)); return m ? m[1] : ''; };
  const SB_RE = /\n?\s*\[\[start-building:\s*([^\]\n]{1,400})\]\]\s*$/;
  function startBuild(text) { const m = SB_RE.exec(S(text)); return m ? {text: S(text).replace(SB_RE, '').trimEnd(), ask: m[1].trim()} : null; }
  function buildCard(a) {
    const k = tkey(a);
    if (THREAD.sbDone?.has(k)) return '';
    return `<div class="sbcard"><div><b>Start building</b><span class="mut sm"> · uses money</span></div><p class="sm">${esc(a)}</p>
      <div class="inl"><button class="b pri sm" type="button" data-act="sb-build" data-sb="${esc(a)}">Build</button><button class="b sm" type="button" data-act="sb-skip" data-sb="${esc(a)}">Skip</button></div></div>`;
  }
  const planKey = t => S(t).trim();
  const planMd = t => md(S(t).replace(/^(#{1,6} [^\n]*)\n(?!\n)/gm, '$1\n\n'));   // a plan's list right under its heading still renders as a list
  function planCard(text) {
    const p = L(THREAD.plans).find(x => planKey(x.text) === planKey(text));
    if (!p) { savePlan(text); return `<div class="plancard"><div class="ph"><b>Plan</b><span class="mut sm">Saving as a version…</span></div></div>`; }
    const st = S(p.status), first = S(p.text).split('\n').map(x => x.replace(/^#+\s*/, '').trim()).find(x => x && !/^goal$/i.test(x)) || 'Plan';
    return `<div class="plancard" data-ver="${p.version}"><div class="ph"><b>Plan</b>${pill('v' + p.version, '')}${st !== 'draft' ? pill(st === 'approved' ? 'Approved' : st === 'skipped' ? 'Skipped' : 'Replaced', st === 'approved' ? 'ok' : '') : ''}</div>
      <p class="mut sm ell">${esc(first)}</p>
      <div class="inl"><button class="b sm" type="button" data-act="plan-open" data-ver="${p.version}">Open plan</button>${st === 'draft' ? `<button class="b pri sm" type="button" data-act="plan-approve" data-ver="${p.version}">Approve</button><button class="b sm" type="button" data-act="plan-skip" data-ver="${p.version}">Skip</button>` : ''}</div></div>`;
  }
  async function loadPlans() {
    if (!CUR) return;
    try { const r = await api('GET', `/api/sites/${enc(CUR.id)}/plans`); THREAD.plans = L(r.plans); } catch { THREAD.plans = THREAD.plans || []; }
  }
  async function savePlan(text) {
    const k = planKey(text); THREAD.planSaving = THREAD.planSaving || new Set();
    if (!CUR || THREAD.planSaving.has(k)) return;
    THREAD.planSaving.add(k);
    try { await api('POST', `/api/sites/${enc(CUR.id)}/plans`, {text, source: 'hoola'}); await loadPlans(); }
    catch (e) { toast(e.message, true); }
    THREAD.sig = ''; drawMsgs(); if (VIEW === 'plans') drawPane();
  }
  async function planStatus(ver, what) {
    const r = await api('POST', `/api/sites/${enc(CUR.id)}/plans/${Number(ver)}/${what}`, {});
    await loadPlans(); THREAD.sig = ''; drawMsgs(); if (VIEW === 'plans') drawPane();
    return r;
  }
  async function approvePlan(ver) {
    const p = L(THREAD.plans).find(x => Number(x.version) === Number(ver)); if (!p) return;
    await planStatus(ver, 'approve');
    setChatMode('build');
    if (VIEW === 'plans') { VIEW = 'preview'; drawPane(); }                 // she watches the build happen
    // the approved text rides this ONE Build message (one line, so the chat shows only her words)
    const flat = S(p.text).replace(/\]/g, ')').replace(/\s*\n\s*/g, ' / ').slice(0, 12000);
    await ask(`Build the approved plan (v${p.version}).`, {mode: 'build', hints: [`approved plan v${p.version} - build exactly this, step by step: ${flat}`]});
  }
  function planView(pane, v) {
    const ps = L(THREAD.plans);
    if (!ps.length) { pane.innerHTML = `<div class="dtop"><button class="b sm" type="button" data-view="preview">${ico('back', 14)}<span>Back to preview</span></button></div><div class="main"><p class="mut">No plan yet. Switch the chat to Plan and describe the change.</p></div>`; return; }
    const cur = ps.find(x => Number(x.version) === Number(THREAD.planVer)) || ps[0];
    THREAD.planVer = cur.version;
    const i = ps.indexOf(cur), st = S(cur.status);
    pane.innerHTML = `<div class="dtop"><button class="b sm" type="button" data-view="preview">${ico('back', 14)}<span>Back to preview</span></button>
        <button class="ib sm" type="button" data-pver="${i + 1 < ps.length ? ps[i + 1].version : ''}" ${i + 1 < ps.length ? '' : 'disabled'} aria-label="Older version">‹</button>
        <span class="sm"><b>Plan v${cur.version}</b> <span class="mut">of ${ps.length}</span></span>
        <button class="ib sm" type="button" data-pver="${i > 0 ? ps[i - 1].version : ''}" ${i > 0 ? '' : 'disabled'} aria-label="Newer version">›</button>
        ${pill(st === 'approved' ? 'Approved' : st === 'skipped' ? 'Skipped' : st === 'superseded' ? 'Replaced' : 'Draft', st === 'approved' ? 'ok' : '')}
        <span class="mut sm">${esc(S(cur.source) === 'her' ? 'Edited by you' : 'Written by Hoola')} · ${esc(clockOf(tsec(cur.at)))}</span><span class="sp"></span>
        ${THREAD.planEdit ? '' : `<button class="b sm" type="button" data-act="plan-comment" title="Select a part of the plan first">Comment on selection</button><button class="b sm" type="button" data-act="plan-edit">Edit</button>
        ${st === 'draft' ? `<button class="b sm" type="button" data-act="plan-skip" data-ver="${cur.version}">Skip</button><button class="b pri sm" type="button" data-act="plan-approve" data-ver="${cur.version}">Approve</button>` : ''}`}</div>
      <div class="main" style="max-width:820px">${THREAD.planEdit
        ? `<form data-form="plan-edit"><textarea id="wsPlanEd" class="in" rows="24" maxlength="30000" style="width:100%;font-family:'JetBrains Mono',monospace;font-size:13px">${esc(cur.text)}</textarea>
           <div class="inl" style="justify-content:flex-end"><button class="b" type="button" data-act="plan-edit-x">Cancel</button><button class="b pri" type="submit">Save as a new version</button></div></form>`
        : `<article class="plandoc ho">${planMd(cur.text)}</article>`}</div>`;
  }
  async function loadInstr() {
    const box = $('#wsInstr'); if (!box || !CUR) return;
    try { const r = await api('GET', `/api/sites/${enc(CUR.id)}/instructions`); if (box.isConnected && !box.dataset.touched) { box.value = S(r.text); countInstr(); } } catch {}
  }
  function countInstr() { const b = $('#wsInstr'), c = $('#wsInstrN'); if (b && c) c.textContent = `${b.value.length.toLocaleString('en-IN')} / 10,000`; }

  function drawMsgs() {
    const box = $('#wsMsgs'); if (!box) return;
    if (!box.querySelector('#wsHist')) {
      box.innerHTML = `<div id="wsHist" class="hist"></div><div id="wsWork"></div><div id="wsLiveBox" class="livebox" hidden></div><div id="wsQ"></div>
        <button class="jump" type="button" data-act="jump-latest" hidden>${ico('down', 14)}<span>Latest</span></button>`;
      box.addEventListener('scroll', () => { THREAD.pinned = box.scrollHeight - box.scrollTop - box.clientHeight < 60; const j = box.querySelector('.jump'); if (j) j.hidden = THREAD.pinned || !THREAD.userScrolled; }, {passive: true});
      ['wheel', 'touchmove', 'keydown'].forEach(k => box.addEventListener(k, () => { THREAD.userScrolled = true; }, {passive: true}));   // only HER scrolling up shows Latest
      THREAD.liveR = null;
    }
    const all = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
    const first = all.findIndex(r => r.role === 'user');
    const rows = first < 0 ? [] : all.slice(first);
    const s = rows.map(r => r.id).join(',') + '|' + THREAD.waiting + '|' + L(THREAD.steps).length + '|' + L(THREAD.costs).length + '|' + THREAD.queue.length + '|' + THREAD.thoughts.size + '|' + [...OPEN_T].join(',');
    const hist = $('#wsHist');
    if (s !== THREAD.sig) {
      THREAD.sig = s;
      const shown = rows.slice(-40);
      const t0 = tsec(shown[0]?.at);
      const day = t0 ? `<div class="dday">${new Date(t0 * 1000).toDateString() === new Date().toDateString() ? 'Today' : new Date(t0 * 1000).toLocaleDateString([], {day: 'numeric', month: 'short'})} · ${esc(clockOf(t0))}</div>` : '';
      const turns = turnsOf(shown);
      hist.innerHTML = rows.length ? day + turns.map((t, i) => {
        let h = '';
        const nextStart = Number(turns[i + 1]?.start) || 0;
        if (t.user) {
          const editing = THREAD.editing === S(t.user.id);
          h += editing ? `<form class="meed" data-form="resend" data-mid="${esc(S(t.user.id))}" data-at="${Number(t.start) || 0}"><label class="sr" for="wsReEd">Edit your message</label>
              <textarea id="wsReEd" rows="3" maxlength="4000">${esc(clean(t.user.text))}</textarea>
              <div class="inl"><span class="mut sm">${verBefore(t.start) && verBefore(t.start) < Number(CUR?.version) ? `The site goes back to v${verBefore(t.start)} first (later changes stay in History).` : 'Sends it again.'}</span><span class="sp"></span>
              <button class="b sm" type="button" data-act="msg-cancel">Cancel</button><button class="b sm pri" type="submit">${verBefore(t.start) && verBefore(t.start) < Number(CUR?.version) ? 'Revert and resend' : 'Resend'}</button></div></form>`
            : `<div class="mewrap"><div class="me" data-mid="${esc(S(t.user.id))}">${esc(clean(t.user.text))}${fileChips(t.user.files)}</div>${S(t.user.id).startsWith('local-') || THREAD.waiting ? '' : `<button class="ib sm meedit" type="button" data-act="msg-edit" data-mid="${esc(S(t.user.id))}" aria-label="Edit and resend this message" title="Edit">${ico('edit', 13)}</button>`}</div>`;
        }
        if (!t.reply) return h;
        const made = versionsIn(t.start, nextStart), before = verBefore(t.start), top = made.length ? Math.max(...made) : 0;
        const vfoot = top ? `<div class="vfoot">${pill('Version ' + top, '')}${made.length > 1 ? `<span class="mut sm">${made.length} versions</span>` : ''}<span class="sp"></span>
            <button class="b sm ghost" type="button" data-act="ver-bm" data-ver="${top}">${ico('star', 13)}<span>Bookmark</span></button>
            ${before && restorable(before) ? `<button class="b sm" type="button" data-act="undo-turn" data-ver="${before}" data-top="${top}">${ico('back', 13)}<span>Undo this change</span></button>` : ''}</div>` : '';
        const took = t.start && t.end > t.start ? t.end - t.start : 0, steps = L(t.steps), k = 'turn-' + t.reply.id;
        const inr = t.start ? costFor(t.start, t.end) : null;
        const th = Number(THREAD.thoughts.get(tkey(t.reply.text))) || 0;   // how long the model thought for THIS answer
        const bits = [th >= 1 ? `Thought for ${dur(th)}` : '', took >= 1 ? `Worked for ${dur(took)}` : '', steps.length ? `${steps.length} step${steps.length > 1 ? 's' : ''}` : '', rs(inr)].filter(Boolean);
        const head = bits.length ? `<div class="turnhead"><details class="actd turnw" data-k="${k}"${OPEN_T.has(k) ? ' open' : ''}><summary>${esc(bits.join(' · '))}</summary>${steps.length ? stepList({steps}) : ''}</details>
          <button class="ib sm" type="button" data-act="details" data-ta="${t.start}" data-tb="${t.end}" title="Timeline and changes" aria-label="Details of this answer">${ico('list', 14)}</button></div>` : '';
        const um = modeOfRow(t.user), sb = startBuild(t.reply.text), body = sb ? sb.text : S(t.reply.text);
        return h + head + who(t.end) + `<div class="ho">${um === 'plan' ? planMd(body) : md(body)}</div>` + (um === 'plan' ? planCard(body) : '') + (sb ? buildCard(sb.ask) : '') + vfoot;
      }).join('') : `${S(CUR?.brief).trim() ? `<div class="me">${esc(clean(S(CUR.brief)))}</div>` : ''}${who(0)}<div class="ho"><p>${esc(S(CUR?.say) || 'Ask for anything on this website.')}</p>${CUR?.name_by === 'hoola' ? `<p class="mut sm">I named it <b>${esc(name(CUR))}</b>. Prefer your own name? Use the menu next to the name and pick Rename.</p>` : ''}</div>
         <div class="mut sm">This chat is only about ${esc(name(CUR || {}))}. It stays here, not in your home chat.</div>
         <div style="display:flex;flex-wrap:wrap;gap:6px">${['Add a shop with cart', 'Add online payments', 'Add a Hindi version', 'Add booking slots'].map(t => `<button class="chip" type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;
      if (THREAD.scrollTo) { const el = hist.querySelector(`[data-mid="${CSS.escape(THREAD.scrollTo)}"]`); THREAD.scrollTo = ''; if (el) box.scrollTop = Math.max(0, el.offsetTop - 12); }
      else keepPinned();
    }
    drawWork(); drawQueue();
  }
  function drawQueue() {
    const q = $('#wsQ'); if (!q) return;
    q.innerHTML = THREAD.queue.map((r, i) => `<div class="me queued" data-mid="${esc(S(r.id))}">${esc(clean(r.text))}${fileChips(r.files)}
      ${i === 0 ? `<span class="qacts"><button class="b sm" type="button" data-act="stop-turn" title="Stop the current work so this runs next">Interrupt</button></span>` : ''}</div>`).join('');
  }
  function keepPinned() { const box = $('#wsMsgs'); if (box && THREAD.pinned) box.scrollTop = box.scrollHeight; }
  /* the working card under her message: thinking shimmer + the live steps + the clock + Stop */
  function drawWork() {
    const w = $('#wsWork'); if (!w) return;
    if (!THREAD.waiting) { w.innerHTML = ''; return; }
    const since = THREAD.startedS || nowS();
    const steps = stepsBetween(since), cur = [...steps].reverse().find(x => x.state === 'run');
    const thinking = THREAD.think && !THREAD.think.end;
    const label = thinking ? '' : cur ? pastLabel(cur.label, 'run') : steps.length ? 'Working on the next step' : (THREAD.live ? 'Writing the answer' : 'Reading your ask');
    w.innerHTML = `<div class="working wcard" aria-live="polite"><div class="step whead"><span class="spin" aria-hidden="true"></span>
        <span class="wt">${thinking ? `<b class="thinking">Thinking…</b>` : `<b>${steps.length ? `Working · step ${steps.length}` : 'Hoola is working'}</b><span>${esc(label)}</span>`}</span>
        <span class="tm" data-t0="${since}"></span><button class="b sm" type="button" data-act="stop-turn" title="Stop after the step it is on">Stop</button></div>
      ${steps.length ? stepList({steps}) : ''}</div>`;
    startTick(); keepPinned();
  }
  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;
      const local = THREAD.rows.filter(x => S(x.id).startsWith('local-') && !L(r.messages).some(m => m.role === 'user' && clean(m.text) === clean(x.text)));
      const waitingTexts = new Set(THREAD.queue.map(q => clean(q.text)));
      THREAD.rows = [...L(r.messages).filter(m => !(m.role === 'user' && waitingTexts.has(clean(m.text)))), ...local];
    } catch { return; }
    if (!THREAD.waiting) {                                   // a reload while Hoola is still answering: pick it up again
      const talk = THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
      const last = talk[talk.length - 1];
      if (last && last.role === 'user' && nowS() - tsec(last.at) < 900) {
        THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = tsec(last.at);
        THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      }
    }
    if (THREAD.waiting || !THREAD.stepsRead) { await Promise.all([readSteps(c), readCosts(c)]); THREAD.stepsRead = true; if (c !== THREAD.conv) return; }
    if (THREAD.waiting) {
      let snap = null;
      try { const res = await api('GET', `/api/conversations/${enc(c)}/live`, undefined, {raw: true}); if (res.status === 200) snap = await res.json(); } catch {}
      if (snap && S(snap.text) && !THREAD.pacer) showLive(S(snap.text), true);   // a reload mid-reply continues the text
      // answered = a reply AFTER her own newest line (a new chat starts with a greeting, which is not the answer)
      const talk = THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
      let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
      const answered = lu >= 0 && talk.slice(lu + 1).some(m => m.role === 'assistant');
      if (answered && !snap && !THREAD.queue.length) {
        if (THREAD.think) { THREAD.think.end = THREAD.think.end || nowS(); THREAD.lastThink = THREAD.think; THREAD.think = null; thoughtFor([...talk].reverse().find(m => m.role === 'assistant')?.text); }
        THREAD.waiting = false; THREAD.startedS = 0; endLive(); reload();
      }
      else if (Date.now() - (THREAD.started || Date.now()) > 15 * 60e3) THREAD.waiting = false;
    }
    drawMsgs();
    // the stream carries the work; this read is the fallback (stream down) and a slow safety net (stream up)
    clearTimeout(THREAD.timer);
    if (THREAD.waiting || !THREAD.connected) THREAD.timer = setTimeout(readThread, THREAD.connected ? 4000 : 1500);
  }
  /* ----- attachments: paperclip, drop, paste (a long paste becomes a chip that travels as a .txt file) ----- */
  function drawTray() {
    const t = $('#wsTray'); if (!t) return;
    const fs = L(THREAD.files);
    t.hidden = !fs.length;
    t.innerHTML = fs.map((f, i) => `<span class="fchip${f.state === 'up' ? ' up' : f.state === 'bad' ? ' bad' : ''}" title="${esc(f.note || '')}">${ico(f.kind === 'paste' ? 'doc' : 'clip', 12)}<span class="ell">${esc(f.label)}</span><button type="button" class="x" data-act="att-x" data-i="${i}" aria-label="Remove ${esc(f.label)}">×</button></span>`).join('');
  }
  async function addFile(file, label, kind) {
    const f = {label: label || file.name || 'File', kind: kind || 'file', state: 'up', id: ''};
    THREAD.files.push(f); drawTray();
    try {
      const c = await ensureConv();
      const fd = new FormData(); fd.append('file', file, file.name || 'file.txt');
      const r = await api('POST', `/api/conversations/${enc(c)}/files`, undefined, {form: fd});
      f.id = S(r.file_id); f.state = f.id ? 'ok' : 'bad'; if (!f.id) f.note = 'Could not attach';
    } catch (e) { f.state = 'bad'; f.note = e.message; toast(e.message, true); }
    drawTray();
  }
  function pasted(ev) {
    const t = ev.clipboardData?.getData('text') || '';
    const imgs = [...(ev.clipboardData?.files || [])];
    if (imgs.length) { ev.preventDefault(); imgs.slice(0, 6).forEach(f => addFile(f, f.name || 'Pasted picture', 'file')); return; }
    if (t.length < LONG_PASTE) return;
    ev.preventDefault();
    const kind = /^\s*[[{]/.test(t) ? 'JSON' : /\t|,.*,.*\n/.test(t) && /\n/.test(t) ? 'Table' : /[{};]\s*\n/.test(t) ? 'Code' : 'Text';
    const lines = t.split('\n').length;
    addFile(new File([t], `pasted-${kind.toLowerCase()}.txt`, {type: 'text/plain'}), `Pasted ${kind.toLowerCase()} · ${lines} lines`, 'paste');
  }
  async function ask(text, opts = {}) {
    text = S(text).trim(); if (!text || !CUR) return;
    if (L(THREAD.files).some(f => f.state === 'up')) return toast('Wait a moment: a file is still attaching.', true);
    let mode = opts.mode || chatMode();
    const cmd = /^\/(plan|chat|build)\b\s*/i.exec(text);          // v0.782 "/plan ..." = this one message in that mode
    if (cmd) { mode = cmd[1].toLowerCase(); text = text.slice(cmd[0].length).trim(); if (!text) { setChatMode(mode); return; } }
    const v = CUR;
    const files = L(THREAD.files).filter(f => f.state === 'ok' && f.id);
    try {
      const c = await ensureConv();
      THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      const id = 'local-' + Date.now(), busy = THREAD.waiting, row = {id, role: 'user', text, mode, files: files.map(f => ({name: f.label}))};
      if (busy) THREAD.queue.push(row);                       // she sent while Hoola works: it waits its turn, greyed, at the bottom
      else { THREAD.rows.push(row); THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = nowS(); THREAD.think = null; THREAD.lastThink = null; endLive(); }
      THREAD.files = []; drawTray();
      if (busy) { THREAD.pinned = true; drawQueue(); keepPinned(); } else { THREAD.scrollTo = id; THREAD.pinned = false; THREAD.sig = ''; drawMsgs(); }
      const hints = [`Web Studio: this chat is only about website ${S(v.number)} "${name(v)}" (site id ${S(v.id)}). Work on THIS website with the website tool; never start a new website unless I ask for one.`, `mode: ${mode}`];
      if (mode === 'plan') hints.push('Plan mode: reply with the PLAN only (## Goal, ## What changes, ## What stays the same, ## Steps, ## Questions if any). Change nothing.');
      if (mode === 'chat') hints.push('Chat mode: talk only, change nothing (the start-building line is in your rules).');   // no square brackets: a hint must stay one strippable [..] line
      for (const h of L(opts.hints)) hints.push(h);
      if (YW.sel.length && S(YW.site) === S(v.id)) {          // v0.795 E3: the elements she pointed at reach this turn once
        try { await api('PUT', `/api/sites/${enc(v.id)}/selection`, {items: YW.sel.map(x => ({k: x.k, e: x.e}))}); hints.push(`selected elements: ${YW.sel.length} (listed in your rules as selected_elements)`); }
        catch (er) { toast(er.message, true); }
        YW.sel = []; drawPills(); ywPost({t: 'selected', items: []}); ywPanel();
      }
      await api('POST', `/api/conversations/${enc(c)}/messages`, {text, client_id: 'ws-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8), hints,
        ...(files.length ? {files: files.map(f => f.id).slice(0, 6)} : {})});
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, THREAD.connected ? 4000 : 900);
    } catch (e) { THREAD.waiting = false; drawMsgs(); toast(e.message, true); }
  }
  async function stopTurn() {
    if (!THREAD.conv) return;
    try { await api('POST', `/api/conversations/${enc(THREAD.conv)}/stop`, {}); toast('Stopping after the step it is on.'); }
    catch (e) { toast(e.message, true); }
  }
  /* ----- Details: the turn's Timeline and Changes, where the preview sits ----- */
  function detailsView(pane, v) {
    const a = Number(THREAD.detail?.a) || 0, b = Number(THREAD.detail?.b) || 0;
    const steps = stepsBetween(a, b), tab = THREAD.detail?.tab === 'changes' ? 'changes' : 'timeline';
    const nextUser = L(THREAD.rows).map(r => r.role === 'user' ? tsec(r.at) : 0).filter(t => t > b).sort((x, y) => x - y)[0] || 0;
    const vers = L(v.versions).filter(x => { const t = tsec(x.at); return t >= a - 2 && (!nextUser || t < nextUser); });
    const inr = costFor(a, b);
    const tl = steps.length ? `<ol class="tline">${steps.map(x => `<li class="${x.state === 'error' ? 'bad' : x.state === 'run' ? 'run' : 'ok'}"><span class="tdot" aria-hidden="true"></span>
        <div class="tl1"><b>${esc(pastLabel(x.label, x.state))}</b><span class="mut sm">${esc(clockOf(x.at))}${x.end ? ' · ' + dur(x.end - x.at) : ''}</span></div></li>`).join('')}</ol>`
      : '<p class="mut">This answer used no tools: Hoola replied from what it already knew.</p>';
    const ch = vers.length ? vers.map(x => `<div class="ver">${pill('v' + S(x.version), '')}<span class="sp ell">${esc(S(x.note) || 'Version')} <span class="mut sm">· ${esc(clockOf(tsec(x.at)))}</span></span>
        ${Number(x.version) > 1 ? `<button class="b sm" type="button" data-act="detail-compare" data-from="${Number(x.version) - 1}" data-to="${Number(x.version)}">Before / after</button>` : ''}</div>`).join('')
      : '<p class="mut">No new version came from this answer.</p>';
    pane.innerHTML = `<div class="dtop"><button class="b sm" type="button" data-view="preview">${ico('back', 14)}<span>Back to preview</span></button>
        <div class="seg" role="tablist" aria-label="Details"><button type="button" role="tab" data-dtab="timeline" aria-pressed="${tab === 'timeline'}">Timeline</button><button type="button" role="tab" data-dtab="changes" aria-pressed="${tab === 'changes'}">Changes</button></div>
        <span class="sp"></span><span class="mut sm">${esc([b > a ? 'Worked for ' + dur(b - a) : '', steps.length ? `${steps.length} step${steps.length > 1 ? 's' : ''}` : '', rs(inr)].filter(Boolean).join(' · '))}</span></div>
      <div class="main" style="max-width:820px">${tab === 'timeline' ? tl : ch}</div>`;
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
  async function editSend(body) {
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/edit`, body); toast(S(r?.say) || 'Saved.'); }
    catch (e) { toast(e.message, true); }
    const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src;
  }
  async function upload(kind, file, about) {
    const fd = new FormData(); fd.append('file', file); fd.append('about', about || '');
    const r = await api('POST', `/api/sites/${enc(CUR.id)}/${kind === 'photo' ? 'photo' : 'media'}`, undefined, {form: fd});
    return S(r.name);
  }
  addEventListener('message', async ev => {
    const d = ev.data;
    if (!d || d.hoola !== 'edit' || !CUR || !EDIT) return;
    const fr = APP.querySelector('.frame iframe'); if (!fr || ev.source !== fr.contentWindow) return;   // only our own preview
    const k = S(d.k), e = S(d.e);
    if (d.page != null) YW.page = S(d.page);
    if (d.t === 'ready') return ywSync();
    if (d.t === 'where') { const w = YW.wait; YW.wait = null; if (w) w({y: Number(d.y) || 0, page: S(d.page)}); return; }
    if (d.t === 'select') { YW.sel = L(d.items).slice(0, 8).map(x => ({k: S(x.k), e: S(x.e), name: S(x.name)})); drawPills(); ywPanel(); return; }
    if (d.t === 'comment') return ywComment(k, e, S(d.name));
    if (d.t === 'text') return editSend({k, e, op: 'text', value: S(d.value)});
    if (d.t === 'remove') { if (confirm(`Remove "${S(d.text).slice(0, 60)}" from the page? (Undo brings it back)`)) editSend({k, e, op: 'remove'}); return; }
    if (d.t === 'link') {
      const f = await dialog('Link', `<label class="fld">Where should "${esc(S(d.text).slice(0, 40))}" go?<input class="in" name="href" value="${esc(S(d.href))}" placeholder="https://… · tel:+91… · contact/"></label>`);
      if (f) editSend({k, e, op: 'link', value: S(f.get('href')).trim()}); return;
    }
    if (d.t === 'image') {
      const ph = L(CUR.photos);
      const f = await dialog('Change the picture', `${ph.length ? `<label class="fld">Use one of your photos<select class="in" name="pick"><option value="">—</option>${ph.map(p => `<option value="${esc(S(p))}">${esc(S(p))}</option>`).join('')}</select></label>` : ''}
        <label class="fld">${ph.length ? 'Or upload' : 'Upload'} a photo (JPEG, PNG, WebP)<input type="file" name="file" accept="image/jpeg,image/png,image/webp"></label>`);
      if (!f) return;
      let pick = S(f.get('pick')); const file = f.get('file');
      try { if (file && file.size) pick = await upload('photo', file, ''); } catch (er) { return toast(er.message, true); }
      if (pick && pick !== S(d.img)) editSend({k, e, op: 'image', value: pick}); return;
    }
    if (d.t === 'add') {
      const f = await dialog('Add below this', `<label class="fld">What<select class="in" name="kind"><option value="photo">Photo</option><option value="video">Video (MP4)</option><option value="audio">Audio</option><option value="file">Download file</option><option value="youtube">YouTube link</option></select></label>
        <label class="fld">File<input type="file" name="file"></label><label class="fld">YouTube link<input class="in" name="url" placeholder="https://youtu.be/…"></label>
        <label class="fld">Caption (optional)<input class="in" name="caption" maxlength="160"></label>`);
      if (!f) return;
      const kind = S(f.get('kind')), spec = {kind, caption: S(f.get('caption')).trim()};
      try {
        if (kind === 'youtube') { spec.url = S(f.get('url')).trim(); if (!spec.url) return toast('Paste the YouTube link.', true); }
        else { const file = f.get('file'); if (!file || !file.size) return toast('Choose a file to add.', true); spec.name = await upload(kind, file, spec.caption); }
      } catch (er) { return toast(er.message, true); }
      return editSend({k, e, op: 'insert', value: JSON.stringify(spec)});
    }
    if (d.t === 'ai') { const t = $('#wsTh'); if (t) { t.value = `"${S(d.text).slice(0, 80)}" ko `; t.focus(); } }
  });

  /* ================= events ================= */
  APP.addEventListener('click', async e => {
    const b = e.target.closest('button, a'); if (!b || !APP.contains(b)) return;
    const d = b.dataset;
    if (d.menu) { e.preventDefault(); openMenu(b, d.menu); return; }
    if (d.tpl) { openTpl(d.tpl); return; }
    if ('improve' in d) {                       // HOOLA PROMPTING: what Hoola understood, as chips she can change; never a silent rewrite
      const ta = $('#wsAsk'); if (!ta) return;
      if (IMP_BACK !== null && ta.value === IMP_DONE) { ta.value = IMP_BACK; IMP_BACK = null; IMP_DONE = ''; b.textContent = 'Improve'; ta.focus(); return; }
      const mine = ta.value;
      if (!mine.trim()) { ta.focus(); toast('Write one line about the website first.'); return; }
      IMPUI = IMPUI || window.HoolaImprove({api, esc, toast});
      IMPUI.open(mine, {section: 'web', onUse: t => { ta.value = S(t).slice(0, 2000); IMP_BACK = mine; IMP_DONE = ta.value; b.textContent = 'Undo'; ta.focus(); }});
      return; }
    if (d.act === 'tpl-more') { loadTpl(false); return; }
    if (d.mode) { store.set(MODE_KEY, d.mode); APP.querySelectorAll('[data-mode]').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.mode === d.mode)));
      const n = $('#wsModeNote'); if (n) n.textContent = d.mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: 3 full looks first'; return; }
    if (d.cmode) { setChatMode(d.cmode); return; }
    if (d.chip) { HOME.kind = HOME.kind === d.chip ? '' : d.chip; drawStarters(); return; }
    if (d.starter) { chooseStarter(d.starter); return; }
    if (d.type) { if (location.hash && location.hash !== '#/') { PREFILL = `${d.type} ki website banao: `; go('#/'); return; }
      const t = $('#wsAsk'); if (t) { t.value = `${d.type} ki website banao: `; t.focus(); t.setSelectionRange(t.value.length, t.value.length); } return; }
    if (d.src) { if (d.src === 'focus') { drawSource(''); $('#wsAsk')?.focus(); } else { drawSource(d.src); $('#wsSrc input')?.focus(); } return; }
    if (d.live === 'follow' || d.live === 'code') {        // v0.664 live build toggles
      if (d.live === 'follow') { LIVE.follow = !LIVE.follow; b.setAttribute('aria-pressed', String(LIVE.follow)); if (LIVE.follow) followPage(); }
      else { LIVE.code = !LIVE.code; drawPane(); }
      return;
    }
    if (d.lpage) { LIVE.follow = false; APP.querySelector('[data-live="follow"]')?.setAttribute('aria-pressed', 'false'); setLivePage(d.lpage); return; }
    if (d.lcode) { LIVE.codeKey = d.lcode; LIVE.codePinned = true; drawLiveBits(); return; }
    if (d.act === 'details') { THREAD.detail = {a: Number(d.ta) || 0, b: Number(d.tb) || 0, tab: 'timeline'}; VIEW = 'details'; drawPane(); return; }
    if (d.dtab) { if (THREAD.detail) THREAD.detail.tab = d.dtab; drawPane(); return; }
    if (d.act === 'detail-compare') { LIVE.justDone = {site: S(CUR.id), from: Number(d.from), to: Number(d.to)}; LIVE.compare = true; VIEW = 'preview'; drawPane(); return; }
    if (d.act === 'stop-turn') { stopTurn(); return; }
    if (d.act === 'plan-open') { THREAD.planVer = Number(d.ver); THREAD.planEdit = false; VIEW = 'plans'; drawPane(); return; }
    if (d.act === 'plan-approve') { approvePlan(d.ver).catch(er => toast(er.message, true)); return; }
    if (d.act === 'plan-skip') { planStatus(d.ver, 'skip').then(() => toast('Plan skipped. Nothing was changed.')).catch(er => toast(er.message, true)); return; }
    if (d.act === 'plan-edit') { THREAD.planEdit = true; drawPane(); return; }
    if (d.act === 'plan-edit-x') { THREAD.planEdit = false; drawPane(); return; }
    if (d.pver) { THREAD.planVer = Number(d.pver); THREAD.planEdit = false; drawPane(); return; }
    if (d.act === 'plan-comment') {
      const sel = S(window.getSelection()?.toString()).trim(), doc = APP.querySelector('.plandoc');
      if (!sel || !doc || !doc.contains(window.getSelection().anchorNode)) return toast('Select a part of the plan first, then press Comment.', true);
      const fd = await dialog('What should change in this part?', `<blockquote class="mut sm" style="margin:8px 0;border-left:3px solid var(--line);padding-left:8px">${esc(sel.slice(0, 400))}</blockquote><textarea name="c" class="in" rows="3" required style="width:100%"></textarea>`);
      const c = S(fd?.get('c')).trim(); if (!c) return;
      ask(`In plan v${THREAD.planVer}, change this part: "${sel.slice(0, 600)}" - ${c}. Write the whole updated plan.`, {mode: 'plan'});
      return;
    }
    if (d.act === 'sb-build' || d.act === 'sb-skip') {
      (THREAD.sbDone = THREAD.sbDone || new Set()).add(tkey(d.sb)); THREAD.sig = ''; drawMsgs();
      if (d.act === 'sb-build') { setChatMode('build'); ask(S(d.sb), {mode: 'build'}); }
      return;
    }
    if (d.act === 'attach') { $('#wsFile')?.click(); return; }
    if (d.act === 'att-x') { THREAD.files.splice(Number(d.i), 1); drawTray(); return; }
    if (d.act === 'jump-latest') { const bx = $('#wsMsgs'); if (bx) { THREAD.pinned = true; bx.scrollTop = bx.scrollHeight; } b.hidden = true; return; }
    if (d.act === 'compare') { LIVE.compare = !LIVE.compare; drawPane(); return; }
    if (d.act === 'jd-close') { LIVE.justDone = null; LIVE.compare = false; drawPane(); return; }
    if (d.view) { VIEW = d.view; EDIT = false; history.replaceState(null, '', `#/site/${enc(CUR.id)}/${VIEW}`); drawPane(); return; }
    if (d.dev) { DEVICE = d.dev; drawPane(); return; }
    if (d.look) { LOOK = Number(d.look) || 0; drawPane(); return; }
    if (d.file) { openFile(d.file); return; }
    if (d.coll) { openColl(d.coll); return; }
    if (d.ask != null && d.ask !== '') {
      if (d.ask.endsWith(': ')) { const t = $('#wsTh'); if (t) { t.value = d.ask; t.focus(); } return; }
      ask(d.ask); return;
    }
    const act = d.act; if (!act) return;
    if (act === 'new') { if (location.hash && location.hash !== '#/') go('#/'); else $('#wsAsk')?.focus(); return; }
    if (act === 'reload') { const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src; return; }
    if (act === 'select') {
      if (!CUR || !hasVersion(CUR)) return toast('Selecting on the page opens once the first version is built.', true);
      VIEW = 'preview';
      try { const em = await api('POST', `/api/sites/${enc(CUR.id)}/edit-mode`, {}); YW.tokens = M(em?.tokens); YW.mode = 'select'; EDIT = true; ywLoadComments(); drawPane(); } catch (er) { toast(er.message, true); }
      return;
    }
    if (act === 'edit-done') { EDIT = false; YW.strokes = []; YW.notes = []; await reload(); return; }
    if (act === 'dft-accept' || act === 'dft-discard') return draftAct(act, d.did, b.closest('[data-draft]'));   // v0.837 L13
    if (act === 'ver-restore') return restoreVer(Number(d.ver));     // v0.808 WAPAS
    if (act === 'ver-bm') return bookmarkVer(Number(d.ver));
    if (act === 'ver-diff') return diffVer(Number(d.ver));
    if (act === 'undo-turn') return restoreVer(Number(d.ver), `Undo this change: put the site back to v${d.ver} (as it was before this answer)?`);
    if (act === 'msg-edit') { THREAD.editing = d.mid; THREAD.sig = ''; drawMsgs(); $('#wsReEd')?.focus(); return; }
    if (act === 'msg-cancel') { THREAD.editing = ''; THREAD.sig = ''; drawMsgs(); return; }
    if (act === 'err-fix') return fixError(d.id);           // v0.802 GALTI PAKDO
    if (act === 'err-more') { GALTI.open[d.id] = !GALTI.open[d.id]; return drawErrors(); }
    if (act === 'err-ign') { try { await api('POST', `/api/sites/${enc(CUR.id)}/errors/${enc(d.id)}/ignored`, {}); } catch (er) { return toast(er.message, true); } return loadErrors(); }
    if (act && act.startsWith('pt-') || act === 'pill-x' || act === 'sty' || act.startsWith('cm-') || act.startsWith('dr-')) return ywAct(act, b);
    if (BUSY) return;
    const id = CUR ? enc(CUR.id) : '';
    BUSY = true; b.setAttribute('aria-disabled', 'true');
    try {
      if (act === 'approve') { await api('POST', `/api/sites/${id}/plan`, {conversation_id: await ensureConv().catch(() => '')}); toast('Making three complete looks.'); await reload(); }
      else if (act === 'pick-look') {
        await api('POST', `/api/sites/${id}/look`, {index: LOOK, conversation_id: await ensureConv().catch(() => '')});
        toast('Building your website in this look.'); await reload();
      } else if (act === 'approve-plan') {
        const pid = parts()[1];
        const conv = store.get('hoola.ws.spec.conv.' + pid);
        // v0.707 her tap shows at once: the button turns into a working line and the chat says what is starting
        b.disabled = true; b.innerHTML = `<span class="spin" aria-hidden="true"></span>Starting the build`;
        const box = $('#wsPlanMsgs');
        if (box) { const w = document.createElement('div'); w.className = 'step'; w.dataset.work = '1';
          w.innerHTML = `<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>Building this plan · the website opens in a moment<span class="sp"></span><span class="tm" data-t0="${nowS()}"></span>`;
          box.appendChild(w); box.scrollTop = box.scrollHeight; startTick(); }
        let r;
        try { r = await api('POST', `/api/site-architect/${enc(pid)}/approve`, {hash: d.hash, conversation_id: conv}); }
        catch (er) {
          b.disabled = false; b.textContent = 'Build this plan';
          const w = box?.querySelector('[data-work]'); if (w) { w.className = 'li bad'; w.textContent = er.message; }
          throw er;
        }
        await loadLists();
        const site = SITES.find(x => S(x.id) === S(r.site) || S(x.number) === S(r.number));
        if (site && conv) store.set(convKey(site.id), conv);
        toast(S(r.say).slice(0, 160) || 'Building the plan.');
        go(site ? '#/site/' + enc(S(site.id)) : '#/sites');
      } else if (act === 'use-design') {
        const brief = S($('#wsAsk')?.value).trim();
        const r = await api('POST', '/api/site-design/use', {token: d.token, keep: d.keep === '1', brief});
        toast(S(r.say).slice(0, 160) || 'Design added.');
        if (r.site) go('#/site/' + enc(S(r.site)));
      } else if (act === 'delete') {
        if (!confirm(`Delete ${name(CUR)}? Nothing has been built yet.`)) return;
        await api('DELETE', `/api/sites/${id}`); toast('Deleted.'); go('#/');
      } else if (act === 'resume') { await api('POST', `/api/sites/${id}/resume`, {}); toast('Building again.'); await reload(); }
      else if (act === 'stop') { await api('POST', `/api/sites/${id}/stop`, {}); toast('Pausing after the current part.'); await reload(); }
      else if (act === 'undo') { const r = await api('POST', `/api/sites/${id}/undo`, {}); toast(S(r?.say) || 'Undone.'); const fr = APP.querySelector('.frame iframe'); if (fr) fr.src = fr.src; }
      else if (act === 'export') {                    // v0.663 the zip lands on her computer, not only in her files
        toast(d.fmt === 'react' ? 'Packing the React + Vite project…' : 'Packing the website files…');
        const res = await api('GET', `/api/sites/${id}/download?format=${d.fmt === 'react' ? 'react' : 'zip'}`, undefined, {raw: true})
          .catch(e => { let x = {}; try { x = JSON.parse(e.message); } catch {} throw new Error(S(x.detail || x.error) || e.message); });
        const blob = await res.blob();
        const cd = res.headers.get('Content-Disposition') || '';
        const fn = decodeURIComponent((cd.match(/filename\*=UTF-8''([^;]+)/) || [])[1] || '') || `website${d.fmt === 'react' ? '-react' : ''}.zip`;
        const url = URL.createObjectURL(blob), a = document.createElement('a');
        a.href = url; a.download = fn; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        toast(`Downloaded ${fn} · ${Math.max(1, Math.round(blob.size / 1024))} KB`);
      }
      else if (act === 'launch') await launch();
      else if (act === 'golive') {
        if (!confirm(`Put ${name(CUR)} v${S(CUR.version)} live now?`)) return;
        const r = await api('POST', `/api/sites/${id}/launch`, {hash: d.hash}); toast(S(r.say) || 'Live.'); await reload();
      } else if (act === 'rollback') {
        const card = await api('POST', `/api/sites/${id}/rollback-request`, {version: Number(d.ver)});
        if (!confirm(S(card.say) || `Bring back v${d.ver} on your live addresses?`)) return;
        const r = await api('POST', `/api/sites/${id}/rollback`, {version: Number(d.ver), hash: S(card.hash)}); toast(S(r.say) || 'Restored.'); await reload();
      } else if (act === 'dns-apply') {
        if (!confirm('Add these DNS records to your domain now? Undo is there for 7 days.')) return;
        const r = await api('POST', `/api/sites-dns/${enc(d.plan)}/apply`, {hash: d.hash}); toast(S(r.say) || 'Records added.'); await reload();
      } else if (act === 'dns-undo') {
        if (!confirm('Put the DNS back the way it was?')) return;
        const r = await api('POST', `/api/sites-dns/${enc(d.plan)}/undo`, {}); toast(S(r.say) || 'Undone.'); await reload();
      } else if (act === 'dns-check') {
        const out = b.closest('[data-dns]')?.querySelector('[data-dnsout]');
        if (out) out.innerHTML = '<p class="mut sm">Asking three public DNS servers…</p>';
        const r = await api('GET', `/api/sites-dns/${enc(d.plan)}/check`);
        const rows = L(r.checks);
        if (out) out.innerHTML = `<p class="li ${r.done ? 'ok' : ''}">${r.done ? 'Seen everywhere. HTTPS is set up next, by itself.' : `${rows.filter(x => x.all).length} of ${rows.length} records are seen everywhere so far. New records take 10 to 30 minutes, sometimes a day.`}</p>
          ${rows.map(x => `<div class="kv"><code class="ell">${esc(S(x.type))} ${esc(S(x.name))}</code>${pill(x.all ? 'Seen' : 'Not yet', x.all ? 'ok' : 'warn')}</div>`).join('')}`;
      } else if (act === 'takedown') {
        if (!confirm(`Take ${name(CUR)} off the internet? Your pages, data and versions are kept.`)) return;
        const r = await api('POST', `/api/sites/${id}/takedown`, {}); toast(S(r.say) || 'Taken down.'); await reload();
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (b.isConnected) b.removeAttribute('aria-disabled'); }
  });

  APP.addEventListener('input', e => {             // v0.683 template search, as she types
    if (e.target.id !== 'wsTplQ') return;
    clearTimeout(TPL.t); TPL.t = setTimeout(() => { TPL.q = S(e.target.value).trim(); loadTpl(true); }, 250);
  });
  APP.addEventListener('change', e => {
    const k = {wsTplInd: 'sector', wsTplGoal: 'kind', wsTplStyle: 'style'}[e.target.id]; if (!k) return;
    TPL[k] = S(e.target.value); loadTpl(true);
  });
  APP.addEventListener('input', e => {
    if (e.target.id !== 'wsFind') return;
    const q = S(e.target.value).trim().toLowerCase(); let shown = 0;
    APP.querySelectorAll('#wsAll .cw').forEach(c => { const hit = !q || c.textContent.toLowerCase().includes(q); c.hidden = !hit; shown += hit; });
    const n = $('#wsNone'); if (n) n.hidden = shown > 0;
  });
  addEventListener('keydown', e => {                       // v0.667 ⌘K / Ctrl+K: a new website from anywhere in the Studio
    if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && S(e.key).toLowerCase() === 'k') {
      e.preventDefault();
      if (location.hash && location.hash !== '#/') go('#/'); else $('#wsAsk')?.focus();
      setTimeout(() => $('#wsAsk')?.focus(), 60);
    }
  });
  APP.addEventListener('keydown', e => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    if (e.target.matches?.('#wsAsk, #wsTh, #wsRev')) { e.preventDefault(); e.target.form?.requestSubmit(); }
  });

  APP.addEventListener('submit', async e => {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form;
    if (kind === 'thread') { const t = f.querySelector('textarea'); const x = S(t.value).trim(); if (!x) return; t.value = ''; return ask(x); }
    if (kind === 'resend') {                              // v0.808 Revert and resend: the site goes back first, then her edited words go
      const x = S(f.querySelector('textarea')?.value).trim(); if (!x) return;
      const before = verBefore(Number(f.dataset.at) || 0);
      if (before && before < Number(CUR?.version) && restorable(before)) {
        const ok = await restoreVer(before, `Revert and resend: put the site back to v${before} and send your edited message?`);
        if (!ok) return;
      }
      THREAD.editing = ''; THREAD.sig = '';
      return ask(x);
    }
    if (kind === 'dft-new') {                             // v0.837 L13 start a draft
      const nm = S(f.querySelector('[name=name]')?.value).trim(); if (!nm) return;
      try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/drafts`, {name: nm}); toast(S(r.say).slice(0, 160)); go('#/site/' + enc(S(r.id))); }
      catch (er) { toast(er.message, true); }
      return;
    }
    if (kind === 'instr') {
      try { await api('PUT', `/api/sites/${enc(CUR.id)}/instructions`, {text: S($('#wsInstr')?.value)}); toast('Instructions saved. Hoola reads them on every message about this site.'); }
      catch (er) { toast(er.message, true); }
      return;
    }
    if (kind === 'plan-edit') {
      try {
        const r = await api('POST', `/api/sites/${enc(CUR.id)}/plans`, {text: S($('#wsPlanEd')?.value), source: 'her', note: 'Edited by you'});
        THREAD.planEdit = false; THREAD.planVer = Number(r.version); await loadPlans(); THREAD.sig = ''; drawMsgs(); drawPane(); toast(`Saved as plan v${r.version}.`);
      } catch (er) { toast(er.message, true); }
      return;
    }
    if (BUSY) return;
    const btn = f.querySelector('[type=submit]');
    BUSY = true; if (btn) btn.disabled = true;
    try {
      if (kind === 'ask') {
        const ta = f.querySelector('textarea'), t = S(ta.value).trim(); if (!t) return toast('Write one line about the website.', true);
        const plan = store.get(MODE_KEY) === 'plan';
        let design = null;
        if (!plan && !(TPLSEL && t.includes('[Hoola template #'))) {   // v0.784 a template already has its design
          const got = await askDesign(t);
          if (got === null) { PREFILL = t; drawHome('home'); return; }
          design = got.design;
        }
        const ticket = plan ? '' : 'st-' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
        drawPending(plan, t, ticket);               // v0.707: straight into the workspace, the work shows there
        try { await startFromAsk(t, design, ticket); }
        catch (er) {
          clearInterval(drawPending._t);
          PREFILL = t; drawHome('home');            // back home with her words still in the box and the reason under it
          const note = $('#wsAskWork');
          if (note) { note.hidden = false; note.innerHTML = `<span class="li bad">${esc(er.message)} · your words are still in the box, press send again</span>`; }
          throw er;
        }
        finally { clearInterval(drawPending._t); }
      }
      else if (kind === 'old' || kind === 'shot') await readDesign(f, kind);
      else if (kind === 'revise') {
        const ta = f.querySelector('textarea'), t = S(ta.value).trim(); if (!t) return;
        const pid = parts()[1];
        const box = $('#wsPlanMsgs'), work = document.createElement('div');
        work.className = 'pending';
        work.innerHTML = `<div class="me">${esc(t)}</div><div class="step" data-work><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>Updating the plan · about a minute<span class="sp"></span><span class="tm" data-t0="${nowS()}"></span></div>`;
        box?.appendChild(work); if (box) box.scrollTop = box.scrollHeight; startTick();
        ta.value = ''; ta.readOnly = true;
        try { CARD = await api('POST', `/api/site-architect/${enc(pid)}/revise`, {words: t}); }
        catch (er) {
          const w = work.querySelector('[data-work]'); if (w) { w.className = 'li bad'; w.textContent = `${er.message} · your words are back in the box`; }
          if (ta.isConnected) { ta.readOnly = false; if (!ta.value) ta.value = t; }
          throw er;
        }
        const key = 'hoola.ws.spec.log.' + pid;
        let log = []; try { log = JSON.parse(sessionStorage.getItem(key) || '[]'); } catch {}
        log.push({me: t, done: 'Plan updated'}); try { sessionStorage.setItem(key, JSON.stringify(log.slice(-20))); } catch {}
        await openPlan(pid);
      } else if (kind === 'code') {
        const path = f.dataset.path, codeText = S(f.querySelector('textarea').value);
        const r = await api('PUT', `/api/sites/${enc(CUR.id)}/code`, {path, code: codeText}); toast(S(r?.say) || 'Saved as a new version.');
      } else if (kind === 'facts') {
        const answers = {}; new FormData(f).forEach((val, key) => { const x = S(val).trim(); if (x && x !== S(M(CUR.facts)[key])) answers[key] = x; });
        if (!Object.keys(answers).length) return toast('Nothing changed.');
        await api('POST', `/api/sites/${enc(CUR.id)}/answers`, {answers}); toast('Details saved.'); await reload();
      } else if (kind === 'domain') {
        const dom = S(f.querySelector('input').value).trim(); if (!dom) return toast('Write the domain first.', true);
        const r = await api('POST', `/api/sites/${enc(CUR.id)}/domain`, {domain: dom}); toast(S(r.say) || 'Domain added: follow the records shown.'); await reload();
      } else if (kind === 'moves') {
        const keep = new Set([...f.querySelectorAll('input[name=keep]:checked')].map(x => x.value));
        const drop = [...f.querySelectorAll('input[name=keep]')].map(x => x.value).filter(x => !keep.has(x));
        if (!confirm(`Send ${keep.size} old address(es) to their new pages?`)) return;
        const r = await api('POST', `/api/sites/${enc(CUR.id)}/moves`, {hash: f.dataset.hash, drop}); toast(S(r.say) || 'Saved.'); await reload();
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (btn?.isConnected) btn.disabled = false; }
  });

  addEventListener('keydown', e => {                       // v0.782 Alt+P cycles Build / Plan / Chat in a site chat
    if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === 'p' || e.key === 'P' || e.code === 'KeyP') && $('#wsTh')) {
      e.preventDefault(); const m = chatMode(); setChatMode(MODES[(MODES.indexOf(m) + 1) % MODES.length]);
    }
  });
  APP.addEventListener('input', e => { if (e.target.id === 'wsInstr') { e.target.dataset.touched = '1'; countInstr(); } });
  APP.addEventListener('paste', e => { if (e.target.id === 'wsTh') pasted(e); });          // v0.777 attachments
  APP.addEventListener('change', e => { if (e.target.id === 'wsFile') { [...e.target.files].slice(0, 6).forEach(f => addFile(f)); e.target.value = ''; } });
  APP.addEventListener('dragover', e => { if (e.target.closest?.('.chat') && e.dataTransfer?.types?.includes('Files')) { e.preventDefault(); e.target.closest('.chat').classList.add('drop'); } });
  APP.addEventListener('dragleave', e => { e.target.closest?.('.chat')?.classList.remove('drop'); });
  APP.addEventListener('drop', e => { const c = e.target.closest?.('.chat'); if (!c || !e.dataTransfer?.files?.length) return; e.preventDefault(); c.classList.remove('drop'); [...e.dataTransfer.files].slice(0, 6).forEach(f => addFile(f)); });

  // v0.814 APP ENGINE 1: appengine.js draws the app pages with the Studio's own helpers and sidebar
  window.HoolaWSKit = {api, esc, enc, ico, toast, sidebar, go, store, pill, ago, md: window.HoolaMD, APP, clean};
  route();
})();
