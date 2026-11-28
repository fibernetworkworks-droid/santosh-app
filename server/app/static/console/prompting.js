/* HOOLA PROMPTING - the page (/console/prompting; docs/HOOLA_PROMPTING_PLAN.md P3). Its own full-screen app like Hoola
   Flow: the same sign-in as the console (its token in this browser), the /api/prompting routes, the same strict CSP.

   Home (one box) -> the workbench (her words | what Hoola understood | score + the finished prompt) -> Run in Hoola /
   Copy / Save. Recipes = Hoola's starters with blanks. My prompts = what she saved.
   "Run in Hoola" only HANDS THE TEXT to the engine's own box (Web Studio or the chat) - it is never sent for her, and
   the engine shows its own price before anything is made. */
'use strict';
(function () {
  const $ = s => document.querySelector(s);
  const esc = v => (v == null ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  if (!TOKEN) { location.replace('/console/'); return; }
  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch (e) { /* no body */ }
    if (!r.ok) { const bad = data && Array.isArray(data.detail) && data.detail[0];
      throw new Error((data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) || (bad ? String(bad.msg) : '') || `The server refused the request (${r.status})`); }
    return data;
  }
  function toast(msg, bad) { const t = $('#toast'); t.textContent = String(msg); t.className = 'hp-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200); }
  const UI = window.HoolaImprove({api, esc, toast});
  const I = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const ICON = {home: I('<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>'),
    web: I('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/>'),
    image: I('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M21 16l-5-5-8 8"/>'),
    script: I('<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h7M9 16h5"/>'),
    app: I('<rect x="7" y="2.5" width="10" height="19" rx="2.2"/><path d="M11 18h2"/>'),
    video: I('<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>'),
    music: I('<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>'),
    marketing: I('<path d="M4 10v4h3l6 4V6L7 10z"/><path d="M17 9a4 4 0 0 1 0 6"/>'),
    doc: I('<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M10 12h5M10 16h5"/>'),
    code: I('<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>'),
    research: I('<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>'),
    data: I('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>'),
    aiapp: I('<rect x="4" y="7" width="16" height="12" rx="3"/><path d="M12 3v4M9 13h.01M15 13h.01M9.5 16h5"/>'),
    chat: I('<path d="M4 5h16v11H9l-5 4z"/>'),
    learn: I('<path d="M3 8l9-4 9 4-9 4z"/><path d="M7 10v5c0 1.5 2.5 3 5 3s5-1.5 5-3v-5"/>'),
    results: I('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
    recipes: I('<path d="M5 4h14v16H5z"/><path d="M9 8h6M9 12h6"/>'), saved: I('<path d="M6 3h12v18l-6-4-6 4z"/>'),
    back: I('<path d="M15 6l-6 6 6 6"/>')};
  const PH = {web: 'a website for my bakery, with the menu and a way to order a cake',
    image: 'a poster for our spring sale, a bit premium, soft green and gold',
    script: 'a 30-second reel script for a language school',
    app: 'an app for my grocery shop: order, home delivery, pay on the phone',
    video: "a 10-second video of my bakery's morning bread coming out of the oven, warm and slow",
    music: 'a 15-second jingle for my coffee shop, a warm female voice',
    marketing: 'a message to my regular customers: 20% off everything this weekend',
    doc: 'a quotation for a yearly maintenance contract on 10 air conditioners',
    code: 'fix the bug: the cart total shows 0 after a coupon, in server/app/shop.py',
    research: 'compare the cheapest couriers for 5 kg parcels between two cities, latest prices',
    data: 'in sales_october.xlsx, which 5 products made the most profit? a chart by product',
    aiapp: 'an AI for my salon that takes bookings, open 10 am to 8 pm, closed on Tuesday',
    chat: 'a polite reply to a customer whose cake came 40 minutes late'};
  const RUN = {web: ['hoola.prompt.toWeb', '/console/web', 'Opens the Web Studio with this in its box. Nothing is built until you press Build there.'],
    app: ['hoola.prompt.toApp', '/console/apps', 'Opens the App Studio with this in its box. Nothing is built until you press Build there.'],
    code: ['', '/console/code', 'Opens Hoola Code with this in its box. Nothing starts until you press Send there.']};
  const CHAT_NOTE = 'Puts this in the chat box. Nothing is sent until you press Send; a paid job shows its price first.';
  const st = {secs: [], known: [], section: '', text: '', view: null, pack: null, savedId: '', mine: null, fill: null, cmp: null, ready: null, recipe: null, q: '', rsec: '', shelf: 'hoola', wq: '', wgroup: '', wfam: '', wkind: '', wsort: 'loved', wpage: 1, wfill: null, paste: null, lib0: null, libEl: '', mcat: '', adapted: null};

  /* the Hoola Orbit mark (static/console/mark.js), drawn in the accent colour */
  const MARK = '<svg class="hp-mark" viewBox="20 20 60 60" aria-hidden="true"><g fill="currentColor"><path d="M31.50 27.82A28.88 28.88 0 0 1 72.18 68.50L67.95 64.28A23.41 23.41 0 0 0 35.72 32.05Z"/><path d="M68.50 72.18A28.88 28.88 0 0 1 27.82 31.50L32.05 35.72A23.41 23.41 0 0 0 64.28 67.95Z"/><path d="M38.26 34.58A19.38 19.38 0 0 1 65.42 61.74L62.03 58.35A15.12 15.12 0 0 0 41.65 37.97Z"/><path d="M61.74 65.42A19.38 19.38 0 0 1 34.58 38.26L37.97 41.65A15.12 15.12 0 0 0 58.35 62.03Z"/><path d="M22 22L51.77 48.23L78 78L48.23 51.77Z"/><circle cx="50" cy="50" r="9.58"/></g></svg>';
  const CHEV = I('<path d="M6 9l6 6 6-6"/>'), GRID = I('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
    ARROW = I('<path d="M5 12h14M13 6l6 6-6 6"/>'), HEART = I('<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>'),
    SEARCH = I('<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>'), PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M7 4.5v15l13-7.5z"/></svg>',
    SOUND = I('<path d="M11 5L6 9H3v6h3l5 4V5z"/><path d="M16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>');
  const TOPS = ['library', 'recipes', 'saved', 'results', 'learn'];
  function shell(active, body) {
    const on = TOPS.includes(active) ? active : 'home';
    const nav = (key, hash, label) => `<a class="hp-nav" href="${hash}" ${on === key ? 'aria-current="page"' : ''}>${esc(label)}</a>`;
    $('#hp').innerHTML = `<div class="hp"><header class="hp-bar">
        <a class="hp-brand" href="#/" aria-label="Hoola Prompting home">${MARK}<span>Prompting</span></a>
        <nav class="hp-navs" aria-label="Hoola Prompting">${nav('home', '#/', 'Make a prompt')}${nav('library', '#/library', 'Library')}${nav('recipes', '#/recipes', "Hoola's starters")}${nav('saved', '#/saved', 'My prompts')}${nav('results', '#/results', 'Results')}${nav('learn', '#/learn', 'Learn')}</nav>
        <span class="hp-sp"></span><a class="hp-back" href="/console/">${ICON.back}<span>Back to Hoola chat</span></a>
      </header><main class="hp-main" id="hpMain"><div class="hp-wrap">${body}</div></main></div>`;
  }
  function seg() {
    return `<span class="hp-seg" role="group" aria-label="What are you making?">${[['', 'Auto'], ...st.secs.map(s => [s.key, s.label])]
      .map(([k, l]) => `<button type="button" data-sec="${esc(k)}" aria-pressed="${st.section === k}">${esc(l)}</button>`).join('')}</span>`;
  }
  const cards = items => items.map(r => `<button type="button" class="hp-card" data-recipe="${esc(r.id)}"><b>${esc(r.title)}</b><span>${esc(r.makes || '')}${r.community ? esc(' · by ' + (r.by || 'a Hoola user')) : ''}</span>
      <i><span class="hp-tag">${esc(r.world ? r.kind_label : (st.secs.find(s => s.key === r.section) || {label: r.section}).label)}</span> ${r.safety ? '<span class="hp-tag hp-warn">Copy only</span> ' : r.use === 'fill' ? '<span class="hp-tag hp-long">Long</span> ' : ''}${r.kept ? `<span class="hp-kept">kept ${r.kept.kept} of ${r.kept.of} times</span> ` : ''}${r.blanks && r.blanks.length ? esc(r.blanks.length + ' blank' + (r.blanks.length > 1 ? 's' : '') + ' to fill') : 'ready to use'}</i></button>`).join('');

  /* ---------- home: Make a prompt (one box, every category) + the Ready prompt library below ---------- */
  const fmt = n => Number(n || 0).toLocaleString('en');
  async function lib0() {          // the families (53 categories in 8) and kinds, read once
    if (!st.lib0) st.lib0 = await api('GET', '/api/prompting/world?per=1').catch(() => ({families: [], kinds: [], all: 0}));
    return st.lib0;
  }
  const catOf = key => { for (const f of (st.lib0 || {}).families || []) { const c = f.cats.find(x => x.key === key); if (c) return {...c, family: f.key, flabel: f.label}; } return null; };
  function picker() {
    const fams = (st.lib0 || {}).families || [];
    return `<div class="hp-pop" id="hpPop" role="dialog" aria-label="Choose a category" hidden>
        <button type="button" class="hp-popany" data-mcat="">Any category <span>Hoola works it out from your words</span></button>
        ${fams.map(f => `<div class="hp-popf"><div class="hp-popn">${esc(f.label)}</div><div class="hp-chips">${f.cats.map(c => `<button type="button" class="hp-chip" data-mcat="${esc(c.key)}">${esc(c.label)} <span>${fmt(c.n)}</span></button>`).join('')}</div></div>`).join('')}</div>`;
  }
  function everyCat() {
    const fams = (st.lib0 || {}).families || [], n = fams.reduce((a, f) => a + f.cats.length, 0);
    return fams.length ? `<div class="hp-cats"><div class="hp-catsh"><h2>Every category</h2><span>${n} categories · tap one to start from it</span></div>
        ${fams.map(f => `<div class="hp-fam"><div class="hp-famn">${esc(f.label)}</div><div class="hp-chips">${f.cats.map(c => `<a class="hp-chip" href="#/m/${esc(c.key)}">${esc(c.label)} <span>${fmt(c.n)}</span></a>`).join('')}</div></div>`).join('')}</div>` : '';
  }
  async function home(section, catKey) {
    await lib0();
    const cat = catKey ? catOf(catKey) : null;
    st.section = cat ? cat.section : (section || ''); st.mcat = cat ? cat.key : '';
    const sec = st.secs.find(s => s.key === st.section);
    const label = cat ? cat.label : 'Any category';
    shell('home', `<section class="hp-hero" id="hpMake">
        ${cat ? `<nav class="hl-crumb" aria-label="Where you are"><a href="#/">Make a prompt</a>${I('<path d="M9 6l6 6-6 6"/>')}<span>${esc(cat.label)}</span></nav>` : ''}
        <h1>${cat ? esc('A prompt for ' + cat.label) : section && sec ? esc('A prompt for ' + sec.makes) : 'What should we make a prompt for?'}</h1>
        <p>Say it in your own words, in any language. Hoola asks only what is missing and writes the prompt for the tool that will make it.</p>
        <form class="hp-ask" id="hpAsk"><label class="hp-lab" for="hpText" style="position:absolute;left:-9999px">Your idea</label>
          <textarea id="hpText" maxlength="2000" placeholder="${esc(PH[st.section] || PH.video)}">${esc(st.text)}</textarea>
          <div class="hp-askrow"><button type="button" class="hp-pick" id="hpPick" aria-haspopup="dialog" aria-expanded="false" aria-controls="hpPop">${GRID}<span>${esc(label)}</span>${CHEV}</button>
            ${cat ? `<a class="hp-b sm ghost" href="#/" aria-label="Clear the category">Clear</a>` : ''}
            <span class="hp-sp"></span><button class="hp-b pri lg" type="submit">Make my prompt ${ARROW}</button></div>
          ${picker()}</form>
        ${cat ? `<div class="hp-strip"><div class="hp-catsh"><h2>Or start from a ready ${esc(cat.label)} prompt</h2><button type="button" class="hp-link" data-wlib="${esc(cat.key)}" data-wfam="${esc(cat.family)}">All ${fmt(cat.n)} ${ARROW}</button></div><div class="hl-row" id="hpCatRow"><p class="hp-empty">Loading…</p></div></div>` : everyCat()}
      </section>
      ${cat ? '' : '<section class="hl" id="hpLib" aria-label="Ready prompt library"></section>'}`);
    $('#hpText').focus();
    if (cat) { const r = await api('GET', `/api/prompting/world?group=${encodeURIComponent(cat.key)}&sort=media&per=10`).catch(() => ({items: []}));
      const row = $('#hpCatRow'); if (row) row.innerHTML = (r.items || []).map(libCard).join('') || '<p class="hp-empty">No ready prompts here yet.</p>'; }
    else await library($('#hpLib'));
  }
  const rows = items => items.map(p => `<div class="hp-rowi"><div><b>${esc(p.title)}</b><span>${esc(p.prompt)}</span></div>
      <span class="hp-tag">${esc((st.secs.find(s => s.key === p.section) || {label: p.section}).label)}</span>
      ${p.version > 1 ? `<span class="hp-tag">v${esc(p.version)}</span>` : ''}${p.scheduled ? '<span class="hp-tag">Scheduled</span>' : ''}${p.shared ? '<span class="hp-tag">Shared</span>' : ''}${(p.ask || []).length ? '<span class="hp-tag">Fill each time</span>' : ''}
      <button type="button" class="hp-b sm" data-open="${esc(p.id)}">Open</button><button type="button" class="hp-b sm ghost danger" data-del="${esc(p.id)}" aria-label="Delete ${esc(p.title)}">Delete</button></div>`).join('');

  /* ---------- the workbench ---------- */
  function bench() {
    const p = st.pack, sec = UI.secOf(p.brief.section);
    shell(p.brief.section, `<div class="hp-top"><a class="hp-b sm ghost" href="#/s/${esc(p.brief.section)}">${ICON.back} New prompt</a><h1>${esc(sec.label)} prompt</h1><span class="hp-sp"></span>
        <span class="hp-tag">${st.savedId ? 'Saved' : 'Not saved'}</span></div>
      <div class="hp-bench"><div class="hp-pane"><label class="hp-lab" for="hpHers">Your words</label>
          <textarea class="hp-hers" id="hpHers" maxlength="2000">${esc(p.brief.intent)}</textarea>
          <div class="hp-acts" style="margin-bottom:18px"><button type="button" class="hp-b sm" id="hpAgain">Read my words again</button></div>
          <div id="hpBrief"></div></div>
        <div class="hp-pane sticky"><div id="hpResult"></div>
          <div class="hp-acts"><button type="button" class="hp-b pri" id="hpRun">${esc(p.out.run.label)}</button>
            <button type="button" class="hp-b" id="hpCopy">Copy</button><button type="button" class="hp-b" id="hpSave">${st.savedId ? 'Save changes' : 'Save'}</button>
            <button type="button" class="hp-b" id="hpCmp">Compare</button><button type="button" class="hp-b" id="hpOut" aria-expanded="false" aria-controls="hpOutBox">Other AI tools</button></div>
          <div id="hpOutBox" class="hp-out" hidden></div>
          <p class="hpi-note" style="margin-top:10px;font-size:12.5px;color:var(--dim)">${esc((RUN[p.out.run.to] || [])[2] || CHAT_NOTE)}</p>
          <div id="hpLearn"></div>
          ${st.savedId ? '<div id="hpMine" class="hp-mine" aria-live="polite"></div>' : ''}</div></div>`);
    st.view = UI.mount($('#hpBrief'), p, {resultEl: $('#hpResult'), onChange(pk) { st.pack = pk; $('#hpRun').textContent = pk.out.run.label; }});
    if (st.savedId) mine().catch(e => toast(e.message, true));
    benchLessons().catch(() => null);
  }

  /* ---------- P9 SEEKHO: lessons from her own prompts ---------- */
  const lessonCard = x => `<div class="hp-lesson" data-lesson-card="${esc(x.id)}"><b>${esc(x.title)}</b><p>${esc(x.idea)}</p>
      ${x.hers ? `<p class="hp-before"><span>You wrote</span>${esc(x.hers)}</p>` : ''}<p class="hp-after"><span>Better</span>${esc(x.instead)}</p>
      ${x.proof ? Object.values(x.proof).map(p => `<p class="hp-proof">${esc(p.say)}</p>`).join('') : ''}
      <p class="hp-basis">${esc(x.basis)}${x.times > 1 ? esc(' Seen in ' + x.times + ' of your prompts.') : ''}</p>
      <div class="hp-acts"><button type="button" class="hp-b sm" data-lesson="${esc(x.id)}" data-state="got_it">Got it</button>
        <button type="button" class="hp-b sm ghost" data-lesson="${esc(x.id)}" data-state="not_useful">Not useful</button></div></div>`;
  async function benchLessons() {
    const el = $('#hpLearn'); if (!el || !st.pack) return;
    const r = await api('POST', '/api/prompting/learn/brief', {brief: st.pack.brief});
    el.innerHTML = (r.lessons || []).length ? `<div class="hp-mine"><h3>Learn from this prompt</h3>${r.lessons.map(lessonCard).join('')}</div>` : '';
  }
  async function learn() {
    const r = await api('GET', '/api/prompting/learn');
    shell('learn', `<div class="hp-top"><h1>Learn</h1><span class="hp-tag">from ${esc(r.from)} saved prompt${r.from === 1 ? '' : 's'}</span></div>
      <p class="hp-lead">Short lessons made from your own prompts, one idea each. Where your own results prove the point, the numbers are shown; otherwise it says it is Hoola's starter guidance.</p>
      ${(r.lessons || []).length ? `<div class="hp-lessons">${r.lessons.map(lessonCard).join('')}</div>` : `<p class="hp-empty">${esc(r.note || 'Nothing to learn from your saved prompts right now - they read clearly.')}</p>`}
      ${r.hidden ? `<p class="hp-lead" style="margin-top:14px">${esc(r.hidden)} lesson${r.hidden === 1 ? '' : 's'} hidden after you marked ${r.hidden === 1 ? 'it' : 'them'}. 'Got it' comes back after 30 days if it still applies.</p>` : ''}`);
  }

  /* ---------- P7 MERE PROMPT: one saved prompt's history, the parts she fills each time, its schedule, its share link ---------- */
  const REPEAT = [['weekly', 'Every week'], ['daily', 'Every day'], ['weekdays', 'Every weekday'], ['monthly', 'Every month']];
  const nextAt = () => { const d = new Date(Date.now() + 864e5); d.setHours(9, 0, 0, 0);
    return new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 16); };
  async function mine() {
    const el = $('#hpMine'); if (!el) return;
    const id = st.savedId, sec = UI.secOf(st.pack.brief.section);
    const [me, sch] = await Promise.all([api('GET', '/api/prompting/saved/' + encodeURIComponent(id)), api('GET', `/api/prompting/saved/${encodeURIComponent(id)}/schedule`).catch(() => ({schedule: null}))]);
    st.mine = me; const ask = me.ask || [], sc = sch.schedule;
    const canRun = st.pack.out.run.to === 'chat';
    el.innerHTML = `<h3>This saved prompt</h3>
      <div class="hp-mrow"><div><b>Version ${esc(me.version || 1)}</b><span>Every change is kept. Bring back any version.</span></div>
        <a class="hp-b sm" href="#/v/${esc(id)}">History</a></div>
      <div class="hp-mrow col"><div><b>Fill each time</b><span>Parts Hoola asks you for every time you use it, like this week's offer.</span></div>
        <div class="hp-chk" role="group" aria-label="Fill each time">${sec.slots.map(x => `<button type="button" class="hp-b sm${ask.includes(x.key) ? ' on' : ''}" data-ask="${esc(x.key)}" aria-pressed="${ask.includes(x.key)}">${esc(x.label)}</button>`).join('')}</div></div>
      <div class="hp-mrow col"><div><b>Run on a schedule</b><span>${sc ? esc('Runs ' + (sc.repeat || '') + (sc.next_run_local || sc.next_run ? ' - next ' + (sc.next_run_local || sc.next_run) : '') + '. The result comes to your Hoola chat; anything that sends or spends still waits for your tap.')
          : canRun ? (ask.length ? 'A prompt that asks you for something cannot run by itself.' : 'Hoola does it for you on the days you choose; the result comes to your chat.') : 'This prompt opens a studio where you press Build yourself, so it cannot run on a schedule.'}</span></div>
        ${sc ? '<button type="button" class="hp-b sm ghost danger" id="hpUnsched">Stop the schedule</button>'
          : canRun && !ask.length ? `<form id="hpSched" class="hp-sched"><select name="repeat" aria-label="How often">${REPEAT.map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select>
            <input type="datetime-local" name="at" value="${nextAt()}" aria-label="First run" required><button class="hp-b sm pri" type="submit">Schedule</button></form>` : ''}</div>
      <div class="hp-mrow col"><div><b>Share with your team</b><span>${me.shared ? esc('A link is on until ' + new Date(me.share_until).toLocaleDateString() + '. Anyone with it can see this prompt, including your facts in it, and save a copy.') : 'Make a link a teammate opens in Hoola and saves a copy from. Your facts in the prompt go with it.'}</span></div>
        <div class="hp-acts">${me.shared ? '<button type="button" class="hp-b sm" id="hpShare">Make a new link</button><button type="button" class="hp-b sm ghost danger" id="hpUnshare">Turn the link off</button>' : '<button type="button" class="hp-b sm" id="hpShare">Make a share link</button>'}</div>
        <div id="hpLink"></div></div>
      <div id="hpOffer"></div>`;
    offerRow().catch(() => null);
  }
  /* ---------- P11 BAHAR: the brief written for a tool outside Hoola (copy only) ---------- */
  async function outBox(target) {
    const el = $('#hpOutBox'); if (!el) return;
    const t = await api('GET', '/api/prompting/export/targets?section=' + encodeURIComponent(st.pack.brief.section));
    if (!(t.targets || []).length) { el.innerHTML = '<p class="hp-empty">Copying for other AI tools is switched off.</p>'; return; }
    target = target || st.outT || t.targets[0].key; st.outT = target;
    const x = await api('POST', '/api/prompting/export', {brief: st.pack.brief, target});
    st.outText = x.prompt;
    el.innerHTML = `<div class="hp-seg" role="group" aria-label="Other AI tool">${t.targets.map(o => `<button type="button" data-outt="${esc(o.key)}" aria-pressed="${o.key === target}">${esc(o.label)}</button>`).join('')}</div>
      <pre class="hp-pre" tabindex="0" id="hpOutPre">${esc(x.prompt)}</pre>
      <div class="hp-acts"><button type="button" class="hp-b sm pri" id="hpOutCopy">Copy for ${esc(x.label)}</button></div>
      <p class="hpi-note" style="font-size:12.5px;color:var(--dim)">${esc(x.note)}${(x.blanks || []).length ? esc(' Still empty: ' + x.blanks.join(', ') + '.') : ''}</p>`;
  }
  /* ---------- P11 SAMUDAAY: offer a saved prompt as a recipe for everyone (the owner approves each one) ---------- */
  async function offerRow() {
    const el = $('#hpOffer'); if (!el) return;
    const c = await api('GET', '/api/prompting/community');
    if (!c.on) { el.innerHTML = ''; return; }
    const me = (c.mine || []).find(x => x.title === (st.mine && st.mine.title) && x.status !== 'withdrawn');
    el.innerHTML = `<div class="hp-mrow col"><div><b>Offer as a recipe for everyone</b><span>${me ? esc('Offered as "' + me.title + '" - ' + ({submitted: 'waiting for review', approved: 'on the Recipes shelf', refused: 'not accepted: ' + me.reason}[me.status] || me.status) + '.')
        : 'Hoola reads it first. Your business details stay out; only the prompt\'s shape and words go to the shelf, under a name you choose.'}</span></div>
      ${me ? '' : `<form id="hpOfferF" class="hp-sched"><input name="by" maxlength="60" placeholder="Show my name as (optional)" aria-label="Name shown with the recipe"><button class="hp-b sm" type="submit">Offer it</button></form>`}</div>`;
  }
  async function communityBox() {
    const el = $('#hpComm'); if (!el) return;
    const c = await api('GET', '/api/prompting/community').catch(() => null);
    if (!c || (!c.on && !c.owner)) { el.innerHTML = ''; return; }
    const stl = {submitted: 'Waiting for review', approved: 'On the shelf', refused: 'Not accepted', withdrawn: 'Taken back'};
    const mineRows = (c.mine || []).filter(x => x.status !== 'withdrawn');
    el.innerHTML = `<h2 class="hp-sub2">Community recipes</h2>
      <p class="hp-lead">${c.on ? esc('Recipes people offered from their saved prompts. Each one is read by Hoola before it goes on the shelf. ' + c.note) : 'Switched off. People cannot offer recipes until the owner switches community recipes on.'}</p>
      ${mineRows.length ? `<h3 class="hp-sub3">Yours</h3><div class="hp-rows">${mineRows.map(x => `<div class="hp-rowi hp-wrapr"><div><b>${esc(x.title)}</b><span>${esc(stl[x.status] || x.status)}${x.kept ? esc(' · results kept ' + x.kept.kept + ' of ' + x.kept.of) : ''}${x.reason ? esc(' · ' + x.reason) : ''}</span></div>
        ${x.status === 'submitted' || x.status === 'approved' ? `<button type="button" class="hp-b sm ghost" data-cwd="${esc(x.id)}">Take back</button>` : ''}</div>`).join('')}</div>` : ''}
      ${c.owner && (c.review || []).length ? `<h3 class="hp-sub3">Waiting for your review</h3><div class="hp-rows">${c.review.map(x => `<div class="hp-rowi hp-wrapr"><div><b>${esc(x.title)} · ${esc(x.by)}</b><span>${esc(x.brief.intent || '')}</span>${(x.problems || []).length ? `<span>${esc('Cannot go on the shelf: ' + x.problems.join('; '))}</span>` : ''}${x.copy_of ? `<span class="hp-bad">${esc('Almost the same as "' + x.copy_of.title + '" (' + Math.round(x.copy_of.score * 100) + '% alike)')}</span>` : (x.similar || []).length ? `<span>${esc('Close to: ' + x.similar.map(y => y.title + ' (' + Math.round(y.score * 100) + '%)').join(', '))}</span>` : ''}</div>
        <button type="button" class="hp-b sm pri" data-cdec="${esc(x.id)}" data-act="approve" ${(x.problems || []).length ? 'disabled' : ''}>Approve</button><button type="button" class="hp-b sm ghost" data-cdec="${esc(x.id)}" data-act="refuse">Refuse</button></div>`).join('')}</div>` : ''}`;
  }
  /* ---------- P8 MUQABLA: this prompt (A) against another (B) ---------- */
  async function cmpStart() {
    const a = st.pack.brief, sec = UI.secOf(a.section);
    const saved = await api('GET', '/api/prompting/saved?section=' + encodeURIComponent(a.section)).catch(() => ({items: []}));
    st.cmp = {a, b: null, pr: null, quote: null, run: null, cid: '', pick: ''};
    shell(a.section, `<div class="hp-top"><a class="hp-b sm ghost" href="#/w">${ICON.back} Back to the prompt</a><h1>Compare</h1></div>
      <p class="hp-lead">A is the prompt you have open. Choose what to set it against. Comparing the two prompts is free.</p>
      <div class="hp-grid">
        <button type="button" class="hp-card" data-cmpb="raw"><b>Your words alone</b><span>What happens without the brief - just the line you wrote.</span></button>
        <div class="hp-card"><b>Another wording</b><span>Write the same ask another way.</span>
          <form id="hpCmpWords"><textarea class="hp-hers" name="t" rows="3" maxlength="2000" placeholder="${esc(PH[a.section] || '')}" required></textarea>
          <div class="hp-acts"><button class="hp-b sm" type="submit">Use as B</button></div></form></div>
        ${(saved.items || []).filter(x => x.id !== st.savedId).slice(0, 6).map(x => `<button type="button" class="hp-card" data-cmps="${esc(x.id)}"><b>${esc(x.title)}</b><span>A saved ${esc(sec.label.toLowerCase())} prompt</span></button>`).join('')}
      </div>`);
  }
  async function cmpShow() {
    const c = st.cmp;
    c.pr = await api('POST', '/api/prompting/compare', {a: c.a, b: c.b});
    const pr = c.pr, sec = UI.secOf(pr.section), srcLab = k => ({her_words: 'your words', her_memory: 'your business', her_answer: 'your answer', recipe: 'recipe', hoola_guess: "Hoola's suggestion"}[k] || '');
    const col = side => { const x = pr[side]; return `<div class="hp-pane hp-cmpcol"><div class="hp-cmph"><b>${side.toUpperCase()}</b><span class="hp-tag">Score ${esc(x.score.score)}</span></div>
        <pre class="hp-pre">${esc(x.out.prompt)}</pre><div id="hpRes_${side}" class="hp-res"></div></div>`; };
    shell(pr.section, `<div class="hp-top"><a class="hp-b sm ghost" href="#/c">${ICON.back} Choose B again</a><h1>Compare - ${esc(sec.label)}</h1></div>
      ${(pr.notes || []).map(n => `<p class="hp-lead">${esc(n)}</p>`).join('')}
      <div class="hp-cmp">${col('a')}${col('b')}</div>
      <div class="hp-rows">${pr.rows.filter(r => !r.same).map(r => `<div class="hp-rowi hp-wrapr"><div><b>${esc(r.label)}${r.required ? '' : ' (extra)'}</b>
        <span>A: ${esc(r.a || '- not given')}${r.a ? ' (' + esc(srcLab(r.a_source)) + ')' : ''}</span><span>B: ${esc(r.b || '- not given')}${r.b ? ' (' + esc(srcLab(r.b_source)) + ')' : ''}</span></div></div>`).join('') || '<p class="hp-empty">The two sides fill the same parts the same way.</p>'}</div>
      <div id="hpCmpRun" class="hp-mine"></div>`);
    cmpRunBox();
  }
  function cmpRunBox() {
    const c = st.cmp, el = $('#hpCmpRun'); if (!el) return;
    const pickRow = `<div class="hp-mrow col"><div><b>Which is better?</b><span>${c.run ? 'Judge the two results.' : 'Judge the two prompts.'} Your pick is kept (as shape, never your words) and teaches Hoola which kind of prompt works for you.</span></div>
      <div class="hp-acts">${c.pick ? `<span class="hp-tag">You picked ${c.pick === 'same' ? 'about the same' : c.pick.toUpperCase()}</span>`
        : '<button type="button" class="hp-b sm" data-pick="a">A is better</button><button type="button" class="hp-b sm" data-pick="b">B is better</button><button type="button" class="hp-b sm ghost" data-pick="same">About the same</button>'}</div></div>`;
    if (!c.pr.runnable) { el.innerHTML = `<h3>Run</h3><p class="hp-lead">${esc(c.pr.why_not)}</p>${pickRow}`; return; }
    if (c.run) { el.innerHTML = `<h3>Both ran</h3><p class="hp-lead">${esc(c.run.credits)} credits.</p>${pickRow}`; return; }
    el.innerHTML = c.quote ? `<h3>Price first</h3><p class="hp-lead">${esc(c.quote.say)}</p>
        <div class="hp-rows"><div class="hp-rowi"><div><b>A: ${esc(c.quote.a.credits)} credits</b><span>${esc(c.quote.a.basis)}</span></div></div>
          <div class="hp-rowi"><div><b>B: ${esc(c.quote.b.credits)} credits</b><span>${esc(c.quote.b.basis)}</span></div></div></div>
        <div class="hp-acts"><button type="button" class="hp-b pri" id="hpCmpGo">Run both for ${esc(c.quote.total)} credits</button></div>${pickRow}`
      : `<h3>Run both</h3><p class="hp-lead">See what each prompt really makes. You see the price before anything runs.</p>
        <div class="hp-acts"><button type="button" class="hp-b" id="hpCmpPrice">See the price</button></div>${pickRow}`;
  }
  async function cmpResults(r) {
    for (const side of ['a', 'b']) {
      const box = $('#hpRes_' + side); if (!box) continue;
      if (r[side].text != null) { box.innerHTML = `<h4>Result</h4><pre class="hp-pre">${esc(r[side].text)}</pre>`; continue; }
      box.innerHTML = '<p class="hp-lead">Making the picture…</p>';
      const jid = r[side].job.id;
      for (let i = 0; i < 90; i++) {
        const j = await api('GET', '/api/create/jobs/' + encodeURIComponent(jid)).catch(() => null);
        if (j && j.status === 'done' && (j.items || []).length) {
          const f = await fetch('/api/create/items/' + encodeURIComponent(j.items[0].id), {headers: {Authorization: 'Bearer ' + TOKEN}});
          box.innerHTML = `<img class="hp-resimg" alt="Result ${side.toUpperCase()}" src="${URL.createObjectURL(await f.blob())}">`; break; }
        if (j && j.status === 'failed') { box.innerHTML = `<p class="hp-bad">${esc(j.error || 'It could not be made.')}</p>`; break; }
        await new Promise(res => setTimeout(res, 2000));
      }
    }
  }
  async function history(id) {
    const [me, r] = await Promise.all([api('GET', '/api/prompting/saved/' + encodeURIComponent(id)), api('GET', `/api/prompting/saved/${encodeURIComponent(id)}/versions`)]);
    shell('saved', `<div class="hp-top"><a class="hp-b sm ghost" href="#/saved">${ICON.back} My prompts</a><h1>${esc(me.title)}</h1><span class="hp-sp"></span><span class="hp-tag">Version ${esc(me.version || 1)} now</span></div>
      <p class="hp-lead">Every saved change is kept. Bringing one back makes it a new version, so you can always go back again.</p>
      <div class="hp-rows">${(r.versions || []).map(v => `<div class="hp-rowi hp-wrapr"><div><b>Version ${esc(v.n)} · ${esc(v.note)}</b><span>${esc(new Date(v.at).toLocaleString())} - ${esc(v.prompt)}</span></div>
        ${v.n === me.version ? '<span class="hp-tag">Now</span>' : `<button type="button" class="hp-b sm" data-restore="${esc(v.n)}" data-pid="${esc(id)}">Bring this back</button>`}</div>`).join('')}</div>`);
  }
  async function openSaved(id) {
    const r = await api('GET', '/api/prompting/saved/' + encodeURIComponent(id));
    if (!r.out) { toast('This saved prompt could not be opened.', true); return; }
    st.savedId = r.id; st.text = r.brief.intent;
    if ((r.ask || []).length) { st.fill = r; go('#/f'); return; }
    st.pack = {brief: r.brief, score: r.score, out: r.out, source_labels: r.source_labels}; go('#/w');
  }
  function fillForm() {
    const r = st.fill, sec = UI.secOf(r.section);
    shell('saved', `<div class="hp-top"><a class="hp-b sm ghost" href="#/saved">${ICON.back} My prompts</a><h1>${esc(r.title)}</h1></div>
      <p class="hp-lead">Fill in this time's details. Your saved prompt stays as it is.</p>
      <form id="hpFillSaved" class="hp-form">${r.ask.map(k => { const x = sec.slots.find(z => z.key === k) || {label: k, q: ''};
        const cur = ((r.brief.slots || {})[k] || {}).value || '';
        return `<label class="hp-f"><span>${esc(x.label)}</span><input name="${esc(k)}" value="${esc(cur)}" placeholder="${esc(x.eg || x.q || '')}" maxlength="400" required></label>`; }).join('')}
        <div class="hp-acts"><button class="hp-b pri" type="submit">Use these</button></div></form>`);
    const f = $('#hpFillSaved input'); if (f) f.focus();
  }
  async function sharedView(token) {
    const r = await api('GET', '/api/prompting/shared/' + encodeURIComponent(token));
    const sec = UI.secOf(r.section);
    shell('saved', `<div class="hp-top"><h1>${esc(r.title)}</h1><span class="hp-sp"></span><span class="hp-tag">${esc(sec.label)}</span><span class="hp-tag">Shared with you</span></div>
      <p class="hp-lead">A prompt someone shared with you. Save a copy to use it as your own; nothing runs from here.</p>
      <pre class="hp-pre">${esc(r.prompt)}</pre>
      ${(r.problems || []).length ? `<p class="hp-bad">This prompt cannot be copied: ${esc(r.problems.join('; '))}.</p>`
        : `<div class="hp-acts"><button type="button" class="hp-b pri" id="hpCopyShared" data-token="${esc(token)}">Save a copy to My prompts</button></div>`}`);
  }
  async function understand(text, section, keep, pasted) {
    text = String(text || '').trim();
    if (text.length < 3) { toast('Write one line about what you want to make.', true); return; }
    if (!keep && !pasted) {
      const pb = await api('POST', '/api/prompting/paste', {text}).catch(() => null);
      if (pb && (pb.blanks || []).length) { st.paste = {text, section, blanks: pb.blanks}; go('#/pb'); return; }
    }
    st.text = text;
    const btn = document.querySelector('#hpAsk [type=submit], #hpAgain'); if (btn) { btn.disabled = true; btn.textContent = 'Reading…'; }
    try {
      const pack = await api('POST', '/api/prompting/understand', {text, section: section || ''});
      if (pack.choose_section) { toast('Pick a category so Hoola knows what you are making.'); openPick(true); if (btn) { btn.disabled = false; btn.innerHTML = 'Make my prompt ' + ARROW; } return; }
      st.pack = pack; if (!keep) st.savedId = '';   // re-reading a SAVED prompt's words keeps it the same saved prompt (P7: a new version)
      go('#/w');
    } catch (e) { toast(e.message, true); if (btn) { btn.disabled = false; if (btn.id === 'hpAgain') btn.textContent = 'Read my words again'; else btn.innerHTML = 'Make my prompt ' + ARROW; } }
  }
  /* NATIJA KHATA: tell the ledger a prompt was taken out (shape only). Never blocks her. */
  function hand(how) {
    const rd = location.hash === '#/ready';
    const body = rd ? {text: st.ready.run.text || st.ready.prompt, section: 'web', recipe_id: st.ready.id || '', how}
      : {text: how === 'copy' ? st.pack.out.prompt : (st.pack.out.run.text || st.pack.out.prompt), brief: st.pack.brief, how};
    return api('POST', '/api/prompting/runs', {...body, origin: 'page'}).catch(() => null);
  }
  function run(r) {
    const dest = RUN[r.to] || ['hoola.flow.toChat', '/console/'];
    if (r.to === 'code') { location.assign(dest[1] + '?prompt=' + encodeURIComponent(String(r.text || '').slice(0, 6000))); return; }
    try { localStorage.setItem(dest[0], String(r.text || '')); }
    catch (e) { toast('This browser could not hand the text over. Use Copy.', true); return; }
    location.assign(dest[1]);
  }
  async function copy(text) {
    try { await navigator.clipboard.writeText(text); toast('Copied.'); }
    catch (e) { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); toast('Copied.'); } catch (er) { toast('Could not copy. Select the text and copy it.', true); } t.remove(); }
  }

  /* ---------- recipes ---------- */
  const shelfSeg = () => `<span class="hp-seg" role="group" aria-label="Shelf">${[['hoola', "Hoola's starters"], ['world', 'World prompts library']].map(([k, l]) => `<button type="button" data-shelf="${k}" aria-pressed="${st.shelf === k}">${l}</button>`).join('')}</span>`;
  async function recipes() {
    if (st.shelf === 'world') { st.shelf = 'hoola'; go('#/library'); return; }
    const r = await api('GET', `/api/prompting/recipes?section=${encodeURIComponent(st.rsec)}&q=${encodeURIComponent(st.q)}`).catch(e => { toast(e.message, true); return {items: []}; });
    shell('recipes', `<div class="hp-top"><h1>Hoola's starters</h1><span class="hp-sp"></span>${shelfSeg()}</div>
      <form class="hp-find" id="hpFind"><input type="search" id="hpQ" value="${esc(st.q)}" placeholder="Search: poster, reel, salon, Diwali, bakery…" aria-label="Search recipes">
        <span class="hp-seg" role="group" aria-label="Kind">${[['', 'All'], ...st.secs.map(s => [s.key, s.label])].map(([k, l]) => `<button type="button" data-rsec="${esc(k)}" aria-pressed="${st.rsec === k}">${esc(l)}</button>`).join('')}</span>
        <button class="hp-b" type="submit">Search</button></form>
      <div class="hp-grid">${cards(r.items || []) || '<p class="hp-empty">Nothing matches. Try one word, like "poster" or "reel".</p>'}</div>
      <p style="margin-top:16px;color:var(--dim);font-size:13px">These are starting points written by Hoola. Once enough people have used a recipe, the ones whose results were kept come first, with the count. Every recipe also has a public page at <a href="/prompts" target="_blank" rel="noopener">/prompts</a>.</p>
      <div id="hpComm"></div>`);
    communityBox().catch(() => null);
  }
  /* ---------- the Ready prompt library: every prompts.chat prompt (CC0), by its own categories ---------- */
  const ini = n => (String(n || '?').trim().charAt(0) || '?').toUpperCase();
  function libCard(c) {
    const m = c.media, tag = esc(c.kind_label || 'Text');
    const top = m && m.type !== 'audio'
      ? `<span class="hl-media${m.type === 'video' ? ' vid' : ''}"><img loading="lazy" decoding="async" src="${esc(m.thumb)}" alt=""><span class="hl-kind">${tag}</span>${m.type === 'video' ? `<span class="hl-play">${PLAY}Video</span>` : ''}</span>`
      : m ? `<span class="hl-media snd">${SOUND}<span class="hl-kind">${tag}</span></span>`
      : `<span class="hl-quote"><span class="hl-kind">${tag}</span><span class="hl-q">${esc(c.excerpt || '')}</span></span>`;
    return `<button type="button" class="hp-card hl-card" data-recipe="${esc(c.id)}">${top}<span class="hl-body"><span class="hl-cat">${esc(c.group_label)}</span>
        <b>${esc(c.title)}</b>${c.desc ? `<span class="hl-desc">${esc(c.desc)}</span>` : ''}
        <span class="hl-meta"><span class="hl-av" aria-hidden="true">${esc(ini(c.name || c.by))}</span><span class="hl-by">${esc(c.name || c.by || 'prompts.chat')}</span>
          ${c.safety ? '<span class="hp-tag hp-warn">Copy only</span>' : c.use === 'fill' ? '<span class="hp-tag hp-long">Long</span>' : ''}
          ${c.votes ? `<span class="hl-votes" aria-label="${esc(c.votes)} likes">${HEART}${esc(c.votes)}</span>` : ''}</span></span></button>`;
  }
  const libQuery = page => `/api/prompting/world?q=${encodeURIComponent(st.wq)}&group=${encodeURIComponent(st.wgroup)}&family=${encodeURIComponent(st.wfam || '')}&kind=${encodeURIComponent(st.wkind || '')}&sort=${encodeURIComponent(st.wsort || 'loved')}&page=${page}&per=24`;
  async function library(el) {
    if (!el) return;
    st.libEl = '#' + el.id;
    const r = await api('GET', libQuery(1)).catch(e => { toast(e.message, true); return {items: [], families: [], kinds: []}; });
    st.wpage = 1; st.wlast = r;
    if (r.on === false) { el.innerHTML = '<p class="hp-empty">The prompt library is switched off.</p>'; return; }
    const fams = r.families || [], cat = st.wgroup ? catOf(st.wgroup) : null, fam = fams.find(f => f.key === st.wfam);
    const ncat = fams.reduce((a, f) => a + f.cats.length, 0);
    const title = st.wq ? `Results for “${st.wq}”` : cat ? cat.label : fam ? fam.label : {new: 'Newest prompts', media: 'With pictures and videos first'}[st.wsort] || 'Most loved prompts';
    el.innerHTML = `<div class="hl-head"><div class="hl-hl"><h2>Ready prompt library</h2>
          <p>${fmt(r.all)} prompts written by people around the world, in ${ncat} categories and many languages. Free to use, from <a href="${esc((r.source || {}).url || 'https://prompts.chat')}" target="_blank" rel="noopener">prompts.chat</a> (CC0).</p></div>
        <form class="hl-find" id="hpWFind" role="search"><label class="hl-search">${SEARCH}<span class="hp-lab" style="position:absolute;left:-9999px">Search prompts</span>
            <input type="search" id="hpWQ" value="${esc(st.wq)}" placeholder="Search ${fmt(r.all)} prompts" aria-label="Search prompts"></label>
          <select id="hpWSort" aria-label="Order">${[['loved', 'Most loved'], ['media', 'Pictures and videos first'], ['new', 'Newest']].map(([k, l]) => `<option value="${k}"${(st.wsort || 'loved') === k ? ' selected' : ''}>${l}</option>`).join('')}</select>
          <button class="hp-b" type="submit">Search</button></form></div>
      <div class="hl-kinds" role="group" aria-label="Kind">${[{key: '', label: 'All', n: r.all}, ...(r.kinds || [])].map(k => `<button type="button" data-wkind="${esc(k.key)}" aria-pressed="${(st.wkind || '') === k.key}">${esc(k.label)} <span>${fmt(k.n)}</span></button>`).join('')}</div>
      <div class="hl-cols"><aside class="hl-rail" aria-label="Categories">
          <button type="button" data-wfam="" data-wgroup="" aria-pressed="${!st.wfam && !st.wgroup}">All prompts <span>${fmt(r.all)}</span></button>
          ${fams.map(f => `<button type="button" class="hl-fam" data-wfam="${esc(f.key)}" data-wgroup="" aria-pressed="${st.wfam === f.key && !st.wgroup}" aria-expanded="${st.wfam === f.key}">${esc(f.label)} <span>${fmt(f.total)}</span></button>
            ${st.wfam === f.key ? `<div class="hl-sub">${f.cats.map(c => `<button type="button" data-wfam="${esc(f.key)}" data-wgroup="${esc(c.key)}" aria-pressed="${st.wgroup === c.key}">${esc(c.label)} <span>${fmt(c.n)}</span></button>`).join('')}</div>` : ''}`).join('')}
        </aside>
        <div class="hl-main"><div class="hl-sum"><h3>${esc(title)}</h3><span id="hlCount">Showing ${fmt(Math.min(24, r.total))} of ${fmt(r.total)}</span></div>
          <div class="hl-grid" id="hlGrid">${(r.items || []).map(libCard).join('') || '<p class="hp-empty">Nothing matches. Try one word, like “interview” or “poster”.</p>'}</div>
          ${(r.pages || 1) > 1 ? '<div class="hl-more"><button type="button" class="hp-b" id="hpWMore">Show more prompts</button></div>' : ''}
          <p class="hl-foot">Pictures and videos are the ones each author made with their prompt. Prompts that Hoola's checks flag are marked “Copy only”: you can read and copy them, but Hoola does not run them.</p></div></div>`;
  }
  async function libMore(b) {
    b.disabled = true; b.textContent = 'Loading…';
    try { const r = await api('GET', libQuery(st.wpage + 1)); st.wpage = r.page;
      $('#hlGrid').insertAdjacentHTML('beforeend', (r.items || []).map(libCard).join(''));
      $('#hlCount').textContent = `Showing ${fmt(Math.min(st.wpage * 24, r.total))} of ${fmt(r.total)}`;
      if (st.wpage >= (r.pages || 1)) b.parentNode.remove(); else { b.disabled = false; b.textContent = 'Show more prompts'; }
    } catch (e) { toast(e.message, true); b.disabled = false; b.textContent = 'Show more prompts'; }
  }
  async function libPage() { await lib0(); shell('library', '<section class="hl hl-page" id="hpLib" aria-label="Ready prompt library"></section>'); await library($('#hpLib')); }
  async function worldShelf() { const el = st.libEl && $(st.libEl); if (el) await library(el); else await libPage(); }
  function bigMedia(m, title) {
    if (!m) return '';
    const body = m.type === 'video' ? `<video src="${esc(m.full)}" poster="${esc(m.thumb)}" controls muted autoplay loop playsinline preload="metadata" aria-label="${esc(title)}"></video>`
      : m.type === 'audio' ? `<div class="hd-snd">${SOUND}<audio src="${esc(m.full)}" controls preload="none"></audio></div>`
      : `<img src="${esc(m.full)}" alt="${esc(title)}">`;
    return `<figure class="hd-media${m.type === 'video' ? ' vid' : ''}">${body}<figcaption>The author's own result with this prompt, as shared on prompts.chat.</figcaption></figure>`;
  }
  async function openWorld(id) {
    await lib0();
    const r = await api('GET', '/api/prompting/world/' + encodeURIComponent(id));
    st.recipe = r; st.wfill = null; st.adapted = null;
    const fam = ((st.lib0 || {}).families || []).find(f => f.key === r.family);
    const btn = r.use === 'workbench' ? (r.blanks.length ? 'Fill it in and open' : 'Use this prompt') : 'Fill it in';
    const ol = r.outline || {parts: []};
    const date = r.created ? new Date(r.created + 'T00:00:00Z').toLocaleDateString('en', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC'}) : '';
    const say = {image: 'Change it, e.g. make it a winter scene in Oslo', video: 'Change it, e.g. Romans in Rome instead, and 15 seconds'}[r.kind] || 'Change it, e.g. for a small bakery, and shorter';
    shell('library', `<nav class="hl-crumb" aria-label="Where you are"><a href="#/library">Ready prompt library</a>${I('<path d="M9 6l6 6-6 6"/>')}
        ${fam ? `<button type="button" class="hp-link" data-wfam="${esc(fam.key)}" data-wgroup="" data-wgo="1">${esc(fam.label)}</button>${I('<path d="M9 6l6 6-6 6"/>')}` : ''}
        <button type="button" class="hp-link" data-wfam="${esc(r.family)}" data-wgroup="${esc(r.group)}" data-wgo="1">${esc(r.group_label)}</button></nav>
      <div class="hd${r.media ? '' : ' nomedia'}">${bigMedia(r.media, r.title)}
          <section class="hd-prompt" aria-label="The prompt"><div class="hd-ph"><h2>The prompt</h2><span>${fmt(r.chars)} characters${ol.parts.length ? ' · ' + ol.parts.length + ' parts' : ''}</span></div>
            ${ol.parts.length ? `${ol.lead ? `<p class="hd-lead">${esc(ol.lead)}</p>` : ''}${ol.parts.map(p => `<div class="hd-sec"><h4>${esc(p.head)}</h4><p>${esc(p.first)}</p></div>`).join('')}
              <details class="hd-all"><summary>Show the whole prompt</summary><pre class="hp-pre" tabindex="0" id="hpWText">${esc(r.text)}</pre></details>`
              : `<pre class="hp-pre" tabindex="0" id="hpWText">${esc(r.text)}</pre>`}
          </section>
        <aside class="hd-side" aria-label="About this prompt"><div class="hd-kind">${esc(r.kind_label)} · ${esc(r.group_label)}</div>
          <h1>${esc(r.title)}</h1>
          <div class="hd-by"><span class="hl-av lg" aria-hidden="true">${esc(ini(r.name || r.by))}</span><div><b>${esc(r.name || r.by || 'prompts.chat')}</b><span>on prompts.chat${date ? ' · ' + esc(date) : ''}</span></div>
            ${r.votes ? `<span class="hl-votes" aria-label="${esc(r.votes)} likes">${HEART}${esc(r.votes)}</span>` : ''}</div>
          ${r.desc ? `<p class="hd-desc">${esc(r.desc)}</p>` : ''}
          ${(r.tags || []).length ? `<div class="hd-tags">${r.tags.map(t => `<span>${esc(t)}</span>`).join('')}</div>` : ''}
          ${r.notes.length ? `<p class="hp-wnotes${r.safety ? ' hp-warn' : ''}">${r.safety ? "Hoola's checks flagged this prompt, so Hoola does not run it. You can still read and copy it. " : ''}Notes: ${esc(r.notes.join(' · '))}.</p>` : ''}
          ${r.needs ? `<p class="hp-wnotes">This prompt starts from your own ${esc(r.needs)}: add it in the tool you use it in.</p>` : ''}
          <div class="hd-box"><form class="hp-form" id="hpFill">${r.blanks.length ? `<p class="hd-fillh">Fill what you know. The example is the author's and is not used unless you type it.</p>
              ${r.blanks.map(b => `<div><label for="bl_${esc(b.key)}">${esc(b.label)}</label><input id="bl_${esc(b.key)}" name="${esc(b.key)}" maxlength="120" placeholder="${esc(b.eg ? 'for example: ' + b.eg : '')}" autocomplete="off"></div>`).join('')}` : ''}
              <div class="hd-acts">${r.use === 'workbench' || r.blanks.length ? `<button class="hp-b pri lg" type="submit">${btn} ${ARROW}</button>` : ''}
                <button type="button" class="hp-b" id="hpWCopy">Copy</button>${r.use !== 'copy' ? '<button type="button" class="hp-b" id="hpWChat">Put in the Hoola chat</button>' : ''}</div></form>
            ${r.use !== 'copy' ? `<form class="hd-mine" id="hpAdapt"><label for="hpAdaptQ">Make it yours</label><p>Say what to change. Hoola rewrites it and keeps the rest.</p>
              <div class="hd-minerow"><input id="hpAdaptQ" maxlength="300" placeholder="${esc(say)}" autocomplete="off"><button class="hp-b acc" type="submit" aria-label="Rewrite it">${ARROW}</button></div></form><div id="hpAdapted" aria-live="polite"></div>` : ''}</div>
          <p class="hd-src">A prompt from <a href="https://prompts.chat" target="_blank" rel="noopener">prompts.chat</a>${r.by ? esc(' by ' + (r.name || r.by)) : ''}, public domain (CC0).${r.use === 'workbench' ? ' It opens in your workbench, where Hoola scores it and writes it for the tool.' : r.use === 'fill' ? ' It is longer than a brief: fill it here, then copy it or put it in your Hoola chat.' : ''}</p>
        </aside></div>
      <section class="hd-more" aria-label="More like this"><div class="hp-catsh"><h2>More ${esc(r.group_label)} prompts</h2><button type="button" class="hp-link" data-wfam="${esc(r.family)}" data-wgroup="${esc(r.group)}" data-wgo="1">See all ${ARROW}</button></div><div class="hl-row" id="hpMore"></div></section>`);
    const more = await api('GET', `/api/prompting/world?group=${encodeURIComponent(r.group)}&sort=media&per=11`).catch(() => ({items: []}));
    const box = $('#hpMore'); if (box) box.innerHTML = (more.items || []).filter(x => x.id !== r.id).slice(0, 10).map(libCard).join('') || '<p class="hp-empty">No other prompts in this category.</p>';
  }
  async function adapt(change) {
    const v = {}; document.querySelectorAll('#hpFill input').forEach(i => { v[i.name] = i.value.trim(); });
    const box = $('#hpAdapted'), b = $('#hpAdapt [type=submit]'); b.disabled = true; box.innerHTML = '<p class="hd-wait">Hoola is rewriting it…</p>';
    try { const r = await api('POST', '/api/prompting/world/' + encodeURIComponent(st.recipe.id) + '/adapt', {change, values: v});
      st.adapted = r;
      box.innerHTML = `<div class="hd-new"><div class="hd-ph"><h3>Your version</h3><span>${fmt(r.chars)} characters</span></div><pre class="hp-pre" tabindex="0">${esc(r.text)}</pre>
        <div class="hd-acts">${r.fits_brief ? `<button type="button" class="hp-b pri" data-awb="1">Open in the workbench ${ARROW}</button>` : ''}<button type="button" class="hp-b" data-acopy="1">Copy</button><button type="button" class="hp-b" data-achat="1">Put in the Hoola chat</button></div></div>`;
    } catch (e) { box.innerHTML = `<p class="hp-bad">${esc(e.message)}</p>`; }
    b.disabled = false;
  }
  function openPick(open) {
    const pop = $('#hpPop'), b = $('#hpPick'); if (!pop || !b) return;
    const show = open === undefined ? pop.hidden : open; pop.hidden = !show; b.setAttribute('aria-expanded', String(show));
    if (show) { const first = pop.querySelector('button'); if (first) first.focus(); }
  }
  async function worldFilled() {
    const v = {}; document.querySelectorAll('#hpFill input').forEach(i => { v[i.name] = i.value.trim(); });
    const got = await api('POST', '/api/prompting/world/' + encodeURIComponent(st.recipe.id) + '/fill', {values: v});
    st.wfill = got.text; const pre = $('#hpWText'); if (pre) pre.textContent = got.text;
    return got.text;
  }
  /* ---------- paste reader: blanks in a prompt she pasted ---------- */
  function pasteForm() {
    const p = st.paste;
    shell(p.section || 'home', `<div class="hp-top"><a class="hp-b sm ghost" href="#/">${ICON.back} Back</a><h1>Your prompt has blanks</h1></div>
      <p class="hp-lead">The text you pasted has ${esc(p.blanks.length)} blank${p.blanks.length === 1 ? '' : 's'} to fill. Fill what you know; anything you leave empty stays in the prompt as an open part, never a made-up value.</p>
      <form class="hp-form" id="hpPaste">${p.blanks.map(b => `<div><label for="pb_${esc(b.key)}">${esc(b.label)}</label><input id="pb_${esc(b.key)}" name="${esc(b.key)}" maxlength="120" placeholder="${esc(b.eg ? 'for example: ' + b.eg : '')}" autocomplete="off"></div>`).join('')}
        <div class="hp-acts"><button class="hp-b pri" type="submit">Put these in</button><button type="button" class="hp-b ghost" id="hpPasteSkip">Use my words as they are</button></div></form>`);
    $('#hpPaste input')?.focus();
  }
  async function openRecipe(id) {
    if (id.startsWith('world:')) return openWorld(id);
    const list = await api('GET', '/api/prompting/recipes?section=' + (id.startsWith('web:') ? 'web' : '') + '&q=' + (id.startsWith('web:') ? encodeURIComponent(st.q) : '')).catch(() => ({items: []}));
    const r = (list.items || []).find(x => x.id === id) || {id, title: 'Recipe', blanks: []};
    if (!r.blanks || !r.blanks.length) return useRecipe(id, {});
    st.recipe = r;
    shell('recipes', `<div class="hp-top"><a class="hp-b sm ghost" href="#/recipes">${ICON.back} Recipes</a><h1>${esc(r.title)}</h1></div>
      <form class="hp-form" id="hpFill"><p style="color:var(--mut)">${esc(r.makes || '')}. Fill what you know - anything you leave empty becomes a question, never a made-up value.</p>
        ${r.blanks.map(b => `<div><label for="bl_${esc(b.key)}">${esc(b.label)}</label><input id="bl_${esc(b.key)}" name="${esc(b.key)}" maxlength="120" placeholder="${esc(b.eg || '')}" autocomplete="off"></div>`).join('')}
        <div><button class="hp-b pri" type="submit">Make my prompt</button></div></form>`);
    $('#hpFill input')?.focus();
  }
  async function useRecipe(id, values) {
    try {
      const got = await api('POST', '/api/prompting/recipes/use', {recipe_id: id, values});
      if (got.ready) { st.ready = {...got.ready, id}; go('#/ready'); return; }
      st.pack = got; st.savedId = ''; st.text = got.brief.intent; go('#/w');
    } catch (e) { toast(e.message, true); }
  }
  function ready() {
    const r = st.ready;
    shell('recipes', `<div class="hp-top"><a class="hp-b sm ghost" href="#/recipes">${ICON.back} Recipes</a><h1>${esc(r.title)}</h1><span class="hp-tag">Website template</span></div>
      <pre class="hp-pre" tabindex="0">${esc(r.prompt)}</pre>
      <div class="hp-acts"><button type="button" class="hp-b pri" id="hpRun">${esc(r.run.label)}</button><button type="button" class="hp-b" id="hpCopy">Copy</button></div>
      <p style="margin-top:10px;color:var(--dim);font-size:13px">A complete website prompt from the Web Studio library. The name is a working name you can change there.</p>`);
  }

  /* ---------- my prompts ---------- */
  async function saved() {
    const r = await api('GET', '/api/prompting/saved').catch(e => { toast(e.message, true); return {items: []}; });
    shell('saved', `<div class="hp-top"><h1>My prompts</h1><span class="hp-tag">${(r.items || []).length} saved</span></div>
      ${(r.items || []).length ? `<div class="hp-rows">${rows(r.items)}</div>` : '<p class="hp-empty">Nothing saved yet. Make a prompt and press Save to keep it here.</p>'}`);
  }

  /* ---------- results: the ledger (NATIJA KHATA) ---------- */
  const GRADE = {kept: 'Kept', kept_after_edit: 'Kept after an edit', redone: 'Redone', dropped: 'Dropped', unused: 'Never used'};
  function runState(r) {
    if (r.grade) return GRADE[r.grade] + (r.grade.startsWith('kept') && !r.by_her ? ' (still there after 3 days)' : '');
    return {handed: r.how === 'copy' ? 'Copied out of Hoola' : 'Not run yet', running: 'Being made', ready: 'Made - waiting to see what you do with it', settled: 'Closed'}[r.status] || r.status;
  }
  function four(n) {
    const v = (x, unit) => x === null || x === undefined ? '<b class="hp-na">-</b>' : `<b>${esc(String(x))}${unit || ''}</b>`;
    return `<div class="hp-four">
      <div><span>Kept rate</span>${v(n.kept_rate, '%')}<small>${n.kept} kept of ${n.graded} judged</small></div>
      <div><span>Redos for each kept result</span>${v(n.redos_per_kept)}<small>${n.redone} redone</small></div>
      <div><span>Rupees for each kept result</span>${v(n.inr_per_kept === null || n.inr_per_kept === undefined ? null : 'Rs ' + n.inr_per_kept)}<small>AI list price, not a bill</small></div>
      <div><span>Minutes to a kept result</span>${v(n.minutes_to_kept)}<small>from taking the prompt to keeping the result</small></div></div>
      ${n.enough ? '' : `<p class="hp-empty">Numbers appear after ${n.min_runs} results have been judged. So far: ${n.graded}. ${n.open ? n.open + ' still open.' : ''}</p>`}`;
  }
  async function results() {
    const r = await api('GET', '/api/prompting/ledger' + (st.everyone ? '?everyone=1' : ''));
    const n = r.numbers, lab = k => (st.secs.find(s => s.key === k) || {label: k}).label;
    shell('results', `<div class="hp-top"><h1>Results</h1><span class="hp-tag">last ${n.days} days</span>
        ${r.owner ? `<span class="hp-seg" role="group" aria-label="Whose numbers"><button type="button" data-who="" aria-pressed="${!st.everyone}">Mine</button><button type="button" data-who="1" aria-pressed="${!!st.everyone}">All users who share</button></span>` : ''}</div>
      <p class="hp-lead">What happened to the results of the prompts you took from here. This is how Hoola Prompting is judged.</p>
      ${four(n.all)}
      <h2 class="hp-sub2">By kind</h2>
      <div class="hp-rows">${Object.keys(n.sections).map(k => { const s = n.sections[k]; return `<div class="hp-rowi hp-wrapr"><div><b>${esc(lab(k))}</b>
          <span>${s.enough ? `${s.kept_rate}% kept (${s.kept} of ${s.graded})` : `${s.graded} judged so far - numbers after ${s.min_runs}`} · ${s.redone} redone · ${s.dropped} dropped · ${s.unused} never used</span>
          <span>Prompt Score check: ${esc(s.score_check.say)}</span></div></div>`; }).join('')}</div>
      ${st.everyone ? '' : `<h2 class="hp-sub2">Your recent prompts</h2>
      ${(r.recent || []).length ? `<div class="hp-rows">${r.recent.map(x => `<div class="hp-rowi hp-wrapr"><div><b>${esc(lab(x.section))}${x.recipe ? ' · from a recipe' : ''} · score ${x.score || '-'}</b>
          <span>${esc(runState(x))}${x.edited_before ? ' · you changed the prompt before running it' : ''}${x.edits ? ` · ${x.edits} change${x.edits > 1 ? 's' : ''} to the result` : ''}${x.inr ? ` · Rs ${x.inr}` : ''} · ${esc(new Date(x.at).toLocaleString())}</span></div>
          <button type="button" class="hp-b sm${x.thumb === 'up' ? ' pri' : ''}" data-thumb="up" data-run="${esc(x.id)}" aria-pressed="${x.thumb === 'up'}">Good result</button>
          <button type="button" class="hp-b sm${x.thumb === 'down' ? ' danger' : ''}" data-thumb="down" data-run="${esc(x.id)}" aria-pressed="${x.thumb === 'down'}">Not right</button></div>`).join('')}</div>`
        : '<p class="hp-empty">Nothing yet. Make a prompt and press its Open or Use button; what you do with the result shows here.</p>'}
      <h2 class="hp-sub2">What is kept about your prompts</h2>
      <p class="hp-lead">Only the shape: the kind, the recipe, which details were filled, the score and what happened to the result. Your words, prices, names and numbers are not stored here. Nothing is written from an incognito chat.</p>
      <div class="hp-acts"><label class="hp-sw"><input type="checkbox" id="hpLedger" ${r.prefs.ledger ? 'checked' : ''}> Keep this record for me</label>
        <label class="hp-sw"><input type="checkbox" id="hpShare" ${r.prefs.share ? 'checked' : ''}> Let my results (shape only) help order recipes for everyone</label>
        <button type="button" class="hp-b sm danger" id="hpForget">Delete my record</button></div>`}
      <p style="margin-top:16px;color:var(--dim);font-size:13px">${esc(n.note)}</p>
      ${st.everyone ? '' : '<div id="hpUsual"></div>'}${r.owner ? '<div id="hpKhud"></div><div id="hpProof"></div>' : ''}`);
    if (!st.everyone) usualBox().catch(() => null);
    if (r.owner) { khudBox().catch(e => toast(e.message, true)); proofBox().catch(() => null); }
  }

  /* ---------- P12 PROOF: does Hoola's own brief beat her raw line (owner) ---------- */
  async function proofBox() {
    const el = $('#hpProof'); if (!el) return;
    const p = await api('GET', '/api/prompting/proof'), f = p.free || {}, u = p.users || {};
    const pc = x => x == null ? '-' : Math.round(x * 100) + '%';
    el.innerHTML = `<h2 class="hp-sub2">Proof</h2>
      <p class="hp-lead">How much of what a perfect prompt adds Hoola's own brief already has - from the fixed test asks, words only, no engine run. The live run puts every version through the real engines: <code>python -m app.quality prompt proof --live --budget-inr N</code>.</p>
      <div class="hp-rows">${Object.entries(f.sections || {}).map(([s, d]) => `<div class="hp-rowi hp-wrapr"><div><b>${esc(s === 'web' ? 'Web design' : 'Script')}</b><span>${esc('Must-have items in the prompt: her words ' + pc(d.raw) + ', Hoola\'s brief ' + pc(d.hoola) + ', a perfect brief ' + pc(d.hand) + '. Questions still asked: ' + d.questions_left + '.')}</span></div>${d.share_of_ceiling != null ? `<span class="hp-tag">${esc(pc(d.share_of_ceiling) + ' of the gap')}</span>` : ''}</div>`).join('')}</div>
      <p class="hp-lead">${esc((u.have || 0) + ' of ' + (u.want || 10) + ' users have enough judged results for a before / after.')}</p>
      ${(u.users || []).length ? `<div class="hp-rows">${u.users.map(x => `<div class="hp-rowi hp-wrapr"><div><b>${esc(x.user)}</b><span>${esc('Kept ' + (x.before.kept_rate ?? '-') + '% -> ' + (x.after.kept_rate ?? '-') + '%')}</span></div></div>`).join('')}</div>` : ''}
      ${p.live ? `<p class="hp-lead">${esc('Last live run: ' + p.live.file)}</p>` : '<p class="hp-lead">No live run yet.</p>'}`;
  }
  /* ---------- P10 KHUD SEEKHE: Hoola improving itself (owner) + her own usual choices ---------- */
  async function usualBox() {
    const el = $('#hpUsual'); if (!el) return;
    const r = await api('GET', '/api/prompting/usual');
    const list = (r.usual || []).filter(u => u.status !== 'declined');
    el.innerHTML = list.length ? `<h2 class="hp-sub2">Your usual choices</h2>
      <p class="hp-lead">You picked these again and again. Turn one on and new prompts start with it, marked "your usual choice"; you can still change it.</p>
      <div class="hp-rows">${list.map(u => `<div class="hp-rowi hp-wrapr"><div><b>${esc(u.what)}</b><span>${u.status === 'on' ? 'On' : 'Not on yet'}</span></div>
        ${u.status === 'on' ? `<button type="button" class="hp-b sm" data-usual="${esc(u.id)}" data-on="0">Turn off</button>`
          : `<button type="button" class="hp-b sm pri" data-usual="${esc(u.id)}" data-on="1">Turn on</button><button type="button" class="hp-b sm ghost" data-usual="${esc(u.id)}" data-on="0">No thanks</button>`}</div>`).join('')}</div>` : '';
  }
  const KH_STATE = {proposed: 'Proposed', accepted: 'In use', refused: 'Refused', undone: 'Undone', dismissed: 'Seen'};
  async function khudBox() {
    const el = $('#hpKhud'); if (!el) return;
    const r = await api('GET', '/api/prompting/khud'), rl = r.rules || {};
    const open = (r.changes || []).filter(c => c.status === 'proposed'), rest = (r.changes || []).filter(c => c.status !== 'proposed').slice(0, 20);
    const row = c => `<div class="hp-rowi hp-wrapr"><div><b>${esc(c.what)}</b><span>${esc(c.evidence)}</span>${c.reason ? `<span>${esc(c.reason)}</span>` : ''}</div>
      <span class="hp-tag">${esc(KH_STATE[c.status] || c.status)}</span>
      ${c.status === 'proposed' ? (c.kind === 'alert' ? `<button type="button" class="hp-b sm" data-khud="${esc(c.id)}" data-act="dismiss">Seen</button>`
        : `<button type="button" class="hp-b sm pri" data-khud="${esc(c.id)}" data-act="accept">Accept</button><button type="button" class="hp-b sm ghost" data-khud="${esc(c.id)}" data-act="refuse">Refuse</button>`)
        : c.status === 'accepted' ? `<button type="button" class="hp-b sm ghost" data-khud="${esc(c.id)}" data-act="undo">Undo</button>` : ''}</div>`;
    el.innerHTML = `<h2 class="hp-sub2">Hoola improving itself</h2>
      <p class="hp-lead">Changes Hoola found in the results of everyone who shares. A change is offered only with ${esc(rl.min_each_side)} judged results on each side and a gain of at least ${esc(rl.gain_points)} points (or, to stop asking a question, a difference under ${esc(rl.same_points)}). Accepting checks the numbers again - no gain, no change.</p>
      ${open.length ? `<div class="hp-rows">${open.map(row).join('')}</div>` : '<p class="hp-empty">Nothing to change yet - not enough judged results show a clear gain.</p>'}
      ${rest.length ? `<h3 class="hp-sub3">Decided</h3><div class="hp-rows">${rest.map(row).join('')}</div>` : ''}`;
  }

  /* ---------- routing + events ---------- */
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }
  async function route() {
    const h = location.hash || '#/';
    st.libEl = '';
    try {
      if (h === '#/w') { if (st.pack) bench(); else go('#/'); }
      else if (h === '#/ready') { if (st.ready) ready(); else go('#/recipes'); }
      else if (h === '#/recipes') await recipes();
      else if (h === '#/library') await libPage();
      else if (h.startsWith('#/m/')) await home('', decodeURIComponent(h.slice(4)));
      else if (h === '#/saved') await saved();
      else if (h === '#/c') { if (st.pack) await cmpStart(); else go('#/'); }
      else if (h === '#/cx') { if (st.cmp && st.cmp.b) await cmpShow(); else go('#/'); }
      else if (h === '#/pb') { if (st.paste) pasteForm(); else go('#/'); }
      else if (h === '#/f') { if (st.fill) fillForm(); else go('#/saved'); }
      else if (h.startsWith('#/v/')) await history(decodeURIComponent(h.slice(4)));
      else if (h.startsWith('#/shared/')) await sharedView(decodeURIComponent(h.slice(9)));
      else if (h.startsWith('#/r/')) await openRecipe(decodeURIComponent(h.slice(4)));
      else if (h === '#/results') await results();
      else if (h === '#/learn') await learn();
      else if (h.startsWith('#/s/') && st.secs.some(s => s.key === h.slice(4))) await home(h.slice(4));
      else await home('');
    } catch (e) { toast(e.message, true); }
    const m = $('#hpMain'); if (m) m.scrollTop = 0;
  }
  document.addEventListener('submit', e => {
    if (e.target.id === 'hpAsk') { e.preventDefault(); understand($('#hpText').value, st.section); }
    if (e.target.id === 'hpOfferF') { e.preventDefault(); api('POST', '/api/prompting/community', {saved_id: st.savedId, title: (st.mine && st.mine.title) || '', by: e.target.by.value.trim()}).then(() => { toast('Offered. Hoola reads it before it goes on the shelf.'); return offerRow(); }).catch(er => toast(er.message, true)); return; }
    if (e.target.id === 'hpWFind') { e.preventDefault(); st.wq = $('#hpWQ').value.trim(); st.wpage = 1; worldShelf(); return; }
    if (e.target.id === 'hpAdapt') { e.preventDefault(); const q = $('#hpAdaptQ').value.trim(); if (q.length < 3) { toast('Say what to change, in a few words.', true); return; } adapt(q); return; }
    if (e.target.id === 'hpPaste') { e.preventDefault(); const v = {}; e.target.querySelectorAll('input').forEach(i => { v[i.name] = i.value.trim(); });
      api('POST', '/api/prompting/paste/fill', {text: st.paste.text, values: v}).then(f => { const p = st.paste; st.paste = null; return understand(f.text, p.section, false, true); }).catch(er => toast(er.message, true)); return; }
    if (e.target.id === 'hpFind') { e.preventDefault(); st.q = $('#hpQ').value.trim(); recipes(); }
    if (e.target.id === 'hpFillSaved') { e.preventDefault(); const v = {}; e.target.querySelectorAll('input').forEach(i => { v[i.name] = i.value.trim(); });
      api('POST', `/api/prompting/saved/${encodeURIComponent(st.fill.id)}/fill`, {values: v}).then(pk => { st.pack = pk; st.fill = null; go('#/w'); }).catch(er => toast(er.message, true)); return; }
    if (e.target.id === 'hpCmpWords') { e.preventDefault(); const t = e.target.t.value.trim();
      api('POST', '/api/prompting/understand', {text: t, section: st.cmp.a.section}).then(pk => { st.cmp.b = pk.brief; go('#/cx'); }).catch(er => toast(er.message, true)); return; }
    if (e.target.id === 'hpSched') { e.preventDefault(); const f = new FormData(e.target);
      api('PUT', `/api/prompting/saved/${encodeURIComponent(st.savedId)}/schedule`, {repeat: f.get('repeat'), at: f.get('at')})
        .then(() => { toast('Scheduled. The result will come to your Hoola chat.'); mine(); }).catch(er => toast(er.message, true)); return; }
    if (e.target.id === 'hpFill') { e.preventDefault();
      if (st.recipe && st.recipe.world && st.recipe.use !== 'workbench') { worldFilled().then(() => toast(st.recipe.blanks.length ? 'Filled in. Copy it when you are ready.' : 'Ready.')).catch(er => toast(er.message, true)); return; }
      const v = {}; e.target.querySelectorAll('input').forEach(i => { v[i.name] = i.value.trim(); }); useRecipe(st.recipe.id, v); }
  });
  document.addEventListener('error', e => {       // a picture that could not be fetched: a plain tile, never a broken image
    const t = e.target; if (!t || t.tagName !== 'IMG') return; const m = t.closest('.hl-media'); if (m) { m.classList.add('broken'); t.remove(); }
  }, true);
  document.addEventListener('click', e => { const pop = $('#hpPop'); if (pop && !pop.hidden && !e.target.closest('#hpPop') && !e.target.closest('#hpPick')) openPick(false); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('#hpPop') && !$('#hpPop').hidden) { openPick(false); $('#hpPick').focus(); } });
  document.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && e.target.id === 'hpText') { e.preventDefault(); $('#hpAsk').requestSubmit(); } });
  document.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.sec !== undefined) { st.section = b.dataset.sec; document.querySelectorAll('[data-sec]').forEach(x => x.setAttribute('aria-pressed', String(x === b))); return; }
    if (b.dataset.shelf) { st.shelf = b.dataset.shelf; recipes(); return; }
    if (b.id === 'hpPick') { openPick(); return; }
    if (b.dataset.mcat !== undefined) { openPick(false); const t = $('#hpText') ? $('#hpText').value : ''; st.text = t; go(b.dataset.mcat ? '#/m/' + b.dataset.mcat : '#/'); return; }
    if (b.id === 'hpWMore') { libMore(b); return; }
    if (b.dataset.wlib) { st.wgroup = b.dataset.wlib; st.wfam = b.dataset.wfam || ''; st.wq = ''; st.wkind = ''; go('#/library'); return; }
    if (b.dataset.acopy) { copy(st.adapted.text); return; }
    if (b.dataset.achat) { run({to: 'chat', text: st.adapted.text}); return; }
    if (b.dataset.awb) { understand(st.adapted.text, st.recipe.section === 'chat' ? (st.recipe.make_in || '') : st.recipe.section, false, true); return; }
    if (b.id === 'hpWCopy') { worldFilled().then(t => copy(t)).catch(er => toast(er.message, true)); return; }
    if (b.id === 'hpWChat') { worldFilled().then(t => run({to: 'chat', text: t})).catch(er => toast(er.message, true)); return; }
    if (b.dataset.wkind !== undefined) { st.wkind = b.dataset.wkind; st.wpage = 1; st.wq = $('#hpWQ') ? $('#hpWQ').value.trim() : st.wq; worldShelf(); return; }
    if (b.dataset.wfam !== undefined) { const same = st.wfam === b.dataset.wfam && !b.dataset.wgroup && !st.wgroup && b.dataset.wfam;
      st.wfam = same ? '' : b.dataset.wfam; st.wgroup = b.dataset.wgroup || ''; st.wpage = 1;
      if (b.dataset.wgo) { st.wq = ''; st.wkind = ''; go('#/library'); return; }
      st.wq = $('#hpWQ') ? $('#hpWQ').value.trim() : st.wq; worldShelf(); return; }
    if (b.dataset.wpage) { st.wpage = Math.max(1, st.wpage + Number(b.dataset.wpage)); worldShelf(); return; }
    if (b.id === 'hpPasteSkip') { const p = st.paste; st.paste = null; understand(p.text, p.section, false, true); return; }
    if (b.dataset.rsec !== undefined) { st.rsec = b.dataset.rsec; st.q = $('#hpQ') ? $('#hpQ').value.trim() : st.q; recipes(); return; }
    if (b.dataset.recipe) { openRecipe(b.dataset.recipe); return; }
    if (b.dataset.who !== undefined) { st.everyone = !!b.dataset.who; results().catch(er => toast(er.message, true)); return; }
    if (b.dataset.thumb) { try { await api('POST', `/api/prompting/runs/${encodeURIComponent(b.dataset.run)}/thumb`, {value: b.dataset.thumb}); await results(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpForget') { if (!confirm('Delete the whole record of your prompts and their results? This cannot be undone.')) return;
      try { const r = await api('DELETE', '/api/prompting/ledger?confirm=DELETE'); toast(`Deleted ${r.deleted} record${r.deleted === 1 ? '' : 's'}.`); await results(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpAgain') { understand($('#hpHers').value, st.pack.brief.section, true); return; }
    if (b.id === 'hpRun') { b.disabled = true; await hand('run'); run(location.hash === '#/ready' ? st.ready.run : st.pack.out.run); return; }
    if (b.id === 'hpCopy') { hand('copy'); copy(location.hash === '#/ready' ? st.ready.prompt : st.pack.out.prompt); return; }
    if (b.id === 'hpSave') { b.disabled = true;
      try { const r = await api('POST', '/api/prompting/saved', {brief: st.pack.brief, id: st.savedId}); st.savedId = r.id; toast('Saved in My prompts.'); bench(); }
      catch (er) { toast(er.message, true); b.disabled = false; } return; }
    if (b.dataset.open) { try { await openSaved(b.dataset.open); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.lesson) { try { await api('PUT', '/api/prompting/learn/' + encodeURIComponent(b.dataset.lesson), {state: b.dataset.state});
        const card = b.closest('.hp-lesson'); if (card) card.remove(); toast(b.dataset.state === 'got_it' ? 'Noted. It comes back in 30 days only if it still applies.' : 'Hidden. Thank you.');
      } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpOut') { const box = $('#hpOutBox'), open = box.hidden; box.hidden = !open; b.setAttribute('aria-expanded', String(open)); if (open) outBox().catch(er => toast(er.message, true)); return; }
    if (b.dataset.outt) { outBox(b.dataset.outt).catch(er => toast(er.message, true)); return; }
    if (b.id === 'hpOutCopy') { copy(st.outText || ''); return; }
    if (b.dataset.cwd) { try { await api('POST', `/api/prompting/community/${encodeURIComponent(b.dataset.cwd)}/withdraw`); await communityBox(); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.cdec) { try { await api('POST', `/api/prompting/community/${encodeURIComponent(b.dataset.cdec)}/${b.dataset.act}`, {}); toast(b.dataset.act === 'approve' ? 'On the Recipes shelf.' : 'Refused.'); await recipes(); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.usual) { try { await api('POST', '/api/prompting/usual/' + encodeURIComponent(b.dataset.usual), {on: b.dataset.on === '1'}); await usualBox(); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.khud) { try { const c = await api('POST', `/api/prompting/khud/${encodeURIComponent(b.dataset.khud)}/${b.dataset.act}`);
        toast(c.status === 'accepted' ? 'In use from the next prompt.' : c.status === 'refused' && b.dataset.act === 'accept' ? 'Refused: ' + c.reason : 'Done.', c.status === 'refused' && b.dataset.act === 'accept'); await khudBox(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpCmp') { go('#/c'); return; }
    if (b.dataset.cmpb === 'raw') { st.cmp.b = {section: st.cmp.a.section, intent: st.cmp.a.intent, slots: {}}; go('#/cx'); return; }
    if (b.dataset.cmps) { try { const r = await api('GET', '/api/prompting/saved/' + encodeURIComponent(b.dataset.cmps)); st.cmp.b = r.brief; go('#/cx'); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpCmpPrice') { try { st.cmp.quote = await api('POST', '/api/prompting/compare/quote', {a: st.cmp.a, b: st.cmp.b}); cmpRunBox(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpCmpGo') { b.disabled = true; b.textContent = 'Running both…';
      try { const r = await api('POST', '/api/prompting/compare/run', {a: st.cmp.a, b: st.cmp.b, quality: st.cmp.quote.quality, token: st.cmp.quote.token});
        st.cmp.run = r; st.cmp.cid = r.id; cmpRunBox(); cmpResults(r); } catch (er) { toast(er.message, true); st.cmp.quote = null; cmpRunBox(); } return; }
    if (b.dataset.pick) { try {
        if (!st.cmp.cid) st.cmp.cid = (await api('POST', '/api/prompting/compare/judge', {a: st.cmp.a, b: st.cmp.b})).id;
        await api('POST', `/api/prompting/compare/${encodeURIComponent(st.cmp.cid)}/pick`, {side: b.dataset.pick}); st.cmp.pick = b.dataset.pick; cmpRunBox(); toast('Kept. Thank you.');
      } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.ask) { const cur = (st.mine && st.mine.ask) || [], k = b.dataset.ask;
      const next = cur.includes(k) ? cur.filter(x => x !== k) : [...cur, k];
      try { await api('PATCH', '/api/prompting/saved/' + encodeURIComponent(st.savedId), {ask: next}); await mine(); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.restore) { try { await api('POST', `/api/prompting/saved/${encodeURIComponent(b.dataset.pid)}/versions/${encodeURIComponent(b.dataset.restore)}/restore`);
        toast('Brought back as a new version.'); await history(b.dataset.pid); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpUnsched') { try { await api('DELETE', `/api/prompting/saved/${encodeURIComponent(st.savedId)}/schedule`); toast('The schedule is stopped.'); await mine(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpShare') { try { const r = await api('POST', `/api/prompting/saved/${encodeURIComponent(st.savedId)}/share`); await mine();
        const url = location.origin + r.path; $('#hpLink').innerHTML = `<p class="hp-lead">Copy this link now - Hoola shows it only once.</p><input class="hp-in" id="hpLinkIn" readonly value="${esc(url)}" aria-label="Share link"><div class="hp-acts"><button type="button" class="hp-b sm" id="hpLinkCopy">Copy the link</button></div>`;
        $('#hpLinkIn').select(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpLinkCopy') { copy($('#hpLinkIn').value); return; }
    if (b.id === 'hpUnshare') { if (!confirm('Turn the share link off? Anyone who has it will no longer be able to open it.')) return;
      try { await api('DELETE', `/api/prompting/saved/${encodeURIComponent(st.savedId)}/share`); toast('The link is off.'); await mine(); } catch (er) { toast(er.message, true); } return; }
    if (b.id === 'hpCopyShared') { try { const r = await api('POST', `/api/prompting/shared/${encodeURIComponent(b.dataset.token)}/copy`); toast('Saved in My prompts.'); await openSaved(r.id); } catch (er) { toast(er.message, true); } return; }
    if (b.dataset.del) { if (!confirm('Delete this saved prompt?')) return;
      try { await api('DELETE', '/api/prompting/saved/' + encodeURIComponent(b.dataset.del)); toast('Deleted.'); route(); } catch (er) { toast(er.message, true); } }
  });
  document.addEventListener('change', async e => {
    if (e.target.id === 'hpWSort') { st.wsort = e.target.value; st.wpage = 1; st.wq = $('#hpWQ') ? $('#hpWQ').value.trim() : st.wq; worldShelf(); return; }
    if (e.target.id !== 'hpLedger' && e.target.id !== 'hpShare') return;
    try { await api('PUT', '/api/prompting/ledger/prefs', e.target.id === 'hpLedger' ? {ledger: e.target.checked} : {share: e.target.checked}); toast('Saved.'); }
    catch (er) { e.target.checked = !e.target.checked; toast(er.message, true); }
  });
  window.addEventListener('hashchange', route);
  (async () => {
    try { const s = await UI.sections(); st.secs = s.list; st.known = s.known; }
    catch (e) { $('#hp').innerHTML = `<p class="hp-boot">${esc(e.message)}</p>`; return; }
    route();
  })();
})();
