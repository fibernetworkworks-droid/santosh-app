/* v0.890 HOOLA COMPUTER (v0.999.233 COMPUTER V2: top bar with both computers, a hub that picks the machine, each machine's screen with Hoola's pointer + checklist + yes cards) - one section, two computers. Home (two cards) -> Hoola PC workspace (straight in) or Your PC
   (setup steps until it connects, then its workspace). Each computer has its OWN chats (server: kind 'computer'), never
   mixed with her Hoola chats. The live screen shows whatever runs on that computer for her, even a task her voice call
   started. Same sign-in as the console. Routes: #/ , #/hoola[/<chat>], #/mine[/<chat>].
   HOOLA CHAT KIT: the chat column is the shared thread (chatkit.js) - her message shows the moment she sends, ONE
   working row with the real step of the task running on this computer for this chat, replies land word by word,
   Copy / Read aloud under the newest reply, the shared typing box (+ = attach, Send turns into Stop while it works). */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const S = v => (v === null || v === undefined) ? '' : String(v);
  const esc = v => S(v).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const enc = encodeURIComponent;
  let TOKEN = '';
  try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch {}
  const APP = $('#hc');
  if (!TOKEN) { location.replace('/console/'); return; }

  async function api(method, path, body, form) {
    const headers = {Authorization: 'Bearer ' + TOKEN};
    let payload;
    if (form) payload = form; else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    const r = await fetch(path, {method, headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    let data = null; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error((data && typeof data.detail === 'string' && data.detail) || `The server refused the request (${r.status})`);
    return data;
  }
  function toast(msg, bad) {
    const t = $('#toast'); t.textContent = S(msg); t.className = 'hc-toast' + (bad ? ' bad' : ''); t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, 4200);
  }
  const svg = (d, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
  const IC = {
    back: '<path d="M15 18l-6-6 6-6"/>', plus: '<path d="M12 5v14M5 12h14"/>',
    cloud: '<path d="M17.5 19a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.5A4 4 0 0 0 6 19z"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    down: '<path d="M12 3v12M6 11l6 6 6-6M4 21h16"/>', check: '<path d="M5 12l5 5L20 7"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    mark: '<circle cx="12" cy="12" r="3"/><path d="M12 3a9 9 0 0 1 9 9"/><path d="M12 21a9 9 0 0 1-9-9"/>',
    list: '<path d="M4 6h16M4 12h10M4 18h6"/>', redo: '<path d="M4 12a8 8 0 1 0 3-6.2"/><path d="M4 4v4h4"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/>', up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    lock: '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>', key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l2 2"/>',
    warn: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/>'};
  const NAME = {hoola: 'Hoola PC', mine: 'Your PC'};

  const ST = {status: null, which: '', chat: '', chats: [], msgs: [], pair: null, files: [], sending: false,
    frameUrl: '', frameSeq: -1, timers: [], thread: null, bar: null, rows: [], res: null, steps: [], working: false, seq: 0};
  const stripHints = t => S(t).replace(/(?:\n\n\[Web console [^\]\n]*\])+$/, '');
  const when = iso => { if (!iso) return ''; const d = new Date(iso); const m = Math.round((Date.now() - d) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : d.toLocaleDateString(); };
  const resultLine = r => {
    if (!r) return ['', ''];
    const st = S(r.status);
    if (st === 'working' || st === 'queued') return ['run', 'Working now'];
    if (r.needs_you) return ['wait', 'Waiting for you'];
    if (st === 'done') return ['', 'Done' + (r.made && r.made.length ? ` · ${r.made.length} file${r.made.length > 1 ? 's' : ''}` : '')];
    if (st) return ['', st[0].toUpperCase() + st.slice(1)];
    return ['', ''];
  };

  function stopTimers() {
    ST.timers.forEach(clearInterval); ST.timers = [];
    if (ST.thread) { ST.thread.clear(); ST.thread = null; }      // the chat column is about to be redrawn
    ST.bar = null; ST.rows = []; ST.res = null; ST.steps = []; ST.working = false; ST.loading = false; ST._sig = ''; ST.drawn = false;
  }
  function every(ms, fn) { ST.timers.push(setInterval(fn, ms)); }

  /* ---------------------------------------------------------------- routing */
  function route() {
    const p = (location.hash.replace(/^#\/?/, '') || '').split('/').filter(Boolean);
    stopTimers();
    ST.which = p[0] === 'hoola' || p[0] === 'mine' ? p[0] : '';
    ST.connect = p[0] === 'connect';
    ST.chat = p[1] || '';
    ST.msgs = []; ST.files = []; ST.frameSeq = -1;
    load();
  }
  async function load() {
    try { ST.status = await api('GET', '/api/computer'); } catch (e) { APP.innerHTML = `<div class="hc-empty">${esc(e.message)}</div>`; return; }
    if (ST.connect) { ST.connecting = !!ST.status.mine.devices.length; setup(); every(3000, setupPoll); return; }   // v0.999.145 add a PC
    if (!ST.which) { home(); every(5000, refreshStatus); return; }
    if (ST.which === 'mine' && (!ST.status.mine.on || !ST.status.mine.devices.length)) { setup(); every(3000, setupPoll); return; }
    await workspace();
  }
  async function refreshStatus() {
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    if (!ST.which && !ST.connect) { const a = document.activeElement; if (a && a.id === 'ask') return homeShots(); home(); }   // never under her typing
  }

  /* ---------------------------------------------------------------- v0.999.233 COMPUTER V2 (her prototype "One job on each
     computer" -> "GO"): one top bar with the two machines as tabs; the hub asks "What should a computer do for you?",
     Hoola picks the machine and says why, the chosen machine lights up; a job opens on that machine's own screen with
     Hoola's pointer, its thought, a checklist of the real steps, and the cards that need her (sign in privately, yes /
     not now, move to my PC). Chat, live screen, take control and the private sign-in below are the same code as before. */
  const devName = () => { const d = (ST.status && ST.status.mine.devices || [])[0]; return d ? d.name : 'Your PC'; };
  const osOf = d => { const o = S(d && d.os).toLowerCase(); return o.startsWith('darwin') || o.includes('mac') ? 'Mac' : o.startsWith('linux') ? 'Linux' : 'Windows'; };
  function topbar() {
    const h = ST.status.hoola, m = ST.status.mine, here = ST.connect ? 'connect' : ST.which || 'home';
    const dot = (busy, on) => `<i class="cx-dot${busy ? ' busy' : on ? ' on' : ''}"></i>`;
    const mineOk = m.on && m.devices.length;
    return `<header class="cx-top">
      <a class="cx-mark" href="/console/" aria-label="Hoola - back to Hoola chat">${window.HoolaMark ? HoolaMark.svg() : '<img src="/static/hoola-mark.png" alt="" width="26" height="26">'}</a>
      <a class="cx-title" href="#/"${here === 'home' ? ' aria-current="page"' : ''}>Computer</a>
      <nav class="cx-tabs" aria-label="Computers">
        <a href="#/hoola"${here === 'hoola' ? ' aria-current="page"' : ''}>${dot(!!h.running, h.online)}Hoola PC</a>
        <a href="${mineOk ? '#/mine' : '#/connect'}"${here === 'mine' || here === 'connect' ? ' aria-current="page"' : ''}>${dot(!!m.running, m.online)}${esc(mineOk ? devName() : 'Your PC')}</a>
      </nav>
      <a class="cx-back" href="/console/">${svg(IC.back)}Back to Hoola chat</a>
      <nav class="cx-links" aria-label="PC tools">
        <a href="/console/pcjobs">All jobs</a><a href="/console/pcjobs#/routines">Routines</a><a href="/console/pcjobs#/rules">Your rules</a>
      </nav>
    </header>`;
  }
  const frame = (inner, cls) => `<div class="cx${cls ? ' ' + cls : ''}">${topbar()}<div class="cx-body">${inner}</div></div>`;
  // kept for the older checks that look for the old sidebar's links
  function side() { return ''; }

  /* ---------------------------------------------------------------- the hub */
  const ago = sec => { const m = Math.round((Date.now() / 1000 - sec) / 60); return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };
  const took = j => { const s = j.ended && j.started ? Math.max(1, j.ended - j.started) : 0; return !s ? ago(j.started) : s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  function machine(which, run, chosen) {
    const h = ST.status.hoola, m = ST.status.mine, mineOk = m.on && m.devices.length, onl = m.devices.filter(d => d.online);
    const hoola = which === 'hoola';
    const state = hoola ? (run ? `<b class="busy">Working · step ${esc(run.step)}</b>` : h.online ? '<b class="ok">Ready</b>' : '<b>Starting</b>')
      : !m.on ? '<b>Not set up</b>' : !m.devices.length ? '<b>Waiting for your PC</b>'
      : run ? `<b class="busy">Working · step ${esc(run.step)}</b>` : onl.length ? `<b class="ok">Online${m.chrome ? ' · Chrome connected' : ''}</b>` : '<b>Offline · open Hoola Desktop</b>';
    const line = hoola ? "Hoola's own computer in the cloud. Awake 24×7, your logins in your own locked folder."
      : mineOk ? `${esc(osOf(onl[0] || m.devices[0]))} · your internet, your Chrome and your apps.` : 'Connect it for sites that refuse cloud computers.';
    return `<a class="cx-machine${chosen ? ' chosen' : ''}" data-machine="${which}" href="${hoola ? '#/hoola' : mineOk ? '#/mine' : '#/connect'}">
      <span class="cx-art ${hoola ? 'cloud' : 'laptop'}" data-shot="${which}" data-sid="${run ? esc(run.session_id) : ''}"><span class="scr"></span>${hoola ? '' : '<span class="base"></span>'}</span>
      <span class="cx-mtext"><span class="cx-mname">${hoola ? 'Hoola PC' : esc(mineOk ? devName() : 'Your PC')}</span>
        <span class="cx-mline">${line}</span>${state}${run ? `<span class="cx-mthought">${esc(S(run.thought).trim() || S(run.task))}</span>` : ''}</span></a>`;
  }
  function home() {
    const h = ST.status.hoola, m = ST.status.mine;
    const askVal = ($('#ask') || {}).value || ST.askText || '', where = ST.askWhere || 'auto';
    const mineOk = m.on && m.devices.length;
    APP.innerHTML = frame(`<main class="cx-hub">
      <h1 class="cx-q">What should a computer do for you?</h1>
      <form class="cx-ask" id="askForm" autocomplete="off">
        <label class="sr" for="ask">Give Hoola a computer job</label>
        <textarea id="ask" rows="2" placeholder="Download my October GSTR-2B and tell me which suppliers haven't filed">${esc(askVal)}</textarea>
        <div class="cx-askrow">
          <div class="cx-where" role="radiogroup" aria-label="Where it runs">
            ${[['auto', 'Let Hoola choose'], ['hoola', 'Hoola PC'], ['mine', mineOk ? devName() : 'Your PC']].map(([k, t]) =>
              `<button type="button" role="radio" aria-checked="${where === k}" data-where="${k}">${esc(t)}</button>`).join('')}</div>
          <button class="cx-go hc-go" type="submit" aria-label="Start the job">${svg(IC.up)}</button>
        </div>
      </form>
      <div class="cx-route" id="route" role="status" hidden></div>
      <section class="cx-machines" aria-label="Your computers">${machine('hoola', h.running)}${machine('mine', m.running)}</section>
      <section class="cx-today" aria-label="Today">
        <div class="cx-sec"><h2>Recent jobs</h2><a href="/console/pcjobs">See all</a></div>
        <ul class="cx-jobs" id="jobs"><li class="mut">Loading…</li></ul>
        <div class="cx-twocol">
          <div class="cx-panel"><div class="cx-sec"><h2>Routines</h2><a href="/console/pcjobs#/routines">Manage</a></div>
            <p class="cx-small">A job that went well, saved. It runs again in seconds, with no AI, and asks only for what changes.</p><div id="routines"></div></div>
          <div class="cx-panel"><div class="cx-sec"><h2>You stay in charge</h2><a href="/console/pcjobs#/rules">Your rules</a></div>
            <ul class="cx-ticks"><li>${svg(IC.check)}Paying, sending, deleting and saving files wait for your yes.</li>
              <li>${svg(IC.check)}Passwords, OTPs and national sign-ins stay yours.</li><li id="ruleLine">${svg(IC.check)}Your rules for sites</li></ul>
            <label class="sw cx-mineSw">Use my PC for jobs<input type="checkbox" role="switch" id="mineSw" ${m.on ? 'checked' : ''}></label></div>
        </div>
      </section>
    </main>`, 'cx-home');
    $('#mineSw').addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine', {on: e.target.checked}); ST.status.mine.on = e.target.checked; home();
        if (e.target.checked && !ST.status.mine.devices.length) location.hash = '#/connect'; }
      catch (err) { toast(err.message, true); e.target.checked = !e.target.checked; }
    });
    const ask = $('#ask');
    ask.addEventListener('input', e => { ST.askText = e.target.value; });
    ask.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); $('#askForm').requestSubmit(); } });
    document.querySelector('.cx-where').addEventListener('click', e => { const b = e.target.closest('[data-where]'); if (!b) return;
      ST.askWhere = b.dataset.where; for (const x of document.querySelectorAll('[data-where]')) x.setAttribute('aria-checked', x === b); });
    $('#askForm').addEventListener('submit', homeAsk);
    homeShots(); homeLists();
  }
  async function homeShots() {          // the live picture of what each computer is doing right now, inside its drawing
    for (const el of document.querySelectorAll('[data-shot]')) {
      const sid = el.dataset.sid; if (!sid) continue;
      try {
        const r = await fetch(`/api/browser/${enc(sid)}/frame`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
        if (!r.ok) continue;
        const u = URL.createObjectURL(await r.blob()), v = el.querySelector('.scr');
        ST.homeUrls = (ST.homeUrls || []); ST.homeUrls.push(u);
        v.innerHTML = `<img src="${u}" alt="Live screen of ${esc(NAME[el.dataset.shot])}">`;
      } catch {}
    }
    while ((ST.homeUrls || []).length > 6) URL.revokeObjectURL(ST.homeUrls.shift());
  }
  async function homeLists() {
    const [jobs, rts, rules] = await Promise.all([api('GET', '/api/pc/trace?limit=6').catch(() => null),
      api('GET', '/api/pc/routines').catch(() => null), api('GET', '/api/pc/rules').catch(() => null)]);
    const J = $('#jobs');
    if (J) {
      const rows = (jobs && jobs.jobs) || [];
      const tone = st => st === 'done' ? 'ok' : st === 'running' ? 'busy' : st === 'needs_confirm' || st === 'partial' ? 'wait' : st === 'failed' || st === 'cancelled' ? 'bad' : '';
      const word = st => ({done: 'Done', running: 'Working', needs_confirm: 'Waiting for you', partial: 'Stopped part-way', failed: 'Did not finish', cancelled: 'Stopped'})[st] || S(st);
      J.innerHTML = rows.length ? rows.map(j => `<li class="cx-job ${tone(j.status)}">
          <span class="cx-pill ${j.kind === 'hoola_pc' ? 'v' : ''}">${j.kind === 'hoola_pc' ? 'Hoola PC' : esc(devName())}</span>
          <b>${esc(S(j.task).replace(/\s*\(Originally:.*$/, '').slice(0, 110))}</b>
          <span class="cx-jmeta"><span>${esc(word(j.status))}</span> · ${esc(j.steps || 0)} steps · ${esc(took(j))}</span>
          <a href="/console/pcjobs#/job/${enc(j.job)}">Watch it again</a></li>`).join('')
        : '<li class="mut cx-empty">No computer jobs yet. Give one above and watch it happen.</li>';
    }
    const R = $('#routines');
    if (R) {
      const rows = ((rts && rts.routines) || []).slice(0, 3);
      R.innerHTML = rows.length ? rows.map(r => `<div class="hc-rt"><span><b>${esc(r.name)}</b><small>${(r.blanks || []).length ? 'asks for ' + esc(r.blanks.map(b => b.name).join(', ')) : 'nothing to fill'} · ran ${esc(r.runs || 0)}×</small></span>
          <a class="btn xs" href="/console/pcjobs#/routines">Run</a></div>`).join('')
        : '<p class="cx-small mut">None yet. After a job goes well, say "save that as a routine".</p>';
    }
    const L = $('#ruleLine');
    if (L && rules) { const n = (rules.never || []).length, a = (rules.ask || []).length, t = (rules.notes || []).length;
      L.innerHTML = `${svg(IC.check)}${n} never-open site${n === 1 ? '' : 's'} · ${a} ask-first site${a === 1 ? '' : 's'}${t ? ` · ${t} note${t === 1 ? '' : 's'} of yours` : ''}`; }
  }
  async function homeAsk(e) {
    e.preventDefault();
    const text = S($('#ask').value).trim(); if (!text) { $('#ask').focus(); return; }
    const go = $('.cx-go'); if (go.disabled) return; go.disabled = true;
    let which = ST.askWhere || 'auto', why = '';
    try {
      if (which === 'auto') { const c = await api('POST', '/api/computer/choose', {text}); which = c.which; why = c.why; }
      else why = which === 'hoola' ? 'you chose it' : 'you chose it';
      if (which === 'mine' && !(ST.status.mine.on && ST.status.mine.devices.length)) { location.hash = '#/connect'; toast('Connect your PC first'); return; }
      // say where it goes and why, light that machine up, then open its screen
      const rt = $('#route');
      if (rt) { rt.className = `cx-route ${which === 'hoola' ? 'v' : ''}`; rt.innerHTML = `${svg(IC.arrow)}<span><b>${esc(which === 'hoola' ? 'Hoola PC' : devName())}</b> · ${esc(why)}</span>`; rt.hidden = false; }
      for (const mc of document.querySelectorAll('[data-machine]')) mc.classList.toggle('chosen', mc.dataset.machine === which);
      const r = await api('POST', `/api/computer/${which}/chats`);
      await api('POST', `/api/conversations/${enc(r.id)}/messages`, {text, client_id: 'hc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)});
      ST.askText = '';
      await new Promise(res => setTimeout(res, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 900));
      location.hash = `#/${which}/${enc(r.id)}`;
    } catch (err) { toast(err.message, true); }
    finally { go.disabled = false; }
  }

  /* ---------------------------------------------------------------- Connect your PC */
  function guessOs() { const p = S(navigator.userAgentData && navigator.userAgentData.platform || navigator.platform || navigator.userAgent).toLowerCase();
    return p.includes('mac') ? 'mac' : p.includes('linux') && !p.includes('android') ? 'linux' : 'windows'; }
  function setup() {
    const m = ST.status.mine, code = ST.pair && ST.pair.code;
    const os = ST.os || guessOs(), dl = (m.downloads || {})[os] || m.download;
    const OSN = {windows: ['Windows', 'Windows 10 or 11', 'SantoshDesktop.exe · about 20 MB'], mac: ['Mac', 'Apple-chip Macs', 'Hoola Desktop for Mac (zip) · right-click > Open the first time'],
      linux: ['Linux', 'X11 desktops', 'Hoola-Desktop-linux.tar.gz · run ./SantoshDesktop']};
    const step = (n, cls, title, sub, right) => `<li class="hc-step ${cls}"><span class="n">${cls === 'done' ? svg(IC.check) + '<span class="sr">Done:</span>' : n}</span>
      <div class="t"><b>${title}</b><span>${sub}</span></div>${right || ''}</li>`;
    APP.innerHTML = frame(`<main class="hc-main hc-connect cx-connect">
        <header class="hc-top"><div><h1 class="cx-q sm">Connect your computer</h1><p class="hc-lead">Three steps, about two minutes. Some sites refuse cloud computers; on your own computer Hoola uses your internet, your Chrome and your apps.</p></div>
          <label class="sw">Use my PC<input type="checkbox" role="switch" id="mineSw" ${m.on ? 'checked' : ''}></label></header>
        ${!m.on ? `<p class="hc-lead">Turn on "Use my PC" to start.</p>` : `
        <div class="hc-os" role="radiogroup" aria-label="Your computer">
          ${Object.entries(OSN).map(([k, [t, sub]]) => `<button type="button" role="radio" aria-checked="${k === os}" data-os="${k}"><b>${t}</b><span>${sub}</span></button>`).join('')}</div>
        <ol class="hc-steplist" aria-label="Steps">
          ${step(1, code ? 'done' : 'now', 'Download Hoola Desktop', esc(OSN[os][2]),
            `<a class="btn${code ? '' : ' pri'}" href="${esc(dl)}" id="dl" rel="noopener">${svg(IC.down)}${code ? 'Download again' : 'Download'}</a>`)}
          ${step(2, code ? 'now' : '', 'Open it and type this code', code ? 'The code works once and expires in 10 minutes.' : 'Get a code after the download starts.',
            code ? `<div class="hc-codebox"><span class="code">${esc(S(code).replace(/^(\d{3})(\d{3})$/, '$1 $2'))}</span>
              <button class="btn sm" type="button" id="newCode">New code</button></div>`
                 : `<button class="btn sm" type="button" id="newCode">Show my code</button>`)}
          ${step(3, '', 'Let Hoola work in your Chrome', 'In Hoola Desktop open Browser extension, add it to Chrome, then press "Let Hoola work on my pages".', '<span class="mut hc-opt">optional</span>')}
        </ol>
        <div class="hc-wait" role="status"><i></i>Waiting for your computer… this page opens its screen by itself when it connects.</div>`}
        <section class="hc-safe" aria-label="Safety">
          <div><b>You stay in control</b><span>A banner with Stop shows on your screen while Hoola works.</span></div>
          <div><b>Asks before big steps</b><span>Paying, sending, deleting and saving files always wait for your yes.</span></div>
          <div><b>Turn off any time</b><span>Switch off "Use my PC" and Hoola stops using it.</span></div>
        </section>
      </main>`, 'cx-setup');
    $('#mineSw').addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine', {on: e.target.checked}); ST.status.mine.on = e.target.checked; setup(); }
      catch (err) { toast(err.message, true); }
    });
    const osg = document.querySelector('.hc-os'); if (osg) osg.addEventListener('click', e => { const b = e.target.closest('[data-os]'); if (b) { ST.os = b.dataset.os; setup(); } });
    const getCode = async () => { try { ST.pair = await api('POST', '/api/computer/mine/pair'); setup(); } catch (err) { toast(err.message, true); } };
    const nc = $('#newCode'); if (nc) nc.addEventListener('click', getCode);
    const d = $('#dl'); if (d) d.addEventListener('click', () => { if (!ST.pair) setTimeout(getCode, 300); });
  }
  async function setupPoll() {
    const before = ST.status ? ST.status.mine.devices.length : 0;
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    if (ST.status.mine.on && ST.status.mine.devices.length > (ST.connecting ? before : 0)) {
      toast('Your computer is connected'); stopTimers(); ST.which = 'mine'; ST.connecting = false; history.replaceState(null, '', '#/mine'); workspace(); }
  }

  /* ---------------------------------------------------------------- a machine's screen */
  async function workspace() {
    const w = ST.which;
    try { ST.chats = (await api('GET', `/api/computer/${w}/chats`)).chats || []; } catch (e) { toast(e.message, true); ST.chats = []; }
    if (!ST.chat) {
      const first = ST.chats[0];
      if (first) { history.replaceState(null, '', `#/${w}/${enc(first.id)}`); ST.chat = first.id; }
      else {
        try { const r = await api('POST', `/api/computer/${w}/chats`); ST.chat = r.id; history.replaceState(null, '', `#/${w}/${enc(r.id)}`);
          ST.chats = (await api('GET', `/api/computer/${w}/chats`)).chats || []; } catch (e) { toast(e.message, true); }
      }
    }
    drawWorkspace();
    await loadMsgs(true);
    every(2500, () => loadMsgs(false));
    every(3000, liveTick);
    liveTick();
  }
  function chatRows() {
    return ST.chats.map(c => { const [cls, line] = resultLine(c.result);
      return `<button type="button" class="hc-chat" data-chat="${esc(c.id)}" ${c.id === ST.chat ? 'aria-current="page"' : ''}>
        <b>${esc(c.empty ? 'New job' : c.title)}</b><span class="${cls}">${esc(line || when(c.updated_at))}</span></button>`; }).join('');
  }
  function drawWorkspace() {
    const w = ST.which, m = ST.status.mine, hoola = w === 'hoola';
    const foot = hoola
      ? `<div class="hc-foot">
          <div class="hc-tile">${svg(IC.lock)}<span><b>Your locked folder</b>Logins and downloads, only yours</span></div>
          ${ST.status.hoola.email ? `<div class="hc-tile">${svg(IC.mail)}<span><b>Hoola's own email</b><span class="hc-mail">${esc(ST.status.hoola.email)}</span></span></div>` : ''}
          <button class="hc-tile" type="button" id="savedBtn">${svg(IC.key)}<span><b>Saved sign-ins</b>Used only when you tap</span></button></div>`
      : `<div class="hc-foot hc-card2">
          ${m.devices.map(d => `<span class="hc-st"><span class="dot ${d.online ? 'ok' : ''}"></span>${esc(d.name)} · ${esc(osOf(d))} · ${d.online ? 'online' : 'offline'}</span>`).join('')}
          <span class="hc-st"><span class="dot ${m.chrome ? 'ok' : ''}"></span>${m.chrome ? 'Works in your Chrome' : 'Chrome extension not connected'}</span>
          <label class="sw">Work in the background<input type="checkbox" role="switch" id="bgSw" ${m.background ? 'checked' : ''}></label>
          <span class="hc-small">Hoola uses buttons and fields and never takes your mouse or keyboard without asking.</span>
          <button class="hc-nav" type="button" id="addPc">${svg(IC.plus)}Add another computer</button>
          <button class="hc-nav" type="button" id="offPc" style="color:var(--bad)">Turn off "Use my PC"</button></div>`;
    const chrome = hoola
      ? `<div class="cx-chrome dk"><span class="lights"><i></i><i></i><i></i></span><span class="u" id="stUrl">Hoola PC</span><span class="live" id="stLive" hidden><i></i>live</span></div>`
      : `<div class="cx-chrome tabs"><span class="tab">Your tabs</span><span class="tab hoola" id="stTab" hidden><i></i><span id="stUrl">Hoola</span></span></div>
         <div class="cx-banner" id="stBanner" hidden>Hoola is working in this tab <button type="button" data-stop>Stop</button></div>`;
    APP.innerHTML = frame(`
      <nav class="cx-list" aria-label="${esc(NAME[w])} jobs">
        <button class="hc-new" type="button" id="newTask">${svg(IC.plus)}New job</button>
        <div class="hc-lab">Jobs on ${esc(hoola ? 'Hoola PC' : devName())}</div><div id="chatList">${chatRows()}</div>${foot}
      </nav>
      <section class="cx-stage" aria-label="Live screen">
        <header class="hc-stagehead"><div><h1 id="stTitle">${esc(hoola ? 'Hoola PC' : devName())}</h1><span id="stSub">Nothing running right now</span></div>
          <div class="hc-acts"><button class="btn sm" type="button" id="takeBtn" hidden>Take control</button>
          <button class="btn sm stop" type="button" id="stopBtn" hidden>Stop</button></div></header>
        <div class="cx-device ${hoola ? 'dk' : 'lt'}">${chrome}
          <div class="cx-view hc-view" id="stView">${!hoola && !m.online ? 'Your computer is offline. Open Hoola Desktop on it, then give the job here.' : 'Give a job and watch it happen here.'}</div>
          <span class="cx-ptr" id="ptr" hidden aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 2l16 9-7 2-3 7z"/></svg><b>Hoola</b></span>
          <div class="cx-think hc-think"><span class="dot" id="stDot"></span><span id="stThink">Waiting for a job</span></div>
        </div>
        <div class="hc-hands" id="hands" hidden>
          <p class="hc-handsnote">You have control. Click on the screen, type below, then press <b>I'm done</b>. Hoola waits and never sees what you type.</p>
          <form class="hc-typer" id="typer" autocomplete="off"><input id="typeIn" type="text" autocomplete="off" spellcheck="false" placeholder="Type into the computer" aria-label="Type into the computer">
            <button class="btn sm" type="submit">Type</button></form>
          <div class="hc-keys">${['Enter', 'Tab', 'Backspace', 'Escape'].map(k => `<button class="btn sm" type="button" data-key="${k}">${k === 'Escape' ? 'Esc' : k}</button>`).join('')}
            <button class="btn sm" type="button" data-scroll="3">Scroll up</button><button class="btn sm" type="button" data-scroll="-3">Scroll down</button></div>
        </div>
        <div class="hc-also" id="also" hidden></div>
      </section>
      <aside class="cx-side" aria-label="This job and its chat">
        <div class="cx-now" id="jobPanel">
          <span class="cx-pill ${hoola ? 'v' : ''}">${hoola ? 'Hoola PC · cloud' : esc(devName()) + ' · your computer'}</span>
          <h2 class="cx-jt" id="jobTitle">No job running</h2>
          <ol class="cx-check" id="steps" aria-label="Steps"></ol>
          <form class="hc-login cx-card" id="login" hidden autocomplete="off"></form>
          <div class="cx-card amber" id="approve" role="status" hidden></div>
          <div class="cx-card amber" id="move" role="status" hidden></div>
        </div>
        <div class="hc-chatcol cx-chat" aria-label="${esc(NAME[w])} chat">
          <div class="hc-chathead"><b>Chat</b><span>only for ${esc(hoola ? 'Hoola PC' : devName())}</span></div>
          ${!hoola && !m.online ? '<div class="hc-off">Your computer is offline right now. Hoola will tell you if a job needs it on.</div>' : ''}
          <div class="hc-msgs" id="msgs"><div id="thread" class="hck-tight"></div></div>
          <div class="hc-need" id="need" role="status" hidden></div>
          <div class="hc-comp"><div class="hc-files" id="files"></div>
            <div id="bar"></div><input type="file" id="fileIn" hidden multiple></div>
        </div>
      </aside>`, 'cx-work');
    ST.thread = HoolaChat.mount($('#thread'), {scroller: $('#msgs'), jump: true});
    ST.bar = HoolaChat.bar($('#bar'), {placeholder: `Tell ${hoola ? 'Hoola PC' : devName()} what to do`, plus: true,
      onSend: text => send(text), onStop: stopTurn, onPlus: () => $('#fileIn').click()});
    // a file with no words can go too: the shared box sends only words, so the button is opened here
    const go = $('#bar .go');
    const fileOnly = () => !ST.bar.working && !ST.bar.value.trim() && ST.files.length > 0;
    ST.bar.input.addEventListener('input', () => { if (fileOnly()) go.disabled = false; });
    ST.bar.input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && fileOnly()) send(''); });
    go.addEventListener('click', () => { if (fileOnly()) send(''); });
    $('#newTask').addEventListener('click', async () => {
      try { const r = await api('POST', `/api/computer/${w}/chats`); location.hash = `#/${w}/${enc(r.id)}`; } catch (e) { toast(e.message, true); }
    });
    $('#chatList').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (b) location.hash = `#/${w}/${enc(b.dataset.chat)}`; });
    $('#fileIn').addEventListener('change', upload);
    $('#stopBtn').addEventListener('click', stopRun);
    const bs = document.querySelector('[data-stop]'); if (bs) bs.addEventListener('click', stopRun);
    const sb = $('#savedBtn'); if (sb) sb.addEventListener('click', savedList);
    $('#takeBtn').addEventListener('click', toggleTake);
    $('#stView').addEventListener('click', screenClick);
    $('#typer').addEventListener('submit', e => { e.preventDefault(); const i = $('#typeIn'); const t = i.value; if (!t) return;
      i.value = ''; hand({op: 'type', text: t}); });
    $('#hands').addEventListener('click', e => { const k = e.target.closest('[data-key]'), sc = e.target.closest('[data-scroll]');
      if (k) hand({op: 'key', keys: k.dataset.key});
      if (sc) { const im = $('#stView img'); hand({op: 'scroll', x: im ? im.naturalWidth / 2 : 640, y: im ? im.naturalHeight / 2 : 400, amount: +sc.dataset.scroll}); } });
    $('#login').addEventListener('submit', sendLogin);
    $('#approve').addEventListener('click', e => { const b = e.target.closest('[data-yes]'); if (b) decide(b.dataset.yes === '1'); });
    const bgs = $('#bgSw'); if (bgs) bgs.addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine/background', {on: e.target.checked}); ST.status.mine.background = e.target.checked;
        toast(e.target.checked ? 'Hoola works in the background on your computer' : 'Hoola may use your mouse and keyboard again'); }
      catch (err) { e.target.checked = !e.target.checked; toast(err.message, true); }
    });
    const add = $('#addPc'); if (add) add.addEventListener('click', () => { ST.pair = null; location.hash = '#/connect'; });
    const off = $('#offPc'); if (off) off.addEventListener('click', async () => {
      if (!confirm('Turn off "Use my PC"? Hoola will stop using your computer.')) return;
      try { await api('PUT', '/api/computer/mine', {on: false}); location.hash = '#/'; } catch (e) { toast(e.message, true); }
    });
    ST.bar.focus();
  }

  function merge(rows) {
    if (!ST.rows.length || !rows.length) { if (rows.length || !ST.rows.length) ST.rows = rows; return; }
    const got = new Set(rows.map(r => r.id)), have = new Map(ST.rows.map(r => [r.id, r]));
    if (ST.rows.some(r => r.id >= rows[0].id && !got.has(r.id))) { ST.rows = rows; return; }   // the list was rewritten
    const max = ST.rows[ST.rows.length - 1].id;
    for (const r of rows) { if (r.id > max) ST.rows.push(r); else if (have.has(r.id)) have.get(r.id).text = r.text; }
  }
  const lastIsHers = () => { const l = ST.rows[ST.rows.length - 1]; return !!l && l.role === 'user'; };
  const myRun = () => { const run = ST.status && ST.status[ST.which] && ST.status[ST.which].running; return run && run.conv === ST.chat ? run : null; };
  async function loadMsgs(first) {
    if (!ST.chat || ST.loading) return;
    const chat = ST.chat; ST.loading = true;
    try {
      // how her newest ask stands (queued / working / needs her / ended): asked only while something may be running,
      // and BEFORE the rows, so "ended" with no reply in the rows really means no reply came
      const ask = async () => {
        const seq = ST.seq; let r = null;
        try { r = await api('GET', `/api/conversations/${enc(chat)}/result`); } catch { /* an old server: the rows alone decide */ }
        if (seq === ST.seq) ST.res = r;                // she sent meanwhile: an answer from before her message says nothing
      };
      if (!first && (ST.sending || ST.working || lastIsHers() || myRun() || (ST.res && ST.res.needs_you))) await ask();
      let rows;
      try { rows = (await api('GET', `/api/conversations/${enc(chat)}/messages?limit=200`)).messages || []; } catch { return; }
      if (chat !== ST.chat || !ST.thread) return;
      const sig = rows.map(r => r.id).join(',');
      const changed = sig !== ST._sig;
      ST._sig = sig; merge(rows);
      if (first && lastIsHers()) { await ask(); if (chat !== ST.chat || !ST.thread) return; }
      paintThread();
      if (!first && changed) refreshChats();
    } finally { ST.loading = false; }
  }
  /* ONE picture of the chat for the kit: the rows, whether Hoola is working, the working row's words and steps */
  function paintThread() {
    if (!ST.thread) return;
    const run = myRun(), st = ST.res ? S(ST.res.status) : null;
    const working = ST.sending || !!run || (st === null ? lastIsHers() : st === 'working' || st === 'queued');
    if (run) {
      const id = run.session_id + ':' + run.step, words = S(run.thought).trim() || `Step ${run.step}`;
      const cur = ST.steps[ST.steps.length - 1];
      if (!cur || cur.id !== id) { if (cur) { cur.state = 'done'; cur.send = true; } ST.steps.push({id, label: words, send: true}); }
      else if (cur.label !== words) { cur.label = words; cur.send = true; }
    } else if (ST.steps.length) { const cur = ST.steps[ST.steps.length - 1]; if (!cur.state) { cur.state = 'done'; cur.send = true; } }
    const steps = ST.steps.filter(x => x.send).map(x => { x.send = false; return {id: x.id, label: x.label, state: x.state}; });
    if (!working) ST.steps = [];
    const label = run ? (run.status === 'queued' ? 'Waiting for a free Hoola PC' : run.status === 'needs_confirm' ? 'Waiting for your OK' : S(run.thought).trim() || 'Working on the computer')
      : ST.res && (st === 'working' || st === 'queued') && ST.res.line ? S(ST.res.line) : 'Thinking…';
    const messages = ST.rows.map(r => ({id: r.id, role: r.role === 'user' ? 'her' : 'hoola', text: r.role === 'user' ? stripHints(r.text) : S(r.text)}));
    // what was already in the chat when it opened is drawn whole (the first call), never landed again
    if (!ST.drawn) { ST.drawn = true; if (working && messages.length) ST.thread.sync({key: ST.chat, messages, working: false}); }
    ST.thread.sync({key: ST.chat, working, label, steps: working ? steps : [], messages});
    ST.working = working;
    if (!working) paintMove(); else { const mv = $('#move'); if (mv) mv.hidden = true; }
    if (ST.bar) ST.bar.working = working && !ST.sending;
    const need = $('#need');
    if (need) { const on = !working && !!(ST.res && ST.res.needs_you); need.hidden = !on; need.textContent = on ? `Waiting for you: ${S(ST.res.line)}` : ''; }
  }
  async function refreshChats() {
    try { ST.chats = (await api('GET', `/api/computer/${ST.which}/chats`)).chats || []; } catch { return; }
    const l = $('#chatList'); if (l) l.innerHTML = chatRows();
  }
  async function send(text) {
    text = S(text).trim();
    if ((!text && !ST.files.length) || ST.sending || !ST.chat || !ST.thread) { if (text && ST.bar) ST.bar.value = text; return; }
    const say = text || 'Here is the file.', files = ST.files.slice();
    ST.sending = true; ST.res = null; ST.seq++;
    const mine = ST.thread.her(say, {pending: true, files: files.map(f => f.name)});   // on screen the moment she sends
    const box = $('#thread'), ho = box && box.lastElementChild && box.lastElementChild.previousElementSibling;
    if (ho && ho.classList.contains('hck-ho') && ho.querySelector('.hck-work') && !ho.querySelector('.hck-txt')) box.append(ho);   // sent while Hoola works: the working row stays last
    ST.files = []; drawFiles(); paintThread();
    let ok = true;
    try {
      await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: say, files: files.map(f => f.file_id),
        client_id: 'hc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)});
    } catch (e) { ok = false; toast(e.message, true); mine.remove(); if (ST.bar) ST.bar.value = text; ST.files = files; drawFiles(); }
    ST.sending = false;
    if (ok) { ST.seq++; ST.res = {status: 'queued', needs_you: false, line: ''}; await loadMsgs(false); }   // accepted: waiting to start
    paintThread();
  }
  async function stopTurn() {
    const run = myRun();
    try {
      await api('POST', `/api/conversations/${enc(ST.chat)}/stop`);
      if (run) await api('POST', `/api/browser/${enc(run.session_id)}/stop`).catch(() => {});
      toast('Stopping. The step that was running may stop halfway.'); liveTick();
    } catch (e) { toast(e.message, true); }
  }
  async function upload(e) {
    for (const f of Array.from(e.target.files || []).slice(0, 6 - ST.files.length)) {
      const fd = new FormData(); fd.append('file', f);
      try { const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, fd);
        ST.files.push({file_id: r.file_id || r.id, name: f.name}); } catch (err) { toast(err.message, true); }
    }
    e.target.value = ''; drawFiles();
  }
  function drawFiles() {
    const b = $('#files'); if (b) b.innerHTML = ST.files.map(f => `<span>${esc(f.name)}</span>`).join('');
    const go = $('#bar .go'); if (go && ST.bar && !ST.bar.working && !ST.bar.value.trim()) go.disabled = !ST.files.length;
  }

  /* ---------------------------------------------------------------- live screen */
  async function liveTick() {
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    const run = ST.status[ST.which] && ST.status[ST.which].running;
    const t = $('#stTitle'); if (!t) return;
    paintThread();                                     // the working row follows the task's real step
    const stop = $('#stopBtn'), view = $('#stView'), mine = ST.which === 'mine';
    const show = (sel, on) => { const el = $(sel); if (el) el.hidden = !on; };
    show('#stLive', !!run); show('#stTab', !!run); show('#stBanner', !!run && mine);
    if (!run) {
      t.textContent = mine ? devName() : NAME[ST.which]; $('#stSub').textContent = 'Nothing running right now';
      $('#stThink').textContent = 'Waiting for a job'; $('#stDot').className = 'dot'; stop.hidden = true;
      $('#jobTitle').textContent = 'No job running';
      ST.run = null; paintHands(null); paintSteps(null); paintApprove(null);
      return;
    }
    ST.run = run; paintHands(run); paintSteps(run); paintApprove(run);
    t.textContent = mine ? devName() : NAME[ST.which];
    $('#jobTitle').textContent = S(run.task).replace(/\s*\(Originally:.*$/, '').slice(0, 140);
    const secs = Math.max(0, Math.round(Date.now() / 1000 - run.started)), long = secs < 86400 ? ` · ${secs < 60 ? secs + ' s' : Math.floor(secs / 60) + ' min'}` : '';
    $('#stSub').textContent = `${mine && ST.status.mine.chrome ? 'In your Chrome · ' : run.pc ? run.pc + ' · ' : ''}step ${run.step}${run.from === 'call' ? ' · started on your voice call' : run.from === 'chat' ? ' · started from a Hoola chat' : ''}${long}`;
    $('#stThink').textContent = run.thought || (run.status === 'queued' ? 'Waiting for a free Hoola PC' : run.status === 'needs_confirm' ? 'Waiting for your yes' : 'Working…');
    $('#stDot').className = 'dot ' + (run.status === 'needs_confirm' ? 'wait' : 'run');
    stop.hidden = false; stop.dataset.sid = run.session_id;
    try {
      const lv = await api('GET', `/api/browser/${enc(run.session_id)}/live`);
      if (lv && lv.url) { let u = S(lv.url); try { u = new URL(u).host.replace(/^www\./, '') || u; } catch {} $('#stUrl').textContent = mine ? 'Hoola · ' + u : u; }
      if (lv && lv.seq !== ST.frameSeq) {
        const r = await fetch(`/api/browser/${enc(run.session_id)}/frame`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
        if (r.ok) {
          const u = URL.createObjectURL(await r.blob());
          if (ST.frameUrl) URL.revokeObjectURL(ST.frameUrl);
          ST.frameUrl = u; ST.frameSeq = lv.seq;
          view.className = 'cx-view hc-view has'; view.innerHTML = `<img src="${u}" alt="Live screen of ${esc(NAME[ST.which])}">`;
          const im = view.querySelector('img'); im.addEventListener('load', placePointer, {once: true});
        }
      }
    } catch {}
  }
  /* the job's own steps as a checklist beside the screen (its step record), and Hoola's pointer on the screen at the
     place of the last click it made */
  const plain = x => { const a = S(x.thought).trim() || S(x.action || x.tool).replace(/_/g, ' ');
    return a.length > 90 ? a.slice(0, 88) + '…' : a; };
  async function paintSteps(run) {
    const el = $('#steps'); if (!el) return;
    if (!run) { el.innerHTML = ''; el.dataset.sig = ''; ST.ptr = null; placePointer(); return; }
    let d = null;
    try { d = await api('GET', `/api/pc/trace/${enc(run.session_id)}`); } catch { return; }
    if (!ST.run || ST.run.session_id !== run.session_id) return;
    const rows = ((d && (d.steps_list || d.steps)) || []).filter(x => typeof x === 'object');
    const last = rows.slice(-8), hidden = rows.length - last.length;
    const sig = run.session_id + ':' + rows.length + ':' + run.status;
    if (el.dataset.sig !== sig) { el.dataset.sig = sig; el.innerHTML = (hidden > 0 ? `<li class="more">${hidden} earlier step${hidden === 1 ? '' : 's'}</li>` : '') +
      last.map((x, i) => { const now = i === last.length - 1 && run.status !== 'needs_confirm';
        return `<li class="${now ? 'now' : 'done'}"><i aria-hidden="true">${now ? '' : svg(IC.check)}</i><span>${esc(plain(x))}</span><span class="sr">${now ? ' (now)' : ' (done)'}</span></li>`; }).join('')
      || '<li class="now"><i aria-hidden="true"></i><span>Getting the computer ready</span></li>'; }   // redrawn only when a step lands
    const click = [...rows].reverse().find(x => x.args && isFinite(+x.args.x) && isFinite(+x.args.y));
    ST.ptr = click ? {x: +click.args.x, y: +click.args.y} : null;
    placePointer();
  }
  function placePointer() {
    const p = $('#ptr'), im = $('#stView img'), dev = document.querySelector('.cx-device');
    if (!p) return;
    if (!ST.ptr || !im || !im.naturalWidth || !dev) { p.hidden = true; return; }
    const r = im.getBoundingClientRect(), d = dev.getBoundingClientRect();
    p.style.left = `${r.left - d.left + ST.ptr.x * r.width / im.naturalWidth}px`;
    p.style.top = `${r.top - d.top + ST.ptr.y * r.height / im.naturalHeight}px`;
    p.hidden = false;
  }
  window.addEventListener('resize', () => placePointer());
  /* a step that needs her yes (paying, sending, deleting, saving a file): the question and two buttons, answered here */
  function paintApprove(run) {
    const el = $('#approve'); if (!el) return;
    const pd = run && run.status === 'needs_confirm' && run.pending;
    if (!pd || !pd.id) { el.hidden = true; el.dataset.id = ''; return; }
    if (el.dataset.id === pd.id) return;
    el.dataset.id = pd.id; el.dataset.sid = run.session_id;
    el.innerHTML = `<b>${svg(IC.shield)}Hoola needs your yes</b><p>${esc(pd.what || 'A step that cannot be undone')}</p>
      <div class="cx-acts"><button class="btn sm pri" type="button" data-yes="1">Yes, do it</button><button class="btn sm" type="button" data-yes="0">Not now</button></div>`;
    el.hidden = false;
  }
  async function decide(yes) {
    const el = $('#approve'); const sid = el.dataset.sid, id = el.dataset.id; if (!sid || !id) return;
    for (const b of el.querySelectorAll('button')) b.disabled = true;
    try { await api('POST', `/api/computer/task/${enc(sid)}/decide`, {yes, id}); toast(yes ? 'Hoola carries on' : 'Hoola will not do that step');
      el.hidden = true; el.dataset.id = ''; liveTick(); }
    catch (e) { toast(e.message, true); for (const b of el.querySelectorAll('button')) b.disabled = false; }
  }
  function paintMove() {
    const el = $('#move'); if (!el || ST.which !== 'hoola') return;
    const lastHoola = [...ST.rows].reverse().find(r => r.role !== 'user');
    const hit = lastHoola && /refuses cloud computers|refusing a CLOUD computer|needs HER own PC|from (your|her) own PC/i.test(S(lastHoola.text));
    const m = ST.status && ST.status.mine;
    if (!hit || !m) { el.hidden = true; return; }
    const ask = (ST.rows.find(r => r.role === 'user') || {}).text || '';
    el.innerHTML = `<b>${svg(IC.warn)}This site refuses cloud computers</b><p>Hoola can do it on your PC${m.online ? '' : ' when it is on'}, with your own internet.</p>
      <div class="cx-acts">${m.on && m.devices.length ? `<button class="btn sm pri" type="button" id="moveBtn"${ask ? '' : ' disabled'}>Move to my PC</button>` : '<a class="btn sm pri" href="#/connect">Connect your PC</a>'}</div>`;
    el.hidden = false;
    const b = $('#moveBtn'); if (b) b.addEventListener('click', async () => {
      try { const r = await api('POST', '/api/computer/mine/chats');
        await api('POST', `/api/conversations/${enc(r.id)}/messages`, {text: stripHints(ask), client_id: 'hc' + Date.now().toString(36)});
        location.hash = `#/mine/${enc(r.id)}`; toast('Moved to your PC'); } catch (e) { toast(e.message, true); } });
  }

  /* ---------------------------------------------------------------- her hands: take control, the sign-in form */
  function paintHands(run) {
    const take = $('#takeBtn'), hands = $('#hands'), view = $('#stView'), login = $('#login'), also = $('#also');
    if (!take) return;
    const on = !!(run && run.takeover);
    take.hidden = !run || run.status === 'queued' || ST.which !== 'hoola';   // on her own PC she uses her own mouse
    take.textContent = on ? "I'm done" : 'Take control';
    take.classList.toggle('pri', on);
    take.dataset.sid = run ? run.session_id : '';
    hands.hidden = !on; view.classList.toggle('tk', on);
    // v0.999.145 only the polling speed changes here: stopTimers() also wipes the chat column (the chat kit), which left
    // every Hoola Computer chat blank after the first live check
    if (on !== !!ST.fastLive) { ST.fastLive = on; ST.timers.forEach(clearInterval); ST.timers = []; every(2500, () => loadMsgs(false)); every(on ? 1000 : 3000, liveTick); }
    const lg = run && run.login;
    if (lg && login.dataset.id !== lg.id) {
      login.dataset.id = lg.id; login.dataset.sid = run.session_id;
      login.innerHTML = `<b>Sign in to ${esc(lg.site)}</b><span class="mut">Private: typed straight into ${esc(NAME[ST.which])}. Hoola never sees it${lg.can_save ? ', and it is kept only if you tick Save' : ', and it is not kept'}.</span>
        ${lg.onepw ? `<button class="btn sm pri" type="button" id="useOnepw">Use 1Password sign-in · ${esc(lg.onepw.title)}${lg.onepw.user ? ' (' + esc(lg.onepw.user) + ')' : ''}</button>` : ''}
        ${lg.saved ? `<button class="btn sm${lg.onepw ? '' : ' pri'}" type="button" id="useSaved">Use saved sign-in${lg.saved.user ? ' (' + esc(lg.saved.user) + ')' : ''}</button><span class="mut">or type another one:</span>` : ''}
        ${lg.fields === 'password' ? '' : '<input name="u" type="text" autocomplete="off" spellcheck="false" placeholder="User name" aria-label="User name">'}
        <input name="p" type="password" autocomplete="new-password" placeholder="Password" aria-label="Password" required>
        ${lg.can_save ? '<label class="hc-save"><input type="checkbox" name="s"> Save for next time (kept locked; used only when you tap)</label>' : ''}
        <div class="hc-loginacts"><button class="btn sm${lg.saved ? '' : ' pri'}" type="submit">Type it in</button>
        <button class="btn sm" type="button" id="selfSign">I'll sign in myself</button></div>`;
      $('#selfSign').addEventListener('click', () => sendLogin(null, true));
      const us = $('#useSaved'); if (us) us.addEventListener('click', () => sendLogin(null, false, true));
      const u1 = $('#useOnepw'); if (u1) u1.addEventListener('click', () => sendLogin(null, false, false, true));
    }
    login.hidden = !lg;
    if (!lg) login.dataset.id = '';
    const others = (run && run.others) || [];
    also.hidden = !others.length;
    also.textContent = others.length ? 'Also working at the same time: ' + others.map(o => `${o.task}${o.status === 'queued' ? ' (waiting for a free Hoola PC)' : o.pc ? ' on ' + o.pc : ''}`).join(' · ') : '';
  }
  async function toggleTake() {
    const sid = $('#takeBtn').dataset.sid; if (!sid) return;
    const on = !(ST.run && ST.run.takeover);
    try { await api('POST', `/api/computer/task/${enc(sid)}/takeover`, {on}); toast(on ? 'You have control - Hoola is waiting' : 'Hoola carries on'); liveTick(); }
    catch (e) { toast(e.message, true); }
  }
  async function hand(body) {
    const sid = ST.run && ST.run.takeover ? ST.run.session_id : ''; if (!sid) return;
    try { await api('POST', `/api/computer/task/${enc(sid)}/input`, body); ST.frameSeq = -1; liveTick(); } catch (e) { toast(e.message, true); }
  }
  function screenClick(e) {
    if (!(ST.run && ST.run.takeover)) return;
    const im = e.target.closest('img'); if (!im) return;
    const r = im.getBoundingClientRect();
    const x = (e.clientX - r.left) * im.naturalWidth / r.width, y = (e.clientY - r.top) * im.naturalHeight / r.height;
    hand({op: e.detail === 2 ? 'double_click' : 'click', x, y});
  }
  async function sendLogin(e, self, saved, onepw) {
    if (e) e.preventDefault();
    const f = $('#login'); const sid = f.dataset.sid, id = f.dataset.id; if (!id) return;
    const u = f.querySelector('[name=u]'), p = f.querySelector('[name=p]'), sv = f.querySelector('[name=s]');
    const body = self ? {id, skip: true} : onepw ? {id, use_onepw: true} : saved ? {id, use_saved: true}
      : {id, username: u ? u.value : '', password: p ? p.value : '', save: !!(sv && sv.checked)};
    if (u) u.value = ''; if (p) p.value = '';
    try {
      await api('POST', `/api/computer/task/${enc(sid)}/login`, body);
      f.hidden = true; f.dataset.id = '';
      if (self) { await api('POST', `/api/computer/task/${enc(sid)}/takeover`, {on: true}); toast('You have control - sign in, then press I\'m done'); }
      else toast('Typed in for you');
      liveTick();
    } catch (err) { toast(err.message, true); }
  }
  async function savedList() {
    let rows = [], op = {};
    try { rows = (await api('GET', '/api/computer/logins')).logins || []; op = await api('GET', '/api/computer/1password'); }
    catch (e) { toast(e.message, true); return; }
    const d = document.createElement('dialog'); d.className = 'hc-dlg';
    d.innerHTML = `<b>Saved sign-ins</b><p class="mut"><a href="/console/?v=cred">Open Hoola Cred</a> - your own password manager; a login there switched to "Hoola may use" shows up here. `+ `Kept locked on Hoola's server. Hoola uses one only when you tap "Use saved sign-in". Bank and payment sign-ins are never saved.</p>
      ${rows.length ? rows.map(r => `<div class="hc-srow"><div><b>${esc(r.label)}</b><span class="mut">${esc(r.site)}${r.user ? ' · ' + esc(r.user) : ''}</span></div>
        <button class="btn sm" type="button" data-del="${esc(r.id)}">Delete</button></div>`).join('') : '<p class="mut">Nothing saved yet. Tick "Save for next time" on a sign-in form.</p>'}
      <div class="hc-1p"><b>1Password</b>${op.connected
        ? `<p class="mut">Connected · Hoola reads only the vault <b>${esc(op.vault)}</b>. A login there that lists a site is offered as "Use 1Password sign-in" - typed only when you tap.</p>
           <button class="btn sm" type="button" data-1poff>Disconnect 1Password</button>`
        : `<p class="mut">In 1Password, make a vault for Hoola (e.g. "Hoola") with the portal logins Hoola may use, then create a <b>service account</b> with read access to that vault only and paste its token here. It is kept locked and never shown again.${op.installed === false ? ' (1Password support is still installing on the server - run the deploy again.)' : ''}</p>
           <form class="hc-1pform" data-1pform autocomplete="off"><input name="t" type="password" autocomplete="off" placeholder="ops_..." aria-label="1Password service account token" required>
           <button class="btn sm pri" type="submit">Connect</button></form><div data-1pvaults></div>`}</div>
      <div class="hc-loginacts"><button class="btn sm" type="button" data-close>Close</button></div>`;
    document.body.appendChild(d); d.showModal();
    const f1 = d.querySelector('[data-1pform]');
    const connect1p = async (body) => {
      const r = await api('POST', '/api/computer/1password', body);
      if (r.vaults && r.vaults.length) {
        d.querySelector('[data-1pvaults]').innerHTML = `<p class="mut">This token can see more than one vault - pick the one for Hoola:</p>` +
          r.vaults.map(v => `<button class="btn sm" type="button" data-1pv="${esc(v.id)}">${esc(v.name)}</button>`).join(' ');
        return;
      }
      toast(r.note || `1Password connected · vault ${r.vault}`); d.close(); d.remove();
    };
    if (f1) f1.addEventListener('submit', async ev => { ev.preventDefault(); const t = f1.querySelector('[name=t]'); const v = t.value; t.value = '';
      try { await connect1p({token: v}); } catch (err) { toast(err.message, true); } });
    d.addEventListener('click', async ev => {
      const pv = ev.target.closest('[data-1pv]');
      if (pv) { try { await connect1p({vault_id: pv.getAttribute('data-1pv')}); } catch (err) { toast(err.message, true); } return; }
      if (ev.target.closest('[data-1poff]')) { if (!confirm('Disconnect 1Password from Hoola?')) return;
        try { await api('DELETE', '/api/computer/1password'); toast('1Password disconnected'); d.close(); d.remove(); } catch (err) { toast(err.message, true); } return; }
      const del = ev.target.closest('[data-del]');
      if (del) { try { await api('DELETE', `/api/computer/logins/${enc(del.dataset.del)}`); del.closest('.hc-srow').remove(); toast('Deleted'); } catch (err) { toast(err.message, true); } }
      if (ev.target.closest('[data-close]') || ev.target === d) { d.close(); d.remove(); }
    });
  }
  async function stopRun() {
    const sid = $('#stopBtn').dataset.sid; if (!sid) return;
    try { await api('POST', `/api/browser/${enc(sid)}/stop`); toast('Stopped'); liveTick(); } catch (e) { toast(e.message, true); }
  }

  document.addEventListener('click', e => { const b = e.target.closest('[data-go]'); if (b) location.hash = b.dataset.go; });
  window.addEventListener('hashchange', route);
  route();
})();
