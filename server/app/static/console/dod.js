/* v0.999.306 HOOLA DOD - her coworker. Meet it once (a face from the 200 looks, a name, a voice), then give it
   real work; every step, question and file shows here. The page only relays her taps to /api/dod/*: give a task,
   tell it something, answer it, stop it. Parts of the page that hold her typing are drawn once and never redrawn
   by the refresh. */
(function () {
  'use strict';
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) {}
  if (!TOKEN) { location.replace('/console/'); return; }

  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const enc = encodeURIComponent;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const main = $('#main');

  async function api(method, path, body) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const r = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
    if (r.status === 401) { location.replace('/console/'); throw new Error('signed out'); }
    let j = {};
    try { j = await r.json(); } catch (e) {}
    if (!r.ok) throw new Error(j.detail || ('Something went wrong (' + r.status + ').'));
    return j;
  }
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 3800);
  }

  try { if (window.HoolaMark) $('#brandMark').innerHTML = HoolaMark.svg({color: '#FFFFFF'}); } catch (e) {}

  const IC = {
    check: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 5 5 9-10"/></svg>',
    bang: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7v6M12 16.5v.5"/></svg>',
    you: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="9" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    up: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V6"/><path d="m6.5 11.5 5.5-5.5 5.5 5.5"/></svg>',
    browser: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M4 12h16M12 4a12 12 0 0 1 0 16M12 4a12 12 0 0 0 0 16"/></svg>',
    code: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 8-4 4 4 4M16 8l4 4-4 4"/></svg>',
    long: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    cart: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h2l2 11h10l2-8H7"/><circle cx="10" cy="20" r="1"/><circle cx="17" cy="20" r="1"/></svg>',
    doc: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z"/><path d="M9 12h6M9 16h6M9 8h2"/></svg>',
    rows: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/><path d="M8 4v16"/></svg>',
    lock: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8.5 11V8a3.5 3.5 0 0 1 7 0v3"/></svg>',
    play: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true" style="width:16px;height:16px"><path d="M8 5v14l11-7z"/></svg>',
    arrow: '<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  };

  let ST = null;           // /api/dod/status
  let TASKS = [];          // the latest list
  let POLL = null;
  let VIEW = '';
  let GEN = 0;           // one number per page drawn: a listener from an older page does nothing

  // ------------------------------------------------------------------ small helpers
  const ago = iso => {
    if (!iso) return '';
    const s = Math.max(0, (Date.now() - Date.parse(iso)) / 1000);
    if (s < 60) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min ago';
    if (s < 86400) return Math.round(s / 3600) + ' h ago';
    return new Date(iso).toLocaleDateString(undefined, {day: 'numeric', month: 'short'});
  };
  const dur = (a, b) => {
    if (!a) return '';
    const s = Math.max(0, ((b ? Date.parse(b) : Date.now()) - Date.parse(a)) / 1000);
    if (s < 60) return Math.round(s) + ' s';
    const m = Math.floor(s / 60);
    if (m < 60) return m + ' min';
    return Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0') + ' min';
  };
  const clock = (from, at) => {
    if (!from || !at) return '';
    const s = Math.max(0, (Date.parse(at) - Date.parse(from)) / 1000);
    const m = Math.floor(s / 60), r = Math.floor(s % 60);
    return m >= 60 ? Math.floor(m / 60) + ':' + String(m % 60).padStart(2, '0') + ':' + String(r).padStart(2, '0') : m + ':' + String(r).padStart(2, '0');
  };
  const greet = () => { const h = new Date().getHours(); return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'; };
  const size = n => n < 1024 ? n + ' B' : n < 1048576 ? Math.round(n / 1024) + ' KB' : (n / 1048576).toFixed(1) + ' MB';
  const ext = n => (String(n).split('.').pop() || '').toLowerCase().slice(0, 4);
  const NAME = () => (ST && ST.profile && ST.profile.name) || 'Your coworker';
  // v0.999.320 the voice she picked is used: her coworker reads its question and its answer aloud in it, on her tap
  const VOICES = {warm: [0.95, 1], bright: [1.08, 1.15], calm: [0.88, 0.92], confident: [1.0, 0.98]};
  function speak(text, voice) {
    try {
      if (!('speechSynthesis' in window)) throw new Error('no speech');
      const u = new SpeechSynthesisUtterance(String(text || '').slice(0, 1500));
      const [rate, pitch] = VOICES[voice || (ST && ST.profile && ST.profile.voice)] || VOICES.warm;
      u.rate = rate; u.pitch = pitch;
      speechSynthesis.cancel(); speechSynthesis.speak(u); return true;
    } catch (err) { toast('This browser cannot play the voice.'); return false; }
  }
  const STATUS = {
    queued: ['live', 'Starting'], working: ['live', 'Working'], needs_you: ['warn', 'Needs your OK'],
    done: ['ok', 'Done'], failed: ['bad', 'Did not finish'], stopped: ['mute', 'Stopped'],
  };
  function tag(st) {
    const [c, w] = STATUS[st] || ['mute', st];
    const live = (st === 'working' || st === 'queued') ? ' dd-live' : '';
    return `<span class="dd-tag ${c}${live}">${live ? '<span class="dd-dot"></span>' : ''}${esc(w)}</span>`;
  }
  function ring(src, px, on, alt) {
    return `<div class="dd-ring${on ? ' on' : ''}" style="width:${px}px;height:${px}px"><div>${src ? `<img src="${esc(src)}" alt="${esc(alt || '')}">` : ''}</div></div>`;
  }
  function stepRow(s, from) {
    const cls = s.you ? 'you' : s.ask ? 'wait' : s.state === 'now' ? 'now' : 'done';
    const icon = cls === 'done' ? IC.check : cls === 'wait' ? IC.bang : cls === 'you' ? IC.you : '';
    const title = cls === 'now' ? `<span class="dd-shimmer">${esc(s.title)}</span>` : esc(s.title);
    const why = s.detail ? `<div class="d${s.you ? '' : ' why'}">${esc(s.detail)}</div>` : '';
    return `<div class="dd-step${s.you ? ' you' : ''}"><span class="dd-sm ${cls}">${icon}</span><div class="t">${title}${why}</div><span class="tm">${clock(from, s.at)}</span></div>`;
  }
  function questionBox(t) {
    const q = t.question;
    if (!q) return '';
    const data = `data-task="${esc(t.id)}" data-q="${esc(q.id)}" data-hash="${esc(q.hash)}"`;
    if (q.kind === 'pay') {
      const amt = (q.currency ? q.currency + ' ' : '') + (q.amount != null ? Number(q.amount).toLocaleString() : '');
      return `<div class="dd-q"><div class="what"><div>${esc(q.question)}</div><span class="amt">${esc(amt)}</span>${q.details ? `<div>${esc(q.details)}</div>` : ''}</div>
        <button class="dd-btn ink" type="button" data-answer="yes" ${data}>Approve ${esc(amt)}</button><button class="dd-btn" type="button" data-answer="no" ${data}>Not now</button></div>`;
    }
    if (q.kind === 'choice' && (q.options || []).length) {
      return `<div class="dd-q"><div class="what"><span class="qt">${esc(q.question)}</span></div>${q.options.map(o =>
        `<button class="dd-btn" type="button" data-answer="${esc(o)}" ${data}>${esc(o)}</button>`).join('')}</div>`;
    }
    if (q.kind === 'info') {
      return `<div class="dd-q"><div class="what"><span class="qt">${esc(q.question)}</span>${q.details ? `<div>${esc(q.details)}</div>` : ''}</div>
        <form class="dd-qform" ${data} style="display:flex;gap:8px;flex:1;min-width:240px"><input name="a" aria-label="Your answer" placeholder="Your answer" style="flex:1;height:38px;border-radius:12px;border:1px solid var(--line2);background:var(--card);color:var(--ink);font:inherit;padding:0 12px"><button class="dd-btn ink" type="submit">Answer</button></form></div>`;
    }
    const verb = {send: 'Send it', delete: 'Delete it', book: 'Book it'}[q.kind] || 'Yes';
    return `<div class="dd-q"><div class="what"><span class="qt">${esc(q.question)}</span>${q.details ? `<div>${esc(q.details)}</div>` : ''}</div>
      <button class="dd-btn ink" type="button" data-answer="yes" ${data}>${esc(verb)}</button><button class="dd-btn" type="button" data-answer="no" ${data}>Not now</button></div>`;
  }
  function fileCard(t, f) {
    const e = ext(f.name);
    return `<button type="button" class="dd-file" data-file="${esc(f.name)}" data-task="${esc(t.id)}"><span class="dd-ft ${esc(e)}">${esc(e.toUpperCase() || 'FILE')}</span><div style="min-width:0"><b>${esc(f.title || f.name)}</b><small>${esc(f.name)} · ${size(f.size || 0)}</small></div></button>`;
  }
  function taskCard(t) {
    const steps = t.steps || [];
    const now = [...steps].reverse().find(s => s.state === 'now');
    const done = steps.filter(s => !s.you).slice(-3);
    const timeLine = t.status === 'needs_you' ? 'Waiting for you' : (t.started_at ? dur(t.started_at) : 'Starting');
    let body = '';
    if (t.status === 'needs_you') body = done.map(s => stepRow(s, t.started_at)).join('') + questionBox(t);
    else if (now) body = stepRow(now, t.started_at);
    else body = `<div class="dd-step"><span class="dd-sm now"></span><div class="t"><span class="dd-shimmer">${esc(NAME())} is getting ready</span></div><span></span></div>`;
    const files = (t.files || []).slice(-1).map(f => fileCard(t, f)).join('');
    return `<article class="dd-card dd-task${t.status === 'needs_you' ? ' ask' : ''}"><div class="head">${tag(t.status)}<small>${esc(timeLine)}</small><a class="dd-lnk" href="#/t/${enc(t.id)}">Open</a></div>
      <h3>${esc(t.title)}</h3><div>${body}</div>${files ? `<div style="display:flex">${files}</div>` : ''}</article>`;
  }

  // ------------------------------------------------------------------ data
  async function loadStatus() {
    ST = await api('GET', '/api/dod/status');
    const p = ST.profile;
    const who = $('#who');
    if (p) {
      who.hidden = false;
      const s = ST.summary || {};
      const line = s.needs_you ? `${s.needs_you} needs your OK` : s.working ? `Working on ${s.working} task${s.working > 1 ? 's' : ''}` : 'Ready for work';
      who.innerHTML = `${ring(p.head, 42, !!s.working)}<div style="min-width:0"><b>${esc(p.name)}</b><div class="dd-state${s.working ? ' dd-live' : ' idle'}" style="font-size:12.5px">${s.working ? '<span class="dd-dot"></span>' : ''}${esc(line)}</div></div>`;
      $('#canUse').textContent = p.name + ' can use';
      const nc = $('#needCount'); nc.hidden = !s.needs_you; nc.textContent = s.needs_you || '';
    }
    const m = $('#meter');
    if (ST.spent && ST.spent.limit) {
      const pct = Math.min(100, Math.round(100 * ST.spent.usage / ST.spent.limit));
      m.hidden = false;
      m.innerHTML = `<div class="row"><span style="color:var(--mut)">Work budget used</span><b style="font-weight:600">${pct}%</b></div><div class="dd-bar still" style="height:5px"><i style="width:${pct}%"></i></div><small>Each coworker has its own budget, so nobody spends another's.</small>`;
    } else m.hidden = true;
    return ST;
  }
  async function loadTasks(state) {
    const j = await api('GET', '/api/dod/tasks' + (state ? '?state=' + enc(state) : ''));
    TASKS = j.tasks || [];
    if (!state) { const c = $('#allCount'); c.hidden = !TASKS.length; c.textContent = TASKS.length; }
    return TASKS;
  }

  function setNav(key) { $$('.dd-nav[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === key)); }
  function poll(fn, ms) { clearInterval(POLL); POLL = setInterval(() => { if (!document.hidden) fn().catch(() => {}); }, ms); }

  // ------------------------------------------------------------------ setup: meet your coworker
  async function viewSetup() {
    setNav(''); clearInterval(POLL);
    const [{looks}] = await Promise.all([api('GET', '/api/dod/looks')]);
    const cur = ST.profile || {};
    let picked = cur.look || 'f002';
    let gender = (looks.find(l => l.id === picked) || {}).gender || 'f';
    let voice = cur.voice || 'warm';
    let typed = cur.name || '';
    const first = !ST.profile;
    main.innerHTML = `<div class="dd-setup">
      <header class="dd-rise"><span class="k">${first ? 'HOOLA DOD · MEET YOUR COWORKER' : 'HOOLA DOD · YOUR COWORKER'}</span>
        <h1>${first ? 'Meet your coworker.' : 'Change your coworker.'}</h1>
        <p>Choose how they look and what to call them. They will do real work for you every day, from ordering dinner to coding for hours.</p></header>
      <div class="dd-scols">
        <section class="dd-card dd-pickcard dd-rise" aria-label="Choose your coworker">
          <div><div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:12px;flex-wrap:wrap"><h2>Pick a face</h2>
            <div class="dd-filt" role="group" aria-label="Show"><button type="button" class="dd-chip" data-g="f">Women</button><button type="button" class="dd-chip" data-g="m">Men</button></div></div>
            <div class="dd-faces" id="faces"></div></div>
          <div class="dd-field"><label for="nm">Give them a name</label><input id="nm" maxlength="20" autocomplete="off">
            <small>Any language works. Names of banks, police or government offices are not allowed.</small><div class="dd-err" id="nmErr" hidden></div></div>
          <div class="dd-field"><span class="lb">How they sound</span><div class="dd-filt" id="voices"></div></div>
        </section>
        <section class="dd-card dd-prev dd-rise r2" aria-label="Preview">
          <div class="dd-stage"><div class="dd-halo" aria-hidden="true"></div><img class="dd-float" id="pv" alt=""></div>
          <div class="dd-card dd-say"><span class="dd-wv" aria-hidden="true"><i></i><i></i><i></i><i></i></span><div><div style="font-weight:600;margin-bottom:4px" id="pvName"></div><div class="q" id="pvSay"></div></div></div>
          <button class="dd-btn ink dd-start" type="button" id="startBtn"></button>
          <span style="font-size:12.5px;color:var(--lab)">You can change the face, name and voice later.</span>
        </section>
      </div></div>`;
    const nm = $('#nm');
    nm.value = typed;
    const nameOf = () => (nm.value.trim() || (looks.find(l => l.id === picked) || {}).name || 'your coworker');
    function drawFaces() {
      $$('[data-g]').forEach(b => b.classList.toggle('on', b.dataset.g === gender));
      $('#faces').innerHTML = looks.filter(l => l.gender === gender).map(l =>
        `<button type="button" class="dd-face${l.id === picked ? ' on' : ''}" data-look="${esc(l.id)}" aria-label="Pick ${esc(l.name)}, ${esc(l.city)}" aria-pressed="${l.id === picked}"><img src="${esc(l.head)}" alt="" loading="lazy"></button>`).join('');
    }
    function drawVoices() {
      $('#voices').innerHTML = ['warm', 'bright', 'calm', 'confident'].map(v =>
        `<button type="button" class="dd-chip${v === voice ? ' on' : ''}" data-voice="${v}" aria-pressed="${v === voice}">${v[0].toUpperCase() + v.slice(1)}</button>`).join('') +
        `<button type="button" class="dd-chip" id="hear" style="border-style:dashed">${IC.play}Hear it</button>`;
    }
    function drawPreview() {
      const l = looks.find(x => x.id === picked) || looks[0];
      $('#pv').src = l.full; $('#pv').alt = nameOf() + ', your coworker';
      $('#pvName').textContent = nameOf();
      $('#pvSay').textContent = `“Hi, I'm ${nameOf()}. Give me any real work. I'll do it on my own computer, show you every step, and ask before I pay or send anything.”`;
      $('#startBtn').innerHTML = (first ? 'Start working with ' : 'Save ') + esc(nameOf()) + IC.arrow;
    }
    const gen = GEN;
    main.addEventListener('click', function onClick(e) {
      if (gen !== GEN) { main.removeEventListener('click', onClick); return; }
      const g = e.target.closest('[data-g]'); if (g) { gender = g.dataset.g; drawFaces(); return; }
      const f = e.target.closest('[data-look]');
      if (f) { const prevName = (looks.find(l => l.id === picked) || {}).name; picked = f.dataset.look;
        if (!nm.value.trim() || nm.value.trim() === prevName) nm.value = (looks.find(l => l.id === picked) || {}).name || '';
        drawFaces(); drawPreview(); return; }
      const v = e.target.closest('[data-voice]'); if (v) { voice = v.dataset.voice; drawVoices(); return; }
      if (e.target.closest('#hear')) {
        speak(`Hi, I'm ${nameOf()}. Ready when you are.`, voice);
        return;
      }
      if (e.target.closest('#startBtn')) save();
    });
    nm.addEventListener('input', drawPreview);
    async function save() {
      const err = $('#nmErr'); err.hidden = true;
      try {
        await api('PUT', '/api/dod/profile', {name: nameOf(), look: picked, voice});
        await loadStatus();
        location.hash = '#/';
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    }
    if (!nm.value) nm.value = (looks.find(l => l.id === picked) || {}).name || '';
    drawFaces(); drawVoices(); drawPreview();
  }

  // ------------------------------------------------------------------ home
  let KIND = 'task';
  async function viewHome() {
    setNav('home');
    const p = ST.profile;
    const s = ST.summary || {};
    const eng = ST.engine || {};
    main.innerHTML = `<div class="dd-wrap">
      <section class="dd-hero dd-rise">${ring(p.head, 112, !!s.working, p.name + ', your coworker')}
        <div style="display:flex;flex-direction:column;gap:10px;min-width:0;flex:1"><div id="heroState"></div>
          <h1>${esc(greet())}. What should ${esc(p.name)} do next?</h1>
          <p>${esc(p.name)} works on their own computer in the background, shows you every step, and asks before paying, sending or deleting anything.</p></div></section>
      ${eng.ok ? '' : `<div class="dd-banner">${esc(eng.why || 'Your coworker cannot start work yet.')}</div>`}
      <form class="dd-card dd-ask dd-rise r2" id="askForm" aria-label="Give ${esc(p.name)} a task">
        <label for="ask" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Describe the task</label>
        <textarea id="ask" rows="2" placeholder="Book a table for four at a quiet Italian place on Saturday at 8, and send the address to Rahul…"></textarea>
        <div class="row" id="kinds">
          <button class="dd-chip" type="button" data-kind="browser">${IC.browser}Websites</button>
          <button class="dd-chip" type="button" data-kind="code">${IC.code}Code</button>
          <button class="dd-chip" type="button" data-kind="long">${IC.long}Long job</button>
          <span class="note">Asks before paying, sending or deleting</span>
          <button type="submit" class="dd-send" id="sendBtn" aria-label="Give the task" disabled>${IC.up}</button>
        </div></form>
      <div class="dd-cols">
        <section aria-labelledby="wn" class="dd-rise r3"><div class="dd-sect"><h2 id="wn">Working now</h2><a class="dd-lnk" href="#/tasks">All tasks</a></div><div id="openList" style="display:flex;flex-direction:column;gap:16px"></div></section>
        <aside class="dd-rise r4" style="display:flex;flex-direction:column;gap:28px">
          <section aria-labelledby="dt"><div class="dd-sect"><h2 id="dt">Done today</h2><a class="dd-lnk" href="#/tasks">See all</a></div><div class="dd-card dd-done" id="doneList"></div></section>
          <section aria-labelledby="wk"><div class="dd-sect"><h2 id="wk">${esc(p.name)} this week</h2></div><div class="dd-card dd-stats" id="stats"></div></section>
        </aside></div>
      <section aria-labelledby="try" class="dd-rise r4"><div class="dd-sect"><h2 id="try">Give real work</h2></div><div class="dd-try">
        <button class="dd-card" type="button" data-try="browser" data-text="Order dinner for two from a good place nearby for 8:30 tonight. Show me the cart before paying.">${IC.cart}<b>Order or book anything</b><span>Food, tickets, a cab, a table. Stops before paying.</span></button>
        <button class="dd-card" type="button" data-try="code" data-text="In my repository, add an export button to the invoices page with tests, and keep going until the tests pass.">${IC.code}<b>Code for hours</b><span>Builds, tests and fixes until it is done.</span></button>
        <button class="dd-card" type="button" data-try="long" data-text="Write a clear user guide for my product from the files I give you, as a Word document.">${IC.doc}<b>Write the documents</b><span>Guides, reports, proposals, from your files.</span></button>
        <button class="dd-card" type="button" data-try="browser" data-text="Collect the name, price and stock of every product from these supplier websites into a spreadsheet:">${IC.rows}<b>Collect data at scale</b><span>Thousands of rows from many sites, into a sheet.</span></button>
      </div></section></div>`;
    const ask = $('#ask'), send = $('#sendBtn');
    const sync = () => { send.disabled = ask.value.trim().length < 3; };
    ask.addEventListener('input', sync);
    ask.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); give(); } });
    $('#kinds').addEventListener('click', e => {
      const b = e.target.closest('[data-kind]'); if (!b) return;
      KIND = KIND === b.dataset.kind ? 'task' : b.dataset.kind; drawKinds();
    });
    function drawKinds() { $$('#kinds [data-kind]').forEach(b => b.classList.toggle('on', b.dataset.kind === KIND)); }
    $('.dd-try').addEventListener('click', e => {
      const b = e.target.closest('[data-try]'); if (!b) return;
      KIND = b.dataset.try; drawKinds(); ask.value = b.dataset.text; sync(); ask.focus();
      ask.setSelectionRange(ask.value.length, ask.value.length);
    });
    $('#askForm').addEventListener('submit', e => { e.preventDefault(); give(); });
    async function give() {
      const text = ask.value.trim(); if (text.length < 3) return;
      send.disabled = true;
      try {
        const j = await api('POST', '/api/dod/tasks', {ask: text, kind: KIND});
        ask.value = ''; KIND = 'task'; drawKinds(); sync();
        toast(`${NAME()} is on it.`);
        location.hash = '#/t/' + enc(j.task.id);
      } catch (ex) { toast(ex.message); sync(); }
    }
    drawKinds();
    await drawHomeLists();
    poll(async () => { await loadStatus(); await drawHomeLists(); }, 3000);
  }
  async function drawHomeLists() {
    await loadTasks('');
    const s = ST.summary || {};
    const open = TASKS.filter(t => ['queued', 'working', 'needs_you'].includes(t.status))
      .sort((a, b) => (b.status === 'needs_you') - (a.status === 'needs_you'));
    const today = new Date().toDateString();
    const done = TASKS.filter(t => t.status === 'done' && t.ended_at && new Date(t.ended_at).toDateString() === today);
    const hs = $('#heroState');
    if (hs) {
      const bits = [];
      if (s.working) bits.push(`${s.working} task${s.working > 1 ? 's' : ''}`);
      if (s.needs_you) bits.push(`${s.needs_you} need${s.needs_you > 1 ? '' : 's'} your OK`);
      hs.innerHTML = bits.length ? `<div class="dd-state dd-live"><span class="dd-dot"></span>Working now · ${esc(bits.join(' · '))}</div>`
        : `<div class="dd-state idle">Ready for work</div>`;
    }
    const ol = $('#openList');
    if (ol) ol.innerHTML = open.length ? open.slice(0, 6).map(taskCard).join('')
      : `<div class="dd-card dd-quiet">Nothing running. Give ${esc(NAME())} a task above.</div>`;
    const dl = $('#doneList');
    if (dl) dl.innerHTML = done.length ? done.slice(0, 5).map(t => `<a class="it" href="#/t/${enc(t.id)}"><span class="dd-tag ok" style="flex:none">Done</span><div style="min-width:0"><b>${esc(t.title)}</b><small>${esc(dur(t.started_at, t.ended_at))}${(t.files || []).length ? ' · ' + t.files.length + ' file' + (t.files.length > 1 ? 's' : '') : ''}</small></div></a>`).join('')
      : `<div class="dd-quiet" style="padding:14px">Finished work shows here.</div>`;
    const st = $('#stats');
    if (st) st.innerHTML = `<div><span>Tasks done</span><b>${s.done_week || 0}</b></div><div><span>Hours worked</span><b>${s.hours_week || 0}</b></div>
      <div><span>Asked you</span><b>${s.asked_week || 0}</b></div><div><span>Files made</span><b>${s.files_week || 0}</b></div>`;
  }

  // ------------------------------------------------------------------ lists
  async function viewList(which) {
    setNav(which);
    const titles = {tasks: 'All tasks', needs: 'Needs you', files: 'Files'};
    main.innerHTML = `<div class="dd-wrap"><div class="dd-sect" style="margin:0"><h1 class="serif" style="margin:0;font-size:32px;font-weight:350">${titles[which]}</h1></div>
      ${which === 'tasks' ? `<div class="dd-filters" id="filt"><button class="dd-chip on" data-f="">All</button><button class="dd-chip" data-f="open">Working</button><button class="dd-chip" data-f="done">Done</button><button class="dd-chip" data-f="failed">Did not finish</button></div>` : ''}
      <div id="list"></div></div>`;
    let f = which === 'needs' ? 'needs' : '';
    const draw = async () => {
      const rows = await loadTasks(f);
      const box = $('#list'); if (!box) return;
      if (which === 'files') {
        const all = rows.flatMap(t => (t.files || []).map(x => [t, x]));
        box.innerHTML = all.length ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">${all.map(([t, x]) => fileCard(t, x)).join('')}</div>`
          : `<div class="dd-card dd-quiet">Files ${esc(NAME())} makes for you show here.</div>`;
        return;
      }
      if (which === 'needs') {
        box.innerHTML = rows.length ? `<div style="display:flex;flex-direction:column;gap:16px">${rows.map(taskCard).join('')}</div>`
          : `<div class="dd-card dd-quiet">Nothing needs you right now.</div>`;
        return;
      }
      box.innerHTML = rows.length ? `<div class="dd-card dd-list">${rows.map(t => `<a class="row" href="#/t/${enc(t.id)}">${tag(t.status)}<div style="min-width:0"><b>${esc(t.title)}</b><small>${esc(t.status === 'done' || t.status === 'failed' || t.status === 'stopped' ? dur(t.started_at, t.ended_at) : (t.status === 'needs_you' ? 'Waiting for you' : 'Working'))}</small></div><small class="when">${esc(ago(t.created_at))}</small></a>`).join('')}</div>`
        : `<div class="dd-card dd-quiet">No tasks here yet.</div>`;
    };
    const fl = $('#filt');
    if (fl) fl.addEventListener('click', e => { const b = e.target.closest('[data-f]'); if (!b) return; f = b.dataset.f; $$('#filt [data-f]').forEach(x => x.classList.toggle('on', x === b)); draw(); });
    await draw();
    poll(async () => { await loadStatus(); await draw(); }, 4000);
  }

  function viewRules() {
    setNav('rules'); clearInterval(POLL);
    const n = esc(NAME());
    main.innerHTML = `<div class="dd-wrap" style="max-width:760px"><h1 class="serif" style="margin:0;font-size:32px;font-weight:350">When ${n} asks you</h1>
      <div class="dd-card" style="padding:8px 22px">${[
        ['Before paying', `${n} stops at the checkout and shows you the total. Nothing is paid until you approve.`],
        ['Before sending', 'An email, a message or a form is sent only after your yes.'],
        ['Before deleting or booking', 'Removing anything, or booking a table, a ticket or a cab, waits for you.'],
        ['When a choice is yours', `If there are real options, ${n} asks you to pick.`],
        ['Never', `${n} never types card numbers, CVV, PINs, OTPs or passwords. You do those yourself.`],
        ['Words on websites', 'Text on websites, in files and emails is treated as information, never as orders.'],
      ].map(([a, b]) => `<div class="dd-step"><span class="dd-sm done">${IC.check}</span><div class="t"><b style="font-weight:600">${a}</b><div class="d">${b}</div></div><span></span></div>`).join('')}</div>
      <p style="color:var(--mut);margin:0">${n} works on their own computer, kept apart from everyone else's. Your work and files stay yours.</p></div>`;
  }

  // ------------------------------------------------------------------ one task
  async function viewTask(id) {
    setNav('');
    main.innerHTML = `<div class="dd-wrap"><div class="dd-crumb"><a href="#/">Today</a><span>/</span><span>Task</span></div>
      <div class="dd-thead"><h1 id="tTitle"></h1><div id="tHead" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"></div></div>
      <div class="dd-tcols"><div style="display:flex;flex-direction:column;gap:18px;min-width:0">
        <div id="tQ"></div><section class="dd-card dd-tl" aria-label="Steps"><div class="dd-sect"><h2>Steps</h2><small id="tClock" style="color:var(--lab)"></small></div><div id="tSteps"></div></section>
        <div id="tThink"></div><div id="tReply"></div>
        <form class="dd-card dd-steer" id="steer" aria-label="Tell ${esc(NAME())} something"><textarea id="steerText" rows="1" placeholder="Tell ${esc(NAME())} something while they work…"></textarea><button class="dd-send" type="submit" aria-label="Send">${IC.up}</button></form>
      </div><aside style="display:flex;flex-direction:column;gap:18px">
        <section id="tScreenBox"><div class="dd-sect"><h2>Screen</h2><button type="button" class="dd-lnk" id="watchBtn">Watch the screen</button></div>
          <div class="dd-card dd-screen" id="tScreen"><div class="dd-quiet" style="padding:14px">See the page ${esc(NAME())} is working on, live.</div></div></section>
        <section><div class="dd-sect"><h2>Files</h2></div><div id="tFiles" style="display:flex;flex-direction:column;gap:10px"></div></section>
        <section class="dd-card"><div class="dd-sect" style="padding:16px 18px 0"><h2>Your task</h2></div><div id="tAsk" style="padding:4px 18px 18px;white-space:pre-wrap;color:var(--mut)"></div></section>
        <div class="dd-card dd-safe">${IC.lock}<div>${esc(NAME())} asks before paying, sending, deleting or booking, and never types card numbers, PINs, OTPs or passwords.</div></div>
      </aside></div></div>`;
    const ta = $('#steerText');
    ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(160, ta.scrollHeight) + 'px'; });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#steer').requestSubmit(); } });
    $('#steer').addEventListener('submit', async e => {
      e.preventDefault(); const text = ta.value.trim(); if (!text) return;
      try { await api('POST', `/api/dod/tasks/${enc(id)}/note`, {text}); ta.value = ''; ta.style.height = 'auto'; toast(`${NAME()} will read it at the next step.`); await draw(); }
      catch (ex) { toast(ex.message); }
    });
    let lastQ = '', SAY = {q: '', r: ''};
    main.addEventListener('click', function onSay(e) {
      if (gen !== GEN) { main.removeEventListener('click', onSay); return; }
      const b = e.target.closest('[data-say]'); if (b && SAY[b.dataset.say]) speak(SAY[b.dataset.say]);
    });
    async function draw() {
      const {task: t} = await api('GET', `/api/dod/tasks/${enc(id)}`);
      if (gen !== GEN) return;
      $('#tTitle').textContent = t.title;
      const open = ['queued', 'working', 'needs_you'].includes(t.status);
      $('#tHead').innerHTML = tag(t.status) + (open ? `<button class="dd-btn s bad" type="button" id="stopBtn">Stop</button>` : `<a class="dd-btn s" href="#/">Give another task</a>`);
      $('#tClock').textContent = t.started_at ? (open ? 'Working for ' : 'Took ') + dur(t.started_at, open ? null : t.ended_at) : '';
      const qKey = t.question ? t.question.id : '';
      if (qKey !== lastQ) { $('#tQ').innerHTML = t.question ? `<div class="dd-card dd-task ask"><div class="head"><span class="dd-tag warn">Needs your OK</span><small>${esc(ago(t.question.at))}</small></div>${questionBox(t)}<button type="button" class="dd-lnk" data-say="q">${IC.play}Read aloud</button></div>` : ''; lastQ = qKey; }
      SAY = {q: t.question ? [t.question.question, t.question.details].filter(Boolean).join('. ') : '', r: t.reply || ''};
      $('#tSteps').innerHTML = (t.steps || []).map(s => stepRow(s, t.started_at)).join('') || `<div class="dd-step"><span class="dd-sm now"></span><div class="t"><span class="dd-shimmer">${esc(NAME())} is getting ready</span></div><span></span></div>`;
      $('#tThink').innerHTML = (open && t.thought) ? `<div class="dd-think" aria-label="What ${esc(NAME())} is writing">${esc(t.thought.slice(-500))}</div>` : '';
      $('#tReply').innerHTML = t.reply ? `<div class="dd-card dd-reply">${esc(t.reply)}<div><button type="button" class="dd-lnk" data-say="r">${IC.play}Read aloud</button></div></div>` : (t.error ? `<div class="dd-banner">${esc(t.error)}</div>` : '');
      $('#tFiles').innerHTML = (t.files || []).length ? t.files.map(f => fileCard(t, f)).join('') : `<div class="dd-card dd-quiet" style="padding:14px">Files ${esc(NAME())} makes show here.</div>`;
      $('#tAsk').textContent = t.ask;
      $('#steer').hidden = !open;
      $('#tScreenBox').hidden = !open;
      if (!open) { clearInterval(POLL); stopWatch(); }
    }
    let WATCH = null, lastUrl = '';
    function stopWatch() { clearInterval(WATCH); WATCH = null; const b = $('#watchBtn'); if (b) b.textContent = 'Watch the screen'; }
    async function shot() {
      const box = $('#tScreen'); if (!box || document.hidden) return;
      try {
        const r = await fetch(`/api/dod/tasks/${enc(id)}/screen`, {headers: {Authorization: 'Bearer ' + TOKEN}});
        if (!r.ok) { if (!lastUrl) box.innerHTML = `<div class="dd-quiet" style="padding:14px">No page open right now. It shows here when ${esc(NAME())} uses a website.</div>`; return; }
        const url = URL.createObjectURL(await r.blob());
        box.innerHTML = `<img src="${url}" alt="The page ${esc(NAME())} is working on"><span class="dd-tag live dd-live"><span class="dd-dot"></span>Live</span>`;
        if (lastUrl) URL.revokeObjectURL(lastUrl);
        lastUrl = url;
      } catch (e) { /* the next look tries again */ }
    }
    $('#watchBtn').addEventListener('click', () => {
      if (WATCH) { stopWatch(); return; }
      $('#watchBtn').textContent = 'Stop watching'; shot(); WATCH = setInterval(() => { if (gen !== GEN) { stopWatch(); return; } shot(); }, 3000);
    });
    const gen = GEN;
    main.addEventListener('click', async function onStop(e) {
      if (gen !== GEN) { main.removeEventListener('click', onStop); return; }
      if (!e.target.closest('#stopBtn')) return;
      const b = e.target.closest('#stopBtn');
      if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = 'Tap again to stop'; setTimeout(() => { if (b.isConnected) { b.dataset.sure = ''; b.textContent = 'Stop'; } }, 4000); return; }
      try { await api('POST', `/api/dod/tasks/${enc(id)}/stop`); toast('Stopped.'); await draw(); } catch (ex) { toast(ex.message); }
    });
    await draw();
    poll(draw, 2000);
  }

  // ------------------------------------------------------------------ her answers + files (anywhere on the page)
  async function sendAnswer(el, choice) {
    const task = el.dataset.task;
    try {
      await api('POST', `/api/dod/tasks/${enc(task)}/answer`, {id: el.dataset.q, hash: el.dataset.hash, choice});
      toast(choice === 'no' ? 'Told: not now.' : 'Done. Work goes on.');
      route();
    } catch (ex) { toast(ex.message); }
  }
  main.addEventListener('click', async e => {
    const a = e.target.closest('[data-answer]');
    if (a) { a.disabled = true; await sendAnswer(a, a.dataset.answer); return; }
    const f = e.target.closest('[data-file]');
    if (f) {
      try {
        const r = await fetch(`/api/dod/tasks/${enc(f.dataset.task)}/files/${enc(f.dataset.file)}`, {headers: {Authorization: 'Bearer ' + TOKEN}});
        if (!r.ok) throw new Error('That file is no longer here.');
        const url = URL.createObjectURL(await r.blob());
        const link = document.createElement('a'); link.href = url; link.download = f.dataset.file; document.body.appendChild(link); link.click();
        setTimeout(() => { URL.revokeObjectURL(url); link.remove(); }, 2000);
      } catch (ex) { toast(ex.message); }
    }
  });
  main.addEventListener('submit', async e => {
    const fm = e.target.closest('.dd-qform'); if (!fm) return;
    e.preventDefault(); const v = fm.querySelector('input').value.trim(); if (!v) return;
    await sendAnswer(fm, v);
  });
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); location.hash = '#/'; setTimeout(() => { const a = $('#ask'); if (a) a.focus(); }, 60); }
  });

  // ------------------------------------------------------------------ router
  async function route() {
    clearInterval(POLL);
    GEN += 1;
    const h = location.hash.replace(/^#\/?/, '');
    try {
      await loadStatus();
      if (!ST.profile && h !== 'setup') { VIEW = 'setup'; await viewSetup(); return; }
      if (h === 'setup') { VIEW = 'setup'; await viewSetup(); return; }
      if (h.startsWith('t/')) { const id = decodeURIComponent(h.slice(2)); VIEW = 'task:' + id; await viewTask(id); return; }
      if (h === 'tasks' || h === 'needs' || h === 'files') { VIEW = h; await viewList(h); return; }
      if (h === 'rules') { VIEW = 'rules'; viewRules(); return; }
      VIEW = 'home'; await viewHome();
    } catch (ex) {
      main.innerHTML = `<div class="dd-empty"><p>${esc(ex.message || 'Hoola DOD could not open.')}</p><button class="dd-btn" type="button" id="retry">Try again</button></div>`;
      $('#retry').addEventListener('click', () => { ST = null; route(); });
    }
  }
  window.addEventListener('hashchange', route);
  route();
})();
