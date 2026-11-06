/* v0.635 WEB DEVELOPMENT PANEL (console) - one place for every website she builds, the owner-approved prototype
   ("PERFECT", 6 Nov 2026) made real. Home (ask box, four ways to start, her sites, business types) and, per site, nine
   tabs: Overview, Build, Edit, Code, Data, Integrations, Publish, Health, Settings.

   Rules this page keeps (they are the server's rules, drawn):
   - Build / Edit / Code / Data / Shop / Blog / Languages OPEN THE EXISTING WEBSITE STUDIO (build.js) on that tab - one
     editor, one preview, one code mode; this page never re-implements them;
   - going live, rolling back, taking down and the old-address redirects are HER taps: each asks `confirm()` first and sends
     the hash the server gave (a changed list or version is refused by the server, never forced);
   - a new website, a payment link, a domain purchase and every integration start as her words in chat (`say`), so the
     agent's plan card and its rules apply exactly as on the phone;
   - every value from the server goes through esc() - a site name, a page title or a tip is data, never markup. */
'use strict';
window.HoolaWebDev = function ({api, esc, toast, say, studio}) {
  let EL = null, SITES = [], CUR = null, TAB = 'overview', BUSY = false;
  const S = v => v == null ? '' : String(v);
  const L = v => Array.isArray(v) ? v : [];
  const M = v => v && typeof v === 'object' ? v : {};
  const TABS = [['overview', 'Overview'], ['build', 'Build'], ['edit', 'Edit'], ['code', 'Code'], ['data', 'Data & logins'],
    ['integrations', 'Integrations'], ['publish', 'Publish'], ['health', 'Health'], ['settings', 'Settings']];
  const STATUS = {draft: ['Starting', ''], planned: ['Plan: needs your Haan', 'warn'], looks: ['Pick a look', 'warn'],
    building: ['Building', 'v'], checking: ['Checking', 'v'], ready: ['Ready', 'ok'], failed: ['Problem', 'bad'], stopped: ['Stopped', '']};
  const pill = (t, c) => `<span class="wd-pill ${c || ''}">${esc(t)}</span>`;
  const ICON = {
    chat: '<path d="M4 5h16v11H8l-4 4z"/>', move: '<path d="M4 12a8 8 0 0 1 14-5M20 12a8 8 0 0 1-14 5M18 3v4h-4M6 21v-4h4"/>',
    pic: '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M3 15l5-5 4 4 3-3 6 6"/>', sheet: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    cart: '<path d="M4 6h2l2 10h10l2-7H8"/><circle cx="10" cy="20" r="1.4"/><circle cx="17" cy="20" r="1.4"/>', card: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>', blog: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 11h8M8 15h6"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>', pin: '<path d="M12 21s-7-6-7-12a7 7 0 0 1 14 0c0 6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    spark: '<path d="M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'};
  const ico = k => `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] || ''}</svg>`;
  const statusPill = v => { const [t, c] = STATUS[S(v.status)] || [S(v.status) || '…', '']; return pill(t + (v.version ? ` · v${v.version}` : ''), c); };
  const name = v => S(v.name) || S(v.field_label) || 'Website';
  const TYPES = ['Sweet shop', 'Restaurant menu', 'Salon booking', 'Clinic', 'School admissions', 'Coaching classes', 'Online shop',
    'Portfolio', 'Event / wedding', 'NGO / cause', 'Real estate', 'Personal page'];

  async function loadSites() {
    try { SITES = L((await api('GET', '/api/sites')).sites); } catch (e) { SITES = []; toast(e.message, true); }
  }
  async function loadSite(id) {
    try { CUR = await api('GET', `/api/sites/${encodeURIComponent(id)}`); return true; }
    catch (e) { toast(e.message, true); CUR = null; return false; }
  }

  async function open(el, arg) {
    EL = el;
    if (!EL.dataset.wdBound) { EL.dataset.wdBound = '1'; EL.addEventListener('click', onClick); EL.addEventListener('submit', onSubmit); }
    if (arg) { if (await loadSite(arg)) { TAB = 'overview'; return draw(); } }
    if (!CUR) { EL.innerHTML = `<div class="vh"><h2>Web Development</h2></div><div class="empty">Loading…</div>`; await loadSites(); }
    draw();
  }

  function draw() { if (!EL) return; if (CUR) drawSite(); else drawHome(); }

  /* ---------------- home ---------------- */
  function drawHome() {
    const start = [['chat', 'Describe it', 'One line here, in chat or on a voice call.', 'focus'],
      ['move', 'Move my old site', 'Your own site only, after a quick ownership check. Old addresses keep working.', 'Meri purani website ka address hai: [address]. Usi se nayi website banao, pages aur sections ka kram purana jaisa rakho.'],
      ['pic', 'Screenshot or Figma', 'Colours and style are measured; no words or logos are taken.', 'Main ek screenshot bhej rahi hoon - is design ke rang aur andaaz se meri website banao.'],
      ['sheet', 'A product sheet', 'Excel, CSV or Google Sheet becomes a catalogue, previewed first.', 'Meri product sheet se website ka catalogue banao: [Google Sheet link ya file].']];
    const sites = SITES.length ? `<div class="wd-grid3">${SITES.map(v => `<button class="wd-site" type="button" data-wd-site="${esc(S(v.id))}">
        <span class="wd-thumb" aria-hidden="true"><i></i><i></i><i></i><b></b></span>
        <span class="wd-row"><b>${esc(name(v))}</b>${statusPill(v)}</span>
        <span class="wd-mut">${esc(S(v.number))}${v.field_label ? ' · ' + esc(S(v.field_label)) : ''}${v.goal_label ? ' · ' + esc(S(v.goal_label)) : ''}</span></button>`).join('')}</div>`
      : `<div class="wd-card wd-mut">No website yet. Write one line above, or ask Hoola in chat.</div>`;
    EL.innerHTML = `<div class="wd">
      <div class="wd-top"><h2>Web Development</h2><span class="wd-mut">Plan first, nothing is built before your Haan, nothing goes live before your tap.</span></div>
      <section class="wd-hero"><h3>What should we build today?</h3>
        <p class="wd-mut">Describe it in your own words. Hoola plans the pages, shows you three looks, builds and checks every page, and puts it live only when you tap.</p>
        <form class="wd-card wd-ask" data-wd-form="ask"><label for="wdAsk" class="wd-lbl">Your website in one line</label>
          <textarea id="wdAsk" rows="3" placeholder="e.g. Sharma Sweets, Akola ki mithai dukaan ki website banao - menu, Diwali orders aur WhatsApp button"></textarea>
          <div class="wd-row wrap"><span class="wd-mut sm">Hoola asks only what is missing; anything you don't know stays blank, never made up.</span><span class="sp"></span>
          <button class="btn go" type="submit">Plan my website</button></div></form></section>
      <section><h4>Or start from</h4><div class="wd-grid4">${start.map(([k, t, d, ask]) => `<button class="wd-start" type="button" data-wd-start="${esc(ask)}"><span class="wd-ico">${ico(k)}</span><b>${esc(t)}</b><span class="wd-mut sm">${esc(d)}</span></button>`).join('')}</div></section>
      <section><div class="wd-row"><h4>Your websites</h4><span class="sp"></span><button class="btn soft" type="button" data-wd-act="refresh">Refresh</button></div>${sites}</section>
      <section><h4>Start with a business type</h4><div class="wd-chips">${TYPES.map(t => `<button class="wd-chip" type="button" data-wd-type="${esc(t)}">${esc(t)}</button>`).join('')}</div></section>
    </div>`;
  }

  /* ---------------- one site ---------------- */
  function drawSite() {
    const v = CUR;
    EL.innerHTML = `<div class="wd">
      <div class="wd-top"><button class="btn soft" type="button" data-wd-act="home" aria-label="Back to all websites">← Web Development</button>
        <h2>${esc(name(v))}</h2>${statusPill(v)}<span class="sp"></span>
        ${v.preview ? `<a class="btn soft" href="${esc(S(v.preview))}" target="_blank" rel="noopener">Open preview</a>` : ''}
        <button class="btn go" type="button" data-wd-tab="publish">Publish</button></div>
      <nav class="wd-tabs" aria-label="Website sections">${TABS.map(([k, n]) => `<button type="button" data-wd-tab="${k}" aria-current="${k === TAB ? 'page' : 'false'}">${esc(n)}</button>`).join('')}</nav>
      <div class="wd-body" id="wdBody"><div class="empty">Loading…</div></div></div>`;
    const body = EL.querySelector('#wdBody');
    ({overview, build, edit, code, data, integrations, publish, health, settings})[TAB](body, v);
  }

  const studioBtn = (tab, label, cls = 'go', extra = '') => `<button class="btn ${cls}" type="button" data-wd-studio="${tab}" ${extra}>${esc(label)}</button>`;
  const hasVersion = v => !!Number(v.version);

  function overview(box, v) {
    const pages = L(M(v.plan).pages), chk = M(v.checks);
    const next = {planned: ['Approve the plan', 'plan'], looks: ['Pick one of the three looks', 'looks'], ready: ['Put it live', 'publish'],
      failed: ['See what went wrong', 'kadam'], stopped: ['Continue building', 'resume']}[S(v.status)];
    box.innerHTML = `<div class="wd-split"><div class="wd-col">
        <section class="wd-card"><p class="wd-say">${esc(S(v.say))}</p>
          ${next ? `<div class="wd-row wrap">${next[1] === 'publish' ? `<button class="btn go" type="button" data-wd-tab="publish">${esc(next[0])}</button>`
            : next[1] === 'resume' ? `<button class="btn go" type="button" data-wd-act="resume">${esc(next[0])}</button>` : studioBtn(next[1], next[0])}</div>` : ''}</section>
        <section class="wd-card"><h4>Pages${pages.length ? ` (${pages.length})` : ''}</h4>
          ${pages.length ? `<div class="wd-chips">${pages.map(p => `<span class="wd-pill">${esc(S(p.title))}</span>`).join('')}</div>` : '<p class="wd-mut">The plan appears here once Hoola has written it.</p>'}</section>
        <section class="wd-card"><h4>Checks</h4>${chk.passed == null ? '<p class="wd-mut">Checks run after the website is built.</p>'
          : `<div class="wd-chips">${pill(chk.passed ? 'All blocking checks passed' : `${L(chk.blocking).length} must be fixed`, chk.passed ? 'ok' : 'bad')}${L(chk.warnings).length ? pill(`${L(chk.warnings).length} notes`, 'warn') : ''}${L(chk.journeys).length ? pill(`Test visitor: ${L(chk.journeys).length} walks`, '') : ''}</div>
            ${L(chk.blocking).slice(0, 5).map(x => `<p class="wd-li bad">${esc(S(M(x).text || x))}</p>`).join('')}`}</section></div>
      <div class="wd-col narrow"><section class="wd-card"><h4>About this website</h4>
          ${[['Number', v.number], ['Business', v.field_label], ['Goal', v.goal_label], ['Look', v.style_label], ['Languages', L(v.languages).join(', ')], ['Enquiries', v.leads]]
            .filter(x => S(x[1])).map(([k, val]) => `<div class="wd-kv"><span>${esc(k)}</span><b>${esc(S(val))}</b></div>`).join('')}</section>
        <section class="wd-card"><h4>Ask for a change</h4>${changeForm(v)}</section></div></div>`;
  }

  const changeForm = v => hasVersion(v) || ['building', 'checking'].includes(S(v.status))
    ? `<form data-wd-form="change"><label for="wdChg" class="wd-lbl">In your own words</label><textarea id="wdChg" rows="3" placeholder="e.g. Hero mein Diwali offer daalo, 10% off on gift boxes"></textarea>
       <div class="wd-row"><span class="wd-mut sm">Only the parts it touches are rewritten; anything that goes missing is named.</span><span class="sp"></span><button class="btn go" type="submit">Send</button></div></form>`
    : '<p class="wd-mut">Changes open once the first version is built.</p>';

  function build(box, v) {
    box.innerHTML = `<div class="wd-split"><div class="wd-col"><section class="wd-card"><h4>Live preview and build board</h4>
        <p class="wd-mut">The Website studio opens beside this page: preview on a computer and a phone, the board of pages and parts, every step and every check.</p>
        <div class="wd-row wrap">${studioBtn('preview', 'Open live preview')}${studioBtn('board', 'Board', 'soft')}${studioBtn('kadam', 'Steps', 'soft')}${studioBtn('jaanch', 'Checks', 'soft')}
        ${['building', 'checking'].includes(S(v.status)) ? '<button class="btn soft" type="button" data-wd-act="stop">Stop building</button>' : ''}</div></section>
      <section class="wd-card"><h4>Ask for a change</h4>${changeForm(v)}</section></div>
      <div class="wd-col narrow"><section class="wd-card"><h4>Grow it</h4><p class="wd-mut">More pages, a big catalogue or a second language: say it and Hoola plans it first.</p>
        <div class="wd-row wrap"><button class="btn soft" type="button" data-wd-say="${esc(name(v))} website mein aur pages jodo: ">More pages</button>
        <button class="btn soft" type="button" data-wd-say="${esc(name(v))} website ko 100 page wali badi website bana do">100-page site</button></div></section></div></div>`;
  }

  function edit(box, v) {
    box.innerHTML = `<section class="wd-card"><h4>Visual edit</h4>
      <p class="wd-mut">Click any words on the page and type; replace a photo, change a link, add a photo / video / file after any block, change the site colours. No AI is used and every edit becomes a checked version with Undo.</p>
      ${hasVersion(v) ? `<div class="wd-row wrap">${studioBtn('preview', 'Start editing', 'go', 'data-wd-edit="1"')}${studioBtn('preview', 'Just look', 'soft')}</div>` : '<p class="wd-mut">Editing opens once the first version is built.</p>'}</section>
      <section class="wd-card"><h4>Or ask Hoola to change a section</h4>${changeForm(v)}</section>`;
  }

  function code(box, v) {
    box.innerHTML = `<section class="wd-card"><h4>Your website's real code</h4>
      <p class="wd-mut">Every section's HTML, CSS and script, and the design kit. Edit by hand or ask Hoola; every save is checked for safety, becomes a new version, and Undo brings it back.</p>
      ${hasVersion(v) ? `<div class="wd-row wrap">${studioBtn('code', 'Open the code')}</div>` : '<p class="wd-mut">The code opens once the first version is built.</p>'}</section>
      <section class="wd-card"><h4>Your code is yours</h4><p class="wd-mut">Download the whole site, a React + Vite project, or put it in your own GitHub (that push waits for your tap).</p>
      ${hasVersion(v) ? `<div class="wd-row wrap"><button class="btn soft" type="button" data-wd-act="export" data-fmt="zip">Download ZIP</button>
        <button class="btn soft" type="button" data-wd-act="export" data-fmt="react">Export React + Vite</button>
        <button class="btn soft" type="button" data-wd-say="${esc(name(v))} website ka code mere GitHub par daalo">Push to my GitHub</button></div>` : ''}</section>`;
  }

  function data(box, v) {
    const lists = L(v.app);
    box.innerHTML = `<div class="wd-split"><div class="wd-col"><section class="wd-card"><h4>Lists on this site</h4>
        ${lists.length ? `<div class="wd-chips">${lists.map(c => `<span class="wd-pill">${esc(S(c.label))}</span>`).join('')}</div>
          <div class="wd-row wrap" style="margin-top:12px">${studioBtn('data', 'Open App & data')}</div>`
          : `<p class="wd-mut">No lists yet. Orders, enquiries, members, bookings: ask for the ones you need.</p>
          <div class="wd-row wrap"><button class="btn go" type="button" data-wd-say="${esc(name(v))} website mein logins aur ek list jodo: ">Add lists and logins</button></div>`}</section>
        <section class="wd-card"><h4>Import</h4><p class="wd-mut">A product sheet (Excel, CSV or Google Sheet) becomes catalogue pages. You see a preview first; nothing is written before your Apply.</p>
          <button class="btn soft" type="button" data-wd-say="${esc(name(v))} website mein meri sheet se catalogue banao: [link]">Catalogue from a sheet</button></section></div>
      <div class="wd-col narrow"><section class="wd-card"><h4>Rules that always hold</h4>
        <p class="wd-li">Totals and prices are worked out by the server.</p><p class="wd-li">Visitors see only their own rows.</p>
        <p class="wd-li">Mobile + OTP logins, staff two-step code, consent and "download / delete my data" are built in.</p></section></div></div>`;
  }

  function integrations(box, v) {
    const langs = L(v.languages), nm = name(v);
    const items = [['cart', 'Shop and cart', 'Prices and stock checked by the server, COD, pickup, coupons, GST invoices on your series.', 'shop', `${nm} website mein shop chalu karo`],
      ['card', 'Online payments', 'UPI QR to your UPI ID, or your own Razorpay / Cashfree / PhonePe account. Paid only when the gateway confirms.', '', `${nm} website par online payment jodo`],
      ['cal', 'Booking slots', 'Real time slots with limits; you confirm each booking.', '', `${nm} website mein booking slot lagao`],
      ['blog', 'Blog', 'Hoola drafts posts, you say Haan to publish. Categories, RSS, scheduled posts.', 'blog', `${nm} website par blog chalu karo`],
      ['globe', 'Languages', `Now: ${langs.join(', ') || 'en'}. Up to 4 more Indian languages with a switch in the menu.`, 'langs', `${nm} website mein Hindi version bhi jodo`],
      ['chat', 'Visitor chat', 'Visitors message your team from the site; your reply goes only on your tap.', '', `${nm} website par visitor chat chalu karo`],
      ['pin', 'Map and directions', 'Loads only when the visitor taps, so the page stays fast.', '', `${nm} website ke contact page par map lagao`],
      ['spark', 'Rich pieces', 'Quiz, configurator, comparison table, Lottie animation, 3D hero, scroll motion.', '', `${nm} website mein ek quiz jodo: `],
      ['link', 'Your other apps', 'Send new orders to HubSpot, Slack or Google Sheets through your own account.', '', `${nm} website ke naye orders meri Google Sheet mein bhejo`]];
    box.innerHTML = `<p class="wd-mut" style="margin:0 0 14px">Each one starts as your words in chat, so Hoola plans it first. Money never moves without your tap.</p>
      <div class="wd-grid3">${items.map(([k, t, d, tab, ask]) => `<section class="wd-card wd-int"><div class="wd-row"><span class="wd-ico">${ico(k)}</span><b>${esc(t)}</b></div>
        <p class="wd-mut sm">${esc(d)}</p><div class="sp"></div><div class="wd-row wrap">
        ${tab && hasVersion(v) ? studioBtn(tab, 'Manage', 'soft') : ''}<button class="btn ${tab && hasVersion(v) ? 'soft' : 'go'}" type="button" data-wd-say="${esc(ask)}">${tab && hasVersion(v) ? 'Change in chat' : 'Add'}</button></div></section>`).join('')}</div>`;
  }

  /* ---------------- publish ---------------- */
  async function publish(box, v) {
    box.innerHTML = '<div class="empty">Loading the addresses…</div>';
    let host = null, moves = null;
    try { host = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/hosting`); } catch (e) { host = {hosts: [], error: e.message}; }
    try { moves = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/moves`); } catch { moves = null; }      // 404 = no old site
    if (!CUR || CUR.id !== v.id || TAB !== 'publish') return;
    const hosts = L(host.hosts), versions = L(v.versions);
    const rows = L(moves?.rows);
    box.innerHTML = `<div class="wd-split"><div class="wd-col">
      <section class="wd-card accent"><h4>Put v${esc(S(v.version || '–'))} live</h4>
        ${hasVersion(v) ? `<p class="wd-mut">Hoola checks the version and the addresses first and shows you what will happen. Nothing goes live until you tap.</p>
          <div class="wd-row wrap"><button class="btn go" type="button" data-wd-act="launch">Check and go live…</button></div><div id="wdLaunch"></div>`
          : '<p class="wd-mut">There is nothing to put live yet: the first version is still being made.</p>'}</section>
      ${moves ? `<section class="wd-card"><div class="wd-row wrap"><h4>Old site addresses</h4>${pill(moves.approved ? 'Approved' : `${rows.length} found · waiting for your Haan`, moves.approved ? 'ok' : 'warn')}</div>
        <p class="wd-mut">Links and Google results from your old site (${esc(S(moves.from_host))}) open the matching new page (301). Untick any you don't want.</p>
        <form data-wd-form="moves" data-hash="${esc(S(moves.hash))}">${rows.slice(0, 200).map((r, i) => `<label class="wd-mv"><input type="checkbox" name="keep" value="${esc(S(r.old))}" ${r.guess ? '' : 'checked'}>
          <code>${esc(S(r.old))}</code><span aria-hidden="true">→</span><code>${esc(S(r.new))}</code>${pill(S(r.how), r.guess ? 'warn' : '')}</label>`).join('') || '<p class="wd-mut">Every old address already exists on the new site.</p>'}
          ${rows.length ? `<div class="wd-row wrap"><button class="btn soft" type="button" data-wd-act="compare">Compare old vs new</button><span class="sp"></span><button class="btn go" type="submit">Haan, jod do</button></div>` : ''}</form><div id="wdCompare"></div></section>` : ''}
    </div><div class="wd-col narrow">
      <section class="wd-card"><h4>Addresses</h4>${host.error ? `<p class="wd-mut">${esc(host.error)}</p>` : ''}
        ${hosts.length ? hosts.map(h => `<div class="wd-kv"><code>${esc(S(h.host))}</code>${pill(S(h.stage) || S(h.status), S(h.stage) === 'Live' ? 'ok' : S(h.stage) === 'Offline' ? 'bad' : 'warn')}</div>
          ${h.problem ? `<p class="wd-li bad">${esc(S(h.problem))}</p>` : ''}`).join('') : '<p class="wd-mut">Not live yet. Your free address is made when you first go live.</p>'}</section>
      <section class="wd-card"><h4>Connect your domain</h4><p class="wd-mut">Hoola gives you the exact records to add, checks them from three places, then sets up HTTPS.</p>
        <form data-wd-form="domain" class="wd-row"><input id="wdDom" aria-label="Your domain" placeholder="yourname.in" autocomplete="off"><button class="btn soft" type="submit">Connect</button></form>
        <button class="btn soft" type="button" data-wd-say="${esc(name(v))} website ke liye achha domain dhoondho" style="margin-top:8px">Find a domain to buy</button></section>
      <section class="wd-card"><h4>Versions</h4>${versions.length ? versions.slice(0, 8).map(x => `<div class="wd-kv"><span>${pill('v' + S(x.version), Number(x.version) === Number(v.version) ? 'ok' : '')} ${esc(S(x.note).slice(0, 60))}</span>
          ${Number(x.version) !== Number(v.version) && hosts.length ? `<button class="btn soft sm" type="button" data-wd-act="rollback" data-ver="${esc(S(x.version))}">Roll back…</button>` : ''}</div>`).join('') : '<p class="wd-mut">No versions yet.</p>'}</section>
    </div></div>`;
  }

  async function launch() {
    const out = EL.querySelector('#wdLaunch');
    try {
      const card = await api('POST', `/api/sites/${encodeURIComponent(CUR.id)}/launch-request`, {});
      const blk = L(card.blockers);
      out.innerHTML = `<div class="wd-launch"><p>${esc(S(card.say))}</p>
        ${blk.length ? blk.map(b => `<p class="wd-li bad">${esc(S(b))}</p>`).join('') : `<div class="wd-chips">${L(card.hosts).map(h => `<code>${esc(S(h))}</code>`).join(' ')}</div>
        <div class="wd-row"><span class="sp"></span><button class="btn go" type="button" data-wd-act="golive" data-hash="${esc(S(card.hash))}">Haan, live karo</button></div>`}</div>`;
    } catch (e) { out.innerHTML = `<p class="wd-li bad">${esc(e.message)}</p>`; }
  }

  /* ---------------- health ---------------- */
  async function health(box, v) {
    if (!hasVersion(v)) { box.innerHTML = '<section class="wd-card"><p class="wd-mut">Health shows up once the website is built and live.</p></section>'; return; }
    box.innerHTML = '<div class="empty">Reading visits, speed and backups…</div>';
    let care = null, ops = null;
    try { care = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/care?days=30`); } catch (e) { care = {error: e.message}; }
    try { ops = await api('GET', `/api/sites/${encodeURIComponent(v.id)}/ops?days=30`); } catch (e) { ops = {error: e.message}; }
    if (!CUR || CUR.id !== v.id || TAB !== 'health') return;
    const chk = M(v.checks), sp = M(care.speed || ops.speed), bk = M(ops.backup), rt = M(bk.restore_test);
    const band = g => g === 'good' ? 'ok' : g === 'poor' ? 'bad' : 'warn';
    const speedRow = (k, label) => sp[k] ? `<div class="wd-kv"><span>${esc(label)}</span>${pill(`${S(sp[k].p75)} · ${S(sp[k].grade)}`, band(S(sp[k].grade)))}</div>` : '';
    box.innerHTML = `${care.say ? `<section class="wd-card accent"><p class="wd-say">${esc(S(care.say))}</p>${L(care.tips).map(t => `<p class="wd-li">${esc(S(t))}</p>`).join('')}</section>` : ''}
      <div class="wd-grid2">
      <section class="wd-card"><h4>Visitors and results (30 days)</h4><p class="wd-mut sm">No cookies, no trackers: pages counted per day only.</p>
        ${care.error ? `<p class="wd-mut">${esc(care.error)}</p>` : `
        <div class="wd-kv"><span>Page visits</span><b>${esc(S(care.views ?? '–'))}</b></div>
        <div class="wd-kv"><span>Enquiries</span><b>${esc(S(care.leads ?? '–'))}${care.views ? ` (${esc(S(care.conversion_pct))}%)` : ''}</b></div>
        <div class="wd-kv"><span>Uptime</span><b>${care.uptime_pct == null ? 'not measured yet' : esc(S(care.uptime_pct)) + '%'}</b></div>
        ${Object.entries(M(care.ssl_days)).map(([h, d]) => `<div class="wd-kv"><span>HTTPS · <code>${esc(S(h))}</code></span><b>${d == null ? '–' : esc(S(d)) + ' days left'}</b></div>`).join('')}
        ${L(care.top_pages).slice(0, 4).map(p => `<div class="wd-kv"><code>${esc(S(L(p)[0]))}</code><span>${esc(S(L(p)[1]))}</span></div>`).join('')}`}</section>
      <section class="wd-card"><h4>Speed on real phones</h4><p class="wd-mut sm">Measured in your visitors' browsers, shown as bands (p75).</p>
        ${speedRow('lcp', 'Main picture shows') + speedRow('fcp', 'First paint') + speedRow('cls', 'Layout shift') + speedRow('ttfb', 'Server answer') || '<p class="wd-mut">No real visits measured yet.</p>'}</section>
      <section class="wd-card"><h4>Checks before going live</h4>
        ${chk.passed == null ? '<p class="wd-mut">Not run yet.</p>' : `<div class="wd-kv"><span>Blocking checks</span>${pill(chk.passed ? 'Passed' : L(chk.blocking).length + ' to fix', chk.passed ? 'ok' : 'bad')}</div>
        <div class="wd-kv"><span>Notes (incl. the "looks AI-made" check)</span>${pill(String(L(chk.warnings).length), L(chk.warnings).length ? 'warn' : 'ok')}</div>
        <div class="wd-kv"><span>Test visitor walks</span>${pill(String(L(chk.journeys).length), '')}</div>`}
        <div class="wd-row" style="margin-top:10px">${studioBtn('jaanch', 'Open all checks', 'soft')}</div></section>
      <section class="wd-card"><h4>Errors and backups</h4>${ops.error ? `<p class="wd-mut">${esc(ops.error)}</p>` : `
        <div class="wd-kv"><span>Visitor page errors</span>${pill(Number(ops.errors) ? String(ops.errors) : 'None', Number(ops.errors) ? 'warn' : 'ok')}</div>
        <div class="wd-kv"><span>Backups</span>${pill(bk.enabled ? (bk.last_day ? 'Last ' + S(bk.last_day) : 'On') : 'Off', bk.enabled ? 'ok' : 'warn')}</div>
        <div class="wd-kv"><span>Restore test</span>${rt.day ? pill(rt.ok ? 'Matched · ' + S(rt.day) : 'Did not match · ' + S(rt.day), rt.ok ? 'ok' : 'bad') : pill('Not run yet', '')}</div>`}</section></div>`;
  }

  /* ---------------- settings ---------------- */
  function settings(box, v) {
    const f = M(v.facts);
    const fields = [['name', 'Business name'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp'], ['email', 'Email'], ['hours', 'Opening hours'], ['address', 'Address'], ['city', 'City'], ['instagram', 'Instagram']];
    box.innerHTML = `<div class="wd-split"><div class="wd-col">
      <form class="wd-card" data-wd-form="facts"><h4>Business details</h4><p class="wd-mut sm">Used on every page. A change here is used in the next version; ask for a change to rebuild now.</p>
        <div class="wd-grid2 tight">${fields.map(([k, l]) => `<label class="wd-fld"><span>${esc(l)}</span><input name="${k}" value="${esc(S(f[k]))}" autocomplete="off"></label>`).join('')}</div>
        <div class="wd-row"><span class="sp"></span><button class="btn go" type="submit">Save details</button></div></form>
      <section class="wd-card"><h4>SEO and Google</h4><p class="wd-mut">Page titles, descriptions, sitemap and Search Console are set by Hoola on every build. For a monthly audit and keyword plan, hire the SEO employee.</p>
        <div class="wd-row wrap"><button class="btn soft" type="button" data-v="hire">AI Employees</button><button class="btn soft" type="button" data-wd-say="${esc(name(v))} website ka SEO check karo">Check SEO now</button></div></section>
    </div><div class="wd-col narrow">
      <section class="wd-card"><h4>Team</h4><p class="wd-mut">Writers draft, editors review, publishers put live. Invite them by saying it.</p>
        <button class="btn soft" type="button" data-wd-say="${esc(name(v))} website ke CMS mein ek team member jodo: ">Invite a team member</button></section>
      <section class="wd-card danger"><h4>Take the site down</h4><p class="wd-mut">The site stops answering; your pages, data and versions are kept.</p>
        <button class="btn soft bad" type="button" data-wd-act="takedown">Take down…</button></section>
    </div></div>`;
  }

  /* ---------------- events ---------------- */
  async function onClick(e) {
    const b = e.target.closest('button, a'); if (!b || !EL.contains(b) || BUSY) return;
    const d = b.dataset;
    if (d.wdSite) { if (await loadSite(d.wdSite)) { TAB = 'overview'; draw(); } return; }
    if (d.wdTab) { TAB = d.wdTab; draw(); return; }
    if (d.wdStudio) { if (!studio) return toast('The Website studio is not available here.', true);
      studio(CUR, d.wdStudio, d.wdEdit === '1'); return; }
    if (d.wdSay != null && d.wdSay !== '') { say(d.wdSay); return; }
    if (d.wdStart != null) { const t = EL.querySelector('#wdAsk'); if (!t) return; if (d.wdStart !== 'focus') t.value = d.wdStart; t.focus(); return; }
    if (d.wdType) { const t = EL.querySelector('#wdAsk'); if (t) { t.value = `${d.wdType} ki website banao: [naam, shehar]`; t.focus(); } return; }
    const act = d.wdAct; if (!act) return;
    const id = CUR ? encodeURIComponent(CUR.id) : '';
    BUSY = true; b.disabled = true;
    try {
      if (act === 'home') { CUR = null; TAB = 'overview'; await loadSites(); draw(); }
      else if (act === 'refresh') { await loadSites(); draw(); }
      else if (act === 'resume') { await api('POST', `/api/sites/${id}/resume`, {}); toast('Building again.'); await reload(); }
      else if (act === 'stop') { await api('POST', `/api/sites/${id}/stop`, {}); toast('Stopping after the current part.'); await reload(); }
      else if (act === 'export') { const r = await api('POST', `/api/sites/${id}/export`, {format: d.fmt}); toast(S(r.say) || 'Ready: it is in your chat files.'); }
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
        const out = EL.querySelector('#wdCompare'); out.innerHTML = '<div class="empty">Opening both pages…</div>';
        const r = await api('POST', `/api/sites/${id}/compare-old`, {old: '/'});
        out.innerHTML = `<div class="wd-launch"><p>${esc(S(r.say))}</p>${L(r.differences).map(x => `<p class="wd-li">${esc(S(x))}</p>`).join('')}${r.note ? `<p class="wd-mut sm">${esc(S(r.note))}</p>` : ''}</div>`;
      }
    } catch (er) { toast(er.message, true); }
    finally { BUSY = false; if (b.isConnected) b.disabled = false; }
  }

  async function reload() { if (CUR && await loadSite(CUR.id)) draw(); }

  async function onSubmit(e) {
    const f = e.target.closest('form[data-wd-form]'); if (!f || !EL.contains(f)) return;
    e.preventDefault(); if (BUSY) return;
    const kind = f.dataset.wdForm, id = CUR ? encodeURIComponent(CUR.id) : '';
    BUSY = true;
    try {
      if (kind === 'ask') { const t = S(f.querySelector('textarea').value).trim(); if (!t) return toast('Write one line about the website.', true); say(t); }
      else if (kind === 'change') { const t = S(f.querySelector('textarea').value).trim(); if (!t) return toast('Write the change first.', true);
        const r = await api('POST', `/api/sites/${id}/change`, {instruction: t}); toast(S(r.say) || 'Change started.'); f.reset(); await reload(); }
      else if (kind === 'facts') {
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
    finally { BUSY = false; }
  }

  return {open, draw, reset() { CUR = null; SITES = []; TAB = 'overview'; }};
};
