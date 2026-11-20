/* v0.890 HOOLA COMPUTER - one section, two computers. Home (two cards) -> Hoola PC workspace (straight in) or Your PC
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
    mark: '<circle cx="12" cy="12" r="3"/><path d="M12 3a9 9 0 0 1 9 9"/><path d="M12 21a9 9 0 0 1-9-9"/>'};
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
    ST.chat = p[1] || '';
    ST.msgs = []; ST.files = []; ST.frameSeq = -1;
    load();
  }
  async function load() {
    try { ST.status = await api('GET', '/api/computer'); } catch (e) { APP.innerHTML = `<div class="hc-empty">${esc(e.message)}</div>`; return; }
    if (!ST.which) { home(); every(5000, refreshStatus); return; }
    if (ST.which === 'mine' && (!ST.status.mine.on || !ST.status.mine.devices.length)) { setup(); every(3000, setupPoll); return; }
    await workspace();
  }
  async function refreshStatus() {
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    if (!ST.which) home();
  }

  /* ---------------------------------------------------------------- shared sidebar */
  function side(inner) {
    return `<nav class="hc-side" aria-label="Hoola Computer">
      <a class="hc-brand" href="/console/"><i>${svg(IC.mark)}</i>Hoola</a>
      ${ST.which ? `<a class="hc-nav" href="#/">${svg(IC.back)}Hoola Computer</a>
        <div class="hc-seg" role="tablist" aria-label="Computer">
          <button type="button" role="tab" aria-selected="${ST.which === 'hoola'}" data-go="#/hoola">Hoola PC</button>
          <button type="button" role="tab" aria-selected="${ST.which === 'mine'}" data-go="#/mine">Your PC</button></div>`
        : `<a class="hc-nav" href="/console/">${svg(IC.back)}Back to chats</a>
           <a class="hc-nav" href="#/" aria-current="page">${svg(IC.pc)}Hoola Computer</a>`}
      ${inner || ''}
    </nav>`;
  }

  /* ---------------------------------------------------------------- home */
  function home() {
    const h = ST.status.hoola, m = ST.status.mine;
    const hrun = h.running, mrun = m.running;
    const hState = !h.online ? '<span class="mut"><span class="dot"></span>Offline - Hoola is starting it</span>'
      : hrun ? `<span style="color:var(--acct)"><span class="dot run"></span>Working · ${esc(hrun.task.slice(0, 48))}</span>`
      : '<span class="okt"><span class="dot ok"></span>Online · ready</span>';
    const mState = !m.on ? '<span class="mut">Not set up</span>'
      : !m.devices.length ? '<span class="mut">Waiting for your PC to connect</span>'
      : mrun ? `<span style="color:var(--acct)"><span class="dot run"></span>Working · ${esc(mrun.task.slice(0, 48))}</span>`
      : m.online ? `<span class="okt"><span class="dot ok"></span>Online · ${esc(m.devices.filter(d => d.online).map(d => d.name).join(', '))}</span>`
      : `<span class="mut"><span class="dot"></span>Offline · open Hoola Desktop on ${esc(m.devices[0].name)}</span>`;
    const last = l => l ? `<div class="hc-last"><small>Last work</small><span>${esc(l.title)}</span>
        <span class="mut" style="font-size:13px">${esc(resultLine(l.result)[1])}</span></div>` : '';
    APP.innerHTML = side(`<div class="hc-note"><b>Separate chats</b>Each computer keeps its own chats here. They never show in your Hoola chats.</div>`) +
      `<main class="hc-main">
        <header><h1>Hoola Computer</h1><p class="hc-lead">Give Hoola work that needs a real computer: portals, forms, downloads, repeat entries. Pick where it runs.</p></header>
        <section class="hc-cards" aria-label="Computers">
          <article class="hc-card">
            <div class="hc-head"><div class="hc-ico v">${svg(IC.cloud, '')}</div><div><h2>Hoola PC</h2>${hState}</div></div>
            <p>Hoola's own computer in the cloud. Works even when your PC is off. Your logins and files sit in your own locked folder.</p>
            ${last(h.last)}
            <a class="btn pri" href="#/hoola">Open workspace${svg(IC.arrow)}</a>
          </article>
          <article class="hc-card">
            <div class="hc-head"><div class="hc-ico">${svg(IC.pc, '')}</div><div><h2>Your PC</h2>${mState}</div>
              <label class="sw">Use my PC<input type="checkbox" role="switch" id="mineSw" ${m.on ? 'checked' : ''}></label></div>
            <p>Hoola works on your own Windows computer, with your home internet. Best for sites that refuse cloud computers, like Aadhaar and Parivahan.</p>
            ${m.on && m.devices.length ? last(m.last) : `<ol class="hc-steps"><li>Download Hoola Desktop (.exe)</li><li>Open it and type the 6-digit code</li><li>Done. Your PC shows here as online</li></ol>`}
            <a class="btn${m.on && m.devices.length ? ' pri' : ''}" href="#/mine">${m.on && m.devices.length ? 'Open workspace' + svg(IC.arrow) : 'Set up my PC'}</a>
          </article>
        </section>
        <section class="hc-call" aria-label="Voice call"><i>${svg(IC.phone)}</i>
          <div><b>One voice call for both computers</b><span>Say "run it on Hoola PC" or "run it on my PC". The work shows on that computer's screen here.</span></div>
          <a class="btn dark sm" href="/console/">Open Hoola to call</a></section>
      </main>`;
    $('#mineSw').addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine', {on: e.target.checked}); ST.status.mine.on = e.target.checked; home();
        if (e.target.checked && !ST.status.mine.devices.length) location.hash = '#/mine'; }
      catch (err) { toast(err.message, true); e.target.checked = !e.target.checked; }
    });
  }

  /* ---------------------------------------------------------------- Your PC setup */
  function setup() {
    const m = ST.status.mine, code = ST.pair && ST.pair.code;
    const step = (n, cls, title, sub, right) => `<li class="hc-step ${cls}"><span class="n">${cls === 'done' ? svg(IC.check) + '<span class="sr">Done:</span>' : n}</span>
      <div class="t"><b>${title}</b><span>${sub}</span></div>${right || ''}</li>`;
    APP.innerHTML = side(`<div class="hc-lab">Your PC chats will show here once your computer is connected.</div>`) +
      `<main class="hc-main">
        <header style="display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start;max-width:880px">
          <div style="flex:1 1 420px"><h1>Connect your PC</h1><p class="hc-lead">Hoola works on your Windows computer with your own internet. Three steps, about two minutes.</p></div>
          <label class="sw" style="margin:8px 0 0">Use my PC<input type="checkbox" role="switch" id="mineSw" ${m.on ? 'checked' : ''}></label></header>
        ${!m.on ? `<p class="hc-lead">Turn on "Use my PC" to start.</p>` : `
        <ol class="hc-steplist" aria-label="Steps">
          ${step(1, code ? 'done' : 'now', 'Download Hoola Desktop', 'Windows 10 or 11 · about 20 MB',
            `<a class="btn${code ? '' : ' pri'}" href="${esc(m.download)}" id="dl" rel="noopener">${svg(IC.down)}${code ? 'Download again' : 'Download .exe'}</a>`)}
          ${step(2, code ? 'now' : '', 'Open it and type this code', code ? 'The code works once and expires in 10 minutes.' : 'Get a code after the download starts.',
            code ? `<div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px"><span class="code">${esc(code)}</span>
              <button class="btn sm" type="button" id="newCode">New code</button></div>`
                 : `<button class="btn sm" type="button" id="newCode">Show my code</button>`)}
          ${step(3, '', 'Waiting for your PC', 'This page opens your PC\'s workspace by itself when it connects.')}
        </ol>`}
        <section class="hc-safe" aria-label="Safety">
          <div><b>You stay in control</b><span>A banner with a Stop button shows on your screen while Hoola works.</span></div>
          <div><b>Asks before big steps</b><span>Paying, sending, deleting and installing always wait for your tap.</span></div>
          <div><b>Turn off any time</b><span>Switch off "Use my PC" and Hoola stops using it.</span></div>
        </section>
      </main>`;
    $('#mineSw').addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine', {on: e.target.checked}); ST.status.mine.on = e.target.checked; setup(); }
      catch (err) { toast(err.message, true); }
    });
    const getCode = async () => { try { ST.pair = await api('POST', '/api/computer/mine/pair'); setup(); } catch (err) { toast(err.message, true); } };
    const nc = $('#newCode'); if (nc) nc.addEventListener('click', getCode);
    const dl = $('#dl'); if (dl) dl.addEventListener('click', () => { if (!ST.pair) setTimeout(getCode, 300); });
  }
  async function setupPoll() {
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    if (ST.status.mine.on && ST.status.mine.devices.length) { toast('Your PC is connected'); stopTimers(); workspace(); }
  }

  /* ---------------------------------------------------------------- workspace */
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
        <b>${esc(c.empty ? 'New task' : c.title)}</b><span class="${cls}">${esc(line || when(c.updated_at))}</span></button>`; }).join('');
  }
  function drawWorkspace() {
    const w = ST.which, m = ST.status.mine;
    const pcRow = w === 'mine' ? (m.devices.map(d => `<div class="hc-pcrow">${svg(IC.pc)}<div><b>${esc(d.name)}</b>
        <span class="${d.online ? 'okt' : 'mut'}"><span class="dot ${d.online ? 'ok' : ''}"></span>${d.online ? 'Online' : 'Offline'}</span></div></div>`).join('')) : '';
    const foot = w === 'hoola'
      ? `${ST.status.hoola.email ? `<div class="hc-note"><b>Hoola's own email</b><span class="hc-mail">${esc(ST.status.hoola.email)}</span>Give it to a site when you want codes and receipts to come straight to Hoola.</div>` : ''}
         <button class="hc-nav" type="button" id="savedBtn">Saved sign-ins</button>
         <div class="hc-note"><b>Your locked folder</b>Logins and downloads stay in your own folder on Hoola PC. Nobody else sees them.</div>`
      : `<div style="margin-top:auto;display:flex;flex-direction:column;gap:4px">
          <div class="hc-note"><label class="sw" style="margin:0">Work in the background<input type="checkbox" role="switch" id="bgSw" ${m.background ? 'checked' : ''}></label>
            Hoola works through your PC's buttons and fields and never takes your mouse or keyboard without asking.</div>
          <button class="hc-nav" type="button" id="addPc">${svg(IC.plus)}Add another PC</button>
          <button class="hc-nav" type="button" id="offPc" style="color:var(--bad)">Turn off "Use my PC"</button></div>`;
    APP.innerHTML = side(`${pcRow}<button class="hc-new" type="button" id="newTask">${svg(IC.plus)}New task</button>
        <div class="hc-lab">${esc(NAME[w])} chats</div><div id="chatList">${chatRows()}</div>${foot}`) +
      `<section class="hc-stage" aria-label="Live screen">
        <header class="hc-stagehead"><div><h1 id="stTitle">${esc(NAME[w])}</h1><span id="stSub">Nothing running right now</span></div>
          <div class="hc-acts"><button class="btn sm" type="button" id="takeBtn" hidden>Take control</button>
          <button class="btn sm stop" type="button" id="stopBtn" hidden>Stop</button></div></header>
        <div class="hc-screen"><div class="hc-bar"><span class="d"><i></i><i></i><i></i></span><span class="u" id="stUrl">${esc(NAME[w])}</span></div>
          <div class="hc-view" id="stView">${w === 'mine' && !m.online ? 'Your PC is offline. Open Hoola Desktop on it, then give the task here.' : 'The live screen shows here while Hoola works.'}</div>
          <div class="hc-think"><span class="dot" id="stDot"></span><span id="stThink">Waiting for a task</span></div></div>
        <div class="hc-hands" id="hands" hidden>
          <p class="hc-handsnote">You have control. Click on the screen, type below, then press <b>I'm done</b>. Hoola waits and never sees what you type.</p>
          <form class="hc-typer" id="typer" autocomplete="off"><input id="typeIn" type="text" autocomplete="off" spellcheck="false" placeholder="Type into the PC" aria-label="Type into the PC">
            <button class="btn sm" type="submit">Type</button></form>
          <div class="hc-keys">${['Enter', 'Tab', 'Backspace', 'Escape'].map(k => `<button class="btn sm" type="button" data-key="${k}">${k === 'Escape' ? 'Esc' : k}</button>`).join('')}
            <button class="btn sm" type="button" data-scroll="3">Scroll up</button><button class="btn sm" type="button" data-scroll="-3">Scroll down</button></div>
        </div>
        <form class="hc-login" id="login" hidden autocomplete="off"></form>
        <div class="hc-also" id="also" hidden></div>
      </section>
      <aside class="hc-chatcol" aria-label="${esc(NAME[w])} chat">
        <div class="hc-chathead"><b>Chat</b><span>only for ${esc(NAME[w])}</span></div>
        ${w === 'mine' && !m.online ? '<div class="hc-off">Your PC is offline right now. Hoola will tell you if a task needs it on.</div>' : ''}
        <div class="hc-msgs" id="msgs"><div id="thread" class="hck-tight"></div></div>
        <div class="hc-need" id="need" role="status" hidden></div>
        <div class="hc-comp"><div class="hc-files" id="files"></div>
          <div id="bar"></div><input type="file" id="fileIn" hidden multiple></div>
      </aside>`;
    ST.thread = HoolaChat.mount($('#thread'), {scroller: $('#msgs'), jump: true});
    ST.bar = HoolaChat.bar($('#bar'), {placeholder: `Tell ${NAME[w]} what to do`, plus: true,
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
    const sb = $('#savedBtn'); if (sb) sb.addEventListener('click', savedList);
    $('#takeBtn').addEventListener('click', toggleTake);
    $('#stView').addEventListener('click', screenClick);
    $('#typer').addEventListener('submit', e => { e.preventDefault(); const i = $('#typeIn'); const t = i.value; if (!t) return;
      i.value = ''; hand({op: 'type', text: t}); });
    $('#hands').addEventListener('click', e => { const k = e.target.closest('[data-key]'), sc = e.target.closest('[data-scroll]');
      if (k) hand({op: 'key', keys: k.dataset.key});
      if (sc) { const im = $('#stView img'); hand({op: 'scroll', x: im ? im.naturalWidth / 2 : 640, y: im ? im.naturalHeight / 2 : 400, amount: +sc.dataset.scroll}); } });
    $('#login').addEventListener('submit', sendLogin);
    const bgs = $('#bgSw'); if (bgs) bgs.addEventListener('change', async e => {
      try { await api('PUT', '/api/computer/mine/background', {on: e.target.checked}); ST.status.mine.background = e.target.checked;
        toast(e.target.checked ? 'Hoola works in the background on your PC' : 'Hoola may use your mouse and keyboard again'); }
      catch (err) { e.target.checked = !e.target.checked; toast(err.message, true); }
    });
    const add = $('#addPc'); if (add) add.addEventListener('click', async () => { stopTimers(); ST.pair = null; setup(); every(3000, setupPoll); });
    const off = $('#offPc'); if (off) off.addEventListener('click', async () => {
      if (!confirm('Turn off "Use my PC"? Hoola will stop using your computer.')) return;
      try { await api('PUT', '/api/computer/mine', {on: false}); location.hash = '#/'; } catch (e) { toast(e.message, true); }
    });
    ST.bar.focus();
  }

  /* the rows only ever grow here (the server sends the newest 200), so a long chat keeps landing new replies */
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
    const stop = $('#stopBtn'), view = $('#stView');
    if (!run) {
      t.textContent = NAME[ST.which]; $('#stSub').textContent = 'Nothing running right now';
      $('#stThink').textContent = 'Waiting for a task'; $('#stDot').className = 'dot'; stop.hidden = true;
      ST.run = null; paintHands(null);
      return;
    }
    ST.run = run; paintHands(run);
    t.textContent = run.task.slice(0, 80);
    const mins = Math.max(0, Math.round((Date.now() / 1000 - run.started) / 6) / 10);
    $('#stSub').textContent = `${run.pc || NAME[ST.which]} · step ${run.step}${run.from === 'call' ? ' · started on your voice call' : run.from === 'chat' ? ' · started from a Hoola chat' : ''} · ${mins} min`;
    $('#stThink').textContent = run.thought || (run.status === 'queued' ? 'Waiting for a free Hoola PC' : 'Working…');
    $('#stDot').className = 'dot ' + (run.status === 'needs_confirm' ? 'wait' : 'run');
    stop.hidden = false; stop.dataset.sid = run.session_id;
    try {
      const lv = await api('GET', `/api/browser/${enc(run.session_id)}/live`);
      if (lv && lv.url) $('#stUrl').textContent = lv.url;
      if (lv && lv.seq !== ST.frameSeq) {
        const r = await fetch(`/api/browser/${enc(run.session_id)}/frame`, {headers: {Authorization: 'Bearer ' + TOKEN}, cache: 'no-store'});
        if (r.ok) {
          const u = URL.createObjectURL(await r.blob());
          if (ST.frameUrl) URL.revokeObjectURL(ST.frameUrl);
          ST.frameUrl = u; ST.frameSeq = lv.seq;
          view.className = 'hc-view has'; view.innerHTML = `<img src="${u}" alt="Live screen of ${esc(NAME[ST.which])}">`;
        }
      }
    } catch {}
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
    if (on !== ST.fastLive) { ST.fastLive = on; stopTimers(); every(2500, () => loadMsgs(false)); every(on ? 1000 : 3000, liveTick); }
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
    d.innerHTML = `<b>Saved sign-ins</b><p class="mut"><a href="/console/cred">Open Hoola Cred</a> - your own password manager; a login there switched to "Hoola may use" shows up here. `+ `Kept locked on Hoola's server. Hoola uses one only when you tap "Use saved sign-in". Bank and payment sign-ins are never saved.</p>
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
