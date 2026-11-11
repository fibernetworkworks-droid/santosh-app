/* v0.785 VIDEO LEARNER, PREMIUM (owner: "FIX ALL 7 PROPERLY ... MAKE ENTIRE SECTION PROPER AND PREMIUM WITH PERFECT
   ALIGNMENT OF TEXT, BUTTON, TEXTURE ... WITH SOME VISUAL GRAPHICAL ANIMATION IN IT"). Four screens on one page:
     home   - a hero with a drawn, moving picture of what the page does, her numbers, teach a task (link / upload)
              and her learned tasks as cards (Proven / Learned, not tried / Notes / Could not learn / being done now)
     watch  - the video in a lit frame, Hoola's notes arriving AS GEMINI WRITES THEM (streamed, never paced fakes),
              every [m:ss] jumps the video, the five real stages on a filling timeline with HOW LONG each took, Stop
     task   - the learned steps as a timeline with their video moments, Before you start / Watch out / Not seen,
              a form built from what the task needs (a file step gets a file picker), a confidence ring, Do it now
     run    - Hoola doing it: the chat turn's own live steps on this page, a card that needs her = "Answer",
              then "Did it work?" -> Proven
   The seven fixes of v0.785 live here and in seekh.py / seekh_console.py:
     1 the Learning pill no longer wears the chat panel's `.live` class      5 a stage shows how long it took
     2 Re-learn / Try again send `replace`, the old row leaves the list       6 an uploaded video is kept by the learner
     3 the run is kept on the server: leaving the page loses nothing, and     7 a watch the restart cut is picked up
       a task really done by the operator becomes Proven by itself              again (the page says so)
     4 a step that uploads a file gets a file picker; the files ride the chat turn
   Rules kept from v0.718 / v0.745: every stage is a real boundary of seekh.watch; learned is NOT proven until a
   real run worked; nothing is performed by this page itself - Do it now is one chat turn through the composer's
   door, so sending / submitting still asks for her tap; every server value goes through esc().
   Motion (CRISP TEXT): only drawings, dots, bars and rings move - never a layer that holds text; entrances play
   once and leave no transform behind; "Reduce motion" and calm switch all of it off for #app. */
