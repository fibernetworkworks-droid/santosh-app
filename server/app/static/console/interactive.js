/* v0.772 HOOLA INTERACTIVE - the whole product as its own full page with its own sidebar (owner: "GO - BUILD IT INTO
   CONSOLE END TO END", after the approved twelve-page design).

   Twelve pages: Home, Avatars, Voices, Studio, Templates, Brand, Translate, Live, Apps, Projects, Developers, Settings.
   What each one stands on is real: /api/interactive/studio/* (the film: draft -> scenes -> make) and
   /api/interactive/hub/* (brand, glossary, templates, batch, names, translate, trash, brains, usage).
   What is NOT connected on this server (twin, cloned voice, lip-matched dubbing of outside videos, the live stream,
   the public API) is read from hub.status().connected and SAID on the page - no control pretends to work.
   Her text is always shown with esc(); every number on a look is hers (the server blanks the rest). */
window.HoolaInteractive = function ({api, esc, toast, upload, back}) {
  const S = '/api/interactive/studio', H = '/api/interactive/hub';
  let ROOT = null, PAGE = 'home', ARG = '', D = null, P = null, POLL = 0, SAVE_T = 0, DLG = '';
  const UI = {tab: {}, tool: 'Look', scene: 0, list: false, slim: null, use: '', pick: '', tlang: ''};
  const URLS = new Map();
  const PAGES = [['home', 'Home', 'home'], ['avatars', 'Avatars', 'user'], ['voices', 'Voices', 'mic'], ['studio', 'Studio', 'film'],
    ['templates', 'Templates', 'grid'], ['brand', 'Brand', 'brand'], ['translate', 'Translate', 'globe'], ['live', 'Live', 'live'],
    ['apps', 'Apps', 'apps'], ['projects', 'Projects', 'folder'], ['developers', 'Developers', 'code'], ['settings', 'Settings', 'gear']];
  const KIND = {talking_head: 'Talking avatar', product: 'Product film', reel: 'Reel with captions'};
  const LOOK = {none: 'Just the words', title: 'Big title', big_number: 'Big number', price: 'Price reveal', bar_chart: 'Bar chart', lower_third: 'Name strip'};
  const PATHS = {
    home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-7 8-7s8 3 8 7"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    film: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
    grid: '<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="5" rx="2"/><rect x="13" y="10" width="8" height="11" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/>',
    brand: '<path d="M12 3a9 9 0 1 0 0 18c1.6 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="8" cy="11" r="1"/><circle cx="12" cy="7.5" r="1"/><circle cx="16" cy="10" r="1"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    live: '<circle cx="12" cy="12" r="2.5"/><path d="M7.5 7.5a6.4 6.4 0 0 0 0 9M16.5 7.5a6.4 6.4 0 0 1 0 9M4.5 4.5a10.6 10.6 0 0 0 0 15M19.5 4.5a10.6 10.6 0 0 1 0 15"/>',
    apps: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><path d="M17.5 14v7M14 17.5h7"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 5l-3 14"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M18.7 5.3l-2.1 2.1M7.4 16.6l-2.1 2.1"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    play: '<path d="M8 5.5v13l11-6.5z"/>', side: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>', warn: '<path d="M12 4l9 15.5H3zM12 10v4.5M12 17.2v.1"/>', left: '<path d="M14.5 6l-6 6 6 6"/>', right: '<path d="M9.5 6l6 6-6 6"/>',
    rows: '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>', clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>', lang: '<path d="M4 6h9M8.5 4v2M6 6c.6 3.6 3 6.4 6 7.6M11.5 6c-.7 3.8-3.4 6.8-7 8M13 20l4-9 4 9M14.4 17h5.2"/>',
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>', down: '<path d="M12 5v14M6 13l6 6 6-6"/>', x: '<path d="M6 6l12 12M18 6L6 18"/>', back: '<path d="M19 12H5M11 6l-6 6 6 6"/>'};
  const ic = n => `<svg class="hi-i" viewBox="0 0 24 24" aria-hidden="true">${PATHS[n] || ''}</svg>`;
  const $ = s => ROOT && ROOT.querySelector(s);
  const $$ = s => ROOT ? [...ROOT.querySelectorAll(s)] : [];
  const q = encodeURIComponent;
  const ago = iso => { const t = Date.parse(iso || ''); if (!t) return ''; const m = Math.round((Date.now() - t) / 60000);
    return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`; };
  const secs = s => { s = Math.round(+s || 0); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, '0')} s`; };
  const clock = s => { s = Math.round(+s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
  const mb = b => `${((+b || 0) / 1048576).toFixed(1)} MB`;
  const langs = () => D?.status?.langs || {hi: 'Hindi'};
  const con = () => D?.status?.connected || {};
  const state = p => ({ready: ['ok', 'Ready'], making: ['pri', 'Making it'], failed: ['bad', 'Could not make it']}[p.status]
    || ((p.scenes || []).some(s => s.needs) ? ['warn', 'Waiting for your numbers'] : ['', 'Draft']));
  const chip = p => { const [c, t] = state(p); return `<span class="hi-chip ${c}">${t}</span>`; };
  const estimate = p => (p.scenes || []).reduce((n, s) => n + Math.max(2, (s.say || '').split(/\s+/).filter(Boolean).length / 2.6) + .35, 0);
  const tabs = (id, names) => { const on = UI.tab[id] || names[0];
    return `<div class="hi-tabs" role="tablist">${names.map(n => `<button class="hi-tab" role="tab" aria-selected="${n === on}" data-a="tab" data-k="${id}" data-v="${esc(n)}">${esc(n)}</button>`).join('')}</div>`; };
  const cur = (id, d) => UI.tab[id] || d;
  const opts = (o, on) => Object.entries(o).map(([k, n]) => `<option value="${esc(k)}"${k === on ? ' selected' : ''}>${esc(n)}</option>`).join('');
  const avOpts = on => `<option value="">Brand mark (no face)</option>${(D.avatars || []).map(a => `<option value="${esc(a.id)}"${a.id === on ? ' selected' : ''}>${esc(a.name)}</option>`).join('')}`;
  const init = n => (String(n || '').trim() || 'H').slice(0, 2).toUpperCase();
  const hex = c => /^#[0-9a-f]{6}$/i.test(c || '') ? c : '#7C5CFF';
  const TINT = ['#7C5CFF', '#F27A52', '#C055F5', '#2DB8A8', '#E0A23A'];
  const tint = id => TINT[[...String(id || '')].reduce((n, ch) => (n * 31 + ch.charCodeAt(0)) >>> 0, 7) % TINT.length];
  const face = (a, cls = '') => `<span class="hi-face ${cls}">${a ? `<img data-av="${esc(a.id)}" alt="${esc(a.name)}">` : esc(init(D.brand?.name))}</span>`;
  const pick = (id, label, inner, i) => `<label class="hi-pick">${i ? ic(i) : ''}<select id="${id}" aria-label="${label}">${inner}</select></label>`;
  const thumb = (id, title, extra = '') => `<span class="hi-thumb" style="--t:${tint(id)}">${extra}<span class="cap">${esc(title)}</span></span>`;
  const mini = s => { const k = s.look || {}, t = k.kind === 'title' ? k.text : k.kind === 'big_number' ? k.value : k.kind === 'price' ? k.new : k.kind === 'lower_third' ? k.title : '';
    return `<span class="mini" aria-hidden="true">${k.kind === 'bar_chart' ? '<span class="mb"><u style="height:45%"></u><u style="height:70%"></u><u style="height:100%"></u></span>' : t ? `<b>${esc(t)}</b>` : '<span class="ml"><u></u><u></u></span>'}${s.needs ? '<i class="wn"></i>' : ''}</span>`; };
  const blockBox = list => list?.length ? `<div class="hi-block" role="status">${ic('warn')}<div><b>Before Hoola can make it</b>${list.map(x => `<span>${esc(x)}</span>`).join('')}</div></div>` : '';
  const engine = () => { const st = D.status || {};
    return D.error ? ['bad', D.error, 'Not loaded'] : !st.draw ? ['bad', 'The video engine is not installed on this server yet', 'Engine missing']
      : st.voice ? ['ok', `Video and voice engines are ready${st.busy ? ' - another video is being drawn' : ''}`, 'Engines ready'] : ['warn', 'Voice engine is not set up - videos are made with captions, no voice', 'Captions only']; };
  const notYet = why => `<div class="hi-note warn"><b>Not connected on this server yet.</b> ${esc(why)}</div>`;
  const head = (h, p, btn = '') => `<div class="hi-head"><div><h1>${h}</h1>${p ? `<p>${p}</p>` : ''}</div>${btn}</div>`;
  const vidCard = p => `<button class="hi-av" data-a="open" data-id="${esc(p.id)}">${thumb(p.id, p.title, p.status === 'ready' ? `<span class="play">${ic('play')}</span>${p.video?.duration ? `<span class="len hi-num">${clock(p.video.duration)}</span>` : ''}` : `<span class="cnt hi-num">${(p.scenes || []).length} scene${(p.scenes || []).length === 1 ? '' : 's'}</span>`)}
    <span class="hi-row nw" style="justify-content:space-between"><span class="hi-sm hi-mut">${esc(langs()[p.lang] || p.lang)} · ${esc(ago(p.updated || p.created))}</span>${chip(p)}</span></button>`;

  async function blobUrl(path) {
    if (URLS.has(path)) return URLS.get(path);
    const r = await api('GET', path, undefined, {raw: true});
    const u = URL.createObjectURL(await r.blob());
    URLS.set(path, u);
    return u;
  }
  async function photos() {                           // avatar pictures need the key, so they come as blobs
    for (const img of $$('img[data-av]')) {
      const gone = () => img.isConnected && img.replaceWith(document.createTextNode(init(img.alt)));   // a picture that cannot be shown = her initials, never a broken image
      img.onerror = gone;
      try { img.src = await blobUrl(`${S}/photo?id=${q(img.dataset.av)}`); } catch { gone(); }
    }
  }
  async function load() {
    try { D = await api('GET', `${H}/overview`); }
    catch (e) { D = {projects: [], avatars: [], templates: [], glossary: [], trash: [], brains: [], brand: {}, usage: {}, status: {connected: {}}, error: e.message}; }
  }

  // ------------------------------------------------------------------ shell ---
  function mount() {
    if (ROOT) { ROOT.hidden = false; return; }
    ROOT = document.createElement('div');
    ROOT.id = 'hiRoot';
    ROOT.setAttribute('role', 'application');
    ROOT.setAttribute('aria-label', 'Hoola Interactive');
    ROOT.innerHTML = `<nav class="hi-rail" id="hiRail" aria-label="Hoola Interactive pages"></nav>
      <div class="hi-main"><main class="hi-view" id="hiView"></main></div>`;
    document.body.appendChild(ROOT);
    ROOT.addEventListener('click', onClick);
    ROOT.addEventListener('input', onInput);
    ROOT.addEventListener('change', onChange);
    ROOT.addEventListener('submit', onSubmit);
  }
  async function open() {
    mount();
    clearInterval(POLL);
    await load();
    if (D.running) return go('making', D.running);
    go(PAGE === 'making' ? 'home' : PAGE, ARG);
  }
  function leave() { clearInterval(POLL); clearTimeout(SAVE_T); if (ROOT) ROOT.hidden = true; }
  function rail() {
    const on = {editor: 'studio', making: 'studio', video: 'projects', avatar: 'avatars', proof: 'translate'}[PAGE] || PAGE, [ec, et, es] = engine();
    const slim = UI.slim ?? PAGE === 'editor';                       // the editor opens folded so the canvas has room; her own choice wins
    ROOT.dataset.slim = slim ? 1 : 0;
    $('#hiRail').innerHTML = `<div class="hi-rhead"><button class="hi-mark" data-a="go" data-p="home" title="Hoola Interactive home"><i>${ic('play')}</i><span>Hoola<small>Interactive</small></span></button>
        <button class="hi-ib" data-a="slim" aria-label="${slim ? 'Open' : 'Fold'} the sidebar" title="${slim ? 'Open' : 'Fold'} the sidebar">${ic('side')}</button></div>
      <button class="hi-new" data-a="go" data-p="home" aria-label="Create a video" title="Create a video">${ic('plus')}<span>Create video</span></button>` +
      PAGES.map(([id, n, i], k) => `${k === 10 ? '<hr>' : ''}<button class="hi-rb" data-a="go" data-p="${id}" title="${n}"${id === on ? ' aria-current="page"' : ''}><span class="hi-tile">${ic(i)}</span><span class="hi-rl">${n}</span></button>`).join('') +
      `<span class="hi-sp"></span><button class="hi-rs ${ec}" data-a="go" data-p="settings" data-arg="Engines" aria-label="${esc(et)}" title="${esc(et)}"><i></i><span class="hi-rl">${es}</span></button>
       <button class="hi-rb" data-a="back" title="Back to the Hoola console"><span class="hi-tile">${ic('back')}</span><span class="hi-rl">Back to console</span></button>`;
  }
  const flash = (cls, ms) => { const v = $('#hiView'); if (!v) return; v.classList.remove('hi-in', 'hi-tabin', 'hi-scin'); void v.offsetWidth; v.classList.add(cls);
    clearTimeout(flash.t); flash.t = setTimeout(() => v.classList.remove(cls), ms); };
  function go(page, arg) {
    clearInterval(POLL); clearTimeout(SAVE_T);
    PAGE = V[page] ? page : 'home'; ARG = arg || ''; DLG = '';
    rail(); draw(); flash('hi-in', 900);                // the page rises in once; later redraws of the same page do not replay it
    $('#hiView').scrollTop = 0;
  }
  function draw() {
    const r = V[PAGE]();
    if (typeof r === 'string') { $('#hiView').innerHTML = r + (DLG ? `<div class="hi-ov" id="hiOv">${DLG}</div>` : ''); photos(); }
  }
  const dialog = html => { DLG = `<div class="hi-dlg" role="dialog" aria-modal="true">${html}</div>`; draw(); $('#hiOv button, #hiOv input')?.focus(); };
  const closeDlg = () => { DLG = ''; draw(); };
  async function act(fn, done) {
    try { const r = await fn(); await load(); if (done) done(r); else { rail(); draw(); } }
    catch (e) { toast(e.message || 'That did not work.', true); }
  }

  // ------------------------------------------------------------------ pages ---
  const V = {
    home() {
      const mine = D.avatars[0], c = con(), u = D.usage || {}, [ec, et] = engine(), kept = u.kept_max || 40;
      const step = (ok, n, t) => `<li class="hi-step ${ok ? 'done' : ''}"><span class="n">${ok ? ic('check') : n}</span>${t}</li>`;
      return `<div class="hi-wrap"><section class="hi-hero"><span class="hi-eye"><i></i>Hoola Interactive</span><h1>What video should Hoola make?</h1>
        <form class="hi-ask" data-f="draft"><label class="hi-sm hi-mut" for="hiLine">Describe the video in one line</label>
          <textarea id="hiLine" rows="2" maxlength="1200" placeholder="e.g. A Diwali offer for my shop - Rs 40 off every cement bag till 10 November"></textarea>
          <div class="hi-askrow">${pick('hiKind', 'Kind of video', opts(KIND, 'talking_head'), 'film')}${pick('hiLang', 'Language', opts(langs(), 'hi'), 'lang')}
            ${pick('hiSecs', 'Length', [15, 30, 45, 60].map(s => `<option value="${s}"${s === 30 ? ' selected' : ''}>${s} seconds</option>`).join(''), 'clock')}${pick('hiAvSel', 'Avatar', avOpts(''), 'user')}
            <span class="hi-fill"></span><button class="hi-btn lg" id="hiGo">Write the script ${ic('arrow')}</button></div></form>
        <div class="hi-row"><span class="hi-sm hi-mut">Try</span>${['A festival offer for my shop', 'Tomorrow the shop is closed', 'Introduce my business in half a minute', 'Thank a customer by name']
          .map(t => `<button type="button" class="hi-sel" data-a="eg" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div></section>
        <div class="hi-strap ${ec}"><i></i><span class="hi-fill">${esc(et)}</span><button class="hi-link" data-a="go" data-p="settings" data-arg="Engines">See engines</button></div>
        <section class="hi-grid"><h2>Start a different way</h2><div class="hi-grid hi-g3">${[
          ['film', 'Build scene by scene', 'Open a draft: script on the left, your avatar on the canvas.', 'studio'], ['user', 'Create my avatar', 'A photo of you, or of a person who agreed.', 'avatars'],
          ['grid', 'Start from a template', 'Offers, lessons, updates, greetings - you fill the words.', 'templates'], ['globe', 'Translate a video', 'The same video in another Indian language.', 'translate'],
          ['apps', 'Batches and names', 'Many scripts at once, or one video for many people.', 'apps'], ['brand', 'Set my brand', 'Your name, closing line and colour on every video.', 'brand'],
          ['mic', 'Voices', 'Hear the Hoola voice in each language.', 'voices'], ['live', 'Talk live', 'What a live avatar should know about your business.', 'live']]
          .map(([i, t, d, g]) => `<button class="hi-flow" data-a="go" data-p="${g}"><span class="hi-ftop"><span class="ic">${ic(i)}</span><span class="arr">${ic('arrow')}</span></span><h3>${t}</h3><span class="hi-mut hi-sm">${d}</span></button>`).join('')}</div></section>
        <section class="hi-cols"><div class="hi-card hi-grid"><div class="hi-sh"><h3>Your avatar</h3><button class="hi-btn q s" data-a="go" data-p="avatars">Open</button></div>
            ${mine ? `<div class="hi-row nw"><span class="hi-dot">${face(mine)}</span><span><b>${esc(mine.name)}</b><br><span class="hi-sm hi-mut">Photo avatar · consent given ${esc(ago(mine.consent_at))}</span></span></div>`
                   : `<p class="hi-mut">No avatar yet. Without one, videos show your brand mark.</p>`}
            <ol class="hi-steps">${step(mine, 1, 'Photo with consent')}${step(c.voice, 2, `Hoola voice${c.voice ? '' : ' - engine not set up'}`)}${step(false, 3, 'Talking face - not connected yet')}</ol></div>
          <div class="hi-card hi-grid"><div class="hi-sh"><h3>This month</h3><button class="hi-btn q s" data-a="go" data-p="settings">Usage</button></div>
            <div class="hi-stats"><div class="hi-stat"><b>${u.videos || 0}</b><span class="hi-sm hi-mut">videos made</span></div><div class="hi-stat"><b>${u.minutes || 0}</b><span class="hi-sm hi-mut">minutes of video</span></div>
              <div class="hi-stat"><b>${u.stored || 0} / ${kept}</b><span class="hi-sm hi-mut">kept on this server</span></div></div>
            <div class="hi-bar"><i style="width:${Math.min(100, (u.stored || 0) / kept * 100)}%"></i></div>
            <p class="hi-sm hi-mut">Counted from the videos on this server. There is no rupee meter yet.</p></div></section>
        <section class="hi-grid"><div class="hi-sh"><h2>Recent</h2>${D.projects.length ? `<button class="hi-btn q s" data-a="go" data-p="projects">See all</button>` : ''}</div>
          ${D.projects.length ? `<div class="hi-grid hi-g3">${D.projects.slice(0, 6).map(vidCard).join('')}</div>` : `<div class="hi-empty"><b>No videos yet</b>Write one line above and Hoola drafts the scenes.</div>`}</section></div>`;
    },

    avatars() {
      const t = cur('av', 'My avatars'), c = con();
      return `<div class="hi-wrap">${head('Avatars', 'A photo avatar appears beside your words in every scene. Every real face needs a yes.', `<button class="hi-btn" data-a="tab" data-k="av" data-v="New avatar">${ic('plus')}New avatar</button>`)}
        ${tabs('av', ['My avatars', 'Hoola faces', 'New avatar'])}
        ${t === 'My avatars' ? (D.avatars.length ? `<div class="hi-grid hi-g4">${D.avatars.map(a => `<button class="hi-av" data-a="go" data-p="avatar" data-arg="${esc(a.id)}">${face(a)}<span><b>${esc(a.name)}</b><br><span class="hi-sm hi-mut">${esc(langs()[a.lang] || a.lang)}</span></span>
            <span class="hi-row" style="gap:6px"><span class="hi-chip pri">Photo</span><span class="hi-chip ok">Consent given</span></span></button>`).join('')}</div>`
            : `<div class="hi-empty"><b>No avatars yet</b>Add a clear photo of a face looking at the camera.<button class="hi-btn" data-a="tab" data-k="av" data-v="New avatar">Add a photo avatar</button></div>`)
        : t === 'Hoola faces' ? `<div class="hi-empty"><b>No Hoola faces on this server yet</b>Ready-made presenters are AI-made on the GPU lab, each with a record that says it is not a real person. None has been published here.</div>`
        : `<div class="hi-cols"><form class="hi-card hi-grid" data-f="avatar"><h3>Photo avatar</h3>
              <label class="hi-f">Name<input id="hiAvName" maxlength="40" required placeholder="e.g. Priya"></label>
              <label class="hi-f">Photo (png, jpg or webp, face to camera)<input id="hiAvFile" type="file" accept="image/png,image/jpeg,image/webp" required></label>
              <label class="hi-check"><input type="checkbox" id="hiAvOk" required><span>This is me, or the person in the photo agreed to be my avatar</span></label>
              <button class="hi-btn hi-start" id="hiAvGo">Add avatar</button>
              <p class="hi-sm hi-mut">Not accepted: anyone under 18, public figures, or a person who has not agreed.</p></form>
            <div class="hi-grid"><div class="hi-card hi-grid"><h3>My twin</h3><p class="hi-mut">Record 30 to 60 seconds and read a consent line. The avatar looks and sounds like you.</p>${c.twin ? '' : notYet('It needs the face engine on the GPU, and a consent recording step that is not built.')}</div>
              <div class="hi-card hi-grid"><h3>AI-made face</h3><p class="hi-mut">Describe a person who does not exist and choose from four.</p>${c.ai_face ? '' : notYet('Faces are made in the GPU lab today; the console cannot ask for one yet.')}</div></div></div>`}</div>`;
    },

    avatar() {
      const a = D.avatars.find(x => x.id === ARG);
      if (!a) return V.avatars();
      const used = D.projects.filter(p => p.avatar_id === a.id).length, t = cur('avd', 'Look');
      return `<div class="hi-wrap"><button class="hi-btn q s hi-start" data-a="go" data-p="avatars">${ic('left')}Avatars</button>
        <div class="hi-cols"><div style="max-width:300px">${face(a)}</div><div class="hi-grid"><div class="hi-row"><h1>${esc(a.name)}</h1><span class="hi-chip pri">Photo avatar</span></div>
          <p class="hi-mut">${esc(langs()[a.lang] || a.lang)} · used in ${used} video${used === 1 ? '' : 's'}</p>
          <div class="hi-row"><button class="hi-btn" data-a="go" data-p="home">Use in a video</button><button class="hi-btn danger" data-a="rmav" data-id="${esc(a.id)}">Remove</button></div>
          ${tabs('avd', ['Look', 'Voice', 'Consent'])}
          ${t === 'Look' ? `<p class="hi-mut">One photo. It is shown beside your words; it does not move. A talking face that moves its lips is not connected on this server yet.</p>`
          : t === 'Voice' ? `<p class="hi-mut">Videos with this avatar are spoken in the Hoola voice, in the language you choose for each video.${con().voice ? '' : ' The voice engine is not set up here, so videos are made with captions and no voice.'}</p><button class="hi-btn q hi-start" data-a="go" data-p="voices">Open Voices</button>`
          : `<div class="hi-card hi-grid"><h3>Consent on record</h3><div class="hi-kv"><span class="hi-mut">Given</span><span>${esc((a.consent_at || '').replace('T', ' '))}</span></div><div class="hi-kv"><span class="hi-mut">By</span><span>You, when you added the photo</span></div>
              <p class="hi-sm hi-mut">If the person in the photo asks for it to be removed, press Remove. Videos already made keep their copy.</p></div>`}</div></div></div>`;
    },

    voices() {
      const c = con();
      return `<div class="hi-wrap">${head('Voices', 'One Hoola voice, in every language your videos use.')}
        ${c.voice ? '' : notYet('The voice engine is not set up, so videos are made with captions and no voice. "Hear it" will work once it is.')}
        <div class="hi-card" style="padding:4px 20px">${Object.entries(langs()).map(([k, n]) => `<div class="hi-kv" style="align-items:center">
          <span class="hi-row nw"><span class="hi-sn" style="width:36px;height:36px;border-radius:11px;background:var(--pri-soft);color:var(--pri-ink)">${ic('mic')}</span><span><b>${esc(n)}</b><br><span class="hi-sm hi-mut">Hoola voice</span></span></span>
          <button class="hi-btn q s" data-a="hear" data-lang="${esc(k)}"${c.voice ? '' : ' disabled'}>Hear it</button></div>`).join('')}</div>
        <div class="hi-cols"><div class="hi-card hi-grid"><h3>Clone my voice</h3><p class="hi-mut">One minute of your speech, with your recorded yes.</p>${notYet('Voice cloning runs on the GPU engine and its console step is not built.')}</div>
          <div class="hi-card hi-grid"><h3>Words that must stay as written</h3><p class="hi-mut">Names of places, brands and products are kept when a video is translated.</p><button class="hi-btn q hi-start" data-a="go" data-p="brand" data-arg="Glossary">Open the glossary</button></div></div></div>`;
    },

    studio() {
      const drafts = D.projects.filter(p => p.status !== 'ready');
      return `<div class="hi-wrap">${head('Studio', 'Script on the left, your avatar on the canvas, tools on the right.', `<button class="hi-btn" data-a="go" data-p="home">${ic('plus')}New video</button>`)}
        ${drafts.length ? `<div class="hi-grid hi-g3">${drafts.map(vidCard).join('')}</div>` : `<div class="hi-empty"><b>No drafts open</b>Start from one line on Home, or from a template.<div class="hi-row"><button class="hi-btn" data-a="go" data-p="home">Home</button><button class="hi-btn q" data-a="go" data-p="templates">Templates</button></div></div>`}</div>`;
    },

    editor() {
      if (!P || P.id !== ARG) { loadProject(ARG); return `<div class="hi-wrap"><p class="hi-mut">Opening…</p></div>`; }
      const p = P, i = Math.min(UI.scene, p.scenes.length - 1), sc = p.scenes[i] || {say: '', look: {kind: 'none'}}, lk = sc.look || {kind: 'none'};
      const av = D.avatars.find(a => a.id === p.avatar_id), noVoice = !con().voice, tools = ['Look', 'Avatar', 'Voice', 'Video', 'Brand'];
      const f = (k, label, ph) => `<label class="hi-f">${label}<input data-lk="${k}" value="${esc(lk[k] ?? '')}" placeholder="${esc(ph)}" maxlength="60"></label>`;
      const lookFields = lk.kind === 'title' ? f('text', 'Title words', 'Diwali offer')
        : lk.kind === 'big_number' ? f('value', 'The number', 'e.g. 500+') + f('label', 'What it is', 'happy customers')
        : lk.kind === 'price' ? f('new', 'Price now', 'Rs 512') + f('old', 'Old price (optional)', 'Rs 640') + f('label', 'Label (optional)', 'per kg')
        : lk.kind === 'lower_third' ? f('title', 'Main line', 'Station Road, Akola') + f('sub', 'Second line (optional)', 'Open 9 am to 9 pm')
        : lk.kind === 'bar_chart' ? (lk.bars?.length ? lk.bars : [{label: '', value: ''}, {label: '', value: ''}]).map((b, j) =>
            `<div class="hi-row nw"><label class="hi-f hi-fill">Bar ${j + 1}<input data-bar="${j}" data-bk="label" value="${esc(b.label || '')}" maxlength="16" placeholder="2025"></label>
             <label class="hi-f hi-fill">Number<input data-bar="${j}" data-bk="value" value="${esc(b.value || '')}" inputmode="decimal" maxlength="16"></label></div>`).join('')
            + ((lk.bars || []).length < 6 ? `<button type="button" class="hi-btn q s" data-a="addbar">Add a bar</button>` : '') : '';
      const panel = {
        Look: `<label class="hi-f">Scene ${i + 1} shows<select id="hiLook">${opts(LOOK, lk.kind)}</select></label>${lookFields}<p class="hi-sm hi-mut">Numbers come only from your own words. Hoola never fills one in.</p>`,
        Avatar: `<div class="hi-row nw"><span class="hi-dot">${face(av)}</span><span><b>${esc(av ? av.name : 'Brand mark')}</b><br><span class="hi-sm hi-mut">${av ? 'Photo avatar' : 'No face'}</span></span></div>
          <label class="hi-f">Avatar<select id="hiAv">${avOpts(p.avatar_id)}</select></label><button type="button" class="hi-btn q s" data-a="go" data-p="avatars">Add an avatar</button>`,
        Voice: `<label class="hi-f">Language of the voice<select id="hiPLang">${opts(langs(), p.lang)}</select></label>
          <label class="hi-check"><input type="checkbox" id="hiSilent"${noVoice ? ' checked disabled' : ''}><span>No voice, captions only</span></label>
          ${noVoice ? `<p class="hi-sm hi-mut">The voice engine is not set up on this server, so this video is made with captions.</p>` : ''}`,
        Video: `<label class="hi-f">Kind<select id="hiShape">${opts(KIND, p.shape)}</select></label>
          ${p.shape !== 'reel' ? `<label class="hi-f">Size<select id="hiAspect">${opts({'16:9': 'Wide 16:9', '1:1': 'Square 1:1'}, p.aspect)}</select></label>` : `<p class="hi-sm hi-mut">A reel is always tall, 9:16.</p>`}`,
        Brand: `<label class="hi-f">Business name<input id="hiBrand" value="${esc(p.brand || '')}" maxlength="40"></label>
          <label class="hi-f">Closing card<input id="hiClose" value="${esc(p.closing || '')}" maxlength="80" placeholder="Order today"></label>
          ${D.brand?.color ? `<div class="hi-row"><span class="hi-sw" style="background:${esc(D.brand.color)}"></span><span class="hi-sm hi-mut">Your brand colour is drawn into the film.</span></div>` : `<button type="button" class="hi-btn q s" data-a="go" data-p="brand">Set a brand colour</button>`}`}[UI.tool];
      const shown = lk.kind === 'title' ? `<div class="big">${esc(lk.text || '')}</div>`
        : lk.kind === 'big_number' ? (lk.value ? `<div class="big hi-num">${esc(lk.value)}</div><div>${esc(lk.label || '')}</div>` : `<div class="ph">Needs your number</div>`)
        : lk.kind === 'price' ? (lk.new ? `${lk.old ? `<div class="old hi-num">${esc(lk.old)}</div>` : ''}<div class="big hi-num">${esc(lk.new)}</div><div>${esc(lk.label || '')}</div>` : `<div class="ph">Needs your price</div>`)
        : lk.kind === 'lower_third' ? `<div style="font-weight:700;font-size:clamp(14px,2.2vw,24px)">${esc(lk.title || '')}</div><div style="color:var(--hi-stage-mut)">${esc(lk.sub || '')}</div>`
        : lk.kind === 'bar_chart' ? (() => { const v = (lk.bars || []).map(b => parseFloat(String(b.value).replace(/,/g, '')) || 0), m = Math.max(...v, 1);
            return v.some(Boolean) ? `<div class="bars" role="img" aria-label="Bar chart preview">${v.map(x => `<span style="height:${Math.max(6, x / m * 90)}px"></span>`).join('')}</div>` : `<div class="ph">Needs your numbers</div>`; })() : '';
      const last = p.scenes.length - 1, size = p.aspect === '9:16' ? '9:16' : p.aspect === '1:1' ? '1:1' : '16:9';
      return `<div class="hi-wrap wide"><div class="hi-edhead"><button class="hi-btn q ico" data-a="go" data-p="studio" aria-label="Back to Studio" title="Back to Studio">${ic('left')}</button>
            <input id="hiTitle" class="hi-title" aria-label="Video title" value="${esc(p.title)}" maxlength="80"><span class="hi-saved" id="hiSaved">Saved</span>
            <button class="hi-btn q" data-a="tpl">Save as template</button><button class="hi-btn" id="hiMake" data-a="gen"${p.problems?.length ? ' disabled' : ''}>${ic('play')}Generate</button></div>
        <div id="hiProblems">${blockBox(p.problems)}</div>
        <div class="hi-ed"><section class="hi-edcol" aria-label="Script"><h3>Script, scene by scene</h3>
            ${p.scenes.map((s, n) => `<div class="hi-scene" data-on="${n === i ? 1 : 0}" data-a="scene" data-n="${n}"><div class="hd"><span class="hi-sn">${n + 1}</span><span class="hi-sm hi-mut hi-fill">Scene ${n + 1}</span>
                <button type="button" class="hi-ib" data-a="mv" data-n="${n}" data-d="-1" aria-label="Move scene ${n + 1} up" title="Move up"${n ? '' : ' disabled'}>${ic('up')}</button>
                <button type="button" class="hi-ib" data-a="mv" data-n="${n}" data-d="1" aria-label="Move scene ${n + 1} down" title="Move down"${n < last ? '' : ' disabled'}>${ic('down')}</button>
                <button type="button" class="hi-ib" data-a="rm" data-n="${n}" aria-label="Remove scene ${n + 1}" title="Remove">${ic('x')}</button></div>
              <textarea aria-label="Scene ${n + 1} line" data-say="${n}" maxlength="300" placeholder="What is said in this scene">${esc(s.say)}</textarea>
              <div class="ft">${s.needs ? `<span class="hi-chip warn">${esc(s.needs)}</span>` : `<span class="hi-chip">${esc(LOOK[s.look?.kind] || LOOK.none)}</span>`}<span class="hi-sm hi-dim hi-num">about ${secs(estimate({scenes: [s]}))}</span></div></div>`).join('')}
            ${p.scenes.length < 12 ? `<button type="button" class="hi-add" data-a="add">${ic('plus')}Add scene</button>` : ''}
            ${p.shape === 'product' ? `<h3>Products</h3>${(p.items.length ? p.items : [{name: '', price: '', note: ''}]).map((it, j) => `<div class="hi-scene"><label class="hi-f">Product<input data-item="${j}" data-ik="name" value="${esc(it.name)}" maxlength="48"></label>
              <label class="hi-f">Price<input data-item="${j}" data-ik="price" value="${esc(it.price)}" maxlength="24"></label></div>`).join('')}${p.items.length < 8 ? `<button type="button" class="hi-btn q s hi-start" data-a="additem">Add a product</button>` : ''}` : ''}</section>
          <section class="hi-edcol" style="--hi-brand:${hex(D.brand?.color)}"><div class="hi-stage ${p.aspect === '9:16' ? 'tall' : p.aspect === '1:1' ? 'sq' : ''}"><span class="hi-stag hi-num">Scene ${i + 1} of ${p.scenes.length} · ${size}</span><div class="who">${face(av)}</div><div class="look" id="hiShown">${shown}</div><div class="sub" id="hiSub">${esc(sc.say)}</div></div>
            <div class="hi-trans"><button type="button" class="hi-ib" data-a="scene" data-n="${i - 1}" aria-label="Previous scene"${i ? '' : ' disabled'}>${ic('left')}</button><span class="hi-num">${i + 1} / ${p.scenes.length}</span>
              <button type="button" class="hi-ib" data-a="scene" data-n="${i + 1}" aria-label="Next scene"${i < last ? '' : ' disabled'}>${ic('right')}</button><span class="hi-fill"></span><span>About <span class="hi-num">${secs(estimate(p))}</span> long</span></div>
            <div class="hi-strip">${p.scenes.map((s, n) => `<button type="button" class="hi-sc" data-on="${n === i ? 1 : 0}" data-a="scene" data-n="${n}">${mini(s)}<span class="lb"><b class="hi-num">${n + 1}</b><span class="hi-mut">${esc(LOOK[s.look?.kind] || LOOK.none)}</span></span></button>`).join('')}</div>
            <p class="hi-sm hi-mut">This is a layout preview. The real scenes are checked and drawn when you generate.</p></section>
          <aside class="hi-card hi-tools" aria-label="Tools"><div class="hi-tt">${tools.map(t => `<button type="button" aria-pressed="${t === UI.tool}" data-a="tool" data-t="${t}">${t}</button>`).join('')}</div><div class="hi-panel">${panel}</div></aside></div></div>`;
    },

    making() {
      const p = D.projects.find(x => x.id === ARG) || {title: ''};
      setTimeout(() => poll(ARG), 0);
      return `<div class="hi-wrap narrow">${head('Hoola is making your video', esc(p.title), `<button class="hi-btn q" id="hiStop" data-a="stop">Stop</button>`)}
        <div class="hi-card hi-grid"><div class="hi-row"><span class="hi-chip hi-now">Working</span><span id="hiClock" class="hi-mut hi-num" aria-live="polite">Starting…</span></div><ol class="hi-steps" id="hiStepsBox"></ol></div>
        <p class="hi-note">One video is drawn at a time on the server, at low priority so calls never stutter. You can leave this page - the video keeps being made and waits for you under Projects.</p></div>`;
    },

    video() {
      const p = D.projects.find(x => x.id === ARG);
      if (!p || p.status !== 'ready') return V.projects();
      const v = p.video || {}, tall = (v.aspect || p.aspect) === '9:16';
      setTimeout(async () => { const path = `${S}/video?id=${q(p.id)}`;
        try { const u = await blobUrl(path); const b = $('#hiPlayer'); if (b) b.innerHTML = `<video controls playsinline preload="metadata" src="${u}" aria-label="${esc(p.title)}"></video>`; }
        catch (e) { const b = $('#hiPlayer'); if (b) b.textContent = e.message || 'The video file could not be loaded.'; } }, 0);
      return `<div class="hi-wrap"><button class="hi-btn q s hi-start" data-a="go" data-p="projects">${ic('left')}Projects</button>
        <div class="hi-cols"><div class="hi-player ${tall ? 'tall' : ''}" id="hiPlayer">Loading the video…</div>
          <div class="hi-grid"><span class="hi-chip ok hi-start">Ready${v.made_s ? ' · made in ' + secs(v.made_s) : ''}</span><h1>${esc(p.title)}</h1>
            <p class="hi-mut">${esc(KIND[p.shape])} · ${(p.scenes || []).length} scenes · ${v.silent ? 'captions, no voice' : 'spoken in ' + esc(langs()[p.lang] || p.lang)}</p>
            <div class="hi-row" style="gap:8px"><button class="hi-btn" data-a="dl" data-id="${esc(p.id)}">${ic('down')}Download MP4</button><button class="hi-btn q" data-a="edit" data-id="${esc(p.id)}">Change something</button>
              <button class="hi-btn q" data-a="go" data-p="translate" data-arg="${esc(p.id)}">Translate</button><button class="hi-btn q" data-a="dup" data-id="${esc(p.id)}">Duplicate</button>
              <button class="hi-btn danger" data-a="trash" data-id="${esc(p.id)}">Move to trash</button></div>
            <div><div class="hi-kv"><span class="hi-mut">Length</span><span class="hi-num">${v.duration ? secs(v.duration) : '-'}</span></div>
              <div class="hi-kv"><span class="hi-mut">Size</span><span class="hi-num">${tall ? '1080 × 1920' : p.aspect === '1:1' ? '1080 × 1080' : '1920 × 1080'} · ${mb(v.size)}</span></div>
              <div class="hi-kv"><span class="hi-mut">Captions</span><span>${v.silent ? 'timed at reading speed' : v.words_estimated ? 'timed by sentence' : 'on each spoken word'}</span></div>
              <div class="hi-kv"><span class="hi-mut">Made</span><span>${esc(ago(v.made))}</span></div></div>
            <p class="hi-note">To send it on WhatsApp or post it, download it - or ask Hoola in chat; sending always asks you first. A public share link is not built yet.</p></div></div></div>`;
    },

    templates() {
      const groups = ['All', ...new Set(D.templates.map(t => t.group))], g = cur('tpg', 'All'), t = D.templates.find(x => x.id === UI.use);
      const list = D.templates.filter(x => g === 'All' || x.group === g);
      return `<div class="hi-wrap">${head('Templates', 'A shape that works. The marked words are the ones you fill in - Hoola never fills them for you.')}
        ${t ? `<form class="hi-card hi-grid" data-f="use"><div class="hi-sh"><h3>${esc(t.name)}</h3><button type="button" class="hi-btn q s" data-a="use" data-id="">Close</button></div>
            <div class="hi-cols">${t.variables.map(v => `<label class="hi-f">${esc(v.replace(/_/g, ' '))}<input data-var="${esc(v)}" maxlength="60" required></label>`).join('')}
              <label class="hi-f">Language<select id="hiTLang">${opts(langs(), 'hi')}</select></label><label class="hi-f">Avatar<select id="hiTAv">${avOpts('')}</select></label></div>
            <button class="hi-btn hi-start">Make the draft</button></form>` : ''}
        <div class="hi-row">${groups.map(x => `<button class="hi-sel" aria-pressed="${x === g}" data-a="tab" data-k="tpg" data-v="${esc(x)}">${esc(x)}</button>`).join('')}</div>
        <div class="hi-grid hi-g3">${list.map(x => `<div class="hi-av hov">${thumb(x.id, x.name, `<span class="cnt">${esc(x.mine ? 'Yours' : x.group || '')}</span>`)}<span class="hi-sm hi-mut">${x.count} scenes · ${esc(KIND[x.shape] || '')}</span>
          <span class="hi-row" style="gap:6px">${x.variables.map(v => `<span class="hi-chip pri">{${esc(v)}}</span>`).join('') || '<span class="hi-chip">no blanks</span>'}</span>
          <span class="hi-row" style="gap:6px"><button class="hi-btn s" data-a="use" data-id="${esc(x.id)}">Use this</button>${x.mine ? `<button class="hi-btn danger s" data-a="rmtpl" data-id="${esc(x.id)}">Remove</button>` : ''}</span></div>`).join('')}</div>
        <p class="hi-sm hi-mut">To make your own: open any video in Studio, write {name} or {price} where the words change, and press Save as template.</p></div>`;
    },

    brand() {
      if (ARG) { UI.tab.br = ARG; ARG = ''; }
      const t = cur('br', 'Brand kit'), b = D.brand || {};
      return `<div class="hi-wrap">${head('Brand', 'Set it once. Every new video starts with it.')}${tabs('br', ['Brand kit', 'Glossary'])}
        ${t === 'Brand kit' ? `<div class="hi-cols"><form class="hi-card hi-grid" data-f="brand"><label class="hi-f">Business name<input id="hiBName" value="${esc(b.name || '')}" maxlength="40" placeholder="Sharma Traders"></label>
              <label class="hi-f">Closing card<input id="hiBClose" value="${esc(b.closing || '')}" maxlength="80" placeholder="Station Road, Akola"></label>
              <label class="hi-f">Brand colour<span class="hi-row nw"><input type="color" id="hiBColor" value="${esc(hex(b.color))}"><span class="hi-sm hi-mut">Drawn into titles, prices and charts.</span></span></label>
              <button class="hi-btn hi-start">Save</button></form>
            <div class="hi-card hi-grid"><h3>How it looks</h3><div class="hi-stage" style="--hi-brand:${hex(b.color)}"><div class="look" style="left:8%;right:8%;width:auto;top:30%;text-align:center"><div class="big">${esc(b.name || 'Your business')}</div><div style="color:var(--hi-stage-mut)">${esc(b.closing || 'Your closing line')}</div></div></div>
              <p class="hi-sm hi-mut">Logo and fonts are not built yet: the film uses Hoola's bundled font so Hindi and Marathi always draw correctly.</p></div></div>`
        : `<form class="hi-card hi-cols" data-f="gloss"><label class="hi-f">Word<input id="hiGTerm" maxlength="40" required placeholder="Akola"></label>
              <label class="hi-f">Rule<select id="hiGMode"><option value="keep">Keep exactly as written</option><option value="as">Always translate as…</option></select></label>
              <label class="hi-f">Becomes (for "translate as")<input id="hiGTo" maxlength="60" placeholder="sawlat"></label>
              <label class="hi-f">In language<select id="hiGLang">${opts(langs(), 'mr')}</select></label><button class="hi-btn" style="align-self:end;justify-self:start">Add</button></form>
            ${D.glossary.length ? `<div class="hi-card hi-scroll"><table><thead><tr><th>Word</th><th>Rule</th><th>Language</th><th></th></tr></thead><tbody>${D.glossary.map(x => `<tr><td><b>${esc(x.term)}</b></td>
              <td>${x.mode === 'keep' ? 'Kept as written' : 'Becomes "' + esc(x.to) + '"'}</td><td>${x.mode === 'keep' ? 'All' : esc(langs()[x.lang] || x.lang)}</td><td><button class="hi-btn danger s" data-a="rmgl" data-id="${esc(x.id)}">Remove</button></td></tr>`).join('')}</tbody></table></div>`
              : `<div class="hi-empty"><b>No words yet</b>Add your shop name, place names and product names so a translation never changes them.</div>`}
            <p class="hi-sm hi-mut">Hoola checks every translated line against these rules and flags a line that breaks one. How a word is pronounced cannot be set yet.</p>`}</div>`;
    },

    translate() {
      if (ARG) { UI.pick = ARG; ARG = ''; }
      const src = D.projects.filter(p => !p.from), p = src.find(x => x.id === UI.pick) || null, done = D.projects.filter(x => x.from);
      return `<div class="hi-wrap">${head('Translate', 'The same video in another Indian language. Hoola translates the lines; you check them; then it is made.')}
        <div class="hi-cols"><div class="hi-card hi-grid"><h3>1. Choose a video</h3>${src.length ? `<label class="hi-f">Video<select id="hiTrPick"><option value="">Choose…</option>${src.map(x => `<option value="${esc(x.id)}"${x.id === UI.pick ? ' selected' : ''}>${esc(x.title)} (${esc(langs()[x.lang] || x.lang)})</option>`).join('')}</select></label>`
              : `<p class="hi-mut">You have no videos yet. Make one on Home first.</p>`}
            <h3>2. Translate into</h3><div class="hi-row">${Object.entries(langs()).filter(([k]) => !p || k !== p.lang).map(([k, n]) => `<button class="hi-sel" aria-pressed="${k === UI.tlang}" data-a="tlang" data-lang="${esc(k)}">${esc(n)}</button>`).join('')}</div>
            <button class="hi-btn hi-start" id="hiTrGo" data-a="translate"${p && UI.tlang ? '' : ' disabled'}>Translate the lines</button>
            <p class="hi-sm hi-mut">Every number, price and date must come through unchanged. A line where one changed is flagged for you.</p></div>
          <div class="hi-card hi-grid"><h3>A video made somewhere else</h3><p class="hi-mut">Upload any video and get it back in another language with the lips matched.</p>${notYet('Lip-matched dubbing runs on the GPU engine and is not connected to the console.')}</div></div>
        ${done.length ? `<section class="hi-grid"><h2>Translations</h2><div class="hi-grid hi-g3">${done.map(x => `<button class="hi-av" data-a="go" data-p="proof" data-arg="${esc(x.id)}">${thumb(x.id, x.title)}
          <span class="hi-row nw" style="justify-content:space-between"><span class="hi-sm hi-mut">${esc(langs()[x.from_lang] || '')} to ${esc(langs()[x.lang] || x.lang)}</span>${(x.tr || []).some(n => n.flag) && x.status !== 'ready' ? '<span class="hi-chip warn">Lines to check</span>' : chip(x)}</span></button>`).join('')}</div></section>` : ''}</div>`;
    },

    proof() {
      const p = D.projects.find(x => x.id === ARG);
      if (!p) return V.translate();
      const flags = (p.tr || []).filter(n => n.flag).length;
      return `<div class="hi-wrap"><button class="hi-btn q s hi-start" data-a="go" data-p="translate">${ic('left')}Translate</button>
        <div class="hi-sh"><div class="hi-row"><h1>${esc(p.title)}</h1><span class="hi-chip pri">${esc(langs()[p.from_lang] || '')} to ${esc(langs()[p.lang] || p.lang)}</span>${flags ? `<span class="hi-chip warn">${flags} line${flags === 1 ? '' : 's'} to check</span>` : '<span class="hi-chip ok">Numbers and glossary hold</span>'}</div>
          <div class="hi-row"><button class="hi-btn q" data-a="proofsave" data-id="${esc(p.id)}">Save</button><button class="hi-btn" data-a="proofopen" data-id="${esc(p.id)}">Open in Studio</button></div></div>
        <div class="hi-card hi-scroll"><table><thead><tr><th>#</th><th>Original</th><th>Translation, tap to edit</th><th>Check</th></tr></thead><tbody>${p.scenes.map((s, n) => `<tr><td class="hi-num hi-dim">${n + 1}</td><td class="hi-mut">${esc((p.tr || [])[n]?.src || '')}</td>
          <td><textarea data-pf="${n}" aria-label="Translation of line ${n + 1}" rows="2" maxlength="300" class="hi-area" style="min-width:220px">${esc(s.say)}</textarea></td>
          <td>${(p.tr || [])[n]?.flag ? `<span class="hi-chip warn">${esc(p.tr[n].flag)}</span>` : `<span class="hi-chip ok">OK</span>`}</td></tr>`).join('')}</tbody></table></div>
        <p class="hi-sm hi-mut">The words on screen (titles, name strips) were translated too - check them in Studio. Nothing is made until you press Generate there.</p></div>`;
    },

    live() {
      const b = D.brains.find(x => x.id === UI.brain) || {};
      return `<div class="hi-wrap">${head('Live', 'An avatar that listens and answers from the facts you give it.')}
        ${notYet('The live face runs on the GPU engine and was measured there, but the stream to a visitor\'s browser has not been tested end to end. You can write what it should know now; "Try it" and the website embed open when the stream is connected.')}
        <div class="hi-cols"><form class="hi-card hi-grid" data-f="brain"><h3>${b.id ? 'Edit' : 'New'} brain</h3><input type="hidden" id="hiBrId" value="${esc(b.id || '')}">
            <label class="hi-f">Name<input id="hiBrName" value="${esc(b.name || '')}" maxlength="40" required placeholder="Shop helper"></label>
            <label class="hi-f">What it knows<textarea id="hiBrKnows" rows="5" maxlength="4000" required placeholder="Your timings, products, prices, address, delivery rules.">${esc(b.knows || '')}</textarea></label>
            <label class="hi-f">First line it says<input id="hiBrOpen" value="${esc(b.opening || '')}" maxlength="160" placeholder="Namaste! Aapka swagat hai."></label>
            <label class="hi-f">Pages it may read (one per line)<textarea id="hiBrLinks" rows="2">${esc((b.links || []).join('\n'))}</textarea></label>
            <label class="hi-f">Language<select id="hiBrLang">${opts(langs(), b.lang || 'hi')}</select></label>
            <div class="hi-row"><button class="hi-btn">Save</button>${b.id ? `<button type="button" class="hi-btn q" data-a="brain" data-id="">New</button>` : ''}</div>
            <p class="hi-sm hi-mut">If a question is outside these facts, the avatar must say it does not know.</p></form>
          <div class="hi-grid">${D.brains.length ? D.brains.map(x => `<div class="hi-card hi-grid"><div class="hi-sh"><h3>${esc(x.name)}</h3><span class="hi-chip">${esc(langs()[x.lang] || x.lang)}</span></div>
              <p class="hi-mut hi-sm">${esc((x.knows || '').slice(0, 180))}${(x.knows || '').length > 180 ? '…' : ''}</p>
              <div class="hi-row"><button class="hi-btn q s" data-a="brain" data-id="${esc(x.id)}">Edit</button><button class="hi-btn q s" disabled>Try it</button><button class="hi-btn danger s" data-a="rmbrain" data-id="${esc(x.id)}">Remove</button></div></div>`).join('')
            : `<div class="hi-empty"><b>No brains yet</b>Write what a live avatar should know about your business.</div>`}</div></div></div>`;
    },

    apps() {
      const t = cur('ap', ''), withName = D.projects.filter(p => JSON.stringify(p.scenes).includes('{name}'));
      const card = (i, n, d, ok, a) => `<button class="hi-flow" ${ok ? a : 'disabled'}><span class="hi-ftop"><span class="ic">${ic(i)}</span>${ok ? '<span class="hi-chip ok">Ready</span>' : '<span class="hi-chip">Not connected yet</span>'}</span><h3>${n}</h3><span class="hi-mut hi-sm">${d}</span></button>`;
      return `<div class="hi-wrap">${head('Apps', 'Small tools that each do one job.')}
        ${t === 'Batch' ? `<form class="hi-card hi-grid" data-f="batch"><div class="hi-sh"><h3>Batch</h3><button type="button" class="hi-btn q s" data-a="tab" data-k="ap" data-v="">Close</button></div>
            <label class="hi-f">Scripts - leave an empty line between two videos (up to ${D.limits?.batch || 20})<textarea id="hiBatch" rows="8" required placeholder="Aaj ka cement rate teen sau assi rupaye hai.&#10;&#10;Kal dukaan band rahegi."></textarea></label>
            <div class="hi-row"><label class="hi-pick"><select id="hiBLang" aria-label="Language">${opts(langs(), 'hi')}</select></label><label class="hi-pick"><select id="hiBAv" aria-label="Avatar">${avOpts('')}</select></label><button class="hi-btn">Make the drafts</button></div>
            <p class="hi-sm hi-mut">Each script becomes one draft, cut into scenes at sentence ends. Your words are not rewritten.</p></form>` : ''}
        ${t === 'Names' ? `<form class="hi-card hi-grid" data-f="names"><div class="hi-sh"><h3>One video, many names</h3><button type="button" class="hi-btn q s" data-a="tab" data-k="ap" data-v="">Close</button></div>
            ${withName.length ? `<label class="hi-f">Video that says {name}<select id="hiNPick">${withName.map(p => `<option value="${esc(p.id)}">${esc(p.title)}</option>`).join('')}</select></label>
              <label class="hi-f">Names, one per line (up to ${D.limits?.batch || 20})<textarea id="hiNames" rows="6" required placeholder="Sunita&#10;Rahul"></textarea></label><button class="hi-btn hi-start">Make a draft for each</button>
              <p class="hi-sm hi-mut">Only for people who agreed to hear from you. Nothing is sent from here.</p>`
              : `<p class="hi-mut">First write {name} in a video's script where the person's name should be said. The "Thank-you to a customer" template has it.</p><button type="button" class="hi-btn q hi-start" data-a="go" data-p="templates">Open Templates</button>`}</form>` : ''}
        <section class="hi-grid"><h2>Make a video</h2><div class="hi-grid hi-g3">
          ${card('film', 'Quick video', 'One line in, scenes out.', true, 'data-a="go" data-p="home"')}${card('grid', 'From a template', 'Fill the blanks, get the draft.', true, 'data-a="go" data-p="templates"')}
          ${card('apps', 'Batch', 'Many scripts at once, one draft each.', true, 'data-a="tab" data-k="ap" data-v="Batch"')}${card('user', 'One video, many names', 'Each person hears their own name.', true, 'data-a="tab" data-k="ap" data-v="Names"')}
          ${card('globe', 'Translate', 'A video you made, in another language.', true, 'data-a="go" data-p="translate"')}${card('user', 'Talking photo', 'A photo whose lips move with the words.', false)}
          ${card('grid', 'Slides to video', 'A deck or PDF, one scene per slide.', false)}${card('globe', 'Link to video', 'A web page becomes a script.', false)}
          ${card('mic', 'Podcast', 'Two hosts talk through your topic.', false)}${card('film', 'Series', 'The same kind of video, on a schedule.', false)}</div></section>
        <section class="hi-grid"><h2>Improve a video</h2><div class="hi-grid hi-g3">${card('film', 'Clips', 'A long recording becomes short clips.', false)}${card('mic', 'Speech cleanup', 'Removes "um" and long pauses.', false)}
          ${card('live', 'Lip sync', 'New audio on a video you already have.', false)}${card('grid', 'Sharper picture', 'To 1080p and 4K.', false)}</div></section></div>`;
    },

    projects() {
      const t = cur('pr', 'Videos');
      const list = t === 'Videos' ? D.projects.filter(p => p.status === 'ready') : t === 'Drafts' ? D.projects.filter(p => p.status !== 'ready' && !p.from)
        : t === 'Translations' ? D.projects.filter(p => p.from) : D.trash;
      return `<div class="hi-wrap">${head('Projects', 'Everything you have made, in one place.', `<span class="hi-tabs" role="group" aria-label="View"><button class="hi-tab" aria-pressed="${!UI.list}" data-a="view" data-l="0" aria-label="Grid view" title="Grid">${ic('grid')}</button><button class="hi-tab" aria-pressed="${UI.list}" data-a="view" data-l="1" aria-label="List view" title="List">${ic('rows')}</button></span>`)}
        ${tabs('pr', ['Videos', 'Drafts', 'Translations', 'Trash'])}
        ${t === 'Trash' ? (list.length ? `<div class="hi-row"><span class="hi-mut hi-sm">Kept for ${D.limits?.trash_days || 30} days, then removed for good.</span><span class="hi-fill"></span><button class="hi-btn danger" data-a="emptytrash">Empty the trash</button></div>
            <div class="hi-card hi-scroll"><table><thead><tr><th>Name</th><th>Deleted</th><th></th></tr></thead><tbody>${list.map(p => `<tr><td><b>${esc(p.title)}</b></td><td>${esc(ago(p.trashed))}</td><td><button class="hi-btn q s" data-a="restore" data-id="${esc(p.id)}">Restore</button></td></tr>`).join('')}</tbody></table></div>`
            : `<div class="hi-empty"><b>Nothing in the trash</b>Deleted videos wait here for ${D.limits?.trash_days || 30} days.</div>`)
        : !list.length ? `<div class="hi-empty"><b>Nothing here yet</b><button class="hi-btn" data-a="go" data-p="home">Make a video</button></div>`
        : UI.list ? `<div class="hi-card hi-scroll"><table><thead><tr><th>Name</th><th>Language</th><th>Length</th><th>Changed</th><th>Status</th><th></th></tr></thead><tbody>${list.map(p => `<tr><td><button data-a="open" data-id="${esc(p.id)}" class="hi-link" style="color:var(--ink);font-size:14px;text-align:left">${esc(p.title)}</button></td>
            <td>${esc(langs()[p.lang] || p.lang)}</td><td class="hi-num">${p.video?.duration ? clock(p.video.duration) : '-'}</td><td>${esc(ago(p.updated || p.created))}</td><td>${chip(p)}</td>
            <td><span class="hi-row nw" style="gap:6px;justify-content:flex-end"><button class="hi-btn q s" data-a="dup" data-id="${esc(p.id)}">Duplicate</button><button class="hi-btn danger s" data-a="trash" data-id="${esc(p.id)}">Trash</button></span></td></tr>`).join('')}</tbody></table></div>`
        : `<div class="hi-grid hi-g3">${list.map(vidCard).join('')}</div>`}</div>`;
    },

    developers() {
      return `<div class="hi-wrap">${head('Developers', 'Make videos from your own software.')}
        ${notYet('The public API, keys and webhooks are not open. Nothing below can be called yet; it is the shape they will have.')}
        <div class="hi-cols"><div class="hi-card hi-grid"><h3>What it will do</h3><ol class="hi-steps"><li class="hi-step"><span class="n">1</span>Create a video from a script or a template</li><li class="hi-step"><span class="n">2</span>Ask for its status, or get a signed message when it is ready</li>
            <li class="hi-step"><span class="n">3</span>Send the same request twice safely (one video, not two)</li></ol></div>
          <div class="hi-card hi-grid"><h3>Planned request</h3><pre>POST /v1/interactive/videos
Authorization: Bearer &lt;your key&gt;
Idempotency-Key: diwali-offer-01

{"type": "template", "template": "tp_offer",
 "language": "hi", "values": {"shop": "...", "price": "..."}}</pre></div></div>
        <p class="hi-sm hi-mut">Until then, Hoola's chat can make videos for you: ask it there.</p></div>`;
    },

    settings() {
      if (ARG) { UI.tab.se = ARG; ARG = ''; }
      const t = cur('se', 'Usage'), u = D.usage || {}, st = D.status || {}, c = con();
      const line = (ok, a, b) => `<li class="hi-step ${ok ? 'done' : 'off'}"><span class="n">${ok ? ic('check') : ic('x')}</span><span><b>${a}</b><br><span class="hi-sm hi-mut">${b}</span></span></li>`;
      return `<div class="hi-wrap">${head('Settings', 'What you have used, which engines are connected, and the rules Hoola keeps.')}${tabs('se', ['Usage', 'Engines', 'Safety'])}
        ${t === 'Usage' ? `<div class="hi-cols"><div class="hi-card hi-grid"><h3>This month (${esc(u.month || '')})</h3>
              <div class="hi-kv"><span class="hi-mut">Videos made</span><b class="hi-num">${u.videos || 0}</b></div><div class="hi-kv"><span class="hi-mut">Minutes of video</span><b class="hi-num">${u.minutes || 0}</b></div>
              ${(u.by_language || []).map(x => `<div class="hi-kv"><span class="hi-mut">${esc(x.lang)}</span><span class="hi-num">${x.minutes} min</span></div>`).join('')}
              <div class="hi-grid" style="gap:8px;padding-top:10px"><div class="hi-row nw" style="justify-content:space-between"><span class="hi-mut">Videos kept on this server</span><b class="hi-num">${u.stored || 0} / ${u.kept_max || 40}</b></div><div class="hi-bar"><i style="width:${Math.min(100, (u.stored || 0) / (u.kept_max || 40) * 100)}%"></i></div></div>
              <p class="hi-sm hi-mut">When the limit is reached, the oldest video file is removed. Download the ones you need.</p></div>
            <div class="hi-card hi-scroll"><table><thead><tr><th>Made</th><th>Video</th><th>Length</th></tr></thead><tbody>${(u.recent || []).map(r => `<tr><td>${esc(ago(r.made))}</td><td>${esc(r.title)}</td><td class="hi-num">${clock(r.seconds)}</td></tr>`).join('') || '<tr><td colspan="3" class="hi-mut">No videos made this month.</td></tr>'}</tbody></table></div></div>`
        : t === 'Engines' ? `<div class="hi-card"><ol class="hi-steps">${line(st.draw, 'Scene drawing', st.draw ? 'HyperFrames is installed.' : 'HyperFrames is not installed on this server.')}
              ${line(c.voice, 'Voice', c.voice ? 'The voice engine answers.' : 'Not set up. Videos are made with captions, no voice.')}
              ${line(st.whisper, 'Word timing', st.whisper ? 'Captions follow each spoken word.' : 'Not installed. Captions are timed by sentence.')}
              ${line(c.twin, 'Talking face, twin, AI-made faces', 'Built in the GPU lab. Not connected to this page.')}${line(c.voice_clone, 'Voice cloning', 'Built in the GPU lab. Not connected to this page.')}
              ${line(c.dub_outside_video, 'Lip-matched dubbing', 'Built in the GPU lab. Not connected to this page.')}${line(c.live_stream, 'Live stream', 'Measured on the GPU. The stream to a browser is not tested end to end.')}
              ${line(c.api, 'Public API', 'Not open.')}</ol></div>`
        : `<div class="hi-card"><ol class="hi-steps">${line(true, 'Every real face needs your yes', 'A photo avatar cannot be added without the consent tick. The date is kept.')}
              ${line(true, 'Numbers come only from your words', 'A price or count Hoola wrote without you is removed and the video waits for you.')}
              ${line(true, 'Translations are checked by code', 'A line where a number changed, or a glossary rule broke, is flagged.')}
              ${line(true, 'Your photos and videos stay on this server', 'They are files in your own folder. Deleting a video moves it to the trash for 30 days.')}
              ${line(false, 'AI mark inside the video file', 'Not built yet. Videos are not labelled as AI-made in the file.')}</ol></div>`}</div>`;
    }
  };

  // ------------------------------------------------------------------ the editor ---
  async function loadProject(pid) {
    try { P = await api('GET', `${S}/project?id=${q(pid)}`); UI.scene = 0; if (PAGE === 'editor' && ARG === pid) draw(); }
    catch (e) { toast(e.message, true); go('studio'); }
  }
  function collect() {
    const p = P; if (!p) return;
    for (const t of $$('[data-say]')) if (p.scenes[+t.dataset.say]) p.scenes[+t.dataset.say].say = t.value;
    const sc = p.scenes[Math.min(UI.scene, p.scenes.length - 1)];
    if (sc) { sc.look = sc.look || {kind: 'none'};
      for (const inp of $$('[data-lk]')) sc.look[inp.dataset.lk] = inp.value;
      for (const inp of $$('[data-bar]')) { sc.look.bars = sc.look.bars?.length ? sc.look.bars : [{label: '', value: ''}, {label: '', value: ''}];
        (sc.look.bars[+inp.dataset.bar] ||= {label: '', value: ''})[inp.dataset.bk] = inp.value; } }
    for (const inp of $$('[data-item]')) (p.items[+inp.dataset.item] ||= {name: '', price: '', note: ''})[inp.dataset.ik] = inp.value;
    const v = id => $(id)?.value;
    p.title = v('#hiTitle') || p.title;
    for (const [id, k] of [['#hiShape', 'shape'], ['#hiAspect', 'aspect'], ['#hiPLang', 'lang'], ['#hiAv', 'avatar_id'], ['#hiBrand', 'brand'], ['#hiClose', 'closing']]) if ($(id)) p[k] = v(id);
  }
  async function persist(redraw) {
    if (!P) return;
    collect();
    const p = P, mark = $('#hiSaved'); if (mark) mark.textContent = 'Saving…';
    try {
      const out = await api('PUT', `${S}/project?id=${q(p.id)}`, {title: p.title, shape: p.shape, lang: p.lang, aspect: p.aspect, avatar_id: p.avatar_id,
        brand: p.brand, closing: p.closing, scenes: p.scenes.map(s => ({say: s.say, look: s.look})), items: p.items});
      if (P && P.id === out.id) { if (redraw) { P = out; draw(); } else { P.problems = out.problems; out.scenes.forEach((s, n) => { if (P.scenes[n]) P.scenes[n].needs = s.needs; }); syncProblems(); } }
    } catch (e) { toast(e.message, true); if (mark) mark.textContent = 'Not saved'; }
  }
  function syncProblems() {                       // after a quiet save: the block list + Generate button, without stealing focus
    const box = $('#hiProblems'), mk = $('#hiMake'), mark = $('#hiSaved');
    if (mark) mark.textContent = 'Saved';
    if (box) box.innerHTML = blockBox(P.problems);
    if (mk) mk.disabled = !!P.problems?.length;
  }
  const later = () => { clearTimeout(SAVE_T); const m = $('#hiSaved'); if (m) m.textContent = 'Editing…'; SAVE_T = setTimeout(() => persist(false), 700); };

  async function poll(pid) {
    clearInterval(POLL);
    const tick = async () => {
      let v; try { v = await api('GET', `${S}/progress?id=${q(pid)}`); } catch (e) { clearInterval(POLL); toast(e.message, true); return; }
      if (PAGE !== 'making' || ARG !== pid) return clearInterval(POLL);
      if (v.lost) { clearInterval(POLL); $('#hiClock').textContent = 'The server restarted while this was being made. Open the video and press Generate again - your script is kept.'; return; }
      const box = $('#hiStepsBox');
      if (box && v.steps?.length) box.innerHTML = v.steps.map(s => { const on = s.k === v.current && !v.done, did = s.at !== null && !on;
        return `<li class="hi-step ${on ? 'on' : did ? 'done' : ''}"><span class="n">${did ? ic('check') : ''}</span><span><b>${esc(s.label)}</b>${s.detail ? `<br><span class="hi-sm hi-mut">${esc(s.detail)}</span>` : ''}</span><span class="t hi-num">${on ? 'now' : did ? secs(s.at) : ''}</span></li>`; }).join('');
      $('#hiClock').textContent = v.done ? '' : `${secs(v.elapsed)} so far${v.stopping ? ' · stopping after this step' : ''}`;
      if (v.done) {
        clearInterval(POLL); await load(); P = null;
        if (v.status === 'ready') return go('video', pid);
        toast(v.status === 'stopped' ? 'Stopped. Nothing was kept - your script is still here.' : `Could not make it: ${v.error}`, v.status !== 'stopped');
        go('editor', pid);
      }
    };
    await tick();
    POLL = setInterval(tick, 1500);
  }
  const openProject = id => { const p = D.projects.find(x => x.id === id); if (!p) return;
    go(p.status === 'ready' ? 'video' : p.status === 'making' ? 'making' : p.from && (p.tr || []).some(n => n.flag) ? 'proof' : 'editor', id); };

  // ------------------------------------------------------------------ events ---
  function onClick(ev) {
    if (ev.target.id === 'hiOv') return closeDlg();
    const b = ev.target.closest('[data-a]'); if (!b || b.disabled) return;
    const d = b.dataset, id = d.id;
    switch (d.a) {
      case 'back': return back ? back() : leave();
      case 'go': if (PAGE === 'editor') { clearTimeout(SAVE_T); persist(false); } return go(d.p, d.arg);
      case 'tab': UI.tab[d.k] = d.v; draw(); return flash('hi-tabin', 400);
      case 'slim': UI.slim = ROOT.dataset.slim !== '1'; return rail();
      case 'view': UI.list = d.l === '1'; return draw();
      case 'open': return openProject(id);
      case 'edit': P = null; return go('editor', id);
      case 'use': UI.use = id; return draw();
      case 'tlang': UI.tlang = d.lang; return draw();
      case 'brain': UI.brain = id; return draw();
      case 'close': return closeDlg();
      case 'scene': if (ev.target.closest('button[data-a="mv"],button[data-a="rm"]')) return; if (+d.n === UI.scene) return; collect(); UI.scene = +d.n; UI.tool = 'Look'; later(); draw(); return flash('hi-scin', 600);
      case 'tool': collect(); UI.tool = d.t; draw(); return flash('hi-tabin', 400);
      case 'eg': { const t = $('#hiLine'); if (t) { t.value = d.t; t.focus(); } return; }
      case 'add': collect(); P.scenes.push({say: '', look: {kind: 'none'}, needs: ''}); UI.scene = P.scenes.length - 1; draw(); return $(`[data-say="${UI.scene}"]`)?.focus();
      case 'rm': collect(); P.scenes.splice(+d.n, 1); UI.scene = Math.max(0, Math.min(UI.scene, P.scenes.length - 1)); return persist(true);
      case 'mv': { collect(); const n = +d.n, m = n + +d.d; [P.scenes[n], P.scenes[m]] = [P.scenes[m], P.scenes[n]]; UI.scene = m; return persist(true); }
      case 'addbar': { collect(); const sc = P.scenes[UI.scene]; sc.look.bars = [...(sc.look.bars || []), {label: '', value: ''}]; return draw(); }
      case 'additem': collect(); P.items.push({name: '', price: '', note: ''}); return draw();
      case 'gen': return genBox();
      case 'make': return startMake(id, d.silent === '1');
      case 'stop': return act(() => api('POST', `${S}/stop`, {id: ARG}), () => { const s = $('#hiStop'); if (s) { s.disabled = true; s.textContent = 'Stopping after this step…'; } });
      case 'tpl': return act(async () => { await persist(false); return api('POST', `${H}/template`, {project: P.id}); }, t => { toast(`Saved as a template with ${t.variables.length} blank${t.variables.length === 1 ? '' : 's'}.`); go('templates'); });
      case 'rmtpl': return confirm('Remove this template?') && act(() => api('DELETE', `${H}/template?id=${q(id)}`));
      case 'rmgl': return act(() => api('DELETE', `${H}/glossary?id=${q(id)}`));
      case 'rmbrain': return confirm('Remove this brain?') && act(() => api('DELETE', `${H}/brain?id=${q(id)}`), () => { UI.brain = ''; draw(); });
      case 'rmav': return confirm('Remove this avatar? Videos already made keep their copy.') && act(() => api('DELETE', `${S}/avatar?id=${q(id)}`), () => go('avatars'));
      case 'dup': return act(() => api('POST', `${H}/duplicate`, {id}), p => { toast('Copied.'); P = null; go('editor', p.id); });
      case 'trash': return confirm('Move this to the trash? You can restore it for 30 days.') && act(() => api('POST', `${H}/trash`, {id}), () => { P = null; go('projects'); });
      case 'restore': return act(() => api('POST', `${H}/restore`, {id}), () => { toast('Restored.'); draw(); });
      case 'emptytrash': return confirm('Remove everything in the trash for good?') && act(() => api('POST', `${H}/trash/empty`));
      case 'translate': { const btn = b; btn.disabled = true; btn.textContent = 'Translating…';
        return act(() => api('POST', `${H}/translate`, {id: UI.pick, lang: UI.tlang}), p => { UI.tlang = ''; go('proof', p.id); }).finally(() => { if (btn.isConnected) { btn.disabled = false; btn.textContent = 'Translate the lines'; } }); }
      case 'proofsave': case 'proofopen': { const p = D.projects.find(x => x.id === id); if (!p) return;
        const scenes = p.scenes.map((s, n) => ({say: $(`[data-pf="${n}"]`)?.value ?? s.say, look: s.look}));
        return act(() => api('PUT', `${S}/project?id=${q(id)}`, {scenes}), () => { if (d.a === 'proofopen') { P = null; go('editor', id); } else { toast('Saved.'); draw(); } }); }
      case 'hear': return hear(d.lang, b);
      case 'dl': return download(id);
    }
  }
  function onInput(ev) {
    const t = ev.target;
    if (PAGE !== 'editor' || !P) return;
    if (t.dataset.say !== undefined) { if (+t.dataset.say === UI.scene && $('#hiSub')) $('#hiSub').textContent = t.value; later(); }
    else if (t.dataset.lk || t.dataset.bar !== undefined || t.dataset.item !== undefined || ['hiTitle', 'hiBrand', 'hiClose'].includes(t.id)) later();
  }
  function onChange(ev) {
    const t = ev.target;
    if (t.id === 'hiTrPick') { UI.pick = t.value; UI.tlang = ''; return draw(); }
    if (PAGE !== 'editor' || !P) return;
    if (t.id === 'hiLook') { collect(); const sc = P.scenes[UI.scene]; sc.look = {kind: t.value, ...(t.value === 'bar_chart' ? {bars: [{label: '', value: ''}, {label: '', value: ''}]} : {})}; return persist(true); }
    if (['hiShape', 'hiAspect', 'hiPLang', 'hiAv'].includes(t.id)) return persist(true);
    if (t.dataset.lk || t.dataset.bar !== undefined) { clearTimeout(SAVE_T); return persist(true); }
  }
  function onSubmit(ev) {
    const f = ev.target.closest('form[data-f]'); if (!f) return;
    ev.preventDefault();
    const v = id => ($(id)?.value || '').trim(), btn = f.querySelector('button.hi-btn:not(.q)');
    const busy = (on, txt) => { if (btn?.isConnected) { btn.disabled = on; if (txt) btn.dataset.t = btn.dataset.t || btn.textContent, btn.textContent = on ? txt : btn.dataset.t; } };
    const run = (fn, done, txt) => { busy(true, txt); act(fn, done).finally(() => busy(false, txt)); };
    switch (f.dataset.f) {
      case 'draft': if (v('#hiLine').length < 6) { toast('Say in one line what the video should be about.', true); return $('#hiLine').focus(); }
        return run(() => api('POST', `${S}/draft`, {ask: v('#hiLine'), shape: v('#hiKind'), lang: v('#hiLang'), seconds: +v('#hiSecs') || 30, avatar_id: v('#hiAvSel')}), p => { P = null; go('editor', p.id); }, 'Writing the script…');
      case 'avatar': { const file = $('#hiAvFile').files[0]; if (!file) return;
        return run(async () => { const up = await upload(file); return api('POST', `${S}/avatar`, {name: v('#hiAvName'), file_id: up?.file_id || up?.id, consent: $('#hiAvOk').checked}); }, () => { toast('Avatar added.'); UI.tab.av = 'My avatars'; go('avatars'); }, 'Adding…'); }
      case 'brand': return run(() => api('PUT', `${H}/brand`, {name: v('#hiBName'), closing: v('#hiBClose'), color: v('#hiBColor')}), () => { toast('Saved. New videos start with it.'); draw(); });
      case 'gloss': return run(() => api('POST', `${H}/glossary`, {term: v('#hiGTerm'), mode: v('#hiGMode'), to: v('#hiGTo'), lang: v('#hiGLang')}));
      case 'use': { const values = {}; for (const i of $$('[data-var]')) values[i.dataset.var] = i.value;
        return run(() => api('POST', `${H}/template/use`, {id: UI.use, values, lang: v('#hiTLang'), avatar_id: v('#hiTAv')}), p => { UI.use = ''; P = null; go('editor', p.id); }, 'Making the draft…'); }
      case 'batch': return run(() => api('POST', `${H}/batch`, {scripts: $('#hiBatch').value.split(/\n\s*\n/), lang: v('#hiBLang'), avatar_id: v('#hiBAv')}), r => { toast(`${r.made.length} draft${r.made.length === 1 ? '' : 's'} made.`); UI.tab.ap = ''; UI.tab.pr = 'Drafts'; go('projects'); }, 'Making the drafts…');
      case 'names': return run(() => api('POST', `${H}/personalise`, {project: v('#hiNPick'), names: $('#hiNames').value.split('\n')}), r => { toast(`${r.made.length} draft${r.made.length === 1 ? '' : 's'} made.`); UI.tab.ap = ''; UI.tab.pr = 'Drafts'; go('projects'); }, 'Making the drafts…');
      case 'brain': return run(() => api('POST', `${H}/brain`, {id: v('#hiBrId'), name: v('#hiBrName'), knows: v('#hiBrKnows'), opening: v('#hiBrOpen'), links: v('#hiBrLinks').split('\n'), lang: v('#hiBrLang')}), b => { UI.brain = b.id; toast('Saved.'); draw(); });
    }
  }

  async function genBox() {
    clearTimeout(SAVE_T); await persist(false);
    if (!P || P.problems?.length) return draw();
    const p = P, silent = !con().voice || !!$('#hiSilent')?.checked, st = D.status || {};
    dialog(`<h2>Generate video</h2><div><div class="hi-kv"><span class="hi-mut">Scenes</span><b class="hi-num">${p.scenes.length}</b></div>
        <div class="hi-kv"><span class="hi-mut">Length</span><b class="hi-num">about ${secs(estimate(p))}</b></div>
        <div class="hi-kv"><span class="hi-mut">Size</span><span>${p.aspect === '9:16' ? 'Tall 9:16' : p.aspect === '1:1' ? 'Square 1:1' : 'Wide 16:9'}</span></div>
        <div class="hi-kv"><span class="hi-mut">Sound</span><span>${silent ? 'Captions only, no voice' : 'Hoola voice, ' + esc(langs()[p.lang] || p.lang)}</span></div></div>
      ${st.draw ? '' : `<div class="hi-note warn">The video engine is not installed on this server, so this cannot be made here yet.</div>`}
      <p class="hi-sm hi-mut">Drawing takes a few minutes. No money is charged on this server; a rupee meter is not built yet.</p>
      <div class="hi-row" style="justify-content:flex-end"><button class="hi-btn q" data-a="close">Not now</button><button class="hi-btn" data-a="make" data-id="${esc(p.id)}" data-silent="${silent ? 1 : 0}"${st.draw ? '' : ' disabled'}>Make the video</button></div>`);
  }
  async function startMake(id, silent) {
    try { await api('POST', `${S}/make`, {id, silent}); URLS.delete(`${S}/video?id=${q(id)}`); await load(); P = null; go('making', id); }
    catch (e) { toast(e.message, true); closeDlg(); }
  }
  async function hear(lang, btn) {
    btn.disabled = true; const was = btn.textContent; btn.textContent = 'Speaking…';
    try { const r = await api('GET', `${H}/voice?lang=${q(lang)}`, undefined, {raw: true}); const a = new Audio(URL.createObjectURL(await r.blob())); await a.play(); }
    catch (e) { toast(e.message || 'The voice engine did not answer.', true); }
    btn.disabled = false; btn.textContent = was;
  }
  async function download(id) {
    const p = D.projects.find(x => x.id === id);
    try { const a = document.createElement('a'); a.href = await blobUrl(`${S}/video?id=${q(id)}`); a.download = `${(p?.title || 'hoola-video').replace(/[^\w .-]+/g, '_').slice(0, 60)}.mp4`; document.body.appendChild(a); a.click(); a.remove(); }
    catch (e) { toast(e.message, true); }
  }

  return {open, leave};
};
