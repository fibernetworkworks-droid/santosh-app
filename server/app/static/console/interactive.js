/* v0.747 HOOLA INTERACTIVE - the console's video studio (owner: "a perfect Hoola Interactive page in console, same as
   HeyGen, with HyperFrames in it end to end" -> the approved canvas -> "go").

   Screens (one module, one root):
     home    one line -> Write the script; the three film kinds; her videos; her avatars; what the engines can do now
     studio  the film as scenes: each spoken line + its look (title / big number / price / bar chart / lower third),
             kind, language, avatar, closing line; what still blocks Make, in her words
     making  the real steps of the make job (voice -> words -> HyperFrames check + draw -> kept), Stop
     ready   the video plays, Download, Change something, the facts
     avatars photo avatars with consent; Live + Translate say plainly they are not built yet
   Her text is always shown with esc(); every number on a look is hers (the server blanks the rest). */
window.HoolaInteractive = function ({api, esc, toast, upload}) {
  let EL = null, VIEW = 'home', PID = '', LIST = {projects: [], avatars: []}, ST = {}, PROJ = null, POLL = 0, SAVE_T = 0;
  const URLS = new Map();
  const KIND = {talking_head: ['Talking avatar', 'Your avatar speaks, with titles, prices and charts beside it.'],
                product: ['Product film', 'Your products and your prices, one scene each, with a voice.'],
                reel: ['Reel with captions', '9:16, big moving words, ready for Instagram and Shorts.']};
  const LOOK = {none: 'Just the words', title: 'Big title', big_number: 'Big number', price: 'Price reveal',
                bar_chart: 'Bar chart', lower_third: 'Lower third'};
  const ICON = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5l11 7-11 7z" fill="currentColor"/></svg>',
    ok: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>',
    up: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'};

  const $ = s => EL && EL.querySelector(s);
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const secs = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  const mb = b => `${((+b || 0) / 1048576).toFixed(1)} MB`;
  const pill = p => ({ready: ['ok', 'Ready'], making: ['run', 'Making it'], failed: ['bad', 'Could not make it']}[p.status]
                     || (p.problems?.length || (p.scenes || []).some(s => s.needs) ? ['warn', 'Waiting for your numbers'] : ['soft', 'Draft']));
  const tabs = on => `<nav class="hiv-tabs" aria-label="Hoola Interactive">${[['home', 'Home'], ['videos', 'My videos'], ['avatars', 'Avatars'], ['live', 'Live avatar'], ['translate', 'Translate']]
      .map(([k, n]) => `<button type="button" data-go="${k}" aria-current="${k === on}">${n}</button>`).join('')}<span class="hiv-flex"></span>${readyLine()}</nav>`;

  function readyLine() {
    if (!ST.enabled) return '';
    if (!ST.draw) return `<span class="hiv-state bad"><i></i>The video engine is not installed on this server yet</span>`;
    return ST.voice ? `<span class="hiv-state ok"><i></i>Video + voice engines ready${ST.busy ? ' · another video is being drawn' : ''}</span>`
                    : `<span class="hiv-state warn"><i></i>Voice engine is not set up - videos are made with captions, no voice</span>`;
  }

  async function blobUrl(path) {
    if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true});
    const u = URL.createObjectURL(await r.blob());
    URLS.set(path, u);
    return u;
  }
  async function photos() {                          // avatar pictures need the key, so they come as blobs
    for (const img of EL.querySelectorAll('img[data-av]')) {
      try { img.src = await blobUrl(`/api/interactive/studio/photo?id=${encodeURIComponent(img.dataset.av)}`); } catch { img.remove(); }
    }
  }

  async function load() {
    const [st, li] = await Promise.all([api('GET', '/api/interactive/studio/status').catch(() => ({})),
                                        api('GET', '/api/interactive/studio/list').catch(e => ({error: e.message}))]);
    ST = st || {}; LIST = li && !li.error ? li : {projects: [], avatars: [], error: li?.error};
  }

  async function open(root, arg) {
    EL = root || EL;
    if (!EL) return;
    clearInterval(POLL);
    await load();
    if (LIST.running) return show('making', LIST.running);
    show(VIEW === 'making' && !LIST.running ? 'home' : VIEW, PID, arg);
  }
  function leave() { clearInterval(POLL); clearTimeout(SAVE_T); }

  function show(view, pid, arg) {
    VIEW = view; PID = pid || '';
    clearInterval(POLL);
    if (view === 'studio') return studio(PID);
    if (view === 'making') return making(PID);
    if (view === 'ready') return ready(PID);
    if (view === 'avatars') return avatars();
    if (view === 'videos') return videos();
    if (view === 'live' || view === 'translate') return later(view);
    return home(arg);
  }

  function wire() {
    EL.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => show(b.dataset.go)));
    EL.querySelectorAll('[data-open]').forEach(b => b.addEventListener('click', () => {
      const p = LIST.projects.find(x => x.id === b.dataset.open);
      show(p?.status === 'ready' ? 'ready' : p?.status === 'making' ? 'making' : 'studio', b.dataset.open);
    }));
  }

  function rows(list) {
    if (!list.length) return `<p class="hiv-empty">No videos yet. Write one line above and Hoola writes the script.</p>`;
    return `<ul class="hiv-list">${list.map(p => { const [k, t] = pill(p);
      return `<li><button type="button" class="hiv-row" data-open="${esc(p.id)}">
        <span class="hiv-thumb ${p.shape === 'reel' ? 'tall' : ''}" aria-hidden="true">${p.status === 'ready' ? ICON.play : ''}</span>
        <span class="hiv-rb"><b>${esc(p.title || 'Untitled')}</b><small>${esc(KIND[p.shape]?.[0] || '')} · ${(p.scenes || []).length} scenes${p.video?.duration ? ' · ' + secs(p.video.duration) : ''} · ${esc(ago(p.updated))}</small></span>
        <span class="hiv-pill ${k}">${t}</span></button></li>`; }).join('')}</ul>`;
  }

  function avatarStrip() {
    return `<div class="hiv-avs">${(LIST.avatars || []).map(a => `<span class="hiv-av"><img data-av="${esc(a.id)}" alt=""><span><b>${esc(a.name)}</b> · photo avatar</span></span>`).join('')}
      <button type="button" class="hiv-btn" data-go="avatars">+ New avatar</button></div>`;
  }

  // ------------------------------------------------------------------ home ---
  let SHAPE = 'talking_head', LANG = 'hi', SECS = 30, AVATAR = '';
  function home() {
    const langs = ST.langs || {hi: 'Hindi', en: 'English'};
    EL.innerHTML = `<div class="hiv">${tabs('home')}
      ${LIST.error ? `<p class="hiv-err">${esc(LIST.error)}</p>` : ''}
      <header class="hiv-hd"><h1>What video should Hoola make?</h1>
        <p>Write it in one line. Hoola writes the script as scenes, speaks it in your avatar's voice and draws every scene with HyperFrames - you see each step.</p></header>
      <form class="hiv-ask" id="hivAsk">
        <label for="hivLine" class="hiv-sr">Describe the video</label>
        <textarea id="hivLine" rows="2" maxlength="1200" placeholder="e.g. A 30-second Diwali offer for my sweet shop - 20% off kaju katli, now Rs 512 instead of Rs 640"></textarea>
        <div class="hiv-askrow">
          <label class="hiv-chip">Language <select id="hivLang">${Object.entries(langs).map(([k, n]) => `<option value="${k}"${k === LANG ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
          <label class="hiv-chip">Length <select id="hivSecs">${[15, 30, 45, 60].map(s => `<option value="${s}"${s === SECS ? ' selected' : ''}>${s} s</option>`).join('')}</select></label>
          <label class="hiv-chip">Avatar <select id="hivAv"><option value="">Brand mark (no face)</option>${(LIST.avatars || []).map(a => `<option value="${esc(a.id)}"${a.id === AVATAR ? ' selected' : ''}>${esc(a.name)}</option>`).join('')}</select></label>
          <span class="hiv-flex"></span>
          <span class="hiv-mut">Nothing is made until you press Make</span>
          <button class="hiv-btn pri" id="hivWrite" type="submit">Write the script</button>
        </div>
      </form>
      <div class="hiv-shapes" role="radiogroup" aria-label="What kind of video">${Object.entries(KIND).map(([k, [n, d]]) =>
        `<button type="button" class="hiv-shape" role="radio" aria-checked="${k === SHAPE}" data-shape="${k}"><b>${n}</b><span>${d}</span></button>`).join('')}</div>
      <section class="hiv-sec"><div class="hiv-sh"><h2>Your recent videos</h2>${LIST.projects.length > 4 ? '<button type="button" class="hiv-link" data-go="videos">See all</button>' : ''}</div>${rows(LIST.projects.slice(0, 4))}</section>
      <section class="hiv-sec"><div class="hiv-sh"><h2>Your avatars</h2><button type="button" class="hiv-link" data-go="avatars">Manage</button></div>${avatarStrip()}</section>
    </div>`;
    wire(); photos();
    EL.querySelectorAll('[data-shape]').forEach(b => b.addEventListener('click', () => {
      SHAPE = b.dataset.shape; EL.querySelectorAll('[data-shape]').forEach(x => x.setAttribute('aria-checked', String(x === b)));
    }));
    $('#hivAsk').addEventListener('submit', async ev => {
      ev.preventDefault();
      const ask = $('#hivLine').value.trim(), btn = $('#hivWrite');
      LANG = $('#hivLang').value; SECS = +$('#hivSecs').value; AVATAR = $('#hivAv').value;
      if (ask.length < 6) return toast('Say in one line what the video should be about.', true);
      btn.disabled = true; btn.textContent = 'Writing the script…';
      try {
        const p = await api('POST', '/api/interactive/studio/draft', {ask, shape: SHAPE, lang: LANG, seconds: SECS, avatar_id: AVATAR});
        LIST.projects.unshift(p); show('studio', p.id);
      } catch (e) { toast(e.message || 'Hoola could not write the script just now.', true); btn.disabled = false; btn.textContent = 'Write the script'; }
    });
  }

  function videos() {
    EL.innerHTML = `<div class="hiv">${tabs('videos')}<header class="hiv-hd"><h1>My videos</h1><p>Every video you started, newest first. Finished ones stay here (up to 40).</p></header>${rows(LIST.projects)}</div>`;
    wire();
  }

  // ------------------------------------------------------------------ studio ---
  function lookFields(lk, i) {
    const f = (k, label, ph, v) => `<label class="hiv-f"><span>${label}</span><input data-i="${i}" data-k="${k}" value="${esc(v ?? lk[k] ?? '')}" placeholder="${esc(ph)}" maxlength="60"></label>`;
    if (lk.kind === 'title') return f('text', 'Title words', 'Diwali offer');
    if (lk.kind === 'big_number') return f('value', 'The number', 'e.g. 500+') + f('label', 'What it is', 'happy customers');
    if (lk.kind === 'price') return f('new', 'Price now', 'Rs 512') + f('old', 'Old price (optional)', 'Rs 640') + f('label', 'Label (optional)', 'This week only');
    if (lk.kind === 'lower_third') return f('title', 'Main line', 'Station Road, Akola') + f('sub', 'Second line (optional)', 'Open 9 am to 9 pm');
    if (lk.kind === 'bar_chart') {
      const bars = lk.bars?.length ? lk.bars : [{label: '', value: ''}, {label: '', value: ''}];
      return `<div class="hiv-bars">${bars.map((b, j) => `<label class="hiv-f"><span>Bar ${j + 1} label</span><input data-i="${i}" data-bar="${j}" data-bk="label" value="${esc(b.label || '')}" maxlength="16"></label>
        <label class="hiv-f"><span>Bar ${j + 1} number</span><input data-i="${i}" data-bar="${j}" data-bk="value" value="${esc(b.value || '')}" inputmode="decimal" maxlength="16"></label>`).join('')}</div>
        ${bars.length < 6 ? `<button type="button" class="hiv-link" data-addbar="${i}">+ Add a bar</button>` : ''}${f('unit', 'Unit (optional)', '%')}`;
    }
    return '';
  }

  async function studio(pid) {
    try { PROJ = await api('GET', `/api/interactive/studio/project?id=${encodeURIComponent(pid)}`); }
    catch (e) { toast(e.message, true); return show('home'); }
    drawStudio();
  }

  function drawStudio() {
    const p = PROJ, langs = ST.langs || {hi: 'Hindi', en: 'English'};
    const probs = p.problems || [], noVoice = !ST.voice;
    EL.innerHTML = `<div class="hiv">
      <nav class="hiv-crumb" aria-label="Breadcrumb"><button type="button" class="hiv-link" data-go="home">Hoola Interactive</button> <span aria-hidden="true">/</span> ${esc(p.title)}</nav>
      <header class="hiv-top"><div class="hiv-tt"><label for="hivTitle" class="hiv-sr">Video title</label>
        <input id="hivTitle" class="hiv-title" value="${esc(p.title)}" maxlength="80">
        <p>${p.scenes.length} scenes · ${esc(KIND[p.shape][0])} · ${esc(langs[p.lang] || p.lang)}${p.status === 'failed' ? ' · last try failed' : ''}</p></div>
        <div class="hiv-acts"><label class="hiv-check"><input type="checkbox" id="hivSilent"${noVoice ? ' checked disabled' : ''}> No voice, captions only</label>
          <button class="hiv-btn pri" id="hivMake" type="button"${probs.length ? ' disabled' : ''}>Make the video</button></div></header>
      ${p.status === 'failed' && p.error ? `<p class="hiv-err">The last try stopped: ${esc(p.error)}</p>` : ''}
      ${probs.length ? `<div class="hiv-block" role="status"><b>Before Hoola can make it:</b><ul>${probs.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}
      <div class="hiv-split">
        <section class="hiv-main" aria-labelledby="hivSc"><div class="hiv-sh"><h2 id="hivSc">Script, scene by scene</h2><span class="hiv-mut">Every number shown is one you gave.</span></div>
          <ol class="hiv-scenes">${p.scenes.map((s, i) => `<li class="hiv-scene${s.needs ? ' needs' : ''}">
            <span class="hiv-n">${i + 1}</span>
            <div class="hiv-sb">
              <label class="hiv-sr" for="hivSay${i}">Scene ${i + 1} line</label>
              <textarea id="hivSay${i}" class="hiv-say" data-i="${i}" data-k="say" rows="2" maxlength="300">${esc(s.say)}</textarea>
              <div class="hiv-lookrow"><label class="hiv-f"><span>Look</span><select data-i="${i}" data-look>${Object.entries(LOOK).map(([k, n]) => `<option value="${k}"${k === s.look.kind ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
                ${s.needs ? `<span class="hiv-pill warn">${esc(s.needs)}</span>` : ''}</div>
              <div class="hiv-lookf">${lookFields(s.look, i)}</div>
            </div>
            <div class="hiv-move"><button type="button" class="hiv-ib" data-mv="${i}" data-d="-1" aria-label="Move scene ${i + 1} up"${i ? '' : ' disabled'}>${ICON.up}</button>
              <button type="button" class="hiv-ib" data-mv="${i}" data-d="1" aria-label="Move scene ${i + 1} down"${i < p.scenes.length - 1 ? '' : ' disabled'}>${ICON.down}</button>
              <button type="button" class="hiv-ib" data-rm="${i}" aria-label="Remove scene ${i + 1}">${ICON.x}</button></div>
          </li>`).join('')}</ol>
          ${p.scenes.length < 12 ? '<button type="button" class="hiv-btn" id="hivAdd">+ Add a scene</button>' : ''}
          ${p.shape === 'product' ? `<section class="hiv-sec"><div class="hiv-sh"><h2>Products</h2><span class="hiv-mut">Name and your price - shown exactly as you write them.</span></div>
            <div class="hiv-items">${(p.items.length ? p.items : [{name: '', price: '', note: ''}]).map((it, j) => `<div class="hiv-item">
              <label class="hiv-f"><span>Product</span><input data-item="${j}" data-ik="name" value="${esc(it.name)}" maxlength="48"></label>
              <label class="hiv-f"><span>Price</span><input data-item="${j}" data-ik="price" value="${esc(it.price)}" maxlength="24"></label>
              <label class="hiv-f"><span>Note</span><input data-item="${j}" data-ik="note" value="${esc(it.note)}" maxlength="60"></label></div>`).join('')}</div>
            <button type="button" class="hiv-link" id="hivAddItem">+ Add a product</button></section>` : ''}
        </section>
        <aside class="hiv-side" aria-label="Video settings">
          <label class="hiv-f"><span>Kind</span><select id="hivShape">${Object.entries(KIND).map(([k, [n]]) => `<option value="${k}"${k === p.shape ? ' selected' : ''}>${n}</option>`).join('')}</select></label>
          ${p.shape !== 'reel' ? `<label class="hiv-f"><span>Size</span><select id="hivAspect"><option value="16:9"${p.aspect === '16:9' ? ' selected' : ''}>16:9 wide</option><option value="1:1"${p.aspect === '1:1' ? ' selected' : ''}>1:1 square</option></select></label>` : '<p class="hiv-mut">Reels are always 9:16.</p>'}
          <label class="hiv-f"><span>Language of the voice</span><select id="hivPLang">${Object.entries(langs).map(([k, n]) => `<option value="${k}"${k === p.lang ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>
          <label class="hiv-f"><span>Avatar</span><select id="hivPAv"><option value="">Brand mark (no face)</option>${(LIST.avatars || []).map(a => `<option value="${esc(a.id)}"${a.id === p.avatar_id ? ' selected' : ''}>${esc(a.name)}</option>`).join('')}</select></label>
          <label class="hiv-f"><span>Business name (optional)</span><input id="hivBrand" value="${esc(p.brand || '')}" maxlength="40"></label>
          <label class="hiv-f"><span>Closing card (optional)</span><input id="hivClose" value="${esc(p.closing || '')}" maxlength="80" placeholder="e.g. Order on WhatsApp today"></label>
          <p class="hiv-note">Each scene is drawn by HyperFrames, so titles, prices and charts stay sharp. Hoola checks every scene before drawing it.</p>
          <button type="button" class="hiv-link danger" id="hivDel">Delete this video</button>
        </aside>
      </div></div>`;
    wireStudio();
  }

  function collect() {
    const p = PROJ;
    EL.querySelectorAll('[data-k][data-i]').forEach(inp => {
      const s = p.scenes[+inp.dataset.i]; if (!s) return;
      if (inp.dataset.k === 'say') s.say = inp.value; else s.look[inp.dataset.k] = inp.value;
    });
    EL.querySelectorAll('[data-bar]').forEach(inp => {
      const s = p.scenes[+inp.dataset.i]; if (!s) return;
      s.look.bars = s.look.bars?.length ? s.look.bars : [{label: '', value: ''}, {label: '', value: ''}];
      const b = s.look.bars[+inp.dataset.bar] || (s.look.bars[+inp.dataset.bar] = {label: '', value: ''});
      b[inp.dataset.bk] = inp.value;
    });
    const items = [];
    EL.querySelectorAll('[data-item]').forEach(inp => { const j = +inp.dataset.item; items[j] = items[j] || {name: '', price: '', note: ''}; items[j][inp.dataset.ik] = inp.value; });
    if (p.shape === 'product') p.items = items.filter(Boolean);
    p.title = $('#hivTitle')?.value || p.title;
    p.brand = $('#hivBrand')?.value ?? p.brand; p.closing = $('#hivClose')?.value ?? p.closing;
  }

  async function persist(redraw) {
    collect();
    const p = PROJ;
    try {
      PROJ = await api('PUT', `/api/interactive/studio/project?id=${encodeURIComponent(p.id)}`,
        {title: p.title, shape: p.shape, lang: p.lang, aspect: p.aspect, avatar_id: p.avatar_id, brand: p.brand,
         closing: p.closing, items: p.items, scenes: p.scenes.map(s => ({say: s.say, look: s.look}))});
      const i = LIST.projects.findIndex(x => x.id === PROJ.id); if (i >= 0) LIST.projects[i] = PROJ;
      if (redraw) drawStudio(); else syncProblems();
    } catch (e) { toast(e.message || 'Could not save.', true); }
  }
  function syncProblems() {                     // after a quiet save: the block list + Make button, without stealing focus
    const probs = PROJ.problems || [], btn = $('#hivMake');
    if (btn) btn.disabled = !!probs.length;
    PROJ.scenes.forEach((s, i) => { const li = EL.querySelectorAll('.hiv-scene')[i]; if (li) { li.classList.toggle('needs', !!s.needs); const pl = li.querySelector('.hiv-lookrow .hiv-pill'); if (pl && !s.needs) pl.remove(); } });
    const blk = $('.hiv-block');
    if (!probs.length && blk) blk.remove();
    else if (blk) blk.querySelector('ul').innerHTML = probs.map(x => `<li>${esc(x)}</li>`).join('');
    else if (probs.length) drawStudio();
  }
  const later_save = () => { clearTimeout(SAVE_T); SAVE_T = setTimeout(() => persist(false), 700); };

  function wireStudio() {
    const p = PROJ;
    wire();
    EL.querySelectorAll('input,textarea').forEach(x => { if (x.type !== 'checkbox') x.addEventListener('input', later_save); });
    EL.querySelectorAll('[data-look]').forEach(s => s.addEventListener('change', () => {
      collect(); const sc = p.scenes[+s.dataset.i]; sc.look = {kind: s.value, ...(s.value === 'bar_chart' ? {bars: [{label: '', value: ''}, {label: '', value: ''}]} : {})}; persist(true);
    }));
    EL.querySelectorAll('[data-addbar]').forEach(b => b.addEventListener('click', () => {
      collect(); const sc = p.scenes[+b.dataset.addbar]; sc.look.bars = [...(sc.look.bars || []), {label: '', value: ''}]; drawStudio();
    }));
    EL.querySelectorAll('[data-mv]').forEach(b => b.addEventListener('click', () => {
      collect(); const i = +b.dataset.mv, j = i + +b.dataset.d; [p.scenes[i], p.scenes[j]] = [p.scenes[j], p.scenes[i]]; persist(true);
    }));
    EL.querySelectorAll('[data-rm]').forEach(b => b.addEventListener('click', () => { collect(); p.scenes.splice(+b.dataset.rm, 1); persist(true); }));
    $('#hivAdd')?.addEventListener('click', () => { collect(); p.scenes.push({say: '', look: {kind: 'none'}}); persist(true); });
    $('#hivAddItem')?.addEventListener('click', () => { collect(); p.items = [...p.items, {name: '', price: '', note: ''}]; drawStudio(); });
    const sel = (id, k) => $(id)?.addEventListener('change', e => { collect(); p[k] = e.target.value; persist(true); });
    sel('#hivShape', 'shape'); sel('#hivAspect', 'aspect'); sel('#hivPLang', 'lang'); sel('#hivPAv', 'avatar_id');
    $('#hivDel').addEventListener('click', async () => {
      if (!confirm('Delete this video and its script? This cannot be undone.')) return;
      try { await api('DELETE', `/api/interactive/studio/project?id=${encodeURIComponent(p.id)}`); LIST.projects = LIST.projects.filter(x => x.id !== p.id); show('home'); }
      catch (e) { toast(e.message, true); }
    });
    $('#hivMake').addEventListener('click', async () => {
      clearTimeout(SAVE_T);
      await persist(false);
      if (PROJ.problems?.length) return drawStudio();
      try { await api('POST', '/api/interactive/studio/make', {id: PROJ.id, silent: $('#hivSilent').checked}); show('making', PROJ.id); }
      catch (e) { toast(e.message, true); }
    });
  }

  // ------------------------------------------------------------------ making ---
  async function making(pid) {
    const p = LIST.projects.find(x => x.id === pid) || {title: ''};
    EL.innerHTML = `<div class="hiv">
      <nav class="hiv-crumb" aria-label="Breadcrumb"><button type="button" class="hiv-link" data-go="home">Hoola Interactive</button> <span aria-hidden="true">/</span> ${esc(p.title)} <span aria-hidden="true">/</span> Making it</nav>
      <header class="hiv-top"><div class="hiv-tt"><h1>Hoola is making your video</h1><p id="hivClock" aria-live="polite">Starting…</p></div>
        <div class="hiv-acts"><button type="button" class="hiv-btn" id="hivStop">Stop</button></div></header>
      <div class="hiv-split"><section class="hiv-main"><ol class="hiv-steps" id="hivSteps"></ol></section>
        <aside class="hiv-side"><p class="hiv-note">One video is drawn at a time on the server, at low priority so calls never stutter. You can leave this page - the video keeps being made and waits for you under My videos.</p></aside></div></div>`;
    wire();
    $('#hivStop').addEventListener('click', async () => {
      try { await api('POST', '/api/interactive/studio/stop', {id: pid}); $('#hivStop').disabled = true; $('#hivStop').textContent = 'Stopping after this step…'; }
      catch (e) { toast(e.message, true); }
    });
    const tick = async () => {
      let v; try { v = await api('GET', `/api/interactive/studio/progress?id=${encodeURIComponent(pid)}`); } catch (e) { clearInterval(POLL); toast(e.message, true); return; }
      if (VIEW !== 'making' || PID !== pid) return clearInterval(POLL);
      if (v.lost) { clearInterval(POLL); $('#hivClock').textContent = 'The server restarted while this was being made. Press Make again - your script is kept.'; return; }
      const box = $('#hivSteps');
      if (box && v.steps?.length) box.innerHTML = v.steps.map(s => { const on = s.k === v.current && !v.done, did = s.at !== null && !on;
        return `<li class="${on ? 'on' : did ? 'did' : ''}"><span class="hiv-dot" aria-hidden="true">${did ? ICON.ok : on ? '<i></i>' : ''}</span>
          <span><b>${esc(s.label)}</b>${s.detail ? `<small>${esc(s.detail)}${s.k === 'voice' && v.silent ? '' : ''}</small>` : ''}</span><span class="hiv-t">${on ? 'now' : did ? secs(s.at) : ''}</span></li>`; }).join('');
      $('#hivClock').textContent = v.done ? '' : `${secs(v.elapsed)} so far${v.stopping ? ' · stopping after this step' : ''}`;
      if (v.done) {
        clearInterval(POLL);
        await load();
        if (v.status === 'ready') return show('ready', pid);
        toast(v.status === 'stopped' ? 'Stopped. Nothing was kept - your script is still here.' : `Could not make it: ${v.error}`, v.status !== 'stopped');
        show('studio', pid);
      }
    };
    await tick();
    POLL = setInterval(tick, 1500);
  }

  // ------------------------------------------------------------------ ready ---
  async function ready(pid) {
    let p; try { p = await api('GET', `/api/interactive/studio/project?id=${encodeURIComponent(pid)}`); } catch (e) { toast(e.message, true); return show('home'); }
    const v = p.video || {}, tall = (v.aspect || p.aspect) === '9:16';
    EL.innerHTML = `<div class="hiv">
      <nav class="hiv-crumb" aria-label="Breadcrumb"><button type="button" class="hiv-link" data-go="home">Hoola Interactive</button> <span aria-hidden="true">/</span> ${esc(p.title)}</nav>
      <div class="hiv-ready">
        <div class="hiv-player ${tall ? 'tall' : ''}" id="hivPlayer"><span class="hiv-mut">Loading the video…</span></div>
        <div class="hiv-rinfo">
          <p class="hiv-state ok"><i></i>Ready${v.made_s ? ' · made in ' + secs(v.made_s) : ''}</p>
          <h1>${esc(p.title)}</h1>
          <p class="hiv-mut">${esc(KIND[p.shape][0])} · ${(p.scenes || []).length} scenes · ${v.silent ? 'captions, no voice' : 'spoken in ' + esc((ST.langs || {})[p.lang] || p.lang)}</p>
          <div class="hiv-acts wrap"><button type="button" class="hiv-btn pri" id="hivDl">Download MP4</button>
            <button type="button" class="hiv-btn" id="hivEdit">Change something</button>
            <button type="button" class="hiv-btn" id="hivAgain">Make a new version</button></div>
          <dl class="hiv-facts">
            <div><dt>Length</dt><dd>${v.duration ? secs(v.duration) : '-'}</dd></div>
            <div><dt>Size</dt><dd>${tall ? '1080 × 1920 · 9:16' : (p.aspect === '1:1' ? '1080 × 1080 · 1:1' : '1920 × 1080 · 16:9')} · ${mb(v.size)}</dd></div>
            <div><dt>Scenes</dt><dd>${v.scenes || (p.scenes || []).length} · drawn with HyperFrames</dd></div>
            <div><dt>Captions</dt><dd>${v.silent ? 'timed at reading speed' : v.words_estimated ? 'timed by sentence (word timing not installed)' : 'on each spoken word'}</dd></div>
            <div><dt>Made</dt><dd>${esc(ago(v.made))}</dd></div>
          </dl>
          <p class="hiv-note">To send it on WhatsApp or post it, download it - or ask Hoola in chat; sending always asks you first.</p>
        </div></div></div>`;
    wire();
    const path = `/api/interactive/studio/video?id=${encodeURIComponent(pid)}`;
    try { const u = await blobUrl(path); $('#hivPlayer').innerHTML = `<video controls playsinline preload="metadata" src="${u}" aria-label="${esc(p.title)}"></video>`; }
    catch (e) { $('#hivPlayer').innerHTML = `<span class="hiv-err">${esc(e.message || 'The video file could not be loaded.')}</span>`; }
    $('#hivDl').addEventListener('click', async () => {
      try { const a = document.createElement('a'); a.href = await blobUrl(path); a.download = `${(p.title || 'hoola-video').replace(/[^\w .-]+/g, '_').slice(0, 60)}.mp4`; document.body.appendChild(a); a.click(); a.remove(); }
      catch (e) { toast(e.message, true); }
    });
    $('#hivEdit').addEventListener('click', () => show('studio', pid));
    $('#hivAgain').addEventListener('click', async () => {
      try { await api('POST', '/api/interactive/studio/make', {id: pid, silent: !!v.silent || !ST.voice}); URLS.delete(path); show('making', pid); } catch (e) { toast(e.message, true); }
    });
  }

  // ------------------------------------------------------------------ avatars ---
  function avatars() {
    EL.innerHTML = `<div class="hiv">${tabs('avatars')}
      <header class="hiv-hd"><h1>Your avatars</h1><p>A photo avatar appears beside your words in every scene. Use your own photo, or one of a person who agreed.</p></header>
      <div class="hiv-avgrid">${(LIST.avatars || []).map(a => `<article class="hiv-avc"><img data-av="${esc(a.id)}" alt="${esc(a.name)}"><div><b>${esc(a.name)}</b><small>Photo avatar · consent given ${esc(ago(a.consent_at))}</small>
        <button type="button" class="hiv-link danger" data-rmav="${esc(a.id)}">Remove</button></div></article>`).join('') || '<p class="hiv-empty">No avatars yet.</p>'}</div>
      <form class="hiv-newav" id="hivNewAv"><h2>New photo avatar</h2>
        <label class="hiv-f"><span>Name</span><input id="hivAvName" maxlength="40" required placeholder="e.g. Priya"></label>
        <label class="hiv-f"><span>Photo (png, jpg or webp, face to camera)</span><input id="hivAvFile" type="file" accept="image/png,image/jpeg,image/webp" required></label>
        <label class="hiv-check"><input type="checkbox" id="hivAvOk" required> This is me, or the person in the photo agreed to be my avatar</label>
        <button class="hiv-btn pri" type="submit" id="hivAvGo">Add avatar</button>
        <p class="hiv-note">A talking face that moves its lips from a 2-minute consent video is next - it needs the face engine on our GPU, which is not switched on for videos yet.</p>
      </form></div>`;
    wire(); photos();
    EL.querySelectorAll('[data-rmav]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Remove this avatar? Videos already made keep their copy.')) return;
      try { await api('DELETE', `/api/interactive/studio/avatar?id=${encodeURIComponent(b.dataset.rmav)}`); await load(); avatars(); } catch (e) { toast(e.message, true); }
    }));
    $('#hivNewAv').addEventListener('submit', async ev => {
      ev.preventDefault();
      const f = $('#hivAvFile').files[0], btn = $('#hivAvGo');
      if (!f) return;
      btn.disabled = true; btn.textContent = 'Adding…';
      try {
        const up = await upload(f);
        const fid = up?.file_id || up?.id;
        await api('POST', '/api/interactive/studio/avatar', {name: $('#hivAvName').value, file_id: fid, consent: $('#hivAvOk').checked});
        await load(); avatars(); toast('Avatar added.');
      } catch (e) { toast(e.message || 'Could not add the avatar.', true); btn.disabled = false; btn.textContent = 'Add avatar'; }
    });
  }

  function later(view) {
    const t = view === 'live'
      ? ['Live avatar', 'A face that answers visitors in real time on your website.', 'The live face engine was tested on our GPU (about 1 second to first word when warm), but the stream to a visitor\'s browser is not built yet. Until then, make a talking video on Home.']
      : ['Translate', 'The same video in another language, with the lips matched.', 'Not built yet. For now: open a video, choose Change something, set the voice language, rewrite the lines and make it again.'];
    EL.innerHTML = `<div class="hiv">${tabs(view)}<header class="hiv-hd"><h1>${t[0]}</h1><p>${t[1]}</p></header>
      <div class="hiv-block"><b>Coming next.</b> ${esc(t[2])}</div><button type="button" class="hiv-btn" data-go="home">Back to Home</button></div>`;
    wire();
  }

  return {open, leave};
};
