/* v0.716 SEEKH MANCH ON THE CONSOLE - the HOOLA AI VIDEO LEARNER (the owner's console page for v0.713's
   learn-from-a-video): load a video, watch Hoola take notes in REALTIME, see the MEMORY it prepared, and
   tell it to PERFORM THIS TASK NOW on this very page - Hoola runs the task with its own browser through
   one honest chat turn (the computer operator reads the draft recipe at job start).

   Rules this page keeps (the server's rules, drawn):
   - every stage shown is a REAL boundary of seekh.watch (classify / fetch / notes / distill / memory),
     never a guess - the elapsed times come from the pipeline itself;
   - the notes area shows exactly what Hoola's eyes returned (the [m:ss] moments included); the word-by-word
     reveal is pacing, the text is not touched;
   - learned is NOT proven: the memory card says so until a real run has worked, and the perform turn asks
     for the run to be verified step by step against the live page;
   - nothing is performed by this page itself: PERFORM composes one chat turn through the same door the
     composer uses, so sending / submitting still asks for her tap;
   - every value that came from the server goes through esc() - a step note, a site name or a gotcha is
     data, never markup. */
'use strict';
window.HoolaSeekh = function ({api, esc, toast, send, upload, open, live}) {
  let EL = null, TIMER = null, PACER = null;
  let LIST = null;                 // GET /api/seekh/console/watches
  let JOB = null;                  // {id, stage, stages, perception, done, error, result, ...}
  let NOTES_AT = 0;                // how many chars of the perception are drawn (the pacer)
  let PERFORM = '';                // the kaam title the perform form is aimed at

  const IN = 'border:1px solid var(--hair);border-radius:10px;padding:9px 12px;background:var(--bg);color:var(--ink);min-width:0';
  const mmss = s => { s = Math.max(0, Math.round(+s || 0)); const m = Math.floor(s / 60), x = String(s % 60).padStart(2, '0'); return `${m}:${x}`; };
  const when = iso => { if (!iso) return '–'; const d = new Date(iso); return isNaN(d) ? '–' : d.toLocaleString('en-IN', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}); };
  const pct = c => Math.round(Math.min(1, Math.max(0, +c || 0)) * 100);
  const tag = (c, n) => `<span class="tag ${c}">${esc(n)}</span>`;

  // the five steps the panel shows - every one a real pipeline boundary
  const STEPS = [['classify', 'Pehchana', 'kaunsa video hai'],
                 ['fetch', 'Video dekh rahi hoon', 'download karke aankhon se dekh rahi hoon'],
                 ['notes', 'Notes likh rahi hoon', 'jo jo dikha, timestamp ke saath'],
                 ['distill', 'Steps bana rahi hoon', 'ek recipe bana rahi hoon'],
                 ['memory', 'Memory', 'Seekhe hue kaam mein rakh rahi hoon']];
  const stepOf = st => st === 'done' ? 4 : Math.max(0, STEPS.findIndex(([k]) => k === st));
  const atStage = k => !JOB ? -1 : (JOB.stages || []).findIndex(s => s.k === k || (k === 'distill' && s.k === 'distill_start'));

  // ------------------------------------------------------------ open + draw
  async function open(el) {
    EL = el;
    EL.innerHTML = `<div class="vh"><h2>HOOLA AI Video Learner</h2></div><div class="empty">Loading…</div>`;
    await refresh();
    if (EL.isConnected) draw();
  }

  async function refresh() {
    try { LIST = await api('GET', '/api/seekh/console/watches'); }
    catch (e) { if (EL) EL.innerHTML = `<div class="vh"><h2>HOOLA AI Video Learner</h2></div><p class="badc">${esc(e.message)}</p>`; return false; }
    if (LIST && LIST.running && (!JOB || JOB.id !== LIST.running)) {   // a watch is already live: adopt it
      JOB = {id: LIST.running, stage: 'fetch', stages: [], perception: '', done: false};
      NOTES_AT = 0; startPoll();
    }
    return true;
  }

  function draw() {
    if (!EL || !LIST) return;
    const off = LIST.enabled === false;
    const head = `<div class="vh"><h2>HOOLA AI Video Learner</h2>
        <span class="muted">Load a video - Hoola watches it, takes notes in realtime, keeps the way of working in memory. Then tell it to perform the task on this page - with its own browser.</span></div>
        <div class="sk-tags">${off ? tag('bad', 'Seekhna band hai') : `${tag('ok', 'On')} ${tag('v', `Aaj ${LIST.today}/${LIST.max_per_day} seekhe`)}`}</div>`;
    if (off) { EL.innerHTML = head + `<div class="card"><p>Video se seekhna server par band kar diya gaya hai.</p></div>`; return; }
    EL.innerHTML = head + learnCard() + liveCard() + memoryCard() + performCard() + listCard();
    wire();
    drawLive(); renderNotes();                     // paint whatever the job already is
  }

  // ------------------------------------------------------------ the cards
  function learnCard() {
    return `<section class="tile gl sk-card" aria-labelledby="skLearnH">
      <h3 id="skLearnH"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="14" height="14" rx="2"/><path d="M16 10l6-3v10l-6-3"/></svg>Naya kaam seekhaye</h3>
      <div class="sk-form">
        <label class="sk-field sk-grow"><span>Video ka link <small class="muted">(YouTube, Shorts ya direct URL)</small></span>
          <input id="skRef" type="text" autocomplete="off" spellcheck="false" placeholder="https://youtube.com/watch?v=… ya video ka URL" style="${IN}"></label>
        <label class="sk-field"><span>Naam <small class="muted">(optional)</small></span>
          <input id="skTitle" type="text" autocomplete="off" placeholder="Jaise: NSP form bharne ka tareeka" style="${IN}"></label>
        <div class="sk-btnrow">
          <input type="file" id="skFile" accept="video/*" hidden>
          <button type="button" class="btn soft" id="skPick"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px;vertical-align:-2px;margin-right:5px" aria-hidden="true"><path d="M21 12.5l-8.5 8.5a5 5 0 0 1-7-7L14 5.5a3.3 3.3 0 0 1 4.7 4.7L10.2 18.7a1.7 1.7 0 0 1-2.4-2.4L15.5 8.6"/></svg>Video file chuniye</button>
          <button type="button" class="btn go" id="skWatch">Watch &amp; Learn</button>
        </div>
        <p class="muted sk-small">File 25 MB tak chat lane se jaati hai; bade video ka link dijiye. Hoola 3 ghante tak ke video dekh leti hai. Jo seekha ja raha hai usme koi personal value nahi rakhi jaati - values bharni aapko hongi.</p>
      </div></section>`;
  }

  function liveCard() {
    const steps = STEPS.map(([k, t, sub], i) => `<li class="sk-step" data-step="${i}"><i class="sk-dot"></i><span><b>${esc(t)}</b><small>${esc(sub)}</small></span><em></em></li>`).join('');
    return `<section class="tile gl sk-card sk-live" id="skLive"${JOB ? '' : ' hidden'} aria-labelledby="skLiveH">
      <h3 id="skLiveH"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>Hoola dekh rahi hai<span class="sk-elapsed" id="skElapsed"></span></h3>
      <ol class="sk-steps">${steps}</ol>
      <div class="sk-notes" aria-live="polite">
        <div class="sk-notes-hd">HOOLA KI NOTES <small>- jaise-jaise dikha, likha</small></div>
        <div class="sk-notes-bd" id="skNotesBody"><span class="sk-watching">Video dekh rahi hoon…</span></div>
      </div></section>`;
  }

  function memoryCard() {
    if (!JOB || !JOB.done || JOB.error) return '';
    const r = JOB.result || {};
    const steps = (r.steps || []).map(s => `<li><span class="sk-n">${esc(s.n)}</span><span class="sk-act">${esc(s.action)}</span>
        <span class="sk-note">${esc(s.note || s.value_hint || '')}</span>
        ${(s.evidence || []).map(e => `<span class="sk-ev">@${esc(e)}</span>`).join('')}</li>`).join('');
    const chips = (r.preconditions || []).map(x => `<span class="sk-chip">pehle: ${esc(x)}</span>`).join('')
      + (r.gotchas || []).map(x => `<span class="sk-chip warn">dhyan: ${esc(x)}</span>`).join('')
      + (r.unsure || []).map(x => `<span class="sk-chip v">nahi dikha: ${esc(x)}</span>`).join('');
    return `<section class="tile gl sk-card sk-mem" id="skMem" aria-labelledby="skMemH">
      <h3 id="skMemH"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.4 5.6L20 11l-5.6 2.4L12 19l-2.4-5.6L4 11l5.6-2.4z"/></svg>Memory taiyar hai</h3>
      <div class="sk-mem-hd"><b class="sk-title">${esc(r.learned || '')}</b>
        <span class="sk-badges">${tag(r.kind === 'website_work' ? 'ok' : 'v', r.kind === 'website_work' ? (r.site ? 'Website ka kaam · ' + r.site : 'Website ka kaam') : 'Doosra kaam')}
        ${r.recipe ? tag('ok', 'Browser recipe (draft)') : ''}${tag('warn', 'Seekha hai - saabit nahi')}</span></div>
      <ol class="sk-msteps">${steps}</ol>
      ${chips ? `<div class="sk-chips">${chips}</div>` : ''}
      <div class="sk-conf"><span>Bharosa</span><i class="sk-bar"><b style="width:${pct(r.confidence)}%"></b></i><span>${pct(r.confidence)}%</span></div>
      <p class="muted sk-small">${esc(r.say || '')}${r.note_for_you ? ' ' + esc(r.note_for_you.split('.')[0]) + '.' : ''}</p>
      <div class="sk-btnrow"><button type="button" class="btn go" id="skToPerform">Perform this task NOW ↓</button></div>
      <p class="muted sk-small sk-src">source: ${esc(r.source || '')}${r.procedure_id ? ' · procedure ' + esc(r.procedure_id) : ''}${r.recipe ? ' · recipe "' + esc(r.recipe) + '"' : ''}</p>
    </section>`;
  }

  function performCard() {
    const r = (JOB && JOB.done && !JOB.error && JOB.result) || null;
    const kaam = PERFORM || (r && r.learned) || (LIST && LIST.watches && LIST.watches[0] && LIST.watches[0].title) || '';
    const hints = r && (r.steps || []).filter(s => s.value_hint).map(s => esc(s.value_hint)).filter(Boolean);
    return `<section class="tile gl sk-card" id="skPerform" aria-labelledby="skPerfH">
      <h3 id="skPerfH"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4M7 10l2 2 4-4"/></svg>Perform this task NOW</h3>
      ${kaam ? `<p class="sk-aim">Kaam: <b>${esc(kaam)}</b></p>` : '<p class="muted sk-small">Pehle ek video se kaam seekhaye, phir yahan se usko bulayein.</p>'}
      <label class="sk-field"><span>Kya karna hai? <small class="muted">(jo values bharni hain woh likh dijiye)</small></span>
        <textarea id="skAsk" rows="3" placeholder="Jaise: mera form bhar do - naam Ramesh Kumar, gaon Sitapur, class 10… jo video mein dikha tha wahi kaam." style="${IN}resize:vertical"></textarea></label>
      ${hints && hints.length ? `<div class="sk-chips">${hints.map(h => `<span class="sk-chip">bharna hai: ${h}</span>`).join('')}</div>` : ''}
      <div class="sk-btnrow">
        <button type="button" class="btn go" id="skGo"${kaam ? '' : ' disabled'}>Perform NOW - Hoola ke browser se</button>
        <span class="muted sk-small">Hoola apne browser mein karega; bhejne / submit karne se pehle aapse poochhega.</span>
      </div>
      <div class="sk-sent" id="skSent" hidden>
        <b>Kaam Hoola ko de diya.</b> Woh apne browser mein shuru karega - Live mein har step dikhega, aur jahan kuch bhejna ho wahan aapka tap lagega.
        <div class="sk-btnrow"><button type="button" class="btn soft" id="skLiveBtn">Live activity dekhiye</button>
          <button type="button" class="btn soft" id="skChatBtn">Chat kholiye</button></div>
      </div></section>`;
  }

  function listCard() {
    const rows = (LIST && LIST.watches) || [];
    return `<section class="tile gl sk-card" aria-labelledby="skListH">
      <h3 id="skListH"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5V6a2 2 0 0 1 2-2h6v16H6a2 2 0 0 0-2 1.5zM12 4h6a2 2 0 0 1 2 2v13.5H12"/></svg>Seekhe hue kaam <span class="muted sk-small">(${(LIST && LIST.total) || 0})</span></h3>
      ${rows.length ? `<div class="sk-list">${rows.map(w => `
        <div class="sk-row">
          <div class="sk-row-bd"><b>${esc(w.title || w.source || 'Kaam')}</b>
            <small>${esc(when(w.ts))} · ${esc(w.steps || 0)} steps · bharosa ${pct(w.confidence)}%${w.recipe ? ' · ' + esc(w.recipe) : ''}</small>
            <small class="muted">${esc(w.source || '')}</small></div>
          <button type="button" class="btn soft sk-perform" data-title="${esc(w.title || '')}">Perform</button>
        </div>`).join('')}</div>`
        : '<p class="muted sk-small">Abhi kuch nahi seekha. Pehla video upar dijiye.</p>'}
    </section>`;
  }

  // ------------------------------------------------------------ wiring
  function wire() {
    const q = s => EL.querySelector(s);
    q('#skWatch')?.addEventListener('click', start);
    q('#skPick')?.addEventListener('click', () => q('#skFile')?.click());
    q('#skFile')?.addEventListener('change', async e => {
      const f = e.target.files && e.target.files[0]; e.target.value = '';
      if (!f) return;
      if (f.size > 25 * 1024 * 1024) return toast(`${f.name}: 25 MB se badi file yahan nahi jaati - video ka link dijiye.`, true);
      const btn = q('#skPick'); const was = btn.textContent;
      btn.disabled = true; btn.textContent = 'Upload ho raha hai…';
      try {
        const r = await upload(f);
        q('#skRef').value = r.file_id || '';
        toast('Video upload ho gaya - ab Watch & Learn dabaiye.');
      } catch (er) { toast(`${f.name}: ${er.message || 'upload fail'}`, true); }
      btn.disabled = false; btn.textContent = was;
    });
    q('#skRef')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); start(); } });
    q('#skToPerform')?.addEventListener('click', () => { const p = q('#skPerform'); p?.scrollIntoView({behavior: 'smooth', block: 'center'}); q('#skAsk')?.focus(); });
    q('#skGo')?.addEventListener('click', perform);
    q('#skLiveBtn')?.addEventListener('click', () => live());
    q('#skChatBtn')?.addEventListener('click', () => open('chat'));
    EL.querySelectorAll('.sk-perform').forEach(b => b.addEventListener('click', () => {
      PERFORM = b.dataset.title || '';
      const p = q('#skPerform'); p?.scrollIntoView({behavior: 'smooth', block: 'center'});
      const aim = q('.sk-aim'); if (aim) aim.innerHTML = `Kaam: <b>${esc(PERFORM)}</b>`;
      const go = q('#skGo'); if (go) go.disabled = !PERFORM;
      q('#skAsk')?.focus();
    }));
  }

  // ------------------------------------------------------------ the watch job
  async function start() {
    const ref = String(EL.querySelector('#skRef')?.value || '').trim();
    const title = String(EL.querySelector('#skTitle')?.value || '').trim();
    if (!ref) return toast('Kaunsa video? Link dijiye ya file chuniye.', true);
    const btn = EL.querySelector('#skWatch'); btn.disabled = true; btn.textContent = 'Shuru…';
    try {
      const r = await api('POST', '/api/seekh/console/watch', {video: ref, title});
      if (r.already_running) toast('Ek video pehle se chal raha hai - wahi dikh raha hoon.');
      else toast('Hoola video dekhne lagi - notes yahin aayenge.');
      JOB = {id: r.id, stage: 'queue', stages: [], perception: '', done: false};
      NOTES_AT = 0;
      qLive(true); drawLive(); startPoll();
    } catch (e) {
      toast(e.message || 'Shuru nahi ho paya', true);
    }
    btn.disabled = false; btn.textContent = 'Watch & Learn';
  }

  function qLive(on) { const c = EL && EL.querySelector('#skLive'); if (c) c.hidden = !on; }

  function drawLive() {                                   // the live card only (re-drawn on state flips)
    if (!EL) return;
    const live = EL.querySelector('#skLive'); if (!live || live.hidden) return;
    const cur = stepOf(JOB && JOB.stage);
    EL.querySelectorAll('.sk-step').forEach((li, i) => {
      li.classList.toggle('on', i === cur && !(JOB && JOB.done));
      li.classList.toggle('did', i < cur || (JOB && JOB.done && !JOB.error));
      const em = li.querySelector('em');
      const hit = ((JOB && JOB.stages) || []).find(s => s.k === STEPS[i][0] || (STEPS[i][0] === 'distill' && s.k === 'distill_start'));
      if (em) em.textContent = hit ? mmss(hit.ts) : (li.classList.contains('on') ? '…' : '');
    });
    const el = EL.querySelector('#skElapsed');
    if (el) el.textContent = (JOB && JOB.done) ? `· poora hua ${mmss(JOB.elapsed)} mein` : `· ${mmss((JOB && JOB.elapsed) || 0)}`;
  }

  function startPoll() {
    stopPoll();
    TIMER = setInterval(poll, 1200);
    poll();
  }
  function stopPoll() { if (TIMER) { clearInterval(TIMER); TIMER = null; } }

  async function poll() {
    if (!JOB || JOB.done) { stopPoll(); return; }
    try {
      const r = await api('GET', `/api/seekh/console/progress?id=${encodeURIComponent(JOB.id || '')}`);
      const wasNotes = atStage('notes') >= 0;
      JOB = {...JOB, ...r};
      qLive(true);
      drawLive();
      if (!wasNotes && atStage('notes') >= 0) startPacer();
      if (r.done && !r.error) {
        stopPacer(); NOTES_AT = Infinity; renderNotes();
        PERFORM = (r.result && r.result.learned) || PERFORM;
        stopPoll();
        await refresh();
        if (EL && EL.isConnected) { draw(); EL.querySelector('#skMem')?.scrollIntoView({behavior: 'smooth', block: 'center'}); }
      } else if (r.done && r.error) {
        stopPacer(); stopPoll();
        const body = EL.querySelector('#skNotesBody');
        if (body) body.innerHTML = `<span class="sk-err">${esc(r.error)}</span>`;
        toast(r.error, true);
      }
    } catch (e) {
      if (e.status === 404) {                             // restart took the job; the memory keeps what landed
        stopPoll(); stopPacer(); JOB = null;
        await refresh(); if (EL && EL.isConnected) draw();
        toast('Yeh watch restart mein chhoot gaya - jo seekha tha woh memory mein hai.', true);
      }
    }
  }

  // ------------------------------------------------------------ the realtime notes (a paced reveal of the REAL text)
  function startPacer() {
    stopPacer();
    const total = (JOB.perception || '').length;
    if (!total) { renderNotes(); return; }
    const step = Math.max(9, Math.ceil(total / 110));      // ~110 ticks ≈ 10 s, any length
    PACER = setInterval(() => {
      NOTES_AT = Math.min(total, NOTES_AT + step);
      renderNotes();
      if (NOTES_AT >= total) stopPacer();
    }, 90);
  }
  function stopPacer() { if (PACER) { clearInterval(PACER); PACER = null; } }

  function renderNotes() {
    if (!EL) return;
    const body = EL.querySelector('#skNotesBody'); if (!body) return;
    if (JOB && JOB.error) return;                          // the error branch owns the box
    const txt = (JOB && JOB.perception) || '';
    if (!txt) return;                                      // still watching: keep the heartbeat line
    body.textContent = txt.slice(0, NOTES_AT === Infinity ? undefined : NOTES_AT);
    body.scrollTop = body.scrollHeight;
  }

  // ------------------------------------------------------------ perform NOW (one honest chat turn; the page stays)
  async function perform() {
    const r = (JOB && JOB.done && JOB.result) || null;
    const kaam = PERFORM || (r && r.learned) || '';
    if (!kaam) return toast('Pehle ek video se kaam seekhaye.', true);
    const ask = String(EL.querySelector('#skAsk')?.value || '').trim();
    const website = !!(r && r.kind === 'website_work');
    const msg = `Seekhe hue kaam "${kaam}" ab ek baar asli mein chala ke dekhna hai. ${ask || 'Jo video mein dikha tha, wahi kaam ab kijiye.'}`
      + (website
        ? ' Computer operator se kahiye: apne browser mein yeh kaam karein, video se bani recipe (draft) ko guide maanein, har step live page se check karein - jahan kuch bhi bhejna ya submit karna ho wahan pehle mujhse poochein. Jo cheez video mein nahi dikhi thi, wahan ruk kar pooch lein.'
        : ' Video se seekha hai, steps memory mein hain - har step aage badhne se pehle apne aap check karein, aur jahan kuch bhejna ya badalna ho wahan pehle mujhse poochein.');
    const btn = EL.querySelector('#skGo'); btn.disabled = true;
    try {
      await send(msg);
      const sent = EL.querySelector('#skSent'); if (sent) sent.hidden = false;
      EL.querySelector('#skAsk').value = '';
      toast('Kaam Hoola ko de diya - Live mein dekhiye.');
    } catch (e) {
      toast('Nahi bhej paya: ' + (e.message || ''), true);
      btn.disabled = false;
    }
  }

  return {open};
};
