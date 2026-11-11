/* HOOLA DESIGN - the app (docs/HOOLA_DESIGN_PLAN.md, section 3: HD.app).
   Signs in with the console's token, routes  #/  (your files)  and  #/f/<file id>  (the editor), opens a file
   (file row -> live room -> first document -> editor), keeps the file's thumbnail fresh and guards changes that
   have not reached the server yet. Later phases add feature files after this one and plug in through HD.ui.
   Phase D5:  #/s/<share token>  opens a VIEW-ONLY editor with no sign-in at all (the public /shared routes and
   the ?share= socket; while it is open every other /api call is answered here with a 403, so nothing can send a
   signed-out visitor to the sign-in page); "?node=<id>" after either address selects that layer and zooms to it;
   on('open' | 'close', fn(file)) tells feature files when an editor is mounted / about to go. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui, h = ui.h, icon = ui.icon, clear = ui.clear;
  const em = new HD.Emitter(), rawFetch = window.fetch.bind(window);
  const app = HD.app = {file: null, boot: boot, openFile: openFile, openShared: openShared, closeFile: closeFile, route: route, home: showHome, saveThumb: saveThumb, focusNode: focusNode,
    on: (evt, fn) => em.on(evt, fn), rawFetch: rawFetch, link: link};
  let root = null, opening = 0, wired = false, thumbT = 0, thumbDirty = false, editorEl = null, lastThumb = null, shared = null;
  const enc = encodeURIComponent;
  const SHARE_RE = /^#\/s\/([^/?#]+)(?:\/p\/([^/?#]+))?/;
  const hashNode = () => { const m = /[?&]node=([^&#]+)/.exec(location.hash || ''); try { return m ? decodeURIComponent(m[1]) : null; } catch (e) { return null; } };
  /* the address of this file (or of one layer in it): signed-in people get #/f/<id>, a share link stays #/s/<token> */
  function link(node, token) { const f = app.file; if (!f) return ''; const t = token === undefined ? f.share : token;
    return location.origin + location.pathname + (t ? '#/s/' + enc(t) : '#/f/' + enc(f.id)) + (node ? '?node=' + enc(node) : ''); }
  /* While a share link is open, nothing but the public /shared routes may be asked of the server: a signed-out
     visitor would get a 401, and HD.ui.api answers a 401 by leaving for the sign-in page. Every other /api call
     is answered right here instead, whoever makes it. */
  window.fetch = function (input, init) {
    if (shared) { let path = typeof input === 'string' ? input : (input && input.url) || ''; try { path = new URL(path, location.href).pathname; } catch (e) { /* keep it */ }
      if (/^\/api\//.test(path) && !/^\/api\/design\/shared\//.test(path)) return Promise.resolve(new Response(JSON.stringify({detail: 'This is a view-only link. Sign in to do that.'}), {status: 403, headers: {'Content-Type': 'application/json'}})); }
    return rawFetch(input, init);
  };
  function sharedMode(token) { shared = token || null; if (HD.render) HD.render.assetURL = token ? (hash => '/api/design/shared/' + enc(token) + '/assets/' + enc(hash)) : null; }

  function boot() {
    root = document.getElementById('hd-app'); if (!root) { root = h('div', {id: 'hd-app'}); document.body.appendChild(root); }
    if (!ui.token && !SHARE_RE.test(location.hash || '')) { location.replace('/console/'); return; }
    window.addEventListener('hashchange', route);
    window.addEventListener('beforeunload', ev => { if (!app.file) return; if (thumbDirty) saveThumb(true);
      if (HD.net && HD.net.pending && HD.net.pending() > 0 && HD.store && !HD.store.readOnly) { ev.preventDefault(); ev.returnValue = 'Some changes have not reached the server yet.'; } });
    document.addEventListener('visibilitychange', () => { if (document.hidden && app.file && thumbDirty) saveThumb(true); });
    route();
  }
  function route() {
    const sm = SHARE_RE.exec(location.hash || '');
    if (sm) { let token = sm[1], play = sm[2] || null; try { token = decodeURIComponent(token); if (play) play = decodeURIComponent(play); } catch (e) { /* as typed */ }
      if (app.file && app.file.share === token) { if (play) ui.fire('present', play); else focusNode(hashNode()); return; }
      openShared(token).then(ok => { if (ok && play && ui.hooks.present) ui.fire('present', play); }); return; }
    if (!ui.token) { location.replace('/console/'); return; }      /* signed out, and not a share link */
    const m = /^#\/f\/([^/?#]+)(?:\/p\/([^/?#]+))?/.exec(location.hash || '');
    if (!m) { closeFile(); showHome(); return; }
    const id = decodeURIComponent(m[1]), node = m[2] ? decodeURIComponent(m[2]) : null;
    if (app.file && app.file.id === id && !app.file.share) { if (node) ui.fire('present', node); else focusNode(hashNode()); return; }
    openFile(id).then(ok => { if (ok && node && ui.hooks.present) ui.fire('present', node); });
  }
  /* select one layer and bring it into view (the "?node=" of a copied link) */
  function focusNode(id) {
    if (!id || !app.file || !HD.store.has(id)) return false; const st = HD.store, n = st.get(id); if (!n || n.type === 'DOCUMENT') return false;
    const pg = n.type === 'PAGE' ? id : st.pageOf(id); if (pg && pg !== HD.sel.page) { if (ui.setPage) ui.setPage(pg); else HD.sel.setPage(pg); }
    if (n.type === 'PAGE') { try { HD.render.zoomToFit(undefined, true); } catch (e) { /* empty page */ } return true; }
    HD.sel.set([id]); if (ui.revealLayers) { try { ui.revealLayers([id]); } catch (e) { /* the layers list is not up yet */ } }
    const cv = HD.tools.canvas, b = st.worldBounds(id); if (!cv || !b || !(b.w > 0) || !(b.h > 0)) return true;
    const z = Math.max(0.02, Math.min(1, Math.min(cv.clientWidth / b.w, cv.clientHeight / b.h) * 0.82));
    HD.render.setView(HD.tools.view.at(z, b.x + b.w / 2, b.y + b.h / 2, cv.clientWidth / 2, cv.clientHeight / 2), true); return true;
  }

  /* ---------------------------------------------------------------- opening a file */
  function loading(text) { clear(root); root.appendChild(h('div', {class: 'hd-loading', role: 'status'}, h('div', null, h('i'), h('span', {text: text})))); }
  function problem(title, text) {
    clear(root); root.appendChild(h('div', {class: 'hd-home'}, h('div', {class: 'hd-empty', role: 'alert'}, h('div', {class: 'hd-art', 'aria-hidden': 'true'}, h('i'), h('i'), h('i'), h('i'), h('i'), h('i')), h('h2', {text: title}), h('p', {text: text}),
      h('button', {class: 'hd-btn pri big', type: 'button', text: 'Back to your files', on: {click: () => { location.hash = '#/'; }}}))));
  }
  /* a share link that does not open: a page that says so, never a blank screen and never the sign-in wall */
  function sharedProblem(title, text, again) {
    clear(root); document.title = 'Hoola Design'; root.appendChild(h('div', {class: 'hd-home'}, h('div', {class: 'hd-empty hd-co-gone', role: 'alert'}, h('div', {class: 'hd-art', 'aria-hidden': 'true'}, h('i'), h('i'), h('i'), h('i'), h('i'), h('i')), h('h2', {text: title}), h('p', {text: text}),
      h('div', {class: 'hd-co-gone-acts'}, again ? h('button', {class: 'hd-btn big', type: 'button', text: 'Try again', on: {click: again}}) : null,
        h('a', {class: 'hd-btn pri big', href: '/console/', text: ui.token ? 'Open Hoola' : 'Sign in to Hoola'})))));
  }
  function waitInit(id, opts) {
    return new Promise(resolve => { let done = false; const offs = []; const fin = v => { if (done) return; done = true; for (const o of offs) { try { if (typeof o === 'function') o(); } catch (e) { /* listener already gone */ } } resolve(v); };
      offs.push(HD.net.on('init', () => fin('live'))); offs.push(HD.net.on('status', s => { if (s === 'auth' || s === 'forbidden' || s === 'notfound') fin(s); }));
      try { HD.net.connect(id, opts); } catch (e) { fin('offline'); } setTimeout(() => fin('offline'), 9000); });
  }
  async function openShared(token) {
    shut(); const my = ++opening; loading('Opening the shared design…'); let d = null, why = '';
    try { const r = await rawFetch('/api/design/shared/' + enc(token) + '/doc', {credentials: 'omit', cache: 'no-store'});
      if (r.ok) d = await r.json(); else why = r.status === 429 ? 'busy' : r.status === 404 || r.status === 422 ? 'gone' : 'down'; } catch (e) { why = 'down'; }
    if (my !== opening) return false;
    if (!d || !d.doc) { if (why === 'gone') sharedProblem('This link is not active', 'The owner may have switched the link off, or the file is no longer there. Ask them to share it again.');
      else if (why === 'busy') sharedProblem('Too many requests', 'This link was opened very often in the last minute. Please wait a minute and try again.', () => openShared(token));
      else sharedProblem('The shared design could not be opened', 'The server did not answer. Check your connection and try again.', () => openShared(token)); return false; }
    const info = d.file || {}; app.file = {id: info.id || '', name: info.name || 'Untitled', role: 'view', share: token}; sharedMode(token);
    const state = await waitInit(app.file.id, {share: token}); if (my !== opening) return false;
    if (state === 'notfound' || state === 'auth' || state === 'forbidden') { app.file = null; HD.net.close(); sharedMode(null); sharedProblem('This link is not active', 'The owner may have switched the link off, or the file is no longer there. Ask them to share it again.'); return false; }
    if (state !== 'live') { HD.store.load(d.doc, 0); HD.tools.readOnly = true; }     /* no live room right now: what the link showed a moment ago */
    mountEditor(my); return true;
  }
  async function openFile(id) {
    shut(); const my = ++opening; loading('Opening your design…'); let meta;
    try { meta = await ui.api('GET', '/files/' + enc(id)); } catch (e) { if (my === opening) problem('This file could not be opened', e.message || 'It may have been deleted, or it belongs to another account.'); return false; }
    if (my !== opening) return false;
    app.file = {id: meta.id || id, name: meta.name || 'Untitled', role: 'edit'};
    const state = await waitInit(app.file.id); if (my !== opening) return false;
    if (state === 'auth') { location.replace('/console/'); return false; }
    if (state === 'notfound') { app.file = null; HD.net.close(); problem('This file could not be found', 'It may have been deleted, or it belongs to another account.'); return false; }
    if (state !== 'live') {   /* no live room right now: show the last saved document, read only, and keep trying */
      try { const d = await ui.api('GET', '/files/' + enc(app.file.id) + '/doc'); if (my !== opening) return false; HD.store.load(d.doc || {nodes: {}}, 0); HD.tools.readOnly = true; }
      catch (e) { if (my === opening) { app.file = null; HD.net.close(); problem('This file could not be opened', e.message || 'The server did not answer. Please try again.'); } return false; }
    }
    mountEditor(my); return true;
  }
  function mountEditor(my) {
    syncRole(); wire(); clear(root); editorEl = h('div', {class: 'hd-editor-host', style: {height: '100%'}}); root.appendChild(editorEl); ui.mount(editorEl);
    document.title = app.file.name + ' – Hoola Design'; thumbDirty = false; const node = hashNode();
    em.emit('open', app.file);
    requestAnimationFrame(() => { if (my !== opening || !app.file) return; try { HD.render.zoomToFit(undefined, false); } catch (e) { /* an empty page */ } if (node) focusNode(node); loadFonts(); ui.refresh(); });
  }
  function syncRole() { if (!app.file) return; const nf = HD.net.file; if (nf && nf.name) app.file.name = nf.name; if (HD.net.role) { app.file.role = HD.net.role === 'view' ? 'view' : 'edit'; HD.tools.readOnly = false; }
    if (app.file.role === 'view' && HD.tools.current && !{move: 1, hand: 1, comment: 1, zoom: 1}[HD.tools.current]) HD.tools.set('move'); }
  function wire() {
    if (wired) return; wired = true;
    HD.net.on('init', () => { if (!app.file) return; syncRole(); document.title = app.file.name + ' – Hoola Design'; loadFonts(); ui.refresh(); });
    HD.net.on('status', s => { if (!app.file) return; const was = app.file;
      if (was.share) { if (s === 'notfound' || s === 'auth') { closeFile(); sharedProblem('This link was switched off', 'The owner stopped sharing “' + was.name + '”, or the file is no longer there. Ask them to share it again.'); } return; }
      if (s === 'auth') location.replace('/console/'); else if (s === 'notfound') { closeFile(); problem('This file is no longer here', '“' + was.name + '” was moved to the trash or deleted.'); } else if (s === 'forbidden') { app.file.role = 'view'; ui.refresh(); } });
    HD.net.on('file', f => { if (app.file && f && f.name) document.title = f.name + ' – Hoola Design'; });
    HD.net.on('reject', () => ui.toast('The server did not accept one change, so it was taken back.', true));
    HD.store.on('change', ch => { if (!app.file || app.file.share || (ch && ch.remote)) return; thumbDirty = true; clearTimeout(thumbT); thumbT = setTimeout(() => saveThumb(false), 30000); });
  }
  function loadFonts() { const seen = new Set(); let n = 0; for (const p of HD.store.pages()) HD.store.walk(p, (id, node) => { if (++n > 20000) return false; if (node && node.type === 'TEXT') seen.add(node.font || 'Inter'); return true; }); seen.forEach(f => ui.loadFont(f)); }
  function closeFile() { opening++; shut(); }
  function shut() {
    clearTimeout(thumbT); if (!app.file) { sharedMode(null); return; } if (thumbDirty) lastThumb = saveThumb(false);
    try { em.emit('close', app.file); } catch (e) { /* a listener must not keep a file open */ }
    try { ui.unmount(); } catch (e) { /* not mounted */ } try { HD.net.close(); } catch (e) { /* not connected */ }
    sharedMode(null); app.file = null; editorEl = null; HD.tools.readOnly = false; document.title = 'Hoola Design';
  }

  /* ---------------------------------------------------------------- thumbnail (the first frame, else the first layer) */
  function thumbTarget() { const pages = HD.store.pages(); for (const p of pages) { const kids = HD.store.children(p); if (!kids.length) continue; const frame = kids.find(k => { const n = HD.store.get(k); return n && (n.type === 'FRAME' || n.type === 'COMPONENT') && n.visible !== false; }); return frame || kids[0]; } return null; }
  function toBlob(cv) { return new Promise(resolve => { try { cv.toBlob(b => resolve(b), 'image/png'); } catch (e) { resolve(null); } }); }
  async function saveThumb(leaving) {
    const f = app.file; if (!f || f.role === 'view' || f.share || !HD.render || !HD.render.toCanvas) return;
    if (HD.net && HD.net.held) { if (!leaving) { clearTimeout(thumbT); thumbT = setTimeout(() => saveThumb(false), 30000); } return; }   /* a version preview is on screen: never the file's picture */
    thumbDirty = false; clearTimeout(thumbT);
    try { const id = thumbTarget(); if (!id) return; const b = HD.store.worldBounds(id), side = Math.max(b.w, b.h, 1); let scale = Math.min(1, 480 / side), blob = null;
      for (let i = 0; i < 4; i++) { const cv = HD.render.toCanvas(id, scale, {bg: '#FFFFFF'}); if (!cv || !cv.width || !cv.height) return; blob = await toBlob(cv); if (blob && blob.size <= 290 * 1024) break; scale *= 0.6; blob = null; }
      if (!blob) return;
      if (leaving && window.fetch) { fetch('/api/design/files/' + enc(f.id) + '/thumb', {method: 'PUT', headers: {Authorization: 'Bearer ' + ui.token, 'Content-Type': 'image/png'}, body: blob, keepalive: blob.size < 60000, credentials: 'omit'}).catch(() => {}); return; }
      await ui.api('PUT', '/files/' + enc(f.id) + '/thumb', blob);
    } catch (e) { /* a thumbnail is never worth an error on her screen */ }
  }

  /* ---------------------------------------------------------------- your files */
  const home = {tab: 'recent', q: '', files: [], urls: new Map(), grid: null, title: null, seq: 0, t: 0};
  const TABS = [['recent', 'Recent'], ['starred', 'Starred'], ['trash', 'Trash']];
  function ago(iso) {
    const t = Date.parse(iso || ''); if (!t) return ''; const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now'; if (s < 3600) { const m = Math.floor(s / 60); return m + (m === 1 ? ' minute ago' : ' minutes ago'); } if (s < 86400) { const hr = Math.floor(s / 3600); return hr + (hr === 1 ? ' hour ago' : ' hours ago'); }
    if (s < 172800) return 'yesterday'; if (s < 86400 * 7) return Math.floor(s / 86400) + ' days ago';
    try { return new Date(t).toLocaleDateString(undefined, {day: 'numeric', month: 'short', year: 'numeric'}); } catch (e) { return ''; }
  }
  function showHome() {
    document.title = 'Hoola Design'; clear(root);
    const search = h('input', {class: 'hd-in', type: 'search', placeholder: 'Search your designs', 'aria-label': 'Search your designs', value: home.q});
    search.addEventListener('input', () => { home.q = search.value.trim(); clearTimeout(home.t); home.t = setTimeout(load, 220); });
    const theme = h('button', {class: 'hd-ib', type: 'button', title: 'Light or dark', 'aria-label': 'Switch between light and dark'}, icon(window.HoolaTheme && window.HoolaTheme.dark() ? 'sun' : 'moon'));
    theme.addEventListener('click', ev => { const th = window.HoolaTheme; if (!th) return; th.setTheme(th.dark() ? 'light' : 'dark', ev); clear(theme).appendChild(icon(th.dark() ? 'sun' : 'moon')); });
    if (window.HoolaTheme && !home.themed) { home.themed = true; window.HoolaTheme.onChange(() => { const b = document.querySelector('.hd-hright .hd-ib'); if (b) clear(b).appendChild(icon(window.HoolaTheme.dark() ? 'sun' : 'moon')); }); }
    home.title = h('h1', {text: 'Recent'}); home.tabs = h('div', {class: 'hd-seg', role: 'tablist', 'aria-label': 'Which files'});
    for (const t of TABS) home.tabs.appendChild(h('button', {class: 'hd-segb', type: 'button', role: 'tab', 'data-v': t[0], text: t[1], on: {click: () => { home.tab = t[0]; load(); }}}));
    home.grid = h('div', {class: 'hd-grid', 'aria-live': 'polite'});
    root.appendChild(h('div', {class: 'hd-home'},
      h('header', {class: 'hd-hhead'}, h('a', {class: 'hd-brand', href: '#/', 'aria-label': 'Hoola Design, your files'}, h('img', {src: '/static/hoola-mark.png', alt: '', width: 28, height: 28}), h('span', null, 'Hoola ', h('span', {text: 'Design'}))),
        h('div', {class: 'hd-hsearch', role: 'search'}, icon('search'), search),
        h('div', {class: 'hd-hright'}, h('a', {class: 'hd-hlink', href: '/console/', text: 'Console'}), theme, h('button', {class: 'hd-btn pri big', type: 'button', on: {click: newFile}}, icon('plus'), h('span', {text: 'New design file'})))),
      h('main', {class: 'hd-hmain'}, h('div', {class: 'hd-hbar'}, home.title, home.tabs), home.grid)));
    load(); if (lastThumb) { const p = lastThumb; lastThumb = null; p.then(() => { if (home.grid && document.contains(home.grid)) load(); }); }
  }
  async function newFile(ev) {
    const b = ev && ev.currentTarget; if (b) b.disabled = true;
    try { const f = await ui.api('POST', '/files', {name: 'Untitled'}); location.hash = '#/f/' + enc(f.id); } catch (e) { ui.toast(e.message || 'A new file could not be made.', true); if (b) b.disabled = false; }
  }
  async function load() {
    if (!home.grid || !document.contains(home.grid)) return; const my = ++home.seq, trash = home.tab === 'trash';
    for (const b of home.tabs.children) { const on = b.dataset.v === home.tab; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); }
    home.title.textContent = home.q ? 'Search results' : (TABS.find(t => t[0] === home.tab) || TABS[0])[1];
    if (!home.grid.firstChild) for (let i = 0; i < 6; i++) home.grid.appendChild(h('div', {class: 'hd-skel', 'aria-hidden': 'true'}));
    let files;
    try { const r = await ui.api('GET', '/files?q=' + enc(home.q) + '&trash=' + (trash ? 1 : 0)); files = (r && r.files) || []; }
    catch (e) { if (my !== home.seq) return; clear(home.grid); home.grid.className = ''; home.grid.appendChild(h('div', {class: 'hd-herr', role: 'alert'}, h('p', {text: e.message || 'Your files could not be loaded.'}), h('button', {class: 'hd-btn', type: 'button', text: 'Try again', on: {click: load}}))); return; }
    if (my !== home.seq) return; if (home.tab === 'starred') files = files.filter(f => f.star); home.files = files; draw();
  }
  function draw() {
    const g = home.grid, files = home.files, trash = home.tab === 'trash'; clear(g); g.className = 'hd-grid';
    if (!files.length) { g.className = ''; let t = 'Start your first design', p = 'Frames, shapes, text and vectors on an endless canvas. Everyone you invite works in the same file at the same time.', btn = true;
      if (home.q) { t = 'Nothing called “' + home.q + '”'; p = 'Try a shorter word, or look in the trash.'; btn = false; } else if (trash) { t = 'The trash is empty'; p = 'Files you delete wait here until you delete them for good.'; btn = false; } else if (home.tab === 'starred') { t = 'No starred files yet'; p = 'Star a file to keep it at the top.'; btn = false; }
      g.appendChild(h('div', {class: 'hd-empty'}, h('div', {class: 'hd-art', 'aria-hidden': 'true'}, h('i'), h('i'), h('i'), h('i'), h('i'), h('i')), h('h2', {text: t}), h('p', {text: p}), btn ? h('button', {class: 'hd-btn pri big', type: 'button', on: {click: newFile}}, icon('plus'), h('span', {text: 'New design file'})) : null)); return; }
    if (!trash && !home.q && home.tab === 'recent') g.appendChild(h('button', {class: 'hd-newcard', type: 'button', on: {click: newFile}}, h('span', {class: 'hd-plus'}, icon('plus', 20)), h('span', {text: 'New design file'})));
    for (const f of files) g.appendChild(card(f, trash));
  }
  function thumb(f, box) {
    if (!f.thumb_at) return; const key = f.id + '@' + f.thumb_at, put = url => { if (!document.contains(box)) return; clear(box).appendChild(h('img', {src: url, alt: '', loading: 'lazy', draggable: 'false'})); };
    if (home.urls.has(key)) { put(home.urls.get(key)); return; }
    ui.api('GET', '/files/' + enc(f.id) + '/thumb').then(blob => { if (!blob || !blob.size) return; const url = URL.createObjectURL(blob); home.urls.set(key, url); if (home.urls.size > 300) { const first = home.urls.keys().next().value; URL.revokeObjectURL(home.urls.get(first)); home.urls.delete(first); } put(url); }).catch(() => {});
  }
  function card(f, trash) {
    const box = h('div', {class: 'hd-thumb'}, icon('frame', 34)), name = h('span', {class: 'hd-cname', text: f.name || 'Untitled'});
    const open = h('button', {class: 'hd-open', type: 'button', 'aria-label': (trash ? 'Options for ' : 'Open ') + (f.name || 'Untitled')}, box, h('div', {class: 'hd-cmeta'}, name, h('span', {class: 'hd-ctime', text: trash ? 'Deleted ' + ago(f.trashed_at) : 'Edited ' + ago(f.updated_at)})));
    const more = h('button', {class: 'hd-ib hd-cmore', type: 'button', title: 'More', 'aria-label': 'More options for ' + (f.name || 'Untitled'), 'aria-haspopup': 'menu'}, icon('dots'));
    const star = trash ? null : h('button', {class: 'hd-ib hd-cstar' + (f.star ? ' on' : ''), type: 'button', title: f.star ? 'Remove the star' : 'Star this file', 'aria-label': f.star ? 'Remove the star' : 'Star this file', 'aria-pressed': String(!!f.star)}, icon('star2'));
    const el = h('article', {class: 'hd-card', 'data-file': f.id}, open, star, more);   /* data-file: feature files badge a card (D9c branches) */
    const act = (p, okMsg) => p.then(() => { if (okMsg) ui.toast(okMsg); load(); }).catch(e => ui.toast(e.message || 'That did not work.', true));
    const rename = () => { const inp = h('input', {class: 'hd-in hd-inline', type: 'text', value: f.name || '', 'aria-label': 'File name', maxlength: '120'}); let done = false;
      const fin = save => { if (done) return; done = true; const v = inp.value.trim(); if (inp.parentNode) inp.parentNode.replaceChild(name, inp); if (save && v && v !== f.name) { name.textContent = v; act(ui.api('PATCH', '/files/' + enc(f.id), {name: v})); } };
      inp.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') fin(true); else if (ev.key === 'Escape') fin(false); }); inp.addEventListener('blur', () => fin(true)); inp.addEventListener('click', ev => { ev.stopPropagation(); ev.preventDefault(); });
      name.parentNode.replaceChild(inp, name); inp.focus(); inp.select(); };
    const toggleStar = () => act(ui.api('PATCH', '/files/' + enc(f.id), {star: !f.star}));
    const items = () => trash ? [{label: 'Restore', icon: 'undo', run: () => act(ui.api('POST', '/files/' + enc(f.id) + '/restore'), 'Restored.')}, '-', {label: 'Delete for good', icon: 'trash', danger: true, run: () => { if (window.confirm('Delete “' + (f.name || 'Untitled') + '” for good? This cannot be undone.')) act(ui.api('DELETE', '/files/' + enc(f.id) + '?forever=1'), 'Deleted.'); }}]
      : [{label: 'Open', icon: 'right', run: () => { location.hash = '#/f/' + enc(f.id); }}, {label: 'Open in a new tab', icon: 'link', run: () => window.open(location.pathname + '#/f/' + enc(f.id), '_blank', 'noopener')}, '-', {label: 'Rename', icon: 'text', run: rename}, {label: 'Duplicate', icon: 'copy', run: () => act(ui.api('POST', '/files/' + enc(f.id) + '/duplicate'), 'Duplicated.')}, {label: f.star ? 'Remove the star' : 'Star', icon: 'star2', run: toggleStar}, '-', {label: 'Move to the trash', icon: 'trash', danger: true, run: () => act(ui.api('DELETE', '/files/' + enc(f.id)), 'Moved to the trash.')}];
    open.addEventListener('click', ev => { if (ev.target.tagName === 'INPUT') return; if (trash) ui.menu(more, items(), {label: 'File'}); else location.hash = '#/f/' + enc(f.id); });
    more.addEventListener('click', () => ui.menu(more, items(), {label: 'File'})); if (star) star.addEventListener('click', toggleStar);
    el.addEventListener('contextmenu', ev => { ev.preventDefault(); ui.menu({x: ev.clientX, y: ev.clientY}, items(), {label: 'File'}); });
    name.addEventListener('dblclick', ev => { if (!trash) { ev.stopPropagation(); ev.preventDefault(); rename(); } });
    thumb(f, box); return el;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
