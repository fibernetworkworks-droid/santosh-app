/* v0.890 HOOLA COMPUTER - one section, two computers. Home (two cards) -> Hoola PC workspace (straight in) or Your PC
   (setup steps until it connects, then its workspace). Each computer has its OWN chats (server: kind 'computer'), never
   mixed with her Hoola chats. The live screen shows whatever runs on that computer for her, even a task her voice call
   started. Same sign-in as the console. Routes: #/ , #/hoola[/<chat>], #/mine[/<chat>]. */
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
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>', send: '<path d="M12 19V5M5 12l7-7 7 7"/>',
    clip: '<path d="M21 12l-8.5 8.5a5 5 0 0 1-7-7L14 5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 8"/>',
    down: '<path d="M12 3v12M6 11l6 6 6-6M4 21h16"/>', check: '<path d="M5 12l5 5L20 7"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    mark: '<circle cx="12" cy="12" r="3"/><path d="M12 3a9 9 0 0 1 9 9"/><path d="M12 21a9 9 0 0 1-9-9"/>'};
  const NAME = {hoola: 'Hoola PC', mine: 'Your PC'};

  const ST = {status: null, which: '', chat: '', chats: [], msgs: [], pair: null, files: [], sending: false,
    frameUrl: '', frameSeq: -1, timers: []};
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

  function stopTimers() { ST.timers.forEach(clearInterval); ST.timers = []; }
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
          <div><b>One voice call for both computers</b><span>Say "Hoola PC pe karo" or "mere PC pe karo". The work shows on that computer's screen here.</span></div>
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
      ? `<div class="hc-note"><b>Your locked folder</b>Logins and downloads stay in your own folder on Hoola PC. Nobody else sees them.</div>`
      : `<div style="margin-top:auto;display:flex;flex-direction:column;gap:4px">
          <button class="hc-nav" type="button" id="addPc">${svg(IC.plus)}Add another PC</button>
          <button class="hc-nav" type="button" id="offPc" style="color:var(--bad)">Turn off "Use my PC"</button></div>`;
    APP.innerHTML = side(`${pcRow}<button class="hc-new" type="button" id="newTask">${svg(IC.plus)}New task</button>
        <div class="hc-lab">${esc(NAME[w])} chats</div><div id="chatList">${chatRows()}</div>${foot}`) +
      `<section class="hc-stage" aria-label="Live screen">
        <header class="hc-stagehead"><div><h1 id="stTitle">${esc(NAME[w])}</h1><span id="stSub">Nothing running right now</span></div>
          <button class="btn sm stop" type="button" id="stopBtn" hidden>Stop</button></header>
        <div class="hc-screen"><div class="hc-bar"><span class="d"><i></i><i></i><i></i></span><span class="u" id="stUrl">${esc(NAME[w])}</span></div>
          <div class="hc-view" id="stView">${w === 'mine' && !m.online ? 'Your PC is offline. Open Hoola Desktop on it, then give the task here.' : 'The live screen shows here while Hoola works.'}</div>
          <div class="hc-think"><span class="dot" id="stDot"></span><span id="stThink">Waiting for a task</span></div></div>
      </section>
      <aside class="hc-chatcol" aria-label="${esc(NAME[w])} chat">
        <div class="hc-chathead"><b>Chat</b><span>only for ${esc(NAME[w])}</span></div>
        ${w === 'mine' && !m.online ? '<div class="hc-off">Your PC is offline right now. Hoola will tell you if a task needs it on.</div>' : ''}
        <div class="hc-msgs" id="msgs" aria-live="polite"></div>
        <div class="hc-comp"><div class="hc-files" id="files"></div>
          <div class="hc-box"><label class="sr" for="say">Message ${esc(NAME[w])}</label>
            <textarea id="say" rows="2" placeholder="Tell ${esc(NAME[w])} what to do…"></textarea>
            <input type="file" id="fileIn" hidden multiple>
            <button class="ib" type="button" id="attach" aria-label="Attach Excel or file">${svg(IC.clip)}</button>
            <button class="ib pri" type="button" id="sendBtn" aria-label="Send">${svg(IC.send)}</button></div></div>
      </aside>`;
    $('#newTask').addEventListener('click', async () => {
      try { const r = await api('POST', `/api/computer/${w}/chats`); location.hash = `#/${w}/${enc(r.id)}`; } catch (e) { toast(e.message, true); }
    });
    $('#chatList').addEventListener('click', e => { const b = e.target.closest('[data-chat]'); if (b) location.hash = `#/${w}/${enc(b.dataset.chat)}`; });
    const say = $('#say');
    say.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    say.addEventListener('input', () => { say.style.height = 'auto'; say.style.height = Math.min(say.scrollHeight, 180) + 'px'; });
    $('#sendBtn').addEventListener('click', send);
    $('#attach').addEventListener('click', () => $('#fileIn').click());
    $('#fileIn').addEventListener('change', upload);
    $('#stopBtn').addEventListener('click', stopRun);
    const add = $('#addPc'); if (add) add.addEventListener('click', async () => { stopTimers(); ST.pair = null; setup(); every(3000, setupPoll); });
    const off = $('#offPc'); if (off) off.addEventListener('click', async () => {
      if (!confirm('Turn off "Use my PC"? Hoola will stop using your computer.')) return;
      try { await api('PUT', '/api/computer/mine', {on: false}); location.hash = '#/'; } catch (e) { toast(e.message, true); }
    });
    say.focus();
  }

  async function loadMsgs(first) {
    if (!ST.chat) return;
    let rows;
    try { rows = (await api('GET', `/api/conversations/${enc(ST.chat)}/messages?limit=80`)).messages || []; } catch { return; }
    const sig = rows.map(r => r.id).join(',');
    if (!first && sig === ST._sig) return;
    ST._sig = sig;
    const box = $('#msgs'); if (!box) return;
    const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
    const last = rows[rows.length - 1];
    const waiting = ST.sending || (last && last.role === 'user');
    box.innerHTML = rows.map(r => r.role === 'user'
      ? `<div class="m-u">${esc(stripHints(r.text))}</div>`
      : `<div class="m-a">${window.HoolaMD ? HoolaMD.render(S(r.text)) : esc(r.text)}</div>`).join('') +
      (waiting ? '<div class="m-work"><span class="dot run"></span>Hoola is working…</div>' : '');
    if (first || atEnd) box.scrollTop = box.scrollHeight;
    if (!first) refreshChats();
  }
  async function refreshChats() {
    try { ST.chats = (await api('GET', `/api/computer/${ST.which}/chats`)).chats || []; } catch { return; }
    const l = $('#chatList'); if (l) l.innerHTML = chatRows();
  }
  async function send() {
    const say = $('#say'); const text = say.value.trim();
    if ((!text && !ST.files.length) || ST.sending || !ST.chat) return;
    ST.sending = true; $('#sendBtn').disabled = true;
    try {
      await api('POST', `/api/conversations/${enc(ST.chat)}/messages`, {text: text || 'Here is the file.',
        files: ST.files.map(f => f.file_id), client_id: 'hc' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7)});
      say.value = ''; say.style.height = ''; ST.files = []; drawFiles();
    } catch (e) { toast(e.message, true); }
    ST.sending = false; $('#sendBtn').disabled = false;
    ST._sig = ''; loadMsgs(false);
  }
  async function upload(e) {
    for (const f of Array.from(e.target.files || []).slice(0, 6 - ST.files.length)) {
      const fd = new FormData(); fd.append('file', f);
      try { const r = await api('POST', `/api/conversations/${enc(ST.chat)}/files`, undefined, fd);
        ST.files.push({file_id: r.file_id || r.id, name: f.name}); } catch (err) { toast(err.message, true); }
    }
    e.target.value = ''; drawFiles();
  }
  function drawFiles() { const b = $('#files'); if (b) b.innerHTML = ST.files.map(f => `<span>${esc(f.name)}</span>`).join(''); }

  /* ---------------------------------------------------------------- live screen */
  async function liveTick() {
    try { ST.status = await api('GET', '/api/computer'); } catch { return; }
    const run = ST.status[ST.which] && ST.status[ST.which].running;
    const t = $('#stTitle'); if (!t) return;
    const stop = $('#stopBtn'), view = $('#stView');
    if (!run) {
      t.textContent = NAME[ST.which]; $('#stSub').textContent = 'Nothing running right now';
      $('#stThink').textContent = 'Waiting for a task'; $('#stDot').className = 'dot'; stop.hidden = true;
      return;
    }
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
  async function stopRun() {
    const sid = $('#stopBtn').dataset.sid; if (!sid) return;
    try { await api('POST', `/api/browser/${enc(sid)}/stop`); toast('Stopped'); liveTick(); } catch (e) { toast(e.message, true); }
  }

  document.addEventListener('click', e => { const b = e.target.closest('[data-go]'); if (b) location.hash = b.dataset.go; });
  window.addEventListener('hashchange', route);
  route();
})();
