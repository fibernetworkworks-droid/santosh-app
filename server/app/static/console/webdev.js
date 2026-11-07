/* v0.646 WEB DEVELOPMENT PANEL 2 (console) - the panel WORKS ON ITS OWN, end to end.

   v0.636 drew the owner-approved prototype but sent every ask to the main chat ("when I type the prompt it goes to main
   chat on homepage"). Now nothing leaves this page:
   - the home ask creates the website here (POST /api/sites) and opens its workspace;
   - the workspace walks the real steps on the server's own state: the plan (pages to keep, the questions, the AI cost)
     -> her Haan -> three looks with their real screenshots -> her pick -> the build with its progress -> the live preview
     (phone / computer) -> changes in her words -> Publish. The page polls the site while the server is working;
   - every site has ITS OWN Hoola thread inside the workspace (a conversation of its own, never the home chat): shop,
     payments, booking, languages, GitHub, team... are asked there, so the agent's plan cards and rules apply as before;
   - "Move my old site" and "Screenshot" read the design here (/api/site-design/read): her own site only, the ownership
     proof is shown when the server asks for it; her tap uses it (/api/site-design/use);
   - going live, rollback, take-down and the old-address redirects stay HER taps with the server's hash (confirm first);
   - every value from the server goes through esc(); colours are drawn only when they are plain #hex.

   Class prefix `wdp-` on purpose: `#app .wd-body` / `.wd-new` / `.wd-info` already belong to the Game Desk (v0.420) and
   were pulling this page into a wrapped flex row - that is what broke the alignment. */
