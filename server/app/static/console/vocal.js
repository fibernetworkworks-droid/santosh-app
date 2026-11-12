/* v0.787 HOOLA VOCAL - the voice studio as its own full page with its own sidebar (owner: "HOOLA VOCAL ... same 11labs
   for hoola end to end"). Twelve pages: Home, Voices, Text to speech, Dialogue, Studio, Voice changer, Sound effects,
   Voice isolator, More tools, Dictionary, History, Settings. Everything stands on /api/vocal/* (vocal/service.py), which
   stands on Hoola's own engines. What this server cannot do is read from status.connected and SAID on the page - no
   control pretends. Same design system as Hoola Interactive (the shared block in v2.css). Her text is always esc()'d. */
window.HoolaVocal = function ({api, esc, toast, upload, back, go: consoleGo}) {
  const A = '/api/vocal';
  let ROOT = null, PAGE = 'home', ARG = '', D = null, NOW = null;
  const UI = {tab: {}, slim: null, voice: '', lang: 'hi', style: 'friendly', speed: 1, text: '', filter: 'All', hist: 'All',
    dlg: {lines: [{speaker: 'Asha', text: ''}, {speaker: 'Ravi', text: ''}], cast: {}}, seed: 1, proj: null};
  const URLS = new Map();
  const PAGES = [['home', 'Home', 'home'], ['voices', 'Voices', 'user'], ['tts', 'Text to speech', 'wave'], ['dialogue', 'Dialogue', 'chat'],
    ['studio', 'Studio', 'book'], ['changer', 'Voice changer', 'swap'], ['sfx', 'Sound effects', 'spark'], ['isolate', 'Voice isolator', 'filter'],
    ['more', 'More tools', 'apps'], ['dict', 'Dictionary', 'abc'], ['history', 'History', 'clock'], ['settings', 'Settings', 'gear']];
  const KIND = {tts: 'Speech', dialogue: 'Dialogue', chapter: 'Chapter', book: 'Reading', sfx: 'Effect', cleanup: 'Cleaned', music: 'Music'};
  const PATHS = {
    home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    wave: '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>',
    chat: '<path d="M4 5h11a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H9l-4 3v-3H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/><path d="M20 9v7h-1v3l-3-3"/>',
    book: '<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11M9 8h6"/>',
    swap: '<path d="M4 8h14M14 4l4 4-4 4M20 16H6M10 12l-4 4 4 4"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    apps: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><path d="M17.5 14v7M14 17.5h7"/>',
    abc: '<path d="M4 17l3.5-10L11 17M5.3 13.5h4.4M14 7v10M14 12.5a2.5 2.5 0 1 1 0 4.5M20 13a2.5 2.5 0 1 0 0 4"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', x: '<path d="M6 6l12 12M18 6L6 18"/>', arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 6l-6 6 6 6"/>', left: '<path d="M14.5 6l-6 6 6 6"/>', play: '<path d="M8 5.5v13l11-6.5z"/>', down: '<path d="M12 5v14M6 13l6 6 6-6"/>',
    side: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>', mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    lang: '<path d="M4 6h9M8.5 4v2M6 6c.6 3.6 3 6.4 6 7.6M11.5 6c-.7 3.8-3.4 6.8-7 8M13 20l4-9 4 9M14.4 17h5.2"/>', music: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
    film: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>', warn: '<path d="M12 4l9 15.5H3zM12 10v4.5M12 17.2v.1"/>'};
  const ic = n => `<svg class="hi-i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[n] || ''}</svg>`;
  const $ = s => ROOT && ROOT.querySelector(s);
  const $$ = s => ROOT ? [...ROOT.querySelectorAll(s)] : [];
  const q = encodeURIComponent;
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const secs = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  const con = () => D?.status?.connected || {};
  const langs = () => D?.langs || {hi: 'Hindi'};
  const TINT = ['#7C5CFF', '#F27A52', '#C055F5', '#2DB8A8', '#E0A23A'];
  const tint = id => TINT[[...String(id || '')].reduce((n, ch) => (n * 31 + ch.charCodeAt(0)) >>> 0, 7) % TINT.length];
  const opts = (o, on) => Object.entries(o).map(([k, n]) => `<option value="${esc(k)}"${k === on ? ' selected' : ''}>${esc(n)}</option>`).join('');
  const voiceOpts = on => { const g = {hoola: 'Hoola voices', clone: 'My voices', design: 'My voices'}, by = {};
    for (const v of D.voices) (by[g[v.kind]] ||= []).push(v);
    return Object.entries(by).map(([n, l]) => `<optgroup label="${n}">${l.map(v => `<option value="${esc(v.id)}"${v.id === on ? ' selected' : ''}${v.ready ? '' : ' disabled'}>${esc(v.name)}${v.tone ? ' - ' + esc(v.tone) : ''}</option>`).join('')}</optgroup>`).join('') || '<option value="">No voice on this server</option>'; };
  const pick = (id, label, inner, i) => `<label class="hi-pick">${i ? ic(i) : ''}<select id="${id}" aria-label="${label}">${inner}</select></label>`;
  const tabs = (id, names) => { const on = UI.tab[id] || names[0];
    return `<div class="hi-tabs" role="tablist">${names.map(n => `<button class="hi-tab" role="tab" aria-selected="${n === on}" data-a="tab" data-k="${id}" data-val="${esc(n)}">${esc(n)}</button>`).join('')}</div>`; };
  const cur = (id, d) => UI.tab[id] || d;
  const head = (h, p, btn = '') => `<div class="hi-head"><div><h1>${h}</h1>${p ? `<p>${p}</p>` : ''}</div>${btn}</div>`;
  const notYet = why => `<div class="hi-note warn"><b>Not connected on this server yet.</b> ${esc(why)}</div>`;
  const orb = (v, cls = '') => `<span class="hv-orb ${cls}" style="--t:${tint(v.id)}">${ic(v.kind === 'hoola' ? 'wave' : v.kind === 'clone' ? 'mic' : 'spark')}</span>`;
  const row = h => `<div class="hv-row"><button class="hi-btn q ico s" data-a="play" data-id="${esc(h.id)}" aria-label="Play ${esc(h.title)}" title="Play">${ic('play')}</button>
      <span class="hi-fill"><b>${esc(h.title || KIND[h.kind])}</b><br><span class="hi-sm hi-mut">${esc(h.voice_name || '')}${h.seconds ? ' · ' + secs(h.seconds) : ''} · ${esc(ago(h.made))}</span></span>
      <span class="hi-chip">${KIND[h.kind] || esc(h.kind)}</span><button class="hi-btn q ico s" data-a="dl" data-id="${esc(h.id)}" aria-label="Download" title="Download">${ic('down')}</button>
      <button class="hi-ib" data-a="rmh" data-id="${esc(h.id)}" aria-label="Remove" title="Remove">${ic('x')}</button></div>`;
  const recent = (kinds, n = 5, title = 'Latest') => { const l = D.history.filter(h => kinds.includes(h.kind)).slice(0, n);
    return l.length ? `<section class="hi-grid"><h2>${title}</h2><div class="hi-card hv-list">${l.map(row).join('')}</div></section>` : ''; };
  const engine = () => { const e = D.status?.engines || {};
    return D.error ? ['bad', D.error, 'Not loaded'] : e.speech && e.lab ? ['ok', 'Speech and your-own-voice engines are ready', 'Engines ready']
      : e.speech ? ['warn', 'Hoola voices are ready. Your own voices (clone, design) need the GPU voice engine, which is not connected', 'Hoola voices only']
      : e.lab ? ['warn', 'Your own voices are ready. Hoola\'s ready-made voices need the speech engine key', 'Own voices only']
      : ['bad', 'No speech engine is set up on this server yet - effects and clean-up still work', 'No speech engine']; };

  async function blobUrl(path) { if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true}); const u = URL.createObjectURL(await r.blob()); URLS.set(path, u); return u; }
  async function load() {
    try { D = await api('GET', `${A}/overview`); }
    catch (e) { D = {voices: [], rules: [], history: [], projects: [], usage: {}, langs: {hi: 'Hindi'}, styles: {friendly: 'Friendly'}, sfx: [], limits: {}, status: {engines: {}, connected: {}}, error: e.message}; }
    if (!D.voices.some(v => v.id === UI.voice && v.ready)) UI.voice = (D.voices.find(v => v.ready) || {}).id || '';
  }
  async function play(id, src, title) {
    try { const u = src || await blobUrl(`${A}/audio?id=${q(id)}`); const h = D.history.find(x => x.id === id);
      NOW = {id, title: title || h?.title || 'Sound'}; const bar = $('#hvBar'); bar.hidden = false;
      $('#hvNow').textContent = NOW.title; const a = $('#hvAudio'); a.src = u; await a.play().catch(() => {}); }
    catch (e) { toast(e.message || 'That sound could not be played.', true); }
  }
  async function download(id) { const h = D.history.find(x => x.id === id);
    try { const a = document.createElement('a'); a.href = await blobUrl(`${A}/audio?id=${q(id)}`);
      a.download = `${(h?.title || 'hoola-vocal').replace(/[^\w .-]+/g, '_').slice(0, 60)}.${h?.ext || 'wav'}`; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); } }

  // ------------------------------------------------------------------ shell ---
  function mount() {
    if (ROOT) { ROOT.hidden = false; return; }
    ROOT = document.createElement('div'); ROOT.id = 'hvRoot';
    ROOT.setAttribute('role', 'application'); ROOT.setAttribute('aria-label', 'Hoola Vocal');
    ROOT.innerHTML = `<nav class="hi-rail" id="hvRail" aria-label="Hoola Vocal pages"></nav>
      <div class="hi-main hv-main"><main class="hi-view" id="hvView"></main>
        <div class="hv-bar" id="hvBar" hidden><span class="hv-orb s" style="--t:#7C5CFF">${ic('wave')}</span><b id="hvNow" class="hi-fill"></b><audio id="hvAudio" controls preload="none"></audio>
          <button class="hi-ib" data-a="closebar" aria-label="Close the player">${ic('x')}</button></div></div>`;
    document.body.appendChild(ROOT);
    ROOT.addEventListener('click', onClick); ROOT.addEventListener('input', onInput);
    ROOT.addEventListener('change', onChange); ROOT.addEventListener('submit', onSubmit);
  }
  async function open() { mount(); await load(); go(PAGE, ARG); }
  function leave() { if (ROOT) { $('#hvAudio')?.pause(); ROOT.hidden = true; } }
  function rail() {
    const on = {reading: 'studio'}[PAGE] || PAGE, [ec, et, es] = engine(), slim = UI.slim ?? false;
    ROOT.dataset.slim = slim ? 1 : 0;
    $('#hvRail').innerHTML = `<div class="hi-rhead"><button class="hi-mark" data-a="go" data-p="home" title="Hoola Vocal home"><i>${ic('wave')}</i><span>Hoola<small>Vocal</small></span></button>
        <button class="hi-ib" data-a="slim" aria-label="${slim ? 'Open' : 'Fold'} the sidebar" title="${slim ? 'Open' : 'Fold'} the sidebar">${ic('side')}</button></div>
      <button class="hi-new" data-a="go" data-p="tts" aria-label="Create speech" title="Create speech">${ic('plus')}<span>Create speech</span></button>` +
      PAGES.map(([id, n, i], k) => `${k === 9 ? '<hr>' : ''}<button class="hi-rb" data-a="go" data-p="${id}" title="${n}"${id === on ? ' aria-current="page"' : ''}><span class="hi-tile">${ic(i)}</span><span class="hi-rl">${n}</span></button>`).join('') +
      `<span class="hi-sp"></span><button class="hi-rs ${ec}" data-a="go" data-p="settings" data-arg="Engines" aria-label="${esc(et)}" title="${esc(et)}"><i></i><span class="hi-rl">${es}</span></button>
       <button class="hi-rb" data-a="back" title="Back to the Hoola console"><span class="hi-tile">${ic('back')}</span><span class="hi-rl">Back to console</span></button>`;
  }
  const flash = (cls, ms) => { const v = $('#hvView'); if (!v) return; v.classList.remove('hi-in', 'hi-tabin'); void v.offsetWidth; v.classList.add(cls);
    clearTimeout(flash.t); flash.t = setTimeout(() => v.classList.remove(cls), ms); };
  function go(page, arg) { keep(); PAGE = V[page] ? page : 'home'; ARG = arg || ''; rail(); draw(); flash('hi-in', 900); $('#hvView').scrollTop = 0; }
  function draw() { $('#hvView').innerHTML = V[PAGE](); }
  async function act(fn, done, btn, txt) {
    const was = btn?.innerHTML; if (btn) { btn.disabled = true; if (txt) btn.textContent = txt; }
    try { const r = await fn(); await load(); if (done) done(r); else { rail(); draw(); } }
    catch (e) { toast(e.message || 'That did not work.', true); if (btn?.isConnected) { btn.disabled = false; btn.innerHTML = was; } }
  }
  function keep() {                                   // what she typed survives a redraw
    if (!ROOT) return;
    const v = id => $(id)?.value;
    if (PAGE === 'tts' && $('#hvText')) Object.assign(UI, {text: v('#hvText'), voice: v('#hvVoice') || UI.voice, lang: v('#hvLang') || UI.lang, style: v('#hvStyle') || UI.style, speed: +v('#hvSpeed') || 1});
    if (PAGE === 'dialogue' && $('[data-dl]')) { UI.dlg.lines = $$('[data-dl]').map(t => ({speaker: ($(`[data-ds="${t.dataset.dl}"]`)?.value || 'Speaker').trim(), text: t.value}));
      for (const s of $$('[data-cast]')) UI.dlg.cast[s.dataset.cast] = s.value; UI.lang = v('#hvDLang') || UI.lang; }
    if (PAGE === 'reading' && UI.proj && $('#hvPTitle')) Object.assign(UI.proj, {title: v('#hvPTitle'), voice: v('#hvPVoice'), lang: v('#hvPLang'),
      chapters: $$('[data-ct]').map((t, n) => ({...(UI.proj.chapters[n] || {}), title: $(`[data-cn="${n}"]`)?.value || '', text: t.value}))});
  }

  // ------------------------------------------------------------------ pages ---
  const V = {
    home() {
      const c = con(), u = D.usage || {}, [ec, et] = engine();
      const tile = (i, t, d, p, ok = true) => `<button class="hi-flow" data-a="go" data-p="${p}"><span class="hi-ftop"><span class="ic">${ic(i)}</span>${ok ? `<span class="arr">${ic('arrow')}</span>` : '<span class="hi-chip">Not connected yet</span>'}</span><h3>${t}</h3><span class="hi-mut hi-sm">${d}</span></button>`;
      return `<div class="hi-wrap"><section class="hi-hero"><span class="hi-eye"><i></i>Hoola Vocal</span><h1>What should Hoola say?</h1>
        <form class="hi-ask" data-f="quick"><label class="hi-sm hi-mut" for="hvQuick">Type the words</label>
          <textarea id="hvQuick" rows="2" maxlength="5000" placeholder="e.g. Welcome to Sharma Traders. We are open from nine this morning."></textarea>
          <div class="hi-askrow">${pick('hvQVoice', 'Voice', voiceOpts(UI.voice), 'user')}${pick('hvQLang', 'Language', opts(langs(), UI.lang), 'lang')}
            <span class="hi-fill"></span><button class="hi-btn lg"${c.tts ? '' : ' disabled'}>${ic('play')}Speak it</button></div></form></section>
        <div class="hi-strap ${ec}"><i></i><span class="hi-fill">${esc(et)}</span><button class="hi-link" data-a="go" data-p="settings" data-arg="Engines">See engines</button></div>
        <section class="hi-grid"><h2>Everything in the studio</h2><div class="hi-grid hi-g3">
          ${tile('wave', 'Text to speech', 'Words in, a natural voice out, in eleven Indian languages.', 'tts', c.tts)}${tile('user', 'Voices', `${D.hoola_voices || 0} Hoola voices, and your own.`, 'voices')}
          ${tile('chat', 'Dialogue', 'Two or more speakers, each in their own voice, in one file.', 'dialogue', c.dialogue)}${tile('book', 'Studio', 'Long readings in chapters: stories, lessons, audiobooks.', 'studio', c.studio)}
          ${tile('mic', 'Clone my voice', 'From a short recording, with your yes.', 'voices', c.clone)}${tile('spark', 'Sound effects', 'Short sounds for videos, games and apps.', 'sfx')}
          ${tile('filter', 'Voice isolator', 'Clean a noisy recording.', 'isolate', c.cleanup)}${tile('abc', 'Dictionary', 'How your names and words must be said.', 'dict')}</div></section>
        <section class="hi-cols"><div class="hi-card hi-grid"><div class="hi-sh"><h3>This month</h3><button class="hi-btn q s" data-a="go" data-p="settings">Usage</button></div>
            <div class="hi-stats"><div class="hi-stat"><b>${(u.characters || 0).toLocaleString('en-IN')}</b><span class="hi-sm hi-mut">characters spoken</span></div>
              <div class="hi-stat"><b>${u.minutes || 0}</b><span class="hi-sm hi-mut">minutes of sound</span></div><div class="hi-stat"><b>${u.kept || 0} / ${u.kept_max || 200}</b><span class="hi-sm hi-mut">kept on this server</span></div></div>
            <div class="hi-bar"><i style="width:${Math.min(100, (u.kept || 0) / (u.kept_max || 200) * 100)}%"></i></div><p class="hi-sm hi-mut">Counted from your own results. There is no rupee meter yet.</p></div>
          <div class="hi-card hi-grid"><div class="hi-sh"><h3>My voices</h3><button class="hi-btn q s" data-a="go" data-p="voices" data-arg="My voices">Open</button></div>
            ${D.voices.filter(v => v.kind !== 'hoola').slice(0, 3).map(v => `<div class="hi-row nw">${orb(v)}<span class="hi-fill"><b>${esc(v.name)}</b><br><span class="hi-sm hi-mut">${v.kind === 'clone' ? 'From your recording' : 'Described voice'}</span></span></div>`).join('')
              || '<p class="hi-mut">None yet. Record 30 to 60 seconds, or describe a voice in words.</p>'}</div></section>
        ${recent(Object.keys(KIND), 6, 'Recent') || '<div class="hi-empty"><b>Nothing made yet</b>Type a line above and press Speak it.</div>'}</div>`;
    },

    voices() {
      if (ARG) { UI.tab.vo = ARG; ARG = ''; }
      const t = cur('vo', 'Library'), c = con(), f = UI.filter;
      const card = v => `<div class="hi-av hov hv-voice">${orb(v, 'l')}<span><b>${esc(v.name)}</b><br><span class="hi-sm hi-mut">${esc(v.tone || '')}</span></span>
          <span class="hi-row" style="gap:6px">${v.gender ? `<span class="hi-chip">${v.gender === 'female' ? 'Female' : 'Male'}</span>` : ''}${v.kind === 'clone' ? '<span class="hi-chip ok">Consent given</span>' : v.kind === 'design' ? '<span class="hi-chip pri">Described</span>' : ''}</span>
          <span class="hi-row" style="gap:6px"><button class="hi-btn q s" data-a="hear" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}>${ic('play')}Hear</button><button class="hi-btn s" data-a="usev" data-id="${esc(v.id)}"${v.ready ? '' : ' disabled'}>Use</button>
            ${v.kind !== 'hoola' ? `<button class="hi-btn danger s" data-a="rmv" data-id="${esc(v.id)}">Remove</button>` : ''}</span></div>`;
      const lib = D.voices.filter(v => v.kind === 'hoola' && (f === 'All' || v.gender === f.toLowerCase())), mine = D.voices.filter(v => v.kind !== 'hoola');
      return `<div class="hi-wrap">${head('Voices', 'Hoola\'s ready voices, and the ones you make. Every recorded voice needs a yes.', `<button class="hi-btn" data-a="tab" data-k="vo" data-val="Clone a voice">${ic('plus')}Add a voice</button>`)}
        ${tabs('vo', ['Library', 'My voices', 'Clone a voice', 'Design a voice'])}
        ${t === 'Library' ? (c.library ? `<div class="hi-row">${['All', 'Female', 'Male'].map(x => `<button class="hi-sel" aria-pressed="${x === f}" data-a="filter" data-val="${x}">${x}</button>`).join('')}</div><div class="hi-grid hi-g4">${lib.map(card).join('')}</div>`
            : notYet('Hoola\'s ready-made voices need the speech engine key (GEMINI_API_KEY) on this server.'))
        : t === 'My voices' ? (mine.length ? `${c.clone ? '' : notYet('Your voices are saved, but speaking in them needs the GPU voice engine.')}<div class="hi-grid hi-g4">${mine.map(card).join('')}</div>`
            : `<div class="hi-empty"><b>No voices of your own yet</b>Record yourself, or describe a voice in words.<div class="hi-row"><button class="hi-btn" data-a="tab" data-k="vo" data-val="Clone a voice">Clone a voice</button><button class="hi-btn q" data-a="tab" data-k="vo" data-val="Design a voice">Design a voice</button></div></div>`)
        : t === 'Clone a voice' ? `<div class="hi-cols"><form class="hi-card hi-grid" data-f="clone"><h3>Instant clone</h3>${c.clone ? '' : notYet('The voice is saved with its consent, but it can speak only once the GPU voice engine is connected.')}
              <label class="hi-f">Name<input id="hvCName" maxlength="40" required placeholder="e.g. My voice"></label>
              <label class="hi-f">Recording, 30 to 60 seconds, one person, quiet room (wav, mp3, m4a - up to ${D.limits?.sample_mb || 2} MB)<input id="hvCFile" type="file" accept="audio/*" required></label>
              <label class="hi-f">Language spoken<select id="hvCLang">${opts(langs(), 'hi')}</select></label>
              <label class="hi-check"><input type="checkbox" id="hvCOk" required><span>This is my own voice, or the person speaking agreed to this</span></label>
              <button class="hi-btn hi-start">Add the voice</button><p class="hi-sm hi-mut">Not accepted: anyone under 18, public figures, or a person who has not agreed. Removing a voice deletes its recording.</p></form>
            <div class="hi-card hi-grid"><h3>Professional clone</h3><p class="hi-mut">Thirty minutes or more of your speech, trained into a voice that is hard to tell from you.</p>${notYet('It needs a training run on the GPU and a spoken-consent check. Neither is built.')}</div></div>`
        : `<div class="hi-cols"><form class="hi-card hi-grid" data-f="design"><h3>Describe a voice</h3>${c.design ? '' : notYet('The description is saved, but it can speak only once the GPU voice engine is connected.')}
              <label class="hi-f">Name<input id="hvDName" maxlength="40" required placeholder="e.g. Dadi"></label>
              <label class="hi-f">What the voice is like<textarea id="hvDDesc" rows="4" maxlength="300" required placeholder="An older woman with a warm, slow voice, telling a bedtime story in a quiet room."></textarea></label>
              <label class="hi-f">Gender<select id="hvDGender"><option value="">Not set</option><option value="female">Female</option><option value="male">Male</option></select></label>
              <button class="hi-btn hi-start">Save the voice</button></form>
            <div class="hi-card hi-grid"><h3>What works</h3><ol class="hi-steps"><li class="hi-step"><span class="n">1</span>Who is speaking: age, and whether a man or a woman</li><li class="hi-step"><span class="n">2</span>The tone: warm, firm, cheerful, calm</li><li class="hi-step"><span class="n">3</span>The pace and the room: slow, quick, close to the microphone</li></ol>
              <p class="hi-sm hi-mut">Describe the voice itself. Hoola does not imitate a named person.</p></div></div>`}</div>`;
    },

    tts() {
      const c = con(), lim = D.limits?.characters || 40000, n = (UI.text || '').length;
      return `<div class="hi-wrap">${head('Text to speech', 'Type or paste the words. Long text is cut at sentence ends and joined for you.')}
        ${c.tts ? '' : notYet('No speech engine is set up on this server.')}
        <form class="hv-two" data-f="tts"><div class="hi-card hv-write"><textarea id="hvText" aria-label="Words to speak" maxlength="${lim}" placeholder="Start typing here, or paste your script…">${esc(UI.text)}</textarea>
            <div class="hi-row"><span class="hi-sm hi-mut hi-num" id="hvCount">${n.toLocaleString('en-IN')} / ${lim.toLocaleString('en-IN')} characters</span><span class="hi-fill"></span>
              <button class="hi-btn lg"${c.tts ? '' : ' disabled'}>${ic('play')}Generate speech</button></div></div>
          <aside class="hi-card hi-grid"><h3>Settings</h3><label class="hi-f">Voice<select id="hvVoice">${voiceOpts(UI.voice)}</select></label>
            <label class="hi-f">Language<select id="hvLang">${opts(langs(), UI.lang)}</select></label><label class="hi-f">Style<select id="hvStyle">${opts(D.styles || {}, UI.style)}</select></label>
            <label class="hi-f">Speed <span class="hi-num" id="hvSpeedV">${(+UI.speed).toFixed(2)}x</span><input type="range" id="hvSpeed" min="0.8" max="1.3" step="0.05" value="${UI.speed}"></label>
            <label class="hi-check"><input type="checkbox" id="hvRules" checked><span>Use my dictionary (${D.rules.length} word${D.rules.length === 1 ? '' : 's'})</span></label>
            <p class="hi-sm hi-mut">Style and speed apply to Hoola voices. Your own voices keep the way they were recorded or described.</p></aside></form>
        ${recent(['tts'])}</div>`;
    },

    dialogue() {
      const c = con(), L = UI.dlg.lines, who = [...new Set(L.map(l => (l.speaker || 'Speaker').trim() || 'Speaker'))];
      const able = D.voices.filter(v => v.ready); who.forEach((w, i) => { if (!UI.dlg.cast[w] && able.length) UI.dlg.cast[w] = able[i % able.length].id; });   // each new speaker starts on a different voice
      return `<div class="hi-wrap">${head('Dialogue', 'Several speakers in one file. Give each speaker a voice.')}${c.dialogue ? '' : notYet('No speech engine is set up on this server.')}
        <form class="hv-two" data-f="dialogue"><div class="hi-grid">${L.map((l, n) => `<div class="hi-scene"><div class="hd"><span class="hi-sn">${n + 1}</span>
              <input class="hv-who" data-ds="${n}" value="${esc(l.speaker)}" maxlength="30" aria-label="Speaker of line ${n + 1}" list="hvWho"><span class="hi-fill"></span>
              <button type="button" class="hi-ib" data-a="dlrm" data-n="${n}" aria-label="Remove line ${n + 1}"${L.length > 1 ? '' : ' disabled'}>${ic('x')}</button></div>
              <textarea data-dl="${n}" aria-label="Line ${n + 1}" maxlength="1500" placeholder="What this speaker says">${esc(l.text)}</textarea></div>`).join('')}
            <datalist id="hvWho">${who.map(w => `<option value="${esc(w)}">`).join('')}</datalist>
            ${L.length < (D.limits?.lines || 40) ? `<button type="button" class="hi-add" data-a="dladd">${ic('plus')}Add a line</button>` : ''}</div>
          <aside class="hi-card hi-grid"><h3>Cast</h3>${who.map(w => `<label class="hi-f">${esc(w)}<select data-cast="${esc(w)}">${voiceOpts(UI.dlg.cast[w] || '')}</select></label>`).join('')}
            <label class="hi-f">Language<select id="hvDLang">${opts(langs(), UI.lang)}</select></label>
            <button class="hi-btn"${c.dialogue ? '' : ' disabled'}>${ic('play')}Generate dialogue</button>
            <p class="hi-sm hi-mut">Use Hoola voices together, or your own voices together. The two kinds cannot be joined in one file.</p></aside></form>
        ${recent(['dialogue'])}</div>`;
    },

    studio() {
      return `<div class="hi-wrap">${head('Studio', 'Long readings in chapters: stories, lessons, audiobooks.', `<button class="hi-btn" data-a="newproj">${ic('plus')}New reading</button>`)}
        ${D.projects.length ? `<div class="hi-grid hi-g3">${D.projects.map(p => { const done = p.chapters.filter(c => c.audio).length;
            return `<button class="hi-av" data-a="proj" data-id="${esc(p.id)}"><span class="hi-thumb" style="--t:${tint(p.id)}"><span class="cnt hi-num">${p.chapters.length} chapter${p.chapters.length === 1 ? '' : 's'}</span><span class="cap">${esc(p.title)}</span></span>
              <span class="hi-row nw" style="justify-content:space-between"><span class="hi-sm hi-mut">${esc(langs()[p.lang] || p.lang)} · ${esc(ago(p.updated || p.made))}</span><span class="hi-chip ${done && done === p.chapters.length ? 'ok' : ''}">${done} of ${p.chapters.length} read</span></span></button>`; }).join('')}</div>`
          : `<div class="hi-empty"><b>No readings yet</b>Paste a story or a lesson, split it into chapters, and Hoola reads each one.<button class="hi-btn" data-a="newproj">New reading</button></div>`}</div>`;
    },

    reading() {
      const p = UI.proj; if (!p) return V.studio();
      const c = con(), all = p.chapters.length && p.chapters.every(x => x.audio);
      return `<div class="hi-wrap"><div class="hi-edhead"><button class="hi-btn q ico" data-a="go" data-p="studio" aria-label="Back to Studio" title="Back to Studio">${ic('left')}</button>
          <input id="hvPTitle" class="hi-title" aria-label="Title" value="${esc(p.title || '')}" maxlength="80" placeholder="Title of the reading">
          ${p.id ? `<button class="hi-btn danger" data-a="rmproj" data-id="${esc(p.id)}">Remove</button>` : ''}<button class="hi-btn q" data-a="saveproj">Save</button>
          <button class="hi-btn" data-a="export"${all ? '' : ' disabled'} title="${all ? 'Join every chapter into one file' : 'Read every chapter first'}">${ic('down')}Export as one file</button></div>
        ${c.studio ? '' : notYet('No speech engine is set up on this server. You can write and save; reading needs the engine.')}
        <div class="hv-two"><div class="hi-grid">${p.chapters.map((ch, n) => `<div class="hi-scene"><div class="hd"><span class="hi-sn">${n + 1}</span><input class="hv-who" data-cn="${n}" value="${esc(ch.title || '')}" maxlength="80" aria-label="Chapter ${n + 1} title" placeholder="Chapter title"><span class="hi-fill"></span>
                ${ch.audio ? `<button type="button" class="hi-btn q s" data-a="play" data-id="${esc(ch.audio)}">${ic('play')}${secs(ch.seconds)}</button>` : ''}
                <button type="button" class="hi-btn s" data-a="readch" data-n="${n}"${c.studio ? '' : ' disabled'}>${ch.audio ? 'Read again' : 'Read'}</button>
                <button type="button" class="hi-ib" data-a="chrm" data-n="${n}" aria-label="Remove chapter ${n + 1}"${p.chapters.length > 1 ? '' : ' disabled'}>${ic('x')}</button></div>
              <textarea data-ct="${n}" aria-label="Chapter ${n + 1} words" style="min-height:140px" maxlength="${D.limits?.characters || 40000}" placeholder="The words of this chapter">${esc(ch.text || '')}</textarea>
              <div class="ft"><span class="hi-chip ${ch.audio ? 'ok' : ''}">${ch.audio ? 'Read' : 'Not read yet'}</span><span class="hi-sm hi-dim hi-num">${(ch.text || '').length.toLocaleString('en-IN')} characters</span></div></div>`).join('')}
            <button type="button" class="hi-add" data-a="chadd">${ic('plus')}Add a chapter</button></div>
          <aside class="hi-card hi-grid"><h3>Reading voice</h3><label class="hi-f">Voice<select id="hvPVoice">${voiceOpts(p.voice || UI.voice)}</select></label>
            <label class="hi-f">Language<select id="hvPLang">${opts(langs(), p.lang || 'hi')}</select></label>
            <p class="hi-sm hi-mut">Each chapter is read on its own, so you can fix one without redoing the rest. A chapter whose words change must be read again.</p></aside></div></div>`;
    },

    changer() {
      return `<div class="hi-wrap narrow">${head('Voice changer', 'Speak in your own voice and hear it back in another, with the same feeling and timing.')}
        ${notYet('Changing one voice into another while keeping the acting needs a speech-to-speech model. Hoola has none connected, so nothing here can run.')}
        <div class="hi-card hi-grid"><h3>What works today instead</h3><ol class="hi-steps"><li class="hi-step"><span class="n">1</span>Type the words, and choose any voice in Text to speech</li>
            <li class="hi-step"><span class="n">2</span>For a recording you already have: get its words in Hoola Flow, then speak them here</li></ol>
          <p class="hi-sm hi-mut">That keeps the words but not the acting: the new voice reads them its own way.</p>
          <div class="hi-row"><button class="hi-btn" data-a="go" data-p="tts">Open Text to speech</button><a class="hi-btn q" href="/console/flow">Open Hoola Flow</a></div></div></div>`;
    },

    sfx() {
      return `<div class="hi-wrap">${head('Sound effects', 'Short sounds for videos, games and apps. Each is made by code, so the same choice always gives the same sound.')}
        <div class="hi-card hi-grid"><div class="hi-row"><label class="hi-f" style="width:140px">Variation<input type="number" id="hvSeed" min="1" max="9999" value="${UI.seed}"></label>
            <span class="hi-sm hi-mut hi-fill">Change the number for a different take of the same sound.</span></div>
          <div class="hv-pads">${(D.sfx || []).map(p => `<button class="hv-pad" data-a="sfx" data-p="${esc(p)}"><span class="hv-orb s" style="--t:${tint(p)}">${ic('spark')}</span>${esc(p.replace(/_/g, ' '))}</button>`).join('')}</div></div>
        <div class="hi-card hi-grid"><h3>Describe any sound</h3><p class="hi-mut">"Rain on a tin roof", "a busy market", "a door creaking open".</p>${notYet('Making a sound from a description needs a sound model. None is connected, so only the sounds above can be made.')}</div>
        ${recent(['sfx'], 6)}</div>`;
    },

    isolate() {
      const c = con();
      return `<div class="hi-wrap">${head('Voice isolator', 'Clean a noisy recording so the voice is easier to hear.')}
        <div class="hi-cols"><form class="hi-card hi-grid" data-f="cleanup"><h3>Clean a recording</h3>${c.cleanup ? '' : notYet('ffmpeg is not installed on this server.')}
            <label class="hi-f">Recording (any common sound or video file)<input id="hvIFile" type="file" accept="audio/*,video/*" required></label>
            <label class="hi-check"><input type="checkbox" id="hvI1" checked><span>Remove steady background noise (fan, hum, hiss)</span></label>
            <label class="hi-check"><input type="checkbox" id="hvI2" checked><span>Make the voice clearer</span></label>
            <label class="hi-check"><input type="checkbox" id="hvI3"><span>Cut long silences</span></label>
            <label class="hi-check"><input type="checkbox" id="hvI4" checked><span>Even out the loudness</span></label>
            <button class="hi-btn hi-start"${c.cleanup ? '' : ' disabled'}>Clean it</button></form>
          <div class="hi-card hi-grid"><h3>Lift a voice out of music</h3><p class="hi-mut">Take the singing or speech out of a song, or the music out from under a voice.</p>
            ${notYet('That needs a separation model. None is connected. Cleaning on the left uses sound filters: it reduces steady noise, it does not remove music or another person talking.')}</div></div>
        ${recent(['cleanup'])}</div>`;
    },

    more() {
      const c = con(), t = cur('mo', '');
      const card = (i, n, d, ok, act, lbl) => `<div class="hi-flow"><span class="hi-ftop"><span class="ic">${ic(i)}</span>${ok ? '<span class="hi-chip ok">Ready</span>' : '<span class="hi-chip">Not connected yet</span>'}</span><h3>${n}</h3><span class="hi-mut hi-sm">${d}</span><span class="hi-row" style="margin-top:8px">${act(lbl)}</span></div>`;
      return `<div class="hi-wrap">${head('More tools', 'The rest of the voice work, some of it in other parts of Hoola.')}
        ${t === 'Music' ? `<form class="hi-card hi-grid" data-f="music"><div class="hi-sh"><h3>Music</h3><button type="button" class="hi-btn q s" data-a="tab" data-k="mo" data-val="">Close</button></div>
            <label class="hi-f">What it is for<textarea id="hvMBrief" rows="2" maxlength="600" required placeholder="A cheerful opening tune for a sweet shop's Diwali video"></textarea></label>
            <div class="hi-cols"><label class="hi-f">Kind<input id="hvMGenre" maxlength="40" placeholder="Folk, pop, classical…"></label><label class="hi-f">Mood<input id="hvMMood" maxlength="40" placeholder="Happy, calm…"></label>
              <label class="hi-f">Singing<select id="hvMVocals"><option value="instrumental">No singing</option><option value="female">A woman sings</option><option value="male">A man sings</option><option value="duet">Duet</option></select></label></div>
            <button class="hi-btn hi-start">Make the music</button></form>` : ''}
        <div class="hi-grid hi-g3">
          ${card('mic', 'Speech to text', 'Turn a recording or live speech into words, with speakers and timings.', c.stt, l => `<a class="hi-btn q s" href="/console/flow">${l}</a>`, 'Open Hoola Flow')}
          ${card('music', 'Music', 'A tune from a line of description.', c.music, l => `<button class="hi-btn q s" data-a="tab" data-k="mo" data-val="Music"${c.music ? '' : ' disabled'}>${l}</button>`, 'Make music')}
          ${card('film', 'Dubbing', 'A video spoken again in another language, timed to the original.', c.dub, l => `<button class="hi-btn q s" data-a="console" data-val="creative">${l}</button>`, 'Open Create')}
          ${card('chat', 'Voice agents', 'An AI that talks with your customers on a call or a chat page.', true, l => `<button class="hi-btn q s" data-a="console" data-val="aiapps">${l}</button>`, 'Open AI Apps')}
          ${card('wave', 'Website player', 'A player that reads your web page aloud to visitors.', false, () => '<span class="hi-sm hi-mut">Not built.</span>')}
          ${card('swap', 'Voice changer', 'One voice into another, keeping the acting.', false, l => `<button class="hi-btn q s" data-a="go" data-p="changer">${l}</button>`, 'Read more')}</div>
        ${recent(['music'])}</div>`;
    },

    dict() {
      return `<div class="hi-wrap">${head('Dictionary', 'How your names, places and product words must be said. Hoola applies these before any voice reads your text.')}
        <form class="hi-card hi-cols" data-f="rule"><label class="hi-f">Word as written<input id="hvRWord" maxlength="60" required placeholder="Akola"></label>
          <label class="hi-f">Say it as<input id="hvRSay" maxlength="120" required placeholder="Uh-ko-laa"></label>
          <label class="hi-f">In language<select id="hvRLang"><option value="">Every language</option>${opts(langs(), '')}</select></label><button class="hi-btn hi-start" style="align-self:end">Add</button></form>
        ${D.rules.length ? `<div class="hi-card hi-scroll"><table><thead><tr><th>Word</th><th>Said as</th><th>Language</th><th></th></tr></thead><tbody>${D.rules.map(r => `<tr><td><b>${esc(r.word)}</b></td><td>${esc(r.say)}</td>
            <td>${r.lang ? esc(langs()[r.lang] || r.lang) : 'Every language'}</td><td style="text-align:right"><button class="hi-btn danger s" data-a="rmrule" data-id="${esc(r.id)}">Remove</button></td></tr>`).join('')}</tbody></table></div>`
          : '<div class="hi-empty"><b>No words yet</b>Add your shop name, your town, a product - anything a voice says wrongly.</div>'}
        <p class="hi-sm hi-mut">A rule matches the whole word, in any letter case. Your history keeps the words as you wrote them and shows how many were changed.</p></div>`;
    },

    history() {
      const kinds = ['All', ...new Set(D.history.map(h => KIND[h.kind] || h.kind))], f = UI.hist;
      const list = D.history.filter(h => f === 'All' || (KIND[h.kind] || h.kind) === f);
      return `<div class="hi-wrap">${head('History', `Everything you have made. The newest ${D.limits?.history || 200} are kept; download the ones you need.`)}
        <div class="hi-row">${kinds.map(x => `<button class="hi-sel" aria-pressed="${x === f}" data-a="hist" data-val="${esc(x)}">${esc(x)}</button>`).join('')}</div>
        ${list.length ? `<div class="hi-card hv-list">${list.map(row).join('')}</div>` : '<div class="hi-empty"><b>Nothing here yet</b><button class="hi-btn" data-a="go" data-p="tts">Create speech</button></div>'}</div>`;
    },

    settings() {
      if (ARG) { UI.tab.se = ARG; ARG = ''; }
      const t = cur('se', 'Usage'), u = D.usage || {}, e = D.status?.engines || {}, c = con();
      const line = (ok, a, b) => `<li class="hi-step ${ok ? 'done' : 'off'}"><span class="n">${ok ? ic('check') : ic('x')}</span><span><b>${a}</b><br><span class="hi-sm hi-mut">${b}</span></span></li>`;
      return `<div class="hi-wrap">${head('Settings', 'What you have used, which engines are connected, and the rules Hoola keeps.')}${tabs('se', ['Usage', 'Engines', 'Safety', 'Developers'])}
        ${t === 'Usage' ? `<div class="hi-cols"><div class="hi-card hi-grid"><h3>This month (${esc(u.month || '')})</h3><div>
              <div class="hi-kv"><span class="hi-mut">Characters spoken</span><b class="hi-num">${(u.characters || 0).toLocaleString('en-IN')}</b></div><div class="hi-kv"><span class="hi-mut">Minutes of sound</span><b class="hi-num">${u.minutes || 0}</b></div>
              <div class="hi-kv"><span class="hi-mut">Things made</span><b class="hi-num">${u.made || 0}</b></div>${Object.entries(u.by_kind || {}).map(([k, n]) => `<div class="hi-kv"><span class="hi-mut">${KIND[k] || esc(k)}</span><span class="hi-num">${n}</span></div>`).join('')}</div>
              <div class="hi-grid" style="gap:8px"><div class="hi-row nw" style="justify-content:space-between"><span class="hi-mut">Kept on this server</span><b class="hi-num">${u.kept || 0} / ${u.kept_max || 200}</b></div><div class="hi-bar"><i style="width:${Math.min(100, (u.kept || 0) / (u.kept_max || 200) * 100)}%"></i></div></div></div>
            <div class="hi-card hi-grid"><h3>Cost</h3><p class="hi-mut">There is no rupee meter on this page yet. Speech and music are billed by the engine's own account; effects and clean-up run on this server at no engine cost.</p></div></div>`
        : t === 'Engines' ? `<div class="hi-card"><ol class="hi-steps">${line(e.speech, 'Hoola voices', e.speech ? 'The speech engine answers.' : 'Not set up: the server needs its speech key.')}
              ${line(e.lab, 'Your own voices (clone and design)', e.lab ? 'The GPU voice engine is connected.' : 'The GPU voice engine is not connected.')}
              ${line(true, 'Sound effects', 'Made by code on this server.')}${line(e.ffmpeg, 'Clean-up and joining', e.ffmpeg ? 'ffmpeg is installed.' : 'ffmpeg is not installed.')}
              ${line(e.stt, 'Speech to text', e.stt ? 'Switched on (Hoola Flow).' : 'Switched off on this server (Hoola Flow).')}${line(e.music, 'Music', e.music ? 'The music engine answers.' : 'Not set up.')}
              ${line(e.dub, 'Dubbing', e.dub ? 'Ready in Create.' : 'Not set up.')}${line(c.changer, 'Voice changer', 'No speech-to-speech model is connected.')}
              ${line(c.isolate, 'Voice out of music', 'No separation model is connected.')}${line(c.sfx_text, 'Sound from a description', 'No sound model is connected.')}${line(c.pro_clone, 'Professional clone', 'Not built.')}</ol></div>`
        : t === 'Safety' ? `<div class="hi-card"><ol class="hi-steps">${line(true, 'Every recorded voice needs a yes', 'A voice cannot be added without the consent tick. The time is kept; removing the voice deletes its recording.')}
              ${line(true, 'No imitation of a named person', 'A described voice that asks to sound like someone is refused.')}
              ${line(true, 'Your dictionary is applied by code', 'The count of changed words is recorded with every result.')}
              ${line(true, 'Your sounds stay on this server', 'They are files in your own folder. Nobody else can fetch them.')}
              ${line(false, 'AI mark inside the sound file', 'Not built yet. Files are not marked as AI-made.')}</ol></div>`
        : `<div class="hi-grid">${notYet('The public API, keys and webhooks are not open. Until then, Hoola\'s chat can make speech for you: ask it there.')}
            <div class="hi-card hi-grid"><h3>Planned request</h3><pre>POST /v1/vocal/speech
Authorization: Bearer &lt;your key&gt;

{"text": "Hello!", "voice": "hv_Kore", "language": "hi"}</pre></div></div>`}</div>`;
    }
  };

  // ------------------------------------------------------------------ events ---
  const speak = (body, btn, then) => act(() => api('POST', `${A}/tts`, body), r => { then?.(r); rail(); draw(); play(r.id); toast('Ready.'); }, btn, 'Speaking…');
  function onClick(ev) {
    const b = ev.target.closest('[data-a]'); if (!b || b.disabled) return;
    const d = b.dataset, id = d.id;
    switch (d.a) {
      case 'back': return back ? back() : leave();
      case 'console': leave(); return consoleGo?.(d.val);
      case 'go': return go(d.p, d.arg);
      case 'slim': UI.slim = ROOT.dataset.slim !== '1'; return rail();
      case 'tab': keep(); UI.tab[d.k] = d.val; draw(); return flash('hi-tabin', 400);
      case 'filter': UI.filter = d.val; return draw();
      case 'hist': UI.hist = d.val; return draw();
      case 'play': return play(id);
      case 'dl': return download(id);
      case 'closebar': $('#hvAudio').pause(); $('#hvBar').hidden = true; return;
      case 'rmh': return confirm('Remove this from your history? The file is deleted.') && act(() => api('DELETE', `${A}/history?id=${q(id)}`), () => { URLS.delete(`${A}/audio?id=${q(id)}`); if (UI.proj) UI.proj = D.projects.find(p => p.id === UI.proj.id) || UI.proj; draw(); });
      case 'hear': { const v = D.voices.find(x => x.id === id); b.disabled = true;
        return blobUrl(`${A}/voice/preview?id=${q(id)}&lang=${q(UI.lang)}`).then(u => play('', u, `${v?.name || 'Voice'} - sample`)).catch(e => toast(e.message, true)).finally(() => { if (b.isConnected) b.disabled = false; }); }
      case 'usev': UI.voice = id; return go('tts');
      case 'rmv': return confirm('Remove this voice? Its recording is deleted. Sounds already made are kept.') && act(() => api('DELETE', `${A}/voice?id=${q(id)}`));
      case 'rmrule': return act(() => api('DELETE', `${A}/rule?id=${q(id)}`));
      case 'dladd': keep(); UI.dlg.lines.push({speaker: UI.dlg.lines.at(-2)?.speaker || 'Speaker', text: ''}); draw(); return $(`[data-dl="${UI.dlg.lines.length - 1}"]`)?.focus();
      case 'dlrm': keep(); UI.dlg.lines.splice(+d.n, 1); return draw();
      case 'sfx': UI.seed = +$('#hvSeed')?.value || 1; return act(() => api('POST', `${A}/sfx`, {preset: d.p, seed: UI.seed}), r => { draw(); play(r.id); }, b);
      case 'newproj': UI.proj = {id: '', title: '', voice: UI.voice, lang: UI.lang, chapters: [{title: 'Chapter 1', text: ''}]}; return go('reading');
      case 'proj': UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === id) || null)); return go('reading');
      case 'chadd': keep(); UI.proj.chapters.push({title: `Chapter ${UI.proj.chapters.length + 1}`, text: ''}); return draw();
      case 'chrm': keep(); UI.proj.chapters.splice(+d.n, 1); return draw();
      case 'saveproj': return saveProj(b).then(ok => ok && toast('Saved.'));
      case 'readch': return saveProj().then(ok => ok && act(() => api('POST', `${A}/project/chapter`, {id: UI.proj.id, n: +d.n}), r => { UI.proj = JSON.parse(JSON.stringify(D.projects.find(p => p.id === UI.proj.id))); draw(); play(r.id); }, $(`[data-a="readch"][data-n="${d.n}"]`), 'Reading…'));
      case 'export': return act(() => api('POST', `${A}/project/export`, {id: UI.proj.id}), r => { toast('Joined into one file. It is in your history.'); draw(); play(r.id); }, b, 'Joining…');
      case 'rmproj': return confirm('Remove this reading? Sounds already made stay in your history.') && act(() => api('DELETE', `${A}/project?id=${q(id)}`), () => { UI.proj = null; go('studio'); });
    }
  }
  async function saveProj(btn) {
    keep(); const p = UI.proj;
    try { if (btn) btn.disabled = true;
      const out = await api('POST', `${A}/project`, {id: p.id, title: p.title, voice: p.voice, lang: p.lang, chapters: p.chapters.map(c => ({title: c.title, text: c.text}))});
      await load(); UI.proj = JSON.parse(JSON.stringify(out)); rail(); draw(); return true; }
    catch (e) { toast(e.message, true); if (btn?.isConnected) btn.disabled = false; return false; }
  }
  function onInput(ev) { const t = ev.target;
    if (t.id === 'hvText') { const c = $('#hvCount'); if (c) c.textContent = `${t.value.length.toLocaleString('en-IN')} / ${(D.limits?.characters || 40000).toLocaleString('en-IN')} characters`; }
    if (t.id === 'hvSpeed') { const v = $('#hvSpeedV'); if (v) v.textContent = `${(+t.value).toFixed(2)}x`; } }
  function onChange(ev) { const t = ev.target;
    if (t.dataset.ds !== undefined) { keep(); draw(); }                          // a speaker was renamed: the cast list follows
    if (['hvVoice', 'hvLang', 'hvQVoice', 'hvQLang'].includes(t.id)) { if (t.id.endsWith('Voice')) UI.voice = t.value; else UI.lang = t.value; } }
  function onSubmit(ev) {
    const f = ev.target.closest('form[data-f]'); if (!f) return;
    ev.preventDefault();
    const v = id => ($(id)?.value || '').trim(), btn = f.querySelector('button.hi-btn:not(.q):not([type=button])');
    const up = async id => { const file = $(id).files[0]; const r = await upload(file); return {file_id: r?.file_id || r?.id, name: file.name}; };
    switch (f.dataset.f) {
      case 'quick': if (v('#hvQuick').length < 2) { toast('Type the words to speak.', true); return $('#hvQuick').focus(); }
        return speak({text: v('#hvQuick'), voice: v('#hvQVoice'), lang: v('#hvQLang')}, btn);
      case 'tts': keep(); if (UI.text.trim().length < 2) { toast('Type the words to speak.', true); return $('#hvText').focus(); }
        return speak({text: UI.text, voice: UI.voice, lang: UI.lang, style: UI.style, speed: UI.speed, rules: $('#hvRules').checked}, btn);
      case 'dialogue': keep(); return act(() => api('POST', `${A}/dialogue`, {lines: UI.dlg.lines, cast: UI.dlg.cast, lang: UI.lang}), r => { draw(); play(r.id); toast('Ready.'); }, btn, 'Speaking…');
      case 'clone': return act(async () => { const u = await up('#hvCFile'); return api('POST', `${A}/voice/clone`, {name: v('#hvCName'), file_id: u.file_id, consent: $('#hvCOk').checked, lang: v('#hvCLang')}); },
        () => { toast('Voice added.'); UI.tab.vo = 'My voices'; go('voices'); }, btn, 'Adding…');
      case 'design': return act(() => api('POST', `${A}/voice/design`, {name: v('#hvDName'), description: v('#hvDDesc'), gender: v('#hvDGender')}), () => { toast('Voice saved.'); UI.tab.vo = 'My voices'; go('voices'); }, btn);
      case 'rule': return act(() => api('POST', `${A}/rule`, {word: v('#hvRWord'), say: v('#hvRSay'), lang: v('#hvRLang')}), null, btn);
      case 'cleanup': return act(async () => { const u = await up('#hvIFile'); return api('POST', `${A}/cleanup`, {file_id: u.file_id, name: u.name, denoise: $('#hvI1').checked, voice: $('#hvI2').checked, silence: $('#hvI3').checked, level: $('#hvI4').checked}); },
        r => { draw(); play(r.id); toast('Cleaned.'); }, btn, 'Cleaning…');
      case 'music': return act(() => api('POST', `${A}/music`, {brief: v('#hvMBrief'), genre: v('#hvMGenre'), mood: v('#hvMMood'), vocals: v('#hvMVocals'), lang: UI.lang}), r => { UI.tab.mo = ''; draw(); play(r.id); }, btn, 'Making the music…');
    }
  }
  return {open, leave};
};
