/* v0.745 VIDEO LEARNER, REDESIGNED (owner: "make all screen perfect and all feature functional" -> the approved
   canvas -> "go"). Four screens on one page, same console look:
     home   - teach a task (link / upload) + her learned tasks (Proven / Learned, not tried / Notes / Could not learn)
     watch  - the video plays, Hoola's notes arrive AS GEMINI WRITES THEM (streamed, never paced fakes), every
              [m:ss] jumps the video, the five real stages with their own times, Stop
     task   - the learned steps with their video moments, Before you start / Watch out / Not seen, a form built
              from what the task needs, Do it now
     run    - Hoola doing it: the chat turn's own live steps on this page, a card that needs her = "Answer",
              then "Did it work?" -> Proven
   Rules kept from v0.718: every stage is a real boundary of seekh.watch; learned is NOT proven until she says a
   run worked; nothing is performed by this page itself - Do it now is one chat turn through the composer's door,
   so sending / submitting still asks for her tap; every server value goes through esc(). */
'use strict';
window.HoolaSeekh = function ({api, esc, toast, send, upload, open: go, live}) {
  let EL = null, VIEW = 'home', FILTER = 'all';
  let LIST = null;          // GET /api/seekh/console/watches
  let JOB = null;           // the watch job being shown
  let TASK = null;          // the task page's row
  let RUN = null;           // {cid, after, task, steps:Map, cards:[], text, done, t0}
  let POLL = null, TICK = null;
  const MEDIA = new Map();  // file_id -> blob url
  const STAGES = [['classify', 'Opened the video', 'checked the link'],
                  ['fetch', 'Watching', 'frame by frame, with the sound'],
                  ['notes', 'Writing notes', 'every step with its moment'],
                  ['distill', 'Turning notes into steps', 'a recipe Hoola can follow'],
                  ['memory', 'Saving to memory', 'added to your learned tasks']];
  const mmss = s => { s = Math.max(0, Math.round(+s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const secs = t => { const p = String(t || '').split(':').map(Number); return p.some(isNaN) ? 0 : p.reduce((a, b) => a * 60 + b, 0); };
  const when = iso => { const d = new Date(iso || ''); return isNaN(d) ? '' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit'}); };
  const pct = c => Math.round(Math.min(1, Math.max(0, +c || 0)) * 100);
  const human = v => String(v || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
  const stop = () => { if (POLL) clearInterval(POLL); if (TICK) clearInterval(TICK); POLL = TICK = null; };
  const ICON = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>',
    tick: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>',
    link: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    up: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5M4 20h16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    warn: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 8v5M12 16.5v.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  };

  // ---------------------------------------------------------------- sources and video
  function srcOf(row) {                    // "youtube:ID" | "file:FID" | "url:..." -> {kind, key}
    const s = String((row && (row.source || '')) || ''), i = s.indexOf(':');
    return i < 0 ? {kind: '', key: s} : {kind: s.slice(0, i), key: s.slice(i + 1)};
  }
  function refOf(row) {                    // what to send back to /watch for Try again / Re-learn
    if (row && row.ref) return row.ref;
    const {kind, key} = srcOf(row);
    return kind === 'youtube' ? `https://youtu.be/${key}` : key;
  }
  function thumb(row) {
    const {kind, key} = srcOf(row);
    if (row.status === 'failed') return `<span class="skv-thumb fail" aria-hidden="true">${ICON.warn}</span>`;
    const img = kind === 'youtube' && /^[\w-]{11}$/.test(key) ? `<img src="https://i.ytimg.com/vi/${esc(key)}/mqdefault.jpg" alt="" loading="lazy">` : '';
    return `<span class="skv-thumb" aria-hidden="true">${img}<i>${ICON.play}</i></span>`;
  }
  async function playerHTML(src, start) {   // youtube embed / her uploaded file / a link we cannot embed
    if (src.kind === 'youtube' && /^[\w-]{11}$/.test(src.key)) {
      return `<iframe class="skv-frame" id="skvFrame" title="The video" src="https://www.youtube-nocookie.com/embed/${esc(src.key)}?rel=0&start=${Math.floor(start || 0)}" allow="encrypted-media; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
    }
    if (src.kind === 'file') {
      try {
        if (!MEDIA.has(src.key)) {
          const r = await api('GET', `/api/panel/files/${encodeURIComponent(src.key)}`, undefined, {raw: true});
          MEDIA.set(src.key, URL.createObjectURL(await r.blob()));
        }
        return `<video class="skv-frame" id="skvVideo" controls preload="metadata" src="${MEDIA.get(src.key)}"></video>`;
      } catch { /* falls through to the plain box */ }
    }
    return `<div class="skv-frame skv-noplay">${ICON.play}<span>This video plays at its own link</span>${src.kind === 'url' ? `<a href="${esc(src.key)}" target="_blank" rel="noopener noreferrer">Open the video</a>` : ''}</div>`;
  }
  function seek(t) {                       // a [m:ss] chip: jump the video there
    const s = secs(t), v = EL && EL.querySelector('#skvVideo'), f = EL && EL.querySelector('#skvFrame');
    if (v) { v.currentTime = s; v.play?.().catch(() => {}); return true; }
    if (f) { f.src = f.src.replace(/([?&])start=\d+/, `$1start=${s}`) + (f.src.includes('autoplay=1') ? '' : '&autoplay=1'); return true; }
    return false;
  }
  function markers() {                     // purple ticks on the bar where notes landed (only when the length is known)
    const v = EL && EL.querySelector('#skvVideo'), box = EL && EL.querySelector('#skvMarks');
    if (!v || !box || !(v.duration > 0) || !JOB) return;
    const ts = notesOf(JOB.perception).map(n => secs(n.t)).filter(x => x > 0 && x <= v.duration);
    box.innerHTML = ts.map(x => `<i style="left:${(x / v.duration * 100).toFixed(2)}%"></i>`).join('');
  }

  // ---------------------------------------------------------------- notes: the watcher's own text, split per moment
  function notesOf(text) {
    const out = [];
    for (const raw of String(text || '').split(/\n+/)) {
      const line = raw.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim();
      if (!line) continue;
      const m = line.match(/\[?\(?(\d{1,2}:\d{2}(?::\d{2})?)\)?\]?/);
      const body = m ? line.replace(m[0], '').replace(/^[\s:–-]+/, '').trim() : line;
      if (!body) continue;
      out.push({t: m ? m[1] : '', text: body.replace(/\*\*/g, '')});
    }
    return out;
  }
  function notesHTML(text, writing) {
    const ns = notesOf(text);
    if (!ns.length) return `<p class="skv-quiet">${writing ? 'Hoola is watching — notes appear here as it writes them.' : 'No notes yet.'}</p>`;
    return ns.map(n => `<div class="skv-note">${n.t ? `<button type="button" class="skv-ts" data-t="${esc(n.t)}">${esc(n.t)}</button>` : '<span></span>'}<span>${esc(n.text)}</span></div>`).join('')
      + (writing ? '<div class="skv-note skv-writing"><span></span><span>Writing…</span></div>' : '');
  }

  // ---------------------------------------------------------------- open + list
  async function openPage(el) {
    EL = el; stop();
    EL.innerHTML = '<div class="skv"><p class="skv-quiet">Loading…</p></div>';
    if (!(await refresh())) return;
    if (LIST.running) { JOB = {id: LIST.running, stage: 'fetch', stages: [], perception: '', done: false}; return showWatch(); }
    showHome();
  }
  async function refresh() {
    try { LIST = await api('GET', '/api/seekh/console/watches'); return true; }
    catch (e) { if (EL) EL.innerHTML = `<div class="skv"><h1 class="skv-h1">Video Learner</h1><p class="badc">${esc(e.message)}</p></div>`; return false; }
  }
  const crumbs = (...xs) => `<nav class="skv-crumb" aria-label="Breadcrumb"><button type="button" data-go="hub">AI Employees</button>`
    + xs.map(([label, to]) => ` <span aria-hidden="true">/</span> ${to ? `<button type="button" data-go="${to}">${esc(label)}</button>` : `<span>${esc(label)}</span>`}`).join('') + '</nav>';
  function status(row) {
    if (row.status === 'failed') return ['bad', 'Could not learn'];
    const w = +row.wins || 0, f = +row.fails || 0;
    if (w > 0) return ['ok', w === 1 ? 'Proven · worked once' : `Proven · worked ${w} times`];
    if (f > 0) return ['warn', 'Tried · did not work yet'];
    if (row.kind && row.kind !== 'website_work') return ['mute', 'Learned as notes'];
    return ['warn', 'Learned · not tried yet'];
  }

  // ---------------------------------------------------------------- screen 1: home
  function showHome() {
    VIEW = 'home'; stop();
    const off = LIST.enabled === false, rows = LIST.watches || [];
    const proven = rows.filter(r => +r.wins > 0), fresh = rows.filter(r => r.status !== 'failed' && !(+r.wins > 0));
    const shown = FILTER === 'proven' ? proven : FILTER === 'fresh' ? fresh : rows;
    EL.innerHTML = `<div class="skv">${crumbs(['Video Learner'])}
      <header class="skv-head"><div><h1 class="skv-h1">Video Learner</h1>
        <p class="skv-lede">Show Hoola a video of any task once. It watches, writes down every step, and can then do that task for you in its own browser.</p></div>
        <span class="skv-pill mute">${off ? 'Switched off on this server' : `${LIST.today} of ${LIST.max_per_day} videos learned today`}</span></header>
      ${off ? '<p class="skv-quiet">Learning from videos is switched off on this server.</p>' : `
      <section class="skv-teach" aria-labelledby="skvTeach" id="skvDrop">
        <h2 id="skvTeach">Teach Hoola a new task</h2>
        <div class="skv-teachrow">
          <label class="skv-link">${ICON.link}<span class="sr">Video link</span><input id="skvRef" type="text" autocomplete="off" spellcheck="false" placeholder="Paste a YouTube, Shorts or video link"></label>
          <label class="skv-name"><span class="sr">Name this task</span><input id="skvTitle" type="text" autocomplete="off" placeholder="Name it (optional) — e.g. Fill the NSP scholarship form"></label>
          <button type="button" class="btn go skv-big" id="skvWatch">Watch &amp; learn</button>
        </div>
        <div class="skv-teachfoot"><input type="file" id="skvFile" accept="video/*" hidden>
          <button type="button" class="btn soft" id="skvPick">${ICON.up}Upload a video file</button>
          <span class="skv-meta">or drop it here · up to 25 MB as a file, up to 3 hours as a link</span></div>
        <p class="skv-fine">Hoola never copies personal values from the video. Names, numbers and passwords you fill in yourself when it does the task.</p>
      </section>`}
      <section class="skv-list" aria-labelledby="skvLearned">
        <div class="skv-listhead"><h2 id="skvLearned" class="skv-h2">Your learned tasks</h2>
          <div class="skv-filters" role="group" aria-label="Filter">
            ${[['all', `All ${rows.length}`], ['proven', `Proven ${proven.length}`], ['fresh', `Not proven yet ${fresh.length}`]]
              .map(([k, n]) => `<button type="button" class="btn soft${FILTER === k ? ' on' : ''}" data-filter="${k}" aria-pressed="${FILTER === k}">${esc(n)}</button>`).join('')}
          </div></div>
        ${shown.length ? shown.map(rowHTML).join('') : `<p class="skv-quiet">${rows.length ? 'Nothing in this filter.' : 'Nothing learned yet. Paste a video link above to teach Hoola its first task.'}</p>`}
      </section></div>`;
    wire();
  }
  function rowHTML(r) {
    const [cls, word] = status(r), failed = r.status === 'failed', id = esc(r.id || r.procedure_id || '');
    const site = r.site ? `${esc(r.site)} · ` : '';
    const meta = failed ? esc(r.error || 'Hoola could not watch this video.')
      : `${site}${esc(r.steps || 0)} steps · learned ${esc(when(r.ts))}${r.last_run ? ' · last done ' + esc(when(r.last_run)) : ''}`;
    const title = esc(r.title || 'Untitled task');
    return `<div class="skv-row">
      ${failed ? thumb(r) : `<button type="button" class="skv-thumbbtn" data-task="${id}" aria-label="Open ${title}">${thumb(r)}</button>`}
      <div class="skv-rowbd">${failed ? `<b>${title}</b>` : `<button type="button" class="skv-title" data-task="${id}">${title}</button>`}
        <div class="skv-rowmeta"><span class="skv-pill ${cls}">${esc(word)}</span><span class="skv-meta">${meta}</span></div></div>
      <div class="skv-rowact">${failed
        ? `<button type="button" class="btn soft" data-retry="${id}">Try again</button><button type="button" class="btn soft" data-forget="${id}">Remove</button>`
        : `<button type="button" class="btn soft" data-task="${id}">Open</button>${r.kind === 'website_work' || !r.kind ? `<button type="button" class="btn go" data-doit="${id}">Do it now</button>` : ''}`}</div>
    </div>`;
  }

  // ---------------------------------------------------------------- screen 2: watching
  async function startWatch(ref, title) {
    if (!ref) return toast('Which video? Paste a link or upload a file.', true);
    const btn = EL.querySelector('#skvWatch'); if (btn) { btn.disabled = true; btn.textContent = 'Starting…'; }
    try {
      const r = await api('POST', '/api/seekh/console/watch', {video: ref, title});
      if (r.already_running) toast('A video is already being learned — showing that one.');
      JOB = {id: r.id, stage: 'queue', stages: [], perception: '', done: false, ref, title, kind: r.kind || ''};
      showWatch();
    } catch (e) {
      toast(e.message || 'Could not start', true);
      if (btn) { btn.disabled = false; btn.textContent = 'Watch & learn'; }
    }
  }
  async function showWatch() {
    VIEW = 'watch'; stop();
    const src = JOB.ref ? (() => { const s = String(JOB.ref); const yt = s.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/); return yt ? {kind: 'youtube', key: yt[1]} : /^https?:/i.test(s) ? {kind: 'url', key: s} : {kind: 'file', key: s}; })() : {kind: '', key: ''};
    EL.innerHTML = `<div class="skv">${crumbs(['Video Learner', 'home'], ['Watching'])}
      <header class="skv-head"><div><h1 class="skv-h1 sm" id="skvWTitle">${esc(JOB.title || 'Learning a new task')}</h1>
        <p class="skv-meta" id="skvWSrc">${esc(JOB.ref || '')}</p></div>
        <div class="skv-headact"><span class="skv-pill live" id="skvLive"><i></i>Learning</span><button type="button" class="btn soft" id="skvStop">Stop</button></div></header>
      <div class="skv-split">
        <div class="skv-main">
          <div class="skv-player" id="skvPlayer"><div class="skv-frame skv-noplay"><span>Loading the video…</span></div></div>
          <div class="skv-marks" id="skvMarks" aria-hidden="true"></div>
          <p class="skv-meta skv-hint">Click a time in the notes to jump the video there.</p>
          <section aria-labelledby="skvNotesH" class="skv-notes"><div class="skv-listhead"><h2 id="skvNotesH" class="skv-h3">Hoola's notes</h2><span class="skv-meta" id="skvNCount">written as Hoola watches</span></div>
            <div id="skvNotes" aria-live="polite">${notesHTML('', true)}</div></section>
        </div>
        <aside class="skv-side" aria-labelledby="skvHow"><h2 id="skvHow" class="skv-h3">How it's going</h2>
          <ol class="skv-stages" id="skvStages">${STAGES.map(([k, t, sub]) => `<li data-k="${k}"><span class="skv-dot"></span><span><b>${esc(t)}</b><small>${esc(sub)}</small></span><em></em></li>`).join('')}</ol>
          <p class="skv-fine">Usually takes about as long as the video. You can leave this page — Hoola keeps learning, and your task appears in the list when it's done.</p></aside>
      </div></div>`;
    wire();
    EL.querySelector('#skvPlayer').innerHTML = src.kind ? await playerHTML(src, 0) : '<div class="skv-frame skv-noplay"><span>The video is on its way</span></div>';
    EL.querySelector('#skvVideo')?.addEventListener('loadedmetadata', markers);
    paintWatch();
    POLL = setInterval(pollWatch, 1200); pollWatch();
    TICK = setInterval(() => { const l = EL && EL.querySelector('#skvLive'); if (l && JOB && !JOB.done) l.lastChild.textContent = `Learning · ${mmss((JOB.elapsed || 0) + (Date.now() - (JOB._at || Date.now())) / 1000)} so far`; }, 1000);
  }
  function paintWatch() {
    if (!EL || VIEW !== 'watch' || !JOB) return;
    const order = ['classify', 'fetch', 'notes', 'distill', 'memory'];
    const seen = new Map((JOB.stages || []).map(s => [s.k === 'distill_start' ? 'distill' : s.k, s.ts]));
    // which stage is live now: fetch = watching, the first streamed words = writing notes, notes done = distilling
    const cur = JOB.done ? 5 : seen.has('memory') ? 4 : seen.has('distill') || seen.has('notes') ? 3
      : JOB.perception ? 2 : seen.has('fetch') ? 1 : 0;
    const writing = !JOB.done && !seen.has('notes');
    EL.querySelectorAll('#skvStages li').forEach((li, i) => {
      li.className = (i < cur && !JOB.error) || (JOB.done && !JOB.error) ? 'did' : i === cur && !JOB.done ? 'on' : '';
      const k = order[i], em = li.querySelector('em');
      em.textContent = li.className === 'on' ? 'now' : seen.has(k) && li.className === 'did' ? mmss(seen.get(k)) : '';
    });
    const box = EL.querySelector('#skvNotes');
    if (box) {
      const atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
      box.innerHTML = notesHTML(JOB.perception, !JOB.done);
      if (atEnd) box.scrollTop = box.scrollHeight;
      const n = notesOf(JOB.perception).length, c = EL.querySelector('#skvNCount');
      if (c) c.textContent = n ? `written as Hoola watches · ${n} so far` : 'written as Hoola watches';
    }
    if (JOB.title) { const t = EL.querySelector('#skvWTitle'); if (t) t.textContent = JOB.title; }
    markers();
  }
  async function pollWatch() {
    if (!JOB || JOB.done) return;
    try {
      const r = await api('GET', `/api/seekh/console/progress?id=${encodeURIComponent(JOB.id || '')}`);
      JOB = {...JOB, ...r, ref: r.ref || JOB.ref, title: r.title || JOB.title, _at: Date.now()};
      if (!EL.querySelector('#skvVideo') && !EL.querySelector('#skvFrame') && JOB.ref) {  // adopted after a reload
        const s = String(JOB.ref), yt = s.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/);
        const p = EL.querySelector('#skvPlayer');
        if (p && (yt || r.kind === 'file')) p.innerHTML = await playerHTML(yt ? {kind: 'youtube', key: yt[1]} : {kind: 'file', key: s}, 0);
        const w = EL.querySelector('#skvWSrc'); if (w) w.textContent = JOB.ref;
      }
      paintWatch();
      if (r.done) {
        stop();
        await refresh();
        if (r.error) {
          if (r.stopped) { toast('Stopped. Nothing was kept.'); return showHome(); }
          const l = EL.querySelector('#skvLive'); if (l) { l.className = 'skv-pill bad'; l.textContent = 'Could not learn'; }
          const box = EL.querySelector('#skvNotes');
          if (box) box.insertAdjacentHTML('afterbegin', `<div class="skv-error"><b>Hoola could not learn this video.</b><span>${esc(r.error)}</span>
            <div class="skv-btnrow"><button type="button" class="btn go" id="skvAgain">Try again</button><button type="button" class="btn soft" data-go="home">Back to the list</button></div></div>`);
          EL.querySelector('#skvAgain')?.addEventListener('click', () => startWatch(JOB.ref, JOB.title));
          wire();
          return;
        }
        toast('Learned. It is in your learned tasks now.');
        const pid = r.result && r.result.procedure_id;
        if (pid) return openTask(pid); else showHome();
      }
    } catch (e) {
      if (e.status === 404) { stop(); toast('This watch was lost (the server restarted). Start it again.', true); await refresh(); showHome(); }
    }
  }
  async function stopWatch() {
    if (!JOB) return;
    const b = EL.querySelector('#skvStop'); if (b) { b.disabled = true; b.textContent = 'Stopping…'; }
    try { await api('POST', '/api/seekh/console/stop', {id: JOB.id}); } catch (e) { toast(e.message, true); if (b) { b.disabled = false; b.textContent = 'Stop'; } }
  }

  // ---------------------------------------------------------------- screen 3: one learned task
  async function openTask(id) {
    stop();
    try { TASK = await api('GET', `/api/seekh/console/task?id=${encodeURIComponent(id)}`); }
    catch (e) { toast(e.message, true); return showHome(); }
    showTask();
  }
  function fieldsOf(t) {                    // the form: one box per thing the task needs (from the learned hints)
    const seen = new Set(), out = [];
    for (const s of ((t.detail || {}).steps || [])) {
      const key = s.value_var || (s.value_hint ? s.value_hint.slice(0, 40) : '');
      if (!key || seen.has(key)) continue; seen.add(key);
      out.push({key, label: s.value_var ? human(s.value_var) : human(s.value_hint), hint: s.value_hint || ''});
    }
    return out.slice(0, 12);
  }
  async function showTask() {
    VIEW = 'task';
    const t = TASK, d = t.detail || {}, steps = d.steps || [], [cls, word] = status(t), web = !t.kind || t.kind === 'website_work';
    const box = (title, xs, warn) => xs && xs.length ? `<div class="skv-box${warn ? ' warn' : ''}"><h3>${title}</h3><ul>${xs.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
    const fields = fieldsOf(t);
    EL.innerHTML = `<div class="skv">${crumbs(['Video Learner', 'home'], [t.title || 'Learned task'])}
      <header class="skv-head"><div><h1 class="skv-h1">${esc(t.title || 'Learned task')}</h1>
        <div class="skv-rowmeta"><span class="skv-pill ${cls}">${esc(word)}</span>${t.site ? `<span class="skv-pill mute">Website task · ${esc(t.site)}</span>` : web ? '' : '<span class="skv-pill mute">Not a website task</span>'}
        <span class="skv-meta">${esc(t.steps || steps.length)} steps · learned ${esc(when(t.ts))}</span></div></div>
        <div class="skv-headact"><button type="button" class="btn soft" id="skvRelearn">Re-learn</button><button type="button" class="btn soft" data-forget="${esc(t.id || t.procedure_id)}">Remove</button></div></header>
      <div class="skv-split">
        <div class="skv-main">
          <details class="skv-vid" id="skvVid"><summary>Watch the video</summary><div class="skv-player" id="skvPlayer"></div></details>
          <section aria-labelledby="skvStepsH"><div class="skv-listhead"><h2 id="skvStepsH" class="skv-h3">The steps Hoola learned</h2><span class="skv-meta">each with the moment it was seen</span></div>
            <ol class="skv-steps">${steps.map((s, i) => `<li><span class="skv-n">${esc(s.n || i + 1)}</span>
              <span>${esc(s.note || human(s.action))}${s.value_hint ? `<small>You fill: ${esc(s.value_hint)}</small>` : ''}</span>
              <span class="skv-evs">${(s.evidence || []).slice(0, 2).map(e => `<button type="button" class="skv-ts" data-t="${esc(e)}">${esc(e)}</button>`).join('')}</span></li>`).join('') || '<li><span></span><span class="skv-quiet">No steps were kept for this task.</span><span></span></li>'}</ol></section>
          <div class="skv-boxes">${box('Before you start', d.preconditions)}${box('Watch out', d.gotchas, true)}${box('Not seen in the video', d.unsure)}</div>
        </div>
        <aside class="skv-side skv-doit" aria-labelledby="skvDoH">
          <h2 id="skvDoH" class="skv-h3">${web ? 'Let Hoola do it' : 'Ask Hoola to guide you'}</h2>
          <p class="skv-fine">${web ? 'Fill what the video can\'t know. Hoola uses its own browser and asks you before submitting anything.' : 'This was not a website task, so Hoola walks you through the steps in chat.'}</p>
          <form id="skvForm" class="skv-form">
            ${fields.map((f, i) => `<label>${esc(f.label)}<input name="f${i}" data-label="${esc(f.label)}" placeholder="${esc(f.hint)}" autocomplete="off"></label>`).join('')}
            <label><span>Anything else for Hoola <span class="skv-opt">(optional)</span></span><input name="extra" placeholder="e.g. use the photo I sent yesterday" autocomplete="off"></label>
            <button type="submit" class="btn go skv-big">${web ? 'Do it now' : 'Guide me now'}</button>
          </form>
          <div class="skv-conf"><span>How sure Hoola is</span><span><i><b style="width:${pct(t.confidence)}%"></b></i>${pct(t.confidence)}%</span></div>
        </aside>
      </div></div>`;
    wire();
    EL.querySelector('#skvRelearn')?.addEventListener('click', () => { if (confirm('Watch this video again and replace what was learned?')) startWatch(refOf(t), t.title || ''); });
    EL.querySelector('#skvForm')?.addEventListener('submit', e => { e.preventDefault(); doIt(); });
    const det = EL.querySelector('#skvVid');
    det?.addEventListener('toggle', async () => { const p = EL.querySelector('#skvPlayer'); if (det.open && p && !p.innerHTML) p.innerHTML = await playerHTML(srcOf(t), 0); });
  }

  // ---------------------------------------------------------------- screen 4: Hoola doing it
  async function doIt() {
    const t = TASK; if (!t) return;
    const form = EL.querySelector('#skvForm'), vals = [];
    form.querySelectorAll('input[data-label]').forEach(i => { if (i.value.trim()) vals.push(`${i.dataset.label}: ${i.value.trim()}`); });
    const extra = String(form.querySelector('[name=extra]')?.value || '').trim();
    const web = !t.kind || t.kind === 'website_work';
    const msg = `Do the learned task "${t.title}" now, for real.`
      + (vals.length ? ` The values to use: ${vals.join('; ')}.` : '')
      + (extra ? ` ${extra}` : '')
      + (web ? ' Use your own browser and the recipe learned from the video as a guide, checking every step against the live page. Ask me before sending or submitting anything, and ask me for any value the video did not show.'
             : ' Walk me through the steps one by one; check each one with me before moving on.');
    const b = form.querySelector('button[type=submit]'); b.disabled = true; b.textContent = 'Starting…';
    try {
      const r = await send(msg);
      const cid = (r && (r.conversation_id || r.conv)) || '';
      RUN = {cid, after: (r && r.after) || 0, task: t, steps: new Map(), cards: [], reply: '', done: false, t0: Date.now()};
      showRun();
    } catch (e) { toast('Could not start: ' + (e.message || ''), true); b.disabled = false; b.textContent = web ? 'Do it now' : 'Guide me now'; }
  }
  function showRun() {
    VIEW = 'run'; stop();
    const t = RUN.task, planned = ((t.detail || {}).steps || []);
    EL.innerHTML = `<div class="skv">${crumbs(['Video Learner', 'home'], [t.title || 'Task', 'task'], ['Doing it'])}
      <header class="skv-head"><div><h1 class="skv-h1 sm">Hoola is doing: ${esc(t.title || 'your task')}</h1>
        <p class="skv-meta" id="skvRunMeta">Starting…</p></div>
        <div class="skv-headact"><button type="button" class="btn soft" id="skvRunStop">Stop</button><button type="button" class="btn soft" id="skvRunChat">Open in chat</button></div></header>
      <div class="skv-split">
        <div class="skv-main">
          <div id="skvWait"></div>
          <section aria-labelledby="skvActH"><h2 id="skvActH" class="skv-h3">What Hoola is doing</h2><ol class="skv-acts" id="skvActs" aria-live="polite"><li class="skv-quiet">Waiting for the first step…</li></ol></section>
          <div id="skvReply"></div>
          <div id="skvVerdict"></div>
        </div>
        <aside class="skv-side"><h2 class="skv-h3">The learned steps</h2>
          <ol class="skv-plan">${planned.map((s, i) => `<li><span class="skv-n">${esc(s.n || i + 1)}</span><span>${esc(s.note || human(s.action))}</span></li>`).join('')}</ol>
          <p class="skv-fine">The page may look different from the video — Hoola checks every step against the live page.</p></aside>
      </div></div>`;
    wire();
    EL.querySelector('#skvRunChat')?.addEventListener('click', () => go('chat'));
    EL.querySelector('#skvRunStop')?.addEventListener('click', async () => {
      if (!RUN.cid) return;
      try { await api('POST', `/api/conversations/${encodeURIComponent(RUN.cid)}/stop`, {}); toast('Stopped.'); } catch (e) { toast(e.message, true); }
    });
    POLL = setInterval(pollRun, 2000); pollRun();
    TICK = setInterval(() => { const m = EL && EL.querySelector('#skvRunMeta'); if (m && RUN && !RUN.done) m.textContent = `${RUN.steps.size} steps so far · ${mmss((Date.now() - RUN.t0) / 1000)} · in Hoola's own browser`; }, 1000);
  }
  async function pollRun() {
    if (!RUN || !RUN.cid || RUN.done) return;
    let tl;
    try { tl = await api('GET', `/api/conversations/${encodeURIComponent(RUN.cid)}/timeline?steps=1&own=1&limit=120`); } catch { return; }
    const evs = (tl.events || []).filter(e => e.id > RUN.after);
    if (!RUN.started) {                     // our own message is the start line: everything after it is this run
      const mine = [...evs].reverse().find(e => e.kind === 'message' && e.payload && e.payload.role === 'user' && String(e.payload.text || '').includes(RUN.task.title || '\u0000'));
      if (!mine) return;
      RUN.after = mine.id; RUN.started = true;
    }
    const after = evs.filter(e => e.id > RUN.after);
    let running = false, reply = '';
    const cards = [];
    for (const e of after) {
      const p = e.payload || {};
      if (e.kind === 'step') { RUN.steps.set(p.id || e.id, {label: p.label || p.tool || 'Working', state: p.state || 'running', at: e.at}); if (p.state === 'running') running = true; }
      else if (e.kind === 'message' && p.role === 'assistant' && p.source !== 'greeting') reply = String(p.text || '');
      else if (needsHer(p)) cards.push({id: e.id, title: p.title || p.question || p.label || human(e.kind)});
    }
    const acts = EL.querySelector('#skvActs');
    if (acts && RUN.steps.size) acts.innerHTML = [...RUN.steps.values()].map(s => `<li class="${s.state === 'running' ? 'on' : s.state === 'failed' || s.state === 'error' ? 'bad' : 'did'}"><span class="skv-dot">${s.state === 'running' ? '' : s.state === 'failed' || s.state === 'error' ? '!' : ICON.tick}</span><span>${esc(s.label)}</span><em>${esc(new Date(s.at).toLocaleTimeString('en-IN', {hour: 'numeric', minute: '2-digit'}))}</em></li>`).join('');
    const wait = EL.querySelector('#skvWait');
    if (wait) wait.innerHTML = cards.length ? `<section class="skv-waiting" aria-label="Waiting for you"><small>Waiting for you</small><b>${esc(cards[cards.length - 1].title)}</b>
      <span class="skv-fine">Answer it in the chat — Hoola carries on the moment you do.</span><div class="skv-btnrow"><button type="button" class="btn go" id="skvAnswer">Answer</button></div></section>` : '';
    EL.querySelector('#skvAnswer')?.addEventListener('click', () => go('chat'));
    if (reply) { const rb = EL.querySelector('#skvReply'); if (rb) rb.innerHTML = `<div class="skv-replybox"><small>Hoola says</small><p>${esc(reply.slice(0, 900))}</p></div>`; }
    if (reply && !running && !cards.length) {
      RUN.done = true; stop();
      const m = EL.querySelector('#skvRunMeta'); if (m) m.textContent = `Finished in ${mmss((Date.now() - RUN.t0) / 1000)}`;
      const v = EL.querySelector('#skvVerdict');
      if (v) v.innerHTML = `<section class="skv-verdict"><div><b>Did it work?</b><span>Saying yes marks this task Proven, so next time Hoola goes faster and asks less.</span></div>
        <div class="skv-btnrow"><button type="button" class="btn go skv-yes" data-verdict="1">Yes, it worked</button><button type="button" class="btn soft" data-verdict="0">Something was wrong</button></div></section>`;
      v?.querySelectorAll('[data-verdict]').forEach(b => b.addEventListener('click', () => verdict(b.dataset.verdict === '1')));
    }
  }
  const needsHer = p => { const st = String(p.status || p.state || '').toLowerCase(); return ['pending', 'waiting', 'ask', 'needs_you', 'open'].includes(st) && !p.decided && !p.answered; };
  async function verdict(ok) {
    try {
      await api('POST', '/api/seekh/console/proven', {id: RUN.task.id || RUN.task.procedure_id, ok});
      toast(ok ? 'Marked Proven.' : 'Noted. You can re-learn it or tell Hoola what went wrong in chat.');
      await refresh(); openTask(RUN.task.id || RUN.task.procedure_id);
    } catch (e) { toast(e.message, true); }
  }

  // ---------------------------------------------------------------- wiring shared by every screen
  async function forget(id) {
    if (!confirm('Remove this task? Hoola forgets these steps.')) return;
    try { await api('DELETE', `/api/seekh/console/task?id=${encodeURIComponent(id)}`); toast('Removed.'); await refresh(); showHome(); }
    catch (e) { toast(e.message, true); }
  }
  function wire() {
    const q = s => EL.querySelector(s);
    EL.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', async () => {
      const to = b.dataset.go;
      if (to === 'hub') { stop(); return go('hire'); }
      if (to === 'task' && TASK) return openTask(TASK.id || TASK.procedure_id);
      await refresh(); showHome();
    }));
    q('#skvWatch')?.addEventListener('click', () => startWatch(String(q('#skvRef')?.value || '').trim(), String(q('#skvTitle')?.value || '').trim()));
    q('#skvRef')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q('#skvWatch')?.click(); } });
    q('#skvPick')?.addEventListener('click', () => q('#skvFile')?.click());
    q('#skvFile')?.addEventListener('change', e => { const f = e.target.files && e.target.files[0]; e.target.value = ''; if (f) take(f); });
    const drop = q('#skvDrop');
    if (drop) {
      drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
      drop.addEventListener('dragleave', () => drop.classList.remove('over'));
      drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); const f = e.dataTransfer?.files?.[0]; if (f) take(f); });
    }
    q('#skvStop')?.addEventListener('click', stopWatch);
    EL.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => { FILTER = b.dataset.filter; showHome(); }));
    EL.querySelectorAll('[data-task]').forEach(b => b.addEventListener('click', () => openTask(b.dataset.task)));
    EL.querySelectorAll('[data-doit]').forEach(b => b.addEventListener('click', async () => { await openTask(b.dataset.doit); EL.querySelector('#skvForm input')?.focus(); }));
    EL.querySelectorAll('[data-forget]').forEach(b => b.addEventListener('click', () => forget(b.dataset.forget)));
    EL.querySelectorAll('[data-retry]').forEach(b => b.addEventListener('click', () => {
      const row = (LIST.watches || []).find(r => (r.id || r.procedure_id) === b.dataset.retry);
      if (row) startWatch(refOf(row), row.title || '');
    }));
    EL.querySelectorAll('.skv-ts').forEach(b => b.addEventListener('click', async () => {
      const det = EL.querySelector('#skvVid');
      if (det && !det.open) { det.open = true; const p = EL.querySelector('#skvPlayer'); if (p && !p.innerHTML) p.innerHTML = await playerHTML(srcOf(TASK), secs(b.dataset.t)); return; }
      if (!seek(b.dataset.t)) toast('This video can only be played at its own link.');
    }));
  }
  async function take(f) {
    if (f.size > 25 * 1024 * 1024) return toast(`${f.name} is over 25 MB — paste the video's link instead.`, true);
    if (!/^video\//.test(f.type || '')) return toast(`${f.name} is not a video file.`, true);
    const b = EL.querySelector('#skvPick'); if (b) { b.disabled = true; b.textContent = 'Uploading…'; }
    try {
      const r = await upload(f);
      const title = String(EL.querySelector('#skvTitle')?.value || '').trim() || f.name.replace(/\.[^.]+$/, '');
      await startWatch(r.file_id || '', title);
    } catch (e) { toast(`${f.name}: ${e.message || 'upload failed'}`, true); if (b) { b.disabled = false; b.innerHTML = ICON.up + 'Upload a video file'; } }
  }
  // the console re-opens the page by calling open(el); stop polling when the page is left
  document.addEventListener('visibilitychange', () => { if (document.hidden) return; if (VIEW === 'run' && RUN && !RUN.done && !POLL) POLL = setInterval(pollRun, 2000); });
  return {open: openPage, leave: stop};
};