'use strict';
window.HoolaWebDev = function ({api, esc, toast, studio}) {
  let EL = null, SITES = [], CUR = null, TAB = 'overview', BUSY = false, POLL = null, DEVICE = 'pc';
  const THREAD = {site: '', conv: '', rows: [], live: '', waiting: false, since: 0, timer: null, sig: ''};
  const BLOBS = new Map();
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' ? v : {};
  const HEX = v => /^#[0-9a-f]{3,8}$/i.test(S(v)) ? S(v) : '';
  const sid = () => encodeURIComponent(CUR?.id || '');
  const TABS = [['overview', 'Workspace'], ['build', 'Build'], ['edit', 'Edit'], ['code', 'Code'], ['data', 'Data & logins'],
    ['integrations', 'Integrations'], ['publish', 'Publish'], ['health', 'Health'], ['settings', 'Settings']];
  const STATUS = {draft: ['Starting', ''], planned: ['Plan ready', 'warn'], looks: ['Pick a look', 'warn'],
    building: ['Building', 'v'], checking: ['Checking', 'v'], ready: ['Ready', 'ok'], failed: ['Needs attention', 'bad'], stopped: ['Paused', '']};
  const WORKING = v => ['building', 'checking'].includes(S(v.status)) || (S(v.status) === 'looks' && !L(v.looks).length) || !!v.mapping;
  const pill = (t, c) => `<span class="wdp-pill ${c || ''}">${esc(t)}</span>`;
  const ICON = {
    chat: '<path d="M4 5h16v11H8l-4 4z"/>', move: '<path d="M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4"/>',
    pic: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 15l5-5 4 4 3-3 6 6"/>', sheet: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    cart: '<path d="M4 6h2l2 10h10l2-7H8"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>', card: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>', blog: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 11h8M8 15h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>', pin: '<path d="M12 21s-7-6-7-12a7 7 0 0 1 14 0c0 6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    send: '<path d="M5 12h13M13 6l6 6-6 6"/>', back: '<path d="M15 5l-7 7 7 7"/>', phone: '<rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>', ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5H5V6h5"/>', check: '<path d="M5 12l5 5 9-10"/>'};
  const ico = (k, n = 20) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const statusPill = v => { const [t, c] = STATUS[S(v.status)] || [S(v.status) || '…', '']; return pill(t + (Number(v.version) ? ` · v${v.version}` : ''), c); };
  const name = v => S(v.name) || S(v.field_label) || 'Website';
  const hasVersion = v => !!Number(v.version);
  const TYPES = ['Sweet shop', 'Restaurant menu', 'Salon booking', 'Clinic', 'School admissions', 'Coaching classes', 'Online shop',
    'Portfolio', 'Event / wedding', 'NGO / cause', 'Real estate', 'Personal page'];
  const store = {get(k) { try { return localStorage.getItem(k) || ''; } catch { return ''; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }};
  const convKey = id => 'hoola.wdp.conv.' + id;
  const live = () => !!EL && EL.isConnected && EL.offsetParent !== null;

  async function loadSites() {
    try { SITES = L((await api('GET', '/api/sites')).sites); } catch (e) { SITES = []; toast(e.message, true); }
  }
  async function loadSite(id) {
    try { CUR = await api('GET', `/api/sites/${encodeURIComponent(id)}`); return true; }
    catch (e) { toast(e.message, true); CUR = null; return false; }
  }

  async function open(el, arg) {
    EL = el;
    if (!EL.dataset.wdBound) {
      EL.dataset.wdBound = '1';
      EL.addEventListener('click', onClick); EL.addEventListener('submit', onSubmit); EL.addEventListener('keydown', onKey);
      EL.addEventListener('change', onChange);
    }
    if (arg) { if (await loadSite(arg)) { TAB = 'overview'; return draw(); } }
    if (!CUR) { EL.innerHTML = `<div class="wdp"><div class="wdp-empty">Loading…</div></div>`; await loadSites(); }
    draw();
  }

  function draw() {
    if (!EL) return;
    stopPoll();
    if (CUR) drawSite(); else drawHome();
  }

  /* ================= home ================= */
  function drawHome() {
    const start = [['chat', 'Describe it', 'One line in your own words. Hoola plans first.', 'focus'],
      ['move', 'Move my old site', 'Your own site only. Old addresses keep working.', 'old'],
      ['pic', 'Screenshot or picture', 'Colours and style are measured; no words or logos taken.', 'shot'],
      ['sheet', 'A product sheet', 'Excel, CSV or Google Sheet becomes a catalogue.', 'sheet']];
    const sites = SITES.length ? `<div class="wdp-sites">${SITES.map(v => `<button class="wdp-site" type="button" data-wd-site="${esc(S(v.id))}">
        <span class="wdp-thumb" aria-hidden="true"><i></i><i></i><i></i><b></b></span>
        <span class="wdp-site-row"><b>${esc(name(v))}</b>${statusPill(v)}</span>
        <span class="wdp-mut sm">${esc([S(v.number), S(v.field_label), S(v.goal_label)].filter(Boolean).join(' · '))}</span></button>`).join('')}</div>`
      : `<div class="wdp-card wdp-mut">No website yet. Write one line above and Hoola starts here.</div>`;
    EL.innerHTML = `<div class="wdp">
      <header class="wdp-head"><div><h2>Web Development</h2><p class="wdp-mut">Plan first. Nothing is built before your Haan, nothing goes live before your tap.</p></div></header>
      <section class="wdp-hero"><h3>What should we build today?</h3>
        <p class="wdp-mut">Hoola plans the pages, shows you three looks, builds and checks every page, and puts it live only when you tap.</p>
        <form class="wdp-ask" data-wd-form="ask">
          <label for="wdAsk" class="wdp-sr">Your website in one line</label>
          <textarea id="wdAsk" rows="3" maxlength="2000" placeholder="e.g. Sharma Sweets, Akola ki mithai dukaan ki website banao - menu, Diwali orders aur WhatsApp button"></textarea>
          <div class="wdp-ask-bar"><span class="wdp-mut sm">Anything you don't know stays blank, never made up.</span>
            <button class="wdp-send" type="submit" aria-label="Plan my website"><span>Plan my website</span>${ico('send', 18)}</button></div>
        </form></section>
      <section class="wdp-sec"><h4>Or start from</h4><div class="wdp-starts">${start.map(([k, t, d, a]) => `<button class="wdp-start" type="button" data-wd-start="${a}">
          <span class="wdp-ico">${ico(k)}</span><span class="wdp-start-t"><b>${esc(t)}</b><span class="wdp-mut sm">${esc(d)}</span></span></button>`).join('')}</div>
        <div id="wdpSource"></div></section>
      <section class="wdp-sec"><div class="wdp-sec-head"><h4>Your websites${SITES.length ? ` <span class="wdp-mut">(${SITES.length})</span>` : ''}</h4>
        <button class="wdp-btn ghost" type="button" data-wd-act="refresh">Refresh</button></div>${sites}</section>
      <section class="wdp-sec"><h4>Start with a business type</h4><div class="wdp-chips">${TYPES.map(t => `<button class="wdp-chip" type="button" data-wd-type="${esc(t)}">${esc(t)}</button>`).join('')}</div></section>
    </div>`;
  }

  function drawSource(kind) {
    const box = EL.querySelector('#wdpSource'); if (!box) return;
    if (kind === 'old') box.innerHTML = `<form class="wdp-card wdp-src" data-wd-form="old"><h4>Move my old website</h4>
        <p class="wdp-mut sm">Hoola reads your own site's pages, colours, photos and addresses. If it can't tell the site is yours, it shows you one line to add first.</p>
        <div class="wdp-inline"><input name="url" type="url" inputmode="url" aria-label="Your old website address" placeholder="https://your-old-site.in" required>
        <button class="wdp-btn pri" type="submit">Read my site</button></div><div class="wdp-src-out"></div></form>`;
    else if (kind === 'shot') box.innerHTML = `<form class="wdp-card wdp-src" data-wd-form="shot"><h4>Use a design you like</h4>
        <p class="wdp-mut sm">A screenshot or picture: its colours and style are measured. No words, logos or photos are taken from it.</p>
        <div class="wdp-inline"><input name="file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Screenshot" required>
        <button class="wdp-btn pri" type="submit">Read the design</button></div><div class="wdp-src-out"></div></form>`;
    else if (kind === 'sheet') box.innerHTML = `<div class="wdp-card wdp-src"><h4>From a product sheet</h4>
        <p class="wdp-mut sm">Write one line about the shop above and put the sheet link in it. Once the website is built, open Data &amp; logins to preview the catalogue before anything is written.</p></div>`;
    else box.innerHTML = '';
  }

  /* ================= one site ================= */
  function drawSite() {
    const v = CUR;
    EL.innerHTML = `<div class="wdp">
      <header class="wdp-head site"><button class="wdp-iconbtn" type="button" data-wd-act="home" aria-label="Back to all websites" title="All websites">${ico('back', 18)}</button>
        <div class="wdp-title"><div class="wdp-title-row"><h2>${esc(name(v))}</h2><span id="wdpPill">${statusPill(v)}</span></div>
          <p class="wdp-mut sm">${esc([S(v.number), S(v.field_label), S(v.goal_label)].filter(Boolean).join(' · '))}</p></div>
        <div class="wdp-head-acts">${v.preview && hasVersion(v) ? `<a class="wdp-btn" href="${esc(S(v.preview))}" target="_blank" rel="noopener">${ico('ext', 16)}<span>Preview</span></a>` : ''}
          ${hasVersion(v) ? '<button class="wdp-btn pri" type="button" data-wd-tab="publish">Publish</button>' : ''}</div></header>
      <nav class="wdp-tabs" aria-label="Website sections">${TABS.map(([k, n]) => `<button type="button" data-wd-tab="${k}" aria-current="${k === TAB ? 'page' : 'false'}">${esc(n)}</button>`).join('')}</nav>
      <div class="wdp-pane" id="wdpPane"><div class="wdp-empty">Loading…</div></div></div>`;
    const pane = EL.querySelector('#wdpPane');
    ({overview, build, edit, code, data, integrations, publish, health, settings})[TAB](pane, v);
  }

  /* ---------- Workspace: the steps on the left, the site's own Hoola thread on the right ---------- */
  function overview(box, v) {
    box.innerHTML = `<div class="wdp-split"><div class="wdp-main" id="wdpFlow"></div>
      <aside class="wdp-side"><section class="wdp-card wdp-thread" aria-label="Ask Hoola about this website">
        <div class="wdp-thread-head"><b>Ask Hoola</b><span class="wdp-mut sm">about ${esc(name(v))} only</span></div>
        <div class="wdp-msgs" id="wdpMsgs" aria-live="polite"></div>
        <form class="wdp-compose" data-wd-form="thread"><label for="wdpTh" class="wdp-sr">Message about this website</label>
          <textarea id="wdpTh" rows="2" maxlength="4000" placeholder="Add a shop, online payments, a Hindi version…"></textarea>
          <button class="wdp-send round" type="submit" aria-label="Send">${ico('send', 18)}</button></form></section></aside></div>`;
    drawFlow();
    openThread();
  }

  function drawFlow() {
    const box = EL?.querySelector('#wdpFlow'); if (!box || !CUR) return;
    const v = CUR, st = S(v.status);
    const pillEl = EL.querySelector('#wdpPill'); if (pillEl) pillEl.innerHTML = statusPill(v);
    const say = S(v.say) ? `<p class="wdp-say">${esc(S(v.say))}</p>` : '';
    let main = '';
    if (st === 'planned' && v.mapping) main = progressCard('Making the site map', 'A big website: Hoola is planning every page first.', v);
    else if (st === 'planned') main = planCard(v);
    else if (st === 'looks' && !L(v.looks).length) main = progressCard('Making three looks', 'Three different designs of your home page, with real screenshots.', v);
    else if (st === 'looks') main = looksCard(v);
    else if (WORKING(v)) main = progressCard(st === 'checking' ? 'Checking every page' : 'Building your website', 'Each page is written, put together and checked on a phone and a computer.', v);
    else if (st === 'failed' || st === 'stopped') main = `<section class="wdp-card ${st === 'failed' ? 'danger' : ''}"><h4>${st === 'failed' ? 'The build stopped on a problem' : 'Building is paused'}</h4>
        ${say}${v.error ? `<p class="wdp-li bad">${esc(S(v.error))}</p>` : ''}
        <div class="wdp-acts"><button class="wdp-btn pri" type="button" data-wd-act="resume">${st === 'failed' ? 'Try again' : 'Continue building'}</button>
        <button class="wdp-btn" type="button" data-wd-studio="kadam">See every step</button></div></section>`;
    if (hasVersion(v) && !WORKING(v)) main += previewCard(v);
    box.innerHTML = stepper(v) + (main || `<section class="wdp-card">${say || '<p class="wdp-mut">Nothing to do right now.</p>'}</section>`)
      + (hasVersion(v) ? `<section class="wdp-card"><h4>Change something</h4>${changeForm(v)}</section>` : '');
    fitPreview();
    loadLookShots();
    if (WORKING(v)) startPoll();
  }

  function stepper(v) {
    const st = S(v.status);
    const at = st === 'planned' ? 0 : st === 'looks' ? 1 : WORKING(v) ? 2 : hasVersion(v) ? 3 : 0;
    const done = st === 'ready' && hasVersion(v);
    const steps = ['Plan', 'Look', 'Build', 'Preview'];
    return `<ol class="wdp-steps" aria-label="Steps">${steps.map((t, i) => {
      const cls = i < at || (done && i === at) ? 'done' : i === at ? 'now' : '';
      return `<li class="${cls}" ${i === at ? 'aria-current="step"' : ''}><span class="wdp-dot">${cls === 'done' ? ico('check', 14) : i + 1}</span><span>${t}</span></li>`;
    }).join('')}</ol>`;
  }

  function planCard(v) {
    const pages = L(M(v.plan).pages), qs = L(v.questions), est = M(v.estimate);
    return `<form class="wdp-card accent" data-wd-form="plan"><div class="wdp-card-head"><h4>The plan: ${pages.length} pages</h4>${pill('Waiting for your Haan', 'warn')}</div>
      <p class="wdp-mut sm">Untick a page you don't want. Home always stays.</p>
      <div class="wdp-pages">${pages.map(p => `<label class="wdp-page"><input type="checkbox" name="page" value="${esc(S(p.slug))}" checked ${S(p.slug) === 'home' ? 'disabled' : ''}>
        <span><b>${esc(S(p.title))}</b><span class="wdp-mut sm">${esc(L(p.sections).slice(0, 4).join(' · '))}</span></span></label>`).join('')}</div>
      ${qs.length ? `<div class="wdp-qs"><h5>A few details (leave blank if you don't know)</h5>${qs.map((q, i) => `<label class="wdp-fld"><span>${esc(S(q))}</span><input name="q${i}" data-q="${i}" autocomplete="off"></label>`).join('')}</div>` : ''}
      ${est.say ? `<p class="wdp-note">${esc(S(est.say))}</p>` : ''}
      <div class="wdp-acts end"><button class="wdp-btn danger-ghost" type="button" data-wd-act="delete">Delete</button><span class="sp"></span><button class="wdp-btn pri" type="submit">Haan, aage badho</button></div></form>`;
  }

  function looksCard(v) {
    return `<section class="wdp-card accent"><div class="wdp-card-head"><h4>Pick one of three looks</h4>${pill('Your pick', 'warn')}</div>
      <p class="wdp-mut sm">Real screenshots of your home page. Pick one; the whole site is then built in it.</p>
      <div class="wdp-looks">${L(v.looks).slice(0, 3).map((lk, i) => {
        const sh = M(lk.shots), shot = S(sh['1280'] || sh['390'] || Object.values(sh)[0] || '');
        return `<article class="wdp-look"><div class="wdp-look-img">${shot ? `<img alt="Look ${i + 1}: ${esc(S(lk.label))}" data-shot="${esc(shot)}">` : '<span class="wdp-mut sm">No screenshot</span>'}</div>
          <div class="wdp-look-body"><div class="wdp-site-row"><b>${i + 1}. ${esc(S(lk.label))}</b></div>
          <div class="wdp-swatches">${L(lk.colors).map(HEX).filter(Boolean).map(c => `<i style="background:${c}" title="${c}"></i>`).join('')}</div>
          ${lk.concept ? `<p class="wdp-mut sm">${esc(S(lk.concept))}</p>` : ''}
          <button class="wdp-btn pri full" type="button" data-wd-act="look" data-i="${Number(lk.i ?? i)}">Choose this look</button></div></article>`;
      }).join('')}</div></section>`;
  }

  function progressCard(title, note, v) {
    const b = M(v.board), pct = Math.max(4, Math.min(100, Number(b.pct) || 0));
    return `<section class="wdp-card"><div class="wdp-card-head"><h4>${esc(title)}</h4><span class="wdp-spin" aria-hidden="true"></span></div>
      <p class="wdp-mut sm">${esc(note)}</p>
      <div class="wdp-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><i style="width:${pct}%"></i></div>
      <div class="wdp-site-row"><span class="wdp-mut sm">${esc(S(b.now) || S(v.say) || 'Working…')}</span>${b.total ? `<span class="wdp-mut sm">${esc(S(b.done || 0))} / ${esc(S(b.total))}</span>` : ''}</div>
      ${['building', 'checking'].includes(S(v.status)) ? `<div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-studio="board">Watch the board</button><button class="wdp-btn" type="button" data-wd-act="stop">Pause</button></div>` : ''}</section>`;
  }

  function previewCard(v) {
    if (!v.preview) return '';
    return `<section class="wdp-card wdp-prevcard"><div class="wdp-card-head"><h4>Preview · v${esc(S(v.version))}</h4>
        <div class="wdp-seg" role="group" aria-label="Device"><button type="button" data-wd-dev="pc" aria-pressed="${DEVICE === 'pc'}">${ico('pc', 16)}<span>Computer</span></button>
        <button type="button" data-wd-dev="phone" aria-pressed="${DEVICE === 'phone'}">${ico('phone', 16)}<span>Phone</span></button></div></div>
      <div class="wdp-frame ${DEVICE}" data-w="${DEVICE === 'pc' ? 1280 : 390}" data-h="${DEVICE === 'pc' ? 800 : 780}">
        <iframe title="Website preview" sandbox="allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer" src="${esc(S(v.preview))}"></iframe></div>
      <div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-studio="preview" data-wd-edit="1">Edit on the page</button>
        <button class="wdp-btn" type="button" data-wd-studio="jaanch">Checks</button><span class="sp"></span>
        <button class="wdp-btn pri" type="button" data-wd-tab="publish">Go live…</button></div></section>`;
  }

  let RO = null;
  function fitPreview() {
    const f = EL?.querySelector('.wdp-frame'); if (!f) return;
    const go = () => {
      const w = Number(f.dataset.w), h = Number(f.dataset.h), fr = f.querySelector('iframe'); if (!fr) return;
      const k = Math.min(1, f.clientWidth / w);
      fr.style.width = w + 'px'; fr.style.height = h + 'px'; fr.style.transform = `scale(${k})`;
      f.style.height = Math.round(h * k) + 'px';
    };
    go();
    if (window.ResizeObserver) { RO?.disconnect(); RO = new ResizeObserver(go); RO.observe(f); }
  }

  function loadLookShots() {
    EL?.querySelectorAll('img[data-shot]').forEach(img => {
      const p = `/api/sites/${sid()}/shots/${S(img.dataset.shot).split('/').map(encodeURIComponent).join('/')}`;
      const have = BLOBS.get(p);
      const set = u => { img.src = u; img.classList.add('in'); };
      if (have) return have.then(set).catch(() => img.replaceWith(Object.assign(document.createElement('span'), {className: 'wdp-mut sm', textContent: 'Picture not found'})));
      const pr = api('GET', p, undefined, {raw: true}).then(r => r.blob()).then(b => URL.createObjectURL(b));
      BLOBS.set(p, pr);
      pr.then(set).catch(() => { BLOBS.delete(p); img.alt = 'Picture not found'; });
    });
  }

  function startPoll() {
    stopPoll();
    const id = CUR?.id;
    POLL = setTimeout(async () => {
      POLL = null;
      if (!live() || !CUR || CUR.id !== id) return;
      try { CUR = await api('GET', `/api/sites/${encodeURIComponent(id)}`); } catch { return startPoll(); }
      if (TAB === 'overview') drawFlow(); else { const p = EL.querySelector('#wdpPill'); if (p) p.innerHTML = statusPill(CUR); if (WORKING(CUR)) startPoll(); }
    }, 3500);
  }
  function stopPoll() { if (POLL) { clearTimeout(POLL); POLL = null; } }

  const changeForm = v => hasVersion(v) || WORKING(v)
    ? `<form data-wd-form="change" class="wdp-change"><label for="wdChg" class="wdp-sr">Change in your own words</label>
        <textarea id="wdChg" rows="2" maxlength="2000" placeholder="e.g. Hero mein Diwali offer daalo, 10% off on gift boxes"></textarea>
        <div class="wdp-ask-bar"><span class="wdp-mut sm">Only the parts it touches are rewritten; anything that goes missing is named.</span>
        <button class="wdp-btn pri" type="submit">Make the change</button></div></form>`
    : '<p class="wdp-mut">Changes open once the first version is built.</p>';

  /* ---------- the site's own Hoola thread (its own conversation, never the home chat) ---------- */
  async function ensureConv() {
    if (THREAD.conv && THREAD.site === CUR.id) return THREAD.conv;
    THREAD.site = CUR.id;
    const key = convKey(CUR.id);
    let c = store.get(key);
    if (c) { try { await api('GET', `/api/conversations/${encodeURIComponent(c)}/messages?limit=1`); } catch { c = ''; } }
    if (!c) {
      c = S((await api('POST', '/api/conversations')).id);
      store.set(key, c);
      api('PATCH', `/api/conversations/${encodeURIComponent(c)}`, {title: `Website · ${name(CUR)}`}).catch(() => {});
    }
    THREAD.conv = c;
    return c;
  }

  async function openThread() {
    clearTimeout(THREAD.timer);
    Object.assign(THREAD, {site: CUR.id, conv: '', rows: [], live: '', sig: '', waiting: false, since: 0});
    const c = store.get(convKey(CUR.id));
    drawMsgs();
    if (!c) return;
    THREAD.conv = c;
    await readThread();
  }

  const clean = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  const md = t => window.HoolaMD ? window.HoolaMD.render(t, false) : `<p>${esc(t)}</p>`;

  function drawMsgs() {
    const box = EL?.querySelector('#wdpMsgs'); if (!box) return;
    const all = THREAD.rows.filter(r => r.role === 'user' || r.role === 'assistant').filter(r => S(r.text).trim());
    const first = all.findIndex(r => r.role === 'user');
    const rows = first < 0 ? [] : all.slice(first);              // the new chat's greeting is not part of this site's thread
    const sig = rows.map(r => r.id).join(',') + '|' + THREAD.live.length + '|' + THREAD.waiting;
    if (sig === THREAD.sig) return;
    THREAD.sig = sig;
    const near = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    box.innerHTML = rows.length || THREAD.waiting ? rows.slice(-40).map(r => r.role === 'user'
        ? `<div class="wdp-msg me">${esc(clean(r.text))}</div>` : `<div class="wdp-msg hoola">${md(S(r.text))}</div>`).join('')
        + (THREAD.waiting ? `<div class="wdp-msg hoola typing">${THREAD.live ? md(THREAD.live) : '<span class="wdp-dots" aria-label="Hoola is working"><i></i><i></i><i></i></span>'}</div>` : '')
      : `<div class="wdp-thread-empty"><p class="wdp-mut sm">Ask for anything on this website. It stays here, not in your home chat.</p>
          <div class="wdp-chips">${['Add a shop with cart', 'Add online payments', 'Add a Hindi version', 'Add booking slots'].map(t => `<button class="wdp-chip" type="button" data-wd-ask="${esc(t)}">${esc(t)}</button>`).join('')}</div></div>`;
    if (near || THREAD.waiting) box.scrollTop = box.scrollHeight;
  }

  async function readThread() {
    const c = THREAD.conv; if (!c) return;
    try {
      const r = await api('GET', `/api/conversations/${encodeURIComponent(c)}/messages?limit=60`);
      if (c !== THREAD.conv) return;                       // she moved to another site meanwhile
      THREAD.rows = L(r.messages);
    } catch { return; }
    if (THREAD.waiting) {
      let snap = null;
      try { const res = await api('GET', `/api/conversations/${encodeURIComponent(THREAD.conv)}/live`, undefined, {raw: true}); if (res.status === 200) snap = await res.json(); } catch {}
      THREAD.live = S(snap?.text);
      const answered = THREAD.rows.some(m => m.role === 'assistant' && Number(m.id) > THREAD.since && S(m.text).trim());
      if (answered && !snap) { THREAD.waiting = false; THREAD.live = ''; if (CUR) reloadQuiet(); }
      else if (Date.now() - THREAD.started > 15 * 60e3) THREAD.waiting = false;
    }
    drawMsgs();
    if (THREAD.waiting && live()) { clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 1500); }
  }

  async function ask(text) {
    text = S(text).trim(); if (!text || !CUR) return;
    if (TAB !== 'overview') { TAB = 'overview'; drawSite(); }
    const v = CUR;
    try {
      const c = await ensureConv();
      THREAD.since = Math.max(0, ...THREAD.rows.map(m => Number(m.id) || 0));
      THREAD.rows.push({id: 'local-' + Date.now(), role: 'user', text});
      THREAD.waiting = true; THREAD.started = Date.now(); THREAD.live = '';
      drawMsgs();
      await api('POST', `/api/conversations/${encodeURIComponent(c)}/messages`, {text,
        client_id: 'wdp-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8),
        hints: [`Web Development panel: this chat is only about website ${S(v.number)} "${name(v)}" (site id ${S(v.id)}). `
          + 'Work on THIS website with the website tool; never start a new website unless I ask for one.']});
      clearTimeout(THREAD.timer); THREAD.timer = setTimeout(readThread, 900);
    } catch (e) { THREAD.waiting = false; drawMsgs(); toast(e.message, true); }
  }

  async function reloadQuiet() {
    const id = CUR?.id; if (!id) return;
    try { const v = await api('GET', `/api/sites/${encodeURIComponent(id)}`); if (CUR?.id === id) { CUR = v; if (TAB === 'overview') drawFlow(); } } catch {}
  }

  /* ---------- Build / Edit / Code / Data / Integrations ---------- */
  const studioBtn = (tab, label, cls = 'pri', extra = '') => `<button class="wdp-btn ${cls}" type="button" data-wd-studio="${tab}" ${extra}>${esc(label)}</button>`;

  function build(box, v) {
    box.innerHTML = `<div class="wdp-split"><div class="wdp-main"><section class="wdp-card"><h4>Live preview and build board</h4>
        <p class="wdp-mut">The Website studio opens beside this page: preview on a computer and a phone, the board of pages and parts, every step and every check.</p>
        <div class="wdp-acts">${studioBtn('preview', 'Open the studio')}${studioBtn('board', 'Board', '')}${studioBtn('kadam', 'Steps', '')}${studioBtn('jaanch', 'Checks', '')}
        ${['building', 'checking'].includes(S(v.status)) ? '<button class="wdp-btn" type="button" data-wd-act="stop">Pause building</button>' : ''}</div></section>
      <section class="wdp-card"><h4>Change something</h4>${changeForm(v)}</section></div>
      <aside class="wdp-side"><section class="wdp-card"><h4>Grow it</h4><p class="wdp-mut">More pages, a big catalogue or a second language. Hoola plans it first.</p>
        <div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-ask="Is website mein aur pages jodo: ">More pages</button>
        <button class="wdp-btn" type="button" data-wd-ask="Is website ko 100 page wali badi website bana do">100-page site</button></div></section></aside></div>`;
  }

  function edit(box, v) {
    box.innerHTML = `<div class="wdp-stack"><section class="wdp-card"><h4>Visual edit</h4>
      <p class="wdp-mut">Click any words on the page and type; replace a photo, change a link, add a photo, video or file after any block, change the colours. No AI is used and every edit becomes a checked version with Undo.</p>
      ${hasVersion(v) ? `<div class="wdp-acts">${studioBtn('preview', 'Start editing', 'pri', 'data-wd-edit="1"')}${studioBtn('preview', 'Just look', '')}</div>` : '<p class="wdp-mut">Editing opens once the first version is built.</p>'}</section>
      <section class="wdp-card"><h4>Or ask Hoola to change a section</h4>${changeForm(v)}</section></div>`;
  }

  function code(box, v) {
    box.innerHTML = `<div class="wdp-stack"><section class="wdp-card"><h4>Your website's real code</h4>
      <p class="wdp-mut">Every section's HTML, CSS and script, and the design kit. Edit by hand or ask Hoola; every save is checked, becomes a new version, and Undo brings it back.</p>
      ${hasVersion(v) ? `<div class="wdp-acts">${studioBtn('code', 'Open the code')}</div>` : '<p class="wdp-mut">The code opens once the first version is built.</p>'}</section>
      <section class="wdp-card"><h4>Your code is yours</h4><p class="wdp-mut">Download the whole site, a React + Vite project, or put it in your own GitHub (that push waits for your tap).</p>
      ${hasVersion(v) ? `<div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-act="export" data-fmt="zip">Download ZIP</button>
        <button class="wdp-btn" type="button" data-wd-act="export" data-fmt="react">Export React + Vite</button>
        <button class="wdp-btn" type="button" data-wd-ask="Is website ka code mere GitHub par daalo">Push to my GitHub</button></div>` : ''}</section></div>`;
  }

  function data(box, v) {
    const lists = L(v.app);
    box.innerHTML = `<div class="wdp-split"><div class="wdp-main"><section class="wdp-card"><h4>Lists on this site</h4>
        ${lists.length ? `<div class="wdp-chips">${lists.map(c => `<span class="wdp-pill">${esc(S(c.label))}</span>`).join('')}</div>
          <div class="wdp-acts">${studioBtn('data', 'Open App & data')}</div>`
          : `<p class="wdp-mut">No lists yet. Orders, enquiries, members, bookings: ask for the ones you need.</p>
          <div class="wdp-acts"><button class="wdp-btn pri" type="button" data-wd-ask="Is website mein logins aur ek list jodo: ">Add lists and logins</button></div>`}</section>
        <section class="wdp-card"><h4>Import a catalogue</h4><p class="wdp-mut">A product sheet (Excel, CSV or Google Sheet) becomes catalogue pages. You see a preview first; nothing is written before your Apply.</p>
          <div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-ask="Is website mein meri sheet se catalogue banao: ">Catalogue from a sheet</button></div></section></div>
      <aside class="wdp-side"><section class="wdp-card"><h4>Rules that always hold</h4>
        <p class="wdp-li">Totals and prices are worked out by the server.</p><p class="wdp-li">Visitors see only their own rows.</p>
        <p class="wdp-li">Mobile + OTP logins, a staff two-step code, consent and "download / delete my data" are built in.</p></section></aside></div>`;
  }

  function integrations(box, v) {
    const langs = L(v.languages), built = hasVersion(v);
    const items = [['cart', 'Shop and cart', 'Prices and stock checked by the server, COD, pickup, coupons, GST invoices on your series.', 'shop', 'Is website mein shop chalu karo'],
      ['card', 'Online payments', 'UPI QR to your UPI ID, or your own Razorpay / Cashfree / PhonePe. Paid only when the gateway confirms.', '', 'Is website par online payment jodo'],
      ['cal', 'Booking slots', 'Real time slots with limits; you confirm each booking.', '', 'Is website mein booking slot lagao'],
      ['blog', 'Blog', 'Hoola drafts posts, you say Haan to publish. Categories, RSS, scheduled posts.', 'blog', 'Is website par blog chalu karo'],
      ['globe', 'Languages', `Now: ${langs.join(', ') || 'en'}. Up to 4 more Indian languages with a switch in the menu.`, 'langs', 'Is website mein Hindi version bhi jodo'],
      ['chat', 'Visitor chat', 'Visitors message your team from the site; your reply goes only on your tap.', '', 'Is website par visitor chat chalu karo'],
      ['pin', 'Map and directions', 'Loads only when the visitor taps, so the page stays fast.', '', 'Is website ke contact page par map lagao'],
      ['spark', 'Rich pieces', 'Quiz, configurator, comparison table, Lottie animation, 3D hero, scroll motion.', '', 'Is website mein ek quiz jodo: '],
      ['link', 'Your other apps', 'Send new orders to HubSpot, Slack or Google Sheets through your own account.', '', 'Is website ke naye orders meri Google Sheet mein bhejo']];
    box.innerHTML = `<p class="wdp-mut wdp-lead">Each one is asked in this website's own Hoola thread, so it is planned first. Money never moves without your tap.</p>
      <div class="wdp-ints">${items.map(([k, t, d, tab, q]) => `<section class="wdp-card wdp-int"><div class="wdp-int-head"><span class="wdp-ico">${ico(k)}</span><b>${esc(t)}</b></div>
        <p class="wdp-mut sm">${esc(d)}</p><div class="wdp-acts">
        ${tab && built ? studioBtn(tab, 'Manage', '') : ''}<button class="wdp-btn ${tab && built ? '' : 'pri'}" type="button" data-wd-ask="${esc(q)}">${tab && built ? 'Ask Hoola' : 'Add'}</button></div></section>`).join('')}</div>`;
  }

  /* ---------- Publish ---------- */
  async function publish(box, v) {
    box.innerHTML = '<div class="wdp-empty">Loading the addresses…</div>';
    let host = null, moves = null;
    try { host = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/hosting`); } catch (e) { host = {hosts: [], error: e.message}; }
    try { moves = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/moves`); } catch { moves = null; }      // 404 = no old site
    if (!CUR || CUR.id !== v.id || TAB !== 'publish') return;
    const hosts = L(host.hosts), versions = L(v.versions), rows = L(moves?.rows);
    box.innerHTML = `<div class="wdp-split"><div class="wdp-main">
      <section class="wdp-card accent"><div class="wdp-card-head"><h4>Put v${esc(S(v.version || '–'))} live</h4></div>
        ${hasVersion(v) ? `<p class="wdp-mut">Hoola checks the version and the addresses first and shows you what will happen. Nothing goes live until you tap.</p>
          <div class="wdp-acts"><button class="wdp-btn pri" type="button" data-wd-act="launch">Check and go live…</button></div><div id="wdLaunch"></div>`
          : '<p class="wdp-mut">There is nothing to put live yet: the first version is still being made.</p>'}</section>
      ${moves ? `<section class="wdp-card"><div class="wdp-card-head"><h4>Old site addresses</h4>${pill(moves.approved ? 'Approved' : `${rows.length} found · waiting for your Haan`, moves.approved ? 'ok' : 'warn')}</div>
        <p class="wdp-mut">Links and Google results from your old site (${esc(S(moves.from_host))}) open the matching new page (301). Untick any you don't want.</p>
        <form data-wd-form="moves" data-hash="${esc(S(moves.hash))}">${rows.slice(0, 200).map(r => `<label class="wdp-mv"><input type="checkbox" name="keep" value="${esc(S(r.old))}" ${r.guess ? '' : 'checked'}>
          <code>${esc(S(r.old))}</code><span aria-hidden="true">→</span><code>${esc(S(r.new))}</code>${pill(S(r.how), r.guess ? 'warn' : '')}</label>`).join('') || '<p class="wdp-mut">Every old address already exists on the new site.</p>'}
          ${rows.length ? `<div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-act="compare">Compare old vs new</button><span class="sp"></span><button class="wdp-btn pri" type="submit">Haan, jod do</button></div>` : ''}</form><div id="wdCompare"></div></section>` : ''}
    </div><aside class="wdp-side">
      <section class="wdp-card"><h4>Addresses</h4>${host.error ? `<p class="wdp-mut">${esc(host.error)}</p>` : ''}
        ${hosts.length ? hosts.map(h => `<div class="wdp-kv"><code>${esc(S(h.host))}</code>${pill(S(h.stage) || S(h.status), S(h.stage) === 'Live' ? 'ok' : S(h.stage) === 'Offline' ? 'bad' : 'warn')}</div>
          ${h.problem ? `<p class="wdp-li bad">${esc(S(h.problem))}</p>` : ''}`).join('') : '<p class="wdp-mut">Not live yet. Your free address is made when you first go live.</p>'}</section>
      <section class="wdp-card"><h4>Connect your domain</h4><p class="wdp-mut sm">Hoola gives you the exact records to add, checks them from three places, then sets up HTTPS.</p>
        <form data-wd-form="domain" class="wdp-inline"><input id="wdDom" aria-label="Your domain" placeholder="yourname.in" autocomplete="off"><button class="wdp-btn" type="submit">Connect</button></form>
        <div class="wdp-acts"><button class="wdp-btn ghost" type="button" data-wd-ask="Is website ke liye achha domain dhoondho">Find a domain to buy</button></div></section>
      <section class="wdp-card"><h4>Versions</h4>${versions.length ? versions.slice(0, 8).map(x => `<div class="wdp-kv"><span class="wdp-kv-l">${pill('v' + S(x.version), Number(x.version) === Number(v.version) ? 'ok' : '')}<span class="wdp-ell">${esc(S(x.note).slice(0, 60))}</span></span>
          ${Number(x.version) !== Number(v.version) && hosts.length ? `<button class="wdp-btn sm" type="button" data-wd-act="rollback" data-ver="${esc(S(x.version))}">Roll back…</button>` : ''}</div>`).join('') : '<p class="wdp-mut">No versions yet.</p>'}</section>
    </aside></div>`;
  }

  async function launch() {
    const out = EL.querySelector('#wdLaunch');
    try {
      const card = await api('POST', `/api/sites/${sid()}/launch-request`, {});
      const blk = L(card.blockers);
      out.innerHTML = `<div class="wdp-launch"><p>${esc(S(card.say))}</p>
        ${blk.length ? blk.map(b => `<p class="wdp-li bad">${esc(S(b))}</p>`).join('') : `<div class="wdp-chips">${L(card.hosts).map(h => `<code>${esc(S(h))}</code>`).join(' ')}</div>
        <div class="wdp-acts end"><button class="wdp-btn pri" type="button" data-wd-act="golive" data-hash="${esc(S(card.hash))}">Haan, live karo</button></div>`}</div>`;
    } catch (e) { out.innerHTML = `<p class="wdp-li bad">${esc(e.message)}</p>`; }
  }

  /* ---------- Health ---------- */
  async function health(box, v) {
    if (!hasVersion(v)) { box.innerHTML = '<section class="wdp-card"><p class="wdp-mut">Health shows up once the website is built and live.</p></section>'; return; }
    box.innerHTML = '<div class="wdp-empty">Reading visits, speed and backups…</div>';
    let care = null, ops = null;
    try { care = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/care?days=30`); } catch (e) { care = {error: e.message}; }
    try { ops = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/ops?days=30`); } catch (e) { ops = {error: e.message}; }
    if (!CUR || CUR.id !== v.id || TAB !== 'health') return;
    const chk = M(v.checks), sp = M(care.speed || ops.speed), bk = M(ops.backup), rt = M(bk.restore_test);
    const band = g => g === 'good' ? 'ok' : g === 'poor' ? 'bad' : 'warn';
    const speedRow = (k, label) => sp[k] ? `<div class="wdp-kv"><span>${esc(label)}</span>${pill(`${S(sp[k].p75)} · ${S(sp[k].grade)}`, band(S(sp[k].grade)))}</div>` : '';
    box.innerHTML = `<div class="wdp-stack">${care.say ? `<section class="wdp-card accent"><p class="wdp-say">${esc(S(care.say))}</p>${L(care.tips).map(t => `<p class="wdp-li">${esc(S(t))}</p>`).join('')}</section>` : ''}
      <div class="wdp-grid2">
      <section class="wdp-card"><h4>Visitors and results (30 days)</h4><p class="wdp-mut sm">No cookies, no trackers: pages counted per day only.</p>
        ${care.error ? `<p class="wdp-mut">${esc(care.error)}</p>` : `
        <div class="wdp-kv"><span>Page visits</span><b>${esc(S(care.views ?? '–'))}</b></div>
        <div class="wdp-kv"><span>Enquiries</span><b>${esc(S(care.leads ?? '–'))}${care.views ? ` (${esc(S(care.conversion_pct))}%)` : ''}</b></div>
        <div class="wdp-kv"><span>Uptime</span><b>${care.uptime_pct == null ? 'not measured yet' : esc(S(care.uptime_pct)) + '%'}</b></div>
        ${Object.entries(M(care.ssl_days)).map(([h, d]) => `<div class="wdp-kv"><span class="wdp-ell">HTTPS · <code>${esc(S(h))}</code></span><b>${d == null ? '–' : esc(S(d)) + ' days left'}</b></div>`).join('')}
        ${L(care.top_pages).slice(0, 4).map(p => `<div class="wdp-kv"><code class="wdp-ell">${esc(S(L(p)[0]))}</code><span>${esc(S(L(p)[1]))}</span></div>`).join('')}`}</section>
      <section class="wdp-card"><h4>Speed on real phones</h4><p class="wdp-mut sm">Measured in your visitors' browsers, shown as bands (p75).</p>
        ${speedRow('lcp', 'Main picture shows') + speedRow('fcp', 'First paint') + speedRow('cls', 'Layout shift') + speedRow('ttfb', 'Server answer') || '<p class="wdp-mut">No real visits measured yet.</p>'}</section>
      <section class="wdp-card"><h4>Checks before going live</h4>
        ${chk.passed == null ? '<p class="wdp-mut">Not run yet.</p>' : `<div class="wdp-kv"><span>Blocking checks</span>${pill(chk.passed ? 'Passed' : L(chk.blocking).length + ' to fix', chk.passed ? 'ok' : 'bad')}</div>
        <div class="wdp-kv"><span>Notes (incl. the "looks AI-made" check)</span>${pill(String(L(chk.warnings).length), L(chk.warnings).length ? 'warn' : 'ok')}</div>
        <div class="wdp-kv"><span>Test visitor walks</span>${pill(String(L(chk.journeys).length), '')}</div>`}
        <div class="wdp-acts">${studioBtn('jaanch', 'Open all checks', '')}</div></section>
      <section class="wdp-card"><h4>Errors and backups</h4>${ops.error ? `<p class="wdp-mut">${esc(ops.error)}</p>` : `
        <div class="wdp-kv"><span>Visitor page errors</span>${pill(Number(ops.errors) ? String(ops.errors) : 'None', Number(ops.errors) ? 'warn' : 'ok')}</div>
        <div class="wdp-kv"><span>Backups</span>${pill(bk.enabled ? (bk.last_day ? 'Last ' + S(bk.last_day) : 'On') : 'Off', bk.enabled ? 'ok' : 'warn')}</div>
        <div class="wdp-kv"><span>Restore test</span>${rt.day ? pill(rt.ok ? 'Matched · ' + S(rt.day) : 'Did not match · ' + S(rt.day), rt.ok ? 'ok' : 'bad') : pill('Not run yet', '')}</div>`}</section></div></div>`;
  }

  /* ---------- Settings ---------- */
  function settings(box, v) {
    const f = M(v.facts);
    const fields = [['name', 'Business name'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'], ['hours', 'Opening hours'], ['address', 'Address'], ['city', 'City'], ['instagram', 'Instagram']];
    box.innerHTML = `<div class="wdp-split"><div class="wdp-main">
      <form class="wdp-card" data-wd-form="facts"><h4>Business details</h4><p class="wdp-mut sm">Used on every page. A change here is used in the next version; ask for a change to rebuild now.</p>
        <div class="wdp-grid2 tight">${fields.map(([k, l]) => `<label class="wdp-fld"><span>${esc(l)}</span><input name="${k}" value="${esc(S(f[k]))}" autocomplete="off"></label>`).join('')}</div>
        <div class="wdp-acts end"><button class="wdp-btn pri" type="submit">Save details</button></div></form>
      <section class="wdp-card"><h4>SEO and Google</h4><p class="wdp-mut">Page titles, descriptions, sitemap and Search Console are set by Hoola on every build. For a monthly audit and keyword plan, hire the SEO employee.</p>
        <div class="wdp-acts"><button class="wdp-btn" type="button" data-v="hire">AI Employees</button><button class="wdp-btn" type="button" data-wd-ask="Is website ka SEO check karo">Check SEO now</button></div></section>
    </div><aside class="wdp-side">
      <section class="wdp-card"><h4>Team</h4><p class="wdp-mut">Writers draft, editors review, publishers put live.</p>
        <div class="wdp-acts"><button class="wdp-btn" type="button" data-wd-ask="Is website ke CMS mein ek team member jodo: ">Invite a team member</button></div></section>
      <section class="wdp-card danger"><h4>Take the site down</h4><p class="wdp-mut">The site stops answering; your pages, data and versions are kept.</p>
        <div class="wdp-acts"><button class="wdp-btn danger-ghost" type="button" data-wd-act="takedown">Take down…</button></div></section>
    </aside></div>`;
  }

  /* ================= events ================= */
  function onKey(e) {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    const t = e.target;
    if (t.matches?.('#wdAsk, #wdpTh')) { e.preventDefault(); t.form?.requestSubmit(); }
  }

  function onChange(e) {
    const f = e.target.closest?.('form[data-wd-form=shot]');
    if (f && e.target.type === 'file') f.querySelector('.wdp-src-out').innerHTML = '';
  }

  async function onClick(e) {
    const b = e.target.closest('button, a'); if (!b || !EL.contains(b)) return;
    const d = b.dataset;
    if (d.wdTab) { TAB = d.wdTab; draw(); return; }
    if (d.wdDev) { DEVICE = d.wdDev; drawFlow(); return; }
    if (d.wdStudio) { if (!studio) return toast('The Website studio is not available here.', true); studio(CUR, d.wdStudio, d.wdEdit === '1'); return; }
    if (d.wdAsk != null && d.wdAsk !== '') {
      if (d.wdAsk.endsWith(': ')) { if (TAB !== 'overview') { TAB = 'overview'; drawSite(); } const t = EL.querySelector('#wdpTh'); if (t) { t.value = d.wdAsk; t.focus(); } return; }
      ask(d.wdAsk); return;
    }
    if (d.wdStart != null) {
      const t = EL.querySelector('#wdAsk');
      if (d.wdStart === 'focus') { drawSource(''); t?.focus(); }
      else { drawSource(d.wdStart); EL.querySelector('#wdpSource input')?.focus(); EL.querySelector('#wdpSource')?.scrollIntoView({block: 'nearest', behavior: 'smooth'}); }
      return;
    }
    if (d.wdType) { const t = EL.querySelector('#wdAsk'); if (t) { t.value = `${d.wdType} ki website banao: `; t.focus(); t.setSelectionRange(t.value.length, t.value.length); } return; }
    if (BUSY) return;
    if (d.wdSite) { BUSY = true; try { if (await loadSite(d.wdSite)) { TAB = 'overview'; draw(); } } finally { BUSY = false; } return; }
    const act = d.wdAct; if (!act) return;
    const id = sid();
    BUSY = true; b.disabled = true;
    try {
      if (act === 'home') { stopPoll(); CUR = null; TAB = 'overview'; await loadSites(); draw(); }
      else if (act === 'refresh') { await loadSites(); draw(); }
      else if (act === 'resume') { await api('POST', `/api/sites/${id}/resume`, {}); toast('Building again.'); await reload(); }
      else if (act === 'stop') { await api('POST', `/api/sites/${id}/stop`, {}); toast('Pausing after the current part.'); await reload(); }
      else if (act === 'look') {
        await api('POST', `/api/sites/${id}/look`, {index: Number(d.i) || 0, conversation_id: await ensureConv().catch(() => '')});
        toast('Building your website in this look.'); await reload();
      } else if (act === 'delete') {
        if (!confirm(`Delete ${name(CUR)}? Nothing has been built yet.`)) return;
        await api('DELETE', `/api/sites/${id}`); toast('Deleted.'); CUR = null; await loadSites(); draw();
      } else if (act === 'export') { const r = await api('POST', `/api/sites/${id}/export`, {format: d.fmt}); toast(S(r.say) || 'Ready: it is in your files.'); }
      else if (act === 'launch') await launch();
      else if (act === 'golive') {
        if (!confirm(`Put ${name(CUR)} v${S(CUR.version)} live now?`)) return;
        const r = await api('POST', `/api/sites/${id}/launch`, {hash: d.hash}); toast(S(r.say) || 'Live.'); await reload();
      } else if (act === 'rollback') {
        const card = await api('POST', `/api/sites/${id}/rollback-request`, {version: Number(d.ver)});
        if (!confirm(S(card.say) || `Bring back v${d.ver} on your live addresses?`)) return;
        const r = await api('POST', `/api/sites/${id}/rollback`, {version: Number(d.ver), hash: S(card.hash)}); toast(S(r.say) || 'Rolled back.'); await reload();
      } else if (act === 'takedown') {
        if (!confirm(`Take ${name(CUR)} off the internet? Your pages, data and versions are kept.`)) return;
        const r = await api('POST', `/api/sites/${id}/takedown`, {}); toast(S(r.say) || 'Taken down.'); await reload();
      } else if (act === 'compare') {
        const out = EL.querySelector('#wdCompare'); out.innerHTML = '<div class="wdp-empty">Opening both pages…</div>';
        const r = await api('POST', `/api/sites/${id}/compare-old`, {old: '/'});
        out.innerHTML = `<div class="wdp-launch"><p>${esc(S(r.say))}</p>${L(r.differences).map(x => `<p class="wdp-li">${esc(S(x))}</p>`).join('')}${r.note ? `<p class="wdp-mut sm">${esc(S(r.note))}</p>` : ''}</div>`;
      } else if (act === 'use-design') {
        const brief = S(EL.querySelector('#wdAsk')?.value).trim();
        const r = await api('POST', '/api/site-design/use', {token: d.token, keep: d.keep === '1', brief});
        toast(S(r.say).slice(0, 160) || 'Design added.');
        if (r.site && await loadSite(r.site)) {
          try { CUR && await ensureConv(); } catch {}            // its own thread; the plan / look taps hand it to the server
          TAB = 'overview'; draw();
        }
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (b.isConnected) b.disabled = false; }
  }

  async function reload() { if (CUR && await loadSite(CUR.id)) draw(); }

  async function readDesign(f, kind) {
    const out = f.querySelector('.wdp-src-out');
    out.innerHTML = '<div class="wdp-empty sm">Reading…</div>';
    let res;
    if (kind === 'old') {
      const url = S(f.url.value).trim(); if (!url) { out.innerHTML = ''; return toast('Write the address first.', true); }
      res = await api('POST', '/api/site-design/read', {source: 'site', url}, {raw: true}).then(async r => ({ok: true, data: await r.json()}))
        .catch(e => { let x = {}; try { x = JSON.parse(e.message); } catch {} return {ok: false, status: e.status, data: x, msg: S(x.detail || x.error) || e.message}; });
    } else {
      const file = f.file.files?.[0]; if (!file) { out.innerHTML = ''; return toast('Choose a picture first.', true); }
      const fd = new FormData(); fd.append('file', file);
      res = await api('POST', '/api/site-design/read', undefined, {form: fd}).then(data => ({ok: true, data})).catch(e => ({ok: false, msg: e.message}));
    }
    if (!res.ok) {
      const p = M(res.data?.proof);
      out.innerHTML = p.txt_value ? `<div class="wdp-launch"><p><b>First show the site is yours.</b> Add one of these, then press Read my site again:</p>
          <div class="wdp-kv"><span>DNS TXT record</span><code class="wdp-ell">${esc(S(p.txt_name))} = ${esc(S(p.txt_value))}</code></div>
          <div class="wdp-kv"><span>Or in the home page &lt;head&gt;</span><code class="wdp-ell">${esc(S(p.meta))}</code></div></div>`
        : `<p class="wdp-li bad">${esc(res.msg || 'Could not read it.')}</p>`;
      return;
    }
    const r = res.data;
    out.innerHTML = `<div class="wdp-launch"><p>${esc(S(r.say))}</p>
      ${kind === 'shot' ? '<p class="wdp-mut sm">Write one line about the website in the box above first (what it is for); then use the design.</p>' : ''}
      <div class="wdp-acts end">${kind === 'old' ? `<button class="wdp-btn" type="button" data-wd-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">New layout, my content</button>
        <button class="wdp-btn pri" type="button" data-wd-act="use-design" data-token="${esc(S(r.token))}" data-keep="1">Keep my pages and order</button>`
        : `<button class="wdp-btn pri" type="button" data-wd-act="use-design" data-token="${esc(S(r.token))}" data-keep="0">Use this design</button>`}</div></div>`;
  }

  async function onSubmit(e) {
    const f = e.target.closest('form[data-wd-form]'); if (!f || !EL.contains(f)) return;
    e.preventDefault();
    const kind = f.dataset.wdForm;
    if (kind === 'thread') { const t = f.querySelector('textarea'); const x = S(t.value).trim(); if (!x) return; t.value = ''; return ask(x); }
    if (BUSY) return;
    const id = sid(), btn = f.querySelector('[type=submit]');
    BUSY = true; if (btn) btn.disabled = true;
    try {
      if (kind === 'ask') {
        const t = S(f.querySelector('textarea').value).trim(); if (!t) return toast('Write one line about the website.', true);
        if (btn) btn.classList.add('busy');
        // its own thread FIRST and handed to the server: the site's cards and step lines go there. (A site made with no
        // conversation publishes to her HOME chat - that was the "it lands on the home page chat" leak.)
        const conv = S((await api('POST', '/api/conversations')).id);
        let v;
        try { v = await api('POST', '/api/sites', {brief: t, conversation_id: conv}); }
        catch (er) { api('DELETE', `/api/conversations/${encodeURIComponent(conv)}`).catch(() => {}); throw er; }
        if (v.id) {
          store.set(convKey(v.id), conv);
          api('PATCH', `/api/conversations/${encodeURIComponent(conv)}`, {title: `Website · ${name(v)}`}).catch(() => {});
          await loadSite(v.id); TAB = 'overview'; draw();
        }
      } else if (kind === 'old' || kind === 'shot') await readDesign(f, kind);
      else if (kind === 'plan') {
        const answers = {};
        f.querySelectorAll('input[data-q]').forEach(x => { const val = S(x.value).trim(); if (val) answers[x.dataset.q] = val; });
        if (Object.keys(answers).length) await api('POST', `/api/sites/${id}/answers`, {answers});
        const pages = [...f.querySelectorAll('input[name=page]')].filter(x => x.checked || x.disabled).map(x => x.value);
        await api('POST', `/api/sites/${id}/plan`, {pages, conversation_id: await ensureConv().catch(() => '')});
        toast('Making three looks for you.'); await reload();
      } else if (kind === 'change') {
        const t = S(f.querySelector('textarea').value).trim(); if (!t) return toast('Write the change first.', true);
        const r = await api('POST', `/api/sites/${id}/change`, {instruction: t}); toast(S(r.say) || 'Change started.'); f.reset(); await reload();
      } else if (kind === 'facts') {
        const answers = {}; new FormData(f).forEach((val, key) => { const x = S(val).trim(); if (x && x !== S(M(CUR.facts)[key])) answers[key] = x; });
        if (!Object.keys(answers).length) return toast('Nothing changed.');
        await api('POST', `/api/sites/${id}/answers`, {answers}); toast('Details saved.'); await reload();
      } else if (kind === 'domain') {
        const dom = S(f.querySelector('input').value).trim(); if (!dom) return toast('Write the domain first.', true);
        const r = await api('POST', `/api/sites/${id}/domain`, {domain: dom}); toast(S(r.say) || 'Domain added: follow the records shown.'); await reload();
      } else if (kind === 'moves') {
        const keep = new Set([...f.querySelectorAll('input[name=keep]:checked')].map(x => x.value));
        const drop = [...f.querySelectorAll('input[name=keep]')].map(x => x.value).filter(x => !keep.has(x));
        if (!confirm(`Send ${keep.size} old address(es) to their new pages?`)) return;
        const r = await api('POST', `/api/sites/${id}/moves`, {hash: f.dataset.hash, drop}); toast(S(r.say) || 'Saved.'); await reload();
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (btn?.isConnected) { btn.disabled = false; btn.classList.remove('busy'); } }
  }

  return {open, draw, reset() { stopPoll(); CUR = null; SITES = []; TAB = 'overview'; }};
};
