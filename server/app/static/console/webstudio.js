/* v0.649 HOOLA WEB STUDIO - the website builder as its OWN full-screen app (owner-approved prototype, "PERFECT").

   Home (own sidebar): one line + a Build | Plan switch.
     Build = the site is made at once (POST /api/sites) and its plan is accepted (POST /plan) so the THREE LOOKS start.
     Plan  = Hoola's architect writes a plan from HER words (POST /api/site-architect): she reads it as a document,
             changes it in the chat (/revise), and only "Build this plan" (/approve, with the hash she saw) makes the site.
   v0.999.24 PROTOTYPE FIRST: either way she then gets a PROTOTYPE of every page and section (server: site/prototype.py),
   clickable in a computer / tablet / phone frame; she changes it in the chat, by clicking a section, or with Undo, and only
   "Build the real website" (POST /prototype/approve, with the hash she saw) builds. With studio_prototype off the server
   still makes THREE COMPLETE LOOKS (service._full_looks) and "Build in this look" builds (POST /look).
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
  // v0.987 HOOLA LOGO: the real Hoola mark (mark.js, the same drawing as the app and the console), not a gradient ring
  const hoolaMark = () => (window.HoolaMark ? HoolaMark.svg({mono: true}) : '<span></span>');
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
  window.HoolaQuality?.use(api);              // v0.999.29 credits + the quality tier under every typing box

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
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>', aim: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>', lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
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
    x: '<path d="M6 6l12 12M18 6L6 18"/>', panel: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M14 4v16"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'};
  const ico = (k, n = 18) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const tick = `<span class="tick" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M5 12l5 5 9-10"/></svg></span>`;
  const STATUS = {draft: ['Starting', ''], planned: ['Plan ready', 'v'], prototype: ['Prototype', 'warn'], looks: ['Pick a look', 'warn'], building: ['Building', 'v'],
    checking: ['Checking', 'v'], ready: ['Ready', 'ok'], failed: ['Needs attention', 'bad'], stopped: ['Paused', '']};
  const pill = (t, c) => `<span class="pill ${c || ''}">${esc(t)}</span>`;
  const PMAKING = v => S(v.status) === 'prototype' && S(M(v.prototype).status) === 'making';   // v0.999.24
  const statusPill = v => {
    if (PMAKING(v)) return pill('Making the prototype', 'v');
    if (S(v.status) === 'looks' && !L(v.looks).length) return pill('Making 3 looks', 'v');
    const [t, c] = STATUS[S(v.status)] || [S(v.status) || '…', ''];
    return pill(t + (Number(v.version) ? ` · v${v.version}` : ''), c);
  };
  const dotCls = v => ({ready: 'ok', looks: 'warn', prototype: 'warn', planned: 'v', building: 'v', checking: 'v', failed: 'bad'}[S(v.status)] || '');
  const name = v => S(v.name) || S(v.field_label) || 'Website';
  const hasVersion = v => !!Number(v.version);

  /* ================= v0.999.35 STUDIO WORKSPACE (the owner-approved design): while Hoola works the chat shows ONE
     working row (the Hoola mark, the real step, a clock - the Hoola chat's own row), the panel shows the animated mark
     with what has been planned so far under it, then the plan or the live pages; no Preview / Code tabs until there is
     something to look at; the panel is a Claude-style panel (one header row, close); the chat is resizable. ======== */
  const hmThink = px => (window.HoolaMark ? HoolaMark.think(px) : '<span class="spin" aria-hidden="true"></span>');
  const CW_KEY = 'hoola.ws.chatw', PANE_KEY = 'hoola.ws.paneshut';
  const chatW = () => { const n = Number(store.get(CW_KEY)); return n >= 320 && n <= 1200 ? n : 0; };
  const wspAttrs = (extra = '') => `class="wsp${extra}${store.get(PANE_KEY) === '1' ? ' pclosed' : ''}"${chatW() ? ` style="--wsc:${chatW()}px"` : ''}`;
  const SPLIT = '<div class="wsplit" role="separator" aria-orientation="vertical" aria-label="Chat width: drag, or use the arrow keys" title="Drag to resize · double-click to reset" tabindex="0"></div>';
  const paneX = () => `<button class="ib pclose" type="button" data-act="pane-close" aria-label="Close the panel" title="Close the panel">${ico('x', 16)}</button>`;
  const popen = () => `<button class="b popen" type="button" data-act="pane-open">${ico('panel', 15)}<span>Show panel</span></button>`;
  const TICKSVG = '<svg class="tk" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';
  let WROW_OPEN = false, PPICK = false;
  function swapText(el, txt) {
    if (!el || el.textContent === txt) return;
    const had = !!el.textContent; el.textContent = txt;
    if (had) { el.classList.remove('swap'); void el.offsetWidth; el.classList.add('swap'); }
  }
  function workRow(host, label, t0, stepsHtml, foot) {
    // the chat's working row, kept and updated in place so the mark keeps turning between polls
    if (!host) return;
    let row = host.querySelector(':scope > .wrow');
    if (!row) {
      host.innerHTML = `<div class="hck wrow"><div class="hck-work${WROW_OPEN ? ' open' : ''}"><span class="hck-mark">${hmThink(22)}</span><span class="hck-label"></span><span class="hck-secs"></span>`
        + `<button class="hck-tog" type="button" data-act="wrow" aria-expanded="${WROW_OPEN}" aria-label="Show the steps" title="Show the steps"><svg class="hck-dn" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>`
        + '<div class="hck-steps"></div></div><div class="wrow-foot"></div></div>';
      row = host.querySelector(':scope > .wrow');
    }
    swapText(row.querySelector('.hck-label'), S(label) + '…');
    const sc = row.querySelector('.hck-secs');
    if (t0) { sc.dataset.t0 = t0; sc.textContent = sc.textContent || '0s'; } else { delete sc.dataset.t0; sc.textContent = ''; }
    if (stepsHtml != null) {
      const stp = row.querySelector('.hck-steps');
      if (stp._h !== stepsHtml) { stp._h = stepsHtml; stp.innerHTML = stepsHtml; }
      row.querySelector('.hck-tog').hidden = !stepsHtml;
    }
    if (foot != null) { const ft = row.querySelector('.wrow-foot'); if (ft._h !== foot) { ft._h = foot; ft.innerHTML = foot; } }
    tickClocks();
  }
  function panelHead(title, sub, opts = {}) {
    if (opts.live) return `<div class="ptop phd wk lv"><span class="pttl ell">${esc(S(title))}</span>${opts.extra || ''}${paneX()}</div>`;
    return `<div class="ptop phd wk"><span class="pttl ell">${esc(S(title))}</span><span class="psub"><span class="psm"${opts.mark ? '' : ' hidden'}>${hmThink(16)}</span><span class="ell${opts.mark ? '' : ' shim'}">${esc(S(sub))}</span></span>${opts.extra || ''}<span class="sp"></span>${paneX()}</div>`;
  }
  function workPane(pane, o) {
    // the panel while Hoola works: the animated mark, the step + clock, each part as it is planned; then the live pages
    if (!pane) return;
    let x = pane.querySelector('#wsX');
    if (!x) {
      pane.innerHTML = panelHead('', '') + `<div class="wkstage"><div class="wsx" id="wsX" aria-live="polite"><span class="wsx-mark">${hmThink(84)}</span>`
        + '<div class="wsx-st"><span class="wsx-lbl"></span><span class="wsx-tm"></span></div><ol class="wsx-ups" aria-label="Planned so far"></ol><p class="wsx-foot"></p></div>'
        + '<div class="wsx-res" id="wsXres" hidden><div class="wstrip" role="group" aria-label="Pages"></div><div class="stage wkframe"></div></div></div>';
      x = pane.querySelector('#wsX');
    }
    const made = L(o.made), hd = pane.querySelector('.phd');
    hd.querySelector('.pttl').textContent = S(o.title);
    hd.querySelector('.psm').hidden = !made.length;
    const sub = hd.querySelector('.psub .ell'); sub.textContent = S(o.sub); sub.classList.toggle('shim', !made.length);
    swapText(x.querySelector('.wsx-lbl'), S(o.label) + '…');
    const tm = x.querySelector('.wsx-tm');
    if (o.t0) { tm.dataset.t0 = o.t0; } else { delete tm.dataset.t0; tm.textContent = ''; }
    const ol = x.querySelector('.wsx-ups'), ups = L(o.ups);
    if (ol.children.length > ups.length) ol.innerHTML = '';
    ups.forEach((u, i) => {
      const cls = u.done ? 'ok' : 'now', li = ol.children[i];
      if (!li) { ol.insertAdjacentHTML('beforeend', `<li class="${cls}">${u.done ? TICKSVG : '<span class="dot" aria-hidden="true"></span>'}<span class="ut">${esc(S(u.text))}</span></li>`); return; }
      if (li.className !== cls) { li.className = cls; li.firstElementChild.outerHTML = u.done ? TICKSVG : '<span class="dot" aria-hidden="true"></span>'; }
      const ut = li.querySelector('.ut'); if (ut.textContent !== S(u.text)) ut.textContent = S(u.text);
    });
    const ft = x.querySelector('.wsx-foot'); if (ft.textContent !== S(o.foot)) ft.textContent = S(o.foot);
    const res = pane.querySelector('#wsXres');
    x.hidden = !!made.length; res.hidden = !made.length;
    if (made.length) {
      const pick = PPICK && made.some(p => S(p.slug) === PPAGE) ? PPAGE : S(made[made.length - 1].slug);
      PPAGE = pick;
      const left = Math.max(0, Number(o.left) || 0);
      const strip = made.map(p => `<button type="button" data-ppage="${esc(S(p.slug))}" aria-pressed="${S(p.slug) === pick}">${TICKSVG}<span>${esc(S(p.title))}</span></button>`).join('')
        + (left ? `<span class="wpend"><span class="spin" aria-hidden="true"></span>${left} more page${left === 1 ? '' : 's'}</span>` : '');
      const st = res.querySelector('.wstrip'); if (st._h !== strip) { st._h = strip; st.innerHTML = strip; }
      const pg = made.find(p => S(p.slug) === pick), box = res.querySelector('.wkframe');
      if (pg && box._u !== S(pg.url) + DEVICE) { box._u = S(pg.url) + DEVICE; box.innerHTML = pg.url ? frame(S(pg.url), 'Prototype: ' + S(pg.title)) : ''; fit(); }
    }
    startTick();
  }
  const actUps = a => L(a.steps).filter(x => !x.final).map(x => ({text: S(x.label) + (x.note ? ` · ${S(x.note)}` : ''), done: x.state !== 'run'}));
  /* v0.667 PREMIUM STUDIO helpers: a site's status in a few words, how long ago, a time of day, the thumbnail tint */
  const statusText = v => S(v.status) === 'building' && Number(M(v.board).pct) ? `Building · ${Math.round(Number(M(v.board).pct))}%`
    : PMAKING(v) ? 'Making the prototype' : S(v.status) === 'looks' && !L(v.looks).length ? 'Making 3 looks' : (STATUS[S(v.status)] || [S(v.status) || 'Draft'])[0] + (S(v.status) === 'ready' && Number(v.version) ? ` · v${v.version}` : '');
  const isoS = x => { const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(S(x)) ? S(x) : S(x) + 'Z'); return isNaN(t) ? 0 : t / 1000; };
  const ago = x => { const t = isoS(x); if (!t) return ''; const d = Math.max(0, Date.now() / 1000 - t);
    return d < 60 ? 'just now' : d < 3600 ? `${Math.floor(d / 60)} min ago` : d < 86400 ? `${Math.floor(d / 3600)} h ago` : `${Math.floor(d / 86400)} d ago`; };
  const clockOf = t => t ? new Date(t * 1000).toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'}) : '';
  const tint = id => { let h = 0; for (const c of S(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return 'g' + (h % 4); };
  const MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || '');
  const WORKING = v => ['building', 'checking'].includes(S(v.status)) || (S(v.status) === 'looks' && !L(v.looks).length) || PMAKING(v) || !!v.mapping;
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
    if (!(p[0] === 'site' && p[1])) { stopStream(); dropKit(); }   // v0.777 the thread's live stream ends with the site (and its kit thread)
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
      <div class="brand"><div class="mark" aria-hidden="true">${hoolaMark()}</div><div><b>Hoola</b><span>Web Studio</span></div></div>
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
      <span class="meta"><span style="display:flex;align-items:center;gap:8px;min-width:0"><b>${esc(S(x.name) || 'New plan')}</b>${pill('Plan · your approval', 'v')}</span>
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
        ${SPECS.length ? `<div class="sec"><h2>Plans waiting for your approval</h2></div><div class="grid">${SPECS.map(specCard).join('')}</div>` : ''}
        ${SITES.length ? `<div class="grid" id="wsAll">${SITES.map(siteCard).join('')}</div><p class="mut" id="wsNone" hidden>No website matches.</p>` : '<div class="panel mut">No website yet. Write one line on the Studio home.</div>'}</section>`;
    } else if (page === 'starred') {
      const st = SITES.filter(v => isStar(v.id));
      main = `<section class="wrap"><div class="sec"><h2 style="font-size:24px">Starred</h2></div>
        ${st.length ? `<div class="grid">${st.map(siteCard).join('')}</div>` : `<div class="panel mut">Nothing starred yet. Open the ${ico('more', 14)} menu on any website and choose Add to starred.</div>`}</section>`;
    } else {
      main = `<div class="aura" aria-hidden="true"><i class="a1"></i><i class="a2"></i><i class="a3"></i><i class="a4"></i></div>
      <section class="hero"><span class="eyebrow"><b>New</b>Watch your website being built, live${ico('arrow', 14)}</span><h1 id="wsGreet">${esc(greetLine(''))}</h1>
        <p class="mut">Describe what you want to make in one line: for a business, for yourself, an event, a class, or just for fun. Hoola plans every page, shows it to you first, and builds it right in front of you. Nothing goes live until you tap.</p>
        <form class="ask" data-form="ask">
          <label for="wsAsk" class="sr">Describe your website</label>
          <textarea id="wsAsk" rows="3" maxlength="2000" placeholder="Ask Hoola to build a portfolio, a store, a wedding page, a game..." data-type-ph>${esc(PREFILL)}</textarea>
          <div class="bar">
            <button class="b ghost" type="button" data-src="old">${ico('globe', 15)}Use my old site</button>
            <button class="b ghost" type="button" data-src="shot">${ico('pic', 15)}From a screenshot</button>
            ${window.HoolaImprove ? `<button class="b ghost" type="button" data-improve title="See what Hoola understood and turn this into a complete website prompt">Improve</button>` : ''}
            <span class="sp"></span>
            <span class="mut sm mnote" id="wsModeNote">${mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: a prototype of every page first'}</span>
            <div class="seg" role="group" aria-label="Mode"><button type="button" data-mode="build" aria-pressed="${mode === 'build'}">Build</button><button type="button" data-mode="plan" aria-pressed="${mode === 'plan'}">Plan</button></div>
            <button class="go" type="submit" aria-label="Start">${ico('up', 18)}</button>
          </div>
        </form>
        <div class="hq-under" style="max-width:780px;margin:0 auto"><span data-hoola-quality></span></div>
        <div id="wsAskWork" class="step wrap" role="status" aria-live="polite" style="max-width:780px;margin-top:10px" hidden></div>
        <div id="wsSrc" class="wrap" style="max-width:780px"></div>
        <div class="chips" role="group" aria-label="What are you making?">${CHIPS.map(t => `<button class="chip" type="button" data-chip="${esc(t)}" aria-pressed="false">${esc(t)}</button>`).join('')}<a class="chip" href="#/templates">Ideas</a></div>
      </section>
      <section class="wrap" id="wsStarters" hidden><div class="sec"><h2 id="wsStartersH">Starting points</h2><span class="mut sm">Pick one, change any word, then send. Thumbnails show the look each one is built in.</span></div>
        <div class="sgrid" id="wsStartGrid"></div></section>
      ${SPECS.length ? `<section class="wrap"><div class="sec"><h2>Plans waiting for your approval</h2></div><div class="grid">${SPECS.slice(0, 4).map(specCard).join('')}</div></section>` : ''}
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
  const CHIPS = ['Website', 'Online store', 'Web app', 'Portfolio', 'Event', 'Community', 'Course', 'Tool or game'];
  const ENDS = ['a website for my clinic...', 'a portfolio for my photography...', 'a wedding website with RSVP...', 'an online store that takes UPI...',
    'a quiz game for my class...', 'an EMI calculator...', 'a page for our running club...', 'a dashboard to track my sales...', 'a course with lessons and quizzes...'];
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
  /* v0.986 PLAN PEEK: the start screen never sits on a grey skeleton. Her long message folds (Show all) so the work
     card is in view, she can write her next message while Hoola works (kept for the workspace), and the preview shows
     the plan as Hoola writes it: the name, every page and its sections, read from the model's own words. */
  const PEND_KEY = 'hoola.ws.pend.draft';
  function pendMe(text) {
    const long = S(text).length > 360 || S(text).split('\n').length > 7;
    return long ? `<div class="me clip" id="wsPendMe"><div class="mtx">${esc(text)}</div><button class="b ghost sm more" type="button" data-act="pend-more" aria-expanded="false">Show all</button></div>`
      : `<div class="me">${esc(text)}</div>`;
  }
  function pendScroll() {
    const m = $('#wsPendMsgs'), c = m && m.querySelector('.wrow');
    if (m && c) m.scrollTop = Math.max(0, c.offsetTop - m.offsetTop - 120);
  }
  function peekView(pk, plan) {
    const head = `<div class="pkh"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><b>${plan ? 'The plan is being written' : 'What Hoola is planning'}</b><span class="sp"></span>`;
    if (!pk || !(S(pk.name) || L(pk.pages).length)) {
      return `<article class="doc skel peek" aria-busy="true">${head}</div>
        <p class="mut sm">Hoola is reading your message and choosing the pages. Each page and its sections appear here the moment they are written, then the prototype of every page.</p>
        <div class="skl"><i class="sk w40"></i><i class="sk h"></i><i class="sk"></i><i class="sk w80"></i><i class="sk w60"></i><i class="sk h"></i><i class="sk w70"></i></div></article>`;
    }
    const pages = L(pk.pages), secs = pages.reduce((n, p) => n + L(p.sections).length, 0), done = !!pk.done;
    const kind = S(pk.kind).replace(/_/g, ' ');
    return `<article class="doc peek" aria-busy="${done ? 'false' : 'true'}" aria-label="The plan so far">
      ${head}<span class="cnt">${pages.length} page${pages.length === 1 ? '' : 's'} · ${secs} section${secs === 1 ? '' : 's'}${done ? '' : ' so far'}</span></div>
      ${S(pk.name) ? `<h2 class="pkn">${esc(S(pk.name))}</h2>` : ''}${kind ? `<span class="tag">${esc(kind)}</span>` : ''}
      ${S(pk.summary) ? `<p class="pks">${esc(S(pk.summary))}</p>` : ''}
      <ol class="pkp">${pages.map((p, i) => `<li class="${!done && i === pages.length - 1 ? 'now' : ''}"><div class="pt"><b>${esc(S(p.title))}</b>${S(p.for) ? `<span class="tag">${esc(S(p.for))}</span>` : ''}</div>
        ${S(p.purpose) ? `<p class="mut sm">${esc(S(p.purpose))}</p>` : ''}
        ${L(p.sections).length ? `<div class="pkc">${L(p.sections).map(x => `<span>${esc(S(x))}</span>`).join('')}</div>` : ''}</li>`).join('')}</ol>
      <p class="mut sm pkf">${done ? 'The plan is set. Next: a prototype of every page to check and change.' : 'Still writing…'}</p></article>`;
  }

  function peekUps(pk) {
    // what Hoola has planned so far, one line per page (the model's own words as they arrive)
    if (!pk) return [];
    const pages = L(pk.pages), done = !!pk.done, out = [];
    if (S(pk.summary)) out.push({text: S(pk.summary), done: true});
    pages.forEach((p, i) => out.push({text: S(p.title) + (L(p.sections).length ? `: ${L(p.sections).map(S).join(', ')}` : ''), done: done || i < pages.length - 1}));
    return out;
  }
  function drawPending(plan, text, ticket = '') {
    const steps = plan ? ['Reading your words', 'Choosing the pages, users and data', 'Writing the plan document']
      : ['Reading your idea', 'Planning the pages and what each one holds', 'Choosing colours and fonts, and setting up the website'];
    const t0 = nowS();
    APP.innerHTML = `<div ${wspAttrs(' wsp-in')} data-pending="${plan ? 'plan' : 'build'}">
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true">${hoolaMark()}</div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">${plan ? 'New plan' : 'New website'}</span>${pill(plan ? 'Writing the plan' : 'Starting', 'v')}<span class="sp"></span>
        ${popen()}<a class="b ghost" href="#/sites">All websites</a></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola">
          <div class="msgs" id="wsPendMsgs" aria-live="polite">${pendMe(text)}<div id="wsPendRow"></div></div>
          <form class="comp" data-form="pend" aria-describedby="wsPendNote"><label for="wsPendTa" class="sr">Write your next message</label>
            <textarea id="wsPendTa" rows="2" maxlength="4000" placeholder="Write your next message: it waits here and is ready to send when ${plan ? 'the plan' : 'the website'} opens…">${esc(store.get(PEND_KEY) || '')}</textarea>
            <div class="cbar"><span class="mut sm" id="wsPendNote">${plan ? 'Plan mode' : 'Build mode'} · Hoola is working on your first message</span><span class="sp"></span><button class="send" type="button" disabled aria-label="Send (opens when the workspace is ready)" title="Opens when the workspace is ready">${ico('up', 16)}</button></div></form>
        </section>
        ${SPLIT}
        <section class="pane" aria-label="${plan ? 'Plan' : 'Website'}" id="wsPeek"></section></div></div>`;
    document.title = `${plan ? 'New plan' : 'New website'} · Hoola Web Studio`;
    const stepsOl = `<ol class="acts" id="wsPendSteps">${steps.map((x, i) => `<li class="${i ? 'wait' : 'run'}" data-i="${i}">${i ? '<span class="tick off" aria-hidden="true"></span>' : '<span class="spin" aria-hidden="true"></span>'}<div class="sl"><span class="ell">${esc(x)}</span></div><span class="tm"${i ? '' : ` data-t0="${t0}"`}></span></li>`).join('')}</ol>`;
    const foot = `<span class="mut sm">${plan ? 'About a minute. Nothing is built until you say so.' : 'A big website takes a few minutes. You can write your next message meanwhile.'}</span>`;
    workRow($('#wsPendRow'), steps[0], t0, stepsOl, foot);
    const title = plan ? 'New plan' : 'New website', sub = plan ? 'Writing the plan' : 'Writing';
    const paneFoot = plan ? 'The plan document appears here. Nothing is built until you say so.' : 'Each page appears here as it is planned, then the prototype of every page.';
    workPane($('#wsPeek'), {title, sub, label: steps[0], t0, ups: [], foot: paneFoot});
    pendScroll();
    startTick();
    clearInterval(drawPending._t);
    drawPending._sig = drawPending._psig = '';
    if (ticket) {          // v0.835 L12: the steps are the server's own (what the call is really doing), never client-timed labels
      let seq = 0;
      drawPending._t = setInterval(async () => {
        const ol = $('#wsPendSteps'); if (!ol) return clearInterval(drawPending._t);
        let r; const me = ++seq;
        try { r = await api('GET', `/api/sites/stage/${enc(ticket)}`); } catch (e) { return; }
        if (me !== seq || !$('#wsPendSteps') || !L(r.steps).length) return;
        CLOCK = Number(r.now) - Date.now() / 1000;
        const sig = L(r.steps).map(x => [x.label, x.state, x.note].join('~')).join('|');
        if (sig !== drawPending._sig) {       // the running step keeps its live clock (data-t0) between polls
          drawPending._sig = sig;
          ol.innerHTML = L(r.steps).map(x => {
            const run = x.state === 'run', end = x.end || r.now;
            return `<li class="${run ? 'run' : x.state === 'error' ? 'bad' : 'ok'}">${run ? '<span class="spin" aria-hidden="true"></span>' : tick}<div class="sl"><span class="ell">${esc(S(x.label))}</span>${x.note ? `<span class="sn ell">${esc(S(x.note))}</span>` : ''}</div>${run ? `<span class="tm" data-t0="${Number(x.at)}"></span>` : `<span class="tm">${esc(dur(end - x.at))}</span>`}</li>`;
          }).join('');
          tickClocks();
        }
        const cur = L(r.steps).filter(x => x.state === 'run').pop() || L(r.steps).pop();
        const lbl = cur ? S(cur.label).replace(/[.…]+$/, '') : steps[0];
        workRow($('#wsPendRow'), lbl, t0, null, null);
        const psig = JSON.stringify(r.peek || null);
        if (psig !== drawPending._psig || lbl !== drawPending._lbl) {
          drawPending._psig = psig; drawPending._lbl = lbl;
          const pk = r.peek, pages = L(pk && pk.pages);
          workPane($('#wsPeek'), {title: S(pk && pk.name) || title, sub: pages.length ? `${pages.length} page${pages.length === 1 ? '' : 's'} so far` : sub,
            label: lbl, t0, ups: peekUps(pk), foot: pk && pk.done ? 'The plan is set. Next: the prototype of every page.' : paneFoot});
        }
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
      workRow($('#wsPendRow'), steps[k], t0, null, null);
      workPane($('#wsPeek'), {title, sub, label: steps[k], t0, ups: steps.slice(0, k).map(s => ({text: s, done: true})), foot: paneFoot});
      tickClocks();
    }, plan ? 14000 : 6000);
  }

  /* ================= v0.988 PROMPT FIRST: Hoola reads her words, then asks what it must know (the v0.784 choices page is gone) ===== */
  function askCard(v) {
    const qs = L(v.questions);
    return `<div class="chatact wcard qcard" id="wsAskQ" role="group" aria-labelledby="wsAskQh">
      <div class="step whead"><span class="wt"><b id="wsAskQh">A few questions first</b>${S(v.reading) ? `<span>${esc(S(v.reading))}</span>` : ''}</span></div>
      <p class="sm aqn">The answers change what gets built. Tap what fits, write your own, or skip and Hoola decides.</p>
      <form id="wsAskF">${qs.map((q, i) => `<fieldset class="aq"><legend>${esc(S(q.q))}</legend>
        ${L(q.options).length ? `<div class="aqo">${L(q.options).map((o, k) => `<label class="aqc"><input type="checkbox" name="o${i}" value="${esc(S(o))}" id="wsAq${i}-${k}"><span>${esc(S(o))}</span></label>`).join('')}</div>` : ''}
        <input class="in aqt" name="t${i}" maxlength="400" aria-label="Your own answer" placeholder="Or write your own answer"></fieldset>`).join('')}
        <div class="aqb"><button class="b ghost" type="button" data-aq="skip">Skip, Hoola decides</button><span class="sp"></span>
          <button class="b pri" type="submit">Answer and plan${ico('arrow', 16)}</button></div></form></div>`;
  }
  function askAnswers(v) {
    // resolves [{q, a}] (her answers), [] (skip: Hoola decides) - never sends anything by itself
    const f = $('#wsAskF');
    return new Promise(res => {
      f.addEventListener('submit', e => {
        e.preventDefault(); e.stopPropagation();
        const fd = new FormData(f);
        res(L(v.questions).map((q, i) => ({q: S(q.q), a: [...fd.getAll('o' + i), S(fd.get('t' + i)).trim()].filter(Boolean).join('; ')})).filter(x => x.a));
      });
      f.addEventListener('click', e => { const b = e.target.closest('[data-aq]'); if (!b) return; e.stopPropagation(); res([]); });
    });
  }
  async function askFirst(v, text) {
    // the pending screen turns into Hoola's questions: no plan, no preview until she answers (or skips)
    clearInterval(drawPending._t);
    const card = $('#wsPendRow'); if (card) card.outerHTML = askCard(v);
    const pk = $('#wsPeek');
    if (pk) pk.innerHTML = panelHead('New website', 'Waiting for your answers') + `<div class="stage"><article class="doc peek"><div class="pkh"><b>Nothing is planned yet</b></div>
      <p class="mut sm">Hoola read your message${S(v.kind) ? ` as a <b>${esc(S(v.kind).replace(/_/g, ' '))}</b>` : ''} and needs a few answers first. The plan, the design and the preview start from your words and your answers.</p></article></div>`;
    const pill_ = $('.wsp .top .pill'); if (pill_) pill_.textContent = 'Questions';
    pendScroll();
    $('#wsAskF input')?.focus();
    const qa = await askAnswers(v);
    const shown = text + (qa.length ? '\n\n' + qa.map(x => `${x.q} ${x.a}`).join('\n') : '');
    const ticket = 'st-' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
    drawPending(false, shown, ticket);
    return {qa, ticket};
  }

  async function startFromAsk(text, ticket = '') {
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
      let v = await api('POST', '/api/sites', body);
      if (L(v.questions).length && !v.id) {           // v0.988 PROMPT FIRST: Hoola asks before it plans
        const got = await askFirst(v, text);
        v = await api('POST', '/api/sites', {...body, ticket: got.ticket, qa: got.qa, asked: true});
      }
      store.set(convKey(v.id), conv);
      api('PATCH', `/api/conversations/${enc(conv)}`, {title: `Website · ${name(v)}`}).catch(() => {});
      if (S(v.status) === 'planned' && !v.mapping) {         // Build mode: no plan step - the prototype starts now (v0.999.24)
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
    APP.innerHTML = `<div ${wspAttrs()}>
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true">${hoolaMark()}</div></a>
        <span class="pname">${esc(S(CARD.name) || 'New website')}</span>${pill('Plan mode · nothing built yet', 'v')}<span class="sp"></span>
        ${popen()}<a class="b ghost" href="#/sites">All websites</a></header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this plan">
          <div class="msgs" id="wsPlanMsgs"><div id="wsPlanHist" class="hck-tight"></div></div>
          <div class="pbar"><div id="wsRevBar"></div><p class="mut sm">For example: teachers also mark attendance on the phone. Nothing is built until you say so.</p></div>
        </section>
        ${SPLIT}
        <section class="pane" aria-label="Plan">
          <div class="ptop phd"><span class="pttl ell">${esc(S(CARD.name) || 'Website')} plan</span><span class="psub"><span class="ell">Nothing is built until you say so</span></span><span class="sp"></span>${paneX()}</div>
          <div class="stage">${planDoc(CARD, words)}</div>
        </section>
      </div></div>`;
    document.title = `${S(CARD.name) || 'Plan'} · Hoola Web Studio`;
    planThread(id, words, log);
  }
  /* the plan chat on the chat kit (chatkit.js): her lines and Hoola's are the kit's, the one working row runs while
     the plan is rewritten, and Hoola's line lands when the new plan is back. The plan itself stays on the right. */
  let PLANKIT = null;
  const planAsks = qs => (L(qs).length ? `Before you build, tell me if you can:\n\n${L(qs).map(q => `- ${S(q).replace(/\s*\n\s*/g, ' ')}`).join('\n')}` : '');
  function planThread(id, words, log) {
    const root = $('#wsPlanHist'), host = $('#wsRevBar'); PLANKIT = null;
    if (!root || !host || !window.HoolaChat) return;
    const t = window.HoolaChat.mount(root, {scroller: $('#wsPlanMsgs')});
    const done = x => ({role: 'raw', html: `<div class="step">${tick}${esc(x)}</div>`});
    const list = [];
    if (words) list.push({role: 'her', text: words});
    list.push(done('Plan written from your words · on the right'));
    const first = [S(CARD.summary), planAsks(CARD.questions)].filter(Boolean).join('\n\n');
    if (first) list.push({role: 'hoola', text: first});
    for (const x of log) { list.push({role: 'her', text: S(x.me)}); if (x.say) list.push({role: 'hoola', text: S(x.say)}); else list.push(done(S(x.done))); }
    t.set(list.map((m, i) => ({id: 'p' + i, ...m})));
    const bar = window.HoolaChat.bar(host, {placeholder: 'Change anything in the plan…', quality: true, onSend: t => revisePlan(t)});   // short: it fits the box on one line
    bar.input.id = 'wsRev'; bar.input.maxLength = 2000;
    PLANKIT = {id, t, bar, words, busy: false};
  }
  async function revisePlan(t) {
    const K = PLANKIT; if (!K || K.busy || BUSY) { if (K && !K.bar.value) K.bar.value = t; return; }
    const pid = K.id, was = [S(CARD.summary), planAsks(CARD.questions)];
    K.busy = BUSY = true; K.bar.input.readOnly = true;       // one change at a time; there is no way to stop a rewrite
    K.t.her(t); K.t.begin('Updating the plan · about a minute');
    let card = null, err = null;
    try { card = await api('POST', `/api/site-architect/${enc(pid)}/revise`, {words: t}); } catch (er) { err = er; }
    BUSY = false;
    if (PLANKIT !== K || !K.t.el.isConnected) { K.t.clear(); return; }   // she left this plan meanwhile
    K.busy = false; K.bar.input.readOnly = false;
    if (err) {
      K.t.end(); K.t.raw({html: `<div class="li bad">${esc(err.message)} · your words are back in the box</div>`});
      if (!K.bar.value) K.bar.value = t;
      toast(err.message, true); return;
    }
    CARD = card;
    const now = [S(CARD.summary), planAsks(CARD.questions)];
    const say = ['The plan on the right has your change.', now[0] !== was[0] ? now[0] : '', now[1] !== was[1] ? now[1] : ''].filter(Boolean).join('\n\n');
    const key = 'hoola.ws.spec.log.' + pid;
    let log = []; try { log = JSON.parse(sessionStorage.getItem(key) || '[]'); } catch {}
    log.push({me: t, done: 'Plan updated', say}); try { sessionStorage.setItem(key, JSON.stringify(log.slice(-20))); } catch {}
    if (S(CARD.status) === 'built' && CARD.site) return openPlan(pid);
    const stage = APP.querySelector('.wsp .stage'), pn = APP.querySelector('.wsp .pname');
    if (stage) stage.innerHTML = planDoc(CARD, K.words);
    if (pn) pn.textContent = S(CARD.name) || 'New website';
    await K.t.final(say); K.t.end();
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
      <div class="dfoot"><span class="mut sm sp">Next: a prototype of every page and section to check and change. Nothing real is built until you approve it.</span>
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
    APP.innerHTML = `<div ${wspAttrs()}>
      <header class="top"><a href="#/" aria-label="Web Studio home" style="display:flex"><div class="mark" aria-hidden="true">${hoolaMark()}</div></a><span class="tsep" aria-hidden="true">/</span>
        <span class="pname">${esc(name(v))}</span>${v.draft_of ? pill('Draft · ' + S(v.draft_name), 'v') : ''}<button class="ib" type="button" data-menu="${esc(S(v.id))}" aria-label="Project options" title="Rename, star, delete">${ico('chev', 16)}</button>${v.name_by === 'hoola' ? `<button class="namedby" type="button" data-menu="${esc(S(v.id))}" title="Hoola picked this brand name. Tap to rename it.">✦ Named by Hoola</button>` : ''}<span id="wsPill">${statusPill(v)}</span><span class="sp"></span>
        <span class="tsave">Every change is saved as a version</span>
        ${popen()}<button class="b" type="button" data-view="history">${ico('hist', 15)}<span>History</span></button>
        ${v.draft_of ? `<a class="b" href="#/site/${enc(S(v.draft_of))}">Back to the website</a><button class="b dark" type="button" data-view="drafts"><span>Accept or discard</span></button>`
          : '<button class="b dark" type="button" data-view="publish"><span>Publish</span></button>'}</header>
      <div class="body">
        <section class="chat" aria-label="Chat with Hoola about this website">
          <div class="msgs" id="wsMsgs"></div>
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
              <span class="sp"></span><button class="send stopb" type="button" id="wsStop" data-act="stop-turn" aria-label="Stop" title="Stop after the step it is on" hidden>${ico('stop', 14)}</button>
              <button class="send" type="submit" aria-label="Send">${ico('up', 16)}</button></div></form>
          <div class="hq-under" style="padding:0 18px 8px"><span data-hoola-quality></span></div>
        </section>
        ${SPLIT}
        <section class="pane" id="wsPane" aria-label="Website"></section>
      </div></div>`;
    document.title = `${name(v)} · Hoola Web Studio`;
    const pd = S(store.get(PEND_KEY)).trim();       // v0.986 what she wrote while the website was starting: kept, never sent
    if (pd) { const ta = $('#wsTh'); if (ta && !S(ta.value).trim()) ta.value = pd; store.set(PEND_KEY, ''); }
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
    if (WORKING(v)) {                    // v0.999.35 the working row (the Hoola chat's own), the steps behind its arrow
      const cur = [...st].reverse().find(x => x.state === 'run');
      const title = PMAKING(v) ? 'Making the prototype' : S(v.status) === 'looks' ? 'Making three designs' : S(v.status) === 'checking' ? 'Checking every page'
        : hasVersion(v) ? 'Updating your website' : 'Building your website';
      const stepPct = cur && Number(cur.total) ? Math.round(100 * Number(cur.done || 0) / Number(cur.total)) : null;
      const label = cur ? S(cur.label) + (stepPct !== null ? ` · ${cur.done || 0} of ${cur.total}` : '') : title;
      const writingN = LIVE.site === S(v.id) ? Object.values(LIVE.slots).filter(writing).length : 0;
      const foot = `<span class="mut sm ell">${esc(title)} · ${writingN > 1 ? `${writingN} parts writing at once` : writingN === 1 ? '1 part writing now' : 'you can keep chatting; changes wait for this build'}</span>`
        + (['building', 'checking'].includes(S(v.status)) ? `<button class="b sm ghost" type="button" data-act="stop">${ico('pause', 14)}Pause</button>` : '');
      if (!box.querySelector(':scope > .wrow')) box.innerHTML = '';
      workRow(box, label, a.started ? Number(a.started) : 0, st.length ? stepList(a) : '', foot);
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
    if ($('#wsX') && CUR && VIEW === 'preview') drawPane();         // v0.999.35 the mark's updates move with the steps
    drawState();
  }

  const MORE_VIEWS = VIEWS.filter(([k]) => k !== 'preview' && k !== 'code');
  function viewsBar(extra = '', live = false) {
    const looks = S(CUR.status) === 'looks' && L(CUR.looks).length, proto = S(CUR.status) === 'prototype';
    if (!hasVersion(CUR) && (WORKING(CUR) || PMAKING(CUR))) return panelHead(name(CUR), PMAKING(CUR) ? 'Making the prototype' : 'Building', {mark: true, extra, live});
    const pv = proto ? 'Prototype' : looks ? '3 looks' : 'Preview';
    const seg = `<div class="pvseg" role="group" aria-label="View">${[['preview', pv, 'eye'], ['code', 'Code', 'code']].map(([k, n, ic]) => `<button type="button" data-view="${k}" aria-pressed="${VIEW === k}"${VIEW === k ? ' aria-current="page"' : ''} aria-label="${n}" title="${n}">${ico(ic, 15)}</button>`).join('')}</div>`;
    const mv = MORE_VIEWS.find(([k]) => k === VIEW);
    const ttl = VIEW === 'preview' ? pv + (proto && M(CUR.prototype).v ? ` · v${M(CUR.prototype).v}` : hasVersion(CUR) ? ` · v${CUR.version}` : '') : VIEW === 'code' ? 'Code' : mv ? mv[1] : '';
    const more = `<span class="vmw"><button class="b sm ghost vmore${mv ? ' on' : ''}" type="button" data-act="views-more" aria-haspopup="menu" aria-expanded="false">${esc(mv ? mv[1] : 'More')}${ico('chev', 13)}</button></span>`;
    return `<div class="ptop phd${live ? ' lv' : ''}">${seg}<span class="pttl ell">${esc(ttl)}</span>${extra}${extra.includes('class="sp"') ? '' : '<span class="sp"></span>'}${more}${paneX()}</div>`;
  }
  const devSeg = () => `<div class="seg" role="group" aria-label="Device">${Object.entries(DEV).map(([k, d]) => `<button type="button" data-dev="${k}" aria-pressed="${DEVICE === k}" aria-label="${d[2]}" title="${d[2]}">${ico(k === 'pc' ? 'pc' : k === 'tablet' ? 'tab' : 'phone', 16)}</button>`).join('')}</div>`;
  const frame = (src, title) => `<div class="frame ${DEVICE}" data-w="${DEV[DEVICE][0]}" data-h="${DEV[DEVICE][1]}"><iframe title="${esc(title)}" sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer" src="${esc(src)}"></iframe></div>`;

  /* ================= v0.999.70 D7 EDIT FOREVER: a React website changed by clicking it, at Rs 0 ================= */
  const RXE = {on: false, site: '', secs: null, pick: null, panel: '', design: null, busy: false};
  const rxFrame = () => APP.querySelector('.frame iframe');
  const rxSay = (m) => { const f = rxFrame(); try { f && f.contentWindow.postMessage(Object.assign({hoola: 'ae-cmd'}, m), '*'); } catch (e) { /* not ready */ } };
  async function rxLoad(force) {
    if (!CUR) return null;
    if (RXE.site !== CUR.id) { RXE.site = CUR.id; RXE.secs = null; RXE.pick = null; RXE.design = null; }
    if (!RXE.secs || force) { try { RXE.secs = await api('GET', `/api/sites/${enc(CUR.id)}/rx/sections`); } catch (e) { toast(e.message, true); RXE.secs = null; } }
    return RXE.secs;
  }
  const rxSec = sec => L(RXE.secs?.sections).find(x => S(x.sec) === S(sec));
  const NICE = {plain: 'Plain', surface: 'Soft', ink: 'Dark', primary: 'Brand colour'};
  function rxDraw() {
    const box = $('#wsRx'); if (!box) return;
    if (RXE.panel === 'design' && RXE.design) {
      const d = M(RXE.design.design), fs = L(RXE.design.fonts);
      const opt = (list, cur, lab) => list.map(x => `<option value="${esc(S(x.key ?? x))}"${S(x.key ?? x) === S(cur) ? ' selected' : ''}>${esc(lab ? lab(x) : S(x.label ?? x))}</option>`).join('');
      box.hidden = false;
      box.innerHTML = `<div class="rxh"><b>Design</b><span class="sp"></span><button class="ib" type="button" data-act="rx-close" aria-label="Close">×</button></div>
        <p class="mut sm">One change and every page follows. Every colour pair is checked before it is used. Free.</p>
        <label class="fld">Brand colour<input class="in" type="color" data-rxd="colour" value="${esc(S(d.primary) || '#4f46e5')}"></label>
        <label class="fld">Look<select class="in" data-rxd="direction">${opt(L(RXE.design.directions), d.seed_direction)}</select></label>
        <label class="fld">Light or dark<select class="in" data-rxd="mode">${opt(L(RXE.design.modes), d.mode)}</select></label>
        <label class="fld">Corners: <span data-rxr>${esc(S(d.radius))}</span> px<input type="range" min="0" max="32" step="1" data-rxd="radius" value="${esc(S(d.radius))}"></label>
        <label class="fld">Spacing<select class="in" data-rxd="density">${opt(L(RXE.design.densities), d.density)}</select></label>
        <label class="fld">Motion<select class="in" data-rxd="motion">${opt(L(RXE.design.motions), d.motion)}</select></label>
        <label class="fld">Headings font<select class="in" data-rxd="display">${opt(fs.filter(f => L(f.role).includes('display')).map(f => S(f.name)), M(d.fonts).display)}</select></label>
        <label class="fld">Text font<select class="in" data-rxd="text">${opt(fs.filter(f => L(f.role).includes('text')).map(f => S(f.name)), M(d.fonts).text)}</select></label>
        <p class="mut sm" data-rxmsg>${esc(S(d.checks) === 'every colour pair readable' ? 'Every colour pair is readable.' : S(d.checks))}</p>`;
      return;
    }
    const p = RXE.pick, sx = p ? rxSec(p.sec) : null;
    if (!RXE.on || !p || !sx) { box.hidden = !RXE.on; if (RXE.on) box.innerHTML = `<div class="rxh"><b>Edit on the page</b><span class="sp"></span><button class="ib" type="button" data-act="rx-edit" aria-label="Stop editing">×</button></div><p class="mut sm">Click any words or section in the preview. Words, layouts and backgrounds change at no cost; your phone, address and hours are in Settings.</p>`; return; }
    const canWords = S(sx.block) !== 'custom' && S(p.text);
    box.hidden = false;
    box.innerHTML = `<div class="rxh"><b>${esc(S(sx.page))} · section ${esc(S(sx.n))}</b><span class="mut sm">${esc(S(sx.block).replace(/_/g, ' '))}</span><span class="sp"></span><button class="ib" type="button" data-act="rx-close" aria-label="Close">×</button></div>
      ${canWords ? `<form data-form="rx-words"><label class="fld">Words<textarea class="in" name="new" rows="${Math.min(6, Math.max(2, Math.ceil(S(p.text).length / 38)))}" maxlength="600">${esc(S(p.text))}</textarea></label>
        <div class="inl"><span class="mut sm">Free</span><span class="sp"></span><button class="b sm pri" type="submit">Save words</button></div></form>`
        : `<p class="mut sm">${S(sx.block) === 'custom' ? 'This section was written specially for your site: ask in the chat to change its words.' : 'Click on words to change them.'}</p>`}
      ${L(sx.alts).length ? `<label class="fld">Layout<select class="in" data-rxs="variant"><option value="">${esc(S(sx.variant) || 'as it is')} (now)</option>${L(sx.alts).map(a => `<option value="${esc(a)}">${esc(a)}</option>`).join('')}</select></label>` : ''}
      ${L(sx.tones).length ? `<label class="fld">Background<select class="in" data-rxs="tone"><option value="">${esc(NICE[S(sx.tone) || 'plain'] || S(sx.tone))} (now)</option>${L(sx.tones).map(t => `<option value="${esc(t)}">${esc(NICE[t] || t)}</option>`).join('')}</select></label>` : ''}
      <div class="inl"><button class="b sm ghost bad" type="button" data-act="rx-drop">Leave this section out</button></div>`;
  }
  async function rxDo(path, body, after) {
    if (RXE.busy) return; RXE.busy = true;
    try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/rx/${path}`, body || {}); toast(S(r.say).slice(0, 160)); if (after) after(r); await rxLoad(true); rxDraw(); rxWatch(); }
    catch (er) { toast(er.message, true); }
    finally { RXE.busy = false; }
  }
  let RXT = 0;
  function rxWatch() {                                   // the debounced build lands -> the preview reloads by itself
    clearTimeout(RXT); const site = CUR?.id, v0 = Number(RXE.secs?.version) || 0; let n = 0;
    const tick = async () => {
      if (!CUR || CUR.id !== site || ++n > 40) return;
      try { const x = await api('GET', `/api/sites/${enc(site)}/rx/sections`); RXE.secs = x;
        if (Number(x.version) > v0 && !x.building) { const f = rxFrame(); if (f) f.src = f.src; toast('The new version is in the preview.'); return; } } catch { /* try again */ }
      RXT = setTimeout(tick, 3000);
    };
    RXT = setTimeout(tick, 3000);
  }

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
      const w = Number(f.dataset.w); let h = Number(f.dataset.h), k = Math.min(1, (f.clientWidth || w) / w);
      const st = f.parentElement?.classList.contains('stage') ? f.parentElement : null;   // v0.999.43 the frame fills the stage
      if (st) {
        const cs = getComputedStyle(st), aw = st.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
          ah = st.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
        if (f.classList.contains('pc')) { if (ah > 0) h = Math.max(h, Math.floor(ah / k)); }
        else if (aw > 0 && ah > 0) {                                     // tablet / phone: the whole device in view
          const bd = (f.offsetWidth - f.clientWidth) || 20;
          k = Math.min(1, (aw - bd) / w, (ah - bd) / h);
          f.style.width = Math.round(w * k + bd) + 'px';
        }
      }
      fr.style.width = w + 'px'; fr.style.height = h + 'px'; fr.style.transform = `scale(${k})`;
      f.style.height = Math.round(h * k) + (f.classList.contains('pc') ? 0 : (f.offsetHeight - f.clientHeight)) + 'px';
    });
    doit();
    if (window.ResizeObserver) { RO?.disconnect(); RO = new ResizeObserver(doit); fs.forEach(f => RO.observe(f.parentElement?.classList.contains('stage') ? f.parentElement : f)); }
  }

  function preview(pane, v) {
    const st = S(v.status), b = M(v.board);
    if (st === 'prototype') { delete pane.dataset.live; return protoView(pane, v); }   // v0.999.24 PROTOTYPE FIRST
    if (WORKING(v) && !EDIT && !v.mapping && st !== 'planned') return liveView(pane, v);
    if (pane.dataset.live && LIVE.from && st === 'ready' && Number(v.version) > LIVE.from) { LIVE.justDone = {site: S(v.id), from: LIVE.from, to: Number(v.version)}; LIVE.compare = false; }
    if (pane.dataset.live) LIVE.from = 0;
    delete pane.dataset.live;
    if (st === 'planned' && !v.mapping) {
      const pages = L(M(v.plan).pages);
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>The plan is ready</h2><p class="mut">${esc(S(v.say))}</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${pages.map(p => pill(S(p.title))).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b ghost bad" type="button" data-act="delete">Delete</button><button class="b pri" type="button" data-act="approve">Make the prototype</button></div></div></div>`;
      return;
    }
    if (st === 'looks' && L(v.looks).length) return looksView(pane, v);
    if (WORKING(v) && !hasVersion(v)) {          // v0.999.35 the animated mark + every step so far
      const t = v.mapping ? 'Planning every page of a big site' : st === 'looks' ? 'Making three complete looks' : st === 'checking' ? 'Checking every page' : 'Building your website';
      const note = st === 'looks' ? 'Every page of your site is written once, then shown in three different designs. You click through all of them before anything is built.'
        : 'Each page is written, put together and checked on a phone and a computer.';
      const a = ACTV(v), cur = [...L(a.steps)].reverse().find(x => x.state === 'run');
      workPane(pane, {title: name(v), sub: t, label: cur ? S(cur.label) : S(b.now) || t, t0: a.started ? Number(a.started) : 0, ups: actUps(a), foot: note});
      return;
    }
    const rx = M(v.react), isRx = !!S(rx.id);             // v0.999.65 D4: written as a React website from the kit
    const src = S(v.preview) + (EDIT && !isRx ? '__edit/' : '');
    const top = `<div class="url" title="A private preview: nobody else can see it until you publish.">${ico('lock', 14)}<span class="un">${esc(name(v))}</span><span class="ubadge${EDIT ? ' ed' : ''}">${EDIT ? 'Editing' : 'Draft · not live'}</span></div>${devSeg()}
      <button class="ib" type="button" data-act="reload" aria-label="Reload preview">${ico('reload', 16)}</button>
      ${v.preview ? `<a class="ib" href="${esc(S(v.preview))}" target="_blank" rel="noopener" aria-label="Open in a new tab">${ico('ext', 16)}</a>` : ''}`;
    const jd = LIVE.justDone && LIVE.justDone.site === S(v.id) ? LIVE.justDone : null;
    if (jd && LIVE.compare) return compareView(pane, v, jd, top);
    pane.innerHTML = viewsBar(top)
      + (jd ? `<div class="edbar okbar"><b>New version v${esc(S(jd.to))} is ready</b><span class="ell">You are looking at it now. Nothing is live until you publish.</span><span class="sp"></span>
          <button class="b sm" type="button" data-act="compare">Before / after</button><button class="ib" type="button" data-act="jd-close" aria-label="Close">×</button></div>` : '')

      + (st === 'failed' || st === 'stopped' ? `<div class="edbar"><b>${st === 'failed' ? 'The last build stopped on a problem' : 'Building is paused'}</b><span class="ell">${esc(S(v.error))}</span><span class="sp"></span><button class="b sm pri" type="button" data-act="resume">${st === 'failed' ? 'Try again' : 'Continue'}</button></div>` : '')
      + (WORKING(v) ? `<div class="edbar"><span class="spin" aria-hidden="true"></span><span class="ell">${esc(S(b.now) || 'Updating your website…')}</span></div>` : '')
      + (isRx ? `<div class="edbar okbar"><b>Written in React from your prototype</b><span class="ell">${L(rx.blanks).length ? 'Fill in before going live: ' + esc(L(rx.blanks).join(', ')) : 'Every section is a kit block with your words; ' + esc(S(rx.fixed || 0)) + ' small fixes made by code.'}</span><span class="sp"></span>
          <button class="b sm${RXE.on ? ' pri' : ''}" type="button" data-act="rx-edit" aria-pressed="${RXE.on ? 'true' : 'false'}">${RXE.on ? 'Done editing' : 'Edit on the page'}</button>
          <button class="b sm" type="button" data-act="rx-design">Design</button>
          <button class="b sm ghost" type="button" data-act="rx-undo">Undo</button>
          <a class="b sm ghost" href="#/app/${esc(S(rx.id))}">Open the code</a></div>` : '')
      + (isRx && M(rx.critic).say ? `<div class="edbar okbar" data-critic><b>Design review</b><span class="ell">${esc(S(M(rx.critic).say))}${L(M(rx.critic).problems).length && !M(rx.critic).passed ? ' · still: ' + esc(L(M(rx.critic).problems).slice(0, 2).join('; ')) : ''}</span></div>` : '')
      + '<div class="perrbar" id="wsPerr" role="alert" hidden></div>'
      + `<div class="stage">${v.preview ? frame(src, 'Website preview') : '<div class="empty">No preview yet.</div>'}${isRx ? '<aside id="wsRx" class="rxpanel" hidden></aside>' : ''}</div>`
      + (EDIT ? '<div id="wsYW"></div>' : '');
    if (isRx) rxDraw();
    fit();
    drawErrors();
    if (EDIT) ywDraw();                                  // v0.795 YEH WALA: the preview toolbar, style panel, draw layer
  }

  /* ================= v0.999.24 PROTOTYPE FIRST: every page and section before anything real is built ================= */
  let PPAGE = '', PSEL = null;
  function protoView(pane, v) {
    const p = M(v.prototype), st = S(p.status), pages = L(p.pages);
    if (st === 'failed' || (st !== 'making' && !pages.length)) {
      pane.innerHTML = viewsBar() + `<div class="stage"><div class="box"><h2>The prototype did not come</h2><p class="mut">${esc(S(p.error) || S(v.error) || 'Something stopped it.')}</p>
        <div class="inl" style="justify-content:flex-end"><button class="b pri" type="button" data-act="approve">Try again</button></div></div></div>`;
      return;
    }
    if (st === 'making') {                      // v0.999.35 the mark while the first page is written, then each page as it is made
      const a = ACTV(v), cur = [...L(a.steps)].reverse().find(x => x.state === 'run');
      const made = L(p.made), total = Number(p.total) || 0;
      workPane(pane, {title: name(v), sub: made.length ? `Making the prototype · ${made.length} of ${total || made.length} pages` : 'Making the prototype',
        label: cur ? S(cur.label) : 'Making the prototype', t0: a.started ? Number(a.started) : 0, ups: actUps(a), made, left: total - made.length,
        foot: 'Every page and every section, with real words and the design Hoola chose. Nothing real is built until you approve it.'});
      return;
    }
    if (!pages.some(x => S(x.slug) === PPAGE)) { PPAGE = S(pages[0].slug); PSEL = null; }
    const pg = pages.find(x => S(x.slug) === PPAGE);
    const pub = pages.filter(x => S(x.for) === 'public'), inner = pages.filter(x => S(x.for) !== 'public');
    const tab = x => `<button type="button" data-ppage="${esc(S(x.slug))}" aria-pressed="${S(x.slug) === PPAGE}"><span>${esc(S(x.title))}</span></button>`;
    const secs = pages.reduce((n, x) => n + L(x.sections).length, 0);
    pane.innerHTML = viewsBar(`<span class="sp"></span>${devSeg()}`)
      + `<div class="ptop pstrip"><div class="lks" role="group" aria-label="Pages">${pub.map(tab).join('')}${inner.length ? `<span class="mut sm pgrp">Signed in</span>${inner.map(tab).join('')}` : ''}</div></div>`
      + `<div class="stage">${pg.url ? frame(S(pg.url), 'Prototype: ' + S(pg.title)) : '<div class="empty">No preview yet.</div>'}</div>`
      + '<div id="wsProtoEdBox"></div>'
      + `<div class="choose"><span class="sm"><b>Prototype · version ${esc(S(p.v))}</b> <span class="mut">· ${pages.length} page${pages.length === 1 ? '' : 's'} · ${secs} sections · click a section to edit it, or ask for changes in the chat</span></span><span class="sp"></span>
          ${L(p.history).length > 1 ? '<button class="b" type="button" data-act="proto-undo">Undo</button>' : ''}
          <button class="b pri" type="button" data-act="proto-approve" data-hash="${esc(S(p.hash))}">Build the real website</button></div>`;
    fit();
    drawProtoEd();
  }
  function drawProtoEd() {
    const box = $('#wsProtoEdBox'); if (!box || !CUR) return;
    const p = M(CUR.prototype), pg = L(p.pages).find(x => S(x.slug) === PPAGE);
    const s = PSEL && pg && PSEL.page === PPAGE ? L(pg.sections)[PSEL.i] : null;
    if (!s) { box.innerHTML = ''; return; }
    box.innerHTML = `<form class="cardp protoed" data-form="proto-edit" data-page="${esc(S(pg.slug))}" data-i="${PSEL.i}" data-hash="${esc(S(p.hash))}" aria-label="Edit ${esc(S(s.label))}">
      <div class="inl"><b class="sp">${esc(S(s.label))}</b>
        <button class="b sm" type="button" data-act="proto-move" data-op="up" ${PSEL.i === 0 ? 'disabled' : ''}>Move up</button>
        <button class="b sm" type="button" data-act="proto-move" data-op="down" ${PSEL.i >= L(pg.sections).length - 1 ? 'disabled' : ''}>Move down</button>
        <button class="b sm ghost bad" type="button" data-act="proto-move" data-op="remove">Remove</button>
        <button class="ib" type="button" data-act="proto-close" aria-label="Close">×</button></div>
      <div class="pegrid"><label><span class="mut sm">Heading</span><input class="in" id="wsPeHeading" name="heading" maxlength="90" value="${esc(S(s.heading))}"></label>
        <label><span class="mut sm">Button</span><input class="in" id="wsPeCta" name="cta" maxlength="40" value="${esc(S(s.cta))}"></label></div>
      <label><span class="mut sm">Text</span><textarea class="in" id="wsPeLine" name="line" rows="2" maxlength="320">${esc(S(s.line))}</textarea></label>
      <label><span class="mut sm">Parts, one per line</span><textarea class="in" id="wsPeItems" name="items" rows="3">${esc(L(s.items).join('\n'))}</textarea></label>
      <div class="inl" style="justify-content:flex-end"><button class="b pri sm" type="submit">Save</button></div></form>`;
  }
  function protoFrame(m) { const f = APP.querySelector('.frame iframe'); if (f && f.contentWindow) f.contentWindow.postMessage({hoola: 'proto-cmd', ...m}, '*'); }
  addEventListener('message', ev => {
    const d = ev.data; if (!d || d.hoola !== 'proto' || !CUR || S(CUR.status) !== 'prototype') return;
    const f = APP.querySelector('.frame iframe'); if (!f || ev.source !== f.contentWindow) return;
    if (d.t === 'page' && S(d.page) && S(d.page) !== PPAGE) {
      PPAGE = S(d.page); PSEL = null;
      APP.querySelectorAll('[data-ppage]').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.ppage === PPAGE)));
      drawProtoEd();
    } else if (d.t === 'pick') { PPAGE = S(d.page) || PPAGE; PSEL = {page: PPAGE, i: Number(d.i) || 0}; drawProtoEd(); $('#wsPeHeading')?.focus(); }
  });
  async function protoAct(act, b) {
    const id = enc(CUR.id), p = M(CUR.prototype);
    if (act === 'proto-close') { PSEL = null; protoFrame({t: 'clear'}); drawProtoEd(); return; }
    if (act === 'proto-move') {
      const r = await api('POST', `/api/sites/${id}/prototype/move`, {page: PPAGE, index: PSEL ? PSEL.i : 0, op: b.dataset.op});
      if (PSEL && b.dataset.op === 'up') PSEL.i -= 1; else if (PSEL && b.dataset.op === 'down') PSEL.i += 1; else PSEL = null;
      CUR.prototype = r; drawPane(); toast(b.dataset.op === 'remove' ? 'Section removed.' : 'Moved.'); return;
    }
    if (act === 'proto-undo') { const r = await api('POST', `/api/sites/${id}/prototype/undo`, {}); CUR.prototype = r; PSEL = null; drawPane(); toast(`Back to the earlier version (now v${r.v}).`); return; }
    if (act === 'proto-approve') {
      b.disabled = true; b.innerHTML = '<span class="spin" aria-hidden="true"></span>Starting the build';
      try { await api('POST', `/api/sites/${id}/prototype/approve`, {hash: S(b.dataset.hash) || S(p.hash), conversation_id: await ensureConv().catch(() => '')}); }
      catch (er) { b.disabled = false; b.textContent = 'Build the real website'; throw er; }
      PSEL = null; toast('Building the real website from your prototype.'); await reload();
    }
  }
  async function protoSave(f) {
    const old = L(L(M(CUR.prototype).pages).find(x => S(x.slug) === S(f.dataset.page))?.sections)[Number(f.dataset.i)] || {};
    const fd = new FormData(f), id = enc(CUR.id);
    let base = S(f.dataset.hash), r = null;
    for (const k of ['heading', 'line', 'cta', 'items']) {
      const val = k === 'items' ? S(fd.get(k)).split('\n').map(x => x.trim()).filter(Boolean) : S(fd.get(k)).trim();
      const was = k === 'items' ? L(old.items) : S(old[k]);
      if (JSON.stringify(val) === JSON.stringify(was)) continue;
      r = await api('POST', `/api/sites/${id}/prototype/edit`, {page: f.dataset.page, index: Number(f.dataset.i), field: k, value: val, base});
      base = S(r.hash);
    }
    if (!r) return toast('Nothing changed.');
    CUR.prototype = r; drawPane(); toast(`Saved as version ${r.v}.`);
  }

  function looksView(pane, v) {
    const looks = L(v.looks);
    if (LOOK >= looks.length) LOOK = 0;
    const lk = M(looks[LOOK]);
    const est = M(v.estimate);
    pane.innerHTML = viewsBar(`<span class="sp"></span>${devSeg()}`)
      + `<div class="ptop"><div class="lks" role="group" aria-label="Look">${looks.map((x, i) => `<button type="button" data-look="${i}" aria-pressed="${i === LOOK}">
          <span class="sw" aria-hidden="true">${L(x.colors).map(HEX).filter(Boolean).slice(0, 4).map(c => `<i style="background:${c}"></i>`).join('')}</span><span>${i + 1} · ${esc(S(x.label))}</span></button>`).join('')}</div>
        <span class="sp"></span><span class="mut sm">${lk.own_bodies ? 'The whole site · every page in its own design' : lk.full ? 'The whole site · every page works' : 'The top of the home page (the whole site is made after you pick)'}</span></div>`
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
    // v0.999.41 ONE ROW: the live status, the page picker, device, Follow and Code all sit in the panel header
    const tools = `<span class="lstat" id="wsLBar" aria-live="polite"></span>`
      + (mode === 'site' ? `<span class="lpw"><button class="b sm ghost lpbtn" type="button" data-act="lpages" aria-haspopup="menu" aria-expanded="false" aria-controls="wsLPages"><span class="ell" id="wsLPageName">${esc(S(LIVE.page))}</span>${ico('chev', 13)}</button><div class="lpmenu" id="wsLPages" role="menu" aria-label="Pages being built" hidden></div></span>` : '')
      + `<span class="sp"></span>${mode === 'site' ? devSeg() : ''}
      <button class="b sm ghost ib" type="button" data-live="follow" aria-pressed="${LIVE.follow}" aria-label="Follow the part being written" title="Follow the part being written">${ico('aim', 16)}</button>
      <button class="b sm ghost ib" type="button" data-live="code" aria-pressed="${LIVE.code}" aria-label="Code" title="Show the code as it is written">${ico('code', 16)}</button>`;
    let stage;
    if (mode === 'looks') {
      const n = Math.max(3, LIVE.looks.length);
      stage = `<div class="lgrid">${Array.from({length: n}, (_, i) => `<div class="lcol"><div class="lhead"><b>Look ${i + 1}</b><span class="mut sm ell" data-lklabel="${i}">${esc(S(LIVE.looks[i]?.label))}</span><span class="sp"></span><span class="lstate" data-lkstate="${i}"></span></div>
        ${liveFrame(liveSrc(v, 'home', i), `Look ${i + 1} being made`, 'home', i, 'pc')}</div>`).join('')}</div>`;
    } else {
      stage = `<div class="stage lstage">${liveFrame(liveSrc(v, LIVE.page, -1), 'Your website being built', LIVE.page, -1)}</div>`;
    }
    pane.innerHTML = viewsBar(tools, true)
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
      const what = lead ? `${esc(lead.kind === 'fix' ? '' : lead.state === 'think' ? 'Designing ' : 'Writing ')}<b>${esc(S(lead.label))}</b>`
        : esc(S([...L(a.steps)].reverse().find(x => x.state === 'run')?.label) || S(b.now) || (S(CUR.status) === 'checking' ? 'Checking every page' : 'Working…'));
      const html = `<span class="livetag"><i aria-hidden="true"></i>LIVE</span><span class="lead ell">${what}${act.length > 1 ? ` <span class="mut lmore">· ${act.length} at once</span>` : ''}</span>`
        + `${Number(b.total) ? `<span class="lparts">${esc(S(b.done || 0))}/${esc(S(b.total))} parts</span>` : ''}${a.started ? `<span class="tm" data-t0="${Number(a.started)}"></span>` : ''}`;
      if (bar.dataset.h !== html) { bar.dataset.h = html; bar.innerHTML = html; tickClocks(); }
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
      const cur = pages.find(p => S(p.slug) === LIVE.page), nm = $('#wsLPageName');
      if (nm) nm.textContent = S(cur?.title) || S(LIVE.page);
      pg.innerHTML = pages.map(p => {
        const mine = all.filter(x => x.look < 0 && S(x.page) === S(p.slug)), w = mine.some(writing);
        const done = mine.length && !w && mine.every(x => x.state === 'done');
        return `<button type="button" role="menuitem" data-lpage="${esc(S(p.slug))}" aria-current="${S(p.slug) === LIVE.page ? 'page' : 'false'}">${w ? '<span class="dot v"></span>' : done ? tick : ''}<span class="ell">${esc(S(p.title) || S(p.slug))}</span></button>`;
      }).join('');
    }
    const tabs = $('#wsLTabs'), pre = $('#wsLCode');
    if (tabs && pre) {
      const list = all.filter(x => !looksMode || x.look >= 0).sort((x, y) => Number(x.at) - Number(y.at));
      const show = [...list.filter(writing), ...list.filter(x => !writing(x)).slice(-6)];
      if (!LIVE.codeKey || !LIVE.slots[LIVE.codeKey] || (!writing(LIVE.slots[LIVE.codeKey]) && act.length && !LIVE.codePinned)) LIVE.codeKey = S((act[0] || show[show.length - 1] || {}).key);
      tabs.innerHTML = show.map(x => `<button type="button" data-lcode="${esc(x.key)}" aria-current="${x.key === LIVE.codeKey ? 'page' : 'false'}">${writing(x) ? '<span class="dot v"></span>' : ''}<span class="ell">${esc(S(x.label))}</span></button>`).join('') || '<span class="mut sm">The code shows here as it is written.</span>';
      const sl = LIVE.slots[LIVE.codeKey];
      const txt = !sl ? '' : sl.state === 'think' && !sl.html ? '// Hoola is designing this section…' : (S(sl.html) + (sl.css ? '\n\n/* styles */\n' + S(sl.css) : ''));
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
      + `<div class="split"><nav class="subnav" aria-label="Files">${groups.map(g => `<div class="h">${esc(S(g.title))}</div>${L(g.files).map(f => { const [nm, ...ty] = S(f.label).split(' · '), t = ty.join(' · '); return `<button type="button" data-file="${esc(S(f.path))}" title="${esc(S(f.path))}"><span class="fty ${esc(t.toLowerCase().replace(/[^a-z]/g, ''))}">${esc(t || 'File')}</span><span class="ell">${esc(nm)}</span></button>`; }).join('')}`).join('') || '<div class="h">No files yet</div>'}</nav>
        <div class="code" id="wsCode"><div class="cempty"><span class="cico" aria-hidden="true">${ico('code', 22)}</span><b>Pick a file to read or change</b><span>Every save is checked for safety and becomes a new version. Undo brings the last one back.</span></div></div></div>`;
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
        <div class="inl">${studioBtn('Add lists and logins', 'Add logins and a list to this website: ', true)}</div>${a.error ? `<p class="mut sm">${esc(a.error)}</p>` : ''}</div></div>`;
      return;
    }
    pane.innerHTML = viewsBar() + `<div class="split"><nav class="subnav" aria-label="Lists"><div class="h">Data</div>${cols.map((c, i) => `<button type="button" data-coll="${esc(S(c.key))}" ${i ? '' : 'aria-current="page"'}>${esc(S(c.label))}${M(a.counts)[c.key] != null ? `<span class="sp"></span><span class="mut sm">${esc(S(M(a.counts)[c.key]))}</span>` : ''}</button>`).join('')}
        <div class="h">People</div><button type="button" data-coll="__members">Members and logins</button><button type="button" data-coll="__signin">Sign-in</button>
        <div class="h">Backend</div><button type="button" data-coll="__files">Files</button><button type="button" data-coll="__mail">Emails</button>
        <button type="button" data-coll="__log">Change log</button><button type="button" data-coll="__backups">Backups and restore</button>
        <button type="button" data-coll="__secrets">Secrets and outside services</button><button type="button" data-coll="__usage">Usage and limits</button>
        <div class="h">Safety</div><button type="button" data-coll="__rules">Rule tests</button></nav><div class="main" id="wsCloud"></div></div>`;
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
          ${rows.map(x => `<tr><td>${esc(S(x.name) || '—')}</td><td>${esc(S(x.phone || x.email || x.login))}</td><td><select class="in sm" data-role="${esc(S(x.id))}" aria-label="Role of ${esc(S(x.name) || 'member')}">
            ${['member', 'staff', 'admin'].map(o => `<option${S(x.role) === o ? ' selected' : ''}>${o}</option>`).join('')}</select></td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">Nobody has signed up yet.</p>'}
          <p class="note">Staff and admins see every entry the rules give staff; a member sees only what the list's rules allow.</p>`;
        box.querySelectorAll('[data-role]').forEach(sel => sel.addEventListener('change', async () => {
          if (!confirm(`Make this person ${sel.value}?`)) { openColl('__members'); return; }
          try { await api('POST', `/api/sites/${enc(CUR.id)}/app/members/${enc(sel.dataset.role)}/role`, {role: sel.value}); toast('Role changed.'); }
          catch (er) { toast(er.message, true); openColl('__members'); }
        }));
        return;
      }
      if (key === '__rules') {                       // v0.990 B3: the data rules played by a visitor, two members and an admin
        const draw = t => {
          const bad = L(t.failed), all = L(t.checks);
          box.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><h2 style="font-size:18px" class="sp">Rule tests</h2>
              ${pill(t.ok ? 'Passed' : bad.length + ' failed', t.ok ? 'ok' : 'bad')}<button class="b" type="button" id="wsRulesRun">Run again</button></div>
            <p>${esc(S(t.say))}</p><p class="mut sm">Played on a throwaway copy of your lists through the same server code every visitor uses; your entries and members are never touched. A failed rule stops the website going live until it is fixed.</p>
            ${all.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">List</th><th scope="col">Check</th><th scope="col">Should be</th><th scope="col">Was</th></tr></thead>
              <tbody>${[...bad, ...all.filter(c => c.ok)].slice(0, 300).map(c => `<tr><td>${esc(S(c.list))}</td><td>${esc(S(c.check))}${c.note ? `<div class="mut sm">${esc(S(c.note))}</div>` : ''}</td><td>${esc(S(c.want))}</td><td>${c.ok ? esc(S(c.got)) : pill(S(c.got), 'bad')}</td></tr>`).join('')}</tbody></table></div>` : ''}`;
          const btn = $('#wsRulesRun');
          if (btn) btn.addEventListener('click', async () => {
            btn.disabled = true; btn.textContent = 'Running…';
            try { draw(await api('POST', `/api/sites/${enc(CUR.id)}/rule-tests`)); } catch (er) { toast(er.message, true); btn.disabled = false; btn.textContent = 'Run again'; }
          });
        };
        draw(await api('GET', `/api/sites/${enc(CUR.id)}/rule-tests`));
        return;
      }
      if (key === '__log' || key === '__backups' || key === '__secrets' || key === '__usage') return backendPane(box, key);
      if (key === '__signin' || key === '__files' || key === '__mail') return accessPane(box, key);
      const r = await api('GET', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}`);
      const c = M(r.collection), fields = L(c.fields).slice(0, 8), rows = L(r.rows);
      const val = (row, k) => { const d = M(row.data || row); const x = d[k]; return x == null ? '' : typeof x === 'object' ? JSON.stringify(x) : S(x); };
      box.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><h2 style="font-size:18px" class="sp">${esc(S(c.label) || key)}</h2><span class="mut sm">${rows.length} rows</span>
          <button class="b pri" type="button" id="wsRowAdd">Add entry</button></div>
        ${rows.length ? `<div class="tbox"><table class="t"><thead><tr>${fields.map(f => `<th scope="col">${esc(S(f.label || f.key))}</th>`).join('')}<th scope="col"><span class="ws-sr">Actions</span></th></tr></thead>
          <tbody>${rows.slice(0, 200).map(row => `<tr>${fields.map(f => `<td>${esc(val(row, f.key))}</td>`).join('')}
            <td class="nw"><button class="b ghost sm" type="button" data-rowedit="${esc(S(row.id))}">Edit</button><button class="b ghost sm" type="button" data-rowdel="${esc(S(row.id))}">Delete</button></td></tr>`).join('')}</tbody></table></div>` : '<p class="mut">No rows yet.</p>'}
        <p class="note">Your entries go through the same checks, rules and logic as every visitor's, and each one is in the change log.</p>`;
      const form = row => L(c.fields).filter(f => !f.hidden && !f.computed && !['photo', 'photos', 'file', 'video', 'audio', 'signature', 'location', 'scan'].includes(S(f.type)))
        .map(f => { const v = row ? val(row, f.key) : ''; const n = esc(S(f.key));
          return `<label class="fld">${esc(S(f.label || f.key))}${f.type === 'choice' ? `<select class="in" name="${n}">${L(f.options).map(o => `<option${S(o) === v ? ' selected' : ''}>${esc(S(o))}</option>`).join('')}</select>`
            : f.type === 'long_text' || f.type === 'richtext' ? `<textarea class="in" name="${n}" rows="3">${esc(v)}</textarea>`
            : `<input class="in" name="${n}" value="${esc(v)}" type="${f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : f.type === 'email' ? 'email' : 'text'}">`}</label>`; }).join('');
      const body = fd => { const o = {}; fd.forEach((v, k) => { o[k] = v; }); return o; };
      $('#wsRowAdd')?.addEventListener('click', async () => {
        const f = await dialog(`Add to ${S(c.label) || key}`, form(null)); if (!f) return;
        try { await api('POST', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}`, body(f)); toast('Added.'); openColl(key); } catch (er) { toast(er.message, true); }
      });
      box.querySelectorAll('[data-rowedit]').forEach(b => b.addEventListener('click', async () => {
        const row = rows.find(x => S(x.id) === b.dataset.rowedit); const f = await dialog('Change this entry', form(row)); if (!f) return;
        try { await api('PATCH', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}/${enc(b.dataset.rowedit)}`, body(f)); toast('Saved.'); openColl(key); } catch (er) { toast(er.message, true); }
      }));
      box.querySelectorAll('[data-rowdel]').forEach(b => b.addEventListener('click', async () => {
        if (!confirm('Delete this entry? A backup can bring it back (Backups and restore).')) return;
        try { await api('DELETE', `/api/sites/${enc(CUR.id)}/app/rows/${enc(key)}/${enc(b.dataset.rowdel)}`); toast('Deleted.'); openColl(key); } catch (er) { toast(er.message, true); }
      }));
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }

  /* ---------- v0.991 B5 BACKEND: change log, backups + restore, secrets + outside services, usage + limits ---------- */
  async function backendPane(box, key) {
    let o;
    try { o = await api('GET', `/api/sites/${enc(CUR.id)}/backend`); } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const ref = enc(S(M(o.app).id)), when = t => S(t).replace('T', ' ').slice(0, 16);
    const pvSay = pv => `${Number(pv.come_back) || 0} entries come back, ${Number(pv.go_away) || 0} go away and ${Number(pv.change) || 0} change.`;
    const head = t => `<h2 style="font-size:18px">${esc(t)}</h2>`;
    if (key === '__log') {
      const r = await api('GET', `/api/sites/${enc(CUR.id)}/app/log?limit=200`), rows = L(r.log);
      box.innerHTML = head('Change log') + (rows.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">When</th><th scope="col">Who</th><th scope="col">What</th><th scope="col">List</th><th scope="col">Fields</th></tr></thead>
        <tbody>${rows.map(x => `<tr><td class="nw">${esc(when(x.at))}</td><td>${esc(S(x.by))}</td><td>${esc(S(x.op))}</td><td>${esc(S(x.list))}</td><td class="mut sm">${esc(L(x.fields).join(', '))}</td></tr>`).join('')}</tbody></table></div>`
        : '<p class="mut">No changes yet.</p>') + '<p class="note">Every write to your data is recorded here: by a visitor, your staff, you, or one of your rules.</p>';
      return;
    }
    if (key === '__backups') {
      const bk = L(o.backups);
      box.innerHTML = head('Backups and restore') + `<div class="inl"><button class="b pri" type="button" id="wsBkNow">Back up now</button><button class="b" type="button" id="wsBkZip">Download all data (ZIP)</button></div>
        <section class="cardp"><h3>Back to a moment</h3><p class="mut sm">Every change is in the journal, so your data can go back to any minute. See what would change first; nothing changes until you confirm.</p>
          <div class="inl"><input class="in" type="datetime-local" id="wsBkAt" aria-label="Moment (India time)"><button class="b" type="button" id="wsBkPrev">See what would change</button></div><div id="wsBkOut"></div></section>
        ${bk.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">When</th><th scope="col">Why</th><th scope="col">Entries</th><th scope="col"><span class="ws-sr">Actions</span></th></tr></thead>
          <tbody>${bk.map(x => `<tr><td class="nw">${esc(when(x.at))}</td><td>${esc(S(x.why || x.kind))}</td><td>${esc(S(x.rows))}</td><td><button class="b ghost sm" type="button" data-bkname="${esc(S(x.name))}">Restore…</button></td></tr>`).join('')}</tbody></table></div>`
          : '<p class="mut">No backups yet. One is taken every day and before every risky change.</p>'}`;
      const out = $('#wsBkOut');
      const restore = async (body, label) => {
        try {
          const pv = await api('POST', `/api/apps/${ref}/backups/preview`, body);
          if (!confirm(`${label}\n\n${pvSay(pv)}\n\nA safety backup of today's data is taken first. Restore now?`)) return;
          const r = await api('POST', `/api/apps/${ref}/backups/restore`, body); toast(S(r.say) || 'Restored.'); backendPane(box, key);
        } catch (er) { toast(er.message, true); }
      };
      $('#wsBkNow')?.addEventListener('click', async () => { try { await api('POST', `/api/apps/${ref}/backups/now`, {}); toast('Backed up.'); backendPane(box, key); } catch (er) { toast(er.message, true); } });
      $('#wsBkZip')?.addEventListener('click', async () => {
        try { const res = await api('GET', `/api/apps/${ref}/export`, undefined, {raw: true}); const blob = await res.blob();
          const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'website-data.zip'; document.body.appendChild(a); a.click(); a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 30000); toast('Downloaded your data.'); } catch (er) { toast(er.message, true); }
      });
      $('#wsBkPrev')?.addEventListener('click', async () => {
        const at = S($('#wsBkAt')?.value); if (!at) { toast('Pick a moment first.', true); return; }
        try { const pv = await api('POST', `/api/apps/${ref}/backups/preview`, {at});
          out.innerHTML = `<p>${esc(pvSay(pv))}</p><button class="b bad" type="button" id="wsBkGo">Restore to ${esc(at.replace('T', ' '))}…</button>`;
          $('#wsBkGo')?.addEventListener('click', () => restore({at}, `Restore your data to ${at.replace('T', ' ')} (India time)?`));
        } catch (er) { toast(er.message, true); }
      });
      box.querySelectorAll('[data-bkname]').forEach(b => b.addEventListener('click', () => restore({name: b.dataset.bkname}, 'Restore your data to this backup?')));
      return;
    }
    if (key === '__secrets') {
      const con = M(o.connect), sec = L(con.secrets), acts = L(con.actions), runs = L(con.runs);
      box.innerHTML = head('Secrets and outside services') + `<section class="cardp"><h3>Secrets</h3><p class="mut sm">Keys your outside services need. Type one here: it is sealed at once and never shown again, not even to you.</p>
          ${sec.length ? sec.map(n => `<div class="kv"><span><code>${esc(S(n))}</code></span><span class="inl"><span class="mut sm">set</span><button class="b ghost sm" type="button" data-secdel="${esc(S(n))}">Remove</button></span></div>`).join('') : '<p class="mut">No secrets yet.</p>'}
          <form class="inl" id="wsSecForm" autocomplete="off"><input class="in" name="name" placeholder="sheet_key" pattern="[a-z][a-z0-9_]{0,39}" required aria-label="Secret name (small letters, numbers, _)">
            <input class="in" name="value" type="password" placeholder="Paste the key" required autocomplete="new-password" aria-label="Secret value"><button class="b pri" type="submit">Save secret</button></form></section>
        <section class="cardp"><h3>Outside services</h3><p class="mut sm">Actions your data sends to other services. Each one runs only after your approval tap; a draft change waits for you again.</p>
          ${acts.length ? acts.map(a => `<div class="kv"><span><b>${esc(S(a.label || a.key))}</b> <span class="mut sm">${esc(S(a.coll))} · ${esc(S(a.trigger))}${a.leaves ? ' · sends ' + esc(L(a.leaves).join(', ')) : ''}</span></span>
            <span class="inl">${a.approved ? pill('Approved', 'ok') : `<button class="b sm" type="button" data-actok="${esc(S(a.key))}">Approve…</button>`}</span></div>`).join('') : '<p class="mut">None yet. Ask Hoola in the chat, for example "send new orders to my Google Sheet".</p>'}
          ${runs.length ? `<h3 style="margin-top:12px">Recent runs</h3>${runs.map(x => `<div class="kv"><span>${esc(S(x.action))} <span class="mut sm">${esc(when(x.at))}</span></span>${pill(S(x.status), S(x.status) === 'ok' ? 'ok' : S(x.status) === 'failed' ? 'bad' : '')}</div>`).join('')}` : ''}</section>`;
      $('#wsSecForm')?.addEventListener('submit', async ev => {
        ev.preventDefault(); const fd = new FormData(ev.target), n = S(fd.get('name')).trim().toLowerCase(), v = S(fd.get('value'));
        ev.target.reset();
        try { await api('PUT', `/api/apps/${ref}/connect/secrets/${enc(n)}`, {value: v}); toast(`Saved ${n}. It will not be shown again.`); backendPane(box, key); } catch (er) { toast(er.message, true); }
      });
      box.querySelectorAll('[data-secdel]').forEach(b => b.addEventListener('click', async () => {
        if (!confirm(`Remove the secret ${b.dataset.secdel}? Actions that use it stop working.`)) return;
        try { await api('DELETE', `/api/apps/${ref}/connect/secrets/${enc(b.dataset.secdel)}`); toast('Removed.'); backendPane(box, key); } catch (er) { toast(er.message, true); }
      }));
      box.querySelectorAll('[data-actok]').forEach(b => b.addEventListener('click', async () => {
        const a = acts.find(x => S(x.key) === b.dataset.actok);
        if (!confirm(`Approve "${S(a?.label || b.dataset.actok)}"? From now on it sends ${L(a?.leaves).join(', ') || 'data'} to an outside service when it runs.`)) return;
        try { await api('POST', `/api/apps/${ref}/connect/actions/${enc(b.dataset.actok)}/approve`, {her_tap: true}); toast('Approved.'); backendPane(box, key); } catch (er) { toast(er.message, true); }
      }));
      return;
    }
    const u = M(o.usage), lim = M(u.limits), used = {rows: u.rows, files_mb: u.files_mb, writes_day: u.writes_today};
    const row = (k, label, unit) => `<div class="kv"><span>${esc(label)}</span><span class="inl"><b>${esc(S(used[k] ?? '–'))}</b><span class="mut sm">of</span>
      <input class="in sm" type="number" min="0" name="${k}" value="${esc(S(lim[k] ?? ''))}" style="width:110px" aria-label="Limit for ${esc(label)}"><span class="mut sm">${esc(unit)}</span></span></div>`;
    box.innerHTML = head('Usage and limits') + `<form class="cardp" id="wsUseForm">${row('rows', 'Entries', 'entries')}${row('files_mb', 'Files', 'MB')}${row('writes_day', 'Writes today', 'a day')}
      <p class="mut sm">A limit can never be set below what is already used or above your plan's ceiling.</p><div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save limits</button></div></form>
      ${u.error ? `<p class="mut sm">${esc(S(u.error))}</p>` : ''}`;
    $('#wsUseForm')?.addEventListener('submit', async ev => {
      ev.preventDefault(); const fd = new FormData(ev.target), b = {}; fd.forEach((v, k) => { if (S(v) !== '') b[k] = Number(v); });
      try { const r = await api('PUT', `/api/apps/${ref}/usage`, b); toast(S(r?.say) || 'Limits saved.'); backendPane(box, key); } catch (er) { toast(er.message, true); }
    });
  }

  /* ---------- v0.995 B6 SIGN-IN, FILES, EMAIL: Google sign-in, the website's files, its sign-in + receipt emails ---------- */
  async function accessPane(box, key) {
    const head = t => `<h2 style="font-size:18px">${esc(t)}</h2>`, when = t => S(t).replace('T', ' ').slice(0, 16);
    const kb = n => { n = Number(n) || 0; return n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB'; };
    if (key === '__signin') {
      const g = await api('GET', `/api/sites/${enc(CUR.id)}/signin`);
      box.innerHTML = head('Sign-in') + `<section class="cardp"><h3>Email and password</h3><p class="mut sm">Always on. Mobile OTP and email codes show in the login box when their service is set up.</p></section>
        <form class="cardp" id="wsGForm"><div style="display:flex;align-items:center;gap:10px"><h3 class="sp">Sign in with Google</h3>${pill(g.ready ? 'On' : 'Off', g.ready ? 'ok' : '')}</div>
          <p class="mut sm">${esc(S(g.how))}</p>
          ${L(g.origins).length ? `<p class="mut sm">Authorized JavaScript origins to add:</p>${L(g.origins).map(o => `<div class="kv"><code>${esc(S(o))}</code></div>`).join('')}` : ''}
          <label class="fld">Web client ID<input class="in" name="client_id" value="${esc(S(g.client_id))}" placeholder="1234567890-abc123.apps.googleusercontent.com" autocomplete="off" spellcheck="false"></label>
          <label class="inl"><input type="checkbox" name="on" ${g.on ? 'checked' : ''}> Show "Sign in with Google" in the website's login box</label>
          <p class="mut sm">A new account made with Google still needs the privacy-notice tick. Someone who already has a password account with the same email stays one person.</p>
          <div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save</button></div></form>`;
      $('#wsGForm')?.addEventListener('submit', async ev => {
        ev.preventDefault(); const fd = new FormData(ev.target);
        try { const r = await api('PUT', `/api/sites/${enc(CUR.id)}/signin`, {client_id: S(fd.get('client_id')).trim(), on: fd.get('on') === 'on'}); toast(S(r.say) || 'Saved.'); accessPane(box, key); }
        catch (er) { toast(er.message, true); }
      });
      return;
    }
    if (key === '__files') {
      const f = await api('GET', `/api/sites/${enc(CUR.id)}/files`), rows = L(f.files), ref = enc(S(M(f.app).id));
      box.innerHTML = head('Files') + `<p class="mut sm">${esc(S(f.say))}</p><p class="mut sm">${rows.length} files, ${esc(kb(f.bytes))} in all.</p>
        ${rows.length ? `<div class="tbox"><table class="t"><thead><tr><th scope="col">File</th><th scope="col">Sent by</th><th scope="col">When</th><th scope="col">Who can open it</th><th scope="col">Used in</th><th scope="col"><span class="ws-sr">Actions</span></th></tr></thead>
          <tbody>${rows.map(x => `<tr><td>${esc(S(x.kind))} <span class="mut sm">${esc(kb(x.size))}</span></td><td>${esc(S(x.by))}</td><td class="nw">${esc(when(x.at))}</td>
            <td>${x.public ? pill('Anyone', 'warn') : pill('Private', 'ok')}</td><td class="mut sm">${L(x.used_in).length ? esc(L(x.used_in).map(u => S(u.list)).join(', ')) : 'not used'}</td>
            <td class="nw"><button class="b ghost sm" type="button" data-fopen="${esc(S(x.id))}">Open</button>${L(x.used_in).length ? '' : `<button class="b ghost sm" type="button" data-fdel="${esc(S(x.id))}">Delete…</button>`}</td></tr>`).join('')}</tbody></table></div>`
          : '<p class="mut">No files yet. Photos, documents and videos sent through your website\'s forms show here.</p>'}`;
      box.querySelectorAll('[data-fopen]').forEach(b => b.addEventListener('click', async () => {
        try { const res = await api('GET', `/api/apps/${ref}/files/${enc(b.dataset.fopen)}`, undefined, {raw: true}); const url = URL.createObjectURL(await res.blob());
          window.open(url, '_blank', 'noopener'); setTimeout(() => URL.revokeObjectURL(url), 60000); } catch (er) { toast(er.message, true); }
      }));
      box.querySelectorAll('[data-fdel]').forEach(b => b.addEventListener('click', async () => {
        if (!confirm('Delete this file for good? No entry uses it, and it cannot be brought back.')) return;
        try { await api('DELETE', `/api/sites/${enc(CUR.id)}/files/${enc(b.dataset.fdel)}`); toast('Deleted.'); accessPane(box, key); } catch (er) { toast(er.message, true); }
      }));
      return;
    }
    const m = await api('GET', `/api/sites/${enc(CUR.id)}/mail`), lists = L(m.lists), rec = L(m.receipts), log = L(m.log);
    box.innerHTML = head('Emails') + (m.ready ? `<p class="mut sm">Sent from <code>${esc(S(m.from))}</code> through your mail service. ${esc(S(m.sent_today))} sent today${m.daily_cap ? ` of ${esc(S(m.daily_cap))} a day` : ''}.</p>`
        : '<section class="cardp"><p><b>No mail service is set up yet.</b></p><p class="mut sm">Emails go through your own transactional mail service (ZeptoMail, Amazon SES or Brevo give an SMTP login). Its login is added on the server (SITE_MAIL_* in the server settings), never typed in chat. Until then nothing is sent and the login box does not offer email codes.</p></section>') +
      `<form class="cardp" id="wsMailForm"><h3>Sign-in emails</h3>
        <label class="inl"><input type="checkbox" name="codes" ${m.codes ? 'checked' : ''}> "Email me a code" and "Forgot password?" in the login box</label>
        <p class="mut sm">A code works for 10 minutes and only once; the email never says whether an account exists. A new password signs that person out everywhere.</p>
        <h3 style="margin-top:12px">Receipts</h3><p class="mut sm">After a signed-in visitor adds an entry, one short email says it arrived. It repeats nothing they typed.</p>
        ${lists.length ? lists.map(c => `<label class="inl"><input type="checkbox" name="rc" value="${esc(S(c.key))}" ${rec.includes(S(c.key)) ? 'checked' : ''}> ${esc(S(c.label))}</label>`).join('') : '<p class="mut">No lists yet.</p>'}
        <label class="fld">Replies go to<input class="in" name="reply_to" type="email" value="${esc(S(m.reply_to))}" placeholder="you@example.in"></label>
        <div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save</button></div></form>
      ${log.length ? `<h3>Sent lately</h3><div class="tbox"><table class="t"><thead><tr><th scope="col">When</th><th scope="col">What</th><th scope="col">To</th><th scope="col">Result</th></tr></thead>
        <tbody>${log.map(x => `<tr><td class="nw">${esc(when(x.at))}</td><td>${esc(S(x.kind).replace('_', ' '))}</td><td>${esc(S(x.to))}</td><td>${x.ok ? pill('Sent', 'ok') : pill(S(x.why) || 'Not sent', 'bad')}</td></tr>`).join('')}</tbody></table></div>` : ''}`;
    $('#wsMailForm')?.addEventListener('submit', async ev => {
      ev.preventDefault(); const fd = new FormData(ev.target);
      try { await api('PUT', `/api/sites/${enc(CUR.id)}/mail`, {codes: fd.get('codes') === 'on', receipts: fd.getAll('rc').map(String), reply_to: S(fd.get('reply_to')).trim()}); toast('Saved.'); accessPane(box, key); }
      catch (er) { toast(er.message, true); }
    });
  }

  function integrations(pane, v) {
    const langs = L(v.languages), items = [['cart', 'Shop and cart', 'Prices and stock checked by the server, COD, pickup, coupons, GST invoices.', 'Turn on a shop on this website'],
      ['card', 'Online payments', 'UPI QR to your UPI ID, or your own Razorpay / Cashfree / PhonePe. Paid only when the gateway confirms.', 'Add online payments to this website'],
      ['cal', 'Booking slots', 'Real time slots with limits; you confirm each booking.', 'Add booking slots to this website'],
      ['blog', 'Blog', 'Hoola drafts posts, you approve them to publish. RSS and scheduling.', 'Turn on a blog on this website'],
      ['globe', 'Languages', `Now: ${langs.join(', ') || 'en'}. Up to 4 more Indian languages with a switch in the menu.`, 'Add a Hindi version of this website too'],
      ['chat', 'Visitor chat', 'Visitors message your team from the site; your reply goes only on your tap.', 'Turn on visitor chat on this website'],
      ['pin', 'Map and directions', 'Loads only when the visitor taps, so the page stays fast.', 'Put a map on this website\'s contact page'],
      ['spark', 'Rich pieces', 'Quiz, configurator, comparison table, animation, 3D hero.', 'Add a quiz to this website: '],
      ['link', 'Your other apps', 'New orders to Google Sheets, HubSpot or Slack through your own account.', 'Send this website\'s new orders to my Google Sheet']];
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
    /* O1: the details follow what the site is for - a business keeps "Business details", anything else speaks plainly. */
    const purpose = S(M(M(v.plan).spec).purpose), biz = !purpose || purpose === 'business';
    const fields = [['name', biz ? 'Business name' : 'Site name'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'],
      ['hours', biz ? 'Opening hours' : 'Times (if any)'], ['address', biz ? 'Address' : 'Place (if any)'], ['city', 'City'], ['instagram', 'Instagram']];
    pane.innerHTML = viewsBar() + `<div class="main" style="max-width:900px">
      <form class="cardp" data-form="facts"><h3>${biz ? 'Business details' : 'Site details'}</h3><p class="mut sm">Used on every page. A change here is used in the next version; ask in the chat to rebuild now.</p>
        <div class="g2">${fields.map(([k, l]) => `<label class="fld">${esc(l)}<input class="in" name="${k}" value="${esc(S(f[k]))}" autocomplete="off"></label>`).join('')}</div>
        <div class="inl" style="justify-content:flex-end"><button class="b pri" type="submit">Save details</button></div></form>
      <form class="cardp" data-form="instr"><h3>Instructions for Hoola</h3><p class="mut sm">Your standing brief for this website: who it is for, tone, colours, words to use or avoid, what must never change. Hoola reads it on every message about this site, in every mode.</p>
        <textarea id="wsInstr" class="in" rows="7" maxlength="10000" placeholder="Example: For families in Nagpur. Warm and simple English. Never change the phone number or the Book now button."></textarea>
        <div class="inl"><span class="mut sm" id="wsInstrN">0 / 10,000</span><span class="sp"></span><button class="b pri" type="submit">Save instructions</button></div></form>
      <section class="cardp" data-likes><h3>Sites you like</h3><p class="mut sm">Give Hoola up to 8 websites whose look you like. They are used as a pattern - the feel, the colours - when your React website is written and reviewed. Nothing is copied from them: no words, pictures or code.</p>
        <div id="wsLikes"><p class="mut sm">Loading…</p></div>
        <form class="inl" data-form="like-add" style="margin-top:10px"><input class="in" name="url" maxlength="400" placeholder="https://a-site-you-like.com" aria-label="Website address" required><input class="in" name="note" maxlength="300" placeholder="What you like about it (optional)" aria-label="What you like about it"><button class="b" type="submit">Add</button></form></section>
      <section class="cardp"><h3>SEO and Google</h3><p class="mut">Page titles, descriptions, sitemap and Search Console are set by Hoola on every build.</p><div class="inl">${studioBtn('Check SEO now', 'Check this website\'s SEO', false)}</div></section>
      <section class="cardp"><h3>Team</h3><p class="mut">Writers draft, editors review, publishers put live.</p><div class="inl">${studioBtn('Invite a team member', 'Add a team member to this website\'s CMS: ', false)}</div></section>
      <section class="cardp danger"><h3>Take the site down</h3><p class="mut">The site stops answering; your pages, data and versions are kept.</p><div class="inl"><button class="b bad" type="button" data-act="takedown">Take down…</button></div></section></div>`;
    loadInstr();
    loadLikes();
  }
  /* v0.999.69 D6: the sites she likes (patterns for the writer and the critic, never copied) */
  async function loadLikes() {
    const box = $('#wsLikes'); if (!box) return;
    let r; try { r = await api('GET', '/api/appengine-refs'); } catch (e) { box.innerHTML = `<p class="mut sm">${esc(e.message)}</p>`; return; }
    if (!box.isConnected) return;
    const ls = L(r.links);
    box.innerHTML = ls.length ? ls.map(x => `<div class="kv" data-like="${esc(S(x.id))}"><span class="ell"><b>${esc(S(x.host))}</b>${S(x.note) ? ` <span class="mut sm">· ${esc(S(x.note))}</span>` : ''}</span>
        <span class="sp"></span>${L(x.colours).slice(0, 5).map(c => `<span title="${esc(c)}" style="display:inline-block;width:14px;height:14px;border-radius:4px;border:1px solid rgba(0,0,0,.15);background:${esc(c)}"></span>`).join('')}
        <button class="b sm ghost" type="button" data-act="like-del" data-like-id="${esc(S(x.id))}">Remove</button></div>`).join('')
      : '<p class="mut sm">No sites yet.</p>';
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
        <div class="inl">${studioBtn('Find a domain to buy', 'Find a good domain for this website', false)}</div></section>
      ${moves ? `<section class="cardp"><div style="display:flex;align-items:center;gap:8px"><h3 class="sp">Old site addresses</h3>${pill(moves.approved ? 'Approved' : `${rows.length} found`, moves.approved ? 'ok' : 'warn')}</div>
        <p class="mut sm">Links and Google results from your old site (${esc(S(moves.from_host))}) open the matching new page (301). Untick any you don't want.</p>
        <form data-form="moves" data-hash="${esc(S(moves.hash))}">${rows.slice(0, 200).map(r => `<label class="mv"><input type="checkbox" name="keep" value="${esc(S(r.old))}" ${r.guess ? '' : 'checked'}><code>${esc(S(r.old))}</code><span aria-hidden="true">→</span><code>${esc(S(r.new))}</code>${pill(S(r.how), r.guess ? 'warn' : '')}</label>`).join('') || '<p class="mut">Every old address already exists on the new site.</p>'}
          ${rows.length ? `<div class="inl" style="justify-content:flex-end;margin-top:8px"><button class="b pri" type="submit">Yes, connect it</button></div>` : ''}</form></section>` : ''}
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
        <div class="inl" style="justify-content:flex-end">${st === 'planned' && todo.length ? `<button class="b pri" type="button" data-act="dns-apply" data-plan="${esc(S(p.id))}" data-hash="${esc(S(p.hash))}">Yes, add them for me</button>` : ''}
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
          <div class="inl" style="justify-content:flex-end"><button class="b pri" type="button" data-act="golive" data-hash="${esc(S(card.hash))}">Yes, go live</button></div>`}</div>`;
    } catch (e) { out.innerHTML = `<p class="li bad">${esc(e.message)}</p>`; }
  }

  /* ---------- polling while the server works ---------- */
  function sig(v) { return [v.status, v.version, M(v.board).pct, M(v.board).now, L(v.looks).length, L(v.looks).map(x => x.full).join(), v.error, M(v.prototype).v, M(v.prototype).status, L(M(v.prototype).made).length].join('|'); }
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
    THREAD.conv = c; THREAD.loaded = true;
    startStream(c);
    return c;
  }
  async function openThread() {
    clearTimeout(THREAD.timer); stopStream();
    Object.assign(THREAD, {site: CUR.id, conv: store.get(convKey(CUR.id)), rows: [], live: '', raw: '', rawSeg: null, seq: 0, sig: '', waiting: false,
      since: 0, steps: [], stepMap: new Map(), stepsRead: false, startedS: 0, turn: '', costs: [], think: null, loaded: false, stopping: false, sendNow: false,
      queue: [], files: [], pinned: true, thoughts: new Map(), turnOf: new Map(), editing: '', kl: {gen: (THREAD.kl?.gen || 0) + 1, n: 0, items: [], day: ''}});
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
  /* ----- HOOLA CHAT KIT: the thread is drawn by chatkit.js (window.HoolaChat) -----
     Her bubbles, Hoola's replies (Literata 16 / 1.5, words landing at the shared pace), the ONE working row and the
     action row are the kit's. This file only tells the kit what is in the thread (kitDraw) and hangs the Studio's own
     things on the kit's blocks (adorn): Thought for · steps · Rs + Details, the plan card, the Start building card,
     Version N / Undo this change, Edit and resend. The Studio keeps its own scroll rule (her new message goes to the
     top of the view, the stream never pulls her down, Latest), so the kit is given a scroller of its own to move. */
  const SB_MARK = '[[start-building:';
  const isLocal = r => S(r && r.id).startsWith('local-');
  const planFix = t => S(t).replace(/^(#{1,6} [^\n]*)\n(?!\n)/gm, '$1\n\n');   // a plan's list right under its heading still renders as a list
  /* the words a reply shows: the start-building marker never shows, not even half-written while it streams. Nothing
     before the marker is trimmed, so a longer text always starts with the shorter one (the landing never restarts). */
  function replyWords(t) {
    t = S(t); const i = t.lastIndexOf(SB_MARK);
    if (i >= 0 && !/\]\]\s*\S/.test(t.slice(i))) return t.slice(0, i);
    for (let k = Math.min(t.length, SB_MARK.length - 1); k > 0; k--) if (t.endsWith(SB_MARK.slice(0, k))) return t.slice(0, t.length - k);
    return t;
  }
  const lastUser = () => [...THREAD.rows].reverse().find(r => r.role === 'user');
  const liveText = () => { const w = replyWords(THREAD.raw); return modeOfRow(lastUser()) === 'plan' ? planFix(w) : w; };
  function endLive() { THREAD.raw = ''; THREAD.rawSeg = null; THREAD.live = ''; THREAD.turn = ''; }
  let KIT = null;
  const KD = {running: false, again: false};
  const KOPT = {acts: ['copy', 'aloud', 'up', 'down'], scroller: document.createElement('div'), startedAt: 0,
    onAct: (kind, text, value, msg) => threadAct(kind, value, msg), onEnd: () => kitEnded()};
  function kitOf() {
    const root = $('#wsHist'); if (!root || !window.HoolaChat) return null;
    if (!KIT || KIT.root !== root) {
      dropKit();
      KIT = {root, t: window.HoolaChat.mount(root, KOPT), key: null, ids: [], locals: new Set(), sent: new Map(), gone: new Set(), ending: false, liveOn: false, liveText: ''};
      if (window.ResizeObserver) { KIT.ro = new ResizeObserver(() => keepPinned()); KIT.ro.observe(root); }
    }
    return KIT;
  }
  function dropKit() { if (KIT) { KIT.ro?.disconnect(); try { KIT.t.clear(); } catch { /* already gone */ } KIT = null; } }   // its clock stops with it
  function kitEnded() { if (!KIT) return; KIT.ending = false; KIT.liveOn = false; KIT.liveText = ''; kitDraw(); }
  /* the thread as the kit sees it. Rows come with two kinds of id (the stream's event id, then the message's own id
     when the list is read again), so each row keeps ONE id of ours for as long as the thread is open: a list read
     again is lined up with what is drawn by its words, and only what is new is added (and lands). */
  function threadItems() {
    const kl = THREAD.kl || (THREAD.kl = {gen: 1, n: 0, items: [], day: ''});
    const all = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
    const first = all.findIndex(r => r.role === 'user');
    const rows = first < 0 ? [] : all.slice(first);
    const B = rows.filter(r => !isLocal(r)).map(r => ({role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? clean(r.text).trim() : S(r.text).trim(), row: r}));
    const A = kl.items, make = b => ({...b, kid: 'k' + (++kl.n), turn: S(b.row.turn)});
    if (!A.length) kl.items = B.slice(-40).map(make);
    else {
      let best = null;                                       // B[j] is A[j + s]: the longest run that agrees wins
      for (let s = A.length - 1; s > -B.length; s--) {
        const j0 = Math.max(0, -s), j1 = Math.min(B.length, A.length - s); let ok = j1 > j0;
        for (let j = j0; j < j1 && ok; j++) ok = A[j + s].role === B[j].role && A[j + s].text === B[j].text;
        if (ok && (!best || j1 - j0 > best.n)) best = {s, n: j1 - j0};
      }
      if (!best) { kl.gen++; kl.day = ''; kl.items = B.slice(-40).map(make); }       // another story: drawn again, whole
      else {
        for (let j = Math.max(0, -best.s); j < B.length; j++) {
          const a = A[j + best.s];
          if (a) { a.row = B[j].row; a.turn = a.turn || S(B[j].row.turn); } else A.push(make(B[j]));
        }
      }
    }
    return {kl, items: kl.items, locals: rows.filter(isLocal)};
  }
  /* each reply's turn: [her message, its reply, start, end, steps, the next turn's start]. A line of hers that is
     still on its way to the server counts too (a reply can come back before her own line does). */
  function turnsOf(items) {
    const by = new Map(), seq = []; let cur = null;
    const talk = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
    const inList = new Set(talk), byRow = new Map(items.map(it => [it.row, it]));
    const line = [...items.filter(it => !inList.has(it.row)), ...talk.map(r => byRow.get(r) || (isLocal(r) ? {role: 'her', row: r} : null)).filter(Boolean)];
    for (const it of line) {
      const at = tsec(it.row.at);
      if (it.role === 'her') { cur = {user: it, start: at || 0}; seq.push(cur); continue; }
      let t;
      if (cur && !cur.reply) { cur.reply = it; cur.end = at; cur.steps = cur.start && cur.end ? stepsBetween(cur.start, cur.end) : []; t = cur; }
      else { t = {reply: it, start: at, end: at, steps: []}; seq.push(t); }
      by.set(it.kid, t);
    }
    seq.forEach((t, i) => { t.next = Number(seq[i + 1]?.start) || 0; });
    return by;
  }
  function threadState() {
    const {kl, items, locals} = threadItems();
    const base = S(CUR?.id) + '|' + kl.gen;
    if (!items.length && !locals.length && !THREAD.waiting) {
      if (THREAD.conv && !THREAD.loaded) return {key: base + '|load', msgs: [], items, locals};
      const nm = name(CUR || {});
      const msgs = [];
      if (S(CUR?.brief).trim()) msgs.push({id: 'brief', role: 'her', text: clean(S(CUR.brief)).trim()});
      msgs.push({id: 'say', role: 'hoola', text: S(CUR?.say) || 'Ask for anything on this website.'});
      msgs.push({id: 'start', role: 'raw', html: `${CUR?.name_by === 'hoola' ? `<p class="mut sm">I named it <b>${esc(nm)}</b>. Prefer your own name? Use the menu next to the name and pick Rename.</p>` : ''}
         <p class="mut sm">This chat is only about ${esc(nm)}. It stays here, not in your home chat.</p>
         <div class="ws-starts">${['Add a shop with cart', 'Add online payments', 'Add a Hindi version', 'Add booking slots'].map(t => `<button class="chip" type="button" data-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div>`});
      return {key: base + '|new|' + S(CUR?.say), msgs, items, locals};   // her site's line changed: said again
    }
    if (!kl.day) {
      const t0 = tsec(items[0]?.row.at) || nowS(), d = new Date(t0 * 1000);
      kl.day = `<div class="dday">${d.toDateString() === new Date().toDateString() ? 'Today' : d.toLocaleDateString([], {day: 'numeric', month: 'short'})} · ${esc(clockOf(t0))}</div>`;
    }
    const turns = turnsOf(items);
    const msgs = [{id: 'day', role: 'raw', html: kl.day}];
    for (const it of items) {
      if (it.role === 'her') { msgs.push({id: it.kid, role: 'her', text: it.text, files: L(it.row.files).map(f => S(M(f).name) || 'File')}); continue; }
      if (it.shown == null) it.shown = modeOfRow(turns.get(it.kid)?.user?.row) === 'plan' ? planFix(replyWords(it.row.text)) : replyWords(it.row.text);
      const t = turns.get(it.kid) || {}, steps = L(t.steps), took = t.start && t.end > t.start ? t.end - t.start : 0;
      msgs.push({id: it.kid, role: 'hoola', text: it.shown, ...(steps.length ? {worked: dur(took || 1), steps: steps.map(x => [pastLabel(x.label, x.state), x.end ? dur(x.end - x.at) : ''])} : {})});
    }
    return {key: base + '|t', msgs, items, locals};
  }
  /* what the working row says when no step is running */
  function workLabel() {
    if (THREAD.stopping) return 'Stopping after this step';
    if (THREAD.think && !THREAD.think.end) return 'Thinking…';
    return stepsBetween(THREAD.startedS || nowS()).length ? 'Working on the next step' : (THREAD.raw ? 'Writing the answer' : 'Reading your ask');
  }
  /* the steps of the turn that is running, only the ones that are new or changed since the kit last heard */
  function newSteps(K) {
    const since = THREAD.startedS || nowS(), out = [];
    const mine = [...THREAD.stepMap.entries()].filter(([, x]) => x.at && x.at >= since - 2).sort((a, b) => a[1].at - b[1].at);
    for (const [k, x] of mine) {
      if (K.gone.has(k)) continue;                           // folded into "Worked for" already
      const run = x.state === 'run', label = pastLabel(x.label, x.state), sig = x.state + '|' + label;
      if (K.sent.get(k) === sig) continue;
      K.sent.set(k, sig);
      out.push({id: k, label, ...(run ? {} : {state: x.state, ...(x.end ? {secs: Math.max(0, x.end - x.at)} : {})})});
    }
    return out;
  }
  function kitDraw() {
    if (KD.running) { KD.again = true; return; }
    KD.running = true;
    try { do { KD.again = false; kitOnce(); } while (KD.again); } finally { KD.running = false; }
  }
  function kitOnce() {
    const K = kitOf(); if (!K) return;
    const st = threadState(), ids = st.msgs.map(m => String(m.id));
    const same = K.key === st.key && K.ids.length <= ids.length && K.ids.every((x, i) => x === ids[i]);
    if (!same) {                                             // first time / another story: history, drawn whole
      K.t.sync({key: st.key, messages: st.msgs, working: false});
      Object.assign(K, {key: st.key, ids, locals: new Set(), sent: new Map(), gone: new Set(), ending: false, liveOn: false, liveText: ''});
    } else if (ids.length > K.ids.length) {
      const add = st.msgs.slice(K.ids.length), reply = add.find(m => m.role === 'hoola');
      if (reply) {
        // a finished reply: it goes on from the words already landing (their trailing space kept) and lands to its end
        const lt = K.liveText, cut = lt.trimEnd();
        if (lt && !reply.text.startsWith(lt) && reply.text.startsWith(cut)) { reply.text = lt + reply.text.slice(cut.length); const it = st.items.find(x => x.kid === reply.id); if (it) it.shown = reply.text; }
        K.t.sync({key: st.key, messages: st.msgs, working: false});
        const ho = [...K.root.querySelectorAll(':scope > .hck-ho')].pop(); if (ho && !ho.dataset.id) ho.dataset.id = reply.id;
        K.ending = K.t.busy; K.liveOn = false; K.liveText = '';
      } else K.t.sync({key: st.key, messages: st.msgs, working: K.t.busy && !K.ending});
      K.ids = ids;
    }
    // her message, shown the moment she sends (the server's copy is matched to it by the kit, never drawn twice)
    const fresh = st.locals.filter(r => !K.locals.has(r.id));
    if (fresh.length) {
      if (K.t.busy && !K.ending) { K.t.sync({key: st.key, messages: st.msgs, working: false}); K.ending = K.t.busy; K.liveOn = false; }
      if (K.t.busy) { if (!THREAD.sendNow) return; K.t.end(); }   // she just sent: the reply still landing is shown whole
      for (const r of fresh) { K.t.her(clean(r.text).trim(), {pending: true, id: r.id, files: L(r.files).map(f => S(M(f).name) || 'File')}); K.locals.add(r.id); }
    }
    THREAD.sendNow = false;
    if (K.ending) return;                                    // the last reply is still landing: kitEnded() draws again
    if (THREAD.waiting) {
      if (!K.t.busy) { K.sent = new Map(); K.gone = new Set(); K.liveText = ''; KOPT.startedAt = THREAD.startedS ? (THREAD.startedS - CLOCK) * 1000 : 0; }
      K.t.sync({key: st.key, messages: st.msgs, working: true, label: workLabel(), steps: newSteps(K)});
      K.liveOn = true; kitLive();
    } else if (K.t.busy) { K.t.sync({key: st.key, messages: st.msgs, working: false}); K.liveOn = false; }
    adorn(st.items);
    const box = $('#wsMsgs');
    if (THREAD.scrollTo && box) { const el = K.root.querySelector(`[data-id="${CSS.escape(THREAD.scrollTo)}"]`); THREAD.scrollTo = ''; if (el) box.scrollTop = Math.max(0, el.offsetTop - 12); }
    else keepPinned();
  }
  /* streamed words go to the kit as "the text so far": it lands only what is new, at the shared pace */
  function kitLive() {
    const K = KIT; if (!K || !K.liveOn || K.ending || !K.t.busy) return;
    const tx = liveText(); if (tx === K.liveText) return;
    if (!K.liveText) for (const k of K.sent.keys()) K.gone.add(k);   // words start: the steps so far fold
    K.liveText = tx; K.t.text(tx);
  }
  function kitNext() { const K = KIT; if (K && K.liveOn && !K.ending && K.t.busy && K.liveText) { K.t.nextBlock(); K.liveText = ''; } }
  const turnFor = it => S(it && (it.turn || THREAD.turnOf?.get(tkey(it.row.text))));
  /* Good answer / Not right: the same route the main chat uses, for the turn that wrote this reply */
  async function threadAct(kind, value, msg) {
    if (kind !== 'up' && kind !== 'down') return;
    const it = L(THREAD.kl?.items).find(x => x.kid === S(msg && msg.id)), turn = turnFor(it);
    if (!turn || !THREAD.conv) return;
    try {
      await api('POST', `/api/conversations/${enc(THREAD.conv)}/feedback`, {turn, value});
      if (value === 'down') toast('Thanks. Tell Hoola what was wrong and it will fix it.');
    } catch (e) { toast(e.message, true); KIT?.root.querySelectorAll('.hck-acts [aria-pressed="true"]').forEach(b => { if (b.dataset.act === kind) b.setAttribute('aria-pressed', 'false'); }); }
  }
  /* one named place inside a kit block for the Studio's own things; drawn again only when its words change */
  function slot(host, nm, html, before) {
    let s = host.querySelector(`:scope > [data-slot="${nm}"]`);
    if (!html) { s?.remove(); return null; }
    if (!s) { s = document.createElement('div'); s.dataset.slot = nm; s.className = 'ws-' + nm; }
    if (s._h !== html) { s.innerHTML = html; s._h = html; }
    const ref = before ? before() : null;
    if (s.parentNode !== host || s.nextElementSibling !== ref) host.insertBefore(s, ref);
    return s;
  }
  function adorn(items) {
    const K = KIT; if (!K) return;
    const turns = turnsOf(items), nodes = new Map();
    for (const n of K.root.children) if (n.dataset && n.dataset.id) nodes.set(n.dataset.id, n);
    const newest = [...items].reverse().find(x => x.role === 'hoola');
    for (const it of items) {
      const n = nodes.get(it.kid); if (!n) continue;
      if (it.role === 'her') {
        const editing = THREAD.editing === it.kid, at = tsec(it.row.at), before = verBefore(at), back = before && before < Number(CUR?.version);
        n.dataset.mid = it.kid; n.classList.toggle('editing', editing);
        slot(n, 'meedit', !editing && !THREAD.waiting ? `<button class="ib sm meedit" type="button" data-act="msg-edit" data-mid="${esc(it.kid)}" aria-label="Edit and resend this message" title="Edit">${ico('edit', 13)}</button>` : '');
        slot(n, 'meedwrap', editing ? `<form class="meed" data-form="resend" data-mid="${esc(it.kid)}" data-at="${Number(at) || 0}"><label class="sr" for="wsReEd">Edit your message</label>
              <textarea id="wsReEd" rows="3" maxlength="4000">${esc(it.text)}</textarea>
              <div class="inl"><span class="mut sm">${back ? `The site goes back to v${before} first (later changes stay in History).` : 'Sends it again.'}</span><span class="sp"></span>
              <button class="b sm" type="button" data-act="msg-cancel">Cancel</button><button class="b sm pri" type="submit">${back ? 'Revert and resend' : 'Resend'}</button></div></form>` : '');
        continue;
      }
      if (n.querySelector(':scope > .hck-work')) continue;   // still being written
      const t = turns.get(it.kid) || {}, txt = n.querySelector(':scope > .hck-txt'), fold = n.querySelector(':scope > .hck-fold'), acts = () => n.querySelector(':scope > .hck-acts');
      const took = t.start && t.end > t.start ? t.end - t.start : 0, steps = L(t.steps), inr = t.start ? costFor(t.start, t.end) : null;
      const th = Number(THREAD.thoughts.get(tkey(it.row.text))) || 0;   // how long the model thought for THIS answer
      const bits = [th >= 1 ? `Thought for ${dur(th)}` : '', !fold && took >= 1 ? `Worked for ${dur(took)}` : '', steps.length ? `${steps.length} step${steps.length > 1 ? 's' : ''}` : '', rs(inr)].filter(Boolean);
      slot(n, 'tmeta', bits.length ? `<span>${esc(bits.join(' · '))}</span><button class="ib sm" type="button" data-act="details" data-ta="${t.start}" data-tb="${t.end}" title="Timeline and changes" aria-label="Details of this answer">${ico('list', 14)}</button>` : '',
        () => txt || n.querySelector(':scope > [data-slot="cards"]') || acts());
      const um = modeOfRow(t.user?.row), sb = startBuild(it.row.text), body = sb ? sb.text : S(it.row.text);
      const made = t.reply === it ? versionsIn(t.start, t.next) : [], before = verBefore(t.start), top = made.length ? Math.max(...made) : 0;
      const vfoot = top ? `<div class="vfoot">${pill('Version ' + top, '')}${made.length > 1 ? `<span class="mut sm">${made.length} versions</span>` : ''}<span class="sp"></span>
            <button class="b sm ghost" type="button" data-act="ver-bm" data-ver="${top}">${ico('star', 13)}<span>Bookmark</span></button>
            ${before && restorable(before) ? `<button class="b sm" type="button" data-act="undo-turn" data-ver="${before}" data-top="${top}">${ico('back', 13)}<span>Undo this change</span></button>` : ''}</div>` : '';
      slot(n, 'cards', (um === 'plan' ? planCard(body) : '') + (sb ? buildCard(sb.ask) : '') + vfoot, acts);
      // Good answer / Not right only where the turn that wrote the reply is known (the server keeps them per turn)
      const can = it === newest && !!turnFor(it);
      acts()?.querySelectorAll('[data-act="up"],[data-act="down"]').forEach(b => { b.hidden = !can; });
    }
  }
  function onThreadEvent(ev) {
    const p = M(ev.payload);
    switch (ev.kind) {
      case 'reply_start':
        THREAD.waiting = true; THREAD.turn = S(p.turn); THREAD.raw = ''; THREAD.rawSeg = null; THREAD.seq = 0;
        drawWork(); return;
      case 'delta': {
        if (p.seq && p.seq <= (THREAD.seq || 0)) return; THREAD.seq = p.seq || 0;
        let moved = false;
        if (THREAD.think && !THREAD.think.end) { THREAD.think.end = nowS(); moved = true; }
        if (!THREAD.waiting) { THREAD.waiting = true; THREAD.startedS = THREAD.startedS || nowS(); moved = true; }
        if (p.seg != null && THREAD.rawSeg != null && p.seg !== THREAD.rawSeg && THREAD.raw) { THREAD.raw = ''; kitNext(); }   // words, steps, words: a new block
        if (p.seg != null) THREAD.rawSeg = p.seg;
        if (!THREAD.raw) moved = true;
        THREAD.raw += S(p.text);
        if (moved) drawWork(); else kitLive();
        return;
      }
      case 'delta_reset': THREAD.raw = ''; kitLive(); return;   // the words so far are void: the block is written again
      case 'reply_end': return;                                 // the words keep landing at their own pace
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
        if (!THREAD.waiting) { THREAD.waiting = true; THREAD.startedS = THREAD.startedS || x.at || nowS(); }
        drawWork(); return;
      }
      case 'typing':
        if (p.on) { if (!THREAD.waiting) { THREAD.waiting = true; THREAD.startedS = THREAD.startedS || nowS(); drawWork(); } }
        return;
      case 'message': {
        if (S(p.source) === 'greeting') return;
        const row = {id: ev.id, role: p.role, text: S(p.text), at: ev.at, source: p.source, files: p.files, turn: S(p.turn)};
        const talk = THREAD.rows.filter(r => (r.role === 'user' || r.role === 'assistant') && S(r.text).trim());
        if (p.role === 'user') {
          if (THREAD.queue.some(q => clean(q.text) === clean(row.text))) return;   // still waiting its turn (drawn greyed below)
          const mine = THREAD.rows.findIndex(r => S(r.id).startsWith('local-') && clean(r.text) === clean(row.text));
          const tail = talk[talk.length - 1];                 // the list was read first: the same line is not added twice
          if (mine >= 0) THREAD.rows[mine] = {...THREAD.rows[mine], ...row};
          else if (!THREAD.rows.some(r => r.id === row.id) && !(tail && tail.role === 'user' && !isLocal(tail) && clean(tail.text) === clean(row.text))) THREAD.rows.push(row);
          drawMsgs(); return;
        }
        if (p.role !== 'assistant' || p.ack || !row.text.trim()) return;
        let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
        const had = talk.slice(lu + 1).find(m => m.role === 'assistant' && S(m.text).trim() === row.text.trim());
        if (had) had.turn = had.turn || row.turn;
        else if (!THREAD.rows.some(r => r.id === row.id)) THREAD.rows.push(row);
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
    THREAD.stopping = false;
    drawMsgs();                                              // the reply lands now; its steps / rupees line follows
    await Promise.all([readSteps(c), readCosts(c)]);
    if (c !== THREAD.conv) return;
    drawMsgs(); reload();
  }
  async function readCosts(c) {
    try { const r = await api('GET', `/api/conversations/${enc(c)}/costs?limit=60`); THREAD.costs = L(r.costs); } catch { /* the rupee line is extra */ }
  }
  const costFor = (a, b) => {
    let inr = 0, n = 0;
    for (const x of L(THREAD.costs)) { const e = tsec(x.end) || tsec(x.start); if (e >= a - 2 && e <= b + 120) { inr += (Number(x.usd) || 0) * 1000; n++; } }   // credits
    return n ? inr : null;
  };
  // v0.999.29 a turn's cost in credits (1 credit = $0.001 of AI cost), never rupees
  const rs = v => v == null ? '' : v < 1 ? 'under 1 credit' : Math.round(v).toLocaleString('en-US') + (Math.round(v) === 1 ? ' credit' : ' credits');
  const clean = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  /* v0.658 the chat's own work feed, like Lovable: every tool step a turn ran (the timeline's step events), with a live
     timer while Hoola works and "Worked for 42s · 5 steps" kept above each answer. Times are the server's clock. */
  const tsec = a => { const t = S(a); if (!t) return 0; const ms = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(t) ? t : t + 'Z'); return isNaN(ms) ? 0 : ms / 1000; };
  async function readSteps(c) {
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/timeline?limit=200&steps=1`);
      const by = new Map();
      for (const ev of L(r.events)) {
        if (ev.kind === 'message') { const pm = M(ev.payload); if (pm.role === 'assistant' && pm.turn && S(pm.text).trim()) THREAD.turnOf.set(tkey(pm.text), S(pm.turn)); continue; }
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
  const fileChips = fs => L(fs).length ? `<div class="mfiles">${L(fs).map(f => `<span class="fchip">${ico('clip', 12)}<span class="ell">${esc(S(M(f).name) || 'File')}</span></span>`).join('')}</div>` : '';
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
      box.innerHTML = `<div id="wsHist" class="hck-tight"></div><div id="wsQ"></div>
        <button class="jump" type="button" data-act="jump-latest" hidden>${ico('down', 14)}<span>Latest</span></button>`;
      box.addEventListener('scroll', () => { THREAD.pinned = box.scrollHeight - box.scrollTop - box.clientHeight < 60; const j = box.querySelector('.jump'); if (j) j.hidden = THREAD.pinned || !THREAD.userScrolled; }, {passive: true});
      ['wheel', 'touchmove', 'keydown'].forEach(k => box.addEventListener(k, () => { THREAD.userScrolled = true; }, {passive: true}));   // only HER scrolling up shows Latest
    }
    kitDraw(); drawQueue(); drawStop();
  }
  function drawQueue() {
    const q = $('#wsQ'); if (!q) return;
    q.innerHTML = THREAD.queue.map((r, i) => `<div class="me queued" data-mid="${esc(S(r.id))}">${esc(clean(r.text))}${fileChips(r.files)}
      ${i === 0 ? `<span class="qacts"><button class="b sm" type="button" data-act="stop-turn" title="Stop the current work so this runs next">Interrupt</button></span>` : ''}</div>`).join('');
  }
  function keepPinned() { const box = $('#wsMsgs'); if (box && THREAD.pinned) box.scrollTop = box.scrollHeight; }
  /* Stop sits beside Send only while Hoola works (Send still queues her next message) */
  function drawStop() { const b = $('#wsStop'); if (b) b.hidden = !THREAD.waiting; }
  /* the ONE working row: the kit's mark + the real step words + the clock (kitDraw), and Stop in the composer */
  function drawWork() { kitDraw(); drawStop(); }
  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${enc(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;
      const local = THREAD.rows.filter(x => S(x.id).startsWith('local-') && !L(r.messages).some(m => m.role === 'user' && clean(m.text) === clean(x.text)));
      const waitingTexts = new Set(THREAD.queue.map(q => clean(q.text)));
      THREAD.rows = [...L(r.messages).filter(m => !(m.role === 'user' && waitingTexts.has(clean(m.text)))), ...local];
      THREAD.loaded = true;
    } catch { if (c === THREAD.conv && !THREAD.loaded) { THREAD.loaded = true; drawMsgs(); } return; }
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
      if (snap && S(snap.text) && !THREAD.raw) { THREAD.raw = S(snap.text); THREAD.rawSeg = snap.seg ?? null; THREAD.seq = Math.max(THREAD.seq || 0, Number(snap.seq) || 0); }   // a reload mid-reply continues the text
      // answered = a reply AFTER her own newest line (a new chat starts with a greeting, which is not the answer)
      const talk = THREAD.rows.filter(m => (m.role === 'user' || m.role === 'assistant') && S(m.text).trim());
      let lu = -1; talk.forEach((m, i) => { if (m.role === 'user') lu = i; });
      const answered = lu >= 0 && talk.slice(lu + 1).some(m => m.role === 'assistant');
      if (answered && !snap && !THREAD.queue.length) {
        if (THREAD.think) { THREAD.think.end = THREAD.think.end || nowS(); THREAD.lastThink = THREAD.think; THREAD.think = null; thoughtFor([...talk].reverse().find(m => m.role === 'assistant')?.text); }
        THREAD.waiting = false; THREAD.startedS = 0; THREAD.stopping = false; endLive(); reload();
      }
      else if (Date.now() - (THREAD.started || Date.now()) > 15 * 60e3) { THREAD.waiting = false; THREAD.stopping = false; }
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
      else { THREAD.rows.push(row); THREAD.waiting = true; THREAD.started = Date.now(); THREAD.startedS = nowS(); THREAD.think = null; THREAD.lastThink = null; THREAD.stopping = false; THREAD.sendNow = true; THREAD.seq = 0; endLive(); }
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
    try { await api('POST', `/api/conversations/${enc(THREAD.conv)}/stop`, {}); THREAD.stopping = THREAD.waiting; drawWork(); toast('Stopping after the step it is on.'); }
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

  /* v0.999.35 the chat is resizable: drag the line between the chat and the panel, arrow keys on it, double-click resets */
  let SPL = null;
  const setChatW = (w, save) => {
    const wsp = APP.querySelector('.wsp'); if (!wsp) return;
    w = Math.round(Math.max(320, Math.min(w, Math.max(320, window.innerWidth - 420), 1200)));
    wsp.style.setProperty('--wsc', w + 'px'); if (save) store.set(CW_KEY, String(w));
  };
  APP.addEventListener('pointerdown', e => {
    const sp = e.target.closest('.wsplit'); if (!sp) return;
    const ch = APP.querySelector('.wsp .chat'); if (!ch) return;
    SPL = {x: e.clientX, w: ch.getBoundingClientRect().width, el: sp};
    sp.classList.add('drag'); APP.querySelector('.wsp')?.classList.add('dragging');
    try { sp.setPointerCapture(e.pointerId); } catch {}
    e.preventDefault();
  });
  APP.addEventListener('pointermove', e => { if (SPL) setChatW(SPL.w + e.clientX - SPL.x, false); });
  const endDrag = () => {
    if (!SPL) return; SPL.el.classList.remove('drag'); APP.querySelector('.wsp')?.classList.remove('dragging');
    const ch = APP.querySelector('.wsp .chat'); if (ch) setChatW(ch.getBoundingClientRect().width, true); SPL = null;
  };
  APP.addEventListener('pointerup', endDrag); APP.addEventListener('pointercancel', endDrag);
  APP.addEventListener('dblclick', e => { if (e.target.closest('.wsplit')) { store.set(CW_KEY, ''); APP.querySelector('.wsp')?.style.removeProperty('--wsc'); } });
  APP.addEventListener('keydown', e => {
    if (e.target.closest?.('.wsplit') && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      const ch = APP.querySelector('.wsp .chat'); if (!ch) return;
      setChatW(ch.getBoundingClientRect().width + (e.key === 'ArrowLeft' ? -24 : 24), true); e.preventDefault();
    }
    if (e.key === 'Escape' && $('#wsLPages') && !$('#wsLPages').hidden) { $('#wsLPages').hidden = true; const t = APP.querySelector('[data-act="lpages"]'); t?.setAttribute('aria-expanded', 'false'); t?.focus(); }
    if (e.key === 'Escape' && APP.querySelector('.vmenu')) { APP.querySelectorAll('.vmenu').forEach(m => m.remove()); APP.querySelector('[data-act="views-more"]')?.focus(); }
  });
  document.addEventListener('click', e => {
    if (!e.target.closest('.vmw')) APP.querySelectorAll('.vmenu').forEach(m => m.remove());
    if (!e.target.closest('.lpw')) { const m = $('#wsLPages'); if (m && !m.hidden) { m.hidden = true; APP.querySelector('[data-act="lpages"]')?.setAttribute('aria-expanded', 'false'); } }
  });
  APP.addEventListener('click', async e => {
    const b = e.target.closest('button, a'); if (!b || !APP.contains(b)) return;
    if (b.closest('.hck-acts, .hck-bar')) return;            // Copy / Read aloud / Good answer / the kit's box: the kit handles them
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
      const n = $('#wsModeNote'); if (n) n.textContent = d.mode === 'plan' ? 'Plan: a plan for you to check first' : 'Build: a prototype of every page first'; return; }
    if (d.cmode) { setChatMode(d.cmode); return; }
    if (d.chip) { HOME.kind = HOME.kind === d.chip ? '' : d.chip; drawStarters(); return; }
    if (d.starter) { chooseStarter(d.starter); return; }
    if (d.type) { if (location.hash && location.hash !== '#/') { PREFILL = `Build a ${d.type} website: `; go('#/'); return; }
      const t = $('#wsAsk'); if (t) { t.value = `Build a ${d.type} website: `; t.focus(); t.setSelectionRange(t.value.length, t.value.length); } return; }
    if (d.src) { if (d.src === 'focus') { drawSource(''); $('#wsAsk')?.focus(); } else { drawSource(d.src); $('#wsSrc input')?.focus(); } return; }
    if (d.live === 'follow' || d.live === 'code') {        // v0.664 live build toggles
      if (d.live === 'follow') { LIVE.follow = !LIVE.follow; b.setAttribute('aria-pressed', String(LIVE.follow)); if (LIVE.follow) followPage(); }
      else { LIVE.code = !LIVE.code; drawPane(); }
      return;
    }
    if (d.lpage) { const m = $('#wsLPages'); if (m) { m.hidden = true; APP.querySelector('[data-act="lpages"]')?.setAttribute('aria-expanded', 'false'); } LIVE.follow = false; APP.querySelector('[data-live="follow"]')?.setAttribute('aria-pressed', 'false'); setLivePage(d.lpage); return; }
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
    if (d.ppage) { PPAGE = d.ppage; PSEL = null; PPICK = true; drawPane(); return; }           // v0.999.24 a prototype page
    if (d.file) { openFile(d.file); return; }
    if (d.coll) { openColl(d.coll); return; }
    if (d.ask != null && d.ask !== '') {
      if (d.ask.endsWith(': ')) { const t = $('#wsTh'); if (t) { t.value = d.ask; t.focus(); } return; }
      ask(d.ask); return;
    }
    const act = d.act; if (!act) return;
    if (act === 'new') { if (location.hash && location.hash !== '#/') go('#/'); else $('#wsAsk')?.focus(); return; }
    if (act === 'wrow') {                          // v0.999.35 the working row's steps
      WROW_OPEN = !WROW_OPEN; const w = b.closest('.hck-work'); if (w) w.classList.toggle('open', WROW_OPEN);
      b.setAttribute('aria-expanded', String(WROW_OPEN)); return;
    }
    if (act === 'lpages') {
      const m = $('#wsLPages'); if (!m) return;
      m.hidden = !m.hidden; b.setAttribute('aria-expanded', String(!m.hidden));
      if (!m.hidden) (m.querySelector('[aria-current="page"]') || m.querySelector('button'))?.focus();
      return;
    }
    if (act === 'views-more') {
      const w = b.closest('.vmw'), open = w && w.querySelector('.vmenu');
      APP.querySelectorAll('.vmenu').forEach(m => m.remove());
      if (!w || open) { b.setAttribute('aria-expanded', 'false'); return; }
      w.insertAdjacentHTML('beforeend', `<div class="vmenu" role="menu">${MORE_VIEWS.map(([k, n]) => `<button type="button" role="menuitem" data-view="${k}"${VIEW === k ? ' aria-current="page"' : ''}>${esc(n)}</button>`).join('')}</div>`);
      b.setAttribute('aria-expanded', 'true'); w.querySelector('.vmenu button')?.focus(); return;
    }
    if (act === 'pane-close' || act === 'pane-open') {
      const shut = act === 'pane-close'; store.set(PANE_KEY, shut ? '1' : '');
      APP.querySelector('.wsp')?.classList.toggle('pclosed', shut); if (!shut) fit(); return;
    }
    if (act === 'pend-more') {                     // v0.986 her long first message, folded so the work card stays in view
      const m = $('#wsPendMe'), open = m && m.classList.toggle('open');
      b.textContent = open ? 'Show less' : 'Show all'; b.setAttribute('aria-expanded', open ? 'true' : 'false'); return;
    }
    if (act === 'rx-edit') { RXE.on = !RXE.on; RXE.panel = ''; RXE.pick = null; if (RXE.on) await rxLoad(true); rxSay({t: 'mode', mode: RXE.on ? 'site' : 'off'}); drawPane(); return; }
    if (act === 'rx-close') { RXE.pick = null; RXE.panel = ''; rxDraw(); return; }
    if (act === 'rx-undo') return rxDo('undo');
    if (act === 'rx-drop') { if (RXE.pick && confirm('Leave this section out of the page? Undo brings it back.')) return rxDo('section', {sec: RXE.pick.sec, drop: true}, () => { RXE.pick = null; }); return; }
    if (act === 'rx-design') { try { RXE.design = await api('GET', `/api/sites/${enc(CUR.id)}/rx/design`); RXE.panel = 'design'; rxDraw(); } catch (er) { toast(er.message, true); } return; }
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
    if (act && act.startsWith('proto-')) {                                        // v0.999.24 PROTOTYPE FIRST
      BUSY = true;
      try { await protoAct(act, b); } catch (er) { toast(er.message, true); } finally { BUSY = false; }
      return;
    }
    const id = CUR ? enc(CUR.id) : '';
    BUSY = true; b.setAttribute('aria-disabled', 'true');
    try {
      if (act === 'approve') { await api('POST', `/api/sites/${id}/plan`, {conversation_id: await ensureConv().catch(() => '')}); toast('Making the prototype of every page.'); await reload(); }
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
      } else if (act === 'like-del') {
        await api('DELETE', `/api/appengine-refs/links/${enc(S(b.dataset.likeId))}`); toast('Removed.'); await loadLikes();
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
  APP.addEventListener('input', e => { if (e.target.id === 'wsPendTa') store.set(PEND_KEY, S(e.target.value)); });   // v0.986
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
    if (e.target.matches?.('#wsAsk, #wsTh')) { e.preventDefault(); e.target.form?.requestSubmit(); }   // #wsRev is the kit's own box
  });

  APP.addEventListener('submit', async e => {
    const f = e.target.closest('form[data-form]'); if (!f) return;
    e.preventDefault();
    const kind = f.dataset.form;
    if (kind === 'proto-edit') { try { await protoSave(f); } catch (er) { toast(er.message, true); } return; }
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
    if (kind === 'rx-words') {                            // v0.999.70 D7 her words, shown at once, built by code
      const p = RXE.pick, nw = S(f.querySelector('[name=new]')?.value).trim(); if (!p || !nw) return;
      return rxDo('words', {sec: p.sec, old: p.text, new: nw}, () => { rxSay({t: 'sec-text', sec: p.sec, old: p.text, new: nw}); p.text = nw; });
    }
    if (kind === 'like-add') {                            // v0.999.69 D6 a site she likes (a picture of its first screen is taken)
      const url = S(f.querySelector('[name=url]')?.value).trim(); if (!url) return;
      const btn = f.querySelector('button'); if (btn) btn.disabled = true;
      try { await api('POST', '/api/appengine-refs/links', {url, note: S(f.querySelector('[name=note]')?.value).trim()}); f.reset(); toast('Added. Hoola will use its feel as a pattern.'); await loadLikes(); }
      catch (er) { toast(er.message, true); }
      finally { if (btn) btn.disabled = false; }
      return;
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
        const ticket = plan ? '' : 'st-' + Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
        drawPending(plan, t, ticket);               // v0.707: straight into the workspace, the work shows there
        try { await startFromAsk(t, ticket); }   // v0.988 no choices page: Hoola reads her words and asks if it must
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
      else if (kind === 'code') {
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
  // v0.999.70 D7: the preview tells what she clicked; the panels change a section / the design (all free)
  addEventListener('message', ev => {
    const d = ev.data || {}; if (d.hoola !== 'ae' || !CUR) return;
    const f = rxFrame(); if (!f || ev.source !== f.contentWindow) return;
    if (d.t === 'ready' && RXE.on) rxSay({t: 'mode', mode: 'site'});
    if (d.t === 'sec-pick' && RXE.on) { RXE.pick = {sec: S(d.sec), text: S(d.text), tag: S(d.tag)}; RXE.panel = ''; rxDraw(); }
    if (d.t === 'mode' && d.mode === 'off' && RXE.on) { RXE.on = false; drawPane(); }
  });
  APP.addEventListener('change', e => {
    const t = e.target;
    if (t.dataset.rxs && RXE.pick && t.value) return rxDo('section', {sec: RXE.pick.sec, [t.dataset.rxs]: t.value});
    if (t.dataset.rxd && CUR) {
      const k = t.dataset.rxd, body = {[k]: k === 'radius' ? Number(t.value) : t.value};
      (async () => { try { const r = await api('POST', `/api/sites/${enc(CUR.id)}/rx/design`, body); RXE.design.design = M(r.design); toast(S(r.say).slice(0, 140)); rxDraw(); rxWatch(); } catch (er) { toast(er.message, true); } })();
    }
  });
  APP.addEventListener('input', e => { if (e.target.dataset.rxd === 'radius') { const o = APP.querySelector('[data-rxr]'); if (o) o.textContent = e.target.value; } });
  APP.addEventListener('change', e => { if (e.target.id === 'wsFile') { [...e.target.files].slice(0, 6).forEach(f => addFile(f)); e.target.value = ''; } });
  APP.addEventListener('dragover', e => { if (e.target.closest?.('.chat') && e.dataTransfer?.types?.includes('Files')) { e.preventDefault(); e.target.closest('.chat').classList.add('drop'); } });
  APP.addEventListener('dragleave', e => { e.target.closest?.('.chat')?.classList.remove('drop'); });
  APP.addEventListener('drop', e => { const c = e.target.closest?.('.chat'); if (!c || !e.dataTransfer?.files?.length) return; e.preventDefault(); c.classList.remove('drop'); [...e.dataTransfer.files].slice(0, 6).forEach(f => addFile(f)); });

  // v0.814 APP ENGINE 1: appengine.js draws the app pages with the Studio's own helpers and sidebar
  window.HoolaWSKit = {api, esc, enc, ico, toast, sidebar, go, store, pill, ago, md: window.HoolaMD, APP, clean};
  route();
})();