'use strict';
window.HoolaSeekh = function ({api, esc, toast, send, upload, open: go, chat, live}) {
  let EL = null, VIEW = 'home', FILTER = 'all';
  let LIST = null;          // GET /api/seekh/console/watches
  let JOB = null;           // the watch job being shown
  let TASK = null;          // the task page's row
  let RUN = null;           // {cid, after, task, steps:Map, reply, done, t0, waiting:[]}
  let POLL = null, TICK = null, COUNTED = false, SHOWN = 0;
  const MEDIA = new Map();  // row id / file id -> blob url
  const STAGES = [['classify', 'Opened the video', 'checked the link'],
                  ['fetch', 'Watching', 'frame by frame, with the sound'],
                  ['notes', 'Writing notes', 'every step with its moment'],
                  ['distill', 'Turning notes into steps', 'a recipe Hoola can follow'],
                  ['memory', 'Saving to memory', 'added to your learned tasks']];
  const mmss = s => { s = Math.max(0, Math.round(+s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const took = s => { s = Math.max(0, +s || 0); return s < 1 ? 'under 1s' : s < 60 ? `${Math.round(s)}s` : `${Math.floor(s / 60)}m ${String(Math.round(s % 60)).padStart(2, '0')}s`; };
  const secs = t => { const p = String(t || '').split(':').map(Number); return p.some(isNaN) ? 0 : p.reduce((a, b) => a * 60 + b, 0); };
  const when = iso => { const d = new Date(iso || ''); return isNaN(d) ? '' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit'}); };
  const pct = c => Math.round(Math.min(1, Math.max(0, +c || 0)) * 100);
  const human = v => String(v || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
  const rid = r => String((r && (r.id || r.procedure_id)) || '');
  const calm = () => document.documentElement.classList.contains('calm') || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const stop = () => { if (POLL) clearInterval(POLL); if (TICK) clearInterval(TICK); POLL = TICK = null; };
  const svg = (d, extra = '') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"${extra}>${d}</svg>`;
  const ICON = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" fill="currentColor"/></svg>',
    tick: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    link: svg('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'),
    up: svg('<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>'),
    warn: svg('<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.5v.5"/>'),
    eye: svg('<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
    clock: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    shield: svg('<path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>'),
    list: svg('<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>'),
    spark: svg('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>'),
    file: svg('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'),
    again: svg('<path d="M4 12a8 8 0 0 1 13.7-5.7L20 8.5M20 4v4.5h-4.5M20 12a8 8 0 0 1-13.7 5.7L4 15.5M4 20v-4.5h4.5"/>'),
    bin: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V4h6v3"/>'),
    chat: svg('<path d="M21 12a8 8 0 0 1-11.8 7L4 20l1.1-4.6A8 8 0 1 1 21 12z"/>'),
    arrow: svg('<path d="M5 12h14M13 6l6 6-6 6"/>'),
    // one small picture per kind of step
    open: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.8 3 2.8 15 0 18M12 3c-2.8 3-2.8 15 0 18"/>'),
    click: svg('<path d="M9 3v3M3.5 5.5l2 2M3 11h3M14.5 5.5l-2 2"/><path d="M10 10l9 4-4 1.5L13.5 20z"/>'),
    fill: svg('<rect x="3" y="7" width="18" height="10" rx="2.5"/><path d="M8 10.5v3M11.5 12h5"/>'),
    select: svg('<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M8 11l4 4 4-4"/>'),
    check: svg('<rect x="4" y="4" width="16" height="16" rx="3.5"/><path d="M8 12.5l3 3 5-6"/>'),
    upload: svg('<path d="M12 16V5M7.5 9.5L12 5l4.5 4.5M5 19h14"/>'),
    wait: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    other: svg('<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>'),
  };
  const stepIcon = a => ICON[{type: 'fill', open: 'open', click: 'click', fill: 'fill', select: 'select', check: 'check', upload: 'upload', wait: 'wait'}[String(a || '').toLowerCase()] || 'other'];

  // ---------------------------------------------------------------- the drawings (no text inside: they may move)
  // The hero picture: a video is scanned, three moments light up, they become three steps, a pointer does them.
  const ART_LEARN = `<svg class="skv-art" viewBox="0 0 400 290" aria-hidden="true" focusable="false">
    <defs><linearGradient id="skvG1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" class="skv-g-a"/><stop offset="1" class="skv-g-b"/></linearGradient>
      <linearGradient id="skvG2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <clipPath id="skvClip"><rect x="26" y="26" width="222" height="132" rx="14"/></clipPath></defs>
    <rect class="skv-a-shadow" x="34" y="36" width="222" height="132" rx="14"/>
    <rect x="26" y="26" width="222" height="132" rx="14" fill="url(#skvG1)"/>
    <g clip-path="url(#skvClip)"><rect class="skv-a-scan" x="-70" y="26" width="70" height="132" fill="url(#skvG2)"/></g>
    <circle class="skv-a-play" cx="137" cy="86" r="21"/><path d="M130 76v20l17-10z" fill="#fff"/>
    <rect class="skv-a-track" x="42" y="138" width="190" height="5" rx="2.5"/>
    <rect class="skv-a-prog" x="42" y="138" width="190" height="5" rx="2.5"/>
    <g class="skv-a-marks"><rect x="78" y="134" width="5" height="13" rx="2.5"/><rect x="128" y="134" width="5" height="13" rx="2.5"/><rect x="186" y="134" width="5" height="13" rx="2.5"/></g>
    <path class="skv-a-flow" d="M150 162c0 34 36 30 60 30h18" />
    <rect class="skv-a-card-sh" x="216" y="126" width="164" height="142" rx="16"/>
    <rect class="skv-a-card" x="208" y="118" width="164" height="142" rx="16"/>
    <g class="skv-a-rows">
      <g><rect class="skv-a-chip" x="224" y="138" width="34" height="18" rx="6"/><rect class="skv-a-line" x="268" y="143" width="72" height="8" rx="4"/><circle class="skv-a-ok" cx="352" cy="147" r="9"/><path class="skv-a-tk" d="M347.5 147l3.2 3.2 5.6-6.4"/></g>
      <g><rect class="skv-a-chip" x="224" y="180" width="34" height="18" rx="6"/><rect class="skv-a-line" x="268" y="185" width="58" height="8" rx="4"/><circle class="skv-a-ok" cx="352" cy="189" r="9"/><path class="skv-a-tk" d="M347.5 189l3.2 3.2 5.6-6.4"/></g>
      <g><rect class="skv-a-chip" x="224" y="222" width="34" height="18" rx="6"/><rect class="skv-a-line" x="268" y="227" width="66" height="8" rx="4"/><circle class="skv-a-ok" cx="352" cy="231" r="9"/><path class="skv-a-tk" d="M347.5 231l3.2 3.2 5.6-6.4"/></g>
    </g>
    <g class="skv-a-cursor"><path d="M0 0l15 6.5-6.2 2.3L6.5 15z"/></g>
  </svg>`;
  // The run picture: a browser window whose fields fill one after another.
  const ART_BROWSER = `<svg class="skv-bart" viewBox="0 0 360 150" aria-hidden="true" focusable="false">
    <rect class="skv-b-win" x="1" y="1" width="358" height="148" rx="14"/>
    <path class="skv-b-bar" d="M1 15a14 14 0 0 1 14-14h330a14 14 0 0 1 14 14v19H1z"/>
    <circle class="skv-b-dot" cx="20" cy="18" r="4"/><circle class="skv-b-dot" cx="34" cy="18" r="4"/><circle class="skv-b-dot" cx="48" cy="18" r="4"/>
    <rect class="skv-b-url" x="70" y="10" width="214" height="16" rx="8"/>
    <g class="skv-b-f"><rect class="skv-b-box" x="24" y="52" width="196" height="20" rx="6"/><rect class="skv-b-ink f1" x="32" y="59" width="120" height="6" rx="3"/></g>
    <g class="skv-b-f"><rect class="skv-b-box" x="24" y="82" width="196" height="20" rx="6"/><rect class="skv-b-ink f2" x="32" y="89" width="150" height="6" rx="3"/></g>
    <g class="skv-b-f"><rect class="skv-b-box" x="24" y="112" width="110" height="20" rx="6"/><rect class="skv-b-ink f3" x="32" y="119" width="70" height="6" rx="3"/></g>
    <rect class="skv-b-btn" x="252" y="108" width="84" height="26" rx="13"/>
    <rect class="skv-b-side" x="244" y="52" width="92" height="42" rx="8"/>
    <g class="skv-b-cur"><path d="M0 0l13 5.6-5.4 2L5.6 13z"/></g>
  </svg>`;
  const BARS = '<span class="skv-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span>';
  const DOTS = '<span class="skv-dots" aria-hidden="true"><i></i><i></i><i></i></span>';
  const ring = (p, big) => { const r = big ? 36 : 19, c = 2 * Math.PI * r, s = big ? 84 : 44, w = big ? 7 : 4;
    return `<span class="skv-ring${big ? ' big' : ''}" role="img" aria-label="${p}% sure"><svg viewBox="0 0 ${s} ${s}" aria-hidden="true"><circle class="t" cx="${s / 2}" cy="${s / 2}" r="${r}" stroke-width="${w}"/><circle class="v" cx="${s / 2}" cy="${s / 2}" r="${r}" stroke-width="${w}" stroke-dasharray="${c.toFixed(1)}" stroke-dashoffset="${c.toFixed(1)}" data-off="${(c * (1 - p / 100)).toFixed(1)}"/></svg><b>${p}%</b></span>`; };
  function settle(root) {                    // rings draw themselves and numbers count up - once, after the paint
    const still = calm();
    requestAnimationFrame(() => requestAnimationFrame(() => root.querySelectorAll('.skv-ring .v').forEach(v => { v.style.strokeDashoffset = v.dataset.off; })));
    const nums = [...root.querySelectorAll('[data-count]')];
    if (still || COUNTED) { nums.forEach(n => { n.textContent = n.dataset.count; }); return; }
    COUNTED = true;
    const t0 = performance.now(), dur = 900;
    (function frame(t) {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      nums.forEach(n => { n.textContent = Math.round(+n.dataset.count * e); });
      if (k < 1) requestAnimationFrame(frame);
    })(t0);
  }
  function mount(html, view) {               // one place draws a screen: the entrance plays only when the screen changes
    const fresh = VIEW !== view || !SHOWN;
    VIEW = view; SHOWN++;
    EL.innerHTML = `<div class="skv skv-v-${view}${fresh ? ' skv-in' : ''}">${html}</div>`;
    wire(); settle(EL);
  }

  // ---------------------------------------------------------------- sources and video
  function srcOf(row) {                    // "youtube:ID" | "file:FID" | "url:..." -> {kind, key}
    const s = String((row && (row.source || '')) || ''), i = s.indexOf(':');
    return i < 0 ? {kind: '', key: s} : {kind: s.slice(0, i), key: s.slice(i + 1)};
  }
  function refOf(row) {                    // what to send back to /watch for Try again / Re-learn
    if (row && row.media) return `kept:${rid(row)}`;     // v0.785 the learner's own copy outlives the chat's 24 hours
    if (row && row.ref) return row.ref;
    const {kind, key} = srcOf(row);
    return kind === 'youtube' ? `https://youtu.be/${key}` : key;
  }
  function sourceWord(row) {
    const {kind, key} = srcOf(row);
    if (kind === 'youtube') return 'YouTube';
    if (kind === 'url') { try { return new URL(key).hostname.replace(/^www\./, ''); } catch { return 'Video link'; } }
    return row && row.media && row.media.name ? row.media.name : 'Uploaded video';
  }
  function thumb(row) {
    const {kind, key} = srcOf(row);
    if (row.status === 'failed') return `<span class="skv-thumb fail" aria-hidden="true">${ICON.warn}</span>`;
    const img = kind === 'youtube' && /^[\w-]{11}$/.test(key) ? `<img src="https://i.ytimg.com/vi/${esc(key)}/mqdefault.jpg" alt="" loading="lazy">` : '';
    return `<span class="skv-thumb${img ? '' : ' plain'}" aria-hidden="true">${img}<i>${ICON.play}</i><em>${esc(row.steps || 0)} steps</em></span>`;
  }
  async function blobOf(key, path) {
    if (!MEDIA.has(key)) {
      const r = await api('GET', path, undefined, {raw: true});
      MEDIA.set(key, URL.createObjectURL(await r.blob()));
    }
    return MEDIA.get(key);
  }
  async function playerHTML(src, start, row) {   // youtube embed / the learner's kept copy / her fresh upload / a link
    if (src.kind === 'youtube' && /^[\w-]{11}$/.test(src.key)) {
      return `<iframe class="skv-frame" id="skvFrame" title="The video" src="https://www.youtube-nocookie.com/embed/${esc(src.key)}?rel=0&start=${Math.floor(start || 0)}" allow="encrypted-media; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
    }
    const video = url => `<video class="skv-frame" id="skvVideo" controls preload="metadata" src="${url}"></video>`;
    if (row && row.media) {
      try { return video(await blobOf('m:' + rid(row), `/api/seekh/console/media?id=${encodeURIComponent(rid(row))}`)); } catch { /* the copy is gone: say so below */ }
    }
    if (src.kind === 'file' && src.key && src.key !== 'kept') {
      try { return video(await blobOf('f:' + src.key, `/api/panel/files/${encodeURIComponent(src.key)}`)); } catch { /* swept: the plain box */ }
    }
    if (src.kind === 'url') return `<div class="skv-frame skv-noplay">${ICON.play}<span>This video plays at its own link</span><a href="${esc(src.key)}" target="_blank" rel="noopener noreferrer">Open the video</a></div>`;
    return `<div class="skv-frame skv-noplay">${ICON.play}<span>This video is not kept any more. The learned steps are.</span></div>`;
  }
  function seek(t) {                       // a [m:ss] chip: jump the video there
    const s = secs(t), v = EL && EL.querySelector('#skvVideo'), f = EL && EL.querySelector('#skvFrame');
    if (v) { v.currentTime = s; v.play?.().catch(() => {}); return true; }
    if (f) { f.src = f.src.replace(/([?&])start=\d+/, `$1start=${s}`) + (f.src.includes('autoplay=1') ? '' : '&autoplay=1'); return true; }
    return false;
  }
  function markers() {                     // violet ticks on the bar where notes landed (only when the length is known)
    const v = EL && EL.querySelector('#skvVideo'), box = EL && EL.querySelector('#skvMarks');
    if (!v || !box || !(v.duration > 0) || !JOB) return;
    const ts = notesOf(JOB.perception).map(n => secs(n.t)).filter(x => x > 0 && x <= v.duration);
    box.innerHTML = ts.map(x => `<i style="left:${(x / v.duration * 100).toFixed(2)}%"></i>`).join('');
    box.classList.toggle('on', ts.length > 0);
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
  const noteHTML = n => `${n.t ? `<button type="button" class="skv-ts" data-t="${esc(n.t)}">${esc(n.t)}</button>` : '<span></span>'}<span>${esc(n.text)}</span>`;
  function paintNotes(text, writing) {       // only what changed is touched: a note already on screen never re-plays
    const box = EL && EL.querySelector('#skvNotes'); if (!box) return 0;
    const ns = notesOf(text), atEnd = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
    box.querySelector('.skv-quiet')?.remove();
    let rows = [...box.querySelectorAll('.skv-note:not(.skv-writing)')];
    while (rows.length > ns.length) rows.pop().remove();
    let tail = box.querySelector('.skv-writing');
    ns.forEach((n, i) => {
      const html = noteHTML(n);
      if (rows[i]) { if (rows[i].dataset.h !== html) { rows[i].innerHTML = html; rows[i].dataset.h = html; wireTs(rows[i]); } return; }
      const d = document.createElement('div'); d.className = 'skv-note new'; d.dataset.h = html; d.innerHTML = html;
      box.insertBefore(d, tail || null); wireTs(d);
    });
    if (writing && !tail) { tail = document.createElement('div'); tail.className = 'skv-note skv-writing'; tail.innerHTML = `<span></span><span>${DOTS}<span class="sr">Writing</span></span>`; box.appendChild(tail); }
    if (!writing && tail) tail.remove();
    if (!ns.length && !writing) box.insertAdjacentHTML('afterbegin', '<p class="skv-quiet">No notes yet.</p>');
    if (!ns.length && writing && !box.querySelector('.skv-wait')) box.insertAdjacentHTML('afterbegin', '<p class="skv-quiet skv-wait">Hoola is watching. Notes appear here as it writes them.</p>');
    if (ns.length) box.querySelector('.skv-wait')?.remove();
    if (atEnd) box.scrollTop = box.scrollHeight;
    return ns.length;
  }

  // ---------------------------------------------------------------- open + list
  async function openPage(el) {
    EL = el; stop(); SHOWN = 0;
    EL.innerHTML = '<div class="skv"><div class="skv-skel" aria-hidden="true"><i></i><i></i><i></i></div><p class="sr">Loading</p></div>';
    if (!(await refresh())) return;
    if (LIST.running) { JOB = {id: LIST.running, stage: 'fetch', stages: [], perception: '', done: false}; return showWatch(); }
    if (RUN && !RUN.done && RUN.task) return showRun();          // she left mid-run and came back
    showHome();
  }
  async function refresh() {
    try { LIST = await api('GET', '/api/seekh/console/watches'); return true; }
    catch (e) { if (EL) EL.innerHTML = `<div class="skv"><h1 class="skv-h1">Video Learner</h1><p class="badc">${esc(e.message)}</p></div>`; return false; }
  }
  const crumbs = (...xs) => `<nav class="skv-crumb" aria-label="Breadcrumb"><button type="button" data-go="hub">AI Employees</button>`
    + xs.map(([label, to]) => ` <span aria-hidden="true">/</span> ${to ? `<button type="button" data-go="${to}">${esc(label)}</button>` : `<span aria-current="page">${esc(label)}</span>`}`).join('') + '</nav>';
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
    stop();
    const off = LIST.enabled === false, rows = LIST.watches || [];
    const learned = rows.filter(r => r.status !== 'failed');
    const proven = rows.filter(r => +r.wins > 0), fresh = learned.filter(r => !(+r.wins > 0));
    const shown = FILTER === 'proven' ? proven : FILTER === 'fresh' ? fresh : rows;
    const c = LIST.counts || {learned: learned.length, proven: proven.length, steps: learned.reduce((a, r) => a + (+r.steps || 0), 0)};
    const left = Math.max(0, (+LIST.max_per_day || 0) - (+LIST.today || 0));
    const doing = rows.filter(r => r.run && r.run.cid);
    const stat = (n, label, cls, d) => `<div class="skv-stat" style="animation-delay:${d}s"><b class="${cls}" data-count="${+n || 0}">${COUNTED ? +n || 0 : 0}</b><span>${label}</span></div>`;
    mount(`${crumbs(['Video Learner'])}
      <section class="skv-hero">
        <div class="skv-herotext">
          <span class="skv-eyebrow">${ICON.spark}AI Employee skill</span>
          <h1 class="skv-h1">Video Learner</h1>
          <p class="skv-lede">Show Hoola a video of any task once. It watches, writes down every step, and can then do that task for you in its own browser.</p>
          <ul class="skv-points">
            <li>${ICON.eye}<span>Watches the whole video, with the sound</span></li>
            <li>${ICON.list}<span>Keeps every step with the moment it saw it</span></li>
            <li>${ICON.shield}<span>Asks you before it sends or submits anything</span></li>
          </ul>
        </div>
        <div class="skv-heroart">${ART_LEARN}</div>
      </section>
      <div class="skv-stats">${stat(c.learned, 'tasks learned', '', .05)}${stat(c.proven, 'proven by a real run', 'ok', .1)}${stat(c.steps, 'steps Hoola knows', '', .15)}
        <div class="skv-stat day" style="animation-delay:.2s"><span class="skv-pill mute">${off ? 'Switched off on this server' : `${+LIST.today || 0} of ${+LIST.max_per_day || 0} videos learned today`}</span>
          <i class="skv-meter" aria-hidden="true"><u style="width:${LIST.max_per_day ? Math.min(100, (LIST.today || 0) / LIST.max_per_day * 100) : 0}%"></u></i><span>${off ? 'Ask the server owner to switch it on' : left ? `${left} more today` : 'Back tomorrow'}</span></div></div>
      ${doing.length ? doing.map(r => `<button type="button" class="skv-nowbar" data-run="${esc(rid(r))}"><span class="skv-pulse" aria-hidden="true"></span><span><b>${r.run.scored ? 'Hoola finished' : 'Hoola is doing'}: ${esc(r.title || 'your task')}</b><small>${r.run.scored ? 'Tell Hoola if it worked' : 'Started ' + esc(when(r.run.ts)) + ' · see how it is going'}</small></span><span class="skv-nowgo">${r.run.scored ? 'Did it work?' : 'View'}${ICON.arrow}</span></button>`).join('') : ''}
      ${off ? '<p class="skv-quiet">Learning from videos is switched off on this server.</p>' : `
      <section class="skv-teach" aria-labelledby="skvTeach" id="skvDrop">
        <div class="skv-teachhead"><h2 id="skvTeach">Teach Hoola a new task</h2><span class="skv-meta">A link or a file. One video, one task.</span></div>
        <div class="skv-teachrow">
          <label class="skv-link">${ICON.link}<span class="sr">Video link</span><input id="skvRef" type="text" autocomplete="off" spellcheck="false" placeholder="Paste a YouTube, Shorts or video link"></label>
          <label class="skv-name"><span class="sr">Name this task</span><input id="skvTitle" type="text" autocomplete="off" placeholder="Name it (optional), e.g. Fill the NSP scholarship form"></label>
          <button type="button" class="btn go skv-big" id="skvWatch">${ICON.eye}<span>Watch &amp; learn</span></button>
        </div>
        <div class="skv-teachfoot"><input type="file" id="skvFile" accept="video/*" hidden>
          <button type="button" class="btn soft skv-mid" id="skvPick">${ICON.up}<span>Upload a video file</span></button>
          <span class="skv-meta">or drop it here · up to 25 MB as a file, up to 3 hours as a link</span></div>
        <p class="skv-fine skv-lock">${ICON.shield}<span>Hoola never copies personal values from the video. Names, numbers and passwords you fill in yourself when it does the task.</span></p>
        <div class="skv-dropveil" aria-hidden="true">${ICON.up}<span>Drop the video to start</span></div>
      </section>`}
      <section class="skv-list" aria-labelledby="skvLearned">
        <div class="skv-listhead"><h2 id="skvLearned" class="skv-h2">Your learned tasks</h2>
          <div class="skv-filters" role="group" aria-label="Filter">
            ${[['all', 'All', rows.length], ['proven', 'Proven', proven.length], ['fresh', 'Not proven yet', fresh.length]]
              .map(([k, n, q]) => `<button type="button" class="${FILTER === k ? 'on' : ''}" data-filter="${k}" aria-pressed="${FILTER === k}">${esc(n)} <b>${q}</b></button>`).join('')}
          </div></div>
        ${shown.length ? `<div class="skv-rows">${shown.map(rowHTML).join('')}</div>` : rows.length ? '<p class="skv-quiet">Nothing in this filter.</p>' : emptyHTML()}
      </section>`, 'home');
  }
  const emptyHTML = () => `<div class="skv-empty"><ol>
      <li><span class="skv-estep">${ICON.play}</span><b>Show a video</b><small>A screen recording, a tutorial, a Short.</small></li>
      <li><span class="skv-estep">${ICON.list}</span><b>Hoola writes the steps</b><small>Each with the moment it was seen.</small></li>
      <li><span class="skv-estep">${ICON.click}</span><b>Hoola does the task</b><small>In its own browser, asking you first.</small></li></ol>
      <p class="skv-quiet">Nothing learned yet. Paste a video link above to teach Hoola its first task.</p></div>`;
  function rowHTML(r, i) {
    const [cls, word] = status(r), failed = r.status === 'failed', id = esc(rid(r));
    const site = r.site ? `${esc(r.site)} · ` : '';
    const meta = failed ? esc(r.error || 'Hoola could not watch this video.')
      : `${site}${esc(r.steps || 0)} steps · learned ${esc(when(r.ts))}${r.last_run ? ' · last done ' + esc(when(r.last_run)) : ''}`;
    const title = esc(r.title || 'Untitled task'), web = r.kind === 'website_work' || !r.kind, busy = r.run && r.run.cid;
    return `<div class="skv-row${failed ? ' failed' : ''}" style="animation-delay:${Math.min(i, 8) * .04}s">
      ${failed ? thumb(r) : `<button type="button" class="skv-thumbbtn" data-task="${id}" aria-label="Open ${title}">${thumb(r)}</button>`}
      <div class="skv-rowbd">${failed ? `<b class="skv-title still">${title}</b>` : `<button type="button" class="skv-title" data-task="${id}">${title}</button>`}
        <div class="skv-rowmeta">${busy ? `<span class="skv-pill lrn"><i></i>${r.run.scored ? 'Finished · did it work?' : 'Hoola is doing it'}</span>` : `<span class="skv-pill ${cls}">${esc(word)}</span>`}<span class="skv-meta">${meta}</span></div></div>
      ${failed ? '' : ring(pct(r.confidence))}
      <div class="skv-rowact">${failed
        ? `<button type="button" class="btn soft skv-mid" data-retry="${id}">Try again</button><button type="button" class="btn soft skv-mid" data-forget="${id}">Remove</button>`
        : `<button type="button" class="btn soft skv-mid" data-task="${id}">Open</button>${busy ? `<button type="button" class="btn go skv-mid" data-run="${id}">${r.run.scored ? 'Answer' : 'View'}</button>` : web ? `<button type="button" class="btn go skv-mid" data-doit="${id}">Do it now</button>` : ''}`}</div>
    </div>`;
  }

  // ---------------------------------------------------------------- screen 2: watching
  async function startWatch(ref, title, replace) {
    if (!ref) return toast('Which video? Paste a link or upload a file.', true);
    const btn = EL.querySelector('#skvWatch'); if (btn) { btn.disabled = true; btn.lastElementChild.textContent = 'Starting…'; }
    try {
      const r = await api('POST', '/api/seekh/console/watch', {video: ref, title, ...(replace ? {replace} : {})});
      if (r.already_running) toast('A video is already being learned. Showing that one.');
      JOB = {id: r.id, stage: 'queue', stages: [], perception: '', done: false, ref, title, kind: r.kind || '', row: replace ? (LIST.watches || []).find(x => rid(x) === replace) : null};
      showWatch();
    } catch (e) {
      toast(e.message || 'Could not start', true);
      if (btn) { btn.disabled = false; btn.lastElementChild.textContent = 'Watch & learn'; }
    }
  }
  function srcOfRef(ref, kind) {
    const s = String(ref || ''), yt = s.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([\w-]{11})/);
    if (yt) return {kind: 'youtube', key: yt[1]};
    if (/^https?:/i.test(s)) return {kind: 'url', key: s};
    if (/^kept:/.test(s)) return {kind: 'kept', key: s.slice(5)};
    return s ? {kind: kind === 'youtube' ? 'youtube' : 'file', key: s} : {kind: '', key: ''};
  }
  async function watchPlayer() {
    const p = EL.querySelector('#skvPlayer'); if (!p || !JOB.ref) return;
    const src = srcOfRef(JOB.ref, JOB.kind);
    if (src.kind === 'kept') {                // the learner's own copy: play it through its row
      const row = JOB.row || (LIST.watches || []).find(x => rid(x) === src.key);
      p.innerHTML = await playerHTML({kind: 'file', key: 'kept'}, 0, row || {id: src.key, media: {}});
    } else p.innerHTML = await playerHTML(src, 0);
    EL.querySelector('#skvVideo')?.addEventListener('loadedmetadata', markers);
  }
  async function showWatch() {
    stop();
    mount(`${crumbs(['Video Learner', 'home'], ['Watching'])}
      <header class="skv-head"><div class="skv-headtx"><h1 class="skv-h1 sm" id="skvWTitle">${esc(JOB.title || 'Learning a new task')}</h1>
        <p class="skv-meta skv-src" id="skvWSrc">${esc(/^kept:/.test(JOB.ref || '') ? 'Your uploaded video' : JOB.ref || '')}</p></div>
        <div class="skv-headact"><span class="skv-pill lrn" id="skvLive"><i></i><span id="skvLiveTx">Learning</span></span><button type="button" class="btn soft skv-mid" id="skvStop">Stop</button></div></header>
      <div id="skvNotice"></div>
      <div class="skv-split">
        <div class="skv-main">
          <div class="skv-glow on" id="skvGlow"><div class="skv-player" id="skvPlayer"><div class="skv-frame skv-noplay"><span>Loading the video…</span></div></div>
            <span class="skv-watchtag" id="skvTag">${BARS}<span>Hoola is watching</span></span></div>
          <div class="skv-marks" id="skvMarks" aria-hidden="true"></div>
          <section aria-labelledby="skvNotesH" class="skv-notes"><div class="skv-listhead"><h2 id="skvNotesH" class="skv-h3">Hoola's notes</h2><span class="skv-meta" id="skvNCount">written as Hoola watches</span></div>
            <div id="skvNotes" aria-live="polite"></div>
            <p class="skv-meta skv-hint">Click a time to jump the video there.</p></section>
        </div>
        <aside class="skv-side" aria-labelledby="skvHow"><h2 id="skvHow" class="skv-h3">How it's going</h2>
          <ol class="skv-stages" id="skvStages"><span class="skv-rail" aria-hidden="true"><u id="skvRail"></u></span>${STAGES.map(([k, t, sub]) => `<li data-k="${k}"><span class="skv-dot"></span><span><b>${esc(t)}</b><small>${esc(sub)}</small></span><em></em></li>`).join('')}</ol>
          <div class="skv-sofar"><div><b id="skvSoN">0</b><span>notes so far</span></div><div><b id="skvSoT">0:00</b><span>time so far</span></div></div>
          <p class="skv-fine">Usually takes about as long as the video. You can leave this page. Hoola keeps learning, and your task appears in the list when it is done.</p></aside>
      </div>`, 'watch');
    paintNotes('', true);
    await watchPlayer();
    paintWatch();
    POLL = setInterval(pollWatch, 1200); pollWatch();
    TICK = setInterval(tickWatch, 1000);
  }
  const elapsedNow = () => (JOB.elapsed || 0) + (JOB.done ? 0 : (Date.now() - (JOB._at || Date.now())) / 1000);
  function stageTimes() {                    // when each shown stage began (seconds into the job), from the real boundaries
    const at = new Map((JOB.stages || []).map(s => [s.k, s.ts]));
    const b = [at.get('classify'), at.get('fetch'), JOB.first_note || at.get('notes'), at.get('distill_start') ?? at.get('notes'), at.get('distill') ?? at.get('memory'), at.get('done')];
    if (JOB.done && !JOB.error && b[5] == null) b[5] = JOB.elapsed;
    return b;
  }
  function tickWatch() {
    if (!EL || VIEW !== 'watch' || !JOB) return;
    const t = elapsedNow();
    const l = EL.querySelector('#skvLiveTx'); if (l && !JOB.done) l.textContent = `Learning · ${mmss(t)}`;
    const so = EL.querySelector('#skvSoT'); if (so) so.textContent = mmss(t);
    const on = EL.querySelector('#skvStages li.on em');     // the stage running now counts up
    if (on && !JOB.done) { const b = stageTimes(), i = [...EL.querySelectorAll('#skvStages li')].indexOf(on.parentElement); if (b[i] != null) on.textContent = took(t - b[i]); }
  }
  function paintWatch() {
    if (!EL || VIEW !== 'watch' || !JOB) return;
    const b = stageTimes(), seen = new Set((JOB.stages || []).map(s => s.k));
    // which stage is live now: fetch = watching, the first streamed words = writing notes, notes done = distilling
    const at = seen.has('distill') || seen.has('memory') ? 4 : seen.has('notes') || seen.has('distill_start') ? 3
      : JOB.perception ? 2 : seen.has('fetch') ? 1 : 0;
    const cur = JOB.done && !JOB.error ? 5 : at;
    const lis = [...EL.querySelectorAll('#skvStages li')];
    lis.forEach((li, i) => {
      const did = i < cur;
      li.className = did ? 'did' : i === cur && !JOB.done ? 'on' : i === cur && JOB.error ? 'bad' : '';
      const dot = li.querySelector('.skv-dot'); if (did && !dot.innerHTML) dot.innerHTML = ICON.tick; if (!did) dot.innerHTML = li.className === 'bad' ? '!' : '';
      const em = li.querySelector('em');               // v0.785 how long the stage TOOK (it used to show when it began)
      if (did && b[i] != null && b[i + 1] != null) em.textContent = took(b[i + 1] - b[i]);
      else if (!did && !li.classList.contains('on')) em.textContent = '';
    });
    const rail = EL.querySelector('#skvRail');
    if (rail && lis.length) rail.style.height = `${Math.min(100, cur / (lis.length - 1) * 100)}%`;
    const n = paintNotes(JOB.perception, !JOB.done && !seen.has('notes'));
    const c = EL.querySelector('#skvNCount'); if (c) c.textContent = n ? `written as Hoola watches · ${n} so far` : 'written as Hoola watches';
    const so = EL.querySelector('#skvSoN'); if (so) so.textContent = n;
    const tag = EL.querySelector('#skvTag');
    if (tag) tag.lastElementChild.textContent = cur <= 1 ? 'Hoola is watching' : cur === 2 ? 'Hoola is writing notes' : cur === 3 ? 'Hoola is building the steps' : 'Saving to memory';
    if (JOB.title) { const t = EL.querySelector('#skvWTitle'); if (t) t.textContent = JOB.title; }
    const note = EL.querySelector('#skvNotice');
    if (note && JOB.resumed && !note.innerHTML) note.innerHTML = `<p class="skv-banner">${ICON.again}<span>The server restarted while Hoola was watching, so it started this video again from the beginning. Nothing else was lost.</span></p>`;
    tickWatch(); markers();
  }
  async function pollWatch() {
    if (!JOB || JOB.done) return;
    try {
      const r = await api('GET', `/api/seekh/console/progress?id=${encodeURIComponent(JOB.id || '')}`);
      const hadRef = !!JOB.ref;
      JOB = {...JOB, ...r, ref: r.ref || JOB.ref, title: r.title || JOB.title, _at: Date.now()};
      if (!hadRef && JOB.ref) {                          // adopted after a reload: now the page knows the video
        await watchPlayer();
        const w = EL.querySelector('#skvWSrc'); if (w) w.textContent = /^kept:/.test(JOB.ref) ? 'Your uploaded video' : JOB.ref;
      }
      paintWatch();
      if (r.done) {
        stop();
        EL.querySelector('#skvGlow')?.classList.remove('on');
        EL.querySelector('#skvTag')?.remove();
        await refresh();
        if (r.error) {
          if (r.stopped) { toast('Stopped. Nothing was kept.'); return showHome(); }
          const l = EL.querySelector('#skvLive'); if (l) { l.className = 'skv-pill bad'; l.textContent = 'Could not learn'; }
          EL.querySelector('#skvStop')?.remove();
          const box = EL.querySelector('#skvNotice');
          if (box) box.innerHTML = `<div class="skv-error">${ICON.warn}<div><b>Hoola could not learn this video.</b><span>${esc(r.error)}</span>
            <div class="skv-btnrow"><button type="button" class="btn go skv-mid" id="skvAgain">Try again</button><button type="button" class="btn soft skv-mid" data-go="home">Back to the list</button></div></div></div>`;
          EL.querySelector('#skvAgain')?.addEventListener('click', () => {      // the failure row now holds the video: retry replaces it
            const f = (LIST.watches || []).find(x => x.status === 'failed' && (x.ref === JOB.ref || refOf(x) === JOB.ref)) || (LIST.watches || []).find(x => x.status === 'failed');
            startWatch(f ? refOf(f) : JOB.ref, JOB.title, f ? rid(f) : '');
          });
          wire();
          return;
        }
        const l = EL.querySelector('#skvLive'); if (l) { l.className = 'skv-pill ok'; l.textContent = 'Learned'; }
        toast('Learned. It is in your learned tasks now.');
        const pid = r.result && (r.result.id || r.result.procedure_id);
        setTimeout(() => { if (VIEW !== 'watch') return; if (pid) openTask(pid, true); else showHome(); }, calm() ? 0 : 700);
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
  async function openTask(id, justLearned) {
    stop();
    try { TASK = await api('GET', `/api/seekh/console/task?id=${encodeURIComponent(id)}`); }
    catch (e) { toast(e.message, true); return showHome(); }
    showTask(justLearned);
  }
  function fieldsOf(t) {                    // the form: one box per thing the task needs (from the learned hints)
    const seen = new Set(), out = [];
    for (const s of ((t.detail || {}).steps || [])) {
      const key = s.value_var || (s.value_hint ? s.value_hint.slice(0, 40) : '');
      const isFile = String(s.action || '').toLowerCase() === 'upload';
      if ((!key && !isFile) || seen.has(key || 'file' + s.n)) continue; seen.add(key || 'file' + s.n);
      out.push({key, file: isFile, label: s.value_var ? human(s.value_var) : human(s.value_hint || s.note || 'File to upload'), hint: s.value_hint || ''});
    }
    return out.slice(0, 12);
  }
  function showTask(justLearned) {
    const t = TASK, d = t.detail || {}, steps = d.steps || [], [cls, word] = status(t), web = !t.kind || t.kind === 'website_work';
    const box = (title, xs, kind, ic) => xs && xs.length ? `<div class="skv-box ${kind}"><h3>${ic}${title}</h3><ul>${xs.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
    const fields = fieldsOf(t), id = esc(rid(t)), busy = t.run && t.run.cid;
    const wins = +t.wins || 0, fails = +t.fails || 0;
    const proof = wins ? `Worked ${wins === 1 ? 'once' : wins + ' times'}${fails ? ` · did not work ${fails === 1 ? 'once' : fails + ' times'}` : ''}${t.last_run ? ' · last done ' + esc(when(t.last_run)) : ''}`
      : fails ? `Tried ${fails === 1 ? 'once' : fails + ' times'}, not right yet` : 'Not tried yet. The first real run proves it.';
    mount(`${crumbs(['Video Learner', 'home'], [t.title || 'Learned task'])}
      <header class="skv-head"><div class="skv-headtx"><h1 class="skv-h1">${esc(t.title || 'Learned task')}</h1>
        <div class="skv-rowmeta"><span class="skv-pill ${cls}">${esc(word)}</span>${t.site ? `<span class="skv-pill mute">Website task · ${esc(t.site)}</span>` : web ? '' : '<span class="skv-pill mute">Not a website task</span>'}
        <span class="skv-meta">${esc(t.steps || steps.length)} steps · learned ${esc(when(t.ts))} · from ${esc(sourceWord(t))}</span></div></div>
        <div class="skv-headact"><button type="button" class="btn soft skv-mid" id="skvRelearn">${ICON.again}<span>Re-learn</span></button><button type="button" class="btn soft skv-mid" data-forget="${id}">${ICON.bin}<span>Remove</span></button></div></header>
      ${justLearned ? `<p class="skv-banner ok">${ICON.tick}<span>Learned from the video. Check the steps below, then let Hoola try it for real.</span></p>` : ''}
      ${busy ? `<button type="button" class="skv-nowbar" data-run="${id}"><span class="skv-pulse" aria-hidden="true"></span><span><b>${t.run.scored ? 'Hoola finished this task' : 'Hoola is doing this task now'}</b><small>${t.run.scored ? 'Tell Hoola if it worked' : 'Started ' + esc(when(t.run.ts))}</small></span><span class="skv-nowgo">${t.run.scored ? 'Did it work?' : 'View'}${ICON.arrow}</span></button>` : ''}
      <div class="skv-split">
        <div class="skv-main">
          <details class="skv-vid" id="skvVid"><summary><span class="skv-vidic">${ICON.play}</span><span><b>Watch the video</b><small>${esc(sourceWord(t))} · click any time below to jump there</small></span></summary><div class="skv-player" id="skvPlayer"></div></details>
          <section aria-labelledby="skvStepsH"><div class="skv-listhead"><h2 id="skvStepsH" class="skv-h3">The steps Hoola learned</h2><span class="skv-meta">each with the moment it was seen</span></div>
            <ol class="skv-steps">${steps.map((s, i) => `<li style="animation-delay:${Math.min(i, 10) * .035}s"><span class="skv-n">${esc(s.n || i + 1)}</span>
              <span class="skv-stepbd"><span class="skv-act" title="${esc(human(s.action))}">${stepIcon(s.action)}</span><span>${esc(s.note || human(s.action))}${s.value_hint ? `<small>You fill: ${esc(s.value_hint)}</small>` : ''}</span></span>
              <span class="skv-evs">${(s.evidence || []).slice(0, 2).map(e => `<button type="button" class="skv-ts" data-t="${esc(e)}">${esc(e)}</button>`).join('')}</span></li>`).join('') || '<li class="none"><span></span><span class="skv-quiet">No steps were kept for this task.</span><span></span></li>'}</ol></section>
          <div class="skv-boxes">${box('Before you start', d.preconditions, 'pre', ICON.check)}${box('Watch out', d.gotchas, 'warn', ICON.warn)}${box('Not seen in the video', d.unsure, 'dim', ICON.eye)}</div>
        </div>
        <aside class="skv-side skv-doit" aria-labelledby="skvDoH">
          <div class="skv-sure">${ring(pct(t.confidence), true)}<div><b>How sure Hoola is</b><small>${proof}</small></div></div>
          <h2 id="skvDoH" class="skv-h3">${web ? 'Let Hoola do it' : 'Ask Hoola to guide you'}</h2>
          <p class="skv-fine first">${web ? 'Fill what the video can\'t know. Hoola uses its own browser and asks you before submitting anything.' : 'This was not a website task, so Hoola walks you through the steps in chat.'}</p>
          <form id="skvForm" class="skv-form">
            ${fields.map((f, i) => f.file
              ? `<div class="skv-field"><span class="skv-lab">${esc(f.label)}</span><label class="skv-filepick"><input type="file" name="u${i}" data-file="${esc(f.label)}"><span class="skv-fileic">${ICON.file}</span><span class="skv-filetx" data-empty="${esc(f.hint || 'Choose the file to upload')}">${esc(f.hint || 'Choose the file to upload')}</span><span class="skv-filebtn">Choose</span></label></div>`
              : `<label class="skv-field"><span class="skv-lab">${esc(f.label)}</span><input name="f${i}" data-label="${esc(f.label)}" placeholder="${esc(f.hint)}" autocomplete="off"></label>`).join('')}
            <label class="skv-field"><span class="skv-lab">Anything else for Hoola <span class="skv-opt">(optional)</span></span><input name="extra" placeholder="e.g. use the photo I sent yesterday" autocomplete="off"></label>
            <button type="submit" class="btn go skv-big skv-wide"${busy ? ' disabled' : ''}>${ICON.click}<span>${web ? 'Do it now' : 'Guide me now'}</span></button>
            ${busy ? '<p class="skv-fine first">Hoola is already on this task. Open that run above.</p>' : ''}
          </form>
        </aside>
      </div>`, 'task');
    EL.querySelector('#skvRelearn')?.addEventListener('click', () => {      // v0.785 the new watch takes this task's place
      if (confirm('Watch this video again? What Hoola learns now replaces these steps.')) startWatch(refOf(t), t.title || '', rid(t));
    });
    EL.querySelector('#skvForm')?.addEventListener('submit', e => { e.preventDefault(); doIt(); });
    EL.querySelectorAll('.skv-filepick input').forEach(inp => inp.addEventListener('change', () => {
      const f = inp.files && inp.files[0], tx = inp.parentElement.querySelector('.skv-filetx');
      if (f && f.size > 25 * 1024 * 1024) { inp.value = ''; tx.textContent = tx.dataset.empty; inp.parentElement.classList.remove('has'); return toast(`${f.name} is over 25 MB.`, true); }
      tx.textContent = f ? f.name : tx.dataset.empty; inp.parentElement.classList.toggle('has', !!f);
    }));
    const det = EL.querySelector('#skvVid');
    det?.addEventListener('toggle', async () => { const p = EL.querySelector('#skvPlayer'); if (det.open && p && !p.innerHTML) p.innerHTML = await playerHTML(srcOf(t), 0, t); });
  }

  // ---------------------------------------------------------------- screen 4: Hoola doing it
  async function doIt() {
    const t = TASK; if (!t) return;
    const form = EL.querySelector('#skvForm'), vals = [];
    form.querySelectorAll('input[data-label]').forEach(i => { if (i.value.trim()) vals.push(`${i.dataset.label}: ${i.value.trim()}`); });
    const extra = String(form.querySelector('[name=extra]')?.value || '').trim();
    const web = !t.kind || t.kind === 'website_work';
    const b = form.querySelector('button[type=submit]'), label = b.lastElementChild;
    b.disabled = true; label.textContent = 'Starting…';
    try {
      const fileIds = [], named = [];                     // v0.785 a step that uploads a file: the file rides this chat turn
      for (const inp of form.querySelectorAll('input[data-file]')) {
        const f = inp.files && inp.files[0]; if (!f) continue;
        label.textContent = `Sending ${f.name}…`;
        const up = await upload(f);
        if (up && up.file_id) { fileIds.push(up.file_id); named.push(`${inp.dataset.file}: the attached file "${f.name}"`); }
      }
      label.textContent = 'Starting…';
      const msg = `Do the learned task "${t.title}" now, for real.`
        + (vals.length ? ` The values to use: ${vals.join('; ')}.` : '')
        + (named.length ? ` Files to upload: ${named.join('; ')}.` : '')
        + (extra ? ` ${extra}` : '')
        + (web ? ' Use your own browser and the recipe learned from the video as a guide, checking every step against the live page. Ask me before sending or submitting anything, and ask me for any value the video did not show.'
               : ' Walk me through the steps one by one; check each one with me before moving on.');
      const r = await send(msg, fileIds);
      const cid = (r && (r.conversation_id || r.conv)) || '';
      RUN = {cid, after: 0, task: t, steps: new Map(), reply: '', done: false, t0: Date.now(), waiting: []};
      try {                                               // remember the run on the server: leaving the page loses nothing
        const tl = await api('GET', `/api/conversations/${encodeURIComponent(cid)}/timeline?own=1&limit=30`);
        const mine = [...(tl.events || [])].reverse().find(e => e.kind === 'message' && e.payload && e.payload.role === 'user' && String(e.payload.text || '').startsWith('Do the learned task'));
        if (mine) { RUN.after = mine.id - 1; }
        await api('POST', '/api/seekh/console/run', {id: rid(t), conversation_id: cid, after: RUN.after});
        t.run = {cid, after: RUN.after, ts: new Date().toISOString(), scored: false};
      } catch { /* the run still shows on this page; only the come-back is lost */ }
      showRun();
    } catch (e) { toast('Could not start: ' + (e.message || ''), true); b.disabled = false; label.textContent = web ? 'Do it now' : 'Guide me now'; }
  }
  async function resumeRun(id) {             // from the list / the task: an open run kept on the server
    stop();
    try { TASK = await api('GET', `/api/seekh/console/task?id=${encodeURIComponent(id)}`); }
    catch (e) { toast(e.message, true); return showHome(); }
    const run = TASK.run || {};
    if (!run.cid) return showTask();
    RUN = {cid: run.cid, after: +run.after || 0, task: TASK, steps: new Map(), reply: '', done: false, t0: Date.parse(run.ts) || Date.now(), waiting: [], scored: !!run.scored};
    showRun();
  }
  function showRun() {
    stop();
    const t = RUN.task, planned = ((t.detail || {}).steps || []);
    mount(`${crumbs(['Video Learner', 'home'], [t.title || 'Task', 'task'], ['Doing it'])}
      <header class="skv-head"><div class="skv-headtx"><h1 class="skv-h1 sm"><span id="skvRunVerb">Hoola is doing</span>: ${esc(t.title || 'your task')}</h1>
        <p class="skv-meta" id="skvRunMeta">Starting…</p></div>
        <div class="skv-headact"><span class="skv-pill lrn" id="skvRunPill"><i></i><span>Working</span></span><button type="button" class="btn soft skv-mid" id="skvRunStop">Stop</button><button type="button" class="btn soft skv-mid" id="skvRunChat">${ICON.chat}<span>Open in chat</span></button></div></header>
      <div class="skv-split">
        <div class="skv-main">
          <div class="skv-stage on" id="skvStage"><div class="skv-stageart">${ART_BROWSER}</div>
            <div class="skv-stagetx"><small>Hoola's own browser</small><b id="skvNow">Getting ready…</b><span class="skv-meta">The page may look different from the video. Hoola checks every step against the live page.</span></div></div>
          <div id="skvWait"></div>
          <section aria-labelledby="skvActH"><div class="skv-listhead"><h2 id="skvActH" class="skv-h3">What Hoola is doing</h2><span class="skv-meta" id="skvActN"></span></div>
            <ol class="skv-acts" id="skvActs" aria-live="polite"><li class="none"><span></span><span class="skv-quiet">Waiting for the first step…</span><span></span></li></ol></section>
          <div id="skvReply"></div>
          <div id="skvVerdict"></div>
        </div>
        <aside class="skv-side"><h2 class="skv-h3">The learned steps</h2>
          <ol class="skv-plan">${planned.map((s, i) => `<li><span class="skv-n">${esc(s.n || i + 1)}</span><span>${esc(s.note || human(s.action))}</span></li>`).join('')}</ol>
          <p class="skv-fine">You can leave this page. The run keeps going, and this task shows "Hoola is doing it" until you say how it went.</p></aside>
      </div>`, 'run');
    EL.querySelector('#skvRunChat')?.addEventListener('click', () => openChat());
    EL.querySelector('#skvRunStop')?.addEventListener('click', async () => {
      if (!RUN.cid) return;
      try { await api('POST', `/api/conversations/${encodeURIComponent(RUN.cid)}/stop`, {}); toast('Stopped.'); } catch (e) { toast(e.message, true); }
    });
    POLL = setInterval(pollRun, 2000); pollRun();
    TICK = setInterval(() => { const m = EL && EL.querySelector('#skvRunMeta'); if (m && RUN && !RUN.done) m.textContent = `${RUN.steps.size} ${RUN.steps.size === 1 ? 'step' : 'steps'} so far · ${mmss((Date.now() - RUN.t0) / 1000)} · in Hoola's own browser`; }, 1000);
  }
  const openChat = () => (chat ? chat(RUN && RUN.cid) : go('chat'));
  async function pollRun() {
    if (!RUN || !RUN.cid || RUN.done || VIEW !== 'run') return;
    let tl, rv = null;
    try { tl = await api('GET', `/api/conversations/${encodeURIComponent(RUN.cid)}/timeline?steps=1&own=1&limit=200`); } catch { return; }
    try { rv = await api('GET', `/api/seekh/console/run?id=${encodeURIComponent(rid(RUN.task))}`); } catch { /* an old server: the timeline alone */ }
    if (!RUN || VIEW !== 'run') return;
    const evs = (tl.events || []).filter(e => e.id > RUN.after);
    if (!RUN.started) {                     // our own message is the start line: everything after it is this run
      const mine = evs.find(e => e.kind === 'message' && e.payload && e.payload.role === 'user' && String(e.payload.text || '').includes(RUN.task.title || '\u0000'));
      if (!mine) return;
      RUN.after = mine.id; RUN.started = true;
    }
    const after = evs.filter(e => e.id > RUN.after);
    let running = false, reply = '';
    const cards = [];
    for (const e of after) {
      const p = e.payload || {};
      if (e.kind === 'step') { RUN.steps.set(p.id || e.id, {label: p.label || p.tool || 'Working', state: p.state || 'running', at: e.at}); }
      else if (e.kind === 'message' && p.role === 'assistant' && p.source !== 'greeting') reply = String(p.text || '');
      else if (!rv && needsHer(p)) cards.push({id: e.id, title: p.title || p.question || p.label || human(e.kind)});
    }
    for (const s of RUN.steps.values()) if (s.state === 'running') running = true;
    if (rv) { (rv.waiting || []).forEach(w => cards.push(w)); if (rv.run && rv.run.scored) RUN.scored = true; if (rv.busy) running = true; }
    // the steps: keyed, so a step already on screen is only updated (its entrance never re-plays)
    const acts = EL.querySelector('#skvActs');
    if (acts && RUN.steps.size) {
      acts.querySelector('.none')?.remove();
      for (const [key, s] of RUN.steps) {
        const cls = s.state === 'running' ? 'on' : s.state === 'failed' || s.state === 'error' ? 'bad' : 'did';
        let li = acts.querySelector(`li[data-k="${CSS.escape(String(key))}"]`);
        if (!li) { li = document.createElement('li'); li.dataset.k = String(key); li.innerHTML = '<span class="skv-dot"></span><span></span><em></em>'; acts.appendChild(li); li.classList.add('new'); }
        if (li.dataset.s !== cls + s.label) {
          li.dataset.s = cls + s.label; li.className = cls + (li.classList.contains('new') ? ' new' : '');
          li.children[0].innerHTML = cls === 'on' ? '' : cls === 'bad' ? '!' : ICON.tick;
          li.children[1].textContent = s.label;
          li.children[2].textContent = new Date(s.at).toLocaleTimeString('en-IN', {hour: 'numeric', minute: '2-digit'});
        }
      }
      const n = EL.querySelector('#skvActN'); if (n) n.textContent = `${RUN.steps.size} so far`;
    }
    const last = [...RUN.steps.values()].pop(), now = EL.querySelector('#skvNow'), stage = EL.querySelector('#skvStage'), pill = EL.querySelector('#skvRunPill');
    const waiting = cards.length > 0;
    if (now) now.textContent = waiting ? 'Waiting for your answer' : last && last.state === 'running' ? last.label : last ? 'Thinking about the next step…' : 'Getting ready…';
    if (stage) stage.classList.toggle('on', !waiting);
    if (pill) { pill.className = `skv-pill ${waiting ? 'warn' : 'lrn'}`; pill.innerHTML = waiting ? 'Needs you' : '<i></i><span>Working</span>'; }
    const wait = EL.querySelector('#skvWait'), wkey = cards.map(c => c.id).join(',');
    if (wait && wait.dataset.k !== wkey) {
      wait.dataset.k = wkey;
      wait.innerHTML = waiting ? `<section class="skv-waiting" aria-label="Waiting for you"><span class="skv-waitic">${ICON.warn}</span><div><small>Waiting for you</small><b>${esc(cards[cards.length - 1].title)}</b>
        <span class="skv-fine first">Answer it in the chat. Hoola carries on the moment you do.</span></div><button type="button" class="btn go skv-mid" id="skvAnswer">Answer</button></section>` : '';
      EL.querySelector('#skvAnswer')?.addEventListener('click', () => openChat());
    }
    if (reply && RUN.reply !== reply) { RUN.reply = reply; const rb = EL.querySelector('#skvReply'); if (rb) rb.innerHTML = `<div class="skv-replybox"><small>Hoola says</small><p>${esc(reply.slice(0, 900))}</p></div>`; }
    if ((reply && !running && !waiting) || (RUN.scored && !running && !waiting)) finishRun();
  }
  function finishRun() {
    RUN.done = true; stop();
    const m = EL.querySelector('#skvRunMeta'); if (m) m.textContent = `Finished · ${RUN.steps.size} ${RUN.steps.size === 1 ? 'step' : 'steps'} · ${mmss((Date.now() - RUN.t0) / 1000)}`;
    const stage = EL.querySelector('#skvStage'); if (stage) { stage.classList.remove('on'); stage.classList.add('end'); }
    const verb = EL.querySelector('#skvRunVerb'); if (verb) verb.textContent = 'Hoola did';
    const ah = EL.querySelector('#skvActH'); if (ah) ah.textContent = 'What Hoola did';
    const an = EL.querySelector('#skvActN'); if (an) an.textContent = `${RUN.steps.size} ${RUN.steps.size === 1 ? 'step' : 'steps'}`;
    const now = EL.querySelector('#skvNow'); if (now) now.textContent = RUN.scored ? 'The browser work finished well' : 'Hoola has finished its turn';
    const pill = EL.querySelector('#skvRunPill'); if (pill) { pill.className = 'skv-pill mute'; pill.textContent = 'Finished'; }
    EL.querySelector('#skvRunStop')?.remove();
    const v = EL.querySelector('#skvVerdict');
    if (v) v.innerHTML = `<section class="skv-verdict"><div><b>Did it work?</b><span>${RUN.scored ? 'The browser work finished, so this task already counts as Proven. Tell Hoola if something was wrong.' : 'Saying yes marks this task Proven, so next time Hoola goes faster and asks less.'}</span></div>
      <div class="skv-btnrow"><button type="button" class="btn go skv-yes skv-mid" data-verdict="1">${ICON.tick}<span>Yes, it worked</span></button><button type="button" class="btn soft skv-mid" data-verdict="0">Something was wrong</button><button type="button" class="skv-skip" data-verdict="skip">Not sure yet</button></div></section>`;
    v?.querySelectorAll('[data-verdict]').forEach(b => b.addEventListener('click', () => verdict(b.dataset.verdict)));
  }
  const needsHer = p => { const st = String(p.status || p.state || '').toLowerCase(); return ['pending', 'waiting', 'ask', 'needs_you', 'open'].includes(st) && !p.decided && !p.answered; };
  async function verdict(how) {
    const id = rid(RUN.task), ok = how === '1';
    try {
      await api('POST', '/api/seekh/console/proven', how === 'skip' ? {id, skip: true} : {id, ok});
      RUN = null;
      if (how === 'skip') { await refresh(); return openTask(id); }
      const v = EL.querySelector('#skvVerdict');
      if (ok && v && !calm()) {                           // one small celebration, then the task page
        v.innerHTML = `<section class="skv-verdict won"><span class="skv-won" aria-hidden="true"><svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="27"/><path d="M20 33l8.5 8.5L45 24"/></svg>${'<i></i>'.repeat(8)}</span><div><b>Proven</b><span>Hoola will go faster and ask less next time.</span></div></section>`;
        await new Promise(r => setTimeout(r, 1300));
      } else toast(ok ? 'Marked Proven.' : 'Noted. You can re-learn it or tell Hoola what went wrong in chat.');
      await refresh(); openTask(id);
    } catch (e) { toast(e.message, true); }
  }

  // ---------------------------------------------------------------- wiring shared by every screen
  async function forget(id) {
    if (!confirm('Remove this task? Hoola forgets these steps.')) return;
    try { await api('DELETE', `/api/seekh/console/task?id=${encodeURIComponent(id)}`); toast('Removed.'); await refresh(); showHome(); }
    catch (e) { toast(e.message, true); }
  }
  function wireTs(root) {
    root.querySelectorAll('.skv-ts').forEach(b => { if (b.dataset.w) return; b.dataset.w = '1'; b.addEventListener('click', async () => {
      const det = EL.querySelector('#skvVid');
      if (det && !det.open) { det.open = true; const p = EL.querySelector('#skvPlayer'); if (p && !p.innerHTML) p.innerHTML = await playerHTML(srcOf(TASK), secs(b.dataset.t), TASK); if (!seek(b.dataset.t)) return; return; }
      if (!seek(b.dataset.t)) toast('This video can only be played at its own link.');
    }); });
  }
  function wire() {
    const q = s => EL.querySelector(s);
    EL.querySelectorAll('[data-go]').forEach(b => { if (b.dataset.w) return; b.dataset.w = '1'; b.addEventListener('click', async () => {
      const to = b.dataset.go;
      if (to === 'hub') { stop(); return go('hire'); }
      if (to === 'task' && TASK) return openTask(rid(TASK));
      await refresh(); showHome();
    }); });
    q('#skvWatch')?.addEventListener('click', () => startWatch(String(q('#skvRef')?.value || '').trim(), String(q('#skvTitle')?.value || '').trim()));
    q('#skvRef')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q('#skvWatch')?.click(); } });
    q('#skvTitle')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); q('#skvWatch')?.click(); } });
    q('#skvPick')?.addEventListener('click', () => q('#skvFile')?.click());
    q('#skvFile')?.addEventListener('change', e => { const f = e.target.files && e.target.files[0]; e.target.value = ''; if (f) take(f); });
    const drop = q('#skvDrop');
    if (drop) {
      drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
      drop.addEventListener('dragleave', e => { if (!drop.contains(e.relatedTarget)) drop.classList.remove('over'); });
      drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); const f = e.dataTransfer?.files?.[0]; if (f) take(f); });
    }
    q('#skvStop')?.addEventListener('click', stopWatch);
    EL.querySelectorAll('[data-filter]').forEach(b => b.addEventListener('click', () => { FILTER = b.dataset.filter; showHome(); }));
    EL.querySelectorAll('[data-task]').forEach(b => b.addEventListener('click', () => openTask(b.dataset.task)));
    EL.querySelectorAll('[data-run]').forEach(b => b.addEventListener('click', () => resumeRun(b.dataset.run)));
    EL.querySelectorAll('[data-doit]').forEach(b => b.addEventListener('click', async () => { await openTask(b.dataset.doit); EL.querySelector('#skvForm input:not([type=file])')?.focus(); }));
    EL.querySelectorAll('[data-forget]').forEach(b => b.addEventListener('click', () => forget(b.dataset.forget)));
    EL.querySelectorAll('[data-retry]').forEach(b => b.addEventListener('click', () => {
      const row = (LIST.watches || []).find(r => rid(r) === b.dataset.retry);
      if (row) startWatch(refOf(row), row.title || '', rid(row));       // v0.785 the retry takes the failed row's place
    }));
    wireTs(EL);
  }
  async function take(f) {
    if (f.size > 25 * 1024 * 1024) return toast(`${f.name} is over 25 MB. Paste the video's link instead.`, true);
    if (!/^video\//.test(f.type || '')) return toast(`${f.name} is not a video file.`, true);
    const b = EL.querySelector('#skvPick'); if (b) { b.disabled = true; b.lastElementChild.textContent = 'Uploading…'; }
    try {
      const r = await upload(f);
      const title = String(EL.querySelector('#skvTitle')?.value || '').trim() || f.name.replace(/\.[^.]+$/, '');
      await startWatch(r.file_id || '', title);
    } catch (e) { toast(`${f.name}: ${e.message || 'upload failed'}`, true); if (b) { b.disabled = false; b.lastElementChild.textContent = 'Upload a video file'; } }
  }
  // the console re-opens the page by calling open(el); polling stops when the page is left and picks up on return
  document.addEventListener('visibilitychange', () => { if (document.hidden) return; if (VIEW === 'run' && RUN && !RUN.done && !POLL && EL && EL.isConnected && EL.offsetParent) POLL = setInterval(pollRun, 2000); });
  return {open: openPage, leave: stop};
};
